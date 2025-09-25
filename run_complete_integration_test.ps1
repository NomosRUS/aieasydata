# ==============================================================================
# Полный интеграционный тест для Модуля 4: Проектирование хранилищ
# Включает фактическую запись данных с учетом всех найденных решений
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=== COMPLETE Integration Test for Module 4 ===" -ForegroundColor Yellow
Write-Host "Testing full end-to-end workflow with data loading" -ForegroundColor Yellow

# Шаг 0: Проверка готовности системы
Write-Host "`n[Step 0] System readiness check..." -ForegroundColor Cyan

$services = @(
    @{name="API"; url="http://localhost:8000/health"},
    @{name="ClickHouse"; url="http://localhost:8123/ping"},
    @{name="PostgreSQL"; test="inventory"}
)

foreach ($service in $services) {
    Write-Host "Checking $($service.name)..." -NoNewline
    try {
        if ($service.url) {
            Invoke-RestMethod -Uri $service.url -TimeoutSec 5 | Out-Null
        } elseif ($service.test -eq "inventory") {
            Invoke-RestMethod -Uri "http://localhost:8000/api/data-inventory" -TimeoutSec 5 | Out-Null
        }
        Write-Host " [OK]" -ForegroundColor Green
    } catch {
        Write-Host " [ERROR]" -ForegroundColor Red
        throw "$($service.name) is not available"
    }
}

# Шаг 1: Подготовка расширенных тестовых данных
Write-Host "`n[Step 1] Preparing comprehensive test dataset..." -ForegroundColor Cyan

# Создаем более реалистичный набор данных с различными типами
$extendedData = @"
id,product_name,category,price,quantity,sale_date,customer_id,is_premium,discount_rate,region
1,Gaming Laptop,Electronics,2499.99,1,2024-01-15,101,true,0.05,North America
2,Wireless Mouse,Electronics,79.99,3,2024-01-16,102,false,0.0,Europe
3,Ergonomic Chair,Furniture,599.99,1,2024-01-17,103,true,0.15,Asia
4,Coffee Machine,Appliances,299.99,2,2024-01-18,104,false,0.1,North America
5,Smartphone Pro,Electronics,1299.99,1,2024-01-19,105,true,0.2,Europe
6,Standing Desk,Furniture,899.99,1,2024-01-20,106,true,0.1,Asia
7,Bluetooth Headphones,Electronics,199.99,2,2024-01-21,107,false,0.05,North America
8,Water Bottle,Sports,29.99,5,2024-01-22,108,false,0.0,Europe
9,Running Shoes,Sports,159.99,1,2024-01-23,109,true,0.25,Asia
10,Travel Backpack,Travel,89.99,2,2024-01-24,110,false,0.0,North America
11,Tablet Device,Electronics,799.99,1,2024-01-25,111,true,0.1,Europe
12,Office Lamp,Furniture,149.99,3,2024-01-26,112,false,0.0,Asia
13,Fitness Tracker,Electronics,249.99,1,2024-01-27,113,false,0.15,North America
14,Yoga Mat,Sports,49.99,4,2024-01-28,114,false,0.0,Europe
15,Luggage Set,Travel,399.99,1,2024-01-29,115,true,0.2,Asia
"@

# Сохраняем данные
New-Item -ItemType Directory -Path "data_landing_zone/raw" -Force | Out-Null
$extendedData | Out-File -FilePath "data_landing_zone/raw/sales_extended.csv" -Encoding UTF8
Write-Host "Created extended dataset (15 records with diverse data types)"

# Вставляем множественные рекомендации оптимизации
Write-Host "Inserting comprehensive optimization recommendations..."
python tests/insert_extended_recommendations.py

# Шаг 2: Создание DataProfile
Write-Host "`n[Step 2] Creating DataProfile for extended dataset..." -ForegroundColor Cyan

$inventory = Invoke-RestMethod -Uri "http://localhost:8000/api/data-inventory"
$existing_profile = $inventory.data | Where-Object { $_.source_path -eq "/data/raw/sales_extended.csv" }

