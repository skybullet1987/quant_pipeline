import pandas as pd
import numpy as np
from run_full_365d_lifecycle import (
    df, unique_bars, bar_snaps, HOLD_BARS,
    LONG_TP_MULT, LONG_SL_MULT, SHORT_TP_MULT, SHORT_SL_MULT
)

def evaluate_long_tuning(l_p, bbw_max, risk_frac=0.04, max_lev=2.4, friction_bps=12.0):
    equity = 1000.0
    open_pos, closed_trades, curve = {}, [], []
    fee_rate = friction_bps / 10000.0

    for b_idx, ts in enumerate(unique_bars):
        b_df = bar_snaps[ts]
        if b_df.empty:
            curve.append(equity)
            continue
            
        px_map = b_df.set_index("asset")["close"].to_dict()
        op_map = b_df.set_index("asset")["open"].to_dict()
        hi_map = b_df.set_index("asset")["high"].to_dict()
        lo_map = b_df.set_index("asset")["low"].to_dict()

        # Update Open Positions
        closed = []
        for sym, pos in list(open_pos.items()):
            if sym not in px_map: continue
            o, h, l, c = op_map[sym], hi_map[sym], lo_map[sym], px_map[sym]
            atr = pos["entry_atr"]
            pos["highest"] = max(pos["highest"], h)
            pos["lowest"] = min(pos["lowest"], l)
            b_held = b_idx - pos["entry_bar"]

            if pos["dir"] == 1:
                if (pos["highest"] - pos["entry_px"]) >= (1.8 * atr) and not pos["ratchet_hit"]:
                    pos["ratchet_hit"] = True
                    pos["current_sl"] = max(pos["current_sl"], pos["entry_px"] + (0.20 * atr))
                pos["current_sl"] = max(pos["current_sl"], pos["highest"] - (2.0 * atr))

                hit_tp = (h >= pos["tp_px"])
                hit_sl = (l <= pos["current_sl"])
                hit_time = (not hit_tp and not hit_sl and b_held >= HOLD_BARS)

                if hit_tp and hit_sl: exit_p = pos["tp_px"] if abs(o - pos["tp_px"]) <= abs(o - pos["current_sl"]) else pos["current_sl"]
                elif hit_tp: exit_p = pos["tp_px"]
                elif hit_sl: exit_p = pos["current_sl"]
                elif hit_time: exit_p = c
                else: exit_p = None

                if exit_p is not None:
                    net_pnl = (pos["size_usd"] * ((exit_p / pos["entry_px"]) - 1.0)) - (pos["size_usd"] * fee_rate)
                    equity += net_pnl
                    closed_trades.append({"asset": sym, "dir": "LONG", "pnl": net_pnl, "win": net_pnl > 0})
                    closed.append(sym)

            elif pos["dir"] == -1:
                hit_tp = (l <= pos["tp_px"])
                hit_sl = (h >= pos["sl_px"])
                hit_time = (not hit_tp and not hit_sl and b_held >= 6)

                if hit_tp and hit_sl: exit_p = pos["tp_px"] if abs(o - pos["tp_px"]) <= abs(o - pos["sl_px"]) else pos["sl_px"]
                elif hit_tp: exit_p = pos["tp_px"]
                elif hit_sl: exit_p = pos["sl_px"]
                elif hit_time: exit_p = c
                else: exit_p = None

                if exit_p is not None:
                    net_pnl = (pos["size_usd"] * (1.0 - (exit_p / pos["entry_px"]))) - (pos["size_usd"] * fee_rate)
                    equity += net_pnl
                    closed_trades.append({"asset": sym, "dir": "SHORT", "pnl": net_pnl, "win": net_pnl > 0})
                    closed.append(sym)

        for s in closed: del open_pos[s]

        # Entry logic
        reg = str(b_df["regime"].iloc[0])
        mbi = b_df["mbi"].iloc[0]

        valid_l = b_df[(b_df["p_long"] >= l_p) & (b_df["dist_ema20_atr"].between(0.10, 1.35)) & (b_df["bbw_pct_40"] <= bbw_max)]
        valid_s = b_df[(b_df["p_short"] >= 0.56) & (b_df["dist_ema20_atr"] < 0.0)]

        top_l = valid_l.sort_values(by="p_long", ascending=False).head(2)
        top_s = valid_s.sort_values(by="p_short", ascending=False).head(2)

        available_slots = 2 - len(open_pos)
        if available_slots > 0 and equity > 50.0:
            pending = []
            if (reg in ["0", "1"] or mbi >= 0.55) and reg != "2":
                for _, row in top_l.iterrows():
                    sym = row["asset"]
                    if sym not in open_pos and len(pending) < available_slots:
                        atr = row["atr"]
                        sl_dist = LONG_SL_MULT * atr
                        size = (equity * risk_frac) / max(1e-6, sl_dist / row["close"])
                        pending.append({"asset": sym, "dir": 1, "price": row["close"], "size": size, "atr": atr, "tp": row["close"] + (LONG_TP_MULT * atr), "sl": row["close"] - sl_dist})

            if (reg in ["1", "2"] or mbi <= 0.45) and reg != "0":
                for _, row in top_s.iterrows():
                    sym = row["asset"]
                    if sym not in open_pos and (available_slots - len(pending)) > 0:
                        atr = row["atr"]
                        sl_dist = SHORT_SL_MULT * atr
                        size = (equity * risk_frac) / max(1e-6, sl_dist / row["close"])
                        pending.append({"asset": sym, "dir": -1, "price": row["close"], "size": size, "atr": atr, "tp": row["close"] - (SHORT_TP_MULT * atr), "sl": row["close"] + sl_dist})

            if pending:
                tot_req = sum(p["size"] for p in pending)
                curr_lev = tot_req / equity
                if curr_lev > max_lev:
                    for p in pending: p["size"] *= (max_lev / curr_lev)

                for p in pending:
                    open_pos[p["asset"]] = {"dir": p["dir"], "entry_px": p["price"], "entry_bar": b_idx, "entry_atr": p["atr"], "size_usd": p["size"], "tp_px": p["tp"], "sl_px": p["sl"], "current_sl": p["sl"], "highest": p["price"], "lowest": p["price"], "ratchet_hit": False}

        curve.append(equity)

    df_t = pd.DataFrame(closed_trades)
    e_end = curve[-1]
    mult = e_end / 1000.0
    tot_ret = ((e_end - 1000.0) / 1000.0) * 100.0
    peak = pd.Series(curve).cummax()
    max_dd = ((pd.Series(curve) - peak) / peak).min() * 100.0
    
    wins = df_t[df_t["pnl"] > 0]["pnl"].sum() if not df_t.empty else 0.0
    loss = abs(df_t[df_t["pnl"] <= 0]["pnl"].sum()) if not df_t.empty else 1.0
    pf = wins / loss
    wr = df_t["win"].mean() * 100.0 if not df_t.empty else 0.0

    l_t = df_t[df_t["dir"] == "LONG"]
    s_t = df_t[df_t["dir"] == "SHORT"]

    return mult, tot_ret, e_end, max_dd, pf, wr, len(df_t), len(l_t), len(s_t), l_t["pnl"].sum(), s_t["pnl"].sum()

