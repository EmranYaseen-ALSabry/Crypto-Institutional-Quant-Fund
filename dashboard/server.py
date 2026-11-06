"""

================================================================================

Institutional Quant Fund - Interactive Web Dashboard & Control Center

================================================================================

Backend Server: FastAPI + Uvicorn

Provides real-time telemetry, configuration management, ADX studio controls,

trade monitoring, and engine orchestration for both Spot & Futures FreqAI engines.

================================================================================

"""



import argparse

import asyncio

import json

import logging

import os

import shutil

import sqlite3

import subprocess

from datetime import datetime

from pathlib import Path

from typing import Any, Dict, List, Optional



import concurrent.futures

import threading

import numpy as np

import requests

from fastapi import FastAPI, HTTPException, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse, JSONResponse

from fastapi.templating import Jinja2Templates



# Setup logging

logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"

)

logger = logging.getLogger("QuantDashboard")



# Project directories

BASE_DIR = Path(__file__).resolve().parent.parent

USER_DATA_DIR = BASE_DIR / "user_data"

CONFIG_SPOT_PATH = USER_DATA_DIR / "config_spot.json"

CONFIG_FUTURES_PATH = USER_DATA_DIR / "config_futures.json"

STRATEGY_SETTINGS_PATH = USER_DATA_DIR / "strategy_settings.json"

BACKUP_DIR = USER_DATA_DIR / "backups"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)



# Engine API credentials

SPOT_API_URL = "http://localhost:8080/api/v1"

FUTURES_API_URL = "http://localhost:8081/api/v1"

API_AUTH = ("fund_admin", "InstitutionalQuant2026!")



app = FastAPI(

    title="Institutional Quant Fund Control Center",

    version="2.0.0",

    description="Unified management dashboard for Spot & Futures AI Trading Engines"

)



app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



templates_dir = Path(__file__).resolve().parent / "templates"

INDEX_HTML_PATH = templates_dir / "index.html"





# =============================================================================

# Helper Utilities

# =============================================================================

def read_json_file(file_path: Path) -> dict:

    if not file_path.exists():

        return {}

    try:

        with open(file_path, "r", encoding="utf-8") as f:

            return json.load(f)

    except Exception as e:

        logger.error(f"Error reading JSON from {file_path}: {e}")

        return {}





def write_json_atomic(file_path: Path, data: dict) -> bool:

    try:

        # Create a backup first

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_file = BACKUP_DIR / f"{file_path.stem}_{timestamp}.json.bak"

        if file_path.exists():

            shutil.copy2(file_path, backup_file)



        # Write to temporary file then atomically replace

        temp_file = file_path.with_suffix(".tmp")

        with open(temp_file, "w", encoding="utf-8") as f:

            json.dump(data, f, indent=4, ensure_ascii=False)

            f.flush()

            os.fsync(f.fileno())

        shutil.move(str(temp_file), str(file_path))

        return True

    except Exception as e:

        logger.error(f"Error atomically writing JSON to {file_path}: {e}")

        return False





def get_container_status(container_name: str) -> dict:

    try:

        cmd = ["docker", "inspect", "--format", "{{.State.Status}}", container_name]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)

        if res.returncode == 0:

            status = res.stdout.strip()

            return {"status": status, "online": status == "running"}

    except Exception as e:

        logger.debug(f"Docker inspect error for {container_name}: {e}")

    return {"status": "offline", "online": False}





# =============================================================================

# API Endpoints

# =============================================================================

@app.get("/", response_class=HTMLResponse)

async def index():

    """Renders the main dashboard interface."""

    if INDEX_HTML_PATH.exists():

        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:

            return HTMLResponse(content=f.read())

    return HTMLResponse(content="<h1>Dashboard HTML template not found</h1>", status_code=404)





@app.get("/api/status")

async def get_system_status():

    """

    Returns live connectivity status, engine health, and balances.

    """

    spot_docker = get_container_status("freqtrade_spot_engine")

    futures_docker = get_container_status("freqtrade_futures_engine")



    spot_api_online = False

    spot_balance = 0.0

    spot_open_trades_count = 0

    try:

        r = requests.get(f"{SPOT_API_URL}/ping", timeout=1.5)

        if r.status_code == 200:

            spot_api_online = True

            bal_r = requests.get(f"{SPOT_API_URL}/balance", auth=API_AUTH, timeout=1.5)

            if bal_r.status_code == 200:

                spot_balance = bal_r.json().get("total", 0.0)

            trades_r = requests.get(f"{SPOT_API_URL}/status", auth=API_AUTH, timeout=1.5)

            if trades_r.status_code == 200:

                spot_open_trades_count = len(trades_r.json())

    except Exception:

        pass



    futures_api_online = False

    futures_balance = 0.0

    futures_open_trades_count = 0

    try:

        r = requests.get(f"{FUTURES_API_URL}/ping", timeout=1.5)

        if r.status_code == 200:

            futures_api_online = True

            bal_r = requests.get(f"{FUTURES_API_URL}/balance", auth=API_AUTH, timeout=1.5)

            if bal_r.status_code == 200:

                futures_balance = bal_r.json().get("total", 0.0)

            trades_r = requests.get(f"{FUTURES_API_URL}/status", auth=API_AUTH, timeout=1.5)

            if trades_r.status_code == 200:

                futures_open_trades_count = len(trades_r.json())

    except Exception:

        pass



    return {

        "timestamp": datetime.now().isoformat(),

        "spot": {

            "docker": spot_docker,

            "api_online": spot_api_online,

            "balance": round(spot_balance, 2),

            "open_trades": spot_open_trades_count,

            "port": 8080

        },

        "futures": {

            "docker": futures_docker,

            "api_online": futures_api_online,

            "balance": round(futures_balance, 2),

            "open_trades": futures_open_trades_count,

            "port": 8081

        }

    }





@app.get("/api/config")

async def get_all_configs():

    """

    Returns current configuration files:

    1. strategy_settings.json

    2. config_spot.json

    3. config_futures.json

    """

    strategy_settings = read_json_file(STRATEGY_SETTINGS_PATH)

    config_spot = read_json_file(CONFIG_SPOT_PATH)

    config_futures = read_json_file(CONFIG_FUTURES_PATH)



    return {

        "strategy_settings": strategy_settings,

        "config_spot": config_spot,

        "config_futures": config_futures

    }





def sanitize_engine_config(disk_cfg: dict, incoming_cfg: dict) -> dict:

    """

    Deep-merges and sanitizes incoming engine config against existing disk config

    to prevent null/NaN values or accidental disabling of dry_run/freqai.

    """

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

    """

    Preserves minimal_roi and sr_channels if incoming payload sent empty dicts.

    """

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

    """

    Atomically saves updated strategy settings and engine configs with deep sanitization.

    """

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

    }





@app.get("/api/trades")

async def get_trades():

    """

    Fetches open and closed trades from both engines (via REST API with SQLite fallback).

    """

    trades_list = []



    # 1. Fetch Spot Trades

    try:

        r = requests.get(f"{SPOT_API_URL}/status", auth=API_AUTH, timeout=2.0)

        if r.status_code == 200:

            for t in r.json():

                trades_list.append({

                    "engine": "Spot",

                    "trade_id": t.get("trade_id"),

                    "pair": t.get("pair"),

                    "side": "SHORT" if t.get("is_short") else "LONG",

                    "open_rate": t.get("open_rate"),

                    "current_rate": t.get("current_rate"),

                    "profit_pct": round(t.get("profit_pct", 0.0), 2),

                    "profit_abs": round(t.get("profit_abs", 0.0), 2),

                    "stake_amount": round(t.get("stake_amount", 0.0), 2),

                    "open_date": t.get("open_date"),

                    "enter_tag": t.get("enter_tag"),

                    "stop_loss_abs": t.get("stop_loss_abs"),

                    "stoploss_dist_pct": round(t.get("stoploss_current_dist_pct", 0.0), 2)

                })

        else:

            raise Exception("Spot API status failed")

    except Exception:

        # Fallback to Spot SQLite

        spot_db = USER_DATA_DIR / "trades_spot.sqlite"

        if spot_db.exists():

            try:

                conn = sqlite3.connect(f"file:{spot_db.resolve()}?mode=ro", uri=True)

                c = conn.cursor()

                rows = c.execute(

                    "SELECT id, pair, open_rate, is_open, fee_open, open_date, enter_tag "

                    "FROM trades WHERE is_open = 1 ORDER BY id DESC"

                ).fetchall()

                for r in rows:

                    trades_list.append({

                        "engine": "Spot (DB)",

                        "trade_id": r[0],

                        "pair": r[1],

                        "side": "LONG",

                        "open_rate": r[2],

                        "current_rate": r[2],

                        "profit_pct": 0.0,

                        "profit_abs": 0.0,

                        "stake_amount": 0.0,

                        "open_date": str(r[5]),

                        "enter_tag": r[6],

                        "stop_loss_abs": 0.0,

                        "stoploss_dist_pct": 0.0

                    })

                conn.close()

            except Exception as e:

                logger.error(f"Error reading spot sqlite: {e}")



    # 2. Fetch Futures Trades

    try:

        r = requests.get(f"{FUTURES_API_URL}/status", auth=API_AUTH, timeout=2.0)

        if r.status_code == 200:

            for t in r.json():

                trades_list.append({

                    "engine": "Futures",

                    "trade_id": t.get("trade_id"),

                    "pair": t.get("pair"),

                    "side": "SHORT" if t.get("is_short") else "LONG",

                    "open_rate": t.get("open_rate"),

                    "current_rate": t.get("current_rate"),

                    "profit_pct": round(t.get("profit_pct", 0.0), 2),

                    "profit_abs": round(t.get("profit_abs", 0.0), 2),

                    "stake_amount": round(t.get("stake_amount", 0.0), 2),

                    "open_date": t.get("open_date"),

                    "enter_tag": t.get("enter_tag"),

                    "stop_loss_abs": t.get("stop_loss_abs"),

                    "stoploss_dist_pct": round(t.get("stoploss_current_dist_pct", 0.0), 2)

                })

        else:

            raise Exception("Futures API status failed")

    except Exception:

        # Fallback to Futures SQLite

        fut_db = USER_DATA_DIR / "trades_futures.sqlite"

        if fut_db.exists():

            try:

                conn = sqlite3.connect(f"file:{fut_db.resolve()}?mode=ro", uri=True)

                c = conn.cursor()

                rows = c.execute(

                    "SELECT id, pair, open_rate, is_open, fee_open, open_date, enter_tag, is_short "

                    "FROM trades WHERE is_open = 1 ORDER BY id DESC"

                ).fetchall()

                for r in rows:

                    trades_list.append({

                        "engine": "Futures (DB)",

                        "trade_id": r[0],

                        "pair": r[1],

                        "side": "SHORT" if r[7] else "LONG",

                        "open_rate": r[2],

                        "current_rate": r[2],

                        "profit_pct": 0.0,

                        "profit_abs": 0.0,

                        "stake_amount": 0.0,

                        "open_date": str(r[5]),

                        "enter_tag": r[6],

                        "stop_loss_abs": 0.0,

                        "stoploss_dist_pct": 0.0

                    })

                conn.close()

            except Exception as e:

                logger.error(f"Error reading futures sqlite: {e}")



    return {"trades": trades_list, "total_open": len(trades_list)}





@app.post("/api/engine/{engine_name}/{action}")

