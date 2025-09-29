"""
API роутер для модуля валидации данных.

Содержит все API endpoints для валидации, очистки данных,
проверки однородности и получения рекомендаций по хранению.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from .main import DataValidator
from .schemas import (
    DataSource, ValidationResult, ValidationRequest, CleaningRequest,
    ValidationResponse, CleaningResponse, HomogeneityCheckRequest,
    HomogeneityResult, HealthCheckResponse, ValidationStatus
)
from ..config import DataPaths
from ..shared.base_profiler import get_available_databases

logger = logging.getLogger(__name__)

# Создаем роутер
router = APIRouter(prefix="/api/v1/data-quality", tags=["data-quality"])

# Глобальный экземпляр валидатора
data_validator = DataValidator()


@router.get("/health-check", response_model=HealthCheckResponse)
async def health_check():
    """Проверка работоспособности модуля валидации данных."""
    try:
        # Получаем базовый статус без проверки интеграций (быстро)
        status = data_validator.get_basic_health_status()
        
        return HealthCheckResponse(
            status=status["status"],
            version=status["version"],
            integrations=status["integrations"],
            last_check=status["last_check"]
        )
        
    except Exception as e:
        logger.error(f"Ошибка при проверке здоровья модуля: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка проверки здоровья: {str(e)}")


@router.get("/full-diagnostics")
async def full_diagnostics():
    """Полная диагностика модуля с проверкой всех интеграций (может быть медленной)."""
    try:
        # Используем полную проверку здоровья с интеграциями
        status = data_validator.get_health_status()
        
        return {
            "status": status["status"],
            "version": status["version"],
            "integrations": status["integrations"],
            "last_check": status["last_check"],
            "diagnostic_type": "full"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при полной диагностике: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка диагностики: {str(e)}")


@router.get("/sources")
async def get_available_sources():
    """Получение списка доступных источников данных для валидации."""
    try:
        sources = data_validator.get_available_sources()
        
        return {
            "sources": sources,
            "total_count": len(sources),
            "scanned_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении источников данных: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения источников: {str(e)}")


@router.post("/validate/{profile_id}", response_model=ValidationResponse)
async def validate_data_source(
    profile_id: str,
    validation_request: ValidationRequest,
    background_tasks: BackgroundTasks
):
    """
    Валидация данных по профилю.
    
    Args:
        profile_id: Идентификатор профиля данных
        validation_request: Параметры валидации
        background_tasks: Фоновые задачи
    """
    try:
        # Создаем источник данных на основе profile_id
        # В реальной реализации здесь был бы запрос к базе данных
        source = DataSource(
            source_id=profile_id,
            source_type="file",  # Определяется автоматически
            path=f"data_landing_zone/raw/{profile_id}"  # Примерный путь
        )
        
        # Выполняем валидацию
        validation_result = data_validator.validate_data_source(source, validation_request)
        
        if validation_result.status == ValidationStatus.FAILED:
            raise HTTPException(
                status_code=400, 
                detail=validation_result.error_message or "Валидация не удалась"
            )
        
        # Определяем рекомендуемое хранилище
        db_recommendation = next(
            (rec for rec in validation_result.recommendations 
             if rec.recommendation_type == "database_choice"),
            None
        )
        
        recommended_storage = db_recommendation.recommended_value if db_recommendation else "postgresql"
        
        return ValidationResponse(
            validation_id=validation_result.validation_id,
            quality_score=validation_result.quality_score,
            issues=validation_result.issues,
            recommended_storage=recommended_storage,
            storage_recommendations=validation_result.recommendations
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при валидации профиля {profile_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка валидации: {str(e)}")


@router.post("/clean/{profile_id}", response_model=CleaningResponse)
async def clean_data_source(
    profile_id: str,
    cleaning_request: CleaningRequest,
    background_tasks: BackgroundTasks
):
    """
    Очистка данных по профилю.
    
    Args:
        profile_id: Идентификатор профиля данных
        cleaning_request: Параметры очистки
        background_tasks: Фоновые задачи
    """
    try:
        # Создаем источник данных
        source = DataSource(
            source_id=profile_id,
            source_type="file",
            path=f"data_landing_zone/raw/{profile_id}"
        )
        
        # Получаем результат предварительной валидации (если есть)
        validation_result = None
        # В реальной реализации здесь был бы поиск в кэше или БД
        
        # Выполняем очистку
        cleaning_result = data_validator.clean_data_source(
            source, cleaning_request, validation_result
        )
        
        return CleaningResponse(
            cleaned_file_path=cleaning_result["cleaned_file_path"],
            metadata=cleaning_result["metadata"],
            storage_recommendations=cleaning_result["storage_recommendations"]
        )
        
    except Exception as e:
        logger.error(f"Ошибка при очистке профиля {profile_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка очистки: {str(e)}")


@router.post("/clean-file")
async def clean_file_direct(
    file_path: str,
    cleaning_request: CleaningRequest,
    background_tasks: BackgroundTasks
):
    """
    Прямая очистка файла по указанному пути.
    
    Args:
        file_path: Путь к файлу для очистки
        cleaning_request: Параметры очистки
        background_tasks: Фоновые задачи
    """
    try:
        # Создаем источник данных из пути
        source = DataSource(
            source_id=f"direct_{hash(file_path)}",
            source_type="file",
            path=file_path
        )
        
        # Выполняем очистку
        cleaning_result = data_validator.clean_data_source(
            source, cleaning_request, None
        )
        
        return {
            "status": "success",
            "cleaned_file_path": cleaning_result["cleaned_file_path"],
            "metadata": cleaning_result["metadata"],
            "quality_improvement": cleaning_result.get("quality_improvement", 0.0),
            "applied_fixes": cleaning_result.get("applied_fixes", [])
        }
        
    except Exception as e:
        logger.error(f"Ошибка при прямой очистке файла {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка очистки файла: {str(e)}")


@router.post("/check-homogeneity", response_model=HomogeneityResult)
async def check_folder_homogeneity(request: HomogeneityCheckRequest):
    """
    Проверка однородности файлов в папке.
    
    Args:
        request: Запрос на проверку однородности
    """
    try:
        result = data_validator.check_folder_homogeneity(request)
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при проверке однородности папки {request.folder_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка проверки однородности: {str(e)}")


@router.get("/validation/{validation_id}")
async def get_validation_result(validation_id: str):
    """
    Получение результата валидации по ID.
    
    Args:
        validation_id: Идентификатор валидации
    """
    try:
        result = data_validator.get_validation_result(validation_id)
        
        if result is None:
            raise HTTPException(status_code=404, detail="Результат валидации не найден")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении результата валидации {validation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения результата: {str(e)}")


@router.post("/validate-file")
async def validate_file_direct(
    file_path: str,
    validation_options: Optional[Dict[str, Any]] = None
):
    """
    Прямая валидация файла по пути.
    
    Args:
        file_path: Путь к файлу
        validation_options: Опции валидации
    """
    try:
        # Создаем источник данных
        source = DataSource(
            source_id=f"file_{hash(file_path)}",
            source_type="file",
            path=file_path
        )
        
        # Создаем запрос валидации с опциями по умолчанию
        from .schemas import ValidationOptions
        
        options = ValidationOptions()
        if validation_options:
            for key, value in validation_options.items():
                if hasattr(options, key):
                    setattr(options, key, value)
        
        validation_request = ValidationRequest(validation_options=options)
        
        # Выполняем валидацию
        result = data_validator.validate_data_source(source, validation_request)
        
        return {
            "validation_id": result.validation_id,
            "status": result.status,
            "quality_score": result.quality_score,
            "issues_count": len(result.issues),
            "issues": result.issues[:10],  # Ограничиваем вывод
            "recommendations_count": len(result.recommendations),
            "processing_time_ms": result.metadata.processing_time_ms if result.metadata else 0
        }
        
    except Exception as e:
        logger.error(f"Ошибка при валидации файла {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка валидации файла: {str(e)}")


@router.post("/analyze-quality")
async def analyze_data_quality(
    source_data: Dict[str, Any],
    include_anomalies: bool = True,
    include_recommendations: bool = True
):
    """
    Анализ качества данных с детальной информацией.
    
    Args:
        source_data: Данные об источнике
        include_anomalies: Включать ли анализ аномалий
        include_recommendations: Включать ли рекомендации
    """
    try:
        # Создаем источник данных из переданных параметров
        source = DataSource(
            source_id=source_data.get("source_id", "unknown"),
            source_type=source_data.get("source_type", "file"),
            path=source_data.get("path"),
            connection=source_data.get("connection"),
            table=source_data.get("table")
        )
        
        # Настраиваем опции валидации
        from .schemas import ValidationOptions, CleaningOptions
        
        validation_options = ValidationOptions(
            detect_anomalies=include_anomalies,
            generate_recommendations=include_recommendations,
            check_duplicates=True,
            assess_quality=True
        )
        
        validation_request = ValidationRequest(
            validation_options=validation_options,
            cleaning_options=CleaningOptions()
        )
        
        # Выполняем анализ
        result = data_validator.validate_data_source(source, validation_request)
        
        # Формируем детальный ответ
        response = {
            "source": {
                "source_id": source.source_id,
                "source_type": source.source_type,
                "path": source.path
            },
            "quality_analysis": {
                "overall_score": result.quality_score,
                "status": result.status,
                "issues": {
                    "total_count": len(result.issues),
                    "by_severity": {},
                    "by_type": {},
                    "details": result.issues
                }
            },
            "recommendations": {
                "storage": result.recommendations,
                "count": len(result.recommendations)
            },
            "metadata": result.metadata,
            "analysis_id": result.validation_id
        }
        
        # Группируем проблемы по серьезности и типу
        for issue in result.issues:
            severity = issue.severity
            issue_type = issue.type
            
            response["quality_analysis"]["issues"]["by_severity"][severity] = \
                response["quality_analysis"]["issues"]["by_severity"].get(severity, 0) + 1
            
            response["quality_analysis"]["issues"]["by_type"][issue_type] = \
                response["quality_analysis"]["issues"]["by_type"].get(issue_type, 0) + 1
        
        return response
        
    except Exception as e:
        logger.error(f"Ошибка при анализе качества данных: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа качества: {str(e)}")


@router.get("/statistics")
async def get_module_statistics():
    """Получение статистики работы модуля валидации."""
    try:
        # Получаем статистику из кэша валидаций
        cache_stats = {
            "total_validations": len(data_validator.validation_cache),
            "successful_validations": sum(
                1 for result in data_validator.validation_cache.values()
                if result.status == ValidationStatus.COMPLETED
            ),
            "failed_validations": sum(
                1 for result in data_validator.validation_cache.values()
                if result.status == ValidationStatus.FAILED
            )
        }
        
        # Статистика по качеству данных
        quality_stats = {
            "average_quality_score": 0.0,
            "high_quality_sources": 0,
            "medium_quality_sources": 0,
            "low_quality_sources": 0
        }
        
        if cache_stats["successful_validations"] > 0:
            quality_scores = [
                result.quality_score for result in data_validator.validation_cache.values()
                if result.status == ValidationStatus.COMPLETED
            ]
            
            quality_stats["average_quality_score"] = sum(quality_scores) / len(quality_scores)
            quality_stats["high_quality_sources"] = sum(1 for score in quality_scores if score >= 0.8)
            quality_stats["medium_quality_sources"] = sum(1 for score in quality_scores if 0.5 <= score < 0.8)
            quality_stats["low_quality_sources"] = sum(1 for score in quality_scores if score < 0.5)
        
        # Статистика по типам проблем
        issue_stats = {}
        for result in data_validator.validation_cache.values():
            for issue in result.issues:
                issue_type = issue.type
                issue_stats[issue_type] = issue_stats.get(issue_type, 0) + 1
        
        return {
            "module_info": {
                "name": "Data Validator",
                "version": "1.0.0",
                "status": "active"
            },
            "validation_statistics": cache_stats,
            "quality_statistics": quality_stats,
            "issue_statistics": issue_stats,
            "generated_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики модуля: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


@router.delete("/cache")
async def clear_validation_cache():
    """Очистка кэша результатов валидации."""
    try:
        cache_size = len(data_validator.validation_cache)
        data_validator.validation_cache.clear()
        
        return {
            "message": "Кэш валидации очищен",
            "cleared_items": cache_size,
            "cleared_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Ошибка при очистке кэша: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка очистки кэша: {str(e)}")


@router.post("/batch-validate")
async def batch_validate_sources(
    sources: List[Dict[str, Any]],
    validation_options: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Пакетная валидация нескольких источников данных.
    
    Args:
        sources: Список источников для валидации
        validation_options: Общие опции валидации
        background_tasks: Фоновые задачи
    """
    try:
        results = []
        
        # Создаем опции валидации
        from .schemas import ValidationOptions
        
        options = ValidationOptions()
        if validation_options:
            for key, value in validation_options.items():
                if hasattr(options, key):
                    setattr(options, key, value)
        
        validation_request = ValidationRequest(validation_options=options)
        
        # Валидируем каждый источник
        for source_data in sources:
            try:
                source = DataSource(
                    source_id=source_data.get("source_id", f"batch_{hash(str(source_data))}"),
                    source_type=source_data.get("source_type", "file"),
                    path=source_data.get("path"),
                    connection=source_data.get("connection"),
                    table=source_data.get("table")
                )
                
                result = data_validator.validate_data_source(source, validation_request)
                
                # Проверяем статус результата
                status_str = result.status.value if hasattr(result.status, 'value') else str(result.status)
                
                result_dict = {
                    "source_id": source.source_id,
                    "validation_id": result.validation_id,
                    "status": status_str,
                    "quality_score": result.quality_score,
                    "issues_count": len(result.issues),
                    "recommendations_count": len(result.recommendations)
                }
                
                # Если валидация не удалась, добавляем информацию об ошибке
                if status_str == "failed" and result.error_message:
                    result_dict["error"] = result.error_message
                
                results.append(result_dict)
                
            except Exception as e:
                results.append({
                    "source_id": source_data.get("source_id", "unknown"),
                    "status": "failed",
                    "error": str(e)
                })
        
        # Статистика пакетной валидации
        successful_count = sum(1 for r in results if r.get("status") == "completed")
        failed_count = len(results) - successful_count
        
        return {
            "batch_results": results,
            "summary": {
                "total_sources": len(sources),
                "successful_validations": successful_count,
                "failed_validations": failed_count,
                "average_quality_score": sum(
                    r.get("quality_score", 0) for r in results 
                    if r.get("quality_score") is not None
                ) / max(successful_count, 1)
            },
            "processed_at": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Ошибка при пакетной валидации: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка пакетной валидации: {str(e)}")


# Дополнительные utility endpoints

@router.get("/supported-formats")
async def get_supported_formats():
    """Получение списка поддерживаемых форматов данных."""
    return {
        "file_formats": [
            {
                "extension": ".csv",
                "description": "Comma-separated values",
                "auto_detection": True,
                "separators_supported": [",", ";", "\t", "|"]
            },
            {
                "extension": ".json",
                "description": "JavaScript Object Notation",
                "auto_detection": True,
                "formats_supported": ["JSON array", "JSON Lines"]
            },
            {
                "extension": ".xml",
                "description": "eXtensible Markup Language",
                "auto_detection": True,
                "integration": "Module 5"
            },
            {
                "extension": ".parquet",
                "description": "Apache Parquet",
                "auto_detection": True,
                "optimized": True
            }
        ],
        "database_types": [
            {
                "type": "postgresql",
                "description": "PostgreSQL database",
                "connection_string": "postgresql://user:password@host:port/database"
            },
            {
                "type": "clickhouse", 
                "description": "ClickHouse database",
                "connection_string": "http://host:port"
            }
        ]
    }

# Новые API endpoints для работы с организацией данных по базам

@router.post("/validate-with-database-organization")
async def validate_file_with_database_organization(
    file_path: str,
    database_name: str,
    source_id: Optional[str] = None
):
    """
    Валидация файла с сохранением в новой системе организации данных по базам.
    
    Args:
        file_path: Путь к файлу для валидации
        database_name: Имя целевой базы данных
        source_id: Идентификатор источника (опционально)
    
    Returns:
        Результат валидации с информацией о сохраненных файлах
    """
    try:
        result = data_validator.validate_file_with_database_organization(
            file_path, database_name, source_id
        )
        return {
            "status": "success",
            "validation_result": result.dict(),
            "message": f"File validated and saved to database {database_name}"
        }
    except Exception as e:
        logger.error(f"Database validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clean-with-database-organization")
async def clean_data_with_database_organization(
    source_id: str,
    database_name: str
):
    """
    Очистка данных с сохранением в новой системе организации.
    
    Args:
        source_id: Идентификатор источника
        database_name: Имя базы данных
    
    Returns:
        Результат очистки с путями к сохраненным файлам
    """
    try:
        result = data_validator.clean_data_with_database_organization(
            source_id, database_name
        )
        return result
    except Exception as e:
        logger.error(f"Database cleaning failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/databases")
async def get_available_databases_endpoint():
    """Получить список доступных баз данных в системе."""
    try:
        databases = get_available_databases()
        return {
            "status": "success",
            "databases": databases,
            "count": len(databases)
        }
    except Exception as e:
        logger.error(f"Failed to get databases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/database/{database_name}/status")
async def get_database_validation_status(database_name: str):
    """
    Получить статус валидации для конкретной базы данных.
    
    Args:
        database_name: Имя базы данных
    
    Returns:
        Статус валидации всех источников в базе данных
    """
    try:
        status = data_validator.get_database_validation_status(database_name)
        return status
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/organization-status")
async def get_data_organization_status():
    """Получить статус новой системы организации данных."""
    try:
        return {
            "status": "active",
            "base_data_dir": str(DataPaths.BASE_DATA_DIR),
            "available_databases": get_available_databases(),
            "max_file_size_mb": DataPaths.MAX_FILE_SIZE_MB,
            "metadata_db": str(DataPaths.MAIN_METADATA_DB),
            "directories": {
                "raw": str(DataPaths.RAW_DATA_DIR),
                "intermediate": str(DataPaths.INTERMEDIATE_DIR),
                "warehouses": str(DataPaths.WAREHOUSES_DIR),
                "metadata": str(DataPaths.METADATA_DIR)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get organization status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
