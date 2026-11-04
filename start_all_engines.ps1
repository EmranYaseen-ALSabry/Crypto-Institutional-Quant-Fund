# PowerShell Script: Launch Both Spot and Futures Engines via Docker
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "   Starting Institutional Crypto Quant Fund (Dual Engine) " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Spot Dashboard:    http://localhost:8080" -ForegroundColor Cyan
Write-Host "Futures Dashboard: http://localhost:8081" -ForegroundColor Cyan
Write-Host "User: fund_admin | Password: InstitutionalQuant2026!" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Green

docker compose up -d
docker compose ps
