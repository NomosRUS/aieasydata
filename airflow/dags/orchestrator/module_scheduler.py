"""
ModuleScheduler - Гибридный планировщик для модулей и отдельных функций
Поддерживает как модульное планирование (массовые операции), так и функциональное (точечные операции)
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests
import json

logger = logging.getLogger(__name__)

@dataclass
class ScheduledTask:
    """Запланированная задача"""
    task_id: str
    task_type: str  # "module" или "function"
    module: Optional[int]
    endpoint: str
    method: str
    parameters: Dict[str, Any]
    schedule: str
    description: str
    created_at: datetime
    next_run: datetime
    status: str = "active"

class ModuleScheduler:
    """Гибридный планировщик для выполнения модулей и отдельных функций"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        
        # Конфигурация модулей для массовых операций
        self.SCHEDULABLE_MODULES = {
            1: {
                "name": "Data Validation Module",
                "bulk_endpoint": "/api/v1/data-quality/batch-validate",
                "health_check": "/api/v1/data-quality/health-check",
                "method": "POST",
                "default_schedule": "0 2 * * *",  # Ежедневно в 02:00
                "description": "Массовая валидация всех источников данных"
            },
            2: {
                "name": "Data Aggregation Module",
                "bulk_endpoint": "/api/v1/aggregation/create-scenario",  # Создание сценария агрегации
                "health_check": "/api/v1/aggregation/health-check",
                "method": "POST", 
                "default_schedule": "0 3 * * *",  # После валидации
                "description": "Создание и выполнение сценариев агрегации"
            },
            3: {
                "name": "Performance Optimization Module",
                "bulk_endpoint": "/api/v1/performance/bulk-analyze",
                "health_check": "/api/v1/performance/health-check",
                "method": "POST",
                "default_schedule": "0 1 * * 0",  # Еженедельно
                "description": "Массовый анализ производительности всех хранилищ"
            },
            5: {
                "name": "Metrics Collection Module",
                "bulk_endpoint": "/api/v1/metrics/comprehensive-test",
                "health_check": "/api/v1/metrics/health-check",
                "method": "GET",
                "default_schedule": "0 * * * *",  # Каждый час
                "description": "Комплексный сбор метрик со всех источников"
            }
        }
        
        # Конфигурация отдельных функций для точечных операций
        self.SCHEDULABLE_FUNCTIONS = {
            # Модуль 1 - Детальные функции валидации (19 endpoints)
            "validate_file_direct": {
                "module": 1,
                "endpoint": "/api/v1/data-quality/validate-file",
                "method": "POST",
                "parameters": {"file_path": "configurable", "validation_options": "configurable"},
                "schedule_type": "on_demand",
                "description": "Прямая валидация файла по пути"
            },
            "check_folder_homogeneity": {
                "module": 1,
                "endpoint": "/api/v1/data-quality/check-homogeneity",
                "method": "POST",
                "parameters": {"folder_path": "configurable", "auto_separate": "configurable"},
                "schedule_type": "daily",
                "description": "Проверка однородности файлов в папке"
            },
            "clean_data_source": {
                "module": 1,
                "endpoint": "/api/v1/data-quality/clean/{profile_id}",
                "method": "POST",
                "parameters": {"profile_id": "configurable", "strategy": "auto"},
                "schedule_type": "on_demand",
                "description": "Очистка конкретного источника данных"
            },
            "analyze_data_quality": {
                "module": 1,
                "endpoint": "/api/v1/data-quality/analyze-quality",
                "method": "POST",
                "parameters": {"source_data": "configurable"},
                "schedule_type": "weekly",
                "description": "Детальный анализ качества данных"
            },
            
            # Модуль 2 - Специфические агрегации (15 endpoints)
            "execute_scenario": {
                "module": 2,
                "endpoint": "/api/v1/aggregation/execute/{scenario_id}",
                "method": "POST",
                "parameters": {"scenario_id": "configurable"},
                "schedule_type": "configurable",
                "description": "Выполнение конкретного сценария агрегации"
            },
            "create_custom_dataset": {
                "module": 2,
                "endpoint": "/api/v1/aggregation/custom-dataset",
                "method": "POST",
                "parameters": {"dataset_config": "configurable"},
                "schedule_type": "on_demand",
                "description": "Создание кастомного набора данных"
            },
            "preview_join_operation": {
                "module": 2,
                "endpoint": "/api/v1/aggregation/preview-join",
                "method": "POST",
                "parameters": {"join_config": "configurable"},
                "schedule_type": "on_demand",
                "description": "Предварительный просмотр JOIN операции"
            },
            
            # Модуль 3 - Специфические оптимизации (10 endpoints)
            "analyze_performance": {
                "module": 3,
                "endpoint": "/api/v1/performance/analyze",
                "method": "POST",
                "parameters": {"source": "configurable"},
                "schedule_type": "weekly",
                "description": "Анализ производительности конкретного источника"
            },
            "apply_optimizations": {
                "module": 3,
                "endpoint": "/api/v1/performance/optimize/{analysis_id}",
                "method": "POST",
                "parameters": {
                    "analysis_id": "configurable",
                    "recommendation_ids": ["partition", "index", "compression"],
                    "confirm_application": False,
                    "dry_run": True
                },
                "schedule_type": "on_demand",
                "description": "Применение оптимизаций по результатам анализа"
            },
            "get_recommendations": {
                "module": 3,
                "endpoint": "/api/v1/performance/recommendations/{table_name}",
                "method": "GET",
                "parameters": {"table_name": "configurable"},
                "schedule_type": "weekly",
                "description": "Получение рекомендаций для таблицы"
            },
            
            # Модуль 5 - Специфический мониторинг (9 endpoints)
            "monitor_specific_source": {
                "module": 5,
                "endpoint": "/api/v1/metrics/collect",
                "method": "POST",
                "parameters": {"connection_info": "configurable"},
                "schedule_type": "hourly",
                "description": "Мониторинг конкретного источника данных"
            },
            "auto_detect_source": {
                "module": 5,
                "endpoint": "/api/v1/metrics/auto-detect",
                "method": "GET",
                "parameters": {"source": "configurable"},
                "schedule_type": "on_demand",
                "description": "Автоопределение типа данных источника"
            },
            "collect_by_design": {
                "module": 5,
                "endpoint": "/api/v1/metrics/collect-by-design/{design_id}",
                "method": "POST",
                "parameters": {"design_id": "configurable"},
                "schedule_type": "daily",
                "description": "Сбор метрик по design_id из модуля 4"
            }
        }
    
    def schedule_module_execution(self, module: int, schedule: str, config: Dict[str, Any] = None) -> ScheduledTask:
        """Создание расписания для целого модуля (массовые операции)"""
        if module not in self.SCHEDULABLE_MODULES:
            raise ValueError(f"Module {module} is not schedulable")
        
        module_config = self.SCHEDULABLE_MODULES[module]
        task_id = f"module_{module}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task = ScheduledTask(
            task_id=task_id,
            task_type="module",
            module=module,
            endpoint=module_config["bulk_endpoint"],
            method=module_config["method"],
            parameters=config or {},
            schedule=schedule,
            description=module_config["description"],
            created_at=datetime.now(),
            next_run=self._calculate_next_run(schedule)
        )
        
        self.scheduled_tasks[task_id] = task
        logger.info(f"Scheduled module {module} execution: {task_id}")
        return task
    
    def schedule_function_execution(self, function_name: str, schedule: str, parameters: Dict[str, Any]) -> ScheduledTask:
        """Создание расписания для отдельной функции (точечные операции)"""
        if function_name not in self.SCHEDULABLE_FUNCTIONS:
            raise ValueError(f"Function {function_name} is not schedulable")
        
        func_config = self.SCHEDULABLE_FUNCTIONS[function_name]
        task_id = f"function_{function_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Подставляем параметры в endpoint если нужно
        endpoint = func_config["endpoint"]
        for param_name, param_value in parameters.items():
            if f"{{{param_name}}}" in endpoint:
                endpoint = endpoint.replace(f"{{{param_name}}}", str(param_value))
        
        task = ScheduledTask(
            task_id=task_id,
            task_type="function",
            module=func_config["module"],
            endpoint=endpoint,
            method=func_config["method"],
            parameters=parameters,
            schedule=schedule,
            description=func_config["description"],
            created_at=datetime.now(),
            next_run=self._calculate_next_run(schedule)
        )
        
        self.scheduled_tasks[task_id] = task
        logger.info(f"Scheduled function {function_name} execution: {task_id}")
        return task
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Выполнение запланированной задачи"""
        if task_id not in self.scheduled_tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.scheduled_tasks[task_id]
        url = f"{self.base_url}{task.endpoint}"
        
        try:
            logger.info(f"Executing task {task_id}: {task.method} {url}")
            
            if task.method == "GET":
                response = requests.get(url, params=task.parameters, timeout=300)
            elif task.method == "POST":
                response = requests.post(url, json=task.parameters, timeout=300)
            else:
                raise ValueError(f"Unsupported method: {task.method}")
            
            response.raise_for_status()
            result = response.json() if response.content else {}
            
            # Обновляем время следующего запуска
            task.next_run = self._calculate_next_run(task.schedule)
            
            logger.info(f"Task {task_id} executed successfully")
            return {
                "task_id": task_id,
                "status": "success",
                "result": result,
                "executed_at": datetime.now().isoformat(),
                "next_run": task.next_run.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Task {task_id} execution failed: {str(e)}")
            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "executed_at": datetime.now().isoformat(),
                "next_run": task.next_run.isoformat()
            }
    
    def get_scheduled_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получение списка запланированных задач"""
        tasks = []
        for task in self.scheduled_tasks.values():
            if status is None or task.status == status:
                tasks.append({
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "module": task.module,
                    "endpoint": task.endpoint,
                    "method": task.method,
                    "schedule": task.schedule,
                    "description": task.description,
                    "status": task.status,
                    "created_at": task.created_at.isoformat(),
                    "next_run": task.next_run.isoformat()
                })
        return tasks
    
    def check_module_health(self, module: int) -> Dict[str, Any]:
        """Проверка работоспособности модуля"""
        if module not in self.SCHEDULABLE_MODULES:
            return {"status": "error", "message": f"Module {module} not configured"}
        
        module_config = self.SCHEDULABLE_MODULES[module]
        health_url = f"{self.base_url}{module_config['health_check']}"
        
        try:
            response = requests.get(health_url, timeout=10)
            response.raise_for_status()
            return {
                "module": module,
                "status": "healthy",
                "response": response.json() if response.content else {},
                "checked_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "module": module,
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def _calculate_next_run(self, schedule: str) -> datetime:
        """Вычисление времени следующего запуска на основе cron расписания"""
        # Упрощенная реализация - в реальности нужно использовать croniter
        # Для демонстрации добавляем 1 час к текущему времени
        return datetime.now() + timedelta(hours=1)
    
    def get_available_modules(self) -> Dict[int, Dict[str, Any]]:
        """Получение списка доступных для планирования модулей"""
        return self.SCHEDULABLE_MODULES
    
    def get_available_functions(self) -> Dict[str, Dict[str, Any]]:
        """Получение списка доступных для планирования функций"""
        return self.SCHEDULABLE_FUNCTIONS
