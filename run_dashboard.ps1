# Institutional Quant Fund - Dashboard Control Center
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "Starting Institutional Quant Fund Dashboard on http://localhost:5000 ..." -ForegroundColor Green
Write-Host "===============================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $scriptDir

python -m uvicorn dashboard.server:app --host 0.0.0.0 --port 5000
