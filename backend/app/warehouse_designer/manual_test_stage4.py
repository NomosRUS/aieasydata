"""
Ручная диагностика этапа 4 согласно чек-листу ТЗ.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.warehouse_designer.main import generate_ddl, _parse_optimization_recommendations


def test_clickhouse_ddl_with_optimizations():
    """
    Тест: создать контекст с рекомендациями, запустить generate_ddl, 
    убедиться что DDL содержит PARTITION BY и ORDER BY.
    """
    print("=== Тест ClickHouse DDL с оптимизациями ===")
    
    context = {
        "data_profile": {
            "source_path": "/data/sales_data.csv",
            "columns": [
                {"column_name": "id", "column_type": "Int64"},
                {"column_name": "date", "column_type": "Date"},
                {"column_name": "amount", "column_type": "Float64"}
            ]
        },
        "optimization_recommendations": [
            {
                "recommendation_type": "partition",
                "recommendation_details": {"partition_by": "toYYYYMM(date)"}
            },
            {
                "recommendation_type": "order_by",
                "recommendation_details": {"columns": ["date", "id"]}
            }
        ]
    }
    
    try:
        ddl_result = generate_ddl(context, "clickhouse")
        print(f"Сгенерированный DDL:\n{ddl_result}")
        
        # Проверки
        checks = [
            ("PARTITION BY", "toYYYYMM" in ddl_result),
            ("ORDER BY", "ORDER BY" in ddl_result),
            ("CREATE TABLE", "CREATE TABLE" in ddl_result),
            ("MergeTree", "MergeTree" in ddl_result)
        ]
        
        for check_name, result in checks:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {check_name}")
        
        return all(result for _, result in checks)
        
    except Exception as e:
        print(f"[ERROR] Ошибка при генерации DDL: {e}")
        return False


def test_postgres_ddl_with_indexes():
    """
    Тест: создать контекст с индексами для PostgreSQL.
    """
    print("\n=== Тест PostgreSQL DDL с индексами ===")
    
    context = {
        "data_profile": {
            "source_path": "/data/users.json",
            "columns": [
                {"column_name": "id", "column_type": "Int64"},
                {"column_name": "email", "column_type": "String"},
                {"column_name": "created_at", "column_type": "Datetime"}
            ]
        },
        "optimization_recommendations": [
            {
                "recommendation_type": "index",
                "recommendation_details": {"columns": ["email", "created_at"]}
            }
        ]
    }
    
    try:
        ddl_result = generate_ddl(context, "postgres")
        print(f"Сгенерированный DDL:\n{ddl_result}")
        
        # Проверки
        checks = [
            ("CREATE TABLE", "CREATE TABLE" in ddl_result),
            ("CREATE INDEX", "CREATE INDEX" in ddl_result),
            ("email column", "email" in ddl_result),
            ("BIGINT type", "BIGINT" in ddl_result or "TEXT" in ddl_result)
        ]
        
        for check_name, result in checks:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {check_name}")
        
        return all(result for _, result in checks)
        
    except Exception as e:
        print(f"[ERROR] Ошибка при генерации DDL: {e}")
        return False


def test_empty_recommendations():
    """
    Тест: убедиться что без рекомендаций DDL все равно валидный.
    """
    print("\n=== Тест DDL без рекомендаций ===")
    
    context = {
        "data_profile": {
            "source_path": "/data/simple_table.csv",
            "columns": [
                {"column_name": "id", "column_type": "Int64"},
                {"column_name": "name", "column_type": "String"}
            ]
        },
        "optimization_recommendations": []  # Пустые рекомендации
    }
    
    try:
        ddl_result = generate_ddl(context, "clickhouse")
        print(f"Сгенерированный DDL:\n{ddl_result}")
        
        # Проверки базовой валидности
        checks = [
            ("CREATE TABLE", "CREATE TABLE" in ddl_result),
            ("ENGINE", "ENGINE" in ddl_result or "MergeTree" in ddl_result),
            ("Non-empty", len(ddl_result.strip()) > 0)
        ]
        
        for check_name, result in checks:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {check_name}")
        
        return all(result for _, result in checks)
        
    except Exception as e:
        print(f"[ERROR] Ошибка при генерации DDL: {e}")
        return False


def test_recommendation_parser():
    """
    Тест парсера рекомендаций отдельно.
    """
    print("\n=== Тест парсера рекомендаций ===")
    
    recommendations = [
        {
            "recommendation_type": "partition",
            "recommendation_details": {"partition_by": "toYYYYMM(date)"}
        },
        {
            "recommendation_type": "order_by",
            "recommendation_details": {"columns": ["date", "user_id"]}
        }
    ]
    
    result = _parse_optimization_recommendations(recommendations, "clickhouse")
    print(f"Результат парсинга: {result}")
    
    expected_keys = ["partition_by", "order_by"]
    checks = [
        ("partition_by присутствует", "partition_by" in result),
        ("order_by присутствует", "order_by" in result),
        ("partition_by корректен", result.get("partition_by") == "toYYYYMM(date)"),
        ("order_by корректен", result.get("order_by") == ["date", "user_id"])
    ]
    
    for check_name, check_result in checks:
        status = "[PASS]" if check_result else "[FAIL]"
        print(f"{status} {check_name}")
    
    return all(check_result for _, check_result in checks)


def main():
    """Запуск всех тестов диагностики."""
    print("=== Запуск диагностики этапа 4 (Генерация DDL) ===\n")
    
    tests = [
        ("ClickHouse с оптимизациями", test_clickhouse_ddl_with_optimizations),
        ("PostgreSQL с индексами", test_postgres_ddl_with_indexes),
        ("DDL без рекомендаций", test_empty_recommendations),
        ("Парсер рекомендаций", test_recommendation_parser)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[ERROR] Тест '{test_name}' завершился с ошибкой: {e}")
            results.append((test_name, False))
    
    print("\n" + "="*50)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nПройдено тестов: {passed}/{len(results)}")
    
    if passed == len(results):
        print("Все тесты пройдены! Этап 4 готов.")
        return True
    else:
        print("Есть проблемы, требующие исправления.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
