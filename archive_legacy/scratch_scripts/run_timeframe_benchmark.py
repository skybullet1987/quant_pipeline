import os, sys, gc, warnings
import pandas as pd
import numpy as np
from scipy.stats import multivariate_normal
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier
from google.cloud import bigquery
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
LONG_TP, LONG_SL, LONG_MAE = 2.2, 1.1, 0.65
SHORT_TP, SHORT_SL, SHORT_MAE = 1.4, 0.9, 0.55
FEE_BPS = 0.0005  # 5 bps per side

client = bigquery.Client(project=PROJECT_ID)

def evaluate_timeframe(tf_str, seconds, lag_mom, max_hold_bars):
    print(f"\n--> [1/4] Querying & Resampling {tf_str} directly in BigQuery...")
    query = f"""
        WITH raw_buckets AS (
            SELECT
                TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(timestamp), {seconds}) * {seconds}) AS timestamp,
                timestamp AS raw_ts,
                ticker AS asset,
                CAST(open AS FLOAT64) AS open,
                CAST(high AS FLOAT64) AS high,
                CAST(low AS FLOAT64) AS low,
                CAST(close AS FLOAT64) AS close,
                CAST(volume AS FLOAT64) AS volume
            FROM `{PROJECT_ID}.market_data.stg_ohlcv`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        ),
        resampled AS (
            SELECT
                timestamp,
                asset,
                ARRAY_AGG(open ORDER BY raw_ts ASC LIMIT 1)[OFFSET(0)] AS open,
                MAX(high) AS high,
                MIN(low) AS low,
                ARRAY_AGG(close ORDER BY raw_ts DESC LIMIT 1)[OFFSET(0)] AS close,
                SUM(volume) AS volume
            FROM raw_buckets
            GROUP BY 1, 2
        )
        SELECT * FROM resampled ORDER BY timestamp ASC, asset ASC
    """
    df_res = client.query(query).to_dataframe()
    df_res["timestamp"] = pd.to_datetime(df_res["timestamp"])
    print(f"--> [2/4] Loaded {len(df_res):,} {tf_str} bars. Computing features & Causal HMM...")

    # Indicator Features
    df_res["atr"] = df_res.groupby("asset").apply(
        lambda g: (np.maximum(g["high"] - g["low"], np.maximum((g["high"] - g["close"].shift()).abs(), (g["low"] - g["close"].shift()).abs()))).rolling(20, min_periods=5).mean(),
        include_groups=False
    ).reset_index(level=0, drop=True).fillna(df_res["close"] * 0.02)
    df_res["atr_pct"] = df_res["atr"] / (df_res["close"] + 1e-8)

    sma_20 = df_res.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).mean())
    std_20 = df_res.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).std().fillna(0.0))
    bbw = (4.0 * std_20) / (sma_20 + 1e-8)
    roll_min = df_res.groupby("asset")[bbw.name if hasattr(bbw, 'name') else 0].transform(lambda x: x.rolling(40, min_periods=10).min())
    roll_max = df_res.groupby("asset")[bbw.name if hasattr(bbw, 'name') else 0].transform(lambda x: x.rolling(40, min_periods=10).max())

    df_res["dist_ema20_atr"] = (df_res["close"] - sma_20) / (df_res["atr"] + 1e-8)
    df_res["bbw_pct_40"] = ((bbw - roll_min) / (roll_max - roll_min + 1e-8)).fillna(0.5).clip(0.0, 1.0)
    df_res["mom_24h"] = df_res.groupby("asset")["close"].transform(lambda x: x.pct_change(lag_mom).fillna(0.0))

    # Causal Macro HMM
    df_res["ret"] = df_res.groupby("asset")["close"].pct_change().fillna(0.0)
    df_res["ema_20"] = df_res.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
    mbi_ts = df_res.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
    csd_ts = df_res.groupby("timestamp")["ret"].std().fillna(0.01).rename("csd")
    macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

    all_bars = sorted(df_res["timestamp"].unique())
    cutoff_date = all_bars[-1] - pd.Timedelta(days=30)
    macro_tr = macro_df[macro_df.index < cutoff_date][["mbi", "csd"]]

    hmm_scaler = RobustScaler().fit(macro_tr)
    hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100).fit(hmm_scaler.transform(macro_tr))
    canonical_order = np.argsort(-hmm.means_[:, 0])

    X_all = hmm_scaler.transform(macro_df[["mbi", "csd"]])
    T_len = len(X_all)
    alpha = np.zeros((T_len, 3))
    B = np.zeros((T_len, 3))
    for j in range(3):
        B[:, j] = multivariate_normal.pdf(X_all, mean=hmm.means_[j], cov=hmm.covars_[j] + np.eye(2) * 1e-4)

    alpha[0] = hmm.startprob_ * B[0]
    alpha[0] /= np.sum(alpha[0]) + 1e-8
    for t in range(1, T_len):
        alpha[t] = np.dot(alpha[t-1], hmm.transmat_) * B[t]
        alpha[t] /= np.sum(alpha[t]) + 1e-8

    causal_posteriors = alpha[:, canonical_order]
    macro_df["p_bull"] = causal_posteriors[:, 0]
    macro_df["p_chop"] = causal_posteriors[:, 1]
    macro_df["p_bear"] = causal_posteriors[:, 2]
    macro_df["hmm_entropy"] = -np.sum(causal_posteriors * np.log(causal_posteriors + 1e-8), axis=1)
    macro_df["dp_bull"] = macro_df["p_bull"].diff().fillna(0.0)
    macro_df["dp_bear"] = macro_df["p_bear"].diff().fillna(0.0)

    df_res = df_res.merge(macro_df[["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear"]].reset_index(), on="timestamp", how="left")

    # Target Barrier Label Generation
    bar_map = {ts: df_res[df_res["timestamp"] == ts].set_index("asset").to_dict("index") for ts in all_bars}
    recs = []
    for b_idx in range(len(all_bars) - max_hold_bars):
        ts = all_bars[b_idx]
        for sym, r in bar_map[ts].items():
            px, atr = r["close"], r["atr"]
            if px <= 0 or atr <= 0: continue
            tp_l, sl_l = px + (LONG_TP * atr), px - (LONG_SL * atr)
            tp_s, sl_s = px - (SHORT_TP * atr), px + (SHORT_SL * atr)
            hit_tp_l, hit_sl_l, hit_tp_s, hit_sl_s = False, False, False, False
            max_mae_l, max_mae_s = 0.0, 0.0
            for f_idx in range(b_idx + 1, b_idx + 1 + max_hold_bars):
                f_r = bar_map[all_bars[f_idx]].get(sym)
                if not f_r: continue
                f_o, f_h, f_l = f_r["open"], f_r["high"], f_r["low"]
                max_mae_l = max(max_mae_l, (px - f_l) / atr)
                max_mae_s = max(max_mae_s, (f_h - px) / atr)
                if not hit_tp_l and not hit_sl_l:
                    if f_h >= tp_l and f_l <= sl_l:
                        if abs(f_o - tp_l) <= abs(f_o - sl_l): hit_tp_l = True
                        else: hit_sl_l = True
                    elif f_h >= tp_l: hit_tp_l = True
                    elif f_l <= sl_l: hit_sl_l = True
                if not hit_tp_s and not hit_sl_s:
                    if f_l <= tp_s and f_h >= sl_s:
                        if abs(f_o - tp_s) <= abs(f_o - sl_s): hit_tp_s = True
                        else: hit_sl_s = True
                    elif f_l <= tp_s: hit_tp_s = True
                    elif f_h >= sl_s: hit_sl_s = True
            recs.append({
                "timestamp": ts, "asset": sym,
                "target_long": int(hit_tp_l and max_mae_l <= LONG_MAE),
                "target_short": int(hit_tp_s and max_mae_s <= SHORT_MAE)
            })

    df_res = df_res.merge(pd.DataFrame(recs), on=["timestamp", "asset"], how="inner")
    feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]
    for c in feature_cols: df_res[c] = pd.to_numeric(df_res[c], errors="coerce").fillna(0.0)

    # Fit Production CatBoost Models
    print(f"--> [3/4] Training CatBoost on {tf_str} bars...")
    is_mask = df_res["timestamp"] < cutoff_date
    cb_s = CatBoostClassifier(iterations=350, depth=4, learning_rate=0.04, l2_leaf_reg=5.0, thread_count=-1, verbose=False, random_seed=42).fit(df_res.loc[is_mask, feature_cols], df_res.loc[is_mask, "target_short"])
    cb_l = CatBoostClassifier(iterations=350, depth=4, learning_rate=0.03, l2_leaf_reg=5.0, thread_count=-1, verbose=False, random_seed=42).fit(df_res.loc[is_mask, feature_cols], df_res.loc[is_mask, "target_long"])

    df_res["p_model_short"] = cb_s.predict_proba(df_res[feature_cols])[:, 1]
    df_res["p_model_long"] = cb_l.predict_proba(df_res[feature_cols])[:, 1]

    q85_s = float(df_res.loc[is_mask, "p_model_short"].quantile(0.85))
    q92_l = float(df_res.loc[is_mask, "p_model_long"].quantile(0.92))

    # Portfolio Simulation
    print(f"--> [4/4] Simulating N=3, 3.5x Compounding Portfolio...")
    valid_bars = sorted(df_res["timestamp"].unique())
    b_data = {ts: df_res[df_res["timestamp"] == ts].set_index("asset").to_dict("index") for ts in valid_bars}

    equity = 1000.0
    equity_curve = [equity]
    active_positions = []
    trades = []
    total_fee_cost = 0.0

    for ts in valid_bars:
        curr = b_data.get(ts, {})
        if not curr: continue
        first = next(iter(curr.values()))
        p_bull, p_bear = first["p_bull"], first["p_bear"]

        surviving = []
        for pos in active_positions:
            sym = pos["asset"]
            if sym not in curr:
                surviving.append(pos)
                continue
            b = curr[sym]
            hi, lo, cl = b["high"], b["low"], b["close"]
            pos["bars"] += 1
            direction, entry_p, size_usd = pos["dir"], pos["entry_p"], pos["size"]
            tp_p = entry_p + (LONG_TP if direction == "LONG" else -SHORT_TP) * pos["atr"]
            sl_p = entry_p - (LONG_SL if direction == "LONG" else -SHORT_SL) * pos["atr"]

            hit_tp = (hi >= tp_p) if direction == "LONG" else (lo <= tp_p)
            hit_sl = (lo <= sl_p) if direction == "LONG" else (hi >= sl_p)
            exit_p = None

            if hit_tp: exit_p = tp_p
            elif hit_sl: exit_p = sl_p
            elif pos["bars"] >= max_hold_bars: exit_p = cl

            if exit_p is not None:
                pnl_pct = ((exit_p - entry_p) / entry_p) if direction == "LONG" else ((entry_p - exit_p) / entry_p)
                fee = size_usd * 2 * FEE_BPS
                total_fee_cost += fee
                net_usd = (size_usd * pnl_pct) - fee
                equity += net_usd
                trades.append({"dir": direction, "net_usd": net_usd})
            else:
                surviving.append(pos)

        active_positions = surviving
        open_slots = 3 - len(active_positions)

        if open_slots > 0 and equity > 25.0:
            active_syms = {p["asset"] for p in active_positions}
            short_cands = [(s, r["p_model_short"], r["atr_pct"], r["close"], r["atr"], "SHORT") for s, r in curr.items() if s not in active_syms and r["p_model_short"] >= q85_s and p_bear >= 0.45 and r["close"] > 0]
            long_cands = [(s, r["p_model_long"], r["atr_pct"], r["close"], r["atr"], "LONG") for s, r in curr.items() if s not in active_syms and r["p_model_long"] >= q92_l and p_bull >= 0.70 and r["close"] > 0]
            short_cands.sort(key=lambda x: -x[1])
            long_cands.sort(key=lambda x: -x[1])

            selected = short_cands[:open_slots] if len(short_cands) >= len(long_cands) and short_cands else long_cands[:open_slots]

            if selected:
                inv_atrs = [1.0 / max(c[2], 0.005) for c in selected]
                weights = [w / sum(inv_atrs) for w in inv_atrs]
                for idx, (sym, p_val, atr_p, px, atr, dir_str) in enumerate(selected):
                    slot_alloc = (equity * 3.5 * weights[idx]) * (len(selected) / 3)
                    active_positions.append({"asset": sym, "dir": dir_str, "entry_p": px, "atr": atr, "size": slot_alloc, "bars": 0})

        equity_curve.append(max(equity, 1.0))

    eq = pd.Series(equity_curve)
    ret = eq.pct_change().dropna()
    tot_ret = (eq.iloc[-1] - 1000.0) / 1000.0
    max_dd = abs(((eq / eq.cummax()) - 1.0).min())
    sortino = (ret.mean() / (ret[ret < 0].std() + 1e-6)) * np.sqrt(2190 * (4 / (seconds / 3600))) if len(ret[ret < 0]) > 0 else 0.0
    wr = (pd.DataFrame(trades)["net_usd"] > 0).mean() * 100 if trades else 0.0

    del df_res, bar_map, b_data
    gc.collect()

    return {
        "Timeframe": tf_str,
        "Terminal Eq": f"${eq.iloc[-1]:,.2f}",
        "Net Return": f"{tot_ret*100:>+7.1f}%",
        "Sortino": f"{sortino:>5.2f}",
        "Max Drawdown": f"{max_dd*100:>5.1f}%",
        "Win Rate": f"{wr:>4.1f}%",
        "Total Trades": len(trades),
        "Fees Paid": f"${total_fee_cost:,.2f}"
    }

# Grid: 1H, 2H, 4H, 8H with equivalent 72h max holding horizon
grid = [
    {"tf": "1H", "seconds": 3600, "lag_mom": 24, "max_hold": 72},
    {"tf": "2H", "seconds": 7200, "lag_mom": 12, "max_hold": 36},
    {"tf": "4H", "seconds": 14400, "lag_mom": 6, "max_hold": 18},
    {"tf": "8H", "seconds": 28800, "lag_mom": 3, "max_hold": 9}
]

results = [evaluate_timeframe(g["tf"], g["seconds"], g["lag_mom"], g["max_hold"]) for g in grid]

print("\n" + "=" * 115)
print("                   TIMEFRAME SENSITIVITY & PERFORMANCE BENCHMARK                   ")
print("=" * 115)
print(pd.DataFrame(results).to_string(index=False))
print("=" * 115)
