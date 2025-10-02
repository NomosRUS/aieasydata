#!/usr/bin/env python3
"""
Simple test to check if scenarios are valid
"""
import json
import sys
from pathlib import Path

def check_scenario_syntax():
    """Check if all scenario files have valid JSON syntax"""
    scenarios_dir = Path('tests/scenarios')
    scenario_files = list(scenarios_dir.rglob('*.json'))

    print(f"Found {len(scenario_files)} scenario files")
    print()

    all_valid = True

    for scenario_path in scenario_files:
        try:
            with open(scenario_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Basic validation
            required_fields = ['scenario_id', 'name', 'steps', 'ai_training']
            missing_fields = [field for field in required_fields if field not in data]

            if missing_fields:
                print(f"❌ {scenario_path.name}: Missing required fields: {missing_fields}")
                all_valid = False
            else:
                scenario_id = data.get('scenario_id', 'UNKNOWN')
                name = data.get('name', 'UNKNOWN')
                steps = len(data.get('steps', []))
                print(f"✅ {scenario_path.name}: {scenario_id} - {name} ({steps} steps)")

        except json.JSONDecodeError as e:
            print(f"❌ {scenario_path.name}: Invalid JSON - {e}")
            all_valid = False
        except Exception as e:
            print(f"❌ {scenario_path.name}: ERROR - {e}")
            all_valid = False

    print()
    if all_valid:
        print("✅ All scenarios have valid syntax!")
        return True
    else:
        print("❌ Some scenarios have syntax errors!")
        return False

if __name__ == "__main__":
    success = check_scenario_syntax()
    sys.exit(0 if success else 1)
