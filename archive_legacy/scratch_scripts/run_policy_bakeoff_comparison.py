#!/usr/bin/env python3
"""
Policy Bakeoff Comparison Harness: Legacy vs. New Risk Parity Engine
Usage:
    python3 run_policy_bakeoff_comparison.py --days 90
    python3 run_policy_bakeoff_comparison.py --days 30
"""

import os
import sys
import json
import joblib
import argparse
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool

warnings.filterwarnings("ignore")

# ============================================================================
# 1. PARAMETERS & CONFIGURATION
# ============================================================================
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
STARTING_CAPITAL = 1000.0
MAX_POSITIONS = 5
MAX_TRADES_PER_CYCLE = 2
FEE_SLIPPAGE_BPS = 15.0
MAX_TOTAL_MARGIN_UTILIZATION = 0.60
HARD_LIQUIDITY_CAP = 150000.0

# Legacy Policy Parameters
LEG_PROB_LONG = 0.58
LEG_PROB_SHORT = 0.52
LEG_KELLY_LONG = 0.20
LEG_KELLY_SHORT = 0.50
LEG_LEV_LONG = 3.0
LEG_LEV_SHORT = 10.0

# New Risk Parity Policy Parameters
NEW_HARD_MAX_RISK = 0.015  # 1.5% Nominal Risk Cap
NEW_PROB_LONG = 0.58
NEW_PROB_SHORT = 0.54
NEW_EDGE_LONG = 0.35
NEW_EDGE_SHORT = 0.50
PAYOFF_RATIO = 1.5


def get_active_model_dir() -> str:
    manifest_path = "models/manifest.json"
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
                active_ver = data.get("active_version", "v2026_08_01")
                release_dir = os.path.join("models", "releases", active_ver)
                if os.path.exists(release_dir):
                    return release_dir
        except Exception:
            pass
    return "production_models" if os.path.exists("production_models") else "."

PROD_MODELS_DIR = get_active_model_dir()

