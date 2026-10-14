import json

with open("data/polymarket/live_harvester_state.json") as f:
    s = json.load(f)

closed = s.get("closed_positions", [])
print(f"Total closed positions in state file: {len(closed)}")
for i, p in enumerate(closed):
    entry_utc = str(p.get("entry_time_utc", ""))[:19]
    mkt = p.get("market_id")
    tgt = p.get("target_token")
    notional = float(p.get("notional_usd", 0.0))
    payout = float(p.get("payout_usd", 0.0))
    fee = float(p.get("fee_usd", 0.0)) + float(p.get("realized_exit_fee", 0.0))
    net = float(p.get("net_pnl_usd", 0.0))
    reason = p.get("close_reason")
    print(f"{i+1:2d} | Mkt: {mkt} | Entry: {entry_utc} | Tgt: {tgt} | Notional: ${notional:.2f} | Payout: ${payout:.2f} | Fee: ${fee:.2f} | Net: ${net:+.2f} | Reason: {reason}")
