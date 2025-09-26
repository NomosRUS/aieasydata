"""
Игровой имитационный тест модуля 2.
Создает кастомную базу данных из файлов CSV, JSON, XML.
"""

import asyncio
import pandas as pd
import json
import xml.etree.ElementTree as ET
import requests
import time
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Базовый URL API
BASE_URL = "http://localhost:8000"

def analyze_csv_structure(file_path):
    """Анализирует структуру CSV файла."""
    try:
        # Читаем первые 10 строк
        df = pd.read_csv(file_path, nrows=10)
        columns = list(df.columns)
        
        # Выбираем последние 2 колонки
        selected_columns = columns[-2:] if len(columns) >= 2 else columns
        
        logger.info(f"CSV файл {file_path.name}:")
        logger.info(f"  Всего колонок: {len(columns)}")
        logger.info(f"  Выбранные колонки: {selected_columns}")
        logger.info(f"  Первые строки:\n{df[selected_columns].head()}")
        
        return {
            "file_path": str(file_path),
            "total_columns": len(columns),
            "all_columns": columns,
            "selected_columns": selected_columns,
            "sample_data": df[selected_columns].to_dict('records')[:5]
        }
    except Exception as e:
        logger.error(f"Ошибка анализа CSV {file_path}: {str(e)}")
        return None

def analyze_json_structure(file_path):
    """Анализирует структуру JSON файла."""
    try:
        # Читаем JSON файл
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Если это список объектов
        if isinstance(data, list) and len(data) > 0:
            sample_obj = data[0]
            columns = list(sample_obj.keys())
        elif isinstance(data, dict):
            columns = list(data.keys())
            data = [data]  # Преобразуем в список для единообразия
        else:
            logger.error(f"Неподдерживаемый формат JSON в {file_path}")
            return None
        
        # Выбираем последние 2 колонки
        selected_columns = columns[-2:] if len(columns) >= 2 else columns
        
        # Берем первые 10 записей
        sample_data = []
        for i, item in enumerate(data[:10]):
            if isinstance(item, dict):
                sample_data.append({col: item.get(col) for col in selected_columns})
            if i >= 4:  # Ограничиваем для вывода
                break
        
        logger.info(f"JSON файл {file_path.name}:")
        logger.info(f"  Всего колонок: {len(columns)}")
        logger.info(f"  Выбранные колонки: {selected_columns}")
        logger.info(f"  Первые записи: {sample_data}")
        
        return {
            "file_path": str(file_path),
            "total_columns": len(columns),
            "all_columns": columns,
            "selected_columns": selected_columns,
            "sample_data": sample_data
        }
    except Exception as e:
        logger.error(f"Ошибка анализа JSON {file_path}: {str(e)}")
        return None

def analyze_xml_structure(file_path):
    """Анализирует структуру XML файла."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Ищем первый элемент записи
        record_element = None
        for child in root:
            if len(list(child)) > 0:  # Если у элемента есть дочерние элементы
                record_element = child
                break
        
        if record_element is None:
            # Если не нашли, берем первый элемент
            record_element = root[0] if len(root) > 0 else root
        
        # Получаем колонки из первого элемента
        columns = []
        if record_element is not None:
            for child in record_element:
                columns.append(child.tag)
        
        # Выбираем последние 2 колонки
        selected_columns = columns[-2:] if len(columns) >= 2 else columns
        
        # Собираем данные из первых 10 записей
        sample_data = []
        count = 0
        for record in root:
            if count >= 10:
                break
            if len(list(record)) > 0:  # Если это запись с дочерними элементами
                record_data = {}
                for col in selected_columns:
                    element = record.find(col)
                    record_data[col] = element.text if element is not None else None
                sample_data.append(record_data)
                count += 1
                if len(sample_data) >= 5:  # Ограничиваем для вывода
                    break
        
        logger.info(f"XML файл {file_path.name}:")
        logger.info(f"  Всего колонок: {len(columns)}")
        logger.info(f"  Выбранные колонки: {selected_columns}")
        logger.info(f"  Первые записи: {sample_data}")
        
        return {
            "file_path": str(file_path),
            "total_columns": len(columns),
            "all_columns": columns,
            "selected_columns": selected_columns,
            "sample_data": sample_data
        }
    except Exception as e:
        logger.error(f"Ошибка анализа XML {file_path}: {str(e)}")
        return None

def test_api_health():
    """Проверяет доступность API."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/aggregation/health-check", timeout=5)
        if response.status_code == 200:
            logger.info("API модуля 2 доступен")
            return True
        else:
            logger.error(f"API недоступен: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Ошибка подключения к API: {str(e)}")
        return False

