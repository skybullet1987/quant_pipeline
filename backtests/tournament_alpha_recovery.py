"""
CONTROLLED ALPHA RECOVERY TOURNAMENT & INSTITUTIONAL BENCHMARK
================================================================================
Evaluates competing alpha models on a FROZEN, LOW-TURNOVER EXECUTION BASELINE:
- 4 discrete slots (25% NAV each, 1.0x gross leverage, zero compounding)
- Barrier geometry: SL = 1.8x ATR, TP = 2.5x ATR, Max holding = 18 bars (72H)
- Fee friction: 5.5 bps explicit taker rebalancing; 2.0 bps for ALO maker execution

Contestants:
  A0: Static Production LightGBM Ranker
  A1: Walk-Forward LightGBM (60D rolling, retrained every 18 bars / 3 days)
  A2: Walk-Forward CatBoost (60D rolling, retrained every 18 bars / 3 days)
  A3: Ensemble Model (0.50 * A1 + 0.50 * A2)
  A4: Pure Beta-Stripped Residual Momentum (ResMom = Mom_i - beta_i * Mom_BTC)
  A5: Composite Residual Alpha (Residual Momentum + Low-Vol Tilt + Coiling Status)

Dual Attribution:
  - Absolute Metrics: Final Equity, CAGR, Sharpe, Sortino, MaxDD, PF, Win Rate, Turnover, Exact Fee Drag ($)
  - Relative Benchmarks: BTC, ETH, Equal-Weight Alt Index, Top-Decile Long, Bottom-Decile Short, Dollar-Neutral Spread
  - Adverse Selection Diagnostic: Post-fill returns at 1 bar, 2 bars, 4 bars
"""

import sys
import time
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

warnings.filterwarnings("ignore")

import numpy as np
import polars as pl
import pandas as pd
import lightgbm as lgb
from catboost import CatBoostClassifier, Pool

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.execution.papertrade_daemon import FEAT_COLS, CrossSectionalAlphaRanker
from src.signals.residual_alpha_engine import ResidualAlphaEngine

LAKE_CACHE = PIPELINE_ROOT / "data" / "lake" / "fct_4h_production_cache.parquet"
MODELS_DIR = PIPELINE_ROOT / "models" / "prod"


@dataclass
class SlotState:
    symbol: str
    direction: int  # +1 Long, -1 Short
    entry_price: float
    atr: float
    entry_bar: int
    sl_price: float
    tp_price: float
    notional: float


