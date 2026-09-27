import os
import gc
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from catboost import CatBoostClassifier, Pool
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ============================================================================
# 1. PRODUCTION POLICY CONFIGURATION
# ============================================================================
PROJECT_ID = "parnasa-498503"
STARTING_CAPITAL = 1000.0
MAX_POSITIONS = 5
MAX_TRADES_PER_CYCLE = 2
HARD_LIQUIDITY_CAP = 150000.0
FEE_SLIPPAGE_BPS = 15.0

WIN_FRICTION = 0.0014   # 14 bps
LOSS_FRICTION = 0.0020  # 20 bps

ENTRY_THRESHOLD_LONG = 0.58
KELLY_LONG = 0.20
LEVERAGE_LONG = 4.0

ENTRY_THRESHOLD_SHORT = 0.52
KELLY_SHORT = 0.50
LEVERAGE_SHORT = 7.0

CAT_COLS_BASE = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend', 'market_session', 'btc_above_sma50']
FEATURE_COLS_NUM = [
    'market_breadth_sma20', 'top_breakout_breadth', 'pos_bar_count_6p',
    'candle_body_pct', 'candle_upper_wick_pct', 'candle_lower_wick_pct',
    'rank_eth_btc_spread_20p', 'rank_btc_dominance_spread',
    'rank_gk_vol_20p', 'rank_vol_term_structure', 'rank_gk_vol_zscore', 'rank_vol_compression_ratio',
    'rank_mom_24h', 'rank_mom_7d', 'rank_mom_accel_24h', 'rank_mom_ratio_24h_7d',
    'rank_dist_to_120p_high', 'rank_relative_vol_120p', 'rank_rolling_sharpe_20p', 'rank_atr_pct_20',
    'tfm_ret_24h', 'tfm_ret_72h', 'tfm_slope', 'tfm_uncertainty', 'tfm_residual_24h', 'tfm_conviction_delta',
    'total_liq_usd', 'liq_imbalance_ratio', 'long_liq_accel', 'short_liq_accel', 'rank_liq_intensity'
]

# ============================================================================
# 2. CAUSAL EMBARGOED CROSS-VALIDATION
# ============================================================================
class PurgedWalkForwardCV:
    def __init__(self, n_splits=4, purge_hours=72):
        self.n_splits = n_splits
        self.purge_hours = purge_hours
        
    def split(self, df):
        timestamps = np.sort(df['timestamp'].unique())
        chunk_size = len(timestamps) // (self.n_splits + 1)
        
        for i in range(1, self.n_splits + 1):
            train_end_ts = timestamps[i * chunk_size]
            val_start_ts = train_end_ts + pd.Timedelta(hours=self.purge_hours)
            val_end_ts = timestamps[-1] + pd.Timedelta(seconds=1) if i == self.n_splits else timestamps[(i + 1) * chunk_size]
            
            train_idx = df.index[df['timestamp'] <= train_end_ts].tolist()
            val_idx = df.index[(df['timestamp'] >= val_start_ts) & (df['timestamp'] < val_end_ts)].tolist()
            
            if len(train_idx) > 0 and len(val_idx) > 0:
                yield train_idx, val_idx

# ============================================================================
# 3. DATA INGESTION
# ============================================================================
def load_production_feature_matrix():
    print("\n[1/4] Ingesting Full Feature Matrix & Ground-Truth Path Resolutions...")
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*, 
            p.exit_time, p.exit_reason, p.exact_gross_return, p.minutes_in_trade, 
            p.entry_price, p.target_price_1_5_atr, p.stop_loss_1_5_atr,
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
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    
    df = df.dropna(subset=['exit_reason', 'exit_time', 'minutes_in_trade', 'close', 'atr_20']).fillna(0).copy()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)
    print(f"  -> Ingested {len(df):,} causal rows across {df['ticker'].nunique()} tickers.")
    return df

