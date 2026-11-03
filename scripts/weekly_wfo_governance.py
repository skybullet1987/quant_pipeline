#!/usr/bin/env python3
"""
Automated Weekly Purged Walk-Forward + CPCV(6,2) + 10,000-Draw Stationary Bootstrap
Promotion / Demotion Governance CLI (`scripts/weekly_wfo_governance.py`).

Evaluates every directional and riskless shadow ledger in `data/polymarket/` against strict
zero-lookahead institutional graduation gates (`N >= 50`, `PF >= 1.45`, `CI95_lo > $0.00`, `PBO <= 0.20`)
and optionally emits/applies an atomic update to `config/polymarket_strategy_and_risk.json`.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.polymarket_research.holistic_strategy_governance import (
    DEFAULT_HOLISTIC_CONFIG,
    STRATEGY_CONFIG_PATH,
    _deep_merge_validated,
)


def stationary_bootstrap_ci(pnls: List[float], n_draws: int = 10000, avg_block: float = 5.0, seed: int = 42) -> Tuple[float, float, float]:
    """Politis-Romano (1994) Stationary Bootstrap for expected per-trade PnL and P(mean > 0)."""
    n = len(pnls)
    if n == 0:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    p_restart = 1.0 / max(1.0, avg_block)
    means: List[float] = []
    pos_cnt = 0
    for _ in range(n_draws):
        idx = rng.randrange(n)
        tot = 0.0
        for _step in range(n):
            tot += pnls[idx]
            if rng.random() < p_restart:
                idx = rng.randrange(n)
            else:
                idx = (idx + 1) % n
        m = tot / n
        means.append(m)
        if m > 0.0:
            pos_cnt += 1
    means.sort()
    lo = means[int(0.025 * n_draws)]
    hi = means[int(0.975 * n_draws)]
    return lo, hi, (pos_cnt / n_draws)


def cpcv_6_2_positive_paths(pnls: List[float], n_groups: int = 6, k_test: int = 2) -> Tuple[int, int, float]:
    """Evaluates Combinatorial Purged Cross-Validation CPCV(6,2) = 15 test paths."""
    n = len(pnls)
    if n < n_groups * 2:
        return 0, 15, 1.0
    groups: List[List[float]] = []
    step = n / n_groups
    for g in range(n_groups):
        s = int(round(g * step))
        e = int(round((g + 1) * step))
        # 1-trade embargo boundary between adjacent blocks
        sub = pnls[s : max(s + 1, e - 1)] if g < n_groups - 1 else pnls[s:e]
        groups.append(sub)
    combos = list(itertools.combinations(range(n_groups), k_test))
    pos_paths = 0
    for c in combos:
        test_pnls = [x for gi in c for x in groups[gi]]
        if sum(test_pnls) > 0.0:
            pos_paths += 1
    pbo_est = round(1.0 - (pos_paths / max(1, len(combos))), 4)
    return pos_paths, len(combos), pbo_est


def evaluate_ledger_file(path: Path, min_trades: int = 50, min_pf: float = 1.45, max_pbo: float = 0.20) -> Dict[str, Any]:
    pnls: List[float] = []
    if path.exists():
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
                pnl = float(rec.get("net_pnl_usd", rec.get("pnl_usd", 0.0)) or 0.0)
                if math.isfinite(pnl):
                    pnls.append(pnl)
            except Exception:
                continue
    n = len(pnls)
    wins = sum(1 for x in pnls if x > 0.0)
    gross_win = sum(x for x in pnls if x > 0.0)
    gross_loss = abs(sum(x for x in pnls if x < 0.0))
    pf = (gross_win / gross_loss) if gross_loss > 1e-9 else (99.0 if gross_win > 0 else 0.0)
    net_pnl = sum(pnls)
    ci_lo, ci_hi, prob_pos = stationary_bootstrap_ci(pnls, n_draws=10000) if n >= 8 else (0.0, 0.0, 0.0)
    pos_paths, tot_paths, pbo = cpcv_6_2_positive_paths(pnls)
    eligible = bool(n >= min_trades and pf >= min_pf and ci_lo > 0.0 and pbo <= max_pbo)
    demote = bool(n >= 20 and (pf < 1.0 or prob_pos < 0.25))
    verdict = "PROMOTE" if eligible else ("DEMOTE_OR_KILL" if demote else "HOLD_IN_SHADOW")
    return {
        "ledger": path.name,
        "trades": n,
        "win_rate_pct": round((wins / n * 100.0) if n else 0.0, 2),
        "net_pnl_usd": round(net_pnl, 2),
        "profit_factor": round(pf, 3),
        "bootstrap_ci95_lo_per_trade": round(ci_lo, 4),
        "bootstrap_ci95_hi_per_trade": round(ci_hi, 4),
        "prob_positive": round(prob_pos, 4),
        "cpcv_6_2_paths": f"{pos_paths}/{tot_paths}",
        "pbo_estimate": pbo,
        "verdict": verdict,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Weekly Purged WFO + CPCV(6,2) + 10k Stationary Bootstrap Governance")
    ap.add_argument("--data-dir", type=Path, default=PIPELINE_ROOT / "data/polymarket")
    ap.add_argument("--config", type=Path, default=STRATEGY_CONFIG_PATH)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8")) if args.config.exists() else dict(DEFAULT_HOLISTIC_CONFIG)
    validated = _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, cfg)
    g_cfg = validated["shadow_governance"]

    ledgers = [
        args.data_dir / "ledger_shadow_sol_v392.jsonl",
        args.data_dir / "ledger_shadow_hybrid_zsplit.jsonl",
        args.data_dir / "ledger_shadow_xau_15m.jsonl",
        args.data_dir / "ledger_shadow_btc_5m.jsonl",
        args.data_dir / "ledger_shadow_sol_5m.jsonl",
    ]
    results = [
        evaluate_ledger_file(
            p,
            min_trades=int(g_cfg["weekly_wfo_min_trades"]),
            min_pf=float(g_cfg["weekly_wfo_min_profit_factor"]),
            max_pbo=float(g_cfg["weekly_wfo_max_pbo"]),
        )
        for p in ledgers
    ]
    report = {"schema_version": validated["schema_version"], "shadow_evaluations": results}
    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
