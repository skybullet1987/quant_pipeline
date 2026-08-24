import os, sys, warnings
PROJECT_ROOT = os.path.abspath(os.getenv("QUANT_PROJECT_ROOT", "/home/skybullet1987/quant_pipeline"))
import numpy as np, pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV

warnings.filterwarnings("ignore")

# Load Scored Feature Mart
df = pd.read_parquet(f"{PROJECT_ROOT}/data/oos_scored_mart.parquet")
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(by=["timestamp", "asset"]).reset_index(drop=True)

# 1. Temporal Partitioning (Train / Dev / OOS) with 18-Bar (72H) Embargo
timestamps = sorted(df["timestamp"].unique())
n_bars = len(timestamps)

train_end_idx = int(n_bars * 0.50)
dev_end_idx = int(n_bars * 0.70)
embargo_bars = 18

train_ts = timestamps[:train_end_idx]
dev_ts = timestamps[train_end_idx + embargo_bars : dev_end_idx]
oos_ts = timestamps[dev_end_idx + embargo_bars :]

print("="*75)
print("             PURGED TEMPORAL PARTITIONING")
print("="*75)
print(f"Train Set : {train_ts[0].date()} -> {train_ts[-1].date()} ({len(train_ts)} bars)")
print(f"Dev Set   : {dev_ts[0].date()} -> {dev_ts[-1].date()} ({len(dev_ts)} bars)")
print(f"OOS Set   : {oos_ts[0].date()} -> {oos_ts[-1].date()} ({len(oos_ts)} bars)")
print("="*75 + "\n")

# Label Generation: Target is 1.8x ATR favorable excursion reached before 0.85x ATR SL
feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]

# Mock/Simulated TabFM inference wrapper (replace with torch tabpfn/tabfm when available)
# Simulates TabFM attention-based non-linear transformation over feature space
class TabFMChallengerModel:
    def __init__(self):
        self.calibrator = None
        self.cb_aux = CatBoostClassifier(iterations=120, depth=4, learning_rate=0.03, l2_leaf_reg=5.0, verbose=0, random_seed=1337)
    
    def fit(self, X, y):
        # Emulate foundation tabular transformer representation
        self.cb_aux.fit(X, y)
        raw_probs = self.cb_aux.predict_proba(X)[:, 1]
        self.calibrator = LogisticRegression().fit(raw_probs.reshape(-1, 1), y)
        return self

    def predict_proba(self, X):
        raw = self.cb_aux.predict_proba(X)[:, 1]
        cal_p = self.calibrator.predict_proba(raw.reshape(-1, 1))[:, 1]
        return np.vstack([1.0 - cal_p, cal_p]).T

# Create Binary Directional Labels for Short Breakdowns (Primary Engine Alpha)
df["target_short"] = 0
df_indexed = df.set_index(["timestamp", "asset"]).sort_index()

for idx, row in df.iterrows():
    ts = row["timestamp"]
    sym = row["asset"]
    px0 = row["close"]
    atr = row["atr"]
    t_idx = timestamps.index(ts)
    
    fwd_bars = timestamps[t_idx + 1 : min(t_idx + 19, len(timestamps))]
    hit_tp, hit_sl = False, False
    for f_ts in fwd_bars:
        if (f_ts, sym) in df_indexed.index:
            r = df_indexed.loc[(f_ts, sym)]
            if r["high"] >= px0 + (0.85 * atr):
                hit_sl = True
                break
            if r["low"] <= px0 - (1.80 * atr):
                hit_tp = True
                break
    df.at[idx, "target_short"] = 1 if (hit_tp and not hit_sl) else 0

train_mask = df["timestamp"].isin(train_ts)
dev_mask = df["timestamp"].isin(dev_ts)
oos_mask = df["timestamp"].isin(oos_ts)

X_train, y_train = df.loc[train_mask, feature_cols], df.loc[train_mask, "target_short"]
X_dev, y_dev = df.loc[dev_mask, feature_cols], df.loc[dev_mask, "target_short"]
X_oos, y_oos = df.loc[oos_mask, feature_cols], df.loc[oos_mask, "target_short"]

# 2. Train Champion CatBoost & Challenger TabFM
cb_champ = CatBoostClassifier(iterations=250, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, verbose=0, random_seed=42).fit(X_train, y_train)
tabfm_model = TabFMChallengerModel().fit(X_train, y_train)

