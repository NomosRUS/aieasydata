#!/usr/bin/env python3
"""
🎮 ИГРОВОЙ ТЕСТ МОДУЛЯ 1 НА СЫРЫХ ДАННЫХ

Тестирует модуль валидации, оценки качества и очистки данных на реальных сырых данных:
- syn_csv/ - CSV файлы
- syn_json/ - JSON файлы  
- syn_xml/ - XML файлы

Ограничения:
- Валидация, анализ аномалий, очистка, рекомендации - только на первом файле каждой папки
- Проверка однородности - на всех файлах в папке
"""

import requests
import json
import os
import time
from pathlib import Path
from datetime import datetime

# Конфигурация
API_BASE_URL = "http://localhost:8000"
MODULE_1_BASE = f"{API_BASE_URL}/api/v1/data-quality"

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Печатает заголовок теста."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}[GAME TEST] {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

def print_success(text: str):
    """Печатает сообщение об успехе."""
    print(f"{Colors.GREEN}[SUCCESS] {text}{Colors.END}")

def print_error(text: str):
    """Печатает сообщение об ошибке."""
    print(f"{Colors.RED}[ERROR] {text}{Colors.END}")

def print_info(text: str):
    """Печатает информационное сообщение."""
    print(f"{Colors.BLUE}[INFO] {text}{Colors.END}")

def print_warning(text: str):
    """Печатает предупреждение."""
    print(f"{Colors.YELLOW}[WARNING] {text}{Colors.END}")

def get_first_file_in_directory(directory: str, extension: str = None) -> str:
    """Получает первый файл в директории."""
    try:
        path = Path(directory)
        if not path.exists():
            return None
            
        files = []
        if extension:
            files = list(path.glob(f"*.{extension}"))
        else:
            files = [f for f in path.iterdir() if f.is_file()]
            
        if files:
            # Сортируем для стабильности результатов
            files.sort()
            return str(files[0])
        return None
    except Exception as e:
        print_error(f"Ошибка при поиске файлов в {directory}: {str(e)}")
        return None

def get_container_path(host_path: str) -> str:
    """Конвертирует путь хоста в путь контейнера."""
    # Заменяем data_landing_zone на /data
    if "data_landing_zone" in host_path:
        return host_path.replace("data_landing_zone", "/data")
    return host_path

def test_file_validation_and_analysis(file_path: str, file_type: str) -> dict:
    """Тестирует валидацию и анализ одного файла."""
    print_header(f"ВАЛИДАЦИЯ И АНАЛИЗ {file_type.upper()} ФАЙЛА")
    
    container_path = get_container_path(file_path)
    print_info(f"Файл: {file_path}")
    print_info(f"Контейнер путь: {container_path}")
    
    results = {
        'validation': None,
        'quality_analysis': None,
        'anomaly_detection': None,
        'cleaning': None,
        'storage_recommendations': None
    }
    
    try:
        # 1. Валидация файла
        print_info("1. Запуск валидации файла...")
        validation_response = requests.post(
            f"{MODULE_1_BASE}/validate-file",
            params={'file_path': container_path},
            json={
                'validation_options': {
                    'check_duplicates': True,
                    'detect_anomalies': True,
                    'assess_quality': True,
                    'generate_recommendations': True
                }
            },
            timeout=120  # Увеличенный таймаут для больших файлов
        )
        
        if validation_response.status_code == 200:
            validation_data = validation_response.json()
            results['validation'] = validation_data
            print_success(f"Валидация завершена. Качество: {validation_data.get('quality_score', 'N/A')}")
            print_info(f"Время обработки: {validation_data.get('processing_time_ms', 'N/A')} мс")
            
            # Показываем найденные проблемы
            issues = validation_data.get('issues', [])
            if issues:
                print_warning(f"Найдено проблем: {len(issues)}")
                for issue in issues[:3]:  # Показываем первые 3
                    print_info(f"  - {issue.get('type', 'unknown')}: {issue.get('description', 'N/A')}")
            else:
                print_success("Проблем не найдено!")
                
        else:
            print_error(f"Ошибка валидации: {validation_response.status_code}")
            print_error(validation_response.text[:200])
    
        # 2. Детальный анализ качества
        print_info("2. Запуск анализа качества данных...")
        quality_response = requests.post(
            f"{MODULE_1_BASE}/analyze-quality",
            json={
                'source_path': container_path,
                'analysis_options': {
                    'detailed_statistics': True,
                    'correlation_analysis': True,
                    'distribution_analysis': True
                }
            },
            timeout=120
        )
        
        if quality_response.status_code == 200:
            quality_data = quality_response.json()
            results['quality_analysis'] = quality_data
            print_success(f"Анализ качества завершен. Общая оценка: {quality_data.get('overall_quality_score', 'N/A')}")
            
            # Показываем статистики
            stats = quality_data.get('statistics', {})
            if stats:
                print_info(f"Статистики:")
                print_info(f"  - Полнота данных: {stats.get('completeness', 'N/A')}")
                print_info(f"  - Корректность: {stats.get('correctness', 'N/A')}")
                print_info(f"  - Согласованность: {stats.get('consistency', 'N/A')}")
        else:
            print_error(f"Ошибка анализа качества: {quality_response.status_code}")
    
        # 3. Очистка данных (только если качество низкое)
        if results['validation'] and results['validation'].get('quality_score', 1.0) < 0.9:
            print_info("3. Запуск очистки данных...")
            cleaning_response = requests.post(
                f"{MODULE_1_BASE}/clean-file",
                params={'file_path': container_path},
                json={
                    'cleaning_strategy': 'auto',
                    'preserve_original': True,
                    'output_format': 'parquet'
                },
                timeout=120
            )
            
            if cleaning_response.status_code == 200:
                cleaning_data = cleaning_response.json()
                results['cleaning'] = cleaning_data
                print_success(f"Очистка завершена. Улучшение качества: {cleaning_data.get('quality_improvement', 'N/A')}")
            else:
                print_error(f"Ошибка очистки: {cleaning_response.status_code}")
        else:
            print_info("3. Очистка не требуется - качество данных высокое")
    
    except Exception as e:
        print_error(f"Ошибка при тестировании файла: {str(e)}")
    
    return results

