# 📁 СХЕМА ОРГАНИЗАЦИИ ДАННЫХ СИСТЕМЫ AiEasyData

## 🎯 ТЕКУЩЕЕ СОСТОЯНИЕ

### **Существующие папки:**
```
📁 data_landing_zone/          # Основная зона данных
├── raw/                       # Сырые данные (частично используется)
├── cleaned/                   # Очищенные данные (создана, но не используется)
├── aggregated/               # Агрегированные данные (не используется)
├── transformed/              # Трансформированные данные (не используется)
├── syn_csv/, syn_json/, syn_xml/  # Тестовые данные
└── test_data/                # Тестовые данные

📁 aggregated/                 # Дублирует data_landing_zone/aggregated/
├── all_columns_all_files/
├── individual_large_csv_data_10_rows/
└── ...

📁 backend/data_landing_zone/  # Еще одно дублирование
└── aggregated/
```

### **Проблемы текущей структуры:**
❌ Дублирование папок aggregated  
❌ Неясные пути в разных модулях  
❌ Отсутствие централизованного управления метаданными  
❌ Нет четкой схемы для целевых хранилищ  

## 🏗️ ОБНОВЛЕННАЯ СХЕМА ОРГАНИЗАЦИИ

### **1. 📥 СЫРЫЕ ЗАГРУЖАЕМЫЕ ДАННЫЕ**
```
📁 data_landing_zone/raw/
├── uploads/                   # Загруженные пользователем файлы
│   ├── {timestamp}_{user_id}_{filename}
│   └── metadata.json         # Метаданные загрузки
├── external/                  # Внешние источники данных
│   ├── api_sources/
│   ├── database_exports/
│   └── file_imports/
├── synthetic/                 # Синтетические/тестовые данные (существующие)
│   ├── syn_csv/
│   ├── syn_json/
│   └── syn_xml/
└── staging/                   # Временные файлы при загрузке
    └── {session_id}/
```

### **2. 📊 ПРОМЕЖУТОЧНЫЕ ДАННЫЕ (ПО БАЗАМ ДАННЫХ)**
```
📁 data_landing_zone/intermediate/
├── {database_name}/           # Отдельная папка для каждой целевой БД
│   ├── validated/             # После модуля 1 (валидация)
│   │   ├── {source_id}/
│   │   │   ├── data_part_001.parquet  # Макс 500MB
│   │   │   ├── data_part_002.parquet  # Макс 500MB
│   │   │   ├── quality_report.json
│   │   │   └── anomalies.json
│   │   └── metadata.db        # SQLite база метаданных
│   ├── cleaned/               # После очистки модулем 1
│   │   ├── {source_id}/
│   │   │   ├── cleaned_part_001.parquet  # Макс 500MB
│   │   │   ├── cleaned_part_002.parquet  # Макс 500MB
│   │   │   ├── cleaning_log.json
│   │   │   └── quality_metrics.json
│   │   └── metadata.db
│   ├── aggregated/            # После модуля 2 (агрегация)
│   │   ├── {scenario_id}/
│   │   │   ├── result_part_001.parquet   # Макс 500MB
│   │   │   ├── result_part_002.parquet   # Макс 500MB
│   │   │   ├── aggregation_config.json
│   │   │   └── join_metadata.json
│   │   └── metadata.db
│   └── optimized/             # После модуля 3 (оптимизация)
│       ├── {analysis_id}/
│       │   ├── performance_report.json
│       │   ├── recommendations.json
│       │   └── optimized_queries.sql
│       └── metadata.db
└── _temp/                     # Временные файлы (автоудаление)
    └── {process_id}/
```

