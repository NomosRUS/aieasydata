from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime
from etl.operators import ingest_file, validate_data, transform_data, load_data

default_args = {"owner":"ai", "retries":0}

with DAG(
    dag_id="gen_part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000",
    start_date=datetime(2025, 9, 1),
    schedule="0 * * * *",
    catchup=False,
    tags=["generated","aieasydata"],
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    t_ingest = PythonOperator(
        task_id="ingest", 
        python_callable=ingest_file, 
        op_kwargs={"source_config": {"options": {"path": "syn_csv/part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000.csv"}, "type": "csv"} }
    )
    t_validate = PythonOperator(task_id="validate", python_callable=validate_data)
    t_transform = PythonOperator(task_id="transform", python_callable=transform_data)
    t_load = PythonOperator(
        task_id="load", 
        python_callable=load_data,
        op_kwargs={"target_config": {"object": "gen_part-00000-37dced01-2ad2-48c8-a56d-54b4d8760599-c000", "system": "clickhouse"} }
    )

    start >> t_ingest >> t_validate >> t_transform >> t_load >> end