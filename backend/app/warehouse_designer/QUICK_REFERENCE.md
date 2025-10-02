# МОДУЛЬ 4: БЫСТРЫЙ СПРАВОЧНИК

## 🚀 БЫСТРЫЙ СТАРТ

### Минимальный пример использования:
```python
from warehouse_designer.main import analyze_requirements, generate_ddl, execute_ddl_in_database

# 1. Подготовка контекста
context = {
    "data_profile": {"columns": [{"name": "id", "type": "Int64"}], "source_path": "/data/file.csv"},
    "optimization_recommendations": [],
    "request": {"business_requirements": "Нужна быстрая аналитика"}
}

# 2. Анализ и выбор СУБД
analysis = analyze_requirements(context)
selected_db = analysis["llm_analysis"]["final_choice"]

# 3. Генерация и выполнение DDL
ddl = generate_ddl(context, selected_db)
result = execute_ddl_in_database(ddl, selected_db)
```

## 📋 ЧЕКЛИСТ ИНТЕГРАЦИИ

### Перед использованием модуля:
- [ ] Настроены переменные окружения (POSTGRES_DSN, CLICKHOUSE_HTTP, HDFS_WEB)
- [ ] Установлен OpenAI API ключ
- [ ] Запущены целевые СУБД (PostgreSQL, ClickHouse, HDFS)
- [ ] Созданы базы данных и схемы

### Входные данные от других модулей:
- [ ] **DataProfile** от Модуля 1 с колонками и типами данных
- [ ] **OptimizationRecommendation** от Модуля 3 с рекомендациями
- [ ] **AggregationScenario** от Модуля 2 (опционально)

## 🔧 ТИПОВЫЕ СЦЕНАРИИ

### Сценарий 1: Аналитическое хранилище (ClickHouse)
```python
context = {
    "request": {
        "analytics_requirements": {
            "query_patterns": ["analytics", "aggregations"],
            "expected_volume": "high"
        }
    }
}
# Результат: ClickHouse с партиционированием
```

### Сценарий 2: Транзакционная система (PostgreSQL)
```python
context = {
    "request": {
        "analytics_requirements": {
            "refresh_interval": "real-time",
            "query_patterns": ["point_queries", "joins"]
        },
        "constraints": {"consistency": "ACID"}
    }
}
# Результат: PostgreSQL с индексами
```

### Сценарий 3: Big Data хранилище (HDFS)
```python
context = {
    "request": {
        "analytics_requirements": {
            "expected_volume": "very_high",
            "query_patterns": ["batch_processing"]
        },
        "constraints": {"budget": "low", "storage_cost": "critical"}
    }
}
# Результат: HDFS с компрессией
```

## 🎯 ФОРМАТЫ ДАННЫХ

### Входной DataProfile:
```json
{
    "id": 1,
    "source_path": "/data/raw/sales.csv",
    "columns": [
        {"name": "id", "type": "Int64"},
        {"name": "name", "type": "String"},
        {"name": "date", "type": "Date"}
    ],
    "est_rows": 1000000
}
```

### Рекомендации оптимизации:
```json
[
    {
        "table_name": "/data/raw/sales.csv",
        "recommendation_type": "partition",
        "recommendation_details": {"partition_by": "toYYYYMM(date)"}
    },
    {
        "recommendation_type": "index",
        "recommendation_details": {"columns": ["id", "name"]}
    }
]
```

## ⚡ API БЫСТРЫЕ КОМАНДЫ

```bash
# Создать дизайн
curl -X POST http://localhost:8000/api/v1/warehouse/design \
  -H "Content-Type: application/json" \
  -d '{"source_profile_id": 1, "business_requirements": "Аналитика"}'

# Подтвердить выбор
curl -X POST http://localhost:8000/api/v1/warehouse/design/{id}/confirm \
  -d '{"chosen_db": "clickhouse", "accept_llm": true}'

# Создать таблицы
curl -X POST http://localhost:8000/api/v1/warehouse/create/{id}

# Генерировать ETL
curl -X POST http://localhost:8000/api/v1/warehouse/load-data/{id}
```

## 🔍 ОТЛАДКА

### Проверка статуса:
```python
# Проверить дизайн
GET /api/v1/warehouse/design/{design_id}

# Проверить экземпляры
GET /api/v1/warehouse/instances

# Логи в консоли Docker
docker logs aie_api --tail 50
```

### Типичные ошибки:
1. **"Missing columns"** → Проверить DataProfile.columns
2. **"HDFS error: 404"** → Проверить HDFS_WEB переменную
3. **"DDL validation failed"** → Проверить соответствие колонок и оптимизаций

## 📊 МОНИТОРИНГ

### Ключевые метрики:
```python
# Время выполнения этапов
analysis_time = 2-5 сек
ddl_generation_time = 1-3 сек  
table_creation_time = 5-15 сек

# Успешность операций
ddl_success_rate = >95%
table_creation_rate = >90%
etl_generation_rate = >85%
```

## 🧪 ТЕСТИРОВАНИЕ

### Быстрые тесты:
```powershell
# Тест ClickHouse
.\test_full_workflow.ps1

# Тест PostgreSQL  
.\test_postgres_workflow.ps1

# Тест HDFS
.\test_hdfs_workflow.ps1

# Все СУБД
.\test_all_databases.ps1
```

## 🔗 ИНТЕГРАЦИОННЫЕ ТОЧКИ

### С другими модулями:
```python
# Получение данных от Модуля 1
data_profile = module1.get_data_profile(source_path)

# Получение рекомендаций от Модуля 3  
recommendations = module3.get_optimization_recommendations(table_name)

# Передача результатов в ETL систему
etl_config = module4.generate_etl_pipeline(design_id, context, selected_db)
airflow.create_dag(etl_config)
```

## 🚨 КРИТИЧЕСКИЕ МОМЕНТЫ

### Обязательные проверки:
1. **Переменные окружения** - все СУБД должны быть доступны
2. **Права доступа** - пользователи должны иметь права на создание таблиц
3. **Валидация входных данных** - columns не должен быть пустым
4. **Обработка ошибок** - всегда проверять success флаги

### Производительность:
- Не запускать параллельно >5 дизайнов одновременно
- Кэшировать результаты LLM анализа
- Использовать connection pooling для БД

## 📝 ШАБЛОНЫ КОДА

### Обработка ошибок:
```python
try:
    result = execute_ddl_in_database(ddl, selected_db)
    if not result["success"]:
        logger.error(f"DDL execution failed: {result['error']}")
        return {"status": "error", "message": result["error"]}
except Exception as e:
    logger.exception("Unexpected error in DDL execution")
    return {"status": "error", "message": str(e)}
```

### Логирование:
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Starting warehouse design for profile {profile_id}")
logger.debug(f"Context: {context}")
logger.warning(f"LLM confidence is low: {confidence}")
logger.error(f"Failed to create table: {error}")
```
