import os, sys, warnings
PROJECT_ROOT = os.path.abspath(os.getenv("QUANT_PROJECT_ROOT", "/home/skybullet1987/quant_pipeline"))
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
df = pd.read_parquet(f"{PROJECT_ROOT}/data/oos_scored_mart.parquet")
df["timestamp"] = pd.to_datetime(df["timestamp"])

all_ts = sorted(df["timestamp"].unique())
oos_ts = all_ts[int(len(all_ts) * 0.65):]
oos_df = df[df["timestamp"].isin(oos_ts)].copy()

# Short Breakdowns (P_bear >= 0.40, mom_24h < 0)
short_cands = oos_df[(oos_df["p_bear"] >= 0.40) & (oos_df["mom_24h"] < 0.0) & (oos_df["p_model_short"] >= 0.245)].copy()

bins = [0.245, 0.270, 0.300, 0.340, 1.0]
labels = ["0.245-0.270 (Base)", "0.270-0.300 (Moderate)", "0.300-0.340 (High)", ">=0.340 (Max)"]
short_cands["q_bucket"] = pd.cut(short_cands["p_model_short"], bins=bins, labels=labels, right=False)

# Track 70/30 Realized Returns (TP1=1.8x ATR @ 70%, Trail=2.5x ATR @ 30%, SL=0.85x ATR)
df_indexed = df.set_index(["timestamp", "asset"]).sort_index()
results = []

for idx, row in short_cands.iterrows():
    ts = row["timestamp"]
    sym = row["asset"]
    px0 = row["close"]
    atr = row["atr"]
    t_idx = all_ts.index(ts)
    
    tp1_px = px0 - (1.8 * atr)
    sl_px = px0 + (0.85 * atr)
    
    fwd_bars = all_ts[t_idx + 1 : min(t_idx + 19, len(all_ts))]
    tranche_a_closed = False
    hit_sl = False
    runner_best = px0
    final_pnl_pct = 0.0
    
    for f_ts in fwd_bars:
        if (f_ts, sym) in df_indexed.index:
            r = df_indexed.loc[(f_ts, sym)]
            high, low, close = float(r["high"]), float(r["low"]), float(r["close"])
            
            if high >= sl_px:
                hit_sl = True
                break
                
            if not tranche_a_closed and low <= tp1_px:
                tranche_a_closed = True
                sl_px = px0 - (0.5 * atr)
                runner_best = tp1_px
                
            if tranche_a_closed:
                if low < runner_best:
                    runner_best = low
                    sl_px = min(sl_px, runner_best + (2.5 * atr))
    
    if hit_sl and not tranche_a_closed:
        final_pnl_pct = -(0.85 * (atr / px0))
    elif tranche_a_closed and hit_sl:
        pnl_a = 0.70 * (1.8 * (atr / px0))
        pnl_b = 0.30 * ((px0 - sl_px) / px0)
        final_pnl_pct = pnl_a + pnl_b
    elif tranche_a_closed:
        pnl_a = 0.70 * (1.8 * (atr / px0))
        pnl_b = 0.30 * ((px0 - close) / px0)
        final_pnl_pct = pnl_a + pnl_b
    else:
        final_pnl_pct = (px0 - close) / px0

    results.append({
        "q_bucket": row["q_bucket"],
        "pnl_pct": final_pnl_pct,
        "is_win": final_pnl_pct > 0
    })

res_df = pd.DataFrame(results)

summary = res_df.groupby("q_bucket", observed=False).agg(
    n_trades=("pnl_pct", "count"),
    win_rate=("is_win", lambda x: f"{x.mean()*100:.1f}%"),
    avg_win=("pnl_pct", lambda x: f"{x[x > 0].mean()*100:.2f}%" if len(x[x > 0]) > 0 else "0%"),
    avg_loss=("pnl_pct", lambda x: f"{abs(x[x < 0].mean())*100:.2f}%" if len(x[x < 0]) > 0 else "0%"),
    expectancy_per_1x=("pnl_pct", lambda x: f"{x.mean()*100:.3f}%")
).reset_index()

print("="*85)
print("       EMPIRICAL EXPECTANCY & REALIZED PAYOFF BY PROBABILITY BUCKET")
print("="*85)
print(summary.to_string(index=False))
