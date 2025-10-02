"""
Модуль интеллектуальной агрегации и обогащения данных.

Этот модуль предоставляет функциональность для:
- Создания кастомизированных наборов данных из разных источников
- Выполнения сложных агрегаций и JOIN операций
- Автогенерации оптимизаций (индексы, партиции)
- Интеграции с модулями 3, 4, 5
"""

__version__ = "1.0.0"
__author__ = "AiEasyData Team"

from .main import DataAggregator
from .schemas import (
    DataSource,
    AggregationRule,
    EnrichmentRule,
    AggregationScenarioRequest,
    AggregationScenarioResponse,
    CustomDatasetRequest,
    ExecutionResult
)

__all__ = [
    "DataAggregator",
    "DataSource",
    "AggregationRule", 
    "EnrichmentRule",
    "AggregationScenarioRequest",
    "AggregationScenarioResponse",
    "CustomDatasetRequest",
    "ExecutionResult"
]
