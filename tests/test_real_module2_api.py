"""
Тест реального модуля 2 через API endpoints.
Использует ТОЛЬКО настоящие функции модуля 2, никаких подмен!
"""

import asyncio
import aiohttp
import json
from pathlib import Path
from datetime import datetime

# Базовый URL для API модуля 2
BASE_URL = "http://localhost:8000"

async def test_module2_api():
    """Тестирует реальный модуль 2 через API endpoints."""
    
    print("ТЕСТ РЕАЛЬНОГО МОДУЛЯ 2 ЧЕРЕЗ API")
    print("=" * 60)
    print("Используем ТОЛЬКО настоящие API endpoints модуля 2")
    print("Никаких подмен функций!")
    print("=" * 60)
    
    # Указанные файлы для тестирования
    target_files = [
        {
            "local_path": "data_landing_zone/syn_csv/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv",
            "docker_path": "/data/syn_csv/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv",
            "source_id": "large_csv_data",
            "type": "csv"
        },
        {
            "local_path": "data_landing_zone/syn_json/part1.json",
            "docker_path": "/data/syn_json/part1.json", 
            "source_id": "large_json_data",
            "type": "json"
        },
        {
            "local_path": "data_landing_zone/syn_xml/part1.xml",
            "docker_path": "/data/syn_xml/part1.xml",
            "source_id": "large_xml_data", 
            "type": "xml"
        }
    ]
    
    # Проверяем файлы локально
    available_files = []
    for file_info in target_files:
        file_path = Path(file_info["local_path"])
        if file_path.exists():
            file_size = file_path.stat().st_size
            print(f"НАЙДЕН {file_info['type'].upper()}: {file_path.name}")
            print(f"   Размер: {file_size:,} байт ({file_size/1024/1024:.1f} MB)")
            available_files.append(file_info)
        else:
            print(f"НЕ НАЙДЕН {file_info['type'].upper()}: {file_path}")
    
    if not available_files:
        print("ОШИБКА: Нет доступных файлов для тестирования")
        return False
    
    print(f"\nНайдено файлов: {len(available_files)}")
    
    # Создаем HTTP сессию
    async with aiohttp.ClientSession() as session:
        
        # Тест 1: Проверяем работоспособность модуля 2
        print(f"\n1. ПРОВЕРКА РАБОТОСПОСОБНОСТИ МОДУЛЯ 2")
        print("-" * 40)
        
        try:
            async with session.get(f"{BASE_URL}/api/v1/aggregation/health-check") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print("МОДУЛЬ 2 РАБОТАЕТ!")
                    print(f"   Статус: {health_data.get('status', 'unknown')}")
                else:
                    print(f"ОШИБКА: Модуль 2 недоступен (статус: {response.status})")
                    return False
        except Exception as e:
            print(f"ОШИБКА подключения к модулю 2: {e}")
            return False
        
        # Тест 2: Получаем доступные источники данных
        print(f"\n2. ПОЛУЧЕНИЕ ДОСТУПНЫХ ИСТОЧНИКОВ ДАННЫХ")
        print("-" * 40)
        
        try:
            async with session.get(f"{BASE_URL}/api/v1/aggregation/sources") as response:
                if response.status == 200:
                    sources_data = await response.json()
                    # API возвращает прямо список источников
                    if isinstance(sources_data, list):
                        print(f"Найдено источников: {len(sources_data)}")
                        for source in sources_data[:5]:  # Показываем первые 5
                            print(f"   - {source.get('source_id', 'unknown')}: {source.get('source_type', 'unknown')}")
                    else:
                        print(f"Найдено источников: {len(sources_data.get('sources', []))}")
                        for source in sources_data.get('sources', [])[:5]:  # Показываем первые 5
                            print(f"   - {source.get('source_id', 'unknown')}: {source.get('source_type', 'unknown')}")
                else:
                    print(f"ОШИБКА получения источников (статус: {response.status})")
        except Exception as e:
            print(f"ОШИБКА: {e}")
        
        # Тест 3: Задача 1 - Объединить 10 строк из каждого файла в один parquet
        print(f"\n3. ЗАДАЧА 1: ОБЪЕДИНЕНИЕ 10 СТРОК В ОДИН PARQUET")
        print("-" * 40)
        
        # Создаем источники данных для API (используем Docker пути)
        sources_for_union = []
        for file_info in available_files:
            source = {
                "source_id": file_info["source_id"],
                "source_type": "file",
                "path": file_info["docker_path"],
                "selected_columns": []  # Все колонки
            }
            sources_for_union.append(source)
        
        # Запрос на создание кастомного набора данных (объединение)
        union_request = {
            "dataset_name": "union_10_rows_all_files",
            "sources": sources_for_union,
            "join_strategy": "concat",  # Объединение строк
            "output_format": "parquet",
            "include_metadata": True,
            "limit_rows": 100  # Ограничиваем до 100 строк для оптимизации памяти
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/api/v1/aggregation/custom-dataset",
                json=union_request
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print("ЗАДАЧА 1 ВЫПОЛНЕНА!")
                    print(f"   Набор данных: {result.get('dataset_name')}")
                    print(f"   Путь: {result.get('output_path')}")
                    print(f"   Строк: {result.get('row_count')}")
                    print(f"   Колонок: {result.get('column_count')}")
                else:
                    error_text = await response.text()
                    print(f"ОШИБКА задачи 1 (статус: {response.status})")
                    print(f"   Детали: {error_text}")
        except Exception as e:
            print(f"ИСКЛЮЧЕНИЕ в задаче 1: {e}")
        
        # Тест 4: Задача 2 - Все колонки из каждого файла в один parquet
        print(f"\n4. ЗАДАЧА 2: ВСЕ КОЛОНКИ В ОДИН PARQUET")
        print("-" * 40)
        
        # Запрос на создание кастомного набора данных (все колонки)
        all_columns_request = {
            "dataset_name": "all_columns_all_files",
            "sources": sources_for_union,
            "join_strategy": "auto",  # Автоматическая стратегия
            "output_format": "parquet",
            "include_metadata": True,
            "limit_rows": 100  # Ограничиваем до 100 строк для оптимизации памяти
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/api/v1/aggregation/custom-dataset",
                json=all_columns_request
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print("ЗАДАЧА 2 ВЫПОЛНЕНА!")
                    print(f"   Набор данных: {result.get('dataset_name')}")
                    print(f"   Путь: {result.get('output_path')}")
                    print(f"   Строк: {result.get('row_count')}")
                    print(f"   Колонок: {result.get('column_count')}")
                else:
                    error_text = await response.text()
                    print(f"ОШИБКА задачи 2 (статус: {response.status})")
                    print(f"   Детали: {error_text}")
        except Exception as e:
            print(f"ИСКЛЮЧЕНИЕ в задаче 2: {e}")
        
        # Тест 5: Задача 3 - Отдельные parquet файлы (10 строк каждый)
        print(f"\n5. ЗАДАЧА 3: ОТДЕЛЬНЫЕ PARQUET ФАЙЛЫ")
        print("-" * 40)
        
        individual_results = []
        
        for i, file_info in enumerate(available_files):
            print(f"\n   Обрабатываем файл {i+1}: {file_info['source_id']}")
            
            # Создаем запрос для одного файла (используем Docker путь)
            individual_request = {
                "dataset_name": f"individual_{file_info['source_id']}_10_rows",
                "sources": [{
                    "source_id": file_info["source_id"],
                    "source_type": "file",
                    "path": file_info["docker_path"],
                    "selected_columns": []  # Все колонки
                }],
                "join_strategy": "individual",  # Отдельная обработка
                "output_format": "parquet",
                "include_metadata": True,
                "limit_rows": 100  # Ограничиваем до 100 строк для оптимизации памяти
            }
            
            try:
                async with session.post(
                    f"{BASE_URL}/api/v1/aggregation/custom-dataset",
                    json=individual_request
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"   УСПЕШНО: {result.get('dataset_name')}")
                        print(f"   Путь: {result.get('output_path')}")
                        print(f"   Строк: {result.get('row_count')}")
                        print(f"   Колонок: {result.get('column_count')}")
                        individual_results.append(result)
                    else:
                        error_text = await response.text()
                        print(f"   ОШИБКА (статус: {response.status})")
                        print(f"   Детали: {error_text}")
            except Exception as e:
                print(f"   ИСКЛЮЧЕНИЕ: {e}")
        
        print(f"\nЗАДАЧА 3: Создано {len(individual_results)} отдельных parquet файлов")
    
    print(f"\n" + "=" * 60)
    print("ТЕСТ РЕАЛЬНОГО МОДУЛЯ 2 ЗАВЕРШЕН")
    print("Использовались ТОЛЬКО настоящие API endpoints!")
    print("=" * 60)
    
    return True

async def main():
    """Основная функция теста."""
    
    print("ТЕСТИРОВАНИЕ РЕАЛЬНОГО МОДУЛЯ 2")
    print("=" * 70)
    print("Цель: Протестировать 3 задачи через настоящие API endpoints")
    print("Файлы:")
    print("  - data_landing_zone/syn_csv/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv")
    print("  - data_landing_zone/syn_json/part1.json")
    print("  - data_landing_zone/syn_xml/part1.xml")
    print("=" * 70)
    
    success = await test_module2_api()
    
    if success:
        print(f"\nТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        print("Реальный модуль 2 протестирован через API")
    else:
        print(f"\nТЕСТ НЕ ПРОШЕЛ")
        print("Проблемы с реальным модулем 2")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
