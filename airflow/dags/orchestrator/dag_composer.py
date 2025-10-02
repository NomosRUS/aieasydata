"""
DAGComposer - Композиция DAG'ов от Модуля 4 в мастер-пайплайны
НЕ создает новые DAG'и, а использует существующие от Модуля 4
"""

import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from jinja2 import Template
import os

logger = logging.getLogger(__name__)

class Module4Client:
    """Клиент для взаимодействия с Модулем 4"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def generate_etl_pipeline(self, design_id: str) -> Dict[str, Any]:
        """Запрашивает генерацию ETL пайплайна от Модуля 4"""
        url = f"{self.base_url}/api/v1/warehouse/load-data/{design_id}"
        try:
            response = requests.post(url, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to generate ETL pipeline for design {design_id}: {str(e)}")
            raise
    
    def get_available_dags(self) -> List[Dict[str, Any]]:
        """Получает список доступных DAG'ов от Модуля 4"""
        url = f"{self.base_url}/api/v1/warehouse/instances"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get available DAGs: {str(e)}")
            raise
    
    def get_dag_status(self, design_id: str) -> Dict[str, Any]:
        """Получает статус проектирования хранилища"""
        url = f"{self.base_url}/api/v1/warehouse/design/{design_id}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get DAG status for design {design_id}: {str(e)}")
            raise

