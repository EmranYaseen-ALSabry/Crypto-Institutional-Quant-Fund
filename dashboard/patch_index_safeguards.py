from pathlib import Path

p = Path(r"C:\Users\OMRRAN\Desktop\Cource AI\#4- ML\Competitions\trend ai\Crypto-Institutional-Quant-Fund\dashboard\templates\index.html")
text = p.read_text(encoding="utf-8")

old_strat_indicators = """                strat.indicators = {
                    adx: {
                        enabled: document.getElementById('toggle-adx-enabled').checked,
                        timeperiod: 14,
                        min_adx: parseFloat(document.getElementById('input-adx-min').value),
                        require_di_confirmation: document.getElementById('toggle-adx-di').checked,
                        adx_exhaustion_exit: document.getElementById('toggle-adx-exhaustion').checked,
                        exhaustion_threshold: parseFloat(document.getElementById('input-adx-exhaust').value)
                    },
                    rsi: {
                        enabled: document.getElementById('toggle-rsi-enabled').checked,
                        timeperiod: 14,
                        long_rsi_min: parseFloat(document.getElementById('input-rsi-long-min').value),
                        long_rsi_max: parseFloat(document.getElementById('input-rsi-long-max').value),
                        short_rsi_min: parseFloat(document.getElementById('input-rsi-short-min').value),
                        short_rsi_max: parseFloat(document.getElementById('input-rsi-short-max').value)
                    },
                    ema_filter: {
                        enabled: document.getElementById('toggle-ema-enabled').checked,
                        macro_period: 200
                    },
                    volume_filter: {
                        enabled: document.getElementById('toggle-vol-enabled').checked,
                        min_volume_ratio: 0.8
                    }
                };"""

new_strat_indicators = """                strat.risk_management.minimal_roi = (currentConfigs.strategy_settings && currentConfigs.strategy_settings.risk_management && currentConfigs.strategy_settings.risk_management.minimal_roi) || {
                    "0": 0.06,
                    "60": 0.04,
                    "180": 0.025,
                    "360": 0.015
                };

                strat.indicators = {
                    adx: {
                        enabled: document.getElementById('toggle-adx-enabled') ? document.getElementById('toggle-adx-enabled').checked : true,
                        timeperiod: 14,
                        min_adx: parseFloat(document.getElementById('input-adx-min')?.value || 22),
                        require_di_confirmation: document.getElementById('toggle-adx-di') ? document.getElementById('toggle-adx-di').checked : true,
                        adx_exhaustion_exit: document.getElementById('toggle-adx-exhaustion') ? document.getElementById('toggle-adx-exhaustion').checked : true,
                        exhaustion_threshold: parseFloat(document.getElementById('input-adx-exhaust')?.value || 48)
                    },
                    rsi: {
                        enabled: document.getElementById('toggle-rsi-enabled') ? document.getElementById('toggle-rsi-enabled').checked : true,
                        timeperiod: 14,
                        long_rsi_min: parseFloat(document.getElementById('input-rsi-long-min')?.value || 35),
                        long_rsi_max: parseFloat(document.getElementById('input-rsi-long-max')?.value || 78),
                        short_rsi_min: parseFloat(document.getElementById('input-rsi-short-min')?.value || 22),
                        short_rsi_max: parseFloat(document.getElementById('input-rsi-short-max')?.value || 65)
                    },
                    ema_filter: {
                        enabled: document.getElementById('toggle-ema-enabled') ? document.getElementById('toggle-ema-enabled').checked : true,
                        macro_period: 200
                    },
                    volume_filter: {
                        enabled: document.getElementById('toggle-vol-enabled') ? document.getElementById('toggle-vol-enabled').checked : true,
                        min_volume_ratio: 0.8
                    },
                    sr_channels: (currentConfigs.strategy_settings && currentConfigs.strategy_settings.indicators && currentConfigs.strategy_settings.indicators.sr_channels) || {
                        enabled: true,
                        pivot_period: 10,
                        channel_width_pct: 0.025,
                        min_strength: 2,
                        use_for_entry: true,
                        use_for_stoploss: true
                    }
                };"""

text = text.replace(old_strat_indicators, new_strat_indicators)

# Also fix the spot & futures freqai inputs parser
old_freqai_spot = """                if (!spot.freqai) spot.freqai = {};
                spot.freqai.train_period_days = parseInt(document.getElementById('spot-train-days').value);
                spot.freqai.live_retrain_hours = parseInt(document.getElementById('spot-retrain-hours').value);
                spot.freqai.expiration_hours = parseInt(document.getElementById('spot-exp-hours').value);"""

new_freqai_spot = """                if (!spot.freqai) spot.freqai = {};
                const sTrain = parseInt(document.getElementById('spot-train-days')?.value);
                spot.freqai.train_period_days = (!isNaN(sTrain) && sTrain > 0) ? sTrain : (spot.freqai.train_period_days || 30);
                const sRetrain = parseInt(document.getElementById('spot-retrain-hours')?.value);
                spot.freqai.live_retrain_hours = (!isNaN(sRetrain) && sRetrain > 0) ? sRetrain : (spot.freqai.live_retrain_hours || 12);
                const sExp = parseInt(document.getElementById('spot-exp-hours')?.value);
                spot.freqai.expiration_hours = (!isNaN(sExp) && sExp >= 0) ? sExp : (spot.freqai.expiration_hours !== undefined ? spot.freqai.expiration_hours : 0);
                spot.dry_run = true;"""

text = text.replace(old_freqai_spot, new_freqai_spot)

old_freqai_fut = """                if (!fut.freqai) fut.freqai = {};
                fut.freqai.train_period_days = parseInt(document.getElementById('futures-train-days').value);
                fut.freqai.live_retrain_hours = parseInt(document.getElementById('futures-retrain-hours').value);
                fut.freqai.expiration_hours = parseInt(document.getElementById('futures-exp-hours').value);"""

new_freqai_fut = """                if (!fut.freqai) fut.freqai = {};
                const fTrain = parseInt(document.getElementById('futures-train-days')?.value);
                fut.freqai.train_period_days = (!isNaN(fTrain) && fTrain > 0) ? fTrain : (fut.freqai.train_period_days || 30);
                const fRetrain = parseInt(document.getElementById('futures-retrain-hours')?.value);
                fut.freqai.live_retrain_hours = (!isNaN(fRetrain) && fRetrain > 0) ? fRetrain : (fut.freqai.live_retrain_hours || 12);
                const fExp = parseInt(document.getElementById('futures-exp-hours')?.value);
                fut.freqai.expiration_hours = (!isNaN(fExp) && fExp >= 0) ? fExp : (fut.freqai.expiration_hours !== undefined ? fut.freqai.expiration_hours : 0);
                fut.dry_run = true;"""

text = text.replace(old_freqai_fut, new_freqai_fut)

p.write_text(text, encoding="utf-8")
print("Successfully patched index.html saveAllSettings safeguards!")
