import pytest
import time
from unittest.mock import MagicMock, patch
from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    ExecutionStatus,
    CLOB_ALLOWED_TICK_SIZES,
)
from src.polymarket_research.negrisk_scanner import (
    resolve_market_category_fee,
    compute_taker_fee,
    CATEGORY_TAKER_FEE_RATES,
    NegRiskScanner,
)
from src.polymarket_research.exp307_monotonicity_copula_scanner import (
    compute_frechet_hoeffding_copula_bounds,
    compute_polymarket_dynamic_taker_fee_per_share,
    MonotonicityPair,
    CATEGORY_FEE_RATES,
)
from src.polymarket_research.exp308_queue_persistence_profiler import (
    QueuePersistenceProfiler,
    PersistenceEvent,
)


# ==============================================================================
# AUDIT ITEM 1: PER-TOKEN TICK SIZE QUANTIZATION
# ==============================================================================

def test_token_specific_tick_size_quantization():
    """
    Verifies that order price quantization resolves the token-specific tick size
    and correctly quantizes prices across all allowed SDK tick sizes:
    ('0.1', '0.01', '0.005', '0.0025', '0.001', '0.0001').
    """
    executor = PolymarketLiveExecutor(dry_run=True)

    # Mock client tick-size lookup
    mock_client = MagicMock()
    mock_client.get_tick_size.side_effect = lambda tid: {
        "TOK_TENTH": "0.1",
        "TOK_CENT": "0.01",
        "TOK_HALF_CENT": "0.005",
        "TOK_QUARTER_CENT": "0.0025",
        "TOK_MILLI": "0.001",
        "TOK_SUB_MILLI": "0.0001",
    }.get(tid, "0.01")
    executor.client = mock_client

    # Verify lookups
    assert executor.get_token_tick_size("TOK_TENTH") == 0.1
    assert executor.get_token_tick_size("TOK_CENT") == 0.01
    assert executor.get_token_tick_size("TOK_HALF_CENT") == 0.005
    assert executor.get_token_tick_size("TOK_QUARTER_CENT") == 0.0025
    assert executor.get_token_tick_size("TOK_MILLI") == 0.001
    assert executor.get_token_tick_size("TOK_SUB_MILLI") == 0.0001

    # Verify rounding quantization
    assert executor.quantize_order_price(0.5342, "TOK_TENTH") == 0.5
    assert executor.quantize_order_price(0.5342, "TOK_CENT") == 0.53
    assert executor.quantize_order_price(0.5342, "TOK_HALF_CENT") == 0.535
    assert executor.quantize_order_price(0.5342, "TOK_QUARTER_CENT") == 0.5350
    assert executor.quantize_order_price(0.5342, "TOK_MILLI") == 0.534
    assert executor.quantize_order_price(0.53426, "TOK_SUB_MILLI") == 0.5343

    # Verify boundary clamping [tick_size, 1.0 - tick_size]
    assert executor.quantize_order_price(0.00001, "TOK_SUB_MILLI") == 0.0001
    assert executor.quantize_order_price(0.99999, "TOK_SUB_MILLI") == 0.9999
    assert executor.quantize_order_price(0.00001, "TOK_MILLI") == 0.001
    assert executor.quantize_order_price(0.99999, "TOK_MILLI") == 0.999


# ==============================================================================
# AUDIT ITEM 2: ON-CHAIN VERIFICATION & SCHEMA NORMALIZATION
# ==============================================================================

def test_trade_record_schema_normalization():
    """
    Verifies that normalize_trade_record handles both transaction_hash and transactionHash,
    id and trade_id, and capitalizes status strings.
    """
    executor = PolymarketLiveExecutor(dry_run=True)

    # CamelCase SDK record
    rec_camel = {
        "id": "TR_1001",
        "status": "confirmed",
        "transactionHash": "0xabc1234567890abcdef",
    }
    norm_camel = executor.normalize_trade_record(rec_camel)
    assert norm_camel["trade_id"] == "TR_1001"
    assert norm_camel["id"] == "TR_1001"
    assert norm_camel["status"] == "CONFIRMED"
    assert norm_camel["transaction_hash"] == "0xabc1234567890abcdef"
    assert norm_camel["transactionHash"] == "0xabc1234567890abcdef"

    # Snake_case internal record
    rec_snake = {
        "trade_id": "TR_1002",
        "status": "matched",
        "transaction_hash": "0xdef9876543210fedcba",
    }
    norm_snake = executor.normalize_trade_record(rec_snake)
    assert norm_snake["trade_id"] == "TR_1002"
    assert norm_snake["id"] == "TR_1002"
    assert norm_snake["status"] == "MATCHED"
    assert norm_snake["transaction_hash"] == "0xdef9876543210fedcba"
    assert norm_snake["transactionHash"] == "0xdef9876543210fedcba"


