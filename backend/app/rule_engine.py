def recommend_basic_storage(profile: dict):
    """
    БАЗОВЫЕ рекомендации по выбору СУБД.
    Используется как общий компонент для всех модулей.
    Специализированные рекомендации реализованы в соответствующих модулях.
    """
    rows = profile.get("est_rows", 0)
    ts_fields = profile.get("ts_fields", [])
    file_size_mb = profile.get("file_size_mb", 0)
    
    # Базовые эвристики выбора СУБД
    if rows >= 1_000_000 and ts_fields:
        return {
            "recommended_system": "clickhouse",
            "rationale": "Большой объём данных с временными полями → ClickHouse для аналитики",
            "confidence": "high",
            "basic_optimizations": {
                "partition_by": f"toYYYYMM({ts_fields[0]})" if ts_fields else None,
                "order_by": ts_fields[:2] if len(ts_fields) >= 2 else ts_fields
            }
        }
    elif rows < 1_000_000 and file_size_mb < 100:
        return {
            "recommended_system": "postgresql",
            "rationale": "Небольшой объём данных → PostgreSQL для OLTP",
            "confidence": "high",
            "basic_optimizations": {
                "indexes": ["id"] if "id" in str(profile) else [],
                "constraints": ["primary_key", "foreign_keys"]
            }
        }
    else:
        return {
            "recommended_system": "hdfs",
            "rationale": "Большие или разнородные данные → HDFS для хранения",
            "confidence": "medium",
            "basic_optimizations": {
                "format": "parquet",
                "compression": "snappy"
            }
        }

# Обратная совместимость
def recommend(profile: dict):
    """Обратная совместимость со старым API."""
    result = recommend_basic_storage(profile)
    return {
        "system": result["recommended_system"],
        "rationale": result["rationale"]
    }
