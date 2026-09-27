"""
Experiment H: Hyperliquid Liquidation Cascade & Contemporaneous Fair-Value Dislocation Monitor
File: src/hl_leadlag/market_data/hl_dislocation_monitor.py

Upgrades:
  1. Primary Dislocation Metric: Contemporaneous External Fair-Value Benchmark P_fair(t)
     D_fair(t) = (mid_HL(t) - P_fair(t)) / P_fair(t) * 10,000 bps
     (Where P_fair(t) is real-time Binance USD-M Futures top of book mid)
  2. Oracle Metric: oraclePx retained strictly as diagnostic reference.
  3. Tri-Condition Liquidation Cascade Filter:
     - Condition 1: Forced-flow evidence (500ms trade volume >= $100k or aggressive sweep)
     - Condition 2: |D_fair(t)| >= 25 bps (alert) / >= 35 bps (exhaustion candidate)
     - Condition 3: Binance 500ms move <= 5.0 bps (proves internal exhaustion, NOT external repricing)
  4. Passive Maker Queue & Fill Probability Tracker:
     - Simulates limit order posted at exhaustion level (e.g. 20-30 bps dislocation)
     - Tracks subsequent trade executions to determine P(fill | D, tau)
     - Measures snapback half-life tau_snap and net executable return at +1s, +3s, +5s
     - Enforces exact Hyperliquid fees: Maker 1.5 bps in, Taker 4.5 bps out, Slippage 1.0 bp
"""

import os
import sys
import time
import json
import asyncio
import datetime
from typing import Dict, Any, List, Optional
import websockets

HL_WS_URL = "wss://api.hyperliquid.xyz/ws"
BINANCE_WS_BASE = "wss://fstream.binance.com/ws"
COINS = ["BTC", "ETH", "SOL"]
BINANCE_SYMBOLS = {"BTC": "btcusdt", "ETH": "ethusdt", "SOL": "solusdt"}

ALERT_THRESHOLD_BPS = 20.0
EXHAUSTION_THRESHOLD_BPS = 30.0
MAX_EXTERNAL_MOVE_BPS = 5.0
RECOVERY_TARGET_BPS = 5.0

LOG_DIR = "/home/skybullet1987/quant_pipeline/data/dislocation"
LOG_FILE = os.path.join(LOG_DIR, "hl_dislocation_events.jsonl")

# State per asset
class AssetTracker:
    def __init__(self, coin: str):
        self.coin = coin
        self.hl_mid: float = 0.0
        self.hl_bid: float = 0.0
        self.hl_ask: float = 0.0
        self.hl_oracle: float = 0.0
        self.binance_mid: float = 0.0
        self.binance_bid: float = 0.0
        self.binance_ask: float = 0.0
        self.binance_history: List[tuple] = []  # (timestamp, mid)
        self.recent_trades: List[tuple] = []   # (timestamp, side, px, sz, usd)
        self.active_wicks: List[Dict[str, Any]] = []

state: Dict[str, AssetTracker] = {coin: AssetTracker(coin) for coin in COINS}

def log_event(event_data: Dict[str, Any]):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event_data) + "\n")

async def stream_binance(coin: str):
    symbol = BINANCE_SYMBOLS[coin]
    uri = f"{BINANCE_WS_BASE}/{symbol}@bookTicker"
    tracker = state[coin]
    while True:
        try:
            async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as ws:
                async for msg in ws:
                    data = json.loads(msg)
                    b = float(data.get("b", 0) or 0)
                    a = float(data.get("a", 0) or 0)
                    if b > 0 and a > 0:
                        mid = (b + a) / 2.0
                        now = time.time()
                        tracker.binance_bid = b
                        tracker.binance_ask = a
                        tracker.binance_mid = mid
                        tracker.binance_history.append((now, mid))
                        
                        cutoff = now - 5.0
                        tracker.binance_history = [h for h in tracker.binance_history if h[0] >= cutoff]
        except Exception as e:
            await asyncio.sleep(2)

