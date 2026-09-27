import os
import sys
import time
import logging
import sqlite3
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from dotenv import load_dotenv

from tactical_regime import TacticalRegimeEngine
from risk_engine import PortfolioRiskEngine

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
API_URL = os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid-testnet.xyz")
DB_PATH = "execution_telemetry.db"
PROD_MODELS_DIR = "models/prod"

# Safe default
DRY_RUN = os.getenv("DRY_RUN", "true").strip().lower() != "false"

MAX_POSITIONS = 5
MAX_PER_SIDE = 3
MAX_TRADES_PER_CYCLE = 2
FEE_SLIPPAGE_BPS = 12.0
MAX_TOTAL_MARGIN_UTILIZATION = 0.85

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS candidate_evaluations (
            timestamp TEXT,
            symbol TEXT,
            p_long REAL,
            p_short REAL,
            p_chop REAL,
            regime TEXT,
            ev_bps REAL,
            status TEXT,
            reason_code TEXT,
            reason TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS trade_cooldowns (
            symbol TEXT PRIMARY KEY,
            last_closed_bar_ts TEXT,
            closed_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def format_hl_price(px: float, sz_decimals: int) -> float:
    return round(px, max(1, 5 - sz_decimals))

def reconcile_orphaned_triggers(info, exchange, master_addr, open_syms):
    try:
        triggers = info.frontend_open_orders(master_addr)
        for o in triggers:
            coin = o.get("coin")
            if coin not in open_syms:
                exchange.cancel(coin, o["oid"])
                logging.info(f"[TRIGGER CLEANUP] Cancelled orphaned trigger {o['oid']} for flat asset {coin}")
    except Exception as e:
        logging.warning(f"[TRIGGER CLEANUP WARNING] {e}")

def get_active_cooldowns():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT symbol, last_closed_bar_ts FROM trade_cooldowns")
    rows = c.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

def register_cooldown(symbol, bar_ts):
    now_ts = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO trade_cooldowns (symbol, last_closed_bar_ts, closed_at)
        VALUES (?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET last_closed_bar_ts=excluded.last_closed_bar_ts, closed_at=excluded.closed_at
    """, (symbol, str(bar_ts), now_ts))
    conn.commit()
    conn.close()

def fetch_latest_features_and_infer():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*, 
            COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
            COALESCE(t.tfm_ret_72h, 0.0) AS tfm_ret_72h, 
            COALESCE(t.tfm_slope, 0.0) AS tfm_slope, 
            COALESCE(t.tfm_uncertainty, 0.0) AS tfm_uncertainty, 
            COALESCE(t.tfm_residual_24h, 0.0) AS tfm_residual_24h, 
            COALESCE(t.tfm_conviction_delta, 0.0) AS tfm_conviction_delta,
            COALESCE(l.total_liq_usd, 0) AS total_liq_usd,
            COALESCE(l.liq_imbalance_ratio, 0) AS liq_imbalance_ratio,
            COALESCE(l.long_liq_accel, 0) AS long_liq_accel,
            COALESCE(l.short_liq_accel, 0) AS short_liq_accel,
            COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t 
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l 
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        WHERE f.timestamp = (SELECT MAX(timestamp) FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`)
    """
    df = client.query(query).to_dataframe()
    if df.empty:
        return df

    # 1. HMM Inference
    try:
        hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
        hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
        hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
        canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")

        for c in hmm_feats:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0) if c in df.columns else 0.0

        scaled_x = hmm_scaler.transform(df[hmm_feats])
        probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
        df["p_chop"] = probs[:, 0]
        df["regime"] = probs.argmax(axis=1).astype(str)
        df["hmm_regime"] = df["regime"]
    except Exception as e:
        logging.warning(f"HMM fallback: {e}")
        df["regime"] = "1"
        df["hmm_regime"] = "1"
        df["p_chop"] = 0.0

    # 2. Multi-Regime CatBoost Inference
    try:
        all_cat_cols = joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/cat_cols.pkl") else []
        cat_set = set(all_cat_cols)

        models_long = {}
        models_short = {}
        for r in [0, 1, 2]:
            l_path = f"{PROD_MODELS_DIR}/regime_{r}_long_expert.cbm"
            s_path = f"{PROD_MODELS_DIR}/regime_{r}_short_expert.cbm"
            if os.path.exists(l_path):
                models_long[str(r)] = CatBoostClassifier().load_model(l_path)
            if os.path.exists(s_path):
                models_short[str(r)] = CatBoostClassifier().load_model(s_path)

        fallback_long = models_long.get("1", next(iter(models_long.values()), None))
        fallback_short = models_short.get("2", next(iter(models_short.values()), None))

        p_long_list, p_short_list = [], []
        for idx, row in df.iterrows():
            reg_val = str(row.get("regime", "1"))
            model_l = models_long.get(reg_val, fallback_long)
            model_s = models_short.get(reg_val, fallback_short)

            feats_l = model_l.feature_names_
            row_dict_l = {col: (str(reg_val) if col in ["hmm_regime", "regime"] else (str(row[col]) if col in cat_set and col in row and pd.notna(row[col]) else ("missing" if col in cat_set else (float(row[col]) if col in row and pd.notna(row[col]) else 0.0)))) for col in feats_l}
            pool_l = Pool(pd.DataFrame([row_dict_l]), cat_features=[c for c in feats_l if c in cat_set])
            p_l = float(model_l.predict_proba(pool_l)[0, 1])

            feats_s = model_s.feature_names_
            row_dict_s = {col: (str(reg_val) if col in ["hmm_regime", "regime"] else (str(row[col]) if col in cat_set and col in row and pd.notna(row[col]) else ("missing" if col in cat_set else (float(row[col]) if col in row and pd.notna(row[col]) else 0.0)))) for col in feats_s}
            pool_s = Pool(pd.DataFrame([row_dict_s]), cat_features=[c for c in feats_s if c in cat_set])
            p_s = float(model_s.predict_proba(pool_s)[0, 1])

            p_long_list.append(p_l)
            p_short_list.append(p_s)

        df["p_long"] = p_long_list
        df["p_short"] = p_short_list

    except Exception as e:
        logging.error(f"CatBoost inference error: {e}")
        df["p_long"] = 0.50
        df["p_short"] = 0.50

    return df

def run_execution_cycle():
    init_db()
    
    secret_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
    account = Account.from_key(secret_key)
    master_addr = os.getenv("HYPERLIQUID_MASTER_ADDRESS", account.address)

    info = Info(API_URL, skip_ws=True)
    exchange = Exchange(account, API_URL, account_address=master_addr)

    meta, asset_ctxs = info.meta_and_asset_ctxs()
    sz_decimals_map = {a["name"]: a["szDecimals"] for a in meta["universe"]}
    max_lev_map = {a["name"]: a["maxLeverage"] for a in meta["universe"]}
    live_mids = info.all_mids()

    # Unified Collateral & State Inspection
    user_state = info.user_state(master_addr)
    spot_state = info.spot_user_state(master_addr)

    usdc_spot = next((float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == "USDC"), 0.0)
    perp_account_val = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
    margin_used = float(user_state.get("marginSummary", {}).get("totalMarginUsed", 0.0))
    
    equity = usdc_spot if usdc_spot > 0.0 else max(perp_account_val, 600.0)
    open_positions = user_state.get("assetPositions", [])
    
    open_syms = set()
    long_count = 0
    short_count = 0
    for p in open_positions:
        szi = float(p["position"]["szi"])
        if szi != 0:
            open_syms.add(p["position"]["coin"])
            if szi > 0:
                long_count += 1
            else:
                short_count += 1

    # Cleanup Orphaned TP/SL triggers
    reconcile_orphaned_triggers(info, exchange, master_addr, open_syms)

    available_slots = max(0, MAX_POSITIONS - len(open_syms))
    logging.info(f"Mode: {'[DRY RUN]' if DRY_RUN else '[LIVE EXECUTION]'} | Equity: ${equity:.2f} | Margin Used: ${margin_used:.2f} | Open: {len(open_syms)}/5 (Longs: {long_count}, Shorts: {short_count}) | Free Slots: {available_slots}")

    if available_slots <= 0:
        logging.info("All position slots occupied. Exiting cycle.")
        return

    df_scores = fetch_latest_features_and_infer()
    if df_scores.empty:
        logging.warning("No candidate features returned.")
        return

    latest_bar_ts = str(df_scores["timestamp"].iloc[0])
    cooldowns = get_active_cooldowns()

    tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)
    risk_engine = PortfolioRiskEngine(
        risk_budget_pct=0.015,
        max_slot_equity_pct=0.35,
        max_gross_leverage=2.00,
        atr_stop_multiplier=1.20   # 1.20x ATR Tight Stop
    )

    candidate_evals = []
    eligible_candidates = []

    for _, row in df_scores.iterrows():
        coin = str(row["ticker"]).replace("USDT", "").replace("USD", "").upper()
        pl, ps, pc = float(row.get("p_long", 0.0)), float(row.get("p_short", 0.0)), float(row.get("p_chop", 0.0))
        reg = str(row.get("regime", "1"))
        signal_px = float(row.get("close_price", row.get("close", 0.0)))
        atr = float(row.get("atr_14", row.get("atr_20", signal_px * 0.02)))

        live_px = float(live_mids.get(coin, signal_px))
        if live_px <= 0 or atr <= 0:
            continue

        btc_1h = float(row.get("btc_ret_1h", 0.0))
        btc_4h = float(row.get("btc_ret_4h", 0.0))
        breadth = float(row.get("market_breadth_sma20", row.get("market_breadth", 0.50)))
        vol_exp = float(row.get("vol_expansion_ratio", 1.0))

        state = tactical_engine.evaluate_state(
            slow_regime=int(reg) if reg.isdigit() else 1,
            btc_ret_1h=btc_1h,
            btc_ret_4h=btc_4h,
            market_breadth_sma20=breadth,
            vol_expansion_ratio=vol_exp
        )

        l_pass = (pl >= state["long_hurdle"])
        s_pass = (ps >= state["short_hurdle"])
        chop_pass = (pc < 0.60)

        # 2.0x ATR TP / 1.2x ATR SL Asymmetry
        r_win = (2.00 * atr) / live_px
        r_loss = (1.20 * atr) / live_px
        fee_cut = FEE_SLIPPAGE_BPS / 10000.0

        long_ev = (pl * r_win) - ((1.0 - pl) * r_loss) - fee_cut
        short_ev = (ps * r_win) - ((1.0 - ps) * r_loss) - fee_cut

        rec = {
            "coin": coin, "p_l": pl, "p_s": ps, "p_c": pc, "regime": reg,
            "max_p": max(pl, ps), "status": "REJECTED", "reason_code": "NONE",
            "reason": "", "ev_bps": 0.0
        }

        # Cooldown check
        if cooldowns.get(coin) == latest_bar_ts:
            rec["reason_code"] = "COOLDOWN_ACTIVE"
            rec["reason"] = f"Trade exited in current 4H bar ({latest_bar_ts[:16]})"
        elif coin not in sz_decimals_map:
            rec["reason_code"] = "UNIVERSE_EXCLUDED"
            rec["reason"] = "Asset not in Hyperliquid universe"
        elif coin in open_syms:
            rec["reason_code"] = "POSITION_EXISTS"
            rec["reason"] = "Active position already open"
        elif not l_pass and not s_pass:
            rec["reason_code"] = "PROBABILITY_FAIL"
            rec["reason"] = f"Below dynamic hurdles (L:{pl:.2f}>={state['long_hurdle']:.2f}, S:{ps:.2f}>={state['short_hurdle']:.2f})"
        elif not chop_pass:
            rec["reason_code"] = "CHOP_FAIL"
            rec["reason"] = f"Chop filter active (p_chop: {pc:.2f} >= 0.60)"
        else:
            is_buy = l_pass and (not s_pass or pl >= ps)
            side, p_win, ev_val = ("BUY", pl, long_ev) if is_buy else ("SELL", ps, short_ev)
            rec["ev_bps"] = ev_val * 10000.0

            if ev_val <= 0:
                rec["reason_code"] = "NEGATIVE_EV"
                rec["reason"] = f"Negative Net EV ({rec['ev_bps']:+.1f} bps)"
            else:
                rec["status"] = "ELIGIBLE"
                rec["reason_code"] = "PASSED_GATES"
                rec["reason"] = f"Passed gates ({side} {rec['ev_bps']:+.1f} bps)"
                size_mult = state["long_size_mult"] if is_buy else state["short_size_mult"]

                eligible_candidates.append({
                    "coin": coin, "is_buy": is_buy, "side": side, "ev": ev_val,
                    "ev_bps": rec["ev_bps"], "p_win": p_win, "size_mult": size_mult,
                    "signal_px": signal_px, "live_px": live_px, "atr": atr, "bar_ts": latest_bar_ts
                })

        candidate_evals.append(rec)

    # Persist evaluations
    now_ts = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for ce in candidate_evals:
        c.execute("""
            INSERT INTO candidate_evaluations 
            (timestamp, symbol, p_long, p_short, p_chop, regime, ev_bps, status, reason_code, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (now_ts, ce["coin"], ce["p_l"], ce["p_s"], ce["p_c"], ce["regime"], ce["ev_bps"], ce["status"], ce["reason_code"], ce["reason"]))
    conn.commit()
    conn.close()

    logging.info("=== CANDIDATE EVALUATION WATERFALL (TOP 8) ===")
    for ce in sorted(candidate_evals, key=lambda x: x["max_p"], reverse=True)[:8]:
        logging.info(f"{ce['coin']:<8} | L:{ce['p_l']:.2f}/S:{ce['p_s']:.2f} | Chop:{ce['p_c']:.2f} | R:{ce['regime']} | EV:{ce['ev_bps']:>+6.1f} bps | [{ce['reason_code']}] {ce['reason']}")

    if not eligible_candidates:
        logging.info("[CYCLE COMPLETE] No candidate passed gates.")
        return

    # Pass 2: Ranking, Directional Capacity & Sizing
    ranked_candidates = sorted(eligible_candidates, key=lambda x: x["ev"], reverse=True)
    max_executions = min(MAX_TRADES_PER_CYCLE, available_slots)
    approved_orders = []
    available_margin_pool = max(0.0, (equity * MAX_TOTAL_MARGIN_UTILIZATION) - margin_used)

    for cand in ranked_candidates:
        if len(approved_orders) >= max_executions:
            break

        coin = cand["coin"]
        live_px = cand["live_px"]
        is_buy = cand["is_buy"]

        # Directional Exposure Cap Enforcement
        if is_buy and (long_count + sum(1 for o in approved_orders if o["is_buy"])) >= MAX_PER_SIDE:
            logging.info(f"[DIRECTIONAL REJECT] {coin} BUY blocked: Max {MAX_PER_SIDE} Longs reached.")
            continue
        if not is_buy and (short_count + sum(1 for o in approved_orders if not o["is_buy"])) >= MAX_PER_SIDE:
            logging.info(f"[DIRECTIONAL REJECT] {coin} SELL blocked: Max {MAX_PER_SIDE} Shorts reached.")
            continue

        sz_dec = sz_decimals_map.get(coin, 2)
        applied_lev = min(float(max_lev_map.get(coin, 3.0)), 3.0)

        # 2.0x ATR TP / 1.2x ATR SL
        tp_px = format_hl_price(live_px + (2.00 * cand["atr"]) if is_buy else live_px - (2.00 * cand["atr"]), sz_dec)
        sl_px = format_hl_price(live_px - (1.20 * cand["atr"]) if is_buy else live_px + (1.20 * cand["atr"]), sz_dec)

        raw_tokens, target_notional, modeled_risk = risk_engine.compute_order_size(
            account_equity=float(equity),
            current_price=float(live_px),
            atr_20=cand["atr"],
            regime_size_mult=cand["size_mult"],
            model_conviction=cand["p_win"],
            min_notional_usd=15.0
        )

        sz = round(raw_tokens, sz_dec) if sz_dec > 0 else float(int(raw_tokens))
        required_margin = target_notional / applied_lev if applied_lev > 0 else target_notional

        if sz <= 0 or required_margin > available_margin_pool:
            logging.info(f"[SIZING REJECT] {coin} (Size: {sz}, Notional: ${target_notional:.2f})")
            continue

        logging.info(f"[RISK SIZED] {coin} -> Tokens: {sz} | Notional: ${target_notional:.2f} | Modeled Risk: ${modeled_risk:.2f} (SL: ${sl_px})")

        approved_orders.append({
            "coin": coin, "is_buy": is_buy, "side": cand["side"], "ev_bps": cand["ev_bps"],
            "notional": target_notional, "margin": required_margin, "sz": sz, "sz_dec": sz_dec,
            "lev": applied_lev, "signal_px": cand["signal_px"], "ref_px": live_px,
            "tp_px": tp_px, "sl_px": sl_px, "modeled_risk": modeled_risk, "bar_ts": cand["bar_ts"]
        })
        available_margin_pool -= required_margin

    # Pass 3: Execution Dispatch + Native Brackets
    for o in approved_orders:
        coin = o["coin"]
        logging.info(f"[ORDER DISPATCH] {o['side']} {o['sz']} {coin} @ Ref ${o['ref_px']:.4f} | TP: ${o['tp_px']} | SL: ${o['sl_px']}")

        if DRY_RUN:
            logging.info(f"[DRY RUN ACTIVE] Skipped on-chain dispatch for {coin}.")
            continue

        try:
            exchange.update_leverage(int(o["lev"]), coin)
            entry_res = exchange.market_open(coin, o["is_buy"], o["sz"], o["ref_px"], 0.01)
            logging.info(f"[ENTRY RESPONSE] {coin} -> {entry_res}")

            if entry_res.get("status") != "ok":
                continue

            time.sleep(0.5)
            verified_state = info.user_state(master_addr)
            fill_sz = 0.0
            for p in verified_state.get("assetPositions", []):
                if p["position"]["coin"] == coin:
                    fill_sz = abs(float(p["position"]["szi"]))
                    break
            
            actual_sz = fill_sz if fill_sz > 0 else o["sz"]
            is_exit_buy = not o["is_buy"]

            # Register cooldown bar timestamp for this asset
            register_cooldown(coin, o["bar_ts"])

            # TP Trigger Limit Order (2.0x ATR)
            tp_res = exchange.order(
                name=coin,
                is_buy=is_exit_buy,
                sz=actual_sz,
                limit_px=o["tp_px"],
                order_type={"trigger": {"isMarket": False, "triggerPx": o["tp_px"], "tpsl": "tp"}},
                reduce_only=True
            )
            logging.info(f"[TP DISPATCH] {coin} TP @ ${o['tp_px']} -> {tp_res.get('status')}")

            # SL Trigger Market Order (1.2x ATR)
            sl_limit = round(o["sl_px"] * 1.05 if is_exit_buy else o["sl_px"] * 0.95, 4)
            sl_res = exchange.order(
                name=coin,
                is_buy=is_exit_buy,
                sz=actual_sz,
                limit_px=sl_limit,
                order_type={"trigger": {"isMarket": True, "triggerPx": o["sl_px"], "tpsl": "sl"}},
                reduce_only=True
            )
            logging.info(f"[SL DISPATCH] {coin} SL @ ${o['sl_px']} -> {sl_res.get('status')}")

        except Exception as e:
            logging.error(f"[EXECUTION FAILED] {coin}: {e}")

if __name__ == "__main__":
    run_execution_cycle()
