import json
import shutil
from pathlib import Path

user_data = Path(r"C:\Users\OMRRAN\Desktop\Cource AI\#4- ML\Competitions\trend ai\Crypto-Institutional-Quant-Fund\user_data")

# 1. Restore strategy_settings.json from 200901.bak
shutil.copyfile(
    user_data / "backups" / "strategy_settings_20261030_200901.json.bak",
    user_data / "strategy_settings.json"
)
print("Restored strategy_settings.json successfully.")

# 2. Fix config_spot.json
spot_path = user_data / "config_spot.json"
with open(spot_path, "r", encoding="utf-8") as f:
    spot_cfg = json.load(f)

spot_cfg.setdefault("freqai", {})
spot_cfg["freqai"]["train_period_days"] = 30
spot_cfg["freqai"]["backtest_period_days"] = 7
spot_cfg["freqai"]["live_retrain_hours"] = 12
spot_cfg["freqai"]["expiration_hours"] = 0
spot_cfg["freqai"]["enabled"] = True
spot_cfg["force_entry_enable"] = True

with open(spot_path, "w", encoding="utf-8") as f:
    json.dump(spot_cfg, f, indent=4)
print("Fixed config_spot.json freqai parameters.")

# 3. Fix config_futures.json
fut_path = user_data / "config_futures.json"
with open(fut_path, "r", encoding="utf-8") as f:
    fut_cfg = json.load(f)

fut_cfg.setdefault("freqai", {})
fut_cfg["freqai"]["train_period_days"] = 30
fut_cfg["freqai"]["backtest_period_days"] = 7
fut_cfg["freqai"]["live_retrain_hours"] = 12
fut_cfg["freqai"]["expiration_hours"] = 0
fut_cfg["freqai"]["enabled"] = True
fut_cfg["force_entry_enable"] = True

with open(fut_path, "w", encoding="utf-8") as f:
    json.dump(fut_cfg, f, indent=4)
print("Fixed config_futures.json freqai parameters.")
