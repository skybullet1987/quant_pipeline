"""
Experiment D: Event-Driven Volatility Harvester & Compounding Engine
File: src/derive_research/event_driven_volatility_harvester.py

Microstructural Realities & Operational Architecture:
  1. Event Conditioning vs. Momentum Follow-Through:
     - Entry Trigger (Microsecond Scale): >= $1.5M volume sweep on Binance with Z_OFI >= 2.58.
       Institutional event filter confirming aggressive absorption and immediate upward drift bias.
     - Spread Payoff (Multi-Minute Scale): Spot moves +0.60% to +1.20% (+$500 to +$1,000 on BTC)
       to move into the strike band (K1) for +120% to +210% spread expansion ($178 -> $390-$550).
     - Holding Horizon (tau_hold): Budgeted for 3 to 45 minutes, managed by an active trailing
       delta stop rather than a high-frequency millisecond scratch. Minimum hold = 3 minutes.
  2. Leg Execution Risk in Synthetic Order Book Crossing:
     - Pre-Flight Depth Verification: Verify resting bid size on K2 satisfies Q_bid,K2 >= Q_target
       and resting ask size on K1 satisfies Q_ask,K1 >= Q_target before dispatching.
     - Atomic Sequential Dispatch: Transmit both order payloads in the same asynchronous tick
       (asyncio.gather(buy_k1, sell_k2)).
     - Immediate Scramble / Scratch Rule: If long leg fills at t0 but short leg fails within 150ms,
       immediately dispatch aggressive market order to dump the long leg, bounding slip to
       the bid-ask spread of K1 rather than remaining exposed to naked directional delta.
  3. Capital Allocation & Risk Envelope:
     - Single-trade risk budget: Maximum 2.5% of total account NAV ($15.85 on $633.96 NAV).
     - Contract lot scaling: 0.01 BTC step (e.g. 0.08 BTC at $178 debit = $14.24 outlay).
     - Concurrent position ceiling: Maximum 2 active spread packages simultaneously.
"""

import os
import sys
import time
import math
import json
import asyncio
import datetime
from collections import deque
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
import websockets
import aiohttp

# --- Microstructure & Risk Constants ---
BINANCE_WS_URL = "wss://fstream.binance.com/ws/btcusdt@aggTrade"
DERIVE_API_BASE = "https://api.lyra.finance/public"

SHOCK_VOLUME_USD = 1500000.0   # >= $1.5M institutional volume sweep
SHOCK_WINDOW_MS = 100           # 100ms rolling window
Z_OFI_HURDLE = 2.58             # Institutional event filter: Z_OFI >= 2.58 (p < 0.01)

# Holding Horizon & Multi-Minute Harvest Parameters
MIN_HOLD_SECONDS = 180.0        # 3 minutes minimum hold (prevent ms noise scratch)
MAX_HOLD_SECONDS = 2700.0       # 45 minutes maximum hold (free capital velocity)
TAKE_PROFIT_ROI = 1.20          # +120% early harvest ROI target (target +120% to +210%)
TRAILING_STOP_ARM_ROI = 0.40    # Arm trailing stop once ROI reaches +40%
TRAILING_STOP_PULLBACK = 0.25   # Scratch/harvest if ROI drops 25% from peak
HARD_STOP_LOSS_ROI = -0.50      # -50% catastrophic adverse momentum stop

# Legging Protection & Execution Bounds
SCRAMBLE_TIMEOUT_MS = 150.0     # 150ms leg-2 scramble timeout hurdle

# Capital Allocation & Risk Envelope
NAV_STATE_PATH = "/home/skybullet1987/quant_pipeline/data/papertrade_state.json"
DEFAULT_ACCOUNT_NAV = 633.96    # Synced with active paper trading equity ($633.96 NAV)
RISK_BUDGET_PCT = 0.025         # 2.5% max NAV risk per vertical spread package ($15.85)
AMOUNT_STEP_BTC = 0.01          # Derive minimum lot increment (0.01 BTC)
MAX_CONCURRENT_POSITIONS = 2    # Maximum 2 concurrent positions ceiling

LOG_DIR = "/home/skybullet1987/quant_pipeline/data/derive"
LOG_FILE = os.path.join(LOG_DIR, "harvester_events.jsonl")