class DAGComposer:
    """Композиция DAG'ов от Модуля 4 в мастер-пайплайны"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.module4_client = Module4Client(base_url)
        self.templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.generated_dir = os.path.join(os.path.dirname(__file__), "generated")
    
    def request_dag_from_module4(self, design_id: str) -> str:
        """Запрашивает готовый DAG от Модуля 4"""
        try:
            response = self.module4_client.generate_etl_pipeline(design_id)
            if response.get("success"):
                dag_file_path = response.get("dag_file_path")
                logger.info(f"Successfully requested DAG from Module 4: {dag_file_path}")
                return dag_file_path
            else:
                raise Exception(f"Module 4 failed to generate DAG: {response.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Failed to request DAG from Module 4 for design {design_id}: {str(e)}")
            raise
    
    def compose_etl_pipeline(self, design_ids: List[str]) -> Dict[str, Any]:
        """Объединение нескольких ETL DAG'ов в один мастер-пайплайн"""
        try:
            dag_paths = []
            dag_configs = []
            
            # Запрашиваем DAG'и от Модуля 4
            for design_id in design_ids:
                dag_path = self.request_dag_from_module4(design_id)
                dag_status = self.module4_client.get_dag_status(design_id)
                
                dag_paths.append(dag_path)
                dag_configs.append({
                    "design_id": design_id,
                    "dag_path": dag_path,
                    "status": dag_status.get("status"),
                    "target_db": dag_status.get("final_selection", {}).get("chosen_db")
                })
            
            # Создаем мастер-DAG
            master_dag_content = self.compose_multiple_dags(dag_paths, dag_configs)
            master_dag_id = f"master_etl_{'_'.join(design_ids[:3])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            master_dag_path = os.path.join(self.generated_dir, f"{master_dag_id}.py")
            
            # Сохраняем мастер-DAG
            with open(master_dag_path, 'w', encoding='utf-8') as f:
                f.write(master_dag_content)
            
            logger.info(f"Created master DAG: {master_dag_path}")
            
            return {
                "master_dag_id": master_dag_id,
                "master_dag_path": master_dag_path,
                "sub_dags": dag_configs,
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to compose ETL pipeline: {str(e)}")
            raise
    
    def compose_multiple_dags(self, dag_paths: List[str], dag_configs: List[Dict[str, Any]]) -> str:
        """Объединяет несколько DAG'ов в мастер-пайплайн"""
        try:
            # Загружаем шаблон мастер-пайплайна
            template_path = os.path.join(self.templates_dir, "master_pipeline.py.j2")
            
            if not os.path.exists(template_path):
                # Создаем базовый шаблон если его нет
                self._create_master_pipeline_template()
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            
            # Вычисляем зависимости между DAG'ами
            dependencies = self.calculate_dependencies(dag_configs)
            
            # Рендерим шаблон
            master_dag_content = template.render(
                sub_dags=dag_configs,
                dependencies=dependencies,
                master_dag_id=f"master_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                created_at=datetime.now().isoformat()
            )
            
            return master_dag_content
            
        except Exception as e:
            logger.error(f"Failed to compose multiple DAGs: {str(e)}")
            raise
    
    def calculate_dependencies(self, dag_configs: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Вычисляет зависимости между DAG'ами на основе их конфигурации"""
        dependencies = {}
        
        # Простая логика зависимостей:
        # 1. PostgreSQL DAG'и выполняются первыми (OLTP данные)
        # 2. ClickHouse DAG'и выполняются после PostgreSQL (аналитика)
        # 3. HDFS DAG'и выполняются параллельно (архивирование)
        
        postgres_dags = []
        clickhouse_dags = []
        hdfs_dags = []
        
        for config in dag_configs:
            target_db = config.get("target_db", "").lower()
            design_id = config["design_id"]
            
            if "postgres" in target_db:
                postgres_dags.append(design_id)
            elif "clickhouse" in target_db:
                clickhouse_dags.append(design_id)
            elif "hdfs" in target_db:
                hdfs_dags.append(design_id)
        
        # Устанавливаем зависимости
        for dag_id in clickhouse_dags:
            dependencies[dag_id] = postgres_dags  # ClickHouse зависит от PostgreSQL
        
        for dag_id in hdfs_dags:
            dependencies[dag_id] = []  # HDFS может выполняться параллельно
        
        for dag_id in postgres_dags:
            dependencies[dag_id] = []  # PostgreSQL выполняется первым
        
        return dependencies
    
    def _create_master_pipeline_template(self):
        """Создает базовый шаблон мастер-пайплайна"""
        template_content = '''"""
Мастер-пайплайн, созданный автоматически
Объединяет несколько DAG'ов от Модуля 4
Создан: {{ created_at }}
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
import logging

logger = logging.getLogger(__name__)

# Конфигурация мастер-DAG'а
default_args = {
    'owner': 'AiEasyData',
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
    description='Master pipeline combining multiple Module 4 DAGs',
    schedule_interval=None,  # Запускается вручную или по триггеру
    catchup=False,
    tags=['master', 'etl', 'module4'],
)

def log_pipeline_start(**context):
    """Логирование начала выполнения мастер-пайплайна"""
    logger.info(f"Starting master pipeline: {{ master_dag_id }}")
    logger.info(f"Sub-DAGs: {{ sub_dags | map(attribute='design_id') | list }}")
    return "Pipeline started successfully"

def log_pipeline_end(**context):
    """Логирование завершения выполнения мастер-пайплайна"""
    logger.info(f"Master pipeline completed: {{ master_dag_id }}")
    return "Pipeline completed successfully"

# Задача начала пайплайна
start_task = PythonOperator(
    task_id='start_master_pipeline',
    python_callable=log_pipeline_start,
    dag=dag,
)

# Создаем задачи для каждого под-DAG'а
{% for sub_dag in sub_dags %}
trigger_{{ sub_dag.design_id }} = TriggerDagRunOperator(
    task_id='trigger_dag_{{ sub_dag.design_id }}',
    trigger_dag_id='etl_{{ sub_dag.design_id }}',  # Предполагаемый ID DAG'а от Модуля 4
    wait_for_completion=True,
    poke_interval=30,
    timeout=3600,  # 1 час таймаут
    dag=dag,
)
{% endfor %}

# Задача завершения пайплайна
end_task = PythonOperator(
    task_id='end_master_pipeline',
    python_callable=log_pipeline_end,
    dag=dag,
)

# Устанавливаем зависимости
start_task >> [
    {% for sub_dag in sub_dags %}
    trigger_{{ sub_dag.design_id }},
    {% endfor %}
] >> end_task

# Устанавливаем зависимости между под-DAG'ами
{% for dag_id, deps in dependencies.items() %}
{% if deps %}
{% for dep in deps %}
trigger_{{ dep }} >> trigger_{{ dag_id }}
{% endfor %}
{% endif %}
{% endfor %}
'''
        
        template_path = os.path.join(self.templates_dir, "master_pipeline.py.j2")
        os.makedirs(self.templates_dir, exist_ok=True)
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        logger.info(f"Created master pipeline template: {template_path}")
    
    def get_available_dags(self) -> List[Dict[str, Any]]:
        """Получает список доступных DAG'ов от Модуля 4"""
        return self.module4_client.get_available_dags()
    
    def validate_dag_composition(self, design_ids: List[str]) -> Dict[str, Any]:
        """Валидирует возможность композиции DAG'ов"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "dag_statuses": {}
        }
        
        try:
            for design_id in design_ids:
                try:
                    status = self.module4_client.get_dag_status(design_id)
                    validation_result["dag_statuses"][design_id] = status
                    
                    if status.get("status") != "ddl_generated":
                        validation_result["errors"].append(
                            f"Design {design_id} is not ready for DAG generation (status: {status.get('status')})"
                        )
                        validation_result["valid"] = False
                        
                except Exception as e:
                    validation_result["errors"].append(f"Failed to get status for design {design_id}: {str(e)}")
                    validation_result["valid"] = False
            
            return validation_result
            
        except Exception as e:
            logger.error(f"DAG composition validation failed: {str(e)}")
            validation_result["valid"] = False
            validation_result["errors"].append(str(e))
            return validation_result
