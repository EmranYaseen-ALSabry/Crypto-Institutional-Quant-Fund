# PowerShell Script: Run Walk-Forward FreqAI Backtest on Futures
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Executing Institutional Backtest: Futures Engine       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

docker compose run --rm freqtrade-futures backtesting `
    --config /freqtrade/user_data/config_futures.json `
    --strategy InstitutionalDualStrategy `
    --freqaimodel LightGBMRegressor `
    --timerange 20260916-20261101