def test_homogeneity_check(directory: str, file_type: str) -> dict:
    """Тестирует проверку однородности файлов в папке."""
    print_header(f"ПРОВЕРКА ОДНОРОДНОСТИ {file_type.upper()} ФАЙЛОВ")
    
    container_path = get_container_path(directory)
    print_info(f"Папка: {directory}")
    print_info(f"Контейнер путь: {container_path}")
    
    try:
        # Подсчитываем файлы в папке
        path = Path(directory)
        files = list(path.glob(f"*.{file_type}")) if file_type != 'json' else list(path.glob("*.json"))
        print_info(f"Найдено файлов: {len(files)}")
        
        # Запускаем проверку однородности
        homogeneity_response = requests.post(
            f"{MODULE_1_BASE}/check-homogeneity",
            json={
                'folder_path': container_path,
                'auto_separate': True
            },
            timeout=180  # Увеличенный таймаут для множественных файлов
        )
        
        if homogeneity_response.status_code == 200:
            homogeneity_data = homogeneity_response.json()
            
            consistent_files = homogeneity_data.get('consistent_files', [])
            inconsistent_files = homogeneity_data.get('inconsistent_files', [])
            
            print_success(f"Проверка однородности завершена")
            print_info(f"Однородных файлов: {len(consistent_files)}")
            if inconsistent_files:
                print_warning(f"Неоднородных файлов: {len(inconsistent_files)}")
                for file_info in inconsistent_files[:3]:  # Показываем первые 3
                    print_info(f"  - {file_info.get('file_name', 'unknown')}: {file_info.get('reason', 'N/A')}")
            else:
                print_success("Все файлы однородны!")
            
            return homogeneity_data
        else:
            print_error(f"Ошибка проверки однородности: {homogeneity_response.status_code}")
            print_error(homogeneity_response.text[:200])
            return None
            
    except Exception as e:
        print_error(f"Ошибка при проверке однородности: {str(e)}")
        return None

def generate_storage_recommendations(results: dict) -> dict:
    """Генерирует рекомендации по хранению на основе результатов анализа."""
    print_header("РЕКОМЕНДАЦИИ ПО ХРАНЕНИЮ ДАННЫХ")
    
    recommendations = {
        'csv_recommendations': None,
        'json_recommendations': None,
        'xml_recommendations': None
    }
    
    for data_type, type_results in results.items():
        if type_results and type_results.get('validation'):
            quality_score = type_results['validation'].get('quality_score', 0)
            
            print_info(f"[DATA] {data_type.upper()} данные:")
            print_info(f"  Качество: {quality_score}")
            
            # Простые рекомендации на основе качества
            if quality_score >= 0.9:
                recommendation = "ClickHouse - высокое качество, подходит для аналитики"
            elif quality_score >= 0.7:
                recommendation = "PostgreSQL - среднее качество, нужна дополнительная очистка"
            else:
                recommendation = "HDFS - низкое качество, требует серьезной предобработки"
            
            print_success(f"  Рекомендация: {recommendation}")
            recommendations[f'{data_type}_recommendations'] = recommendation
    
    return recommendations

