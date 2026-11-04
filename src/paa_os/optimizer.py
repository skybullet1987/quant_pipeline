"""
PAA Riskless Portfolio Optimizer & Box-Grouped Ledger Aggregator (`src/paa_os/optimizer.py`).

Provides two core capabilities for the 100% Riskless Polymarket Autonomous Agent (PAA):
  1. `group_closed_positions_by_box`: Deterministically aggregates multi-leg arbitrage positions
     (`box_id`, `is_dominance_box`, `box_partner_trade_id`) into atomic box-level PnL records
     while holding back legs whose partner leg is still open in `active_positions`. Prevents
     `$0.00` hedge legs of winning `$1.00`/`$2.00` dominance boxes from triggering false
     `RISKLESS_ZERO_LOSS_BREACH` P0 alerts or corrupting sleeve win/loss accounting.
  2. `PAAOptimizer`: Evaluates live riskless capital utilization, `BOND1` pool balance vs fast
     complete-set / `D1` / `NR4-NR5` liquidity headroom, and near-`Grad-8` zero-loss sleeves,
     producing envelope-safe recommendations for `paa_cli.py hourly-opt`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set


def _sf(val: Any, default: float = 0.0) -> float:
    if val in (None, ""):
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def group_closed_positions_by_box(
    closed_positions: Iterable[Mapping[str, Any]],
    active_positions: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Collapse multi-leg arbitrage box legs sharing a `box_id` into a single box-level record:
      - Sums `notional_usd`, `payout_usd`, `fee_usd`, and `net_pnl_usd` across all settled legs of the box.
      - If ANY sibling leg of `box_id` (or `box_partner_trade_id`) is still open in `active_positions`,
        marks `box_settlement_pending = True` and omits it from settled win/loss breach checks until all
        legs of the box have settled!
      - Standalone single-leg positions (`BOND1`, `W1`, `PreSplitInventoryGun` cycle summaries, etc.) pass
        through unchanged.
    """
    active_map = active_positions if isinstance(active_positions, Mapping) else {}
    open_box_ids: Set[str] = set()
    open_trade_ids: Set[str] = set()
    for tid, pos in active_map.items():
        open_trade_ids.add(str(tid))
        if isinstance(pos, Mapping):
            if pos.get("trade_id"):
                open_trade_ids.add(str(pos["trade_id"]))
            b_open = str(pos.get("box_id") or "").strip()
            if b_open:
                open_box_ids.add(b_open)

    grouped_order: List[str] = []
    box_buckets: Dict[str, List[Dict[str, Any]]] = {}
    passthrough: Dict[str, Dict[str, Any]] = {}

    for idx, raw in enumerate(closed_positions or []):
        if not isinstance(raw, Mapping):
            continue
        rec = dict(raw)
        b_id = str(rec.get("box_id") or "").strip()
        partner_tid = str(rec.get("box_partner_trade_id") or "").strip()
        is_box_leg = bool(
            b_id
            and (
                rec.get("is_dominance_box")
                or rec.get("is_locked_arbitrage_box")
                or partner_tid
                or str(rec.get("box_type") or "").upper()
                in {"DOMINANCE", "COMPLETE_SET", "NEGRISK_2LEG", "MULTI_LEG_BUNDLE", "SPORTS_CORRIDOR", "NBA_DOMINANCE", "BARRIER_MONO", "LADDER_MONO"}
            )
        )
        if not is_box_leg:
            key = f"SINGLE_{idx}_{rec.get('trade_id') or idx}"
            grouped_order.append(key)
            passthrough[key] = rec
            continue

        # Skip legs whose partner or box is still open in active_positions (awaiting redemption/merge)
        if b_id in open_box_ids or (partner_tid and partner_tid in open_trade_ids):
            continue

        b_key = f"BOX::{b_id}"
        if b_key not in box_buckets:
            grouped_order.append(b_key)
            box_buckets[b_key] = []
        box_buckets[b_key].append(rec)

    out: List[Dict[str, Any]] = []
    for key in grouped_order:
        if key in passthrough:
            out.append(passthrough[key])
            continue
        legs = box_buckets[key]
        if len(legs) == 1:
            leg0 = dict(legs[0])
            partner_0 = str(leg0.get("box_partner_trade_id") or "").strip()
            if partner_0 and partner_0 in open_trade_ids:
                continue
            out.append(leg0)
            continue

        first = dict(legs[0])
        b_id = str(first.get("box_id") or "")
        tot_notional = round(sum(_sf(x.get("notional_usd")) for x in legs), 4)
        tot_payout = round(sum(_sf(x.get("payout_usd")) for x in legs), 4)
        tot_fee = round(sum(_sf(x.get("fee_usd")) for x in legs), 4)
        tot_pnl = round(
            sum(_sf(x.get("net_pnl_usd", x.get("realized_pnl_usd", 0.0))) for x in legs),
            4,
        )
        all_phantom = all(
            x.get("close_reason") == "MARKET_RESOLVED_NO_INVENTORY"
            and not bool(x.get("inventory_reconciled", True))
            and str(x.get("exit_order_status") or "") == "ENTRY_OUTCOME_UNKNOWN"
            for x in legs
        )
        merged = dict(first)
        merged.update(
            {
                "trade_id": b_id or str(first.get("trade_id") or ""),
                "box_id": b_id,
                "is_dominance_box": True,
                "box_leg_count": len(legs),
                "box_leg_trade_ids": [str(x.get("trade_id") or "") for x in legs],
                "notional_usd": tot_notional,
                "payout_usd": tot_payout,
                "fee_usd": tot_fee,
                "net_pnl_usd": tot_pnl,
                "realized_pnl_usd": tot_pnl,
                "won": bool(tot_pnl >= -1e-6),
                "exit_fee_estimated": False,
                "entry_time_utc": max(
                    (str(x.get("entry_time_utc") or "") for x in legs),
                    default=str(first.get("entry_time_utc") or ""),
                ),
                "settled_at_utc": max(
                    (str(x.get("settled_at_utc") or "") for x in legs),
                    default=str(first.get("settled_at_utc") or ""),
                ),
            }
        )
        if not all_phantom and merged.get("close_reason") == "MARKET_RESOLVED_NO_INVENTORY":
            merged["close_reason"] = "BOX_MULTI_LEG_SETTLED"
        out.append(merged)
    return out


