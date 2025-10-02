# ЗАДАЧА 6: Расширение Airflow интеграции и создание мастер-оркестратора

**Исполнитель**: Команда разработчиков  
**Ветка Git**: `feature/airflow-orchestrator`  
**Расположение модуля**: `airflow/dags/orchestrator/`

## **1. Цель и концепция**

Создать **мастер-оркестратор** `airflow_orchestrator`, который расширяет существующую функциональность Модуля 4 по генерации DAG'ов и добавляет возможности планирования и мониторинга выполнения модулей 1,2,3,5 по расписанию. Система будет выполнять четыре ключевые функции:

1. **Интеграция с Модулем 4**: Использование существующей системы генерации DAG'ов
2. **Мастер-планировщик**: Создание сложных многоэтапных пайплайнов
3. **Мониторинг выполнения**: Отслеживание статуса и обработка ошибок
4. **Расписание модулей**: Автоматическое выполнение модулей 1,2,3,5 по расписанию

**Уровень реализации**: **Базовый**. Основной фокус — на интеграции с существующей системой и создании мастер-пайплайнов.

## **2. Архитектурное место в системе**

- **НЕ дублирует** функциональность Модуля 4 по генерации DAG'ов
- **Расширяет** существующую систему, добавляя оркестрацию
- Использует готовые DAG'и из Модуля 4 как строительные блоки
- Создает мастер-пайплайны, координирующие выполнение нескольких модулей

## **3. Интеграция с существующей системой**

### **3.1. Использование DAG'ов Модуля 4**
**Модуль 4 уже генерирует DAG'и через:**
```python
# Существующая функция в Модуле 4
generate_etl_pipeline(design_id: str, context: Dict, selected_db: str) -> Dict
```

**Выходные данные Модуля 4:**
```python
{
    "success": bool,
    "dag_id": str,  # "etl_sales_clickhouse_20250927"
    "dag_file_path": str,  # "/opt/airflow/dags/etl_sales_clickhouse_20250927.py"
    "source_config": {...},
    "target_config": {...}
}
```

### **3.2. Новая роль: Мастер-оркестратор**
**Задача 6 создает НАД-систему, которая:**
- Использует готовые DAG'и от Модуля 4
- Создает мастер-пайплайны из нескольких DAG'ов
- Добавляет планирование для модулей 1,2,3,5
- Обеспечивает мониторинг и обработку ошибок

## **4. Архитектура оркестратора**

```
airflow/dags/orchestrator/
├── __init__.py
├── master_orchestrator.py         # Главный класс оркестратора
├── dag_composer.py                # Композиция DAG'ов из Модуля 4
├── module_scheduler.py            # Планировщик для модулей 1,2,3,5
├── execution_monitor.py           # Мониторинг выполнения
├── templates/                     # Шаблоны мастер-пайплайнов
│   ├── daily_full_pipeline.py.j2
│   ├── weekly_optimization.py.j2
│   └── streaming_pipeline.py.j2
└── generated/                     # Сгенерированные мастер-DAG'и
    ├── master_daily_etl.py
    ├── master_weekly_optimization.py
    └── master_streaming_process.py
```

## **5. Основные классы и функции**

### **5.1. MasterOrchestrator (master_orchestrator.py)**
**Назначение:** Главный класс для создания мастер-пайплайнов

#### `create_master_pipeline(pipeline_config: PipelineConfig) -> MasterPipeline`
**Назначение:** Создание сложного пайплайна из нескольких этапов

**Входные параметры:**
```python
PipelineConfig = {
    "pipeline_name": str,
    "schedule": str,  # cron expression
    "stages": [
        {
            "stage_name": str,
            "type": "module_call" | "dag_execution",
            "module": int,  # 1,2,3,5 для module_call
            "dag_id": str,  # для dag_execution (из Модуля 4)
            "depends_on": List[str],  # зависимости от других этапов
            "retry_count": int,
            "timeout": int
        }
    ],
    "notifications": {
        "on_success": List[str],
        "on_failure": List[str]
    }
}
```

**Выходные данные:**
```python
MasterPipeline = {
    "master_dag_id": str,
    "dag_file_path": str,
    "stages_count": int,
    "estimated_duration": int,
    "dependencies_graph": dict,
    "created_at": str
}
```

### **5.2. DAGComposer (dag_composer.py)**
**Назначение:** Композиция DAG'ов от Модуля 4 в мастер-пайплайны

#### `compose_etl_pipeline(design_ids: List[str]) -> ComposedDAG`
**Назначение:** Объединение нескольких ETL DAG'ов в один мастер-пайплайн

