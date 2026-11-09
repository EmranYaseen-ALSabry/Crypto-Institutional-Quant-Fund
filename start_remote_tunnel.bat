@echo off
title AI Quant Fund - Remote Access Tunnel (Cloudflare)
echo ===================================================================
echo   Starting Secure Remote Cloudflare Tunnel for Port 5000...
echo   AI Quant Fund Command Center
echo ===================================================================
echo.

if not exist "%~dp0scratch\cloudflared.exe" (
    echo [ERROR] cloudflared.exe not found in scratch folder!
    pause
    exit /b 1
)

echo Connecting to Cloudflare global network...
"%~dp0scratch\cloudflared.exe" tunnel --url http://localhost:5000
pause
