"""
API Router для Модуля 3 - Оптимизация производительности
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from .schemas import (
    PerformanceAnalysisRequest,
    PerformanceAnalysisResult,
    OptimizationApplication,
    OptimizationResult,
    PerformanceHistory,
    OptimizationRecommendation,
    AnalysisStatus
)
from .main import (
    analyze_performance_source,
    analyze_warehouse_performance,
    apply_performance_optimizations,
    get_analysis_by_id,
    get_table_recommendations,
    get_table_history
)

logger = logging.getLogger(__name__)

# Создаем роутер для модуля оптимизации производительности
router = APIRouter(
    prefix="/api/v1/performance",
    tags=["Performance Optimization"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)


@router.post("/analyze", response_model=PerformanceAnalysisResult)
async def analyze_performance(
    request: PerformanceAnalysisRequest,
    background_tasks: BackgroundTasks
) -> PerformanceAnalysisResult:
    """
    Запуск анализа производительности источника данных
    
    Поддерживаемые источники:
    - Файлы: CSV, JSON, XML, Parquet
    - Базы данных: PostgreSQL, ClickHouse (строки подключения)
    - Директории с файлами
    - Существующие хранилища (design_id:xxx)
    
    Модуль автоматически определит тип данных через интеграцию с Модулем 5
    """
    try:
        logger.info(f"Получен запрос на анализ: {request.source}")
        
        # Проверяем, это анализ существующего хранилища или нового источника
        if request.source.startswith("design_id:"):
            design_id = request.source.split(":")[1]
            result = await analyze_warehouse_performance(design_id)
        else:
            result = await analyze_performance_source(request)
        
        if result.status == AnalysisStatus.ERROR:
            raise HTTPException(
                status_code=400, 
                detail=f"Ошибка анализа: {result.error_message}"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при анализе производительности: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{analysis_id}", response_model=PerformanceAnalysisResult)
async def get_analysis_result(analysis_id: str) -> PerformanceAnalysisResult:
    """
    Получение результатов анализа производительности по ID
    """
    try:
        result = await get_analysis_by_id(analysis_id)
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"Анализ с ID {analysis_id} не найден"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении результата анализа: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize/{analysis_id}", response_model=OptimizationResult)
async def apply_optimizations(
    analysis_id: str,
    application: OptimizationApplication
) -> OptimizationResult:
    """
    Применение рекомендаций по оптимизации
    
    Параметры:
    - dry_run: true для тестового режима (по умолчанию)
    - confirm_application: true для реального применения
    - recommendation_ids: список типов рекомендаций для применения
    """
    try:
        # Устанавливаем analysis_id из URL
        application.analysis_id = analysis_id
        
        # Проверяем подтверждение для реального применения
        if not application.dry_run and not application.confirm_application:
            raise HTTPException(
                status_code=400,
                detail="Для реального применения оптимизаций требуется подтверждение (confirm_application=true)"
            )
        
        result = await apply_performance_optimizations(application)
        
        if result.failed_recommendations and not result.applied_recommendations:
            raise HTTPException(
                status_code=400,
                detail=f"Не удалось применить ни одной рекомендации. Ошибки: {result.execution_details}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при применении оптимизаций: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations/{table_name}", response_model=List[OptimizationRecommendation])
async def get_recommendations_for_table(table_name: str) -> List[OptimizationRecommendation]:
    """
    Получение рекомендаций по оптимизации для конкретной таблицы
    """
    try:
        recommendations = await get_table_recommendations(table_name)
        return recommendations
        
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций для таблицы {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{table_name}", response_model=PerformanceHistory)
async def get_performance_history(table_name: str) -> PerformanceHistory:
    """
    Получение истории оптимизаций и текущих метрик производительности для таблицы
    """
    try:
        history = await get_table_history(table_name)
        return history
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории для таблицы {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-ddl")
async def validate_ddl_script(
    ddl_script: str = Query(..., description="DDL скрипт для валидации"),
    target_db_type: str = Query(..., description="Тип СУБД (clickhouse, postgres, hdfs)")
) -> JSONResponse:
    """
    Валидация DDL-скрипта перед применением
    Использует функции валидации из Модуля 4
    """
    try:
        # Импортируем функцию валидации из Модуля 4
        from ..warehouse_designer.main import _validate_ddl_script
        
        # Валидируем DDL
        validation_result = _validate_ddl_script(
            ddl_script=ddl_script,
            columns=[],  # Для простой валидации синтаксиса
            optimizations={}
        )
        
        return JSONResponse(content={
            "valid": validation_result.get("valid", False),
            "errors": validation_result.get("errors", []),
            "target_db_type": target_db_type,
            "ddl_script": ddl_script
        })
        
    except Exception as e:
        logger.error(f"Ошибка валидации DDL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/{source}")
async def get_current_metrics(source: str) -> JSONResponse:
    """
    Получение текущих метрик производительности источника данных
    Интеграция с Модулем 5 для автоопределения и сбора метрик
    """
    try:
        # Создаем запрос на анализ только для получения метрик
        request = PerformanceAnalysisRequest(source=source)
        
        # Выполняем анализ
        result = await analyze_performance_source(request)
        
        if result.status == AnalysisStatus.ERROR:
            raise HTTPException(
                status_code=400,
                detail=f"Ошибка получения метрик: {result.error_message}"
            )
        
        return JSONResponse(content={
            "source": source,
            "source_type": result.source_type.value,
            "metrics": result.current_metrics.dict() if result.current_metrics else None,
            "bottlenecks": result.bottlenecks,
            "analysis_id": result.analysis_id
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении метрик для {source}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-check")
async def health_check() -> JSONResponse:
    """
    Проверка работоспособности модуля оптимизации производительности
    """
    try:
        # Проверяем доступность Модуля 5
        import httpx
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "http://localhost:8000/api/v1/metrics/health-check",
                    timeout=5.0
                )
                module5_status = "ok" if response.status_code == 200 else "error"
            except:
                module5_status = "unavailable"
        
        # Проверяем доступность БД
        try:
            from ..database import get_db
            db = next(get_db())
            db.execute("SELECT 1")
            db_status = "ok"
            db.close()
        except:
            db_status = "error"
        
        return JSONResponse(content={
            "status": "ok",
            "module": "performance_optimizer",
            "version": "1.0.0",
            "integrations": {
                "module5_metrics": module5_status,
                "database": db_status
            },
            "capabilities": [
                "auto_detect_data_types",
                "performance_analysis", 
                "optimization_recommendations",
                "ddl_generation",
                "module4_integration",
                "module5_integration"
            ]
        })
        
    except Exception as e:
        logger.error(f"Ошибка health check: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )


# Дополнительные endpoints для интеграции

@router.get("/warehouses")
async def get_existing_warehouses() -> JSONResponse:
    """
    Получение списка существующих хранилищ из Модуля 4 для анализа
    """
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8000/api/v1/warehouse/instances",
                timeout=30.0
            )
            
            if response.status_code == 200:
                warehouses = response.json()
                return JSONResponse(content={
                    "warehouses": warehouses,
                    "count": len(warehouses),
                    "available_for_analysis": True
                })
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Ошибка получения списка хранилищ из Модуля 4"
                )
                
    except Exception as e:
        logger.error(f"Ошибка при получении списка хранилищ: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-analyze")
async def bulk_analyze_sources(
    sources: List[str],
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Массовый анализ производительности нескольких источников данных
    """
    try:
        analysis_ids = []
        
        for source in sources:
            request = PerformanceAnalysisRequest(source=source)
            
            # Запускаем анализ в фоне
            background_tasks.add_task(analyze_performance_source, request)
            
            # Генерируем ID для отслеживания
            import uuid
            analysis_id = f"bulk_{uuid.uuid4().hex[:8]}"
            analysis_ids.append({
                "source": source,
                "analysis_id": analysis_id
            })
        
        return JSONResponse(content={
            "message": f"Запущен массовый анализ {len(sources)} источников",
            "analyses": analysis_ids,
            "status": "processing"
        })
        
    except Exception as e:
        logger.error(f"Ошибка массового анализа: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
