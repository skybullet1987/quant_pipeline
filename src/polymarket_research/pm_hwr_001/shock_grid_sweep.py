#!/usr/bin/env python3
"""
PM-HWR-001: Stage 3 & 4 Shock Filter Parameter Grid Sweep
=========================================================
Sweeps conviction filters across all 4,902 shock triggers and evaluates:
  1. Candle Distance Buffer (|dist| >= 0.05% to 0.35%)
  2. TTE Window (60s <= TTE <= 300s, 600s, 900s, 1500s)
  3. OFI Intensity (|OFI| >= 0.50, 0.85, 1.00)
  4. Shock Volume Threshold ($500k, $1.0M, $2.0M)
  5. Price Bounds (Floor: 0.50 to 0.70, Ceiling: 0.85 to 0.94)
  6. Chronological Folds: Train (Sept 28 - Oct 5), Val (Oct 6 - Oct 9), Holdout (Oct 10 - Oct 12)
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path("data/polymarket")
OUTPUT_DIR = Path("data/pm_hwr_001")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SHOCK_FILE = DATA_DIR / "live_shock_triggers.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"


def polymarket_crypto_fee_v2(price: float, fee_rate: float = 0.07) -> float:
    """Polymarket crypto dynamic fee schedule: fee = fee_rate * p * (1 - p)."""
    p = max(0.001, min(0.999, price))
    return fee_rate * p * (1.0 - p)


def get_fold(candle_close_ts: float) -> str:
    dt = datetime.fromtimestamp(candle_close_ts, tz=timezone.utc)
    day_str = dt.strftime("%Y-%m-%d")
    if day_str <= "2026-10-05":
        return "TRAIN"
    elif day_str <= "2026-10-09":
        return "VALIDATION"
    else:
        return "HOLDOUT"


@dataclass
class ShockFilterConfig:
    candidate_id: str
    min_dist_pct: float
    max_tte: float
    min_tte: float
    min_ofi: float
    min_volume_usd: float
    min_price: float
    max_price: float
    max_spread: float = 0.030
    min_depth_ratio: float = 1.50
    one_trade_per_market: bool = True


def run_shock_sweep(configs: List[ShockFilterConfig], ticket_size_usd: float = 30.0) -> Dict[str, Any]:
    # Load resolutions
    resolutions = {}
    with open(RESOLUTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                resolutions[str(r["market_id"])] = r

    # Load shocks
    shocks = []
    with open(SHOCK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    s = json.loads(line)
                    mid = str(s.get("market_id"))
                    if mid in resolutions:
                        shocks.append((s, resolutions[mid]))
                except Exception:
                    pass

    print(f"Loaded {len(shocks)} resolution-matched shocks.")

    results = {}

    for cfg in configs:
        trades_by_fold = {"TRAIN": [], "VALIDATION": [], "HOLDOUT": []}
        seen_market = set()

        for s, res in shocks:
            mid = str(s.get("market_id"))
            if cfg.one_trade_per_market and mid in seen_market:
                continue

            # TTE
            tte = float(s.get("seconds_to_expiry", 9999.0))
            if not (cfg.min_tte <= tte <= cfg.max_tte):
                continue

            # Shock Volume & OFI
            vol = float(s.get("shock_volume_100ms", 0.0))
            if vol < cfg.min_volume_usd:
                continue

            ofi = float(s.get("shock_ofi", 0.0))
            if abs(ofi) < cfg.min_ofi:
                continue

            # Direction & Target Token
            shock_dir = s.get("shock_direction")
            target_token = "UP" if shock_dir == "BUY" else "DOWN"

            # Trend & Distance Congruence
            dist_pct = float(s.get("candle_distance_pct", 0.0))
            if abs(dist_pct) < cfg.min_dist_pct:
                continue
            if target_token == "UP" and dist_pct < cfg.min_dist_pct:
                continue
            if target_token == "DOWN" and dist_pct > -cfg.min_dist_pct:
                continue

            # Book depth & price
            tok_feats = s.get("pre_shock_features_t0", {}).get(target_token, {})
            raw_asks = tok_feats.get("raw_top_asks", [])
            if not raw_asks:
                continue

            # Executable depth
            exec_depth = sum(px * sz for px, sz in raw_asks if px <= cfg.max_price)
            if exec_depth / ticket_size_usd < cfg.min_depth_ratio:
                continue

            spread = float(tok_feats.get("spread", 0.01) or 0.01)
            if spread > cfg.max_spread:
                continue

            vwap_20 = float(tok_feats.get("vwap_$20") or tok_feats.get("best_ask", 0.0) or 0.0)
            if not (cfg.min_price <= vwap_20 <= cfg.max_price):
                continue

            # Winning outcome
            winning_outcome = res.get("winning_outcome")
            won = (target_token == winning_outcome)

            # Economics
            fee_per_share = polymarket_crypto_fee_v2(vwap_20)
            shares = ticket_size_usd / vwap_20
            fee_total = shares * fee_per_share

            gross_pnl = (shares * 1.0 - ticket_size_usd) if won else (-ticket_size_usd)
            net_pnl = gross_pnl - fee_total

            close_ts = float(res.get("candle_close_ts", 0.0))
            fold = get_fold(close_ts)

            trades_by_fold[fold].append({
                "market_id": mid,
                "won": won,
                "entry_price": vwap_20,
                "net_pnl": net_pnl,
                "fee_usd": fee_total,
                "tte": tte,
                "dist_pct": dist_pct,
            })
            seen_market.add(mid)

        # Summarize folds
        fold_stats = {}
        for f_name, f_trades in trades_by_fold.items():
            n = len(f_trades)
            if n == 0:
                fold_stats[f_name] = {
                    "n_trades": 0, "win_rate_pct": 0.0, "win_rate_95ci": [0.0, 0.0],
                    "total_net_pnl": 0.0, "ev_per_trade": 0.0, "avg_win": 0.0, "avg_loss": 0.0, "profit_factor": 0.0
                }
                continue

            wins = [t for t in f_trades if t["won"]]
            losses = [t for t in f_trades if not t["won"]]
            wr = len(wins) / n

            z = 1.96
            denom = 1 + (z**2) / n
            center = (wr + (z**2) / (2 * n)) / denom
            margin = (z * math.sqrt((wr * (1 - wr) / n) + ((z**2) / (4 * (n**2))))) / denom
            ci_lower = max(0.0, center - margin)
            ci_upper = min(1.0, center + margin)

            pnls = [t["net_pnl"] for t in f_trades]
            tot_pnl = sum(pnls)
            ev = tot_pnl / n

            win_pnls = [t["net_pnl"] for t in wins]
            loss_pnls = [t["net_pnl"] for t in losses]
            avg_w = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
            avg_l = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0.0
            pf = abs(sum(win_pnls) / sum(loss_pnls)) if loss_pnls and sum(loss_pnls) != 0 else float("inf")

            fold_stats[f_name] = {
                "n_trades": n,
                "wins": len(wins),
                "losses": len(losses),
                "win_rate_pct": round(wr * 100, 2),
                "win_rate_95ci": [round(ci_lower * 100, 2), round(ci_upper * 100, 2)],
                "total_net_pnl": round(tot_pnl, 2),
                "ev_per_trade": round(ev, 2),
                "avg_win": round(avg_w, 2),
                "avg_loss": round(avg_l, 2),
                "profit_factor": round(pf, 2) if pf != float("inf") else "inf",
            }

        results[cfg.candidate_id] = {
            "config": asdict(cfg),
            "folds": fold_stats,
            "total_qualifying_trades": sum(len(tr) for tr in trades_by_fold.values()),
        }

    return results


def generate_shock_grid() -> List[ShockFilterConfig]:
    grid = []

    # 1. Baseline EXP-302 Control
    grid.append(ShockFilterConfig(
        candidate_id="CONTROL_EXP302_BASELINE",
        min_dist_pct=0.05,
        max_tte=900.0,
        min_tte=60.0,
        min_ofi=0.0,
        min_volume_usd=500_000.0,
        min_price=0.15,
        max_price=0.88,
    ))

    # 2. Strict Distance Buffer Sweep (|dist| >= 0.10%, 0.15%, 0.20%, 0.25%, 0.30%)
    dist_tests = [
        ("CAND_B1_DIST_0.10", 0.10, 900.0, 60.0, 0.50, 1_000_000.0, 0.40, 0.88),
        ("CAND_B2_DIST_0.15", 0.15, 900.0, 60.0, 0.50, 1_000_000.0, 0.40, 0.88),
        ("CAND_B3_DIST_0.20", 0.20, 900.0, 60.0, 0.70, 1_000_000.0, 0.40, 0.88),
        ("CAND_B4_DIST_0.25", 0.25, 900.0, 60.0, 0.85, 1_000_000.0, 0.40, 0.88),
        ("CAND_B5_DIST_0.30", 0.30, 900.0, 60.0, 0.85, 1_000_000.0, 0.40, 0.90),
    ]
    for cid, dist, max_t, min_t, ofi, vol, min_p, max_p in dist_tests:
        grid.append(ShockFilterConfig(
            candidate_id=cid, min_dist_pct=dist, max_tte=max_t, min_tte=min_t,
            min_ofi=ofi, min_volume_usd=vol, min_price=min_p, max_price=max_p
        ))

    # 3. TTE Compression Sweeps (Last 300s, 600s)
    grid.append(ShockFilterConfig(
        candidate_id="CAND_B6_TTE_300S_DIST_0.15",
        min_dist_pct=0.15,
        max_tte=300.0,
        min_tte=60.0,
        min_ofi=0.70,
        min_volume_usd=1_000_000.0,
        min_price=0.50,
        max_price=0.92,
    ))
    grid.append(ShockFilterConfig(
        candidate_id="CAND_B7_TTE_300S_DIST_0.25",
        min_dist_pct=0.25,
        max_tte=300.0,
        min_tte=60.0,
        min_ofi=0.85,
        min_volume_usd=1_000_000.0,
        min_price=0.50,
        max_price=0.94,
    ))
    grid.append(ShockFilterConfig(
        candidate_id="CAND_B8_TTE_600S_DIST_0.20",
        min_dist_pct=0.20,
        max_tte=600.0,
        min_tte=60.0,
        min_ofi=0.80,
        min_volume_usd=1_000_000.0,
        min_price=0.50,
        max_price=0.90,
    ))

    # 4. Ultra-Conviction (Targeting 95%+)
    grid.append(ShockFilterConfig(
        candidate_id="CAND_B9_ULTRA_DIST_0.35_OFI_1.0",
        min_dist_pct=0.35,
        max_tte=600.0,
        min_tte=60.0,
        min_ofi=1.00,
        min_volume_usd=1_500_000.0,
        min_price=0.50,
        max_price=0.94,
    ))

    return grid


def main():
    print("=" * 80)
    print("   PM-HWR-001: SHOCK FILTER RE-CALIBRATION & PARAMETER SWEEP")
    print("=" * 80)

    grid = generate_shock_grid()
    print(f"Testing {len(grid)} candidate configurations against historical shocks.")

    results = run_shock_sweep(grid, ticket_size_usd=30.0)

    out_file = OUTPUT_DIR / "stage3_4_shock_sweep_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"✓ Sweep complete. Results written to: {out_file}\n")

    print(f"{'Candidate ID':<29} | {'Train WR (N)':<16} | {'Val WR (N)':<16} | {'Holdout WR':<12} | {'Holdout 95% CI':<16} | {'Holdout N':<10} | {'Holdout EV':<10}")
    print("-" * 115)
    for cid, res in results.items():
        folds = res["folds"]
        tr_wr = f"{folds['TRAIN']['win_rate_pct']}% ({folds['TRAIN']['n_trades']})" if folds['TRAIN']['n_trades'] > 0 else "0"
        val_wr = f"{folds['VALIDATION']['win_rate_pct']}% ({folds['VALIDATION']['n_trades']})" if folds['VALIDATION']['n_trades'] > 0 else "0"
        ho = folds['HOLDOUT']
        ho_wr = f"{ho['win_rate_pct']}%" if ho['n_trades'] > 0 else "0"
        ho_ci = f"[{ho['win_rate_95ci'][0]}%, {ho['win_rate_95ci'][1]}%]" if ho['n_trades'] > 0 else "N/A"
        ho_n = f"{ho['n_trades']}"
        ho_ev = f"${ho['ev_per_trade']}" if ho['n_trades'] > 0 else "N/A"
        print(f"{cid:<29} | {tr_wr:<16} | {val_wr:<16} | {ho_wr:<12} | {ho_ci:<16} | {ho_n:<10} | {ho_ev:<10}")


if __name__ == "__main__":
    main()
