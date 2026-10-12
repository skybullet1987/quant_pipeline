import json

with open("data/polymarket/live_harvester_state.json") as f:
    d = json.load(f)

closed = d.get("closed_positions", [])
print(f"Total Closed Real-Money Trades: {len(closed)}")
for i, p in enumerate(closed):
    tid = p.get("trade_id")
    asset = p.get("asset", "BTC/ETH")
    notional = p.get("notional_usd", 0.0)
    won = p.get("won")
    pnl = p.get("net_pnl_usd", 0.0)
    reason = p.get("close_reason")
    entry_time = p.get("entry_time_utc", "")[:16]
    print(f"{i+1:2d}. [{entry_time}] {tid}: notional=${notional:.2f}, won={won!s:5s}, pnl=${pnl:+.2f}, reason={reason}")
