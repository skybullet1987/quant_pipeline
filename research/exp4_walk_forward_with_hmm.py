import sys
import json
import time
from pathlib import Path
import numpy as np
import polars as pl
from catboost import CatBoost, Pool
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import compute_hrp_from_cov
from src.backtest.backtest_models import OnlineMicrostructureHMM

print("=" * 82)
print("   WALK-FORWARD EXPERIMENT 4: ROLLING TREES + MICROSTRUCTURE HMM")
print("=" * 82)

models_dir = Path.home() / "quant_pipeline" / "data" / "models"
meta_path = models_dir / "multiscale_meta.json"
FEATURE_COLS = json.load(open(meta_path))["feature_cols"]

lake_path = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_4h.parquet"
df = pl.read_parquet(lake_path)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-3).over("symbol") / pl.col("close")).log().alias("fwd_ret_12h"),
    (pl.col("close").shift(-12).over("symbol") / pl.col("close")).log().alias("fwd_ret_48h"),
    (pl.col("close").shift(-42).over("symbol") / pl.col("close")).log().alias("fwd_ret_168h"),
])

btc_df = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("fwd_ret_12h").alias("btc_fwd_12h"),
    pl.col("fwd_ret_48h").alias("btc_fwd_48h"),
    pl.col("fwd_ret_168h").alias("btc_fwd_168h"),
    pl.col("vol_yang_zhang").alias("btc_vol"),
]).unique(subset=["group_id"])

df = df.join(btc_df, on="group_id", how="left")

