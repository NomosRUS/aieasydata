#!/usr/bin/env python3
"""
Простой тест производительности без эмодзи
"""

import requests
import time
import os

def test_xml_performance():
    """Тест производительности XML файла."""
    
    print("=== ТЕСТ XML ФАЙЛА ===")
    
    # Найдем первый XML файл
    xml_dir = "data_landing_zone/syn_xml"
    if not os.path.exists(xml_dir):
        print("ERROR: XML директория не найдена")
        return False
    
    xml_files = [f for f in os.listdir(xml_dir) if f.endswith('.xml')]
    if not xml_files:
        print("ERROR: XML файлы не найдены")
        return False
    
    test_file = xml_files[0]
    file_path = os.path.join(xml_dir, test_file)
    file_size = os.path.getsize(file_path) / 1024**2  # MB
    
    print(f"Файл: {test_file}")
    print(f"Размер: {file_size:.1f} MB")
    
    try:
        start_time = time.time()
        
        # Используем Docker путь
        docker_path = f"/data/syn_xml/{test_file}"
        
        response = requests.get(
            "http://localhost:8000/api/v1/metrics/auto-detect",
            params={"source": docker_path},
            timeout=180
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"SUCCESS: Обработано за {processing_time:.2f} сек")
            print(f"Скорость: {file_size / processing_time:.2f} MB/сек")
            
            if 'row_count' in result:
                rows = result.get('row_count', 0)
                print(f"Записей: {rows:,}")
                if rows > 0:
                    print(f"Скорость записей: {rows / processing_time:.0f} записей/сек")
            
            return True
        else:
            print(f"ERROR: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_json_performance():
    """Тест производительности JSON файла."""
    
    print("\n=== ТЕСТ JSON ФАЙЛА ===")
    
    # Найдем первый JSON файл
    json_dir = "data_landing_zone/syn_json"
    if not os.path.exists(json_dir):
        print("ERROR: JSON директория не найдена")
        return False
    
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    if not json_files:
        print("ERROR: JSON файлы не найдены")
        return False
    
    test_file = json_files[0]
    file_path = os.path.join(json_dir, test_file)
    file_size = os.path.getsize(file_path) / 1024**2  # MB
    
    print(f"Файл: {test_file}")
    print(f"Размер: {file_size:.1f} MB")
    
    try:
        start_time = time.time()
        
        # Используем Docker путь
        docker_path = f"/data/syn_json/{test_file}"
        
        response = requests.get(
            "http://localhost:8000/api/v1/metrics/auto-detect",
            params={"source": docker_path},
            timeout=180
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"SUCCESS: Обработано за {processing_time:.2f} сек")
            print(f"Скорость: {file_size / processing_time:.2f} MB/сек")
            
            if 'row_count' in result:
                rows = result.get('row_count', 0)
                print(f"Записей: {rows:,}")
                if rows > 0:
                    print(f"Скорость записей: {rows / processing_time:.0f} записей/сек")
            
            return True
        else:
            print(f"ERROR: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_databases():
    """Тест реальных БД."""
    
    print("\n=== ТЕСТ РЕАЛЬНЫХ БД ===")
    
    try:
        # Получаем список хранилищ из модуля 4
        response = requests.get("http://localhost:8000/api/v1/warehouse/instances", timeout=30)
        
        if response.status_code != 200:
            print(f"ERROR: Не удалось получить список БД: {response.status_code}")
            return False
        
        instances = response.json()
        print(f"Найдено хранилищ: {len(instances)}")
        
        if not instances:
            print("ERROR: Нет БД для тестирования")
            return False
        
        success_count = 0
        
        # Тестируем первые 3 БД
        for i, instance in enumerate(instances[:3], 1):
            db_type = instance.get('target_db_type', 'unknown')
            table_name = instance.get('table_name', 'unknown')
            design_id = instance.get('design_id', 'unknown')
            
            print(f"\n{i}. {db_type} - {table_name}")
            
            if db_type in ['clickhouse', 'postgres']:
                try:
                    start_time = time.time()
                    
                    response = requests.post(
                        f"http://localhost:8000/api/v1/metrics/collect-by-design/{design_id}",
                        timeout=30
                    )
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    if response.status_code == 200:
                        metrics = response.json()
                        
                        print(f"   SUCCESS: {processing_time:.2f} сек")
                        print(f"   Строк: {metrics.get('row_count', 0):,}")
                        print(f"   Размер: {metrics.get('size_in_bytes', 0) / 1024**2:.1f} MB")
                        
                        if metrics.get('avg_query_duration_ms'):
                            print(f"   Среднее время запроса: {metrics['avg_query_duration_ms']:.1f} ms")
                        
                        success_count += 1
                        
                    else:
                        print(f"   ERROR: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"   ERROR: {e}")
                    
            else:
                print(f"   SKIP: {db_type} не поддерживается")
        
        print(f"\nУспешно протестировано: {success_count} БД")
        return success_count > 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Главная функция."""
    
    print("ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ МОДУЛЯ 5")
    print("=" * 50)
    
    # Ждем запуска сервера
    time.sleep(3)
    
    results = []
    
    # 1. XML тест
    xml_result = test_xml_performance()
    results.append(("XML", xml_result))
    
    # 2. JSON тест
    json_result = test_json_performance()
    results.append(("JSON", json_result))
    
    # 3. БД тест
    db_result = test_databases()
    results.append(("БД", db_result))
    
    # Итоги
    print("\n" + "=" * 50)
    print("ИТОГИ:")
    
    for test_name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"{test_name:10} : {status}")
    
    successful = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nОбщий результат: {successful}/{total}")
    
    if successful == total:
        print("ОТЛИЧНО: Все тесты пройдены!")
    elif successful > 0:
        print("ХОРОШО: Частично работает")
    else:
        print("ПРОБЛЕМА: Ничего не работает")

if __name__ == "__main__":
    main()
