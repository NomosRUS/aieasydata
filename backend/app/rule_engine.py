def recommend(profile: dict):
    rows = profile.get("est_rows", 0)
    ts_fields = profile.get("ts_fields", [])
    if rows >= 1_000_000 and ts_fields:
        return {
            "system": "clickhouse",
            "rationale": "Большой объём и есть поле времени → ClickHouse (MergeTree).",
            "partition_by": f"toYYYYMM({ts_fields[0]})",
            "order_by": ["dt"]
        }
    if rows < 1_000_000 and not ts_fields:
        return {
            "system": "postgres",
            "rationale": "Небольшой объём и нет явного времени → PostgreSQL.",
            "indexes": ["id"]
        }
    return {
        "system": "hdfs",
        "rationale": "Сырые/разнородные данные либо архив → HDFS (Parquet)."
    }