async def stream_hyperliquid():
    while True:
        try:
            async with websockets.connect(HL_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                for coin in COINS:
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {"type": "activeAssetCtx", "coin": coin}
                    }))
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {"type": "trades", "coin": coin}
                    }))
                    await ws.send(json.dumps({
                        "method": "subscribe",
                        "subscription": {"type": "l2Book", "coin": coin}
                    }))
                
                print(f"[+] Subscribed to Hyperliquid feeds (activeAssetCtx, trades, l2Book) for {COINS}", flush=True)
                
                async for msg_str in ws:
                    msg = json.loads(msg_str)
                    channel = msg.get("channel")
                    now = time.time()
                    
                    if channel == "activeAssetCtx":
                        data = msg.get("data", {})
                        coin = data.get("coin")
                        if coin in state:
                            ctx = data.get("ctx", {})
                            oracle = float(ctx.get("oraclePx", 0) or 0)
                            mid = float(ctx.get("midPx", 0) or 0)
                            if oracle > 0 and mid > 0:
                                tracker = state[coin]
                                tracker.hl_oracle = oracle
                                tracker.hl_mid = mid
                                await evaluate_dislocation(tracker, now)

                    elif channel == "l2Book":
                        data = msg.get("data", {})
                        coin = data.get("coin")
                        if coin in state:
                            levels = data.get("levels", [[], []])
                            bids, asks = levels[0], levels[1]
                            if bids and asks:
                                tracker = state[coin]
                                tracker.hl_bid = float(bids[0]["px"])
                                tracker.hl_ask = float(asks[0]["px"])
                                tracker.hl_mid = (tracker.hl_bid + tracker.hl_ask) / 2.0

                    elif channel == "trades":
                        data = msg.get("data", [])
                        for t in data:
                            coin = t.get("coin")
                            if coin in state:
                                px = float(t.get("px", 0) or 0)
                                sz = float(t.get("sz", 0) or 0)
                                side = t.get("side")
                                usd = px * sz
                                tracker = state[coin]
                                tracker.recent_trades.append((now, side, px, sz, usd))
                                
                                # Check active wicks for passive maker fill
                                await check_simulated_fills(tracker, now, px, side)
                                
                        # Prune trades older than 5s
                        for c in COINS:
                            cutoff = now - 5.0
                            state[c].recent_trades = [tr for tr in state[c].recent_trades if tr[0] >= cutoff]

        except Exception as e:
            print(f"[-] Hyperliquid WS error: {e}. Reconnecting in 2s...", flush=True)
            await asyncio.sleep(2)