class FixedDiscreteSlotEngine:
    """Frozen 4-slot execution engine with explicit fee accounting."""
    def __init__(self, n_slots: int = 4, sl_mult: float = 1.8, tp_mult: float = 2.5, max_bars: int = 18, fee_rate: float = 0.00055):
        self.n_slots = n_slots
        self.sl_mult = sl_mult
        self.tp_mult = tp_mult
        self.max_bars = max_bars
        self.fee_rate = fee_rate
        self.active_slots: Dict[str, SlotState] = {}
        self.cooldown: Dict[str, int] = {}
        self.trades: List[Dict] = []
        self.cum_fee_usd = 0.0
        self.post_fill_tracking: List[Dict] = []

    def evaluate_exits(self, current_bar: int, bar_data: Dict[str, Dict[str, float]], nav: float) -> Tuple[float, float]:
        """Evaluates barrier exits (TP, SL, Time). Returns (pnl_usd, turnover_usd)."""
        closed_syms = []
        bar_pnl = 0.0
        turnover = 0.0

        for sym, slot in list(self.active_slots.items()):
            if sym not in bar_data:
                continue
            hi = bar_data[sym]["high"]
            lo = bar_data[sym]["low"]
            cl = bar_data[sym]["close"]

            hit_tp = (hi >= slot.tp_price) if slot.direction == 1 else (lo <= slot.tp_price)
            hit_sl = (lo <= slot.sl_price) if slot.direction == 1 else (hi >= slot.sl_price)
            time_ex = (current_bar - slot.entry_bar) >= self.max_bars

            if hit_tp or hit_sl or time_ex:
                exit_px = slot.tp_price if hit_tp else (slot.sl_price if hit_sl else cl)
                ret_m = ((exit_px - slot.entry_price) / slot.entry_price) * slot.direction
                gross_pnl = slot.notional * ret_m
                exit_fee = slot.notional * self.fee_rate
                net_pnl = gross_pnl - exit_fee

                bar_pnl += net_pnl
                self.cum_fee_usd += exit_fee
                turnover += slot.notional

                reason = "TP" if hit_tp else ("SL" if hit_sl else "TIME")
                self.trades.append({
                    "symbol": sym, "direction": slot.direction, "entry_bar": slot.entry_bar,
                    "exit_bar": current_bar, "return": ret_m, "pnl": net_pnl, "reason": reason
                })
                closed_syms.append(sym)
                self.cooldown[sym] = current_bar

        for s in closed_syms:
            del self.active_slots[s]

        return bar_pnl, turnover

    def open_positions(
        self,
        target_candidates: List[Tuple[str, int]],  # (symbol, direction)
        current_bar: int,
        bar_data: Dict[str, Dict[str, float]],
        nav: float
    ) -> float:
        """Opens new discrete slots up to n_slots. Returns turnover_usd."""
        avail_slots = self.n_slots - len(self.active_slots)
        if avail_slots <= 0:
            return 0.0

        slot_notional = nav / float(self.n_slots)
        turnover = 0.0

        for sym, direction in target_candidates:
            if avail_slots <= 0:
                break
            if sym in self.active_slots or (current_bar - self.cooldown.get(sym, -999)) < 3:
                continue
            if sym not in bar_data:
                continue

            px = bar_data[sym]["close"]
            atr = bar_data[sym]["atr"]
            entry_fee = slot_notional * self.fee_rate
            self.cum_fee_usd += entry_fee
            turnover += slot_notional

            sl_px = px - (self.sl_mult * atr) if direction == 1 else px + (self.sl_mult * atr)
            tp_px = px + (self.tp_mult * atr) if direction == 1 else px - (self.tp_mult * atr)

            self.active_slots[sym] = SlotState(
                symbol=sym, direction=direction, entry_price=px, atr=atr,
                entry_bar=current_bar, sl_price=sl_px, tp_price=tp_px, notional=slot_notional
            )

            self.post_fill_tracking.append({
                "symbol": sym, "direction": direction, "entry_bar": current_bar, "entry_px": px
            })
            avail_slots -= 1

        return turnover


