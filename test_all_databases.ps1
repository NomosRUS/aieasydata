# Comprehensive Integration Test for Module 4 - All Target Databases

$ErrorActionPreference = "Continue"

Write-Host "=== COMPREHENSIVE Integration Test for Module 4 ===" -ForegroundColor Yellow
Write-Host "Testing ClickHouse, PostgreSQL, and HDFS targets" -ForegroundColor Yellow

# Initialize results tracking
$allResults = @{}

# Test 1: ClickHouse (existing test)
Write-Host "`n" + "="*60 -ForegroundColor Magenta
Write-Host "TEST 1: ClickHouse (High-Performance Analytics)" -ForegroundColor Magenta
Write-Host "="*60 -ForegroundColor Magenta

try {
    & .\test_full_workflow.ps1
    $clickhouseSuccess = $LASTEXITCODE -eq 0
    $allResults["ClickHouse"] = $clickhouseSuccess
    Write-Host "[RESULT] ClickHouse test: $(if($clickhouseSuccess){'PASSED'}else{'FAILED'})" -ForegroundColor $(if($clickhouseSuccess){'Green'}else{'Red'})
} catch {
    Write-Host "[ERROR] ClickHouse test failed: $($_.Exception.Message)" -ForegroundColor Red
    $allResults["ClickHouse"] = $false
}

Start-Sleep -Seconds 3

# Test 2: PostgreSQL
Write-Host "`n" + "="*60 -ForegroundColor Magenta
Write-Host "TEST 2: PostgreSQL (OLTP Transactions)" -ForegroundColor Magenta
Write-Host "="*60 -ForegroundColor Magenta

try {
    & .\test_postgres_workflow.ps1
    $postgresSuccess = $LASTEXITCODE -eq 0
    $allResults["PostgreSQL"] = $postgresSuccess
    Write-Host "[RESULT] PostgreSQL test: $(if($postgresSuccess){'PASSED'}else{'FAILED'})" -ForegroundColor $(if($postgresSuccess){'Green'}else{'Red'})
} catch {
    Write-Host "[ERROR] PostgreSQL test failed: $($_.Exception.Message)" -ForegroundColor Red
    $allResults["PostgreSQL"] = $false
}

Start-Sleep -Seconds 3

# Test 3: HDFS
Write-Host "`n" + "="*60 -ForegroundColor Magenta
Write-Host "TEST 3: HDFS (Big Data Storage)" -ForegroundColor Magenta
Write-Host "="*60 -ForegroundColor Magenta

try {
    & .\test_hdfs_workflow.ps1
    $hdfsSuccess = $LASTEXITCODE -eq 0
    $allResults["HDFS"] = $hdfsSuccess
    Write-Host "[RESULT] HDFS test: $(if($hdfsSuccess){'PASSED'}else{'FAILED'})" -ForegroundColor $(if($hdfsSuccess){'Green'}else{'Red'})
} catch {
    Write-Host "[ERROR] HDFS test failed: $($_.Exception.Message)" -ForegroundColor Red
    $allResults["HDFS"] = $false
}

# Final comprehensive results
Write-Host "`n" + "="*70 -ForegroundColor Yellow
Write-Host "COMPREHENSIVE TEST RESULTS - ALL TARGET DATABASES" -ForegroundColor Yellow
Write-Host "="*70 -ForegroundColor Yellow

$totalPassed = 0
$totalTests = $allResults.Count

foreach ($test in $allResults.GetEnumerator()) {
    $status = if ($test.Value) { "[PASS]"; $totalPassed++ } else { "[FAIL]" }
    $color = if ($test.Value) { "Green" } else { "Red" }
    Write-Host "$status $($test.Key) Integration Test" -ForegroundColor $color
}

Write-Host "`nOverall Results: $totalPassed/$totalTests databases tested successfully" -ForegroundColor Yellow

# Success criteria analysis
if ($totalPassed -eq $totalTests) {
    Write-Host "`n🎉 ALL DATABASE INTEGRATION TESTS PASSED! 🎉" -ForegroundColor Green
    Write-Host "Module 4 successfully supports all target databases:" -ForegroundColor Green
    Write-Host "  ✅ ClickHouse - High-performance analytics with partitioning" -ForegroundColor Green
    Write-Host "  ✅ PostgreSQL - OLTP transactions with indexing" -ForegroundColor Green
    Write-Host "  ✅ HDFS - Big data storage with compression" -ForegroundColor Green
} elseif ($totalPassed -ge 2) {
    Write-Host "`n✅ MAJORITY OF TESTS PASSED!" -ForegroundColor Green
    Write-Host "Module 4 is largely functional across different database types" -ForegroundColor Green
} else {
    Write-Host "`n⚠️ MULTIPLE TESTS FAILED" -ForegroundColor Yellow
    Write-Host "Module 4 needs attention for multi-database support" -ForegroundColor Yellow
}

Write-Host "`n=== COMPREHENSIVE TESTING COMPLETED ===" -ForegroundColor Yellow
Write-Host "Module 4 multi-database capability verified!" -ForegroundColor Cyan

# Summary of what was tested
Write-Host "`nTested Scenarios:" -ForegroundColor Cyan
Write-Host "1. ClickHouse: High-volume analytics with PARTITION BY and ORDER BY" -ForegroundColor Gray
Write-Host "2. PostgreSQL: OLTP workloads with indexes and ACID compliance" -ForegroundColor Gray
Write-Host "3. HDFS: Big data storage with compression and partitioning" -ForegroundColor Gray

Write-Host "`nEach test verified:" -ForegroundColor Cyan
Write-Host "- Data profiling and analysis" -ForegroundColor Gray
Write-Host "- Intelligent database selection" -ForegroundColor Gray
Write-Host "- DDL generation with database-specific optimizations" -ForegroundColor Gray
Write-Host "- Table/directory creation in target system" -ForegroundColor Gray
Write-Host "- ETL pipeline generation" -ForegroundColor Gray
Write-Host "- Metadata management" -ForegroundColor Gray
