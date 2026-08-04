import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from sklearn.metrics import brier_score_loss, log_loss
import warnings

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
CAT_COLS = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend', 'market_session', 'btc_above_sma50', 'hmm_regime']
FEATURE_COLS = [
    'market_breadth_sma20', 'top_breakout_breadth', 'pos_bar_count_6p',
    'candle_body_pct', 'candle_upper_wick_pct', 'candle_lower_wick_pct',
    'rank_eth_btc_spread_20p', 'rank_btc_dominance_spread',
    'rank_gk_vol_20p', 'rank_vol_term_structure', 'rank_gk_vol_zscore', 'rank_vol_compression_ratio',
    'rank_mom_24h', 'rank_mom_7d', 'rank_mom_accel_24h', 'rank_mom_ratio_24h_7d',
    'rank_dist_to_120p_high', 'rank_relative_vol_120p', 'rank_rolling_sharpe_20p', 'rank_atr_pct_20'
]

def load_data():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT f.*, p.exit_time, p.exit_reason, p.exact_gross_return
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exit_reason', 'exit_time']).sort_values('timestamp').reset_index(drop=True)

print("Ingesting Data for Architecture Audit...")
df = load_data()
df['raw_atr_pct'] = df['atr_20'] / df['close']
df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)
df = df.dropna(subset=['return_7d']).reset_index(drop=True)

df['target_long'] = (df['exit_reason'] == 'TP_HIT').astype(int)
df['target_short'] = (df['exit_reason'] == 'SL_HIT').astype(int)

# --- TEST 1: HMM REGIME STABILITY & DURATION ---
print("\n" + "="*70)
print("  AUDIT 1: HMM REGIME STABILITY & TRANSITION DYNAMICS")
print("="*70)

macro = df.groupby('timestamp').agg(
    macro_breadth=('market_breadth_sma20', 'first'),
    macro_volatility=('raw_atr_pct', 'median'),
    macro_momentum=('return_7d', 'median')
).sort_index()

hmm_features = ['macro_breadth', 'macro_volatility', 'macro_momentum']
hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
macro['regime'] = hmm.fit_predict(macro[hmm_features].values)

# Calculate Regime Durations
macro['regime_change'] = (macro['regime'] != macro['regime'].shift(1)).astype(int)
macro['regime_group'] = macro['regime_change'].cumsum()
durations = macro.groupby('regime_group').agg(regime=('regime', 'first'), duration_bars=('regime', 'count'))

print("Transition Matrix:")
print(pd.DataFrame(hmm.transmat_, index=['State 0', 'State 1', 'State 2'], columns=['State 0', 'State 1', 'State 2']).round(3))

print("\nAverage Regime Duration:")
for r in [0, 1, 2]:
    avg_dur = durations[durations['regime'] == r]['duration_bars'].mean() * 4 # 4 hours per bar
    print(f"  Regime {r}: {avg_dur:.1f} hours average persistence")

# Merge Regime back to main DF
df = pd.merge(df, macro[['regime']], left_on='timestamp', right_index=True, how='left')
df['hmm_regime'] = df['regime'].astype(str)

for col in CAT_COLS:
    df[col] = df[col].astype(str)

# --- TEST 2: GLOBAL MODEL VS. EXPERT STACK ---
print("\n" + "="*70)
print("  AUDIT 2: GLOBAL CATBOOST VS. ASYMMETRIC SHORT MODEL CALIBRATION")
print("="*70)

split_idx = int(len(df) * 0.80)
train_df = df.iloc[:split_idx].copy()
val_df = df.iloc[split_idx + 18:].copy()

# A. Global Long Model
global_long = CatBoostClassifier(iterations=600, learning_rate=0.05, depth=5, auto_class_weights='Balanced', verbose=0, random_seed=42)
global_long.fit(train_df[FEATURE_COLS + CAT_COLS], train_df['target_long'], cat_features=CAT_COLS)
val_df['prob_global_long'] = global_long.predict_proba(val_df[FEATURE_COLS + CAT_COLS])[:, 1]

# B. Global Short Model
global_short = CatBoostClassifier(iterations=600, learning_rate=0.05, depth=5, auto_class_weights='Balanced', verbose=0, random_seed=42)
global_short.fit(train_df[FEATURE_COLS + CAT_COLS], train_df['target_short'], cat_features=CAT_COLS)
val_df['prob_global_short'] = global_short.predict_proba(val_df[FEATURE_COLS + CAT_COLS])[:, 1]

brier_long = brier_score_loss(val_df['target_long'], val_df['prob_global_long'])
logloss_long = log_loss(val_df['target_long'], val_df['prob_global_long'])

brier_short = brier_score_loss(val_df['target_short'], val_df['prob_global_short'])
logloss_short = log_loss(val_df['target_short'], val_df['prob_global_short'])

print(f"Global LONG Model  -> Brier Score: {brier_long:.4f} | Log Loss: {logloss_long:.4f}")
print(f"Global SHORT Model -> Brier Score: {brier_short:.4f} | Log Loss: {logloss_short:.4f}")

# --- TEST 3: ASYMMETRY CHECK (TOP 10% CONFIDENCE TRADES) ---
print("\n" + "="*70)
print("  AUDIT 3: TOP 10% CONFIDENCE REALIZED WIN RATE (LONG VS SHORT)")
print("="*70)

top_10_long = val_df[val_df['prob_global_long'] >= val_df['prob_global_long'].quantile(0.90)]
top_10_short = val_df[val_df['prob_global_short'] >= val_df['prob_global_short'].quantile(0.90)]

print(f"Top 10% Long  Confidence -> Trades: {len(top_10_long)} | Realized Win Rate: {top_10_long['target_long'].mean()*100:.2f}%")
print(f"Top 10% Short Confidence -> Trades: {len(top_10_short)} | Realized Win Rate: {top_10_short['target_short'].mean()*100:.2f}%")

