import numpy as np
import polars as pl
from pathlib import Path
from sklearn.linear_model import Ridge

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

df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h"),
    (pl.col("close").shift(-4).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("fwd_ret_4h")
])

btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_24h").alias("btc_ret_24h"),
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

df = df.with_columns([
    ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("f_res_4h"),
    ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("f_res_12h"),
    ((pl.col("ret_24h") - pl.col("beta_btc") * pl.col("btc_ret_24h")) / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("f_res_24h"),
    ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("f_res_72h")
])

FEATURE_COLS = ["f_res_4h", "f_res_12h", "f_res_24h", "f_res_72h"]

# Static Alpha Baseline definition
df = df.with_columns([
    (-0.35 * pl.col("f_res_4h") - 0.25 * pl.col("f_res_12h") + 0.40 * pl.col("f_res_72h")).alias("static_raw_alpha")
])
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("static_raw_alpha").ewm_mean(span=6).over("symbol").alias("static_smoothed_alpha")
])

valid_counts = df.filter(pl.col("dollar_volume_1h") > 25_000).group_by("group_id").len()
active_grps = sorted(valid_counts.filter(pl.col("len") >= 35)["group_id"].to_list())
split_idx = int(len(active_grps) * 0.70)
oos_grps = active_grps[split_idx:]

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

def eval_oos(is_adaptive=True, lookback=600, l2=67.95, k_entry=12, k_exit=32, rebal_clock=6):
    nav = 10_000.0
    turnover = 0.0
    prev_w = {}
    active_longs = set()
    active_shorts = set()
    returns = []
    cached_model = None
    last_train_grp = -1

    for idx, grp in enumerate(oos_grps[:-1]):
        cur_panel = df.filter(pl.col("group_id") == grp)
        valid_panel = cur_panel.filter(
            (pl.col("dollar_volume_1h") > 25_000) &
            pl.col("vol_yang_zhang").is_not_null()
        )
        if valid_panel.height < 35:
            continue

        returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

        if not is_adaptive:
            # Static Mode 2
            alpha_series = valid_panel["static_smoothed_alpha"].to_numpy()
            symbols = valid_panel["symbol"].to_list()
            alpha_dict = dict(zip(symbols, alpha_series))
        else:
            if cached_model is None or (grp - last_train_grp) >= 24:
                train_data = df.filter(
                    (pl.col("group_id") < grp) &
                    (pl.col("group_id") >= grp - lookback) &
                    (pl.col("dollar_volume_1h") > 25_000)
                ).drop_nulls(subset=FEATURE_COLS + ["fwd_ret_4h"])

                if train_data.height > 500:
                    X_tr = train_data.select(FEATURE_COLS).to_numpy()
                    y_tr = train_data["fwd_ret_4h"].to_numpy()
                    ridge = Ridge(alpha=l2, fit_intercept=False)
                    ridge.fit(X_tr, y_tr)
                    cached_model = ridge
                    last_train_grp = grp

            if cached_model is not None:
                X_live = valid_panel.select(FEATURE_COLS).to_numpy()
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

        if (idx % rebal_clock == 0):
            for s in all_ranked[:k_entry]: active_longs.add(s)
            for s in all_ranked[-k_entry:]: active_shorts.add(s)

            active_longs = {s for s in active_longs if rank_map.get(s, 999) < k_exit}
            active_shorts = {s for s in active_shorts if rank_map.get(s, -1) >= (len(all_ranked) - k_exit)}
            active_longs -= active_shorts

            active_syms = active_longs.union(active_shorts)
            if len(active_syms) < 16:
                raw_target = prev_w
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
            raw_target = prev_w

        # Leland Deadband
        dispatched = {}
        all_syms = set(prev_w.keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev_s = prev_w.get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))

            if abs(w_t) < 1e-4 or abs(w_prev_s) < 1e-4 or (w_t * w_prev_s < 0):
                dispatched[s] = w_t
                continue

            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 1.5, 0.020, 0.055)
            delta = w_t - w_prev_s
            if abs(delta) > h_star:
                dispatched[s] = w_t - np.sign(delta) * h_star
            else:
                dispatched[s] = w_prev_s

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}

        to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
        turnover += to
        cost = to * FEE_RATE

        short_exp = sum(abs(w) for w in dispatched.values() if w < 0)
        fund_pnl = short_exp * BASE_FUNDING
        net_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched) - cost + fund_pnl

        nav *= (1.0 + net_pnl)
        returns.append(net_pnl)
        prev_w = dispatched

    r = np.array(returns)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    downside_r = r[r < 0]
    sortino = np.mean(r) / (np.std(downside_r) + 1e-6) * np.sqrt(BARS_PER_YEAR) if len(downside_r) > 0 else 0.0

    return {
        "multiple": nav / 10_000.0,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "mdd": mdd,
        "vol": vol,
        "turnover_ann": turnover * (BARS_PER_YEAR / len(r))
    }

res_optuna = eval_oos(is_adaptive=True, lookback=600, l2=67.95, k_entry=12, k_exit=32, rebal_clock=6)
res_static = eval_oos(is_adaptive=False, rebal_clock=4, k_exit=28)

print("\n" + "=" * 96)
print("             HEAD-TO-HEAD ON UNTOUCHED OUT-OF-SAMPLE (LAST 58.2 DAYS)")
print("=" * 96)
headers = ["Performance Metric", "Static Mode 2 (Baseline)", "Optuna Walk-Forward (Adaptive)"]
print(f"{headers[0]:<30} | {headers[1]:<28} | {headers[2]:<28}")
print("-" * 96)
print(f"{'Terminal Multiple (58.2d)':<30} | {res_static['multiple']:>26.2f}x | {res_optuna['multiple']:>26.2f}x")
print(f"{'Annualized CAGR':<30} | {res_static['cagr']*100:>25.1f}% | {res_optuna['cagr']*100:>25.1f}%")
print(f"{'Net Sharpe Ratio (After Fees)':<30} | {res_static['sharpe']:>28.2f} | {res_optuna['sharpe']:>28.2f}")
print(f"{'Sortino Ratio':<30} | {res_static['sortino']:>28.2f} | {res_optuna['sortino']:>28.2f}")
print(f"{'Max Drawdown':<30} | {res_static['mdd']*100:>27.1f}% | {res_optuna['mdd']*100:>27.1f}%")
print(f"{'Realized Annual Volatility':<30} | {res_static['vol']*100:>27.1f}% | {res_optuna['vol']*100:>27.1f}%")
print(f"{'Annualized Turnover Volume':<30} | {res_static['turnover_ann']:>25.0f}x | {res_optuna['turnover_ann']:>25.0f}x")
print("=" * 96)
