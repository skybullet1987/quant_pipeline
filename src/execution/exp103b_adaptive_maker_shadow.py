#!/usr/bin/env python3
"""
EXP-103B: Adaptive Maker Pegging & Short-Horizon Execution Shadow Engine
========================================================================
Evaluates 5 counterfactual maker execution models on Hyperliquid Layer 1 Derivatives:
  - Model 1 (Baseline Static): 240-second Add-Liquidity-Only (ALO) resting limit order at BBO.
  - Model 2 (Static 60s BBO): 60-second ALO resting limit order at initial BBO (unadapted baseline).
  - Model 2A (Adaptive 60s OFI Repricer): 60-second limit order with dynamic OFI re-pegging and adverse flow pause (> 5 bps).
  - Model 3 (Queue-Priority Peg): Discrete 1-tick improvement inside wide spreads (>= 3 ticks).
  - Model 4 (Native Chase Benchmark): Continuous 1-tick post-only chasing of the BBO.

Causal Invariants:
  1. Enforce discrete price grid: Integer tick multiples (never 0.5 ticks).
  2. Queue Realism Qualification: Trade-level execution shadow with improved queue-consumption semantics.
     QueueAhead(p, t) consumed strictly by aggressive trades at target price (sum Size_aggressive * 1[tradePrice == P]).
     Does not observe cancellations_ahead or full queue-position dynamics.
  3. Directional signed return: r = s * (Mid - Fill) / Fill where s = +1 (BUY), -1 (SELL).
  4. True VIP-0 fee accounting: +1.5 bps maker fee vs 4.5 bps taker fee.
"""

import os
import sys
import json
import time
import math
import signal
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
import numpy as np
import websockets

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_ROOT))

logger = logging.getLogger("EXP103B_MakerShadow")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"
DATA_DIR = PIPELINE_ROOT / "data"
STATE_FILE = DATA_DIR / "exp103b_maker_shadow_state.json"
LEDGER_FILE = DATA_DIR / "shadow_maker_execution.jsonl"
PID_FILE = DATA_DIR / "exp103b_maker.pid"

# Venue Constraints (Hyperliquid Mainnet / Testnet)
TICK_SIZES = {
    "ETH": 0.10,
    "BTC": 1.00,
    "SOL": 0.01
}
MAKER_FEE_BPS = 1.5     # +1.5 bps fee (cost to trader on VIP-0)
TAKER_FEE_BPS = 4.5     # +4.5 bps fee (cost to trader on VIP-0)