def create_custom_dataset_via_api(sources_info):
    """Создает кастомный набор данных через API модуля 2."""
    
    # Формируем запрос для создания кастомного набора данных
    dataset_request = {
        "dataset_name": "game_test_mixed_data",
        "sources": [],
        "join_strategy": "concat",  # Простая конкатенация
        "output_format": "parquet",
        "include_metadata": True
    }
    
    # Добавляем источники
    for i, source_info in enumerate(sources_info):
        if source_info:
            source = {
                "source_id": f"source_{i+1}",
                "source_type": "file",
                "path": source_info["file_path"],
                "selected_columns": source_info["selected_columns"]
            }
            dataset_request["sources"].append(source)
    
    logger.info("Отправляем запрос на создание кастомного набора данных...")
    logger.info(f"Запрос: {json.dumps(dataset_request, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/aggregation/custom-dataset",
            json=dataset_request,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("Кастомный набор данных создан успешно!")
            logger.info(f"Результат: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
        else:
            logger.error(f"Ошибка создания набора данных: {response.status_code}")
            logger.error(f"Ответ: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка запроса: {str(e)}")
        return None

def main():
    """Основная функция игрового теста."""
    
    print("ИГРОВОЙ ИМИТАЦИОННЫЙ ТЕСТ МОДУЛЯ 2")
    print("=" * 50)
    
    # 1. Проверяем доступность API
    print("\n1. Проверка доступности API...")
    if not test_api_health():
        print("API недоступен. Убедитесь, что сервер запущен на http://localhost:8000")
        return False
    
    # 2. Анализируем файлы
    print("\n2. Анализ структуры файлов...")
    
    # Пути к файлам
    base_path = Path("data_landing_zone")
    csv_file = base_path / "syn_csv" / "part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv"
    json_file = base_path / "syn_json" / "part1.json"
    xml_file = base_path / "syn_xml" / "part1.xml"
    
    sources_info = []
    
    # Анализируем CSV
    if csv_file.exists():
        csv_info = analyze_csv_structure(csv_file)
        sources_info.append(csv_info)
    else:
        logger.warning(f"CSV файл не найден: {csv_file}")
        sources_info.append(None)
    
    # Анализируем JSON
    if json_file.exists():
        json_info = analyze_json_structure(json_file)
        sources_info.append(json_info)
    else:
        logger.warning(f"JSON файл не найден: {json_file}")
        sources_info.append(None)
    
    # Анализируем XML
    if xml_file.exists():
        xml_info = analyze_xml_structure(xml_file)
        sources_info.append(xml_info)
    else:
        logger.warning(f"XML файл не найден: {xml_file}")
        sources_info.append(None)
    
    # Проверяем, что хотя бы один файл найден
    valid_sources = [s for s in sources_info if s is not None]
    if not valid_sources:
        logger.error("Не найдено ни одного валидного файла для анализа")
        return False
    
    print(f"\nПроанализировано {len(valid_sources)} файлов из 3")
    
    # 3. Создаем кастомный набор данных
    print("\n3. Создание кастомного набора данных...")
    
    result = create_custom_dataset_via_api(valid_sources)
    
    if result and result.get("success"):
        print("\nИГРОВОЙ ТЕСТ УСПЕШНО ЗАВЕРШЕН!")
        print(f"Путь к созданной базе: {result.get('output_path', 'N/A')}")
        print(f"Строк в результате: {result.get('row_count', 'N/A')}")
        print(f"Колонок в результате: {result.get('column_count', 'N/A')}")
        print(f"Размер данных: {result.get('data_size_bytes', 'N/A')} байт")
        
        # Показываем метаданные если есть
        if result.get('metadata'):
            print(f"\nМетаданные:")
            metadata = result['metadata']
            print(f"  - Источников: {len(metadata.get('sources', []))}")
            print(f"  - Формат: {metadata.get('dataset_info', {}).get('format', 'N/A')}")
            print(f"  - Создан: {metadata.get('dataset_info', {}).get('created_at', 'N/A')}")
        
        return True
    else:
        print("\nИГРОВОЙ ТЕСТ НЕ ПРОШЕЛ")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
