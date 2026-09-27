import pandas as pd
import numpy as np
from run_rigorous_stability_audit import (
    df, unique_bars, models_l, models_s, feature_cols,
    HOLD_BARS, LONG_TP_MULT, LONG_SL_MULT, SHORT_TP_MULT, SHORT_SL_MULT,
    cutoff_date
)

L_THRESH = 0.60
S_THRESH = 0.56
RISK_FRAC = 0.038
MAX_LEV = 2.4

print("--> Pre-computing model probabilities across all 365 days...")
df["p_long"], df["p_short"] = 0.50, 0.50
for r_val, g_idx in df.groupby("regime").groups.items():
    r_str = str(r_val)
    df.loc[g_idx, "p_long"] = models_l[r_str].predict_proba(df.loc[g_idx, feature_cols])[:, 1]
    df.loc[g_idx, "p_short"] = models_s[r_str].predict_proba(df.loc[g_idx, feature_cols])[:, 1]

bar_snaps = {ts: df[df["timestamp"] == ts].copy() for ts in unique_bars}

def simulate_lifecycle(bar_list, friction_bps=12.0):
    equity = 1000.0
    open_pos, closed_trades, curve = {}, [], []
    fee_rate = friction_bps / 10000.0

    for b_idx, ts in enumerate(bar_list):
        b_df = bar_snaps[ts]
        if b_df.empty:
            curve.append(equity)
            continue
            
        px_map = b_df.set_index("asset")["close"].to_dict()
        op_map = b_df.set_index("asset")["open"].to_dict()
        hi_map = b_df.set_index("asset")["high"].to_dict()
        lo_map = b_df.set_index("asset")["low"].to_dict()

        # 1. Update Existing Positions
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

                if hit_tp and hit_sl:
                    exit_p = pos["tp_px"] if abs(o - pos["tp_px"]) <= abs(o - pos["current_sl"]) else pos["current_sl"]
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

                if hit_tp and hit_sl:
                    exit_p = pos["tp_px"] if abs(o - pos["tp_px"]) <= abs(o - pos["sl_px"]) else pos["sl_px"]
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

        # 2. Score Universe & Enter Top 2
        reg = str(b_df["regime"].iloc[0])
        mbi = b_df["mbi"].iloc[0]

        valid_l = b_df[(b_df["p_long"] >= L_THRESH) & (b_df["dist_ema20_atr"].between(0.15, 1.25)) & (b_df["bbw_pct_40"] <= 0.45)]
        valid_s = b_df[(b_df["p_short"] >= S_THRESH) & (b_df["dist_ema20_atr"] < 0.0)]

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
                        size = (equity * RISK_FRAC) / max(1e-6, sl_dist / row["close"])
                        pending.append({
                            "asset": sym, "dir": 1, "price": row["close"], "size": size, "atr": atr,
                            "tp": row["close"] + (LONG_TP_MULT * atr), "sl": row["close"] - sl_dist
                        })

            if (reg in ["1", "2"] or mbi <= 0.45) and reg != "0":
                for _, row in top_s.iterrows():
                    sym = row["asset"]
                    if sym not in open_pos and (available_slots - len(pending)) > 0:
                        atr = row["atr"]
                        sl_dist = SHORT_SL_MULT * atr
                        size = (equity * RISK_FRAC) / max(1e-6, sl_dist / row["close"])
                        pending.append({
                            "asset": sym, "dir": -1, "price": row["close"], "size": size, "atr": atr,
                            "tp": row["close"] - (SHORT_TP_MULT * atr), "sl": row["close"] + sl_dist
                        })

            if pending:
                tot_req = sum(p["size"] for p in pending)
                curr_lev = tot_req / equity
                if curr_lev > MAX_LEV:
                    for p in pending: p["size"] *= (MAX_LEV / curr_lev)

                for p in pending:
                    open_pos[p["asset"]] = {
                        "dir": p["dir"], "entry_px": p["price"], "entry_bar": b_idx, "entry_atr": p["atr"],
                        "size_usd": p["size"], "tp_px": p["tp"], "sl_px": p["sl"], "current_sl": p["sl"],
                        "highest": p["price"], "lowest": p["price"], "ratchet_hit": False
                    }

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

print("\n" + "=" * 110)
print("             PRODUCTION CANDIDATE: FULL 365-DAY MULTI-TIER FRICTION STRESS TEST             ")
print("=" * 110)

tiers = [
    ("Optimistic Maker (Post-Only)", 3.0),
    ("Baseline Production (12 bps)", 12.0),
    ("Moderate Stress (20 bps)", 20.0),
    ("Severe Friction (25 bps)", 25.0)
]

records = []
for label, bps in tiers:
    m, ret, end_cap, dd, pf, wr, n, n_l, n_s, pnl_l, pnl_s = simulate_lifecycle(unique_bars, bps)
    records.append({
        "Friction Regime": label,
        "Multiple": f"{m:>5.2f}x",
        "Total Return": f"{ret:>+7.1f}%",
        "Ending Equity": f"${end_cap:>8.2f}",
        "Max Drawdown": f"{dd:>6.1f}%",
        "Profit Factor": round(pf, 2),
        "Win Rate": f"{wr:>4.1f}%",
        "Total Trades": n,
        "Long (N / PnL)": f"{n_l} / ${pnl_l:>+6.0f}",
        "Short (N / PnL)": f"{n_s} / ${pnl_s:>+6.0f}"
    })

print(pd.DataFrame(records).to_string(index=False))

print("\n" + "=" * 110)
print("             IN-SAMPLE (275d) VS OUT-OF-SAMPLE (90d) PARTITION AUDIT             ")
print("=" * 110)

is_bars = [ts for ts in unique_bars if ts < cutoff_date]
oos_bars = [ts for ts in unique_bars if ts >= cutoff_date]

m_is, ret_is, end_is, dd_is, pf_is, wr_is, n_is, nl_is, ns_is, pl_is, ps_is = simulate_lifecycle(is_bars, 12.0)
m_oos, ret_oos, end_oos, dd_oos, pf_oos, wr_oos, n_oos, nl_oos, ns_oos, pl_oos, ps_oos = simulate_lifecycle(oos_bars, 12.0)

split_recs = [
    {"Split": "In-Sample (275 Days)", "Multiple": f"{m_is:.2f}x", "Return": f"{ret_is:>+6.1f}%", "End Equity": f"${end_is:>7.2f}", "MaxDD": f"{dd_is:>5.1f}%", "PF": round(pf_is, 2), "WinRate": f"{wr_is:.1f}%", "Trades": n_is, "Long PnL": f"${pl_is:.0f}", "Short PnL": f"${ps_is:.0f}"},
    {"Split": "Out-of-Sample (90 Days)", "Multiple": f"{m_oos:.2f}x", "Return": f"{ret_oos:>+6.1f}%", "End Equity": f"${end_oos:>7.2f}", "MaxDD": f"{dd_oos:>5.1f}%", "PF": round(pf_oos, 2), "WinRate": f"{wr_oos:.1f}%", "Trades": n_oos, "Long PnL": f"${pl_oos:.0f}", "Short PnL": f"${ps_oos:.0f}"}
]
print(pd.DataFrame(split_recs).to_string(index=False))
print("=" * 110)
