#!/usr/bin/env python3
"""
Unit and Integration Test Suite for experiments.polymarket
==========================================================
Validates:
  1. exp_s1_negrisk_convert: Gamma API parsing, subset evaluation, pure negative-cost
     arbitrage detection, depth capping (<=50%), simulated batch postOrders,
     on-chain convertPositions, cash unlocking, residual lottery shares, and legging recovery.
  2. exp_s10_insider_shadow: OrderFilled direction decoding, MM/Arb exclusion,
     domain classification, exact Murphy (1973) Brier score decomposition, ECE,
     live shadow triggers, and Sybil wash-trade kill-switches.
  3. exp_s2_uma_na_scanner: Near-expiry extreme skew filtering, semantic text & rule
     parsing (strict cutoffs, named URLs, postponement), asymmetric N/A $0.50 payoffs (12.5x-50x),
     UMA OO bond dispute monitoring, and nuisance disputer detection.
"""

import math
import time
import pytest

from experiments.polymarket.exp_s1_negrisk_convert import (
    NegRiskConvertArbitrageEngine,
    NegRiskMarketBundle,
    NegRiskOutcome,
    SubsetArbitrageOpportunity,
    NEGRISK_ADAPTER_ADDRESS,
)
from experiments.polymarket.exp_s10_insider_shadow import (
    PolygonInsiderShadowEngine,
    OrderFilledTrade,
    MurphyBrierDecomposition,
    compute_murphy_brier_decomposition,
    GNOSIS_SAFE_FACTORY,
)
from experiments.polymarket.exp_s2_uma_na_scanner import (
    UmaNaResolutionScanner,
    UmaDescriptionParser,
    UmaMarketCandidate,
    UmaDisputeEvent,
)


# ==============================================================================
# TEST SUITE 1: EXPERIMENT S1 (NEGRISK CONVERT ARBITRAGE)
# ==============================================================================