def run_alpha_recovery_tournament():
    print("=" * 115)
    print("        CONTROLLED ALPHA RECOVERY TOURNAMENT ON FROZEN LOW-TURNOVER BASELINE        ")
    print("=" * 115)

    if not LAKE_CACHE.exists():
        raise FileNotFoundError(f"Cache {LAKE_CACHE} does not exist.")

    print("--> [1/6] Loading 4H Production Lake Cache & Structuring Memory Maps...")
    df = pl.read_parquet(LAKE_CACHE)
    if "ticker" in df.columns and "symbol" not in df.columns:
        df = df.rename({"ticker": "symbol"})
    if "timestamp" in df.columns and "timestamp_ms" not in df.columns:
        df = df.with_columns(pl.col("timestamp").dt.epoch("ms").alias("timestamp_ms"))

    ts_col = "timestamp_ms"
    df = df.sort(["symbol", ts_col])

    # 1-bar returns
    df = df.with_columns([
        (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).fill_null(0.0).alias("ret_4h"),
        (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("fwd_ret_4h")
    ])

    all_timestamps = sorted(df[ts_col].unique().to_list())
    total_bars = len(all_timestamps)
    print(f"    Loaded {df.height:,} rows across {total_bars} bars and {df['symbol'].n_unique()} symbols.")

    # Memory maps for fast bar-by-bar simulation
    bar_market_data = {}
    fwd_rets_by_bar = {}
    for row in df.select([ts_col, "symbol", "open", "high", "low", "close", "atr_20", "fwd_ret_4h"]).iter_rows(named=True):
        t = row[ts_col]
        s = row["symbol"]
        if t not in bar_market_data:
            bar_market_data[t] = {}
            fwd_rets_by_bar[t] = {}
        c = row["close"] or 1.0
        bar_market_data[t][s] = {
            "open": row["open"] or c,
            "high": row["high"] or (c * 1.01),
            "low": row["low"] or (c * 0.99),
            "close": c,
            "atr": row["atr_20"] or (c * 0.03),
        }
        fwd_rets_by_bar[t][s] = row["fwd_ret_4h"] or 0.0

    # Macro trend map (BTC close > EMA20)
    btc_df = df.filter(pl.col("symbol") == "BTC").sort(ts_col)
    btc_ema20 = btc_df.select([
        ts_col,
        (pl.col("close") > pl.col("close").ewm_mean(span=20)).alias("btc_bull"),
        pl.col("close").alias("btc_close"),
        pl.col("ret_4h").alias("btc_ret")
    ])
    btc_bull_map = dict(zip(btc_ema20[ts_col].to_list(), btc_ema20["btc_bull"].to_list()))
    btc_close_map = dict(zip(btc_ema20[ts_col].to_list(), btc_ema20["btc_close"].to_list()))
    btc_ret_map = dict(zip(btc_ema20[ts_col].to_list(), btc_ema20["btc_ret"].to_list()))

    # ETH close map for relative benchmarking
    eth_df = df.filter(pl.col("symbol") == "ETH").sort(ts_col)
    eth_close_map = dict(zip(eth_df[ts_col].to_list(), eth_df["close"].to_list()))

    # Equal-Weight Alt Index returns per bar
    alt_df = df.filter(pl.col("symbol") != "BTC").group_by(ts_col).agg(pl.col("fwd_ret_4h").mean().alias("alt_index_ret"))
    alt_index_map = dict(zip(alt_df[ts_col].to_list(), alt_df["alt_index_ret"].to_list()))

    print("--> [2/6] Initializing Residual Alpha Engine & Beta Estimation...")
    residual_engine = ResidualAlphaEngine()
    beta_df = residual_engine.estimate_betas(df, ts_col="timestamp_ms", symbol_col="symbol", ret_col="ret_4h")
    df = df.join(beta_df, on=[ts_col, "symbol"], how="left")

    # Load CatBoost production models
    print("--> [3/6] Scoring Production CatBoost Models...")
    cb_feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]
    pdf = df.to_pandas()
    for c in cb_feature_cols:
        if c not in pdf.columns:
            pdf[c] = 0.0
    cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
    cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")
    pdf["catboost_long_score"] = cb_long.predict_proba(pdf[cb_feature_cols])[:, 1]
    pdf["catboost_short_score"] = cb_short.predict_proba(pdf[cb_feature_cols])[:, 1]
    pdf["catboost_net_score"] = pdf["catboost_long_score"] - pdf["catboost_short_score"]
    df = pl.from_pandas(pdf)

    # 4. Initialize 6 Controlled Engines
    print("--> [4/6] Initializing 6 Alpha Models on Frozen Execution Base...")
    WARMUP_BARS = 60
    eval_bars = total_bars - WARMUP_BARS - 1

    engines = {
        "A0_LGBM_STATIC": FixedDiscreteSlotEngine(),
        "A1_LGBM_ROLLING": FixedDiscreteSlotEngine(),
        "A2_CATBOOST_ROLLING": FixedDiscreteSlotEngine(),
        "A3_ENSEMBLE": FixedDiscreteSlotEngine(),
        "A4_RESIDUAL_MOM": FixedDiscreteSlotEngine(),
        "A5_COMPOSITE_ALPHA": FixedDiscreteSlotEngine(),
    }

    equities = {k: 1000.0 for k in engines}
    curves = {k: [1000.0] for k in engines}
    turnovers = {k: [] for k in engines}

    # Relative Benchmark Curves
    btc_start = btc_close_map.get(all_timestamps[WARMUP_BARS], 1.0)
    eth_start = eth_close_map.get(all_timestamps[WARMUP_BARS], 1.0)
    btc_curve = [1000.0]
    eth_curve = [1000.0]
    alt_curve = [1000.0]
    top_decile_curve = [1000.0]
    bot_decile_curve = [1000.0]
    spread_curve = [1000.0]

    top_dec_eq = 1000.0
    bot_dec_eq = 1000.0
    spread_eq = 1000.0
    alt_eq = 1000.0

    # Model training states
    ranker_static = CrossSectionalAlphaRanker()
    ranker_rolling = CrossSectionalAlphaRanker()
    cb_retrained_model = None

    last_retrain_bar = -999

    print(f"--> [5/6] Executing Head-to-Head Tournament across {eval_bars} 4H bars...")
    start_sim = time.time()

    avail_feats = [c for c in FEAT_COLS if c in df.columns]

    for idx in range(WARMUP_BARS, total_bars - 1):
        curr_ts = all_timestamps[idx]
        curr_snap = df.filter(pl.col(ts_col) == curr_ts)
        curr_bar_data = bar_market_data.get(curr_ts, {})
        btc_bull = btc_bull_map.get(curr_ts, True)
        btc_ret = btc_ret_map.get(curr_ts, 0.0)

        # 1. Update Relative Benchmarks
        btc_cur = btc_close_map.get(curr_ts, btc_start)
        eth_cur = eth_close_map.get(curr_ts, eth_start)
        btc_curve.append(1000.0 * (btc_cur / btc_start))
        eth_curve.append(1000.0 * (eth_cur / eth_start))

        alt_r = alt_index_map.get(curr_ts, 0.0)
        alt_eq *= (1.0 + alt_r)
        alt_curve.append(alt_eq)

        # Decile portfolios (Top 10% Long, Bottom 10% Short)
        if curr_snap.height >= 10:
            n_dec = max(1, int(curr_snap.height * 0.10))
            sorted_mom = curr_snap.sort("mom_24h", descending=True)
            top_syms = sorted_mom.head(n_dec)["symbol"].to_list()
            bot_syms = sorted_mom.tail(n_dec)["symbol"].to_list()

            top_r = np.mean([fwd_rets_by_bar.get(curr_ts, {}).get(s, 0.0) for s in top_syms])
            bot_r = np.mean([fwd_rets_by_bar.get(curr_ts, {}).get(s, 0.0) for s in bot_syms])

            top_dec_eq *= (1.0 + top_r - 0.00055 * 0.10)
            bot_dec_eq *= (1.0 - bot_r - 0.00055 * 0.10)
            spread_eq *= (1.0 + (top_r - bot_r) - 0.00055 * 0.20)

        top_decile_curve.append(top_dec_eq)
        bot_decile_curve.append(bot_dec_eq)
        spread_curve.append(spread_eq)

        # 2. Retraining Cadence: Walk-Forward every 18 bars (3 days) on rolling 60D window
        if (idx - last_retrain_bar) >= 18 or last_retrain_bar < 0:
            train_snap = df.filter((pl.col(ts_col) < curr_ts) & (pl.col(ts_col) >= all_timestamps[max(0, idx - 360)]))
            if train_snap.height > 200:
                train_snap = train_snap.with_columns(
                    (pl.col("fwd_ret_4h") > 0).cast(pl.Int32).alias("forward_res_decile")
                )
                # Retrain Rolling LightGBM
                ranker_rolling.train_lambdarank(train_snap, avail_feats)

                # Retrain Rolling CatBoost (on net target)
                cb_pdf = train_snap.select(cb_feature_cols + ["fwd_ret_4h"]).to_pandas().dropna()
                cb_pdf["target"] = (cb_pdf["fwd_ret_4h"] > 0).astype(int)
                cb_retrained_model = CatBoostClassifier(iterations=60, depth=4, learning_rate=0.08, verbose=0)
                cb_retrained_model.fit(cb_pdf[cb_feature_cols], cb_pdf["target"])

                last_retrain_bar = idx

        # Initial Static LightGBM train once at warmup
        if idx == WARMUP_BARS:
            init_train = df.filter(pl.col(ts_col) < curr_ts).with_columns(
                (pl.col("fwd_ret_4h") > 0).cast(pl.Int32).alias("forward_res_decile")
            )
            ranker_static.train_lambdarank(init_train, avail_feats)

        # 3. Generate Model Rankings for this Bar
        # A0: Static LGBM
        ranked_a0 = ranker_static.rank_universe(curr_snap, avail_feats)
        a0_candidates = [
            (s, 1 if btc_bull else -1) for s in ranked_a0.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()
        ]

        # A1: Rolling LGBM
        ranked_a1 = ranker_rolling.rank_universe(curr_snap, avail_feats)
        a1_candidates = [
            (s, 1 if btc_bull else -1) for s in ranked_a1.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()
        ]

        # A2: Rolling CatBoost
        snap_pdf = curr_snap.to_pandas()
        for c in cb_feature_cols:
            if c not in snap_pdf.columns:
                snap_pdf[c] = 0.0
        if cb_retrained_model:
            snap_pdf["cb_rolling_prob"] = cb_retrained_model.predict_proba(snap_pdf[cb_feature_cols])[:, 1]
        else:
            snap_pdf["cb_rolling_prob"] = snap_pdf["catboost_net_score"]
        ranked_a2 = pl.from_pandas(snap_pdf).sort("cb_rolling_prob", descending=True)
        a2_candidates = [
            (s, 1 if btc_bull else -1) for s in ranked_a2.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()
        ]

        # A3: Ensemble (A1 Rank + A2 Prob)
        pdf_ens = ranked_a1.select(["symbol", "predicted_rank_score"]).join(
            ranked_a2.select(["symbol", "cb_rolling_prob"]), on="symbol", how="inner"
        ).to_pandas()
        pdf_ens["ens_score"] = (
            (pdf_ens["predicted_rank_score"] - pdf_ens["predicted_rank_score"].mean()) / (pdf_ens["predicted_rank_score"].std() + 1e-6) +
            (pdf_ens["cb_rolling_prob"] - pdf_ens["cb_rolling_prob"].mean()) / (pdf_ens["cb_rolling_prob"].std() + 1e-6)
        )
        ranked_a3 = pl.from_pandas(pdf_ens).sort("ens_score", descending=True)
        a3_candidates = [
            (s, 1 if btc_bull else -1) for s in ranked_a3.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()
        ]

        # A4: Pure Residual Momentum (beta-stripped momentum)
        snap_res = curr_snap.with_columns(
            (pl.col("mom_24h") - pl.col("beta_btc") * (btc_ret * 6.0)).alias("pure_res_mom")
        ).sort("pure_res_mom", descending=True)
        a4_candidates = [
            (s, 1 if btc_bull else -1) for s in snap_res.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()
        ]

        # A5: Composite Residual Alpha (Residual Mom + Low-Vol Tilt + Coiling)
        ranked_a5 = residual_engine.compute_residual_alpha(curr_snap, btc_ret_snapshot=btc_ret)
        a5_candidates = [
            (s, 1 if btc_bull else -1) for s in ranked_a5.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()
        ]

        model_candidates = {
            "A0_LGBM_STATIC": a0_candidates,
            "A1_LGBM_ROLLING": a1_candidates,
            "A2_CATBOOST_ROLLING": a2_candidates,
            "A3_ENSEMBLE": a3_candidates,
            "A4_RESIDUAL_MOM": a4_candidates,
            "A5_COMPOSITE_ALPHA": a5_candidates,
        }

        # 4. Step All 6 Engines
        for k, eng in engines.items():
            cur_eq = equities[k]
            # 4A. Evaluate Barrier Exits
            pnl_ex, to_ex = eng.evaluate_exits(idx, curr_bar_data, cur_eq)
            cur_eq += pnl_ex

            # 4B. Open Slots
            to_open = eng.open_positions(model_candidates[k], idx, curr_bar_data, cur_eq)

            # 4C. Unleveraged Holding PnL for remaining active slots
            fwd_dict = fwd_rets_by_bar.get(curr_ts, {})
            holding_pnl = sum(
                s.notional * s.direction * fwd_dict.get(sym, 0.0)
                for sym, s in eng.active_slots.items()
            )
            cur_eq += holding_pnl

            equities[k] = cur_eq
            curves[k].append(cur_eq)
            turnovers[k].append((to_ex + to_open) / cur_eq if cur_eq > 0 else 0.0)

    sim_time = time.time() - start_sim
    print(f"--> [6/6] Simulation finished in {sim_time:.2f}s.\n")

    # 5. Institutional Performance Metrics Calculation
    def get_metrics(curve, to_list, fee_usd, trades):
        eq_arr = np.array(curve)
        final_eq = eq_arr[-1]
        cum_ret = (final_eq / 1000.0 - 1.0) * 100.0
        ann_mult = 365.25 / ((eval_bars * 4.0) / 24.0)
        cagr = ((final_eq / 1000.0) ** ann_mult - 1.0) * 100.0 if final_eq > 0 else -100.0
        rets = np.diff(eq_arr) / eq_arr[:-1]
        sharpe = float(np.mean(rets) / (np.std(rets) + 1e-8) * np.sqrt(2190.0))
        down_rets = rets[rets < 0]
        sortino = float(np.mean(rets) / (np.std(down_rets) + 1e-8) * np.sqrt(2190.0)) if len(down_rets) > 0 else 0.0
        peak = np.maximum.accumulate(eq_arr)
        max_dd = float(np.max((peak - eq_arr) / peak)) * 100.0
        avg_to = float(np.mean(to_list)) * 100.0 if to_list else 0.0
        exact_fee_drag = (fee_usd / 1000.0) * 100.0

        n_trades = len(trades)
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]
        wr = (len(wins) / n_trades * 100.0) if n_trades > 0 else 0.0
        gross_win = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        pf = (gross_win / (gross_loss + 1e-8)) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)

        return {
            "final_eq": final_eq, "cum_ret": cum_ret, "cagr": cagr, "sharpe": sharpe,
            "sortino": sortino, "max_dd": max_dd, "avg_to": avg_to, "fee_drag": exact_fee_drag,
            "n_trades": n_trades, "wr": wr, "pf": pf
        }

    # Model Stats
    stats_models = {k: get_metrics(curves[k], turnovers[k], engines[k].cum_fee_usd, engines[k].trades) for k in engines}

    # Benchmark Stats
    def get_bench_stats(curve):
        eq_arr = np.array(curve)
        final_eq = eq_arr[-1]
        cum_ret = (final_eq / 1000.0 - 1.0) * 100.0
        ann_mult = 365.25 / ((eval_bars * 4.0) / 24.0)
        cagr = ((final_eq / 1000.0) ** ann_mult - 1.0) * 100.0 if final_eq > 0 else -100.0
        rets = np.diff(eq_arr) / eq_arr[:-1]
        sharpe = float(np.mean(rets) / (np.std(rets) + 1e-8) * np.sqrt(2190.0))
        peak = np.maximum.accumulate(eq_arr)
        max_dd = float(np.max((peak - eq_arr) / peak)) * 100.0
        return {"final_eq": final_eq, "cum_ret": cum_ret, "cagr": cagr, "sharpe": sharpe, "max_dd": max_dd}

    bench_stats = {
        "BTC Buy & Hold": get_bench_stats(btc_curve),
        "ETH Buy & Hold": get_bench_stats(eth_curve),
        "Equal-Weight Alt Index": get_bench_stats(alt_curve),
        "Long Top-Decile (24H rebal)": get_bench_stats(top_decile_curve),
        "Short Bottom-Decile (24H rebal)": get_bench_stats(bot_decile_curve),
        "Dollar-Neutral Spread (Top-Bot)": get_bench_stats(spread_curve),
    }

    # Print Table 1: Competing Alpha Models
    print("=" * 135)
    print("                     TABLE 1: CONTROLLED ALPHA CONTESTANTS (FROZEN 4-SLOT EXECUTION BASELINE)                     ")
    print("=" * 135)
    header = f"{'METRIC':<28} | {'A0 (LGBM STATIC)':<16} | {'A1 (LGBM ROLL)':<16} | {'A2 (CB ROLL)':<16} | {'A3 (ENSEMBLE)':<16} | {'A4 (RES MOM)':<16} | {'A5 (COMPOSITE)'}"
    print(header)
    print("-" * 135)

    rows = [
        ("Final Ending Equity ($)", lambda m: f"${m['final_eq']:,.2f}"),
        ("Cumulative Return (%)", lambda m: f"{m['cum_ret']:>+7.2f}%"),
        ("Annualized Return (CAGR)", lambda m: f"{m['cagr']:>+7.2f}%"),
        ("Annualized Sharpe Ratio", lambda m: f"{m['sharpe']:>7.2f}"),
        ("Annualized Sortino Ratio", lambda m: f"{m['sortino']:>7.2f}"),
        ("Maximum Drawdown (D_max)", lambda m: f"{m['max_dd']:>6.2f}%"),
        ("Trade Win Rate (%)", lambda m: f"{m['wr']:>6.1f}%"),
        ("Profit Factor", lambda m: f"{m['pf']:>7.2f}"),
        ("Total Trades Executed", lambda m: f"{m['n_trades']:>7d}"),
        ("Avg Turnover / 4H Bar (%)", lambda m: f"{m['avg_to']:>6.2f}%"),
        ("Exact Total Fee Drag (%)", lambda m: f"{m['fee_drag']:>6.2f}%"),
    ]

    for label, fn in rows:
        row_str = f"{label:<28} | " + " | ".join(f"{fn(stats_models[k]):<16}" for k in engines)
        print(row_str)
    print("=" * 135)

    # Print Table 2: Relative Benchmarks
    print("\n" + "=" * 105)
    print("                           TABLE 2: INSTITUTIONAL RELATIVE BENCHMARKS                           ")
    print("=" * 105)
    print(f"{'BENCHMARK':<34} | {'ENDING EQUITY':<15} | {'CUMULATIVE RET':<16} | {'CAGR (%)':<12} | {'SHARPE':<8} | {'MAX DD'}")
    print("-" * 105)
    for b_name, b_data in bench_stats.items():
        print(f"{b_name:<34} | ${b_data['final_eq']:<14,.2f} | {b_data['cum_ret']:>+13.2f}% | {b_data['cagr']:>+9.2f}% | {b_data['sharpe']:>6.2f} | {b_data['max_dd']:>5.2f}%")
    print("=" * 105)

    # Print Table 3: Adverse Selection Diagnostic
    print("\n" + "=" * 105)
    print("               TABLE 3: ADVERSE SELECTION DIAGNOSTIC FOR PASSIVE/LIMIT ENTRIES                 ")
    print("=" * 105)
    print("Measuring post-fill directional price return R_post(Delta t) = (P_{t+Delta t} - P_fill)/P_fill * direction")
    print("-" * 105)

    for k, eng in engines.items():
        post_1b = []
        post_2b = []
        post_4b = []
        for item in eng.post_fill_tracking:
            sym = item["symbol"]
            d = item["direction"]
            ebar = item["entry_bar"]
            px0 = item["entry_px"]

            # Bar 1 (4H)
            if (ebar + 1) < total_bars:
                ts1 = all_timestamps[ebar + 1]
                px1 = bar_market_data.get(ts1, {}).get(sym, {}).get("close", px0)
                post_1b.append(((px1 - px0) / px0) * d * 10000.0)  # bps

            # Bar 2 (8H)
            if (ebar + 2) < total_bars:
                ts2 = all_timestamps[ebar + 2]
                px2 = bar_market_data.get(ts2, {}).get(sym, {}).get("close", px0)
                post_2b.append(((px2 - px0) / px0) * d * 10000.0)

            # Bar 4 (16H)
            if (ebar + 4) < total_bars:
                ts4 = all_timestamps[ebar + 4]
                px4 = bar_market_data.get(ts4, {}).get(sym, {}).get("close", px0)
                post_4b.append(((px4 - px0) / px0) * d * 10000.0)

        m1 = np.mean(post_1b) if post_1b else 0.0
        m2 = np.mean(post_2b) if post_2b else 0.0
        m4 = np.mean(post_4b) if post_4b else 0.0
        print(f"{k:<22} | Fills: {len(eng.post_fill_tracking):<4} | R_post(4H): {m1:>+6.1f} bps | R_post(8H): {m2:>+6.1f} bps | R_post(16H): {m4:>+6.1f} bps")
    print("=" * 105)


if __name__ == "__main__":
    run_alpha_recovery_tournament()
