"""Institutional ML & Alpha Evaluation for 2024 Out-of-Sample Test Period
Supports both Spot and Futures Engines.
"""

import glob
import os
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

def evaluate_engine(engine_name: str, pred_dir: str, data_dir: str, is_futures: bool):
    print("\n" + "=" * 90)
    print(f"   🏛️ EVALUATION REPORT: {engine_name.upper()} ENGINE")
    print(f"   Model: LightGBM Regressor (Walk-Forward Ensemble)")
    print(f"   Evaluation Period: October 1, 2024 - December 31, 2024 (Q4 2024)")
    print("=" * 90)

    coins = ["BTC", "ETH", "SOL"]
    overall_stats = []

    for coin in coins:
        if is_futures:
            true_file = os.path.join(data_dir, f"{coin}_USDT_USDT-1h-futures.feather")
        else:
            true_file = os.path.join(data_dir, f"{coin}_USDT-1h.feather")

        if not os.path.exists(true_file):
            continue

        df_true = pd.read_feather(true_file)
        df_true["date"] = pd.to_datetime(df_true["date"])
        if df_true["date"].dt.tz is not None:
            df_true["date"] = df_true["date"].dt.tz_localize(None)

        # Ground truth 12h future return
        df_true["target_true"] = df_true["close"].shift(-12) / df_true["close"] - 1.0
        df_true["future_price_12h"] = df_true["close"].shift(-12)

        df_true = df_true[(df_true["date"] >= "2024-10-01") & (df_true["date"] <= "2024-12-31")]

        pattern = os.path.join(pred_dir, f"cb_{coin.lower()}_*_prediction.feather")
        pred_files = sorted(glob.glob(pattern))
        if not pred_files:
            continue

        dfs = []
        for pf in pred_files:
            try:
                pdf = pd.read_feather(pf)
                pdf["date"] = pd.to_datetime(pdf["date"])
                if pdf["date"].dt.tz is not None:
                    pdf["date"] = pdf["date"].dt.tz_localize(None)
                if "do_predict" in pdf.columns:
                    pdf = pdf[pdf["do_predict"] == 1]
                dfs.append(pdf)
            except Exception:
                continue

        if not dfs:
            continue

        df_pred = pd.concat(dfs).drop_duplicates(subset=["date"]).sort_values("date")

        cols_pred = ["date", "&-s_close"]
        if "DI_values" in df_pred.columns:
            cols_pred.append("DI_values")

        merged = pd.merge(
            df_true[["date", "close", "future_price_12h", "target_true"]],
            df_pred[cols_pred],
            on="date",
        ).dropna(subset=["&-s_close", "target_true"])

        if len(merged) < 10:
            continue

        merged["pred_sign"] = np.sign(merged["&-s_close"])
        merged["true_sign"] = np.sign(merged["target_true"])
        merged["correct_direction"] = (merged["pred_sign"] == merged["true_sign"]).astype(int)

        acc_overall = merged["correct_direction"].mean() * 100
        conv_05 = merged[merged["&-s_close"].abs() >= 0.005]
        acc_conv_05 = (conv_05["pred_sign"] == conv_05["true_sign"]).mean() * 100 if len(conv_05) > 0 else 0.0
        conv_10 = merged[merged["&-s_close"].abs() >= 0.010]
        acc_conv_10 = (conv_10["pred_sign"] == conv_10["true_sign"]).mean() * 100 if len(conv_10) > 0 else 0.0

        mae = np.abs(merged["&-s_close"] - merged["target_true"]).mean() * 100
        p_corr, _ = pearsonr(merged["&-s_close"], merged["target_true"])
        s_corr, _ = spearmanr(merged["&-s_close"], merged["target_true"])

        m_oct = merged[(merged["date"] >= "2024-10-01") & (merged["date"] < "2024-11-01")]
        m_nov = merged[(merged["date"] >= "2024-11-01") & (merged["date"] < "2024-12-01")]
        m_dec = merged[(merged["date"] >= "2024-12-01") & (merged["date"] <= "2024-12-31")]

        acc_oct = m_oct["correct_direction"].mean() * 100 if len(m_oct) > 0 else 0.0
        acc_nov = m_nov["correct_direction"].mean() * 100 if len(m_nov) > 0 else 0.0
        acc_dec = m_dec["correct_direction"].mean() * 100 if len(m_dec) > 0 else 0.0

        overall_stats.append({
            "Coin": f"{coin}/USDT",
            "Samples": len(merged),
            "HitRate_%": round(acc_overall, 2),
            "Conv_0.5%": round(acc_conv_05, 2),
            "Conv_1.0%": round(acc_conv_10, 2),
            "MAE_%": round(mae, 2),
            "Pearson_r": round(p_corr, 4),
            "Oct_%": round(acc_oct, 2),
            "Nov_%": round(acc_nov, 2),
            "Dec_%": round(acc_dec, 2),
        })

    if overall_stats:
        summary_df = pd.DataFrame(overall_stats)
        print(summary_df.to_string(index=False))

if __name__ == "__main__":
    evaluate_engine(
        "Spot",
        "/freqtrade/user_data/models/spot_quant_model/backtesting_predictions",
        "/freqtrade/user_data/data/binance",
        is_futures=False,
    )
    evaluate_engine(
        "Futures",
        "/freqtrade/user_data/models/futures_quant_model/backtesting_predictions",
        "/freqtrade/user_data/data/binance/futures",
        is_futures=True,
    )
