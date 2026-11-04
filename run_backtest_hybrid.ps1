# PowerShell Script: Run Walk-Forward FreqAI Backtest on Hybrid Model (Isolated)
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   Executing Institutional Backtest: Hybrid Tree+Transformer" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

docker compose run --rm freqtrade-spot backtesting `
    --config /freqtrade/user_data/config_spot_hybrid.json `
    --strategy InstitutionalDualStrategy `
    --freqaimodel HybridTreeTransformer `
    --timerange 20260916-20261101
