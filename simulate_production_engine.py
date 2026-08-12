import os
import joblib
import warnings
import numpy as np
import pandas as pd
from google.cloud import bigquery
from catboost import CatBoostClassifier

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

# Hyperliquid Friction
WIN_FRICTION = 0.0014  
LOSS_FRICTION = 0.0020 

# ============================================================================
# PHASE 2: ASYMMETRIC 10X RISK CONFIGURATION
# ============================================================================
ENTRY_THRESHOLD_SHORT = 0.52
ENTRY_THRESHOLD_LONG = 0.58

LEVERAGE_SHORT = 10.0
LEVERAGE_LONG = 3.0

KELLY_FRACTION_SHORT = 0.50 # Aggressive Half-Kelly on proven Short edge
KELLY_FRACTION_LONG = 0.20  # Defensive Fifth-Kelly on weak Long edge

MAX_CONCURRENT_POSITIONS = 5
HARD_LIQUIDITY_CAP = 150000.0

def load_data():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*, p.exit_time, p.exit_reason, p.exact_gross_return, p.minutes_in_trade, p.entry_price, p.target_price_1_5_atr, p.stop_loss_1_5_atr,
            p.target_long, p.target_short,
            t.tfm_ret_24h, t.tfm_ret_72h, t.tfm_slope, t.tfm_uncertainty, t.tfm_residual_24h, t.tfm_conviction_delta,
            COALESCE(l.total_liq_usd, 0) AS total_liq_usd,
            COALESCE(l.liq_imbalance_ratio, 0) AS liq_imbalance_ratio,
            COALESCE(l.long_liq_accel, 0) AS long_liq_accel,
            COALESCE(l.short_liq_accel, 0) AS short_liq_accel,
            COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
          AND p.exit_reason != 'DATA_ERROR'
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exact_gross_return', 'exit_time', 'minutes_in_trade']).fillna(0).copy()

