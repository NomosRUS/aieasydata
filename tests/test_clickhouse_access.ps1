# Test ClickHouse access with proper authentication

Write-Host "Testing ClickHouse access..." -ForegroundColor Cyan

# Method 1: Using Basic Auth headers
try {
    $headers = @{
        'X-ClickHouse-User' = 'default'
        'X-ClickHouse-Key' = 'password'
    }
    
    Write-Host "Method 1: Using X-ClickHouse headers"
    $response = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SELECT 1" -ContentType "text/plain" -Headers $headers
    Write-Host "[SUCCESS] Response: $response" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Method 1 failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Method 2: Using URL parameters
try {
    Write-Host "`nMethod 2: Using URL parameters"
    $url = "http://localhost:8123/?user=default&password=password"
    $response = Invoke-RestMethod -Uri $url -Method POST -Body "SELECT 1" -ContentType "text/plain"
    Write-Host "[SUCCESS] Response: $response" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Method 2 failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Method 3: Check if authentication is actually required
try {
    Write-Host "`nMethod 3: No authentication"
    $response = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SELECT 1" -ContentType "text/plain"
    Write-Host "[SUCCESS] No auth needed. Response: $response" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Method 3 failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test table verification
Write-Host "`nTesting table verification..." -ForegroundColor Cyan

try {
    $headers = @{
        'X-ClickHouse-User' = 'default'
        'X-ClickHouse-Key' = 'password'
    }
    
    # Check if analytics database exists
    $databases = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SHOW DATABASES" -ContentType "text/plain" -Headers $headers
    Write-Host "Available databases:"
    Write-Host $databases
    
    if ($databases -match "analytics") {
        Write-Host "[SUCCESS] Analytics database found" -ForegroundColor Green
        
        # Check tables in analytics
        $tables = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "SHOW TABLES FROM analytics" -ContentType "text/plain" -Headers $headers
        Write-Host "`nTables in analytics:"
        Write-Host $tables
        
        if ($tables -match "sales_extended") {
            Write-Host "[SUCCESS] sales_extended table found" -ForegroundColor Green
            
            # Get table structure
            $structure = Invoke-RestMethod -Uri "http://localhost:8123/" -Method POST -Body "DESCRIBE analytics.sales_extended" -ContentType "text/plain" -Headers $headers
            Write-Host "`nTable structure:"
            Write-Host $structure
        } else {
            Write-Host "[WARNING] sales_extended table not found" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[WARNING] Analytics database not found" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "[ERROR] Table verification failed: $($_.Exception.Message)" -ForegroundColor Red
}
