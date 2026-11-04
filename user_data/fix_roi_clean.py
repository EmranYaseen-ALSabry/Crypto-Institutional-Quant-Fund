import re
from pathlib import Path

p = Path(r"C:\Users\OMRRAN\Desktop\Cource AI\#4- ML\Competitions\trend ai\Crypto-Institutional-Quant-Fund\user_data\strategies\InstitutionalDualStrategy.py")
text = p.read_text(encoding="utf-8")

# Class attribute must be strings for jsonschema validation
text = re.sub(
    r'minimal_roi\s*=\s*\{[^}]+\}',
    '''minimal_roi = {
        "0": 0.06,      # 6% immediate take-profit
        "60": 0.04,     # 4% after 1 hour
        "180": 0.025,   # 2.5% after 3 hours
        "360": 0.015    # 1.5% after 6 hours
    }''',
    text,
    count=1
)

# In runtime dynamic loading, keys MUST be int for should_exit comparison (x <= trade_dur)
text = text.replace(
    'self.minimal_roi = {str(k): float(v) for k, v in risk_root["minimal_roi"].items()}',
    'self.minimal_roi = {int(k): float(v) for k, v in risk_root["minimal_roi"].items()}'
)

p.write_text(text, encoding="utf-8")
print("Successfully set string keys for class attribute and int keys for runtime self.minimal_roi")
