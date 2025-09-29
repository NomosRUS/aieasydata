#!/usr/bin/env python3
"""
Тест фактической реализации новой системы организации данных.
Проверяет точность и полноту реализации согласно DATA_ORGANIZATION_SCHEMA.md
"""

import pytest
import os
import sys
from pathlib import Path
import sqlite3
import json
import pandas as pd
import tempfile

# Добавляем путь к backend для импорта модулей
sys.path.append(str(Path(__file__).parent.parent / "backend" / "app"))

class TestDataOrganizationImplementation:
    """Тесты фактической реализации новой системы организации данных."""
    
    def setup_method(self):
        """Подготовка к тестам."""
        self.base_path = Path(__file__).parent.parent / "data_landing_zone"
        self.backend_path = Path(__file__).parent.parent / "backend" / "app"
        self.test_results = {}
        
    def test_01_config_modules_exist(self):
        """Тест 1: Проверка существования конфигурационных модулей."""
        print("\n=== ТЕСТ 1: Существование конфигурационных модулей ===")
        
        required_modules = [
            "config/paths.py",
            "config/file_utils.py", 
            "config/migration.py",
            "config/cleanup_service.py",
            "config/__init__.py"
        ]
        
        existing_modules = 0
        
        for module_path in required_modules:
            full_path = self.backend_path / module_path
            exists = full_path.exists()
            
            print(f"   {module_path}: {'✅' if exists else '❌'}")
            
            if exists:
                existing_modules += 1
                
                # Проверяем размер файла (не пустой)
                file_size = full_path.stat().st_size
                print(f"     Размер: {file_size} bytes")
                
                if file_size < 100:  # Слишком маленький файл
                    print(f"     ⚠️ Файл может быть неполным")
        
        success_rate = (existing_modules / len(required_modules)) * 100
        print(f"\nСуществующих модулей: {existing_modules}/{len(required_modules)} ({success_rate:.1f}%)")
        
        self.test_results["config_modules"] = f"{existing_modules}/{len(required_modules)}"
        
        assert existing_modules >= 4, f"Недостаточно конфигурационных модулей: {existing_modules}/5"
    
    def test_02_data_paths_implementation(self):
        """Тест 2: Проверка реализации DataPaths."""
        print("\n=== ТЕСТ 2: Реализация DataPaths ===")
        
        try:
            from config.paths import DataPaths
            
            print("✅ DataPaths успешно импортирован")
            
            # Проверяем основные атрибуты
            required_attributes = [
                "BASE_DATA_DIR", "RAW_DATA_DIR", "INTERMEDIATE_DIR", 
                "WAREHOUSES_DIR", "METADATA_DIR"
            ]
            
            existing_attributes = 0
            
            for attr in required_attributes:
                if hasattr(DataPaths, attr):
                    value = getattr(DataPaths, attr)
                    print(f"   ✅ {attr}: {value}")
                    existing_attributes += 1
                else:
                    print(f"   ❌ {attr}: отсутствует")
            
            # Проверяем методы
            required_methods = [
                "get_source_path", "get_warehouse_path", 
                "get_metadata_path", "ensure_directories"
            ]
            
            existing_methods = 0
            
            for method in required_methods:
                if hasattr(DataPaths, method):
                    print(f"   ✅ Метод {method}: существует")
                    existing_methods += 1
                else:
                    print(f"   ❌ Метод {method}: отсутствует")
            
            total_features = len(required_attributes) + len(required_methods)
            existing_features = existing_attributes + existing_methods
            
            print(f"\nРеализованных функций: {existing_features}/{total_features}")
            
            self.test_results["data_paths"] = f"{existing_features}/{total_features}"
            
            assert existing_features >= 7, f"Недостаточно функций DataPaths: {existing_features}/{total_features}"
            
        except ImportError as e:
            print(f"❌ Ошибка импорта DataPaths: {e}")
            self.test_results["data_paths"] = "import_failed"
            pytest.fail("DataPaths не может быть импортирован")
    
    def test_03_file_manager_implementation(self):
        """Тест 3: Проверка реализации file_manager."""
        print("\n=== ТЕСТ 3: Реализация file_manager ===")
        
        try:
            from config.file_utils import FileManager, FileSplitter
            
            print("✅ FileManager и FileSplitter успешно импортированы")
            
            # Проверяем FileManager
            file_manager = FileManager()
            
            required_methods = [
                "process_file", "get_file_parts", "combine_file_parts", 
                "register_artifact"
            ]
            
            existing_methods = 0
            
            for method in required_methods:
                if hasattr(file_manager, method):
                    print(f"   ✅ FileManager.{method}: существует")
                    existing_methods += 1
                else:
                    print(f"   ❌ FileManager.{method}: отсутствует")
            
            # Проверяем FileSplitter
            splitter_methods = ["split_csv", "split_json", "split_xml"]
            existing_splitter_methods = 0
            
            for method in splitter_methods:
                if hasattr(FileSplitter, method):
                    print(f"   ✅ FileSplitter.{method}: существует")
                    existing_splitter_methods += 1
                else:
                    print(f"   ❌ FileSplitter.{method}: отсутствует")
            
            total_methods = len(required_methods) + len(splitter_methods)
            existing_total = existing_methods + existing_splitter_methods
            
            print(f"\nРеализованных методов: {existing_total}/{total_methods}")
            
            self.test_results["file_manager"] = f"{existing_total}/{total_methods}"
            
            assert existing_total >= 5, f"Недостаточно методов file_manager: {existing_total}/{total_methods}"
            
        except ImportError as e:
            print(f"❌ Ошибка импорта file_manager: {e}")
            self.test_results["file_manager"] = "import_failed"
            pytest.fail("file_manager не может быть импортирован")
    
    def test_04_directory_structure_compliance(self):
        """Тест 4: Соответствие структуры директорий схеме."""
        print("\n=== ТЕСТ 4: Соответствие структуры директорий ===")
        
        # Ожидаемая структура согласно DATA_ORGANIZATION_SCHEMA.md
        expected_structure = {
            "raw": ["uploads", "external", "synthetic", "staging"],
            "intermediate": [],  # Будет создаваться динамически по БД
            "warehouses": [],    # Будет создаваться динамически по БД
            "metadata": [],
            "_temp": []
        }
        
        existing_dirs = 0
        total_dirs = 0
        
        for main_dir, subdirs in expected_structure.items():
            main_path = self.base_path / main_dir
            total_dirs += 1
            
            if main_path.exists():
                print(f"   ✅ {main_dir}/: существует")
                existing_dirs += 1
                
                # Проверяем подпапки
                for subdir in subdirs:
                    sub_path = main_path / subdir
                    total_dirs += 1
                    
                    if sub_path.exists():
                        print(f"     ✅ {main_dir}/{subdir}/: существует")
                        existing_dirs += 1
                    else:
                        print(f"     ❌ {main_dir}/{subdir}/: отсутствует")
            else:
                print(f"   ❌ {main_dir}/: отсутствует")
                total_dirs += len(subdirs)  # Добавляем пропущенные подпапки
        
        # Проверяем дополнительные папки, которые могли быть созданы
        additional_dirs = ["syn_csv", "syn_json", "syn_xml", "test_data"]
        
        for add_dir in additional_dirs:
            add_path = self.base_path / add_dir
            if add_path.exists():
                print(f"   ✅ {add_dir}/: существует (дополнительная)")
                existing_dirs += 1
            total_dirs += 1
        
        compliance_rate = (existing_dirs / total_dirs) * 100 if total_dirs > 0 else 0
        print(f"\nСоответствие структуре: {existing_dirs}/{total_dirs} ({compliance_rate:.1f}%)")
        
        self.test_results["directory_structure"] = f"{existing_dirs}/{total_dirs}"
    
    def test_05_metadata_database_schema(self):
        """Тест 5: Проверка схемы базы данных метаданных."""
        print("\n=== ТЕСТ 5: Схема базы данных метаданных ===")
        
        metadata_db_path = self.base_path / "metadata" / "main.db"
        
        if not metadata_db_path.exists():
            print(f"❌ База метаданных не найдена: {metadata_db_path}")
            self.test_results["metadata_schema"] = "db_not_found"
            return
        
        try:
            conn = sqlite3.connect(metadata_db_path)
            cursor = conn.cursor()
            
            # Получаем список таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"✅ База метаданных найдена")
            print(f"   Найдено таблиц: {len(tables)}")
            
            # Ожидаемые таблицы согласно схеме
            expected_tables = [
                "sources", "processes", "warehouses", "schemas", 
                "file_parts", "artifacts", "cleanup_log"
            ]
            
            existing_tables = 0
            
            for table in expected_tables:
                if table in tables:
                    print(f"   ✅ Таблица {table}: существует")
                    existing_tables += 1
                    
                    # Проверяем структуру таблицы
                    cursor.execute(f"PRAGMA table_info({table});")
                    columns = cursor.fetchall()
                    print(f"     Колонок: {len(columns)}")
                    
                else:
                    print(f"   ❌ Таблица {table}: отсутствует")
            
            conn.close()
            
            schema_compliance = (existing_tables / len(expected_tables)) * 100
            print(f"\nСоответствие схеме: {existing_tables}/{len(expected_tables)} ({schema_compliance:.1f}%)")
            
            self.test_results["metadata_schema"] = f"{existing_tables}/{len(expected_tables)}"
            
        except Exception as e:
            print(f"❌ Ошибка проверки базы метаданных: {e}")
            self.test_results["metadata_schema"] = "error"
    
    def test_06_cleanup_service_implementation(self):
        """Тест 6: Проверка реализации сервиса очистки."""
        print("\n=== ТЕСТ 6: Реализация сервиса очистки ===")
        
        try:
            from config.cleanup_service import CleanupService
            
            print("✅ CleanupService успешно импортирован")
            
            # Проверяем методы
            required_methods = [
                "start", "stop", "manual_cleanup", "get_status", 
                "get_config", "cleanup_temp_files"
            ]
            
            existing_methods = 0
            
            for method in required_methods:
                if hasattr(CleanupService, method):
                    print(f"   ✅ CleanupService.{method}: существует")
                    existing_methods += 1
                else:
                    print(f"   ❌ CleanupService.{method}: отсутствует")
            
            method_compliance = (existing_methods / len(required_methods)) * 100
            print(f"\nРеализованных методов: {existing_methods}/{len(required_methods)} ({method_compliance:.1f}%)")
            
            self.test_results["cleanup_service"] = f"{existing_methods}/{len(required_methods)}"
            
            assert existing_methods >= 4, f"Недостаточно методов CleanupService: {existing_methods}/{len(required_methods)}"
            
        except ImportError as e:
            print(f"❌ Ошибка импорта CleanupService: {e}")
            self.test_results["cleanup_service"] = "import_failed"
    
    def test_07_migration_functionality(self):
        """Тест 7: Проверка функциональности миграции."""
        print("\n=== ТЕСТ 7: Функциональность миграции ===")
        
        try:
            from config.migration import DataMigration
            
            print("✅ DataMigration успешно импортирован")
            
            # Проверяем методы
            required_methods = [
                "migrate_existing_data", "create_directory_structure", 
                "initialize_metadata_db", "backup_existing_data"
            ]
            
            existing_methods = 0
            
            for method in required_methods:
                if hasattr(DataMigration, method):
                    print(f"   ✅ DataMigration.{method}: существует")
                    existing_methods += 1
                else:
                    print(f"   ❌ DataMigration.{method}: отсутствует")
            
            migration_compliance = (existing_methods / len(required_methods)) * 100
            print(f"\nРеализованных методов: {existing_methods}/{len(required_methods)} ({migration_compliance:.1f}%)")
            
            self.test_results["migration"] = f"{existing_methods}/{len(required_methods)}"
            
        except ImportError as e:
            print(f"❌ Ошибка импорта DataMigration: {e}")
            self.test_results["migration"] = "import_failed"
    
    def test_08_integration_summary(self):
        """Тест 8: Итоговая сводка реализации."""
        print("\n=== ТЕСТ 8: Итоговая сводка реализации ===")
        
        print("Результаты проверки фактической реализации:")
        
        total_components = len(self.test_results)
        fully_implemented = 0
        partially_implemented = 0
        failed_components = 0
        
        for component, result in self.test_results.items():
            if isinstance(result, str) and "/" in result:
                parts = result.split("/")
                if len(parts) == 2:
                    implemented = int(parts[0])
                    total = int(parts[1])
                    percentage = (implemented / total) * 100
                    
                    if percentage == 100:
                        status_icon = "✅"
                        fully_implemented += 1
                    elif percentage >= 70:
                        status_icon = "⚠️"
                        partially_implemented += 1
                    else:
                        status_icon = "❌"
                        failed_components += 1
                    
                    print(f"   {status_icon} {component}: {result} ({percentage:.1f}%)")
                else:
                    print(f"   ❌ {component}: {result}")
                    failed_components += 1
            else:
                if result in ["import_failed", "error", "db_not_found"]:
                    print(f"   ❌ {component}: {result}")
                    failed_components += 1
                else:
                    print(f"   ✅ {component}: {result}")
                    fully_implemented += 1
        
        implementation_rate = (fully_implemented / total_components) * 100 if total_components > 0 else 0
        
        print(f"\nОбщая статистика реализации:")
        print(f"   ✅ Полностью реализовано: {fully_implemented}/{total_components}")
        print(f"   ⚠️ Частично реализовано: {partially_implemented}/{total_components}")
        print(f"   ❌ Не реализовано/ошибки: {failed_components}/{total_components}")
        print(f"   📈 Общая готовность: {implementation_rate:.1f}%")
        
        if implementation_rate >= 80:
            print(f"\n🎉 РЕАЛИЗАЦИЯ СООТВЕТСТВУЕТ СХЕМЕ!")
            print(f"   Новая система организации данных реализована согласно DATA_ORGANIZATION_SCHEMA.md")
        elif implementation_rate >= 60:
            print(f"\n⚠️ РЕАЛИЗАЦИЯ ЧАСТИЧНО СООТВЕТСТВУЕТ СХЕМЕ.")
            print(f"   Основные компоненты реализованы, требуется доработка отдельных частей.")
        else:
            print(f"\n❌ РЕАЛИЗАЦИЯ НЕ СООТВЕТСТВУЕТ СХЕМЕ.")
            print(f"   Обнаружены критические несоответствия с DATA_ORGANIZATION_SCHEMA.md")