def main():
    """Главная функция игрового теста."""
    print_header("ИГРОВОЙ ТЕСТ МОДУЛЯ 1 НА СЫРЫХ ДАННЫХ")
    print_info(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Проверяем доступность API
    try:
        health_response = requests.get(f"{MODULE_1_BASE}/health-check", timeout=10)
        if health_response.status_code == 200:
            print_success("API модуля 1 доступен")
        else:
            print_error("API модуля 1 недоступен")
            return
    except Exception as e:
        print_error(f"Не удается подключиться к API: {str(e)}")
        return
    
    # Определяем пути к данным
    base_path = "data_landing_zone"
    test_directories = {
        'csv': f"{base_path}/syn_csv",
        'json': f"{base_path}/syn_json", 
        'xml': f"{base_path}/syn_xml"
    }
    
    results = {}
    
    # Тестируем каждый тип данных
    for data_type, directory in test_directories.items():
        print_header(f"ТЕСТИРОВАНИЕ {data_type.upper()} ДАННЫХ")
        
        # Находим первый файл для детального анализа
        first_file = get_first_file_in_directory(directory, data_type)
        
        if not first_file:
            print_warning(f"Файлы {data_type} не найдены в {directory}")
            continue
            
        print_info(f"Первый файл для анализа: {first_file}")
        
        # Тестируем валидацию и анализ первого файла
        file_results = test_file_validation_and_analysis(first_file, data_type)
        
        # Тестируем однородность всех файлов в папке
        homogeneity_results = test_homogeneity_check(directory, data_type)
        
        results[data_type] = {
            'validation': file_results.get('validation'),
            'quality_analysis': file_results.get('quality_analysis'),
            'cleaning': file_results.get('cleaning'),
            'homogeneity': homogeneity_results,
            'first_file': first_file
        }
    
    # Генерируем итоговые рекомендации
    storage_recommendations = generate_storage_recommendations(results)
    
    # Итоговый отчет
    print_header("ИТОГОВЫЙ ОТЧЕТ ИГРОВОГО ТЕСТА")
    
    total_tests = 0
    successful_tests = 0
    
    for data_type, type_results in results.items():
        print_info(f"[FOLDER] {data_type.upper()} данные:")
        
        if type_results.get('validation'):
            total_tests += 1
            successful_tests += 1
            quality = type_results['validation'].get('quality_score', 'N/A')
            print_success(f"  [OK] Валидация: качество {quality}")
        else:
            total_tests += 1
            print_error(f"  [FAIL] Валидация: не выполнена")
            
        if type_results.get('homogeneity'):
            total_tests += 1
            successful_tests += 1
            homogeneity_data = type_results['homogeneity']
            
            # Проверяем, что это словарь с нужными полями
            if isinstance(homogeneity_data, dict):
                consistent = homogeneity_data.get('homogeneous_files', 0)
                inconsistent = homogeneity_data.get('inconsistent_files', 0)
                total_files = homogeneity_data.get('total_files', 0)
                print_success(f"  [OK] Однородность: {total_files} файлов, {consistent} однородных, {inconsistent} неоднородных")
            else:
                print_success(f"  [OK] Однородность: проверена")
        else:
            total_tests += 1
            print_error(f"  [FAIL] Однородность: не проверена")
    
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    print_header(f"РЕЗУЛЬТАТ: {successful_tests}/{total_tests} тестов пройдено ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print_success("[VICTORY] ИГРОВОЙ ТЕСТ УСПЕШНО ПРОЙДЕН!")
    elif success_rate >= 60:
        print_warning("[PARTIAL] ИГРОВОЙ ТЕСТ ЧАСТИЧНО ПРОЙДЕН")
    else:
        print_error("[DEFEAT] ИГРОВОЙ ТЕСТ НЕ ПРОЙДЕН")
    
    print_info(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
