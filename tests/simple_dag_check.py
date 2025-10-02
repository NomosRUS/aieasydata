#!/usr/bin/env python3
"""
Простая проверка DAG'ов без эмодзи
"""

import requests
import time
import os
import glob

def check_dag_files():
    """Проверка файлов DAG'ов"""
    
    print("ПРОВЕРКА ФАЙЛОВ DAG'ОВ")
    print("=" * 40)
    
    # Ищем новые DAG'и
    pattern = "airflow/dags/*_20250928_023440.py"
    dag_files = glob.glob(pattern)
    
    print(f"Найдено новых DAG'ов: {len(dag_files)}")
    
    for dag_file in dag_files:
        file_size = os.path.getsize(dag_file)
        print(f"  - {os.path.basename(dag_file)} ({file_size} байт)")
        
        # Проверяем содержимое
        try:
            with open(dag_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'dag = DAG(' in content:
                print(f"    DAG объект: OK")
            if 'PythonOperator(' in content:
                print(f"    Задачи: OK")
            if '"columns": [' in content:
                print(f"    Исправленная структура: OK")
                
        except Exception as e:
            print(f"    Ошибка: {e}")

def check_airflow_api():
    """Проверка через Airflow API"""
    
    print("\nПРОВЕРКА AIRFLOW API")
    print("=" * 40)
    
    airflow_url = "http://localhost:8080/api/v1/dags"
    
    try:
        print("Ожидание запуска Airflow (30 сек)...")
        time.sleep(30)
        
        response = requests.get(airflow_url, auth=('admin', 'admin'), timeout=60)
        
        if response.status_code == 200:
            dags_data = response.json()
            dags = dags_data.get('dags', [])
            
            print(f"Всего DAG'ов в Airflow: {len(dags)}")
            
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
                print("\nУСПЕХ: Новые DAG'и обнаружены в Airflow!")
                return True
            else:
                print("\nПроблема: Новые DAG'и не найдены в Airflow")
                print("Возможные причины:")
                print("1. Airflow еще не успел загрузить DAG'и")
                print("2. Синтаксические ошибки в DAG'ах")
                print("3. Проблемы с правами доступа")
                return False
                
        else:
            print(f"Ошибка API: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Не удалось подключиться к Airflow API")
        print("Проверьте, что Airflow запущен на localhost:8080")
        return False
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def test_new_dag():
    """Тест нового исправленного DAG'а"""
    
    print("\nТЕСТ ИСПРАВЛЕННОГО DAG'А")
    print("=" * 40)
    
    # Читаем новый DAG
    dag_file = "airflow/dags/test_module2_aggregation_20250928_023440.py"
    
    if os.path.exists(dag_file):
        with open(dag_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем исправления
        if '"columns": [' in content:
            print("Исправление 1: 'columns' вместо 'group_by_columns' - OK")
        else:
            print("Проблема: 'columns' не найдено")
            
        if '"aggregates": {' in content:
            print("Исправление 2: 'aggregates' вместо 'aggregation_functions' - OK")
        else:
            print("Проблема: 'aggregates' не найдено")
            
        if '"total_value": "SUM(value)"' in content:
            print("Исправление 3: правильный формат aggregates - OK")
        else:
            print("Проблема: правильный формат aggregates не найден")
            
        print("\nИсправленный DAG готов к тестированию!")
        
    else:
        print(f"DAG файл не найден: {dag_file}")

if __name__ == "__main__":
    # Проверка файлов
    check_dag_files()
    
    # Тест исправлений
    test_new_dag()
    
    # Проверка API
    api_success = check_airflow_api()
    
    print(f"\nИТОГИ:")
    if api_success:
        print("Новые исправленные DAG'и успешно загружены в Airflow!")
        print("Откройте http://localhost:8080 для просмотра")
    else:
        print("DAG'и созданы, но еще не загружены в Airflow")
        print("Подождите еще немного или перезапустите Airflow")
