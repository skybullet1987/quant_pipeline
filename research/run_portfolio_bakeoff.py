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

WIN_FRICTION = 0.0014
LOSS_FRICTION = 0.0020
HARD_LIQUIDITY_CAP = 150000.0
GLOBAL_RISK_CAP = 0.05
MAX_POSITIONS = 5

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
        WHERE f.target_tbm_upper_hit IS NOT NULL AND p.exit_reason != 'DATA_ERROR'
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exact_gross_return', 'exit_time', 'minutes_in_trade']).fillna(0).copy()

def run_combined_simulation(df_test, config):
    capital = 1000.0
    peak_capital = capital
    max_dd = 0.0
    open_positions = []
    trade_log = []
    
    all_ts = sorted(df_test['timestamp'].unique())
    
    for ts in all_ts:
        # 1. Process Exits
        still_open = []
        for pos in open_positions:
            if ts >= pos['exit_time']:
                profit = pos['notional'] * pos['net_ret']
                capital += profit
                if capital > peak_cap: peak_cap = capital
                if capital <= 0: return 0.0, 0, 0.0, -100.0, 0.0
                trade_log.append({'profit': profit, 'direction': pos['direction']})
            else:
                still_open.append(pos)
        open_positions = still_open
        
        peak_cap = max(peak_capital, capital)
        dd = (peak_cap - capital) / peak_cap if peak_cap > 0 else 0.0
        if dd > max_dd: max_dd = dd
        
        # 2. Process Entries
        signals = df_test[df_test['timestamp'] == ts]
        current_risk_pct = sum([p['risk_pct'] for p in open_positions])
        
        for _, row in signals.iterrows():
            if len(open_positions) >= MAX_POSITIONS or current_risk_pct >= GLOBAL_RISK_CAP:
                break
                
            regime = str(row['hmm_regime'])
            if row['hmm_p_chop'] >= 0.50 or regime == '0':
                continue
                
            p_l, p_s = row['calibrated_prob_long'], row['calibrated_prob_short']
            direction = None
            
            # Legacy vs New Config Logic
            if config['name'] == 'Legacy':
                if p_l >= 0.58 and regime != '2':
                    direction, p, lev, k_frac = 'LONG', p_l, 3.0, 0.20
                elif p_s >= 0.52:
                    direction, p, lev, k_frac = 'SHORT', p_s, 10.0, 0.50
            else: # Candidate
                if p_l >= 0.60 and regime != '2':
                    direction, p, lev, k_frac = 'LONG', p_l, 4.0, 0.20
                elif p_s >= 0.56 and regime != '1':
                    direction, p, lev, k_frac = 'SHORT', p_s, 7.0, 0.50

            if not direction: continue

            # Calculate EV and Risk
            if direction == 'LONG':
                gross_win = (row['target_price_1_5_atr'] - row['entry_price']) / row['entry_price']
                gross_loss = (row['entry_price'] - row['stop_loss_1_5_atr']) / row['entry_price']
                net_ret = row['exact_gross_return'] - WIN_FRICTION if row['exit_reason'] == 'TP_HIT' else row['exact_gross_return'] - LOSS_FRICTION
            else:
                gross_win = (row['entry_price'] - row['stop_loss_1_5_atr']) / row['entry_price']
                gross_loss = (row['target_price_1_5_atr'] - row['entry_price']) / row['entry_price']
                net_ret = -row['exact_gross_return'] - WIN_FRICTION if row['target_short'] == 1 else -row['exact_gross_return'] - LOSS_FRICTION
                
            net_win, net_loss = gross_win - WIN_FRICTION, gross_loss + LOSS_FRICTION
            ev = (p * net_win) - ((1 - p) * net_loss)
            
            if ev <= 0: continue
            
            dynamic_payoff = net_win / net_loss
            kelly_f = p - ((1 - p) / dynamic_payoff)
            
            dd_multi = 0.25 if dd >= 0.30 else (0.50 if dd >= 0.15 else 1.0)
            trade_notional_pct = min(kelly_f * k_frac * lev * dd_multi, 2.0)
            trade_risk_pct = trade_notional_pct * net_loss
            
            if current_risk_pct + trade_risk_pct > GLOBAL_RISK_CAP:
                rem_risk = max(0.0, GLOBAL_RISK_CAP - current_risk_pct)
                if rem_risk <= 0.0005: continue
                trade_notional_pct *= (rem_risk / trade_risk_pct)
                trade_risk_pct = rem_risk
                
            notional = min(capital * trade_notional_pct, HARD_LIQUIDITY_CAP)
            
            if notional > 10.0:
                open_positions.append({
                    'exit_time': row['exit_time'], 'notional': notional,
                    'net_ret': net_ret, 'risk_pct': trade_risk_pct, 'direction': direction
                })
                current_risk_pct += trade_risk_pct

    trades_df = pd.DataFrame(trade_log)
    if trades_df.empty: return 0.0, 0, 0.0, 0.0, 0.0
    
    wins = trades_df[trades_df['profit'] > 0]
    wr = len(wins) / len(trades_df) * 100.0
    cagr_proxy = (capital / 1000.0) ** (365.0 / 90.0) - 1.0
    calmar = cagr_proxy / max_dd if max_dd > 0 else 0.0
    
    return capital, len(trades_df), wr, max_dd * 100.0, calmar

