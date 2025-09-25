# Integration Test for Module 4 - HDFS Target

$ErrorActionPreference = "Stop"

Write-Host "=== HDFS Integration Test for Module 4 ===" -ForegroundColor Yellow

# Step 0: Check services
Write-Host "`n[Step 0] Checking services..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5 | Out-Null
    Write-Host "[OK] API is healthy" -ForegroundColor Green
} catch {
    throw "API service not available"
}

try {
    Invoke-RestMethod -Uri "http://localhost:9870/" -TimeoutSec 5 | Out-Null
    Write-Host "[OK] HDFS NameNode is healthy" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] HDFS NameNode may not be ready" -ForegroundColor Yellow
}

# Step 1: Prepare HDFS-specific data and recommendations
Write-Host "`n[Step 1] Preparing HDFS test data..." -ForegroundColor Cyan
Write-Host "Inserting HDFS optimization recommendations..."
python tests/insert_hdfs_recommendations.py

# Step 2: Create DataProfile for HDFS dataset
Write-Host "`n[Step 2] Creating DataProfile for HDFS dataset..." -ForegroundColor Cyan
$inventory = Invoke-RestMethod -Uri "http://localhost:8000/api/data-inventory"
$existing_profile = $inventory.data | Where-Object { $_.source_path -eq "/data/raw/sales_hdfs.csv" }

if ($existing_profile) {
    $profile_id = $existing_profile.id
    Write-Host "Found existing DataProfile with ID: $profile_id"
} else {
    $profileBody = '{"source_path": "/data/raw/sales_hdfs.csv"}'
    $dataProfile = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/data-profiles" -Method POST -ContentType "application/json" -Body $profileBody
    $profile_id = $dataProfile.id
    Write-Host "Created new DataProfile with ID: $profile_id"
}

Write-Host "DataProfile columns: $($dataProfile.columns.Count)" -ForegroundColor Gray

# Step 3: Create design request for HDFS (Big Data scenario)
Write-Host "`n[Step 3] Starting HDFS design process..." -ForegroundColor Cyan

# Update request file with correct profile_id
$designRequest = Get-Content "request_payloads/hdfs_design_request.json" | ConvertFrom-Json
$designRequest.source_profile_id = $profile_id
$designRequest | ConvertTo-Json -Depth 10 | Out-File "request_payloads/hdfs_design_request.json" -Encoding UTF8

$design = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design" -Method POST -ContentType "application/json" -InFile "request_payloads/hdfs_design_request.json"
$design_id = $design.design_id
Write-Host "Design ID: $design_id"

# Step 4: Confirm HDFS selection
Write-Host "`n[Step 4] Confirming HDFS selection..." -ForegroundColor Cyan
$confirmResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design/$design_id/confirm" -Method POST -ContentType "application/json" -InFile "request_payloads/hdfs_confirm_request.json"
Write-Host "Status: $($confirmResponse.status)"

$ddl_script = $confirmResponse.results.ddl_script
Write-Host "`nGenerated HDFS DDL:"
Write-Host "=================="
Write-Host $ddl_script
Write-Host "=================="

# Check HDFS-specific optimizations
$optimizations = @()
if ($ddl_script -match "PARTITION") { $optimizations += "PARTITIONING" }
if ($ddl_script -match "parquet") { $optimizations += "PARQUET_FORMAT" }
if ($ddl_script -match "snappy") { $optimizations += "COMPRESSION" }
if ($ddl_script -match "HDFS") { $optimizations += "HDFS_STRUCTURE" }

Write-Host "HDFS optimizations applied: $($optimizations -join ', ')" -ForegroundColor Green

