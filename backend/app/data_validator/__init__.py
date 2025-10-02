"""
Модуль валидации, оценки качества и очистки данных.

Этот модуль предоставляет интеллектуальные инструменты для:
- Валидации данных из различных источников
- Оценки качества данных с присвоением оценки
- Статистического анализа аномалий
- Проверки однородности файлов в папках
- Автоматической очистки данных
- Генерации рекомендаций по хранению

Автор: Алексей
Версия: 1.0.0
Дата создания: 2025-09-27
"""

from .main import DataValidator
from .schemas import (
    DataSource,
    ValidationResult,
    QualityIssue,
    ValidationMetadata,
    StorageRecommendation,
    HomogeneityResult
)

__version__ = "1.0.0"
__author__ = "Алексей"

__all__ = [
    "DataValidator",
    "DataSource",
    "ValidationResult", 
    "QualityIssue",
    "ValidationMetadata",
    "StorageRecommendation",
    "HomogeneityResult"
]
