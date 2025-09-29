#!/usr/bin/env python3
"""
Скрипт для проверки соответствия API, используемых в тестах,
и API, задокументированных в паспортах модулей.
"""

import json
import os
import re
from pathlib import Path

def extract_apis_from_passports(passport_files: list) -> dict:
    """Извлекает все API endpoints из паспортов модулей."""
    api_map = {}
    for passport_file in passport_files:
        try:
            module_name = passport_file.stem
            with open(passport_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ищем эндпоинты вида POST /api/v1/..., GET /api/v1/...
            endpoints = re.findall(r'(POST|GET|PUT|DELETE)\s+(/api/v1/\S+)', content)
            api_map[module_name] = [(method, endpoint) for method, endpoint in endpoints]
        except Exception as e:
            print(f"Ошибка при чтении паспорта {passport_file.name}: {e}")
    return api_map

def check_scenarios(scenarios_dir: Path, api_map: dict):
    """Проверяет все сценарии на соответствие карте API."""
    scenario_files = list(scenarios_dir.rglob("*.json"))
    all_issues = {
        "test_issues": [],
        "module_issues": []
    }

    # Создаем плоский список всех существующих API для удобства проверки
    existing_apis = set()
    for module, apis in api_map.items():
        for method, endpoint in apis:
            # Упрощаем endpoint до базового пути для сравнения
            base_endpoint = endpoint.split('{')[0].rstrip('/')
            existing_apis.add((method, base_endpoint))

    for scenario_file in scenario_files:
        with open(scenario_file, 'r', encoding='utf-8') as f:
            scenario_data = json.load(f)
        
        for step in scenario_data.get('steps', []):
            if step.get('action') == 'module_api_call':
                method = step.get('method')
                endpoint = step.get('endpoint', '')
                module_num = step.get('module')

                if not method or not endpoint:
                    continue

                # Формируем полный путь как в паспорте
                full_endpoint = f"/api/v1/{get_module_path(module_num)}{endpoint}"
                base_full_endpoint = full_endpoint.split('{')[0].rstrip('/')

                if (method, base_full_endpoint) not in existing_apis:
                    issue = {
                        "scenario": scenario_file.name,
                        "step": step.get('step'),
                        "method": method,
                        "endpoint": full_endpoint,
                        "reason": "API не найден в паспортах модулей"
                    }
                    # Если API нет нигде, это проблема модуля
                    all_issues["module_issues"].append(issue)

    return all_issues

def get_module_path(module_num: int) -> str:
    paths = {
        1: "data-quality",
        2: "aggregation",
        3: "performance",
        4: "warehouse",
        5: "metrics"
    }
    return paths.get(module_num, "")

def main():
    """Основная функция."""
    base_dir = Path(__file__).parent
    passport_files = list(base_dir.glob("backend/app/*/MODULE_*_PASSPORT.md"))
    passport_files.append(base_dir / "airflow/dags/orchestrator/MODULE_6_PASSPORT.md")
    
    print("1. Извлечение API из паспортов модулей...")
    api_map = extract_apis_from_passports(passport_files)
    for module, apis in api_map.items():
        print(f"  - {module}: найдено {len(apis)} API")
    
    print("\n2. Проверка сценариев тестирования...")
    scenarios_dir = base_dir / "tests/scenarios"
    issues = check_scenarios(scenarios_dir, api_map)

    print("\n--- РЕЗУЛЬТАТЫ ПРОВЕРКИ ---")

    if issues["test_issues"]:
        print("\n### 😱 Ошибки в тестовых сценариях (нужно исправить тесты):")
        for issue in issues["test_issues"]:
            print(f"- Сценарий: {issue['scenario']}, Шаг: {issue['step']}, API: {issue['method']} {issue['endpoint']}")
    
    if issues["module_issues"]:
        print("\n### Проблемы в модулях (отсутствующие API):")
        with open("MODULE_ISSUES.md", "w", encoding='utf-8') as f:
            f.write("# 💣 Проблемы в модулях (отсутствующие API)\n\n")
            f.write("| Сценарий | Шаг | Метод | API Endpoint |\n")
            f.write("|---|---|---|---|\n")
            for issue in issues["module_issues"]:
                print(f"- Сценарий: {issue['scenario']}, Шаг: {issue['step']}, API: {issue['method']} {issue['endpoint']}")
                f.write(f"| {issue['scenario']} | {issue['step']} | {issue['method']} | `{issue['endpoint']}` |\n")
        print("\nОтчет о проблемах модулей сохранен в MODULE_ISSUES.md")

    if not issues["test_issues"] and not issues["module_issues"]:
        print("\nВсе API в тестах соответствуют документации!")

if __name__ == "__main__":
    main()
