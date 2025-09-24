import uuid
import json
from datetime import date, datetime
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..database import DataProfile
from ..shared.schemas import AggregationScenario, OptimizationRecommendation, WarehouseDesign
from .. import agent
from . import schemas


def run_design_process(request: schemas.DesignRequest, db: Session) -> WarehouseDesign:
    """
    Главная функция-оркестратор процесса проектирования.
    """
    # 1. Создаем запись о процессе проектирования в БД
    design_id = str(uuid.uuid4())
    db_design = WarehouseDesign(
        design_id=design_id,
        status="collecting_data",
        source_profile_id=request.source_profile_id,
        request_payload=request.model_dump()
    )
    db.add(db_design)
    db.commit()
    db.refresh(db_design)

    # 2. Собираем все входные данные
    collected_data = collect_input_data(request.source_profile_id, db)

    decision_context = {
        **collected_data,
        "request": request.model_dump()
    }

    db_design.results = {"context": decision_context}
    db_design.status = "data_collected"
    db.commit()
    db.refresh(db_design)

    heuristic_decision = select_database(decision_context)
    llm_review = review_with_llm(decision_context, heuristic_decision)

    db_design.results = {
        "context": decision_context,
        "heuristic_decision": heuristic_decision,
        "llm_analysis": llm_review
    }
    db_design.status = "awaiting_user_confirmation"
    db.commit()
    db.refresh(db_design)

    return db_design


def collect_input_data(source_profile_id: int, db: Session) -> Dict[str, Any]:
    """
    Собирает все необходимые данные из различных таблиц БД.
    """
    # 1. Получаем основной профиль данных
    profile = db.query(DataProfile).filter(DataProfile.id == source_profile_id).first()
    if not profile:
        raise Exception(f"DataProfile with id {source_profile_id} not found.")

    # 2. Получаем сценарии агрегации (от Задачи 2)
    agg_scenarios = db.query(AggregationScenario).filter(AggregationScenario.source_id == source_profile_id).all()

    # 3. Получаем рекомендации по оптимизации (от Задачи 3)
    # В ТЗ указано, что рекомендации связаны с таблицей, поэтому ищем по имени источника
    opt_recommendations = db.query(OptimizationRecommendation).filter(OptimizationRecommendation.table_name == profile.source_path).all()

    # 4. Собираем все в единый контекст
    context = {
        "data_profile": _serialize_sqlalchemy_instance(profile),
        "aggregation_scenarios": [_serialize_sqlalchemy_instance(sc) for sc in agg_scenarios],
        "optimization_recommendations": [_serialize_sqlalchemy_instance(rec) for rec in opt_recommendations],
    }

    return context


def _serialize_sqlalchemy_instance(instance) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for column in instance.__table__.columns:  # type: ignore[attr-defined]
        value = getattr(instance, column.name)
        data[column.name] = _serialize_value(value)
    return data


