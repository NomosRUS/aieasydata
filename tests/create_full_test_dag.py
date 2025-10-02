#!/usr/bin/env python3
"""
Создание полного тестового DAG'а со всеми модулями
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags'))

try:
    from orchestrator.master_orchestrator import MasterOrchestrator
except ImportError as e:
    print(f"Error: Could not import orchestrator modules: {e}")
    exit(1)

def create_full_test_dag():
    """Создание полного тестового DAG'а со всеми модулями"""
    print("\n=== СОЗДАНИЕ ПОЛНОГО ТЕСТОВОГО DAG'А ===")
    
    orchestrator = MasterOrchestrator()
    
    config = {
        "pipeline_name": "full_modules_test",
        "schedule": "0 3 * * *",  # Каждый день в 03:00
        "description": "Полный тест всех модулей системы",
        "stages": [
            # ЭТАП 1: Автоопределение источников (Модуль 5)
            {
                "stage_name": "auto_detect_data_sources",
                "type": "function_call",
                "function": "auto_detect_source",
                "endpoint": "/api/v1/metrics/auto-detect",
                "method": "GET",
                "parameters": {"source": "/data/raw"},
                "depends_on": []
            },
            
            # ЭТАП 2: Валидация данных (Модуль 1)
            {
                "stage_name": "validate_all_sources",
                "type": "module_call",
                "module": 1,
                "endpoint": "/api/v1/data-quality/batch-validate",
                "method": "POST",
                "parameters": {
                    "sources": [
                        {
                            "source_id": "sales_csv",
                            "source_type": "file",
                            "path": "/data/raw/sales.csv"
                        },
                        {
                            "source_id": "customers_json", 
                            "source_type": "file",
                            "path": "/data/syn_json"
                        }
                    ],
                    "validation_options": {
                        "check_duplicates": True,
                        "detect_anomalies": True,
                        "assess_quality": True
                    }
                },
                "depends_on": ["auto_detect_data_sources"]
            },
            
            # ЭТАП 3: Агрегация данных (Модуль 2)
            {
                "stage_name": "create_aggregation_scenario",
                "type": "module_call",
                "module": 2,
                "endpoint": "/api/v1/aggregation/create-scenario",
                "method": "POST",
                "parameters": {
                    "name": "full_test_scenario",
                    "description": "Full system test aggregation scenario",
                    "sources": [
                        {
                            "source_id": "sales_data",
                            "source_type": "file",
                            "path": "/data/raw/sales.csv",
                            "selected_columns": ["sale_date", "customer_id", "amount"]
                        }
                    ],
                    "aggregations": [
                        {
                            "type": "group_by",
                            "parameters": {
                                "group_by_columns": ["sale_date"],
                                "aggregation_functions": [
                                    {"column": "amount", "function": "sum"},
                                    {"column": "customer_id", "function": "count"}
                                ]
                            }
                        }
                    ],
                    "target_requirements": {
                        "expected_volume": "large",
                        "performance_priority": "speed"
                    }
                },
                "depends_on": ["validate_all_sources"]
            },
            
            # ЭТАП 4: Выполнение агрегации (Модуль 2)
            {
                "stage_name": "execute_aggregation",
                "type": "function_call",
                "function": "execute_scenario",
                "endpoint": "/api/v1/aggregation/execute/full_test_scenario",
                "method": "POST",
                "parameters": {
                    "scenario_id": "full_test_scenario"
                },
                "depends_on": ["create_aggregation_scenario"]
            },
            
            # ЭТАП 5: Анализ производительности (Модуль 3)
            {
                "stage_name": "analyze_performance",
                "type": "module_call",
                "module": 3,
                "endpoint": "/api/v1/performance/bulk-analyze",
                "method": "POST",
                "parameters": [
                    "/data/raw/sales.csv",
                    "/data/aggregated/full_test_scenario"
                ],
                "depends_on": ["execute_aggregation"]
            },
            
            # ЭТАП 6: Сбор метрик по design_id (Модуль 5)
            {
                "stage_name": "collect_by_design",
                "type": "function_call",
                "function": "collect_by_design",
                "endpoint": "/api/v1/metrics/collect-by-design/test_design",
                "method": "POST",
                "parameters": {
                    "design_id": "test_design"
                },
                "depends_on": ["analyze_performance"]
            },
            
            # ЭТАП 7: Мониторинг результатов (Модуль 5)
            {
                "stage_name": "monitor_warehouse",
                "type": "function_call",
                "function": "monitor_specific_source",
                "endpoint": "/api/v1/metrics/collect",
                "method": "POST",
                "parameters": {
                    "db_type": "clickhouse",
                    "host": "clickhouse",
                    "port": 9000,
                    "db_name": "analytics",
                    "user": "default",
                    "password": ""
                },
                "depends_on": ["collect_by_design"]
            },
            
            # ЭТАП 8: Финальная валидация (Модуль 1)
            {
                "stage_name": "final_validation",
                "type": "function_call",
                "function": "validate_file_direct",
                "endpoint": "/api/v1/data-quality/validate-file",
                "method": "POST",
                "parameters": {
                    "file_path": "/data/warehouses/analytics/sales_table",
                    "validation_options": {
                        "check_completeness": True,
                        "verify_constraints": True
                    }
                },
                "depends_on": ["monitor_warehouse"]
            }
        ]
    }
    
    try:
        pipeline = orchestrator.create_master_pipeline(config)
        print(f"[SUCCESS] Создан полный тестовый DAG: {pipeline.master_dag_id}")
        print(f"[INFO] Файл: {pipeline.dag_file_path}")
        print(f"[INFO] Этапов: {pipeline.stages_count}")
        print(f"[INFO] Расписание: {config['schedule']}")
        print(f"[INFO] Описание: {config['description']}")
        
        # Показываем структуру DAG'а
        print(f"\n[INFO] СТРУКТУРА DAG'А:")
        for i, stage in enumerate(config['stages'], 1):
            stage_type = "МОДУЛЬ" if stage['type'] == 'module_call' else "ФУНКЦИЯ"
            module_info = f" (Модуль {stage.get('module', 'N/A')})" if stage['type'] == 'module_call' else ""
            print(f"  {i}. {stage['stage_name']}{module_info} - {stage_type}")
        
        return pipeline.master_dag_id
    except Exception as e:
        print(f"[ERROR] Ошибка создания полного тестового DAG: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("СОЗДАНИЕ ПОЛНОГО ТЕСТОВОГО DAG'А ДЛЯ ВСЕХ МОДУЛЕЙ")
    print("=" * 60)
    
    result = create_full_test_dag()
    
    if result:
        print(f"\nУСПЕХ! Создан DAG: {result}")
        print("\nЭТАПЫ ТЕСТИРОВАНИЯ:")
        print("1. Модуль 5: Автоопределение источников данных")
        print("2. Модуль 1: Валидация найденных источников")
        print("3. Модуль 2: Создание сценария агрегации")
        print("4. Модуль 2: Выполнение агрегации данных")
        print("5. Модуль 3: Анализ производительности")
        print("6. Модуль 5: Сбор метрик по design_id")
        print("7. Модуль 5: Мониторинг созданного хранилища")
        print("8. Модуль 1: Финальная валидация результатов")
        
        print(f"\nDAG готов к запуску в Airflow UI!")
        print("   Откройте http://localhost:8080 и найдите DAG с именем:")
        print(f"   {result}")
    else:
        print("\nОШИБКА при создании DAG'а")
