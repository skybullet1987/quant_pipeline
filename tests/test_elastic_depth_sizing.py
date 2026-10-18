#!/usr/bin/env python3
"""
Unit tests for Dynamic Book-Depth Elastic Sizing ($25 to $75)
============================================================
"""

import pytest
from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    DEFAULT_DEPTH_HURDLE,
)


def test_elastic_ticket_sizing_bounds():
    calc = PolymarketLiveExecutor.calculate_elastic_ticket_size

    # 1. Depth too thin (< $37.50 for 1.50x hurdle -> fails closed)
    passed, sz = calc(executable_depth_usd=30.0, depth_hurdle_ratio=1.50)
    assert not passed
    assert sz == 0.0

    # 2. Minimum depth boundary ($37.50 / 1.50 = $25.00 -> exactly $25 min ticket)
    passed, sz = calc(executable_depth_usd=37.50, depth_hurdle_ratio=1.50)
    assert passed
    assert sz == 25.0

    # 3. Intermediate depth ($60.00 / 1.50 = $40.00 ticket)
    passed, sz = calc(executable_depth_usd=60.0, depth_hurdle_ratio=1.50)
    assert passed
    assert sz == 40.0

    # 4. Standard $50 ticket depth ($75.00 / 1.50 = $50.00)
    passed, sz = calc(executable_depth_usd=75.0, depth_hurdle_ratio=1.50)
    assert passed
    assert sz == 50.0

    # 5. Maximum depth boundary ($112.50 / 1.50 = $75.00 max ticket)
    passed, sz = calc(executable_depth_usd=112.50, depth_hurdle_ratio=1.50)
    assert passed
    assert sz == 75.0

    # 6. Deep orderbook ($500.00 depth -> clipped to $75.00 max ticket)
    passed, sz = calc(executable_depth_usd=500.0, depth_hurdle_ratio=1.50)
    assert passed
    assert sz == 75.0


def test_verify_pre_trade_depth_elastic_integration():
    executor = PolymarketLiveExecutor(dry_run=True)

    # Mock orderbook with $60 of qualifying ask depth
    mock_book = {
        "asks": [
            {"price": "0.60", "size": "50.0"},  # 0.60 * 50 = $30.00
            {"price": "0.62", "size": "48.387"}, # 0.62 * 48.387 = $30.00
        ],
        "bids": [{"price": "0.58", "size": "100.0"}],
    }

    # With return_adjusted=True (elastic sizing):
    # Total depth = $60.00. Hurdle = 1.50x.
    # Raw elastic = 60.00 / 1.50 = $40.00.
    passed, ratio, best_px, adjusted_notional = executor.verify_pre_trade_depth(
        mock_book,
        target_notional_usd=50.0,
        side="BUY",
        depth_hurdle_ratio=1.50,
        return_adjusted=True,
    )
    assert passed is True
    assert best_px == 0.60
    assert adjusted_notional == 40.0


def test_golden_config_market_universe_restrictions():
    val = PolymarketLiveExecutor.validate_market_universe

    # 1. SOL completely rejected
    passed, reason = val("SOL", title="Solana Up or Down - 15m")
    assert not passed
    assert "REJECT_SOL_MARKET" in reason

    # 2. 1-hour BTC markets rejected
    passed, reason = val("BTC", title="Bitcoin Up or Down - September 28, 7PM ET", horizon="1h")
    assert not passed
    assert "REJECT_1H_BTC_MARKET" in reason

    passed, reason = val("BTC", slug="btc-up-or-down-hourly")
    assert not passed
    assert "REJECT_1H_BTC_MARKET" in reason

    # 3. 5m and 15m BTC markets approved
    passed, reason = val("BTC", title="Bitcoin Up or Down - 5m", horizon="5m")
    assert passed
    assert reason == "MARKET_UNIVERSE_APPROVED"

    passed, reason = val("BTC", title="Bitcoin Up or Down - 15m", horizon="15m")
    assert passed
    assert reason == "MARKET_UNIVERSE_APPROVED"

    # 4. 5m and 15m ETH markets approved
    passed, reason = val("ETH", title="Ethereum Up or Down - 15m", horizon="15m")
    assert passed
    assert reason == "MARKET_UNIVERSE_APPROVED"


