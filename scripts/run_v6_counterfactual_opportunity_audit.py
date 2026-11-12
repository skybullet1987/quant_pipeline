#!/usr/bin/env python3
"""
Reproducible Counterfactual Opportunity-Cost & Capital Efficiency Benchmark
(`scripts/run_v6_counterfactual_opportunity_audit.py`).

Evaluates real recorded Dominus full-universe telemetry (`data/full_throttle/`) and
reconciled wallet/ledger state (`$48.70` liquid `pUSD`, `$48.83` mark-to-bid NAV,
`$50.51` quarantined `KMIA` disputed cost, `79W / 0L` `+$18.2461` pure-riskless live track record)
to quantify:
  1. Measured realized financial impacts vs simulated counterfactual opportunity costs across R-01..R-44.
  2. Before (`v5.0/v5.1` static cliffs + allowlists + blind exemptions) vs After (`v6.0` Dynamic
     Marginal Capital Allocator + Mathematical Proof Admission + CWCE + Loss-Cause Controller)
     across `$48.70` (live cash), `$99.21` (if `KMIA` settles at par), `$253` (Stage G), and `$500` NAV.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.polymarket_research.universal_arb_verifier import OpportunityClass
from src.polymarket_research.v6_restriction_and_capital_allocator import (
    DynamicMarginalCapitalAllocator,
    ExecutionMode,
    FIXED_DAILY_VM_COST_USD,
    FIXED_HOURLY_VM_COST_USD,
    FIXED_MONTHLY_VM_COST_USD,
    LossCauseAwareCapitalController,
    PortfolioCandidateSpec,
    RECONCILED_NOV11_BOOK_EQUITY_USD,
    RECONCILED_NOV11_KMIA_DISPUTED_BID_USD,
    RECONCILED_NOV11_KMIA_DISPUTED_COST_USD,
    RECONCILED_NOV11_LIQUID_PUSD_USD,
    RECONCILED_NOV11_MARK_TO_BID_NAV_USD,
    evaluate_disputed_inventory_recovery_options,
    evaluate_evidence_based_venue_readiness,
    reconcile_infrastructure_expenses,
    simulate_legacy_v5_cliff_allocator,
    validate_wallet_split_merge_capabilities,
)


def build_representative_mixed_opportunity_batch() -> List[PortfolioCandidateSpec]:
    """
    Constructs a deterministic, realistic arrival batch calibrated to actual observed Dominus
    telemetry (`PROFIT_SCORECARD.md` 107 D1 collateral-starvation skips, `scans_d_to_i` 3 `CLASS_B`
    boxes, `alpha124` `CAL1` 12W/0L boxes, `C1` gasless merge boxes, and `BOND1` carries):
      - `CAND_0_TRAP_30D_DOM`: 30-day (`720h`) `D1_SAME_ORACLE_DOMINANCE_BOX` earning only `30 bps`
        (`0.0417 bps/hr`!). Arrives FIRST and greedily locks cash in v5 because `DOMINANCE` was
        unconditionally exempted from `passes_capital_velocity_hurdle` (`holistic_strategy_governance.py:838`)!
      - `CAND_1_C1_GASLESS_MERGE`: Same-condition `C1_BINARY_COMPLETE_SET` (`$0.9935` net cost, `65 bps`
        instant gasless Relayer V2 merge in `18s` = `0.005h` -> `13,000 bps/hr`, `$0` oracle exposure!).
      - `CAND_2_CAL1_FEE_BEARING_PROVEN`: Fee-bearing `CAL1` deadline box (`4%` politics fee schedule,
        exact fee-adjusted net cost `$0.9860` -> `+140 bps` worst-case guaranteed payoff over `6.0h` =
        `23.33 bps/hr`). Blocked in v5 by `PURE_RISKLESS_CAL1_COND1_REQUIRES_ZERO_FEE` (`R-02`)!
      - `CAND_3_DUP_EQUIV_2LEG`: Mathematically proven cross-event duplicate equivalence `CLASS_B` box
        (`FAMILY_I` pattern from `scans_d_to_i`, net cost `$0.9880` -> `+120 bps` over `8.0h` = `15.0 bps/hr`).
        Blocked in v5 by `PURE_RISKLESS_SLEEVE_NOT_ALLOWLISTED` (`R-02`)!
      - `CAND_4_IDLE_CARRY_26H`: Verified `26.0h` `COND1_MACRO_PARTITION_BOX` (`0%` fee, net cost `$0.9720`
        -> `+280 bps` = `10.77 bps/hr`). Blocked in v5 by the rigid `24.0h` `seed_max_lockup_hours` cliff
        (`R-09`/`R-43`), leaving remainder cash idle at `0.0 bps/hr`!
      - `CAND_5_SUB500_3LEG_SEQ`: Non-atomic `3`-leg sequential bundle (`+190 bps`, `partial_fill_prob=0.18`,
        `unwind_loss=0.04`). Admitted in `SHADOW` (`R-40`) to measure true post-legging EV, strictly
        quarantined in `LIVE` below `$500` NAV (`D-007`).
    """
    return [
        PortfolioCandidateSpec(
            candidate_id="CAND_0_TRAP_30D_DOM",
            family_code="F",
            sleeve_name="D1_SAME_ORACLE_DOMINANCE_BOX",
            opportunity_class=OpportunityClass.CLASS_B,
            cluster_keys=("EVT:CRYPTO_DEC_EXPIRY",),
            instrument_ids=("TOK_TRAP_A", "TOK_TRAP_B"),
            max_executable_shares=45.0,
            capital_per_share_usd=0.9970,
            worst_case_net_payoff_per_share_usd=0.0030,
            expected_net_payoff_per_share_usd=0.0040,
            fees_and_conversion_per_share_usd=0.0,
            nominal_maturity_hours=720.0,
            settlement_or_merge_hours=1.0,
            can_instant_merge_or_recycle=False,
            partial_fill_prob=0.02,
            unwind_loss_per_share_if_partial_usd=0.01,
        ),
        PortfolioCandidateSpec(
            candidate_id="CAND_1_C1_GASLESS_MERGE",
            family_code="A",
            sleeve_name="C1_BINARY_COMPLETE_SET",
            opportunity_class=OpportunityClass.CLASS_A,
            cluster_keys=("COND:0xSAME_BINARY_1",),
            instrument_ids=("TOK_C1_YES", "TOK_C1_NO"),
            max_executable_shares=22.0,
            capital_per_share_usd=0.9935,
            worst_case_net_payoff_per_share_usd=0.0065,
            expected_net_payoff_per_share_usd=0.0065,
            fees_and_conversion_per_share_usd=0.0,
            nominal_maturity_hours=120.0,
            settlement_or_merge_hours=0.005,
            can_instant_merge_or_recycle=True,
            is_same_condition_mergeable_box=True,
            is_atomic_or_inventory_locked=True,
        ),
        PortfolioCandidateSpec(
            candidate_id="CAND_2_CAL1_FEE_BEARING_PROVEN",
            family_code="E",
            sleeve_name="CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
            opportunity_class=OpportunityClass.CLASS_B,
            cluster_keys=("EVT:CAL_DEADLINE_1",),
            instrument_ids=("TOK_CAL_EARLY_YES", "TOK_CAL_LATE_NO"),
            max_executable_shares=15.0,
            capital_per_share_usd=0.9860,
            worst_case_net_payoff_per_share_usd=0.0140,
            expected_net_payoff_per_share_usd=0.0180,
            fees_and_conversion_per_share_usd=0.0038,
            nominal_maturity_hours=6.0,
            settlement_or_merge_hours=0.5,
            partial_fill_prob=0.03,
            unwind_loss_per_share_if_partial_usd=0.012,
        ),
        PortfolioCandidateSpec(
            candidate_id="CAND_3_DUP_EQUIV_2LEG",
            family_code="I",
            sleeve_name="FT_I_PROVEN_DUPLICATE_EQUIVALENCE",
            opportunity_class=OpportunityClass.CLASS_B,
            cluster_keys=("EVT:DUP_PAIR_1",),
            instrument_ids=("TOK_DUP_1_YES", "TOK_DUP_2_NO"),
            max_executable_shares=15.0,
            capital_per_share_usd=0.9880,
            worst_case_net_payoff_per_share_usd=0.0120,
            expected_net_payoff_per_share_usd=0.0120,
            fees_and_conversion_per_share_usd=0.0015,
            nominal_maturity_hours=8.0,
            settlement_or_merge_hours=0.5,
            partial_fill_prob=0.03,
            unwind_loss_per_share_if_partial_usd=0.010,
        ),
        PortfolioCandidateSpec(
            candidate_id="CAND_4_IDLE_CARRY_26H",
            family_code="D",
            sleeve_name="COND1_MACRO_PARTITION_BOX",
            opportunity_class=OpportunityClass.CLASS_B,
            cluster_keys=("EVT:MACRO_CPI_WINDOW",),
            instrument_ids=("TOK_COND_A", "TOK_COND_B"),
            max_executable_shares=15.0,
            capital_per_share_usd=0.9720,
            worst_case_net_payoff_per_share_usd=0.0280,
            expected_net_payoff_per_share_usd=0.0280,
            fees_and_conversion_per_share_usd=0.0,
            nominal_maturity_hours=25.5,
            settlement_or_merge_hours=0.5,
            partial_fill_prob=0.02,
            unwind_loss_per_share_if_partial_usd=0.010,
        ),
        PortfolioCandidateSpec(
            candidate_id="CAND_5_SUB500_3LEG_SEQ",
            family_code="B",
            sleeve_name="MULTI_OUTCOME_3LEG_SLATE",
            opportunity_class=OpportunityClass.CLASS_B,
            cluster_keys=("EVT:SLATE_3WAY",),
            instrument_ids=("TOK_3W_1", "TOK_3W_2", "TOK_3W_3"),
            max_executable_shares=20.0,
            capital_per_share_usd=0.9810,
            worst_case_net_payoff_per_share_usd=0.0190,
            expected_net_payoff_per_share_usd=0.0190,
            fees_and_conversion_per_share_usd=0.0,
            nominal_maturity_hours=4.0,
            settlement_or_merge_hours=0.5,
            sequential_clob_legs=3,
            is_atomic_or_inventory_locked=False,
            partial_fill_prob=0.18,
            unwind_loss_per_share_if_partial_usd=0.040,
        ),
    ]


def load_empirical_full_throttle_stats() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    dash_p = REPO_ROOT / "data" / "full_throttle" / "pipeline" / "dashboard_latest.json"
    if dash_p.exists():
        d = json.loads(dash_p.read_text(encoding="utf-8"))
        out["full_throttle_universe"] = d.get("section_1_universe_coverage", {})
        out["full_throttle_opportunity_metrics"] = d.get("section_2_opportunity_metrics", {})
        out["full_throttle_dormant_store"] = {
            k: v
            for k, v in (d.get("section_2c_dormant_opportunity_store") or {}).items()
            if k != "closest_near_misses"
        }
    ab_p = REPO_ROOT / "data" / "full_throttle" / "scans_ab_c_j" / "scan_summary.json"
    if ab_p.exists():
        ab = json.loads(ab_p.read_text(encoding="utf-8"))
        out["scan_ab_c_j_universe"] = ab.get("universe_coverage", {})
        out["scan_ab_c_j_summary"] = ab.get("overall_summary_at_live_nav", {})
    di_p = REPO_ROOT / "data" / "full_throttle" / "scans_d_to_i" / "scan_summary.json"
    if di_p.exists():
        di = json.loads(di_p.read_text(encoding="utf-8"))
        out["scan_d_to_i_classes"] = di.get("class_distribution", {})
        out["scan_d_to_i_rule_mismatches_prevented"] = di.get("total_rule_mismatch_rejections_prevented", 0)
    return out


def run_counterfactual_audit() -> Dict[str, Any]:
    batch = build_representative_mixed_opportunity_batch()
    allocator = DynamicMarginalCapitalAllocator()

    tier_comparisons: Dict[str, Any] = {}
    for label, nav_usd in (
        ("live_cash_48_70", RECONCILED_NOV11_LIQUID_PUSD_USD),
        ("post_kmia_par_99_21", RECONCILED_NOV11_BOOK_EQUITY_USD),
        ("stage_g_unlock_253_00", 253.00),
        ("multileg_unlock_500_00", 500.00),
    ):
        legacy_v5 = simulate_legacy_v5_cliff_allocator(
            batch, deployable_liquid_cash_usd=nav_usd, reconciled_nav_usd=nav_usd
        )
        v6_live = allocator.allocate(
            batch,
            mode=ExecutionMode.LIVE,
            deployable_liquid_cash_usd=nav_usd,
            reconciled_nav_usd=nav_usd,
            jurisdiction="FI_AUTHORIZED_TEST",
            venue_live_authorized=True,
            live_promotion_approved=True,
        )
        v6_shadow = allocator.allocate(
            batch,
            mode=ExecutionMode.SHADOW,
            deployable_liquid_cash_usd=nav_usd,
            reconciled_nav_usd=nav_usd,
        )
        v6_research = allocator.allocate(
            batch,
            mode=ExecutionMode.RESEARCH,
            deployable_liquid_cash_usd=nav_usd,
            reconciled_nav_usd=nav_usd,
        )
        tier_comparisons[label] = {
            "nav_usd": round(nav_usd, 2),
            "legacy_v5_live_rnv_usd": legacy_v5["total_realizable_net_value_usd"],
            "legacy_v5_deployed_usd": legacy_v5["deployed_cash_usd"],
            "legacy_v5_accepted_ids": legacy_v5["accepted_candidate_ids"],
            "legacy_v5_rejections": legacy_v5["rejected_counts"],
            "v6_live_rnv_usd": v6_live.total_realizable_net_value_usd,
            "v6_live_mrnv_usd": v6_live.total_marginal_realizable_net_value_usd,
            "v6_live_floor_pnl_usd": v6_live.total_worst_case_guaranteed_floor_pnl_usd,
            "v6_live_deployed_usd": v6_live.deployed_cash_usd,
            "v6_live_accepted_ids": [d.candidate_id for d in v6_live.decisions if d.accepted],
            "v6_shadow_accepted_ids": [d.candidate_id for d in v6_shadow.decisions if d.accepted],
            "v6_research_accepted_ids": [d.candidate_id for d in v6_research.decisions if d.accepted],
            "net_rnv_uplift_per_batch_usd": round(
                v6_live.total_realizable_net_value_usd - legacy_v5["total_realizable_net_value_usd"], 6
            ),
        }

    # R-01 Loss-cause controller comparison
    lcc = LossCauseAwareCapitalController()
    kmia_zero_writeoff = lcc.evaluate(
        liquid_pusd_usd=RECONCILED_NOV11_LIQUID_PUSD_USD,
        quarantined_disputed_cost_usd=0.0,
        quarantined_disputed_bid_usd=0.0,
        baseline_quarantined_disputed_cost_usd=RECONCILED_NOV11_KMIA_DISPUTED_COST_USD,
        post_baseline_closed_riskless_pnls_usd=[0.18, 0.14],
    )
    real_legging_bug_above_30 = lcc.evaluate(
        liquid_pusd_usd=47.05,
        quarantined_disputed_cost_usd=RECONCILED_NOV11_KMIA_DISPUTED_COST_USD,
        quarantined_disputed_bid_usd=RECONCILED_NOV11_KMIA_DISPUTED_BID_USD,
        post_baseline_closed_riskless_pnls_usd=[-1.65],
    )

    # R-10 Infra reconciliation over 14-day (336h) post-lock riskless window (+$18.2461 realized across 79 wins)
    infra_14d = reconcile_infrastructure_expenses(
        window_hours=336.0,
        realized_trading_net_pnl_usd=18.246110,
        liquid_nav_usd=RECONCILED_NOV11_LIQUID_PUSD_USD,
        hourly_vm_rate_usd=FIXED_HOURLY_VM_COST_USD,
        ai_billing_mode="subscription_flat",
        clips_executed_in_window=79,
        legacy_intraday_vm_hours_reported=7.27,  # 07:16 UTC snapshot distortion
    )

    # R-44 KMIA objective EV vs distressed sale
    kmia_ev = evaluate_disputed_inventory_recovery_options()

    # R-21 Wallet split/merge matrix
    wallet_matrix = {
        f"sig{sig}_{gen}": {
            "merge_supported": cap.merge_supported,
            "batch_merge_supported": cap.batch_merge_supported,
            "effective_recycle_lockup_hours": cap.effective_recycle_lockup_hours,
            "defects": list(cap.verified_constraints_and_defects),
        }
        for sig in (0, 2, 3)
        for gen in ("CTF_V1_PUSD", "CTF_V1_LEGACY_USDCE", "PROTOCOL_V2_POSITION_MANAGER")
        for cap in (validate_wallet_split_merge_capabilities(signature_type=sig, protocol_generation=gen),)
    }

    # R-42 ForecastEx actual telemetry vs high-evidence canary comparison
    fex_actual = evaluate_evidence_based_venue_readiness(
        venue_or_sleeve="forecastex_current_snapshot",
        uncontaminated_live_l2_samples=600,
        distinct_liquidity_regimes_observed=1,
        observed_live_hours=1.5,
        uptime_pct=100.0,
        api_error_rate_pct=0.0,
        p99_latency_ms=623.85,
        double_zero_or_clause_incidents=0,
        post_delay_simulated_trades=0,
        post_delay_net_executable_pnl_usd=0.0,
        settlement_and_custody_lifecycle_tested=False,
    )
    high_ev_72h = evaluate_evidence_based_venue_readiness(
        venue_or_sleeve="regulated_venue_72h_high_evidence",
        uncontaminated_live_l2_samples=3_400,
        distinct_liquidity_regimes_observed=4,
        observed_live_hours=72.0,
        uptime_pct=99.8,
        api_error_rate_pct=0.2,
        p99_latency_ms=410.0,
        double_zero_or_clause_incidents=0,
        post_delay_simulated_trades=38,
        post_delay_net_executable_pnl_usd=6.42,
        settlement_and_custody_lifecycle_tested=True,
    )

    return {
        "reconciled_balance_sheet": {
            "liquid_pusd_usd": RECONCILED_NOV11_LIQUID_PUSD_USD,
            "mark_to_bid_nav_usd": RECONCILED_NOV11_MARK_TO_BID_NAV_USD,
            "book_equity_usd": RECONCILED_NOV11_BOOK_EQUITY_USD,
            "quarantined_kmia_cost_usd": RECONCILED_NOV11_KMIA_DISPUTED_COST_USD,
            "quarantined_kmia_bid_usd": RECONCILED_NOV11_KMIA_DISPUTED_BID_USD,
            "fixed_monthly_vm_usd": FIXED_MONTHLY_VM_COST_USD,
            "fixed_daily_vm_usd": FIXED_DAILY_VM_COST_USD,
            "fixed_hourly_vm_usd": FIXED_HOURLY_VM_COST_USD,
        },
        "empirical_universe_telemetry": load_empirical_full_throttle_stats(),
        "allocator_before_vs_after_by_nav": tier_comparisons,
        "r01_loss_cause_verification": {
            "kmia_writeoff_halts_trading": kmia_zero_writeoff.halted,
            "legging_anomaly_at_47_05_halts_trading": real_legging_bug_above_30.halted,
            "legging_anomaly_reasons": list(real_legging_bug_above_30.halt_reasons),
        },
        "r10_infra_reconciliation_14d": {
            "true_marginal_trading_profit_usd": infra_14d.true_marginal_trading_profit_usd,
            "sunk_fixed_vm_14d_usd": infra_14d.sunk_fixed_vm_cost_usd,
            "full_cost_net_economic_profit_usd": infra_14d.full_cost_net_economic_profit_usd,
            "legacy_midnight_distorted_net_usd": infra_14d.legacy_accountant_distorted_net_usd,
            "double_counted_error_eliminated_usd": infra_14d.double_counted_error_eliminated_usd,
            "breakeven_bps_per_hr_at_48_70": infra_14d.portfolio_breakeven_bps_per_hr_on_liquid_nav,
        },
        "r44_kmia_recovery_evaluation": kmia_ev,
        "r21_wallet_capability_matrix": wallet_matrix,
        "r42_evidence_readiness_comparison": {
            "forecastex_current": {
                "ready": fex_actual.ready_for_owner_canary_proposal,
                "score_pct": fex_actual.evidence_score_pct,
                "deficiencies": list(fex_actual.blocking_deficiencies),
            },
            "high_evidence_72h_canary": {
                "ready": high_ev_72h.ready_for_owner_canary_proposal,
                "score_pct": high_ev_72h.evidence_score_pct,
                "deficiencies": list(high_ev_72h.blocking_deficiencies),
            },
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_counterfactual_audit(), indent=2))
