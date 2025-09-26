# Integration Test for Module 4 - PostgreSQL Target

$ErrorActionPreference = "Stop"

Write-Host "=== PostgreSQL Integration Test for Module 4 ===" -ForegroundColor Yellow

# Step 0: Check services
Write-Host "`n[Step 0] Checking services..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5 | Out-Null
    Write-Host "[OK] API is healthy" -ForegroundColor Green
} catch {
    throw "API service not available"
}

# Step 1: Prepare PostgreSQL-specific data and recommendations
Write-Host "`n[Step 1] Preparing PostgreSQL test data..." -ForegroundColor Cyan
Write-Host "Inserting PostgreSQL optimization recommendations..."
python tests/insert_postgres_recommendations.py

# Step 2: Create DataProfile for PostgreSQL dataset
Write-Host "`n[Step 2] Creating DataProfile for PostgreSQL dataset..." -ForegroundColor Cyan
$inventory = Invoke-RestMethod -Uri "http://localhost:8000/api/data-inventory"
$existing_profile = $inventory.data | Where-Object { $_.source_path -eq "/data/raw/sales_postgres.csv" }

if ($existing_profile) {
    $profile_id = $existing_profile.id
    Write-Host "Found existing DataProfile with ID: $profile_id"
} else {
    $profileBody = '{"source_path": "/data/raw/sales_postgres.csv"}'
    $dataProfile = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/data-profiles" -Method POST -ContentType "application/json" -Body $profileBody
    $profile_id = $dataProfile.id
    Write-Host "Created new DataProfile with ID: $profile_id"
}

Write-Host "DataProfile columns: $($dataProfile.columns.Count)" -ForegroundColor Gray

# Step 3: Create design request for PostgreSQL (OLTP scenario)
Write-Host "`n[Step 3] Starting PostgreSQL design process..." -ForegroundColor Cyan

# Update request file with correct profile_id
$designRequest = Get-Content "request_payloads/postgres_design_request.json" | ConvertFrom-Json
$designRequest.source_profile_id = $profile_id
$designRequest | ConvertTo-Json -Depth 10 | Out-File "request_payloads/postgres_design_request.json" -Encoding UTF8

$design = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design" -Method POST -ContentType "application/json" -InFile "request_payloads/postgres_design_request.json"
$design_id = $design.design_id
Write-Host "Design ID: $design_id"

# Step 4: Confirm PostgreSQL selection
Write-Host "`n[Step 4] Confirming PostgreSQL selection..." -ForegroundColor Cyan
$confirmResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design/$design_id/confirm" -Method POST -ContentType "application/json" -InFile "request_payloads/postgres_confirm_request.json"
Write-Host "Status: $($confirmResponse.status)"

$ddl_script = $confirmResponse.results.ddl_script
Write-Host "`nGenerated PostgreSQL DDL:"
Write-Host "========================"
Write-Host $ddl_script
Write-Host "========================"

# Check PostgreSQL-specific optimizations
$optimizations = @()
if ($ddl_script -match "CREATE INDEX") { $optimizations += "INDEXES" }
if ($ddl_script -match "PARTITION") { $optimizations += "PARTITIONING" }

Write-Host "PostgreSQL optimizations applied: $($optimizations -join ', ')" -ForegroundColor Green