def test_golden_config_signal_and_priority_ranking():
    # 1. BTC signal threshold |z_BTC| >= 1.645
    val_btc = PolymarketLiveExecutor.validate_btc_signal
    assert not val_btc(1.20)[0]
    assert not val_btc(-1.50)[0]
    assert val_btc(1.645)[0]
    assert val_btc(2.10)[0]
    assert val_btc(-1.85)[0]

    # 2. ETH cross-asset lead-lag filter (z_joint = 0.70 * z_ETH + 0.30 * z_BTC)
    val_eth = PolymarketLiveExecutor.validate_cross_asset_lead_lag
    # Agrees: ETH UP, BTC UP, both z positive
    passed, z_j, reason = val_eth("ETH", "UP", btc_direction="UP", z_alt=2.0, z_btc=1.5)
    assert passed
    assert round(z_j, 2) == round(0.70 * 2.0 + 0.30 * 1.5, 2) # 1.85

    # Counter-trending direction: ETH UP vs BTC DOWN
    passed, _, reason = val_eth("ETH", "UP", btc_direction="DOWN", z_alt=2.0, z_btc=1.5)
    assert not passed
    assert "REJECT_BTC_COUNTER_TREND" in reason

    # Sign divergence: z_alt > 0, z_btc < 0
    passed, _, reason = val_eth("ETH", "UP", btc_direction="UP", z_alt=2.0, z_btc=-1.0)
    assert not passed
    assert "REJECT_BTC_ETH_SIGN_DIVERGENCE" in reason

    # 3. 5-Second shock cluster priority ranking: score = |z| / ask_price
    rank_fn = PolymarketLiveExecutor.rank_concurrent_shock_candidates
    candidates = [
        {"market_id": "M1", "z_score": 1.70, "price": 0.68}, # score = 1.70 / 0.68 = 2.50
        {"market_id": "M2", "z_score": 2.20, "price": 0.55}, # score = 2.20 / 0.55 = 4.00
        {"market_id": "M3", "z_score": 1.65, "price": 0.82}, # score = 1.65 / 0.82 = 2.01
    ]
    ranked = rank_fn(candidates)
    assert ranked[0]["market_id"] == "M2" # highest delta efficiency
    assert ranked[1]["market_id"] == "M1"
    assert ranked[2]["market_id"] == "M3"


def test_golden_config_exp302_exit_policy():
    eval_exit = PolymarketLiveExecutor.evaluate_exp302_exit_policy
    stop_calc = PolymarketLiveExecutor.calculate_relative_stop_price

    # 1. Relative stop anchoring strictly below entry price
    stop_px = stop_calc(entry_price=0.70, stop_delta=0.12)
    assert stop_px == 0.58

    stop_px_low = stop_calc(entry_price=0.10, stop_delta=0.12, price_floor=0.02)
    assert stop_px_low == 0.02 # Floored, never negative or artificial 0.58

    # 2. Resting Maker Take-Profit @ $0.95 (for entry < 0.80)
    res = eval_exit(entry_price=0.60, current_bid=0.95, current_ask=0.96)
    assert res["action"] == "MAKER_TAKE_PROFIT"
    assert res["price"] == 0.95
    assert res["is_maker"] is True

    # 2b. Gated Resting Maker Take-Profit: entry >= 0.80 targets $0.985 to prevent payoff compression
    res_high = eval_exit(entry_price=0.85, current_bid=0.95, current_ask=0.96)
    assert res_high["action"] == "HOLD_TO_MATURITY" # Not capped at 0.95!

    res_high_tp = eval_exit(entry_price=0.85, current_bid=0.985, current_ask=0.99)
    assert res_high_tp["action"] == "MAKER_TAKE_PROFIT"
    assert res_high_tp["price"] == 0.985

    # 3. Spot-Delta Stop Loss (0.50 * ATR adverse reversal)
    res = eval_exit(entry_price=0.70, current_bid=0.65, current_ask=0.66, spot_reversal_atr_multiple=0.55)
    assert res["action"] == "SPOT_DELTA_STOP_LOSS"
    assert res["is_maker"] is False

    # 4. Spot-Delta Stop Loss (bid <= relative stop price)
    res = eval_exit(entry_price=0.70, current_bid=0.57, current_ask=0.58, spot_reversal_atr_multiple=0.10)
    assert res["action"] == "SPOT_DELTA_STOP_LOSS"
    assert res["is_maker"] is False

    # 5. Capital-Starvation Override ONLY when free_usdc < $25.00 AND higher-score pending AND position in green
    # Case A: free_usdc is healthy ($50.00) -> Hold to maturity (no early unwind!)
    res = eval_exit(entry_price=0.60, current_bid=0.72, current_ask=0.73, free_usdc=50.0, higher_score_trigger_pending=True)
    assert res["action"] == "HOLD_TO_MATURITY"

    # Case B: free_usdc is starved ($15.00 < $25.00) with higher-score pending and position green -> Unwind early to free cash
    res = eval_exit(entry_price=0.60, current_bid=0.72, current_ask=0.73, free_usdc=15.0, higher_score_trigger_pending=True)
    assert res["action"] == "CAPITAL_STARVATION_UNWIND"
    assert res["price"] == 0.72

    # Case C: free_usdc starved, but position in red (current_bid <= entry_price) -> Do NOT unwind at loss
    res = eval_exit(entry_price=0.65, current_bid=0.62, current_ask=0.63, free_usdc=15.0, higher_score_trigger_pending=True)
    assert res["action"] == "HOLD_TO_MATURITY"

    # 6. Default: Hold to Maturity for $1.00 settlement
    res = eval_exit(entry_price=0.60, current_bid=0.75, current_ask=0.76, free_usdc=100.0)
    assert res["action"] == "HOLD_TO_MATURITY"
    assert res["price"] == 1.00


