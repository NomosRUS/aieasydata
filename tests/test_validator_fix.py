#!/usr/bin/env python3
"""
Тест исправленного валидатора на неправильной структуре
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags', 'orchestrator'))

from dag_validator import validate_dag_file

def test_validator_on_wrong_structure():
    """Тест валидатора на неправильной структуре, которая вызывала 422 ошибку"""
    
    print("ТЕСТ ВАЛИДАТОРА НА НЕПРАВИЛЬНОЙ СТРУКТУРЕ")
    print("=" * 50)
    
    # Неправильная структура (та, что вызывала 422 ошибку)
    wrong_config = {
        "dag_id": "test_wrong_structure",
        "stages": [
            {
                "stage_name": "create_scenario_wrong",
                "stage_type": {"value": "module_call"},
                "module": 2,
                "endpoint": "/api/v1/aggregation/create-scenario",
                "method": "POST",
                "parameters": {
                    "name": "test_aggregation",
                    "description": "Test with wrong structure",
                    "sources": [
                        {
                            "source_id": "test_data",
                            "source_type": "file",
                            "path": "/data/test.csv",
                            "selected_columns": ["id", "value", "category"]
                        }
                    ],
                    "aggregations": [
                        {
                            "type": "group_by",
                            "parameters": {
                                "group_by_columns": ["category"],  # ❌ НЕПРАВИЛЬНО
                                "aggregation_functions": [        # ❌ НЕПРАВИЛЬНО
                                    {"column": "value", "function": "sum"},
                                    {"column": "id", "function": "count"}
                                ]
                            }
                        }
                    ],
                    "target_requirements": {
                        "expected_volume": "small",
                        "performance_priority": "balanced"
                    }
                }
            }
        ]
    }
    
    # Правильная структура
    correct_config = {
        "dag_id": "test_correct_structure",
        "stages": [
            {
                "stage_name": "create_scenario_correct",
                "stage_type": {"value": "module_call"},
                "module": 2,
                "endpoint": "/api/v1/aggregation/create-scenario",
                "method": "POST",
                "parameters": {
                    "name": "test_aggregation",
                    "description": "Test with correct structure",
                    "sources": [
                        {
                            "source_id": "test_data",
                            "source_type": "file",
                            "path": "/data/test.csv",
                            "selected_columns": ["id", "value", "category"]
                        }
                    ],
                    "aggregations": [
                        {
                            "type": "group_by",
                            "parameters": {
                                "columns": ["category"],           # ✅ ПРАВИЛЬНО
                                "aggregates": {                   # ✅ ПРАВИЛЬНО
                                    "total_value": "SUM(value)",
                                    "count_records": "COUNT(id)"
                                }
                            }
                        }
                    ],
                    "target_requirements": {
                        "expected_volume": "small",
                        "performance_priority": "balanced"
                    }
                }
            }
        ]
    }
    
    print("\n1. ТЕСТ НЕПРАВИЛЬНОЙ СТРУКТУРЫ:")
    print("-" * 30)
    
    wrong_result = validate_dag_file(wrong_config)
    print(f"Валидна: {wrong_result['is_valid']}")
    print(f"Ошибок: {wrong_result['error_count']}")
    
    if not wrong_result['is_valid']:
        print("Найденные ошибки:")
        for error in wrong_result['errors']['errors']:
            print(f"  - {error.message}")
            print(f"    Предложение: {error.suggestion}")
    
    print("\n2. ТЕСТ ПРАВИЛЬНОЙ СТРУКТУРЫ:")
    print("-" * 30)
    
    correct_result = validate_dag_file(correct_config)
    print(f"Валидна: {correct_result['is_valid']}")
    print(f"Ошибок: {correct_result['error_count']}")
    
    if not correct_result['is_valid']:
        print("Найденные ошибки:")
        for error in correct_result['errors']['errors']:
            print(f"  - {error.message}")
    
    print("\n3. ИТОГИ:")
    print("-" * 30)
    
    if not wrong_result['is_valid'] and correct_result['is_valid']:
        print("УСПЕХ: Валидатор правильно обнаруживает ошибки!")
        print("- Неправильная структура отклонена")
        print("- Правильная структура принята")
        return True
    elif wrong_result['is_valid']:
        print("ПРОБЛЕМА: Валидатор пропускает неправильную структуру!")
        return False
    elif not correct_result['is_valid']:
        print("ПРОБЛЕМА: Валидатор отклоняет правильную структуру!")
        return False
    else:
        print("НЕОПРЕДЕЛЕННЫЙ РЕЗУЛЬТАТ")
        return False

if __name__ == "__main__":
    success = test_validator_on_wrong_structure()
    
    if success:
        print("\nВАЛИДАТОР ИСПРАВЛЕН И РАБОТАЕТ КОРРЕКТНО!")
        print("Теперь 422 ошибки будут предотвращаться на этапе валидации.")
    else:
        print("\nВАЛИДАТОР ТРЕБУЕТ ДОПОЛНИТЕЛЬНЫХ ИСПРАВЛЕНИЙ!")
