"""
Базовый профилировщик данных для всех модулей системы.
Предоставляет общие функции профилирования без специализации.
Интегрирован с новой системой организации данных.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

# Импортируем новую систему путей
try:
    from ..config import DataPaths, file_manager
except ImportError:
    # Fallback для случаев, когда модуль config еще не готов
    DataPaths = None
    file_manager = None

SUPPORTED_FORMATS = (".parquet", ".csv", ".json", ".jsonl", ".xlsx", ".tsv", ".xml")

def scan_data_zone(path: str = None) -> List[str]:
    """
    Рекурсивно сканирует зону данных и возвращает список поддерживаемых файлов.
    БАЗОВАЯ ФУНКЦИЯ - используется всеми модулями.
    Теперь интегрирована с новой системой путей.
    """
    if path is None and DataPaths:
        # Используем новую систему путей
        path = str(DataPaths.BASE_DATA_DIR)
    elif path is None:
        # Fallback к старому пути
        path = "data_landing_zone"
    
    found_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.lower().endswith(SUPPORTED_FORMATS):
                found_files.append(os.path.join(root, file))
    return found_files

def get_basic_file_info(file_path: str) -> Dict[str, Any]:
    """
    Получает базовую информацию о файле: размер, тип, количество строк.
    БАЗОВАЯ ФУНКЦИЯ - без анализа качества или производительности.
    """
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        
        basic_info = {
            "file_path": file_path,
            "file_type": file_ext,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2)
        }
        
        # Базовый подсчет строк без детального анализа
        row_count = _get_basic_row_count(file_path, file_ext)
        basic_info["estimated_rows"] = row_count
        
        return basic_info
        
    except Exception as e:
        return {
            "file_path": file_path,
            "error": f"Failed to get basic info: {str(e)}"
        }

def get_basic_schema_info(file_path: str, sample_size: int = 100) -> Dict[str, Any]:
    """
    Получает базовую информацию о схеме данных: колонки, типы, примеры.
    БАЗОВАЯ ФУНКЦИЯ - без анализа качества или аномалий.
    """
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.csv':
            df = pl.read_csv(file_path, n_rows=sample_size, infer_schema_length=sample_size)
        elif file_ext in ['.json', '.jsonl']:
            df = pl.read_json(file_path, infer_schema_length=sample_size)
        elif file_ext == '.parquet':
            df = pl.read_parquet(file_path, n_rows=sample_size)
        elif file_ext == '.xlsx':
            df = pl.read_excel(file_path, sheet_id=0)
        else:
            return {"error": f"Unsupported format for schema analysis: {file_ext}"}
        
        # Базовая информация о схеме
        schema_info = {
            "columns": [],
            "total_columns": len(df.columns),
            "sample_rows": min(sample_size, df.height),
            "sample_data": df.head(5).to_dicts() if df.height > 0 else []
        }
        
        # Базовые типы колонок
        for col_name in df.columns:
            col_type = str(df[col_name].dtype)
            schema_info["columns"].append({
                "name": col_name,
                "type": col_type,
                "sample_values": df[col_name].head(3).to_list()
            })
        
        return schema_info
        
    except Exception as e:
        return {"error": f"Failed to analyze schema: {str(e)}"}

def _get_basic_row_count(file_path: str, file_ext: str) -> int:
    """Базовый подсчет строк без детального анализа."""
    try:
        if file_ext == '.csv':
            # Быстрый подсчет через wc или аналог
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f) - 1  # Минус заголовок
        elif file_ext in ['.json', '.jsonl']:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_ext == '.jsonl':
                    return sum(1 for _ in f)
                else:
                    # Для JSON пробуем загрузить и посчитать
                    data = json.load(f)
                    if isinstance(data, list):
                        return len(data)
                    return 1
        elif file_ext == '.parquet':
            df = pl.read_parquet(file_path)
            return df.height
        elif file_ext == '.xml':
            # Базовый подсчет XML без детального парсинга
            return _count_xml_elements_basic(file_path)
        return 0
    except:
        return 0

def _count_xml_elements_basic(file_path: str) -> int:
    """Базовый подсчет элементов XML."""
    try:
        # Пробуем найти повторяющиеся теги
        common_tags = ['item', 'record', 'row', 'entry', 'data', 'object']
        
        for tag in common_tags:
            try:
                count = 0
                context = etree.iterparse(file_path, events=('end',), tag=tag)
                for _, elem in context:
                    count += 1
                    elem.clear()
                    if count > 1000:  # Ограничение для базового подсчета
                        break
                if count > 0:
                    return count
            except:
                continue
        return 0
    except:
        return 0

def classify_dataset_basic(files_info: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Базовая классификация набора данных.
    БАЗОВАЯ ФУНКЦИЯ - без анализа качества или производительности.
    """
    if not files_info:
        return {"type": "empty", "files_count": 0}
    
    total_files = len(files_info)
    total_size = sum(info.get("file_size_bytes", 0) for info in files_info)
    total_rows = sum(info.get("estimated_rows", 0) for info in files_info)
    
    # Определяем доминирующий тип файлов
    file_types = {}
    for info in files_info:
        file_type = info.get("file_type", "unknown")
        file_types[file_type] = file_types.get(file_type, 0) + 1
    
    dominant_type = max(file_types, key=file_types.get) if file_types else "unknown"
    
    # Базовая классификация по размеру
    if total_size > 1024 * 1024 * 1024:  # > 1GB
        size_category = "large"
    elif total_size > 100 * 1024 * 1024:  # > 100MB
        size_category = "medium"
    else:
        size_category = "small"
    
    return {
        "type": "dataset",
        "dominant_file_type": dominant_type,
        "files_count": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "estimated_total_rows": total_rows,
        "size_category": size_category,
        "file_types_distribution": file_types
    }