### **3. 🎯 ЦЕЛЕВЫЕ ХРАНИЛИЩА (ПО БАЗАМ ДАННЫХ)**
```
📁 data_landing_zone/warehouses/
├── {database_name}/           # Отдельная папка для каждой БД
│   ├── postgresql/
│   │   ├── {warehouse_id}/
│   │   │   ├── ddl/           # DDL скрипты
│   │   │   │   ├── create_tables.sql
│   │   │   │   ├── create_indexes.sql
│   │   │   │   └── create_partitions.sql
│   │   │   ├── data/          # Экспортированные данные (макс 500MB)
│   │   │   │   ├── {table_name}_part_001.csv
│   │   │   │   └── {table_name}_part_002.csv
│   │   │   ├── etl/           # ETL пайплайны
│   │   │   │   └── airflow_dag.py
│   │   │   └── metadata.db    # SQLite метаданные
│   │   └── connections/       # Конфигурации подключений
│   ├── clickhouse/
│   │   ├── {warehouse_id}/
│   │   │   ├── ddl/
│   │   │   │   ├── create_tables.sql
│   │   │   │   └── partitions.sql
│   │   │   ├── data/          # Данные (макс 500MB)
│   │   │   │   ├── {table_name}_part_001.parquet
│   │   │   │   └── {table_name}_part_002.parquet
│   │   │   ├── etl/
│   │   │   └── metadata.db
│   │   └── connections/
│   ├── hdfs/
│   │   ├── {warehouse_id}/
│   │   │   ├── ddl/
│   │   │   │   └── external_tables.sql
│   │   │   ├── data/          # Партиционированные данные (макс 500MB)
│   │   │   │   └── partitioned/
│   │   │   │       └── year={year}/month={month}/
│   │   │   │           ├── data_part_001.parquet
│   │   │   │           └── data_part_002.parquet
│   │   │   ├── etl/
│   │   │   └── metadata.db
│   │   └── connections/
│   └── exports/              # Готовые экспорты
│       ├── {export_id}/
│       └── scheduled/
└── _shared/                  # Общие ресурсы
    ├── templates/            # Шаблоны DDL/ETL
    └── scripts/              # Общие скрипты
```

### **4. 📋 ЦЕНТРАЛИЗОВАННЫЕ МЕТАДАННЫЕ (SQLite БД)**
```
📁 data_landing_zone/metadata/
├── main.db                   # Основная SQLite база метаданных
│   ├── sources               # Таблица источников данных
│   ├── processes             # Таблица процессов (валидация, агрегация, оптимизация)
│   ├── warehouses            # Таблица хранилищ
│   ├── schemas               # Таблица схем данных
│   ├── artifacts             # Таблица артефактов (DDL, DAG, DSL)
│   ├── file_parts            # Таблица частей файлов (для контроля размера)
│   └── cleanup_log           # Лог автоудаления файлов
├── backups/                  # Резервные копии БД
│   ├── main_backup_{timestamp}.db
│   └── retention_policy.json
└── exports/                  # Экспорты метаданных
    ├── sources_registry.json
    ├── warehouses_catalog.json
    └── system_health.json
```

### **📏 КОНТРОЛЬ РАЗМЕРА ФАЙЛОВ**
```sql
-- Таблица для отслеживания частей файлов
CREATE TABLE file_parts (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,
    database_name TEXT NOT NULL,
    stage TEXT NOT NULL,  -- raw, validated, cleaned, aggregated
    part_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_size_mb REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT max_size CHECK (file_size_mb <= 500)
);
```

## 🔧 ЦЕНТРАЛИЗОВАННОЕ УПРАВЛЕНИЕ ПУТЯМИ

### **Создадим конфигурационный модуль:**

