"""
Pydantic модели для модуля агрегации данных.
"""

from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Типы источников данных."""
    FILE = "file"
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    HDFS = "hdfs"


class AggregationType(str, Enum):
    """Типы агрегаций."""
    JOIN = "join"
    GROUP_BY = "group_by"
    WINDOW = "window"
    UNION = "union"


class EnrichmentType(str, Enum):
    """Типы обогащения данных."""
    CALCULATED_FIELD = "calculated_field"
    LOOKUP = "lookup"
    TRANSFORMATION = "transformation"


class JoinType(str, Enum):
    """Типы JOIN операций."""
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"


class DataSource(BaseModel):
    """Модель источника данных."""
    source_id: str = Field(..., description="Уникальный идентификатор источника")
    source_type: SourceType = Field(..., description="Тип источника данных")
    path: Optional[str] = Field(None, description="Путь к файлу или директории")
    connection: Optional[str] = Field(None, description="Строка подключения к БД")
    table: Optional[str] = Field(None, description="Имя таблицы в БД")
    selected_columns: List[str] = Field(..., description="Выбранные колонки")
    filters: Optional[Dict[str, Any]] = Field(None, description="Фильтры для данных")
    
    @validator('connection')
    def validate_connection_for_db(cls, v, values):
        """Валидация строки подключения для БД."""
        source_type = values.get('source_type')
        if source_type in [SourceType.POSTGRESQL, SourceType.CLICKHOUSE] and not v:
            raise ValueError(f"Connection string required for {source_type}")
        return v
    
    @validator('path')
    def validate_path_for_file(cls, v, values):
        """Валидация пути для файловых источников."""
        source_type = values.get('source_type')
        if source_type in [SourceType.FILE, SourceType.HDFS] and not v:
            raise ValueError(f"Path required for {source_type}")
        return v


class JoinRule(BaseModel):
    """Правило JOIN операции."""
    left_source: str = Field(..., description="ID левого источника")
    right_source: str = Field(..., description="ID правого источника")
    join_keys: Dict[str, str] = Field(..., description="Ключи соединения {left_key: right_key}")
    join_type: JoinType = Field(JoinType.INNER, description="Тип JOIN")
    conditions: Optional[List[str]] = Field(None, description="Дополнительные условия")


class GroupByRule(BaseModel):
    """Правило GROUP BY агрегации."""
    columns: List[str] = Field(..., description="Колонки для группировки")
    aggregates: Dict[str, str] = Field(..., description="Агрегатные функции {alias: expression}")
    having: Optional[List[str]] = Field(None, description="Условия HAVING")


class WindowRule(BaseModel):
    """Правило оконных функций."""
    function: str = Field(..., description="Оконная функция")
    partition_by: List[str] = Field(..., description="Колонки для PARTITION BY")
    order_by: Optional[List[str]] = Field(None, description="Колонки для ORDER BY")
    alias: str = Field(..., description="Алиас результата")


class UnionRule(BaseModel):
    """Правило UNION операции."""
    sources: List[str] = Field(..., description="ID источников для объединения")
    union_type: Literal["union", "union_all"] = Field("union", description="Тип UNION")


class AggregationRule(BaseModel):
    """Правило агрегации данных."""
    type: AggregationType = Field(..., description="Тип агрегации")
    parameters: Union[JoinRule, GroupByRule, WindowRule, UnionRule] = Field(..., description="Параметры агрегации")
    
    @validator('parameters')
    def validate_parameters_type(cls, v, values):
        """Валидация соответствия параметров типу агрегации."""
        agg_type = values.get('type')
        expected_types = {
            AggregationType.JOIN: JoinRule,
            AggregationType.GROUP_BY: GroupByRule,
            AggregationType.WINDOW: WindowRule,
            AggregationType.UNION: UnionRule
        }
        
        if agg_type and not isinstance(v, expected_types[agg_type]):
            raise ValueError(f"Parameters must be {expected_types[agg_type].__name__} for {agg_type}")
        return v


class EnrichmentRule(BaseModel):
    """Правило обогащения данных."""
    type: EnrichmentType = Field(..., description="Тип обогащения")
    name: str = Field(..., description="Имя нового поля")
    expression: str = Field(..., description="Выражение для вычисления")
    description: Optional[str] = Field(None, description="Описание обогащения")


class TargetRequirements(BaseModel):
    """Требования к целевой системе."""
    target_db_type: Optional[Literal["clickhouse", "postgres", "hdfs"]] = Field(None, description="Целевая СУБД")
    refresh_interval: str = Field("daily", description="Интервал обновления")
    expected_volume: str = Field(..., description="Ожидаемый объем данных")
    performance_priority: Literal["query_speed", "storage_size", "balanced"] = Field("balanced", description="Приоритет производительности")
    compression: Optional[bool] = Field(True, description="Использовать сжатие")


class AggregationScenarioRequest(BaseModel):
    """Запрос на создание сценария агрегации."""
    name: str = Field(..., description="Имя сценария", min_length=1, max_length=100)
    description: str = Field(..., description="Описание сценария")
    sources: List[DataSource] = Field(..., description="Источники данных", min_items=1)
    aggregations: List[AggregationRule] = Field(..., description="Правила агрегации", min_items=1)
    enrichments: Optional[List[EnrichmentRule]] = Field([], description="Правила обогащения")
    target_requirements: TargetRequirements = Field(..., description="Требования к целевой системе")
    
    @validator('name')
    def validate_name(cls, v):
        """Валидация имени сценария."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Name must contain only alphanumeric characters, underscores and hyphens")
        return v


