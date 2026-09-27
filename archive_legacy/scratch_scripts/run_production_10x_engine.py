import os
import joblib
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
PROD_MODELS_DIR = "models/prod"
INITIAL_CAPITAL = 1000.0
TOTAL_DAYS = 270

print("--> [1/4] Pulling 270 days of 4H universe data from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT 
        f.*,
        COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
        COALESCE(t.tfm_slope, 0.0) AS tfm_slope,
        COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t 
        ON f.timestamp = t.timestamp AND f.ticker = t.ticker
    LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l 
        ON f.timestamp = l.timestamp AND f.ticker = l.ticker
    WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {TOTAL_DAYS} DAY)
    ORDER BY f.timestamp ASC, f.ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Normalize column mappings
if "asset" not in df.columns and "ticker" in df.columns:
    df["asset"] = df["ticker"]

if "open" not in df.columns or df["open"].isnull().all():
    df["open"] = df.groupby("asset")["close"].shift(1).fillna(df["close"])

if "atr_20" in df.columns:
    df["raw_atr"] = df["atr_20"].fillna(df["close"] * 0.02)
elif "atr" in df.columns:
    df["raw_atr"] = df["atr"].fillna(df["close"] * 0.02)
else:
    df["raw_atr"] = df["close"] * 0.02

if "funding_rate" in df.columns:
    df["funding_rate"] = df["funding_rate"].fillna(0.0)
else:
    df["funding_rate"] = 0.0

print("--> [2/4] Engineering Cross-Sectional Squeeze, Distance & Microstructure Features...")
df["atr_20"] = df["raw_atr"]
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
df["dist_ema20_atr"] = (df["close"] - df["ema_20"]) / (df["atr_20"] + 1e-8)

sma_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).mean())
std_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).std().fillna(0.0))
bb_upper = sma_20 + 2.0 * std_20
bb_lower = sma_20 - 2.0 * std_20
df["bbw"] = (bb_upper - bb_lower) / (sma_20 + 1e-8)

roll_min = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).min())
roll_max = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).max())
df["bbw_pct_40"] = ((df["bbw"] - roll_min) / (roll_max - roll_min + 1e-8)).fillna(0.50).clip(0.0, 1.0)
df["mom_24h"] = df.groupby("asset")["close"].transform(lambda x: x.pct_change(6).fillna(0.0))
df["funding_annual"] = df["funding_rate"] * 24.0 * 365.0

print("--> [3/4] Computing Directional Expert Model Probabilities...")
hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")
cat_set = set(joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/cat_cols.pkl") else [])

models_l, models_s = {}, {}
for r in [0, 1, 2]:
    lp, sp = f"{PROD_MODELS_DIR}/regime_{r}_long_expert.cbm", f"{PROD_MODELS_DIR}/regime_{r}_short_expert.cbm"
    if os.path.exists(lp): models_l[str(r)] = CatBoostClassifier().load_model(lp)
    if os.path.exists(sp): models_s[str(r)] = CatBoostClassifier().load_model(sp)

fb_l = models_l.get("1", next(iter(models_l.values()), None))
fb_s = models_s.get("2", next(iter(models_s.values()), None))

for c in hmm_feats: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0) if c in df.columns else 0.0
probs = hmm_model.predict_proba(hmm_scaler.transform(df[hmm_feats]))[:, canonical_order]
df["p_chop"] = probs[:, 0]
df["regime"] = probs.argmax(axis=1).astype(str)

df["p_long"], df["p_short"] = 0.50, 0.50
for reg_val, group_idx in df.groupby("regime").groups.items():
    reg_str = str(reg_val)
    sub = df.loc[group_idx].copy()
    ml, ms = models_l.get(reg_str, fb_l), models_s.get(reg_str, fb_s)

    for c in ml.feature_names_:
        if c in ["hmm_regime", "regime"]: sub[c] = reg_str
        elif c in cat_set: sub[c] = sub[c].fillna("missing").astype(str)
        else: sub[c] = pd.to_numeric(sub[c], errors="coerce").fillna(0.0) if c in sub.columns else 0.0
    df.loc[group_idx, "p_long"] = ml.predict_proba(Pool(sub[ml.feature_names_], cat_features=[c for c in ml.feature_names_ if c in cat_set]))[:, 1]

    for c in ms.feature_names_:
        if c in ["hmm_regime", "regime"]: sub[c] = reg_str
        elif c in cat_set: sub[c] = sub[c].fillna("missing").astype(str)
        else: sub[c] = pd.to_numeric(sub[c], errors="coerce").fillna(0.0) if c in sub.columns else 0.0
    df.loc[group_idx, "p_short"] = ms.predict_proba(Pool(sub[ms.feature_names_], cat_features=[c for c in ms.feature_names_ if c in cat_set]))[:, 1]

