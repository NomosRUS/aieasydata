#!/usr/bin/env python3
"""
Генератор DAG'ов с интегрированной валидацией
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from jinja2 import Template, Environment, FileSystemLoader

sys.path.append(os.path.dirname(__file__))
from dag_validator import DAGValidator, validate_dag_file

class DAGGenerator:
    """Генератор DAG'ов с автоматической валидацией"""
    
    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        
        self.templates_dir = templates_dir
        self.validator = DAGValidator()
        self.jinja_env = Environment(loader=FileSystemLoader(templates_dir))
        
        # Директория для сохранения DAG'ов (правильный путь к airflow/dags/)
        self.dags_output_dir = os.path.join(os.path.dirname(__file__), "..")
    
    def generate_dag(self, config: Dict[str, Any], validate: bool = True) -> Dict[str, Any]:
        """Генерация DAG'а с валидацией"""
        
        # 1. Валидация конфигурации (если включена)
        if validate:
            validation_result = validate_dag_file(config)
            if not validation_result["is_valid"]:
                return {
                    "success": False,
                    "errors": validation_result["errors"],
                    "message": f"Validation failed: {validation_result['error_count']} errors"
                }
        
        # 2. Генерация DAG'а из шаблона
        try:
            dag_content = self._render_dag_template(config)
            dag_filename = self._generate_dag_filename(config)
            dag_filepath = os.path.join(self.dags_output_dir, dag_filename)
            
            # 3. Сохранение DAG'а
            with open(dag_filepath, 'w', encoding='utf-8') as f:
                f.write(dag_content)
            
            return {
                "success": True,
                "dag_filename": dag_filename,
                "dag_filepath": dag_filepath,
                "validation_result": validation_result if validate else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to generate DAG: {str(e)}"
            }
    
    def _render_dag_template(self, config: Dict[str, Any]) -> str:
        """Рендеринг DAG'а из Jinja2 шаблона"""
        
        template = self.jinja_env.get_template("master_orchestrator.py.j2")
        
        # Подготовка данных для шаблона
        dag_id = config.get("dag_id", f"generated_dag_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Создаем объект config для шаблона
        template_config = {
            "schedule": config.get("schedule_interval", "@once"),
            "stages": config.get("stages", []),
            "pipeline_name": config.get("dag_id", "test_pipeline")
        }
        
        template_data = {
            "config": template_config,
            "master_dag_id": dag_id or "generated_dag",
            "description": config.get("description", "Auto-generated DAG"),
            "schedule_interval": config.get("schedule_interval", "@once"),
            "start_date": config.get("start_date", "datetime(2025, 9, 28)"),
            "tags": config.get("tags", ["generated", "aieasydata"]),
            "stages": config.get("stages", []),
            "dependencies_graph": config.get("dependencies_graph", {}),
            "created_at": datetime.now().isoformat()
        }
        
        return template.render(**template_data)
    
    def _generate_dag_filename(self, config: Dict[str, Any]) -> str:
        """Генерация имени файла DAG'а"""
        
        dag_id = config.get("dag_id", "generated_dag")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{dag_id}_{timestamp}.py"
    
    def create_test_dag_configs(self) -> List[Dict[str, Any]]:
        """Создание 4 тестовых конфигураций DAG'ов"""
        
        # Маленький тестовый файл (путь в Docker контейнере)
        test_file = "/data/raw/test_small.csv"
        
        configs = []
        
        # 1. DAG для Модуля 1 (Валидация)
        config1 = {
            "dag_id": "test_module1_validation",
            "description": "Test DAG for Module 1 - Data Validation",
            "schedule_interval": "@once",
            "tags": ["test", "module1", "validation"],
            "stages": [
                {
                    "stage_name": "validate_small_file",
                    "stage_type": {"value": "function_call"},
                    "module": 1,
                    "endpoint": "/api/v1/data-quality/validate-file",
                    "method": "POST",
                    "function": "validate_file_direct",
                    "retry_count": 1,
                    "timeout": 3600,
                    "parameters": {
                        "file_path": test_file,
                        "validation_options": {
                            "assess_quality": True,
                            "check_duplicates": True,
                            "detect_anomalies": True
                        }
                    }
                }
            ]
        }
        configs.append(config1)
        
        # 2. DAG для Модуля 2 (Агрегация)
        config2 = {
            "dag_id": "test_module2_aggregation",
            "description": "Test DAG for Module 2 - Data Aggregation",
            "schedule_interval": "@once",
            "tags": ["test", "module2", "aggregation"],
            "stages": [
                {
                    "stage_name": "create_test_scenario",
                    "stage_type": {"value": "module_call"},
                    "module": 2,
                    "endpoint": "/api/v1/aggregation/create-scenario",
                    "method": "POST",
                    "retry_count": 1,
                    "timeout": 3600,
                    "parameters": {
                        "name": "test_small_aggregation",
                        "description": "Test aggregation for small file",
                        "sources": [
                            {
                                "source_id": "test_small_data",
                                "source_type": "file",
                                "path": test_file,
                                "selected_columns": ["id", "value", "category"]
                            }
                        ],
                        "aggregations": [
                            {
                                "type": "group_by",
                                "parameters": {
                                    "columns": ["category"],
                                    "aggregates": {
                                        "total_value": "SUM(value)",
                                        "count_records": "COUNT(id)"
                                    }
                                }
                            }
                        ],
                        "target_requirements": {
                            "expected_volume": "small",
                            "performance_priority": "balanced"
                        }
                    }
                }
            ]
        }
        configs.append(config2)
        
        # 3. DAG для Модуля 3 (Оптимизация)
        config3 = {
            "dag_id": "test_module3_optimization",
            "description": "Test DAG for Module 3 - Performance Optimization",
            "schedule_interval": "@once",
            "tags": ["test", "module3", "optimization"],
            "stages": [
                {
                    "stage_name": "analyze_small_file",
                    "stage_type": {"value": "function_call"},
                    "module": 3,
                    "endpoint": "/api/v1/performance/analyze",
                    "method": "POST",
                    "function": "analyze_performance",
                    "retry_count": 1,
                    "timeout": 3600,
                    "parameters": {
                        "source": test_file,
                        "analysis_type": "comprehensive",
                        "options": {
                            "include_recommendations": True,
                            "target_db_type": "postgres"
                        }
                    }
                }
            ]
        }
        configs.append(config3)
        
        # 4. DAG для Модуля 5 (Мониторинг)
        config4 = {
            "dag_id": "test_module5_monitoring",
            "description": "Test DAG for Module 5 - Data Monitoring",
            "schedule_interval": "@once",
            "tags": ["test", "module5", "monitoring"],
            "stages": [
                {
                    "stage_name": "auto_detect_small_file",
                    "stage_type": {"value": "function_call"},
                    "module": 5,
                    "endpoint": "/api/v1/metrics/auto-detect",
                    "method": "GET",
                    "function": "auto_detect_source",
                    "retry_count": 1,
                    "timeout": 3600,
                    "parameters": {
                        "source": test_file
                    }
                }
            ]
        }
        configs.append(config4)
        
        return configs
    
    def generate_test_dags(self) -> Dict[str, Any]:
        """Генерация всех 4 тестовых DAG'ов"""
        
        configs = self.create_test_dag_configs()
        results = []
        
        for config in configs:
            print(f"\nГенерация DAG'а: {config['dag_id']}")
            
            # Валидация конфигурации
            validation_result = validate_dag_file(config)
            print(f"  Валидация: {'Пройдена' if validation_result['is_valid'] else 'Ошибки'}")
            
            if not validation_result["is_valid"]:
                print(f"  Ошибки: {validation_result['error_count']}")
                for error in validation_result["errors"]["errors"]:
                    print(f"    - {error.message}")
            
            # Генерация DAG'а
            result = self.generate_dag(config, validate=True)
            results.append({
                "config": config,
                "result": result,
                "validation": validation_result
            })
            
            if result["success"]:
                print(f"  Создан: {result['dag_filename']}")
            else:
                print(f"  Ошибка: {result.get('message', 'Unknown error')}")
        
        return {
            "total_dags": len(results),
            "successful": len([r for r in results if r["result"]["success"]]),
            "failed": len([r for r in results if not r["result"]["success"]]),
            "results": results
        }

def create_test_data_file():
    """Создание маленького тестового файла"""
    
    test_data_dir = "c:\\Users\\admin\\aieasydata\\AiEasyData_Skeleton_OpenAI\\data_landing_zone\\raw"
    os.makedirs(test_data_dir, exist_ok=True)
    
    test_file_path = os.path.join(test_data_dir, "test_small.csv")
    
    # Создаем маленький CSV файл для тестирования
    test_data = """id,value,category,date
1,100,A,2025-01-01
2,200,B,2025-01-02
3,150,A,2025-01-03
4,300,C,2025-01-04
5,250,B,2025-01-05
6,180,A,2025-01-06
7,220,C,2025-01-07
8,190,B,2025-01-08
9,160,A,2025-01-09
10,280,C,2025-01-10"""
    
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_data)
    
    print(f"Создан тестовый файл: {test_file_path}")
    return test_file_path

if __name__ == "__main__":
    # Создание тестового файла
    test_file = create_test_data_file()
    
    # Создание генератора
    generator = DAGGenerator()
    
    # Генерация тестовых DAG'ов
    print("\nГЕНЕРАЦИЯ 4 ТЕСТОВЫХ DAG'ОВ")
    print("=" * 50)
    
    results = generator.generate_test_dags()
    
    print(f"\nИТОГИ:")
    print(f"  Всего DAG'ов: {results['total_dags']}")
    print(f"  Успешно: {results['successful']}")
    print(f"  Ошибок: {results['failed']}")
    
    if results['successful'] > 0:
        print(f"\nСозданы DAG'и:")
        for result in results['results']:
            if result['result']['success']:
                print(f"  - {result['result']['dag_filename']}")
    
    if results['failed'] > 0:
        print(f"\nОшибки в DAG'ах:")
        for result in results['results']:
            if not result['result']['success']:
                print(f"  - {result['config']['dag_id']}: {result['result'].get('message', 'Unknown error')}")
