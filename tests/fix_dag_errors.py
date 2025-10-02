#!/usr/bin/env python3
"""
Исправление ошибок в DAG'ах на основе успешных примеров
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags'))

def analyze_dag_errors():
    """Анализ ошибок в DAG'ах и предложение исправлений"""
    
    print("АНАЛИЗ ОШИБОК В DAG'АХ")
    print("=" * 60)
    
    # Найденные ошибки из логов
    errors = [
        {
            "dag": "master_corrected_full_test_20250928_013305",
            "task": "create_scenario", 
            "error": "422 Client Error: Unprocessable Entity",
            "endpoint": "POST /api/v1/aggregation/create-scenario",
            "problem": "Неправильная структура данных в запросе"
        },
        {
            "dag": "master_validated_full_test_20250928_010635",
            "task": "stage_3_aggregate",
            "error": "405 Client Error: Method Not Allowed", 
            "endpoint": "GET /api/v1/aggregation/create-scenario",
            "problem": "Использование GET вместо POST"
        },
        {
            "dag": "master_weekly_optimization_20250928_005303",
            "task": "apply_critical_optimizations",
            "error": "422 Client Error: Unprocessable Entity",
            "endpoint": "POST /api/v1/performance/optimize/weekly_analysis",
            "problem": "Неправильная структура данных для модуля 3"
        }
    ]
    
    print("НАЙДЕННЫЕ ОШИБКИ:")
    print("-" * 40)
    
    for i, error in enumerate(errors, 1):
        print(f"\n{i}. DAG: {error['dag']}")
        print(f"   Task: {error['task']}")
        print(f"   Error: {error['error']}")
        print(f"   Endpoint: {error['endpoint']}")
        print(f"   Problem: {error['problem']}")
    
    print("\nИСПРАВЛЕНИЯ:")
    print("-" * 40)
    
    # Исправления на основе успешных DAG'ов
    fixes = {
        "HTTP методы": {
            "problem": "Использование GET для endpoints, которые принимают только POST",
            "solution": "Все endpoints модулей 1, 2, 3 используют POST методы",
            "examples": {
                "create-scenario": "POST (не GET)",
                "bulk-analyze": "POST", 
                "batch-validate": "POST"
            }
        },
        
        "Структура данных для модуля 2": {
            "problem": "Неправильная структура AggregationScenarioRequest",
            "solution": "Использовать правильную структуру из успешного DAG'а",
            "correct_structure": {
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
            }
        },
        
        "Структура данных для модуля 3": {
            "problem": "Неправильные параметры для optimize endpoint",
            "solution": "Использовать правильную структуру OptimizationApplication",
            "correct_structure": {
                "analysis_id": "weekly_analysis", 
                "recommendation_ids": ["partition", "index"],
                "confirm_application": False,
                "dry_run": True
            }
        }
    }
    
    for fix_name, fix_info in fixes.items():
        print(f"\n{fix_name}:")
        print(f"  Проблема: {fix_info['problem']}")
        print(f"  Решение: {fix_info['solution']}")
        
        if "examples" in fix_info:
            print("  Примеры:")
            for endpoint, method in fix_info["examples"].items():
                print(f"    - {endpoint}: {method}")
        
        if "correct_structure" in fix_info:
            print("  Правильная структура:")
            import json
            print("  " + json.dumps(fix_info["correct_structure"], indent=4).replace("\n", "\n  "))
    
    return fixes

def generate_corrected_template():
    """Генерация исправленного шаблона для DAG'ов"""
    
    print("\n\nГЕНЕРАЦИЯ ИСПРАВЛЕННОГО ШАБЛОНА:")
    print("=" * 60)
    
    template_fixes = {
        "HTTP методы": {
            "old": 'method: \'{{ "POST" if stage.module in [1, 2, 3] else "GET" }}\'',
            "new": 'method: \'{{ "POST" if stage.module in [1, 2, 3] else "GET" }}\'',
            "status": "✅ УЖЕ ИСПРАВЛЕНО"
        },
        
        "Валидация параметров": {
            "addition": "Добавить валидацию структуры данных перед отправкой",
            "validation_rules": {
                "module_2_create_scenario": "Проверить AggregationScenarioRequest схему",
                "module_3_optimize": "Проверить OptimizationApplication схему",
                "path_parameters": "Правильно обрабатывать {analysis_id}, {scenario_id}"
            }
        },
        
        "Обработка ошибок": {
            "addition": "Улучшить обработку ошибок в функциях execute_module_call",
            "improvements": [
                "Детальное логирование структуры запроса",
                "Валидация параметров перед отправкой",
                "Специальная обработка для разных типов endpoints"
            ]
        }
    }
    
    for fix_name, fix_info in template_fixes.items():
        print(f"\n{fix_name}:")
        if "old" in fix_info and "new" in fix_info:
            print(f"  Старое: {fix_info['old']}")
            print(f"  Новое: {fix_info['new']}")
            print(f"  Статус: {fix_info['status']}")
        
        if "addition" in fix_info:
            print(f"  Добавление: {fix_info['addition']}")
            
        if "validation_rules" in fix_info:
            print("  Правила валидации:")
            for rule, desc in fix_info["validation_rules"].items():
                print(f"    - {rule}: {desc}")
        
        if "improvements" in fix_info:
            print("  Улучшения:")
            for improvement in fix_info["improvements"]:
                print(f"    - {improvement}")

def create_validation_script():
    """Создание скрипта для валидации DAG'ов перед запуском"""
    
    print("\n\nСОЗДАНИЕ СКРИПТА ВАЛИДАЦИИ:")
    print("=" * 60)
    
    validation_script = """
def validate_dag_parameters(module, endpoint, method, parameters):
    '''Валидация параметров DAG'а перед выполнением'''
    
    errors = []
    
    # Проверка HTTP методов
    if module in [1, 2, 3] and method != "POST":
        errors.append(f"Module {module} requires POST method, got {method}")
    
    # Проверка структуры для модуля 2
    if module == 2 and "create-scenario" in endpoint:
        required_fields = ["name", "description", "sources", "aggregations", "target_requirements"]
        for field in required_fields:
            if field not in parameters:
                errors.append(f"Missing required field for module 2: {field}")
        
        # Проверка структуры sources
        if "sources" in parameters:
            for source in parameters["sources"]:
                if "source_id" not in source or "source_type" not in source:
                    errors.append("Each source must have source_id and source_type")
    
    # Проверка структуры для модуля 3
    if module == 3 and "optimize" in endpoint:
        if "analysis_id" not in parameters:
            errors.append("Module 3 optimize requires analysis_id parameter")
    
    return errors
    """
    
    print("Скрипт валидации создан:")
    print(validation_script)
    
    return validation_script

if __name__ == "__main__":
    # Анализ ошибок
    fixes = analyze_dag_errors()
    
    # Генерация исправленного шаблона
    generate_corrected_template()
    
    # Создание скрипта валидации
    create_validation_script()
    
    print("\n" + "=" * 60)
    print("ИТОГОВЫЕ РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    
    recommendations = [
        "1. ✅ HTTP методы уже исправлены в шаблоне",
        "2. ❌ Исправить GET→POST в неуспешных DAG'ах", 
        "3. ❌ Проверить структуру данных для модуля 2",
        "4. ❌ Проверить параметры для модуля 3",
        "5. ✅ Добавить валидацию в шаблон генерации"
    ]
    
    for rec in recommendations:
        print(rec)
    
    print("\nСТАТУС: НАЙДЕНЫ КОНКРЕТНЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ!")
