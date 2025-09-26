"""
Интеграционный тест для Модуля 3 - Оптимизация производительности
Тестирует интеграцию с модулями 4 и 5
"""

import asyncio
import requests
import json
from datetime import datetime


def test_module3_health_check():
    """Тест работоспособности модуля"""
    print("🔍 Тестирование health check модуля 3...")
    
    try:
        response = requests.get("http://localhost:8000/api/v1/performance/health-check")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Модуль 3 работает: {data['status']}")
            print(f"📊 Интеграции: {data['integrations']}")
            print(f"🛠️ Возможности: {data['capabilities']}")
            return True
        else:
            print(f"❌ Ошибка health check: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения к модулю 3: {str(e)}")
        return False


def test_performance_analysis():
    """Тест анализа производительности"""
    print("\n🔍 Тестирование анализа производительности...")
    
    # Тестируем анализ CSV файла
    test_sources = [
        "/data/syn_csv",  # Директория с CSV файлами
        "temp_sales.csv",  # Отдельный файл
    ]
    
    for source in test_sources:
        try:
            print(f"📊 Анализируем источник: {source}")
            
            response = requests.post(
                "http://localhost:8000/api/v1/performance/analyze",
                json={
                    "source": source,
                    "performance_requirements": {
                        "max_query_time_ms": 1000,
                        "expected_volume": "large"
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Анализ завершен: {data['analysis_id']}")
                print(f"📈 Тип источника: {data['source_type']}")
                print(f"🎯 Статус: {data['status']}")
                
                if data.get('current_metrics'):
                    metrics = data['current_metrics']
                    print(f"📊 Размер данных: {metrics.get('data_size_bytes', 0) / (1024*1024):.2f} MB")
                    print(f"📊 Количество строк: {metrics.get('row_count', 0):,}")
                
                if data.get('bottlenecks'):
                    print(f"⚠️ Узкие места: {data['bottlenecks']}")
                
                if data.get('recommendations'):
                    print(f"💡 Рекомендации: {len(data['recommendations'])}")
                    for rec in data['recommendations'][:3]:  # Показываем первые 3
                        print(f"   - {rec['recommendation_type']}: {rec['estimated_improvement']:.1f}% улучшение")
                
                return data['analysis_id']
                
            else:
                print(f"❌ Ошибка анализа: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Ошибка при анализе {source}: {str(e)}")
    
    return None


def test_optimization_application(analysis_id):
    """Тест применения оптимизаций"""
    if not analysis_id:
        print("⏭️ Пропускаем тест применения оптимизаций (нет analysis_id)")
        return
    
    print(f"\n🔍 Тестирование применения оптимизаций для {analysis_id}...")
    
    try:
        # Сначала тестовый запуск (dry_run)
        response = requests.post(
            f"http://localhost:8000/api/v1/performance/optimize/{analysis_id}",
            json={
                "recommendation_ids": ["partition", "index"],
                "dry_run": True,
                "confirm_application": False
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Тестовое применение успешно")
            print(f"📊 Применено рекомендаций: {len(data.get('applied_recommendations', []))}")
            print(f"❌ Ошибок: {len(data.get('failed_recommendations', []))}")
            
            if data.get('applied_recommendations'):
                print(f"✅ Успешные рекомендации: {data['applied_recommendations']}")
            
            return True
        else:
            print(f"❌ Ошибка применения: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при применении оптимизаций: {str(e)}")
    
    return False


def test_module5_integration():
    """Тест интеграции с модулем 5"""
    print("\n🔍 Тестирование интеграции с модулем 5...")
    
    try:
        # Тестируем получение метрик через модуль 3
        response = requests.get(
            "http://localhost:8000/api/v1/performance/metrics/temp_sales.csv"
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Интеграция с модулем 5 работает")
            print(f"📊 Автоопределенный тип: {data.get('source_type')}")
            
            if data.get('metrics'):
                metrics = data['metrics']
                print(f"📊 Размер: {metrics.get('data_size_bytes', 0)} байт")
                print(f"📊 Строк: {metrics.get('row_count', 0)}")
            
            return True
        else:
            print(f"❌ Ошибка интеграции с модулем 5: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка интеграции с модулем 5: {str(e)}")
    
    return False


def test_module4_integration():
    """Тест интеграции с модулем 4"""
    print("\n🔍 Тестирование интеграции с модулем 4...")
    
    try:
        # Получаем список существующих хранилищ
        response = requests.get("http://localhost:8000/api/v1/performance/warehouses")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Интеграция с модулем 4 работает")
            print(f"📊 Найдено хранилищ: {data.get('count', 0)}")
            
            # Если есть хранилища, тестируем анализ одного из них
            warehouses = data.get('warehouses', [])
            if warehouses:
                warehouse = warehouses[0]
                design_id = warehouse.get('design_id')
                
                if design_id:
                    print(f"🔍 Анализируем хранилище: {design_id}")
                    
                    analysis_response = requests.post(
                        "http://localhost:8000/api/v1/performance/analyze",
                        json={"source": f"design_id:{design_id}"}
                    )
                    
                    if analysis_response.status_code == 200:
                        analysis_data = analysis_response.json()
                        print(f"✅ Анализ хранилища успешен: {analysis_data['analysis_id']}")
                        return True
            
            return True
        else:
            print(f"❌ Ошибка интеграции с модулем 4: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка интеграции с модулем 4: {str(e)}")
    
    return False


def test_ddl_validation():
    """Тест валидации DDL"""
    print("\n🔍 Тестирование валидации DDL...")
    
    test_ddl = """
    CREATE TABLE test_table (
        id INT PRIMARY KEY,
        name VARCHAR(100),
        created_date DATE
    ) ENGINE = MergeTree
    PARTITION BY toYYYYMM(created_date)
    ORDER BY (created_date, id);
    """
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/performance/validate-ddl",
            params={
                "ddl_script": test_ddl,
                "target_db_type": "clickhouse"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Валидация DDL: {'успешна' if data.get('valid') else 'неуспешна'}")
            
            if data.get('errors'):
                print(f"❌ Ошибки валидации: {data['errors']}")
            
            return data.get('valid', False)
        else:
            print(f"❌ Ошибка валидации DDL: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при валидации DDL: {str(e)}")
    
    return False


def main():
    """Основная функция тестирования"""
    print("ИНТЕГРАЦИОННЫЙ ТЕСТ МОДУЛЯ 3 - ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 70)
    
    # Счетчик успешных тестов
    passed_tests = 0
    total_tests = 6
    
    # Тест 1: Health check
    if test_module3_health_check():
        passed_tests += 1
    
    # Тест 2: Анализ производительности
    analysis_id = test_performance_analysis()
    if analysis_id:
        passed_tests += 1
    
    # Тест 3: Применение оптимизаций
    if test_optimization_application(analysis_id):
        passed_tests += 1
    
    # Тест 4: Интеграция с модулем 5
    if test_module5_integration():
        passed_tests += 1
    
    # Тест 5: Интеграция с модулем 4
    if test_module4_integration():
        passed_tests += 1
    
    # Тест 6: Валидация DDL
    if test_ddl_validation():
        passed_tests += 1
    
    # Итоговые результаты
    print("\n" + "=" * 70)
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ МОДУЛЯ 3")
    print(f"✅ Пройдено тестов: {passed_tests}/{total_tests}")
    print(f"📈 Успешность: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Модуль 3 полностью функционален и готов к использованию")
    elif passed_tests >= total_tests * 0.8:
        print("⚠️ Большинство тестов пройдено, модуль в основном работает")
    else:
        print("❌ Много неудачных тестов, требуется отладка")
    
    print("\n🔧 Для запуска модуля используйте:")
    print("   cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    main()
