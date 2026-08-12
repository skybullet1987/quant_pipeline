import os
import time
import datetime
import uuid
import joblib
import warnings
import numpy as np
import pandas as pd
from google.cloud import bigquery
from catboost import CatBoostClassifier

from execution.base_executor import Order
from execution.paper_executor import PaperExecutionEngine

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

ENTRY_THRESHOLD = 0.55
MAX_CHOP_PROB = 0.60
MAX_CONCURRENT_POSITIONS = 5
KELLY_FRACTION = 0.50
MAX_NOTIONAL_PER_TRADE = 2.0
HARD_LIQUIDITY_CAP = 150000.0
LEVERAGE = 10.0

WIN_FRICTION = 0.0014
LOSS_FRICTION = 0.0020

def load_latest_features():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        WITH latest_ts AS (
            SELECT MAX(timestamp) as max_ts 
            FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`
        )
        SELECT 
            f.*,
            t.tfm_ret_24h, t.tfm_ret_72h, t.tfm_slope, t.tfm_uncertainty, t.tfm_residual_24h, t.tfm_conviction_delta,
            COALESCE(l.total_liq_usd, 0) AS total_liq_usd,
            COALESCE(l.liq_imbalance_ratio, 0) AS liq_imbalance_ratio,
            COALESCE(l.long_liq_accel, 0) AS long_liq_accel,
            COALESCE(l.short_liq_accel, 0) AS short_liq_accel,
            COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        CROSS JOIN latest_ts
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        WHERE f.timestamp = latest_ts.max_ts
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['close', 'atr_20']).fillna(0).reset_index(drop=True)

def main():
    print("=================================================================")
    print("     DEGEN MODE: 10X DUAL-DIRECTIONAL HYPERLIQUID DAEMON        ")
    print("=================================================================")

    hmm_model = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{MODEL_DIR}/hmm_scaler.pkl")
    hmm_features = joblib.load(f"{MODEL_DIR}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
    
    meta_long = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_long.cbm")
    cal_long = joblib.load(f"{MODEL_DIR}/meta_calibrator_long.pkl")
    meta_short = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_short.cbm")
    cal_short = joblib.load(f"{MODEL_DIR}/meta_calibrator_short.pkl")
    
    all_cat_cols = joblib.load(f"{MODEL_DIR}/cat_cols.pkl")
    all_features = joblib.load(f"{MODEL_DIR}/feature_names.pkl")

    engine = PaperExecutionEngine(initial_capital=1000.0, db_path="live_execution_telemetry.db")
    print(f"Paper Account Balance Initialized: ${engine.get_account_equity():,.2f}")

    iteration = 0
    while True:
        iteration += 1
        now = datetime.datetime.now(datetime.timezone.utc)
        print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S UTC')}] --- Iteration #{iteration} ---")

        try:
            df = load_latest_features()
            if df.empty:
                print("No new candle features available in BigQuery. Waiting...")
                time.sleep(60)
                continue

            ticker_market_data = {
                row['ticker']: {
                    'open': float(row['close']),
                    'high': float(row['close'] * (1 + abs(row['atr_20']/row['close']))),
                    'low': float(row['close'] * (1 - abs(row['atr_20']/row['close']))),
                    'close': float(row['close'])
                } for _, row in df.iterrows()
            }
            fills = engine.process_market_update(now, ticker_market_data)
            if fills:
                print(f"Processed {len(fills)} Fills/Exits!")

            scaled_x = hmm_scaler.transform(df[hmm_features].fillna(0))
            can_probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
            
            df['hmm_p_chop'] = can_probs[:, 0]
            df['hmm_p_trend'] = can_probs[:, 1]
            df['hmm_p_cascade'] = can_probs[:, 2]
            df['hmm_regime'] = can_probs.argmax(axis=1).astype(str)

            for col in all_cat_cols: df[col] = df[col].astype(str)

            df['primary_prob_long'] = 0.0
            df['primary_prob_short'] = 0.0

            for regime in ['0', '1', '2']:
                m_l_path = f"{MODEL_DIR}/regime_{regime}_long_expert.cbm"
                m_s_path = f"{MODEL_DIR}/regime_{regime}_short_expert.cbm"
                regime_idx = df[df['hmm_regime'] == regime].index
                
                if len(regime_idx) > 0 and os.path.exists(m_l_path):
                    exp_l = CatBoostClassifier().load_model(m_l_path)
                    df.loc[regime_idx, 'primary_prob_long'] = exp_l.predict_proba(df.loc[regime_idx, all_features])[:, 1]
                if len(regime_idx) > 0 and os.path.exists(m_s_path):
                    exp_s = CatBoostClassifier().load_model(m_s_path)
                    df.loc[regime_idx, 'primary_prob_short'] = exp_s.predict_proba(df.loc[regime_idx, all_features])[:, 1]

            df['calibrated_prob_long'] = cal_long.predict(meta_long.predict_proba(df[meta_long.feature_names_])[:, 1])
            df['calibrated_prob_short'] = cal_short.predict(meta_short.predict_proba(df[meta_short.feature_names_])[:, 1])

            current_capital = engine.get_account_equity()

            for idx, cand in df.iterrows():
                symbol = cand['ticker']
                if symbol in [p['order'].symbol for p in engine.get_open_positions().values()] or cand['hmm_p_chop'] >= MAX_CHOP_PROB or cand['hmm_regime'] == '0':
                    continue

                p_l, p_s = cand['calibrated_prob_long'], cand['calibrated_prob_short']
                entry_price = float(cand['close'])
                
                tp_l, sl_l = entry_price + (1.50 * cand['atr_20']), entry_price - (1.50 * cand['atr_20'])
                net_win_l, net_loss_l = ((tp_l - entry_price)/entry_price) - WIN_FRICTION, ((entry_price - sl_l)/entry_price) + LOSS_FRICTION
                ev_l = (p_l * net_win_l) - ((1 - p_l) * net_loss_l)

                tp_s, sl_s = entry_price - (1.50 * cand['atr_20']), entry_price + (1.50 * cand['atr_20'])
                net_win_s, net_loss_s = ((entry_price - tp_s)/entry_price) - WIN_FRICTION, ((sl_s - entry_price)/entry_price) + LOSS_FRICTION
                ev_s = (p_s * net_win_s) - ((1 - p_s) * net_loss_s)

                side, p_best, ev_best, tp_best, sl_best, net_win, net_loss = None, 0, 0, 0, 0, 0, 0
                if ev_l > ev_s and ev_l > 0 and p_l >= ENTRY_THRESHOLD:
                    side, p_best, ev_best, tp_best, sl_best, net_win, net_loss = "BUY", p_l, ev_l, tp_l, sl_l, net_win_l, net_loss_l
                elif ev_s > ev_l and ev_s > 0 and p_s >= ENTRY_THRESHOLD:
                    side, p_best, ev_best, tp_best, sl_best, net_win, net_loss = "SELL", p_s, ev_s, tp_s, sl_s, net_win_s, net_loss_s

                if side and len(engine.get_open_positions()) < MAX_CONCURRENT_POSITIONS:
                    dynamic_payoff = net_win / net_loss
                    kelly_f = p_best - ((1 - p_best) / dynamic_payoff)
                    
                    trade_notional_pct = min(kelly_f * KELLY_FRACTION * LEVERAGE, MAX_NOTIONAL_PER_TRADE)
                    raw_notional = current_capital * trade_notional_pct
                    notional_size = min(raw_notional, HARD_LIQUIDITY_CAP)

                    order = Order(
                        order_id=str(uuid.uuid4())[:8], symbol=symbol, side=side, order_type="LIMIT",
                        price=entry_price, size_notional=notional_size, stop_loss=sl_best,
                        take_profit=tp_best, timestamp=now, regime=f"State_{cand['hmm_regime']}",
                        p_tp=float(p_best), kelly_fraction=trade_notional_pct
                    )

                    if engine.submit_order(order):
                        print(f"  [ORDER SUBMITTED] [{side}] {symbol} | P: {p_best:.4f} | Size: ${notional_size:,.2f} | EV: {ev_best:.4f}")

            free_margin = engine.get_available_margin(leverage=LEVERAGE)
            print(f"Portfolio Status -> Cash Equity: ${engine.get_account_equity():,.2f} | Free Margin: ${free_margin:,.2f} | Open Positions: {len(engine.get_open_positions())}")

        except Exception as e:
            print(f"[ERROR] Exception in daemon loop: {str(e)}")

        print("Sleeping for 15 minutes until next update check...")
        time.sleep(900)

if __name__ == "__main__":
    main()