def _serialize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def select_database(context: Dict[str, Any]) -> Dict[str, Any]:
    profile = context.get("data_profile", {}) or {}
    aggregations = context.get("aggregation_scenarios", []) or []
    request = context.get("request", {}) or {}
    constraints = request.get("constraints", {}) or {}
    analytics = request.get("analytics_requirements", {}) or {}
    business_text = (request.get("business_requirements") or "").lower()

    scores = {"clickhouse": 0, "postgres": 0, "hdfs": 0}
    reasons = []

    total_rows = profile.get("total_row_count") or 0
    if total_rows and total_rows >= 100_000_000:
        scores["clickhouse"] += 2
        reasons.append("Объём данных превышает 100 млн строк — ClickHouse справится лучше всего.")
    elif total_rows and total_rows >= 10_000_000:
        scores["clickhouse"] += 1
        reasons.append("Объём данных десятки миллионов строк — ClickHouse предпочтителен.")

    if aggregations:
        complex_ops = [agg for agg in aggregations if any(keyword in (agg.get("aggregation_type") or "") for keyword in ["JOIN", "WINDOW", "GROUP BY"])]
        if complex_ops:
            scores["clickhouse"] += 2
            reasons.append("Есть сложные агрегации и joins — ClickHouse оптимален для аналитических нагрузок.")
        frequent = analytics.get("queries_per_hour") or analytics.get("frequency_per_hour")
        if frequent and frequent >= 100:
            scores["clickhouse"] += 1
            reasons.append("Высокая частота аналитических запросов — ClickHouse обладает лучшей пропускной способностью.")

    quality_score = profile.get("quality_score")
    if quality_score is not None and quality_score < 0.7:
        scores["hdfs"] += 2
        reasons.append("Низкое качество данных (quality_score < 0.7) — лучше сохранить в HDFS как сырые данные.")

    if "oltp" in business_text or "transaction" in business_text:
        scores["postgres"] += 2
        reasons.append("Бизнес-требования упоминают OLTP/транзакционную нагрузку — PostgreSQL подходит лучше всего.")

    latency = constraints.get("latency_ms") or analytics.get("latency_ms")
    if latency is not None and latency <= 200:
        scores["postgres"] += 1
        reasons.append("Требуется низкая задержка ответа — PostgreSQL обеспечивает быстрые транзакции.")

    max_storage = constraints.get("max_storage_gb")
    if max_storage is not None and max_storage < 50 and total_rows:
        scores["postgres"] += 1
        reasons.append("Ограничение по хранилищу < 50 ГБ — PostgreSQL экономичнее по месту.")

    if not any(scores.values()):
        scores["postgres"] += 1
        reasons.append("Не найдено явных преимуществ — выбран PostgreSQL как универсальное решение.")

    candidate = max(scores.items(), key=lambda item: item[1])[0]

    return {
        "candidate": candidate,
        "scores": scores,
        "reasons": reasons,
        "evaluated_facts": {
            "total_row_count": total_rows,
            "quality_score": quality_score,
            "aggregation_types": [agg.get("aggregation_type") for agg in aggregations],
            "analytics_requirements": analytics,
            "constraints": constraints,
        },
    }


def review_with_llm(context: Dict[str, Any], heuristic: Dict[str, Any]) -> Dict[str, Any]:
    prompt_payload = {
        "context": context,
        "heuristic": heuristic,
    }

    prompt = (
        "Ты эксперт по архитектуре хранилищ. Тебе передают контекст (профиль данных, требования) и результат "
        "эвристического выбора СУБД. Проверь вывод эвристики. Ответ верни строго в JSON с ключами: "
        "final_choice (одно из clickhouse/postgres/hdfs), summary (короткое обоснование), "
        "critical_arguments (список ключевых факторов), confidence (низкая/средняя/высокая), "
        "notes (доп. рекомендации)."
        "\nЕсли не согласен с эвристикой, предложи альтернативу и объясни почему."
        "\nКонтекст:"
    )

    prompt += "\n" + json.dumps(prompt_payload, ensure_ascii=False, indent=2)

    try:
        llm_response = agent.get_llm_response(prompt)
        content = llm_response.get("content", "")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {
                "final_choice": heuristic.get("candidate"),
                "summary": content,
                "critical_arguments": heuristic.get("reasons", []),
                "confidence": "средняя",
                "notes": "Ответ LLM не в формате JSON; использовано содержание как есть."
            }
        parsed["debug_log"] = llm_response.get("debug_log")
        return parsed
    except Exception as exc:
        return {
            "final_choice": heuristic.get("candidate"),
            "summary": f"Не удалось получить ответ от LLM: {exc}",
            "critical_arguments": heuristic.get("reasons", []),
            "confidence": "средняя",
            "notes": "Использовано эвристическое решение по умолчанию.",
        }


