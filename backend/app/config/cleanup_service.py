"""
Сервис автоматической очистки временных файлов.
Настраивает периодическую очистку временных файлов и старых данных.
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
import threading
import json

from .paths import DataPaths

logger = logging.getLogger(__name__)

class CleanupService:
    """Сервис автоматической очистки временных файлов."""
    
    def __init__(self):
        self.is_running = False
        self.cleanup_thread = None
        self.stats = {
            "last_cleanup": None,
            "files_cleaned": 0,
            "space_freed_mb": 0.0,
            "cleanup_runs": 0
        }
        
        # Настройки очистки из конфигурации
        self.config = self._load_cleanup_config()
        
    def _load_cleanup_config(self) -> Dict[str, Any]:
        """Загрузить конфигурацию очистки."""
        try:
            config_file = DataPaths.METADATA_DIR / "backups" / "retention_policy.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cleanup config: {e}")
        
        # Конфигурация по умолчанию
        return {
            "temp_files_hours": 24,
            "intermediate_files_days": 7,
            "backup_files_days": 30,
            "log_files_days": 90,
            "auto_cleanup_enabled": True,
            "cleanup_interval_hours": 6
        }
    
    def start(self):
        """Запустить сервис автоматической очистки."""
        if self.is_running:
            logger.warning("Cleanup service is already running")
            return
        
        if not self.config.get("auto_cleanup_enabled", True):
            logger.info("Auto cleanup is disabled in configuration")
            return
        
        self.is_running = True
        
        # Настраиваем расписание
        interval_hours = self.config.get("cleanup_interval_hours", 6)
        schedule.every(interval_hours).hours.do(self._run_cleanup)
        
        # Запускаем в отдельном потоке
        self.cleanup_thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info(f"Cleanup service started with {interval_hours}h interval")
        
        # Выполняем первую очистку через 5 минут после запуска
        threading.Timer(300, self._run_cleanup).start()
    
    def stop(self):
        """Остановить сервис автоматической очистки."""
        self.is_running = False
        schedule.clear()
        logger.info("Cleanup service stopped")
    
    def _schedule_loop(self):
        """Основной цикл планировщика."""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"Error in cleanup schedule loop: {e}")
                time.sleep(300)  # При ошибке ждем 5 минут
    
    def _run_cleanup(self):
        """Выполнить очистку."""
        try:
            logger.info("Starting automatic cleanup")
            
            cleanup_stats = {
                "files_cleaned": 0,
                "space_freed_mb": 0.0,
                "start_time": datetime.now()
            }
            
            # 1. Очистка временных файлов
            self._cleanup_temp_files(cleanup_stats)
            
            # 2. Очистка старых промежуточных файлов
            self._cleanup_intermediate_files(cleanup_stats)
            
            # 3. Очистка старых резервных копий
            self._cleanup_backup_files(cleanup_stats)
            
            # 4. Очистка старых логов
            self._cleanup_log_files(cleanup_stats)
            
            # Обновляем статистику
            self.stats["last_cleanup"] = datetime.now().isoformat()
            self.stats["files_cleaned"] += cleanup_stats["files_cleaned"]
            self.stats["space_freed_mb"] += cleanup_stats["space_freed_mb"]
            self.stats["cleanup_runs"] += 1
            
            # Логируем результаты
            duration = (datetime.now() - cleanup_stats["start_time"]).total_seconds()
            logger.info(
                f"Cleanup completed: {cleanup_stats['files_cleaned']} files, "
                f"{cleanup_stats['space_freed_mb']:.2f} MB freed in {duration:.1f}s"
            )
            
            # Сохраняем статистику
            self._save_cleanup_stats()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def _cleanup_temp_files(self, stats: Dict):
        """Очистка временных файлов."""
        try:
            temp_hours = self.config.get("temp_files_hours", 24)
            cutoff_time = datetime.now() - timedelta(hours=temp_hours)
            
            if DataPaths.TEMP_DIR.exists():
                for temp_item in DataPaths.TEMP_DIR.iterdir():
                    if temp_item.is_dir():
                        # Проверяем время создания
                        creation_time = datetime.fromtimestamp(temp_item.stat().st_ctime)
                        if creation_time < cutoff_time:
                            size_mb = self._get_directory_size_mb(temp_item)
                            self._remove_directory(temp_item)
                            
                            stats["files_cleaned"] += 1
                            stats["space_freed_mb"] += size_mb
                            
                            logger.debug(f"Removed temp directory: {temp_item}")
            
        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")
    
    def _cleanup_intermediate_files(self, stats: Dict):
        """Очистка старых промежуточных файлов."""
        try:
            intermediate_days = self.config.get("intermediate_files_days", 7)
            cutoff_time = datetime.now() - timedelta(days=intermediate_days)
            
            if DataPaths.INTERMEDIATE_DIR.exists():
                for db_dir in DataPaths.INTERMEDIATE_DIR.iterdir():
                    if db_dir.is_dir():
                        for stage_dir in db_dir.iterdir():
                            if stage_dir.is_dir():
                                for source_dir in stage_dir.iterdir():
                                    if source_dir.is_dir():
                                        # Проверяем время последнего изменения
                                        mod_time = datetime.fromtimestamp(source_dir.stat().st_mtime)
                                        if mod_time < cutoff_time:
                                            size_mb = self._get_directory_size_mb(source_dir)
                                            self._remove_directory(source_dir)
                                            
                                            stats["files_cleaned"] += 1
                                            stats["space_freed_mb"] += size_mb
                                            
                                            logger.debug(f"Removed old intermediate data: {source_dir}")
            
        except Exception as e:
            logger.error(f"Error cleaning intermediate files: {e}")
    
    def _cleanup_backup_files(self, stats: Dict):
        """Очистка старых резервных копий."""
        try:
            backup_days = self.config.get("backup_files_days", 30)
            cutoff_time = datetime.now() - timedelta(days=backup_days)
            
            backup_dir = DataPaths.METADATA_DIR / "backups"
            if backup_dir.exists():
                for backup_item in backup_dir.iterdir():
                    if backup_item.is_dir() and backup_item.name.startswith("migration_"):
                        creation_time = datetime.fromtimestamp(backup_item.stat().st_ctime)
                        if creation_time < cutoff_time:
                            size_mb = self._get_directory_size_mb(backup_item)
                            self._remove_directory(backup_item)
                            
                            stats["files_cleaned"] += 1
                            stats["space_freed_mb"] += size_mb
                            
                            logger.debug(f"Removed old backup: {backup_item}")
            
        except Exception as e:
            logger.error(f"Error cleaning backup files: {e}")
    
    def _cleanup_log_files(self, stats: Dict):
        """Очистка старых лог файлов."""
        try:
            log_days = self.config.get("log_files_days", 90)
            cutoff_time = datetime.now() - timedelta(days=log_days)
            
            # Ищем лог файлы в разных местах
            log_patterns = ["*.log", "*.log.*"]
            search_dirs = [
                Path("logs"),
                Path("/var/log"),
                DataPaths.METADATA_DIR / "exports"
            ]
            
            for search_dir in search_dirs:
                if search_dir.exists():
                    for pattern in log_patterns:
                        for log_file in search_dir.glob(pattern):
                            if log_file.is_file():
                                mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                                if mod_time < cutoff_time:
                                    size_mb = log_file.stat().st_size / (1024 * 1024)
                                    log_file.unlink()
                                    
                                    stats["files_cleaned"] += 1
                                    stats["space_freed_mb"] += size_mb
                                    
                                    logger.debug(f"Removed old log file: {log_file}")
            
        except Exception as e:
            logger.error(f"Error cleaning log files: {e}")
    
    def _get_directory_size_mb(self, directory: Path) -> float:
        """Получить размер директории в MB."""
        try:
            total_size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
            return total_size / (1024 * 1024)
        except:
            return 0.0
    
    def _remove_directory(self, directory: Path):
        """Безопасно удалить директорию."""
        try:
            import shutil
            shutil.rmtree(directory)
        except Exception as e:
            logger.error(f"Failed to remove directory {directory}: {e}")
    
    def _save_cleanup_stats(self):
        """Сохранить статистику очистки."""
        try:
            stats_file = DataPaths.METADATA_DIR / "exports" / "cleanup_stats.json"
            stats_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save cleanup stats: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику очистки."""
        return {
            **self.stats,
            "is_running": self.is_running,
            "config": self.config
        }
    
    def manual_cleanup(self) -> Dict[str, Any]:
        """Выполнить ручную очистку."""
        logger.info("Manual cleanup requested")
        self._run_cleanup()
        return self.get_stats()

# Глобальный экземпляр сервиса очистки
cleanup_service = CleanupService()
