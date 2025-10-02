#!/usr/bin/env python3
"""
Тест создания DAG'ов с исправленными параметрами API
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'airflow', 'dags'))

try:
    from orchestrator.master_orchestrator import MasterOrchestrator
except ImportError as e:
    print(f"Error: Could not import orchestrator modules: {e}")
    exit(1)

def test_01_daily_etl_pipeline():
    """Тест 1: Ежедневный ETL пайплайн с исправленными параметрами"""
    print("\n=== ТЕСТ 1: Создание ежедневного ETL пайплайна ===")
    
    orchestrator = MasterOrchestrator()
    
    config = {
        "pipeline_name": "daily_etl_production",
        "schedule": "0 2 * * *",  # Каждый день в 02:00
        "description": "Ежедневный ETL пайплайн для продакшена",
        "stages": [
            {
                "stage_name": "auto_detect_sources",
                "type": "function_call",
                "function": "auto_detect_source",
                "endpoint": "/api/v1/metrics/auto-detect",
                "method": "GET",
                "parameters": {"source": "/data/raw"},
                "depends_on": []
            },
            {
                "stage_name": "batch_validate_sources",
                "type": "module_call",
                "module": 1,
                "endpoint": "/api/v1/data-quality/batch-validate",
                "method": "POST",
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
                    }
                },
                "depends_on": ["auto_detect_sources"]
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
    """Тест 2: Еженедельная оптимизация с исправленными параметрами"""
    print("\n=== ТЕСТ 2: Создание еженедельной оптимизации ===")
    
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
                "endpoint": "/api/v1/performance/optimize/weekly_analysis",
                "method": "POST",
                "parameters": {"analysis_id": "weekly_analysis"},
                "depends_on": ["analyze_all_performance"]
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
    """Тест 3: Ежечасный мониторинг с исправленными параметрами"""
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
                "endpoint": "/api/v1/metrics/auto-detect",
                "method": "GET",
                "parameters": {"source": "/data/landing_zone"},
                "depends_on": []
            },
            {
                "stage_name": "check_data_homogeneity",
                "type": "function_call",
                "function": "check_folder_homogeneity",
                "endpoint": "/api/v1/data-quality/check-homogeneity",
                "method": "POST",
                "parameters": {"folder_path": "/data/syn_csv", "auto_separate": True},
                "depends_on": ["auto_detect_new_sources"]
            },
            {
                "stage_name": "monitor_critical_sources",
                "type": "function_call",
                "function": "monitor_specific_source",
                "endpoint": "/api/v1/metrics/collect",
                "method": "POST",
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

if __name__ == "__main__":
    print("ТЕСТИРОВАНИЕ СОЗДАНИЯ DAG'ОВ С ИСПРАВЛЕННЫМИ ПАРАМЕТРАМИ")
    print("=" * 70)
    
    results = []
    
    # Запускаем все тесты
    results.append(test_01_daily_etl_pipeline())
    results.append(test_02_weekly_optimization_pipeline())
    results.append(test_03_hourly_monitoring_pipeline())
    
    # Подводим итоги
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    
    successful = [r for r in results if r is not None]
    failed = [r for r in results if r is None]
    
    print(f"Успешно создано DAG'ов: {len(successful)}")
    print(f"Ошибок при создании: {len(failed)}")
    
    if successful:
        print("\nСОЗДАННЫЕ DAG'Ы:")
        for dag_id in successful:
            print(f"  - {dag_id}")
    
    if failed:
        print(f"\nИз {len(results)} тестов {len(failed)} завершились с ошибками")
    else:
        print("\nВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    
    print("\nНовые DAG'ы с суффиксом '_20250928_004831' должны работать без 422 ошибок")