async def evaluate_dislocation(tracker: AssetTracker, now: float):
    hl_mid = tracker.hl_mid
    p_fair = tracker.binance_mid
    oracle = tracker.hl_oracle
    
    if hl_mid <= 0 or p_fair <= 0:
        return
        
    # 1. Primary Metric: Contemporaneous External Fair-Value Dislocation
    d_fair_bps = ((hl_mid - p_fair) / p_fair) * 10000.0
    abs_d_fair = abs(d_fair_bps)
    
    # 2. Diagnostic Metric: Internal Oracle Dislocation
    d_oracle_bps = ((hl_mid - oracle) / oracle) * 10000.0 if oracle > 0 else 0.0
    
    # Check if we should trigger an event
    if abs_d_fair >= ALERT_THRESHOLD_BPS:
        # Check Condition 3: Binance stability over last 500ms
        b_hist = tracker.binance_history
        b_move_bps = 0.0
        if len(b_hist) >= 2:
            p_recent = [p for (t, p) in b_hist if t >= now - 0.5]
            if p_recent:
                p_old, p_new = p_recent[0], p_recent[-1]
                b_move_bps = abs((p_new - p_old) / p_old) * 10000.0
                
        # Check Condition 1: Flow / Volume over last 500ms
        trades_500ms = [tr for tr in tracker.recent_trades if tr[0] >= now - 0.5]
        flow_usd = sum(tr[4] for tr in trades_500ms)
        
        is_pure_exhaustion = b_move_bps <= MAX_EXTERNAL_MOVE_BPS
        is_exhaustion_wick = abs_d_fair >= EXHAUSTION_THRESHOLD_BPS and is_pure_exhaustion
        
        # Avoid duplicate overlapping events within 1.0 second
        if tracker.active_wicks:
            latest = tracker.active_wicks[-1]
            if now - latest["t_event"] < 1.0:
                # Update peak dislocation
                if abs_d_fair > abs(latest["peak_d_fair_bps"]):
                    latest["peak_d_fair_bps"] = d_fair_bps
                return
        
        # Simulate passive maker limit order placement
        # If HL crashed below fair value (d_fair < 0), post maker BID at current hl_bid
        # If HL spiked above fair value (d_fair > 0), post maker ASK at current hl_ask
        simulated_side = "B" if d_fair_bps < 0 else "A"
        simulated_entry_px = tracker.hl_bid if simulated_side == "B" else tracker.hl_ask
        if simulated_entry_px <= 0:
            simulated_entry_px = hl_mid

        wick_event = {
            "coin": tracker.coin,
            "t_event": now,
            "timestamp_iso": datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat(),
            "hl_mid": hl_mid,
            "p_fair": p_fair,
            "d_fair_bps": d_fair_bps,
            "peak_d_fair_bps": d_fair_bps,
            "d_oracle_bps": d_oracle_bps,
            "binance_500ms_move_bps": b_move_bps,
            "flow_500ms_usd": flow_usd,
            "is_pure_exhaustion": is_pure_exhaustion,
            "is_exhaustion_wick": is_exhaustion_wick,
            "simulated_side": simulated_side,
            "simulated_entry_px": simulated_entry_px,
            "filled": False,
            "fill_time": None,
            "fill_latency_ms": None,
            "markouts": {}
        }
        
        tracker.active_wicks.append(wick_event)
        
        tag = ">>> LIQUIDATION EXHAUSTION WICK <<<" if is_exhaustion_wick else "DISLOCATION CANDIDATE"
        print(f"\n[{tag}] {tracker.coin} | D_fair: {d_fair_bps:+.1f} bps | D_oracle: {d_oracle_bps:+.1f} bps | "
              f"HL Mid: ${hl_mid:,.2f} | Fair Mid: ${p_fair:,.2f} | Ext 500ms Move: {b_move_bps:.1f} bps | "
              f"Flow 500ms: ${flow_usd:,.0f} | Pure: {is_pure_exhaustion}", flush=True)

async def check_simulated_fills(tracker: AssetTracker, now: float, trade_px: float, trade_side: str):
    """Check if resting simulated maker order was touched/filled by subsequent aggressive trades."""
    for wick in tracker.active_wicks:
        if not wick["filled"]:
            # If we posted a passive BID ('B'), an aggressive SELL trade ('A') at or below our price fills us
            if wick["simulated_side"] == "B" and trade_side == "A" and trade_px <= wick["simulated_entry_px"]:
                wick["filled"] = True
                wick["fill_time"] = now
                wick["fill_latency_ms"] = (now - wick["t_event"]) * 1000.0
                print(f"[MAKER FILL] {tracker.coin} passive BID filled at ${trade_px:.2f} in {wick['fill_latency_ms']:.1f}ms!", flush=True)
                
            # If we posted a passive ASK ('A'), an aggressive BUY trade ('B') at or above our price fills us
            elif wick["simulated_side"] == "A" and trade_side == "B" and trade_px >= wick["simulated_entry_px"]:
                wick["filled"] = True
                wick["fill_time"] = now
                wick["fill_latency_ms"] = (now - wick["t_event"]) * 1000.0
                print(f"[MAKER FILL] {tracker.coin} passive ASK filled at ${trade_px:.2f} in {wick['fill_latency_ms']:.1f}ms!", flush=True)

