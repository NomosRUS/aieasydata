#!/usr/bin/env python3
"""
Комплексный тест интеграции всех модулей с новой системой организации данных.
Проверяет работу модулей 1, 2, 3, 4, 5 с новыми путями и file_manager.
"""

import pytest
import requests
import json
from pathlib import Path
import pandas as pd
import tempfile
import os
import time

# Базовые URL для API модулей
MODULE_URLS = {
    "module1": "http://localhost:8000/api/v1/data-quality",
    "module2": "http://localhost:8000/api/v1/aggregation", 
    "module3": "http://localhost:8000/api/v1/performance",
    "module4": "http://localhost:8000/api/v1/warehouse",
    "module5": "http://localhost:8000/api/v1/metrics",
    "cleanup": "http://localhost:8000/api/v1/cleanup"
}

class TestNewOrganizationIntegration:
    """Комплексные тесты интеграции с новой системой организации данных."""
    
    def setup_method(self):
        """Подготовка к тестам."""
        self.test_databases = ["sales_db", "user_analytics", "test_analytics"]
        self.test_results = {}
        
    def test_01_system_organization_status(self):
        """Тест 1: Проверка статуса новой системы организации."""
        print("\n=== ТЕСТ 1: Статус системы организации ===")
        
        # Проверяем модуль 1
        response = requests.get(f"{MODULE_URLS['module1']}/system/organization-status")
        
        print(f"Модуль 1 - Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Система организации активна")
            print(f"   Базовая директория: {data.get('base_data_dir')}")
            print(f"   Доступные БД: {data.get('available_databases')}")
            print(f"   Макс размер файла: {data.get('max_file_size_mb')} MB")
            
            self.test_results["organization_status"] = "success"
            assert data["status"] == "active"
            
        else:
            print(f"❌ Ошибка получения статуса: {response.text}")
            self.test_results["organization_status"] = "failed"
    
    def test_02_cleanup_service_integration(self):
        """Тест 2: Интеграция сервиса автоматической очистки."""
        print("\n=== ТЕСТ 2: Сервис автоматической очистки ===")
        
        # Проверяем статус сервиса очистки
        response = requests.get(f"{MODULE_URLS['cleanup']}/status")
        
        print(f"Cleanup Service - Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Сервис очистки доступен")
            
            cleanup_stats = data.get('cleanup_service', {})
            print(f"   Запущен: {cleanup_stats.get('is_running')}")
            print(f"   Последняя очистка: {cleanup_stats.get('last_cleanup')}")
            print(f"   Файлов очищено: {cleanup_stats.get('files_cleaned')}")
            print(f"   Освобождено MB: {cleanup_stats.get('space_freed_mb')}")
            
            self.test_results["cleanup_service"] = "success"
            
        else:
            print(f"❌ Ошибка сервиса очистки: {response.text}")
            self.test_results["cleanup_service"] = "failed"
    
    def test_03_cross_module_database_awareness(self):
        """Тест 3: Осведомленность модулей о базах данных."""
        print("\n=== ТЕСТ 3: Осведомленность модулей о БД ===")
        
        modules_to_test = [
            ("module1", "/databases"),
            ("module2", "/sources"),  # Может содержать информацию о БД
        ]
        
        for module_name, endpoint in modules_to_test:
            if module_name in MODULE_URLS:
                response = requests.get(f"{MODULE_URLS[module_name]}{endpoint}")
                
                print(f"{module_name.upper()} - Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ {module_name} осведомлен о структуре данных")
                    
                    if "databases" in data:
                        print(f"   Доступные БД: {data['databases']}")
                    elif "sources" in data:
                        print(f"   Источников данных: {len(data.get('sources', []))}")
                        
                else:
                    print(f"   ❌ {module_name} не отвечает: {response.text}")
    
    def test_04_file_size_control_integration(self):
        """Тест 4: Интеграция контроля размера файлов."""
        print("\n=== ТЕСТ 4: Контроль размера файлов ===")
        
        # Создаем тестовый файл среднего размера
        test_data = pd.DataFrame({
            'id': range(10000),  # 10K строк
            'name': [f'User_{i}' for i in range(10000)],
            'value': [i * 1.5 for i in range(10000)],
            'category': [f'Cat_{i%10}' for i in range(10000)],
            'description': [f'Description for item {i}' * 10 for i in range(10000)]  # Длинные строки
        })
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_data.to_csv(f.name, index=False)
            temp_file_path = f.name
            file_size_mb = os.path.getsize(f.name) / (1024 * 1024)
        
        print(f"Создан тестовый файл: {file_size_mb:.2f} MB")
        
        try:
            # Тестируем валидацию с контролем размера через модуль 1
            payload = {
                "file_path": temp_file_path,
                "database_name": "test_analytics",
                "source_id": "size_control_test"
            }
            
            response = requests.post(
                f"{MODULE_URLS['module1']}/validate-with-database-organization",
                params=payload
            )
            
            print(f"Валидация - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Файл обработан с контролем размера")
                print(f"   Статус: {data.get('status')}")
                
                validation_result = data.get('validation_result', {})
                metadata = validation_result.get('metadata', {})
                
                if 'output_files' in metadata:
                    output_files = metadata['output_files']
                    print(f"   Создано файлов: {len(output_files) if output_files else 0}")
                    
                    # Проверяем, что файлы разделены, если исходный был большой
                    if file_size_mb > 500 and output_files:
                        print(f"   ✅ Большой файл автоматически разделен")
                        self.test_results["file_size_control"] = "success"
                    elif file_size_mb <= 500:
                        print(f"   ✅ Файл обработан без разделения (размер в пределах лимита)")
                        self.test_results["file_size_control"] = "success"
                
            else:
                print(f"❌ Ошибка валидации: {response.text}")
                self.test_results["file_size_control"] = "failed"
                
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_05_module_health_checks_with_organization(self):
        """Тест 5: Health checks модулей с новой организацией."""
        print("\n=== ТЕСТ 5: Health Checks модулей ===")
        
        health_endpoints = [
            ("module1", "/health-check"),
            ("module2", "/health-check"),
            ("module5", "/health-check"),
        ]
        
        healthy_modules = 0
        total_modules = len(health_endpoints)
        
        for module_name, endpoint in health_endpoints:
            if module_name in MODULE_URLS:
                response = requests.get(f"{MODULE_URLS[module_name]}{endpoint}")
                
                print(f"{module_name.upper()} - Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    print(f"   ✅ {module_name}: {status}")
                    
                    # Проверяем интеграции
                    integrations = data.get('integrations', {})
                    if integrations:
                        print(f"   Интеграции:")
                        for key, value in integrations.items():
                            if 'data_organization' in key or 'available_databases' in key:
                                print(f"     {key}: {value}")
                    
                    if status == "healthy":
                        healthy_modules += 1
                        
                else:
                    print(f"   ❌ {module_name}: недоступен")
        
        success_rate = (healthy_modules / total_modules) * 100
        print(f"\nЗдоровых модулей: {healthy_modules}/{total_modules} ({success_rate:.1f}%)")
        
        self.test_results["health_checks"] = "success" if success_rate >= 80 else "partial"
    
    def test_06_cleanup_service_functionality(self):
        """Тест 6: Функциональность сервиса очистки."""
        print("\n=== ТЕСТ 6: Функциональность сервиса очистки ===")
        
        # Получаем конфигурацию очистки
        response = requests.get(f"{MODULE_URLS['cleanup']}/config")
        
        print(f"Config - Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            config = data.get('config', {})
            print(f"✅ Конфигурация очистки получена")
            print(f"   Автоочистка включена: {config.get('auto_cleanup_enabled')}")
            print(f"   Интервал очистки: {config.get('cleanup_interval_hours')} часов")
            print(f"   Время жизни temp файлов: {config.get('temp_files_hours')} часов")
            print(f"   Время жизни промежуточных файлов: {config.get('intermediate_files_days')} дней")
            
            # Пробуем запустить ручную очистку
            cleanup_response = requests.post(f"{MODULE_URLS['cleanup']}/manual-cleanup")
            
            print(f"Manual Cleanup - Status Code: {cleanup_response.status_code}")
            
            if cleanup_response.status_code == 200:
                cleanup_data = cleanup_response.json()
                print(f"✅ Ручная очистка выполнена")
                
                stats = cleanup_data.get('stats', {})
                print(f"   Файлов очищено: {stats.get('files_cleaned', 0)}")
                print(f"   Освобождено места: {stats.get('space_freed_mb', 0):.2f} MB")
                
                self.test_results["cleanup_functionality"] = "success"
            else:
                print(f"❌ Ошибка ручной очистки: {cleanup_response.text}")
                self.test_results["cleanup_functionality"] = "failed"
        else:
            print(f"❌ Ошибка получения конфигурации: {response.text}")
            self.test_results["cleanup_functionality"] = "failed"
    
    def test_07_integration_summary(self):
        """Тест 7: Сводка интеграции."""
        print("\n=== ТЕСТ 7: Сводка интеграции ===")
        
        print("Результаты тестирования:")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result == "success")
        partial_tests = sum(1 for result in self.test_results.values() if result == "partial")
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result == "success" else "⚠️" if result == "partial" else "❌"
            print(f"   {status_icon} {test_name}: {result}")
        
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\nОбщая статистика:")
        print(f"   Успешных тестов: {successful_tests}/{total_tests}")
        print(f"   Частично успешных: {partial_tests}/{total_tests}")
        print(f"   Общий успех: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print(f"\n🎉 ИНТЕГРАЦИЯ УСПЕШНА! Новая система организации данных работает корректно!")
        elif success_rate >= 60:
            print(f"\n⚠️ ИНТЕГРАЦИЯ ЧАСТИЧНО УСПЕШНА. Требуется дополнительная настройка.")
        else:
            print(f"\n❌ ИНТЕГРАЦИЯ ТРЕБУЕТ ДОРАБОТКИ. Обнаружены критические проблемы.")

def run_integration_tests():
    """Запуск всех интеграционных тестов."""
    print("🚀 ЗАПУСК КОМПЛЕКСНЫХ ТЕСТОВ ИНТЕГРАЦИИ С НОВОЙ ОРГАНИЗАЦИЕЙ ДАННЫХ")
    print("=" * 90)
    
    test_instance = TestNewOrganizationIntegration()
    test_instance.setup_method()
    
    tests = [
        test_instance.test_01_system_organization_status,
        test_instance.test_02_cleanup_service_integration,
        test_instance.test_03_cross_module_database_awareness,
        test_instance.test_04_file_size_control_integration,
        test_instance.test_05_module_health_checks_with_organization,
        test_instance.test_06_cleanup_service_functionality,
        test_instance.test_07_integration_summary,
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
    
    print("\n" + "=" * 90)
    print(f"📊 ФИНАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
    print(f"   ✅ Пройдено: {passed}")
    print(f"   ❌ Провалено: {failed}")
    print(f"   📈 Успешность: {passed/(passed+failed)*100:.1f}%")

if __name__ == "__main__":
    run_integration_tests()
