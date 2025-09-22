#!/usr/bin/env bash
set -euo pipefail

# This script generates the complete directory structure and files for the AiEasyData project.
# To run on Windows, you need a bash environment like WSL or Git Bash.

ROOT="AiEasyData_Skeleton_OpenAI"

echo "--- Creating project structure in ./${ROOT}/ ---"

# Helper functions to create directories and write files
mk() { mkdir -p "$1"; }
wr() { 
    mkdir -p "$(dirname "$1")"; 
    cat > "$1" 
}

# ---------------------------
# 1. Create directory structure
# ---------------------------
mk "$ROOT"
mk "$ROOT/backend/app/templates/ddl"
mk "$ROOT/backend/app/templates/dag"
mk "$ROOT/backend/app/dsl_examples"
mk "$ROOT/airflow/dags"
mk "$ROOT/db/init"
mk "$ROOT/ui/src"

echo "Directory structure created."

# ---------------------------
# 2. Write configuration files
# ---------------------------
echo "Writing docker-compose.yml..."
wr "$ROOT/docker-compose.yml" <<'YAML'
version: "3.9"

x-airflow-env: &airflow-env
  AIRFLOW__CORE__LOAD_EXAMPLES: "False"
  AIRFLOW__CORE__EXECUTOR: "LocalExecutor"
  AIRFLOW__WEBSERVER__EXPOSE_CONFIG: "True"
  AIRFLOW__WEBSERVER__RBAC: "True"
  AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/aieasydata
  AIRFLOW_UID: "50000"

services:
  # =============== DATA LAYER (core) ===============
  hdfs-namenode:
    image: bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8
    profiles: [core]
    container_name: aie_hdfs_nn
    environment:
      - CLUSTER_NAME=aieasydata
      - CORE_CONF_fs_defaultFS=hdfs://hdfs-namenode:8020
    ports: [ "9870:9870" ]
    volumes: [ "hdfs_name:/hadoop/dfs/name" ]

  hdfs-datanode:
    image: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8
    profiles: [core]
    container_name: aie_hdfs_dn
    environment:
      - CORE_CONF_fs_defaultFS=hdfs://hdfs-namenode:8020
      - CLUSTER_NAME=aieasydata
    volumes: [ "hdfs_data:/hadoop/dfs/data" ]
    depends_on: [ hdfs-namenode ]
    ports: [ "9864:9864" ]

  postgres:
    image: postgres:16
    profiles: [core]
    container_name: aie_pg
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: aieasydata
    ports: [ "5432:5432" ]
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d

  clickhouse:
    image: clickhouse/clickhouse-server:24.8
    profiles: [core]
    container_name: aie_ch
    ports: [ "8123:8123", "9000:9000" ]
    volumes: [ "ch_data:/var/lib/clickhouse" ]

  # =============== ORCHESTRATION (core) ===============
  airflow:
    image: apache/airflow:2.9.3
    profiles: [core]
    container_name: aie_airflow
    depends_on:
      - postgres
    environment:
      <<: *airflow-env
      # (не обязательно, но полезно) ключ шифрования для паролей коннекшенов:
      AIRFLOW__CORE__FERNET_KEY: "m2mZ0O0N5Gm7pZ5uQ2a3o6R8t1u2w3x4y5z6A7B8C9D="
    user: "50000:0"
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./airflow/requirements.txt:/opt/airflow/requirements.txt
    command: >
      bash -lc "
      pip install --no-cache-dir -r /opt/airflow/requirements.txt &&
      until pg_isready -h postgres -p 5432 -U ${POSTGRES_USER}; do echo 'waiting for postgres...' && sleep 2; done &&
      airflow db check || airflow db init &&
      airflow db upgrade &&
      airflow users create --username admin --firstname Ai --lastname Easy --role Admin --email admin@example.com --password admin || true &&
      airflow webserver & airflow scheduler
      "
    ports:
      - "8080:8080"

  # =============== BACKEND & UI (core) ===============
  api:
    image: python:3.11-slim
    profiles: [core]
    container_name: aie_api
    working_dir: /app
    environment:
      POSTGRES_DSN: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/aieasydata
      CLICKHOUSE_HTTP: http://clickhouse:8123
      HDFS_WEB: http://hdfs-namenode:9870
      AIRFLOW_DAGS_DIR: /airflow_dags
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_BASE_URL: ${OPENAI_BASE_URL:-}
      OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4o-mini}
    volumes:
      - ./backend:/app
      - ./airflow/dags:/airflow_dags
    command: bash -lc "pip install --no-cache-dir -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000"
    ports: [ "8000:8000" ]
    depends_on: [ postgres, clickhouse, hdfs-namenode, airflow ]

  ui:
    image: node:18
    profiles: [core]
    container_name: aie_ui
    working_dir: /app
    environment:
      VITE_API_BASE: http://localhost:8000
    volumes:
      - ./ui:/app
    command: bash -lc "npm install && npm run dev -- --host 0.0.0.0 --port 3000"
    ports: [ "3000:3000" ]
    depends_on: [ api ]

  # =============== STREAMING (optional) ===============
  zookeeper:
    image: bitnami/zookeeper:3.9
    profiles: [stream]
    container_name: aie_zk
    environment: [ "ALLOW_ANONYMOUS_LOGIN=yes" ]
    ports: [ "2181:2181" ]

  kafka:
    image: bitnami/kafka:3.6
    profiles: [stream]
    container_name: aie_kafka
    environment:
      - KAFKA_CFG_ZOOKEEPER_CONNECT=zookeeper:2181
      - ALLOW_PLAINTEXT_LISTENER=yes
      - KAFKA_CFG_LISTENERS=PLAINTEXT://:9092
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
      - KAFKA_CFG_OFFSETS_TOPIC_REPLICATION_FACTOR=1
    depends_on: [ zookeeper ]
    ports: [ "9092:9092" ]