def main():
    print("1. Ingesting Matrix and Isolating OOS Test Block...")
    df = load_data()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].copy().reset_index(drop=True)

    max_minutes = df['minutes_in_trade'].max()
    purge_bars = int(np.ceil(max_minutes / 240.0))

    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    test_ts = timestamps[split_idx + purge_bars :]
    df_test = df[df['timestamp'].isin(test_ts)].copy().reset_index(drop=True)

    print("2. Scoring Canonical HMM Regimes...")
    hmm_model = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{MODEL_DIR}/hmm_scaler.pkl")
    hmm_features = joblib.load(f"{MODEL_DIR}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
    
    scaled_x = hmm_scaler.transform(df_test[hmm_features].fillna(0))
    can_probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
    
    df_test["hmm_p_chop"] = can_probs[:, 0]
    df_test["hmm_p_trend"] = can_probs[:, 1]
    df_test["hmm_p_cascade"] = can_probs[:, 2]
    df_test["hmm_regime"] = can_probs.argmax(axis=1).astype(str)

    all_cat_cols = joblib.load(f"{MODEL_DIR}/cat_cols.pkl")
    all_features = joblib.load(f"{MODEL_DIR}/feature_names.pkl")
    for col in all_cat_cols: df_test[col] = df_test[col].astype(str)

    print("3. Scoring Primary Experts & Calibrated Meta-Labelers...")
    df_test['primary_prob_long'] = 0.0
    df_test['primary_prob_short'] = 0.0

    for regime in ['0', '1', '2']:
        m_l_path = f"{MODEL_DIR}/regime_{regime}_long_expert.cbm"
        m_s_path = f"{MODEL_DIR}/regime_{regime}_short_expert.cbm"
        regime_idx = df_test[df_test['hmm_regime'] == regime].index
        
        if len(regime_idx) > 0 and os.path.exists(m_l_path):
            exp_long = CatBoostClassifier().load_model(m_l_path)
            df_test.loc[regime_idx, 'primary_prob_long'] = exp_long.predict_proba(df_test.loc[regime_idx, all_features])[:, 1]
            
        if len(regime_idx) > 0 and os.path.exists(m_s_path):
            exp_short = CatBoostClassifier().load_model(m_s_path)
            df_test.loc[regime_idx, 'primary_prob_short'] = exp_short.predict_proba(df_test.loc[regime_idx, all_features])[:, 1]

    meta_long = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_long.cbm")
    cal_long = joblib.load(f"{MODEL_DIR}/meta_calibrator_long.pkl")
    meta_short = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_short.cbm")
    cal_short = joblib.load(f"{MODEL_DIR}/meta_calibrator_short.pkl")

    df_test['calibrated_prob_long'] = cal_long.predict(meta_long.predict_proba(df_test[meta_long.feature_names_])[:, 1])
    df_test['calibrated_prob_short'] = cal_short.predict(meta_short.predict_proba(df_test[meta_short.feature_names_])[:, 1])

    print("4. Executing Phase 2 Asymmetric Kelly Simulator...")
    all_timestamps = sorted(df_test['timestamp'].unique())
    starting_capital = 1000.0
    realized_capital = starting_capital
    available_capital = starting_capital
    peak_capital = starting_capital
    
    open_positions = []
    portfolio_history = []
    trade_log = []

    for ts in all_timestamps:
        still_open = []
        for pos in open_positions:
            if ts >= pos['exit_time']:
                profit = pos['notional_size'] * pos['net_ret']
                realized_capital += profit
                available_capital += (pos['margin_tied'] + profit)
                
                if realized_capital > peak_capital:
                    peak_capital = realized_capital

                if realized_capital <= 0:
                    print(f"\n[!] LIQUIDATED at {ts}")
                    return

                trade_log.append({
                    'profit': profit, 'net_ret': pos['net_ret'], 
                    'direction': pos['direction'], 'hmm_regime': pos['hmm_regime']
                })
            else:
                still_open.append(pos)
        open_positions = still_open

        if ts.hour == 0:
            portfolio_history.append({'date': ts.date(), 'mtm_equity': realized_capital})

        # Calculate Current Drawdown Scale Factor
        current_drawdown = (peak_capital - realized_capital) / peak_capital if peak_capital > 0 else 0
        dd_multiplier = 1.0
        if current_drawdown >= 0.30:
            dd_multiplier = 0.25
        elif current_drawdown >= 0.15:
            dd_multiplier = 0.50

        current_signals = df_test[df_test['timestamp'] == ts]
        for _, row in current_signals.iterrows():
            # RULE 1: Complete Ban on Chop (State 0)
            if len(open_positions) >= MAX_CONCURRENT_POSITIONS or row['hmm_p_chop'] >= 0.50 or row['hmm_regime'] == '0':
                continue

            p_l, p_s = row['calibrated_prob_long'], row['calibrated_prob_short']

            # Evaluate Long
            gross_win_l = (row['target_price_1_5_atr'] - row['entry_price']) / row['entry_price']
            gross_loss_l = (row['entry_price'] - row['stop_loss_1_5_atr']) / row['entry_price']
            net_win_l, net_loss_l = gross_win_l - WIN_FRICTION, gross_loss_l + LOSS_FRICTION
            ev_l = (p_l * net_win_l) - ((1 - p_l) * net_loss_l)

            # Evaluate Short
            gross_win_s = (row['entry_price'] - row['stop_loss_1_5_atr']) / row['entry_price']
            gross_loss_s = (row['target_price_1_5_atr'] - row['entry_price']) / row['entry_price']
            net_win_s, net_loss_s = gross_win_s - WIN_FRICTION, gross_loss_s + LOSS_FRICTION
            ev_s = (p_s * net_win_s) - ((1 - p_s) * net_loss_s)

            direction = None
            # RULE 2: Asymmetric Directional Hurdles
            # Longs blocked during State 2 (Cascade); require p >= 0.58
            if ev_l > ev_s and ev_l > 0 and p_l >= ENTRY_THRESHOLD_LONG and row['hmm_regime'] != '2':
                direction, p, net_win, net_loss = 'LONG', p_l, net_win_l, net_loss_l
                net_ret = row['exact_gross_return'] - WIN_FRICTION if row['exit_reason'] == 'TP_HIT' else row['exact_gross_return'] - LOSS_FRICTION
                leverage = LEVERAGE_LONG
                kelly_fraction = KELLY_FRACTION_LONG
            
            # Shorts favored; require p >= 0.52
            elif ev_s > ev_l and ev_s > 0 and p_s >= ENTRY_THRESHOLD_SHORT:
                direction, p, net_win, net_loss = 'SHORT', p_s, net_win_s, net_loss_s
                net_ret = -row['exact_gross_return'] - WIN_FRICTION if row['exit_reason'] == 'SL_HIT' else -row['exact_gross_return'] - LOSS_FRICTION
                leverage = LEVERAGE_SHORT
                kelly_fraction = KELLY_FRACTION_SHORT

            if direction:
                dynamic_payoff = net_win / net_loss
                kelly_f = p - ((1 - p) / dynamic_payoff)
                
                # Apply Drawdown Throttle Multiplier
                trade_notional_pct = min(kelly_f * kelly_fraction * leverage * dd_multiplier, 2.0)
                raw_notional = realized_capital * trade_notional_pct
                notional_size = min(raw_notional, HARD_LIQUIDITY_CAP)
                margin_required = notional_size / leverage

                if available_capital >= margin_required and notional_size > 10.0:
                    available_capital -= margin_required
                    open_positions.append({
                        'entry_time': ts, 'exit_time': row['exit_time'], 
                        'notional_size': notional_size, 'margin_tied': margin_required,
                        'net_ret': net_ret, 'minutes_in_trade': row['minutes_in_trade'],
                        'direction': direction, 'hmm_regime': row['hmm_regime']
                    })

    print("\n========================================================")
    print("      PHASE 2 ASYMMETRIC 10X PRODUCTION RESULTS         ")
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
        
        print(f"  - Starting Capital: ${starting_capital:,.2f}")
        print(f"  - Total Trades Executed: {len(trade_df)}")
        print(f"  - Win Rate (Calibrated): {win_rate:.2%}")
        print(f"  - Final Mark-to-Market Equity: ${final_equity:,.2f}")
        print(f"  - True Compound Annual Growth Rate (CAGR): {cagr:.2%}")
        print(f"  - Maximum Drawdown: {max_dd:.2%}")
        print(f"  - Annualized Sharpe Ratio: {sharpe:.2f}")

        if not trade_df.empty:
            print("\n            PER-DIRECTION PERFORMANCE BREAKDOWN         ")
            dir_df = trade_df.groupby('direction').agg(
                Trades=('net_ret', 'count'),
                Win_Rate=('net_ret', lambda x: f"{(x > 0).mean():.2%}"),
                Total_Profit=('profit', lambda x: f"${x.sum():,.2f}"),
                Avg_Net_Ret=('net_ret', lambda x: f"{x.mean():.2%}")
            )
            print(dir_df.to_string())

if __name__ == "__main__":
    main()
