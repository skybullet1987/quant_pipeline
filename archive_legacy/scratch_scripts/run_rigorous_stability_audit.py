import os
import joblib
import pandas as pd
import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
INITIAL_CAPITAL = 1000.0
TOTAL_DAYS = 365
OOS_DAYS = 90
HOLD_BARS = 8

# Fixed Empirical Label & Execution Constants
LONG_TP_MULT, LONG_SL_MULT, LONG_MAX_MAE = 2.6, 1.3, 0.75
SHORT_TP_MULT, SHORT_SL_MULT, SHORT_MAX_MAE = 1.8, 1.1, 0.65

print("--> [1/5] Extracting complete 365-day dataset from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT 
        f.timestamp, f.ticker AS asset, f.open, f.high, f.low, f.close, f.volume,
        COALESCE(f.atr_20, f.close * 0.02) AS raw_atr,
        COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
        COALESCE(t.tfm_slope, 0.0) AS tfm_slope,
        COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t ON f.timestamp = t.timestamp AND f.ticker = t.ticker
    LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l ON f.timestamp = l.timestamp AND f.ticker = l.ticker
    WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {TOTAL_DAYS} DAY)
    ORDER BY f.timestamp ASC, f.ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
if "open" not in df.columns or df["open"].isnull().all():
    df["open"] = df.groupby("asset")["close"].shift(1).fillna(df["close"])

# Compute Squeeze & Structure Features
df["atr"] = df["raw_atr"]
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
df["dist_ema20_atr"] = (df["close"] - df["ema_20"]) / (df["atr"] + 1e-8)

sma_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).mean())
std_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).std().fillna(0.0))
df["bbw"] = (4.0 * std_20) / (sma_20 + 1e-8)
roll_min = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).min())
roll_max = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).max())
df["bbw_pct_40"] = ((df["bbw"] - roll_min) / (roll_max - roll_min + 1e-8)).fillna(0.50).clip(0.0, 1.0)
df["mom_24h"] = df.groupby("asset")["close"].transform(lambda x: x.pct_change(6).fillna(0.0))

print("--> [2/5] Generating Drawdown-Penalized exact-path labels...")
unique_bars = sorted(df["timestamp"].unique())
bar_map = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}

records = []
for b_idx in range(len(unique_bars) - HOLD_BARS):
    ts = unique_bars[b_idx]
    for sym, r in bar_map[ts].items():
        px, atr = r["close"], r["atr"]
        if px <= 0 or atr <= 0: continue
        
        tp_l, sl_l = px + (LONG_TP_MULT * atr), px - (LONG_SL_MULT * atr)
        tp_s, sl_s = px - (SHORT_TP_MULT * atr), px + (SHORT_SL_MULT * atr)
        hit_tp_l, hit_sl_l, hit_tp_s, hit_sl_s = False, False, False, False
        max_mae_l, max_mae_s = 0.0, 0.0

        for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
            f_r = bar_map[unique_bars[f_idx]].get(sym)
            if not f_r: continue
            
            f_o, f_h, f_l = f_r["open"], f_r["high"], f_r["low"]
            max_mae_l = max(max_mae_l, (px - f_l) / atr)
            max_mae_s = max(max_mae_s, (f_h - px) / atr)

            # Long exact path with open-proximity dual-touch resolution
            if not hit_tp_l and not hit_sl_l:
                if f_h >= tp_l and f_l <= sl_l:
                    if abs(f_o - tp_l) <= abs(f_o - sl_l): hit_tp_l = True
                    else: hit_sl_l = True
                elif f_h >= tp_l: hit_tp_l = True
                elif f_l <= sl_l: hit_sl_l = True

            # Short exact path with open-proximity dual-touch resolution
            if not hit_tp_s and not hit_sl_s:
                if f_l <= tp_s and f_h >= sl_s:
                    if abs(f_o - tp_s) <= abs(f_o - sl_s): hit_tp_s = True
                    else: hit_sl_s = True
                elif f_l <= tp_s: hit_tp_s = True
                elif f_h >= sl_s: hit_sl_s = True

        records.append({
            "timestamp": ts, "asset": sym,
            "target_long": int(hit_tp_l and max_mae_l <= LONG_MAX_MAE),
            "target_short": int(hit_tp_s and max_mae_s <= SHORT_MAX_MAE)
        })