# ============================================================================
# 4. WALK-FORWARD TRAINING & SCORING
# ============================================================================
def execute_walk_forward_oos_scoring(df):
    print("\n[2/4] Executing 3-Fold Expanding Walk-Forward Training & Scoring...")
    
    max_ts = df['timestamp'].max()
    oos_start_ts = max_ts - pd.Timedelta(days=90)
    fold_duration = (max_ts - oos_start_ts) / 3
    
    f1_start, f1_end = oos_start_ts, oos_start_ts + fold_duration
    f2_start, f2_end = f1_end, f1_end + fold_duration
    f3_start, f3_end = f2_end, max_ts
    
    fold_schedule = [
        (f1_start, f1_end, f"Fold 1 ({f1_start.strftime('%m/%d')} - {f1_end.strftime('%m/%d')})"),
        (f2_start, f2_end, f"Fold 2 ({f2_start.strftime('%m/%d')} - {f2_end.strftime('%m/%d')})"),
        (f3_start, f3_end, f"Fold 3 ({f3_start.strftime('%m/%d')} - {f3_end.strftime('%m/%d')})")
    ]
    
    scored_oos_blocks = []

    for fold_i, (test_start, test_end, fold_label) in enumerate(fold_schedule, 1):
        print(f"\n--- TRAINING & SCORING {fold_label.upper()} ---")
        
        train_cutoff = test_start - pd.Timedelta(hours=72)
        df_train = df[df['timestamp'] <= train_cutoff].copy().reset_index(drop=True)
        df_test = df[(df['timestamp'] >= test_start) & (df['timestamp'] <= test_end)].copy().reset_index(drop=True)
        
        print(f"  - Training Period : {df_train['timestamp'].min().strftime('%Y-%m-%d')} -> {train_cutoff.strftime('%Y-%m-%d %H:%M')} ({len(df_train):,} bars)")
        print(f"  - OOS Test Period : {test_start.strftime('%Y-%m-%d %H:%M')} -> {test_end.strftime('%Y-%m-%d %H:%M')} ({len(df_test):,} bars)")
        
        # A. Canonical HMM
        hmm_features = ["rank_gk_vol_zscore", "rank_mom_7d", "market_breadth_sma20"]
        hmm_scaler = StandardScaler()
        scaled_train_hmm = hmm_scaler.fit_transform(df_train[hmm_features].fillna(0))
        
        hmm_model = GaussianHMM(n_components=3, covariance_type="full", n_iter=400, random_state=42).fit(scaled_train_hmm)
        state_vol = [df_train.loc[hmm_model.predict(scaled_train_hmm) == i, "rank_gk_vol_zscore"].median() for i in range(3)]
        canonical_order = np.argsort(state_vol)
        
        df_train["hmm_regime"] = hmm_model.predict_proba(scaled_train_hmm)[:, canonical_order].argmax(axis=1).astype(str)
        
        scaled_test_hmm = hmm_scaler.transform(df_test[hmm_features].fillna(0))
        test_can_probs = hmm_model.predict_proba(scaled_test_hmm)[:, canonical_order]
        df_test["p_chop"] = test_can_probs[:, 0]
        df_test["regime"] = test_can_probs.argmax(axis=1).astype(str)
        
        all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
        all_features = FEATURE_COLS_NUM + all_cat_cols
        for col in all_cat_cols: df_train[col] = df_train[col].astype(str)
            
        test_cat_cols = CAT_COLS_BASE + ['regime']
        test_features = FEATURE_COLS_NUM + test_cat_cols
        for col in test_cat_cols: df_test[col] = df_test[col].astype(str)

        # B. Purged OOF CatBoost Experts
        df_train['primary_prob_long'] = 0.0
        df_train['primary_prob_short'] = 0.0
        cv = PurgedWalkForwardCV(n_splits=4, purge_hours=72)
        
        long_experts = {}
        short_experts = {}

        for r_state in ['0', '1', '2']:
            r_idx = df_train[df_train['hmm_regime'] == r_state].index
            if len(r_idx) > 100:
                df_regime = df_train.loc[r_idx].copy().reset_index(drop=True)
                for tr_i, val_i in cv.split(df_regime):
                    orig_tr, orig_val = r_idx[tr_i], r_idx[val_i]
                    
                    m_l = CatBoostClassifier(iterations=600, depth=5, early_stopping_rounds=40, learning_rate=0.03, verbose=0, random_seed=42)
                    m_l.fit(df_train.loc[orig_tr, all_features], df_train.loc[orig_tr, 'target_long'], cat_features=all_cat_cols, eval_set=(df_train.loc[orig_val, all_features], df_train.loc[orig_val, 'target_long']))
                    df_train.loc[orig_val, 'primary_prob_long'] = m_l.predict_proba(df_train.loc[orig_val, all_features])[:, 1]
                    
                    m_s = CatBoostClassifier(iterations=600, depth=5, early_stopping_rounds=40, learning_rate=0.03, verbose=0, random_seed=42)
                    m_s.fit(df_train.loc[orig_tr, all_features], df_train.loc[orig_tr, 'target_short'], cat_features=all_cat_cols, eval_set=(df_train.loc[orig_val, all_features], df_train.loc[orig_val, 'target_short']))
                    df_train.loc[orig_val, 'primary_prob_short'] = m_s.predict_proba(df_train.loc[orig_val, all_features])[:, 1]
                
                f_l = CatBoostClassifier(iterations=600, depth=5, learning_rate=0.03, verbose=0, random_seed=42)
                f_l.fit(df_train.loc[r_idx, all_features], df_train.loc[r_idx, 'target_long'], cat_features=all_cat_cols)
                long_experts[r_state] = f_l
                
                f_s = CatBoostClassifier(iterations=600, depth=5, learning_rate=0.03, verbose=0, random_seed=42)
                f_s.fit(df_train.loc[r_idx, all_features], df_train.loc[r_idx, 'target_short'], cat_features=all_cat_cols)
                short_experts[r_state] = f_s

        # C. Causal Meta-Labelers & Calibrators
        meta_models = {}
        calibrators = {}

        for direction, prob_col, target_col in [('long', 'primary_prob_long', 'target_long'), ('short', 'primary_prob_short', 'target_short')]:
            meta_tr = df_train[df_train[prob_col] > 0.50].copy().reset_index(drop=True)
            meta_feats = FEATURE_COLS_NUM + [prob_col]
            
            if len(meta_tr) > 50:
                meta_tr['oof_meta_prob'] = 0.0
                for tr_i, val_i in cv.split(meta_tr):
                    m_cv = CatBoostClassifier(iterations=400, depth=4, early_stopping_rounds=30, learning_rate=0.03, verbose=0, random_seed=42)
                    m_cv.fit(meta_tr.loc[tr_i, meta_feats], meta_tr.loc[tr_i, target_col], eval_set=(meta_tr.loc[val_i, meta_feats], meta_tr.loc[val_i, target_col]))
                    meta_tr.loc[val_i, 'oof_meta_prob'] = m_cv.predict_proba(meta_tr.loc[val_i, meta_feats])[:, 1]
                    
                final_meta = CatBoostClassifier(iterations=400, depth=4, learning_rate=0.03, verbose=0, random_seed=42)
                final_meta.fit(meta_tr[meta_feats], meta_tr[target_col])
                meta_models[direction] = final_meta
                
                cal = IsotonicRegression(out_of_bounds='clip')
                cal.fit(meta_tr['oof_meta_prob'], meta_tr[target_col])
                calibrators[direction] = cal

        # D. Predict OOS
        df_test['p_long'] = 0.0
        df_test['p_short'] = 0.0

        for r_state in ['0', '1', '2']:
            t_idx = df_test[df_test['regime'] == r_state].index
            if len(t_idx) > 0 and r_state in long_experts and r_state in short_experts:
                df_test_chunk = df_test.loc[t_idx, test_features].rename(columns={'regime': 'hmm_regime'})
                df_test.loc[t_idx, 'primary_prob_long'] = long_experts[r_state].predict_proba(df_test_chunk)[:, 1]
                df_test.loc[t_idx, 'primary_prob_short'] = short_experts[r_state].predict_proba(df_test_chunk)[:, 1]

        if 'long' in meta_models and 'long' in calibrators:
            meta_in_l = df_test[FEATURE_COLS_NUM + ['primary_prob_long']]
            df_test['p_long'] = calibrators['long'].predict(meta_models['long'].predict_proba(meta_in_l)[:, 1])
            
        if 'short' in meta_models and 'short' in calibrators:
            meta_in_s = df_test[FEATURE_COLS_NUM + ['primary_prob_short']]
            df_test['p_short'] = calibrators['short'].predict(meta_models['short'].predict_proba(meta_in_s)[:, 1])

        df_test['fold_name'] = fold_label
        scored_oos_blocks.append(df_test)

    full_df = pd.concat(scored_oos_blocks, ignore_index=True)
    full_df = full_df.drop_duplicates(subset=['timestamp', 'ticker']).sort_values('timestamp').reset_index(drop=True)
    return full_df, fold_schedule

