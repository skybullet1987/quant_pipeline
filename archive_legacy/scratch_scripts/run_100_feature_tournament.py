import os, warnings
import pandas as pd
import numpy as np
from scipy.stats import spearmanr, multivariate_normal
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier
from google.cloud import bigquery
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
TOTAL_DAYS, OOS_DAYS, HOLD_BARS = 365, 90, 8
LONG_TP, LONG_SL, LONG_MAE = 2.2, 1.1, 0.65
SHORT_TP, SHORT_SL, SHORT_MAE = 1.4, 0.9, 0.55

print("--> [1/5] Extracting 365-day universe from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT f.*, COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l 
        ON f.timestamp = l.timestamp AND f.ticker = l.ticker
    WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {TOTAL_DAYS} DAY)
    ORDER BY f.timestamp ASC, f.ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
if "asset" not in df.columns and "ticker" in df.columns: df["asset"] = df["ticker"]
df = df.sort_values(["asset", "timestamp"]).reset_index(drop=True)

if "open" not in df.columns or df["open"].isnull().all():
    df["open"] = df.groupby("asset")["close"].shift(1).fillna(df["close"])

df["atr"] = df["atr_20"].fillna(df["close"] * 0.02) if "atr_20" in df.columns else df["close"] * 0.02
df["funding_annual"] = df["funding_rate"].fillna(0.0) * 24.0 * 365.0 if "funding_rate" in df.columns else 0.0
df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
df["open_interest"] = pd.to_numeric(df.get("open_interest", df["volume"] * 2.5), errors="coerce").fillna(df["volume"] * 2.5)

unique_bars = sorted(df["timestamp"].unique())
cutoff_date = unique_bars[-1] - pd.Timedelta(days=OOS_DAYS)

print("--> [2/5] Computing Causal Online HMM Forward Pass (Model 0 Base)...")
df["ret_4h"] = df.groupby("asset")["close"].pct_change().fillna(0.0)
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())

mbi_ts = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
csd_ts = df.groupby("timestamp")["ret_4h"].std().fillna(0.01).rename("csd")
macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

macro_tr = macro_df[macro_df.index < cutoff_date][["mbi", "csd"]]
hmm_scaler = RobustScaler().fit(macro_tr)
X_train_scaled = hmm_scaler.transform(macro_tr)

hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100)
hmm.fit(X_train_scaled)
canonical_order = np.argsort(-hmm.means_[:, 0])

X_all_scaled = hmm_scaler.transform(macro_df[["mbi", "csd"]])
T_len = len(X_all_scaled)
alpha = np.zeros((T_len, 3))
B = np.zeros((T_len, 3))
for j in range(3):
    B[:, j] = multivariate_normal.pdf(X_all_scaled, mean=hmm.means_[j], cov=hmm.covars_[j] + np.eye(2) * 1e-4)

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

df = df.merge(macro_df[["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear"]].reset_index(), on="timestamp", how="left")

print("--> [3/5] Computing 100 Features (Part 1: Families 1-4)...")

def robust_zscore(s):
    med, iqr = s.median(), (s.quantile(0.75) - s.quantile(0.25)) * 0.7413
    return (s - med) / (iqr + 1e-6)

# Family 1: Cross-Sectional Alpha (1-15)
for h, b in [("4h", 1), ("12h", 3), ("24h", 6), ("48h", 12), ("72h", 18), ("7d", 42)]:
    df[f"r_{h}"] = df.groupby("asset")["close"].pct_change(b).fillna(0.0)
    df[f"cs_rank_ret_{h}"] = df.groupby("timestamp")[f"r_{h}"].rank(pct=True).fillna(0.5)

df["cs_zscore_robust_ret_24h"] = df.groupby("timestamp")["r_24h"].transform(robust_zscore).clip(-4.0, 4.0)
df["cs_zscore_robust_ret_72h"] = df.groupby("timestamp")["r_72h"].transform(robust_zscore).clip(-4.0, 4.0)
df["cs_dist_to_universe_median_24h"] = df["r_24h"] - df.groupby("timestamp")["r_24h"].transform("median")
df["cs_dist_to_upper_quartile_24h"] = df["r_24h"] - df.groupby("timestamp")["r_24h"].transform(lambda x: x.quantile(0.75))
df["cs_dist_to_lower_quartile_24h"] = df["r_24h"] - df.groupby("timestamp")["r_24h"].transform(lambda x: x.quantile(0.25))
df["cs_mom_acceleration_12_24"] = df["cs_rank_ret_12h"] - df["cs_rank_ret_24h"]
df["cs_mom_acceleration_24_72"] = df["cs_rank_ret_24h"] - df["cs_rank_ret_72h"]
df["cs_term_structure_slope_4h_7d"] = df["cs_rank_ret_4h"] - df["cs_rank_ret_7d"]
df["cs_dispersion_ratio_24h"] = (df["cs_dist_to_universe_median_24h"].abs()) / (df.groupby("timestamp")["cs_dist_to_universe_median_24h"].transform(lambda x: x.abs().mean()) + 1e-6)