async def engine_action(engine_name: str, action: str):

    """

    Controls docker containers:

    engine_name: 'spot', 'futures', or 'all'

    action: 'restart', 'stop', 'start'

    """

    if action not in ["restart", "stop", "start"]:

        raise HTTPException(status_code=400, detail="Invalid action")



    containers = []

    if engine_name in ["spot", "all"]:

        containers.append("freqtrade_spot_engine")

    if engine_name in ["futures", "all"]:

        containers.append("freqtrade_futures_engine")



    if not containers:

        raise HTTPException(status_code=400, detail="Invalid engine name")



    results = {}

    for c in containers:

        try:

            cmd = ["docker", action, c]

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            results[c] = "success" if res.returncode == 0 else f"failed: {res.stderr.strip()}"

        except Exception as e:

            results[c] = f"error: {str(e)}"



    return {

        "engine": engine_name,

        "action": action,

        "results": results

    }





@app.post("/api/trades/forceexit")

async def force_exit_trade(payload: dict):

    """

    Forces exit of a specific trade by ID via the Freqtrade API.

    Payload: {"engine": "spot"|"futures", "trade_id": 1}

    """

    engine = payload.get("engine", "").lower()

    trade_id = payload.get("trade_id")

    if not trade_id:

        raise HTTPException(status_code=400, detail="Missing trade_id")



    url = SPOT_API_URL if "spot" in engine else FUTURES_API_URL

    try:

        r = requests.post(

            f"{url}/forceexit",

            auth=API_AUTH,

            json={"tradeid": str(trade_id)},

            timeout=5.0

        )

        return r.json()

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))





@app.get("/api/logs/{engine_name}")

async def get_logs(engine_name: str, lines: int = 50):

    """

    Fetches recent docker logs for the specified engine.

    """

    container = "freqtrade_spot_engine" if engine_name == "spot" else "freqtrade_futures_engine"

    try:

        cmd = ["docker", "logs", "--tail", str(lines), container]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        raw_logs = res.stdout if res.stdout else res.stderr

        return {"engine": engine_name, "logs": raw_logs}

    except Exception as e:

        return {"engine": engine_name, "logs": f"Error fetching logs: {str(e)}"}







@app.get("/api/sr_channels/{symbol}")

async def get_sr_channels(symbol: str):

    """

    Computes real-time Support Resistance Channels for any symbol

    using the exact TradingView LonesomeTheBlue pivot clustering algorithm.

    """

    try:

        clean_sym = symbol.replace("/", "").replace(":USDT", "").upper()

        if clean_sym.endswith("USDT"):

            base = clean_sym[:-4]

            pair = f"{base}/USDT"

        else:

            pair = f"{clean_sym}/USDT"



        settings = read_json_file(STRATEGY_SETTINGS_PATH)

        sr_cfg = settings.get("indicators", {}).get("sr_channels", {})

        pivot_p = int(sr_cfg.get("pivot_period", 10))

        chan_w = float(sr_cfg.get("channel_width_pct", 0.025))

        min_str = int(sr_cfg.get("min_strength", 2))



        # Fetch candles from Spot API

        r = requests.get(f"{SPOT_API_URL}/pair_candles?pair={pair}&timeframe=1h&limit=200", auth=API_AUTH, timeout=3.0)

        if r.status_code != 200:

            # Fallback to futures pair format

            r = requests.get(f"{FUTURES_API_URL}/pair_candles?pair={pair}:USDT&timeframe=1h&limit=200", auth=API_AUTH, timeout=3.0)

            if r.status_code != 200:

                return {"error": f"Failed to fetch candles for {pair}"}



        c = r.json()

        cols = c.get("columns", [])

        data = c.get("data", [])

        if not data:

            return {"error": "No data returned"}



        close_idx = cols.index("close")

        high_idx = cols.index("high")

        low_idx = cols.index("low")



        highs = [float(row[high_idx]) for row in data]

        lows = [float(row[low_idx]) for row in data]

        closes = [float(row[close_idx]) for row in data]

        n = len(data)



        pivots = []

        half_w = chan_w / 2.0

        start_idx = max(pivot_p, n - 200)



        for i in range(start_idx, n - pivot_p):

            if highs[i] == max(highs[i - pivot_p : i + pivot_p + 1]):

                pivots.append((highs[i], 'high', i))

            if lows[i] == min(lows[i - pivot_p : i + pivot_p + 1]):

                pivots.append((lows[i], 'low', i))



        channels = []

        for p_price, p_type, p_idx in pivots:

            p_top = p_price * (1.0 + half_w)

            p_bot = p_price * (1.0 - half_w)

            matched = False

            for ch in channels:

                if not (p_top < ch['bot'] or p_bot > ch['top']):

                    ch['top'] = max(ch['top'], p_top)

                    ch['bot'] = min(ch['bot'], p_bot)

                    ch['mid'] = (ch['top'] + ch['bot']) / 2.0

                    ch['touches'] += 1

                    matched = True

                    break

            if not matched:

                channels.append({

                    'top': p_top,

                    'bot': p_bot,

                    'mid': p_price,

                    'touches': 1

                })



        filtered = [ch for ch in channels if ch['touches'] >= min_str]

        filtered.sort(key=lambda x: x['mid'])



        cur_price = closes[-1]

        supports = [ch for ch in filtered if ch['top'] <= cur_price or (ch['bot'] <= cur_price <= ch['top'])]

        resistances = [ch for ch in filtered if ch['bot'] >= cur_price or (ch['bot'] <= cur_price <= ch['top'])]



        near_sup = supports[-1] if supports else None

        near_res = resistances[0] if resistances else None



        return {

            "symbol": pair,

            "current_price": round(cur_price, 2),

            "nearest_support": {

                "bottom": round(near_sup["bot"], 2),

                "top": round(near_sup["top"], 2),

                "touches": near_sup["touches"],

                "dist_pct": round((cur_price - near_sup["top"]) / cur_price * 100, 2)

            } if near_sup else None,

            "nearest_resistance": {

                "bottom": round(near_res["bot"], 2),

                "top": round(near_res["top"], 2),

                "touches": near_res["touches"],

                "dist_pct": round((near_res["bot"] - cur_price) / cur_price * 100, 2)

            } if near_res else None,

            "channels_count": len(filtered),

            "channels": [

                {

                    "type": "SUPPORT" if ch["top"] <= cur_price else ("RESISTANCE" if ch["bot"] >= cur_price else "ACTIVE_ZONE"),

                    "bottom": round(ch["bot"], 2),

                    "top": round(ch["top"], 2),

                    "touches": ch["touches"]

                } for ch in filtered

            ]

        }

    except Exception as e:

        return {"error": str(e)}





# =============================================================================





# =============================================================================

# Market Opportunity Scanner & Pair Management

# =============================================================================



def compute_market_indicators(klines: list) -> Optional[dict]:

    if not klines or len(klines) < 25:

        return None

    try:

        highs = np.array([float(k[2]) for k in klines])

        lows = np.array([float(k[3]) for k in klines])

        closes = np.array([float(k[4]) for k in klines])

        cur_price = float(closes[-1])



        # RSI 14

        deltas = np.diff(closes)

        seed = deltas[:14]

        up = float(seed[seed >= 0].sum() / 14.0) if len(seed[seed >= 0]) > 0 else 0.0

        down = float(-seed[seed < 0].sum() / 14.0) if len(seed[seed < 0]) > 0 else 0.0

        rs = up / down if down != 0 else 100.0

        rsi = 100.0 - (100.0 / (1.0 + rs))

        for d in deltas[14:]:

            up_val = float(d) if d > 0 else 0.0

            down_val = float(-d) if d < 0 else 0.0

            up = (up * 13.0 + up_val) / 14.0

            down = (down * 13.0 + down_val) / 14.0

            rs = up / down if down != 0 else 100.0

            rsi = 100.0 - (100.0 / (1.0 + rs))



        # ADX & DMI 14

        tr_list, plus_dm_list, minus_dm_list = [], [], []

        for i in range(1, len(closes)):

            h_diff = float(highs[i] - highs[i-1])

            l_diff = float(lows[i-1] - lows[i])

            tr = max(float(highs[i] - lows[i]), abs(float(highs[i] - closes[i-1])), abs(float(lows[i] - closes[i-1])))

            tr_list.append(tr)

            plus_dm_list.append(h_diff if (h_diff > l_diff and h_diff > 0) else 0.0)

            minus_dm_list.append(l_diff if (l_diff > h_diff and l_diff > 0) else 0.0)



        tr_s = sum(tr_list[:14])

        p_dm_s = sum(plus_dm_list[:14])

        m_dm_s = sum(minus_dm_list[:14])

        dx_list = []

        p_di = 100.0 * p_dm_s / tr_s if tr_s > 0 else 0.0

        m_di = 100.0 * m_dm_s / tr_s if tr_s > 0 else 0.0

        denom = p_di + m_di

        dx_list.append(100.0 * abs(p_di - m_di) / denom if denom > 0 else 0.0)



        for i in range(14, len(tr_list)):

            tr_s = tr_s - (tr_s / 14.0) + tr_list[i]

            p_dm_s = p_dm_s - (p_dm_s / 14.0) + plus_dm_list[i]

            m_dm_s = m_dm_s - (m_dm_s / 14.0) + minus_dm_list[i]

            p_di = 100.0 * p_dm_s / tr_s if tr_s > 0 else 0.0

            m_di = 100.0 * m_dm_s / tr_s if tr_s > 0 else 0.0

            denom = p_di + m_di

            dx_list.append(100.0 * abs(p_di - m_di) / denom if denom > 0 else 0.0)



        adx = float(np.mean(dx_list[-14:])) if len(dx_list) >= 14 else float(dx_list[-1])



        # Nearest Pivots (period 5)

        sup_levels, res_levels = [], []

        p = 5

        for i in range(p, len(closes) - p):

            if lows[i] == min(lows[i-p : i+p+1]):

                sup_levels.append(float(lows[i]))

            if highs[i] == max(highs[i-p : i+p+1]):

                res_levels.append(float(highs[i]))



        valid_sups = [s for s in sup_levels if s <= cur_price]

        valid_res = [r for r in res_levels if r >= cur_price]

        nearest_sup = max(valid_sups) if valid_sups else float(min(lows))

        nearest_res = min(valid_res) if valid_res else float(max(highs))



        dist_sup_pct = round(((cur_price - nearest_sup) / cur_price) * 100, 2)

        dist_res_pct = round(((nearest_res - cur_price) / cur_price) * 100, 2)

        # MFI 14 (Volume-Weighted Momentum)
        mfi_val = 50.0
        try:
            typical_prices = (highs + lows + closes) / 3.0
            raw_money_flow = typical_prices * volumes
            pos_flow, neg_flow = [], []
            for idx in range(1, len(typical_prices)):
                if typical_prices[idx] > typical_prices[idx-1]:
                    pos_flow.append(raw_money_flow[idx])
                    neg_flow.append(0.0)
                elif typical_prices[idx] < typical_prices[idx-1]:
                    pos_flow.append(0.0)
                    neg_flow.append(raw_money_flow[idx])
                else:
                    pos_flow.append(0.0)
                    neg_flow.append(0.0)
            if len(pos_flow) >= 14:
                pos_mf = sum(pos_flow[-14:])
                neg_mf = sum(neg_flow[-14:])
                if neg_mf > 0:
                    mr = pos_mf / neg_mf
                    mfi_val = round(float(100.0 - (100.0 / (1.0 + mr))), 1)
                else:
                    mfi_val = 100.0 if pos_mf > 0 else 50.0
        except Exception:
            mfi_val = 50.0

        return {

            'cur_price': cur_price,

            'rsi': round(float(rsi), 1),

            'mfi': mfi_val,

            'adx': round(float(adx), 1),

            'plus_di': round(float(p_di), 1),

            'minus_di': round(float(m_di), 1),

            'nearest_sup': round(nearest_sup, 4),

            'nearest_res': round(nearest_res, 4),

            'dist_sup_pct': dist_sup_pct,

            'dist_res_pct': dist_res_pct

        }

    except Exception as e:

        logger.debug(f'Error computing market indicators: {e}')

        return None