print("\n" + "=" * 115)
print("             CALIBRATING LONG PARTICIPATION TO ACHIEVE 10x COMPOUNDING             ")
print("=" * 115)

configs = [
    ("Baseline Conservative", 0.60, 0.45, 0.038),
    ("Balanced Squeeze (p>=0.56, BBW<=0.55)", 0.56, 0.55, 0.040),
    ("Growth Squeeze (p>=0.54, BBW<=0.60)", 0.54, 0.60, 0.042),
    ("High-Convexity (p>=0.52, BBW<=0.65)", 0.52, 0.65, 0.045)
]

records = []
for label, p_l, bbw, rf in configs:
    m, ret, end_cap, dd, pf, wr, n, n_l, n_s, pnl_l, pnl_s = evaluate_long_tuning(p_l, bbw, risk_frac=rf, friction_bps=12.0)
    # Maker test
    m_mk, _, end_mk, _, _, _, _, _, _, _, _ = evaluate_long_tuning(p_l, bbw, risk_frac=rf, friction_bps=3.0)
    records.append({
        "Configuration": label,
        "Taker 12bps": f"{m:>5.2f}x (${end_cap:>7.0f})",
        "Maker 3bps": f"{m_mk:>5.2f}x (${end_mk:>7.0f})",
        "Max Drawdown": f"{dd:>6.1f}%",
        "PF": round(pf, 2),
        "Win Rate": f"{wr:>4.1f}%",
        "Trades (L / S)": f"{n} ({n_l} / {n_s})",
        "Long PnL": f"${pnl_l:>+6.0f}",
        "Short PnL": f"${pnl_s:>+6.0f}"
    })

print(pd.DataFrame(records).to_string(index=False))
print("=" * 115)