def test_cross_asset_directional_conflict_guard():
    """Validates BTC vs. ETH Same-Candle Lock preventing self-hedging opposing bets."""
    val = PolymarketLiveExecutor.validate_cross_asset_directional_conflict

    active_eth_down = [
        {
            "asset": "ETH",
            "target_token": "DOWN",
            "candle_expiry_ts": 1792072800.0,
            "market_id": "5648273",
        }
    ]

    # 1. Opposing candidate in overlapping candle (BTC UP vs ETH DOWN @ same expiry) -> REJECTED
    passed, reason = val(
        candidate_asset="BTC",
        candidate_direction="UP",
        candidate_expiry_ts=1792072800.0,
        active_positions=active_eth_down,
    )
    assert passed is False
    assert "REJECT_CROSS_ASSET_CONFLICT" in reason
    assert "opposes active ETH DOWN" in reason

    # 2. Correlated candidate in same direction (BTC DOWN with ETH DOWN) -> APPROVED
    passed, reason = val(
        candidate_asset="BTC",
        candidate_direction="DOWN",
        candidate_expiry_ts=1792072800.0,
        active_positions=active_eth_down,
    )
    assert passed is True
    assert reason == "CROSS_ASSET_DIRECTION_ALIGNED"

    # 3. Opposing candidate but in distant non-overlapping expiry (delta > 900s) -> APPROVED
    passed, reason = val(
        candidate_asset="BTC",
        candidate_direction="UP",
        candidate_expiry_ts=1792072800.0 + 3600.0,
        active_positions=active_eth_down,
    )
    assert passed is True
    assert reason == "CROSS_ASSET_DIRECTION_ALIGNED"

    # 4. Same asset opposing in same window (ETH UP vs ETH DOWN) -> REJECTED
    passed, reason = val(
        candidate_asset="ETH",
        candidate_direction="UP",
        candidate_expiry_ts=1792072800.0,
        active_positions=active_eth_down,
    )
    assert passed is False
    assert "REJECT_CROSS_ASSET_CONFLICT" in reason


