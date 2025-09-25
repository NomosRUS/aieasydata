from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List
import time
import requests

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

@router.post("/collect-by-design/{design_id}", response_model=WarehouseMetrics)
def collect_metrics_by_design_id(design_id: str, db: Session = Depends(get_db)):
    """
    Собирает метрики для хранилища по design_id из модуля 4.
    Автоматически определяет параметры подключения из WarehouseInstance.
    """
    try:
        # Найти экземпляр хранилища по design_id
        db_instance = db.query(WarehouseInstance).filter(WarehouseInstance.design_id == design_id).first()
        
        if not db_instance:
            raise HTTPException(status_code=404, detail=f"WarehouseInstance with design_id {design_id} not found.")
        
        # Создать ConnectionInfo на основе данных экземпляра
        conn_info = metrics_service.get_connection_info_from_warehouse_instance(
            design_id=design_id,
            db_type=db_instance.target_db_type
        )
        
        # Добавить table_name из экземпляра
        conn_info.table_name = db_instance.table_name
        
        # Собрать метрики
        metrics_data = metrics_service.collect_metrics(conn_info)
        
        # Обновить метрики в базе данных
        db_instance.metrics = metrics_data
        flag_modified(db_instance, 'metrics')
        db.commit()
        db.refresh(db_instance)
        
        return WarehouseMetrics(**metrics_data)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@router.get("/data-landing-zone", response_model=WarehouseMetrics)
