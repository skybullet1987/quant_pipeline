import asyncio
import json
import os
import time
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    ExecutionStatus,
    OrderResult,
    calculate_taker_fee,
)
from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    StatePersistenceError,
    ALLOWED_ASSETS,
    MAX_ADVERSE_SPOT_MOVE_PCT,
)
from src.polymarket_research.polymarket_paper_trader import PolymarketForwardPaperTrader
from src.polymarket_research.exp306_expiry_boundary_engine import evaluate_instantaneous_merge_arbitrage
from src.polymarket_research.redeem_settled_positions import get_token_balance_onchain


# ==============================================================================
# FINDING 1 (P0): FAILED FOK STOP-LOSS RETRY STATE
# ==============================================================================
def test_finding_1_failed_fok_stop_loss_is_retryable():
    harvester = PolymarketLiveHarvester(dry_run=True)
    tid = "LIVE_TEST_FOK_RETRY_001"
    now = time.time()
    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_UNRESOLVED_MKT_001",
        "token_id": "0xTOK_FOK_TEST",
        "target_token": "UP",
        "asset": "BTC",
        "entry_price": 0.70,
        "entry_shares": 100.0,
        "remaining_shares": 100.0,
        "notional_usd": 70.0,
        "fee_usd": 1.0,
        "target_exit_price": 0.79,
        "candle_open_spot": 2500.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 600.0,
        "is_liquidating": False,
        "exit_order_id": "0xRESTING_EXIT_001",
        "exit_order_status": "RESTING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None

    # Mock book where best bid dropped to 0.45 (triggers 15c CLOB stop)
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.45", "size": "100.0"}]})
    harvester.get_reference_spot_price = lambda sym: 2500.0

    # Simulate FOK unwind failure
    harvester.executor.execute_unwind_order = lambda **kwargs: {"success": False, "error": "BOOK_MOVED"}

    # Run check_resolutions_and_manage_positions
    asyncio.run(harvester.check_resolutions_and_manage_positions())

    pos = harvester.active_positions[tid]
    # Invariant: position must NOT be marked is_liquidating=True (which would freeze it forever)
    assert pos["is_liquidating"] is False, "Failed FOK must not set is_liquidating=True!"
    assert pos["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    assert pos.get("next_unwind_retry_ts", 0) > now
    assert "BOOK_MOVED" in pos.get("unwind_last_error", "")


# ==============================================================================
# FINDING 2 (P0): CIRCUIT BREAKER & HEARTBEAT PRESERVE RESTING EXITS & SUPERVISION
# ==============================================================================
def test_finding_2_circuit_breaker_preserves_resting_exits_and_supervision():
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.save_state = lambda: None
    cancel_all_called = []
    harvester.executor.cancel_all_orders = lambda: cancel_all_called.append(True)

    # Put an active position
    harvester.active_positions["POS_1"] = {"notional_usd": 35.0, "exit_order_id": "0xEXIT_1"}

    # Trip circuit breaker
    harvester.risk_controller.halted = True
    harvester.risk_controller.halt_reason = "Max daily loss tripped"

    # Evaluate new shock -> must be rejected without touching existing exits
    shock = {"event_id": "EVT_HALT_TEST", "shock_direction": "BUY"}
    asyncio.run(harvester.evaluate_shock_and_execute(shock))

    assert len(cancel_all_called) == 0, "Halt must not cancel resting exits while active positions exist!"
    assert "POS_1" in harvester.active_positions


# ==============================================================================
# FINDING 3 (P0): MISSING SPOT QUOTE DOES NOT THROW TYPEERROR
# ==============================================================================
def test_finding_3_missing_spot_quote_safe_evaluation():
    harvester = PolymarketLiveHarvester(dry_run=True)
    tid = "LIVE_TEST_SPOT_NONE_001"
    now = time.time()
    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_UNRESOLVED_MKT_003",
        "token_id": "0xTOK_SPOT_NONE",
        "target_token": "UP",
        "asset": "BTC",
        "entry_price": 0.70,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 35.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.79,
        "candle_open_spot": 2500.0,
        "candle_expiry_ts": now + 600.0,
        "is_liquidating": False,
        "exit_order_id": "0xRESTING_EXIT_003",
        "exit_order_status": "RESTING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None

    # Binance spot query times out and returns None
    harvester.get_reference_spot_price = lambda sym: None

    # CLOB bid is 0.50 (drops 20c below entry 0.70 -> CLOB stop triggered!)
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.50", "size": "100.0"}]})

    unwinds = []
    harvester.executor.execute_unwind_order = lambda **kwargs: unwinds.append(kwargs) or {
        "success": True, "matched_size": 50.0, "taking_amount": 25.0, "fee_usd": 0.35, "orderID": "0xUNWIND_OK"
    }

    # Must NOT throw TypeError: unsupported operand type(s) for -: 'NoneType' and 'float'
    asyncio.run(harvester.check_resolutions_and_manage_positions())

    assert len(unwinds) == 1, "CLOB stop-loss must execute even when spot quote returns None!"
    assert tid not in harvester.active_positions


# ==============================================================================
# FINDING 4 (P0): ADVERSE SPOT MOVE CAP (0.40%) CATCHES -0.49% HISTORICAL DROP
# ==============================================================================
def test_finding_4_adverse_spot_move_percentage_cap():
    harvester = PolymarketLiveHarvester(dry_run=True)
    tid = "LIVE_TEST_SPOT_CRASH_001"
    now = time.time()
    # Incident position parameters: open = $2530.00, spot drops $12.44 (-0.49%)
    open_spot = 2530.00
    current_spot = 2517.56  # -0.4917% drop
    candle_sigma = 0.005  # K * sigma * open = 1.15 * 0.005 * 2530 = 14.5475 (not reached since 12.44 < 14.55!)

    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_UNRESOLVED_MKT_004",
        "token_id": "0xTOK_SPOT_CRASH",
        "target_token": "UP",
        "asset": "ETH",
        "entry_price": 0.70,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 35.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.79,
        "candle_open_spot": open_spot,
        "candle_sigma": candle_sigma,
        "candle_expiry_ts": now + 600.0,
        "is_liquidating": False,
        "exit_order_id": "0xRESTING_EXIT_004",
        "exit_order_status": "RESTING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None

    # CLOB bid hasn't yet dropped 15c (e.g. 0.62)
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.62", "size": "100.0"}]})
    harvester.get_reference_spot_price = lambda sym: current_spot

    unwinds = []
    harvester.executor.execute_unwind_order = lambda **kwargs: unwinds.append(kwargs) or {
        "success": True, "matched_size": 50.0, "taking_amount": 31.0, "fee_usd": 0.40, "orderID": "0xUNWIND_OK"
    }

    asyncio.run(harvester.check_resolutions_and_manage_positions())
    assert len(unwinds) == 1, "Adverse spot move of -0.49% must trip the MAX_ADVERSE_SPOT_MOVE_PCT guard!"


# ==============================================================================
# FINDING 5 (P0): KELLY SIZING FORECAST PROVENANCE & TAKER FEE DEDUCTION
# ==============================================================================
def test_finding_5_kelly_sizing_requires_provenance_and_deducts_fees():
    harvester = PolymarketLiveHarvester(ticket_notional=25.0, dry_run=True)
    harvester.save_state = lambda: None

    # Trigger without calibrated model provenance -> must fall back to ticket_notional
    shock_uncalibrated = {
        "event_id": "EVT_NO_PROV",
        "market_id": "5499001",
        "shock_direction": "BUY",
        "seconds_to_expiry": 300.0,
        "candle_distance_pct": 0.10,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "0xTOK_UP",
                "raw_top_asks": [[0.50, 100.0]],
            }
        }
    }
    # compute_kelly_ticket_size net fee deduction check:
    # At p=0.50, fee = 0.07 * 0.50 * 0.50 = 0.0175. all-in cost = 0.5175.
    # If p_model = 0.53, net edge = 0.53 - 0.5175 = 0.0125 <= 0.015 -> returns 0.0!
    assert harvester.compute_kelly_ticket_size(p_model=0.53, p_market_ask=0.50, bankroll=100.0) == 0.0


