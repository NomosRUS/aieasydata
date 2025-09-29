import logging

# Configure logging at the very beginning
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import asyncio
import json
import os
from pathlib import Path

from tests.intelligent_scenarios.api_client import APIClient
from tests.intelligent_scenarios.scenario_engine import ScenarioEngine

logger = logging.getLogger(__name__)

# Base URLs for the API modules
BASE_URLS = {
    1: "http://localhost:8000/api/v1/data-quality/",
    2: "http://localhost:8000/api/v1/aggregation/",
    3: "http://localhost:8000/api/v1/performance/",
    4: "http://localhost:8000/api/v1/warehouse/",
    0: "http://localhost:8000/", # Общие эндпоинты
    5: "http://localhost:8000/api/v1/metrics/"
}

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

async def main():
    """Основная функция для запуска тестового набора."""
    logger.info("Starting Test Suite...")
    logger.info("Please ensure all services are running via 'docker-compose up -d'.")

    api_client = APIClient(base_urls=BASE_URLS)
    engine = ScenarioEngine(api_client=api_client)
    
    scenario_files = list(SCENARIOS_DIR.glob("*.json"))
    if not scenario_files:
        logger.warning(f"No scenarios found in {SCENARIOS_DIR}")
        return

    total_scenarios = len(scenario_files)
    passed_scenarios = 0

    for scenario_path in scenario_files:
        logger.info(f"--- Loading scenario: {scenario_path.name} ---")
        with open(scenario_path, 'r', encoding='utf-8') as f:
            scenario_data = json.load(f)
        
        result = await engine.run_scenario(scenario_data)
        
        if result.success:
            passed_scenarios += 1
            logger.info(f"[SUCCESS] Scenario '{scenario_data.get('name', 'N/A')}' passed.")
        else:
            logger.error(f"[FAILURE] Scenario '{scenario_data.get('name', 'N/A')}' failed. Error: {result.error}")
            trajectory_str = json.dumps(result.trajectory, indent=2, ensure_ascii=False)
            logger.error(f"Failed trajectory: {trajectory_str}")
        
        print("-" * 50)

    await api_client.close()
    
    logger.info("--- Test Suite Summary ---")
    logger.info(f"Total scenarios: {total_scenarios}")
    logger.info(f"Passed: {passed_scenarios}")
    logger.info(f"Failed: {total_scenarios - passed_scenarios}")
    logger.info("--------------------------")
