#!/usr/bin/env python3
"""
Проверка DAG'ов в Airflow через API
"""

import requests
import time

def check_airflow_dags():
    """Проверка DAG'ов через Airflow API"""
    
    print("ПРОВЕРКА DAG'ОВ В AIRFLOW")
    print("=" * 40)
    
    # URL Airflow API
    airflow_url = "http://localhost:8080/api/v1/dags"
    
    try:
        # Ждем немного, чтобы Airflow успел загрузиться
        print("Ожидание запуска Airflow...")
        time.sleep(10)
        
        # Получаем список DAG'ов
        response = requests.get(airflow_url, auth=('admin', 'admin'), timeout=30)
        
        if response.status_code == 200:
            dags_data = response.json()
            dags = dags_data.get('dags', [])
            
            print(f"Найдено DAG'ов: {len(dags)}")
            print("\nСписок DAG'ов:")
            
            # Ищем наши тестовые DAG'и
            test_dags = []
            for dag in dags:
                dag_id = dag.get('dag_id', '')
                is_paused = dag.get('is_paused', True)
                print(f"  - {dag_id} (пауза: {is_paused})")
                
                if dag_id.startswith('test_module'):
                    test_dags.append(dag_id)
            
            print(f"Найдено тестовых DAG'ов: {len(test_dags)}")
            for test_dag in test_dags:
                print(f"  {test_dag}")
            
            if len(test_dags) > 0:
                print("\nУСПЕХ: Тестовые DAG'и обнаружены в Airflow!")
            else:
                print("\nПРОБЛЕМА: Тестовые DAG'и не найдены")
                
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            print(f"Ответ: {response.text}")
            
        print("❌ Не удалось подключиться к Airflow API")
        print("Проверьте, что Airflow запущен на localhost:8080")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def check_dag_files():
    """Проверка файлов DAG'ов"""
    
    print("\nПРОВЕРКА ФАЙЛОВ DAG'ОВ")
    print("=" * 40)
    
    import os
    import glob
    
    # Путь к директории DAG'ов
    dags_dir = "airflow/dags"
    
    # Ищем тестовые DAG'и
    pattern = os.path.join(dags_dir, "test_module*_20250928_*.py")
    dag_files = glob.glob(pattern)
    
    print(f"Найдено файлов DAG'ов: {len(dag_files)}")
    
    for dag_file in dag_files:
        file_size = os.path.getsize(dag_file)
        print(f"  - {os.path.basename(dag_file)} ({file_size} байт)")
        
        # Проверяем синтаксис
        try:
            with open(dag_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Проверяем ключевые элементы
            if 'dag = DAG(' in content:
                print(f"    DAG объект найден")
            else:
                print(f"    DAG объект не найден")
                
            if 'PythonOperator(' in content:
                print(f"    Задачи найдены")
            else:
                print(f"    Задачи не найдены")
                
        except Exception as e:
            print(f"    Ошибка чтения: {e}")

if __name__ == "__main__":
    # Проверка файлов
    check_dag_files()
    
    # Проверка через API
    check_airflow_dags()
    
    print(f"\nРЕКОМЕНДАЦИИ:")
    print("1. Убедитесь, что Airflow полностью запущен")
    print("2. Откройте http://localhost:8080 в браузере")
    print("3. Войдите как admin/admin")
    print("4. Проверьте список DAG'ов в UI")
    print("5. Если DAG'и не видны, проверьте логи Airflow на ошибки")
