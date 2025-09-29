#!/usr/bin/env python3
"""
Создание исправленных DAG'ов с правильными параметрами API
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags'))

try:
    from orchestrator.master_orchestrator import MasterOrchestrator
except ImportError as e:
    print(f"Error: Could not import orchestrator modules: {e}")
    exit(1)

def create_corrected_dag():
    """Создание исправленного DAG'а с правильными параметрами"""
    print("СОЗДАНИЕ ИСПРАВЛЕННОГО DAG'А")
    print("=" * 50)
    
    orchestrator = MasterOrchestrator()
    
    config = {
        "pipeline_name": "corrected_full_test",
        "schedule": "0 5 * * *",  # Каждый день в 05:00
        "description": "Исправленный полный тест с правильными параметрами API",
        "stages": [
            # ЭТАП 1: Автоопределение источников (Модуль 5) - РАБОТАЕТ
            {
                "stage_name": "auto_detect_sources",
                "type": "function_call",
                "function": "auto_detect_source",
                "endpoint": "/api/v1/metrics/auto-detect",
                "method": "GET",
                "parameters": {"source": "/data/raw"},
                "depends_on": []
            },
            
            # ЭТАП 2: Валидация данных (Модуль 1) - РАБОТАЕТ
            {
                "stage_name": "validate_sources",
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
                        }
                    ],
                    "validation_options": {
                        "check_duplicates": True,
                        "detect_anomalies": True,
                        "assess_quality": True
                    }
                },
                "depends_on": ["auto_detect_sources"]
            },
            
            # ЭТАП 3: Создание сценария агрегации (Модуль 2) - ИСПРАВЛЕНО
            {
                "stage_name": "create_scenario",
                "type": "module_call",
                "module": 2,
                "endpoint": "/api/v1/aggregation/create-scenario",
                "method": "POST",  # ИСПРАВЛЕНО: было GET
                "parameters": {
                    "name": "corrected_test_scenario",
                    "description": "Corrected test aggregation scenario",
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
                "depends_on": ["validate_sources"]
            },
            
            # ЭТАП 4: Выполнение сценария (Модуль 2) - ИСПРАВЛЕНО
            {
                "stage_name": "execute_scenario",
                "type": "function_call",
                "function": "execute_scenario",
                "endpoint": "/api/v1/aggregation/execute/{scenario_id}",
                "method": "POST",
                "parameters": {
                    "scenario_id": "corrected_test_scenario"  # Будет подставлен в URL
                },
                "depends_on": ["create_scenario"]
            },
            
            # ЭТАП 5: Анализ производительности (Модуль 3) - РАБОТАЕТ
            {
                "stage_name": "analyze_performance",
                "type": "module_call",
                "module": 3,
                "endpoint": "/api/v1/performance/bulk-analyze",
                "method": "POST",
                "parameters": ["/data/raw/sales.csv"],  # Массив напрямую
                "depends_on": ["execute_scenario"]
            },
            
            # ЭТАП 6: Применение оптимизаций (Модуль 3) - ИСПРАВЛЕНО
            {
                "stage_name": "apply_optimizations",
                "type": "function_call",
                "function": "apply_optimizations",
                "endpoint": "/api/v1/performance/optimize/{analysis_id}",
                "method": "POST",
                "parameters": {
                    "analysis_id": "corrected_analysis",  # Будет подставлен в URL
                    "recommendation_ids": ["partition", "index"],  # ИСПРАВЛЕНО: добавлены обязательные поля
                    "confirm_application": False,  # ИСПРАВЛЕНО: добавлено обязательное поле
                    "dry_run": True  # ИСПРАВЛЕНО: добавлено обязательное поле
                },
                "depends_on": ["analyze_performance"]
            },
            
            # ЭТАП 7: Мониторинг результатов (Модуль 5) - РАБОТАЕТ
            {
                "stage_name": "monitor_results",
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
                "depends_on": ["apply_optimizations"]
            }
        ]
    }
    
    try:
        pipeline = orchestrator.create_master_pipeline(config)
        print(f"УСПЕХ! Создан исправленный DAG: {pipeline.master_dag_id}")
        print(f"Файл: {pipeline.dag_file_path}")
        print(f"Этапов: {pipeline.stages_count}")
        print(f"Расписание: {config['schedule']}")
        
        print(f"\nИСПРАВЛЕНИЯ В DAG'Е:")
        print("1. Модуль 2 create-scenario: GET -> POST")
        print("2. Функция apply_optimizations: добавлены обязательные поля")
        print("3. Path parameters: правильная обработка {analysis_id} и {scenario_id}")
        print("4. Параметры API: соответствуют схемам Pydantic")
        
        return pipeline.master_dag_id
    except Exception as e:
        print(f"ОШИБКА создания исправленного DAG: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("СОЗДАНИЕ ИСПРАВЛЕННОГО DAG'А С ПРАВИЛЬНЫМИ ПАРАМЕТРАМИ API")
    print("=" * 70)
    
    result = create_corrected_dag()
    
    if result:
        print(f"\nИСПРАВЛЕННЫЙ DAG СОЗДАН: {result}")
        print("\nОСНОВНЫЕ ИСПРАВЛЕНИЯ:")
        print("- 405 Method Not Allowed: исправлены HTTP методы")
        print("- 422 Unprocessable Entity: исправлены параметры API")
        print("- Path parameters: правильная подстановка в URL")
        print("- Pydantic схемы: соответствие обязательным полям")
        print(f"\nDAG готов к тестированию в Airflow UI!")
    else:
        print("\nОШИБКА: Не удалось создать исправленный DAG")
