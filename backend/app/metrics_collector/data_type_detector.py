#!/usr/bin/env python3
"""
Модуль автоматического определения типов данных для модуля 3
Может определить: CSV, JSON, XML, реальные БД (ClickHouse, PostgreSQL)
"""

import os
import json
import re
import csv
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse

# Попытка импорта библиотек для работы с БД
try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import clickhouse_connect
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False

try:
    from lxml import etree
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False

class DataTypeDetector:
    """Класс для автоматического определения типов данных."""
    
    def __init__(self):
        self.supported_file_extensions = {
            '.csv': 'csv',
            '.tsv': 'csv',
            '.json': 'json',
            '.jsonl': 'json',
            '.xml': 'xml',
            '.parquet': 'parquet',
            '.xlsx': 'excel',
            '.xls': 'excel'
        }
    
    def detect_data_type(self, source: str) -> Dict[str, Any]:
        """
        Главная функция определения типа данных.
        
        Args:
            source: Путь к файлу, директории или строка подключения к БД
            
        Returns:
            Dict с информацией о типе данных и параметрах подключения
        """
        
        # 1. Проверяем, является ли это строкой подключения к БД
        db_result = self._detect_database_connection(source)
        if db_result['type'] != 'unknown':
            return db_result
        
        # 2. Проверяем, является ли это файлом
        if os.path.isfile(source):
            return self._detect_file_type(source)
        
        # 3. Проверяем, является ли это директорией
        if os.path.isdir(source):
            return self._detect_directory_type(source)
        
        # 4. Проверяем, является ли это URL
        if self._is_url(source):
            return self._detect_url_type(source)
        
        # 5. Если ничего не подошло
        return {
            'type': 'unknown',
            'source': source,
            'error': 'Could not determine data type'
        }
    
    def _detect_database_connection(self, source: str) -> Dict[str, Any]:
        """Определяет тип БД по строке подключения или параметрам."""
        
        # Паттерны для определения типа БД
        db_patterns = {
            'postgresql': [
                r'postgresql://',
                r'postgres://',
                r'host.*port.*dbname',
                r'psycopg2'
            ],
            'clickhouse': [
                r'clickhouse://',
                r'http://.*:8123',
                r'tcp://.*:9000',
                r'clickhouse_connect'
            ]
        }
        
        source_lower = source.lower()
        
        for db_type, patterns in db_patterns.items():
            for pattern in patterns:
                if re.search(pattern, source_lower):
                    return self._analyze_database_connection(source, db_type)
        
        # Проверяем стандартные порты
        if ':5432' in source:
            return self._analyze_database_connection(source, 'postgresql')
        elif ':8123' in source or ':9000' in source:
            return self._analyze_database_connection(source, 'clickhouse')
        
        return {'type': 'unknown'}
    
    def _analyze_database_connection(self, source: str, db_type: str) -> Dict[str, Any]:
        """Анализирует параметры подключения к БД."""
        
        result = {
            'type': 'database',
            'db_type': db_type,
            'source': source,
            'connection_available': False,
            'tables': [],
            'estimated_size': 0
        }
        
        # Пытаемся извлечь параметры подключения
        connection_params = self._parse_connection_string(source, db_type)
        result.update(connection_params)
        
        # Пытаемся подключиться и получить метаданные
        if db_type == 'postgresql' and POSTGRES_AVAILABLE:
            try:
                conn = psycopg2.connect(source)
                result['connection_available'] = True
                result['tables'] = self._get_postgres_tables(conn)
                conn.close()
            except Exception as e:
                result['connection_error'] = str(e)
        
        elif db_type == 'clickhouse' and CLICKHOUSE_AVAILABLE:
            try:
                # Парсим параметры для ClickHouse
                params = self._parse_clickhouse_params(source)
                client = clickhouse_connect.get_client(**params)
                result['connection_available'] = True
                result['tables'] = self._get_clickhouse_tables(client)
                client.close()
            except Exception as e:
                result['connection_error'] = str(e)
        
        return result
    
    def _detect_file_type(self, file_path: str) -> Dict[str, Any]:
        """Определяет тип отдельного файла."""
        
        path = Path(file_path)
        file_ext = path.suffix.lower()
        
        result = {
            'type': 'file',
            'file_type': self.supported_file_extensions.get(file_ext, 'unknown'),
            'source': file_path,
            'file_size': path.stat().st_size,
            'file_name': path.name
        }
        
        # Дополнительный анализ содержимого
        if result['file_type'] == 'unknown':
            result['file_type'] = self._detect_by_content(file_path)
        
        # Детальный анализ структуры данных
        if result['file_type'] in ['csv', 'json', 'xml']:
            if result['file_type'] == 'csv':
                csv_info = self._analyze_csv_file(file_path)
                result.update(csv_info)
            else:
                structure_info = self._analyze_file_structure(file_path, result['file_type'])
                result.update(structure_info)
        
        return result
    
    def _detect_directory_type(self, dir_path: str) -> Dict[str, Any]:
        """Определяет тип данных в директории."""
        
        path = Path(dir_path)
        
        result = {
            'type': 'directory',
            'source': dir_path,
            'total_files': 0,
            'file_types': {},
            'total_size': 0,
            'dominant_type': 'unknown'
        }
        
        # Анализируем все файлы в директории
        for file_path in path.rglob("*"):
            if file_path.is_file():
                result['total_files'] += 1
                result['total_size'] += file_path.stat().st_size
                
                file_ext = file_path.suffix.lower()
                file_type = self.supported_file_extensions.get(file_ext, 'other')
                
                if file_type in result['file_types']:
                    result['file_types'][file_type] += 1
                else:
                    result['file_types'][file_type] = 1
        
        # Определяем доминирующий тип
        if result['file_types']:
            result['dominant_type'] = max(result['file_types'], key=result['file_types'].get)
        
        # Анализ первого файла доминирующего типа
        if result['dominant_type'] in ['csv', 'json', 'xml']:
            sample_file = self._find_sample_file(dir_path, result['dominant_type'])
            if sample_file:
                structure_info = self._analyze_file_structure(sample_file, result['dominant_type'])
                result['sample_structure'] = structure_info
        
        return result
    
    def _detect_by_content(self, file_path: str) -> str:
        """Определяет тип файла по содержимому."""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = [f.readline().strip() for _ in range(3)]
                content_sample = ''.join(first_lines)
            
            # JSON проверка
            if content_sample.startswith('{') or content_sample.startswith('['):
                try:
                    json.loads(content_sample)
                    return 'json'
                except:
                    pass
            
            # XML проверка
            if content_sample.startswith('<?xml') or content_sample.startswith('<'):
                return 'xml'
            
            # CSV проверка (наличие разделителей)
            if any(sep in content_sample for sep in [',', ';', '\t']):
                return 'csv'
            
        except Exception:
            pass
        
        return 'unknown'
    
    def _analyze_file_structure(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Анализирует структуру файла данных."""
        
        structure = {
            'columns': [],
            'estimated_rows': 0,
            'sample_data': [],
            'encoding': 'utf-8'
        }
        
        try:
            if file_type == 'csv':
                structure.update(self._analyze_csv_structure(file_path))
            elif file_type == 'json':
                structure.update(self._analyze_json_structure(file_path))
            elif file_type == 'xml' and XML_AVAILABLE:
                structure.update(self._analyze_xml_structure(file_path))
        except Exception as e:
            structure['analysis_error'] = str(e)
        
        return structure
    
    def _analyze_csv_structure(self, file_path: str) -> Dict[str, Any]:
        """Анализирует структуру CSV файла."""
        
        import pandas as pd
        
        # Пробуем разные разделители
        separators = [',', ';', '\t', '|']
        best_separator = ','
        max_columns = 0
        
        for sep in separators:
            try:
                df_sample = pd.read_csv(file_path, sep=sep, nrows=1)
                if len(df_sample.columns) > max_columns:
                    max_columns = len(df_sample.columns)
                    best_separator = sep
            except:
                continue
        
        # Читаем с лучшим разделителем
        df = pd.read_csv(file_path, sep=best_separator, nrows=100)
        
        return {
            'separator': best_separator,
            'columns': list(df.columns),
            'column_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'estimated_rows': self._estimate_csv_rows(file_path, best_separator),
            'sample_data': df.head(3).to_dict('records')
        }
    
    def _analyze_json_structure(self, file_path: str) -> Dict[str, Any]:
        """Анализирует структуру JSON файла."""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            # Пробуем прочитать как обычный JSON
            try:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return {
                        'format': 'json_array',
                        'columns': list(data[0].keys()) if isinstance(data[0], dict) else [],
                        'estimated_rows': len(data),
                        'sample_data': data[:3]
                    }
                elif isinstance(data, dict):
                    return {
                        'format': 'json_object',
                        'columns': list(data.keys()),
                        'estimated_rows': 1,
                        'sample_data': [data]
                    }
            except:
                # Пробуем как JSON Lines
                f.seek(0)
                lines = f.readlines()[:100]
                valid_lines = []
                
                for line in lines:
                    try:
                        obj = json.loads(line.strip())
                        valid_lines.append(obj)
                    except:
                        continue
                
                if valid_lines:
                    return {
                        'format': 'json_lines',
                        'columns': list(valid_lines[0].keys()) if isinstance(valid_lines[0], dict) else [],
                        'estimated_rows': len(lines),
                        'sample_data': valid_lines[:3]
                    }
        
        return {'format': 'unknown'}
    
    def _analyze_xml_structure(self, file_path: str) -> Dict[str, Any]:
        """Анализирует структуру XML файла."""
        
        try:
            # Определяем тег записи
            context = etree.iterparse(file_path, events=('start',))
            level = 0
            record_tag = None
            
            for event, elem in context:
                level += 1
                if level == 2:  # Второй уровень обычно содержит записи
                    record_tag = elem.tag
                    break
                elif level > 5:
                    break
            
            if record_tag:
                # Анализируем структуру записи
                context = etree.iterparse(file_path, events=('end',), tag=record_tag)
                sample_records = []
                
                for i, (_, elem) in enumerate(context):
                    if i < 3:  # Берем первые 3 записи
                        record_data = {child.tag: child.text for child in elem}
                        sample_records.append(record_data)
                        elem.clear()
                    else:
                        break
                
                columns = list(sample_records[0].keys()) if sample_records else []
                
                return {
                    'record_tag': record_tag,
                    'columns': columns,
                    'estimated_rows': self._estimate_xml_rows(file_path, record_tag),
                    'sample_data': sample_records
                }
        
        except Exception as e:
            return {'analysis_error': str(e)}
        
        return {'format': 'unknown'}
    
    def _estimate_csv_rows(self, file_path: str, separator: str) -> int:
        """Оценивает количество строк в CSV файле."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return sum(1 for line in f) - 1  # -1 для заголовка
        except:
            return 0
    
    def _estimate_xml_rows(self, file_path: str, record_tag: str) -> int:
        """Оценивает количество записей в XML файле."""
        try:
            count = 0
            context = etree.iterparse(file_path, events=('end',), tag=record_tag)
            for _, elem in context:
                count += 1
                elem.clear()
                if count > 10000:  # Ограничиваем для больших файлов
                    break
            return count
        except:
            return 0
    
    def _find_sample_file(self, dir_path: str, file_type: str) -> Optional[str]:
        """Находит образец файла указанного типа в директории."""
        
        extensions = {
            'csv': ['.csv', '.tsv'],
            'json': ['.json', '.jsonl'],
            'xml': ['.xml']
        }
        
        target_extensions = extensions.get(file_type, [])
        
        for file_path in Path(dir_path).rglob("*"):
            if file_path.suffix.lower() in target_extensions:
                return str(file_path)
        
        return None
    
    def _is_url(self, source: str) -> bool:
        """Проверяет, является ли строка URL."""
        try:
            result = urlparse(source)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _detect_url_type(self, url: str) -> Dict[str, Any]:
        """Определяет тип данных по URL."""
        return {
            'type': 'url',
            'source': url,
            'url_type': 'api' if 'api' in url.lower() else 'web'
        }
    
    def _parse_connection_string(self, source: str, db_type: str) -> Dict[str, Any]:
        """Парсит строку подключения к БД."""
        
        params = {}
        
        if db_type == 'postgresql':
            # Пример: postgresql://user:password@localhost:5432/dbname
            if '://' in source:
                parsed = urlparse(source)
                params.update({
                    'host': parsed.hostname,
                    'port': parsed.port or 5432,
                    'user': parsed.username,
                    'password': parsed.password,
                    'database': parsed.path.lstrip('/')
                })
        
        elif db_type == 'clickhouse':
            # Пример: http://localhost:8123 или clickhouse://user:password@localhost:9000/db
            if '://' in source:
                parsed = urlparse(source)
                params.update({
                    'host': parsed.hostname,
                    'port': parsed.port or (8123 if parsed.scheme == 'http' else 9000),
                    'user': parsed.username or 'default',
                    'password': parsed.password or '',
                    'database': parsed.path.lstrip('/') or 'default'
                })
        
        return params
    
    def _parse_clickhouse_params(self, source: str) -> Dict[str, Any]:
        """Парсит параметры для ClickHouse подключения."""
        
        if '://' in source:
            parsed = urlparse(source)
            return {
                'host': parsed.hostname or 'localhost',
                'port': parsed.port or 8123,
                'username': parsed.username or 'default',
                'password': parsed.password or '',
                'database': parsed.path.lstrip('/') or 'default'
            }
        
        return {'host': 'localhost', 'port': 8123, 'username': 'default'}
    
    def _get_postgres_tables(self, conn) -> list:
        """Получает список таблиц из PostgreSQL."""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            return [row[0] for row in cursor.fetchall()]
        except:
            return []
    
    def _get_clickhouse_tables(self, client) -> list:
        """Получает список таблиц из ClickHouse."""
        try:
            result = client.query("SHOW TABLES")
            return [row[0] for row in result.result_rows]
        except:
            return []
    
    def _analyze_csv_file(self, file_path: str) -> Dict[str, Any]:
        """Детальный анализ CSV файла с определением разделителя и схемы."""
        result = {
            'format': 'csv',
            'separator': ',',
            'encoding': 'utf-8',
            'schema': None,
            'sample_data': []
        }
        
        try:
            # Определяем кодировку и разделитель
            encodings = ['utf-8', 'latin-1', 'cp1251']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read(2048)  # Читаем первые 2KB
                        result['encoding'] = encoding
                        break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                return result
            
            # Определяем разделитель
            sniffer = csv.Sniffer()
            try:
                # Берем только первые несколько строк для анализа
                sample_lines = '\\n'.join(content.split('\\n')[:10])
                dialect = sniffer.sniff(sample_lines, delimiters=',;\t|')
                result['separator'] = dialect.delimiter
            except:
                # Fallback: подсчитываем разделители в первых строках
                first_lines = '\\n'.join(content.split('\\n')[:5])
                separators = {',': first_lines.count(','), ';': first_lines.count(';'), 
                             '\\t': first_lines.count('\\t'), '|': first_lines.count('|')}
                result['separator'] = max(separators, key=separators.get) if separators else ','
            
            # Анализируем схему
            with open(file_path, 'r', encoding=result['encoding']) as f:
                reader = csv.reader(f, delimiter=result['separator'])
                
                # Читаем заголовки
                headers = next(reader, [])
                if headers:
                    # Читаем несколько строк для определения типов
                    sample_rows = []
                    for i, row in enumerate(reader):
                        if i >= 5:  # Ограничиваем 5 строками
                            break
                        sample_rows.append(row)
                    
                    # Определяем типы колонок
                    columns = []
                    for i, header in enumerate(headers):
                        col_type = self._detect_column_type([row[i] if i < len(row) else '' for row in sample_rows])
                        columns.append({
                            'name': header.strip(),
                            'type': col_type,
                            'index': i
                        })
                    
                    result['schema'] = {
                        'columns': columns,
                        'column_count': len(columns)
                    }
                    result['sample_data'] = sample_rows[:3]  # Первые 3 строки
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _detect_column_type(self, values: list) -> str:
        """Определяет тип колонки по значениям."""
        non_empty_values = [v for v in values if v and str(v).strip()]
        
        if not non_empty_values:
            return 'string'
        
        # Проверяем на числа
        numeric_count = 0
        date_count = 0
        
        for value in non_empty_values:
            value = str(value).strip()
            
            # Проверяем на число
            try:
                float(value)
                numeric_count += 1
                continue
            except ValueError:
                pass
            
            # Проверяем на дату
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
                r'\d{2}\.\d{2}\.\d{4}' # DD.MM.YYYY
            ]
            
            for pattern in date_patterns:
                if re.match(pattern, value):
                    date_count += 1
                    break
        
        total = len(non_empty_values)
        
        if numeric_count / total > 0.8:
            return 'numeric'
        elif date_count / total > 0.8:
            return 'date'
        else:
            return 'string'

# Функция-утилита для быстрого использования
def detect_data_type(source: str) -> Dict[str, Any]:
    """
    Быстрая функция для определения типа данных.
    
    Args:
        source: Путь к файлу, директории или строка подключения к БД
        
    Returns:
        Dict с информацией о типе данных
    """
    detector = DataTypeDetector()
    return detector.detect_data_type(source)

# Пример использования
if __name__ == "__main__":
    # Тестовые примеры
    test_sources = [
        "/data/syn_csv",  # Директория с CSV
        "/data/syn_json/part1.json",  # JSON файл
        "/data/syn_xml/part1.xml",  # XML файл
        "postgresql://user:password@localhost:5432/aieasydata",  # PostgreSQL
        "http://localhost:8123",  # ClickHouse
    ]
    
    detector = DataTypeDetector()
    
    for source in test_sources:
        print(f"\nАнализ: {source}")
        result = detector.detect_data_type(source)
        print(f"Тип: {result['type']}")
        if 'file_type' in result:
            print(f"Формат файла: {result['file_type']}")
        if 'db_type' in result:
            print(f"Тип БД: {result['db_type']}")
        print("-" * 50)
