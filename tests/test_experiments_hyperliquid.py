"""
Unit and Microstructure Integration Tests for Hyperliquid Experiments (S4, S6, S5)
==================================================================================
Tests:
  - Experiment S4: Stage-1 30s Partial-Liquidation Cooldown Wick Catcher (exp_s4_hl_wick_catcher.py)
  - Experiment S6: HIP-2 Geometric Grid Exhaustion & Hyperp 8h EMA Squeeze (exp_s6_hip2_hyperp.py)
  - Experiment S5: HyperEVM Precompile (0x0808) to CoreWriter Simulator (exp_s5_hyperevm_atomic.py)
"""

import math
import time
import pytest

from experiments.core.hl_mark_replicator import HyperCoreMarkPriceReplicator
from experiments.core.shadow_broker import L2Book, OrderType, RealisticShadowBroker, Side
from experiments.hyperliquid.exp_s4_hl_wick_catcher import (
    CooldownState,
    ExpS4WickCatcher,
    S4Config,
    calculate_equity_cushion_to_mmr,
    calculate_exact_liq_price,
)
from experiments.hyperliquid.exp_s6_hip2_hyperp import (
    ExpS6Runner,
    HIP2GenesisParams,
    HIP2SpotTracker,
    Hyperp8hEMATracker,
)
from experiments.hyperliquid.exp_s5_hyperevm_atomic import (
    CORE_WRITER_LIMIT_ORDER_HEADER,
    FelixCDP,
    HyperCoreAtomicArbSimulator,
    HyperswapReserves,
    calculate_precompile_gas,
    strip_dust,
)


# ==============================================================================
# EXPERIMENT S4 TESTS: STAGE-1 30s COOLDOWN WICK CATCHER
# ==============================================================================

