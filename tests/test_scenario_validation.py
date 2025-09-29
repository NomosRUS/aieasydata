#!/usr/bin/env python3
"""
Simple test for scenario validation
"""
import asyncio
import json
import sys
from pathlib import Path

# Add the tests directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from intelligent_scenarios.utils.schemas import Scenario

def test_scenario_validation():
    """Test that all scenario files are valid JSON and conform to schema"""
    scenarios_dir = Path(__file__).parent / "scenarios"
    scenario_files = list(scenarios_dir.rglob('*.json'))

    print(f"Found {len(scenario_files)} scenario files")

    valid_scenarios = 0
    invalid_scenarios = []

    for scenario_path in scenario_files:
        try:
            # Test JSON validity
            with open(scenario_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Test schema validation
            scenario = Scenario(**data)
            print(f"✅ {scenario_path.name}: Valid ({scenario.scenario_id})")
            valid_scenarios += 1

        except json.JSONDecodeError as e:
            print(f"❌ {scenario_path.name}: Invalid JSON - {e}")
            invalid_scenarios.append((scenario_path.name, f"JSON Error: {e}"))
        except Exception as e:
            print(f"❌ {scenario_path.name}: Schema validation failed - {e}")
            invalid_scenarios.append((scenario_path.name, f"Schema Error: {e}"))

    print(f"\nSummary: {valid_scenarios}/{len(scenario_files)} scenarios are valid")

    if invalid_scenarios:
        print("\nInvalid scenarios:")
        for name, error in invalid_scenarios:
            print(f"  - {name}: {error}")
        return False

    return True

if __name__ == "__main__":
    success = test_scenario_validation()
    sys.exit(0 if success else 1)
