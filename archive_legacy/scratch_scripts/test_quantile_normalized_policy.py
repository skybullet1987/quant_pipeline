import pandas as pd
import numpy as np
from optimizer_cache import load_and_cache_dataset
from tactical_regime import TacticalRegimeEngine

train_bars, train_dict, oos_bars, oos_dict = load_and_cache_dataset(270, 90)
tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)

# Pre-calculate empirical quantile thresholds from distribution
# Long: 80th %ile = 0.480, 85th = 0.500, 90th = 0.520
# Short: 80th %ile = 0.590, 85th = 0.620, 90th = 0.652

def simulate_quantile_policy(p, unique_bars, dict_bars, friction_bps=12.0):
    equity = 1000.0
    open_pos, cooldowns, trades, curve = {}, {}, [], []

    tp_mult, sl_mult = p["tp"], p["sl"]
    hold_bars = p["hold"]
    risk_pct = p["risk"]
    
    # Quantile thresholds
    l_min_p = p["l_thresh"]
    s_min_p = p["s_thresh"]

    for b_idx, b_dict in enumerate(dict_bars):
        b_ts = unique_bars[b_idx]
        closed = []

        # 1. Resolve positions
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
                    "net": net, "side": "LONG" if pos["is_buy"] else "SHORT",
                    "win": net > 0, "p_raw": pos["p_raw"]
                })
                closed.append(sym)
                cooldowns[sym] = b_ts

        for s in closed: del open_pos[s]

        # 2. Gate & Allocate using Normalized Quantile Z-Scores
        free = max(0, 5 - len(open_pos))
        long_c = sum(1 for pos in open_pos.values() if pos["is_buy"])
        short_c = sum(1 for pos in open_pos.values() if not pos["is_buy"])

        if free > 0 and equity > 100.0 and b_dict:
            first_v = next(iter(b_dict.values()))
            b_ret4h, breadth = first_v["btc_ret_4h"], first_v["market_breadth"]
            is_bull_t = (b_ret4h >= 0.025 and breadth >= 0.60)

            cands = []
            for sym, r in b_dict.items():
                pl, ps, pc, px, atr = r["p_long"], r["p_short"], r["p_chop"], r["close"], r["atr"]
                if px <= 0 or atr <= 0 or cooldowns.get(sym) == b_ts or sym in open_pos: continue
                if pc >= p["chop"]: continue

                # Normalize to Empirical Quantile Scores (0.0 to 1.0 scale based on distribution)
                # Long distribution: median=0.408, 90th=0.520
                q_long = (pl - 0.408) / (0.520 - 0.408)
                # Short distribution: median=0.495, 90th=0.652
                q_short = (ps - 0.495) / (0.652 - 0.495)

                if is_bull_t: q_short -= 0.50  # Macro breadth veto on relative score

                l_pass = (pl >= l_min_p) and (q_long >= 0.80)
                s_pass = (ps >= s_min_p) and (q_short >= 0.80)

                if not l_pass and not s_pass: continue

                is_buy = l_pass and (not s_pass or q_long >= q_short)
                p_win = pl if is_buy else ps
                ev = (p_win * ((tp_mult * atr) / px)) - ((1.0 - p_win) * ((sl_mult * atr) / px)) - (friction_bps / 10000.0)

                if ev > 0:
                    cands.append({"sym": sym, "is_buy": is_buy, "ev": ev, "px": px, "atr": atr, "p_win": p_win, "q_score": q_long if is_buy else q_short})

            alloc = 0
            for cand in sorted(cands, key=lambda x: x["q_score"], reverse=True):
                if alloc >= 2 or len(open_pos) >= 5: break
                is_buy = cand["is_buy"]
                if (is_buy and long_c >= 3) or (not is_buy and short_c >= 3): continue

                raw_tokens = (equity * risk_pct) / max(1e-6, sl_mult * cand["atr"])
                target_notional = min(equity * 0.40, raw_tokens * cand["px"])
                raw_tokens = target_notional / cand["px"]

                if raw_tokens <= 0 or target_notional < 15.0: continue

                open_pos[cand["sym"]] = {
                    "is_buy": is_buy, "entry_px": cand["px"], "entry_b_idx": b_idx,
                    "size": raw_tokens, "notional": target_notional, "p_raw": cand["p_win"],
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
    peak = pd.Series(curve).cummax()
    max_dd = ((pd.Series(curve) - peak) / peak).min() * 100.0
    wins = df_t[df_t["net"] > 0]["net"].sum() if not df_t.empty else 0.0
    loss = abs(df_t[df_t["net"] <= 0]["net"].sum()) if not df_t.empty else 1.0
    pf = wins / loss
    wr = df_t["win"].mean() * 100.0 if not df_t.empty else 0.0

    long_trades = df_t[df_t["side"] == "LONG"]
    short_trades = df_t[df_t["side"] == "SHORT"]
    long_pnl = long_trades["net"].sum() if not long_trades.empty else 0.0
    short_pnl = short_trades["net"].sum() if not short_trades.empty else 0.0

    return tot_ret, max_dd, pf, wr, len(df_t), long_pnl, short_pnl

configs = [
    {"name": "Quantile Norm A (Top 15% Thresholds: L>=0.49, S>=0.61)", "l_thresh": 0.49, "s_thresh": 0.61, "tp": 2.6, "sl": 1.4, "hold": 8, "risk": 0.020, "chop": 0.45},
    {"name": "Quantile Norm B (Top 10% Thresholds: L>=0.52, S>=0.65)", "l_thresh": 0.52, "s_thresh": 0.65, "tp": 2.8, "sl": 1.4, "hold": 9, "risk": 0.025, "chop": 0.45},
    {"name": "Quantile Norm C (Asymmetric Convexity: 3.0x TP / 1.4x SL)", "l_thresh": 0.50, "s_thresh": 0.63, "tp": 3.0, "sl": 1.4, "hold": 10, "risk": 0.025, "chop": 0.45},
]

print("\n" + "=" * 110)
print("              EVALUATION OF QUANTILE-NORMALIZED RELATIVE CONVICTION POLICIES              ")
print("=" * 110)

results = []
for c in configs:
    is_ret, is_dd, is_pf, is_wr, is_n, is_lpnl, is_spnl = simulate_quantile_policy(c, train_bars, train_dict, 12.0)
    oos_ret, oos_dd, oos_pf, oos_wr, oos_n, oos_lpnl, oos_spnl = simulate_quantile_policy(c, oos_bars, oos_dict, 12.0)
    oos_20 = simulate_quantile_policy(c, oos_bars, oos_dict, 20.0)[2]

    results.append({
        "Policy": c["name"],
        "IS Ret": f"{is_ret:>+6.1f}%",
        "IS PF": round(is_pf, 2),
        "IS Long PnL": f"${is_lpnl:>+6.1f}",
        "IS Short PnL": f"${is_spnl:>+6.1f}",
        "OOS Ret": f"{oos_ret:>+6.1f}%",
        "OOS PF": round(oos_pf, 2),
        "OOS Long PnL": f"${oos_lpnl:>+6.1f}",
        "OOS Short PnL": f"${oos_spnl:>+6.1f}",
        "OOS @20bp": round(oos_20, 2)
    })

print(pd.DataFrame(results).to_string(index=False))
print("=" * 110)
