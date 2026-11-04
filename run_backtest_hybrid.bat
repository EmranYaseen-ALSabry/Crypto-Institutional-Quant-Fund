@echo off
echo ==========================================================
echo    Executing Institutional Backtest: Hybrid Tree+Transformer
echo ==========================================================

docker compose run --rm freqtrade-spot backtesting --config /freqtrade/user_data/config_spot_hybrid.json --strategy InstitutionalDualStrategy --freqaimodel HybridTreeTransformer --timerange 20260916-20261101
pause
