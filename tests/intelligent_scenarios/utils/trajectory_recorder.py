# This module will record the execution trajectory of scenarios.
import json
import time
from pathlib import Path

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge_base" / "successful_trajectories"

class TrajectoryRecorder:
    def __init__(self):
        KNOWLEDGE_BASE_PATH.mkdir(parents=True, exist_ok=True)

    def save_success(self, scenario: dict, trajectory: list):
        """Saves a successful trajectory to the knowledge base."""
        scenario_id = scenario.get("scenario_id", "unknown_scenario")
        timestamp = int(time.time())
        filename = f"trajectory_{scenario_id}_{timestamp}.json"
        filepath = KNOWLEDGE_BASE_PATH / filename

        record = {
            "scenario_id": scenario_id,
            "name": scenario.get("name"),
            "category": scenario.get("category"),
            "timestamp": timestamp,
            "trajectory": trajectory
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=4)
        
        print(f"Successfully saved trajectory to {filepath}")
