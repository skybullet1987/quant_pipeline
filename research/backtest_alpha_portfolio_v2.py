import numpy as np
import polars as pl
from pathlib import Path
from catboost import CatBoostRegressor

print("=" * 65)
print("   OFFLINE PORTFOLIO LAB: TIMING-CORRECTED BENCHMARK (V2)")
print("=" * 65)

data_dir = Path.home() / "quant_pipeline" / "data" / "features"
files = list(data_dir.glob("*.parquet")) if data_dir.exists() else []
if not files:
    data_dir = Path.home() / "quant_pipeline" / "data" / "lake"
    files = list(data_dir.glob("*.parquet"))

df = pl.read_parquet(files).sort(["symbol", "timestamp_ms"])

# 1. Feature Engineering
df = df.with_columns([
    (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).alias("ret_4h")
])
mkt = df.group_by("timestamp_ms").agg(pl.col("ret_4h").median().alias("ret_mkt"))
df = df.join(mkt, on="timestamp_ms", how="left")

df = df.with_columns([
    (pl.col("ret_4h") - pl.col("ret_mkt")).alias("residual_ret"),
    ((pl.col("high").log() - pl.col("low").log()).pow(2) / (4.0 * np.log(2))).sqrt().alias("parkinson_vol"),
    (pl.col("volume") / (pl.col("volume").rolling_mean(window_size=18).over("symbol") + 1e-6)).alias("vol_ratio_72h")
])

df = df.with_columns([
    pl.col("residual_ret").rolling_sum(window_size=6).over("symbol").alias("idio_mom_24h"),
    pl.col("residual_ret").rolling_sum(window_size=18).over("symbol").alias("idio_mom_72h"),
    pl.col("residual_ret").rolling_sum(window_size=42).over("symbol").alias("idio_mom_168h"),
    (pl.col("vol_ratio_72h") * pl.col("residual_ret").sign()).alias("signed_vol_flow"),
    ((pl.col("close") - pl.col("close").rolling_mean(window_size=18).over("symbol")) / 
     (pl.col("close").rolling_std(window_size=18).over("symbol") + 1e-6)).alias("z_disparity_72h")
])

df = df.with_columns([
    (pl.col("idio_mom_24h") / (pl.col("parkinson_vol").rolling_mean(window_size=6).over("symbol") + 1e-4)).alias("vol_adj_mom_24h"),
    (pl.col("idio_mom_72h") / (pl.col("parkinson_vol").rolling_mean(window_size=18).over("symbol") + 1e-4)).alias("vol_adj_mom_72h"),
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).alias("raw_fwd_ret")
])

df = df.with_columns([
    (pl.col("raw_fwd_ret").rank().over("timestamp_ms") / 
     pl.col("raw_fwd_ret").count().over("timestamp_ms")).alias("target_rank_4h")
])

feature_cols = [
    "idio_mom_24h", "idio_mom_72h", "idio_mom_168h",
    "vol_adj_mom_24h", "vol_adj_mom_72h",
    "signed_vol_flow", "z_disparity_72h"
]

clean_df = df.select(["timestamp_ms", "symbol", "target_rank_4h", "raw_fwd_ret", "parkinson_vol"] + feature_cols).drop_nulls()

timestamps = sorted(clean_df["timestamp_ms"].unique().to_list())
split_idx = int(len(timestamps) * 0.70)
split_ts = timestamps[split_idx]

train_data = clean_df.filter(pl.col("timestamp_ms") < split_ts)
test_data = clean_df.filter(pl.col("timestamp_ms") >= split_ts)

# Train CatBoost
print("[+] Training regularized CatBoost...")
model = CatBoostRegressor(iterations=250, learning_rate=0.03, depth=5, l2_leaf_reg=10.0, rsm=0.70, subsample=0.80, random_seed=42, verbose=0)
model.fit(train_data.select(feature_cols).to_pandas(), train_data["target_rank_4h"].to_pandas())

test_data = test_data.with_columns(pl.Series("alpha_score", model.predict(test_data.select(feature_cols).to_pandas())))

# 2. Portfolio Simulation Setup
test_timestamps = sorted(test_data["timestamp_ms"].unique().to_list())
fee_rate = 0.00035  # 3.5 bps maker fee / slippage
GROSS_LEVERAGE = 1.64
K = 10  # Optimal breadth zone: 10 longs, 10 shorts per paper

static_nav = 10_000.0
leland_nav = 10_000.0
static_turnover_total = 0.0
leland_turnover_total = 0.0

prev_static_weights = {}
prev_leland_weights = {}

static_returns = []
leland_returns = []