def generate_ddl(context: Dict[str, Any], selected_db: str) -> str:
    """
    Генерирует DDL-скрипт с учетом рекомендаций по оптимизации.
    
    Args:
        context: Контекст с данными профиля, агрегациями и рекомендациями оптимизации
        selected_db: Выбранная СУБД ('clickhouse', 'postgres', 'hdfs')
    
    Returns:
        str: Готовый DDL-скрипт
    """
    # Получаем данные профиля
    data_profile = context.get("data_profile", {})
    optimization_recommendations = context.get("optimization_recommendations", [])
    
    # Извлекаем схему таблицы из профиля
    columns = data_profile.get("columns", [])
    if not columns:
        raise ValueError("Отсутствует схема данных в профиле")
    
    # Определяем имя таблицы из source_path
    source_path = data_profile.get("source_path", "unknown_table")
    table_name = _extract_table_name(source_path)
    
    # Парсим рекомендации оптимизации
    optimizations = _parse_optimization_recommendations(optimization_recommendations, selected_db)
    
    # Подготавливаем параметры для шаблона
    template_params = {
        "table": {
            "db": "analytics",  # Дефолтная схема/база
            "table": table_name
        },
        "columns": _convert_columns_for_template(columns, selected_db),
        **optimizations
    }
    
    # Генерируем DDL через существующую функцию agent
    ddl_result = agent.generate_ddl_with_explanation({
        "target_system": selected_db,
        **template_params
    })
    
    return ddl_result.get("ddl", "")


def _extract_table_name(source_path: str) -> str:
    """
    Извлекает имя таблицы из пути к источнику данных.
    """
    import os
    import re
    
    # Получаем базовое имя файла без расширения
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    
    # Приводим к безопасному SQL-идентификатору
    # Заменяем небуквенно-цифровые символы на подчеркивания
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', base_name)
    
    # Убираем множественные подчеркивания
    safe_name = re.sub(r'_+', '_', safe_name)
    
    # Убираем подчеркивания в начале и конце
    safe_name = safe_name.strip('_')
    
    # Если имя пустое или начинается с цифры, добавляем префикс
    if not safe_name or safe_name[0].isdigit():
        safe_name = f"table_{safe_name}"
    
    return safe_name.lower()



def _convert_columns_for_template(columns: list, selected_db: str) -> list:
    converted = []

    for col in columns:
        # accept both {'column_name': ...} and {'name': ...}
        raw_name = col.get("column_name") or col.get("name") or "unknown_column"
        raw_type = col.get("column_type") or col.get("type") or "String"

        safe_name = _extract_table_name(raw_name)

        if selected_db == "clickhouse":
            mapped_type = _map_type_to_clickhouse(raw_type)
        elif selected_db == "postgres":
            mapped_type = _map_type_to_postgres(raw_type)
        else:
            mapped_type = "STRING"

        converted.append({"name": safe_name, "type": mapped_type})

    return converted


def _map_type_to_clickhouse(original_type: str) -> str:
    """Маппинг типов данных для ClickHouse."""
    type_mapping = {
        "String": "String",
        "INTEGER": "Int64",
        "DECIMAL": "Decimal64(2)", 
        "TIMESTAMP": "DateTime",
        "Int64": "Int64", 
        "Float64": "Float64",
        "Boolean": "UInt8",
        "Date": "Date",
        "Datetime": "DateTime",
        "object": "String",
        "int64": "Int64",
        "float64": "Float64",
        "bool": "UInt8"
    }
    return type_mapping.get(original_type, "String")


def _map_type_to_postgres(original_type: str) -> str:
    """Маппинг типов данных для PostgreSQL."""
    type_mapping = {
        "String": "TEXT",
        "Int64": "BIGINT",
        "Float64": "DOUBLE PRECISION", 
        "Boolean": "BOOLEAN",
        "Date": "DATE",
        "Datetime": "TIMESTAMP",
        "object": "TEXT",
        "int64": "BIGINT",
        "float64": "DOUBLE PRECISION",
        "bool": "BOOLEAN"
    }
    return type_mapping.get(original_type, "TEXT")


