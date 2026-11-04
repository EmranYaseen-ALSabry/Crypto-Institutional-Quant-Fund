# PowerShell Script: Download Market Data for Spot and Futures
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Downloading Institutional Market Data via Docker       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Download Spot Data (1h and 4h)
Write-Host "`n[1/2] Downloading Spot Data (BTC, ETH, SOL)..." -ForegroundColor Yellow
docker compose run --rm freqtrade-spot download-data `
    --config /freqtrade/user_data/config_spot.json `
    --pairs BTC/USDT ETH/USDT SOL/USDT `
    --timeframes 1h 4h `
    --timerange 20240101-

# 2. Download Futures Data (1h and 4h)
Write-Host "`n[2/2] Downloading Futures Data (BTC, ETH, SOL)..." -ForegroundColor Yellow
docker compose run --rm freqtrade-futures download-data `
    --config /freqtrade/user_data/config_futures.json `
    --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT `
    --timeframes 1h 4h `
    --timerange 20240101-

Write-Host "`nData download complete! Market data saved to user_data/data/" -ForegroundColor Green
