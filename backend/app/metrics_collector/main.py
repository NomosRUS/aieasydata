import psycopg2
import clickhouse_connect
import os
import glob
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, Union
from .schemas import ConnectionInfo
from ..data_type_detector import DataTypeDetector

# Добавляем поддержку XML
try:
    from lxml import etree
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False

def collect_metrics(conn_info: ConnectionInfo) -> dict:
    """Главная функция-диспетчер для сбора метрик."""
    if conn_info.db_type == 'clickhouse':
        return _collect_clickhouse_metrics(conn_info)
    elif conn_info.db_type == 'postgres':
        return _collect_postgres_metrics(conn_info)
    elif conn_info.db_type == 'file_system':
        return _collect_filesystem_metrics(conn_info)
    else:
        raise ValueError(f"Unsupported DB type: {conn_info.db_type}")

def auto_detect_and_collect_metrics(source: str) -> dict:
    """
    Автоматически определяет тип данных и собирает метрики.
    Это главная функция для модуля 3 - она сама определит что перед ней.
    """
    detector = DataTypeDetector()
    detection_result = detector.detect_data_type(source)
    
    # Собираем базовые метрики
    metrics = {}
    
    if detection_result['type'] == 'database':
        # Создаем ConnectionInfo для БД
        conn_info = ConnectionInfo(
            db_type=detection_result['db_type'],
            host=detection_result.get('host', 'localhost'),
            port=detection_result.get('port', 5432 if detection_result['db_type'] == 'postgres' else 8123),
            user=detection_result.get('user', 'default'),
            password=detection_result.get('password', ''),
            db_name=detection_result.get('database', 'default'),
            table_name=detection_result.get('tables', ['unknown'])[0] if detection_result.get('tables') else 'unknown'
        )
        metrics = collect_metrics(conn_info)
    
    elif detection_result['type'] in ['file', 'directory']:
        # Создаем ConnectionInfo для файловой системы
        conn_info = ConnectionInfo(
            db_type='file_system',
            host='localhost',
            port=0,
            user='',
            password='',
            db_name='',
            table_name='',
            file_path=source
        )
        metrics = collect_metrics(conn_info)
    
    else:
        metrics = {
            'error': f"Unsupported data type: {detection_result['type']}",
            'row_count': 0,
            'size_in_bytes': 0,
            'file_count': 0
        }
    
    # Добавляем информацию об автоопределении
    metrics.update({
        'data_type': detection_result.get('format', detection_result.get('type')),
        'format': detection_result.get('format'),
        'detected_type': detection_result.get('type'),
        'schema': detection_result.get('schema'),
        'separator': detection_result.get('separator'),
        'encoding': detection_result.get('encoding'),
        'detection_details': detection_result
    })
    
    return metrics

def _collect_clickhouse_metrics(conn_info: ConnectionInfo) -> dict:
    """Собирает метрики из ClickHouse."""
    metrics = {}
    try:
        client = clickhouse_connect.get_client(
            host=conn_info.host,
            port=conn_info.port,
            user=conn_info.user,
            password=conn_info.password
        )

        # Базовые метрики: количество строк и размер
        size_query = f"""
        SELECT
            count() AS row_count,
            sum(bytes_on_disk) AS size_in_bytes
        FROM system.parts
        WHERE database = '{conn_info.db_name}' AND table = '{conn_info.table_name}' AND active
        """
        result = client.query(size_query)
        metrics['row_count'] = result.result_rows[0][0] if result.result_rows else 0
        metrics['size_in_bytes'] = result.result_rows[0][1] if result.result_rows else 0

        # Метрики производительности
        perf_query = f"""
        SELECT
            avg(query_duration_ms) AS avg_query_duration_ms,
            quantile(0.95)(query_duration_ms) AS p95_query_duration_ms,
            count() AS total_queries
        FROM system.query_log
        WHERE (query LIKE '%%{conn_info.table_name}%%') AND (type = 'QueryFinish')
        """
        result = client.query(perf_query)
        metrics['avg_query_duration_ms'] = result.result_rows[0][0] if result.result_rows else 0
        metrics['p95_query_duration_ms'] = result.result_rows[0][1] if result.result_rows else 0
        metrics['total_queries'] = result.result_rows[0][2] if result.result_rows else 0

    except Exception as e:
        # В случае ошибки возвращаем базовые значения, чтобы не ломать API
        print(f"Error collecting ClickHouse metrics: {e}")
        return {"row_count": 0, "size_in_bytes": 0}

    return metrics

