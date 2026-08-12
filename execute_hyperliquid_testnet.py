
def _fmt_sb(data):
    try:
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            t_col = next((c for c in data.columns if 'ticker' in c.lower()), data.columns[0])
            p_col = next((c for c in data.columns if 'prob' in c.lower() or 'score' in c.lower()), data.columns[1])
            return ", ".join([f"{row[t_col]}: {float(row[p_col]):.4f}" for _, row in data.iterrows()])
        elif hasattr(data, 'items'):
            return ", ".join([f"{k}: {float(v):.4f}" for k, v in data.items()])
        else:
            return ", ".join([f"{x[0]}: {float(x[1]):.4f}" for x in data])
    except Exception:
        return "Unable to parse scoreboard"


class BatchPortfolioRiskEngine:
    def __init__(self, global_risk_cap=0.05, max_leverage=10.0, kelly_fraction=0.50, btc_beta_threshold=0.03, btc_beta_multiplier=0.10):
        self.global_risk_cap = global_risk_cap
        self.max_leverage = max_leverage
        self.kelly_fraction = kelly_fraction
        self.btc_beta_threshold = btc_beta_threshold
        self.btc_beta_multiplier = btc_beta_multiplier

    def evaluate_batch(self, candidate_signals, current_open_risk_pct=0.0, btc_24h_ret=0.0):
        if not candidate_signals: return []
        
        valid_candidates = []
        for cand in candidate_signals:
            price, atr, p = cand.get('entry_price', 0), cand.get('atr', 0), cand.get('prob', 0)
            c_entry, c_tp, c_sl = cand.get('c_entry', 0), cand.get('c_tp', 0), cand.get('c_sl', 0)
            direction = cand.get('direction', 'SHORT')
            
            if price <= 0 or atr <= 0: continue
            
            r_dist = (1.50 * atr) / price
            net_win = r_dist - c_entry - c_tp
            net_loss = r_dist + c_entry + c_sl
            ev = (p * net_win) - ((1.0 - p) * net_loss)
            
            # STAGE 1: EV Gate
            if ev <= 0 or net_win <= 0: continue
                
            dynamic_payoff = net_win / net_loss if net_loss > 0 else 1.0
            kelly_f = p - ((1.0 - p) / dynamic_payoff)
            
            target_notional_pct = min(kelly_f * self.kelly_fraction * self.max_leverage, 2.0)
            
            # STAGE 2: Soft BTC Beta Gate
            if direction == 'SHORT' and btc_24h_ret >= self.btc_beta_threshold:
                target_notional_pct *= self.btc_beta_multiplier
                
            target_risk_pct = target_notional_pct * net_loss
            ev_density = ev / net_loss if net_loss > 0 else 0.0
            
            valid_candidates.append({
                'ticker': cand['ticker'], 'direction': direction, 'ev': ev,
                'ev_density': ev_density, 'net_win': net_win, 'net_loss': net_loss,
                'target_notional_pct': target_notional_pct, 'target_risk_pct': target_risk_pct,
                'price': price, 'atr': atr
            })
            
        if not valid_candidates: return []
        
        # STAGE 3: EV Density Ranking
        ranked_candidates = sorted(valid_candidates, key=lambda x: x['ev_density'], reverse=True)
        
        # STAGE 4: Portfolio Risk Budget Allocation
        remaining_budget = max(0.0, self.global_risk_cap - current_open_risk_pct)
        allocated_trades = []
        
        for cand in ranked_candidates:
            if remaining_budget <= 0.0005: break
            
            req_risk = cand['target_risk_pct']
            if req_risk <= remaining_budget:
                allocated_notional_pct = cand['target_notional_pct']
                allocated_risk_pct = req_risk
                remaining_budget -= req_risk
            else:
                scale_factor = remaining_budget / req_risk
                allocated_notional_pct = cand['target_notional_pct'] * scale_factor
                allocated_risk_pct = remaining_budget
                remaining_budget = 0.0
                
            cand['approved_notional_pct'] = allocated_notional_pct
            cand['approved_risk_pct'] = allocated_risk_pct
            allocated_trades.append(cand)
            
        return allocated_trades