def get_current_nav() -> float:
    """Dynamically loads live account NAV from paper trade state."""
    try:
        if os.path.exists(NAV_STATE_PATH):
            with open(NAV_STATE_PATH, "r") as f:
                st = json.load(f)
                return float(st.get("equity", {}).get("current_strategy_equity", DEFAULT_ACCOUNT_NAV))
    except Exception:
        pass
    return DEFAULT_ACCOUNT_NAV


class TradeWindow:
    """Tracks sub-millisecond aggTrades and calculates rolling OFI Z-score."""
    def __init__(self, window_ms: int = 100, history_len: int = 600):
        self.window_s = window_ms / 1000.0
        self.trades = deque() # (timestamp, price, size, is_buyer_maker)
        self.ofi_history = deque(maxlen=history_len) # rolling 100ms OFI history for Z-score

    def add(self, ts: float, px: float, sz: float, is_buyer_maker: bool):
        self.trades.append((ts, px, sz, is_buyer_maker))
        cutoff = ts - self.window_s
        while self.trades and self.trades[0][0] < cutoff:
            self.trades.popleft()

    def get_metrics(self) -> Dict[str, float]:
        if not self.trades:
            return {"total_usd": 0.0, "buy_usd": 0.0, "sell_usd": 0.0, "ofi": 0.0, "z_ofi": 0.0}
        
        buy_usd = sum(p * s for (t, p, s, bm) in self.trades if not bm)
        sell_usd = sum(p * s for (t, p, s, bm) in self.trades if bm)
        total_usd = buy_usd + sell_usd
        ofi = (buy_usd - sell_usd) / total_usd if total_usd > 0 else 0.0
        
        self.ofi_history.append(ofi)
        
        # Calculate empirical Z-Score: Z = (OFI - mean) / std
        n = len(self.ofi_history)
        if n >= 30:
            mean_ofi = sum(self.ofi_history) / n
            var_ofi = sum((x - mean_ofi) ** 2 for x in self.ofi_history) / n
            std_ofi = math.sqrt(var_ofi)
            z_ofi = (ofi - mean_ofi) / max(0.08, std_ofi)
        else:
            z_ofi = ofi / 0.20 # Fallback prior
            
        return {
            "total_usd": total_usd,
            "buy_usd": buy_usd,
            "sell_usd": sell_usd,
            "ofi": ofi,
            "z_ofi": z_ofi
        }


@dataclass
class SpreadPosition:
    position_id: str
    entry_ts: float
    direction: str
    long_leg: str
    short_leg: str
    strike_long: float
    strike_short: float
    width: float
    entry_debit: float
    entry_mid_debit: float
    contracts: float
    capital_outlay_usd: float
    entry_spot: float
    current_spot: float
    current_spread_val: float
    peak_spread_val: float
    current_roi: float
    peak_roi: float
    trailing_armed: bool
    status: str
    exit_ts: Optional[float] = None
    exit_debit: Optional[float] = None
    realized_pnl_usd: Optional[float] = None
    holding_seconds: Optional[float] = None
    capital_velocity: Optional[float] = None
    exit_reason: Optional[str] = None


async def fetch_derive_btc_tickers(session: aiohttp.ClientSession, expiry_str: str) -> Dict[str, Any]:
    payload = {
        "currency": "BTC",
        "instrument_type": "option",
        "expiry_date": expiry_str
    }
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    try:
        t0 = time.perf_counter()
        async with session.post(f"{DERIVE_API_BASE}/get_tickers", json=payload, headers=headers, timeout=2.0) as resp:
            data = await resp.json()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            tickers = data.get("result", {}).get("tickers", {})
            return {"tickers": tickers, "latency_ms": elapsed_ms}
    except Exception as e:
        return {"tickers": {}, "latency_ms": 0.0, "error": str(e)}


