"""
Мастер-оркестратор для Airflow интеграции
Расширяет функциональность Модуля 4 и добавляет планирование модулей 1,2,3,5
"""

from .master_orchestrator import MasterOrchestrator
from .module_scheduler import ModuleScheduler
from .dag_composer import DAGComposer
from .execution_monitor import ExecutionMonitor

__version__ = "1.0.0"
__author__ = "AiEasyData Team"

__all__ = [
    "MasterOrchestrator",
    "ModuleScheduler", 
    "DAGComposer",
    "ExecutionMonitor"
]