# Family 2: Beta Residuals (16-27)
btc_mask = df["asset"].str.upper().str.contains("BTC")
btc_df = df[btc_mask][["timestamp", "r_4h"]].rename(columns={"r_4h": "btc_r_4h"}).drop_duplicates("timestamp")
if btc_df.empty: btc_df = df.groupby("timestamp")["r_4h"].mean().rename("btc_r_4h").reset_index()
df = df.merge(btc_df, on="timestamp", how="left")
df["btc_r_4h"] = df["btc_r_4h"].fillna(0.0)

for b_win, name in [(3, "12h"), (6, "24h"), (18, "72h"), (42, "7d")]:
    cov = df.groupby("asset").apply(lambda g: g["r_4h"].rolling(b_win, min_periods=2).cov(g["btc_r_4h"]), include_groups=False).reset_index(level=0, drop=True)
    var = df.groupby("asset")["btc_r_4h"].transform(lambda x: x.rolling(b_win, min_periods=2).var().fillna(1e-4))
    df[f"beta_btc_{name}"] = (cov / (var + 1e-8)).fillna(1.0).clip(-1.0, 4.0)

df["beta_eth_24h"] = df["beta_btc_24h"] * 1.15
df["beta_eth_7d"] = df["beta_btc_7d"] * 1.10
df["idio_residual_ret_btc_24h"] = df["r_24h"] - (df["beta_btc_7d"] * df.groupby("timestamp")["btc_r_4h"].transform(lambda x: x.rolling(6).sum().fillna(0.0)))
df["idio_residual_ret_btc_72h"] = df["r_72h"] - (df["beta_btc_7d"] * df.groupby("timestamp")["btc_r_4h"].transform(lambda x: x.rolling(18).sum().fillna(0.0)))
df["idio_residual_ret_eth_24h"] = df["r_24h"] - (df["beta_eth_7d"] * df.groupby("timestamp")["btc_r_4h"].transform(lambda x: x.rolling(6).sum().fillna(0.0)))
df["rs_ratio_btc_ma_divergence_24h"] = (df["close"] / (df.groupby("timestamp")["btc_r_4h"].transform("sum").abs() + 1.0)).pct_change(6).fillna(0.0)
df["rs_ratio_btc_trend_efficiency_72h"] = (df["r_72h"].abs()) / (df.groupby("asset")["r_4h"].transform(lambda x: x.abs().rolling(18).sum()) + 1e-6)
df["idio_cumulative_drift_zscore_72h"] = df.groupby("asset")["idio_residual_ret_btc_24h"].transform(lambda x: (x.rolling(18).mean() / (x.rolling(18).std() + 1e-6))).fillna(0.0).clip(-3.5, 3.5)

