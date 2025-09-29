import time
import requests

print("Ожидание обновления DAG'ов...")
time.sleep(30)

try:
    response = requests.get("http://localhost:8080/api/v1/dags", auth=('admin', 'admin'), timeout=30)
    if response.status_code == 200:
        dags = response.json().get('dags', [])
        new_dags = [d['dag_id'] for d in dags if d['dag_id'].startswith('test_module') and '030022' in d['dag_id']]
        print(f"Найдено новых DAG'ов: {len(new_dags)}")
        for dag_id in new_dags:
            print(f"  - {dag_id}")
        
        if len(new_dags) == 4:
            print("УСПЕХ: Все 4 DAG'а загружены!")
        else:
            print("Ожидайте еще немного...")
    else:
        print(f"Ошибка: {response.status_code}")
except Exception as e:
    print(f"Ошибка: {e}")
    print("Попробуйте обновить страницу в браузере")
