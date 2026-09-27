import pandas as pd
import numpy as np
from tactical_regime import TacticalRegimeEngine
from optimizer_cache import load_and_cache_dataset

train_bars, train_dict, oos_bars, oos_dict = load_and_cache_dataset(270, 90)
tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)

def simulate_vol_gated(cfg, unique_bars, dict_bars, friction_bps=12.0):
    equity = 1000.0
    open_pos, cooldowns, trades, curve = {}, {}, [], []

    tp_mult, sl_mult = cfg["tp"], cfg["sl"]
    hold_bars = cfg["hold"]
    risk_pct = cfg["risk"]
    max_slot_pct = cfg["slot_pct"]
    max_slots = cfg["max_slots"]

    for b_idx, b_dict in enumerate(dict_bars):
        b_ts = unique_bars[b_idx]
        closed = []

        # 1. Resolve Active Positions
        for sym, pos in list(open_pos.items()):
            r = b_dict.get(sym)
            if not r: continue
            h, l, c = r["high"], r["low"], r["close"]
            hit_tp, hit_sl, hit_time, exit_px = False, False, False, c

            if pos["is_buy"]:
                if l <= pos["sl_px"]: hit_sl, exit_px = True, pos["sl_px"]
                elif h >= pos["tp_px"]: hit_tp, exit_px = True, pos["tp_px"]
            else:
                if h >= pos["sl_px"]: hit_sl, exit_px = True, pos["sl_px"]
                elif l <= pos["tp_px"]: hit_tp, exit_px = True, pos["tp_px"]

            if not hit_tp and not hit_sl and (b_idx - pos["entry_b_idx"]) >= hold_bars:
                hit_time, exit_px = True, c

            if hit_tp or hit_sl or hit_time:
                gross = ((exit_px - pos["entry_px"]) if pos["is_buy"] else (pos["entry_px"] - exit_px)) * pos["size"]
                fee = (pos["notional"] + (exit_px * pos["size"])) * (friction_bps / 10000.0 / 2.0)
                net = gross - fee
                equity += net
                trades.append({
                    "ticker": sym, "side": "LONG" if pos["is_buy"] else "SHORT",
                    "net": net, "win": net > 0
                })
                closed.append(sym)
                cooldowns[sym] = b_ts

        for s in closed: del open_pos[s]

        # 2. Gate & Allocate strictly inside Sweet-Spots + Volatility Expansion
        free = max(0, max_slots - len(open_pos))
        long_c = sum(1 for pos in open_pos.values() if pos["is_buy"])
        short_c = sum(1 for pos in open_pos.values() if not pos["is_buy"])

        if free > 0 and equity > 50.0 and b_dict:
            first_v = next(iter(b_dict.values()))
            b_ret4h, breadth = first_v["btc_ret_4h"], first_v["market_breadth"]
            is_bull_t = (b_ret4h >= 0.025 and breadth >= 0.60)

            cands = []
            for sym, r in b_dict.items():
                pl, ps, pc, px, atr = r["p_long"], r["p_short"], r["p_chop"], r["close"], r["atr"]
                vol_exp = r.get("vol_expansion_ratio", 1.0)
                
                if px <= 0 or atr <= 0 or cooldowns.get(sym) == b_ts or sym in open_pos: continue
                
                # Volatility and Regime Filters
                if pc >= cfg["chop_max"]: continue
                if vol_exp < cfg["min_vol_exp"]: continue  # Block dead range drift

                # Sweet Spot Probability Boundaries
                l_pass = (cfg["l_min"] <= pl <= cfg["l_max"])
                s_pass = (cfg["s_min"] <= ps <= cfg["s_max"]) and not is_bull_t

                if not l_pass and not s_pass: continue

                is_buy = l_pass and (not s_pass or pl >= ps)
                p_win = pl if is_buy else ps
                ev = (p_win * ((tp_mult * atr) / px)) - ((1.0 - p_win) * ((sl_mult * atr) / px)) - (friction_bps / 10000.0)

                if ev > 0:
                    cands.append({"sym": sym, "is_buy": is_buy, "ev": ev, "px": px, "atr": atr, "p_win": p_win})

            alloc = 0
            for cand in sorted(cands, key=lambda x: x["ev"], reverse=True):
                if alloc >= 2 or len(open_pos) >= max_slots: break
                is_buy = cand["is_buy"]
                if (is_buy and long_c >= cfg["max_side"]) or (not is_buy and short_c >= cfg["max_side"]): continue

                raw_tokens = (equity * risk_pct) / max(1e-6, sl_mult * cand["atr"])
                target_notional = min(equity * max_slot_pct, raw_tokens * cand["px"])
                raw_tokens = target_notional / cand["px"]

                if raw_tokens <= 0 or target_notional < 15.0: continue

                open_pos[cand["sym"]] = {
                    "is_buy": is_buy, "entry_px": cand["px"], "entry_b_idx": b_idx,
                    "size": raw_tokens, "notional": target_notional,
                    "tp_px": cand["px"] + (tp_mult * cand["atr"]) if is_buy else cand["px"] - (tp_mult * cand["atr"]),
                    "sl_px": cand["px"] - (sl_mult * cand["atr"]) if is_buy else cand["px"] + (sl_mult * cand["atr"])
                }
                if is_buy: long_c += 1
                else: short_c += 1
                alloc += 1

        curve.append(equity)

    df_t = pd.DataFrame(trades)
    e_end = curve[-1]
    tot_ret = ((e_end - 1000.0) / 1000.0) * 100.0
    mult = e_end / 1000.0
    peak = pd.Series(curve).cummax()
    max_dd = ((pd.Series(curve) - peak) / peak).min() * 100.0
    wins = df_t[df_t["net"] > 0]["net"].sum() if not df_t.empty else 0.0
    loss = abs(df_t[df_t["net"] <= 0]["net"].sum()) if not df_t.empty else 1.0
    pf = wins / loss
    wr = df_t["win"].mean() * 100.0 if not df_t.empty else 0.0

    return tot_ret, mult, max_dd, pf, wr, len(df_t), e_end

