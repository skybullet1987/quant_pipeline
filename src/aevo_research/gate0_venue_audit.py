"""Gate 0: Venue Truth Audit for Aevo 0DTE Options.

Strictly read-only inspection module.
Verifies live contract specifications, minimum lot sizes, nearest expiries,
active orderbook spreads, fee thresholds, minimum viable capital (B_min),
and empirical WebSocket round-trip ping latency.

ISOLATION INVARIANT:
This module does NOT touch or import any Hyperliquid or perpetual pipeline code.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

try:
    import websockets
except ImportError:
    websockets = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Gate0Audit")

AEVO_REST_BASE = "https://api.aevo.xyz"
AEVO_WS_URL = "wss://ws.aevo.xyz"


@dataclass
class ContractSpecs:
    instrument_name: str
    underlying_asset: str
    strike: float
    option_type: str  # "call" or "put"
    expiry_timestamp: int
    hours_to_expiry: float
    amount_step: float
    price_step: float
    min_order_value: float
    is_active: bool


@dataclass
class OrderbookSnapshot:
    instrument_name: str
    best_bid: float
    best_bid_qty: float
    best_ask: float
    best_ask_qty: float
    mid_price: float
    spread_abs: float
    spread_pct: float
    timestamp_ns: int


@dataclass
class VenueAuditReport:
    audit_time_utc: str
    btc_contracts_found: int
    eth_contracts_found: int
    nearest_btc_expiry_hours: float
    nearest_eth_expiry_hours: float
    btc_sample_specs: List[ContractSpecs] = field(default_factory=list)
    eth_sample_specs: List[ContractSpecs] = field(default_factory=list)
    book_snapshots: List[OrderbookSnapshot] = field(default_factory=list)
    min_contract_outlay_usd: float = 0.0
    l_max_usd: float = 0.0
    b_min_usd: float = 0.0
    b_min_compliant_at_500: bool = False
    ws_ping_rtt_mean_ms: float = 0.0
    ws_ping_rtt_p50_ms: float = 0.0
    ws_ping_rtt_p95_ms: float = 0.0
    ws_ping_rtt_min_ms: float = 0.0


def http_get_json(url: str, timeout: float = 10.0) -> Any:
    """Synchronous HTTP GET with urllib (no external dependencies required)."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AevoResearchGate0/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read().decode("utf-8")
        return json.loads(data)


def fetch_live_options(asset: str = "BTC") -> List[Dict[str, Any]]:
    """Fetch live option contracts from Aevo /markets endpoint."""
    url = f"{AEVO_REST_BASE}/markets?asset={asset}&instrument_type=OPTION"
    logger.info("Querying Aevo markets for %s from %s...", asset, url)
    try:
        data = http_get_json(url)
        if isinstance(data, list):
            return [m for m in data if m.get("is_active", True) and m.get("instrument_type") == "OPTION"]
        elif isinstance(data, dict) and "markets" in data:
            return [m for m in data["markets"] if m.get("is_active", True) and m.get("instrument_type") == "OPTION"]
        return []
    except Exception as e:
        logger.error("Failed to query Aevo markets for %s: %s", asset, e)
        return []


def fetch_orderbook(instrument_name: str) -> Optional[OrderbookSnapshot]:
    """Fetch live L2 orderbook snapshot for an instrument."""
    url = f"{AEVO_REST_BASE}/orderbook?instrument_name={instrument_name}"
    try:
        t_read = time.time_ns()
        data = http_get_json(url)
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        
        best_bid = float(bids[0][0]) if bids else 0.0
        best_bid_qty = float(bids[0][1]) if bids else 0.0
        best_ask = float(asks[0][0]) if asks else 0.0
        best_ask_qty = float(asks[0][1]) if asks else 0.0
        
        if best_bid > 0 and best_ask > 0:
            mid = (best_bid + best_ask) / 2.0
            spread_abs = best_ask - best_bid
            spread_pct = (spread_abs / mid) * 100.0 if mid > 0 else 0.0
        else:
            mid = best_ask if best_ask > 0 else best_bid
            spread_abs = 0.0
            spread_pct = 0.0
            
        return OrderbookSnapshot(
            instrument_name=instrument_name,
            best_bid=best_bid,
            best_bid_qty=best_bid_qty,
            best_ask=best_ask,
            best_ask_qty=best_ask_qty,
            mid_price=mid,
            spread_abs=spread_abs,
            spread_pct=spread_pct,
            timestamp_ns=t_read,
        )
    except Exception as e:
        logger.warning("Failed to fetch orderbook for %s: %s", instrument_name, e)
        return None


