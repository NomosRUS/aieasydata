"""
Основной модуль агрегации и обогащения данных.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .schemas import (
    AggregationScenarioRequest,
    AggregationScenarioResponse,
    CustomDatasetRequest,
    ExecutionResult,
    PreviewJoinRequest,
    PreviewJoinResponse,
    HealthCheckResponse,
    SourceAnalysis,
    OptimizationRecommendation
)
from .data_source_collector import DataSourceCollector
from .custom_dataset_builder import CustomDatasetBuilder
from .aggregation_engine import AggregationEngine
from .optimization_generator import OptimizationGenerator
from ..shared.schemas import AggregationScenario, OptimizationRecommendation as DBOptimizationRecommendation
from ..database import get_db

logger = logging.getLogger(__name__)


class DataAggregator:
    """Основной класс модуля агрегации и обогащения данных."""
    
    def __init__(self):
        self.data_collector = DataSourceCollector()
        self.dataset_builder = CustomDatasetBuilder()
        self.aggregation_engine = AggregationEngine()
        self.optimization_generator = OptimizationGenerator()
        
        # Кэш для хранения результатов выполнения
        self.execution_cache: Dict[str, ExecutionResult] = {}
        
        # Статистика модуля
        self.stats = {
            "scenarios_created": 0,
            "executions_completed": 0,
            "last_execution": None,
            "active_scenarios": 0
        }
    
    async def create_scenario(self, request: AggregationScenarioRequest, db: Session) -> AggregationScenarioResponse:
        """
        Создает новый сценарий агрегации данных.
        
        Args:
            request: Запрос на создание сценария
            db: Сессия базы данных
            
        Returns:
            AggregationScenarioResponse: Информация о созданном сценарии
        """
        try:
            logger.info(f"Creating aggregation scenario: {request.name}")
            
            # Генерируем уникальный ID сценария
            scenario_id = str(uuid.uuid4())
            
            # Анализируем все источники данных
            sources_analysis = []
            validation_errors = []
            
            for source in request.sources:
                try:
                    analysis = await self.data_collector.analyze_source(source)
                    sources_analysis.append(analysis)
                    
                    # Собираем ошибки валидации
                    if analysis.compatibility_issues:
                        validation_errors.extend(analysis.compatibility_issues)
                        
                except Exception as e:
                    error_msg = f"Failed to analyze source {source.source_id}: {str(e)}"
                    validation_errors.append(error_msg)
                    logger.error(error_msg)
            
            # Проверяем совместимость источников
            compatibility_issues = self.data_collector.validate_source_compatibility(request.sources)
            validation_errors.extend(compatibility_issues)
            
            # Определяем статус сценария
            if validation_errors:
                status = "error"
                logger.warning(f"Scenario {request.name} has validation errors: {validation_errors}")
            else:
                status = "validated"
            
            # Оцениваем размер результата и рекомендуемую СУБД
            estimated_size, recommended_engine = self._estimate_output_characteristics(
                sources_analysis, request.aggregations, request.target_requirements
            )
            
            # Сохраняем сценарий в базу данных
            db_scenario = AggregationScenario(
                scenario_name=request.name,
                description=request.description,
                sources=self._serialize_sources(request.sources),
                aggregations=self._serialize_aggregations(request.aggregations),
                enrichments=self._serialize_enrichments(request.enrichments),
                target_requirements=request.target_requirements.dict(),
                status=status
            )
            
            db.add(db_scenario)
            db.commit()
            db.refresh(db_scenario)
            
            # Обновляем статистику
            self.stats["scenarios_created"] += 1
            self.stats["active_scenarios"] += 1
            
            logger.info(f"Scenario {request.name} created successfully with ID: {scenario_id}")
            
            return AggregationScenarioResponse(
                scenario_id=str(db_scenario.id),
                name=request.name,
                description=request.description,
                status=status,
                sources_analysis=sources_analysis,
                estimated_output_size=estimated_size,
                recommended_engine=recommended_engine,
                validation_errors=validation_errors
            )
            
        except Exception as e:
            logger.error(f"Error creating scenario: {str(e)}")
            raise
    
    async def execute_scenario(self, scenario_id: str, db: Session) -> ExecutionResult:
        """
        Выполняет сценарий агрегации данных.
        
        Args:
            scenario_id: ID сценария
            db: Сессия базы данных
            
        Returns:
            ExecutionResult: Результат выполнения
        """
        try:
            logger.info(f"Executing scenario: {scenario_id}")
            
            # Получаем сценарий из базы данных
            db_scenario = db.query(AggregationScenario).filter(
                AggregationScenario.id == int(scenario_id)
            ).first()
            
            if not db_scenario:
                raise ValueError(f"Scenario {scenario_id} not found")
            
            # Генерируем ID выполнения
            execution_id = str(uuid.uuid4())
            
            # Создаем результат выполнения
            execution_result = ExecutionResult(
                execution_id=execution_id,
                scenario_id=scenario_id,
                status="running"
            )
            
            # Сохраняем в кэш
            self.execution_cache[execution_id] = execution_result
            
            try:
                # Десериализуем данные сценария
                sources = self._deserialize_sources(db_scenario.sources)
                aggregations = self._deserialize_aggregations(db_scenario.aggregations)
                enrichments = self._deserialize_enrichments(db_scenario.enrichments)
                target_requirements = db_scenario.target_requirements
                
                # Выполняем агрегацию
                aggregation_result = await self.aggregation_engine.execute_aggregation_scenario(
                    sources, aggregations, enrichments
                )
                
                if not aggregation_result["success"]:
                    raise Exception(aggregation_result["error"])
                
                result_df = aggregation_result["result_dataframe"]
                execution_stats = aggregation_result["execution_stats"]
                
                # Сохраняем результат
                output_path = await self._save_aggregation_result(
                    result_df, db_scenario.scenario_name, target_requirements
                )
                
                # Генерируем DDL для целевой таблицы
                target_table_ddl = await self._generate_target_ddl(
                    result_df, db_scenario.scenario_name, target_requirements
                )
                
                # Генерируем рекомендации по оптимизации
                optimization_recommendations = self.optimization_generator.generate_optimizations(
                    result_df, aggregations, sources, target_requirements, db_scenario.scenario_name
                )
                
                # Сохраняем рекомендации в базу данных для модуля 3
                await self._save_optimization_recommendations(
                    optimization_recommendations, db_scenario.scenario_name, db
                )
                
                # Обновляем результат выполнения
                execution_result.status = "completed"
                execution_result.output_path = output_path
                execution_result.target_table_ddl = target_table_ddl
                execution_result.optimization_recommendations = optimization_recommendations
                execution_result.execution_stats = execution_stats
                execution_result.completed_at = datetime.utcnow()
                
                # Обновляем сценарий в базе данных
                db_scenario.status = "completed"
                db_scenario.last_executed = datetime.utcnow()
                db_scenario.execution_stats = execution_stats.dict()
                flag_modified(db_scenario, 'execution_stats')
                db.commit()
                
                # Обновляем статистику
                self.stats["executions_completed"] += 1
                self.stats["last_execution"] = datetime.utcnow()
                
                # Уведомляем модуль 4 о готовности данных
                await self._notify_module4_data_ready(db_scenario.scenario_name, output_path)
                
                logger.info(f"Scenario {scenario_id} executed successfully")
                
            except Exception as e:
                # Обновляем результат с ошибкой
                execution_result.status = "failed"
                execution_result.error_message = str(e)
                execution_result.completed_at = datetime.utcnow()
                
                # Обновляем сценарий в базе данных
                db_scenario.status = "error"
                db.commit()
                
                logger.error(f"Scenario {scenario_id} execution failed: {str(e)}")
            
            # Обновляем кэш
            self.execution_cache[execution_id] = execution_result
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error executing scenario {scenario_id}: {str(e)}")
            raise
    
    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionResult]:
        """
        Получает статус выполнения по ID.
        
        Args:
            execution_id: ID выполнения
            
        Returns:
            Optional[ExecutionResult]: Результат выполнения или None
        """
        return self.execution_cache.get(execution_id)
    
    async def create_custom_dataset(self, request: CustomDatasetRequest) -> Dict[str, Any]:
        """
        Создает кастомный набор данных.
        
        Args:
            request: Запрос на создание кастомного набора данных
            
        Returns:
            Dict: Результат создания набора данных
        """
        try:
            logger.info(f"Creating custom dataset: {request.dataset_name}")
            
            result = await self.dataset_builder.create_custom_dataset(request)
            
            if result["success"]:
                logger.info(f"Custom dataset {request.dataset_name} created successfully")
            else:
                logger.error(f"Failed to create custom dataset {request.dataset_name}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating custom dataset: {str(e)}")
            return {
                "success": False,
                "error": "Dataset creation failed",
                "details": str(e)
            }
    
    async def preview_join(self, request: PreviewJoinRequest) -> PreviewJoinResponse:
        """
        Предварительный просмотр JOIN операции.
        
        Args:
            request: Запрос на предварительный просмотр
            
        Returns:
            PreviewJoinResponse: Результат предварительного просмотра
        """
        try:
            return await self.dataset_builder.preview_join(request)
        except Exception as e:
            logger.error(f"Error in join preview: {str(e)}")
            return PreviewJoinResponse(
                preview_data=[],
                total_estimated_rows=0,
                join_statistics={"error": str(e)},
                warnings=[f"Preview failed: {str(e)}"]
            )
    
    async def get_available_columns(self, source_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Получает доступные колонки из источника данных.
        
        Args:
            source_dict: Словарь с конфигурацией источника
            
        Returns:
            List[Dict]: Список доступных колонок
        """
        try:
            # Преобразуем словарь в объект DataSource
            from .schemas import DataSource
            source = DataSource(**source_dict)
            
            columns = await self.dataset_builder.get_available_columns(source)
            
            return [
                {
                    "name": col.name,
                    "type": col.type,
                    "nullable": col.nullable,
                    "description": col.description
                }
                for col in columns
            ]
            
        except Exception as e:
            logger.error(f"Error getting available columns: {str(e)}")
            return []
    
    async def validate_scenario(self, request: AggregationScenarioRequest) -> Dict[str, Any]:
        """
        Валидирует сценарий агрегации без создания.
        
        Args:
            request: Запрос на создание сценария
            
        Returns:
            Dict: Результат валидации
        """
        try:
            validation_errors = []
            warnings = []
            
            # Проверяем источники данных
            for source in request.sources:
                try:
                    analysis = await self.data_collector.analyze_source(source)
                    if analysis.compatibility_issues:
                        validation_errors.extend(analysis.compatibility_issues)
                except Exception as e:
                    validation_errors.append(f"Source {source.source_id}: {str(e)}")
            
            # Проверяем совместимость источников
            compatibility_issues = self.data_collector.validate_source_compatibility(request.sources)
            validation_errors.extend(compatibility_issues)
            
            # Проверяем агрегации
            for i, aggregation in enumerate(request.aggregations):
                try:
                    # Базовая валидация структуры агрегации
                    if not aggregation.parameters:
                        validation_errors.append(f"Aggregation {i+1}: Missing parameters")
                except Exception as e:
                    validation_errors.append(f"Aggregation {i+1}: {str(e)}")
            
            # Генерируем предупреждения
            if len(request.sources) > 5:
                warnings.append("Large number of sources may impact performance")
            
            if len(request.aggregations) > 10:
                warnings.append("Complex aggregation scenario may require optimization")
            
            return {
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": warnings,
                "sources_count": len(request.sources),
                "aggregations_count": len(request.aggregations)
            }
            
        except Exception as e:
            logger.error(f"Error validating scenario: {str(e)}")
            return {
                "valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": [],
                "sources_count": 0,
                "aggregations_count": 0
            }
    
    async def get_health_status(self) -> HealthCheckResponse:
        """
        Получает статус работоспособности модуля.
        
        Returns:
            HealthCheckResponse: Статус работоспособности
        """
        try:
            # Проверяем интеграции с другими модулями
            integrations = {
                "module_5_metrics": await self._check_module5_integration(),
                "module_4_warehouse": await self._check_module4_integration(),
                "database": await self._check_database_connection()
            }
            
            # Определяем общий статус - если модули 4 и 5 работают, считаем healthy
            if integrations.get("module_5_metrics", False) and integrations.get("module_4_warehouse", False):
                status = "healthy"  # Основная функциональность работает
            elif any(integrations.values()):
                status = "degraded"
            else:
                status = "unhealthy"
            
            return HealthCheckResponse(
                status=status,
                version="1.0.0",
                integrations=integrations,
                active_scenarios=self.stats["active_scenarios"],
                last_execution=self.stats["last_execution"]
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return HealthCheckResponse(
                status="unhealthy",
                version="1.0.0",
                integrations={},
                active_scenarios=0,
                error_details=str(e)
            )
    
    # Вспомогательные методы
    
    def _serialize_sources(self, sources) -> List[Dict[str, Any]]:
        """Сериализует источники данных для сохранения в БД."""
        return [source.dict() for source in sources]
    
    def _serialize_aggregations(self, aggregations) -> List[Dict[str, Any]]:
        """Сериализует агрегации для сохранения в БД."""
        result = []
        for agg in aggregations:
            agg_dict = {
                "type": agg.type.value,
                "parameters": agg.parameters.dict()
            }
            result.append(agg_dict)
        return result
    
    def _serialize_enrichments(self, enrichments) -> List[Dict[str, Any]]:
        """Сериализует обогащения для сохранения в БД."""
        return [enrich.dict() for enrich in enrichments]
    
    def _deserialize_sources(self, sources_data) -> List:
        """Десериализует источники данных из БД."""
        from .schemas import DataSource
        return [DataSource(**source_dict) for source_dict in sources_data]
    
    def _deserialize_aggregations(self, aggregations_data) -> List:
        """Десериализует агрегации из БД."""
        from .schemas import AggregationRule, AggregationType, JoinRule, GroupByRule, WindowRule, UnionRule
        
        result = []
        for agg_dict in aggregations_data:
            agg_type = AggregationType(agg_dict["type"])
            
            # Определяем тип параметров по типу агрегации
            if agg_type == AggregationType.JOIN:
                parameters = JoinRule(**agg_dict["parameters"])
            elif agg_type == AggregationType.GROUP_BY:
                parameters = GroupByRule(**agg_dict["parameters"])
            elif agg_type == AggregationType.WINDOW:
                parameters = WindowRule(**agg_dict["parameters"])
            elif agg_type == AggregationType.UNION:
                parameters = UnionRule(**agg_dict["parameters"])
            else:
                continue
            
            result.append(AggregationRule(type=agg_type, parameters=parameters))
        
        return result
    
    def _deserialize_enrichments(self, enrichments_data) -> List:
        """Десериализует обогащения из БД."""
        from .schemas import EnrichmentRule
        return [EnrichmentRule(**enrich_dict) for enrich_dict in enrichments_data]
    
    def _estimate_output_characteristics(self, sources_analysis, aggregations, target_requirements) -> tuple:
        """Оценивает характеристики выходных данных."""
        # Простая оценка размера
        total_rows = sum(analysis.row_count or 0 for analysis in sources_analysis)
        
        # Учитываем влияние агрегаций
        for aggregation in aggregations:
            if aggregation.type.value == "group_by":
                total_rows = int(total_rows * 0.1)  # GROUP BY обычно уменьшает количество строк
            elif aggregation.type.value == "join":
                total_rows = int(total_rows * 1.2)  # JOIN может увеличить количество строк
        
        estimated_size = max(total_rows, 1000)
        
        # Рекомендуемая СУБД
        if target_requirements.target_db_type:
            recommended_engine = target_requirements.target_db_type
        elif estimated_size > 1000000:
            recommended_engine = "clickhouse"  # Для больших данных
        elif any(agg.type.value == "join" for agg in aggregations):
            recommended_engine = "postgres"  # Для сложных JOIN
        else:
            recommended_engine = "postgres"  # По умолчанию
        
        return estimated_size, recommended_engine
    
    async def _save_aggregation_result(self, df, scenario_name, target_requirements) -> str:
        """Сохраняет результат агрегации."""
        output_dir = Path("data_landing_zone/aggregated") / scenario_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"{scenario_name}.parquet"
        df.to_parquet(output_path, index=False)
        
        return str(output_path)
    
    async def _generate_target_ddl(self, df, table_name, target_requirements) -> str:
        """Генерирует DDL для целевой таблицы."""
        # Простая генерация DDL
        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            if 'int' in dtype:
                sql_type = 'INTEGER'
            elif 'float' in dtype:
                sql_type = 'FLOAT'
            elif 'datetime' in dtype:
                sql_type = 'TIMESTAMP'
            else:
                sql_type = 'TEXT'
            
            columns.append(f"    {col} {sql_type}")
        
        ddl = f"""CREATE TABLE {table_name} (
{chr(10).join(columns)}
);"""
        
        return ddl
    
    async def _save_optimization_recommendations(self, recommendations, table_name, db: Session):
        """Сохраняет рекомендации по оптимизации в БД для модуля 3."""
        try:
            for rec in recommendations:
                db_rec = DBOptimizationRecommendation(
                    table_name=table_name,
                    recommendation_type=rec.type,
                    recommendation_details={
                        "target": rec.target,
                        "reasoning": rec.reasoning,
                        "priority": rec.priority,
                        "estimated_improvement": rec.estimated_improvement
                    }
                )
                db.merge(db_rec)  # Используем merge для избежания дубликатов
            
            db.commit()
            logger.info(f"Saved {len(recommendations)} optimization recommendations for {table_name}")
            
        except Exception as e:
            logger.error(f"Error saving optimization recommendations: {str(e)}")
            db.rollback()
    
    async def _notify_module4_data_ready(self, scenario_name: str, output_path: str):
        """Уведомляет модуль 4 о готовности данных."""
        try:
            import aiohttp
            
            notification_data = {
                "scenario_name": scenario_name,
                "output_path": output_path,
                "data_ready": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/api/v1/warehouse/notify-data-ready",
                    json=notification_data
                ) as response:
                    if response.status == 200:
                        logger.info(f"Successfully notified Module 4 about {scenario_name}")
                    else:
                        logger.warning(f"Failed to notify Module 4: {response.status}")
                        
        except Exception as e:
            logger.warning(f"Failed to notify Module 4: {str(e)}")
    
    async def _check_module5_integration(self) -> bool:
        """Проверяет интеграцию с модулем 5."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/api/v1/metrics/health-check") as response:
                    return response.status == 200
        except:
            return False
    
    async def _check_module4_integration(self) -> bool:
        """Проверяет интеграцию с модулем 4."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/api/v1/warehouse/instances") as response:
                    return response.status == 200
        except:
            return False
    
    async def _check_database_connection(self) -> bool:
        """Проверяет подключение к базе данных."""
        try:
            db = next(get_db())
            db.execute("SELECT 1")
            return True
        except:
            return False
