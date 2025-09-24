from pydantic import BaseModel
from typing import Optional, Literal

class ConnectionInfo(BaseModel):
    """Модель для передачи данных для подключения к БД."""
    db_type: Literal['clickhouse', 'postgres']
    host: str
    port: int
    user: str
    password: str
    db_name: str
    table_name: str
    design_id: Optional[str] = None  # Для опциональной связи с проектом

class WarehouseMetrics(BaseModel):
    """Модель для возврата собранных метрик."""
    row_count: int
    size_in_bytes: int
    avg_query_duration_ms: Optional[float] = None
    p95_query_duration_ms: Optional[float] = None
    total_queries: Optional[int] = None
