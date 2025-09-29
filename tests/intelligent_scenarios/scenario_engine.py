import json
import logging
import re
import time
from typing import Dict, Any, List

from .api_client import APIClient
from .utils.format_validator import FormatValidator
from .utils.schemas import Scenario, ScenarioStep, ScenarioResult
from .utils.trajectory_recorder import TrajectoryRecorder
from .utils.external_api_client import ExternalAPIClient
from .utils.airflow_client import AirflowClient

logger = logging.getLogger(__name__)

class ScenarioEngine:
    """Движок для выполнения тестовых сценариев."""
    
    def __init__(self, api_client: APIClient, external_api_client: ExternalAPIClient = None, airflow_client: AirflowClient = None):
        self.api_client = api_client
        self.format_validator = FormatValidator()
        self.trajectory_recorder = TrajectoryRecorder()
        self.external_api_client = external_api_client or ExternalAPIClient()
        self.airflow_client = airflow_client or AirflowClient()
        self.step_outputs = {}


    def _interpolate(self, data: str) -> str:
        """Заменяет плейсхолдеры вида '{{...}}' в строке."""
        if not isinstance(data, str):
            return data

        # Замена timestamp
        if '{{timestamp}}' in data:
            data = data.replace('{{timestamp}}', str(int(time.time())))

        # Безопасная замена вложенных плейсхолдеров
        def replacer(match):
            expression = match.group(1).strip()
            keys = expression.split('.')
            value = self.step_outputs

            logger.debug(f"Resolving placeholder '{{{{{expression}}}}}' with keys: {keys}")
            logger.debug(f"Available step_outputs keys: {list(self.step_outputs.keys())}")

            try:
                for i, key in enumerate(keys):
                    logger.debug(f"Step {i}: key='{key}', current_value_type={type(value)}")
                    if isinstance(value, dict):
                        if key in value:
                            value = value[key]
                            logger.debug(f"Found dict key '{key}': {type(value)}")
                        else:
                            logger.debug(f"Dict key '{key}' not found in {list(value.keys())}")
                            raise KeyError(f"Key '{key}' not found in step outputs")
                    elif isinstance(value, list):
                        value = value[int(key)]
                        logger.debug(f"Accessed list index {key}: {type(value)}")
                    else:
                        raise KeyError(f"Cannot access key '{key}' in non-dict/list value")

                result = str(value)
                logger.debug(f"Successfully resolved to: {result}")

                # Попытка конвертации в число, если это возможно
                try:
                    if '.' in result:
                        return float(result)
                    else:
                        return int(result)
                except ValueError:
                    return result
            except (KeyError, IndexError, TypeError, ValueError) as e:
                logger.warning(f"Could not resolve placeholder '{{{{{expression}}}}}': {e}")
                logger.warning(f"Available step outputs: {self.step_outputs}")
                return match.group(0)  # Возвращаем исходный плейсхолдер, если разрешение не удалось

        return re.sub(r'\{\{(.+?)\}\}', replacer, data)

    def _resolve_placeholders(self, data: Any) -> Any:
        """Рекурсивно заменяет плейсхолдеры в данных."""
        if isinstance(data, dict):
            return {k: self._resolve_placeholders(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_placeholders(item) for item in data]
        elif isinstance(data, str):
            return self._interpolate(data)
        return data

    async def execute_step(self, step_data: ScenarioStep) -> Dict[str, Any]:
        """Выполняет один шаг сценария."""
        action = step_data.action
        logger.info(f"Executing step {step_data.step}: {step_data.description}")
        
        result = {"success": False, "error": "Unknown error"}  # Инициализация по умолчанию
        
        # Унифицируем обработку плейсхолдеров для всех вызовов
        endpoint = self._interpolate(step_data.endpoint) if step_data.endpoint else ""
        params = self._resolve_placeholders(step_data.params) if step_data.params else None
        payload = self._resolve_placeholders(step_data.payload) if step_data.payload else None

        if action == "module_api_call":
            result = await self.api_client.call(
                module=step_data.module,
                endpoint=endpoint,
                method=step_data.method,
                params=params,
                json_data=payload,
                headers=step_data.headers,
                timeout=step_data.timeout
            )
        elif action == "external_api_call":
            result = await self.external_api_client.call_api(
                endpoint=endpoint,
                method=step_data.method,
                params=params,
                payload=payload,
                headers=step_data.headers
            )
        elif action == "format_validation":
            logger.info(f"Executing format validation for source: {step_data.source}")
            source_path = self._interpolate(step_data.source)
            expected_schema = step_data.expected_schema
            result = self.format_validator.validate(source_path, expected_schema)
            result['data'] = result.copy() # Для обратной совместимости
        elif action == "sleep":
            duration = step_data.duration or 1
            logger.info(f"Action 'sleep': waiting for {duration} seconds.")
            time.sleep(duration)
            result = {"success": True, "data": f"Slept for {duration} seconds."}
        elif action == "airflow_dag_trigger":
            dag_id = self._interpolate(step_data.dag_id) if step_data.dag_id else None
            result = self.airflow_client.trigger_dag(
                dag_id=dag_id,
                conf=params
            )
        else:
            logger.warning(f"Unknown action type: {action}")
            result = {"success": False, "error": f"Unsupported action type: {action}"}

        if result.get("success") and step_data.save_to:
            self.step_outputs[step_data.save_to] = result.get("data")
            logger.info(f"Saved output of step {step_data.step} to '{step_data.save_to}': {type(result.get('data'))}")
            logger.debug(f"Step output data: {result.get('data')}")

        return result

    async def run_scenario(self, scenario: Scenario) -> ScenarioResult:
        """Запускает полный сценарий."""
        self.step_outputs = {} # Сброс состояний перед новым сценарием
        trajectory: List[Dict[str, Any]] = []
        
        for step_model in scenario.steps:
            if step_model.condition:
                interpolated_condition = self._interpolate(step_model.condition)
                try:
                    # Мы все еще используем eval для гибкости условий, но после безопасной подстановки.
                    should_execute = eval(interpolated_condition, globals(), self.step_outputs)
                    if not should_execute:
                        logger.info(f"Skipping step {step_model.step} due to condition: {step_model.condition}")
                        # Save None to the output to avoid key errors in subsequent steps
                        if step_model.save_to:
                            self.step_outputs[step_model.save_to] = None
                        continue
                except Exception as e:
                    logger.error(f"Error evaluating condition for step {step_model.step}: {e}")
                    return ScenarioResult(success=False, trajectory=trajectory, error=f"Condition evaluation failed for step {step_model.step}")

            step_result = await self.execute_step(step_model)
            
            trajectory.append({
                "step": step_model.model_dump(),
                "result": step_result
            })

            if not step_result.get("success"):
                logger.error(f"Scenario '{scenario.name}' failed at step {step_model.step}")
                return ScenarioResult(success=False, trajectory=trajectory, error=f"Step {step_model.step} failed")

        logger.info(f"Scenario '{scenario.name}' completed successfully.")
        self.trajectory_recorder.save_success(scenario.model_dump(), trajectory)
        return ScenarioResult(success=True, trajectory=trajectory)
