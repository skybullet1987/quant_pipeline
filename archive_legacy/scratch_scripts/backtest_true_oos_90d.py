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
# 1. PRODUCTION POLICY CONFIGURATION (SYNCHRONIZED WITH EXECUTOR)
# ============================================================================
PROJECT_ID = "parnasa-498503"
STARTING_CAPITAL = 1000.0
MAX_POSITIONS = 5
MAX_TRADES_PER_CYCLE = 2
HARD_LIQUIDITY_CAP = 150000.0
FEE_SLIPPAGE_BPS = 15.0  # 15 bps roundtrip haircut

WIN_FRICTION = 0.0014   # 14 bps
LOSS_FRICTION = 0.0020  # 20 bps

# Asymmetric Alpha Hurdles
ENTRY_THRESHOLD_LONG = 0.58
KELLY_LONG = 0.35
LEVERAGE_LONG = 6.0

ENTRY_THRESHOLD_SHORT = 0.52
KELLY_SHORT = 0.75
LEVERAGE_SHORT = 10.0

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
    """Strictly causal expanding-window CV with a 72-hour target purge boundary."""
    def __init__(self, n_splits=4, purge_hours=72):
        self.n_splits = n_splits
        self.purge_hours = purge_hours
        
    def split(self, df):
        timestamps = np.sort(df['timestamp'].unique())
        chunk_size = len(timestamps) // (self.n_splits + 1)
        
        for i in range(1, self.n_splits + 1):
            train_end_ts = timestamps[i * chunk_size]
            val_start_ts = train_end_ts + pd.Timedelta(hours=self.purge_hours)
            
            if i == self.n_splits:
                val_end_ts = timestamps[-1] + pd.Timedelta(seconds=1)
            else:
                val_end_ts = timestamps[(i + 1) * chunk_size]
                
            train_idx = df.index[df['timestamp'] <= train_end_ts].tolist()
            val_idx = df.index[(df['timestamp'] >= val_start_ts) & (df['timestamp'] < val_end_ts)].tolist()
            
            if len(train_idx) > 0 and len(val_idx) > 0:
                yield train_idx, val_idx

# ============================================================================
# 3. DATA INGESTION FROM BIGQUERY
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
    
    # Active volatility universe filter
    df = df.dropna(subset=['exit_reason', 'exit_time', 'minutes_in_trade', 'close', 'atr_20']).fillna(0).copy()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)
    print(f"  -> Ingested {len(df):,} causal rows across {df['ticker'].nunique()} tickers.")
    return df

# ============================================================================
# 4. EXPANDING WALK-FORWARD TRAINING & OOS INFERENCE PIPELINE
# ============================================================================
def execute_walk_forward_oos_scoring(df):
    print("\n[2/4] Executing 3-Fold Expanding Walk-Forward Training & Scoring...")
    
    max_ts = df['timestamp'].max()
    oos_start_ts = max_ts - pd.Timedelta(days=90)
    
    fold_schedule = [
        (oos_start_ts, oos_start_ts + pd.Timedelta(days=30), "Fold 1 (May 16 - Jun 15)"),
        (oos_start_ts + pd.Timedelta(days=30), oos_start_ts + pd.Timedelta(days=60), "Fold 2 (Jun 15 - Jul 15)"),
        (oos_start_ts + pd.Timedelta(days=60), max_ts, "Fold 3 (Jul 15 - Aug 14)")
    ]
    
    scored_oos_blocks = []

    for fold_i, (test_start, test_end, fold_label) in enumerate(fold_schedule, 1):
        print(f"\n=======================================================")
        print(f"  TRAINING & SCORING {fold_label.upper()}")
        print(f"=======================================================")
        
        # Hard 72h Purge Embargo at Fold Boundary
        train_cutoff = test_start - pd.Timedelta(hours=72)
        df_train = df[df['timestamp'] <= train_cutoff].copy().reset_index(drop=True)
        df_test = df[(df['timestamp'] >= test_start) & (df['timestamp'] < test_end)].copy().reset_index(drop=True)
        
        print(f"  - Training Period : {df_train['timestamp'].min().strftime('%Y-%m-%d')} -> {train_cutoff.strftime('%Y-%m-%d %H:%M')} ({len(df_train):,} bars)")
        print(f"  - OOS Test Period : {test_start.strftime('%Y-%m-%d %H:%M')} -> {test_end.strftime('%Y-%m-%d %H:%M')} ({len(df_test):,} bars)")
        
        # A. Train Canonical Gaussian HMM (Sorted strictly by volatility means)
        hmm_features = ["rank_gk_vol_zscore", "rank_mom_7d", "market_breadth_sma20"]
        hmm_scaler = StandardScaler()
        scaled_train_hmm = hmm_scaler.fit_transform(df_train[hmm_features].fillna(0))
        
        hmm_model = GaussianHMM(n_components=3, covariance_type="full", n_iter=400, random_state=42).fit(scaled_train_hmm)
        state_vol = [df_train.loc[hmm_model.predict(scaled_train_hmm) == i, "rank_gk_vol_zscore"].median() for i in range(3)]
        canonical_order = np.argsort(state_vol) # 0=Chop, 1=Trend, 2=Cascade
        
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

        # B. Purged OOF Primary Expert Training
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
                
                # Fit Final Fold Models
                f_l = CatBoostClassifier(iterations=600, depth=5, learning_rate=0.03, verbose=0, random_seed=42)
                f_l.fit(df_train.loc[r_idx, all_features], df_train.loc[r_idx, 'target_long'], cat_features=all_cat_cols)
                long_experts[r_state] = f_l
                
                f_s = CatBoostClassifier(iterations=600, depth=5, learning_rate=0.03, verbose=0, random_seed=42)
                f_s.fit(df_train.loc[r_idx, all_features], df_train.loc[r_idx, 'target_short'], cat_features=all_cat_cols)
                short_experts[r_state] = f_s

        # C. Train Causal Meta-Labelers & Isotonic Calibrators
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

        # D. Predict on Unseen OOS Slice
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

    return pd.concat(scored_oos_blocks, ignore_index=True)