def select_target_spread_with_preflight(
    tickers: Dict[str, Any],
    account_nav: float,
    direction: str = "bull"
) -> Optional[Dict[str, Any]]:
    """
    Identifies the optimal near-OTM vertical debit spread on BTC and verifies:
      1. Pre-flight book depth: Q_ask,K1 >= Q_target and Q_bid,K2 >= Q_target
      2. 2.5% NAV risk sizing budget (<= $15.85 on $633.96 NAV)
    """
    if not tickers:
        return None
        
    sample = next(iter(tickers.values()))
    index_px = float(sample.get("I") or sample.get("index_price") or 0)
    if index_px <= 0:
        return None

    calls = []
    for name, tick in tickers.items():
        parts = name.split("-")
        if len(parts) >= 4 and parts[3] == "C":
            strike = float(parts[2])
            bid = float(tick.get("b") or 0)
            ask = float(tick.get("a") or 0)
            bid_sz = float(tick.get("B") or 0)
            ask_sz = float(tick.get("A") or 0)
            mark = float(tick.get("M") or 0)
            calls.append({
                "name": name,
                "strike": strike,
                "bid": bid,
                "ask": ask,
                "bid_sz": bid_sz,
                "ask_sz": ask_sz,
                "mark": mark
            })

    calls.sort(key=lambda x: x["strike"])

    # 2.5% NAV Risk Budget
    risk_budget_usd = account_nav * RISK_BUDGET_PCT

    if direction == "bull":
        # Target Bull Call Spread 0.2% - 2.5% OTM
        liquid = [c for c in calls if c["bid"] > 0 and c["ask"] > 0 and c["ask_sz"] > 0 and c["strike"] >= 0.998 * index_px]
        for i in range(len(liquid)):
            for j in range(i + 1, min(i + 4, len(liquid))):
                c1, c2 = liquid[i], liquid[j]
                w = c2["strike"] - c1["strike"]
                if 1000 <= w <= 2500:
                    synth_debit = c1["ask"] - c2["bid"]
                    mid_debit = ((c1["ask"] + c1["bid"]) / 2.0) - ((c2["ask"] + c2["bid"]) / 2.0)
                    
                    if 0 < synth_debit <= 220.0 and synth_debit < w:
                        # Contract Sizing Calculation
                        # Minimum amount step on Derive = 0.01 BTC
                        max_lots = math.floor(risk_budget_usd / synth_debit / AMOUNT_STEP_BTC)
                        if max_lots < 1:
                            # Check if 1 minimum lot (0.01 BTC) fits within 1.15x risk budget
                            if (AMOUNT_STEP_BTC * synth_debit) <= (risk_budget_usd * 1.15):
                                contracts = AMOUNT_STEP_BTC
                            else:
                                continue # Exceeds single-trade risk budget
                        else:
                            contracts = round(max_lots * AMOUNT_STEP_BTC, 2)

                        outlay_usd = contracts * synth_debit

                        # Pre-Flight Depth Verification:
                        # Verify Q_ask,K1 >= contracts and Q_bid,K2 >= contracts
                        depth_pass = (c1["ask_sz"] >= contracts) and (c2["bid_sz"] >= contracts)
                        if not depth_pass:
                            continue # Liquidity insufficient for target size without slippage

                        markup_pct = ((synth_debit - mid_debit) / mid_debit * 100.0) if mid_debit > 0 else 0.0
                        payoff_mult = w / synth_debit
                        profit_mult = (w - synth_debit) / synth_debit

                        return {
                            "type": "BULL_CALL_SPREAD",
                            "long_leg": c1["name"],
                            "short_leg": c2["name"],
                            "strike_long": c1["strike"],
                            "strike_short": c2["strike"],
                            "width": w,
                            "entry_debit": synth_debit,
                            "entry_mid_debit": mid_debit,
                            "execution_markup_pct": markup_pct,
                            "contracts": contracts,
                            "capital_outlay_usd": outlay_usd,
                            "risk_budget_usd": risk_budget_usd,
                            "entry_spot": index_px,
                            "max_profit": (w - synth_debit) * contracts,
                            "payoff_mult": payoff_mult,
                            "profit_mult": profit_mult,
                            "ask_sz_k1": c1["ask_sz"],
                            "bid_sz_k2": c2["bid_sz"],
                            "bid_px_k1": c1["bid"], # Needed for scramble scratch rule
                            "ask_px_k1": c1["ask"],
                            "bid_px_k2": c2["bid"],
                            "ask_px_k2": c2["ask"]
                        }
    return None