def test_s1_negrisk_pure_negative_cost_detection():
    """Verify detection of Pure Negative-Cost subsets: Sum P_ask(NO) < |M| - 1."""
    # Construct a 4-outcome NegRisk event (N=4)
    # Outcome 0: NO ask = 0.60
    # Outcome 1: NO ask = 0.65
    # Outcome 2: NO ask = 0.60
    # Outcome 3: NO ask = 0.90
    # For subset M = {0, 1, 2}, |M| = 3.
    # Sum P_ask(NO) = 0.60 + 0.65 + 0.60 = 1.85.
    # Unlocked Cash = |M| - 1 = 3 - 1 = 2.00 USDC!
    # Pure Negative Cost: 1.85 < 2.00!
    # Immediate cash profit per share = 2.00 - 1.85 = +0.15 USDC cash,
    # PLUS 1 share of free residual Outcome 3 YES!
    outcomes = [
        NegRiskOutcome(
            outcome_index=0, title="Candidate A", condition_id="0xCOND_0",
            yes_token_id="TOK_A_Y", no_token_id="TOK_A_N",
            best_bid_yes=0.35, best_ask_yes=0.40, depth_bid_yes=1000.0, depth_ask_yes=1000.0,
            best_bid_no=0.55, best_ask_no=0.60, depth_bid_no=1000.0, depth_ask_no=500.0,
        ),
        NegRiskOutcome(
            outcome_index=1, title="Candidate B", condition_id="0xCOND_1",
            yes_token_id="TOK_B_Y", no_token_id="TOK_B_N",
            best_bid_yes=0.30, best_ask_yes=0.35, depth_bid_yes=1000.0, depth_ask_yes=1000.0,
            best_bid_no=0.60, best_ask_no=0.65, depth_bid_no=1000.0, depth_ask_no=400.0,
        ),
        NegRiskOutcome(
            outcome_index=2, title="Candidate C", condition_id="0xCOND_2",
            yes_token_id="TOK_C_Y", no_token_id="TOK_C_N",
            best_bid_yes=0.35, best_ask_yes=0.40, depth_bid_yes=1000.0, depth_ask_yes=1000.0,
            best_bid_no=0.55, best_ask_no=0.60, depth_bid_no=1000.0, depth_ask_no=600.0,
        ),
        NegRiskOutcome(
            outcome_index=3, title="Candidate D (Longshot)", condition_id="0xCOND_3",
            yes_token_id="TOK_D_Y", no_token_id="TOK_D_N",
            best_bid_yes=0.05, best_ask_yes=0.10, depth_bid_yes=1000.0, depth_ask_yes=1000.0,
            best_bid_no=0.85, best_ask_no=0.90, depth_bid_no=1000.0, depth_ask_no=800.0,
        ),
    ]

    bundle = NegRiskMarketBundle(
        event_id="EVT_NEGRISK_1",
        title="2028 Presidential Primary (4-way)",
        neg_risk_market_id=NEGRISK_ADAPTER_ADDRESS,
        outcomes=outcomes,
        category="politics",
        taker_fee_rate=0.00,
    )

    engine = NegRiskConvertArbitrageEngine(depth_cap_ratio=0.50)
    engine.bundles[bundle.event_id] = bundle

    opps = engine.evaluate_bundle_subsets(bundle)
    assert len(opps) > 0

    # Look for the pure negative cost opportunity on {0, 1, 2}
    pure_opps = [o for o in opps if o.is_pure_negative_cost]
    assert len(pure_opps) >= 1

    # Both 3-leg and 4-leg pure negative cost subsets exist
    opp_3legs = [o for o in pure_opps if o.num_legs == 3]
    assert len(opp_3legs) >= 1
    opp_3leg = opp_3legs[0]
    assert set(opp_3leg.subset_indices) == {0, 1, 2}
    assert opp_3leg.sum_no_ask == 1.85
    assert opp_3leg.unlocked_cash_per_share == 2.0
    # Net edge should include unlocked cash (2.00) + residual YES bid (0.05) - cost (1.85) - gas (0.02)
    assert opp_3leg.is_pure_negative_cost is True

    # Sizing check: Depth cap <= 50% min ask depth
    # Min ask depth across {0, 1, 2} is min(500, 400, 600) = 400.0
    # Q = 400.0 * 0.50 = 200.0 shares
    assert opp_3leg.max_executable_qty == 200.0
    # Immediate cash profit = (2.0 - 1.85) * 200.0 = $30.00 cash
    assert opp_3leg.immediate_cash_profit_usd == 30.0
    # Residual lottery shares: 200.0 shares of Candidate D YES
    assert "Candidate D (Longshot)" in opp_3leg.residual_lottery_shares
    assert opp_3leg.residual_lottery_shares["Candidate D (Longshot)"] == 200.0


def test_s1_batch_execution_and_legging_salvage():
    """Verify batch order execution, on-chain conversion, and fallback subset salvage on miss."""
    outcomes = [
        NegRiskOutcome(0, "A", "C0", "YA", "NA", 0.3, 0.4, 500, 500, 0.5, 0.6, 500, 500),
        NegRiskOutcome(1, "B", "C1", "YB", "NB", 0.3, 0.4, 500, 500, 0.5, 0.6, 500, 500),
        NegRiskOutcome(2, "C", "C2", "YC", "NC", 0.3, 0.4, 500, 500, 0.5, 0.6, 500, 500),
        NegRiskOutcome(3, "D", "C3", "YD", "ND", 0.05, 0.1, 500, 500, 0.8, 0.9, 500, 500),
    ]
    bundle = NegRiskMarketBundle("EVT_2", "Primary", NEGRISK_ADAPTER_ADDRESS, outcomes)
    engine = NegRiskConvertArbitrageEngine()
    engine.bundles[bundle.event_id] = bundle

    opps = engine.evaluate_bundle_subsets(bundle)
    opp = opps[0]

    # Test 1: Full fill (0% miss probability)
    res_full = engine.simulate_execution(opp, target_qty=100.0, leg_miss_probability=0.0)
    assert res_full.is_full_bundle_fill is True
    assert res_full.legging_failed is False
    assert len(res_full.legs_filled) == opp.num_legs
    assert res_full.cash_unlocked_usd > 0
    assert "0x" in res_full.polygon_tx_hash

    # Test 2: Simulated leg miss (force leg 2 to miss)
    # If 1 leg misses among 3 legs, remaining 2 legs can STILL convert via convertPositions(|M'| = 2)!
    res_partial = engine.simulate_execution(opp, target_qty=100.0, leg_miss_probability=0.35)
    # Regardless of miss, if >=2 legs filled, fallback subset is salvaged
    if len(res_partial.legs_filled) >= 2:
        assert res_partial.cash_unlocked_usd == (len(res_partial.converted_subset) - 1) * 100.0
    audit = engine.get_audit_summary()
    assert audit["total_simulated_executions"] == 2


