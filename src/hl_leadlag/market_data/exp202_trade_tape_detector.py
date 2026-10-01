#!/usr/bin/env python3
"""
EXP-202: Binance Trade-Tape De-Censoring Telemetry Engine
=========================================================
Monitors Binance USD-M futures public trades (aggTrade @ 100ms) and depth to detect
synthetic aggressive sweeps, validating them causally against the 1,000ms delayed
!forceOrder@arr stream.

Causal Invariants:
  1. Never assume an aggressive sweep is a liquidation until verified by !forceOrder.
  2. Measure dual lead times:
       Lead_event = T_exchange(forceOrder) - T_exchange(sweep)
       Lead_actionable = T_recv(forceOrder) - T_detect(sweep)
  3. Separate precision and recall:
       Precision = matches / synthetic_sweeps
       ObservableRecall = matches / eligible_forceOrders
  4. Measure proxy depth recovery (resting depth near trigger relative to 10% sweep notional).
"""

import os
import sys
import json
import time
import signal
import asyncio
import logging
from pathlib import Path
from collections import deque
from typing import Dict, List, Optional, Any, Tuple
import websockets

PIPELINE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PIPELINE_ROOT))

logger = logging.getLogger("EXP202_Detector")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BINANCE_WS_BASE = "wss://fstream.binance.com/ws"
AGGTRADE_STREAM = "btcusdt@aggTrade"
DEPTH_STREAM = "btcusdt@depth20@100ms"
FORCE_ORDER_STREAM = "!forceOrder@arr"

DATA_DIR = PIPELINE_ROOT / "data" / "exp202"
STATE_FILE = DATA_DIR / "trade_tape_telemetry_state.json"
EVENTS_FILE = DATA_DIR / "trade_tape_events.jsonl"
PID_FILE = DATA_DIR / "exp202_telemetry.pid"

# Detection Parameters
SWEEP_VOLUME_USD_HURDLE = 1_500_000.0  # $1.5M institutional volume hurdle
SWEEP_WINDOW_MS = 100.0                # 100ms rolling aggregation window
MIN_TICKS_PENETRATED = 3               # Minimum discrete tick penetration
CONFIRMATION_WINDOW_SEC = 2.0          # Max wait time for !forceOrder matching
TICK_SIZE_BTC = 0.10