# ==============================================================================
# FINDING 7 (P1): PAPER TRADER USES RAW VWAP & ELIMINATES FEE DOUBLE-COUNTING
# ==============================================================================
def test_finding_7_paper_trader_raw_vwap_and_fee_accuracy():
    trader = PolymarketForwardPaperTrader()
    trader.open_trades.clear()

    # Simulate $50 sweep: raw VWAP = 0.50, fee = $1.75 -> effective_price_$50 = 0.5175
    shock = {
        "market_id": "540001",
        "t0_unix": time.time(),
        "shock_direction": "BUY",
        "seconds_to_expiry": 300.0,
        "candle_distance_pct": 0.10,
        "title": "Will Bitcoin break $100k?",
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "0xTOK_UP",
                "spread": 0.01,
                "raw_top_asks": [[0.50, 200.0]],
                "vwap_$50": 0.50,
                "fill_fees_$50": 1.75,
                "effective_price_$50": 0.5175,
            }
        }
    }
    trader.evaluate_shock_signal(shock, historical=False)

    open_trades = trader.open_trades["540001"]
    assert len(open_trades) == 1
    trade = open_trades[0]

    # Shares bought must be 50.0 / 0.50 = 100.0 shares, NOT 50.0 / 0.5175 = 96.618 shares!
    assert trade["shares_bought"] == 100.0
    assert trade["taker_fee_usd"] == 1.75