def _parse_optimization_recommendations(recommendations: list, selected_db: str) -> Dict[str, Any]:
    """
    Парсит рекомендации оптимизации и преобразует их в параметры для шаблонов.
    """
    optimizations = {}
    
    for rec in recommendations:
        rec_type = rec.get("recommendation_type", "")
        rec_details = rec.get("recommendation_details", {})
        
        if selected_db == "clickhouse":
            if rec_type == "partition":
                # Для ClickHouse: PARTITION BY
                partition_expr = rec_details.get("partition_by")
                if partition_expr:
                    optimizations["partition_by"] = partition_expr
            
            elif rec_type == "order_by":
                # Для ClickHouse: ORDER BY
                order_columns = rec_details.get("columns", [])
                if order_columns:
                    optimizations["order_by"] = order_columns
        
        elif selected_db == "postgres":
            if rec_type == "index":
                # Для PostgreSQL: CREATE INDEX
                index_columns = rec_details.get("columns", [])
                if index_columns:
                    optimizations["indexes"] = index_columns
            
            elif rec_type == "partition":
                # Для PostgreSQL: партиционирование (если поддерживается)
                partition_expr = rec_details.get("partition_by")
                if partition_expr:
                    optimizations["partition_by"] = partition_expr
    
    return optimizations


