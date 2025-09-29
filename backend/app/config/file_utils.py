"""
Утилиты для работы с файлами с контролем максимального размера.
Автоматическое разделение файлов на части по 500MB.
"""

import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Any, Iterator, Tuple
import os
from lxml import etree
import sqlite3

from .paths import DataPaths

class FileSplitter:
    """Класс для разделения больших файлов на части."""
    
    def __init__(self, max_size_mb: int = 500):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def split_csv(self, source_path: Path, database_name: str, source_id: str, 
                  stage: str) -> List[Path]:
        """Алиас для split_csv_file для совместимости с тестами."""
        return self.split_csv_file(source_path, database_name, source_id, stage)
    
    def split_json(self, source_path: Path, database_name: str, source_id: str, 
                   stage: str) -> List[Path]:
        """Алиас для split_json_file для совместимости с тестами."""
        return self.split_json_file(source_path, database_name, source_id, stage)
    
    def split_xml(self, source_path: Path, database_name: str, source_id: str, 
                  stage: str) -> List[Path]:
        """Алиас для split_xml_file для совместимости с тестами."""
        return self.split_xml_file(source_path, database_name, source_id, stage)
    
    def split_csv_file(self, source_path: Path, database_name: str, source_id: str, 
                      stage: str) -> List[Path]:
        """
        Разделить CSV файл на части с контролем размера.
        
        Args:
            source_path: Путь к исходному файлу
            database_name: Имя базы данных
            source_id: Идентификатор источника
            stage: Этап обработки
        
        Returns:
            Список путей к созданным частям
        """
        # Проверяем размер исходного файла
        file_size = source_path.stat().st_size
        if file_size <= self.max_size_bytes:
            # Файл не требует разделения
            target_path = DataPaths.get_source_path(database_name, source_id, stage)
            target_path.mkdir(parents=True, exist_ok=True)
            
            final_path = target_path / f"{source_id}.parquet"
            
            # Конвертируем в Parquet для оптимизации
            df = pd.read_csv(source_path)
            df.to_parquet(final_path, index=False)
            
            # Регистрируем в метаданных
            actual_size_mb = final_path.stat().st_size / (1024 * 1024)
            DataPaths.register_file_part(source_id, database_name, stage, 1, 
                                       final_path, actual_size_mb)
            
            return [final_path]
        
        # Файл требует разделения
        return self._split_large_csv(source_path, database_name, source_id, stage)
    
    def _split_large_csv(self, source_path: Path, database_name: str, 
                        source_id: str, stage: str) -> List[Path]:
        """Разделить большой CSV файл на части."""
        target_dir = DataPaths.get_source_path(database_name, source_id, stage)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Читаем CSV по частям
        chunk_size = self._estimate_csv_chunk_size(source_path)
        part_paths = []
        part_number = 1
        
        for chunk in pd.read_csv(source_path, chunksize=chunk_size):
            part_path = target_dir / f"{source_id}_part_{part_number:03d}.parquet"
            
            # Сохраняем часть в Parquet
            chunk.to_parquet(part_path, index=False)
            
            # Проверяем размер
            actual_size_mb = part_path.stat().st_size / (1024 * 1024)
            
            # Регистрируем в метаданных
            DataPaths.register_file_part(source_id, database_name, stage, 
                                       part_number, part_path, actual_size_mb)
            
            part_paths.append(part_path)
            part_number += 1
            
            # Если часть все еще слишком большая, разделяем дальше
            if actual_size_mb > self.max_size_mb:
                part_paths.extend(self._split_parquet_further(part_path, database_name, 
                                                            source_id, stage, part_number))
        
        return part_paths
    
    def _estimate_csv_chunk_size(self, csv_path: Path) -> int:
        """Оценить размер чанка для CSV файла."""
        # Читаем первые 1000 строк для оценки
        sample_df = pd.read_csv(csv_path, nrows=1000)
        
        # Оценка размера одной строки в байтах
        sample_size = sample_df.memory_usage(deep=True).sum()
        bytes_per_row = sample_size / len(sample_df)
        
        # Рассчитываем количество строк для максимального размера
        target_rows = int(self.max_size_bytes / bytes_per_row * 0.8)  # 80% от лимита для безопасности
        
        return max(1000, target_rows)  # Минимум 1000 строк
    
    def split_json_file(self, source_path: Path, database_name: str, source_id: str, 
                       stage: str) -> List[Path]:
        """Разделить JSON файл на части."""
        file_size = source_path.stat().st_size
        if file_size <= self.max_size_bytes:
            return self._convert_single_json(source_path, database_name, source_id, stage)
        
        return self._split_large_json(source_path, database_name, source_id, stage)
    
    def _convert_single_json(self, source_path: Path, database_name: str, 
                           source_id: str, stage: str) -> List[Path]:
        """Конвертировать JSON в Parquet без разделения."""
        target_path = DataPaths.get_source_path(database_name, source_id, stage)
        target_path.mkdir(parents=True, exist_ok=True)
        
        final_path = target_path / f"{source_id}.parquet"
        
        # Читаем JSON и конвертируем в DataFrame
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame([data])
        
        # Сохраняем в Parquet
        df.to_parquet(final_path, index=False)
        
        # Регистрируем в метаданных
        actual_size_mb = final_path.stat().st_size / (1024 * 1024)
        DataPaths.register_file_part(source_id, database_name, stage, 1, 
                                   final_path, actual_size_mb)
        
        return [final_path]
    
    def _split_large_json(self, source_path: Path, database_name: str, 
                         source_id: str, stage: str) -> List[Path]:
        """Разделить большой JSON файл на части."""
        target_dir = DataPaths.get_source_path(database_name, source_id, stage)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        part_paths = []
        part_number = 1
        current_batch = []
        current_size = 0
        
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            data = [data]
        
        for item in data:
            item_size = len(json.dumps(item, ensure_ascii=False).encode('utf-8'))
            
            if current_size + item_size > self.max_size_bytes and current_batch:
                # Сохраняем текущую часть
                part_path = self._save_json_part(current_batch, target_dir, source_id, 
                                               part_number, database_name, stage)
                part_paths.append(part_path)
                
                # Начинаем новую часть
                current_batch = [item]
                current_size = item_size
                part_number += 1
            else:
                current_batch.append(item)
                current_size += item_size
        
        # Сохраняем последнюю часть
        if current_batch:
            part_path = self._save_json_part(current_batch, target_dir, source_id, 
                                           part_number, database_name, stage)
            part_paths.append(part_path)
        
        return part_paths
    
    def _save_json_part(self, data: List[Dict], target_dir: Path, source_id: str, 
                       part_number: int, database_name: str, stage: str) -> Path:
        """Сохранить часть JSON данных в Parquet."""
        part_path = target_dir / f"{source_id}_part_{part_number:03d}.parquet"
        
        df = pd.DataFrame(data)
        df.to_parquet(part_path, index=False)
        
        # Регистрируем в метаданных
        actual_size_mb = part_path.stat().st_size / (1024 * 1024)
        DataPaths.register_file_part(source_id, database_name, stage, 
                                   part_number, part_path, actual_size_mb)
        
        return part_path
    
    def split_xml_file(self, source_path: Path, database_name: str, source_id: str, 
                      stage: str) -> List[Path]:
        """Разделить XML файл на части."""
        file_size = source_path.stat().st_size
        if file_size <= self.max_size_bytes:
            return self._convert_single_xml(source_path, database_name, source_id, stage)
        
        return self._split_large_xml(source_path, database_name, source_id, stage)
    
    def _convert_single_xml(self, source_path: Path, database_name: str, 
                          source_id: str, stage: str) -> List[Path]:
        """Конвертировать XML в Parquet без разделения."""
        target_path = DataPaths.get_source_path(database_name, source_id, stage)
        target_path.mkdir(parents=True, exist_ok=True)
        
        final_path = target_path / f"{source_id}.parquet"
        
        # Парсим XML и конвертируем в DataFrame
        data = self._parse_xml_to_records(source_path)
        df = pd.DataFrame(data)
        
        # Сохраняем в Parquet
        df.to_parquet(final_path, index=False)
        
        # Регистрируем в метаданных
        actual_size_mb = final_path.stat().st_size / (1024 * 1024)
        DataPaths.register_file_part(source_id, database_name, stage, 1, 
                                   final_path, actual_size_mb)
        
        return [final_path]
    
    def _split_large_xml(self, source_path: Path, database_name: str, 
                        source_id: str, stage: str) -> List[Path]:
        """Разделить большой XML файл на части."""
        target_dir = DataPaths.get_source_path(database_name, source_id, stage)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        part_paths = []
        part_number = 1
        current_batch = []
        current_size = 0
        
        # Определяем тег записи
        record_tag = self._detect_xml_record_tag(source_path)
        
        # Парсим XML по частям
        context = etree.iterparse(source_path, events=('end',), tag=record_tag)
        
        for event, elem in context:
            # Конвертируем элемент в словарь
            record = self._xml_element_to_dict(elem)
            record_size = len(str(record).encode('utf-8'))
            
            if current_size + record_size > self.max_size_bytes and current_batch:
                # Сохраняем текущую часть
                part_path = self._save_xml_part(current_batch, target_dir, source_id, 
                                              part_number, database_name, stage)
                part_paths.append(part_path)
                
                # Начинаем новую часть
                current_batch = [record]
                current_size = record_size
                part_number += 1
            else:
                current_batch.append(record)
                current_size += record_size
            
            # Очищаем память
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        
        # Сохраняем последнюю часть
        if current_batch:
            part_path = self._save_xml_part(current_batch, target_dir, source_id, 
                                          part_number, database_name, stage)
            part_paths.append(part_path)
        
        return part_paths
    
    def _parse_xml_to_records(self, xml_path: Path) -> List[Dict]:
        """Парсить XML файл в список записей."""
        records = []
        record_tag = self._detect_xml_record_tag(xml_path)
        
        context = etree.iterparse(xml_path, events=('end',), tag=record_tag)
        
        for event, elem in context:
            record = self._xml_element_to_dict(elem)
            records.append(record)
            
            # Очищаем память
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        
        return records
    
    def _detect_xml_record_tag(self, xml_path: Path) -> str:
        """Определить тег записи в XML файле."""
        common_tags = ['item', 'record', 'row', 'entry', 'data', 'object', 'order', 'transaction']
        
        # Читаем начало файла для анализа
        with open(xml_path, 'rb') as f:
            sample = f.read(10000).decode('utf-8', errors='ignore')
        
        for tag in common_tags:
            if f'<{tag}' in sample and f'</{tag}>' in sample:
                return tag
        
        # Если не найден стандартный тег, берем первый повторяющийся
        try:
            tree = etree.parse(xml_path)
            root = tree.getroot()
            if len(root) > 0:
                return root[0].tag
        except:
            pass
        
        return 'item'  # Fallback
    
    def _xml_element_to_dict(self, element) -> Dict:
        """Конвертировать XML элемент в словарь."""
        result = {}
        
        # Атрибуты
        if element.attrib:
            result.update(element.attrib)
        
        # Текст элемента
        if element.text and element.text.strip():
            if len(element) == 0:  # Листовой элемент
                result['text'] = element.text.strip()
            else:
                result['_text'] = element.text.strip()
        
        # Дочерние элементы
        for child in element:
            child_data = self._xml_element_to_dict(child)
            
            if child.tag in result:
                # Если тег уже существует, создаем список
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    def _save_xml_part(self, data: List[Dict], target_dir: Path, source_id: str, 
                      part_number: int, database_name: str, stage: str) -> Path:
        """Сохранить часть XML данных в Parquet."""
        part_path = target_dir / f"{source_id}_part_{part_number:03d}.parquet"
        
        df = pd.DataFrame(data)
        df.to_parquet(part_path, index=False)
        
        # Регистрируем в метаданных
        actual_size_mb = part_path.stat().st_size / (1024 * 1024)
        DataPaths.register_file_part(source_id, database_name, stage, 
                                   part_number, part_path, actual_size_mb)
        
        return part_path

