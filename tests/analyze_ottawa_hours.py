import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict

ottawa_tz = ZoneInfo("America/Toronto")
hourly = defaultdict(list)

with open("data/polymarket/paper_trading_validation_ledger.jsonl") as f:
    for line in f:
        if line.strip():
            t = json.loads(line)
            raw_t = t["entry_time"].replace(" UTC", "")
            dt_utc = datetime.fromisoformat(raw_t).replace(tzinfo=timezone.utc)
            dt_ottawa = dt_utc.astimezone(ottawa_tz)
            hourly[dt_ottawa.hour].append(t)

print("=== TRADES PER HOUR IN OTTAWA TIME (EDT / EASTERN TIME) ===")
total_trades = 0
for h in range(24):
    trades = hourly[h]
    n = len(trades)
    total_trades += n
    pnl = sum(t["net_pnl_usd"] for t in trades)
    wins = sum(1 for t in trades if t["net_pnl_usd"] > 0)
    bar = "█" * n
    sign = "+" if pnl >= 0 else ""
    pnl_str = f"{sign}${pnl * 2:.2f}"
    wr = f"{wins / n * 100:.0f}%" if n > 0 else "  - "
    print(f"{h:02d}:00 - {h:02d}:59 ET | {n:2d} trades ({wins:2d}W-{n-wins:1d}L | WR: {wr:>4}) | Net PnL ($100 lot): {pnl_str:>9} | {bar}")

print(f"\nTotal trades analyzed: {total_trades}")