def execute_ddl_in_database(ddl_script: str, selected_db: str) -> Dict[str, Any]:
    """
    Выполняет DDL-скрипт в целевой СУБД.
    
    Args:
        ddl_script: DDL-скрипт для выполнения
        selected_db: Целевая СУБД ('clickhouse', 'postgres', 'hdfs')
    
    Returns:
        Dict с результатом выполнения
    """
    import os
    import requests
    import psycopg2
    from datetime import datetime
    
    result = {
        "executed_at": datetime.utcnow().isoformat(),
        "database": selected_db,
        "success": False,
        "error": None,
        "details": {}
    }
    
    try:
        if selected_db == "postgres":
            # Подключение к PostgreSQL
            postgres_dsn = os.environ.get("POSTGRES_DSN")
            if not postgres_dsn:
                raise ValueError("POSTGRES_DSN не найден в переменных окружения")
            
            conn = psycopg2.connect(postgres_dsn)
            cursor = conn.cursor()
            
            # Выполняем DDL (может содержать несколько команд)
            cursor.execute(ddl_script)
            conn.commit()
            
            result["success"] = True
            result["details"]["rows_affected"] = cursor.rowcount
            
            cursor.close()
            conn.close()
            
        elif selected_db == "clickhouse":
            # Подключение к ClickHouse через HTTP API
            clickhouse_url = os.environ.get("CLICKHOUSE_HTTP", "http://clickhouse:8123")
            
            # Разделяем DDL на отдельные команды (ClickHouse не поддерживает multi-statements)
            statements = [stmt.strip() for stmt in ddl_script.split(';') if stmt.strip()]
            responses = []
            
            for statement in statements:
                if not statement:
                    continue
                    
                response = requests.post(
                    f"{clickhouse_url}/",
                    data=statement,
                    headers={
                        "Content-Type": "text/plain",
                        "X-ClickHouse-User": os.environ.get("CLICKHOUSE_USER", "default"),
                        "X-ClickHouse-Key": os.environ.get("CLICKHOUSE_PASSWORD", "password")
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise Exception(f"ClickHouse error: {response.status_code} - {response.text}")
                
                responses.append(response.text.strip())
            
            result["success"] = True
            result["details"]["responses"] = responses
                
        elif selected_db == "hdfs":
            # Для HDFS создаем директорию (DDL в данном случае - это создание структуры папок)
            hdfs_web = os.environ.get("HDFS_WEB", "http://hdfs-namenode:9870")
            
            # Извлекаем имя таблицы из DDL для создания директории
            import re
            table_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+\.)?(\w+)', ddl_script, re.IGNORECASE)
            if table_match:
                table_name = table_match.group(2)
                
                # Создаем директорию в HDFS через WebHDFS API
                hdfs_path = f"/warehouse/{table_name}"
                response = requests.put(
                    f"{hdfs_web}/webhdfs/v1{hdfs_path}?op=MKDIRS&user.name=root"
                )
                
                if response.status_code in [200, 201]:
                    result["success"] = True
                    result["details"]["hdfs_path"] = hdfs_path
                else:
                    raise Exception(f"HDFS error: {response.status_code} - {response.text}")
            else:
                raise ValueError("Не удалось извлечь имя таблицы из DDL")
        
        else:
            raise ValueError(f"Неподдерживаемая СУБД: {selected_db}")
            
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    
    return result


def generate_etl_pipeline(design_id: str, context: Dict[str, Any], selected_db: str) -> Dict[str, Any]:
    """
    Генерирует ETL-пайплайн для загрузки данных в созданное хранилище.
    
    Args:
        design_id: ID дизайна хранилища
        context: Контекст с данными профиля и настройками
        selected_db: Целевая СУБД
    
    Returns:
        Dict с информацией о созданном пайплайне
    """
    import os
    from datetime import datetime
    from ..dag_compiler import compile_dag
    
    # Извлекаем данные из контекста
    data_profile = context.get("data_profile", {})
    source_path = data_profile.get("source_path", "")
    if not source_path.startswith("hdfs://"):
        source_path = f"hdfs://namenode:9000{source_path if source_path.startswith('/') else '/' + source_path}"
    
    # Определяем имя таблицы
    table_name = _extract_table_name(source_path)
    
    # Подготавливаем конфигурацию источника
    source_config = {
        "type": "file",  # Пока поддерживаем только файлы
        "path": source_path,
        "format": _detect_file_format(source_path),
        "columns": data_profile.get("columns", [])
    }
    
    # Подготавливаем конфигурацию целевой системы
    target_config = {
        "type": selected_db,
        "table_name": table_name,
        "database": "analytics",  # Дефолтная база
        "connection_params": _get_connection_params(selected_db)
    }
    
    # Добавляем оптимизации в конфигурацию
    optimizations = context.get("optimization_recommendations", [])
    if optimizations:
        target_config["optimizations"] = _parse_optimization_recommendations(optimizations, selected_db)
    
    # Подготавливаем DSL для генерации DAG
    dag_dsl = {
        "name": f"warehouse_etl_{design_id}_{table_name}",
        "schedule": "@once",  # Запуск по требованию
        "source": source_config,
        "target": target_config,
        "design_id": design_id,
        "created_at": datetime.utcnow().isoformat()
    }
    
    try:
        # Генерируем DAG файл
        dag_file_path = compile_dag(dag_dsl)
        
        return {
            "success": True,
            "dag_id": dag_dsl["name"],
            "dag_file_path": dag_file_path,
            "source_config": source_config,
            "target_config": target_config,
            "created_at": dag_dsl["created_at"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "dag_id": dag_dsl["name"]
        }


def _detect_file_format(file_path: str) -> str:
    """Определяет формат файла по расширению."""
    import os
    
    ext = os.path.splitext(file_path)[1].lower()
    format_mapping = {
        ".csv": "csv",
        ".json": "json",
        ".xlsx": "excel",
        ".xls": "excel",
        ".parquet": "parquet",
        ".txt": "text"
    }
    return format_mapping.get(ext, "csv")


def _get_connection_params(selected_db: str) -> Dict[str, str]:
    """Возвращает параметры подключения для целевой СУБД."""
    import os
    
    if selected_db == "postgres":
        return {
            "dsn": os.environ.get("POSTGRES_DSN", "postgresql://user:pass@postgres:5432/aieasydata")
        }
    elif selected_db == "clickhouse":
        return {
            "http_url": os.environ.get("CLICKHOUSE_HTTP", "http://clickhouse:8123"),
            "host": "clickhouse",
            "port": "9000"
        }
    elif selected_db == "hdfs":
        return {
            "namenode_url": os.environ.get("HDFS_WEB", "http://hdfs-namenode:9870"),
            "base_path": "/warehouse"
        }
    else:
        return {}