```python
# backend/app/config/paths.py
from pathlib import Path
from typing import Dict, Any
import os

class DataPaths:
    """Централизованное управление путями к данным."""
    
    # Базовые пути
    BASE_DATA_DIR = Path(os.getenv("DATA_BASE_DIR", "/data"))
    
    # 1. Сырые данные
    RAW_DATA_DIR = BASE_DATA_DIR / "raw"
    RAW_UPLOADS = RAW_DATA_DIR / "uploads"
    RAW_EXTERNAL = RAW_DATA_DIR / "external"
    RAW_SYNTHETIC = RAW_DATA_DIR / "synthetic"
    RAW_STAGING = RAW_DATA_DIR / "staging"
    
    # 2. Промежуточные данные
    INTERMEDIATE_DIR = BASE_DATA_DIR / "intermediate"
    VALIDATED_DIR = INTERMEDIATE_DIR / "validated"
    CLEANED_DIR = INTERMEDIATE_DIR / "cleaned"
    AGGREGATED_DIR = INTERMEDIATE_DIR / "aggregated"
    OPTIMIZED_DIR = INTERMEDIATE_DIR / "optimized"
    
    # 3. Целевые хранилища
    WAREHOUSES_DIR = BASE_DATA_DIR / "warehouses"
    POSTGRESQL_DIR = WAREHOUSES_DIR / "postgresql"
    CLICKHOUSE_DIR = WAREHOUSES_DIR / "clickhouse"
    HDFS_DIR = WAREHOUSES_DIR / "hdfs"
    EXPORTS_DIR = WAREHOUSES_DIR / "exports"
    
    # 4. Метаданные
    METADATA_DIR = BASE_DATA_DIR / "metadata"
    SOURCES_METADATA = METADATA_DIR / "sources"
    PROCESSES_METADATA = METADATA_DIR / "processes"
    SCHEMAS_METADATA = METADATA_DIR / "schemas"
    ARTIFACTS_METADATA = METADATA_DIR / "artifacts"
    SYSTEM_METADATA = METADATA_DIR / "system"
    
    @classmethod
    def get_source_path(cls, source_id: str, data_type: str = "raw") -> Path:
        """Получить путь для источника данных."""
        if data_type == "raw":
            return cls.RAW_UPLOADS / source_id
        elif data_type == "validated":
            return cls.VALIDATED_DIR / source_id
        elif data_type == "cleaned":
            return cls.CLEANED_DIR / source_id
        elif data_type == "aggregated":
            return cls.AGGREGATED_DIR / source_id
        else:
            raise ValueError(f"Unknown data type: {data_type}")
    
    @classmethod
    def get_warehouse_path(cls, warehouse_id: str, db_type: str) -> Path:
        """Получить путь для хранилища."""
        if db_type == "postgresql":
            return cls.POSTGRESQL_DIR / warehouse_id
        elif db_type == "clickhouse":
            return cls.CLICKHOUSE_DIR / warehouse_id
        elif db_type == "hdfs":
            return cls.HDFS_DIR / warehouse_id
        else:
            raise ValueError(f"Unknown database type: {db_type}")
    
    @classmethod
    def get_metadata_path(cls, metadata_type: str, item_id: str) -> Path:
        """Получить путь для метаданных."""
        if metadata_type == "source":
            return cls.SOURCES_METADATA / f"{item_id}.json"
        elif metadata_type == "process":
            return cls.PROCESSES_METADATA / metadata_type / f"{item_id}.json"
        elif metadata_type == "schema":
            return cls.SCHEMAS_METADATA / "discovered" / f"{item_id}_schema.json"
        elif metadata_type == "artifact":
            return cls.ARTIFACTS_METADATA / metadata_type / item_id
        else:
            raise ValueError(f"Unknown metadata type: {metadata_type}")
    
    @classmethod
    def ensure_directories(cls):
        """Создать все необходимые директории."""
        directories = [
            cls.RAW_UPLOADS, cls.RAW_EXTERNAL, cls.RAW_SYNTHETIC, cls.RAW_STAGING,
            cls.VALIDATED_DIR, cls.CLEANED_DIR, cls.AGGREGATED_DIR, cls.OPTIMIZED_DIR,
            cls.POSTGRESQL_DIR, cls.CLICKHOUSE_DIR, cls.HDFS_DIR, cls.EXPORTS_DIR,
            cls.SOURCES_METADATA, cls.PROCESSES_METADATA, cls.SCHEMAS_METADATA,
            cls.ARTIFACTS_METADATA, cls.SYSTEM_METADATA
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
```

## 🔄 ИНТЕГРАЦИЯ С МОДУЛЯМИ

### **Модуль 1 (Валидация):**
```python
# Входные данные
input_path = DataPaths.get_source_path(source_id, "raw")

# Выходные данные
validated_path = DataPaths.get_source_path(source_id, "validated")
cleaned_path = DataPaths.get_source_path(source_id, "cleaned")

# Метаданные
quality_metadata = DataPaths.get_metadata_path("process", f"validation_{source_id}")
```

### **Модуль 2 (Агрегация):**
```python
# Входные данные
cleaned_data = DataPaths.get_source_path(source_id, "cleaned")

# Выходные данные
aggregated_path = DataPaths.get_source_path(scenario_id, "aggregated")

# Метаданные
aggregation_metadata = DataPaths.get_metadata_path("process", f"aggregation_{scenario_id}")
```

### **Модуль 3 (Оптимизация):**
```python
# Анализ данных
data_path = DataPaths.get_source_path(source_id, "cleaned")

# Выходные рекомендации
recommendations_path = DataPaths.OPTIMIZED_DIR / analysis_id / "recommendations.json"

# Метаданные
optimization_metadata = DataPaths.get_metadata_path("process", f"optimization_{analysis_id}")
```

### **Модуль 4 (Проектирование):**
```python
# Создание хранилища
warehouse_path = DataPaths.get_warehouse_path(warehouse_id, db_type)

# DDL скрипты
ddl_path = warehouse_path / "ddl"

# ETL пайплайны
etl_path = warehouse_path / "etl"

# Метаданные
warehouse_metadata = DataPaths.get_metadata_path("process", f"warehouse_{warehouse_id}")
```

