import polars as pl
import os

# Пути внутри контейнера
DATA_DIR = "/data"

def ingest_file(source_config: dict, **kwargs):
    """Reads data from a file source (CSV, JSON) and pushes it to XCom."""
    source_type = source_config.get("type")
    path = source_config.get("options", {}).get("path")
    full_path = os.path.join(DATA_DIR, path)

    print(f"Ingesting from {full_path}...")

    if source_type == "csv":
        df = pl.read_csv(full_path)
    elif source_type == "json":
        df = pl.read_json(full_path)
    else:
        raise NotImplementedError(f"Ingestion from '{source_type}' is not supported.")

    # Airflow не может передавать большие данные через XCom напрямую.
    # Для прототипа мы передадим данные как список словарей в формате JSON.
    # В реальной системе здесь бы использовался S3, HDFS или другая промежуточная система хранения.
    data_json = df.to_dicts()
    print(f"Ingested {len(data_json)} rows.")
    kwargs['ti'].xcom_push(key='extracted_data', value=data_json)

def load_data(target_config: dict, **kwargs):
    """Pulls data from XCom and loads it into a target system (Postgres, ClickHouse)."""
    ti = kwargs['ti']
    data_json = ti.xcom_pull(key='extracted_data', task_ids='ingest')
    if not data_json:
        print("No data to load. Skipping.")
        return

    df = pl.from_dicts(data_json)
    target_system = target_config.get("system")
    table_name = target_config.get("object")

    print(f"Loading {len(df)} rows to {target_system}.{table_name}...")

    # TODO: Реализовать логику загрузки в PG и CH, используя clickhouse-connect и psycopg2
    # Сейчас это просто заглушка
    print("--- LOAD LOGIC IS A STUB ---")
    print(df.head())
    print("--- END STUB ---")

    print("Load complete.")

def validate_data(**kwargs):
    """(STUB) Validates data."""
    print("Validation logic is a stub.")

def transform_data(**kwargs):
    """(STUB) Transforms data."""
    print("Transform logic is a stub.")
