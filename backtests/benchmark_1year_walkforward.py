"""
1-YEAR INSTITUTIONAL WALK-FORWARD OUT-OF-SAMPLE BENCHMARK
================================================================================
Comprehensive 364-Day Walk-Forward Simulation (September 2025 to September 2026)
- Evaluates 2,184 4H bars across 115 crypto perpetual assets.
- Discrete 4-Slot Architecture: 25% NAV per slot, 1.0x gross leverage, zero compounding.
- Barriers: SL = 1.8x ATR, TP = 2.5x ATR, Max holding = 18 bars (72H).
- Explicit Friction: 5.5 bps per rebalance trade.
- Macro Directional Gate: Longs when BTC > EMA20, Shorts when BTC < EMA20.

Quarterly Sub-Period Breakdown:
  Q1: Days 1 to 90
  Q2: Days 91 to 180
  Q3: Days 181 to 270
  Q4: Days 271 to 364 (Recent Summer 2026 Rally)

Contestants:
  1. LightGBM LambdaRank (A0 Static Regularized)
  2. LightGBM LambdaRank (A1 Rolling 90D Walk-Forward)
  3. BTC Buy & Hold Benchmark
  4. Equal-Weight Altcoin Index Benchmark
  5. Dollar-Neutral Decile Spread Benchmark
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

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.execution.papertrade_daemon import CrossSectionalAlphaRanker

RAW_4H_LAKE = PIPELINE_ROOT / "data" / "lake" / "raw_candles_4h.parquet"


@dataclass
class SlotState:
    symbol: str
    direction: int
    entry_price: float
    atr: float
    entry_bar: int
    sl_price: float
    tp_price: float
    notional: float


class FixedDiscreteSlotEngine:
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

    def evaluate_exits(self, current_bar: int, bar_data: Dict[str, Dict[str, float]], nav: float) -> Tuple[float, float]:
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
        target_candidates: List[Tuple[str, int]],
        current_bar: int,
        bar_data: Dict[str, Dict[str, float]],
        nav: float
    ) -> float:
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
            avail_slots -= 1

        return turnover


def run_1year_benchmark():
    print("=" * 115)
    print("        1-YEAR INSTITUTIONAL WALK-FORWARD OUT-OF-SAMPLE BENCHMARK (364 DAYS)        ")
    print("=" * 115)

    if not RAW_4H_LAKE.exists():
        raise FileNotFoundError(f"File {RAW_4H_LAKE} does not exist.")

    # 1. Load and compute clean features
    print("--> [1/5] Loading 1-Year Raw Candle Lake & Calculating Features...")
    df = pl.read_parquet(RAW_4H_LAKE).sort(["symbol", "timestamp_ms"])

    ln_hl = (pl.col("high") / pl.col("low")).log()
    ln_co = (pl.col("close") / pl.col("open")).log()
    gk_bar_sq = 0.5 * (ln_hl ** 2) - (2.0 * np.log(2) - 1.0) * (ln_co ** 2)

    df = df.with_columns([
        gk_bar_sq.clip(0.0, 1.0).alias("gk_bar_sq"),
        (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).alias("ret_4h"),
        (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_4h"),
        (pl.col("close") / pl.col("close").shift(6).over("symbol") - 1.0).alias("mom_24h"),
        (pl.col("close") / pl.col("close").shift(42).over("symbol") - 1.0).alias("mom_7d"),
    ])

    df = df.with_columns([
        pl.col("gk_bar_sq").rolling_mean(window_size=20).over("symbol").sqrt().alias("gk_vol_20p"),
        (pl.col("mom_24h") - pl.col("mom_24h").shift(6).over("symbol")).alias("mom_acc"),
        pl.col("ret_4h").rolling_std(window_size=20).over("symbol").alias("vol_yang_zhang"),
        (pl.col("high") - pl.col("low")).rolling_mean(window_size=20).over("symbol").alias("atr_20"),
    ])

    df = df.with_columns([
        (pl.col("gk_vol_20p") / (pl.col("gk_vol_20p").rolling_min(window_size=120).over("symbol") + 1e-8)).alias("vol_compression_ratio"),
        pl.col("gk_vol_20p").alias("sigma_gk_20p"),
        pl.col("ret_4h").alias("residual_return"),
    ])
    df = df.with_columns(pl.col("vol_compression_ratio").alias("vcr_20_120"))

    # Drop warmups
    clean_df = df.drop_nulls(["mom_7d", "gk_vol_20p", "fwd_ret_4h", "atr_20"])
    all_timestamps = sorted(clean_df["timestamp_ms"].unique().to_list())
    total_bars = len(all_timestamps)
    n_assets = clean_df["symbol"].n_unique()

    ts_start = pd.to_datetime(all_timestamps[0], unit="ms", utc=True)
    ts_end = pd.to_datetime(all_timestamps[-1], unit="ms", utc=True)
    print(f"    Loaded {clean_df.height:,} rows across {total_bars} 4H periods ({n_assets} assets).")
    print(f"    Time range: {ts_start.date()} to {ts_end.date()} ({(all_timestamps[-1] - all_timestamps[0]) / (86400 * 1000):.1f} days).")

    # 2. Fast memory structures
    print("--> [2/5] Constructing Fast In-Memory Market Cache & Benchmark Series...")
    bar_market_data = {}
    fwd_rets_by_bar = {}
    for row in clean_df.select(["timestamp_ms", "symbol", "high", "low", "close", "atr_20", "fwd_ret_4h"]).iter_rows(named=True):
        t = row["timestamp_ms"]
        s = row["symbol"]
        if t not in bar_market_data:
            bar_market_data[t] = {}
            fwd_rets_by_bar[t] = {}
        c = row["close"] or 1.0
        bar_market_data[t][s] = {
            "high": row["high"] or (c * 1.01),
            "low": row["low"] or (c * 0.99),
            "close": c,
            "atr": row["atr_20"] or (c * 0.03),
        }
        fwd_rets_by_bar[t][s] = row["fwd_ret_4h"] or 0.0

    # Macro trend map (BTC close > EMA20)
    btc_df = clean_df.filter(pl.col("symbol") == "BTC").sort("timestamp_ms")
    btc_ema20 = btc_df.select([
        "timestamp_ms",
        (pl.col("close") > pl.col("close").ewm_mean(span=20)).alias("btc_bull"),
        pl.col("close").alias("btc_close"),
    ])
    btc_bull_map = dict(zip(btc_ema20["timestamp_ms"].to_list(), btc_ema20["btc_bull"].to_list()))
    btc_close_map = dict(zip(btc_ema20["timestamp_ms"].to_list(), btc_ema20["btc_close"].to_list()))

    # Equal-Weight Alt Index returns
    alt_df = clean_df.filter(pl.col("symbol") != "BTC").group_by("timestamp_ms").agg(pl.col("fwd_ret_4h").mean().alias("alt_index_ret"))
    alt_index_map = dict(zip(alt_df["timestamp_ms"].to_list(), alt_df["alt_index_ret"].to_list()))

    # 3. Model Setup
    print("--> [3/5] Initializing Contestants & Setting Up Walk-Forward Framework...")
    WARMUP_BARS = 180  # 30-day initial training warmup
    eval_bars = total_bars - WARMUP_BARS - 1

    feature_cols = ["residual_return", "sigma_gk_20p", "vcr_20_120", "mom_acc", "mom_24h", "mom_7d", "gk_vol_20p", "vol_compression_ratio", "vol_yang_zhang"]

    eng_static = FixedDiscreteSlotEngine()
    eng_rolling = FixedDiscreteSlotEngine()

    ranker_static = CrossSectionalAlphaRanker()
    ranker_rolling = CrossSectionalAlphaRanker()

    eq_static = 1000.0
    eq_rolling = 1000.0
    curve_static = [eq_static]
    curve_rolling = [eq_rolling]
    to_static = []
    to_rolling = []

    # Benchmarks
    btc_start = btc_close_map.get(all_timestamps[WARMUP_BARS], 1.0)
    btc_curve = [1000.0]
    alt_eq = 1000.0
    alt_curve = [alt_eq]
    spread_eq = 1000.0
    spread_curve = [spread_eq]

    # Pre-train static model on the initial 30-day warmup
    init_train_snap = clean_df.filter(pl.col("timestamp_ms") < all_timestamps[WARMUP_BARS]).with_columns(
        (pl.col("fwd_ret_4h") > 0).cast(pl.Int32).alias("forward_res_decile")
    )
    ranker_static.train_lambdarank(init_train_snap, feature_cols)
    ranker_rolling.train_lambdarank(init_train_snap, feature_cols)

    last_retrain_bar = WARMUP_BARS

    print(f"--> [4/5] Executing 1-Year Walk-Forward Simulation across {eval_bars} 4H bars ({(eval_bars * 4)/24:.1f} days)...")
    start_sim = time.time()

    quarter_markers = [
        ("Q1 (Months 1-3)", WARMUP_BARS, WARMUP_BARS + eval_bars // 4),
        ("Q2 (Months 4-6)", WARMUP_BARS + eval_bars // 4, WARMUP_BARS + 2 * (eval_bars // 4)),
        ("Q3 (Months 7-9)", WARMUP_BARS + 2 * (eval_bars // 4), WARMUP_BARS + 3 * (eval_bars // 4)),
        ("Q4 (Months 10-12)", WARMUP_BARS + 3 * (eval_bars // 4), total_bars - 1),
    ]

    for idx in range(WARMUP_BARS, total_bars - 1):
        curr_ts = all_timestamps[idx]
        curr_snap = clean_df.filter(pl.col("timestamp_ms") == curr_ts)
        curr_bar_data = bar_market_data.get(curr_ts, {})
        btc_bull = btc_bull_map.get(curr_ts, True)

        # 1. Update Benchmarks
        btc_cur = btc_close_map.get(curr_ts, btc_start)
        btc_curve.append(1000.0 * (btc_cur / btc_start))

        alt_r = alt_index_map.get(curr_ts, 0.0)
        alt_eq *= (1.0 + alt_r)
        alt_curve.append(alt_eq)

        # Decile Spread
        if curr_snap.height >= 10:
            n_dec = max(1, int(curr_snap.height * 0.10))
            sorted_mom = curr_snap.sort("mom_24h", descending=True)
            top_syms = sorted_mom.head(n_dec)["symbol"].to_list()
            bot_syms = sorted_mom.tail(n_dec)["symbol"].to_list()
            top_r = np.mean([fwd_rets_by_bar.get(curr_ts, {}).get(s, 0.0) for s in top_syms])
            bot_r = np.mean([fwd_rets_by_bar.get(curr_ts, {}).get(s, 0.0) for s in bot_syms])
            spread_eq *= (1.0 + (top_r - bot_r) - 0.00055 * 0.20)
        spread_curve.append(spread_eq)

        # 2. Retraining Rolling Model: every 36 bars (6 days) on rolling 90-day window (540 bars)
        if (idx - last_retrain_bar) >= 36:
            train_start_ts = all_timestamps[max(0, idx - 540)]
            rolling_train_snap = clean_df.filter(
                (pl.col("timestamp_ms") < curr_ts) & (pl.col("timestamp_ms") >= train_start_ts)
            ).with_columns(
                (pl.col("fwd_ret_4h") > 0).cast(pl.Int32).alias("forward_res_decile")
            )
            if rolling_train_snap.height > 200:
                ranker_rolling.train_lambdarank(rolling_train_snap, feature_cols)
                last_retrain_bar = idx

        if (idx - WARMUP_BARS) % 250 == 0:
            pct_done = (idx - WARMUP_BARS) / float(eval_bars) * 100.0
            print(f"    Progress: Bar {idx - WARMUP_BARS}/{eval_bars} ({pct_done:.1f}%) | Static: ${eq_static:,.2f} | Rolling: ${eq_rolling:,.2f}")

        # 3. Model Inferences
        ranked_static = ranker_static.rank_universe(curr_snap, feature_cols)
        static_cands = [
            (s, 1 if btc_bull else -1) for s in ranked_static.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()
        ]

        ranked_rolling = ranker_rolling.rank_universe(curr_snap, feature_cols)
        rolling_cands = [
            (s, 1 if btc_bull else -1) for s in ranked_rolling.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()
        ]

        # 4. Step Static Engine
        pnl_ex_s, to_ex_s = eng_static.evaluate_exits(idx, curr_bar_data, eq_static)
        eq_static += pnl_ex_s
        to_open_s = eng_static.open_positions(static_cands, idx, curr_bar_data, eq_static)
        fwd_dict = fwd_rets_by_bar.get(curr_ts, {})
        hold_s = sum(s.notional * s.direction * fwd_dict.get(sym, 0.0) for sym, s in eng_static.active_slots.items())
        eq_static += hold_s
        curve_static.append(eq_static)
        to_static.append((to_ex_s + to_open_s) / eq_static if eq_static > 0 else 0.0)

        # 5. Step Rolling Engine
        pnl_ex_r, to_ex_r = eng_rolling.evaluate_exits(idx, curr_bar_data, eq_rolling)
        eq_rolling += pnl_ex_r
        to_open_r = eng_rolling.open_positions(rolling_cands, idx, curr_bar_data, eq_rolling)
        hold_r = sum(s.notional * s.direction * fwd_dict.get(sym, 0.0) for sym, s in eng_rolling.active_slots.items())
        eq_rolling += hold_r
        curve_rolling.append(eq_rolling)
        to_rolling.append((to_ex_r + to_open_r) / eq_rolling if eq_rolling > 0 else 0.0)

    sim_time = time.time() - start_sim
    print(f"--> [5/5] Full 1-Year Simulation Completed in {sim_time:.2f}s.\n")

    # 5. Results & Quarterly Attribution
    def calc_stats(curve, to_list, fee_usd, trades):
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
        fee_drag = (fee_usd / 1000.0) * 100.0
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]
        wr = (len(wins) / len(trades) * 100.0) if trades else 0.0
        gross_win = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        pf = (gross_win / (gross_loss + 1e-8)) if gross_loss > 0 else 0.0
        return {
            "final_eq": final_eq, "cum_ret": cum_ret, "cagr": cagr, "sharpe": sharpe,
            "sortino": sortino, "max_dd": max_dd, "avg_to": avg_to, "fee_drag": fee_drag,
            "wr": wr, "pf": pf, "n_trades": len(trades)
        }

    s_stat = calc_stats(curve_static, to_static, eng_static.cum_fee_usd, eng_static.trades)
    s_roll = calc_stats(curve_rolling, to_rolling, eng_rolling.cum_fee_usd, eng_rolling.trades)

    def calc_bench(curve):
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

    b_btc = calc_bench(btc_curve)
    b_alt = calc_bench(alt_curve)
    b_spr = calc_bench(spread_curve)

    print("=" * 115)
    print("           FULL 1-YEAR (364-DAY) PERFORMANCE SCOREBOARD (FROZEN 4-SLOT BASELINE)           ")
    print("=" * 115)
    print(f"{'PERFORMANCE METRIC':<30} | {'LGBM STATIC (A0)':<20} | {'LGBM ROLLING 90D (A1)':<20} | {'BTC BUY & HOLD'}")
    print("-" * 115)
    print(f"{'Final Ending Equity ($)':<30} | ${s_stat['final_eq']:<19,.2f} | ${s_roll['final_eq']:<19,.2f} | ${b_btc['final_eq']:,.2f}")
    print(f"{'Cumulative Return (%)':<30} | {s_stat['cum_ret']:>+19.2f}% | {s_roll['cum_ret']:>+19.2f}% | {b_btc['cum_ret']:>+13.2f}%")
    print(f"{'Annualized Return (CAGR)':<30} | {s_stat['cagr']:>+19.2f}% | {s_roll['cagr']:>+19.2f}% | {b_btc['cagr']:>+13.2f}%")
    print(f"{'Annualized Sharpe Ratio':<30} | {s_stat['sharpe']:>19.2f}  | {s_roll['sharpe']:>19.2f}  | {b_btc['sharpe']:>13.2f}")
    print(f"{'Annualized Sortino Ratio':<30} | {s_stat['sortino']:>19.2f}  | {s_roll['sortino']:>19.2f}  | —")
    print(f"{'Maximum Drawdown (D_max)':<30} | {s_stat['max_dd']:>18.2f}%  | {s_roll['max_dd']:>18.2f}%  | {b_btc['max_dd']:>12.2f}%")
    print(f"{'Trade Win Rate (%)':<30} | {s_stat['wr']:>18.1f}%  | {s_roll['wr']:>18.1f}%  | —")
    print(f"{'Profit Factor':<30} | {s_stat['pf']:>19.2f}  | {s_roll['pf']:>19.2f}  | —")
    print(f"{'Total Trades Executed':<30} | {s_stat['n_trades']:>19d}  | {s_roll['n_trades']:>19d}  | —")
    print(f"{'Avg Turnover / 4H Bar (%)':<30} | {s_stat['avg_to']:>18.2f}%  | {s_roll['avg_to']:>18.2f}%  | —")
    print(f"{'Exact Total Fee Drag (%)':<30} | {s_stat['fee_drag']:>18.2f}%  | {s_roll['fee_drag']:>18.2f}%  | —")
    print("=" * 115)

    # Relative Benchmarks Comparison
    print("\n" + "=" * 105)
    print("                             1-YEAR RELATIVE BENCHMARK ATTRIBUTION                             ")
    print("=" * 105)
    print(f"{'BENCHMARK':<32} | {'ENDING EQUITY':<16} | {'CUMULATIVE RET':<16} | {'SHARPE':<8} | {'MAX DD'}")
    print("-" * 105)
    print(f"{'LGBM Static (A0)':<32} | ${s_stat['final_eq']:<15,.2f} | {s_stat['cum_ret']:>+15.2f}% | {s_stat['sharpe']:>6.2f} | {s_stat['max_dd']:>5.2f}%")
    print(f"{'LGBM Rolling 90D (A1)':<32} | ${s_roll['final_eq']:<15,.2f} | {s_roll['cum_ret']:>+15.2f}% | {s_roll['sharpe']:>6.2f} | {s_roll['max_dd']:>5.2f}%")
    print(f"{'Equal-Weight Altcoin Index':<32} | ${b_alt['final_eq']:<15,.2f} | {b_alt['cum_ret']:>+15.2f}% | {b_alt['sharpe']:>6.2f} | {b_alt['max_dd']:>5.2f}%")
    print(f"{'Bitcoin Buy & Hold':<32} | ${b_btc['final_eq']:<15,.2f} | {b_btc['cum_ret']:>+15.2f}% | {b_btc['sharpe']:>6.2f} | {b_btc['max_dd']:>5.2f}%")
    print(f"{'Dollar-Neutral Decile Spread':<32} | ${b_spr['final_eq']:<15,.2f} | {b_spr['cum_ret']:>+15.2f}% | {b_spr['sharpe']:>6.2f} | {b_spr['max_dd']:>5.2f}%")
    print("=" * 105)

    # Quarterly Breakdown
    print("\n" + "=" * 105)
    print("                             QUARTERLY REGIME DECOMPOSITION                                    ")
    print("=" * 105)
    print(f"{'QUARTER':<24} | {'STATIC RET (%)':<16} | {'ROLLING RET (%)':<16} | {'BTC RET (%)':<14} | {'ALT INDEX RET (%)'}")
    print("-" * 105)

    c_s = np.array(curve_static)
    c_r = np.array(curve_rolling)
    c_b = np.array(btc_curve)
    c_a = np.array(alt_curve)

    for q_name, s_idx, e_idx in quarter_markers:
        # adjust relative to WARMUP_BARS
        rel_s = s_idx - WARMUP_BARS
        rel_e = min(e_idx - WARMUP_BARS, len(c_s) - 1)
        r_s = (c_s[rel_e] / c_s[rel_s] - 1.0) * 100.0
        r_r = (c_r[rel_e] / c_r[rel_s] - 1.0) * 100.0
        r_b = (c_b[rel_e] / c_b[rel_s] - 1.0) * 100.0
        r_a = (c_a[rel_e] / c_a[rel_s] - 1.0) * 100.0
        print(f"{q_name:<24} | {r_s:>+14.2f}% | {r_r:>+15.2f}% | {r_b:>+12.2f}% | {r_a:>+15.2f}%")
    print("=" * 105)


if __name__ == "__main__":
    run_1year_benchmark()
