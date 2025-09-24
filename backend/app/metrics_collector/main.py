import psycopg2
import clickhouse_connect
from .schemas import ConnectionInfo

def collect_metrics(conn_info: ConnectionInfo) -> dict:
    """Главная функция-диспетчер для сбора метрик."""
    if conn_info.db_type == 'clickhouse':
        return _collect_clickhouse_metrics(conn_info)
    elif conn_info.db_type == 'postgres':
        return _collect_postgres_metrics(conn_info)
    else:
        raise ValueError(f"Unsupported DB type: {conn_info.db_type}")

def _collect_clickhouse_metrics(conn_info: ConnectionInfo) -> dict:
    """Собирает метрики из ClickHouse."""
    metrics = {}
    try:
        client = clickhouse_connect.get_client(
            host=conn_info.host,
            port=conn_info.port,
            user=conn_info.user,
            password=conn_info.password
        )

        # Базовые метрики: количество строк и размер
        size_query = f"""
        SELECT
            count() AS row_count,
            sum(bytes_on_disk) AS size_in_bytes
        FROM system.parts
        WHERE database = '{conn_info.db_name}' AND table = '{conn_info.table_name}' AND active
        """
        result = client.query(size_query)
        metrics['row_count'] = result.result_rows[0][0] if result.result_rows else 0
        metrics['size_in_bytes'] = result.result_rows[0][1] if result.result_rows else 0

        # Метрики производительности
        perf_query = f"""
        SELECT
            avg(query_duration_ms) AS avg_query_duration_ms,
            quantile(0.95)(query_duration_ms) AS p95_query_duration_ms,
            count() AS total_queries
        FROM system.query_log
        WHERE (query LIKE '%%{conn_info.table_name}%%') AND (type = 'QueryFinish')
        """
        result = client.query(perf_query)
        metrics['avg_query_duration_ms'] = result.result_rows[0][0] if result.result_rows else 0
        metrics['p95_query_duration_ms'] = result.result_rows[0][1] if result.result_rows else 0
        metrics['total_queries'] = result.result_rows[0][2] if result.result_rows else 0

    except Exception as e:
        # В случае ошибки возвращаем базовые значения, чтобы не ломать API
        print(f"Error collecting ClickHouse metrics: {e}")
        return {"row_count": 0, "size_in_bytes": 0}

    return metrics

def _collect_postgres_metrics(conn_info: ConnectionInfo) -> dict:
    """Собирает метрики из PostgreSQL."""
    metrics = {}
    dsn = f"dbname='{conn_info.db_name}' user='{conn_info.user}' password='{conn_info.password}' host='{conn_info.host}' port='{conn_info.port}'"
    try:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cursor:
                # В PostgreSQL нет простого способа получить schema из DSN, предполагаем 'public' или передаем явно
                schema_name = 'analytics' # Хардкод для нашего случая

                # Размер таблицы
                cursor.execute(f"SELECT pg_total_relation_size('{schema_name}.{conn_info.table_name}')")
                size_result = cursor.fetchone()
                metrics['size_in_bytes'] = size_result[0] if size_result else 0

                # Приблизительное количество строк
                cursor.execute(f"SELECT reltuples::bigint FROM pg_class WHERE relname = '{conn_info.table_name}'")
                rows_result = cursor.fetchone()
                metrics['row_count'] = rows_result[0] if rows_result else 0

                # Метрики производительности (требуют pg_stat_statements)
                try:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
                    cursor.execute(f"""
                    SELECT mean_exec_time, calls
                    FROM pg_stat_statements
                    WHERE query LIKE '%%{conn_info.table_name}%%'
                    LIMIT 1
                    """)
                    perf_result = cursor.fetchone()
                    if perf_result:
                        metrics['avg_query_duration_ms'] = perf_result[0]
                        metrics['total_queries'] = perf_result[1]
                except psycopg2.Error as pg_err:
                    print(f"Could not query pg_stat_statements: {pg_err}")
                    conn.rollback() # Откатываем CREATE EXTENSION если что-то пошло не так

    except Exception as e:
        print(f"Error collecting PostgreSQL metrics: {e}")
        return {"row_count": 0, "size_in_bytes": 0}

    return metrics