def score_opportunity(item: dict) -> tuple:
    rsi = float(item.get('rsi', 50))
    mfi = float(item.get('mfi', 50))
    adx = float(item.get('adx', 20))
    p_di = float(item.get('plus_di', 20))
    m_di = float(item.get('minus_di', 20))
    dist_sup = float(item.get('dist_sup_pct', 5.0))
    dist_res = float(item.get('dist_res_pct', 5.0))
    vol_m = float(item.get('volume_m', 0))
    chg = float(item.get('change_24h', 0))

    # Base baseline scores
    long_score = 40.0
    short_score = 40.0

    vol_boost = 0.0
    if vol_m > 100:
        vol_boost = 10.0
    elif vol_m > 50:
        vol_boost = 5.0

    # 1. Long Opportunity Scoring (Spot / Futures Long)
    if p_di > m_di:
        long_score += 6.0
    if dist_sup <= 2.2 and rsi <= 52:
        long_score += 30.0 + max(0.0, (2.2 - dist_sup) * 5)
        long_sig = 'ارتداد دعم واعد (شراء Spot/Long)'
        long_col = 'emerald'
    elif p_di > m_di and adx >= 24 and chg > 0:
        long_score += 26.0 + min(18.0, (adx - 20) * 1.5)
        long_sig = 'زخم صاعد قوي (شراء Spot/Long)'
        long_col = 'cyan'
    elif rsi < 32 or mfi < 25:
        long_score += 28.0 + max(0.0, (32 - min(32, rsi)) * 1.5)
        long_sig = 'تشبع بيعي ارتدادي (مراقبة شراء)'
        long_col = 'amber'
    elif dist_res <= 1.5 and p_di > m_di:
        long_score += 15.0
        long_sig = 'اختبار مقاومة (Long)'
        long_col = 'purple'
    else:
        long_sig = 'تجميع واستقرار'
        long_col = 'slate'
    long_score += vol_boost

    # 2. Short Opportunity Scoring (Futures Short Only)
    # HARD OVERSOLD VETO: If RSI < 35 or MFI < 25, the market is in deep oversold exhaustion.
    # Shorting here is strictly forbidden!
    if rsi < 35.0 or mfi < 25.0:
        short_score = int(max(15, 36 - max(0, 35 - rsi) * 1.5 - max(0, 25 - mfi)))
        short_sig = 'تشبع واستنزاف بيعي (مراقبة ارتداد صاعد)'
        short_col = 'amber'
    else:
        if m_di > p_di:
            short_score += 6.0
        if m_di > p_di and adx >= 24 and chg < 0 and 35.0 <= rsi <= 65.0:
            short_score += 28.0 + min(18.0, (adx - 20) * 1.5)
            short_sig = 'زخم هابط متزن (بيع Futures/Short)'
            short_col = 'rose'
        elif dist_res <= 2.2 and rsi >= 48 and m_di > p_di:
            short_score += 30.0 + max(0.0, (2.2 - dist_res) * 5)
            short_sig = 'ارتداد بيعي من المقاومة (Futures/Short)'
            short_col = 'rose'
        elif rsi > 68 and m_di > p_di:
            short_score += 26.0 + max(0.0, (rsi - 68) * 1.5)
            short_sig = 'تشبع شرائي تصريفي (Futures/Short)'
            short_col = 'amber'
        elif dist_sup <= 1.8 and m_di > p_di and adx >= 22 and 35.0 <= rsi <= 60.0:
            short_score += 22.0
            short_sig = 'كسر دعم هابط (Futures/Short)'
            short_col = 'rose'
        else:
            short_sig = 'تذبذب هابط ضعيف'
            short_col = 'slate'
        short_score += vol_boost

    # Determine recommended side & engine (Only allow short if NOT oversold!)
    if short_score > long_score and m_di > p_di and adx >= 20 and rsi >= 35.0 and mfi >= 25.0:
        final_score = int(min(98, max(20, round(short_score))))
        signal = short_sig
        color = short_col
        rec_side = 'short'
        rec_engine = 'futures'
        engine_badge = 'Futures: بيع 📉'
    else:
        final_score = int(min(98, max(20, round(long_score))))
        signal = long_sig
        color = long_col
        rec_side = 'long'
        rec_engine = 'spot'
        engine_badge = 'Spot: شراء 📈'

    item['recommended_side'] = rec_side
    item['recommended_engine'] = rec_engine
    item['engine_badge'] = engine_badge
    item['long_score'] = int(min(98, max(20, round(long_score))))
    item['short_score'] = int(min(98, max(20, round(short_score))))

    return final_score, signal, color









@app.get('/api/market/scan')

async def scan_market_opportunities(

    preset: str = 'all',

    min_volume: float = 20.0,

    sort_by: str = 'score',

    limit: int = 30

):

    try:

        r = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=7.0)

        if r.status_code != 200:

            raise HTTPException(status_code=502, detail='Failed to fetch Binance 24h ticker')

        raw_tickers = r.json()



        blacklist = [

            'UPUSDT', 'DOWNUSDT', 'BULLUSDT', 'BEARUSDT', 'USDCUSDT', 'FDUSDUSDT',

            'TUSDUSDT', 'BUSDUSDT', 'EURUSDT', 'GBPUSDT', 'DAIUSDT', 'USD1USDT',

            'USDEUSDT', 'USDDUSDT', 'PYUSDUSDT', 'PAXGUSDT', 'AEURUSDT', 'INTCBUSDT', 'UUSDT'

        ]



        cfg_spot = read_json_file(CONFIG_SPOT_PATH)

        cfg_futures = read_json_file(CONFIG_FUTURES_PATH)

        spot_pairs = set(cfg_spot.get('exchange', {}).get('pair_whitelist', []))

        futures_pairs = set(cfg_futures.get('exchange', {}).get('pair_whitelist', []))



        candidates = []

        for t in raw_tickers:

            sym = t.get('symbol', '')

            if not sym.endswith('USDT') or sym in blacklist:

                continue

            vol_m = float(t.get('quoteVolume', 0)) / 1_000_000.0

            if vol_m < min_volume:

                continue

            base = sym[:-4]

            candidates.append({

                'symbol': sym,

                'base': base,

                'pair_spot': f'{base}/USDT',

                'pair_futures': f'{base}/USDT:USDT',

                'price': float(t.get('lastPrice', 0)),

                'change_24h': round(float(t.get('priceChangePercent', 0)), 2),

                'volume_m': round(vol_m, 1),

                'high_24h': float(t.get('highPrice', 0)),

                'low_24h': float(t.get('lowPrice', 0)),

                'in_spot': f'{base}/USDT' in spot_pairs,

                'in_futures': f'{base}/USDT:USDT' in futures_pairs

            })



        candidates.sort(key=lambda x: x['volume_m'], reverse=True)

        # Scan top 18 high-volume candidates for ultra-fast, sub-second response

        top_candidates = candidates[:min(20, max(12, limit))]



        def fetch_klines(item):

            sym = item['symbol']

            try:

                kr = requests.get(f'https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&limit=55', timeout=2.5)

                if kr.status_code == 200:

                    ind = compute_market_indicators(kr.json())

                    if ind:

                        item.update(ind)

                        score, sig, col = score_opportunity(item)

                        item['score'] = score

                        item['signal'] = sig

                        item['signal_color'] = col

                        return item

            except Exception:

                pass

            item['score'] = 40

            item['signal'] = 'بيانات غير مكتملة'

            item['signal_color'] = 'slate'

            item['rsi'] = 50.0

            item['adx'] = 20.0

            item['plus_di'] = 20.0

            item['minus_di'] = 20.0

            item['dist_sup_pct'] = 0.0

            item['dist_res_pct'] = 0.0

            return item



        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:

            analyzed = list(executor.map(fetch_klines, top_candidates))



        if preset == 'support_bounce':

            analyzed = [x for x in analyzed if x.get('dist_sup_pct', 99) <= 2.5 and x.get('rsi', 100) <= 52]

        elif preset == 'breakout':

            analyzed = [x for x in analyzed if x.get('adx', 0) >= 22 and x.get('plus_di', 0) > x.get('minus_di', 0)]

        elif preset == 'oversold':

            analyzed = [x for x in analyzed if x.get('rsi', 100) <= 40]

        elif preset == 'high_volume':

            analyzed = [x for x in analyzed if x.get('volume_m', 0) >= 50.0]



        if sort_by == 'score':

            analyzed.sort(key=lambda x: x.get('score', 0), reverse=True)

        elif sort_by == 'volume':

            analyzed.sort(key=lambda x: x.get('volume_m', 0), reverse=True)

        elif sort_by == 'change_desc':

            analyzed.sort(key=lambda x: x.get('change_24h', 0), reverse=True)

        elif sort_by == 'change_asc':

            analyzed.sort(key=lambda x: x.get('change_24h', 0))

        elif sort_by == 'rsi_low':

            analyzed.sort(key=lambda x: x.get('rsi', 100))



        return {

            'timestamp': datetime.now().isoformat(),

            'scanned_count': len(candidates),

            'results_count': len(analyzed[:limit]),

            'spot_tracked_count': len(spot_pairs),

            'futures_tracked_count': len(futures_pairs),

            'opportunities': analyzed[:limit]

        }

    except Exception as e:

        logger.error(f'Error in scan_market_opportunities: {e}')

        raise HTTPException(status_code=500, detail=str(e))





@app.post('/api/market/add_pair')