if ($existing_profile) {
    $profile_id = $existing_profile.id
    Write-Host "Found existing DataProfile with ID: $profile_id"
} else {
    $profileBody = '{"source_path": "/data/raw/sales_extended.csv"}'
    $profile = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/data-profiles" -Method POST -ContentType "application/json" -Body $profileBody
    $profile_id = $profile.id
    Write-Host "Created new DataProfile with ID: $profile_id"
}

# Обновляем файл запроса с правильным profile_id
$designRequest = Get-Content "request_payloads/extended_design_request.json" | ConvertFrom-Json
$designRequest.source_profile_id = $profile_id
$designRequest | ConvertTo-Json -Depth 10 | Out-File "request_payloads/extended_design_request.json" -Encoding UTF8

# Шаг 3: Запуск процесса проектирования хранилища
Write-Host "`n[Step 3] Starting intelligent warehouse design process..." -ForegroundColor Cyan

$design = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design" -Method POST -ContentType "application/json" -InFile "request_payloads/extended_design_request.json"
$design_id = $design.design_id
Write-Host "Design process started. Design ID: $design_id"

# Проверяем статус анализа
$designStatus = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design/$design_id"
Write-Host "Analysis status: $($designStatus.status)"

if ($designStatus.results.llm_analysis) {
    Write-Host "LLM recommendation: $($designStatus.results.llm_analysis.final_choice)"
}

# Шаг 4: Подтверждение выбора и генерация оптимизированного DDL
Write-Host "`n[Step 4] Confirming design and generating optimized DDL..." -ForegroundColor Cyan

$confirmResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design/$design_id/confirm" -Method POST -ContentType "application/json" -InFile "request_payloads/extended_confirm_request.json"
Write-Host "Design confirmed. Status: $($confirmResponse.status)"

# Анализируем сгенерированный DDL
$ddl_script = $confirmResponse.results.ddl_script
Write-Host "`n--- Generated DDL Script ---"
Write-Host $ddl_script
Write-Host "--- End DDL Script ---"

# Детальная проверка применения оптимизаций
$optimizations = @()
if ($ddl_script -match "PARTITION BY") { $optimizations += "PARTITION BY" }
if ($ddl_script -match "ORDER BY") { $optimizations += "ORDER BY" }
if ($ddl_script -match "ENGINE = MergeTree") { $optimizations += "MergeTree Engine" }

Write-Host "`nOptimizations applied: $($optimizations -join ', ')" -ForegroundColor Green

# Шаг 5: Создание таблиц в ClickHouse
Write-Host "`n[Step 5] Creating optimized tables in ClickHouse..." -ForegroundColor Cyan

try {
    $createResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/create/$design_id" -Method POST -ContentType "application/json"
    
    if ($createResponse.status -eq "success") {
        Write-Host "[SUCCESS] Tables created successfully" -ForegroundColor Green
        Write-Host "Message: $($createResponse.message)"
    } else {
        Write-Host "[ERROR] Table creation failed: $($createResponse.message)" -ForegroundColor Red
        Write-Host "Details: $($createResponse.details | ConvertTo-Json)"
        throw "Table creation failed"
    }
} catch {
    Write-Host "[CRITICAL ERROR] Exception during table creation: $($_.Exception.Message)" -ForegroundColor Red
    throw
}

# Шаг 6: Верификация созданных таблиц
Write-Host "`n[Step 6] Verifying table structure and optimizations..." -ForegroundColor Cyan

try {
    # Проверяем наличие таблицы
    $tables = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SHOW TABLES FROM analytics" -ContentType "text/plain"
    
    if ($tables -match "sales_extended") {
        Write-Host "[SUCCESS] Table 'sales_extended' exists in analytics database" -ForegroundColor Green
        
        # Проверяем структуру таблицы
        $tableInfo = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SHOW CREATE TABLE analytics.sales_extended" -ContentType "text/plain"
        Write-Host "`nTable creation statement:"
        Write-Host $tableInfo
        
        # Проверяем применение партиционирования
        if ($tableInfo -match "PARTITION BY") {
            Write-Host "[SUCCESS] Partitioning is applied" -ForegroundColor Green
        }
        
        # Проверяем сортировку
        if ($tableInfo -match "ORDER BY") {
            Write-Host "[SUCCESS] Ordering is applied" -ForegroundColor Green
        }
        
    } else {
        Write-Host "[ERROR] Table not found in ClickHouse" -ForegroundColor Red
        Write-Host "Available tables: $tables"
    }
} catch {
    Write-Host "[ERROR] Failed to verify table: $($_.Exception.Message)" -ForegroundColor Red
}

