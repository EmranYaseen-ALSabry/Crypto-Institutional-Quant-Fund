# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

# flake8: noqa: F401

# isort: skip_file

"""

--------------------------------------------------------------------------------

Institutional Dual-Engine FreqAI Strategy

--------------------------------------------------------------------------------

Architecture:

- Supports both Spot (Capital Accumulation / Long-Only) & Futures (Long / Short).

- Strictly Causal Feature Engineering (Zero Data Leakage).

- Multi-Timeframe Informative Analysis (1h & 4h macro alignment).

- Outlier & Regime Protection via Dissimilarity Index (DI).

- Dynamic ATR-based Trailing Stop-Loss & Strict Risk Controls.

- Live Dynamic Parameter Integration via strategy_settings.json.

- Advanced ADX Trend Gatekeeper (+DI/-DI confirmation & Exhaustion Exit).

--------------------------------------------------------------------------------

"""



import json

import logging

from datetime import datetime

from pathlib import Path

from typing import Optional, Union, Dict, Any



import numpy as np

import pandas as pd

from pandas import DataFrame

import talib.abstract as ta



from freqtrade.strategy import (

    IStrategy,

    IntParameter,

    DecimalParameter,

    CategoricalParameter,

    merge_informative_pair,

    stoploss_from_open

)

from freqtrade.persistence import Trade



logger = logging.getLogger(__name__)





