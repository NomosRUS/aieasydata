# ==============================================================================
# Диагностический скрипт для Модуля 4
# Проверяет состояние всех компонентов и помогает выявить проблемы
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host "=== Module 4 Diagnostic Tool ===" -ForegroundColor Yellow
Write-Host "Checking all components and data flow..." -ForegroundColor Yellow

# --- Проверка 1: Состояние сервисов ---
Write-Host "`n[Check 1] Service Health Status" -ForegroundColor Cyan

$services = @(
    @{name="PostgreSQL"; url=""; port=5432; host="localhost"},
    @{name="ClickHouse"; url="http://localhost:8123/ping"; port=8123},
    @{name="API Server"; url="http://localhost:8000/health"; port=8000},
    @{name="Airflow"; url="http://localhost:8080/health"; port=8080}
)

foreach ($service in $services) {
    Write-Host "Checking $($service.name)..." -NoNewline
    
    if ($service.url) {
        try {
            $response = Invoke-RestMethod -Uri $service.url -TimeoutSec 5 -ErrorAction Stop
            Write-Host " [OK]" -ForegroundColor Green
        } catch {
            Write-Host " [ERROR] $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        # Port check for services without HTTP endpoint
        try {
            $connection = Test-NetConnection -ComputerName $service.host -Port $service.port -WarningAction SilentlyContinue
            if ($connection.TcpTestSucceeded) {
                Write-Host " [OK]" -ForegroundColor Green
            } else {
                Write-Host " [ERROR] Port not accessible" -ForegroundColor Red
            }
        } catch {
            Write-Host " [ERROR] Connection failed" -ForegroundColor Red
        }
    }
}

# --- Проверка 2: База данных и таблицы ---
Write-Host "`n[Check 2] Database Tables and Data" -ForegroundColor Cyan

try {
    # Проверяем таблицы в PostgreSQL
    Write-Host "Checking PostgreSQL tables..."
    $inventory = Invoke-RestMethod -Uri "http://localhost:8000/api/data-inventory" -ErrorAction Stop
    Write-Host "  - data_profiles: $($inventory.total_count) records" -ForegroundColor Green
    
    # Проверяем рекомендации оптимизации
    python -c "
import os, psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

try:
    load_dotenv()
    DATABASE_URL = os.getenv('POSTGRES_DSN').replace('@postgres:', '@localhost:')
    result = urlparse(DATABASE_URL)
    db_params = {
        'user': result.username, 'password': result.password,
        'host': result.hostname, 'port': result.port, 'dbname': result.path[1:]
    }
    
    with psycopg2.connect(**db_params) as conn:
        with conn.cursor() as cur:
            # Проверяем optimization_recommendations
            cur.execute('SELECT COUNT(*) FROM optimization_recommendations')
            opt_count = cur.fetchone()[0]
            print(f'  - optimization_recommendations: {opt_count} records')
            
            # Проверяем warehouse_designs
            cur.execute('SELECT COUNT(*) FROM warehouse_designs')
            design_count = cur.fetchone()[0]
            print(f'  - warehouse_designs: {design_count} records')
            
            # Проверяем warehouse_instances
            cur.execute('SELECT COUNT(*) FROM warehouse_instances')
            instance_count = cur.fetchone()[0]
            print(f'  - warehouse_instances: {instance_count} records')
            
            # Показываем последние рекомендации
            cur.execute('SELECT table_name, recommendation_type, recommendation_details FROM optimization_recommendations ORDER BY created_at DESC LIMIT 3')
            recommendations = cur.fetchall()
            if recommendations:
                print('  Latest recommendations:')
                for rec in recommendations:
                    print(f'    * {rec[0]} -> {rec[1]}: {rec[2]}')
            
except Exception as e:
    print(f'  [ERROR] Database check failed: {e}')
"

} catch {
    Write-Host "  [ERROR] Failed to check PostgreSQL: $($_.Exception.Message)" -ForegroundColor Red
}

# Проверяем ClickHouse
try {
    Write-Host "Checking ClickHouse databases..."
    $databases = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SHOW DATABASES" -ContentType "text/plain" -ErrorAction Stop
    if ($databases -match "analytics") {
        Write-Host "  - analytics database: [EXISTS]" -ForegroundColor Green
        
        # Проверяем таблицы в analytics
        $tables = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SHOW TABLES FROM analytics" -ContentType "text/plain"
        if ($tables.Trim()) {
            Write-Host "  - Tables in analytics:"
            $tables.Split("`n") | ForEach-Object {
                if ($_.Trim()) {
                    Write-Host "    * $($_.Trim())" -ForegroundColor Green
                    
                    # Проверяем количество записей в каждой таблице
                    try {
                        $count = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SELECT COUNT(*) FROM analytics.$($_.Trim())" -ContentType "text/plain"
                        Write-Host "      Records: $($count.Trim())" -ForegroundColor Gray
                    } catch {
                        Write-Host "      Records: [ERROR]" -ForegroundColor Red
                    }
                }
            }
        } else {
            Write-Host "  - No tables found in analytics database" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  - analytics database: [NOT FOUND]" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] Failed to check ClickHouse: $($_.Exception.Message)" -ForegroundColor Red
}

# --- Проверка 3: Файлы данных ---
Write-Host "`n[Check 3] Data Files" -ForegroundColor Cyan

$dataFiles = @(
    "data_landing_zone/raw/sales.csv",
    "data_landing_zone/raw/sales_extended.csv",
    "temp_sales.csv"
)

foreach ($file in $dataFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length
        Write-Host "  - $file: [EXISTS] ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "  - $file: [NOT FOUND]" -ForegroundColor Yellow
    }
}

# --- Проверка 4: Airflow DAGs ---
Write-Host "`n[Check 4] Airflow DAGs" -ForegroundColor Cyan

try {
    # Проверяем сгенерированные DAG файлы
    $dagFiles = Get-ChildItem -Path "airflow/dags" -Filter "generated_warehouse_etl_*.py" -ErrorAction SilentlyContinue
    if ($dagFiles) {
        Write-Host "  - Generated DAG files: $($dagFiles.Count)" -ForegroundColor Green
        $dagFiles | ForEach-Object {
            Write-Host "    * $($_.Name) ($(Get-Date $_.LastWriteTime -Format 'yyyy-MM-dd HH:mm'))" -ForegroundColor Gray
        }
    } else {
        Write-Host "  - No generated DAG files found" -ForegroundColor Yellow
    }
    
    # Пытаемся получить список DAGs из Airflow API
    try {
        $airflowDags = Invoke-RestMethod -Uri "http://localhost:8080/api/v1/dags" -Headers @{Authorization="Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin"))} -ErrorAction Stop
        $warehouseDags = $airflowDags.dags | Where-Object { $_.dag_id -like "*warehouse_etl*" }
        if ($warehouseDags) {
            Write-Host "  - Warehouse DAGs in Airflow: $($warehouseDags.Count)" -ForegroundColor Green
            $warehouseDags | ForEach-Object {
                $status = if ($_.is_active) { "ACTIVE" } else { "INACTIVE" }
                Write-Host "    * $($_.dag_id): [$status]" -ForegroundColor Gray
            }
        } else {
            Write-Host "  - No warehouse DAGs found in Airflow" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  - Cannot access Airflow API (may be normal): $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "  [ERROR] Failed to check Airflow DAGs: $($_.Exception.Message)" -ForegroundColor Red
}

# --- Проверка 5: Последние операции ---
Write-Host "`n[Check 5] Recent Operations" -ForegroundColor Cyan

try {
    # Проверяем последние дизайны хранилищ
    python -c "
import os, psycopg2, json
from dotenv import load_dotenv
from urllib.parse import urlparse

try:
    load_dotenv()
    DATABASE_URL = os.getenv('POSTGRES_DSN').replace('@postgres:', '@localhost:')
    result = urlparse(DATABASE_URL)
    db_params = {
        'user': result.username, 'password': result.password,
        'host': result.hostname, 'port': result.port, 'dbname': result.path[1:]
    }
    
    with psycopg2.connect(**db_params) as conn:
        with conn.cursor() as cur:
            # Последние дизайны
            cur.execute('''
                SELECT design_id, status, selected_db, created_at 
                FROM warehouse_designs 
                ORDER BY created_at DESC LIMIT 5
            ''')
            designs = cur.fetchall()
            
            if designs:
                print('  Recent warehouse designs:')
                for design in designs:
                    print(f'    * {design[0][:8]}... | {design[1]} | {design[2]} | {design[3]}')
            else:
                print('  - No warehouse designs found')
                
except Exception as e:
    print(f'  [ERROR] Cannot check recent operations: {e}')
"

} catch {
    Write-Host "  [ERROR] Failed to check recent operations: $($_.Exception.Message)" -ForegroundColor Red
}

# --- Проверка 6: Конфигурация ---
Write-Host "`n[Check 6] Configuration" -ForegroundColor Cyan

# Проверяем переменные окружения
$envVars = @("POSTGRES_DSN", "CLICKHOUSE_HTTP", "HDFS_WEB", "OPENAI_API_KEY")
foreach ($var in $envVars) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if ($value) {
        $maskedValue = if ($var -like "*KEY*" -or $var -like "*PASSWORD*") { 
            $value.Substring(0, [Math]::Min(10, $value.Length)) + "..." 
        } else { 
            $value 
        }
        Write-Host "  - $var: [SET] $maskedValue" -ForegroundColor Green
    } else {
        Write-Host "  - $var: [NOT SET]" -ForegroundColor Yellow
    }
}

# --- Рекомендации ---
Write-Host "`n[Recommendations] Troubleshooting Tips" -ForegroundColor Cyan

Write-Host "If you encounter issues:" -ForegroundColor White
Write-Host "  1. Ensure all Docker services are running: docker-compose ps" -ForegroundColor Gray
Write-Host "  2. Check service logs: docker-compose logs [service_name]" -ForegroundColor Gray
Write-Host "  3. Restart services if needed: docker-compose restart" -ForegroundColor Gray
Write-Host "  4. For ClickHouse connection issues, verify CLICKHOUSE_HTTP env var" -ForegroundColor Gray
Write-Host "  5. For Airflow DAG issues, check airflow/dags directory permissions" -ForegroundColor Gray
Write-Host "  6. For data loading issues, verify source file format and permissions" -ForegroundColor Gray

Write-Host "`n=== Diagnostic Complete ===" -ForegroundColor Yellow
