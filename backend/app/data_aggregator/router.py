"""
API роутер для модуля агрегации данных.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

from .main import DataAggregator
from .schemas import (
    AggregationScenarioRequest,
    AggregationScenarioResponse,
    CustomDatasetRequest,
    ExecutionResult,
    PreviewJoinRequest,
    PreviewJoinResponse,
    HealthCheckResponse,
    ColumnInfo
)
from ..database import get_db

logger = logging.getLogger(__name__)

# Создаем роутер
router = APIRouter(prefix="/api/v1/aggregation", tags=["Data Aggregation"])

# Создаем экземпляр агрегатора
aggregator = DataAggregator()


@router.post("/create-scenario", response_model=AggregationScenarioResponse)
async def create_aggregation_scenario(
    request: AggregationScenarioRequest,
    db: Session = Depends(get_db)
):
    """
    Создает новый сценарий агрегации данных.
    
    Этот endpoint позволяет создать сценарий для агрегации данных из множественных источников
    с поддержкой кастомизации (выбор конкретных колонок) и сложных операций JOIN, GROUP BY.
    """
    try:
        logger.info(f"Creating aggregation scenario: {request.name}")
        
        result = await aggregator.create_scenario(request, db)
        
        logger.info(f"Scenario created successfully: {result.scenario_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error creating scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create scenario: {str(e)}")


@router.get("/scenario/{scenario_id}", response_model=Dict[str, Any])
async def get_scenario_info(
    scenario_id: str,
    db: Session = Depends(get_db)
):
    """
    Получает информацию о сценарии агрегации.
    """
    try:
        from ..shared.schemas import AggregationScenario
        
        scenario = db.query(AggregationScenario).filter(
            AggregationScenario.id == int(scenario_id)
        ).first()
        
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        return {
            "scenario_id": str(scenario.id),
            "name": scenario.scenario_name,
            "description": scenario.description,
            "status": scenario.status,
            "sources": scenario.sources,
            "aggregations": scenario.aggregations,
            "enrichments": scenario.enrichments,
            "target_requirements": scenario.target_requirements,
            "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
            "last_executed": scenario.last_executed.isoformat() if scenario.last_executed else None,
            "execution_stats": scenario.execution_stats
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scenario ID")
    except Exception as e:
        logger.error(f"Error getting scenario info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get scenario info: {str(e)}")


@router.post("/execute/{scenario_id}", response_model=ExecutionResult)
async def execute_aggregation_scenario(
    scenario_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Выполняет сценарий агрегации данных.
    
    Запускает выполнение агрегации в фоновом режиме и возвращает ID выполнения
    для отслеживания статуса.
    """
    try:
        logger.info(f"Starting execution of scenario: {scenario_id}")
        
        # Запускаем выполнение в фоновом режиме
        background_tasks.add_task(aggregator.execute_scenario, scenario_id, db)
        
        # Возвращаем начальный статус
        execution_result = ExecutionResult(
            execution_id=f"exec_{scenario_id}_{int(datetime.utcnow().timestamp())}",
            scenario_id=scenario_id,
            status="running"
        )
        
        return execution_result
        
    except Exception as e:
        logger.error(f"Error starting scenario execution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.get("/execution/{execution_id}", response_model=ExecutionResult)
async def get_execution_status(execution_id: str):
    """
    Получает статус выполнения агрегации по ID выполнения.
    """
    try:
        result = await aggregator.get_execution_status(execution_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting execution status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")


@router.post("/custom-dataset", response_model=Dict[str, Any])
async def create_custom_dataset(request: CustomDatasetRequest):
    """
    Создает кастомизированный набор данных из выбранных колонок разных источников.
    
    Это ключевая функция модуля - позволяет создавать микс данных из файлов,
    PostgreSQL, ClickHouse, HDFS в виде единой оптимизированной базы данных.
    """
    try:
        logger.info(f"Creating custom dataset: {request.dataset_name}")
        
        result = await aggregator.create_custom_dataset(request)
        
        if result["success"]:
            logger.info(f"Custom dataset created successfully: {request.dataset_name}")
        else:
            logger.error(f"Failed to create custom dataset: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating custom dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create custom dataset: {str(e)}")


@router.post("/preview-join", response_model=PreviewJoinResponse)
async def preview_join_operation(request: PreviewJoinRequest):
    """
    Предварительный просмотр результата JOIN операции.
    
    Позволяет увидеть результат соединения данных перед выполнением полной агрегации.
    """
    try:
        logger.info(f"Previewing JOIN between {request.left_source.source_id} and {request.right_source.source_id}")
        
        result = await aggregator.preview_join(request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in join preview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to preview join: {str(e)}")


@router.get("/column-mapping/{source_id}", response_model=List[Dict[str, Any]])
async def get_column_mapping(
    source_id: str,
    source_type: str,
    path: Optional[str] = None,
    connection: Optional[str] = None,
    table: Optional[str] = None
):
    """
    Получает список доступных колонок из источника данных.
    
    Используется для построения UI выбора колонок при создании кастомных наборов данных.
    """
    try:
        logger.info(f"Getting column mapping for source: {source_id}")
        
        # Создаем конфигурацию источника
        source_config = {
            "source_id": source_id,
            "source_type": source_type,
            "path": path,
            "connection": connection,
            "table": table,
            "selected_columns": []  # Пустой список для получения всех колонок
        }
        
        columns = await aggregator.get_available_columns(source_config)
        
        return columns
        
    except Exception as e:
        logger.error(f"Error getting column mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get column mapping: {str(e)}")


@router.post("/validate-scenario", response_model=Dict[str, Any])
async def validate_aggregation_scenario(request: AggregationScenarioRequest):
    """
    Валидирует сценарий агрегации без его создания.
    
    Проверяет совместимость источников данных, корректность агрегаций
    и возвращает предупреждения и ошибки.
    """
    try:
        logger.info(f"Validating scenario: {request.name}")
        
        result = await aggregator.validate_scenario(request)
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to validate scenario: {str(e)}")


@router.get("/sources", response_model=List[Dict[str, Any]])
async def get_available_sources():
    """
    Получает список доступных источников данных.
    
    Сканирует data_landing_zone и возвращает информацию о доступных файлах и БД.
    """
    try:
        logger.info("Getting available data sources")
        
        sources = []
        
        # Сканируем data_landing_zone
        from pathlib import Path
        
        # Очищенные данные от модуля 1
        cleaned_dir = Path("data_landing_zone/cleaned")
        if cleaned_dir.exists():
            for source_dir in cleaned_dir.iterdir():
                if source_dir.is_dir():
                    for file_path in source_dir.glob("*.parquet"):
                        sources.append({
                            "source_id": f"cleaned_{source_dir.name}_{file_path.stem}",
                            "source_type": "file",
                            "path": str(file_path),
                            "description": f"Cleaned data from module 1: {source_dir.name}",
                            "format": "parquet"
                        })
        
        # Сырые данные
        raw_dir = Path("data_landing_zone/raw")
        if raw_dir.exists():
            for file_path in raw_dir.glob("*"):
                if file_path.is_file() and file_path.suffix in ['.csv', '.json', '.xml', '.parquet']:
                    sources.append({
                        "source_id": f"raw_{file_path.stem}",
                        "source_type": "file",
                        "path": str(file_path),
                        "description": f"Raw data file: {file_path.name}",
                        "format": file_path.suffix[1:]  # Убираем точку
                    })
        
        # Добавляем примеры подключений к БД
        sources.extend([
            {
                "source_id": "postgres_example",
                "source_type": "postgresql",
                "connection": "postgresql://user:password@localhost:5432/database",
                "description": "Example PostgreSQL connection",
                "tables": ["customers", "orders", "products"]
            },
            {
                "source_id": "clickhouse_example",
                "source_type": "clickhouse",
                "connection": "http://localhost:8123",
                "description": "Example ClickHouse connection",
                "tables": ["events", "analytics", "metrics"]
            }
        ])
        
        logger.info(f"Found {len(sources)} available sources")
        return sources
        
    except Exception as e:
        logger.error(f"Error getting available sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get available sources: {str(e)}")


@router.post("/analyze-sources", response_model=Dict[str, Any])
async def analyze_sources_compatibility(sources: List[Dict[str, Any]]):
    """
    Анализирует совместимость источников данных для агрегации.
    
    Проверяет возможность выполнения JOIN операций между источниками.
    """
    try:
        logger.info(f"Analyzing compatibility of {len(sources)} sources")
        
        # Преобразуем в объекты DataSource
        from .schemas import DataSource
        source_objects = []
        
        for source_dict in sources:
            try:
                source = DataSource(**source_dict)
                source_objects.append(source)
            except Exception as e:
                logger.warning(f"Invalid source configuration: {str(e)}")
                continue
        
        # Проверяем совместимость
        compatibility_issues = aggregator.data_collector.validate_source_compatibility(source_objects)
        
        # Анализируем каждый источник
        sources_analysis = []
        for source in source_objects:
            try:
                analysis = await aggregator.data_collector.analyze_source(source)
                sources_analysis.append({
                    "source_id": analysis.source_id,
                    "source_type": analysis.source_type.value,
                    "columns_count": len(analysis.columns),
                    "row_count": analysis.row_count,
                    "data_size_bytes": analysis.data_size_bytes,
                    "compatibility_issues": analysis.compatibility_issues
                })
            except Exception as e:
                logger.error(f"Error analyzing source {source.source_id}: {str(e)}")
                sources_analysis.append({
                    "source_id": source.source_id,
                    "source_type": source.source_type.value,
                    "error": str(e)
                })
        
        return {
            "compatible": len(compatibility_issues) == 0,
            "compatibility_issues": compatibility_issues,
            "sources_analysis": sources_analysis,
            "total_sources": len(source_objects),
            "analyzable_sources": len([s for s in sources_analysis if "error" not in s])
        }
        
    except Exception as e:
        logger.error(f"Error analyzing sources compatibility: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze sources: {str(e)}")


@router.get("/recommendations/{scenario_id}", response_model=List[Dict[str, Any]])
async def get_optimization_recommendations(
    scenario_id: str,
    db: Session = Depends(get_db)
):
    """
    Получает рекомендации по оптимизации для сценария агрегации.
    
    Интеграция с модулем 3 - возвращает сохраненные рекомендации по индексам и партициям.
    """
    try:
        from ..shared.schemas import OptimizationRecommendation, AggregationScenario
        
        # Получаем сценарий
        scenario = db.query(AggregationScenario).filter(
            AggregationScenario.id == int(scenario_id)
        ).first()
        
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        # Получаем рекомендации
        recommendations = db.query(OptimizationRecommendation).filter(
            OptimizationRecommendation.table_name == scenario.scenario_name
        ).all()
        
        result = []
        for rec in recommendations:
            result.append({
                "id": rec.id,
                "table_name": rec.table_name,
                "recommendation_type": rec.recommendation_type,
                "recommendation_details": rec.recommendation_details,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
                "updated_at": rec.updated_at.isoformat() if rec.updated_at else None
            })
        
        return result
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scenario ID")
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.get("/health-check", response_model=HealthCheckResponse)
async def health_check():
    """
    Проверка работоспособности модуля агрегации.
    
    Проверяет интеграции с модулями 3, 4, 5 и общее состояние системы.
    """
    try:
        result = await aggregator.get_health_status()
        return result
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/statistics", response_model=Dict[str, Any])
async def get_module_statistics():
    """
    Получает статистику работы модуля.
    """
    try:
        return {
            "module_stats": aggregator.stats,
            "cache_size": len(aggregator.execution_cache),
            "version": "1.0.0",
            "uptime": "N/A"  # Можно добавить отслеживание времени работы
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# Дополнительные utility endpoints

@router.delete("/scenario/{scenario_id}")
async def delete_scenario(
    scenario_id: str,
    db: Session = Depends(get_db)
):
    """
    Удаляет сценарий агрегации.
    """
    try:
        from ..shared.schemas import AggregationScenario
        
        scenario = db.query(AggregationScenario).filter(
            AggregationScenario.id == int(scenario_id)
        ).first()
        
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        
        db.delete(scenario)
        db.commit()
        
        # Обновляем статистику
        aggregator.stats["active_scenarios"] = max(0, aggregator.stats["active_scenarios"] - 1)
        
        return {"message": f"Scenario {scenario_id} deleted successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scenario ID")
    except Exception as e:
        logger.error(f"Error deleting scenario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete scenario: {str(e)}")


@router.get("/scenarios", response_model=List[Dict[str, Any]])
async def list_scenarios(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Получает список всех сценариев агрегации с фильтрацией.
    """
    try:
        from ..shared.schemas import AggregationScenario
        
        query = db.query(AggregationScenario)
        
        if status:
            query = query.filter(AggregationScenario.status == status)
        
        scenarios = query.offset(offset).limit(limit).all()
        
        result = []
        for scenario in scenarios:
            result.append({
                "scenario_id": str(scenario.id),
                "name": scenario.scenario_name,
                "description": scenario.description,
                "status": scenario.status,
                "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
                "last_executed": scenario.last_executed.isoformat() if scenario.last_executed else None,
                "sources_count": len(scenario.sources) if scenario.sources else 0,
                "aggregations_count": len(scenario.aggregations) if scenario.aggregations else 0
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing scenarios: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list scenarios: {str(e)}")


# Импортируем datetime для использования в execute_aggregation_scenario
from datetime import datetime