# Predictions
p_cb_dev = cb_champ.predict_proba(X_dev)[:, 1]
p_tfm_dev = tabfm_model.predict_proba(X_dev)[:, 1]

p_cb_oos = cb_champ.predict_proba(X_oos)[:, 1]
p_tfm_oos = tabfm_model.predict_proba(X_oos)[:, 1]

# 3. Test B: Find Optimal Linear Blend Weight on DEV set only
blend_weights = [0.1, 0.2, 0.3, 0.4, 0.5]
best_w, best_dev_brier = 0.0, 999.0

for w in blend_weights:
    p_blend = (1 - w) * p_cb_dev + w * p_tfm_dev
    b_score = brier_score_loss(y_dev, p_blend)
    if b_score < best_dev_brier:
        best_dev_brier = b_score
        best_w = w

# 4. Test C: Retrain Meta-Feature CatBoost
df_meta = df.copy()
all_p_tfm = tabfm_model.predict_proba(df[feature_cols])[:, 1]
df_meta["tfm_prob"] = all_p_tfm
df_meta["tfm_spread"] = all_p_tfm - df["p_model_short"]
df_meta["tfm_rank"] = df_meta.groupby("timestamp")["tfm_prob"].rank(pct=True)

meta_cols = feature_cols + ["tfm_prob", "tfm_spread", "tfm_rank"]
cb_meta = CatBoostClassifier(iterations=250, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, verbose=0, random_seed=42)
cb_meta.fit(df_meta.loc[train_mask, meta_cols], y_train)

p_meta_oos = cb_meta.predict_proba(df_meta.loc[oos_mask, meta_cols])[:, 1]
p_blend_oos = (1 - best_w) * p_cb_oos + best_w * p_tfm_oos

# 5. OOS Statistical Comparison
print("="*75)
print("             OUT-OF-SAMPLE (OOS) METRIC COMPARISON")
print("="*75)

models = {
    "Champion (CatBoost)": p_cb_oos,
    "Challenger (Pure TabFM)": p_tfm_oos,
    f"Blend ({(1-best_w)*100:.0f}% CB / {best_w*100:.0f}% TFM)": p_blend_oos,
    "Meta-Feature (CatBoost + TFM Inputs)": p_meta_oos
}

metrics = []
for name, preds in models.items():
    auc = roc_auc_score(y_oos, preds)
    brier = brier_score_loss(y_oos, preds)
    ll = log_loss(y_oos, preds)
    
    # Continuation rate on top decile predictions
    top_decile_cutoff = np.percentile(preds, 85)
    top_mask = preds >= top_decile_cutoff
    continuation_rate = y_oos[top_mask].mean() * 100 if top_mask.sum() > 0 else 0.0

    metrics.append({
        "Model Architecture": name,
        "AUC-ROC": round(auc, 4),
        "Brier Score": round(brier, 4),
        "Log-Loss": round(ll, 4),
        "Top-15% Setup Continuation (>=1.8x ATR)": f"{continuation_rate:.2f}%"
    })

print(pd.DataFrame(metrics).to_string(index=False))

# 6. Conditional Incremental Alpha Table
print("\n" + "="*75)
print("     CONDITIONAL ALPHA: Does TabFM Differentiate Inside CatBoost Q >= 0.245?")
print("="*75)

oos_subset = df.loc[oos_mask].copy()
oos_subset["p_cb"] = p_cb_oos
oos_subset["p_tfm"] = p_tfm_oos
oos_subset["y"] = y_oos

eligible_setups = oos_subset[oos_subset["p_cb"] >= 0.245].copy()
eligible_setups["tfm_residual_signal"] = eligible_setups["p_tfm"] - eligible_setups["p_cb"]

eligible_setups["tfm_bucket"] = pd.qcut(eligible_setups["tfm_residual_signal"], q=3, labels=["TabFM Bearish/Negative", "TabFM Neutral", "TabFM Bullish/Positive"])

cond_summary = eligible_setups.groupby("tfm_bucket", observed=False).agg(
    count=("y", "count"),
    realized_tp_rate=("y", lambda x: f"{x.mean()*100:.2f}%")
).reset_index()

print(cond_summary.to_string(index=False))
