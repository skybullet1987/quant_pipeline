import pandas as pd
import numpy as np
from tactical_regime import TacticalRegimeEngine
from optimizer_cache import load_and_cache_dataset
from optimizer_sim import simulate_policy_fast

train_bars, train_dict, oos_bars, oos_dict = load_and_cache_dataset(270, 90)
tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)

configs = [
    {"name": "Refined Alpha 1 (2.4x TP / 1.4x SL / Strict Longs)", "tp": 2.4, "sl": 1.4, "l_boost": 0.12, "s_boost": 0.00, "hold": 8, "risk": 0.012, "chop": 0.45},
    {"name": "Refined Alpha 2 (2.6x TP / 1.4x SL / Strict Longs)", "tp": 2.6, "sl": 1.4, "l_boost": 0.12, "s_boost": 0.00, "hold": 8, "risk": 0.012, "chop": 0.45},
    {"name": "Refined Alpha 3 (2.8x TP / 1.5x SL / Strict Longs)", "tp": 2.8, "sl": 1.5, "l_boost": 0.14, "s_boost": 0.00, "hold": 9, "risk": 0.012, "chop": 0.40},
    {"name": "Short-Dominant (2.5x TP / 1.4x SL / Ultra-Strict Longs)", "tp": 2.5, "sl": 1.4, "l_boost": 0.16, "s_boost": -0.01, "hold": 8, "risk": 0.015, "chop": 0.45},
]

results = []

for cfg in configs:
    p = {
        "tp_atr_mult": cfg["tp"], "sl_atr_mult": cfg["sl"], "risk_budget_pct": cfg["risk"],
        "max_slot_equity_pct": 0.35, "max_longs": 2, "max_shorts": 3,
        "max_net_imbalance": 2, "max_hold_bars": cfg["hold"],
        "long_hurdle_boost": cfg["l_boost"], "short_hurdle_boost": cfg["s_boost"],
        "chop_filter_threshold": cfg["chop"], "max_trades_per_bar": 1,
        "btc_bull_veto_pct": 0.025
    }

    # In-Sample Performance
    _, is_ret, is_cagr, is_dd, is_pf, is_wr, is_tr, _, _ = simulate_policy_fast(p, train_bars, train_dict, tactical_engine, 12.0)
    
    # Out-of-Sample Performance
    _, oos_ret, oos_cagr, oos_dd, oos_pf, oos_wr, oos_tr, _, _ = simulate_policy_fast(p, oos_bars, oos_dict, tactical_engine, 12.0)
    
    # 20 bps & 35 bps Friction Stress
    pf_20bps = simulate_policy_fast(p, oos_bars, oos_dict, tactical_engine, 20.0)[4]
    pf_35bps = simulate_policy_fast(p, oos_bars, oos_dict, tactical_engine, 35.0)[4]

    results.append({
        "Configuration": cfg["name"],
        "IS Return": f"{is_ret:>+6.1f}%",
        "OOS Return": f"{oos_ret:>+6.1f}%",
        "OOS MaxDD": f"{oos_dd:>5.1f}%",
        "OOS PF": round(oos_pf, 2),
        "PF @ 20bps": round(pf_20bps, 2),
        "PF @ 35bps": round(pf_35bps, 2),
        "OOS WinRate": f"{oos_wr:.1f}%",
        "OOS Trades": oos_tr
    })

print("\n" + "=" * 95)
print("                    TARGETED REFINEMENT RESULTS (IN-SAMPLE & OOS)                     ")
print("=" * 95)
df_res = pd.DataFrame(results)
print(df_res.to_string(index=False))
print("=" * 95)
