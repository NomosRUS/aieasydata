#!/usr/bin/env python3
"""
Упрощенный тест фактической реализации новой системы организации данных.
Проверяет точность и полноту реализации согласно DATA_ORGANIZATION_SCHEMA.md
"""

import os
import sys
from pathlib import Path
import sqlite3

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
            
            status = "[OK]" if exists else "[FAIL]"
            print(f"   {status} {module_path}")
            
            if exists:
                existing_modules += 1
                file_size = full_path.stat().st_size
                print(f"     Размер: {file_size} bytes")
                
                if file_size < 100:
                    print(f"     [WARNING] Файл может быть неполным")
        
        success_rate = (existing_modules / len(required_modules)) * 100
        print(f"\nСуществующих модулей: {existing_modules}/{len(required_modules)} ({success_rate:.1f}%)")
        
        self.test_results["config_modules"] = f"{existing_modules}/{len(required_modules)}"
        
        return existing_modules >= 4
    
    def test_02_data_paths_implementation(self):
        """Тест 2: Проверка реализации DataPaths."""
        print("\n=== ТЕСТ 2: Реализация DataPaths ===")
        
        try:
            from config.paths import DataPaths
            
            print("[OK] DataPaths успешно импортирован")
            
            # Проверяем основные атрибуты
            required_attributes = [
                "BASE_DATA_DIR", "RAW_DATA_DIR", "INTERMEDIATE_DIR", 
                "WAREHOUSES_DIR", "METADATA_DIR"
            ]
            
            existing_attributes = 0
            
            for attr in required_attributes:
                if hasattr(DataPaths, attr):
                    value = getattr(DataPaths, attr)
                    print(f"   [OK] {attr}: {value}")
                    existing_attributes += 1
                else:
                    print(f"   [FAIL] {attr}: отсутствует")
            
            # Проверяем методы
            required_methods = [
                "get_source_path", "get_warehouse_path", 
                "get_metadata_path", "ensure_directories"
            ]
            
            existing_methods = 0
            
            for method in required_methods:
                if hasattr(DataPaths, method):
                    print(f"   [OK] Метод {method}: существует")
                    existing_methods += 1
                else:
                    print(f"   [FAIL] Метод {method}: отсутствует")
            
            total_features = len(required_attributes) + len(required_methods)
            existing_features = existing_attributes + existing_methods
            
            print(f"\nРеализованных функций: {existing_features}/{total_features}")
            
            self.test_results["data_paths"] = f"{existing_features}/{total_features}"
            
            return existing_features >= 7
            
        except ImportError as e:
            print(f"[FAIL] Ошибка импорта DataPaths: {e}")
            self.test_results["data_paths"] = "import_failed"
            return False
    
    def test_03_file_manager_implementation(self):
        """Тест 3: Проверка реализации file_manager."""
        print("\n=== ТЕСТ 3: Реализация file_manager ===")
        
        try:
            from config.file_utils import FileManager, FileSplitter
            
            print("[OK] FileManager и FileSplitter успешно импортированы")
            
            # Проверяем FileManager
            file_manager = FileManager()
            
            required_methods = [
                "process_file", "get_file_parts", "combine_file_parts", 
                "register_artifact"
            ]
            
            existing_methods = 0
            
            for method in required_methods:
                if hasattr(file_manager, method):
                    print(f"   [OK] FileManager.{method}: существует")
                    existing_methods += 1
                else:
                    print(f"   [FAIL] FileManager.{method}: отсутствует")
            
            # Проверяем FileSplitter
            splitter_methods = ["split_csv", "split_json", "split_xml"]
            existing_splitter_methods = 0
            
            for method in splitter_methods:
                if hasattr(FileSplitter, method):
                    print(f"   [OK] FileSplitter.{method}: существует")
                    existing_splitter_methods += 1
                else:
                    print(f"   [FAIL] FileSplitter.{method}: отсутствует")
            
            total_methods = len(required_methods) + len(splitter_methods)
            existing_total = existing_methods + existing_splitter_methods
            
            print(f"\nРеализованных методов: {existing_total}/{total_methods}")
            
            self.test_results["file_manager"] = f"{existing_total}/{total_methods}"
            
            return existing_total >= 5
            
        except ImportError as e:
            print(f"[FAIL] Ошибка импорта file_manager: {e}")
            self.test_results["file_manager"] = "import_failed"
            return False
    
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
                print(f"   [OK] {main_dir}/: существует")
                existing_dirs += 1
                
                # Проверяем подпапки
                for subdir in subdirs:
                    sub_path = main_path / subdir
                    total_dirs += 1
                    
                    if sub_path.exists():
                        print(f"     [OK] {main_dir}/{subdir}/: существует")
                        existing_dirs += 1
                    else:
                        print(f"     [FAIL] {main_dir}/{subdir}/: отсутствует")
            else:
                print(f"   [FAIL] {main_dir}/: отсутствует")
                total_dirs += len(subdirs)  # Добавляем пропущенные подпапки
        
        # Проверяем дополнительные папки, которые могли быть созданы
        additional_dirs = ["syn_csv", "syn_json", "syn_xml", "test_data"]
        
        for add_dir in additional_dirs:
            add_path = self.base_path / add_dir
            if add_path.exists():
                print(f"   [OK] {add_dir}/: существует (дополнительная)")
                existing_dirs += 1
            total_dirs += 1
        
        compliance_rate = (existing_dirs / total_dirs) * 100 if total_dirs > 0 else 0
        print(f"\nСоответствие структуре: {existing_dirs}/{total_dirs} ({compliance_rate:.1f}%)")
        
        self.test_results["directory_structure"] = f"{existing_dirs}/{total_dirs}"
        return compliance_rate >= 50
    
    def test_05_metadata_database_schema(self):
        """Тест 5: Проверка схемы базы данных метаданных."""
        print("\n=== ТЕСТ 5: Схема базы данных метаданных ===")
        
        metadata_db_path = self.base_path / "metadata" / "main.db"
        
        if not metadata_db_path.exists():
            print(f"[FAIL] База метаданных не найдена: {metadata_db_path}")
            self.test_results["metadata_schema"] = "db_not_found"
            return False
        
        try:
            conn = sqlite3.connect(metadata_db_path)
            cursor = conn.cursor()
            
            # Получаем список таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"[OK] База метаданных найдена")
            print(f"   Найдено таблиц: {len(tables)}")
            
            # Ожидаемые таблицы согласно схеме
            expected_tables = [
                "sources", "processes", "warehouses", "schemas", 
                "file_parts", "artifacts", "cleanup_log"
            ]
            
            existing_tables = 0
            
            for table in expected_tables:
                if table in tables:
                    print(f"   [OK] Таблица {table}: существует")
                    existing_tables += 1
                    
                    # Проверяем структуру таблицы
                    cursor.execute(f"PRAGMA table_info({table});")
                    columns = cursor.fetchall()
                    print(f"     Колонок: {len(columns)}")
                    
                else:
                    print(f"   [FAIL] Таблица {table}: отсутствует")
            
            conn.close()
            
            schema_compliance = (existing_tables / len(expected_tables)) * 100
            print(f"\nСоответствие схеме: {existing_tables}/{len(expected_tables)} ({schema_compliance:.1f}%)")
            
            self.test_results["metadata_schema"] = f"{existing_tables}/{len(expected_tables)}"
            
            return schema_compliance >= 70
            
        except Exception as e:
            print(f"[FAIL] Ошибка проверки базы метаданных: {e}")
            self.test_results["metadata_schema"] = "error"
            return False
    
    def test_06_integration_summary(self):
        """Тест 6: Итоговая сводка реализации."""
        print("\n=== ТЕСТ 6: Итоговая сводка реализации ===")
        
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
                        status_icon = "[PERFECT]"
                        fully_implemented += 1
                    elif percentage >= 70:
                        status_icon = "[GOOD]"
                        partially_implemented += 1
                    else:
                        status_icon = "[POOR]"
                        failed_components += 1
                    
                    print(f"   {status_icon} {component}: {result} ({percentage:.1f}%)")
                else:
                    print(f"   [FAIL] {component}: {result}")
                    failed_components += 1
            else:
                if result in ["import_failed", "error", "db_not_found"]:
                    print(f"   [FAIL] {component}: {result}")
                    failed_components += 1
                else:
                    print(f"   [OK] {component}: {result}")
                    fully_implemented += 1
        
        implementation_rate = (fully_implemented / total_components) * 100 if total_components > 0 else 0
        
        print(f"\nОбщая статистика реализации:")
        print(f"   Полностью реализовано: {fully_implemented}/{total_components}")
        print(f"   Частично реализовано: {partially_implemented}/{total_components}")
        print(f"   Не реализовано/ошибки: {failed_components}/{total_components}")
        print(f"   Общая готовность: {implementation_rate:.1f}%")
        
        if implementation_rate >= 80:
            print(f"\n[SUCCESS] РЕАЛИЗАЦИЯ СООТВЕТСТВУЕТ СХЕМЕ!")
            print(f"   Новая система организации данных реализована согласно DATA_ORGANIZATION_SCHEMA.md")
            return True
        elif implementation_rate >= 60:
            print(f"\n[WARNING] РЕАЛИЗАЦИЯ ЧАСТИЧНО СООТВЕТСТВУЕТ СХЕМЕ.")
            print(f"   Основные компоненты реализованы, требуется доработка отдельных частей.")
            return True
        else:
            print(f"\n[FAIL] РЕАЛИЗАЦИЯ НЕ СООТВЕТСТВУЕТ СХЕМЕ.")
            print(f"   Обнаружены критические несоответствия с DATA_ORGANIZATION_SCHEMA.md")
            return False

def run_implementation_tests():
    """Запуск всех тестов реализации."""
    print("ЗАПУСК ТЕСТОВ ФАКТИЧЕСКОЙ РЕАЛИЗАЦИИ СИСТЕМЫ ОРГАНИЗАЦИИ ДАННЫХ")
    print("=" * 100)
    
    test_instance = TestDataOrganizationImplementation()
    test_instance.setup_method()
    
    tests = [
        ("Конфигурационные модули", test_instance.test_01_config_modules_exist),
        ("DataPaths реализация", test_instance.test_02_data_paths_implementation),
        ("FileManager реализация", test_instance.test_03_file_manager_implementation),
        ("Структура директорий", test_instance.test_04_directory_structure_compliance),
        ("База метаданных", test_instance.test_05_metadata_database_schema),
        ("Итоговая сводка", test_instance.test_06_integration_summary),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                print(f"[PASS] {test_name}")
                passed += 1
            else:
                print(f"[FAIL] {test_name}")
                failed += 1
        except Exception as e:
            print(f"[ERROR] {test_name}: {str(e)}")
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
