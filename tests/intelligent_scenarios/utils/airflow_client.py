import os
import requests
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class AirflowClient:
    """Клиент для интеграции с Apache Airflow API."""
    
    def __init__(
        self, 
        base_url: Optional[str] = None,
        username: str = "admin",
        password: str = "admin",
        timeout: int = 300
    ):
        self.base_url = base_url or os.getenv("AIRFLOW_URL", "http://localhost:8080")
        self.base_url = self.base_url.rstrip('/')
        self.auth = (username, password)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def trigger_dag(
        self, 
        dag_id: str, 
        conf: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = False
    ) -> Dict[str, Any]:
        """
        Запускает DAG в Airflow.
        
        Args:
            dag_id: Идентификатор DAG
            conf: Конфигурация для передачи в DAG
            wait_for_completion: Ждать завершения выполнения
            
        Returns:
            Результат запуска DAG
        """
        try:
            url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns"
            
            payload = {
                "dag_run_id": f"manual__{int(time.time())}",
                "execution_date": datetime.now().isoformat(),
                "conf": conf or {}
            }
            
            logger.info(f"Triggering DAG: {dag_id}")
            response = self.session.post(
                url, 
                json=payload, 
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                dag_run_data = response.json()
                dag_run_id = dag_run_data.get("dag_run_id")
                
                result = {
                    "success": True,
                    "dag_run_id": dag_run_id,
                    "dag_id": dag_id,
                    "execution_date": dag_run_data.get("execution_date"),
                    "state": dag_run_data.get("state", "running")
                }
                
                # Ожидание завершения если требуется
                if wait_for_completion and dag_run_id:
                    completion_result = self.wait_for_dag_completion(dag_id, dag_run_id)
                    result.update(completion_result)
                
                return result
            else:
                return {
                    "success": False,
                    "error": f"Failed to trigger DAG: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logger.error(f"Error triggering DAG {dag_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def wait_for_dag_completion(
        self, 
        dag_id: str, 
        dag_run_id: str, 
        max_wait_time: int = 1800
    ) -> Dict[str, Any]:
        """
        Ожидает завершения выполнения DAG.
        
        Args:
            dag_id: Идентификатор DAG
            dag_run_id: Идентификатор запуска DAG
            max_wait_time: Максимальное время ожидания в секундах
            
        Returns:
            Результат выполнения DAG
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = self.get_dag_run_status(dag_id, dag_run_id)
            
            if not status["success"]:
                return status
            
            state = status["state"]
            
            if state in ["success", "failed"]:
                # Получение детальной информации о задачах
                tasks_info = self.get_dag_run_tasks(dag_id, dag_run_id)
                
                return {
                    "success": state == "success",
                    "state": state,
                    "execution_time": time.time() - start_time,
                    "tasks": tasks_info.get("tasks", [])
                }
            
            logger.info(f"DAG {dag_id} still running, state: {state}")
            time.sleep(10)  # Проверка каждые 10 секунд
        
        return {
            "success": False,
            "error": "Timeout waiting for DAG completion",
            "state": "timeout"
        }
    
    def get_dag_run_status(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Получает статус выполнения DAG."""
        try:
            url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}"
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "state": data.get("state"),
                    "start_date": data.get("start_date"),
                    "end_date": data.get("end_date")
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get DAG status: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_dag_run_tasks(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Получает информацию о задачах DAG."""
        try:
            url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                tasks_data = response.json()
                
                tasks = []
                for task in tasks_data.get("task_instances", []):
                    tasks.append({
                        "task_id": task.get("task_id"),
                        "state": task.get("state"),
                        "start_date": task.get("start_date"),
                        "end_date": task.get("end_date"),
                        "duration": task.get("duration")
                    })
                
                return {
                    "success": True,
                    "tasks": tasks
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get tasks: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_dags_list(self) -> Dict[str, Any]:
        """Получает список всех DAG'ов."""
        try:
            url = f"{self.base_url}/api/v1/dags"
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                dags_data = response.json()
                
                dags = []
                for dag in dags_data.get("dags", []):
                    dags.append({
                        "dag_id": dag.get("dag_id"),
                        "is_active": dag.get("is_active"),
                        "is_paused": dag.get("is_paused"),
                        "description": dag.get("description")
                    })
                
                return {
                    "success": True,
                    "dags": dags
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get DAGs list: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def pause_dag(self, dag_id: str) -> Dict[str, Any]:
        """Приостанавливает DAG."""
        return self._toggle_dag(dag_id, is_paused=True)
    
    def unpause_dag(self, dag_id: str) -> Dict[str, Any]:
        """Возобновляет DAG."""
        return self._toggle_dag(dag_id, is_paused=False)
    
    def _toggle_dag(self, dag_id: str, is_paused: bool) -> Dict[str, Any]:
        """Изменяет состояние паузы DAG."""
        try:
            url = f"{self.base_url}/api/v1/dags/{dag_id}"
            
            payload = {"is_paused": is_paused}
            
            response = self.session.patch(
                url, 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "dag_id": dag_id,
                    "is_paused": is_paused
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to toggle DAG: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