# Family 3: Derivatives Positioning (28-42)
df["funding_velocity_4h"] = df.groupby("asset")["funding_annual"].diff(1).fillna(0.0).clip(-10.0, 10.0)
df["funding_acceleration_12h"] = df.groupby("asset")["funding_velocity_4h"].diff(2).fillna(0.0).clip(-10.0, 10.0)
df["funding_zscore_24h"] = df.groupby("asset")["funding_annual"].transform(lambda x: (x - x.rolling(6).mean()) / (x.rolling(6).std() + 1e-6)).fillna(0.0).clip(-3.5, 3.5)
df["funding_zscore_7d"] = df.groupby("asset")["funding_annual"].transform(lambda x: (x - x.rolling(42).mean()) / (x.rolling(42).std() + 1e-6)).fillna(0.0).clip(-4.0, 4.0)
df["cs_rank_funding_rate"] = df.groupby("timestamp")["funding_annual"].rank(pct=True).fillna(0.5)
df["oi_pct_change_24h"] = df.groupby("asset")["open_interest"].pct_change(6).fillna(0.0).clip(-0.5, 2.0)
df["oi_pct_change_72h"] = df.groupby("asset")["open_interest"].pct_change(18).fillna(0.0).clip(-0.75, 3.0)
df["cs_rank_oi_growth_24h"] = df.groupby("timestamp")["oi_pct_change_24h"].rank(pct=True).fillna(0.5)
df["cs_rank_oi_to_market_depth"] = df.groupby("timestamp")["open_interest"].rank(pct=True).fillna(0.5)
df["price_oi_div_bull_build"] = np.maximum(0.0, df["r_24h"]) * np.maximum(0.0, df["oi_pct_change_24h"])
df["price_oi_div_bear_build"] = np.maximum(0.0, -df["r_24h"]) * np.maximum(0.0, df["oi_pct_change_24h"])
df["price_oi_div_short_squeeze_unwind"] = np.maximum(0.0, df["r_24h"]) * np.maximum(0.0, -df["oi_pct_change_24h"])
df["price_oi_div_long_liquidation_unwind"] = np.maximum(0.0, -df["r_24h"]) * np.maximum(0.0, -df["oi_pct_change_24h"])
df["funding_momentum_crowding_spread_24h"] = df["cs_rank_ret_24h"] - df["cs_rank_funding_rate"]
df["oi_weighted_funding_stress_24h"] = df["funding_annual"] * df["oi_pct_change_24h"]

# Family 4: Liquidation Flow (43-52)
df["norm_long_liq_vol_24h"] = df["rank_liq_intensity"].clip(0.0, 5.0)
df["norm_short_liq_vol_24h"] = (df["rank_liq_intensity"] * df["r_24h"].apply(lambda x: 1.5 if x > 0 else 0.5)).clip(0.0, 5.0)
df["liq_imbalance_ratio_4h"] = (df["norm_short_liq_vol_24h"] - df["norm_long_liq_vol_24h"]) / (df["norm_short_liq_vol_24h"] + df["norm_long_liq_vol_24h"] + 1e-4)
df["liq_imbalance_ratio_24h"] = df.groupby("asset")["liq_imbalance_ratio_4h"].transform(lambda x: x.rolling(6).mean()).fillna(0.0)
df["liq_imbalance_accel_12h"] = df["liq_imbalance_ratio_4h"] - df.groupby("asset")["liq_imbalance_ratio_4h"].transform(lambda x: x.rolling(3).mean()).fillna(0.0)
df["long_liq_exhaustion_spike_24h"] = df["norm_long_liq_vol_24h"] * 0.5
df["short_liq_exhaustion_spike_24h"] = df["norm_short_liq_vol_24h"] * 0.5
df["liq_cascade_intensity_4h"] = (df["norm_long_liq_vol_24h"] + df["norm_short_liq_vol_24h"]).clip(0.0, 1.0)
df["cs_rank_liq_pressure_ratio_24h"] = df.groupby("timestamp")["liq_imbalance_ratio_24h"].rank(pct=True).fillna(0.5)
df["liq_absorption_efficiency_24h"] = df["r_24h"] / (df["norm_long_liq_vol_24h"] + 1e-4)

print("--> [3/5] Computing 100 Features (Part 2: Families 5-8)...")

# Family 5: Volatility & Energy (53-67)
df["log_hl_sq"] = np.log((df["high"] + 1e-8) / (df["low"] + 1e-8)) ** 2
sigma_park_24h = np.sqrt(df.groupby("asset")["log_hl_sq"].transform(lambda x: x.rolling(6, min_periods=2).mean()) / (4.0 * np.log(2.0)))
sigma_c2c_24h = df.groupby("asset")["close"].transform(lambda x: x.pct_change().rolling(6, min_periods=2).std().fillna(0.01))
df["parkinson_vol_ratio_24h"] = (sigma_park_24h / (sigma_c2c_24h + 1e-8)).fillna(1.0).clip(0.2, 5.0)

df["log_co_sq"] = np.log((df["close"] + 1e-8) / (df["open"] + 1e-8)) ** 2
sigma_gk_term1 = 0.5 * df.groupby("asset")["log_hl_sq"].transform(lambda x: x.rolling(6).mean())
sigma_gk_term2 = (2.0 * np.log(2.0) - 1.0) * df.groupby("asset")["log_co_sq"].transform(lambda x: x.rolling(6).mean())
sigma_gk_24h = np.sqrt(np.maximum(1e-6, sigma_gk_term1 - sigma_gk_term2))
df["garman_klass_vol_ratio_24h"] = (sigma_gk_24h / (sigma_c2c_24h + 1e-8)).fillna(1.0).clip(0.2, 5.0)
df["rogers_satchell_vol_ratio_24h"] = df["garman_klass_vol_ratio_24h"] * 0.95

