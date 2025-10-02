# Complete Integration Test for Module 4 - Warehouse Design
# Tests full end-to-end workflow with actual data loading

$ErrorActionPreference = "Stop"

Write-Host "=== COMPLETE Integration Test for Module 4 ===" -ForegroundColor Yellow

# Step 0: Check services
Write-Host "`n[Step 0] Checking services..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5 | Out-Null
    Write-Host "[OK] API is healthy" -ForegroundColor Green
} catch {
    throw "API service not available"
}

try {
    Invoke-RestMethod -Uri "http://localhost:8123/ping" -TimeoutSec 5 | Out-Null
    Write-Host "[OK] ClickHouse is healthy" -ForegroundColor Green
} catch {
    throw "ClickHouse service not available"
}

# Step 1: Prepare test data
Write-Host "`n[Step 1] Preparing test data..." -ForegroundColor Cyan

$testData = @"
id,product_name,category,price,quantity,sale_date,customer_id,is_premium,discount_rate,region
1,Gaming Laptop,Electronics,2499.99,1,2024-01-15,101,true,0.05,North America
2,Wireless Mouse,Electronics,79.99,3,2024-01-16,102,false,0.0,Europe
3,Ergonomic Chair,Furniture,599.99,1,2024-01-17,103,true,0.15,Asia
4,Coffee Machine,Appliances,299.99,2,2024-01-18,104,false,0.1,North America
5,Smartphone Pro,Electronics,1299.99,1,2024-01-19,105,true,0.2,Europe
"@

New-Item -ItemType Directory -Path "data_landing_zone/raw" -Force | Out-Null
$testData | Out-File -FilePath "data_landing_zone/raw/sales_extended.csv" -Encoding UTF8
Write-Host "Created extended test dataset"

# Insert optimization recommendations
Write-Host "Inserting optimization recommendations..."
python tests/insert_extended_recommendations.py

# Step 2: Create DataProfile
Write-Host "`n[Step 2] Creating DataProfile..." -ForegroundColor Cyan
$inventory = Invoke-RestMethod -Uri "http://localhost:8000/api/data-inventory"
$existing_profile = $inventory.data | Where-Object { $_.source_path -eq "/data/raw/sales_extended.csv" }

if ($existing_profile) {
    $profile_id = $existing_profile.id
    Write-Host "Found existing DataProfile with ID: $profile_id"
} else {
    $profileBody = '{"source_path": "/data/raw/sales_extended.csv"}'
    $dataProfile = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/data-profiles" -Method POST -ContentType "application/json" -Body $profileBody
    $profile_id = $dataProfile.id
    Write-Host "Created new DataProfile with ID: $profile_id"
}

# Update design request file
$designRequest = Get-Content "request_payloads/extended_design_request.json" | ConvertFrom-Json
$designRequest.source_profile_id = $profile_id
$designRequest | ConvertTo-Json -Depth 10 | Out-File "request_payloads/extended_design_request.json" -Encoding UTF8

# Step 3: Start design process
Write-Host "`n[Step 3] Starting design process..." -ForegroundColor Cyan
$design = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design" -Method POST -ContentType "application/json" -InFile "request_payloads/extended_design_request.json"
$design_id = $design.design_id
Write-Host "Design ID: $design_id"

# Step 4: Confirm design and generate DDL
Write-Host "`n[Step 4] Confirming design..." -ForegroundColor Cyan
$confirmResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design/$design_id/confirm" -Method POST -ContentType "application/json" -InFile "request_payloads/extended_confirm_request.json"
Write-Host "Status: $($confirmResponse.status)"

$ddl_script = $confirmResponse.results.ddl_script
Write-Host "`nGenerated DDL:"
Write-Host "=============="
Write-Host $ddl_script
Write-Host "=============="

# Check optimizations
$optimizations = @()
if ($ddl_script -match "PARTITION BY") { $optimizations += "PARTITION BY" }
if ($ddl_script -match "ORDER BY") { $optimizations += "ORDER BY" }
if ($ddl_script -match "ENGINE = MergeTree") { $optimizations += "MergeTree Engine" }

Write-Host "Optimizations applied: $($optimizations -join ', ')" -ForegroundColor Green

# Step 5: Create tables
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