volumes:
  hdfs_name:
  hdfs_data:
  pg_data:
  ch_data:
YAML

echo "Writing .env.example..."
wr "$ROOT/.env.example" <<'ENV'
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow

# OpenAI API (обязательно для этой версии)
OPENAI_API_KEY=sk-...
# (опц.) альтернативный базовый URL (если нужен прокси/регион)
# OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
ENV

echo "Writing README.md..."
wr "$ROOT/README.md" <<'MD'
# AiEasyData — Skeleton (OpenAI API version)

Эта версия использует **OpenAI API** (Responses API / Chat Completions) для ИИ-агента.

## Требования
- Docker Desktop (Compose v2). Ресурсы: 4 vCPU, 8 GB RAM, 20+ GB диска.
- **OpenAI API ключ** (платный, pay-as-you-go). Хранить в `.env`.

## Запуск

1.  Переименуйте `.env.example` в `.env` и укажите ваш `OPENAI_API_KEY`.
2.  Запустите все сервисы командой:
    ```bash
    docker-compose up -d --build
    ```

## Основные эндпоинты
- **UI**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs
- **Airflow**: http://localhost:8080 (логин/пароль: `admin`/`admin`)
- **HDFS NameNode**: http://localhost:9870
MD

# ---------------------------
# 3. Write application files
# ---------------------------
echo "Writing backend and airflow requirements..."
wr "$ROOT/backend/requirements.txt" <<'PIP'
fastapi==0.115.0
uvicorn[standard]==0.30.6
jinja2==3.1.4
pydantic==2.8.2
psycopg2-binary==2.9.9
clickhouse-connect==0.7.17
requests==2.32.3
polars==1.9.0
pandera==0.20.3
pyarrow==16.1.0
openai>=1.30.0
PIP

wr "$ROOT/airflow/requirements.txt" <<'PIP'
psycopg2-binary==2.9.9
clickhouse-connect==0.7.17
pandas==2.2.2
polars==1.9.0
pandera==0.20.3
pyarrow==16.1.0
requests==2.32.3
PIP

echo "Writing backend application source..."
wr "$ROOT/backend/app/main.py" <<'PY'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any
import os
from . import agent, analyzer, rule_engine, dag_compiler

