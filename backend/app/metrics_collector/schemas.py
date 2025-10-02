from pydantic import BaseModel
from typing import Optional, Literal

class ConnectionInfo(BaseModel):
    """Модель для передачи данных для подключения к БД."""
    db_type: Literal['clickhouse', 'postgres', 'file_system']
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    db_name: Optional[str] = None
    table_name: Optional[str] = None
    file_path: Optional[str] = None  # Для мониторинга файловой системы
    design_id: Optional[str] = None  # Для опциональной связи с проектом

class WarehouseMetrics(BaseModel):
    """Модель для возврата собранных метрик."""
    row_count: int
    size_in_bytes: int
    avg_query_duration_ms: Optional[float] = None
    p95_query_duration_ms: Optional[float] = None
    total_queries: Optional[int] = None
    # Дополнительные метрики для файловой системы
    file_count: Optional[int] = None
    avg_file_size: Optional[int] = None
    file_types: Optional[dict] = None
