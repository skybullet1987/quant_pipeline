#!/usr/bin/env python3
"""
High-Octane Compounding OOS Backtest Engine (Testnet Parameter Parity)
Usage:
    python3 run_high_octane_production_backtest.py --days 90
    python3 run_high_octane_production_backtest.py --days 30
"""

import os
import sys
import json
import joblib
import requests
import argparse
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool

warnings.filterwarnings("ignore")

# ============================================================================
# 1. PARAMETERS (EXACT MATCH TO TESTNET DAEMON)
# ============================================================================
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
STARTING_CAPITAL = 1000.0
MAX_POSITIONS = 5
MAX_TRADES_PER_CYCLE = 2
MAX_TOTAL_MARGIN_UTILIZATION = 0.85
HARD_LIQUIDITY_CAP_USD = 150000.0
FEE_SLIPPAGE_BPS = 15.0
MAX_HOLD_HOURS = 72

# Alpha & Compounding Parameters
ENTRY_THRESHOLD_LONG = 0.58
ENTRY_THRESHOLD_SHORT = 0.52
KELLY_FRACTION_LONG = 0.20
KELLY_FRACTION_SHORT = 0.50
LEVERAGE_LONG = 3.0
LEVERAGE_SHORT = 10.0


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


def get_hyperliquid_max_leverage() -> dict:
    try:
        resp = requests.post("https://api.hyperliquid.xyz/info", json={"type": "meta"}, timeout=5)
        return {a["name"]: a["maxLeverage"] for a in resp.json().get("universe", [])}
    except Exception:
        return {}


