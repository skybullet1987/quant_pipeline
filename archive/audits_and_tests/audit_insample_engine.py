import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
import joblib
import warnings
import os

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

WIN_FRICTION = 0.0047  
LOSS_FRICTION = 0.0062 

CAT_COLS_BASE = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend', 'market_session', 'btc_above_sma50']
FEATURE_COLS_NUM = [
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
        SELECT f.*, p.exit_time, p.exit_reason, p.exact_gross_return, p.minutes_in_trade, p.entry_price, p.target_price_1_5_atr, p.stop_loss_1_5_atr
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exact_gross_return', 'exit_time', 'minutes_in_trade']).copy()

def main():
    WIN_FRICTION = 0.0047
    LOSS_FRICTION = 0.0062
    print("1. Ingesting Matrix and Isolating OOS Test Block...")
    df = load_data()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].copy().reset_index(drop=True)
    df['exact_gross_return'] = df['exact_gross_return'].astype(float)
    df['minutes_in_trade'] = df['minutes_in_trade'].astype(float)

    max_minutes = df['minutes_in_trade'].max()
    purge_bars = int(np.ceil(max_minutes / 240.0))

    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    test_ts = timestamps[:split_idx]
    df_test = df[df['timestamp'].isin(test_ts)].copy().reset_index(drop=True)

    print("2. Loading HMM Macro Filter...")
    hmm_model = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl")
    hmm_features = ['rank_gk_vol_zscore', 'rank_mom_7d', 'market_breadth_sma20']
    df_test['hmm_regime'] = hmm_model.predict(df_test[hmm_features].values).astype(str)

    all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
    all_features = FEATURE_COLS_NUM + all_cat_cols
    for col in all_cat_cols: df_test[col] = df_test[col].astype(str)

    print("3. Generating Primary Expert Predictions...")
    df_test['primary_prob'] = 0.0
    for regime in df_test['hmm_regime'].unique():
        model_path = f"{MODEL_DIR}/regime_{regime}_expert.cbm"
        if os.path.exists(model_path):
            expert = CatBoostClassifier().load_model(model_path)
            regime_idx = df_test[df_test['hmm_regime'] == regime].index
            if len(regime_idx) > 0:
                df_test.loc[regime_idx, 'primary_prob'] = expert.predict_proba(df_test.loc[regime_idx, all_features])[:, 1]

    print("4. Applying Meta-Labeler & Isotonic Calibration...")
    test_signals = df_test[df_test['primary_prob'] > 0.45].copy()
    
    meta_model = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler.cbm")
    calibrator = joblib.load(f"{MODEL_DIR}/meta_calibrator.pkl")
    
    meta_features = FEATURE_COLS_NUM + ['primary_prob']
    raw_probs = meta_model.predict_proba(test_signals[meta_features])[:, 1]
    
    # Map raw scores to true calibrated probabilities
    test_signals['calibrated_prob'] = calibrator.predict(raw_probs)

    print("5. Executing Production Kelly Simulator (Quarter-Kelly + Hard Caps)...")
    df_test['net_ret'] = np.where(
        df_test['exit_reason'] == 'TP_HIT',
        df_test['exact_gross_return'] - WIN_FRICTION,
        df_test['exact_gross_return'] - LOSS_FRICTION
    )

    all_timestamps = sorted(df_test['timestamp'].unique())
    starting_capital = 10000.0
    realized_capital = starting_capital
    available_capital = starting_capital
    
    open_positions = []
    portfolio_history = []
    trade_log = []
    
    MAX_CONCURRENT_POSITIONS = 5
    KELLY_FRACTION = 0.25 
    MAX_RISK_PER_TRADE = 0.05 
    
    for ts in all_timestamps:
        still_open = []
        for pos in open_positions:
            if ts >= pos['exit_time']:
                profit = pos['investment'] * pos['net_ret']
                realized_capital += profit
                available_capital += (pos['investment'] + profit)
                trade_log.append({'profit': profit, 'net_ret': pos['net_ret'], 'hmm_regime': pos['hmm_regime']})
            else:
                still_open.append(pos)
        open_positions = still_open

        if ts.hour == 0:
            mtm_unrealized = sum([(pos['investment'] * pos['net_ret'] * min(((ts - pos['entry_time']).total_seconds() / 60.0) / max(pos['minutes_in_trade'], 1), 1.0)) for pos in open_positions])
            mtm_total_equity = realized_capital + mtm_unrealized
            portfolio_history.append({'date': ts.date(), 'mtm_equity': mtm_total_equity})

        if not test_signals.empty:
            current_signals = test_signals[test_signals['timestamp'] == ts].sort_values('calibrated_prob', ascending=False)
            for _, row in current_signals.iterrows():
                p = row['calibrated_prob']
                
                # Dynamic EV Calculation
                # Reconstruct gross targets based on the 3.0 vs 1.5 ATR math
                gross_win_pct = (row['target_price_1_5_atr'] - row['entry_price']) / row['entry_price']
                gross_loss_pct = (row['entry_price'] - row['stop_loss_1_5_atr']) / row['entry_price']
                
                net_win_pct = gross_win_pct - WIN_FRICTION
                net_loss_pct = gross_loss_pct + LOSS_FRICTION
                
                # Calculate Expected Value
                expected_value = (p * net_win_pct) - ((1 - p) * net_loss_pct)
                
                # Only execute if mathematically profitable
                if expected_value > 0 and p > 0.55 and len(open_positions) < MAX_CONCURRENT_POSITIONS:
                    # Calculate true dynamic payoff ratio for Kelly sizing
                    dynamic_payoff_ratio = net_win_pct / net_loss_pct
                    kelly_f = p - ((1 - p) / dynamic_payoff_ratio)
                    trade_pct = kelly_f * KELLY_FRACTION
                    trade_pct = max(min(trade_pct, MAX_RISK_PER_TRADE), 0.01) 
                    
                    trade_size = realized_capital * trade_pct
                    if available_capital >= trade_size:
                        available_capital -= trade_size
                        open_positions.append({
                            'entry_time': ts, 'exit_time': row['exit_time'],
                            'investment': trade_size, 'net_ret': df_test.loc[row.name, 'net_ret'],
                            'minutes_in_trade': row['minutes_in_trade'], 'hmm_regime': row['hmm_regime']
                        })

    print("\n========================================================")
    print("      LIVE PRODUCTION ENGINE: CALIBRATED QUARTER-KELLY    ")
    print("========================================================")
    if portfolio_history:
        port_df = pd.DataFrame(portfolio_history)
        trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()
        
        years = max((port_df['date'].iloc[-1] - port_df['date'].iloc[0]).days / 365.25, 0.1)
        final_equity = port_df['mtm_equity'].iloc[-1]
        cagr = (final_equity / starting_capital) ** (1 / years) - 1
        port_df['daily_return'] = port_df['mtm_equity'].pct_change().fillna(0)
        daily_std = port_df['daily_return'].std()
        sharpe = (port_df['daily_return'].mean() / daily_std) * np.sqrt(365) if daily_std > 0 else 0.0
        max_dd = ((port_df['mtm_equity'] - port_df['mtm_equity'].cummax()) / port_df['mtm_equity'].cummax()).min()
        win_rate = (trade_df['net_ret'] > 0).mean() if not trade_df.empty else 0
        
        print(f"  - Total Trades Executed: {len(trade_df)}")
        print(f"  - Win Rate (Calibrated): {win_rate:.2%}")
        print(f"  - Final Mark-to-Market Equity: ${final_equity:,.2f} (from $10k)")
        print(f"  - True Compound Annual Growth Rate (CAGR): {cagr:.2%}")
        print(f"  - Maximum Drawdown: {max_dd:.2%}")
        print(f"  - Annualized Sharpe Ratio: {sharpe:.2f}")
        
        if not trade_df.empty and 'hmm_regime' in trade_df.columns:
            print("\n--------------------------------------------------------")
            print("            PER-REGIME PERFORMANCE BREAKDOWN           ")
            print("--------------------------------------------------------")
            reg_df = trade_df.groupby('hmm_regime').agg(
                Trades=('net_ret', 'count'),
                Win_Rate=('net_ret', lambda x: f"{(x > 0).mean():.2%}"),
                Total_Profit=('profit', lambda x: f"${x.sum():,.2f}"),
                Avg_Net_Ret=('net_ret', lambda x: f"{x.mean():.2%}")
            )
            print(reg_df.to_string())

if __name__ == "__main__":
    main()
