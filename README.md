# 🏛️ Crypto Institutional Quant Fund
### Production-Grade Dual-Engine Algorithmic Trading & Investment System (FreqAI + Freqtrade)

[![Trading Mode](https://img.shields.io/badge/Engines-Spot%20%26%20Futures-blue.svg)](#)
[![Docker Orchestration](https://img.shields.io/badge/Docker%20Compose-Dual%20Isolated%20Containers-green.svg)](#)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-FreqAI%20CatBoost%20Ensemble-orange.svg)](#)
[![Leakage Guard](https://img.shields.io/badge/Data%20Integrity-Zero%20Lookahead%20Causal-success.svg)](#)
[![License: Private/MIT](https://img.shields.io/badge/License-Proprietary%20Quant-lightgrey.svg)](#)

---

> [!IMPORTANT]
> 📖 **للاطلاع على الدليل الشامل والمبسط باللغة العربية (شرح الفلسفة الاستثمارية، طريقة التشغيل خطوة بخطوة، وإدارة المخاطر):**  
> راجع وثيقة: [**الدليل المعماري والتشغيلي (SYSTEM_ARCHITECTURE_AR.md)**](SYSTEM_ARCHITECTURE_AR.md)

---

## 🌟 Overview

**Crypto Institutional Quant Fund** is an end-to-end, institutional-grade quantitative trading framework designed to operate as an all-weather crypto investment fund. 

It runs on top of **Freqtrade** and its **FreqAI** machine learning subsystem, utilizing a **Dual-Engine Architecture** to achieve capital accumulation and tactical alpha generation simultaneously:
1. **Spot Engine (Port 8080):** Zero-leverage, capital preservation, long-only asset accumulation (BTC, ETH, SOL).
2. **Futures Engine (Port 8081):** Long & Short tactical execution with strict risk-bounded leverage (up to 2.0x) and dynamic hedging against bear markets.

---

## 🏗️ Architecture Blueprint

```text
Crypto-Institutional-Quant-Fund/
├── docker-compose.yml                      # Dual-container orchestration
├── .env.example                            # API keys & Telegram template
├── SYSTEM_ARCHITECTURE_AR.md               # Complete Arabic manual
├── README.md                               # Project documentation
│
├── download_data.bat / .ps1                # Batch downloader for 1h/4h OHLCV data
├── run_backtest_spot.bat / .ps1            # FreqAI Walk-Forward backtest for Spot
├── run_backtest_futures.bat / .ps1         # FreqAI Walk-Forward backtest for Futures
├── start_all_engines.bat / .ps1            # Launches both engines simultaneously
├── stop_all_engines.bat / .ps1             # Graceful shutdown script
│
└── user_data/
    ├── config_spot.json                    # Spot configuration & FreqAI parameters
    ├── config_futures.json                 # Futures configuration & Shorting rules
    ├── strategies/
    │   └── InstitutionalDualStrategy.py    # Unified Causal Strategy for Spot & Futures
    └── data/                               # Downloaded market data storage
```

---

## ⚡ Quickstart

### 1. Requirements
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- Windows 10/11 or Linux.

### 2. Download Historical Market Data
Double-click `download_data.bat` or run in PowerShell:
```powershell
.\download_data.ps1
```

### 3. Run Backtest
```powershell
.\run_backtest_spot.ps1
.\run_backtest_futures.ps1
```

### 4. Launch Dual Engines (Dry-Run Mode)
```powershell
.\start_all_engines.ps1
```
Access the web dashboards:
- **Spot Dashboard:** [http://localhost:8080](http://localhost:8080)
- **Futures Dashboard:** [http://localhost:8081](http://localhost:8081)
- **Default Credentials:** Username: `fund_admin` | Password: `InstitutionalQuant2026!`

---

## 🛡️ Key Risk Features
- **Strict Causal Feature Engineering:** Zero lookahead leakage across all timeframes.
- **Dissimilarity Index (DI) Filter:** Rejects trades during black swan events and unseen market regimes.
- **Dynamic ATR Trailing Stop:** Protects capital and locks in profits automatically.
- **Institutional Leverage Policy:** Hard-capped at 2.0x max on Futures to eliminate liquidation risk.
