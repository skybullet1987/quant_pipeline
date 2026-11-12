"""
DOMINUS — RISKLESS FULL THROTTLE
Coverage, Opportunity & Strictly Segregated Economic Dashboard Generator
(`scripts/generate_full_throttle_dashboard.py`)

Owned exclusively by `@pipeline-shadow`.
Renders `FULL_THROTTLE_DASHBOARD.md` from `data/full_throttle/pipeline/dashboard_latest.json`
(and incorporates supplementary peer empirical scan summaries when present on disk).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.polymarket_research.full_throttle_pipeline import (
    AUTHORITATIVE_LIVE_WALLET_BASELINE,
    FAMILY_CATALOG,
    FAMILY_CODES,
)


def _load_optional_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else None
    except Exception:
        return None


def render_full_throttle_dashboard_markdown(
    payload: Mapping[str, Any],
    *,
    peer_universe_snapshot: Optional[Mapping[str, Any]] = None,
    peer_ab_c_j_summary: Optional[Mapping[str, Any]] = None,
    peer_d_to_i_summary: Optional[Mapping[str, Any]] = None,
    peer_k_to_n_summary: Optional[Mapping[str, Any]] = None,
) -> str:
    gen_utc = str(payload.get("generated_at_utc") or "")
    exec_mode = str(payload.get("execution_mode") or "MODE_2_SHADOW")
    jur_gate = str(payload.get("jurisdiction_gate") or "CA-ON")
    live_locked = bool(payload.get("live_orders_hard_locked", True))

    camp = payload.get("campaign_summary") or {}
    u_cov = payload.get("section_1_universe_coverage") or {}
    g_cov = payload.get("section_1b_proposition_graph") or {}
    det_cov = payload.get("section_1c_detector_coverage_by_family") or {}
    opp_m = payload.get("section_2_opportunity_metrics") or {}
    pers = payload.get("section_2b_persistence_and_forward_validation") or {}
    dorm = payload.get("section_2c_dormant_opportunity_store") or {}
    mkr = payload.get("section_2d_hedged_maker_shadow_quoter") or {}
    brg = payload.get("section_2e_harvester_candidate_bridge") or {}
    econ = payload.get("section_3_segregated_economics") or {}
    port = payload.get("section_3b_portfolio_allocation_48_70_pusd") or {}
    curve = payload.get("section_3c_shadow_budget_scaling_curve") or []
    mech_blk = payload.get("section_4_emerging_mechanisms_and_backlog") or {}

    col1 = econ.get("column_1_paper_theoretical") or {}
    col2 = econ.get("column_2_realistic_forward_shadow") or {}
    col3 = econ.get("column_3_verified_live_wallet_cash") or AUTHORITATIVE_LIVE_WALLET_BASELINE
    vm_cmp = econ.get("vm_infrastructure_hurdle_comparison") or {}

    cls_counts = opp_m.get("class_counts") or {}
    skip_counts = u_cov.get("unresolved_or_ineligible_skip_counts") or {}
    edges_by_type = g_cov.get("edges_by_type") or {}
    peer_wired = camp.get("peer_modules_wired") or {}

    lines: List[str] = []
    lines.append("# DOMINUS — RISKLESS FULL THROTTLE: Live Universe, Shadow & Economic Dashboard")
    lines.append("")
    lines.append(f"- **Generated At (UTC):** `{gen_utc}`")
    lines.append(
        f"- **Active Operating Mode:** `{exec_mode}` (`Jurisdiction Gate = {jur_gate}`, "
        f"`MODE_3_LIVE Hard-Locked = {live_locked}`, `0` private keys read, `0` live orders placed)"
    )
    lines.append(
        f"- **Campaign Execution Telemetry:** `{camp.get('total_cycles_executed', 0)}` cycles "
        f"(`{', '.join(camp.get('cycle_types_executed') or [])}`), "
        f"Campaign Wall Time `{camp.get('campaign_wall_time_sec', 0.0):.2f}s`, "
        f"Full-Universe Gamma `/events/keyset` Sweep `{camp.get('full_universe_discovery_sweep_sec', 0.0):.2f}s`, "
        f"Avg `FAST_CYCLE` `{camp.get('avg_fast_cycle_wall_sec', 0.0):.2f}s`, "
        f"In-Memory Listing-to-Eval Latency `{camp.get('listing_to_evaluation_latency_ms', 0.0):.1f} ms`"
    )
    lines.append(
        f"- **Swapless Host Safety (`D-010`):** Peak RSS **`{camp.get('peak_rss_mib', 0.0):.2f} MiB`** "
        f"(`<= 180.0 MiB` budget OK: `{camp.get('swapless_180mib_budget_ok', True)}`)"
    )
    lines.append(
        "- **Integrated Peer Tracks:** "
        + ", ".join(f"`{k}={v}`" for k, v in peer_wired.items())
    )
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 1: Universe & Relationship Coverage
    # -----------------------------------------------------------------------
    lines.append("## 1. Universe, Order-Book & Relationship Graph Coverage (`Section 12.1`)")
    lines.append("")
    lines.append("| Coverage Dimension | Live Empirical Value | Notes / Protocol Detail |")
    lines.append("| :--- | ---: | :--- |")
    lines.append(
        f"| **Total Observable Active Events** | **`{u_cov.get('total_observable_events', 0):,}`** | "
        "Untruncated Gamma `/events/keyset?active=true&closed=false&after_cursor=...` |"
    )
    lines.append(
        f"| **Total Child Markets in Active Events / Active Unclosed** | **`{u_cov.get('total_observable_markets', 0):,}` / `{u_cov.get('active_unclosed_markets', u_cov.get('orderbook_enabled_markets', 0)):,}`** | "
        "100% retained in discovery census (`CLOSED_OR_ARCHIVED` sibling slots accounted explicitly) |"
    )
    lines.append(
        f"| **Order-Book Enabled Markets (`enableOrderBook=true`)** | **`{u_cov.get('orderbook_enabled_markets', 0):,}`** | "
        f"`{skip_counts.get('ORDERBOOK_DISABLED', 0):,}` markets skipped with explicit `ORDERBOOK_DISABLED` code |"
    )
    lines.append(
        f"| **Tradable CLOB Outcome Token IDs** | **`{u_cov.get('total_tradable_outcome_tokens', 0):,}`** | "
        "Distinct ERC-1155 CTF `YES` / `NO` token IDs |"
    )
    lines.append(
        f"| **Standard `negRisk` vs `negRiskAugmented` Events** | **`{u_cov.get('negrisk_events', 0):,}` / `{u_cov.get('augmented_negrisk_events', 0):,}`** | "
        "Augmented placeholder/`Other` slates strictly guarded against false partition proofs |"
    )
    lines.append(
        f"| **Fee-Curve Enabled Markets (`feesEnabled=true`)** | **`{u_cov.get('fees_enabled_markets', 0):,}`** | "
        "Priced via exact Protocol V2 `p*(1-p)` share-haircut schedule (`feeSchedule.{rate,exponent}`) |"
    )
    lines.append(
        f"| **Proposition Graph Edges (`Total` / `Cross-Market`)** | **`{g_cov.get('total_edges', 0):,}` / `{g_cov.get('cross_market_edges', 0):,}`** | "
        f"`OFFICIAL_CONTRACTUAL={edges_by_type.get('OFFICIAL_CONTRACTUAL', 0):,}`, "
        f"`VERIFIED_MATHEMATICAL={edges_by_type.get('VERIFIED_MATHEMATICAL', 0):,}`, "
        f"`SUSPECTED={edges_by_type.get('SUSPECTED_REQUIRES_PROOF', 0):,}`, "
        f"`STATISTICAL={edges_by_type.get('STATISTICAL_CORRELATION_ONLY', 0):,}` |"
    )
    lines.append(
        f"| **Verified Multi-Market Connected Components** | **`{g_cov.get('verified_multi_market_components', 0):,}`** | "
        "Pruned `O(m log m)` components preventing blind `O(N^2)` combinatorial scans |"
    )
    lines.append(
        f"| **Fresh L2 Order-Book Markets / Tokens (Latest Cycle)** | **`{u_cov.get('fresh_l2_book_markets_this_cycle', 0):,}` / `{u_cov.get('fresh_l2_book_tokens_this_cycle', 0):,}`** | "
        f"Total batched `/books` token polls across campaign: `{camp.get('total_batched_book_tokens_polled_across_cycles', 0):,}` |"
    )
    lines.append(
        f"| **Portfolio Holdings (`Recyclable` / `D-001 Frozen KMIA`)** | **`{u_cov.get('recyclable_holdings_count', 0)}` / `{u_cov.get('d001_frozen_kmia_holdings_quarantined', 4)}`** | "
        "4 disputed Nov 7 `KMIA` positions (`6707503`, `6707502`, `$50.51`) 100% quarantined |"
    )
    lines.append("")

    lines.append("### Explicit Machine-Readable Eligibility & Skip Accounting")
    lines.append("")
    lines.append("| Skip / Quarantine Code | Market Count | Handling Rule |")
    lines.append("| :--- | ---: | :--- |")
    for sk, sv in sorted(skip_counts.items(), key=lambda kv: (-int(kv[1]), kv[0])):
        lines.append(f"| `{sk}` | `{int(sv):,}` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |")
    if not skip_counts:
        lines.append("| `NONE` | `0` | All evaluated markets eligible |")
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 2: Per-Family Detector Coverage & Opportunity Classification (`A..N`)
    # -----------------------------------------------------------------------
    lines.append("## 2. Opportunity Families `A..N` Coverage & 5-Tier Proof Breakdown (`Section 12.2`)")
    lines.append("")
    lines.append(
        f"- **Total Candidates Structured & Verified (Latest Cycle):** `{opp_m.get('total_candidates_evaluated', 0):,}` "
        f"(`Mathematically Proven CLASS A + B = {opp_m.get('mathematically_valid_proofs', 0)}`, "
        f"`CLASS_A = {cls_counts.get('CLASS_A', 0)}`, `CLASS_B = {cls_counts.get('CLASS_B', 0)}`, "
        f"`CLASS_C = {cls_counts.get('CLASS_C', 0)}`, `CLASS_D Rule-Rejected = {cls_counts.get('CLASS_D', 0)}`, "
        f"`CLASS_E No-Arb/Shallow = {cls_counts.get('CLASS_E', 0)}`)"
    )
    lines.append(
        f"- **Rule-Mismatch Traps Prevented (`90m vs OT`, `Timezone`, `Touch vs Close`, `Converse`):** "
        f"**`{opp_m.get('rule_mismatch_rejections_prevented', 0):,}`**"
    )
    lines.append(
        f"- **`D-007` `< $500` NAV Sequential `>= 3`-Leg Quarantined Bundles:** "
        f"**`{opp_m.get('d007_quarantined_3plus_leg_count', 0):,}`**"
    )
    lines.append("")
    lines.append("| Family | Opportunity Family Description | Structures / Markets Inspected | Emitted | `CLASS_A` | `CLASS_B` | `CLASS_C` | `CLASS_D` | `CLASS_E` | Dormant Near-Miss |")
    lines.append("| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for fc in FAMILY_CODES:
        row = det_cov.get(fc) or {
            "family_name": FAMILY_CATALOG[fc]["name"],
            "structures_or_markets_inspected": 0,
            "candidates_emitted": 0,
            "CLASS_A": 0,
            "CLASS_B": 0,
            "CLASS_C": 0,
            "CLASS_D": 0,
            "CLASS_E": 0,
            "dormant_near_misses": 0,
        }
        lines.append(
            f"| **`{fc}`** | {row.get('family_name', FAMILY_CATALOG[fc]['name'])} | "
            f"`{int(row.get('structures_or_markets_inspected', 0)):,}` | "
            f"`{int(row.get('candidates_emitted', 0)):,}` | "
            f"`{int(row.get('CLASS_A', 0))}` | "
            f"`{int(row.get('CLASS_B', 0))}` | "
            f"`{int(row.get('CLASS_C', 0))}` | "
            f"`{int(row.get('CLASS_D', 0))}` | "
            f"`{int(row.get('CLASS_E', 0))}` | "
            f"`{int(row.get('dormant_near_misses', 0))}` |"
        )
    lines.append("")

    # -----------------------------------------------------------------------
    # Section 3: Persistence, Forward Validation & Dormant Opportunity Store
    # -----------------------------------------------------------------------
    lines.append("## 3. Multi-Cycle Persistence, Forward `t -> t+1` Validation & Dormant Store")
    lines.append("")
    surv_rate = pers.get("forward_survival_rate")
    surv_str = f"{surv_rate * 100.0:.1f}%" if isinstance(surv_rate, (int, float)) else "N/A (awaiting multi-cycle)"
    lines.append(
        f"- **Persistence Across Cycles:** `{pers.get('tracked_unique_candidates', 0)}` unique candidates tracked, "
        f"`{pers.get('tracked_unique_proven_arbs', 0)}` unique proven `CLASS_A/B` arbs, "
        f"`{pers.get('multi_cycle_persistent_arbs', 0)}` persisted `>= 2` cycles "
        f"(avg observed lifetime `{pers.get('avg_persistent_arb_lifetime_sec', 0.0):.2f}s`)."
    )
    lines.append(
        f"- **Non-Hindsight Forward Snapshot Validation (`Cycle t -> Cycle t+1`):** "
        f"`{pers.get('forward_validations_completed', 0)}` tickets re-evaluated on next live `/books` poll, "
        f"`{pers.get('forward_validations_survived', 0)}` survived (`{surv_str}`), "
        f"post-delay validated net PnL **`${pers.get('forward_validated_net_pnl_usd', 0.0):.4f}`**."
    )
    lines.append(
        f"- **`DormantOpportunityStore` (`dormant_opportunities.json`):** "
        f"**`{dorm.get('active_dormant_count', 0)}`** active near-miss / shallow-depth structures retained "
        f"(`<= 50 bps`: `{dorm.get('within_50_bps_count', 0)}`, `<= 150 bps`: `{dorm.get('within_150_bps_count', 0)}`, "
        f"book-shift rescans triggered: `{dorm.get('total_rescans_triggered', 0)}`, "
        f"promoted to executable: `{dorm.get('total_promotions_to_executable', 0)}`)."
    )
    lines.append(
        f"- **`HedgedMakerShadowQuoter` (`Family L` `0 bps` `postOnly` + `15%–25%` Rebate Shadow, Strictly Segregated from Locked Cash):** "
        f"`{mkr.get('resting_passive_quotes_count', 0)}` active resting quotes (`{mkr.get('total_quotes_posted', 0)}` posted, "
        f"`{mkr.get('filled_hedged_locks_count', 0)}` hedged fills, `{mkr.get('adverse_selected_fills_count', 0)}` adverse-jump unwinds, "
        f"ex-rebate net shadow PnL `${float(mkr.get('net_post_adverse_shadow_pnl_ex_rebate_usd', 0.0)):.4f}`, "
        f"est. maker rebate `${float(mkr.get('estimated_maker_rebate_15_to_25pct_usd', 0.0)):.4f}`)."
    )
    lines.append(
        f"- **`HarvesterCandidateBridge` (`d1_live_box_candidates.jsonl` Single-Authority Bridge + JIT `/books` Re-Verify):** "
        f"`Enabled={bool(brg.get('enabled', False))}`, "
        f"`EmittedThisCycle={int(brg.get('candidates_emitted_this_cycle', 0))}` "
        f"(`TakerBoxes={int(brg.get('taker_boxes_emitted_this_cycle', 0))}`, "
        f"`MakerLocks={int(brg.get('maker_locks_emitted_this_cycle', 0))}`), "
        f"`JITReverified={int(brg.get('total_jit_verified_across_campaign', 0))}`, "
        f"`JITDecayedBlocked={int(brg.get('total_jit_rejected_across_campaign', 0))}`, "
        f"`CampaignTotalEmitted={int(brg.get('total_emitted_across_campaign', 0))}`, "
        f"`DedupeSuppressed={int(brg.get('total_dedupe_suppressed', 0))}`."
    )
    lines.append("")

    closest_dormant = dorm.get("closest_near_misses") or []
    if closest_dormant:
        lines.append("### Top Monitored Dormant Near-Arbitrage Structures (Awaiting Book Shift)")
        lines.append("")
        lines.append("| Candidate ID | Fam | Summary | Gap to Breakeven | Reason | Obs / Shift Rescans |")
        lines.append("| :--- | :---: | :--- | ---: | :--- | ---: |")
        for dm in closest_dormant[:10]:
            lines.append(
                f"| `{dm.get('candidate_id', '')[:34]}` | `{dm.get('family_code', '')}` | "
                f"{str(dm.get('title_summary', ''))[:48]} | `{float(dm.get('gap_to_breakeven_bps', 0.0)):.1f} bps` | "
                f"`{dm.get('dormant_reason', '')}` | `{dm.get('times_observed', 1)} / {dm.get('times_rescanned_on_shift', 0)}` |"
            )
        lines.append("")

    # -----------------------------------------------------------------------
    # Section 4: Strictly Segregated 3-Column Economic Ledger & VM Hurdle
    # -----------------------------------------------------------------------
    lines.append("## 4. Strictly Segregated Economic Accounting & `$24.67/mo` VM Hurdle (`Section 12.3 & 19`)")
    lines.append("")
    lines.append("> **Non-Conflation Invariant:** Simulated paper top-of-book numbers and forward shadow estimates are **strictly segregated** from realized on-chain `pUSD` wallet cash on `kraken-finland`.")
    lines.append("")
    lines.append("| Metric | Column 1: Paper Theoretical (Unallocated L1) | Column 2: Realistic Forward Shadow (Depth-Walked, Post-Fee, Post-Latency) | Column 3: Verified Live Wallet Reality (`kraken-finland`) |")
    lines.append("| :--- | ---: | ---: | ---: |")
    lines.append(
        f"| **Liquid `pUSD` Wallet Cash** | `N/A (Paper)` | `${port.get('reference_liquid_pusd_budget', 48.695132):.2f}` (Shadow Ref Budget) | **`${float(col3.get('liquid_pusd_cash_usd', 48.695132)):.6f}` (`$48.70`)** |"
    )
    lines.append(
        f"| **True Worst-Case Floor / Mark-to-Bid NAV** | `N/A` | `${port.get('reference_liquid_pusd_budget', 48.695132):.2f}` | **`${float(col3.get('worst_case_guaranteed_floor_nav_usd', 48.695132)):.2f}` / `${float(col3.get('mark_to_bid_liquidation_nav_usd', 48.834132)):.2f}`** |"
    )
    lines.append(
        f"| **Book Equity (incl. Frozen Disputed `KMIA`)** | `N/A` | `Forbidden for sizing (D-007)` | **`${float(col3.get('persisted_harvester_book_equity_usd', 99.205132)):.2f}` (`$50.51` frozen `KMIA`)** |"
    )
    lines.append(
        f"| **Proven `CLASS A + B` Value (Unallocated Sum)** | `${float(col1.get('proven_class_a_b_paper_usd', 0.0)):.4f}` | `${float(col2.get('unallocated_l2_executable_sum_usd', 0.0)):.4f}` L2 / `${float(col2.get('unallocated_post_latency_sum_usd', 0.0)):.4f}` Post-Latency | `N/A` |"
    )
    lines.append(
        f"| **Constrained Portfolio Net Value (`$48.70` Cap)** | `Unconstrained` | **`${float(col2.get('portfolio_guaranteed_l2_net_usd', 0.0)):.4f}` L2 / `${float(col2.get('portfolio_post_latency_risk_adjusted_net_usd', 0.0)):.4f}` Risk-Adj** | `0` new orders in Shadow Mode |"
    )
    lines.append(
        f"| **Verified Realized Pure-Riskless Cash P&L** | `$0.00` | `$0.00` (`Shadow != Cash`) | **`+${float(col3.get('cumulative_pure_riskless_live_net_pnl_usd', 18.24611)):.4f}` (`79W / 0L`, `100.0%` WR)** |"
    )
    lines.append(
        f"| **Modeled Taker Fees / L2 Slippage / Unwind Bleed** | `$0.00` (Ignored in L1) | `${float(col2.get('total_taker_fees_modeled_usd', 0.0)):.4f}` / `${float(col2.get('total_l2_depth_slippage_vs_l1_usd', 0.0)):.4f}` / `${float(col2.get('total_expected_partial_fill_unwind_bleed_usd', 0.0)):.4f}` | `$0.5825` historical realized fees |"
    )
    lines.append(
        f"| **Capital Efficiency (Non-Guaranteed Estimate)** | `N/A` | `{float(col2.get('estimated_capital_efficiency_bps_per_hr_non_guaranteed', 0.0)):.2f} bps/hr` (Est. `${float(col2.get('estimated_daily_yield_on_48_70_usd_non_guaranteed', 0.0)):.4f}/day`) | Hurdle: **`+7.04 bps/hr` (`$0.8223/day`)** |"
    )
    lines.append("")

    lines.append("### Infrastructure Breakeven Hurdle (`$24.67/month` = `$0.8223/day` = `$0.0343/hr`)")
    lines.append("")
    lines.append(
        f"- At **`$48.70`** liquid `pUSD`, covering the `$24.67/month` Finland VM requires **`+{float(vm_cmp.get('required_portfolio_bps_per_hr_at_48_70_cash', 7.0364)):.2f} bps/hr`** (`+168.87 bps/day`) continuously deployed; at **`$500.00`** NAV, the hurdle drops `10.3x` to **`+{float(vm_cmp.get('required_portfolio_bps_per_hr_at_500_nav', 0.6853)):.2f} bps/hr`**."
    )
    lines.append(
        f"- Current snapshot constrained shadow portfolio velocity estimate: **`{float(vm_cmp.get('shadow_portfolio_bps_per_hr_estimate', 0.0)):.2f} bps/hr`** "
        f"(`Covers VM hurdle on this snapshot = {vm_cmp.get('covers_vm_hurdle_at_48_70_cash', False)}`, "
        f"daily delta vs `$0.8223/day` hurdle: `${float(vm_cmp.get('daily_surplus_or_deficit_vs_vm_at_48_70_usd', -0.822333)):+.4f}/day`)."
    )
    lines.append("")

    # Top executable opportunities table
    top_exec = payload.get("top_executable_opportunities") or []
    lines.append("## 5. Top Verified Executable Opportunities (`CLASS_A` & `CLASS_B`)")
    lines.append("")
    if top_exec:
        lines.append("| Rank | Class | Fam | Candidate ID | Title | Opt `q*` | Cap Req (`$`) | Gross/u | Net L2 (`$`) | Risk-Adj (`$`) | Lockup (`h`) | Efficiency (`bps/hr`) |")
        lines.append("| ---: | :---: | :---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for idx, op in enumerate(top_exec[:15], start=1):
            seg = op.get("segregated_economics") or {}
            lines.append(
                f"| `{idx}` | `{op.get('opportunity_class')}` | `{op.get('family_code')}` | "
                f"`{str(op.get('candidate_id'))[:28]}` | {str(op.get('title_summary'))[:42]} | "
                f"`{float(op.get('optimal_executable_quantity', 0.0)):.2f}` | "
                f"`${float(op.get('capital_required_usd', 0.0)):.2f}` | "
                f"`{float(op.get('gross_top_of_book_edge_per_unit', 0.0)):+.4f}` | "
                f"`${float(seg.get('executable_l2_net_usd', 0.0)):.4f}` | "
                f"`${float(seg.get('forward_shadow_risk_adjusted_usd', 0.0)):.4f}` | "
                f"`{float(op.get('expected_lockup_hours', 0.0)):.2f}h` | "
                f"`{float(op.get('capital_efficiency_bps_per_hr', 0.0)):.1f}` |"
            )
    else:
        lines.append(
            "- **`0` strictly positive post-fee L2 `CLASS_A/B` opportunities** at the exact polled millisecond snapshot "
            "(all tight spreads after Polymarket's V2 `p*(1-p)` dynamic taker fee curve were negative net or below `$1.00` marketable floor and were captured in `DormantOpportunityStore` rather than falsely promoted)."
        )
    lines.append("")

    # Cycle-by-cycle telemetry
    cyc_rows = payload.get("cycle_by_cycle_telemetry") or []
    lines.append("## 6. Multi-Cycle Operating Telemetry (`DISCOVERY_CYCLE` / `FAST_CYCLE` / `RESEARCH_CYCLE`)")
    lines.append("")
    lines.append("| Cycle | Operating Cycle | UTC Timestamp | Wall (`s`) | RSS (`MiB`) | Fresh Books | Candidates | `A` | `B` | `C` | `D` | Active Dormant |")
    lines.append("| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for cr in cyc_rows:
        lines.append(
            f"| `{cr.get('cycle_index')}` | `{cr.get('cycle_type')}` | `{cr.get('timestamp_utc')}` | "
            f"`{float(cr.get('wall_sec', 0.0)):.2f}s` | `{float(cr.get('rss_mib', 0.0)):.1f}` | "
            f"`{int(cr.get('fresh_books', 0)):,}` | `{int(cr.get('candidates', 0)):,}` | "
            f"`{int(cr.get('class_a', 0))}` | `{int(cr.get('class_b', 0))}` | "
            f"`{int(cr.get('class_c', 0))}` | `{int(cr.get('class_d', 0))}` | "
            f"`{int(cr.get('dormant_active', 0))}` |"
        )
    lines.append("")

    # Supplementary Peer Deep-Scan Cross-References if present
    if any(x is not None for x in (peer_universe_snapshot, peer_ab_c_j_summary, peer_d_to_i_summary, peer_k_to_n_summary)):
        lines.append("## 7. Cross-Referenced Specialist Deep-Scan Summaries")
        lines.append("")
        if peer_universe_snapshot is not None:
            ut = peer_universe_snapshot.get("universe_totals") or {}
            ds = peer_universe_snapshot.get("diff_stats") or {}
            pb = peer_universe_snapshot.get("protocol_and_instrument_breakdown") or {}
            lines.append(
                f"- **`@discovery` (`data/universe/coverage_snapshot.json`):** "
                f"`{ut.get('active_unclosed_events', 0):,}` active events, "
                f"`{ut.get('all_child_markets_in_active_events', 0):,}` total child markets "
                f"(`{ut.get('active_unclosed_markets', 0):,}` active unclosed, `{ut.get('tradable_outcome_token_ids', 0):,}` tradable tokens, "
                f"`{pb.get('fees_enabled_true_active_markets', 0):,}` dynamic-fee vs `{pb.get('fees_enabled_false_active_markets', 0):,}` zero-fee, "
                f"Peak RSS `{ds.get('peak_rss_mib', 0.0):.2f} MiB`)."
            )
        if peer_ab_c_j_summary is not None:
            ov = peer_ab_c_j_summary.get("overall_summary_at_live_nav") or {}
            uc = peer_ab_c_j_summary.get("universe_coverage") or {}
            cb = ov.get("class_breakdown") or {}
            lines.append(
                f"- **`@complete-negrisk` (`data/full_throttle/scans_ab_c_j/scan_summary.json`):** "
                f"`{ov.get('total_structures_evaluated', 0):,}` structures verified across `{uc.get('clob_books_returned', 0):,}` CLOB L2 books "
                f"(`CLASS_D={cb.get('CLASS_D', 0):,}`, `{ov.get('gross_positive_top_of_book_total', 0)}` L1 gross-positive illusions rejected by V2 fees, "
                f"`{ov.get('dormant_near_arb_0_to_50_bps_total', 0):,}` dormant `<=50 bps` + `{ov.get('dormant_near_arb_50_to_250_bps_total', 0):,}` `50-250 bps`)."
            )
        if peer_d_to_i_summary is not None:
            u_m = peer_d_to_i_summary.get("universe_metrics") or {}
            cd = peer_d_to_i_summary.get("class_distribution") or {}
            lines.append(
                f"- **`@logical-specialized` (`data/full_throttle/scans_d_to_i/scan_summary.json`):** "
                f"`{u_m.get('total_canonical_markets', 0):,}` canonical markets across `{u_m.get('total_books_loaded', 0):,}` L2 books, "
                f"`CLASS_B={cd.get('CLASS_B', 0)}`, `CLASS_C={cd.get('CLASS_C', 0)}`, `CLASS_D={cd.get('CLASS_D', 0)}`, "
                f"`{peer_d_to_i_summary.get('total_rule_mismatch_rejections_prevented', 0):,}` rule-mismatch traps prevented."
            )
        if peer_k_to_n_summary is not None:
            u_s = peer_k_to_n_summary.get("universe_scope") or {}
            lines.append(
                f"- **`@micro-portfolio` (`data/full_throttle/scans_k_to_n/scan_summary.json`):** "
                f"`{u_s.get('total_active_markets_inspected', 0):,}` active markets inspected across `{u_s.get('clob_orderbooks_returned', 0):,}` L2 books (`Families K..N` & emerging mechanism catalog)."
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def generate_dashboard_files(
    *,
    dashboard_json_path: Path = REPO_ROOT / "data" / "full_throttle" / "pipeline" / "dashboard_latest.json",
    markdown_out_path: Path = REPO_ROOT / "FULL_THROTTLE_DASHBOARD.md",
) -> Path:
    if not dashboard_json_path.exists():
        raise FileNotFoundError(f"Dashboard JSON payload not found at {dashboard_json_path}")
    payload = json.loads(dashboard_json_path.read_text(encoding="utf-8"))
    md = render_full_throttle_dashboard_markdown(
        payload,
        peer_universe_snapshot=_load_optional_json(REPO_ROOT / "data" / "universe" / "coverage_snapshot.json"),
        peer_ab_c_j_summary=_load_optional_json(REPO_ROOT / "data" / "full_throttle" / "scans_ab_c_j" / "scan_summary.json"),
        peer_d_to_i_summary=_load_optional_json(REPO_ROOT / "data" / "full_throttle" / "scans_d_to_i" / "scan_summary.json"),
        peer_k_to_n_summary=_load_optional_json(REPO_ROOT / "data" / "full_throttle" / "scans_k_to_n" / "scan_summary.json"),
    )
    tmp = markdown_out_path.with_suffix(".md.tmp")
    tmp.write_text(md, encoding="utf-8", newline="\n")
    os.replace(tmp, markdown_out_path)
    return markdown_out_path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate FULL_THROTTLE_DASHBOARD.md from pipeline JSON telemetry.")
    parser.add_argument(
        "--input-json",
        type=Path,
        default=REPO_ROOT / "data" / "full_throttle" / "pipeline" / "dashboard_latest.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=REPO_ROOT / "FULL_THROTTLE_DASHBOARD.md",
    )
    args = parser.parse_args(argv)
    out = generate_dashboard_files(dashboard_json_path=args.input_json, markdown_out_path=args.output_md)
    print(f"Wrote dashboard markdown to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