for ts in test_timestamps:
    bar = test_data.filter(pl.col("timestamp_ms") == ts)
    if bar.height < (K * 2):
        continue

    # Softmax Temperature-Scaled Rank Weights (tau = 0.50)
    sorted_bar = bar.sort("alpha_score", descending=True)
    long_slice = sorted_bar.head(K)
    short_slice = sorted_bar.tail(K)

    long_scores = long_slice["alpha_score"].to_numpy()
    short_scores = short_slice["alpha_score"].to_numpy()

    # Softmax conversion
    tau = 0.50
    exp_long = np.exp((long_scores - np.mean(long_scores)) / tau)
    w_long = (exp_long / np.sum(exp_long)) * (GROSS_LEVERAGE / 2.0)

    exp_short = np.exp(-(short_scores - np.mean(short_scores)) / tau)
    w_short = -(exp_short / np.sum(exp_short)) * (GROSS_LEVERAGE / 2.0)

    target_weights = {}
    for sym, w in zip(long_slice["symbol"], w_long):
        target_weights[sym] = float(w)
    for sym, w in zip(short_slice["symbol"], w_short):
        target_weights[sym] = float(w)

    returns_map = dict(zip(bar["symbol"].to_list(), bar["raw_fwd_ret"].to_list()))
    vols_map = dict(zip(bar["symbol"].to_list(), bar["parkinson_vol"].to_list()))

    all_static_syms = set(prev_static_weights.keys()).union(target_weights.keys())

    # --- 1. Static Execution (Corrected Timing) ---
    turnover_static = sum(abs(target_weights.get(s, 0.0) - prev_static_weights.get(s, 0.0)) for s in all_static_syms)
    static_turnover_total += turnover_static
    cost_static = turnover_static * fee_rate

    # The dispatched weights earn returns over [ts, ts+1]
    gross_pnl_static = sum(target_weights.get(s, 0.0) * returns_map.get(s, 0.0) for s in target_weights)
    net_pnl_static = gross_pnl_static - cost_static
    static_nav *= (1.0 + net_pnl_static)
    static_returns.append(net_pnl_static)
    prev_static_weights = target_weights

    # --- 2. Leland Deadband Execution (Turnover-Buffered) ---
    all_leland_syms = set(prev_leland_weights.keys()).union(target_weights.keys())
    leland_dispatched = {}

    for s in all_leland_syms:
        w_t = target_weights.get(s, 0.0)
        w_prev = prev_leland_weights.get(s, 0.0)
        sigma = max(0.01, vols_map.get(s, 0.02))

        # Leland cubic root deadband half-width: h* = ((4/3 * c * sigma^2) / gamma)^(1/3)
        # Calibrated for fractional portfolio weights: threshold in range [0.015, 0.040]
        h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / 0.05) ** (1.0 / 3.0), 0.015, 0.040)

        delta = w_t - w_prev
        if abs(delta) > h_star:
            # Partial adjustment to outer band
            leland_dispatched[s] = w_t - np.sign(delta) * h_star
        else:
            leland_dispatched[s] = w_prev

    # Clean zero dust
    leland_dispatched = {s: w for s, w in leland_dispatched.items() if abs(w) > 1e-4}

    turnover_leland = sum(abs(leland_dispatched.get(s, 0.0) - prev_leland_weights.get(s, 0.0)) for s in all_leland_syms)
    leland_turnover_total += turnover_leland
    cost_leland = turnover_leland * fee_rate

    # Dispatched weights earn returns over [ts, ts+1]
    gross_pnl_leland = sum(leland_dispatched.get(s, 0.0) * returns_map.get(s, 0.0) for s in leland_dispatched)
    net_pnl_leland = gross_pnl_leland - cost_leland
    leland_nav *= (1.0 + net_pnl_leland)
    leland_returns.append(net_pnl_leland)
    prev_leland_weights = leland_dispatched

# Performance Summary
bars_per_year = 6 * 365
ret_s = np.array(static_returns)
ret_l = np.array(leland_returns)

cagr_static = (static_nav / 10_000.0) ** (bars_per_year / len(ret_s)) - 1.0
cagr_leland = (leland_nav / 10_000.0) ** (bars_per_year / len(ret_l)) - 1.0

sharpe_static = np.mean(ret_s) / (np.std(ret_s) + 1e-6) * np.sqrt(bars_per_year)
sharpe_leland = np.mean(ret_l) / (np.std(ret_l) + 1e-6) * np.sqrt(bars_per_year)

def calc_max_dd(rets):
    cum = np.cumprod(1.0 + rets)
    peak = np.maximum.accumulate(cum)
    return np.min((cum - peak) / peak)

print("\n" + "=" * 65)
print("       OUT-OF-SAMPLE BENCHMARK V2 RESULTS (TIMING CORRECTED)")
print("=" * 65)
print(f"• Baseline Static CAGR        : {cagr_static * 100:+.2f}%")
print(f"• Leland Buffered CAGR        : {cagr_leland * 100:+.2f}%")
print(f"• Baseline Sharpe Ratio       : {sharpe_static:.2f}")
print(f"• Leland Buffered Sharpe      : {sharpe_leland:.2f}")
print(f"• Baseline Max Drawdown       : {calc_max_dd(ret_s) * 100:.2f}%")
print(f"• Leland Max Drawdown         : {calc_max_dd(ret_l) * 100:.2f}%")
print(f"• Total Static Turnover       : {static_turnover_total:,.1f}x NAV")
print(f"• Total Leland Turnover       : {leland_turnover_total:,.1f}x NAV")
turnover_reduc = (1.0 - leland_turnover_total / static_turnover_total) * 100
print(f"• Turnover Reduction Achieved : {turnover_reduc:.1f}%  (Target: >= 35%)")
print("=" * 65)
