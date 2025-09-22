import os
from typing import List, Dict, Any
import polars as pl
from lxml import etree
import multiprocessing

def _element_to_dict(element) -> dict:
    """Рекурсивно конвертирует XML-элемент и его дочерние элементы в словарь."""
    # Если у элемента нет дочерних элементов, возвращаем его текст
    if not list(element):
        return element.text

    d = {}
    for child in element:
        child_dict = _element_to_dict(child)
        # Если тег уже есть в словаре, значит, это список элементов
        if child.tag in d:
            # Если это еще не список, делаем его списком
            if not isinstance(d[child.tag], list):
                d[child.tag] = [d[child.tag]]
            d[child.tag].append(child_dict)
        else:
            d[child.tag] = child_dict
    return d

def _count_xml_records_subprocess(file_path: str, record_tag: str) -> int:
    """Эта функция выполняется в отдельном процессе для подсчета записей в XML."""
    count = 0
    try:
        # Если record_tag не определен, парсер не будет работать, но это безопасно
        if not record_tag:
            return 0
        context = etree.iterparse(file_path, events=('end',), tag=record_tag)
        for _, elem in context:
            count += 1
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        return count
    except Exception:
        return 0

SUPPORTED_FORMATS = (".parquet", ".csv", ".json", ".jsonl", ".xlsx", ".tsv", ".xml")

def scan_data_landing_zone(path: str) -> List[str]:
    """
    Recursively scans the data landing zone and returns a list of supported files.
    """
    found_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.lower().endswith(SUPPORTED_FORMATS):
                found_files.append(os.path.join(root, file))
    return found_files

def classify_table(profile_data: Dict[str, Any]) -> str:
    """
    Classifies a table as 'fact', 'dimension', or 'mapping' based on heuristics.
    """
    if profile_data.get("error"):
        return "unknown"

    row_count = profile_data.get("total_row_count", 0)
    column_profiles = profile_data.get("columns", [])
    column_names = [c.get('column_name', '').lower() for c in column_profiles]
    column_count = len(column_names)

    # Heuristic for mapping tables
    is_mapping = False
    if 2 <= column_count <= 3 and row_count < 100000: # Usually not very large
        id_like_columns = [name for name in column_names if 'id' in name or 'key' in name or 'code' in name]
        if len(id_like_columns) >= 2:
            is_mapping = True

    if is_mapping:
        return "mapping"

    # Heuristic for fact tables
    # Typically large, multiple foreign keys (ending in _id, _key)
    if row_count >= 200000:
        id_like_columns = [name for name in column_names if 'id' in name or 'key' in name]
        if len(id_like_columns) >= 2: # Multiple FKs
            return "fact"

    # Default fallback to dimension
    return "dimension"



def _get_row_count(file_path: str, record_tag: str = None) -> int:
    """Получает количество строк в файле."""
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext == '.csv':
            df = pl.read_csv(file_path, n_rows=None, separator=';', truncate_ragged_lines=True)
            return df.height
        elif file_ext in ['.json', '.jsonl']:
            df = pl.read_json(file_path)
            return df.height
        elif file_ext == '.parquet':
            df = pl.read_parquet(file_path)
            return df.height
        elif file_ext == '.xlsx':
            df = pl.read_excel(file_path)
            return df.height
        elif file_ext == '.xml':
            # Запускаем тяжелый подсчет в отдельном процессе с таймаутом
            # Это предотвращает блокировку GIL и зависание heartbeat Airflow
            # Используем get_context, чтобы избежать проблем на Windows
            pool = multiprocessing.get_context("spawn").Pool(processes=1)
            try:
                # Таймаут в 120 секунд. Если файл слишком большой, мы не будем ждать вечно.
                result = pool.apply_async(_count_xml_records_subprocess, (file_path, record_tag)).get(timeout=120)
                pool.close()
                pool.join()
                return result
            except (multiprocessing.TimeoutError, Exception):
                pool.terminate()
                pool.join()
                return 0 # Возвращаем 0, если подсчет занял слишком много времени
        return 0
    except:
        return 0

def profile_source(source_path: str) -> Dict[str, Any]:
    """
    Профилирует источник данных (папку с файлами).
    Возвращает агрегированную информацию о всех файлах в источнике.
    """
    try:
        all_files = []
        for root, _, files in os.walk(source_path):
            for file in files:
                if file.endswith(SUPPORTED_FORMATS):
                    all_files.append(os.path.join(root, file))

        if not all_files:
            return {"source_path": source_path, "error": "No supported files found in directory."}

        # 1. Get schema and sample data from the first file
        first_file = all_files[0]
        file_ext = os.path.splitext(first_file)[1].lower()
        df: pl.DataFrame
        sample_data = []

        if file_ext == '.csv':
            df = pl.read_csv(first_file, n_rows=100, infer_schema_length=100, truncate_ragged_lines=True, separator=';')
        elif file_ext in ['.json', '.jsonl']:
            df = pl.read_json(first_file, infer_schema_length=100)
        elif file_ext == '.parquet':
            df = pl.read_parquet(first_file)
        elif file_ext == '.xlsx':
            df = pl.read_excel(first_file, read_options={"n_rows": 100})
        elif file_ext == '.xml':
            # XML schema extraction
            column_names = []
            record_tag = None # Определяем тег здесь
            context = etree.iterparse(first_file, events=('end',), tag='*')
            for _, elem in context:
                if elem.getparent() is not None and elem.getparent().getparent() is None:
                    record_tag = elem.tag # Запоминаем тег
                    column_names = [child.tag for child in elem]
                    break # We only need the schema from the first record
            
            if not column_names:
                 return {"source_path": source_path, "error": "Could not determine columns from XML structure."}

            # Memory-efficient sample data extraction for XML using the determined record_tag
            if record_tag:
                context = etree.iterparse(first_file, events=('end',), tag=record_tag)
                for i, (_, elem) in enumerate(context):
                    if i < 5:
                        # Convert each child element to a clean dictionary
                        sample_data.append({child.tag: _element_to_dict(child) for child in elem})
                        # Clear the element and its predecessors to save memory
                        elem.clear()
                        while elem.getprevious() is not None:
                            del elem.getparent()[0]
                    else:
                        break # Stop after 5 samples
            
            # Create a dummy dataframe with the correct schema, defaulting to String type
            dummy_data = {col: [""] for col in column_names} # Use empty string to infer String type
            df = pl.DataFrame(dummy_data, schema={col: pl.String for col in column_names})
        else:
            return {"source_path": source_path, "error": f"Unsupported file type for schema inference: {file_ext}"}

        if not sample_data: # If sample_data wasn't populated by the XML logic
            sample_data = df.head(5).to_dicts()

        columns = [{'column_name': c, 'column_type': str(t)} for c, t in df.schema.items()]

        # 2. Get total row count by summing up all files
        # Для XML, JSON, JSONL считаем строки только в первом файле и экстраполируем для скорости
        if file_ext in ['.xml', '.json', '.jsonl']:
            record_tag = locals().get('record_tag') # Безопасно получаем record_tag, если он есть (для XML)
            first_file_rows = _get_row_count(first_file, record_tag=record_tag)
            total_rows = first_file_rows * len(all_files) # Экстраполяция на все файлы
        else:
            total_rows = sum(_get_row_count(f) for f in all_files)

        # 3. Get file count
        file_count = len(all_files)

        return {
            "source_path": source_path,
            "total_row_count": total_rows,
            "file_count": file_count,
            "columns": columns,
            "sample_data": sample_data,
            "error": None
        }
    except Exception as e:
        return {"source_path": source_path, "error": str(e)}
