"""
1-YEAR ADVANCED ARCHITECTURE COMPARISON
================================================================================
Compares:
  1. Barebones Model (from previous run)
  2. Cash-Preservation Mode (Longs in Bull, 100% CASH in Bear)
  3. Corrected Directional Model (Longs on Top Alpha in Bull, Shorts on Bottom Alpha in Bear)
  4. Full Advanced Research Architecture (Grossman-Zhou Risk Governor + Two-Tranche State Machine + Macro Cash Governor + Walk-Forward LightGBM)
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

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.execution.papertrade_daemon import CrossSectionalAlphaRanker
from src.risk.grossman_zhou_engine import GrossmanZhouRiskGovernor

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
    tranche_a_closed: bool = False
    highest_price: float = 0.0
    lowest_price: float = 1e9


class AdvancedTwoTrancheSlotEngine:
    def __init__(self, n_slots: int = 4, sl_mult: float = 1.8, tp_a_mult: float = 2.0, max_bars: int = 18, fee_rate: float = 0.00055):
        self.n_slots = n_slots
        self.sl_mult = sl_mult
        self.tp_a_mult = tp_a_mult
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

            slot.highest_price = max(slot.highest_price, hi)
            slot.lowest_price = min(slot.lowest_price, lo)

            # 1. Tranche A Early Harvest (+2.0x ATR)
            if not slot.tranche_a_closed:
                hit_tp_a = (hi >= slot.entry_price + self.tp_a_mult * slot.atr) if slot.direction == 1 else (lo <= slot.entry_price - self.tp_a_mult * slot.atr)
                if hit_tp_a:
                    tp_a_px = slot.entry_price + self.tp_a_mult * slot.atr if slot.direction == 1 else slot.entry_price - self.tp_a_mult * slot.atr
                    ret_a = ((tp_a_px - slot.entry_price) / slot.entry_price) * slot.direction
                    pnl_a = (slot.notional * 0.5) * ret_a
                    fee_a = (slot.notional * 0.5) * self.fee_rate
                    bar_pnl += (pnl_a - fee_a)
                    self.cum_fee_usd += fee_a
                    turnover += (slot.notional * 0.5)
                    slot.tranche_a_closed = True
                    # Ratchet stop-loss to Breakeven
                    slot.sl_price = slot.entry_price

            # 2. Stop-Loss or Trailing Ratchet Exit
            if slot.tranche_a_closed:
                # Trailing stop: 1.5x ATR behind peak
                trail_sl = slot.highest_price - (1.5 * slot.atr) if slot.direction == 1 else slot.lowest_price + (1.5 * slot.atr)
                current_sl = max(slot.sl_price, trail_sl) if slot.direction == 1 else min(slot.sl_price, trail_sl)
            else:
                current_sl = slot.sl_price

            hit_sl = (lo <= current_sl) if slot.direction == 1 else (hi >= current_sl)
            time_ex = (current_bar - slot.entry_bar) >= self.max_bars

            if hit_sl or time_ex:
                exit_px = current_sl if hit_sl else cl
                rem_size = 0.5 if slot.tranche_a_closed else 1.0
                ret_rem = ((exit_px - slot.entry_price) / slot.entry_price) * slot.direction
                gross_pnl = (slot.notional * rem_size) * ret_rem
                exit_fee = (slot.notional * rem_size) * self.fee_rate
                net_pnl = gross_pnl - exit_fee

                bar_pnl += net_pnl
                self.cum_fee_usd += exit_fee
                turnover += (slot.notional * rem_size)

                reason = "TRAIL_SL" if (hit_sl and slot.tranche_a_closed) else ("INIT_SL" if hit_sl else "TIME")
                self.trades.append({
                    "symbol": sym, "direction": slot.direction, "entry_bar": slot.entry_bar,
                    "exit_bar": current_bar, "return": ret_rem, "pnl": net_pnl, "reason": reason
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
        nav: float,
        operational_leverage: float = 1.0
    ) -> float:
        avail_slots = self.n_slots - len(self.active_slots)
        if avail_slots <= 0 or operational_leverage <= 0.10:
            return 0.0

        slot_notional = (nav * operational_leverage) / float(self.n_slots)
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
            tp_px = px + (self.tp_a_mult * atr) if direction == 1 else px - (self.tp_a_mult * atr)

            self.active_slots[sym] = SlotState(
                symbol=sym, direction=direction, entry_price=px, atr=atr,
                entry_bar=current_bar, sl_price=sl_px, tp_price=tp_px, notional=slot_notional,
                highest_price=px, lowest_price=px
            )
            avail_slots -= 1

        return turnover


def run_advanced_comparison():
    print("=" * 115)
    print("          1-YEAR MACRO CASH DEFENSE & ADVANCED ARCHITECTURE COMPARISON          ")
    print("=" * 115)

    # 1. Load Data
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

    clean_df = df.drop_nulls(["mom_7d", "gk_vol_20p", "fwd_ret_4h", "atr_20"])
    all_timestamps = sorted(clean_df["timestamp_ms"].unique().to_list())
    total_bars = len(all_timestamps)

    # In-memory lookup
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

    # BTC EMA20
    btc_df = clean_df.filter(pl.col("symbol") == "BTC").sort("timestamp_ms")
    btc_ema20 = btc_df.select([
        "timestamp_ms",
        (pl.col("close") > pl.col("close").ewm_mean(span=20)).alias("btc_bull"),
        pl.col("close").alias("btc_close"),
    ])
    btc_bull_map = dict(zip(btc_ema20["timestamp_ms"].to_list(), btc_ema20["btc_bull"].to_list()))
    btc_close_map = dict(zip(btc_ema20["timestamp_ms"].to_list(), btc_ema20["btc_close"].to_list()))

    WARMUP_BARS = 180
    eval_bars = total_bars - WARMUP_BARS - 1
    feature_cols = ["residual_return", "sigma_gk_20p", "vcr_20_120", "mom_acc", "mom_24h", "mom_7d", "gk_vol_20p", "vol_compression_ratio", "vol_yang_zhang"]

    # 4 Architecture Variations
    eng_cash = AdvancedTwoTrancheSlotEngine()
    eng_adv = AdvancedTwoTrancheSlotEngine()

    ranker_cash = CrossSectionalAlphaRanker()
    ranker_adv = CrossSectionalAlphaRanker()

    gz_adv = GrossmanZhouRiskGovernor(d_max=0.22, l_base=2.5)

    eq_cash = 1000.0
    eq_adv = 1000.0
    curve_cash = [eq_cash]
    curve_adv = [eq_adv]
    to_cash = []
    to_adv = []

    # Initial training
    init_train = clean_df.filter(pl.col("timestamp_ms") < all_timestamps[WARMUP_BARS]).with_columns(
        (pl.col("fwd_ret_4h") > 0).cast(pl.Int32).alias("forward_res_decile")
    )
    ranker_cash.train_lambdarank(init_train, feature_cols)
    ranker_adv.train_lambdarank(init_train, feature_cols)

    last_retrain_bar = WARMUP_BARS

    print(f"--> Executing 1-Year Walk-Forward Simulation across {eval_bars} bars...")
    start_sim = time.time()

    for idx in range(WARMUP_BARS, total_bars - 1):
        curr_ts = all_timestamps[idx]
        curr_snap = clean_df.filter(pl.col("timestamp_ms") == curr_ts)
        curr_bar_data = bar_market_data.get(curr_ts, {})
        btc_bull = btc_bull_map.get(curr_ts, True)

        # Walk-forward retraining every 36 bars (6 days)
        if (idx - last_retrain_bar) >= 36:
            train_start_ts = all_timestamps[max(0, idx - 540)]
            rolling_train_snap = clean_df.filter(
                (pl.col("timestamp_ms") < curr_ts) & (pl.col("timestamp_ms") >= train_start_ts)
            ).with_columns(
                (pl.col("fwd_ret_4h") > 0).cast(pl.Int32).alias("forward_res_decile")
            )
            if rolling_train_snap.height > 200:
                ranker_cash.train_lambdarank(rolling_train_snap, feature_cols)
                ranker_adv.train_lambdarank(rolling_train_snap, feature_cols)
                last_retrain_bar = idx

        # Rank universe
        ranked_cash = ranker_cash.rank_universe(curr_snap, feature_cols)
        ranked_adv = ranker_adv.rank_universe(curr_snap, feature_cols)

        # -------------------------------------------------------------
        # SYSTEM 1: CASH DEFENSE (Longs in Bull, 100% CASH in Bear)
        # -------------------------------------------------------------
        if btc_bull:
            cands_cash = [(s, 1) for s in ranked_cash.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()]
        else:
            cands_cash = []  # ZERO POSITIONS -> 100% CASH PRESERVATION

        pnl_ex_c, to_ex_c = eng_cash.evaluate_exits(idx, curr_bar_data, eq_cash)
        eq_cash += pnl_ex_c
        to_open_c = eng_cash.open_positions(cands_cash, idx, curr_bar_data, eq_cash, operational_leverage=1.0)
        fwd_dict = fwd_rets_by_bar.get(curr_ts, {})
        hold_c = sum(s.notional * s.direction * (0.5 if s.tranche_a_closed else 1.0) * fwd_dict.get(sym, 0.0) for sym, s in eng_cash.active_slots.items())
        eq_cash += hold_c
        curve_cash.append(eq_cash)
        to_cash.append((to_ex_c + to_open_c) / eq_cash if eq_cash > 0 else 0.0)

        # -------------------------------------------------------------
        # SYSTEM 2: ADVANCED RESEARCH (GZ Governor + Two-Tranche + Asymmetric)
        # -------------------------------------------------------------
        lev_adv, _ = gz_adv.compute_leverage(eq_adv, 0.60 if btc_bull else 0.20, 0.80)
        if btc_bull:
            cands_adv = [(s, 1) for s in ranked_adv.filter(pl.col("symbol") != "BTC").head(6)["symbol"].to_list()]
        else:
            # When BTC is in Bear, ONLY short the absolute bottom laggards if leverage allows
            cands_adv = [(s, -1) for s in ranked_adv.filter(pl.col("symbol") != "BTC").tail(4)["symbol"].to_list()]

        pnl_ex_a, to_ex_a = eng_adv.evaluate_exits(idx, curr_bar_data, eq_adv)
        eq_adv += pnl_ex_a
        to_open_a = eng_adv.open_positions(cands_adv, idx, curr_bar_data, eq_adv, operational_leverage=lev_adv)
        hold_a = sum(s.notional * s.direction * (0.5 if s.tranche_a_closed else 1.0) * fwd_dict.get(sym, 0.0) for sym, s in eng_adv.active_slots.items())
        eq_adv += hold_a
        curve_adv.append(eq_adv)
        to_adv.append((to_ex_a + to_open_a) / eq_adv if eq_adv > 0 else 0.0)

        if (idx - WARMUP_BARS) % 500 == 0:
            pct = (idx - WARMUP_BARS) / float(eval_bars) * 100.0
            print(f"    Bar {idx - WARMUP_BARS}/{eval_bars} ({pct:.1f}%) | Cash Defense: ${eq_cash:,.2f} | Advanced GZ: ${eq_adv:,.2f}")

    sim_time = time.time() - start_sim
    print(f"--> Simulation finished in {sim_time:.2f}s.\n")

    def calc_stats(curve, to_list, fee_usd, trades):
        eq_arr = np.array(curve)
        final_eq = eq_arr[-1]
        cum_ret = (final_eq / 1000.0 - 1.0) * 100.0
        ann_mult = 365.25 / ((eval_bars * 4.0) / 24.0)
        cagr = ((final_eq / 1000.0) ** ann_mult - 1.0) * 100.0 if final_eq > 0 else -100.0
        rets = np.diff(eq_arr) / eq_arr[:-1]
        sharpe = float(np.mean(rets) / (np.std(rets) + 1e-8) * np.sqrt(2190.0))
        peak = np.maximum.accumulate(eq_arr)
        max_dd = float(np.max((peak - eq_arr) / peak)) * 100.0
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]
        wr = (len(wins) / len(trades) * 100.0) if trades else 0.0
        gross_win = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        pf = (gross_win / (gross_loss + 1e-8)) if gross_loss > 0 else 0.0
        return {
            "final_eq": final_eq, "cum_ret": cum_ret, "cagr": cagr, "sharpe": sharpe,
            "max_dd": max_dd, "wr": wr, "pf": pf, "n_trades": len(trades)
        }

    s_c = calc_stats(curve_cash, to_cash, eng_cash.cum_fee_usd, eng_cash.trades)
    s_a = calc_stats(curve_adv, to_adv, eng_adv.cum_fee_usd, eng_adv.trades)

    print("=" * 115)
    print("           FULL 1-YEAR (364-DAY) ADVANCED COMPARISON SCOREBOARD           ")
    print("=" * 115)
    print(f"{'METRIC':<30} | {'100% CASH DEFENSE IN BEAR':<28} | {'ADVANCED GZ + TWO-TRANCHE'}")
    print("-" * 115)
    print(f"{'Final Ending Equity ($)':<30} | ${s_c['final_eq']:<27,.2f} | ${s_a['final_eq']:,.2f}")
    print(f"{'Cumulative Return (%)':<30} | {s_c['cum_ret']:>+27.2f}% | {s_a['cum_ret']:>+24.2f}%")
    print(f"{'Annualized Return (CAGR)':<30} | {s_c['cagr']:>+27.2f}% | {s_a['cagr']:>+24.2f}%")
    print(f"{'Annualized Sharpe Ratio':<30} | {s_c['sharpe']:>27.2f}  | {s_a['sharpe']:>24.2f}")
    print(f"{'Maximum Drawdown (D_max)':<30} | {s_c['max_dd']:>26.2f}%  | {s_a['max_dd']:>23.2f}%")
    print(f"{'Trade Win Rate (%)':<30} | {s_c['wr']:>26.1f}%  | {s_a['wr']:>23.1f}%")
    print(f"{'Profit Factor':<30} | {s_c['pf']:>27.2f}  | {s_a['pf']:>24.2f}")
    print(f"{'Total Trades Executed':<30} | {s_c['n_trades']:>27d}  | {s_a['n_trades']:>24d}")
    print("=" * 115)


if __name__ == "__main__":
    run_advanced_comparison()
