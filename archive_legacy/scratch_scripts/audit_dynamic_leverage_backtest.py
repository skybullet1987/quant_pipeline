import os, joblib, requests, warnings
import pandas as pd
import numpy as np
from google.cloud import bigquery
from catboost import CatBoostClassifier

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

ENTRY_THRESHOLD_SHORT, ENTRY_THRESHOLD_LONG = 0.52, 0.58
KELLY_FRACTION_SHORT, KELLY_FRACTION_LONG = 0.50, 0.20
MAX_CONCURRENT_POSITIONS = 5
HARD_LIQUIDITY_CAP = 150000.0
WIN_FRICTION, LOSS_FRICTION = 0.0014, 0.0020
MAINTENANCE_MARGIN_BUFFER = 0.05

def get_hyperliquid_max_leverage():
    try:
        resp = requests.post('https://api.hyperliquid.xyz/info', json={"type": "meta"}, timeout=10)
        meta = resp.json()
        return {asset['name']: asset['maxLeverage'] for asset in meta['universe']}
    except Exception as e:
        print(f"Warning: Could not fetch HL meta: {e}")
        return {}

def main():
    print("=====================================================================")
    print("  SIMULATING DYNAMIC PLATFORM LEVERAGE BACKTEST (5-YEAR OOS)")
    print("=====================================================================")
    
    hl_max_lev_map = get_hyperliquid_max_leverage()
    client = bigquery.Client(project=PROJECT_ID)
    
    print("Fetching exact historical path outcomes & full feature set...")
    query = f"""
        SELECT 
            f.*, 
            t.* EXCEPT (ticker, timestamp),
            l.* EXCEPT (ticker, timestamp),
            p.target_price_1_5_atr, p.stop_loss_1_5_atr,
            p.target_short, p.target_long, p.minutes_in_trade
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.ticker = p.ticker AND f.timestamp = p.signal_time
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t 
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l 
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Load Models & Feature Maps
    hmm_model, hmm_scaler = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl"), joblib.load(f"{MODEL_DIR}/hmm_scaler.pkl")
    hmm_features, canonical_order = joblib.load(f"{MODEL_DIR}/hmm_feature_names.pkl"), joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
    meta_long, cal_long = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_long.cbm"), joblib.load(f"{MODEL_DIR}/meta_calibrator_long.pkl")
    meta_short, cal_short = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_short.cbm"), joblib.load(f"{MODEL_DIR}/meta_calibrator_short.pkl")
    all_cat_cols, all_features = joblib.load(f"{MODEL_DIR}/cat_cols.pkl"), joblib.load(f"{MODEL_DIR}/feature_names.pkl")

    # Align columns and ensure no missing features cause KeyErrors
    for col in all_features:
        if col not in df.columns:
            df[col] = 0.0
    for col in hmm_features:
        if col not in df.columns:
            df[col] = 0.0

    df = df.fillna(0)

    # Score HMM & Models
    scaled_x = hmm_scaler.transform(df[hmm_features].fillna(0))
    can_probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
    df['hmm_p_chop'], df['hmm_regime'] = can_probs[:, 0], can_probs.argmax(axis=1).astype(str)
    for col in all_cat_cols: df[col] = df[col].astype(str)

    df['primary_prob_short'] = 0.0
    for regime in ['0', '1', '2']:
        m_s_path = f"{MODEL_DIR}/regime_{regime}_short_expert.cbm"
        idx = df[df['hmm_regime'] == regime].index
        if len(idx) > 0 and os.path.exists(m_s_path):
            df.loc[idx, 'primary_prob_short'] = CatBoostClassifier().load_model(m_s_path).predict_proba(df.loc[idx, all_features])[:, 1]

    df['calibrated_prob_short'] = cal_short.predict(meta_short.predict_proba(df[meta_short.feature_names_])[:, 1])

    # Filter to valid trade triggers
    df_triggers = df[(df['hmm_p_chop'] < 0.50) & (df['hmm_regime'] != '0') & (df['calibrated_prob_short'] >= ENTRY_THRESHOLD_SHORT)].copy()
    
    def run_simulation(mode="fixed"):
        capital = 1000.0
        peak_capital = capital
        max_dd = 0.0
        trades_executed = 0
        wins = 0
        
        for _, row in df_triggers.iterrows():
            coin = str(row['ticker']).replace("USDT", "").replace("USD", "").upper()
            entry_price, atr = float(row['close']), float(row['atr_20'])
            p_s = float(row['calibrated_prob_short'])
            
            # Determine Leverage
            if mode == "fixed":
                lev = 10.0
            else:
                exchange_max = hl_max_lev_map.get(coin, 5)
                sl_pct = (1.5 * atr) / entry_price if entry_price > 0 else 0.05
                math_max = int((1.0 - MAINTENANCE_MARGIN_BUFFER) / sl_pct) if sl_pct > 0 else exchange_max
                lev = max(1, min(exchange_max, math_max))

            dd_pct = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0
            dd_multi = 0.25 if dd_pct >= 0.30 else (0.50 if dd_pct >= 0.15 else 1.0)

            tp_s, sl_s = entry_price - (1.50 * atr), entry_price + (1.50 * atr)
            net_win = ((entry_price - tp_s)/entry_price) - WIN_FRICTION
            net_loss = ((sl_s - entry_price)/entry_price) + LOSS_FRICTION
            
            dynamic_payoff = net_win / net_loss
            kelly_f = p_s - ((1 - p_s) / dynamic_payoff)
            trade_notional_pct = min(kelly_f * KELLY_FRACTION_SHORT * lev * dd_multi, 2.0)
            notional_size = min(capital * trade_notional_pct, HARD_LIQUIDITY_CAP)
            
            if notional_size < 12.0: continue

            # Outcome
            is_win = (row['target_short'] == 1)
            trades_executed += 1
            if is_win:
                wins += 1
                pnl = notional_size * net_win
            else:
                pnl = -notional_size * net_loss
                
            capital += pnl
            if capital > peak_capital: peak_capital = capital
            current_dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0
            if current_dd > max_dd: max_dd = current_dd

        win_rate = (wins / trades_executed * 100) if trades_executed > 0 else 0
        return capital, trades_executed, win_rate, max_dd

    cap_fixed, trades_fixed, wr_fixed, dd_fixed = run_simulation(mode="fixed")
    cap_dyn, trades_dyn, wr_dyn, dd_dyn = run_simulation(mode="dynamic")

    print("\n------------------- BACKTEST COMPARISON RESULTS -------------------")
    print(f"{'Metric':<25} | {'Fixed 10x Baseline':<20} | {'Dynamic Platform Lev':<20}")
    print("-" * 70)
    print(f"{'Final Equity ($1k Start)':<25} | ${cap_fixed:>18,.2f} | ${cap_dyn:>18,.2f}")
    print(f"{'Total Trades Executed':<25} | {trades_fixed:>20,} | {trades_dyn:>20,}")
    print(f"{'Win Rate':<25} | {wr_fixed:>19.2f}% | {wr_dyn:>19.2f}%")
    print(f"{'Maximum Drawdown':<25} | -{dd_fixed*100:>18.2f}% | -{dd_dyn*100:>18.2f}%")
    print("=====================================================================")

if __name__ == "__main__":
    main()
