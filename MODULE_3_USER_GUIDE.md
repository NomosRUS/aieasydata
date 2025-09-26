# РУКОВОДСТВО ПОЛЬЗОВАТЕЛЯ - МОДУЛЬ 3: ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ

## 🚀 БЫСТРЫЙ СТАРТ

### 1. Запуск сервера
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Проверка работоспособности
```bash
# Через браузер
http://localhost:8000/api/v1/performance/health-check

# Через curl
curl http://localhost:8000/api/v1/performance/health-check
```

### 3. API Документация
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 📊 ОСНОВНЫЕ СЦЕНАРИИ ИСПОЛЬЗОВАНИЯ

### Сценарий 1: Анализ CSV файла

**Шаг 1:** Запустить анализ
```bash
curl -X POST "http://localhost:8000/api/v1/performance/analyze" \
  -H "Content-Type: application/json" \
  -d '{"source": "path/to/your/file.csv"}'
```

**Ответ:**
```json
{
  "analysis_id": "analysis_20250925_175246_099426",
  "source": "file.csv",
  "source_type": "csv",
  "status": "completed",
  "current_metrics": {
    "data_size_bytes": 1048576,
    "row_count": 10000,
    "processing_time_ms": 150.5
  },
  "bottlenecks": [
    "Большое количество строк требует индексирования"
  ],
  "recommendations": [
    {
      "recommendation_type": "index",
      "target_table": "file",
      "ddl_script": "CREATE INDEX idx_file_id ON file(id);",
      "estimated_improvement": 25.0,
      "reasoning": "Индекс на колонке id ускорит поиск и фильтрацию"
    }
  ]
}
```

**Шаг 2:** Применить рекомендации (тестовый режим)
```bash
curl -X POST "http://localhost:8000/api/v1/performance/optimize/analysis_20250925_175246_099426" \
  -H "Content-Type: application/json" \
  -d '{
    "recommendation_ids": ["index"],
    "dry_run": true,
    "confirm_application": false
  }'
```

### Сценарий 2: Анализ существующего хранилища

**Шаг 1:** Получить список хранилищ
```bash
curl "http://localhost:8000/api/v1/performance/warehouses"
```

**Шаг 2:** Анализировать конкретное хранилище
```bash
curl -X POST "http://localhost:8000/api/v1/performance/analyze" \
  -H "Content-Type: application/json" \
  -d '{"source": "design_id:12345"}'
```

### Сценарий 3: Валидация DDL скрипта

```bash
curl -X POST "http://localhost:8000/api/v1/performance/validate-ddl" \
  -d "ddl_script=CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100));" \
  -d "target_db_type=postgres"
```

**Ответ:**
```json
{
  "valid": true,
  "errors": [],
  "target_db_type": "postgres",
  "ddl_script": "CREATE TABLE users..."
}
```

---

## 🔧 ПОДДЕРЖИВАЕМЫЕ ИСТОЧНИКИ ДАННЫХ

### Файлы:
- ✅ **CSV** - автоопределение разделителей (`,`, `;`, `\t`)
- ✅ **JSON** - поддержка JSON и JSON Lines
- ✅ **XML** - автоопределение тегов записей
- ✅ **Parquet** - прямая поддержка

### Базы данных:
- ✅ **PostgreSQL** - строки подключения `postgresql://user:pass@host:port/db`
- ✅ **ClickHouse** - строки подключения `clickhouse://host:port/db`

### Директории:
- ✅ **Смешанные форматы** - анализ доминирующего типа файлов
- ✅ **Большие объемы** - оптимизированная обработка >1GB

### Существующие хранилища:
- ✅ **Из Модуля 4** - анализ по `design_id:xxx`

---

## 🛠️ ТИПЫ РЕКОМЕНДАЦИЙ

### 1. PARTITION - Партиционирование
**Когда применяется:** Таблицы > 1M строк

**ClickHouse:**
```sql
PARTITION BY toYYYYMM(sale_date)
```

**PostgreSQL:**
```sql
PARTITION BY RANGE (sale_date)
```

**HDFS:**
```sql
PARTITIONED BY (year_month)
```

### 2. INDEX - Индексирование
**Когда применяется:** Часто запрашиваемые колонки

**PostgreSQL:**
```sql
CREATE INDEX idx_table_column ON table(column);
```

