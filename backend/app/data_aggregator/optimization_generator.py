"""
Генератор оптимизаций для агрегированных данных.
"""

import pandas as pd
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import re

from .schemas import (
    OptimizationRecommendation,
    AggregationRule,
    AggregationType,
    JoinRule,
    GroupByRule,
    DataSource,
    TargetRequirements
)

logger = logging.getLogger(__name__)


class OptimizationGenerator:
    """Генератор рекомендаций по оптимизации для агрегированных данных."""
    
    def __init__(self):
        self.date_patterns = [
            r'.*date.*', r'.*time.*', r'.*created.*', r'.*updated.*',
            r'.*timestamp.*', r'.*dt.*', r'.*_at$'
        ]
        self.id_patterns = [
            r'.*_id$', r'^id$', r'.*key.*', r'.*uuid.*'
        ]
        
    def generate_optimizations(self, 
                             result_df: pd.DataFrame,
                             aggregations: List[AggregationRule],
                             sources: List[DataSource],
                             target_requirements: TargetRequirements,
                             table_name: str) -> List[OptimizationRecommendation]:
        """
        Генерирует рекомендации по оптимизации для агрегированных данных.
        
        Args:
            result_df: Результирующий DataFrame
            aggregations: Примененные агрегации
            sources: Источники данных
            target_requirements: Требования к целевой системе
            table_name: Имя целевой таблицы
            
        Returns:
            List[OptimizationRecommendation]: Список рекомендаций
        """
        recommendations = []
        
        try:
            # 1. Анализируем структуру данных
            data_analysis = self._analyze_data_structure(result_df)
            
            # 2. Генерируем рекомендации по партиционированию
            partition_recs = self._generate_partition_recommendations(
                result_df, aggregations, target_requirements, table_name, data_analysis
            )
            recommendations.extend(partition_recs)
            
            # 3. Генерируем рекомендации по индексам
            index_recs = self._generate_index_recommendations(
                result_df, aggregations, target_requirements, table_name, data_analysis
            )
            recommendations.extend(index_recs)
            
            # 4. Генерируем рекомендации по сжатию
            compression_recs = self._generate_compression_recommendations(
                result_df, target_requirements, table_name, data_analysis
            )
            recommendations.extend(compression_recs)
            
            # 5. Генерируем рекомендации по сортировке (для ClickHouse)
            if target_requirements.target_db_type == "clickhouse":
                order_recs = self._generate_order_by_recommendations(
                    result_df, aggregations, table_name, data_analysis
                )
                recommendations.extend(order_recs)
            
            logger.info(f"Generated {len(recommendations)} optimization recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating optimizations: {str(e)}")
            return []
    
    def _analyze_data_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Анализирует структуру данных для оптимизации."""
        
        analysis = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "columns": {}
        }
        
        for column in df.columns:
            col_analysis = {
                "name": column,
                "dtype": str(df[column].dtype),
                "null_count": int(df[column].isnull().sum()),
                "unique_count": int(df[column].nunique()),
                "cardinality": df[column].nunique() / len(df) if len(df) > 0 else 0,
                "is_date_like": self._is_date_column(column, df[column]),
                "is_id_like": self._is_id_column(column),
                "is_categorical": self._is_categorical_column(df[column]),
                "memory_usage_mb": df[column].memory_usage(deep=True) / (1024 * 1024)
            }
            
            analysis["columns"][column] = col_analysis
        
        return analysis
    
    def _is_date_column(self, column_name: str, series: pd.Series) -> bool:
        """Определяет, является ли колонка датой."""
        # Проверяем по имени
        for pattern in self.date_patterns:
            if re.match(pattern, column_name.lower()):
                return True
        
        # Проверяем по типу данных
        if pd.api.types.is_datetime64_any_dtype(series):
            return True
            
        return False
    
    def _is_id_column(self, column_name: str) -> bool:
        """Определяет, является ли колонка идентификатором."""
        for pattern in self.id_patterns:
            if re.match(pattern, column_name.lower()):
                return True
        return False
    
    def _is_categorical_column(self, series: pd.Series) -> bool:
        """Определяет, является ли колонка категориальной."""
        if len(series) == 0:
            return False
            
        # Если уникальных значений мало относительно общего количества
        cardinality = series.nunique() / len(series)
        
        # Категориальная если:
        # 1. Строковый тип и низкая кардинальность
        # 2. Или очень мало уникальных значений
        if (pd.api.types.is_string_dtype(series) and cardinality < 0.1) or \
           (series.nunique() < 50 and cardinality < 0.5):
            return True
            
        return False
    
    def _generate_partition_recommendations(self, 
                                         df: pd.DataFrame,
                                         aggregations: List[AggregationRule],
                                         target_requirements: TargetRequirements,
                                         table_name: str,
                                         data_analysis: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Генерирует рекомендации по партиционированию."""
        recommendations = []
        
        # Партиционирование имеет смысл только для больших таблиц
        if data_analysis["row_count"] < 100000:
            return recommendations
        
        # Ищем подходящие колонки для партиционирования
        partition_candidates = []
        
        for col_name, col_info in data_analysis["columns"].items():
            # Датные колонки - отличные кандидаты для партиционирования
            if col_info["is_date_like"]:
                partition_candidates.append({
                    "column": col_name,
                    "type": "date",
                    "priority": "high",
                    "reasoning": f"Date column '{col_name}' is ideal for time-based partitioning"
                })
            
            # Категориальные колонки с умеренной кардинальностью
            elif col_info["is_categorical"] and 5 <= col_info["unique_count"] <= 100:
                partition_candidates.append({
                    "column": col_name,
                    "type": "categorical",
                    "priority": "medium",
                    "reasoning": f"Categorical column '{col_name}' with {col_info['unique_count']} values"
                })
        
        # Генерируем рекомендации для каждого кандидата
        for candidate in partition_candidates[:2]:  # Максимум 2 рекомендации
            
            if target_requirements.target_db_type == "clickhouse":
                if candidate["type"] == "date":
                    partition_expr = f"toYYYYMM({candidate['column']})"
                else:
                    partition_expr = candidate['column']
                    
            elif target_requirements.target_db_type == "postgres":
                if candidate["type"] == "date":
                    partition_expr = f"RANGE ({candidate['column']})"
                else:
                    partition_expr = f"LIST ({candidate['column']})"
                    
            elif target_requirements.target_db_type == "hdfs":
                partition_expr = candidate['column']
            else:
                continue
            
            recommendations.append(OptimizationRecommendation(
                type="partition",
                target=candidate['column'],
                reasoning=candidate['reasoning'],
                priority=candidate['priority'],
                estimated_improvement=self._estimate_partition_improvement(
                    data_analysis, candidate['column']
                )
            ))
        
        return recommendations
    
    def _generate_index_recommendations(self,
                                      df: pd.DataFrame,
                                      aggregations: List[AggregationRule],
                                      target_requirements: TargetRequirements,
                                      table_name: str,
                                      data_analysis: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Генерирует рекомендации по индексам."""
        recommendations = []
        
        # Для HDFS индексы не применимы
        if target_requirements.target_db_type == "hdfs":
            return recommendations
        
        index_candidates = set()
        
        # 1. Анализируем JOIN ключи из агрегаций
        for aggregation in aggregations:
            if aggregation.type == AggregationType.JOIN:
                join_rule = aggregation.parameters
                for left_key, right_key in join_rule.join_keys.items():
                    if left_key in df.columns:
                        index_candidates.add(left_key)
        
        # 2. Анализируем GROUP BY колонки
        for aggregation in aggregations:
            if aggregation.type == AggregationType.GROUP_BY:
                group_rule = aggregation.parameters
                for column in group_rule.columns:
                    if column in df.columns:
                        index_candidates.add(column)
        
        # 3. Добавляем ID колонки (высокий приоритет)
        for col_name, col_info in data_analysis["columns"].items():
            if col_info["is_id_like"] and col_info["cardinality"] > 0.8:
                index_candidates.add(col_name)
        
        # 4. Добавляем часто используемые колонки
        for col_name, col_info in data_analysis["columns"].items():
            # Колонки с высокой кардинальностью хорошо подходят для индексов
            if 0.1 < col_info["cardinality"] < 0.9 and col_info["unique_count"] > 100:
                index_candidates.add(col_name)
        
        # Генерируем рекомендации
        for column in list(index_candidates)[:5]:  # Максимум 5 индексов
            col_info = data_analysis["columns"][column]
            
            # Определяем приоритет
            if col_info["is_id_like"]:
                priority = "high"
                reasoning = f"ID column '{column}' with high cardinality"
            elif column in [agg.parameters.columns[0] if hasattr(agg.parameters, 'columns') and agg.parameters.columns else '' 
                          for agg in aggregations if agg.type == AggregationType.GROUP_BY]:
                priority = "high"
                reasoning = f"Column '{column}' used in GROUP BY operations"
            else:
                priority = "medium"
                reasoning = f"Column '{column}' with good selectivity ({col_info['cardinality']:.2f})"
            
            recommendations.append(OptimizationRecommendation(
                type="index",
                target=column,
                reasoning=reasoning,
                priority=priority,
                estimated_improvement=self._estimate_index_improvement(col_info)
            ))
        
        return recommendations
    
    def _generate_compression_recommendations(self,
                                           df: pd.DataFrame,
                                           target_requirements: TargetRequirements,
                                           table_name: str,
                                           data_analysis: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Генерирует рекомендации по сжатию."""
        recommendations = []
        
        # Сжатие имеет смысл для больших таблиц
        if data_analysis["memory_usage_mb"] < 10:  # Меньше 10 МБ
            return recommendations
        
        compression_benefit = 0
        reasoning_parts = []
        
        # Анализируем типы данных для оценки эффективности сжатия
        for col_name, col_info in data_analysis["columns"].items():
            if col_info["is_categorical"]:
                compression_benefit += 0.3  # Категориальные данные хорошо сжимаются
                reasoning_parts.append(f"categorical column '{col_name}'")
            
            if pd.api.types.is_string_dtype(df[col_name]):
                compression_benefit += 0.2  # Строки обычно хорошо сжимаются
                reasoning_parts.append(f"string column '{col_name}'")
        
        if compression_benefit > 0.5:  # Если ожидается хорошее сжатие
            
            if target_requirements.target_db_type == "clickhouse":
                compression_type = "LZ4"
            elif target_requirements.target_db_type == "hdfs":
                compression_type = "snappy"
            else:
                compression_type = "gzip"
            
            reasoning = f"Table has {reasoning_parts[:3]} that compress well with {compression_type}"
            
            recommendations.append(OptimizationRecommendation(
                type="compression",
                target=table_name,
                reasoning=reasoning,
                priority="medium",
                estimated_improvement=min(compression_benefit * 50, 70)  # До 70% экономии места
            ))
        
        return recommendations
    
    def _generate_order_by_recommendations(self,
                                         df: pd.DataFrame,
                                         aggregations: List[AggregationRule],
                                         table_name: str,
                                         data_analysis: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Генерирует рекомендации по ORDER BY для ClickHouse."""
        recommendations = []
        
        order_candidates = []
        
        # 1. Датные колонки - отличный выбор для ORDER BY
        for col_name, col_info in data_analysis["columns"].items():
            if col_info["is_date_like"]:
                order_candidates.append({
                    "column": col_name,
                    "priority": "high",
                    "reasoning": f"Date column '{col_name}' for time-series queries"
                })
        
        # 2. ID колонки
        for col_name, col_info in data_analysis["columns"].items():
            if col_info["is_id_like"] and col_info["cardinality"] > 0.8:
                order_candidates.append({
                    "column": col_name,
                    "priority": "high",
                    "reasoning": f"ID column '{col_name}' for point queries"
                })
        
        # 3. Колонки из GROUP BY
        for aggregation in aggregations:
            if aggregation.type == AggregationType.GROUP_BY:
                group_rule = aggregation.parameters
                for column in group_rule.columns:
                    if column in df.columns:
                        order_candidates.append({
                            "column": column,
                            "priority": "medium",
                            "reasoning": f"Column '{column}' used in GROUP BY operations"
                        })
        
        # Выбираем лучшие кандидаты (максимум 3 колонки в ORDER BY)
        if order_candidates:
            # Убираем дубликаты и сортируем по приоритету
            unique_candidates = {}
            for candidate in order_candidates:
                col = candidate["column"]
                if col not in unique_candidates or candidate["priority"] == "high":
                    unique_candidates[col] = candidate
            
            selected_columns = list(unique_candidates.keys())[:3]
            
            if selected_columns:
                order_expr = f"({', '.join(selected_columns)})"
                reasoning = f"Optimal sort order for columns: {', '.join(selected_columns)}"
                
                recommendations.append(OptimizationRecommendation(
                    type="order_by",
                    target=order_expr,
                    reasoning=reasoning,
                    priority="high",
                    estimated_improvement=25.0  # ORDER BY может значительно ускорить запросы
                ))
        
        return recommendations
    
    def _estimate_partition_improvement(self, data_analysis: Dict[str, Any], column: str) -> float:
        """Оценивает улучшение производительности от партиционирования."""
        col_info = data_analysis["columns"][column]
        
        # Базовая оценка зависит от размера данных и кардинальности
        base_improvement = min(data_analysis["row_count"] / 100000 * 10, 50)
        
        # Бонус для датных колонок
        if col_info["is_date_like"]:
            base_improvement *= 1.5
        
        # Штраф за слишком высокую или низкую кардинальность
        if col_info["cardinality"] < 0.01 or col_info["cardinality"] > 0.5:
            base_improvement *= 0.7
        
        return min(base_improvement, 80)  # Максимум 80% улучшения
    
    def _estimate_index_improvement(self, col_info: Dict[str, Any]) -> float:
        """Оценивает улучшение производительности от индекса."""
        # Базовая оценка зависит от кардинальности
        if col_info["cardinality"] > 0.8:  # Высокая селективность
            return 60.0
        elif col_info["cardinality"] > 0.3:  # Средняя селективность
            return 40.0
        else:  # Низкая селективность
            return 20.0
    
    def generate_ddl_optimizations(self, 
                                 recommendations: List[OptimizationRecommendation],
                                 target_db_type: str,
                                 table_name: str) -> Dict[str, Any]:
        """
        Генерирует DDL оптимизации в формате, совместимом с модулем 4.
        
        Args:
            recommendations: Список рекомендаций
            target_db_type: Целевая СУБД
            table_name: Имя таблицы
            
        Returns:
            Dict: Оптимизации в формате модуля 4
        """
        optimizations = {}
        
        for rec in recommendations:
            if rec.type == "partition":
                if target_db_type == "clickhouse":
                    if rec.target and any(pattern in rec.target.lower() for pattern in ['date', 'time', 'created', 'updated']):
                        optimizations["partition_by"] = f"toYYYYMM({rec.target})"
                    else:
                        optimizations["partition_by"] = rec.target
                elif target_db_type == "postgres":
                    optimizations["partition_by"] = f"RANGE ({rec.target})"
                elif target_db_type == "hdfs":
                    optimizations["partition_by"] = rec.target
            
            elif rec.type == "index":
                if "indexes" not in optimizations:
                    optimizations["indexes"] = []
                optimizations["indexes"].append(rec.target)
            
            elif rec.type == "order_by" and target_db_type == "clickhouse":
                # Парсим выражение ORDER BY
                if rec.target.startswith('(') and rec.target.endswith(')'):
                    columns = [col.strip() for col in rec.target[1:-1].split(',')]
                    optimizations["order_by"] = columns
                else:
                    optimizations["order_by"] = [rec.target]
            
            elif rec.type == "compression":
                if target_db_type == "clickhouse":
                    optimizations["compression"] = "LZ4"
                elif target_db_type == "hdfs":
                    optimizations["compression"] = {
                        "type": "snappy",
                        "block_size": "128MB"
                    }
        
        return optimizations
