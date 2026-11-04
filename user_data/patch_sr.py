from pathlib import Path
import re

p = Path(r"C:\Users\OMRRAN\Desktop\Cource AI\#4- ML\Competitions\trend ai\Crypto-Institutional-Quant-Fund\user_data\strategies\InstitutionalDualStrategy.py")
text = p.read_text(encoding="utf-8")

# Enhance calculate_sr_channels to guarantee valid non-zero support and resistance levels
target = """            s_bot, s_top, s_touches = (supports[-1]['bot'], supports[-1]['top'], supports[-1]['touches']) if supports else (0.0, 0.0, 0)
            r_bot, r_top, r_touches = (resistances[0]['bot'], resistances[0]['top'], resistances[0]['touches']) if resistances else (0.0, 0.0, 0)"""

replacement = """            # Institutional Fallback: If no multi-touch cluster, fallback to nearest pivot point (min 1 touch) or recent rolling extremes
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
                    r_bot, r_top, r_touches = recent_high * (1.0 - half_w), recent_high * (1.0 + half_w), 1"""

if target in text:
    text = text.replace(target, replacement)
    p.write_text(text, encoding="utf-8")
    print("Successfully enhanced calculate_sr_channels with smart pivot fallback.")
else:
    print("Target not found.")
