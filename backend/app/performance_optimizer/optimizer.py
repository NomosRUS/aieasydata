"""
Генератор оптимизаций для Модуля 3
Создание DDL-скриптов и рекомендаций по оптимизации производительности
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .schemas import (
    PerformanceAnalysisResult,
    PerformanceMetrics,
    OptimizationRecommendation,
    RecommendationType,
    Priority,
    SourceType
)
from ..agent import get_llm_response

logger = logging.getLogger(__name__)


class OptimizationGenerator:
    """
    Генератор рекомендаций по оптимизации производительности
    """
    
    def __init__(self):
        self.ddl_templates = self._load_ddl_templates()
    
    def generate_recommendations(
        self, 
        analysis_result: PerformanceAnalysisResult,
        target_db_type: Optional[str] = None
    ) -> List[OptimizationRecommendation]:
        """
        Генерация рекомендаций по оптимизации на основе анализа
        
        Args:
            analysis_result: Результат анализа производительности
            target_db_type: Целевая СУБД (clickhouse, postgres, hdfs)
            
        Returns:
            List[OptimizationRecommendation]: Список рекомендаций
        """
        recommendations = []
        
        if not analysis_result.current_metrics:
            logger.warning("Нет метрик для генерации рекомендаций")
            return recommendations
        
        metrics = analysis_result.current_metrics
        
        # Определяем целевую СУБД
        if not target_db_type:
            target_db_type = self._determine_optimal_db_type(metrics)
        
        # Генерируем рекомендации по партиционированию
        partition_rec = self._generate_partition_recommendation(metrics, target_db_type, analysis_result.source)
        if partition_rec:
            recommendations.append(partition_rec)
        
        # Генерируем рекомендации по индексам
        index_recs = self._generate_index_recommendations(metrics, target_db_type, analysis_result.source)
        recommendations.extend(index_recs)
        
        # Генерируем рекомендации по сжатию
        compression_rec = self._generate_compression_recommendation(metrics, target_db_type, analysis_result.source)
        if compression_rec:
            recommendations.append(compression_rec)
        
        # Генерируем рекомендации по ORDER BY (для ClickHouse)
        if target_db_type == "clickhouse":
            order_by_rec = self._generate_order_by_recommendation(metrics, analysis_result.source)
            if order_by_rec:
                recommendations.append(order_by_rec)
        
        # Генерируем рекомендации по реструктуризации
        restructure_rec = self._generate_restructure_recommendation(metrics, target_db_type, analysis_result.source)
        if restructure_rec:
            recommendations.append(restructure_rec)
        
        logger.info(f"Сгенерировано {len(recommendations)} рекомендаций для {analysis_result.source}")
        return recommendations
    
    def _determine_optimal_db_type(self, metrics: PerformanceMetrics) -> str:
        """
        Определение оптимальной СУБД на основе метрик
        """
        # Логика выбора СУБД (упрощенная версия из Модуля 4)
        if metrics.data_size_bytes > 10_000_000_000:  # > 10GB
            return "hdfs"
        elif metrics.row_count > 100_000_000:  # > 100M строк
            return "clickhouse"
        else:
            return "postgres"
    
    def _generate_partition_recommendation(
        self, 
        metrics: PerformanceMetrics, 
        target_db_type: str, 
        source: str
    ) -> Optional[OptimizationRecommendation]:
        """
        Генерация рекомендации по партиционированию
        """
        # Партиционирование нужно для больших таблиц
        if metrics.row_count < 1_000_000:  # < 1M строк
            return None
        
        table_name = self._extract_table_name(source)
        
        # Определяем колонку для партиционирования из структуры
        partition_column = self._find_partition_column(metrics.structure_info)
        if not partition_column:
            return None
        
        # Генерируем DDL в зависимости от СУБД
        if target_db_type == "clickhouse":
            ddl_script, details = self._generate_clickhouse_partition_ddl(table_name, partition_column)
        elif target_db_type == "postgres":
            ddl_script, details = self._generate_postgres_partition_ddl(table_name, partition_column)
        elif target_db_type == "hdfs":
            ddl_script, details = self._generate_hdfs_partition_ddl(table_name, partition_column)
        else:
            return None
        
        # Оценка улучшения производительности
        estimated_improvement = self._estimate_partition_improvement(metrics)
        
        return OptimizationRecommendation(
            recommendation_type=RecommendationType.PARTITION,
            target_table=table_name,
            target_db_type=target_db_type,
            ddl_script=ddl_script,
            recommendation_details=details,
            estimated_improvement=estimated_improvement,
            reasoning=f"Партиционирование по {partition_column} улучшит производительность запросов с фильтрацией по этому полю",
            priority=Priority.HIGH if metrics.row_count > 10_000_000 else Priority.MEDIUM
        )
    
    def _generate_index_recommendations(
        self, 
        metrics: PerformanceMetrics, 
        target_db_type: str, 
        source: str
    ) -> List[OptimizationRecommendation]:
        """
        Генерация рекомендаций по индексам
        """
        recommendations = []
        table_name = self._extract_table_name(source)
        
        # Находим колонки для индексирования
        index_columns = self._find_index_columns(metrics.structure_info)
        
        for column in index_columns:
            if target_db_type == "postgres":
                ddl_script = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{column} ON {table_name}({column});"
                details = {"indexes": [column]}
            elif target_db_type == "clickhouse":
                # В ClickHouse индексы создаются через INDEX в CREATE TABLE
                ddl_script = f"-- INDEX idx_{column} {column} TYPE minmax GRANULARITY 1"
                details = {"index_type": "minmax", "column": column}
            else:
                continue
            
            estimated_improvement = self._estimate_index_improvement(metrics, column)
            
            recommendations.append(OptimizationRecommendation(
                recommendation_type=RecommendationType.INDEX,
                target_table=table_name,
                target_db_type=target_db_type,
                ddl_script=ddl_script,
                recommendation_details=details,
                estimated_improvement=estimated_improvement,
                reasoning=f"Индекс на колонке {column} ускорит поиск и фильтрацию",
                priority=Priority.MEDIUM
            ))
        
        return recommendations
    
    def _generate_compression_recommendation(
        self, 
        metrics: PerformanceMetrics, 
        target_db_type: str, 
        source: str
    ) -> Optional[OptimizationRecommendation]:
        """
        Генерация рекомендации по сжатию
        """
        # Сжатие актуально для больших данных
        if metrics.data_size_bytes < 100_000_000:  # < 100MB
            return None
        
        table_name = self._extract_table_name(source)
        
        if target_db_type == "clickhouse":
            ddl_script = f"ALTER TABLE {table_name} MODIFY SETTING compress_block_size = 65536;"
            details = {"compression": {"type": "lz4", "block_size": "64KB"}}
        elif target_db_type == "hdfs":
            ddl_script = "-- Compression configured in table properties"
            details = {"compression": {"type": "snappy", "block_size": "128MB"}}
        else:
            return None
        
        estimated_improvement = 30.0  # Примерная оценка сжатия
        
        return OptimizationRecommendation(
            recommendation_type=RecommendationType.COMPRESSION,
            target_table=table_name,
            target_db_type=target_db_type,
            ddl_script=ddl_script,
            recommendation_details=details,
            estimated_improvement=estimated_improvement,
            reasoning="Сжатие данных уменьшит размер хранения и улучшит I/O производительность",
            priority=Priority.LOW
        )
    
    def _generate_order_by_recommendation(
        self, 
        metrics: PerformanceMetrics, 
        source: str
    ) -> Optional[OptimizationRecommendation]:
        """
        Генерация рекомендации по ORDER BY для ClickHouse
        """
        table_name = self._extract_table_name(source)
        
        # Находим оптимальные колонки для сортировки
        order_columns = self._find_order_by_columns(metrics.structure_info)
        if not order_columns:
            return None
        
        order_by_clause = ", ".join(order_columns)
        ddl_script = f"-- ORDER BY ({order_by_clause}) in CREATE TABLE"
        
        details = {"order_by": order_columns}
        estimated_improvement = 20.0
        
        return OptimizationRecommendation(
            recommendation_type=RecommendationType.ORDER_BY,
            target_table=table_name,
            target_db_type="clickhouse",
            ddl_script=ddl_script,
            recommendation_details=details,
            estimated_improvement=estimated_improvement,
            reasoning=f"Сортировка по {order_by_clause} улучшит производительность запросов с фильтрацией",
            priority=Priority.MEDIUM
        )
    
    def _generate_restructure_recommendation(
        self, 
        metrics: PerformanceMetrics, 
        target_db_type: str, 
        source: str
    ) -> Optional[OptimizationRecommendation]:
        """
        Генерация рекомендации по реструктуризации
        """
        # Реструктуризация нужна при неэффективном формате данных
        if metrics.source_type not in [SourceType.CSV, SourceType.JSON, SourceType.XML]:
            return None
        
        if metrics.data_size_bytes < 500_000_000:  # < 500MB
            return None
        
        table_name = self._extract_table_name(source)
        
        if target_db_type == "hdfs":
            ddl_script = f"-- Convert {metrics.source_type.value} to Parquet format"
            details = {"target_format": "parquet", "source_format": metrics.source_type.value}
            estimated_improvement = 50.0
            reasoning = f"Конвертация из {metrics.source_type.value} в Parquet формат значительно улучшит производительность"
        else:
            ddl_script = f"-- Load {metrics.source_type.value} data into {target_db_type} table"
            details = {"target_db": target_db_type, "source_format": metrics.source_type.value}
            estimated_improvement = 40.0
            reasoning = f"Загрузка данных в {target_db_type} улучшит производительность запросов"
        
        return OptimizationRecommendation(
            recommendation_type=RecommendationType.RESTRUCTURE,
            target_table=table_name,
            target_db_type=target_db_type,
            ddl_script=ddl_script,
            recommendation_details=details,
            estimated_improvement=estimated_improvement,
            reasoning=reasoning,
            priority=Priority.HIGH
        )
    
    def _extract_table_name(self, source: str) -> str:
        """
        Извлечение имени таблицы из источника
        """
        # Простая логика извлечения имени таблицы
        if "design_id:" in source:
            return f"table_{source.split(':')[1]}"
        
        # Для файлов - берем имя файла без расширения
        import os
        if os.path.isfile(source) or "/" in source or "\\" in source:
            filename = os.path.basename(source)
            name_without_ext = os.path.splitext(filename)[0]
            return name_without_ext.replace("-", "_").replace(" ", "_")
        
        return "optimized_table"
    
    def _find_partition_column(self, structure_info: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Поиск подходящей колонки для партиционирования
        """
        if not structure_info or "columns" not in structure_info:
            return None
        
        columns = structure_info["columns"]
        
        # Ищем колонки с датой/временем
        for col in columns:
            col_name = col.get("name", "").lower()
            col_type = col.get("type", "").lower()
            
            if any(keyword in col_name for keyword in ["date", "time", "created", "updated"]):
                return col["name"]
            
            if any(keyword in col_type for keyword in ["date", "timestamp", "datetime"]):
                return col["name"]
        
        # Если нет дат, ищем числовые колонки с большой кардинальностью
        for col in columns:
            col_type = col.get("type", "").lower()
            if "int" in col_type or "number" in col_type:
                return col["name"]
        
        return None
    
    def _find_index_columns(self, structure_info: Optional[Dict[str, Any]]) -> List[str]:
        """
        Поиск колонок для индексирования
        """
        if not structure_info or "columns" not in structure_info:
            return []
        
        columns = structure_info["columns"]
        index_columns = []
        
        # Ищем колонки, которые часто используются в WHERE
        for col in columns:
            col_name = col.get("name", "").lower()
            col_type = col.get("type", "").lower()
            
            # ID колонки
            if "id" in col_name:
                index_columns.append(col["name"])
            
            # Внешние ключи
            if col_name.endswith("_id"):
                index_columns.append(col["name"])
            
            # Статусные поля
            if any(keyword in col_name for keyword in ["status", "type", "category"]):
                index_columns.append(col["name"])
        
        return index_columns[:3]  # Ограничиваем количество индексов
    
    def _find_order_by_columns(self, structure_info: Optional[Dict[str, Any]]) -> List[str]:
        """
        Поиск колонок для ORDER BY в ClickHouse
        """
        if not structure_info or "columns" not in structure_info:
            return []
        
        columns = structure_info["columns"]
        order_columns = []
        
        # Сначала ищем дату/время
        for col in columns:
            col_name = col.get("name", "").lower()
            col_type = col.get("type", "").lower()
            
            if any(keyword in col_name for keyword in ["date", "time", "created"]):
                order_columns.append(col["name"])
                break
        
        # Затем добавляем ID или другие часто используемые колонки
        for col in columns:
            col_name = col.get("name", "").lower()
            if "id" in col_name and col["name"] not in order_columns:
                order_columns.append(col["name"])
                break
        
        return order_columns[:2]  # ClickHouse рекомендует не более 2-3 колонок
    
    def _estimate_partition_improvement(self, metrics: PerformanceMetrics) -> float:
        """
        Оценка улучшения от партиционирования
        """
        if metrics.row_count > 100_000_000:
            return 40.0
        elif metrics.row_count > 10_000_000:
            return 25.0
        else:
            return 15.0
    
    def _estimate_index_improvement(self, metrics: PerformanceMetrics, column: str) -> float:
        """
        Оценка улучшения от индекса
        """
        if "id" in column.lower():
            return 30.0
        elif column.lower().endswith("_id"):
            return 25.0
        else:
            return 15.0
    
    def _load_ddl_templates(self) -> Dict[str, str]:
        """
        Загрузка шаблонов DDL
        """
        return {
            "clickhouse_partition": "PARTITION BY {partition_expr}",
            "postgres_partition": "PARTITION BY RANGE ({column})",
            "hdfs_partition": "PARTITIONED BY ({column})"
        }
    
    def _generate_clickhouse_partition_ddl(self, table_name: str, column: str) -> tuple[str, Dict[str, Any]]:
        """
        Генерация DDL партиционирования для ClickHouse
        """
        # Определяем выражение партиционирования на основе типа колонки
        if any(keyword in column.lower() for keyword in ["date", "time"]):
            partition_expr = f"toYYYYMM({column})"
        else:
            partition_expr = f"intHash64({column}) % 10"
        
        ddl = f"-- PARTITION BY {partition_expr} in CREATE TABLE"
        details = {"partition_by": partition_expr}
        
        return ddl, details
    
    def _generate_postgres_partition_ddl(self, table_name: str, column: str) -> tuple[str, Dict[str, Any]]:
        """
        Генерация DDL партиционирования для PostgreSQL
        """
        ddl = f"-- Create partitioned table\nCREATE TABLE {table_name}_partitioned (LIKE {table_name}) PARTITION BY RANGE ({column});"
        details = {"partition_by": f"RANGE ({column})"}
        
        return ddl, details
    
    def _generate_hdfs_partition_ddl(self, table_name: str, column: str) -> tuple[str, Dict[str, Any]]:
        """
        Генерация DDL партиционирования для HDFS
        """
        ddl = f"-- PARTITIONED BY ({column}) in CREATE EXTERNAL TABLE"
        details = {"partition_by": column, "format": "parquet"}
        
        return ddl, details
