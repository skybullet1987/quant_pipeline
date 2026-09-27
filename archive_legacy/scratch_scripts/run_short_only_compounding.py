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

print("--> Pulling universe data from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT 
        f.*,
        COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
        COALESCE(t.tfm_slope, 0.0) AS tfm_slope
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t 
        ON f.timestamp = t.timestamp AND f.ticker = t.ticker
    WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {TOTAL_DAYS} DAY)
    ORDER BY f.timestamp ASC, f.ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
if "asset" not in df.columns and "ticker" in df.columns: df["asset"] = df["ticker"]
if "open" not in df.columns or df["open"].isnull().all(): df["open"] = df.groupby("asset")["close"].shift(1).fillna(df["close"])
df["atr_20"] = df["atr_20"].fillna(df["close"] * 0.02) if "atr_20" in df.columns else df["close"] * 0.02
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
df["dist_ema20_atr"] = (df["close"] - df["ema_20"]) / (df["atr_20"] + 1e-8)
df["mom_24h"] = df.groupby("asset")["close"].transform(lambda x: x.pct_change(6).fillna(0.0))

print("--> Loading HMM & Short Models...")
hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")
cat_set = set(joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/cat_cols.pkl") else [])

models_s = {}
for r in [0, 1, 2]:
    sp = f"{PROD_MODELS_DIR}/regime_{r}_short_expert.cbm"
    if os.path.exists(sp): models_s[str(r)] = CatBoostClassifier().load_model(sp)
fb_s = models_s.get("2", next(iter(models_s.values()), None))

for c in hmm_feats: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0) if c in df.columns else 0.0
probs = hmm_model.predict_proba(hmm_scaler.transform(df[hmm_feats]))[:, canonical_order]
df["p_chop"] = probs[:, 0]
df["regime"] = probs.argmax(axis=1).astype(str)

df["p_short"] = 0.50
for reg_val, group_idx in df.groupby("regime").groups.items():
    reg_str = str(reg_val)
    sub = df.loc[group_idx].copy()
    ms = models_s.get(reg_str, fb_s)
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

def run_short_sim(risk_fraction=0.04, max_slots=3, max_leverage=2.5, friction_bps=12.0):
    equity = INITIAL_CAPITAL
    active_positions = {}
    closed_trades = []
    equity_curve = []
    fee_rate = friction_bps / 10000.0

    for bar_idx, ts in enumerate(unique_bars):
        df_bar = bar_snapshots[ts]
        current_prices = df_bar.set_index("asset")["close"].to_dict()
        current_highs = df_bar.set_index("asset")["high"].to_dict()
        current_lows = df_bar.set_index("asset")["low"].to_dict()
        current_atrs = df_bar.set_index("asset")["atr_20"].to_dict()

        # 1. Update Short Positions (1.8x TP / 1.1x SL / 6-Bar Hold)
        closed_assets = []
        for asset, pos in list(active_positions.items()):
            if asset not in current_prices: continue
            high, low, close = current_highs[asset], current_lows[asset], current_prices[asset]
            atr = current_atrs.get(asset, (high - low))
            bars_held = bar_idx - pos["entry_bar"]

            hard_tp = pos["entry_price"] - (1.80 * atr)
            hard_sl = pos["entry_price"] + (1.10 * atr)

            hit_tp = (low <= hard_tp)
            hit_sl = (high >= hard_sl)
            hit_time = (not hit_tp and not hit_sl and bars_held >= 6)

            if hit_tp or hit_sl or hit_time:
                exit_p = hard_tp if hit_tp else (hard_sl if hit_sl else close)
                gross_pnl = pos["size_usd"] * (1.0 - (exit_p / pos["entry_price"]))
                net_pnl = gross_pnl - (pos["size_usd"] * fee_rate)
                equity += net_pnl
                closed_trades.append({"asset": asset, "pnl": net_pnl, "win": net_pnl > 0, "type": "TP" if hit_tp else ("SL" if hit_sl else "TIME")})
                closed_assets.append(asset)

        for a in closed_assets: del active_positions[a]

        # 2. Score & Rank Shorts (p_short <= 0.50 Continuation Sweetspot)
        mbi = (df_bar["close"] > df_bar["ema_20"]).mean()
        if mbi < 0.60: # Only short when market breadth is not in a runaway bull trend
            z_short_ml = robust_zscore(df_bar["p_short"].apply(lambda p: (1.0 - p) if p <= 0.50 else 0.0))
            z_mom = robust_zscore(df_bar["mom_24h"])
            df_bar = df_bar.copy()
            df_bar["short_score"] = (0.50 * z_short_ml) - (0.50 * z_mom)
            
            # Entry condition: breakdown structure + continuation confidence
            valid_shorts = df_bar[(df_bar["dist_ema20_atr"] < 0.0) & (df_bar["mom_24h"] < -0.01) & (df_bar["p_short"] <= 0.50)]
            top_shorts = valid_shorts.sort_values(by="short_score", ascending=False).head(max_slots)

            available_slots = max_slots - len(active_positions)
            if available_slots > 0 and equity > 50.0:
                pending = []
                for _, row in top_shorts.iterrows():
                    sym = row["asset"]
                    if sym not in active_positions and len(pending) < available_slots:
                        sl_dist = 1.10 * row["atr_20"]
                        nom_size = (equity * risk_fraction) / max(1e-6, sl_dist / row["close"])
                        pending.append({"asset": sym, "price": row["close"], "size": nom_size, "atr": row["atr_20"]})

                if pending:
                    tot_req = sum(p["size"] for p in pending)
                    curr_lev = tot_req / equity
                    if curr_lev > max_leverage:
                        scale = max_leverage / curr_lev
                        for p in pending: p["size"] *= scale

                    for p in pending:
                        active_positions[p["asset"]] = {
                            "entry_price": p["price"], "entry_bar": bar_idx,
                            "size_usd": p["size"], "atr": p["atr"]
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

    return mult, tot_ret, e_end, max_dd, pf, wr, len(df_t)

print("\n" + "=" * 100)
print("           ISOLATED SHORT PRODUCTION ENGINE: 270-DAY COMPOUNDING EVALUATION           ")
print("=" * 100)

for label, bps in [("Maker (3 bps)", 3.0), ("Base (12 bps)", 12.0), ("Stress (20 bps)", 20.0), ("Severe (25 bps)", 25.0)]:
    m, ret, end_cap, dd, pf, wr, n = run_short_sim(risk_fraction=0.04, max_slots=3, max_leverage=2.5, friction_bps=bps)
    print(f"[{label:<18}] Multiplier: {m:>5.2f}x | Ret: {ret:>+7.1f}% | Equity: ${end_cap:>8.2f} | MaxDD: {dd:>6.1f}% | PF: {pf:.2f} | WR: {wr:.1f}% | Trades: {n}")
print("=" * 100)