class TradeTapeDeCensoringEngine:
    def __init__(self, hurdle_usd: float = SWEEP_VOLUME_USD_HURDLE):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.hurdle_usd = hurdle_usd
        self.running = False
        
        # Ingestion Queues & Buffers
        self.rolling_trades: deque = deque() # (t_ms, price, qty_usd, is_buyer_maker)
        self.current_orderbook: Dict[str, Any] = {"bids": [], "asks": [], "ts": 0.0}
        
        # Sweep Tracking
        self.pending_sweeps: Dict[str, Dict[str, Any]] = {} # sweep_id -> sweep_record
        self.completed_sweeps_count = 0
        self.matched_force_orders_count = 0
        self.unmatched_sweeps_count = 0
        self.eligible_force_orders_count = 0
        self.actionable_lead_times_ms: List[float] = []
        self.event_lead_times_ms: List[float] = []
        
        # Load state if present
        self.load_state()

    def load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                    m = data.get("metrics", data)
                    self.completed_sweeps_count = m.get("total_synthetic_sweeps", 0)
                    self.matched_force_orders_count = m.get("matched_force_orders", 0)
                    self.unmatched_sweeps_count = m.get("unmatched_sweeps", 0)
                    self.eligible_force_orders_count = m.get("eligible_force_orders_seen", 0)
                    self.actionable_lead_times_ms = data.get("actionable_lead_times_sample", data.get("lead_times_sample", []))[-500:]
                    self.event_lead_times_ms = data.get("event_lead_times_sample", [])[-500:]
            except Exception as e:
                logger.warning(f"Could not load state: {e}")

    def save_state(self):
        # Precision: Matched sweeps / Total synthetic sweeps detected
        match_precision = (self.matched_force_orders_count / self.completed_sweeps_count * 100.0) if self.completed_sweeps_count > 0 else 0.0
        # Recall: Matched sweeps / Eligible observed forceOrder broadcasts
        observable_recall = (self.matched_force_orders_count / self.eligible_force_orders_count * 100.0) if self.eligible_force_orders_count > 0 else 0.0

        p50_act = float(np.median(self.actionable_lead_times_ms)) if self.actionable_lead_times_ms else 0.0
        p95_act = float(np.percentile(self.actionable_lead_times_ms, 95)) if len(self.actionable_lead_times_ms) >= 5 else 0.0
        mean_act = float(np.mean(self.actionable_lead_times_ms)) if self.actionable_lead_times_ms else 0.0

        p50_evt = float(np.median(self.event_lead_times_ms)) if self.event_lead_times_ms else 0.0
        p95_evt = float(np.percentile(self.event_lead_times_ms, 95)) if len(self.event_lead_times_ms) >= 5 else 0.0
        mean_evt = float(np.mean(self.event_lead_times_ms)) if self.event_lead_times_ms else 0.0

        state = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "governance": {
                "experiment": "EXP-202",
                "specification": "v3.4-trade-tape-decensoring-recalled",
                "volume_hurdle_usd": self.hurdle_usd,
                "window_ms": SWEEP_WINDOW_MS,
                "matching_policy": "Strict 1-to-1 bijection (one forceOrder <-> at most one synthetic sweep)",
                "matching_constraints": {
                    "symbol": "BTCUSDT",
                    "direction": "SELL forceOrder <-> SELL_SWEEP; BUY forceOrder <-> BUY_SWEEP",
                    "max_temporal_distance_sec": CONFIRMATION_WINDOW_SEC,
                    "max_price_distance_bps": 25.0,
                    "selection_rule": "Earliest eligible pending sweep (FIFO)"
                },
                "observable_recovery_horizons_ms": [100, 250, 500],
                "lead_time_definitions": {
                    "actionable": "T_local_recv(forceOrder) - T_local_detect(synthetic_sweep)",
                    "event": "T_exchange(forceOrder) - T_exchange(sweep_trade)"
                },
                "recovery_metric_definition": "proxy_depth_recovery: resting depth near trigger relative to 10% sweep notional (proxy, not true replenishment flow)"
            },
            "metrics": {
                "total_synthetic_sweeps": self.completed_sweeps_count,
                "matched_force_orders": self.matched_force_orders_count,
                "unmatched_sweeps": self.unmatched_sweeps_count,
                "eligible_force_orders_seen": self.eligible_force_orders_count,
                "forceOrder_match_precision_pct": round(match_precision, 2),
                "forceOrder_observable_recall_pct": round(observable_recall, 2),
                "lead_time_actionable_mean_ms": round(mean_act, 1),
                "lead_time_actionable_p50_ms": round(p50_act, 1),
                "lead_time_actionable_p95_ms": round(p95_act, 1),
                "lead_time_event_mean_ms": round(mean_evt, 1),
                "lead_time_event_p50_ms": round(p50_evt, 1),
                "lead_time_event_p95_ms": round(p95_evt, 1),
                "matched_samples_count": len(self.actionable_lead_times_ms)
            },
            "actionable_lead_times_sample": self.actionable_lead_times_ms[-100:],
            "event_lead_times_sample": self.event_lead_times_ms[-100:]
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    def process_agg_trade(self, msg: Dict[str, Any], recv_ns: int):
        # msg schema: { e: 'aggTrade', E: event_ts, s: 'BTCUSDT', a: agg_trade_id, p: price, q: qty, f: first_id, l: last_id, T: trade_ts, m: is_buyer_maker }
        t_ms = msg.get("T", 0)
        px = float(msg.get("p", 0.0))
        qty = float(msg.get("q", 0.0))
        is_buyer_maker = msg.get("m", False) # True means buyer is maker (i.e. sell taker trade); False means buyer is taker (buy trade)
        notional_usd = px * qty

        self.rolling_trades.append((t_ms, px, notional_usd, is_buyer_maker, recv_ns))

        # Evict trades older than SWEEP_WINDOW_MS
        cutoff_ms = t_ms - SWEEP_WINDOW_MS
        while self.rolling_trades and self.rolling_trades[0][0] < cutoff_ms:
            self.rolling_trades.popleft()

        # Check for aggressive sweep candidate
        if len(self.rolling_trades) >= 3:
            total_buy_notional = sum(t[2] for t in self.rolling_trades if not t[3])
            total_sell_notional = sum(t[2] for t in self.rolling_trades if t[3])
            
            prices = [t[1] for t in self.rolling_trades]
            min_px, max_px = min(prices), max(prices)
            ticks_penetrated = round((max_px - min_px) / TICK_SIZE_BTC, 1)

            # Trigger condition
            if total_sell_notional >= self.hurdle_usd and ticks_penetrated >= MIN_TICKS_PENETRATED:
                self.register_synthetic_sweep("SELL_SWEEP", total_sell_notional, ticks_penetrated, min_px, max_px, t_ms, recv_ns)
            elif total_buy_notional >= self.hurdle_usd and ticks_penetrated >= MIN_TICKS_PENETRATED:
                self.register_synthetic_sweep("BUY_SWEEP", total_buy_notional, ticks_penetrated, min_px, max_px, t_ms, recv_ns)

    def register_synthetic_sweep(self, side: str, notional: float, ticks: float, min_px: float, max_px: float, exchange_ts_ms: int, recv_ns: int):
        # Debounce: avoid duplicate registrations within 250ms
        now_sec = time.time()
        for s in self.pending_sweeps.values():
            if now_sec - s["detect_time_sec"] < 0.250:
                return

        sweep_id = f"SWEEP_{exchange_ts_ms}_{side}"
        sweep_record = {
            "sweep_id": sweep_id,
            "side": side,
            "notional_usd": round(notional, 2),
            "ticks_penetrated": ticks,
            "price_low": min_px,
            "price_high": max_px,
            "exchange_ts_ms": exchange_ts_ms,
            "detect_time_ns": recv_ns,
            "detect_time_sec": now_sec,
            "matched_force_order": False,
            "lead_time_actionable_ms": None,
            "lead_time_event_ms": None,
            "proxy_depth_recovery_100ms_ratio": None,
            "proxy_depth_recovery_250ms_ratio": None,
            "proxy_depth_recovery_500ms_ratio": None,
            "forward_move_500ms_bps": None,
            "status": "PENDING_CONFIRMATION"
        }
        self.pending_sweeps[sweep_id] = sweep_record
        logger.info(f"[SYNTHETIC SWEEP DETECTED] {side} | Notional: ${notional:,.0f} | Ticks: {ticks} | Waiting for !forceOrder...")

        # Schedule recovery check in background
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.monitor_queue_recovery(sweep_id, min_px if side == "SELL_SWEEP" else max_px, notional))
        except RuntimeError:
            pass

    async def monitor_queue_recovery(self, sweep_id: str, trigger_px: float, notional: float):
        """Measures resting queue recovery proxy at observable 100ms, 250ms, and 500ms horizons."""
        horizons = [(0.100, "proxy_depth_recovery_100ms_ratio"),
                    (0.250, "proxy_depth_recovery_250ms_ratio"),
                    (0.500, "proxy_depth_recovery_500ms_ratio")]
        
        for delay, key in horizons:
            await asyncio.sleep(delay)
            if sweep_id not in self.pending_sweeps:
                return
            # Sample current orderbook depth near trigger price
            bids = self.current_orderbook.get("bids", [])
            asks = self.current_orderbook.get("asks", [])
            depth_recovered = 0.0
            if "SELL" in sweep_id:
                depth_recovered = sum(p * sz for p, sz in bids if p >= trigger_px * 0.9995)
            else:
                depth_recovered = sum(p * sz for p, sz in asks if p <= trigger_px * 1.0005)
            
            recovery_ratio = round(depth_recovered / max(notional * 0.10, 1.0), 4)
            self.pending_sweeps[sweep_id][key] = recovery_ratio

    def process_depth(self, msg: Dict[str, Any]):
        bids = [[float(p), float(q)] for p, q in msg.get("bids", [])]
        asks = [[float(p), float(q)] for p, q in msg.get("asks", [])]
        self.current_orderbook = {"bids": bids, "asks": asks, "ts": time.time()}

    def process_force_order(self, msg: Dict[str, Any], recv_ns: int):
        # msg schema: { e: 'forceOrder', E: event_ts, o: { s: 'BTCUSDT', S: 'SELL', o: 'LIMIT', f: 'IOC', q: qty, p: price, ap: avg_price, X: 'FILLED', l: last_qty, z: cum_qty, T: trade_ts } }
        order = msg.get("o", {})
        sym = order.get("s")
        if sym != "BTCUSDT":
            return

        # Track every eligible observed liquidation broadcast on BTCUSDT for true recall denominator
        self.eligible_force_orders_count += 1
        
        # Strict 1-to-1 Event Matching Policy:
        # Constraint 1: Same symbol (BTCUSDT)
        # Constraint 2: Same direction (SELL forceOrder <-> SELL_SWEEP; BUY forceOrder <-> BUY_SWEEP)
        # Constraint 3: Maximum temporal distance (0.0 <= time_delta <= CONFIRMATION_WINDOW_SEC)
        # Constraint 4: Maximum price distance (<= 25 bps between forceOrder price and sweep trigger price)
        # Constraint 5: Bijection: Each forceOrder matches at most one sweep; matched sweep is immediately pruned
        force_px = float(order.get("p", 0.0))
        expected_side = "SELL_SWEEP" if force_side == "SELL" else "BUY_SWEEP"

        eligible_sweeps = []
        for s_id, sweep in self.pending_sweeps.items():
            if sweep["side"] == expected_side:
                time_delta_sec = recv_sec - sweep["detect_time_sec"]
                if 0.0 <= time_delta_sec <= CONFIRMATION_WINDOW_SEC:
                    # Check price distance if both prices available
                    trigger_px = sweep.get("trigger_price", 0.0)
                    if force_px > 0 and trigger_px > 0:
                        px_dist_bps = abs(force_px - trigger_px) / trigger_px * 10000.0
                        if px_dist_bps > 25.0:
                            continue  # Exceeds max price distance hurdle (25 bps)
                    eligible_sweeps.append((sweep["detect_time_ns"], s_id, sweep))

        # Select earliest pending sweep (FIFO selection rule)
        if eligible_sweeps:
            eligible_sweeps.sort(key=lambda x: x[0])
            _, matched_s_id, sweep = eligible_sweeps[0]

            lead_actionable_ms = (recv_ns - sweep["detect_time_ns"]) / 1_000_000.0
            lead_event_ms = float(force_ts_ms - sweep["exchange_ts_ms"])
            sweep["matched_force_order"] = True
            sweep["lead_time_actionable_ms"] = round(lead_actionable_ms, 2)
            sweep["lead_time_event_ms"] = round(lead_event_ms, 2)
            sweep["force_order_recv_ns"] = recv_ns
            sweep["force_order_ts_ms"] = force_ts_ms
            sweep["force_order_price"] = force_px
            sweep["status"] = "CONFIRMED_BY_FORCE_ORDER"
            
            self.matched_force_orders_count += 1
            self.actionable_lead_times_ms.append(lead_actionable_ms)
            self.event_lead_times_ms.append(lead_event_ms)
            
            logger.info(f"[CONFIRMATION MATCHED 1-to-1] Sweep {matched_s_id} verified by !forceOrder! "
                        f"Actionable Lead: {lead_actionable_ms:.1f}ms | Exchange Event Lead: {lead_event_ms:.1f}ms")
            self.finalize_sweep(sweep)
        
        # Save state periodically on force orders to keep recall updated
        if self.eligible_force_orders_count % 5 == 0:
            self.save_state()

    def finalize_sweep(self, sweep: Dict[str, Any]):
        s_id = sweep["sweep_id"]
        if s_id in self.pending_sweeps:
            del self.pending_sweeps[s_id]
        
        self.completed_sweeps_count += 1
        with open(EVENTS_FILE, "a") as f:
            f.write(json.dumps(sweep) + "\n")
        self.save_state()

    def prune_stale_sweeps(self):
        now_sec = time.time()
        for s_id, sweep in list(self.pending_sweeps.items()):
            if now_sec - sweep["detect_time_sec"] > CONFIRMATION_WINDOW_SEC:
                # Timed out without matching !forceOrder -> Unmatched synthetic sweep (normal aggressive market flow)
                sweep["status"] = "UNMATCHED_AGGRESSIVE_FLOW"
                self.unmatched_sweeps_count += 1
                self.finalize_sweep(sweep)