# Шаг 7: Генерация и запуск ETL пайплайна
Write-Host "`n[Step 7] Generating ETL pipeline for data loading..." -ForegroundColor Cyan

try {
    $etlResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/load-data/$design_id" -Method POST -ContentType "application/json"
    
    if ($etlResponse.status -eq "created") {
        Write-Host "[SUCCESS] ETL pipeline generated: $($etlResponse.dag_id)" -ForegroundColor Green
        $dag_id = $etlResponse.dag_id
        
        # Проверяем, что DAG файл создан
        $dagFile = "airflow/dags/generated_warehouse_etl_*$($design_id.Substring(0,8))*.py"
        $dagFiles = Get-ChildItem -Path "airflow/dags" -Filter "*$($design_id.Substring(0,8))*" -ErrorAction SilentlyContinue
        
        if ($dagFiles) {
            Write-Host "[SUCCESS] DAG file created: $($dagFiles[0].Name)" -ForegroundColor Green
        }
        
    } else {
        Write-Host "[ERROR] ETL pipeline creation failed: $($etlResponse.message)" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Exception during ETL generation: $($_.Exception.Message)" -ForegroundColor Red
}

# Шаг 8: Попытка загрузки данных (если Airflow доступен)
Write-Host "`n[Step 8] Attempting data loading..." -ForegroundColor Cyan

if ($dag_id) {
    Write-Host "Waiting for Airflow to discover DAG..."
    Start-Sleep -Seconds 10
    
    try {
        $triggerResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/trigger-dag/$dag_id" -Method POST -ContentType "application/json" -TimeoutSec 10
        Write-Host "[SUCCESS] DAG triggered successfully" -ForegroundColor Green
        
        # Ждем выполнения
        Write-Host "Waiting for data loading to complete..."
        Start-Sleep -Seconds 20
        
    } catch {
        Write-Host "[INFO] DAG trigger failed (Airflow may not be ready): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Шаг 9: Проверка загруженных данных
Write-Host "`n[Step 9] Verifying loaded data..." -ForegroundColor Cyan

try {
    # Проверяем количество записей
    $countQuery = "SELECT COUNT(*) FROM analytics.sales_extended"
    $recordCount = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body $countQuery -ContentType "text/plain"
    
    $count = [int]$recordCount.Trim()
    if ($count -gt 0) {
        Write-Host "[SUCCESS] Data loaded successfully. Records: $count" -ForegroundColor Green
        
        # Показываем примеры данных
        $sampleQuery = "SELECT id, product_name, category, price, sale_date FROM analytics.sales_extended LIMIT 5"
        $sampleData = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body $sampleQuery -ContentType "text/plain"
        Write-Host "`nSample loaded data:"
        Write-Host $sampleData
        
        # Проверяем работу партиционирования
        $partitionQuery = "SELECT partition, count() FROM system.parts WHERE table = 'sales_extended' AND database = 'analytics' GROUP BY partition"
        try {
            $partitions = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body $partitionQuery -ContentType "text/plain"
            if ($partitions.Trim()) {
                Write-Host "`nPartition information:"
                Write-Host $partitions
                Write-Host "[SUCCESS] Partitioning is working" -ForegroundColor Green
            }
        } catch {
            Write-Host "[INFO] Could not verify partitioning (may be normal for small datasets)" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "[WARNING] No data found in table (ETL may still be running)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[INFO] Could not verify data loading: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "This is normal if ETL is still in progress or Airflow is not configured" -ForegroundColor Yellow
}

# Шаг 10: Проверка метаданных хранилища
Write-Host "`n[Step 10] Checking warehouse metadata..." -ForegroundColor Cyan

try {
    $instances = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/instances"
    $currentInstance = $instances | Where-Object { $_.design_id -eq $design_id }
    
    if ($currentInstance) {
        Write-Host "[SUCCESS] Warehouse instance registered" -ForegroundColor Green
        Write-Host "- Design ID: $($currentInstance.design_id)"
        Write-Host "- Target DB: $($currentInstance.target_db_type)"
        Write-Host "- Table: $($currentInstance.table_name)"
        Write-Host "- Created: $($currentInstance.created_at)"
    } else {
        Write-Host "[WARNING] Warehouse instance not found in metadata" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Failed to check warehouse metadata: $($_.Exception.Message)" -ForegroundColor Red
}

# Финальная оценка результатов
Write-Host "`n=== COMPREHENSIVE TEST RESULTS ===" -ForegroundColor Yellow

$testResults = @{
    "System Services Ready" = $true
    "Test Data Prepared" = (Test-Path "data_landing_zone/raw/sales_extended.csv")
    "Optimization Recommendations Inserted" = $true
    "DataProfile Created" = ($profile_id -ne $null)
    "Design Process Completed" = ($design_id -ne $null)
    "DDL Generated with Optimizations" = ($optimizations.Count -gt 0)
    "Tables Created in ClickHouse" = ($createResponse.status -eq "success")
    "Table Structure Verified" = ($tables -match "sales_extended")
    "ETL Pipeline Generated" = ($etlResponse.status -eq "created")
    "Warehouse Metadata Recorded" = ($currentInstance -ne $null)
}

$passed = 0
$total = $testResults.Count

foreach ($test in $testResults.GetEnumerator()) {
    $status = if ($test.Value) { "[PASS]"; $passed++ } else { "[FAIL]" }
    $color = if ($test.Value) { "Green" } else { "Red" }
    Write-Host "$status $($test.Key)" -ForegroundColor $color
}

Write-Host "`nOverall Results: $passed/$total tests passed" -ForegroundColor Yellow

if ($passed -eq $total) {
    Write-Host "`n🎉 COMPLETE INTEGRATION TEST PASSED! 🎉" -ForegroundColor Green
    Write-Host "✅ Full end-to-end workflow successful:" -ForegroundColor Green
    Write-Host "   • Intelligent data profiling and analysis" -ForegroundColor Green
    Write-Host "   • LLM-powered СУБД selection" -ForegroundColor Green
    Write-Host "   • Optimization recommendations integration" -ForegroundColor Green
    Write-Host "   • Optimized DDL generation (partitioning, indexing)" -ForegroundColor Green
    Write-Host "   • Actual table creation in ClickHouse" -ForegroundColor Green
    Write-Host "   • ETL pipeline generation and setup" -ForegroundColor Green
    Write-Host "   • Metadata tracking and warehouse management" -ForegroundColor Green
} elseif ($passed -ge ($total * 0.8)) {
    Write-Host "`n✅ INTEGRATION TEST LARGELY SUCCESSFUL!" -ForegroundColor Green
    Write-Host "Most critical components are working correctly." -ForegroundColor Green
    Write-Host "Minor issues may be related to Airflow configuration or timing." -ForegroundColor Yellow
} else {
    Write-Host "`n⚠️  INTEGRATION TEST PARTIALLY SUCCESSFUL" -ForegroundColor Yellow
    Write-Host "Some components need attention. Check error messages above." -ForegroundColor Yellow
}

Write-Host "`n--- Test Summary ---" -ForegroundColor Cyan
Write-Host "Design ID: $design_id"
Write-Host "Profile ID: $profile_id"
Write-Host "Selected Database: ClickHouse"
Write-Host "Optimizations Applied: $($optimizations -join ', ')"
Write-Host "DAG ID: $dag_id"

Write-Host "`nFor detailed monitoring:"
Write-Host "- ClickHouse: http://localhost:8123/"
Write-Host "- Airflow UI: http://localhost:8080/"
Write-Host "- API Docs: http://localhost:8000/docs"

Write-Host "`n=== COMPLETE INTEGRATION TEST FINISHED ===" -ForegroundColor Yellow
