"""Regression and adversarial tests for v6.0 Portfolio-Wide Risk & Capital Allocation."""

from __future__ import annotations

import pathlib
import unittest

from src.polymarket_research.universal_arb_verifier import OpportunityClass
from src.polymarket_research.v6_restriction_and_capital_allocator import (
    CapitalReservationLedger,
    DynamicMarginalCapitalAllocator,
    ExecutionMode,
    ExposurePositionSpec,
    HierarchicalRiskBudgetConfig,
    OrderReservationStatus,
    PortfolioCandidateSpec,
    SleeveRiskConfig,
    aggregate_correlated_exposure,
    evaluate_correlated_worst_case_exposure,
)


def _cand(
    cid: str,
    *,
    family: str = "A",
    sleeve: str = "C1_BINARY_COMPLETE_SET",
    model_id: str = "M1",
    opp_class: OpportunityClass = OpportunityClass.CLASS_A,
    clusters: tuple[str, ...] = (),
    instruments: tuple[str, ...] = (),
    shares: float = 10.0,
    cap_per_share: float = 0.98,
    wc_edge: float = 0.02,
    exp_edge: float = 0.02,
    mat_h: float = 1.0,
    settle_h: float = 0.05,
    instant_merge: bool = False,
    mergeable_box: bool = False,
    event_id: str = "",
    market_family: str = "",
    underlying_asset: str = "",
    resolution_source: str = "",
    directional_sign: int = 0,
) -> PortfolioCandidateSpec:
    return PortfolioCandidateSpec(
        candidate_id=cid,
        family_code=family,
        sleeve_name=sleeve,
        opportunity_class=opp_class,
        cluster_keys=clusters,
        instrument_ids=instruments or (f"TOK_{cid}_Y", f"TOK_{cid}_N"),
        max_executable_shares=shares,
        capital_per_share_usd=cap_per_share,
        worst_case_net_payoff_per_share_usd=wc_edge,
        expected_net_payoff_per_share_usd=exp_edge,
        fees_and_conversion_per_share_usd=0.0,
        nominal_maturity_hours=mat_h,
        settlement_or_merge_hours=settle_h,
        can_instant_merge_or_recycle=instant_merge,
        is_same_condition_mergeable_box=mergeable_box,
        is_atomic_or_inventory_locked=True,
        model_id=model_id,
        event_id=event_id,
        market_family=market_family,
        underlying_asset=underlying_asset,
        resolution_source=resolution_source,
        directional_sign=directional_sign,
    )


