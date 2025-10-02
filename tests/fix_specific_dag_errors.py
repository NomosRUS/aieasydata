#!/usr/bin/env python3
"""
Конкретные исправления для найденных ошибок в DAG'ах
"""

import json

def fix_dag_errors():
    """Исправление конкретных ошибок в DAG'ах"""
    
    print("КОНКРЕТНЫЕ ИСПРАВЛЕНИЯ ДЛЯ DAG ОШИБОК")
    print("=" * 50)
    
    # Проблема 1: 405 Method Not Allowed
    print("\n1. ИСПРАВЛЕНИЕ 405 ОШИБКИ (Method Not Allowed):")
    print("-" * 30)
    print("Проблема: stage_3_aggregate использует GET вместо POST")
    print("Файл: master_validated_full_test_20250928_010635.py")
    print("Строка 155:")
    print("  НЕПРАВИЛЬНО: 'method': 'GET'")
    print("  ПРАВИЛЬНО:   'method': 'POST'")
    
    # Проблема 2: 422 Unprocessable Entity для модуля 2
    print("\n2. ИСПРАВЛЕНИЕ 422 ОШИБКИ ДЛЯ МОДУЛЯ 2:")
    print("-" * 30)
    print("Проблема: Неправильная структура AggregationScenarioRequest")
    
    # Неправильная структура (из неуспешного DAG'а)
    wrong_structure = {
        "aggregations": [{"parameters": {"type": "group_by"}, "type": "group_by"}],
        "description": "Validated test scenario", 
        "name": "validated_test_scenario",
        "sources": [{"path": "/data/raw/sales.csv", "selected_columns": [], "source_id": "test_data", "source_type": "file"}],
        "target_requirements": {"expected_volume": "medium", "performance_priority": "balanced"}
    }
    
    # Правильная структура (из успешного DAG'а)
    correct_structure = {
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
                    "aggregation_functions": [{"column": "amount", "function": "sum"}]
                }
            }
        ],
        "target_requirements": {
            "expected_volume": "medium",
            "performance_priority": "balanced"
        }
    }
    
    print("НЕПРАВИЛЬНАЯ структура:")
    print(json.dumps(wrong_structure, indent=2))
    print("\nПРАВИЛЬНАЯ структура:")
    print(json.dumps(correct_structure, indent=2))
    
    # Проблема 3: 422 Unprocessable Entity для модуля 3
    print("\n3. ИСПРАВЛЕНИЕ 422 ОШИБКИ ДЛЯ МОДУЛЯ 3:")
    print("-" * 30)
    print("Проблема: Неправильный analysis_id в URL")
    print("Endpoint: /api/v1/performance/optimize/weekly_analysis")
    print("Проблема: 'weekly_analysis' не существует как analysis_id")
    
    correct_module3_structure = {
        "analysis_id": "corrected_analysis",  # Должен существовать
        "recommendation_ids": ["partition", "index"],
        "confirm_application": False,
        "dry_run": True
    }
    
    print("ПРАВИЛЬНАЯ структура для модуля 3:")
    print(json.dumps(correct_module3_structure, indent=2))
    
    return {
        "method_fix": "GET -> POST для всех модулей 1,2,3",
        "module2_structure": correct_structure,
        "module3_structure": correct_module3_structure
    }

def create_validation_rules():
    """Создание правил валидации для предотвращения ошибок"""
    
    print("\n\nПРАВИЛА ВАЛИДАЦИИ ДЛЯ DAG ГЕНЕРАЦИИ:")
    print("=" * 50)
    
    validation_rules = {
        "http_methods": {
            "rule": "Модули 1, 2, 3 ВСЕГДА используют POST",
            "modules": {
                1: "POST - все endpoints валидации",
                2: "POST - все endpoints агрегации", 
                3: "POST - все endpoints оптимизации",
                5: "GET/POST - зависит от endpoint'а"
            }
        },
        
        "required_fields": {
            "module_2_create_scenario": [
                "name", "description", "sources", "aggregations", "target_requirements"
            ],
            "module_3_optimize": [
                "analysis_id", "recommendation_ids", "confirm_application", "dry_run"
            ]
        },
        
        "data_structure_validation": {
            "sources": "Каждый source должен иметь: source_id, source_type, path, selected_columns",
            "aggregations": "Каждая aggregation должна иметь: type, parameters",
            "parameters": "parameters должны соответствовать типу aggregation"
        }
    }
    
    for rule_name, rule_info in validation_rules.items():
        print(f"\n{rule_name.upper()}:")
        if isinstance(rule_info, dict):
            for key, value in rule_info.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        print(f"    {k}: {v}")
                elif isinstance(value, list):
                    print(f"  {key}: {', '.join(value)}")
                else:
                    print(f"  {key}: {value}")
        else:
            print(f"  {rule_info}")
    
    return validation_rules

def generate_fixed_examples():
    """Генерация исправленных примеров DAG'ов"""
    
    print("\n\nИСПРАВЛЕННЫЕ ПРИМЕРЫ:")
    print("=" * 50)
    
    # Исправленный пример для модуля 2
    fixed_module2_task = {
        "task_id": "create_scenario_fixed",
        "python_callable": "execute_module_call",
        "op_kwargs": {
            "module": 2,
            "endpoint": "/api/v1/aggregation/create-scenario",
            "method": "POST",  # Исправлено с GET на POST
            "parameters": {
                "name": "fixed_scenario",
                "description": "Fixed aggregation scenario",
                "sources": [
                    {
                        "source_id": "sales_data",
                        "source_type": "file",
                        "path": "/data/raw/sales.csv",
                        "selected_columns": ["sale_date", "customer_id", "amount"]  # Не пустой массив
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
            }
        }
    }
    
    # Исправленный пример для модуля 3
    fixed_module3_task = {
        "task_id": "apply_optimizations_fixed",
        "python_callable": "execute_function_call",
        "op_kwargs": {
            "function": "apply_optimizations",
            "endpoint": "/api/v1/performance/optimize/{analysis_id}",
            "method": "POST",
            "parameters": {
                "analysis_id": "existing_analysis",  # Должен существовать
                "recommendation_ids": ["partition", "index"],
                "confirm_application": False,
                "dry_run": True
            }
        }
    }
    
    print("ИСПРАВЛЕННЫЙ ПРИМЕР ДЛЯ МОДУЛЯ 2:")
    print(json.dumps(fixed_module2_task, indent=2))
    
    print("\nИСПРАВЛЕННЫЙ ПРИМЕР ДЛЯ МОДУЛЯ 3:")
    print(json.dumps(fixed_module3_task, indent=2))
    
    return {
        "module2_fixed": fixed_module2_task,
        "module3_fixed": fixed_module3_task
    }

if __name__ == "__main__":
    # Исправление ошибок
    fixes = fix_dag_errors()
    
    # Правила валидации
    rules = create_validation_rules()
    
    # Исправленные примеры
    examples = generate_fixed_examples()
    
    print("\n" + "=" * 50)
    print("ИТОГОВЫЕ ИСПРАВЛЕНИЯ:")
    print("=" * 50)
    
    final_fixes = [
        "1. Изменить GET на POST в неуспешных DAG'ах",
        "2. Исправить структуру данных для модуля 2",
        "3. Использовать существующий analysis_id для модуля 3", 
        "4. Добавить валидацию в генератор DAG'ов",
        "5. Проверить selected_columns не пустые"
    ]
    
    for fix in final_fixes:
        print(fix)
    
    print("\nСТАТУС: КОНКРЕТНЫЕ ИСПРАВЛЕНИЯ ОПРЕДЕЛЕНЫ!")