class TestExperimentS4WickCatcher:

    def test_exact_liq_price_formula(self):
        """
        Tests: liq_price = price - (side * margin_available / position_size) / (1 - mmr * side)
        """
        # Long position: Entry $100, 1000 units, $4000 equity, 4% MMR
        # liq_price = 100 - (1 * 4000 / 1000) / (1 - 0.04) = 100 - 4 / 0.96 = 100 - 4.1667 = 95.8333
        p_liq_long = calculate_exact_liq_price(
            price=100.0,
            side=1,
            margin_available=4000.0,
            position_size=1000.0,
            mmr=0.04,
        )
        assert math.isclose(p_liq_long, 100.0 - (4.0 / 0.96), rel_tol=1e-5)

        # Short position: Entry $100, 1000 units, $4000 equity, 4% MMR
        # liq_price = 100 + (4000 / 1000) / (1 + 0.04) = 100 + 4 / 1.04 = 100 + 3.84615 = 103.84615
        p_liq_short = calculate_exact_liq_price(
            price=100.0,
            side=-1,
            margin_available=4000.0,
            position_size=1000.0,
            mmr=0.04,
        )
        assert math.isclose(p_liq_short, 100.0 + (4.0 / 1.04), rel_tol=1e-5)

    def test_equity_cushion_and_vault_takeover_boundary(self):
        """Tests 1.0 x MMR vs 2/3 x MMR threshold computation."""
        pos_size = 1000.0
        mark_px = 100.0
        equity = 3500.0
        mmr = 0.04

        mmr_req, hlp_req, ratio = calculate_equity_cushion_to_mmr(
            position_size=pos_size,
            current_mark=mark_px,
            account_equity=equity,
            mmr=mmr,
        )
        # 1000 * 100 * 0.04 = 4000.0
        assert math.isclose(mmr_req, 4000.0)
        # 2/3 * 4000 = 2666.67
        assert math.isclose(hlp_req, 4000.0 * (2.0 / 3.0), rel_tol=1e-5)
        # 3500 / 4000 = 0.875
        assert math.isclose(ratio, 0.875)

    def test_whale_registration_and_stage1_trigger(self):
        """Tests $100k notional gate and Stage-1 20% partial liquidation trigger."""
        catcher = ExpS4WickCatcher(config=S4Config(min_whale_notional=100_000.0))

        # Whale with $50k notional -> should be ignored
        small_pos = catcher.register_whale_position(
            symbol="SOL",
            wallet="0xSmall",
            size=500.0,
            entry_price=100.0,
            margin_available=2000.0,
        )
        assert small_pos is None

        # Whale with $200k notional -> should be registered
        whale_pos = catcher.register_whale_position(
            symbol="SOL",
            wallet="0xWhale",
            size=2000.0,
            entry_price=100.0,
            margin_available=7900.0,
        )
        assert whale_pos is not None
        assert whale_pos.notional == 200_000.0

        # Trigger Stage 1
        t0 = 1000.0
        event = catcher.on_stage1_partial_liquidation(
            symbol="SOL",
            wallet="0xWhale",
            partial_size=400.0,  # 20% of 2000
            price=100.0,
            timestamp=t0,
        )
        assert event is not None
        assert event.partial_liq_size == 400.0
        assert event.remaining_dump_size == 1600.0
        assert event.state == CooldownState.MONITORING

    def test_cooldown_verification_hlp_invalidation(self):
        """
        If mark price drops so far that equity <= 2/3 x MMR, HLP vault takes over off-book
        and the CLOB dump is cancelled => setup MUST be invalidated.
        """
        catcher = ExpS4WickCatcher()
        pos = catcher.register_whale_position(
            symbol="SOL",
            wallet="0xWhale",
            size=2000.0,
            entry_price=100.0,
            margin_available=7900.0,
            mmr=0.04,
        )
        t0 = 1000.0
        event = catcher.on_stage1_partial_liquidation("SOL", "0xWhale", 400.0, 100.0, timestamp=t0)

        # Severe price crash: SOL drops to $97.0
        # PnL = 2000 * (97 - 100) = -6000
        # Remaining equity = 7900 - 6000 = 1900
        # MMR req at 97 = 2000 * 97 * 0.04 = 7760. 2/3 x MMR = 5173.33
        # Since 1900 <= 5173.33, HLP vault takes over!
        catcher.mark_replicator.update_hl_book("SOL", 97.0, 97.1, timestamp_mono=t0 + 10.0)
        catcher.mark_replicator.update_hl_oracle("SOL", 97.0, timestamp_mono=t0 + 10.0)

        valid = catcher.verify_cooldown_invariants(event, current_ts=t0 + 10.0)
        assert valid is False
        assert event.state == CooldownState.INVALIDATED_HLP_TAKEOVER

    def test_cooldown_verification_top_up_invalidation(self):
        """If whale deposits margin or price recovers above 1.0 x MMR, Stage 2 is cancelled."""
        catcher = ExpS4WickCatcher()
        pos = catcher.register_whale_position(
            symbol="SOL",
            wallet="0xWhale",
            size=2000.0,
            entry_price=100.0,
            margin_available=7900.0,
            mmr=0.04,
        )
        t0 = 1000.0
        event = catcher.on_stage1_partial_liquidation("SOL", "0xWhale", 400.0, 100.0, timestamp=t0)

        # Price rebounds to $101.0 -> Equity rises above MMR requirement
        catcher.mark_replicator.update_hl_book("SOL", 101.0, 101.1, timestamp_mono=t0 + 10.0)
        catcher.mark_replicator.update_hl_oracle("SOL", 101.0, timestamp_mono=t0 + 10.0)

        valid = catcher.verify_cooldown_invariants(event, current_ts=t0 + 10.0)
        assert valid is False
        assert event.state == CooldownState.INVALIDATED_TOP_UP

    def test_geometric_ladder_generation(self):
        """Tests geometric ALO maker order ladder generation."""
        catcher = ExpS4WickCatcher(config=S4Config(ladder_levels=4, wick_bottom_fraction=0.30))
        ladder = catcher.generate_geometric_ladder(
            symbol="SOL",
            whale_side=1,  # Downward wick
            p_mark=100.0,
            clearing_px=80.0,
            total_ladder_size=400.0,
        )
        assert len(ladder) == 4
        # Prices must be sorted ascending within the bottom band
        prices = [px for px, sz in ladder]
        assert prices == sorted(prices)
        assert all(px <= 95.0 for px in prices)  # At least 5% below p_mark
        assert all(px >= 82.0 for px in prices)  # Clamped to max 18% below p_mark
        assert sum(sz for px, sz in ladder) == pytest.approx(400.0, rel=1e-3)

    def test_macro_vol_kill_switch(self):
        """Tests that external Binance/OKX volatility spikes trip kill switch."""
        catcher = ExpS4WickCatcher(config=S4Config(vol_spike_threshold_pct=0.015))
        t = 1000.0
        catcher.record_cex_price("SOL", 100.0, t - 4.0)
        catcher.record_cex_price("SOL", 100.0, t - 2.0)
        catcher.record_cex_price("SOL", 98.0, t)  # 2.0% drop in 4 seconds > 1.5%

        tripped = catcher.check_macro_vol_kill_switch("SOL", t)
        assert tripped is True

    def test_full_stage1_stage2_lifecycle(self):
        """Simulates full 30s lifecycle with book clearing, ladder fill, delta hedge, and TP order."""
        catcher = ExpS4WickCatcher()
        book = L2Book(symbol="SOL")
        mid = 100.0
        for i in range(1, 30):
            book.set_level(mid - i * 0.5, 20.0, Side.BUY)
            book.set_level(mid + i * 0.5, 200.0, Side.SELL)

        event = catcher.simulate_lifecycle_event(
            symbol="SOL",
            wallet="0xWhale1111",
            position_size=2000.0,
            entry_price=100.0,
            margin_available=7900.0,
            book=book,
            cex_vol_spike=False,
        )
        assert event.state == CooldownState.FILLED_AND_HEDGED
        assert event.filled_size > 0
        assert event.hedged_size == event.filled_size * 0.50
        assert event.take_profit_order_id is not None
        assert event.realized_pnl > 0