def main():
    print("Loading Core Data and Models...")
    df = load_data()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].copy().reset_index(drop=True)

    max_minutes = df['minutes_in_trade'].max()
    purge_bars = int(np.ceil(max_minutes / 240.0))

    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    test_ts = timestamps[split_idx + purge_bars :]
    df_test = df[df['timestamp'].isin(test_ts)].copy().reset_index(drop=True)

    hmm_model = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{MODEL_DIR}/hmm_scaler.pkl")
    hmm_features = joblib.load(f"{MODEL_DIR}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
    
    scaled_x = hmm_scaler.transform(df_test[hmm_features].fillna(0))
    can_probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
    df_test["hmm_p_chop"] = can_probs[:, 0]
    df_test["hmm_regime"] = can_probs.argmax(axis=1).astype(str)

    all_cat_cols = joblib.load(f"{MODEL_DIR}/cat_cols.pkl")
    all_features = joblib.load(f"{MODEL_DIR}/feature_names.pkl")
    for col in all_cat_cols: df_test[col] = df_test[col].astype(str)

    for direction in ['long', 'short']:
        df_test[f'primary_prob_{direction}'] = 0.0
        for regime in ['0', '1', '2']:
            path = f"{MODEL_DIR}/regime_{regime}_{direction}_expert.cbm"
            idx = df_test[df_test['hmm_regime'] == regime].index
            if len(idx) > 0 and os.path.exists(path):
                exp = CatBoostClassifier().load_model(path)
                df_test.loc[idx, f'primary_prob_{direction}'] = exp.predict_proba(df_test.loc[idx, all_features])[:, 1]
                
        meta = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_{direction}.cbm")
        cal = joblib.load(f"{MODEL_DIR}/meta_calibrator_{direction}.pkl")
        df_test[f'calibrated_prob_{direction}'] = cal.predict(meta.predict_proba(df_test[meta.feature_names_])[:, 1])

    print("\n" + "="*95)
    print("           PORTFOLIO BAKEOFF: LEGACY VS CONDITIONAL ALLOCATOR            ")
    print("="*95)

    configs = [
        {'name': 'Legacy'},
        {'name': 'Candidate'}
    ]

    h1, h2, h3, h4, h5, h6 = "Configuration", "Terminal Equity", "Max DD", "Calmar", "Win Rate", "Total Trades"
    print(f"{h1:<15} | {h2:<18} | {h3:<10} | {h4:<8} | {h5:<10} | {h6:<12}")
    print("-" * 95)

    for c in configs:
        eq, tr, wr, dd, calmar = run_combined_simulation(df_test, c)
        print(f"{c['name']:<15} | ${eq:>16,.2f} | -{dd:>9.2f}% | {calmar:>8.2f} | {wr:>9.2f}% | {tr:>12}")
    print("="*95 + "\n")

if __name__ == "__main__":
    main()
