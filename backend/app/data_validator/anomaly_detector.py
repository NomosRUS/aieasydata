"""
Статистический анализ аномалий.

Содержит продвинутые алгоритмы для обнаружения аномалий в данных
с использованием статистических методов (средний уровень сложности).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import uuid
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import warnings

from .schemas import AnomalyInfo

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


class AnomalyDetector:
    """Класс для статистического обнаружения аномалий."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Пороговые значения для различных методов
        self.thresholds = {
            'z_score': 3.0,           # Z-score > 3 считается аномалией
            'iqr_multiplier': 1.5,    # Множитель для IQR метода
            'isolation_contamination': 0.1,  # Ожидаемая доля аномалий для Isolation Forest
            'rare_category_threshold': 0.01   # Категории с частотой < 1% считаются редкими
        }
    
    def detect_statistical_anomalies(self, df: pd.DataFrame) -> List[AnomalyInfo]:
        """
        Выполняет комплексное обнаружение статистических аномалий.
        
        Args:
            df: DataFrame для анализа
            
        Returns:
            Список обнаруженных аномалий
        """
        anomalies = []
        
        try:
            # 1. Обнаружение выбросов в числовых данных
            numeric_anomalies = self._detect_numeric_anomalies(df)
            anomalies.extend(numeric_anomalies)
            
            # 2. Обнаружение аномалий в категориальных данных
            categorical_anomalies = self._detect_categorical_anomalies(df)
            anomalies.extend(categorical_anomalies)
            
            # 3. Обнаружение временных аномалий
            temporal_anomalies = self._detect_temporal_anomalies(df)
            anomalies.extend(temporal_anomalies)
            
            # 4. Многомерное обнаружение аномалий
            multivariate_anomalies = self._detect_multivariate_anomalies(df)
            anomalies.extend(multivariate_anomalies)
            
            self.logger.info(f"Обнаружено {len(anomalies)} аномалий")
            
        except Exception as e:
            self.logger.error(f"Ошибка при обнаружении аномалий: {str(e)}")
        
        # Ограничиваем количество возвращаемых аномалий
        return anomalies[:100]
    
    def _detect_numeric_anomalies(self, df: pd.DataFrame) -> List[AnomalyInfo]:
        """Обнаруживает аномалии в числовых данных."""
        anomalies = []
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            try:
                non_null_data = df[column].dropna()
                if len(non_null_data) < 10:  # Недостаточно данных для анализа
                    continue
                
                # Метод 1: Z-score анализ
                z_score_anomalies = self._detect_z_score_anomalies(non_null_data, column)
                anomalies.extend(z_score_anomalies)
                
                # Метод 2: IQR метод
                iqr_anomalies = self._detect_iqr_anomalies(non_null_data, column)
                anomalies.extend(iqr_anomalies)
                
                # Метод 3: Модифицированный Z-score (более устойчивый к выбросам)
                modified_z_anomalies = self._detect_modified_z_score_anomalies(non_null_data, column)
                anomalies.extend(modified_z_anomalies)
                
            except Exception as e:
                self.logger.warning(f"Ошибка при анализе числовой колонки {column}: {str(e)}")
        
        return anomalies
    
    def _detect_z_score_anomalies(self, data: pd.Series, column: str) -> List[AnomalyInfo]:
        """Обнаруживает аномалии методом Z-score."""
        anomalies = []
        
        try:
            mean_val = data.mean()
            std_val = data.std()
            
            if std_val == 0:  # Все значения одинаковые
                return anomalies
            
            z_scores = np.abs((data - mean_val) / std_val)
            outlier_indices = data[z_scores > self.thresholds['z_score']].index
            
            for idx in outlier_indices[:20]:  # Ограничиваем количество
                anomalies.append(AnomalyInfo(
                    anomaly_id=f"z_score_{column}_{idx}",
                    column=column,
                    anomaly_type="z_score_outlier",
                    value=float(data.loc[idx]),
                    score=float(z_scores.loc[idx]),
                    method="Z-Score",
                    description=f"Z-score выброс в колонке {column}: значение {data.loc[idx]:.2f} (Z-score: {z_scores.loc[idx]:.2f})"
                ))
                
        except Exception as e:
            self.logger.warning(f"Ошибка в Z-score анализе для {column}: {str(e)}")
        
        return anomalies
    
    def _detect_iqr_anomalies(self, data: pd.Series, column: str) -> List[AnomalyInfo]:
        """Обнаруживает аномалии методом межквартильного размаха (IQR)."""
        anomalies = []
        
        try:
            q1 = data.quantile(0.25)
            q3 = data.quantile(0.75)
            iqr = q3 - q1
            
            if iqr == 0:  # Нет разброса в данных
                return anomalies
            
            lower_bound = q1 - self.thresholds['iqr_multiplier'] * iqr
            upper_bound = q3 + self.thresholds['iqr_multiplier'] * iqr
            
            outliers = data[(data < lower_bound) | (data > upper_bound)]
            
            for idx, value in outliers.head(20).items():  # Ограничиваем количество
                # Вычисляем оценку аномальности
                if value < lower_bound:
                    score = (lower_bound - value) / iqr
                else:
                    score = (value - upper_bound) / iqr
                
                anomalies.append(AnomalyInfo(
                    anomaly_id=f"iqr_{column}_{idx}",
                    column=column,
                    anomaly_type="iqr_outlier",
                    value=float(value),
                    score=float(score),
                    method="IQR",
                    description=f"IQR выброс в колонке {column}: значение {value:.2f} (границы: {lower_bound:.2f} - {upper_bound:.2f})"
                ))
                
        except Exception as e:
            self.logger.warning(f"Ошибка в IQR анализе для {column}: {str(e)}")
        
        return anomalies
    
    def _detect_modified_z_score_anomalies(self, data: pd.Series, column: str) -> List[AnomalyInfo]:
        """Обнаруживает аномалии модифицированным Z-score (на основе медианы)."""
        anomalies = []
        
        try:
            median_val = data.median()
            mad = np.median(np.abs(data - median_val))  # Медианное абсолютное отклонение
            
            if mad == 0:  # Нет разброса в данных
                return anomalies
            
            # Модифицированный Z-score
            modified_z_scores = 0.6745 * (data - median_val) / mad
            outlier_indices = data[np.abs(modified_z_scores) > 3.5].index
            
            for idx in outlier_indices[:15]:  # Ограничиваем количество
                anomalies.append(AnomalyInfo(
                    anomaly_id=f"modified_z_{column}_{idx}",
                    column=column,
                    anomaly_type="modified_z_outlier",
                    value=float(data.loc[idx]),
                    score=float(abs(modified_z_scores.loc[idx])),
                    method="Modified Z-Score",
                    description=f"Модифицированный Z-score выброс в колонке {column}: значение {data.loc[idx]:.2f} (M-Z-score: {modified_z_scores.loc[idx]:.2f})"
                ))
                
        except Exception as e:
            self.logger.warning(f"Ошибка в модифицированном Z-score анализе для {column}: {str(e)}")
        
        return anomalies
    
    def _detect_categorical_anomalies(self, df: pd.DataFrame) -> List[AnomalyInfo]:
        """Обнаруживает аномалии в категориальных данных."""
        anomalies = []
        categorical_columns = df.select_dtypes(include=['object']).columns
        
        for column in categorical_columns:
            try:
                non_null_data = df[column].dropna()
                if len(non_null_data) == 0:
                    continue
                
                # Анализ частоты категорий
                value_counts = non_null_data.value_counts()
                total_count = len(non_null_data)
                
                # Находим редкие категории
                rare_categories = value_counts[value_counts / total_count < self.thresholds['rare_category_threshold']]
                
                for category, count in rare_categories.head(10).items():
                    frequency = count / total_count
                    
                    # Находим индексы строк с редкой категорией
                    category_indices = non_null_data[non_null_data == category].index
                    
                    for idx in category_indices[:5]:  # Ограничиваем количество примеров
                        anomalies.append(AnomalyInfo(
                            anomaly_id=f"rare_category_{column}_{idx}",
                            column=column,
                            anomaly_type="rare_category",
                            value=str(category),
                            score=1 - frequency,  # Чем реже, тем выше оценка аномальности
                            method="Frequency Analysis",
                            description=f"Редкая категория в колонке {column}: '{category}' (частота: {frequency:.3f})"
                        ))
                
                # Анализ неожиданных форматов
                format_anomalies = self._detect_format_anomalies(non_null_data, column)
                anomalies.extend(format_anomalies)
                
            except Exception as e:
                self.logger.warning(f"Ошибка при анализе категориальной колонки {column}: {str(e)}")
        
        return anomalies
    
    def _detect_format_anomalies(self, data: pd.Series, column: str) -> List[AnomalyInfo]:
        """Обнаруживает аномалии в форматах строковых данных."""
        anomalies = []
        
        try:
            # Анализируем форматы значений
            format_patterns = {}
            
            for idx, value in data.head(1000).items():  # Анализируем первые 1000 значений
                pattern = self._get_string_pattern(str(value))
                if pattern not in format_patterns:
                    format_patterns[pattern] = []
                format_patterns[pattern].append((idx, value))
            
            # Находим редкие форматы
            total_analyzed = sum(len(indices) for indices in format_patterns.values())
            
            for pattern, indices_values in format_patterns.items():
                frequency = len(indices_values) / total_analyzed
                
                if frequency < 0.05 and len(indices_values) < 10:  # Редкие форматы
                    for idx, value in indices_values[:3]:  # Ограничиваем примеры
                        anomalies.append(AnomalyInfo(
                            anomaly_id=f"format_anomaly_{column}_{idx}",
                            column=column,
                            anomaly_type="format_anomaly",
                            value=str(value),
                            score=1 - frequency,
                            method="Format Analysis",
                            description=f"Необычный формат в колонке {column}: '{value}' (паттерн: {pattern})"
                        ))
                        
        except Exception as e:
            self.logger.warning(f"Ошибка при анализе форматов для {column}: {str(e)}")
        
        return anomalies
    
    def _get_string_pattern(self, value: str) -> str:
        """Определяет паттерн строки для анализа форматов."""
        if not value:
            return "empty"
        
        pattern = ""
        for char in value:
            if char.isdigit():
                pattern += "D"
            elif char.isalpha():
                pattern += "A"
            elif char.isspace():
                pattern += "S"
            else:
                pattern += "X"
        
        # Упрощаем паттерн, объединяя последовательные символы
        simplified = ""
        prev_char = ""
        for char in pattern:
            if char != prev_char:
                simplified += char
            prev_char = char
        
        return simplified[:20]  # Ограничиваем длину паттерна
    
    def _detect_temporal_anomalies(self, df: pd.DataFrame) -> List[AnomalyInfo]:
        """Обнаруживает временные аномалии."""
        anomalies = []
        
        # Ищем колонки с датами
        date_columns = df.select_dtypes(include=['datetime64']).columns
        
        # Также проверяем object колонки, которые могут содержать даты
        for column in df.select_dtypes(include=['object']).columns:
            if any(keyword in column.lower() for keyword in ['date', 'time', 'created', 'updated']):
                try:
                    # Пытаемся преобразовать в дату
                    sample_data = df[column].dropna().head(100)
                    if len(sample_data) > 0:
                        pd.to_datetime(sample_data.iloc[0])
                        date_columns = date_columns.union([column])
                except:
                    pass
        
        for column in date_columns:
            try:
                # Преобразуем в datetime если нужно
                if df[column].dtype == 'object':
                    date_data = pd.to_datetime(df[column], errors='coerce')
                else:
                    date_data = df[column]
                
                date_data = date_data.dropna()
                if len(date_data) == 0:
                    continue
                
                # Проверяем на даты в будущем
                future_dates = date_data[date_data > pd.Timestamp.now()]
                for idx, date_val in future_dates.head(10).items():
                    days_in_future = (date_val - pd.Timestamp.now()).days
                    
                    if days_in_future > 365:  # Более года в будущем
                        anomalies.append(AnomalyInfo(
                            anomaly_id=f"future_date_{column}_{idx}",
                            column=column,
                            anomaly_type="future_date",
                            value=str(date_val),
                            score=min(days_in_future / 365, 10),  # Нормализуем оценку
                            method="Temporal Analysis",
                            description=f"Дата в далеком будущем в колонке {column}: {date_val} ({days_in_future} дней)"
                        ))
                
                # Проверяем на очень старые даты
                very_old_dates = date_data[date_data < pd.Timestamp('1900-01-01')]
                for idx, date_val in very_old_dates.head(10).items():
                    anomalies.append(AnomalyInfo(
                        anomaly_id=f"old_date_{column}_{idx}",
                        column=column,
                        anomaly_type="very_old_date",
                        value=str(date_val),
                        score=5.0,
                        method="Temporal Analysis",
                        description=f"Очень старая дата в колонке {column}: {date_val}"
                    ))
                
                # Анализ временных промежутков (если данные отсортированы)
                if len(date_data) > 10:
                    time_gaps = self._analyze_time_gaps(date_data, column)
                    anomalies.extend(time_gaps)
                    
            except Exception as e:
                self.logger.warning(f"Ошибка при анализе временной колонки {column}: {str(e)}")
        
        return anomalies
    
    def _analyze_time_gaps(self, date_data: pd.Series, column: str) -> List[AnomalyInfo]:
        """Анализирует промежутки между датами."""
        anomalies = []
        
        try:
            sorted_dates = date_data.sort_values()
            if len(sorted_dates) < 2:
                return anomalies
            
            # Вычисляем промежутки между соседними датами
            time_diffs = sorted_dates.diff().dt.days
            time_diffs = time_diffs.dropna()
            
            if len(time_diffs) == 0:
                return anomalies
            
            # Находим аномально большие промежутки
            median_diff = time_diffs.median()
            q3 = time_diffs.quantile(0.75)
            
            # Аномально большие промежутки (более чем в 5 раз больше медианы)
            large_gaps = time_diffs[time_diffs > max(median_diff * 5, q3 * 2)]
            
            for idx, gap_days in large_gaps.head(5).items():
                anomalies.append(AnomalyInfo(
                    anomaly_id=f"time_gap_{column}_{idx}",
                    column=column,
                    anomaly_type="large_time_gap",
                    value=f"{gap_days} days",
                    score=min(gap_days / median_diff, 10) if median_diff > 0 else 5,
                    method="Time Gap Analysis",
                    description=f"Аномально большой временной промежуток в колонке {column}: {gap_days} дней"
                ))
                
        except Exception as e:
            self.logger.warning(f"Ошибка при анализе временных промежутков для {column}: {str(e)}")
        
        return anomalies
    
    def _detect_multivariate_anomalies(self, df: pd.DataFrame) -> List[AnomalyInfo]:
        """Обнаруживает многомерные аномалии с использованием Isolation Forest."""
        anomalies = []
        
        try:
            # Выбираем только числовые колонки для многомерного анализа
            numeric_df = df.select_dtypes(include=[np.number])
            
            if numeric_df.shape[1] < 2:  # Нужно минимум 2 числовые колонки
                return anomalies
            
            # Удаляем строки с пропущенными значениями
            clean_df = numeric_df.dropna()
            
            if len(clean_df) < 10:  # Недостаточно данных
                return anomalies
            
            # Нормализуем данные
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(clean_df)
            
            # Применяем Isolation Forest
            isolation_forest = IsolationForest(
                contamination=self.thresholds['isolation_contamination'],
                random_state=42,
                n_estimators=100
            )
            
            outlier_labels = isolation_forest.fit_predict(scaled_data)
            outlier_scores = isolation_forest.decision_function(scaled_data)
            
            # Находим аномалии
            outlier_indices = clean_df.index[outlier_labels == -1]
            
            for i, idx in enumerate(outlier_indices[:20]):  # Ограничиваем количество
                score = abs(outlier_scores[i])
                
                # Определяем, какие колонки вносят наибольший вклад в аномальность
                row_data = clean_df.loc[idx]
                contributing_columns = []
                
                for col in numeric_df.columns:
                    col_z_score = abs((row_data[col] - numeric_df[col].mean()) / (numeric_df[col].std() + 1e-6))
                    if col_z_score > 2:  # Значительное отклонение
                        contributing_columns.append(f"{col}={row_data[col]:.2f}")
                
                anomalies.append(AnomalyInfo(
                    anomaly_id=f"multivariate_{idx}",
                    column="multivariate",
                    anomaly_type="multivariate_outlier",
                    value=f"Row {idx}: {', '.join(contributing_columns[:3])}",
                    score=float(score),
                    method="Isolation Forest",
                    description=f"Многомерная аномалия в строке {idx}: необычная комбинация значений"
                ))
                
        except Exception as e:
            self.logger.warning(f"Ошибка при многомерном анализе аномалий: {str(e)}")
        
        return anomalies