### **Модуль 5 (Мониторинг):**
```python
# Мониторинг всех типов данных
raw_data = DataPaths.RAW_DATA_DIR
intermediate_data = DataPaths.INTERMEDIATE_DIR
warehouses = DataPaths.WAREHOUSES_DIR

# Метрики производительности
metrics_path = DataPaths.SYSTEM_METADATA / "performance_metrics.json"
```

## 🎯 ПРЕИМУЩЕСТВА ПРЕДЛАГАЕМОЙ СХЕМЫ

### **✅ Четкая организация:**
- Каждый тип данных имеет свое место
- Логическое разделение по этапам обработки
- Централизованное управление метаданными

### **✅ Масштабируемость:**
- Поддержка множественных источников и хранилищ
- Версионирование данных и артефактов
- Легкое добавление новых типов хранилищ

### **✅ Прозрачность:**
- Все модули знают, откуда брать и куда передавать данные
- Полная трассируемость данных
- Централизованные метаданные

### **✅ Надежность:**
- Резервное копирование по этапам
- Восстановление данных на любом этапе
- Аудит всех операций

## 🚀 ГОТОВЫЕ КОМПОНЕНТЫ ДЛЯ ВНЕДРЕНИЯ

### **✅ СОЗДАННЫЕ МОДУЛИ:**

#### **1. config/paths.py - Централизованное управление путями**
- ✅ Класс `DataPaths` с методами для всех типов данных
- ✅ Поддержка разделения по базам данных
- ✅ Контроль максимального размера файлов (500MB)
- ✅ Автоматическое создание директорий
- ✅ SQLite база метаданных с полной схемой

#### **2. config/file_utils.py - Утилиты для работы с файлами**
- ✅ Класс `FileSplitter` для автоматического разделения больших файлов
- ✅ Поддержка CSV, JSON, XML с конвертацией в Parquet
- ✅ Класс `FileManager` для управления частями файлов
- ✅ Автоматическая регистрация в метаданных
- ✅ Функции объединения частей файлов

#### **3. config/migration.py - Скрипт миграции данных**
- ✅ Класс `DataMigration` для автоматической миграции
- ✅ Перенос существующих syn_csv, syn_json, syn_xml
- ✅ Миграция агрегированных данных
- ✅ Создание резервных копий
- ✅ Подробное логирование процесса

### **🎯 ИНТЕГРАЦИЯ С МОДУЛЯМИ - ГОТОВЫЕ ПРИМЕРЫ:**

#### **Модуль 1 (Валидация):**
```python
from backend.app.config import DataPaths, file_manager

# Обработка файла с автоматическим разделением
def validate_file(source_path: str, database_name: str):
    # Определяем источник
    source_id = Path(source_path).stem
    
    # Обрабатываем с автоматическим разделением
    parts = file_manager.process_file(
        Path(source_path), database_name, source_id, "validated"
    )
    
    # Валидируем каждую часть
    for part_path in parts:
        df = pd.read_parquet(part_path)
        # ... логика валидации
    
    # Сохраняем результаты в cleaned/
    cleaned_parts = file_manager.process_file(
        cleaned_data_path, database_name, source_id, "cleaned"
    )
```

#### **Модуль 2 (Агрегация):**
```python
# Агрегация данных из разных баз
def aggregate_cross_database(scenario_id: str):
    databases = DataPaths.get_database_list()
    
    for db_name in databases:
        # Получаем очищенные данные
        cleaned_path = DataPaths.get_database_intermediate_path(db_name, "cleaned")
        
        # Объединяем части файлов
        df = file_manager.combine_file_parts(source_id, db_name, "cleaned")
        
        # Выполняем агрегацию
        result_df = perform_aggregation(df)
        
        # Сохраняем с автоматическим разделением
        result_parts = file_manager.process_file(
            result_path, db_name, scenario_id, "aggregated"
        )
```

#### **Модуль 4 (Проектирование):**
```python
# Создание хранилища с учетом базы данных
def create_warehouse(warehouse_id: str, database_name: str, db_type: str):
    # Получаем путь для хранилища
    warehouse_path = DataPaths.get_warehouse_path(database_name, warehouse_id, db_type)
    
    # Создаем структуру
    ddl_path = warehouse_path / "ddl"
    data_path = warehouse_path / "data"
    etl_path = warehouse_path / "etl"
    
    # Генерируем DDL с учетом частей файлов
    parts = file_manager.get_file_parts(source_id, database_name, "cleaned")
    
    # Создаем таблицы для каждой части или объединенную таблицу
    if len(parts) > 1:
        # Партиционированная таблица
        ddl = generate_partitioned_ddl(parts)
    else:
        # Обычная таблица
        ddl = generate_single_table_ddl(parts[0])
```