configs = [
    {
        "name": "Vol-Expansion 1 (Min VolExp 1.00 / Chop < 0.35 / 2.5% Risk)",
        "l_min": 0.58, "l_max": 0.67, "s_min": 0.45, "s_max": 0.57,
        "min_vol_exp": 1.00, "chop_max": 0.35, "tp": 2.7, "sl": 1.4, "hold": 8,
        "risk": 0.025, "slot_pct": 0.60, "max_slots": 4, "max_side": 3
    },
    {
        "name": "Vol-Expansion 2 (Min VolExp 1.08 / Chop < 0.30 / 2.8% Risk)",
        "l_min": 0.58, "l_max": 0.67, "s_min": 0.45, "s_max": 0.57,
        "min_vol_exp": 1.08, "chop_max": 0.30, "tp": 2.8, "sl": 1.4, "hold": 8,
        "risk": 0.028, "slot_pct": 0.65, "max_slots": 5, "max_side": 4
    },
    {
        "name": "Aggressive Impulse (Min VolExp 1.15 / Chop < 0.25 / 3.2% Risk)",
        "l_min": 0.57, "l_max": 0.68, "s_min": 0.44, "s_max": 0.58,
        "min_vol_exp": 1.15, "chop_max": 0.25, "tp": 3.0, "sl": 1.4, "hold": 9,
        "risk": 0.032, "slot_pct": 0.70, "max_slots": 5, "max_side": 4
    }
]

print("\n" + "=" * 115)
print("             VOLATILITY-EXPANSION GATED POLICY (IN-SAMPLE, OOS & FULL LIFECYCLE)             ")
print("=" * 115)

records = []
full_bars = train_bars + oos_bars
full_dict = train_dict + oos_dict

for c in configs:
    is_ret, is_m, is_dd, is_pf, is_wr, is_n, _ = simulate_vol_gated(c, train_bars, train_dict, 12.0)
    oos_ret, oos_m, oos_dd, oos_pf, oos_wr, oos_n, _ = simulate_vol_gated(c, oos_bars, oos_dict, 12.0)
    tot_ret, mult, f_dd, f_pf, f_wr, f_n, f_end = simulate_vol_gated(c, full_bars, full_dict, 12.0)
    stress_ret, stress_mult, _, stress_pf, _, _, stress_end = simulate_vol_gated(c, full_bars, full_dict, 25.0)

    records.append({
        "Configuration": c["name"],
        "IS PF": round(is_pf, 2),
        "OOS PF": round(oos_pf, 2),
        "OOS Ret": f"{oos_ret:>+6.1f}%",
        "270d Mult": f"{mult:.2f}x",
        "270d Ret": f"{tot_ret:>+6.1f}%",
        "270d DD": f"{f_dd:>5.1f}%",
        "270d PF": round(f_pf, 2),
        "Trades": f_n,
        "Stress 25bps": f"{stress_mult:.2f}x (${stress_end:.0f})"
    })

print(pd.DataFrame(records).to_string(index=False))
print("=" * 115)
