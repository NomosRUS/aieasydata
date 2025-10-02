"""
Главный модуль валидации данных.

Содержит основной класс DataValidator, который координирует работу
всех компонентов модуля валидации, оценки качества и очистки данных.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import uuid
import requests
from pathlib import Path
import json

# Импортируем новую систему путей
from ..config import DataPaths, file_manager
from ..shared.base_profiler import process_file_with_size_control, get_available_databases

from .schemas import (
    DataSource, ValidationResult, ValidationRequest, CleaningRequest,
    ValidationStatus, ValidationMetadata, QualityAssessment,
    HomogeneityResult, HomogeneityCheckRequest, SourceType, DataFormat
)
from .validator import DataValidator as BaseValidator
from .quality_assessor import QualityAssessor
from .anomaly_detector import AnomalyDetector
from .homogeneity_checker import HomogeneityChecker
from .data_cleaner import DataCleaner
from .storage_recommender import StorageRecommender

logger = logging.getLogger(__name__)


class DataValidator:
    """Главный класс модуля валидации данных."""
    
    def __init__(self, module5_url: str = "http://localhost:8000/api/v1/metrics"):
        self.logger = logging.getLogger(__name__)
        
        # Инициализируем компоненты модуля
        self.base_validator = BaseValidator()
        self.quality_assessor = QualityAssessor()
        self.anomaly_detector = AnomalyDetector()
        self.homogeneity_checker = HomogeneityChecker(module5_url)
        self.data_cleaner = DataCleaner()
        self.storage_recommender = StorageRecommender()
        
        # URL модуля 5 для интеграции
        self.module5_url = module5_url
        
        # Кэш для результатов валидации
        self.validation_cache = {}
    
    def validate_data_source(self, source: DataSource, 
                           validation_request: ValidationRequest) -> ValidationResult:
        """
        Выполняет полную валидацию источника данных.
        
        Args:
            source: Источник данных для валидации
            validation_request: Параметры валидации
            
        Returns:
            Результат валидации данных
        """
        validation_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Начинаем валидацию источника {source.source_id}")
            
            # Загружаем данные из источника
            df = self._load_data_from_source(source)
            
            if df is None or df.empty:
                return ValidationResult(
                    validation_id=validation_id,
                    source=source,
                    status=ValidationStatus.FAILED,
                    quality_score=0.0,
                    error_message="Не удалось загрузить данные из источника"
                )
            
            # Выполняем валидацию
            issues = []
            quality_assessment = None
            recommendations = []
            
            # 1. Базовая валидация
            if validation_request.validation_options.check_duplicates or \
               validation_request.validation_options.assess_quality:
                validation_issues = self.base_validator.validate_dataframe(df, source)
                issues.extend(validation_issues)
            
            # 2. Обнаружение аномалий
            if validation_request.validation_options.detect_anomalies:
                anomalies = self.anomaly_detector.detect_statistical_anomalies(df)
                # Преобразуем аномалии в issues (упрощенно)
                for anomaly in anomalies[:10]:  # Ограничиваем количество
                    issues.append(self._anomaly_to_issue(anomaly))
            
            # 3. Оценка качества
            if validation_request.validation_options.assess_quality:
                quality_assessment = self.quality_assessor.assess_data_quality(df, issues)
            
            # 4. Генерация рекомендаций по хранению
            if validation_request.validation_options.generate_recommendations and quality_assessment:
                data_profile = self._create_data_profile(df, source)
                storage_recommendations = self.storage_recommender.generate_storage_recommendations(
                    quality_assessment, data_profile
                )
                recommendations.extend(storage_recommendations)
            
            # Определяем итоговую оценку качества
            final_quality_score = quality_assessment.overall_score if quality_assessment else 0.5
            
            # Создаем метаданные
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            metadata = ValidationMetadata(
                schema_version="1.0",
                cleaning_timestamp=datetime.now(),
                quality_score=final_quality_score,
                row_count_before=len(df),
                row_count_after=len(df),  # Пока без очистки
                column_count=len(df.columns),
                applied_fixes=[],
                processing_time_ms=processing_time
            )
            
            result = ValidationResult(
                validation_id=validation_id,
                source=source,
                status=ValidationStatus.COMPLETED,
                quality_score=final_quality_score,
                issues=issues,
                recommendations=recommendations,
                metadata=metadata,
                completed_at=datetime.now()
            )
            
            # Кэшируем результат
            self.validation_cache[validation_id] = result
            
            self.logger.info(f"Валидация завершена. ID: {validation_id}, качество: {final_quality_score:.3f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при валидации источника {source.source_id}: {str(e)}")
            
            return ValidationResult(
                validation_id=validation_id,
                source=source,
                status=ValidationStatus.FAILED,
                quality_score=0.0,
                error_message=str(e),
                completed_at=datetime.now()
            )
    
    def clean_data_source(self, source: DataSource, 
                         cleaning_request: CleaningRequest,
                         validation_result: Optional[ValidationResult] = None) -> Dict[str, Any]:
        """
        Выполняет очистку данных источника.
        
        Args:
            source: Источник данных
            cleaning_request: Параметры очистки
            validation_result: Результат предварительной валидации (опционально)
            
        Returns:
            Результат очистки данных
        """
        try:
            self.logger.info(f"Начинаем очистку источника {source.source_id}")
            
            # Загружаем данные
            df = self._load_data_from_source(source)
            
            if df is None or df.empty:
                raise ValueError("Не удалось загрузить данные для очистки")
            
            # Получаем проблемы качества
            issues = validation_result.issues if validation_result else []
            if not issues:
                # Если нет предварительной валидации, выполняем быструю проверку
                issues = self.base_validator.validate_dataframe(df, source)
            
            # Выполняем очистку
            cleaned_df, applied_fixes = self.data_cleaner.clean_dataframe(
                df, issues, cleaning_request.cleaning_strategy, cleaning_request.preserve_original
            )
            
            # Сохраняем очищенные данные
            cleaned_file_path = self.data_cleaner.save_cleaned_data(
                cleaned_df, source.path or f"source_{source.source_id}"
            )
            
            # Повторная оценка качества после очистки
            post_cleaning_assessment = self.quality_assessor.assess_data_quality(cleaned_df)
            
            # Генерируем рекомендации по хранению
            data_profile = self._create_data_profile(cleaned_df, source)
            storage_recommendations = self.storage_recommender.generate_storage_recommendations(
                post_cleaning_assessment, data_profile
            )
            
            # Создаем метаданные
            metadata = ValidationMetadata(
                schema_version="1.0",
                cleaning_timestamp=datetime.now(),
                quality_score=post_cleaning_assessment.overall_score,
                row_count_before=len(df),
                row_count_after=len(cleaned_df),
                column_count=len(cleaned_df.columns),
                applied_fixes=applied_fixes,
                processing_time_ms=0  # Будет обновлено позже
            )
            
            # Формируем рекомендации по хранению в формате для модуля 4
            db_recommendation = next(
                (rec for rec in storage_recommendations if rec.recommendation_type == "database_choice"),
                None
            )
            
            recommended_db = db_recommendation.recommended_value if db_recommendation else "postgresql"
            
            storage_config = self.storage_recommender.get_database_specific_recommendations(
                recommended_db, storage_recommendations
            )
            
            result = {
                "cleaned_file_path": cleaned_file_path,
                "metadata": metadata,
                "storage_recommendations": {
                    "recommended_db": recommended_db,
                    **storage_config
                }
            }
            
            self.logger.info(f"Очистка завершена. Файл сохранен: {cleaned_file_path}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке данных: {str(e)}")
            raise
    
    def check_folder_homogeneity(self, request: HomogeneityCheckRequest) -> HomogeneityResult:
        """
        Проверяет однородность файлов в папке.
        
        Args:
            request: Запрос на проверку однородности
            
        Returns:
            Результат проверки однородности
        """
        try:
            self.logger.info(f"Проверяем однородность папки: {request.folder_path}")
            
            result = self.homogeneity_checker.check_folder_homogeneity(
                request.folder_path, request.auto_separate
            )
            
            self.logger.info(f"Проверка однородности завершена. Однородных файлов: {result.homogeneous_files}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке однородности: {str(e)}")
            raise
    
    def get_available_sources(self) -> List[Dict[str, Any]]:
        """
        Возвращает список доступных источников данных.
        
        Returns:
            Список источников данных
        """
        sources = []
        
        try:
            # Сканируем data_landing_zone
            data_landing_zone = Path("data_landing_zone")
            
            # Сырые данные
            raw_path = data_landing_zone / "raw"
            if raw_path.exists():
                sources.extend(self._scan_directory(raw_path, "raw"))
            
            # Очищенные данные (если есть)
            cleaned_path = data_landing_zone / "cleaned"
            if cleaned_path.exists():
                sources.extend(self._scan_directory(cleaned_path, "cleaned"))
            
            # Тестовые данные
            for test_dir in ["syn_csv", "syn_json", "syn_xml"]:
                test_path = data_landing_zone / test_dir
                if test_path.exists():
                    sources.extend(self._scan_directory(test_path, test_dir))
            
            # Примеры подключений к БД (заглушки)
            sources.extend([
                {
                    "source_id": "postgresql_example",
                    "source_type": "postgresql",
                    "description": "Пример подключения к PostgreSQL",
                    "connection": "postgresql://user:password@localhost:5432/database"
                },
                {
                    "source_id": "clickhouse_example", 
                    "source_type": "clickhouse",
                    "description": "Пример подключения к ClickHouse",
                    "connection": "http://localhost:8123"
                }
            ])
            
        except Exception as e:
            self.logger.warning(f"Ошибка при сканировании источников: {str(e)}")
        
        return sources
    
    def get_validation_result(self, validation_id: str) -> Optional[ValidationResult]:
        """
        Получает результат валидации по ID.
        
        Args:
            validation_id: Идентификатор валидации
            
        Returns:
            Результат валидации или None
        """
        return self.validation_cache.get(validation_id)
    
    def _load_data_from_source(self, source: DataSource) -> Optional[pd.DataFrame]:
        """Загружает данные из источника."""
        try:
            if source.source_type == SourceType.FILE:
                return self._load_file_data(source)
            elif source.source_type == SourceType.POSTGRESQL:
                return self._load_postgresql_data(source)
            elif source.source_type == SourceType.CLICKHOUSE:
                return self._load_clickhouse_data(source)
            else:
                self.logger.warning(f"Неподдерживаемый тип источника: {source.source_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке данных из источника: {str(e)}")
            return None
    
    def _load_file_data(self, source: DataSource) -> Optional[pd.DataFrame]:
        """Загружает данные из файла."""
        if not source.path:
            return None
        
        # В контейнере используем путь как есть, если он начинается с /data
        if source.path.startswith('/data'):
            file_path = Path(source.path)
        else:
            # Если путь не начинается с /data, преобразуем его
            host_path = source.path
            if source.path.startswith('data_landing_zone'):
                host_path = source.path.replace('data_landing_zone', '/data')
            file_path = Path(host_path)
        
        if not file_path.exists():
            self.logger.warning(f"Файл не найден: {file_path} (исходный путь: {source.path})")
            return None
        
        # Пытаемся использовать модуль 5 для автоопределения
        try:
            response = requests.get(
                f"{self.module5_url}/auto-detect",
                params={"source": str(file_path)},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Если модуль 5 вернул данные, используем их
                if "sample_data" in data:
                    # Преобразуем данные в DataFrame (упрощенная реализация)
                    return pd.DataFrame(data["sample_data"][:1000])  # Ограничиваем размер
                    
        except Exception as e:
            self.logger.debug(f"Не удалось использовать модуль 5: {str(e)}")
        
        # Fallback к прямому чтению
        try:
            extension = file_path.suffix.lower()
            
            if extension == '.csv':
                # Пробуем разные разделители
                for sep in [',', ';', '\t', '|']:
                    try:
                        df = pd.read_csv(file_path, sep=sep, nrows=10000)  # Ограничиваем размер
                        if len(df.columns) > 1:
                            return df
                    except:
                        continue
                        
            elif extension == '.json':
                # Сначала пробуем обычный JSON массив
                try:
                    df = pd.read_json(file_path)
                    return df.head(10000)  # Ограничиваем размер
                except:
                    # Если не получилось, пробуем JSON Lines
                    df = pd.read_json(file_path, lines=True, nrows=10000)
                    return df
                
            elif extension == '.parquet':
                df = pd.read_parquet(file_path)
                return df.head(10000)  # Ограничиваем размер
                
        except Exception as e:
            self.logger.error(f"Ошибка при чтении файла {source.path}: {str(e)}")
        
        return None
    
    def _load_postgresql_data(self, source: DataSource) -> Optional[pd.DataFrame]:
        """Загружает данные из PostgreSQL."""
        # Заглушка для подключения к PostgreSQL
        self.logger.info("Загрузка данных из PostgreSQL (заглушка)")
        return None
    
    def _load_clickhouse_data(self, source: DataSource) -> Optional[pd.DataFrame]:
        """Загружает данные из ClickHouse."""
        # Заглушка для подключения к ClickHouse
        self.logger.info("Загрузка данных из ClickHouse (заглушка)")
        return None
    
    def _create_data_profile(self, df: pd.DataFrame, source: DataSource) -> Dict[str, Any]:
        """Создает профиль данных для рекомендаций."""
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": df.columns.tolist(),
            "column_types": {col: str(df[col].dtype) for col in df.columns},
            "data_size_bytes": df.memory_usage(deep=True).sum(),
            "source_type": source.source_type,
            "source_path": source.path
        }
    
    def _anomaly_to_issue(self, anomaly) -> Any:
        """Преобразует аномалию в проблему качества."""
        from .schemas import QualityIssue, IssueType, IssueSeverity
        
        return QualityIssue(
            issue_id=anomaly.anomaly_id,
            type=IssueType.ANOMALY,
            severity=IssueSeverity.MEDIUM if anomaly.score > 5 else IssueSeverity.LOW,
            column=anomaly.column,
            count=1,
            percentage=0.1,  # Примерное значение
            description=anomaly.description,
            suggested_fix="Проверьте аномальное значение на корректность"
        )
    
    def _scan_directory(self, directory: Path, source_type: str) -> List[Dict[str, Any]]:
        """Сканирует директорию на наличие файлов данных."""
        sources = []
        
        try:
            supported_extensions = {'.csv', '.json', '.xml', '.parquet'}
            
            for file_path in directory.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    sources.append({
                        "source_id": f"{source_type}_{file_path.stem}",
                        "source_type": "file",
                        "path": str(file_path),
                        "format": file_path.suffix[1:].lower(),
                        "size_bytes": file_path.stat().st_size,
                        "description": f"Файл {file_path.name} из {source_type}"
                    })
                    
        except Exception as e:
            self.logger.warning(f"Ошибка при сканировании {directory}: {str(e)}")
        
        return sources
    
    def get_basic_health_status(self) -> Dict[str, Any]:
        """
        Возвращает базовый статус здоровья модуля без проверки интеграций.
        Быстрый метод для health check endpoint.
        
        Returns:
            Словарь со статусом модуля
        """
        return {
            "status": "healthy",
            "version": "1.0.0",
            "integrations": {
                "module_5": "not_checked",
                "data_landing_zone": "available" if Path("/data").exists() else "unavailable"
            },
            "last_check": datetime.now()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Возвращает статус здоровья модуля и его интеграций.
        
        Returns:
            Словарь со статусом модуля
        """
        status = {
            "status": "healthy",
            "version": "1.0.0",
            "integrations": {},
            "last_check": datetime.now()
        }
        
        # Проверяем интеграцию с модулем 5 (критично для автоопределения типов)
        try:
            # В контейнере обращаемся к самому себе через localhost
            health_url = f"{self.module5_url}/health-check"
            
            # Делаем несколько попыток с увеличенным таймаутом
            for attempt in range(2):
                try:
                    response = requests.get(health_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "healthy":
                            status["integrations"]["module_5"] = "healthy"
                            break
                        else:
                            status["integrations"]["module_5"] = "degraded"
                            break
                    else:
                        status["integrations"]["module_5"] = "degraded"
                        self.logger.warning(f"Module 5 responded with status {response.status_code}")
                        break
                except requests.exceptions.Timeout:
                    if attempt == 0:
                        continue  # Повторяем попытку
                    else:
                        raise  # Последняя попытка не удалась
                        
        except Exception as e:
            status["integrations"]["module_5"] = "unavailable"
            self.logger.debug(f"Module 5 unavailable: {str(e)}")  # Понижаем уровень логирования
        
        # Проверяем доступность новой системы организации данных
        try:
            if DataPaths.BASE_DATA_DIR.exists() and DataPaths.BASE_DATA_DIR.is_dir():
                status["integrations"]["data_organization"] = "available"
                status["integrations"]["available_databases"] = get_available_databases()
                status["integrations"]["base_data_dir"] = str(DataPaths.BASE_DATA_DIR)
            else:
                status["integrations"]["data_organization"] = "unavailable"
        except Exception:
            status["integrations"]["data_organization"] = "error"
        
        return status
    
    def validate_file_with_database_organization(self, file_path: str, database_name: str, 
                                               source_id: str = None) -> ValidationResult:
        """
        Валидация файла с использованием новой системы организации данных по базам.
        
        Args:
            file_path: Путь к исходному файлу
            database_name: Имя целевой базы данных
            source_id: Идентификатор источника (если не указан, используется имя файла)
        
        Returns:
            ValidationResult с информацией о сохраненных файлах
        """
        if source_id is None:
            source_id = Path(file_path).stem
        
        # Выполняем стандартную валидацию
        validation_result = self.validate_file(file_path)
        
        if validation_result.status == ValidationStatus.VALID:
            try:
                # Сохраняем валидированные данные с контролем размера
                validated_files = process_file_with_size_control(
                    file_path, database_name, source_id, "validated"
                )
                
                # Обновляем результат валидации
                validation_result.metadata.output_files = validated_files
                validation_result.metadata.database_name = database_name
                validation_result.metadata.stage = "validated"
                
                self.logger.info(f"File validated and saved to database {database_name}: {validated_files}")
                
            except Exception as e:
                self.logger.error(f"Failed to save validated file: {e}")
                validation_result.status = ValidationStatus.ERROR
                validation_result.errors.append(f"Failed to save validated file: {str(e)}")
        
        return validation_result
    
    def clean_data_with_database_organization(self, source_id: str, database_name: str) -> Dict[str, Any]:
        """
        Очистка данных с сохранением в новой системе организации.
        
        Args:
            source_id: Идентификатор источника
            database_name: Имя базы данных
        
        Returns:
            Результат очистки с путями к сохраненным файлам
        """
        try:
            # Получаем валидированные файлы
            validated_path = DataPaths.get_source_path(database_name, source_id, "validated")
            
            if not validated_path.exists():
                raise ValueError(f"Validated data not found for {source_id} in {database_name}")
            
            # Находим файлы для очистки
            validated_files = list(validated_path.glob("*.parquet"))
            if not validated_files:
                raise ValueError(f"No parquet files found in {validated_path}")
            
            cleaned_files = []
            
            for validated_file in validated_files:
                # Загружаем данные
                df = pd.read_parquet(validated_file)
                
                # Выполняем очистку
                cleaned_df = self.data_cleaner.clean_dataframe(df)
                
                # Сохраняем очищенные данные с контролем размера
                temp_cleaned_file = validated_path.parent / "temp_cleaned.parquet"
                cleaned_df.to_parquet(temp_cleaned_file, index=False)
                
                # Обрабатываем с контролем размера
                processed_files = process_file_with_size_control(
                    str(temp_cleaned_file), database_name, source_id, "cleaned"
                )
                
                cleaned_files.extend(processed_files)
                
                # Удаляем временный файл
                temp_cleaned_file.unlink()
            
            return {
                "status": "success",
                "source_id": source_id,
                "database_name": database_name,
                "cleaned_files": cleaned_files,
                "files_count": len(cleaned_files)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to clean data: {e}")
            return {
                "status": "error",
                "source_id": source_id,
                "database_name": database_name,
                "error": str(e)
            }
    
    def get_database_validation_status(self, database_name: str) -> Dict[str, Any]:
        """
        Получить статус валидации для конкретной базы данных.
        
        Args:
            database_name: Имя базы данных
        
        Returns:
            Статус валидации всех источников в базе данных
        """
        try:
            db_path = DataPaths.get_database_intermediate_path(database_name, "validated")
            
            if not db_path.exists():
                return {
                    "database_name": database_name,
                    "status": "no_data",
                    "sources": []
                }
            
            sources = []
            for source_dir in db_path.iterdir():
                if source_dir.is_dir():
                    files = list(source_dir.glob("*.parquet"))
                    total_size = sum(f.stat().st_size for f in files)
                    
                    sources.append({
                        "source_id": source_dir.name,
                        "files_count": len(files),
                        "total_size_mb": round(total_size / (1024 * 1024), 2),
                        "files": [str(f) for f in files]
                    })
            
            return {
                "database_name": database_name,
                "status": "active" if sources else "empty",
                "sources_count": len(sources),
                "sources": sources
            }
            
        except Exception as e:
            return {
                "database_name": database_name,
                "status": "error",
                "error": str(e)
            }
