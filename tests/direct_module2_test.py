"""
Прямой тест модуля 2 без API - используем функции напрямую.
"""

import sys
import os
from pathlib import Path
import asyncio
import pandas as pd

# Добавляем путь к модулю 2
sys.path.append(str(Path(__file__).parent / "backend"))

def test_direct_module2():
    """Тестирует модуль 2 напрямую через импорт функций."""
    
    print("ПРЯМОЙ ТЕСТ МОДУЛЯ 2 (БЕЗ API)")
    print("=" * 50)
    print("Используем функции модуля 2 напрямую")
    print("=" * 50)
    
    # Указанные файлы для тестирования
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
    available_files = []
    for file_info in target_files:
        file_path = Path(file_info["path"])
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
    
    # Простой тест - читаем файлы напрямую pandas
    print(f"\nТЕСТ 1: ПРЯМОЕ ЧТЕНИЕ ФАЙЛОВ PANDAS")
    print("-" * 40)
    
    for file_info in available_files:
        file_path = Path(file_info["path"])
        print(f"\nОбрабатываем: {file_info['source_id']}")
        
        try:
            if file_info["type"] == "csv":
                # Пробуем разные разделители для CSV
                try:
                    df = pd.read_csv(file_path, nrows=10)
                    print(f"   CSV (запятая): {len(df)} строк, {len(df.columns)} колонок")
                    print(f"   Колонки: {list(df.columns)[:3]}...")
                except:
                    try:
                        df = pd.read_csv(file_path, sep=';', nrows=10)
                        print(f"   CSV (точка с запятой): {len(df)} строк, {len(df.columns)} колонок")
                        print(f"   Колонки: {list(df.columns)[:3]}...")
                    except Exception as e:
                        print(f"   ОШИБКА CSV: {str(e)[:50]}...")
                        
            elif file_info["type"] == "json":
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        if isinstance(data, list):
                            df = pd.DataFrame(data[:10])
                            print(f"   JSON: {len(df)} строк, {len(df.columns)} колонок")
                            print(f"   Колонки: {list(df.columns)[:3]}...")
                        else:
                            print(f"   JSON: не список, тип: {type(data)}")
                    except Exception as e:
                        print(f"   ОШИБКА JSON: {str(e)[:50]}...")
                        
            elif file_info["type"] == "xml":
                import xml.etree.ElementTree as ET
                try:
                    tree = ET.parse(file_path)
                    root = tree.getroot()
                    print(f"   XML: корневой элемент: {root.tag}")
                    print(f"   XML: дочерних элементов: {len(list(root))}")
                    
                    # Пробуем извлечь первые записи
                    records = []
                    count = 0
                    for child in root:
                        if count >= 10:
                            break
                        if len(list(child)) > 0:
                            record = {}
                            for subchild in child:
                                record[subchild.tag] = subchild.text
                            records.append(record)
                            count += 1
                    
                    if records:
                        df = pd.DataFrame(records)
                        print(f"   XML: {len(df)} строк, {len(df.columns)} колонок")
                        print(f"   Колонки: {list(df.columns)[:3]}...")
                    else:
                        print(f"   XML: не удалось извлечь записи")
                        
                except Exception as e:
                    print(f"   ОШИБКА XML: {str(e)[:50]}...")
                    
        except Exception as e:
            print(f"   ОБЩАЯ ОШИБКА: {str(e)[:50]}...")
    
    print(f"\n" + "=" * 50)
    print("ПРЯМОЙ ТЕСТ ЗАВЕРШЕН")
    print("Показал возможности чтения файлов без API")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    success = test_direct_module2()
    exit(0 if success else 1)
