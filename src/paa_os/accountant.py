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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.paa_autonomous_controller import (
    _load_riskless_governance_flags,
    is_phantom_unfilled_position,
    reconcile_authoritative_ledger,
    reconcile_closed_position_record,
)
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
                    if status_u in ("MATCHED", "FILLED", "LIVE", "RESTING", "POSITION_CONFIRMED") or rec.get("success") is True:
                        filled_orders += 1
                    elif (
                        "ERROR" in status_u
                        or "EXCEPTION" in status_u
                        or "TIMEOUT" in status_u
                        or rec.get("success") is False
                        or bool(rec.get("error"))
                    ):
                        error_orders += 1
                    ms = rec.get("clob_http_post_ms") if rec.get("clob_http_post_ms") is not None else rec.get("latency_ms")
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
        zl_sh_t1000_pnl = 0.0
        zl_sh_wins = 0
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
                for v in by_sl.values():
                    if not isinstance(v, dict):
                        continue
                    w_sl = int(v.get("wins", 0) or 0)
                    l_sl = int(v.get("losses", 0) or 0)
                    p_sl = float(v.get("realized_pnl_t1000_usd", v.get("pnl_t1000_usd", v.get("net_pnl_t1000", 0.0))) or 0.0)
                    if l_sl == 0 and w_sl > 0 and p_sl > 0.0:
                        zl_sh_t1000_pnl += p_sl
                        zl_sh_wins += w_sl
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
            "zero_loss_shadow_t1000_pnl_usd": round(zl_sh_t1000_pnl, 2),
            "zero_loss_shadow_wins": zl_sh_wins,
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
        pusd_only_raw = ledger.get("free_cash_pusd_only")
        onchain_candidates = [onchain_cash]
        if isinstance(pusd_only_raw, (int, float)) and not isinstance(pusd_only_raw, bool):
            onchain_candidates.append(float(pusd_only_raw))
        state_cash = float(st.get("live_bankroll") if st.get("live_bankroll") is not None else onchain_cash)
        pend_dicts = [i for i in (st.get("pending_entry_intents") or {}).values() if isinstance(i, dict)]
        inflight_usd = sum(float(i.get("notional_usd", 0.0) or 0.0) for i in pend_dicts)
        matched_intent_usd = sum(float(i.get("matched_notional_usd", 0.0) or 0.0) for i in pend_dicts)
        ps_st = st.get("pre_split_inventory_state") if isinstance(st.get("pre_split_inventory_state"), dict) else {}
        ps_realized = float(ps_st.get("realized_cash_usd") or 0.0) if ps_st.get("active") else 0.0
        eff_state_cash = state_cash + ps_realized
        raw_cash_diff = min(abs(oc - eff_state_cash) for oc in onchain_candidates)
        if inflight_usd > 0.0 or matched_intent_usd > 0.0:
            # Resting EIP-712 Maker limit orders keep unfilled pUSD in wallet (`inflight_usd`) while any
            # already-matched partial fills (`matched_intent_usd`) drop `onchain_cash` before or during collateral sync.
            cash_diff = min(
                [raw_cash_diff]
                + [abs(oc - max(0.0, eff_state_cash - matched_intent_usd)) for oc in onchain_candidates]
                + [abs(oc - max(0.0, eff_state_cash - inflight_usd)) for oc in onchain_candidates]
                + [abs(oc - max(0.0, eff_state_cash - matched_intent_usd - inflight_usd)) for oc in onchain_candidates]
            )
        else:
            cash_diff = raw_cash_diff
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
        tok_groups: Dict[str, Dict[str, Any]] = {}
        for idx_op, op in enumerate(ledger.get("open_positions") or []):
            if not isinstance(op, dict):
                continue
            tk_key = str(op.get("token_id") or "").strip() or f"__single__:{op.get('trade_id') or idx_op}"
            grp = tok_groups.setdefault(
                tk_key,
                {
                    "trade_ids": [],
                    "shares_ledger": 0.0,
                    "shares_onchain": op.get("shares_onchain"),
                    "best_bid": float(op.get("best_bid") or 0.50),
                },
            )
            grp["trade_ids"].append(str(op.get("trade_id") or ""))
            grp["shares_ledger"] += float(op.get("shares_ledger") or 0.0)
            if grp["shares_onchain"] is None and op.get("shares_onchain") is not None:
                grp["shares_onchain"] = op.get("shares_onchain")
            grp["best_bid"] = max(grp["best_bid"], float(op.get("best_bid") or 0.50))

        for grp in tok_groups.values():
            sh_led = float(grp["shares_ledger"] or 0.0)
            sh_chain = grp["shares_onchain"]
            if sh_chain is not None and not settling_open:
                sh_diff = abs(sh_led - float(sh_chain))
                if sh_diff > sh_tol:
                    est_usd = sh_diff * max(0.50, float(grp["best_bid"] or 0.50))
                    max_share_usd_gap = max(max_share_usd_gap, est_usd)
                    anomalies.append(
                        f"CTF_SHARE_DISCREPANCY:{'+'.join(grp['trade_ids'])}:ledger={sh_led:.2f}_vs_onchain={float(sh_chain):.2f}"
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

    def _compute_riskless_live_and_quoting_metrics(self, ledger: Dict[str, Any]) -> Dict[str, Any]:
        """Computes pure zero-loss live W/L, post-lock sentinel stats, and live working CLOB Maker quoting utilization."""
        riskless_only_mode, paused_sleeves = _load_riskless_governance_flags()
        directional_sleeves = {"SLEEVE_1_CORE_302", "SLEEVE_1_SUBHOURLY_15M"}
        live_by_sl = ledger.get("live_by_sleeve") or {}

        pure_rl_trades, pure_rl_wins, pure_rl_losses, pure_rl_flat_merges, pure_rl_pnl = 0, 0, 0, 0, 0.0
        for sl, rec in live_by_sl.items():
            if not isinstance(rec, dict):
                continue
            if sl in directional_sleeves or sl.upper() in paused_sleeves:
                continue
            n_tr = int(rec.get("real_trades") or 0)
            pure_rl_trades += n_tr
            pure_rl_wins += int(rec.get("wins") or 0)
            pure_rl_losses += int(rec.get("losses") or 0)
            pure_rl_flat_merges += int(rec.get("flat_merges") or 0)
            pure_rl_pnl += float(rec.get("verified_net_pnl_usd") or 0.0)

        st_path = self.data_dir / "live_harvester_state.json"
        st = json.loads(st_path.read_text(encoding="utf-8")) if st_path.exists() else {}
        rl_epoch_cut = str((self.cfg.get("riskless_mandate") or {}).get("riskless_epoch_start_utc") or "2026-11-04T02:05:00Z")
        post_lock_w, post_lock_l, post_lock_flat, post_lock_pnl = 0, 0, 0, 0.0
        from src.paa_os.optimizer import group_closed_positions_by_box
        norm_closed_for_lock = [
            reconcile_closed_position_record(raw_c)[0]
            for raw_c in (st.get("closed_positions") or [])
            if isinstance(raw_c, dict) and not is_phantom_unfilled_position(raw_c)
        ]
        for c in group_closed_positions_by_box(norm_closed_for_lock, st.get("active_positions") or []):
            if not isinstance(c, dict):
                continue
            ts_c = str(c.get("entry_time_utc") or c.get("settled_at_utc") or c.get("exit_time_utc") or "")
            if not ts_c:
                raw_ts = float(c.get("entry_ts") or c.get("exit_ts") or 0.0)
                if raw_ts > 0.0:
                    ts_c = datetime.fromtimestamp(raw_ts, tz=timezone.utc).isoformat()
            if ts_c < rl_epoch_cut:
                continue
            p_u = float(c.get("net_pnl_usd", c.get("realized_pnl_usd", 0.0)) or 0.0)
            rsn_u = str(c.get("close_reason") or "").upper()
            post_lock_pnl += p_u
            if abs(p_u) <= 1e-6 and (c.get("won") is True or "MERGED" in rsn_u):
                post_lock_flat += 1
            elif p_u > 0 or c.get("won") is True:
                post_lock_w += 1
            elif p_u < -1e-6:
                post_lock_l += 1

        now_q = time.time()
        pend_map = st.get("pending_entry_intents") or {}
        act_map = st.get("active_positions") or {}
        fresh_intents = [
            i for i in pend_map.values()
            if isinstance(i, dict)
            and (now_q - max(float(i.get("heartbeat_ts") or 0.0), float(i.get("ts", i.get("created_ts", 0.0)) or 0.0))) <= 90.0
        ]
        intents_usd = sum(float(i.get("notional_usd", 0.0) or 0.0) for i in fresh_intents)
        intents_cnt = len(fresh_intents)
        tracked_clob_oids = {
            str(v).strip()
            for rec_d in (*pend_map.values(), *act_map.values())
            if isinstance(rec_d, dict)
            for v in (
                rec_d.get("entry_order_id"),
                rec_d.get("order_id"),
                rec_d.get("exit_order_id"),
                rec_d.get("unwind_order_id"),
                rec_d.get("maker_order_id"),
            )
            if v
        }

        def _clob_created_ts(ord_d: Dict[str, Any]) -> float:
            raw_ct = ord_d.get("created_at")
            if isinstance(raw_ct, (int, float)):
                v_ct = float(raw_ct)
                return v_ct / 1000.0 if v_ct > 1e12 else v_ct
            if isinstance(raw_ct, str) and raw_ct.strip():
                s_ct = raw_ct.strip()
                if s_ct.isdigit():
                    v_ct = float(s_ct)
                    return v_ct / 1000.0 if v_ct > 1e12 else v_ct
                try:
                    return datetime.fromisoformat(s_ct.replace("Z", "+00:00")).timestamp()
                except Exception:
                    return 0.0
            return 0.0

        ord_cache_p = Path("/tmp/dominus_clob_open_orders_cache.json")
        if ord_cache_p.exists() and (now_q - ord_cache_p.stat().st_mtime) <= 60.0:
            try:
                raw_ords = json.loads(ord_cache_p.read_text(encoding="utf-8"))
                if isinstance(raw_ords, list):
                    buy_ords = []
                    for o in raw_ords:
                        if (
                            not isinstance(o, dict)
                            or str(o.get("status") or "").upper() not in ("LIVE", "OPEN")
                            or str(o.get("side") or "BUY").upper() != "BUY"
                            or max(0.0, float(o.get("original_size") or 0.0) - float(o.get("size_matched") or 0.0)) <= 0.001
                        ):
                            continue
                        oid_o = str(o.get("id") or o.get("orderID") or "").strip()
                        cts_o = _clob_created_ts(o)
                        if cts_o > 0.0 and (now_q - cts_o) > 3600.0 and (not oid_o or oid_o not in tracked_clob_oids):
                            continue
                        buy_ords.append(o)
                    intents_usd = sum(
                        max(0.0, float(o.get("original_size") or 0.0) - float(o.get("size_matched") or 0.0)) * float(o.get("price") or 0.0)
                        for o in buy_ords
                    )
                    intents_cnt = len(buy_ords)
            except Exception:
                pass

        nav_book = max(0.01, float(ledger.get("portfolio_nav_book_usd") or ledger.get("free_cash_pusd") or 0.01))
        open_cost = float(ledger.get("open_cost_basis_usd") or 0.0)
        eff_deploy_pct = round(min(100.0, 100.0 * (open_cost + intents_usd) / nav_book), 2)

        return {
            "operating_mode": "RISKLESS_PAA" if riskless_only_mode else "HYBRID_PAA",
            "riskless_only_mode": riskless_only_mode,
            "paused_riskless_sleeves": sorted(paused_sleeves),
            "pure_riskless_live_trades": pure_rl_trades,
            "pure_riskless_live_wins": pure_rl_wins,
            "pure_riskless_live_losses": pure_rl_losses,
            "pure_riskless_flat_merges": pure_rl_flat_merges,
            "pure_riskless_live_wr_pct": round(100.0 * pure_rl_wins / pure_rl_trades, 2) if pure_rl_trades > 0 else 100.0,
            "pure_riskless_realized_pnl_usd": round(pure_rl_pnl, 4),
            "riskless_epoch_start_utc": rl_epoch_cut,
            "post_lock_wins": post_lock_w,
            "post_lock_losses": post_lock_l,
            "post_lock_flat_merges": post_lock_flat,
            "post_lock_net_pnl_usd": round(post_lock_pnl, 4),
            "working_maker_buy_orders_count": intents_cnt,
            "working_maker_quoting_usd": round(intents_usd, 2),
            "effective_deploy_or_quoting_pct": eff_deploy_pct,
        }

    def measure_and_record(
        self,
        live_rpc_check: bool = True,
        ledger_override: Optional[Dict[str, Any]] = None,
        state_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Runs full financial measurement, strictly separates realized vs simulated PnL, and enforces safeguards."""
        if ledger_override is not None:
            ledger = ledger_override
        elif self.data_dir != DATA_PM:
            try:
                ledger = reconcile_authoritative_ledger(live_rpc_check=live_rpc_check, data_dir=self.data_dir)
            except TypeError:
                ledger = reconcile_authoritative_ledger(live_rpc_check=live_rpc_check)
        else:
            ledger = reconcile_authoritative_ledger(live_rpc_check=live_rpc_check)
        if ledger_override is None and state_override is None and isinstance(ledger, dict) and "reconciled_at_utc" in ledger:
            ledger_file = self.paa_dir / "authoritative_financial_ledger.json"
            tmp_lf = ledger_file.with_suffix(".json.tmp")
            tmp_lf.write_text(json.dumps(ledger, indent=2, default=str), encoding="utf-8")
            tmp_lf.replace(ledger_file)
        exec_m = self._compute_execution_and_slippage_metrics()
        sim_m = self._compute_simulated_benchmarks()
        riskless_m = self._compute_riskless_live_and_quoting_metrics(ledger)
        budget_m = self.budget.get_usage_summary()
        acct_ok, disc_usd, anomalies = self.verify_accounting_integrity(ledger, state_override=state_override)

        if not acct_ok:
            self.enforce_accounting_safeguard(disc_usd, anomalies)
        elif (live_rpc_check or ledger_override is not None) and "POLYGON_RPC_READONLY_FALLBACK_TO_STATE" not in (
            ledger.get("watchdog_alerts") or []
        ):
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
            "zero_loss_shadow_t1000_pnl_usd": sim_m["zero_loss_shadow_t1000_pnl_usd"],
            "zero_loss_shadow_wins": sim_m["zero_loss_shadow_wins"],
            "simulated_paper_oos_pnl_usd": sim_m["simulated_paper_oos_pnl_usd"],
            "riskless_metrics": riskless_m,
            "details": {
                "anomalies": anomalies,
                "execution_metrics": exec_m,
                "simulated_benchmarks": sim_m,
                "riskless_metrics": riskless_m,
                "budget_summary": budget_m,
                "watchdog_alerts": ledger.get("watchdog_alerts") or [],
            },
        }
        self.db.record_financial_snapshot(snapshot)
        zt_cfg = self.cfg.get("zero_trust") or {}
        fin_ttl = float(zt_cfg.get("financial_fact_ttl_sec", 300.0))
        lat_ttl = float(zt_cfg.get("latency_fact_ttl_sec", 180.0))
        src_type = "POLYGON_RPC_AND_STATE_LEDGER" if live_rpc_check else "AUTHORITATIVE_STATE_LEDGER"
        self.db.upsert_verified_fact(
            fact_key="riskless.mode_locked",
            category="RISKLESS_GOVERNANCE",
            value=bool(riskless_m["riskless_only_mode"]),
            epistemic_status="VERIFIED_FACT",
            source_type="GOVERNANCE_CONFIG",
            source_ref="config/polymarket_strategy_and_risk.json:directional.riskless_only_mode",
            verified_by="PAAAccountant",
            ttl_sec=fin_ttl,
            revalidation_rule="RECHECK_GOVERNANCE_CONFIG_EVERY_CYCLE",
        )
        self.db.upsert_verified_fact(
            fact_key="riskless.pure_live_win_rate_pct",
            category="FINANCIAL_TRUTH",
            value=riskless_m["pure_riskless_live_wr_pct"],
            epistemic_status="VERIFIED_FACT",
            source_type=src_type,
            source_ref="PAAAccountant._compute_riskless_live_and_quoting_metrics",
            verified_by="PAAAccountant",
            ttl_sec=fin_ttl,
            revalidation_rule="RECOMPUTE_FROM_RECONCILED_PURE_RISKLESS_SLEEVES",
        )
        self.db.upsert_verified_fact(
            fact_key="wallet.free_cash_pusd",
            category="FINANCIAL_TRUTH",
            value=round(snapshot["free_cash_pusd"], 4),
            epistemic_status="VERIFIED_FACT",
            source_type=src_type,
            source_ref="financial_snapshots:free_cash_pusd",
            verified_by="PAAAccountant",
            ttl_sec=fin_ttl,
            revalidation_rule="REQUERY_POLYGON_WALLET_AND_HARVESTER_STATE",
        )
        self.db.upsert_verified_fact(
            fact_key="wallet.verified_realized_net_pnl_usd",
            category="FINANCIAL_TRUTH",
            value=round(snapshot["verified_realized_net_pnl_usd"], 4),
            epistemic_status="VERIFIED_FACT",
            source_type=src_type,
            source_ref="financial_snapshots:verified_realized_net_pnl_usd",
            verified_by="PAAAccountant",
            ttl_sec=fin_ttl,
            revalidation_rule="RECONCILE_SETTLED_POSITIONS_NET_OF_FEES",
        )
        self.db.upsert_verified_fact(
            fact_key="wallet.accounting_reconciled_ok",
            category="FINANCIAL_TRUTH",
            value=bool(acct_ok),
            epistemic_status="VERIFIED_FACT",
            source_type=src_type,
            source_ref="PAAAccountant.verify_accounting_integrity",
            verified_by="PAAAccountant",
            ttl_sec=fin_ttl,
            revalidation_rule="REVERIFY_CASH_AND_CTF_SHARES",
        )
        if exec_m.get("clob_post_p50_ms") is not None:
            self.db.upsert_verified_fact(
                fact_key="clob.http_post_p50_ms",
                category="EXCHANGE_OBSERVATION",
                value=exec_m["clob_post_p50_ms"],
                epistemic_status="OBSERVATION",
                source_type="LIVE_ORDERS_TELEMETRY",
                source_ref="data/polymarket/live_orders.jsonl:clob_http_post_ms",
                verified_by="PAAAccountant",
                ttl_sec=lat_ttl,
                revalidation_rule="EXPIRES_AFTER_180S_DO_NOT_TREAT_AS_PERMANENT_TRUTH",
            )
        self.db.record_heartbeat(
            "paa_accountant",
            status="OK" if acct_ok else "ACCOUNTING_SAFEGUARD",
            details={"nav_bid": snapshot["nav_mark_to_bid_usd"], "accounting_ok": acct_ok},
        )
        return snapshot
