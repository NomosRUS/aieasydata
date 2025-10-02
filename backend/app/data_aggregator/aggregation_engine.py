"""
Движок для выполнения сложных агрегаций данных.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
from pathlib import Path

from .schemas import (
    AggregationRule, 
    AggregationType,
    JoinRule, 
    GroupByRule, 
    WindowRule, 
    UnionRule,
    EnrichmentRule,
    EnrichmentType,
    DataSource,
    ExecutionStats
)
from .data_source_collector import DataSourceCollector

logger = logging.getLogger(__name__)


class AggregationEngine:
    """Движок для выполнения агрегаций и обогащения данных."""
    
    def __init__(self):
        self.data_collector = DataSourceCollector()
        
    async def execute_aggregation_scenario(self, sources: List[DataSource], 
                                         aggregations: List[AggregationRule],
                                         enrichments: List[EnrichmentRule]) -> Dict[str, Any]:
        """
        Выполняет полный сценарий агрегации данных.
        
        Args:
            sources: Список источников данных
            aggregations: Правила агрегации
            enrichments: Правила обогащения
            
        Returns:
            Dict: Результат выполнения агрегации
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting aggregation scenario with {len(sources)} sources")
            
            # 1. Загружаем данные из всех источников
            dataframes = {}
            total_input_rows = 0
            
            for source in sources:
                df = await self.data_collector.load_data(source)
                dataframes[source.source_id] = df
                total_input_rows += len(df)
                logger.info(f"Loaded {len(df)} rows from {source.source_id}")
            
            # 2. Выполняем агрегации в порядке их определения
            result_df = None
            for i, aggregation in enumerate(aggregations):
                logger.info(f"Executing aggregation {i+1}/{len(aggregations)}: {aggregation.type}")
                
                if aggregation.type == AggregationType.JOIN:
                    result_df = await self._execute_join(dataframes, aggregation.parameters, result_df)
                elif aggregation.type == AggregationType.GROUP_BY:
                    result_df = await self._execute_group_by(result_df or dataframes, aggregation.parameters)
                elif aggregation.type == AggregationType.WINDOW:
                    result_df = await self._execute_window_function(result_df or dataframes, aggregation.parameters)
                elif aggregation.type == AggregationType.UNION:
                    result_df = await self._execute_union(dataframes, aggregation.parameters)
                else:
                    raise ValueError(f"Unsupported aggregation type: {aggregation.type}")
            
            # Если не было агрегаций, объединяем все источники
            if result_df is None and len(dataframes) > 1:
                result_df = pd.concat(list(dataframes.values()), ignore_index=True)
            elif result_df is None:
                result_df = list(dataframes.values())[0]
            
            # 3. Применяем обогащения
            if enrichments:
                result_df = await self._apply_enrichments(result_df, enrichments)
            
            # 4. Вычисляем статистику выполнения
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds() * 1000
            
            execution_stats = ExecutionStats(
                processing_time_ms=int(processing_time),
                input_rows=total_input_rows,
                output_rows=len(result_df),
                data_reduction_ratio=len(result_df) / max(total_input_rows, 1),
                memory_usage_mb=result_df.memory_usage(deep=True).sum() / (1024 * 1024)
            )
            
            return {
                "success": True,
                "result_dataframe": result_df,
                "execution_stats": execution_stats,
                "completed_at": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Aggregation scenario failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            }
    
    async def _execute_join(self, dataframes: Dict[str, pd.DataFrame], 
                          join_rule: JoinRule, current_result: Optional[pd.DataFrame]) -> pd.DataFrame:
        """Выполняет JOIN операцию."""
        
        # Получаем левый DataFrame
        if current_result is not None:
            left_df = current_result
        else:
            left_df = dataframes[join_rule.left_source]
        
        # Получаем правый DataFrame
        right_df = dataframes[join_rule.right_source]
        
        # Подготавливаем ключи соединения
        left_keys = list(join_rule.join_keys.keys())
        right_keys = list(join_rule.join_keys.values())
        
        # Переименовываем колонки в правом DataFrame если нужно
        right_df_prepared = right_df.copy()
        rename_mapping = {}
        for left_key, right_key in join_rule.join_keys.items():
            if left_key != right_key:
                rename_mapping[right_key] = left_key
        
        if rename_mapping:
            right_df_prepared = right_df_prepared.rename(columns=rename_mapping)
        
        # Определяем тип JOIN
        how_mapping = {
            "inner": "inner",
            "left": "left", 
            "right": "right",
            "full": "outer"
        }
        
        how = how_mapping.get(join_rule.join_type.value, "inner")
        
        # Выполняем JOIN
        result_df = left_df.merge(
            right_df_prepared,
            on=left_keys,
            how=how,
            suffixes=('', f'_{join_rule.right_source}')
        )
        
        # Применяем дополнительные условия если есть
        if join_rule.conditions:
            for condition in join_rule.conditions:
                try:
                    # Простая реализация условий через query
                    result_df = result_df.query(condition)
                except Exception as e:
                    logger.warning(f"Failed to apply condition '{condition}': {str(e)}")
        
        logger.info(f"JOIN result: {len(result_df)} rows")
        return result_df
    
    async def _execute_group_by(self, dataframes: Union[Dict[str, pd.DataFrame], pd.DataFrame], 
                              group_rule: GroupByRule) -> pd.DataFrame:
        """Выполняет GROUP BY агрегацию."""
        
        # Получаем DataFrame для группировки
        if isinstance(dataframes, dict):
            # Если несколько источников, объединяем их
            df = pd.concat(list(dataframes.values()), ignore_index=True)
        else:
            df = dataframes
        
        # Проверяем наличие колонок для группировки
        missing_columns = [col for col in group_rule.columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing columns for GROUP BY: {missing_columns}")
        
        # Выполняем группировку
        grouped = df.groupby(group_rule.columns)
        
        # Применяем агрегатные функции
        agg_dict = {}
        for alias, expression in group_rule.aggregates.items():
            try:
                # Парсим выражение агрегации
                agg_func, column = self._parse_aggregate_expression(expression)
                
                if column not in df.columns:
                    logger.warning(f"Column '{column}' not found for aggregation '{alias}'")
                    continue
                
                if column not in agg_dict:
                    agg_dict[column] = []
                agg_dict[column].append(agg_func)
                
            except Exception as e:
                logger.error(f"Failed to parse aggregate expression '{expression}': {str(e)}")
                continue
        
        # Выполняем агрегацию
        if agg_dict:
            result_df = grouped.agg(agg_dict).reset_index()
            
            # Переименовываем колонки согласно алиасам
            column_mapping = {}
            for alias, expression in group_rule.aggregates.items():
                try:
                    agg_func, column = self._parse_aggregate_expression(expression)
                    old_name = (column, agg_func)
                    if old_name in result_df.columns:
                        column_mapping[old_name] = alias
                except:
                    continue
            
            if column_mapping:
                result_df = result_df.rename(columns=column_mapping)
        else:
            # Если нет агрегатных функций, просто группируем
            result_df = df.groupby(group_rule.columns).size().reset_index(name='count')
        
        # Применяем условия HAVING если есть
        if group_rule.having:
            for condition in group_rule.having:
                try:
                    result_df = result_df.query(condition)
                except Exception as e:
                    logger.warning(f"Failed to apply HAVING condition '{condition}': {str(e)}")
        
        logger.info(f"GROUP BY result: {len(result_df)} rows")
        return result_df
    
    async def _execute_window_function(self, dataframes: Union[Dict[str, pd.DataFrame], pd.DataFrame],
                                     window_rule: WindowRule) -> pd.DataFrame:
        """Выполняет оконную функцию."""
        
        # Получаем DataFrame
        if isinstance(dataframes, dict):
            df = pd.concat(list(dataframes.values()), ignore_index=True)
        else:
            df = dataframes.copy()
        
        # Проверяем наличие колонок
        required_columns = window_rule.partition_by + (window_rule.order_by or [])
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing columns for window function: {missing_columns}")
        
        # Выполняем оконную функцию
        try:
            if window_rule.order_by:
                # Сортируем по указанным колонкам
                df = df.sort_values(window_rule.order_by)
            
            # Создаем группировку для PARTITION BY
            if window_rule.partition_by:
                grouped = df.groupby(window_rule.partition_by)
            else:
                # Если нет PARTITION BY, работаем со всем DataFrame
                grouped = df.groupby(lambda x: 0)  # Все строки в одной группе
            
            # Применяем оконную функцию
            if window_rule.function.upper().startswith('ROW_NUMBER'):
                df[window_rule.alias] = grouped.cumcount() + 1
            elif window_rule.function.upper().startswith('RANK'):
                # Упрощенная реализация RANK
                df[window_rule.alias] = grouped.cumcount() + 1
            elif window_rule.function.upper().startswith('LAG'):
                # Упрощенная реализация LAG
                df[window_rule.alias] = grouped.shift(1)
            elif window_rule.function.upper().startswith('LEAD'):
                # Упрощенная реализация LEAD
                df[window_rule.alias] = grouped.shift(-1)
            else:
                logger.warning(f"Unsupported window function: {window_rule.function}")
                df[window_rule.alias] = 0
            
        except Exception as e:
            logger.error(f"Window function execution failed: {str(e)}")
            df[window_rule.alias] = None
        
        logger.info(f"Window function result: {len(df)} rows")
        return df
    
    async def _execute_union(self, dataframes: Dict[str, pd.DataFrame], 
                           union_rule: UnionRule) -> pd.DataFrame:
        """Выполняет UNION операцию."""
        
        # Получаем DataFrame для объединения
        dfs_to_union = []
        for source_id in union_rule.sources:
            if source_id in dataframes:
                dfs_to_union.append(dataframes[source_id])
            else:
                logger.warning(f"Source '{source_id}' not found for UNION")
        
        if not dfs_to_union:
            raise ValueError("No valid sources found for UNION")
        
        # Выполняем UNION
        if union_rule.union_type == "union":
            # UNION (удаляем дубликаты)
            result_df = pd.concat(dfs_to_union, ignore_index=True).drop_duplicates()
        else:
            # UNION ALL (оставляем дубликаты)
            result_df = pd.concat(dfs_to_union, ignore_index=True)
        
        logger.info(f"UNION result: {len(result_df)} rows")
        return result_df
    
    async def _apply_enrichments(self, df: pd.DataFrame, 
                               enrichments: List[EnrichmentRule]) -> pd.DataFrame:
        """Применяет правила обогащения данных."""
        
        result_df = df.copy()
        
        for enrichment in enrichments:
            try:
                if enrichment.type == EnrichmentType.CALCULATED_FIELD:
                    # Вычисляемое поле
                    result_df[enrichment.name] = result_df.eval(enrichment.expression)
                    
                elif enrichment.type == EnrichmentType.TRANSFORMATION:
                    # Трансформация существующего поля
                    if enrichment.name in result_df.columns:
                        result_df[enrichment.name] = result_df.eval(enrichment.expression)
                    else:
                        logger.warning(f"Column '{enrichment.name}' not found for transformation")
                        
                elif enrichment.type == EnrichmentType.LOOKUP:
                    # Lookup (упрощенная реализация)
                    logger.warning(f"LOOKUP enrichment not fully implemented: {enrichment.name}")
                    result_df[enrichment.name] = None
                    
                logger.info(f"Applied enrichment: {enrichment.name}")
                
            except Exception as e:
                logger.error(f"Failed to apply enrichment '{enrichment.name}': {str(e)}")
                # Добавляем колонку с NULL значениями в случае ошибки
                result_df[enrichment.name] = None
        
        return result_df
    
    def _parse_aggregate_expression(self, expression: str) -> tuple:
        """
        Парсит выражение агрегатной функции.
        
        Args:
            expression: Выражение типа "SUM(amount)" или "COUNT(DISTINCT customer_id)"
            
        Returns:
            tuple: (функция, колонка)
        """
        expression = expression.strip().upper()
        
        # Простой парсинг основных агрегатных функций
        if expression.startswith('SUM(') and expression.endswith(')'):
            column = expression[4:-1].strip()
            return 'sum', column
        elif expression.startswith('COUNT(') and expression.endswith(')'):
            column = expression[6:-1].strip()
            if column.startswith('DISTINCT '):
                column = column[9:].strip()
                return 'nunique', column
            else:
                return 'count', column
        elif expression.startswith('AVG(') and expression.endswith(')'):
            column = expression[4:-1].strip()
            return 'mean', column
        elif expression.startswith('MIN(') and expression.endswith(')'):
            column = expression[4:-1].strip()
            return 'min', column
        elif expression.startswith('MAX(') and expression.endswith(')'):
            column = expression[4:-1].strip()
            return 'max', column
        elif expression.startswith('STD(') and expression.endswith(')'):
            column = expression[4:-1].strip()
            return 'std', column
        else:
            # Если не удалось распарсить, возвращаем как есть
            return 'first', expression
    
    def generate_sql_preview(self, sources: List[DataSource], 
                           aggregations: List[AggregationRule],
                           target_db_type: str = "postgresql") -> str:
        """
        Генерирует SQL запрос для предварительного просмотра агрегации.
        
        Args:
            sources: Источники данных
            aggregations: Правила агрегации
            target_db_type: Целевая СУБД
            
        Returns:
            str: SQL запрос
        """
        try:
            sql_parts = []
            
            # Базовый SELECT для первого источника
            main_source = sources[0]
            sql_parts.append(f"SELECT {', '.join(main_source.selected_columns)}")
            sql_parts.append(f"FROM {main_source.table or main_source.path}")
            
            # Добавляем JOIN если есть
            for aggregation in aggregations:
                if aggregation.type == AggregationType.JOIN:
                    join_rule = aggregation.parameters
                    right_source = next(s for s in sources if s.source_id == join_rule.right_source)
                    
                    join_type = join_rule.join_type.value.upper()
                    sql_parts.append(f"{join_type} JOIN {right_source.table or right_source.path}")
                    
                    # Условия JOIN
                    join_conditions = []
                    for left_key, right_key in join_rule.join_keys.items():
                        join_conditions.append(f"{main_source.table}.{left_key} = {right_source.table}.{right_key}")
                    
                    sql_parts.append(f"ON {' AND '.join(join_conditions)}")
            
            # Добавляем GROUP BY если есть
            for aggregation in aggregations:
                if aggregation.type == AggregationType.GROUP_BY:
                    group_rule = aggregation.parameters
                    sql_parts.append(f"GROUP BY {', '.join(group_rule.columns)}")
                    
                    if group_rule.having:
                        sql_parts.append(f"HAVING {' AND '.join(group_rule.having)}")
            
            return '\n'.join(sql_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate SQL preview: {str(e)}")
            return f"-- SQL generation failed: {str(e)}"
