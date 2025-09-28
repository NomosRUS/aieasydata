"""
ExecutionMonitor - Мониторинг выполнения мастер-пайплайнов
"""

import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class StageStatus:
    stage_name: str
    status: PipelineStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

@dataclass
class PipelineExecutionStatus:
    master_dag_id: str
    overall_status: PipelineStatus
    stages: Dict[str, StageStatus]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

class ExecutionMonitor:
    """Мониторинг выполнения мастер-пайплайнов"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.execution_history: Dict[str, PipelineExecutionStatus] = {}
    
    def monitor_master_pipeline(self, master_dag_id: str) -> PipelineExecutionStatus:
        """Мониторинг выполнения мастер-пайплайна"""
        try:
            # В реальной реализации здесь был бы запрос к Airflow API
            # Для демонстрации создаем базовый статус
            if master_dag_id not in self.execution_history:
                self.execution_history[master_dag_id] = PipelineExecutionStatus(
                    master_dag_id=master_dag_id,
                    overall_status=PipelineStatus.PENDING,
                    stages={}
                )
            
            return self.execution_history[master_dag_id]
            
        except Exception as e:
            logger.error(f"Failed to monitor pipeline {master_dag_id}: {str(e)}")
            raise
    
    def check_module_status(self, module: int, task_id: str) -> Dict[str, Any]:
        """Проверка статуса выполнения модуля"""
        try:
            # Проверяем health-check модуля
            health_endpoints = {
                1: "/api/v1/data-quality/health-check",
                2: "/api/v1/aggregation/health-check", 
                3: "/api/v1/performance/health-check",
                5: "/api/v1/metrics/health-check"
            }
            
            if module not in health_endpoints:
                return {"status": "error", "message": f"Unknown module: {module}"}
            
            url = f"{self.base_url}{health_endpoints[module]}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return {
                "module": module,
                "task_id": task_id,
                "status": "healthy",
                "response": response.json() if response.content else {},
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "module": module,
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def check_dag_status(self, dag_id: str) -> Dict[str, Any]:
        """Проверка статуса DAG'а"""
        # В реальной реализации здесь был бы запрос к Airflow API
        return {
            "dag_id": dag_id,
            "status": "running",
            "checked_at": datetime.now().isoformat()
        }
    
    def get_execution_history(self, master_dag_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получение истории выполнения"""
        if master_dag_id:
            if master_dag_id in self.execution_history:
                status = self.execution_history[master_dag_id]
                return [self._serialize_execution_status(status)]
            return []
        
        return [self._serialize_execution_status(status) for status in self.execution_history.values()]
    
    def _serialize_execution_status(self, status: PipelineExecutionStatus) -> Dict[str, Any]:
        """Сериализация статуса выполнения"""
        return {
            "master_dag_id": status.master_dag_id,
            "overall_status": status.overall_status.value,
            "stages_count": len(status.stages),
            "started_at": status.started_at.isoformat() if status.started_at else None,
            "completed_at": status.completed_at.isoformat() if status.completed_at else None,
            "estimated_completion": status.estimated_completion.isoformat() if status.estimated_completion else None
        }
