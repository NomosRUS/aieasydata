"""
Pydantic модели для Модуля 3 - Оптимизация производительности
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class SourceType(str, Enum):
    """Типы источников данных"""
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    PARQUET = "parquet"
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    DIRECTORY = "directory"
    EXISTING_WAREHOUSE = "existing_warehouse"


class RecommendationType(str, Enum):
    """Типы рекомендаций по оптимизации"""
    INDEX = "index"
    PARTITION = "partition"
    COMPRESSION = "compression"
    ORDER_BY = "order_by"
    RESTRUCTURE = "restructure"


class Priority(str, Enum):
    """Приоритет рекомендации"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnalysisStatus(str, Enum):
    """Статус анализа производительности"""
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    ERROR = "error"
    APPLYING = "applying"
    APPLIED = "applied"


class PerformanceAnalysisRequest(BaseModel):
    """Запрос на анализ производительности"""
    source: str = Field(..., description="Путь к файлу/директории или строка подключения к БД")
    source_type: Optional[SourceType] = Field(None, description="Тип источника (автоопределяется если не указан)")
    performance_requirements: Optional[Dict[str, Any]] = Field(
        None, 
        description="Требования к производительности"
    )
    constraints: Optional[Dict[str, Any]] = Field(
        None, 
        description="Ограничения для применения оптимизаций"
    )
    target_db_type: Optional[str] = Field(
        None, 
        description="Целевая СУБД для оптимизации (clickhouse, postgres, hdfs)"
    )


class PerformanceMetrics(BaseModel):
    """Метрики производительности источника данных"""
    source_type: SourceType
    data_size_bytes: int = Field(..., description="Размер данных в байтах")
    row_count: int = Field(..., description="Количество строк")
    column_count: Optional[int] = Field(None, description="Количество колонок")
    processing_time_ms: Optional[float] = Field(None, description="Время обработки в миллисекундах")
    avg_query_time_ms: Optional[float] = Field(None, description="Среднее время выполнения запроса")
    index_usage_stats: Optional[Dict[str, Any]] = Field(None, description="Статистика использования индексов")
    partition_stats: Optional[Dict[str, Any]] = Field(None, description="Статистика партиций")
    bottlenecks: List[str] = Field(default_factory=list, description="Выявленные узкие места")
    structure_info: Optional[Dict[str, Any]] = Field(None, description="Информация о структуре данных")


class OptimizationRecommendation(BaseModel):
    """Рекомендация по оптимизации"""
    recommendation_type: RecommendationType
    target_table: str = Field(..., description="Целевая таблица")
    target_db_type: str = Field(..., description="Тип СУБД (clickhouse, postgres, hdfs)")
    ddl_script: str = Field(..., description="DDL скрипт для применения оптимизации")
    recommendation_details: Dict[str, Any] = Field(..., description="Детали рекомендации")
    estimated_improvement: float = Field(..., description="Ожидаемое улучшение в %")
    reasoning: str = Field(..., description="Обоснование от LLM")
    priority: Priority = Field(default=Priority.MEDIUM, description="Приоритет применения")
    validation_status: Optional[str] = Field(None, description="Статус валидации DDL")


class PerformanceAnalysisResult(BaseModel):
    """Результат анализа производительности"""
    analysis_id: str = Field(..., description="Уникальный ID анализа")
    source: str = Field(..., description="Источник данных")
    source_type: SourceType
    status: AnalysisStatus = Field(default=AnalysisStatus.ANALYZING)
    current_metrics: Optional[PerformanceMetrics] = None
    bottlenecks: List[str] = Field(default_factory=list)
    recommendations: List[OptimizationRecommendation] = Field(default_factory=list)
    llm_analysis: Optional[str] = Field(None, description="Анализ от LLM")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class OptimizationApplication(BaseModel):
    """Применение оптимизации"""
    analysis_id: str
    recommendation_ids: List[str] = Field(..., description="ID рекомендаций для применения")
    confirm_application: bool = Field(default=False, description="Подтверждение применения")
    dry_run: bool = Field(default=True, description="Тестовый запуск без реального применения")


class OptimizationResult(BaseModel):
    """Результат применения оптимизации"""
    analysis_id: str
    applied_recommendations: List[str] = Field(default_factory=list)
    failed_recommendations: List[str] = Field(default_factory=list)
    before_metrics: Optional[PerformanceMetrics] = None
    after_metrics: Optional[PerformanceMetrics] = None
    improvement_percentage: Optional[float] = None
    execution_details: Dict[str, Any] = Field(default_factory=dict)
    rollback_script: Optional[str] = Field(None, description="Скрипт для отката изменений")


class PerformanceHistory(BaseModel):
    """История оптимизаций для таблицы"""
    table_name: str
    optimizations: List[Dict[str, Any]] = Field(default_factory=list)
    current_performance: Optional[PerformanceMetrics] = None
    total_improvements: float = Field(default=0.0, description="Общее улучшение производительности в %")


# Модели для интеграции с Модулем 5
class Module5MetricsRequest(BaseModel):
    """Запрос метрик к Модулю 5"""
    source: str
    auto_detect: bool = Field(default=True, description="Использовать автоопределение типа")


class Module5MetricsResponse(BaseModel):
    """Ответ с метриками от Модуля 5"""
    detected_type: str
    metrics: Dict[str, Any]
    structure: Optional[Dict[str, Any]] = None
    processing_time: float
    success: bool
    error: Optional[str] = None


# Модели для интеграции с Модулем 4
class Module4RecommendationSave(BaseModel):
    """Сохранение рекомендации для Модуля 4"""
    table_name: str
    recommendation_type: str
    recommendation_details: Dict[str, Any]
    estimated_improvement: Optional[float] = None
    reasoning: Optional[str] = None
