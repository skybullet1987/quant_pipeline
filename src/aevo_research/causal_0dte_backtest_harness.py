"""Causal 0DTE Backtesting and Simulation Harness for Aevo Latency Mispricing.

Implements the Frozen A0 research specification:
- Multi-source causal clock benchmarking: t2 = max(t1_binance, t1_hl) + eval_delay
- Queue depletion: Q_exec = max(0, Q_displayed - Q_depleted)
- Dynamic piece-wise linear fee engine: min(0.0005 * S * Q, 0.125 * P * Q) with $260 crossover
- LOO surface valuation & sparse-chain delta-gamma fallback
- Explicit terminal state transitions: SOLD, EXPIRED_ITM, EXPIRED_OTM
- Dual OCR: OCR_book and OCR_target
- Paired episode permutation test: D_i = Edge_i(0) - Edge_i(+25ms)
- Stationary block bootstrap for LCB_95%

ISOLATION INVARIANT:
Completely segregated in src/aevo_research/; zero imports of existing Hyperliquid code.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class OptionQuote:
    strike: float
    is_call: bool
    expiry_hours: float
    bid_px: float
    bid_qty: float
    ask_px: float
    ask_qty: float
    iv: float = 0.80


@dataclass
class ShockEpisode:
    episode_id: int
    underlying_symbol: str  # "BTC" or "ETH"
    t1_binance_ns: int
    t1_hl_ns: int
    spot_pre_shock: float
    spot_post_shock: float
    shock_magnitude_pct: float
    volume_sweep_usd: float
    aevo_target_strike: float
    is_call: bool
    expiry_hours: float
    target_quote_at_t2: OptionQuote
    chain_quotes: List[OptionQuote] = field(default_factory=list)
    subsequent_fills_depletion_qty: float = 0.0
    underlying_spot_trajectory: List[Tuple[float, float]] = field(default_factory=list)  # (dt_s, spot)


@dataclass
class TradeExecutionResult:
    episode_id: int
    causal_offset_ms: float
    t2_actionable_ns: int
    t4_arrival_ns: int
    q_displayed: float
    q_executable: float
    is_filled: bool
    entry_fill_px: float
    entry_fee: float
    terminal_state: str  # "SOLD", "EXPIRED_ITM", "EXPIRED_OTM"
    terminal_cash_flow: float
    terminal_fee: float
    net_realized_pnl: float
    net_edge_per_contract: float
    ocr_book: float
    ocr_target: float


class AevoFeeEngine:
    """Computes exact per-fill Aevo options taker fee."""

    @staticmethod
    def compute_taker_fee(underlying_spot: float, premium: float, qty: float) -> float:
        """Fee = min(0.0005 * S * Q, 0.125 * P * Q)."""
        fee_notional = 0.0005 * underlying_spot * qty
        fee_premium = 0.125 * premium * qty
        return min(fee_notional, fee_premium)


class Causal0DTEBacktestHarness:
    def __init__(
        self,
        eval_delay_us: float = 100.0,  # 100 microseconds local evaluation
        base_network_latency_ms: float = 15.0,  # 15ms Frankfurt -> Aevo
        target_order_qty: float = 1.0,  # Canary order size (e.g. 1 contract)
    ):
        self.eval_delay_ns = int(eval_delay_us * 1000)
        self.base_latency_ns = int(base_network_latency_ms * 1_000_000)
        self.target_order_qty = target_order_qty
        self.fee_engine = AevoFeeEngine()

    def evaluate_fair_value_change(
        self,
        target_quote: OptionQuote,
        chain: List[OptionQuote],
        spot_pre: float,
        spot_post: float,
    ) -> float:
        """Evaluates theoretical fair value change using LOO surface or delta-gamma fallback."""
        delta_s = spot_post - spot_pre
        valid_strikes = [q for q in chain if q.strike != target_quote.strike and q.bid_px > 0 and q.ask_px > 0]
        
        # Hard Rule: N_valid strikes >= 5 for LOO surface, else fallback to delta-gamma
        if len(valid_strikes) < 5:
            # Local Delta-Gamma approximation (Diagnostic Fallback)
            # Estimate local delta/gamma from Black-Scholes baseline
            t_annual = max(0.0001, target_quote.expiry_hours / 8760.0)
            sigma = target_quote.iv
            d1 = (math.log(spot_pre / target_quote.strike) + (0.5 * sigma * sigma) * t_annual) / (sigma * math.sqrt(t_annual))
            # Standard normal CDF approximation
            norm_cdf = 0.5 * (1.0 + math.erf(d1 / math.sqrt(2.0)))
            delta = norm_cdf if target_quote.is_call else (norm_cdf - 1.0)
            phi = math.exp(-0.5 * d1 * d1) / math.sqrt(2.0 * math.pi)
            gamma = phi / (spot_pre * sigma * math.sqrt(t_annual))
            return delta * delta_s + 0.5 * gamma * (delta_s ** 2)
        else:
            # Leave-One-Out surface fitting: average IV of nearest strikes
            neighbor_ivs = [q.iv for q in valid_strikes]
            loo_iv = sum(neighbor_ivs) / len(neighbor_ivs)
            t_annual = max(0.0001, target_quote.expiry_hours / 8760.0)
            # Revalue at post-shock spot
            d1_post = (math.log(spot_post / target_quote.strike) + (0.5 * loo_iv * loo_iv) * t_annual) / (loo_iv * math.sqrt(t_annual))
            d2_post = d1_post - loo_iv * math.sqrt(t_annual)
            call_post = spot_post * (0.5 * (1.0 + math.erf(d1_post / math.sqrt(2.0)))) - target_quote.strike * (0.5 * (1.0 + math.erf(d2_post / math.sqrt(2.0))))
            fair_post = call_post if target_quote.is_call else (call_post - spot_post + target_quote.strike)
            current_mid = (target_quote.bid_px + target_quote.ask_px) / 2.0
            return fair_post - current_mid

    def simulate_episode(
        self,
        episode: ShockEpisode,
        causal_offset_ms: float = 0.0,
    ) -> TradeExecutionResult:
        """Simulate single episode execution at t_entry = t2 + causal_offset_ms."""
        # 1. Multi-source ingress rule: t2 = max(t1_binance, t1_hl) + eval_delay
        t2 = max(episode.t1_binance_ns, episode.t1_hl_ns) + self.eval_delay_ns
        offset_ns = int(causal_offset_ms * 1_000_000)
        t4_arrival = t2 + self.base_latency_ns + offset_ns

        # 2. Queue Depletion
        # If latency is delayed (offset > 0), additional market depletion consumes ask liquidity
        delay_penalty_ratio = max(0.0, (self.base_latency_ns + offset_ns) / 15_000_000.0)
        effective_depletion = episode.subsequent_fills_depletion_qty * delay_penalty_ratio
        q_displayed = episode.target_quote_at_t2.ask_qty
        q_exec = max(0.0, q_displayed - effective_depletion)

        ocr_book = (q_exec / q_displayed) if q_displayed > 0 else 0.0
        ocr_target = min(q_exec, self.target_order_qty) / self.target_order_qty

        # 3. Execution check
        if q_exec < (0.1 * self.target_order_qty):
            # Unfillable event: contribute exactly $0.00
            return TradeExecutionResult(
                episode_id=episode.episode_id,
                causal_offset_ms=causal_offset_ms,
                t2_actionable_ns=t2,
                t4_arrival_ns=t4_arrival,
                q_displayed=q_displayed,
                q_executable=0.0,
                is_filled=False,
                entry_fill_px=0.0,
                entry_fee=0.0,
                terminal_state="UNFILLED",
                terminal_cash_flow=0.0,
                terminal_fee=0.0,
                net_realized_pnl=0.0,
                net_edge_per_contract=0.0,
                ocr_book=ocr_book,
                ocr_target=ocr_target,
            )

        filled_qty = min(q_exec, self.target_order_qty)
        entry_px = episode.target_quote_at_t2.ask_px
        entry_fee = self.fee_engine.compute_taker_fee(episode.spot_pre_shock, entry_px, filled_qty)

        # 4. Exit / Terminal State simulation
        # Trajectory forward 5 seconds: spot move monetization
        terminal_spot = episode.spot_post_shock
        if episode.underlying_spot_trajectory:
            terminal_spot = episode.underlying_spot_trajectory[-1][1]

        # Check option theoretical value at exit
        fair_delta = self.evaluate_fair_value_change(
            episode.target_quote_at_t2,
            episode.chain_quotes,
            episode.spot_pre_shock,
            terminal_spot,
        )
        # Exit bid reflects updated fair value minus bid-ask spread
        exit_bid_px = max(0.1, entry_px + fair_delta - (0.05 * entry_px))

        # Check terminal state
        if episode.expiry_hours <= 0.05:  # <= 3 minutes to expiry
            if episode.is_call:
                intrinsic = max(0.0, terminal_spot - episode.aevo_target_strike)
            else:
                intrinsic = max(0.0, episode.aevo_target_strike - terminal_spot)
            if intrinsic > 0:
                terminal_state = "EXPIRED_ITM"
                terminal_cf = intrinsic * filled_qty
                terminal_fee = 0.0  # Daily options exempt from settlement fee
            else:
                terminal_state = "EXPIRED_OTM"
                terminal_cf = 0.0
                terminal_fee = 0.0
        else:
            terminal_state = "SOLD"
            terminal_cf = exit_bid_px * filled_qty
            terminal_fee = self.fee_engine.compute_taker_fee(terminal_spot, exit_bid_px, filled_qty)

        # Authoritative realized cash flow:
        # PnL = Terminal Cash Flow - Entry Value - Entry Fee - Terminal Fee
        entry_val = entry_px * filled_qty
        pnl_realized = terminal_cf - entry_val - entry_fee - terminal_fee
        pnl_per_contract = pnl_realized / filled_qty if filled_qty > 0 else 0.0

        return TradeExecutionResult(
            episode_id=episode.episode_id,
            causal_offset_ms=causal_offset_ms,
            t2_actionable_ns=t2,
            t4_arrival_ns=t4_arrival,
            q_displayed=q_displayed,
            q_executable=q_exec,
            is_filled=True,
            entry_fill_px=entry_px,
            entry_fee=entry_fee,
            terminal_state=terminal_state,
            terminal_cash_flow=terminal_cf,
            terminal_fee=terminal_fee,
            net_realized_pnl=pnl_realized,
            net_edge_per_contract=pnl_per_contract,
            ocr_book=ocr_book,
            ocr_target=ocr_target,
        )

    def run_backtest_suite(
        self,
        episodes: List[ShockEpisode],
        bootstrap_iterations: int = 1000,
        block_size: int = 10,
    ) -> Dict[str, Any]:
        """Runs complete Gate 1 (Opportunity) and Gate 2 (Latency Permutation) evaluation."""
        if not episodes:
            return {"status": "FAILED", "reason": "No episodes provided"}

        btc_episodes = [e for e in episodes if e.underlying_symbol == "BTC"]
        eth_episodes = [e for e in episodes if e.underlying_symbol == "ETH"]

        # Check preregistered count rules: N_btc >= 200, N_eth >= 200, N_total >= 500
        n_total = len(episodes)
        n_btc = len(btc_episodes)
        n_eth = len(eth_episodes)

        logger_msg = f"Auditing Sample Size: Total={n_total} (Req >=500), BTC={n_btc} (Req >=200), ETH={n_eth} (Req >=200)"

        # 1. Gate 1 Evaluation at delta = 0 (15ms baseline latency)
        results_delta_0 = [self.simulate_episode(e, causal_offset_ms=0.0) for e in episodes]
        results_delta_25 = [self.simulate_episode(e, causal_offset_ms=25.0) for e in episodes]

        # Compute fillable probability and expected PnL per trigger
        filled_count_0 = sum(1 for r in results_delta_0 if r.is_filled)
        p_fillable_0 = filled_count_0 / n_total if n_total > 0 else 0.0
        edges_0 = [r.net_edge_per_contract for r in results_delta_0]
        mean_edge_0 = sum(edges_0) / len(edges_0) if edges_0 else 0.0

        # Stationary Block Bootstrap for LCB_95%
        random.seed(42)
        bootstrap_means: List[float] = []
        n_blocks = max(1, n_total // block_size)
        for _ in range(bootstrap_iterations):
            sample: List[float] = []
            for _ in range(n_blocks):
                idx = random.randint(0, max(0, n_total - block_size))
                sample.extend(edges_0[idx : idx + block_size])
            if sample:
                bootstrap_means.append(sum(sample) / len(sample))

        bootstrap_means.sort()
        lcb_95_idx = int(0.05 * len(bootstrap_means))
        lcb_95 = bootstrap_means[lcb_95_idx] if bootstrap_means else 0.0

        # Expected PnL per trigger:
        # E[PnL per trigger] = P(Q_exec > 0) * E[Net PnL | fillable]
        fillable_pnls = [r.net_realized_pnl for r in results_delta_0 if r.is_filled]
        mean_fillable_pnl = sum(fillable_pnls) / len(fillable_pnls) if fillable_pnls else 0.0
        expected_pnl_per_trigger = p_fillable_0 * mean_fillable_pnl

        # 2. Gate 2 Paired Permutation Test: D_i = Edge_i(0) - Edge_i(+25ms)
        paired_diffs = [
            r0.net_edge_per_contract - r25.net_edge_per_contract
            for r0, r25 in zip(results_delta_0, results_delta_25)
        ]
        mean_paired_d = sum(paired_diffs) / len(paired_diffs) if paired_diffs else 0.0

        # Bootstrap paired difference for H0: E[D] <= 0
        diff_means: List[float] = []
        for _ in range(bootstrap_iterations):
            sample_d: List[float] = []
            for _ in range(n_blocks):
                idx = random.randint(0, max(0, n_total - block_size))
                sample_d.extend(paired_diffs[idx : idx + block_size])
            if sample_d:
                diff_means.append(sum(sample_d) / len(sample_d))

        diff_means.sort()
        paired_lcb_95 = diff_means[int(0.05 * len(diff_means))] if diff_means else 0.0
        p_val_h0 = sum(1 for dm in diff_means if dm <= 0.0) / len(diff_means) if diff_means else 1.0

        # Mean OCRs
        ocr_book_mean = sum(r.ocr_book for r in results_delta_0) / n_total if n_total > 0 else 0.0
        ocr_target_mean = sum(r.ocr_target for r in results_delta_0) / n_total if n_total > 0 else 0.0

        gate1_pass = lcb_95 > 0.0 and expected_pnl_per_trigger > 0.0
        gate2_pass = paired_lcb_95 > 0.0 and p_val_h0 < 0.05

        return {
            "sample_counts": {
                "n_total": n_total,
                "n_btc": n_btc,
                "n_eth": n_eth,
                "meets_preregistered_sample_size": (n_total >= 500 and n_btc >= 200 and n_eth >= 200),
            },
            "gate1_opportunity_existence": {
                "mean_net_edge_per_contract": mean_edge_0,
                "lcb_95_net_edge": lcb_95,
                "surviving_liquidity_probability_pct": p_fillable_0 * 100.0,
                "expected_pnl_per_trigger_usd": expected_pnl_per_trigger,
                "ocr_book_pct": ocr_book_mean * 100.0,
                "ocr_target_pct": ocr_target_mean * 100.0,
                "gate1_status": "PASS" if gate1_pass else "FAIL",
            },
            "gate2_causal_latency_attribution": {
                "mean_paired_difference_d": mean_paired_d,
                "paired_diff_lcb_95": paired_lcb_95,
                "p_value_h0": p_val_h0,
                "gate2_status": "PASS" if gate2_pass else "FAIL",
            },
        }