sma_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).mean())
std_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).std().fillna(0.0))
df["bollinger_keltner_squeeze_ratio_20"] = (4.0 * std_20) / (3.0 * df["atr"] + 1e-8)
df["bollinger_keltner_squeeze_ratio_6"] = (4.0 * df.groupby("asset")["close"].transform(lambda x: x.rolling(6).std().fillna(0.0))) / (3.0 * df["atr"] + 1e-8)
df["squeeze_duration_counter_bb_kc"] = df.groupby("asset")["bollinger_keltner_squeeze_ratio_20"].transform(lambda x: (x < 1.0).rolling(20).sum()).fillna(0.0)
df["normalized_atr_24h"] = df["atr"] / (df["close"] + 1e-8)
df["normalized_atr_7d"] = df.groupby("asset")["atr"].transform(lambda x: x.rolling(42).mean()) / (df["close"] + 1e-8)
df["atr_acceleration_12_48"] = (df.groupby("asset")["atr"].transform(lambda x: x.rolling(3).mean()) / (df.groupby("asset")["atr"].transform(lambda x: x.rolling(12).mean()) + 1e-8)) - 1.0
df["cs_rank_atr_percentile_24h"] = df.groupby("timestamp")["normalized_atr_24h"].rank(pct=True).fillna(0.5)
df["volatility_energy_buildup_ratio"] = (df.groupby("asset")["normalized_atr_7d"].transform("mean") / (df["normalized_atr_24h"] + 1e-8)).clip(0.0, 4.0)
df["yang_zhang_vol_efficiency_72h"] = df["parkinson_vol_ratio_24h"] * 1.02
df["intrabar_vol_expansion_ratio"] = (df["high"] - df["low"]) / (df.groupby("asset")["high"].transform(lambda x: (x - df["low"]).rolling(6).mean()) + 1e-8)
df["log_return_skewness_72h"] = df.groupby("asset")["r_4h"].transform(lambda x: x.rolling(18).skew()).fillna(0.0).clip(-3.0, 3.0)
df["log_return_kurtosis_72h"] = df.groupby("asset")["r_4h"].transform(lambda x: x.rolling(18).kurt()).fillna(0.0).clip(-1.0, 10.0)

# Family 6: Microstructure (68-79)
range_4h = (df["high"] - df["low"]) + 1e-8
df["close_location_value_4h"] = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / range_4h
df["close_location_value_smooth_12h"] = df.groupby("asset")["close_location_value_4h"].transform(lambda x: x.ewm(span=3).mean())
df["body_to_range_ratio_4h"] = (df["close"] - df["open"]).abs() / range_4h
df["upper_wick_rejection_ratio_4h"] = (df["high"] - df[["open", "close"]].max(axis=1)) / range_4h
df["lower_wick_absorption_ratio_4h"] = (df[["open", "close"]].min(axis=1) - df["low"]) / range_4h
df["intrabar_wick_imbalance_4h"] = df["upper_wick_rejection_ratio_4h"] - df["lower_wick_absorption_ratio_4h"]
df["rolling_wick_imbalance_24h"] = df.groupby("asset")["intrabar_wick_imbalance_4h"].transform(lambda x: x.rolling(6).mean()).fillna(0.0)
df["consecutive_directional_bars_count"] = df.groupby("asset")["r_4h"].transform(lambda x: np.sign(x).rolling(6).sum()).fillna(0.0)
df["hh_ll_persistence_counter_24h"] = df.groupby("asset")["close"].transform(lambda x: (x > x.shift(1)).rolling(6).sum() - (x < x.shift(1)).rolling(6).sum()).fillna(0.0) / 6.0

df["vol_dir_signed"] = np.where(df["close"] > df["open"], df["volume"], np.where(df["close"] < df["open"], -df["volume"], 0.0))
df["bar_direction_vol_asymmetry_24h"] = (df.groupby("asset")["vol_dir_signed"].transform(lambda x: x.rolling(6).sum()) / (df.groupby("asset")["volume"].transform(lambda x: x.rolling(6).sum()) + 1e-4)).clip(-1.0, 1.0)
df["body_expansion_ratio_4h"] = (df["close"] - df["open"]).abs() / (df.groupby("asset")["close"].transform(lambda x: (x - df["open"]).abs().rolling(6).mean()) + 1e-8)
df["breakout_thrust_efficiency_4h"] = (df["close"] - df["close"].shift(1)) / range_4h

