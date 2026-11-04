import re
from pathlib import Path

p = Path(r"C:\Users\OMRRAN\Desktop\Cource AI\#4- ML\Competitions\trend ai\Crypto-Institutional-Quant-Fund\dashboard\server.py")
text = p.read_text(encoding="utf-8")

# 1. Enhance save_all_configs with robust deep merge and validation
save_all_target = """@app.post("/api/config/save")
async def save_all_configs(payload: dict):
    \"\"\"
    Atomically saves updated strategy settings and engine configs.
    Creates automated backups before overwriting.
    \"\"\"
    results = {}

    if "strategy_settings" in payload and isinstance(payload["strategy_settings"], dict):
        ok = write_json_atomic(STRATEGY_SETTINGS_PATH, payload["strategy_settings"])
        results["strategy_settings"] = "saved" if ok else "error"

    if "config_spot" in payload and isinstance(payload["config_spot"], dict):
        ok = write_json_atomic(CONFIG_SPOT_PATH, payload["config_spot"])
        results["config_spot"] = "saved" if ok else "error"

    if "config_futures" in payload and isinstance(payload["config_futures"], dict):
        ok = write_json_atomic(CONFIG_FUTURES_PATH, payload["config_futures"])
        results["config_futures"] = "saved" if ok else "error"

    return {
        "status": "success" if all(v == "saved" for v in results.values()) else "partial",
        "results": results,
        "saved_at": datetime.now().isoformat()
    }"""

save_all_replacement = """def sanitize_engine_config(disk_cfg: dict, incoming_cfg: dict) -> dict:
    \"\"\"
    Deep-merges and sanitizes incoming engine config against existing disk config
    to prevent null/NaN values or accidental disabling of dry_run/freqai.
    \"\"\"
    merged = json.loads(json.dumps(disk_cfg))
    
    # Preserve dry_run unless explicitly specified as a boolean
    if "dry_run" in incoming_cfg and isinstance(incoming_cfg["dry_run"], bool):
        merged["dry_run"] = incoming_cfg["dry_run"]
    else:
        merged["dry_run"] = True  # Always fallback to safe dry_run
        
    for k in ["max_open_trades", "tradable_balance_ratio", "dry_run_wallet", "margin_mode"]:
        if k in incoming_cfg and incoming_cfg[k] is not None:
            merged[k] = incoming_cfg[k]
            
    if "stake_amount" in incoming_cfg and incoming_cfg["stake_amount"] is not None:
        merged["stake_amount"] = incoming_cfg["stake_amount"]
        
    # Whitelist
    inc_wl = incoming_cfg.get("exchange", {}).get("pair_whitelist")
    if inc_wl and isinstance(inc_wl, list) and len(inc_wl) > 0:
        merged.setdefault("exchange", {})["pair_whitelist"] = inc_wl
        
    # FreqAI protection
    merged.setdefault("freqai", {})
    inc_freqai = incoming_cfg.get("freqai", {})
    merged["freqai"]["enabled"] = True
    for field, default_val in [("train_period_days", 30), ("backtest_period_days", 7), ("live_retrain_hours", 12), ("expiration_hours", 0)]:
        val = inc_freqai.get(field)
        if isinstance(val, int) and val >= 0:
            merged["freqai"][field] = val
        elif merged["freqai"].get(field) is None or not isinstance(merged["freqai"].get(field), int):
            merged["freqai"][field] = default_val

    # Telegram
    if "telegram" in incoming_cfg and isinstance(incoming_cfg["telegram"], dict):
        merged["telegram"] = incoming_cfg["telegram"]
        
    merged["force_entry_enable"] = True
    return merged


def sanitize_strategy_settings(disk_settings: dict, incoming_settings: dict) -> dict:
    \"\"\"
    Preserves minimal_roi and sr_channels if incoming payload sent empty dicts.
    \"\"\"
    merged = json.loads(json.dumps(disk_settings))
    for root_key in ["ai_model", "risk_management", "indicators"]:
        if root_key in incoming_settings and isinstance(incoming_settings[root_key], dict):
            for sub_k, sub_v in incoming_settings[root_key].items():
                if sub_k == "minimal_roi" and (not sub_v or len(sub_v) == 0):
                    continue  # Keep disk minimal_roi
                merged.setdefault(root_key, {})[sub_k] = sub_v
    return merged


@app.post("/api/config/save")
async def save_all_configs(payload: dict):
    \"\"\"
    Atomically saves updated strategy settings and engine configs with deep sanitization.
    \"\"\"
    results = {}

    if "strategy_settings" in payload and isinstance(payload["strategy_settings"], dict):
        cur_strat = read_json_file(STRATEGY_SETTINGS_PATH)
        safe_strat = sanitize_strategy_settings(cur_strat, payload["strategy_settings"])
        ok = write_json_atomic(STRATEGY_SETTINGS_PATH, safe_strat)
        results["strategy_settings"] = "saved" if ok else "error"

    if "config_spot" in payload and isinstance(payload["config_spot"], dict):
        cur_spot = read_json_file(CONFIG_SPOT_PATH)
        safe_spot = sanitize_engine_config(cur_spot, payload["config_spot"])
        ok = write_json_atomic(CONFIG_SPOT_PATH, safe_spot)
        results["config_spot"] = "saved" if ok else "error"

    if "config_futures" in payload and isinstance(payload["config_futures"], dict):
        cur_fut = read_json_file(CONFIG_FUTURES_PATH)
        safe_fut = sanitize_engine_config(cur_fut, payload["config_futures"])
        ok = write_json_atomic(CONFIG_FUTURES_PATH, safe_fut)
        results["config_futures"] = "saved" if ok else "error"

    return {
        "status": "success" if all(v == "saved" for v in results.values()) else "partial",
        "results": results,
        "saved_at": datetime.now().isoformat()
    }"""