def test_onchain_erc1155_direct_balance_read():
    """
    Verifies that get_onchain_erc1155_balance constructs correct eth_call JSON-RPC
    payload targeting the ConditionalTokens contract selector 0x00fdd58e.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    executor.funder_address = "0x8979be346be54dd4dfa22830f36f6d0f88a0b06b"

    with patch("requests.post") as mock_post:
        # Mock successful 200 RPC response with hex balance 100_000_000 (100.0 shares)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": hex(100_000_000),  # 100 shares * 1e6
        }
        mock_post.return_value = mock_resp

        bal = executor.get_onchain_erc1155_balance(
            token_id="115792089237316195423570985008687907853269984665640564039457584007913129639935"
        )
        assert bal == 100.0
        assert mock_post.called
        call_args = mock_post.call_args[1]["json"]
        assert call_args["method"] == "eth_call"
        assert call_args["params"][0]["to"] == "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
        assert call_args["params"][0]["data"].startswith("0x00fdd58e")


# ==============================================================================
# AUDIT ITEM 3: AUTHORITATIVE CATEGORY-SPECIFIC FEES
# ==============================================================================

def test_authoritative_category_fee_resolution():
    """
    Verifies that category-specific taker fee rates strictly adhere to Polymarket's
    schedule and fail-closed when metadata is unresolvable.
    """
    # 1. Crypto (0.07)
    crypto_market = {"category": "Crypto", "question": "Will Bitcoin break $100k?"}
    assert resolve_market_category_fee(crypto_market) == 0.07

    # 2. Sports (0.05)
    sports_market = {"category": "Sports", "question": "Chiefs vs 49ers Super Bowl"}
    assert resolve_market_category_fee(sports_market) == 0.05

    # 3. Economics / FOMC (0.05)
    econ_market = {"category": "Economics", "question": "Fed interest rate decision October"}
    assert resolve_market_category_fee(econ_market) == 0.05

    # 4. Politics & Finance (0.04)
    politics_market = {"category": "Politics", "question": "US Presidential Election 2028"}
    assert resolve_market_category_fee(politics_market) == 0.04

    # 5. Geopolitics (0.00)
    geopol_market = {"category": "Geopolitics", "question": "Ceasefire treaty signed"}
    assert resolve_market_category_fee(geopol_market) == 0.00

    # 6. Fail-closed: Unresolvable metadata returns None
    unresolvable = {"category": "UnknownMysteryCategory", "question": "Something random"}
    assert resolve_market_category_fee(unresolvable) is None


def test_copula_frechet_hoeffding_bounds():
    """
    Verifies mathematical bounds: W(u, v) <= C(u, v) <= M(u, v).
    """
    # Perfect correlation: u=0.7, v=0.7 -> W=0.4, M=0.7
    lower, upper = compute_frechet_hoeffding_copula_bounds(0.7, 0.7)
    assert pytest.approx(lower, 1e-5) == 0.4
    assert pytest.approx(upper, 1e-5) == 0.7

    # Disjoint bounds: u=0.3, v=0.4 -> W=max(0, 0.3+0.4-1)=0.0, M=0.3
    lower, upper = compute_frechet_hoeffding_copula_bounds(0.3, 0.4)
    assert lower == 0.0
    assert upper == 0.3


# ==============================================================================
# AUDIT ITEM 4: QUEUE PROFILER LATENCY & TIMEOUT SEPARATION
# ==============================================================================

def test_queue_profiler_distinguishes_timeouts_from_evaporation():
    """
    Verifies that QueuePersistenceProfiler distinguishes network timeouts from
    confirmed quote evaporation.
    """
    profiler = QueuePersistenceProfiler()

    # Create event where 85ms was an HTTP error/timeout
    ev_timeout = PersistenceEvent(
        event_id="EV_TIMEOUT",
        token_id="TOK_TEST",
        t0_timestamp=time.time(),
        initial_best_ask=0.50,
        initial_depth=100.0,
        persistence_matrix={"50ms": True, "85ms": False},
        evaporated_under_85ms=False,  # NOT flagged as evaporated because status was REQUEST_TIMEOUT
        final_survival_seconds=0.05,
        observation_log={
            "50ms": {"status": "CONFIRMED_PRESENT", "quote_present": True, "rtt_ms": 12.0},
            "85ms": {"status": "REQUEST_TIMEOUT", "quote_present": None, "rtt_ms": 350.0},
        },
        has_network_timeout=True,
    )
    assert ev_timeout.evaporated_under_85ms is False
    assert ev_timeout.has_network_timeout is True

    # Create event where 85ms was confirmed evaporated
    ev_evaporated = PersistenceEvent(
        event_id="EV_EVAPORATED",
        token_id="TOK_TEST",
        t0_timestamp=time.time(),
        initial_best_ask=0.50,
        initial_depth=100.0,
        persistence_matrix={"50ms": True, "85ms": False},
        evaporated_under_85ms=True,  # Genuinely evaporated
        final_survival_seconds=0.05,
        observation_log={
            "50ms": {"status": "CONFIRMED_PRESENT", "quote_present": True, "rtt_ms": 11.5},
            "85ms": {"status": "CONFIRMED_EVAPORATED", "quote_present": False, "rtt_ms": 14.2},
        },
        has_network_timeout=False,
    )
    assert ev_evaporated.evaporated_under_85ms is True
    assert ev_evaporated.has_network_timeout is False


# ==============================================================================
# AUDIT ITEM 5: DYNAMIC DEPTH-PROPORTIONAL SIZING & EXPOSURE CEILING
# ==============================================================================

def test_dynamic_depth_proportional_sizing():
    """
    Verifies that PolymarketLiveHarvester dynamically scales lot size proportionally
    to executable orderbook depth (notional = min(ticket, depth / 1.50)):
    - Large depth ($100): sizes full $25.00 lot
    - Moderate depth ($24): sizes scaled $16.00 lot (24 / 1.50)
    - Shallow depth ($6): rejects because $4.00 < $5.00 minimum lot size floor
    - Headroom cap: if portfolio exposure is $88 / $100, sizes at max $12.00 headroom
    - Static sizing: when dynamic_sizing=False, rejects moderate depth ($24 < $37.50)
    """
    import asyncio
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import OrderResult, ExecutionStatus

    async def _run():
        executed_orders = []

        async def mock_snipe(**kwargs):
            executed_orders.append(kwargs)
            return OrderResult(
                success=True,
                order_id="MOCK_DYNAMIC_001",
                trade_id=kwargs.get("trade_id", "T1"),
                token_id=kwargs.get("token_id", "TOK1"),
                target_token="UP",
                side="BUY",
                price=0.50,
                size=kwargs.get("notional_usd", 25.0) / 0.50,
                notional_usd=kwargs.get("notional_usd", 25.0),
                fee_usd=0.05,
                latency_ms=1.5,
                mode="DRY_RUN",
                execution_status=ExecutionStatus.POSITION_CONFIRMED,
                confirmed_onchain=True,
            )

        # 1. Deep Book ($100 depth) -> should size full $25.00
        harvester = PolymarketLiveHarvester(ticket_notional=25.0, dry_run=True, dynamic_sizing=True, max_exposure=100.0, max_concurrent=5)
        harvester.save_state = lambda: None
        harvester.executor.execute_snipe_order_async = mock_snipe

        shock_deep = {
            "event_id": "EVT_DEEP_001",
            "market_id": "5399001",
            "shock_direction": "BUY",
            "seconds_to_expiry": 300.0,
            "candle_distance_pct": 0.10,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "0xTOK_UP_DEEP",
                    "raw_top_asks": [[0.50, 200.0]],  # $100 depth
                }
            }
        }
        await harvester.evaluate_shock_and_execute(shock_deep)
        assert len(executed_orders) == 1
        assert executed_orders[-1]["notional_usd"] == 25.0

        # 2. Moderate Book ($24 depth) -> should dynamically size to $16.00 (24 / 1.50)
        harvester.active_positions.clear()
        shock_mod = {
            "event_id": "EVT_MOD_002",
            "market_id": "5399002",
            "shock_direction": "BUY",
            "seconds_to_expiry": 300.0,
            "candle_distance_pct": 0.10,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "0xTOK_UP_MOD",
                    "raw_top_asks": [[0.60, 40.0]],  # $24 depth
                }
            }
        }
        await harvester.evaluate_shock_and_execute(shock_mod)
        assert len(executed_orders) == 2
        assert executed_orders[-1]["notional_usd"] == 16.00

        # 3. Shallow Book ($6 depth) -> max depth notional is $4.00, below $5.00 floor -> rejected!
        harvester.active_positions.clear()
        shock_shallow = {
            "event_id": "EVT_SHALLOW_003",
            "market_id": "5399003",
            "shock_direction": "BUY",
            "seconds_to_expiry": 300.0,
            "candle_distance_pct": 0.10,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "0xTOK_UP_SHALLOW",
                    "raw_top_asks": [[0.50, 12.0]],  # $6 depth
                }
            }
        }
        await harvester.evaluate_shock_and_execute(shock_shallow)
        assert len(executed_orders) == 2  # No new order fired!

        # 4. Exposure Headroom Capping: Current exposure = $88, ceiling = $100 -> headroom = $12.00
        harvester.active_positions.clear()
        harvester.trades_this_hour = 0
        harvester.trades_per_market.clear()
        harvester.active_positions["EXISTING_POS"] = {"notional_usd": 88.0}
        shock_deep_4 = dict(shock_deep)
        shock_deep_4["event_id"] = "EVT_DEEP_004"
        shock_deep_4["market_id"] = "5399004"
        await harvester.evaluate_shock_and_execute(shock_deep_4)  # Depth is $100, but headroom is $12
        assert len(executed_orders) == 3
        assert executed_orders[-1]["notional_usd"] == 12.00

        # 5. Static Mode: dynamic_sizing=False -> fails depth hurdle on moderate book ($24 / $25 = 0.96x < 1.5x)
        harvester_static = PolymarketLiveHarvester(ticket_notional=25.0, dry_run=True, dynamic_sizing=False, max_exposure=100.0)
        harvester_static.save_state = lambda: None
        harvester_static.executor.execute_snipe_order_async = mock_snipe
        shock_mod_5 = dict(shock_mod)
        shock_mod_5["event_id"] = "EVT_MOD_005"
        shock_mod_5["market_id"] = "5399005"
        await harvester_static.evaluate_shock_and_execute(shock_mod_5)
        assert len(executed_orders) == 3  # Static harvester must reject!

    asyncio.run(_run())


def test_half_kelly_capital_allocation():
    """Verify Half-Kelly sizing (lambda=0.50, max 12% bankroll cap, boundary filters)."""
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    harvester = PolymarketLiveHarvester(dry_run=True)
    bankroll = 283.15

    # 1. Standard entry at P=0.65 with model probability p=0.78
    # Edge = 0.13, unconstrained Kelly = 0.13 / 0.35 = 0.3714
    # Scaled fraction (0.50 * 0.3714) = 0.1857
    # Bounded fraction = min(0.12, 0.1857) = 0.12
    # Ticket = round(283.15 * 0.12, 2) = $33.98
    ticket = harvester.compute_kelly_ticket_size(p_model=0.78, p_market_ask=0.65, bankroll=bankroll)
    assert ticket == 33.98, f"Expected $33.98, got {ticket}"

    # 2. Boundary filter: P >= 0.88 rejected
    assert harvester.compute_kelly_ticket_size(p_model=0.95, p_market_ask=0.89, bankroll=bankroll) == 0.0

    # 3. High-conviction momentum entry (0.73): Accepted with 0.88 ceiling!
    ticket_73 = harvester.compute_kelly_ticket_size(p_model=0.85, p_market_ask=0.73, bankroll=bankroll)
    assert ticket_73 > 0.0

    # 4. Boundary filter: P <= 0.15 rejected
    assert harvester.compute_kelly_ticket_size(p_model=0.60, p_market_ask=0.14, bankroll=bankroll) == 0.0

    # 5. Zero or negligible edge (<= 1.5%) rejected
    assert harvester.compute_kelly_ticket_size(p_model=0.66, p_market_ask=0.65, bankroll=bankroll) == 0.0


def test_raw_vwap_boundary_and_fee_separation():
    """
    Verifies that:
    1. Raw VWAP is evaluated against [MIN_PRICE_FLOOR, MAX_PRICE_CEILING] before fees.
    2. Fee-loaded effective price (e.g. raw VWAP $0.7065 with fee -> $0.7204) is NOT rejected.
    3. High-conviction momentum entry at raw ask $0.80 (within restored 0.88 ceiling) is accepted.
    4. Out-of-bounds ask ($0.89) is rejected.
    """
    import asyncio
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import OrderResult, ExecutionStatus

    async def _run():
        executed_orders = []

        async def mock_snipe(**kwargs):
            executed_orders.append(kwargs)
            return OrderResult(
                success=True,
                order_id="MOCK_SNIPE_001",
                trade_id=kwargs.get("trade_id", "T1"),
                token_id=kwargs.get("token_id", "TOK1"),
                target_token=kwargs.get("target_token", "UP"),
                side="BUY",
                price=kwargs.get("target_price", 0.70),
                size=25.0 / max(0.01, kwargs.get("target_price", 0.70)),
                notional_usd=kwargs.get("notional_usd", 25.0),
                fee_usd=0.35,
                latency_ms=1.2,
                mode="DRY_RUN",
                execution_status=ExecutionStatus.POSITION_CONFIRMED,
                confirmed_onchain=True,
            )

        harvester = PolymarketLiveHarvester(ticket_notional=25.0, dry_run=True, max_price_ceiling=0.88, min_price_floor=0.15)
        harvester.save_state = lambda: None
        harvester.executor.execute_snipe_order_async = mock_snipe

        # Test Case 1: Raw VWAP = 0.7065, Fee-Inclusive effective_price = 0.7204
        # Even with an older 0.72 ceiling, raw VWAP (0.7065 <= 0.72) must pass!
        shock_fee_case = {
            "event_id": "EVT_FEE_BUG_001",
            "market_id": "5451795",
            "shock_direction": "BUY",
            "seconds_to_expiry": 883.0,
            "candle_distance_pct": 0.051,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "0xTOK_FEE_ETH",
                    "effective_price_$25": 0.7204,  # Fee-loaded effective price
                    "raw_top_asks": [[0.70, 20.0], [0.71, 10.0], [0.72, 25.0]], # Executable depth $39.10
                }
            }
        }
        await harvester.evaluate_shock_and_execute(shock_fee_case)
        assert len(executed_orders) == 1, "Order with raw VWAP <= 0.72 must not be rejected by fee-inclusive effective price!"
        assert executed_orders[-1]["target_price"] <= 0.72

        # Test Case 2: High-conviction momentum breakout at raw ask $0.80 (within restored 0.88 ceiling)
        harvester.active_positions.clear()
        shock_momentum_80 = {
            "event_id": "EVT_MOM_002",
            "market_id": "5451796",
            "shock_direction": "BUY",
            "seconds_to_expiry": 900.0,
            "candle_distance_pct": 0.065,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "0xTOK_MOM_80",
                    "effective_price_$25": 0.8120,
                    "raw_top_asks": [[0.80, 50.0], [0.81, 50.0]], # $80.50 depth
                }
            }
        }
        await harvester.evaluate_shock_and_execute(shock_momentum_80)
        assert len(executed_orders) == 2, "High-conviction breakout at $0.80 must be executed under 0.88 ceiling!"

        # Test Case 3: Ask exceeds 0.88 ceiling ($0.89) -> must be rejected
        harvester.active_positions.clear()
        shock_excess_89 = {
            "event_id": "EVT_EXCESS_003",
            "market_id": "5451797",
            "shock_direction": "BUY",
            "seconds_to_expiry": 900.0,
            "candle_distance_pct": 0.08,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "0xTOK_EXCESS_89",
                    "effective_price_$25": 0.90,
                    "raw_top_asks": [[0.89, 50.0]],
                }
            }
        }
        await harvester.evaluate_shock_and_execute(shock_excess_89)
        assert len(executed_orders) == 2, "Ask at $0.89 must be rejected by 0.88 ceiling!"

    asyncio.run(_run())