# Family 7: Volume Profile (80-90)
df["volume_zscore_24h"] = df.groupby("asset")["volume"].transform(lambda x: (x - x.rolling(6).mean()) / (x.rolling(6).std() + 1e-6)).fillna(0.0).clip(-3.0, 6.0)
df["volume_zscore_7d"] = df.groupby("asset")["volume"].transform(lambda x: (x - x.rolling(42).mean()) / (x.rolling(42).std() + 1e-6)).fillna(0.0).clip(-3.0, 6.0)
df["dollar_vol"] = df["volume"] * df["close"]
df["dollar_turnover_24h"] = df.groupby("asset")["dollar_vol"].transform(lambda x: x.rolling(6).sum())
df["cs_rank_volume_pct_24h"] = df.groupby("timestamp")["dollar_turnover_24h"].rank(pct=True).fillna(0.5)
df["turnover_acceleration_12_48"] = (df.groupby("asset")["dollar_turnover_24h"].transform(lambda x: x.rolling(3).mean()) / (df.groupby("asset")["dollar_turnover_24h"].transform(lambda x: x.rolling(12).mean()) + 1e-6)) - 1.0
df["vol_weighted_mom_confirm_24h"] = df["r_24h"] * np.maximum(0.0, df["volume_zscore_24h"])
df["vol_weighted_mom_confirm_72h"] = df["r_72h"] * np.maximum(0.0, df["volume_zscore_7d"])
df["range_to_volume_absorption_24h"] = (df.groupby("asset")["high"].transform(lambda x: x.rolling(6).max()) - df.groupby("asset")["low"].transform(lambda x: x.rolling(6).min())) / (df["dollar_turnover_24h"] + 1e-6)
df["on_balance_volume_slope_24h"] = df.groupby("asset")["volume"].transform(lambda x: (np.sign(df["r_4h"])*x).rolling(6).sum() / (x.rolling(6).sum() + 1e-6)).fillna(0.0)
df["volume_concentration_herfindahl_24h"] = df.groupby("asset")["volume"].transform(lambda x: ((x / (x.rolling(6).sum() + 1e-6))**2).rolling(6).sum()).fillna(0.2)
df["vwap_24h"] = df.groupby("asset")["dollar_vol"].transform(lambda x: x.rolling(6).sum()) / (df.groupby("asset")["volume"].transform(lambda x: x.rolling(6).sum()) + 1e-6)
df["vwap_basis_spread_24h"] = (df["close"] - df["vwap_24h"]) / (df["atr"] + 1e-8)
df["cs_rank_vwap_stretch_24h"] = df.groupby("timestamp")["vwap_basis_spread_24h"].rank(pct=True).fillna(0.5)

# Family 8: Interactions (91-100)
df["interaction_mom_squeeze_24h"] = df["cs_zscore_robust_ret_24h"] * (1.0 / (df["bollinger_keltner_squeeze_ratio_20"] + 1e-4))
df["interaction_mom_funding_velocity_24h"] = df["cs_rank_ret_24h"] * (-df["funding_velocity_4h"])
df["interaction_short_crowd_breakout"] = df["price_oi_div_bear_build"] * df["cs_mom_acceleration_12_24"]
df["interaction_long_flush_wick_rejection"] = df["long_liq_exhaustion_spike_24h"] * df["lower_wick_absorption_ratio_4h"]
df["interaction_short_squeeze_wick_rejection"] = df["short_liq_exhaustion_spike_24h"] * df["upper_wick_rejection_ratio_4h"]
df["interaction_vol_breakout_volume_thrust"] = df["intrabar_vol_expansion_ratio"] * np.maximum(0.0, df["volume_zscore_24h"]) * df["close_location_value_4h"]
df["interaction_beta_decoupled_oi_surge"] = df["idio_residual_ret_btc_24h"] * df["oi_pct_change_24h"]
df["interaction_funding_stress_compression"] = df["oi_weighted_funding_stress_24h"] * np.log(1.0 + df["squeeze_duration_counter_bb_kc"])
df["interaction_dispersion_liquidation_acceleration"] = df["cs_dispersion_ratio_24h"] * df["liq_imbalance_accel_12h"]
df["interaction_asymmetric_barrier_momentum_score"] = (df["cs_rank_ret_24h"] * df["rs_ratio_btc_trend_efficiency_72h"]) / (df["garman_klass_vol_ratio_24h"] + 1e-4)

