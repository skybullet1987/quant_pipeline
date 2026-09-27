import re

with open("execute_hyperliquid_testnet.py", "r") as f:
    code = f.read()

# 1. Add Cooldown Table to DB Init
old_db = """    c.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS candidate_evaluations ("""

new_db = """    c.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS closed_trades_cooldown (
            symbol TEXT PRIMARY KEY,
            closed_at TEXT,
            bar_timestamp TEXT
        )
    \"\"\")
    c.execute(\"\"\"
        CREATE TABLE IF NOT EXISTS candidate_evaluations ("""

if "closed_trades_cooldown" not in code:
    code = code.replace(old_db, new_db)

# 2. Update Risk Parameters to Asymmetric R:R
code = code.replace('atr_stop_multiplier=1.50', 'atr_stop_multiplier=1.20')
code = code.replace('live_px + (1.50 * cand["atr"])', 'live_px + (2.00 * cand["atr"])')
code = code.replace('live_px - (1.50 * cand["atr"])', 'live_px - (2.00 * cand["atr"])')

with open("execute_hyperliquid_testnet.py", "w") as f:
    f.write(code)

print("[OK] Applied asymmetric 2.0x TP / 1.2x SL and cooldown database schema.")
