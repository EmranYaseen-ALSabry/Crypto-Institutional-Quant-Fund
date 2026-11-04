@echo off
echo ==========================================================
echo    Executing Institutional Backtest: Spot Engine         
echo ==========================================================

docker compose run --rm freqtrade-spot backtesting --config /freqtrade/user_data/config_spot.json --strategy InstitutionalDualStrategy --freqaimodel LightGBMRegressor --timerange 20260916-20261101

pause