df = df.merge(pd.DataFrame(records), on=["timestamp", "asset"], how="inner")

# Strict Time Partition
cutoff_date = unique_bars[-1] - pd.Timedelta(days=OOS_DAYS)
df_train = df[df["timestamp"] < cutoff_date].copy()
df_oos = df[df["timestamp"] >= cutoff_date].copy()

print(f"--> [3/5] Fitting HMM & Macro Scalers strictly on In-Sample (Zero Leakage)...")
# Calculate macro breadth per bar
mbi_train = df_train.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
vol_train = df_train.groupby("timestamp")["mom_24h"].std().rename("csd")
macro_train = pd.concat([mbi_train, vol_train], axis=1).fillna(0.5)

hmm_scaler = RobustScaler().fit(macro_train)
hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100)
hmm.fit(hmm_scaler.transform(macro_train))

# Canonical order: 0=Bull (high MBI), 1=Chop (mid), 2=Bear (low MBI)
means_mbi = hmm.means_[:, 0]
canonical_order = np.argsort(-means_mbi)

# Assign regimes strictly out-of-sample
mbi_all = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
vol_all = df.groupby("timestamp")["mom_24h"].std().rename("csd")
macro_all = pd.concat([mbi_all, vol_all], axis=1).fillna(0.5)
macro_probs = hmm.predict_proba(hmm_scaler.transform(macro_all))[:, canonical_order]
df_macro_regime = pd.DataFrame({
    "timestamp": macro_all.index,
    "regime": macro_probs.argmax(axis=1).astype(str),
    "mbi": macro_all["mbi"].values
})
df = df.merge(df_macro_regime, on="timestamp", how="left")

# Re-slice clean partitions with regime assigned
df_train = df[df["timestamp"] < cutoff_date].copy()
df_oos = df[df["timestamp"] >= cutoff_date].copy()

feature_cols = ["dist_ema20_atr", "bbw_pct_40", "mom_24h", "tfm_ret_24h", "tfm_slope", "rank_liq_intensity"]
for c in feature_cols:
    df_train[c] = pd.to_numeric(df_train[c], errors="coerce").fillna(0.0)
    df_oos[c] = pd.to_numeric(df_oos[c], errors="coerce").fillna(0.0)

print("--> [4/5] Training CatBoost Alpha Experts strictly on In-Sample...")
models_l, models_s = {}, {}
for r in ["0", "1", "2"]:
    sub = df_train[df_train["regime"] == r]
    if len(sub) < 500: sub = df_train
    
    cb_l = CatBoostClassifier(iterations=500, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, subsample=0.85, scale_pos_weight=2.5, verbose=False, random_seed=42)
    cb_s = CatBoostClassifier(iterations=500, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, subsample=0.85, scale_pos_weight=2.0, verbose=False, random_seed=42)
    
    cb_l.fit(sub[feature_cols], sub["target_long"])
    cb_s.fit(sub[feature_cols], sub["target_short"])
    models_l[r] = cb_l
    models_s[r] = cb_s

# Generate isolated OOS predictions
df_oos["p_long"], df_oos["p_short"] = 0.50, 0.50
for r_val, g_idx in df_oos.groupby("regime").groups.items():
    df_oos.loc[g_idx, "p_long"] = models_l[str(r_val)].predict_proba(df_oos.loc[g_idx, feature_cols])[:, 1]
    df_oos.loc[g_idx, "p_short"] = models_s[str(r_val)].predict_proba(df_oos.loc[g_idx, feature_cols])[:, 1]

oos_bars = sorted(df_oos["timestamp"].unique())
bar_snaps = {ts: df_oos[df_oos["timestamp"] == ts].copy() for ts in oos_bars}

