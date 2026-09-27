#!/usr/bin/env python3
"""
Realistic High-Octane 90-Day Compounding Backtest Engine
Features:
- Exact time-stepped position ledger (margin locked for duration of trade)
- Single concurrent position per asset lockout
- Exact ATR barrier price resolution
- 60% concurrent margin utilization ceiling
- Asymmetric Kelly sizing (0.75 Short / 0.35 Long)
"""

import os
import requests
import joblib
import numpy as np
import pandas as pd
from datetime import timedelta
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = "parnasa-498503"
STARTING_CAPITAL = 1000.0
ROUNDTRIP_FEE_BPS = 15.0  # 15 bps taker fee + slippage
MAX_PORTFOLIO_MARGIN = 0.60
MAX_CONCURRENT_POSITIONS = 8


def find_model_dir():
    for d in ["production_models", "/home/skybullet1987/quant_pipeline/production_models", "models", "."]:
        if os.path.exists(os.path.join(d, "hmm_macro.pkl")):
            return os.path.abspath(d)
    return "."


def get_hyperliquid_max_leverage():
    try:
        resp = requests.post("https://api.hyperliquid.xyz/info", json={"type": "meta"}, timeout=5)
        return {a["name"]: a["maxLeverage"] for a in resp.json().get("universe", [])}
    except Exception:
        return {}