def monitor_data_landing_zone(path: str = "/data/landing_zone"):
    """
    Мониторинг сырого хранилища данных (data_landing_zone).
    """
    try:
        conn_info = ConnectionInfo(
            db_type='file_system',
            file_path=path
        )
        
        metrics_data = metrics_service.collect_metrics(conn_info)
        return WarehouseMetrics(**metrics_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error monitoring data landing zone: {e}")

@router.get("/health-check")
def health_check():
    """
    Проверка работоспособности модуля мониторинга.
    """
    return {
        "status": "healthy",
        "module": "metrics_collector",
        "supported_db_types": ["clickhouse", "postgres", "file_system"],
        "version": "1.0"
    }

@router.get("/auto-detect")
def auto_detect_data_type(source: str):
    """
    Автоматически определяет тип данных и собирает метрики.
    Это главная функция для модуля 3 - она сама определит что перед ней.
    """
    try:
        result = metrics_service.auto_detect_and_collect_metrics(source)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-detection failed: {e}")

@router.get("/test-xml")
def test_xml_monitoring():
    """Тестирование мониторинга XML файлов из syn_xml."""
    try:
        conn_data = {
            "db_type": "file_system",
            "file_path": "/data/syn_xml"
        }
        
        start_time = time.time()
        metrics_data = metrics_service.collect_metrics(ConnectionInfo(**conn_data))
        analysis_time = time.time() - start_time
        
        return {
            "status": "success",
            "analysis_time_seconds": analysis_time,
            "metrics": metrics_data,
            "message": f"XML мониторинг: {metrics_data.get('file_count', 0)} файлов, {metrics_data.get('row_count', 0):,} записей"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"XML monitoring failed: {e}")

@router.get("/test-json")
def test_json_monitoring():
    """Тестирование мониторинга JSON файлов из syn_json."""
    try:
        conn_data = {
            "db_type": "file_system",
            "file_path": "/data/syn_json"
        }
        
        start_time = time.time()
        metrics_data = metrics_service.collect_metrics(ConnectionInfo(**conn_data))
        analysis_time = time.time() - start_time
        
        return {
            "status": "success",
            "analysis_time_seconds": analysis_time,
            "metrics": metrics_data,
            "message": f"JSON мониторинг: {metrics_data.get('file_count', 0)} файлов, {metrics_data.get('row_count', 0):,} записей"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JSON monitoring failed: {e}")

@router.get("/test-real-databases")
def test_real_databases():
    """Тестирование подключения к реальным БД из модуля 4."""
    results = {}
    
    # Получаем список созданных таблиц из модуля 4
    try:
        instances_response = requests.get("http://localhost:8000/api/v1/warehouse/instances")
        if instances_response.status_code == 200:
            instances = instances_response.json()
            
            for instance in instances[:3]:  # Тестируем первые 3 экземпляра
                db_type = instance['target_db_type']
                table_name = instance['table_name']
                design_id = instance['design_id']
                
                if db_type in ['clickhouse', 'postgres']:
                    try:
                        # Создаем подключение к реальной БД
                        conn_info = metrics_service._get_real_db_connection_info(db_type, table_name)
                        
                        # Собираем метрики
                        start_time = time.time()
                        metrics = metrics_service.collect_metrics(conn_info)
                        analysis_time = time.time() - start_time
                        
                        results[f"{db_type}_{table_name}"] = {
                            "status": "success",
                            "design_id": design_id,
                            "analysis_time": analysis_time,
                            "metrics": metrics
                        }
                        
                    except Exception as e:
                        results[f"{db_type}_{table_name}"] = {
                            "status": "error",
                            "design_id": design_id,
                            "error": str(e)
                        }
        
        return {
            "status": "completed",
            "tested_databases": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real database testing failed: {e}")

@router.get("/comprehensive-test")
def comprehensive_test():
    """Комплексное тестирование всех возможностей модуля 5."""
    start_time = time.time()
    results = {
        "csv_test": None,
        "xml_test": None,
        "json_test": None,
        "real_db_test": None,
        "summary": {}
    }
    
    try:
        # 1. Тест CSV (syn_csv)
        try:
            csv_response = requests.get("http://localhost:8000/api/v1/metrics/data-landing-zone?path=/data/syn_csv")
            if csv_response.status_code == 200:
                results["csv_test"] = csv_response.json()
        except Exception as e:
            results["csv_test"] = {"error": str(e)}
        
        # 2. Тест XML (syn_xml)
        try:
            xml_response = requests.get("http://localhost:8000/api/v1/metrics/test-xml")
            if xml_response.status_code == 200:
                results["xml_test"] = xml_response.json()
        except Exception as e:
            results["xml_test"] = {"error": str(e)}
        
        # 3. Тест JSON (syn_json)
        try:
            json_response = requests.get("http://localhost:8000/api/v1/metrics/test-json")
            if json_response.status_code == 200:
                results["json_test"] = json_response.json()
        except Exception as e:
            results["json_test"] = {"error": str(e)}
        
        # 4. Тест реальных БД
        try:
            db_response = requests.get("http://localhost:8000/api/v1/metrics/test-real-databases")
            if db_response.status_code == 200:
                results["real_db_test"] = db_response.json()
        except Exception as e:
            results["real_db_test"] = {"error": str(e)}
        
        # Создаем сводку
        total_time = time.time() - start_time
        
        csv_files = results["csv_test"].get("file_count", 0) if results["csv_test"] and "error" not in results["csv_test"] else 0
        xml_files = results["xml_test"]["metrics"].get("file_count", 0) if results["xml_test"] and "error" not in results["xml_test"] else 0
        json_files = results["json_test"]["metrics"].get("file_count", 0) if results["json_test"] and "error" not in results["json_test"] else 0
        
        csv_rows = results["csv_test"].get("row_count", 0) if results["csv_test"] and "error" not in results["csv_test"] else 0
        xml_rows = results["xml_test"]["metrics"].get("row_count", 0) if results["xml_test"] and "error" not in results["xml_test"] else 0
        json_rows = results["json_test"]["metrics"].get("row_count", 0) if results["json_test"] and "error" not in results["json_test"] else 0
        
        results["summary"] = {
            "total_test_time": total_time,
            "total_files_analyzed": csv_files + xml_files + json_files,
            "total_rows_analyzed": csv_rows + xml_rows + json_rows,
            "csv_files": csv_files,
            "xml_files": xml_files,
            "json_files": json_files,
            "real_databases_tested": len(results["real_db_test"].get("results", {})) if results["real_db_test"] and "error" not in results["real_db_test"] else 0
        }
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive test failed: {e}")