unique_bars = sorted(df["timestamp"].unique())
bar_snapshots = {ts: df[df["timestamp"] == ts].copy() for ts in unique_bars}

def robust_zscore(series: pd.Series) -> pd.Series:
    median = series.median()
    iqr = series.quantile(0.75) - series.quantile(0.25)
    if iqr == 0 or np.isnan(iqr): return series - median
    return (series - median) / (iqr * 0.7413)

def run_production_simulation(friction_bps=12.0):
    equity = INITIAL_CAPITAL
    active_positions = {}
    closed_trades = []
    equity_curve = []

    # Risk parameters (Quarter-Kelly)
    risk_fraction = 0.04
    max_gross_leverage = 2.50
    long_sl_atr = 1.30
    short_sl_atr = 1.10
    fee_rate = friction_bps / 10000.0

    for bar_idx, ts in enumerate(unique_bars):
        df_bar = bar_snapshots[ts]
        current_prices = df_bar.set_index("asset")["close"].to_dict()
        current_highs = df_bar.set_index("asset")["high"].to_dict()
        current_lows = df_bar.set_index("asset")["low"].to_dict()
        current_atrs = df_bar.set_index("asset")["atr_20"].to_dict()

        # 1. Update Existing Positions
        closed_assets = []
        for asset, pos in list(active_positions.items()):
            if asset not in current_prices: continue
            high, low, close = current_highs[asset], current_lows[asset], current_prices[asset]
            atr = current_atrs.get(asset, (high - low))
            bars_held = bar_idx - pos["entry_bar"]

            pos["highest_price"] = max(pos["highest_price"], high)
            pos["lowest_price"] = min(pos["lowest_price"], low)

            # LONG POSITION MANAGEMENT (Partial TP + Chandelier Trailing Stop)
            if pos["direction"] == 1:
                mfe_atr = (pos["highest_price"] - pos["entry_price"]) / (atr + 1e-8)
                if mfe_atr >= 2.0 and not pos["partial_tp_hit"]:
                    pos["partial_tp_hit"] = True
                    pnl_fraction = 0.40
                    exit_p = pos["entry_price"] + 2.0 * atr
                    gross_pnl = (pos["size_usd"] * pnl_fraction) * ((exit_p / pos["entry_price"]) - 1.0)
                    net_pnl = gross_pnl - (pos["size_usd"] * pnl_fraction * fee_rate)
                    equity += net_pnl
                    pos["size_usd"] *= (1.0 - pnl_fraction)
                    pos["current_sl"] = max(pos["current_sl"], pos["entry_price"] + 0.20 * atr)

                chandelier_stop = pos["highest_price"] - 2.20 * atr
                pos["current_sl"] = max(pos["current_sl"], chandelier_stop)

                if low <= pos["current_sl"]:
                    exit_p = pos["current_sl"]
                    gross_pnl = pos["size_usd"] * ((exit_p / pos["entry_price"]) - 1.0)
                    net_pnl = gross_pnl - (pos["size_usd"] * fee_rate)
                    equity += net_pnl
                    closed_trades.append({"asset": asset, "dir": "LONG", "pnl": net_pnl, "bars": bars_held, "win": net_pnl > 0})
                    closed_assets.append(asset)
                elif bars_held >= 12:  # 48-Hour Vertical Barrier
                    exit_p = close
                    gross_pnl = pos["size_usd"] * ((exit_p / pos["entry_price"]) - 1.0)
                    net_pnl = gross_pnl - (pos["size_usd"] * fee_rate)
                    equity += net_pnl
                    closed_trades.append({"asset": asset, "dir": "LONG", "pnl": net_pnl, "bars": bars_held, "win": net_pnl > 0})
                    closed_assets.append(asset)

            # SHORT POSITION MANAGEMENT (Fixed Asymmetric Capture: 1.8x TP / 1.1x SL)
            elif pos["direction"] == -1:
                hard_tp = pos["entry_price"] - 1.80 * atr
                hard_sl = pos["current_sl"]

                if low <= hard_tp:
                    exit_p = hard_tp
                    gross_pnl = pos["size_usd"] * (1.0 - (exit_p / pos["entry_price"]))
                    net_pnl = gross_pnl - (pos["size_usd"] * fee_rate)
                    equity += net_pnl
                    closed_trades.append({"asset": asset, "dir": "SHORT", "pnl": net_pnl, "bars": bars_held, "win": net_pnl > 0})
                    closed_assets.append(asset)
                elif high >= hard_sl:
                    exit_p = hard_sl
                    gross_pnl = pos["size_usd"] * (1.0 - (exit_p / pos["entry_price"]))
                    net_pnl = gross_pnl - (pos["size_usd"] * fee_rate)
                    equity += net_pnl
                    closed_trades.append({"asset": asset, "dir": "SHORT", "pnl": net_pnl, "bars": bars_held, "win": net_pnl > 0})
                    closed_assets.append(asset)
                elif bars_held >= 6:  # 24-Hour Vertical Barrier
                    exit_p = close
                    gross_pnl = pos["size_usd"] * (1.0 - (exit_p / pos["entry_price"]))
                    net_pnl = gross_pnl - (pos["size_usd"] * fee_rate)
                    equity += net_pnl
                    closed_trades.append({"asset": asset, "dir": "SHORT", "pnl": net_pnl, "bars": bars_held, "win": net_pnl > 0})
                    closed_assets.append(asset)

        for a in closed_assets: del active_positions[a]

        # 2. Cross-Sectional Ranking & Macro Evaluation
        mbi = (df_bar["close"] > df_bar["ema_20"]).mean()
        csd = df_bar["mom_24h"].std()

        if mbi >= 0.65 and csd >= 0.035: regime = 0
        elif mbi < 0.35: regime = 2
        else: regime = 1

        z_l_ml = robust_zscore(df_bar["p_long"])
        z_mom = robust_zscore(df_bar["mom_24h"])
        z_bbw_inv = robust_zscore(-df_bar["bbw_pct_40"])
        z_dist_inv = robust_zscore(-df_bar["dist_ema20_atr"].abs())
        z_fund = robust_zscore(df_bar["funding_annual"])

        df_bar = df_bar.copy()
        df_bar["long_score"] = (0.35 * z_l_ml) + (0.25 * z_mom) + (0.15 * z_bbw_inv) + (0.15 * z_dist_inv) - (0.10 * z_fund)

        long_valid = (
            (df_bar["dist_ema20_atr"] >= 0.20) &
            (df_bar["dist_ema20_atr"] <= 1.20) &
            (df_bar["bbw_pct_40"] <= 0.45) &
            (df_bar["funding_annual"] <= 0.35)
        )

        z_short_ml = robust_zscore(df_bar["p_short"].apply(lambda p: (1.0 - p) if p <= 0.50 else 0.0))
        df_bar["short_score"] = (0.40 * z_short_ml) + (0.30 * z_fund) - (0.30 * z_mom)
        short_valid = (df_bar["dist_ema20_atr"] < 0.0) & (df_bar["mom_24h"] < 0.0)

        top_longs = df_bar[long_valid].sort_values(by="long_score", ascending=False).head(2)
        top_shorts = df_bar[short_valid].sort_values(by="short_score", ascending=False).head(2)

        # 3. Position Allocation & Leverage Ceiling
        available_slots = 2 - len(active_positions)
        if available_slots > 0 and equity > 50.0:
            pending = []
            if regime in [0, 1]:
                for _, row in top_longs.iterrows():
                    sym = row["asset"]
                    if sym not in active_positions and len(pending) < available_slots:
                        sl_dist = long_sl_atr * row["atr_20"]
                        nom_size = (equity * risk_fraction) / max(1e-6, sl_dist / row["close"])
                        pending.append({"asset": sym, "dir": 1, "price": row["close"], "size": nom_size, "sl": row["close"] - sl_dist, "atr": row["atr_20"]})

            if regime in [1, 2]:
                for _, row in top_shorts.iterrows():
                    sym = row["asset"]
                    if sym not in active_positions and (available_slots - len(pending)) > 0:
                        sl_dist = short_sl_atr * row["atr_20"]
                        nom_size = (equity * risk_fraction) / max(1e-6, sl_dist / row["close"])
                        pending.append({"asset": sym, "dir": -1, "price": row["close"], "size": nom_size, "sl": row["close"] + sl_dist, "atr": row["atr_20"]})

            if pending:
                tot_req = sum(p["size"] for p in pending)
                curr_lev = tot_req / equity
                if curr_lev > max_gross_leverage:
                    scale = max_gross_leverage / curr_lev
                    for p in pending: p["size"] *= scale

                for p in pending:
                    active_positions[p["asset"]] = {
                        "direction": p["dir"], "entry_price": p["price"], "entry_bar": bar_idx,
                        "size_usd": p["size"], "current_sl": p["sl"], "partial_tp_hit": False,
                        "highest_price": p["price"], "lowest_price": p["price"]
                    }

        equity_curve.append(equity)

    df_t = pd.DataFrame(closed_trades)
    e_end = equity_curve[-1]
    mult = e_end / INITIAL_CAPITAL
    tot_ret = ((e_end - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100.0
    peak = pd.Series(equity_curve).cummax()
    max_dd = ((pd.Series(equity_curve) - peak) / peak).min() * 100.0
    
    wins = df_t[df_t["pnl"] > 0]["pnl"].sum() if not df_t.empty else 0.0
    loss = abs(df_t[df_t["pnl"] <= 0]["pnl"].sum()) if not df_t.empty else 1.0
    pf = wins / loss
    wr = df_t["win"].mean() * 100.0 if not df_t.empty else 0.0
    
    l_t = df_t[df_t["dir"] == "LONG"]
    s_t = df_t[df_t["dir"] == "SHORT"]
    l_wr = l_t["win"].mean() * 100.0 if not l_t.empty else 0.0
    s_wr = s_t["win"].mean() * 100.0 if not s_t.empty else 0.0
    l_pnl = l_t["pnl"].sum() if not l_t.empty else 0.0
    s_pnl = s_t["pnl"].sum() if not s_t.empty else 0.0

    return mult, tot_ret, e_end, max_dd, pf, wr, len(df_t), l_wr, s_wr, l_pnl, s_pnl

print("\n" + "=" * 115)
print("             PRODUCTION ARCHITECTURE: 270-DAY MULTI-TIER FRICTION STRESS TEST             ")
print("=" * 115)

friction_tiers = [
    ("Optimistic Maker (Post-Only)", 3.0),
    ("Baseline Production (12 bps)", 12.0),
    ("Moderate Stress (20 bps)", 20.0),
    ("Severe Slippage (25 bps)", 25.0),
    ("Extreme Illiquidity (35 bps)", 35.0)
]

results = []
for label, bps in friction_tiers:
    mult, tot_ret, e_end, max_dd, pf, wr, n_tr, l_wr, s_wr, l_pnl, s_pnl = run_production_simulation(bps)
    results.append({
        "Friction Regime": label,
        "Multiple": f"{mult:>5.2f}x",
        "Total Return": f"{tot_ret:>+7.1f}%",
        "Ending Capital": f"${e_end:>8.2f}",
        "Max Drawdown": f"{max_dd:>6.1f}%",
        "Profit Factor": round(pf, 2),
        "Win Rate": f"{wr:>5.1f}%",
        "Trades": n_tr,
        "Long PnL (WR%)": f"${l_pnl:>+6.0f} ({l_wr:.0f}%)",
        "Short PnL (WR%)": f"${s_pnl:>+6.0f} ({s_wr:.0f}%)"
    })

print(pd.DataFrame(results).to_string(index=False))
print("=" * 115)