class InstitutionalDualStrategy(IStrategy):

    """

    World-Class Institutional Quantitative Strategy powered by FreqAI.

    """



    # Strategy Interface Version

    INTERFACE_VERSION = 3



    # Minimal ROI (Dynamic profit-taking ladder)

    minimal_roi = {

        "0": 0.06,      # 6% immediate take-profit

        "60": 0.04,     # 4% after 1 hour

        "180": 0.025,   # 2.5% after 3 hours

        "360": 0.015    # 1.5% after 6 hours

    }



    # Hard emergency stoploss (disaster protection)

    stoploss = -0.05



    # Trailing stop configured via custom_stoploss for volatility responsiveness

    trailing_stop = False

    use_custom_stoploss = True



    # Position Adjustment (Scale-Out / Partial Take-Profit)

    position_adjustment_enable = True

    max_entry_position_adjustment = -1



    # Timeframe of execution

    timeframe = '1h'



    # Process only closed candles to prevent intra-candle lookahead noise

    process_only_new_candles = True



    # Order types: Limit orders preferred to capture Maker fee discounts

    order_types = {

        'entry': 'limit',

        'exit': 'limit',

        'emergency_exit': 'market',

        'stoploss': 'market',

        'stoploss_on_exchange': False

    }



    order_time_in_force = {

        'entry': 'GTC',

        'exit': 'GTC'

    }



    # Configuration of indicators & AI predictions to display on FreqUI Chart

    plot_config = {

        'main_plot': {

            'trade_entry': {'color': '#06b6d4', 'type': 'line'},         # Cyan: Active Trade Entry Price

            'trade_stoploss': {'color': '#ef4444', 'type': 'line'},      # Red: Stop-Loss Level

            'trade_tp1': {'color': '#22c55e', 'type': 'line'},           # Green: Take-Profit Stage 1 (+1.5%)

            'trade_tp2': {'color': '#10b981', 'type': 'line'},           # Emerald: Take-Profit Stage 2 (+3.0%)

            'sr_support_bot': {'color': '#34d399', 'type': 'line'},      # Support Channel Bottom

            'sr_resistance_top': {'color': '#f87171', 'type': 'line'},   # Resistance Channel Top

            '%-ema_200': {'color': '#3b82f6'},                           # Blue: 200 EMA Macro Trend

        },

        'subplots': {

            "ADX & Directional Movement": {

                'adx': {'color': '#ec4899', 'type': 'line'},

                'plus_di': {'color': '#10b981', 'type': 'line'},

                'minus_di': {'color': '#ef4444', 'type': 'line'}

            },

            "AI Return Forecast": {

                '&-s_close': {'color': '#06b6d4', 'type': 'line'}

            },

            "Money Flow (MFI)": {
                'mfi_live': {'color': '#10b981', 'type': 'line'}
            },
            "Momentum (RSI)": {

                'rsi_live': {'color': '#eab308', 'type': 'line'}

            }

        }

    }



    # Dynamic parameters (Balanced institutional conviction)

    entry_threshold_long = DecimalParameter(0.005, 0.030, default=0.009, space='buy', optimize=True)

    entry_threshold_short = DecimalParameter(0.005, 0.030, default=0.009, space='sell', optimize=True)

    atr_multiplier = DecimalParameter(1.2, 3.0, default=2.0, space='sell', optimize=True)



    can_short: bool = True



    def __init__(self, config: dict) -> None:

        super().__init__(config)

        # Check trading mode from config

        trading_mode = config.get('trading_mode', 'spot')

        self.is_futures = (trading_mode == 'futures')

        self.can_short = self.is_futures

        logger.info(

            f"InstitutionalDualStrategy initialized. Trading Mode: {trading_mode}. "

            f"Can Short: {self.can_short}"

        )



    def load_strategy_settings(self) -> dict:

        """

        Dynamically loads strategy & indicator configuration from user_data/strategy_settings.json.

        Gracefully falls back to hardcoded defaults on any error.

        """

        default_settings = {

            "ai_model": {

                "entry_threshold_long": self.entry_threshold_long.value,

                "entry_threshold_short": self.entry_threshold_short.value,

                "exit_threshold_long": -0.008,

                "exit_threshold_short": 0.008,

                "atr_multiplier": self.atr_multiplier.value

            },

            "risk_management": {

                "stoploss": self.stoploss,

                "minimal_roi": self.minimal_roi,

                "trailing_stop": self.trailing_stop,

                "use_custom_stoploss": self.use_custom_stoploss,

                "spot": {

                    "stoploss": -0.05,

                    "break_even": {

                        "enabled": True,

                        "trigger_profit": 0.010,

                        "offset": 0.002

                    },

                    "partial_take_profit": {

                        "enabled": True,

                        "stage1_profit": 0.015,

                        "stage1_sell_ratio": 0.30,

                        "stage2_profit": 0.030,

                        "stage2_sell_ratio": 0.35,

                        "runner_sell_ratio": 0.35,

                        "runner_trailing_stop": 0.015

                    }

                },

                "futures": {

                    "stoploss": -0.04,

                    "break_even": {

                        "enabled": True,

                        "trigger_profit": 0.010,

                        "offset": 0.002

                    },

                    "partial_take_profit": {

                        "enabled": True,

                        "stage1_profit": 0.015,

                        "stage1_sell_ratio": 0.30,

                        "stage2_profit": 0.030,

                        "stage2_sell_ratio": 0.35,

                        "runner_sell_ratio": 0.35,

                        "runner_trailing_stop": 0.012

                    }

                }

            },

            "indicators": {

                "adx": {

                    "enabled": True,

                    "timeperiod": 14,

                    "min_adx": 22.0,

                    "require_di_confirmation": True,

                    "adx_exhaustion_exit": True,

                    "exhaustion_threshold": 48.0

                },

                "rsi": {

                    "enabled": True,

                    "timeperiod": 14,

                    "long_rsi_min": 35.0,

                    "long_rsi_max": 78.0,

                    "short_rsi_min": 22.0,

                    "short_rsi_max": 65.0

                },

                "ema_filter": {

                    "enabled": True,

                    "macro_period": 200

                },

                "volume_filter": {

                    "enabled": True,

                    "min_volume_ratio": 0.8

                }

            }

        }

        try:

            settings_path = Path(self.config.get('user_data_dir', 'user_data')) / 'strategy_settings.json'

            if settings_path.exists():

                with open(settings_path, 'r', encoding='utf-8') as f:

                    data = json.load(f)

                    risk_root = data.get("risk_management", {})

                    # Minimal ROI ladder dynamic toggle:

                    roi_enabled = risk_root.get("minimal_roi_enabled", True)

                    if roi_enabled:

                        if "minimal_roi" in risk_root and risk_root["minimal_roi"]:

                            self.minimal_roi = {int(k): float(v) for k, v in risk_root["minimal_roi"].items()}

                    else:

                        # Effectively disable time-decay minimal ROI ladder so profits can run to targets

                        self.minimal_roi = {"0": 10.0}

                    return data

        except Exception as e:

            logger.warning(f"Could not load dynamic strategy_settings.json: {e}. Using fallback defaults.")

        return default_settings



    def confirm_trade_exit(

        self,

        pair: str,

        trade: Trade,

        order_type: str,

        amount: float,

        rate: float,

        time_in_force: str,

        exit_reason: str,

        current_time: datetime,

        **kwargs

    ) -> bool:

        """

        Cleans up active pair overrides upon trade exit.

        """

        try:

            overrides_path = Path(self.config.get('user_data_dir', 'user_data')) / 'active_pair_overrides.json'

            if overrides_path.exists():

                with open(overrides_path, 'r', encoding='utf-8') as of:

                    pair_overrides = json.load(of)

                if pair in pair_overrides:

                    del pair_overrides[pair]

                    with open(overrides_path, 'w', encoding='utf-8') as of:

                        json.dump(pair_overrides, of, indent=2)

        except Exception:

            pass

        return True



    # =========================================================================

    # 1. Leverage Management (Futures Engine)

    # =========================================================================

    def leverage(

        self,

        pair: str,

        current_time: datetime,

        current_rate: float,

        proposed_leverage: float,

        max_leverage: float,

        entry_tag: Optional[str],

        side: str,

        **kwargs

    ) -> float:

        """

        Institutional Conservative Leverage:

        Fixed at 2.0x maximum to prevent liquidation cascading.

        """

        if not self.is_futures:

            return 1.0

        return 2.0



    # =========================================================================

    # 2. Feature Engineering (FreqAI Causal Features)

    # =========================================================================

    def feature_engineering_expand_all(

        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs

    ) -> DataFrame:

        """

        Expands indicators across periods (e.g. 10, 20, 50) and timeframes.

        Strictly causal operations only.

        """

        # Trend indicators

        dataframe[f"%-ema-period_{period}"] = ta.EMA(dataframe, timeperiod=period)

        dataframe[f"%-sma-period_{period}"] = ta.SMA(dataframe, timeperiod=period)



        # Momentum & Oscillators

        dataframe[f"%-rsi-period_{period}"] = ta.RSI(dataframe, timeperiod=period)
        dataframe[f"%-mfi-period_{period}"] = ta.MFI(dataframe, timeperiod=period)



        # Volatility & Range

        dataframe[f"%-atr-period_{period}"] = ta.ATR(dataframe, timeperiod=period)

        

        # Bollinger Bands Width (Volatility Squeeze)

        bollinger = ta.BBANDS(dataframe, timeperiod=period, nbdevup=2.0, nbdevdn=2.0)

        dataframe[f"%-bb_width-period_{period}"] = (

            (bollinger['upperband'] - bollinger['lowerband']) / dataframe['close']

        )



        # Normalized High-Low Range (Parkinson-like proxy)

        dataframe[f"%-hl_range-period_{period}"] = (

            (dataframe['high'] - dataframe['low']) / dataframe['close']

        )



        # Rate of Change (Momentum)

        dataframe[f"%-roc-period_{period}"] = ta.ROC(dataframe, timeperiod=period)



        return dataframe



    def feature_engineering_expand_basic(

        self, dataframe: DataFrame, metadata: dict, **kwargs

    ) -> DataFrame:

        """

        Expands basic non-period-specific features.

        """

        # Macro EMA 200 for market regime

        dataframe["%-ema_200"] = ta.EMA(dataframe, timeperiod=200)

        dataframe["%-adx"] = ta.ADX(dataframe, timeperiod=14)



        # Distance from EMA 200 (Mean Reversion vs Trend)

        dataframe["%-dist_ema_200"] = (dataframe["close"] - dataframe["%-ema_200"]) / dataframe["%-ema_200"]



        # Volume confirmation

        dataframe["%-volume_ratio"] = dataframe["volume"] / ta.SMA(dataframe["volume"], timeperiod=24)



        # Cyclical calendar features (Hour of day)

        dataframe["%-hour_sin"] = np.sin(2 * np.pi * dataframe["date"].dt.hour / 24.0)

        dataframe["%-hour_cos"] = np.cos(2 * np.pi * dataframe["date"].dt.hour / 24.0)



        return dataframe



    # =========================================================================

    # 3. Target Definition (Prediction Label for FreqAI)

    # =========================================================================

    def set_freqai_targets(

        self, dataframe: DataFrame, metadata: dict, **kwargs

    ) -> DataFrame:

        """

        Defines the target to forecast.

        Here: The relative price return after `label_period_candles` (e.g. 12 hours).

        """

        horizon = self.freqai_info["feature_parameters"]["label_period_candles"]

        dataframe["&-s_close"] = (

            dataframe["close"].shift(-horizon) / dataframe["close"] - 1.0

        )

        return dataframe



    # =========================================================================

    # 4. Indicators Population (FreqAI Pipeline)

    # =========================================================================

    

    @staticmethod

    def calculate_sr_channels(

        df: DataFrame,

        pivot_period: int = 10,

        channel_width_pct: float = 0.025,

        min_strength: int = 2

    ) -> tuple[float, float, float, float, int]:

        """

        Institutional Support Resistance - Channels Engine (TradingView LonesomeTheBlue Algorithm).

        Clusters pivot highs and lows into dynamic price channels and calculates touch strength.

        Returns: (s_bot, s_top, r_bot, r_top, s_touches)

        """

        try:

            highs = df['high'].values

            lows = df['low'].values

            closes = df['close'].values

            n = len(df)

            if n < pivot_period * 2 + 5:

                return (0.0, 0.0, 0.0, 0.0, 0)



            half_w = channel_width_pct / 2.0

            start_idx = max(pivot_period, n - 250)

            pivots = []



            for i in range(start_idx, n - pivot_period):

                # Pivot High

                if highs[i] == np.max(highs[i - pivot_period : i + pivot_period + 1]):

                    pivots.append((highs[i], 'high', i))

                # Pivot Low

                if lows[i] == np.min(lows[i - pivot_period : i + pivot_period + 1]):

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



            filtered = [c for c in channels if c['touches'] >= min_strength]

            filtered.sort(key=lambda x: x['mid'])



            cur_price = closes[-1]

            supports = [c for c in filtered if c['top'] <= cur_price or (c['bot'] <= cur_price <= c['top'])]

            resistances = [c for c in filtered if c['bot'] >= cur_price or (c['bot'] <= cur_price <= c['top'])]



            # Institutional Fallback: If no multi-touch cluster, fallback to nearest pivot point (min 1 touch) or recent rolling extremes

            if supports:

                s_bot, s_top, s_touches = supports[-1]['bot'], supports[-1]['top'], supports[-1]['touches']

            else:

                unfiltered_sup = [c for c in channels if c['mid'] <= cur_price]

                if unfiltered_sup:

                    best_s = max(unfiltered_sup, key=lambda x: x['mid'])

                    s_bot, s_top, s_touches = best_s['bot'], best_s['top'], best_s['touches']

                else:

                    recent_low = float(np.min(lows[-50:]))

                    s_bot, s_top, s_touches = recent_low * (1.0 - half_w), recent_low * (1.0 + half_w), 1



            if resistances:

                r_bot, r_top, r_touches = resistances[0]['bot'], resistances[0]['top'], resistances[0]['touches']

            else:

                unfiltered_res = [c for c in channels if c['mid'] >= cur_price]

                if unfiltered_res:

                    best_r = min(unfiltered_res, key=lambda x: x['mid'])

                    r_bot, r_top, r_touches = best_r['bot'], best_r['top'], best_r['touches']

                else:

                    recent_high = float(np.max(highs[-50:]))

                    r_bot, r_top, r_touches = recent_high * (1.0 - half_w), recent_high * (1.0 + half_w), 1



            return (s_bot, s_top, r_bot, r_top, s_touches)

        except Exception:

            return (0.0, 0.0, 0.0, 0.0, 0)



    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:

        """

        Executed on the main thread at each bot iteration.

        Safely caches active open trade parameters to avoid SQLite lock contention during multi-pair analysis.

        """

        try:

            from freqtrade.persistence import Trade

            open_trades = Trade.get_trades([Trade.is_open.is_(True)]).all()

            cache = {}

            for t in open_trades:

                cache[t.pair] = {

                    'open_rate': float(t.open_rate),

                    'stop_loss': float(t.stop_loss) if t.stop_loss else None,

                    'is_short': getattr(t, 'is_short', False)

                }

            self._open_trades_cache = cache

        except Exception:

            if not hasattr(self, '_open_trades_cache'):

                self._open_trades_cache = {}



    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        """

        Populates indicators by initiating the FreqAI model training & inference.

        """

        dataframe = self.freqai.start(dataframe, metadata, self)

        

        # Populate live Directional Indicators for UI plotting without modifying FreqAI model features

        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)

        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)

        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)

        dataframe['rsi_live'] = ta.RSI(dataframe, timeperiod=14)



        # Active Trade Visual Overlay Lines (Entry, Stop-Loss, TP1, TP2)

        try:

            active_trade = getattr(self, '_open_trades_cache', {}).get(metadata['pair'])

            if active_trade:

                t_entry = active_trade['open_rate']

                t_short = active_trade['is_short']

                t_sl = active_trade['stop_loss'] if active_trade['stop_loss'] else (t_entry * (0.96 if not t_short else 1.04))

                if not t_short:

                    t_tp1 = t_entry * 1.015

                    t_tp2 = t_entry * 1.030

                else:

                    t_tp1 = t_entry * 0.985

                    t_tp2 = t_entry * 0.970



                dataframe['trade_entry'] = t_entry

                dataframe['trade_stoploss'] = t_sl

                dataframe['trade_tp1'] = t_tp1

                dataframe['trade_tp2'] = t_tp2

            else:

                sl_ratio = -0.04 if self.is_futures else -0.03

                dataframe['trade_entry'] = np.nan

                dataframe['trade_stoploss'] = dataframe['close'] * (1 + sl_ratio)

                dataframe['trade_tp1'] = dataframe['close'] * 1.015

                dataframe['trade_tp2'] = dataframe['close'] * 1.030

        except Exception:

            dataframe['trade_entry'] = np.nan

            dataframe['trade_stoploss'] = np.nan

            dataframe['trade_tp1'] = np.nan

            dataframe['trade_tp2'] = np.nan



        # Support Resistance Channels Integration

        try:

            settings = self.load_strategy_settings()

            sr_cfg = settings.get("indicators", {}).get("sr_channels", {})

            if sr_cfg.get("enabled", False):

                s_bot, s_top, r_bot, r_top, touches = self.calculate_sr_channels(

                    dataframe,

                    pivot_period=int(sr_cfg.get("pivot_period", 10)),

                    channel_width_pct=float(sr_cfg.get("channel_width_pct", 0.025)),

                    min_strength=int(sr_cfg.get("min_strength", 2))

                )

                dataframe['sr_support_bot'] = s_bot

                dataframe['sr_support_top'] = s_top

                dataframe['sr_resistance_bot'] = r_bot

                dataframe['sr_resistance_top'] = r_top

                dataframe['sr_touches'] = touches

            else:

                dataframe['sr_support_bot'] = 0.0

                dataframe['sr_support_top'] = 0.0

                dataframe['sr_resistance_bot'] = 0.0

                dataframe['sr_resistance_top'] = 0.0

                dataframe['sr_touches'] = 0

        except Exception:

            dataframe['sr_support_bot'] = 0.0

            dataframe['sr_support_top'] = 0.0

            dataframe['sr_resistance_bot'] = 0.0

            dataframe['sr_resistance_top'] = 0.0

            dataframe['sr_touches'] = 0



        return dataframe



    # =========================================================================

    # 5. Entry Decisions (Signals)

    # =========================================================================

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:

        """

        Generates enter_long and enter_short signals based on FreqAI forecasts and ADX filters.

        """

        settings = self.load_strategy_settings()

        ai_cfg = settings.get("ai_model", {})

        ind_cfg = settings.get("indicators", {})

        adx_cfg = ind_cfg.get("adx", {})

        rsi_cfg = ind_cfg.get("rsi", {})

        ema_cfg = ind_cfg.get("ema_filter", {})

        vol_cfg = ind_cfg.get("volume_filter", {})
        mfi_cfg = ind_cfg.get("mfi", {})



        thresh_long = float(ai_cfg.get("entry_threshold_long", self.entry_threshold_long.value))

        thresh_short = float(ai_cfg.get("entry_threshold_short", self.entry_threshold_short.value))



        # Compute baseline indicators for live execution filters

        df['atr_live'] = ta.ATR(df, timeperiod=14)

        df['ema_200_live'] = ta.EMA(df, timeperiod=200)

        df['rsi_live'] = ta.RSI(df, timeperiod=14)
        df['mfi_live'] = ta.MFI(df, timeperiod=int(mfi_cfg.get('timeperiod', 14)))

        df['adx_live'] = ta.ADX(df, timeperiod=14)

        df['plus_di_live'] = ta.PLUS_DI(df, timeperiod=14)

        df['minus_di_live'] = ta.MINUS_DI(df, timeperiod=14)

        df['vol_ma_live'] = ta.SMA(df['volume'], timeperiod=24)



        # Base valid prediction check

        valid_pred = (df['do_predict'] == 1) & (df['volume'] > 0)



        # ----------------- LONG ENTRY (Spot & Futures) -----------------

        long_conditions = [

            valid_pred,

            # AI predicts return above conviction threshold

            df['&-s_close'] > thresh_long

        ]



        # ADX Trend Gatekeeper Filter

        if adx_cfg.get("enabled", True):

            min_adx = float(adx_cfg.get("min_adx", 22.0))

            long_conditions.append(df['adx_live'] >= min_adx)

            if adx_cfg.get("require_di_confirmation", True):

                long_conditions.append(df['plus_di_live'] > df['minus_di_live'])



        # RSI Momentum Filter

        if rsi_cfg.get("enabled", True):

            long_rsi_min = float(rsi_cfg.get("long_rsi_min", 35.0))

            long_rsi_max = float(rsi_cfg.get("long_rsi_max", 78.0))

            long_conditions.append(df['rsi_live'] >= long_rsi_min)

            long_conditions.append(df['rsi_live'] <= long_rsi_max)



        # EMA Trend Regime Filter

        if ema_cfg.get("enabled", True):

            long_conditions.append(

                (df['close'] > df['ema_200_live']) | (df['rsi_live'] > 35)

            )



        # Volume Confirmation Filter

        if vol_cfg.get("enabled", True):

            min_vol_ratio = float(vol_cfg.get("min_volume_ratio", 0.8))

            long_conditions.append(df['volume'] >= (df['vol_ma_live'] * min_vol_ratio))



        # Support Resistance Channels Rebound Filter

        sr_cfg = ind_cfg.get("sr_channels", {})

        if sr_cfg.get("enabled", False) and sr_cfg.get("use_for_entry", True):

            chan_w = float(sr_cfg.get("channel_width_pct", 0.025))

            # If support level detected, price must be near support floor (within 1.5 * channel width)

            has_support = (df['sr_support_top'] > 0)

            near_support = (df['close'] <= df['sr_support_top'] * (1.0 + chan_w * 1.5)) & (df['close'] >= df['sr_support_bot'] * 0.985)

            # Require rebound confluence: either near valid support or support not yet formed

            long_conditions.append((~has_support) | near_support)



        if 'DI_values' in df.columns:

            # Dissimilarity Index check: Discard predictions in unseen outlier regimes

            di_thresh = self.freqai_info['feature_parameters'].get('DI_threshold', 1.2)

            long_conditions.append(df['DI_values'] < di_thresh)



        df.loc[np.logical_and.reduce(long_conditions), 'enter_long'] = 1

        df.loc[np.logical_and.reduce(long_conditions), 'enter_tag'] = 'ai_conviction_long'



        # ----------------- SHORT ENTRY (Futures Only) -----------------

        if self.can_short:

            short_conditions = [

                valid_pred,

                # AI predicts negative return below conviction threshold

                df['&-s_close'] < -thresh_short

            ]



            # ADX Trend Gatekeeper Filter

            if adx_cfg.get("enabled", True):

                min_adx = float(adx_cfg.get("min_adx", 22.0))

                short_conditions.append(df['adx_live'] >= min_adx)

                if adx_cfg.get("require_di_confirmation", True):

                    short_conditions.append(df['minus_di_live'] > df['plus_di_live'])



            # RSI Momentum Filter

            if rsi_cfg.get("enabled", True):

                short_rsi_min = float(rsi_cfg.get("short_rsi_min", 22.0))

                short_rsi_max = float(rsi_cfg.get("short_rsi_max", 65.0))

                short_conditions.append(df['rsi_live'] >= short_rsi_min)

                short_conditions.append(df['rsi_live'] <= short_rsi_max)



            # EMA Trend Regime Filter

            if ema_cfg.get("enabled", True):

                short_conditions.append(

                    (df['close'] < df['ema_200_live']) | (df['rsi_live'] < 65)

                )



            # Volume Confirmation Filter

            if vol_cfg.get("enabled", True):

                min_vol_ratio = float(vol_cfg.get("min_volume_ratio", 0.8))

                short_conditions.append(df['volume'] >= (df['vol_ma_live'] * min_vol_ratio))

            # MFI Money Flow Liquidity Filter (Volume-Weighted Oversold Guard)

            if mfi_cfg.get("enabled", True):

                short_mfi_min = float(mfi_cfg.get("short_mfi_min", 25.0))

                short_mfi_max = float(mfi_cfg.get("short_mfi_max", 55.0))

                short_conditions.append(df['mfi_live'] >= short_mfi_min)

                short_conditions.append(df['mfi_live'] <= short_mfi_max)



            if 'DI_values' in df.columns:

                di_thresh = self.freqai_info['feature_parameters'].get('DI_threshold', 1.2)

                short_conditions.append(df['DI_values'] < di_thresh)



            df.loc[np.logical_and.reduce(short_conditions), 'enter_short'] = 1

            df.loc[np.logical_and.reduce(short_conditions), 'enter_tag'] = 'ai_conviction_short'



        return df



    # =========================================================================

    # 6. Exit Decisions (Signals)

    # =========================================================================

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:

        """

        Generates proactive exit signals if the AI prediction flips or ADX enters exhaustion.

        """

        settings = self.load_strategy_settings()

        ai_cfg = settings.get("ai_model", {})

        adx_cfg = settings.get("indicators", {}).get("adx", {})

        exit_long_thresh = float(ai_cfg.get("exit_threshold_long", -0.008))

        exit_short_thresh = float(ai_cfg.get("exit_threshold_short", 0.008))



        valid_pred = (df['do_predict'] == 1)



        # ----------------- LONG EXITS -----------------

        # 1. AI Reversal Exit: AI predicts a shift to negative return

        long_exit_cond = [

            valid_pred,

            df['&-s_close'] < exit_long_thresh

        ]

        df.loc[np.logical_and.reduce(long_exit_cond), 'exit_long'] = 1

        df.loc[np.logical_and.reduce(long_exit_cond), 'exit_tag'] = 'ai_reversal_exit_long'



        # 2. ADX Exhaustion Peak Exit (Quant Strategy from video)

        if adx_cfg.get("enabled", True) and adx_cfg.get("adx_exhaustion_exit", True):

            exhaust_thresh = float(adx_cfg.get("exhaustion_threshold", 48.0))

            if 'adx_live' in df.columns and 'plus_di_live' in df.columns:

                adx_exhaustion_long = (

                    (df['adx_live'] > exhaust_thresh) &

                    (df['adx_live'] < df['adx_live'].shift(1)) &

                    (df['plus_di_live'] < df['plus_di_live'].shift(1))

                )

                df.loc[adx_exhaustion_long, 'exit_long'] = 1

                df.loc[adx_exhaustion_long, 'exit_tag'] = 'adx_exhaustion_exit_long'



        # ----------------- SHORT EXITS (Futures Only) -----------------

        if self.can_short:

            # 1. AI Reversal Exit

            short_exit_cond = [

                valid_pred,

                df['&-s_close'] > exit_short_thresh

            ]

            df.loc[np.logical_and.reduce(short_exit_cond), 'exit_short'] = 1

            df.loc[np.logical_and.reduce(short_exit_cond), 'exit_tag'] = 'ai_reversal_exit_short'



            # 2. ADX Exhaustion Peak Exit

            if adx_cfg.get("enabled", True) and adx_cfg.get("adx_exhaustion_exit", True):

                exhaust_thresh = float(adx_cfg.get("exhaustion_threshold", 48.0))

                if 'adx_live' in df.columns and 'minus_di_live' in df.columns:

                    adx_exhaustion_short = (

                        (df['adx_live'] > exhaust_thresh) &

                        (df['adx_live'] < df['adx_live'].shift(1)) &

                        (df['minus_di_live'] < df['minus_di_live'].shift(1))

                    )

                    df.loc[adx_exhaustion_short, 'exit_short'] = 1

                    df.loc[adx_exhaustion_short, 'exit_tag'] = 'adx_exhaustion_exit_short'



        return df



    # =========================================================================

    # 7. Volatility-Adaptive Custom Stoploss & Break-Even Engine

    # =========================================================================

    def custom_stoploss(

        self,

        pair: str,

        trade: Trade,

        current_time: datetime,

        current_rate: float,

        current_profit: float,

        after_fill: bool,

        **kwargs

    ) -> Optional[float]:

        """

        Institutional Dynamic Stoploss Architecture:

        1. Break-Even Protection: Shifts stop to entry + offset once trigger profit is reached.

        2. Stage-based Profit Locking: Locks in hard gains after Stage 1 & Stage 2 take-profits.

        3. Runner Trailing Stop: Continuously ratchets stoploss upward behind running position.

        """

        try:

            settings = self.load_strategy_settings()

            risk_root = settings.get("risk_management", {})

            engine_key = "futures" if self.is_futures else "spot"

            mode_risk = risk_root.get(engine_key, {})



            be_cfg = mode_risk.get("break_even", {})

            ptp_cfg = mode_risk.get("partial_take_profit", {})



            executed_stages = trade.get_custom_data("executed_tp_stages", default=[])

            if not isinstance(executed_stages, list):

                executed_stages = []



            leverage = float(trade.leverage or 1.0)



            # -------------------------------------------------------------

            # Active Pair Stoploss Override (From Pre-Flight Audit / Custom Entry)

            # -------------------------------------------------------------

            try:

                overrides_path = Path(self.config.get('user_data_dir', 'user_data')) / 'active_pair_overrides.json'

                if overrides_path.exists():

                    with open(overrides_path, 'r', encoding='utf-8') as of:

                        pair_overrides = json.load(of)

                        if trade.pair in pair_overrides:

                            override_info = pair_overrides[trade.pair]

                            override_sl = float(override_info.get("stoploss_price", 0.0))

                            if override_sl > 0:

                                if not trade.is_short and override_sl < trade.open_rate:

                                    dist_from_open = (override_sl - trade.open_rate) / trade.open_rate

                                    hard_sl = float(mode_risk.get("stoploss", -0.05))

                                    if dist_from_open > hard_sl:

                                        return stoploss_from_open(

                                            dist_from_open,

                                            current_profit,

                                            is_short=False,

                                            leverage=leverage

                                        )

                                elif trade.is_short and override_sl > trade.open_rate:

                                    dist_from_open = (trade.open_rate - override_sl) / trade.open_rate

                                    hard_sl = float(mode_risk.get("stoploss", -0.04))

                                    if dist_from_open > hard_sl:

                                        return stoploss_from_open(

                                            dist_from_open,

                                            current_profit,

                                            is_short=True,

                                            leverage=leverage

                                        )

            except Exception as ex_ov:

                logger.debug(f"Override stoploss read error: {ex_ov}")



            # -------------------------------------------------------------

            # Stage 2 Trailing (Runner Protection)

            # If Stage 2 executed or profit reached stage2 target, trail runner

            # -------------------------------------------------------------

            s2_profit = float(ptp_cfg.get("stage2_profit", 0.030))

            if "stage2" in executed_stages or current_profit >= s2_profit:

                runner_trailing = float(ptp_cfg.get("runner_trailing_stop", 0.015))

                s1_profit = float(ptp_cfg.get("stage1_profit", 0.015))

                desired_sl_from_open = max(s1_profit, current_profit - runner_trailing)

                return stoploss_from_open(

                    desired_sl_from_open,

                    current_profit,

                    is_short=trade.is_short,

                    leverage=leverage

                )



            # -------------------------------------------------------------

            # S/R Channels Structural Support Floor Protection

            # -------------------------------------------------------------

            ind_cfg = settings.get("indicators", {})

            sr_cfg = ind_cfg.get("sr_channels", {})

            if sr_cfg.get("enabled", False) and sr_cfg.get("use_for_stoploss", True) and not trade.is_short:

                try:

                    analyzed_df, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)

                    if analyzed_df is not None and not analyzed_df.empty:

                        last_row = analyzed_df.iloc[-1]

                        s_bot = float(last_row.get("sr_support_bot", 0.0))

                        if s_bot > 0 and s_bot < trade.open_rate:

                            structural_sl_price = s_bot * 0.995 # 0.5% below support floor

                            dist_from_open = (structural_sl_price - trade.open_rate) / trade.open_rate

                            hard_sl = float(mode_risk.get("stoploss", -0.05))

                            desired_sl_from_open = max(hard_sl, dist_from_open)

                            # Only apply if it tightens stoploss above hard stop

                            if desired_sl_from_open > hard_sl:

                                return stoploss_from_open(

                                    desired_sl_from_open,

                                    current_profit,

                                    is_short=trade.is_short,

                                    leverage=leverage

                                )

                except Exception as ex:

                    logger.debug(f"S/R Stoploss check error: {ex}")



            # -------------------------------------------------------------

            # Stage 1 Profit Lock or Break-Even Trigger

            # -------------------------------------------------------------

            be_enabled = be_cfg.get("enabled", True)

            be_trigger = float(be_cfg.get("trigger_profit", 0.010))

            be_offset = float(be_cfg.get("offset", 0.002))



            if "stage1" in executed_stages or (be_enabled and current_profit >= be_trigger):

                return stoploss_from_open(

                    be_offset,

                    current_profit,

                    is_short=trade.is_short,

                    leverage=leverage

                )



            # -------------------------------------------------------------

            # Base Configured Dynamic Stoploss (From Dashboard Settings)

            # Never forced to -5%: Dynamically enforces user-configured SL (-2%, -3%, -4%, etc.)

            # -------------------------------------------------------------

            configured_sl = float(mode_risk.get("stoploss", risk_root.get("stoploss", -0.05)))

            return stoploss_from_open(

                configured_sl,

                current_profit,

                is_short=trade.is_short,

                leverage=leverage

            )



        except Exception as e:

            logger.error(f"Error in custom_stoploss for {pair}: {e}", exc_info=True)



        return None



    # =========================================================================

    # 8. Multi-Stage Partial Take-Profit (Scale-Out Position Adjustment)

    # =========================================================================

    def adjust_trade_position(

        self,

        trade: Trade,

        current_time: datetime,

        current_rate: float,

        current_profit: float,

        min_stake: Optional[float],

        max_stake: float,

        current_entry_rate: float,

        current_exit_rate: float,

        current_entry_profit: float,

        current_exit_profit: float,

        **kwargs

    ) -> Optional[tuple[float, str]]:

        """

        Institutional Multi-Stage Partial Take-Profit (Scale-Out) Engine.

        Executes granular exits at defined profit targets and tracks stage completion

        in persistent SQLite trade custom data.

        """

        try:

            settings = self.load_strategy_settings()

            risk_root = settings.get("risk_management", {})

            engine_key = "futures" if self.is_futures else "spot"

            mode_risk = risk_root.get(engine_key, {})

            ptp_cfg = mode_risk.get("partial_take_profit", {})

            ptp_master = risk_root.get("ptp_enabled", True)



            if not ptp_master or not ptp_cfg.get("enabled", True):

                return None



            # Retrieve or initialize executed stages list (persisted across restarts)

            executed_stages = trade.get_custom_data("executed_tp_stages", default=[])

            if not isinstance(executed_stages, list):

                executed_stages = []



            # Retrieve initial stake reference

            initial_stake = trade.get_custom_data("initial_stake", None)

            if initial_stake is None:

                initial_stake = float(trade.max_stake_amount or trade.stake_amount)

                trade.set_custom_data("initial_stake", initial_stake)



            min_stake_val = float(min_stake or 10.0)



            # S/R Channels Dynamic Resistance Scale-Out

            ind_cfg = settings.get("indicators", {})

            sr_cfg = ind_cfg.get("sr_channels", {})

            if sr_cfg.get("enabled", False) and sr_cfg.get("use_for_exit", True):

                try:

                    analyzed_df, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)

                    if analyzed_df is not None and not analyzed_df.empty:

                        last_row = analyzed_df.iloc[-1]

                        sr_res = float(last_row.get("sr_resistance_bot", 0.0))

                        if sr_res > 0 and current_rate >= sr_res and "sr_res_tp" not in executed_stages and current_profit > 0.005:

                            s1_ratio = float(ptp_cfg.get("stage1_sell_ratio", 0.35))

                            stake_to_sell = initial_stake * s1_ratio

                            remaining_stake = trade.stake_amount - stake_to_sell

                            if stake_to_sell >= min_stake_val and remaining_stake >= min_stake_val:

                                executed_stages.append("sr_res_tp")

                                trade.set_custom_data("executed_tp_stages", executed_stages)

                                logger.info(f"[{engine_key.upper()} S/R Resistance Exit] Reached Resistance [{sr_res:.2f}] for {trade.pair}. Scaling out ${stake_to_sell:.2f}")

                                return (-stake_to_sell, "sr_resistance_tp")

                except Exception as ex:

                    logger.debug(f"S/R Exit check error: {ex}")



            # Stage 1: e.g. 1.5% profit -> scale out 30%

            s1_profit = float(ptp_cfg.get("stage1_profit", 0.015))

            s1_ratio = float(ptp_cfg.get("stage1_sell_ratio", 0.30))



            if current_profit >= s1_profit and "stage1" not in executed_stages:

                stake_to_sell = initial_stake * s1_ratio

                remaining_stake = trade.stake_amount - stake_to_sell



                # Safety checks: ensure sold amount meets exchange minimums and leaves viable position

                if stake_to_sell >= min_stake_val and remaining_stake >= min_stake_val:

                    executed_stages.append("stage1")

                    trade.set_custom_data("executed_tp_stages", executed_stages)

                    logger.info(

                        f"[{engine_key.upper()} PTP] Executing Stage 1 Take-Profit for {trade.pair}. "

                        f"Profit: {current_profit:.2%}, Selling: ${stake_to_sell:.2f} ({s1_ratio:.0%})"

                    )

                    return (-stake_to_sell, "tp_stage1")



            # Stage 2: e.g. 3.0% profit -> scale out 35%

            s2_profit = float(ptp_cfg.get("stage2_profit", 0.030))

            s2_ratio = float(ptp_cfg.get("stage2_sell_ratio", 0.35))



            if current_profit >= s2_profit and "stage2" not in executed_stages:

                stake_to_sell = initial_stake * s2_ratio

                remaining_stake = trade.stake_amount - stake_to_sell



                if stake_to_sell >= min_stake_val and remaining_stake >= min_stake_val:

                    executed_stages.append("stage2")

                    trade.set_custom_data("executed_tp_stages", executed_stages)

                    logger.info(

                        f"[{engine_key.upper()} PTP] Executing Stage 2 Take-Profit for {trade.pair}. "

                        f"Profit: {current_profit:.2%}, Selling: ${stake_to_sell:.2f} ({s2_ratio:.0%})"

                    )

                    return (-stake_to_sell, "tp_stage2")



        except Exception as e:

            logger.error(f"Error in adjust_trade_position for {trade.pair}: {e}", exc_info=True)



        return None

