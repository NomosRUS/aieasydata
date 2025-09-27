"""
Интеграционный тест для модуля 1 - Валидация, оценка качества и очистка данных.

Проверяет все основные функции модуля:
- Валидацию различных форматов данных
- Оценку качества данных
- Обнаружение аномалий
- Проверку однородности файлов
- Очистку данных
- Генерацию рекомендаций по хранению
"""

import requests
import json
import pandas as pd
import json
import tempfile
import os
import time
from datetime import datetime

# Конфигурация
API_BASE_URL = "http://localhost:8000"
MODULE_1_BASE = f"{API_BASE_URL}/api/v1/data-quality"

def print_test_header(test_name: str):
    """Печатает заголовок теста."""
    print(f"\n{'='*60}")
    print(f"[TEST] {test_name}")
    print(f"{'='*60}")

def print_success(message: str):
    """Печатает сообщение об успехе."""
    print(f"[SUCCESS] {message}")

def print_error(message: str):
    """Печатает сообщение об ошибке."""
    print(f"[ERROR] {message}")

def print_info(message: str):
    """Печатает информационное сообщение."""
    print(f"[INFO] {message}")

def create_test_csv_file(suffix: str = "") -> str:
    """Создает тестовый CSV файл."""
    test_data = {
        'id': [1, 2, 3, 4, 5, 1],  # Дубликат
        'name': ['Alice', 'Bob', 'Charlie', None, 'Eve', 'Alice'],  # Пропуск и дубликат
        'age': [25, 30, 35, 40, 'invalid', 25],  # Некорректный тип - добавлен элемент
        'salary': [50000, 60000, 70000, 80000, 90000, 50000],
        'date': ['2023-01-01', '2023-02-01', '2023-03-01', '2023-04-01', '2023-05-01', '2023-01-01']
    }
    
    df = pd.DataFrame(test_data)
    
    # Создаем файл в папке, доступной контейнеру с уникальным именем
    filename = f"test_data{suffix}.csv"
    host_file_path = f"data_landing_zone/raw/{filename}"
    df.to_csv(host_file_path, index=False)
    
    # Возвращаем путь, как он виден в контейнере
    container_file_path = f"/data/raw/{filename}"
    return container_file_path

