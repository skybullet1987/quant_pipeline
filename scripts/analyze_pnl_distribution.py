import json

with open("data/polymarket/live_harvester_state.json") as f:
    st = json.load(f)

closed = st.get("closed_positions", [])
wins = []
losses = []
notionals = []

print(f"Total closed positions: {len(closed)}")
for i, p in enumerate(closed, 1):
    pnl = p.get("net_pnl_usd")
    notional = float(p.get("notional_usd", 0.0) or 0.0)
    reason = p.get("close_reason", "")
    won = p.get("won")
    if notional > 0:
        notionals.append(notional)
    print(f"Trade #{i:02d}: Notional=${notional:.2f} | NetPnL={pnl} | Won={won} | Reason={reason}")
    if pnl is not None:
        if pnl > 0:
            wins.append(pnl)
        elif pnl < 0:
            losses.append(pnl)

print("=" * 60)
if notionals:
    print(f"Average Deployed Notional: ${sum(notionals)/len(notionals):.2f} (Min: ${min(notionals):.2f}, Max: ${max(notionals):.2f})")
if wins:
    print(f"Empirical Wins (n={len(wins)}): Avg = +${sum(wins)/len(wins):.2f} (Min: +${min(wins):.2f}, Max: +${max(wins):.2f})")
if losses:
    print(f"Empirical Losses (n={len(losses)}): Avg = ${sum(losses)/len(losses):.2f} (Min: ${min(losses):.2f}, Max: ${max(losses):.2f})")

# Also check EXP-302 / EXP-303