app = FastAPI(title="AiEasyData API (OpenAI)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class DSLModel(BaseModel):
    name: str
    mode: Literal["batch","stream"] = "batch"
    schedule: Optional[str] = "0 * * * *"
    source: Dict[str, Any]
    validate: Optional[Dict[str, Any]] = None
    transforms: Optional[List[Dict[str, Any]]] = []
    target: Dict[str, Any]
    ddl_overrides: Optional[Dict[str, str]] = {}

@app.get("/health")
def health():
    return {"ok": True, "uses": "OpenAI API", "model": os.environ.get("OPENAI_MODEL","gpt-4o-mini")}

@app.post("/analyze")
def api_analyze(cfg: Dict[str, Any]):
    return analyzer.quick_profile(cfg)

@app.post("/recommend")
def api_recommend(profile: Dict[str, Any]):
    return rule_engine.recommend(profile)

@app.post("/ddl")
def api_ddl(payload: Dict[str, Any]):
    return agent.generate_ddl_with_explanation(payload)

@app.post("/dag/compile")
def api_dag_compile(dsl: DSLModel):
    path = dag_compiler.compile_dag(dsl.model_dump())
    return {"dag_path": path, "message": "DAG generated. Open Airflow UI to trigger."}
PY

wr "$ROOT/backend/app/agent.py" <<'PY'
import os, json
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

TPL_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TPL_DIR), autoescape=False, trim_blocks=True, lstrip_blocks=True)

def _client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    base = os.environ.get("OPENAI_BASE_URL")  # optional
    return OpenAI(api_key=api_key, base_url=base) if base else OpenAI(api_key=api_key)

def _render(tpl_path: str, ctx: dict) -> str:
    tpl = env.get_template(tpl_path)
    return tpl.render(**ctx)

def generate_ddl_with_explanation(payload: dict):
    system = payload.get("target_system","clickhouse")
    if system == "clickhouse":
        ddl = _render("ddl/create_table_ch.sql.j2", payload)
    else:
        ddl = _render("ddl/create_table_pg.sql.j2", payload)

    client = _client()
    model = os.environ.get("OPENAI_MODEL","gpt-4o-mini")
    prompt = f"""
Выводи по-русски. Дано DDL (SQL) таблицы. Объясни простыми словами, почему такая структура уместна.
Если видишь безопасные улучшения (партиции/ORDER BY/индексы), перечисли кратко.
DDL:
{ddl}
    """
    try:
        resp = client.chat.completions.create(model=model, messages=[{"role":"user","content":prompt}])
        explanation = resp.choices[0].message.content
    except Exception as e:
        explanation = f"Error calling OpenAI: {e}"

    return {"system": system, "ddl": ddl, "explanation": explanation}
PY

wr "$ROOT/backend/app/analyzer.py" <<'PY'
def quick_profile(cfg: dict):
    """Minimal stub profiler: columns and hints; replace with real sampling."""
    sample = [{"dt":"2025-09-01","amount":100},{"dt":"2025-09-02","amount":120}]
    columns = [{"name":"dt","type":"Date"},{"name":"amount","type":"Int64"}]
    profile = {"columns": columns, "est_rows": 1_000_000, "ts_fields":["dt"], "sample": sample}
    return profile
PY

wr "$ROOT/backend/app/rule_engine.py" <<'PY'
def recommend(profile: dict):
    rows = profile.get("est_rows", 0)
    ts_fields = profile.get("ts_fields", [])
    if rows >= 1_000_000 and ts_fields:
        return {
            "system": "clickhouse",
            "rationale": "Большой объём и есть поле времени → ClickHouse (MergeTree).",
            "partition_by": f"toYYYYMM({ts_fields[0]})",
            "order_by": ["dt"]
        }
    if rows < 1_000_000 and not ts_fields:
        return {
            "system": "postgres",
            "rationale": "Небольшой объём и нет явного времени → PostgreSQL.",
            "indexes": ["id"]
        }
    return {
        "system": "hdfs",
        "rationale": "Сырые/разнородные данные либо архив → HDFS (Parquet)."
    }
PY

wr "$ROOT/backend/app/dag_compiler.py" <<'PY'
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
PY