async def add_pair_to_engine(payload: dict):

    raw_symbol = payload.get('symbol', '').strip().upper()

    engines = payload.get('engines', ['spot'])

    download_data = payload.get('download_data', True)

    auto_hunt = payload.get('auto_hunt', True)



    if not raw_symbol:

        raise HTTPException(status_code=400, detail='Missing symbol')



    clean = raw_symbol.replace('/USDT', '').replace(':USDT', '').replace('USDT', '')

    pair_spot = f'{clean}/USDT'

    pair_futures = f'{clean}/USDT:USDT'



    results = {}

    reloaded = {}



    if 'spot' in engines:

        cfg = read_json_file(CONFIG_SPOT_PATH)

        if 'exchange' not in cfg:

            cfg['exchange'] = {}

        whitelist = cfg['exchange'].get('pair_whitelist', [])

        if pair_spot not in whitelist:

            whitelist.append(pair_spot)

            cfg['exchange']['pair_whitelist'] = whitelist

            write_json_atomic(CONFIG_SPOT_PATH, cfg)

            results['spot'] = f'Added {pair_spot}'

            try:

                r = requests.post(f'{SPOT_API_URL}/reload_config', auth=API_AUTH, timeout=3.0)

                reloaded['spot'] = (r.status_code == 200)

            except Exception:

                reloaded['spot'] = False

        else:

            results['spot'] = f'{pair_spot} already in whitelist'



    if 'futures' in engines:

        cfg = read_json_file(CONFIG_FUTURES_PATH)

        if 'exchange' not in cfg:

            cfg['exchange'] = {}

        whitelist = cfg['exchange'].get('pair_whitelist', [])

        if pair_futures not in whitelist:

            whitelist.append(pair_futures)

            cfg['exchange']['pair_whitelist'] = whitelist

            write_json_atomic(CONFIG_FUTURES_PATH, cfg)

            results['futures'] = f'Added {pair_futures}'

            try:

                r = requests.post(f'{FUTURES_API_URL}/reload_config', auth=API_AUTH, timeout=3.0)

                reloaded['futures'] = (r.status_code == 200)

            except Exception:

                reloaded['futures'] = False

        else:

            results['futures'] = f'{pair_futures} already in whitelist'



    if download_data:

        def run_download():

            try:

                if 'spot' in engines:

                    subprocess.run(

                        ['docker', 'exec', 'freqtrade_spot_engine', 'freqtrade', 'download-data',

                         '--pairs', pair_spot, '--timeframes', '1h', '4h', '--timerange', '20260101-'],

                        capture_output=True, text=True, timeout=120

                    )

                if 'futures' in engines:

                    subprocess.run(

                        ['docker', 'exec', 'freqtrade_futures_engine', 'freqtrade', 'download-data',

                         '--pairs', pair_futures, '--trading-mode', 'futures', '--timeframes', '1h', '4h', '--timerange', '20260101-'],

                        capture_output=True, text=True, timeout=120

                    )

            except Exception as dl_err:

                logger.error(f'Background download error for {clean}: {dl_err}')



        t = threading.Thread(target=run_download, daemon=True)

        t.start()



    # Search for immediate opportunity on the added coin

    opportunity_result = {

        'searched': True,

        'entered': False,

        'trade_id': None,

        'message': f'تمت إضافة {clean} بنجاح'

    }

    if auto_hunt:

        try:

            sym_binance = f'{clean}USDT'

            kr = requests.get(f'https://api.binance.com/api/v3/klines?symbol={sym_binance}&interval=1h&limit=55', timeout=4.0)

            if kr.status_code == 200:

                ind = compute_market_indicators(kr.json())

                if ind:

                    score, sig, col = score_opportunity(ind)

                    opportunity_result['analysis'] = {

                        'price': ind.get('cur_price'),

                        'rsi': ind.get('rsi'),

                        'adx': ind.get('adx'),

                        'dist_sup_pct': ind.get('dist_sup_pct'),

                        'score': score,

                        'signal': sig

                    }

                    if score >= 60:

                        target_eng = 'spot' if 'spot' in engines else 'futures'

                        api_url = SPOT_API_URL if target_eng == 'spot' else FUTURES_API_URL

                        ent_p = pair_spot if target_eng == 'spot' else pair_futures

                        f_body = {'pair': ent_p}

                        if target_eng == 'futures':

                            f_body['side'] = 'short' if ind.get('minus_di', 0) > ind.get('plus_di', 0) else 'long'

                        

                        fe_r = requests.post(f'{api_url}/forceenter', auth=API_AUTH, json=f_body, timeout=4.0)

                        if fe_r.status_code == 200:

                            t_id = fe_r.json().get('trade_id')

                            opportunity_result['entered'] = True

                            opportunity_result['trade_id'] = t_id

                            opportunity_result['message'] = f'تم فحص {clean} واكتشاف فرصة واعدة (يقين {score}%)، وتم تنفيذ أمر الدخول في الصفقة #{t_id} فورياً!'

                        else:

                            opportunity_result['message'] = f'تم فحص {clean} واكتشاف فرصة واعدة (يقين {score}%) وهي تحت مراقبة الاستراتيجية.'

                    else:

                        opportunity_result['message'] = f'تمت إضافة {clean} بنجاح. يقين الدخول الحالي {score}%، وتنتظر الاستراتيجية اكتمال الشروط للدخول التلقائي.'

        except Exception as hunt_err:

            logger.debug(f'Auto hunt error for {clean}: {hunt_err}')



    return {

        'status': 'success',

        'symbol': clean,

        'results': results,

        'reloaded': reloaded,

        'download_started': download_data,

        'opportunity': opportunity_result

    }





