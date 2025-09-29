"""
Main entry point for the test suite.
"""
import asyncio
import logging
import time
from pathlib import Path

from .intelligent_scenarios.api_client import APIClient
from .intelligent_scenarios.scenario_engine import ScenarioEngine
from .intelligent_scenarios.utils.schemas import Scenario
from .intelligent_scenarios.utils.report_generator import ReportGenerator
from .intelligent_scenarios.ai_trainer import AITrainer

# Basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """Main function to run the test suite."""
    logging.info("Starting Test Suite...")
    logging.info("Please ensure all services are running via 'docker-compose up -d'.")

    start_time = time.time()

    base_urls = {
        0: "http://localhost:8000", # General API
        1: "http://localhost:8000",  # Module 1 - data-quality
        2: "http://localhost:8000",  # Module 2 - aggregation
        3: "http://localhost:8000",  # Module 3 - performance
        4: "http://localhost:8000",  # Module 4 - warehouse
        5: "http://localhost:8000",  # Module 5 - metrics
    }
    api_client = APIClient(base_urls=base_urls)
    engine = ScenarioEngine(api_client=api_client)

    scenarios_path = Path(__file__).parent / "scenarios"
    scenario_files = list(scenarios_path.rglob('S013_module4_to_module5.json'))

    passed_scenarios = 0
    failed_scenarios = 0
    all_results = []

    for scenario_path in scenario_files:
        try:
            logging.info(f"--- Loading scenario: {scenario_path.name} ---")
            scenario = Scenario.parse_file(scenario_path)
            logging.info(f"Running scenario: {scenario.name}")
            
            result = await engine.run_scenario(scenario)
            all_results.append({"scenario": scenario, "result": result})

            if result.success:
                logging.info(f"[SUCCESS] Scenario '{scenario.name}' passed.")
                passed_scenarios += 1
            else:
                logging.error(f"[FAILURE] Scenario '{scenario.name}' failed. Error: {result.error}")
                logging.error("Trajectory:")
                for entry in result.trajectory:
                    logging.error(entry)
                failed_scenarios += 1

        except FileNotFoundError:
            logging.error(f"Scenario file not found: {scenario_path}")
            failed_scenarios += 1
        except Exception as e:
            logging.error(f"An unexpected error occurred with scenario {scenario_path.name}: {e}", exc_info=True)
            failed_scenarios += 1


    logging.info("--- Test Suite Summary ---")
    logging.info(f"Total scenarios: {len(scenario_files)}")
    logging.info(f"Passed: {passed_scenarios}")
    logging.info(f"Failed: {failed_scenarios}")
    logging.info("--------------------------")

    # Generate HTML report
    report_generator = ReportGenerator()
    report_file = report_generator.generate_html_report(all_results, time.time() - start_time)
    logging.info(f"HTML report generated at: {report_file}")

    # Generate AI training data
    logging.info("--- Generating AI Training Dataset ---")
    ai_trainer = AITrainer()
    training_data_result = ai_trainer.generate_training_dataset()
    logging.info(training_data_result["message"])
    logging.info(f"Total examples created: {training_data_result['total_examples']}")
    logging.info("------------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
