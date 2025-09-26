from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
import os
from . import agent, analyzer, rule_engine, dag_compiler
from .warehouse_designer.router import router as warehouse_router
from .metrics_collector.router import router as metrics_router
from .performance_optimizer.router import router as performance_router
from .database import get_db, DataProfile
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from dotenv import load_dotenv
import requests

load_dotenv()

app = FastAPI(title="AiEasyData API (OpenAI)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(warehouse_router)
app.include_router(metrics_router)
app.include_router(performance_router)

class DSLModel(BaseModel):
    name: str
    mode: Literal["batch","stream"] = "batch"
    schedule: Optional[str] = "0 * * * *"
    source: Dict[str, Any]
    validation_rules: Optional[Dict[str, Any]] = None
    transforms: Optional[List[Dict[str, Any]]] = []
    target: Dict[str, Any]
    ddl_overrides: Optional[Dict[str, str]] = {}

class DataProfileResponse(BaseModel):
    id: int
    kind: Optional[str] = None
    source_path: str
    total_row_count: Optional[int] = None
    file_count: Optional[int] = None
    columns: Optional[List[Dict[str, Any]]] = None
    sample_data: Optional[List[Dict[str, Any]]] = None
    llm_summary: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DataInventoryResponse(BaseModel):
    total_count: int
    data: List[DataProfileResponse]

@app.get("/")
def root():
    return {
        "message": "AiEasyData API - Модули 3, 4, 5 готовы к работе!",
        "modules": {
            "module_3": "Оптимизация производительности",
            "module_4": "Проектирование хранилищ", 
            "module_5": "Мониторинг хранилищ"
        },
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "performance": "/api/v1/performance/health-check",
            "warehouse": "/api/v1/warehouse/design",
            "metrics": "/api/v1/metrics/health-check"
        }
    }

@app.get("/health")
def health():
    return {"ok": True, "uses": "OpenAI API", "model": os.environ.get("OPENAI_MODEL","gpt-4o-mini")}

@app.get("/api/data-inventory", response_model=DataInventoryResponse)
def get_data_inventory(db: Session = Depends(get_db)):
    """
    Retrieves a list of all data profiles from the database.
    """
    profiles = db.query(DataProfile).order_by(DataProfile.id.desc()).all()
    return {"total_count": len(profiles), "data": profiles}

class CreateDataProfileRequest(BaseModel):
    source_path: str

@app.post("/api/v1/data-profiles", response_model=DataProfileResponse, status_code=201)
def create_data_profile(request: CreateDataProfileRequest, db: Session = Depends(get_db)):
    """
    Creates a new data profile by analyzing the source data.
    """
    try:
        # Выполняем быстрый анализ для получения метаданных
        profile_data = analyzer.quick_profile({'source_path': request.source_path})
        
        # Создаем новый объект DataProfile
        new_profile = DataProfile(
            source_path=request.source_path,
            kind=profile_data.get('kind'),
            total_row_count=profile_data.get('total_row_count'),
            file_count=profile_data.get('file_count'),
            columns=profile_data.get('columns'),
            sample_data=profile_data.get('sample_data')
        )
        
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        
        return new_profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create data profile: {str(e)}")

@app.post("/api/analyze-profile/{profile_id}", response_model=DataProfileResponse)
def analyze_profile(profile_id: int, db: Session = Depends(get_db)):
    """
    Analyzes a single data profile using the LLM agent and saves the summary.
    """
    profile = db.query(DataProfile).filter(DataProfile.id == profile_id).first()
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Profile not found")

    # Правильное и надежное преобразование объекта SQLAlchemy в словарь
    profile_dict = {
        "id": profile.id,
        "source_path": profile.source_path,
        "kind": profile.kind,
        "total_row_count": profile.total_row_count,
        "file_count": profile.file_count,
        "columns": profile.columns,
        "sample_data": profile.sample_data,
        "llm_summary": profile.llm_summary,
        "error": profile.error,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }

    # Вызываем агент для анализа
    analysis_result = agent.analyze_data_profile(profile_dict)
    summary = analysis_result.get("content")

    # Сохраняем результат в базу данных
    profile.llm_summary = summary
    db.commit()
    db.refresh(profile)

    return profile


@app.post("/analyze")
def api_analyze(cfg: Dict[str, Any]):
    return analyzer.quick_profile(cfg)

@app.post("/recommend")
def api_recommend(profile: Dict[str, Any]):
    return rule_engine.recommend(profile)

@app.post("/ddl")
def api_ddl(payload: Dict[str, Any]):
    return agent.generate_ddl_with_explanation(payload)

@app.post("/dag/compile")
def api_dag_compile(dsl: DSLModel):
    path = dag_compiler.compile_dag(dsl.model_dump())
    return {"dag_path": path, "message": "DAG generated. Open Airflow UI to trigger."}

@app.post("/api/trigger-dag/{dag_id}")
def trigger_dag(dag_id: str):
    """
    Triggers a specific Airflow DAG using the Airflow REST API.
    """
    airflow_url = "http://airflow:8080"
    airflow_user = "admin"
    airflow_pass = "admin"

    api_url = f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns"

    try:
        response = requests.post(
            api_url,
            auth=(airflow_user, airflow_pass),
            json={"conf": {}},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        response.raise_for_status()  # Will raise an exception for 4xx/5xx status codes

        return {"message": f"DAG '{dag_id}' triggered successfully.", "details": response.json()}

    except requests.exceptions.RequestException as e:
        # This will catch connection errors, timeouts, etc.
        error_details = str(e)
        if e.response is not None:
            try:
                error_details = e.response.json().get('detail', e.response.text)
            except Exception:
                error_details = e.response.text
        raise HTTPException(
            status_code=502,  # Bad Gateway
            detail=f"Failed to trigger DAG '{dag_id}'. Could not connect to Airflow: {error_details}"
        )