# ============================================================================
# 2. DATA INGESTION & FEATURE SCORING
# ============================================================================
def load_feature_matrix(days: int) -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)
    print(f"\n[1/3] Querying last {days} days of path outcomes from BigQuery...")

    query = f"""
        SELECT 
            f.*, 
            p.exit_time, p.exit_reason, p.exact_gross_return, p.minutes_in_trade,
            p.target_long, p.target_short,
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
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.ticker = p.ticker AND f.timestamp = p.signal_time
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
          AND p.exit_reason != 'DATA_ERROR'
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    print(f"  -> Loaded {len(df):,} candle observations across {df['ticker'].nunique()} tickers.")
    return df


def score_model_probabilities(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[2/3] Executing HMM & CatBoost Meta-Labeler Inference...")

    hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
    hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")

    for c in hmm_feats:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    scaled_x = hmm_scaler.transform(df[hmm_feats])
    probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
    df["p_chop"] = probs[:, 0]
    df["regime"] = probs.argmax(axis=1).astype(str)

    cb_long = CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_1_long_expert.cbm")
    cb_short = CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_2_short_expert.cbm")
    all_cat_cols = joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/cat_cols.pkl") else []
    cat_set = set(all_cat_cols)

    feats_l = cb_long.feature_names_
    feats_s = cb_short.feature_names_

    for c in set(feats_l + feats_s):
        if c not in df.columns:
            df[c] = "missing" if c in cat_set else 0.0
        elif c in cat_set:
            df[c] = df[c].astype(str).fillna("missing")
        else:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    pool_l = Pool(df[feats_l], cat_features=[c for c in feats_l if c in cat_set])
    pool_s = Pool(df[feats_s], cat_features=[c for c in feats_s if c in cat_set])

    cal_l = joblib.load(f"{PROD_MODELS_DIR}/meta_calibrator_long.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/meta_calibrator_long.pkl") else None
    cal_s = joblib.load(f"{PROD_MODELS_DIR}/meta_calibrator_short.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/meta_calibrator_short.pkl") else None

    raw_pl = cb_long.predict_proba(pool_l)[:, 1]
    raw_ps = cb_short.predict_proba(pool_s)[:, 1]

    df["p_long"] = cal_l.predict(raw_pl) if cal_l and hasattr(cal_l, "predict") else raw_pl
    df["p_short"] = cal_s.predict(raw_ps) if cal_s and hasattr(cal_s, "predict") else raw_ps

    return df

# ============================================================================
# 3. TIME-STEPPED LEDGER SIMULATOR
# ============================================================================
def run_simulation(df: pd.DataFrame, policy: str = "NEW") -> tuple:
    capital = STARTING_CAPITAL
    peak_capital = capital
    max_dd = 0.0
    open_positions = []
    trade_log = []
    daily_snapshots = []

    fee_cut = FEE_SLIPPAGE_BPS / 10000.0
    timestamps = sorted(df["timestamp"].unique())

    for current_ts in timestamps:
        still_open = []
        for pos in open_positions:
            if current_ts >= pos["exit_time"]:
                capital += pos["margin"] + pos["pnl"]
                if capital > peak_capital:
                    peak_capital = capital
                trade_log.append(pos)
            else:
                still_open.append(pos)
        open_positions = still_open

        dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

        if current_ts.hour == 0:
            daily_snapshots.append({"timestamp": current_ts, "equity": capital})

        if capital <= 10.0:
            break

        if policy == "NEW":
            if dd >= 0.30:
                break
            elif dd >= 0.25:
                dd_mult = 0.10
            elif dd >= 0.20:
                dd_mult = 0.25
            elif dd >= 0.15:
                dd_mult = 0.50
            elif dd >= 0.10:
                dd_mult = 0.75
            else:
                dd_mult = 1.00
        else:
            dd_mult = 0.25 if dd >= 0.30 else (0.50 if dd >= 0.15 else 1.0)

        bar_candidates = df[df["timestamp"] == current_ts]
        active_coins = {p["coin"] for p in open_positions}
        available_slots = MAX_POSITIONS - len(open_positions)

        if available_slots <= 0:
            continue

        btc_row = bar_candidates[bar_candidates["ticker"].str.upper().isin(["BTCUSD", "BTC", "BTCUSDT"])]
        btc_mom_rank = float(btc_row["rank_mom_24h"].iloc[0]) if not btc_row.empty else 0.50
        btc_above_sma50 = str(btc_row["btc_above_sma50"].iloc[0]) == "1" if not btc_row.empty else False
        market_breadth = float(bar_candidates["market_breadth_sma20"].mean())

        macro_bull_score = (
            (0.40 * (1.0 if btc_above_sma50 else 0.0)) +
            (0.35 * btc_mom_rank) +
            (0.25 * market_breadth)
        )

        eligible = []
        for _, row in bar_candidates.iterrows():
            coin = str(row["ticker"]).replace("USDT", "").replace("USD", "").upper()
            if coin in active_coins:
                continue

            pl, ps, pc, reg = float(row["p_long"]), float(row["p_short"]), float(row["p_chop"]), str(row["regime"])
            px, atr = float(row["close"]), float(row["atr_20"])
            if px <= 0 or atr <= 0 or pc >= 0.50:
                continue

            if policy == "NEW":
                sl_pct = (1.00 * atr) / px
                tp_pct = (1.50 * atr) / px
                l_pass = (pl >= NEW_PROB_LONG and reg != "2")
                s_pass = (ps >= NEW_PROB_SHORT and macro_bull_score < 0.90 and not (macro_bull_score >= 0.75 and ps < 0.65))
            else:
                sl_pct = (1.50 * atr) / px
                tp_pct = (1.50 * atr) / px
                l_pass = (pl >= LEG_PROB_LONG and reg != "2")
                s_pass = (ps >= LEG_PROB_SHORT and reg != "1")

            if not l_pass and not s_pass:
                continue

            long_ev = (pl * tp_pct) - ((1.0 - pl) * sl_pct) - fee_cut
            short_ev = (ps * tp_pct) - ((1.0 - ps) * sl_pct) - fee_cut

            is_buy = l_pass and (not s_pass or pl >= ps)
            side, p_win, ev_val = ("BUY", pl, long_ev) if is_buy else ("SELL", ps, short_ev)

            if ev_val > 0:
                eligible.append({
                    "coin": coin, "is_buy": is_buy, "side": side, "ev": ev_val,
                    "p_win": p_win, "px": px, "atr": atr, "sl_pct": sl_pct, "tp_pct": tp_pct,
                    "target_long": row["target_long"], "target_short": row["target_short"],
                    "exit_time": row["exit_time"], "exact_gross_return": row["exact_gross_return"]
                })

        ranked = sorted(eligible, key=lambda x: x["ev"], reverse=True)
        margin_used = sum(p["margin"] for p in open_positions)
        available_margin = max(0.0, (capital * MAX_TOTAL_MARGIN_UTILIZATION) - margin_used)
        trades_this_cycle = 0

        for cand in ranked:
            if trades_this_cycle >= min(MAX_TRADES_PER_CYCLE, available_slots):
                break

            coin = cand["coin"]
            px, atr, sl_pct, p_win, is_buy = cand["px"], cand["atr"], cand["sl_pct"], cand["p_win"], cand["is_buy"]

            if policy == "NEW":
                edge_f = max(0.0, min(1.0, (p_win * (PAYOFF_RATIO + 1.0) - 1.0) / PAYOFF_RATIO))
                k_scaler = NEW_EDGE_LONG if is_buy else NEW_EDGE_SHORT
                dollar_risk = capital * NEW_HARD_MAX_RISK * edge_f * k_scaler * dd_mult
                ideal_notional = dollar_risk / sl_pct
                applied_lev = 6.0 if is_buy else 10.0
            else:
                k_frac = LEG_KELLY_LONG if is_buy else LEG_KELLY_SHORT
                applied_lev = LEG_LEV_LONG if is_buy else LEG_LEV_SHORT
                dynamic_payoff = 1.0
                kelly_f = p_win - ((1.0 - p_win) / dynamic_payoff)
                notional_pct = min(kelly_f * k_frac * applied_lev * dd_mult, 2.0)
                ideal_notional = capital * notional_pct

            max_notional = available_margin * applied_lev
            final_notional = min(ideal_notional, max_notional, HARD_LIQUIDITY_CAP)
            req_margin = final_notional / applied_lev

            if req_margin > available_margin or final_notional < 10.0:
                continue

            hit_target = (cand["target_long"] == 1) if is_buy else (cand["target_short"] == 1)
            raw_ret = cand["tp_pct"] if hit_target else -cand["sl_pct"]
            net_ret = raw_ret - fee_cut
            pnl = final_notional * net_ret

            capital -= req_margin
            available_margin -= req_margin
            trades_this_cycle += 1

            open_positions.append({
                "coin": coin, "side": cand["side"], "margin": req_margin,
                "notional": final_notional, "pnl": pnl, "net_ret": net_ret,
                "exit_time": cand["exit_time"], "hit_target": hit_target
            })
            active_coins.add(coin)

    for pos in open_positions:
        capital += pos["margin"] + pos["pnl"]
        trade_log.append(pos)

    return pd.DataFrame(trade_log), daily_snapshots, capital, max_dd

# ============================================================================
# 4. REPORT GENERATION & ENTRY POINT
# ============================================================================
def generate_metrics(trades_df: pd.DataFrame, daily_snaps: list, end_cap: float, m_dd: float, days: int) -> dict:
    n = len(trades_df)
    if n == 0:
        return {}

    wr = (trades_df["pnl"] > 0).mean() * 100.0
    cagr = ((end_cap / STARTING_CAPITAL) ** (365.0 / max(1, days)) - 1.0) * 100.0 if end_cap > 0 else -100.0
    calmar = (cagr / (m_dd * 100.0)) if m_dd > 0 else 0.0

    d_df = pd.DataFrame(daily_snaps).drop_duplicates("timestamp").set_index("timestamp")
    d_rets = d_df["equity"].pct_change().dropna()
    sharpe = (d_rets.mean() / d_rets.std() * np.sqrt(365)) if d_rets.std() > 0 else 0.0

    downside = d_rets[d_rets < 0]
    sortino = (d_rets.mean() / downside.std() * np.sqrt(365)) if len(downside) > 0 and downside.std() > 0 else 0.0

    gross_profit = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else np.nan

    worst_trade = trades_df["pnl"].min()
    worst_5_seq = trades_df["pnl"].rolling(5).sum().min()

    longs = trades_df[trades_df["side"] == "BUY"]
    shorts = trades_df[trades_df["side"] == "SELL"]

    return {
        "Final Equity ($1k Start)": f"${end_cap:>13,.2f}",
        "Net Realized PnL ($)": f"${end_cap - STARTING_CAPITAL:>13,.2f}",
        "Annualized CAGR": f"{cagr:>+13.2f}%",
        "Maximum Drawdown": f"-{m_dd*100:>12.2f}%",
        "Calmar Ratio": f"{calmar:>14.2f}",
        "Sharpe Ratio": f"{sharpe:>14.2f}",
        "Sortino Ratio": f"{sortino:>14.2f}",
        "Profit Factor": f"{profit_factor:>14.2f}",
        "Total Trades Executed": f"{n:>14}",
        "Win Rate (%)": f"{wr:>13.2f}%",
        "Worst Single Trade ($)": f"${worst_trade:>13.2f}",
        "Worst 5-Trade Sequence": f"${worst_5_seq:>13.2f}",
        "Long Realized PnL ($)": f"${longs['pnl'].sum():>13,.2f}",
        "Short Realized PnL ($)": f"${shorts['pnl'].sum():>13,.2f}"
    }


def main():
    parser = argparse.ArgumentParser(description="Run policy bakeoff backtest.")
    parser.add_argument("--days", type=int, default=90, help="Lookback days for historical simulation (default: 90)")
    args = parser.parse_args()

    print("=" * 85)
    print(f"      {args.days}-DAY HISTORICAL POLICY BAKEOFF: LEGACY vs. RISK PARITY")
    print("=" * 85)

    df_raw = load_feature_matrix(args.days)
    df_scored = score_model_probabilities(df_raw)

    print("\n[3/3] Running Side-by-Side Time-Stepped Simulations...")
    t_leg, d_leg, cap_leg, dd_leg = run_simulation(df_scored.copy(), policy="LEGACY")
    t_new, d_new, cap_new, dd_new = run_simulation(df_scored.copy(), policy="NEW")

    m_leg = generate_metrics(t_leg, d_leg, cap_leg, dd_leg, args.days)
    m_new = generate_metrics(t_new, d_new, cap_new, dd_new, args.days)

    print("\n" + "=" * 85)
    print(f"{'Performance Metric':<28} | {'Legacy Policy':<24} | {'New Risk Parity':<24}")
    print("-" * 85)
    for k in m_leg.keys():
        print(f"{k:<28} | {m_leg[k]:>24} | {m_new[k]:>24}")
    print("=" * 85 + "\n")

    t_leg.to_csv(f"bakeoff_trades_legacy_{args.days}d.csv", index=False)
    t_new.to_csv(f"bakeoff_trades_new_{args.days}d.csv", index=False)
    print(f"[SUCCESS] Trade logs saved to 'bakeoff_trades_legacy_{args.days}d.csv' and 'bakeoff_trades_new_{args.days}d.csv'\n")


if __name__ == "__main__":
    main()