def _collect_postgres_metrics(conn_info: ConnectionInfo) -> dict:
    """Собирает метрики из PostgreSQL."""
    metrics = {}
    dsn = f"dbname='{conn_info.db_name}' user='{conn_info.user}' password='{conn_info.password}' host='{conn_info.host}' port='{conn_info.port}'"
    try:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cursor:
                # В PostgreSQL нет простого способа получить schema из DSN, предполагаем 'public' или передаем явно
                schema_name = 'analytics' # Хардкод для нашего случая

                # Размер таблицы
                cursor.execute(f"SELECT pg_total_relation_size('{schema_name}.{conn_info.table_name}')")
                size_result = cursor.fetchone()
                metrics['size_in_bytes'] = size_result[0] if size_result else 0

                # Приблизительное количество строк
                cursor.execute(f"SELECT reltuples::bigint FROM pg_class WHERE relname = '{conn_info.table_name}'")
                rows_result = cursor.fetchone()
                metrics['row_count'] = rows_result[0] if rows_result else 0

                # Метрики производительности (требуют pg_stat_statements)
                try:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                    cursor.execute(f"""
                    SELECT mean_exec_time, calls
                    FROM pg_stat_statements
                    WHERE query LIKE '%%{conn_info.table_name}%%'
                    LIMIT 1
                    """)
                    perf_result = cursor.fetchone()
                    if perf_result:
                        metrics['avg_query_duration_ms'] = perf_result[0]
                        metrics['total_queries'] = perf_result[1]
                except psycopg2.Error as pg_err:
                    print(f"Could not query pg_stat_statements: {pg_err}")
                    conn.rollback() # Откатываем CREATE EXTENSION если что-то пошло не так

    except Exception as e:
        print(f"Error collecting PostgreSQL metrics: {e}")
        return {"row_count": 0, "size_in_bytes": 0}

    return metrics

def _collect_filesystem_metrics(conn_info: ConnectionInfo) -> dict:
    """Собирает метрики из файловой системы (data_landing_zone)."""
    metrics = {
        "row_count": 0,
        "size_in_bytes": 0,
        "file_count": 0,
        "avg_file_size": 0,
        "file_types": {}
    }
    
    try:
        if not conn_info.file_path:
            raise ValueError("file_path is required for file_system monitoring")
            
        path = Path(conn_info.file_path)
        
        if not path.exists():
            print(f"Warning: Path {conn_info.file_path} does not exist")
            return metrics
            
        total_size = 0
        file_count = 0
        row_count = 0
        file_types = {}
        
        # Рекурсивный обход всех файлов
        for file_path in path.rglob("*"):
            if file_path.is_file():
                file_size = file_path.stat().st_size
                total_size += file_size
                file_count += 1
                
                # Подсчет типов файлов
                file_ext = file_path.suffix.lower()
                if file_ext in file_types:
                    file_types[file_ext] += 1
                else:
                    file_types[file_ext] = 1
                
                # Попытка подсчета строк для структурированных файлов
                try:
                    if file_ext in ['.csv', '.tsv']:
                        # Пробуем разные разделители для CSV
                        df = None
                        for sep in [',', ';', '\t']:
                            try:
                                df = pd.read_csv(file_path, sep=sep, nrows=1)
                                # Проверяем, что получили больше одной колонки
                                if len(df.columns) > 1:
                                    # Читаем весь файл с найденным разделителем
                                    df = pd.read_csv(file_path, sep=sep)
                                    row_count += len(df)
                                    break
                            except:
                                continue
                        
                        # Если не удалось определить разделитель, читаем как есть
                        if df is None:
                            df = pd.read_csv(file_path)
                            row_count += len(df)
                            
                    elif file_ext in ['.json', '.jsonl']:
                        # Обработка JSON файлов
                        json_rows = _count_json_rows(file_path)
                        row_count += json_rows
                        
                    elif file_ext in ['.xml']:
                        # Обработка XML файлов
                        if XML_AVAILABLE:
                            xml_rows = _count_xml_rows(file_path)
                            row_count += xml_rows
                        else:
                            print(f"XML support not available, skipping {file_path}")
                            
                    elif file_ext in ['.parquet']:
                        df = pd.read_parquet(file_path)
                        row_count += len(df)
                        
                except Exception as e:
                    # Если не удается прочитать файл, просто пропускаем подсчет строк
                    print(f"Could not read file {file_path} for row counting: {e}")
                    continue
        
        metrics.update({
            "row_count": row_count,
            "size_in_bytes": total_size,
            "file_count": file_count,
            "avg_file_size": total_size // file_count if file_count > 0 else 0,
            "file_types": file_types
        })
        
    except Exception as e:
        print(f"Error collecting filesystem metrics: {e}")
        # Возвращаем базовые метрики в случае ошибки
        return {"row_count": 0, "size_in_bytes": 0, "file_count": 0}
    
    return metrics

