# PowerShell Script: Stop all engines
Write-Host "Stopping all Quant Fund containers..." -ForegroundColor Yellow
docker compose down
Write-Host "All containers stopped safely." -ForegroundColor Green
