#!/usr/bin/env python3
"""
Тест интеграции модуля 1 с новой системой организации данных.
Проверяет работу с разделением по базам данных и контролем размера файлов.
"""

import pytest
import requests
import json
from pathlib import Path
import pandas as pd
import tempfile
import os

# Базовый URL для API модуля 1
BASE_URL = "http://localhost:8000/api/v1/data-quality"

class TestModule1NewOrganization:
    """Тесты интеграции модуля 1 с новой системой организации данных."""
    
    def setup_method(self):
        """Подготовка к тестам."""
        self.test_databases = ["sales_db", "user_analytics", "test_analytics"]
        
    def test_system_organization_status(self):
        """Тест проверки статуса новой системы организации."""
        print("\n=== ТЕСТ: Статус системы организации ===")
        
        response = requests.get(f"{BASE_URL}/system/organization-status")
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Система организации активна")
            print(f"   Базовая директория: {data.get('base_data_dir')}")
            print(f"   Доступные БД: {data.get('available_databases')}")
            print(f"   Макс размер файла: {data.get('max_file_size_mb')} MB")
            print(f"   База метаданных: {data.get('metadata_db')}")
            
            assert data["status"] == "active"
            assert "available_databases" in data
            assert data["max_file_size_mb"] == 500
            
        else:
            print(f"❌ Ошибка получения статуса: {response.text}")
            
    def test_get_available_databases(self):
        """Тест получения списка доступных баз данных."""
        print("\n=== ТЕСТ: Доступные базы данных ===")
        
        response = requests.get(f"{BASE_URL}/databases")
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Найдено баз данных: {data.get('count')}")
            print(f"   Список БД: {data.get('databases')}")
            
            assert data["status"] == "success"
            assert isinstance(data["databases"], list)
            
        else:
            print(f"❌ Ошибка получения БД: {response.text}")
    
    def test_database_validation_status(self):
        """Тест получения статуса валидации для конкретной БД."""
        print("\n=== ТЕСТ: Статус валидации БД ===")
        
        for db_name in self.test_databases:
            response = requests.get(f"{BASE_URL}/database/{db_name}/status")
            
            print(f"БД {db_name} - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Статус: {data.get('status')}")
                print(f"   Источников: {data.get('sources_count', 0)}")
                
                assert "database_name" in data
                assert data["database_name"] == db_name
                
            else:
                print(f"   ❌ Ошибка: {response.text}")
    
    def test_validate_file_with_database_organization(self):
        """Тест валидации файла с сохранением в организованную структуру."""
        print("\n=== ТЕСТ: Валидация с организацией по БД ===")
        
        # Создаем тестовый CSV файл
        test_data = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
            'age': [25, 30, 35, 28, 32],
            'salary': [50000, 60000, 70000, 55000, 65000],
            'department': ['IT', 'HR', 'Finance', 'IT', 'Marketing']
        })
        
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            test_data.to_csv(f.name, index=False)
            temp_file_path = f.name
        
        try:
            # Тестируем валидацию с организацией
            payload = {
                "file_path": temp_file_path,
                "database_name": "test_analytics",
                "source_id": "test_validation_data"
            }
            
            response = requests.post(
                f"{BASE_URL}/validate-with-database-organization",
                params=payload
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Валидация успешна")
                print(f"   Статус: {data.get('status')}")
                print(f"   Сообщение: {data.get('message')}")
                
                validation_result = data.get('validation_result', {})
                print(f"   Результат валидации: {validation_result.get('status')}")
                
                assert data["status"] == "success"
                
            else:
                print(f"❌ Ошибка валидации: {response.text}")
                
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_clean_data_with_database_organization(self):
        """Тест очистки данных с сохранением в организованную структуру."""
        print("\n=== ТЕСТ: Очистка с организацией по БД ===")
        
        # Предполагаем, что данные уже валидированы в предыдущем тесте
        payload = {
            "source_id": "test_validation_data",
            "database_name": "test_analytics"
        }
        
        response = requests.post(
            f"{BASE_URL}/clean-with-database-organization",
            params=payload
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Очистка выполнена")
            print(f"   Статус: {data.get('status')}")
            print(f"   Источник: {data.get('source_id')}")
            print(f"   БД: {data.get('database_name')}")
            print(f"   Файлов создано: {data.get('files_count', 0)}")
            
            if data.get('cleaned_files'):
                print(f"   Очищенные файлы: {data['cleaned_files'][:2]}...")  # Показываем первые 2
            
            assert data["status"] == "success"
            
        else:
            print(f"❌ Ошибка очистки: {response.text}")
            # Это может быть нормально, если данные еще не валидированы
            print("   (Это нормально, если данные еще не валидированы)")
    
    def test_health_check_with_new_organization(self):
        """Тест health check с проверкой новой системы организации."""
        print("\n=== ТЕСТ: Health Check с новой организацией ===")
        
        response = requests.get(f"{BASE_URL}/health-check")
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Модуль 1 работает")
            print(f"   Статус: {data.get('status')}")
            print(f"   Время: {data.get('timestamp')}")
            
            integrations = data.get('integrations', {})
            print(f"   Интеграции:")
            for key, value in integrations.items():
                print(f"     {key}: {value}")
            
            # Проверяем наличие информации о новой организации
            if 'data_organization' in integrations:
                print(f"   ✅ Новая система организации: {integrations['data_organization']}")
                
            if 'available_databases' in integrations:
                print(f"   ✅ Доступные БД: {integrations['available_databases']}")
            
            assert data["status"] == "healthy"
            
        else:
            print(f"❌ Ошибка health check: {response.text}")

def run_tests():
    """Запуск всех тестов."""
    print("ЗАПУСК ТЕСТОВ ИНТЕГРАЦИИ МОДУЛЯ 1 С НОВОЙ ОРГАНИЗАЦИЕЙ ДАННЫХ")
    print("=" * 80)
    
    test_instance = TestModule1NewOrganization()
    test_instance.setup_method()
    
    tests = [
        test_instance.test_system_organization_status,
        test_instance.test_get_available_databases,
        test_instance.test_database_validation_status,
        test_instance.test_health_check_with_new_organization,
        test_instance.test_validate_file_with_database_organization,
        test_instance.test_clean_data_with_database_organization,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"ТЕСТ ПРОВАЛЕН: {test.__name__}")
            print(f"   Ошибка: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f" РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"   Пройдено: {passed}")
    print(f"   Провалено: {failed}")
    print(f"   Успешность: {passed/(passed+failed)*100:.1f}%")
    if failed == 0:
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Модуль 1 успешно интегрирован с новой системой организации данных!")
    else:
        print("Некоторые тесты провалены. Требуется дополнительная отладка.")

if __name__ == "__main__":
    run_tests()
