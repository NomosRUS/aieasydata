#!/usr/bin/env python3
"""
Тест исправленной схемы БД с DAG'ом модуля 2
"""

import requests
import time

def test_fixed_schema():
    """Тестирование исправленной схемы БД"""
    
    print("ТЕСТИРОВАНИЕ ИСПРАВЛЕННОЙ СХЕМЫ БД")
    print("=" * 50)
    
    # Данные для тестирования (те же, что использует DAG)
    test_data = {
        "name": "test_small_aggregation",
        "description": "Test aggregation for small file", 
        "sources": [
            {
                "source_id": "test_small_data",
                "source_type": "file",
                "path": "/data/raw/test_small.csv",
                "selected_columns": ["id", "value", "category"]
            }
        ],
        "aggregations": [
            {
                "type": "group_by",
                "parameters": {
                    "columns": ["category"],  # Исправленная структура
                    "aggregates": {           # Исправленная структура
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
    
    print("1. Тестирование API endpoint модуля 2...")
    
    try:
        # Отправляем запрос к модулю 2
        response = requests.post(
            "http://localhost:8000/api/v1/aggregation/create-scenario",
            json=test_data,
            timeout=30
        )
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("УСПЕХ: Схема БД исправлена!")
            print(f"Создан scenario_id: {result.get('scenario_id', 'N/A')}")
            print(f"Имя сценария: {result.get('name', 'N/A')}")
            print(f"Статус: {result.get('status', 'N/A')}")
            return True
            
        elif response.status_code == 422:
            print("ОШИБКА 422: Проблема с валидацией данных")
            print("Валидатор DAG'а сработал правильно, но есть проблема в структуре")
            
        elif response.status_code == 500:
            print("ОШИБКА 500: Проблема на сервере")
            try:
                error_text = response.text
                if "scenario_name" in error_text:
                    print("Проблема все еще с колонкой scenario_name")
                else:
                    print("Другая проблема на сервере")
                print(f"Детали: {error_text[:200]}...")
            except:
                print("Не удалось получить детали ошибки")
                
        else:
            print(f"Неожиданный статус: {response.status_code}")
            print(f"Ответ: {response.text[:200]}...")
            
        return False
        
    except requests.exceptions.ConnectionError:
        print("ОШИБКА: Не удалось подключиться к API")
        print("Убедитесь, что контейнер aie_api запущен")
        return False
        
    except Exception as e:
        print(f"ОШИБКА: {e}")
        return False

def check_database_schema():
    """Проверка схемы БД"""
    
    print("\n2. Проверка схемы БД...")
    
    import subprocess
    
    try:
        # Проверяем структуру таблицы
        result = subprocess.run([
            'docker', 'exec', 'aie_pg', 'psql', '-U', 'airflow', '-d', 'aieasydata',
            '-c', '\\d aggregation_scenarios'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            output = result.stdout
            if "scenario_name" in output:
                print("✓ Колонка scenario_name найдена в БД")
                return True
            else:
                print("✗ Колонка scenario_name не найдена в БД")
                return False
        else:
            print(f"Ошибка проверки БД: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Ошибка проверки БД: {e}")
        return False

if __name__ == "__main__":
    # Проверяем схему БД
    db_ok = check_database_schema()
    
    # Тестируем API
    api_ok = test_fixed_schema()
    
    print(f"\nРЕЗУЛЬТАТЫ:")
    print(f"Схема БД: {'✓ OK' if db_ok else '✗ ERROR'}")
    print(f"API тест: {'✓ OK' if api_ok else '✗ ERROR'}")
    
    if db_ok and api_ok:
        print("\n🎉 ВСЕ ИСПРАВЛЕНО! DAG модуля 2 должен работать без ошибок!")
    elif db_ok and not api_ok:
        print("\n⚠️ Схема БД исправлена, но есть другие проблемы в API")
    else:
        print("\n❌ Требуются дополнительные исправления")
