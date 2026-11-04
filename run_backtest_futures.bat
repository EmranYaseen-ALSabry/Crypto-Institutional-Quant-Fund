@echo off
echo ==========================================================
echo    Executing Institutional Backtest: Futures Engine      
echo ==========================================================

docker compose run --rm freqtrade-futures backtesting --config /freqtrade/user_data/config_futures.json --strategy InstitutionalDualStrategy --freqaimodel LightGBMRegressor --timerange 20260916-20261101

pause
