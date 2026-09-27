#!/usr/bin/env python3
import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

key = os.getenv("HYPERLIQUID_TESTNET_PRIVATE_KEY") or os.getenv("HYPERLIQUID_PRIVATE_KEY")
if not key:
    raise ValueError("Private key not found.")

account = Account.from_key(key)
info = Info(constants.TESTNET_API_URL, skip_ws=True)
master_addr = os.getenv("HYPERLIQUID_MASTER_ADDRESS") or account.address
epoch_start = datetime.now(timezone.utc) - timedelta(days=2)

raw_fills = info.user_fills(master_addr)
fill_rows = []

for f in raw_fills:
    t = datetime.fromtimestamp(f["time"] / 1000.0, timezone.utc)
    pnl = float(f.get("closedPnl", 0.0))
    if t >= epoch_start and pnl != 0.0:
        fill_rows.append({
            "time": t,
            "coin": f["coin"],
            "dir": f.get("dir", ""),
            "pnl": pnl,
            "fee": float(f.get("fee", 0.0)),
            "bucket": t.strftime("%Y-%m-%d %H:%M")
        })

if not fill_rows:
    print("No closed trades found in the last 48 hours.")
    exit()

df = pd.DataFrame(fill_rows)
trades = df.groupby(["coin", "bucket", "dir"]).agg({
    "pnl": "sum",
    "fee": "sum",
    "time": "max"
}).reset_index()

trades["net"] = trades["pnl"] - trades["fee"]
trades = trades.sort_values("time", ascending=False)

print("\n" + "=" * 75)
print(f"{'Time (UTC)':<18} {'Coin':<10} {'Direction':<14} {'Net PnL':<12} {'Outcome'}")
print("-" * 75)

for _, r in trades.iterrows():
    outcome = "WIN" if r["net"] > 0 else "LOSS"
    print(f"{r['time'].strftime('%Y-%m-%d %H:%M'):<18} {r['coin']:<10} {r['dir']:<14} ${r['net']:>+8.2f}    [{outcome}]")

wins = trades[trades["net"] > 0]
losses = trades[trades["net"] <= 0]

avg_win = wins["net"].mean() if len(wins) else 0.0
avg_loss = abs(losses["net"].mean()) if len(losses) else 0.0
ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

print("=" * 75)
print(f"Total Trades: {len(trades)} ({len(wins)}W / {len(losses)}L | Win Rate: {len(wins)/len(trades)*100:.1f}%)")
print(f"Average Win:  +${avg_win:.2f}")
print(f"Average Loss: -${avg_loss:.2f}")
print(f"Win/Loss Payoff Ratio: {ratio:.2f} (Target: >= 1.30)")
print(f"Total Net PnL: ${trades['net'].sum():>+8.2f}")
print("=" * 75 + "\n")
