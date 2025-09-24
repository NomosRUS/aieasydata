from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..shared.schemas import WarehouseInstance
from . import main as metrics_service
from .schemas import ConnectionInfo, WarehouseMetrics

router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["Metrics Collector"],
)

@router.post("/collect", response_model=WarehouseMetrics)
def collect_and_store_metrics(conn_info: ConnectionInfo, db: Session = Depends(get_db)):
    """
    Собирает метрики с указанного хранилища и сохраняет их в БД.
    """
    try:
        # 1. Собрать метрики
        metrics_data = metrics_service.collect_metrics(conn_info)

        # 2. Если передан design_id, найти или создать запись для сохранения
        if conn_info.design_id:
            db_instance = db.query(WarehouseInstance).filter(WarehouseInstance.design_id == conn_info.design_id).first()

            if not db_instance:
                # Если экземпляр еще не создан, создаем его
                # Это потребует доп. информации, которую нужно будет передавать
                # Для простоты пока будем считать, что он должен существовать
                # TODO: Расширить логику для создания, если нужно
                raise HTTPException(status_code=404, detail=f"WarehouseInstance with design_id {conn_info.design_id} not found.")
            
            # Обновляем метрики
            db_instance.metrics = metrics_data
            db.commit()
            db.refresh(db_instance)

        # 3. Вернуть собранные метрики
        return WarehouseMetrics(**metrics_data)

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