class AdaptiveMakerShadowEngine:
    def __init__(self, symbols: List[str] = ["ETH", "BTC", "SOL"]):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.symbols = symbols
        self.running = False
        
        # Market State
        self.orderbooks: Dict[str, Dict[str, Any]] = {
            s: {"bids": [], "asks": [], "mid": 0.0, "spread_ticks": 0, "ts": 0.0} for s in symbols
        }
        self.recent_trades: Dict[str, deque] = {s: deque(maxlen=200) for s in symbols}
        
        # Counterfactual Order State
        self.active_virtual_orders: List[Dict[str, Any]] = []
        self.completed_virtual_orders: List[Dict[str, Any]] = []
        
        # Load state
        self.load_state()

    def load_state(self):
        if LEDGER_FILE.exists():
            with open(LEDGER_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            rec = json.loads(line)
                            # Backwards compatibility: accurately map previous static 60s BBO observations
                            if rec.get("model") == "MODEL_2_ADAPTIVE_60S":
                                rec["model"] = "MODEL_2_60S_STATIC_BBO"
                            self.completed_virtual_orders.append(rec)
                        except Exception as parse_err:
                            logger.warning(f"Skipping malformed ledger line: {parse_err}")
        logger.info(f"Loaded {len(self.completed_virtual_orders)} completed counterfactual orders.")

    def save_state(self):
        total = len(self.completed_virtual_orders)
        if total == 0:
            return

        models = [
            "MODEL_1_STATIC_240S",
            "MODEL_2_60S_STATIC_BBO",
            "MODEL_2A_ADAPTIVE_OFI",
            "MODEL_3_QUEUE_PRIORITY",
            "MODEL_4_NATIVE_CHASE"
        ]
        stats = {}
        for m in models:
            m_orders = [o for o in self.completed_virtual_orders if o.get("model") == m]
            m_total = len(m_orders)
            if m_total == 0:
                stats[m] = {
                    "total_orders": 0,
                    "fills_count": 0,
                    "fill_rate_pct": 0.0,
                    "mean_adverse_selection_1s_bps": 0.0,
                    "mean_adverse_selection_5s_bps": 0.0,
                    "expected_net_edge_per_fill_bps": 0.0,
                    "expected_pnl_per_order_attempt_usd": 0.0,
                    "cumulative_net_pnl_usd": 0.0,
                    "maker_fee_paid_usd": 0.0
                }
                continue
            fills = [o for o in m_orders if o.get("status") == "FILLED"]
            fill_rate = len(fills) / m_total * 100.0
            adv_1s = [f.get("adverse_selection_1s_bps", 0.0) for f in fills]
            adv_5s = [f.get("adverse_selection_5s_bps", 0.0) for f in fills]
            net_pnls = [f.get("net_pnl_usd", 0.0) for f in fills]
            net_edges = [f.get("net_edge_bps", 0.0) for f in fills]

            # Dimensional correction:
            # E[PnL/attempt] = (FillRate / 100) * (E[NetEdge_bps | Fill] / 10000) * MeanSize_USD
            mean_size_usd = float(np.mean([o.get("size_usd", 20.0) for o in m_orders])) if m_orders else 20.0
            mean_net_edge = float(np.mean(net_edges)) if net_edges else 0.0
            expected_pnl_attempt = (len(fills) / m_total) * (mean_net_edge / 10000.0) * mean_size_usd if m_total > 0 else 0.0

            stats[m] = {
                "total_orders": m_total,
                "fills_count": len(fills),
                "fill_rate_pct": round(fill_rate, 2),
                "mean_adverse_selection_1s_bps": round(float(np.mean(adv_1s)), 2) if adv_1s else 0.0,
                "mean_adverse_selection_5s_bps": round(float(np.mean(adv_5s)), 2) if adv_5s else 0.0,
                "expected_net_edge_per_fill_bps": round(mean_net_edge, 2),
                "expected_pnl_per_order_attempt_usd": round(expected_pnl_attempt, 4),
                "cumulative_net_pnl_usd": round(sum(net_pnls), 2),
                "maker_fee_paid_usd": round(sum(f.get("maker_fee_usd", 0.0) for f in fills), 4)
            }

        state = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "governance": {
                "experiment": "EXP-103B",
                "specification": "v3.4-adaptive-maker-preregistered",
                "research_role": "TELEMETRY_ONLY",
                "research_status": "OBSERVATION_ONLY",
                "purpose": "EXECUTION_MODEL_DISCOVERY",
                "portfolio_eligibility": False,
                "promotion_path": False,
                "note": "Execution instrumentation only. Discovery of maker-fill and queue dynamics; no new alpha discovery.",
                "promotion_criterion": "NetPnL(adaptive) > NetPnL(static) with adverse selection within bounds",
                "maker_fee_bps": MAKER_FEE_BPS,
                "taker_fee_bps": TAKER_FEE_BPS,
                "execution_model_qualification": "Trade-level execution shadow with improved queue-consumption semantics (not full queue-position simulation; Q_ahead does not track cancellations_ahead)",
                "expected_pnl_per_attempt_formula": "E[PnL/attempt] = (FillRate/100) * (E[NetEdge_bps | Fill]/10000) * MeanSize_USD",
                "queue_consumption_invariant": "Strict trades_at_price == target_price (sum Size_aggressive * 1[tradePrice == targetPrice])",
                "directional_return_invariant": "Signed markout r = s * (Mid - Fill) / Fill"
            },
            "models_comparison": stats
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    def trigger_rebalance_scenario(self, symbol: str, side: str = "BUY", size_usd: float = 115.0):
        """Simulates an autonomous rebalance event across all 5 models."""
        ob = self.orderbooks.get(symbol)
        if not ob or not ob["bids"] or not ob["asks"]:
            return

        tick = TICK_SIZES.get(symbol, 0.10)
        best_bid = ob["bids"][0][0]
        best_ask = ob["asks"][0][0]
        mid = ob.get("mid", (best_bid + best_ask) / 2.0)
        spread_ticks = round((best_ask - best_bid) / tick)

        now_sec = time.time()
        order_id_base = f"VORD_{symbol}_{int(now_sec*1000)}"

        # Initial Prices and Queues per model
        # Model 1 (Static 240s ALO): Peg to best BBO
        p1 = best_bid if side == "BUY" else best_ask
        q_ahead_1 = ob["bids"][0][1] if side == "BUY" else ob["asks"][0][1]

        # Model 2 (Static 60s BBO): 60-second limit order at BBO without OFI adaptation
        p2 = p1
        q_ahead_2 = q_ahead_1

        # Model 2A (Adaptive 60s OFI Repricer): 60-second limit order with OFI-conditioned re-pegging & adverse flow pause (> 5 bps)
        p2a = p1
        q_ahead_2a = q_ahead_1

        # Model 3 (Queue-Priority Peg): If spread >= 3 ticks, improve 1 tick inside spread; else BBO
        if spread_ticks >= 3:
            p3 = round(best_bid + tick, 4) if side == "BUY" else round(best_ask - tick, 4)
            q_ahead_3 = 0.0  # At new improved price, we are front of queue
        else:
            p3 = p1
            q_ahead_3 = q_ahead_1

        # Model 4 (Native Chase): Continuously tracks BBO
        p4 = p1
        q_ahead_4 = q_ahead_1

        orders = [
            {"model": "MODEL_1_STATIC_240S", "price": p1, "queue_ahead": q_ahead_1, "timeout_sec": 240.0},
            {"model": "MODEL_2_60S_STATIC_BBO", "price": p2, "queue_ahead": q_ahead_2, "timeout_sec": 60.0},
            {"model": "MODEL_2A_ADAPTIVE_OFI", "price": p2a, "queue_ahead": q_ahead_2a, "timeout_sec": 60.0},
            {"model": "MODEL_3_QUEUE_PRIORITY", "price": p3, "queue_ahead": q_ahead_3, "timeout_sec": 60.0},
            {"model": "MODEL_4_NATIVE_CHASE", "price": p4, "queue_ahead": q_ahead_4, "timeout_sec": 240.0}
        ]

        for o in orders:
            v_order = {
                "order_id": f"{order_id_base}_{o['model']}",
                "model": o["model"],
                "symbol": symbol,
                "side": side,
                "target_price": o["price"],
                "initial_price": o["price"],
                "initial_mid": mid,
                "queue_ahead": o["queue_ahead"],
                "size_usd": size_usd,
                "shares": round(size_usd / o["price"], 4),
                "created_sec": now_sec,
                "timeout_sec": o["timeout_sec"],
                "trades_at_price": 0.0,
                "paused": False,
                "paused_reason": "",
                "status": "OPEN",
                "fill_price": None,
                "fill_time_sec": None,
                "adverse_selection_1s_bps": 0.0,
                "adverse_selection_5s_bps": 0.0,
                "maker_fee_usd": 0.0,
                "net_pnl_usd": 0.0,
                "net_edge_bps": 0.0
            }
            self.active_virtual_orders.append(v_order)

        logger.info(f"[EXP-103B REBALANCE TRIGGERED] {symbol} {side} ${size_usd:.0f} | 5 Counterfactual Models Armed (Spread: {spread_ticks} ticks)")

    def calculate_ofi_5s(self, symbol: str, now_sec: float) -> float:
        """Computes Order Flow Imbalance over the last 5 seconds from recent trades."""
        trades = self.recent_trades.get(symbol, [])
        cutoff = now_sec - 5.0
        buy_vol = sum(t[2] for t in trades if t[0] >= cutoff and t[3] == "BUY")
        sell_vol = sum(t[2] for t in trades if t[0] >= cutoff and t[3] == "SELL")
        total_vol = buy_vol + sell_vol
        return (buy_vol - sell_vol) / total_vol if total_vol > 0 else 0.0

    def process_trade_update(self, symbol: str, price: float, sz: float, side: str):
        now_sec = time.time()
        # Record trade in rolling buffer for OFI calculation
        self.recent_trades[symbol].append((now_sec, price, sz, side))
        ofi_5s = self.calculate_ofi_5s(symbol, now_sec)

        ob = self.orderbooks.get(symbol, {})
        current_mid = ob.get("mid", price)

        for o in list(self.active_virtual_orders):
            if o["symbol"] != symbol or o["status"] != "OPEN":
                continue

            # Model 2A (Adaptive OFI Repricer): OFI-conditioned re-pegging & adverse flow pause (> 5 bps)
            if o["model"] == "MODEL_2A_ADAPTIVE_OFI":
                # Compute adverse price drift against order in bps
                # For BUY: adverse drift is mid falling below initial_mid
                # For SELL: adverse drift is mid rising above initial_mid
                drift_bps = ((o["initial_mid"] - current_mid) / o["initial_mid"] * 10000.0) if o["side"] == "BUY" else ((current_mid - o["initial_mid"]) / o["initial_mid"] * 10000.0)
                
                # Adverse flow trigger: adverse drift > 5.0 bps OR heavy opposing OFI
                adverse_flow = (drift_bps > 5.0) or (o["side"] == "BUY" and ofi_5s < -0.60) or (o["side"] == "SELL" and ofi_5s > 0.60)
                if adverse_flow:
                    if not o["paused"]:
                        o["paused"] = True
                        o["paused_reason"] = f"Adverse flow: drift={drift_bps:.1f}bps, OFI={ofi_5s:.2f}"
                        logger.info(f"[EXP-103B PAUSE] {o['order_id']} paused: {o['paused_reason']}")
                else:
                    # If flow normalizes, unpause and re-peg to current BBO
                    if o["paused"] and ofi_5s >= -0.20 if o["side"] == "BUY" else ofi_5s <= 0.20:
                        o["paused"] = False
                        o["paused_reason"] = ""
                    
                    # Re-peg to current BBO if BBO improved and order not paused
                    if not o["paused"]:
                        current_bbo = ob["bids"][0][0] if (o["side"] == "BUY" and ob.get("bids")) else (ob["asks"][0][0] if ob.get("asks") else o["target_price"])
                        if current_bbo != o["target_price"]:
                            o["target_price"] = current_bbo
                            o["queue_ahead"] = ob["bids"][0][1] if (o["side"] == "BUY" and ob.get("bids")) else (ob["asks"][0][1] if ob.get("asks") else 0.0)
                            o["trades_at_price"] = 0.0

            # Model 4 (Chase): Update price if BBO moved
            if o["model"] == "MODEL_4_NATIVE_CHASE":
                current_bbo = ob["bids"][0][0] if (o["side"] == "BUY" and ob.get("bids")) else (ob["asks"][0][0] if ob.get("asks") else o["target_price"])
                if current_bbo != o["target_price"]:
                    o["target_price"] = current_bbo
                    o["queue_ahead"] = ob["bids"][0][1] if (o["side"] == "BUY" and ob.get("bids")) else (ob["asks"][0][1] if ob.get("asks") else 0.0)
                    o["trades_at_price"] = 0.0

            # CAUSAL INVARIANT: Queue Consumption strictly by aggressive trades at target price
            # QueueConsumed(P, t) = sum Size_aggressive * 1[tradePrice == P]
            if not o.get("paused", False):
                is_fill_trade = False
                if o["side"] == "BUY" and side == "SELL" and math.isclose(price, o["target_price"], abs_tol=1e-5):
                    is_fill_trade = True
                elif o["side"] == "SELL" and side == "BUY" and math.isclose(price, o["target_price"], abs_tol=1e-5):
                    is_fill_trade = True

                if is_fill_trade:
                    o["trades_at_price"] += sz
                    if o["trades_at_price"] >= o["queue_ahead"]:
                        # Order Filled!
                        o["status"] = "FILLED"
                        o["fill_price"] = o["target_price"]
                        o["fill_time_sec"] = now_sec
                        o["maker_fee_usd"] = o["size_usd"] * (MAKER_FEE_BPS / 10000.0)
                        
                        # Schedule post-fill directional adverse selection markout
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(self.markout_adverse_selection(o))
                        except RuntimeError:
                            pass
                        self.active_virtual_orders.remove(o)

    async def markout_adverse_selection(self, order: Dict[str, Any]):
        symbol = order["symbol"]
        fill_px = order["fill_price"]
        s = 1.0 if order["side"] == "BUY" else -1.0  # Signed direction: +1 for BUY, -1 for SELL
        
        await asyncio.sleep(1.0)
        mid_1s = self.orderbooks[symbol].get("mid", fill_px)
        # Directional adverse selection: positive value means market moved adversely against filled order
        order["adverse_selection_1s_bps"] = round(s * (fill_px - mid_1s) / fill_px * 10000.0, 2)

        await asyncio.sleep(4.0)
        mid_5s = self.orderbooks[symbol].get("mid", fill_px)
        order["adverse_selection_5s_bps"] = round(s * (fill_px - mid_5s) / fill_px * 10000.0, 2)
        
        # Directional signed return: r = s * (Mid_5s - Fill_Px) / Fill_Px
        pnl_pct = s * (mid_5s - fill_px) / fill_px
        maker_fee = order.get("maker_fee_usd", order["size_usd"] * (MAKER_FEE_BPS / 10000.0))
        order["net_pnl_usd"] = round(order["size_usd"] * pnl_pct - maker_fee, 4)
        order["net_edge_bps"] = round((pnl_pct - (MAKER_FEE_BPS / 10000.0)) * 10000.0, 2)

        self.completed_virtual_orders.append(order)
        with open(LEDGER_FILE, "a") as f:
            f.write(json.dumps(order) + "\n")
        self.save_state()

        logger.info(f"[EXP-103B FILL RECORDED] {order['model']} {order['side']} on {symbol}: "
                    f"Fill Px: {fill_px:.2f} | Adv 1s: {order['adverse_selection_1s_bps']:+.1f} bps | "
                    f"Net PnL: ${order['net_pnl_usd']:+.3f} | Net Edge: {order['net_edge_bps']:+.1f} bps")

    def check_timeouts(self):
        now_sec = time.time()
        for o in list(self.active_virtual_orders):
            if now_sec - o["created_sec"] > o["timeout_sec"]:
                o["status"] = "EXPIRED"
                self.active_virtual_orders.remove(o)
                self.completed_virtual_orders.append(o)
                with open(LEDGER_FILE, "a") as f:
                    f.write(json.dumps(o) + "\n")
                self.save_state()


async def stream_hyperliquid(engine: AdaptiveMakerShadowEngine):
    logger.info(f"Connecting to Hyperliquid L2 WebSocket: {HYPERLIQUID_WS_URL}")
    while engine.running:
        try:
            async with websockets.connect(HYPERLIQUID_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                # Subscribe to l2Book and trades for configured symbols
                for sym in engine.symbols:
                    await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "l2Book", "coin": sym}}))
                    await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "trades", "coin": sym}}))

                logger.info(f"[STREAM CONNECTED] Ingesting L2 book & trades for {engine.symbols}...")
                
                # Synthetic periodic rebalance trigger every 120s for continuous benchmarking
                last_trigger_ts = time.time()

                while engine.running:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    channel = data.get("channel")

                    if channel == "l2Book":
                        book_data = data.get("data", {})
                        coin = book_data.get("coin")
                        if coin in engine.orderbooks:
                            levels = book_data.get("levels", [[], []])
                            bids = [[float(l["px"]), float(l["sz"])] for l in levels[0]]
                            asks = [[float(l["px"]), float(l["sz"])] for l in levels[1]]
                            mid = (bids[0][0] + asks[0][0]) / 2.0 if bids and asks else 0.0
                            spread_ticks = round((asks[0][0] - bids[0][0]) / TICK_SIZES.get(coin, 0.10)) if bids and asks else 0
                            engine.orderbooks[coin] = {
                                "bids": bids, "asks": asks, "mid": mid, "spread_ticks": spread_ticks, "ts": time.time()
                            }

                    elif channel == "trades":
                        trades_data = data.get("data", [])
                        for t in trades_data:
                            coin = t.get("coin")
                            if coin in engine.symbols:
                                px = float(t.get("px", 0.0))
                                sz = float(t.get("sz", 0.0))
                                side = t.get("side", "BUY") # side of aggressor
                                engine.process_trade_update(coin, px, sz, side)

                    # Trigger regular rebalance benchmark scenario every 120s
                    if time.time() - last_trigger_ts >= 120.0:
                        engine.trigger_rebalance_scenario("ETH", "BUY", 115.0)
                        last_trigger_ts = time.time()

                    engine.check_timeouts()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[STREAM ERROR] Hyperliquid connection error: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3.0)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    engine = AdaptiveMakerShadowEngine()
    engine.running = True

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown(signum, frame):
        logger.info("Termination signal received. Shutting down EXP-103B...")
        engine.running = False
        engine.save_state()
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        loop.run_until_complete(stream_hyperliquid(engine))
    finally:
        loop.close()
        if PID_FILE.exists():
            PID_FILE.unlink()
        logger.info("EXP-103B Adaptive Maker Shadow Daemon stopped.")


if __name__ == "__main__":
    main()
