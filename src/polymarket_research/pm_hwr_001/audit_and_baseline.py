#!/usr/bin/env python3
"""
PM-HWR-001: Stage 1 (Data & Pipeline Audit) and Stage 2 (Freeze Baseline)
=======================================================================
Audit the recorded datasets, calculate exact integrity metrics, and
freeze the baseline performance across all historical trading ledgers.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data/polymarket")
OUTPUT_DIR = Path("data/pm_hwr_001")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def audit_datasets() -> Dict[str, Any]:
    files_to_audit = [
        "finalized_market_resolutions.jsonl",
        "polymarket_hourly_telemetry.jsonl",
        "polymarket_hourly_telemetry_eth.jsonl",
        "live_shock_triggers.jsonl",
        "paper_trading_validation_ledger.jsonl",
        "shadow_fast_unwind_ledger.jsonl",
        "live_harvester_state.json",
    ]

    audit_records = {}
    for fname in files_to_audit:
        fpath = DATA_DIR / fname
        if not fpath.exists():
            audit_records[fname] = {"exists": False}
            continue

        size_bytes = fpath.stat().st_size
        sha = sha256_file(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            if fname.endswith(".jsonl"):
                line_count = sum(1 for line in f if line.strip())
            else:
                line_count = 1  # json file

        audit_records[fname] = {
            "exists": True,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "line_count": line_count,
            "sha256": sha,
        }

    # Resolution Market Audit
    res_path = DATA_DIR / "finalized_market_resolutions.jsonl"
    resolutions = []
    with open(res_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                resolutions.append(json.loads(line))

    asset_counts = Counter()
    dates_counter = Counter()
    outcome_counts = Counter()
    market_ids = set()

    for r in resolutions:
        mid = str(r["market_id"])
        market_ids.add(mid)
        title = r.get("title", "")
        asset = "BTC" if "Bitcoin" in title else "ETH" if "Ethereum" in title else "UNKNOWN"
        asset_counts[asset] += 1
        outcome_counts[r.get("winning_outcome", "UNKNOWN")] += 1
        
        # Datetime
        ts = r.get("candle_close_ts")
        if ts:
            dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            dates_counter[dt_str] += 1

    return {
        "files": audit_records,
        "market_universe": {
            "total_finalized_markets": len(resolutions),
            "unique_market_ids": len(market_ids),
            "asset_distribution": dict(asset_counts),
            "outcome_distribution": dict(outcome_counts),
            "date_range": {
                "start": min(dates_counter.keys()) if dates_counter else None,
                "end": max(dates_counter.keys()) if dates_counter else None,
                "distinct_calendar_days": len(dates_counter),
                "daily_market_counts": dict(sorted(dates_counter.items())),
            },
            "ground_truth_contract_duration_seconds": 3600.0,
            "independent_event_clusters": len(market_ids),
        },
    }


def compute_ledger_metrics(trades: List[Dict[str, Any]], pnl_key: str = "net_pnl_usd") -> Dict[str, Any]:
    if not trades:
        return {"error": "NO_TRADES"}

    n = len(trades)
    wins = [t for t in trades if t.get(pnl_key, 0.0) > 0]
    losses = [t for t in trades if t.get(pnl_key, 0.0) < 0]
    scratches = [t for t in trades if t.get(pnl_key, 0.0) == 0]

    # Settlement accuracy (contract was correct outcome)
    settled_wins = [t for t in trades if t.get("won") is True]
    settlement_accuracy = len(settled_wins) / n if n > 0 else 0.0

    net_profitable_rate = len(wins) / n if n > 0 else 0.0

    pnls = [float(t.get(pnl_key, 0.0)) for t in trades]
    total_net_pnl = sum(pnls)
    win_pnls = [float(t.get(pnl_key, 0.0)) for t in wins]
    loss_pnls = [float(t.get(pnl_key, 0.0)) for t in losses]

    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0.0
    profit_factor = abs(sum(win_pnls) / sum(loss_pnls)) if loss_pnls and sum(loss_pnls) != 0 else float("inf")

    # Drawdown calculation
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cum += p
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    worst_loss = min(pnls) if pnls else 0.0

    # Total fees paid
    total_fees = sum(float(t.get("taker_fee_usd", 0.0) or t.get("fee_usd", 0.0) or t.get("entry_fee_usd", 0.0) or 0.0) for t in trades)

    # 95% Wilson Score Interval for settlement accuracy
    p = settlement_accuracy
    z = 1.96
    denom = 1 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) / n) + ((z**2) / (4 * (n**2))))) / denom
    ci_lower = max(0.0, center - margin)
    ci_upper = min(1.0, center + margin)

    return {
        "n_trades": n,
        "settled_wins": len(settled_wins),
        "settlement_accuracy_pct": round(settlement_accuracy * 100, 2),
        "settlement_accuracy_95ci": [round(ci_lower * 100, 2), round(ci_upper * 100, 2)],
        "net_profitable_count": len(wins),
        "net_loss_count": len(losses),
        "net_profitable_rate_pct": round(net_profitable_rate * 100, 2),
        "total_net_pnl_usd": round(total_net_pnl, 2),
        "avg_win_usd": round(avg_win, 2),
        "avg_loss_usd": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "inf",
        "max_drawdown_usd": round(max_dd, 2),
        "worst_single_loss_usd": round(worst_loss, 2),
        "total_fees_usd": round(total_fees, 2),
    }


def freeze_baseline() -> Dict[str, Any]:
    # 1. EXP-302 Paper Trading Validation Ledger
    exp302_path = DATA_DIR / "paper_trading_validation_ledger.jsonl"
    exp302_trades = []
    if exp302_path.exists():
        with open(exp302_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    exp302_trades.append(json.loads(line))

    exp302_metrics = compute_ledger_metrics(exp302_trades, "net_pnl_usd")

    # 2. EXP-303 Policy B2 (Maker-First Scalp)
    exp303_path = DATA_DIR / "shadow_fast_unwind_ledger.jsonl"
    exp303_trades = []
    if exp303_path.exists():
        with open(exp303_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    raw = json.loads(line)
                    b2 = raw.get("policy_b2", {})
                    exp303_trades.append({
                        "trade_id": raw.get("trade_id"),
                        "won": b2.get("net_pnl_usd", 0.0) > 0,
                        "net_pnl_usd": b2.get("net_pnl_usd", 0.0),
                        "entry_fee_usd": b2.get("entry_fee_usd", 0.0),
                    })

    exp303_metrics = compute_ledger_metrics(exp303_trades, "net_pnl_usd")

    # 3. Live Real-Money Harvester
    live_path = DATA_DIR / "live_harvester_state.json"
    live_trades = []
    if live_path.exists():
        with open(live_path, "r", encoding="utf-8") as f:
            st = json.load(f)
            live_trades = st.get("closed_positions", [])

    live_metrics = compute_ledger_metrics(live_trades, "net_pnl_usd")

    return {
        "exp302_paper_validation": exp302_metrics,
        "exp303_policy_b2_shadow": exp303_metrics,
        "live_production_harvester": live_metrics,
    }


def main():
    print("=" * 80)
    print("   PM-HWR-001: STAGE 1 (DATA AUDIT) & STAGE 2 (BASELINE FREEZE)")
    print("=" * 80)

    audit_res = audit_datasets()
    baseline_res = freeze_baseline()

    report = {
        "campaign_id": "PM-HWR-001",
        "stage": "STAGE_1_AND_2_AUDIT_AND_BASELINE",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "audit": audit_res,
        "baseline": baseline_res,
    }

    out_file = OUTPUT_DIR / "stage1_2_audit_baseline_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"✓ Saved Stage 1 & 2 Audit Report to: {out_file}")
    print("\nData Universe Summary:")
    print(f"  - Total Finalized Markets: {audit_res['market_universe']['total_finalized_markets']}")
    print(f"  - Unique Market IDs: {audit_res['market_universe']['unique_market_ids']}")
    print(f"  - Asset Distribution: {audit_res['market_universe']['asset_distribution']}")
    print(f"  - Date Range: {audit_res['market_universe']['date_range']['start']} to {audit_res['market_universe']['date_range']['end']} ({audit_res['market_universe']['date_range']['distinct_calendar_days']} days)")
    print("\nBaseline Ledgers Summary:")
    print("  [EXP-302 Paper Trading (Hold to Expiry)]:")
    print(f"    • Trades: {baseline_res['exp302_paper_validation']['n_trades']}")
    print(f"    • Settlement Accuracy: {baseline_res['exp302_paper_validation']['settlement_accuracy_pct']}% (95% CI: {baseline_res['exp302_paper_validation']['settlement_accuracy_95ci']})")
    print(f"    • Net PnL: ${baseline_res['exp302_paper_validation']['total_net_pnl_usd']}")
    print(f"    • Profit Factor: {baseline_res['exp302_paper_validation']['profit_factor']}")
    print(f"    • Max Drawdown: ${baseline_res['exp302_paper_validation']['max_drawdown_usd']}")
    print("  [EXP-303 Policy B2 (Maker-First Scalp)]:")
    print(f"    • Trades: {baseline_res['exp303_policy_b2_shadow']['n_trades']}")
    print(f"    • Win Rate: {baseline_res['exp303_policy_b2_shadow']['net_profitable_rate_pct']}%")
    print(f"    • Net PnL: ${baseline_res['exp303_policy_b2_shadow']['total_net_pnl_usd']}")
    print("  [Live Production Harvester (Real Money)]:")
    print(f"    • Trades: {baseline_res['live_production_harvester']['n_trades']}")
    print(f"    • Settlement Accuracy: {baseline_res['live_production_harvester']['settlement_accuracy_pct']}%")
    print(f"    • Net Profitable Rate: {baseline_res['live_production_harvester']['net_profitable_rate_pct']}%")
    print(f"    • Net PnL: ${baseline_res['live_production_harvester']['total_net_pnl_usd']}")
    print(f"    • Avg Win: +${baseline_res['live_production_harvester']['avg_win_usd']}, Avg Loss: ${baseline_res['live_production_harvester']['avg_loss_usd']}")


if __name__ == "__main__":
    main()
