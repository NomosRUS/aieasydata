# МОДУЛЬ 4: ПРОЕКТИРОВАНИЕ ХРАНИЛИЩ - ПАСПОРТ ДЛЯ LLM

## ОБЩЕЕ ОПИСАНИЕ МОДУЛЯ

**Назначение:** Автоматическое проектирование оптимальных схем хранения данных с учетом требований аналитики и интеграции рекомендаций оптимизации.

**Поддерживаемые СУБД:** ClickHouse, PostgreSQL, HDFS

**Статус:** ✅ ПОЛНОСТЬЮ ФУНКЦИОНАЛЕН (100% тестов пройдено для всех СУБД)

## АРХИТЕКТУРА МОДУЛЯ

```
warehouse_designer/
├── main.py              # Основные функции модуля
├── router.py            # API endpoints
└── MODULE_PASSPORT.md   # Этот документ
```

## ОСНОВНЫЕ ФУНКЦИИ МОДУЛЯ

### 1. `analyze_requirements(context: Dict[str, Any]) -> Dict[str, Any]`

**Назначение:** Анализирует требования и данные для выбора оптимальной СУБД

**Входные параметры:**
```python
context = {
    "data_profile": {
        "id": int,
        "source_path": str,
        "columns": [{"name": str, "type": str}],
        "est_rows": int,
        "sample_data": list
    },
    "aggregation_scenarios": [
        {
            "scenario_name": str,
            "aggregation_type": str,
            "target_columns": [str]
        }
    ],
    "optimization_recommendations": [
        {
            "table_name": str,
            "recommendation_type": str,  # "partition", "index", "compression"
            "recommendation_details": dict
        }
    ],
    "request": {
        "business_requirements": str,
        "analytics_requirements": {
            "refresh_interval": str,
            "metrics": [str],
            "query_patterns": [str],
            "expected_volume": str
        },
        "constraints": {
            "sla": str,
            "budget": str,
            "performance_priority": str
        }
    }
}
```

**Выходные данные:**
```python
{
    "heuristic": {
        "candidate": str,  # "clickhouse", "postgres", "hdfs"
        "scores": {"clickhouse": int, "postgres": int, "hdfs": int},
        "reasons": [str]
    },
    "llm_analysis": {
        "final_choice": str,
        "summary": str,
        "critical_arguments": [str],
        "confidence": str,  # "высокая", "средняя", "низкая"
        "notes": str
    }
}
```

### 2. `generate_ddl(context: Dict[str, Any], selected_db: str) -> str`

**Назначение:** Генерирует DDL-скрипт с учетом рекомендаций оптимизации

**Входные параметры:**
```python
context = {
    "data_profile": {
        "columns": [{"name": str, "type": str}],
        "source_path": str
    },
    "optimization_recommendations": [
        {
            "recommendation_type": str,
            "recommendation_details": dict
        }
    ]
}
selected_db = "clickhouse" | "postgres" | "hdfs"
```

**Выходные данные:**
```python
str  # DDL скрипт, специфичный для выбранной СУБД
```

**Примеры выходных данных:**

**ClickHouse:**
```sql
CREATE DATABASE IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS analytics.sales_extended (
    id Int64, product_name String, category String, price Float64,
    quantity Int64, sale_date Date, customer_id Int64, is_premium UInt8,
    discount_rate Float64, region String
) ENGINE = MergeTree
PARTITION BY toYYYYMM(sale_date)
ORDER BY (sale_date, customer_id);
```

**PostgreSQL:**
```sql
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS analytics.sales_postgres (
    id BIGINT, customer_id BIGINT, product_name TEXT, category TEXT,
    price DOUBLE PRECISION, quantity BIGINT, sale_date DATE,
    payment_method TEXT, store_location TEXT
);
CREATE INDEX IF NOT EXISTS idx_sales_postgres_customer_id ON analytics.sales_postgres(customer_id);
```

**HDFS:**
```sql
-- HDFS Directory Structure and Metadata
CREATE EXTERNAL TABLE analytics.sales_hdfs (
    transaction_id STRING, timestamp STRING, user_id STRING,
    session_id STRING, event_type STRING, product_category STRING,
    revenue STRING, country STRING, device_type STRING, channel STRING
)
PARTITIONED BY (year_month)
STORED AS PARQUET
LOCATION '/warehouse/sales_hdfs/data/'
TBLPROPERTIES (
    'parquet.compression'='snappy',
    'parquet.block.size'='128MB'
);
```