if save_all_target in text:
    text = text.replace(save_all_target, save_all_replacement)
    print("Patched save_all_configs with deep sanitization.")
else:
    print("save_all_target not found.")

# 2. Add reload_config await and retry loop in revitalize_and_enter
revitalize_target = """        # Add to whitelist if needed
        cfg_path = CONFIG_SPOT_PATH if target_engine == 'spot' else CONFIG_FUTURES_PATH
        cfg = read_json_file(cfg_path)
        wl = cfg.get('exchange', {}).get('pair_whitelist', [])
        if entry_pair not in wl:
            wl.append(entry_pair)
            cfg['exchange']['pair_whitelist'] = wl
            write_json_atomic(cfg_path, cfg)
            try:
                requests.post(f'{api_url}/reload_config', auth=API_AUTH, timeout=3.0)
            except Exception:
                pass

        # Execute forceenter
        body = {'pair': entry_pair}
        if target_engine == 'futures':
            is_short = candidate.get('minus_di', 0) > candidate.get('plus_di', 0) and candidate.get('rsi', 50) > 55
            body['side'] = 'short' if is_short else 'long'

        entered_ok = False
        trade_id = None
        error_msg = None
        try:
            fe_r = requests.post(f'{api_url}/forceenter', auth=API_AUTH, json=body, timeout=5.0)
            if fe_r.status_code == 200:
                data = fe_r.json()
                entered_ok = True
                trade_id = data.get('trade_id')
            else:
                error_msg = fe_r.text
        except Exception as e:
            error_msg = str(e)"""

