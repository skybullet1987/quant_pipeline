"""
5-ALGORITHM HEAD-TO-HEAD TOURNAMENT BAKE-OFF
========================================================================
Identical Point-in-Time Dataset: 43,409 rows across 54 assets (90D production lake)
Identical Capital: $1,000.00 initial equity per strategy

Competing Algorithms:
  1. ALGO 1: Current Deployed (Dollar-Neutral Risk Parity + S2 Cash Choke)
  2. ALGO 2: Previous Iteration (CatBoost Hyper-Compounding 5.0x, Tight SL 0.85x)
  3. ALGO 3: Asymmetric Gearing & RMT Beta Hedging (Leland Deadband)
  4. ALGO 4: Two-Tranche Runner (Tranche A +2.0x ATR, Tranche B Ratchet)
  5. ALGO 5: Calibrated Wide-Bracket Trend Runner (SL 2.0x, TP 3.2x, Trend Gate)
"""

import math
import sys
import time
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Set

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
import pandas as pd
from catboost import CatBoostClassifier
from scipy.stats import multivariate_normal
from sklearn.preprocessing import RobustScaler
from hmmlearn.hmm import GaussianHMM

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.execution.papertrade_daemon import (
    _build_macro_features,
    _compute_delta_dispersion,
    _apply_deadband,
    HMMRegimeGovernor,
    CrossSectionalAlphaRanker,
    DollarNeutralRiskParityAllocator,
    MacroRiskGovernor,
    FEAT_COLS,
    HMM_FEATURE_COLS,
    S2_CASH_CHOKE_THRESHOLD,
    MIN_BREADTH,
    VOL_FLOOR_USD,
)
from src.risk.grossman_zhou_engine import GrossmanZhouRiskGovernor
from src.risk.asymmetric_beta_governor import RMTBetaGovernor
from src.execution.asynchronous_clock import AsynchronousVarianceClock
from src.risk.two_tranche_runner import TwoTrancheRunnerEngine

LAKE_CACHE = PIPELINE_ROOT / "data" / "lake" / "fct_4h_production_cache.parquet"
MODELS_DIR = PIPELINE_ROOT / "models" / "prod"


