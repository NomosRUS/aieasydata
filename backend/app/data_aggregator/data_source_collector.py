"""
Сборщик данных из различных источников.
"""

import os
import pandas as pd
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import asyncio
import aiohttp
import psycopg2
from sqlalchemy import create_engine, text
import requests
from urllib.parse import urlparse

from .schemas import DataSource, SourceType, ColumnInfo, SourceAnalysis
from ..database import get_db

logger = logging.getLogger(__name__)


class DataSourceCollector:
    """Класс для подключения и сбора данных из различных источников."""
    
    def __init__(self):
        self.module5_base_url = "http://localhost:8000/api/v1/metrics"
        
    async def analyze_source(self, source: DataSource) -> SourceAnalysis:
        """
        Анализирует источник данных и возвращает информацию о его структуре.
        
        Args:
            source: Конфигурация источника данных
            
        Returns:
            SourceAnalysis: Анализ источника данных
        """
        try:
            if source.source_type == SourceType.FILE:
                return await self._analyze_file_source(source)
            elif source.source_type == SourceType.POSTGRESQL:
                return await self._analyze_postgresql_source(source)
            elif source.source_type == SourceType.CLICKHOUSE:
                return await self._analyze_clickhouse_source(source)
            elif source.source_type == SourceType.HDFS:
                return await self._analyze_hdfs_source(source)
            else:
                raise ValueError(f"Unsupported source type: {source.source_type}")
                
        except Exception as e:
            logger.error(f"Error analyzing source {source.source_id}: {str(e)}")
            return SourceAnalysis(
                source_id=source.source_id,
                source_type=source.source_type,
                columns=[],
                compatibility_issues=[f"Analysis failed: {str(e)}"]
            )
    
    async def _analyze_file_source(self, source: DataSource) -> SourceAnalysis:
        """Анализ файлового источника через интеграцию с модулем 5."""
        try:
            # Используем автоопределение модуля 5
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.module5_base_url}/auto-detect",
                    params={"source": source.path}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_module5_response(source, data)
                    else:
                        # Fallback к прямому анализу файла
                        return await self._direct_file_analysis(source)
                        
        except Exception as e:
            logger.warning(f"Module 5 integration failed, using direct analysis: {str(e)}")
            return await self._direct_file_analysis(source)
    
    async def _direct_file_analysis(self, source: DataSource) -> SourceAnalysis:
        """Прямой анализ файла без модуля 5."""
        try:
            file_path = Path(source.path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {source.path}")
            
            # Определяем тип файла по расширению
            extension = file_path.suffix.lower()
            
            if extension == '.csv':
                # Используем потоковую загрузку для анализа
                df = await self._load_csv_streaming(source.path, ',', 'utf-8', 1000)  # Анализируем первые 1000 строк
            elif extension == '.parquet':
                df = pd.read_parquet(source.path)
            elif extension == '.json':
                df = pd.read_json(source.path, lines=True, nrows=1000)
            else:
                raise ValueError(f"Unsupported file format: {extension}")
            
            columns = []
            for col in df.columns:
                if col in source.selected_columns:
                    columns.append(ColumnInfo(
                        name=col,
                        type=str(df[col].dtype),
                        nullable=df[col].isnull().any(),
                        description=f"Column from {file_path.name}"
                    ))
            
            # Получаем размер файла
            file_size = file_path.stat().st_size
            
            return SourceAnalysis(
                source_id=source.source_id,
                source_type=source.source_type,
                columns=columns,
                row_count=len(df),
                data_size_bytes=file_size,
                sample_data=df.head(5).to_dict('records') if len(df) > 0 else [],
                compatibility_issues=[]
            )
            
        except Exception as e:
            logger.error(f"Direct file analysis failed: {str(e)}")
            raise
    
    async def _analyze_postgresql_source(self, source: DataSource) -> SourceAnalysis:
        """Анализ PostgreSQL источника."""
        try:
            engine = create_engine(source.connection)
            
            # Получаем информацию о колонках
            columns_query = text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = :table_name
                AND column_name = ANY(:selected_columns)
                ORDER BY ordinal_position
            """)
            
            with engine.connect() as conn:
                result = conn.execute(columns_query, {
                    'table_name': source.table,
                    'selected_columns': source.selected_columns
                })
                
                columns = []
                for row in result:
                    columns.append(ColumnInfo(
                        name=row.column_name,
                        type=row.data_type,
                        nullable=row.is_nullable == 'YES',
                        description=f"PostgreSQL column from {source.table}"
                    ))
                
                # Получаем количество строк
                count_query = text(f"SELECT COUNT(*) FROM {source.table}")
                row_count = conn.execute(count_query).scalar()
                
                # Получаем образец данных
                sample_query = text(f"""
                    SELECT {', '.join(source.selected_columns)} 
                    FROM {source.table} 
                    LIMIT 5
                """)
                sample_result = conn.execute(sample_query)
                sample_data = [dict(row._mapping) for row in sample_result]
            
            return SourceAnalysis(
                source_id=source.source_id,
                source_type=source.source_type,
                columns=columns,
                row_count=row_count,
                sample_data=sample_data,
                compatibility_issues=[]
            )
            
        except Exception as e:
            logger.error(f"PostgreSQL analysis failed: {str(e)}")
            raise
    
    async def _analyze_clickhouse_source(self, source: DataSource) -> SourceAnalysis:
        """Анализ ClickHouse источника."""
        try:
            # Парсим URL подключения
            parsed = urlparse(source.connection)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Получаем информацию о колонках
            columns_query = f"""
                SELECT name, type 
                FROM system.columns 
                WHERE table = '{source.table}'
                AND name IN ({', '.join([f"'{col}'" for col in source.selected_columns])})
            """
            
            async with aiohttp.ClientSession() as session:
                # Запрос информации о колонках
                async with session.get(
                    base_url,
                    params={'query': columns_query},
                    headers={'X-ClickHouse-Format': 'JSON'}
                ) as response:
                    if response.status == 200:
                        columns_data = await response.json()
                        
                        columns = []
                        for row in columns_data.get('data', []):
                            columns.append(ColumnInfo(
                                name=row['name'],
                                type=row['type'],
                                nullable='Nullable' in row['type'],
                                description=f"ClickHouse column from {source.table}"
                            ))
                
                # Получаем количество строк
                count_query = f"SELECT COUNT(*) as count FROM {source.table}"
                async with session.get(
                    base_url,
                    params={'query': count_query},
                    headers={'X-ClickHouse-Format': 'JSON'}
                ) as response:
                    if response.status == 200:
                        count_data = await response.json()
                        row_count = count_data['data'][0]['count'] if count_data['data'] else 0
                
                # Получаем образец данных
                sample_query = f"""
                    SELECT {', '.join(source.selected_columns)} 
                    FROM {source.table} 
                    LIMIT 5
                """
                async with session.get(
                    base_url,
                    params={'query': sample_query},
                    headers={'X-ClickHouse-Format': 'JSON'}
                ) as response:
                    if response.status == 200:
                        sample_data_response = await response.json()
                        sample_data = sample_data_response.get('data', [])
            
            return SourceAnalysis(
                source_id=source.source_id,
                source_type=source.source_type,
                columns=columns,
                row_count=row_count,
                sample_data=sample_data,
                compatibility_issues=[]
            )
            
        except Exception as e:
            logger.error(f"ClickHouse analysis failed: {str(e)}")
            raise
    
    async def _analyze_hdfs_source(self, source: DataSource) -> SourceAnalysis:
        """Анализ HDFS источника."""
        try:
            # Для HDFS используем WebHDFS API
            # Предполагаем, что файлы в формате Parquet
            
            # Пока возвращаем базовую информацию
            # В реальной реализации здесь был бы запрос к HDFS
            columns = []
            for col in source.selected_columns:
                columns.append(ColumnInfo(
                    name=col,
                    type="string",  # Базовый тип, в реальности нужно определять
                    nullable=True,
                    description=f"HDFS column from {source.path}"
                ))
            
            return SourceAnalysis(
                source_id=source.source_id,
                source_type=source.source_type,
                columns=columns,
                row_count=None,  # Требует дополнительного запроса
                data_size_bytes=None,
                sample_data=[],
                compatibility_issues=["HDFS analysis requires additional implementation"]
            )
            
        except Exception as e:
            logger.error(f"HDFS analysis failed: {str(e)}")
            raise
    
    def _parse_module5_response(self, source: DataSource, data: Dict[str, Any]) -> SourceAnalysis:
        """Парсит ответ от модуля 5 в SourceAnalysis."""
        try:
            columns = []
            
            # Извлекаем информацию о колонках из ответа модуля 5
            structure_info = data.get('structure_info', {})
            columns_info = structure_info.get('columns', [])
            
            for col_info in columns_info:
                if col_info.get('name') in source.selected_columns:
                    columns.append(ColumnInfo(
                        name=col_info.get('name'),
                        type=col_info.get('type', 'unknown'),
                        nullable=col_info.get('nullable', True),
                        description=f"Column detected by Module 5"
                    ))
            
            return SourceAnalysis(
                source_id=source.source_id,
                source_type=source.source_type,
                columns=columns,
                row_count=data.get('row_count'),
                data_size_bytes=data.get('data_size_bytes'),
                sample_data=data.get('sample_data', []),
                compatibility_issues=[]
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Module 5 response: {str(e)}")
            raise
    
    async def load_data(self, source: DataSource, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Загружает данные из источника с оптимизацией памяти.
        
        Args:
            source: Конфигурация источника данных
            limit: Ограничение на количество строк
            
        Returns:
            pd.DataFrame: Загруженные данные
        """
        try:
            # Принудительная очистка памяти перед загрузкой
            import gc
            gc.collect()
            
            if source.source_type == SourceType.FILE:
                result = await self._load_file_data(source, limit)
            elif source.source_type == SourceType.POSTGRESQL:
                result = await self._load_postgresql_data(source, limit)
            elif source.source_type == SourceType.CLICKHOUSE:
                result = await self._load_clickhouse_data(source, limit)
            elif source.source_type == SourceType.HDFS:
                result = await self._load_hdfs_data(source, limit)
            else:
                raise ValueError(f"Unsupported source type: {source.source_type}")
            
            # Принудительная очистка памяти после загрузки
            gc.collect()
            
            logger.info(f"Loaded {len(result)} rows, {len(result.columns)} columns from {source.source_id}")
            return result
                
        except Exception as e:
            logger.error(f"Error loading data from source {source.source_id}: {str(e)}")
            # Очистка памяти даже при ошибке
            import gc
            gc.collect()
            raise
    
    async def _load_file_data(self, source: DataSource, limit: Optional[int]) -> pd.DataFrame:
        """Загрузка данных из файла с улучшенной поддержкой форматов."""
        file_path = Path(source.path)
        extension = file_path.suffix.lower()
        
        # Сначала пробуем использовать модуль 5 для автоопределения формата
        try:
            timeout = aiohttp.ClientTimeout(total=30)  # Таймаут 30 секунд
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.module5_base_url}/auto-detect",
                    params={"source": source.path}
                ) as response:
                    if response.status == 200:
                        detection_data = await response.json()
                        return await self._load_with_detection_data(source, limit, detection_data)
        except Exception as e:
            logger.warning(f"Module 5 auto-detection failed, using fallback: {str(e)}")
        
        # Fallback к улучшенному прямому чтению
        return await self._load_file_direct_improved(source, limit, extension)
    
    async def _load_with_detection_data(self, source: DataSource, limit: Optional[int], detection_data: Dict[str, Any]) -> pd.DataFrame:
        """Загрузка файла с использованием данных автоопределения модуля 5."""
        file_path = Path(source.path)
        
        try:
            if detection_data.get('file_type') == 'csv':
                # Используем определенный разделитель с потоковой обработкой
                separator = detection_data.get('separator', ',')
                encoding = detection_data.get('encoding', 'utf-8')
                logger.info(f"Using Module 5 detected CSV params: sep='{separator}', encoding='{encoding}'")
                df = await self._load_csv_streaming(source.path, separator, encoding, limit)
                
            elif detection_data.get('file_type') == 'json':
                # Используем потоковую обработку JSON
                logger.info("Using Module 5 detected JSON format with streaming")
                df = await self._load_json_robust(source.path, limit)
                    
            elif detection_data.get('file_type') == 'xml' or file_path.suffix.lower() == '.xml':
                # XML поддержка через модуль 5
                return await self._load_xml_via_module5(source, limit)
                
            elif detection_data.get('file_type') == 'parquet':
                df = pd.read_parquet(source.path)
                if limit:
                    df = df.head(limit)
            else:
                raise ValueError(f"Unsupported file type from detection: {detection_data.get('file_type')}")
            
            # Фильтруем колонки
            return self._filter_selected_columns(df, source)
            
        except Exception as e:
            logger.error(f"Failed to load with detection data: {str(e)}")
            # Fallback к прямому чтению
            extension = file_path.suffix.lower()
            return await self._load_file_direct_improved(source, limit, extension)
    
    async def _load_xml_via_module5(self, source: DataSource, limit: Optional[int]) -> pd.DataFrame:
        """Загрузка XML файла через модуль 5."""
        try:
            # Используем модуль 5 для обработки XML
            timeout = aiohttp.ClientTimeout(total=30)  # Таймаут 30 секунд
            async with aiohttp.ClientSession(timeout=timeout) as session:
                request_data = {
                    "source_path": source.path,
                    "source_type": "xml"
                }
                if limit:
                    request_data["limit_rows"] = limit
                
                async with session.post(
                    f"{self.module5_base_url}/collect",
                    json=request_data
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Преобразуем данные модуля 5 в DataFrame
                        if 'sample_data' in data and data['sample_data']:
                            df = pd.DataFrame(data['sample_data'])
                            # Фильтруем только выбранные колонки
                            available_columns = [col for col in source.selected_columns if col in df.columns]
                            if not available_columns:
                                # Если ни одна колонка не найдена, возвращаем все колонки
                                logger.warning(f"None of selected columns {source.selected_columns} found in data. Available columns: {list(df.columns)}")
                                result_df = df
                            else:
                                result_df = df[available_columns]
                            return self._filter_selected_columns(result_df, source)
                    
            raise ValueError("Failed to load XML via Module 5")
            
        except Exception as e:
            logger.error(f"XML loading via Module 5 failed: {str(e)}")
            raise ValueError(f"XML format not supported: {str(e)}")
    
    async def _load_file_direct_improved(self, source: DataSource, limit: Optional[int], extension: str) -> pd.DataFrame:
        """Улучшенное прямое чтение файла с проверенными методами обработки."""
        
        if extension == '.csv':
            df = await self._load_csv_robust(source.path, limit)
                
        elif extension == '.parquet':
            df = pd.read_parquet(source.path)
            if limit:
                df = df.head(limit)
                
        elif extension == '.json':
            df = await self._load_json_robust(source.path, limit)
                    
        elif extension == '.xml':
            df = await self._load_xml_robust(source.path, limit)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
        
        return self._filter_selected_columns(df, source)
    
    async def _load_csv_robust(self, file_path: str, limit: Optional[int]) -> pd.DataFrame:
        """Надежная потоковая загрузка CSV с автоопределением параметров."""
        
        # Пробуем разные комбинации разделителей и кодировок
        separators = [',', ';', '\t', '|']
        encodings = ['utf-8', 'latin-1', 'cp1251']
        
        for sep in separators:
            for encoding in encodings:
                try:
                    # Пробуем первые 10 строк для проверки
                    test_df = pd.read_csv(file_path, sep=sep, encoding=encoding, nrows=10)
                    if len(test_df.columns) > 1:  # Если получили больше одной колонку
                        logger.info(f"CSV format detected: sep='{sep}', encoding='{encoding}'")
                        # ПОТОКОВАЯ ОБРАБОТКА: читаем чанками
                        return await self._load_csv_streaming(file_path, sep, encoding, limit)
                except Exception:
                    continue
        
        # Если ничего не сработало, пробуем стандартные параметры потоково
        try:
            return await self._load_csv_streaming(file_path, ',', 'utf-8', limit)
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file with all attempted parameters: {str(e)}")
    
    async def _load_csv_streaming(self, file_path: str, sep: str, encoding: str, limit: Optional[int]) -> pd.DataFrame:
        """Потоковая загрузка CSV по чанкам для экономии памяти."""
        chunk_size = 1000  # Читаем по 1000 строк за раз
        chunks = []
        total_rows = 0
        
        try:
            # Читаем файл чанками
            for chunk in pd.read_csv(file_path, sep=sep, encoding=encoding, chunksize=chunk_size):
                chunks.append(chunk)
                total_rows += len(chunk)
                
                # Принудительная очистка памяти после каждого чанка
                import gc
                gc.collect()
                
                # Прерываем если достигли лимита
                if limit and total_rows >= limit:
                    logger.info(f"Reached limit {limit} rows, stopping CSV streaming")
                    break
                    
                # Защита от переполнения памяти - максимум 10 чанков за раз
                if len(chunks) >= 10:
                    # Объединяем накопленные чанки
                    partial_df = pd.concat(chunks, ignore_index=True)
                    chunks = [partial_df]  # Заменяем чанки объединенным DataFrame
                    gc.collect()
            
            # Объединяем все чанки в финальный DataFrame
            if chunks:
                df = pd.concat(chunks, ignore_index=True)
                
                # Применяем лимит если нужно
                if limit and len(df) > limit:
                    df = df.head(limit)
                
                logger.info(f"CSV streaming completed: {len(df)} rows loaded")
                return df
            else:
                raise ValueError("No data loaded from CSV file")
                
        except Exception as e:
            logger.error(f"CSV streaming failed: {str(e)}")
            raise
    
    async def _load_json_robust(self, file_path: str, limit: Optional[int]) -> pd.DataFrame:
        """Потоковая загрузка JSON с поддержкой разных форматов."""
        import json
        
        # Сначала пробуем определить формат JSON, читая только начало файла
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_chars = f.read(100).strip()
                
            # Если начинается с '[', это JSON массив
            if first_chars.startswith('['):
                logger.info("Detected JSON array format, using streaming parser")
                return await self._load_json_array_streaming(file_path, limit)
            # Иначе пробуем JSON Lines
            else:
                logger.info("Detected JSON Lines format, using streaming parser")
                return await self._load_json_lines_streaming(file_path, limit)
                
        except Exception as e:
            logger.warning(f"JSON format detection failed: {str(e)}, trying fallback")
            # Fallback к pandas с ограничениями
            return await self._load_json_pandas_fallback(file_path, limit)
    
    async def _load_json_array_streaming(self, file_path: str, limit: Optional[int]) -> pd.DataFrame:
        """Потоковая обработка JSON массива без загрузки всего файла в память."""
        import json
        
        records = []
        bracket_count = 0
        current_object = ""
        object_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    for char in line:
                        current_object += char
                        
                        if char == '{':
                            bracket_count += 1
                        elif char == '}':
                            bracket_count -= 1
                            
                            # Если закрыли объект, пробуем его парсить
                            if bracket_count == 0 and current_object.strip().endswith('}'):
                                try:
                                    # Очищаем от лишних символов
                                    clean_object = current_object.strip().rstrip(',').strip()
                                    if clean_object.startswith('{') and clean_object.endswith('}'):
                                        obj = json.loads(clean_object)
                                        records.append(obj)
                                        object_count += 1
                                        
                                        # Очистка памяти каждые 100 объектов
                                        if object_count % 100 == 0:
                                            import gc
                                            gc.collect()
                                        
                                        # Проверяем лимит
                                        if limit and object_count >= limit:
                                            break
                                            
                                except json.JSONDecodeError:
                                    pass
                                
                                current_object = ""
                    
                    # Прерываем внешний цикл если достигли лимита
                    if limit and object_count >= limit:
                        break
            
            if records:
                df = pd.DataFrame(records)
                logger.info(f"JSON array streaming completed: {len(df)} records loaded")
                return df
            else:
                raise ValueError("No valid JSON objects found in array")
                
        except Exception as e:
            logger.error(f"JSON array streaming failed: {str(e)}")
            raise
    
    async def _load_json_lines_streaming(self, file_path: str, limit: Optional[int]) -> pd.DataFrame:
        """Потоковая обработка JSON Lines построчно."""
        import json
        
        records = []
        line_count = 0
        max_lines_to_process = limit * 2 if limit else 1000  # Ограничиваем количество строк для обработки
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    # Защита от бесконечного чтения
                    if i >= max_lines_to_process:
                        logger.warning(f"Reached max lines limit {max_lines_to_process}, stopping JSON Lines streaming")
                        break
                    
                    line = line.strip()
                    if line:
                        try:
                            obj = json.loads(line)
                            records.append(obj)
                            line_count += 1
                            
                            # Очистка памяти каждые 100 записей
                            if line_count % 100 == 0:
                                import gc
                                gc.collect()
                            
                            # Проверяем лимит
                            if limit and line_count >= limit:
                                break
                                
                        except json.JSONDecodeError:
                            continue
            
            if records:
                df = pd.DataFrame(records)
                logger.info(f"JSON Lines streaming completed: {len(df)} records loaded")
                return df
            else:
                raise ValueError("No valid JSON objects found in lines")
                
        except Exception as e:
            logger.error(f"JSON Lines streaming failed: {str(e)}")
            raise
    
    async def _load_json_pandas_fallback(self, file_path: str, limit: Optional[int]) -> pd.DataFrame:
        """Fallback к pandas с ограничениями памяти."""
        try:
            # Пробуем JSON Lines с pandas
            if limit:
                df = pd.read_json(file_path, lines=True, nrows=limit)
            else:
                df = pd.read_json(file_path, lines=True)
            logger.info("JSON loaded using pandas read_json with lines=True (fallback)")
            return df
        except Exception:
            try:
                # Пробуем обычный JSON с pandas (nrows не поддерживается для обычного JSON)
                df = pd.read_json(file_path)
                if limit:
                    df = df.head(limit)
                logger.info("JSON loaded using pandas read_json (fallback)")
                return df
            except Exception as final_e:
                raise ValueError(f"Failed to parse JSON file with all methods: {str(final_e)}")
    
    async def _load_xml_robust(self, file_path: str, limit: Optional[int]) -> pd.DataFrame:
        """Потоковая загрузка XML с минимальным использованием памяти."""
        
        # Сначала пробуем потоковый парсинг
        try:
            logger.info("Attempting XML streaming parse")
            return await self._load_xml_streaming(file_path, limit)
        except Exception as e:
            logger.warning(f"XML streaming failed: {str(e)}, trying Module 5 fallback")
            return await self._load_xml_via_module5_fallback(file_path, limit)
    
    async def _load_xml_streaming(self, file_path: str, limit: Optional[int]) -> pd.DataFrame:
        """Потоковая обработка XML с использованием iterparse для экономии памяти."""
        import xml.etree.ElementTree as ET
        
        records = []
        count = 0
        max_records_to_process = limit * 2 if limit else 1000  # Ограничиваем обработку
        
        try:
            # Используем iterparse для потоковой обработки
            context = ET.iterparse(file_path, events=('start', 'end'))
            context = iter(context)
            event, root = next(context)
            
            current_record = {}
            record_tag = None
            inside_record = False
            
            for event, elem in context:
                # Защита от переполнения памяти
                if count >= max_records_to_process:
                    logger.warning(f"Reached max records limit {max_records_to_process}, stopping XML streaming")
                    break
                
                if event == 'start':
                    # Определяем тег записи (первый дочерний элемент корня)
                    if record_tag is None and elem != root:
                        record_tag = elem.tag
                        inside_record = True
                        current_record = {}
                    elif elem.tag == record_tag:
                        inside_record = True
                        current_record = {}
                
                elif event == 'end':
                    if elem.tag == record_tag and inside_record:
                        # Завершили запись
                        for child in elem:
                            if child.text:
                                current_record[child.tag] = child.text.strip()
                        
                        if current_record:
                            records.append(current_record.copy())
                            count += 1
                            
                            # Очистка памяти каждые 100 записей
                            if count % 100 == 0:
                                import gc
                                gc.collect()
                            
                            # Проверяем лимит
                            if limit and count >= limit:
                                break
                        
                        inside_record = False
                        current_record = {}
                        
                        # Очищаем элемент для экономии памяти
                        elem.clear()
                        # Очищаем родительские ссылки (если доступно)
                        try:
                            if hasattr(elem, 'getprevious') and elem.getprevious() is not None:
                                parent = elem.getparent() if hasattr(elem, 'getparent') else None
                                if parent is not None:
                                    parent.remove(elem.getprevious())
                        except:
                            pass  # Игнорируем ошибки очистки
            
            if records:
                df = pd.DataFrame(records)
                logger.info(f"XML streaming completed: {len(df)} records loaded")
                return df
            else:
                # Если потоковый парсинг не нашел записей, пробуем простую структуру
                return await self._load_xml_simple_structure(file_path, limit)
                
        except Exception as e:
            logger.error(f"XML streaming failed: {str(e)}")
            # Fallback к простой структуре
            return await self._load_xml_simple_structure(file_path, limit)
    
    async def _load_xml_simple_structure(self, file_path: str, limit: Optional[int]) -> pd.DataFrame:
        """Обработка XML с простой структурой (плоский XML)."""
        import xml.etree.ElementTree as ET
        
        try:
            # Читаем только начало файла для определения структуры
            with open(file_path, 'r', encoding='utf-8') as f:
                sample = f.read(10000)  # Читаем первые 10KB
            
            # Парсим образец
            sample_root = ET.fromstring(sample + '</root>' if not sample.strip().endswith('>') else sample)
            
            records = []
            
            # Если корневой элемент содержит прямые текстовые дочерние элементы
            if len(list(sample_root)) > 0:
                record_data = {}
                for child in sample_root:
                    if child.text:
                        record_data[child.tag] = child.text.strip()
                
                if record_data:
                    records.append(record_data)
            
            if records:
                df = pd.DataFrame(records)
                logger.info(f"XML simple structure loaded: {len(df)} records")
                return df
            else:
                raise ValueError("No records found in XML simple structure")
                
        except Exception as e:
            logger.error(f"XML simple structure parsing failed: {str(e)}")
            raise
    
    async def _load_xml_via_module5_fallback(self, file_path: str, limit: Optional[int]) -> pd.DataFrame:
        """Fallback загрузка XML через модуль 5."""
        try:
            # Создаем временный DataSource для вызова модуля 5
            temp_source = DataSource(
                source_id="temp_xml",
                source_type=SourceType.FILE,
                path=file_path,
                selected_columns=[]
            )
            return await self._load_xml_via_module5(temp_source, limit)
        except Exception as e:
            raise ValueError(f"XML format not supported and Module 5 fallback failed: {str(e)}")
    
    def _filter_selected_columns(self, df: pd.DataFrame, source: DataSource) -> pd.DataFrame:
        """Фильтрует DataFrame по выбранным колонкам."""
        # Если не указаны конкретные колонки, возвращаем все
        if not source.selected_columns:
            result_df = df
        else:
            # Фильтруем только выбранные колонки
            available_columns = [col for col in source.selected_columns if col in df.columns]
            if not available_columns:
                # Если ни одна колонка не найдена, возвращаем все колонки
                logger.warning(f"None of selected columns {source.selected_columns} found in data. Available columns: {list(df.columns)}")
                result_df = df
            else:
                result_df = df[available_columns]
        
        # Конвертируем numpy типы в стандартные Python типы для совместимости с Pydantic
        return self._convert_numpy_types(result_df)
    
    def _convert_numpy_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Конвертирует numpy типы в стандартные Python типы для совместимости с Pydantic."""
        import numpy as np
        
        # Создаем копию DataFrame
        df_converted = df.copy()
        
        for col in df_converted.columns:
            dtype = str(df_converted[col].dtype)
            
            # Конвертируем числовые типы
            if dtype in ['int64', 'Int64']:
                # Обрабатываем NaN значения
                df_converted[col] = df_converted[col].fillna(0).astype('int32')
            elif dtype in ['float64', 'Float64']:
                df_converted[col] = df_converted[col].astype('float32')
            elif dtype in ['int32', 'Int32']:
                df_converted[col] = df_converted[col].fillna(0).astype('int32')
            elif dtype in ['float32', 'Float32']:
                df_converted[col] = df_converted[col].astype('float32')
            elif dtype == 'object':
                # Конвертируем object в string, обрабатывая None значения
                df_converted[col] = df_converted[col].fillna('').astype(str)
            elif dtype.startswith('datetime'):
                # Конвертируем datetime в string для JSON сериализации
                df_converted[col] = df_converted[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
            elif dtype == 'bool':
                # Булевы значения оставляем как есть, но обрабатываем NaN
                df_converted[col] = df_converted[col].fillna(False)
            elif dtype.startswith('category'):
                # Категориальные данные конвертируем в строки
                df_converted[col] = df_converted[col].astype(str)
        
        # Дополнительная проверка и очистка данных
        df_converted = self._clean_dataframe_for_serialization(df_converted)
        
        return df_converted
    
    def _clean_dataframe_for_serialization(self, df: pd.DataFrame) -> pd.DataFrame:
        """Дополнительная очистка DataFrame для JSON сериализации."""
        import numpy as np
        
        # Заменяем все NaN, inf, -inf на None или подходящие значения
        df_clean = df.copy()
        
        for col in df_clean.columns:
            # Заменяем numpy NaN на None для числовых колонок
            if df_clean[col].dtype in ['float32', 'float64']:
                df_clean[col] = df_clean[col].replace([np.inf, -np.inf], None)
                df_clean[col] = df_clean[col].where(pd.notna(df_clean[col]), None)
            elif df_clean[col].dtype in ['int32', 'int64']:
                df_clean[col] = df_clean[col].where(pd.notna(df_clean[col]), 0)
            else:
                # Для строковых колонок заменяем NaN на пустую строку
                df_clean[col] = df_clean[col].where(pd.notna(df_clean[col]), '')
        
        return df_clean
    
    async def _load_postgresql_data(self, source: DataSource, limit: Optional[int]) -> pd.DataFrame:
        """Загрузка данных из PostgreSQL."""
        engine = create_engine(source.connection)
        
        query = f"SELECT {', '.join(source.selected_columns)} FROM {source.table}"
        
        # Добавляем фильтры если есть
        if source.filters:
            conditions = []
            for key, value in source.filters.items():
                if isinstance(value, str):
                    conditions.append(f"{key} = '{value}'")
                else:
                    conditions.append(f"{key} = {value}")
            if conditions:
                query += f" WHERE {' AND '.join(conditions)}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return pd.read_sql(query, engine)
    
    async def _load_clickhouse_data(self, source: DataSource, limit: Optional[int]) -> pd.DataFrame:
        """Загрузка данных из ClickHouse."""
        parsed = urlparse(source.connection)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        query = f"SELECT {', '.join(source.selected_columns)} FROM {source.table}"
        
        # Добавляем фильтры если есть
        if source.filters:
            conditions = []
            for key, value in source.filters.items():
                if isinstance(value, str):
                    conditions.append(f"{key} = '{value}'")
                else:
                    conditions.append(f"{key} = {value}")
            if conditions:
                query += f" WHERE {' AND '.join(conditions)}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                base_url,
                params={'query': query},
                headers={'X-ClickHouse-Format': 'JSON'}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return pd.DataFrame(data.get('data', []))
                else:
                    raise Exception(f"ClickHouse query failed: {response.status}")
    
    async def _load_hdfs_data(self, source: DataSource, limit: Optional[int]) -> pd.DataFrame:
        """Загрузка данных из HDFS."""
        # Заглушка для HDFS - требует дополнительной реализации
        raise NotImplementedError("HDFS data loading not implemented yet")
    
    def validate_source_compatibility(self, sources: List[DataSource]) -> List[str]:
        """
        Проверяет совместимость источников данных для JOIN операций.
        
        Args:
            sources: Список источников данных
            
        Returns:
            List[str]: Список проблем совместимости
        """
        issues = []
        
        # Проверяем, что есть хотя бы один источник
        if not sources:
            issues.append("No data sources provided")
            return issues
        
        # Для каждой пары источников проверяем совместимость
        for i, source1 in enumerate(sources):
            for j, source2 in enumerate(sources[i+1:], i+1):
                # Проверяем пересечение колонок для потенциальных JOIN
                common_columns = set(source1.selected_columns) & set(source2.selected_columns)
                if not common_columns:
                    issues.append(
                        f"Sources {source1.source_id} and {source2.source_id} "
                        f"have no common columns for JOIN"
                    )
        
        return issues