revitalize_replacement = """        # Add to whitelist if needed
        cfg_path = CONFIG_SPOT_PATH if target_engine == 'spot' else CONFIG_FUTURES_PATH
        cfg = read_json_file(cfg_path)
        wl = cfg.get('exchange', {}).get('pair_whitelist', [])
        if entry_pair not in wl:
            wl.append(entry_pair)
            cfg['exchange']['pair_whitelist'] = wl
            write_json_atomic(cfg_path, cfg)
            try:
                requests.post(f'{api_url}/reload_config', auth=API_AUTH, timeout=3.0)
                await asyncio.sleep(2.0)  # Grace period for bot reload
            except Exception:
                pass

        # Execute forceenter with graceful retries
        body = {'pair': entry_pair}
        if target_engine == 'futures':
            is_short = candidate.get('minus_di', 0) > candidate.get('plus_di', 0) and candidate.get('rsi', 50) > 55
            body['side'] = 'short' if is_short else 'long'

        entered_ok = False
        trade_id = None
        error_msg = None
        for attempt in range(4):
            try:
                fe_r = requests.post(f'{api_url}/forceenter', auth=API_AUTH, json=body, timeout=5.0)
                if fe_r.status_code == 200:
                    data = fe_r.json()
                    entered_ok = True
                    trade_id = data.get('trade_id')
                    break
                else:
                    error_msg = fe_r.text
                    if "trader is not running" in error_msg or fe_r.status_code == 503:
                        await asyncio.sleep(1.5)
                        continue
                    break
            except Exception as e:
                error_msg = str(e)
                await asyncio.sleep(1.0)"""

if revitalize_target in text:
    text = text.replace(revitalize_target, revitalize_replacement)
    print("Patched revitalize_and_enter with retry loop.")
else:
    print("revitalize_target not found.")

# 3. Add reload_config await and retry in manual_enter_pair
manual_target = """    if target_pair not in wl:
        wl.append(target_pair)
        cfg['exchange']['pair_whitelist'] = wl
        write_json_atomic(cfg_path, cfg)
        try:
            requests.post(f'{api_url}/reload_config', auth=API_AUTH, timeout=3.0)
        except Exception:
            pass

    body = {'pair': target_pair}
    if engine == 'futures':
        body['side'] = side

    try:
        r = requests.post(f'{api_url}/forceenter', auth=API_AUTH, json=body, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            return {
                'status': 'success',
                'pair': target_pair,
                'engine': engine,
                'side': side,
                'trade_id': data.get('trade_id'),
                'open_rate': data.get('open_rate'),
                'stake_amount': data.get('stake_amount'),
                'message': f'تم تنفيذ أمر الدخول في {target_pair} بنجاح!'
            }
        else:
            return {'status': 'error', 'message': r.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))"""

manual_replacement = """    if target_pair not in wl:
        wl.append(target_pair)
        cfg['exchange']['pair_whitelist'] = wl
        write_json_atomic(cfg_path, cfg)
        try:
            requests.post(f'{api_url}/reload_config', auth=API_AUTH, timeout=3.0)
            await asyncio.sleep(2.0)
        except Exception:
            pass

    body = {'pair': target_pair}
    if engine == 'futures':
        body['side'] = side

    for attempt in range(4):
        try:
            r = requests.post(f'{api_url}/forceenter', auth=API_AUTH, json=body, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                return {
                    'status': 'success',
                    'pair': target_pair,
                    'engine': engine,
                    'side': side,
                    'trade_id': data.get('trade_id'),
                    'open_rate': data.get('open_rate'),
                    'stake_amount': data.get('stake_amount'),
                    'message': f'تم تنفيذ أمر الدخول في {target_pair} بنجاح!'
                }
            else:
                err_text = r.text
                if "trader is not running" in err_text or r.status_code == 503:
                    await asyncio.sleep(1.5)
                    continue
                return {'status': 'error', 'message': err_text}
        except Exception as e:
            if attempt == 3:
                raise HTTPException(status_code=500, detail=str(e))
            await asyncio.sleep(1.0)"""

if manual_target in text:
    text = text.replace(manual_target, manual_replacement)
    print("Patched manual_enter_pair with retry loop.")
else:
    print("manual_target not found.")

p.write_text(text, encoding="utf-8")
