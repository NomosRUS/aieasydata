import time
import requests

print("Ожидание запуска Airflow webserver...")
time.sleep(60)

print("Проверка доступности localhost:8080...")
try:
    response = requests.get("http://localhost:8080", timeout=10)
    print(f"Статус: {response.status_code}")
    if response.status_code == 200:
        print("✅ Airflow webserver работает!")
        print("Откройте http://localhost:8080 в браузере")
    else:
        print(f"❌ Ошибка: {response.status_code}")
except requests.exceptions.ConnectionError:
    print("❌ Не удалось подключиться к localhost:8080")
    print("Airflow webserver еще не запустился")
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("\nПроверка логов...")
import subprocess
try:
    result = subprocess.run(['docker', 'logs', 'aie_airflow', '--tail', '5'], 
                          capture_output=True, text=True, timeout=10)
    print("Последние логи:")
    print(result.stdout)
except Exception as e:
    print(f"Ошибка получения логов: {e}")