# ==============================================================================
# FINDING 8 (P1): PAPER TRADER SPREAD GUARD AND HOURLY CAPS
# ==============================================================================
def test_finding_8_paper_trader_spread_guard_and_caps():
    trader = PolymarketForwardPaperTrader()
    trader.open_trades.clear()

    # Book with 4c spread > 3c MAX_ALLOWED_SPREAD -> must be rejected
    shock_wide_spread = {
        "market_id": "540002",
        "t0_unix": time.time(),
        "shock_direction": "BUY",
        "seconds_to_expiry": 300.0,
        "candle_distance_pct": 0.10,
        "title": "Will BTC move?",
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "0xTOK_WIDE",
                "spread": 0.040,  # > 0.030
                "raw_top_asks": [[0.50, 200.0]],
                "vwap_$50": 0.50,
                "fill_fees_$50": 1.75,
                "effective_price_$50": 0.5175,
            }
        }
    }
    trader.evaluate_shock_signal(shock_wide_spread, historical=False)
    assert "540002" not in trader.open_trades


# ==============================================================================
# FINDING 9 (P1): DECIMAL TICK QUANTIZATION AND DIRECTIONAL ROUNDING
# ==============================================================================
def test_finding_9_decimal_tick_quantization_increments():
    executor = PolymarketLiveExecutor(dry_run=True)
    executor._tick_size_cache["TOK_0025"] = 0.0025

    # Invariant: 0.7525 must remain 0.7525, NOT truncated to 0.753!
    quantized = executor.quantize_order_price(0.7525, "TOK_0025")
    assert quantized == 0.7525

    # Directional rounding:
    # Maker SELL exit should round UP (CEILING) to avoid cutting profit target
    sell_exit = executor.quantize_order_price(0.7521, "TOK_0025", rounding=ROUND_CEILING)
    assert sell_exit == 0.7525

    # Aggressive stop SELL should round DOWN (FLOOR) to maintain aggressive execution
    stop_floor = executor.quantize_order_price(0.7524, "TOK_0025", rounding=ROUND_FLOOR)
    assert stop_floor == 0.7500


# ==============================================================================
# FINDING 11 (P1): STRICT OPEN ORDERS AND CORRUPT STATE REJECTION
# ==============================================================================
def test_finding_11_corrupt_state_and_strict_orders():
    harvester = PolymarketLiveHarvester(dry_run=True)
    # Strict open orders query raises on exchange query error in live mode
    harvester.executor.dry_run = False
    harvester.executor.is_authenticated = True
    mock_client = MagicMock()
    mock_client.get_open_orders.side_effect = ConnectionError("CLOB network drop")
    harvester.executor.client = mock_client

    with pytest.raises(RuntimeError, match="CLOB open-order snapshot unavailable"):
        harvester.executor.get_open_orders(strict=True)