**Пример использования:**
```python
# Модуль 4 создал 3 DAG'а для разных источников
dag_ids = [
    "etl_sales_clickhouse_001",
    "etl_customers_postgres_002", 
    "etl_products_hdfs_003"
]

# Оркестратор создает мастер-DAG
master_dag = compose_etl_pipeline(dag_ids)
```

### **5.3. ModuleScheduler (module_scheduler.py)**
**Назначение:** Гибридный планировщик для выполнения модулей и отдельных функций

#### `schedule_module_execution(module: int, schedule: str, config: dict) -> ScheduledTask`
**Назначение:** Создание расписания для целого модуля (массовые операции)

**Поддерживаемые модули:**
```python
SCHEDULABLE_MODULES = {
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
        "bulk_endpoint": "/api/v1/aggregation/scenarios",  # Получение всех сценариев + выполнение активных
        "health_check": "/api/v1/aggregation/health-check",
        "method": "GET", 
        "default_schedule": "0 3 * * *",  # После валидации
        "description": "Выполнение всех активных сценариев агрегации"
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
```

#### `schedule_function_execution(function_name: str, schedule: str, parameters: dict) -> ScheduledTask`
**Назначение:** Создание расписания для отдельной функции (точечные операции)

**Поддерживаемые функции:**
```python
SCHEDULABLE_FUNCTIONS = {
    # Модуль 1 - Детальные функции валидации (19 endpoints)
    "validate_specific_source": {
        "module": 1,
        "endpoint": "/api/v1/data-quality/validate/{profile_id}",
        "method": "POST",
        "parameters": {"profile_id": "configurable"},
        "schedule_type": "on_demand",
        "description": "Валидация конкретного источника данных"
    },
    "check_folder_homogeneity": {
        "module": 1,
        "endpoint": "/api/v1/data-quality/check-homogeneity",
        "method": "POST",
        "parameters": {"folder_path": "configurable"},
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
        "parameters": {"analysis_id": "configurable"},
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
```

## **6. Примеры мастер-пайплайнов**

### **6.1. Ежедневный полный ETL (модульный подход)**
```python
# Конфигурация мастер-пайплайна
daily_config = {
    "pipeline_name": "daily_full_etl",
    "schedule": "0 2 * * *",
    "stages": [
        {
            "stage_name": "monitor_sources",
            "type": "module_call",
            "module": 5,
            "endpoint": "/api/v1/metrics/comprehensive-test",
            "depends_on": []
        },
        {
            "stage_name": "validate_data", 
            "type": "module_call",
            "module": 1,
            "endpoint": "/api/v1/data-quality/batch-validate",
            "depends_on": ["monitor_sources"]
        },
        {
            "stage_name": "aggregate_data",
            "type": "module_call", 
            "module": 2,
            "endpoint": "/api/v1/aggregation/scenarios",  # Получение списка сценариев
            "depends_on": ["validate_data"]
        },
        {
            "stage_name": "load_to_warehouses",
            "type": "dag_execution",
            "dag_id": "etl_daily_combined",  # DAG от Модуля 4
            "depends_on": ["aggregate_data"]
        }
    ]
}

master_pipeline = MasterOrchestrator.create_master_pipeline(daily_config)
```

### **6.1.2. Специфическая обработка продаж (функциональный подход)**
```python
# Конфигурация с отдельными функциями
custom_pipeline = {
    "pipeline_name": "sales_data_processing",
    "schedule": "0 6 * * 1",  # Понедельник 06:00
    "stages": [
        {
            "stage_name": "check_sales_homogeneity",
            "type": "function_call",
            "function": "check_folder_homogeneity",
            "parameters": {"folder_path": "/data/sales"},
            "depends_on": []
        },
        {
            "stage_name": "validate_sales_profile",
            "type": "function_call",
            "function": "validate_specific_source",
            "parameters": {"profile_id": "sales_profile_001"},
            "depends_on": ["check_sales_homogeneity"]
        },
        {
            "stage_name": "execute_sales_aggregation",
            "type": "function_call",
            "function": "execute_scenario",
            "parameters": {"scenario_id": "sales_aggregation_weekly"},
            "depends_on": ["validate_sales_profile"]
        },
        {
            "stage_name": "analyze_sales_performance",
            "type": "function_call",
            "function": "analyze_performance",
            "parameters": {"source": "/data/sales_warehouse"},
            "depends_on": ["execute_sales_aggregation"]
        }
    ]
}
```

