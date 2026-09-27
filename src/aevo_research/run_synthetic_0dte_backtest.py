"""Synthetic 0DTE Backtest Demonstration & Diagnostic Benchmark.

Simulates 500 shock episodes (250 BTC, 250 ETH) to evaluate:
1. Gate 1: Opportunity Existence (LCB_95% > 0, E[PnL per trigger] > 0)
2. Gate 2: Causal Latency Attribution (paired difference Edge(0) - Edge(+25ms))
3. Dual Opportunity Capture Rates (OCR_book, OCR_target)
4. Terminal state distribution (SOLD, EXPIRED_ITM, EXPIRED_OTM, UNFILLED)

ISOLATION INVARIANT:
Completely segregated in src/aevo_research/; zero interaction with Hyperliquid code.
"""

from __future__ import annotations

import random
import time
from src.aevo_research.causal_0dte_backtest_harness import (
    Causal0DTEBacktestHarness,
    OptionQuote,
    ShockEpisode,
)


def generate_synthetic_episodes(n_episodes: int = 500) -> list[ShockEpisode]:
    random.seed(42)
    episodes: list[ShockEpisode] = []

    for i in range(1, n_episodes + 1):
        is_btc = (i <= n_episodes // 2)
        symbol = "BTC" if is_btc else "ETH"
        base_spot = 65000.0 if is_btc else 2600.0

        # Shock magnitude between +0.5% and +2.5%
        shock_pct = random.uniform(0.5, 2.5)
        spot_post = base_spot * (1.0 + shock_pct / 100.0)

        # Expiry hours: between 0.2h (12m) and 3.5h
        expiry_h = random.uniform(0.2, 3.5)

        # Strike is roughly 0.5% to 1.5% OTM
        strike_dist = random.uniform(0.005, 0.015)
        target_strike = round(base_spot * (1.0 + strike_dist), -2 if is_btc else -1)

        # Initial option premium (stale quote at t2)
        # Roughly $10 to $40 for BTC, $1 to $5 for ETH
        base_prem = random.uniform(8.0, 35.0) if is_btc else random.uniform(1.0, 4.0)

        target_quote = OptionQuote(
            strike=target_strike,
            is_call=True,
            expiry_hours=expiry_h,
            bid_px=base_prem * 0.90,
            bid_qty=random.uniform(2.0, 10.0),
            ask_px=base_prem,
            ask_qty=random.uniform(1.0, 5.0),
            iv=random.uniform(0.70, 0.85),
        )

        # Generate 4-6 neighboring strikes for LOO surface
        chain: list[OptionQuote] = []
        for offset in [-400, -200, 200, 400, 600] if is_btc else [-40, -20, 20, 40, 60]:
            nbr_k = target_strike + offset
            nbr_prem = max(0.5, base_prem - (offset * 0.02 if is_btc else offset * 0.05))
            chain.append(
                OptionQuote(
                    strike=nbr_k,
                    is_call=True,
                    expiry_hours=expiry_h,
                    bid_px=nbr_prem * 0.90,
                    bid_qty=5.0,
                    ask_px=nbr_prem,
                    ask_qty=5.0,
                    iv=random.uniform(0.72, 0.82),
                )
            )

        # Multi-venue timestamp arrival: Binance and HL arrive within 1-5ms of each other
        t_base = time.time_ns() + (i * 10_000_000_000)  # 10s lockout spacing
        t_binance = t_base + random.randint(1_000_000, 3_000_000)
        t_hl = t_base + random.randint(1_000_000, 4_000_000)

        # Random competing market depletion
        subsequent_depletion = random.uniform(0.0, 3.0)

        episodes.append(
            ShockEpisode(
                episode_id=i,
                underlying_symbol=symbol,
                t1_binance_ns=t_binance,
                t1_hl_ns=t_hl,
                spot_pre_shock=base_spot,
                spot_post_shock=spot_post,
                shock_magnitude_pct=shock_pct,
                volume_sweep_usd=random.uniform(2_100_000, 6_000_000),
                aevo_target_strike=target_strike,
                is_call=True,
                expiry_hours=expiry_h,
                target_quote_at_t2=target_quote,
                chain_quotes=chain,
                subsequent_fills_depletion_qty=subsequent_depletion,
                underlying_spot_trajectory=[(5.0, spot_post + random.uniform(-50.0, 100.0) if is_btc else spot_post + random.uniform(-2.0, 5.0))],
            )
        )

    return episodes


def main():
    print("=" * 70)
    print("RUNNING 0DTE CAUSAL BACKTEST HARNESS DEMO (A0 BENCHMARK)")
    print("=" * 70)

    episodes = generate_synthetic_episodes(n_episodes=500)
    harness = Causal0DTEBacktestHarness(
        eval_delay_us=100.0,
        base_network_latency_ms=15.0,
        target_order_qty=1.0,
    )

    results = harness.run_backtest_suite(episodes)

    sample = results["sample_counts"]
    print(f"\n[SAMPLE AUDIT]")
    print(f"  Total Episodes: {sample['n_total']} (Preregistered >= 500: {sample['n_total'] >= 500})")
    print(f"  BTC Episodes:   {sample['n_btc']} (Preregistered >= 200: {sample['n_btc'] >= 200})")
    print(f"  ETH Episodes:   {sample['n_eth']} (Preregistered >= 200: {sample['n_eth'] >= 200})")
    print(f"  Sample Size Valid? {sample['meets_preregistered_sample_size']}")

    g1 = results["gate1_opportunity_existence"]
    print(f"\n[GATE 1: OPPORTUNITY EXISTENCE]")
    print(f"  Mean Net Edge / Contract:       ${g1['mean_net_edge_per_contract']:.2f}")
    print(f"  95% LCB Net Edge:               ${g1['lcb_95_net_edge']:.2f}")
    print(f"  Surviving Liquidity Probability: {g1['surviving_liquidity_probability_pct']:.1f}%")
    print(f"  Expected PnL per Trigger:       ${g1['expected_pnl_per_trigger_usd']:.2f}")
    print(f"  OCR (Book Displayed):           {g1['ocr_book_pct']:.1f}%")
    print(f"  OCR (Target 1-Contract Size):   {g1['ocr_target_pct']:.1f}%")
    print(f"  GATE 1 VERDICT:                 >>> {g1['gate1_status']} <<<")

    g2 = results["gate2_causal_latency_attribution"]
    print(f"\n[GATE 2: CAUSAL LATENCY ATTRIBUTION]")
    print(f"  Mean Paired Diff D (0 vs 25ms): ${g2['mean_paired_difference_d']:.2f}")
    print(f"  95% LCB Paired Difference:      ${g2['paired_diff_lcb_95']:.2f}")
    print(f"  p-value (H0: E[D] <= 0):         {g2['p_value_h0']:.4f}")
    print(f"  GATE 2 VERDICT:                 >>> {g2['gate2_status']} <<<")
    print("=" * 70)


if __name__ == "__main__":
    main()
