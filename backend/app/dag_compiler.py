import os
from jinja2 import Environment, FileSystemLoader

TPL_DIR = os.path.join(os.path.dirname(__file__), "templates", "dag")
DAGS_DIR = os.environ.get("AIRFLOW_DAGS_DIR", "/airflow_dags")

env = Environment(loader=FileSystemLoader(TPL_DIR), autoescape=False, trim_blocks=True, lstrip_blocks=True)

def compile_dag(dsl: dict) -> str:
    tpl = env.get_template("dag_template.py.j2")
    code = tpl.render(**dsl)
    fname = f"generated_{dsl['name']}.py"
    out = os.path.join(DAGS_DIR, fname)
    with open(out, "w", encoding="utf-8") as f:
        f.write(code)
    return out