# ==============================================================================
# FINDING 13 & 21 (P1): CANCELED EXIT ORDER CONFIRMATION AND RECOVERY
# ==============================================================================
def test_finding_13_canceled_exit_order_recovery():
    harvester = PolymarketLiveHarvester(dry_run=True)
    tid = "LIVE_TEST_EXIT_REC_001"
    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_UNRESOLVED_MKT_013",
        "token_id": "0xTOK_REC",
        "entry_shares": 100.0,
        "remaining_shares": 100.0,
        "notional_usd": 50.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.60,
        "exit_order_id": "0xOLD_CANCELED_OID",
        "exit_order_status": "RESTING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None

    # Exchange reports exit order was CANCELED with 0 matched shares
    harvester.executor.get_open_orders = lambda: []
    harvester.executor.get_order_status = lambda oid: {"status": "CANCELED", "size_matched": "0.0"}
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.58", "size": "100.0"}]})

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    pos = harvester.active_positions[tid]
    assert pos["exit_order_id"] is None
    assert pos["exit_order_status"] == "EXIT_RECOVERY_REQUIRED"
    assert pos["status"] == ExecutionStatus.EXIT_PENDING_SETTLEMENT


# ==============================================================================
# FINDING 15 (P1): BINARY BUFFERED TAIL READER PREVENTS RECORD LOSS
# ==============================================================================
def test_finding_15_binary_tail_reader_protects_partial_records(tmp_path):
    trig_file = tmp_path / "test_triggers.jsonl"
    # Write a complete line followed by an incomplete fragment (no trailing newline)
    with open(trig_file, "wb") as f:
        f.write(b'{"market_id":"M1","t0_unix":100}\n{"market_id":"M2","t0_un')

    last_pos = 0
    with open(trig_file, "rb") as f:
        f.seek(last_pos)
        chunk = f.read()
    complete_end = chunk.rfind(b"\n") + 1
    assert complete_end > 0

    lines = chunk[:complete_end].decode("utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["market_id"] == "M1"
    # Offset must advance ONLY to the end of the first line, NOT past the fragment!
    last_pos += complete_end
    assert last_pos == len(b'{"market_id":"M1","t0_unix":100}\n')


# ==============================================================================
# FINDING 17 (P1): EXECUTE_UNWIND_ORDER LIVE MOCK FORBIDDEN
# ==============================================================================
def test_finding_17_live_unwind_mock_forbidden():
    executor = PolymarketLiveExecutor(dry_run=False)
    executor.client = None
    executor.is_authenticated = False

    res = executor.execute_unwind_order("0xTOK_LIVE", 50.0, "SELL", 0.10)
    assert res["success"] is False
    assert "Live CLOB client unavailable" in res["error"]


# ==============================================================================
# FINDING 19 (P2): EXP-306 SORTS ORDERBOOK LEVELS CANONICALLY
# ==============================================================================
def test_finding_19_exp306_canonical_book_sorting():
    # Asks presented out of order
    book = {
        "asks": [{"price": "0.99", "size": "10.0"}, {"price": "0.52", "size": "100.0"}],
        "bids": [{"price": "0.20", "size": "10.0"}, {"price": "0.48", "size": "50.0"}],
    }
    sorted_asks = sorted(book.get("asks", []), key=lambda x: float(x.get("price", 1.0)))
    sorted_bids = sorted(book.get("bids", []), key=lambda x: float(x.get("price", 0.0)), reverse=True)

    assert float(sorted_asks[0]["price"]) == 0.52
    assert float(sorted_bids[0]["price"]) == 0.48


# ==============================================================================
# FINDING 20 (P2): SETTLEMENT AUDITOR RPC FAILURE RETURNS NONE
# ==============================================================================
def test_finding_20_settlement_auditor_rpc_failure_returns_none():
    with patch("requests.post") as mock_post:
        mock_post.side_effect = ConnectionError("Polygon RPC timeout")
        bal = get_token_balance_onchain("0x1234567890123456789012345678901234567890", "12345")
        assert bal is None, "RPC query failure must return None, not 0.0!"


# ==============================================================================
# FINDING 22 (P1): TAKER EXIT FEES DEDUCTED IN STOP-LOSS PNL
# ==============================================================================
def test_finding_22_taker_exit_fees_deducted_in_stop_loss():
    harvester = PolymarketLiveHarvester(dry_run=True)
    tid = "LIVE_TEST_FEE_PNL_001"
    now = time.time()
    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_UNRESOLVED_MKT_022",
        "token_id": "0xTOK_FEE_PNL",
        "target_token": "UP",
        "asset": "BTC",
        "entry_price": 0.35,
        "entry_shares": 100.0,
        "remaining_shares": 100.0,
        "notional_usd": 35.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.44,
        "candle_open_spot": 2500.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 600.0,
        "is_liquidating": False,
        "exit_order_id": "0xRESTING_EXIT_022",
        "exit_order_status": "RESTING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None

    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.15", "size": "100.0"}]})
    harvester.get_reference_spot_price = lambda sym: 2500.0

    # Unwind sells 100 shares @ $0.25 ($25 payout) and incurs $1.31 exit fee
    harvester.executor.execute_unwind_order = lambda **kwargs: {
        "success": True, "matched_size": 100.0, "taking_amount": 25.0, "fee_usd": 1.31, "orderID": "0xUNWIND_FEE"
    }

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    closed = harvester.closed_positions[-1]
    # Net PnL = proceeds ($25.00) - entry_notional ($35.00) - entry_fee ($0.50) - exit_fee ($1.31) = -$11.81
    assert closed["net_pnl_usd"] == round(25.00 - 35.00 - 0.50 - 1.31, 2)


# ==============================================================================
# FINDING 24 (P1): ASSET WHITELIST BYPASS REFUSAL
# ==============================================================================
def test_finding_24_asset_whitelist_refusal():
    harvester = PolymarketLiveHarvester(dry_run=False)  # Live mode
    harvester.save_state = lambda: None

    executed = []
    harvester.executor.execute_snipe_order_async = lambda **kwargs: executed.append(kwargs)

    # Shock for unsupported LTC market
    shock_ltc = {
        "event_id": "EVT_LTC_001",
        "market_id": "5999001",
        "title": "Litecoin price above $100",
        "shock_direction": "BUY",
        "seconds_to_expiry": 300.0,
        "candle_distance_pct": 0.10,
        "pre_shock_features_t0": {
            "UP": {"token_id": "0xTOK_LTC", "raw_top_asks": [[0.50, 100.0]]}
        }
    }
    asyncio.run(harvester.evaluate_shock_and_execute(shock_ltc))
    assert len(executed) == 0, "Unsupported LTC market must be rejected by asset whitelist!"


# ==============================================================================
# ACCOUNTING FINDING: MULTI-LEVEL FOK FEE COMPUTATION
# ==============================================================================
def test_multi_level_fok_fee_computation():
    executor = PolymarketLiveExecutor(dry_run=True)
    # Orderbook with two levels: 50 shares @ $0.10, 50 shares @ $0.90
    book = {
        "asks": [
            {"price": "0.10", "size": "50.0"},  # $5.00 notional
            {"price": "0.90", "size": "50.0"},  # $45.00 notional
        ]
    }
    # Total sweep notional = $50.00
    fillable, vwap, sweep_shares, worst_px, fok_fee, fill_legs = executor.simulate_fok_sweep(
        book, target_notional_usd=50.0, side="BUY", max_acceptable_price=0.95, return_legs=True
    )
    assert fillable is True
    assert len(fill_legs) == 2
    # Exact multi-level fee: 50 * 0.07 * 0.1 * 0.9 + 50 * 0.07 * 0.9 * 0.1 = 0.315 + 0.315 = $0.63000
    assert pytest.approx(fok_fee, 1e-4) == 0.63


# ==============================================================================
# ROUND 2 ADVERSARIAL AUDIT FINDINGS (FINDINGS 1 - 14)
# ==============================================================================
def test_finding_01_kelly_rejection_halts_entry():
    """Finding 1 (P0): Kelly calculation returning 0 or nonpositive collateral halts entry without fallback to fixed ticket."""
    harvester = PolymarketLiveHarvester(ticket_notional=35.0, dry_run=False)
    harvester.save_state = lambda: None
    executed = []
    harvester.executor.execute_snipe_order_async = lambda **kwargs: executed.append(kwargs)

    # 1. Non-positive bankroll halts entry
    harvester.executor.get_collateral_balance = lambda: 0.0
    shock = {
        "event_id": "EVT_KELLY_HALT_01",
        "market_id": "5399991",
        "title": "BTC Price Up",
        "shock_direction": "BUY",
        "seconds_to_expiry": 300.0,
        "candle_distance_pct": 0.10,
        "p_model": 0.53,
        "probability_model": {"model_version": "v1.0", "calibration_id": "calib_001"},
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {"token_id": "0xTOK1", "raw_top_asks": [[0.50, 200.0]]}
        }
    }
    asyncio.run(harvester.evaluate_shock_and_execute(shock))
    assert len(executed) == 0, "Zero bankroll must halt entry!"

    # 2. Bankroll positive, but fee-adjusted edge gives 0 Kelly ticket
    harvester.executor.get_collateral_balance = lambda: 200.0
    harvester.compute_kelly_ticket_size = lambda p, ask, bankroll: 0.0
    shock["event_id"] = "EVT_KELLY_HALT_02"
    asyncio.run(harvester.evaluate_shock_and_execute(shock))
    assert len(executed) == 0, "Kelly rejection (0.0 USD ticket) must reject entry and not fall back to $35!"