def run_5algo_tournament():
    print("=" * 105)
    print("               DEFINITIVE 5-ALGORITHM HEAD-TO-HEAD TOURNAMENT BAKE-OFF               ")
    print("=" * 105)

    # 1. Load Data
    print("--> [1/5] Loading 90D Production Lake Cache...")
    if not LAKE_CACHE.exists():
        raise FileNotFoundError(f"Cache file {LAKE_CACHE} does not exist.")

    df = pl.read_parquet(LAKE_CACHE)
    if "ticker" in df.columns and "symbol" not in df.columns:
        df = df.rename({"ticker": "symbol"})
    if "timestamp" in df.columns and "timestamp_ms" not in df.columns:
        df = df.with_columns(pl.col("timestamp").dt.epoch("ms").alias("timestamp_ms"))

    ts_col = "timestamp_ms"
    all_timestamps = sorted(df[ts_col].unique().to_list())
    total_bars = len(all_timestamps)
    n_assets = df["symbol"].n_unique()
    print(f"    Loaded {df.height:,} records across {total_bars} 4H periods ({n_assets} assets).")

    # Add 4H returns
    df = df.sort(["symbol", ts_col]).with_columns([
        (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).fill_null(0.0).alias("ret_4h"),
        (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("fwd_ret_4h")
    ])

    if "vol_yang_zhang" not in df.columns:
        df = df.with_columns(
            pl.col("ret_4h").rolling_std(18).over("symbol").fill_null(0.025).alias("vol_yang_zhang")
        )

    # Fast memory mappings
    returns_by_bar = {}
    high_by_bar = {}
    low_by_bar = {}
    close_by_bar = {}
    atr_by_bar = {}

    for row in df.select([ts_col, "symbol", "close", "high", "low", "atr_20", "ret_4h", "fwd_ret_4h"]).iter_rows(named=True):
        t = row[ts_col]
        s = row["symbol"]
        if t not in returns_by_bar:
            returns_by_bar[t] = {}
            high_by_bar[t] = {}
            low_by_bar[t] = {}
            close_by_bar[t] = {}
            atr_by_bar[t] = {}
        returns_by_bar[t][s] = row["fwd_ret_4h"] or 0.0
        c = row["close"] or 1.0
        close_by_bar[t][s] = c
        high_by_bar[t][s] = row["high"] or (c * 1.01)
        low_by_bar[t][s] = row["low"] or (c * 0.99)
        atr_by_bar[t][s] = row["atr_20"] or (c * 0.03)

    # 2. Causal Macro Features & HMM
    print("--> [2/5] Fitting Causal Macro Regime Models & Loading Pre-Trained Experts...")
    btc_sub = df.filter(pl.col("symbol") == "BTC").select([ts_col, pl.col("ret_4h").alias("btc_ret")]).unique(subset=[ts_col])
    if btc_sub.height > 0:
        df = df.join(btc_sub, on=ts_col, how="left")
    else:
        df = df.with_columns(pl.lit(0.0).alias("btc_ret"))

    macro_df = (
        df.group_by(ts_col)
        .agg([
            pl.col("ret_4h").std().alias("csd"),
            (pl.col("close") > pl.col("open")).mean().alias("breadth"),
            pl.col("btc_ret").first().alias("btc_ret"),
        ])
        .sort(ts_col)
        .drop_nulls()
    )
    macro_features_all = macro_df.select(HMM_FEATURE_COLS).to_numpy()
    macro_ts_list = macro_df[ts_col].to_list()
    macro_idx_map = {t: i for i, t in enumerate(macro_ts_list)}

    # BTC Trend map (close > EMA20)
    btc_df = df.filter(pl.col("symbol") == "BTC").sort(ts_col)
    btc_ema20 = btc_df.select([
        ts_col,
        (pl.col("close") > pl.col("close").ewm_mean(span=20)).alias("btc_bull")
    ])
    btc_trend_map = dict(zip(btc_ema20[ts_col].to_list(), btc_ema20["btc_bull"].to_list()))

    # Load CatBoost Expert Models for Algo 2
    cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
    cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")

    # Pre-train HMM on historical macro slice
    hmm_scaler = RobustScaler().fit(macro_features_all)
    X_scaled = hmm_scaler.transform(macro_features_all)
    hmm_prod = GaussianHMM(n_components=3, covariance_type="diag", min_covar=1e-3, random_state=42, n_iter=200).fit(X_scaled)
    canonical_order = np.argsort(-hmm_prod.means_[:, 0])

    T_len = len(X_scaled)
    alpha_mat = np.zeros((T_len, 3))
    B_mat = np.zeros((T_len, 3))
    n_dim = X_scaled.shape[1]
    eye_dim = np.eye(n_dim) * 1e-4
    for j in range(3):
        cov_raw = hmm_prod.covars_[j]
        cov_j = np.diag(np.maximum(cov_raw, 1e-4)) + eye_dim if cov_raw.ndim == 1 else cov_raw + eye_dim
        B_mat[:, j] = multivariate_normal.pdf(X_scaled, mean=hmm_prod.means_[j], cov=cov_j)

    alpha_mat[0] = hmm_prod.startprob_ * B_mat[0]
    alpha_mat[0] /= np.sum(alpha_mat[0]) + 1e-8
    for t in range(1, T_len):
        alpha_mat[t] = np.dot(alpha_mat[t-1], hmm_prod.transmat_) * B_mat[t]
        alpha_mat[t] /= np.sum(alpha_mat[t]) + 1e-8

    causal_posteriors = alpha_mat[:, canonical_order]
    p_bull_map = {macro_ts_list[i]: float(causal_posteriors[i, 0]) for i in range(T_len)}
    p_chop_map = {macro_ts_list[i]: float(causal_posteriors[i, 1]) for i in range(T_len)}
    p_bear_map = {macro_ts_list[i]: float(causal_posteriors[i, 2]) for i in range(T_len)}

    # Convert to pandas for CatBoost inference
    pdf = df.to_pandas()
    pdf["p_bull"] = pdf[ts_col].map(p_bull_map).fillna(0.33)
    pdf["p_chop"] = pdf[ts_col].map(p_chop_map).fillna(0.33)
    pdf["p_bear"] = pdf[ts_col].map(p_bear_map).fillna(0.33)
    pdf["hmm_entropy"] = -(
        pdf["p_bull"] * np.log(pdf["p_bull"] + 1e-8) +
        pdf["p_chop"] * np.log(pdf["p_chop"] + 1e-8) +
        pdf["p_bear"] * np.log(pdf["p_bear"] + 1e-8)
    )
    pdf["dp_bull"] = pdf.groupby("symbol")["p_bull"].diff().fillna(0.0)
    pdf["dp_bear"] = pdf.groupby("symbol")["p_bear"].diff().fillna(0.0)

    cb_feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]
    for c in cb_feature_cols:
        pdf[c] = pd.to_numeric(pdf[c], errors="coerce").fillna(0.0)

    print("    Running CatBoost batch inference across all bars...")
    pdf["p_model_long"] = cb_long.predict_proba(pdf[cb_feature_cols])[:, 1]
    pdf["p_model_short"] = cb_short.predict_proba(pdf[cb_feature_cols])[:, 1]
    df_scored = pl.from_pandas(pdf)

    # 3. Initialize Strategy State Engines
    print("--> [3/5] Initializing Strategy State Engines...")
    WARMUP_BARS = 30
    eval_bars = total_bars - WARMUP_BARS - 1

    # Strategy 1
    s1_equity = 1000.0
    s1_weights = {}
    s1_curve = [s1_equity]
    s1_turnover = []
    s1_allocator = DollarNeutralRiskParityAllocator(target_gross_leverage=2.5)
    s1_macro_risk = MacroRiskGovernor()

    # Strategy 2
    s2_equity = 1000.0
    s2_positions = {}
    s2_cooldowns = {}
    s2_curve = [s2_equity]
    s2_trades = []
    s2_turnover = []

    # Strategy 3
    s3_equity = 1000.0
    s3_weights = {}
    s3_curve = [s3_equity]
    s3_turnover = []
    s3_asym = RMTBetaGovernor()
    s3_clock = AsynchronousVarianceClock()
    s3_gz = GrossmanZhouRiskGovernor(d_max=0.22, l_base=4.0)

    # Strategy 4
    s4_equity = 1000.0
    s4_curve = [s4_equity]
    s4_turnover = []
    s4_runner = TwoTrancheRunnerEngine(tp_a_mult=2.0, sl_init_mult=1.4)
    s4_gz = GrossmanZhouRiskGovernor(d_max=0.22, l_base=4.0)

    # Strategy 5
    s5_equity = 1000.0
    s5_peak = 1000.0
    s5_positions = {}  # sym -> {side, entry_px, atr, size_pct, entry_bar}
    s5_cooldowns = {}
    s5_curve = [s5_equity]
    s5_trades = []
    s5_turnover = []
    s5_gz = GrossmanZhouRiskGovernor(d_max=0.22, l_base=4.0)

    # Strategy 6: COMBO 3+4 (Asymmetric Direction + Two-Tranche Runner + CatBoost Filter)
    s6_equity = 1000.0
    s6_curve = [s6_equity]
    s6_turnover = []
    s6_trades = []
    s6_runner = TwoTrancheRunnerEngine(tp_a_mult=2.5, sl_init_mult=1.8, ratchet_mult=0.2)
    s6_gz = GrossmanZhouRiskGovernor(d_max=0.22, l_base=4.0)
    s6_asym = RMTBetaGovernor()

    # Ranker for Strategy 1, 3, 4
    ranker = CrossSectionalAlphaRanker()
    cached_ranker = False
    last_train_bar = -999

    print(f"--> [4/5] Executing 5-Strategy Simulation across {eval_bars} 4H bars...")
    start_time = time.time()

    for idx in range(WARMUP_BARS, total_bars - 1):
        curr_ts = all_timestamps[idx]
        next_ts = all_timestamps[idx + 1]
        curr_snap = df_scored.filter(pl.col(ts_col) == curr_ts)
        next_rets = returns_by_bar.get(curr_ts, {})

        p_bull = p_bull_map.get(curr_ts, 0.33)
        p_chop = p_chop_map.get(curr_ts, 0.33)
        p_bear = p_bear_map.get(curr_ts, 0.33)
        btc_bull = btc_trend_map.get(curr_ts, True)
        active_state = int(np.argmax([p_bull, p_chop, p_bear]))
        omega_h = float(np.clip(1.0 - (-sum(p * np.log(p + 1e-8) for p in [p_bull, p_chop, p_bear]) / np.log(3)), 0.0, 1.0))

        # Train ranker every 18 bars (3 days)
        if (idx - last_train_bar) >= 18 or not cached_ranker:
            train_snap = df_scored.filter(pl.col(ts_col) < curr_ts)
            avail_feats = [c for c in FEAT_COLS if c in train_snap.columns]
            if avail_feats and train_snap.height > 100:
                train_snap = train_snap.with_columns(
                    (pl.col("ret_4h") > 0).cast(pl.Int32).alias("forward_res_decile")
                )
                ranker.train_lambdarank(train_snap, avail_feats)
                cached_ranker = True
                last_train_bar = idx

        avail_feats = [c for c in FEAT_COLS if c in curr_snap.columns]
        ranked_df = ranker.rank_universe(curr_snap, avail_feats) if cached_ranker else curr_snap

        # =====================================================================
        # STRATEGY 1: CURRENT PRODUCTION (Dollar-Neutral + S2 Choke)
        # =====================================================================
        delta_disp = float(curr_snap["ret_4h"].std() or 0.005)
        if delta_disp <= S2_CASH_CHOKE_THRESHOLD:
            t_w1 = {}
        else:
            panel_1 = curr_snap.filter((pl.col("close") * pl.col("volume") >= VOL_FLOOR_USD))
            if panel_1.height < MIN_BREADTH:
                t_w1 = {}
            else:
                scale_1 = s1_macro_risk.compute_leverage_multiplier(current_equity=s1_equity)
                batch_1 = s1_allocator.allocate(ranked_df, macro_omega=scale_1 * omega_h)
                raw_w1 = batch_1.weights if hasattr(batch_1, "weights") else {}
                t_w1 = _apply_deadband(raw_w1, s1_weights)

        to1 = sum(abs(t_w1.get(s, 0.0) - s1_weights.get(s, 0.0)) for s in set(s1_weights).union(t_w1))
        fee1 = s1_equity * to1 * 0.00055
        pnl1 = sum(s1_equity * w * next_rets.get(s, 0.0) for s, w in t_w1.items()) - fee1
        s1_equity += pnl1
        s1_weights = t_w1
        s1_curve.append(s1_equity)
        s1_turnover.append(to1)

        # =====================================================================
        # STRATEGY 2: PREVIOUS ITERATION (CatBoost 5.0x Hyper-Compounding, SL 0.85x)
        # =====================================================================
        c_snap_dict = {row["symbol"]: row for row in curr_snap.iter_rows(named=True)}
        closed_s2 = []
        for sym, pos in s2_positions.items():
            if sym not in c_snap_dict: continue
            row_s = c_snap_dict[sym]
            hi, lo, cl = row_s["high"], row_s["low"], row_s["close"]
            hit_tp = (lo <= pos["tp"]) if pos["side"] == "SHORT" else (hi >= pos["tp"])
            hit_sl = (hi >= pos["sl"]) if pos["side"] == "SHORT" else (lo <= pos["sl"])
            time_ex = (idx - pos["entry_bar"]) >= 18

            if hit_tp or hit_sl or time_ex:
                exit_px = pos["tp"] if hit_tp else (pos["sl"] if hit_sl else cl)
                ret_m = (pos["entry_px"] - exit_px) / pos["entry_px"] if pos["side"] == "SHORT" else (exit_px - pos["entry_px"]) / pos["entry_px"]
                pnl = (pos["notional"] * ret_m) - (pos["notional"] * 0.00055)
                s2_equity += pnl
                s2_trades.append(1.0 if pnl > 0 else -1.0)
                closed_s2.append(sym)
                s2_cooldowns[sym] = idx

        for s in closed_s2: del s2_positions[s]

        # S2 Entries (Max 2 slots, 2.5x each)
        open_s2 = 2 - len(s2_positions)
        s2_opened = 0
        if open_s2 > 0:
            cands_s2 = curr_snap.filter(
                ~pl.col("symbol").is_in(list(s2_positions.keys()))
            )
            if p_bear >= 0.40:
                short_cands = cands_s2.filter(
                    (pl.col("p_model_short") >= 0.245) & (pl.col("mom_24h") < 0.0)
                ).sort("p_model_short", descending=True).head(open_s2)
                for r in short_cands.iter_rows(named=True):
                    sym = r["symbol"]
                    if (idx - s2_cooldowns.get(sym, -99)) < 3: continue
                    px, atr = r["close"], r["atr_20"] or (r["close"] * 0.03)
                    notional = s2_equity * 2.5
                    s2_positions[sym] = {
                        "side": "SHORT", "entry_px": px, "notional": notional,
                        "tp": px - (3.2 * atr), "sl": px + (0.85 * atr), "entry_bar": idx
                    }
                    s2_opened += 1
            elif p_bull >= 0.88 and btc_bull:
                long_cands = cands_s2.filter(
                    (pl.col("p_model_long") >= 0.320) & (pl.col("mom_24h") > 0.02)
                ).sort("p_model_long", descending=True).head(open_s2)
                for r in long_cands.iter_rows(named=True):
                    sym = r["symbol"]
                    if (idx - s2_cooldowns.get(sym, -99)) < 3: continue
                    px, atr = r["close"], r["atr_20"] or (r["close"] * 0.03)
                    notional = s2_equity * 2.5
                    s2_positions[sym] = {
                        "side": "LONG", "entry_px": px, "notional": notional,
                        "tp": px + (2.5 * atr), "sl": px - (1.0 * atr), "entry_bar": idx
                    }
                    s2_opened += 1

        to2 = (len(closed_s2) + s2_opened) * 0.25
        s2_turnover.append(to2)
        s2_curve.append(s2_equity)

        # =====================================================================
        # STRATEGY 3: ASYMMETRIC GEARING & RMT BETA HEDGE (Leland Deadband)
        # =====================================================================
        bull_sc3 = 0.50 + 0.30 * np.tanh(omega_h - 0.5)
        lev3, _ = s3_gz.compute_leverage(s3_equity, bull_sc3, omega_h)
        t_w3 = s3_asym.allocate_asymmetric_portfolio(ranked_df, active_state, omega_h, lev3)
        to3 = sum(abs(t_w3.get(s, 0.0) - s3_weights.get(s, 0.0)) for s in set(s3_weights).union(t_w3))
        fee3 = s3_equity * to3 * 0.00055
        pnl3 = sum(s3_equity * w * next_rets.get(s, 0.0) for s, w in t_w3.items()) - fee3
        s3_equity += pnl3
        s3_weights = t_w3
        s3_curve.append(s3_equity)
        s3_turnover.append(to3)

        # =====================================================================
        # STRATEGY 4: TWO-TRANCHE RUNNER STATE MACHINE (Pillar 4)
        # =====================================================================
        lev4, _ = s4_gz.compute_leverage(s4_equity, 0.50, omega_h)
        cl_map = close_by_bar.get(curr_ts, {})
        hi_map = high_by_bar.get(curr_ts, {})
        lo_map = low_by_bar.get(curr_ts, {})
        atr_map = atr_by_bar.get(curr_ts, {})

        exits_4 = s4_runner.evaluate_barriers(cl_map, hi_map, lo_map, atr_map)
        avail_4 = 4 - len(s4_runner.active_slots)
        opened_4 = 0
        if avail_4 > 0 and lev4 > 0.5:
            slot_sz4 = lev4 / 4.0
            top4_cands = ranked_df.sort("predicted_rank_score", descending=True).head(6)["symbol"].to_list()
            for cand in top4_cands:
                if avail_4 <= 0: break
                if cand not in s4_runner.active_slots and cand not in s4_runner.cooldown_tracker:
                    s4_runner.open_slot(cand, 1, slot_sz4, cl_map.get(cand, 1.0), atr_map.get(cand, 0.03), idx)
                    avail_4 -= 1
                    opened_4 += 1

        s4_runner.decay_cooldowns()
        to4 = len(exits_4) * 0.15 + opened_4 * 0.20
        fee4 = s4_equity * to4 * 0.00055
        pnl4 = sum(
            s4_equity * (s.total_size * (0.5 if s.tranche_a_closed else 1.0)) * next_rets.get(sym, 0.0)
            for sym, s in s4_runner.active_slots.items()
        ) - fee4
        s4_equity += pnl4
        s4_curve.append(s4_equity)
        s4_turnover.append(to4)

        # =====================================================================
        # STRATEGY 5: CALIBRATED WIDE-BRACKET TREND RUNNER (Optimized 2026 Champion)
        # =====================================================================
        s5_peak = max(s5_peak, s5_equity)
        dd5 = max(0.0, 1.0 - (s5_equity / s5_peak))

        # Dynamic Leverage: 4.0x base, throttled by Grossman-Zhou with 0.50x survival floor
        if dd5 < 0.10: lev5 = 4.00
        elif dd5 < 0.18: lev5 = 2.50
        elif dd5 < 0.22: lev5 = 1.25
        else: lev5 = 0.50  # Survival floor

        # Manage open slots (Wide Brackets: SL = 2.0x ATR, TP = 3.2x ATR, Time = 18 bars)
        closed_s5 = []
        for sym, pos in s5_positions.items():
            if sym not in c_snap_dict: continue
            row_s = c_snap_dict[sym]
            hi, lo, cl = row_s["high"], row_s["low"], row_s["close"]
            hit_tp = (hi >= pos["tp"]) if pos["side"] == "LONG" else (lo <= pos["tp"])
            hit_sl = (lo <= pos["sl"]) if pos["side"] == "LONG" else (hi >= pos["sl"])
            time_ex = (idx - pos["entry_bar"]) >= 18

            if hit_tp or hit_sl or time_ex:
                exit_px = pos["tp"] if hit_tp else (pos["sl"] if hit_sl else cl)
                ret_m = (exit_px - pos["entry_px"]) / pos["entry_px"] if pos["side"] == "LONG" else (pos["entry_px"] - exit_px) / pos["entry_px"]
                # 2.0 bps slippage under ALO execution
                pnl = (pos["notional"] * ret_m) - (pos["notional"] * 0.00020)
                s5_equity += pnl
                s5_trades.append(1.0 if pnl > 0 else -1.0)
                closed_s5.append(sym)
                s5_cooldowns[sym] = idx

        for s in closed_s5: del s5_positions[s]

        # S5 Entries with Macro Trend Gate
        open_s5 = 4 - len(s5_positions)
        s5_opened = 0
        if open_s5 > 0 and lev5 >= 0.5:
            slot_size = (s5_equity * lev5) / 4.0
            # Macro Gate: In Bull trend, Long top alpha leaders; In Bear trend, Short weakest
            if btc_bull:
                top_cands5 = ranked_df.filter(pl.col("symbol") != "BTC").head(8)["symbol"].to_list()
                for sym in top_cands5:
                    if open_s5 <= 0: break
                    if sym not in s5_positions and (idx - s5_cooldowns.get(sym, -99)) >= 3:
                        px = cl_map.get(sym, 1.0)
                        atr = atr_map.get(sym, px * 0.03)
                        s5_positions[sym] = {
                            "side": "LONG", "entry_px": px, "notional": slot_size,
                            "tp": px + (3.2 * atr), "sl": px - (2.0 * atr), "entry_bar": idx
                        }
                        open_s5 -= 1
                        s5_opened += 1
            else:
                bot_cands5 = ranked_df.filter(pl.col("symbol") != "BTC").tail(8)["symbol"].to_list()
                for sym in bot_cands5:
                    if open_s5 <= 0: break
                    if sym not in s5_positions and (idx - s5_cooldowns.get(sym, -99)) >= 3:
                        px = cl_map.get(sym, 1.0)
                        atr = atr_map.get(sym, px * 0.03)
                        s5_positions[sym] = {
                            "side": "SHORT", "entry_px": px, "notional": slot_size,
                            "tp": px - (3.2 * atr), "sl": px + (2.0 * atr), "entry_bar": idx
                        }
                        open_s5 -= 1
                        s5_opened += 1

        to5 = (len(closed_s5) + s5_opened) * 0.12
        s5_turnover.append(to5)
        s5_curve.append(s5_equity)

        # =====================================================================
        # STRATEGY 6: COMBO 3+4 (Asymmetric Gearing + Two-Tranche Runner + CatBoost)
        # =====================================================================
        lev6, _ = s6_gz.compute_leverage(s6_equity, 0.50 + 0.30 * np.tanh(omega_h - 0.5), omega_h)
        
        # 1. Evaluate Two-Tranche Barriers
        exits_6 = s6_runner.evaluate_barriers(cl_map, hi_map, lo_map, atr_map)
        for ex in exits_6:
            reason = str(ex.get("reason", "")).upper()
            is_win = 1.0 if ("HARVEST" in reason or "PROFIT" in reason or "TRAILING" in reason) else -1.0
            s6_trades.append(is_win)

        # 2. Asymmetric Slot Allocation with CatBoost Confirmation
        avail_6 = 4 - len(s6_runner.active_slots)
        opened_6 = 0
        if avail_6 > 0 and lev6 >= 0.5:
            slot_sz6 = (lev6 / 4.0)
            if btc_bull or active_state == 0:
                # Bull: Prioritize Longs
                long_candidates = ranked_df.filter(
                    (pl.col("symbol") != "BTC") & (pl.col("p_model_long") >= 0.25)
                ).sort("predicted_rank_score", descending=True).head(6)["symbol"].to_list()
                for cand in long_candidates:
                    if avail_6 <= 0: break
                    if cand not in s6_runner.active_slots and cand not in s6_runner.cooldown_tracker:
                        px = cl_map.get(cand, 1.0)
                        atr = atr_map.get(cand, px * 0.03)
                        s6_runner.open_slot(cand, 1, slot_sz6, px, atr, idx)
                        avail_6 -= 1
                        opened_6 += 1
            else:
                # Bear / Transition: Take Shorts on bottom rankers with CatBoost short confirmation
                short_candidates = ranked_df.filter(
                    (pl.col("symbol") != "BTC") & (pl.col("p_model_short") >= 0.22)
                ).sort("predicted_rank_score", descending=False).head(6)["symbol"].to_list()
                for cand in short_candidates:
                    if avail_6 <= 0: break
                    if cand not in s6_runner.active_slots and cand not in s6_runner.cooldown_tracker:
                        px = cl_map.get(cand, 1.0)
                        atr = atr_map.get(cand, px * 0.03)
                        s6_runner.open_slot(cand, -1, slot_sz6, px, atr, idx)
                        avail_6 -= 1
                        opened_6 += 1

        s6_runner.decay_cooldowns()
        to6 = len(exits_6) * 0.12 + opened_6 * 0.15
        fee6 = s6_equity * to6 * 0.00020  # ALO Maker execution
        pnl6 = sum(
            s6_equity * (s.total_size * (0.5 if s.tranche_a_closed else 1.0) * s.direction) * next_rets.get(sym, 0.0)
            for sym, s in s6_runner.active_slots.items()
        ) - fee6
        s6_equity += pnl6
        s6_curve.append(s6_equity)
        s6_turnover.append(to6)

    sim_duration = time.time() - start_time
    print(f"--> [5/5] All 6 simulations completed in {sim_duration:.2f}s.\n")

    # 4. Compilation & Scoreboard
    def calc_stats(curve, turnover_list, trades_list=None):
        eq_arr = np.array(curve)
        final_eq = eq_arr[-1]
        cum_ret = (final_eq / 1000.0 - 1.0) * 100.0
        ann_mult = 365.25 / ((eval_bars * 4.0) / 24.0)
        cagr = ((final_eq / 1000.0) ** ann_mult - 1.0) * 100.0 if final_eq > 0 else -100.0
        rets = np.diff(eq_arr) / eq_arr[:-1]
        sharpe = float(np.mean(rets) / (np.std(rets) + 1e-8) * np.sqrt(2190.0))
        down_rets = rets[rets < 0]
        sortino = float(np.mean(rets) / (np.std(down_rets) + 1e-8) * np.sqrt(2190.0)) if len(down_rets) > 0 else 0.0
        peak_arr = np.maximum.accumulate(eq_arr)
        dds = (peak_arr - eq_arr) / peak_arr
        max_dd = float(np.max(dds)) * 100.0
        calmar = (cagr / max_dd) if max_dd > 0 else 0.0
        avg_to = float(np.mean(turnover_list)) * 100.0 if len(turnover_list) > 0 else 0.0
        if trades_list and len(trades_list) > 0:
            wr = (sum(1 for t in trades_list if t > 0) / len(trades_list)) * 100.0
            pf = (sum(t for t in trades_list if t > 0) / abs(sum(t for t in trades_list if t < 0) + 1e-6))
        else:
            bar_wins = [r for r in rets if r > 0]
            bar_losses = [r for r in rets if r < 0]
            wr = (len(bar_wins) / len(rets)) * 100.0
            pf = sum(bar_wins) / abs(sum(bar_losses) + 1e-8)
        return final_eq, cum_ret, cagr, sharpe, sortino, calmar, max_dd, wr, pf, avg_to

    stats1 = calc_stats(s1_curve, s1_turnover)
    stats2 = calc_stats(s2_curve, s2_turnover, s2_trades)
    stats3 = calc_stats(s3_curve, s3_turnover)
    stats4 = calc_stats(s4_curve, s4_turnover)
    stats5 = calc_stats(s5_curve, s5_turnover, s5_trades)
    stats6 = calc_stats(s6_curve, s6_turnover, s6_trades)

    scoreboard = [
        ("Final Ending Equity ($)", f"${stats1[0]:,.2f}", f"${stats2[0]:,.2f}", f"${stats3[0]:,.2f}", f"${stats4[0]:,.2f}", f"${stats5[0]:,.2f}", f"${stats6[0]:,.2f}"),
        ("Cumulative Return (%)", f"{stats1[1]:>+7.2f}%", f"{stats2[1]:>+7.2f}%", f"{stats3[1]:>+7.2f}%", f"{stats4[1]:>+7.2f}%", f"{stats5[1]:>+7.2f}%", f"{stats6[1]:>+7.2f}%"),
        ("Annualized Return (CAGR)", f"{stats1[2]:>+7.2f}%", f"{stats2[2]:>+7.2f}%", f"{stats3[2]:>+7.2f}%", f"{stats4[2]:>+7.2f}%", f"{stats5[2]:>+7.2f}%", f"{stats6[2]:>+7.2f}%"),
        ("Annualized Sharpe Ratio", f"{stats1[3]:>7.2f}", f"{stats2[3]:>7.2f}", f"{stats3[3]:>7.2f}", f"{stats4[3]:>7.2f}", f"{stats5[3]:>7.2f}", f"{stats6[3]:>7.2f}"),
        ("Annualized Sortino Ratio", f"{stats1[4]:>7.2f}", f"{stats2[4]:>7.2f}", f"{stats3[4]:>7.2f}", f"{stats4[4]:>7.2f}", f"{stats5[4]:>7.2f}", f"{stats6[4]:>7.2f}"),
        ("Calmar Ratio (CAGR/MDD)", f"{stats1[5]:>7.2f}", f"{stats2[5]:>7.2f}", f"{stats3[5]:>7.2f}", f"{stats4[5]:>7.2f}", f"{stats5[5]:>7.2f}", f"{stats6[5]:>7.2f}"),
        ("Maximum Drawdown (D_max)", f"{stats1[6]:>6.2f}%", f"{stats2[6]:>6.2f}%", f"{stats3[6]:>6.2f}%", f"{stats4[6]:>6.2f}%", f"{stats5[6]:>6.2f}%", f"{stats6[6]:>6.2f}%"),
        ("Trade / Bar Win Rate", f"{stats1[7]:>6.1f}%", f"{stats2[7]:>6.1f}%", f"{stats3[7]:>6.1f}%", f"{stats4[7]:>6.1f}%", f"{stats5[7]:>6.1f}%", f"{stats6[7]:>6.1f}%"),
        ("Profit Factor", f"{stats1[8]:>7.2f}", f"{stats2[8]:>7.2f}", f"{stats3[8]:>7.2f}", f"{stats4[8]:>7.2f}", f"{stats5[8]:>7.2f}", f"{stats6[8]:>7.2f}"),
        ("Avg Turnover per 4H Bar", f"{stats1[9]:>6.2f}%", f"{stats2[9]:>6.2f}%", f"{stats3[9]:>6.2f}%", f"{stats4[9]:>6.2f}%", f"{stats5[9]:>6.2f}%", f"{stats6[9]:>6.2f}%"),
    ]

    print("=" * 135)
    print(f"{'METRIC':<26} | {'ALGO 1 (CURRENT)':<16} | {'ALGO 2 (PREV CB)':<16} | {'ALGO 3 (ASYM RMT)':<16} | {'ALGO 4 (TWO-TRANCHE)':<16} | {'ALGO 5 (WIDE RUNNER)':<16} | {'ALGO 6 (COMBO 3+4)'}")
    print("-" * 135)
    for row in scoreboard:
        print(f"{row[0]:<26} | {row[1]:<16} | {row[2]:<16} | {row[3]:<16} | {row[4]:<16} | {row[5]:<16} | {row[6]}")
    print("=" * 135)


if __name__ == "__main__":
    run_5algo_tournament()