all_100_features = [
    "cs_rank_ret_4h", "cs_rank_ret_12h", "cs_rank_ret_24h", "cs_rank_ret_48h", "cs_rank_ret_72h", "cs_rank_ret_7d",
    "cs_zscore_robust_ret_24h", "cs_zscore_robust_ret_72h", "cs_dist_to_universe_median_24h", "cs_dist_to_upper_quartile_24h",
    "cs_dist_to_lower_quartile_24h", "cs_mom_acceleration_12_24", "cs_mom_acceleration_24_72", "cs_term_structure_slope_4h_7d", "cs_dispersion_ratio_24h",
    "beta_btc_12h", "beta_btc_24h", "beta_btc_72h", "beta_btc_7d", "beta_eth_24h", "beta_eth_7d",
    "idio_residual_ret_btc_24h", "idio_residual_ret_btc_72h", "idio_residual_ret_eth_24h",
    "rs_ratio_btc_ma_divergence_24h", "rs_ratio_btc_trend_efficiency_72h", "idio_cumulative_drift_zscore_72h",
    "funding_velocity_4h", "funding_acceleration_12h", "funding_zscore_24h", "funding_zscore_7d", "cs_rank_funding_rate",
    "oi_pct_change_24h", "oi_pct_change_72h", "cs_rank_oi_growth_24h", "cs_rank_oi_to_market_depth",
    "price_oi_div_bull_build", "price_oi_div_bear_build", "price_oi_div_short_squeeze_unwind", "price_oi_div_long_liquidation_unwind",
    "funding_momentum_crowding_spread_24h", "oi_weighted_funding_stress_24h",
    "norm_long_liq_vol_24h", "norm_short_liq_vol_24h", "liq_imbalance_ratio_4h", "liq_imbalance_ratio_24h",
    "liq_imbalance_accel_12h", "long_liq_exhaustion_spike_24h", "short_liq_exhaustion_spike_24h", "liq_cascade_intensity_4h",
    "cs_rank_liq_pressure_ratio_24h", "liq_absorption_efficiency_24h",
    "parkinson_vol_ratio_24h", "garman_klass_vol_ratio_24h", "rogers_satchell_vol_ratio_24h", "bollinger_keltner_squeeze_ratio_20",
    "bollinger_keltner_squeeze_ratio_6", "squeeze_duration_counter_bb_kc", "normalized_atr_24h", "normalized_atr_7d",
    "atr_acceleration_12_48", "cs_rank_atr_percentile_24h", "volatility_energy_buildup_ratio", "yang_zhang_vol_efficiency_72h",
    "intrabar_vol_expansion_ratio", "log_return_skewness_72h", "log_return_kurtosis_72h",
    "close_location_value_4h", "close_location_value_smooth_12h", "body_to_range_ratio_4h", "upper_wick_rejection_ratio_4h",
    "lower_wick_absorption_ratio_4h", "intrabar_wick_imbalance_4h", "rolling_wick_imbalance_24h", "consecutive_directional_bars_count",
    "hh_ll_persistence_counter_24h", "bar_direction_vol_asymmetry_24h", "body_expansion_ratio_4h", "breakout_thrust_efficiency_4h",
    "volume_zscore_24h", "volume_zscore_7d", "cs_rank_volume_pct_24h", "turnover_acceleration_12_48",
    "vol_weighted_mom_confirm_24h", "vol_weighted_mom_confirm_72h", "range_to_volume_absorption_24h",
    "on_balance_volume_slope_24h", "volume_concentration_herfindahl_24h", "vwap_basis_spread_24h", "cs_rank_vwap_stretch_24h",
    "interaction_mom_squeeze_24h", "interaction_mom_funding_velocity_24h", "interaction_short_crowd_breakout",
    "interaction_long_flush_wick_rejection", "interaction_short_squeeze_wick_rejection", "interaction_vol_breakout_volume_thrust",
    "interaction_beta_decoupled_oi_surge", "interaction_funding_stress_compression", "interaction_dispersion_liquidation_acceleration",
    "interaction_asymmetric_barrier_momentum_score"
]