# ============================================================================
# 2. BIGQUERY DATA INGESTION & MODEL SCORING
# ============================================================================
def load_feature_matrix(days: int) -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)
    print(f"\n[1/3] Querying historical feature store for the last {days} days...")

    query = f"""
        WITH max_time AS (
            SELECT MAX(signal_time) AS max_ts 
            FROM `{PROJECT_ID}.market_data.fct_exact_path_resolution`
        )
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
        CROSS JOIN max_time
        WHERE f.timestamp >= TIMESTAMP_SUB(max_time.max_ts, INTERVAL {days} DAY)
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
# 3. TIME-STEPPED LEDGER & DRAWDOWN LADDER SIMULATION
# ============================================================================
def calculate_drawdown_multiplier(drawdown: float) -> float:
    if drawdown >= 0.30:
        return 0.0
    elif drawdown >= 0.25:
        return 0.10
    elif drawdown >= 0.20:
        return 0.25
    elif drawdown >= 0.15:
        return 0.50
    elif drawdown >= 0.10:
        return 0.75
    return 1.00


def run_high_octane_simulation(df: pd.DataFrame) -> tuple:
    hl_max_lev_map = get_hyperliquid_max_leverage()

    capital = STARTING_CAPITAL
    peak_capital = capital
    max_dd = 0.0
    open_positions = []
    trade_log = []
    daily_snapshots = []
    circuit_breaker_tripped = False

    fee_cut = FEE_SLIPPAGE_BPS / 10000.0
    timestamps = sorted(df["timestamp"].unique())

    for current_ts in timestamps:
        # 1. Process Exits
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

        # Drawdown Tracking
        dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

        if current_ts.hour == 0:
            daily_snapshots.append({"timestamp": current_ts, "equity": capital})

        dd_mult = calculate_drawdown_multiplier(dd)
        if dd_mult == 0.0:
            circuit_breaker_tripped = True
            break

        if capital <= 10.0:
            break

        # 2. Evaluate Candidates (Pass 1)
        bar_candidates = df[df["timestamp"] == current_ts]
        active_coins = {p["coin"] for p in open_positions}
        available_slots = MAX_POSITIONS - len(open_positions)

        if available_slots <= 0:
            continue

        eligible = []
        for _, row in bar_candidates.iterrows():
            coin = str(row["ticker"]).replace("USDT", "").replace("USD", "").upper()
            if coin in active_coins:
                continue

            pl, ps, pc, reg = float(row["p_long"]), float(row["p_short"]), float(row["p_chop"]), str(row["regime"])
            px, atr = float(row["close"]), float(row["atr_20"])
            if px <= 0 or atr <= 0 or pc >= 0.50:
                continue

            l_pass = (pl >= ENTRY_THRESHOLD_LONG and reg != "2")
            s_pass = (ps >= ENTRY_THRESHOLD_SHORT and reg != "1")

            if not l_pass and not s_pass:
                continue

            r_dist = (1.50 * atr) / px
            long_ev = (((2.0 * pl) - 1.0) * r_dist) - fee_cut
            short_ev = (((2.0 * ps) - 1.0) * r_dist) - fee_cut

            is_buy = l_pass and (not s_pass or pl >= ps)
            side, p_win, ev_val = ("BUY", pl, long_ev) if is_buy else ("SELL", ps, short_ev)
            k_frac = KELLY_FRACTION_LONG if is_buy else KELLY_FRACTION_SHORT
            base_lev = LEVERAGE_LONG if is_buy else LEVERAGE_SHORT

            if ev_val > 0:
                eligible.append({
                    "coin": coin, "is_buy": is_buy, "side": side, "ev": ev_val,
                    "p_win": p_win, "k_frac": k_frac, "base_lev": base_lev,
                    "px": px, "atr": atr, "r_dist": r_dist,
                    "target_long": row["target_long"], "target_short": row["target_short"],
                    "exit_time": row["exit_time"], "exact_gross_return": row["exact_gross_return"]
                })

        # 3. Two-Pass Ranking & Allocation (Pass 2)
        ranked = sorted(eligible, key=lambda x: x["ev"], reverse=True)
        margin_used = sum(p["margin"] for p in open_positions)
        available_margin = max(0.0, (capital * MAX_TOTAL_MARGIN_UTILIZATION) - margin_used)
        trades_this_cycle = 0

        for cand in ranked:
            if trades_this_cycle >= min(MAX_TRADES_PER_CYCLE, available_slots):
                break

            coin = cand["coin"]
            p_win = cand["p_win"]
            k_frac = cand["k_frac"]
            is_buy = cand["is_buy"]

            # High-Octane 10x Kelly Sizing: f* = 2p - 1
            kelly_f = p_win - ((1.0 - p_win) / 1.0)
            coin_max_lev = float(hl_max_lev_map.get(coin, cand["base_lev"]))
            applied_lev = min(coin_max_lev, cand["base_lev"])

            trade_notional_pct = min(kelly_f * k_frac * applied_lev * dd_mult, 2.0)
            ideal_notional = capital * trade_notional_pct

            max_notional = available_margin * applied_lev
            final_notional = min(ideal_notional, max_notional, HARD_LIQUIDITY_CAP_USD)
            req_margin = final_notional / applied_lev

            if req_margin > available_margin or final_notional < 10.0:
                continue

            hit_target = (cand["target_long"] == 1) if is_buy else (cand["target_short"] == 1)
            raw_ret = cand["r_dist"] if hit_target else -cand["r_dist"]
            net_ret = raw_ret - fee_cut
            pnl = final_notional * net_ret

            capital -= req_margin
            available_margin -= req_margin
            trades_this_cycle += 1

            open_positions.append({
                "coin": coin, "side": cand["side"], "margin": req_margin,
                "notional": final_notional, "pnl": pnl, "net_ret": net_ret,
                "entry_time": current_ts, "exit_time": cand["exit_time"],
                "hit_target": hit_target, "leverage": applied_lev
            })
            active_coins.add(coin)

    # Flush open positions
    for pos in open_positions:
        capital += pos["margin"] + pos["pnl"]
        trade_log.append(pos)

    return pd.DataFrame(trade_log), daily_snapshots, capital, max_dd, circuit_breaker_tripped

# ============================================================================
# 4. REPORTING & DRAWDOWN AUTOPSY
# ============================================================================
def print_comprehensive_audit(trades_df: pd.DataFrame, daily_snaps: list, final_capital: float, max_dd: float, cb_tripped: bool, days: int):
    print("\n" + "=" * 90)
    print(f"       HIGH-OCTANE PRODUCTION BACKTEST AUDIT (LAST {days} DAYS)")
    print("=" * 90)

    total_trades = len(trades_df)
    if total_trades == 0:
        print("[ERROR] Zero trades executed.")
        return

    net_pnl = final_capital - STARTING_CAPITAL
    cagr = ((final_capital / STARTING_CAPITAL) ** (365.0 / max(1, days)) - 1.0) * 100.0 if final_capital > 0 else -100.0
    calmar = (cagr / (max_dd * 100.0)) if max_dd > 0 else 0.0

    wins = trades_df[trades_df["pnl"] > 0]
    win_rate = (len(wins) / total_trades) * 100.0

    gross_profit = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else np.nan

    d_df = pd.DataFrame(daily_snaps).drop_duplicates("timestamp").set_index("timestamp")
    d_rets = d_df["equity"].pct_change().dropna()
    sharpe = (d_rets.mean() / d_rets.std() * np.sqrt(365)) if d_rets.std() > 0 else 0.0

    downside = d_rets[d_rets < 0]
    sortino = (d_rets.mean() / downside.std() * np.sqrt(365)) if len(downside) > 0 and downside.std() > 0 else 0.0

    worst_trade = trades_df["pnl"].min()
    worst_5_seq = trades_df["pnl"].rolling(5).sum().min()

    long_trades = trades_df[trades_df["side"] == "BUY"]
    short_trades = trades_df[trades_df["side"] == "SELL"]

    print(f"Starting Capital:            ${STARTING_CAPITAL:,.2f}")
    print(f"Ending Equity:               ${final_capital:,.2f}")
    print(f"Total Net PnL:               ${net_pnl:>+12,.2f} ({(final_capital/STARTING_CAPITAL - 1)*100:+.2f}%)")
    print(f"Annualized CAGR:             {cagr:>+12.2f}%")
    print(f"Maximum Drawdown:           -{max_dd * 100.0:>11.2f}%")
    print(f"Circuit Breaker Status:      {'TRIPPED (>=30% HALT)' if cb_tripped else 'CLEAN (Continuous)'}")
    print(f"Calmar Ratio:                {calmar:>12.2f}")
    print(f"Sharpe Ratio:                {sharpe:>12.2f}")
    print(f"Sortino Ratio:               {sortino:>12.2f}")
    print(f"Profit Factor:               {profit_factor:>12.2f}")
    print("-" * 90)
    print(f"Total Trades Executed:       {total_trades}")
    print(f"  ├── Long Trades:           {len(long_trades):>4}  (Win Rate: {(long_trades['pnl']>0).mean()*100:.1f}% | PnL: ${long_trades['pnl'].sum():>+9,.2f})")
    print(f"  └── Short Trades:          {len(short_trades):>4}  (Win Rate: {(short_trades['pnl']>0).mean()*100:.1f}% | PnL: ${short_trades['pnl'].sum():>+9,.2f})")
    print(f"Overall Win Rate:            {win_rate:.2f}% ({len(wins)}/{total_trades})")
    print(f"Worst Single Trade Loss:     ${worst_trade:,.2f}")
    print(f"Worst 5-Trade Sequence PnL:  ${worst_5_seq:,.2f}")

    # Drawdown Autopsy Decomposition
    print("\n" + "-" * 90)
    print("                      TOP DRAWDOWN EPISODE AUTOPSY")
    print("-" * 90)
    eq_curve = [STARTING_CAPITAL] + list(trades_df["pnl"].cumsum() + STARTING_CAPITAL)
    eq_arr = np.array(eq_curve)
    peaks = np.maximum.accumulate(eq_arr)
    drawdowns = (eq_arr - peaks) / peaks
    max_idx = np.argmin(drawdowns)
    peak_idx = np.argmax(eq_arr[:max_idx + 1]) if max_idx > 0 else 0

    print(f"Peak Equity:                 ${eq_arr[peak_idx]:,.2f} (Trade #{peak_idx})")
    print(f"Trough Equity:               ${eq_arr[max_idx]:,.2f} (Trade #{max_idx})")
    print(f"Max Drawdown Depth:         -{abs(drawdowns[max_idx]) * 100.0:.2f}%")
    print(f"Episode Duration:            {max_idx - peak_idx} trades")

    # Export Trade Logs
    out_file = f"high_octane_trades_{days}d.csv"
    trades_df.to_csv(out_file, index=False)
    print(f"\n[SUCCESS] Granular trade execution log exported to: {out_file}\n" + "=" * 90 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run High-Octane OOS Backtest.")
    parser.add_argument("--days", type=int, default=90, help="Lookback days (default: 90)")
    args = parser.parse_args()

    df_raw = load_feature_matrix(args.days)
    df_scored = score_model_probabilities(df_raw)

    print("\n[3/3] Simulating Time-Stepped High-Octane Compounding...")
    trades_df, daily_snaps, final_cap, max_dd, cb_tripped = run_high_octane_simulation(df_scored)
    print_comprehensive_audit(trades_df, daily_snaps, final_cap, max_dd, cb_tripped, args.days)


if __name__ == "__main__":
    main()
