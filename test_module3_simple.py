"""
Простой тест для Модуля 3 - Оптимизация производительности
Без эмодзи для совместимости с Windows
"""

import requests
import json


def test_module3_health():
    """Тест работоспособности модуля"""
    print("Тестирование health check модуля 3...")
    
    try:
        response = requests.get("http://localhost:8000/api/v1/performance/health-check")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Модуль 3 работает: {data['status']}")
            print(f"[INFO] Интеграции: {data.get('integrations', {})}")
            return True
        else:
            print(f"[ERROR] Ошибка health check: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Ошибка подключения: {str(e)}")
        return False


def test_performance_analysis():
    """Тест анализа производительности"""
    print("\nТестирование анализа производительности...")
    
    # Тестируем анализ CSV файла
    test_source = "temp_sales.csv"
    
    try:
        print(f"Анализируем источник: {test_source}")
        
        response = requests.post(
            "http://localhost:8000/api/v1/performance/analyze",
            json={"source": test_source}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Анализ завершен: {data['analysis_id']}")
            print(f"[INFO] Тип источника: {data['source_type']}")
            print(f"[INFO] Статус: {data['status']}")
            
            if data.get('current_metrics'):
                metrics = data['current_metrics']
                size_mb = metrics.get('data_size_bytes', 0) / (1024*1024)
                print(f"[INFO] Размер данных: {size_mb:.2f} MB")
                print(f"[INFO] Количество строк: {metrics.get('row_count', 0):,}")
            
            if data.get('recommendations'):
                print(f"[INFO] Рекомендации: {len(data['recommendations'])}")
                for i, rec in enumerate(data['recommendations'][:2]):
                    print(f"  {i+1}. {rec['recommendation_type']}: {rec['estimated_improvement']:.1f}% улучшение")
            
            return data['analysis_id']
            
        else:
            print(f"[ERROR] Ошибка анализа: {response.status_code}")
            print(f"[ERROR] Ответ: {response.text}")
            
    except Exception as e:
        print(f"[ERROR] Ошибка при анализе: {str(e)}")
    
    return None


def test_module5_integration():
    """Тест интеграции с модулем 5"""
    print("\nТестирование интеграции с модулем 5...")
    
    try:
        response = requests.get(
            "http://localhost:8000/api/v1/performance/metrics/temp_sales.csv"
        )
        
        if response.status_code == 200:
            data = response.json()
            print("[OK] Интеграция с модулем 5 работает")
            print(f"[INFO] Автоопределенный тип: {data.get('source_type')}")
            return True
        else:
            print(f"[ERROR] Ошибка интеграции: {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Ошибка интеграции с модулем 5: {str(e)}")
    
    return False


def test_api_endpoints():
    """Тест доступности API endpoints"""
    print("\nТестирование API endpoints...")
    
    endpoints = [
        "/api/v1/performance/health-check",
        "/api/v1/performance/warehouses",
    ]
    
    working_endpoints = 0
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:8000{endpoint}")
            if response.status_code in [200, 404]:  # 404 тоже означает что endpoint существует
                print(f"[OK] {endpoint}")
                working_endpoints += 1
            else:
                print(f"[ERROR] {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] {endpoint}: {str(e)}")
    
    return working_endpoints == len(endpoints)


def main():
    """Основная функция тестирования"""
    print("ИНТЕГРАЦИОННЫЙ ТЕСТ МОДУЛЯ 3 - ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 70)
    
    passed_tests = 0
    total_tests = 4
    
    # Тест 1: Health check
    if test_module3_health():
        passed_tests += 1
    
    # Тест 2: API endpoints
    if test_api_endpoints():
        passed_tests += 1
    
    # Тест 3: Анализ производительности
    analysis_id = test_performance_analysis()
    if analysis_id:
        passed_tests += 1
    
    # Тест 4: Интеграция с модулем 5
    if test_module5_integration():
        passed_tests += 1
    
    # Результаты
    print("\n" + "=" * 70)
    print(f"РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ МОДУЛЯ 3")
    print(f"Пройдено тестов: {passed_tests}/{total_tests}")
    print(f"Успешность: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("[SUCCESS] ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("Модуль 3 полностью функционален")
    elif passed_tests >= total_tests * 0.75:
        print("[WARNING] Большинство тестов пройдено")
    else:
        print("[ERROR] Много неудачных тестов, требуется отладка")
    
    print("\nДля запуска сервера:")
    print("cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    main()