def parse_contract_specs(raw: Dict[str, Any], now_epoch: float) -> Optional[ContractSpecs]:
    """Parse raw Aevo instrument metadata into ContractSpecs."""
    try:
        name = raw.get("instrument_name", "")
        asset = raw.get("underlying_asset", "")
        strike = float(raw.get("strike", 0.0))
        opt_type = raw.get("option_type", "").lower()
        
        expiry_raw = int(raw.get("expiry", 0))
        # Aevo expiry can be in nanoseconds or seconds
        if expiry_raw > 1e15:
            expiry_s = expiry_raw / 1e9
        elif expiry_raw > 1e11:
            expiry_s = expiry_raw / 1e3
        else:
            expiry_s = float(expiry_raw)
            
        hours_to_exp = max(0.0, (expiry_s - now_epoch) / 3600.0)
        
        amount_step = float(raw.get("amount_step", 0.01))
        price_step = float(raw.get("price_step", 0.1))
        min_order_value = float(raw.get("min_order_value", 10.0))
        is_active = bool(raw.get("is_active", True))
        
        return ContractSpecs(
            instrument_name=name,
            underlying_asset=asset,
            strike=strike,
            option_type=opt_type,
            expiry_timestamp=int(expiry_s),
            hours_to_expiry=hours_to_exp,
            amount_step=amount_step,
            price_step=price_step,
            min_order_value=min_order_value,
            is_active=is_active,
        )
    except Exception as e:
        logger.debug("Failed to parse instrument: %s (%s)", raw, e)
        return None


async def measure_ws_rtt_latency(num_samples: int = 30) -> Dict[str, float]:
    """Measure empirical WebSocket round-trip ping/pong latency distribution."""
    if websockets is None:
        logger.warning("websockets package not available; skipping WS RTT probe.")
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "min": 0.0}
        
    logger.info("Opening WebSocket connection to %s for %d latency probes...", AEVO_WS_URL, num_samples)
    rtts_ms: List[float] = []
    
    try:
        async with websockets.connect(AEVO_WS_URL, ping_interval=None) as ws:
            # Measure ping round-trip
            for i in range(num_samples):
                t_start = time.perf_counter()
                ping_waiter = await ws.ping()
                await asyncio.wait_for(ping_waiter, timeout=5.0)
                t_end = time.perf_counter()
                rtt_ms = (t_end - t_start) * 1000.0
                rtts_ms.append(rtt_ms)
                await asyncio.sleep(0.05)
    except Exception as e:
        logger.warning("WebSocket latency probe encountered error: %s", e)
        if not rtts_ms:
            return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "min": 0.0}
            
    rtts_ms.sort()
    n = len(rtts_ms)
    mean_val = sum(rtts_ms) / n
    p50_val = rtts_ms[int(n * 0.50)]
    p95_val = rtts_ms[min(int(n * 0.95), n - 1)]
    min_val = rtts_ms[0]
    
    logger.info(
        "WS Latency (%d samples): Min=%.2fms, P50=%.2fms, P95=%.2fms, Mean=%.2fms",
        n, min_val, p50_val, p95_val, mean_val
    )
    return {"mean": mean_val, "p50": p50_val, "p95": p95_val, "min": min_val}


