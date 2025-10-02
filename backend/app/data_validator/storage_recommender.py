"""
Рекомендации по хранению данных.

Содержит алгоритмы для генерации рекомендаций по выбору оптимальной СУБД
и настройке хранения данных на основе анализа качества и характеристик данных.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from .schemas import (
    StorageRecommendation, QualityAssessment, DataSource,
    RecommendationType
)

logger = logging.getLogger(__name__)


class StorageRecommender:
    """Класс для генерации рекомендаций по хранению данных."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Пороговые значения для принятия решений
        self.thresholds = {
            'quality_score': {
                'high': 0.8,      # Высокое качество данных
                'medium': 0.5,    # Среднее качество данных
                'low': 0.3        # Низкое качество данных
            },
            'data_size': {
                'small': 1_000_000,      # < 1M строк
                'medium': 10_000_000,    # < 10M строк
                'large': 100_000_000     # < 100M строк
            },
            'partitioning_threshold': 1_000_000,  # Партиционирование для >1M строк
            'indexing_threshold': 100_000         # Индексы для >100K строк
        }
    
    def generate_storage_recommendations(self, quality_assessment: QualityAssessment, 
                                       data_profile: Dict[str, Any],
                                       business_requirements: Optional[str] = None) -> List[StorageRecommendation]:
        """
        Генерирует рекомендации по хранению данных.
        
        Args:
            quality_assessment: Результат оценки качества данных
            data_profile: Профиль данных (размер, структура, типы)
            business_requirements: Бизнес-требования (опционально)
            
        Returns:
            Список рекомендаций по хранению
        """
        recommendations = []
        
        try:
            # 1. Рекомендация по выбору СУБД
            db_recommendation = self._recommend_database(quality_assessment, data_profile, business_requirements)
            recommendations.append(db_recommendation)
            
            # 2. Рекомендации по партиционированию
            partitioning_recommendations = self._recommend_partitioning(data_profile)
            recommendations.extend(partitioning_recommendations)
            
            # 3. Рекомендации по индексированию
            indexing_recommendations = self._recommend_indexing(data_profile)
            recommendations.extend(indexing_recommendations)
            
            # 4. Рекомендации по сжатию
            compression_recommendations = self._recommend_compression(data_profile, quality_assessment.overall_score)
            recommendations.extend(compression_recommendations)
            
            self.logger.info(f"Сгенерировано {len(recommendations)} рекомендаций по хранению")
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации рекомендаций: {str(e)}")
            
            # Возвращаем базовую рекомендацию при ошибке
            recommendations.append(StorageRecommendation(
                recommendation_type=RecommendationType.DATABASE_CHOICE,
                target="database",
                recommended_value="postgresql",
                reasoning=f"Ошибка при анализе: {str(e)}. Рекомендуется PostgreSQL как универсальное решение.",
                confidence=0.5,
                estimated_benefit="Стабильное хранение данных"
            ))
        
        return recommendations
    
    def _recommend_database(self, quality_assessment: QualityAssessment, 
                           data_profile: Dict[str, Any],
                           business_requirements: Optional[str] = None) -> StorageRecommendation:
        """Рекомендует оптимальную СУБД."""
        
        quality_score = quality_assessment.overall_score
        row_count = data_profile.get('row_count', 0)
        column_count = data_profile.get('column_count', 0)
        
        # Анализируем характеристики данных
        has_analytics_patterns = self._detect_analytics_patterns(data_profile, business_requirements)
        has_transactional_patterns = self._detect_transactional_patterns(data_profile, business_requirements)
        is_large_dataset = row_count > self.thresholds['data_size']['large']
        
        # Логика выбора СУБД
        if quality_score < self.thresholds['quality_score']['low']:
            # Низкое качество данных - рекомендуем HDFS для сырых данных
            recommended_db = "hdfs"
            reasoning = f"Низкое качество данных ({quality_score:.2f}) требует хранения в HDFS для последующей обработки"
            confidence = 0.8
            
        elif has_analytics_patterns and quality_score >= self.thresholds['quality_score']['medium']:
            # Аналитические паттерны + хорошее качество = ClickHouse
            recommended_db = "clickhouse"
            reasoning = f"Обнаружены аналитические паттерны, качество данных {quality_score:.2f} подходит для ClickHouse"
            confidence = 0.9
            
        elif has_transactional_patterns and quality_score >= self.thresholds['quality_score']['high']:
            # Транзакционные паттерны + высокое качество = PostgreSQL
            recommended_db = "postgresql"
            reasoning = f"Обнаружены транзакционные паттерны, высокое качество данных ({quality_score:.2f}) подходит для PostgreSQL"
            confidence = 0.85
            
        elif is_large_dataset and quality_score >= self.thresholds['quality_score']['medium']:
            # Большой объем данных = ClickHouse для аналитики
            recommended_db = "clickhouse"
            reasoning = f"Большой объем данных ({row_count:,} строк) эффективнее обрабатывать в ClickHouse"
            confidence = 0.75
            
        else:
            # По умолчанию PostgreSQL как универсальное решение
            recommended_db = "postgresql"
            reasoning = f"Универсальное решение для данных среднего качества ({quality_score:.2f}) и размера ({row_count:,} строк)"
            confidence = 0.7
        
        return StorageRecommendation(
            recommendation_type=RecommendationType.DATABASE_CHOICE,
            target="database",
            recommended_value=recommended_db,
            reasoning=reasoning,
            confidence=confidence,
            estimated_benefit=self._estimate_db_benefit(recommended_db, data_profile)
        )
    
    def _detect_analytics_patterns(self, data_profile: Dict[str, Any], 
                                 business_requirements: Optional[str] = None) -> bool:
        """Обнаруживает паттерны аналитического использования."""
        
        # Проверяем бизнес-требования
        if business_requirements:
            analytics_keywords = ['аналитика', 'отчет', 'dashboard', 'bi', 'olap', 'агрегация', 'метрики']
            if any(keyword in business_requirements.lower() for keyword in analytics_keywords):
                return True
        
        # Анализируем структуру данных
        columns = data_profile.get('columns', [])
        column_types = data_profile.get('column_types', {})
        
        # Ищем признаки аналитических данных
        has_date_columns = any('date' in col.lower() or 'time' in col.lower() for col in columns)
        has_numeric_measures = sum(1 for col_type in column_types.values() 
                                 if col_type in ['int64', 'float64', 'number']) > len(columns) * 0.3
        has_categorical_dimensions = sum(1 for col_type in column_types.values() 
                                       if col_type in ['object', 'string']) > 2
        
        return has_date_columns and has_numeric_measures and has_categorical_dimensions
    
    def _detect_transactional_patterns(self, data_profile: Dict[str, Any], 
                                     business_requirements: Optional[str] = None) -> bool:
        """Обнаруживает паттерны транзакционного использования."""
        
        # Проверяем бизнес-требования
        if business_requirements:
            transactional_keywords = ['oltp', 'транзакц', 'crud', 'операции', 'обновление', 'вставка']
            if any(keyword in business_requirements.lower() for keyword in transactional_keywords):
                return True
        
        # Анализируем структуру данных
        columns = data_profile.get('columns', [])
        
        # Ищем признаки транзакционных данных
        has_id_columns = any('id' in col.lower() for col in columns)
        has_status_columns = any('status' in col.lower() or 'state' in col.lower() for col in columns)
        has_user_columns = any('user' in col.lower() or 'customer' in col.lower() for col in columns)
        
        return has_id_columns and (has_status_columns or has_user_columns)
    
    def _estimate_db_benefit(self, db_type: str, data_profile: Dict[str, Any]) -> str:
        """Оценивает ожидаемую пользу от выбранной СУБД."""
        
        row_count = data_profile.get('row_count', 0)
        
        if db_type == "clickhouse":
            if row_count > 10_000_000:
                return "Ускорение аналитических запросов в 10-100 раз"
            else:
                return "Ускорение аналитических запросов в 3-10 раз"
                
        elif db_type == "postgresql":
            return "ACID транзакции, надежность, универсальность"
            
        elif db_type == "hdfs":
            return "Масштабируемое хранение больших объемов сырых данных"
            
        else:
            return "Оптимизированное хранение данных"
    
    def _recommend_partitioning(self, data_profile: Dict[str, Any]) -> List[StorageRecommendation]:
        """Генерирует рекомендации по партиционированию."""
        recommendations = []
        
        row_count = data_profile.get('row_count', 0)
        columns = data_profile.get('columns', [])
        column_types = data_profile.get('column_types', {})
        
        # Партиционирование имеет смысл только для больших таблиц
        if row_count < self.thresholds['partitioning_threshold']:
            return recommendations
        
        # Ищем подходящие колонки для партиционирования
        
        # 1. Временные колонки (приоритет 1)
        date_columns = [col for col in columns 
                       if any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated'])
                       and column_types.get(col) in ['datetime64', 'date', 'object']]
        
        for date_col in date_columns[:1]:  # Берем только первую найденную
            recommendations.append(StorageRecommendation(
                recommendation_type=RecommendationType.PARTITIONING,
                target=date_col,
                recommended_value="monthly",
                reasoning=f"Партиционирование по месяцам для временной колонки '{date_col}' ускорит запросы с фильтрацией по времени",
                confidence=0.9,
                estimated_benefit="Ускорение запросов в 5-20 раз при фильтрации по дате"
            ))
        
        # 2. Категориальные колонки с умеренной кардинальностью
        if not date_columns:  # Только если нет временных колонок
            categorical_columns = [col for col in columns 
                                 if column_types.get(col) in ['object', 'string']
                                 and any(keyword in col.lower() for keyword in ['region', 'category', 'type', 'status'])]
            
            for cat_col in categorical_columns[:1]:  # Берем только одну
                recommendations.append(StorageRecommendation(
                    recommendation_type=RecommendationType.PARTITIONING,
                    target=cat_col,
                    recommended_value="categorical",
                    reasoning=f"Партиционирование по категориальной колонке '{cat_col}' для равномерного распределения данных",
                    confidence=0.7,
                    estimated_benefit="Ускорение запросов в 2-5 раз при фильтрации по категориям"
                ))
        
        return recommendations
    
    def _recommend_indexing(self, data_profile: Dict[str, Any]) -> List[StorageRecommendation]:
        """Генерирует рекомендации по индексированию."""
        recommendations = []
        
        row_count = data_profile.get('row_count', 0)
        columns = data_profile.get('columns', [])
        column_types = data_profile.get('column_types', {})
        
        # Индексы имеют смысл для таблиц среднего размера и больше
        if row_count < self.thresholds['indexing_threshold']:
            return recommendations
        
        # Приоритеты для индексирования:
        
        # 1. ID колонки (высокий приоритет)
        id_columns = [col for col in columns 
                     if col.lower().endswith('_id') or col.lower() == 'id']
        
        for id_col in id_columns:
            recommendations.append(StorageRecommendation(
                recommendation_type=RecommendationType.INDEXING,
                target=id_col,
                recommended_value="btree_index",
                reasoning=f"Индекс на ID колонке '{id_col}' для быстрого поиска записей",
                confidence=0.95,
                estimated_benefit="Ускорение поиска по ID в 100-1000 раз"
            ))
        
        # 2. Внешние ключи (высокий приоритет)
        fk_columns = [col for col in columns 
                     if col.lower().endswith('_id') and col.lower() != 'id'
                     and col not in id_columns]
        
        for fk_col in fk_columns[:3]:  # Ограничиваем количество
            recommendations.append(StorageRecommendation(
                recommendation_type=RecommendationType.INDEXING,
                target=fk_col,
                recommended_value="btree_index",
                reasoning=f"Индекс на внешнем ключе '{fk_col}' для ускорения JOIN операций",
                confidence=0.85,
                estimated_benefit="Ускорение JOIN операций в 10-100 раз"
            ))
        
        # 3. Часто используемые для поиска колонки (средний приоритет)
        search_columns = [col for col in columns 
                         if any(keyword in col.lower() for keyword in ['name', 'email', 'phone', 'code'])
                         and column_types.get(col) in ['object', 'string']]
        
        for search_col in search_columns[:2]:  # Ограничиваем количество
            recommendations.append(StorageRecommendation(
                recommendation_type=RecommendationType.INDEXING,
                target=search_col,
                recommended_value="btree_index",
                reasoning=f"Индекс на колонке '{search_col}' для ускорения текстового поиска",
                confidence=0.7,
                estimated_benefit="Ускорение текстового поиска в 5-50 раз"
            ))
        
        return recommendations
    
    def _recommend_compression(self, data_profile: Dict[str, Any], quality_score: float) -> List[StorageRecommendation]:
        """Генерирует рекомендации по сжатию данных."""
        recommendations = []
        
        data_size_bytes = data_profile.get('data_size_bytes', 0)
        columns = data_profile.get('columns', [])
        column_types = data_profile.get('column_types', {})
        
        # Сжатие имеет смысл для данных размером больше 100MB
        if data_size_bytes < 100 * 1024 * 1024:  # 100MB
            return recommendations
        
        # Анализируем типы данных для выбора алгоритма сжатия
        
        # Подсчитываем типы колонок
        string_columns = sum(1 for col_type in column_types.values() 
                           if col_type in ['object', 'string'])
        numeric_columns = sum(1 for col_type in column_types.values() 
                            if col_type in ['int64', 'float64', 'number'])
        
        total_columns = len(columns)
        
        if total_columns == 0:
            return recommendations
        
        string_ratio = string_columns / total_columns
        numeric_ratio = numeric_columns / total_columns
        
        # Выбираем алгоритм сжатия
        if string_ratio > 0.6:
            # Много строковых данных - хорошо сжимается
            compression_type = "lz4"
            compression_ratio = "60-80%"
            reasoning = f"Высокая доля строковых данных ({string_ratio:.1%}) эффективно сжимается алгоритмом LZ4"
            
        elif numeric_ratio > 0.6:
            # Много числовых данных - умеренное сжатие
            compression_type = "zstd"
            compression_ratio = "40-60%"
            reasoning = f"Высокая доля числовых данных ({numeric_ratio:.1%}) эффективно сжимается алгоритмом ZSTD"
            
        else:
            # Смешанные данные - универсальное сжатие
            compression_type = "lz4"
            compression_ratio = "50-70%"
            reasoning = "Смешанные типы данных эффективно сжимаются универсальным алгоритмом LZ4"
        
        # Учитываем качество данных
        if quality_score < 0.7:
            reasoning += f". Низкое качество данных ({quality_score:.2f}) может снизить эффективность сжатия"
            compression_ratio = "30-50%"
        
        recommendations.append(StorageRecommendation(
            recommendation_type=RecommendationType.COMPRESSION,
            target="table",
            recommended_value=compression_type,
            reasoning=reasoning,
            confidence=0.8,
            estimated_benefit=f"Экономия дискового пространства на {compression_ratio}"
        ))
        
        return recommendations
    
    def get_database_specific_recommendations(self, db_type: str, 
                                           general_recommendations: List[StorageRecommendation]) -> Dict[str, Any]:
        """
        Преобразует общие рекомендации в специфичные для конкретной СУБД.
        
        Args:
            db_type: Тип базы данных (clickhouse, postgresql, hdfs)
            general_recommendations: Общие рекомендации
            
        Returns:
            Словарь с рекомендациями, специфичными для СУБД
        """
        
        if db_type == "clickhouse":
            return self._get_clickhouse_recommendations(general_recommendations)
        elif db_type == "postgresql":
            return self._get_postgresql_recommendations(general_recommendations)
        elif db_type == "hdfs":
            return self._get_hdfs_recommendations(general_recommendations)
        else:
            return {}
    
    def _get_clickhouse_recommendations(self, recommendations: List[StorageRecommendation]) -> Dict[str, Any]:
        """Генерирует рекомендации специфичные для ClickHouse."""
        
        clickhouse_config = {}
        
        for rec in recommendations:
            if rec.recommendation_type == RecommendationType.PARTITIONING:
                if rec.recommended_value == "monthly":
                    clickhouse_config["partition_by"] = f"toYYYYMM({rec.target})"
                elif rec.recommended_value == "categorical":
                    clickhouse_config["partition_by"] = rec.target
                    
            elif rec.recommendation_type == RecommendationType.INDEXING:
                if "order_by" not in clickhouse_config:
                    clickhouse_config["order_by"] = []
                clickhouse_config["order_by"].append(rec.target)
                
            elif rec.recommendation_type == RecommendationType.COMPRESSION:
                clickhouse_config["compression"] = rec.recommended_value.upper()
        
        return clickhouse_config
    
    def _get_postgresql_recommendations(self, recommendations: List[StorageRecommendation]) -> Dict[str, Any]:
        """Генерирует рекомендации специфичные для PostgreSQL."""
        
        postgresql_config = {}
        
        for rec in recommendations:
            if rec.recommendation_type == RecommendationType.PARTITIONING:
                if rec.recommended_value == "monthly":
                    postgresql_config["partition_by"] = f"RANGE ({rec.target})"
                elif rec.recommended_value == "categorical":
                    postgresql_config["partition_by"] = f"LIST ({rec.target})"
                    
            elif rec.recommendation_type == RecommendationType.INDEXING:
                if "indexes" not in postgresql_config:
                    postgresql_config["indexes"] = []
                postgresql_config["indexes"].append(rec.target)
        
        return postgresql_config
    
    def _get_hdfs_recommendations(self, recommendations: List[StorageRecommendation]) -> Dict[str, Any]:
        """Генерирует рекомендации специфичные для HDFS."""
        
        hdfs_config = {
            "format": "parquet",  # По умолчанию Parquet для HDFS
            "compression": {"type": "snappy", "block_size": "128MB"}
        }
        
        for rec in recommendations:
            if rec.recommendation_type == RecommendationType.PARTITIONING:
                hdfs_config["partition_by"] = rec.target
                
            elif rec.recommendation_type == RecommendationType.COMPRESSION:
                if rec.recommended_value == "lz4":
                    hdfs_config["compression"]["type"] = "lz4"
                elif rec.recommended_value == "zstd":
                    hdfs_config["compression"]["type"] = "zstd"
        
        return hdfs_config
