# 🚀 AiEasyData - Руководство для новичков

## 📖 Описание проекта

**AiEasyData** - это MVP ИИ-ассистента для автоматизации ETL-задач. Система может подключаться к источникам данных, анализировать их структуру, предлагать оптимальные решения для хранения и автоматически строить ETL-пайплайны.

## 🏗️ Архитектура системы

- **Backend:** FastAPI (Python)
- **Frontend:** React (Vite) 
- **Оркестрация:** Apache Airflow
- **БД:** PostgreSQL (метаданные), ClickHouse (данные), HDFS
- **Инфраструктура:** Docker Compose

## 📥 Как скачать проект

### 1. Клонирование репозитория

```bash
git clone https://github.com/NomosRUS/aieasydata.git
cd aieasydata
```

### 2. Переключение на рабочую ветку

```bash
git checkout feature/warehouse-design3
```

## 📁 Структура проекта и расположение модулей

```
AiEasyData_Skeleton_OpenAI/
├── backend/app/                    # Основное приложение FastAPI
│   ├── main.py                     # Главный файл приложения
│   ├── data_validator/             # 📦 МОДУЛЬ 1: Валидация и очистка данных
│   │   ├── main.py                 # Координатор валидации
│   │   ├── router.py               # API endpoints (12 штук)
│   │   ├── validator.py            # Базовая валидация
│   │   ├── quality_assessor.py     # Оценка качества данных
│   │   ├── anomaly_detector.py     # Анализ аномалий
│   │   ├── homogeneity_checker.py  # Проверка однородности файлов
│   │   ├── data_cleaner.py         # Автоматическая очистка
│   │   ├── storage_recommender.py  # Рекомендации по хранению
│   │   └── MODULE_1_PASSPORT.md    # Документация модуля
│   │
│   ├── data_aggregator/            # 📦 МОДУЛЬ 2: Агрегация и обогащение
│   │   ├── main.py                 # Координатор агрегации
│   │   ├── router.py               # API endpoints (15 штук)
│   │   ├── data_source_collector.py # Подключение к источникам
│   │   ├── custom_dataset_builder.py # Кастомные наборы данных
│   │   ├── aggregation_engine.py   # Движок агрегаций
│   │   └── MODULE_2_PASSPORT.md    # Документация модуля
│   │
│   ├── performance_optimizer/      # 📦 МОДУЛЬ 3: Оптимизация производительности
│   │   ├── main.py                 # Координатор оптимизации
│   │   ├── router.py               # API endpoints (12 штук)
│   │   ├── analyzer.py             # Анализ производительности
│   │   ├── optimizer.py            # Генератор оптимизаций
│   │   └── MODULE_3_PASSPORT.md    # Документация модуля
│   │
│   ├── warehouse_designer/         # 📦 МОДУЛЬ 4: Проектирование хранилищ
│   │   ├── main.py                 # Координатор проектирования
│   │   ├── router.py               # API endpoints
│   │   ├── analyzer.py             # Анализ данных
│   │   └── MODULE_4_PASSPORT.md    # Документация модуля
│   │
│   ├── metrics_collector/          # 📦 МОДУЛЬ 5: Мониторинг хранилищ
│   │   ├── main.py                 # Координатор мониторинга
│   │   ├── router.py               # API endpoints
│   │   ├── data_type_detector.py   # Автоопределение типов данных
│   │   └── MODULE_5_PASSPORT.md    # Документация модуля
│   │
│   └── shared/                     # Общие компоненты
│       ├── schemas.py              # Общие модели данных
│       └── database.py             # Подключение к БД
│
├── ui/                             # Frontend React приложение
│   ├── src/
│   │   ├── App.jsx                 # Главный компонент
│   │   └── main.jsx                # Точка входа
│   ├── index.html                  # HTML шаблон
│   └── package.json                # Зависимости frontend
│
├── airflow/                        # Apache Airflow
│   ├── dags/                       # DAG файлы
│   └── requirements.txt            # Зависимости Airflow
│
├── tests/                          # Тесты
│   ├── test_module1_integration.py # Интеграционный тест модуля 1
│   ├── game_test_module1_raw_data.py # Игровой тест модуля 1
│   └── ...                         # Другие тесты
│
├── data_landing_zone/              # Зона данных
│   ├── raw/                        # Исходные данные
│   ├── cleaned/                    # Очищенные данные
│   ├── aggregated/                 # Агрегированные данные
│   ├── syn_csv/                    # Тестовые CSV файлы (13 файлов)
│   ├── syn_json/                   # Тестовые JSON файлы (32 файла)
│   └── syn_xml/                    # Тестовые XML файлы (17 файлов)
│
├── docker-compose.yml              # Конфигурация Docker
├── requirements.txt                # Python зависимости
└── README.md                       # Основная документация
```

