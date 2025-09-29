#!/usr/bin/env python3
"""
Валидация существования функций перед созданием DAG'ов
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags'))

try:
    from orchestrator.module_scheduler import ModuleScheduler
except ImportError as e:
    print(f"Error: Could not import ModuleScheduler: {e}")
    exit(1)

def validate_functions_exist():
    """Проверка существования всех функций перед созданием DAG'ов"""
    print("ВАЛИДАЦИЯ СУЩЕСТВОВАНИЯ ФУНКЦИЙ")
    print("=" * 50)
    
    scheduler = ModuleScheduler()
    
    # Проверяем доступные модули
    print("\nДОСТУПНЫЕ МОДУЛИ:")
    for module_id, config in scheduler.SCHEDULABLE_MODULES.items():
        print(f"  Модуль {module_id}: {config['name']}")
    
    # Проверяем доступные функции
    print(f"\nДОСТУПНЫЕ ФУНКЦИИ ({len(scheduler.SCHEDULABLE_FUNCTIONS)}):")
    for func_name, config in scheduler.SCHEDULABLE_FUNCTIONS.items():
        print(f"  {func_name}: Модуль {config['module']} - {config['description']}")
    
    return scheduler

def create_validated_dag_config():
    """Создание конфигурации DAG'а только с проверенными функциями"""
    scheduler = validate_functions_exist()
    
    print(f"\nСОЗДАНИЕ ВАЛИДИРОВАННОЙ КОНФИГУРАЦИИ DAG'А")
    print("=" * 50)
    
    # Функции, которые мы хотим использовать
    required_functions = [
        "auto_detect_source",
        "validate_file_direct", 
        "execute_scenario",
        "monitor_specific_source",
        "collect_by_design"
    ]
    
    # Проверяем существование каждой функции
    validated_functions = []
    missing_functions = []
    
    for func_name in required_functions:
        if func_name in scheduler.SCHEDULABLE_FUNCTIONS:
            validated_functions.append(func_name)
            config = scheduler.SCHEDULABLE_FUNCTIONS[func_name]
            print(f"  НАЙДЕНА: {func_name} -> {config['endpoint']}")
        else:
            missing_functions.append(func_name)
            print(f"  ОТСУТСТВУЕТ: {func_name}")
    
    # Модули, которые мы хотим использовать
    required_modules = [1, 2, 3, 5]
    validated_modules = []
    missing_modules = []
    
    for module_id in required_modules:
        if module_id in scheduler.SCHEDULABLE_MODULES:
            validated_modules.append(module_id)
            config = scheduler.SCHEDULABLE_MODULES[module_id]
            print(f"  НАЙДЕН: Модуль {module_id} -> {config['bulk_endpoint']}")
        else:
            missing_modules.append(module_id)
            print(f"  ОТСУТСТВУЕТ: Модуль {module_id}")
    
    # Создаем конфигурацию только с проверенными элементами
    config = {
        "pipeline_name": "validated_full_test",
        "schedule": "0 4 * * *",
        "description": "Полный тест с валидированными функциями",
        "stages": []
    }
    
    # Добавляем этапы только для существующих функций/модулей
    stage_counter = 1
    
    if "auto_detect_source" in validated_functions:
        config["stages"].append({
            "stage_name": f"stage_{stage_counter}_auto_detect",
            "type": "function_call",
            "function": "auto_detect_source",
            "endpoint": "/api/v1/metrics/auto-detect",
            "method": "GET",
            "parameters": {"source": "/data/raw"},
            "depends_on": []
        })
        stage_counter += 1
    
    if 1 in validated_modules:
        config["stages"].append({
            "stage_name": f"stage_{stage_counter}_validate",
            "type": "module_call",
            "module": 1,
            "endpoint": "/api/v1/data-quality/batch-validate",
            "method": "POST",
            "parameters": {
                "sources": [
                    {
                        "source_id": "test_csv",
                        "source_type": "file",
                        "path": "/data/raw/sales.csv"
                    }
                ],
                "validation_options": {
                    "check_duplicates": True,
                    "detect_anomalies": True,
                    "assess_quality": True
                }
            },
            "depends_on": [f"stage_{stage_counter-1}_auto_detect"] if stage_counter > 1 else []
        })
        stage_counter += 1
    
    if 2 in validated_modules:
        config["stages"].append({
            "stage_name": f"stage_{stage_counter}_aggregate",
            "type": "module_call",
            "module": 2,
            "endpoint": "/api/v1/aggregation/create-scenario",
            "method": "POST",
            "parameters": {
                "name": "validated_test_scenario",
                "description": "Validated test scenario",
                "sources": [
                    {
                        "source_id": "test_data",
                        "source_type": "file",
                        "path": "/data/raw/sales.csv",
                        "selected_columns": []
                    }
                ],
                "aggregations": [
                    {
                        "type": "group_by",
                        "parameters": {
                            "group_by_columns": ["sale_date"],
                            "aggregation_functions": [
                                {"column": "amount", "function": "sum"}
                            ]
                        }
                    }
                ],
                "target_requirements": {
                    "expected_volume": "medium",
                    "performance_priority": "balanced"
                }
            },
            "depends_on": [f"stage_{stage_counter-1}_validate"] if stage_counter > 1 else []
        })
        stage_counter += 1
    
    if 3 in validated_modules:
        config["stages"].append({
            "stage_name": f"stage_{stage_counter}_analyze",
            "type": "module_call",
            "module": 3,
            "endpoint": "/api/v1/performance/bulk-analyze",
            "method": "POST",
            "parameters": ["/data/raw/sales.csv"],
            "depends_on": [f"stage_{stage_counter-1}_aggregate"] if stage_counter > 1 else []
        })
        stage_counter += 1
    
    if "monitor_specific_source" in validated_functions:
        config["stages"].append({
            "stage_name": f"stage_{stage_counter}_monitor",
            "type": "function_call",
            "function": "monitor_specific_source",
            "endpoint": "/api/v1/metrics/collect",
            "method": "POST",
            "parameters": {
                "db_type": "postgres",
                "host": "localhost",
                "port": 5432,
                "db_name": "analytics",
                "user": "postgres",
                "password": "password"
            },
            "depends_on": [f"stage_{stage_counter-1}_analyze"] if stage_counter > 1 else []
        })
        stage_counter += 1
    
    print(f"\nВАЛИДИРОВАННАЯ КОНФИГУРАЦИЯ:")
    print(f"  Этапов: {len(config['stages'])}")
    print(f"  Проверенных функций: {len(validated_functions)}")
    print(f"  Проверенных модулей: {len(validated_modules)}")
    
    if missing_functions:
        print(f"\nОТСУТСТВУЮЩИЕ ФУНКЦИИ: {missing_functions}")
    if missing_modules:
        print(f"ОТСУТСТВУЮЩИЕ МОДУЛИ: {missing_modules}")
    
    return config

def create_validated_dag():
    """Создание DAG'а с валидированными функциями"""
    try:
        from orchestrator.master_orchestrator import MasterOrchestrator
    except ImportError as e:
        print(f"Error: Could not import MasterOrchestrator: {e}")
        return None
    
    config = create_validated_dag_config()
    
    if not config["stages"]:
        print("ОШИБКА: Нет доступных этапов для создания DAG'а")
        return None
    
    orchestrator = MasterOrchestrator()
    
    try:
        pipeline = orchestrator.create_master_pipeline(config)
        print(f"\nУСПЕХ! Создан валидированный DAG: {pipeline.master_dag_id}")
        print(f"Файл: {pipeline.dag_file_path}")
        print(f"Этапов: {pipeline.stages_count}")
        return pipeline.master_dag_id
    except Exception as e:
        print(f"ОШИБКА создания DAG: {str(e)}")
        return None

if __name__ == "__main__":
    result = create_validated_dag()
    
    if result:
        print(f"\nВАЛИДИРОВАННЫЙ DAG СОЗДАН: {result}")
        print("DAG использует только проверенные функции и модули")
    else:
        print("\nОШИБКА: Не удалось создать валидированный DAG")
