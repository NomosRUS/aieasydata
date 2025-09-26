"""
Простые API вызовы для тестирования Модуля 3
"""

import requests
import json


def test_health_check():
    """Тест health check"""
    print("=== HEALTH CHECK ===")
    try:
        response = requests.get("http://localhost:8000/api/v1/performance/health-check")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Module: {data['module']}")
            print(f"Status: {data['status']}")
            print(f"Integrations: {data['integrations']}")
            print(f"Capabilities: {len(data['capabilities'])} возможностей")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def test_performance_analysis():
    """Тест анализа производительности"""
    print("\n=== PERFORMANCE ANALYSIS ===")
    try:
        payload = {"source": "temp_sales.csv"}
        response = requests.post(
            "http://localhost:8000/api/v1/performance/analyze",
            json=payload
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Analysis ID: {data['analysis_id']}")
            print(f"Source Type: {data['source_type']}")
            print(f"Status: {data['status']}")
            
            if data.get('current_metrics'):
                metrics = data['current_metrics']
                print(f"Data Size: {metrics.get('data_size_bytes', 0)} bytes")
                print(f"Row Count: {metrics.get('row_count', 0)}")
            
            if data.get('recommendations'):
                print(f"Recommendations: {len(data['recommendations'])}")
                for i, rec in enumerate(data['recommendations'][:3]):
                    print(f"  {i+1}. {rec['recommendation_type']}: {rec['estimated_improvement']:.1f}% improvement")
            
            return data['analysis_id']
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    return None


def test_get_metrics():
    """Тест получения метрик"""
    print("\n=== GET METRICS ===")
    try:
        response = requests.get("http://localhost:8000/api/v1/performance/metrics/temp_sales.csv")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Source: {data['source']}")
            print(f"Source Type: {data['source_type']}")
            if data.get('metrics'):
                print("Metrics received successfully")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def test_validate_ddl():
    """Тест валидации DDL"""
    print("\n=== DDL VALIDATION ===")
    try:
        ddl_script = """
        CREATE TABLE test_table (
            id INT PRIMARY KEY,
            name VARCHAR(100),
            created_date DATE
        );
        """
        
        params = {
            "ddl_script": ddl_script,
            "target_db_type": "postgres"
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/performance/validate-ddl",
            params=params
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Valid: {data['valid']}")
            if data.get('errors'):
                print(f"Errors: {data['errors']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def test_api_docs():
    """Проверка доступности документации API"""
    print("\n=== API DOCS ===")
    try:
        response = requests.get("http://localhost:8000/docs")
        print(f"API Docs Status: {response.status_code}")
        if response.status_code == 200:
            print("API Documentation is available at: http://localhost:8000/docs")
        
        response = requests.get("http://localhost:8000/openapi.json")
        print(f"OpenAPI Schema Status: {response.status_code}")
        if response.status_code == 200:
            schema = response.json()
            paths = schema.get('paths', {})
            performance_paths = [path for path in paths.keys() if '/performance/' in path]
            print(f"Performance endpoints found: {len(performance_paths)}")
            for path in performance_paths[:5]:  # Показываем первые 5
                print(f"  - {path}")
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Основная функция тестирования"""
    print("ТЕСТИРОВАНИЕ API МОДУЛЯ 3")
    print("=" * 50)
    
    # Тест 1: Health Check
    test_health_check()
    
    # Тест 2: Анализ производительности
    analysis_id = test_performance_analysis()
    
    # Тест 3: Получение метрик
    test_get_metrics()
    
    # Тест 4: Валидация DDL
    test_validate_ddl()
    
    # Тест 5: Документация API
    test_api_docs()
    
    print("\n" + "=" * 50)
    print("[SUCCESS] ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("Документация API: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/api/v1/performance/health-check")


if __name__ == "__main__":
    main()