def audit_pair_opportunity(pair: str, engine: str = 'spot', side: str = 'long') -> dict:

    """

    Comprehensive Pre-Flight Trade Diagnostic & Quantitative Feasibility Audit.

    Evaluates ADX, Support/Resistance channels, RSI momentum, and Volatility risk

    before committing capital or executing entry.

    """

    clean = pair.replace('/USDT', '').replace(':USDT', '').replace('USDT', '').strip().upper()

    sym_binance = f'{clean}USDT'

    

    # 1. Fetch recent 1h klines from Binance

    try:

        r = requests.get('https://api.binance.com/api/v3/klines', params={'symbol': sym_binance, 'interval': '1h', 'limit': 65}, timeout=4.5)

        if r.status_code != 200 or len(r.json()) < 25:

            return {'status': 'error', 'message': f'تعذر جلب بيانات الشموع اللحظية لـ {clean}'}

        klines = r.json()

    except Exception as e:

        return {'status': 'error', 'message': f'خطأ اتصال مع Binance: {str(e)}'}



    # 2. Fetch 24h ticker statistics

    chg_24h, vol_24h_m = 0.0, 0.0

    try:

        tr = requests.get('https://api.binance.com/api/v3/ticker/24hr', params={'symbol': sym_binance}, timeout=3.0)

        if tr.status_code == 200:

            td = tr.json()

            chg_24h = round(float(td.get('priceChangePercent', 0)), 2)

            vol_24h_m = round(float(td.get('quoteVolume', 0)) / 1_000_000.0, 1)

    except Exception:

        pass



    # 2.5 Query local Freqtrade engine for FreqAI LightGBM predictions

    ai_metrics = {

        'available': False,

        'expected_return': None,

        'do_predict': None,

        'di_value': None,

        'conviction_text': 'النموذج جاهز للتدريب عند الإضافة',

        'badge': 'secondary'

    }

    try:

        engine_port = 8081 if engine == 'futures' else 8080

        pair_query = f'{clean}/USDT:USDT' if engine == 'futures' else f'{clean}/USDT'

        ai_resp = requests.get(

            f'http://localhost:{engine_port}/api/v1/pair_candles',

            params={'pair': pair_query, 'timeframe': '1h', 'limit': 1},

            auth=API_AUTH,

            timeout=1.5

        )

        if ai_resp.status_code == 200:

            cdata = ai_resp.json()

            if cdata.get('data') and len(cdata['data']) > 0:

                cols = cdata.get('columns', [])

                row = cdata['data'][0]

                rec = dict(zip(cols, row))

                s_close = rec.get('&-s_close')

                d_pred = rec.get('do_predict')

                di_val = rec.get('DI_values')

                if s_close is not None:

                    exp_ret = round(float(s_close) * 100, 2)

                    ai_metrics['available'] = True

                    ai_metrics['expected_return'] = exp_ret

                    ai_metrics['do_predict'] = int(float(d_pred)) if d_pred is not None else 0

                    ai_metrics['di_value'] = round(float(di_val), 2) if di_val is not None else 0.0

                    if ai_metrics['do_predict'] == 1 and exp_ret > 0.4:

                        ai_metrics['conviction_text'] = f'يقين صاعد قوي (+{exp_ret}%)'

                        ai_metrics['badge'] = 'pass'

                    elif ai_metrics['do_predict'] == 1 and exp_ret < -0.4:

                        ai_metrics['conviction_text'] = f'يقين هابط قوي ({exp_ret}%)'

                        ai_metrics['badge'] = 'danger'

                    elif ai_metrics['do_predict'] == 0:

                        ai_metrics['conviction_text'] = f'عدم يقين / تذبذب ({exp_ret}%)'

                        ai_metrics['badge'] = 'warning'

                    else:

                        ai_metrics['conviction_text'] = f'محايد ({exp_ret}%)'

                        ai_metrics['badge'] = 'info'

    except Exception as ex_ai:

        logger.debug(f"FreqAI query debug: {ex_ai}")



    highs = np.array([float(k[2]) for k in klines])

    lows = np.array([float(k[3]) for k in klines])

    closes = np.array([float(k[4]) for k in klines])

    cur_price = float(closes[-1])



    # 3. Calculate RSI 14

    deltas = np.diff(closes)

    seed = deltas[:14]

    up = float(seed[seed >= 0].sum() / 14.0) if len(seed[seed >= 0]) > 0 else 0.0

    down = float(-seed[seed < 0].sum() / 14.0) if len(seed[seed < 0]) > 0 else 0.0

    rs = up / down if down != 0 else 100.0

    rsi = 100.0 - (100.0 / (1.0 + rs))

    for d in deltas[14:]:

        up = (up * 13.0 + (float(d) if d > 0 else 0.0)) / 14.0

        down = (down * 13.0 + (float(-d) if d < 0 else 0.0)) / 14.0

        rs = up / down if down != 0 else 100.0

        rsi = 100.0 - (100.0 / (1.0 + rs))

    rsi = round(float(rsi), 1)



    # 3.5 Calculate MFI 14 (Money Flow Index - Volume-Weighted Momentum)
    mfi_val = 50.0
    try:
        volumes = np.array([float(k[5]) for k in klines])
        typical_prices = (highs + lows + closes) / 3.0
        raw_money_flow = typical_prices * volumes
        pos_flow, neg_flow = [], []
        for idx in range(1, len(typical_prices)):
            if typical_prices[idx] > typical_prices[idx-1]:
                pos_flow.append(raw_money_flow[idx])
                neg_flow.append(0.0)
            elif typical_prices[idx] < typical_prices[idx-1]:
                pos_flow.append(0.0)
                neg_flow.append(raw_money_flow[idx])
            else:
                pos_flow.append(0.0)
                neg_flow.append(0.0)
        if len(pos_flow) >= 14:
            pos_mf = sum(pos_flow[-14:])
            neg_mf = sum(neg_flow[-14:])
            if neg_mf > 0:
                mr = pos_mf / neg_mf
                mfi_val = round(float(100.0 - (100.0 / (1.0 + mr))), 1)
            else:
                mfi_val = 100.0 if pos_mf > 0 else 50.0
    except Exception as e:
        logger.warning(f"Error calculating MFI in audit: {e}")
        mfi_val = 50.0

        # 4. Calculate ADX, +DI, -DI 14 & ATR

    tr_list, plus_dm_list, minus_dm_list = [], [], []

    for i in range(1, len(closes)):

        h_diff = float(highs[i] - highs[i-1])

        l_diff = float(lows[i-1] - lows[i])

        tr = max(float(highs[i] - lows[i]), abs(float(highs[i] - closes[i-1])), abs(float(lows[i] - closes[i-1])))

        tr_list.append(tr)

        plus_dm_list.append(h_diff if (h_diff > l_diff and h_diff > 0) else 0.0)

        minus_dm_list.append(l_diff if (l_diff > h_diff and l_diff > 0) else 0.0)



    tr_s = sum(tr_list[:14])

    p_dm_s = sum(plus_dm_list[:14])

    m_dm_s = sum(minus_dm_list[:14])

    dx_list = []

    p_di = 100.0 * p_dm_s / tr_s if tr_s > 0 else 0.0

    m_di = 100.0 * m_dm_s / tr_s if tr_s > 0 else 0.0

    denom = p_di + m_di

    dx_list.append(100.0 * abs(p_di - m_di) / denom if denom > 0 else 0.0)

    for i in range(14, len(tr_list)):

        tr_s = tr_s - (tr_s / 14.0) + tr_list[i]

        p_dm_s = p_dm_s - (p_dm_s / 14.0) + plus_dm_list[i]

        m_dm_s = m_dm_s - (m_dm_s / 14.0) + minus_dm_list[i]

        p_di = 100.0 * p_dm_s / tr_s if tr_s > 0 else 0.0

        m_di = 100.0 * m_dm_s / tr_s if tr_s > 0 else 0.0

        denom = p_di + m_di

        dx_list.append(100.0 * abs(p_di - m_di) / denom if denom > 0 else 0.0)



    adx = float(np.mean(dx_list[-14:])) if len(dx_list) >= 14 else float(dx_list[-1])

    adx = round(adx, 1)

    p_di = round(p_di, 1)

    m_di = round(m_di, 1)

    atr = float(np.mean(tr_list[-14:])) if len(tr_list) >= 14 else float(tr_list[-1])

    atr_pct = round((atr / cur_price) * 100, 2)



    # 5. Support / Resistance Pivots (Window 5 + Rolling 20)

    sup_levels, res_levels = [], []

    p = 5

    for i in range(p, len(closes) - p):

        if lows[i] == min(lows[i-p : i+p+1]):

            sup_levels.append(float(lows[i]))

        if highs[i] == max(highs[i-p : i+p+1]):

            res_levels.append(float(highs[i]))



    valid_sups = [s for s in sup_levels if s <= cur_price]

    valid_res = [r for r in res_levels if r >= cur_price]

    nearest_sup = max(valid_sups) if valid_sups else float(min(lows[-20:]))

    nearest_res = min(valid_res) if valid_res else float(max(highs[-20:]))

    dist_sup_pct = round(((cur_price - nearest_sup) / cur_price) * 100, 2)

    dist_res_pct = round(((nearest_res - cur_price) / cur_price) * 100, 2)



    # 6. Load Strategy Rules & Active Limits

    strat_settings = read_json_file(STRATEGY_SETTINGS_PATH)

    ind_cfg = strat_settings.get('indicators', {})

    adx_min = float(ind_cfg.get('adx', {}).get('min_adx', 22.0))

    adx_exhaust = float(ind_cfg.get('adx', {}).get('exhaustion_threshold', 48.0))

    rsi_min = float(ind_cfg.get('rsi', {}).get('long_rsi_min', 35.0))

    rsi_max = float(ind_cfg.get('rsi', {}).get('long_rsi_max', 78.0))



    checks = []

    # Check 0: FreqAI Model Conviction

    if ai_metrics.get('available'):

        d_pred = ai_metrics.get('do_predict', 0)

        exp_ret = ai_metrics.get('expected_return', 0.0)

        di_v = ai_metrics.get('di_value', 0.0)

        if d_pred == 1 and ((side == 'long' and exp_ret > 0.2) or (side == 'short' and exp_ret < -0.2)):

            checks.append({

                'id': 'freqai_ai',

                'name': 'تنبؤ الذكاء الاصطناعي FreqAI',

                'status': 'pass',

                'badge': 'يقين مرتفع',

                'value': f'{exp_ret:+}% (DI: {di_v})',

                'detail': f'نموذج LightGBM يتوقع عائداً مستقبلياً قدره ({exp_ret:+}% - بثقة تنبؤ عالية).'

            })

        elif d_pred == 0:

            checks.append({

                'id': 'freqai_ai',

                'name': 'تنبؤ الذكاء الاصطناعي FreqAI',

                'status': 'warning',

                'badge': 'سوق غير معتاد (Outlier)',

                'value': f'{exp_ret:+}% (DI: {di_v})',

                'detail': f'النموذج يرى تذبذباً استثنائياً ويوصي بعدم التداول العشوائي لحين وضوح الاتجاه.'

            })



    # Check 1: ADX & Momentum Exhaustion

    if adx >= adx_exhaust:

        checks.append({

            'id': 'adx',

            'name': 'مؤشر قوة وإنهاك الاتجاه (ADX)',

            'status': 'danger',

            'badge': 'إنهاك اتجاهي حرج',

            'value': f'{adx}',

            'detail': f'مؤشر ADX وصل لمنطقة الإنهاك القصوى ({adx} > {adx_exhaust})، مما يعني اقتراب ذروة الشراء وخطر تفعيل الخروج الإجباري من الاستراتيجية.'

        })

    elif adx >= adx_min:

        checks.append({

            'id': 'adx',

            'name': 'مؤشر قوة الاتجاه (ADX)',

            'status': 'pass',

            'badge': 'زخم اتجاهي صحي',

            'value': f'{adx}',

            'detail': f'مؤشر ADX يعكس قوة اتجاه واضحة ومستقرة ({adx} >= {adx_min}) بدون تذبذب عشوائي.'

        })

    else:

        checks.append({

            'id': 'adx',

            'name': 'مؤشر قوة الاتجاه (ADX)',

            'status': 'warning',

            'badge': 'تذبذب عرضي ضعيف',

            'value': f'{adx}',

            'detail': f'مؤشر ADX أقل من عتبة القوة ({adx} < {adx_min})، مما يعكس حركة سوق أفقية قد تعطي إشارات وهمية.'

        })



    # Check 2: DI Liquidity Dominance

    if side == 'long':

        if p_di > m_di:

            checks.append({

                'id': 'di_flow',

                'name': 'قوى السيولة والاتجاه (+DI مقابل -DI)',

                'status': 'pass',

                'badge': 'سيولة شرائية غالبة',

                'value': f'+DI: {p_di} | -DI: {m_di}',

                'detail': f'قوى الشراء (+DI: {p_di}) تتفوق بوضوح على قوى البيع (-DI: {m_di}).'

            })

        else:

            checks.append({

                'id': 'di_flow',

                'name': 'قوى السيولة والاتجاه (+DI مقابل -DI)',

                'status': 'danger',

                'badge': 'ضغط بيعي معاكس',

                'value': f'+DI: {p_di} | -DI: {m_di}',

                'detail': f'قوى البيع (-DI: {m_di}) تسيطر على السوق مقابل (+DI: {p_di})، مما يتعارض مع الدخول شراء.'

            })

    else:

        if m_di > p_di:

            checks.append({

                'id': 'di_flow',

                'name': 'قوى السيولة والاتجاه (-DI مقابل +DI)',

                'status': 'pass',

                'badge': 'سيولة بيعية غالبة',

                'value': f'-DI: {m_di} | +DI: {p_di}',

                'detail': f'قوى البيع (-DI: {m_di}) تتفوق على الشراء وتدعم صفقة البيع Short.'

            })

        else:

            checks.append({

                'id': 'di_flow',

                'name': 'قوى السيولة والاتجاه (-DI مقابل +DI)',

                'status': 'danger',

                'badge': 'ضغط شرائي صاعد',

                'value': f'-DI: {m_di} | +DI: {p_di}',

                'detail': f'قوى الشراء (+DI: {p_di}) ما زالت متفوقة على البيع.'

            })



    # Check 3: S/R Channels Proximity & Headroom Guard
    if side == 'long':
        if dist_res_pct < 2.0:
            checks.append({
                'id': 'sr_proximity',
                'name': 'قنوات الدعم والمقاومة S/R',
                'status': 'danger',
                'badge': 'خطر سقف المقاومة',
                'value': f'دعم: +{dist_sup_pct}% | مقاومة: -{dist_res_pct}%',
                'detail': f'السعر يلتصق بسقف المقاومة (-{dist_res_pct}% < 2.0%)، هامش الربح قبل المقاومة ضئيل جداً وخطر الارتداد الهابط مرتفع!'
            })
        elif dist_sup_pct <= 2.5 and dist_res_pct >= 2.5:
            checks.append({
                'id': 'sr_proximity',
                'name': 'قنوات الدعم والمقاومة S/R',
                'status': 'pass',
                'badge': 'ارتداد مثالي من الدعم',
                'value': f'دعم: +{dist_sup_pct}% | مقاومة: -{dist_res_pct}%',
                'detail': f'السعر قريب جداً من أرضية الدعم (+{dist_sup_pct}%) مع هامش صعود آمن للمقاومة (-{dist_res_pct}%).'
            })
        elif dist_sup_pct <= 5.0 and dist_res_pct >= 2.0:
            checks.append({
                'id': 'sr_proximity',
                'name': 'قنوات الدعم والمقاومة S/R',
                'status': 'warning',
                'badge': 'متوسط البعد عن الدعم',
                'value': f'دعم: +{dist_sup_pct}% | مقاومة: -{dist_res_pct}%',
                'detail': f'السعر يبتعد (+{dist_sup_pct}%) عن الدعم مع هامش معقول للمقاومة (-{dist_res_pct}%).'
            })
        else:
            checks.append({
                'id': 'sr_proximity',
                'name': 'قنوات الدعم والمقاومة S/R',
                'status': 'danger',
                'badge': 'تضخم سعري بعيد عن الدعم',
                'value': f'دعم: +{dist_sup_pct}% | مقاومة: -{dist_res_pct}%',
                'detail': f'السعر متضخم وبعيد جداً عن أرضية الدعم (+{dist_sup_pct}% > 5%) أو غير كافٍ قبل المقاومة، مخاطرة القمة مرتفعة جداً!'
            })
    else:  # short
        if dist_sup_pct < 2.0:
            checks.append({
                'id': 'sr_proximity',
                'name': 'قنوات الدعم والمقاومة S/R',
                'status': 'danger',
                'badge': 'خطر أرضية الدعم',
                'value': f'مقاومة: -{dist_res_pct}% | دعم: +{dist_sup_pct}%',
                'detail': f'السعر يلتصق بأرضية الدعم (+{dist_sup_pct}% < 2.0%)، البيع على المكشوف هنا عالي المخاطر لاحتمالية الارتداد الصاعد!'
            })
        elif dist_res_pct <= 2.5 and dist_sup_pct >= 2.5:
            checks.append({
                'id': 'sr_proximity',
                'name': 'قنوات الدعم والمقاومة S/R',
                'status': 'pass',
                'badge': 'منطقة بيع مثالية من المقاومة',
                'value': f'مقاومة: -{dist_res_pct}% | دعم: +{dist_sup_pct}%',
                'detail': f'السعر ملامس لجدار المقاومة (-{dist_res_pct}%) مع هامش هبوط آمن حتى الدعم (+{dist_sup_pct}%).'
            })
        elif dist_res_pct <= 5.0 and dist_sup_pct >= 2.0:
            checks.append({
                'id': 'sr_proximity',
                'name': 'قنوات الدعم والمقاومة S/R',
                'status': 'warning',
                'badge': 'متوسط البعد عن المقاومة',
                'value': f'مقاومة: -{dist_res_pct}% | دعم: +{dist_sup_pct}%',
                'detail': f'السعر يبعد بنسبة (-{dist_res_pct}%) عن المقاومة مع هامش متاح للدعم.'
            })
        else:
            checks.append({
                'id': 'sr_proximity',
                'name': 'قنوات الدعم والمقاومة S/R',
                'status': 'danger',
                'badge': 'قاع بيعي غير ملائم',
                'value': f'مقاومة: -{dist_res_pct}% | دعم: +{dist_sup_pct}%',
                'detail': f'السعر بعيد جداً عن المقاومة (-{dist_res_pct}% > 5%) ومقترب من قاع تصحيحي، البيع هنا متأخر وخطر!'
            })



    # Check 4: RSI Momentum Safe Zone

    if side == 'long':

        if rsi >= 75.0:

            checks.append({

                'id': 'rsi_zone',

                'name': 'مؤشر القوة النسبية (RSI 14)',

                'status': 'danger',

                'badge': 'تشبع شرائي مفرط',

                'value': f'RSI: {rsi}',

                'detail': f'مؤشر RSI وصل لمستوى تشبع شرائي حرج ({rsi} >= 75.0)، مما يرفع احتمالية التصحيح الهابط السريع.'

            })

        elif 68.0 < rsi < 75.0:

            checks.append({

                'id': 'rsi_zone',

                'name': 'مؤشر القوة النسبية (RSI 14)',

                'status': 'warning',

                'badge': 'زخم صاعد قوي (يقترب من القمة)',

                'value': f'RSI: {rsi}',

                'detail': f'مؤشر RSI عند {rsi} يعكس زخماً صاعداً قوياً، ولكنه يقترب من مناطق التشبع الشرائي.'

            })

        elif 38.0 <= rsi <= 68.0:

            checks.append({

                'id': 'rsi_zone',

                'name': 'مؤشر القوة النسبية (RSI 14)',

                'status': 'pass',

                'badge': 'نطاق زخم ذهبي',

                'value': f'RSI: {rsi}',

                'detail': f'مؤشر RSI عند {rsi} في المنطقة المثالية المتوازنة لبدء الحركة الصاعدة.'

            })

        else:

            checks.append({

                'id': 'rsi_zone',

                'name': 'مؤشر القوة النسبية (RSI 14)',

                'status': 'warning',

                'badge': 'زخم هابط / تشبع بيعي',

                'value': f'RSI: {rsi}',

                'detail': f'مؤشر RSI عند {rsi}، ما زال الزخم ضعيفاً أو يعاني من ضغط هابط.'

            })

    else:

        if rsi <= 28.0:

            checks.append({

                'id': 'rsi_zone',

                'name': 'مؤشر القوة النسبية (RSI 14)',

                'status': 'danger',

                'badge': 'تشبع بيعي مفرط',

                'value': f'RSI: {rsi}',

                'detail': f'مؤشر RSI وصل لتشبع بيعي مفرط ({rsi} <= 28.0)، خطر ارتداد صاعد مفاجئ ضد صفقة Short.'

            })

        else:

            checks.append({

                'id': 'rsi_zone',

                'name': 'مؤشر القوة النسبية (RSI 14)',

                'status': 'pass',

                'badge': 'نطاق بيعي مناسب',

                'value': f'RSI: {rsi}',

                'detail': f'مؤشر RSI عند {rsi} يدعم حركة الهبوط.'

            })



        # Check 5: Volatility & ATR Risk
    if 0.5 <= atr_pct <= 4.8:
        checks.append({
            'id': 'volatility',
            'name': 'مستوى التقلب والمخاطرة (ATR)',
            'status': 'pass',
            'badge': 'طبيعي وآمن',
            'value': f'ATR: {atr_pct}%',
            'detail': f'نسبة التقلب الحالي ({atr_pct}%) تقع ضمن النطاق المقبول لحماية رأس المال.'
        })
    else:
        checks.append({
            'id': 'volatility',
            'name': 'مستوى التقلب والمخاطرة (ATR)',
            'status': 'warning',
            'badge': 'مخاطرة تقلب',
            'value': f'ATR: {atr_pct}%',
            'detail': f'نسبة التقلب ({atr_pct}%) غير مثالية لحماية رأس المال.'
        })

    # Check 6: MFI Money Flow Liquidity Confirmation
    mfi_conf = strat_settings.get('indicators', {}).get('mfi', {})
    mfi_enabled = mfi_conf.get('enabled', True)
    long_mfi_min = float(mfi_conf.get('long_mfi_min', 45.0))
    long_mfi_max = float(mfi_conf.get('long_mfi_max', 80.0))
    short_mfi_min = float(mfi_conf.get('short_mfi_min', 20.0))
    short_mfi_max = float(mfi_conf.get('short_mfi_max', 55.0))

    if not mfi_enabled:
        checks.append({
            'id': 'mfi_flow',
            'name': 'تدفق السيولة (MFI 14)',
            'status': 'neutral',
            'badge': 'معطل يدوياً',
            'value': f'MFI: {mfi_val}',
            'detail': f'مؤشر MFI معطل من الإعدادات. القيمة الحالية {mfi_val} للعلم فقط.'
        })
    elif side == 'long':
        if mfi_val >= 85.0:
            checks.append({
                'id': 'mfi_flow',
                'name': 'تدفق السيولة (MFI 14)',
                'status': 'danger',
                'badge': 'تشبع سيولة شرائية',
                'value': f'MFI: {mfi_val}',
                'detail': f'مؤشر MFI في منطقة تشبع شرائي مفرط ({mfi_val} >= 85)، مخاطرة انعكاس تصريفي وشيك.'
            })
        elif long_mfi_min <= mfi_val <= long_mfi_max:
            checks.append({
                'id': 'mfi_flow',
                'name': 'تدفق السيولة (MFI 14)',
                'status': 'pass',
                'badge': 'سيولة مؤسسية متدفقة',
                'value': f'MFI: {mfi_val}',
                'detail': f'تدفق السيولة قوي وداعم للصعود ({mfi_val} ضمن النطاق المؤسسي {long_mfi_min}-{long_mfi_max}).'
            })
        else:
            checks.append({
                'id': 'mfi_flow',
                'name': 'تدفق السيولة (MFI 14)',
                'status': 'warning',
                'badge': 'سيولة ضعيفة / غير كافية',
                'value': f'MFI: {mfi_val}',
                'detail': f'تدفق السيولة ضعيف نسبياً ({mfi_val})، أقل من الحد الأدنى للدخول ({long_mfi_min}).'
            })
    else:  # short
        if mfi_val <= 18.0:
            checks.append({
                'id': 'mfi_flow',
                'name': 'تدفق السيولة (MFI 14)',
                'status': 'danger',
                'badge': 'تشبع بيعي مفرط',
                'value': f'MFI: {mfi_val}',
                'detail': f'مؤشر MFI في تشبع بيعي مفرط ({mfi_val} <= 18)، ارتداد صعودي محتمل.'
            })
        elif short_mfi_min <= mfi_val <= short_mfi_max:
            checks.append({
                'id': 'mfi_flow',
                'name': 'تدفق السيولة (MFI 14)',
                'status': 'pass',
                'badge': 'تصريف بيعي مؤكد',
                'value': f'MFI: {mfi_val}',
                'detail': f'تدفق السيولة يؤكد الضغط البيعي ({mfi_val} ضمن نطاق الشورت {short_mfi_min}-{short_mfi_max}).'
            })
        else:
            checks.append({
                'id': 'mfi_flow',
                'name': 'تدفق السيولة (MFI 14)',
                'status': 'warning',
                'badge': 'سيولة بيعية غير مكتملة',
                'value': f'MFI: {mfi_val}',
                'detail': f'مؤشر MFI بيعياً ({mfi_val}) لا يزال مرتفعاً وغير مواتٍ لصفقة بيع.'
            })

    # Composite Scoring & Verdict

    danger_cnt = sum(1 for c in checks if c['status'] == 'danger')

    warn_cnt = sum(1 for c in checks if c['status'] == 'warning')

    pass_cnt = sum(1 for c in checks if c['status'] == 'pass')

    audit_score = int(max(15, min(98, 100 - (danger_cnt * 32) - (warn_cnt * 12))))



    if danger_cnt >= 1:

        verdict = 'صفقة عالية المخاطر (مرفوضة آلياً / غير موصى بها)'

        verdict_badge = 'danger'

        can_enter = False

        alert_msg = '⚠️ اكتشف الفحص الكمي مؤشرات إنهاك حرجة أو تضخماً سعرياً يتعارض مع قواعد الاستراتيجية المؤسسية. الدخول حالياً قد يؤدي إلى خسارة سريعة أو تفعيل خروج إجباري.'

    elif warn_cnt >= 2:

        verdict = 'صفقة متوسطة المخاطر (تحفظات في التوقيت)'

        verdict_badge = 'warning'

        can_enter = True

        alert_msg = 'الصفقة مقبولة فنياً ولكنها تحتوي على بعض التحفظات. الدخول متاح بقرارك اليدوي وإدارتك لرأس المال.'

    else:

        verdict = 'صفقة مؤسسية موصى بها (يقين مرتفع وتوافق الشروط)'

        verdict_badge = 'success'

        can_enter = True

        alert_msg = '✅ جميع الفلاتر الأمنية للمؤشرات مستوفاة بنجاح وتمنح الضوء الأخضر للدخول بنسبة أمان عالية.'



    # Suggested Levels Formatting

    fmt = (lambda p: f'{p:.6f}' if p < 1 else (f'{p:.4f}' if p < 10 else f'{p:.2f}'))

    if side == 'long':

        sl_val = max(cur_price * 0.965, nearest_sup * 0.992) if dist_sup_pct <= 5.0 else cur_price * (1.0 - max(0.02, atr_pct * 0.01 * 1.5))

        sl_pct = round(((cur_price - sl_val) / cur_price) * 100, 2)

        tp1_val = nearest_res * 0.998 if dist_res_pct >= 2.0 else cur_price * (1.0 + max(0.03, sl_pct * 0.01 * 1.6))

        tp1_pct = round(((tp1_val - cur_price) / cur_price) * 100, 2)

        tp2_val = cur_price + (tp1_val - cur_price) * 1.618

        tp2_pct = round(((tp2_val - cur_price) / cur_price) * 100, 2)

    else:

        sl_val = min(cur_price * 1.035, nearest_res * 1.008) if dist_res_pct <= 5.0 else cur_price * (1.0 + max(0.02, atr_pct * 0.01 * 1.5))

        sl_pct = round(((sl_val - cur_price) / cur_price) * 100, 2)

        tp1_val = nearest_sup * 1.002 if dist_sup_pct >= 2.0 else cur_price * (1.0 - max(0.03, sl_pct * 0.01 * 1.6))

        tp1_pct = round(((cur_price - tp1_val) / cur_price) * 100, 2)

        tp2_val = cur_price - (cur_price - tp1_val) * 1.618

        tp2_pct = round(((cur_price - tp2_val) / cur_price) * 100, 2)



    rr_ratio = round(tp1_pct / max(0.5, sl_pct), 2)

    # Multi-Engine Suitability Matrix Calculations
    # 1. Spot Long
    if p_di <= m_di:
        spot_long_score = int(max(15, 45 - (m_di - p_di) * 1.5))
        spot_long_badge = 'danger'
        spot_long_verdict = 'غير مواتية / ضغط بيعي غالب 🛑'
        spot_long_reason = f'قوى البيع (-DI: {m_di}) تسيطر على السوق مقابل (+DI: {p_di})، مخاطرة تراجع في السوق الفوري.'
    elif rsi >= 75.0 or adx >= 48.0:
        spot_long_score = 38
        spot_long_badge = 'warning'
        spot_long_verdict = 'مخاطرة قمة أو إنهاك اتجاهي ⚠️'
        spot_long_reason = f'السوق في مناطق قمة أو إنهاك اتجاهي (RSI: {rsi} | ADX: {adx})، يفضل انتظار التصحيح.'
    elif dist_sup_pct > 6.0:
        spot_long_score = 48
        spot_long_badge = 'warning'
        spot_long_verdict = 'تضخم سعري بعيد عن الدعم ⚠️'
        spot_long_reason = f'السعر يبعد (+{dist_sup_pct}%) عن أرضية الدعم المؤسسي، مخاطرة الشراء مرتفعة.'
    else:
        spot_long_score = int(min(96, max(75, 78 + (2.5 - dist_sup_pct) * 4)))
        spot_long_badge = 'success'
        spot_long_verdict = 'موصى به للشراء الفوري (Spot Long) ✅'
        spot_long_reason = f'شروط حماية رأس المال مستوفاة: ارتداد دعم آمن (+{dist_sup_pct}%) وزخم صاعد متزن.'

    # 2. Futures Long
    if p_di <= m_di:
        fut_long_score = int(max(10, 40 - (m_di - p_di) * 2.0))
        fut_long_badge = 'danger'
        fut_long_verdict = 'مرفوضة للشراء / اتجاه هابط ❌'
        fut_long_reason = f'سيطرة قوى البيع تعرّض صفقات الشراء الآجل لخطر التصفية أو ضرب الوقف السريع.'
    elif adx < adx_min:
        fut_long_score = 42
        fut_long_badge = 'warning'
        fut_long_verdict = 'زخم اتجاهي ضعيف ⚠️'
        fut_long_reason = f'مؤشر ADX عند {adx} يعكس حركة أفقية وتذبذباً ضعيفاً غير ملائم للشراء برافعة.'
    else:
        fut_long_score = int(min(95, max(72, 75 + min(15.0, (adx - 20) * 1.5))))
        fut_long_badge = 'success'
        fut_long_verdict = 'مؤهل للشراء الآجل (Futures Long) 📈'
        fut_long_reason = f'قوى الشراء (+DI: {p_di}) متفوقة والزخم الاتجاهي قوي (ADX: {adx}) مع رافعة 2.0x.'

    # 3. Futures Short (with Dual RSI + MFI Oversold Veto)
    if rsi < 35.0 or mfi_val < 25.0:
        fut_short_score = int(max(10, 28 - max(0, 35 - rsi) - max(0, 25 - mfi_val)))
        fut_short_badge = 'danger'
        fut_short_verdict = 'مرفوضة للبيع / تشبع واستنزاف بيعي 🛑'
        fut_short_reason = f'السوق في ذروة البيع (RSI: {rsi} < 35 | MFI: {mfi_val} < 25)، مخاطرة ارتداد صاعد وشيك ضد صفقة Short.'
    elif p_di > m_di:
        fut_short_score = int(max(10, 40 - (p_di - m_di) * 2.0))
        fut_short_badge = 'danger'
        fut_short_verdict = 'مرفوضة للبيع / اتجاه صاعد ❌'
        fut_short_reason = f'قوى الشراء (+DI: {p_di}) متفوقة على البيع، فتح صفقات بيع معاكس للاتجاه مخاطرة عالية.'
    elif adx < adx_min:
        fut_short_score = 45
        fut_short_badge = 'warning'
        fut_short_verdict = 'زخم بيعي غير كافٍ ⚠️'
        fut_short_reason = f'قوة الاتجاه ADX ({adx}) أقل من عتبة الزخم المطلوبة (22).'
    else:
        fut_short_score = int(min(96, max(75, 78 + min(15.0, (adx - 20) * 1.5) + max(0.0, dist_sup_pct * 1.5))))
        fut_short_badge = 'success'
        fut_short_verdict = 'موصى به للبيع على المكشوف (Futures Short) 📉'
        fut_short_reason = f'قوى البيع (-DI: {m_di}) تسيطر وزخم الهبوط متزن دون تشبع (RSI: {rsi} | MFI: {mfi_val}).'

    suitability_matrix = {
        'spot_long': {
            'engine': 'spot',
            'side': 'long',
            'label': 'Spot الفوري - شراء Long 📈',
            'score': spot_long_score,
            'verdict': spot_long_verdict,
            'badge': spot_long_badge,
            'reason': spot_long_reason
        },
        'futures_long': {
            'engine': 'futures',
            'side': 'long',
            'label': 'Futures الآجل - شراء Long 📈',
            'score': fut_long_score,
            'verdict': fut_long_verdict,
            'badge': fut_long_badge,
            'reason': fut_long_reason
        },
        'futures_short': {
            'engine': 'futures',
            'side': 'short',
            'label': 'Futures الآجل - بيع Short 📉',
            'score': fut_short_score,
            'verdict': fut_short_verdict,
            'badge': fut_short_badge,
            'reason': fut_short_reason
        }
    }

    if fut_short_score >= 70 and fut_short_score > spot_long_score and fut_short_score > fut_long_score:
        best_market_action = f'🎯 التوصية المؤسسية المثلى: دخول صفقة بيع SHORT في العقود الآجلة Futures (يقين {fut_short_score}%)'
        best_action_badge = 'purple'
    elif spot_long_score >= 70 and spot_long_score >= fut_long_score:
        best_market_action = f'🎯 التوصية المؤسسية المثلى: دخول صفقة شراء LONG في السوق الفوري Spot (يقين {spot_long_score}%)'
        best_action_badge = 'emerald'
    elif fut_long_score >= 70:
        best_market_action = f'🎯 التوصية المؤسسية المثلى: دخول صفقة شراء LONG في العقود الآجلة Futures (يقين {fut_long_score}%)'
        best_action_badge = 'cyan'
    else:
        best_market_action = '🛑 التوصية المؤسسية المثلى: تفادي التداول في هذه العملة والاحتفاظ برأس المال كاش 100% USDT'
        best_action_badge = 'amber'

    return {
        'status': 'success',
        'suitability_matrix': suitability_matrix,
        'best_market_action': best_market_action,
        'best_action_badge': best_action_badge,

        'symbol': clean,

        'pair': f'{clean}/USDT' if engine == 'spot' else f'{clean}/USDT:USDT',

        'engine': engine,

        'side': side,

        'cur_price': cur_price,

        'cur_price_str': fmt(cur_price),

        'change_24h': chg_24h,

        'volume_24h_m': vol_24h_m,

        'audit_score': audit_score,

        'verdict': verdict,

        'verdict_badge': verdict_badge,

        'can_enter': can_enter,

        'alert_msg': alert_msg,

        'checks': checks,

        'freqai': ai_metrics,

        'counts': {'pass': pass_cnt, 'warning': warn_cnt, 'danger': danger_cnt},

        'levels': {

            'entry_price': cur_price,

            'entry_price_str': fmt(cur_price),

            'stoploss_price': sl_val,

            'stoploss_price_str': fmt(sl_val),

            'stoploss_pct': sl_pct,

            'tp1_price': tp1_val,

            'tp1_price_str': fmt(tp1_val),

            'tp1_pct': tp1_pct,

            'tp2_price': tp2_val,

            'tp2_price_str': fmt(tp2_val),

            'tp2_pct': tp2_pct,

            'risk_reward_ratio': rr_ratio

        }

    }





