#!/usr/bin/env python3
"""
EXP-306: Historical Replay Backtester & Empirical Alpha Evaluator
================================================================
Replays the BoundaryConvergenceEngine across historical telemetry frames
and validates signal profitability against ground-truth finalized market resolutions.

Data Sources:
  - Telemetry: data/polymarket/polymarket_hourly_telemetry.jsonl (Granular L2 books & Binance spot)
  - Ground Truth: data/polymarket/finalized_market_resolutions.jsonl (On-chain settled outcomes)
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data" / "exp306"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TELEMETRY_FILE = PROJECT_ROOT / "data/polymarket/polymarket_hourly_telemetry.jsonl"
RESOLUTIONS_FILE = PROJECT_ROOT / "data/polymarket/finalized_market_resolutions.jsonl"
OUTPUT_REPORT = DATA_DIR / "historical_backtest_report.json"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [EXP306-BACKTEST] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("EXP306Backtest")

from src.polymarket_research.exp306_expiry_boundary_engine import BoundaryConvergenceEngine


@dataclass
class BacktestTrade:
    market_id: str
    timestamp: str
    seconds_to_expiry: float
    side: str
    entry_price: float
    available_shares: float
    ticket_usd: float
    shares_bought: float
    fee_usd: float
    settled_winning_outcome: str
    won: bool
    gross_pnl_usd: float
    net_pnl_usd: float


def run_historical_backtest(ticket_size_usd: float = 10.0) -> Dict[str, Any]:
    logger.info("=" * 80)
    logger.info("   EXP-306 DETERMINISTIC BOUNDARY HISTORICAL REPLAY BACKTEST")
    logger.info("=" * 80)

    if not RESOLUTIONS_FILE.exists() or not TELEMETRY_FILE.exists():
        logger.error("Required data files not found for historical replay.")
        return {"status": "DATA_MISSING"}

    # 1. Load ground-truth resolutions
    resolutions: Dict[str, Dict[str, Any]] = {}
    with open(RESOLUTIONS_FILE, "r") as f:
        for line in f:
            if line.strip():
                try:
                    r = json.loads(line)
                    resolutions[str(r.get("market_id"))] = r
                except Exception:
                    pass
    logger.info(f"Loaded {len(resolutions)} ground-truth market resolutions.")

    # 2. Replay telemetry frames
    trades: List[BacktestTrade] = []
    seen_markets = set()
    engines_by_market: Dict[str, BoundaryConvergenceEngine] = {}
    frames_scanned = 0

    with open(TELEMETRY_FILE, "r") as f:
        for line in f:
            if not line.strip():
                continue
            frames_scanned += 1
            try:
                frame = json.loads(line)
                mid = str(frame.get("market_id"))
                if mid not in resolutions or mid in seen_markets:
                    continue

                tte = float(frame.get("seconds_to_expiry", 9999.0))
                spot = float(frame.get("binance_spot", 0.0))
                open_px = float(frame.get("binance_1h_open", 0.0))
                ts_unix = float(frame.get("timestamp_unix", 0.0))
                if spot <= 0 or open_px <= 0:
                    continue

                if mid not in engines_by_market:
                    engines_by_market[mid] = BoundaryConvergenceEngine(
                        strike_price=open_px,
                        expiry_timestamp=ts_unix + tte,
                        resolution_type="DISCRETE_CLOSE",
                        discrete_jump_threshold=3.5,
                    )
                engine = engines_by_market[mid]
                engine.record_composite_tick(spot, ts_unix)

                # Evaluate in terminal boundary window (10s to 600s before expiry)
                if not (10.0 <= tte <= 600.0):
                    continue

                res = resolutions[mid]
                winning_side = res.get("winning_outcome")  # "UP" or "DOWN"

                book_up = frame.get("UP", {})
                book_down = frame.get("DOWN", {})

                best_ask_up = float(book_up.get("best_ask", 0.0))
                depth_up = float(book_up.get("ask_size_l1") or book_up.get("ask_size") or 0.0)

                best_ask_down = float(book_down.get("best_ask", 0.0))
                depth_down = float(book_down.get("ask_size_l1") or book_down.get("ask_size") or 0.0)

                # Evaluate UP
                entry_up = engine.evaluate_execution_entry(
                    "UP", best_ask_up, depth_up, frame.get("timestamp_unix", 0.0)
                ) if best_ask_up > 0 else None

                # Evaluate DOWN
                entry_down = engine.evaluate_execution_entry(
                    "DOWN", best_ask_down, depth_down, frame.get("timestamp_unix", 0.0)
                ) if best_ask_down > 0 else None

                chosen_entry = entry_up or entry_down
                if chosen_entry and chosen_entry.get("shares", 0.0) > 5.0:
                    side = chosen_entry["side"]
                    ask_px = chosen_entry["price"]
                    fee = chosen_entry["fee"]

                    shares = ticket_size_usd / ask_px
                    won = (side == winning_side)
                    gross_pnl = (shares * 1.0 - ticket_size_usd) if won else (-ticket_size_usd)
                    fee_total = shares * fee
                    net_pnl = gross_pnl - fee_total

                    trades.append(BacktestTrade(
                        market_id=mid,
                        timestamp=frame.get("timestamp", ""),
                        seconds_to_expiry=tte,
                        side=side,
                        entry_price=ask_px,
                        available_shares=chosen_entry["shares"],
                        ticket_usd=ticket_size_usd,
                        shares_bought=round(shares, 4),
                        fee_usd=round(fee_total, 4),
                        settled_winning_outcome=winning_side,
                        won=won,
                        gross_pnl_usd=round(gross_pnl, 4),
                        net_pnl_usd=round(net_pnl, 4),
                    ))
                    seen_markets.add(mid)

            except Exception as e:
                continue

    # 3. Statistical Analysis
    total_trades = len(trades)
    wins = sum(1 for t in trades if t.won)
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0

    total_net_pnl = sum(t.net_pnl_usd for t in trades)
    total_fees = sum(t.fee_usd for t in trades)
    gross_pnl = sum(t.gross_pnl_usd for t in trades)

    pnls = [t.net_pnl_usd for t in trades]
    avg_pnl = (sum(pnls) / len(pnls)) if pnls else 0.0
    variance = sum((p - avg_pnl) ** 2 for p in pnls) / len(pnls) if len(pnls) > 1 else 0.0
    sharpe = (avg_pnl / math.sqrt(variance)) * math.sqrt(365 * 24) if variance > 0 else 0.0

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "frames_scanned": frames_scanned,
        "markets_evaluated": len(seen_markets),
        "ticket_size_usd": ticket_size_usd,
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(win_rate, 2),
        "gross_pnl_usd": round(gross_pnl, 2),
        "total_fees_usd": round(total_fees, 2),
        "net_pnl_usd": round(total_net_pnl, 2),
        "annualized_sharpe": round(sharpe, 2),
        "sample_trades": [asdict(t) for t in trades[:10]],
    }

    with open(OUTPUT_REPORT, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Backtest Completed across {total_trades} trades.")
    logger.info(f"Win Rate: {win_rate:.2f}% | Net PnL: ${total_net_pnl:.2f} | Sharpe: {sharpe:.2f}")
    return report


if __name__ == "__main__":
    rep = run_historical_backtest(ticket_size_usd=10.0)
    print("=" * 80)
    print("      EXP-306 HISTORICAL BACKTEST PERFORMANCE SUMMARY")
    print("=" * 80)
    print(f"Total Trades:     {rep.get('total_trades')}")
    print(f"Win Rate:         {rep.get('win_rate_pct')}% ({rep.get('wins')}W / {rep.get('losses')}L)")
    print(f"Gross PnL:        ${rep.get('gross_pnl_usd'):.2f}")
    print(f"Total Fees:       ${rep.get('total_fees_usd'):.2f}")
    print(f"Net PnL:          ${rep.get('net_pnl_usd'):.2f}")
    print(f"Annualized Sharpe:{rep.get('annualized_sharpe')}")
    print("=" * 80)