# ============================================================================
# 5. FORENSIC PORTFOLIO SIMULATOR
# ============================================================================
def simulate_forensic_portfolio(df_oos):
    print("\n[3/4] Running Dual Simulator (Compounding Kelly vs. Fixed $1k Base)...")
    
    capital = STARTING_CAPITAL
    peak_capital = capital
    max_dd = 0.0
    
    fixed_capital = STARTING_CAPITAL
    fixed_peak = fixed_capital
    fixed_max_dd = 0.0
    
    open_positions = []
    closed_trades = []
    executed_entries_count = 0
    daily_snapshots = []
    
    funnel = {
        'universe_evaluated': 0, 'invalid_stale_data': 0, 'passed_prob_gate': 0,
        'passed_regime_chop': 0, 'passed_best_direction': 0, 'passed_positive_ev': 0,
        'portfolio_eligible': 0, 'passed_position_limit': 0, 'passed_exposure_limit': 0,
        'final_executed_entries': 0
    }
    
    rejections = {
        'SHORT_REGIME_BLOCKED': 0, 'LONG_REGIME_BLOCKED': 0, 'PROB_BELOW_BOTH_THRESHOLDS': 0,
        'CHOP_FILTER_ACTIVE': 0, 'NEGATIVE_NET_EV': 0, 'EXISTING_POSITION_ACTIVE': 0,
        'MAX_POSITIONS_REACHED': 0, 'MAX_TRADES_PER_CYCLE_REACHED': 0, 'INVALID_OR_ZERO_ATR': 0
    }

    all_timestamps = sorted(df_oos['timestamp'].unique())
    last_timestamp = all_timestamps[-1]

    for ts in all_timestamps:
        # 1. Process Exits
        still_open = []
        for pos in open_positions:
            if ts >= pos['exit_time']:
                profit_comp = pos['notional_comp'] * pos['net_ret']
                profit_fixed = pos['notional_fixed'] * pos['net_ret']
                
                capital += profit_comp
                fixed_capital += profit_fixed
                
                if capital > peak_capital: peak_capital = capital
                if fixed_capital > fixed_peak: fixed_peak = fixed_capital
                
                closed_trades.append({
                    'entry_time': pos['entry_time'], 'exit_time': pos['exit_time'],
                    'fold_name': pos['fold_name'], 'ticker': pos['ticker'],
                    'direction': pos['direction'], 'net_ret': pos['net_ret'],
                    'profit_comp': profit_comp, 'profit_fixed': profit_fixed,
                    'notional_comp': pos['notional_comp'], 'notional_fixed': pos['notional_fixed'],
                    'notional_pct_of_equity': pos['notional_pct'],
                    'leverage': pos['leverage'], 'exit_reason': pos['exit_reason'],
                    'p_win': pos['p_win'], 'regime': pos['regime'],
                    'minutes_in_trade': pos['minutes_in_trade'],
                    'capital_after_comp': capital, 'capital_after_fixed': fixed_capital
                })
            else:
                still_open.append(pos)
        open_positions = still_open

        dd_comp = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0.0
        if dd_comp > max_dd: max_dd = dd_comp
        
        dd_fixed = (fixed_peak - fixed_capital) / fixed_peak if fixed_peak > 0 else 0.0
        if dd_fixed > fixed_max_dd: fixed_max_dd = dd_fixed
        
        if ts.hour == 0:
            daily_snapshots.append({'timestamp': ts, 'equity_comp': capital, 'equity_fixed': fixed_capital})

        dd_multiplier = 0.25 if dd_comp >= 0.30 else (0.50 if dd_comp >= 0.15 else 1.0)
        
        # 2. Process Candidate Signals
        bar_candidates = df_oos[df_oos['timestamp'] == ts].copy()
        funnel['universe_evaluated'] += len(bar_candidates)
        active_tickers = {p['ticker'] for p in open_positions}
        valid_cycle_candidates = []
        
        for _, row in bar_candidates.iterrows():
            ticker = str(row['ticker']).replace("USDT", "").replace("USD", "").upper()
            p_l, p_s, p_c = float(row['p_long']), float(row['p_short']), float(row['p_chop'])
            reg = str(row['regime'])
            close_px, atr = float(row['close']), float(row['atr_20'])

            long_pass = (p_l >= ENTRY_THRESHOLD_LONG)
            short_pass = (p_s >= ENTRY_THRESHOLD_SHORT)
            chop_pass = (p_c < 0.50)
            
            r_dist = (1.50 * atr) / close_px if close_px > 0 else 0.0
            fee_haircut = FEE_SLIPPAGE_BPS / 10000.0
            long_ev = (((2 * p_l) - 1) * r_dist) - fee_haircut if r_dist > 0 else -1.0
            short_ev = (((2 * p_s) - 1) * r_dist) - fee_haircut if r_dist > 0 else -1.0

            if atr <= 0 or close_px <= 0:
                funnel['invalid_stale_data'] += 1
                rejections['INVALID_OR_ZERO_ATR'] += 1
            elif ticker in active_tickers:
                rejections['EXISTING_POSITION_ACTIVE'] += 1
            elif not long_pass and not short_pass:
                rejections['PROB_BELOW_BOTH_THRESHOLDS'] += 1
            else:
                funnel['passed_prob_gate'] += 1
                if not chop_pass:
                    rejections['CHOP_FILTER_ACTIVE'] += 1
                elif long_pass and reg == '2':
                    rejections['LONG_REGIME_BLOCKED'] += 1
                elif short_pass and reg == '1':
                    rejections['SHORT_REGIME_BLOCKED'] += 1
                else:
                    funnel['passed_regime_chop'] += 1
                    
                    if long_pass and (not short_pass or p_l >= p_s):
                        direction = 'LONG'
                        p_win, ev_val = p_l, long_ev
                        kelly_frac, lev = KELLY_LONG, LEVERAGE_LONG
                        net_ret = row['exact_gross_return'] - WIN_FRICTION if row['exit_reason'] == 'TP_HIT' else row['exact_gross_return'] - LOSS_FRICTION
                    else:
                        direction = 'SHORT'
                        p_win, ev_val = p_s, short_ev
                        kelly_frac, lev = KELLY_SHORT, LEVERAGE_SHORT
                        net_ret = -row['exact_gross_return'] - WIN_FRICTION if row['target_short'] == 1 else -row['exact_gross_return'] - LOSS_FRICTION

                    funnel['passed_best_direction'] += 1

                    if ev_val <= 0:
                        rejections['NEGATIVE_NET_EV'] += 1
                    else:
                        funnel['passed_positive_ev'] += 1
                        dynamic_payoff = 1.0
                        kelly_f = p_win - ((1.0 - p_win) / dynamic_payoff)
                        trade_notional_pct = min(kelly_f * kelly_frac * lev * dd_multiplier, 2.0)
                        
                        notional_comp = min(capital * trade_notional_pct, HARD_LIQUIDITY_CAP)
                        notional_fixed = min(STARTING_CAPITAL * trade_notional_pct, HARD_LIQUIDITY_CAP)
                        
                        valid_cycle_candidates.append({
                            'ticker': ticker, 'direction': direction, 'ev': ev_val,
                            'p_win': p_win, 'regime': reg, 'notional_comp': notional_comp,
                            'notional_fixed': notional_fixed, 'notional_pct': trade_notional_pct,
                            'leverage': lev, 'net_ret': net_ret, 'exit_time': row['exit_time'],
                            'exit_reason': row['exit_reason'], 'fold_name': row['fold_name'],
                            'minutes_in_trade': row['minutes_in_trade']
                        })

        # 3. Apply Portfolio Caps
        valid_cycle_candidates = sorted(valid_cycle_candidates, key=lambda x: x['ev'], reverse=True)
        trades_this_tick = 0
        
        for cand in valid_cycle_candidates:
            if len(open_positions) >= MAX_POSITIONS:
                rejections['MAX_POSITIONS_REACHED'] += 1
                continue
            funnel['passed_position_limit'] += 1
            
            if trades_this_tick >= MAX_TRADES_PER_CYCLE:
                rejections['MAX_TRADES_PER_CYCLE_REACHED'] += 1
                continue
                
            if cand['notional_comp'] >= 10.0:
                funnel['portfolio_eligible'] += 1
                funnel['passed_exposure_limit'] += 1
                funnel['final_executed_entries'] += 1
                executed_entries_count += 1
                
                open_positions.append({
                    'entry_time': ts, 'exit_time': cand['exit_time'],
                    'ticker': cand['ticker'], 'direction': cand['direction'],
                    'notional_comp': cand['notional_comp'], 'notional_fixed': cand['notional_fixed'],
                    'notional_pct': cand['notional_pct'], 'leverage': cand['leverage'],
                    'net_ret': cand['net_ret'], 'exit_reason': cand['exit_reason'],
                    'p_win': cand['p_win'], 'regime': cand['regime'],
                    'fold_name': cand['fold_name'], 'minutes_in_trade': cand['minutes_in_trade']
                })
                active_tickers.add(cand['ticker'])
                trades_this_tick += 1

    return pd.DataFrame(closed_trades), open_positions, executed_entries_count, daily_snapshots, capital, fixed_capital, max_dd, fixed_max_dd, funnel, rejections