class TestV6PortfolioRiskAllocator(unittest.TestCase):
    def test_01_reservation_ledger_pending_partial_fills_and_cancel(self) -> None:
        ledger = CapitalReservationLedger(total_wallet_cash_usd=50.0, safety_buffer_usd=2.0)
        self.assertAlmostEqual(ledger.available_deployable_cash_usd, 48.0, places=6)

        ok, msg, rec = ledger.reserve_order(
            reservation_id="ORD_1",
            market_id="MKT_1",
            instrument_id="TOK_1",
            family_code="A",
            sleeve_name="C1",
            requested_notional_usd=20.0,
            model_id="MOD_A",
            underlying_asset="BTC",
        )
        self.assertTrue(ok, msg)
        self.assertIsNotNone(rec)
        self.assertAlmostEqual(ledger.available_deployable_cash_usd, 28.0, places=6)

        # Duplicate reservation ID must be rejected
        ok_dup, msg_dup, _ = ledger.reserve_order(
            reservation_id="ORD_1",
            market_id="MKT_1",
            instrument_id="TOK_1",
            family_code="A",
            sleeve_name="C1",
            requested_notional_usd=5.0,
        )
        self.assertFalse(ok_dup)
        self.assertIn("DUPLICATE_ACTIVE_RESERVATION", msg_dup)

        # Partial fill of $12.00 where $8.00 already dropped from wallet cash on-chain
        ok_pf, st_pf = ledger.record_partial_fill(
            "ORD_1",
            delta_filled_notional_usd=12.0,
            collat_drop_delta_usd=8.0,
        )
        self.assertTrue(ok_pf)
        self.assertEqual(st_pf, OrderReservationStatus.PARTIALLY_FILLED.value)
        # Unfilled = $8.00, matched_unsettled = $12.00, synced = $8.00 -> reserved = 8 + (12 - 8) = $12.00
        self.assertAlmostEqual(ledger.total_reserved_cash_usd, 12.0, places=6)
        self.assertAlmostEqual(ledger.available_deployable_cash_usd, 36.0, places=6)

        # Cancelling ORD_1 releases only unfilled $8.00; $4.00 unsynced matched remains tracked
        ok_rel, released = ledger.release_reservation("ORD_1", reason="CANCELLED")
        self.assertTrue(ok_rel)
        self.assertAlmostEqual(released, 8.0, places=6)
        self.assertAlmostEqual(ledger.total_reserved_cash_usd, 4.0, places=6)

        # Settling clears remaining reservation
        ok_set, released_set = ledger.release_reservation("ORD_1", reason="SETTLED")
        self.assertTrue(ok_set)
        self.assertAlmostEqual(released_set, 4.0, places=6)
        self.assertAlmostEqual(ledger.total_reserved_cash_usd, 0.0, places=6)
        self.assertAlmostEqual(ledger.available_deployable_cash_usd, 48.0, places=6)

    def test_02_concurrent_instant_merge_cannot_overcommit_wallet_cash(self) -> None:
        ledger = CapitalReservationLedger(total_wallet_cash_usd=47.38)
        alloc = DynamicMarginalCapitalAllocator(max_cluster_nav_pct=0.50)

        # Three simultaneous $20 instant-merge candidates ($60 total demand > $47.38 wallet cash)
        cands = [
            _cand(
                f"C1_SIM_{i}",
                shares=20.0,
                cap_per_share=1.0,
                wc_edge=0.01,
                exp_edge=0.01,
                mat_h=0.5,
                settle_h=0.01,
                instant_merge=True,
                mergeable_box=True,
                clusters=(f"COND:MKT_{i}",),
            )
            for i in range(3)
        ]
        res = alloc.allocate(
            cands,
            mode=ExecutionMode.LIVE,
            deployable_liquid_cash_usd=47.38,
            reconciled_nav_usd=47.38,
            reservation_ledger=ledger,
        )
        # Must NOT exceed $47.38 total deployed cash
        self.assertLessEqual(res.deployed_cash_usd, 47.38 + 1e-6)
        self.assertGreaterEqual(ledger.available_deployable_cash_usd, 0.0)
        self.assertAlmostEqual(ledger.total_reserved_cash_usd, res.deployed_cash_usd, places=4)

    def test_03_stale_cash_argument_cannot_bypass_ledger_pending_orders(self) -> None:
        ledger = CapitalReservationLedger(total_wallet_cash_usd=47.38)
        ok, _, _ = ledger.reserve_order(
            reservation_id="PENDING_BTC_1",
            market_id="MKT_BTC_1",
            instrument_id="TOK_BTC_1",
            family_code="A",
            sleeve_name="D1_SAME_ORACLE",
            requested_notional_usd=40.0,
            underlying_asset="BTC",
        )
        self.assertTrue(ok)

        alloc = DynamicMarginalCapitalAllocator(max_cluster_nav_pct=0.50)
        cand = _cand(
            "NEW_ETH_1",
            shares=15.0,
            cap_per_share=1.0,
            wc_edge=0.02,
            exp_edge=0.02,
            underlying_asset="ETH",
        )
        # Caller passes stale $47.38 cash, but ledger only has $7.38 available
        res = alloc.allocate(
            [cand],
            mode=ExecutionMode.LIVE,
            deployable_liquid_cash_usd=47.38,
            reconciled_nav_usd=47.38,
            reservation_ledger=ledger,
        )
        self.assertAlmostEqual(res.initial_deployable_cash_usd, 7.38, places=4)
        self.assertLessEqual(res.deployed_cash_usd, 7.38 + 1e-6)

    def test_04_hierarchical_risk_budgets_family_sleeve_model_and_market(self) -> None:
        cfg = HierarchicalRiskBudgetConfig(
            portfolio_max_utilization_pct=0.90,
            family_max_nav_pct={"FAM_B": 0.20},
            sleeve_configs={
                "SL_DISABLED": SleeveRiskConfig(sleeve_name="SL_DISABLED", enabled=False),
                "SL_FAST_ONLY": SleeveRiskConfig(
                    sleeve_name="SL_FAST_ONLY",
                    min_bps_per_hour=50.0,
                    max_nav_pct=0.30,
                    max_concurrent_positions=1,
                    max_single_market_nav_pct=0.15,
                ),
            },
            model_max_nav_pct={"MOD_CAPPED": 0.12},
        )
        alloc = DynamicMarginalCapitalAllocator(max_cluster_nav_pct=0.50)
        cands = [
            _cand("C_DISABLED", sleeve="SL_DISABLED", shares=10.0, cap_per_share=1.0),
            _cand("C_SLOW", sleeve="SL_FAST_ONLY", shares=10.0, cap_per_share=1.0, wc_edge=0.001, exp_edge=0.001, mat_h=5.0),
            _cand("C_FAST_1", family="FAM_B", sleeve="SL_FAST_ONLY", model_id="MOD_CAPPED", shares=20.0, cap_per_share=1.0, wc_edge=0.02, exp_edge=0.02, mat_h=1.0, clusters=("E1",)),
            _cand("C_FAST_2", family="FAM_B", sleeve="SL_FAST_ONLY", model_id="MOD_CAPPED", shares=20.0, cap_per_share=1.0, wc_edge=0.02, exp_edge=0.02, mat_h=1.0, clusters=("E2",)),
        ]
        res = alloc.allocate(
            cands,
            mode=ExecutionMode.LIVE,
            deployable_liquid_cash_usd=100.0,
            reconciled_nav_usd=100.0,
            risk_budget_config=cfg,
        )
        dec = {d.candidate_id: d for d in res.decisions}
        self.assertFalse(dec["C_DISABLED"].accepted)
        self.assertIn("SLEEVE_DISABLED_BY_RISK_CONFIG", dec["C_DISABLED"].rejection_reason)
        self.assertFalse(dec["C_SLOW"].accepted)
        self.assertIn("SLEEVE_MIN_BPS_HR_NOT_MET", dec["C_SLOW"].rejection_reason)
        self.assertTrue(dec["C_FAST_1"].accepted)
        # Model cap 12% of $100 = $12.00
        self.assertLessEqual(dec["C_FAST_1"].allocated_capital_usd, 12.0 + 1e-6)
        self.assertFalse(dec["C_FAST_2"].accepted)
        self.assertIn("SLEEVE_MAX_CONCURRENT_POSITIONS_REACHED", dec["C_FAST_2"].rejection_reason)

    def test_05_structured_correlation_and_hidden_directional_correlation(self) -> None:
        existing = [
            ExposurePositionSpec(
                position_id="POS_BTC_15M",
                cluster_keys=(),
                capital_committed_usd=7.0,
                underlying_asset="BTC",
                event_id="BTC_DAILY",
                market_family="CRYPTO_DIRECTIONAL",
                resolution_source="BINANCE_SPOT",
                directional_sign=1,
                sleeve_name="SLEEVE_15M",
            ),
            ExposurePositionSpec(
                position_id="POS_BTC_BARRIER",
                cluster_keys=(),
                capital_committed_usd=5.0,
                underlying_asset="BTC",
                event_id="BTC_WEEKLY",
                market_family="BARRIER_MONO",
                resolution_source="BINANCE_SPOT",
                directional_sign=1,
                sleeve_name="SLEEVE_BARRIER",
            ),
        ]
        summary = aggregate_correlated_exposure(existing)
        self.assertAlmostEqual(summary.by_underlying_asset_usd["BTC"], 12.0, places=6)
        self.assertAlmostEqual(summary.directional_net_by_asset_usd["BTC"], 12.0, places=6)
        self.assertTrue(any("HIDDEN_DIRECTIONAL_CORRELATION:BTC:LONG" in w for w in summary.hidden_correlation_warnings))

        # A 3rd BTC candidate with empty cluster_keys must still be blocked by ASSET:BTC CWCE
        cand_btc = ExposurePositionSpec(
            position_id="POS_BTC_3",
            cluster_keys=(),
            capital_committed_usd=3.0,
            underlying_asset="BTC",
        )
        verdict = evaluate_correlated_worst_case_exposure(cand_btc, existing, reconciled_nav_usd=50.0, max_cluster_nav_pct=0.15)
        self.assertFalse(verdict.allowed)
        self.assertEqual(verdict.binding_cluster_key, "ASSET:BTC")

        # Adversarial: mergeable boxes with non-zero unwind risk cannot bypass cap_usd
        m_existing = [
            ExposurePositionSpec(
                position_id="M_1",
                cluster_keys=("EVT:X",),
                capital_committed_usd=20.0,
                is_same_condition_mergeable_box=True,
                partial_leg_unwind_risk_usd=6.0,
            )
        ]
        m_cand = ExposurePositionSpec(
            position_id="M_2",
            cluster_keys=("EVT:X",),
            capital_committed_usd=20.0,
            is_same_condition_mergeable_box=True,
            partial_leg_unwind_risk_usd=3.0,
        )
        v_m = evaluate_correlated_worst_case_exposure(m_cand, m_existing, reconciled_nav_usd=50.0, max_cluster_nav_pct=0.15)
        self.assertFalse(v_m.allowed)

    def test_06_kmia_d001_non_interference_and_lf_hygiene(self) -> None:
        alloc = DynamicMarginalCapitalAllocator()
        kmia_cand = _cand("KMIA_LIVE_PROBE", clusters=("6707503",), shares=10.0, cap_per_share=0.50)
        res = alloc.allocate([kmia_cand], mode=ExecutionMode.LIVE, deployable_liquid_cash_usd=47.38, reconciled_nav_usd=47.52)
        self.assertFalse(res.decisions[0].accepted)
        self.assertIn("D001", res.decisions[0].rejection_reason.upper())

        for rel in (
            "src/polymarket_research/v6_restriction_and_capital_allocator.py",
            "src/polymarket_research/polymarket_live_harvester.py",
            "src/polymarket_research/riskless_protocol_v2_expansion.py",
            "tests/test_v6_portfolio_risk_allocator.py",
            "tests/test_phase4_latency_optimizations.py",
        ):
            raw = pathlib.Path(rel).read_bytes()
            self.assertNotIn(b"\r\n", raw, f"CRLF found in {rel}")

    def test_07_harvester_sync_capital_reservation_ledger_and_kmia_exclusion(self) -> None:
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            check_per_event_concentration_cap,
            evaluate_candidate_v6_cwce_and_reservation,
        )

        harv = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        harv.dry_run = False
        harv._last_known_collateral = 47.38
        harv.active_positions = {
            "WS_SNIPE_Miami_KMIA_242960": {
                "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                "market_id": "6707503",
                "token_id": "tok_kmia_no",
                "asset": "KMIA",
                "notional_usd": 33.95,
                "remaining_shares": 35.0,
                "best_bid": 0.002,
                "umaResolutionStatus": "disputed",
                "is_single_leg_lock": True,
                "candle_expiry_ts": 1762500000.0,
            },
            "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898",
                "market_id": "6707502",
                "token_id": "tok_kmia_yes",
                "asset": "KMIA",
                "notional_usd": 16.56,
                "remaining_shares": 17.0,
                "best_bid": 0.004,
                "umaResolutionStatus": "disputed",
                "box_type": "MULTI_LEG_RESIDUAL",
                "candle_expiry_ts": 1762500000.0,
            },
            "HEALTHY_BTC_POS": {
                "trade_id": "HEALTHY_BTC_POS",
                "market_id": "900100",
                "token_id": "tok_btc_up",
                "asset": "BTC",
                "sleeve": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
                "notional_usd": 4.00,
                "remaining_shares": 5.0,
                "best_bid": 0.80,
                "status": "POSITION_CONFIRMED",
            },
        }
        harv.pending_entry_intents = {
            "MKR_INTENT_1": {
                "market_id": "900200",
                "token_id": "tok_eth_up",
                "asset": "ETH",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "posted_notional_usd": 15.0,
                "notional_usd": 9.0,           # $9.00 unfilled resting
                "matched_notional_usd": 6.0,   # $6.00 matched
                "collat_drop_usd": 4.0,        # $4.00 already dropped from wallet cash on-chain
                "live_maker_anchor_inflight": True,
            }
        }
        harv._active_maker_orders = {
            "MKR_ORDER_2": {
                "market_id": "900300",
                "token_id": "tok_sol_up",
                "asset": "SOL",
                "sleeve": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                "notional_usd": 5.0,
            }
        }

        ledger = harv.sync_capital_reservation_ledger(now_ts=1763000000.0)
        # Reserved cash = MKR_INTENT_1 ($9 unfilled + ($6 matched - $4 synced) = $11) + MKR_ORDER_2 ($5) = $16.00
        self.assertAlmostEqual(ledger.total_reserved_cash_usd, 16.00, places=4)
        self.assertAlmostEqual(ledger.available_deployable_cash_usd, 47.38 - 16.00, places=4)
        # Non-frozen open positions must strictly exclude the $50.51 frozen KMIA positions
        self.assertAlmostEqual(harv._non_frozen_open_positions_usd, 4.00, places=4)
        self.assertAlmostEqual(harv._frozen_disputed_positions_usd, 50.51, places=4)
        # Reconciled NAV = $47.38 cash + $4.00 healthy BTC + $4.00 synced maker escrow + $0.138 KMIA bid = $55.518 (<< $97.89 book)
        self.assertLess(harv._reconciled_non_frozen_sizing_nav_usd, 56.0)

        # 1. D-001 KMIA candidate must be blocked immediately
        kmia_chk = harv.check_pre_trade_reservation_and_budget(
            {"candidate_id": "KMIA_TRY", "market_id": "6707503", "asset": "KMIA"},
            requested_notional_usd=5.0,
            now_ts=1763000000.0,
        )
        self.assertFalse(kmia_chk["allowed"])
        self.assertIn("KMIA", kmia_chk["reason"].upper())

        # 2a. Paused sleeve in governance config (S2_RTDS_EXACT_TWAP_INTEGRATOR) is blocked by HierarchicalRiskBudgetConfig
        s2_paused_chk = evaluate_candidate_v6_cwce_and_reservation(
            harv,
            {
                "candidate_id": "S2_PAUSED_CHECK",
                "market_id": "900104",
                "token_id": "tok_btc_s2",
                "asset": "BTC",
                "sleeve": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
                "box_type": "SINGLE_LEG_LOCK",
            },
            requested_notional_usd=5.0,
            now_ts=1763000000.0,
        )
        self.assertFalse(s2_paused_chk["allowed"])
        self.assertIn("SLEEVE_DISABLED_BY_RISK_CONFIG:S2_RTDS_EXACT_TWAP_INTEGRATOR", s2_paused_chk["reason"])

        # 2b. Correlated BTC candidate on enabled sleeve exceeding 15% reconciled NAV ($55.518 * 0.15 = $8.3277; $4.00 already used by HEALTHY_BTC_POS)
        btc_over_chk = evaluate_candidate_v6_cwce_and_reservation(
            harv,
            {
                "candidate_id": "BTC_OVER_CWCE",
                "market_id": "900105",
                "token_id": "tok_btc_2",
                "asset": "BTC",
                "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                "box_type": "SINGLE_LEG_LOCK",
            },
            requested_notional_usd=5.0,
            now_ts=1763000000.0,
        )
        self.assertFalse(btc_over_chk["allowed"])
        self.assertIn("CORRELATED_WORST_CASE_CAP_EXCEEDED:ASSET:BTC", btc_over_chk["reason"])

        # 3. Same-condition mergeable C1 box has $0 oracle directional/dispute risk and passes CWCE + reserves capital
        c1_ok_chk = harv.check_pre_trade_reservation_and_budget(
            {
                "candidate_id": "C1_MERGE_OK",
                "market_id": "900400",
                "leg_a_token_id": "tok_xrp_y",
                "leg_b_token_id": "tok_xrp_n",
                "leg_a_condition_id": "0xcond_xrp",
                "leg_b_condition_id": "0xcond_xrp",
                "asset": "XRP",
                "sleeve_source": "C1_BINARY_COMPLETE_SET",
                "box_type": "COMPLETE_SET",
                "is_same_condition_mergeable_box": True,
            },
            requested_notional_usd=10.0,
            now_ts=1763000000.0,
            reserve_on_accept=True,
        )
        self.assertTrue(c1_ok_chk["allowed"], c1_ok_chk["reason"])
        self.assertIsNotNone(c1_ok_chk["reservation_record"])
        self.assertAlmostEqual(ledger.available_deployable_cash_usd, 47.38 - 16.00 - 10.00, places=4)

        # 4. HierarchicalRiskBudgetConfig sleeve disablement & check_per_event_concentration_cap hook
        harv.hierarchical_risk_budget_config = HierarchicalRiskBudgetConfig(
            sleeve_configs={
                "PAUSED_TEST_SLEEVE": SleeveRiskConfig(sleeve_name="PAUSED_TEST_SLEEVE", enabled=False),
            },
            default_market_max_nav_pct=0.15,
        )
        harv.enforce_v6_cwce_and_reservation = True
        harv.enforce_event_concentration_cap = True
        ok_evt, rsn_evt, _, _ = check_per_event_concentration_cap(
            harv,
            {
                "candidate_id": "PAUSED_CAND",
                "market_id": "900500",
                "event_id": "EVT_500",
                "sleeve": "PAUSED_TEST_SLEEVE",
                "notional_usd": 5.0,
            },
            now_ts=1763000000.0,
        )
        self.assertFalse(ok_evt)
        self.assertIn("SLEEVE_DISABLED_BY_RISK_CONFIG:PAUSED_TEST_SLEEVE", rsn_evt)


if __name__ == "__main__":
    unittest.main()
