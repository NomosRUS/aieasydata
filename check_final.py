import requests
import time

print("Ожидание запуска Airflow...")
time.sleep(30)

try:
    response = requests.get("http://localhost:8080/api/v1/dags", auth=('admin', 'admin'), timeout=30)
    if response.status_code == 200:
        dags = response.json().get('dags', [])
        test_dags = [d['dag_id'] for d in dags if d['dag_id'].startswith('test_module')]
        print(f"Найдено тестовых DAG'ов: {len(test_dags)}")
        for dag_id in test_dags:
            print(f"  - {dag_id}")
    else:
        print(f"Ошибка API: {response.status_code}")
except Exception as e:
    print(f"Ошибка: {e}")
