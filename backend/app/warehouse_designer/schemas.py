from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class DesignRequest(BaseModel):
    source_profile_id: int
    business_requirements: str
    analytics_requirements: Dict[str, Any]
    constraints: Dict[str, Any]

class ConfirmSelectionRequest(BaseModel):
    chosen_db: str
    accept_llm: bool = True
    notes: Optional[str] = None

class DesignStatusResponse(BaseModel):
    design_id: str
    status: str
    results: Optional[Dict[str, Any]] = None

class CreateResponse(BaseModel):
    status: str
    message: str

class LoadDataResponse(BaseModel):
    status: str
    message: str
    dag_id: str

class WarehouseInstanceResponse(BaseModel):
    id: int
    design_id: str
    target_db_type: str
    db_name: str
    table_name: str
    metrics: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MetricsResponse(BaseModel):
    table_sizes: List[Dict[str, Any]]
    row_counts: List[Dict[str, Any]]
