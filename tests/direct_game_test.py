"""
Прямой игровой тест модуля 2 без API.
Тестирует логику создания кастомных наборов данных.
"""

import sys
import os
import asyncio
import pandas as pd
import json
import xml.etree.ElementTree as ET
from pathlib import Path

# Добавляем путь к модулю
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Импортируем компоненты модуля 2
from app.data_aggregator.custom_dataset_builder import CustomDatasetBuilder
from app.data_aggregator.schemas import DataSource, CustomDatasetRequest

def analyze_test_files():
    """Анализирует тестовые файлы."""
    
    print("АНАЛИЗ ТЕСТОВЫХ ФАЙЛОВ")
    print("=" * 40)
    
    # CSV файл
    csv_file = Path("test_sales.csv")
    if csv_file.exists():
        df_csv = pd.read_csv(csv_file)
        csv_columns = list(df_csv.columns)
        csv_selected = csv_columns[-2:]  # Последние 2 колонки
        print(f"\nCSV файл ({csv_file.name}):")
        print(f"  Всего колонок: {len(csv_columns)}")
        print(f"  Все колонки: {csv_columns}")
        print(f"  Выбранные: {csv_selected}")
        print(f"  Первые строки:\n{df_csv[csv_selected].head()}")
    
    # JSON файл
    json_file = Path("test_customers.json")
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            data_json = json.load(f)
        json_columns = list(data_json[0].keys()) if data_json else []
        json_selected = json_columns[-2:]  # Последние 2 колонки
        print(f"\nJSON файл ({json_file.name}):")
        print(f"  Всего колонок: {len(json_columns)}")
        print(f"  Все колонки: {json_columns}")
        print(f"  Выбранные: {json_selected}")
        print(f"  Первые записи:")
        for i, item in enumerate(data_json[:3]):
            selected_data = {col: item.get(col) for col in json_selected}
            print(f"    {i+1}: {selected_data}")
    
    # XML файл
    xml_file = Path("test_products.xml")
    if xml_file.exists():
        tree = ET.parse(xml_file)
        root = tree.getroot()
        first_product = root[0] if len(root) > 0 else None
        xml_columns = [child.tag for child in first_product] if first_product is not None else []
        xml_selected = xml_columns[-2:]  # Последние 2 колонки
        print(f"\nXML файл ({xml_file.name}):")
        print(f"  Всего колонок: {len(xml_columns)}")
        print(f"  Все колонки: {xml_columns}")
        print(f"  Выбранные: {xml_selected}")
        print(f"  Первые записи:")
        for i, product in enumerate(root[:3]):
            selected_data = {}
            for col in xml_selected:
                element = product.find(col)
                selected_data[col] = element.text if element is not None else None
            print(f"    {i+1}: {selected_data}")
    
    return {
        "csv": {"file": str(csv_file), "columns": csv_selected} if csv_file.exists() else None,
        "json": {"file": str(json_file), "columns": json_selected} if json_file.exists() else None,
        "xml": {"file": str(xml_file), "columns": xml_selected} if xml_file.exists() else None
    }

async def test_custom_dataset_creation(file_info):
    """Тестирует создание кастомного набора данных."""
    
    print("\nСОЗДАНИЕ КАСТОМНОГО НАБОРА ДАННЫХ")
    print("=" * 40)
    
    # Создаем источники данных
    sources = []
    
    for source_type, info in file_info.items():
        if info:
            source = DataSource(
                source_id=f"{source_type}_source",
                source_type="file",
                path=info["file"],
                selected_columns=info["columns"]
            )
            sources.append(source)
            print(f"Добавлен источник: {source_type} - {info['columns']}")
    
    if not sources:
        print("Нет доступных источников для тестирования")
        return False
    
    # Создаем запрос на кастомный набор данных
    request = CustomDatasetRequest(
        dataset_name="game_test_mixed_data",
        sources=sources,
        join_strategy="concat",  # Простая конкатенация
        output_format="parquet",
        include_metadata=True
    )
    
    print(f"\nЗапрос на создание набора данных:")
    print(f"  Имя: {request.dataset_name}")
    print(f"  Источников: {len(request.sources)}")
    print(f"  Стратегия: {request.join_strategy}")
    print(f"  Формат: {request.output_format}")
    
    # Создаем экземпляр построителя
    builder = CustomDatasetBuilder()
    
    try:
        # Выполняем создание кастомного набора данных
        print("\nВыполняем создание кастомного набора данных...")
        result = await builder.create_custom_dataset(request)
        
        if result.get("success"):
            print("\nУСПЕШНО! Кастомный набор данных создан!")
            print(f"  Путь: {result.get('output_path', 'N/A')}")
            print(f"  Строк: {result.get('row_count', 'N/A')}")
            print(f"  Колонок: {result.get('column_count', 'N/A')}")
            print(f"  Размер: {result.get('data_size_bytes', 'N/A')} байт")
            
            # Показываем метаданные
            if result.get('metadata'):
                metadata = result['metadata']
                print(f"\nМетаданные:")
                print(f"  Источников: {len(metadata.get('sources', []))}")
                print(f"  Создан: {metadata.get('dataset_info', {}).get('created_at', 'N/A')}")
                
                # Показываем схему результата
                if 'result_schema' in metadata:
                    schema = metadata['result_schema']
                    print(f"  Схема результата:")
                    for col_info in schema.get('columns', []):
                        print(f"    - {col_info['name']}: {col_info['type']} (null: {col_info['null_count']})")
            
            return True
        else:
            print(f"\nОШИБКА: {result.get('error', 'Неизвестная ошибка')}")
            if result.get('details'):
                print(f"Детали: {result['details']}")
            return False
            
    except Exception as e:
        print(f"\nИСКЛЮЧЕНИЕ: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Основная функция теста."""
    
    print("ПРЯМОЙ ИГРОВОЙ ТЕСТ МОДУЛЯ 2")
    print("=" * 50)
    
    # 1. Анализируем тестовые файлы
    file_info = analyze_test_files()
    
    # 2. Тестируем создание кастомного набора данных
    success = await test_custom_dataset_creation(file_info)
    
    if success:
        print("\nИГРОВОЙ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        
        # Проверяем созданный файл
        output_path = Path("data_landing_zone/aggregated/game_test_mixed_data/game_test_mixed_data.parquet")
        if output_path.exists():
            print(f"\nПУТЬ К СОЗДАННОЙ БАЗЕ: {output_path.absolute()}")
            
            # Читаем и показываем содержимое
            try:
                df_result = pd.read_parquet(output_path)
                print(f"\nСОДЕРЖИМОЕ СОЗДАННОЙ БАЗЫ:")
                print(f"  Размер: {df_result.shape}")
                print(f"  Колонки: {list(df_result.columns)}")
                print(f"\nПервые строки:")
                print(df_result.head())
            except Exception as e:
                print(f"Ошибка чтения результата: {str(e)}")
        else:
            print(f"Файл результата не найден: {output_path}")
        
        return True
    else:
        print("\nИГРОВОЙ ТЕСТ НЕ ПРОШЕЛ")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
