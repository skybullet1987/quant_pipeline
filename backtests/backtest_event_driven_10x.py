import joblib
import numpy as np
import pandas as pd
from google.cloud import bigquery
import warnings
warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

# --- 10X LEVERAGE EVENT-DRIVEN SIMULATION ---
INITIAL_CAPITAL = 1000.0
LEVERAGE = 10.0                 # 10x Leverage on Hyperliquid
MARGIN_PER_TRADE = 0.20         # 20% margin per position (200% notional per trade)
MAX_CONCURRENT_TRADES = 5       # Max 5 open trades = 1,000% total account exposure (10x)
ROUNDTRIP_FEE = 0.0014          # 0.14% roundtrip fee + slippage on notional
ENTRY_THRESHOLD = 0.58          # Model entry threshold
MAX_CHOP_PROB = 0.50            # HMM Filter: Avoid high-chop periods

def load_data():
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
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    return df.dropna(subset=['exit_reason', 'exit_time', 'tfm_residual_24h']).reset_index(drop=True)

def main():
    # 1. Load Models & Metadata
    calibrated_model = joblib.load(f"{MODEL_DIR}/catboost_calibrated_production.pkl")
    hmm_raw = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl")
    canonical_order = joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
    all_features = joblib.load(f"{MODEL_DIR}/feature_names.pkl")
    cat_cols = joblib.load(f"{MODEL_DIR}/cat_cols.pkl")

    # 2. Prepare Data
    df = load_data()
    df['raw_atr_pct'] = df['atr_20'] / df['close']
    df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)
    df = df.dropna(subset=['return_7d'])
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)

    # Walk-forward OOS Validation (Last 15%)
    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    val_ts = timestamps[split_idx:]
    df_val = df[df['timestamp'].isin(val_ts)].copy().reset_index(drop=True)

    # 3. Macro HMM Features
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
    macro_val['hmm_entropy'] = -np.sum(np.clip(can_probs, 1e-12, 1.0) * np.log(np.clip(can_probs, 1e-12, 1.0)), axis=1)
    macro_val['hmm_regime'] = np.argmax(can_probs, axis=1).astype(str)

    df_val = pd.merge(df_val, macro_val, left_on='timestamp', right_index=True, how='left')

    # 4. Predict P(TP)
    X_val = df_val[all_features].copy()
    for col in cat_cols:
        X_val[col] = X_val[col].astype('category').cat.codes
    df_val['p_tp'] = calibrated_model.predict_proba(X_val)[:, 1]

    # 5. Build Chronological Event Queue
    events = []
    order_id = 0
    for idx, row in df_val.iterrows():
        if row['p_tp'] >= ENTRY_THRESHOLD and row['hmm_p_chop'] <= MAX_CHOP_PROB:
            order_id += 1
            events.append({'time': row['timestamp'], 'type': 'ENTRY', 'id': order_id, 'data': row})
            events.append({'time': row['exit_time'], 'type': 'EXIT', 'id': order_id, 'data': row})

    # Sort events strictly by time. If timestamps match, process EXITS first to free up margin.
    events.sort(key=lambda x: (x['time'], 0 if x['type'] == 'EXIT' else 1))

    # 6. Simulation State Variables
    capital = INITIAL_CAPITAL
    peak_capital = capital
    max_dd = 0.0
    open_trades = {}
    trades_executed = 0
    wins = 0

    print("Running 10x Leverage Event-Driven Backtest (Chronological Queue)...")
    
    for ev in events:
        if capital <= 10.0:
            print("\n[LIQUIDATION] Account equity dropped below $10. Simulation halted.")
            break

        if ev['type'] == 'ENTRY':
            # Respect max capacity limit
            if len(open_trades) < MAX_CONCURRENT_TRADES:
                # 20% margin * 10x leverage = 200% notional position
                margin = capital * MARGIN_PER_TRADE
                notional_size = margin * LEVERAGE
                open_trades[ev['id']] = notional_size
                trades_executed += 1

        elif ev['type'] == 'EXIT':
            if ev['id'] in open_trades:
                notional_size = open_trades.pop(ev['id'])
                row = ev['data']
                
                # PnL at 10x leverage
                if row['exit_reason'] == 'TP_HIT':
                    gross_pnl = notional_size * 0.02  # +2% price move = +20% on allocated margin
                    wins += 1
                elif row['exit_reason'] == 'SL_HIT':
                    gross_pnl = -notional_size * 0.01 # -1% price move = -10% on allocated margin
                else:
                    gross_pnl = 0.0

                friction = notional_size * ROUNDTRIP_FEE
                net_pnl = gross_pnl - friction
                capital += net_pnl

                if capital > peak_capital:
                    peak_capital = capital
                dd = (capital - peak_capital) / peak_capital
                if dd < max_dd:
                    max_dd = dd

    win_rate = (wins / trades_executed * 100) if trades_executed > 0 else 0

    print("\n=========================================================")
    print("      10X LEVERAGE EVENT-DRIVEN BACKTEST RESULTS         ")
    print("=========================================================")
    print(f" Initial Capital      : ${INITIAL_CAPITAL:,.2f}")
    print(f" Final Capital        : ${capital:,.2f}")
    print(f" Net Return           : {((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100:+.2f}%")
    print("---------------------------------------------------------")
    print(f" Total Trades Executed: {trades_executed}")
    print(f" Max Concurrent Trades: {MAX_CONCURRENT_TRADES} (10x Max Portfolio Notional)")
    print(f" Win Rate             : {win_rate:.2f}%")
    print(f" Max Drawdown         : {max_dd * 100:.2f}%")
    print("=========================================================\n")

if __name__ == "__main__":
    main()
