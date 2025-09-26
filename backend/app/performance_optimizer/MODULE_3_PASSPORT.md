# МОДУЛЬ 3: ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ - ПАСПОРТ ДЛЯ LLM

## ОБЩЕЕ ОПИСАНИЕ МОДУЛЯ

**Назначение:** Автоматический анализ производительности и генерация рекомендаций по оптимизации для различных источников данных с интеграцией с модулями 4 и 5.

**Поддерживаемые источники:** CSV, JSON, XML, Parquet файлы, PostgreSQL, ClickHouse, директории, существующие хранилища

**Статус:** ✅ ПОЛНОСТЬЮ ФУНКЦИОНАЛЕН (Реализован согласно ТЗ)

## АРХИТЕКТУРА МОДУЛЯ

```
performance_optimizer/
├── __init__.py          # Инициализация модуля
├── main.py              # Основная логика и координация
├── analyzer.py          # Анализ производительности
├── optimizer.py         # Генерация рекомендаций
├── router.py            # API endpoints
├── schemas.py           # Pydantic модели
└── MODULE_3_PASSPORT.md # Этот документ
```

## ОСНОВНЫЕ КЛАССЫ И ФУНКЦИИ

### 1. `PerformanceAnalyzer` (analyzer.py)

**Назначение:** Анализ производительности источников данных с интеграцией с Модулем 5

**Основные методы:**

#### `analyze_source(source: str, source_type: Optional[SourceType] = None) -> PerformanceAnalysisResult`

**Назначение:** Полный анализ производительности источника данных

**Входные параметры:**
```python
source = str  # Путь к файлу/директории или строка подключения к БД
source_type = Optional[SourceType]  # Тип источника (автоопределяется если не указан)
```

**Выходные данные:**
```python
PerformanceAnalysisResult = {
    "analysis_id": str,
    "source": str,
    "source_type": SourceType,
    "status": AnalysisStatus,
    "current_metrics": PerformanceMetrics,
    "bottlenecks": List[str],
    "recommendations": List[OptimizationRecommendation],
    "llm_analysis": str,
    "created_at": datetime,
    "completed_at": Optional[datetime],
    "error_message": Optional[str]
}
```

**Интеграция с Модулем 5:**
- Использует `GET /api/v1/metrics/auto-detect` для автоопределения типов данных
- Получает метрики производительности через DataTypeDetector
- Поддерживает все форматы: CSV, JSON, XML, Parquet, PostgreSQL, ClickHouse

#### `analyze_existing_warehouse(design_id: str) -> PerformanceAnalysisResult`

**Назначение:** Анализ производительности существующего хранилища из Модуля 4

**Интеграция с Модулем 4:**
- Использует `POST /api/v1/metrics/collect-by-design/{design_id}`
- Получает метрики реальных БД (ClickHouse, PostgreSQL)
- Анализирует созданные в Модуле 4 таблицы

### 2. `OptimizationGenerator` (optimizer.py)

**Назначение:** Генерация рекомендаций по оптимизации производительности

#### `generate_recommendations(analysis_result: PerformanceAnalysisResult, target_db_type: Optional[str] = None) -> List[OptimizationRecommendation]`

**Назначение:** Создание DDL-скриптов и рекомендаций по оптимизации

**Типы рекомендаций:**
- **PARTITION** - Партиционирование для больших таблиц
- **INDEX** - Индексы для ускорения запросов  
- **COMPRESSION** - Сжатие данных для экономии места
- **ORDER_BY** - Оптимальная сортировка (ClickHouse)
- **RESTRUCTURE** - Изменение формата данных

**Поддерживаемые СУБД:**
- **ClickHouse:** `PARTITION BY toYYYYMM(date)`, `ORDER BY (date, id)`
- **PostgreSQL:** `CREATE INDEX`, `PARTITION BY RANGE`
- **HDFS:** `PARTITIONED BY`, `STORED AS PARQUET`, `COMPRESSION snappy`

