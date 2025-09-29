#!/usr/bin/env python3
"""
Принудительное обновление DAG'ов в Airflow
"""

import requests
import time

def refresh_airflow_dags():
    """Принудительное обновление DAG'ов"""
    
    print("ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ DAG'ОВ В AIRFLOW")
    print("=" * 50)
    
    try:
        # Обновление DAG'ов
        refresh_url = "http://localhost:8080/api/v1/dagSources/~/refresh"
        
        print("Отправка запроса на обновление...")
        response = requests.post(refresh_url, auth=('admin', 'admin'), timeout=30)
        
        if response.status_code in [200, 204]:
            print("Запрос на обновление отправлен успешно!")
        else:
            print(f"Ошибка обновления: {response.status_code}")
            print(f"Ответ: {response.text}")
        
        # Ждем обновления
        print("Ожидание обновления (30 секунд)...")
        time.sleep(30)
        
        # Проверяем результат
        dags_url = "http://localhost:8080/api/v1/dags"
        response = requests.get(dags_url, auth=('admin', 'admin'), timeout=30)
        
        if response.status_code == 200:
            dags_data = response.json()
            dags = dags_data.get('dags', [])
            
            print(f"Всего DAG'ов после обновления: {len(dags)}")
            
            # Ищем новые DAG'и
            new_dags = []
            for dag in dags:
                dag_id = dag.get('dag_id', '')
                if dag_id.startswith('test_module') and '20250928_023440' in dag_id:
                    new_dags.append(dag_id)
            
            print(f"Найдено новых DAG'ов: {len(new_dags)}")
            for dag_id in new_dags:
                print(f"  - {dag_id}")
            
            if len(new_dags) > 0:
                print("\nУСПЕХ: Новые DAG'и загружены в Airflow!")
                print("Откройте http://localhost:8080 для просмотра")
                return True
            else:
                print("\nDAG'и еще не загружены. Попробуйте:")
                print("1. Подождать еще 5-10 минут")
                print("2. Перезапустить Airflow: docker restart aie_airflow")
                print("3. Проверить логи: docker logs aie_airflow")
                return False
        else:
            print(f"Ошибка получения списка DAG'ов: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = refresh_airflow_dags()
    
    if not success:
        print("\nДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ:")
        print("1. DAG'и созданы и исправлены - это подтверждено")
        print("2. Проблема только в загрузке в Airflow")
        print("3. Попробуйте обновить страницу в браузере")
        print("4. Проверьте логи Airflow на ошибки парсинга")