def _count_json_rows(file_path: Path) -> int:
    """Подсчитывает количество строк в JSON файле."""
    try:
        file_size = file_path.stat().st_size
        
        # Для очень больших файлов (>100MB) используем оптимизированный подход
        if file_size > 100 * 1024 * 1024:
            print(f"Large JSON file detected: {file_path.name} ({file_size / 1024**2:.1f}MB)")
            return _count_json_rows_optimized(file_path)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            # Вариант 1: JSON Lines (каждая строка - отдельный JSON объект)
            if file_path.suffix.lower() == '.jsonl':
                content = f.read()
                return len(content.strip().split('\n'))
            
            # Вариант 2: Обычный JSON
            try:
                content = f.read()
                data = json.loads(content)
                if isinstance(data, list):
                    return len(data)
                elif isinstance(data, dict):
                    return 1
                else:
                    return 1
            except json.JSONDecodeError:
                # Вариант 3: Попробуем как JSON Lines
                f.seek(0)
                valid_lines = 0
                for line in f:
                    try:
                        json.loads(line.strip())
                        valid_lines += 1
                    except:
                        continue
                return valid_lines
                
    except Exception as e:
        print(f"Error counting JSON rows in {file_path}: {e}")
        return 0

def _count_json_rows_optimized(file_path: Path) -> int:
    """Оптимизированный подсчет для больших JSON файлов."""
    try:
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            # Читаем файл по частям
            buffer_size = 1024 * 1024  # 1MB буфер
            buffer = ""
            
            while True:
                chunk = f.read(buffer_size)
                if not chunk:
                    break
                    
                buffer += chunk
                
                # Ищем завершенные JSON объекты
                lines = buffer.split('\n')
                buffer = lines[-1]  # Сохраняем неполную строку
                
                for line in lines[:-1]:
                    line = line.strip()
                    if line:
                        try:
                            json.loads(line)
                            count += 1
                        except:
                            # Возможно, это массив JSON - пробуем другой подход
                            if '[' in line or '{' in line:
                                # Подсчитываем количество открывающих скобок как приблизительное количество объектов
                                count += line.count('{')
                
                # Показываем прогресс для больших файлов
                if count > 0 and count % 50000 == 0:
                    print(f"Processed {count} JSON records so far...")
            
            # Обрабатываем последнюю строку
            if buffer.strip():
                try:
                    json.loads(buffer.strip())
                    count += 1
                except:
                    count += buffer.count('{')
        
        print(f"JSON file {file_path.name}: {count} records")
        return count
        
    except Exception as e:
        print(f"Error in optimized JSON counting for {file_path}: {e}")
        return 0