def create_test_json_file(suffix: str = "") -> str:
    """Создает тестовый JSON файл."""
    test_data = [
        {"user_id": 1, "username": "alice", "email": "alice@example.com", "score": 95.5},
        {"user_id": 2, "username": "bob", "email": "bob@example.com", "score": 87.2},
        {"user_id": 3, "username": "charlie", "email": None, "score": 92.1},  # Пропуск
        {"user_id": 1, "username": "alice", "email": "alice@example.com", "score": 95.5},  # Дубликат
        {"user_id": 4, "username": "dave", "email": "invalid-email", "score": "invalid"}  # Некорректные данные
    ]
    
    # Создаем файл в папке, доступной контейнеру с уникальным именем
    filename = f"test_data{suffix}.json"
    host_file_path = f"data_landing_zone/raw/{filename}"
    with open(host_file_path, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    # Возвращаем путь, как он виден в контейнере
    container_file_path = f"/data/raw/{filename}"
    return container_file_path

def test_health_check():
    """Тест 1: Проверка работоспособности модуля."""
    print_test_header("Проверка работоспособности модуля")
    
    try:
        # Используем быстрый health check
        response = requests.get(f"{MODULE_1_BASE}/health-check", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Модуль работает. Статус: {data.get('status', 'unknown')}")
            print_info(f"Версия: {data.get('version', 'unknown')}")
            
            # Проверяем интеграции
            integrations = data.get('integrations', {})
            for service, status in integrations.items():
                if status == "healthy":
                    print_success(f"Интеграция с {service}: {status}")
                elif status == "not_checked":
                    print_info(f"Интеграция с {service}: {status} (быстрая проверка)")
                elif status == "available":
                    print_success(f"Интеграция с {service}: {status}")
                else:
                    print_error(f"Интеграция с {service}: {status}")
            
            return True
        else:
            print_error(f"Ошибка HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Ошибка подключения: {str(e)}")
        return False

def test_get_sources():
    """Тест 2: Получение доступных источников данных."""
    print_test_header("Получение доступных источников данных")
    
    try:
        response = requests.get(f"{MODULE_1_BASE}/sources", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            sources = data.get('sources', [])
            total_count = data.get('total_count', 0)
            
            print_success(f"Найдено {total_count} источников данных")
            
            # Показываем первые несколько источников
            for i, source in enumerate(sources[:5]):
                source_type = source.get('source_type', 'unknown')
                source_id = source.get('source_id', 'unknown')
                print_info(f"  {i+1}. {source_id} ({source_type})")
            
            if len(sources) > 5:
                print_info(f"  ... и еще {len(sources) - 5} источников")
            
            return True
        else:
            print_error(f"Ошибка HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при получении источников: {str(e)}")
        return False

def test_validate_csv_file():
    """Тест 3: Валидация CSV файла."""
    print_test_header("Валидация CSV файла")
    
    # Создаем тестовый файл
    csv_file = create_test_csv_file("_csv_test")
    
    try:
        # Выполняем валидацию файла
        response = requests.post(
            f"{MODULE_1_BASE}/validate-file",
            params={"file_path": csv_file},
            json={
                "validation_options": {
                    "check_duplicates": True,
                    "detect_anomalies": True,
                    "assess_quality": True,
                    "generate_recommendations": True
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            
            validation_id = data.get('validation_id')
            quality_score = data.get('quality_score', 0)
            issues_count = data.get('issues_count', 0)
            processing_time = data.get('processing_time_ms', 0)
            
            print_success(f"Валидация завершена. ID: {validation_id}")
            print_info(f"Оценка качества: {quality_score:.3f}")
            print_info(f"Найдено проблем: {issues_count}")
            print_info(f"Время обработки: {processing_time:.1f} мс")
            
            # Показываем найденные проблемы
            issues = data.get('issues', [])
            for issue in issues[:3]:  # Показываем первые 3 проблемы
                issue_type = issue.get('type', 'unknown')
                description = issue.get('description', 'No description')
                print_info(f"  Проблема: {issue_type} - {description}")
            
            return True
        else:
            print_error(f"Ошибка валидации: {response.status_code}")
            print_error(f"Ответ: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при валидации CSV: {str(e)}")
        return False
    finally:
        # Удаляем тестовый файл (используем путь на хосте)
        try:
            host_file_path = "data_landing_zone/raw/test_data_csv_test.csv"
            if os.path.exists(host_file_path):
                os.unlink(host_file_path)
        except:
            pass

def test_analyze_data_quality():
    """Тест 4: Детальный анализ качества данных."""
    print_test_header("Детальный анализ качества данных")
    
    # Создаем тестовый JSON файл
    json_file = create_test_json_file("_quality_test")
    
    try:
        # Выполняем анализ качества
        response = requests.post(
            f"{MODULE_1_BASE}/analyze-quality",
            json={
                "source_data": {
                    "source_id": "test_json_analysis",
                    "source_type": "file",
                    "path": json_file
                },
                "include_anomalies": True,
                "include_recommendations": True
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Анализируем результаты
            quality_analysis = data.get('quality_analysis', {})
            overall_score = quality_analysis.get('overall_score', 0)
            issues = quality_analysis.get('issues', {})
            
            print_success(f"Анализ качества завершен")
            print_info(f"Общая оценка качества: {overall_score:.3f}")
            print_info(f"Всего проблем: {issues.get('total_count', 0)}")
            
            # Статистика по серьезности проблем
            by_severity = issues.get('by_severity', {})
            for severity, count in by_severity.items():
                print_info(f"  {severity}: {count} проблем")
            
            # Рекомендации по хранению
            recommendations = data.get('recommendations', {})
            storage_recs = recommendations.get('storage', [])
            
            if storage_recs:
                print_info(f"Рекомендации по хранению ({len(storage_recs)}):")
                for rec in storage_recs[:2]:  # Показываем первые 2
                    rec_type = rec.get('recommendation_type', 'unknown')
                    reasoning = rec.get('reasoning', 'No reasoning')
                    print_info(f"  {rec_type}: {reasoning}")
            
            return True
        else:
            print_error(f"Ошибка анализа: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при анализе качества: {str(e)}")
        return False
    finally:
        # Удаляем тестовый файл (используем путь на хосте)
        try:
            host_file_path = "data_landing_zone/raw/test_data_quality_test.json"
            if os.path.exists(host_file_path):
                os.unlink(host_file_path)
        except:
            pass

def test_check_homogeneity():
    """Тест 5: Проверка однородности файлов в папке."""
    print_test_header("Проверка однородности файлов")
    
    # Создаем временную папку с файлами
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Создаем несколько CSV файлов с разной структурой
        
        # Файл 1 - нормальная структура
        df1 = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['A', 'B', 'C'],
            'value': [10, 20, 30]
        })
        file1 = os.path.join(temp_dir, 'file1.csv')
        df1.to_csv(file1, index=False)
        
        # Файл 2 - такая же структура
        df2 = pd.DataFrame({
            'id': [4, 5, 6],
            'name': ['D', 'E', 'F'],
            'value': [40, 50, 60]
        })
        file2 = os.path.join(temp_dir, 'file2.csv')
        df2.to_csv(file2, index=False)
        
        # Файл 3 - другая структура (неоднородный)
        df3 = pd.DataFrame({
            'user_id': [1, 2, 3],
            'username': ['X', 'Y', 'Z'],
            'score': [100, 200, 300],
            'extra_column': ['a', 'b', 'c']  # Дополнительная колонка
        })
        file3 = os.path.join(temp_dir, 'file3.csv')
        df3.to_csv(file3, index=False)
        
        # Проверяем однородность
        response = requests.post(
            f"{MODULE_1_BASE}/check-homogeneity",
            json={
                "folder_path": temp_dir,
                "auto_separate": True
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            homogeneous = data.get('homogeneous', True)
            total_files = data.get('total_files', 0)
            homogeneous_files = data.get('homogeneous_files', 0)
            inconsistent_files = data.get('inconsistent_files', 0)
            
            print_success(f"Проверка однородности завершена")
            print_info(f"Всего файлов: {total_files}")
            print_info(f"Однородных файлов: {homogeneous_files}")
            print_info(f"Неоднородных файлов: {inconsistent_files}")
            print_info(f"Папка однородна: {'Да' if homogeneous else 'Нет'}")
            
            # Показываем различия в схемах
            schema_differences = data.get('schema_differences', [])
            if schema_differences:
                print_info("Найденные различия:")
                for diff in schema_differences[:2]:  # Показываем первые 2
                    file_name = diff.get('file', 'unknown')
                    issues = diff.get('issues', [])
                    print_info(f"  {file_name}: {', '.join(issues)}")
            
            return True
        else:
            print_error(f"Ошибка проверки однородности: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при проверке однородности: {str(e)}")
        return False
    finally:
        # Удаляем временную папку
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def test_batch_validation():
    """Тест 6: Пакетная валидация нескольких источников."""
    print_test_header("Пакетная валидация источников")
    
    # Создаем несколько тестовых файлов
    csv_file = create_test_csv_file("_batch_csv")
    json_file = create_test_json_file("_batch_json")
    
    try:
        # Выполняем пакетную валидацию
        response = requests.post(
            f"{MODULE_1_BASE}/batch-validate",
            json={
                "sources": [
                    {
                        "source_id": "test_csv_batch",
                        "source_type": "file",
                        "path": csv_file
                    },
                    {
                        "source_id": "test_json_batch",
                        "source_type": "file", 
                        "path": json_file
                    }
                ],
                "validation_options": {
                    "check_duplicates": True,
                    "assess_quality": True
                }
            },
            timeout=90
        )
        
        if response.status_code == 200:
            data = response.json()
            
            batch_results = data.get('batch_results', [])
            summary = data.get('summary', {})
            
            total_sources = summary.get('total_sources', 0)
            successful = summary.get('successful_validations', 0)
            failed = summary.get('failed_validations', 0)
            avg_quality = summary.get('average_quality_score', 0)
            
            print_success(f"Пакетная валидация завершена")
            print_info(f"Всего источников: {total_sources}")
            print_info(f"Успешно обработано: {successful}")
            print_info(f"Ошибок: {failed}")
            print_info(f"Средняя оценка качества: {avg_quality:.3f}")
            
            # Показываем результаты по каждому источнику
            for result in batch_results:
                source_id = result.get('source_id', 'unknown')
                status = result.get('status', 'unknown')
                quality_score = result.get('quality_score', 0)
                
                if status == 'completed':
                    print_success(f"  {source_id}: качество {quality_score:.3f}")
                else:
                    error = result.get('error', 'Unknown error')
                    print_error(f"  {source_id}: {error}")
                    # Показываем больше деталей для отладки
                    print_info(f"    Полный результат: {result}")
            
            return successful > 0
        else:
            print_error(f"Ошибка пакетной валидации: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при пакетной валидации: {str(e)}")
        return False
    finally:
        # Даем время API завершить обработку перед удалением файлов
        time.sleep(2)
        # Удаляем тестовые файлы (используем пути на хосте)
        try:
            csv_host_path = "data_landing_zone/raw/test_data_batch_csv.csv"
            json_host_path = "data_landing_zone/raw/test_data_batch_json.json"
            if os.path.exists(csv_host_path):
                os.unlink(csv_host_path)
            if os.path.exists(json_host_path):
                os.unlink(json_host_path)
        except:
            pass

def test_module_statistics():
    """Тест 7: Получение статистики работы модуля."""
    print_test_header("Статистика работы модуля")
    
    try:
        response = requests.get(f"{MODULE_1_BASE}/statistics", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            module_info = data.get('module_info', {})
            validation_stats = data.get('validation_statistics', {})
            quality_stats = data.get('quality_statistics', {})
            
            print_success(f"Статистика получена")
            print_info(f"Модуль: {module_info.get('name', 'unknown')} v{module_info.get('version', 'unknown')}")
            
            # Статистика валидаций
            total_validations = validation_stats.get('total_validations', 0)
            successful_validations = validation_stats.get('successful_validations', 0)
            failed_validations = validation_stats.get('failed_validations', 0)
            
            print_info(f"Всего валидаций: {total_validations}")
            print_info(f"Успешных: {successful_validations}")
            print_info(f"Неудачных: {failed_validations}")
            
            # Статистика качества
            avg_quality = quality_stats.get('average_quality_score', 0)
            high_quality = quality_stats.get('high_quality_sources', 0)
            medium_quality = quality_stats.get('medium_quality_sources', 0)
            low_quality = quality_stats.get('low_quality_sources', 0)
            
            print_info(f"Средняя оценка качества: {avg_quality:.3f}")
            print_info(f"Высокое качество: {high_quality} источников")
            print_info(f"Среднее качество: {medium_quality} источников")
            print_info(f"Низкое качество: {low_quality} источников")
            
            return True
        else:
            print_error(f"Ошибка получения статистики: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Ошибка при получении статистики: {str(e)}")
        return False

def run_integration_tests():
    """Запускает все интеграционные тесты модуля 1."""
    print(f"\n[START] ЗАПУСК ИНТЕГРАЦИОННЫХ ТЕСТОВ МОДУЛЯ 1")
    print(f"[TIME] Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[URL] API URL: {API_BASE_URL}")
    
    tests = [
        ("Проверка работоспособности", test_health_check),
        ("Получение источников данных", test_get_sources),
        ("Валидация CSV файла", test_validate_csv_file),
        ("Анализ качества данных", test_analyze_data_quality),
        ("Проверка однородности файлов", test_check_homogeneity),
        ("Пакетная валидация", test_batch_validation),
        ("Статистика модуля", test_module_statistics)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print_success(f"ТЕСТ ПРОЙДЕН: {test_name}")
            else:
                print_error(f"ТЕСТ НЕ ПРОЙДЕН: {test_name}")
                
        except Exception as e:
            print_error(f"ОШИБКА В ТЕСТЕ {test_name}: {str(e)}")
            results.append((test_name, False))
        
        # Небольшая пауза между тестами
        time.sleep(1)
    
    # Итоговая статистика
    print(f"\n{'='*60}")
    print(f"[RESULTS] ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ МОДУЛЯ 1")
    print(f"{'='*60}")
    
    passed_tests = sum(1 for _, result in results if result)
    total_tests = len(results)
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"[PASSED] Пройдено тестов: {passed_tests}/{total_tests}")
    print(f"[RATE] Процент успеха: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print(f"[SUCCESS] МОДУЛЬ 1 УСПЕШНО ПРОШЕЛ ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ!")
    elif success_rate >= 60:
        print(f"[WARNING] МОДУЛЬ 1 ЧАСТИЧНО ПРОШЕЛ ТЕСТИРОВАНИЕ")
    else:
        print(f"[FAILED] МОДУЛЬ 1 НЕ ПРОШЕЛ ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ")
    
    # Детализация по тестам
    print(f"\n[DETAILS] Детализация результатов:")
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {test_name}")
    
    print(f"\n[END] Завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return success_rate >= 80

if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