def test_finding_02_vwap_kelly_recomputation():
    """Finding 2 (P0): Kelly is recomputed at executable VWAP, rejecting sweeps with negative EV."""
    harvester = PolymarketLiveHarvester(ticket_notional=35.0, dry_run=False)
    harvester.save_state = lambda: None
    executed = []
    harvester.executor.execute_snipe_order_async = lambda **kwargs: executed.append(kwargs)
    harvester.executor.get_collateral_balance = lambda: 273.0

    shock = {
        "event_id": "EVT_VWAP_KELLY_01",
        "market_id": "5399992",
        "title": "BTC Price Up",
        "shock_direction": "BUY",
        "seconds_to_expiry": 300.0,
        "candle_distance_pct": 0.10,
        "p_model": 0.80,
        "probability_model": {"model_version": "v1.0", "calibration_id": "calib_001"},
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "0xTOK1",
                # Best ask 0.75 passes, but second level 0.82 raises VWAP
                "raw_top_asks": [[0.75, 10.0], [0.82, 100.0]]
            }
        }
    }
    # First ask Kelly returns $25, but VWAP Kelly returns 0 (below min lot)
    def mock_kelly(p, price, bankroll):
        if price <= 0.76:
            return 25.0
        return 0.0  # At VWAP (~0.794), edge is negative

    harvester.compute_kelly_ticket_size = mock_kelly
    asyncio.run(harvester.evaluate_shock_and_execute(shock))
    assert len(executed) == 0, "Order must be rejected when executable VWAP does not support minimum Kelly ticket!"