df = df.with_columns([
    ((pl.col("fwd_ret_12h") - (pl.col("beta_btc") * pl.col("btc_fwd_12h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_12h"),
    ((pl.col("fwd_ret_48h") - (pl.col("beta_btc") * pl.col("btc_fwd_48h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_48h"),
    ((pl.col("fwd_ret_168h") - (pl.col("beta_btc") * pl.col("btc_fwd_168h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_168h")
]).sort(["group_id", "symbol"])

all_groups = sorted(df["group_id"].unique().to_list())
TRAIN_WINDOW, STEP_SIZE, EMBARGO = 900, 180, 42
fee_rate, gamma_mvo = 0.00015, 0.05
TARGET_ANN_VOL = 0.22
BARS_PER_YEAR = 6 * 365
TARGET_BAR_VOL = TARGET_ANN_VOL / np.sqrt(BARS_PER_YEAR)

start_eval_grp = TRAIN_WINDOW + EMBARGO
eval_splits = []
curr = start_eval_grp
while curr + STEP_SIZE <= all_groups[-1]:
    eval_splits.append((curr, curr + STEP_SIZE))
    curr += STEP_SIZE
if curr < all_groups[-1]:
    eval_splits.append((curr, all_groups[-1]))

def zscore(arr):
    s = np.std(arr)
    return (arr - np.mean(arr)) / (s if s > 1e-6 else 1.0)

nav = 10_000.0
total_turnover = 0.0
prev_w = {}
all_returns = []

hmm = OnlineMicrostructureHMM()

t0 = time.time()
for fold_idx, (test_start, test_end) in enumerate(eval_splits):
    train_end = test_start - EMBARGO
    train_start = max(0, train_end - TRAIN_WINDOW)

    train_data = df.filter((pl.col("group_id") >= train_start) & (pl.col("group_id") < train_end)).drop_nulls(
        subset=FEATURE_COLS + ["target_12h", "target_48h", "target_168h"]
    ).sort(["group_id", "symbol"])

    X_train = train_data.select(FEATURE_COLS).to_pandas()
    grp_train = train_data.select("group_id").to_series().to_numpy()

    m12 = CatBoost({"iterations": 150, "depth": 4, "learning_rate": 0.05, "loss_function": "YetiRank", "verbose": False, "thread_count": -1, "random_seed": 42}).fit(
        Pool(X_train, train_data["target_12h"].to_numpy(), group_id=grp_train)
    )
    m48 = CatBoost({"iterations": 150, "depth": 4, "learning_rate": 0.05, "loss_function": "YetiRank", "verbose": False, "thread_count": -1, "random_seed": 42}).fit(
        Pool(X_train, train_data["target_48h"].to_numpy(), group_id=grp_train)
    )
    m168 = CatBoost({"iterations": 150, "depth": 4, "learning_rate": 0.05, "loss_function": "YetiRank", "verbose": False, "thread_count": -1, "random_seed": 42}).fit(
        Pool(X_train, train_data["target_168h"].to_numpy(), group_id=grp_train)
    )

    fold_rets = []
    for grp in range(test_start, test_end):
        cur_panel = df.filter(pl.col("group_id") == grp)
        next_panel = df.filter(pl.col("group_id") == grp + 1)
        if cur_panel.height < 15 or next_panel.height < 15:
            continue

        returns_map = dict(zip(next_panel["symbol"].to_list(), next_panel["ret_4h"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))
        symbols = cur_panel["symbol"].to_list()

        # Step HMM Filter
        b_vol = float(cur_panel.filter(pl.col("symbol") == "BTC")["vol_yang_zhang"][0]) if "BTC" in symbols else 0.025
        mean_zvol = float(cur_panel.select(pl.mean("volume_zscore_72h")).to_series()[0])
        obs = np.array([b_vol, mean_zvol, 0.002])
        _, hmm_lev, dom_state = hmm.filter_step(obs)

        X_live = cur_panel.select(FEATURE_COLS).to_pandas()
        z12 = zscore(m12.predict(X_live))
        z48 = zscore(m48.predict(X_live))
        z168 = zscore(m168.predict(X_live))

        alpha_vec = (0.25 * z12) + (0.45 * z48) + (0.30 * z168)
        alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

        hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
        piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
        v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]
        if len(v_cols) < 20:
            continue

        shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
        a_sub = np.array([alpha_dict[s] for s in v_cols])

        w_unit = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=1.0, top_k=10)
        port_var = float(w_unit.T @ shrunk_cov @ w_unit)
        port_vol = np.sqrt(max(port_var, 1e-8))

        # Modulate leverage via HMM regime multiplier
        lev_target = float(np.clip((TARGET_BAR_VOL / port_vol) * (hmm_lev / 1.0), 0.40, 2.50))
        w_scaled = w_unit * lev_target

        # Asymmetric Regime 0 hedging
        if dom_state == 0:
            w_scaled[w_scaled < 0] *= 1.30

        raw_target = {v_cols[i]: float(w_scaled[i]) for i in range(len(v_cols)) if abs(w_scaled[i]) > 0.005}

        # Leland Deadband
        dispatched = {}
        all_syms = set(prev_w.keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_w.get(s, 0.0)
            sigma_raw = vols_map.get(s, 0.025)
            sigma = 0.025 if (sigma_raw is None or np.isnan(sigma_raw)) else max(0.015, float(sigma_raw))

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
        total_turnover += to
        cost = to * fee_rate
        pnl = sum(dispatched.get(s, 0.0) * returns_map.get(s, 0.0) for s in dispatched) - cost
        nav *= (1.0 + pnl)
        all_returns.append(pnl)
        fold_rets.append(pnl)
        prev_w = dispatched

    f_rets = np.array(fold_rets)
    f_cum = (np.prod(1.0 + f_rets) - 1.0) * 100
    f_sharpe = np.mean(f_rets) / (np.std(f_rets) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    f_win = np.mean(f_rets > 0) * 100
    print(f"  • Fold {fold_idx + 1}/{len(eval_splits)} (Bars {test_start:>4}-{test_end:<4}) -> Net Return: {f_cum:>+6.2f}% | Sharpe: {f_sharpe:>5.2f} | Win Rate: {f_win:>5.1f}%")

r = np.array(all_returns)
cum = np.cumprod(1.0 + r)
cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))

print("\n" + "=" * 82)
print("     OOS WALK-FORWARD SUMMARY: TREES + MICROSTRUCTURE HMM")
print("=" * 82)
print(f"• Total Evaluated Bars (Pure OOS) : {len(r)} ({len(r)/6:.1f} days)")
print(f"• Net CAGR                        : {cagr * 100:+.2f}%")
print(f"• Net Sharpe Ratio                : {sharpe:.2f}")
print(f"• Calmar Ratio                    : {cagr / abs(mdd):.2f}")
print(f"• Realized Annual Volatility      : {vol * 100:.2f}%")
print(f"• Max Drawdown                    : {mdd * 100:.2f}%")
print(f"• Bar Win Rate                    : {np.mean(r > 0) * 100:.1f}%")
print(f"• Mean Turnover per 4H Bar        : {total_turnover / len(r):.2f}x NAV")
print(f"• Elapsed Execution Time          : {time.time() - t0:.1f}s")
print("=" * 82)
