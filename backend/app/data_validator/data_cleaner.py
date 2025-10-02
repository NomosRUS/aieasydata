"""
Автоматическая очистка данных.

Содержит алгоритмы для исправления найденных проблем качества данных,
включая обработку пропусков, дубликатов и нормализацию данных.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import re
from pathlib import Path

from .schemas import (
    QualityIssue, CleaningStrategy, ValidationMetadata,
    IssueType, IssueSeverity
)

logger = logging.getLogger(__name__)


class DataCleaner:
    """Класс для автоматической очистки данных."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Настройки очистки по умолчанию
        self.cleaning_config = {
            'missing_value_threshold': 0.5,  # Удалять колонки с >50% пропусков
            'duplicate_threshold': 0.95,     # Считать дубликатами при >95% совпадении
            'outlier_threshold': 3.0,        # Z-score порог для выбросов
            'rare_category_threshold': 0.01   # Категории с частотой <1% объединять
        }
    
    def clean_dataframe(self, df: pd.DataFrame, issues: List[QualityIssue], 
                       strategy: CleaningStrategy = CleaningStrategy.AUTO,
                       preserve_original: bool = True) -> Tuple[pd.DataFrame, List[str]]:
        """
        Выполняет автоматическую очистку DataFrame.
        
        Args:
            df: DataFrame для очистки
            issues: Список найденных проблем качества
            strategy: Стратегия очистки
            preserve_original: Сохранять ли оригинальные данные
            
        Returns:
            Кортеж (очищенный DataFrame, список примененных исправлений)
        """
        if preserve_original:
            cleaned_df = df.copy()
        else:
            cleaned_df = df
        
        applied_fixes = []
        
        try:
            # Применяем исправления в зависимости от стратегии
            if strategy == CleaningStrategy.CONSERVATIVE:
                applied_fixes = self._apply_conservative_cleaning(cleaned_df, issues)
            elif strategy == CleaningStrategy.AUTO:
                applied_fixes = self._apply_automatic_cleaning(cleaned_df, issues)
            elif strategy == CleaningStrategy.MANUAL:
                applied_fixes = self._apply_manual_cleaning(cleaned_df, issues)
            
            self.logger.info(f"Очистка завершена. Применено {len(applied_fixes)} исправлений")
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке данных: {str(e)}")
            applied_fixes.append(f"Ошибка очистки: {str(e)}")
        
        return cleaned_df, applied_fixes
    
    def _apply_conservative_cleaning(self, df: pd.DataFrame, issues: List[QualityIssue]) -> List[str]:
        """Применяет консервативную очистку (минимальные изменения)."""
        applied_fixes = []
        
        # Только критические исправления
        critical_issues = [issue for issue in issues if issue.severity == IssueSeverity.CRITICAL]
        
        for issue in critical_issues:
            if issue.type == IssueType.DUPLICATES:
                # Удаляем только точные дубликаты
                before_count = len(df)
                df.drop_duplicates(inplace=True)
                after_count = len(df)
                
                if before_count != after_count:
                    applied_fixes.append(f"Удалено {before_count - after_count} точных дубликатов")
            
            elif issue.type == IssueType.TYPE_MISMATCH and issue.column:
                # Пытаемся исправить только очевидные проблемы типов
                fix_applied = self._fix_obvious_type_issues(df, issue.column)
                if fix_applied:
                    applied_fixes.append(f"Исправлены типы данных в колонке '{issue.column}'")
        
        return applied_fixes
    
    def _apply_automatic_cleaning(self, df: pd.DataFrame, issues: List[QualityIssue]) -> List[str]:
        """Применяет автоматическую очистку (сбалансированный подход)."""
        applied_fixes = []
        
        # 1. Исправление типов данных
        type_fixes = self._fix_data_types(df, issues)
        applied_fixes.extend(type_fixes)
        
        # 2. Обработка пропущенных значений
        missing_fixes = self._handle_missing_values(df, issues)
        applied_fixes.extend(missing_fixes)
        
        # 3. Удаление дубликатов
        duplicate_fixes = self._remove_duplicates(df, issues)
        applied_fixes.extend(duplicate_fixes)
        
        # 4. Нормализация данных
        normalization_fixes = self._normalize_data(df)
        applied_fixes.extend(normalization_fixes)
        
        # 5. Обработка выбросов
        outlier_fixes = self._handle_outliers(df, issues)
        applied_fixes.extend(outlier_fixes)
        
        return applied_fixes
    
    def _apply_manual_cleaning(self, df: pd.DataFrame, issues: List[QualityIssue]) -> List[str]:
        """Применяет ручную очистку (только явно указанные исправления)."""
        applied_fixes = []
        
        # В ручном режиме применяем только исправления с suggested_fix
        for issue in issues:
            if issue.suggested_fix and issue.column:
                try:
                    if "заполните медианным значением" in issue.suggested_fix.lower():
                        if df[issue.column].dtype in ['int64', 'float64']:
                            median_val = df[issue.column].median()
                            filled_count = df[issue.column].isna().sum()
                            df[issue.column].fillna(median_val, inplace=True)
                            applied_fixes.append(f"Заполнено {filled_count} пропусков медианой в колонке '{issue.column}'")
                    
                    elif "заполните модальным значением" in issue.suggested_fix.lower():
                        mode_val = df[issue.column].mode().iloc[0] if not df[issue.column].mode().empty else "Unknown"
                        filled_count = df[issue.column].isna().sum()
                        df[issue.column].fillna(mode_val, inplace=True)
                        applied_fixes.append(f"Заполнено {filled_count} пропусков модой в колонке '{issue.column}'")
                        
                except Exception as e:
                    self.logger.warning(f"Не удалось применить исправление для {issue.column}: {str(e)}")
        
        return applied_fixes
    
    def _fix_data_types(self, df: pd.DataFrame, issues: List[QualityIssue]) -> List[str]:
        """Исправляет проблемы с типами данных."""
        applied_fixes = []
        
        type_issues = [issue for issue in issues if issue.type == IssueType.TYPE_MISMATCH]
        
        for issue in type_issues:
            if not issue.column:
                continue
            
            try:
                column = issue.column
                
                # Пытаемся автоматически определить правильный тип
                if df[column].dtype == 'object':
                    # Проверяем, можно ли привести к числовому типу
                    numeric_converted = self._try_convert_to_numeric(df, column)
                    if numeric_converted:
                        applied_fixes.append(f"Преобразована колонка '{column}' в числовой тип")
                        continue
                    
                    # Проверяем, можно ли привести к дате
                    date_converted = self._try_convert_to_datetime(df, column)
                    if date_converted:
                        applied_fixes.append(f"Преобразована колонка '{column}' в тип даты")
                        continue
                
            except Exception as e:
                self.logger.warning(f"Ошибка при исправлении типа колонки {issue.column}: {str(e)}")
        
        return applied_fixes
    
    def _try_convert_to_numeric(self, df: pd.DataFrame, column: str) -> bool:
        """Пытается преобразовать колонку в числовой тип."""
        try:
            # Проверяем, какой процент значений можно преобразовать в числа
            non_null_values = df[column].dropna()
            if len(non_null_values) == 0:
                return False
            
            convertible_count = 0
            for value in non_null_values.head(1000):  # Проверяем первые 1000 значений
                try:
                    float(str(value).replace(',', '.').strip())
                    convertible_count += 1
                except (ValueError, TypeError):
                    pass
            
            conversion_rate = convertible_count / len(non_null_values.head(1000))
            
            if conversion_rate >= 0.8:  # Если 80%+ значений можно преобразовать
                # Выполняем преобразование
                df[column] = pd.to_numeric(df[column].astype(str).str.replace(',', '.'), errors='coerce')
                return True
                
        except Exception as e:
            self.logger.debug(f"Не удалось преобразовать {column} в числовой тип: {str(e)}")
        
        return False
    
    def _try_convert_to_datetime(self, df: pd.DataFrame, column: str) -> bool:
        """Пытается преобразовать колонку в тип даты."""
        try:
            # Проверяем, содержит ли колонка даты
            non_null_values = df[column].dropna()
            if len(non_null_values) == 0:
                return False
            
            # Пытаемся преобразовать несколько значений
            sample_size = min(100, len(non_null_values))
            convertible_count = 0
            
            for value in non_null_values.head(sample_size):
                try:
                    pd.to_datetime(str(value))
                    convertible_count += 1
                except:
                    pass
            
            conversion_rate = convertible_count / sample_size
            
            if conversion_rate >= 0.7:  # Если 70%+ значений можно преобразовать в даты
                df[column] = pd.to_datetime(df[column], errors='coerce')
                return True
                
        except Exception as e:
            self.logger.debug(f"Не удалось преобразовать {column} в тип даты: {str(e)}")
        
        return False
    
    def _handle_missing_values(self, df: pd.DataFrame, issues: List[QualityIssue]) -> List[str]:
        """Обрабатывает пропущенные значения."""
        applied_fixes = []
        
        missing_issues = [issue for issue in issues if issue.type == IssueType.MISSING_VALUES]
        
        for issue in missing_issues:
            if not issue.column:
                continue
            
            try:
                column = issue.column
                missing_percentage = issue.percentage
                
                # Стратегия зависит от процента пропусков и типа данных
                if missing_percentage >= 50:
                    # Слишком много пропусков - помечаем колонку для возможного удаления
                    applied_fixes.append(f"Колонка '{column}' имеет {missing_percentage:.1f}% пропусков (критично)")
                    continue
                
                elif missing_percentage >= 20:
                    # Много пропусков - заполняем значением по умолчанию
                    if df[column].dtype in ['int64', 'float64']:
                        fill_value = df[column].median()
                        method = "медианой"
                    else:
                        fill_value = df[column].mode().iloc[0] if not df[column].mode().empty else "Unknown"
                        method = "модой"
                    
                    filled_count = df[column].isna().sum()
                    df[column].fillna(fill_value, inplace=True)
                    applied_fixes.append(f"Заполнено {filled_count} пропусков {method} в колонке '{column}'")
                
                else:
                    # Немного пропусков - используем интерполяцию или forward fill
                    if df[column].dtype in ['int64', 'float64']:
                        filled_count = df[column].isna().sum()
                        df[column].interpolate(inplace=True)
                        df[column].fillna(method='ffill', inplace=True)
                        df[column].fillna(method='bfill', inplace=True)
                        applied_fixes.append(f"Интерполировано {filled_count} пропусков в колонке '{column}'")
                    else:
                        filled_count = df[column].isna().sum()
                        df[column].fillna(method='ffill', inplace=True)
                        df[column].fillna(method='bfill', inplace=True)
                        df[column].fillna("Unknown", inplace=True)
                        applied_fixes.append(f"Заполнено {filled_count} пропусков в колонке '{column}'")
                        
            except Exception as e:
                self.logger.warning(f"Ошибка при обработке пропусков в колонке {issue.column}: {str(e)}")
        
        return applied_fixes
    
    def _remove_duplicates(self, df: pd.DataFrame, issues: List[QualityIssue]) -> List[str]:
        """Удаляет дубликаты."""
        applied_fixes = []
        
        duplicate_issues = [issue for issue in issues if issue.type == IssueType.DUPLICATES]
        
        for issue in duplicate_issues:
            try:
                if issue.column:
                    # Дубликаты в конкретной колонке
                    before_count = len(df)
                    df.drop_duplicates(subset=[issue.column], inplace=True)
                    after_count = len(df)
                    
                    if before_count != after_count:
                        applied_fixes.append(f"Удалено {before_count - after_count} дубликатов по колонке '{issue.column}'")
                else:
                    # Полные дубликаты строк
                    before_count = len(df)
                    df.drop_duplicates(inplace=True)
                    after_count = len(df)
                    
                    if before_count != after_count:
                        applied_fixes.append(f"Удалено {before_count - after_count} полных дубликатов строк")
                        
            except Exception as e:
                self.logger.warning(f"Ошибка при удалении дубликатов: {str(e)}")
        
        return applied_fixes
    
    def _normalize_data(self, df: pd.DataFrame) -> List[str]:
        """Нормализует данные (форматы, регистр, пробелы)."""
        applied_fixes = []
        
        string_columns = df.select_dtypes(include=['object']).columns
        
        for column in string_columns:
            try:
                original_values = df[column].dropna().head(1000)
                if len(original_values) == 0:
                    continue
                
                # Удаляем лишние пробелы
                df[column] = df[column].astype(str).str.strip()
                
                # Проверяем, нужно ли нормализовать регистр
                if self._should_normalize_case(original_values):
                    df[column] = df[column].str.title()
                    applied_fixes.append(f"Нормализован регистр в колонке '{column}'")
                
                # Нормализуем специальные форматы
                if self._looks_like_phone(original_values):
                    df[column] = df[column].apply(self._normalize_phone)
                    applied_fixes.append(f"Нормализованы телефонные номера в колонке '{column}'")
                
                elif self._looks_like_email(original_values):
                    df[column] = df[column].str.lower()
                    applied_fixes.append(f"Нормализованы email адреса в колонке '{column}'")
                    
            except Exception as e:
                self.logger.warning(f"Ошибка при нормализации колонки {column}: {str(e)}")
        
        return applied_fixes
    
    def _should_normalize_case(self, values: pd.Series) -> bool:
        """Определяет, нужно ли нормализовать регистр."""
        # Проверяем, есть ли смешанный регистр
        mixed_case_count = 0
        for value in values.head(100):
            str_val = str(value)
            if str_val != str_val.lower() and str_val != str_val.upper():
                mixed_case_count += 1
        
        return mixed_case_count > len(values.head(100)) * 0.3  # Более 30% смешанного регистра
    
    def _looks_like_phone(self, values: pd.Series) -> bool:
        """Проверяет, похожи ли значения на телефонные номера."""
        phone_pattern = re.compile(r'[\d\s\-\+\(\)]{7,}')
        phone_count = 0
        
        for value in values.head(50):
            if phone_pattern.match(str(value)):
                phone_count += 1
        
        return phone_count > len(values.head(50)) * 0.7  # Более 70% похожи на телефоны
    
    def _looks_like_email(self, values: pd.Series) -> bool:
        """Проверяет, похожи ли значения на email адреса."""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        email_count = 0
        
        for value in values.head(50):
            if email_pattern.match(str(value)):
                email_count += 1
        
        return email_count > len(values.head(50)) * 0.7  # Более 70% похожи на email
    
    def _normalize_phone(self, phone: str) -> str:
        """Нормализует телефонный номер."""
        if pd.isna(phone):
            return phone
        
        # Удаляем все кроме цифр и +
        cleaned = re.sub(r'[^\d\+]', '', str(phone))
        
        # Базовая нормализация для российских номеров
        if cleaned.startswith('8') and len(cleaned) == 11:
            cleaned = '+7' + cleaned[1:]
        elif cleaned.startswith('7') and len(cleaned) == 11:
            cleaned = '+' + cleaned
        
        return cleaned
    
    def _handle_outliers(self, df: pd.DataFrame, issues: List[QualityIssue]) -> List[str]:
        """Обрабатывает выбросы в данных."""
        applied_fixes = []
        
        anomaly_issues = [issue for issue in issues if issue.type == IssueType.ANOMALY]
        
        for issue in anomaly_issues:
            if not issue.column:
                continue
            
            try:
                column = issue.column
                
                if df[column].dtype in ['int64', 'float64']:
                    # Применяем winsorization (ограничиваем экстремальные значения)
                    q1 = df[column].quantile(0.05)
                    q99 = df[column].quantile(0.95)
                    
                    outliers_count = ((df[column] < q1) | (df[column] > q99)).sum()
                    
                    if outliers_count > 0:
                        df[column] = df[column].clip(lower=q1, upper=q99)
                        applied_fixes.append(f"Ограничены {outliers_count} выбросов в колонке '{column}' (winsorization)")
                        
            except Exception as e:
                self.logger.warning(f"Ошибка при обработке выбросов в колонке {issue.column}: {str(e)}")
        
        return applied_fixes
    
    def _fix_obvious_type_issues(self, df: pd.DataFrame, column: str) -> bool:
        """Исправляет очевидные проблемы с типами данных."""
        try:
            # Пытаемся исправить только очевидные случаи
            if df[column].dtype == 'object':
                sample_values = df[column].dropna().head(100)
                
                # Проверяем, все ли значения числовые
                all_numeric = True
                for value in sample_values:
                    try:
                        float(str(value))
                    except (ValueError, TypeError):
                        all_numeric = False
                        break
                
                if all_numeric:
                    df[column] = pd.to_numeric(df[column], errors='coerce')
                    return True
            
            return False
            
        except Exception:
            return False
    
    def save_cleaned_data(self, df: pd.DataFrame, original_path: str, 
                         output_dir: str = "data_landing_zone/cleaned") -> str:
        """
        Сохраняет очищенные данные в формате Parquet.
        
        Args:
            df: Очищенный DataFrame
            original_path: Путь к оригинальному файлу
            output_dir: Директория для сохранения
            
        Returns:
            Путь к сохраненному файлу
        """
        try:
            # Создаем структуру папок
            original_file = Path(original_path)
            output_path = Path(output_dir) / original_file.stem
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем в формате Parquet
            cleaned_file_path = output_path / f"{original_file.stem}_cleaned.parquet"
            df.to_parquet(cleaned_file_path, index=False)
            
            self.logger.info(f"Очищенные данные сохранены: {cleaned_file_path}")
            
            return str(cleaned_file_path)
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении очищенных данных: {str(e)}")
            raise
