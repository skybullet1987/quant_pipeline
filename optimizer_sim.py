import pandas as pd
import numpy as np

INITIAL_CAPITAL = 1000.0

def simulate_policy_fast(params, unique_bars, dict_bars, tactical_engine, friction_bps=12.0):
    equity = INITIAL_CAPITAL
    open_pos, cooldowns, trades, curve, trans_trades = {}, {}, [], [], []

    tp_mult, sl_mult = params["tp_atr_mult"], params["sl_atr_mult"]
    risk_pct, max_slot_pct = params["risk_budget_pct"], params["max_slot_equity_pct"]
    max_longs, max_shorts = params["max_longs"], params["max_shorts"]
    max_net_imb, max_hold = params["max_net_imbalance"], params["max_hold_bars"]
    l_boost, s_boost = params["long_hurdle_boost"], params["short_hurdle_boost"]
    chop_th, max_alloc = params["chop_filter_threshold"], params["max_trades_per_bar"]
    btc_veto = params.get("btc_bull_veto_pct", 0.025)

    for b_idx, b_dict in enumerate(dict_bars):
        b_ts = unique_bars[b_idx]
        closed = []

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

            if not hit_tp and not hit_sl and (b_idx - pos["entry_b_idx"]) >= max_hold:
                hit_time, exit_px = True, c

            if hit_tp or hit_sl or hit_time:
                gross = ((exit_px - pos["entry_px"]) if pos["is_buy"] else (pos["entry_px"] - exit_px)) * pos["size"]
                net = gross - ((pos["notional"] + (exit_px * pos["size"])) * (friction_bps / 10000.0 / 2.0))
                equity += net
                trades.append({"net": net, "win": net > 0})
                if pos.get("is_trans", False): trans_trades.append(net)
                closed.append(sym)
                cooldowns[sym] = b_ts

        for s in closed: del open_pos[s]

        free = max(0, 5 - len(open_pos))
        long_c = sum(1 for p in open_pos.values() if p["is_buy"])
        short_c = sum(1 for p in open_pos.values() if not p["is_buy"])

        if free > 0 and equity > 100.0 and b_dict:
            first_v = next(iter(b_dict.values()))
            b_ret4h, breadth = first_v["btc_ret_4h"], first_v["market_breadth"]
            is_bull_t = (b_ret4h >= btc_veto and breadth >= 0.60)

            cands = []
            for sym, r in b_dict.items():
                pl, ps, pc, px, atr = r["p_long"], r["p_short"], r["p_chop"], r["close"], r["atr"]
                if px <= 0 or atr <= 0 or cooldowns.get(sym) == b_ts or sym in open_pos: continue

                state = tactical_engine.evaluate_state(
                    slow_regime=int(r["regime"]) if str(r["regime"]).isdigit() else 1,
                    btc_ret_1h=r["btc_ret_1h"], btc_ret_4h=b_ret4h,
                    market_breadth_sma20=breadth, vol_expansion_ratio=r["vol_expansion_ratio"]
                )

                lh = state["long_hurdle"] + l_boost
                sh = state["short_hurdle"] + s_boost + (0.15 if is_bull_t else 0.0)
                if pc >= chop_th or (pl < lh and ps < sh): continue

                is_buy = (pl >= lh) and (ps < sh or pl >= ps)
                p_win = pl if is_buy else ps
                ev = (p_win * ((tp_mult * atr) / px)) - ((1.0 - p_win) * ((sl_mult * atr) / px)) - (friction_bps / 10000.0)

                if ev > 0:
                    cands.append({"sym": sym, "is_buy": is_buy, "ev": ev, "px": px, "atr": atr, "p_win": p_win, "is_trans": is_bull_t})

            alloc = 0
            for cand in sorted(cands, key=lambda x: x["ev"], reverse=True):
                if alloc >= max_alloc or len(open_pos) >= 5: break
                is_buy = cand["is_buy"]
                if (is_buy and long_c >= max_longs) or (not is_buy and short_c >= max_shorts): continue
                if abs((long_c + (1 if is_buy else 0)) - (short_c + (0 if is_buy else 1))) > max_net_imb: continue

                raw_tokens = (equity * risk_pct) / max(1e-6, sl_mult * cand["atr"])
                target_notional = min(equity * max_slot_pct, raw_tokens * cand["px"])
                raw_tokens = target_notional / cand["px"]

                if raw_tokens <= 0 or target_notional < 15.0: continue

                open_pos[cand["sym"]] = {
                    "is_buy": is_buy, "entry_px": cand["px"], "entry_b_idx": b_idx,
                    "size": raw_tokens, "notional": target_notional,
                    "tp_px": cand["px"] + (tp_mult * cand["atr"]) if is_buy else cand["px"] - (tp_mult * cand["atr"]),
                    "sl_px": cand["px"] - (sl_mult * cand["atr"]) if is_buy else cand["px"] + (sl_mult * cand["atr"]),
                    "is_trans": cand["is_trans"]
                }
                if is_buy: long_c += 1
                else: short_c += 1
                alloc += 1

        curve.append(equity)

    if not trades or len(trades) < 50:
        return -100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, INITIAL_CAPITAL, 0.0

    e_end = curve[-1]
    tot_ret = ((e_end - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100.0
    days = max(1.0, (unique_bars[-1] - unique_bars[0]).total_seconds() / 86400.0)
    cagr = ((e_end / INITIAL_CAPITAL) ** (365.25 / days) - 1.0) * 100.0

    peak = pd.Series(curve).cummax()
    max_dd = ((pd.Series(curve) - peak) / peak).min() * 100.0

    wins = [t["net"] for t in trades if t["net"] > 0]
    losses = [abs(t["net"]) for t in trades if t["net"] <= 0]
    pf = (sum(wins) / sum(losses)) if sum(losses) > 0 else 0.0
    wr = (len(wins) / len(trades)) * 100.0
    exp = sum(t["net"] for t in trades) / len(trades)

    if abs(max_dd) > 25.0 or e_end < INITIAL_CAPITAL:
        score = -50.0
    else:
        score = ((cagr / abs(max_dd)) * 0.40) + (pf * 10.0) + (exp * 2.0)

    return score, tot_ret, cagr, max_dd, pf, wr, len(trades), e_end, sum(trans_trades)