# ============================================================================
# 5. SIMULATION & CANDIDATE-LEVEL DECISION LEDGER
# ============================================================================
def simulate_and_audit_portfolio(df_oos):
    print("\n[3/4] Running Portfolio State Machine & Building Granular Decision Ledger...")
    
    capital = STARTING_CAPITAL
    peak_capital = capital
    max_dd = 0.0
    open_positions = []
    trade_log = []
    daily_snapshots = []
    
    candidate_ledger = []
    
    # Deep Decision Funnel Counters
    funnel = {
        'universe_evaluated': 0,
        'invalid_stale_data': 0,
        'passed_prob_gate': 0,
        'passed_regime_chop': 0,
        'passed_positive_ev': 0,
        'passed_best_direction': 0,
        'portfolio_eligible': 0,
        'passed_position_limit': 0,
        'passed_exposure_limit': 0,
        'final_executed': 0
    }
    
    rejections = {
        'SHORT_REGIME_BLOCKED': 0,
        'LONG_REGIME_BLOCKED': 0,
        'LONG_PROB_BELOW_THRESHOLD': 0,
        'SHORT_PROB_BELOW_THRESHOLD': 0,
        'PROB_BELOW_BOTH_THRESHOLDS': 0,
        'CHOP_FILTER_ACTIVE': 0,
        'NEGATIVE_NET_EV': 0,
        'EXISTING_POSITION_ACTIVE': 0,
        'MAX_POSITIONS_REACHED': 0,
        'MAX_TRADES_PER_CYCLE_REACHED': 0,
        'GROSS_EXPOSURE_LIMIT': 0,
        'INVALID_OR_ZERO_ATR': 0
    }

    all_timestamps = sorted(df_oos['timestamp'].unique())

    for ts in all_timestamps:
        # A. Process Exits
        still_open = []
        for pos in open_positions:
            if ts >= pos['exit_time']:
                profit = pos['notional'] * pos['net_ret']
                capital += profit
                if capital > peak_capital: peak_capital = capital
                
                trade_log.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': pos['exit_time'],
                    'fold_name': pos['fold_name'],
                    'ticker': pos['ticker'],
                    'direction': pos['direction'],
                    'net_ret': pos['net_ret'],
                    'profit': profit,
                    'notional': pos['notional'],
                    'exit_reason': pos['exit_reason'],
                    'p_win': pos['p_win'],
                    'capital_after': capital
                })
            else:
                still_open.append(pos)
        open_positions = still_open

        dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0.0
        if dd > max_dd: max_dd = dd
        
        if ts.hour == 0:
            daily_snapshots.append({'timestamp': ts, 'equity': capital})

        dd_multiplier = 0.25 if dd >= 0.30 else (0.50 if dd >= 0.15 else 1.0)
        
        # B. Process Candidate Signals on Current Timestamp
        bar_candidates = df_oos[df_oos['timestamp'] == ts].copy()
        funnel['universe_evaluated'] += len(bar_candidates)
        
        active_tickers = {p['ticker'] for p in open_positions}
        valid_cycle_candidates = []
        
        for _, row in bar_candidates.iterrows():
            ticker = str(row['ticker']).replace("USDT", "").replace("USD", "").upper()
            p_l, p_s, p_c = float(row['p_long']), float(row['p_short']), float(row['p_chop'])
            reg = str(row['regime'])
            close_px = float(row['close'])
            atr = float(row['atr_20'])
            tp_px = float(row['target_price_1_5_atr'])
            sl_px = float(row['stop_loss_1_5_atr'])

            # Stage Gates Tracking
            long_thresh_pass = (p_l >= ENTRY_THRESHOLD_LONG)
            short_thresh_pass = (p_s >= ENTRY_THRESHOLD_SHORT)
            chop_pass = (p_c < 0.50)
            regime_pass = not ((long_thresh_pass and reg == '2') or (short_thresh_pass and reg == '1'))
            
            # Net EV Calculations
            r_dist = (1.50 * atr) / close_px if close_px > 0 else 0.0
            fee_haircut = FEE_SLIPPAGE_BPS / 10000.0
            
            long_ev = (((2 * p_l) - 1) * r_dist) - fee_haircut if r_dist > 0 else -1.0
            short_ev = (((2 * p_s) - 1) * r_dist) - fee_haircut if r_dist > 0 else -1.0
            
            # Decision Tree
            final_decision = "REJECT"
            rejection_reason = ""
            selected_direction = None
            ev_pass = False
            p_win = 0.0
            kelly_f = 0.0
            target_notional = 0.0

            if atr <= 0 or close_px <= 0:
                funnel['invalid_stale_data'] += 1
                rejections['INVALID_OR_ZERO_ATR'] += 1
                rejection_reason = "INVALID_OR_ZERO_ATR"
            elif ticker in active_tickers:
                rejections['EXISTING_POSITION_ACTIVE'] += 1
                rejection_reason = "EXISTING_POSITION_ACTIVE"
            elif not long_thresh_pass and not short_thresh_pass:
                rejections['PROB_BELOW_BOTH_THRESHOLDS'] += 1
                rejection_reason = "PROB_BELOW_BOTH_THRESHOLDS"
            else:
                funnel['passed_prob_gate'] += 1
                
                if not chop_pass:
                    rejections['CHOP_FILTER_ACTIVE'] += 1
                    rejection_reason = "CHOP_FILTER_ACTIVE"
                elif long_thresh_pass and reg == '2':
                    rejections['LONG_REGIME_BLOCKED'] += 1
                    rejection_reason = "LONG_REGIME_BLOCKED"
                elif short_thresh_pass and reg == '1':
                    rejections['SHORT_REGIME_BLOCKED'] += 1
                    rejection_reason = "SHORT_REGIME_BLOCKED"
                else:
                    funnel['passed_regime_chop'] += 1
                    
                    # Direction Selection
                    if long_thresh_pass and (not short_thresh_pass or p_l >= p_s):
                        selected_direction = 'LONG'
                        p_win = p_l
                        ev_val = long_ev
                        kelly_frac = KELLY_LONG
                        leverage = LEVERAGE_LONG
                        net_ret = row['exact_gross_return'] - WIN_FRICTION if row['exit_reason'] == 'TP_HIT' else row['exact_gross_return'] - LOSS_FRICTION
                    else:
                        selected_direction = 'SHORT'
                        p_win = p_s
                        ev_val = short_ev
                        kelly_frac = KELLY_SHORT
                        leverage = LEVERAGE_SHORT
                        net_ret = -row['exact_gross_return'] - WIN_FRICTION if row['target_short'] == 1 else -row['exact_gross_return'] - LOSS_FRICTION

                    funnel['passed_best_direction'] += 1

                    if ev_val <= 0:
                        rejections['NEGATIVE_NET_EV'] += 1
                        rejection_reason = "NEGATIVE_NET_EV"
                    else:
                        ev_pass = True
                        funnel['passed_positive_ev'] += 1
                        
                        dynamic_payoff = 1.0
                        kelly_f = p_win - ((1.0 - p_win) / dynamic_payoff)
                        trade_notional_pct = min(kelly_f * kelly_frac * leverage * dd_multiplier, 2.0)
                        target_notional = min(capital * trade_notional_pct, HARD_LIQUIDITY_CAP)
                        
                        valid_cycle_candidates.append({
                            'ticker': ticker,
                            'direction': selected_direction,
                            'ev': ev_val,
                            'p_win': p_win,
                            'notional': target_notional,
                            'net_ret': net_ret,
                            'exit_time': row['exit_time'],
                            'exit_reason': row['exit_reason'],
                            'fold_name': row['fold_name'],
                            'row_data': row
                        })

            # Record Granular Candidate Log
            candidate_ledger.append({
                'timestamp': ts,
                'ticker': ticker,
                'fold_name': row['fold_name'],
                'p_long': p_l,
                'p_short': p_s,
                'p_chop': p_c,
                'regime': reg,
                'long_threshold_pass': long_thresh_pass,
                'short_threshold_pass': short_thresh_pass,
                'chop_pass': chop_pass,
                'regime_pass': regime_pass,
                'long_ev_bps': long_ev * 10000.0,
                'short_ev_bps': short_ev * 10000.0,
                'selected_direction': selected_direction if selected_direction else "NONE",
                'ev_pass': ev_pass,
                'final_decision': "PENDING_PORTFOLIO" if ev_pass else "REJECT",
                'rejection_reason': rejection_reason if rejection_reason else "NONE",
                'entry_price': close_px,
                'atr': atr,
                'take_profit_px': tp_px,
                'stop_loss_px': sl_px,
                'kelly_fraction': kelly_f,
                'position_size_usd': target_notional
            })

        # C. Apply Sizing & Portfolio Caps
        valid_cycle_candidates = sorted(valid_cycle_candidates, key=lambda x: x['ev'], reverse=True)
        trades_this_tick = 0
        
        for cand in valid_cycle_candidates:
            cand_ticker = cand['ticker']
            
            # Find matching candidate row in ledger to update final decision
            cand_idx = len(candidate_ledger) - len(bar_candidates) + bar_candidates.index[bar_candidates['ticker'].str.contains(cand_ticker)].tolist()[0] - bar_candidates.index[0]
            
            if len(open_positions) >= MAX_POSITIONS:
                rejections['MAX_POSITIONS_REACHED'] += 1
                candidate_ledger[cand_idx]['final_decision'] = "REJECT"
                candidate_ledger[cand_idx]['rejection_reason'] = "MAX_POSITIONS_REACHED"
                continue
                
            funnel['passed_position_limit'] += 1
            
            if trades_this_tick >= MAX_TRADES_PER_CYCLE:
                rejections['MAX_TRADES_PER_CYCLE_REACHED'] += 1
                candidate_ledger[cand_idx]['final_decision'] = "REJECT"
                candidate_ledger[cand_idx]['rejection_reason'] = "MAX_TRADES_PER_CYCLE_REACHED"
                continue
                
            if cand['notional'] >= 10.0:
                funnel['portfolio_eligible'] += 1
                funnel['passed_exposure_limit'] += 1
                funnel['final_executed'] += 1
                
                candidate_ledger[cand_idx]['final_decision'] = "EXECUTED"
                candidate_ledger[cand_idx]['rejection_reason'] = "APPROVED_PASSED_ALL_GATES"
                
                open_positions.append({
                    'entry_time': ts,
                    'exit_time': cand['exit_time'],
                    'ticker': cand['ticker'],
                    'direction': cand['direction'],
                    'notional': cand['notional'],
                    'net_ret': cand['net_ret'],
                    'exit_reason': cand['exit_reason'],
                    'p_win': cand['p_win'],
                    'fold_name': cand['fold_name']
                })
                active_tickers.add(cand['ticker'])
                trades_this_tick += 1

    ledger_df = pd.DataFrame(candidate_ledger)
    return pd.DataFrame(trade_log), daily_snapshots, capital, max_dd, funnel, rejections, ledger_df