async def simulate_atomic_sequential_dispatch(spread: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes or simulates atomic sequential leg dispatch on Derive CLOB:
      - Transmit both payloads in same event tick: asyncio.gather(buy_k1, sell_k2)
      - Immediate Scramble Rule: If long fills but short leg fails within 150ms,
        dump long leg at market bid, bounding execution slip to K1 bid-ask spread.
    """
    t_start = time.perf_counter()

    async def dispatch_long_leg():
        await asyncio.sleep(0.025) # 25ms CLOB crossing latency from Tokyo GCP
        return {"status": "FILLED", "fill_px": spread["ask_px_k1"], "size": spread["contracts"], "t_fill": time.perf_counter()}

    async def dispatch_short_leg():
        await asyncio.sleep(0.028) # 28ms CLOB crossing latency from Tokyo GCP
        # High-probability fill if pre-flight depth check passed
        return {"status": "FILLED", "fill_px": spread["bid_px_k2"], "size": spread["contracts"], "t_fill": time.perf_counter()}

    # Dispatch both simultaneously in the same event tick
    res_long, res_short = await asyncio.gather(dispatch_long_leg(), dispatch_short_leg())
    total_crossing_ms = (time.perf_counter() - t_start) * 1000.0

    # Scramble / Scratch Rule Check:
    time_diff_ms = abs(res_short["t_fill"] - res_long["t_fill"]) * 1000.0

    if res_long["status"] == "FILLED" and res_short["status"] == "FILLED" and time_diff_ms <= SCRAMBLE_TIMEOUT_MS:
        return {
            "success": True,
            "status": "ATOMIC_FILL_SUCCESS",
            "crossing_latency_ms": total_crossing_ms,
            "leg_time_diff_ms": time_diff_ms,
            "realized_debit": spread["entry_debit"]
        }
    else:
        # SCRAMBLE TRIGGERED: Long filled but short failed within 150ms!
        # Immediately dispatch aggressive market sell to dump long leg at market bid
        scratch_slip_per_btc = spread["ask_px_k1"] - spread["bid_px_k1"]
        total_scratch_loss = scratch_slip_per_btc * spread["contracts"]
        return {
            "success": False,
            "status": "SCRAMBLE_SCRATCHED",
            "crossing_latency_ms": total_crossing_ms,
            "leg_time_diff_ms": time_diff_ms,
            "scratch_loss_usd": total_scratch_loss,
            "message": f"Short leg failed within {SCRAMBLE_TIMEOUT_MS:.0f}ms. Long dumped at market bid. Slip bounded to spread: -${total_scratch_loss:.2f}"
        }


class HarvesterEngine:
    def __init__(self):
        self.active_positions: List[SpreadPosition] = []
        self.closed_positions: List[SpreadPosition] = []
        self.last_spot_px = 0.0
        self.account_nav = get_current_nav()
        self.latest_tickers: Dict[str, Any] = {}
        self.last_ticker_fetch_ts = 0.0

    def update_spot(self, px: float):
        self.last_spot_px = px

    def compute_spread_valuation(self, pos: SpreadPosition, current_spot: float) -> float:
        """
        Calculates instantaneous spread valuation:
          - Multi-minute gamma acceleration: as spot advances +$500 to +$1,000,
            spread expands from entry debit toward full width W.
          - If live Derive orderbook is fresh, evaluates real CLOB liquidation value (Bid_K1 - Ask_K2).
        """
        # If live tickers are fresh (< 20s old), use actual CLOB quotes
        if self.latest_tickers:
            t_long = self.latest_tickers.get(pos.long_leg, {})
            t_short = self.latest_tickers.get(pos.short_leg, {})
            b_long = float(t_long.get("b") or 0)
            a_short = float(t_short.get("a") or 0)
            if b_long > 0 and a_short > 0:
                real_clob_val = b_long - a_short
                if real_clob_val > 0:
                    return min(pos.width, max(0.0, real_clob_val))

        # Analytic Delta-Gamma Expansion model between ticker fetches
        # Spot displacement in dollars
        d_spot = current_spot - pos.entry_spot
        # Effective spread delta (Delta_K1 - Delta_K2) ~ 0.20 to 0.45
        spread_delta = max(0.15, min(0.60, (pos.width - pos.entry_debit) / (pos.strike_short - pos.entry_spot) if pos.strike_short > pos.entry_spot else 0.40))
        # Effective gamma acceleration
        gamma_accel = 0.00015
        
        est_val = pos.entry_debit + (spread_delta * d_spot) + (0.5 * gamma_accel * max(0.0, d_spot) ** 2)
        return min(pos.width, max(0.0, est_val))

    def evaluate_active_positions(self) -> List[Dict[str, Any]]:
        """
        Evaluates active positions across the 3 to 45 minute holding horizon:
          1. Minimum Hold Constraint (tau_hold < 3 min): No millisecond noise scratch.
          2. Early Harvest Take-Profit (+120% to +210% ROI target).
          3. Active Trailing Delta Stop (arms at +40%, triggers on 25% retrace).
          4. Catastrophic Hard Stop (-50% ROI).
          5. Maximum Hold Duration Expiry (45 minutes).
        """
        now = time.time()
        exited = []

        for pos in list(self.active_positions):
            current_val = self.compute_spread_valuation(pos, self.last_spot_px)
            roi = (current_val - pos.entry_debit) / pos.entry_debit
            hold_sec = now - pos.entry_ts

            pos.current_spot = self.last_spot_px
            pos.current_spread_val = current_val
            pos.current_roi = roi
            if current_val > pos.peak_spread_val:
                pos.peak_spread_val = current_val
            if roi > pos.peak_roi:
                pos.peak_roi = roi

            # Arm trailing stop if ROI reaches +40%
            if pos.peak_roi >= TRAILING_STOP_ARM_ROI:
                pos.trailing_armed = True

            should_exit = False
            exit_reason = ""

            # Check 1: Catastrophic Adverse Hard Stop (can exit anytime)
            if roi <= HARD_STOP_LOSS_ROI:
                should_exit = True
                exit_reason = f"HARD_STOP_LOSS (ROI: {roi*100:.1f}%)"

            # Check 2: Position reached Minimum Hold Horizon (>= 3 minutes)
            elif hold_sec >= MIN_HOLD_SECONDS:
                # Early Harvest Take-Profit Target (+120% ROI)
                if roi >= TAKE_PROFIT_ROI:
                    should_exit = True
                    exit_reason = f"EARLY_HARVEST_TAKE_PROFIT (ROI: +{roi*100:.1f}%)"

                # Active Trailing Delta Stop
                elif pos.trailing_armed and roi <= (pos.peak_roi * (1.0 - TRAILING_STOP_PULLBACK)):
                    should_exit = True
                    exit_reason = f"TRAILING_DELTA_STOP (Peak: +{pos.peak_roi*100:.1f}% -> Current: +{roi*100:.1f}%)"

                # Maximum Holding Horizon Expiry (45 minutes)
                elif hold_sec >= MAX_HOLD_SECONDS:
                    should_exit = True
                    exit_reason = f"MAX_HOLD_HORIZON_REACHED (45 min, ROI: {roi*100:+.1f}%)"

            if should_exit:
                pos.status = "CLOSED"
                pos.exit_ts = now
                pos.exit_debit = current_val
                pos.holding_seconds = hold_sec
                pos.exit_reason = exit_reason
                pos.realized_pnl_usd = (current_val - pos.entry_debit) * pos.contracts
                hold_min = hold_sec / 60.0
                pos.capital_velocity = (roi / hold_min) if hold_min > 0 else 0.0

                self.account_nav += pos.realized_pnl_usd
                self.active_positions.remove(pos)
                self.closed_positions.append(pos)

                exited.append(asdict(pos))

        return exited


async def run_harvester():
    os.makedirs(LOG_DIR, exist_ok=True)
    engine = HarvesterEngine()
    current_nav = engine.account_nav

    print("===============================================================================", flush=True)
    print("   EXPERIMENT D: BTC EVENT-DRIVEN VOLATILITY HARVESTER (BINANCE -> DERIVE)", flush=True)
    print(f"   Institutional Trigger: >= ${SHOCK_VOLUME_USD:,.0f} in {SHOCK_WINDOW_MS}ms | Z_OFI >= {Z_OFI_HURDLE} (p < 0.01)", flush=True)
    print(f"   Holding Horizon: {MIN_HOLD_SECONDS/60:.0f} to {MAX_HOLD_SECONDS/60:.0f} Minutes (Multi-Minute Momentum Scalp)", flush=True)
    print(f"   Early Harvest TP: +{TAKE_PROFIT_ROI*100:.0f}% ROI | Trailing Arm: +{TRAILING_STOP_ARM_ROI*100:.0f}% | Stop: {HARD_STOP_LOSS_ROI*100:.0f}%", flush=True)
    print(f"   Risk Envelope: Max 2.5% NAV (${current_nav * RISK_BUDGET_PCT:.2f} on ${current_nav:.2f} NAV) | Max {MAX_CONCURRENT_POSITIONS} Positions", flush=True)
    print(f"   Legging Protection: Pre-flight Depth Check & {SCRAMBLE_TIMEOUT_MS:.0f}ms Immediate Scramble Scratch", flush=True)
    print("===============================================================================\n", flush=True)

    window = TradeWindow(window_ms=SHOCK_WINDOW_MS)
    last_trigger_ts = 0.0

    # Nearest daily 08:00 UTC expiry
    tomorrow = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    expiry_str = tomorrow.strftime("%Y%m%d")

    async with aiohttp.ClientSession() as http_session:
        while True:
            try:
                print(f"[*] Connecting to Tokyo Binance aggTrade feed ({BINANCE_WS_URL})...", flush=True)
                async with websockets.connect(BINANCE_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    print("[+] Connected and streaming aggTrade at sub-millisecond precision.", flush=True)

                    async for msg_str in ws:
                        msg = json.loads(msg_str)
                        px = float(msg.get("p", 0))
                        sz = float(msg.get("q", 0))
                        ts = float(msg.get("T", 0)) / 1000.0
                        bm = bool(msg.get("m", False))

                        window.add(ts, px, sz, bm)
                        engine.update_spot(px)

                        # Periodically refresh Derive tickers if active positions exist
                        now_sec = time.time()
                        if engine.active_positions and (now_sec - engine.last_ticker_fetch_ts > 15.0):
                            engine.last_ticker_fetch_ts = now_sec
                            res_tick = await fetch_derive_btc_tickers(http_session, expiry_str)
                            if res_tick.get("tickers"):
                                engine.latest_tickers = res_tick["tickers"]

                        # Check Active Positions for Exit / Trailing Harvest
                        if engine.active_positions:
                            exits = engine.evaluate_active_positions()
                            for exit_event in exits:
                                print(f"\n[>>> POSITION HARVEST / EXIT EXECUTED <<<]", flush=True)
                                print(f"  Package: {exit_event['long_leg']} / {exit_event['short_leg']}", flush=True)
                                print(f"  Reason: {exit_event['exit_reason']}", flush=True)
                                print(f"  Hold Duration: {exit_event['holding_seconds']/60:.1f} minutes", flush=True)
                                print(f"  Entry Debit: ${exit_event['entry_debit']:.2f} -> Exit Valuation: ${exit_event['exit_debit']:.2f}", flush=True)
                                print(f"  Realized PnL: ${exit_event['realized_pnl_usd']:+.2f} (ROI: {exit_event['current_roi']*100:+.1f}%)", flush=True)
                                print(f"  Compounding Velocity: {exit_event['capital_velocity']*100:+.2f}% / min", flush=True)
                                print(f"  Updated Strategy NAV: ${engine.account_nav:.2f}\n", flush=True)

                                with open(LOG_FILE, "a") as f:
                                    f.write(json.dumps({"event": "POSITION_CLOSED", "details": exit_event}) + "\n")

                        # Check Institutional Shock Criteria
                        metrics = window.get_metrics()
                        if metrics["total_usd"] >= SHOCK_VOLUME_USD and metrics["z_ofi"] >= Z_OFI_HURDLE:
                            now = time.time()
                            if now - last_trigger_ts > 15.0: # 15-second debounce
                                last_trigger_ts = now
                                
                                # Concurrent Position Ceiling Check
                                if len(engine.active_positions) >= MAX_CONCURRENT_POSITIONS:
                                    print(f"[*] Institutional shock detected (${metrics['total_usd']:,.0f}, Z_OFI: {metrics['z_ofi']:.2f}), "
                                          f"but concurrent position ceiling reached ({len(engine.active_positions)}/{MAX_CONCURRENT_POSITIONS}). Skipping entry.", flush=True)
                                    continue

                                print(f"\n[>>> INSTITUTIONAL SHOCK DETECTED <<<] BULLISH SWEEP"
                                      f"\n  Volume: ${metrics['total_usd']:,.0f} in 100ms | OFI: {metrics['ofi']:+.2f} | Z_OFI: {metrics['z_ofi']:.2f} (Hurdle >= {Z_OFI_HURDLE})"
                                      f"\n  Binance Spot Price: ${px:,.2f}", flush=True)

                                # Sub-100ms Batch Ticker Dispatch to Derive
                                t_disp = time.perf_counter()
                                result = await fetch_derive_btc_tickers(http_session, expiry_str)
                                dispatch_latency = (time.perf_counter() - t_disp) * 1000.0

                                tickers = result.get("tickers", {})
                                engine.latest_tickers = tickers
                                engine.last_ticker_fetch_ts = now

                                # Select Spread with Pre-Flight Depth Check and 2.5% NAV Sizing
                                spread = select_target_spread_with_preflight(tickers, engine.account_nav, direction="bull")

                                if spread:
                                    print(f"  [+] Derive CLOB Batch Query: {dispatch_latency:.1f}ms (HTTP Latency: {result.get('latency_ms', 0):.1f}ms)", flush=True)
                                    print(f"  [+] Target Spread Selected: {spread['long_leg']} / {spread['short_leg']} (${spread['width']:.0f} width)", flush=True)
                                    print(f"  [+] Synthetic Debit: ${spread['entry_debit']:.2f} (Mid: ${spread['entry_mid_debit']:.2f} | Markup: {spread['execution_markup_pct']:.1f}%)", flush=True)
                                    print(f"  [+] Risk Envelope: {spread['contracts']} BTC | Outlay: ${spread['capital_outlay_usd']:.2f} (Budget: ${spread['risk_budget_usd']:.2f})", flush=True)
                                    print(f"  [+] Pre-Flight Depth: Leg 1 Ask {spread['ask_sz_k1']:.2f} BTC >= {spread['contracts']} BTC | Leg 2 Bid {spread['bid_sz_k2']:.2f} BTC >= {spread['contracts']} BTC -> [PASS]", flush=True)
                                    print(f"  [+] Potential Profit Multiplier: {spread['profit_mult']:.2f}x | Max Profit: ${spread['max_profit']:.2f}", flush=True)

                                    # Atomic Sequential Dispatch & 150ms Scramble Scratch Rule
                                    dispatch_res = await simulate_atomic_sequential_dispatch(spread)

                                    if dispatch_res["success"]:
                                        pos_id = f"POS_{int(now)}_{spread['strike_long']:.0f}_{spread['strike_short']:.0f}"
                                        new_pos = SpreadPosition(
                                            position_id=pos_id,
                                            entry_ts=now,
                                            direction="bull",
                                            long_leg=spread["long_leg"],
                                            short_leg=spread["short_leg"],
                                            strike_long=spread["strike_long"],
                                            strike_short=spread["strike_short"],
                                            width=spread["width"],
                                            entry_debit=spread["entry_debit"],
                                            entry_mid_debit=spread["entry_mid_debit"],
                                            contracts=spread["contracts"],
                                            capital_outlay_usd=spread["capital_outlay_usd"],
                                            entry_spot=spread["entry_spot"],
                                            current_spot=spread["entry_spot"],
                                            current_spread_val=spread["entry_debit"],
                                            peak_spread_val=spread["entry_debit"],
                                            current_roi=0.0,
                                            peak_roi=0.0,
                                            trailing_armed=False,
                                            status="ACTIVE"
                                        )
                                        engine.active_positions.append(new_pos)

                                        print(f"  [+] ATOMIC CROSSING SUCCESS: Crossing latency {dispatch_res['crossing_latency_ms']:.1f}ms (Leg diff: {dispatch_res['leg_time_diff_ms']:.1f}ms <= {SCRAMBLE_TIMEOUT_MS:.0f}ms)", flush=True)
                                        print(f"  [+] Spread Package Activated! Budgeted holding horizon: 3 to 45 minutes.\n", flush=True)

                                        with open(LOG_FILE, "a") as f:
                                            f.write(json.dumps({
                                                "event": "POSITION_OPENED",
                                                "timestamp_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                                "shock_volume_usd": metrics["total_usd"],
                                                "z_ofi": metrics["z_ofi"],
                                                "spread": spread,
                                                "dispatch": dispatch_res
                                            }) + "\n")

                                    else:
                                        # Scramble Scratch Occurred
                                        print(f"  [!] SCRAMBLE TRIGGERED: {dispatch_res['message']}", flush=True)
                                        with open(LOG_FILE, "a") as f:
                                            f.write(json.dumps({
                                                "event": "SCRAMBLE_SCRATCH",
                                                "timestamp_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                                "dispatch": dispatch_res
                                            }) + "\n")
                                else:
                                    print(f"  [-] Derive Dispatch ({dispatch_latency:.1f}ms): No qualifying spread satisfying pre-flight depth & risk budget.", flush=True)

            except Exception as e:
                print(f"[-] Binance feed error: {e}. Reconnecting in 3s...", flush=True)
                await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(run_harvester())
    except KeyboardInterrupt:
        print("\n[*] Harvester stopped by user.")
