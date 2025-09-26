"""
Быстрая проверка доступных API endpoints модуля 2.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoints():
    """Быстро проверяем доступные endpoints."""
    
    print("БЫСТРАЯ ПРОВЕРКА API МОДУЛЯ 2")
    print("=" * 40)
    
    # Список возможных endpoints для проверки
    endpoints_to_test = [
        "/",
        "/docs",
        "/health",
        "/api/v1/aggregation/health-check",
        "/api/v1/aggregation/sources",
        "/api/v1/aggregation/custom-dataset"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            print(f"Проверяем: {endpoint}")
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=2)
            print(f"  Статус: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ РАБОТАЕТ!")
            else:
                print(f"  ❌ Ошибка: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Исключение: {str(e)[:50]}...")
        print()

if __name__ == "__main__":
    test_endpoints()