echo "Writing DDL and DAG templates..."
wr "$ROOT/backend/app/templates/ddl/create_table_ch.sql.j2" <<'SQL'
-- ClickHouse DDL (MergeTree)
CREATE DATABASE IF NOT EXISTS {{ table.db }};

CREATE TABLE IF NOT EXISTS {{ table.db }}.{{ table.table }} (
{% for col in columns -%}
  {{ col.name }} {{ col.type }}{% if not loop.last %},{% endif %}
{% endfor %}
)
ENGINE = MergeTree
{% if partition_by %}PARTITION BY {{ partition_by }}{% endif %}
{% if order_by %}ORDER BY ({{ order_by | join(', ') }}){% else %}ORDER BY tuple(){% endif %};
SQL

wr "$ROOT/backend/app/templates/ddl/create_table_pg.sql.j2" <<'SQL'
-- PostgreSQL DDL
CREATE SCHEMA IF NOT EXISTS {{ table.db }};
CREATE TABLE IF NOT EXISTS {{ table.db }}.{{ table.table }} (
{% for col in columns -%}
  {{ col.name }} {{ col.type }}{% if not loop.last %},{% endif %}
{% endfor %}
);
{% if indexes %}
-- indexes
{% for idx in indexes %}
CREATE INDEX IF NOT EXISTS idx_{{ table.table }}_{{ idx }} ON {{ table.db }}.{{ table.table }}({{ idx }});
{% endfor %}
{% endif %}
SQL

wr "$ROOT/backend/app/templates/dag/dag_template.py.j2" <<'PY'
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime

default_args = {"owner":"ai", "retries":0}

with DAG(
    dag_id="{{ name }}",
    start_date=datetime(2025, 9, 1),
    schedule="{{ schedule }}",
    catchup=False,
    tags=["generated","aieasydata"],
) as dag:

    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    def ingest(**ctx):
        print("Ingest from: {{ source.type }} with options: {{ source.options | tojson }}")

    def validate(**ctx):
        print("Validate checks: {{ (validate.checks if validate else []) | tojson }}")

    def transform(**ctx):
        print("Transforms: {{ transforms | tojson }}")

    def load(**ctx):
        print("Load to: {{ target.system }} object: {{ target.object }}")

    t_ingest = PythonOperator(task_id="ingest", python_callable=ingest)
    t_validate = PythonOperator(task_id="validate", python_callable=validate)
    t_transform = PythonOperator(task_id="transform", python_callable=transform)
    t_load = PythonOperator(task_id="load", python_callable=load)

    start >> t_ingest >> t_validate >> t_transform >> t_load >> end
PY

echo "Writing DSL example..."
wr "$ROOT/backend/app/dsl_examples/sales_daily.json" <<'JSON'
{
  "name": "sales_daily",
  "mode": "batch",
  "schedule": "0 * * * *",
  "source": { "type": "csv", "options": { "path": "/data/sales_*.csv", "delimiter": "," } },
  "validate": { "checks": ["not_null:amount","type:amount:int"] },
  "transforms": [
    { "op":"derive","expr":"dt = toDate(event_time)" },
    { "op":"agg","by":["dt"],"metrics":[{"sum":"amount"}] }
  ],
  "target": { "system": "clickhouse", "object": "analytics.sales_by_day", "partitions": ["dt"] },
  "ddl_overrides": {}
}
JSON

echo "Writing DB init script..."
wr "$ROOT/db/init/catalog_schema.sql" <<'SQL'
CREATE SCHEMA IF NOT EXISTS catalog;

