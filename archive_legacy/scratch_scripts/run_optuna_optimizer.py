import os
import sys
import math
import optuna
import joblib
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from dotenv import load_dotenv
from tactical_regime import TacticalRegimeEngine

optuna.logging.set_verbosity(optuna.logging.WARNING)
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
PROD_MODELS_DIR = "models/prod"
INITIAL_CAPITAL = 1000.0
FEE_SLIPPAGE_BPS = 12.0

def cache_inference_data(lookback_days=90):
    print(f"--> Pulling {lookback_days} days of multi-table features from BigQuery...")
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
    
    # ATR & breadth fallbacks
    if "atr" not in df.columns:
        df["atr"] = df["atr_20"].fillna(df["close"] * 0.02) if "atr_20" in df.columns else df["close"] * 0.02
    if "market_breadth" not in df.columns:
        df["market_breadth"] = df["market_breadth_sma20"] if "market_breadth_sma20" in df.columns else 0.50
    if "vol_expansion_ratio" not in df.columns: df["vol_expansion_ratio"] = 1.0
    if "btc_ret_1h" not in df.columns: df["btc_ret_1h"] = 0.0
    if "btc_ret_4h" not in df.columns: df["btc_ret_4h"] = 0.0

    print("--> Pre-computing HMM & CatBoost Inferences...")
    hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
    hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")
    all_cat_cols = joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/cat_cols.pkl") else []
    cat_set = set(all_cat_cols)

    models_long, models_short = {}, {}
    for r in [0, 1, 2]:
        l_path, s_path = f"{PROD_MODELS_DIR}/regime_{r}_long_expert.cbm", f"{PROD_MODELS_DIR}/regime_{r}_short_expert.cbm"
        if os.path.exists(l_path): models_long[str(r)] = CatBoostClassifier().load_model(l_path)
        if os.path.exists(s_path): models_short[str(r)] = CatBoostClassifier().load_model(s_path)

    fallback_long = models_long.get("1", next(iter(models_long.values()), None))
    fallback_short = models_short.get("2", next(iter(models_short.values()), None))

    # HMM
    for c in hmm_feats: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0) if c in df.columns else 0.0
    scaled_x = hmm_scaler.transform(df[hmm_feats])
    probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
    df["p_chop"] = probs[:, 0]
    df["regime"] = probs.argmax(axis=1).astype(str)
    df["hmm_regime"] = df["regime"]

    # CatBoost
    p_longs, p_shorts = [], []
    for _, row in df.iterrows():
        reg_val = str(row.get("regime", "1"))
        model_l, model_s = models_long.get(reg_val, fallback_long), models_short.get(reg_val, fallback_short)
        
        feats_l = model_l.feature_names_
        row_l = {col: (str(reg_val) if col in ["hmm_regime", "regime"] else (str(row[col]) if col in cat_set and col in row and pd.notna(row[col]) else ("missing" if col in cat_set else (float(row[col]) if col in row and pd.notna(row[col]) else 0.0)))) for col in feats_l}
        p_longs.append(float(model_l.predict_proba(Pool(pd.DataFrame([row_l]), cat_features=[c for c in feats_l if c in cat_set]))[0, 1]))

        feats_s = model_s.feature_names_
        row_s = {col: (str(reg_val) if col in ["hmm_regime", "regime"] else (str(row[col]) if col in cat_set and col in row and pd.notna(row[col]) else ("missing" if col in cat_set else (float(row[col]) if col in row and pd.notna(row[col]) else 0.0)))) for col in feats_s}
        p_shorts.append(float(model_s.predict_proba(Pool(pd.DataFrame([row_s]), cat_features=[c for c in feats_s if c in cat_set]))[0, 1]))

    df["p_long"] = p_longs
    df["p_short"] = p_shorts

    # Group into chronologically indexed bars
    unique_bars = sorted(df["timestamp"].unique())
    bar_groups = [df[df["timestamp"] == ts] for ts in unique_bars]
    print(f"--> Memory Cache Ready: {len(bar_groups)} 4H periods ({len(df):,} records).")
    return unique_bars, bar_groups

