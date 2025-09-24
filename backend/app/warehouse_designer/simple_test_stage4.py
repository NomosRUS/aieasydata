"""
Упрощенная диагностика этапа 4 без зависимости от OpenAI API.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.warehouse_designer.main import (
    _extract_table_name, 
    _convert_columns_for_template,
    _parse_optimization_recommendations,
    _map_type_to_clickhouse,
    _map_type_to_postgres
)


def test_extract_table_name():
    """Тест извлечения имени таблицы."""
    print("=== Тест извлечения имени таблицы ===")
    
    test_cases = [
        ("/data/sales_data.csv", "sales_data"),
        ("/path/Sales-Data_2023.xlsx", "sales_data_2023"),
        ("/path/Sales Data 2023.json", "sales_data_2023"),
        ("/path/2023_sales.csv", "table_2023_sales"),
        ("", "table_")
    ]
    
    all_passed = True
    for input_path, expected in test_cases:
        result = _extract_table_name(input_path)
        passed = result == expected
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {input_path} -> {result} (ожидалось: {expected})")
        if not passed:
            all_passed = False
    
    return all_passed


def test_column_conversion():
    """Тест преобразования колонок."""
    print("\n=== Тест преобразования колонок ===")
    
    columns = [
        {"column_name": "id", "column_type": "Int64"},
        {"column_name": "name", "column_type": "String"},
        {"column_name": "is_active", "column_type": "Boolean"}
    ]
    
    # Тест для ClickHouse
    ch_result = _convert_columns_for_template(columns, "clickhouse")
    ch_expected = [
        {"name": "id", "type": "Int64"},
        {"name": "name", "type": "String"},
        {"name": "is_active", "type": "UInt8"}
    ]
    
    ch_passed = ch_result == ch_expected
    print(f"[{'PASS' if ch_passed else 'FAIL'}] ClickHouse колонки: {ch_result}")
    
    # Тест для PostgreSQL
    pg_result = _convert_columns_for_template(columns, "postgres")
    pg_expected = [
        {"name": "id", "type": "BIGINT"},
        {"name": "name", "type": "TEXT"},
        {"name": "is_active", "type": "BOOLEAN"}
    ]
    
    pg_passed = pg_result == pg_expected
    print(f"[{'PASS' if pg_passed else 'FAIL'}] PostgreSQL колонки: {pg_result}")
    
    return ch_passed and pg_passed


def test_optimization_parser():
    """Тест парсера рекомендаций оптимизации."""
    print("\n=== Тест парсера оптимизации ===")
    
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
    
    # Тест для ClickHouse
    ch_result = _parse_optimization_recommendations(recommendations, "clickhouse")
    ch_expected = {
        "partition_by": "toYYYYMM(date)",
        "order_by": ["date", "user_id"]
    }
    
    ch_passed = ch_result == ch_expected
    print(f"[{'PASS' if ch_passed else 'FAIL'}] ClickHouse оптимизации: {ch_result}")
    
    # Тест для PostgreSQL с индексами
    pg_recommendations = [
        {
            "recommendation_type": "index",
            "recommendation_details": {"columns": ["email", "created_at"]}
        }
    ]
    
    pg_result = _parse_optimization_recommendations(pg_recommendations, "postgres")
    pg_expected = {"indexes": ["email", "created_at"]}
    
    pg_passed = pg_result == pg_expected
    print(f"[{'PASS' if pg_passed else 'FAIL'}] PostgreSQL оптимизации: {pg_result}")
    
    return ch_passed and pg_passed


def test_type_mappings():
    """Тест маппинга типов данных."""
    print("\n=== Тест маппинга типов ===")
    
    test_types = ["String", "Int64", "Boolean", "Float64", "unknown_type"]
    
    print("ClickHouse маппинг:")
    ch_passed = True
    for orig_type in test_types:
        mapped = _map_type_to_clickhouse(orig_type)
        expected_fallback = mapped == "String" if orig_type == "unknown_type" else True
        print(f"  {orig_type} -> {mapped}")
        if orig_type == "Boolean" and mapped != "UInt8":
            ch_passed = False
    
    print("PostgreSQL маппинг:")
    pg_passed = True
    for orig_type in test_types:
        mapped = _map_type_to_postgres(orig_type)
        expected_fallback = mapped == "TEXT" if orig_type == "unknown_type" else True
        print(f"  {orig_type} -> {mapped}")
        if orig_type == "Int64" and mapped != "BIGINT":
            pg_passed = False
    
    status_ch = "[PASS]" if ch_passed else "[FAIL]"
    status_pg = "[PASS]" if pg_passed else "[FAIL]"
    print(f"{status_ch} ClickHouse маппинг")
    print(f"{status_pg} PostgreSQL маппинг")
    
    return ch_passed and pg_passed


def test_integration_flow():
    """Тест интеграционного потока без внешних зависимостей."""
    print("\n=== Тест интеграционного потока ===")
    
    # Имитируем контекст данных
    context = {
        "data_profile": {
            "source_path": "/data/sales_2023.csv",
            "columns": [
                {"column_name": "sale_id", "column_type": "Int64"},
                {"column_name": "sale_date", "column_type": "Date"},
                {"column_name": "amount", "column_type": "Float64"}
            ]
        },
        "optimization_recommendations": [
            {
                "recommendation_type": "partition",
                "recommendation_details": {"partition_by": "toYYYYMM(sale_date)"}
            },
            {
                "recommendation_type": "order_by",
                "recommendation_details": {"columns": ["sale_date", "sale_id"]}
            }
        ]
    }
    
    # Проверяем каждый шаг
    table_name = _extract_table_name(context["data_profile"]["source_path"])
    columns = _convert_columns_for_template(context["data_profile"]["columns"], "clickhouse")
    optimizations = _parse_optimization_recommendations(context["optimization_recommendations"], "clickhouse")
    
    checks = [
        ("Имя таблицы", table_name == "sales_2023"),
        ("Колонки преобразованы", len(columns) == 3),
        ("Партиционирование", optimizations.get("partition_by") == "toYYYYMM(sale_date)"),
        ("Сортировка", optimizations.get("order_by") == ["sale_date", "sale_id"])
    ]
    
    all_passed = True
    for check_name, result in checks:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    return all_passed


def main():
    """Запуск всех тестов."""
    print("=== Диагностика этапа 4 (без OpenAI API) ===\n")
    
    tests = [
        ("Извлечение имени таблицы", test_extract_table_name),
        ("Преобразование колонок", test_column_conversion),
        ("Парсер оптимизации", test_optimization_parser),
        ("Маппинг типов", test_type_mappings),
        ("Интеграционный поток", test_integration_flow)
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
        print("Все базовые тесты пройдены! Логика этапа 4 работает корректно.")
        print("Примечание: Для полного тестирования требуется настройка OpenAI API.")
        return True
    else:
        print("Есть проблемы в базовой логике, требующие исправления.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