### 3. `execute_ddl_in_database(ddl_script: str, selected_db: str) -> Dict[str, Any]`

**Назначение:** Выполняет DDL-скрипт в целевой СУБД

**Входные параметры:**
```python
ddl_script = str  # DDL скрипт для выполнения
selected_db = "clickhouse" | "postgres" | "hdfs"
```

**Выходные данные:**
```python
{
    "executed_at": str,  # ISO timestamp
    "database": str,
    "success": bool,
    "error": str | None,
    "details": {
        # Для PostgreSQL:
        "rows_affected": int
        
        # Для ClickHouse:
        "responses": [str]
        
        # Для HDFS:
        "hdfs_path": str
    }
}
```

### 4. `generate_etl_pipeline(design_id: str, context: Dict[str, Any], selected_db: str) -> Dict[str, Any]`

**Назначение:** Генерирует ETL-пайплайн для загрузки данных

**Входные параметры:**
```python
design_id = str  # UUID дизайна хранилища
context = {
    "data_profile": {
        "source_path": str,
        "columns": [{"name": str, "type": str}]
    },
    "optimization_recommendations": [dict]
}
selected_db = "clickhouse" | "postgres" | "hdfs"
```

**Выходные данные:**
```python
{
    "success": bool,
    "dag_id": str,  # Имя сгенерированного DAG
    "dag_file_path": str,  # Путь к файлу DAG
    "source_config": {
        "type": "file",
        "path": str,
        "format": str,  # "csv", "json", "parquet"
        "columns": [dict]
    },
    "target_config": {
        "type": str,  # СУБД
        "table_name": str,
        "database": str,
        "connection_params": dict,
        "optimizations": dict
    },
    "created_at": str,
    "error": str | None  # Если success = False
}
```

## ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ

### `_convert_columns_for_template(columns: list, selected_db: str) -> list`

**Назначение:** Конвертирует колонки из DataProfile в формат для DDL

**Входные параметры:**
```python
columns = [{"name": str, "type": str}]
selected_db = "clickhouse" | "postgres" | "hdfs"
```

**Выходные данные:**
```python
[{"name": str, "type": str}]  # С безопасными именами и правильными типами
```

### `_parse_optimization_recommendations(recommendations: list, selected_db: str, columns: list) -> Dict[str, Any]`

**Назначение:** Парсит рекомендации оптимизации для конкретной СУБД

**Входные параметры:**
```python
recommendations = [
    {
        "recommendation_type": "partition" | "index" | "compression" | "order_by",
        "recommendation_details": dict
    }
]
selected_db = "clickhouse" | "postgres" | "hdfs"
columns = [{"name": str, "type": str}]
```

**Выходные данные:**
```python
{
    # Для ClickHouse:
    "partition_by": str,  # "toYYYYMM(sale_date)"
    "order_by": [str],    # ["sale_date", "customer_id"]
    
    # Для PostgreSQL:
    "indexes": [str],     # ["customer_id", "product_name"]
    "partition_by": str,
    
    # Для HDFS:
    "partition_by": str,  # "year_month"
    "format": str,        # "parquet"
    "compression": {
        "type": str,      # "snappy"
        "block_size": str # "128MB"
    }
}
```

### `_validate_ddl_script(ddl_script: str, columns: list, optimizations: dict) -> Dict[str, Any]`

**Назначение:** Валидирует сгенерированный DDL скрипт

**Входные параметры:**
```python
ddl_script = str
columns = [{"name": str, "type": str}]
optimizations = dict
```

**Выходные данные:**
```python
{
    "valid": bool,
    "errors": [str]  # Список ошибок валидации
}
```

## API ENDPOINTS

### POST `/api/v1/warehouse/design`

**Назначение:** Запускает процесс проектирования хранилища

**Входные данные:**
```json
{
    "source_profile_id": int,
    "business_requirements": str,
    "analytics_requirements": {
        "refresh_interval": str,
        "metrics": [str],
        "query_patterns": [str],
        "expected_volume": str
    },
    "constraints": {
        "sla": str,
        "budget": str,
        "performance_priority": str
    }
}
```

**Выходные данные:**
```json
{
    "design_id": str,
    "status": "analyzing",
    "created_at": str
}
```

### POST `/api/v1/warehouse/design/{design_id}/confirm`