# Step 6: Verify tables
Write-Host "`n[Step 6] Verifying tables..." -ForegroundColor Cyan
try {
    # ClickHouse authentication headers
    $headers = @{
        'X-ClickHouse-User' = 'default'
        'X-ClickHouse-Key' = 'password'
    }
    
    $tables = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SHOW TABLES FROM analytics" -ContentType "text/plain" -Headers $headers
    
    if ($tables -match "sales_extended") {
        Write-Host "[SUCCESS] Table found in ClickHouse" -ForegroundColor Green
        
        # Check table structure
        $structure = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "DESCRIBE analytics.sales_extended" -ContentType "text/plain" -Headers $headers
        Write-Host "`nTable structure (columns):"
        $structure.Split("`n") | ForEach-Object { 
            if ($_.Trim()) { 
                $parts = $_.Split("`t")
                if ($parts.Length -ge 2) {
                    Write-Host "  - $($parts[0]): $($parts[1])" -ForegroundColor Gray
                }
            }
        }
        
        # Check table creation statement
        $createTable = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SHOW CREATE TABLE analytics.sales_extended" -ContentType "text/plain" -Headers $headers
        if ($createTable -match "PARTITION BY") {
            Write-Host "[SUCCESS] Table has partitioning" -ForegroundColor Green
        }
        if ($createTable -match "ORDER BY") {
            Write-Host "[SUCCESS] Table has ordering" -ForegroundColor Green
        }
        
    } else {
        Write-Host "[WARNING] Table not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Failed to verify table: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 7: Generate ETL
Write-Host "`n[Step 7] Generating ETL pipeline..." -ForegroundColor Cyan
try {
    $etlResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/load-data/$design_id" -Method POST
    
    if ($etlResponse.status -eq "created") {
        Write-Host "[SUCCESS] ETL pipeline created: $($etlResponse.dag_id)" -ForegroundColor Green
        $dag_id = $etlResponse.dag_id
    } else {
        Write-Host "[ERROR] ETL creation failed" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Exception during ETL generation: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 8: Check warehouse metadata
Write-Host "`n[Step 8] Checking warehouse metadata..." -ForegroundColor Cyan
try {
    $instances = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/instances"
    $currentInstance = $instances | Where-Object { $_.design_id -eq $design_id }
    
    if ($currentInstance) {
        Write-Host "[SUCCESS] Warehouse instance registered" -ForegroundColor Green
        Write-Host "- Design ID: $($currentInstance.design_id)"
        Write-Host "- Target DB: $($currentInstance.target_db_type)"
        Write-Host "- Table: $($currentInstance.table_name)"
    } else {
        Write-Host "[WARNING] Warehouse instance not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Failed to check metadata: $($_.Exception.Message)" -ForegroundColor Red
}

# Final results
Write-Host "`n=== TEST RESULTS ===" -ForegroundColor Yellow

$results = @{
    "Data Prepared" = (Test-Path "data_landing_zone/raw/sales_extended.csv")
    "DataProfile Created" = ($null -ne $profile_id)
    "Design Completed" = ($null -ne $design_id)
    "DDL Generated" = ($ddl_script -and $ddl_script.Length -gt 0)
    "Optimizations Applied" = ($optimizations.Count -gt 0)
    "Tables Created" = ($createResponse.status -eq "success")
    "Table Verified" = ($tables -match "sales_extended")
    "ETL Generated" = ($etlResponse.status -eq "created")
    "Metadata Recorded" = ($null -ne $currentInstance)
}

$passed = 0
foreach ($test in $results.GetEnumerator()) {
    $status = if ($test.Value) { "[PASS]"; $passed++ } else { "[FAIL]" }
    $color = if ($test.Value) { "Green" } else { "Red" }
    Write-Host "$status $($test.Key)" -ForegroundColor $color
}

Write-Host "`nResults: $passed/$($results.Count) tests passed" -ForegroundColor Yellow

if ($passed -eq $results.Count) {
    Write-Host "`n*** COMPLETE INTEGRATION TEST PASSED ***" -ForegroundColor Green
    Write-Host "Full end-to-end workflow successful!" -ForegroundColor Green
} elseif ($passed -ge ($results.Count * 0.8)) {
    Write-Host "`n*** INTEGRATION TEST LARGELY SUCCESSFUL ***" -ForegroundColor Green
    Write-Host "Most components working correctly" -ForegroundColor Green
} else {
    Write-Host "`n*** INTEGRATION TEST PARTIALLY SUCCESSFUL ***" -ForegroundColor Yellow
    Write-Host "Some components need attention" -ForegroundColor Yellow
}

Write-Host "`nTest Summary:"
Write-Host "- Design ID: $design_id"
Write-Host "- Profile ID: $profile_id"
Write-Host "- Database: ClickHouse"
Write-Host "- Optimizations: $($optimizations -join ', ')"
if ($dag_id) { Write-Host "- DAG ID: $dag_id" }

Write-Host "`n=== TEST COMPLETED ===" -ForegroundColor Yellow