### **6.1.3. Смешанный пайплайн (гибридный подход)**
```python
# Комбинация модулей и отдельных функций
hybrid_pipeline = {
    "pipeline_name": "hybrid_data_processing",
    "schedule": "0 4 * * *",
    "stages": [
        {
            "stage_name": "bulk_monitoring",
            "type": "module_call",  # Массовый мониторинг
            "module": 5,
            "endpoint": "/api/v1/metrics/comprehensive-test",
            "depends_on": []
        },
        {
            "stage_name": "critical_source_validation",
            "type": "function_call",  # Точечная валидация
            "function": "validate_specific_source",
            "parameters": {"profile_id": "critical_data_001"},
            "depends_on": ["bulk_monitoring"]
        },
        {
            "stage_name": "bulk_aggregation",
            "type": "module_call",  # Массовая агрегация
            "module": 2,
            "endpoint": "/api/v1/aggregation/scenarios",  # Получение списка сценариев
            "depends_on": ["critical_source_validation"]
        },
        {
            "stage_name": "specific_performance_check",
            "type": "function_call",  # Точечная оптимизация
            "function": "analyze_performance",
            "parameters": {"source": "high_priority_warehouse"},
            "depends_on": ["bulk_aggregation"]
        }
    ]
}
```

### **6.2. Еженедельная оптимизация**
```python
weekly_config = {
    "pipeline_name": "weekly_optimization",
    "schedule": "0 1 * * 0",  # Воскресенье 01:00
    "stages": [
        {
            "stage_name": "analyze_performance",
            "type": "module_call",
            "module": 3,
            "endpoint": "/api/v1/performance/bulk-analyze",
            "depends_on": []
        },
        {
            "stage_name": "apply_optimizations",
            "type": "function_call",  # Используем функциональный подход
            "function": "apply_optimizations",
            "parameters": {"analysis_id": "from_previous_stage"},
            "depends_on": ["analyze_performance"]
        },
        {
            "stage_name": "regenerate_warehouses",
            "type": "dag_execution",
            "dag_id": "warehouse_optimization_rebuild",  # DAG от Модуля 4
            "depends_on": ["apply_optimizations"]
        }
    ]
}
```

## **7. Интеграция с Модулем 4**

### **7.1. Использование существующих функций**
```python
# НЕ создаем новые DAG'и, а используем существующие!
class DAGComposer:
    def __init__(self):
        self.module4_client = Module4Client()
    
    def request_dag_from_module4(self, design_id: str) -> str:
        """Запрашивает готовый DAG от Модуля 4"""
        response = self.module4_client.generate_etl_pipeline(design_id)
        return response["dag_file_path"]
    
    def compose_multiple_dags(self, dag_paths: List[str]) -> str:
        """Объединяет несколько DAG'ов в мастер-пайплайн"""
        master_dag_template = self.load_template("master_pipeline.py.j2")
        return master_dag_template.render(
            sub_dags=dag_paths,
            dependencies=self.calculate_dependencies(dag_paths)
        )
```

### **7.2. API интеграция с Модулем 4**
```python
class Module4Integration:
    def get_available_dags(self) -> List[dict]:
        """Получает список доступных DAG'ов от Модуля 4"""
        return requests.get("/api/v1/warehouse/instances").json()
    
    def trigger_dag_generation(self, design_id: str) -> dict:
        """Запускает генерацию DAG'а в Модуле 4"""
        return requests.post(f"/api/v1/warehouse/load-data/{design_id}").json()
    
    def get_dag_status(self, design_id: str) -> dict:
        """Получает статус проектирования хранилища"""
        return requests.get(f"/api/v1/warehouse/design/{design_id}").json()
```

## **8. Мониторинг и обработка ошибок**

### **8.1. ExecutionMonitor (execution_monitor.py)**
```python
class ExecutionMonitor:
    def monitor_master_pipeline(self, master_dag_id: str) -> PipelineStatus:
        """Мониторинг выполнения мастер-пайплайна"""
        stages_status = {}
        
        for stage in self.get_pipeline_stages(master_dag_id):
            if stage["type"] == "module_call":
                status = self.check_module_status(stage["module"], stage["task_id"])
            elif stage["type"] == "dag_execution":
                status = self.check_dag_status(stage["dag_id"])
            
            stages_status[stage["stage_name"]] = status
        
        return PipelineStatus(
            overall_status=self.calculate_overall_status(stages_status),
            stages=stages_status,
            estimated_completion=self.estimate_completion_time(stages_status)
        )
```

## **9. API Endpoints оркестратора**

### **9.1. Управление мастер-пайплайнами**

#### `POST /api/v1/orchestrator/create-master-pipeline`
**Назначение:** Создание нового мастер-пайплайна

