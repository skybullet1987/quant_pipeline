import os, sys, warnings
PROJECT_ROOT = os.path.abspath(os.getenv("QUANT_PROJECT_ROOT", "/home/skybullet1987/quant_pipeline"))
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
df = pd.read_parquet(f"{PROJECT_ROOT}/data/oos_scored_mart.parquet")
df["timestamp"] = pd.to_datetime(df["timestamp"])

all_ts = sorted(df["timestamp"].unique())
split_idx = int(len(all_ts) * 0.65)
oos_ts = all_ts[split_idx:]

friction_rate = (0.00035 + 0.00020) * 2

def run_sim(target_ts, split_ratio, tp1_mult, trail_mult, sl_act_mult, is_base=False):
    equity = 500.00
    equity_curve = [equity]
    trades, active_positions, cooldown = [], {}, {}
    
    for t_idx, ts in enumerate(target_ts):
        bar_df = df[df["timestamp"] == ts].set_index("asset")
        if bar_df.empty:
            continue
        p_bull = float(bar_df["p_bull"].iloc[0])
        p_bear = float(bar_df["p_bear"].iloc[0])
        btc_bull = bool(bar_df["btc_above_ema20"].iloc[0])

        # Resolve Exits (Pessimistic: Stop-Loss Checked First)
        closed_syms = []
        for sym, pos in active_positions.items():
            if sym not in bar_df.index:
                continue
            c_row = bar_df.loc[sym]
            c_high, c_low, c_close = float(c_row["high"]), float(c_row["low"]), float(c_row["close"])
            bars_held = t_idx - pos["entry_bar"]

            if is_base:
                hit_tp, hit_sl, time_exit = False, False, False
                exit_px = c_close
                if pos["side"] == "LONG":
                    if c_low <= pos["sl_px"]: hit_sl, exit_px = True, pos["sl_px"]
                    elif c_high >= pos["tp_px"]: hit_tp, exit_px = True, pos["tp_px"]
                    elif bars_held >= 18: time_exit, exit_px = True, c_close
                else:
                    if c_high >= pos["sl_px"]: hit_sl, exit_px = True, pos["sl_px"]
                    elif c_low <= pos["tp_px"]: hit_tp, exit_px = True, pos["tp_px"]
                    elif bars_held >= 18: time_exit, exit_px = True, c_close

                if hit_tp or hit_sl or time_exit:
                    ret_m = (exit_px - pos["entry_price"]) / pos["entry_price"] if pos["side"] == "LONG" else (pos["entry_price"] - exit_px) / pos["entry_price"]
                    pnl = (pos["notional"] * ret_m) - (pos["notional"] * friction_rate)
                    equity += pnl
                    trades.append({"pnl": pnl})
                    closed_syms.append(sym)
                    cooldown[sym] = t_idx
            else:
                stopped_out = (c_low <= pos["sl_px"]) if pos["side"] == "LONG" else (c_high >= pos["sl_px"])
                if stopped_out:
                    rem_ntl = (pos["notional_a"] if not pos["tranche_a_closed"] else 0.0) + pos["notional_b"]
                    exit_px = pos["sl_px"]
                    ret_m = (exit_px - pos["entry_price"]) / pos["entry_price"] if pos["side"] == "LONG" else (pos["entry_price"] - exit_px) / pos["entry_price"]
                    equity += (rem_ntl * ret_m) - (rem_ntl * friction_rate)
                    trades.append({"pnl": (rem_ntl * ret_m) - (rem_ntl * friction_rate)})
                    closed_syms.append(sym)
                    cooldown[sym] = t_idx
                    continue

                if not pos["tranche_a_closed"]:
                    hit_tp1 = (c_high >= pos["tp1_px"]) if pos["side"] == "LONG" else (c_low <= pos["tp1_px"])
                    if hit_tp1:
                        pnl_a = (pos["notional_a"] * ((pos["tp1_px"] - pos["entry_price"] if pos["side"] == "LONG" else pos["entry_price"] - pos["tp1_px"]) / pos["entry_price"])) - (pos["notional_a"] * friction_rate)
                        equity += pnl_a
                        pos["tranche_a_closed"] = True
                        pos["sl_px"] = pos["entry_price"] + (sl_act_mult * pos["atr"]) if pos["side"] == "LONG" else pos["entry_price"] - (sl_act_mult * pos["atr"])
                        pos["runner_best"] = pos["tp1_px"]

                if pos["tranche_a_closed"] and pos["notional_b"] > 0:
                    if pos["side"] == "LONG" and c_high > pos["runner_best"]:
                        pos["runner_best"] = c_high
                        pos["sl_px"] = max(pos["sl_px"], pos["runner_best"] - (trail_mult * pos["atr"]))
                    elif pos["side"] == "SHORT" and c_low < pos["runner_best"]:
                        pos["runner_best"] = c_low
                        pos["sl_px"] = min(pos["sl_px"], pos["runner_best"] + (trail_mult * pos["atr"]))

                if bars_held >= 18:
                    rem_ntl = (pos["notional_a"] if not pos["tranche_a_closed"] else 0.0) + pos["notional_b"]
                    ret_m = (c_close - pos["entry_price"]) / pos["entry_price"] if pos["side"] == "LONG" else (pos["entry_price"] - c_close) / pos["entry_price"]
                    equity += (rem_ntl * ret_m) - (rem_ntl * friction_rate)
                    trades.append({"pnl": (rem_ntl * ret_m) - (rem_ntl * friction_rate)})
                    closed_syms.append(sym)
                    cooldown[sym] = t_idx

        for s in closed_syms:
            del active_positions[s]

        # Sizing / Entry Allocation
        open_slots = 2 - len(active_positions)
        if open_slots > 0:
            el = [s for s in bar_df.index if s not in active_positions and (t_idx - cooldown.get(s, -99)) >= 3]
            if p_bear >= 0.40:
                cands = bar_df.loc[el]
                cands = cands[(cands["p_model_short"] >= 0.245) & (cands["mom_24h"] < 0.0)].sort_values(by="p_model_short", ascending=False).head(open_slots)
                for sym, row in cands.iterrows():
                    px, atr = float(row["close"]), float(row["atr"])
                    slot_lev = float(np.clip(2.5 + (max(0.0, float(row["p_model_short"]) - 0.28) / 0.15 * 0.5), 2.5, 3.0))
                    ntl = equity * slot_lev
                    if is_base:
                        active_positions[sym] = {"side": "SHORT", "entry_price": px, "atr": atr, "notional": ntl, "tp_px": px - (3.2 * atr), "sl_px": px + (0.85 * atr), "entry_bar": t_idx}
                    else:
                        active_positions[sym] = {"side": "SHORT", "entry_price": px, "atr": atr, "entry_bar": t_idx, "notional_a": ntl * split_ratio, "notional_b": ntl * (1.0 - split_ratio), "tp1_px": px - (tp1_mult * atr), "sl_px": px + (0.85 * atr), "tranche_a_closed": False, "runner_best": px}
            elif p_bull >= 0.88 and btc_bull:
                cands = bar_df.loc[el]
                cands = cands[(cands["p_model_long"] >= 0.320) & (cands["mom_24h"] > 0.02)].sort_values(by="p_model_long", ascending=False).head(open_slots)
                for sym, row in cands.iterrows():
                    px, atr = float(row["close"]), float(row["atr"])
                    ntl = equity * 2.5
                    if is_base:
                        active_positions[sym] = {"side": "LONG", "entry_price": px, "atr": atr, "notional": ntl, "tp_px": px + (2.5 * atr), "sl_px": px - (1.0 * atr), "entry_bar": t_idx}
                    else:
                        active_positions[sym] = {"side": "LONG", "entry_price": px, "atr": atr, "entry_bar": t_idx, "notional_a": ntl * split_ratio, "notional_b": ntl * (1.0 - split_ratio), "tp1_px": px + (tp1_mult * atr), "sl_px": px - (1.0 * atr), "tranche_a_closed": False, "runner_best": px}

        equity_curve.append(equity)

    eq_s = pd.Series(equity_curve)
    mdd = abs(((eq_s - eq_s.cummax()) / eq_s.cummax()).min()) * 100
    ret_pct = ((equity - 500.0) / 500.0) * 100
    t_df = pd.DataFrame(trades)
    pf = (t_df[t_df["pnl"] > 0]["pnl"].sum() / abs(t_df[t_df["pnl"] < 0]["pnl"].sum())) if (len(t_df) > 0 and len(t_df[t_df["pnl"] < 0]) > 0) else np.nan

    return {
        "ending_eq": equity, "ret_pct": ret_pct, "mdd": mdd,
        "calmar": ret_pct / (mdd + 1e-8), "pf": pf, "trades": len(t_df)
    }

