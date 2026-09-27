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

MAJORS = {'BTCUSD', 'ETHUSD', 'SOLUSD', 'BTC', 'ETH', 'SOL'}
LIQUID_ALTS = {'AVAXUSD', 'NEARUSD', 'LINKUSD', 'SUIUSD', 'AAVEUSD', 'BNBUSD', 'XRPUSD', 'DOGEUSD', 'ADAUSD', 'TRXUSD'}

def get_tier_frictions(ticker):
    t = str(ticker).upper()
    if t in MAJORS:
        return 0.0007, 0.0005, 0.0010
    elif t in LIQUID_ALTS:
        return 0.0010, 0.0008, 0.0015
    else:
        return 0.0016, 0.0012, 0.0022

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
    print("="*85)
    print("          DEEP SHORT-SIDE ABLATION & SENSITIVITY AUTOPSY         ")
    print("="*85)

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

    df_test['primary_prob_short'] = 0.0
    for regime in ['0', '1', '2']:
        m_s_path = f"{MODEL_DIR}/regime_{regime}_short_expert.cbm"
        regime_idx = df_test[df_test['hmm_regime'] == regime].index
        if len(regime_idx) > 0 and os.path.exists(m_s_path):
            exp_short = CatBoostClassifier().load_model(m_s_path)
            df_test.loc[regime_idx, 'primary_prob_short'] = exp_short.predict_proba(df_test.loc[regime_idx, all_features])[:, 1]

    meta_short = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_short.cbm")
    cal_short = joblib.load(f"{MODEL_DIR}/meta_calibrator_short.pkl")
    df_test['calibrated_prob_short'] = cal_short.predict(meta_short.predict_proba(df_test[meta_short.feature_names_])[:, 1])

    # ------------------------------------------------------------------------
    # SECTION A: SIGNAL QUALITY BY PROBABILITY BUCKET (ALL SHORTS p >= 0.50)
    # ------------------------------------------------------------------------
    print("\n--- SECTION A: SHORT SIGNAL QUALITY BY CALIBRATED PROBABILITY BUCKET ---")
    all_short_candidates = df_test[(df_test['calibrated_prob_short'] >= 0.50) & (df_test['hmm_p_chop'] < 0.50)].copy()
    
    bins = [0.50, 0.52, 0.55, 0.58, 0.62, 1.00]
    labels = ['0.50-0.52', '0.52-0.55', '0.55-0.58', '0.58-0.62', '0.62+']
    all_short_candidates['p_bucket'] = pd.cut(all_short_candidates['calibrated_prob_short'], bins=bins, labels=labels, right=False)
    
    all_short_candidates['net_win_pct'] = ((all_short_candidates['entry_price'] - all_short_candidates['stop_loss_1_5_atr']) / all_short_candidates['entry_price']) - WIN_FRICTION
    all_short_candidates['net_loss_pct'] = ((all_short_candidates['target_price_1_5_atr'] - all_short_candidates['entry_price']) / all_short_candidates['entry_price']) + LOSS_FRICTION
    
    # Target short is 1 if it hits the lower barrier (TP for shorts)
    all_short_candidates['is_win'] = (all_short_candidates['target_short'] == 1).astype(int)
    all_short_candidates['trade_net_ret'] = np.where(
        all_short_candidates['is_win'] == 1,
        all_short_candidates['net_win_pct'],
        -all_short_candidates['net_loss_pct']
    )

    bucket_stats = all_short_candidates.groupby('p_bucket', observed=False).agg(
        Trade_Count=('is_win', 'count'),
        Win_Rate=('is_win', 'mean'),
        Avg_Net_Ret=('trade_net_ret', 'mean'),
        Gross_Profit=('trade_net_ret', lambda x: x[x > 0].sum()),
        Gross_Loss=('trade_net_ret', lambda x: abs(x[x < 0].sum()))
    )
    bucket_stats['Win_Rate'] = bucket_stats['Win_Rate'].map(lambda x: f"{x*100:.2f}%")
    bucket_stats['Avg_Net_Ret'] = bucket_stats['Avg_Net_Ret'].map(lambda x: f"{x*100:.2f}%")
    bucket_stats['Profit_Factor'] = (bucket_stats['Gross_Profit'] / bucket_stats['Gross_Loss'].replace(0, np.nan)).round(2)
    print(bucket_stats[['Trade_Count', 'Win_Rate', 'Avg_Net_Ret', 'Profit_Factor']].to_string())

    # ------------------------------------------------------------------------
    # SECTION B: SHORT PERFORMANCE BY HMM REGIME (0, 1, 2)
    # ------------------------------------------------------------------------
    print("\n--- SECTION B: SHORT PERFORMANCE DECOMPOSITION BY HMM REGIME ---")
    regime_stats = all_short_candidates.groupby('hmm_regime').agg(
        Trade_Count=('is_win', 'count'),
        Win_Rate=('is_win', 'mean'),
        Avg_Net_Ret=('trade_net_ret', 'mean'),
        Gross_Profit=('trade_net_ret', lambda x: x[x > 0].sum()),
        Gross_Loss=('trade_net_ret', lambda x: abs(x[x < 0].sum()))
    )
    regime_stats['Win_Rate'] = regime_stats['Win_Rate'].map(lambda x: f"{x*100:.2f}%")
    regime_stats['Avg_Net_Ret'] = regime_stats['Avg_Net_Ret'].map(lambda x: f"{x*100:.2f}%")
    regime_stats['Profit_Factor'] = (regime_stats['Gross_Profit'] / regime_stats['Gross_Loss'].replace(0, np.nan)).round(2)
    print(regime_stats[['Trade_Count', 'Win_Rate', 'Avg_Net_Ret', 'Profit_Factor']].to_string())

    # ------------------------------------------------------------------------
    # SECTION C: SHORT SIMULATION ABLATION EXPERIMENTS
    # ---------------------------------------------------------
    def run_short_sim(threshold=0.52, block_r1=False, block_r2=False, leverage=10.0, kelly_frac=0.50):
        starting_cap = 1000.0
        capital = starting_cap
        available_cap = starting_cap
        peak_cap = starting_cap
        max_dd = 0.0
        open_positions = []
        trade_log = []
        
        all_ts = sorted(df_test['timestamp'].unique())
        
        for ts in all_ts:
            still_open = []
            for pos in open_positions:
                if ts >= pos['exit_time']:
                    profit = pos['notional'] * pos['net_ret']
                    capital += profit
                    available_cap += (pos['margin'] + profit)
                    if capital > peak_cap: peak_cap = capital
                    if capital <= 0: return 0.0, 0, 0.0, -100.0
                    trade_log.append(profit)
                else:
                    still_open.append(pos)
            open_positions = still_open
            
            dd = (peak_cap - capital) / peak_cap if peak_cap > 0 else 0.0
            if dd > max_dd: max_dd = dd
            
            signals = df_test[df_test['timestamp'] == ts]
            for _, row in signals.iterrows():
                if len(open_positions) >= 5 or row['hmm_p_chop'] >= 0.50 or row['hmm_regime'] == '0':
                    continue
                if block_r1 and row['hmm_regime'] == '1': continue
                if block_r2 and row['hmm_regime'] == '2': continue
                    
                p = row['calibrated_prob_short']
                if p >= threshold:
                    gross_win = (row['entry_price'] - row['stop_loss_1_5_atr']) / row['entry_price']
                    gross_loss = (row['target_price_1_5_atr'] - row['entry_price']) / row['entry_price']
                    net_win, net_loss = gross_win - WIN_FRICTION, gross_loss + LOSS_FRICTION
                    ev = (p * net_win) - ((1 - p) * net_loss)
                    
                    if ev <= 0: continue
                    
                    dynamic_payoff = net_win / net_loss
                    kelly_f = p - ((1 - p) / dynamic_payoff)
                    
                    dd_multi = 0.25 if dd >= 0.30 else (0.50 if dd >= 0.15 else 1.0)
                    trade_notional_pct = min(kelly_f * kelly_frac * leverage * dd_multi, 2.0)
                    notional = min(capital * trade_notional_pct, HARD_LIQUIDITY_CAP)
                    margin = notional / leverage
                    
                    if available_cap >= margin and notional > 10.0:
                        available_cap -= margin
                        net_ret = -row['exact_gross_return'] - WIN_FRICTION if row['target_short'] == 1 else -row['exact_gross_return'] - LOSS_FRICTION
                        open_positions.append({'exit_time': row['exit_time'], 'notional': notional, 'margin': margin, 'net_ret': net_ret})

        wins = [t for t in trade_log if t > 0]
        wr = (len(wins) / len(trade_log) * 100.0) if trade_log else 0.0
        return capital, len(trade_log), wr, max_dd * 100.0

    print("\n--- SECTION C: SHORT-ONLY ABLATION EXPERIMENTS ---")
    exp_a = run_short_sim(threshold=0.52, block_r1=False, block_r2=False, leverage=10.0, kelly_frac=0.50)
    exp_b = run_short_sim(threshold=0.52, block_r1=True, block_r2=False, leverage=10.0, kelly_frac=0.50)
    exp_c = run_short_sim(threshold=0.55, block_r1=False, block_r2=False, leverage=10.0, kelly_frac=0.50)
    exp_d1 = run_short_sim(threshold=0.52, block_r1=False, block_r2=False, leverage=7.0, kelly_frac=0.50)
    exp_d2 = run_short_sim(threshold=0.52, block_r1=False, block_r2=False, leverage=10.0, kelly_frac=0.25)

    print(f"{'Experiment':<35} | {'Final Equity':<15} | {'Trades':<8} | {'Win Rate':<10} | {'Max DD':<10}")
    print("-" * 85)
    print(f"{'Exp A: Baseline (p>=0.52, All Reg, 10x)':<35} | ${exp_a[0]:>13,.2f} | {exp_a[1]:>8} | {exp_a[2]:>9.2f}% | -{exp_a[3]:>8.2f}%")
    print(f"{'Exp B: Block Regime 1 (Trend)':<35} | ${exp_b[0]:>13,.2f} | {exp_b[1]:>8} | {exp_b[2]:>9.2f}% | -{exp_b[3]:>8.2f}%")
    print(f"{'Exp C: Higher Threshold (p>=0.55)':<35} | ${exp_c[0]:>13,.2f} | {exp_c[1]:>8} | {exp_c[2]:>9.2f}% | -{exp_c[3]:>8.2f}%")
    print(f"{'Exp D1: Lower Leverage (7x)':<35} | ${exp_d1[0]:>13,.2f} | {exp_d1[1]:>8} | {exp_d1[2]:>9.2f}% | -{exp_d1[3]:>8.2f}%")
    print(f"{'Exp D2: Lower Kelly (0.25K)':<35} | ${exp_d2[0]:>13,.2f} | {exp_d2[1]:>8} | {exp_d2[2]:>9.2f}% | -{exp_d2[3]:>8.2f}%")

    # ------------------------------------------------------------------------
    # SECTION D: 2D SHORT EFFICIENT FRONTIER GRID (Threshold x Leverage)
    # ------------------------------------------------------------------------
    print("\n--- SECTION D: 2D EFFICIENT FRONTIER GRID (THRESHOLD x LEVERAGE) ---")
    thresholds = [0.50, 0.52, 0.54, 0.56, 0.58]
    leverages = [3.0, 5.0, 7.0, 10.0, 15.0]
    
    results_grid = []
    for th in thresholds:
        for lev in leverages:
            eq, n_tr, wr, dd = run_short_sim(threshold=th, block_r1=False, block_r2=False, leverage=lev, kelly_frac=0.50)
            results_grid.append({
                'Threshold': th, 'Leverage': f"{lev:.0f}x",
                'Equity': eq, 'Trades': n_tr, 'Win_Rate': wr, 'Max_DD': dd
            })
            
    grid_df = pd.DataFrame(results_grid)
    pivot_eq = grid_df.pivot(index='Threshold', columns='Leverage', values='Equity')
    pivot_dd = grid_df.pivot(index='Threshold', columns='Leverage', values='Max_DD')
    
    print("\n[TERMINAL EQUITY ($1k Start)]")
    print((pivot_eq.map(lambda x: f"${x:,.0f}")).to_string())
    
    print("\n[MAXIMUM DRAWDOWN (%)]")
    print((pivot_dd.map(lambda x: f"-{x:.1f}%")).to_string())
    print("="*85 + "\n")

if __name__ == "__main__":
    main()
