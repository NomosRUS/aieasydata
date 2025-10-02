import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

# ╨Ч╨░╨│╤А╤Г╨╢╨░╨╡╨╝ ╨┐╨╡╤А╨╡╨╝╨╡╨╜╨╜╤Л╨╡ ╨╛╨║╤А╤Г╨╢╨╡╨╜╨╕╤П ╨╕╨╖ .env ╤Д╨░╨╣╨╗╨░ ╨▓ ╨║╨╛╤А╨╜╨╡ ╨┐╤А╨╛╨╡╨║╤В╨░
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# DSN ╨┤╨╗╤П ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╨╕╤П ╨║ PostgreSQL
DATABASE_URL = os.getenv("POSTGRES_DSN")
if not DATABASE_URL:
    raise ValueError("POSTGRES_DSN is not set in .env file")

# ╨Ч╨░╨╝╨╡╨╜╤П╨╡╨╝ ╨╕╨╝╤П ╤Е╨╛╤Б╤В╨░ ╨┤╨╗╤П ╨╗╨╛╨║╨░╨╗╤М╨╜╨╛╨│╨╛ ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╨╕╤П
DATABASE_URL = DATABASE_URL.replace("@postgres:", "@localhost:")

# ╨а╨░╨╖╨▒╨╕╤А╨░╨╡╨╝ DSN ╨╜╨░ ╨║╨╛╨╝╨┐╨╛╨╜╨╡╨╜╤В╤Л ╨┤╨╗╤П ╨╜╨░╨┤╨╡╨╢╨╜╨╛╨│╨╛ ╨┐╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╨╕╤П
result = urlparse(DATABASE_URL)
db_params = {
    'user': result.username,
    'password': result.password,
    'host': result.hostname,
    'port': result.port,
    'dbname': result.path[1:]
}

# ╨Ф╨░╨╜╨╜╤Л╨╡ ╨┤╨╗╤П ╨▓╤Б╤В╨░╨▓╨║╨╕
TABLE_NAME = "/data/raw/sales.csv"
RECOMMENDATION_TYPE = "partition"
RECOMMENDATION_DETAILS = '{"partition_by": "toYYYYMM(dt)"}'

# SQL-╨╖╨░╨┐╤А╨╛╤Б
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
            print("Inserting/updating test recommendation...")
            cur.execute(INSERT_QUERY, (TABLE_NAME, RECOMMENDATION_TYPE, RECOMMENDATION_DETAILS))
            conn.commit()
            print(f"[SUCCESS] Test recommendation for table '{TABLE_NAME}' is in the database.")

except Exception as e:
    print(f"[ERROR] Database operation failed: {e}")
