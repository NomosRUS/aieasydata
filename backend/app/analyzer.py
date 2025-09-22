def quick_profile(cfg: dict):
    """Minimal stub profiler: columns and hints; replace with real sampling."""
    sample = [{"dt":"2025-09-01","amount":100},{"dt":"2025-09-02","amount":120}]
    columns = [{"name":"dt","type":"Date"},{"name":"amount","type":"Int64"}]
    profile = {"columns": columns, "est_rows": 1_000_000, "ts_fields":["dt"], "sample": sample}
    return profile