class CustomDatasetRequest(BaseModel):
    """Запрос на создание кастомного набора данных."""
    dataset_name: str = Field(..., description="Имя набора данных")
    sources: List[DataSource] = Field(..., description="Источники данных", min_items=1)
    join_strategy: Optional[str] = Field("auto", description="Стратегия соединения")
    output_format: Literal["parquet", "csv", "json"] = Field("parquet", description="Формат выходных данных")
    include_metadata: bool = Field(True, description="Включить метаданные")
    limit_rows: Optional[int] = Field(None, description="Ограничение количества строк для обработки", ge=1, le=10000)


class ColumnInfo(BaseModel):
    """Информация о колонке."""
    name: str = Field(..., description="Имя колонки")
    type: str = Field(..., description="Тип данных")
    nullable: bool = Field(True, description="Может ли быть NULL")
    description: Optional[str] = Field(None, description="Описание колонки")


class SourceAnalysis(BaseModel):
    """Анализ источника данных."""
    source_id: str = Field(..., description="ID источника")
    source_type: SourceType = Field(..., description="Тип источника")
    columns: List[ColumnInfo] = Field(..., description="Информация о колонках")
    row_count: Optional[int] = Field(None, description="Количество строк")
    data_size_bytes: Optional[int] = Field(None, description="Размер данных в байтах")
    sample_data: Optional[List[Dict[str, Any]]] = Field(None, description="Образец данных")
    compatibility_issues: List[str] = Field([], description="Проблемы совместимости")


class OptimizationRecommendation(BaseModel):
    """Рекомендация по оптимизации."""
    type: Literal["index", "partition", "compression", "order_by"] = Field(..., description="Тип оптимизации")
    target: str = Field(..., description="Целевая колонка или выражение")
    reasoning: str = Field(..., description="Обоснование рекомендации")
    priority: Literal["high", "medium", "low"] = Field("medium", description="Приоритет")
    estimated_improvement: Optional[float] = Field(None, description="Ожидаемое улучшение в %")


class ExecutionStats(BaseModel):
    """Статистика выполнения."""
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах")
    input_rows: int = Field(..., description="Количество входных строк")
    output_rows: int = Field(..., description="Количество выходных строк")
    data_reduction_ratio: float = Field(..., description="Коэффициент сжатия данных")
    memory_usage_mb: Optional[float] = Field(None, description="Использование памяти в МБ")


class ExecutionResult(BaseModel):
    """Результат выполнения агрегации."""
    execution_id: str = Field(..., description="ID выполнения")
    scenario_id: str = Field(..., description="ID сценария")
    status: Literal["running", "completed", "failed"] = Field(..., description="Статус выполнения")
    output_path: Optional[str] = Field(None, description="Путь к результатам")
    target_table_ddl: Optional[str] = Field(None, description="DDL для целевой таблицы")
    optimization_recommendations: List[OptimizationRecommendation] = Field([], description="Рекомендации по оптимизации")
    execution_stats: Optional[ExecutionStats] = Field(None, description="Статистика выполнения")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Время создания")
    completed_at: Optional[datetime] = Field(None, description="Время завершения")


class AggregationScenarioResponse(BaseModel):
    """Ответ с информацией о сценарии агрегации."""
    scenario_id: str = Field(..., description="ID сценария")
    name: str = Field(..., description="Имя сценария")
    description: str = Field(..., description="Описание сценария")
    status: Literal["created", "validated", "ready", "error"] = Field(..., description="Статус сценария")
    sources_analysis: List[SourceAnalysis] = Field([], description="Анализ источников")
    estimated_output_size: Optional[int] = Field(None, description="Ожидаемый размер результата")
    recommended_engine: Optional[str] = Field(None, description="Рекомендуемая СУБД")
    validation_errors: List[str] = Field([], description="Ошибки валидации")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Время создания")
    last_modified: datetime = Field(default_factory=datetime.utcnow, description="Время последнего изменения")


class PreviewJoinRequest(BaseModel):
    """Запрос на предварительный просмотр JOIN."""
    left_source: DataSource = Field(..., description="Левый источник")
    right_source: DataSource = Field(..., description="Правый источник")
    join_rule: JoinRule = Field(..., description="Правило JOIN")
    limit: int = Field(10, description="Количество строк для просмотра", ge=1, le=100)


class PreviewJoinResponse(BaseModel):
    """Ответ с предварительным просмотром JOIN."""
    preview_data: List[Dict[str, Any]] = Field(..., description="Данные предварительного просмотра")
    total_estimated_rows: Optional[int] = Field(None, description="Ожидаемое общее количество строк")
    join_statistics: Dict[str, Any] = Field(..., description="Статистика JOIN")
    warnings: List[str] = Field([], description="Предупреждения")


class HealthCheckResponse(BaseModel):
    """Ответ проверки работоспособности."""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Статус модуля")
    version: str = Field(..., description="Версия модуля")
    integrations: Dict[str, bool] = Field(..., description="Статус интеграций с другими модулями")
    active_scenarios: int = Field(..., description="Количество активных сценариев")
    last_execution: Optional[datetime] = Field(None, description="Время последнего выполнения")
    error_details: Optional[str] = Field(None, description="Детали ошибок")
