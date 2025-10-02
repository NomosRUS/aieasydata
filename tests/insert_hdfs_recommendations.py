import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

# Загружаем переменные окружения из .env файла в корне проекта
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# DSN для подключения к PostgreSQL
DATABASE_URL = os.getenv("POSTGRES_DSN")
if not DATABASE_URL:
    raise ValueError("POSTGRES_DSN is not set in .env file")

# Заменяем имя хоста для локального подключения
DATABASE_URL = DATABASE_URL.replace("@postgres:", "@localhost:")

# Разбираем DSN на компоненты для надежного подключения
result = urlparse(DATABASE_URL)
db_params = {
    'user': result.username,
    'password': result.password,
    'host': result.hostname,
    'port': result.port,
    'dbname': result.path[1:]
}

# Рекомендации для HDFS (большие объемы сырых данных)
recommendations = [
    ('/data/raw/sales_hdfs.csv', 'partition', '{"partition_by": "year_month", "format": "parquet"}'),
    ('/data/raw/sales_hdfs.csv', 'compression', '{"type": "snappy", "block_size": "128MB"}'),
]

# SQL-запрос для вставки/обновления рекомендаций
INSERT_QUERY = """
INSERT INTO optimization_recommendations (table_name, recommendation_type, recommendation_details)
VALUES (%s, %s, %s)
ON CONFLICT (table_name, recommendation_type) DO UPDATE SET
    recommendation_details = EXCLUDED.recommendation_details;
"""

try:
    print(f"Connecting to database '{db_params['dbname']}' on '{db_params['host']}:{db_params['port']}'...")
    with psycopg2.connect(**db_params) as conn:
        with conn.cursor() as cur:
            print("Inserting/updating HDFS recommendations...")
            
            for table_name, rec_type, rec_details in recommendations:
                print(f"  - {table_name} -> {rec_type}: {rec_details}")
                cur.execute(INSERT_QUERY, (table_name, rec_type, rec_details))
            
            conn.commit()
            print(f"[SUCCESS] {len(recommendations)} HDFS optimization recommendations inserted.")

except Exception as e:
    print(f"[ERROR] Database operation failed: {e}")
    exit(1)
