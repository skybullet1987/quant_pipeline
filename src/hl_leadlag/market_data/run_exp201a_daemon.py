"""
EXP-201A Spillover Live Telemetry Daemon (v3.2.1 A0.1)
File: src/hl_leadlag/market_data/run_exp201a_daemon.py

Runs the live asynchronous telemetry listener on the Tokyo GCP node:
  1. Subscribes to Binance USD-M liquidation stream: wss://fstream.binance.com/ws/!forceOrder@arr
  2. Subscribes to Hyperliquid L2 Book streams: SOL, BTC, ETH
  3. Records decomposed wire timestamps (T_Binance, E_Binance, t_recv, delta_transport)
  4. Selects pre-treatment counterfactual matched controls C_i in R(t_i^-)
  5. Measures markout returns across [5s, 10s, 20s, 30s, 45s, 60s]
  6. Evaluates primary endpoint: 30s net strategy return (Gate A hurdle > 2.5 bps net)
  7. Outputs real-time records to data/exp201/exp201a_spillover_telemetry.jsonl
"""

import os
import sys
import json
import time
import signal
import asyncio
import logging
from pathlib import Path
import websockets

PIPELINE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PIPELINE_ROOT))

from src.hl_leadlag.market_data.exp201a_spillover_telemetry import (
    EXP201ASpilloverEngine,
    BINANCE_WS_URL,
    HYPERLIQUID_WS_URL,
    PRIMARY_ENDPOINT_SEC,
    EXECUTION_FRICTION_BPS,
    MIN_NET_EDGE_BPS
)

logger = logging.getLogger("EXP201A_Daemon")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

OUTPUT_DIR = Path("data/exp201")
PID_FILE = OUTPUT_DIR / "exp201a_telemetry.pid"
STATE_FILE = OUTPUT_DIR / "exp201a_telemetry_state.json"


class EXP201ATelemetryDaemon:
    def __init__(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.engine = EXP201ASpilloverEngine(output_dir=str(OUTPUT_DIR), run_shadow=True)
        self.is_running = True
        self.assets = ["SOL", "BTC", "ETH"]
        self.last_heartbeat = time.time()
        self.total_binance_events = 0
        self.total_hl_updates = 0

    def write_pid(self):
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

    def remove_pid(self):
        if PID_FILE.exists():
            PID_FILE.unlink()

    def update_state(self):
        state = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "status": "RUNNING" if self.is_running else "STOPPED",
            "pid": os.getpid(),
            "total_binance_liquidation_events": self.total_binance_events,
            "total_hl_book_updates": self.total_hl_updates,
            "raw_shocks_admitted": self.engine.raw_event_counter,
            "independent_episodes_created": self.engine.episode_counter,
            "current_episode_id": self.engine.current_episode_id,
            "pending_markouts_count": len(self.engine.pending_treatments),
            "ledger_file": str(self.engine.ledger_file),
            "governance": {
                "specification": "v3.2.1-A0.1-tokyo",
                "estimator": "PRE_TREATMENT_RESIDUALIZED_MATCHED_EVENT_ESTIMATOR",
                "primary_endpoint": "30s_markout",
                "execution_friction_bps": EXECUTION_FRICTION_BPS,
                "min_net_edge_hurdle_bps": MIN_NET_EDGE_BPS
            }
        }
        with open(STATE_FILE, "w") as f:
            f.write(json.dumps(state, indent=2))

    async def stream_binance_liquidations(self):
        """Streams Binance !forceOrder@arr liquidation events."""
        logger.info("Connecting to Binance Liquidations: %s", BINANCE_WS_URL)
        while self.is_running:
            try:
                async with websockets.connect(BINANCE_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("Binance Liquidation stream active.")
                    while self.is_running:
                        try:
                            msg_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            payload = json.loads(msg_raw)
                            self.total_binance_events += 1
                            self.engine.process_binance_liquidation(payload)
                        except asyncio.TimeoutError:
                            continue
            except Exception as e:
                if self.is_running:
                    logger.warning("Binance WS disconnected: %s. Reconnecting in 2s...", e)
                    await asyncio.sleep(2.0)

    async def stream_hyperliquid_l2(self):
        """Streams Hyperliquid L2 books for SOL, BTC, ETH."""
        logger.info("Connecting to Hyperliquid L1/L2: %s", HYPERLIQUID_WS_URL)
        while self.is_running:
            try:
                async with websockets.connect(HYPERLIQUID_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    for coin in self.assets:
                        sub = {"method": "subscribe", "subscription": {"type": "l2Book", "coin": coin}}
                        await ws.send(json.dumps(sub))
                    logger.info("Hyperliquid L2 Book subscriptions active for %s", self.assets)

                    while self.is_running:
                        try:
                            msg_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            payload = json.loads(msg_raw)
                            if payload.get("channel") == "l2Book":
                                data = payload.get("data", {})
                                coin = data.get("coin")
                                levels = data.get("levels", [[], []])
                                bids = levels[0] if len(levels) > 0 else []
                                asks = levels[1] if len(levels) > 1 else []

                                if bids and asks and coin in self.assets:
                                    best_bid = float(bids[0]["px"])
                                    best_ask = float(asks[0]["px"])
                                    bid_sz = float(bids[0]["sz"])
                                    ask_sz = float(asks[0]["sz"])
                                    self.engine.update_hl_book(coin, best_bid, best_ask, bid_sz, ask_sz)
                                    self.total_hl_updates += 1
                        except asyncio.TimeoutError:
                            continue
            except Exception as e:
                if self.is_running:
                    logger.warning("Hyperliquid WS disconnected: %s. Reconnecting in 2s...", e)
                    await asyncio.sleep(2.0)

    async def markout_checker_loop(self):
        """Periodic markout polling and heartbeat logging."""
        while self.is_running:
            self.engine.check_pending_markouts()

            now = time.time()
            if now - self.last_heartbeat >= 60.0:
                self.last_heartbeat = now
                self.update_state()
                logger.info(
                    "[EXP-201A HEARTBEAT] Binance Events: %d | HL Book Updates: %d | "
                    "Shocks Admitted: %d | Episodes: %d | Pending Markouts: %d",
                    self.total_binance_events, self.total_hl_updates,
                    self.engine.raw_event_counter, self.engine.episode_counter,
                    len(self.engine.pending_treatments)
                )

            await asyncio.sleep(0.5)

    async def start(self):
        self.write_pid()
        self.update_state()
        logger.info("Starting EXP-201A Telemetry Daemon (PID: %d)...", os.getpid())
        try:
            await asyncio.gather(
                self.stream_binance_liquidations(),
                self.stream_hyperliquid_l2(),
                self.markout_checker_loop()
            )
        finally:
            self.update_state()
            self.remove_pid()
            logger.info("EXP-201A Telemetry Daemon stopped.")


def main():
    daemon = EXP201ATelemetryDaemon()

    def handle_signal(sig, frame):
        logger.info("Shutdown signal received. Stopping daemon...")
        daemon.is_running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    asyncio.run(daemon.start())


if __name__ == "__main__":
    main()
