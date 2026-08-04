import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
import warnings

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
PURGE_BARS = 18 

TAKER_FEE = 0.0026
MAKER_FEE = 0.0016
SLIPPAGE = 0.0005
WIN_FRICTION = TAKER_FEE + SLIPPAGE + MAKER_FEE
LOSS_FRICTION = TAKER_FEE + SLIPPAGE + TAKER_FEE + SLIPPAGE

CAT_COLS = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend', 'market_session', 'btc_above_sma50', 'hmm_regime']
FEATURE_COLS = [
    'market_breadth_sma20', 'top_breakout_breadth', 'pos_bar_count_6p',
    'candle_body_pct', 'candle_upper_wick_pct', 'candle_lower_wick_pct',
    'rank_eth_btc_spread_20p', 'rank_btc_dominance_spread',
    'rank_gk_vol_20p', 'rank_vol_term_structure', 'rank_gk_vol_zscore', 'rank_vol_compression_ratio',
    'rank_mom_24h', 'rank_mom_7d', 'rank_mom_accel_24h', 'rank_mom_ratio_24h_7d',
    'rank_dist_to_120p_high', 'rank_relative_vol_120p', 'rank_rolling_sharpe_20p', 'rank_atr_pct_20'
]

CB_PARAMS = {
    'iterations': 800, 'learning_rate': 0.05, 'depth': 5, 
    'l2_leaf_reg': 5.0, 'random_strength': 5.0, 
    'auto_class_weights': 'Balanced', 'verbose': 0, 'random_seed': 42
}

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

