"""
Оценка качества данных.

Содержит алгоритмы для комплексной оценки качества данных
с присвоением итоговой оценки от 0.0 до 1.0.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from pathlib import Path
from ..shared.base_profiler import get_basic_file_info, get_basic_schema_info

from .schemas import QualityAssessment, QualityIssue, AnomalyInfo
import logging

logger = logging.getLogger(__name__)

class QualityAssessor:
    """Класс для оценки качества данных."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Веса для компонентов оценки качества
        self.weights = {
            'completeness': 0.4,    # 40% - полнота данных
            'correctness': 0.3,     # 30% - корректность типов и форматов
            'consistency': 0.2,     # 20% - согласованность данных
            'uniqueness': 0.1       # 10% - уникальность (отсутствие дубликатов)
        }
    
    def assess_data_quality(self, df: pd.DataFrame, issues: List[QualityIssue] = None) -> QualityAssessment:
        """
        Выполняет комплексную оценку качества данных.
        
        Args:
            df: DataFrame для оценки
            issues: Список найденных проблем качества (опционально)
            
        Returns:
            Результат оценки качества данных
        """
        try:
            # Вычисляем компоненты оценки качества
            completeness_score = self._calculate_completeness_score(df)
            correctness_score = self._calculate_correctness_score(df, issues)
            consistency_score = self._calculate_consistency_score(df)
            uniqueness_score = self._calculate_uniqueness_score(df)
            
            # Вычисляем общую оценку качества
            overall_score = (
                completeness_score * self.weights['completeness'] +
                correctness_score * self.weights['correctness'] +
                consistency_score * self.weights['consistency'] +
                uniqueness_score * self.weights['uniqueness']
            )
            
            # Ограничиваем оценку диапазоном [0.0, 1.0]
            overall_score = max(0.0, min(1.0, overall_score))
            
            # Генерируем рекомендации
            recommendations = self._generate_quality_recommendations(
                completeness_score, correctness_score, consistency_score, uniqueness_score
            )
            
            # Обнаруживаем аномалии (базовый анализ)
            anomalies = self._detect_basic_anomalies(df)
            
            self.logger.info(f"Оценка качества завершена. Общая оценка: {overall_score:.3f}")
            
            return QualityAssessment(
                overall_score=overall_score,
                completeness_score=completeness_score,
                correctness_score=correctness_score,
                consistency_score=consistency_score,
                uniqueness_score=uniqueness_score,
                anomalies=anomalies,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при оценке качества данных: {str(e)}")
            
            # Возвращаем минимальную оценку при ошибке
            return QualityAssessment(
                overall_score=0.0,
                completeness_score=0.0,
                correctness_score=0.0,
                consistency_score=0.0,
                uniqueness_score=0.0,
                anomalies=[],
                recommendations=[f"Ошибка при оценке качества: {str(e)}"]
            )
    
    def _calculate_completeness_score(self, df: pd.DataFrame) -> float:
        """
        Вычисляет оценку полноты данных (40% от общей оценки).
        
        Args:
            df: DataFrame для анализа
            
        Returns:
            Оценка полноты от 0.0 до 1.0
        """
        if df.empty:
            return 0.0
        
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isna().sum().sum()
        
        if total_cells == 0:
            return 0.0
        
        completeness = 1 - (missing_cells / total_cells)
        return max(0.0, min(1.0, completeness))
    
    def _calculate_correctness_score(self, df: pd.DataFrame, issues: List[QualityIssue] = None) -> float:
        """
        Вычисляет оценку корректности данных (30% от общей оценки).
        
        Args:
            df: DataFrame для анализа
            issues: Список проблем качества
            
        Returns:
            Оценка корректности от 0.0 до 1.0
        """
        if df.empty:
            return 0.0
        
        correctness_score = 1.0
        
        # Анализируем проблемы типов данных из issues
        if issues:
            type_issues = [issue for issue in issues if issue.type == "type_mismatch"]
            if type_issues:
                # Снижаем оценку на основе серьезности проблем с типами
                type_penalty = sum(issue.percentage / 100 * 0.1 for issue in type_issues)
                correctness_score -= min(type_penalty, 0.5)  # Максимальный штраф 50%
        
        # Дополнительная проверка корректности типов
        for column in df.columns:
            try:
                if df[column].dtype == 'object':
                    # Проверяем, можно ли привести к более специфичному типу
                    non_null_values = df[column].dropna()
                    if len(non_null_values) > 0:
                        # Пытаемся определить, должна ли колонка быть числовой
                        numeric_convertible = 0
                        for value in non_null_values.head(100):
                            try:
                                float(str(value))
                                numeric_convertible += 1
                            except (ValueError, TypeError):
                                pass
                        
                        # Если большинство значений можно привести к числу, но тип object
                        if numeric_convertible / len(non_null_values.head(100)) > 0.8:
                            correctness_score -= 0.05  # Небольшой штраф за неоптимальный тип
                            
            except Exception as e:
                self.logger.warning(f"Ошибка при анализе корректности колонки {column}: {str(e)}")
        
        return max(0.0, min(1.0, correctness_score))
    
    def _calculate_consistency_score(self, df: pd.DataFrame) -> float:
        """
        Вычисляет оценку согласованности данных (20% от общей оценки).
        
        Args:
            df: DataFrame для анализа
            
        Returns:
            Оценка согласованности от 0.0 до 1.0
        """
        if df.empty:
            return 0.0
        
        consistency_score = 1.0
        
        # Проверяем согласованность форматов в строковых колонках
        string_columns = df.select_dtypes(include=['object']).columns
        
        for column in string_columns:
            try:
                non_null_values = df[column].dropna()
                if len(non_null_values) == 0:
                    continue
                
                # Анализируем форматы строк
                formats = self._analyze_string_formats(non_null_values)
                
                if len(formats) > 1:
                    # Если найдено несколько форматов, снижаем оценку
                    format_inconsistency = 1 - (max(formats.values()) / len(non_null_values))
                    consistency_score -= format_inconsistency * 0.1  # Штраф до 10% за колонку
                    
            except Exception as e:
                self.logger.warning(f"Ошибка при анализе согласованности колонки {column}: {str(e)}")
        
        # Проверяем согласованность диапазонов в числовых колонках
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            try:
                if len(df[column].dropna()) > 0:
                    # Проверяем на экстремальные выбросы
                    q1 = df[column].quantile(0.25)
                    q3 = df[column].quantile(0.75)
                    iqr = q3 - q1
                    
                    if iqr > 0:
                        lower_bound = q1 - 3 * iqr
                        upper_bound = q3 + 3 * iqr
                        
                        outliers_ratio = ((df[column] < lower_bound) | (df[column] > upper_bound)).sum() / len(df)
                        
                        if outliers_ratio > 0.05:  # Более 5% выбросов
                            consistency_score -= outliers_ratio * 0.2  # Штраф пропорционально количеству выбросов
                            
            except Exception as e:
                self.logger.warning(f"Ошибка при анализе выбросов в колонке {column}: {str(e)}")
        
        return max(0.0, min(1.0, consistency_score))
    
    def _calculate_uniqueness_score(self, df: pd.DataFrame) -> float:
        """
        Вычисляет оценку уникальности данных (10% от общей оценки).
        
        Args:
            df: DataFrame для анализа
            
        Returns:
            Оценка уникальности от 0.0 до 1.0
        """
        if df.empty:
            return 0.0
        
        # Проверяем дубликаты строк
        duplicate_rows_ratio = df.duplicated().sum() / len(df)
        
        # Базовая оценка на основе дубликатов строк
        uniqueness_score = 1 - duplicate_rows_ratio
        
        # Дополнительно проверяем ключевые колонки
        key_columns = self._identify_key_columns(df)
        
        if key_columns:
            key_duplicates_penalty = 0
            for column in key_columns:
                column_duplicates_ratio = df[column].duplicated().sum() / len(df)
                key_duplicates_penalty += column_duplicates_ratio * 0.2  # Штраф за дубликаты в ключевых колонках
            
            uniqueness_score -= min(key_duplicates_penalty, 0.3)  # Максимальный штраф 30%
        
        return max(0.0, min(1.0, uniqueness_score))
    
    def _analyze_string_formats(self, series: pd.Series) -> Dict[str, int]:
        """
        Анализирует форматы строк в серии.
        
        Args:
            series: Серия строковых данных
            
        Returns:
            Словарь с количеством значений для каждого формата
        """
        formats = {}
        
        for value in series.head(1000):  # Анализируем первые 1000 значений
            try:
                value_str = str(value).strip()
                
                # Определяем формат строки
                format_key = self._classify_string_format(value_str)
                formats[format_key] = formats.get(format_key, 0) + 1
                
            except Exception:
                formats['unknown'] = formats.get('unknown', 0) + 1
        
        return formats
    
    def _classify_string_format(self, value: str) -> str:
        """
        Классифицирует формат строки.
        
        Args:
            value: Строковое значение
            
        Returns:
            Тип формата строки
        """
        if not value:
            return 'empty'
        
        # Проверяем различные форматы
        if value.isdigit():
            return 'numeric'
        
        if '@' in value and '.' in value:
            return 'email'
        
        if value.startswith(('http://', 'https://')):
            return 'url'
        
        if len(value.split()) > 1:
            return 'multi_word'
        
        if value.isalpha():
            return 'alphabetic'
        
        if any(char.isdigit() for char in value) and any(char.isalpha() for char in value):
            return 'alphanumeric'
        
        return 'other'
    
    def _identify_key_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Идентифицирует потенциальные ключевые колонки.
        
        Args:
            df: DataFrame для анализа
            
        Returns:
            Список имен ключевых колонок
        """
        key_columns = []
        
        for column in df.columns:
            column_lower = column.lower()
            
            # Ищем колонки, которые могут быть ключевыми
            if any(keyword in column_lower for keyword in ['id', 'key', 'code', 'number', 'uuid']):
                # Проверяем уникальность
                unique_ratio = df[column].nunique() / len(df)
                if unique_ratio > 0.95:  # Более 95% уникальных значений
                    key_columns.append(column)
        
        return key_columns
    
    def _generate_quality_recommendations(self, completeness: float, correctness: float, 
                                        consistency: float, uniqueness: float) -> List[str]:
        """
        Генерирует рекомендации по улучшению качества данных.
        
        Args:
            completeness: Оценка полноты
            correctness: Оценка корректности
            consistency: Оценка согласованности
            uniqueness: Оценка уникальности
            
        Returns:
            Список рекомендаций
        """
        recommendations = []
        
        if completeness < 0.8:
            recommendations.append("Улучшите полноту данных: заполните пропущенные значения или найдите дополнительные источники")
        
        if correctness < 0.8:
            recommendations.append("Исправьте проблемы с типами данных: приведите значения к правильным типам")
        
        if consistency < 0.8:
            recommendations.append("Повысьте согласованность данных: стандартизируйте форматы и удалите выбросы")
        
        if uniqueness < 0.9:
            recommendations.append("Устраните дубликаты: удалите повторяющиеся записи и проверьте уникальность ключевых полей")
        
        # Общие рекомендации на основе общей оценки
        overall_score = (completeness + correctness + consistency + uniqueness) / 4
        
        if overall_score >= 0.9:
            recommendations.append("Отличное качество данных! Рекомендуется использовать ClickHouse для аналитики")
        elif overall_score >= 0.7:
            recommendations.append("Хорошее качество данных. Подходит для PostgreSQL или ClickHouse")
        elif overall_score >= 0.5:
            recommendations.append("Среднее качество данных. Рекомендуется дополнительная очистка перед использованием")
        else:
            recommendations.append("Низкое качество данных. Рекомендуется HDFS для сырых данных и серьезная очистка")
        
        return recommendations
    
    def _detect_basic_anomalies(self, df: pd.DataFrame) -> List[AnomalyInfo]:
        """
        Обнаруживает базовые аномалии в данных.
        
        Args:
            df: DataFrame для анализа
            
        Returns:
            Список обнаруженных аномалий
        """
        anomalies = []
        
        # Анализируем числовые колонки на выбросы
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            try:
                non_null_values = df[column].dropna()
                if len(non_null_values) == 0:
                    continue
                
                # Используем метод межквартильного размаха (IQR)
                q1 = non_null_values.quantile(0.25)
                q3 = non_null_values.quantile(0.75)
                iqr = q3 - q1
                
                if iqr > 0:
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    outliers = non_null_values[(non_null_values < lower_bound) | (non_null_values > upper_bound)]
                    
                    for idx, value in outliers.head(10).items():  # Ограничиваем количество аномалий
                        anomalies.append(AnomalyInfo(
                            anomaly_id=f"outlier_{column}_{idx}",
                            column=column,
                            anomaly_type="statistical_outlier",
                            value=float(value),
                            score=abs(value - non_null_values.median()) / (non_null_values.std() + 1e-6),
                            method="IQR",
                            description=f"Статистический выброс в колонке {column}: {value}"
                        ))
                        
            except Exception as e:
                self.logger.warning(f"Ошибка при поиске аномалий в колонке {column}: {str(e)}")
        
        return anomalies[:50]  # Ограничиваем общее количество аномалий
