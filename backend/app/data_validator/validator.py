"""
Базовая валидация данных.

Содержит классы и функции для валидации различных типов данных,
проверки типов, поиска пропусков и дубликатов.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import uuid

from .schemas import (
    DataSource, QualityIssue, IssueType, IssueSeverity,
    SourceType, DataFormat
)

logger = logging.getLogger(__name__)


class DataValidator:
    """Класс для базовой валидации данных."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_dataframe(self, df: pd.DataFrame, source: DataSource) -> List[QualityIssue]:
        """
        Выполняет комплексную валидацию DataFrame.
        
        Args:
            df: DataFrame для валидации
            source: Информация об источнике данных
            
        Returns:
            Список найденных проблем качества данных
        """
        issues = []
        
        try:
            # Проверка типов данных
            type_issues = self._check_data_types(df)
            issues.extend(type_issues)
            
            # Проверка пропущенных значений
            missing_issues = self._check_missing_values(df)
            issues.extend(missing_issues)
            
            # Проверка дубликатов
            duplicate_issues = self._check_duplicates(df)
            issues.extend(duplicate_issues)
            
            # Проверка целостности данных
            integrity_issues = self._check_data_integrity(df)
            issues.extend(integrity_issues)
            
            self.logger.info(f"Валидация завершена. Найдено {len(issues)} проблем.")
            
        except Exception as e:
            self.logger.error(f"Ошибка при валидации данных: {str(e)}")
            issues.append(QualityIssue(
                issue_id=str(uuid.uuid4()),
                type=IssueType.CONSTRAINT_VIOLATION,
                severity=IssueSeverity.CRITICAL,
                count=1,
                percentage=100.0,
                description=f"Критическая ошибка валидации: {str(e)}",
                suggested_fix="Проверьте формат и структуру данных"
            ))
        
        return issues
    
    def _check_data_types(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Проверяет соответствие типов данных."""
        issues = []
        
        for column in df.columns:
            try:
                # Проверяем, есть ли смешанные типы в колонке
                if df[column].dtype == 'object':
                    # Анализируем содержимое object колонок
                    type_analysis = self._analyze_column_types(df[column])
                    
                    if type_analysis['mixed_types']:
                        issues.append(QualityIssue(
                            issue_id=str(uuid.uuid4()),
                            type=IssueType.TYPE_MISMATCH,
                            severity=IssueSeverity.MEDIUM,
                            column=column,
                            count=type_analysis['inconsistent_count'],
                            percentage=(type_analysis['inconsistent_count'] / len(df)) * 100,
                            description=f"Колонка '{column}' содержит смешанные типы данных: {type_analysis['types_found']}",
                            suggested_fix="Приведите все значения к единому типу или очистите некорректные данные"
                        ))
                
                # Проверяем числовые колонки на наличие нечисловых значений
                if df[column].dtype in ['int64', 'float64']:
                    invalid_numeric = df[column].isna().sum()
                    if invalid_numeric > 0:
                        issues.append(QualityIssue(
                            issue_id=str(uuid.uuid4()),
                            type=IssueType.TYPE_MISMATCH,
                            severity=IssueSeverity.LOW,
                            column=column,
                            count=invalid_numeric,
                            percentage=(invalid_numeric / len(df)) * 100,
                            description=f"Числовая колонка '{column}' содержит {invalid_numeric} нечисловых значений",
                            suggested_fix="Замените нечисловые значения на числовые или удалите строки"
                        ))
                        
            except Exception as e:
                self.logger.warning(f"Ошибка при проверке типов для колонки {column}: {str(e)}")
        
        return issues
    
    def _analyze_column_types(self, series: pd.Series) -> Dict[str, Any]:
        """Анализирует типы данных в колонке."""
        types_found = set()
        inconsistent_count = 0
        
        # Удаляем NaN значения для анализа
        non_null_values = series.dropna()
        
        if len(non_null_values) == 0:
            return {
                'mixed_types': False,
                'types_found': [],
                'inconsistent_count': 0
            }
        
        for value in non_null_values.head(1000):  # Анализируем первые 1000 значений
            try:
                # Пытаемся определить тип значения
                if isinstance(value, str):
                    # Проверяем, может ли строка быть числом
                    try:
                        float(value)
                        types_found.add('numeric_string')
                    except ValueError:
                        # Проверяем, может ли быть датой
                        try:
                            pd.to_datetime(value)
                            types_found.add('date_string')
                        except:
                            types_found.add('string')
                elif isinstance(value, (int, float)):
                    types_found.add('numeric')
                elif isinstance(value, datetime):
                    types_found.add('datetime')
                else:
                    types_found.add('other')
                    
            except Exception:
                inconsistent_count += 1
        
        return {
            'mixed_types': len(types_found) > 1,
            'types_found': list(types_found),
            'inconsistent_count': inconsistent_count
        }
    
    def _check_missing_values(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Проверяет пропущенные значения."""
        issues = []
        
        for column in df.columns:
            missing_count = df[column].isna().sum()
            
            if missing_count > 0:
                missing_percentage = (missing_count / len(df)) * 100
                
                # Определяем серьезность проблемы
                if missing_percentage >= 50:
                    severity = IssueSeverity.CRITICAL
                elif missing_percentage >= 20:
                    severity = IssueSeverity.HIGH
                elif missing_percentage >= 5:
                    severity = IssueSeverity.MEDIUM
                else:
                    severity = IssueSeverity.LOW
                
                issues.append(QualityIssue(
                    issue_id=str(uuid.uuid4()),
                    type=IssueType.MISSING_VALUES,
                    severity=severity,
                    column=column,
                    count=missing_count,
                    percentage=missing_percentage,
                    description=f"Колонка '{column}' содержит {missing_count} пропущенных значений ({missing_percentage:.1f}%)",
                    suggested_fix=self._suggest_missing_value_fix(missing_percentage, df[column].dtype)
                ))
        
        return issues
    
    def _suggest_missing_value_fix(self, percentage: float, dtype) -> str:
        """Предлагает способ исправления пропущенных значений."""
        if percentage >= 50:
            return "Рассмотрите удаление колонки или поиск альтернативного источника данных"
        elif percentage >= 20:
            return "Заполните значениями по умолчанию или используйте интерполяцию"
        elif dtype in ['int64', 'float64']:
            return "Заполните медианным значением или используйте интерполяцию"
        else:
            return "Заполните модальным значением или значением по умолчанию"
    
    def _check_duplicates(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Проверяет наличие дубликатов."""
        issues = []
        
        # Проверка полных дубликатов строк
        duplicate_rows = df.duplicated().sum()
        if duplicate_rows > 0:
            duplicate_percentage = (duplicate_rows / len(df)) * 100
            
            severity = IssueSeverity.HIGH if duplicate_percentage >= 10 else IssueSeverity.MEDIUM
            
            issues.append(QualityIssue(
                issue_id=str(uuid.uuid4()),
                type=IssueType.DUPLICATES,
                severity=severity,
                count=duplicate_rows,
                percentage=duplicate_percentage,
                description=f"Найдено {duplicate_rows} полных дубликатов строк ({duplicate_percentage:.1f}%)",
                suggested_fix="Удалите дублирующиеся строки, сохранив первое вхождение"
            ))
        
        # Проверка дубликатов в потенциальных ключевых колонках
        key_columns = self._identify_key_columns(df)
        for column in key_columns:
            column_duplicates = df[column].duplicated().sum()
            if column_duplicates > 0:
                duplicate_percentage = (column_duplicates / len(df)) * 100
                
                issues.append(QualityIssue(
                    issue_id=str(uuid.uuid4()),
                    type=IssueType.DUPLICATES,
                    severity=IssueSeverity.MEDIUM,
                    column=column,
                    count=column_duplicates,
                    percentage=duplicate_percentage,
                    description=f"Ключевая колонка '{column}' содержит {column_duplicates} дубликатов ({duplicate_percentage:.1f}%)",
                    suggested_fix="Проверьте уникальность ключевых значений или объедините дублирующиеся записи"
                ))
        
        return issues
    
    def _identify_key_columns(self, df: pd.DataFrame) -> List[str]:
        """Идентифицирует потенциальные ключевые колонки."""
        key_columns = []
        
        for column in df.columns:
            column_lower = column.lower()
            
            # Ищем колонки, которые могут быть ключевыми
            if any(keyword in column_lower for keyword in ['id', 'key', 'code', 'number']):
                # Проверяем уникальность
                unique_ratio = df[column].nunique() / len(df)
                if unique_ratio > 0.95:  # Более 95% уникальных значений
                    key_columns.append(column)
        
        return key_columns
    
    def _check_data_integrity(self, df: pd.DataFrame) -> List[QualityIssue]:
        """Проверяет целостность данных."""
        issues = []
        
        # Проверка диапазонов для числовых колонок
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            try:
                # Проверяем на отрицательные значения в колонках, которые должны быть положительными
                if any(keyword in column.lower() for keyword in ['count', 'quantity', 'amount', 'price', 'age']):
                    negative_count = (df[column] < 0).sum()
                    if negative_count > 0:
                        issues.append(QualityIssue(
                            issue_id=str(uuid.uuid4()),
                            type=IssueType.CONSTRAINT_VIOLATION,
                            severity=IssueSeverity.MEDIUM,
                            column=column,
                            count=negative_count,
                            percentage=(negative_count / len(df)) * 100,
                            description=f"Колонка '{column}' содержит {negative_count} отрицательных значений",
                            suggested_fix="Проверьте корректность отрицательных значений или замените их на абсолютные"
                        ))
                
                # Проверяем на экстремальные выбросы
                if len(df[column].dropna()) > 0:
                    q1 = df[column].quantile(0.25)
                    q3 = df[column].quantile(0.75)
                    iqr = q3 - q1
                    
                    if iqr > 0:  # Избегаем деления на ноль
                        lower_bound = q1 - 3 * iqr
                        upper_bound = q3 + 3 * iqr
                        
                        outliers = ((df[column] < lower_bound) | (df[column] > upper_bound)).sum()
                        if outliers > 0:
                            outlier_percentage = (outliers / len(df)) * 100
                            
                            if outlier_percentage >= 5:  # Только если выбросов много
                                issues.append(QualityIssue(
                                    issue_id=str(uuid.uuid4()),
                                    type=IssueType.ANOMALY,
                                    severity=IssueSeverity.LOW,
                                    column=column,
                                    count=outliers,
                                    percentage=outlier_percentage,
                                    description=f"Колонка '{column}' содержит {outliers} потенциальных выбросов ({outlier_percentage:.1f}%)",
                                    suggested_fix="Проверьте выбросы на корректность или примените методы нормализации"
                                ))
                                
            except Exception as e:
                self.logger.warning(f"Ошибка при проверке целостности для колонки {column}: {str(e)}")
        
        # Проверка дат
        date_columns = df.select_dtypes(include=['datetime64']).columns
        for column in date_columns:
            try:
                # Проверяем на даты в будущем (если это не планируемые события)
                if 'plan' not in column.lower() and 'future' not in column.lower():
                    future_dates = (df[column] > pd.Timestamp.now()).sum()
                    if future_dates > 0:
                        issues.append(QualityIssue(
                            issue_id=str(uuid.uuid4()),
                            type=IssueType.CONSTRAINT_VIOLATION,
                            severity=IssueSeverity.LOW,
                            column=column,
                            count=future_dates,
                            percentage=(future_dates / len(df)) * 100,
                            description=f"Колонка '{column}' содержит {future_dates} дат в будущем",
                            suggested_fix="Проверьте корректность будущих дат"
                        ))
                        
            except Exception as e:
                self.logger.warning(f"Ошибка при проверке дат для колонки {column}: {str(e)}")
        
        return issues
    
    def validate_schema_consistency(self, df1: pd.DataFrame, df2: pd.DataFrame) -> List[str]:
        """
        Проверяет согласованность схем между двумя DataFrame.
        
        Args:
            df1: Первый DataFrame
            df2: Второй DataFrame
            
        Returns:
            Список различий в схемах
        """
        differences = []
        
        # Проверяем количество колонок
        if len(df1.columns) != len(df2.columns):
            differences.append(f"Разное количество колонок: {len(df1.columns)} vs {len(df2.columns)}")
        
        # Проверяем имена колонок
        df1_cols = set(df1.columns)
        df2_cols = set(df2.columns)
        
        missing_in_df2 = df1_cols - df2_cols
        missing_in_df1 = df2_cols - df1_cols
        
        if missing_in_df2:
            differences.append(f"Колонки отсутствуют во втором файле: {list(missing_in_df2)}")
        
        if missing_in_df1:
            differences.append(f"Дополнительные колонки во втором файле: {list(missing_in_df1)}")
        
        # Проверяем типы данных для общих колонок
        common_columns = df1_cols & df2_cols
        for column in common_columns:
            if df1[column].dtype != df2[column].dtype:
                differences.append(f"Разные типы данных в колонке '{column}': {df1[column].dtype} vs {df2[column].dtype}")
        
        return differences
