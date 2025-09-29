"""
Централизованное управление путями к данным с поддержкой разделения по базам данных
и контролем размера файлов.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import sqlite3
import json
from datetime import datetime

class DataPaths:
    """Централизованное управление путями к данным."""
    
    # Базовые пути (используем data_landing_zone)
    BASE_DATA_DIR = Path(os.getenv("DATA_BASE_DIR", "data_landing_zone"))
    
    # 1. Сырые данные
    RAW_DATA_DIR = BASE_DATA_DIR / "raw"
    RAW_UPLOADS = RAW_DATA_DIR / "uploads"
    RAW_EXTERNAL = RAW_DATA_DIR / "external"
    RAW_SYNTHETIC = RAW_DATA_DIR / "synthetic"  # Существующие syn_csv, syn_json, syn_xml
    RAW_STAGING = RAW_DATA_DIR / "staging"
    
    # 2. Промежуточные данные (по базам данных)
    INTERMEDIATE_DIR = BASE_DATA_DIR / "intermediate"
    
    # 3. Целевые хранилища (по базам данных)
    WAREHOUSES_DIR = BASE_DATA_DIR / "warehouses"
    
    # 4. Централизованные метаданные
    METADATA_DIR = BASE_DATA_DIR / "metadata"
    MAIN_METADATA_DB = METADATA_DIR / "main.db"
    
    # Временные файлы (автоудаление)
    TEMP_DIR = BASE_DATA_DIR / "_temp"
    
    # Максимальный размер файла в MB
    MAX_FILE_SIZE_MB = 500
    
    @classmethod
    def get_database_intermediate_path(cls, database_name: str, stage: str) -> Path:
        """
        Получить путь для промежуточных данных конкретной базы данных.
        
        Args:
            database_name: Имя целевой базы данных
            stage: Этап обработки (validated, cleaned, aggregated, optimized)
        """
        return cls.INTERMEDIATE_DIR / database_name / stage
    
    @classmethod
    def get_source_path(cls, database_name: str, source_id: str, stage: str) -> Path:
        """
        Получить путь для источника данных в конкретной базе и на конкретном этапе.
        
        Args:
            database_name: Имя целевой базы данных
            source_id: Идентификатор источника
            stage: Этап обработки
        """
        if stage == "raw":
            return cls.RAW_UPLOADS / source_id
        else:
            return cls.get_database_intermediate_path(database_name, stage) / source_id
    
    @classmethod
    def get_warehouse_path(cls, database_name: str, warehouse_id: str, db_type: str) -> Path:
        """
        Получить путь для хранилища в конкретной базе данных.
        
        Args:
            database_name: Имя базы данных
            warehouse_id: Идентификатор хранилища
            db_type: Тип БД (postgresql, clickhouse, hdfs)
        """
        return cls.WAREHOUSES_DIR / database_name / db_type / warehouse_id
    
    @classmethod
    def get_file_parts_paths(cls, database_name: str, source_id: str, stage: str, 
                           total_size_mb: float) -> List[Path]:
        """
        Получить список путей для частей файла с учетом максимального размера.
        
        Args:
            database_name: Имя базы данных
            source_id: Идентификатор источника
            stage: Этап обработки
            total_size_mb: Общий размер данных в MB
        
        Returns:
            Список путей для частей файла
        """
        base_path = cls.get_source_path(database_name, source_id, stage)
        
        if total_size_mb <= cls.MAX_FILE_SIZE_MB:
            # Один файл
            return [base_path / f"{source_id}.parquet"]
        
        # Несколько частей
        parts_count = int(total_size_mb / cls.MAX_FILE_SIZE_MB) + 1
        return [
            base_path / f"{source_id}_part_{i:03d}.parquet"
            for i in range(1, parts_count + 1)
        ]
    
    @classmethod
    def get_metadata_db_path(cls, database_name: str, stage: str) -> Path:
        """Получить путь к локальной SQLite базе метаданных для конкретного этапа."""
        return cls.get_database_intermediate_path(database_name, stage) / "metadata.db"
    
    @classmethod
    def get_metadata_path(cls, metadata_type: str, item_id: str) -> Path:
        """
        Получить путь для метаданных конкретного типа и элемента.
        
        Args:
            metadata_type: Тип метаданных (source, process, schema, artifact, etc.)
            item_id: Идентификатор элемента
        
        Returns:
            Путь к файлу метаданных
        """
        if metadata_type == "source":
            return cls.METADATA_DIR / "sources" / f"{item_id}.json"
        elif metadata_type == "process":
            return cls.METADATA_DIR / "processes" / f"{item_id}.json"
        elif metadata_type == "schema":
            return cls.METADATA_DIR / "schemas" / f"{item_id}_schema.json"
        elif metadata_type == "artifact":
            return cls.METADATA_DIR / "artifacts" / item_id
        elif metadata_type == "warehouse":
            return cls.METADATA_DIR / "warehouses" / f"{item_id}.json"
        elif metadata_type == "system":
            return cls.METADATA_DIR / "system" / f"{item_id}.json"
        else:
            # Общий путь для любых других типов
            return cls.METADATA_DIR / metadata_type / f"{item_id}.json"
    
    @classmethod
    def get_temp_path(cls, process_id: str) -> Path:
        """Получить путь для временных файлов процесса."""
        return cls.TEMP_DIR / process_id
    
    @classmethod
    def get_raw_data_path(cls) -> Path:
        """Получить путь к сырым данным."""
        return cls.RAW_DATA_DIR
    
    @classmethod
    def get_intermediate_path(cls) -> Path:
        """Получить путь к промежуточным данным."""
        return cls.INTERMEDIATE_DIR
    
    @classmethod
    def get_warehouses_path(cls) -> Path:
        """Получить путь к хранилищам."""
        return cls.WAREHOUSES_DIR
    
    @classmethod
    def get_database_path(cls, database_name: str, stage: str) -> Path:
        """Получить путь для базы данных и этапа."""
        return cls.get_database_intermediate_path(database_name, stage)
    
    @classmethod
    def get_warehouse_path(cls, database_name: str) -> Path:
        """Получить путь к хранилищу базы данных."""
        return cls.WAREHOUSES_DIR / database_name
    
    @classmethod
    def ensure_directories(cls, database_name: Optional[str] = None):
        """
        Создать все необходимые директории.
        
        Args:
            database_name: Если указано, создает структуру для конкретной БД
        """
        # Базовые директории
        base_directories = [
            cls.RAW_UPLOADS, cls.RAW_EXTERNAL, cls.RAW_SYNTHETIC, cls.RAW_STAGING,
            cls.METADATA_DIR, cls.TEMP_DIR
        ]
        
        for directory in base_directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Директории для конкретной базы данных
        if database_name:
            db_directories = [
                cls.get_database_intermediate_path(database_name, "validated"),
                cls.get_database_intermediate_path(database_name, "cleaned"),
                cls.get_database_intermediate_path(database_name, "aggregated"),
                cls.get_database_intermediate_path(database_name, "optimized"),
                cls.WAREHOUSES_DIR / database_name / "postgresql",
                cls.WAREHOUSES_DIR / database_name / "clickhouse",
                cls.WAREHOUSES_DIR / database_name / "hdfs",
                cls.WAREHOUSES_DIR / database_name / "exports"
            ]
            
            for directory in db_directories:
                directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def init_metadata_db(cls):
        """Инициализировать основную базу метаданных."""
        cls.METADATA_DIR.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(cls.MAIN_METADATA_DB)
        cursor = conn.cursor()
        
        # Создаем таблицы метаданных
        cursor.executescript("""
        -- Источники данных
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            database_name TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,  -- csv, json, xml, database
            original_path TEXT,
            size_mb REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Процессы обработки
        CREATE TABLE IF NOT EXISTS processes (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            database_name TEXT NOT NULL,
            type TEXT NOT NULL,  -- validation, cleaning, aggregation, optimization
            status TEXT NOT NULL,  -- pending, running, completed, failed
            stage TEXT NOT NULL,  -- validated, cleaned, aggregated, optimized
            config TEXT,  -- JSON конфигурация
            result TEXT,  -- JSON результат
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources (id)
        );
        
        -- Хранилища
        CREATE TABLE IF NOT EXISTS warehouses (
            id TEXT PRIMARY KEY,
            database_name TEXT NOT NULL,
            name TEXT NOT NULL,
            db_type TEXT NOT NULL,  -- postgresql, clickhouse, hdfs
            connection_config TEXT,  -- JSON конфигурация подключения
            ddl_path TEXT,
            etl_path TEXT,
            status TEXT NOT NULL,  -- created, deployed, active, inactive
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Схемы данных
        CREATE TABLE IF NOT EXISTS schemas (
            id TEXT PRIMARY KEY,
            source_id TEXT,
            warehouse_id TEXT,
            database_name TEXT NOT NULL,
            type TEXT NOT NULL,  -- discovered, validated, target
            schema_json TEXT NOT NULL,  -- JSON схема
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources (id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (id)
        );
        
        -- Части файлов (для контроля размера)
        CREATE TABLE IF NOT EXISTS file_parts (
            id INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL,
            database_name TEXT NOT NULL,
            stage TEXT NOT NULL,  -- raw, validated, cleaned, aggregated
            part_number INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            file_size_mb REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources (id),
            CONSTRAINT max_size CHECK (file_size_mb <= 500)
        );
        
        -- Артефакты (DDL, DAG, DSL)
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            warehouse_id TEXT,
            database_name TEXT NOT NULL,
            type TEXT NOT NULL,  -- ddl, dag, dsl, recommendation
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (id)
        );
        
        -- Лог автоудаления
        CREATE TABLE IF NOT EXISTS cleanup_log (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            file_size_mb REAL,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reason TEXT  -- expired, manual, error
        );
        
        -- Индексы для производительности
        CREATE INDEX IF NOT EXISTS idx_sources_database ON sources (database_name);
        CREATE INDEX IF NOT EXISTS idx_processes_source ON processes (source_id);
        CREATE INDEX IF NOT EXISTS idx_processes_database ON processes (database_name);
        CREATE INDEX IF NOT EXISTS idx_file_parts_source ON file_parts (source_id);
        CREATE INDEX IF NOT EXISTS idx_warehouses_database ON warehouses (database_name);
        """)
        
        conn.commit()
        conn.close()
    
    @classmethod
    def register_file_part(cls, source_id: str, database_name: str, stage: str, 
                          part_number: int, file_path: Path, file_size_mb: float):
        """Зарегистрировать часть файла в метаданных."""
        conn = sqlite3.connect(cls.MAIN_METADATA_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO file_parts (source_id, database_name, stage, part_number, file_path, file_size_mb)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (source_id, database_name, stage, part_number, str(file_path), file_size_mb))
        
        conn.commit()
        conn.close()
    
    @classmethod
    def get_database_list(cls) -> List[str]:
        """Получить список всех баз данных в системе."""
        conn = sqlite3.connect(cls.MAIN_METADATA_DB)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT database_name FROM sources ORDER BY database_name")
        databases = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return databases
    
    @classmethod
    def cleanup_temp_files(cls, older_than_hours: int = 24):
        """Автоматическая очистка временных файлов."""
        import shutil
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        if cls.TEMP_DIR.exists():
            for temp_dir in cls.TEMP_DIR.iterdir():
                if temp_dir.is_dir():
                    # Проверяем время создания
                    creation_time = datetime.fromtimestamp(temp_dir.stat().st_ctime)
                    if creation_time < cutoff_time:
                        # Логируем удаление
                        size_mb = sum(f.stat().st_size for f in temp_dir.rglob('*') if f.is_file()) / (1024 * 1024)
                        
                        conn = sqlite3.connect(cls.MAIN_METADATA_DB)
                        cursor = conn.cursor()
                        cursor.execute("""
                        INSERT INTO cleanup_log (file_path, file_size_mb, reason)
                        VALUES (?, ?, ?)
                        """, (str(temp_dir), size_mb, "expired"))
                        conn.commit()
                        conn.close()
                        
                        # Удаляем директорию
                        shutil.rmtree(temp_dir)

# Инициализация при импорте
DataPaths.init_metadata_db()
