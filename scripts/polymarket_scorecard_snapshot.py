#!/usr/bin/env python3
"""Read-only Live + Shadow Polymarket scorecard snapshot for scheduled monitoring."""

import json
import pathlib
import subprocess

ROOT = pathlib.Path("/home/skybullet1987/quant_pipeline")
SERVICES = [
    "polymarket-live-harvester",
    "polymarket-trader",
    "polymarket-exp316-shadow",
    "polymarket-recorder",
    "polymarket-recorder-eth",
    "polymarket-recorder-sol",
    "polymarket-recorder-xrp",
]


def _read_json(rel_path: str) -> dict:
    p = ROOT / rel_path
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc)}


def main() -> None:
    svc_map = {
        s: subprocess.run(
            ["systemctl", "--user", "is-active", s],
            capture_output=True,
            text=True,
        ).stdout.strip()
        for s in SERVICES
    }

    live = _read_json("data/polymarket/live_harvester_state.json")
    paper = _read_json("data/polymarket/paper_trader_state.json")
    sol = _read_json("data/polymarket/state_shadow_sol_v392.json")
    xrp = _read_json("data/polymarket/state_shadow_xrp_v392.json")
    exp316 = _read_json("data/exp316/exp316_shadow_state.json")

    closed = live.get("closed_positions") or []
    wins = sum(
        1
        for t in closed
        if float(
            t.get("realized_pnl_usd")
            or t.get("net_pnl_usd")
            or (
                float(t.get("realized_exit_cash", 0.0))
                - float(t.get("notional_usd", 0.0))
                - float(t.get("fee_usd", 0.0))
            )
        )
        > 0
    )

    j_out = subprocess.run(
        [
            "journalctl",
            "--user",
            "-u",
            "polymarket-live-harvester",
            "--since",
            "24 hours ago",
            "--no-pager",
        ],
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    p3a = [line for line in j_out if "SHADOW_PHASE3A" in line][-5:]
    p4 = [line for line in j_out if "SHADOW_PHASE4" in line][-5:]

    alt_keys = [
        "timestamp",
        "current_equity",
        "realized_pnl",
        "total_trades_settled",
        "winning_trades",
        "losing_trades",
        "win_rate_pct",
        "profit_factor",
        "active_open_positions_count",
        "ready_for_live_graduation",
        "graduation_criteria",
    ]

    snapshot = {
        "services": svc_map,
        "all_services_active": all(v == "active" for v in svc_map.values()),
        "live_v392": {
            "updated_at_utc": live.get("updated_at_utc"),
            "live_bankroll_usd": live.get("live_bankroll"),
            "total_account_equity_usd": live.get("total_account_equity"),
            "high_water_mark_equity_usd": live.get("high_water_mark_equity"),
            "active_positions_count": live.get("active_positions_count"),
            "closed_positions_count": len(closed),
            "closed_wins": wins,
            "progress_to_n40_gate": f"{len(closed)}/40",
            "distance_to_88_dynamic_tier_usd": round(
                max(0.0, 88.0 - float(live.get("total_account_equity") or 0.0)), 2
            ),
            "distance_to_110_scaleup_tier_usd": round(
                max(0.0, 110.0 - float(live.get("total_account_equity") or 0.0)), 2
            ),
            "risk_halt": live.get("risk_halt"),
            "reconciliation_required": live.get("reconciliation_required"),
            "global_halt_reasons": live.get("global_halt_reasons"),
        },
        "paper_sleeve1_benchmark": paper.get("validation_oos_epoch", {}),
        "shadow_sol_v392": {k: sol.get(k) for k in alt_keys},
        "shadow_xrp_v392": {k: xrp.get(k) for k in alt_keys},
        "shadow_exp316": exp316,
        "shadow_phase3a_recent_24h": p3a,
        "shadow_phase4_recent_24h": p4,
    }
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()