@app.get('/api/market/preflight_audit/{pair:path}')

async def get_preflight_audit(pair: str, engine: str = 'spot', side: str = 'long'):

    """

    Returns full quantitative pre-flight audit for the specified pair.

    """

    try:

        res = await asyncio.to_thread(audit_pair_opportunity, pair, engine, side)

        return res

    except Exception as e:

        logger.error(f'Error auditing pair {pair}: {e}')

        raise HTTPException(status_code=500, detail=str(e))





@app.post('/api/market/revitalize_and_enter')

async def revitalize_and_enter(payload: Optional[dict] = None):

    """

    Revitalizes the engines, searches for top opportunities, and automatically enters the best setup.

    """

    try:

        req = payload or {}

        preferred_engine = req.get('engine', 'both').lower()

        min_score = float(req.get('min_score', 65.0))

        auto_enter = bool(req.get('auto_enter', False))



        # Scan Binance

        scan_res = await scan_market_opportunities(preset='all', min_volume=15.0, sort_by='score', limit=12)

        opps = scan_res.get('opportunities', [])

        if not opps:

            return {'status': 'warning', 'message': 'لم يتم العثور على فرص تطابق معايير السيولة'}



        # Check existing open trades to avoid duplicate

        open_spot = set()

        open_fut = set()

        try:

            r_s = requests.get(f'{SPOT_API_URL}/status', auth=API_AUTH, timeout=2.0)

            if r_s.status_code == 200:

                open_spot = {t.get('pair') for t in r_s.json() if t.get('is_open')}

            r_f = requests.get(f'{FUTURES_API_URL}/status', auth=API_AUTH, timeout=2.0)

            if r_f.status_code == 200:

                open_fut = {t.get('pair') for t in r_f.json() if t.get('is_open')}

        except Exception:

            pass



        candidate = None

        target_engine = preferred_engine

        for o in opps:

            b = o['base']

            ps = f'{b}/USDT'

            pf = f'{b}/USDT:USDT'

            if target_engine in ['spot', 'both'] and ps not in open_spot:

                candidate = o

                target_engine = 'spot'

                break

            elif target_engine in ['futures', 'both'] and pf not in open_fut:

                candidate = o

                target_engine = 'futures'

                break



        if not candidate:

            candidate = opps[0]



        base = candidate['base']

        pair_spot = f'{base}/USDT'

        pair_fut = f'{base}/USDT:USDT'

        entry_pair = pair_spot if target_engine == 'spot' else pair_fut

        api_url = SPOT_API_URL if target_engine == 'spot' else FUTURES_API_URL
        # Determine side for futures & appropriate engine
        cand_side = candidate.get('recommended_side')
        if not cand_side:
            cand_side = 'short' if (candidate.get('minus_di', 0) > candidate.get('plus_di', 0) and candidate.get('rsi', 50) <= 65) else 'long'

        target_side = cand_side if target_engine == 'futures' else 'long'
        if cand_side == 'short' and preferred_engine in ['futures', 'both']:
            target_engine = 'futures'
            target_side = 'short'
            entry_pair = pair_fut
            api_url = FUTURES_API_URL



        # Anti-Churn Cooldown Guard (منع تكرار فتح صفقات لنفس العملة وحرق الرسوم)
        try:
            trades_req = requests.get(f"{api_url}/trades?limit=8", auth=API_AUTH, timeout=2.0)
            if trades_req.status_code == 200:
                recent_t_list = trades_req.json()
                for rt in recent_t_list:
                    if rt.get('pair') == entry_pair and rt.get('close_timestamp'):
                        close_sec = rt.get('close_timestamp') / 1000.0
                        sec_passed = time.time() - close_sec
                        # 60 minutes cooldown
                        if sec_passed < 3600:
                            rem_mins = max(1, int((3600 - sec_passed) / 60))
                            return {
                                'status': 'cooldown_active',
                                'entered': False,
                                'engine': target_engine,
                                'pair': entry_pair,
                                'base': base,
                                'message': f'⏳ العملة {base} في فترة تهدئة (Cooldown) بعد إغلاق الصفقة #{rt.get("trade_id")}. متبقي {rem_mins} دقيقة لتفادي حرق الرسوم.'
                            }
        except Exception as e:
            logger.debug(f"Error checking trade cooldown: {e}")

        # FreqAI Consensus Gate (التحقق المسبق من توافق توقع الذكاء الاصطناعي للبوت)
        try:
            c_res = requests.get(f"{api_url}/pair_candles?pair={entry_pair}&timeframe=1h&limit=1", auth=API_AUTH, timeout=2.5)
            if c_res.status_code == 200:
                c_data = c_res.json()
                c_cols = c_data.get('columns', [])
                if '&-s_close' in c_cols:
                    pred_idx = c_cols.index('&-s_close')
                    c_rows = c_data.get('data', [])
                    if c_rows:
                        bot_ai_pred = float(c_rows[-1][pred_idx])
                        if target_engine == 'futures' and target_side == 'short' and bot_ai_pred > 0.002:
                            return {
                                'status': 'consensus_blocked',
                                'entered': False,
                                'engine': 'futures',
                                'pair': entry_pair,
                                'base': base,
                                'message': f'🛑 تم حظر الشورت في {base}: نموذج الذكاء الاصطناعي للبوت يتوقع ارتداداً صاعداً (+{bot_ai_pred*100:.2f}%) والدخول الآن سيؤدي لإغلاق فوري بخسارة!'
                            }
                        elif target_side == 'long' and bot_ai_pred < -0.005:
                            return {
                                'status': 'consensus_blocked',
                                'entered': False,
                                'engine': target_engine,
                                'pair': entry_pair,
                                'base': base,
                                'message': f'🛑 تم حظر الشراء في {base}: نموذج الذكاء الاصطناعي للبوت يتوقع هبوطاً بنسبة ({bot_ai_pred*100:.2f}%)!'
                            }
        except Exception as e:
            logger.debug(f"Error checking FreqAI consensus: {e}")

        # Run Pre-Flight Trade Diagnostic Audit
        audit_res = await asyncio.to_thread(audit_pair_opportunity, base, target_engine, target_side)

        # Safety Guard: If auto-enter is active, do NOT enter a trade that fails risk audit!
        if auto_enter and not audit_res.get('can_enter', True):
            return {
                'status': 'safety_aborted',
                'entered': False,
                'engine': target_engine,
                'pair': entry_pair,
                'base': base,
                'score': candidate.get('score'),
                'message': f'🛑 تم حظر الدخول التلقائي في {base} لأن الفحص الكمي الاستباقي صنفها عالية المخاطر ({audit_res.get("verdict")}). تم حماية رأس المال!'
            }



        # If user has not explicitly confirmed auto_enter, return full audit report for modal confirmation!

        if not auto_enter:

            return {

                'status': 'audit_ready',

                'needs_confirmation': True,

                'engine': target_engine,

                'side': target_side,

                'pair': entry_pair,

                'base': base,

                'price': candidate.get('price'),

                'score': candidate.get('score'),

                'signal': candidate.get('signal'),

                'rsi': candidate.get('rsi'),

                'adx': candidate.get('adx'),

                'dist_sup_pct': candidate.get('dist_sup_pct'),

                'audit': audit_res,

                'message': f'تم فحص واقتناص فرصة {base} (يقين {candidate.get("score")}%). يرجى مراجعة تقرير الفحص المسبق وتأكيد الدخول.'

            }



        # Add to whitelist if needed

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
            body['side'] = target_side



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

                await asyncio.sleep(1.0)



        return {

            'status': 'success' if entered_ok else 'partial',

            'entered': entered_ok,

            'engine': target_engine,

            'pair': entry_pair,

            'base': base,

            'price': candidate.get('price'),

            'score': candidate.get('score'),

            'signal': candidate.get('signal'),

            'rsi': candidate.get('rsi'),

            'adx': candidate.get('adx'),

            'dist_sup_pct': candidate.get('dist_sup_pct'),

            'trade_id': trade_id,

            'error': error_msg,

            'message': f'تم إنعاش النظام بنجاح واقتناص فرصة {base} (يقين {candidate.get("score")}%) والدخول في الصفقة #{trade_id} فورياً!' if entered_ok else f'تم تحليل فرصة {base} لكن المحرك أبلغ: {error_msg}'

        }

    except Exception as e:

        logger.error(f'Error in revitalize_and_enter: {e}')

        raise HTTPException(status_code=500, detail=str(e))





