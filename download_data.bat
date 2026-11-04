@echo off
echo ==========================================================
echo    Downloading Institutional Market Data via Docker      
echo ==========================================================

echo [1/2] Downloading Spot Data (BTC, ETH, SOL)...
docker compose run --rm freqtrade-spot download-data --config /freqtrade/user_data/config_spot.json --pairs BTC/USDT ETH/USDT SOL/USDT --timeframes 1h 4h --timerange 20240101-

echo.
echo [2/2] Downloading Futures Data (BTC, ETH, SOL)...
docker compose run --rm freqtrade-futures download-data --config /freqtrade/user_data/config_futures.json --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT --timeframes 1h 4h --timerange 20240101-

echo.
echo Data download complete!
pause