def round_hl_price(price: float, sz_decimals: int = 2) -> float:
    if not price or price <= 0:
        return price
    import math
    digits = int(math.floor(math.log10(abs(price)))) + 1
    max_decimals = max(0, 6 - int(sz_decimals))
    decimals = max(0, min(max_decimals, 5 - digits))
    return round(float(price), decimals)

import os, time, uuid, joblib, logging, warnings, requests
import numpy as np, pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from catboost import CatBoostClassifier

from execution.hyperliquid_executor import HyperliquidExecutionEngine
from execution.base_executor import Order

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s UTC] [%(levelname)s] %(message)s")
logger = logging.getLogger("HYPERLIQUID_DAEMON")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

# Alpha Parameters
ENTRY_THRESHOLD_SHORT, ENTRY_THRESHOLD_LONG = 0.52, 0.58
KELLY_FRACTION_SHORT, KELLY_FRACTION_LONG = 0.50, 0.20

# Execution Parameters
MAX_CONCURRENT_POSITIONS = 5
HARD_LIQUIDITY_CAP = 150000.0
WIN_FRICTION, LOSS_FRICTION = 0.0014, 0.0020
MAINTENANCE_MARGIN_BUFFER = 0.05
MAX_ENTRY_DRIFT = 0.025  # Max 2.5% drift from 4H close allowed
ATR_OFFSET_FACTOR = 0.05 # Limit priced at 5% of ATR away from live price

def get_hyperliquid_meta():
    try:
        resp = requests.post('https://api.hyperliquid.xyz/info', json={"type": "meta"}, timeout=10)
        return {asset['name']: asset['maxLeverage'] for asset in resp.json()['universe']}
    except Exception as e:
        logger.warning(f"Failed to fetch live Hyperliquid max leverage: {e}")
        return {}

def get_hyperliquid_live_mids():
    try:
        resp = requests.post('https://api.hyperliquid.xyz/info', json={"type": "allMids"}, timeout=10)
        return {k: float(v) for k, v in resp.json().items()}
    except Exception as e:
        logger.warning(f"Failed to fetch live mids: {e}")
        return {}

