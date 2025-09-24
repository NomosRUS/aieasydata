from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import Any
from datetime import datetime

from ..database import get_db
from . import schemas, main as service
from ..shared.schemas import WarehouseDesign # Импортируем основную модель

router = APIRouter(
    prefix="/api/v1/warehouse",
    tags=["Warehouse Designer"],
)

CONFIRMABLE_STATES = {"awaiting_user_confirmation"}

@router.post("/design", response_model=schemas.DesignStatusResponse)
def design_warehouse(request: schemas.DesignRequest, db: Session = Depends(get_db)) -> Any:
    """Запускает процесс проектирования хранилища."""
    try:
        design_process = service.run_design_process(request, db)
        return {
            "design_id": design_process.design_id,
            "status": design_process.status,
            "results": design_process.results
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/design/{design_id}", response_model=schemas.DesignStatusResponse)
def get_design_status(design_id: str, db: Session = Depends(get_db)) -> Any:
    """Проверяет статус и получает результаты проектирования."""
    db_design = db.query(WarehouseDesign).filter(WarehouseDesign.design_id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail=f"Design with id {design_id} not found.")
    
    return {
        "design_id": db_design.design_id,
        "status": db_design.status,
        "results": db_design.results
    }

@router.post("/design/{design_id}/confirm", response_model=schemas.DesignStatusResponse)
def confirm_design_selection(
    design_id: str,
    payload: schemas.ConfirmSelectionRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Подтверждает выбор СУБД пользователем и фиксирует решение."""
    db_design = db.query(WarehouseDesign).filter(WarehouseDesign.design_id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail=f"Design with id {design_id} not found.")

    if db_design.status not in CONFIRMABLE_STATES:
        raise HTTPException(status_code=400, detail="Design is not awaiting confirmation.")

    results = db_design.results or {}
    llm_analysis = results.get("llm_analysis", {})

    final_choice = payload.chosen_db
    explanation = llm_analysis.get("summary", "")
    if not payload.accept_llm:
        explanation = payload.notes or "Пользователь выбрал собственный вариант."

    results["final_selection"] = {
        "chosen_db": final_choice,
        "accepted_llm": payload.accept_llm,
        "user_notes": payload.notes,
        "confirmation_timestamp": datetime.utcnow().isoformat(),
        "explanation": explanation,
    }

    try:
        context = results.get("context", {})
        ddl_script = service.generate_ddl(context, final_choice)
        results["ddl_script"] = ddl_script
        results["ddl_generated_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        results["ddl_error"] = str(e)

    db_design.results = results
    flag_modified(db_design, 'results')
    db_design.status = "ddl_generated" if "ddl_script" in results else "ddl_error"
    db_design.selected_db = final_choice
    db.commit()
    db.refresh(db_design)

    return {
        "design_id": db_design.design_id,
        "status": db_design.status,
        "results": db_design.results
    }

@router.post("/create/{design_id}", response_model=schemas.CreateResponse)
def create_tables(design_id: str, db: Session = Depends(get_db)):
    """
    Выполняет сгенерированный DDL-скрипт для создания таблиц в целевом хранилище.
    """
    db_design = db.query(WarehouseDesign).filter(WarehouseDesign.design_id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail="Design not found")

    if db_design.status != "ddl_generated":
        raise HTTPException(status_code=400, detail="DDL must be generated before creating warehouse.")
    
    results = db_design.results or {}
    ddl_script = results.get("ddl_script")
    if not ddl_script:
        raise HTTPException(status_code=400, detail="DDL script not found in design results.")
    
    selected_db = db_design.selected_db
    if not selected_db:
        raise HTTPException(status_code=400, detail="No database selected for DDL execution.")

    try:
        execution_result = service.execute_ddl_in_database(ddl_script, selected_db)
        message = ""

        if execution_result.get("success"):
            db_design.status = "tables_created"
            message = f"Tables successfully created in {selected_db}"

            # Создаем запись в WarehouseInstance после успешного создания таблиц
            from ..shared.schemas import WarehouseInstance
            existing_instance = db.query(WarehouseInstance).filter(WarehouseInstance.design_id == design_id).first()
            if not existing_instance:
                new_instance = WarehouseInstance(
                    design_id=design_id,
                    target_db_type=db_design.selected_db,
                    db_name="analytics",
                    table_name=results.get("etl_pipeline", {}).get("target_config", {}).get("table_name", "unknown"),
                    ddl_script=ddl_script,
                    metrics={}
                )
                db.add(new_instance)
        else:
            db_design.status = "creation_failed"
            message = f"Failed to create tables: {execution_result.get('error')}"

        results["ddl_execution"] = execution_result
        db_design.results = results
        flag_modified(db_design, 'results')
        db.commit()
        db.refresh(db_design)

        return {
            "status": "success" if execution_result.get("success") else "error",
            "message": message,
            "details": execution_result
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during DDL execution: {e}")

@router.post("/load-data/{design_id}", response_model=schemas.LoadDataResponse)
def load_data(design_id: str, db: Session = Depends(get_db)):
    """
    Генерирует и запускает ETL-пайплайн для загрузки данных.
    """
    db_design = db.query(WarehouseDesign).filter(WarehouseDesign.design_id == design_id).first()
    if not db_design:
        raise HTTPException(status_code=404, detail=f"Design with id {design_id} not found.")

    if db_design.status != "tables_created":
        raise HTTPException(status_code=400, detail="Tables must be created before loading data.")

    results = db_design.results or {}
    context = results.get("context", {})
    selected_db = db_design.selected_db

    if not selected_db:
        raise HTTPException(status_code=400, detail="Database not selected for this design.")

    try:
        pipeline_result = service.generate_etl_pipeline(design_id, context, selected_db)
        if not pipeline_result["success"]:
            raise Exception(f"Failed to generate ETL pipeline: {pipeline_result['error']}")

        results["etl_pipeline"] = pipeline_result
        db_design.status = "data_loading"
        results["data_loading_started_at"] = datetime.utcnow().isoformat()
        message = f"ETL pipeline '{pipeline_result['dag_id']}' created. Airflow will execute it shortly."

        db_design.results = results
        flag_modified(db_design, 'results')
        db.commit()
        db.refresh(db_design)

        return {
            "status": "created",
            "message": message,
            "dag_id": pipeline_result['dag_id'],
        }

    except Exception as e:
        results["etl_error"] = {"error": str(e), "occurred_at": datetime.utcnow().isoformat()}
        db_design.status = "loading_failed"
        db_design.results = results
        flag_modified(db_design, 'results')
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error setting up ETL pipeline: {str(e)}")


@router.get("/instances", response_model=list[schemas.WarehouseInstanceResponse])
def get_warehouse_instances(db: Session = Depends(get_db)):
    """Возвращает список всех созданных экземпляров хранилищ с их метриками."""
    from ..shared.schemas import WarehouseInstance
    instances = db.query(WarehouseInstance).all()
    return instances
