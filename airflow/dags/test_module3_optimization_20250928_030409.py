"""
Мастер-оркестратор DAG
Создан автоматически: 2025-09-28T03:04:09.218301
Пайплайн: test_module3_optimization
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
# Убираем SimpleHttpOperator - используем requests напрямую
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
    'test_module3_optimization',
    default_args=default_args,
    schedule_interval='@once',
    catchup=False,
    tags=['master', 'orchestrator', 'aieasydata'],
)

def execute_module_call(module: int, endpoint: str, method: str, parameters, **context):
    """Выполнение вызова модуля"""
    # В Docker контейнере используем имя сервиса API
    base_url = "http://api:8000"
    url = f"{base_url}{endpoint}"
    
    try:
        logger.info(f"Executing module {module} call: {method} {url}")
        
        if method.upper() == "GET":
            response = requests.get(url, params=parameters, timeout=300)
        elif method.upper() == "POST":
            # Специальная обработка для bulk-analyze - передаем массив напрямую
            if endpoint == "/api/v1/performance/bulk-analyze":
                response = requests.post(url, json=parameters, timeout=300)
            else:
                # Обычная обработка - параметры как JSON объект
                response = requests.post(url, json=parameters, timeout=300)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        
        logger.info(f"Module {module} call completed successfully")
        return response.json()
        
    except Exception as e:
        logger.error(f"Module {module} call failed: {str(e)}")
        raise

def execute_function_call(function: str, endpoint: str, method: str, parameters: dict, **context):
    """Выполнение вызова функции"""
    # В Docker контейнере используем имя сервиса API
    base_url = "http://api:8000"
    
    # Обработка path parameters для функций
    if function == "apply_optimizations" and "{analysis_id}" in endpoint:
        analysis_id = parameters.get("analysis_id", "default_analysis")
        endpoint = endpoint.replace("{analysis_id}", analysis_id)
        # Убираем analysis_id из параметров, так как он уже в URL
        parameters = {k: v for k, v in parameters.items() if k != "analysis_id"}
    elif function == "execute_scenario" and "{scenario_id}" in endpoint:
        scenario_id = parameters.get("scenario_id", "default_scenario")
        endpoint = endpoint.replace("{scenario_id}", scenario_id)
        # Убираем scenario_id из параметров, так как он уже в URL
        parameters = {k: v for k, v in parameters.items() if k != "scenario_id"}
    
    url = f"{base_url}{endpoint}"
    
    try:
        logger.info(f"Executing function {function}: {method} {url}")
        
        if method.upper() == "GET":
            response = requests.get(url, params=parameters, timeout=300)
        elif method.upper() == "POST":
            # Для некоторых endpoints параметры передаются как query params, а не JSON
            if function in ["validate_file_direct"]:
                # Для validate-file передаем file_path как query param
                query_params = {}
                
                if "file_path" in parameters:
                    query_params["file_path"] = parameters["file_path"]
                if "validation_options" in parameters:
                    query_params["validation_options"] = parameters["validation_options"]
                
                response = requests.post(url, params=query_params, timeout=300)
            elif function in ["check_folder_homogeneity", "monitor_specific_source"]:
                # Для check-homogeneity и monitor_specific_source передаем как JSON body
                response = requests.post(url, json=parameters, timeout=300)
            else:
                # По умолчанию передаем как JSON
                response = requests.post(url, json=parameters, timeout=300)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        
        logger.info(f"Function {function} completed successfully")
        return response.json()
        
    except Exception as e:
        logger.error(f"Function {function} failed: {str(e)}")
        raise

# Создание задач DAG'а
tasks = {}



tasks['analyze_small_file'] = PythonOperator(
    task_id='analyze_small_file',
    python_callable=execute_function_call,
    op_kwargs={
        'function': 'analyze_performance',
        'endpoint': '/api/v1/performance/analyze',
        'method': 'POST',
        'parameters': {"analysis_type": "comprehensive", "options": {"include_recommendations": True, "target_db_type": "postgres"}, "source": "/data/raw/test_small.csv"}
    },
    retries=1,
    execution_timeout=timedelta(seconds=3600),
    dag=dag,
)





# Устанавливаем зависимости
