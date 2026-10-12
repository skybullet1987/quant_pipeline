#!/usr/bin/env python3
"""
EXP-308: Orderbook Queue Persistence & Microstructure Latency Profiler
======================================================================
Implements Phase 2 of the Empirical Strategy Validation Framework.
Measures the empirical survival time (half-life) of resting CLOB liquidity
following an identified pricing dislocation.

Specific Gate Criteria (Phase 2):
  - Tracks quote survival across intervals: [50ms, 85ms, 150ms, 300ms, 500ms, 1000ms].
  - Evaluates whether resting liquidity vanishes before 85ms (Finland VM RTT to AWS us-east-1).
  - Gate 2 Rule: If > 25% of opportunities evaporate in under 85ms across >= 100 events,
    halt live direct execution and redirect toward a co-located AWS US-East proxy relay.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data" / "exp308"
DATA_DIR.mkdir(parents=True, exist_ok=True)

EVENTS_FILE = DATA_DIR / "persistence_events.jsonl"
METRICS_FILE = DATA_DIR / "persistence_metrics.json"
PID_FILE = DATA_DIR / "exp308_profiler.pid"
LOG_FILE = DATA_DIR / "exp308_profiler.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [EXP308] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("EXP308Profiler")

CLOB_API_URL = "https://clob.polymarket.com"
OBSERVATION_DELAYS = [0.050, 0.085, 0.150, 0.300, 0.500, 1.000]


@dataclass
class PersistenceEvent:
    event_id: str
    token_id: str
    t0_timestamp: float
    initial_best_ask: float
    initial_depth: float
    persistence_matrix: Dict[str, bool]  # e.g., {"50ms": True, "85ms": True, ...}
    evaporated_under_85ms: bool
    final_survival_seconds: float
    observation_log: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    has_network_timeout: bool = False
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class QueuePersistenceProfiler:
    """Measures high-resolution quote persistence following edge identification."""

    def __init__(self):
        self.running = False
        self.events: List[PersistenceEvent] = []
        self.stats = {
            "total_events": 0,
            "evaporated_under_85ms_count": 0,
            "evaporated_under_85ms_pct": 0.0,
            "survived_over_150ms_pct": 0.0,
            "survived_over_500ms_pct": 0.0,
            "gate_status": "PENDING_EVENTS",  # "PASS_CANARY_APPROVED" or "FAIL_US_EAST_REQUIRED"
        }
        self._load_existing_events()

    def _load_existing_events(self) -> None:
        if EVENTS_FILE.exists():
            with open(EVENTS_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            d = json.loads(line)
                            ev = PersistenceEvent(
                                event_id=d["event_id"],
                                token_id=d["token_id"],
                                t0_timestamp=d["t0_timestamp"],
                                initial_best_ask=d["initial_best_ask"],
                                initial_depth=d["initial_depth"],
                                persistence_matrix=d["persistence_matrix"],
                                evaporated_under_85ms=d["evaporated_under_85ms"],
                                final_survival_seconds=d["final_survival_seconds"],
                                observation_log=d.get("observation_log", {}),
                                has_network_timeout=d.get("has_network_timeout", False),
                                timestamp_utc=d.get("timestamp_utc", ""),
                            )
                            self.events.append(ev)
                        except Exception:
                            pass
            self._recalculate_metrics()

    def _recalculate_metrics(self) -> None:
        n = len(self.events)
        self.stats["total_events"] = n
        if n == 0:
            return

        under_85 = sum(1 for e in self.events if e.evaporated_under_85ms)
        over_150 = sum(1 for e in self.events if e.persistence_matrix.get("150ms", False))
        over_500 = sum(1 for e in self.events if e.persistence_matrix.get("500ms", False))

        self.stats["evaporated_under_85ms_count"] = under_85
        self.stats["evaporated_under_85ms_pct"] = round((under_85 / n) * 100.0, 2)
        self.stats["survived_over_150ms_pct"] = round((over_150 / n) * 100.0, 2)
        self.stats["survived_over_500ms_pct"] = round((over_500 / n) * 100.0, 2)

        if n >= 100:
            if self.stats["evaporated_under_85ms_pct"] > 25.0:
                self.stats["gate_status"] = "FAIL_US_EAST_REQUIRED"
            else:
                self.stats["gate_status"] = "PASS_CANARY_APPROVED"
        else:
            self.stats["gate_status"] = f"PENDING_EVENTS ({n}/100)"

        with open(METRICS_FILE, "w") as f:
            json.dump(self.stats, f, indent=2)

    async def profile_opportunity(
        self,
        token_id: str,
        initial_ask: float,
        initial_depth: float,
        event_id: Optional[str] = None,
        t0: Optional[float] = None,
    ) -> PersistenceEvent:
        """Tracks the persistence decay of a resting quote across defined latency checkpoints."""
        t0 = t0 or time.time()
        event_id = event_id or f"PERSIST_{int(t0 * 1000)}_{token_id[:8]}"
        matrix: Dict[str, bool] = {}
        obs_log: Dict[str, Dict[str, Any]] = {}
        last_survived = 0.0
        network_timeout = False

        headers = {"User-Agent": "EXP308Profiler/1.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            for delay in OBSERVATION_DELAYS:
                now = time.time()
                elapsed = now - t0
                target_sleep = delay - elapsed
                if target_sleep > 0:
                    await asyncio.sleep(target_sleep)

                # Sample book state with measured round-trip time and status categorization
                t_req_start = time.time()
                try:
                    async with session.get(f"{CLOB_API_URL}/book", params={"token_id": token_id}, timeout=0.35) as resp:
                        rtt_ms = (time.time() - t_req_start) * 1000.0
                        actual_elapsed_ms = (time.time() - t0) * 1000.0
                        if resp.status == 200:
                            book = await resp.json()
                            asks = book.get("asks", [])
                            # Check if initial ask (or better) is still available with depth
                            still_present = any(
                                float(a["price"]) <= (initial_ask + 0.001) and float(a["size"]) >= (initial_depth * 0.5)
                                for a in asks
                            )
                            matrix[f"{int(delay * 1000)}ms"] = still_present
                            obs_log[f"{int(delay * 1000)}ms"] = {
                                "status": "CONFIRMED_PRESENT" if still_present else "CONFIRMED_EVAPORATED",
                                "quote_present": still_present,
                                "target_delay_ms": delay * 1000.0,
                                "actual_elapsed_ms": round(actual_elapsed_ms, 2),
                                "rtt_ms": round(rtt_ms, 2),
                                "http_code": 200,
                            }
                            if still_present:
                                last_survived = delay
                        else:
                            matrix[f"{int(delay * 1000)}ms"] = False
                            obs_log[f"{int(delay * 1000)}ms"] = {
                                "status": "HTTP_ERROR",
                                "quote_present": None,
                                "target_delay_ms": delay * 1000.0,
                                "actual_elapsed_ms": round(actual_elapsed_ms, 2),
                                "rtt_ms": round(rtt_ms, 2),
                                "http_code": resp.status,
                            }
                            network_timeout = True
                except asyncio.TimeoutError:
                    rtt_ms = (time.time() - t_req_start) * 1000.0
                    actual_elapsed_ms = (time.time() - t0) * 1000.0
                    matrix[f"{int(delay * 1000)}ms"] = False
                    obs_log[f"{int(delay * 1000)}ms"] = {
                        "status": "REQUEST_TIMEOUT",
                        "quote_present": None,
                        "target_delay_ms": delay * 1000.0,
                        "actual_elapsed_ms": round(actual_elapsed_ms, 2),
                        "rtt_ms": round(rtt_ms, 2),
                        "http_code": None,
                    }
                    network_timeout = True
                except Exception as e:
                    rtt_ms = (time.time() - t_req_start) * 1000.0
                    actual_elapsed_ms = (time.time() - t0) * 1000.0
                    matrix[f"{int(delay * 1000)}ms"] = False
                    obs_log[f"{int(delay * 1000)}ms"] = {
                        "status": f"ERROR_{type(e).__name__}",
                        "quote_present": None,
                        "target_delay_ms": delay * 1000.0,
                        "actual_elapsed_ms": round(actual_elapsed_ms, 2),
                        "rtt_ms": round(rtt_ms, 2),
                        "http_code": None,
                    }
                    network_timeout = True

        # Evaporated under 85ms requires confirmed disappearance, not network timeout
        check_85 = obs_log.get("85ms", {})
        evaporated_under_85 = (check_85.get("status") == "CONFIRMED_EVAPORATED")

        event = PersistenceEvent(
            event_id=event_id,
            token_id=token_id,
            t0_timestamp=t0,
            initial_best_ask=initial_ask,
            initial_depth=initial_depth,
            persistence_matrix=matrix,
            evaporated_under_85ms=evaporated_under_85,
            final_survival_seconds=last_survived,
            observation_log=obs_log,
            has_network_timeout=network_timeout,
        )

        self.events.append(event)
        with open(EVENTS_FILE, "a") as f:
            f.write(json.dumps(asdict(event)) + "\n")

        self._recalculate_metrics()
        logger.info(
            f"[PERSISTENCE-AUDIT] {event_id} | Evaporated <85ms: {evaporated_under_85} | "
            f"Survival: {last_survived * 1000:.0f}ms | Gate: {self.stats['gate_status']}"
        )
        return event

    async def profile_opportunity_async(
        self,
        event_id: Optional[str] = None,
        token_id: str = "",
        initial_ask: float = 0.0,
        initial_depth: float = 0.0,
        t0: Optional[float] = None,
    ) -> PersistenceEvent:
        """Asynchronous wrapper for daemon compatibility."""
        return await self.profile_opportunity(
            token_id=token_id,
            initial_ask=initial_ask,
            initial_depth=initial_depth,
            event_id=event_id,
            t0=t0,
        )


async def run_profiler_daemon():
    profiler = QueuePersistenceProfiler()
    trigger_file = PROJECT_ROOT / "data/polymarket/live_shock_triggers.jsonl"
    logger.info(f"Starting EXP-308 Profiler Daemon. Tailing {trigger_file}...")
    seen_events = set()
    last_pos = trigger_file.stat().st_size if trigger_file.exists() else 0

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    while True:
        try:
            if trigger_file.exists():
                cur_size = trigger_file.stat().st_size
                if cur_size > last_pos:
                    with open(trigger_file, "r") as f:
                        f.seek(last_pos)
                        lines = f.readlines()
                        last_pos = f.tell()

                    for line in lines:
                        if not line.strip():
                            continue
                        try:
                            shock = json.loads(line)
                            eid = shock.get("event_id") or shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
                            if eid in seen_events:
                                continue
                            seen_events.add(eid)

                            target = "UP" if shock.get("shock_direction") == "BUY" else "DOWN"
                            features = shock.get("pre_shock_features_t0", {}).get(target, {})
                            raw_asks = features.get("raw_top_asks", [])
                            token_id = features.get("token_id")
                            if raw_asks and token_id:
                                ask_px = float(raw_asks[0][0])
                                ask_sz = float(raw_asks[0][1])
                                asyncio.create_task(
                                    profiler.profile_opportunity_async(
                                        event_id=eid,
                                        token_id=token_id,
                                        initial_ask=ask_px,
                                        initial_depth=ask_sz,
                                        t0=time.time(),
                                    )
                                )
                        except Exception as e:
                            logger.error(f"Error parsing shock in profiler: {e}")

            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in profiler loop: {e}")
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EXP-308 Queue Persistence Profiler")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon mode")
    args = parser.parse_args()

    if args.daemon:
        asyncio.run(run_profiler_daemon())
    else:
        profiler = QueuePersistenceProfiler()
        print("=" * 80)
        print("   EXP-308 QUEUE PERSISTENCE & LATENCY PROFILER INITIALIZED")
        print(f"   Metrics: {METRICS_FILE}")
        print(f"   Events:  {EVENTS_FILE}")
        print("   Current State:", json.dumps(profiler.stats, indent=2))
        print("=" * 80)

