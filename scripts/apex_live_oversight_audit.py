#!/usr/bin/env python3
"""
APEX 24/7 Automated Post-Rebalance Oversight & Mainnet Microstructure Recorder
==============================================================================
Triggered every 4 hours (`00:08, 04:08, 08:08, 12:08, 16:08, 20:08 UTC`) via
`apex-oversight-audit.timer` on `kraken-finland` to execute:
  1. Post-rebalance live profitability, maker compliance, & reconciliation audit
     (`data/apex/live_oversight_ledger.jsonl`).
  2. 4-Track Champion/Challenger shadow arena attribution (`v5.0` vs `v5.1 iso-vol`
     vs `v5.1 VT35` vs `EXP-506b`).
  3. Authoritative Mainnet Top-15 Majors perp-oracle basis, open-interest, funding,
     and Top-5 L2 OBI snapshot recording (`data/apex/mainnet_microstructure_snapshots.jsonl`)
     for sub-5m basis & liquidation-cascade strategy validation.
  4. Cross-platform Dominus Treasury RoC comparison (Polymarket Live vs APEX).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hyperliquid.info import Info
from hyperliquid.utils import constants
from src.execution.ws_market_cache import compute_l2_microstructure
from src.research.apex_champion_challenger import compute_live_profitability_decomposition
from scripts.apex_mainnet_canary_preflight import evaluate_canary_readiness


def run_oversight_cycle(repo_root: Path = REPO_ROOT) -> Dict[str, Any]:
    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    apex_dir = repo_root / "data" / "apex"
    apex_dir.mkdir(parents=True, exist_ok=True)

    state_path = repo_root / "data" / "papertrade_state.json"
    journal_path = repo_root / "data" / "papertrade_journal.jsonl"
    shadow_path = apex_dir / "champion_challenger_shadow.json"
    pm_path = repo_root / "data" / "polymarket" / "live_harvester_state.json"

    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    shadow = json.loads(shadow_path.read_text(encoding="utf-8")) if shadow_path.exists() else {}
    pm_state = json.loads(pm_path.read_text(encoding="utf-8")) if pm_path.exists() else {}

    decomp = compute_live_profitability_decomposition(journal_path)
    canary = evaluate_canary_readiness(repo_root=repo_root)

    # Record Mainnet Top-15 Majors Basis + Open Interest + L2 OBI_5 snapshot
    basis_rows: List[Dict[str, Any]] = []
    try:
        m_info = Info(constants.MAINNET_API_URL, skip_ws=True)
        meta, ctxs = m_info.meta_and_asset_ctxs()
        univ = meta.get("universe", [])
        ranked = []
        for idx, tok in enumerate(univ):
            if idx < len(ctxs):
                dv = float(ctxs[idx].get("dayNtlVlm") or 0.0)
                ranked.append((dv, tok["name"], int(tok.get("szDecimals", 2)), ctxs[idx]))
        ranked.sort(key=lambda x: x[0], reverse=True)
        for dv, coin, sz_dec, ctx in ranked[:15]:
            oracle_px = float(ctx.get("oraclePx") or 0.0)
            mark_px = float(ctx.get("markPx") or 0.0)
            premium_bps = ((mark_px - oracle_px) / oracle_px * 10000.0) if oracle_px > 0 else 0.0
            obi_5 = 0.0
            spread_bps = 0.0
            try:
                l2 = m_info.l2_snapshot(coin)
                lvls = l2.get("levels", [[], []])
                ms = compute_l2_microstructure(lvls[0], lvls[1])
                if ms:
                    obi_5 = round(ms["obi_5"], 4)
                    spread_bps = round(ms["spread_bps"], 2)
            except Exception:
                pass
            basis_rows.append({
                "coin": coin,
                "oracle_px": oracle_px,
                "mark_px": mark_px,
                "basis_bps": round(premium_bps, 2),
                "funding_1h_bps": round(float(ctx.get("funding") or 0.0) * 10000.0, 4),
                "open_interest": float(ctx.get("openInterest") or 0.0),
                "day_ntl_vlm_usd": round(dv, 2),
                "obi_5": obi_5,
                "spread_bps": spread_bps,
            })
        snap_file = apex_dir / "mainnet_microstructure_snapshots.jsonl"
        with open(snap_file, "a", encoding="utf-8") as sf:
            sf.write(json.dumps({"timestamp_utc": now_utc, "majors": basis_rows}) + "\n")
    except Exception as exc:
        basis_rows = [{"error": str(exc)}]

    # Cross-platform treasury comparison (Polymarket Live vs APEX)
    pm_closed = pm_state.get("closed_positions") or []
    pm_net_pnl = round(sum(float(c.get("net_pnl_usd", 0.0)) for c in pm_closed), 2)
    pm_eq = round(float(pm_state.get("total_account_equity") or pm_state.get("live_bankroll") or 0.0), 2)

    eq_block = state.get("equity") or {}
    acct_block = state.get("accounting_ledger") or {}
    shadow_tracks = {
        k: {"nav": v.get("nav"), "hwm": v.get("hwm")}
        for k, v in (shadow.get("tracks") or {}).items()
    }
    sh_hist = shadow.get("history") or []
    latest_regime = (sh_hist[-1].get("regime") if sh_hist else None) or {}

    record = {
        "timestamp_utc": now_utc,
        "apex": {
            "version": state.get("version"),
            "circuit_breaker": state.get("circuit_breaker"),
            "reconciliation_status": acct_block.get("reconciliation_status"),
            "valuation_residual_usd": acct_block.get("valuation_residual_usd"),
            "nav_usd": eq_block.get("current_strategy_equity"),
            "hwm_usd": eq_block.get("historical_hwm"),
            "drawdown_pct": eq_block.get("drawdown_pct"),
            "active_leverage": eq_block.get("active_leverage"),
            "ws_market_cache": state.get("ws_market_cache") or {},
            "regime": latest_regime,
            "shadow_tracks": shadow_tracks,
            "journal_decomposition": decomp,
            "canary_gate_ready": canary["ready_for_mainnet_canary"],
            "post_v51_fills": canary["post_v51_fills"],
            "total_gate2_fills": canary["total_gate2_fills"],
        },
        "polymarket_comparison": {
            "equity_usd": pm_eq,
            "epoch_closed_trades": len(pm_closed),
            "epoch_net_pnl_usd": pm_net_pnl,
            "risk_halt": bool(pm_state.get("risk_halt", False)),
        },
        "recorded_mainnet_majors": len(basis_rows),
    }

    ledger_file = apex_dir / "live_oversight_ledger.jsonl"
    with open(ledger_file, "a", encoding="utf-8") as lf:
        lf.write(json.dumps(record) + "\n")

    print(
        f"[{now_utc}] APEX Oversight OK | ver={record['apex']['version']} | "
        f"NAV=${record['apex']['nav_usd']} | Recon={record['apex']['reconciliation_status']} | "
        f"PostV51Fills={canary['post_v51_fills']}/100 | MajorsSnap={len(basis_rows)}"
    )
    return record


if __name__ == "__main__":
    run_oversight_cycle()
