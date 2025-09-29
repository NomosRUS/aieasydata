"""
API роутер для управления сервисом автоматической очистки.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from .config import cleanup_service

logger = logging.getLogger(__name__)

# Создаем роутер
router = APIRouter(prefix="/api/v1/cleanup", tags=["cleanup"])

@router.get("/status")
async def get_cleanup_status():
    """Получить статус сервиса автоматической очистки."""
    try:
        stats = cleanup_service.get_stats()
        return {
            "status": "success",
            "cleanup_service": stats
        }
    except Exception as e:
        logger.error(f"Failed to get cleanup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_cleanup_service():
    """Запустить сервис автоматической очистки."""
    try:
        cleanup_service.start()
        return {
            "status": "success",
            "message": "Cleanup service started",
            "is_running": cleanup_service.is_running
        }
    except Exception as e:
        logger.error(f"Failed to start cleanup service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_cleanup_service():
    """Остановить сервис автоматической очистки."""
    try:
        cleanup_service.stop()
        return {
            "status": "success",
            "message": "Cleanup service stopped",
            "is_running": cleanup_service.is_running
        }
    except Exception as e:
        logger.error(f"Failed to stop cleanup service: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/manual-cleanup")
async def run_manual_cleanup():
    """Выполнить ручную очистку."""
    try:
        stats = cleanup_service.manual_cleanup()
        return {
            "status": "success",
            "message": "Manual cleanup completed",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Manual cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_cleanup_config():
    """Получить конфигурацию очистки."""
    try:
        return {
            "status": "success",
            "config": cleanup_service.config
        }
    except Exception as e:
        logger.error(f"Failed to get cleanup config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