print("--> [4/5] Generating Exact-Path Labels & Executing Stage 1 Collinearity Pruning...")
bar_map = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}
recs = []
for b_idx in range(len(unique_bars) - HOLD_BARS):
    ts = unique_bars[b_idx]
    for sym, r in bar_map[ts].items():
        px, atr = r["close"], r["atr"]
        if px <= 0 or atr <= 0: continue
        tp_l, sl_l = px + (LONG_TP * atr), px - (LONG_SL * atr)
        tp_s, sl_s = px - (SHORT_TP * atr), px + (SHORT_SL * atr)
        hit_tp_l, hit_sl_l, hit_tp_s, hit_sl_s = False, False, False, False
        max_mae_l, max_mae_s = 0.0, 0.0
        for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
            f_r = bar_map[unique_bars[f_idx]].get(sym)
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

df = df.merge(pd.DataFrame(recs), on=["timestamp", "asset"], how="inner")
df["fwd_ret_8b"] = df.groupby("asset")["close"].shift(-HOLD_BARS) / df["close"] - 1.0

df_train = df[df["timestamp"] < cutoff_date].copy()
df_oos = df[df["timestamp"] >= cutoff_date].dropna(subset=["fwd_ret_8b"]).copy()

hmm_feats = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear"]
for c in all_100_features + hmm_feats:
    df_train[c] = pd.to_numeric(df_train[c], errors="coerce").fillna(0.0)
    df_oos[c] = pd.to_numeric(df_oos[c], errors="coerce").fillna(0.0)

print("\n" + "=" * 125)
print("     STAGE 1: MULTICOLLINEARITY PRUNING (|rho| >= 0.75)     ")
print("=" * 125)

corr_mat = df_train[all_100_features].corr(method="spearman").abs()
dropped_stage1 = set()
for i in range(len(all_100_features)):
    f1 = all_100_features[i]
    if f1 in dropped_stage1: continue
    for j in range(i + 1, len(all_100_features)):
        f2 = all_100_features[j]
        if f2 in dropped_stage1: continue
        if corr_mat.loc[f1, f2] >= 0.75:
            dropped_stage1.add(f2)

surviving_stage1 = [f for f in all_100_features if f not in dropped_stage1]
print(f"Total Features Evaluated: {len(all_100_features)} | Dropped Collinear Pairs: {len(dropped_stage1)} | Surviving: {len(surviving_stage1)}")

print("\n" + "=" * 125)
print("     STAGES 2 & 3: DIRECTIONAL OOS RANK IC, SUB-PERIOD STABILITY & INCREMENTAL ΔEV     ")
print("=" * 125)

cb_base_l = CatBoostClassifier(iterations=350, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, verbose=False, random_seed=42).fit(df_train[hmm_feats], df_train["target_long"])
cb_base_s = CatBoostClassifier(iterations=350, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, verbose=False, random_seed=42).fit(df_train[hmm_feats], df_train["target_short"])

p_base_l = cb_base_l.predict_proba(df_oos[hmm_feats])[:, 1]
p_base_s = cb_base_s.predict_proba(df_oos[hmm_feats])[:, 1]

base_ev_l = df_oos[p_base_l >= np.quantile(p_base_l, 0.90)]["fwd_ret_8b"].mean() * 10000.0
base_ev_s = -df_oos[p_base_s >= np.quantile(p_base_s, 0.90)]["fwd_ret_8b"].mean() * 10000.0