### **📊 АВТОМАТИЧЕСКИЙ КОНТРОЛЬ РАЗМЕРА ФАЙЛОВ:**

```python
# Пример автоматического разделения
source_file = "/data_landing_zone/raw/uploads/large_dataset.csv"  # 2GB файл

# Автоматически разделится на части по 500MB
parts = file_manager.process_file(
    Path(source_file), "sales_db", "large_dataset", "validated"
)

# Результат:
# parts = [
#     "/data_landing_zone/intermediate/sales_db/validated/large_dataset/large_dataset_part_001.parquet",
#     "/data_landing_zone/intermediate/sales_db/validated/large_dataset/large_dataset_part_002.parquet", 
#     "/data_landing_zone/intermediate/sales_db/validated/large_dataset/large_dataset_part_003.parquet",
#     "/data_landing_zone/intermediate/sales_db/validated/large_dataset/large_dataset_part_004.parquet"
# ]

# Каждый файл <= 500MB
# Автоматически зарегистрированы в SQLite метаданных
```

### **🎯 ЗАПУСК МИГРАЦИИ:**

```python
# Простой запуск миграции
from backend.app.config import run_migration

# Автоматически:
# 1. Создает новую структуру директорий
# 2. Переносит все существующие данные
# 3. Создает SQLite базу метаданных
# 4. Регистрирует все файлы
# 5. Создает резервные копии
# 6. Генерирует отчет о миграции

migration = run_migration()
```

### **📋 ГОТОВНОСТЬ К ВНЕДРЕНИЮ: 100%**

**✅ Все компоненты созданы и готовы к использованию:**
- Централизованное управление путями
- Автоматическое разделение файлов по 500MB
- SQLite база метаданных с полной схемой
- Скрипт автоматической миграции
- Примеры интеграции для всех модулей
- Контроль размера файлов
- Разделение по базам данных
- Автоматическая очистка временных файлов

## **📊 СХЕМА БАЗЫ ДАННЫХ**

### **Основные таблицы модулей:**

#### **1. aggregation_scenarios (Модуль 2)**
```sql
CREATE TABLE aggregation_scenarios (
    id                  SERIAL PRIMARY KEY,
    scenario_name       VARCHAR UNIQUE NOT NULL,  -- Уникальное имя сценария
    description         TEXT,                     -- Описание сценария
    sources             JSON,                     -- Список источников данных
    aggregations        JSON,                     -- Конфигурация агрегаций
    enrichments         JSON,                     -- Правила обогащения
    target_requirements JSON,                     -- Требования к целевой системе
    status              VARCHAR DEFAULT 'created', -- Статус выполнения
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_executed       TIMESTAMP,                -- Время последнего выполнения
    execution_stats     JSON                      -- Статистика выполнения
);
```

#### **2. optimization_recommendations (Модуль 3)**
```sql
CREATE TABLE optimization_recommendations (
    id                     SERIAL PRIMARY KEY,
    table_name            VARCHAR,               -- Имя таблицы для оптимизации
    recommendation_type   VARCHAR,               -- Тип рекомендации (partition, index, etc.)
    recommendation_details JSON,                 -- Детали рекомендации
    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW(),
    UNIQUE(table_name, recommendation_type)
);
```

#### **3. warehouse_instances (Модуль 4)**
```sql
CREATE TABLE warehouse_instances (
    id            SERIAL PRIMARY KEY,
    design_id     VARCHAR UNIQUE,              -- Уникальный ID дизайна
    target_db_type VARCHAR,                    -- Тип целевой БД (clickhouse, postgresql, hdfs)
    db_name       VARCHAR,                     -- Имя базы данных
    table_name    VARCHAR,                     -- Имя таблицы
    ddl_script    TEXT,                        -- DDL скрипт создания
    status        VARCHAR DEFAULT 'created',   -- Статус создания
    created_at    TIMESTAMP DEFAULT NOW()
);
```

### **Обновления схемы (28.09.2025):**
- ✅ Исправлена таблица `aggregation_scenarios` - добавлена колонка `scenario_name`
- ✅ Обновлена структура для совместимости с Pydantic моделями модуля 2
- ✅ Добавлены правильные ограничения уникальности

**🚀 ГОТОВО К НЕМЕДЛЕННОМУ ВНЕДРЕНИЮ!**

**Хотите запустить миграцию прямо сейчас?**
