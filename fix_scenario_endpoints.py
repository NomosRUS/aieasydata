#!/usr/bin/env python3
"""
Скрипт для исправления эндпоинтов в JSON-сценариях.
Убирает лишние части пути, оставляя только сам метод.
"""

import json
from pathlib import Path

def fix_endpoint(endpoint: str) -> str:
    """Оставляет только последнюю часть эндпоинта."""
    if not endpoint:
        return ""
    # Удаляем ведущий слэш, если он есть
    endpoint = endpoint.lstrip('/')
    # Разделяем по слэшу и берем последнее
    parts = endpoint.split('/')
    return parts[-1]

def fix_scenario_file(file_path: Path):
    """Исправляет один файл сценария."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        changed = False
        for step in data.get('steps', []):
            if 'endpoint' in step:
                original_endpoint = step['endpoint']
                # Пропускаем плейсхолдеры
                if '{{' in original_endpoint and '}}' in original_endpoint:
                    continue
                
                cleaned_endpoint = fix_endpoint(original_endpoint)
                if original_endpoint != cleaned_endpoint:
                    step['endpoint'] = cleaned_endpoint
                    changed = True
                    print(f"  - {file_path.name}: '{original_endpoint}' -> '{cleaned_endpoint}'")

        if changed:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"  Файл {file_path.name} исправлен.")
        return True
    except Exception as e:
        print(f"Ошибка при обработке {file_path.name}: {e}")
        return False

def main():
    """Основная функция."""
    scenarios_dir = Path("tests/scenarios")
    json_files = list(scenarios_dir.rglob("*.json"))
    
    print(f"Найдено {len(json_files)} файлов сценариев для проверки.")
    print("--- Начало исправления эндпоинтов ---")
    
    fixed_count = 0
    for json_file in json_files:
        if fix_scenario_file(json_file):
            fixed_count += 1
            
    print("--- Завершено ---")
    print(f"Проверено файлов: {len(json_files)}")

if __name__ == "__main__":
    main()
