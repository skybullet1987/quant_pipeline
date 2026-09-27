import sys
import pandas as pd
from run_full_backtest import load_backtest_dataset, print_performance_analytics
from tactical_regime import TacticalRegimeEngine
import joblib
import os
import math
from catboost import CatBoostClassifier, Pool
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
PROD_MODELS_DIR = "models/prod"

# --- HIGH-OCTANE AGGRESSION CONFIG ---
INITIAL_CAPITAL = 1000.0
MAX_POSITIONS = 5
MAX_PER_SIDE = 5               # Allow 100% directional concentration (5/5 Shorts or Longs)
MAX_TRADES_PER_BAR = 3          # Faster capital deployment
FEE_SLIPPAGE_BPS = 12.0

TP_ATR_MULT = 2.20             # Expanded profit targets
SL_ATR_MULT = 1.10             # Tight stop for higher asymmetric payoff (2:1 R:R)
RISK_BUDGET_PCT = 0.040        # 4.0% equity risk per stop (High Octane)
MAX_SLOT_EQUITY_PCT = 0.80     # Up to 80% notional per slot

def run_high_octane_simulation(df):
    print("--> Initializing High-Octane Engines...")
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
        if os.path.exists(l_path): models_long[str(r)] = CatBoostClassifier().load_model(l_path)
        if os.path.exists(s_path): models_short[str(r)] = CatBoostClassifier().load_model(s_path)

    fallback_long = models_long.get("1", next(iter(models_long.values()), None))
    fallback_short = models_short.get("2", next(iter(models_short.values()), None))

    tactical_engine = TacticalRegimeEngine(bull_breadth_threshold=0.65, bear_breadth_threshold=0.30)

    equity = INITIAL_CAPITAL
    open_positions, cooldowns = {}, {}
    trade_ledger, equity_curve = [], []
    unique_bars = sorted(df["timestamp"].unique())
    print(f"--> Simulating High-Octane Run over {len(unique_bars)} periods...")

    for bar_idx, bar_ts in enumerate(unique_bars):
        bar_df = df[df["timestamp"] == bar_ts].copy()
        
        # 1. Resolve Open Positions
        closed_tickers = []
        for ticker, pos in open_positions.items():
            t_row = bar_df[bar_df["ticker"] == ticker]
            if t_row.empty: continue
            
            high, low, close = float(t_row["high"].iloc[0]), float(t_row["low"].iloc[0]), float(t_row["close"].iloc[0])
            hit_tp, hit_sl, exit_px = False, False, close

            if pos["is_buy"]:
                if high >= pos["tp_px"]: hit_tp, exit_px = True, pos["tp_px"]
                elif low <= pos["sl_px"]: hit_sl, exit_px = True, pos["sl_px"]
            else:
                if low <= pos["tp_px"]: hit_tp, exit_px = True, pos["tp_px"]
                elif high >= pos["sl_px"]: hit_sl, exit_px = True, pos["sl_px"]

            if hit_tp and hit_sl: hit_tp = False

            if hit_tp or hit_sl:
                gross_pnl = ((exit_px - pos["entry_px"]) if pos["is_buy"] else (pos["entry_px"] - exit_px)) * pos["size_tokens"]
                fee = (pos["notional"] + (exit_px * pos["size_tokens"])) * (FEE_SLIPPAGE_BPS / 10000.0 / 2.0)
                net_pnl = gross_pnl - fee
                equity += net_pnl

                trade_ledger.append({
                    "ticker": ticker, "side": "LONG" if pos["is_buy"] else "SHORT",
                    "entry_ts": pos["entry_ts"], "exit_ts": bar_ts,
                    "entry_px": pos["entry_px"], "exit_px": exit_px,
                    "size_tokens": pos["size_tokens"], "notional": pos["notional"],
                    "net_pnl": net_pnl, "outcome": "TP" if hit_tp else "SL",
                    "equity_after": equity, "duration_bars": bar_idx - pos["entry_bar_idx"]
                })
                closed_tickers.append(ticker)
                cooldowns[ticker] = bar_ts

        for t in closed_tickers: del open_positions[t]

        # 2. HMM Inference
        try:
            for c in hmm_feats: bar_df[c] = pd.to_numeric(bar_df[c], errors="coerce").fillna(0.0) if c in bar_df.columns else 0.0
            scaled_x = hmm_scaler.transform(bar_df[hmm_feats])
            probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
            bar_df["p_chop"] = probs[:, 0]
            bar_df["regime"] = probs.argmax(axis=1).astype(str)
            bar_df["hmm_regime"] = bar_df["regime"]
        except Exception:
            bar_df["p_chop"], bar_df["regime"], bar_df["hmm_regime"] = 0.0, "1", "1"

        # 3. CatBoost Inference
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

        bar_df["p_long"], bar_df["p_short"] = p_long_list, p_short_list

        # 4. Gating & Sizing
        open_syms = set(open_positions.keys())
        free_slots = max(0, MAX_POSITIONS - len(open_positions))

        if free_slots > 0 and equity > 100.0:
            eligible_candidates = []
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
                if pc >= 0.60 or (not l_pass and not s_pass): continue

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
            allocated = 0

            for cand in ranked:
                if allocated >= MAX_TRADES_PER_BAR or len(open_positions) >= MAX_POSITIONS:
                    break

                px, atr = cand["price"], cand["atr"]
                is_buy = cand["is_buy"]
                p_win = cand["p_win"]

                # High Octane Sizing: Dynamic Conviction Scaling
                dollar_risk = equity * RISK_BUDGET_PCT
                stop_dist = SL_ATR_MULT * atr
                raw_tokens = dollar_risk / max(1e-6, stop_dist)
                
                # Conviction multiplier boost
                conviction_boost = 1.0 + max(0.0, (p_win - 0.60) * 3.0)  # e.g., P=0.80 -> 1.6x
                raw_tokens *= (cand["size_mult"] * conviction_boost)
                
                target_notional = raw_tokens * px
                max_notional = equity * MAX_SLOT_EQUITY_PCT
                if target_notional > max_notional:
                    target_notional = max_notional
                    raw_tokens = target_notional / px

                if raw_tokens <= 0 or target_notional < 15.0:
                    continue

                open_positions[cand["ticker"]] = {
                    "is_buy": is_buy, "entry_px": px, "entry_ts": bar_ts,
                    "entry_bar_idx": bar_idx, "size_tokens": raw_tokens, "notional": target_notional,
                    "tp_px": px + (TP_ATR_MULT * atr) if is_buy else px - (TP_ATR_MULT * atr),
                    "sl_px": px - (SL_ATR_MULT * atr) if is_buy else px + (SL_ATR_MULT * atr),
                }
                allocated += 1

        equity_curve.append({"timestamp": bar_ts, "equity": equity, "open_positions": len(open_positions)})

    return pd.DataFrame(trade_ledger), pd.DataFrame(equity_curve)

if __name__ == "__main__":
    lookback = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    df_data = load_backtest_dataset(lookback_days=lookback)
    trades, curve = run_high_octane_simulation(df_data)
    print_performance_analytics(trades, curve)