class PAAOptimizer:
    """
    Hourly Riskless Portfolio Velocity & Pool Allocation Optimizer (`paa_cli.py hourly-opt`).
    Operates strictly within the 100% riskless parameter envelope — never enables directional sleeves.
    """

    def __init__(self, repo_root: Path, data_dir: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root)
        self.data_dir = Path(data_dir) if data_dir is not None else (self.repo_root / "data" / "polymarket")

    def run_hourly_optimization(self) -> Dict[str, Any]:
        st_path = self.data_dir / "live_harvester_state.json"
        a124_path = self.data_dir / "alpha124_shadow_state.json"
        cfg_path = self.repo_root / "config" / "polymarket_strategy_and_risk.json"

        st = json.loads(st_path.read_text(encoding="utf-8")) if st_path.exists() else {}
        a124 = json.loads(a124_path.read_text(encoding="utf-8")) if a124_path.exists() else {}
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}

        bankroll = _sf(st.get("live_bankroll"), 0.0)
        active_pos = st.get("active_positions") or {}
        grouped_closed = group_closed_positions_by_box(st.get("closed_positions") or [], active_pos)

        bond1_deployed = sum(
            _sf(p.get("notional_usd"))
            for p in active_pos.values()
            if isinstance(p, dict) and str(p.get("sleeve") or "").startswith("BOND1")
        )
        box_deployed = sum(
            _sf(p.get("notional_usd"))
            for p in active_pos.values()
            if isinstance(p, dict) and not str(p.get("sleeve") or "").startswith("BOND1")
        )

        by_sl = a124.get("by_sleeve") or a124.get("per_strategy") or {}
        grad8_zero_loss: List[str] = []
        near_grad8_zero_loss: List[Dict[str, Any]] = []
        for sl_name, rec in sorted(by_sl.items()):
            if not isinstance(rec, dict):
                continue
            closed_n = int(rec.get("closed", 0) or 0)
            losses_n = int(rec.get("losses", 0) or 0)
            pnl_u = _sf(rec.get("legging_adjusted_pnl_t1000_usd", rec.get("realized_pnl_t1000_usd", 0.0)))
            if losses_n == 0 and pnl_u > 0.0:
                if closed_n >= 8:
                    grad8_zero_loss.append(sl_name)
                elif 4 <= closed_n < 8:
                    near_grad8_zero_loss.append({"sleeve": sl_name, "closed": closed_n, "pnl_t1000_usd": round(pnl_u, 2)})

        rl_boxes_cfg = cfg.get("riskless_boxes") or {}
        bond1_pool_pct = _sf(rl_boxes_cfg.get("seed_zero_loss_focus_bond1_pool_pct"), 0.92)
        dir_cfg = cfg.get("directional") or {}
        riskless_locked = bool(dir_cfg.get("riskless_only_mode", False))

        recommendations: List[str] = []
        if bond1_pool_pct > 0.94:
            recommendations.append(
                f"Cap seed_zero_loss_focus_bond1_pool_pct <= 0.92 (currently {bond1_pool_pct:.2f}) while keeping <120ms fast-box preemption active."
            )
        if not riskless_locked:
            recommendations.append("CRITICAL: Set directional.riskless_only_mode=true immediately.")

        return {
            "ts_unix": round(time.time(), 2),
            "riskless_only_mode_verified": riskless_locked,
            "live_bankroll_usd": round(bankroll, 2),
            "bond1_deployed_usd": round(bond1_deployed, 2),
            "fast_box_deployed_usd": round(box_deployed, 2),
            "box_grouped_closed_count": len(grouped_closed),
            "grad8_zero_loss_sleeves": grad8_zero_loss,
            "near_grad8_zero_loss_sleeves": near_grad8_zero_loss,
            "bond1_pool_pct": bond1_pool_pct,
            "recommendations": recommendations,
        }