def _count_xml_rows(file_path: Path) -> int:
    """Подсчитывает количество записей в XML файле."""
    try:
        if not XML_AVAILABLE:
            return 0
            
        # Определяем тег записи - ищем элементы второго уровня (дети root)
        record_tag = None
        
        try:
            # Быстрый анализ для определения тега записи
            context = etree.iterparse(str(file_path), events=('start',))
            level = 0
            for event, elem in context:
                level += 1
                if level == 2:  # Второй уровень - это обычно записи
                    record_tag = elem.tag
                    print(f"Found record tag: {record_tag}")
                    break
                elif level > 5:  # Не идем слишком глубоко
                    break
        except Exception as e:
            print(f"Error determining record tag: {e}")
        
        # Если не нашли тег, пробуем стандартные варианты
        if not record_tag:
            common_tags = ['item', 'record', 'row', 'entry', 'data']
            for tag in common_tags:
                try:
                    context = etree.iterparse(str(file_path), events=('end',), tag=tag)
                    for _, elem in context:
                        record_tag = tag
                        print(f"Using common tag: {record_tag}")
                        break
                    if record_tag:
                        break
                except:
                    continue
        
        if not record_tag:
            print(f"Could not determine record tag for {file_path}")
            return 0
        
        # Подсчитываем записи с найденным тегом
        count = 0
        try:
            context = etree.iterparse(str(file_path), events=('end',), tag=record_tag)
            for _, elem in context:
                count += 1
                # Очищаем память для больших файлов
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
                    
                # Прерываем подсчет для очень больших файлов (оптимизация)
                if count > 0 and count % 100000 == 0:
                    print(f"Processed {count} records so far...")
                    
        except Exception as e:
            print(f"Error parsing XML {file_path}: {e}")
            return count  # Возвращаем то, что успели подсчитать
            
        print(f"XML file {file_path.name}: {count} records")
        return count
        
    except Exception as e:
        print(f"Error counting XML rows in {file_path}: {e}")
        return 0

def get_connection_info_from_warehouse_instance(design_id: str, db_type: str) -> ConnectionInfo:
    """Создает ConnectionInfo на основе данных из WarehouseInstance."""
    # Эта функция будет использоваться для интеграции с модулем 4
    # Получает параметры подключения из созданного хранилища
    
    if db_type == 'clickhouse':
        return ConnectionInfo(
            db_type='clickhouse',
            host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
            port=int(os.getenv('CLICKHOUSE_PORT', '8123')),
            user=os.getenv('CLICKHOUSE_USER', 'default'),
            password=os.getenv('CLICKHOUSE_PASSWORD', ''),
            db_name='analytics',  # Стандартная схема из модуля 4
            table_name='unknown',
            design_id=design_id
        )
    elif db_type == 'postgres':
        return ConnectionInfo(
            db_type='postgres',
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            user=os.getenv('POSTGRES_USER', 'user'),
            password=os.getenv('POSTGRES_PASSWORD', 'password'),
            db_name=os.getenv('POSTGRES_DB', 'aieasydata'),
            table_name='unknown',
            design_id=design_id
        )
    elif db_type == 'file_system':
        return ConnectionInfo(
            db_type='file_system',
            host='localhost',
            port=0,
            user='',
            password='',
            db_name='',
            table_name='',
            file_path='/data/landing_zone',  # Стандартный путь для data_landing_zone
            design_id=design_id
        )
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

def _get_real_db_connection_info(db_type: str, table_name: str = None) -> ConnectionInfo:
    """Получает информацию о подключении к реальным БД из модуля 4."""
    
    if db_type == 'clickhouse':
        return ConnectionInfo(
            db_type='clickhouse',
            host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
            port=int(os.getenv('CLICKHOUSE_PORT', '8123')),
            user=os.getenv('CLICKHOUSE_USER', 'default'),
            password=os.getenv('CLICKHOUSE_PASSWORD', ''),
            db_name='analytics',  # Стандартная схема из модуля 4
            table_name=table_name or 'unknown'
        )
    elif db_type == 'postgres':
        return ConnectionInfo(
            db_type='postgres',
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            user=os.getenv('POSTGRES_USER', 'user'),
            password=os.getenv('POSTGRES_PASSWORD', 'password'),
            db_name=os.getenv('POSTGRES_DB', 'aieasydata'),
            table_name=table_name or 'unknown'
        )
    else:
        raise ValueError(f"Unsupported database type for real DB connection: {db_type}")