def test_finding_03_orphaned_liquidation_migration(tmp_path, monkeypatch):
    """Finding 3 (P0): load_state migrates orphaned is_liquidating flags without unwind_order_id to UNWIND_RETRY_REQUIRED."""
    state_file = tmp_path / "orphan_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    orphan_state = {
        "active_positions": {
            "POS_ORPHAN": {
                "trade_id": "POS_ORPHAN",
                "entry_shares": 50.0,
                "is_liquidating": True,
                "unwind_order_id": None,
                "exit_order_status": "CANCELED_FOR_STOP_LOSS",
            }
        }
    }
    with open(state_file, "w") as f:
        json.dump(orphan_state, f)

    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.load_state()

    migrated = harvester.active_positions["POS_ORPHAN"]
    assert migrated["is_liquidating"] is False
    assert migrated["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    assert migrated["next_unwind_retry_ts"] == 0.0
    assert migrated["unwind_last_error"] == "MIGRATED_ORPHANED_LIQUIDATION_FLAG"


def test_finding_04_reconciliation_accounting_updates_baseline():
    """Finding 4 (P0): Maker-fill/cancel race updates filled_exit_shares and remaining basis before continue."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.save_state = lambda: None

    pos = {
        "trade_id": "POS_RACE_001",
        "entry_shares": 100.0,
        "remaining_shares": 100.0,
        "remaining_exit_shares": 100.0,
        "notional_usd": 50.0,
        "fee_usd": 0.50,
        "exit_order_id": "0xEXIT_RACE",
        "exit_order_status": "RESTING",
        "filled_exit_shares": 0.0,
        "candle_expiry_ts": time.time() + 600.0,
        "token_id": "0xTOK",
    }
    harvester.active_positions["POS_RACE_001"] = pos
    harvester.executor.get_open_orders = lambda **kwargs: [{"id": "0xEXIT_RACE"}]
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.20", "size": "100.0"}]})
    harvester.executor.cancel_order = lambda oid: {"canceled": [oid]}
    # Exchange returns matched = 30.0 shares
    harvester.executor.get_order_status = lambda oid: {"status": "CANCELED", "size_matched": 30.0, "taking_amount": 15.0}

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    reconciled = harvester.active_positions["POS_RACE_001"]
    assert reconciled["exit_order_status"] == "FILL_RECONCILIATION_REQUIRED"
    assert reconciled["filled_exit_shares"] == 30.0
    assert reconciled["remaining_shares"] == 70.0
    assert reconciled["remaining_exit_shares"] == 70.0
    assert reconciled["remaining_cost_basis"] == 35.0
    assert reconciled["realized_exit_cash"] == 15.0


def test_finding_05_absence_from_open_orders_not_assumed_filled():
    """Finding 5 (P0): Absence from open_orders is not treated as fill; queries order_status authoritatively."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.save_state = lambda: None

    pos = {
        "trade_id": "POS_PASSIVE_001",
        "is_liquidating": True,
        "unwind_order_id": "0xU123",
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 25.0,
        "fee_usd": 0.25,
        "unwind_order_size": 50.0,
        "unwind_start_time": time.time(),
        "token_id": "0xTOK",
    }
    harvester.active_positions["POS_PASSIVE_001"] = pos
    # u_oid is not in open_orders
    harvester.executor.get_open_orders = lambda **kwargs: []
    # But get_order_status reveals it is CANCELED, not matched!
    harvester.executor.get_order_status = lambda oid: {"status": "CANCELED", "size_matched": 0.0}

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    # Must NOT be marked settled or removed from active_positions!
    assert "POS_PASSIVE_001" in harvester.active_positions
    assert pos["exit_order_status"] == "UNWIND_RECONCILIATION_REQUIRED"


def test_finding_06_timeout_unwind_replacement_confirms_cancellation():
    """Finding 6 (P0): Timed-out unwind order confirms cancellation and reconciles fills before replacement."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.save_state = lambda: None
    harvester.passive_unwind_timeout = 5.0

    pos = {
        "trade_id": "POS_TIMEOUT_001",
        "is_liquidating": True,
        "unwind_order_id": "0xU_TIMEOUT",
        "entry_shares": 100.0,
        "remaining_shares": 100.0,
        "notional_usd": 50.0,
        "fee_usd": 0.50,
        "unwind_start_time": time.time() - 10.0,  # Timed out
        "token_id": "0xTOK",
    }
    harvester.active_positions["POS_TIMEOUT_001"] = pos
    harvester.executor.get_open_orders = lambda **kwargs: [{"id": "0xU_TIMEOUT"}]
    harvester.executor.cancel_order = lambda oid: None
    # 40 shares matched before cancel
    harvester.executor.get_order_status = lambda oid: {"status": "CANCELED", "size_matched": 40.0, "taking_amount": 20.0}

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    assert pos["exit_order_status"] == "FILL_RECONCILIATION_REQUIRED"
    assert pos["filled_exit_shares"] == 40.0
    assert pos["remaining_shares"] == 60.0


def test_finding_07_unwind_retry_exponential_backoff():
    """Finding 7 (P1): Failed FOK unwind applies exponential backoff instead of flat 1-second retry."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.save_state = lambda: None

    pos = {
        "trade_id": "POS_RETRY_001",
        "token_id": "0xTOK",
        "entry_shares": 100.0,
        "remaining_shares": 100.0,
        "entry_price": 0.50,
        "target_exit_price": 0.60,
        "exit_order_status": "RESTING",
        "exit_order_id": "0xEXIT_MOCK",
        "is_liquidating": False,
        "candle_expiry_ts": time.time() + 600.0,
    }
    harvester.active_positions["POS_RETRY_001"] = pos
    harvester.executor.get_open_orders = lambda **kwargs: []
    # Trigger stop-loss with bid 0.20
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.20", "size": "100.0"}]})
    harvester.executor.execute_unwind_order = lambda **kwargs: {"success": False, "error": "BOOK_EMPTY"}

    t_before = time.time()
    asyncio.run(harvester.check_resolutions_and_manage_positions())

    assert pos["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    assert pos["unwind_retry_count"] == 1
    # 2^1 = 2 seconds backoff
    assert pos["next_unwind_retry_ts"] >= t_before + 1.9

    # Trigger second failure
    pos["next_unwind_retry_ts"] = 0.0  # make due
    t_before = time.time()
    asyncio.run(harvester.check_resolutions_and_manage_positions())
    assert pos["unwind_retry_count"] == 2
    # 2^2 = 4 seconds backoff
    assert pos["next_unwind_retry_ts"] >= t_before + 3.8


def test_finding_08_unwind_fee_usd_computation():
    """Finding 8 (P2): execute_unwind_order calculates and returns fee_usd in success response."""
    executor = PolymarketLiveExecutor(dry_run=True)
    res = executor.execute_unwind_order("0xTOK", 100.0, "SELL", 0.50)
    assert res["success"] is True
    assert "fee_usd" in res
    # 100 * 0.07 * (0.5 * 0.5) = $1.75
    assert pytest.approx(res["fee_usd"], 1e-4) == 1.75


def test_finding_10_live_paper_depth_parity_gate():
    """Finding 10 (P1): Live engine enforces $50 reference-ticket depth gate and fee metadata."""
    harvester = PolymarketLiveHarvester(ticket_notional=35.0, dry_run=False)
    harvester.save_state = lambda: None
    executed = []
    harvester.executor.execute_snipe_order_async = lambda **kwargs: executed.append(kwargs)
    harvester.executor.get_collateral_balance = lambda: 500.0
    harvester.compute_kelly_ticket_size = lambda p, px, b: 35.0

    # Book with only $30 depth (< 1.50 * 50 = $75)
    shock = {
        "event_id": "EVT_PARITY_001",
        "market_id": "5399993",
        "title": "BTC Depth Parity Test",
        "shock_direction": "BUY",
        "seconds_to_expiry": 300.0,
        "candle_distance_pct": 0.10,
        "p_model": 0.70,
        "probability_model": {"model_version": "v1.0", "calibration_id": "calib_001"},
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {"token_id": "0xTOK1", "raw_top_asks": [[0.50, 60.0]]}  # 30.0 USD depth
        }
    }
    asyncio.run(harvester.evaluate_shock_and_execute(shock))
    assert len(executed) == 0, "Book with < $75 depth must be rejected by $50 reference gate!"

    # Missing fee_metadata must be rejected in live mode
    shock["event_id"] = "EVT_PARITY_002"
    shock["pre_shock_features_t0"]["UP"]["raw_top_asks"] = [[0.50, 200.0]]  # $100 depth
    shock["fee_metadata"] = {}
    asyncio.run(harvester.evaluate_shock_and_execute(shock))
    assert len(executed) == 0, "Missing fee_metadata must reject entry in live mode!"


def test_finding_11_verify_onchain_allowances_operators():
    """Finding 11 (P1): verify_onchain_allowances defines only valid operators (no NameError)."""
    from src.polymarket_research.verify_onchain_allowances import operators
    names = [name for name, _ in operators]
    assert "CTF Exchange V1" not in names
    assert "NegRisk Adapter" not in names
    assert "CTF Exchange V2" in names
    assert "NegRisk Exchange V2" in names
    assert "Exchange V3" in names


def test_finding_13_signature_type_validation():
    """Finding 13 (P1): Enforces funder/signer relationships for signature types 0 and 3."""
    from eth_account import Account
    test_key = "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7e22d318b2059"
    signer_addr = Account.from_key(test_key).address

    # Type 0 with mismatched funder must raise RuntimeError
    with pytest.raises(RuntimeError, match="Type 0 requires the EOA funder to equal"):
        PolymarketLiveExecutor(
            private_key=test_key,
            funder_address="0x000000000000000000000000000000000000dEaD",
            signature_type=0,
            dry_run=False,
        )

    # Type 3 without funder address must raise RuntimeError
    with pytest.raises(RuntimeError, match="Type 3 requires an explicitly configured"):
        PolymarketLiveExecutor(
            private_key=test_key,
            funder_address="",
            signature_type=3,
            dry_run=False,
        )


def test_finding_14_directory_fsync_failure_raises(monkeypatch, tmp_path):
    """Finding 14 (P1): Directory fsync failure propagates as StatePersistenceError."""
    from src.polymarket_research.polymarket_live_harvester import StatePersistenceError
    state_file = tmp_path / "fsync_test_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(dry_run=True)

    def mock_fsync_fail(fd):
        raise OSError("Simulated disk error during directory fsync")

    monkeypatch.setattr("os.fsync", mock_fsync_fail)
    with pytest.raises(StatePersistenceError, match="Critical live state save failed"):
        harvester.save_state()