**Входные данные:**
```json
{
    "pipeline_name": "daily_sales_processing",
    "description": "Ежедневная обработка данных продаж",
    "schedule": "0 2 * * *",
    "stages": [
        {
            "stage_name": "validate_sales_data",
            "type": "module_call",
            "module": 1,
            "config": {"source_pattern": "sales_*.csv"}
        },
        {
            "stage_name": "load_to_clickhouse", 
            "type": "dag_execution",
            "dag_id": "etl_sales_clickhouse_001"
        }
    ]
}
```

#### `GET /api/v1/orchestrator/pipelines`
**Назначение:** Список всех мастер-пайплайнов

#### `POST /api/v1/orchestrator/trigger/{pipeline_id}`
**Назначение:** Ручной запуск мастер-пайплайна

#### `GET /api/v1/orchestrator/status/{pipeline_id}`
**Назначение:** Статус выполнения мастер-пайплайна

## **10. Тестирование интеграции**

**Интеграционный тест:** `test_orchestrator_integration.py`

**Проверяемые сценарии:**
1. ✅ Интеграция с существующими DAG'ами Модуля 4
2. ✅ Создание мастер-пайплайнов из нескольких этапов
3. ✅ Планирование выполнения модулей 1,2,3,5
4. ✅ Мониторинг и обработка ошибок
5. ✅ Композиция сложных зависимостей между этапами
6. ✅ Уведомления о статусе выполнения
7. ✅ Интеграция с Airflow Web UI

## **11. Соответствие сценариям тестирования**

**Из Задачи 7 - Airflow сценарии (S021-S030):**

- **S021**: ✅ Ежедневный ETL пайплайн - мастер-оркестратор создает из DAG'ов Модуля 4
- **S022**: ✅ Еженедельная оптимизация - планировщик модуля 3
- **S023**: ✅ Ежечасный мониторинг - планировщик модуля 5
- **S024**: ✅ Обработка ошибок - ExecutionMonitor
- **S025**: ✅ Условное выполнение - зависимости в мастер-пайплайнах
- **S026**: ✅ Параллельные DAG'и - композиция нескольких DAG'ов
- **S027**: ✅ Зависимости между DAG'ами - мастер-оркестратор
- **S028**: ✅ Мониторинг производительности - интеграция с модулем 3
- **S029**: ✅ Автоматический перезапуск - retry логика
- **S030**: ✅ Динамическое создание - API для создания пайплайнов

## **12. План работ**

### **Этап 1: Интеграция с Модулем 4 (2 часа)**
1. Создать Module4Client для взаимодействия с существующими DAG'ами
2. Реализовать DAGComposer для объединения DAG'ов
3. Протестировать получение и использование DAG'ов от Модуля 4
4. Создать базовые шаблоны мастер-пайплайнов

### **Этап 2: Планировщик модулей (2 часа)**
1. Реализовать ModuleScheduler для модулей 1,2,3,5
2. Создать конфигурации расписания для каждого модуля
3. Добавить API endpoints для управления расписанием
4. Интегрировать с Airflow scheduler

### **Этап 3: Мастер-оркестратор (1 час)**
1. Реализовать MasterOrchestrator для создания сложных пайплайнов
2. Добавить поддержку зависимостей между этапами
3. Создать систему мониторинга выполнения
4. Добавить обработку ошибок и retry логику

### **Этап 4: Тестирование и документация (1 час)**
1. Создать интеграционные тесты с Модулем 4
2. Протестировать все сценарии из Задачи 7
3. Добавить документацию по использованию
4. Провести end-to-end тестирование мастер-пайплайнов

**Общее время разработки:** 6 часов (базовый уровень сложности)

---

**СТАТУС ТЗ:** 📋 ГОТОВО К РЕАЛИЗАЦИИ

**КЛЮЧЕВЫЕ ПРЕИМУЩЕСТВА ИСПРАВЛЕННОГО ПОДХОДА:**

1. **✅ НЕ дублирует Модуль 4** - использует существующую систему генерации DAG'ов
2. **✅ Расширяет функциональность** - добавляет мастер-оркестрацию
3. **✅ Соответствует ТЗ** - создает пайплайны с использованием готовых операторов
4. **✅ Проверяемо в сценариях** - все сценарии S021-S030 покрыты
5. **✅ Архитектурно правильно** - не создает лишних слоев абстракции

**Мастер-оркестратор интегрируется с проверенной системой Модуля 4 и добавляет возможности планирования и композиции сложных пайплайнов без дублирования функциональности.**