@app.post('/api/market/enter_pair')

async def manual_enter_pair(payload: dict):

    """

    Directly force-enters a specific pair on Spot or Futures.

    Payload: {"pair": "TRX/USDT", "engine": "spot"|"futures", "side": "long"|"short"}

    """

    pair = payload.get('pair', '').strip()

    engine = payload.get('engine', 'spot').lower()

    side = payload.get('side', 'long').lower()



    if not pair:

        raise HTTPException(status_code=400, detail='Missing pair')



    clean = pair.replace('/USDT', '').replace(':USDT', '').replace('USDT', '')

    pair_spot = f'{clean}/USDT'

    pair_fut = f'{clean}/USDT:USDT'

    target_pair = pair_spot if engine == 'spot' else pair_fut

    api_url = SPOT_API_URL if engine == 'spot' else FUTURES_API_URL



    # Ensure in whitelist

    cfg_path = CONFIG_SPOT_PATH if engine == 'spot' else CONFIG_FUTURES_PATH

    cfg = read_json_file(cfg_path)

    wl = cfg.get('exchange', {}).get('pair_whitelist', [])

    if target_pair not in wl:

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



    custom_sl = payload.get('custom_stoploss')

    if custom_sl and float(custom_sl) > 0:

        try:

            ov_path = USER_DATA_DIR / 'active_pair_overrides.json'

            ov_data = read_json_file(ov_path) if ov_path.exists() else {}

            ov_data[target_pair] = {

                'stoploss_price': float(custom_sl),

                'engine': engine,

                'side': side,

                'timestamp': datetime.utcnow().isoformat()

            }

            write_json_atomic(ov_path, ov_data)

        except Exception as ex_ov:

            logger.error(f'Failed to write active_pair_overrides: {ex_ov}')



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

            await asyncio.sleep(1.0)