def simulate_trial(params, unique_bars, bar_groups, tactical_engine):
    equity = INITIAL_CAPITAL
    open_pos, cooldowns = {}, {}
    trades, curve = [], []

    tp_mult = params["tp_atr_mult"]
    sl_mult = params["sl_atr_mult"]
    risk_pct = params["risk_budget_pct"]
    max_slot_pct = params["max_slot_equity_pct"]
    max_side = params["max_per_side"]
    max_hold = params["max_hold_bars"]
    l_boost = params["long_hurdle_boost"]
    s_boost = params["short_hurdle_boost"]
    chop_thresh = params["chop_filter_threshold"]
    max_alloc_bar = params["max_trades_per_bar"]

    for b_idx, bar_df in enumerate(bar_groups):
        b_ts = unique_bars[b_idx]
        closed = []

        # 1. Resolve Active Positions
        for sym, pos in open_pos.items():
            t_row = bar_df[bar_df["ticker"] == sym]
            if t_row.empty: continue
            
            h, l, c = float(t_row["high"].iloc[0]), float(t_row["low"].iloc[0]), float(t_row["close"].iloc[0])
            hit_tp, hit_sl, hit_time = False, False, False
            exit_px = c

            if pos["is_buy"]:
                if h >= pos["tp_px"]: hit_tp, exit_px = True, pos["tp_px"]
                elif l <= pos["sl_px"]: hit_sl, exit_px = True, pos["sl_px"]
            else:
                if l <= pos["tp_px"]: hit_tp, exit_px = True, pos["tp_px"]
                elif h >= pos["sl_px"]: hit_sl, exit_px = True, pos["sl_px"]

            if hit_tp and hit_sl: hit_tp = False
            if not hit_tp and not hit_sl and (b_idx - pos["entry_b_idx"]) >= max_hold:
                hit_time, exit_px = True, c

            if hit_tp or hit_sl or hit_time:
                gross = ((exit_px - pos["entry_px"]) if pos["is_buy"] else (pos["entry_px"] - exit_px)) * pos["size"]
                fee = (pos["notional"] + (exit_px * pos["size"])) * (FEE_SLIPPAGE_BPS / 10000.0 / 2.0)
                net = gross - fee
                equity += net
                trades.append(net)
                closed.append(sym)
                cooldowns[sym] = b_ts

        for s in closed: del open_pos[s]

        # 2. Gate & Allocate
        free = max(0, 5 - len(open_pos))
        long_c = sum(1 for p in open_pos.values() if p["is_buy"])
        short_c = sum(1 for p in open_pos.values() if not p["is_buy"])

        if free > 0 and equity > 100.0:
            cands = []
            for _, r in bar_df.iterrows():
                sym = str(r["ticker"])
                pl, ps, pc = float(r["p_long"]), float(r["p_short"]), float(r["p_chop"])
                px, atr = float(r["close"]), float(r["atr"])

                if px <= 0 or atr <= 0 or cooldowns.get(sym) == b_ts or sym in open_pos: continue

                state = tactical_engine.evaluate_state(
                    slow_regime=int(r["regime"]) if str(r["regime"]).isdigit() else 1,
                    btc_ret_1h=float(r["btc_ret_1h"]), btc_ret_4h=float(r["btc_ret_4h"]),
                    market_breadth_sma20=float(r["market_breadth"]), vol_expansion_ratio=float(r["vol_expansion_ratio"])
                )

                l_hurdle = state["long_hurdle"] + l_boost
                s_hurdle = state["short_hurdle"] + s_boost

                l_pass = (pl >= l_hurdle)
                s_pass = (ps >= s_hurdle)
                if pc >= chop_thresh or (not l_pass and not s_pass): continue

                is_buy = l_pass and (not s_pass or pl >= ps)
                p_win = pl if is_buy else ps
                r_win = (tp_mult * atr) / px
                r_loss = (sl_mult * atr) / px
                ev = (p_win * r_win) - ((1.0 - p_win) * r_loss) - (FEE_SLIPPAGE_BPS / 10000.0)

                if ev > 0:
                    cands.append({"sym": sym, "is_buy": is_buy, "ev": ev, "px": px, "atr": atr, "p_win": p_win})

            ranked = sorted(cands, key=lambda x: x["ev"], reverse=True)
            alloc = 0
            for cand in ranked:
                if alloc >= max_alloc_bar or len(open_pos) >= 5: break
                if cand["is_buy"] and long_c >= max_side: continue
                if not cand["is_buy"] and short_c >= max_side: continue

                stop_dist = sl_mult * cand["atr"]
                raw_tokens = (equity * risk_pct) / max(1e-6, stop_dist)
                target_notional = min(equity * max_slot_pct, raw_tokens * cand["px"])
                raw_tokens = target_notional / cand["px"]

                if raw_tokens <= 0 or target_notional < 15.0: continue

                open_pos[cand["sym"]] = {
                    "is_buy": cand["is_buy"], "entry_px": cand["px"], "entry_b_idx": b_idx,
                    "size": raw_tokens, "notional": target_notional,
                    "tp_px": cand["px"] + (tp_mult * cand["atr"]) if cand["is_buy"] else cand["px"] - (tp_mult * cand["atr"]),
                    "sl_px": cand["px"] - (sl_mult * cand["atr"]) if cand["is_buy"] else cand["px"] + (sl_mult * cand["atr"]),
                }
                if cand["is_buy"]: long_c += 1
                else: short_c += 1
                alloc += 1

        curve.append(equity)

    if not trades or len(trades) < 50:
        return -100.0, 0.0, 0.0, 0.0, 0.0, 0, INITIAL_CAPITAL

    # Performance Analytics
    e_end = curve[-1]
    tot_ret = ((e_end - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100.0
    days = max(1.0, (unique_bars[-1] - unique_bars[0]).total_seconds() / 86400.0)
    cagr = ((e_end / INITIAL_CAPITAL) ** (365.25 / days) - 1.0) * 100.0

    peak = pd.Series(curve).cummax()
    max_dd = ((pd.Series(curve) - peak) / peak).min() * 100.0

    # Friction-penalized score: Calmar Ratio with heavy drawdown penalties
    if abs(max_dd) < 1e-4: max_dd = -0.5
    calmar = (cagr / abs(max_dd))

    wins = [t for t in trades if t > 0]
    losses = [abs(t) for t in trades if t <= 0]
    pf = (sum(wins) / sum(losses)) if sum(losses) > 0 else 0.0
    wr = (len(wins) / len(trades)) * 100.0

    # Severe penalty for excess risk
    if abs(max_dd) > 28.0 or e_end < INITIAL_CAPITAL:
        calmar -= 50.0

    return calmar, tot_ret, cagr, max_dd, pf, wr, len(trades), e_end

def run_optuna_study(n_trials=150):
    unique_bars, bar_groups = cache_inference_data(lookback_days=90)
    tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)
    
    trials_records = []

    def objective(trial):
        params = {
            "tp_atr_mult": trial.suggest_float("tp_atr_mult", 1.80, 3.50, step=0.10),
            "sl_atr_mult": trial.suggest_float("sl_atr_mult", 1.20, 2.20, step=0.10),
            "risk_budget_pct": trial.suggest_float("risk_budget_pct", 0.015, 0.035, step=0.005),
            "max_slot_equity_pct": trial.suggest_float("max_slot_equity_pct", 0.30, 0.65, step=0.05),
            "max_per_side": trial.suggest_int("max_per_side", 2, 4),
            "max_hold_bars": trial.suggest_int("max_hold_bars", 6, 18),
            "long_hurdle_boost": trial.suggest_float("long_hurdle_boost", 0.00, 0.14, step=0.02),
            "short_hurdle_boost": trial.suggest_float("short_hurdle_boost", -0.04, 0.04, step=0.01),
            "chop_filter_threshold": trial.suggest_float("chop_filter_threshold", 0.50, 0.70, step=0.05),
            "max_trades_per_bar": trial.suggest_int("max_trades_per_bar", 1, 2)
        }

        score, ret, cagr, dd, pf, wr, n_tr, e_end = simulate_trial(params, unique_bars, bar_groups, tactical_engine)
        
        trials_records.append({
            "trial": trial.number, "score": score, "net_return": ret, "cagr": cagr,
            "max_dd": dd, "profit_factor": pf, "win_rate": wr, "trades": n_tr,
            "ending_equity": e_end, **params
        })
        return score

    print(f"\n--> Launching Bayesian Hyperparameter Optimization ({n_trials} Trials)...")
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials)

    # Output Rankings
    df_results = pd.DataFrame(trials_records).sort_values(by="score", ascending=False)
    df_results.to_csv("optuna_parameter_study.csv", index=False)

    print("\n" + "=" * 90)
    print("                    TOP 5 OPTUNA STRATEGY CONFIGURATIONS                     ")
    print("=" * 90)
    
    display_cols = ["trial", "net_return", "cagr", "max_dd", "profit_factor", "win_rate", "trades", "tp_atr_mult", "sl_atr_mult", "risk_budget_pct", "max_slot_equity_pct", "max_per_side", "max_hold_bars"]
    print(df_results[display_cols].head(5).to_string(index=False))
    print("=" * 90)
    print("Saved full optimization ledger to 'optuna_parameter_study.csv'.")

if __name__ == "__main__":
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    run_optuna_study(n_trials=trials)