def main():
    print("1. Ingesting Data & Formatting Pure Macro Features...")
    df = load_data()
    df['raw_atr_pct'] = df['atr_20'] / df['close']
    df = df.sort_values(['ticker', 'timestamp'])
    df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)
    df = df.dropna(subset=['return_7d']).copy()
    
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)
    df['target'] = (df['exit_reason'] == 'TP_HIT').astype(int)

    # Expanding Window Parameters
    INITIAL_TRAIN_DAYS = 365 * 2 # Start with a 2-year foundation
    TEST_DAYS = 30               # Step forward 1 month at a time
    
    min_date = df['timestamp'].min()
    max_date = df['timestamp'].max()
    
    current_train_end = min_date + pd.Timedelta(days=INITIAL_TRAIN_DAYS)
    oos_predictions = []
    
    print(f"\n========================================================")
    print(f"   STARTING EXPANDING WINDOW WALK-FORWARD ENGINE")
    print(f"========================================================")

    step = 1
    while current_train_end + pd.Timedelta(hours=4 * PURGE_BARS) + pd.Timedelta(days=TEST_DAYS) <= max_date:
        test_start = current_train_end + pd.Timedelta(hours=4 * PURGE_BARS)
        test_end = test_start + pd.Timedelta(days=TEST_DAYS)
        
        # THE FIX: Training always starts at min_date (keeps all history)
        train_df = df[(df['timestamp'] >= min_date) & (df['timestamp'] < current_train_end)].copy()
        test_df = df[(df['timestamp'] >= test_start) & (df['timestamp'] < test_end)].copy()
        
        print(f"Step {step}: Train [{min_date.date()} to {current_train_end.date()}] -> Predict [{test_start.date()} to {test_end.date()}]")
        
        macro_train = train_df.groupby('timestamp').agg(
            macro_breadth=('market_breadth_sma20', 'first'), macro_volatility=('raw_atr_pct', 'median'), macro_momentum=('return_7d', 'median')
        ).sort_index()
        hmm_features = ['macro_breadth', 'macro_volatility', 'macro_momentum']
        hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
        hmm.fit(macro_train[hmm_features].values)
        
        train_df = pd.merge(train_df, macro_train, left_on='timestamp', right_index=True, how='left')
        train_df['hmm_regime'] = hmm.predict(train_df[hmm_features].values).astype(str)
        
        macro_test = test_df.groupby('timestamp').agg(
            macro_breadth=('market_breadth_sma20', 'first'), macro_volatility=('raw_atr_pct', 'median'), macro_momentum=('return_7d', 'median')
        ).sort_index()
        test_df = pd.merge(test_df, macro_test, left_on='timestamp', right_index=True, how='left')
        test_df['hmm_regime'] = hmm.predict(test_df[hmm_features].values).astype(str)

        for col in CAT_COLS:
            train_df[col] = train_df[col].astype(str)
            test_df[col] = test_df[col].astype(str)

        train_df['primary_prob'] = 0.0
        test_df['primary_prob'] = 0.0
        
        for regime in ['0', '1', '2']:
            r_idx_tr = train_df[train_df['hmm_regime'] == regime].index
            r_idx_te = test_df[test_df['hmm_regime'] == regime].index
            
            if len(r_idx_tr) > 100 and train_df.loc[r_idx_tr, 'target'].nunique() > 1:
                model = CatBoostClassifier(**CB_PARAMS)
                model.fit(train_df.loc[r_idx_tr, FEATURE_COLS + CAT_COLS], train_df.loc[r_idx_tr, 'target'], cat_features=CAT_COLS)
                if len(r_idx_te) > 0:
                    test_df.loc[r_idx_te, 'primary_prob'] = model.predict_proba(test_df.loc[r_idx_te, FEATURE_COLS + CAT_COLS])[:, 1]
                train_df.loc[r_idx_tr, 'primary_prob'] = model.predict_proba(train_df.loc[r_idx_tr, FEATURE_COLS + CAT_COLS])[:, 1]

        train_df['prob_conviction'] = abs(train_df['primary_prob'] - 0.50)
        train_df['prob_x_vol'] = train_df['primary_prob'] * train_df['rank_gk_vol_zscore']
        train_df['prob_x_mom'] = train_df['primary_prob'] * train_df['rank_mom_24h']
        
        meta_features = ['primary_prob', 'prob_conviction', 'prob_x_vol', 'prob_x_mom', 'rank_gk_vol_zscore', 'rank_relative_vol_120p', 'rank_atr_pct_20', 'market_breadth_sma20']
        
        meta_tr = train_df[train_df['primary_prob'] > 0.50].copy()
        test_df['meta_prob'] = 0.0
        
        if len(meta_tr) > 50 and meta_tr['target'].nunique() > 1:
            meta = CatBoostClassifier(iterations=300, depth=4, learning_rate=0.03, verbose=0, random_seed=42)
            meta.fit(meta_tr[meta_features], meta_tr['target'])
            
            test_df['prob_conviction'] = abs(test_df['primary_prob'] - 0.50)
            test_df['prob_x_vol'] = test_df['primary_prob'] * test_df['rank_gk_vol_zscore']
            test_df['prob_x_mom'] = test_df['primary_prob'] * test_df['rank_mom_24h']
            
            meta_te_idx = test_df[test_df['primary_prob'] > 0.50].index
            if len(meta_te_idx) > 0:
                test_df.loc[meta_te_idx, 'meta_prob'] = meta.predict_proba(test_df.loc[meta_te_idx, meta_features])[:, 1]
        
        oos_predictions.append(test_df)
        # Advance the training end date by 1 month
        current_train_end += pd.Timedelta(days=TEST_DAYS)
        step += 1

    print(f"\n========================================================")
    print(f"   WALK-FORWARD EVALUATION (STITCHED OOS)")
    print(f"========================================================")
    
    if len(oos_predictions) == 0:
        print("Not enough data to run expanding window.")
        return

    final_df = pd.concat(oos_predictions, ignore_index=True)
    raw_atr_pct = final_df['atr_20'] / final_df['close']
    prob_win = final_df['meta_prob']
    
    final_df['expected_value'] = (prob_win * (1.50 * raw_atr_pct)) + ((1 - prob_win) * (-1.50 * raw_atr_pct)) - ((prob_win * WIN_FRICTION) + ((1 - prob_win) * LOSS_FRICTION))

    valid_setups = final_df[final_df['expected_value'] > 0].copy()
    if len(valid_setups) == 0:
        print("No positive EV setups found across all walk-forward windows.")
        return

    for threshold in [0.0, 0.001, 0.002]:
        signals = valid_setups[valid_setups['expected_value'] > threshold].copy()
        signals = signals.sort_values(by=['timestamp', 'expected_value'], ascending=[True, False]).reset_index(drop=True)
        
        raw_atr_pct_sig = signals['atr_20'] / signals['close']
        fair_loss = np.clip(signals['exact_gross_return'], -1.50 * raw_atr_pct_sig, 0.0)
        signals['gross_ret'] = np.where(signals['exit_reason'] == 'TP_HIT', 1.50 * raw_atr_pct_sig, fair_loss)
        signals['net_ret'] = np.where(signals['exit_reason'] == 'TP_HIT', signals['gross_ret'] - WIN_FRICTION, signals['gross_ret'] - LOSS_FRICTION)

        cap = 10000.0
        hist = []
        for date, day_data in signals.groupby(signals['timestamp'].dt.date):
            day_data = day_data.nlargest(5, 'expected_value')
            ret = (day_data['net_ret'] * (0.20 / len(day_data))).sum()
            cap *= (1 + ret)
            hist.append({'date': date, 'ret': ret, 'cap': cap})
            
        port = pd.DataFrame(hist)
        if len(port) > 0:
            yrs = max((port['date'].iloc[-1] - port['date'].iloc[0]).days / 365.25, 0.1)
            cagr = (cap / 10000.0) ** (1 / yrs) - 1
            max_dd = ((port['cap'] - port['cap'].cummax()) / port['cap'].cummax()).min()
            win_rate = (signals['net_ret'] > 0).mean()
            
            print(f"--- Expanding Window Trades (EV > {threshold*100:.2f}%) ---")
            print(f"  Total Trades: {len(signals)} | Win Rate: {win_rate:.2%}")
            print(f"  Final Capital: ${cap:,.2f} | CAGR: {cagr:.2%} | Max DD: {max_dd:.2%}\n")

if __name__ == "__main__":
    main()