## 🐳 Как поднять контейнер

### 1. Убедитесь, что Docker установлен

```bash
docker --version
docker-compose --version
```

### 2. Запуск всех сервисов

```bash
# Запуск в фоновом режиме
docker-compose up -d

# Или с выводом логов
docker-compose up
```

### 3. Проверка статуса контейнеров

```bash
docker-compose ps
```

Должны быть запущены следующие сервисы:
- `aie_api` - Основное FastAPI приложение
- `aie_postgres` - PostgreSQL база данных
- `aie_clickhouse` - ClickHouse база данных
- `aie_airflow` - Apache Airflow (опционально)

### 4. Остановка сервисов

```bash
docker-compose down
```

## 🌐 Доступ к API и интерфейсам

### Основные URL:

| Сервис | URL | Описание |
|--------|-----|----------|
| **FastAPI API** | http://localhost:8000 | Основное API приложения |
| **Swagger UI** | http://localhost:8000/docs | Интерактивная документация API |
| **ReDoc** | http://localhost:8000/redoc | Альтернативная документация API |
| **React UI** | http://localhost:3000 | Web интерфейс (если запущен) |
| **Airflow** | http://localhost:8080 | Интерфейс Airflow (если запущен) |

### Доступ к базам данных:

| База данных | Хост | Порт | Пользователь | Пароль |
|-------------|------|------|--------------|--------|
| **PostgreSQL** | localhost | 5432 | postgres | postgres |
| **ClickHouse** | localhost | 8123 | default | (пустой) |

## 🧪 Проверка работоспособности модулей

### 📦 МОДУЛЬ 1: Валидация и очистка данных

**Базовая проверка:**
```bash
curl -X GET "http://localhost:8000/api/v1/data-quality/health-check"
```

**Валидация файла:**
```bash
curl -X POST "http://localhost:8000/api/v1/data-quality/validate-file?file_path=/data/raw/sales.csv" \
  -H "Content-Type: application/json" \
  -d '{"validation_options": {"check_duplicates": true, "detect_anomalies": true}}'
```

**Проверка однородности файлов:**
```bash
curl -X POST "http://localhost:8000/api/v1/data-quality/check-homogeneity" \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "/data/syn_csv", "auto_separate": true}'
```

**Интеграционный тест:**
```bash
python tests/test_module1_integration.py
```

### 📦 МОДУЛЬ 2: Агрегация и обогащение

**Базовая проверка:**
```bash
curl -X GET "http://localhost:8000/api/v1/aggregation/health-check"
```

**Получение источников данных:**
```bash
curl -X GET "http://localhost:8000/api/v1/aggregation/sources"
```

**Создание кастомного набора данных:**
```bash
curl -X POST "http://localhost:8000/api/v1/aggregation/custom-dataset" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "test_dataset",
    "sources": [{"source_id": "csv_source", "selected_columns": ["id", "name"]}],
    "join_strategy": "concat",
    "limit": 100
  }'
```

### 📦 МОДУЛЬ 3: Оптимизация производительности

**Базовая проверка:**
```bash
curl -X GET "http://localhost:8000/api/v1/performance/health-check"
```