def main():
    print("=" * 80)
    print("  RUNNING LEDGER-ACCURATE 90-DAY HIGH-OCTANE COMPOUNDING BACKTEST")
    print("=" * 80)

    model_dir = find_model_dir()
    hl_lev_map = get_hyperliquid_max_leverage()
    client = bigquery.Client(project=PROJECT_ID)

    print("[1/4] Querying BigQuery for features and path resolutions...")
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
        WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    print(f"Loaded {len(df):,} candidate rows.")

    print("[2/4] Executing ML Model & Regime Inference...")
    hmm_model = joblib.load(f"{model_dir}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{model_dir}/hmm_scaler.pkl")
    hmm_features = joblib.load(f"{model_dir}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{model_dir}/hmm_canonical_order.pkl")
    meta_long = CatBoostClassifier().load_model(f"{model_dir}/meta_labeler_long.cbm")
    cal_long = joblib.load(f"{model_dir}/meta_calibrator_long.pkl")
    meta_short = CatBoostClassifier().load_model(f"{model_dir}/meta_labeler_short.cbm")
    cal_short = joblib.load(f"{model_dir}/meta_calibrator_short.pkl")
    all_cat_cols = joblib.load(f"{model_dir}/cat_cols.pkl")
    all_features = joblib.load(f"{model_dir}/feature_names.pkl")
    cat_set = set(all_cat_cols)

    for col in hmm_features:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0) if col in df.columns else 0.0

    scaled_x = hmm_scaler.transform(df[hmm_features])
    can_probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
    df["hmm_regime"] = can_probs.argmax(axis=1).astype(str)

    for col in all_features:
        if col not in df.columns:
            df[col] = "missing" if col in cat_set else 0.0
        elif col in cat_set:
            df[col] = df[col].astype(str).fillna("missing")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    cat_features_in_base = [c for c in all_features if c in cat_set]
    df["primary_prob_short"] = 0.0
    df["primary_prob_long"] = 0.0

    for regime in ["0", "1", "2"]:
        m_s_path = f"{model_dir}/regime_{regime}_short_expert.cbm"
        m_l_path = f"{model_dir}/regime_{regime}_long_expert.cbm"
        mask = df["hmm_regime"] == regime
        if mask.sum() > 0:
            reg_pool = Pool(df.loc[mask, all_features], cat_features=cat_features_in_base)
            if os.path.exists(m_s_path):
                df.loc[mask, "primary_prob_short"] = CatBoostClassifier().load_model(m_s_path).predict_proba(reg_pool)[:, 1]
            if os.path.exists(m_l_path):
                df.loc[mask, "primary_prob_long"] = CatBoostClassifier().load_model(m_l_path).predict_proba(reg_pool)[:, 1]

    meta_s_features = meta_short.feature_names_
    meta_l_features = meta_long.feature_names_

    for col in meta_s_features + meta_l_features:
        if col not in df.columns:
            df[col] = "missing" if col in cat_set else 0.0
        elif col in cat_set:
            df[col] = df[col].astype(str).fillna("missing")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    pool_s = Pool(df[meta_s_features], cat_features=[c for c in meta_s_features if c in cat_set])
    pool_l = Pool(df[meta_l_features], cat_features=[c for c in meta_l_features if c in cat_set])

    raw_s = meta_short.predict_proba(pool_s)[:, 1]
    raw_l = meta_long.predict_proba(pool_l)[:, 1]

    df["prob_short_cal"] = cal_short.predict(raw_s) if hasattr(cal_short, "predict") else raw_s
    df["prob_long_cal"] = cal_long.predict(raw_l) if hasattr(cal_long, "predict") else raw_l

    print("[3/4] Running Ledger-Accurate Time-Stepped Simulation...")

    def run_ledger_simulation(mode="dynamic"):
        equity = STARTING_CAPITAL
        peak_equity = STARTING_CAPITAL
        max_dd = 0.0
        
        # Position Ledger: {ticker: {'margin': float, 'exit_time': timestamp, 'pnl': float, ...}}
        open_positions = {}
        closed_trades = []

        timestamps = sorted(df["timestamp"].unique())

        for current_time in timestamps:
            current_time = pd.to_datetime(current_time)

            # 1. Close matured positions whose exit_time <= current_time
            to_remove = []
            for ticker, pos in open_positions.items():
                if current_time >= pos["exit_time"]:
                    equity += pos["margin"] + pos["pnl"]
                    if equity > peak_equity:
                        peak_equity = equity
                    closed_trades.append(pos)
                    to_remove.append(ticker)

            for ticker in to_remove:
                del open_positions[ticker]

            # 2. Update Drawdown Governor
            current_dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0.0
            if current_dd > max_dd:
                max_dd = current_dd

            dd_mult = 0.25 if current_dd >= 0.30 else (0.50 if current_dd >= 0.15 else 1.0)

            # 3. Available Margin Capacity
            currently_locked_margin = sum(p["margin"] for p in open_positions.values())
            max_allowed_margin = equity * MAX_PORTFOLIO_MARGIN
            available_margin = max(0.0, max_allowed_margin - currently_locked_margin)

            if len(open_positions) >= MAX_CONCURRENT_POSITIONS or available_margin <= 5.0:
                continue

            # 4. Evaluate Candidates for this candle
            candle_df = df[df["timestamp"] == current_time]
            for _, row in candle_df.iterrows():
                ticker = row["ticker"]
                if ticker in open_positions:
                    continue  # Already in an active position for this asset

                p_short = row["prob_short_cal"]
                p_long = row["prob_long_cal"]

                side = None
                if p_short >= 0.52:
                    side = "SHORT"
                    k_frac = 0.75
                    asset_max = hl_lev_map.get(ticker.replace("USD", "").replace("USDT", ""), 10.0)
                    leverage = 10.0 if mode == "fixed" else min(asset_max, 10.0)
                elif p_long >= 0.58:
                    side = "LONG"
                    k_frac = 0.35
                    asset_max = hl_lev_map.get(ticker.replace("USD", "").replace("USDT", ""), 6.0)
                    leverage = 6.0 if mode == "fixed" else min(asset_max, 6.0)

                if side is None:
                    continue

                target_margin = equity * k_frac * dd_mult
                if target_margin > available_margin:
                    target_margin = available_margin
                if target_margin < 5.0:
                    break

                available_margin -= target_margin
                currently_locked_margin += target_margin
                notional = target_margin * leverage

                # Path Resolution & Return Calculation
                entry_px = float(row["close"]) if "close" in row and row["close"] > 0 else 1.0
                tp_px = float(row["target_price_1_5_atr"]) if "target_price_1_5_atr" in row else entry_px * 1.025
                sl_px = float(row["stop_loss_1_5_atr"]) if "stop_loss_1_5_atr" in row else entry_px * 0.985
                hold_min = int(row["minutes_in_trade"]) if "minutes_in_trade" in row and row["minutes_in_trade"] > 0 else 240

                if side == "SHORT":
                    is_win = (row["target_short"] == 1)
                    raw_ret = ((entry_px - tp_px) / entry_px) if is_win else ((entry_px - sl_px) / entry_px)
                else:
                    is_win = (row["target_long"] == 1)
                    raw_ret = ((tp_px - entry_px) / entry_px) if is_win else ((sl_px - entry_px) / entry_px)

                net_ret = raw_ret - (ROUNDTRIP_FEE_BPS / 10000.0)
                dollar_pnl = notional * net_ret

                # Deduct initial margin from liquid cash
                equity -= target_margin

                open_positions[ticker] = {
                    "entry_time": current_time,
                    "exit_time": current_time + timedelta(minutes=hold_min),
                    "ticker": ticker,
                    "side": side,
                    "margin": target_margin,
                    "notional": notional,
                    "pnl": dollar_pnl,
                    "win": 1 if dollar_pnl > 0 else 0
                }

                if len(open_positions) >= MAX_CONCURRENT_POSITIONS or available_margin <= 5.0:
                    break

            if (equity + currently_locked_margin) <= 10.0:
                print("[CRITICAL] Account liquidation.")
                break

        # Flush remaining open positions
        for pos in open_positions.values():
            equity += pos["margin"] + pos["pnl"]
            closed_trades.append(pos)

        t_df = pd.DataFrame(closed_trades)
        wr = (t_df["win"].sum() / len(t_df) * 100.0) if len(t_df) > 0 else 0.0
        return equity, len(t_df), wr, max_dd

    eq_fixed, n_fixed, wr_fixed, dd_fixed = run_ledger_simulation("fixed")
    eq_dyn, n_dyn, wr_dyn, dd_dyn = run_ledger_simulation("dynamic")

    print("\n" + "=" * 76)
    print("       REALISTIC 90-DAY TIME-STEPPED LEDGER AUDIT RESULTS")
    print("=" * 76)
    print(f"{'Metric':<28} | {'Fixed 10x Baseline':<20} | {'Dynamic Platform Lev':<20}")
    print("-" * 76)
    print(f"{'Final Equity ($1k Start)':<28} | ${eq_fixed:>18,.2f} | ${eq_dyn:>18,.2f}")
    print(f"{'Total Trades Executed':<28} | {n_fixed:>18,} | {n_dyn:>18,}")
    print(f"{'Win Rate':<28} | {wr_fixed:>17.2f}% | {wr_dyn:>17.2f}%")
    print(f"{'Maximum Drawdown':<28} | -{dd_fixed*100:>16.2f}% | -{dd_dyn*100:>16.2f}%")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    main()
