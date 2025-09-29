"""
Скрипт миграции данных к новой организационной структуре.
Переносит существующие данные в новую схему с разделением по базам данных.
"""

import os
import shutil
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd

from .paths import DataPaths

class DataMigration:
    """Класс для миграции данных к новой структуре."""
    
    def __init__(self):
        self.migration_log = []
        self.errors = []
        
    def log(self, message: str, level: str = "INFO"):
        """Логирование процесса миграции."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {level}: {message}"
        self.migration_log.append(log_entry)
        print(log_entry)
    
    def migrate_all(self):
        """Выполнить полную миграцию данных."""
        self.log("Начинаем миграцию к новой структуре данных")
        
        try:
            # 1. Создаем новую структуру директорий
            self.create_new_structure()
            
            # 2. Мигрируем существующие данные
            self.migrate_existing_data()
            
            # 3. Создаем метаданные
            self.create_metadata()
            
            # 4. Обновляем конфигурации модулей
            self.update_module_configs()
            
            # 5. Создаем резервные копии старых данных
            self.backup_old_structure()
            
            self.log("Миграция успешно завершена!")
            self.save_migration_report()
            
        except Exception as e:
            self.log(f"Ошибка миграции: {str(e)}", "ERROR")
            self.errors.append(str(e))
            raise
    
    def create_new_structure(self):
        """Создать новую структуру директорий."""
        self.log("Создаем новую структуру директорий")
        
        # Инициализируем базовые директории
        DataPaths.ensure_directories()
        
        # Создаем структуру для тестовых баз данных
        test_databases = ["test_analytics", "sales_db", "user_analytics"]
        
        for db_name in test_databases:
            DataPaths.ensure_directories(db_name)
            self.log(f"   Создана структура для БД: {db_name}")
        
        # Инициализируем метаданные
        DataPaths.init_metadata_db()
        self.log("   Инициализирована база метаданных")
    
    def migrate_existing_data(self):
        """Мигрировать существующие данные."""
        self.log("Мигрируем существующие данные")
        
        old_base = Path("data_landing_zone")  # Текущая структура
        
        # 1. Мигрируем сырые данные
        self.migrate_raw_data(old_base)
        
        # 2. Мигрируем агрегированные данные
        self.migrate_aggregated_data(old_base)
        
        # 3. Мигрируем очищенные данные (если есть)
        self.migrate_cleaned_data(old_base)
    
    def migrate_raw_data(self, old_base: Path):
        """Мигрировать сырые данные."""
        self.log("   Мигрируем сырые данные")
        
        # Существующие синтетические данные
        synthetic_dirs = ["syn_csv", "syn_json", "syn_xml"]
        
        for syn_dir in synthetic_dirs:
            old_path = old_base / syn_dir
            new_path = DataPaths.RAW_SYNTHETIC / syn_dir
            
            if old_path.exists():
                if new_path.exists():
                    shutil.rmtree(new_path)
                shutil.copytree(old_path, new_path)
                self.log(f"     Перенесен {syn_dir}")
                
                # Регистрируем в метаданных
                self.register_synthetic_data(syn_dir, new_path)
        
        # Отдельные файлы
        test_files = ["sale.csv", "test_customers.json"]
        for file_name in test_files:
            old_file = old_base / file_name
            new_file = DataPaths.RAW_UPLOADS / file_name
            
            if old_file.exists():
                new_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old_file, new_file)
                self.log(f"     Перенесен {file_name}")
                
                # Регистрируем в метаданных
                self.register_single_file(file_name, new_file)
    
    def migrate_aggregated_data(self, old_base: Path):
        """Мигрировать агрегированные данные."""
        self.log("   Мигрируем агрегированные данные")
        
        # Проверяем существующие агрегированные данные
        aggregated_sources = [
            old_base / "aggregated",
            Path("/aggregated"),  # Корневая папка aggregated
            old_base / "backend" / "data_landing_zone" / "aggregated"
        ]
        
        for source_path in aggregated_sources:
            if source_path.exists():
                self.migrate_aggregated_from_path(source_path)
    
    def migrate_aggregated_from_path(self, source_path: Path):
        """Мигрировать агрегированные данные из конкретного пути."""
        for item in source_path.iterdir():
            if item.is_dir():
                # Определяем целевую базу данных по имени
                database_name = self.determine_database_from_name(item.name)
                
                # Создаем путь в новой структуре
                new_path = DataPaths.get_database_intermediate_path(database_name, "aggregated") / item.name
                
                # Копируем данные
                if new_path.exists():
                    shutil.rmtree(new_path)
                shutil.copytree(item, new_path)
                
                self.log(f"     Перенесен {item.name} в БД {database_name}")
                
                # Регистрируем в метаданных
                self.register_aggregated_data(item.name, database_name, new_path)
    
    def migrate_cleaned_data(self, old_base: Path):
        """Мигрировать очищенные данные."""
        self.log("   Мигрируем очищенные данные")
        
        cleaned_path = old_base / "cleaned"
        if cleaned_path.exists():
            for item in cleaned_path.iterdir():
                if item.is_dir():
                    database_name = self.determine_database_from_name(item.name)
                    new_path = DataPaths.get_database_intermediate_path(database_name, "cleaned") / item.name
                    
                    if new_path.exists():
                        shutil.rmtree(new_path)
                    shutil.copytree(item, new_path)
                    
                    self.log(f"     Перенесены очищенные данные {item.name}")
    
    def determine_database_from_name(self, name: str) -> str:
        """Определить имя базы данных по имени файла/папки."""
        # Логика определения базы данных
        if "csv" in name.lower():
            return "sales_db"
        elif "json" in name.lower() or "user" in name.lower():
            return "user_analytics"
        elif "xml" in name.lower() or "order" in name.lower():
            return "order_analytics"
        else:
            return "test_analytics"
    
    def register_synthetic_data(self, syn_dir: str, path: Path):
        """Регистрировать синтетические данные в метаданных."""
        conn = sqlite3.connect(DataPaths.MAIN_METADATA_DB)
        cursor = conn.cursor()
        
        # Подсчитываем размер
        total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        
        # Определяем тип данных
        data_type = syn_dir.replace("syn_", "")
        database_name = self.determine_database_from_name(syn_dir)
        
        cursor.execute("""
        INSERT OR REPLACE INTO sources (id, database_name, name, type, original_path, size_mb)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (syn_dir, database_name, syn_dir, data_type, str(path), size_mb))
        
        conn.commit()
        conn.close()
    
    def register_single_file(self, file_name: str, path: Path):
        """Регистрировать отдельный файл в метаданных."""
        conn = sqlite3.connect(DataPaths.MAIN_METADATA_DB)
        cursor = conn.cursor()
        
        size_mb = path.stat().st_size / (1024 * 1024)
        file_type = path.suffix.replace(".", "")
        database_name = self.determine_database_from_name(file_name)
        
        cursor.execute("""
        INSERT OR REPLACE INTO sources (id, database_name, name, type, original_path, size_mb)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (file_name, database_name, file_name, file_type, str(path), size_mb))
        
        conn.commit()
        conn.close()
    
    def register_aggregated_data(self, item_name: str, database_name: str, path: Path):
        """Регистрировать агрегированные данные в метаданных."""
        conn = sqlite3.connect(DataPaths.MAIN_METADATA_DB)
        cursor = conn.cursor()
        
        # Регистрируем как процесс агрегации
        cursor.execute("""
        INSERT OR REPLACE INTO processes (id, source_id, database_name, type, status, stage)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (f"migration_{item_name}", item_name, database_name, "aggregation", "completed", "aggregated"))
        
        conn.commit()
        conn.close()
    
    def create_metadata(self):
        """Создать дополнительные метаданные."""
        self.log("Создаем метаданные")
        
        # Создаем конфигурацию автоочистки
        retention_config = {
            "temp_files_hours": 24,
            "intermediate_files_days": 7,
            "backup_files_days": 30,
            "log_files_days": 90
        }
        
        retention_file = DataPaths.METADATA_DIR / "backups" / "retention_policy.json"
        retention_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(retention_file, 'w') as f:
            json.dump(retention_config, f, indent=2)
        
        self.log("   Создана конфигурация автоочистки")
    
    def update_module_configs(self):
        """Обновить конфигурации модулей для использования новых путей."""
        self.log("Обновляем конфигурации модулей")
        
        # Создаем файл конфигурации для модулей
        module_config = {
            "data_paths": {
                "base_dir": str(DataPaths.BASE_DATA_DIR),
                "raw_data": str(DataPaths.RAW_DATA_DIR),
                "intermediate": str(DataPaths.INTERMEDIATE_DIR),
                "warehouses": str(DataPaths.WAREHOUSES_DIR),
                "metadata": str(DataPaths.METADATA_DIR)
            },
            "file_limits": {
                "max_file_size_mb": DataPaths.MAX_FILE_SIZE_MB,
                "auto_split": True
            },
            "cleanup": {
                "auto_cleanup_enabled": True,
                "temp_retention_hours": 24
            }
        }
        
        config_file = Path("/backend/app/config/data_config.json")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(module_config, f, indent=2)
        
        self.log("   Создана конфигурация модулей")
    
    def backup_old_structure(self):
        """Создать резервные копии старой структуры."""
        self.log("Создаем резервные копии старой структуры")
        
        backup_dir = DataPaths.METADATA_DIR / "backups" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем описание старой структуры
        old_structure = {
            "migration_date": datetime.now().isoformat(),
            "old_paths": {
                "data_landing_zone": "/data_landing_zone",
                "aggregated": "/aggregated",
                "backend_aggregated": "/backend/data_landing_zone/aggregated"
            },
            "migrated_items": len(self.migration_log),
            "errors": self.errors
        }
        
        with open(backup_dir / "migration_info.json", 'w') as f:
            json.dump(old_structure, f, indent=2)
        
        self.log(f"   Резервная копия создана: {backup_dir}")
    
    def save_migration_report(self):
        """Сохранить отчет о миграции."""
        report_file = DataPaths.METADATA_DIR / "exports" / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "migration_completed": datetime.now().isoformat(),
            "total_operations": len(self.migration_log),
            "errors_count": len(self.errors),
            "log": self.migration_log,
            "errors": self.errors,
            "new_structure": {
                "databases": DataPaths.get_database_list(),
                "base_path": str(DataPaths.BASE_DATA_DIR),
                "metadata_db": str(DataPaths.MAIN_METADATA_DB)
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Отчет о миграции сохранен: {report_file}")

def run_migration():
    """Запустить миграцию данных."""
    migration = DataMigration()
    migration.migrate_all()
    return migration

if __name__ == "__main__":
    run_migration()
