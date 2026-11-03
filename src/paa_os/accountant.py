"""
Persistent Financial Intelligence & Accounting Integrity Engine (`src/paa_os/accountant.py`).

Implements PAA Section 4.A.8 (Persistent Financial Intelligence), Acceptance Test #9
(Financial Integrity Test), and Acceptance Test #12 (Profitability Test):
  - Strictly separates:
      1. `REALIZED_ONCHAIN_WALLET` (actual settled cash PnL net of fees)
      2. `UNREALIZED_MARK_TO_BID` / `UNREALIZED_RESTING_MAKER`
      3. `NON_CASH_LEDGER_ARTIFACT` (unfilled Maker orders purged at market close)
      4. `SIMULATED_SHADOW` (`alpha124_shadow_state.json`) & `SIMULATED_PAPER_OOS` (`paper_trading_validation_ledger.jsonl`)
  - Deducts real operational expenses (`research_ai_cost_usd` + `infra_cost_usd`) to compute
    `net_economic_profit_usd` so PAA never optimizes a proxy metric that loses net dollars.
  - Detects accounting discrepancies (`on-chain cash + open CTF shares vs expected ledger state`)
    and immediately triggers `ACCOUNTING_SAFEGUARD_ACTIVE.json` + a `P0` task when breached.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.paa_autonomous_controller import reconcile_authoritative_ledger
from src.paa_os.budget import BudgetManager
from src.paa_os.permissions import load_autonomy_config
from src.paa_os.task_db import PAATaskDB, utc_now_iso

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_PM = PIPELINE_ROOT / "data" / "polymarket"
PAA_DIR = DATA_PM / "paa"


class PAAAccountant:
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
        self.mon_cfg = self.cfg.get("monitoring") or {}

    @property
    def safeguard_file(self) -> Path:
        return self.paa_dir / "ACCOUNTING_SAFEGUARD_ACTIVE.json"

    def _compute_execution_and_slippage_metrics(self) -> Dict[str, Any]:
        """Measures real execution reliability, slippage, latency, and opportunity capture from live state & orders."""
        st_path = self.data_dir / "live_harvester_state.json"
        orders_path = self.data_dir / "live_orders.jsonl"
        st = json.loads(st_path.read_text(encoding="utf-8")) if st_path.exists() else {}
        closed = st.get("closed_positions") or []

        total_slippage_usd = 0.0
        measured_slip_trades = 0
        for c in closed:
            sig_px = c.get("signal_ask_price") or c.get("target_entry_price")
            fill_px = c.get("entry_price")
            sh = float(c.get("entry_shares") or 0.0)
            if sig_px is not None and fill_px is not None and sh > 0:
                try:
                    slip = (float(fill_px) - float(sig_px)) * sh
                    if math.isfinite(slip) and abs(slip) < 50.0:
                        total_slippage_usd += max(0.0, slip)
                        measured_slip_trades += 1
                except Exception:
                    pass

        sent_orders = 0
        filled_orders = 0
        error_orders = 0
        post_ms_samples: List[float] = []
        if orders_path.exists():
            try:
                with orders_path.open("rb") as fh:
                    fh.seek(0, 2)
                    sz = fh.tell()
                    fh.seek(max(0, sz - 524288), 0)
                    lines = fh.read().decode("utf-8", errors="ignore").splitlines()[-400:]
                for ln in lines:
                    if not ln.strip().startswith("{"):
                        continue
                    try:
                        rec = json.loads(ln)
                    except Exception:
                        continue
                    status_u = str(rec.get("status") or rec.get("order_status") or "").upper()
                    sent_orders += 1
                    if status_u in ("MATCHED", "FILLED", "LIVE", "RESTING", "POSITION_CONFIRMED"):
                        filled_orders += 1
                    elif "ERROR" in status_u or "EXCEPTION" in status_u or "TIMEOUT" in status_u:
                        error_orders += 1
                    ms = rec.get("clob_http_post_ms")
                    if isinstance(ms, (int, float)) and 1.0 <= float(ms) <= 30000.0:
                        post_ms_samples.append(float(ms))
            except Exception:
                pass

        post_ms_samples.sort()
        p50_ms = post_ms_samples[len(post_ms_samples) // 2] if post_ms_samples else None
        p90_ms = post_ms_samples[min(len(post_ms_samples) - 1, int(0.9 * len(post_ms_samples)))] if post_ms_samples else None
        reliability = round(100.0 * (1.0 - (error_orders / max(1, sent_orders))), 2) if sent_orders > 0 else 100.0
        capture = round(100.0 * (filled_orders / max(1, sent_orders)), 2) if sent_orders > 0 else 0.0

        return {
            "estimated_slippage_usd": round(total_slippage_usd, 4),
            "measured_slippage_trades": measured_slip_trades,
            "recent_orders_evaluated": sent_orders,
            "recent_orders_filled_or_resting": filled_orders,
            "recent_order_errors": error_orders,
            "execution_reliability_pct": reliability,
            "opportunity_capture_pct": capture,
            "clob_post_p50_ms": round(p50_ms, 2) if p50_ms is not None else None,
            "clob_post_p90_ms": round(p90_ms, 2) if p90_ms is not None else None,
        }

    def _compute_simulated_benchmarks(self) -> Dict[str, Any]:
        """Reads forward shadow & paper ledgers and tags them strictly as SIMULATED (never realized!)."""
        a124_p = self.data_dir / "alpha124_shadow_state.json"
        if not a124_p.exists():
            alt = self.data_dir.parent / "alpha124" / "alpha124_shadow_state.json"
            if alt.exists():
                a124_p = alt
        sh_t1000_pnl = 0.0
        sh_sleeves = 0
        if a124_p.exists():
            try:
                a124 = json.loads(a124_p.read_text(encoding="utf-8"))
                by_sl = a124.get("by_sleeve") or {}
                sh_sleeves = len(by_sl)
                sh_t1000_pnl = round(
                    sum(
                        float(v.get("realized_pnl_t1000_usd", v.get("pnl_t1000_usd", v.get("net_pnl_t1000", 0.0))) or 0.0)
                        for v in by_sl.values()
                        if isinstance(v, dict)
                    ),
                    2,
                )
            except Exception:
                pass

        paper_p = self.data_dir / "paper_trading_validation_ledger.jsonl"
        paper_st_p = self.data_dir / "paper_trader_state.json"
        paper_pnl = 0.0
        paper_trades = 0
        if paper_p.exists():
            try:
                for ln in paper_p.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if not ln.strip():
                        continue
                    r = json.loads(ln)
                    paper_pnl += float(r.get("net_pnl_usd", r.get("pnl_usd", 0.0)) or 0.0)
                    paper_trades += 1
            except Exception:
                pass
        elif paper_st_p.exists():
            try:
                pst = json.loads(paper_st_p.read_text(encoding="utf-8"))
                vo = pst.get("validation_oos_epoch") or {}
                paper_pnl = float(vo.get("cumulative_realized_pnl", 0.0) or 0.0)
                paper_trades = int(vo.get("winning_trades", 0) or 0) + int(vo.get("losing_trades", 0) or 0)
            except Exception:
                pass

        return {
            "performance_origin": "SIMULATED_NON_CASH_BENCHMARK",
            "alpha124_shadow_sleeves_count": sh_sleeves,
            "simulated_shadow_t1000_pnl_usd": round(sh_t1000_pnl, 2),
            "simulated_paper_oos_trades": paper_trades,
            "simulated_paper_oos_pnl_usd": round(paper_pnl, 2),
        }

    def verify_accounting_integrity(
        self,
        ledger: Dict[str, Any],
        state_override: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, float, List[str]]:
        """
        Verifies accounting invariants between authoritative on-chain cash/CTF balances and internal state:
          1. `free_cash_pusd` vs `state.live_bankroll` (minus pending entry intents) within threshold.
          2. Every confirmed open position's on-chain ERC-1155 share balance matches `shares_ledger` within tolerance.
          3. No `UNRESOLVED_BALANCE_DISCREPANCY` status on active or newly closed positions.
        """
        thresh_usd = float(self.mon_cfg.get("accounting_discrepancy_threshold_usd", 1.50))
        sh_tol = float(self.mon_cfg.get("accounting_share_tolerance", 0.75))

        st_path = self.data_dir / "live_harvester_state.json"
        st = state_override if state_override is not None else (
            json.loads(st_path.read_text(encoding="utf-8")) if st_path.exists() else {}
        )

        anomalies: List[str] = []
        onchain_cash = float(ledger.get("free_cash_pusd") or 0.0)
        state_cash = float(st.get("live_bankroll") if st.get("live_bankroll") is not None else onchain_cash)
        inflight_usd = sum(
            float(i.get("notional_usd", 0.0) or 0.0)
            for i in (st.get("pending_entry_intents") or {}).values()
            if isinstance(i, dict)
        )
        cash_diff = abs(onchain_cash - max(0.0, state_cash - inflight_usd))
        # Ignore transient settlement lag if an active position is in MATCHED_PENDING_SETTLEMENT / AWAITING_REDEMPTION
        settling_open = any(
            str(p.get("status") or "").upper() in ("MATCHED_PENDING_SETTLEMENT", "AWAITING_ONCHAIN_SETTLEMENT", "PENDING_CONFIRMATION")
            for p in (st.get("active_positions") or {}).values()
            if isinstance(p, dict)
        )
        if cash_diff > thresh_usd and not settling_open:
            anomalies.append(
                f"CASH_LEDGER_MISMATCH:onchain=${onchain_cash:.2f}_vs_state=${state_cash:.2f}(diff=${cash_diff:.2f}>${thresh_usd:.2f})"
            )

        max_share_usd_gap = 0.0
        for op in ledger.get("open_positions") or []:
            sh_led = float(op.get("shares_ledger") or 0.0)
            sh_chain = op.get("shares_onchain")
            if sh_chain is not None and not settling_open:
                sh_diff = abs(sh_led - float(sh_chain))
                if sh_diff > sh_tol:
                    est_usd = sh_diff * max(0.50, float(op.get("best_bid") or 0.50))
                    max_share_usd_gap = max(max_share_usd_gap, est_usd)
                    anomalies.append(
                        f"CTF_SHARE_DISCREPANCY:{op.get('trade_id')}:ledger={sh_led:.2f}_vs_onchain={float(sh_chain):.2f}"
                    )

        for tid, p in (st.get("active_positions") or {}).items():
            if isinstance(p, dict) and str(p.get("status") or "").upper() == "UNRESOLVED_BALANCE_DISCREPANCY":
                anomalies.append(f"ACTIVE_UNRESOLVED_BALANCE_DISCREPANCY:{tid}")

        total_disc_usd = round(max(cash_diff if not settling_open else 0.0, max_share_usd_gap), 4)
        ok = len(anomalies) == 0
        return ok, total_disc_usd, anomalies

    def enforce_accounting_safeguard(self, discrepancy_usd: float, anomalies: List[str]) -> Dict[str, Any]:
        payload = {
            "activated_at_utc": utc_now_iso(),
            "safeguard": "BLOCK_PROMOTIONS_AND_NEW_EXPOSURE",
            "discrepancy_usd": discrepancy_usd,
            "anomalies": anomalies,
            "live_order_management_preserved": True,
        }
        tmp = self.safeguard_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.safeguard_file)

        self.db.log_event("accountant", "ACCOUNTING_DISCREPANCY_SAFEGUARD_TRIGGERED", payload)
        self.db.enqueue_task(
            category="SAFETY_ACCOUNTING",
            priority_label="P0",
            expected_net_ev_usd_per_day=25.0,
            dedupe_key="SAFETY_ACCOUNTING:LEDGER_DISCREPANCY_RECONCILE",
            title="Reconcile Authoritative Wallet vs Harvester State Discrepancy",
            financial_impact_hypothesis="Prevent trading on drifted cash/share state while keeping open CLOB exits protected.",
            evidence=payload,
            required_permission_class="AUTOMATICALLY_PERMITTED",
            validation_requirements={"accounting_discrepancy_below_threshold": True},
            next_action="RUN_ONCHAIN_RECONCILIATION_AUDIT",
        )
        return payload

    def clear_accounting_safeguard_if_resolved(self, accounting_ok: bool) -> bool:
        if accounting_ok and self.safeguard_file.exists():
            self.safeguard_file.unlink(missing_ok=True)
            self.db.log_event("accountant", "ACCOUNTING_SAFEGUARD_CLEARED", {"status": "RECONCILED_OK"})
            return True
        return False

    def measure_and_record(
        self,
        live_rpc_check: bool = True,
        ledger_override: Optional[Dict[str, Any]] = None,
        state_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Runs full financial measurement, strictly separates realized vs simulated PnL, and enforces safeguards."""
        ledger = ledger_override if ledger_override is not None else reconcile_authoritative_ledger(live_rpc_check=live_rpc_check)
        exec_m = self._compute_execution_and_slippage_metrics()
        sim_m = self._compute_simulated_benchmarks()
        budget_m = self.budget.get_usage_summary()
        acct_ok, disc_usd, anomalies = self.verify_accounting_integrity(ledger, state_override=state_override)

        if not acct_ok:
            self.enforce_accounting_safeguard(disc_usd, anomalies)
        else:
            self.clear_accounting_safeguard_if_resolved(True)

        realized_pnl = float(ledger.get("verified_realized_net_profit_usd") or 0.0)
        ai_cost = float(budget_m.get("all_time_ai_cost_usd") or 0.0)
        infra_today = float(budget_m.get("daily_infra_vm_cost_usd") or 0.0)
        net_econ = round(realized_pnl - ai_cost - infra_today, 4)

        snapshot = {
            "recorded_at_utc": utc_now_iso(),
            "performance_classification": {
                "realized_live": {
                    "origin": "REALIZED_ONCHAIN_WALLET_CASH",
                    "is_real_money": True,
                    "verified_realized_net_pnl_usd": realized_pnl,
                    "raw_state_ledger_pnl_usd": float(ledger.get("raw_state_ledger_realized_pnl_usd") or 0.0),
                    "non_cash_unfilled_artifact_adjustment_usd": float(ledger.get("non_cash_unfilled_artifact_adjustment_usd") or 0.0),
                    "realized_fees_paid_usd": float(ledger.get("total_realized_fees_paid_usd") or 0.0),
                    "estimated_slippage_usd": exec_m["estimated_slippage_usd"],
                    "by_sleeve": ledger.get("live_by_sleeve") or {},
                },
                "unrealized_live": {
                    "origin": "OPEN_LIVE_POSITIONS_MARKED",
                    "is_real_money": True,
                    "free_cash_pusd": float(ledger.get("free_cash_pusd") or 0.0),
                    "open_cost_basis_usd": float(ledger.get("open_cost_basis_usd") or 0.0),
                    "nav_mark_to_bid_usd": float(ledger.get("portfolio_nav_mark_to_bid_usd") or 0.0),
                    "nav_resting_maker_usd": float(ledger.get("portfolio_nav_at_resting_maker_usd") or 0.0),
                    "unrealized_pnl_bid_usd": float(ledger.get("unrealized_pnl_mark_to_bid_usd") or 0.0),
                    "unrealized_pnl_maker_usd": float(ledger.get("unrealized_pnl_at_maker_ask_usd") or 0.0),
                },
                "simulated_or_projected": {
                    "origin": "SIMULATED_SHADOW_AND_PAPER_ONLY",
                    "is_real_money": False,
                    "warning": "Simulated/shadow PnL is NEVER counted toward realized cash or bankroll sizing.",
                    **sim_m,
                },
            },
            "free_cash_pusd": float(ledger.get("free_cash_pusd") or 0.0),
            "open_cost_basis_usd": float(ledger.get("open_cost_basis_usd") or 0.0),
            "nav_mark_to_bid_usd": float(ledger.get("portfolio_nav_mark_to_bid_usd") or 0.0),
            "nav_resting_maker_usd": float(ledger.get("portfolio_nav_at_resting_maker_usd") or 0.0),
            "verified_realized_net_pnl_usd": realized_pnl,
            "raw_ledger_pnl_usd": float(ledger.get("raw_state_ledger_realized_pnl_usd") or 0.0),
            "phantom_adjustment_usd": float(ledger.get("non_cash_unfilled_artifact_adjustment_usd") or 0.0),
            "unrealized_pnl_bid_usd": float(ledger.get("unrealized_pnl_mark_to_bid_usd") or 0.0),
            "unrealized_pnl_maker_usd": float(ledger.get("unrealized_pnl_at_maker_ask_usd") or 0.0),
            "realized_fees_usd": float(ledger.get("total_realized_fees_paid_usd") or 0.0),
            "estimated_slippage_usd": exec_m["estimated_slippage_usd"],
            "drawdown_from_hwm_usd": float(ledger.get("drawdown_from_hwm_usd") or 0.0),
            "capital_utilization_pct": float(ledger.get("capital_utilization_pct") or 0.0),
            "execution_reliability_pct": exec_m["execution_reliability_pct"],
            "opportunity_capture_pct": exec_m["opportunity_capture_pct"],
            "research_ai_cost_usd": ai_cost,
            "infra_cost_usd": infra_today,
            "net_economic_profit_usd": net_econ,
            "accounting_discrepancy_usd": disc_usd,
            "accounting_ok": acct_ok,
            "simulated_shadow_t1000_pnl_usd": sim_m["simulated_shadow_t1000_pnl_usd"],
            "simulated_paper_oos_pnl_usd": sim_m["simulated_paper_oos_pnl_usd"],
            "details": {
                "anomalies": anomalies,
                "execution_metrics": exec_m,
                "budget_summary": budget_m,
                "watchdog_alerts": ledger.get("watchdog_alerts") or [],
            },
        }
        self.db.record_financial_snapshot(snapshot)
        self.db.record_heartbeat(
            "paa_accountant",
            status="OK" if acct_ok else "ACCOUNTING_SAFEGUARD",
            details={"nav_bid": snapshot["nav_mark_to_bid_usd"], "accounting_ok": acct_ok},
        )
        return snapshot