# Step 5: Create tables in PostgreSQL
Write-Host "`n[Step 5] Creating tables in PostgreSQL..." -ForegroundColor Cyan
try {
    $createResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/create/$design_id" -Method POST
    
    if ($createResponse.status -eq "success") {
        Write-Host "[SUCCESS] Tables created in PostgreSQL" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Table creation failed: $($createResponse.message)" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Exception during table creation: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 6: Verify PostgreSQL tables
Write-Host "`n[Step 6] Verifying PostgreSQL tables..." -ForegroundColor Cyan

# Create a separate Python script for verification
$verifyScript = @"
import psycopg2
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()
DATABASE_URL = os.getenv('POSTGRES_DSN').replace('@postgres:', '@localhost:')
result = urlparse(DATABASE_URL)
db_params = {
    'user': result.username,
    'password': result.password,
    'host': result.hostname,
    'port': result.port,
    'dbname': result.path[1:]
}

try:
    with psycopg2.connect(**db_params) as conn:
        with conn.cursor() as cur:
            # Check if analytics schema exists
            cur.execute('SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s', ('analytics',))
            schema_exists = cur.fetchone()
            
            if schema_exists:
                print('[SUCCESS] Analytics schema exists in PostgreSQL')
                
                # Check for sales_postgres table
                cur.execute('SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_name LIKE %s', ('analytics', '%sales_postgres%'))
                tables = cur.fetchall()
                
                if tables:
                    table_name = tables[0][0]
                    print(f'[SUCCESS] Table found: {table_name}')
                    
                    # Get table structure
                    cur.execute('SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position', ('analytics', table_name))
                    columns = cur.fetchall()
                    
                    print('Table structure:')
                    for col_name, col_type in columns:
                        print(f'  - {col_name}: {col_type}')
                    
                    # Check for indexes
                    cur.execute('SELECT indexname FROM pg_indexes WHERE schemaname = %s AND tablename = %s', ('analytics', table_name))
                    indexes = cur.fetchall()
                    
                    if indexes:
                        print('Indexes:')
                        for idx in indexes:
                            print(f'  - {idx[0]}')
                    
                    # Verification success flag
                    print('[VERIFICATION_SUCCESS]')
                else:
                    print('[WARNING] No sales_postgres table found')
            else:
                print('[WARNING] Analytics schema not found')
                
except Exception as e:
    print(f'[ERROR] PostgreSQL verification failed: {e}')
"@

$verifyScript | Out-File -FilePath "temp_verify_postgres.py" -Encoding UTF8

try {
    $verifyOutput = python temp_verify_postgres.py
    Write-Host $verifyOutput
    
    # Check if verification was successful
    if ($verifyOutput -match "\[VERIFICATION_SUCCESS\]") {
        $postgresVerified = $true
        Write-Host "[SUCCESS] PostgreSQL table verification completed" -ForegroundColor Green
    } else {
        $postgresVerified = $false
        Write-Host "[WARNING] PostgreSQL table verification incomplete" -ForegroundColor Yellow
    }
    
    # Clean up
    Remove-Item "temp_verify_postgres.py" -ErrorAction SilentlyContinue
    
} catch {
    Write-Host "[ERROR] Failed to verify PostgreSQL table: $($_.Exception.Message)" -ForegroundColor Red
    $postgresVerified = $false
}

# Step 7: Generate ETL for PostgreSQL
Write-Host "`n[Step 7] Generating PostgreSQL ETL pipeline..." -ForegroundColor Cyan
try {
    $etlResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/load-data/$design_id" -Method POST
    
    if ($etlResponse.status -eq "created") {
        Write-Host "[SUCCESS] PostgreSQL ETL pipeline created: $($etlResponse.dag_id)" -ForegroundColor Green
        $dag_id = $etlResponse.dag_id
    } else {
        Write-Host "[ERROR] ETL creation failed" -ForegroundColor Red
    }
} catch {
    Write-Host "[ERROR] Exception during ETL generation: $($_.Exception.Message)" -ForegroundColor Red
}

# Final results
Write-Host "`n=== PostgreSQL TEST RESULTS ===" -ForegroundColor Yellow

$results = @{
    "PostgreSQL Data Prepared" = (Test-Path "data_landing_zone/raw/sales_postgres.csv")
    "DataProfile Created" = ($null -ne $profile_id)
    "Design Completed" = ($null -ne $design_id)
    "PostgreSQL DDL Generated" = ($ddl_script -and $ddl_script.Length -gt 0)
    "PostgreSQL Optimizations Applied" = ($optimizations.Count -gt 0)
    "PostgreSQL Tables Created" = ($createResponse.status -eq "success")
    "PostgreSQL Tables Verified" = $postgresVerified
    "PostgreSQL ETL Generated" = ($etlResponse.status -eq "created")
}

$passed = 0
foreach ($test in $results.GetEnumerator()) {
    $status = if ($test.Value) { "[PASS]"; $passed++ } else { "[FAIL]" }
    $color = if ($test.Value) { "Green" } else { "Red" }
    Write-Host "$status $($test.Key)" -ForegroundColor $color
}

Write-Host "`nPostgreSQL Results: $passed/$($results.Count) tests passed" -ForegroundColor Yellow

if ($passed -eq $results.Count) {
    Write-Host "`n*** PostgreSQL INTEGRATION TEST PASSED ***" -ForegroundColor Green
} else {
    Write-Host "`n*** PostgreSQL INTEGRATION TEST PARTIALLY PASSED ***" -ForegroundColor Yellow
}

Write-Host "`nPostgreSQL Test Summary:"
Write-Host "- Design ID: $design_id"
Write-Host "- Profile ID: $profile_id"
Write-Host "- Target Database: PostgreSQL"
Write-Host "- Optimizations: $($optimizations -join ', ')"
if ($dag_id) { Write-Host "- DAG ID: $dag_id" }

Write-Host "`n=== PostgreSQL TEST COMPLETED ===" -ForegroundColor Yellow