# ==============================================================================
# EXPERIMENT S6 TESTS: HIP-2 GRID EXHAUSTION & HYPERP 8H EMA SQUEEZE
# ==============================================================================

class TestExperimentS6HIP2Hyperp:

    def test_hip2_geometric_grid_pricing(self):
        """Tests P_k = P_0 * 1.003^(k - 1) and cumulative cost formula."""
        params = HIP2GenesisParams(
            symbol="PURR",
            p0=0.10,
            n_total=300,
            s_level=100_000.0,
            n_seeded=50,
        )
        # Level 1 price
        assert math.isclose(params.price_at_level(1), 0.10)
        # Level 2 price: 0.10 * 1.003 = 0.1003
        assert math.isclose(params.price_at_level(2), 0.1003)

        # Closed-form cost to absorb 1 level
        cost_1 = params.cumulative_cost(1)
        assert math.isclose(cost_1, 100_000.0 * 0.10)  # $10,000

        # Cost to absorb 2 levels
        cost_2 = params.cumulative_cost(2)
        assert math.isclose(cost_2, 10_000.0 + 100_000.0 * 0.1003)

    def test_hip2_grid_level_inversion(self):
        """Tests finding level k from market price and from cumulative spend."""
        params = HIP2GenesisParams(symbol="PURR", p0=0.10, s_level=100_000.0)
        px_50 = params.price_at_level(50)
        lvl_found = params.level_for_price(px_50)
        assert lvl_found == 50

        cost_50 = params.cumulative_cost(50)
        lvl_by_cost = params.level_for_cumulative_usd(cost_50)
        assert lvl_by_cost == 50

    def test_hip2_breakout_trigger_conditions(self):
        """Verifies breakout requires >80% absorption within 15 mins AND external depth < 0.2x."""
        params = HIP2GenesisParams(
            symbol="PURR",
            p0=0.10,
            n_seeded=50,
            baseline_external_depth=50_000.0,
        )
        tracker = HIP2SpotTracker(params)
        t0 = 1000.0

        # Case 1: Absorbed 30 levels (60% < 80%) -> No breakout
        for k in range(1, 31):
            tracker.on_buy_trade(params.price_at_level(k), 100_000.0, t0 + k * 10.0)

        is_brk, _ = tracker.evaluate_breakout_signal(
            external_ask_depth_above_seeded=5_000.0,  # 0.10x baseline
            current_ts=t0 + 300.0,
        )
        assert is_brk is False

        # Case 2: Absorbed 42 levels (84% > 80%) in 600s, but external depth is thick (0.4x > 0.2x) -> No breakout
        for k in range(31, 43):
            tracker.on_buy_trade(params.price_at_level(k), 100_000.0, t0 + k * 10.0)

        is_brk2, _ = tracker.evaluate_breakout_signal(
            external_ask_depth_above_seeded=25_000.0,  # 0.50x baseline
            current_ts=t0 + 500.0,
        )
        assert is_brk2 is False

        # Case 3: Absorbed 42 levels (84%) in 600s AND external depth is thin (0.10x < 0.2x) -> Breakout!
        is_brk3, telem3 = tracker.evaluate_breakout_signal(
            external_ask_depth_above_seeded=5_000.0,
            current_ts=t0 + 600.0,
        )
        assert is_brk3 is True
        assert telem3["is_breakout"] is True

    def test_hip2_auto_stepping_bid_and_trailing_stop(self):
        """Tests 3-second auto-stepping bid and 0.9% (3 ticks: 1.003^3) trailing stop."""
        params = HIP2GenesisParams(symbol="PURR", p0=0.10, n_seeded=50)
        tracker = HIP2SpotTracker(params)
        t0 = 1000.0

        # Push to level 20
        tracker.on_buy_trade(params.price_at_level(20), 100_000.0, t0 + 5.0)
        bid = tracker.auto_stepping_bid
        stop = tracker.trailing_stop_price

        # Trailing stop should be bid / (1.003^3) ~ bid * 0.99105 (~0.9% below)
        expected_stop = bid / (1.003 ** 3)
        assert math.isclose(stop, expected_stop, rel_tol=1e-5)
        assert (bid - stop) / bid == pytest.approx(0.008947, rel=1e-3)

    def test_hyperp_8h_ema_weights_normalization(self):
        """Verifies discrete exponential weights sum to 1.0."""
        tracker = Hyperp8hEMATracker(symbol="W", p_mark_init=1.0)
        assert len(tracker.weights) == 1440
        assert math.isclose(sum(tracker.weights), 1.0, rel_tol=1e-6)

    def test_hyperp_oracle_4x_hard_cap(self):
        """Verifies oracle price is capped at 4x initial mark price."""
        tracker = Hyperp8hEMATracker(symbol="W", p_mark_init=1.0)
        # Feed extreme price ($10.00)
        for _ in range(1440):
            tracker.add_minute_mark(10.0)

        oracle = tracker.compute_hyperp_oracle()
        assert math.isclose(oracle, 4.0)  # Capped at 4 * 1.0 = 4.0

    def test_hyperp_naked_short_blocked_pre_tge(self):
        """Never short naked prior to TGE spot opening."""
        tracker = Hyperp8hEMATracker(symbol="W", p_mark_init=1.0)
        for _ in range(1440):
            tracker.add_minute_mark(1.0)

        # Trading at $2.20 (2.2x oracle > 1.8x), BUT CEX spot is not open
        is_short, reason, telem = tracker.evaluate_short_signal(
            current_hyperp_price=2.20,
            cex_spot_listing_active=False,
        )
        assert is_short is False
        assert reason == "BLOCKED_NO_CEX_SPOT_OPEN"
        assert telem["gate_blocked"] == "NEVER_SHORT_NAKED_PRIOR_TO_TGE_SPOT"

    def test_hyperp_short_trigger_post_tge(self):
        """Once CEX spot opens, basis collapse short signal is triggered."""
        tracker = Hyperp8hEMATracker(symbol="W", p_mark_init=1.0)
        for _ in range(1440):
            tracker.add_minute_mark(1.0)

        is_short, reason, telem = tracker.evaluate_short_signal(
            current_hyperp_price=2.20,
            cex_spot_listing_active=True,
        )
        assert is_short is True
        assert reason == "ARM_POST_TGE_SHORT"


