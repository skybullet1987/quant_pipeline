import os
import warnings
import joblib
import numpy as np
import pandas as pd
from google.cloud import bigquery

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

# --- SIMULATION PARAMETERS ---
INITIAL_CAPITAL = 1000.0   # $1,000 USD Starting Capital
ROUNDTRIP_FEE = 0.0014     # 0.14% Total Friction (Taker Fee + Slippage)
KELLY_FRACTION = 0.25      # Quarter-Kelly Sizing for Conservative Growth
MAX_EQUITY_RISK = 0.10     # Max 10% Margin per Position
ENTRY_THRESHOLD = 0.58     # Min Calibrated P(TP) to trigger trade

def load_backtest_data():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*,
            p.exit_time,
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
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exit_reason', 'exit_time', 'tfm_residual_24h']).reset_index(drop=True)

def calculate_entropy(probs):
    probs = np.clip(probs, 1e-12, 1.0)
    return -np.sum(probs * np.log(probs), axis=1)

def main():
    print("=================================================================")
    print(f"   BACKTESTING PRODUCTION BUNDLE WITH ${INITIAL_CAPITAL:,.2f} CAPITAL   ")
    print("=================================================================")

    # 1. Load Production Models & Metadata
    calibrated_model = joblib.load(f"{MODEL_DIR}/catboost_calibrated_production.pkl")
    hmm_raw = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl")
    canonical_order = joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
    all_features = joblib.load(f"{MODEL_DIR}/feature_names.pkl")
    cat_cols = joblib.load(f"{MODEL_DIR}/cat_cols.pkl")

    # 2. Load Market Data & Build OOS Dataset
    df = load_backtest_data()
    df['raw_atr_pct'] = df['atr_20'] / df['close']
    df = df.sort_values(['ticker', 'timestamp'])
    df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)
    df = df.dropna(subset=['return_7d']).copy()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)

    # Filter out-of-sample (Validation) subset (Last 15% of historical timeline)
    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    val_ts = timestamps[split_idx:]
    
    df_val = df[df['timestamp'].isin(val_ts)].copy().reset_index(drop=True)

    # 3. Generate HMM Regimes for Validation Matrix
    macro_val = df_val.groupby('timestamp').agg(
        macro_breadth=('market_breadth_sma20', 'first'),
        macro_volatility=('raw_atr_pct', 'median'),
        macro_momentum=('return_7d', 'median'),
        macro_surprise=('tfm_residual_24h', 'median')
    ).sort_index()

    hmm_features = ['macro_breadth', 'macro_volatility', 'macro_momentum', 'macro_surprise']
    raw_probs_val = hmm_raw.predict_proba(macro_val[hmm_features].values)
    canonical_probs_val = raw_probs_val[:, canonical_order]

    macro_val['hmm_p_chop'] = canonical_probs_val[:, 0]
    macro_val['hmm_p_trend'] = canonical_probs_val[:, 1]
    macro_val['hmm_p_cascade'] = canonical_probs_val[:, 2]
    macro_val['hmm_entropy'] = calculate_entropy(canonical_probs_val)
    macro_val['hmm_regime'] = np.argmax(canonical_probs_val, axis=1).astype(str)

    df_val = pd.merge(
        df_val, 
        macro_val[['hmm_p_chop', 'hmm_p_trend', 'hmm_p_cascade', 'hmm_entropy', 'hmm_regime']], 
        left_on='timestamp', 
        right_index=True, 
        how='left'
    )

    # 4. Predict Calibrated Probabilities
    X_val = df_val[all_features].copy()
    for col in cat_cols:
        X_val[col] = X_val[col].astype('category').cat.codes

    df_val['p_tp'] = calibrated_model.predict_proba(X_val)[:, 1]

    # 5. Event-Driven Backtest Simulation Loop
    df_val = df_val.sort_values('timestamp').reset_index(drop=True)
    
    capital = INITIAL_CAPITAL
    equity_curve = [capital]
    trade_logs = []

    for idx, row in df_val.iterrows():
        p = row['p_tp']
        
        # Signal Filter: Trigger entry if P(TP) > ENTRY_THRESHOLD
        if p >= ENTRY_THRESHOLD:
            b = 2.0  # Payoff ratio (2:1 TP/SL)
            q = 1.0 - p
            
            # Kelly Fraction calculation
            raw_kelly = max(0.0, (b * p - q) / b)
            
            # Regime-adjusted sizing multiplier
            chop_penalty = 1.0 - row['hmm_p_chop']
            entropy_penalty = 1.0 - (row['hmm_entropy'] / 1.0986)  # Normalized by ln(3)
            
            # Final Position Sizing
            adj_size_fraction = raw_kelly * KELLY_FRACTION * chop_penalty * entropy_penalty
            adj_size_fraction = min(adj_size_fraction, MAX_EQUITY_RISK)
            
            if adj_size_fraction <= 0.005:
                continue  # Skip negligible trade sizes
                
            position_size = capital * adj_size_fraction
            
            # Determine Trade Result
            if row['exit_reason'] == 'TP_HIT':
                gross_pnl = position_size * (b * 0.02)  # Simulated +2% TP
            elif row['exit_reason'] == 'SL_HIT':
                gross_pnl = -position_size * 0.01      # Simulated -1% SL
            else:
                gross_pnl = 0.0                        # Time exit neutral

            # Subtract roundtrip friction (Fees + Slippage)
            friction = position_size * ROUNDTRIP_FEE
            net_pnl = gross_pnl - friction
            
            capital += net_pnl
            equity_curve.append(capital)
            
            trade_logs.append({
                'timestamp': row['timestamp'],
                'ticker': row['ticker'],
                'p_tp': p,
                'p_chop': row['hmm_p_chop'],
                'size_usd': position_size,
                'exit_reason': row['exit_reason'],
                'net_pnl': net_pnl,
                'capital_after': capital
            })

    # 6. Calculate Summary Metrics
    trades_df = pd.DataFrame(trade_logs)
    if trades_df.empty:
        print("[WARNING] No trades executed above the signal threshold.")
        return

    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['net_pnl'] > 0])
    win_rate = (winning_trades / total_trades) * 100.0
    
    total_return_pct = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100.0
    
    # Calculate Max Drawdown
    equity_series = pd.Series(equity_curve)
    peak = equity_series.cummax()
    drawdown = (equity_series - peak) / peak
    max_drawdown_pct = drawdown.min() * 100.0
    
    # Profit Factor
    gross_gains = trades_df[trades_df['net_pnl'] > 0]['net_pnl'].sum()
    gross_losses = abs(trades_df[trades_df['net_pnl'] < 0]['net_pnl'].sum())
    profit_factor = gross_gains / gross_losses if gross_losses > 0 else np.nan

    print("\n=================================================================")
    print("               OUT-OF-SAMPLE BACKTEST RESULTS                    ")
    print("=================================================================")
    print(f" Initial Starting Capital : ${INITIAL_CAPITAL:,.2f}")
    print(f" Final Portfolio Value    : ${capital:,.2f}")
    print(f" Net Total Return (%)     : {total_return_pct:+.2f}%")
    print(f" Total Trades Executed    : {total_trades}")
    print(f" Win Rate (%)             : {win_rate:.2f}%")
    print(f" Profit Factor            : {profit_factor:.2f}")
    print(f" Maximum Drawdown (%)     : {max_drawdown_pct:.2f}%")
    print("=================================================================\n")

if __name__ == "__main__":
    main()
