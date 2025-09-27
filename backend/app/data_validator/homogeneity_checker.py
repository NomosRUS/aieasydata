"""
Проверка однородности файлов в папках.

Содержит алгоритмы для анализа схем файлов и автоматического
разделения неоднородных файлов по отдельным папкам.
"""

import os
import shutil
import pandas as pd
import json
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
import uuid
import requests

from .schemas import (
    HomogeneityResult, SchemaInfo, FileSchemaAnalysis,
    DataFormat
)

logger = logging.getLogger(__name__)


class HomogeneityChecker:
    """Класс для проверки однородности файлов в папках."""
    
    def __init__(self, module5_url: str = "http://localhost:8000/api/v1/metrics"):
        self.logger = logging.getLogger(__name__)
        self.module5_url = module5_url
        
        # Поддерживаемые расширения файлов
        self.supported_extensions = {'.csv', '.json', '.xml', '.parquet'}
        
        # Критерии совместимости схем
        self.compatibility_thresholds = {
            'column_name_similarity': 0.8,  # 80% совпадение имен колонок
            'column_count_tolerance': 0.1,   # 10% разница в количестве колонок
            'type_compatibility': True       # Строгая совместимость типов
        }
    
    def check_folder_homogeneity(self, folder_path: str, auto_separate: bool = True) -> HomogeneityResult:
        """
        Проверяет однородность файлов в папке.
        
        Args:
            folder_path: Путь к папке для проверки
            auto_separate: Автоматически разделять неоднородные файлы
            
        Returns:
            Результат проверки однородности
        """
        try:
            # Преобразуем путь контейнера в путь хоста
            host_folder_path = folder_path
            if folder_path.startswith('/data'):
                # В контейнере /data мапится на data_landing_zone хоста
                # Но в контейнере нужно использовать /data
                host_folder_path_obj = Path(folder_path)
            else:
                # Если путь не начинается с /data, преобразуем его
                if folder_path.startswith('data_landing_zone'):
                    host_folder_path = folder_path.replace('data_landing_zone', '/data')
                host_folder_path_obj = Path(host_folder_path)
            
            if not host_folder_path_obj.exists():
                raise FileNotFoundError(f"Папка не найдена: {host_folder_path_obj} (исходный путь: {host_folder_path})")
            
            # Сканируем файлы в папке
            files = self._scan_folder_files(host_folder_path_obj)
            
            if not files:
                return HomogeneityResult(
                    folder_path=str(folder_path),
                    homogeneous=True,
                    total_files=0,
                    homogeneous_files=0,
                    inconsistent_files=0,
                    file_analyses=[],
                    schema_differences=[]
                )
            
            # Анализируем схему каждого файла
            file_analyses = []
            schemas = []
            
            for file_path in files:
                try:
                    schema = self._analyze_file_schema(file_path)
                    analysis = FileSchemaAnalysis(
                        file_path=str(file_path),
                        schema=schema,
                        is_consistent=True,  # Будет обновлено позже
                        differences=[]
                    )
                    file_analyses.append(analysis)
                    schemas.append(schema)
                    
                except Exception as e:
                    self.logger.warning(f"Не удалось проанализировать файл {file_path}: {str(e)}")
                    # Создаем пустую схему для проблемного файла
                    empty_schema = SchemaInfo(columns=[], column_types={})
                    analysis = FileSchemaAnalysis(
                        file_path=str(file_path),
                        schema=empty_schema,
                        is_consistent=False,
                        differences=[f"Ошибка анализа: {str(e)}"]
                    )
                    file_analyses.append(analysis)
                    schemas.append(empty_schema)
            
            # Определяем эталонную схему (наиболее часто встречающуюся)
            reference_schema = self._determine_reference_schema(schemas)
            
            # Проверяем совместимость каждого файла с эталонной схемой
            inconsistent_files = []
            schema_differences = []
            
            for i, analysis in enumerate(file_analyses):
                differences = self._compare_schemas(reference_schema, analysis.schema)
                
                if differences:
                    analysis.is_consistent = False
                    analysis.differences = differences
                    inconsistent_files.append(files[i])
                    
                    schema_differences.append({
                        "file": analysis.file_path,
                        "issues": differences
                    })
            
            # Автоматическое разделение неоднородных файлов
            inconsistent_folder_path = None
            if auto_separate and inconsistent_files:
                inconsistent_folder_path = self._separate_inconsistent_files(
                    folder_path, inconsistent_files
                )
            
            homogeneous_files_count = len(files) - len(inconsistent_files)
            
            result = HomogeneityResult(
                folder_path=str(folder_path),
                homogeneous=len(inconsistent_files) == 0,
                total_files=len(files),
                homogeneous_files=homogeneous_files_count,
                inconsistent_files=len(inconsistent_files),
                inconsistent_files_moved_to=inconsistent_folder_path,
                reference_schema=reference_schema,
                file_analyses=file_analyses,
                schema_differences=schema_differences
            )
            
            self.logger.info(f"Проверка однородности завершена. Однородных файлов: {homogeneous_files_count}, неоднородных: {len(inconsistent_files)}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке однородности папки {folder_path}: {str(e)}")
            
            return HomogeneityResult(
                folder_path=str(folder_path),
                homogeneous=False,
                total_files=0,
                homogeneous_files=0,
                inconsistent_files=0,
                file_analyses=[],
                schema_differences=[{"error": str(e)}]
            )
    
    def _scan_folder_files(self, folder_path: Path) -> List[Path]:
        """Сканирует папку и возвращает список поддерживаемых файлов."""
        files = []
        
        try:
            for file_path in folder_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                    files.append(file_path)
            
            self.logger.info(f"Найдено {len(files)} поддерживаемых файлов в папке {folder_path}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при сканировании папки {folder_path}: {str(e)}")
        
        return files
    
    def _analyze_file_schema(self, file_path: Path) -> SchemaInfo:
        """
        Анализирует схему файла.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Информация о схеме файла
        """
        try:
            # Сначала пытаемся использовать модуль 5 для автоопределения
            schema_from_module5 = self._get_schema_from_module5(file_path)
            if schema_from_module5:
                return schema_from_module5
            
            # Fallback к прямому анализу
            return self._analyze_schema_directly(file_path)
            
        except Exception as e:
            self.logger.warning(f"Ошибка при анализе схемы файла {file_path}: {str(e)}")
            return SchemaInfo(columns=[], column_types={})
    
    def _get_schema_from_module5(self, file_path: Path) -> Optional[SchemaInfo]:
        """Получает схему файла через модуль 5."""
        try:
            response = requests.get(
                f"{self.module5_url}/auto-detect",
                params={"source": str(file_path)},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Извлекаем информацию о схеме из ответа модуля 5
                if "structure_info" in data and "columns" in data["structure_info"]:
                    columns_info = data["structure_info"]["columns"]
                    
                    columns = list(columns_info.keys())
                    column_types = {col: info.get("type", "unknown") for col, info in columns_info.items()}
                    
                    # Извлекаем дополнительную информацию
                    separator = data.get("structure_info", {}).get("separator")
                    encoding = data.get("structure_info", {}).get("encoding")
                    
                    return SchemaInfo(
                        columns=columns,
                        column_types=column_types,
                        separator=separator,
                        encoding=encoding
                    )
                    
        except Exception as e:
            self.logger.debug(f"Не удалось получить схему через модуль 5 для {file_path}: {str(e)}")
        
        return None
    
    def _analyze_schema_directly(self, file_path: Path) -> SchemaInfo:
        """Анализирует схему файла напрямую."""
        extension = file_path.suffix.lower()
        
        if extension == '.csv':
            return self._analyze_csv_schema(file_path)
        elif extension == '.json':
            return self._analyze_json_schema(file_path)
        elif extension == '.xml':
            return self._analyze_xml_schema(file_path)
        elif extension == '.parquet':
            return self._analyze_parquet_schema(file_path)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {extension}")
    
    def _analyze_csv_schema(self, file_path: Path) -> SchemaInfo:
        """Анализирует схему CSV файла."""
        # Пробуем различные разделители
        separators = [',', ';', '\t', '|']
        encodings = ['utf-8', 'latin-1', 'cp1251']
        
        for encoding in encodings:
            for separator in separators:
                try:
                    df = pd.read_csv(file_path, sep=separator, encoding=encoding, nrows=100)
                    
                    if len(df.columns) > 1:  # Успешно распарсили
                        columns = df.columns.tolist()
                        column_types = {col: str(df[col].dtype) for col in columns}
                        
                        return SchemaInfo(
                            columns=columns,
                            column_types=column_types,
                            separator=separator,
                            encoding=encoding
                        )
                        
                except Exception:
                    continue
        
        # Если не удалось распарсить, возвращаем пустую схему
        return SchemaInfo(columns=[], column_types={})
    
    def _analyze_json_schema(self, file_path: Path) -> SchemaInfo:
        """Анализирует схему JSON файла."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Пытаемся прочитать как обычный JSON
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    # Пытаемся прочитать как JSON Lines
                    f.seek(0)
                    lines = f.readlines()[:10]  # Читаем первые 10 строк
                    data = [json.loads(line.strip()) for line in lines if line.strip()]
            
            # Извлекаем схему из данных
            if isinstance(data, list) and data:
                sample_record = data[0]
            elif isinstance(data, dict):
                sample_record = data
            else:
                return SchemaInfo(columns=[], column_types={})
            
            columns = list(sample_record.keys())
            column_types = {}
            
            for col, value in sample_record.items():
                if isinstance(value, int):
                    column_types[col] = "int64"
                elif isinstance(value, float):
                    column_types[col] = "float64"
                elif isinstance(value, bool):
                    column_types[col] = "bool"
                elif isinstance(value, str):
                    column_types[col] = "object"
                else:
                    column_types[col] = "object"
            
            return SchemaInfo(
                columns=columns,
                column_types=column_types
            )
            
        except Exception as e:
            self.logger.warning(f"Ошибка при анализе JSON файла {file_path}: {str(e)}")
            return SchemaInfo(columns=[], column_types={})
    
    def _analyze_xml_schema(self, file_path: Path) -> SchemaInfo:
        """Анализирует схему XML файла."""
        try:
            import xml.etree.ElementTree as ET
            
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Ищем повторяющиеся элементы (записи)
            record_tags = ['item', 'record', 'row', 'entry', 'data']
            
            for tag in record_tags:
                records = root.findall(f".//{tag}")
                if records:
                    # Анализируем первую запись
                    first_record = records[0]
                    columns = []
                    column_types = {}
                    
                    for child in first_record:
                        columns.append(child.tag)
                        # Пытаемся определить тип по содержимому
                        text = child.text or ""
                        if text.isdigit():
                            column_types[child.tag] = "int64"
                        elif text.replace('.', '').isdigit():
                            column_types[child.tag] = "float64"
                        else:
                            column_types[child.tag] = "object"
                    
                    return SchemaInfo(
                        columns=columns,
                        column_types=column_types
                    )
            
            # Если не нашли стандартные теги, анализируем структуру
            all_tags = set()
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    all_tags.add(elem.tag)
            
            columns = list(all_tags)
            column_types = {col: "object" for col in columns}
            
            return SchemaInfo(
                columns=columns,
                column_types=column_types
            )
            
        except Exception as e:
            self.logger.warning(f"Ошибка при анализе XML файла {file_path}: {str(e)}")
            return SchemaInfo(columns=[], column_types={})
    
    def _analyze_parquet_schema(self, file_path: Path) -> SchemaInfo:
        """Анализирует схему Parquet файла."""
        try:
            df = pd.read_parquet(file_path, engine='pyarrow')
            
            columns = df.columns.tolist()
            column_types = {col: str(df[col].dtype) for col in columns}
            
            return SchemaInfo(
                columns=columns,
                column_types=column_types
            )
            
        except Exception as e:
            self.logger.warning(f"Ошибка при анализе Parquet файла {file_path}: {str(e)}")
            return SchemaInfo(columns=[], column_types={})
    
    def _determine_reference_schema(self, schemas: List[SchemaInfo]) -> SchemaInfo:
        """Определяет эталонную схему на основе наиболее часто встречающейся."""
        if not schemas:
            return SchemaInfo(columns=[], column_types={})
        
        # Группируем схемы по количеству колонок и именам
        schema_groups = {}
        
        for schema in schemas:
            # Создаем ключ на основе отсортированных имен колонок
            key = tuple(sorted(schema.columns))
            
            if key not in schema_groups:
                schema_groups[key] = []
            schema_groups[key].append(schema)
        
        # Выбираем наиболее часто встречающуюся группу
        if not schema_groups:
            return schemas[0]
        
        most_common_group = max(schema_groups.values(), key=len)
        
        # Возвращаем первую схему из наиболее частой группы
        return most_common_group[0]
    
    def _compare_schemas(self, reference: SchemaInfo, target: SchemaInfo) -> List[str]:
        """Сравнивает две схемы и возвращает список различий."""
        differences = []
        
        # Проверяем количество колонок
        if len(reference.columns) != len(target.columns):
            differences.append(f"Разное количество колонок: эталон {len(reference.columns)}, файл {len(target.columns)}")
        
        # Проверяем имена колонок
        ref_columns = set(reference.columns)
        target_columns = set(target.columns)
        
        missing_columns = ref_columns - target_columns
        extra_columns = target_columns - ref_columns
        
        if missing_columns:
            differences.append(f"Отсутствующие колонки: {list(missing_columns)}")
        
        if extra_columns:
            differences.append(f"Дополнительные колонки: {list(extra_columns)}")
        
        # Проверяем типы данных для общих колонок
        common_columns = ref_columns & target_columns
        
        for column in common_columns:
            ref_type = reference.column_types.get(column, "unknown")
            target_type = target.column_types.get(column, "unknown")
            
            if not self._are_types_compatible(ref_type, target_type):
                differences.append(f"Несовместимые типы в колонке '{column}': эталон {ref_type}, файл {target_type}")
        
        # Проверяем разделители для CSV файлов
        if reference.separator and target.separator:
            if reference.separator != target.separator:
                differences.append(f"Разные разделители: эталон '{reference.separator}', файл '{target.separator}'")
        
        return differences
    
    def _are_types_compatible(self, type1: str, type2: str) -> bool:
        """Проверяет совместимость типов данных."""
        # Группы совместимых типов
        numeric_types = {'int64', 'int32', 'float64', 'float32', 'number', 'integer'}
        string_types = {'object', 'string', 'str', 'text'}
        
        # Нормализуем типы
        type1_norm = type1.lower()
        type2_norm = type2.lower()
        
        # Точное совпадение
        if type1_norm == type2_norm:
            return True
        
        # Совместимые числовые типы
        if type1_norm in numeric_types and type2_norm in numeric_types:
            return True
        
        # Совместимые строковые типы
        if type1_norm in string_types and type2_norm in string_types:
            return True
        
        return False
    
    def _separate_inconsistent_files(self, folder_path: Path, inconsistent_files: List[Path]) -> str:
        """
        Создает новую папку и перемещает туда неоднородные файлы.
        
        Args:
            folder_path: Исходная папка
            inconsistent_files: Список неоднородных файлов
            
        Returns:
            Путь к папке с неоднородными файлами
        """
        try:
            # Создаем имя новой папки
            inconsistent_folder_name = f"{folder_path.name}_inconsistent"
            inconsistent_folder_path = folder_path.parent / inconsistent_folder_name
            
            # Создаем папку если она не существует
            inconsistent_folder_path.mkdir(exist_ok=True)
            
            # Перемещаем файлы
            moved_files = []
            for file_path in inconsistent_files:
                try:
                    destination = inconsistent_folder_path / file_path.name
                    
                    # Если файл с таким именем уже существует, добавляем суффикс
                    counter = 1
                    original_destination = destination
                    while destination.exists():
                        stem = original_destination.stem
                        suffix = original_destination.suffix
                        destination = inconsistent_folder_path / f"{stem}_{counter}{suffix}"
                        counter += 1
                    
                    shutil.move(str(file_path), str(destination))
                    moved_files.append(str(destination))
                    
                except Exception as e:
                    self.logger.error(f"Ошибка при перемещении файла {file_path}: {str(e)}")
            
            # Создаем файл с отчетом о перемещении
            report_file = inconsistent_folder_path / "separation_report.json"
            report = {
                "separation_timestamp": pd.Timestamp.now().isoformat(),
                "original_folder": str(folder_path),
                "moved_files": moved_files,
                "reason": "Schema inconsistency detected"
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Перемещено {len(moved_files)} неоднородных файлов в папку {inconsistent_folder_path}")
            
            return str(inconsistent_folder_path)
            
        except Exception as e:
            self.logger.error(f"Ошибка при разделении неоднородных файлов: {str(e)}")
            return ""