configs = [
    ("BASELINE (100% @ 3.2x ATR)", 1.0, 3.2, 2.5, 0.0, True),
    ("Champion 70/30 (TP1=2.0x, Trail=2.0x)", 0.70, 2.0, 2.0, 0.5, False),
    ("Simple 60/40 (TP1=2.0x, Trail=2.0x)", 0.60, 2.0, 2.0, 0.5, False),
    ("Robust 70/30 (TP1=1.8x, Trail=2.5x)", 0.70, 1.8, 2.5, 0.5, False)
]

print("\n" + "="*80)
print("             OUT-OF-SAMPLE (OOS: Last 35% Bars) RESULTS")
print("="*80)
oos_rows = []
for name, sp, tp1, tr, act, is_base in configs:
    r = run_sim(oos_ts, sp, tp1, tr, act, is_base)
    r["config"] = name
    oos_rows.append(r)
print(pd.DataFrame(oos_rows)[["config", "ending_eq", "ret_pct", "mdd", "calmar", "pf", "trades"]].to_string(index=False))

print("\n" + "="*80)
print("             FULL DATASET (IS + OOS: 539 Bars) RESULTS")
print("="*80)
full_rows = []
for name, sp, tp1, tr, act, is_base in configs:
    r = run_sim(all_ts, sp, tp1, tr, act, is_base)
    r["config"] = name
    full_rows.append(r)
print(pd.DataFrame(full_rows)[["config", "ending_eq", "ret_pct", "mdd", "calmar", "pf", "trades"]].to_string(index=False))