**Формат рекомендаций (совместимый с Модулем 4):**
```python
# ClickHouse
recommendation_details = {
    "partition_by": "toYYYYMM(sale_date)",
    "order_by": ["sale_date", "customer_id"]
}

# PostgreSQL
recommendation_details = {
    "indexes": ["customer_id", "product_name"],
    "partition_by": "RANGE (sale_date)"
}

# HDFS
recommendation_details = {
    "partition_by": "year_month",
    "format": "parquet",
    "compression": {"type": "snappy", "block_size": "128MB"}
}
```

### 3. `PerformanceOptimizer` (main.py)

**Назначение:** Главный класс, координирующий работу анализатора и генератора оптимизаций

#### `analyze_performance(request: PerformanceAnalysisRequest) -> PerformanceAnalysisResult`

**Назначение:** Запуск полного анализа производительности

**Процесс:**
1. Анализ через PerformanceAnalyzer + интеграция с Модулем 5
2. Генерация рекомендаций через OptimizationGenerator
3. Валидация DDL-скриптов (интеграция с Модулем 4)
4. Сохранение результатов в кэше

#### `apply_optimizations(application: OptimizationApplication) -> OptimizationResult`

**Назначение:** Применение рекомендаций по оптимизации

**Интеграция с Модулем 4:**
- Сохранение рекомендаций в таблицу `optimization_recommendations`
- Автоматическое встраивание в DDL при создании хранилищ через `_parse_optimization_recommendations`
- Использование функции `_validate_ddl_script` для валидации

## API ENDPOINTS

### Основные endpoints:

#### `POST /api/v1/performance/analyze`
**Назначение:** Анализ производительности источника данных

**Входные данные:**
```json
{
    "source": "string",  // Путь к файлу/директории или строка подключения
    "source_type": "csv|json|xml|parquet|postgresql|clickhouse|directory",  // Опционально
    "performance_requirements": {},  // Требования к производительности
    "constraints": {},  // Ограничения
    "target_db_type": "clickhouse|postgres|hdfs"  // Целевая СУБД
}
```

**Выходные данные:**
```json
{
    "analysis_id": "string",
    "source": "string",
    "source_type": "string",
    "status": "analyzing|completed|error",
    "current_metrics": {
        "data_size_bytes": 0,
        "row_count": 0,
        "processing_time_ms": 0,
        "bottlenecks": []
    },
    "recommendations": [
        {
            "recommendation_type": "partition|index|compression|order_by|restructure",
            "target_table": "string",
            "target_db_type": "string",
            "ddl_script": "string",
            "estimated_improvement": 0.0,
            "reasoning": "string",
            "priority": "high|medium|low"
        }
    ],
    "llm_analysis": "string"
}
```

#### `GET /api/v1/performance/analysis/{analysis_id}`
**Назначение:** Получение результатов анализа по ID

#### `POST /api/v1/performance/optimize/{analysis_id}`
**Назначение:** Применение рекомендаций по оптимизации

**Входные данные:**
```json
{
    "recommendation_ids": ["partition", "index"],
    "dry_run": true,  // Тестовый режим
    "confirm_application": false  // Подтверждение реального применения
}
```

#### `GET /api/v1/performance/recommendations/{table_name}`
**Назначение:** Получение рекомендаций для конкретной таблицы

#### `GET /api/v1/performance/history/{table_name}`
**Назначение:** История оптимизаций таблицы

### Интеграционные endpoints:

#### `GET /api/v1/performance/metrics/{source}`
**Назначение:** Получение текущих метрик через интеграцию с Модулем 5

#### `POST /api/v1/performance/validate-ddl`
**Назначение:** Валидация DDL-скриптов через интеграцию с Модулем 4

#### `GET /api/v1/performance/warehouses`
**Назначение:** Список существующих хранилищ из Модуля 4

