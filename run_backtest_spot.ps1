# PowerShell Script: Run Walk-Forward FreqAI Backtest on Spot
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Executing Institutional Backtest: Spot Engine          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

docker compose run --rm freqtrade-spot backtesting `
    --config /freqtrade/user_data/config_spot.json `
    --strategy InstitutionalDualStrategy `
    --freqaimodel LightGBMRegressor `
    --timerange 20260916-20261101
