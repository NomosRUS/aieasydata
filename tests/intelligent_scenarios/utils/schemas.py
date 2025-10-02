from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

class ScenarioResult(BaseModel):
    success: bool
    trajectory: List[Dict[str, Any]]
    error: Optional[str] = None

class Prerequisites(BaseModel):
    external_api: Optional[str] = None
    target_db: Optional[str] = None

class ScenarioStep(BaseModel):
    step: int
    description: str
    action: Literal[
        "external_api_call", 
        "module_api_call", 
        "format_validation", 
        "airflow_dag_trigger",
        "custom_script",
        "run_command",
        "parallel_execution",
        "airflow_api_call",
        "sleep"
    ]
    module: Optional[int] = None
    endpoint: Optional[str] = None
    method: Optional[Literal["GET", "POST", "PUT", "DELETE", "WEBSOCKET"]] = None
    params: Optional[Dict[str, Any]] = None
    payload: Optional[Any] = None  # Изменено с Dict на Any для поддержки строк
    headers: Optional[Dict[str, str]] = None
    expected_format: Optional[str] = None
    save_to: Optional[str] = None
    expected_response: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    expected_schema: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = 300
    dag_id: Optional[str] = None
    condition: Optional[str] = None
    duration: Optional[int] = None

class FinalCheck(BaseModel):
    type: str
    table: Optional[str] = None
    source: Optional[str] = None
    target: Optional[str] = None
    threshold: Optional[float] = None
    modules: Optional[List[int]] = None
    max_time: Optional[int] = None

class Validation(BaseModel):
    final_checks: List[FinalCheck]

class AITraining(BaseModel):
    goal: str
    success_pattern: str
    key_decisions: List[str]

class Scenario(BaseModel):
    scenario_id: str
    name: str
    description: str
    category: str
    prerequisites: Optional[Prerequisites] = None
    steps: List[ScenarioStep]
    validation: Optional[Validation] = None
    ai_training: AITraining
    execution_time_limit: Optional[int] = None
