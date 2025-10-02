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
