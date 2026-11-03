"""
Autonomous Polymarket Ecosystem Researcher (`src/paa_os/researcher.py`).

Implements PAA Section 4.A.5 (Autonomous Research) & Acceptance Test #11 (Research Continuity Test):
  - Continuously investigates the complete accessible Polymarket ecosystem across ALL categories
    (Politics, Macro, Weather, Sports, Crypto, Culture, UMA Proposed Carries, `clobRewards`
    Maker Pools, and NegRisk Partition/Convert Arbs).
  - Evaluates forward shadow & OOS ledgers via Purged WFO / CPCV(6,2) / 10k Stationary Bootstrap.
  - Generates novel quantitative hypotheses, tests them against live market microstructure &
    capital-velocity hurdles, and records BOTH successful and unsuccessful findings in SQLite.
  - Automatically enqueues high-EV follow-up validation or graduation tasks for the Director.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.paa_autonomous_controller import scan_entire_polymarket_universe
from scripts.weekly_wfo_governance import evaluate_ledger_file
from src.paa_os.budget import BudgetManager
from src.paa_os.permissions import PermissionClass, load_autonomy_config
from src.paa_os.task_db import PAATaskDB, utc_now_iso

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_PM = PIPELINE_ROOT / "data" / "polymarket"


class PAAResearcher:
    def __init__(
        self,
        db: PAATaskDB,
        budget: BudgetManager,
        data_dir: Optional[Path] = None,
        autonomy_cfg: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db = db
        self.budget = budget
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_PM
        self.paa_dir = self.data_dir / "paa"
        self.paa_dir.mkdir(parents=True, exist_ok=True)
        self.cfg = autonomy_cfg or load_autonomy_config()
        self.consecutive_empty_runs = 0

    def run_research_cycle(
        self,
        max_events: int = 800,
        universe_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes an unattended full-ecosystem research & hypothesis-validation pass.
        Persists both accepted (`succeeded=True`) and rejected (`succeeded=False`) findings.
        """
        if universe_override is not None:
            uni = universe_override
        elif self.budget.check_api_rate_limit("gamma_universe_scan", min_interval_sec=30.0):
            uni = scan_entire_polymarket_universe(max_events=max_events)
        else:
            cached_p = self.paa_dir / "market_opportunity_ranking.json"
            uni = json.loads(cached_p.read_text(encoding="utf-8")) if cached_p.exists() else scan_entire_polymarket_universe(max_events=200)

        accepted_count = 0
        rejected_count = 0
        enqueued_tasks: List[str] = []

        # 1. Evaluate UMA Proposed Maker Carries (BOND1 across Politics, Sports, Weather, Macro)
        uma_cands = uni.get("ranked_uma_proposed_carries") or []
        if uma_cands:
            top_uma = uma_cands[0]
            edge_bps = float(top_uma.get("net_edge_bps_maker_0pct") or 0.0)
            liq = float(top_uma.get("liquidity_usd") or 0.0)
            # Realistic net EV on $25 capital assuming 2 cycles/day and 65% maker fill rate
            est_ev_day = round(25.0 * (edge_bps / 10000.0) * 2.0 * 0.65, 4)
            passed = edge_bps >= 50.0 and liq >= 100.0
            fid = f"RF_UMA_{top_uma.get('market_id', 'TOP')}"
            self.db.record_research_finding(
                finding_id=fid,
                category=f"UMA_CARRY:{top_uma.get('category', 'multi')}",
                hypothesis=f"Post-outcome UMA proposed 0%-fee Maker carry on {top_uma.get('question', '')[:60]} yields {edge_bps:.1f} bps.",
                validation_method="Live Gamma + CLOB L1 Bid/Ask + Objective UMA Domain Filter",
                sample_size=len(uma_cands),
                expected_net_ev_usd_per_day=est_ev_day if passed else 0.0,
                metrics=top_uma,
                succeeded=passed,
                verdict="PROMOTED_CANDIDATE" if passed else "REJECTED_THIN_EDGE_OR_LIQUIDITY",
                notes="Authorized under BOND1_UMA_RESOLUTION_CARRY when on-chain OO proposal verified.",
            )
            if passed:
                accepted_count += 1
            else:
                rejected_count += 1

        # 2. Evaluate Intraday <=8h High-Probability Carries (including negative/rejected hypotheses!)
        intra = uni.get("ranked_intraday_high_prob_carries") or []
        for idx, cand in enumerate(intra[:3]):
            bps_hr = float(cand.get("est_bps_per_hour") or 0.0)
            liq = float(cand.get("liquidity_usd") or 0.0)
            v24 = float(cand.get("volume_24h_usd") or 0.0)
            # Strict empirical filter: reject low-turnover traps (<$1,500 24h vol) where maker fills suffer adverse selection
            viable = bps_hr >= 20.0 and liq >= 500.0 and v24 >= 1500.0
            est_ev = round(20.0 * (float(cand.get("net_edge_bps_maker") or 0.0) / 10000.0) * 0.50, 4) if viable else -0.05
            fid = f"RF_INTRADAY_{cand.get('market_id', idx)}"
            self.db.record_research_finding(
                finding_id=fid,
                category=f"INTRADAY_CARRY:{cand.get('category', 'general')}",
                hypothesis=f"Intraday <=8h Maker carry ({cand.get('side')}) on '{cand.get('question', '')[:55]}' @ {bps_hr:.1f} bps/hr.",
                validation_method="Live Gamma Velocity & Turnover Screen (bps/hr >= 20, vol24h >= $1.5k)",
                sample_size=1,
                expected_net_ev_usd_per_day=est_ev,
                metrics=cand,
                succeeded=viable,
                verdict="SHADOW_CANDIDATE" if viable else "REJECTED_ADVERSE_SELECTION_LOW_TURNOVER",
                notes="Stored in research ledger to prevent chasing illiquid unhedged tail carries.",
            )
            if viable:
                accepted_count += 1
            else:
                rejected_count += 1

        # 3. Evaluate Small-Cap USDC `clobRewards` Liquidity Pools
        rw_pools = uni.get("ranked_clob_usdc_reward_pools") or []
        for idx, rw in enumerate(rw_pools[:2]):
            spread_c = round((float(rw.get("best_ask") or 1.0) - float(rw.get("best_bid") or 0.0)) * 100.0, 2)
            min_cap = float(rw.get("min_capital_est_usd") or 999.0)
            ratio = float(rw.get("daily_pool_to_liq_ratio") or 0.0)
            # Only viable on small bankroll if min_capital <= $15 and two-sided spread <= 6c
            viable_rw = (min_cap <= 15.0) and (spread_c <= 6.0) and (ratio >= 0.01)
            est_ev_rw = round(min_cap * ratio * 0.40, 4) if viable_rw else -0.12
            fid = f"RF_REWARD_POOL_{rw.get('market_id', idx)}"
            self.db.record_research_finding(
                finding_id=fid,
                category=f"CLOB_REWARDS:{rw.get('category', 'general')}",
                hypothesis=f"Passive USDC clobRewards harvesting on '{rw.get('question', '')[:55]}' (pool=${rw.get('daily_reward_pool_usd')}/d).",
                validation_method="Small-Bankroll Min-Size & Spread Adverse-Selection Filter",
                sample_size=len(rw_pools),
                expected_net_ev_usd_per_day=est_ev_rw,
                metrics={**rw, "spread_cents": spread_c},
                succeeded=viable_rw,
                verdict="SHADOW_REWARD_CANDIDATE" if viable_rw else "REJECTED_SPREAD_OR_MIN_CAPITAL_TRAP",
                notes="Two-sided unhedged reward quoting rejected when spread > 6c or min_cap > $15.",
            )
            if viable_rw:
                accepted_count += 1
            else:
                rejected_count += 1

        # 4. Evaluate Shadow Directional & Riskless WFO Ledgers (`CPCV(6,2)` + `10k` Bootstrap)
        shadow_ledgers = [
            ("SLEEVE_SOL_V392_SHADOW", self.data_dir / "ledger_shadow_sol_v392.jsonl"),
            ("SLEEVE_HYBRID_ZSPLIT_SHADOW", self.data_dir / "ledger_shadow_hybrid_zsplit.jsonl"),
            ("SLEEVE_BTC_5M_SNIPER_SHADOW", self.data_dir / "ledger_shadow_btc_5m.jsonl"),
            ("SLEEVE_XAU_15M_MAKER_SHADOW", self.data_dir / "ledger_shadow_xau_15m.jsonl"),
        ]
        for sl_name, lpath in shadow_ledgers:
            rep = evaluate_ledger_file(lpath, min_trades=50, min_pf=1.45, max_pbo=0.20)
            n_tr = int(rep["trades"])
            verdict = str(rep["verdict"])
            fid = f"RF_WFO_{sl_name}"
            est_daily_ev = round(max(-1.0, float(rep["net_pnl_usd"]) / max(1.0, n_tr / 6.0)), 4) if n_tr > 0 else 0.0
            self.db.record_research_finding(
                finding_id=fid,
                category="SHADOW_WFO_CPCV",
                hypothesis=f"Shadow sleeve {sl_name} passes institutional Purged WFO + CPCV(6,2) + 10k Bootstrap gates.",
                validation_method="CPCV(6,2) + 10,000-Draw Stationary Bootstrap (N>=50, PF>=1.45, PBO<=0.20)",
                sample_size=n_tr,
                expected_net_ev_usd_per_day=est_daily_ev,
                metrics=rep,
                succeeded=(verdict == "PROMOTE"),
                verdict=verdict,
                notes=f"Trades={n_tr}, PF={rep['profit_factor']}, CI95=[{rep['bootstrap_ci95_lo_per_trade']}, {rep['bootstrap_ci95_hi_per_trade']}], PBO={rep['pbo_estimate']}",
            )
            if verdict == "PROMOTE":
                accepted_count += 1
                t, created = self.db.enqueue_task(
                    category="STRATEGY_EVAL_WFO",
                    priority_label="P1",
                    expected_net_ev_usd_per_day=max(0.50, est_daily_ev),
                    dedupe_key=f"WFO_GRADUATION_REVIEW:{sl_name}",
                    title=f"Evaluate WFO-Graduated Shadow Sleeve {sl_name} for Canary Promotion",
                    financial_impact_hypothesis=f"{sl_name} achieved PF={rep['profit_factor']}, PBO={rep['pbo_estimate']} over N={n_tr} OOS trades.",
                    evidence=rep,
                    required_permission_class=PermissionClass.EXPLICIT_AUTHORIZATION_REQUIRED.value,
                    required_scopes=["NEW_LIVE_TRADING_ACTIVATION"],
                    validation_requirements={"cpcv_pbo_le_020": True, "bootstrap_ci95_gt_0": True},
                    next_action="STAGE_CANARY_RELEASE_PROPOSAL",
                )
                if created:
                    enqueued_tasks.append(t["task_id"])
            else:
                rejected_count += 1

        total_findings = accepted_count + rejected_count
        if int(uni.get("active_markets_scanned") or 0) == 0 or total_findings == 0:
            self.consecutive_empty_runs += 1
        else:
            self.consecutive_empty_runs = 0

        max_empty = int((self.cfg.get("monitoring") or {}).get("max_consecutive_empty_research_runs", 4))
        if self.consecutive_empty_runs >= max_empty:
            self.db.enqueue_task(
                category="ENGINEERING_REPAIR",
                priority_label="P1",
                expected_net_ev_usd_per_day=2.0,
                dedupe_key="ANTI_STALL:EMPTY_RESEARCH_PIPELINE",
                title="Diagnose Zero-Result Polymarket Universe Research Pipeline",
                financial_impact_hypothesis="Restore full-platform Gamma/CLOB opportunity discovery.",
                evidence={"consecutive_empty_runs": self.consecutive_empty_runs},
                required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                next_action="DIAGNOSE_GAMMA_PAGINATION_OR_NETWORK",
            )

        # Sync JSON export for dashboard compatibility
        findings = self.db.list_research_findings(limit=50)
        exp_reg = {
            "updated_at_utc": utc_now_iso(),
            "active_markets_scanned": uni.get("active_markets_scanned", 0),
            "accepted_findings_this_cycle": accepted_count,
            "rejected_findings_this_cycle": rejected_count,
            "experiments": findings,
        }
        tmp_f = self.paa_dir / "validated_experiment_registry.json.tmp"
        tmp_f.write_text(json.dumps(exp_reg, indent=2, default=str), encoding="utf-8")
        tmp_f.replace(self.paa_dir / "validated_experiment_registry.json")

        summary = {
            "scanned_at_utc": utc_now_iso(),
            "active_markets_scanned": int(uni.get("active_markets_scanned") or 0),
            "events_scanned": int(uni.get("events_scanned") or 0),
            "accepted_findings": accepted_count,
            "rejected_findings": rejected_count,
            "enqueued_tasks": enqueued_tasks,
        }
        self.db.record_heartbeat("paa_research", status="OK", details=summary)
        self.db.log_event("researcher", "RESEARCH_CYCLE_COMPLETED", summary)
        return summary