def get_database_files(database_name: str, stage: str = None) -> List[str]:
    """
    Получить файлы для конкретной базы данных из новой системы организации.
    
    Args:
        database_name: Имя базы данных
        stage: Этап обработки (raw, validated, cleaned, aggregated, optimized)
    
    Returns:
        Список путей к файлам
    """
    if not DataPaths:
        return []
    
    files = []
    
    if stage is None:
        # Сканируем все этапы для данной БД
        stages = ["validated", "cleaned", "aggregated", "optimized"]
        for s in stages:
            try:
                stage_path = DataPaths.get_database_intermediate_path(database_name, s)
                if stage_path.exists():
                    files.extend(scan_data_zone(str(stage_path)))
            except:
                continue
    else:
        # Сканируем конкретный этап
        try:
            if stage == "raw":
                stage_path = DataPaths.RAW_DATA_DIR
            else:
                stage_path = DataPaths.get_database_intermediate_path(database_name, stage)
            
            if stage_path.exists():
                files.extend(scan_data_zone(str(stage_path)))
        except:
            pass
    
    return files

def process_file_with_size_control(file_path: str, database_name: str, 
                                 source_id: str, stage: str) -> List[str]:
    """
    Обработать файл с автоматическим контролем размера.
    Интеграция с file_manager для разделения больших файлов.
    
    Args:
        file_path: Путь к исходному файлу
        database_name: Имя базы данных
        source_id: Идентификатор источника
        stage: Этап обработки
    
    Returns:
        Список путей к обработанным файлам
    """
    if not file_manager:
        # Fallback - просто возвращаем исходный файл
        return [file_path]
    
    try:
        # Используем file_manager для обработки с контролем размера
        processed_files = file_manager.process_file(
            Path(file_path), database_name, source_id, stage
        )
        return [str(f) for f in processed_files]
    except Exception as e:
        print(f"Warning: Failed to process file with size control: {e}")
        return [file_path]

def get_available_databases() -> List[str]:
    """Получить список доступных баз данных в системе."""
    if not DataPaths:
        return []
    
    try:
        return DataPaths.get_database_list()
    except:
        return []
