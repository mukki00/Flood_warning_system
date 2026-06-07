param(
    [string]$BaseUrl = "http://127.0.0.1:5000"
)

$ErrorActionPreference = "Stop"

function Print-Step($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

Print-Step "1) GET /api/status"
$status = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/status"
$status | ConvertTo-Json -Depth 6

Print-Step "2) POST sample reading"
$payload = @{
    node_id = "flood_node_1"
    water_level_cm = 21.4
    rain_raw = 2890
    soil_moisture_raw = 3010
    temperature_c = 27.8
    humidity_pct = 68.2
    risk_level = "MODERATE"
    timestamp_ms = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
} | ConvertTo-Json

$post = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/sensor-data" -ContentType "application/json" -Body $payload
$post | ConvertTo-Json -Depth 6

Print-Step "3) GET latest reading"
$latest = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/sensor-data/latest"
$latest | ConvertTo-Json -Depth 6

Print-Step "4) GET alerts"
$alerts = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/alerts"
$alerts | ConvertTo-Json -Depth 6

Print-Step "5) GET status (queue/storage/cloud targets)"
$status2 = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/status"
$status2 | ConvertTo-Json -Depth 8

Write-Host "`nOffline check complete." -ForegroundColor Green
Write-Host "Tip: disconnect internet, run this again, then reconnect and verify sync_queue_pending drops over time."
