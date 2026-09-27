import pandas as pd
from tactical_regime import TacticalRegimeEngine
from optimizer_cache import load_and_cache_dataset
from optimizer_sim import INITIAL_CAPITAL

train_bars, train_dict, oos_bars, oos_dict = load_and_cache_dataset(270, 90)
tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)

# Trial 127 Parameters
params = {
    "tp_atr_mult": 4.20, "sl_atr_mult": 1.60, "risk_budget_pct": 0.010,
    "max_slot_equity_pct": 0.35, "max_longs": 2, "max_shorts": 3,
    "max_net_imbalance": 2, "max_hold_bars": 10, "long_hurdle_boost": 0.06,
    "short_hurdle_boost": 0.00, "chop_filter_threshold": 0.45,
    "max_trades_per_bar": 1, "btc_bull_veto_pct": 0.025
}

open_pos, cooldowns, trades = {}, {}, []

for b_idx, b_dict in enumerate(oos_dict):
    b_ts = oos_bars[b_idx]
    closed = []

    for sym, pos in list(open_pos.items()):
        r = b_dict.get(sym)
        if not r: continue
        h, l, c = r["high"], r["low"], r["close"]
        hit_tp, hit_sl, hit_time, exit_px, exit_reason = False, False, False, c, "TIME"

        if pos["is_buy"]:
            if l <= pos["sl_px"]: hit_sl, exit_px, exit_reason = True, pos["sl_px"], "SL"
            elif h >= pos["tp_px"]: hit_tp, exit_px, exit_reason = True, pos["tp_px"], "TP"
        else:
            if h >= pos["sl_px"]: hit_sl, exit_px, exit_reason = True, pos["sl_px"], "SL"
            elif l <= pos["tp_px"]: hit_tp, exit_px, exit_reason = True, pos["tp_px"], "TP"

        if not hit_tp and not hit_sl and (b_idx - pos["entry_b_idx"]) >= params["max_hold_bars"]:
            hit_time = True

        if hit_tp or hit_sl or hit_time:
            gross = ((exit_px - pos["entry_px"]) if pos["is_buy"] else (pos["entry_px"] - exit_px)) * pos["size"]
            net = gross - ((pos["notional"] + (exit_px * pos["size"])) * (12.0 / 10000.0 / 2.0))
            trades.append({
                "ticker": sym, "side": "LONG" if pos["is_buy"] else "SHORT",
                "exit_reason": exit_reason, "p_entry": pos["p_win"], "regime": pos["regime"],
                "net_pnl": net, "win": net > 0
            })
            closed.append(sym)
            cooldowns[sym] = b_ts

    for s in closed: del open_pos[s]

    free = max(0, 5 - len(open_pos))
    long_c = sum(1 for p in open_pos.values() if p["is_buy"])
    short_c = sum(1 for p in open_pos.values() if not p["is_buy"])

    if free > 0 and b_dict:
        first_v = next(iter(b_dict.values()))
        b_ret4h, breadth = first_v["btc_ret_4h"], first_v["market_breadth"]
        is_bull_t = (b_ret4h >= params["btc_bull_veto_pct"] and breadth >= 0.60)

        cands = []
        for sym, r in b_dict.items():
            pl, ps, pc, px, atr = r["p_long"], r["p_short"], r["p_chop"], r["close"], r["atr"]
            if px <= 0 or atr <= 0 or cooldowns.get(sym) == b_ts or sym in open_pos: continue

            state = tactical_engine.evaluate_state(
                slow_regime=int(r["regime"]) if str(r["regime"]).isdigit() else 1,
                btc_ret_1h=r["btc_ret_1h"], btc_ret_4h=b_ret4h,
                market_breadth_sma20=breadth, vol_expansion_ratio=r["vol_expansion_ratio"]
            )

            lh = state["long_hurdle"] + params["long_hurdle_boost"]
            sh = state["short_hurdle"] + params["short_hurdle_boost"] + (0.15 if is_bull_t else 0.0)
            if pc >= params["chop_filter_threshold"] or (pl < lh and ps < sh): continue

            is_buy = (pl >= lh) and (ps < sh or pl >= ps)
            p_win = pl if is_buy else ps
            ev = (p_win * ((params["tp_atr_mult"] * atr) / px)) - ((1.0 - p_win) * ((params["sl_atr_mult"] * atr) / px)) - (12.0 / 10000.0)

            if ev > 0:
                cands.append({"sym": sym, "is_buy": is_buy, "ev": ev, "px": px, "atr": atr, "p_win": p_win, "regime": r["regime"]})

        alloc = 0
        for cand in sorted(cands, key=lambda x: x["ev"], reverse=True):
            if alloc >= 1 or len(open_pos) >= 5: break
            is_buy = cand["is_buy"]
            if (is_buy and long_c >= params["max_longs"]) or (not is_buy and short_c >= params["max_shorts"]): continue
            if abs((long_c + (1 if is_buy else 0)) - (short_c + (0 if is_buy else 1))) > params["max_net_imbalance"]: continue

            raw_tokens = (1000.0 * params["risk_budget_pct"]) / max(1e-6, params["sl_atr_mult"] * cand["atr"])
            target_notional = min(1000.0 * params["max_slot_equity_pct"], raw_tokens * cand["px"])
            raw_tokens = target_notional / cand["px"]

            if raw_tokens <= 0 or target_notional < 15.0: continue

            open_pos[cand["sym"]] = {
                "is_buy": is_buy, "entry_px": cand["px"], "entry_b_idx": b_idx,
                "size": raw_tokens, "notional": target_notional, "p_win": cand["p_win"], "regime": cand["regime"],
                "tp_px": cand["px"] + (params["tp_atr_mult"] * cand["atr"]) if is_buy else cand["px"] - (params["tp_atr_mult"] * cand["atr"]),
                "sl_px": cand["px"] - (params["sl_atr_mult"] * cand["atr"]) if is_buy else cand["px"] + (params["sl_atr_mult"] * cand["atr"])
            }
            if is_buy: long_c += 1
            else: short_c += 1
            alloc += 1

df_t = pd.DataFrame(trades)
print("=" * 70)
print(f"OUT-OF-SAMPLE ATTRIBUTION ({len(df_t)} Trades)")
print("=" * 70)
print("\n1. EXIT REASON BREAKDOWN:")
print(df_t.groupby("exit_reason").agg(trades=("net_pnl", "count"), win_rate=("win", lambda x: f"{x.mean()*100:.1f}%"), net_pnl=("net_pnl", "sum")))

print("\n2. DIRECTIONAL ATTRIBUTION:")
print(df_t.groupby("side").agg(trades=("net_pnl", "count"), win_rate=("win", lambda x: f"{x.mean()*100:.1f}%"), net_pnl=("net_pnl", "sum")))

print("\n3. REGIME BREAKDOWN:")
print(df_t.groupby("regime").agg(trades=("net_pnl", "count"), win_rate=("win", lambda x: f"{x.mean()*100:.1f}%"), net_pnl=("net_pnl", "sum")))
print("=" * 70)