async def run_stream(engine: TradeTapeDeCensoringEngine):
    stream_url = f"{BINANCE_WS_BASE}/{AGGTRADE_STREAM}/{DEPTH_STREAM}/{FORCE_ORDER_STREAM}"
    logger.info(f"Connecting to Binance Combined Stream: {stream_url}")

    while engine.running:
        try:
            async with websockets.connect(stream_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("[STREAM CONNECTED] Ingesting Binance aggTrade, depth20, and forceOrder streams...")
                while engine.running:
                    raw = await ws.recv()
                    recv_ns = time.time_ns()
                    msg = json.loads(raw)
                    
                    # Binance stream demux
                    data = msg.get("data", msg)
                    event_type = data.get("e")

                    if event_type == "aggTrade":
                        engine.process_agg_trade(data, recv_ns)
                    elif event_type == "depthUpdate":
                        engine.process_depth(data)
                    elif event_type == "forceOrder":
                        engine.process_force_order(data, recv_ns)

                    engine.prune_stale_sweeps()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[STREAM ERROR] Connection failed: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3.0)


def main():
    import numpy as np
    from datetime import datetime, timezone
    # Expose numpy to module scope
    globals()["np"] = np
    globals()["datetime"] = datetime
    globals()["timezone"] = timezone

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    engine = TradeTapeDeCensoringEngine()
    engine.running = True

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown(signum, frame):
        logger.info("Termination signal received. Shutting down...")
        engine.running = False
        engine.save_state()
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        loop.run_until_complete(run_stream(engine))
    finally:
        loop.close()
        if PID_FILE.exists():
            PID_FILE.unlink()
        logger.info("EXP-202 De-Censoring Telemetry Daemon stopped.")


if __name__ == "__main__":
    main()
