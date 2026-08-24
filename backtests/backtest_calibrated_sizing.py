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

def run_sizing_sim(target_ts, sizing_mode="calibrated"):
    equity = 500.00
    equity_curve = [equity]
    trades, active_positions, cooldown = [], {}, {}
    
    for t_idx, ts in enumerate(target_ts):
        bar_df = df[df["timestamp"] == ts].set_index("asset")
        if bar_df.empty:
            continue
        p_bear = float(bar_df["p_bear"].iloc[0])
        p_bull = float(bar_df["p_bull"].iloc[0])
        btc_bull = bool(bar_df["btc_above_ema20"].iloc[0])

        # Resolve Exits (70/30 Architecture: TP1=1.8x, Trail=2.5x, Act=+0.5x)
        closed_syms = []
        for sym, pos in active_positions.items():
            if sym not in bar_df.index:
                continue
            c_row = bar_df.loc[sym]
            c_high, c_low, c_close = float(c_row["high"]), float(c_row["low"]), float(c_row["close"])
            bars_held = t_idx - pos["entry_bar"]

            stopped_out = (c_low <= pos["sl_px"]) if pos["side"] == "LONG" else (c_high >= pos["sl_px"])
            if stopped_out:
                rem_ntl = (pos["notional_a"] if not pos["tranche_a_closed"] else 0.0) + pos["notional_b"]
                exit_px = pos["sl_px"]
                ret_m = (exit_px - pos["entry_price"]) / pos["entry_price"] if pos["side"] == "LONG" else (pos["entry_price"] - exit_px) / pos["entry_price"]
                pnl = (rem_ntl * ret_m) - (rem_ntl * friction_rate)
                equity += pnl
                trades.append({"pnl": pnl})
                closed_syms.append(sym)
                cooldown[sym] = t_idx
                continue

            if not pos["tranche_a_closed"]:
                hit_tp1 = (c_high >= pos["tp1_px"]) if pos["side"] == "LONG" else (c_low <= pos["tp1_px"])
                if hit_tp1:
                    pnl_a = (pos["notional_a"] * ((pos["tp1_px"] - pos["entry_price"] if pos["side"] == "LONG" else pos["entry_price"] - pos["tp1_px"]) / pos["entry_price"])) - (pos["notional_a"] * friction_rate)
                    equity += pnl_a
                    pos["tranche_a_closed"] = True
                    pos["sl_px"] = pos["entry_price"] + (0.5 * pos["atr"]) if pos["side"] == "LONG" else pos["entry_price"] - (0.5 * pos["atr"])
                    pos["runner_best"] = pos["tp1_px"]

            if pos["tranche_a_closed"] and pos["notional_b"] > 0:
                if pos["side"] == "LONG" and c_high > pos["runner_best"]:
                    pos["runner_best"] = c_high
                    pos["sl_px"] = max(pos["sl_px"], pos["runner_best"] - (2.5 * pos["atr"]))
                elif pos["side"] == "SHORT" and c_low < pos["runner_best"]:
                    pos["runner_best"] = c_low
                    pos["sl_px"] = min(pos["sl_px"], pos["runner_best"] + (2.5 * pos["atr"]))

            if bars_held >= 18:
                rem_ntl = (pos["notional_a"] if not pos["tranche_a_closed"] else 0.0) + pos["notional_b"]
                ret_m = (c_close - pos["entry_price"]) / pos["entry_price"] if pos["side"] == "LONG" else (pos["entry_price"] - c_close) / pos["entry_price"]
                pnl = (rem_ntl * ret_m) - (rem_ntl * friction_rate)
                equity += pnl
                trades.append({"pnl": pnl})
                closed_syms.append(sym)
                cooldown[sym] = t_idx

        for s in closed_syms:
            del active_positions[s]

        # Sizing Policies
        open_slots = 2 - len(active_positions)
        if open_slots > 0 and p_bear >= 0.40:
            el = [s for s in bar_df.index if s not in active_positions and (t_idx - cooldown.get(s, -99)) >= 3]
            cands = bar_df.loc[el]
            cands = cands[(cands["p_model_short"] >= 0.245) & (cands["mom_24h"] < 0.0)].sort_values(by="p_model_short", ascending=False)
            
            for sym, row in cands.iterrows():
                if open_slots <= 0:
                    break
                q = float(row["p_model_short"])
                
                # Apply Sizing Rule
                if sizing_mode == "flat":
                    slot_lev = 2.5
                elif sizing_mode == "naive_linear":
                    slot_lev = float(np.clip(2.5 + (max(0.0, q - 0.28) / 0.15 * 0.5), 2.5, 3.0))
                elif sizing_mode == "calibrated":
                    if 0.270 <= q < 0.300:
                        continue  # Prune negative EV zone
                    elif q < 0.270:
                        slot_lev = 2.0
                    elif q < 0.340:
                        slot_lev = 2.5
                    else:
                        slot_lev = 3.5

                px, atr = float(row["close"]), float(row["atr"])
                ntl = equity * slot_lev
                active_positions[sym] = {
                    "side": "SHORT", "entry_price": px, "atr": atr, "entry_bar": t_idx,
                    "notional_a": ntl * 0.70, "notional_b": ntl * 0.30,
                    "tp1_px": px - (1.8 * atr), "sl_px": px + (0.85 * atr),
                    "tranche_a_closed": False, "runner_best": px
                }
                open_slots -= 1

        equity_curve.append(equity)

    eq_s = pd.Series(equity_curve)
    mdd = abs(((eq_s - eq_s.cummax()) / eq_s.cummax()).min()) * 100
    ret_pct = ((equity - 500.0) / 500.0) * 100
    t_df = pd.DataFrame(trades)
    pf = (t_df[t_df["pnl"] > 0]["pnl"].sum() / abs(t_df[t_df["pnl"] < 0]["pnl"].sum())) if (len(t_df) > 0 and len(t_df[t_df["pnl"] < 0]) > 0) else np.nan

    return {
        "mode": sizing_mode,
        "ending_eq": equity,
        "ret_pct": ret_pct,
        "mdd": mdd,
        "calmar": ret_pct / (mdd + 1e-8),
        "trades": len(t_df)
    }

modes = ["flat", "naive_linear", "calibrated"]
print("="*80)
print("             OUT-OF-SAMPLE (OOS) SIZING PERFORMANCE")
print("="*80)
oos_res = [run_sizing_sim(oos_ts, m) for m in modes]
print(pd.DataFrame(oos_res)[["mode", "ending_eq", "ret_pct", "mdd", "calmar", "trades"]].to_string(index=False))

print("\n" + "="*80)
print("             FULL DATASET (539 BARS) SIZING PERFORMANCE")
print("="*80)
full_res = [run_sizing_sim(all_ts, m) for m in modes]
print(pd.DataFrame(full_res)[["mode", "ending_eq", "ret_pct", "mdd", "calmar", "trades"]].to_string(index=False))
