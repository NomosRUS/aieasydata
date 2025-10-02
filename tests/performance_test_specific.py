#!/usr/bin/env python3
"""
Тест производительности на конкретных файлах и реальных БД
"""

import requests
import time
import os

def test_single_xml_file():
    """Тест производительности на одном XML файле."""
    
    print("=== ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ XML ФАЙЛА ===")
    
    base_url = "http://localhost:8000"
    
    # Найдем первый XML файл
    xml_dir = "data_landing_zone/syn_xml"
    xml_files = []
    
    if os.path.exists(xml_dir):
        xml_files = [f for f in os.listdir(xml_dir) if f.endswith('.xml')]
    
    if not xml_files:
        print("❌ XML файлы не найдены")
        return False
    
    # Берем первый файл
    test_file = xml_files[0]
    file_path = os.path.join(xml_dir, test_file)
    file_size = os.path.getsize(file_path) / 1024**2  # MB
    
    print(f"Тестируем файл: {test_file}")
    print(f"Размер файла: {file_size:.1f} MB")
    
    try:
        # Используем автоопределение для одного файла
        start_time = time.time()
        
        response = requests.get(
            f"{base_url}/api/v1/metrics/auto-detect",
            params={"source": file_path},
            timeout=300  # 5 минут максимум
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"[OK] XML файл обработан за {processing_time:.2f} секунд")
            print(f"   Скорость: {file_size / processing_time:.2f} MB/сек")
            
            if 'row_count' in result:
                rows = result.get('row_count', 0)
                print(f"   Записей найдено: {rows:,}")
                if rows > 0:
                    print(f"   Скорость записей: {rows / processing_time:.0f} записей/сек")
            
            if 'detection_result' in result:
                detection = result['detection_result']
                print(f"   Определен тип: {detection.get('type', 'unknown')}")
                if 'file_type' in detection:
                    print(f"   Формат файла: {detection['file_type']}")
            
            return True
            
        else:
            print(f"❌ Ошибка HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def test_single_json_file():
    """Тест производительности на одном JSON файле."""
    
    print("\n=== ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ JSON ФАЙЛА ===")
    
    base_url = "http://localhost:8000"
    
    # Найдем первый JSON файл
    json_dir = "data_landing_zone/syn_json"
    json_files = []
    
    if os.path.exists(json_dir):
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    
    if not json_files:
        print("❌ JSON файлы не найдены")
        return False
    
    # Берем первый файл
    test_file = json_files[0]
    file_path = os.path.join(json_dir, test_file)
    file_size = os.path.getsize(file_path) / 1024**2  # MB
    
    print(f"Тестируем файл: {test_file}")
    print(f"Размер файла: {file_size:.1f} MB")
    
    try:
        # Используем автоопределение для одного файла
        start_time = time.time()
        
        response = requests.get(
            f"{base_url}/api/v1/metrics/auto-detect",
            params={"source": file_path},
            timeout=300  # 5 минут максимум
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ JSON файл обработан за {processing_time:.2f} секунд")
            print(f"   Скорость: {file_size / processing_time:.2f} MB/сек")
            
            if 'row_count' in result:
                rows = result.get('row_count', 0)
                print(f"   Записей найдено: {rows:,}")
                if rows > 0:
                    print(f"   Скорость записей: {rows / processing_time:.0f} записей/сек")
            
            if 'detection_result' in result:
                detection = result['detection_result']
                print(f"   Определен тип: {detection.get('type', 'unknown')}")
                if 'file_type' in detection:
                    print(f"   Формат файла: {detection['file_type']}")
                    if 'format' in detection:
                        print(f"   JSON формат: {detection['format']}")
            
            return True
            
        else:
            print(f"❌ Ошибка HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def test_real_databases():
    """Тест производительности реальных БД из модуля 4."""
    
    print("\n=== ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ РЕАЛЬНЫХ БД ===")
    
    base_url = "http://localhost:8000"
    
    try:
        # Получаем список созданных в модуле 4 хранилищ
        response = requests.get(f"{base_url}/api/v1/warehouse/instances", timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Не удалось получить список хранилищ: {response.status_code}")
            return False
        
        instances = response.json()
        print(f"Найдено хранилищ из модуля 4: {len(instances)}")
        
        if not instances:
            print("❌ Нет созданных хранилищ для тестирования")
            return False
        
        results = []
        
        # Тестируем каждое хранилище
        for i, instance in enumerate(instances[:5], 1):  # Ограничиваем до 5 хранилищ
            db_type = instance.get('target_db_type', 'unknown')
            table_name = instance.get('table_name', 'unknown')
            design_id = instance.get('design_id', 'unknown')
            
            print(f"\n{i}. Тестируем {db_type} - {table_name}")
            print(f"   Design ID: {design_id}")
            
            if db_type in ['clickhouse', 'postgres']:
                try:
                    # Тестируем через collect-by-design
                    start_time = time.time()
                    
                    response = requests.post(
                        f"{base_url}/api/v1/metrics/collect-by-design/{design_id}",
                        timeout=60
                    )
                    
                    end_time = time.time()
                    processing_time = end_time - start_time
                    
                    if response.status_code == 200:
                        metrics = response.json()
                        
                        print(f"   ✅ Обработано за {processing_time:.2f} секунд")
                        print(f"   📊 Строк: {metrics.get('row_count', 0):,}")
                        print(f"   💾 Размер: {metrics.get('size_in_bytes', 0) / 1024**2:.1f} MB")
                        
                        if metrics.get('avg_query_duration_ms'):
                            print(f"   ⚡ Среднее время запроса: {metrics['avg_query_duration_ms']:.1f} ms")
                        
                        if metrics.get('total_queries'):
                            print(f"   📈 Всего запросов: {metrics['total_queries']}")
                        
                        results.append({
                            'db_type': db_type,
                            'table_name': table_name,
                            'processing_time': processing_time,
                            'row_count': metrics.get('row_count', 0),
                            'size_mb': metrics.get('size_in_bytes', 0) / 1024**2,
                            'status': 'success'
                        })
                        
                    else:
                        print(f"   ❌ Ошибка HTTP {response.status_code}")
                        results.append({
                            'db_type': db_type,
                            'table_name': table_name,
                            'status': 'error',
                            'error': f"HTTP {response.status_code}"
                        })
                        
                except Exception as e:
                    print(f"   ❌ Исключение: {e}")
                    results.append({
                        'db_type': db_type,
                        'table_name': table_name,
                        'status': 'error',
                        'error': str(e)
                    })
                    
            elif db_type == 'hdfs':
                print(f"   ⚠️ HDFS пропущен (не поддерживается в метриках)")
                results.append({
                    'db_type': db_type,
                    'table_name': table_name,
                    'status': 'skipped',
                    'reason': 'HDFS not supported in metrics'
                })
            else:
                print(f"   ⚠️ Неизвестный тип БД: {db_type}")
                results.append({
                    'db_type': db_type,
                    'table_name': table_name,
                    'status': 'skipped',
                    'reason': f'Unknown DB type: {db_type}'
                })
        
        # Итоговая статистика
        print(f"\n=== ИТОГИ ТЕСТИРОВАНИЯ БД ===")
        
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'error']
        skipped = [r for r in results if r['status'] == 'skipped']
        
        print(f"Успешно: {len(successful)}")
        print(f"Ошибки: {len(failed)}")
        print(f"Пропущено: {len(skipped)}")
        
        if successful:
            print(f"\n📊 СТАТИСТИКА ПРОИЗВОДИТЕЛЬНОСТИ:")
            for result in successful:
                print(f"  {result['db_type']} ({result['table_name']}):")
                print(f"    Время: {result['processing_time']:.2f}с")
                print(f"    Строк: {result['row_count']:,}")
                print(f"    Размер: {result['size_mb']:.1f} MB")
                if result['row_count'] > 0:
                    print(f"    Скорость: {result['row_count'] / result['processing_time']:.0f} строк/сек")
        
        return len(successful) > 0
        
    except Exception as e:
        print(f"❌ Общая ошибка тестирования БД: {e}")
        return False

def test_database_connections():
    """Дополнительный тест прямых подключений к БД."""
    
    print(f"\n=== ТЕСТ ПРЯМЫХ ПОДКЛЮЧЕНИЙ К БД ===")
    
    base_url = "http://localhost:8000"
    
    # Тестовые строки подключения
    test_connections = [
        {
            'name': 'ClickHouse',
            'source': 'http://localhost:8123',
            'expected_type': 'clickhouse'
        },
        {
            'name': 'PostgreSQL',
            'source': 'postgresql://user:password@localhost:5432/aieasydata',
            'expected_type': 'postgres'
        }
    ]
    
    results = []
    
    for conn in test_connections:
        print(f"\nТестируем {conn['name']}...")
        print(f"Источник: {conn['source']}")
        
        try:
            start_time = time.time()
            
            response = requests.get(
                f"{base_url}/api/v1/metrics/auto-detect",
                params={"source": conn['source']},
                timeout=30
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"✅ Подключение за {processing_time:.2f} секунд")
                
                if 'detection_result' in result:
                    detection = result['detection_result']
                    detected_type = detection.get('db_type', 'unknown')
                    connection_available = detection.get('connection_available', False)
                    
                    print(f"   Определен тип: {detected_type}")
                    print(f"   Подключение доступно: {connection_available}")
                    
                    if detected_type == conn['expected_type']:
                        print(f"   ✅ Тип определен корректно")
                    else:
                        print(f"   ⚠️ Ожидался {conn['expected_type']}, получен {detected_type}")
                    
                    if 'tables' in detection:
                        tables = detection['tables']
                        print(f"   Таблиц найдено: {len(tables)}")
                        if tables:
                            print(f"   Примеры таблиц: {tables[:3]}")
                
                results.append(True)
                
            else:
                print(f"❌ Ошибка HTTP {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"❌ Исключение: {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100 if results else 0
    print(f"\nУспешность подключений: {success_rate:.1f}%")
    
    return success_rate > 50

def main():
    """Главная функция тестирования."""
    
    print("ЗАПУСК ТЕСТИРОВАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 60)
    
    # Ждем запуска сервера
    print("Ожидание запуска сервера...")
    time.sleep(3)
    
    results = []
    
    # 1. Тест XML файла
    print("\n" + "=" * 60)
    xml_result = test_single_xml_file()
    results.append(("XML файл", xml_result))
    
    # 2. Тест JSON файла  
    print("\n" + "=" * 60)
    json_result = test_single_json_file()
    results.append(("JSON файл", json_result))
    
    # 3. Тест реальных БД
    print("\n" + "=" * 60)
    db_result = test_real_databases()
    results.append(("Реальные БД", db_result))
    
    # 4. Тест прямых подключений
    print("\n" + "=" * 60)
    conn_result = test_database_connections()
    results.append(("Прямые подключения", conn_result))
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ ОТЧЕТ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ УСПЕШНО" if success else "❌ ОШИБКА"
        print(f"{test_name:20} : {status}")
    
    successful_tests = sum(1 for _, success in results if success)
    total_tests = len(results)
    success_rate = successful_tests / total_tests * 100
    
    print(f"\nОбщая успешность: {successful_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 75:
        print("🎉 ОТЛИЧНО: Модуль 5 показывает высокую производительность!")
    elif success_rate >= 50:
        print("👍 ХОРОШО: Модуль 5 работает с приемлемой производительностью")
    else:
        print("⚠️ ТРЕБУЕТ ВНИМАНИЯ: Есть проблемы с производительностью")
    
    print("\nТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ ЗАВЕРШЕНО!")

if __name__ == "__main__":
    main()
