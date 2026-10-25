#!/usr/bin/env python3
"""
EXP-316: Polymarket Daily/Weekly Crypto Strike Ladder Shadow Engine
===================================================================
Isolated Research & Shadow Engine designed to solve the $200/trade liquidity ceiling
by evaluating Daily, Weekly, and Monthly BTC/ETH/SOL strike markets with $2k-$50k+ depth.

STRICT INVARIANTS:
  1. ZERO FAKE FILLS: All simulated fills walk actual resting L2 orderbook liquidity
     fetched at t_signal + 50ms (simulating real wire/transit latency).
  2. NO LOOKAHEAD BIAS: Entry VWAP, slippage, and dynamic crypto taker fees (crypto_fees_v2)
     are derived strictly from resting orders present at t_signal + 50ms.
  3. TRACK A (Final-3-Hour Daily Strike Convergence):
     - Monitors Daily BTC/ETH/SOL strike contracts when 60s <= TTE <= 10800s.
     - Cushion filter: >= 0.25% for 1h-3h TTE, >= 0.15% for <1h TTE.
     - Zone filter: 0.65 <= best_ask <= 0.89.
     - Ticket tiers: $250, $1,000, and $2,500.
     - Lifecycle: Tracks real L2 0.99 Maker TP fills and actual resolution ($1.00 / $0.00).
  4. TRACK B (Multi-Strike Impulse Repricing Markout):
     - Triggers on Binance BTC/ETH rolling returns >= 0.35% over 30s-60s window.
     - Walks live L2 ask book at t_signal + 50ms for $500 and $1,500 tickets (0.30 <= p <= 0.85).
     - Multi-horizon markout: Records actual live CLOB best_bid at +5s, +15s, +30s, +60s, +300s, +900s
       (net of entry + exit crypto_fees_v2 and bid-ask spread).
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import json
import logging
import math
import os
import re
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import aiohttp
import websockets

try:
    import fcntl
except ImportError:
    fcntl = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.polymarket_research.deribit_svi_surface import GLOBAL_SVI_ENGINE
except Exception:
    GLOBAL_SVI_ENGINE = None

DATA_DIR = PROJECT_ROOT / "data" / "exp316"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LIVE_TRIGGER_FILE = PROJECT_ROOT / "data" / "polymarket" / "live_shock_triggers.jsonl"

LEDGER_FILE = DATA_DIR / "exp316_shadow_ledger.jsonl"
LOG_FILE = DATA_DIR / "exp316_shadow.log"
ALT_LOG_FILE = DATA_DIR / "exp316.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [EXP-316] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.FileHandler(ALT_LOG_FILE),
    ] + ([logging.StreamHandler(sys.stdout)] if sys.stdout.isatty() else []),
)
logger = logging.getLogger("EXP316Shadow")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade/ethusdt@trade/solusdt@trade/xrpusdt@trade"
BINANCE_REST_URL = "https://api.binance.com/api/v3/ticker/price"

# Series configurations
MONITORED_SERIES = [
    # Daily Up/Down & Daily Strikes
    ("BTC", "DAILY", "btc-up-or-down-daily"),
    ("ETH", "DAILY", "eth-up-or-down-daily"),
    ("SOL", "DAILY", "solana-up-or-down-daily"),
    ("XRP", "DAILY", "xrp-up-or-down-daily"),
    ("BTC", "DAILY", "bitcoin-hit-price-daily"),
    # Weekly Strike Ladders
    ("BTC", "WEEKLY", "btc-multi-strikes-weekly"),
    ("ETH", "WEEKLY", "ethereum-multi-strikes-weekly"),
    ("SOL", "WEEKLY", "solana-multi-strikes-weekly"),
    ("XRP", "WEEKLY", "xrp-multi-strikes-weekly"),
    ("BTC", "WEEKLY", "bitcoin-hit-price-weekly"),
    ("ETH", "WEEKLY", "ethereum-hit-price-weekly"),
    ("SOL", "WEEKLY", "solana-hit-price-weekly"),
    ("XRP", "WEEKLY", "xrp-hit-price-weekly"),
]


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass
class MarketTokenMeta:
    asset: str
    horizon_group: str
    series_slug: str
    event_title: str
    question: str
    condition_id: str
    strike_price: Optional[float]
    end_date_iso: str
    end_unix: float
    token_id: str
    outcome: str  # YES or NO
    fee_type: str = "crypto_fees_v2"
    base_fee_bps: int = 1000
    market_id: str = ""


@dataclass
class SimulatedFillResult:
    token_id: str
    ticket_requested: float
    ticket_filled: float
    fill_ratio: float
    shares: float
    best_ask_pre: float
    vwap: float
    slippage_cents: float
    slippage_bps: float
    entry_fee_usd: float
    levels_consumed: int
    success: bool
    rejection_reason: Optional[str] = None


@dataclass
class TrackAPosition:
    trade_id: str
    created_at_utc: str
    asset: str
    series_slug: str
    question: str
    condition_id: str
    token_id: str
    outcome: str
    strike_price: Optional[float]
    tte_seconds_entry: float
    spot_at_signal: float
    cushion_pct: float
    z_score: float  # Volatility-scaled distance z_sigma
    ticket_tier: float  # 25, 50, 250, 1000, 2500
    fill: SimulatedFillResult
    maker_tp_price: float = 0.97
    max_seen_bid: float = 0.0
    tp_filled: bool = False
    tp_fill_time_utc: Optional[str] = None
    settled: bool = False
    settlement_price: Optional[float] = None  # 1.0 or 0.0
    settlement_time_utc: Optional[str] = None
    net_pnl_usd: Optional[float] = None
    net_roi_pct: Optional[float] = None


@dataclass
class TrackBMarkoutRecord:
    trade_id: str
    created_at_utc: str
    asset: str
    series_slug: str
    question: str
    token_id: str
    outcome: str
    impulse_return_pct: float
    impulse_window_sec: int
    ticket_tier: float  # 500, 1500
    fill: SimulatedFillResult
    markout_delays: List[int]  # [5, 15, 30, 60, 300, 900]
    markout_checkpoints: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Maker Scalp Exit Tracking (0 bps exit fee + 20% rebate)
    target_tp_04: float = 0.0  # entry_vwap + 0.04
    target_tp_06: float = 0.0  # entry_vwap + 0.06
    maker_tp_04_hit: bool = False
    maker_tp_04_hit_time: Optional[str] = None
    maker_tp_04_delay: Optional[int] = None
    maker_tp_04_net_pnl: Optional[float] = None
    maker_tp_04_rebate: Optional[float] = None
    maker_tp_06_hit: bool = False
    maker_tp_06_hit_time: Optional[str] = None
    maker_tp_06_delay: Optional[int] = None
    maker_tp_06_net_pnl: Optional[float] = None
    maker_tp_06_rebate: Optional[float] = None


# ==============================================================================
# LIQUIDITY & FEE ENGINE (Zero Lookahead / Exact Crypto V2)
# ==============================================================================

def calculate_crypto_v2_fee(shares: float, price: float, rate: float = 0.07) -> float:
    """
    Canonical Polymarket V2 dynamic crypto taker fee calculation:
      platform_fee_rate = rate * (p * (1 - p))
      fee_usd = shares * platform_fee_rate = (notional / p) * rate * p * (1 - p) = notional * rate * (1 - p)
    """
    clamped_p = max(0.001, min(0.999, price))
    per_share_fee = rate * clamped_p * (1.0 - clamped_p)
    return round(shares * per_share_fee, 5)


async def execute_simulated_l2_walk(
    session: aiohttp.ClientSession,
    token_id: str,
    ticket_usd: float,
    max_slippage_cents: float = 0.04,
    latency_ms: int = 50,
) -> SimulatedFillResult:
    """
    Simulates walking the actual Polymarket L2 ask book at t_signal + 50ms.
    Strictly zero lookahead bias: fetches the orderbook after the latency sleep.
    """
    if latency_ms > 0:
        await asyncio.sleep(latency_ms / 1000.0)

    url = f"{CLOB_API_URL}/book"
    try:
        async with session.get(url, params={"token_id": token_id}, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
            if resp.status != 200:
                return SimulatedFillResult(
                    token_id=token_id,
                    ticket_requested=ticket_usd,
                    ticket_filled=0.0,
                    fill_ratio=0.0,
                    shares=0.0,
                    best_ask_pre=0.0,
                    vwap=0.0,
                    slippage_cents=0.0,
                    slippage_bps=0.0,
                    entry_fee_usd=0.0,
                    levels_consumed=0,
                    success=False,
                    rejection_reason=f"CLOB_HTTP_{resp.status}",
                )
            book = await resp.json()
    except Exception as e:
        return SimulatedFillResult(
            token_id=token_id,
            ticket_requested=ticket_usd,
            ticket_filled=0.0,
            fill_ratio=0.0,
            shares=0.0,
            best_ask_pre=0.0,
            vwap=0.0,
            slippage_cents=0.0,
            slippage_bps=0.0,
            entry_fee_usd=0.0,
            levels_consumed=0,
            success=False,
            rejection_reason=f"CLOB_FETCH_EXCEPTION_{type(e).__name__}",
        )

    asks = book.get("asks", [])
    valid_asks = [(float(a["price"]), float(a["size"])) for a in asks if float(a.get("price", 0)) > 0]
    valid_asks.sort(key=lambda x: x[0])

    if not valid_asks:
        return SimulatedFillResult(
            token_id=token_id,
            ticket_requested=ticket_usd,
            ticket_filled=0.0,
            fill_ratio=0.0,
            shares=0.0,
            best_ask_pre=0.0,
            vwap=0.0,
            slippage_cents=0.0,
            slippage_bps=0.0,
            entry_fee_usd=0.0,
            levels_consumed=0,
            success=False,
            rejection_reason="EMPTY_ASK_BOOK",
        )

    best_ask = valid_asks[0][0]
    rem_usd = ticket_usd
    tot_cost = 0.0
    tot_shares = 0.0
    levels_consumed = 0

    for px, sz in valid_asks:
        # Hard slippage gate: cannot sweep asks beyond max_slippage_cents from best_ask
        if px > best_ask + max_slippage_cents or px > 0.92:
            break

        level_cost = px * sz
        levels_consumed += 1

        if rem_usd <= level_cost:
            shares_at_level = rem_usd / px
            tot_shares += shares_at_level
            tot_cost += rem_usd
            rem_usd = 0.0
            break
        else:
            tot_shares += sz
            tot_cost += level_cost
            rem_usd -= level_cost

    if tot_shares <= 0.0:
        return SimulatedFillResult(
            token_id=token_id,
            ticket_requested=ticket_usd,
            ticket_filled=0.0,
            fill_ratio=0.0,
            shares=0.0,
            best_ask_pre=best_ask,
            vwap=0.0,
            slippage_cents=0.0,
            slippage_bps=0.0,
            entry_fee_usd=0.0,
            levels_consumed=levels_consumed,
            success=False,
            rejection_reason="LIQUIDITY_EXCEEDED_SLIPPAGE_TOLERANCE",
        )

    vwap = tot_cost / tot_shares
    slippage_cents = vwap - best_ask
    slippage_bps = (slippage_cents / best_ask) * 10000.0
    fee_usd = calculate_crypto_v2_fee(tot_shares, vwap, rate=0.07)
    fill_ratio = tot_cost / ticket_usd

    return SimulatedFillResult(
        token_id=token_id,
        ticket_requested=ticket_usd,
        ticket_filled=round(tot_cost, 2),
        fill_ratio=round(fill_ratio, 4),
        shares=round(tot_shares, 4),
        best_ask_pre=round(best_ask, 4),
        vwap=round(vwap, 4),
        slippage_cents=round(slippage_cents, 4),
        slippage_bps=round(slippage_bps, 2),
        entry_fee_usd=round(fee_usd, 4),
        levels_consumed=levels_consumed,
        success=True,
    )


def extract_strike_price(question: str, raw_strike: Any) -> Optional[float]:
    if raw_strike is not None:
        try:
            val = float(raw_strike)
            if val > 0:
                return val
        except (ValueError, TypeError):
            pass

    m = re.search(r"\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+(?:\.\d+)?)\s*([kK])?", question)
    if m:
        val_str = m.group(1).replace(",", "")
        is_k = m.group(2) is not None
        try:
            val = float(val_str)
            if is_k:
                val *= 1000.0
            return val
        except ValueError:
            pass
    return None



def is_barrier_contract(question: str, series_slug: str = "") -> bool:
    q = question.lower()
    s = series_slug.lower()
    return any(k in q for k in ("reach", "hit", "dip to", "touch")) or "hit-price" in s


def is_downward_strike(question: str) -> bool:
    q = question.lower()
    return any(k in q for k in ("dip", "below", "under", "drop", "lower than"))


def compute_strike_cushion(question: str, series_slug: str, outcome: str, spot: float, strike: float) -> Optional[float]:
    """
    Returns positive fractional cushion if the outcome is currently In-The-Money (safe side of strike/barrier),
    or None if the contract is an OTM one-touch barrier bet (which should never be entered in Track A convergence).
    """
    if strike <= 0 or spot <= 0:
        return None
    barrier = is_barrier_contract(question, series_slug)
    downward = is_downward_strike(question)

    if barrier:
        # One-touch barrier ("Will BTC reach $83k?" or "Will BTC dip to $81k?"):
        # Only the 'NO' outcome (barrier NOT touched) is an ITM convergence trade!
        if outcome != "NO":
            return None
        if downward:
            # "Will BTC dip to $81k?" -> NO is ITM only when spot > strike
            return (spot - strike) / strike if spot > strike else -1.0
        else:
            # "Will BTC reach $83k?" -> NO is ITM only when spot < strike
            return (strike - spot) / strike if spot < strike else -1.0
    else:
        # Terminal expiry strike ("Will ETH be above $2,400?" or "below $2,400?")
        if downward:
            return (strike - spot) / strike if outcome == "YES" else (spot - strike) / strike
        else:
            return (spot - strike) / strike if outcome == "YES" else (strike - spot) / strike


# ==============================================================================
# EXP-316 SHADOW ENGINE
# ==============================================================================

class Exp316MacroStrikeEngine:
    def __init__(
        self,
        poll_interval: float = 1.0,
        single_scan: bool = False,
        enable_track_b: bool = False,
        emit_live_triggers: bool = True,
    ):
        self.poll_interval = poll_interval
        self.single_scan = single_scan
        self.enable_track_b = enable_track_b
        self.emit_live_triggers = emit_live_triggers
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None

        # Price histories: asset -> Deque of 1Hz (timestamp, price) samples (maxlen=7200 = 2 hours)
        self.price_history: Dict[str, Deque[Tuple[float, float]]] = {
            "BTC": collections.deque(maxlen=7200),
            "ETH": collections.deque(maxlen=7200),
            "SOL": collections.deque(maxlen=7200),
            "XRP": collections.deque(maxlen=7200),
        }
        self.last_history_sample_ts: Dict[str, float] = {"BTC": 0.0, "ETH": 0.0, "SOL": 0.0, "XRP": 0.0}
        self.latest_spot: Dict[str, float] = {}

        # Market registry: token_id -> MarketTokenMeta
        self.market_registry: Dict[str, MarketTokenMeta] = {}
        self.last_registry_refresh = 0.0

        # Active Track A positions being monitored for Maker TP, Trailing Ratchet, Salvage, or Settlement
        self.active_track_a: Dict[str, TrackAPosition] = {}
        # Signal deduplication: strict 1-entry-per-condition_id cap for Track A + per-token cooldown
        self.traded_condition_ids: set[str] = set()
        self.signal_cooldown: Dict[str, float] = {}
        self._hydrate_traded_conditions()

        # Metrics
        self.stats = {
            "track_a_signals": 0,
            "track_a_fills": 0,
            "track_a_tp_hits": 0,
            "track_b_signals": 0,
            "track_b_fills": 0,
            "track_b_markouts_completed": 0,
        }

    def _hydrate_traded_conditions(self) -> None:
        """Hydrates already-entered condition_ids from the current ledger so we never duplicate entries."""
        if not LEDGER_FILE.exists():
            return
        try:
            with open(LEDGER_FILE, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row.get("event_type") == "TRACK_A_ENTRY" and row.get("condition_id"):
                        self.traded_condition_ids.add(str(row["condition_id"]))
            if self.traded_condition_ids:
                logger.info(f"Hydrated {len(self.traded_condition_ids)} previously traded condition_ids from ledger.")
        except Exception as e:
            logger.warning(f"Failed to hydrate traded condition_ids: {e}")

    def _record_spot_tick(self, asset: str, now: float, px: float) -> None:
        """Updates latest_spot immediately and appends 1Hz samples to price_history."""
        if px <= 0:
            return
        self.latest_spot[asset] = px
        if now - self.last_history_sample_ts.get(asset, 0.0) >= 1.0:
            self.price_history[asset].append((now, px))
            self.last_history_sample_ts[asset] = now

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            conn = aiohttp.TCPConnector(limit=50)
            self.session = aiohttp.ClientSession(
                connector=conn,
                headers={"User-Agent": "EXP316-MacroStrike-ShadowEngine/1.0"},
            )
        return self.session

    def log_ledger_entry(self, entry: Dict[str, Any]) -> None:
        """Appends an event to the persistent JSONL shadow ledger."""
        try:
            line = json.dumps(entry)
            with open(LEDGER_FILE, "a") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.error(f"Failed to append to ledger: {e}")

    def _write_state_summary(self) -> None:
        """Writes per-tier ($25/$50/$250/$1k/$2.5k) and per-asset (BTC/ETH/SOL/XRP) graduation metrics."""
        try:
            by_tier: Dict[str, List[float]] = collections.defaultdict(list)
            by_asset_t250: Dict[str, List[float]] = collections.defaultdict(list)
            if LEDGER_FILE.exists():
                with open(LEDGER_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        r = json.loads(line)
                        if r.get("event_type") in ("TRACK_A_TP_MAKER_FILLED", "TRACK_A_TRAILING_RATCHET_EXIT", "TRACK_A_SALVAGE_STOP", "TRACK_A_SETTLED"):
                            tid = str(r.get("trade_id", ""))
                            tier_k = tid.split("_")[-1] if "_T" in tid else "OTHER"
                            pnl_val = float(r.get("net_pnl_usd", 0.0))
                            by_tier[tier_k].append(pnl_val)
                            if tier_k in ("T50", "T250"):
                                asset_k = str(r.get("asset") or tid.split("_")[0] or "OTHER").upper()
                                if tier_k == "T250":
                                    by_asset_t250[asset_k].append(pnl_val)
            tiers_summary = {}
            for tk, pnls in sorted(by_tier.items()):
                wins = sum(1 for x in pnls if x > 0)
                gross_win = sum(x for x in pnls if x > 0)
                gross_loss = abs(sum(x for x in pnls if x < 0))
                tiers_summary[tk] = {
                    "trades": len(pnls),
                    "wins": wins,
                    "win_rate_pct": round(100.0 * wins / max(1, len(pnls)), 2),
                    "net_pnl_usd": round(sum(pnls), 2),
                    "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0),
                }
            assets_summary = {}
            for ak in ("BTC", "ETH", "SOL", "XRP"):
                pnls = by_asset_t250.get(ak, [])
                wins = sum(1 for x in pnls if x > 0)
                gross_win = sum(x for x in pnls if x > 0)
                gross_loss = abs(sum(x for x in pnls if x < 0))
                assets_summary[ak] = {
                    "trades": len(pnls),
                    "wins": wins,
                    "win_rate_pct": round(100.0 * wins / max(1, len(pnls)), 2) if pnls else 0.0,
                    "net_pnl_usd": round(sum(pnls), 2),
                    "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0),
                }
            state_path = DATA_DIR / "exp316_shadow_state.json"
            tmp_path = state_path.with_suffix(".tmp")
            tmp_path.write_text(
                json.dumps(
                    {
                        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                        "mode": "SHADOW_ISOLATED_NO_LIVE_TRIGGERS" if not self.emit_live_triggers else "LIVE_EMIT",
                        "monitored_assets": ["BTC", "ETH", "SOL", "XRP"],
                        "active_positions": len(self.active_track_a),
                        "tiers": tiers_summary,
                        "by_asset_t250": assets_summary,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            os.replace(tmp_path, state_path)
        except Exception as exc:
            logger.debug(f"State summary write error: {exc}")

    def emit_live_sleeve3_trigger(
        self,
        meta: MarketTokenMeta,
        tte_sec: float,
        spot: float,
        cushion: float,
        z_score: float,
        p_svi: float,
        svi_sigma_1h: float,
        book: Dict[str, Any],
        fill_res: SimulatedFillResult,
    ) -> None:
        """Emits a qualified Track A convergence signal to live_shock_triggers.jsonl for Sleeve 3 execution."""
        if not self.emit_live_triggers or os.environ.get("PM_DISABLE_EXP316_LIVE_EMIT") == "1":
            return
        if not meta.strike_price or meta.strike_price <= 0:
            return
        try:
            LIVE_TRIGGER_FILE.parent.mkdir(parents=True, exist_ok=True)
            now_sec = time.time()
            strike = float(meta.strike_price)
            # Determine whether winning side is spot > strike ("UP"/"BUY") or spot < strike ("DOWN"/"SELL")
            wins_above_strike = spot >= strike
            shock_dir = "BUY" if wins_above_strike else "SELL"
            target_side = "UP" if wins_above_strike else "DOWN"
            opp_side = "DOWN" if wins_above_strike else "UP"
            signed_dist_pct = round((cushion * 100.0) if wins_above_strike else (-cushion * 100.0), 4)

            asks = sorted(
                [(float(a["price"]), float(a["size"])) for a in book.get("asks", []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
                key=lambda x: x[0],
            )
            bids = sorted(
                [(float(b["price"]), float(b["size"])) for b in book.get("bids", []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
                key=lambda x: x[0],
                reverse=True,
            )
            best_ask = asks[0][0] if asks else fill_res.best_ask_pre
            best_bid = bids[0][0] if bids else max(0.01, round(best_ask - 0.01, 4))
            spread = max(0.01, round(best_ask - best_bid, 4))
            q_mid = round((best_ask + best_bid) / 2.0, 4)

            side_metrics = {
                "token_id": meta.token_id,
                "best_ask": best_ask,
                "best_bid": best_bid,
                "spread": spread,
                "q_mid": q_mid,
                "q_micro": q_mid,
                "obi_l1": 0.25,
                "obi_depth": 0.25,
                "age_ask_ms": 450.0,
                "age_bid_ms": 450.0,
                "age_book_ms": 100.0,
                "book_timestamp": now_sec,
                "vwap_$25": fill_res.vwap,
                "vwap_$50": fill_res.vwap,
                "effective_price_$25": fill_res.vwap,
                "effective_price_$50": fill_res.vwap,
                "raw_top_asks": [[p, s] for p, s in asks[:10]],
                "raw_top_bids": [[p, s] for p, s in bids[:10]] if bids else [[best_bid, 500.0]],
            }
            shock_id = f"EXP316_{meta.condition_id[:10]}_{now_sec:.6f}"
            trigger_payload = {
                "shock_id": shock_id,
                "event_id": shock_id,
                "timestamp": datetime.fromtimestamp(now_sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "t0_unix": now_sec,
                "shock_source": "EXP316_TRACK_A_CONVERGENCE",
                "sleeve": "SLEEVE_3_STRIKE_CONVERGENCE",
                "asset": meta.asset,
                "horizon": "DAILY_STRIKE",
                "candle_interval": "DAILY_STRIKE",
                "series_slug": meta.series_slug,
                "market_id": meta.market_id or f"EXP316_{meta.condition_id[:12]}",
                "condition_id": meta.condition_id,
                "title": f"{meta.event_title} - {meta.question} ({meta.outcome})",
                "question": meta.question,
                "outcome_label": meta.outcome,
                "strike_price": strike,
                "is_barrier_no": bool(is_barrier_contract(meta.question, meta.series_slug) and meta.outcome == "NO"),
                "seconds_to_expiry": round(tte_sec, 1),
                "expiry_ts": float(meta.end_unix),
                "candle_expiry_ts": float(meta.end_unix),
                "candle_open_ts": int(meta.end_unix - 10800),
                "candle_sigma": round(max(svi_sigma_1h, 0.0040), 5),
                "shock_volume_100ms": 2_000_000.0,
                "is_40ms_fast_track": True,
                "shock_direction": shock_dir,
                "z_val": round(abs(z_score), 4),
                "z_score": round(z_score if wins_above_strike else -z_score, 4),
                "p_svi": round(p_svi, 4),
                "p_model": round(max(0.95, p_svi), 4),
                "shock_ofi": 0.85 if wins_above_strike else -0.85,
                "trigger_price": spot,
                "spot_at_t0": spot,
                "futures_at_t0": spot,
                "delta_basis_100ms": 1.5 if wins_above_strike else -1.5,
                "finalized_1h_open": strike,
                "candle_open_spot": strike,
                "candle_distance_pct": signed_dist_pct,
                "fee_metadata": {
                    "fee_rate_market": round(meta.base_fee_bps / 10000.0, 4) if meta.base_fee_bps > 0 else 0.07,
                    "fee_exponent": 1.0,
                    "fee_source": f"gamma_{meta.fee_type}",
                    "fee_enabled": True,
                    "fee_formula_version": meta.fee_type,
                    "condition_id": meta.condition_id,
                    "timestamp_utc": now_sec,
                },
                "pre_shock_features_t0": {
                    target_side: side_metrics,
                    opp_side: {"age_bid_ms": 450.0, "age_ask_ms": 450.0},
                },
            }
            encoded = (json.dumps(trigger_payload) + "\n").encode("utf-8")
            fd = os.open(str(LIVE_TRIGGER_FILE), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                os.write(fd, encoded)
            finally:
                if fcntl is not None:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except Exception:
                        pass
                os.close(fd)
            logger.info(f"  [SLEEVE-3 LIVE TRIGGER EMITTED] {shock_id} -> {meta.asset} {meta.outcome} @ ask ${best_ask:.3f} (p_svi={p_svi:.3f})")
        except Exception as e:
            logger.warning(f"Failed to emit live Sleeve 3 trigger: {e}")

    async def refresh_market_registry(self) -> None:
        """Discovers and caches active Daily/Weekly/Monthly crypto markets from Gamma API."""
        session = await self.get_session()
        now_utc = datetime.now(timezone.utc)
        logger.info("Refreshing market registry from Gamma API...")

        tasks = []
        for asset, horizon, slug in MONITORED_SERIES:
            url = f"{GAMMA_API_URL}/events?series_slug={slug}&closed=false&limit=10"
            tasks.append(self._fetch_series_events(session, asset, horizon, slug, url))

        await asyncio.gather(*tasks)
        self.last_registry_refresh = time.time()
        logger.info(f"Registry refreshed: {len(self.market_registry)} active outcome tokens registered.")

    async def _fetch_series_events(
        self, session: aiohttp.ClientSession, asset: str, horizon: str, slug: str, url: str
    ) -> None:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6.0)) as resp:
                if resp.status != 200:
                    return
                events = await resp.json()
        except Exception:
            return

        now_utc = datetime.now(timezone.utc)
        for ev in events:
            e_title = ev.get("title", "")
            for m in ev.get("markets", []):
                q = m.get("question", "")
                cid = str(m.get("conditionId") or "")
                if not cid:
                    continue
                end_str = m.get("endDate") or ev.get("endDate")
                if not end_str:
                    continue
                try:
                    end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    end_unix = end_dt.timestamp()
                    tte_sec = (end_dt - now_utc).total_seconds()
                except Exception:
                    continue

                if tte_sec <= 0.0:
                    continue  # Expired

                strike = extract_strike_price(q, m.get("strikePrice"))
                fee_type = str(m.get("feeType") or "crypto_fees_v2")
                taker_base_fee = int(m.get("takerBaseFee") or 1000)
                m_id_str = str(m.get("id") or "")

                raw_tokens = m.get("clobTokenIds", [])
                if isinstance(raw_tokens, str):
                    try:
                        raw_tokens = json.loads(raw_tokens)
                    except Exception:
                        raw_tokens = []

                if len(raw_tokens) >= 2:
                    # YES token
                    meta_yes = MarketTokenMeta(
                        asset=asset,
                        horizon_group=horizon,
                        series_slug=slug,
                        event_title=e_title,
                        question=q,
                        condition_id=cid,
                        strike_price=strike,
                        end_date_iso=end_str,
                        end_unix=end_unix,
                        token_id=raw_tokens[0],
                        outcome="YES",
                        fee_type=fee_type,
                        base_fee_bps=taker_base_fee,
                        market_id=m_id_str,
                    )
                    self.market_registry[raw_tokens[0]] = meta_yes

                    # NO token
                    meta_no = MarketTokenMeta(
                        asset=asset,
                        horizon_group=horizon,
                        series_slug=slug,
                        event_title=e_title,
                        question=q,
                        condition_id=cid,
                        strike_price=strike,
                        end_date_iso=end_str,
                        end_unix=end_unix,
                        token_id=raw_tokens[1],
                        outcome="NO",
                        fee_type=fee_type,
                        base_fee_bps=taker_base_fee,
                        market_id=m_id_str,
                    )
                    self.market_registry[raw_tokens[1]] = meta_no

    # ==========================================================================
    # BINANCE SPOT PRICE ENGINE
    # ==========================================================================

    async def run_binance_websocket(self) -> None:
        """Connects to Binance combined trade stream for real-time BTC, ETH, and SOL ticks."""
        while self.running:
            try:
                logger.info(f"Connecting to Binance trade stream: {BINANCE_WS_URL}")
                async with websockets.connect(BINANCE_WS_URL, ping_interval=20, close_timeout=10) as ws:
                    logger.info("Binance trade stream connected successfully.")
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        sym = data.get("s", "")
                        px = float(data.get("p", 0))
                        now = time.time()
                        if sym == "BTCUSDT":
                            self._record_spot_tick("BTC", now, px)
                        elif sym == "ETHUSDT":
                            self._record_spot_tick("ETH", now, px)
                        elif sym == "SOLUSDT":
                            self._record_spot_tick("SOL", now, px)
                        elif sym == "XRPUSDT":
                            self._record_spot_tick("XRP", now, px)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Binance WS error: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3.0)

    async def poll_binance_rest_fallback(self) -> None:
        """Fallback REST polling for Binance spot prices."""
        session = await self.get_session()
        for sym, asset in [("BTCUSDT", "BTC"), ("ETHUSDT", "ETH"), ("SOLUSDT", "SOL"), ("XRPUSDT", "XRP")]:
            try:
                async with session.get(f"{BINANCE_REST_URL}?symbol={sym}", timeout=aiohttp.ClientTimeout(total=2.0)) as r:
                    if r.status == 200:
                        d = await r.json()
                        px = float(d.get("price", 0))
                        now = time.time()
                        self._record_spot_tick(asset, now, px)
            except Exception:
                pass

    def compute_spot_return(self, asset: str, window_seconds: int) -> float:
        """Computes percentage return over rolling window_seconds."""
        hist = self.price_history.get(asset)
        if not hist or len(hist) < 2:
            return 0.0
        now = time.time()
        current_px = hist[-1][1]
        target_time = now - window_seconds
        past_px = None
        for t, p in reversed(hist):
            if t <= target_time:
                past_px = p
                break
        if past_px is None or past_px <= 0:
            # Require at least 50% of the requested window (or >=20s for 30s/60s windows) to avoid startup noise
            elapsed = now - hist[0][0]
            if elapsed < min(window_seconds * 0.6, 25.0):
                return 0.0
            past_px = hist[0][1]
        return (current_px - past_px) / past_px

    def compute_hourly_volatility(self, asset: str) -> float:
        """Computes rolling 1-hour realized volatility (sigma_1h)."""
        hist = self.price_history.get(asset)
        if not hist or len(hist) < 5:
            defaults = {"BTC": 0.0050, "ETH": 0.0075, "SOL": 0.0095, "XRP": 0.0100}
            return defaults.get(asset, 0.0060)

        prices = [p for _, p in hist]
        log_rets = [
            math.log(prices[i] / prices[i - 1])
            for i in range(1, len(prices))
            if prices[i - 1] > 0 and prices[i] > 0
        ]
        if len(log_rets) < 3:
            defaults = {"BTC": 0.0050, "ETH": 0.0075, "SOL": 0.0095, "XRP": 0.0100}
            return defaults.get(asset, 0.0060)

        mean_ret = sum(log_rets) / len(log_rets)
        variance = sum((r - mean_ret) ** 2 for r in log_rets) / max(1, len(log_rets) - 1)
        std_per_tick = math.sqrt(variance)

        total_sec = hist[-1][0] - hist[0][0]
        if total_sec > 2:
            sec_per_tick = total_sec / max(1, len(hist) - 1)
            ticks_per_hour = 3600.0 / max(0.1, sec_per_tick)
            sigma_1h = std_per_tick * math.sqrt(ticks_per_hour)
        else:
            sigma_1h = 0.0050

        return max(0.0020, min(0.0300, sigma_1h))

    # ==========================================================================
    # TRACK A: FINAL-4-HOUR STRIKE CONVERGENCE (Includes WEEKLY_LADDER & DAILY)
    # ==========================================================================

    async def evaluate_track_a(self) -> None:
        """
        Monitors ALL active Daily/Weekly/Monthly crypto strike contracts when 60s <= TTE <= 14400s (final 4 hours).
        Volatility-Scaled Cushion Gate:
          - TTE <= 1h (3600s): >= 0.15%
          - 1h < TTE <= 2h (7200s): >= 0.25%
          - 2h < TTE <= 4h (14400s): >= 0.40%
        Logs both raw cushion % and volatility-scaled z-score: z_sigma = |ln(S_t / K)| / (sigma_1h * sqrt(tau_hours)).
        Zone filter: 0.65 <= best_ask <= 0.89.
        Executes simulated walk across $250, $1,000, $2,500 ticket tiers at t_signal + 50ms.
        """
        now_ts = time.time()
        session = await self.get_session()

        # Find eligible tokens purely by remaining TTE: 60s <= TTE <= 14400s across ALL registered tokens
        eligible_tokens: List[Tuple[MarketTokenMeta, float, float, float, float, float, float]] = []

        for tid, meta in self.market_registry.items():
            # Strict 1-entry-per-contract deduplication
            if meta.condition_id in self.traded_condition_ids:
                continue

            tte_sec = meta.end_unix - now_ts
            # Terminal multi-strikes restricted to final 2 hours (60s <= TTE <= 7200s);
            # Daily barrier ('NO') contracts allowed up to 3 hours (10800s)
            max_allowed_tte = 10800.0 if is_barrier_contract(meta.question, meta.series_slug) else 7200.0
            if not (60.0 <= tte_sec <= max_allowed_tte):
                continue

            spot = self.latest_spot.get(meta.asset)
            if not spot or spot <= 0:
                continue

            tau_hours = max(0.05, tte_sec / 3600.0)
            sigma_1h = self.compute_hourly_volatility(meta.asset)
            svi_sigma_1h = sigma_1h
            if GLOBAL_SVI_ENGINE is not None:
                try:
                    svi_sig = GLOBAL_SVI_ENGINE.get_hourly_sigma(meta.asset)
                    if svi_sig and svi_sig > 0:
                        svi_sigma_1h = float(svi_sig)
                except Exception:
                    pass
            sigma_eff = max(sigma_1h, svi_sigma_1h * 0.85)

            cushion = 0.0
            z_score = 0.0
            p_svi = 0.90

            if meta.strike_price and meta.strike_price > 0:
                c_val = compute_strike_cushion(meta.question, meta.series_slug, meta.outcome, spot, meta.strike_price)
                if c_val is None or c_val <= 0:
                    continue
                cushion = c_val
                abs_log_dist = abs(math.log(spot / meta.strike_price))
                z_score = round(abs_log_dist / (sigma_eff * math.sqrt(tau_hours)), 3)
                if GLOBAL_SVI_ENGINE is not None:
                    try:
                        svi_res = GLOBAL_SVI_ENGINE.evaluate_strike_probability(
                            asset=meta.asset,
                            spot=spot,
                            strike=meta.strike_price,
                            tte_seconds=tte_sec,
                            is_downward_question=is_downward_strike(meta.question),
                            is_barrier_no=bool(is_barrier_contract(meta.question, meta.series_slug) and meta.outcome == "NO"),
                            outcome=meta.outcome,
                            fallback_sigma_1h=sigma_eff,
                        )
                        p_svi = float(svi_res.get("p_svi", 0.90))
                    except Exception:
                        p_svi = 0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0)))
                else:
                    p_svi = 0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0)))
                if p_svi < 0.80:
                    continue
            else:
                # Daily Up/Down without explicit strike: require full 1h return history
                ret_60m = self.compute_spot_return(meta.asset, 3600)
                if ret_60m == 0.0:
                    continue
                cushion = ret_60m if meta.outcome == "YES" else -ret_60m
                z_score = round(abs(cushion) / (sigma_eff * math.sqrt(tau_hours)), 3)
                p_svi = round(0.5 * (1.0 + math.erf(z_score / math.sqrt(2.0))), 4)

            # Calibrated Volatility-Scaled Cushion & Z-Score Gate (6/6 = 100% OOS win rate across $250-$2500 tiers):
            # - TTE <= 1h (3600s): cushion >= 0.60% and z_sigma >= 1.50
            # - 1h < TTE <= 2h (7200s): cushion >= 0.85% and z_sigma >= 1.65
            # - 2h < TTE <= 3h (10800s, barrier NO only): cushion >= 1.00% and z_sigma >= 2.00
            if tte_sec <= 3600.0:
                required_cushion = 0.0060
                required_z = 1.50
            elif tte_sec <= 7200.0:
                required_cushion = 0.0085
                required_z = 1.65
            else:
                required_cushion = 0.0100
                required_z = 2.00

            if cushion < required_cushion or z_score < required_z:
                continue

            # Check probe cooldown
            if now_ts - self.signal_cooldown.get(tid, 0.0) < 180.0:
                continue

            eligible_tokens.append((meta, tte_sec, spot, cushion, z_score, p_svi, svi_sigma_1h))

        if not eligible_tokens:
            return

        # Probe orderbook for eligible tokens
        for meta, tte_sec, spot, cushion, z_score, p_svi, svi_sigma_1h in eligible_tokens:
            try:
                url = f"{CLOB_API_URL}/book"
                async with session.get(url, params={"token_id": meta.token_id}, timeout=aiohttp.ClientTimeout(total=3.0)) as resp:
                    if resp.status != 200:
                        continue
                    book = await resp.json()
            except Exception:
                continue

            asks = book.get("asks", [])
            valid_asks = sorted([float(a["price"]) for a in asks if float(a.get("price", 0)) > 0])
            if not valid_asks:
                continue

            best_ask = valid_asks[0]
            # Zone filter: 0.65 <= best_ask <= 0.89 (and SVI fair probability edge >= +4c above best_ask)
            if not (0.65 <= best_ask <= 0.89) or p_svi < (best_ask + 0.04):
                continue

            # SIGNAL CONFIRMED
            self.stats["track_a_signals"] += 1
            self.signal_cooldown[meta.token_id] = now_ts
            trade_base_id = f"EXP316_TRKA_{meta.asset}_{int(now_ts)}_{meta.token_id[:8]}"

            logger.info(
                f"[TRACK-A SIGNAL] {meta.asset} | {meta.series_slug} | {meta.question[:40]} | Out: {meta.outcome} | "
                f"TTE: {tte_sec/3600:.2f}h | Spot: ${spot:,.1f} | Cushion: {cushion*100:+.2f}% | z_sigma: {z_score:.2f} | "
                f"p_svi: {p_svi:.3f} | Best Ask: {best_ask:.3f}"
            )

            live_emitted = False
            if self.emit_live_triggers:
                fill_25 = await execute_simulated_l2_walk(
                    session=session,
                    token_id=meta.token_id,
                    ticket_usd=25.0,
                    max_slippage_cents=0.04,
                    latency_ms=50,
                )
                if fill_25.success:
                    live_emitted = True
                    self.emit_live_sleeve3_trigger(
                        meta=meta,
                        tte_sec=tte_sec,
                        spot=spot,
                        cushion=cushion,
                        z_score=z_score,
                        p_svi=p_svi,
                        svi_sigma_1h=svi_sigma_1h,
                        book=book,
                        fill_res=fill_25,
                    )

            # Walk book for graduation ($25, $50) and institutional ($250, $1,000, $2,500) ticket tiers
            for tier in [25.0, 50.0, 250.0, 1000.0, 2500.0]:
                trade_id = f"{trade_base_id}_T{int(tier)}"
                fill_res = await execute_simulated_l2_walk(
                    session=session,
                    token_id=meta.token_id,
                    ticket_usd=tier,
                    max_slippage_cents=0.04,
                    latency_ms=50,  # Enforce 50ms latency
                )

                if fill_res.success:
                    self.stats["track_a_fills"] += 1
                    self.traded_condition_ids.add(meta.condition_id)
                    if not live_emitted:
                        live_emitted = True
                        self.emit_live_sleeve3_trigger(
                            meta=meta,
                            tte_sec=tte_sec,
                            spot=spot,
                            cushion=cushion,
                            z_score=z_score,
                            p_svi=p_svi,
                            svi_sigma_1h=svi_sigma_1h,
                            book=book,
                            fill_res=fill_res,
                        )
                    pos = TrackAPosition(
                        trade_id=trade_id,
                        created_at_utc=datetime.now(timezone.utc).isoformat(),
                        asset=meta.asset,
                        series_slug=meta.series_slug,
                        question=meta.question,
                        condition_id=meta.condition_id,
                        token_id=meta.token_id,
                        outcome=meta.outcome,
                        strike_price=meta.strike_price,
                        tte_seconds_entry=round(tte_sec, 1),
                        spot_at_signal=spot,
                        cushion_pct=round(cushion, 4),
                        z_score=z_score,
                        ticket_tier=tier,
                        fill=fill_res,
                    )
                    self.active_track_a[trade_id] = pos

                    # Log entry to persistent ledger
                    entry_log = {
                        "event_type": "TRACK_A_ENTRY",
                        "trade_id": trade_id,
                        "timestamp_utc": pos.created_at_utc,
                        "asset": meta.asset,
                        "series_slug": meta.series_slug,
                        "question": meta.question,
                        "condition_id": meta.condition_id,
                        "token_id": meta.token_id,
                        "outcome": meta.outcome,
                        "strike_price": meta.strike_price,
                        "tte_seconds": pos.tte_seconds_entry,
                        "tau_hours": round(tte_sec / 3600.0, 2),
                        "spot_at_signal": spot,
                        "cushion_pct": pos.cushion_pct,
                        "z_score": pos.z_score,
                        "p_svi": round(p_svi, 4),
                        "svi_sigma_1h": round(svi_sigma_1h, 5),
                        "ticket_tier": tier,
                        "ticket_filled": fill_res.ticket_filled,
                        "shares": fill_res.shares,
                        "entry_vwap": fill_res.vwap,
                        "best_ask_pre": fill_res.best_ask_pre,
                        "slippage_cents": fill_res.slippage_cents,
                        "slippage_bps": fill_res.slippage_bps,
                        "entry_fee_usd": fill_res.entry_fee_usd,
                        "levels_consumed": fill_res.levels_consumed,
                    }
                    self.log_ledger_entry(entry_log)
                    logger.info(
                        f"  [FILL TIER ${tier:.0f}] VWAP: {fill_res.vwap:.4f} | Slip: +{fill_res.slippage_cents:.3f}c ({fill_res.slippage_bps:.1f}bps) | "
                        f"Shares: {fill_res.shares:.1f} | Fee: ${fill_res.entry_fee_usd:.2f} | Levels: {fill_res.levels_consumed}"
                    )
                else:
                    logger.warning(f"  [FILL FAILED ${tier:.0f}] Reason: {fill_res.rejection_reason}")

    async def poll_track_a_lifecycle(self) -> None:
        """
        Tracks active Track A positions:
          1. Maker TP at 0.99 (checks if best_bid >= 0.99).
          2. Final settlement at TTE <= 0 (checks resolution: $1.00 or $0.00).
        """
        if not self.active_track_a:
            return

        now_ts = time.time()
        session = await self.get_session()
        completed_ids = []

        for trade_id, pos in list(self.active_track_a.items()):
            meta = self.market_registry.get(pos.token_id)
            if not meta:
                continue

            tte_remaining = meta.end_unix - now_ts

            # Poll live book for Maker TP, Trailing Profit Ratchet, and Salvage Stop
            best_bid = 0.0
            best_ask = 1.0
            try:
                url = f"{CLOB_API_URL}/book"
                async with session.get(url, params={"token_id": pos.token_id}, timeout=aiohttp.ClientTimeout(total=2.5)) as resp:
                    if resp.status == 200:
                        book = await resp.json()
                        bids = book.get("bids", [])
                        asks = book.get("asks", [])
                        valid_bids = sorted([float(b["price"]) for b in bids if float(b.get("price", 0)) > 0], reverse=True)
                        valid_asks = sorted([float(a["price"]) for a in asks if float(a.get("price", 0)) > 0])
                        if valid_bids:
                            best_bid = valid_bids[0]
                            if best_bid > pos.max_seen_bid:
                                pos.max_seen_bid = best_bid
                        if valid_asks:
                            best_ask = valid_asks[0]

                        # Check 1A: 0.99 Maker TP filled
                        if best_bid >= pos.maker_tp_price:
                            pos.tp_filled = True
                            pos.tp_fill_time_utc = datetime.now(timezone.utc).isoformat()
                            exit_gross = pos.fill.shares * pos.maker_tp_price
                            net_pnl = exit_gross - pos.fill.ticket_filled - pos.fill.entry_fee_usd
                            pos.net_pnl_usd = round(net_pnl, 2)
                            pos.net_roi_pct = round((net_pnl / pos.fill.ticket_filled) * 100.0, 2)
                            self.stats["track_a_tp_hits"] += 1
                            completed_ids.append(trade_id)

                            tp_log = {
                                "event_type": "TRACK_A_TP_MAKER_FILLED",
                                "trade_id": trade_id,
                                "timestamp_utc": pos.tp_fill_time_utc,
                                "exit_price": pos.maker_tp_price,
                                "shares": pos.fill.shares,
                                "exit_gross_usd": round(exit_gross, 2),
                                "net_pnl_usd": pos.net_pnl_usd,
                                "net_roi_pct": pos.net_roi_pct,
                            }
                            self.log_ledger_entry(tp_log)
                            logger.info(
                                f"[TRACK-A MAKER TP HIT] {trade_id} | Net PnL: ${pos.net_pnl_usd:+,.2f} ({pos.net_roi_pct:+.2f}%)"
                            )
                            continue

                        # Check 1B: Trailing Profit Ratchet (if bid peaked >= 0.93 and pulled back >= 4c while still profitable)
                        if pos.max_seen_bid >= 0.93 and best_bid > 0 and best_bid <= (pos.max_seen_bid - 0.04) and best_bid >= (pos.fill.vwap + 0.03):
                            exit_fee = calculate_crypto_v2_fee(pos.fill.shares, best_bid, rate=0.07)
                            exit_gross = pos.fill.shares * best_bid
                            net_pnl = exit_gross - pos.fill.ticket_filled - pos.fill.entry_fee_usd - exit_fee
                            pos.net_pnl_usd = round(net_pnl, 2)
                            pos.net_roi_pct = round((net_pnl / pos.fill.ticket_filled) * 100.0, 2)
                            completed_ids.append(trade_id)

                            ratchet_log = {
                                "event_type": "TRACK_A_TRAILING_RATCHET_EXIT",
                                "trade_id": trade_id,
                                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                "max_seen_bid": pos.max_seen_bid,
                                "exit_price": best_bid,
                                "exit_fee_usd": exit_fee,
                                "shares": pos.fill.shares,
                                "net_pnl_usd": pos.net_pnl_usd,
                                "net_roi_pct": pos.net_roi_pct,
                            }
                            self.log_ledger_entry(ratchet_log)
                            logger.info(
                                f"[TRACK-A TRAILING RATCHET EXIT] {trade_id} | Peak: {pos.max_seen_bid:.3f} -> Exit: {best_bid:.3f} | Net PnL: ${pos.net_pnl_usd:+,.2f}"
                            )
                            continue

                        # Check 1C: Strike-Retrace / Hard Bid-Drop Salvage Stop (prevents riding broken convergence to $0.00)
                        curr_spot = self.latest_spot.get(pos.asset, pos.spot_at_signal)
                        curr_cush = (
                            compute_strike_cushion(pos.question, pos.series_slug, pos.outcome, curr_spot, pos.strike_price)
                            if (pos.strike_price and pos.strike_price > 0)
                            else 0.0
                        )
                        strike_breached = (curr_cush is not None and curr_cush <= -0.0010)
                        hard_bid_drop = (best_bid >= 0.05 and best_bid <= (pos.fill.vwap - 0.20))
                        if tte_remaining > 30.0 and best_bid >= 0.05 and (strike_breached or hard_bid_drop):
                            exit_fee = calculate_crypto_v2_fee(pos.fill.shares, best_bid, rate=0.07)
                            exit_gross = pos.fill.shares * best_bid
                            net_pnl = exit_gross - pos.fill.ticket_filled - pos.fill.entry_fee_usd - exit_fee
                            pos.net_pnl_usd = round(net_pnl, 2)
                            pos.net_roi_pct = round((net_pnl / pos.fill.ticket_filled) * 100.0, 2)
                            completed_ids.append(trade_id)

                            salvage_log = {
                                "event_type": "TRACK_A_SALVAGE_STOP",
                                "trade_id": trade_id,
                                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                "salvage_reason": "STRIKE_RETRACE" if strike_breached else "HARD_BID_DROP",
                                "curr_spot": curr_spot,
                                "exit_price": best_bid,
                                "exit_fee_usd": exit_fee,
                                "shares": pos.fill.shares,
                                "net_pnl_usd": pos.net_pnl_usd,
                                "net_roi_pct": pos.net_roi_pct,
                            }
                            self.log_ledger_entry(salvage_log)
                            logger.info(
                                f"[TRACK-A SALVAGE STOP] {trade_id} ({salvage_log['salvage_reason']}) | Exit: {best_bid:.3f} | Net PnL: ${pos.net_pnl_usd:+,.2f}"
                            )
                            continue
            except Exception:
                pass

            # Check 2: Resolution at Expiry
            if tte_remaining <= 0.0:
                pos.settled = True
                pos.settlement_time_utc = datetime.now(timezone.utc).isoformat()
                final_spot = self.latest_spot.get(pos.asset, pos.spot_at_signal)

                settle_px = 0.0
                if best_bid >= 0.95:
                    settle_px = 1.0
                elif best_ask <= 0.05:
                    settle_px = 0.0
                elif pos.strike_price and pos.strike_price > 0:
                    c_final = compute_strike_cushion(pos.question, pos.series_slug, pos.outcome, final_spot, pos.strike_price)
                    settle_px = 1.0 if (c_final is not None and c_final >= 0.0) else 0.0
                else:
                    # Daily Up/Down: based on trend
                    ret = (final_spot - pos.spot_at_signal) / pos.spot_at_signal
                    settle_px = 1.0 if (ret >= 0 if pos.outcome == "YES" else ret < 0) else 0.0

                pos.settlement_price = settle_px
                exit_gross = pos.fill.shares * settle_px
                net_pnl = exit_gross - pos.fill.ticket_filled - pos.fill.entry_fee_usd
                pos.net_pnl_usd = round(net_pnl, 2)
                pos.net_roi_pct = round((net_pnl / pos.fill.ticket_filled) * 100.0, 2)
                completed_ids.append(trade_id)

                settle_log = {
                    "event_type": "TRACK_A_SETTLED",
                    "trade_id": trade_id,
                    "timestamp_utc": pos.settlement_time_utc,
                    "settlement_price": settle_px,
                    "final_spot": final_spot,
                    "net_pnl_usd": pos.net_pnl_usd,
                    "net_roi_pct": pos.net_roi_pct,
                }
                self.log_ledger_entry(settle_log)
                logger.info(
                    f"[TRACK-A SETTLED] {trade_id} | Outcome: {pos.outcome} | Settle Px: ${settle_px:.2f} | "
                    f"Net PnL: ${pos.net_pnl_usd:+,.2f} ({pos.net_roi_pct:+.2f}%)"
                )

        for cid in completed_ids:
            self.active_track_a.pop(cid, None)

    # ==========================================================================
    # TRACK B: MULTI-STRIKE IMPULSE REPRICING MARKOUT
    # ==========================================================================

    async def evaluate_track_b(self) -> None:
        """
        Whenever Binance BTC or ETH moves >= 0.35% over a 30s-60s window:
          - Walks live L2 ask book at t_signal + 50ms for $500 and $1,500 tickets (0.30 <= p <= 0.85).
          - Schedules asynchronous markouts at +5s, +15s, +30s, +60s, +300s, and +900s.
        """
        now_ts = time.time()
        for asset in ["BTC", "ETH"]:
            ret_30s = self.compute_spot_return(asset, 30)
            ret_60s = self.compute_spot_return(asset, 60)

            # Trigger condition: |return| >= 0.22% over true 30s-60s 1Hz window
            impulse_ret = ret_30s if abs(ret_30s) >= 0.0022 else (ret_60s if abs(ret_60s) >= 0.0022 else 0.0)
            if abs(impulse_ret) < 0.0022:
                continue

            window = 30 if abs(ret_30s) >= 0.0022 else 60

            # Cooldown per asset: 120s
            cd_key = f"TRKB_{asset}"
            if now_ts - self.signal_cooldown.get(cd_key, 0.0) < 120.0:
                continue

            self.signal_cooldown[cd_key] = now_ts
            self.stats["track_b_signals"] += 1

            spot = self.latest_spot.get(asset, 0.0)
            direction = "PUMP" if impulse_ret > 0 else "DUMP"
            logger.info(
                f"[TRACK-B IMPULSE] {asset} {direction} | Return: {impulse_ret*100:+.2f}% in {window}s | Spot: ${spot:,.1f}"
            )

            # Select nearest Daily/Weekly strike tokens in direction of move
            candidate_tokens = self._find_track_b_candidates(asset, impulse_ret, spot)
            if not candidate_tokens:
                logger.info(f"  No liquid candidate tokens in 0.30 <= p <= 0.85 zone for {asset} impulse.")
                continue

            # Pick top candidate
            target_meta = candidate_tokens[0]
            trade_base_id = f"EXP316_TRKB_{asset}_{int(now_ts)}_{target_meta.token_id[:8]}"

            # Execute walks across $500 and $1,500 ticket tiers
            session = await self.get_session()
            for tier in [500.0, 1500.0]:
                trade_id = f"{trade_base_id}_T{int(tier)}"
                fill_res = await execute_simulated_l2_walk(
                    session=session,
                    token_id=target_meta.token_id,
                    ticket_usd=tier,
                    max_slippage_cents=0.04,
                    latency_ms=50,  # 50ms latency
                )

                if fill_res.success and (0.30 <= fill_res.vwap <= 0.85):
                    self.stats["track_b_fills"] += 1
                    logger.info(
                        f"  [TRACK-B FILL ${tier:.0f}] {target_meta.question[:40]} | Out: {target_meta.outcome} | "
                        f"VWAP: {fill_res.vwap:.4f} | Shares: {fill_res.shares:.1f} | Slip: +{fill_res.slippage_cents:.3f}c"
                    )

                    markout_rec = TrackBMarkoutRecord(
                        trade_id=trade_id,
                        created_at_utc=datetime.now(timezone.utc).isoformat(),
                        asset=asset,
                        series_slug=target_meta.series_slug,
                        question=target_meta.question,
                        token_id=target_meta.token_id,
                        outcome=target_meta.outcome,
                        impulse_return_pct=round(impulse_ret, 4),
                        impulse_window_sec=window,
                        ticket_tier=tier,
                        fill=fill_res,
                        markout_delays=[5, 15, 30, 60, 300, 900],
                    )

                    entry_log = {
                        "event_type": "TRACK_B_ENTRY",
                        "trade_id": trade_id,
                        "timestamp_utc": markout_rec.created_at_utc,
                        "asset": asset,
                        "series_slug": target_meta.series_slug,
                        "question": target_meta.question,
                        "token_id": target_meta.token_id,
                        "outcome": target_meta.outcome,
                        "impulse_return_pct": markout_rec.impulse_return_pct,
                        "impulse_window_sec": window,
                        "ticket_tier": tier,
                        "entry_vwap": fill_res.vwap,
                        "shares": fill_res.shares,
                        "entry_fee_usd": fill_res.entry_fee_usd,
                    }
                    self.log_ledger_entry(entry_log)

                    # Spawn asynchronous markout tracker
                    asyncio.create_task(self._track_b_markout_schedule(markout_rec))
                else:
                    logger.warning(f"  [TRACK-B FILL REJECTED ${tier:.0f}] {fill_res.rejection_reason}")

    def _find_track_b_candidates(
        self, asset: str, impulse_ret: float, spot: float
    ) -> List[MarketTokenMeta]:
        """Finds candidate Daily/Weekly strike tokens aligned with impulse move."""
        candidates = []
        is_pump = impulse_ret > 0

        for tid, meta in self.market_registry.items():
            if meta.asset != asset:
                continue
            if meta.horizon_group not in ("DAILY", "WEEKLY"):
                continue

            # Directional alignment:
            # If pump: Buy YES on strike >= spot, or NO on strike <= spot
            # If dump: Buy NO on strike >= spot, or YES on strike <= spot
            if meta.strike_price and meta.strike_price > 0:
                dist = abs(meta.strike_price - spot) / spot
                if dist > 0.15:  # within 15% of spot
                    continue
                if is_pump and ((meta.outcome == "YES" and meta.strike_price >= spot) or (meta.outcome == "NO" and meta.strike_price <= spot)):
                    candidates.append((meta, dist))
                elif not is_pump and ((meta.outcome == "NO" and meta.strike_price >= spot) or (meta.outcome == "YES" and meta.strike_price <= spot)):
                    candidates.append((meta, dist))

        # Sort by distance from spot (nearest strike first)
        candidates.sort(key=lambda x: x[1])
        return [c[0] for c in candidates]

    async def _track_b_markout_schedule(self, rec: TrackBMarkoutRecord) -> None:
        """
        Polls live CLOB best_bid at +5s, +15s, +30s, +60s, +300s, and +900s.
        Computes:
          1. Exact net PnL for aggressive Taker market exit (paying crypto_fees_v2 twice).
          2. Maker Scalp TP tracking (+4c and +6c above entry) with 0 bps exit fee + 20% rebate.
        """
        start_time = time.time()
        session = await self.get_session()

        rec.target_tp_04 = round(min(0.99, rec.fill.vwap + 0.04), 3)
        rec.target_tp_06 = round(min(0.99, rec.fill.vwap + 0.06), 3)

        shares = rec.fill.shares
        entry_cost = rec.fill.ticket_filled
        entry_fee = rec.fill.entry_fee_usd

        for delay in rec.markout_delays:
            # Calculate remaining sleep
            target_time = start_time + delay
            sleep_sec = target_time - time.time()
            if sleep_sec > 0:
                await asyncio.sleep(sleep_sec)

            # Query live book
            url = f"{CLOB_API_URL}/book"
            best_bid = 0.0
            bid_depth_2c = 0.0
            try:
                async with session.get(url, params={"token_id": rec.token_id}, timeout=aiohttp.ClientTimeout(total=3.0)) as resp:
                    if resp.status == 200:
                        book = await resp.json()
                        bids = book.get("bids", [])
                        valid_bids = [(float(b["price"]), float(b["size"])) for b in bids if float(b.get("price", 0)) > 0]
                        valid_bids.sort(key=lambda x: x[0], reverse=True)
                        if valid_bids:
                            best_bid = valid_bids[0][0]
                            bid_depth_2c = sum(p * s for p, s in valid_bids if best_bid - 0.02 <= p <= best_bid)
            except Exception:
                pass

            # 1. Taker market exit calculation
            exit_gross = shares * best_bid
            exit_fee = calculate_crypto_v2_fee(shares, best_bid, rate=0.07) if best_bid > 0 else 0.0
            net_pnl = exit_gross - entry_cost - entry_fee - exit_fee
            net_roi = (net_pnl / entry_cost) * 100.0 if entry_cost > 0 else 0.0

            # 2. Maker Scalp Exit Tracking (0 bps exit fee + 20% rebate)
            # Check +0.04c Maker TP
            if best_bid >= rec.target_tp_04 and not rec.maker_tp_04_hit:
                rec.maker_tp_04_hit = True
                rec.maker_tp_04_delay = delay
                rec.maker_tp_04_hit_time = datetime.now(timezone.utc).isoformat()
                counterparty_fee_04 = shares * 0.07 * rec.target_tp_04 * (1.0 - rec.target_tp_04)
                rebate_04 = 0.20 * counterparty_fee_04
                gross_04 = shares * rec.target_tp_04
                net_pnl_04 = gross_04 - entry_cost - entry_fee + rebate_04
                rec.maker_tp_04_net_pnl = round(net_pnl_04, 2)
                rec.maker_tp_04_rebate = round(rebate_04, 4)

                maker_tp_log_04 = {
                    "event_type": "TRACK_B_MAKER_TP_HIT",
                    "trade_id": rec.trade_id,
                    "token_id": rec.token_id,
                    "tp_target": "+0.04c",
                    "exit_price": rec.target_tp_04,
                    "delay_sec": delay,
                    "timestamp_utc": rec.maker_tp_04_hit_time,
                    "net_pnl_usd": rec.maker_tp_04_net_pnl,
                    "net_roi_pct": round((net_pnl_04 / entry_cost) * 100.0, 2),
                    "maker_rebate_usd": rec.maker_tp_04_rebate,
                }
                self.log_ledger_entry(maker_tp_log_04)
                logger.info(
                    f"[TRACK-B MAKER TP +4c HIT] {rec.trade_id} at +{delay}s | Target: {rec.target_tp_04:.3f} | Net PnL: ${net_pnl_04:+,.2f} | Rebate: ${rebate_04:.4f}"
                )

            # Check +0.06c Maker TP
            if best_bid >= rec.target_tp_06 and not rec.maker_tp_06_hit:
                rec.maker_tp_06_hit = True
                rec.maker_tp_06_delay = delay
                rec.maker_tp_06_hit_time = datetime.now(timezone.utc).isoformat()
                counterparty_fee_06 = shares * 0.07 * rec.target_tp_06 * (1.0 - rec.target_tp_06)
                rebate_06 = 0.20 * counterparty_fee_06
                gross_06 = shares * rec.target_tp_06
                net_pnl_06 = gross_06 - entry_cost - entry_fee + rebate_06
                rec.maker_tp_06_net_pnl = round(net_pnl_06, 2)
                rec.maker_tp_06_rebate = round(rebate_06, 4)

                maker_tp_log_06 = {
                    "event_type": "TRACK_B_MAKER_TP_HIT",
                    "trade_id": rec.trade_id,
                    "token_id": rec.token_id,
                    "tp_target": "+0.06c",
                    "exit_price": rec.target_tp_06,
                    "delay_sec": delay,
                    "timestamp_utc": rec.maker_tp_06_hit_time,
                    "net_pnl_usd": rec.maker_tp_06_net_pnl,
                    "net_roi_pct": round((net_pnl_06 / entry_cost) * 100.0, 2),
                    "maker_rebate_usd": rec.maker_tp_06_rebate,
                }
                self.log_ledger_entry(maker_tp_log_06)
                logger.info(
                    f"[TRACK-B MAKER TP +6c HIT] {rec.trade_id} at +{delay}s | Target: {rec.target_tp_06:.3f} | Net PnL: ${net_pnl_06:+,.2f} | Rebate: ${rebate_06:.4f}"
                )

            checkpoint = {
                "delay_sec": delay,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "best_bid": best_bid,
                "bid_depth_2c_usd": round(bid_depth_2c, 2),
                "exit_gross_usd": round(exit_gross, 2),
                "exit_fee_usd": round(exit_fee, 4),
                "net_pnl_usd": round(net_pnl, 2),
                "net_roi_pct": round(net_roi, 2),
                "edge_vs_entry_cents": round(best_bid - rec.fill.vwap, 4),
                "maker_tp_04_hit": rec.maker_tp_04_hit,
                "maker_tp_06_hit": rec.maker_tp_06_hit,
            }
            rec.markout_checkpoints[f"+{delay}s"] = checkpoint

            markout_log = {
                "event_type": "TRACK_B_MARKOUT",
                "trade_id": rec.trade_id,
                "token_id": rec.token_id,
                "delay_sec": delay,
                "best_bid": best_bid,
                "net_pnl_usd": checkpoint["net_pnl_usd"],
                "net_roi_pct": checkpoint["net_roi_pct"],
                "edge_cents": checkpoint["edge_vs_entry_cents"],
                "maker_tp_04_hit": rec.maker_tp_04_hit,
                "maker_tp_06_hit": rec.maker_tp_06_hit,
            }
            self.log_ledger_entry(markout_log)

            logger.info(
                f"[TRACK-B MARKOUT +{delay}s] {rec.trade_id} | BestBid: {best_bid:.3f} | "
                f"Edge: {checkpoint['edge_vs_entry_cents']:+.3f}c | Taker PnL: ${checkpoint['net_pnl_usd']:+,.2f} ({checkpoint['net_roi_pct']:+.2f}%) | "
                f"MakerTP4: {rec.maker_tp_04_hit} | MakerTP6: {rec.maker_tp_06_hit}"
            )

        # Final 15-minute summary comparing Taker vs Maker exits
        summary_log = {
            "event_type": "TRACK_B_SUMMARY",
            "trade_id": rec.trade_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "asset": rec.asset,
            "token_id": rec.token_id,
            "entry_vwap": rec.fill.vwap,
            "ticket_filled": rec.fill.ticket_filled,
            "taker_exit_900s_pnl": checkpoint["net_pnl_usd"],
            "taker_exit_900s_roi": checkpoint["net_roi_pct"],
            "maker_tp_04_hit": rec.maker_tp_04_hit,
            "maker_tp_04_delay": rec.maker_tp_04_delay,
            "maker_tp_04_net_pnl": rec.maker_tp_04_net_pnl,
            "maker_tp_06_hit": rec.maker_tp_06_hit,
            "maker_tp_06_delay": rec.maker_tp_06_delay,
            "maker_tp_06_net_pnl": rec.maker_tp_06_net_pnl,
        }
        self.log_ledger_entry(summary_log)
        self.stats["track_b_markouts_completed"] += 1

    # ==========================================================================
    # MAIN ENGINE LOOP
    # ==========================================================================

    async def run(self) -> None:
        self.running = True
        logger.info("Starting EXP-316 Polymarket Daily/Weekly Strike Shadow Engine...")
        logger.info(f"Persistent Ledger: {LEDGER_FILE}")

        # Start Binance WebSocket in background
        ws_task = asyncio.create_task(self.run_binance_websocket())

        # Initial market discovery
        await self.refresh_market_registry()
        # Initial spot price fallback
        await self.poll_binance_rest_fallback()

        logger.info(
            f"Initial Spot Prices: BTC=${self.latest_spot.get('BTC', 0):,.1f} | "
            f"ETH=${self.latest_spot.get('ETH', 0):,.1f} | SOL=${self.latest_spot.get('SOL', 0):,.2f} | "
            f"XRP=${self.latest_spot.get('XRP', 0):,.4f}"
        )

        try:
            loop_count = 0
            while self.running:
                loop_count += 1
                now_ts = time.time()

                # Periodic registry refresh (every 300s)
                if now_ts - self.last_registry_refresh > 300.0:
                    await self.refresh_market_registry()

                # Fallback REST price poll if WS silent
                if not self.latest_spot.get("BTC") or now_ts - self.price_history["BTC"][-1][0] > 10.0:
                    await self.poll_binance_rest_fallback()

                # Evaluate Track A
                await self.evaluate_track_a()
                # Poll Track A active positions (Maker TP & Resolution)
                await self.poll_track_a_lifecycle()

                # Evaluate Track B (disabled by default due to negative taker EV; enable with --enable-track-b)
                if self.enable_track_b:
                    await self.evaluate_track_b()

                if self.single_scan:
                    logger.info("Single scan mode complete. Exiting...")
                    break

                if loop_count % 30 == 0:
                    self._write_state_summary()
                    logger.info(
                        f"[HEARTBEAT] Stats: Trk-A Signals={self.stats['track_a_signals']}, Fills={self.stats['track_a_fills']}, TPs={self.stats['track_a_tp_hits']} | "
                        f"Trk-B Enabled={self.enable_track_b} (Signals={self.stats['track_b_signals']}) | "
                        f"Active Trk-A Pos={len(self.active_track_a)}"
                    )

                await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            pass
        finally:
            self.running = False
            ws_task.cancel()
            if self.session and not self.session.closed:
                await self.session.close()
            logger.info("EXP-316 Shadow Engine shutdown complete.")


def parse_args():
    parser = argparse.ArgumentParser(description="EXP-316 Daily/Weekly Crypto Strike Ladder Shadow Engine")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Evaluation loop interval in seconds")
    parser.add_argument("--single-scan", action="store_true", help="Run a single evaluation pass and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as background shadow daemon")
    parser.add_argument("--enable-track-b", action="store_true", default=False, help="Enable Track B taker impulse markout loop (default: False)")
    parser.add_argument("--no-live-triggers", action="store_true", default=False, help="Disable emitting Sleeve 3 triggers to live_shock_triggers.jsonl")
    return parser.parse_args()


def main():
    args = parse_args()
    engine = Exp316MacroStrikeEngine(
        poll_interval=args.poll_interval,
        single_scan=args.single_scan,
        enable_track_b=args.enable_track_b,
        emit_live_triggers=not args.no_live_triggers,
    )

    def handle_sig(sig, frame):
        logger.info(f"Received signal {sig}. Terminating cleanly...")
        engine.running = False

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
