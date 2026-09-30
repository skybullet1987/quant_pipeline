#!/usr/bin/env python3
"""
EXP-401: Cross-Venue Perpetual Basis & Horizon Carry Telemetry Engine
=====================================================================
Evaluates synthetic cross-venue arbitrage between Binance USD-M and Hyperliquid L1:
  - Decomposes Mid-price spread, Oracle spread, and funding rate differential.
  - Multi-Horizon Cashflow Model across H in {1h, 4h, 8h, 24h}:
      E[Pi(H)] = FundingCarry(H) + BasisConvergence(H) - Frictions - LeggingRisk
  - Strictly shadow telemetry (Zero capital at risk; no execution dispatch).
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
import aiohttp
import numpy as np
import websockets

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PIPELINE_ROOT))

logger = logging.getLogger("EXP401_BasisShadow")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BINANCE_WS_URL = "wss://fstream.binance.com/ws"
HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"
BINANCE_FUNDING_API = "https://fapi.binance.com/fapi/v1/premiumIndex"

DATA_DIR = PIPELINE_ROOT / "data" / "exp401"
STATE_FILE = DATA_DIR / "basis_shadow_state.json"
EVENTS_FILE = DATA_DIR / "basis_shadow_events.jsonl"
PID_FILE = DATA_DIR / "exp401_basis.pid"

SYMBOLS = ["BTC", "ETH", "SOL"]
BINANCE_SYMBOLS = {"BTC": "btcusdt", "ETH": "ethusdt", "SOL": "solusdt"}

# Friction Parameters (VIP-0 Base Rates)
BN_TAKER_FEE_BPS = 4.0
HL_TAKER_FEE_BPS = 4.5
ROUNDTRIP_FEES_BPS = (BN_TAKER_FEE_BPS + HL_TAKER_FEE_BPS) * 2.0  # 17.0 bps
ESTIMATED_SLIPPAGE_BPS = 2.0
LEGGING_RISK_BPS = 2.5
TOTAL_HURDLE_BPS = ROUNDTRIP_FEES_BPS + ESTIMATED_SLIPPAGE_BPS + LEGGING_RISK_BPS # 21.5 bps


class PerpBasisShadowEngine:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.running = False
        
        # State per symbol
        self.bn_quotes: Dict[str, Dict[str, float]] = {s: {"bid": 0.0, "ask": 0.0, "mid": 0.0, "funding_8h": 0.0, "ts": 0.0} for s in SYMBOLS}
        self.hl_quotes: Dict[str, Dict[str, float]] = {s: {"bid": 0.0, "ask": 0.0, "mid": 0.0, "oracle": 0.0, "funding_1h": 0.0, "ts": 0.0} for s in SYMBOLS}
        
        self.samples_count = 0
        self.dislocations_detected = 0
        self.recent_events: List[Dict[str, Any]] = []
        self.load_state()

    def load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    d = json.load(f)
                    self.samples_count = d.get("metrics", {}).get("total_samples", 0)
                    self.dislocations_detected = d.get("metrics", {}).get("dislocations_detected", 0)
            except Exception as e:
                logger.warning(f"Could not load state: {e}")

    def save_state(self):
        symbol_summary = {}
        for s in SYMBOLS:
            bn_mid = self.bn_quotes[s]["mid"]
            hl_mid = self.hl_quotes[s]["mid"]
            hl_oracle = self.hl_quotes[s]["oracle"]
            
            spread_bps = ((hl_mid - bn_mid) / bn_mid * 10000.0) if bn_mid > 0 else 0.0
            oracle_spread_bps = ((hl_oracle - bn_mid) / bn_mid * 10000.0) if bn_mid > 0 else 0.0
            
            # Annualized funding rates
            bn_ann_funding = self.bn_quotes[s]["funding_8h"] * 3 * 365 * 100.0
            hl_ann_funding = self.hl_quotes[s]["funding_1h"] * 24 * 365 * 100.0
            funding_diff_ann = hl_ann_funding - bn_ann_funding

            # Cashflow carry over 8H horizon (in bps of notional)
            carry_8h_bps = (self.hl_quotes[s]["funding_1h"] * 8 - self.bn_quotes[s]["funding_8h"]) * 10000.0
            net_8h_edge_bps = carry_8h_bps - TOTAL_HURDLE_BPS

            symbol_summary[s] = {
                "bn_mid": bn_mid,
                "hl_mid": hl_mid,
                "mid_spread_bps": round(spread_bps, 2),
                "oracle_spread_bps": round(oracle_spread_bps, 2),
                "bn_ann_funding_pct": round(bn_ann_funding, 2),
                "hl_ann_funding_pct": round(hl_ann_funding, 2),
                "funding_diff_ann_pct": round(funding_diff_ann, 2),
                "carry_8h_gross_bps": round(carry_8h_bps, 2),
                "net_8h_edge_bps": round(net_8h_edge_bps, 2),
                "hurdle_exceeded": net_8h_edge_bps > 0
            }

        state = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "governance": {
                "experiment": "EXP-401",
                "specification": "v3.2-cross-venue-basis-carry",
                "friction_hurdle_bps": TOTAL_HURDLE_BPS,
                "venues": ["Binance_USDM", "Hyperliquid_L1"]
            },
            "metrics": {
                "total_samples": self.samples_count,
                "dislocations_detected": self.dislocations_detected
            },
            "symbols": symbol_summary
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    def evaluate_spread(self, s: str):
        bn = self.bn_quotes[s]
        hl = self.hl_quotes[s]
        if bn["mid"] <= 0 or hl["mid"] <= 0:
            return

        self.samples_count += 1
        spread_bps = (hl["mid"] - bn["mid"]) / bn["mid"] * 10000.0
        carry_8h_bps = (hl["funding_1h"] * 8 - bn["funding_8h"]) * 10000.0
        net_edge_bps = abs(carry_8h_bps) - TOTAL_HURDLE_BPS

        if net_edge_bps > 0:
            self.dislocations_detected += 1
            evt = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "symbol": s,
                "spread_bps": round(spread_bps, 2),
                "carry_8h_bps": round(carry_8h_bps, 2),
                "net_edge_bps": round(net_edge_bps, 2),
                "bn_mid": bn["mid"],
                "hl_mid": hl["mid"]
            }
            with open(EVENTS_FILE, "a") as f:
                f.write(json.dumps(evt) + "\n")
            logger.info(f"[EXP-401 DISLOCATION DETECTED] {s}: Net 8H Carry Edge = {net_edge_bps:+.2f} bps | Spread: {spread_bps:+.2f} bps")

    async def update_binance_funding(self):
        """Polls Binance USD-M premiumIndex for funding rates every 60s."""
        async with aiohttp.ClientSession() as session:
            while self.running:
                try:
                    for s in SYMBOLS:
                        pair = f"{s}USDT"
                        url = f"{BINANCE_FUNDING_API}?symbol={pair}"
                        async with session.get(url, timeout=5) as resp:
                            if resp.status == 200:
                                d = await resp.json()
                                last_funding = float(d.get("lastFundingRate", 0.0))
                                self.bn_quotes[s]["funding_8h"] = last_funding
                    await asyncio.sleep(60.0)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Error fetching Binance funding: {e}")
                    await asyncio.sleep(10.0)


async def run_binance_stream(engine: PerpBasisShadowEngine):
    streams = "/".join([f"{BINANCE_SYMBOLS[s]}@bookTicker" for s in SYMBOLS])
    url = f"{BINANCE_WS_URL}/{streams}"
    logger.info(f"Connecting to Binance bookTicker stream: {url}")
    while engine.running:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                while engine.running:
                    raw = await ws.recv()
                    msg = json.loads(raw)
                    data = msg.get("data", msg)
                    sym_raw = data.get("s", "")
                    for s in SYMBOLS:
                        if sym_raw.upper() == f"{s}USDT":
                            bid = float(data.get("b", 0.0))
                            ask = float(data.get("a", 0.0))
                            engine.bn_quotes[s]["bid"] = bid
                            engine.bn_quotes[s]["ask"] = ask
                            engine.bn_quotes[s]["mid"] = (bid + ask) / 2.0
                            engine.bn_quotes[s]["ts"] = time.time()
                            engine.evaluate_spread(s)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Binance stream error: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3.0)


async def run_hl_stream(engine: PerpBasisShadowEngine):
    logger.info(f"Connecting to Hyperliquid L2 WebSocket for basis monitoring: {HYPERLIQUID_WS_URL}")
    while engine.running:
        try:
            async with websockets.connect(HYPERLIQUID_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                for s in SYMBOLS:
                    await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "l2Book", "coin": s}}))
                    await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "activeAssetCtx", "coin": s}}))

                while engine.running:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    channel = data.get("channel")
                    
                    if channel == "l2Book":
                        book = data.get("data", {})
                        coin = book.get("coin")
                        if coin in engine.hl_quotes:
                            levels = book.get("levels", [[], []])
                            if levels[0] and levels[1]:
                                bid = float(levels[0][0]["px"])
                                ask = float(levels[1][0]["px"])
                                engine.hl_quotes[coin]["bid"] = bid
                                engine.hl_quotes[coin]["ask"] = ask
                                engine.hl_quotes[coin]["mid"] = (bid + ask) / 2.0
                                engine.hl_quotes[coin]["ts"] = time.time()

                    elif channel == "activeAssetCtx":
                        ctx = data.get("data", {})
                        coin = ctx.get("coin")
                        if coin in engine.hl_quotes:
                            ctx_info = ctx.get("ctx", {})
                            oracle = float(ctx_info.get("oraclePx", 0.0))
                            funding = float(ctx_info.get("funding", 0.0))
                            engine.hl_quotes[coin]["oracle"] = oracle
                            engine.hl_quotes[coin]["funding_1h"] = funding

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Hyperliquid basis stream error: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3.0)


async def periodic_state_saver(engine: PerpBasisShadowEngine):
    while engine.running:
        try:
            engine.save_state()
            await asyncio.sleep(10.0)
        except asyncio.CancelledError:
            break


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    engine = PerpBasisShadowEngine()
    engine.running = True

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown(signum, frame):
        logger.info("Termination signal received. Shutting down EXP-401...")
        engine.running = False
        engine.save_state()
        for task in asyncio.all_tasks(loop):
            task.cancel()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        loop.create_task(run_binance_stream(engine))
        loop.create_task(run_hl_stream(engine))
        loop.create_task(engine.update_binance_funding())
        loop.create_task(periodic_state_saver(engine))
        loop.run_forever()
    finally:
        loop.close()
        if PID_FILE.exists():
            PID_FILE.unlink()
        logger.info("EXP-401 Basis Shadow Daemon stopped.")


if __name__ == "__main__":
    main()
