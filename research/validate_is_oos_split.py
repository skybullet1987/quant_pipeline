import sys
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine, compute_hrp_from_cov

lake_path = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_4h.parquet"
df = pl.read_parquet(lake_path)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

engine = ProductionMultiScaleEngine()
_, _ = engine.compute_live_targets(lake_file=lake_path)

all_groups = sorted(df.select("group_id").unique().to_series().to_list())
eval_groups = [g for g in all_groups if g >= 168]

fee_rate = 0.00015
gamma_mvo = 0.05
TARGET_ANN_VOL = 0.22
BARS_PER_YEAR = 6 * 365
TARGET_BAR_VOL = TARGET_ANN_VOL / np.sqrt(BARS_PER_YEAR)

def zscore(arr):
    s = np.std(arr)
    return (arr - np.mean(arr)) / (s if s > 1e-6 else 1.0)

# Simulate full timeline recording bar-by-bar PnL and group IDs
bar_records = []
prev_w = {}

for idx in range(len(eval_groups) - 1):
    grp = eval_groups[idx]
    next_grp = eval_groups[idx + 1]

    cur_panel = df.filter(pl.col("group_id") == grp)
    next_panel = df.filter(pl.col("group_id") == next_grp)
    returns_map = dict(zip(next_panel["symbol"].to_list(), next_panel["ret_4h"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))
    cur_rows = {r["symbol"]: r for r in cur_panel.iter_rows(named=True)}
    symbols = list(cur_rows.keys())

    X_live = cur_panel.select(engine.m12.feature_names_).to_pandas()
    z12 = zscore(engine.m12.predict(X_live))
    z48 = zscore(engine.m48.predict(X_live))
    z168 = zscore(engine.m168.predict(X_live))

    # Corrected Alpha Ensemble
    alpha_vec = (-0.30 * z12) + (0.45 * z48) + (0.25 * z168)

    hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
    piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
    v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]
    if len(v_cols) < 20:
        continue

    shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
    a_dict = {s: val for s, val in zip(symbols, alpha_vec)}
    a_sub = np.array([a_dict[s] for s in v_cols])

    w_unit = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=1.0, top_k=10)
    port_var = float(w_unit.T @ shrunk_cov @ w_unit)
    port_vol = np.sqrt(max(port_var, 1e-8))
    lev_target = float(np.clip(TARGET_BAR_VOL / port_vol, 0.60, 2.50))
    w_scaled = w_unit * lev_target
    raw_target = {v_cols[i]: float(w_scaled[i]) for i in range(len(v_cols)) if abs(w_scaled[i]) > 0.005}

    # Leland Deadband
    dispatched = {}
    all_syms = set(prev_w.keys()).union(raw_target.keys())
    for s in all_syms:
        w_t = raw_target.get(s, 0.0)
        w_prev = prev_w.get(s, 0.0)
        sigma = max(0.015, vols_map.get(s, 0.025))

        if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
            dispatched[s] = w_t
            continue

        h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / gamma_mvo) ** (1.0 / 3.0), 0.010, 0.035)
        delta = w_t - w_prev
        if abs(delta) > h_star:
            dispatched[s] = w_t - np.sign(delta) * h_star
        else:
            dispatched[s] = w_prev
    dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.005}

    to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
    cost = to * fee_rate
    pnl = sum(dispatched.get(s, 0.0) * returns_map.get(s, 0.0) for s in dispatched) - cost
    bar_records.append({"group_id": grp, "pnl": pnl, "turnover": to})
    prev_w = dispatched

def summarize_slice(records, name):
    r = np.array([x["pnl"] for x in records])
    to = sum(x["turnover"] for x in records)
    cum = np.cumprod(1.0 + r)
    cagr = cum[-1] ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    win = np.mean(r > 0) * 100
    print(f"\n=== {name.upper()} ({len(r)} bars / {len(r)/6:.1f} days) ===")
    print(f"• Net CAGR             : {cagr * 100:+.2f}%")
    print(f"• Net Sharpe Ratio     : {sharpe:.2f}")
    print(f"• Calmar Ratio         : {cagr / abs(mdd):.2f}")
    print(f"• Max Drawdown         : {mdd * 100:.2f}%")
    print(f"• Realized Volatility  : {vol * 100:.2f}%")
    print(f"• Win Rate (% Bars)    : {win:.1f}%")
    print(f"• Mean Turnover / Bar  : {to / len(r):.2f}x NAV")

rec_is = [x for x in bar_records if x["group_id"] < 1315]
rec_oos = [x for x in bar_records if x["group_id"] >= 1315]
rec_recent = [x for x in bar_records if x["group_id"] >= (all_groups[-1] - 180)]

print("=" * 75)
print("       OUT-OF-SAMPLE SLICE VERIFICATION: SIGN-CORRECTED ENSEMBLE")
print("=" * 75)
summarize_slice(rec_is, "In-Sample Training Block (Groups 168 to 1314)")
summarize_slice(rec_oos, "Strict Out-of-Sample Holdout (Groups 1315 to 2221)")
summarize_slice(rec_recent, "Trailing 30-Day Window (Groups 2040 to 2221)")
print("=" * 75)