# ============================================================================
# 6. COMPREHENSIVE REPORT GENERATION & EXPORT
# ============================================================================
def generate_audit_report(trades_df, daily_snapshots, final_capital, max_dd, funnel, rejections, ledger_df):
    print("\n" + "="*95)
    print("                     90-DAY TRUE OOS PRODUCTION ALGORITHM AUDIT")
    print("="*95)
    
    total_trades = len(trades_df)
    start_date = ledger_df['timestamp'].min().strftime('%Y-%m-%d')
    end_date = ledger_df['timestamp'].max().strftime('%Y-%m-%d')
    
    net_return_pct = ((final_capital / STARTING_CAPITAL) - 1.0) * 100.0
    cagr_proxy = ((final_capital / STARTING_CAPITAL) ** (365.0 / 90.0) - 1.0) * 100.0 if final_capital > 0 else -100.0
    
    long_trades = trades_df[trades_df['direction'] == 'LONG'] if total_trades > 0 else pd.DataFrame()
    short_trades = trades_df[trades_df['direction'] == 'SHORT'] if total_trades > 0 else pd.DataFrame()
    
    wins = trades_df[trades_df['net_ret'] > 0] if total_trades > 0 else pd.DataFrame()
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
    
    gross_profit = trades_df[trades_df['profit'] > 0]['profit'].sum() if total_trades > 0 else 0.0
    gross_loss = abs(trades_df[trades_df['profit'] < 0]['profit'].sum()) if total_trades > 0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else np.nan
    
    avg_trade_bps = (trades_df['net_ret'].mean() * 10000.0) if total_trades > 0 else 0.0
    median_trade_bps = (trades_df['net_ret'].median() * 10000.0) if total_trades > 0 else 0.0
    
    if daily_snapshots:
        d_df = pd.DataFrame(daily_snapshots).drop_duplicates('timestamp').set_index('timestamp')
        d_returns = d_df['equity'].pct_change().dropna()
        sharpe = (d_returns.mean() / d_returns.std() * np.sqrt(365)) if d_returns.std() > 0 else 0.0
    else:
        sharpe = 0.0
        
    tp_hits = len(trades_df[trades_df['exit_reason'] == 'TP_HIT']) if total_trades > 0 else 0
    sl_hits = len(trades_df[trades_df['exit_reason'] == 'SL_HIT']) if total_trades > 0 else 0
    timeouts = len(trades_df[trades_df['exit_reason'] == 'TIMEOUT']) if total_trades > 0 else 0

    print(f"OOS PERIOD:                  {start_date}  -->  {end_date}")
    print(f"Starting Equity:             ${STARTING_CAPITAL:,.2f}")
    print(f"Ending Equity:               ${final_capital:,.2f}")
    print(f"Net Realized Return:         {net_return_pct:+.2f}%")
    print(f"Annualized CAGR:             {cagr_proxy:+.2f}%")
    print("-" * 95)
    print(f"Total Trades Executed:       {total_trades}")
    print(f"  ├── Long Trades:           {len(long_trades)}")
    print(f"  └── Short Trades:          {len(short_trades)}")
    print(f"Win Rate:                    {win_rate:.2f}% ({len(wins)} / {total_trades})")
    print(f"Profit Factor:               {profit_factor:.2f}")
    print(f"Average Trade Return:        {avg_trade_bps:+.1f} bps")
    print(f"Median Trade Return:         {median_trade_bps:+.1f} bps")
    print(f"Maximum Drawdown:           -{max_dd * 100.0:.2f}%")
    print(f"Annualized Sharpe Ratio:     {sharpe:.2f}")
    print("-" * 95)
    print(f"Exit Path Resolution:")
    print(f"  ├── Take-Profit (1.5x ATR):{tp_hits:>4} ({tp_hits/max(1,total_trades)*100:.1f}%)")
    print(f"  ├── Stop-Loss   (1.5x ATR):{sl_hits:>4} ({sl_hits/max(1,total_trades)*100:.1f}%)")
    print(f"  └── 72H Timeout Limit:     {timeouts:>4} ({timeouts/max(1,total_trades)*100:.1f}%)")
    
    print("\n" + "="*95)
    print("                                   DECISION FUNNEL")
    print("="*95)
    print(f"Universe Evaluated:                  {funnel['universe_evaluated']:,}")
    print(f" │")
    print(f" ├─ Invalid / Zero ATR Data:         {funnel['invalid_stale_data']:,}")
    print(f" ├─ Passed Probability Gate:         {funnel['passed_prob_gate']:,} ({funnel['passed_prob_gate']/max(1,funnel['universe_evaluated'])*100:.1f}%)")
    print(f" ├─ Passed Regime & Chop Gates:      {funnel['passed_regime_chop']:,} ({funnel['passed_regime_chop']/max(1,funnel['universe_evaluated'])*100:.1f}%)")
    print(f" ├─ Best Direction Selected:         {funnel['passed_best_direction']:,}")
    print(f" ├─ Passed Positive Net EV:          {funnel['passed_positive_ev']:,} ({funnel['passed_positive_ev']/max(1,funnel['universe_evaluated'])*100:.1f}%)")
    print(f" ├─ Portfolio Eligible:              {funnel['portfolio_eligible']:,}")
    print(f" ├─ Passed Concurrent Position Cap:  {funnel['passed_position_limit']:,}")
    print(f" ├─ Passed Max Exposure Cap:         {funnel['passed_exposure_limit']:,}")
    print(f" └─ FINAL EXECUTED TRADES:           {funnel['final_executed']:,}")

    print("\n" + "="*95)
    print("                              REJECTION REASON BREAKDOWN")
    print("="*95)
    for reason, count in sorted(rejections.items(), key=lambda x: x[1], reverse=True):
        print(f"  {reason:<35} {count:>8,}")

    print("\n" + "="*95)
    print("                              MONTHLY OOS BREAKDOWN MATRIX")
    print("="*95)
    print(f"{'Metric':<24} | {'May 16 - Jun 15':<18} | {'Jun 15 - Jul 15':<18} | {'Jul 15 - Aug 14':<18} | {'TOTAL':<12}")
    print("-" * 105)

    folds = ["Fold 1 (May 16 - Jun 15)", "Fold 2 (Jun 15 - Jul 15)", "Fold 3 (Jul 15 - Aug 14)"]
    f_metrics = {}
    for f in folds:
        sub = trades_df[trades_df['fold_name'] == f] if total_trades > 0 else pd.DataFrame()
        n = len(sub)
        w = (sub['net_ret'] > 0).mean() * 100.0 if n > 0 else 0.0
        ev_b = (sub['net_ret'].mean() * 10000.0) if n > 0 else 0.0
        pnl_d = sub['profit'].sum() if n > 0 else 0.0
        f_metrics[f] = {
            'trades': n, 'wr': w, 'ev_bps': ev_b, 'pnl': pnl_d,
            'longs': len(sub[sub['direction'] == 'LONG']) if n > 0 else 0,
            'shorts': len(sub[sub['direction'] == 'SHORT']) if n > 0 else 0
        }

    print(f"{'Trades':<24} | {f_metrics[folds[0]]['trades']:>18} | {f_metrics[folds[1]]['trades']:>18} | {f_metrics[folds[2]]['trades']:>18} | {total_trades:>12}")
    print(f"{'Win Rate (%)':<24} | {f_metrics[folds[0]]['wr']:>17.2f}% | {f_metrics[folds[1]]['wr']:>17.2f}% | {f_metrics[folds[2]]['wr']:>17.2f}% | {win_rate:>11.2f}%")
    print(f"{'Avg Trade Return (bps)':<24} | {f_metrics[folds[0]]['ev_bps']:>+17.1f}  | {f_metrics[folds[1]]['ev_bps']:>+17.1f}  | {f_metrics[folds[2]]['ev_bps']:>+17.1f}  | {avg_trade_bps:>+11.1f}")
    print(f"{'Realized Net P&L ($)':<24} | ${f_metrics[folds[0]]['pnl']:>17,.2f} | ${f_metrics[folds[1]]['pnl']:>17,.2f} | ${f_metrics[folds[2]]['pnl']:>17,.2f} | ${final_capital - STARTING_CAPITAL:>11,.2f}")
    print(f"{'Long Trades':<24} | {f_metrics[folds[0]]['longs']:>18} | {f_metrics[folds[1]]['longs']:>18} | {f_metrics[folds[2]]['longs']:>18} | {len(long_trades):>12}")
    print(f"{'Short Trades':<24} | {f_metrics[folds[0]]['shorts']:>18} | {f_metrics[folds[1]]['shorts']:>18} | {f_metrics[folds[2]]['shorts']:>18} | {len(short_trades):>12}")
    print("=" * 105 + "\n")

    # Export Candidate-Level Parquet File
    parquet_filename = f"oos_decisions_{start_date}_{end_date}.parquet"
    ledger_df.to_parquet(parquet_filename, index=False)
    print(f"[SUCCESS] Exported {len(ledger_df):,} granular candidate decisions to: {parquet_filename}\n")

# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    df = load_production_feature_matrix()
    df_oos = execute_walk_forward_oos_scoring(df)
    trades_df, daily_snapshots, final_capital, max_dd, funnel, rejections, ledger_df = simulate_and_audit_portfolio(df_oos)
    generate_audit_report(trades_df, daily_snapshots, final_capital, max_dd, funnel, rejections, ledger_df)

if __name__ == "__main__":
    main()