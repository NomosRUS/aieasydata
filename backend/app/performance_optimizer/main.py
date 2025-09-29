"""
Основной модуль для Модуля 3 - Оптимизация производительности
Интеграция с модулями 4 и 5, управление анализом и применением оптимизаций
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import requests

# Импортируем новую систему управления данными
from ..config import DataPaths, file_manager
from ..shared.base_profiler import get_database_files, get_available_databases, process_file_with_size_control
from ..shared.schemas import OptimizationRecommendation as DBOptimizationRecommendation
from ..warehouse_designer.main import _validate_ddl_script
from ..database import get_db
from sqlalchemy.orm import Session

from .schemas import (
    PerformanceAnalysisRequest,
    PerformanceAnalysisResult,
    OptimizationRecommendation,
    OptimizationApplication,
    OptimizationResult,
    PerformanceHistory,
    Module4RecommendationSave,
    AnalysisStatus
)
from .analyzer import PerformanceAnalyzer
from .optimizer import OptimizationGenerator
from ..database import get_db
from ..shared.schemas import OptimizationRecommendation as DBOptimizationRecommendation
from ..warehouse_designer.main import _validate_ddl_script

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """
    Главный класс модуля оптимизации производительности
    Координирует работу анализатора и генератора оптимизаций
    """
    
    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        self.optimizer = OptimizationGenerator()
        self.analysis_cache: Dict[str, PerformanceAnalysisResult] = {}
    
    async def analyze_performance(
        self, 
        request: PerformanceAnalysisRequest
    ) -> PerformanceAnalysisResult:
        """
        Запуск полного анализа производительности источника данных
        
        Args:
            request: Запрос на анализ производительности
            
        Returns:
            PerformanceAnalysisResult: Результат анализа с рекомендациями
        """
        try:
            logger.info(f"Начинаем анализ производительности для: {request.source}")
            
            # Шаг 1: Анализ производительности через PerformanceAnalyzer
            analysis_result = await self.analyzer.analyze_source(
                source=request.source,
                source_type=request.source_type
            )
            
            if analysis_result.status == AnalysisStatus.ERROR:
                logger.error(f"Ошибка анализа: {analysis_result.error_message}")
                return analysis_result
            
            # Шаг 2: Генерация рекомендаций через OptimizationGenerator
            logger.info("Генерация рекомендаций по оптимизации")
            recommendations = self.optimizer.generate_recommendations(
                analysis_result=analysis_result,
                target_db_type=request.target_db_type
            )
            
            # Шаг 3: Валидация DDL-скриптов (интеграция с Модулем 4)
            validated_recommendations = []
            for rec in recommendations:
                validation_result = await self._validate_recommendation_ddl(rec, analysis_result)
                rec.validation_status = "valid" if validation_result else "invalid"
                validated_recommendations.append(rec)
            
            analysis_result.recommendations = validated_recommendations
            
            # Шаг 4: Сохранение в кэше
            self.analysis_cache[analysis_result.analysis_id] = analysis_result
            
            logger.info(f"Анализ завершен. Сгенерировано {len(recommendations)} рекомендаций")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Ошибка при анализе производительности: {str(e)}")
            return PerformanceAnalysisResult(
                analysis_id=str(uuid.uuid4()),
                source=request.source,
                source_type=request.source_type or "unknown",
                status=AnalysisStatus.ERROR,
                error_message=str(e)
            )
    
    async def analyze_existing_warehouse(self, design_id: str) -> PerformanceAnalysisResult:
        """
        Анализ производительности существующего хранилища из Модуля 4
        
        Args:
            design_id: ID дизайна хранилища из Модуля 4
            
        Returns:
            PerformanceAnalysisResult: Результат анализа
        """
        try:
            logger.info(f"Анализ существующего хранилища: {design_id}")
            
            # Используем специальный метод анализатора для хранилищ
            analysis_result = await self.analyzer.analyze_existing_warehouse(design_id)
            
            if analysis_result.status == AnalysisStatus.COMPLETED:
                # Генерируем дополнительные рекомендации для существующего хранилища
                recommendations = self.optimizer.generate_recommendations(analysis_result)
                
                # Валидируем рекомендации
                validated_recommendations = []
                for rec in recommendations:
                    validation_result = await self._validate_recommendation_ddl(rec, analysis_result)
                    rec.validation_status = "valid" if validation_result else "invalid"
                    validated_recommendations.append(rec)
                
                analysis_result.recommendations = validated_recommendations
            
            # Сохраняем в кэше
            self.analysis_cache[analysis_result.analysis_id] = analysis_result
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Ошибка при анализе хранилища {design_id}: {str(e)}")
            return PerformanceAnalysisResult(
                analysis_id=str(uuid.uuid4()),
                source=f"design_id:{design_id}",
                source_type="existing_warehouse",
                status=AnalysisStatus.ERROR,
                error_message=str(e)
            )
    
    async def apply_optimizations(
        self, 
        application: OptimizationApplication
    ) -> OptimizationResult:
        """
        Применение рекомендаций по оптимизации
        
        Args:
            application: Запрос на применение оптимизаций
            
        Returns:
            OptimizationResult: Результат применения оптимизаций
        """
        try:
            # Получаем результат анализа из кэша
            analysis_result = self.analysis_cache.get(application.analysis_id)
            if not analysis_result:
                raise ValueError(f"Анализ {application.analysis_id} не найден")
            
            logger.info(f"Применение оптимизаций для анализа: {application.analysis_id}")
            
            # Фильтруем рекомендации по ID
            recommendations_to_apply = [
                rec for rec in analysis_result.recommendations 
                if rec.recommendation_type.value in application.recommendation_ids
            ]
            
            if not recommendations_to_apply:
                raise ValueError("Не найдены рекомендации для применения")
            
            # Сохраняем рекомендации в БД для интеграции с Модулем 4
            applied_recommendations = []
            failed_recommendations = []
            
            for rec in recommendations_to_apply:
                try:
                    if application.dry_run:
                        # Тестовый режим - только валидация
                        logger.info(f"DRY RUN: {rec.recommendation_type.value} для {rec.target_table}")
                        applied_recommendations.append(rec.recommendation_type.value)
                    else:
                        # Реальное применение - сохранение в БД
                        await self._save_recommendation_to_module4(rec)
                        applied_recommendations.append(rec.recommendation_type.value)
                        logger.info(f"Применена рекомендация: {rec.recommendation_type.value}")
                        
                except Exception as e:
                    logger.error(f"Ошибка применения рекомендации {rec.recommendation_type.value}: {str(e)}")
                    failed_recommendations.append(rec.recommendation_type.value)
            
            # Создаем результат применения
            result = OptimizationResult(
                analysis_id=application.analysis_id,
                applied_recommendations=applied_recommendations,
                failed_recommendations=failed_recommendations,
                before_metrics=analysis_result.current_metrics,
                execution_details={
                    "dry_run": application.dry_run,
                    "total_recommendations": len(recommendations_to_apply),
                    "successful": len(applied_recommendations),
                    "failed": len(failed_recommendations)
                }
            )
            
            # Если не dry_run, измеряем улучшение производительности
            if not application.dry_run and applied_recommendations:
                # Здесь можно добавить повторный анализ для измерения улучшений
                pass
            
            logger.info(f"Применение завершено. Успешно: {len(applied_recommendations)}, Ошибок: {len(failed_recommendations)}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при применении оптимизаций: {str(e)}")
            return OptimizationResult(
                analysis_id=application.analysis_id,
                failed_recommendations=application.recommendation_ids,
                execution_details={"error": str(e)}
            )
    
    async def get_analysis_result(self, analysis_id: str) -> Optional[PerformanceAnalysisResult]:
        """
        Получение результата анализа по ID
        """
        return self.analysis_cache.get(analysis_id)
    
    async def get_recommendations_for_table(self, table_name: str) -> List[OptimizationRecommendation]:
        """
        Получение рекомендаций для конкретной таблицы
        """
        recommendations = []
        
        for analysis in self.analysis_cache.values():
            for rec in analysis.recommendations:
                if rec.target_table == table_name:
                    recommendations.append(rec)
        
        return recommendations
    
    async def get_performance_history(self, table_name: str) -> PerformanceHistory:
        """
        Получение истории оптимизаций для таблицы
        """
        # Здесь можно добавить логику получения истории из БД
        optimizations = []
        current_performance = None
        
        # Ищем текущие метрики в кэше
        for analysis in self.analysis_cache.values():
            if analysis.current_metrics and table_name in analysis.source:
                current_performance = analysis.current_metrics
                break
        
        return PerformanceHistory(
            table_name=table_name,
            optimizations=optimizations,
            current_performance=current_performance,
            total_improvements=0.0
        )
    
    async def _validate_recommendation_ddl(
        self, 
        recommendation: OptimizationRecommendation, 
        analysis_result: PerformanceAnalysisResult
    ) -> bool:
        """
        Валидация DDL-скрипта рекомендации (интеграция с Модулем 4)
        """
        try:
            # Получаем информацию о колонках из анализа
            columns = []
            if analysis_result.current_metrics and analysis_result.current_metrics.structure_info:
                structure = analysis_result.current_metrics.structure_info
                if "columns" in structure:
                    columns = structure["columns"]
            
            # Используем функцию валидации из Модуля 4
            validation_result = _validate_ddl_script(
                ddl_script=recommendation.ddl_script,
                columns=columns,
                optimizations=recommendation.recommendation_details
            )
            
            return validation_result.get("valid", False)
            
        except Exception as e:
            logger.error(f"Ошибка валидации DDL: {str(e)}")
            return False
    
    async def _save_recommendation_to_module4(self, recommendation: OptimizationRecommendation):
        """
        Сохранение рекомендации в БД для интеграции с Модулем 4
        """
        try:
            # Получаем сессию БД
            db = next(get_db())
            
            # Создаем запись в таблице optimization_recommendations
            db_recommendation = DBOptimizationRecommendation(
                table_name=recommendation.target_table,
                recommendation_type=recommendation.recommendation_type.value,
                recommendation_details=recommendation.recommendation_details,
                estimated_improvement=recommendation.estimated_improvement,
                reasoning=recommendation.reasoning,
                created_at=datetime.utcnow()
            )
            
            # Проверяем, есть ли уже такая рекомендация
            existing = db.query(DBOptimizationRecommendation).filter(
                DBOptimizationRecommendation.table_name == recommendation.target_table,
                DBOptimizationRecommendation.recommendation_type == recommendation.recommendation_type.value
            ).first()
            
            if existing:
                # Обновляем существующую
                existing.recommendation_details = recommendation.recommendation_details
                existing.estimated_improvement = recommendation.estimated_improvement
                existing.reasoning = recommendation.reasoning
                logger.info(f"Обновлена рекомендация {recommendation.recommendation_type.value} для {recommendation.target_table}")
            else:
                # Создаем новую
                db.add(db_recommendation)
                logger.info(f"Создана рекомендация {recommendation.recommendation_type.value} для {recommendation.target_table}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения рекомендации в БД: {str(e)}")
            db.rollback()
            raise
        finally:
            db.close()


# Глобальный экземпляр оптимизатора
performance_optimizer = PerformanceOptimizer()


async def analyze_performance_source(request: PerformanceAnalysisRequest) -> PerformanceAnalysisResult:
    """
    Функция-обертка для анализа производительности источника данных
    """
    return await performance_optimizer.analyze_performance(request)


async def analyze_warehouse_performance(design_id: str) -> PerformanceAnalysisResult:
    """
    Функция-обертка для анализа производительности хранилища
    """
    return await performance_optimizer.analyze_existing_warehouse(design_id)


async def apply_performance_optimizations(application: OptimizationApplication) -> OptimizationResult:
    """
    Функция-обертка для применения оптимизаций
    """
    return await performance_optimizer.apply_optimizations(application)


async def get_analysis_by_id(analysis_id: str) -> Optional[PerformanceAnalysisResult]:
    """
    Получение результата анализа по ID
    """
    return await performance_optimizer.get_analysis_result(analysis_id)


async def get_table_recommendations(table_name: str) -> List[OptimizationRecommendation]:
    """
    Получение рекомендаций для таблицы
    """
    return await performance_optimizer.get_recommendations_for_table(table_name)


async def get_table_history(table_name: str) -> PerformanceHistory:
    """
    Получение истории оптимизаций таблицы
    """
    return await performance_optimizer.get_performance_history(table_name)

async def analyze_database_performance(database_name: str, stage: str = None) -> Dict[str, Any]:
    """
    Анализ производительности данных в организованной системе.
    
    Args:
        database_name: Имя базы данных
        stage: Этап обработки (validated, cleaned, aggregated, optimized)
    
    Returns:
        Результат анализа производительности
    """
    try:
        # Получаем файлы из организованной структуры
        files = get_database_files(database_name, stage)
        
        if not files:
            return {
                "database_name": database_name,
                "stage": stage,
                "status": "no_data",
                "message": "No files found for analysis"
            }
        
        analysis_results = []
        total_recommendations = 0
        
        for file_path in files[:5]:  # Анализируем первые 5 файлов
            try:
                # Создаем запрос на анализ
                analysis_request = PerformanceAnalysisRequest(
                    source=file_path,
                    analysis_type="file_performance",
                    target_database="auto_detect"
                )
                
                # Выполняем анализ
                result = await performance_optimizer.analyze_performance(analysis_request)
                
                if result.status == "completed":
                    analysis_results.append({
                        "file": str(Path(file_path).name),
                        "recommendations_count": len(result.recommendations),
                        "performance_score": result.performance_metrics.get("overall_score", 0),
                        "recommendations": [r.dict() for r in result.recommendations[:3]]  # Первые 3
                    })
                    total_recommendations += len(result.recommendations)
                
            except Exception as e:
                analysis_results.append({
                    "file": str(Path(file_path).name),
                    "error": str(e)
                })
        
        return {
            "database_name": database_name,
            "stage": stage or "all_stages",
            "status": "completed",
            "files_analyzed": len(analysis_results),
            "total_recommendations": total_recommendations,
            "analysis_results": analysis_results
        }
        
    except Exception as e:
        return {
            "database_name": database_name,
            "stage": stage,
            "status": "error",
            "error": str(e)
        }

def optimize_database_organization(database_name: str) -> Dict[str, Any]:
    """
    Оптимизация организации данных для конкретной базы данных.
    
    Args:
        database_name: Имя базы данных
    
    Returns:
        Результат оптимизации организации
    """
    try:
        optimization_results = {
            "database_name": database_name,
            "timestamp": datetime.now().isoformat(),
            "optimizations_applied": [],
            "recommendations": []
        }
        
        # Анализируем все этапы обработки
        stages = ["validated", "cleaned", "aggregated", "optimized"]
        
        for stage in stages:
            try:
                files = get_database_files(database_name, stage)
                
                if not files:
                    continue
                
                stage_optimization = {
                    "stage": stage,
                    "files_count": len(files),
                    "optimizations": []
                }
                
                # Проверяем размеры файлов
                large_files = []
                for file_path in files:
                    try:
                        file_size = Path(file_path).stat().st_size
                        if file_size > DataPaths.MAX_FILE_SIZE_MB * 1024 * 1024:
                            large_files.append({
                                "file": str(Path(file_path).name),
                                "size_mb": round(file_size / (1024 * 1024), 2)
                            })
                    except:
                        continue
                
                if large_files:
                    stage_optimization["optimizations"].append({
                        "type": "file_splitting",
                        "description": f"Found {len(large_files)} files exceeding size limit",
                        "large_files": large_files,
                        "recommendation": "Split large files using file_manager"
                    })
                
                # Рекомендации по формату файлов
                non_parquet_files = [f for f in files if not f.endswith('.parquet')]
                if non_parquet_files:
                    stage_optimization["optimizations"].append({
                        "type": "format_optimization",
                        "description": f"Found {len(non_parquet_files)} non-Parquet files",
                        "recommendation": "Convert to Parquet format for better performance"
                    })
                
                if stage_optimization["optimizations"]:
                    optimization_results["optimizations_applied"].append(stage_optimization)
                
            except Exception as e:
                optimization_results["recommendations"].append({
                    "stage": stage,
                    "error": str(e),
                    "recommendation": "Check stage directory structure"
                })
        
        # Общие рекомендации
        databases = get_available_databases()
        if len(databases) > 10:
            optimization_results["recommendations"].append({
                "type": "database_consolidation",
                "description": f"Found {len(databases)} databases",
                "recommendation": "Consider consolidating similar databases"
            })
        
        optimization_results["status"] = "completed"
        optimization_results["total_optimizations"] = len(optimization_results["optimizations_applied"])
        
        return optimization_results
        
    except Exception as e:
        return {
            "database_name": database_name,
            "status": "error",
            "error": str(e)
        }

def get_cross_database_optimization_opportunities() -> Dict[str, Any]:
    """
    Поиск возможностей оптимизации между базами данных.
    
    Returns:
        Возможности кросс-базовой оптимизации
    """
    try:
        databases = get_available_databases()
        
        opportunities = {
            "timestamp": datetime.now().isoformat(),
            "total_databases": len(databases),
            "opportunities": []
        }
        
        # Анализ дублирования данных
        database_stats = {}
        for db_name in databases:
            try:
                files = get_database_files(db_name)
                total_size = 0
                file_count = 0
                
                for file_path in files:
                    try:
                        total_size += Path(file_path).stat().st_size
                        file_count += 1
                    except:
                        continue
                
                database_stats[db_name] = {
                    "files": file_count,
                    "size_mb": round(total_size / (1024 * 1024), 2)
                }
                
            except Exception as e:
                database_stats[db_name] = {"error": str(e)}
        
        # Поиск возможностей консолидации
        small_databases = [db for db, stats in database_stats.items() 
                          if isinstance(stats, dict) and stats.get("size_mb", 0) < 100]
        
        if len(small_databases) > 3:
            opportunities["opportunities"].append({
                "type": "database_consolidation",
                "description": f"Found {len(small_databases)} small databases (<100MB)",
                "databases": small_databases,
                "recommendation": "Consider consolidating small databases",
                "potential_savings": "Reduced metadata overhead and improved management"
            })
        
        # Поиск больших баз данных для разделения
        large_databases = [db for db, stats in database_stats.items() 
                          if isinstance(stats, dict) and stats.get("size_mb", 0) > 5000]
        
        if large_databases:
            opportunities["opportunities"].append({
                "type": "database_partitioning",
                "description": f"Found {len(large_databases)} large databases (>5GB)",
                "databases": large_databases,
                "recommendation": "Consider partitioning large databases by time or category",
                "potential_benefits": "Improved query performance and parallel processing"
            })
        
        opportunities["database_stats"] = database_stats
        opportunities["total_opportunities"] = len(opportunities["opportunities"])
        
        return opportunities
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
