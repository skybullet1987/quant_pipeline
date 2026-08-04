import optuna
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
import warnings

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

PROJECT_ID = "parnasa-498503"
PURGE_BARS = 18

# DEX Fees (0.035% Taker, 0.00% Maker, 0.02% Slippage)
WIN_FRICTION = 0.00035 + 0.0002 + 0.0000
LOSS_FRICTION = 0.00035 + 0.0002 + 0.00035 + 0.0002

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
        SELECT 
            f.*,
            p.exit_time,
            p.exit_reason,
            p.exact_gross_return
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exit_reason', 'exit_time']).sort_values('timestamp').reset_index(drop=True)

print("Ingesting BigQuery 4H Features...")
df_raw = load_data()
df_raw['raw_atr_pct'] = df_raw['atr_20'] / df_raw['close']
df_raw['return_7d'] = df_raw.groupby('ticker')['close'].pct_change(42)
df_raw = df_raw.dropna(subset=['return_7d']).reset_index(drop=True)

# Define Targets
df_raw['target_long'] = (df_raw['exit_reason'] == 'TP_HIT').astype(int)
df_raw['target_short'] = (df_raw['exit_reason'] == 'SL_HIT').astype(int)

# 80/20 Time-Series Train/Val Split
split_idx = int(len(df_raw) * 0.80)
train_df = df_raw.iloc[:split_idx].copy()
val_df = df_raw.iloc[split_idx + PURGE_BARS:].copy()

# Train Time-Series Macro HMM
macro_train = train_df.groupby('timestamp').agg(
    macro_breadth=('market_breadth_sma20', 'first'),
    macro_volatility=('raw_atr_pct', 'median'),
    macro_momentum=('return_7d', 'median')
).sort_index()

hmm_features = ['macro_breadth', 'macro_volatility', 'macro_momentum']
hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
hmm.fit(macro_train[hmm_features].values)

train_df = pd.merge(train_df, macro_train, left_on='timestamp', right_index=True, how='left')
train_df['hmm_regime'] = hmm.predict(train_df[hmm_features].values).astype(str)

macro_val = val_df.groupby('timestamp').agg(
    macro_breadth=('market_breadth_sma20', 'first'),
    macro_volatility=('raw_atr_pct', 'median'),
    macro_momentum=('return_7d', 'median')
).sort_index()
val_df = pd.merge(val_df, macro_val, left_on='timestamp', right_index=True, how='left')
val_df['hmm_regime'] = hmm.predict(val_df[hmm_features].values).astype(str)

for col in CAT_COLS:
    train_df[col] = train_df[col].astype(str)
    val_df[col] = val_df[col].astype(str)

def objective(trial):
    params = {
        'iterations': trial.suggest_int('iterations', 400, 1200, step=100),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.10, log=True),
        'depth': trial.suggest_int('depth', 3, 7),
        'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1.0, 10.0),
        'random_strength': trial.suggest_float('random_strength', 1.0, 10.0),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'auto_class_weights': 'Balanced',
        'verbose': 0,
        'random_seed': 42
    }

    # Identify Regime Models
    # Bull Regime (0) -> Train Long Model
    # Bear Regime (2) -> Train Short Model
    # Neutral Regime (1) -> Train Long Model
    
    val_df['long_prob'] = 0.0
    val_df['short_prob'] = 0.0

    for regime, direction in [('0', 'LONG'), ('1', 'LONG'), ('2', 'SHORT')]:
        tr_sub = train_df[train_df['hmm_regime'] == regime]
        val_sub = val_df[val_df['hmm_regime'] == regime]
        
        if len(tr_sub) < 500 or len(val_sub) == 0:
            continue
            
        target_col = 'target_long' if direction == 'LONG' else 'target_short'
        
        model = CatBoostClassifier(**params)
        model.fit(tr_sub[FEATURE_COLS + CAT_COLS], tr_sub[target_col], cat_features=CAT_COLS)
        
        probs = model.predict_proba(val_sub[FEATURE_COLS + CAT_COLS])[:, 1]
        if direction == 'LONG':
            val_df.loc[val_sub.index, 'long_prob'] = probs
        else:
            val_df.loc[val_sub.index, 'short_prob'] = probs

    # Evaluate Validation Performance
    val_df['raw_atr_pct'] = val_df['atr_20'] / val_df['close']
    
    # Long Signals
    long_signals = val_df[val_df['long_prob'] > 0.55].copy()
    long_signals['net_ret'] = np.where(
        long_signals['target_long'] == 1,
        (1.50 * long_signals['raw_atr_pct']) - WIN_FRICTION,
        (-1.50 * long_signals['raw_atr_pct']) - LOSS_FRICTION
    )
    
    # Short Signals
    short_signals = val_df[val_df['short_prob'] > 0.55].copy()
    short_signals['net_ret'] = np.where(
        short_signals['target_short'] == 1,
        (1.50 * short_signals['raw_atr_pct']) - WIN_FRICTION,
        (-1.50 * short_signals['raw_atr_pct']) - LOSS_FRICTION
    )

    all_trades = pd.concat([long_signals, short_signals])
    if len(all_trades) < 50:
        return -999.0  # Penalty for too few trades

    win_rate = (all_trades['net_ret'] > 0).mean()
    avg_ret = all_trades['net_ret'].mean()
    std_ret = all_trades['net_ret'].std() + 1e-6
    
    sharpe = (avg_ret / std_ret) * np.sqrt(len(all_trades))
    
    # Return composite objective (Sharpe + Win Rate boost)
    return sharpe + (win_rate * 10)

print("\nStarting Optuna Hyperparameter Optimization for 4H Long/Short...")
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=30, show_progress_bar=True)

print("\n========================================================")
print("   OPTUNA DUAL LONG/SHORT RESULTS")
print("========================================================")
print(f"Best Trial Objective Value: {study.best_value:.4f}")
print("Best Parameters:")
for k, v in study.best_params.items():
    print(f"  {k}: {v}")