# ==============================================================================
# EXPERIMENT S5 TESTS: HYPEREVM PRECOMPILE (0x0808) & COREWRITER
# ==============================================================================

class TestExperimentS5HyperEVM:

    def test_precompile_0808_gas_formula(self):
        """Tests gas formula 2000 + 65 * (in + out) and 5000 sub-frame cap."""
        # 32 bytes in, 128 bytes out => 2000 + 65 * 160 = 2000 + 10400 = 12400
        gas = calculate_precompile_gas(in_bytes=32, out_bytes=128)
        assert gas == 12400

        # Simulated precompile query
        sim = HyperCoreAtomicArbSimulator()
        book = L2Book(symbol="PURR")
        book.set_level(0.1250, 100_000.0, Side.BUY)
        book.set_level(0.1260, 100_000.0, Side.SELL)
        sim.register_asset(100, "PURR", book)

        res_ok = sim.query_precompile_0808(100)
        assert res_ok.success is True
        assert res_ok.gas_used == 12400
        assert res_ok.best_bid == 0.1250

        # Invalid asset index => capped at 5000 gas
        res_bad = sim.query_precompile_0808(9999)
        assert res_bad.success is False
        assert res_bad.gas_used == 5000

    def test_strip_dust_decimal_rounding(self):
        """Tests decimal rounding strip prior to HyperEVM -> HyperCore transfers."""
        # Raw amount with dust: 1234567890123456789, dust_factor = 1e10
        raw = 1234567890123456789
        factor = 10_000_000_000
        clean, dust = strip_dust(raw, factor)

        assert clean % factor == 0
        assert clean + dust == raw
        assert dust == raw % factor

    def test_core_writer_limit_order_encoding(self):
        """Tests CoreWriter encoding with action header 0x01000001, scaled 1e8, and IOC tif=3."""
        order = HyperCoreAtomicArbSimulator.encode_core_writer_limit_order(
            asset_index=100,
            is_buy=True,
            limit_px=0.1250,
            size=10_000.0,
            reduce_only=False,
            encoded_tif=3,  # IOC
        )
        assert order["header"] == CORE_WRITER_LIMIT_ORDER_HEADER
        assert order["limit_px_1e8"] == int(0.1250 * 1e8)
        assert order["size_1e8"] == int(10_000.0 * 1e8)
        assert order["encoded_tif"] == 3
        assert order["gas_cost"] == 47_000

    def test_atomic_arbitrage_profitability_reversion(self):
        """Tests cross-venue atomic arbitrage and net profit evaluation."""
        sim = HyperCoreAtomicArbSimulator(min_profit_usdc=15.0)

        book = L2Book(symbol="PURR")
        book.set_level(0.1250, 500_000.0, Side.BUY)
        book.set_level(0.1260, 500_000.0, Side.SELL)
        sim.register_asset(100, "PURR", book)

        # Hyperswap cheap pool: spot = 0.1180
        pair = HyperswapReserves(
            pair_address="0xPool1",
            token0_symbol="PURR",
            token1_symbol="USDC",
            reserve0=1_000_000.0,
            reserve1=118_000.0,
        )
        sim.register_hyperswap_pool(pair)

        # Should execute Buy Hyperswap @ 0.118 -> Sell Core @ 0.125
        is_arb, telem, ord_arb = sim.evaluate_atomic_arbitrage(
            asset_index=100,
            pair_address="0xPool1",
            trade_size_usdc=5000.0,
        )
        assert is_arb is True
        assert telem["direction"] == "BUY_HYPERSWAP_SELL_CORE"
        assert telem["net_profit_usd"] > 15.0
        assert ord_arb is not None
        assert ord_arb.order_type == OrderType.TAKER_IOC

    def test_felix_cdp_liquidation_trigger(self):
        """Tests Felix CDP liquidation when CR < 110%."""
        sim = HyperCoreAtomicArbSimulator()
        book = L2Book(symbol="PURR")
        book.set_level(0.1250, 100_000.0, Side.BUY)
        sim.register_asset(100, "PURR", book)

        # CDP with $12,500 collateral, $12,000 debt => CR = 104.17% < 110%
        cdp = FelixCDP(
            cdp_id="cdp_test",
            user_address="0xBorrower",
            collateral_symbol="PURR",
            collateral_amount=100_000.0,
            debt_usdc=12_000.0,
        )
        sim.register_felix_cdp(cdp)

        is_liq, telem, ord_liq = sim.evaluate_felix_cdp_liquidation("cdp_test", asset_index=100)
        assert is_liq is True
        assert telem["cr_pct"] < 110.0
        assert telem["bonus_profit_usd"] > 0
        assert ord_liq is not None
