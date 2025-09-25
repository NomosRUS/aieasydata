#!/usr/bin/env python3
"""
Тест системы автоопределения типов данных
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.data_type_detector import DataTypeDetector

def test_data_type_detection():
    """Тестирует автоопределение различных типов данных."""
    
    print("=== ТЕСТ СИСТЕМЫ АВТООПРЕДЕЛЕНИЯ ТИПОВ ДАННЫХ ===")
    
    detector = DataTypeDetector()
    
    # Тестовые источники данных
    test_cases = [
        {
            'source': 'data_landing_zone/syn_csv',
            'expected_type': 'directory',
            'description': 'Директория с CSV файлами'
        },
        {
            'source': 'data_landing_zone/syn_json',
            'expected_type': 'directory', 
            'description': 'Директория с JSON файлами'
        },
        {
            'source': 'data_landing_zone/syn_xml',
            'expected_type': 'directory',
            'description': 'Директория с XML файлами'
        },
        {
            'source': 'postgresql://user:password@localhost:5432/aieasydata',
            'expected_type': 'database',
            'description': 'PostgreSQL подключение'
        },
        {
            'source': 'http://localhost:8123',
            'expected_type': 'database',
            'description': 'ClickHouse подключение'
        },
        {
            'source': 'clickhouse://default@localhost:9000/analytics',
            'expected_type': 'database',
            'description': 'ClickHouse TCP подключение'
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Тестируем: {test_case['description']}")
        print(f"   Источник: {test_case['source']}")
        
        try:
            result = detector.detect_data_type(test_case['source'])
            
            print(f"   Определенный тип: {result['type']}")
            
            # Дополнительная информация в зависимости от типа
            if result['type'] == 'directory':
                print(f"   Файлов: {result.get('total_files', 0)}")
                print(f"   Доминирующий тип: {result.get('dominant_type', 'unknown')}")
                print(f"   Типы файлов: {result.get('file_types', {})}")
                if result.get('total_size'):
                    print(f"   Общий размер: {result['total_size'] / 1024**3:.2f} GB")
            
            elif result['type'] == 'file':
                print(f"   Тип файла: {result.get('file_type', 'unknown')}")
                print(f"   Размер: {result.get('file_size', 0) / 1024**2:.2f} MB")
                if 'columns' in result:
                    print(f"   Колонок: {len(result['columns'])}")
                    print(f"   Строк (оценка): {result.get('estimated_rows', 0):,}")
            
            elif result['type'] == 'database':
                print(f"   Тип БД: {result.get('db_type', 'unknown')}")
                print(f"   Подключение доступно: {result.get('connection_available', False)}")
                if result.get('tables'):
                    print(f"   Таблиц найдено: {len(result['tables'])}")
                    print(f"   Примеры таблиц: {result['tables'][:3]}")
                if 'connection_error' in result:
                    print(f"   Ошибка подключения: {result['connection_error']}")
            
            # Проверяем соответствие ожидаемому типу
            if result['type'] == test_case['expected_type']:
                print(f"   ✅ УСПЕХ: Тип определен корректно")
                results.append(True)
            else:
                print(f"   ❌ ОШИБКА: Ожидался {test_case['expected_type']}, получен {result['type']}")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ ИСКЛЮЧЕНИЕ: {e}")
            results.append(False)
    
    # Итоговая статистика
    print(f"\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ:")
    
    success_count = sum(results)
    total_count = len(results)
    success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
    
    print(f"Успешно: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 ОТЛИЧНО: Система автоопределения работает корректно!")
    elif success_rate >= 60:
        print("👍 ХОРОШО: Система работает с небольшими проблемами")
    else:
        print("⚠️ ТРЕБУЕТ ДОРАБОТКИ: Много ошибок в определении типов")
    
    return success_rate >= 80

def demo_smart_detection():
    """Демонстрирует интеллектуальные возможности определения."""
    
    print(f"\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ ИНТЕЛЛЕКТУАЛЬНОГО ОПРЕДЕЛЕНИЯ")
    print("=" * 60)
    
    detector = DataTypeDetector()
    
    # Примеры различных форматов строк подключения
    smart_examples = [
        "host=localhost port=5432 dbname=test user=admin",  # PostgreSQL формат
        "Server=localhost;Database=test;Uid=admin;",         # SQL Server стиль
        "localhost:8123",                                    # Простой хост:порт
        "tcp://localhost:9000/analytics",                   # TCP протокол
    ]
    
    print("\nТестируем интеллектуальное определение по паттернам:")
    
    for example in smart_examples:
        print(f"\nСтрока: '{example}'")
        result = detector.detect_data_type(example)
        print(f"Определено как: {result['type']}")
        if result['type'] == 'database':
            print(f"Тип БД: {result.get('db_type', 'unknown')}")

if __name__ == "__main__":
    # Основной тест
    success = test_data_type_detection()
    
    # Демонстрация интеллектуальных возможностей
    demo_smart_detection()
    
    print(f"\n" + "=" * 60)
    if success:
        print("✅ СИСТЕМА АВТООПРЕДЕЛЕНИЯ ГОТОВА ДЛЯ МОДУЛЯ 3!")
        print("Модуль 3 сможет автоматически определять:")
        print("• CSV, JSON, XML файлы и директории")
        print("• PostgreSQL и ClickHouse подключения")
        print("• Структуру данных и метаданные")
        print("• Оценки размеров и производительности")
    else:
        print("⚠️ ТРЕБУЕТСЯ ДОРАБОТКА СИСТЕМЫ АВТООПРЕДЕЛЕНИЯ")
    
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
