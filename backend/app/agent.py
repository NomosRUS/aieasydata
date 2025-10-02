import os, json
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

TPL_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TPL_DIR), autoescape=False, trim_blocks=True, lstrip_blocks=True, auto_reload=True)

def _render(tpl_path: str, ctx: dict) -> str:
    tpl = env.get_template(tpl_path)
    return tpl.render(**ctx)

def _client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    
    base_url = os.environ.get("OPENAI_BASE_URL") # Will be None if not set
    
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    else:
        # If OPENAI_BASE_URL is not set, initialize without it to use the default OpenAI URL
        return OpenAI(api_key=api_key)

def get_llm_response(prompt: str) -> dict:
    """
    Centralized function to interact with the OpenAI LLM.
    Returns a dictionary with 'content' and 'debug_log'.
    """
    client = _client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    
    debug_log = {
        "base_url": str(client.base_url),
        "model": model,
        "prompt": prompt,
        "response": None,
        "error": None
    }

    try:
        chat = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
        response_content = chat.choices[0].message.content
        debug_log["response"] = response_content
        return {"content": response_content, "debug_log": debug_log}
    except Exception as e:
        error_message = f"Не удалось получить ответ от ИИ: {e}"
        debug_log["error"] = str(e)
        return {"content": error_message, "debug_log": debug_log}

def analyze_data_profile(profile: dict) -> dict:
    """
    Analyzes a single data profile and returns a summary from the LLM.
    """
    prompt = _render("analysis/data_profile_summary.txt.j2", {"profile": profile})
    llm_result = get_llm_response(prompt)
    return llm_result

def generate_ddl_with_explanation(payload: dict):
    """
    Render DDL drafts for PG/CH/HDFS and ask OpenAI to explain in RU, offering simple improvements.
    payload = {
      "target_system": "clickhouse|postgres|hdfs",
      "table": {"db":"analytics","table":"sales_by_day"},
      "columns": [{"name":"dt","type":"Date","nullable":False},{"name":"total_amount","type":"Int64"}],
      "partition_by": "toYYYYMM(dt)",
      "order_by": ["dt"],
      "indexes": ["dt"]   # for PG
    }
    """
    system = payload.get("target_system","clickhouse")
    if system == "clickhouse":
        ddl = _render("ddl/create_table_ch.sql.j2", payload)
    elif system == "postgres":
        ddl = _render("ddl/create_table_pg.sql.j2", payload)
    elif system == "hdfs":
        # For HDFS, generate directory structure and metadata
        ddl = _render("ddl/create_hdfs_structure.txt.j2", payload)
    else:
        # Default to PostgreSQL for unknown systems
        ddl = _render("ddl/create_table_pg.sql.j2", payload)

    prompt = f"""
Выводи по-русски. Дано DDL (SQL) таблицы. Объясни простыми словами, почему такая структура уместна.
Если видишь безопасные улучшения (партиции/ORDER BY/индексы), перечисли кратко.
DDL:
{ddl}
    """
    
    llm_result = get_llm_response(prompt)
    explanation = llm_result["content"]
    debug_log = llm_result["debug_log"]

    return {"system": system, "ddl": ddl, "explanation": explanation, "debug_log": debug_log}
