#!/usr/bin/env python3
"""
Тестирование генерации DAG'ов с валидацией
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags', 'orchestrator'))

from dag_generator import DAGGenerator, create_test_data_file

def test_dag_generation():
    """Тестирование генерации 4 DAG'ов"""
    
    print("ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ DAG'ОВ С ВАЛИДАЦИЕЙ")
    print("=" * 60)
    
    # 1. Создание тестового файла данных
    print("\n1. СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ:")
    test_file = create_test_data_file()
    
    # 2. Создание генератора
    print("\n2. ИНИЦИАЛИЗАЦИЯ ГЕНЕРАТОРА:")
    try:
        generator = DAGGenerator()
        print("Генератор создан успешно")
    except Exception as e:
        print(f"Ошибка создания генератора: {e}")
        return
    
    # 3. Создание конфигураций
    print("\n3. СОЗДАНИЕ КОНФИГУРАЦИЙ DAG'ОВ:")
    try:
        configs = generator.create_test_dag_configs()
        print(f"Создано {len(configs)} конфигураций")
        
        for i, config in enumerate(configs, 1):
            print(f"  {i}. {config['dag_id']} - Модуль {config['stages'][0]['module']}")
    except Exception as e:
        print(f"Ошибка создания конфигураций: {e}")
        return
    
    # 4. Валидация каждой конфигурации
    print("\n4. ВАЛИДАЦИЯ КОНФИГУРАЦИЙ:")
    from dag_validator import validate_dag_file
    
    validation_results = []
    for config in configs:
        result = validate_dag_file(config)
        validation_results.append(result)
        
        status = "Валидна" if result["is_valid"] else "Ошибки"
        print(f"  {config['dag_id']}: {status}")
        
        if not result["is_valid"]:
            print(f"    Ошибок: {result['error_count']}")
            for error in result["errors"]["errors"][:3]:  # Показываем первые 3 ошибки
                print(f"      - {error.message}")
    
    # 5. Генерация DAG'ов
    print("\n5. ГЕНЕРАЦИЯ DAG'ОВ:")
    try:
        results = generator.generate_test_dags()
        
        print(f"\nРЕЗУЛЬТАТЫ ГЕНЕРАЦИИ:")
        print(f"  Всего DAG'ов: {results['total_dags']}")
        print(f"  Успешно: {results['successful']}")
        print(f"  Ошибок: {results['failed']}")
        
        # Детали успешных DAG'ов
        if results['successful'] > 0:
            print(f"\nУСПЕШНО СОЗДАННЫЕ DAG'И:")
            for result in results['results']:
                if result['result']['success']:
                    config = result['config']
                    module = config['stages'][0]['module']
                    endpoint = config['stages'][0]['endpoint']
                    method = config['stages'][0]['method']
                    
                    print(f"  {result['result']['dag_filename']}")
                    print(f"     Модуль: {module}")
                    print(f"     Endpoint: {method} {endpoint}")
                    print(f"     Путь: {result['result']['dag_filepath']}")
        
        # Детали ошибок
        if results['failed'] > 0:
            print(f"\nОШИБКИ В DAG'АХ:")
            for result in results['results']:
                if not result['result']['success']:
                    print(f"  {result['config']['dag_id']}: {result['result'].get('message', 'Unknown error')}")
        
        return results
        
    except Exception as e:
        print(f"Ошибка генерации DAG'ов: {e}")
        return None

def analyze_integration():
    """Анализ интеграции валидатора в процесс генерации"""
    
    print("\n" + "=" * 60)
    print("АНАЛИЗ ИНТЕГРАЦИИ ВАЛИДАТОРА")
    print("=" * 60)
    
    integration_points = [
        {
            "component": "DAGGenerator.__init__()",
            "integration": "Создание экземпляра DAGValidator",
            "purpose": "Инициализация валидатора для проверки конфигураций"
        },
        {
            "component": "DAGGenerator.generate_dag()",
            "integration": "validate_dag_file(config) перед генерацией",
            "purpose": "Предотвращение создания невалидных DAG'ов"
        },
        {
            "component": "validate_dag_file()",
            "integration": "Проверка HTTP методов, структур данных, path parameters",
            "purpose": "Обнаружение 405/422 ошибок до создания DAG'а"
        },
        {
            "component": "ValidationError",
            "integration": "Детальные сообщения об ошибках с предложениями",
            "purpose": "Помощь в исправлении проблем"
        }
    ]
    
    for i, point in enumerate(integration_points, 1):
        print(f"\n{i}. {point['component']}:")
        print(f"   Интеграция: {point['integration']}")
        print(f"   Цель: {point['purpose']}")
    
    print(f"\nПРЕИМУЩЕСТВА ИНТЕГРАЦИИ:")
    advantages = [
        "Автоматическая валидация перед генерацией",
        "Предотвращение 405/422 ошибок",
        "Детальные сообщения об ошибках",
        "Предложения по исправлению",
        "Проверка соответствия Pydantic схемам",
        "Валидация HTTP методов для каждого модуля"
    ]
    
    for advantage in advantages:
        print(f"  {advantage}")

if __name__ == "__main__":
    # Тестирование генерации
    results = test_dag_generation()
    
    # Анализ интеграции
    analyze_integration()
    
    print(f"\nТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    
    if results and results['successful'] > 0:
        print(f"Успешно создано {results['successful']} DAG'ов с валидацией!")
    else:
        print("Не удалось создать DAG'и. Проверьте ошибки выше.")
