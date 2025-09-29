"""
Практические тесты создания DAG'ов для Airflow
Создает 4 реальных DAG'а которые можно увидеть в Airflow UI
"""

import sys
import os
from datetime import datetime

# Добавляем путь к оркестратору
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags'))

try:
    from orchestrator.master_orchestrator import MasterOrchestrator
    from orchestrator.module_scheduler import ModuleScheduler
except ImportError as e:
    print(f"Error: Could not import orchestrator modules: {e}")
    exit(1)

def test_01_daily_etl_pipeline():
    """Тест 1: Ежедневный ETL пайплайн"""
    print("\n=== ТЕСТ 1: Создание ежедневного ETL пайплайна ===")
    
    orchestrator = MasterOrchestrator()
    
    config = {
        "schedule": "0 2 * * *",  # Каждый день в 02:00
        "description": "Ежедневный ETL пайплайн для продакшена",
        "stages": [
            {
                "stage_name": "comprehensive_monitoring",
                "type": "function_call",
                "function": "comprehensive_test",
                "endpoint": "/api/v1/metrics/comprehensive-test",
                "method": "GET",
                "parameters": {},
                "depends_on": []
            },
            {
                "stage_name": "batch_data_validation", 
                "type": "function_call",
                "function": "batch_validate_sources",
                "type": "module_call",
                "module": 1,
                "endpoint": "/api/v1/data-quality/batch-validate",
                "parameters": {
                    "sources": [
                        {
                            "source_id": "sales_csv",
                            "source_type": "file",
                            "path": "/data/raw/sales.csv"
                        }
                    ],
                    "validation_options": {
                        "check_duplicates": True,
                        "detect_anomalies": True,
                        "assess_quality": True
                },
                "depends_on": ["comprehensive_monitoring"]
            },
            {
                "stage_name": "execute_aggregation_scenarios",
                "type": "module_call",
                "module": 2,
                "endpoint": "/api/v1/aggregation/create-scenario",
                "method": "POST",
                "parameters": {
                    "name": "daily_etl_scenario",
                    "description": "Daily ETL aggregation scenario",
                    "sources": [
                        {
                            "source_id": "sales_data",
                            "source_type": "file",
                            "path": "/data/raw/sales.csv",
                            "selected_columns": []
                        }
                    ],
                    "aggregations": [
                        {
                            "type": "group_by",
                            "parameters": {
                                "group_by_columns": ["sale_date"],
                                "aggregation_functions": [
                                    {"column": "amount", "function": "sum"}
                                ]
                            }
                        }
                    ],
                    "target_requirements": {
                        "expected_volume": "medium",
                        "performance_priority": "balanced"
                    }
                },
                "depends_on": ["batch_validate_sources"]
            },
            {
                "stage_name": "analyze_all_performance",
                "type": "module_call",
                "module": 3,
                "endpoint": "/api/v1/performance/bulk-analyze",
                "method": "POST",
                "parameters": ["/data/raw/sales.csv"],
                "depends_on": ["execute_aggregation_scenarios"]
            }
        ]
    }
    
    try:
        pipeline = orchestrator.create_master_pipeline(config)
        print(f"[SUCCESS] Создан DAG: {pipeline.master_dag_id}")
        print(f"[INFO] Файл: {pipeline.dag_file_path}")
        print(f"[INFO] Этапов: {pipeline.stages_count}")
        print(f"[INFO] Расписание: {config['schedule']}")
        return pipeline.master_dag_id
    except Exception as e:
        print(f"[ERROR] Ошибка создания DAG: {str(e)}")
        return None

def test_02_weekly_optimization_pipeline():
    """Тест 2: Еженедельная оптимизация"""
    print("\n=== ТЕСТ 2: Создание еженедельного пайплайна оптимизации ===")
    
    orchestrator = MasterOrchestrator()
    
    config = {
        "pipeline_name": "weekly_optimization",
        "schedule": "0 1 * * 0",  # Воскресенье в 01:00
        "description": "Еженедельная оптимизация производительности",
        "stages": [
            {
                "stage_name": "analyze_all_performance",
                "type": "module_call",
                "module": 3,
                "endpoint": "/api/v1/performance/bulk-analyze",
                "method": "POST",
                "parameters": ["/data/raw/sales.csv"],
                "depends_on": []
            },
            {
                "stage_name": "apply_critical_optimizations",
                "type": "function_call",
                "function": "apply_optimizations",
                "parameters": {"analysis_id": "weekly_analysis"},
                "depends_on": ["analyze_all_performance"]
            },
            {
                "stage_name": "validate_optimized_data",
                "type": "function_call",
                "function": "analyze_data_quality",
                "parameters": {"source_data": "optimized_tables"},
                "depends_on": ["apply_critical_optimizations"]
            }
        ]
    }
    
    try:
        pipeline = orchestrator.create_master_pipeline(config)
        print(f"[SUCCESS] Создан DAG: {pipeline.master_dag_id}")
        print(f"[INFO] Файл: {pipeline.dag_file_path}")
        print(f"[INFO] Этапов: {pipeline.stages_count}")
        print(f"[INFO] Расписание: {config['schedule']}")
        return pipeline.master_dag_id
    except Exception as e:
        print(f"[ERROR] Ошибка создания DAG: {str(e)}")
        return None

def test_03_hourly_monitoring_pipeline():
    """Тест 3: Ежечасный мониторинг"""
    print("\n=== ТЕСТ 3: Создание ежечасного мониторинга ===")
    
    orchestrator = MasterOrchestrator()
    
    config = {
        "pipeline_name": "hourly_monitoring",
        "schedule": "0 * * * *",  # Каждый час
        "description": "Ежечасный мониторинг системы",
        "stages": [
            {
                "stage_name": "auto_detect_new_sources",
                "type": "function_call",
                "function": "auto_detect_source",
                "parameters": {"source": "/data/landing_zone"},
                "depends_on": []
            },
            {
                "stage_name": "check_data_homogeneity",
                "type": "function_call",
                "function": "check_folder_homogeneity",
                "parameters": {"folder_path": "/data/syn_csv", "auto_separate": True},
                "depends_on": ["auto_detect_new_sources"]
            },
            {
                "stage_name": "monitor_critical_sources",
                "type": "function_call",
                "function": "monitor_specific_source",
                "parameters": {
                    "db_type": "postgres",
                    "host": "localhost",
                    "port": 5432,
                    "db_name": "analytics",
                    "user": "postgres",
                    "password": "password"
                },
                "depends_on": ["check_data_homogeneity"]
            }
        ]
    }
    
    try:
        pipeline = orchestrator.create_master_pipeline(config)
        print(f"[SUCCESS] Создан DAG: {pipeline.master_dag_id}")
        print(f"[INFO] Файл: {pipeline.dag_file_path}")
        print(f"[INFO] Этапов: {pipeline.stages_count}")
        print(f"[INFO] Расписание: {config['schedule']}")
        return pipeline.master_dag_id
    except Exception as e:
        print(f"[ERROR] Ошибка создания DAG: {str(e)}")
        return None

def test_04_custom_data_processing():
    """Тест 4: Кастомная обработка данных"""
    print("\n=== ТЕСТ 4: Создание кастомного пайплайна обработки ===")
    
    orchestrator = MasterOrchestrator()
    
    config = {
        "pipeline_name": "custom_data_processing",
        "schedule": "0 6 * * 1,3,5",  # Пн, Ср, Пт в 06:00
        "description": "Кастомная обработка данных 3 раза в неделю",
        "stages": [
            {
                "stage_name": "validate_sales_data",
                "type": "function_call",
                "function": "validate_file_direct",
                "parameters": {
                    "file_path": "/data/raw/sales.csv",
                    "validation_options": {
                        "check_duplicates": True,
                        "detect_anomalies": True,
                        "assess_quality": True
                    }
                },
                "depends_on": []
            },
            {
                "stage_name": "create_sales_dataset",
                "type": "function_call",
                "function": "create_custom_dataset",
                "parameters": {
                    "dataset_name": "sales_analytics",
                    "sources": [
                        {
                            "source_id": "sales_csv",
                            "source_type": "file",
                            "path": "/data/raw/sales.csv",
                            "selected_columns": ["sale_date", "customer_id", "amount"]
                        }
                    ],
                    "join_strategy": "individual",
                    "output_format": "parquet",
                    "include_metadata": True
                },
                "depends_on": ["validate_sales_data"]
            },
            {
                "stage_name": "optimize_sales_performance",
                "type": "function_call",
                "function": "analyze_performance",
                "parameters": {
                    "source": "/data/aggregated/sales_analytics.parquet"
                },
                "depends_on": ["create_sales_dataset"]
            },
            {
                "stage_name": "generate_sales_insights",
                "type": "function_call",
                "function": "execute_scenario",
                "parameters": {
                    "scenario_id": "sales_insights_weekly"
                },
                "depends_on": ["optimize_sales_performance"]
            }
        ]
    }
    
    try:
        pipeline = orchestrator.create_master_pipeline(config)
        print(f"[SUCCESS] Создан DAG: {pipeline.master_dag_id}")
        print(f"[INFO] Файл: {pipeline.dag_file_path}")
        print(f"[INFO] Этапов: {pipeline.stages_count}")
        print(f"[INFO] Расписание: {config['schedule']}")
        return pipeline.master_dag_id
    except Exception as e:
        print(f"[ERROR] Ошибка создания DAG: {str(e)}")
        return None

def main():
    """Запуск всех тестов создания DAG'ов"""
    print("=" * 70)
    print("СОЗДАНИЕ 4 ПРАКТИЧЕСКИХ DAG'ОВ ДЛЯ AIRFLOW")
    print("=" * 70)
    
    created_dags = []
    
    # Запускаем все тесты
    dag1 = test_01_daily_etl_pipeline()
    if dag1:
        created_dags.append(dag1)
    
    dag2 = test_02_weekly_optimization_pipeline()
    if dag2:
        created_dags.append(dag2)
    
    dag3 = test_03_hourly_monitoring_pipeline()
    if dag3:
        created_dags.append(dag3)
    
    dag4 = test_04_custom_data_processing()
    if dag4:
        created_dags.append(dag4)
    
    # Итоги
    print("\n" + "=" * 70)
    print("ИТОГИ СОЗДАНИЯ DAG'ОВ")
    print("=" * 70)
    print(f"Успешно создано DAG'ов: {len(created_dags)}/4")
    
    if created_dags:
        print("\nСозданные DAG'и:")
        for i, dag_id in enumerate(created_dags, 1):
            print(f"  {i}. {dag_id}")
        
        print(f"\nФайлы DAG'ов находятся в:")
        print("  airflow/dags/orchestrator/generated/")
        
        print(f"\nДля просмотра в Airflow UI:")
        print("  1. Убедитесь что Airflow запущен")
        print("  2. Откройте http://localhost:8080")
        print("  3. Найдите DAG'и в списке")
        print("  4. Проверьте расписания и зависимости")
    else:
        print("\n[WARNING] Ни один DAG не был создан!")
    
    return len(created_dags)

if __name__ == "__main__":
    success_count = main()
    exit(0 if success_count > 0 else 1)