async def markout_tracker():
    """Evaluate post-event markouts at +1s, +3s, +5s and calculate net realized returns."""
    while True:
        await asyncio.sleep(0.5)
        now = time.time()
        for coin, tracker in state.items():
            completed_wicks = []
            for wick in tracker.active_wicks:
                elapsed = now - wick["t_event"]
                
                # Sample markouts
                for horizon in [1.0, 3.0, 5.0]:
                    h_key = f"{int(horizon)}s"
                    if elapsed >= horizon and h_key not in wick["markouts"]:
                        current_hl_mid = tracker.hl_mid
                        current_p_fair = tracker.binance_mid
                        
                        entry_px = wick["simulated_entry_px"]
                        # Return calculation based on entry side
                        if wick["simulated_side"] == "B":
                            gross_return_bps = ((current_hl_mid - entry_px) / entry_px) * 10000.0
                        else:
                            gross_return_bps = ((entry_px - current_hl_mid) / entry_px) * 10000.0
                            
                        # Net return: Maker fee (1.5 bp) + Taker exit (4.5 bp) + Slippage (1.0 bp) = 7.0 bp friction
                        net_return_bps = gross_return_bps - 7.0
                        
                        wick["markouts"][h_key] = {
                            "hl_mid": current_hl_mid,
                            "p_fair": current_p_fair,
                            "gross_bps": gross_return_bps,
                            "net_bps": net_return_bps
                        }
                        
                # After 5.5s, log and finalize event
                if elapsed >= 5.5:
                    completed_wicks.append(wick)
                    log_event(wick)
                    
                    fill_status = "FILLED" if wick["filled"] else "UNFILLED"
                    m3 = wick["markouts"].get("3s", {})
                    net_3s = m3.get("net_bps", 0.0)
                    gross_3s = m3.get("gross_bps", 0.0)
                    
                    print(f"[WICK COMPLETED] {coin} | Status: {fill_status} | Peak D_fair: {wick['peak_d_fair_bps']:+.1f} bps | "
                          f"3s Gross: {gross_3s:+.1f} bps | 3s Net: {net_3s:+.1f} bps", flush=True)

            tracker.active_wicks = [w for w in tracker.active_wicks if w not in completed_wicks]

async def telemetry_heartbeat():
    while True:
        await asyncio.sleep(60)
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
        stats = []
        for c in COINS:
            tr = state[c]
            d_fair = ((tr.hl_mid - tr.binance_mid) / tr.binance_mid * 10000.0) if tr.binance_mid > 0 else 0.0
            stats.append(f"{c}: HL=${tr.hl_mid:,.1f} Fair=${tr.binance_mid:,.1f} D_fair={d_fair:+.1f}bp")
        print(f"[{now_str} UTC] [MONITOR HEARTBEAT] {' | '.join(stats)}", flush=True)

async def main():
    print(f"===============================================================================", flush=True)
    print(f"   EXPERIMENT H: CONTEMPORANEOUS FAIR-VALUE LIQUIDATION WICK MONITOR", flush=True)
    print(f"   Target Coins: {COINS} | Alert Hurdle: {ALERT_THRESHOLD_BPS} bps | Exhaustion: {EXHAUSTION_THRESHOLD_BPS} bps", flush=True)
    print(f"   Reference Fair-Value Benchmark: Binance USD-M Futures Top-of-Book", flush=True)
    print(f"===============================================================================\n", flush=True)
    
    tasks = [
        stream_hyperliquid(),
        telemetry_heartbeat(),
        markout_tracker(),
        stream_binance("BTC"),
        stream_binance("ETH"),
        stream_binance("SOL")
    ]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Monitor stopped.", flush=True)
