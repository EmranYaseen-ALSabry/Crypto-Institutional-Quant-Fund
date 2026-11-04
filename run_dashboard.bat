@echo off
title Institutional Quant Fund - Dashboard Control Center
echo ===============================================================================
echo Starting Institutional Quant Fund Dashboard on http://localhost:5000 ...
echo ===============================================================================
cd /d "%~dp0"
python -m uvicorn dashboard.server:app --host 0.0.0.0 --port 5000
pause
