import pandas as pd
import numpy as np
from tactical_regime import TacticalRegimeEngine
from optimizer_cache import load_and_cache_dataset

train_bars, train_dict, oos_bars, oos_dict = load_and_cache_dataset(270, 90)
tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)

def simulate_regime_policy(p, unique_bars, dict_bars, with_tactical_veto=True, friction_bps=12.0):
    equity = 1000.0
    open_pos, cooldowns, trades, curve = {}, {}, [], []

    for b_idx, b_dict in enumerate(dict_bars):
        b_ts = unique_bars[b_idx]
        closed = []

        # 1. Resolve active positions
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

            if not hit_tp and not hit_sl and (b_idx - pos["entry_b_idx"]) >= p["hold"]:
                hit_time, exit_px = True, c

            if hit_tp or hit_sl or hit_time:
                gross = ((exit_px - pos["entry_px"]) if pos["is_buy"] else (pos["entry_px"] - exit_px)) * pos["size"]
                fee = (pos["notional"] + (exit_px * pos["size"])) * (friction_bps / 10000.0 / 2.0)
                net = gross - fee
                equity += net
                trades.append({"net": net, "side": "LONG" if pos["is_buy"] else "SHORT", "win": net > 0})
                closed.append(sym)
                cooldowns[sym] = b_ts

        for s in closed: del open_pos[s]

        # 2. Gating & Allocation
        free = max(0, 5 - len(open_pos))
        long_c = sum(1 for pos in open_pos.values() if pos["is_buy"])
        short_c = sum(1 for pos in open_pos.values() if not pos["is_buy"])

        if free > 0 and equity > 100.0 and b_dict:
            first_v = next(iter(b_dict.values()))
            b_ret4h, breadth = first_v["btc_ret_4h"], first_v["market_breadth"]
            is_bull_t = (b_ret4h >= 0.025 and breadth >= 0.60) if with_tactical_veto else False

            cands = []
            for sym, r in b_dict.items():
                pl, ps, pc, px, atr = r["p_long"], r["p_short"], r["p_chop"], r["close"], r["atr"]
                if px <= 0 or atr <= 0 or cooldowns.get(sym) == b_ts or sym in open_pos: continue

                reg_val = str(r["regime"])
                state = tactical_engine.evaluate_state(
                    slow_regime=int(reg_val) if reg_val.isdigit() else 1,
                    btc_ret_1h=r["btc_ret_1h"], btc_ret_4h=b_ret4h,
                    market_breadth_sma20=breadth, vol_expansion_ratio=r["vol_expansion_ratio"]
                )

                if reg_val == "0":
                    lh_boost, sh_boost = p["r0_l_boost"], p["r0_s_boost"]
                elif reg_val == "2":
                    lh_boost, sh_boost = p["r2_l_boost"], p["r2_s_boost"]
                else:
                    lh_boost, sh_boost = p["r1_l_boost"], p["r1_s_boost"]

                lh = state["long_hurdle"] + lh_boost
                sh = state["short_hurdle"] + sh_boost + (0.15 if is_bull_t else 0.0)
                if pc >= p["chop"] or (pl < lh and ps < sh): continue

                is_buy = (pl >= lh) and (ps < sh or pl >= ps)
                p_win = pl if is_buy else ps
                ev = (p_win * ((p["tp"] * atr) / px)) - ((1.0 - p_win) * ((p["sl"] * atr) / px)) - (friction_bps / 10000.0)

                if ev > 0:
                    cands.append({"sym": sym, "is_buy": is_buy, "ev": ev, "px": px, "atr": atr, "p_win": p_win})

            alloc = 0
            for cand in sorted(cands, key=lambda x: x["ev"], reverse=True):
                if alloc >= 1 or len(open_pos) >= 5: break
                is_buy = cand["is_buy"]
                if (is_buy and long_c >= 3) or (not is_buy and short_c >= 3): continue
                if abs((long_c + (1 if is_buy else 0)) - (short_c + (0 if is_buy else 1))) > 2: continue

                raw_tokens = (equity * p["risk"]) / max(1e-6, p["sl"] * cand["atr"])
                target_notional = min(equity * 0.35, raw_tokens * cand["px"])
                raw_tokens = target_notional / cand["px"]

                if raw_tokens <= 0 or target_notional < 15.0: continue

                open_pos[cand["sym"]] = {
                    "is_buy": is_buy, "entry_px": cand["px"], "entry_b_idx": b_idx,
                    "size": raw_tokens, "notional": target_notional,
                    "tp_px": cand["px"] + (p["tp"] * cand["atr"]) if is_buy else cand["px"] - (p["tp"] * cand["atr"]),
                    "sl_px": cand["px"] - (p["sl"] * cand["atr"]) if is_buy else cand["px"] + (p["sl"] * cand["atr"])
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

    return tot_ret, max_dd, pf, wr, len(df_t)

policies = [
    {
        "name": "Policy A (2.6x TP / 1.4x SL)",
        "tp": 2.6, "sl": 1.4, "hold": 8, "risk": 0.015, "chop": 0.45,
        "r0_l_boost": 0.00, "r0_s_boost": 0.12,
        "r1_l_boost": 0.06, "r1_s_boost": 0.02,
        "r2_l_boost": 0.14, "r2_s_boost": -0.01
    },
    {
        "name": "Policy B (2.7x TP / 1.4x SL)",
        "tp": 2.7, "sl": 1.4, "hold": 8, "risk": 0.015, "chop": 0.45,
        "r0_l_boost": -0.02, "r0_s_boost": 0.14,
        "r1_l_boost": 0.08,  "r1_s_boost": 0.00,
        "r2_l_boost": 0.16,  "r2_s_boost": -0.02
    },
    {
        "name": "Policy C (2.5x TP / 1.4x SL)",
        "tp": 2.5, "sl": 1.4, "hold": 8, "risk": 0.012, "chop": 0.40,
        "r0_l_boost": 0.00, "r0_s_boost": 0.10,
        "r1_l_boost": 0.10, "r1_s_boost": 0.04,
        "r2_l_boost": 0.14, "r2_s_boost": 0.00
    }
]

records = []
for mode_name, has_veto in [("HMM + Tactical Veto", True), ("Pure HMM (No Veto)", False)]:
    for p in policies:
        is_ret, is_dd, is_pf, is_wr, is_tr = simulate_regime_policy(p, train_bars, train_dict, with_tactical_veto=has_veto, friction_bps=12.0)
        oos_ret, oos_dd, oos_pf, oos_wr, oos_tr = simulate_regime_policy(p, oos_bars, oos_dict, with_tactical_veto=has_veto, friction_bps=12.0)
        oos_20 = simulate_regime_policy(p, oos_bars, oos_dict, with_tactical_veto=has_veto, friction_bps=20.0)[2]
        oos_35 = simulate_regime_policy(p, oos_bars, oos_dict, with_tactical_veto=has_veto, friction_bps=35.0)[2]

        records.append({
            "Mode": mode_name,
            "Policy": p["name"],
            "IS Ret": f"{is_ret:>+6.1f}%",
            "IS PF": round(is_pf, 2),
            "IS DD": f"{is_dd:>5.1f}%",
            "IS N": is_tr,
            "OOS Ret": f"{oos_ret:>+6.1f}%",
            "OOS PF": round(oos_pf, 2),
            "OOS DD": f"{oos_dd:>5.1f}%",
            "OOS N": oos_tr,
            "20bps": round(oos_20, 2),
            "35bps": round(oos_35, 2)
        })

print("\n" + "=" * 115)
print("              REGIME-CONDITIONED ABLATION SWEEP (IS vs. OOS & FRICTION DEGRADATION)              ")
print("=" * 115)
df_out = pd.DataFrame(records)
print(df_out.to_string(index=False))
print("=" * 115)
