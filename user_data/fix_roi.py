import re
from pathlib import Path

p = Path(r"C:\Users\OMRRAN\Desktop\Cource AI\#4- ML\Competitions\trend ai\Crypto-Institutional-Quant-Fund\user_data\strategies\InstitutionalDualStrategy.py")
text = p.read_text(encoding="utf-8")

# Fix minimal_roi dictionary definition
text = re.sub(
    r'minimal_roi\s*=\s*\{[^}]+\}',
    '''minimal_roi = {
        0: 0.06,      # 6% immediate take-profit
        60: 0.04,     # 4% after 1 hour
        180: 0.025,   # 2.5% after 3 hours
        360: 0.015    # 1.5% after 6 hours
    }''',
    text,
    count=1
)

# Fix minimal_roi dynamic loading to ensure integer keys
text = text.replace(
    'self.minimal_roi = {str(k): float(v) for k, v in risk_root["minimal_roi"].items()}',
    'self.minimal_roi = {int(k): float(v) for k, v in risk_root["minimal_roi"].items()}'
)

p.write_text(text, encoding="utf-8")
print("Fixed minimal_roi in InstitutionalDualStrategy.py successfully.")
