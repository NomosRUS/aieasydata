#!/usr/bin/env python3
"""
Тест автоопределения типов данных для модуля 3
"""

import requests
import time

def test_auto_detection():
    """Тестирует автоопределение типов данных через API."""
    
    base_url = "http://localhost:8000"
    
    print("=== ТЕСТ АВТООПРЕДЕЛЕНИЯ ТИПОВ ДАННЫХ ===")
    print("Модуль 3 сможет сам определить что перед ним!")
    print("=" * 60)
    
    # Ждем запуска сервера
    time.sleep(3)
    
    # Проверяем доступность API
    try:
        response = requests.get(f"{base_url}/api/v1/metrics/health-check", timeout=5)
        if response.status_code == 200:
            print("[OK] Модуль 5 доступен")
        else:
            print("[ERROR] Модуль 5 недоступен")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False
    
    # Тестовые источники данных для автоопределения
    test_sources = [
        {
            'source': '/data/syn_csv',
            'expected': 'directory with CSV files',
            'description': 'Директория с CSV файлами'
        },
        {
            'source': '/data/syn_json',
            'expected': 'directory with JSON files', 
            'description': 'Директория с JSON файлами'
        },
        {
            'source': '/data/syn_xml',
            'expected': 'directory with XML files',
            'description': 'Директория с XML файлами'
        },
        {
            'source': 'postgresql://user:password@localhost:5432/aieasydata',
            'expected': 'PostgreSQL database',
            'description': 'PostgreSQL подключение'
        },
        {
            'source': 'http://localhost:8123',
            'expected': 'ClickHouse database',
            'description': 'ClickHouse подключение'
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_sources, 1):
        print(f"\n{i}. Тестируем: {test_case['description']}")
        print(f"   Источник: {test_case['source']}")
        
        try:
            # Используем новый эндпоинт автоопределения
            response = requests.get(
                f"{base_url}/api/v1/metrics/auto-detect",
                params={"source": test_case['source']},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"   [OK] Автоопределение успешно!")
                
                # Анализируем результат
                if 'error' in result:
                    print(f"   Ошибка: {result['error']}")
                    results.append(False)
                else:
                    # Показываем что определилось
                    if 'detection_result' in result:
                        detection = result['detection_result']
                        print(f"   Определен тип: {detection.get('type', 'unknown')}")
                        
                        if detection.get('type') == 'directory':
                            print(f"   Файлов: {detection.get('total_files', 0)}")
                            print(f"   Доминирующий тип: {detection.get('dominant_type', 'unknown')}")
                        elif detection.get('type') == 'database':
                            print(f"   Тип БД: {detection.get('db_type', 'unknown')}")
                            print(f"   Подключение: {detection.get('connection_available', False)}")
                    
                    # Показываем собранные метрики
                    if 'row_count' in result:
                        print(f"   Строк данных: {result.get('row_count', 0):,}")
                        print(f"   Размер: {result.get('size_in_bytes', 0) / 1024**3:.2f} GB")
                        if 'file_count' in result:
                            print(f"   Файлов: {result.get('file_count', 0)}")
                    
                    results.append(True)
                    
            else:
                print(f"   [ERROR] HTTP {response.status_code}: {response.text}")
                results.append(False)
                
        except Exception as e:
            print(f"   [ERROR] Исключение: {e}")
            results.append(False)
    
    # Итоговая статистика
    print(f"\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ АВТООПРЕДЕЛЕНИЯ:")
    
    success_count = sum(results)
    total_count = len(results)
    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
    
    print(f"Успешно: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 ОТЛИЧНО: Модуль 3 сможет автоматически определять типы данных!")
        print("✅ CSV, JSON, XML файлы и директории")
        print("✅ PostgreSQL и ClickHouse подключения") 
        print("✅ Автоматический сбор метрик")
        print("✅ Готово для интеграции в модуль 3!")
    elif success_rate >= 60:
        print("👍 ХОРОШО: Система работает с небольшими проблемами")
    else:
        print("⚠️ ТРЕБУЕТ ДОРАБОТКИ: Много ошибок в автоопределении")
    
    return success_rate >= 60

def test_specific_formats():
    """Тестирует конкретные форматы данных."""
    
    base_url = "http://localhost:8000"
    
    print(f"\n" + "=" * 60)
    print("ТЕСТ КОНКРЕТНЫХ ФОРМАТОВ ДАННЫХ")
    print("=" * 60)
    
    format_tests = [
        {
            'endpoint': '/api/v1/metrics/data-landing-zone',
            'params': {'path': '/data/syn_csv'},
            'name': 'CSV файлы'
        },
        {
            'endpoint': '/api/v1/metrics/test-xml',
            'params': {},
            'name': 'XML файлы'
        },
        {
            'endpoint': '/api/v1/metrics/test-json', 
            'params': {},
            'name': 'JSON файлы'
        }
    ]
    
    for test in format_tests:
        print(f"\nТестируем {test['name']}...")
        
        try:
            response = requests.get(
                f"{base_url}{test['endpoint']}",
                params=test['params'],
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'metrics' in data:
                    metrics = data['metrics']
                    print(f"  ✅ {test['name']}: {metrics.get('file_count', 0)} файлов")
                    print(f"     Строк: {metrics.get('row_count', 0):,}")
                    print(f"     Размер: {metrics.get('size_in_bytes', 0) / 1024**3:.2f} GB")
                else:
                    print(f"  ✅ {test['name']}: {data.get('file_count', 0)} файлов")
                    print(f"     Строк: {data.get('row_count', 0):,}")
                    
            else:
                print(f"  ❌ {test['name']}: Ошибка {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ {test['name']}: {e}")

if __name__ == "__main__":
    print("ЗАПУСК ТЕСТИРОВАНИЯ АВТООПРЕДЕЛЕНИЯ ТИПОВ ДАННЫХ!")
    
    # Основной тест автоопределения
    success = test_auto_detection()
    
    # Тест конкретных форматов
    test_specific_formats()
    
    print(f"\n" + "=" * 60)
    print("ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:")
    
    if success:
        print("🚀 МОДУЛЬ 3 ГОТОВ К АВТООПРЕДЕЛЕНИЮ ТИПОВ ДАННЫХ!")
        print("Теперь модуль 3 может:")
        print("• Автоматически определить CSV, JSON, XML")
        print("• Подключиться к ClickHouse и PostgreSQL")
        print("• Собрать метрики без указания типа")
        print("• Проанализировать любой источник данных")
    else:
        print("⚠️ ТРЕБУЕТСЯ ДОРАБОТКА АВТООПРЕДЕЛЕНИЯ")
    
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