@app.post('/api/market/remove_pair')

async def remove_pair_from_engine(payload: dict):

    raw_symbol = payload.get('symbol', '').strip().upper()

    engine = payload.get('engine', 'all').lower()



    if not raw_symbol:

        raise HTTPException(status_code=400, detail='Missing symbol')



    clean = raw_symbol.replace('/USDT', '').replace(':USDT', '').replace('USDT', '')

    pair_spot = f'{clean}/USDT'

    pair_futures = f'{clean}/USDT:USDT'



    results = {}



    if engine in ['spot', 'all']:

        cfg = read_json_file(CONFIG_SPOT_PATH)

        wl = cfg.get('exchange', {}).get('pair_whitelist', [])

        if pair_spot in wl:

            wl.remove(pair_spot)

            cfg['exchange']['pair_whitelist'] = wl

            write_json_atomic(CONFIG_SPOT_PATH, cfg)

            try:

                requests.post(f'{SPOT_API_URL}/reload_config', auth=API_AUTH, timeout=3.0)

            except Exception:

                pass

            results['spot'] = f'Removed {pair_spot}'

        else:

            results['spot'] = f'{pair_spot} was not in spot whitelist'



    if engine in ['futures', 'all']:

        cfg = read_json_file(CONFIG_FUTURES_PATH)

        wl = cfg.get('exchange', {}).get('pair_whitelist', [])

        if pair_futures in wl:

            wl.remove(pair_futures)

            cfg['exchange']['pair_whitelist'] = wl

            write_json_atomic(CONFIG_FUTURES_PATH, cfg)

            try:

                requests.post(f'{FUTURES_API_URL}/reload_config', auth=API_AUTH, timeout=3.0)

            except Exception:

                pass

            results['futures'] = f'Removed {pair_futures}'

        else:

            results['futures'] = f'{pair_futures} was not in futures whitelist'



    return {'status': 'success', 'results': results}





@app.get('/api/market/tracked_pairs')

async def get_tracked_pairs():

    cfg_spot = read_json_file(CONFIG_SPOT_PATH)

    cfg_fut = read_json_file(CONFIG_FUTURES_PATH)

    spot_wl = cfg_spot.get('exchange', {}).get('pair_whitelist', [])

    fut_wl = cfg_fut.get('exchange', {}).get('pair_whitelist', [])

    return {

        'spot': spot_wl,

        'spot_count': len(spot_wl),

        'futures': fut_wl,

        'futures_count': len(fut_wl)

    }





@app.post('/api/market/download_data')

async def trigger_download_data(payload: dict):

    pairs = payload.get('pairs', [])

    engine = payload.get('engine', 'all')

    

    def run_dl():

        try:

            if engine in ['spot', 'all']:

                cmd = ['docker', 'exec', 'freqtrade_spot_engine', 'freqtrade', 'download-data', '--timeframes', '1h', '4h', '--timerange', '20260101-']

                if pairs:

                    spot_p = [p.replace(':USDT', '') for p in pairs]

                    cmd.extend(['--pairs'] + spot_p)

                subprocess.run(cmd, capture_output=True, text=True, timeout=180)

            if engine in ['futures', 'all']:

                cmd = ['docker', 'exec', 'freqtrade_futures_engine', 'freqtrade', 'download-data', '--trading-mode', 'futures', '--timeframes', '1h', '4h', '--timerange', '20260101-']

                if pairs:

                    fut_pairs = [p if ':USDT' in p else f'{p}:USDT' for p in pairs]

                    cmd.extend(['--pairs'] + fut_pairs)

                subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        except Exception as e:

            logger.error(f'Error in manual data download: {e}')



    t = threading.Thread(target=run_dl, daemon=True)

    t.start()

    return {'status': 'started', 'message': 'بدء تنزيل البيانات في الخلفية'}





# Main Entry Point

# =============================================================================



# =============================================================================
# Continuous Auto-Pilot Sniper Engine (نظام القناص الآلي المستمر)
# =============================================================================
auto_sniper_state = {
    "enabled": False,
    "status": "stopped",       # "active" or "stopped"
    "interval_seconds": 120,   # scans every 2 minutes or upon candle completion
    "last_scan_time": None,
    "last_sniped_pair": None,
    "last_sniped_action": None,
    "sniped_trades_count": 0,
    "scans_count": 0,
    "log_history": []
}
_auto_sniper_task = None

async def auto_sniper_worker():
    """
    Continuous background loop that scans the market and snipes qualified opportunities.
    """
    logger.info("⚡ [Auto-Sniper] Continuous engine started.")
    auto_sniper_state["status"] = "active"
    auto_sniper_state["enabled"] = True
    
    while auto_sniper_state["enabled"]:
        try:
            auto_sniper_state["scans_count"] += 1
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            auto_sniper_state["last_scan_time"] = now_str
            
            # Execute market revitalization & scan
            res = await revitalize_and_enter(payload={"engine": "both", "min_score": 68.0, "auto_enter": True})
            
            if res.get("status") == "success" and res.get("entered"):
                pair = res.get("pair")
                side = res.get("side", "long")
                eng = res.get("engine", "spot")
                auto_sniper_state["sniped_trades_count"] += 1
                auto_sniper_state["last_sniped_pair"] = pair
                auto_sniper_state["last_sniped_action"] = f"{eng.upper()} {side.upper()} @ ${res.get('price')}"
                log_msg = f"[{now_str}] 🎯 تم اقتناص صفقة {pair} ({eng.upper()} - {side.upper()}) بسعر ${res.get('price')} بنجاح!"
                auto_sniper_state["log_history"].insert(0, log_msg)
                logger.info(f"⚡ [Auto-Sniper] {log_msg}")
            else:
                msg = res.get("message", "فحص دوري: لا توجد فرص تتجاوز عتبة الأمان حالياً")
                auto_sniper_state["log_history"].insert(0, f"[{now_str}] 🔍 {msg}")
            
            # Keep history trimmed
            auto_sniper_state["log_history"] = auto_sniper_state["log_history"][:30]
            
        except Exception as e:
            logger.error(f"Error in auto_sniper_worker: {e}")
            auto_sniper_state["log_history"].insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ خطأ أثناء الفحص: {e}")
        
        # Sleep interval (120 seconds, checking cancellation periodically)
        for _ in range(24):  # 24 * 5s = 120s
            if not auto_sniper_state["enabled"]:
                break
            await asyncio.sleep(5)
            
    auto_sniper_state["status"] = "stopped"
    logger.info("⏸️ [Auto-Sniper] Continuous engine stopped.")

@app.post("/api/market/auto_sniper/toggle")
async def toggle_auto_sniper(payload: Optional[dict] = None):
    global _auto_sniper_task
    req = payload or {}
    req_enable = req.get("enabled")
    if req_enable is None:
        new_state = not auto_sniper_state["enabled"]
    else:
        new_state = bool(req_enable)
        
    if new_state and not auto_sniper_state["enabled"]:
        auto_sniper_state["enabled"] = True
        _auto_sniper_task = asyncio.create_task(auto_sniper_worker())
        msg = "تم تفعيل وضع القناص الآلي المستمر بنجاح! سيعمل النظام دورياً لاقتناص أي فرصة مستوفاة للشروط المؤسسية."
    elif not new_state and auto_sniper_state["enabled"]:
        auto_sniper_state["enabled"] = False
        if _auto_sniper_task and not _auto_sniper_task.done():
            _auto_sniper_task.cancel()
        auto_sniper_state["status"] = "stopped"
        msg = "تم إيقاف وضع القناص الآلي المستمر. النظام الآن في الوضع اليدوي."
    else:
        msg = f"القناص الآلي بالفعل {'نشط' if auto_sniper_state['enabled'] else 'متوقف'}."

    return {
        "status": "success",
        "enabled": auto_sniper_state["enabled"],
        "sniper_state": auto_sniper_state,
        "message": msg
    }

@app.get("/api/market/auto_sniper/status")
async def get_auto_sniper_status():
    return {
        "status": "success",
        "enabled": auto_sniper_state["enabled"],
        "sniper_state": auto_sniper_state
    }


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Institutional Quant Fund Dashboard")

    parser.add_argument("--host", default="0.0.0.0", help="Host IP to bind to")

    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")

    args = parser.parse_args()



    import uvicorn

    logger.info(f"Starting Institutional Quant Fund Dashboard on http://localhost:{args.port}")

    uvicorn.run("server:app", host=args.host, port=args.port, reload=False, log_level="info")

