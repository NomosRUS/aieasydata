#!/usr/bin/env python3
"""
Финальный скрипт для исправления всех оставшихся
логических ошибок в сценариях тестирования.
"""

import json
from pathlib import Path

def fix_scenario_file(file_path: Path):
    """Исправляет один файл сценария."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        changed = False
        for step in data.get('steps', []):
            # --- ИСПРАВЛЕНИЕ 1: validate-file `payload` -> `params` ---
            if step.get('endpoint') == 'validate-file' and 'payload' in step and step['payload'] and 'file_path' in step['payload']:
                if 'params' not in step or step['params'] is None:
                    step['params'] = {}
                step['params']['file_path'] = step['payload']['file_path']
                del step['payload']['file_path']
                if not step['payload']:
                    del step['payload']
                changed = True
                print(f"  - {file_path.name}: Перенес 'file_path' из payload в params для шага {step.get('step')}")

            # --- ИСПРАВЛЕНИЕ 2: Неверный placeholder для batch_id ---
            if 'payload' in step and step['payload'] and isinstance(step['payload'], dict):
                if step['payload'].get('batch_id') == '{{ validation_result.batch_id }}':
                    # В реальности batch_id не возвращается, используем заглушку или удаляем
                    # В данном случае, API batch-clean все равно вернет 404, так что это не критично
                    # Но для чистоты заменим на более осмысленное
                    step['payload']['batch_id'] = 'placeholder_batch_id'
                    changed = True
                    print(f"  - {file_path.name}: Исправлен неверный placeholder 'batch_id' в шаге {step.get('step')}")

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
    
    print(f"Найдено {len(json_files)} файлов сценариев для финального исправления.")
    print("--- Начало исправлений ---")
    
    fixed_count = 0
    for json_file in json_files:
        if fix_scenario_file(json_file):
            fixed_count += 1
            
    print("--- Завершено ---")
    print(f"Проверено файлов: {len(json_files)}")

if __name__ == "__main__":
    main()
