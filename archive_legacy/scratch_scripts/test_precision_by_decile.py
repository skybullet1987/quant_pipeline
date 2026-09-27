import pandas as pd
import numpy as np
from optimizer_cache import load_and_cache_dataset

train_bars, train_dict, oos_bars, oos_dict = load_and_cache_dataset(270, 90)
all_bars = train_bars + oos_bars
all_dict = train_dict + oos_dict

TP_MULT = 2.6
SL_MULT = 1.4
HOLD_BARS = 8
FEE_BPS = 12.0

records = []

print("--> Simulating isolated forward barrier hits for every prediction...")
for b_idx in range(len(all_bars) - HOLD_BARS):
    b_dict = all_dict[b_idx]
    
    for sym, r in b_dict.items():
        px, atr = r["close"], r["atr"]
        pl, ps = r["p_long"], r["p_short"]
        if px <= 0 or atr <= 0: continue

        # 1. Forward simulation for Long
        tp_px_l = px + (TP_MULT * atr)
        sl_px_l = px - (SL_MULT * atr)
        hit_tp_l, hit_sl_l, exit_px_l = False, False, px

        for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
            f_r = all_dict[f_idx].get(sym)
            if not f_r: continue
            if f_r["low"] <= sl_px_l: hit_sl_l, exit_px_l = True, sl_px_l; break
            elif f_r["high"] >= tp_px_l: hit_tp_l, exit_px_l = True, tp_px_l; break
            exit_px_l = f_r["close"]

        ret_l = ((exit_px_l - px) / px) - (FEE_BPS / 10000.0)

        # 2. Forward simulation for Short
        tp_px_s = px - (TP_MULT * atr)
        sl_px_s = px + (SL_MULT * atr)
        hit_tp_s, hit_sl_s, exit_px_s = False, False, px

        for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
            f_r = all_dict[f_idx].get(sym)
            if not f_r: continue
            if f_r["high"] >= sl_px_s: hit_sl_s, exit_px_s = True, sl_px_s; break
            elif f_r["low"] <= tp_px_s: hit_tp_s, exit_px_s = True, tp_px_s; break
            exit_px_s = f_r["close"]

        ret_s = ((px - exit_px_s) / px) - (FEE_BPS / 10000.0)

        records.append({
            "ticker": sym, "regime": r["regime"],
            "p_long": pl, "win_l": ret_l > 0, "ret_l": ret_l,
            "p_short": ps, "win_s": ret_s > 0, "ret_s": ret_s
        })

df = pd.DataFrame(records)

bins = [0.0, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 1.00]
df["p_long_bin"] = pd.cut(df["p_long"], bins=bins)
df["p_short_bin"] = pd.cut(df["p_short"], bins=bins)

print("\n" + "=" * 85)
print("             LONG EXPERT: REALIZED WIN RATE & EXPECTANCY BY PROBABILITY BIN             ")
print("=" * 85)
long_summary = df.groupby("p_long_bin", observed=False).agg(
    signals=("ret_l", "count"),
    win_rate=("win_l", lambda x: f"{x.mean()*100:.1f}%"),
    avg_ret_bps=("ret_l", lambda x: f"{x.mean()*10000:>+6.1f} bps"),
    profit_factor=("ret_l", lambda x: round(x[x > 0].sum() / max(1e-4, abs(x[x <= 0].sum())), 2))
)
print(long_summary)

print("\n" + "=" * 85)
print("            SHORT EXPERT: REALIZED WIN RATE & EXPECTANCY BY PROBABILITY BIN             ")
print("=" * 85)
short_summary = df.groupby("p_short_bin", observed=False).agg(
    signals=("ret_s", "count"),
    win_rate=("win_s", lambda x: f"{x.mean()*100:.1f}%"),
    avg_ret_bps=("ret_s", lambda x: f"{x.mean()*10000:>+6.1f} bps"),
    profit_factor=("ret_s", lambda x: round(x[x > 0].sum() / max(1e-4, abs(x[x <= 0].sum())), 2))
)
print(short_summary)
print("=" * 85)
