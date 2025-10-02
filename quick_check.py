import time
import requests

print("Ожидание запуска webserver...")
time.sleep(30)

try:
    response = requests.get("http://localhost:8080", timeout=10)
    print(f"Статус: {response.status_code}")
    if response.status_code == 200:
        print("Airflow доступен на localhost:8080")
    else:
        print("Проблема с доступом")
except Exception as e:
    print(f"Ошибка: {e}")
    print("Попробуйте:")
    print("1. Подождать еще 1-2 минуты")
    print("2. Обновить страницу в браузере")
    print("3. Очистить кеш браузера")