**Анализ производительности:**
```bash
curl -X POST "http://localhost:8000/api/v1/performance/analyze" \
  -H "Content-Type: application/json" \
  -d '{"source": "/data/raw/sales.csv", "target_db": "clickhouse"}'
```

**Получение метрик через модуль 5:**
```bash
curl -X GET "http://localhost:8000/api/v1/performance/metrics/data_source"
```

### 📦 МОДУЛЬ 4: Проектирование хранилищ

**Базовая проверка:**
```bash
curl -X GET "http://localhost:8000/api/v1/warehouse/health-check"
```

**Создание хранилища:**
```bash
curl -X POST "http://localhost:8000/api/v1/warehouse/design" \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "/data/raw/sales.csv",
    "target_db": "clickhouse",
    "requirements": {"performance": "high", "storage_type": "analytical"}
  }'
```

**Интеграционный тест:**
```bash
python tests/test_module4_integration.py
```

### 📦 МОДУЛЬ 5: Мониторинг хранилищ

**Базовая проверка:**
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/health-check"
```

**Автоопределение типа данных:**
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/auto-detect?source=/data/syn_csv"
```

**Сбор метрик:**
```bash
curl -X POST "http://localhost:8000/api/v1/metrics/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "db_type": "file_system",
    "file_path": "/data/syn_csv"
  }'
```

**Комплексное тестирование:**
```bash
curl -X GET "http://localhost:8000/api/v1/metrics/comprehensive-test"
```

## 🎮 Игровые тесты

### Игровой тест модуля 1 (на реальных данных):
```bash
python tests/game_test_module1_raw_data.py
```

Этот тест проверяет:
- Валидацию файлов CSV, JSON, XML
- Проверку однородности 62+ файлов
- Анализ качества данных
- Рекомендации по хранению

## 🔧 Полезные команды

### Просмотр логов:
```bash
# Логи основного API
docker logs aie_api --tail 50

# Логи PostgreSQL
docker logs aie_postgres --tail 20

# Логи ClickHouse
docker logs aie_clickhouse --tail 20
```

### Перезапуск сервисов:
```bash
# Перезапуск только API
docker-compose restart api

# Перезапуск всех сервисов
docker-compose restart
```

### Подключение к базам данных:
```bash
# PostgreSQL
docker exec -it aie_postgres psql -U postgres -d aieasydata

# ClickHouse
docker exec -it aie_clickhouse clickhouse-client
```

## 🚨 Устранение неполадок

### Проблема: Контейнеры не запускаются
**Решение:**
```bash
docker-compose down
docker system prune -f
docker-compose up --build
```

### Проблема: API недоступен
**Решение:**
1. Проверьте статус: `docker-compose ps`
2. Посмотрите логи: `docker logs aie_api`
3. Перезапустите: `docker-compose restart api`

### Проблема: Базы данных недоступны
**Решение:**
1. Проверьте порты: `netstat -an | grep 5432`
2. Перезапустите БД: `docker-compose restart postgres clickhouse`

### Проблема: Тесты не проходят
**Решение:**
1. Убедитесь, что API запущен: `curl http://localhost:8000/docs`
2. Проверьте данные: `ls -la data_landing_zone/syn_csv/`
3. Увеличьте таймауты в тестах

## 📚 Дополнительные ресурсы

- **Swagger UI:** http://localhost:8000/docs - Полная документация API
- **Паспорта модулей:** Каждый модуль содержит файл `MODULE_X_PASSPORT.md` с детальной документацией
- **Тесты:** В папке `tests/` находятся примеры использования всех модулей

## 🎯 Быстрый старт

1. **Клонируйте репозиторий:** `git clone https://github.com/NomosRUS/aieasydata.git`
2. **Переключитесь на ветку:** `git checkout feature/warehouse-design3`
3. **Запустите контейнеры:** `docker-compose up -d`
4. **Проверьте API:** `curl http://localhost:8000/docs`
5. **Запустите тест:** `python tests/test_module1_integration.py`

**Готово! Система запущена и готова к использованию! 🚀**
