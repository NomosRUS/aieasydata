"""
Pydantic модели для модуля валидации данных.

Содержит все модели данных, используемые в API и внутренней логике модуля.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Типы источников данных."""
    FILE = "file"
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    HDFS = "hdfs"


class DataFormat(str, Enum):
    """Поддерживаемые форматы данных."""
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    PARQUET = "parquet"


class ValidationStatus(str, Enum):
    """Статусы валидации."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class IssueSeverity(str, Enum):
    """Уровни серьезности проблем."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """Типы проблем в данных."""
    MISSING_VALUES = "missing_values"
    DUPLICATES = "duplicates"
    TYPE_MISMATCH = "type_mismatch"
    ANOMALY = "anomaly"
    CONSTRAINT_VIOLATION = "constraint_violation"
    SCHEMA_INCONSISTENCY = "schema_inconsistency"


class RecommendationType(str, Enum):
    """Типы рекомендаций по хранению."""
    DATABASE_CHOICE = "database_choice"
    PARTITIONING = "partitioning"
    INDEXING = "indexing"
    COMPRESSION = "compression"


class CleaningStrategy(str, Enum):
    """Стратегии очистки данных."""
    AUTO = "auto"
    MANUAL = "manual"
    CONSERVATIVE = "conservative"


# Базовые модели данных

class DataSource(BaseModel):
    """Модель источника данных."""
    source_id: str = Field(..., description="Уникальный идентификатор источника")
    source_type: SourceType = Field(..., description="Тип источника данных")
    path: Optional[str] = Field(None, description="Путь к файлу или директории")
    connection: Optional[str] = Field(None, description="Строка подключения к БД")
    table: Optional[str] = Field(None, description="Имя таблицы в БД")
    format: Optional[DataFormat] = Field(None, description="Формат данных")
    
    class Config:
        use_enum_values = True


class QualityIssue(BaseModel):
    """Модель проблемы качества данных."""
    issue_id: str = Field(..., description="Уникальный идентификатор проблемы")
    type: IssueType = Field(..., description="Тип проблемы")
    severity: IssueSeverity = Field(..., description="Уровень серьезности")
    column: Optional[str] = Field(None, description="Колонка, в которой найдена проблема")
    count: int = Field(..., description="Количество проблемных записей")
    percentage: float = Field(..., description="Процент проблемных записей")
    description: str = Field(..., description="Описание проблемы")
    suggested_fix: Optional[str] = Field(None, description="Предлагаемое исправление")
    
    class Config:
        use_enum_values = True


class ValidationMetadata(BaseModel):
    """Метаданные процесса валидации."""
    schema_version: str = Field(..., description="Версия схемы данных")
    cleaning_timestamp: datetime = Field(..., description="Время очистки данных")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Оценка качества данных")
    row_count_before: int = Field(..., description="Количество строк до очистки")
    row_count_after: int = Field(..., description="Количество строк после очистки")
    column_count: int = Field(..., description="Количество колонок")
    applied_fixes: List[str] = Field(default_factory=list, description="Примененные исправления")
    processing_time_ms: float = Field(..., description="Время обработки в миллисекундах")


class StorageRecommendation(BaseModel):
    """Модель рекомендации по хранению."""
    recommendation_type: RecommendationType = Field(..., description="Тип рекомендации")
    target: str = Field(..., description="Цель рекомендации")
    recommended_value: str = Field(..., description="Рекомендуемое значение")
    reasoning: str = Field(..., description="Обоснование рекомендации")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность в рекомендации")
    estimated_benefit: str = Field(..., description="Ожидаемая польза")
    
    class Config:
        use_enum_values = True


class ValidationResult(BaseModel):
    """Результат валидации данных."""
    validation_id: str = Field(..., description="Уникальный идентификатор валидации")
    source: DataSource = Field(..., description="Источник данных")
    status: ValidationStatus = Field(..., description="Статус валидации")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Оценка качества данных")
    issues: List[QualityIssue] = Field(default_factory=list, description="Найденные проблемы")
    recommendations: List[StorageRecommendation] = Field(default_factory=list, description="Рекомендации по хранению")
    cleaned_data_path: Optional[str] = Field(None, description="Путь к очищенным данным")
    metadata: Optional[ValidationMetadata] = Field(None, description="Метаданные валидации")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    created_at: datetime = Field(default_factory=datetime.now, description="Время создания")
    completed_at: Optional[datetime] = Field(None, description="Время завершения")
    
    class Config:
        use_enum_values = True


# Модели для проверки однородности

class SchemaInfo(BaseModel):
    """Информация о схеме файла."""
    columns: List[str] = Field(..., description="Список колонок")
    column_types: Dict[str, str] = Field(..., description="Типы колонок")
    separator: Optional[str] = Field(None, description="Разделитель для CSV")
    encoding: Optional[str] = Field(None, description="Кодировка файла")


class FileSchemaAnalysis(BaseModel):
    """Анализ схемы файла."""
    file_path: str = Field(..., description="Путь к файлу")
    schema: SchemaInfo = Field(..., description="Схема файла")
    is_consistent: bool = Field(..., description="Соответствует ли схема эталонной")
    differences: List[str] = Field(default_factory=list, description="Различия с эталонной схемой")


class HomogeneityResult(BaseModel):
    """Результат проверки однородности файлов."""
    folder_path: str = Field(..., description="Путь к проверяемой папке")
    homogeneous: bool = Field(..., description="Являются ли файлы однородными")
    total_files: int = Field(..., description="Общее количество файлов")
    homogeneous_files: int = Field(..., description="Количество однородных файлов")
    inconsistent_files: int = Field(..., description="Количество неоднородных файлов")
    inconsistent_files_moved_to: Optional[str] = Field(None, description="Путь к папке с неоднородными файлами")
    reference_schema: Optional[SchemaInfo] = Field(None, description="Эталонная схема")
    file_analyses: List[FileSchemaAnalysis] = Field(default_factory=list, description="Анализ каждого файла")
    schema_differences: List[Dict[str, Any]] = Field(default_factory=list, description="Различия в схемах")


# Модели для API запросов

class ValidationOptions(BaseModel):
    """Опции валидации данных."""
    check_duplicates: bool = Field(True, description="Проверять дубликаты")
    detect_anomalies: bool = Field(True, description="Обнаруживать аномалии")
    assess_quality: bool = Field(True, description="Оценивать качество")
    generate_recommendations: bool = Field(True, description="Генерировать рекомендации")


class CleaningOptions(BaseModel):
    """Опции очистки данных."""
    auto_clean: bool = Field(False, description="Автоматическая очистка")
    preserve_original: bool = Field(True, description="Сохранять оригинальные данные")
    cleaning_strategy: CleaningStrategy = Field(CleaningStrategy.CONSERVATIVE, description="Стратегия очистки")
    
    class Config:
        use_enum_values = True


class ValidationRequest(BaseModel):
    """Запрос на валидацию данных."""
    validation_options: ValidationOptions = Field(default_factory=ValidationOptions, description="Опции валидации")
    cleaning_options: CleaningOptions = Field(default_factory=CleaningOptions, description="Опции очистки")


class CleaningRequest(BaseModel):
    """Запрос на очистку данных."""
    cleaning_strategy: CleaningStrategy = Field(CleaningStrategy.AUTO, description="Стратегия очистки")
    preserve_original: bool = Field(True, description="Сохранять оригинальные данные")
    apply_recommendations: List[str] = Field(default_factory=list, description="Применяемые рекомендации")
    
    class Config:
        use_enum_values = True


class HomogeneityCheckRequest(BaseModel):
    """Запрос на проверку однородности."""
    folder_path: str = Field(..., description="Путь к папке для проверки")
    auto_separate: bool = Field(True, description="Автоматически разделять неоднородные файлы")


# Модели для статистического анализа

class AnomalyInfo(BaseModel):
    """Информация об аномалии."""
    anomaly_id: str = Field(..., description="Идентификатор аномалии")
    column: str = Field(..., description="Колонка с аномалией")
    anomaly_type: str = Field(..., description="Тип аномалии")
    value: Union[str, int, float] = Field(..., description="Аномальное значение")
    score: float = Field(..., description="Оценка аномальности")
    method: str = Field(..., description="Метод обнаружения")
    description: str = Field(..., description="Описание аномалии")


class QualityAssessment(BaseModel):
    """Оценка качества данных."""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Общая оценка качества")
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="Оценка полноты")
    correctness_score: float = Field(..., ge=0.0, le=1.0, description="Оценка корректности")
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="Оценка согласованности")
    uniqueness_score: float = Field(..., ge=0.0, le=1.0, description="Оценка уникальности")
    anomalies: List[AnomalyInfo] = Field(default_factory=list, description="Обнаруженные аномалии")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации по улучшению")


# Модели ответов API

class ValidationResponse(BaseModel):
    """Ответ на запрос валидации."""
    validation_id: str = Field(..., description="Идентификатор валидации")
    quality_score: float = Field(..., description="Оценка качества данных")
    issues: List[QualityIssue] = Field(..., description="Найденные проблемы")
    recommended_storage: str = Field(..., description="Рекомендуемое хранилище")
    storage_recommendations: List[StorageRecommendation] = Field(..., description="Рекомендации по хранению")


class CleaningResponse(BaseModel):
    """Ответ на запрос очистки."""
    cleaned_file_path: str = Field(..., description="Путь к очищенным данным")
    metadata: ValidationMetadata = Field(..., description="Метаданные очистки")
    storage_recommendations: Dict[str, Any] = Field(..., description="Рекомендации по хранению")


class HealthCheckResponse(BaseModel):
    """Ответ на проверку здоровья модуля."""
    status: str = Field(..., description="Статус модуля")
    version: str = Field(..., description="Версия модуля")
    integrations: Dict[str, str] = Field(..., description="Статус интеграций")
    last_check: datetime = Field(..., description="Время последней проверки")