CREATE TABLE IF NOT EXISTS catalog.connections (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  uri TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS catalog.datasets (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  zone TEXT NOT NULL,
  schema_json JSONB,
  location TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS catalog.pipelines (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  dsl_json JSONB NOT NULL,
  schedule TEXT,
  target_system TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS catalog.runs (
  id SERIAL PRIMARY KEY,
  pipeline_id INT REFERENCES catalog.pipelines(id),
  dag_run_id TEXT,
  status TEXT,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  rows_in BIGINT,
  rows_out BIGINT,
  notes TEXT
);
SQL

# ---------------------------
# 4. Write UI files
# ---------------------------
echo "Writing UI package files..."
wr "$ROOT/ui/package.json" <<'JSON'
{
  "name": "aieasydata-ui",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview --port 3000"
  },
  "dependencies": {
    "axios": "1.7.2",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "reactflow": "11.10.3"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "4.3.1",
    "vite": "5.4.2"
  }
}
JSON

wr "$ROOT/ui/vite.config.js" <<'JS'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({ plugins: [react()], server: { port: 3000, host: true }})
JS

wr "$ROOT/ui/index.html" <<'HTML'
<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AiEasyData UI</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
HTML

echo "Writing UI source files..."
wr "$ROOT/ui/src/main.jsx" <<'JSX'
import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
createRoot(document.getElementById('root')).render(<App />)
JSX

wr "$ROOT/ui/src/App.jsx" <<'JSX'
import React, { useState } from 'react'
import axios from 'axios'
const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function App() {
  const [health, setHealth] = useState('unknown')
  const [ddl, setDDL] = useState('')
  const [explanation, setExplanation] = useState('')

  const [payload, setPayload] = useState({
    target_system: "clickhouse",
    table: { db: "analytics", table: "sales_by_day" },
    columns: [
      { name: "dt", type: "Date", nullable: false },
      { name: "total_amount", type: "Int64", nullable: false }
    ],
    partition_by: "toYYYYMM(dt)",
    order_by: ["dt"],
    indexes: ["dt"]
  })

  const [dsl, setDsl] = useState(JSON.stringify({
    name: "sales_daily",
    mode: "batch",
    schedule: "0 * * * *",
    source: { type: "csv", options: { path: "/data/sales_*.csv", delimiter: "," } },
    validate: { checks: ["not_null:amount","type:amount:int"] },
    transforms: [
      { op:"derive", expr:"dt = toDate(event_time)" },
      { op:"agg", by:["dt"], metrics:[{ sum:"amount" }] }
    ],
    target: { system:"clickhouse", object:"analytics.sales_by_day", partitions:["dt"] }
  }, null, 2))

  async function checkHealth(){ const r = await axios.get(`${API}/health` ); setHealth(r.data.ok ? `ok (${r.data.uses}, ${r.data.model})`  : 'fail') }
  async function genDDL(){ const r = await axios.post(`${API}/ddl` , payload); setDDL(r.data.ddl); setExplanation(r.data.explanation) }
  async function compileDAG(){ const payload = JSON.parse(dsl); const r = await axios.post(`${API}/dag/compile` , payload); alert(`DAG generated at: ${r.data.dag_path}` ) }

  return (
    <div style={{fontFamily:'sans-serif', padding:20}}>
      <h1>AiEasyData — UI (OpenAI)</h1>
      <button onClick={checkHealth}>Check API health</button> <b>{health}</b>

      <h2>1) Генерация DDL + объяснение (через OpenAI)</h2>
      <pre style={{background:'#f6f6f6', padding:10}}>{JSON.stringify(payload, null, 2)}</pre>
      <button onClick={genDDL}>Generate DDL + Explain</button>
      <h3>DDL</h3>
      <pre style={{whiteSpace:'pre-wrap', background:'#f0f0f0', padding:10}}>{ddl}</pre>
      <h3>Пояснение ИИ</h3>
      <p style={{whiteSpace:'pre-wrap'}}>{explanation}</p>

      <h2>2) JSON-DSL → DAG</h2>
      <textarea value={dsl} onChange={e=>setDsl(e.target.value)} style={{width:'100%', height:300, fontFamily:'monospace'}} />
      <div style={{marginTop:10}}>
        <button onClick={compileDAG}>Compile DAG</button>
      </div>
      <p>Откройте Airflow: <a href="http://localhost:8080" target="_blank" rel="noreferrer">http://localhost:8080</a></p>
    </div>
  )
}
JSX

echo "--- Project generation complete! ---"
echo "Next steps:"
echo "1. cd AiEasyData_Skeleton_OpenAI"
echo "2. cp .env.example .env"
echo "3. Edit .env to add your OPENAI_API_KEY"
echo "4. docker-compose up -d --build"

