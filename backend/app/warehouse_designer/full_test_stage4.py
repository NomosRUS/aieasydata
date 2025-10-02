"""
Полный тест этапа 4 с вызовом LLM для генерации DDL.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
from app.warehouse_designer.main import generate_ddl

# Загружаем переменные окружения из .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))


def test_full_ddl_generation_clickhouse():
    """
    Полный тест генерации DDL для ClickHouse с вызовом LLM.
    """
    print("=== Полный тест ClickHouse DDL с LLM ===")
    
    context = {
        "data_profile": {
            "source_path": "/data/sales_analytics.csv",
            "columns": [
                {"column_name": "sale_id", "column_type": "Int64"},
                {"column_name": "sale_date", "column_type": "Date"},
                {"column_name": "customer_id", "column_type": "Int64"},
                {"column_name": "product_name", "column_type": "String"},
                {"column_name": "amount", "column_type": "Float64"},
                {"column_name": "region", "column_type": "String"}
            ]
        },
        "optimization_recommendations": [
            {
                "recommendation_type": "partition",
                "recommendation_details": {"partition_by": "toYYYYMM(sale_date)"}
            },
            {
                "recommendation_type": "order_by",
                "recommendation_details": {"columns": ["sale_date", "customer_id"]}
            }
        ]
    }
    
    try:
        ddl_result = generate_ddl(context, "clickhouse")
        print(f"Сгенерированный DDL:\n{ddl_result}")
        print("-" * 60)
        
        # Проверки содержимого DDL
        checks = [
            ("CREATE TABLE присутствует", "CREATE TABLE" in ddl_result),
            ("Имя таблицы корректно", "sales_analytics" in ddl_result),
            ("MergeTree движок", "MergeTree" in ddl_result),
            ("PARTITION BY добавлен", "PARTITION BY" in ddl_result and "toYYYYMM" in ddl_result),
            ("ORDER BY добавлен", "ORDER BY" in ddl_result),
            ("Колонки присутствуют", "sale_id" in ddl_result and "amount" in ddl_result),
            ("DDL не пустой", len(ddl_result.strip()) > 50)
        ]
        
        all_passed = True
        for check_name, result in checks:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {check_name}")
            if not result:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"[ERROR] Ошибка при генерации DDL: {e}")
        return False


def test_full_ddl_generation_postgres():
    """
    Полный тест генерации DDL для PostgreSQL с вызовом LLM.
    """
    print("\n=== Полный тест PostgreSQL DDL с LLM ===")
    
    context = {
        "data_profile": {
            "source_path": "/data/user_activity.json",
            "columns": [
                {"column_name": "user_id", "column_type": "Int64"},
                {"column_name": "email", "column_type": "String"},
                {"column_name": "last_login", "column_type": "Datetime"},
                {"column_name": "is_active", "column_type": "Boolean"},
                {"column_name": "registration_date", "column_type": "Date"}
            ]
        },
        "optimization_recommendations": [
            {
                "recommendation_type": "index",
                "recommendation_details": {"columns": ["email", "last_login"]}
            }
        ]
    }
    
    try:
        ddl_result = generate_ddl(context, "postgres")
        print(f"Сгенерированный DDL:\n{ddl_result}")
        print("-" * 60)
        
        # Проверки содержимого DDL
        checks = [
            ("CREATE TABLE присутствует", "CREATE TABLE" in ddl_result),
            ("Имя таблицы корректно", "user_activity" in ddl_result),
            ("CREATE INDEX добавлен", "CREATE INDEX" in ddl_result),
            ("Индекс на email", "email" in ddl_result),
            ("PostgreSQL типы", "BIGINT" in ddl_result or "TEXT" in ddl_result),
            ("BOOLEAN тип", "BOOLEAN" in ddl_result),
            ("DDL не пустой", len(ddl_result.strip()) > 50)
        ]
        
        all_passed = True
        for check_name, result in checks:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {check_name}")
            if not result:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"[ERROR] Ошибка при генерации DDL: {e}")
        return False


def test_ddl_without_optimizations():
    """
    Тест генерации DDL без рекомендаций оптимизации.
    """
    print("\n=== Тест DDL без оптимизаций ===")
    
    context = {
        "data_profile": {
            "source_path": "/data/simple_log.csv",
            "columns": [
                {"column_name": "timestamp", "column_type": "Datetime"},
                {"column_name": "level", "column_type": "String"},
                {"column_name": "message", "column_type": "String"}
            ]
        },
        "optimization_recommendations": []  # Пустые рекомендации
    }
    
    try:
        ddl_result = generate_ddl(context, "clickhouse")
        print(f"Сгенерированный DDL:\n{ddl_result}")
        print("-" * 60)
        
        # Проверки базовой валидности
        checks = [
            ("CREATE TABLE присутствует", "CREATE TABLE" in ddl_result),
            ("MergeTree движок", "MergeTree" in ddl_result),
            ("Колонки присутствуют", "timestamp" in ddl_result and "message" in ddl_result),
            ("ORDER BY по умолчанию", "ORDER BY" in ddl_result),  # Должен быть дефолтный ORDER BY
            ("DDL валидный", len(ddl_result.strip()) > 30)
        ]
        
        all_passed = True
        for check_name, result in checks:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {check_name}")
            if not result:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"[ERROR] Ошибка при генерации DDL: {e}")
        return False


def test_api_key_availability():
    """
    Проверка доступности API ключа OpenAI.
    """
    print("=== Проверка API ключа ===")
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[FAIL] OPENAI_API_KEY не найден в переменных окружения")
        return False
    
    if len(api_key) < 10:
        print("[FAIL] OPENAI_API_KEY слишком короткий")
        return False
    
    print(f"[PASS] OPENAI_API_KEY найден (длина: {len(api_key)} символов)")
    
    # Проверяем базовый URL если есть
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        print(f"[INFO] OPENAI_BASE_URL: {base_url}")
    
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    print(f"[INFO] Используемая модель: {model}")
    
    return True


def main():
    """Запуск полных тестов с LLM."""
    print("=== Полное тестирование этапа 4 с LLM ===\n")
    
    # Сначала проверяем API ключ
    if not test_api_key_availability():
        print("\n[ERROR] Невозможно запустить тесты без API ключа OpenAI")
        print("Убедитесь, что файл .env содержит OPENAI_API_KEY")
        return False
    
    print()
    
    tests = [
        ("ClickHouse DDL с оптимизациями", test_full_ddl_generation_clickhouse),
        ("PostgreSQL DDL с индексами", test_full_ddl_generation_postgres),
        ("DDL без рекомендаций", test_ddl_without_optimizations)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[ERROR] Тест '{test_name}' завершился с ошибкой: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*60)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ ПОЛНОГО ТЕСТИРОВАНИЯ:")
    print("="*60)
    
    passed = 0
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nПройдено тестов: {passed}/{len(results)}")
    
    if passed == len(results):
        print("\nВсе полные тесты пройдены! Этап 4 полностью функционален с LLM.")
        return True
    else:
        print("\nЕсть проблемы в работе с LLM, требующие внимания.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