# ============================================================================
# 6. REPORT GENERATOR & 6-WAY ATTRIBUTION MATRIX
# ============================================================================
def generate_forensic_report(trades_df, open_positions, total_entries, daily_snapshots, final_comp, final_fixed, max_dd_comp, max_dd_fixed, funnel, rejections, fold_schedule, oos_df):
    print("\n" + "="*95)
    print("                90-DAY TRUE OOS FORENSIC ATTRIBUTION & PARITY AUDIT")
    print("="*95)
    
    total_closed = len(trades_df)
    open_at_end = len(open_positions)
    
    start_date = oos_df['timestamp'].min().strftime('%Y-%m-%d')
    end_date = oos_df['timestamp'].max().strftime('%Y-%m-%d')
    
    net_comp_pct = ((final_comp / STARTING_CAPITAL) - 1.0) * 100.0
    net_fixed_pct = ((final_fixed / STARTING_CAPITAL) - 1.0) * 100.0
    
    wins = trades_df[trades_df['net_ret'] > 0]
    win_rate = (len(wins) / total_closed * 100.0) if total_closed > 0 else 0.0
    
    gross_profit_comp = trades_df[trades_df['profit_comp'] > 0]['profit_comp'].sum()
    gross_loss_comp = abs(trades_df[trades_df['profit_comp'] < 0]['profit_comp'].sum())
    pf_comp = (gross_profit_comp / gross_loss_comp) if gross_loss_comp > 0 else np.nan
    
    avg_trade_bps = trades_df['net_ret'].mean() * 10000.0
    median_trade_bps = trades_df['net_ret'].median() * 10000.0
    
    if daily_snapshots:
        d_df = pd.DataFrame(daily_snapshots).drop_duplicates('timestamp').set_index('timestamp')
        sharpe_comp = (d_df['equity_comp'].pct_change().mean() / d_df['equity_comp'].pct_change().std() * np.sqrt(365)) if d_df['equity_comp'].pct_change().std() > 0 else 0.0
        sharpe_fixed = (d_df['equity_fixed'].pct_change().mean() / d_df['equity_fixed'].pct_change().std() * np.sqrt(365)) if d_df['equity_fixed'].pct_change().std() > 0 else 0.0
    else:
        sharpe_comp, sharpe_fixed = 0.0, 0.0

    print(f"OOS TIMELINE:                {start_date}  -->  {end_date} (Latest 90 Days Available in BQ)")
    print("-" * 95)
    print(f"ACCOUNTING RECONCILIATION:")
    print(f"  ├── Executed Entries:      {total_entries}")
    print(f"  ├── Closed Trades (P&L):   {total_closed}")
    print(f"  └── Open at OOS End:       {open_at_end} (Status: In-Flight on Final 4H Bar)")
    print("-" * 95)
    print(f"COMPOUNDING VS. UNCOMPOUNDED (FIXED $1K BASE) DECOMPOSITION:")
    print(f"  ├── [COMPOUNDING KELLY]    Ending: ${final_comp:,.2f}  | Return: {net_comp_pct:+.2f}% | Max DD: -{max_dd_comp*100:.2f}% | Sharpe: {sharpe_comp:.2f}")
    print(f"  └── [FIXED $1K BASE]       Ending: ${final_fixed:,.2f}  | Return: {net_fixed_pct:+.2f}% | Max DD: -{max_dd_fixed*100:.2f}% | Sharpe: {sharpe_fixed:.2f}")
    print(f"  ==> Sizing Multiplier Effect: {final_comp / final_fixed:.2f}x growth driven by reinvesting geometric equity")
    print("-" * 95)
    print(f"PER-TRADE UNIT METRICS (PURE ALPHA INDEPENDENT OF CAPITAL):")
    print(f"  ├── Win Rate:              {win_rate:.2f}% ({len(wins)} Wins / {total_closed - len(wins)} Losses)")
    print(f"  ├── Profit Factor:         {pf_comp:.2f}")
    print(f"  ├── Average Trade Return:  {avg_trade_bps:+.1f} bps")
    print(f"  ├── Median Trade Return:   {median_trade_bps:+.1f} bps")
    print(f"  └── Avg Notional Equity %: {trades_df['notional_pct_of_equity'].mean()*100:.2f}% of Account Balance per Trade")

    # =========================================================================
    # ATTRIBUTION SECTION
    # =========================================================================
    print("\n" + "="*95)
    print("                  1. DIRECTIONAL ATTRIBUTION (LONG VS. SHORT)")
    print("="*95)
    for d in ['LONG', 'SHORT']:
        sub = trades_df[trades_df['direction'] == d]
        n = len(sub)
        wr = (sub['net_ret'] > 0).mean() * 100.0 if n > 0 else 0.0
        ev_bps = sub['net_ret'].mean() * 10000.0 if n > 0 else 0.0
        gp = sub[sub['profit_comp'] > 0]['profit_comp'].sum()
        gl = abs(sub[sub['profit_comp'] < 0]['profit_comp'].sum())
        pf = gp / gl if gl > 0 else np.nan
        pnl = sub['profit_comp'].sum()
        print(f"  {d:<6} | Trades: {n:>3} ({n/total_closed*100:.1f}%) | Win%: {wr:>5.2f}% | EV: {ev_bps:>+6.1f} bps | PF: {pf:>4.2f} | Realized P&L: ${pnl:>12,.2f}")

    print("\n" + "="*95)
    print("                  2. MACRO HMM REGIME DECOMPOSITION")
    print("="*95)
    reg_names = {'0': 'State 0 (Chop)', '1': 'State 1 (Bull Trend)', '2': 'State 2 (Cascade / High Vol)'}
    for r in ['0', '1', '2']:
        sub = trades_df[trades_df['regime'] == r]
        n = len(sub)
        wr = (sub['net_ret'] > 0).mean() * 100.0 if n > 0 else 0.0
        ev_bps = sub['net_ret'].mean() * 10000.0 if n > 0 else 0.0
        pnl = sub['profit_comp'].sum()
        print(f"  {reg_names[r]:<30} | Trades: {n:>3} ({n/total_closed*100:.1f}%) | Win%: {wr:>5.2f}% | EV: {ev_bps:>+6.1f} bps | P&L: ${pnl:>12,.2f}")

    print("\n" + "="*95)
    print("                  3. CALIBRATED PROBABILITY BUCKET AUDIT (ISOTONIC MONOTONICITY)")
    print("="*95)
    bins = [0.52, 0.55, 0.60, 0.65, 0.70, 1.00]
    labels = ['0.52 - 0.55', '0.55 - 0.60', '0.60 - 0.65', '0.65 - 0.70', '> 0.70']
    trades_df['p_bucket'] = pd.cut(trades_df['p_win'], bins=bins, labels=labels, right=False)
    for b in labels:
        sub = trades_df[trades_df['p_bucket'] == b]
        n = len(sub)
        wr = (sub['net_ret'] > 0).mean() * 100.0 if n > 0 else 0.0
        ev_bps = sub['net_ret'].mean() * 10000.0 if n > 0 else 0.0
        pnl = sub['profit_comp'].sum()
        print(f"  Bucket [{b:<11}] | Trades: {n:>3} ({n/total_closed*100:.1f}%) | Realized Win%: {wr:>5.2f}% | EV: {ev_bps:>+6.1f} bps | P&L: ${pnl:>12,.2f}")

    print("\n" + "="*95)
    print("                  4. TOP 10 TICKER CONCENTRATION AUDIT")
    print("="*95)
    print(f"  {'TICKER':<10} | {'TRADES':<8} | {'WIN RATE':<10} | {'AVG EV (bps)':<14} | {'REALIZED P&L ($)':<18} | {'P&L SHARE %'}")
    print("  " + "-"*85)
    ticker_stats = trades_df.groupby('ticker').agg(
        trades=('net_ret', 'count'),
        win_rate=('net_ret', lambda x: (x > 0).mean() * 100.0),
        avg_ev=('net_ret', lambda x: x.mean() * 10000.0),
        pnl=('profit_comp', 'sum')
    ).sort_values('pnl', ascending=False)
    
    for t_sym, row in ticker_stats.head(10).iterrows():
        pnl_share = (row['pnl'] / (final_comp - STARTING_CAPITAL)) * 100.0
        print(f"  {t_sym:<10} | {row['trades']:>8} | {row['win_rate']:>9.2f}% | {row['avg_ev']:>+13.1f} | ${row['pnl']:>16,.2f} | {pnl_share:>9.2f}%")

    print("\n" + "="*95)
    print("                  5. HOLDING TIME DURATION PROFILE")
    print("="*95)
    dur_bins = [0, 240, 720, 1440, 2880, 4320]
    dur_labels = ['< 4 Hours', '4 - 12 Hours', '12 - 24 Hours', '24 - 48 Hours', '48 - 72 Hours']
    trades_df['dur_bucket'] = pd.cut(trades_df['minutes_in_trade'], bins=dur_bins, labels=dur_labels, right=False)
    for dur in dur_labels:
        sub = trades_df[trades_df['dur_bucket'] == dur]
        n = len(sub)
        wr = (sub['net_ret'] > 0).mean() * 100.0 if n > 0 else 0.0
        ev_bps = sub['net_ret'].mean() * 10000.0 if n > 0 else 0.0
        pnl = sub['profit_comp'].sum()
        print(f"  {dur:<15} | Trades: {n:>3} ({n/total_closed*100:.1f}%) | Win%: {wr:>5.2f}% | EV: {ev_bps:>+6.1f} bps | P&L: ${pnl:>12,.2f}")

    print("\n" + "="*95)
    print("                  6. EXIT PATH RESOLUTION X DIRECTION MATRIX")
    print("="*95)
    for reason in ['TP_HIT', 'SL_HIT', 'TIMEOUT']:
        for d in ['LONG', 'SHORT']:
            sub = trades_df[(trades_df['exit_reason'] == reason) & (trades_df['direction'] == d)]
            n = len(sub)
            ev_bps = sub['net_ret'].mean() * 10000.0 if n > 0 else 0.0
            pnl = sub['profit_comp'].sum()
            print(f"  {reason:<8} [{d:<5}] | Trades: {n:>3} ({n/total_closed*100:.1f}%) | Avg Return: {ev_bps:>+7.1f} bps | Realized P&L: ${pnl:>12,.2f}")

    print("\n" + "="*95)
    print("                  7. DYNAMIC MONTHLY OOS WALK-FORWARD BREAKDOWN")
    print("="*95)
    print(f"{'Metric':<24} | {fold_schedule[0][2]:<20} | {fold_schedule[1][2]:<20} | {fold_schedule[2][2]:<20} | {'TOTAL':<12}")
    print("-" * 105)

    f_metrics = {}
    for f in fold_schedule:
        fname = f[2]
        sub = trades_df[trades_df['fold_name'] == fname]
        n = len(sub)
        w = (sub['net_ret'] > 0).mean() * 100.0 if n > 0 else 0.0
        ev_b = (sub['net_ret'].mean() * 10000.0) if n > 0 else 0.0
        pnl_d = sub['profit_comp'].sum() if n > 0 else 0.0
        f_metrics[fname] = {
            'trades': n, 'wr': w, 'ev_bps': ev_b, 'pnl': pnl_d,
            'longs': len(sub[sub['direction'] == 'LONG']),
            'shorts': len(sub[sub['direction'] == 'SHORT'])
        }

    print(f"{'Trades':<24} | {f_metrics[fold_schedule[0][2]]['trades']:>20} | {f_metrics[fold_schedule[1][2]]['trades']:>20} | {f_metrics[fold_schedule[2][2]]['trades']:>20} | {total_closed:>12}")
    print(f"{'Win Rate (%)':<24} | {f_metrics[fold_schedule[0][2]]['wr']:>19.2f}% | {f_metrics[fold_schedule[1][2]]['wr']:>19.2f}% | {f_metrics[fold_schedule[2][2]]['wr']:>19.2f}% | {win_rate:>11.2f}%")
    print(f"{'Avg Trade Return (bps)':<24} | {f_metrics[fold_schedule[0][2]]['ev_bps']:>+19.1f}  | {f_metrics[fold_schedule[1][2]]['ev_bps']:>+19.1f}  | {f_metrics[fold_schedule[2][2]]['ev_bps']:>+19.1f}  | {avg_trade_bps:>+11.1f}")
    print(f"{'Compounded P&L ($)':<24} | ${f_metrics[fold_schedule[0][2]]['pnl']:>19,.2f} | ${f_metrics[fold_schedule[1][2]]['pnl']:>19,.2f} | ${f_metrics[fold_schedule[2][2]]['pnl']:>19,.2f} | ${final_comp - STARTING_CAPITAL:>11,.2f}")
    print(f"{'Long Trades':<24} | {f_metrics[fold_schedule[0][2]]['longs']:>20} | {f_metrics[fold_schedule[1][2]]['longs']:>20} | {f_metrics[fold_schedule[2][2]]['longs']:>20} | {len(trades_df[trades_df['direction'] == 'LONG']):>12}")
    print(f"{'Short Trades':<24} | {f_metrics[fold_schedule[0][2]]['shorts']:>20} | {f_metrics[fold_schedule[1][2]]['shorts']:>20} | {f_metrics[fold_schedule[2][2]]['shorts']:>20} | {len(trades_df[trades_df['direction'] == 'SHORT']):>12}")
    print("=" * 105 + "\n")

# ============================================================================
# MAIN
# ============================================================================
def main():
    df = load_production_feature_matrix()
    df_oos, fold_schedule = execute_walk_forward_oos_scoring(df)
    trades_df, open_pos, total_entries, daily_snapshots, final_comp, final_fixed, max_dd_c, max_dd_f, funnel, rejections = simulate_forensic_portfolio(df_oos)
    generate_forensic_report(trades_df, open_pos, total_entries, daily_snapshots, final_comp, final_fixed, max_dd_c, max_dd_f, funnel, rejections, fold_schedule, df_oos)

if __name__ == "__main__":
    main()