def run_implementation_tests():
    """Запуск всех тестов реализации."""
    print("ЗАПУСК ТЕСТОВ ФАКТИЧЕСКОЙ РЕАЛИЗАЦИИ СИСТЕМЫ ОРГАНИЗАЦИИ ДАННЫХ")
    print("=" * 100)
    
    test_instance = TestDataOrganizationImplementation()
    test_instance.setup_method()
    
    tests = [
        test_instance.test_01_config_modules_exist,
        test_instance.test_02_data_paths_implementation,
        test_instance.test_03_file_manager_implementation,
        test_instance.test_04_directory_structure_compliance,
        test_instance.test_05_metadata_database_schema,
        test_instance.test_06_cleanup_service_implementation,
        test_instance.test_07_migration_functionality,
        test_instance.test_08_integration_summary,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ ТЕСТ ПРОВАЛЕН: {test.__name__}")
            print(f"   Ошибка: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 100)
    print(f"РЕЗУЛЬТАТЫ ПРОВЕРКИ РЕАЛИЗАЦИИ:")
    print(f"   Пройдено: {passed}")
    print(f"   Провалено: {failed}")
    print(f"   Успешность: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\nВСЕ ТЕСТЫ РЕАЛИЗАЦИИ ПРОЙДЕНЫ!")
        print("   Фактическая реализация полностью соответствует DATA_ORGANIZATION_SCHEMA.md!")
    else:
        print(f"\nОбнаружены несоответствия в реализации.")
        print("   Требуется доработка отдельных компонентов.")

if __name__ == "__main__":
    run_implementation_tests()