# ==============================================================================
# TEST SUITE 2: EXPERIMENT S10 (ORDERFILLED INSIDER SHADOWING)
# ==============================================================================

def test_s10_order_filled_direction_decoding():
    """Verify true trade direction decoded from makerAssetId in OrderFilled logs."""
    # Case 1: makerAssetId == 0 -> Maker buying with USDC. Maker is BUYER.
    log_buy = {
        "txHash": "0xABC1",
        "maker": "0xBuyerWallet",
        "taker": "0xSellerWallet",
        "makerAssetId": 0,
        "takerAssetId": 123456789,
        "makerAmountFilled": 5000 * 1e6,  # $5,000 USDC paid
        "takerAmountFilled": 10000 * 1e6, # 10,000 shares received
        "fee": 0,
    }
    trade_buy = PolygonInsiderShadowEngine.decode_order_filled(log_buy, question="Who will win the election?")
    assert trade_buy.buyer == "0xbuyerwallet"
    assert trade_buy.seller == "0xsellerwallet"
    assert trade_buy.price == 0.50
    assert trade_buy.size == 10000.0
    assert trade_buy.usd_notional == 5000.0
    assert trade_buy.domain == "POLITICS"

    # Case 2: makerAssetId != 0 -> Maker selling conditional tokens for USDC. Taker is BUYER.
    log_sell = {
        "txHash": "0xABC2",
        "maker": "0xSellerWallet",
        "taker": "0xBuyerWallet",
        "makerAssetId": 987654321,
        "takerAssetId": 0,
        "makerAmountFilled": 20000 * 1e6, # 20,000 shares sold
        "takerAmountFilled": 4000 * 1e6,  # $4,000 USDC received
        "fee": 0,
    }
    trade_sell = PolygonInsiderShadowEngine.decode_order_filled(log_sell, question="Will the Fed cut interest rates?")
    assert trade_sell.buyer == "0xbuyerwallet"
    assert trade_sell.seller == "0xsellerwallet"
    assert trade_sell.price == 0.20  # 4000 / 20000 = 0.20
    assert trade_sell.size == 20000.0
    assert trade_sell.usd_notional == 4000.0
    assert trade_sell.domain == "MACRO"


def test_s10_murphy_brier_decomposition_identity():
    """Verify exact Murphy (1973) Brier Score decomposition identity: BS = Rel - Res + Unc."""
    # Synthetic predictions and binary outcomes
    history = [
        (0.85, 1), (0.90, 1), (0.80, 1), (0.75, 1),
        (0.20, 0), (0.15, 0), (0.10, 0), (0.05, 0),
        (0.60, 1), (0.40, 0),
    ]
    decomp = compute_murphy_brier_decomposition(history, num_bins=5)

    # Mathematical identity: BS == Reliability - Resolution + Uncertainty
    reconstructed_bs = decomp.reliability - decomp.resolution + decomp.uncertainty
    assert math.isclose(decomp.brier_score, reconstructed_bs, rel_tol=1e-4)

    # Resolution must be positive (measures informative discriminative power)
    assert decomp.resolution > 0.0
    # ECE must be non-negative
    assert decomp.ece >= 0.0