class FileManager:
    """Менеджер для работы с файлами в новой структуре."""
    
    def __init__(self):
        self.splitter = FileSplitter()
    
    def process_file(self, source_path: Path, database_name: str, source_id: str, 
                    stage: str) -> List[Path]:
        """
        Обработать файл с автоматическим разделением при необходимости.
        
        Args:
            source_path: Путь к исходному файлу
            database_name: Имя базы данных
            source_id: Идентификатор источника
            stage: Этап обработки
        
        Returns:
            Список путей к обработанным файлам
        """
        file_ext = source_path.suffix.lower()
        
        if file_ext == '.csv':
            return self.splitter.split_csv_file(source_path, database_name, source_id, stage)
        elif file_ext in ['.json', '.jsonl']:
            return self.splitter.split_json_file(source_path, database_name, source_id, stage)
        elif file_ext == '.xml':
            return self.splitter.split_xml_file(source_path, database_name, source_id, stage)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
    
    def get_file_parts(self, source_id: str, database_name: str, stage: str) -> List[Path]:
        """Получить все части файла."""
        conn = sqlite3.connect(DataPaths.MAIN_METADATA_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT file_path FROM file_parts 
        WHERE source_id = ? AND database_name = ? AND stage = ?
        ORDER BY part_number
        """, (source_id, database_name, stage))
        
        paths = [Path(row[0]) for row in cursor.fetchall()]
        conn.close()
        
        return paths
    
    def combine_file_parts(self, source_id: str, database_name: str, stage: str) -> pd.DataFrame:
        """Объединить все части файла в один DataFrame."""
        parts = self.get_file_parts(source_id, database_name, stage)
        
        if not parts:
            raise ValueError(f"No parts found for {source_id} in {database_name}/{stage}")
        
        # Читаем и объединяем все части
        dataframes = []
        for part_path in parts:
            if part_path.exists():
                df = pd.read_parquet(part_path)
                dataframes.append(df)
        
        if not dataframes:
            raise ValueError(f"No valid parts found for {source_id}")
        
        return pd.concat(dataframes, ignore_index=True)
    
    def register_artifact(self, artifact_type: str, artifact_path: Path, 
                         source_id: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Регистрировать артефакт в системе метаданных.
        
        Args:
            artifact_type: Тип артефакта (ddl, dag, report, etc.)
            artifact_path: Путь к артефакту
            source_id: Идентификатор источника
            metadata: Дополнительные метаданные
        
        Returns:
            True если регистрация успешна
        """
        try:
            conn = sqlite3.connect(DataPaths.MAIN_METADATA_DB)
            cursor = conn.cursor()
            
            # Создаем таблицу artifacts если не существует
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifact_type TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                source_id TEXT NOT NULL,
                file_size_bytes INTEGER,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Проверяем существование колонки artifact_type (для совместимости со старыми БД)
            cursor.execute("PRAGMA table_info(artifacts)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'artifact_type' not in columns:
                # Если старая структура, пересоздаем таблицу
                cursor.execute("DROP TABLE IF EXISTS artifacts")
                cursor.execute("""
                CREATE TABLE artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    artifact_type TEXT NOT NULL,
                    artifact_path TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    file_size_bytes INTEGER,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
            
            # Получаем размер файла
            file_size = artifact_path.stat().st_size if artifact_path.exists() else 0
            
            # Конвертируем метаданные в JSON
            metadata_json = json.dumps(metadata) if metadata else None
            
            # Вставляем запись
            cursor.execute("""
            INSERT INTO artifacts (artifact_type, artifact_path, source_id, file_size_bytes, metadata)
            VALUES (?, ?, ?, ?, ?)
            """, (artifact_type, str(artifact_path), source_id, file_size, metadata_json))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"Error registering artifact: {e}")
            return False
    
    def cleanup_temp_files(self):
        """Очистить временные файлы."""
        DataPaths.cleanup_temp_files()
    
    # Алиасы для методов разделения файлов (для обратной совместимости)
    def split_csv(self, source_path: Path, database_name: str, source_id: str, stage: str) -> List[Path]:
        """Алиас для split_csv_file."""
        return self.split_csv_file(source_path, database_name, source_id, stage)
    
    def split_json(self, source_path: Path, database_name: str, source_id: str, stage: str) -> List[Path]:
        """Алиас для split_json_file."""
        return self.split_json_file(source_path, database_name, source_id, stage)
    
    def split_xml(self, source_path: Path, database_name: str, source_id: str, stage: str) -> List[Path]:
        """Алиас для split_xml_file."""
        return self.split_xml_file(source_path, database_name, source_id, stage)

# Глобальный экземпляр менеджера файлов
file_manager = FileManager()
