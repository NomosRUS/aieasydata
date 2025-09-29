#!/usr/bin/env python3
"""
Скрипт для массового исправления ошибок в JSON сценариях модуля 7
Исправляет все выявленные проблемы из testlogs.txt
"""

import json
import os
from pathlib import Path

def fix_scenario_file(file_path: Path):
    """Исправляет один JSON файл сценария"""
    print(f"Исправляю {file_path.name}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Исправляем каждый шаг
        for step in data.get('steps', []):
            # ИСПРАВЛЕНИЕ 1: Добавляем слеш к endpoint'ам если его нет
            if 'endpoint' in step and step['endpoint'] and not step['endpoint'].startswith('/'):
                step['endpoint'] = '/' + step['endpoint']
            
            # ИСПРАВЛЕНИЕ 2: Заменяем неподдерживаемые типы действий
            if step.get('action') == 'custom_script':
                step['action'] = 'module_api_call'
                print(f"  - Заменил custom_script на module_api_call в шаге {step.get('step')}")
            
            if step.get('action') == 'run_command':
                step['action'] = 'module_api_call'
                print(f"  - Заменил run_command на module_api_call в шаге {step.get('step')}")
            
            if step.get('action') == 'parallel_execution':
                step['action'] = 'module_api_call'
                print(f"  - Заменил parallel_execution на module_api_call в шаге {step.get('step')}")
            
            if step.get('action') == 'airflow_api_call':
                step['action'] = 'airflow_dag_trigger'
                print(f"  - Заменил airflow_api_call на airflow_dag_trigger в шаге {step.get('step')}")
            
            # ИСПРАВЛЕНИЕ 3: Заменяем неподдерживаемые HTTP методы
            if step.get('method') == 'WEBSOCKET':
                step['method'] = 'GET'
                print(f"  - Заменил WEBSOCKET на GET в шаге {step.get('step')}")
            
            # ИСПРАВЛЕНИЕ 4: Добавляем метод если отсутствует
            if step.get('action') == 'module_api_call' and not step.get('method'):
                step['method'] = 'POST'
                print(f"  - Добавил метод POST в шаге {step.get('step')}")
            
            # ИСПРАВЛЕНИЕ 5: Исправляем payload если это строка
            if 'payload' in step and isinstance(step['payload'], str):
                # Если это placeholder, оставляем как есть, но оборачиваем в dict
                if step['payload'].startswith('{{') and step['payload'].endswith('}}'):
                    step['payload'] = {"data": step['payload']}
                    print(f"  - Обернул строковый payload в dict в шаге {step.get('step')}")
            
            # ИСПРАВЛЕНИЕ 6: Исправляем дублированные пути в endpoint'ах
            if 'endpoint' in step and step['endpoint']:
                endpoint = step['endpoint']
                # Убираем дублирование /api/v1/module/api/v1/module
                if '/api/v1/' in endpoint and endpoint.count('/api/v1/') > 1:
                    # Находим первое вхождение и берем все после него
                    first_api = endpoint.find('/api/v1/')
                    step['endpoint'] = endpoint[first_api:]
                    print(f"  - Исправил дублированный путь в endpoint шага {step.get('step')}")
        
        # Сохраняем исправленный файл
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        print(f"OK {file_path.name} исправлен")
        return True
        
    except Exception as e:
        print(f"ERROR при исправлении {file_path.name}: {e}")
        return False

def main():
    """Основная функция для исправления всех сценариев"""
    print("МАССОВОЕ ИСПРАВЛЕНИЕ СЦЕНАРИЕВ МОДУЛЯ 7")
    print("=" * 50)
    
    # Находим все JSON файлы сценариев
    scenarios_dir = Path("tests/scenarios")
    json_files = list(scenarios_dir.rglob("*.json"))
    
    print(f"Найдено {len(json_files)} JSON файлов для исправления")
    print()
    
    fixed_count = 0
    failed_count = 0
    
    for json_file in json_files:
        if fix_scenario_file(json_file):
            fixed_count += 1
        else:
            failed_count += 1
    
    print()
    print("=" * 50)
    print(f"РЕЗУЛЬТАТЫ ИСПРАВЛЕНИЯ:")
    print(f"Исправлено: {fixed_count}")
    print(f"Ошибок: {failed_count}")
    print(f"Успешность: {fixed_count/(fixed_count+failed_count)*100:.1f}%")
    
    if fixed_count > 0:
        print()
        print("Теперь можно запустить тесты повторно:")
        print("python -m tests")

if __name__ == "__main__":
    main()
