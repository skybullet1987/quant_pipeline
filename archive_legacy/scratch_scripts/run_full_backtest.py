import os
import sys
import math
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool
from dotenv import load_dotenv

from tactical_regime import TacticalRegimeEngine
from risk_engine import PortfolioRiskEngine

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
PROD_MODELS_DIR = "models/prod"

INITIAL_CAPITAL = 1000.0
MAX_POSITIONS = 5
MAX_PER_SIDE = 3
MAX_TRADES_PER_BAR = 2
FEE_SLIPPAGE_BPS = 12.0
MAX_TOTAL_MARGIN_UTILIZATION = 0.85

TP_ATR_MULT = 2.00
SL_ATR_MULT = 1.20
MAX_SLOT_EQUITY_PCT = 0.35
RISK_BUDGET_PCT = 0.015

def load_backtest_dataset(lookback_days=180):
    print(f"--> Pulling {lookback_days} days of 4H data from BigQuery...")
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
        WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {lookback_days} DAY)
        ORDER BY f.timestamp ASC, f.ticker ASC
    """
    df = client.query(query).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Dynamic column fallbacks matching live execution
    if "atr" not in df.columns:
        if "atr_20" in df.columns:
            df["atr"] = df["atr_20"].fillna(df["close"] * 0.02)
        elif "atr_14" in df.columns:
            df["atr"] = df["atr_14"].fillna(df["close"] * 0.02)
        else:
            df["atr"] = df["close"] * 0.02

    if "market_breadth" not in df.columns:
        df["market_breadth"] = df["market_breadth_sma20"] if "market_breadth_sma20" in df.columns else 0.50

    if "vol_expansion_ratio" not in df.columns:
        df["vol_expansion_ratio"] = 1.0

    if "btc_ret_1h" not in df.columns:
        df["btc_ret_1h"] = 0.0

    if "btc_ret_4h" not in df.columns:
        df["btc_ret_4h"] = 0.0

    print(f"--> Loaded {len(df):,} rows ({df['ticker'].nunique()} tickers).")
    return df

def run_simulation(df):
    print("--> Initializing Models and Engines...")
    hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
    hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")
    all_cat_cols = joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/cat_cols.pkl") else []
    cat_set = set(all_cat_cols)

    models_long, models_short = {}, {}
    for r in [0, 1, 2]:
        l_path = f"{PROD_MODELS_DIR}/regime_{r}_long_expert.cbm"
        s_path = f"{PROD_MODELS_DIR}/regime_{r}_short_expert.cbm"
        if os.path.exists(l_path):
            models_long[str(r)] = CatBoostClassifier().load_model(l_path)
        if os.path.exists(s_path):
            models_short[str(r)] = CatBoostClassifier().load_model(s_path)

    fallback_long = models_long.get("1", next(iter(models_long.values()), None))
    fallback_short = models_short.get("2", next(iter(models_short.values()), None))

    tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)
    risk_engine = PortfolioRiskEngine(
        risk_budget_pct=RISK_BUDGET_PCT,
        max_slot_equity_pct=MAX_SLOT_EQUITY_PCT,
        max_gross_leverage=2.00,
        atr_stop_multiplier=SL_ATR_MULT
    )

    equity = INITIAL_CAPITAL
    open_positions, cooldowns = {}, {}
    trade_ledger, equity_curve = [], []
    unique_bars = sorted(df["timestamp"].unique())
    print(f"--> Simulating across {len(unique_bars)} 4H periods...")

    for bar_idx, bar_ts in enumerate(unique_bars):
        bar_df = df[df["timestamp"] == bar_ts].copy()
        
        # 1. Resolve Open Positions against Current High/Low
        closed_tickers = []
        for ticker, pos in open_positions.items():
            t_row = bar_df[bar_df["ticker"] == ticker]
            if t_row.empty:
                continue
            
            high = float(t_row["high"].iloc[0])
            low = float(t_row["low"].iloc[0])
            close = float(t_row["close"].iloc[0])
            
            hit_tp, hit_sl, exit_px = False, False, close

            if pos["is_buy"]:
                if high >= pos["tp_px"]:
                    hit_tp, exit_px = True, pos["tp_px"]
                elif low <= pos["sl_px"]:
                    hit_sl, exit_px = True, pos["sl_px"]
            else:
                if low <= pos["tp_px"]:
                    hit_tp, exit_px = True, pos["tp_px"]
                elif high >= pos["sl_px"]:
                    hit_sl, exit_px = True, pos["sl_px"]

            if hit_tp and hit_sl:
                hit_tp = False  # Conservative assumption

            if hit_tp or hit_sl:
                gross_pnl = ((exit_px - pos["entry_px"]) if pos["is_buy"] else (pos["entry_px"] - exit_px)) * pos["size_tokens"]
                fee = (pos["notional"] + (exit_px * pos["size_tokens"])) * (FEE_SLIPPAGE_BPS / 10000.0 / 2.0)
                net_pnl = gross_pnl - fee
                equity += net_pnl

                trade_ledger.append({
                    "ticker": ticker,
                    "side": "LONG" if pos["is_buy"] else "SHORT",
                    "entry_ts": pos["entry_ts"],
                    "exit_ts": bar_ts,
                    "entry_px": pos["entry_px"],
                    "exit_px": exit_px,
                    "size_tokens": pos["size_tokens"],
                    "notional": pos["notional"],
                    "net_pnl": net_pnl,
                    "outcome": "TP" if hit_tp else "SL",
                    "equity_after": equity,
                    "duration_bars": bar_idx - pos["entry_bar_idx"]
                })
                closed_tickers.append(ticker)
                cooldowns[ticker] = bar_ts

        for t in closed_tickers:
            del open_positions[t]

        # 2. HMM Regime Inference
        try:
            for c in hmm_feats:
                bar_df[c] = pd.to_numeric(bar_df[c], errors="coerce").fillna(0.0) if c in bar_df.columns else 0.0
            scaled_x = hmm_scaler.transform(bar_df[hmm_feats])
            probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
            bar_df["p_chop"] = probs[:, 0]
            bar_df["regime"] = probs.argmax(axis=1).astype(str)
            bar_df["hmm_regime"] = bar_df["regime"]
        except Exception:
            bar_df["p_chop"] = 0.0
            bar_df["regime"] = "1"
            bar_df["hmm_regime"] = "1"

        # 3. CatBoost Multi-Regime Inference
        p_long_list, p_short_list = [], []
        for _, row in bar_df.iterrows():
            reg_val = str(row.get("regime", "1"))
            model_l = models_long.get(reg_val, fallback_long)
            model_s = models_short.get(reg_val, fallback_short)

            feats_l = model_l.feature_names_
            row_dict_l = {col: (str(reg_val) if col in ["hmm_regime", "regime"] else (str(row[col]) if col in cat_set and col in row and pd.notna(row[col]) else ("missing" if col in cat_set else (float(row[col]) if col in row and pd.notna(row[col]) else 0.0)))) for col in feats_l}
            p_long_list.append(float(model_l.predict_proba(Pool(pd.DataFrame([row_dict_l]), cat_features=[c for c in feats_l if c in cat_set]))[0, 1]))

            feats_s = model_s.feature_names_
            row_dict_s = {col: (str(reg_val) if col in ["hmm_regime", "regime"] else (str(row[col]) if col in cat_set and col in row and pd.notna(row[col]) else ("missing" if col in cat_set else (float(row[col]) if col in row and pd.notna(row[col]) else 0.0)))) for col in feats_s}
            p_short_list.append(float(model_s.predict_proba(Pool(pd.DataFrame([row_dict_s]), cat_features=[c for c in feats_s if c in cat_set]))[0, 1]))

        bar_df["p_long"] = p_long_list
        bar_df["p_short"] = p_short_list

        # 4. Gating & Allocation
        eligible_candidates = []
        open_syms = set(open_positions.keys())
        long_count = sum(1 for p in open_positions.values() if p["is_buy"])
        short_count = sum(1 for p in open_positions.values() if not p["is_buy"])
        free_slots = max(0, MAX_POSITIONS - len(open_positions))

        if free_slots > 0 and equity > 100.0:
            for _, row in bar_df.iterrows():
                ticker = str(row["ticker"])
                pl, ps, pc = float(row["p_long"]), float(row["p_short"]), float(row["p_chop"])
                reg, px, atr = str(row["regime"]), float(row["close"]), float(row["atr"])

                if px <= 0 or atr <= 0 or cooldowns.get(ticker) == bar_ts or ticker in open_syms:
                    continue

                state = tactical_engine.evaluate_state(
                    slow_regime=int(reg) if reg.isdigit() else 1,
                    btc_ret_1h=float(row["btc_ret_1h"]),
                    btc_ret_4h=float(row["btc_ret_4h"]),
                    market_breadth_sma20=float(row["market_breadth"]),
                    vol_expansion_ratio=float(row["vol_expansion_ratio"])
                )

                l_pass = (pl >= state["long_hurdle"])
                s_pass = (ps >= state["short_hurdle"])
                if pc >= 0.60 or (not l_pass and not s_pass):
                    continue

                r_win = (TP_ATR_MULT * atr) / px
                r_loss = (SL_ATR_MULT * atr) / px
                fee_cut = FEE_SLIPPAGE_BPS / 10000.0

                long_ev = (pl * r_win) - ((1.0 - pl) * r_loss) - fee_cut
                short_ev = (ps * r_win) - ((1.0 - ps) * r_loss) - fee_cut

                is_buy = l_pass and (not s_pass or pl >= ps)
                ev_val = long_ev if is_buy else short_ev
                if ev_val > 0:
                    eligible_candidates.append({
                        "ticker": ticker, "is_buy": is_buy, "ev": ev_val,
                        "p_win": pl if is_buy else ps, "size_mult": state["long_size_mult"] if is_buy else state["short_size_mult"],
                        "price": px, "atr": atr
                    })

            ranked = sorted(eligible_candidates, key=lambda x: x["ev"], reverse=True)
            allocated_this_bar = 0

            for cand in ranked:
                if allocated_this_bar >= MAX_TRADES_PER_BAR or len(open_positions) >= MAX_POSITIONS:
                    break

                is_buy = cand["is_buy"]
                if (is_buy and long_count >= MAX_PER_SIDE) or (not is_buy and short_count >= MAX_PER_SIDE):
                    continue

                px, atr = cand["price"], cand["atr"]
                raw_tokens, target_notional, modeled_risk = risk_engine.compute_order_size(
                    account_equity=float(equity), current_price=px, atr_20=atr,
                    regime_size_mult=cand["size_mult"], model_conviction=cand["p_win"], min_notional_usd=15.0
                )

                if raw_tokens <= 0 or target_notional <= 0:
                    continue

                open_positions[cand["ticker"]] = {
                    "is_buy": is_buy, "entry_px": px, "entry_ts": bar_ts,
                    "entry_bar_idx": bar_idx, "size_tokens": raw_tokens, "notional": target_notional,
                    "tp_px": px + (TP_ATR_MULT * atr) if is_buy else px - (TP_ATR_MULT * atr),
                    "sl_px": px - (SL_ATR_MULT * atr) if is_buy else px + (SL_ATR_MULT * atr),
                    "modeled_risk": modeled_risk
                }
                if is_buy:
                    long_count += 1
                else:
                    short_count += 1
                allocated_this_bar += 1

        equity_curve.append({
            "timestamp": bar_ts, "equity": equity,
            "open_positions": len(open_positions), "longs": long_count, "shorts": short_count
        })

    return pd.DataFrame(trade_ledger), pd.DataFrame(equity_curve)

def print_performance_analytics(df_trades, df_curve):
    print("\n" + "=" * 70)
    print("           QUANTITATIVE STRATEGY BACKTEST RESULTS           ")
    print("=" * 70)

    if df_trades.empty:
        print("No trades generated during the backtest period.")
        return

    start_eq = INITIAL_CAPITAL
    end_eq = df_curve["equity"].iloc[-1]
    total_ret = ((end_eq - start_eq) / start_eq) * 100.0
    days = max(1.0, (df_curve["timestamp"].iloc[-1] - df_curve["timestamp"].iloc[0]).total_seconds() / 86400.0)
    cagr = ((end_eq / start_eq) ** (365.25 / days) - 1.0) * 100.0

    df_curve["peak"] = df_curve["equity"].cummax()
    df_curve["drawdown"] = (df_curve["equity"] - df_curve["peak"]) / df_curve["peak"]
    max_dd = df_curve["drawdown"].min() * 100.0

    df_curve["bar_ret"] = df_curve["equity"].pct_change().fillna(0.0)
    mean_ret = df_curve["bar_ret"].mean() * 2190
    std_ret = df_curve["bar_ret"].std() * math.sqrt(2190)
    sharpe = (mean_ret / std_ret) if std_ret > 0 else 0.0

    total_trades = len(df_trades)
    wins = df_trades[df_trades["net_pnl"] > 0]
    losses = df_trades[df_trades["net_pnl"] <= 0]
    win_rate = (len(wins) / total_trades) * 100.0
    gross_win = wins["net_pnl"].sum()
    gross_loss = abs(losses["net_pnl"].sum())
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    
    avg_win = wins["net_pnl"].mean() if not wins.empty else 0.0
    avg_loss = losses["net_pnl"].mean() if not losses.empty else 0.0
    win_loss_ratio = (avg_win / abs(avg_loss)) if abs(avg_loss) > 0 else float("inf")
    expectancy = (win_rate/100.0 * avg_win) + ((1.0 - win_rate/100.0) * avg_loss)

    long_trades = df_trades[df_trades["side"] == "LONG"]
    short_trades = df_trades[df_trades["side"] == "SHORT"]

    print(f"Initial Balance     : ${start_eq:,.2f}")
    print(f"Ending Balance      : ${end_eq:,.2f}")
    print(f"Total Net Return    : {total_ret:>+8.2f}%")
    print(f"CAGR (Annualized)   : {cagr:>+8.2f}%")
    print(f"Max Peak-to-Trough  : {max_dd:>+8.2f}%")
    print(f"Sharpe Ratio (Ann.) : {sharpe:>8.2f}")
    print("-" * 70)
    print(f"Total Completed Trades: {total_trades}")
    print(f"Win Rate              : {win_rate:.2f}% ({len(wins)} W / {len(losses)} L)")
    print(f"Profit Factor         : {profit_factor:.2f}")
    print(f"Payoff Ratio (W/L)    : {win_loss_ratio:.2f} (Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f})")
    print(f"Trade Expectancy      : ${expectancy:.2f} per trade")
    print("-" * 70)
    print("Directional Attribution:")
    print(f"  • Longs : {len(long_trades)} trades | Win Rate: {(len(long_trades[long_trades['net_pnl']>0])/max(1, len(long_trades)))*100.0:.1f}% | PnL: ${long_trades['net_pnl'].sum():>+8.2f}")
    print(f"  • Shorts: {len(short_trades)} trades | Win Rate: {(len(short_trades[short_trades['net_pnl']>0])/max(1, len(short_trades)))*100.0:.1f}% | PnL: ${short_trades['net_pnl'].sum():>+8.2f}")
    print("=" * 70)

    df_trades.to_csv("backtest_trade_ledger.csv", index=False)
    df_curve.to_csv("backtest_equity_curve.csv", index=False)
    print("Saved 'backtest_trade_ledger.csv' and 'backtest_equity_curve.csv'.")

if __name__ == "__main__":
    lookback = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    df_data = load_backtest_dataset(lookback_days=lookback)
    trades, curve = run_simulation(df_data)
    print_performance_analytics(trades, curve)