def test_s10_mm_arbitrageur_exclusion():
    """Verify wallets calling PositionsConverted or splitPosition are excluded from insider ranking."""
    engine = PolygonInsiderShadowEngine()
    mm_wallet = "0xmarketmaker123"

    # Flag via on-chain contract events
    engine.register_mm_exclusion_event("PositionsConverted", mm_wallet)
    assert mm_wallet.lower() in engine.excluded_mm_wallets

    # Ingest resolved trade for this MM
    trade = OrderFilledTrade(
        tx_hash="0x1", block_number=100, timestamp=time.time(), exchange_address="0xEX",
        order_hash="0xORD", maker=mm_wallet, taker="0xother", maker_asset_id=0, taker_asset_id=1,
        maker_amount=10000, taker_amount=50000, fee=0, buyer=mm_wallet, seller="0xother",
        price=0.20, size=50000, usd_notional=10000, token_id="1", domain="POLITICS",
    )
    engine.record_resolved_trade(trade, outcome=1)
    engine.recompute_all_calibrations()

    # MM wallet must NOT appear in calibrated rankings
    assert mm_wallet not in engine.calibrated_wallets


def test_s10_live_shadow_trigger_and_wash_trade_filter():
    """Verify live copy triggers and mandatory Sybil wash-trade abort."""
    engine = PolygonInsiderShadowEngine()

    insider_wallet = "0xinsideralpha"
    # Seed historical trades with high resolution
    for _ in range(8):
        trade = OrderFilledTrade(
            tx_hash="0xH", block_number=1, timestamp=time.time() - 1000, exchange_address="0xEX",
            order_hash="0xO", maker=insider_wallet, taker="0xrandom", maker_asset_id=0, taker_asset_id=1,
            maker_amount=10000, taker_amount=40000, fee=0, buyer=insider_wallet, seller="0xrandom",
            price=0.25, size=40000, usd_notional=10000, token_id="1", domain="POLITICS",
        )
        engine.record_resolved_trade(trade, outcome=1)
    engine.recompute_all_calibrations()

    # 1. Valid Trigger: Insider buys >$10k at price 0.20 in Politics
    live_trade = OrderFilledTrade(
        tx_hash="0xLIVE1", block_number=200, timestamp=time.time(), exchange_address="0xEX",
        order_hash="0xORD1", maker=insider_wallet, taker="0xclean_seller", maker_asset_id=0, taker_asset_id=1,
        maker_amount=15000, taker_amount=75000, fee=0, buyer=insider_wallet, seller="0xclean_seller",
        price=0.20, size=75000, usd_notional=15000, token_id="1", domain="POLITICS",
        question="Will Candidate A win the general election?",
    )
    sig1 = engine.process_live_order_filled(live_trade)
    assert sig1 is not None
    assert sig1.action == "SHADOW_BUY_FOK"
    assert sig1.wash_trade_flagged is False

    # 2. Sybil Wash-Trade Abort: Counterparty shares upstream EOA cluster
    parent_eoa = "0xwhale_parent_eoa"
    engine.register_proxy_wallet(insider_wallet, GNOSIS_SAFE_FACTORY, time.time() - 10000, 50000, upstream_funding_eoa=parent_eoa)
    engine.register_proxy_wallet("0xsybil_seller", GNOSIS_SAFE_FACTORY, time.time() - 10000, 50000, upstream_funding_eoa=parent_eoa)

    wash_trade = OrderFilledTrade(
        tx_hash="0xWASH", block_number=201, timestamp=time.time(), exchange_address="0xEX",
        order_hash="0xORD2", maker=insider_wallet, taker="0xsybil_seller", maker_asset_id=0, taker_asset_id=1,
        maker_amount=20000, taker_amount=100000, fee=0, buyer=insider_wallet, seller="0xsybil_seller",
        price=0.20, size=100000, usd_notional=20000, token_id="1", domain="POLITICS",
        question="Will Candidate A win the general election?",
    )
    sig_wash = engine.process_live_order_filled(wash_trade)
    assert sig_wash is not None
    assert sig_wash.action == "ABORT_WASH_TRADE"
    assert sig_wash.wash_trade_flagged is True
    assert "COUNTERPARTY_SHARED_FUNDING_EOA" in sig_wash.wash_trade_reason


# ==============================================================================
# TEST SUITE 3: EXPERIMENT S2 (UMA N/A $0.50 & DVM DISPUTE SCANNER)
# ==============================================================================

