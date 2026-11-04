from pathlib import Path

path = Path(r"C:\Users\OMRRAN\Desktop\Cource AI\#4- ML\Competitions\trend ai\Crypto-Institutional-Quant-Fund\dashboard\server.py")
text = path.read_text(encoding="utf-8")

text = text.replace(
    'conn = sqlite3.connect(str(spot_db))',
    'conn = sqlite3.connect(f"file:{spot_db.resolve()}?mode=ro", uri=True)'
)
text = text.replace(
    'conn = sqlite3.connect(str(fut_db))',
    'conn = sqlite3.connect(f"file:{fut_db.resolve()}?mode=ro", uri=True)'
)

path.write_text(text, encoding="utf-8")
print("Updated sqlite3 connects to read-only URI mode successfully.")
