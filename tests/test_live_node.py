import pytest
from pipeline.execution.models import MicrostructureContext
from pipeline.live.node import LiveExecutionNode
from pipeline.live.reconciliation import PositionReconciler, PositionState
from pipeline.live.signer import HyperliquidSigner
from pipeline.strategy.state import FeatureState, RawMarketState, RegimeState


def test_signer_payload_and_dead_mans_switch():
    signer = HyperliquidSigner(
        wallet_address="0x1234567890abcdef1234567890abcdef12345678",
        private_key_hex="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    )

    dms_payload = signer.build_dead_mans_switch_action(countdown_ms=30_000)
    assert dms_payload.action_type == "scheduleCancel"
    assert dms_payload.payload["type"] == "scheduleCancel"
    assert dms_payload.payload["time"] > dms_payload.nonce
    assert len(dms_payload.signature) == 64


def test_position_reconciliation_circuit_breaker():
    reconciler = PositionReconciler(max_position_divergence_pct=0.05)

    # Simulate internal fill of 1.0 BTC
    reconciler.record_fill(cl_ord_id="ord_1", symbol="BTC", fill_size=1.0, is_buy=True)

    # Case 1: Exchange matches within tolerance
    feed_ok = {"BTC": PositionState(symbol="BTC", net_size=0.98, entry_px=50000.0, unrealized_pnl=10.0)}
    assert reconciler.reconcile_exchange_state(feed_ok)
    assert not reconciler.is_circuit_broken

    # Case 2: Exchange diverges significantly (0.5 vs 1.0)
    feed_diverged = {"BTC": PositionState(symbol="BTC", net_size=0.50, entry_px=50000.0, unrealized_pnl=5.0)}
    assert not reconciler.reconcile_exchange_state(feed_diverged)
    assert reconciler.is_circuit_broken
    assert "Position divergence on BTC" in reconciler.circuit_break_reason


def test_live_execution_node_pipeline_dispatch():
    signer = HyperliquidSigner(
        wallet_address="0x1234567890abcdef1234567890abcdef12345678",
        private_key_hex="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    )
    node = LiveExecutionNode(signer=signer, total_equity_usd=10000.0)

    market = RawMarketState(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        best_bid=50000.0,
        best_ask=50000.5,
        mid_price=50000.25,
        last_trade_price=50000.25,
        bid_depth_l5=20.0,
        ask_depth_l5=20.0,
        funding_rate_hourly=0.00001,
        predicted_funding_next=0.00001,
    )

    features = FeatureState(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        log_ret_1m=0.0005,
        rvol_15m=0.15,
        rvol_1h=0.18,
        natr_14m=0.002,
        order_flow_imbalance=0.25,
        vwap_basis_bps=1.5,
        cvd_15m=150.0,
        volume_zscore_60m=1.2,
    )

    regime = RegimeState(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        p_trend=0.80,
        p_chop=0.15,
        p_expansion=0.05,
        p_hazard=0.01,
        long_permission=0.99,
        short_permission=0.99,
        regime_multiplier=1.15,
    )

    microstructure = MicrostructureContext(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        best_bid=50000.0,
        best_ask=50000.5,
        spread_bps=1.0,
        queue_ahead_size=2.0,
        queue_behind_size=15.0,
        trade_flow_imbalance=0.60,
        rolling_cancel_ratio=0.10,
        realized_vol_1m_bps=4.0,
    )

    payload = node.process_tick(
        market=market,
        features=features,
        regime=regime,
        microstructure=microstructure,
        raw_win_prob=0.65,
        expected_gain_pct=0.01,
        expected_loss_pct=0.005,
    )

    assert payload is not None
    assert payload.action_type == "order"
    assert payload.payload["type"] == "order"
    assert len(payload.payload["orders"]) == 1
    assert payload.payload["orders"][0]["b"] is True  # Buy