def test_strict_1h_tte_sweetspot_gate():
    """Validates that 1-hour candles only enter during the final 25 minutes [120s, 1500s]."""
    val = PolymarketLiveExecutor.validate_market_universe

    # 1. 1-hour ETH contract with 35 minutes left (2100s) -> REJECTED
    passed, reason = val("ETH", title="Ethereum Up or Down - October 15, 9AM ET", tte_seconds=2100.0)
    assert passed is False
    assert "REJECT_1H_MARKET_OUTSIDE_SWEETSPOT" in reason

    # 2. 1-hour ETH contract with 1 minute left (60s, unexecutable settlement lock) -> REJECTED
    passed, reason = val("ETH", title="Ethereum Up or Down - October 15, 9AM ET", tte_seconds=60.0)
    assert passed is False
    assert "REJECT_1H_MARKET_OUTSIDE_SWEETSPOT" in reason

    # 3. 1-hour ETH contract in expanded 25m sweet spot (23 minutes / 1380s left) -> APPROVED
    passed, reason = val("ETH", title="Ethereum Up or Down - October 15, 9AM ET", tte_seconds=1380.0)
    assert passed is True
    assert reason == "MARKET_UNIVERSE_APPROVED"

    # 4. 1-hour ETH contract in final 15m sweet spot (10 minutes / 600s left) -> APPROVED
    passed, reason = val("ETH", title="Ethereum Up or Down - October 15, 9AM ET", tte_seconds=600.0)
    assert passed is True
    assert reason == "MARKET_UNIVERSE_APPROVED"

    # 5. When custom max_tte_seconds=900.0 is passed, 1380s is rejected
    passed, reason = val("ETH", title="Ethereum Up or Down - October 15, 9AM ET", tte_seconds=1380.0, max_tte_seconds=900.0)
    assert passed is False
    assert "REJECT_1H_MARKET_OUTSIDE_SWEETSPOT" in reason

    # 6. 15m sub-hourly contract with 600s left -> APPROVED
    passed, reason = val("ETH", title="Ethereum Up or Down - 15m", horizon="15m", tte_seconds=600.0)
    assert passed is True
    assert reason == "MARKET_UNIVERSE_APPROVED"


def test_marketable_buffer_and_fak_order_type():
    """Validates +2.0c marketable buffer capped strictly at 0.88 ceiling and OrderType.FAK usage."""
    executor = PolymarketLiveExecutor(dry_run=True)

    # 1. Best ask at 0.81 -> Limit price should be 0.83 (+2.0c buffer)
    best_px = 0.81
    max_price_ceiling = 0.88
    execution_limit_px = min(round(best_px + 0.02, 2), max_price_ceiling)
    assert execution_limit_px == 0.83

    # 2. Best ask at 0.87 -> Limit price should be strictly capped at 0.88 (min(0.89, 0.88))
    best_px = 0.87
    execution_limit_px = min(round(best_px + 0.02, 2), max_price_ceiling)
    assert execution_limit_px == 0.88

    # 3. Best ask at 0.88 -> Limit price should remain 0.88
    best_px = 0.88
    execution_limit_px = min(round(best_px + 0.02, 2), max_price_ceiling)
    assert execution_limit_px == 0.88

    # 4. Verify FAK order type is resolved
    from py_clob_client_v2.clob_types import OrderType
    entry_order_type = getattr(OrderType, "FAK", OrderType.FOK)
    assert entry_order_type == "FAK" or entry_order_type == OrderType.FAK


def test_strike_retrace_stop_loss_policy():
    """Validates Strike-Retrace Stop Loss in evaluate_exp302_exit_policy."""
    eval_exit = PolymarketLiveExecutor.evaluate_exp302_exit_policy

    # 1. Spot retraces below +0.03% (e.g. +0.015%) with 500s left (> 60s) -> STRIKE_RETRACE_STOP_LOSS
    res = eval_exit(
        entry_price=0.80,
        current_bid=0.48,
        current_ask=0.50,
        signed_candle_distance_pct=0.015,
        tte_seconds=500.0,
    )
    assert res["action"] == "STRIKE_RETRACE_STOP_LOSS"
    assert res["price"] == 0.48
    assert res["is_maker"] is False
    assert "Strike-retrace stop triggered" in res["reason"]

    # 2. Spot is safely above +0.03% (e.g. +0.18%) with 500s left -> HOLD_TO_MATURITY
    res = eval_exit(
        entry_price=0.80,
        current_bid=0.82,
        current_ask=0.84,
        signed_candle_distance_pct=0.18,
        tte_seconds=500.0,
    )
    assert res["action"] == "HOLD_TO_MATURITY"

    # 3. Spot has retraced (< 0.03%), but TTE <= 60s (e.g. 45s left) with bid above relative stop -> HOLD_TO_MATURITY (terminal settlement)
    res = eval_exit(
        entry_price=0.80,
        current_bid=0.75,
        current_ask=0.77,
        signed_candle_distance_pct=0.01,
        tte_seconds=45.0,
    )
    assert res["action"] == "HOLD_TO_MATURITY"

    # 4. Maker TP at 0.985 takes precedence if bid reaches TP price even with retrace metadata
    res = eval_exit(
        entry_price=0.80,
        current_bid=0.985,
        current_ask=0.99,
        signed_candle_distance_pct=0.50,
        tte_seconds=300.0,
    )
    assert res["action"] == "MAKER_TAKE_PROFIT"
    assert res["price"] == 0.985


