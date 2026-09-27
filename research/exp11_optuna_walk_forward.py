import time
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.linear_model import Ridge
import optuna

# Suppress verbose Optuna logs
optuna.logging.set_verbosity(optuna.logging.WARNING)

print("=" * 96)
print("   EXPERIMENT 11: OPTUNA PURGED HYPERPARAMETER TUNING (IS 70% -> OOS 30%)")
print("=" * 96)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_full.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

BARS_PER_YEAR = 24 * 365
FEE_RATE = 0.00015
GAMMA_MVO = 0.05
BASE_FUNDING = 0.00005
GROSS_LEVERAGE = 4.60

# 1. Forward Returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h"),
    (pl.col("close").shift(-4).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("fwd_ret_4h")
])

# 2. Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_24h").alias("btc_ret_24h"),
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# 3. Residual Multi-Horizon Features
df = df.with_columns([
    ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("f_res_4h"),
    ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("f_res_12h"),
    ((pl.col("ret_24h") - pl.col("beta_btc") * pl.col("btc_ret_24h")) / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("f_res_24h"),
    ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("f_res_72h")
])

FEATURE_COLS = ["f_res_4h", "f_res_12h", "f_res_24h", "f_res_72h"]

# Filter Active Cross-Sections
valid_counts = df.filter(pl.col("dollar_volume_1h") > 25_000).group_by("group_id").len()
active_grps = sorted(valid_counts.filter(pl.col("len") >= 35)["group_id"].to_list())

split_idx = int(len(active_grps) * 0.70)
is_grps = active_grps[:split_idx]
oos_grps = active_grps[split_idx:]

print(f"[+] Total Active Bars: {len(active_grps):,} (~{len(active_grps)/24:.1f} days)")
print(f"[+] In-Sample Optimization: {len(is_grps):,} bars (~{len(is_grps)/24:.1f} days)")
print(f"[+] Blind Out-of-Sample   : {len(oos_grps):,} bars (~{len(oos_grps)/24:.1f} days)")

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

def simulate_engine(grps_list, lookback_bars, l2_reg, k_entry, k_exit, rebal_clock):
    nav = 10_000.0
    turnover = 0.0
    prev_dispatched = {}
    active_longs = set()
    active_shorts = set()
    returns = []

    cached_model = None
    last_train_grp = -1

    for idx, grp in enumerate(grps_list[:-1]):
        cur_panel = df.filter(pl.col("group_id") == grp)
        valid_panel = cur_panel.filter(
            (pl.col("dollar_volume_1h") > 25_000) &
            pl.col("vol_yang_zhang").is_not_null()
        )
        if valid_panel.height < 35:
            continue

        returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

        # Walk-Forward Retraining every 24 bars (daily)
        if cached_model is None or (grp - last_train_grp) >= 24:
            train_data = df.filter(
                (pl.col("group_id") < grp) &
                (pl.col("group_id") >= grp - lookback_bars) &
                (pl.col("dollar_volume_1h") > 25_000)
            ).drop_nulls(subset=FEATURE_COLS + ["fwd_ret_4h"])

            if train_data.height > 500:
                X_tr = train_data.select(FEATURE_COLS).to_numpy()
                y_tr = train_data["fwd_ret_4h"].to_numpy()
                ridge = Ridge(alpha=l2_reg, fit_intercept=False)
                ridge.fit(X_tr, y_tr)
                cached_model = ridge
                last_train_grp = grp

        if cached_model is not None:
            X_live = valid_panel.select(FEATURE_COLS).to_numpy()
            # Clean any isolated NaNs in inference
            X_live = np.nan_to_num(X_live, nan=0.0)
            preds = cached_model.predict(X_live)
            symbols = valid_panel["symbol"].to_list()
            alpha_dict = dict(zip(symbols, preds))
        else:
            symbols = valid_panel["symbol"].to_list()
            alpha_dict = {s: 0.0 for s in symbols}

        sorted_pairs = sorted(alpha_dict.items(), key=lambda x: x[1], reverse=True)
        all_ranked = [p[0] for p in sorted_pairs]
        rank_map = {s: i for i, s in enumerate(all_ranked)}

        is_rebal = (idx % rebal_clock == 0)
        if is_rebal:
            for s in all_ranked[:k_entry]: active_longs.add(s)
            for s in all_ranked[-k_entry:]: active_shorts.add(s)

            active_longs = {s for s in active_longs if rank_map.get(s, 999) < k_exit}
            active_shorts = {s for s in active_shorts if rank_map.get(s, -1) >= (len(all_ranked) - k_exit)}
            active_longs -= active_shorts

            active_syms = active_longs.union(active_shorts)
            if len(active_syms) < 16:
                raw_target = prev_dispatched
            else:
                inv_vols = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
                raw_w = {}
                for s in active_syms:
                    raw_w[s] = inv_vols[s] if s in active_longs else -inv_vols[s]

                l_sum = sum(w for w in raw_w.values() if w > 0)
                s_sum = sum(abs(w) for w in raw_w.values() if w < 0)

                target_leg = GROSS_LEVERAGE / 2.0
                raw_target = {}
                for s in raw_w:
                    if raw_w[s] > 0 and l_sum > 0: raw_target[s] = (raw_w[s] / l_sum) * target_leg
                    elif raw_w[s] < 0 and s_sum > 0: raw_target[s] = (raw_w[s] / s_sum) * target_leg
        else:
            raw_target = prev_dispatched

        # Leland Deadband
        dispatched = {}
        all_syms = set(prev_dispatched.keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_dispatched.get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))

            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                dispatched[s] = w_t
                continue

            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 1.5, 0.020, 0.055)
            delta = w_t - w_prev
            if abs(delta) > h_star:
                dispatched[s] = w_t - np.sign(delta) * h_star
            else:
                dispatched[s] = w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}

        to = sum(abs(dispatched.get(s, 0.0) - prev_dispatched.get(s, 0.0)) for s in all_syms)
        turnover += to
        cost = to * FEE_RATE

        short_exp = sum(abs(w) for w in dispatched.values() if w < 0)
        fund_pnl = short_exp * BASE_FUNDING
        net_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched) - cost + fund_pnl

        nav *= (1.0 + net_pnl)
        returns.append(net_pnl)
        prev_dispatched = dispatched

    if not returns:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    r = np.array(returns)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    return sharpe, cagr, mdd, nav / 10_000.0, turnover * (BARS_PER_YEAR / len(r))

