"""
Исправленный третий игровой тест модуля 2.
Использует РЕАЛЬНЫЕ функции модуля 2 для трансформации файлов.
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к модулю 2
sys.path.append(str(Path(__file__).parent / "backend"))

try:
    from app.data_aggregator.custom_dataset_builder import CustomDatasetBuilder
    from app.data_aggregator.data_source_collector import DataSourceCollector
    from app.data_aggregator.schemas import (
        DataSource, CustomDatasetRequest, SourceType
    )
    REAL_MODULE_2 = True
    print("УСПЕШНО: Используем РЕАЛЬНЫЙ модуль 2")
except ImportError as e:
    print(f"ОШИБКА: Не удалось импортировать реальный модуль 2: {e}")
    REAL_MODULE_2 = False

async def test_real_module_2():
    """Тестирует реальный модуль 2 с указанными файлами."""
    
    print("ТЕСТ РЕАЛЬНОГО МОДУЛЯ 2 - ТРАНСФОРМАЦИЯ ФАЙЛОВ")
    print("=" * 60)
    
    if not REAL_MODULE_2:
        print("ОШИБКА: Реальный модуль 2 недоступен")
        return False
    
    # Указанные файлы для трансформации
    target_files = [
        {
            "path": "data_landing_zone/syn_csv/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv",
            "source_id": "large_csv_data",
            "type": "csv"
        },
        {
            "path": "data_landing_zone/syn_json/part1.json", 
            "source_id": "large_json_data",
            "type": "json"
        },
        {
            "path": "data_landing_zone/syn_xml/part1.xml",
            "source_id": "large_xml_data", 
            "type": "xml"
        }
    ]
    
    # Проверяем файлы
    available_sources = []
    for file_info in target_files:
        file_path = Path(file_info["path"])
        if file_path.exists():
            file_size = file_path.stat().st_size
            print(f"НАЙДЕН {file_info['type'].upper()}: {file_path.name}")
            print(f"   Размер: {file_size:,} байт ({file_size/1024/1024:.1f} MB)")
            
            # Создаем DataSource для реального модуля 2
            source = DataSource(
                source_id=file_info["source_id"],
                source_type=SourceType.FILE,
                path=str(file_path),  # Правильное поле для пути к файлу
                selected_columns=[]  # Все колонки
            )
            available_sources.append(source)
        else:
            print(f"НЕ НАЙДЕН {file_info['type'].upper()}: {file_path}")
    
    if not available_sources:
        print("ОШИБКА: Нет доступных файлов для тестирования")
        return False
    
    print(f"\nНайдено файлов для обработки: {len(available_sources)}")
    
    # Создаем экземпляры реального модуля 2
    try:
        data_collector = DataSourceCollector()
        dataset_builder = CustomDatasetBuilder()
        
        print("УСПЕШНО: Экземпляры модуля 2 созданы")
    except Exception as e:
        print(f"ОШИБКА создания экземпляров модуля 2: {e}")
        return False
    
    # Тестируем каждый файл отдельно
    results = []
    
    for i, source in enumerate(available_sources):
        print(f"\nОбрабатываем файл {i+1}: {source.source_id}")
        
        try:
            # Создаем запрос на кастомный набор данных (первые 10 строк)
            request = CustomDatasetRequest(
                dataset_name=f"real_module2_test_{source.source_id}",
                sources=[source],
                join_strategy="auto",
                output_format="parquet",
                include_metadata=True
            )
            
            print(f"   Запрос создан: {request.dataset_name}")
            print(f"   Формат вывода: parquet")
            
            # Выполняем создание набора данных через реальный модуль 2
            result = await dataset_builder.create_custom_dataset(request)
            
            if result.get("success"):
                print(f"   УСПЕШНО: {result.get('dataset_name')}")
                print(f"   Путь: {result.get('output_path')}")
                print(f"   Строк: {result.get('row_count')}")
                print(f"   Колонок: {result.get('column_count')}")
                
                results.append({
                    "source_id": source.source_id,
                    "success": True,
                    "result": result
                })
            else:
                print(f"   ОШИБКА: {result.get('error')}")
                results.append({
                    "source_id": source.source_id,
                    "success": False,
                    "error": result.get('error')
                })
                
        except Exception as e:
            print(f"   ИСКЛЮЧЕНИЕ: {str(e)}")
            results.append({
                "source_id": source.source_id,
                "success": False,
                "error": str(e)
            })
    
    # Подводим итоги
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"\nИТОГИ ТЕСТИРОВАНИЯ РЕАЛЬНОГО МОДУЛЯ 2:")
    print(f"   Успешно: {len(successful)}")
    print(f"   Ошибок: {len(failed)}")
    
    if successful:
        print(f"\nУСПЕШНО ОБРАБОТАННЫЕ ФАЙЛЫ:")
        for result in successful:
            r = result["result"]
            print(f"   {result['source_id']}")
            print(f"      Путь: {r.get('output_path')}")
            print(f"      Строк: {r.get('row_count')}, Колонок: {r.get('column_count')}")
    
    if failed:
        print(f"\nОШИБКИ:")
        for result in failed:
            print(f"   {result['source_id']}: {result['error']}")
    
    return len(successful) > 0

async def main():
    """Основная функция исправленного теста."""
    
    print("ИСПРАВЛЕННЫЙ ТРЕТИЙ ИГРОВОЙ ТЕСТ МОДУЛЯ 2")
    print("=" * 70)
    print("Цель: Использовать РЕАЛЬНЫЕ функции модуля 2")
    print("Задача: Трансформировать файлы (первые 10 строк)")
    print("=" * 70)
    
    success = await test_real_module_2()
    
    if success:
        print(f"\nИСПРАВЛЕННЫЙ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        print("Теперь используются РЕАЛЬНЫЕ функции модуля 2")
    else:
        print(f"\nТЕСТ НЕ ПРОШЕЛ")
        print("Проблемы с реальным модулем 2 или файлами")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