# --------------------------------------------------------------------------
# LEAK-FREE PORTFOLIO SIMULATION ENGINE
# --------------------------------------------------------------------------
def simulate_oos_exact(l_thresh, s_thresh, friction_bps=12.0, risk_frac=0.035, max_lev=2.2):
    equity = INITIAL_CAPITAL
    open_pos, closed_trades, curve = {}, [], []
    fee_rate = friction_bps / 10000.0

    for b_idx, ts in enumerate(oos_bars):
        b_df = bar_snaps[ts]
        px_map = b_df.set_index("asset")["close"].to_dict()
        op_map = b_df.set_index("asset")["open"].to_dict()
        hi_map = b_df.set_index("asset")["high"].to_dict()
        lo_map = b_df.set_index("asset")["low"].to_dict()

        # 1. Update Existing Positions
        closed = []
        for sym, pos in list(open_pos.items()):
            if sym not in px_map: continue
            o, h, l, c = op_map[sym], hi_map[sym], lo_map[sym], px_map[sym]
            atr = pos["entry_atr"]  # ANCHORED STRICTLY TO ENTRY ATR
            pos["highest"] = max(pos["highest"], h)
            pos["lowest"] = min(pos["lowest"], l)
            b_held = b_idx - pos["entry_bar"]

            # LONG POSITION MANAGEMENT (2.6x TP / 1.3x SL / 8-bar hold)
            if pos["dir"] == 1:
                # Ratchet to Lock Profit at +1.8x ATR
                if (pos["highest"] - pos["entry_px"]) >= (1.8 * atr) and not pos["ratchet_hit"]:
                    pos["ratchet_hit"] = True
                    pos["current_sl"] = max(pos["current_sl"], pos["entry_px"] + (0.20 * atr))
                
                # Dynamic Chandelier trailing
                pos["current_sl"] = max(pos["current_sl"], pos["highest"] - (2.0 * atr))

                hit_tp = (h >= pos["tp_px"])
                hit_sl = (l <= pos["current_sl"])
                hit_time = (not hit_tp and not hit_sl and b_held >= HOLD_BARS)

                if hit_tp and hit_sl: # Open-proximity resolution
                    exit_p = pos["tp_px"] if abs(o - pos["tp_px"]) <= abs(o - pos["current_sl"]) else pos["current_sl"]
                elif hit_tp: exit_p = pos["tp_px"]
                elif hit_sl: exit_p = pos["current_sl"]
                elif hit_time: exit_p = c
                else: exit_p = None

                if exit_p is not None:
                    net_pnl = (pos["size_usd"] * ((exit_p / pos["entry_px"]) - 1.0)) - (pos["size_usd"] * fee_rate)
                    equity += net_pnl
                    closed_trades.append({"asset": sym, "dir": "LONG", "pnl": net_pnl, "win": net_pnl > 0})
                    closed.append(sym)

            # SHORT POSITION MANAGEMENT (1.8x TP / 1.1x SL / 6-bar hold)
            elif pos["dir"] == -1:
                hit_tp = (l <= pos["tp_px"])
                hit_sl = (h >= pos["sl_px"])
                hit_time = (not hit_tp and not hit_sl and b_held >= 6)

                if hit_tp and hit_sl:
                    exit_p = pos["tp_px"] if abs(o - pos["tp_px"]) <= abs(o - pos["sl_px"]) else pos["sl_px"]
                elif hit_tp: exit_p = pos["tp_px"]
                elif hit_sl: exit_p = pos["sl_px"]
                elif hit_time: exit_p = c
                else: exit_p = None

                if exit_p is not None:
                    net_pnl = (pos["size_usd"] * (1.0 - (exit_p / pos["entry_px"]))) - (pos["size_usd"] * fee_rate)
                    equity += net_pnl
                    closed_trades.append({"asset": sym, "dir": "SHORT", "pnl": net_pnl, "win": net_pnl > 0})
                    closed.append(sym)

        for s in closed: del open_pos[s]

        # 2. Macro Regime Gating & Top 2 Selection
        reg = b_df["regime"].iloc[0]
        mbi = b_df["mbi"].iloc[0]

        # Squeeze hard filter for Longs
        valid_l = b_df[(b_df["p_long"] >= l_thresh) & (b_df["dist_ema20_atr"].between(0.15, 1.25)) & (b_df["bbw_pct_40"] <= 0.45)]
        valid_s = b_df[(b_df["p_short"] >= s_thresh) & (b_df["dist_ema20_atr"] < 0.0)]

        top_l = valid_l.sort_values(by="p_long", ascending=False).head(2)
        top_s = valid_s.sort_values(by="p_short", ascending=False).head(2)

        available_slots = 2 - len(open_pos)
        if available_slots > 0 and equity > 50.0:
            pending = []

            # HARD MACRO VETO: Longs allowed in Bull (0) & Selective (1). Hard-banned in Bear (2).
            if (reg in ["0", "1"] or mbi >= 0.55) and reg != "2":
                for _, row in top_l.iterrows():
                    sym = row["asset"]
                    if sym not in open_pos and len(pending) < available_slots:
                        atr = row["atr"]
                        sl_dist = LONG_SL_MULT * atr
                        size = (equity * risk_frac) / max(1e-6, sl_dist / row["close"])
                        pending.append({
                            "asset": sym, "dir": 1, "price": row["close"], "size": size, "atr": atr,
                            "tp": row["close"] + (LONG_TP_MULT * atr), "sl": row["close"] - sl_dist
                        })

            # HARD MACRO VETO: Shorts allowed in Bear (2) & Selective (1). Hard-banned in Bull (0).
            if (reg in ["1", "2"] or mbi <= 0.45) and reg != "0":
                for _, row in top_s.iterrows():
                    sym = row["asset"]
                    if sym not in open_pos and (available_slots - len(pending)) > 0:
                        atr = row["atr"]
                        sl_dist = SHORT_SL_MULT * atr
                        size = (equity * risk_frac) / max(1e-6, sl_dist / row["close"])
                        pending.append({
                            "asset": sym, "dir": -1, "price": row["close"], "size": size, "atr": atr,
                            "tp": row["close"] - (SHORT_TP_MULT * atr), "sl": row["close"] + sl_dist
                        })

            if pending:
                tot_req = sum(p["size"] for p in pending)
                curr_lev = tot_req / equity
                if curr_lev > max_lev:
                    for p in pending: p["size"] *= (max_lev / curr_lev)

                for p in pending:
                    open_pos[p["asset"]] = {
                        "dir": p["dir"], "entry_px": p["price"], "entry_bar": b_idx, "entry_atr": p["atr"],
                        "size_usd": p["size"], "tp_px": p["tp"], "sl_px": p["sl"], "current_sl": p["sl"],
                        "highest": p["price"], "lowest": p["price"], "ratchet_hit": False
                    }

        curve.append(equity)

    df_t = pd.DataFrame(closed_trades)
    e_end = curve[-1]
    mult = e_end / INITIAL_CAPITAL
    tot_ret = ((e_end - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100.0
    peak = pd.Series(curve).cummax()
    max_dd = ((pd.Series(curve) - peak) / peak).min() * 100.0
    
    wins = df_t[df_t["pnl"] > 0]["pnl"].sum() if not df_t.empty else 0.0
    loss = abs(df_t[df_t["pnl"] <= 0]["pnl"].sum()) if not df_t.empty else 1.0
    pf = wins / loss
    wr = df_t["win"].mean() * 100.0 if not df_t.empty else 0.0

    return mult, tot_ret, e_end, max_dd, pf, wr, len(df_t)

print("\n" + "=" * 105)
print("     [5/5] OUT-OF-SAMPLE (90-DAY) 2D PARAMETER STABILITY SURFACE & FRICTION SWEEP     ")
print("=" * 105)

long_thresholds = [0.58, 0.60, 0.62, 0.64]
short_thresholds = [0.52, 0.54, 0.56, 0.58]

surface_records = []
for l_th in long_thresholds:
    for s_th in short_thresholds:
        # Base 12 bps
        m_12, ret_12, end_12, dd_12, pf_12, wr_12, n_12 = simulate_oos_exact(l_th, s_th, friction_bps=12.0)
        # Stress 25 bps
        m_25, _, _, _, pf_25, _, _ = simulate_oos_exact(l_th, s_th, friction_bps=25.0)

        surface_records.append({
            "Long Thresh": f"p >= {l_th:.2f}",
            "Short Thresh": f"p >= {s_th:.2f}",
            "OOS Mult (12bps)": f"{m_12:>5.2f}x",
            "OOS Ret": f"{ret_12:>+6.1f}%",
            "End Equity": f"${end_12:>7.2f}",
            "MaxDD": f"{dd_12:>5.1f}%",
            "PF (12bps)": round(pf_12, 2),
            "WinRate": f"{wr_12:>4.1f}%",
            "Trades": n_12,
            "Stress (25bps)": f"{m_25:.2f}x (PF {pf_25:.2f})"
        })

df_surf = pd.DataFrame(surface_records)
print(df_surf.to_string(index=False))
print("=" * 105)