def run_venue_audit() -> VenueAuditReport:
    """Execute complete Gate 0 Venue Truth Audit."""
    now_epoch = time.time()
    now_utc_str = datetime.now(timezone.utc).isoformat()
    logger.info("=== STARTING GATE 0 VENUE TRUTH AUDIT (%s) ===", now_utc_str)
    
    # 1. Fetch Instruments
    btc_raw = fetch_live_options("BTC")
    eth_raw = fetch_live_options("ETH")
    
    btc_specs: List[ContractSpecs] = []
    for raw in btc_raw:
        parsed = parse_contract_specs(raw, now_epoch)
        if parsed and parsed.hours_to_expiry > 0:
            btc_specs.append(parsed)
            
    eth_specs: List[ContractSpecs] = []
    for raw in eth_raw:
        parsed = parse_contract_specs(raw, now_epoch)
        if parsed and parsed.hours_to_expiry > 0:
            eth_specs.append(parsed)
            
    btc_specs.sort(key=lambda s: s.hours_to_expiry)
    eth_specs.sort(key=lambda s: s.hours_to_expiry)
    
    nearest_btc_hours = btc_specs[0].hours_to_expiry if btc_specs else 999.0
    nearest_eth_hours = eth_specs[0].hours_to_expiry if eth_specs else 999.0
    
    logger.info("Found %d active BTC options (Nearest: %.2f hours to expiry)", len(btc_specs), nearest_btc_hours)
    logger.info("Found %d active ETH options (Nearest: %.2f hours to expiry)", len(eth_specs), nearest_eth_hours)
    
    # 2. Inspect active near-dated orderbooks
    target_contracts: List[ContractSpecs] = []
    if btc_specs:
        target_contracts.extend(btc_specs[:5])
    if eth_specs:
        target_contracts.extend(eth_specs[:5])
        
    snapshots: List[OrderbookSnapshot] = []
    sample_outlays: List[float] = []
    
    for contract in target_contracts:
        snap = fetch_orderbook(contract.instrument_name)
        if snap:
            snapshots.append(snap)
            if snap.best_ask > 0:
                # Minimum contract outlay in USD
                outlay = snap.best_ask * contract.amount_step
                sample_outlays.append(outlay)
                logger.info(
                    "[%s] (T=%.1fh) Bid: $%.2f (Qty: %.3f) | Ask: $%.2f (Qty: %.3f) | Spread: %.2f%% | MinOutlay: $%.2f",
                    contract.instrument_name,
                    contract.hours_to_expiry,
                    snap.best_bid,
                    snap.best_bid_qty,
                    snap.best_ask,
                    snap.best_ask_qty,
                    snap.spread_pct,
                    outlay,
                )
                
    # 3. Calculate B_min (Minimum Viable Balance)
    min_outlay = min(sample_outlays) if sample_outlays else 10.0
    # Entry fee: min(0.0005 * S * Q, 0.125 * P * Q)
    # On OTM options, fee is 12.5% of premium
    fee_entry = min_outlay * 0.125
    fee_buffer = min_outlay * 0.05  # 5% buffer for slippage / terminal exit
    l_max = min_outlay + fee_entry + fee_buffer
    b_min = l_max / 0.015
    compliant_500 = b_min <= 500.0
    
    logger.info(
        "=== CAPITAL VIABILITY AUDIT ==="
        "\n  Min Single-Contract Outlay: $%.2f"
        "\n  Max Economic Loss (L_max): $%.2f (Includes 12.5%% fee + buffer)"
        "\n  Required Min Balance (B_min = L_max / 0.015): $%.2f"
        "\n  Deployable with $500 Account? %s",
        min_outlay, l_max, b_min, "YES" if compliant_500 else "NO (Requires $" + f"{b_min:.2f})"
    )
    
    # 4. Measure WebSocket Latency
    ws_stats = {"mean": 0.0, "p50": 0.0, "p95": 0.0, "min": 0.0}
    try:
        ws_stats = asyncio.run(measure_ws_rtt_latency(num_samples=25))
    except Exception as e:
        logger.warning("Could not execute async WS probe: %s", e)
        
    report = VenueAuditReport(
        audit_time_utc=now_utc_str,
        btc_contracts_found=len(btc_specs),
        eth_contracts_found=len(eth_specs),
        nearest_btc_expiry_hours=nearest_btc_hours,
        nearest_eth_expiry_hours=nearest_eth_hours,
        btc_sample_specs=btc_specs[:5],
        eth_sample_specs=eth_specs[:5],
        book_snapshots=snapshots,
        min_contract_outlay_usd=min_outlay,
        l_max_usd=l_max,
        b_min_usd=b_min,
        b_min_compliant_at_500=compliant_500,
        ws_ping_rtt_mean_ms=ws_stats["mean"],
        ws_ping_rtt_p50_ms=ws_stats["p50"],
        ws_ping_rtt_p95_ms=ws_stats["p95"],
        ws_ping_rtt_min_ms=ws_stats["min"],
    )
    
    logger.info("=== GATE 0 VENUE TRUTH AUDIT COMPLETE ===")
    return report


if __name__ == "__main__":
    report = run_venue_audit()