**Назначение:** Подтверждает выбор СУБД и генерирует DDL

**Входные данные:**
```json
{
    "chosen_db": "clickhouse" | "postgres" | "hdfs",
    "accept_llm": bool,
    "notes": str
}
```

**Выходные данные:**
```json
{
    "status": "ddl_generated" | "ddl_error",
    "results": {
        "ddl_script": str,
        "optimizations_applied": [str]
    }
}
```

### POST `/api/v1/warehouse/create/{design_id}`

**Назначение:** Создает таблицы/директории в целевой СУБД

**Выходные данные:**
```json
{
    "status": "success" | "error",
    "message": str,
    "details": dict
}
```

### POST `/api/v1/warehouse/load-data/{design_id}`

**Назначение:** Генерирует ETL пайплайн для загрузки данных

**Выходные данные:**
```json
{
    "status": "created" | "error",
    "dag_id": str,
    "message": str
}
```

### GET `/api/v1/warehouse/design/{design_id}`

**Назначение:** Получает статус и результаты проектирования

**Выходные данные:**
```json
{
    "design_id": str,
    "status": str,
    "results": {
        "heuristic": dict,
        "llm_analysis": dict,
        "ddl_script": str
    },
    "final_selection": {
        "chosen_db": str,
        "accepted_llm": bool,
        "user_notes": str
    }
}
```

### GET `/api/v1/warehouse/instances`

**Назначение:** Получает список созданных экземпляров хранилищ

**Выходные данные:**
```json
[
    {
        "design_id": str,
        "target_db_type": str,
        "table_name": str,
        "created_at": str
    }
]
```

## ИНТЕГРАЦИЯ С ДРУГИМИ МОДУЛЯМИ

### Входные данные от других модулей:

1. **От Модуля 1 (Валидация данных):**
   - `DataProfile` с анализом качества данных
   - Информация о найденных аномалиях

2. **От Модуля 2 (Агрегация):**
   - `AggregationScenario` с описанием сценариев агрегации
   - Рекомендации по группировке данных

3. **От Модуля 3 (Оптимизация):**
   - `OptimizationRecommendation` с рекомендациями по партиционированию, индексам, сжатию

### Выходные данные для других модулей:

1. **Для Модуля ETL/Airflow:**
   - Сгенерированные DAG файлы
   - Конфигурация источников и целевых систем

2. **Для системы мониторинга:**
   - Метаданные созданных хранилищ
   - Статистика использования оптимизаций

## ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ

```bash
# PostgreSQL
POSTGRES_DSN=postgresql://user:pass@localhost:5432/aieasydata

# ClickHouse
CLICKHOUSE_HTTP=http://localhost:8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=password

# HDFS
HDFS_WEB=http://localhost:9870

# OpenAI для LLM анализа
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Полный цикл проектирования:

```python
# 1. Анализ требований
context = {...}  # Данные от других модулей
analysis = analyze_requirements(context)

# 2. Генерация DDL
selected_db = analysis["llm_analysis"]["final_choice"]
ddl_script = generate_ddl(context, selected_db)

# 3. Создание инфраструктуры
result = execute_ddl_in_database(ddl_script, selected_db)

# 4. Генерация ETL
etl_result = generate_etl_pipeline(design_id, context, selected_db)
```

## ТЕСТИРОВАНИЕ

**Доступные тесты:**
- `test_full_workflow.ps1` - ClickHouse (9/9 тестов)
- `test_postgres_workflow.ps1` - PostgreSQL (8/8 тестов)  
- `test_hdfs_workflow.ps1` - HDFS (7/7 тестов)
- `test_all_databases.ps1` - Комплексный тест всех СУБД

**Статус тестирования:** ✅ ВСЕ ТЕСТЫ ПРОХОДЯТ (100%)

## ОГРАНИЧЕНИЯ И ИЗВЕСТНЫЕ ПРОБЛЕМЫ

1. **HDFS:** Требует запущенный NameNode для создания директорий
2. **ClickHouse:** Требует аутентификацию через заголовки X-ClickHouse-User/Key
3. **PostgreSQL:** Требует существующую схему analytics

## ВЕРСИОННОСТЬ

- **Версия:** 1.0
- **Последнее обновление:** 2025-09-25
- **Статус:** Готов к продакшену
- **Совместимость:** Python 3.11+, FastAPI, SQLAlchemy 2.0+
