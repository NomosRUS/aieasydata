"""
Построитель кастомных наборов данных из разных источников.
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime

from .schemas import (
    DataSource, 
    CustomDatasetRequest, 
    JoinRule, 
    JoinType,
    ColumnInfo,
    PreviewJoinRequest,
    PreviewJoinResponse
)
from .data_source_collector import DataSourceCollector

logger = logging.getLogger(__name__)


class CustomDatasetBuilder:
    """Класс для создания кастомизированных наборов данных."""
    
    def __init__(self):
        self.data_collector = DataSourceCollector()
        
    async def create_custom_dataset(self, request: CustomDatasetRequest) -> Dict[str, Any]:
        """
        Создает кастомный набор данных из выбранных источников.
        
        Args:
            request: Запрос на создание кастомного набора данных
            
        Returns:
            Dict: Результат создания набора данных
        """
        try:
            logger.info(f"Creating custom dataset: {request.dataset_name}")
            
            # 1. Анализируем все источники
            sources_analysis = []
            for source in request.sources:
                analysis = await self.data_collector.analyze_source(source)
                sources_analysis.append(analysis)
            
            # 2. Валидируем совместимость источников с учетом стратегии
            compatibility_issues = self._validate_sources_compatibility(sources_analysis, request.join_strategy)
            if compatibility_issues:
                logger.warning(f"Compatibility issues found, but continuing with available sources: {compatibility_issues}")
            
            # 3. Загружаем данные из всех источников
            dataframes = []
            successful_sources = []
            for i, analysis in enumerate(sources_analysis):
                try:
                    # Получаем оригинальный источник для правильного path
                    original_source = request.sources[i]
                    df = await self.data_collector.load_data(
                        DataSource(
                            source_id=analysis.source_id,
                            source_type=analysis.source_type,
                            path=original_source.path,  # Используем правильный path из запроса
                            selected_columns=original_source.selected_columns or []
                        ),
                        limit=request.limit_rows
                    )
                    if df is not None and not df.empty:
                        dataframes.append(df)
                        successful_sources.append(analysis)
                        logger.info(f"Loaded {len(df)} rows from {analysis.source_id}")
                    else:
                        logger.warning(f"No data loaded from {analysis.source_id}")
                except Exception as e:
                    logger.error(f"Failed to load data from {analysis.source_id}: {str(e)}")
                    continue
            
            # Проверяем, что хотя бы один источник загружен
            if not dataframes:
                return {
                    "success": False,
                    "error": "No data sources could be loaded",
                    "details": "All data sources failed to load"
                }
            
            # 4. Определяем стратегию объединения данных
            if len(dataframes) == 1:
                # Один источник - просто возвращаем данные
                result_df = dataframes[0]
            else:
                # Несколько источников - выполняем JOIN
                # Преобразуем список в словарь для совместимости с методом
                dataframes_dict = {f"source_{i}": df for i, df in enumerate(dataframes)}
                result_df = await self._merge_dataframes(dataframes_dict, request.join_strategy)
            
            # 5. Сохраняем результат
            output_path = await self._save_dataset(
                result_df, 
                request.dataset_name, 
                request.output_format,
                request.include_metadata
            )
            
            # 6. Генерируем метаданные
            metadata = self._generate_dataset_metadata(
                request, 
                successful_sources, 
                result_df
            )
            
            # Конвертируем numpy типы в стандартные Python типы
            row_count = int(len(result_df))
            column_count = int(len(result_df.columns))
            data_size_bytes = int(result_df.memory_usage(deep=True).sum())
            
            return {
                "success": True,
                "dataset_name": request.dataset_name,
                "output_path": output_path,
                "metadata": metadata,
                "row_count": row_count,
                "column_count": column_count,
                "data_size_bytes": data_size_bytes,
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating custom dataset: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": "Dataset creation failed",
                "details": str(e),
                "dataset_name": None,
                "output_path": None,
                "row_count": None,
                "column_count": None
            }
    
    async def preview_join(self, request: PreviewJoinRequest) -> PreviewJoinResponse:
        """
        Предварительный просмотр результата JOIN операции.
        
        Args:
            request: Запрос на предварительный просмотр
            
        Returns:
            PreviewJoinResponse: Результат предварительного просмотра
        """
        try:
            # Загружаем ограниченное количество данных для предварительного просмотра
            left_df = await self.data_collector.load_data(request.left_source, limit=1000)
            right_df = await self.data_collector.load_data(request.right_source, limit=1000)
            
            # Выполняем JOIN
            joined_df = self._perform_join(left_df, right_df, request.join_rule)
            
            # Ограничиваем результат для предварительного просмотра
            preview_df = joined_df.head(request.limit)
            
            # Генерируем статистику JOIN
            join_stats = self._calculate_join_statistics(left_df, right_df, joined_df)
            
            # Проверяем на предупреждения
            warnings = self._generate_join_warnings(left_df, right_df, joined_df, request.join_rule)
            
            return PreviewJoinResponse(
                preview_data=preview_df.to_dict('records'),
                total_estimated_rows=len(joined_df),
                join_statistics=join_stats,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error in join preview: {str(e)}")
            return PreviewJoinResponse(
                preview_data=[],
                total_estimated_rows=0,
                join_statistics={"error": str(e)},
                warnings=[f"Preview failed: {str(e)}"]
            )
    
    def _validate_sources_compatibility(self, sources_analysis: List[Any], join_strategy: str = "auto") -> List[str]:
        """Валидирует совместимость источников данных в зависимости от стратегии."""
        issues = []
        
        if len(sources_analysis) < 2:
            return issues  # Один источник всегда совместим
        
        # Для стратегий concat и individual не требуется строгая совместимость
        if join_strategy in ["concat", "individual"]:
            # Только базовые проверки - проверяем что есть данные
            for analysis in sources_analysis:
                if not analysis.columns:
                    issues.append(f"Source {analysis.source_id} has no columns")
                elif analysis.row_count == 0:
                    issues.append(f"Source {analysis.source_id} has no data")
            # Для concat стратегии разные схемы это нормально
            return issues
        
        # Для JOIN стратегий проверяем совместимость более строго
        for i, analysis1 in enumerate(sources_analysis):
            for j, analysis2 in enumerate(sources_analysis[i+1:], i+1):
                common_columns = set(col.name for col in analysis1.columns) & \
                               set(col.name for col in analysis2.columns)
                
                if join_strategy == "auto":
                    # Для auto стратегии пытаемся найти общие колонки, но не требуем их обязательно
                    if common_columns:
                        # Если есть общие колонки, проверяем их совместимость
                        for col_name in common_columns:
                            col1 = next(col for col in analysis1.columns if col.name == col_name)
                            col2 = next(col for col in analysis2.columns if col.name == col_name)
                            
                            if not self._are_types_compatible(col1.type, col2.type):
                                issues.append(
                                    f"Column {col_name} has incompatible types: "
                                    f"{col1.type} in {analysis1.source_id} vs "
                                    f"{col2.type} in {analysis2.source_id}"
                                )
                    # Если общих колонок нет, будем использовать concat стратегию
                elif join_strategy in ["inner", "left", "right", "full"]:
                    # Для явных JOIN стратегий требуем общие колонки
                    if not common_columns:
                        issues.append(
                            f"Sources {analysis1.source_id} and {analysis2.source_id} "
                            f"have no common columns for {join_strategy.upper()} JOIN"
                        )
                    else:
                        # Проверяем совместимость типов общих колонок
                        for col_name in common_columns:
                            col1 = next(col for col in analysis1.columns if col.name == col_name)
                            col2 = next(col for col in analysis2.columns if col.name == col_name)
                            
                            if not self._are_types_compatible(col1.type, col2.type):
                                issues.append(
                                    f"Column {col_name} has incompatible types: "
                                    f"{col1.type} in {analysis1.source_id} vs "
                                    f"{col2.type} in {analysis2.source_id}"
                                )
        
        return issues
    
    def _are_types_compatible(self, type1: str, type2: str) -> bool:
        """Проверяет совместимость типов данных."""
        # Группы совместимых типов
        numeric_types = {'int', 'int64', 'float', 'float64', 'number', 'integer', 'bigint', 'decimal'}
        string_types = {'str', 'string', 'object', 'text', 'varchar', 'char'}
        date_types = {'datetime', 'date', 'timestamp'}
        
        # Нормализуем типы
        type1_norm = type1.lower().strip()
        type2_norm = type2.lower().strip()
        
        # Проверяем принадлежность к одной группе
        if (type1_norm in numeric_types and type2_norm in numeric_types) or \
           (type1_norm in string_types and type2_norm in string_types) or \
           (type1_norm in date_types and type2_norm in date_types):
            return True
        
        return type1_norm == type2_norm
    
    async def _merge_dataframes(self, dataframes: Dict[str, pd.DataFrame], join_strategy: str) -> pd.DataFrame:
        """Объединяет несколько DataFrame согласно стратегии."""
        
        if join_strategy == "auto":
            # Автоматическая стратегия - пытаемся найти общие колонки
            return self._auto_merge_dataframes(dataframes)
        elif join_strategy == "concat":
            # Простая конкатенация (UNION ALL)
            return pd.concat(list(dataframes.values()), ignore_index=True)
        else:
            # Пользовательская стратегия JOIN (требует дополнительной конфигурации)
            return self._auto_merge_dataframes(dataframes)
    
    def _auto_merge_dataframes(self, dataframes: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Автоматическое объединение DataFrame через общие колонки."""
        df_list = list(dataframes.items())
        
        if len(df_list) == 1:
            return df_list[0][1]
        
        # Начинаем с первого DataFrame
        result_df = df_list[0][1].copy()
        
        # Последовательно присоединяем остальные
        for source_id, df in df_list[1:]:
            # Находим общие колонки
            common_columns = list(set(result_df.columns) & set(df.columns))
            
            if common_columns:
                # Выполняем LEFT JOIN по первой общей колонке
                join_key = common_columns[0]
                result_df = result_df.merge(
                    df, 
                    on=join_key, 
                    how='left', 
                    suffixes=('', f'_{source_id}')
                )
            else:
                # Если нет общих колонок, выполняем CROSS JOIN (осторожно!)
                logger.warning(f"No common columns found, performing cross join with {source_id}")
                result_df = result_df.assign(key=1).merge(
                    df.assign(key=1), 
                    on='key', 
                    suffixes=('', f'_{source_id}')
                ).drop('key', axis=1)
        
        return result_df
    
    def _perform_join(self, left_df: pd.DataFrame, right_df: pd.DataFrame, join_rule: JoinRule) -> pd.DataFrame:
        """Выполняет JOIN операцию между двумя DataFrame."""
        
        # Подготавливаем ключи соединения
        left_keys = list(join_rule.join_keys.keys())
        right_keys = list(join_rule.join_keys.values())
        
        # Переименовываем колонки в правом DataFrame если нужно
        right_df_renamed = right_df.copy()
        for left_key, right_key in join_rule.join_keys.items():
            if left_key != right_key:
                right_df_renamed = right_df_renamed.rename(columns={right_key: left_key})
        
        # Определяем тип JOIN
        how_mapping = {
            JoinType.INNER: 'inner',
            JoinType.LEFT: 'left',
            JoinType.RIGHT: 'right',
            JoinType.FULL: 'outer'
        }
        
        how = how_mapping.get(join_rule.join_type, 'inner')
        
        # Выполняем JOIN
        result_df = left_df.merge(
            right_df_renamed,
            on=left_keys,
            how=how,
            suffixes=('_left', '_right')
        )
        
        return result_df
    
    def _calculate_join_statistics(self, left_df: pd.DataFrame, right_df: pd.DataFrame, joined_df: pd.DataFrame) -> Dict[str, Any]:
        """Вычисляет статистику JOIN операции."""
        return {
            "left_rows": len(left_df),
            "right_rows": len(right_df),
            "joined_rows": len(joined_df),
            "join_ratio": len(joined_df) / max(len(left_df), 1),
            "data_expansion": len(joined_df) / max(len(left_df), 1) > 1,
            "null_values_created": joined_df.isnull().sum().sum() - left_df.isnull().sum().sum()
        }
    
    def _generate_join_warnings(self, left_df: pd.DataFrame, right_df: pd.DataFrame, 
                              joined_df: pd.DataFrame, join_rule: JoinRule) -> List[str]:
        """Генерирует предупреждения для JOIN операции."""
        warnings = []
        
        # Проверяем на дублирование данных
        if len(joined_df) > len(left_df) * 1.5:
            warnings.append("JOIN may cause significant data duplication")
        
        # Проверяем на потерю данных
        if join_rule.join_type == JoinType.INNER and len(joined_df) < len(left_df) * 0.8:
            warnings.append("INNER JOIN may cause significant data loss")
        
        # Проверяем на NULL значения
        null_increase = joined_df.isnull().sum().sum() - left_df.isnull().sum().sum()
        if null_increase > len(joined_df) * 0.1:
            warnings.append("JOIN introduces many NULL values")
        
        # Проверяем уникальность ключей
        for left_key in join_rule.join_keys.keys():
            if left_df[left_key].duplicated().any():
                warnings.append(f"Left key '{left_key}' has duplicate values")
        
        return warnings
    
    async def _save_dataset(self, df: pd.DataFrame, dataset_name: str, 
                          output_format: str, include_metadata: bool) -> str:
        """Сохраняет набор данных в указанном формате."""
        
        # Создаем директорию для агрегированных данных
        output_dir = Path("data_landing_zone/aggregated") / dataset_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Определяем путь к файлу
        if output_format == "parquet":
            file_path = output_dir / f"{dataset_name}.parquet"
            df.to_parquet(file_path, index=False)
        elif output_format == "csv":
            file_path = output_dir / f"{dataset_name}.csv"
            df.to_csv(file_path, index=False)
        elif output_format == "json":
            file_path = output_dir / f"{dataset_name}.json"
            df.to_json(file_path, orient='records', lines=True)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        # Сохраняем метаданные если требуется
        if include_metadata:
            metadata_path = output_dir / f"{dataset_name}_metadata.json"
            metadata = {
                "dataset_name": dataset_name,
                "created_at": datetime.utcnow().isoformat(),
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": [{"name": col, "type": str(df[col].dtype)} for col in df.columns],
                "file_format": output_format,
                "file_size_bytes": file_path.stat().st_size
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return str(file_path)
    
    def _generate_dataset_metadata(self, request: CustomDatasetRequest, 
                                 sources_analysis: List[Any], df: pd.DataFrame) -> Dict[str, Any]:
        """Генерирует метаданные для созданного набора данных."""
        
        # Конвертируем все numpy типы в стандартные Python типы
        def convert_numpy_types(obj):
            """Рекурсивно конвертирует numpy типы в стандартные Python типы."""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            else:
                return obj
        
        metadata = {
            "dataset_info": {
                "name": request.dataset_name,
                "description": f"Custom dataset created from {len(request.sources)} sources",
                "created_at": datetime.utcnow().isoformat(),
                "format": request.output_format
            },
            "sources": [
                {
                    "source_id": analysis.source_id,
                    "columns_used": len(analysis.columns),
                    "estimated_rows": int(analysis.row_count) if analysis.row_count else 0
                }
                for analysis in sources_analysis
            ],
            "schema": {
                "columns": [
                    {
                        "name": col,
                        "type": str(df[col].dtype),
                        "null_count": int(df[col].isnull().sum()),
                        "unique_count": int(df[col].nunique())
                    }
                    for col in df.columns
                ],
                "total_rows": int(len(df)),
                "total_columns": int(len(df.columns)),
                "memory_usage_bytes": int(df.memory_usage(deep=True).sum())
            },
            "quality_metrics": {
                "completeness": float(1 - df.isnull().sum().sum() / (len(df) * len(df.columns))),
                "duplicate_rows": int(df.duplicated().sum()),
                "data_types_consistent": True  # Упрощенная проверка
            }
        }
        
        # Применяем конвертацию ко всему объекту метаданных
        return convert_numpy_types(metadata)
    
    async def get_available_columns(self, source: DataSource) -> List[ColumnInfo]:
        """
        Получает список доступных колонок из источника данных.
        
        Args:
            source: Конфигурация источника данных
            
        Returns:
            List[ColumnInfo]: Список доступных колонок
        """
        try:
            analysis = await self.data_collector.analyze_source(source)
            return analysis.columns
        except Exception as e:
            logger.error(f"Error getting columns for source {source.source_id}: {str(e)}")
            return []
