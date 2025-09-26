"""
Детальная проверка XML данных в Parquet файле.
"""

import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path

def check_parquet_data():
    """Проверяет данные в Parquet файле."""
    
    parquet_path = "data_landing_zone/aggregated/game_test_mixed_data/game_test_mixed_data.parquet"
    
    if not Path(parquet_path).exists():
        print(f"Файл не найден: {parquet_path}")
        return
    
    df = pd.read_parquet(parquet_path)
    
    print("=" * 60)
    print("ДЕТАЛЬНАЯ ПРОВЕРКА XML ДАННЫХ В PARQUET")
    print("=" * 60)
    
    print(f"Общий размер файла: {df.shape}")
    print(f"Колонки: {list(df.columns)}")
    
    # Проверяем weight колонку
    print(f"\nWEIGHT КОЛОНКА:")
    print(f"  Всего значений: {len(df['weight'])}")
    print(f"  Не пустых: {df['weight'].notna().sum()}")
    print(f"  Пустых (None/NaN): {df['weight'].isna().sum()}")
    
    # Проверяем warranty колонку
    print(f"\nWARRANTY КОЛОНКА:")
    print(f"  Всего значений: {len(df['warranty'])}")
    print(f"  Не пустых: {df['warranty'].notna().sum()}")
    print(f"  Пустых (None/NaN): {df['warranty'].isna().sum()}")
    
    # Показываем непустые значения
    weight_data = df[df['weight'].notna()]
    if len(weight_data) > 0:
        print(f"\nНЕПУСТЫЕ ЗНАЧЕНИЯ WEIGHT (найдено {len(weight_data)}):")
        print(weight_data[['weight', 'warranty']].to_string())
    else:
        print(f"\nВНИМАНИЕ: НЕ НАЙДЕНО НИ ОДНОГО НЕПУСТОГО ЗНАЧЕНИЯ WEIGHT!")
    
    warranty_data = df[df['warranty'].notna()]
    if len(warranty_data) > 0:
        print(f"\nНЕПУСТЫЕ ЗНАЧЕНИЯ WARRANTY (найдено {len(warranty_data)}):")
        print(warranty_data[['weight', 'warranty']].to_string())
    else:
        print(f"\nВНИМАНИЕ: НЕ НАЙДЕНО НИ ОДНОГО НЕПУСТОГО ЗНАЧЕНИЯ WARRANTY!")
    
    # Проверяем строки где должны быть XML данные (20-29)
    print(f"\nСТРОКИ 20-29 (где должны быть XML данные):")
    xml_section = df.iloc[20:30]
    print(xml_section[['weight', 'warranty']].to_string())
    
    return df

def check_original_xml():
    """Проверяет исходный XML файл."""
    
    xml_path = "test_products.xml"
    
    if not Path(xml_path).exists():
        print(f"XML файл не найден: {xml_path}")
        return
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ИСХОДНОГО XML ФАЙЛА")
    print("=" * 60)
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    print(f"Найдено продуктов в XML: {len(root)}")
    
    # Проверяем первые 10 продуктов
    print(f"\nПервые 10 продуктов из XML:")
    for i, product in enumerate(root[:10]):
        weight_elem = product.find('weight')
        warranty_elem = product.find('warranty')
        
        weight_val = weight_elem.text if weight_elem is not None else "НЕ НАЙДЕН"
        warranty_val = warranty_elem.text if warranty_elem is not None else "НЕ НАЙДЕН"
        
        print(f"  Продукт {i+1}: weight={weight_val}, warranty={warranty_val}")

def compare_data():
    """Сравнивает данные из XML и Parquet."""
    
    print("\n" + "=" * 60)
    print("СРАВНЕНИЕ XML И PARQUET ДАННЫХ")
    print("=" * 60)
    
    # Читаем XML
    xml_path = "test_products.xml"
    if Path(xml_path).exists():
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        xml_data = []
        for product in root[:10]:  # Первые 10 продуктов
            weight_elem = product.find('weight')
            warranty_elem = product.find('warranty')
            
            xml_data.append({
                'weight': weight_elem.text if weight_elem is not None else None,
                'warranty': warranty_elem.text if warranty_elem is not None else None
            })
        
        print("XML данные (первые 10):")
        for i, data in enumerate(xml_data):
            print(f"  {i}: weight={data['weight']}, warranty={data['warranty']}")
    
    # Читаем Parquet
    parquet_path = "data_landing_zone/aggregated/game_test_mixed_data/game_test_mixed_data.parquet"
    if Path(parquet_path).exists():
        df = pd.read_parquet(parquet_path)
        
        # Строки 20-29 должны содержать XML данные
        xml_section = df.iloc[20:30]
        
        print(f"\nParquet данные (строки 20-29):")
        for i, (idx, row) in enumerate(xml_section.iterrows()):
            print(f"  {i}: weight={row['weight']}, warranty={row['warranty']}")

def main():
    """Основная функция проверки."""
    
    print("ПРОВЕРКА ЗАПИСИ XML ДАННЫХ В PARQUET")
    print("=" * 70)
    
    # 1. Проверяем Parquet файл
    df = check_parquet_data()
    
    # 2. Проверяем исходный XML
    check_original_xml()
    
    # 3. Сравниваем данные
    compare_data()
    
    print("\n" + "=" * 70)
    print("ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 70)

if __name__ == "__main__":
    main()