### 3. COMPRESSION - Сжатие
**Когда применяется:** Данные > 100MB

**ClickHouse:**
```sql
ALTER TABLE table MODIFY SETTING compress_block_size = 65536;
```

**HDFS:**
```sql
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression'='snappy')
```

### 4. ORDER_BY - Сортировка (ClickHouse)
**Когда применяется:** Оптимизация запросов с фильтрацией

```sql
ORDER BY (date_column, id_column)
```

### 5. RESTRUCTURE - Реструктуризация
**Когда применяется:** Неэффективный формат данных

**Пример:** Конвертация CSV → Parquet для больших файлов

---

## 📋 API REFERENCE

### Основные Endpoints

#### POST /api/v1/performance/analyze
Анализ производительности источника данных

**Параметры:**
```json
{
  "source": "string",                    // Обязательно
  "source_type": "csv|json|xml|...",     // Опционально (автоопределение)
  "performance_requirements": {},        // Опционально
  "constraints": {},                     // Опционально
  "target_db_type": "clickhouse|postgres|hdfs"  // Опционально
}
```

#### GET /api/v1/performance/analysis/{analysis_id}
Получение результатов анализа

#### POST /api/v1/performance/optimize/{analysis_id}
Применение оптимизаций

**Параметры:**
```json
{
  "recommendation_ids": ["partition", "index"],  // Типы рекомендаций
  "dry_run": true,                              // Тестовый режим
  "confirm_application": false                   // Подтверждение применения
}
```

#### GET /api/v1/performance/recommendations/{table_name}
Получение рекомендаций для таблицы

#### GET /api/v1/performance/metrics/{source}
Получение метрик через Модуль 5

### Интеграционные Endpoints

#### POST /api/v1/performance/validate-ddl
Валидация DDL через Модуль 4

#### GET /api/v1/performance/warehouses
Список хранилищ из Модуля 4

#### GET /api/v1/performance/health-check
Проверка работоспособности

---

## 🔍 ДИАГНОСТИКА И ОТЛАДКА

### Проверка статуса модуля:
```bash
curl http://localhost:8000/api/v1/performance/health-check
```

**Ожидаемый ответ:**
```json
{
  "status": "ok",
  "module": "performance_optimizer",
  "version": "1.0.0",
  "integrations": {
    "module5_metrics": "ok",     // Модуль 5 доступен
    "database": "error"          // БД может быть недоступна
  },
  "capabilities": [
    "auto_detect_data_types",
    "performance_analysis",
    "optimization_recommendations",
    "ddl_generation",
    "module4_integration",
    "module5_integration"
  ]
}
```

### Частые проблемы:

**1. Сервер не запускается**
```bash
# Проверить зависимости
pip install -r requirements.txt

# Проверить порт
netstat -an | findstr :8000
```

**2. Модуль 5 недоступен**
- Убедитесь, что Модуль 5 запущен
- Проверьте URL в коде: `http://localhost:8000/api/v1/metrics/`

**3. База данных недоступна**
- Это не критично для базового функционала
- Для полной функциональности запустите PostgreSQL

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

### Документация:
- **Паспорт модуля:** `backend/app/performance_optimizer/MODULE_3_PASSPORT.md`
- **Техническое задание:** `Task/Задача_3_Оптимизация_производительности_ТЗ.md`
- **Отчет о завершении:** `MODULE_3_COMPLETION_REPORT.md`

### Тестирование:
- **Простой тест:** `python test_module3_simple.py`
- **Полный тест:** `python test_module3_integration.py`
- **API тест:** `python test_api_calls.py`

### Интеграция:
- **Модуль 4:** `backend/app/warehouse_designer/`
- **Модуль 5:** `backend/app/metrics_collector/`

---

## ✅ ЗАКЛЮЧЕНИЕ

Модуль 3 предоставляет мощные возможности для анализа и оптимизации производительности данных:

- 🔍 **Автоматический анализ** любых источников данных
- 🛠️ **Интеллектуальные рекомендации** по оптимизации
- 🔗 **Полная интеграция** с модулями 4 и 5
- 📊 **Поддержка всех СУБД** (ClickHouse, PostgreSQL, HDFS)
- 🚀 **Production ready** решение

**Начните использовать Модуль 3 уже сегодня для оптимизации ваших данных!**