def test_s2_uma_description_rule_parsing():
    """Verify semantic text parsing for strict cutoffs, URLs, and postponement clauses."""
    desc = (
        "This market will resolve to 'YES' if the US Federal Reserve cuts rates by December 31, 2026, 11:59 PM ET. "
        "Resolution will be based on official releases from https://www.federalreserve.gov and Bloomberg. "
        "If the FOMC meeting is postponed or canceled, or if no official release occurs by the deadline, "
        "the market will resolve to 50-50 (N/A)."
    )
    rules = UmaDescriptionParser.parse_description(desc)

    assert rules.has_strict_utc_cutoff is True
    assert rules.cutoff_timestamp_str is not None
    assert "December 31, 2026" in rules.cutoff_timestamp_str

    assert rules.has_named_sources is True
    assert any("federalreserve.gov" in d or "bloomberg.com" in d for d in rules.named_source_domains)

    assert rules.has_postponement_clause is True
    assert rules.has_na_50_50_clause is True


def test_s2_uma_na_asymmetric_payoff_multiplier():
    """Verify candidate flagging and 12.5x to 50x payoff calculation on slipped deadlines."""
    now_ts = 1792000000.0  # Simulated present

    # Market where YES = 0.98, NO = 0.02, but deadline was 2 hours ago!
    markets = [{
        "conditionId": "0xUMA_CAND_1",
        "question": "Will SpaceX launch Starship Flight 10 by October 15, 2026?",
        "description": "Must launch by October 15, 2026, 11:59 PM UTC according to spacex.com. If delayed or postponed, resolves 50-50.",
        "endDate": "2026-10-15T23:59:59Z",
        "end_epoch_ts": now_ts - 7200.0,  # Slipped 2h ago!
        "yes_price": 0.98,
        "no_price": 0.02,
        "clobTokenIds": ["TOK_STAR_Y", "TOK_STAR_N"],
    }]

    scanner = UmaNaResolutionScanner(near_expiry_window_hours=48.0)
    flagged = scanner.scan_active_markets(markets, current_ts=now_ts)

    assert len(flagged) == 1
    cand = flagged[0]
    assert cand.candidate_flagged is True
    assert cand.underdog_side == "NO"
    assert cand.underdog_price == 0.02
    # Payoff on $0.02 underdog shares upon N/A ($0.50) resolution:
    # 0.50 / 0.02 = 25.0x payoff!
    assert cand.potential_na_payoff_multiplier == 25.0
    assert cand.shadow_trade_recommended is True


def test_s2_uma_dvm_dispute_nuisance_detection():
    """Verify detection of underwater nuisance disputers and shadow buy on discounted winners."""
    scanner = UmaNaResolutionScanner()

    # Disputer holds 25,000 NO shares (underwater losing side)
    ctf_holdings = {
        "0xdisputer_address": {
            "NO": 25000.0,
            "YES": 50.0,
        }
    }
    # Market mid price discounted to $0.80 during dispute panic
    market_prices = {"0xCOND_DISPUTED": 0.80}

    dispute_logs = [{
        "disputeId": "disp_001",
        "conditionId": "0xCOND_DISPUTED",
        "question": "Will Donald Trump be inaugurated on Jan 20, 2025?",
        "bondAmountUsd": 5000.0,
        "disputerAddress": "0xdisputer_address",
        "proposedWinner": "YES",
    }]

    events = scanner.monitor_uma_disputes(
        dispute_logs=dispute_logs,
        ctf_holdings_db=ctf_holdings,
        market_mid_prices=market_prices,
    )

    assert len(events) == 1
    ev = events[0]
    assert ev.is_nuisance_disputer is True
    assert "UNDERWATER_LOSING_INVENTORY" in ev.nuisance_reason
    assert ev.shadow_buy_recommended is True
    assert ev.discounted_share_price == 0.80
    # Convergence edge to $1.00: (1.00 - 0.80) / 0.80 * 10,000 = +2500 bps!
    assert ev.expected_convergence_profit_bps == 2500.0
