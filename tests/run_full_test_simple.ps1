# ==============================================================================
# Полный интеграционный тест для Модуля 4 (упрощенная версия)
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "--- Starting FULL Integration Test for Module 4 ---" -ForegroundColor Yellow

# Шаг 0: Проверка сервисов
Write-Host "`n[Step 0] Checking services..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5 | Out-Null
    Write-Host "[OK] API is healthy" -ForegroundColor Green
} catch {
    throw "API service is not available"
}

try {
    Invoke-RestMethod -Uri "http://localhost:8123/ping" -TimeoutSec 5 | Out-Null
    Write-Host "[OK] ClickHouse is healthy" -ForegroundColor Green
} catch {
    throw "ClickHouse service is not available"
}

# Шаг 1: Подготовка данных
Write-Host "`n[Step 1] Preparing test data..." -ForegroundColor Cyan

# Создаем расширенный тестовый файл
$testData = @"
id,product_name,category,price,quantity,sale_date,customer_id,is_premium,discount_rate,region
1,Laptop Pro,Electronics,1299.99,2,2024-01-15,101,true,0.05,North
2,Wireless Mouse,Electronics,29.99,5,2024-01-16,102,false,0.0,South
3,Office Chair,Furniture,199.99,1,2024-01-17,103,true,0.1,East
4,Coffee Maker,Appliances,89.99,3,2024-01-18,104,false,0.0,West
5,Smartphone,Electronics,699.99,1,2024-01-19,105,true,0.15,North
"@

$testData | Out-File -FilePath "data_landing_zone/raw/sales_extended.csv" -Encoding UTF8
Write-Host "Created extended test data file"

# Вставляем рекомендации через Python скрипт
Write-Host "Inserting optimization recommendations..."
python tests/insert_extended_recommendations.py

# Шаг 2: Создание DataProfile
Write-Host "`n[Step 2] Creating DataProfile..." -ForegroundColor Cyan
$inventory = Invoke-RestMethod -Uri "http://localhost:8000/api/data-inventory"
$existing_profile = $inventory.data | Where-Object { $_.source_path -eq "/data/raw/sales_extended.csv" }

if ($existing_profile) {
    $profile_id = $existing_profile.id
    Write-Host "Found existing DataProfile with ID: $profile_id"
} else {
    $profileBody = @{ source_path = "/data/raw/sales_extended.csv" } | ConvertTo-Json
    $profile = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/data-profiles" -Method POST -ContentType "application/json" -Body $profileBody
    $profile_id = $profile.id
    Write-Host "Created new DataProfile with ID: $profile_id"
}

# Шаг 3: Запуск проектирования
Write-Host "`n[Step 3] Starting design process..." -ForegroundColor Cyan
$designBody = @{
    source_profile_id = $profile_id
    business_requirements = "Высокопроизводительная аналитика продаж"
    analytics_requirements = @{
        refresh_interval = "hourly"
        metrics = @("revenue", "orders")
    }
    constraints = @{
        sla = "99.9"
        budget = "high"
    }
} | ConvertTo-Json -Depth 3

$design = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design" -Method POST -ContentType "application/json" -Body $designBody
$design_id = $design.design_id
Write-Host "Design ID: $design_id"

# Шаг 4: Подтверждение и генерация DDL
Write-Host "`n[Step 4] Confirming design..." -ForegroundColor Cyan
$confirmBody = @{
    chosen_db = "clickhouse"
    accept_llm = $true
    notes = "ClickHouse для аналитики"
} | ConvertTo-Json

$confirmResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design/$design_id/confirm" -Method POST -ContentType "application/json" -Body $confirmBody
Write-Host "Status: $($confirmResponse.status)"

$ddl_script = $confirmResponse.results.ddl_script
Write-Host "`nGenerated DDL:"
Write-Host "=============="
Write-Host $ddl_script
Write-Host "=============="

# Проверяем оптимизации
$has_partition = $ddl_script -match "PARTITION BY"
$has_order = $ddl_script -match "ORDER BY"

if ($has_partition) {
    Write-Host "[SUCCESS] DDL contains PARTITION BY optimization" -ForegroundColor Green
}
if ($has_order) {
    Write-Host "[SUCCESS] DDL contains ORDER BY optimization" -ForegroundColor Green
}

# Шаг 5: Создание таблиц
Write-Host "`n[Step 5] Creating tables..." -ForegroundColor Cyan
try {
    $createResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/create/$design_id" -Method POST
    
    if ($createResponse.status -eq "success") {
        Write-Host "[SUCCESS] Tables created in ClickHouse" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Table creation failed: $($createResponse.message)" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Exception during table creation: $($_.Exception.Message)" -ForegroundColor Red
}

# Шаг 6: Проверка таблиц
Write-Host "`n[Step 6] Verifying tables..." -ForegroundColor Cyan
try {
    $tables = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SHOW TABLES FROM analytics" -ContentType "text/plain"
    
    if ($tables -match "sales_extended") {
        Write-Host "[SUCCESS] Table found in ClickHouse" -ForegroundColor Green
        
        # Проверяем структуру
        $structure = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "DESCRIBE analytics.sales_extended" -ContentType "text/plain"
        Write-Host "Table structure:"
        Write-Host $structure
    } else {
        Write-Host "[WARNING] Table not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Failed to verify table: $($_.Exception.Message)" -ForegroundColor Red
}

# Шаг 7: Генерация ETL
Write-Host "`n[Step 7] Generating ETL pipeline..." -ForegroundColor Cyan
try {
    $etlResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/load-data/$design_id" -Method POST
    
    if ($etlResponse.status -eq "created") {
        Write-Host "[SUCCESS] ETL pipeline created: $($etlResponse.dag_id)" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] ETL creation failed" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Exception during ETL generation: $($_.Exception.Message)" -ForegroundColor Red
}

# Финальная проверка
Write-Host "`n[Final Check] Results..." -ForegroundColor Cyan

$results = @{
    "DDL Generated" = ($ddl_script -and $ddl_script.Length -gt 0)
    "Optimizations Applied" = ($has_partition -or $has_order)
    "Tables Created" = ($createResponse.status -eq "success")
    "ETL Generated" = ($etlResponse.status -eq "created")
}

$passed = 0
foreach ($check in $results.GetEnumerator()) {
    $status = if ($check.Value) { "[PASS]"; $passed++ } else { "[FAIL]" }
    $color = if ($check.Value) { "Green" } else { "Red" }
    Write-Host "$status $($check.Key)" -ForegroundColor $color
}

Write-Host "`n=== RESULTS ===" -ForegroundColor Yellow
Write-Host "Passed: $passed / $($results.Count)"

if ($passed -eq $results.Count) {
    Write-Host "`n--- FULL Integration Test PASSED ---" -ForegroundColor Green
    Write-Host "Complete end-to-end workflow successful!" -ForegroundColor Green
} else {
    Write-Host "`n--- Integration Test PARTIALLY PASSED ---" -ForegroundColor Yellow
}

Write-Host "`nTest completed!" -ForegroundColor Cyan
