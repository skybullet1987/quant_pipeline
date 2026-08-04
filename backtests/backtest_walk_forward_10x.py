import joblib
import numpy as np
import pandas as pd
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from catboost import CatBoostClassifier
from sklearn.calibration import CalibratedClassifierCV
import warnings
warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

# --- SIMULATION PARAMETERS ---
INITIAL_CAPITAL = 1000.0
LEVERAGE = 10.0
MARGIN_PER_TRADE = 0.20
MAX_CONCURRENT_TRADES = 5
ROUNDTRIP_FEE = 0.0014
FUNDING_RATE_PER_8H = 0.0001  # 0.01% per 8h
ENTRY_THRESHOLD = 0.58
MAX_CHOP_PROB = 0.50

def load_data():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*, 
            p.exit_time, p.exit_reason, 
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
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    return df.dropna(subset=['exit_reason', 'exit_time', 'tfm_residual_24h']).reset_index(drop=True)

def main():
    print("=================================================================")
    print("      BUILDING DYNAMIC WALK-FORWARD ML QUEUE (3 FOLDS)           ")
    print("=================================================================")

    all_features = joblib.load(f"{MODEL_DIR}/feature_names.pkl")
    cat_cols = joblib.load(f"{MODEL_DIR}/cat_cols.pkl")
    best_params = joblib.load(f"{MODEL_DIR}/best_params.pkl")
    
    best_params.update({'loss_function': 'Logloss', 'eval_metric': 'AUC', 'verbose': False, 'random_seed': 42})

    df = load_data()
    df['raw_atr_pct'] = df['atr_20'] / df['close']
    df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)
    df = df.dropna(subset=['return_7d'])
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)

    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    oos_ts = timestamps[split_idx:]
    
    # Split OOS into 3 chunks for Walk-Forward Validation
    chunk_size = len(oos_ts) // 3
    folds = [
        oos_ts[0 : chunk_size],
        oos_ts[chunk_size : chunk_size*2],
        oos_ts[chunk_size*2 :]
    ]

    all_predictions = []

    for fold_idx, val_ts in enumerate(folds):
        print(f"-> Retraining Model for Fold {fold_idx + 1}/3 (Val Start: {val_ts[0].strftime('%Y-%m-%d')})")
        
        current_train_ts = timestamps[timestamps < val_ts[0]]
        df_train = df[df['timestamp'].isin(current_train_ts)].copy()
        df_val = df[df['timestamp'].isin(val_ts)].copy()

        # 1. Retrain HMM dynamically
        macro_train = df_train.groupby('timestamp').agg(
            macro_breadth=('market_breadth_sma20', 'first'), macro_volatility=('raw_atr_pct', 'median'),
            macro_momentum=('return_7d', 'median'), macro_surprise=('tfm_residual_24h', 'median')
        ).sort_index()

        hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)
        hmm.fit(macro_train.values)
        canonical_order = np.argsort(hmm.means_[:, 1])

        # HMM on Train
        train_probs = hmm.predict_proba(macro_train.values)[:, canonical_order]
        macro_train['hmm_p_chop'], macro_train['hmm_p_trend'], macro_train['hmm_p_cascade'] = train_probs[:,0], train_probs[:,1], train_probs[:,2]
        macro_train['hmm_entropy'] = -np.sum(np.clip(train_probs, 1e-12, 1.0) * np.log(np.clip(train_probs, 1e-12, 1.0)), axis=1)
        macro_train['hmm_regime'] = np.argmax(train_probs, axis=1).astype(str)
        df_train = pd.merge(df_train, macro_train[['hmm_p_chop', 'hmm_p_trend', 'hmm_p_cascade', 'hmm_entropy', 'hmm_regime']], left_on='timestamp', right_index=True)

        # HMM on Val
        macro_val = df_val.groupby('timestamp').agg(
            macro_breadth=('market_breadth_sma20', 'first'), macro_volatility=('raw_atr_pct', 'median'),
            macro_momentum=('return_7d', 'median'), macro_surprise=('tfm_residual_24h', 'median')
        ).sort_index()
        val_probs = hmm.predict_proba(macro_val.values)[:, canonical_order]
        macro_val['hmm_p_chop'], macro_val['hmm_p_trend'], macro_val['hmm_p_cascade'] = val_probs[:,0], val_probs[:,1], val_probs[:,2]
        macro_val['hmm_entropy'] = -np.sum(np.clip(val_probs, 1e-12, 1.0) * np.log(np.clip(val_probs, 1e-12, 1.0)), axis=1)
        macro_val['hmm_regime'] = np.argmax(val_probs, axis=1).astype(str)
        df_val = pd.merge(df_val, macro_val[['hmm_p_chop', 'hmm_p_trend', 'hmm_p_cascade', 'hmm_entropy', 'hmm_regime']], left_on='timestamp', right_index=True)

        # 2. Encode all categorical columns AFTER HMM merge
        for col in cat_cols:
            if col in df_train.columns:
                df_train[col] = df_train[col].astype('category').cat.codes
            if col in df_val.columns:
                df_val[col] = df_val[col].astype('category').cat.codes

        # 3. Retrain & Calibrate CatBoost
        base_model = CatBoostClassifier(**best_params)
        calibrated_model = CalibratedClassifierCV(estimator=base_model, method='isotonic', cv=3)
        
        X_train = df_train[all_features].copy()
        y_train = (df_train['exit_reason'] == 'TP_HIT').astype(int)
        calibrated_model.fit(X_train, y_train)

        # 4. Predict Validation Chunk
        X_val = df_val[all_features].copy()
        df_val['p_tp'] = calibrated_model.predict_proba(X_val)[:, 1]
        all_predictions.append(df_val)

    # --- EVENT DRIVEN QUEUE ---
    print("\n=================================================================")
    print("      RUNNING 10X EVENT-DRIVEN EXECUTION WITH FUNDING DRAG       ")
    print("=================================================================")
    
    df_final = pd.concat(all_predictions).reset_index(drop=True)
    events = []
    order_id = 0
    for idx, row in df_final.iterrows():
        if row['p_tp'] >= ENTRY_THRESHOLD and row['hmm_p_chop'] <= MAX_CHOP_PROB:
            order_id += 1
            events.append({'time': row['timestamp'], 'type': 'ENTRY', 'id': order_id, 'data': row})
            events.append({'time': row['exit_time'], 'type': 'EXIT', 'id': order_id, 'data': row})

    events.sort(key=lambda x: (x['time'], 0 if x['type'] == 'EXIT' else 1))

    capital = INITIAL_CAPITAL
    peak_capital = capital
    max_dd = 0.0
    open_trades = {}
    trades_executed = 0
    wins = 0
    total_funding_paid = 0.0

    for ev in events:
        if capital <= 10.0:
            print("\n[LIQUIDATION] Capital dropped below $10. Simulation halted.")
            break

        if ev['type'] == 'ENTRY':
            if len(open_trades) < MAX_CONCURRENT_TRADES:
                margin = capital * MARGIN_PER_TRADE
                notional_size = margin * LEVERAGE
                open_trades[ev['id']] = {'size': notional_size, 'entry_time': ev['time']}
                trades_executed += 1

        elif ev['type'] == 'EXIT':
            if ev['id'] in open_trades:
                trade = open_trades.pop(ev['id'])
                notional_size = trade['size']
                row = ev['data']
                
                # Calculate Holding Time & Funding Fee
                hours_held = (ev['time'] - trade['entry_time']).total_seconds() / 3600.0
                funding_intervals = max(1, hours_held / 8.0)
                funding_fee = notional_size * (FUNDING_RATE_PER_8H * funding_intervals)
                total_funding_paid += funding_fee
                
                if row['exit_reason'] == 'TP_HIT':
                    gross_pnl = notional_size * 0.02
                    wins += 1
                elif row['exit_reason'] == 'SL_HIT':
                    gross_pnl = -notional_size * 0.01
                else:
                    gross_pnl = 0.0

                friction = notional_size * ROUNDTRIP_FEE
                net_pnl = gross_pnl - friction - funding_fee
                capital += net_pnl

                if capital > peak_capital:
                    peak_capital = capital
                dd = (capital - peak_capital) / peak_capital
                if dd < max_dd:
                    max_dd = dd

    win_rate = (wins / trades_executed * 100) if trades_executed > 0 else 0

    print(f" Final Capital        : ${capital:,.2f}")
    print(f" Net Return           : {((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100:+.2f}%")
    print(f" Total Trades Executed: {trades_executed}")
    print(f" Win Rate             : {win_rate:.2f}%")
    print(f" Max Drawdown         : {max_dd * 100:.2f}%")
    print(f" Total Funding Paid   : ${total_funding_paid:,.2f}")
    print("=================================================================\n")

if __name__ == "__main__":
    main()
