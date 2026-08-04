import joblib
import numpy as np
import pandas as pd
from google.cloud import bigquery
import warnings
warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

# --- DEGEN SIMULATION PARAMETERS ---
INITIAL_CAPITAL = 1000.0
LEVERAGE = 10.0           # 10x Leverage on Hyperliquid
MARGIN_PER_TRADE = 0.30   # 30% Margin per Trade (3x Effective Account Risk!)
ROUNDTRIP_FEE = 0.0020    # 0.20% Friction (Hyperliquid Taker Fee + High Slippage)
ENTRY_THRESHOLD = 0.58

def load_data():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*, 
            p.exit_reason, 
            t.tfm_ret_24h, t.tfm_ret_72h, t.tfm_slope, t.tfm_uncertainty, t.tfm_residual_24h, t.tfm_conviction_delta
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    return df.dropna(subset=['exit_reason', 'tfm_residual_24h']).reset_index(drop=True)

def main():
    calibrated_model = joblib.load(f"{MODEL_DIR}/catboost_calibrated_production.pkl")
    hmm_raw = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl")
    canonical_order = joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
    all_features = joblib.load(f"{MODEL_DIR}/feature_names.pkl")
    cat_cols = joblib.load(f"{MODEL_DIR}/cat_cols.pkl")

    df = load_data()
    df['raw_atr_pct'] = df['atr_20'] / df['close']
    df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)
    df = df.dropna(subset=['return_7d'])
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)

    # OOS validation slice
    timestamps = pd.to_datetime(df['timestamp']).sort_values().unique()
    df_val = df[df['timestamp'] >= timestamps[int(len(timestamps) * 0.85)]].copy().reset_index(drop=True)

    # Macro HMM
    macro_val = df_val.groupby('timestamp').agg(
        macro_breadth=('market_breadth_sma20', 'first'),
        macro_volatility=('raw_atr_pct', 'median'),
        macro_momentum=('return_7d', 'median'),
        macro_surprise=('tfm_residual_24h', 'median')
    ).sort_index()

    raw_probs = hmm_raw.predict_proba(macro_val[['macro_breadth', 'macro_volatility', 'macro_momentum', 'macro_surprise']].values)
    can_probs = raw_probs[:, canonical_order]
    
    macro_val['hmm_p_chop'] = can_probs[:, 0]
    macro_val['hmm_p_trend'] = can_probs[:, 1]
    macro_val['hmm_p_cascade'] = can_probs[:, 2]
    probs_clip = np.clip(can_probs, 1e-12, 1.0)
    macro_val['hmm_entropy'] = -np.sum(probs_clip * np.log(probs_clip), axis=1)
    macro_val['hmm_regime'] = np.argmax(can_probs, axis=1).astype(str)

    df_val = pd.merge(df_val, macro_val, left_on='timestamp', right_index=True, how='left')

    X_val = df_val[all_features].copy()
    for col in cat_cols:
        X_val[col] = X_val[col].astype('category').cat.codes

    df_val['p_tp'] = calibrated_model.predict_proba(X_val)[:, 1]
    df_val = df_val.sort_values('timestamp').reset_index(drop=True)

    capital = INITIAL_CAPITAL
    peak_capital = capital
    max_dd = 0.0
    trades = 0
    wins = 0

    for idx, row in df_val.iterrows():
        if capital <= 10.0:
            print("\n[CRITICAL] ACCOUNT LIQUIDATED. Capital dropped below $10. Backtest terminated early.")
            break

        p = row['p_tp']
        if p >= ENTRY_THRESHOLD:
            trades += 1
            # 30% of account * 10x leverage = 300% notional exposure
            notional_position = capital * MARGIN_PER_TRADE * LEVERAGE
            
            # Outcome at 10x leverage
            if row['exit_reason'] == 'TP_HIT':
                gross_pnl = notional_position * 0.02  # +2% target
                wins += 1
            elif row['exit_reason'] == 'SL_HIT':
                gross_pnl = -notional_position * 0.01 # -1% target
            else:
                gross_pnl = 0.0

            friction = notional_position * ROUNDTRIP_FEE
            capital += (gross_pnl - friction)
            
            if capital > peak_capital:
                peak_capital = capital
            dd = (capital - peak_capital) / peak_capital
            if dd < max_dd:
                max_dd = dd

    print("\n=========================================================")
    print("           10X LEVERAGE / HIGH-RISK BACKTEST RESULTS    ")
    print("=========================================================")
    print(f" Final Capital  : ${capital:,.2f}")
    print(f" Total Trades   : {trades}")
    print(f" Win Rate       : {(wins/trades)*100:.2f}%" if trades > 0 else "N/A")
    print(f" Max Drawdown   : {max_dd*100:.2f}%")
    print("=========================================================\n")

if __name__ == "__main__":
    main()
