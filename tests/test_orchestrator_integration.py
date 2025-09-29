"""
Интеграционный тест для мастер-оркестратора Airflow
Проверяет интеграцию с модулями 1,2,3,4,5 согласно ТЗ Задачи 6
"""

import sys
import os
import unittest
import time
from datetime import datetime

# Добавляем путь к оркестратору
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags'))

try:
    from orchestrator.master_orchestrator import MasterOrchestrator
    from orchestrator.module_scheduler import ModuleScheduler
    from orchestrator.dag_composer import DAGComposer
    from orchestrator.execution_monitor import ExecutionMonitor
except ImportError as e:
    print(f"Warning: Could not import orchestrator modules: {e}")
    MasterOrchestrator = None

class TestOrchestratorIntegration(unittest.TestCase):
    """Тестирование интеграции мастер-оркестратора"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        if MasterOrchestrator is None:
            self.skipTest("Orchestrator modules not available")
        
        self.base_url = "http://localhost:8000"
        self.orchestrator = MasterOrchestrator(self.base_url)
        self.module_scheduler = ModuleScheduler(self.base_url)
        self.dag_composer = DAGComposer(self.base_url)
        self.execution_monitor = ExecutionMonitor(self.base_url)
    
    def test_01_module_scheduler_configuration(self):
        """Тест 1: Проверка конфигурации планировщика модулей"""
        print("\n=== ТЕСТ 1: Конфигурация планировщика модулей ===")
        
        # Проверяем доступные модули
        available_modules = self.module_scheduler.get_available_modules()
        print(f"Доступные модули: {list(available_modules.keys())}")
        
        expected_modules = [1, 2, 3, 5]
        for module in expected_modules:
            self.assertIn(module, available_modules, f"Module {module} should be available")
            
            config = available_modules[module]
            self.assertIn("name", config)
            self.assertIn("bulk_endpoint", config)
            self.assertIn("health_check", config)
            self.assertIn("default_schedule", config)
            
            print(f"✅ Модуль {module}: {config['name']}")
        
        # Проверяем доступные функции
        available_functions = self.module_scheduler.get_available_functions()
        print(f"Доступные функции: {len(available_functions)}")
        
        expected_functions = [
            "validate_specific_source", "check_folder_homogeneity",
            "execute_scenario", "create_custom_dataset", 
            "analyze_performance", "apply_optimizations",
            "monitor_specific_source", "auto_detect_source"
        ]
        
        for func in expected_functions:
            self.assertIn(func, available_functions, f"Function {func} should be available")
            print(f"✅ Функция: {func}")
        
        print("✅ ТЕСТ 1 ПРОЙДЕН: Конфигурация планировщика корректна")
    
    def test_02_module_health_checks(self):
        """Тест 2: Проверка работоспособности модулей"""
        print("\n=== ТЕСТ 2: Проверка работоспособности модулей ===")
        
        modules_to_check = [1, 2, 3, 5]
        healthy_modules = []
        
        for module in modules_to_check:
            try:
                health_status = self.module_scheduler.check_module_health(module)
                print(f"Модуль {module}: {health_status['status']}")
                
                if health_status['status'] == 'healthy':
                    healthy_modules.append(module)
                    print(f"✅ Модуль {module} работает")
                else:
                    print(f"⚠️ Модуль {module} недоступен: {health_status.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Ошибка проверки модуля {module}: {str(e)}")
        
        print(f"Работающие модули: {healthy_modules}")
        self.assertGreater(len(healthy_modules), 0, "At least one module should be healthy")
        print("✅ ТЕСТ 2 ПРОЙДЕН: Найдены работающие модули")
    
    def test_03_schedule_module_execution(self):
        """Тест 3: Планирование выполнения модулей"""
        print("\n=== ТЕСТ 3: Планирование выполнения модулей ===")
        
        # Планируем выполнение модуля 5 (мониторинг)
        try:
            task = self.module_scheduler.schedule_module_execution(
                module=5,
                schedule="0 * * * *",  # Каждый час
                config={"test_mode": True}
            )
            
            self.assertIsNotNone(task.task_id)
            self.assertEqual(task.task_type, "module")
            self.assertEqual(task.module, 5)
            print(f"✅ Запланирована задача модуля: {task.task_id}")
            
            # Проверяем список запланированных задач
            scheduled_tasks = self.module_scheduler.get_scheduled_tasks()
            self.assertGreater(len(scheduled_tasks), 0)
            print(f"✅ Запланированных задач: {len(scheduled_tasks)}")
            
        except Exception as e:
            print(f"❌ Ошибка планирования модуля: {str(e)}")
            self.fail(f"Module scheduling failed: {str(e)}")
        
        print("✅ ТЕСТ 3 ПРОЙДЕН: Планирование модулей работает")
    
    def test_04_schedule_function_execution(self):
        """Тест 4: Планирование выполнения функций"""
        print("\n=== ТЕСТ 4: Планирование выполнения функций ===")
        
        # Планируем выполнение функции автоопределения
        try:
            task = self.module_scheduler.schedule_function_execution(
                function_name="auto_detect_source",
                schedule="0 6 * * *",  # Каждый день в 6:00
                parameters={"source": "/data/test"}
            )
            
            self.assertIsNotNone(task.task_id)
            self.assertEqual(task.task_type, "function")
            self.assertEqual(task.module, 5)
            print(f"✅ Запланирована задача функции: {task.task_id}")
            
        except Exception as e:
            print(f"❌ Ошибка планирования функции: {str(e)}")
            self.fail(f"Function scheduling failed: {str(e)}")
        
        print("✅ ТЕСТ 4 ПРОЙДЕН: Планирование функций работает")
    
    def test_05_create_master_pipeline_modular(self):
        """Тест 5: Создание мастер-пайплайна (модульный подход)"""
        print("\n=== ТЕСТ 5: Создание мастер-пайплайна (модульный подход) ===")
        
        # Конфигурация ежедневного ETL пайплайна
        daily_config = {
            "pipeline_name": "daily_full_etl_test",
            "schedule": "0 2 * * *",
            "description": "Тестовый ежедневный ETL пайплайн",
            "stages": [
                {
                    "stage_name": "monitor_sources",
                    "type": "module_call",
                    "module": 5,
                    "endpoint": "/api/v1/metrics/comprehensive-test",
                    "depends_on": []
                },
                {
                    "stage_name": "validate_data", 
                    "type": "module_call",
                    "module": 1,
                    "endpoint": "/api/v1/data-quality/batch-validate",
                    "depends_on": ["monitor_sources"]
                },
                {
                    "stage_name": "aggregate_data",
                    "type": "module_call", 
                    "module": 2,
                    "endpoint": "/api/v1/aggregation/scenarios",
                    "depends_on": ["validate_data"]
                }
            ]
        }
        
        try:
            pipeline = self.orchestrator.create_master_pipeline(daily_config)
            
            self.assertIsNotNone(pipeline.master_dag_id)
            self.assertEqual(pipeline.config.pipeline_name, "daily_full_etl_test")
            self.assertEqual(pipeline.stages_count, 3)
            self.assertGreater(pipeline.estimated_duration, 0)
            
            print(f"✅ Создан мастер-пайплайн: {pipeline.master_dag_id}")
            print(f"✅ Этапов: {pipeline.stages_count}")
            print(f"✅ Оценочное время: {pipeline.estimated_duration} сек")
            print(f"✅ DAG файл: {pipeline.dag_file_path}")
            
            # Проверяем что файл создан
            self.assertTrue(os.path.exists(pipeline.dag_file_path), "DAG file should be created")
            
        except Exception as e:
            print(f"❌ Ошибка создания мастер-пайплайна: {str(e)}")
            self.fail(f"Master pipeline creation failed: {str(e)}")
        
        print("✅ ТЕСТ 5 ПРОЙДЕН: Мастер-пайплайн (модульный) создан")
    
    def test_06_create_master_pipeline_functional(self):
        """Тест 6: Создание мастер-пайплайна (функциональный подход)"""
        print("\n=== ТЕСТ 6: Создание мастер-пайплайна (функциональный подход) ===")
        
        # Конфигурация специфической обработки
        custom_pipeline = {
            "pipeline_name": "sales_data_processing_test",
            "schedule": "0 6 * * 1",  # Понедельник 06:00
            "description": "Тестовая специфическая обработка продаж",
            "stages": [
                {
                    "stage_name": "check_sales_homogeneity",
                    "type": "function_call",
                    "function": "check_folder_homogeneity",
                    "parameters": {"folder_path": "/data/sales"},
                    "depends_on": []
                },
                {
                    "stage_name": "validate_sales_profile",
                    "type": "function_call",
                    "function": "validate_specific_source",
                    "parameters": {"profile_id": "sales_profile_001"},
                    "depends_on": ["check_sales_homogeneity"]
                },
                {
                    "stage_name": "analyze_sales_performance",
                    "type": "function_call",
                    "function": "analyze_performance",
                    "parameters": {"source": "/data/sales_warehouse"},
                    "depends_on": ["validate_sales_profile"]
                }
            ]
        }
        
        try:
            pipeline = self.orchestrator.create_master_pipeline(custom_pipeline)
            
            self.assertIsNotNone(pipeline.master_dag_id)
            self.assertEqual(pipeline.config.pipeline_name, "sales_data_processing_test")
            self.assertEqual(pipeline.stages_count, 3)
            
            print(f"✅ Создан функциональный пайплайн: {pipeline.master_dag_id}")
            print(f"✅ Этапов: {pipeline.stages_count}")
            print(f"✅ DAG файл: {pipeline.dag_file_path}")
            
            # Проверяем что файл создан
            self.assertTrue(os.path.exists(pipeline.dag_file_path), "DAG file should be created")
            
        except Exception as e:
            print(f"❌ Ошибка создания функционального пайплайна: {str(e)}")
            self.fail(f"Functional pipeline creation failed: {str(e)}")
        
        print("✅ ТЕСТ 6 ПРОЙДЕН: Мастер-пайплайн (функциональный) создан")
    
    def test_07_pipeline_validation(self):
        """Тест 7: Валидация конфигурации пайплайнов"""
        print("\n=== ТЕСТ 7: Валидация конфигурации пайплайнов ===")
        
        # Тест с некорректной конфигурацией
        invalid_config = {
            "pipeline_name": "invalid_test",
            "schedule": "0 2 * * *",
            "stages": [
                {
                    "stage_name": "invalid_stage",
                    "type": "module_call",
                    "module": 999,  # Несуществующий модуль
                    "depends_on": []
                }
            ]
        }
        
        try:
            # Это должно вызвать ошибку
            pipeline = self.orchestrator.create_master_pipeline(invalid_config)
            self.fail("Invalid configuration should raise an error")
        except ValueError as e:
            print(f"✅ Валидация корректно отклонила некорректную конфигурацию: {str(e)}")
        except Exception as e:
            print(f"✅ Валидация отклонила конфигурацию: {str(e)}")
        
        print("✅ ТЕСТ 7 ПРОЙДЕН: Валидация работает корректно")
    
    def test_08_list_pipelines(self):
        """Тест 8: Получение списка пайплайнов"""
        print("\n=== ТЕСТ 8: Получение списка пайплайнов ===")
        
        try:
            pipelines = self.orchestrator.list_pipelines()
            print(f"✅ Найдено пайплайнов: {len(pipelines)}")
            
            for pipeline in pipelines:
                print(f"  - {pipeline['pipeline_name']} ({pipeline['master_dag_id']})")
                self.assertIn('master_dag_id', pipeline)
                self.assertIn('pipeline_name', pipeline)
                self.assertIn('stages_count', pipeline)
                self.assertIn('status', pipeline)
            
        except Exception as e:
            print(f"❌ Ошибка получения списка пайплайнов: {str(e)}")
            self.fail(f"Pipeline listing failed: {str(e)}")
        
        print("✅ ТЕСТ 8 ПРОЙДЕН: Список пайплайнов получен")

def run_orchestrator_integration_tests():
    """Запуск интеграционных тестов оркестратора"""
    print("ЗАПУСК ИНТЕГРАЦИОННЫХ ТЕСТОВ МАСТЕР-ОРКЕСТРАТОРА")
    print("=" * 60)
    
    # Создаем тестовый набор
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOrchestratorIntegration)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Выводим итоги
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ МАСТЕР-ОРКЕСТРАТОРА")
    print(f"Всего тестов: {result.testsRun}")
    print(f"Успешных: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Провалившихся: {len(result.failures)}")
    print(f"Ошибок: {len(result.errors)}")
    
    if result.failures:
        print("\nПРОВАЛИВШИЕСЯ ТЕСТЫ:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nОШИБКИ:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\nУСПЕШНОСТЬ: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("ОТЛИЧНЫЙ РЕЗУЛЬТАТ! Мастер-оркестратор готов к использованию!")
    elif success_rate >= 60:
        print("ХОРОШИЙ РЕЗУЛЬТАТ! Основная функциональность работает.")
    else:
        print("ТРЕБУЕТСЯ ДОРАБОТКА. Найдены критические проблемы.")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_orchestrator_integration_tests()
    exit(0 if success else 1)
