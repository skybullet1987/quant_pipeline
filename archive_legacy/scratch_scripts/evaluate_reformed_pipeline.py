#!/usr/bin/env python3
import glob
import pandas as pd
import numpy as np
from tactical_regime import TacticalRegimeEngine
from risk_engine import PortfolioRiskEngine

files = sorted(glob.glob("oos_decisions_*.parquet"))
if not files:
    print("[ERROR] No oos_decisions_*.parquet found.")
    exit(1)

latest = files[-1]
print(f"\n[1/3] Loading {latest}...")
df = pd.read_parquet(latest)

tactical = TacticalRegimeEngine()
risk_engine = PortfolioRiskEngine(risk_budget_pct=0.015, max_slot_equity_pct=0.35)

ACCOUNT_EQUITY = 1000.0  # Normalized baseline

# Run Simulation
reformed_trades = []
for idx, row in df.iterrows():
    slow_reg = int(row.get('regime', 0))
    p_l = float(row.get('p_long', 0.5))
    p_s = float(row.get('p_short', 0.5))
    p_c = float(row.get('p_chop', 0.0))
    
    # 1. Tactical Evaluation
    state = tactical.evaluate_state(slow_regime=slow_reg)
    
    # Direction Selection with Dynamic Hurdles
    chosen_dir = None
    prob = 0.0
    size_mult = 1.0
    
    if p_l >= state['long_hurdle'] and p_l > p_s:
        chosen_dir = 'LONG'
        prob = p_l
        size_mult = state['long_size_mult']
    elif p_s >= state['short_hurdle'] and p_s > p_l:
        chosen_dir = 'SHORT'
        prob = p_s
        size_mult = state['short_size_mult']
        
    if not chosen_dir or p_c > 0.60:
        continue

    # 2. Risk Sizing
    price = float(row.get('entry_price', 1.0))
    atr = float(row.get('atr', price * 0.015))
    sz_tokens, sz_usd, stop_dist = risk_engine.compute_order_size(
        account_equity=ACCOUNT_EQUITY,
        current_price=price,
        atr_20=atr,
        regime_size_mult=size_mult,
        model_conviction=prob
    )
    
    # Target Barrier Outcome Approximation
    long_ev = float(row.get('long_ev_bps', 0))
    short_ev = float(row.get('short_ev_bps', 0))
    ret_bps = long_ev if chosen_dir == 'LONG' else short_ev
    pnl_usd = sz_usd * (ret_bps / 10000.0)

    reformed_trades.append({
        'timestamp': row.get('timestamp'),
        'ticker': row.get('ticker'),
        'regime': slow_reg,
        'direction': chosen_dir,
        'prob': prob,
        'size_usd': sz_usd,
        'ret_bps': ret_bps,
        'pnl_usd': pnl_usd
    })

res = pd.DataFrame(reformed_trades)
print("\n" + "=" * 80)
print("             REFORMED PIPELINE PERFORMANCE SUMMARY")
print("=" * 80)
print(f"Total Qualified Trades   : {len(res):,}")
print(f"Directional Distribution : {res['direction'].value_counts().to_dict()}")
print(f"Regime Trade Count       : {res['regime'].value_counts().to_dict()}")

wins = res[res['pnl_usd'] > 0]
losses = res[res['pnl_usd'] < 0]
win_rate = (len(wins) / max(len(res), 1)) * 100
total_pnl = res['pnl_usd'].sum()
profit_factor = abs(wins['pnl_usd'].sum() / min(losses['pnl_usd'].sum(), -1e-5))

print(f"\nWin Rate                 : {win_rate:.2f}%")
print(f"Simulated PnL ($)        : ${total_pnl:+.2f}")
print(f"Profit Factor            : {profit_factor:.2f}")
print(f"Avg Position Sizing ($)  : ${res['size_usd'].mean():.2f}")
print("=" * 80 + "\n")
