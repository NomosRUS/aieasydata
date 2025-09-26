# ==============================================================================
# ╨Ш╨╜╤В╨╡╨│╤А╨░╤Ж╨╕╨╛╨╜╨╜╤Л╨╣ ╤В╨╡╤Б╤В ╨┤╨╗╤П ╨Ь╨╛╨┤╤Г╨╗╤П 4: ╨Я╤А╨╛╨╡╨║╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╨╡ ╨е╤А╨░╨╜╨╕╨╗╨╕╤Й
# ==============================================================================

# ╨Ю╤Б╤В╨░╨╜╨░╨▓╨╗╨╕╨▓╨░╨╡╨╝ ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨╕╨╡ ╨┐╤А╨╕ ╨┐╨╡╤А╨▓╨╛╨╣ ╨╛╤И╨╕╨▒╨║╨╡
$ErrorActionPreference = "Stop"

Write-Host "--- Starting Integration Test for Module 4 ---" -ForegroundColor Yellow

# --- ╨и╨░╨│ 1: ╨Я╨╛╨┤╨│╨╛╤В╨╛╨▓╨║╨░ ---
# ╨г╨▒╨╡╨┤╨╕╨╝╤Б╤П, ╤З╤В╨╛ .env ╤Д╨░╨╣╨╗ ╤Б╤Г╤Й╨╡╤Б╤В╨▓╤Г╨╡╤В, ╨╕╨╜╨░╤З╨╡ ╤Б╨║╤А╨╕╨┐╤В ╨┐╨╛╨┤╨│╨╛╤В╨╛╨▓╨║╨╕ ╤Г╨┐╨░╨┤╨╡╤В
if (-not (Test-Path ".env")) {
    Write-Host "'.env' file not found. Copying from '.env.example'..."
    Copy-Item .env.example .env -Force
}

# ╨Т╤Л╨┐╨╛╨╗╨╜╤П╨╡╨╝ Python-╤Б╨║╤А╨╕╨┐╤В ╨┤╨╗╤П ╨▓╤Б╤В╨░╨▓╨║╨╕ ╤В╨╡╤Б╤В╨╛╨▓╨╛╨╣ ╤А╨╡╨║╨╛╨╝╨╡╨╜╨┤╨░╤Ж╨╕╨╕ ╨▓ ╨С╨Ф
Write-Host "`n[Step 1] Preparing test data: Inserting optimization recommendation..." -ForegroundColor Cyan
python tests/insert_test_recommendation.py

Start-Sleep -Seconds 2
# --- ╨и╨░╨│ 2: ╨б╨╛╨╖╨┤╨░╨╜╨╕╨╡ ╨┐╤А╨╛╤Д╨╕╨╗╤П ╨┤╨░╨╜╨╜╤Л╤Е ---
Write-Host "`n[Step 2] Finding or creating a DataProfile for '/data/raw/sales.csv'..." -ForegroundColor Cyan
$profile_id = $null
$inventory = Invoke-RestMethod -Uri "http://localhost:8000/api/data-inventory"
$existing_profile = $inventory.data | Where-Object { $_.source_path -eq "/data/raw/sales.csv" }

if ($existing_profile) {
    $profile_id = $existing_profile.id
    Write-Host "Found existing DataProfile with ID: $profile_id"
} else {
    $profileBody = @{ source_path = "/data/raw/sales.csv" } | ConvertTo-Json
    $profile = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/data-profiles" -Method POST -ContentType "application/json" -Body $profileBody
    $profile_id = $profile.id
    Write-Host "Created new DataProfile with ID: $profile_id"
}

# --- ╨и╨░╨│ 3: ╨Ч╨░╨┐╤Г╤Б╨║ ╨┐╤А╨╛╤Ж╨╡╤Б╤Б╨░ ╨┐╤А╨╛╨╡╨║╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╤П ---
Write-Host "`n[Step 3] Starting a new warehouse design process..." -ForegroundColor Cyan
$designBody = Get-Content -Path "request_payloads/design_request.json" -Encoding Utf8 -Raw | ConvertFrom-Json
$designBody.source_profile_id = $profile_id
$designBodyJson = $designBody | ConvertTo-Json
$design = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design" -Method POST -ContentType "application/json" -Body $designBodyJson
$design_id = $design.design_id
Write-Host "Started Design Process. New Design ID: $design_id"

# --- ╨и╨░╨│ 4: ╨Я╨╛╨┤╤В╨▓╨╡╤А╨╢╨┤╨╡╨╜╨╕╨╡ ╨╕ ╨┐╨╛╨╗╤Г╤З╨╡╨╜╨╕╨╡ DDL ---
Write-Host "`n[Step 4] Confirming design and fetching the generated DDL..." -ForegroundColor Cyan
$confirmResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/warehouse/design/$design_id/confirm" -Method POST -ContentType "application/json" -InFile "request_payloads/confirm_request.json"
$ddl_script = $confirmResponse.results.ddl_script
Write-Host "Design Confirmed. DDL script received."

# --- ╨и╨░╨│ 5: ╨Я╤А╨╛╨▓╨╡╤А╨║╨░ ╤А╨╡╨╖╤Г╨╗╤М╤В╨░╤В╨░ ---
Write-Host "`n[Step 5] Verifying DDL script for optimization clauses..." -ForegroundColor Cyan
if ($ddl_script -match "PARTITION BY") {
    Write-Host "[SUCCESS] The DDL script contains the expected 'PARTITION BY' clause." -ForegroundColor Green
} else {
    Write-Host "[FAILURE] The DDL script is missing the 'PARTITION BY' clause." -ForegroundColor Red
    Write-Host "Received DDL:"
    Write-Host $ddl_script
    # ╨Т╤Л╨╖╤Л╨▓╨░╨╡╨╝ ╨╛╤И╨╕╨▒╨║╤Г, ╤З╤В╨╛╨▒╤Л ╨╛╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤М ╤Б╨║╤А╨╕╨┐╤В ╨╕ ╨┐╨╛╨║╨░╨╖╨░╤В╤М ╨┐╤А╨╛╨▒╨╗╨╡╨╝╤Г
    throw "Test Failed: DDL optimization verification failed."
}

Write-Host "`n--- Integration Test for Module 4 PASSED ---" -ForegroundColor Green
