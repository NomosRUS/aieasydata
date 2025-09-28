"""
MasterOrchestrator - Главный класс для создания мастер-пайплайнов
Координирует выполнение модулей и DAG'ов в сложных пайплайнах
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import os

# Исправляем импорты для работы в Airflow
try:
    from .module_scheduler import ModuleScheduler
    from .dag_composer import DAGComposer
    from .execution_monitor import ExecutionMonitor
except ImportError:
    # Fallback для случая когда файл импортируется Airflow'ом напрямую
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from module_scheduler import ModuleScheduler
    from dag_composer import DAGComposer
    from execution_monitor import ExecutionMonitor

logger = logging.getLogger(__name__)

class StageType(Enum):
    MODULE_CALL = "module_call"
    FUNCTION_CALL = "function_call"
    DAG_EXECUTION = "dag_execution"

@dataclass
class PipelineStage:
    """Этап пайплайна"""
    stage_name: str
    stage_type: StageType
    module: Optional[int] = None
    function: Optional[str] = None
    dag_id: Optional[str] = None
    endpoint: Optional[str] = None
    parameters: Dict[str, Any] = None
    depends_on: List[str] = None
    retry_count: int = 1
    timeout: int = 3600
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.depends_on is None:
            self.depends_on = []

@dataclass
class PipelineConfig:
    """Конфигурация пайплайна"""
    pipeline_name: str
    schedule: str
    stages: List[PipelineStage]
    notifications: Dict[str, List[str]] = None
    description: str = ""
    
    def __post_init__(self):
        if self.notifications is None:
            self.notifications = {"on_success": [], "on_failure": []}

@dataclass
class MasterPipeline:
    """Мастер-пайплайн"""
    master_dag_id: str
    dag_file_path: str
    config: PipelineConfig
    stages_count: int
    estimated_duration: int
    dependencies_graph: Dict[str, List[str]]
    created_at: datetime
    status: str = "created"

class MasterOrchestrator:
    """Главный класс для создания мастер-пайплайнов"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.module_scheduler = ModuleScheduler(base_url)
        self.dag_composer = DAGComposer(base_url)
        self.execution_monitor = ExecutionMonitor(base_url)
        
        self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        # DAG'и должны создаваться в основной папке airflow/dags/ где их ищет Airflow
        self.generated_dir = os.path.join(os.path.dirname(__file__), "..")  # airflow/dags/
        
        # Создаем директории если их нет
        os.makedirs(self.templates_dir, exist_ok=True)
        # generated_dir уже существует (это airflow/dags/)
        
        # Хранилище созданных пайплайнов
        self.pipelines: Dict[str, MasterPipeline] = {}
    
    def create_master_pipeline(self, pipeline_config: Dict[str, Any]) -> MasterPipeline:
        """Создание сложного пайплайна из нескольких этапов"""
        try:
            # Парсим конфигурацию
            config = self._parse_pipeline_config(pipeline_config)
            
            # Валидируем конфигурацию
            validation_result = self._validate_pipeline_config(config)
            if not validation_result["valid"]:
                raise ValueError(f"Invalid pipeline configuration: {validation_result['errors']}")
            
            # Генерируем уникальный ID
            master_dag_id = f"master_{config.pipeline_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Строим граф зависимостей
            dependencies_graph = self._build_dependencies_graph(config.stages)
            
            # Оцениваем время выполнения
            estimated_duration = self._estimate_pipeline_duration(config.stages)
            
            # Генерируем DAG файл
            dag_file_path = self._generate_master_dag_file(master_dag_id, config, dependencies_graph)
            
            # Создаем объект пайплайна
            pipeline = MasterPipeline(
                master_dag_id=master_dag_id,
                dag_file_path=dag_file_path,
                config=config,
                stages_count=len(config.stages),
                estimated_duration=estimated_duration,
                dependencies_graph=dependencies_graph,
                created_at=datetime.now()
            )
            
            # Сохраняем пайплайн
            self.pipelines[master_dag_id] = pipeline
            
            logger.info(f"Created master pipeline: {master_dag_id}")
            return pipeline
            
        except Exception as e:
            logger.error(f"Failed to create master pipeline: {str(e)}")
            raise
    
    def _parse_pipeline_config(self, config_dict: Dict[str, Any]) -> PipelineConfig:
        """Парсинг конфигурации пайплайна"""
        stages = []
        
        for stage_dict in config_dict.get("stages", []):
            stage_type_str = stage_dict.get("type", "module_call")
            
            if stage_type_str == "module_call":
                stage_type = StageType.MODULE_CALL
            elif stage_type_str == "function_call":
                stage_type = StageType.FUNCTION_CALL
            elif stage_type_str == "dag_execution":
                stage_type = StageType.DAG_EXECUTION
            else:
                raise ValueError(f"Unknown stage type: {stage_type_str}")
            
            # Для function_call получаем endpoint из ModuleScheduler
            endpoint = stage_dict.get("endpoint")
            if stage_type == StageType.FUNCTION_CALL and not endpoint:
                function_name = stage_dict.get("function")
                if function_name and function_name in self.module_scheduler.SCHEDULABLE_FUNCTIONS:
                    func_config = self.module_scheduler.SCHEDULABLE_FUNCTIONS[function_name]
                    endpoint = func_config["endpoint"]
                    # Подставляем параметры в endpoint если нужно
                    parameters = stage_dict.get("parameters", {})
                    for param_name, param_value in parameters.items():
                        if f"{{{param_name}}}" in endpoint:
                            endpoint = endpoint.replace(f"{{{param_name}}}", str(param_value))
            
            stage = PipelineStage(
                stage_name=stage_dict["stage_name"],
                stage_type=stage_type,
                module=stage_dict.get("module"),
                function=stage_dict.get("function"),
                dag_id=stage_dict.get("dag_id"),
                endpoint=endpoint,
                parameters=stage_dict.get("parameters", {}),
                depends_on=stage_dict.get("depends_on", []),
                retry_count=stage_dict.get("retry_count", 1),
                timeout=stage_dict.get("timeout", 3600)
            )
            stages.append(stage)
        
        return PipelineConfig(
            pipeline_name=config_dict["pipeline_name"],
            schedule=config_dict["schedule"],
            stages=stages,
            notifications=config_dict.get("notifications", {"on_success": [], "on_failure": []}),
            description=config_dict.get("description", "")
        )
    
    def _validate_pipeline_config(self, config: PipelineConfig) -> Dict[str, Any]:
        """Валидация конфигурации пайплайна"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Проверяем наличие этапов
        if not config.stages:
            validation_result["errors"].append("Pipeline must have at least one stage")
            validation_result["valid"] = False
        
        # Проверяем уникальность имен этапов
        stage_names = [stage.stage_name for stage in config.stages]
        if len(stage_names) != len(set(stage_names)):
            validation_result["errors"].append("Stage names must be unique")
            validation_result["valid"] = False
        
        # Проверяем зависимости
        for stage in config.stages:
            for dep in stage.depends_on:
                if dep not in stage_names:
                    validation_result["errors"].append(f"Stage '{stage.stage_name}' depends on unknown stage '{dep}'")
                    validation_result["valid"] = False
        
        # Проверяем циклические зависимости
        if self._has_circular_dependencies(config.stages):
            validation_result["errors"].append("Pipeline has circular dependencies")
            validation_result["valid"] = False
        
        # Проверяем конфигурацию каждого этапа
        for stage in config.stages:
            stage_validation = self._validate_stage_config(stage)
            if not stage_validation["valid"]:
                validation_result["errors"].extend(stage_validation["errors"])
                validation_result["valid"] = False
            validation_result["warnings"].extend(stage_validation.get("warnings", []))
        
        return validation_result
    
    def _validate_stage_config(self, stage: PipelineStage) -> Dict[str, Any]:
        """Валидация конфигурации этапа"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if stage.stage_type == StageType.MODULE_CALL:
            if stage.module is None:
                validation_result["errors"].append(f"Stage '{stage.stage_name}': module is required for module_call")
                validation_result["valid"] = False
            elif stage.module not in self.module_scheduler.SCHEDULABLE_MODULES:
                validation_result["errors"].append(f"Stage '{stage.stage_name}': module {stage.module} is not schedulable")
                validation_result["valid"] = False
        
        elif stage.stage_type == StageType.FUNCTION_CALL:
            if stage.function is None:
                validation_result["errors"].append(f"Stage '{stage.stage_name}': function is required for function_call")
                validation_result["valid"] = False
            elif stage.function not in self.module_scheduler.SCHEDULABLE_FUNCTIONS:
                validation_result["errors"].append(f"Stage '{stage.stage_name}': function '{stage.function}' is not schedulable")
                validation_result["valid"] = False
        
        elif stage.stage_type == StageType.DAG_EXECUTION:
            if stage.dag_id is None:
                validation_result["errors"].append(f"Stage '{stage.stage_name}': dag_id is required for dag_execution")
                validation_result["valid"] = False
        
        return validation_result
    
    def _has_circular_dependencies(self, stages: List[PipelineStage]) -> bool:
        """Проверка на циклические зависимости"""
        # Простая проверка с помощью топологической сортировки
        graph = {}
        in_degree = {}
        
        # Строим граф
        for stage in stages:
            graph[stage.stage_name] = stage.depends_on
            in_degree[stage.stage_name] = len(stage.depends_on)
        
        # Топологическая сортировка
        queue = [name for name, degree in in_degree.items() if degree == 0]
        processed = 0
        
        while queue:
            current = queue.pop(0)
            processed += 1
            
            for stage in stages:
                if current in stage.depends_on:
                    in_degree[stage.stage_name] -= 1
                    if in_degree[stage.stage_name] == 0:
                        queue.append(stage.stage_name)
        
        return processed != len(stages)
    
    def _build_dependencies_graph(self, stages: List[PipelineStage]) -> Dict[str, List[str]]:
        """Построение графа зависимостей"""
        graph = {}
        for stage in stages:
            graph[stage.stage_name] = stage.depends_on.copy()
        return graph
    
    def _estimate_pipeline_duration(self, stages: List[PipelineStage]) -> int:
        """Оценка времени выполнения пайплайна в секундах"""
        # Простая оценка: сумма таймаутов этапов с учетом параллельности
        max_duration = 0
        stage_durations = {}
        
        # Базовые оценки времени выполнения по типам этапов
        base_durations = {
            StageType.MODULE_CALL: 600,  # 10 минут
            StageType.FUNCTION_CALL: 300,  # 5 минут
            StageType.DAG_EXECUTION: 1800  # 30 минут
        }
        
        for stage in stages:
            stage_durations[stage.stage_name] = min(stage.timeout, base_durations.get(stage.stage_type, 600))
        
        # Вычисляем критический путь (упрощенно)
        def calculate_path_duration(stage_name: str, visited: set) -> int:
            if stage_name in visited:
                return 0
            
            visited.add(stage_name)
            stage = next(s for s in stages if s.stage_name == stage_name)
            
            if not stage.depends_on:
                return stage_durations[stage_name]
            
            max_dep_duration = max(
                calculate_path_duration(dep, visited.copy()) for dep in stage.depends_on
            )
            return max_dep_duration + stage_durations[stage_name]
        
        for stage in stages:
            if not any(stage.stage_name in s.depends_on for s in stages):  # Конечные этапы
                duration = calculate_path_duration(stage.stage_name, set())
                max_duration = max(max_duration, duration)
        
        return max_duration
    
    def _generate_master_dag_file(self, master_dag_id: str, config: PipelineConfig, dependencies_graph: Dict[str, List[str]]) -> str:
        """Генерация файла мастер-DAG'а"""
        try:
            # Создаем шаблон если его нет
            template_path = os.path.join(self.templates_dir, "master_orchestrator.py.j2")
            if not os.path.exists(template_path):
                self._create_master_orchestrator_template()
            
            # Загружаем и рендерим шаблон
            from jinja2 import Template
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            
            dag_content = template.render(
                master_dag_id=master_dag_id,
                config=config,
                dependencies_graph=dependencies_graph,
                created_at=datetime.now().isoformat(),
                base_url=self.base_url
            )
            
            # Сохраняем файл
            dag_file_path = os.path.join(self.generated_dir, f"{master_dag_id}.py")
            with open(dag_file_path, 'w', encoding='utf-8') as f:
                f.write(dag_content)
            
            logger.info(f"Generated master DAG file: {dag_file_path}")
            return dag_file_path
            
        except Exception as e:
            logger.error(f"Failed to generate master DAG file: {str(e)}")
            raise
    
    def _create_master_orchestrator_template(self):
        """Создает шаблон мастер-оркестратора"""
        template_content = '''"""
Мастер-оркестратор DAG
Создан автоматически: {{ created_at }}
Пайплайн: {{ config.pipeline_name }}
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.http import SimpleHttpOperator
import logging
import requests

logger = logging.getLogger(__name__)

# Конфигурация DAG'а
default_args = {
    'owner': 'AiEasyData-Orchestrator',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 27),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Создаем мастер-DAG
dag = DAG(
    '{{ master_dag_id }}',
    default_args=default_args,
    description='{{ config.description or "Master orchestrator pipeline" }}',
    schedule_interval='{{ config.schedule }}',
    catchup=False,
    tags=['master', 'orchestrator', 'aieasydata'],
)

def execute_module_call(module: int, endpoint: str, method: str, parameters: dict, **context):
    """Выполнение вызова модуля"""
    base_url = "{{ base_url }}"
    url = f"{base_url}{endpoint}"
    
    try:
        logger.info(f"Executing module {module} call: {method} {url}")
        
        if method.upper() == "GET":
            response = requests.get(url, params=parameters, timeout=300)
        elif method.upper() == "POST":
            response = requests.post(url, json=parameters, timeout=300)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        result = response.json() if response.content else {}
        
        logger.info(f"Module {module} call completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Module {module} call failed: {str(e)}")
        raise

def execute_function_call(function: str, endpoint: str, method: str, parameters: dict, **context):
    """Выполнение вызова функции"""
    base_url = "{{ base_url }}"
    url = f"{base_url}{endpoint}"
    
    try:
        logger.info(f"Executing function {function}: {method} {url}")
        
        if method.upper() == "GET":
            response = requests.get(url, params=parameters, timeout=300)
        elif method.upper() == "POST":
            response = requests.post(url, json=parameters, timeout=300)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        result = response.json() if response.content else {}
        
        logger.info(f"Function {function} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Function {function} failed: {str(e)}")
        raise

# Создаем задачи для каждого этапа
tasks = {}

{% for stage in config.stages %}
{% if stage.stage_type.value == "module_call" %}
tasks['{{ stage.stage_name }}'] = PythonOperator(
    task_id='{{ stage.stage_name }}',
    python_callable=execute_module_call,
    op_kwargs={
        'module': {{ stage.module }},
        'endpoint': '{{ stage.endpoint or "" }}',
        'method': '{{ "POST" if stage.module in [1, 3] else "GET" }}',
        'parameters': {{ stage.parameters | tojson }}
    },
    retries={{ stage.retry_count }},
    execution_timeout=timedelta(seconds={{ stage.timeout }}),
    dag=dag,
)

{% elif stage.stage_type.value == "function_call" %}
tasks['{{ stage.stage_name }}'] = PythonOperator(
    task_id='{{ stage.stage_name }}',
    python_callable=execute_function_call,
    op_kwargs={
        'function': '{{ stage.function }}',
        'endpoint': '{{ stage.endpoint or "" }}',
        'method': '{{ "POST" }}',
        'parameters': {{ stage.parameters | tojson }}
    },
    retries={{ stage.retry_count }},
    execution_timeout=timedelta(seconds={{ stage.timeout }}),
    dag=dag,
)

{% elif stage.stage_type.value == "dag_execution" %}
tasks['{{ stage.stage_name }}'] = TriggerDagRunOperator(
    task_id='{{ stage.stage_name }}',
    trigger_dag_id='{{ stage.dag_id }}',
    wait_for_completion=True,
    poke_interval=30,
    timeout={{ stage.timeout }},
    retries={{ stage.retry_count }},
    dag=dag,
)
{% endif %}

{% endfor %}

# Устанавливаем зависимости
{% for stage_name, dependencies in dependencies_graph.items() %}
{% if dependencies %}
{% for dep in dependencies %}
tasks['{{ dep }}'] >> tasks['{{ stage_name }}']
{% endfor %}
{% endif %}
{% endfor %}
'''
        
        template_path = os.path.join(self.templates_dir, "master_orchestrator.py.j2")
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        logger.info(f"Created master orchestrator template: {template_path}")
    
    def get_pipeline(self, master_dag_id: str) -> Optional[MasterPipeline]:
        """Получение пайплайна по ID"""
        return self.pipelines.get(master_dag_id)
    
    def list_pipelines(self) -> List[Dict[str, Any]]:
        """Список всех созданных пайплайнов"""
        pipelines = []
        for pipeline in self.pipelines.values():
            pipelines.append({
                "master_dag_id": pipeline.master_dag_id,
                "pipeline_name": pipeline.config.pipeline_name,
                "schedule": pipeline.config.schedule,
                "stages_count": pipeline.stages_count,
                "estimated_duration": pipeline.estimated_duration,
                "status": pipeline.status,
                "created_at": pipeline.created_at.isoformat()
            })
        return pipelines
    
    def delete_pipeline(self, master_dag_id: str) -> bool:
        """Удаление пайплайна"""
        if master_dag_id not in self.pipelines:
            return False
        
        pipeline = self.pipelines[master_dag_id]
        
        # Удаляем файл DAG'а
        try:
            if os.path.exists(pipeline.dag_file_path):
                os.remove(pipeline.dag_file_path)
        except Exception as e:
            logger.warning(f"Failed to delete DAG file {pipeline.dag_file_path}: {str(e)}")
        
        # Удаляем из памяти
        del self.pipelines[master_dag_id]
        
        logger.info(f"Deleted pipeline: {master_dag_id}")
        return True
