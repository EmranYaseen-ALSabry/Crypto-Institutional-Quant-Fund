"""Evaluate Pure Machine Learning Prediction Accuracy (Ground Truth vs Model Predictions).

This script bypasses trading strategy mechanics (stop-loss, trailing-stop, fees)
and evaluates ONLY the mathematical forecasting capability of the AI model on unseen test data.
"""

import glob
import os
import numpy as np
import pandas as pd

COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "NEAR", "SUI", "LINK"]
PRED_DIR = "/freqtrade/user_data/models/futures_quant_model/backtesting_predictions"
DATA_DIR = "/freqtrade/user_data/data/binance/futures"

print("=" * 80)
print("  PURE MACHINE LEARNING ACCURACY EVALUATION (UNSEEN DATA GROUND TRUTH)")
print("=" * 80)

overall_stats = []

for coin in COINS:
    true_file = os.path.join(DATA_DIR, f"{coin}_USDT_USDT-1h-futures.feather")
    if not os.path.exists(true_file):
        continue

    # 1. Load actual real prices and compute true 12-hour future return
    df_true = pd.read_feather(true_file)
    df_true["date"] = pd.to_datetime(df_true["date"])
    # True outcome after 12 candles
    df_true["target_true"] = df_true["close"].shift(-12) / df_true["close"] - 1.0
    df_true["future_price_12h"] = df_true["close"].shift(-12)

    # 2. Load model predictions generated during out-of-sample backtest
    pattern = os.path.join(PRED_DIR, f"cb_{coin.lower()}_*_prediction.feather")
    pred_files = sorted(glob.glob(pattern))

    if not pred_files:
        continue

    dfs = []
    for pf in pred_files:
        try:
            pdf = pd.read_feather(pf)
            pdf["date"] = pd.to_datetime(pdf["date"])
            # Only candles where model actually produced an out-of-sample prediction
            if "do_predict" in pdf.columns:
                pdf = pdf[pdf["do_predict"] == 1]
            dfs.append(pdf)
        except Exception:
            continue

    if not dfs:
        continue

    df_pred = pd.concat(dfs).drop_duplicates(subset=["date"]).sort_values("date")

    # 3. Merge ground truth with AI prediction on exact timestamps
    merged = pd.merge(
        df_true[["date", "close", "future_price_12h", "target_true"]],
        df_pred[["date", "&-s_close", "DI_values"]],
        on="date",
    ).dropna()

    if len(merged) < 10:
        continue

    # Evaluation Metrics
    merged["pred_sign"] = np.sign(merged["&-s_close"])
    merged["true_sign"] = np.sign(merged["target_true"])
    merged["correct_direction"] = (merged["pred_sign"] == merged["true_sign"]).astype(int)

    # When the model has conviction (> 0.5% expected move)
    conviction = merged[merged["&-s_close"].abs() >= 0.005]
    conv_acc = (conviction["pred_sign"] == conviction["true_sign"]).mean() * 100 if len(conviction) > 0 else 0.0

    acc = merged["correct_direction"].mean() * 100
    mae = np.abs(merged["&-s_close"] - merged["target_true"]).mean() * 100
    corr = merged["&-s_close"].corr(merged["target_true"])

    overall_stats.append({
        "Coin": coin,
        "Samples": len(merged),
        "Directional_Accuracy": acc,
        "Conviction_Accuracy": conv_acc,
        "Conviction_Samples": len(conviction),
        "MAE_%": mae,
        "Correlation": corr,
    })

    print(f"\n[+] {coin}/USDT:")
    print(f"    - Unseen Evaluated Candles: {len(merged)}")
    print(f"    - Pure Directional Accuracy: {acc:.2f}% (Hit direction {merged['correct_direction'].sum()}/{len(merged)})")
    print(f"    - High Conviction Accuracy (|Pred| >= 0.5%): {conv_acc:.2f}% ({len(conviction)} candles)")
    print(f"    - Mean Absolute Error: {mae:.2f}%")
    print(f"    - Correlation (Prediction vs Ground Truth): {corr:.4f}")

    # Print 3 recent sample predictions vs reality
    print("    - Recent Ground Truth vs AI Forecast:")
    for _, row in merged.tail(3).iterrows():
        status = "CORRECT [OK]" if row["correct_direction"] == 1 else "WRONG [X]"
        print(f"      {row['date'].strftime('%Y-%m-%d %H:%M')}: Current=${row['close']:,.2f} | Real 12h=${row['future_price_12h']:,.2f} ({row['target_true']*100:+.2f}%) | AI Pred={row['&-s_close']*100:+.2f}% -> {status}")

print("\n" + "=" * 80)
print("  OVERALL LEAGUE TABLE (SORTED BY DIRECTIONAL ACCURACY)")
print("=" * 80)
if overall_stats:
    summary_df = pd.DataFrame(overall_stats).sort_values("Directional_Accuracy", ascending=False)
    print(summary_df.to_string(index=False))