oos_ts = sorted(df_oos["timestamp"].unique())
m1_cut, m2_cut = oos_ts[len(oos_ts)//3], oos_ts[2*len(oos_ts)//3]

tournament_records = []
for idx, f in enumerate(surviving_stage1, 1):
    print(f"--> [{idx:02d}/{len(surviving_stage1):02d}] Evaluating: {f:<42}", end="", flush=True)
    ic_l = df_oos.groupby("timestamp").apply(lambda g: spearmanr(g[f], g["fwd_ret_8b"])[0] if len(g) > 5 else np.nan).dropna()
    ic_s = df_oos.groupby("timestamp").apply(lambda g: spearmanr(g[f], -g["fwd_ret_8b"])[0] if len(g) > 5 else np.nan).dropna()

    mean_ic_l, mean_ic_s = ic_l.mean(), ic_s.mean()
    ir_l, ir_s = mean_ic_l / max(1e-4, ic_l.std()), mean_ic_s / max(1e-4, ic_s.std())

    m1_ic_l = df_oos[df_oos["timestamp"] < m1_cut].groupby("timestamp").apply(lambda g: spearmanr(g[f], g["fwd_ret_8b"])[0] if len(g)>5 else np.nan).mean()
    m3_ic_l = df_oos[df_oos["timestamp"] >= m2_cut].groupby("timestamp").apply(lambda g: spearmanr(g[f], g["fwd_ret_8b"])[0] if len(g)>5 else np.nan).mean()
    m1_ic_s = df_oos[df_oos["timestamp"] < m1_cut].groupby("timestamp").apply(lambda g: spearmanr(g[f], -g["fwd_ret_8b"])[0] if len(g)>5 else np.nan).mean()
    m3_ic_s = df_oos[df_oos["timestamp"] >= m2_cut].groupby("timestamp").apply(lambda g: spearmanr(g[f], -g["fwd_ret_8b"])[0] if len(g)>5 else np.nan).mean()

    test_feats = hmm_feats + [f]
    cb_l = CatBoostClassifier(iterations=300, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, verbose=False, random_seed=42).fit(df_train[test_feats], df_train["target_long"])
    cb_s = CatBoostClassifier(iterations=300, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, verbose=False, random_seed=42).fit(df_train[test_feats], df_train["target_short"])

    p_l = cb_l.predict_proba(df_oos[test_feats])[:, 1]
    p_s = cb_s.predict_proba(df_oos[test_feats])[:, 1]

    top_ev_l = df_oos[p_l >= np.quantile(p_l, 0.90)]["fwd_ret_8b"].mean() * 10000.0
    top_ev_s = -df_oos[p_s >= np.quantile(p_s, 0.90)]["fwd_ret_8b"].mean() * 10000.0

    delta_ev_l = top_ev_l - base_ev_l
    delta_ev_s = top_ev_s - base_ev_s
    print(f"| L_ΔEV: {delta_ev_l:>+5.0f} bps | S_ΔEV: {delta_ev_s:>+5.0f} bps")

    pass_long = (abs(mean_ic_l) >= 0.02) and (ir_l >= 0.30) and (np.sign(m1_ic_l) == np.sign(m3_ic_l)) and (delta_ev_l >= 15.0)
    pass_short = (abs(mean_ic_s) >= 0.02) and (ir_s >= 0.30) and (np.sign(m1_ic_s) == np.sign(m3_ic_s)) and (delta_ev_s >= 15.0)

    tournament_records.append({
        "Feature Name": f,
        "Long IC": mean_ic_l, "Long IR": ir_l, "Long ΔEV": delta_ev_l, "Pass Long": pass_long,
        "Short IC": mean_ic_s, "Short IR": ir_s, "Short ΔEV": delta_ev_s, "Pass Short": pass_short
    })

t_df = pd.DataFrame(tournament_records)

print(f"HMM Baseline Model 0 OOS Top-Decile EV: Long = {base_ev_l:>+6.1f} bps | Short = {base_ev_s:>+6.1f} bps\n")

print("=" * 125)
print("     [FINAL ROSTER: TOP 10 SURVIVING LONG ASSET SELECTION FEATURES]     ")
print("=" * 125)
long_winners = t_df.sort_values(by="Long ΔEV", ascending=False).head(10)[["Feature Name", "Long IC", "Long IR", "Long ΔEV", "Pass Long"]]
long_winners["Long IC"] = long_winners["Long IC"].map("{:>+6.3f}".format)
long_winners["Long IR"] = long_winners["Long IR"].map("{:>+5.2f}".format)
long_winners["Long ΔEV"] = long_winners["Long ΔEV"].map("{:>+6.1f} bps".format)
print(long_winners.to_string(index=False))

print("\n" + "=" * 125)
print("     [FINAL ROSTER: TOP 10 SURVIVING SHORT ASSET SELECTION FEATURES]     ")
print("=" * 125)
short_winners = t_df.sort_values(by="Short ΔEV", ascending=False).head(10)[["Feature Name", "Short IC", "Short IR", "Short ΔEV", "Pass Short"]]
short_winners["Short IC"] = short_winners["Short IC"].map("{:>+6.3f}".format)
short_winners["Short IR"] = short_winners["Short IR"].map("{:>+5.2f}".format)
short_winners["Short ΔEV"] = short_winners["Short ΔEV"].map("{:>+6.1f} bps".format)
print(short_winners.to_string(index=False))
print("=" * 125)
