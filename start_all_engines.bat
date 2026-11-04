@echo off
echo ==========================================================
echo    Starting Institutional Crypto Quant Fund (Dual Engine)
echo ==========================================================
echo Spot Dashboard:    http://localhost:8080
echo Futures Dashboard: http://localhost:8081
echo User: fund_admin ^| Password: InstitutionalQuant2026!
echo ==========================================================

docker compose up -d
docker compose ps
pause