def load_latest_features(client):
    query = f"""
        WITH latest_ts AS (SELECT MAX(timestamp) as max_ts FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`)
        SELECT 
            f.*, 
            t.* EXCEPT (ticker, timestamp), 
            l.* EXCEPT (ticker, timestamp)
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
    # Defensive ATR column resolution
    atr_col = next((c for c in ['atr_20', 'atr_14', 'atr', 'volatility_atr_20'] if c in df.columns), None)
    if atr_col and atr_col != 'atr_20':
        df['atr_20'] = df[atr_col]
    elif not atr_col:
        # Fallback approximation if no explicit ATR column exists in table schema
        df['atr_20'] = df['close'] * 0.02

    return df.dropna(subset=['close']).fillna(0).reset_index(drop=True)

def main():
    logger.info("Executing Decoupled Alpha/Execution Scan Cycle with Basis Telemetry...")
    
    hl_max_lev_map = get_hyperliquid_meta()
    live_mids = get_hyperliquid_live_mids()
    
    hmm_model, hmm_scaler = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl"), joblib.load(f"{MODEL_DIR}/hmm_scaler.pkl")
    hmm_features, canonical_order = joblib.load(f"{MODEL_DIR}/hmm_feature_names.pkl"), joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
    meta_long, cal_long = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_long.cbm"), joblib.load(f"{MODEL_DIR}/meta_calibrator_long.pkl")
    meta_short, cal_short = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_short.cbm"), joblib.load(f"{MODEL_DIR}/meta_calibrator_short.pkl")
    all_cat_cols, all_features = joblib.load(f"{MODEL_DIR}/cat_cols.pkl"), joblib.load(f"{MODEL_DIR}/feature_names.pkl")

    bq_client = bigquery.Client(project=PROJECT_ID)
    engine = HyperliquidExecutionEngine(db_path="live_execution_telemetry.db", is_testnet=True)
    peak_capital = engine.get_account_equity()
    
    last_traded_candle = {}

    account_equity = engine.get_account_equity()
    if account_equity > peak_capital: peak_capital = account_equity
    
    dd_pct = (peak_capital - account_equity) / peak_capital if peak_capital > 0 else 0
    dd_multi = 0.25 if dd_pct >= 0.30 else (0.50 if dd_pct >= 0.15 else 1.0)
    
    open_dex_positions = engine.get_open_positions()
    logger.info(f"Equity: ${account_equity:.2f} | Open Positions: {len(open_dex_positions)} | DD Multiplier: {dd_multi}x")

    # --- 15-MINUTE TTL GARBAGE COLLECTION ---
    try:
        canceled_stale = engine.cancel_stale_orders(open_positions=open_dex_positions)
        if canceled_stale > 0:
            logger.info(f"[GARBAGE COLLECTOR] Cleared {canceled_stale} stale limit order(s) for coins without active positions.")
    except Exception as e:
        logger.warning(f"Garbage collection check error: {e}")

    df = load_latest_features(bq_client)
    if df.empty:
        logger.warning("Feature matrix empty, skipping cycle.")
        return

    # Defensive Column Alignment
    for col in all_features:
        if col not in df.columns: df[col] = 0.0
    for col in hmm_features:
        if col not in df.columns: df[col] = 0.0

    scaled_x = hmm_scaler.transform(df[hmm_features].fillna(0))
    can_probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
    df['hmm_p_chop'], df['hmm_regime'] = can_probs[:, 0], can_probs.argmax(axis=1).astype(str)

    for col in all_cat_cols: df[col] = df[col].astype(str)
    df['primary_prob_long'] = df['primary_prob_short'] = 0.0

    for regime in ['0', '1', '2']:
        m_l_path, m_s_path = f"{MODEL_DIR}/regime_{regime}_long_expert.cbm", f"{MODEL_DIR}/regime_{regime}_short_expert.cbm"
        idx = df[df['hmm_regime'] == regime].index
        if len(idx) > 0 and os.path.exists(m_l_path): df.loc[idx, 'primary_prob_long'] = CatBoostClassifier().load_model(m_l_path).predict_proba(df.loc[idx, all_features])[:, 1]
        if len(idx) > 0 and os.path.exists(m_s_path): df.loc[idx, 'primary_prob_short'] = CatBoostClassifier().load_model(m_s_path).predict_proba(df.loc[idx, all_features])[:, 1]

    df['calibrated_prob_long'] = cal_long.predict(meta_long.predict_proba(df[meta_long.feature_names_])[:, 1])
    df['calibrated_prob_short'] = cal_short.predict(meta_short.predict_proba(df[meta_short.feature_names_])[:, 1])

    # --- TOP 5 CANDIDATE LEADERBOARD LOGGING ---
    top_longs = df.nlargest(5, 'calibrated_prob_long')[['ticker', 'calibrated_prob_long']]
    top_shorts = df.nlargest(5, 'calibrated_prob_short')[['ticker', 'calibrated_prob_short']]
    
    long_str = ', '.join([f"{r.ticker}: {r.calibrated_prob_long:.4f}" for _, r in top_longs.iterrows()])
    short_str = ', '.join([f"{r.ticker}: {r.calibrated_prob_short:.4f}" for _, r in top_shorts.iterrows()])
    
    latest_feature_ts = str(df['timestamp'].max()) if 'timestamp' in df.columns else 'N/A'
    logger.info(f"[MODEL SCOREBOARD | Feature TS: {latest_feature_ts}] Top Longs  -> " + _fmt_sb(top_longs))
    logger.info(f"[MODEL SCOREBOARD | Feature TS: {latest_feature_ts}] Top Shorts -> " + _fmt_sb(top_shorts))

    trades_submitted = 0
    for _, cand in df.iterrows():
        coin = str(cand['ticker']).replace("USDT", "").replace("USD", "").upper()
        current_candle_ts = cand['timestamp']
        
        hist_close = float(cand['close'])
        atr = float(cand['atr_20'])
        live_price = live_mids.get(coin, hist_close)
        p_l, p_s = float(cand['calibrated_prob_long']), float(cand['calibrated_prob_short'])

        if coin in open_dex_positions: continue
        if len(open_dex_positions) + trades_submitted >= MAX_CONCURRENT_POSITIONS: continue
        if p_l > 0.60 or p_s > 0.60:
            if cand['hmm_p_chop'] >= 0.50 or cand['hmm_regime'] == '0':
                logger.info(f"[FILTERED] {coin} high probability (L:{p_l:.2f}/S:{p_s:.2f}) blocked by HMM Regime/Chop (Regime:{cand['hmm_regime']}, Chop:{cand['hmm_p_chop']:.2f})")
                continue
            if ev_s <= 0 and p_s > 0.60:
                logger.info(f"[FILTERED] {coin} short (P:{p_s:.2f}) blocked by EV <= 0 (EV:{ev_s:.4f})")
        elif cand['hmm_p_chop'] >= 0.50 or cand['hmm_regime'] == '0':
            continue
        if coin in last_traded_candle and last_traded_candle[coin] == current_candle_ts: continue

        # --- EXECUTION GUARDRAIL ---
        basis_drift = (live_price - hist_close) / hist_close if hist_close > 0 else 0.0
        if abs(basis_drift) > MAX_ENTRY_DRIFT:
            logger.debug(f"[SKIP] {coin} live price drifted {basis_drift:.2%} away from signal 4H close.")
            continue

        # --- DYNAMIC LIMIT PRICING ---
        maker_offset = atr * ATR_OFFSET_FACTOR
        limit_l = live_price - maker_offset
        limit_s = live_price + maker_offset

        # Risk parameters anchored to execution price, not signal price
        tp_l, sl_l = limit_l + (1.50 * atr), limit_l - (1.50 * atr)
        # --- DYNAMIC ASSET TIER MAPPING (Stage 1) ---
        majors = ['BTC', 'ETH', 'SOL']
        liquid_alts = ['AVAX', 'NEAR', 'LINK', 'SUI', 'AAVE', 'BNB', 'XRP', 'DOGE', 'ADA', 'TRX']
        mid_caps = ['ICP', 'DOT', 'UNI', 'LTC', 'APT', 'INJ', 'STX', 'RNDR']
        
        if coin in majors:
            tier, c_entry, c_tp, c_sl = 'MAJOR', 0.0007, 0.0005, 0.0010
        elif coin in liquid_alts:
            tier, c_entry, c_tp, c_sl = 'LIQUID_ALT', 0.0010, 0.0008, 0.0015
        elif coin in mid_caps:
            tier, c_entry, c_tp, c_sl = 'MID_CAP', 0.0016, 0.0012, 0.0022
        else:
            tier, c_entry, c_tp, c_sl = 'THIN_ALT', 0.0030, 0.0025, 0.0045

        # --- EV CALCULATION (LONG) ---
        reward_dist_l = (tp_l - limit_l) / limit_l
        risk_dist_l = (limit_l - sl_l) / limit_l
        net_win_l = reward_dist_l - c_entry - c_tp
        net_loss_l = risk_dist_l + c_entry + c_sl
        ev_l = (p_l * net_win_l) - ((1 - p_l) * net_loss_l)

        # --- EV CALCULATION (SHORT) ---
        tp_s, sl_s = limit_s - (1.50 * atr), limit_s + (1.50 * atr)
        reward_dist_s = (limit_s - tp_s) / limit_s
        risk_dist_s = (sl_s - limit_s) / limit_s
        net_win_s = reward_dist_s - c_entry - c_tp
        net_loss_s = risk_dist_s + c_entry + c_sl
        ev_s = (p_s * net_win_s) - ((1 - p_s) * net_loss_s)

        # --- TELEMETRY LOGGING (High Conviction Candidates) ---
        if p_l >= 0.65 or p_s >= 0.65:
            active_p = p_l if p_l > p_s else p_s
            active_ev = ev_l if p_l > p_s else ev_s
            active_net_win = net_win_l if p_l > p_s else net_win_s
            active_net_loss = net_loss_l if p_l > p_s else net_loss_s
            active_reward = reward_dist_l if p_l > p_s else reward_dist_s
            direction_str = "LONG" if p_l > p_s else "SHORT"
            
            logger.info(f"\n[EV ANALYSIS] {coin} ({direction_str} | Tier: {tier})")
            logger.info(f"├── Probability (P):    {active_p:.4f} | ATR Target (R): {active_reward*100:.2f}%")
            logger.info(f"├── Static Entry Fric:  {c_entry*10000:.1f} bps")
            logger.info(f"├── Static TP Fric:     {c_tp*10000:.1f} bps")
            logger.info(f"├── Static SL Fric:     {c_sl*10000:.1f} bps")
            logger.info(f"├── Net Win Payoff:     {active_net_win*10000:.1f} bps")
            logger.info(f"├── Net Loss Payoff:    {active_net_loss*10000:.1f} bps")
            logger.info(f"└── Calculated EV:      {active_ev*10000:.1f} bps")

        direction, side, p_best, tp_best, sl_best, net_win, net_loss, kelly_frac, exec_price = None, None, 0, 0, 0, 0, 0, 0, 0
        if ev_l > ev_s and ev_l > 0 and p_l >= ENTRY_THRESHOLD_LONG and cand['hmm_regime'] != '2':
            direction, side, p_best, tp_best, sl_best, net_win, net_loss, kelly_frac, exec_price = "LONG", "BUY", p_l, tp_l, sl_l, net_win_l, net_loss_l, KELLY_FRACTION_LONG, limit_l
        elif ev_s > ev_l and ev_s > 0 and p_s >= ENTRY_THRESHOLD_SHORT:
            direction, side, p_best, tp_best, sl_best, net_win, net_loss, kelly_frac, exec_price = "SHORT", "SELL", p_s, tp_s, sl_s, net_win_s, net_loss_s, KELLY_FRACTION_SHORT, limit_s
        else:
            continue 

        exchange_max_lev = hl_max_lev_map.get(coin, 5)
        sl_pct_distance = (1.50 * atr) / exec_price if exec_price > 0 else 0.05
        math_max_lev = int((1.0 - MAINTENANCE_MARGIN_BUFFER) / sl_pct_distance) if sl_pct_distance > 0 else exchange_max_lev
        applied_leverage = max(1, min(exchange_max_lev, math_max_lev))

        dynamic_payoff = net_win / net_loss
        kelly_f = p_best - ((1 - p_best) / dynamic_payoff)
        trade_notional_pct = min(kelly_f * kelly_frac * applied_leverage * dd_multi, 2.0)
        notional_size = min(account_equity * trade_notional_pct, HARD_LIQUIDITY_CAP)
        
        free_margin = engine.get_available_margin(leverage=applied_leverage)
        margin_required = notional_size / applied_leverage

        limit_offset = (exec_price - live_price) / live_price if live_price > 0 else 0.0

        if free_margin >= margin_required and notional_size > 12.0:

            sz_dec = getattr(engine, "sz_decimals", {}).get(coin, 2) if "engine" in locals() else 2
            sz_dec = getattr(engine, "sz_decimals", {}).get(coin, 2) if "engine" in locals() else 2
            order = Order(
                order_id=str(uuid.uuid4())[:8], symbol=coin, side=side, order_type="LIMIT",
                price=round_hl_price(exec_price, sz_dec), size_notional=notional_size, stop_loss=round_hl_price(sl_best, sz_dec), take_profit=round_hl_price(tp_best, sz_dec),
                timestamp=datetime.now(timezone.utc), regime=f"State_{cand['hmm_regime']}", p_tp=float(p_best), kelly_fraction=trade_notional_pct,
                signal_price_binance=hist_close, live_price_hl=live_price, basis_drift_pct=basis_drift, limit_offset_pct=limit_offset
            )
            if engine.submit_order(order):
                try:
                    engine.attach_native_tp_sl(coin, side, notional_size, tp_best, sl_best)
                except AttributeError:
                    logger.error(f"Execution Engine missing attach_native_tp_sl method! Trading naked on {coin}.")
                
                open_dex_positions[coin] = True
                trades_submitted += 1
                last_traded_candle[coin] = current_candle_ts
                logger.info(f"[ORDER SUBMITTED] {coin} {side} | Lev: {applied_leverage}x | P: {p_best:.3f} | Size: ${notional_size:.2f} | Limit: ${exec_price:.4f} | Basis Drift: {basis_drift:.2%}")

    logger.info(f"Pass completed cleanly. Trades submitted: {trades_submitted}")

if __name__ == "__main__":
    main()
