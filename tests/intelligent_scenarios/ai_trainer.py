# This module will be responsible for processing successful trajectories
# and preparing them for training the LangGraph AI agent.

import json
from pathlib import Path
from typing import List, Dict, Any

class AITrainer:
    """Подготавливает данные из успешных траекторий для обучения LangGraph агента."""

    def __init__(self, knowledge_base_path: str = "tests/intelligent_scenarios/knowledge_base"):
        self.successful_trajectories_path = Path(knowledge_base_path) / "successful_trajectories"

    def process_successful_trajectory(self, trajectory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Преобразует одну успешную траекторию в формат, пригодный для LangGraph."""
        scenario = trajectory_data.get("scenario", {})
        trajectory = trajectory_data.get("trajectory", [])

        langgraph_trajectory = {
            "goal": scenario.get("ai_training", {}).get("goal", "No goal specified"),
            "nodes": [],
            "edges": [],
            "decision_points": scenario.get("ai_training", {}).get("key_decisions", [])
        }

        for i, entry in enumerate(trajectory):
            step = entry.get("step", {})
            result = entry.get("result", {})

            node = {
                "id": f"step_{step.get('step')}",
                "type": "action",
                "action": step.get("action"),
                "parameters": step.get("payload") or step.get("params"),
                "result_summary": {
                    "success": result.get("success"),
                    "status_code": result.get("status_code")
                },
                "thought": f"Execute step: {step.get('description')}"
            }
            langgraph_trajectory["nodes"].append(node)

            if i > 0:
                prev_step = trajectory[i-1].get("step", {})
                langgraph_trajectory["edges"].append({
                    "from": f"step_{prev_step.get('step')}",
                    "to": f"step_{step.get('step')}",
                    "condition": "on_success"
                })

        return langgraph_trajectory

    def generate_training_dataset(self, output_file: str = "reports/ai_training_data.json") -> Dict[str, Any]:
        """Собирает все успешные траектории и генерирует единый обучающий датасет."""
        training_examples = []
        trajectory_files = list(self.successful_trajectories_path.glob("*.json"))

        for file_path in trajectory_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                trajectory_data = json.load(f)
                processed_example = self.process_successful_trajectory(trajectory_data)
                training_examples.append(processed_example)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(training_examples, f, indent=4, ensure_ascii=False)

        return {
            "message": f"Training dataset generated successfully at {output_file}",
            "total_examples": len(training_examples)
        }
