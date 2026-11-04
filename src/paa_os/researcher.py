"""
Autonomous RISKLESS PAA Polymarket Ecosystem Researcher (`src/paa_os/researcher.py`).

Implements PAA Section 4.A.5 (Autonomous Research) & Acceptance Test #11 (Research Continuity Test)
under the RISKLESS PAA ("Kings of Riskless Profit") Mandate:
  - Continuously scans the full Polymarket Gamma/CLOB universe (~20,000+ active markets) for
    100% mathematical zero-loss & post-outcome opportunities:
      1. Post-Outcome UMA OO Proposed 0%-Fee Maker Carries (`BOND1` / `BOND2`)
      2. Post-Clinch 0%-Fee Maker Rebate Sweepers (`MKR_LOCK1`)
      3. Locked Dead-Bracket `clobRewards` Harvesting (`MKR_REWARD_LOCKED_CARRY`)
      4. NegRisk Instant-Convert (`NR2`), Exhaustive Complete-Set (`NR0`), & Maker-Anchor Slate Arbs
         (real-time full-platform radar for Machine-Gun Riskless!)
      5. Alpha-124 & Machine-Gun Riskless Zero-Loss `Grad-8` (`8/8`, `0L`) Graduation Pipeline
  - Explicitly rejects unclinched directional carries, mid-book unhedged `clobRewards` traps,
    long-lockup low-velocity slates, and directional live promotions while `riskless_only_mode=true`,
    persisting BOTH accepted (`succeeded=True`) and rejected (`succeeded=False`) findings in SQLite.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.paa_autonomous_controller import (
    _load_riskless_governance_flags,
    discover_machine_gun_sleeves,
    scan_entire_polymarket_universe,
)
from scripts.weekly_wfo_governance import evaluate_ledger_file
from src.paa_os.budget import BudgetManager
from src.paa_os.permissions import PermissionClass, load_autonomy_config
from src.paa_os.task_db import PAATaskDB, utc_now_iso
from src.paa_os.zero_trust import EpistemicStatus, EvidenceStage, sanitize_untrusted_text

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

    def _is_riskless_only_mode(self) -> bool:
        rl_mandate = self.cfg.get("riskless_mandate") or {}
        if rl_mandate.get("enforce_riskless_only_live") is True:
            return True
        rl_flag, _ = _load_riskless_governance_flags()
        return rl_flag

    def run_research_cycle(
        self,
        max_events: int = 800,
        universe_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes an unattended full-ecosystem RISKLESS PAA research & hypothesis-validation pass.
        Persists both accepted (`succeeded=True`) and rejected (`succeeded=False`) findings.
        """
        if universe_override is not None:
            uni = universe_override
        elif self.budget.check_api_rate_limit("gamma_universe_scan", min_interval_sec=30.0):
            uni = scan_entire_polymarket_universe(max_events=max_events)
            tmp_rank = self.paa_dir / "market_opportunity_ranking.json.tmp"
            tmp_rank.write_text(json.dumps(uni, indent=2, default=str), encoding="utf-8")
            tmp_rank.replace(self.paa_dir / "market_opportunity_ranking.json")
        else:
            cached_p = self.paa_dir / "market_opportunity_ranking.json"
            uni = json.loads(cached_p.read_text(encoding="utf-8")) if cached_p.exists() else scan_entire_polymarket_universe(max_events=200)

        riskless_only = self._is_riskless_only_mode()
        _, paused_sleeves = _load_riskless_governance_flags()
        accepted_count = 0
        rejected_count = 0
        enqueued_tasks: List[str] = []

        # 1. Evaluate Post-Outcome UMA Proposed 0%-Fee Maker Carries (`BOND1` / `BOND2`)
        uma_cands = uni.get("ranked_uma_proposed_carries") or []
        for idx_u, uma_raw in enumerate(uma_cands[:2]):
            top_uma = dict(uma_raw)
            raw_q = str(top_uma.get("question") or "")
            clean_q, inj_hits = sanitize_untrusted_text(raw_q, source_label="gamma_market_question", max_chars=180)
            if inj_hits:
                self.db.log_event("researcher", "PROMPT_INJECTION_NEUTRALIZED", {"market_id": top_uma.get("market_id"), "hits": inj_hits})
            top_uma["sanitized_question"] = clean_q
            edge_bps = float(top_uma.get("net_edge_bps_maker_0pct") or 0.0)
            liq = float(top_uma.get("liquidity_usd") or 0.0)
            est_ev_day = round(25.0 * (edge_bps / 10000.0) * 2.0 * 0.65, 4)
            passed = edge_bps >= 40.0 and liq >= 100.0
            fid = f"RF_UMA_{top_uma.get('market_id', f'TOP_{idx_u}')}"
            safe_q_short = "[SANITIZED_EXTERNAL_TITLE]" if inj_hits else re.sub(r"\s+", " ", raw_q)[:60]
            self.db.record_research_finding(
                finding_id=fid,
                category=f"UMA_CARRY:{top_uma.get('category', 'multi')}",
                hypothesis=f"Post-outcome UMA proposed 0%-fee Maker carry on {safe_q_short} yields {edge_bps:.1f} bps.",
                validation_method="Live Gamma + CLOB L1 Bid/Ask + Objective UMA Domain Filter",
                sample_size=len(uma_cands),
                expected_net_ev_usd_per_day=est_ev_day if passed else 0.0,
                metrics=top_uma,
                succeeded=passed,
                verdict="PROMOTED_CANDIDATE" if passed else "REJECTED_THIN_EDGE_OR_LIQUIDITY",
                notes="Authorized under BOND1_UMA_RESOLUTION_CARRY when on-chain OO proposal verified (never claimed LIVE_VERIFIED without settled live trades).",
                evidence_stage=EvidenceStage.SHADOW_VALIDATED.value if passed else EvidenceStage.HYPOTHESIS.value,
                epistemic_status=EpistemicStatus.OBSERVATION.value if passed else EpistemicStatus.HYPOTHESIS.value,
            )
            if passed:
                accepted_count += 1
            else:
                rejected_count += 1

        # 2. Evaluate Complete-Set, NegRisk Instant-Convert (`NR2`) & Maker-Anchor Slate Arbs (`NR0` / Machine-Gun Radar)
        slate_cands = list(uni.get("ranked_negrisk_slate_arbs") or [])[:2] + list(uni.get("ranked_maker_anchor_slate_arbs") or [])[:2]
        for idx_s, sl_raw in enumerate(slate_cands):
            sl_c = dict(sl_raw)
            raw_t = str(sl_c.get("title") or "")
            clean_t, inj_s = sanitize_untrusted_text(raw_t, source_label="gamma_event_title", max_chars=180)
            if inj_s:
                self.db.log_event("researcher", "PROMPT_INJECTION_NEUTRALIZED", {"title": raw_t[:40], "hits": inj_s})
            sl_c["sanitized_title"] = clean_t
            disp_t = "[SANITIZED_EXTERNAL_TITLE]" if inj_s else raw_t[:55]
            opp_type = str(sl_c.get("opportunity_type") or "NEGRISK_SLATE_ARB")
            ebps_s = float(sl_c.get("net_edge_bps") or 0.0)
            rem_h_s = float(sl_c.get("rem_hours") or 9999.0)
            bps_hr_s = float(sl_c.get("est_bps_per_hour") or 0.0)
            is_instant_conv = opp_type == "NR2_INSTANT_NO_CONVERT_ARB"
            fast_enough = is_instant_conv or (rem_h_s <= 168.0 and bps_hr_s >= 2.0)
            viable_slate = ebps_s >= 35.0 and fast_enough
            est_ev_s = round(22.0 * (ebps_s / 10000.0) * (2.0 if is_instant_conv else 0.75), 4) if viable_slate else 0.0
            slug_h = hashlib.sha1(f"{opp_type}:{raw_t}".encode("utf-8", errors="ignore")).hexdigest()[:10]
            self.db.record_research_finding(
                finding_id=f"RF_SLATE_{slug_h}",
                category=f"COMPLETE_SET_ARB:{sl_c.get('category', 'multi')}",
                hypothesis=f"Riskless {opp_type} on '{disp_t}' ({sl_c.get('legs')} legs) nets {ebps_s:.1f} bps ({bps_hr_s:.1f} bps/hr).",
                validation_method="Fee-Adjusted Complete-Set / NegRisk Convert Invariant & Velocity Hurdle (<=168h or Instant Convert)",
                sample_size=int(sl_c.get("legs") or 2),
                expected_net_ev_usd_per_day=est_ev_s,
                metrics=sl_c,
                succeeded=viable_slate,
                verdict="RISKLESS_ARB_CANDIDATE" if viable_slate else "REJECTED_LOW_VELOCITY_CAPITAL_LOCKUP",
                notes="100% mathematical complete-set / NegRisk convert arbitrage; prioritized for NR0/NR2 & Machine-Gun Riskless.",
                evidence_stage=EvidenceStage.OOS_TESTED.value if viable_slate else EvidenceStage.HYPOTHESIS.value,
                epistemic_status=EpistemicStatus.OBSERVATION.value if viable_slate else EpistemicStatus.HYPOTHESIS.value,
            )
            if viable_slate:
                accepted_count += 1
            else:
                rejected_count += 1

        # 3. Evaluate Post-Clinch 0%-Fee Sweepers (`MKR_LOCK1`) & Locked Dead-Bracket `clobRewards` (`MKR_REWARD_LOCKED_CARRY`)
        for cl_raw in (uni.get("ranked_post_clinch_sweepers") or [])[:2]:
            cl_c = dict(cl_raw)
            raw_cq = str(cl_c.get("question") or "")
            clean_cq, inj_c = sanitize_untrusted_text(raw_cq, source_label="gamma_market_question", max_chars=180)
            cl_c["sanitized_question"] = clean_cq
            disp_cq = "[SANITIZED_EXTERNAL_TITLE]" if inj_c else raw_cq[:55]
            ebps_c = float(cl_c.get("net_edge_bps_maker_0pct") or 0.0)
            liq_c = float(cl_c.get("liquidity_usd") or 0.0)
            ok_cl = ebps_c >= 20.0 and liq_c >= 200.0
            self.db.record_research_finding(
                finding_id=f"RF_POST_CLINCH_{cl_c.get('market_id', '0')}",
                category=f"POST_CLINCH_SWEEPER:{cl_c.get('category', 'multi')}",
                hypothesis=f"Post-clinch 0%-fee Maker bid ({cl_c.get('side')} @ ${cl_c.get('maker_bid_px')}) on '{disp_cq}' yields {ebps_c:.1f} bps.",
                validation_method="Post-Deadline / Clinched Outcome >=99.3c + 0% Maker Fee Filter",
                sample_size=1,
                expected_net_ev_usd_per_day=round(22.0 * (ebps_c / 10000.0), 4) if ok_cl else 0.0,
                metrics=cl_c,
                succeeded=ok_cl,
                verdict="PROMOTED_CANDIDATE" if ok_cl else "REJECTED_THIN_POST_CLINCH_EDGE",
                notes="Authorized live under MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER when p_lock >= 0.999.",
                evidence_stage=EvidenceStage.SHADOW_VALIDATED.value if ok_cl else EvidenceStage.HYPOTHESIS.value,
                epistemic_status=EpistemicStatus.OBSERVATION.value,
            )
            if ok_cl:
                accepted_count += 1
            else:
                rejected_count += 1

        for lrw_raw in (uni.get("ranked_locked_clob_rewards") or [])[:2]:
            lrw = dict(lrw_raw)
            raw_lq = str(lrw.get("question") or "")
            clean_lq, inj_l = sanitize_untrusted_text(raw_lq, source_label="gamma_market_question", max_chars=180)
            lrw["sanitized_question"] = clean_lq
            disp_lq = "[SANITIZED_EXTERNAL_TITLE]" if inj_l else raw_lq[:55]
            min_cap_l = float(lrw.get("min_capital_est_usd") or 999.0)
            bps_hr_l = float(lrw.get("est_bps_per_hour") or 0.0)
            ok_lrw = min_cap_l <= 30.0 and bps_hr_l >= 8.0
            self.db.record_research_finding(
                finding_id=f"RF_LOCKED_REWARD_{lrw.get('market_id', '0')}",
                category=f"LOCKED_CLOB_REWARDS:{lrw.get('category', 'multi')}",
                hypothesis=f"Dead-bracket locked clobRewards ({lrw.get('side')} @ ${lrw.get('locked_maker_bid_px')}) on '{disp_lq}' yields {bps_hr_l:.1f} bps/hr.",
                validation_method="Dead-Bracket >=96.5c Certainty + <=$30 Min-Size + Daily USDC Reward Pool Screen",
                sample_size=1,
                expected_net_ev_usd_per_day=round(min(15.0, min_cap_l) * (bps_hr_l / 10000.0) * 12.0, 4) if ok_lrw else 0.0,
                metrics=lrw,
                succeeded=ok_lrw,
                verdict="SHADOW_LOCKED_REWARD_CANDIDATE" if ok_lrw else "REJECTED_MIN_SIZE_TOO_LARGE",
                notes="Zero mid-book directional exposure; tracked under MKR_REWARD_LOCKED_CARRY toward 8/8 Grad-8.",
                evidence_stage=EvidenceStage.OOS_TESTED.value if ok_lrw else EvidenceStage.HYPOTHESIS.value,
                epistemic_status=EpistemicStatus.OBSERVATION.value,
            )
            if ok_lrw:
                accepted_count += 1
            else:
                rejected_count += 1

        # 4. Explicitly Audit & Reject Unclinched Intraday Carries & Mid-Book Unhedged Reward Traps in RISKLESS PAA Mode
        intra = uni.get("ranked_intraday_high_prob_carries") or []
        for idx, cand_raw in enumerate(intra[:2]):
            cand = dict(cand_raw)
            raw_iq = str(cand.get("question") or "")
            clean_iq, inj_i = sanitize_untrusted_text(raw_iq, source_label="gamma_market_question", max_chars=180)
            if inj_i:
                self.db.log_event("researcher", "PROMPT_INJECTION_NEUTRALIZED", {"market_id": cand.get("market_id"), "hits": inj_i})
            cand["sanitized_question"] = clean_iq
            disp_iq = "[SANITIZED_EXTERNAL_TITLE]" if inj_i else raw_iq[:55]
            bps_hr = float(cand.get("est_bps_per_hour") or 0.0)
            liq = float(cand.get("liquidity_usd") or 0.0)
            v24 = float(cand.get("volume_24h_usd") or 0.0)
            if v24 < 1500.0 or liq < 500.0 or bps_hr < 20.0:
                viable = False
                rej_verdict = "REJECTED_ADVERSE_SELECTION_LOW_TURNOVER"
            elif riskless_only:
                viable = False
                rej_verdict = "REJECTED_UNHEDGED_CARRY_RISKLESS_PAA"
            else:
                viable = True
                rej_verdict = "SHADOW_CANDIDATE"
            est_ev = round(20.0 * (float(cand.get("net_edge_bps_maker") or 0.0) / 10000.0) * 0.50, 4) if viable else -0.05
            fid = f"RF_INTRADAY_{cand.get('market_id', idx)}"
            self.db.record_research_finding(
                finding_id=fid,
                category=f"INTRADAY_CARRY:{cand.get('category', 'general')}",
                hypothesis=f"Intraday <=8h Maker carry ({cand.get('side')}) on '{disp_iq}' @ {bps_hr:.1f} bps/hr.",
                validation_method="RISKLESS PAA Zero-Loss Invariant & Turnover Screen (unclinched <99.5c single-leg rejected)",
                sample_size=1,
                expected_net_ev_usd_per_day=est_ev,
                metrics=cand,
                succeeded=viable,
                verdict=rej_verdict,
                notes="Unclinched single-leg carries have tail wipeout risk and are strictly rejected under RISKLESS PAA.",
                evidence_stage=EvidenceStage.HYPOTHESIS.value,
                epistemic_status=EpistemicStatus.ESTIMATE.value if viable else EpistemicStatus.HYPOTHESIS.value,
            )
            if viable:
                accepted_count += 1
            else:
                rejected_count += 1

        rw_pools = uni.get("ranked_clob_usdc_reward_pools") or []
        for idx, rw_raw in enumerate(rw_pools[:2]):
            rw = dict(rw_raw)
            raw_rq = str(rw.get("question") or "")
            clean_rq, inj_r = sanitize_untrusted_text(raw_rq, source_label="gamma_market_question", max_chars=180)
            if inj_r:
                self.db.log_event("researcher", "PROMPT_INJECTION_NEUTRALIZED", {"market_id": rw.get("market_id"), "hits": inj_r})
            rw["sanitized_question"] = clean_rq
            disp_rq = "[SANITIZED_EXTERNAL_TITLE]" if inj_r else raw_rq[:55]
            spread_c = round((float(rw.get("best_ask") or 1.0) - float(rw.get("best_bid") or 0.0)) * 100.0, 2)
            min_cap = float(rw.get("min_capital_est_usd") or 999.0)
            ratio = float(rw.get("daily_pool_to_liq_ratio") or 0.0)
            if (min_cap > 15.0) or (spread_c > 6.0) or (ratio < 0.01):
                viable_rw = False
                rw_verdict = "REJECTED_SPREAD_OR_MIN_CAPITAL_TRAP"
            elif riskless_only:
                viable_rw = False
                rw_verdict = "REJECTED_UNHEDGED_MIDBOOK_REWARD_RISKLESS_PAA"
            else:
                viable_rw = True
                rw_verdict = "SHADOW_REWARD_CANDIDATE"
            est_ev_rw = round(min_cap * ratio * 0.40, 4) if viable_rw else -0.12
            fid = f"RF_REWARD_POOL_{rw.get('market_id', idx)}"
            self.db.record_research_finding(
                finding_id=fid,
                category=f"CLOB_REWARDS:{rw.get('category', 'general')}",
                hypothesis=f"Mid-book USDC clobRewards quoting on '{disp_rq}' (pool=${rw.get('daily_reward_pool_usd')}/d).",
                validation_method="RISKLESS PAA Mid-Book Inventory Risk & Spread Filter (only locked >=96.5c rewards allowed)",
                sample_size=len(rw_pools),
                expected_net_ev_usd_per_day=est_ev_rw,
                metrics={**rw, "spread_cents": spread_c},
                succeeded=viable_rw,
                verdict=rw_verdict,
                notes="Unhedged mid-book clobRewards quoting rejected under RISKLESS PAA; use MKR_REWARD_LOCKED_CARRY instead.",
                evidence_stage=EvidenceStage.HYPOTHESIS.value,
                epistemic_status=EpistemicStatus.HYPOTHESIS.value,
            )
            if viable_rw:
                accepted_count += 1
            else:
                rejected_count += 1

        # 5. Evaluate Zero-Loss Riskless Shadow Fleet (`alpha124_shadow_state.json` + Machine-Gun Riskless Auto-Discovery)
        a124_p = self.data_dir / "alpha124_shadow_state.json"
        if not a124_p.exists() and (self.data_dir.parent / "alpha124" / "alpha124_shadow_state.json").exists():
            a124_p = self.data_dir.parent / "alpha124" / "alpha124_shadow_state.json"
        by_sl_sh: Dict[str, Any] = {}
        if a124_p.exists():
            try:
                by_sl_sh = dict((json.loads(a124_p.read_text(encoding="utf-8")).get("by_sleeve")) or {})
            except Exception:
                by_sl_sh = {}
        mg_map = discover_machine_gun_sleeves(self.data_dir)
        for mg_k, mg_v in mg_map.items():
            by_sl_sh.setdefault(mg_k, mg_v)

        grad8_zero_loss_count = 0
        near_grad8_zero_loss_count = 0
        for sl_k, sl_v in sorted(by_sl_sh.items()):
            if not isinstance(sl_v, dict) or sl_k.upper() in paused_sleeves:
                continue
            w_s = int(sl_v.get("wins") or 0)
            l_s = int(sl_v.get("losses") or 0)
            pnl_s = float(sl_v.get("realized_pnl_t1000_usd", sl_v.get("pnl_t1000_usd", 0.0)) or 0.0)
            if l_s == 0 and w_s >= 8 and pnl_s > 0.0:
                grad8_zero_loss_count += 1
                accepted_count += 1
                self.db.record_research_finding(
                    finding_id=f"RF_GRAD8_{sl_k}",
                    category="RISKLESS_GRAD8_VALIDATED",
                    hypothesis=f"Zero-loss riskless sleeve {sl_k} maintains 100% shadow WR ({w_s}W/0L, +${pnl_s:.2f} T1000).",
                    validation_method="Forward Zero-Loss Grad-8 Gate (wins >= 8, losses == 0, net_pnl_t1000 > $0)",
                    sample_size=w_s,
                    expected_net_ev_usd_per_day=round(max(0.25, (pnl_s / max(1, w_s)) * 0.06 * 2.0), 4),
                    metrics={"sleeve": sl_k, "wins": w_s, "losses": 0, "t1000_pnl_usd": round(pnl_s, 2)},
                    succeeded=True,
                    verdict="GRAD8_ZERO_LOSS_ACTIVE",
                    notes="Graduated 8/8 zero-loss mathematical sleeve (never labeled LIVE_VERIFIED without reconciled live wallet trades).",
                    evidence_stage=EvidenceStage.SHADOW_VALIDATED.value,
                    epistemic_status=EpistemicStatus.OBSERVATION.value,
                )
            elif l_s == 0 and 4 <= w_s < 8 and pnl_s > 0.0:
                near_grad8_zero_loss_count += 1
                accepted_count += 1
                self.db.record_research_finding(
                    finding_id=f"RF_NEAR_GRAD8_{sl_k}",
                    category="RISKLESS_NEAR_GRAD8",
                    hypothesis=f"Zero-loss candidate {sl_k} accumulating toward Grad-8 ({w_s}/8 W, 0L, +${pnl_s:.2f} T1000).",
                    validation_method="Forward Zero-Loss Shadow Accumulation (4-7W, 0L)",
                    sample_size=w_s,
                    expected_net_ev_usd_per_day=round(max(0.10, (pnl_s / max(1, w_s)) * 0.05), 4),
                    metrics={"sleeve": sl_k, "wins": w_s, "remaining_to_grad8": 8 - w_s, "t1000_pnl_usd": round(pnl_s, 2)},
                    succeeded=True,
                    verdict=f"ACCUMULATING_{w_s}_OF_8_ZERO_LOSS",
                    notes=f"{8 - w_s} more zero-loss shadow settlements required for Grad-8 eligibility.",
                    evidence_stage=EvidenceStage.OOS_TESTED.value,
                    epistemic_status=EpistemicStatus.OBSERVATION.value,
                )

        # 6. Evaluate Directional Shadow WFO Ledgers (`CPCV(6,2)` + `10k` Bootstrap — Held in Shadow under Riskless PAA!)
        shadow_ledgers = [
            ("SLEEVE_SOL_V392_SHADOW", self.data_dir / "ledger_shadow_sol_v392.jsonl"),
            ("SLEEVE_HYBRID_ZSPLIT_SHADOW", self.data_dir / "ledger_shadow_hybrid_zsplit.jsonl"),
            ("SLEEVE_BTC_5M_SNIPER_SHADOW", self.data_dir / "ledger_shadow_btc_5m.jsonl"),
            ("SLEEVE_XAU_15M_MAKER_SHADOW", self.data_dir / "ledger_shadow_xau_15m.jsonl"),
        ]
        for sl_name, lpath in shadow_ledgers:
            rep = evaluate_ledger_file(lpath, min_trades=50, min_pf=1.45, max_pbo=0.20)
            n_tr = int(rep["trades"])
            raw_verdict = str(rep["verdict"])
            verdict = "HELD_SHADOW_ONLY_RISKLESS_MODE" if (riskless_only and raw_verdict == "PROMOTE") else raw_verdict
            fid = f"RF_WFO_{sl_name}"
            est_daily_ev = round(max(-1.0, float(rep["net_pnl_usd"]) / max(1.0, n_tr / 6.0)), 4) if (n_tr > 0 and not riskless_only) else 0.0
            ev_stage = (
                EvidenceStage.SHADOW_VALIDATED.value
                if verdict == "PROMOTE"
                else (EvidenceStage.OOS_TESTED.value if n_tr > 0 else EvidenceStage.HYPOTHESIS.value)
            )
            self.db.record_research_finding(
                finding_id=fid,
                category="SHADOW_WFO_CPCV",
                hypothesis=f"Shadow sleeve {sl_name} passes institutional Purged WFO + CPCV(6,2) + 10k Bootstrap gates.",
                validation_method="CPCV(6,2) + 10,000-Draw Stationary Bootstrap (Held Shadow-Only while riskless_only_mode=true)",
                sample_size=n_tr,
                expected_net_ev_usd_per_day=est_daily_ev,
                metrics=rep,
                succeeded=(verdict == "PROMOTE"),
                verdict=verdict,
                notes=f"Trades={n_tr}, PF={rep['profit_factor']}, PBO={rep['pbo_estimate']}, riskless_only_mode={riskless_only}",
                evidence_stage=ev_stage,
                epistemic_status=EpistemicStatus.OBSERVATION.value if n_tr > 0 else EpistemicStatus.HYPOTHESIS.value,
            )
            if verdict == "PROMOTE" and not riskless_only:
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
            "operating_mode": "RISKLESS_PAA" if riskless_only else "HYBRID_PAA",
            "active_markets_scanned": uni.get("active_markets_scanned", 0),
            "accepted_findings_this_cycle": accepted_count,
            "rejected_findings_this_cycle": rejected_count,
            "grad8_zero_loss_sleeves_count": grad8_zero_loss_count,
            "near_grad8_zero_loss_sleeves_count": near_grad8_zero_loss_count,
            "machine_gun_sleeves_detected": sorted(mg_map.keys()),
            "experiments": findings,
        }
        tmp_f = self.paa_dir / "validated_experiment_registry.json.tmp"
        tmp_f.write_text(json.dumps(exp_reg, indent=2, default=str), encoding="utf-8")
        tmp_f.replace(self.paa_dir / "validated_experiment_registry.json")

        summary = {
            "scanned_at_utc": utc_now_iso(),
            "operating_mode": "RISKLESS_PAA" if riskless_only else "HYBRID_PAA",
            "riskless_only_mode": riskless_only,
            "active_markets_scanned": int(uni.get("active_markets_scanned") or 0),
            "events_scanned": int(uni.get("events_scanned") or 0),
            "uma_carries_ranked": len(uma_cands),
            "negrisk_and_convert_arbs_ranked": len(uni.get("ranked_negrisk_slate_arbs") or []),
            "maker_anchor_slate_arbs_ranked": len(uni.get("ranked_maker_anchor_slate_arbs") or []),
            "post_clinch_sweepers_ranked": len(uni.get("ranked_post_clinch_sweepers") or []),
            "locked_clob_rewards_ranked": len(uni.get("ranked_locked_clob_rewards") or []),
            "grad8_zero_loss_sleeves_count": grad8_zero_loss_count,
            "near_grad8_zero_loss_sleeves_count": near_grad8_zero_loss_count,
            "machine_gun_sleeves_detected": sorted(mg_map.keys()),
            "accepted_findings": accepted_count,
            "rejected_findings": rejected_count,
            "enqueued_tasks": enqueued_tasks,
        }
        self.db.upsert_verified_fact(
            fact_key="riskless.universe_scan_summary",
            category="RISKLESS_RESEARCH_RADAR",
            value={
                "markets": summary["active_markets_scanned"],
                "uma": summary["uma_carries_ranked"],
                "negrisk_arbs": summary["negrisk_and_convert_arbs_ranked"],
                "maker_slate_arbs": summary["maker_anchor_slate_arbs_ranked"],
                "post_clinch": summary["post_clinch_sweepers_ranked"],
                "locked_rewards": summary["locked_clob_rewards_ranked"],
                "grad8_zero_loss": grad8_zero_loss_count,
            },
            epistemic_status=EpistemicStatus.OBSERVATION.value,
            source_type="GAMMA_AND_SHADOW_UNIVERSE_SCAN",
            source_ref="data/polymarket/paa/market_opportunity_ranking.json",
            verified_by="PAAResearcher",
            ttl_sec=600.0,
            revalidation_rule="RESCAN_POLYMARKET_UNIVERSE_EVERY_5M",
        )
        self.db.record_heartbeat("paa_research", status="OK", details=summary)
        self.db.log_event("researcher", "RESEARCH_CYCLE_COMPLETED", summary)
        return summary