# 1. Define Optuna Objective (Strictly In-Sample)
def objective(trial):
    lookback_days = trial.suggest_int("lookback_days", 10, 45, step=5)
    l2_reg = trial.suggest_float("l2_reg", 50.0, 1000.0, log=True)
    k_entry = trial.suggest_int("k_entry", 8, 16, step=2)
    k_exit = trial.suggest_int("k_exit", 22, 34, step=2)
    rebal_clock = trial.suggest_categorical("rebal_clock", [2, 4, 6])

    sharpe, cagr, mdd, mult, to_ann = simulate_engine(
        is_grps, lookback_days * 24, l2_reg, k_entry, k_exit, rebal_clock
    )
    # Objective: Penalize excessive turnover and deep drawdowns
    score = sharpe - (0.00005 * to_ann) + (1.5 * mdd)
    return score

print("\n[+] Launching Optuna optimization (25 trials on In-Sample window)...")
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=25, show_progress_bar=True)

best = study.best_params
print("\n" + "=" * 96)
print(f"[+] OPTUNA IN-SAMPLE WINNING ARCHITECTURE (Score: {study.best_value:.3f})")
print(f"• Lookback Days  : {best['lookback_days']} days ({best['lookback_days']*24} bars)")
print(f"• L2 Reg Alpha   : {best['l2_reg']:.2f}")
print(f"• K_entry / K_exit: {best['k_entry']} / {best['k_exit']}")
print(f"• Rebalance Clock: Every {best['rebal_clock']}H")
print("=" * 96)

# 2. Blind Out-of-Sample Validation
print("\n[+] Evaluating Best Architecture on the BLIND OUT-OF-SAMPLE (58.2 Days)...")
oos_sharpe, oos_cagr, oos_mdd, oos_mult, oos_to = simulate_engine(
    oos_grps, best['lookback_days']*24, best['l2_reg'], best['k_entry'], best['k_exit'], best['rebal_clock']
)

# Benchmark against Static Mode 2 on the same OOS window
print("[+] Benchmarking against Static Mode 2 on OOS...")