#### `GET /api/v1/performance/health-check`
**Назначение:** Проверка работоспособности и интеграций

## МОДЕЛИ ДАННЫХ

### Основные Pydantic модели:

#### `PerformanceAnalysisRequest`
```python
{
    "source": str,
    "source_type": Optional[SourceType],
    "performance_requirements": Optional[Dict],
    "constraints": Optional[Dict],
    "target_db_type": Optional[str]
}
```

#### `PerformanceMetrics`
```python
{
    "source_type": SourceType,
    "data_size_bytes": int,
    "row_count": int,
    "column_count": Optional[int],
    "processing_time_ms": Optional[float],
    "avg_query_time_ms": Optional[float],
    "index_usage_stats": Optional[Dict],
    "partition_stats": Optional[Dict],
    "bottlenecks": List[str],
    "structure_info": Optional[Dict]
}
```

#### `OptimizationRecommendation`
```python
{
    "recommendation_type": RecommendationType,
    "target_table": str,
    "target_db_type": str,
    "ddl_script": str,
    "recommendation_details": Dict,
    "estimated_improvement": float,
    "reasoning": str,
    "priority": Priority,
    "validation_status": Optional[str]
}
```

## ИНТЕГРАЦИЯ С ДРУГИМИ МОДУЛЯМИ

### Интеграция с Модулем 5 (Мониторинг хранилищ):

**Входные данные от Модуля 5:**
1. **Автоопределение типов данных:**
   - API: `GET /api/v1/metrics/auto-detect?source={source}`
   - Поддержка: CSV, JSON, XML, Parquet, PostgreSQL, ClickHouse, директории
   - Автоопределение: разделители, форматы, теги, строки подключения

2. **Метрики производительности:**
   - API: `POST /api/v1/metrics/collect-by-design/{design_id}`
   - Данные: размер, количество строк, время обработки, структура

3. **Мониторинг файловой системы:**
   - API: `GET /api/v1/metrics/data-landing-zone`
   - Обработка больших файлов (>1GB) с оптимизацией

### Интеграция с Модулем 4 (Проектирование хранилищ):

**Выходные данные для Модуля 4:**
1. **Сохранение рекомендаций:**
   - Таблица: `optimization_recommendations`
   - Формат: совместимый с `_parse_optimization_recommendations`
   - Типы: "partition", "index", "compression", "order_by"

2. **Валидация DDL:**
   - Функция: `_validate_ddl_script` из warehouse_designer.main
   - Проверка синтаксиса и совместимости

3. **Получение хранилищ:**
   - API: `GET /api/v1/warehouse/instances`
   - Анализ существующих таблиц по design_id

## АЛГОРИТМЫ АНАЛИЗА

### Выявление узких мест:

1. **Анализ размера данных:**
   - \> 1GB → "Требуется партиционирование"
   - \> 10M строк → "Требуется индексирование"

2. **Анализ производительности:**
   - Время обработки > 10 сек → "Медленная обработка"
   - Время запроса > 1 сек → "Медленные запросы"

3. **Анализ использования индексов:**
   - Использование < 10% → "Неиспользуемые индексы"

4. **Анализ партиций:**
   - Неравномерное распределение > 50% → "Неоптимальное партиционирование"

### Генерация рекомендаций:

1. **Партиционирование:**
   - Условие: row_count > 1M
   - ClickHouse: `toYYYYMM(date_column)`
   - PostgreSQL: `RANGE (date_column)`
   - HDFS: `PARTITIONED BY (column)`

2. **Индексирование:**
   - ID колонки: приоритет HIGH
   - Внешние ключи (*_id): приоритет MEDIUM
   - Статусные поля: приоритет MEDIUM

3. **Сжатие:**
   - Условие: data_size > 100MB
   - ClickHouse: LZ4 compression
   - HDFS: Snappy compression

## ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ

### Анализ CSV файла:
```bash
curl -X POST "/api/v1/performance/analyze" \
  -d '{"source": "/data/syn_csv/part1.csv"}'

# Результат: автоопределение CSV + рекомендации по индексам
```

### Анализ существующего хранилища:
```bash
curl -X POST "/api/v1/performance/analyze" \
  -d '{"source": "design_id:12345"}'

# Результат: анализ ClickHouse/PostgreSQL таблицы + оптимизации
```

### Применение оптимизаций:
```bash
curl -X POST "/api/v1/performance/optimize/analysis_123" \
  -d '{
    "recommendation_ids": ["partition", "index"],
    "dry_run": false,
    "confirm_application": true
  }'

# Результат: сохранение в optimization_recommendations для Модуля 4
```

### Интеграция с Модулем 4:
```python
# Модуль 4 автоматически использует рекомендации при создании DDL:
recommendations = db.query(OptimizationRecommendation).filter(
    OptimizationRecommendation.table_name == table_name
).all()

# Встраивание в DDL через _parse_optimization_recommendations:
optimizations = _parse_optimization_recommendations(recommendations, "clickhouse", columns)
# Результат: PARTITION BY toYYYYMM(sale_date) ORDER BY (sale_date, customer_id)
```

## ТЕСТИРОВАНИЕ

**Интеграционный тест:** `test_module3_integration.py`

**Проверяемые сценарии:**
1. ✅ Health check модуля
2. ✅ Анализ производительности различных источников
3. ✅ Применение оптимизаций (dry_run и реальное)
4. ✅ Интеграция с Модулем 5 (автоопределение + метрики)
5. ✅ Интеграция с Модулем 4 (хранилища + валидация DDL)
6. ✅ Валидация DDL-скриптов

**Запуск тестов:**
```bash
python test_module3_integration.py
```

## ПРОИЗВОДИТЕЛЬНОСТЬ

**Ожидаемые показатели:**
- Анализ CSV файла (100MB): < 5 секунд
- Генерация рекомендаций: < 2 секунд
- Валидация DDL: < 1 секунды
- Интеграция с Модулем 5: < 10 секунд (зависит от размера данных)

**Оптимизации:**
- Кэширование результатов анализа
- Асинхронная обработка через FastAPI
- Потоковая обработка больших файлов через Модуль 5

## ОГРАНИЧЕНИЯ И ИЗВЕСТНЫЕ ПРОБЛЕМЫ

1. **Зависимости:**
   - Требует работающий Модуль 5 для автоопределения
   - Требует доступ к БД для интеграции с Модулем 4

2. **Ограничения анализа:**
   - LLM анализ зависит от доступности OpenAI API
   - Анализ больших файлов (>10GB) может занимать значительное время

3. **Валидация DDL:**
   - Ограниченная проверка синтаксиса для HDFS
   - Требует существующие колонки для полной валидации

## ВЕРСИОННОСТЬ

- **Версия:** 1.0.0
- **Дата создания:** 2025-09-25
- **Статус:** Production Ready
- **Совместимость:** Python 3.11+, FastAPI, SQLAlchemy 2.0+
- **Интеграции:** Модуль 4 (100%), Модуль 5 (100%)

## ROADMAP

**Планируемые улучшения:**
1. Машинное обучение для предсказания оптимизаций
2. Автоматическое A/B тестирование оптимизаций
3. Интеграция с системами мониторинга (Prometheus, Grafana)
4. Поддержка дополнительных СУБД (MongoDB, Elasticsearch)
5. Веб-интерфейс для визуализации рекомендаций

---

**СТАТУС МОДУЛЯ:** 🚀 ПОЛНОСТЬЮ ФУНКЦИОНАЛЕН И ГОТОВ К ПРОДАКШЕНУ!

**Модуль 3 успешно интегрирован с модулями 4 и 5, поддерживает автоопределение типов данных, генерирует валидные DDL-скрипты и сохраняет рекомендации в формате, совместимом с существующей архитектурой.**