# Step 5: Create directories in HDFS
Write-Host "`n[Step 5] Creating directories in HDFS..." -ForegroundColor Cyan
try {
    $createResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/create/$design_id" -Method POST
    
    if ($createResponse.status -eq "success") {
        Write-Host "[SUCCESS] Directories created in HDFS" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Directory creation failed: $($createResponse.message)" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Exception during directory creation: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 6: Verify HDFS directories
Write-Host "`n[Step 6] Verifying HDFS directories..." -ForegroundColor Cyan
try {
    # Check HDFS directories through WebHDFS API
    $hdfsUrl = "http://localhost:9870/webhdfs/v1/warehouse?op=LISTSTATUS&user.name=root"
    $hdfsResponse = Invoke-RestMethod -Uri $hdfsUrl -TimeoutSec 10
    
    if ($hdfsResponse.FileStatuses.FileStatus) {
        Write-Host "[SUCCESS] HDFS warehouse directory accessible" -ForegroundColor Green
        
        $directories = $hdfsResponse.FileStatuses.FileStatus | Where-Object { $_.type -eq "DIRECTORY" }
        if ($directories) {
            Write-Host "HDFS directories found:"
            foreach ($dir in $directories) {
                Write-Host "  - $($dir.pathSuffix)" -ForegroundColor Gray
            }
        }
        
        # Look for sales_hdfs directory
        $salesDir = $directories | Where-Object { $_.pathSuffix -like "*sales_hdfs*" }
        if ($salesDir) {
            Write-Host "[SUCCESS] Sales HDFS directory found: $($salesDir.pathSuffix)" -ForegroundColor Green
        }
    } else {
        Write-Host "[WARNING] No directories found in HDFS warehouse" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "[WARNING] Failed to verify HDFS directories: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "This may be normal if HDFS is not fully initialized" -ForegroundColor Gray
}

# Step 7: Generate ETL for HDFS
Write-Host "`n[Step 7] Generating HDFS ETL pipeline..." -ForegroundColor Cyan
try {
    $etlResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/load-data/$design_id" -Method POST
    
    if ($etlResponse.status -eq "created") {
        Write-Host "[SUCCESS] HDFS ETL pipeline created: $($etlResponse.dag_id)" -ForegroundColor Green
        $dag_id = $etlResponse.dag_id
    } else {
        Write-Host "[ERROR] ETL creation failed" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Exception during ETL generation: $($_.Exception.Message)" -ForegroundColor Red
}

# Final results
Write-Host "`n=== HDFS TEST RESULTS ===" -ForegroundColor Yellow

$results = @{
    "HDFS Data Prepared" = (Test-Path "data_landing_zone/raw/sales_hdfs.csv")
    "DataProfile Created" = ($null -ne $profile_id)
    "Design Completed" = ($null -ne $design_id)
    "HDFS DDL Generated" = ($ddl_script -and $ddl_script.Length -gt 0)
    "HDFS Optimizations Applied" = ($optimizations.Count -gt 0)
    "HDFS Directories Created" = ($createResponse.status -eq "success")
    "HDFS ETL Generated" = ($etlResponse.status -eq "created")
}

$passed = 0
foreach ($test in $results.GetEnumerator()) {
    $status = if ($test.Value) { "[PASS]"; $passed++ } else { "[FAIL]" }
    $color = if ($test.Value) { "Green" } else { "Red" }
    Write-Host "$status $($test.Key)" -ForegroundColor $color
}

Write-Host "`nHDFS Results: $passed/$($results.Count) tests passed" -ForegroundColor Yellow

if ($passed -eq $results.Count) {
    Write-Host "`n*** HDFS INTEGRATION TEST PASSED ***" -ForegroundColor Green
} else {
    Write-Host "`n*** HDFS INTEGRATION TEST PARTIALLY PASSED ***" -ForegroundColor Yellow
}

Write-Host "`nHDFS Test Summary:"
Write-Host "- Design ID: $design_id"
Write-Host "- Profile ID: $profile_id"
Write-Host "- Target Database: HDFS"
Write-Host "- Optimizations: $($optimizations -join ', ')"
if ($dag_id) { Write-Host "- DAG ID: $dag_id" }

Write-Host "`n=== HDFS TEST COMPLETED ===" -ForegroundColor Yellow