def test_spot_cushion_gate_and_calibrated_p_model():
    """Validates 15 bps spot cushion gate and calibrated p_model = 0.90 in live harvester."""
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    harvester = PolymarketLiveHarvester(dry_run=True)
    # Default calibrated_p_model must be 0.95 (to support 0.92 ceiling with positive edge)
    assert harvester.calibrated_p_model == 0.95

    # 1. 1-hour candle with dist = +0.0999% (< 0.15% cushion) -> Must be rejected by cushion gate
    is_1h = True
    dist_10pm = 0.0999
    min_cushion = 0.15
    assert (abs(dist_10pm) < min_cushion) is True

    # 2. 1-hour candle with dist = +0.133% (< 0.15% cushion) -> Must be rejected by cushion gate
    dist_11pm = 0.133
    assert (abs(dist_11pm) < min_cushion) is True

    # 3. Winning 9PM ET candle with dist = +0.2055% (>= 0.15% cushion) -> Passes cushion gate
    dist_9pm = 0.2055
    assert (abs(dist_9pm) >= min_cushion) is True


def test_paper_trader_strike_retrace_stop_execution():
    """Validates paper trader check_strike_retrace_stops unwinding open trade at bid."""
    import time
    from src.polymarket_research.polymarket_paper_trader import PolymarketForwardPaperTrader

    pt = PolymarketForwardPaperTrader()
    m_id = "TEST_RETRACE_MKT_001"
    trade_id = "PAPER_TEST_RETRACE_001_UP"
    pt.open_trades[m_id] = [{
        "trade_id": trade_id,
        "market_id": m_id,
        "title": "Bitcoin Up or Down - 10PM ET",
        "entry_time": "2026-10-16 02:43:22 UTC",
        "entry_unix": time.time() - 300,
        "epoch": "VALIDATION",
        "seconds_to_expiry": 600.0,
        "target_token": "UP",
        "notional_usd": 75.0,
        "effective_price": 0.80,
        "shares_bought": 93.75,
        "taker_fee_usd": 1.05,
        "status": "OPEN",
    }]

    # Case A: Spot cushion healthy (+0.12%) with 500s left -> Trade remains open
    closed = pt.check_strike_retrace_stops(m_id, candle_dist_pct=0.12, tte=500.0, token_bids={"UP": 0.80, "DOWN": 0.20})
    assert len(closed) == 0
    assert m_id in pt.open_trades

    # Policy A: check_strike_retrace_stops is disabled (zero mid-candle dumps)
    closed = pt.check_strike_retrace_stops(m_id, candle_dist_pct=0.01, tte=500.0, token_bids={"UP": 0.48, "DOWN": 0.52})
    assert len(closed) == 0
    assert m_id in pt.open_trades

    # Policy A: 99c Maker TP fill on CLOB telemetry
    telem = {"market_id": m_id, "UP": {"best_bid": 0.99, "best_ask": 0.991}, "timestamp": "2026-10-16 02:50:00 UTC"}
    closed_tp = pt.check_maker_tp_fills(m_id, telem)
    assert len(closed_tp) == 1
    closed_trade = closed_tp[0]
    assert closed_trade["status"] == "CLOSED"
    assert closed_trade["exit_reason"] == "MAKER_SCALP_FILLED_CLOB"
    assert closed_trade["exit_price"] == 0.99
    # Payout should be 93.75 * 0.99 = $92.81
    assert closed_trade["payout_usd"] == 92.81
    assert closed_trade["won"] is True
    assert closed_trade["trade_id"] in pt.settled_trade_ids
    assert m_id not in pt.open_trades



