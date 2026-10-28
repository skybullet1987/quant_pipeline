#!/usr/bin/env python3
"""
Futures/Spot -> Polymarket Information-Flow Experiment (Route 3 - Data Lab v2.6)
================================================================================
Empirical research pipeline testing information transmission between Binance USD(S)-M Futures,
Binance Spot, and Polymarket 1-Hour BTC Up/Down binary contract order books.

Microstructure, Econometric, and Invariant Foundations:
  1. Dual Binance Antennas (Tokyo Latency):
       - Binance Spot:    wss://stream.binance.com:443/ws/btcusdt@aggTrade (Polymarket Settlement Ref)
       - Binance Futures: wss://fstream.binance.com:443/market/ws/btcusdt@aggTrade (Futures Flow Antenna)
       - Microsecond-resolution timestamps: t_binance_event (E), t_binance_trade (T), t_receive_local.
  2. Strict Causal Information Boundary (t0 Anchor):
       - t0 = exact end of qualifying 100-ms shock window.
       - All predictive features X_t strictly satisfy t_feature <= t0.
       - All impulse-response measurements Delta_q(Delta_t) start strictly after t0 + epsilon.
  3. L2 Order Book Invariants & OBI / Microprice Reconciliation:
       - Top-of-Book OBI: OBI_L1 = (Q_bid1 - Q_ask1) / (Q_bid1 + Q_ask1)
       - Top-of-Book Microprice: q_micro = (ask1 * Q_bid1 + bid1 * Q_ask1) / (Q_bid1 + Q_ask1)
       - Invariant: sign(q_micro - q_mid) MUST match sign(OBI_L1).
       - Runtime Assertion:
           if OBI_L1 > 1e-6: assert q_micro >= q_mid - 1e-6
           if OBI_L1 < -1e-6: assert q_micro <= q_mid + 1e-6
       - Depth OBI: OBI_depth = (sum(Q_bid[:5]) - sum(Q_ask[:5])) / (sum(Q_bid[:5]) + sum(Q_ask[:5]))
       - Book Invariants: best_bid < best_ask (unless locked/crossed), depth_i >= 0, VWAP(C) >= best_ask.
       - Explicit logging of: obi_depth_levels, microprice_formula, book_sequence_id, book_timestamp.
  4. Tripartite Quote Age Decomposition:
       - Age_book = time since any L2 message (snapshot or price_change).
       - Age_bid  = time since best bid changed (price or size).
       - Age_ask  = time since best ask changed (price or size) [stale executable quote metric].
  5. Basis & Delta Basis:
       - basis_t0 = P_futures - P_spot (signed USD and bps)
       - Delta_basis_100ms = basis(t0) - basis(t0 - 100ms)
       - |basis| (magnitude)
  6. Pre-Registered Econometric Models:
       - Model A (Spot):    Y = f(q, X_S, TTE, dist)
       - Model B (Futures): Y = f(q, X_F, TTE, dist)
       - Model C (Joint):   Y = f(q, X_S, X_F, basis, Delta_basis, TTE, dist)
       - Model D (Incr):    Y = f(q, X_S, TTE, dist) + g(X_F | X_S) -> Test H0: beta_{F|S} = 0.
  7. Pre-Registered Lead/Lag Cross-Correlation Grid:
       - Delta in {-500, -250, -100, -50, 0, +50, +100, +250, +500, +1000} ms.
  8. Executable Capacity Surface & Dynamic Fee Parameters:
       - EV(C) = p - VWAP(C) - Fee(C) for C in {1, 5, 20, 50, 100}.
       - fee_rate_market, fee_source, fee_enabled, fee_formula_version recorded per contract.
  9. Strategy Dichotomy:
       - Strategy R3-A: Terminal hold (p_t - q_t - fee) -> Primary scientific experiment.
       - Strategy R3-B: Momentum repricing (q_{t+Delta} - q_t - 2*fee - spread/slip) -> Secondary.
  10. Settlement Ground Truth Verification:
       - Y = 1[Close_1H >= Open_1H] verified directly from finalized Binance Spot 1H candle.
  11. Clustered Statistical Inference:
       - Standard errors clustered at market-hour and shock-episode.
       - Response curve IRF(tau) = E[Delta_q(tau)] bootstrapped at shock-event level.
  12. Operational Boundary:
       - Strictly read-only research pipeline; zero orders or authentication.
"""

import asyncio
import collections
from collections import defaultdict, deque
import copy
import statistics
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

import aiohttp
import numpy as np
import websockets

try:
    import orjson as _orjson  # Fast JSON for the 25ms shared-memory tick bus
except Exception:  # pragma: no cover - graceful fallback
    _orjson = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "polymarket"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TRIGGER_FILE = DATA_DIR / "live_shock_triggers.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BINANCE_REST_URL = "https://api.binance.com"
BINANCE_FUTURES_REST_URL = "https://fapi.binance.com"
COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com"

# v3.3 Zero-REST shared-memory fast tick bus (/dev/shm/pm_fast_tick_{ASSET}.json)
SHM_DIR = Path(os.getenv("PM_FAST_TICK_DIR", "/dev/shm"))
FAST_TICK_THROTTLE_SEC = 0.025
COINBASE_STALE_SEC = 5.0
EXP306_REALTIME_LEDGER = DATA_DIR / "exp306_realtime_boundary_merge.jsonl"


def fast_tick_path(asset: str) -> Path:
    return SHM_DIR / f"pm_fast_tick_{str(asset).upper()}.json"


# v3.4 BTC -> ETH cross-asset lead-state bridge (separate OS processes share BTC shock state via RAM)
LEAD_STATE_MAX_AGE_MS = 1500.0
LEAD_STATE_THROTTLE_SEC = 0.025
SYMPATHY_BTC_MAX_AGE_MS = 500.0
SYMPATHY_BTC_MIN_VOL_USD = 2_250_000.0
SYMPATHY_BTC_MIN_ABS_OFI = 0.85
SYMPATHY_THRESHOLD_MULT = 0.65
SYMPATHY_MIN_AGE_ASK_MS = 300.0

# v3.4 Adaptive session-volume shock threshold
ADAPTIVE_THRESH_MIN_MULT = 0.65
ADAPTIVE_THRESH_MAX_MULT = 1.35
ADAPTIVE_THRESH_VOL_MULT = 18.0
ADAPTIVE_THRESH_WINDOW_SEC = 300
ADAPTIVE_THRESH_MIN_COVERAGE_SEC = 60.0


def lead_state_path(asset: str = "BTC") -> Path:
    return SHM_DIR / f"pm_lead_state_{str(asset).upper()}.json"


def write_lead_state(state: Dict[str, Any], path: Optional[Path] = None) -> bool:
    """Atomic (tmp + os.replace) write of the BTC lead state into RAM. Never raises."""
    path = path or lead_state_path("BTC")
    try:
        payload = _orjson.dumps(state) if _orjson else json.dumps(state).encode("utf-8")
        tmp = path.with_suffix(f".tmp.{os.getpid()}")
        with open(tmp, "wb") as f:
            f.write(payload)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def read_lead_state(path: Optional[Path] = None, max_age_ms: float = LEAD_STATE_MAX_AGE_MS,
                    now_ns: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Reads the BTC lead state; returns None if missing, unparsable or older than max_age_ms (wall clock)."""
    path = path or lead_state_path("BTC")
    try:
        with open(path, "rb") as f:
            raw = f.read()
        st = _orjson.loads(raw) if _orjson else json.loads(raw)
        now_ns = now_ns if now_ns is not None else time.time_ns()
        if (now_ns - int(st.get("ts_ns") or 0)) / 1e6 > max_age_ms:
            return None
        return st
    except Exception:
        return None


def compute_adaptive_shock_threshold(base_threshold: float, avg_100ms_vol_5m: Optional[float]) -> float:
    """effective = clamp(18 * avg_100ms_vol_5m, 0.65 * base, 1.35 * base); base when no baseline."""
    if avg_100ms_vol_5m is None or not math.isfinite(avg_100ms_vol_5m) or avg_100ms_vol_5m <= 0.0:
        return float(base_threshold)
    return min(ADAPTIVE_THRESH_MAX_MULT * base_threshold,
               max(ADAPTIVE_THRESH_MIN_MULT * base_threshold, ADAPTIVE_THRESH_VOL_MULT * avg_100ms_vol_5m))


def evaluate_btc_sympathy(lead: Optional[Dict[str, Any]], eth_flow_dir: str, eth_target_age_ask_ms: Optional[float],
                          now_ns: Optional[int] = None) -> bool:
    """
    BTC-led ETH sympathy: BTC fired a shock within 500ms with vol >= $2.25M and |OFI| >= 0.85 in the
    same direction as ETH flow, and ETH's target Polymarket ask is stale (age_ask_ms >= 300ms).
    """
    if not lead or eth_target_age_ask_ms is None:
        return False
    try:
        now_ns = now_ns if now_ns is not None else time.time_ns()
        shock_ts_ns = int(lead.get("last_shock_ts_ns") or 0)
        if shock_ts_ns <= 0 or (now_ns - shock_ts_ns) / 1e6 > SYMPATHY_BTC_MAX_AGE_MS:
            return False
        if float(lead.get("last_shock_vol_100ms") or 0.0) < SYMPATHY_BTC_MIN_VOL_USD:
            return False
        if abs(float(lead.get("last_shock_ofi_100ms") or 0.0)) < SYMPATHY_BTC_MIN_ABS_OFI:
            return False
        if str(lead.get("last_shock_dir") or "").upper() != str(eth_flow_dir).upper():
            return False
        return float(eth_target_age_ask_ms) >= SYMPATHY_MIN_AGE_ASK_MS
    except Exception:
        return False


def evaluate_realtime_exp306_boundary_and_merge(
    asset: str,
    horizon: str,
    market_id: str,
    up_top: Dict[str, Any],
    down_top: Dict[str, Any],
    spot: float,
    strike_open: float,
    secs_left: float,
    fee_rate: float = 0.07,
    sigma_1h: Optional[float] = None,
    estimated_gas_usd: float = 0.015,
) -> Dict[str, Any]:
    """
    Pillar 5B: Read-only EXP-306 expiry-boundary + complementary merge evaluation.
    - Merge: P_ask(UP) + P_ask(DOWN) + taker fees + gas < 1.00 (>= 1.5c/share net).
    - Boundary: |S - K| / (sigma * sqrt(tau)) >= 3.5 within the final 120s.
    Never places orders; returns a diagnostic record only.
    """
    ask_up = float(up_top.get("best_ask") or 0.0)
    ask_dn = float(down_top.get("best_ask") or 0.0)
    sz_up = float(up_top.get("ask_size_l1") or 0.0)
    sz_dn = float(down_top.get("ask_size_l1") or 0.0)
    merge_net = None
    merge_ok = False
    if 0.0 < ask_up < 1.0 and 0.0 < ask_dn < 1.0 and min(sz_up, sz_dn) > 0:
        fee_up = fee_rate * ask_up * (1.0 - ask_up)
        fee_dn = fee_rate * ask_dn * (1.0 - ask_dn)
        gas_ps = estimated_gas_usd / min(sz_up, sz_dn)
        merge_net = round(1.0 - (ask_up + ask_dn + fee_up + fee_dn + gas_ps), 5)
        merge_ok = merge_net >= 0.015

    if sigma_1h is None:
        sigma_1h = 0.0050 if str(asset).upper() == "BTC" else 0.0068
    boundary_z = None
    boundary_ok = False
    boundary_side = None
    if spot > 0 and strike_open > 0 and 0 < secs_left <= 120.0:
        sig_rem = sigma_1h * math.sqrt(max(secs_left, 1.0) / 3600.0)
        boundary_z = round(abs(spot - strike_open) / (strike_open * max(sig_rem, 1e-9)), 3)
        boundary_side = "UP" if spot >= strike_open else "DOWN"
        boundary_ok = boundary_z >= 3.5

    return {
        "timestamp_unix": time.time(),
        "asset": str(asset).upper(),
        "horizon": horizon,
        "market_id": market_id,
        "secs_left": round(float(secs_left), 1),
        "ask_up": ask_up,
        "ask_down": ask_dn,
        "merge_net_per_share": merge_net,
        "merge_opportunity": merge_ok,
        "boundary_z": boundary_z,
        "boundary_side": boundary_side,
        "boundary_opportunity": boundary_ok,
        "mode": "READ_ONLY_SHADOW",
    }

ASSET_CONFIGS = {
    "BTC": {
        "series_slug": "btc-up-or-down-hourly",
        "binance_symbol": "BTCUSDT",
        "binance_spot_ws": "wss://stream.binance.com:443/ws/btcusdt@aggTrade",
        "binance_futures_ws": "wss://fstream.binance.com:443/market/ws/btcusdt@aggTrade",
        "default_shock_threshold": 1_500_000.0,
        "telemetry_file": DATA_DIR / "polymarket_hourly_telemetry.jsonl",
        "shock_file": DATA_DIR / "shock_responses.jsonl",
        "correlations_file": DATA_DIR / "leadlag_cross_correlations.jsonl",
        "log_file": DATA_DIR / "recorder.log",
        "pid_file": DATA_DIR / "recorder.pid",
    },
    "ETH": {
        "series_slug": "eth-up-or-down-hourly",
        "binance_symbol": "ETHUSDT",
        "binance_spot_ws": "wss://stream.binance.com:443/ws/ethusdt@aggTrade",
        "binance_futures_ws": "wss://fstream.binance.com:443/market/ws/ethusdt@aggTrade",
        "default_shock_threshold": 500_000.0,
        "telemetry_file": DATA_DIR / "polymarket_hourly_telemetry_eth.jsonl",
        "shock_file": DATA_DIR / "shock_responses_eth.jsonl",
        "correlations_file": DATA_DIR / "leadlag_cross_correlations_eth.jsonl",
        "log_file": DATA_DIR / "recorder_eth.log",
        "pid_file": DATA_DIR / "recorder_eth.pid",
    },
    "SOL": {
        "series_slug": "solana-up-or-down-hourly",
        "binance_symbol": "SOLUSDT",
        "binance_spot_ws": "wss://stream.binance.com:443/ws/solusdt@aggTrade",
        "binance_futures_ws": "wss://fstream.binance.com:443/market/ws/solusdt@aggTrade",
        "default_shock_threshold": 250_000.0,
        "telemetry_file": DATA_DIR / "polymarket_hourly_telemetry_sol.jsonl",
        "shock_file": DATA_DIR / "shock_responses_sol.jsonl",
        "correlations_file": DATA_DIR / "leadlag_cross_correlations_sol.jsonl",
        "log_file": DATA_DIR / "recorder_sol.log",
        "pid_file": DATA_DIR / "recorder_sol.pid",
    },
    "XRP": {
        "series_slug": "xrp-up-or-down-hourly",
        "binance_symbol": "XRPUSDT",
        "binance_spot_ws": "wss://stream.binance.com:443/ws/xrpusdt@aggTrade",
        "binance_futures_ws": "wss://fstream.binance.com:443/market/ws/xrpusdt@aggTrade",
        "default_shock_threshold": 100_000.0,
        "telemetry_file": DATA_DIR / "polymarket_hourly_telemetry_xrp.jsonl",
        "shock_file": DATA_DIR / "shock_responses_xrp.jsonl",
        "correlations_file": DATA_DIR / "leadlag_cross_correlations_xrp.jsonl",
        "log_file": DATA_DIR / "recorder_xrp.log",
        "pid_file": DATA_DIR / "recorder_xrp.pid",
    },
    "BNB": {
        "series_slug": "bnb-up-or-down-hourly",
        "binance_symbol": "BNBUSDT",
        "binance_spot_ws": "wss://stream.binance.com:443/ws/bnbusdt@aggTrade",
        "binance_futures_ws": "wss://fstream.binance.com:443/market/ws/bnbusdt@aggTrade",
        "default_shock_threshold": 150_000.0,
        "telemetry_file": DATA_DIR / "polymarket_hourly_telemetry_bnb.jsonl",
        "shock_file": DATA_DIR / "shock_responses_bnb.jsonl",
        "correlations_file": DATA_DIR / "leadlag_cross_correlations_bnb.jsonl",
        "log_file": DATA_DIR / "recorder_bnb.log",
        "pid_file": DATA_DIR / "recorder_bnb.pid",
    },
    "DOGE": {
        "series_slug": "doge-up-or-down-hourly",
        "binance_symbol": "DOGEUSDT",
        "binance_spot_ws": "wss://stream.binance.com:443/ws/dogeusdt@aggTrade",
        "binance_futures_ws": "wss://fstream.binance.com:443/market/ws/dogeusdt@aggTrade",
        "default_shock_threshold": 75_000.0,
        "telemetry_file": DATA_DIR / "polymarket_hourly_telemetry_doge.jsonl",
        "shock_file": DATA_DIR / "shock_responses_doge.jsonl",
        "correlations_file": DATA_DIR / "leadlag_cross_correlations_doge.jsonl",
        "log_file": DATA_DIR / "recorder_doge.log",
        "pid_file": DATA_DIR / "recorder_doge.pid",
    },
    "HYPE": {
        "series_slug": "hype-up-or-down-hourly",
        "binance_symbol": "HYPEUSDT",
        "binance_spot_ws": "",
        "binance_futures_ws": "wss://fstream.binance.com:443/market/ws/hypeusdt@aggTrade",
        "futures_only_ref": True,
        "default_shock_threshold": 75_000.0,
        "telemetry_file": DATA_DIR / "polymarket_hourly_telemetry_hype.jsonl",
        "shock_file": DATA_DIR / "shock_responses_hype.jsonl",
        "correlations_file": DATA_DIR / "leadlag_cross_correlations_hype.jsonl",
        "log_file": DATA_DIR / "recorder_hype.log",
        "pid_file": DATA_DIR / "recorder_hype.pid",
    },
}

logger = logging.getLogger("PolymarketDualFeed1H")

_FAST_IPC_SOCK = None
_FAST_IPC_ADDR = b"\x00polymarket_shock_notify"
_IPC_SEND_FAILURES = 0
_IPC_LAST_WARN_TS = 0.0


def _broadcast_fast_trigger_ipc(data: bytes) -> None:
    """Zero-disk-jitter RAM datagram push to harvester (~15 us on Linux abstract AF_UNIX)."""
    global _FAST_IPC_SOCK, _IPC_SEND_FAILURES, _IPC_LAST_WARN_TS
    if os.name == "nt":
        return
    try:
        import socket
        if _FAST_IPC_SOCK is None:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            s.setblocking(False)
            _FAST_IPC_SOCK = s
        # Resolved per send so `POLYMARKET_IPC_SOCKET_NAME` (same env var the harvester listens on) isolates tests
        ipc_addr = b"\x00" + os.environ.get("POLYMARKET_IPC_SOCKET_NAME", "polymarket_shock_notify").encode("utf-8")
        _FAST_IPC_SOCK.sendto(data, ipc_addr)
    except Exception as e:
        _IPC_SEND_FAILURES += 1
        now_u = time.time()
        if (now_u - _IPC_LAST_WARN_TS) >= 60.0:
            _IPC_LAST_WARN_TS = now_u
            logger.debug(f"[FAST IPC NOTICE] Abstract socket send missed ({_IPC_SEND_FAILURES} total, disk fallback active): {e}")


def _dumps_compact(payload: Dict[str, Any]) -> str:
    """Compact whitespace-free JSON serialization for high-frequency JSONL telemetry."""
    if _orjson is not None:
        return _orjson.dumps(payload).decode("utf-8")
    return json.dumps(payload, separators=(",", ":"))


def _atomic_append_jsonl(path: Path, line_str: str, broadcast_ipc: bool = True) -> None:
    """Atomically appends a single JSONL line across concurrent BTC/ETH recorder processes."""
    if not line_str.endswith("\n"):
        line_str += "\n"
    data = line_str.encode("utf-8")
    if broadcast_ipc and (path == TRIGGER_FILE or str(path).endswith("live_shock_triggers.jsonl")):
        _broadcast_fast_trigger_ipc(data)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o664)
    try:
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
        except Exception:
            pass
        os.write(fd, data)
    finally:
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(fd)


def _dispatch_trigger_fast(path: Path, payload: Dict[str, Any]) -> Tuple[bytes, str]:
    """Serializes via orjson, broadcasts RAM IPC immediately, returns (raw_bytes, line_str)."""
    if _orjson is not None:
        raw = _orjson.dumps(payload) + b"\n"
        line_str = raw.decode("utf-8")
    else:
        line_str = json.dumps(payload) + "\n"
        raw = line_str.encode("utf-8")
    if path == TRIGGER_FILE or str(path).endswith("live_shock_triggers.jsonl"):
        _broadcast_fast_trigger_ipc(raw)
    return raw, line_str


def _persist_trigger_nonblocking(path: Path, line_str: str) -> None:
    """
    Fast non-blocking page-cache append after BOTH 1h & 15m RAM IPC datagrams have already fired.
    Attempts LOCK_EX | LOCK_NB (~15us page-cache write); if another recorder holds the lock,
    offloads blocking flock wait to run_in_executor so the asyncio loop never stalls.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = line_str.encode("utf-8")
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        try:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            fd = -1  # sentinel: already closed; finally must not unlock/close a recycled fd number
            try:
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, _atomic_append_jsonl, path, line_str, False)
                return
            except RuntimeError:
                _atomic_append_jsonl(path, line_str, False)
                return
        except Exception:
            pass
        os.write(fd, data)
    finally:
        if fd >= 0:
            try:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                os.close(fd)
            except OSError:
                pass

def setup_logging(asset: str = "BTC"):
    cfg = ASSET_CONFIGS.get(asset.upper(), ASSET_CONFIGS["BTC"])
    log_file = cfg["log_file"]
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s UTC] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(log_file)] + ([logging.StreamHandler(sys.stdout)] if sys.stdout.isatty() else [])
    )
    global logger
    logger = logging.getLogger(f"PolymarketDualFeed1H-{asset.upper()}")

DEFAULT_FEE_RATE = 0.07  # Documented Polymarket crypto fee parameter
TICKET_CAPACITY_LEVELS = [1.0, 5.0, 20.0, 25.0, 50.0, 100.0, 150.0, 200.0, 250.0]  # USD Notional capacity surface
CORRELATION_LAGS_MS = [-1000, -500, -250, -100, -50, 0, 50, 100, 250, 500, 1000]


def calculate_per_share_taker_fee(price: float, fee_rate: float = DEFAULT_FEE_RATE, fee_exponent: float = 1.0) -> float:
    """
    Computes Polymarket crypto taker fee per share: feeRate * (p * (1 - p)) ** fee_exponent.
    Multiply by the number of shares (not dollar notional) for the USD fee. Makers pay zero fee.
    (Renamed from the recorder's 2-arg calculate_taker_fee to avoid colliding with the executor's
    4-arg calculate_taker_fee(notional_usd, price, fee_rate, fee_exponent) in the unified bundle.)
    """
    p = max(0.001, min(0.999, price))
    return fee_rate * ((p * (1.0 - p)) ** fee_exponent)


class L2OrderBook:
    """
    Maintains continuous in-memory full L2 orderbook with exact microstructure invariants,
    OBI/microprice reconciliation, and tripartite quote age tracking.
    """
    def __init__(self, asset_id: str):
        self.asset_id = str(asset_id)
        self.token_id = str(asset_id)
        self.bids: Dict[float, float] = {}  # px -> sz
        self.asks: Dict[float, float] = {}  # px -> sz
        
        # Tripartite quote age tracking
        self.last_book_update_ts: float = 0.0
        self.last_best_bid_change_ts: float = 0.0
        self.last_best_ask_change_ts: float = 0.0
        
        self.prev_best_bid: Tuple[float, float] = (0.0, 0.0)  # (px, sz)
        self.prev_best_ask: Tuple[float, float] = (1.0, 0.0)  # (px, sz)
        
        self.book_sequence_id: int = 0
        self.microprice_formula = "(best_ask * bid_sz_1 + best_bid * ask_sz_1) / (bid_sz_1 + ask_sz_1)"
        self.obi_depth_levels = 5

        # v3.4 sorted-level cache: deltas only mark the book dirty; sorting happens lazily, at most
        # once per book change, when get_metrics() is called (never on every WebSocket delta).
        self._dirty: bool = True
        self._sorted_bids: List[Tuple[float, float]] = []
        self._sorted_asks: List[Tuple[float, float]] = []

    def _sorted_levels(self) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        if self._dirty:
            self._sorted_bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)
            self._sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])
            self._dirty = False
        return self._sorted_bids, self._sorted_asks

    def _check_top_changes(self, now_ts: float):
        # O(n) best-level detection (no full sort on the delta hot path)
        if self.bids:
            bb = max(self.bids)
            curr_best_bid = (bb, self.bids[bb])
        else:
            curr_best_bid = (0.0, 0.0)
        if self.asks:
            ba = min(self.asks)
            curr_best_ask = (ba, self.asks[ba])
        else:
            curr_best_ask = (1.0, 0.0)
        
        if (
            self.last_best_bid_change_ts == 0.0
            or self.prev_best_bid[0] <= 0.0
            or curr_best_bid[0] < self.prev_best_bid[0]
        ):
            self.last_best_bid_change_ts = now_ts
        self.prev_best_bid = curr_best_bid

        if (
            self.last_best_ask_change_ts == 0.0
            or self.prev_best_ask[0] >= 1.0
            or curr_best_ask[0] > self.prev_best_ask[0]
        ):
            self.last_best_ask_change_ts = now_ts
        self.prev_best_ask = curr_best_ask

    def apply_snapshot(self, bids: List[Dict[str, str]], asks: List[Dict[str, str]]):
        now_ts = time.time()
        self.bids = {float(b["price"]): float(b["size"]) for b in bids if float(b["size"]) > 0}
        self.asks = {float(a["price"]): float(a["size"]) for a in asks if float(a["size"]) > 0}
        self.last_book_update_ts = now_ts
        self.book_sequence_id += 1
        self._dirty = True
        self._check_top_changes(now_ts)

    def apply_price_changes(self, changes: List[Dict[str, str]]):
        now_ts = time.time()
        for c in changes:
            px = float(c["price"])
            sz = float(c["size"])
            side = c.get("side", "").upper()
            if side == "BUY":
                if sz <= 0:
                    self.bids.pop(px, None)
                else:
                    self.bids[px] = sz
            elif side == "SELL":
                if sz <= 0:
                    self.asks.pop(px, None)
                else:
                    self.asks[px] = sz
        self.last_book_update_ts = now_ts
        self.book_sequence_id += 1
        if changes:
            self._dirty = True
        self._check_top_changes(now_ts)

    def top_of_book(self, obs_ts: Optional[float] = None) -> Dict[str, Any]:
        """Lightweight O(1) cached top-of-book snapshot for the 25ms shared-memory tick bus."""
        t_now = obs_ts if obs_ts is not None else time.time()
        sorted_bids, sorted_asks = self._sorted_levels()
        best_bid, bid_sz = sorted_bids[0] if sorted_bids else (0.0, 0.0)
        best_ask, ask_sz = sorted_asks[0] if sorted_asks else (1.0, 0.0)
        denom = bid_sz + ask_sz
        return {
            "best_bid": round(best_bid, 4),
            "best_ask": round(best_ask, 4),
            "bid_size_l1": round(bid_sz, 2),
            "ask_size_l1": round(ask_sz, 2),
            "spread": round(best_ask - best_bid, 4),
            "q_mid": round((best_bid + best_ask) / 2.0, 4),
            "obi_l1": round((bid_sz - ask_sz) / denom, 3) if denom > 0 else 0.0,
            "age_book_ms": round((t_now - self.last_book_update_ts) * 1000.0, 1) if self.last_book_update_ts > 0 else None,
            "age_ask_ms": round((t_now - self.last_best_ask_change_ts) * 1000.0, 1) if self.last_best_ask_change_ts > 0 else None,
            "raw_top_bids": sorted_bids[:15],
            "raw_top_asks": sorted_asks[:15],
        }

    def get_metrics(
        self,
        obs_ts: Optional[float] = None,
        fee_rate: float = DEFAULT_FEE_RATE,
        compact: bool = False,
    ) -> Dict[str, Any]:
        t_now = obs_ts if obs_ts is not None else time.time()
        sorted_bids, sorted_asks = self._sorted_levels()

        best_bid = sorted_bids[0][0] if sorted_bids else 0.0
        bid_sz_1 = sorted_bids[0][1] if sorted_bids else 0.0
        best_ask = sorted_asks[0][0] if sorted_asks else 1.0
        ask_sz_1 = sorted_asks[0][1] if sorted_asks else 0.0

        # Book Consistency Invariants
        is_crossed = False
        if best_bid > 0 and best_ask < 1.0 and best_bid >= best_ask:
            is_crossed = True

        spread = best_ask - best_bid
        q_mid = (best_bid + best_ask) / 2.0

        # Top-of-Book Level 1 OBI & Microprice
        l1_denom = bid_sz_1 + ask_sz_1
        if l1_denom > 0:
            obi_l1 = (bid_sz_1 - ask_sz_1) / l1_denom
            q_micro = (best_bid * ask_sz_1 + best_ask * bid_sz_1) / l1_denom
        else:
            obi_l1 = 0.0
            q_micro = q_mid

        # Runtime Invariant Enforcement: sign(q_micro - q_mid) MUST equal sign(obi_l1)
        if not is_crossed and l1_denom > 0 and spread > 1e-5:
            if (obi_l1 > 1e-4 and q_micro < q_mid - 1e-4) or (obi_l1 < -1e-4 and q_micro > q_mid + 1e-4):
                logger.warning(
                    f"[BOOK INVARIANT NOTICE] OBI_L1={obi_l1:.4f}, q_micro={q_micro:.4f}, q_mid={q_mid:.4f}"
                )

        # Multi-level Depth OBI (Top 5 levels)
        top_bid_vol = sum(sz for _, sz in sorted_bids[:self.obi_depth_levels])
        top_ask_vol = sum(sz for _, sz in sorted_asks[:self.obi_depth_levels])
        depth_denom = top_bid_vol + top_ask_vol
        obi_depth = (top_bid_vol - top_ask_vol) / depth_denom if depth_denom > 0 else 0.0

        taker_fee = calculate_per_share_taker_fee(best_ask, fee_rate)
        executable_hurdle = best_ask + taker_fee

        # Crossing Cost & Execution Surface across research ticket sizes (Points 1 & 8)
        # Note: EV_terminal(C) = p_OOS - EffectivePrice(C). Using q_mid measures CrossingCost(C) = EffectivePrice(C) - q_mid.
        execution_surface: Dict[str, Any] = {}
        cap_levels = (20.0, 25.0, 50.0) if compact else TICKET_CAPACITY_LEVELS
        for notional in cap_levels:
            dollar_spent = 0.0
            shares_bought = 0.0
            total_fees = 0.0
            for px, sz in sorted_asks:
                fill_dollars = min(notional - dollar_spent, px * sz)
                shares = fill_dollars / px
                # Exact fill-level fee per consumed level: C_i * feeRate * p_i * (1 - p_i)
                level_fee = shares * fee_rate * px * (1.0 - px)
                dollar_spent += fill_dollars
                shares_bought += shares
                total_fees += level_fee
                if dollar_spent >= notional - 1e-6:
                    break

            if shares_bought > 0:
                vwap_val = round(dollar_spent / shares_bought, 4)
                effective_px = round((dollar_spent + total_fees) / shares_bought, 4)
                crossing_cost = round(effective_px - q_mid, 4)
                # Enforce VWAP buy sweep invariant: VWAP >= best_ask
                if vwap_val < best_ask - 1e-4:
                    vwap_val = round(best_ask, 4)
                execution_surface[f"vwap_${int(notional)}"] = vwap_val
                if not compact:
                    execution_surface[f"effective_price_${int(notional)}"] = effective_px
                    execution_surface[f"crossing_cost_${int(notional)}"] = crossing_cost
                    execution_surface[f"fill_fees_${int(notional)}"] = round(total_fees, 5)
                elif notional == 50.0:
                    execution_surface["effective_price_$50"] = effective_px
                    execution_surface["fill_fees_$50"] = round(total_fees, 5)
            elif not compact:
                execution_surface[f"vwap_${int(notional)}"] = None
                execution_surface[f"effective_price_${int(notional)}"] = None
                execution_surface[f"crossing_cost_${int(notional)}"] = None
                execution_surface[f"fill_fees_${int(notional)}"] = None

        # Tripartite Quote Ages (in milliseconds)
        age_book_ms = round((t_now - self.last_book_update_ts) * 1000.0, 1) if self.last_book_update_ts > 0 else None
        age_bid_ms = round((t_now - self.last_best_bid_change_ts) * 1000.0, 1) if self.last_best_bid_change_ts > 0 else None
        age_ask_ms = round((t_now - self.last_best_ask_change_ts) * 1000.0, 1) if self.last_best_ask_change_ts > 0 else None

        if compact:
            return {
                "best_bid": round(best_bid, 4),
                "best_ask": round(best_ask, 4),
                "bid_size_l1": round(bid_sz_1, 2),
                "ask_size_l1": round(ask_sz_1, 2),
                "spread": round(spread, 4),
                "q_mid": round(q_mid, 4),
                "q_micro": round(q_micro, 4),
                "obi_l1": round(obi_l1, 3),
                "obi_depth": round(obi_depth, 3),
                "book_sequence_id": self.book_sequence_id,
                "book_timestamp": round(self.last_book_update_ts, 3) if self.last_book_update_ts > 0 else 0.0,
                "is_crossed": is_crossed,
                "age_book_ms": age_book_ms,
                "age_bid_ms": age_bid_ms,
                "age_ask_ms": age_ask_ms,
                "taker_fee": round(taker_fee, 5),
                "executable_hurdle": round(executable_hurdle, 5),
                **execution_surface,
                "raw_top_bids": sorted_bids[:10],
                "raw_top_asks": sorted_asks[:10],
            }

        return {
            "best_bid": round(best_bid, 4),
            "best_ask": round(best_ask, 4),
            "bid_size_l1": round(bid_sz_1, 2),
            "ask_size_l1": round(ask_sz_1, 2),
            "spread": round(spread, 4),
            "q_mid": round(q_mid, 4),
            "q_micro": round(q_micro, 4),
            "obi_l1": round(obi_l1, 3),
            "obi_depth": round(obi_depth, 3),
            "obi_depth_levels": self.obi_depth_levels,
            "microprice_formula": self.microprice_formula,
            "book_sequence_id": self.book_sequence_id,
            "book_timestamp": self.last_book_update_ts,
            "is_crossed": is_crossed,
            "age_book_ms": age_book_ms,
            "age_bid_ms": age_bid_ms,
            "age_ask_ms": age_ask_ms,
            "taker_fee": round(taker_fee, 5),
            "executable_hurdle": round(executable_hurdle, 5),
            **execution_surface,
            "raw_top_bids": sorted_bids[:15],
            "raw_top_asks": sorted_asks[:15]
        }


class PolymarketDualFeed1HRecorder:
    def __init__(self, asset: str = "BTC", shock_threshold: Optional[float] = None):
        self.asset = asset.upper()
        if self.asset not in ASSET_CONFIGS:
            raise ValueError(f"Unsupported asset {self.asset}. Must be one of: {list(ASSET_CONFIGS.keys())}")
        self.cfg = ASSET_CONFIGS[self.asset]
        self.series_slug = self.cfg["series_slug"]
        self.binance_symbol = self.cfg["binance_symbol"]
        self.binance_spot_ws = self.cfg["binance_spot_ws"]
        self.binance_futures_ws = self.cfg["binance_futures_ws"]
        self.futures_only_ref: bool = bool(self.cfg.get("futures_only_ref", False))
        self.shock_threshold_usd = shock_threshold if shock_threshold is not None else self.cfg["default_shock_threshold"]
        
        self.telemetry_file = self.cfg["telemetry_file"]
        self.shock_file = self.cfg["shock_file"]
        self.correlations_file = self.cfg["correlations_file"]
        self.pid_file = self.cfg["pid_file"]
        self.log_file = self.cfg["log_file"]

        self.session: Optional[aiohttp.ClientSession] = None
        self.current_market: Optional[Dict[str, Any]] = None
        self.market_15m: Optional[Dict[str, Any]] = None
        self.market_5m: Optional[Dict[str, Any]] = None
        self.market_4h: Optional[Dict[str, Any]] = None
        self.books: Dict[str, L2OrderBook] = {}

        # Trade queues: (t_local_ns, exchange_event_ms, exchange_trade_ms, notional, is_buyer, px)
        self.spot_trades: collections.deque = collections.deque(maxlen=15000)
        self.futures_trades: collections.deque = collections.deque(maxlen=15000)
        self.basis_history: collections.deque = collections.deque(maxlen=2000)  # (t_mono_ns, basis_bps)

        # Real-time state
        self.spot_price: float = 0.0
        self.futures_price: float = 0.0
        self.basis_usd: float = 0.0
        self.basis_bps: float = 0.0
        self.finalized_1h_open: float = 0.0
        
        # Fee configuration parameters
        self.fee_rate_market: float = DEFAULT_FEE_RATE
        self.fee_exponent: float = 1.0
        self.fee_source: str = "polymarket_crypto_schedule_v1"
        self.fee_enabled: bool = True
        self.fee_formula_version: str = "taker_fee_c_times_rate_times_p_one_minus_p"

        # Clock synchronization and offset estimation (Point 3)
        self.clock_offset_ms: float = 0.0
        self.clock_uncertainty_ms: float = 0.0
        self.last_clock_sync_ts: float = 0.0

        self.last_shock_ts: float = 0.0
        self.last_shock_ts_by_source: Dict[str, float] = defaultdict(float)
        self.last_cross_corr_ts: float = 0.0
        self.active_burst_tasks: Set[asyncio.Task] = set()
        self.running: bool = True
        self.clob_ws_connected: bool = False
        self.last_clob_ws_msg_ts: float = 0.0
        self._last_stale_exch_warn_ts: float = 0.0

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.telemetry_15m_file: Path = DATA_DIR / f"polymarket_15m_telemetry_{self.asset.lower()}.jsonl"
        self.telemetry_5m_file: Path = DATA_DIR / f"polymarket_5m_telemetry_{self.asset.lower()}.jsonl"
        self.telemetry_4h_file: Path = DATA_DIR / f"polymarket_4h_telemetry_{self.asset.lower()}.jsonl"
        self._last_telem_bbo_by_hz: Dict[str, Tuple[float, Tuple[Any, ...]]] = {}
        self._spot_1m_bucket: int = 0
        self._last_1m_spot: float = 0.0
        self._rolling_sigma_1h: float = {
            "BTC": 0.0050,
            "ETH": 0.0068,
            "BNB": 0.0068,
            "SOL": 0.0075,
            "XRP": 0.0080,
            "DOGE": 0.0095,
            "HYPE": 0.0110,
        }.get(self.asset, 0.0068)

        # v3.3 Coinbase composite venue feed (fail-open) + /dev/shm fast tick bus
        self.coinbase_product = f"{self.asset}-USD"
        self.coinbase_spot: float = 0.0
        self.coinbase_spot_ts: float = 0.0
        self.coinbase_history: collections.deque = collections.deque(maxlen=600)  # (t_unix, px)
        self._venue_div_history: collections.deque = collections.deque(maxlen=200)  # causal rolling USDT/USD basis bps
        self._cl_proxy_history: collections.deque = collections.deque(maxlen=1200)  # (t_unix, cl_proxy_px) for 60s USD TWAP
        self.chainlink_last_updated_ts: float = 0.0
        self.fast_tick_file: Path = fast_tick_path(self.asset)
        self._last_fast_tick_write: float = 0.0
        self._fast_tick_enabled: bool = SHM_DIR.is_dir()
        self._last_exp306_eval: float = 0.0

        # v3.4 BTC -> ETH lead-state bridge
        self.lead_state_file: Path = lead_state_path("BTC")
        self._last_lead_state_write: float = 0.0
        self._last_btc_shock: Dict[str, Any] = {}
        self._last_btc_flow_z: float = 0.0

        # v3.4 Adaptive session-volume threshold: 1-second dollar-volume buckets (spot + futures)
        self._vol_buckets: collections.deque = collections.deque(maxlen=ADAPTIVE_THRESH_WINDOW_SEC + 2)  # [sec, usd]
        self._vol_first_sec: Optional[int] = None
        self._adaptive_cache: Tuple[float, float] = (0.0, float(self.shock_threshold_usd))  # (computed_at, value)

    # ------------------------------------------------------------------
    # v3.3 Coinbase composite venue helpers (fail-open when disconnected/stale)
    # ------------------------------------------------------------------
    def get_coinbase_spot(self, now: Optional[float] = None) -> float:
        now = now if now is not None else time.time()
        if self.coinbase_spot > 0 and (now - self.coinbase_spot_ts) <= COINBASE_STALE_SEC:
            return self.coinbase_spot
        return 0.0

    def get_venue_divergence_bps(self, now: Optional[float] = None) -> float:
        """Signed (Binance spot - Coinbase spot) / Coinbase in bps. 0.0 when Coinbase unavailable (fail-open)."""
        cb = self.get_coinbase_spot(now)
        if cb <= 0 or self.spot_price <= 0:
            return 0.0
        return round((self.spot_price - cb) / cb * 10000.0, 2)

    def get_venue_divergence_centered_bps(self, now: Optional[float] = None) -> float:
        """Causal basis-centered venue divergence (subtracts trailing 200-sample rolling median of USDT/USD basis)."""
        raw_div = self.get_venue_divergence_bps(now)
        cb = self.get_coinbase_spot(now)
        if cb <= 0 or self.spot_price <= 0:
            return 0.0
        hist = getattr(self, "_venue_div_history", None)
        if hist and len(hist) >= 10:
            return round(raw_div - statistics.median(hist), 2)
        return raw_div

    def get_chainlink_proxy_spot(self, now: Optional[float] = None) -> float:
        """v3.9.2 True-USD synthetic Chainlink oracle proxy (Coinbase USD + USDT/USD-adjusted Binance midpoint)."""
        now_ts = now if now is not None else time.time()
        cb = self.get_coinbase_spot(now_ts)
        hist_div = getattr(self, "_venue_div_history", None)
        bn_usd = 0.0
        if self.spot_price > 0 and hist_div and len(hist_div) >= 10:
            med_bps = max(-250.0, min(250.0, float(statistics.median(hist_div))))
            bn_usd = self.spot_price / (1.0 + med_bps / 10000.0)
        if cb > 0 and bn_usd > 0:
            cl_px = round(0.5 * (cb + bn_usd), 4)
        elif cb > 0:
            cl_px = round(cb, 4)
        elif bn_usd > 0:
            cl_px = round(bn_usd, 4)
        else:
            return 0.0
        hist = getattr(self, "_cl_proxy_history", None)
        if hist is not None and cl_px > 0:
            if not hist or (now_ts - hist[-1][0]) >= 0.20:
                hist.append((now_ts, cl_px))
            while hist and (now_ts - hist[0][0]) > 65.0:
                hist.popleft()
        return cl_px

    def get_chainlink_twap_60s(self, now: Optional[float] = None) -> float:
        """v3.9 R07: Real-time 60-second rolling USD TWAP mirroring Chainlink's btc-usd-twap-60s-streams."""
        now_ts = now if now is not None else time.time()
        cl_now = self.get_chainlink_proxy_spot(now_ts)
        hist = getattr(self, "_cl_proxy_history", None)
        if not hist:
            return cl_now
        pts = [px for t, px in hist if (now_ts - t) <= 60.0 and px > 0]
        if len(pts) < 2:
            return cl_now
        return round(statistics.mean(pts), 4)

    async def fetch_polygon_chainlink_spot(self) -> float:
        """
        v3.8 Blueprint 3 / v3.9 R07: Lightweight Polygon AggregatorV3 latestRoundData() poller (0xfeaf968c)
        for BTC/USD (0xc907...7F6f) and ETH/USD (0xF968...5945). Rejects rounds > 20s stale so non-TWAP
        point feeds never distort 15m boundary anchors. Strictly fail-open (1.5s timeout).
        """
        agg_map = {
            "BTC": "0xc907E116054Ad103354f2D350FD2514433D57F6f",
            "ETH": "0xF9680D99D6C9589e2a93a78A04A279e509205945",
        }
        addr = agg_map.get(self.asset.upper())
        if not addr:
            return 0.0
        rpc_url = os.environ.get("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")
        try:
            session = await self.get_session()
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [{"to": addr, "data": "0xfeaf968c"}, "latest"],
            }
            async with session.post(rpc_url, json=payload, timeout=1.5) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    hex_str = str(res.get("result") or "")
                    if hex_str.startswith("0x") and len(hex_str) >= 2 + 64 * 4:
                        ans = int(hex_str[2 + 64 : 2 + 128], 16)
                        upd = int(hex_str[2 + 192 : 2 + 256], 16)
                        if ans > 0 and (time.time() - upd) <= 20.0:
                            self.chainlink_last_updated_ts = float(upd)
                            return round(ans / 1e8, 4)
        except Exception as e:
            logger.debug(f"Polygon Chainlink AggregatorV3 fetch skipped ({self.asset}): {e}")
        return 0.0

    def get_coinbase_move_bps(self, window_sec: float = 2.0, now: Optional[float] = None) -> float:
        """Signed Coinbase spot move over the trailing window in bps (0.0 if unavailable)."""
        now = now if now is not None else time.time()
        cb = self.get_coinbase_spot(now)
        if cb <= 0 or not self.coinbase_history:
            return 0.0
        ref = None
        for t, px in self.coinbase_history:
            if now - t <= window_sec:
                ref = px
                break
        if not ref or ref <= 0:
            return 0.0
        return round((cb - ref) / ref * 10000.0, 2)

    async def _coinbase_stream_worker(self):
        """Coinbase spot ticker stream for BTC-USD / ETH-USD. Fail-open: entries are never blocked by its absence."""
        backoff = 2.0
        while self.running:
            try:
                async with websockets.connect(COINBASE_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    await ws.send(json.dumps({
                        "type": "subscribe",
                        "product_ids": [self.coinbase_product],
                        "channels": ["ticker"],
                    }))
                    logger.info(f"[+] Subscribed to Coinbase ticker ({self.coinbase_product}) for composite venue filter.")
                    backoff = 2.0
                    async for msg_str in ws:
                        if not self.running:
                            break
                        data = _orjson.loads(msg_str) if _orjson else json.loads(msg_str)
                        if data.get("type") != "ticker" or data.get("product_id") != self.coinbase_product:
                            continue
                        px = float(data.get("price") or 0.0)
                        if px > 0:
                            now = time.time()
                            self.coinbase_spot = px
                            self.coinbase_spot_ts = now
                            self.coinbase_history.append((now, px))
                            if self.spot_price > 0:
                                self._venue_div_history.append(round((self.spot_price - px) / px * 10000.0, 2))
                            while self.coinbase_history and now - self.coinbase_history[0][0] > 30.0:
                                self.coinbase_history.popleft()
            except Exception as e:
                logger.warning(f"Coinbase feed disconnected ({e}); fail-open, retrying in {backoff:.0f}s...")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 2.0)

    # ------------------------------------------------------------------
    # v3.3 /dev/shm 25ms fast tick bus
    # ------------------------------------------------------------------
    def build_fast_tick_snapshot(self, now: Optional[float] = None) -> Dict[str, Any]:
        now = now if now is not None else time.time()
        snap: Dict[str, Any] = {
            "ts": now,
            "timestamp_unix": now,
            "asset": self.asset,
            "market_id": str(self.current_market["market_id"]) if self.current_market else None,
            "spot": self.spot_price,
            "futures": self.futures_price,
            "spot_price": self.spot_price,
            "futures_price": self.futures_price,
            "coinbase_spot": self.get_coinbase_spot(now),
            "chainlink_proxy_spot": self.get_chainlink_proxy_spot(now),
            "chainlink_twap_60s": self.get_chainlink_twap_60s(now),
            "venue_divergence_bps": self.get_venue_divergence_bps(now),
            "venue_divergence_centered_bps": self.get_venue_divergence_centered_bps(now),
            "coinbase_move_bps_2s": self.get_coinbase_move_bps(2.0, now),
            "basis_bps": round(self.basis_bps, 2),
            "finalized_1h_open": self.finalized_1h_open,
        }
        markets_map: Dict[str, Any] = {}
        if "UP" in self.books and "DOWN" in self.books:
            snap["UP"] = self.books["UP"].top_of_book(now)
            snap["DOWN"] = self.books["DOWN"].top_of_book(now)
            if self.current_market and "tokens" in self.current_market:
                snap["UP"]["token_id"] = self.current_market["tokens"].get("UP")
                snap["DOWN"]["token_id"] = self.current_market["tokens"].get("DOWN")
                mid = str(self.current_market.get("market_id"))
                markets_map[mid] = {
                    "market_id": mid,
                    "asset": self.asset,
                    "horizon": "1h",
                    "timestamp_unix": now,
                    "spot_price": self.spot_price,
                    "futures_price": self.futures_price,
                    "UP": snap["UP"],
                    "DOWN": snap["DOWN"],
                }
        for hz, attr_n, up_k, dn_k, snap_k in (
            ("5m", "market_5m", "UP_5M", "DOWN_5M", "m5"),
            ("15m", "market_15m", "UP_15M", "DOWN_15M", "m15"),
            ("4h", "market_4h", "UP_4H", "DOWN_4H", "h4"),
        ):
            mh = getattr(self, attr_n, None)
            if mh and up_k in self.books and dn_k in self.books:
                snap[snap_k] = {
                    "market_id": mh.get("market_id"),
                    "horizon": hz,
                    "finalized_open": mh.get("finalized_open", mh.get("finalized_15m_open")),
                    "finalized_15m_open": mh.get("finalized_15m_open"),
                    "authoritative_chainlink_open": mh.get("authoritative_chainlink_open"),
                    "UP": dict(self.books[up_k].top_of_book(now), token_id=mh["tokens"].get("UP")),
                    "DOWN": dict(self.books[dn_k].top_of_book(now), token_id=mh["tokens"].get("DOWN")),
                }
                mid_h = str(mh.get("market_id"))
                markets_map[mid_h] = {
                    "market_id": mid_h,
                    "asset": self.asset,
                    "horizon": hz,
                    "timestamp_unix": now,
                    "spot_price": self.spot_price,
                    "futures_price": self.futures_price,
                    "UP": snap[snap_k]["UP"],
                    "DOWN": snap[snap_k]["DOWN"],
                }
        snap["markets"] = markets_map
        return snap

    def _publish_shm_fast_tick(self, market_id: str, up_token: str, down_token: str) -> None:
        """
        Atomically updates /dev/shm/pm_fast_tick_{asset}.json using a keyed 'markets' map
        and PID-scoped temp file + os.replace() so 1h and 15m feeds never overwrite each other
        and readers never encounter torn JSON reads.
        """
        if "UP" not in self.books or "DOWN" not in self.books:
            return
        now_ts = time.time()
        up_m = self.books["UP"].get_metrics(obs_ts=now_ts, fee_rate=self.fee_rate_market)
        down_m = self.books["DOWN"].get_metrics(obs_ts=now_ts, fee_rate=self.fee_rate_market)
        up_m["token_id"] = str(up_token)
        down_m["token_id"] = str(down_token)

        horizon_str = str((self.current_market or {}).get("horizon", "1h"))
        mkt_entry = {
            "market_id": str(market_id),
            "asset": self.asset,
            "horizon": horizon_str,
            "timestamp_unix": now_ts,
            "spot_price": self.spot_price,
            "futures_price": self.futures_price,
            "UP": up_m,
            "DOWN": down_m,
        }

        shm_path = SHM_DIR / f"pm_fast_tick_{self.asset}.json"
        tmp_path = SHM_DIR / f"pm_fast_tick_{self.asset}.json.tmp.{os.getpid()}"
        try:
            existing: Dict[str, Any] = {}
            if shm_path.exists():
                try:
                    existing = json.loads(shm_path.read_text(encoding="utf-8"))
                except Exception:
                    existing = {}
            markets_map = existing.get("markets", {}) if isinstance(existing, dict) else {}
            # Prune expired markets older than 60s
            markets_map = {
                k: v for k, v in markets_map.items()
                if isinstance(v, dict) and (now_ts - float(v.get("timestamp_unix", 0.0))) <= 60.0
            }
            markets_map[str(market_id)] = mkt_entry
            for hz, attr_n, up_k, dn_k in (
                ("5m", "market_5m", "UP_5M", "DOWN_5M"),
                ("15m", "market_15m", "UP_15M", "DOWN_15M"),
                ("4h", "market_4h", "UP_4H", "DOWN_4H"),
            ):
                mh = getattr(self, attr_n, None)
                if mh and up_k in self.books and dn_k in self.books:
                    mh_id = str(mh.get("market_id"))
                    f_hz = mh.get("fee_metadata", {}).get("fee_rate_market", 0.07)
                    uph_m = self.books[up_k].get_metrics(obs_ts=now_ts, fee_rate=f_hz)
                    dnh_m = self.books[dn_k].get_metrics(obs_ts=now_ts, fee_rate=f_hz)
                    uph_m["token_id"] = str(mh["tokens"].get("UP"))
                    dnh_m["token_id"] = str(mh["tokens"].get("DOWN"))
                    markets_map[mh_id] = {
                        "market_id": mh_id,
                        "asset": self.asset,
                        "horizon": hz,
                        "timestamp_unix": now_ts,
                        "spot_price": self.spot_price,
                        "futures_price": self.futures_price,
                        "UP": uph_m,
                        "DOWN": dnh_m,
                    }
            payload = {
                **mkt_entry,
                "markets": markets_map,
            }
            tmp_path.write_text(json.dumps(payload), encoding="utf-8")
            os.replace(tmp_path, shm_path)
        except Exception as e:
            logger.debug(f"SHM fast tick publish notice: {e}")

    def _maybe_write_fast_tick(self, force: bool = False) -> bool:
        """Atomic (tmp + os.replace) RAM snapshot, throttled to 25ms. Never raises."""
        if not self._fast_tick_enabled:
            return False
        now = time.time()
        if not force and (now - self._last_fast_tick_write) < FAST_TICK_THROTTLE_SEC:
            return False
        self._last_fast_tick_write = now
        try:
            snap = self.build_fast_tick_snapshot(now)
            payload = _orjson.dumps(snap) if _orjson else json.dumps(snap).encode("utf-8")
            tmp = self.fast_tick_file.with_suffix(f".tmp.{os.getpid()}")
            with open(tmp, "wb") as f:
                f.write(payload)
            os.replace(tmp, self.fast_tick_file)
        except Exception as e:
            logger.debug(f"[FAST TICK] shm write notice: {e}")
            return False
        # Low-frequency (1s) read-only EXP-306 boundary/merge evaluation piggybacks on the tick bus
        if now - self._last_exp306_eval >= 1.0:
            self._last_exp306_eval = now
            self._run_exp306_realtime_eval(snap)
        return True

    def _run_exp306_realtime_eval(self, snap: Dict[str, Any]) -> None:
        try:
            recs = []
            if self.current_market and "UP" in snap and "DOWN" in snap:
                secs_left = (self.current_market["end_dt"] - datetime.now(timezone.utc)).total_seconds()
                recs.append(evaluate_realtime_exp306_boundary_and_merge(
                    self.asset, "1h", str(self.current_market["market_id"]), snap["UP"], snap["DOWN"],
                    self.spot_price, self.finalized_1h_open, secs_left, fee_rate=self.fee_rate_market,
                ))
            m15 = getattr(self, "market_15m", None)
            if m15 and "m15" in snap:
                secs_left_15 = (m15["end_dt"] - datetime.now(timezone.utc)).total_seconds()
                recs.append(evaluate_realtime_exp306_boundary_and_merge(
                    self.asset, "15m", str(m15.get("market_id")), snap["m15"]["UP"], snap["m15"]["DOWN"],
                    self.spot_price, float(m15.get("finalized_15m_open") or 0.0), secs_left_15,
                    fee_rate=float(m15.get("fee_metadata", {}).get("fee_rate_market", 0.07) or 0.07),
                    sigma_1h=self.get_rolling_sigma("1h"),
                ))
            hits = [r for r in recs if r.get("merge_opportunity") or r.get("boundary_opportunity")]
            if hits:
                for r in hits:
                    _atomic_append_jsonl(EXP306_REALTIME_LEDGER, json.dumps(r))
        except Exception as e:
            logger.debug(f"[EXP306 REALTIME] evaluation notice: {e}")

    def _update_rolling_sigma(self, px: float, now_sec: Optional[float] = None) -> None:
        if px <= 0:
            return
        now_sec = now_sec if now_sec is not None else time.time()
        b1m = int(now_sec // 60)
        if b1m > self._spot_1m_bucket:
            if self._last_1m_spot > 0:
                ret_1m = math.log(px / self._last_1m_spot)
                var_1h_obs = 60.0 * (ret_1m ** 2)
                new_var = 0.95 * (self._rolling_sigma_1h ** 2) + 0.05 * var_1h_obs
                self._rolling_sigma_1h = max(0.0020, min(0.0300, math.sqrt(new_var)))
            self._last_1m_spot = px
            self._spot_1m_bucket = b1m

    def get_rolling_sigma(self, horizon: str = "1h") -> float:
        s1h = getattr(self, "_rolling_sigma_1h", 0.0050 if self.asset == "BTC" else 0.0068)
        if str(horizon).lower() == "15m":
            return round(s1h * 0.5, 5)
        return round(s1h, 5)

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "PolymarketDualFeedRecorder/2.7"},
                max_line_size=65536,
                max_field_size=65536,
            )
        return self.session

    async def calibrate_binance_clock_offset(self):
        """
        Calibrates local Tokyo clock offset against Binance server time using Cristian's algorithm.
        Offset = (t_req + t_resp)/2 - t_server
        Uncertainty = RTT / 2
        """
        session = await self.get_session()
        try:
            t0 = time.time() * 1000.0
            async with session.get(f"{BINANCE_REST_URL}/api/v3/time") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    server_time_ms = float(data["serverTime"])
                    t1 = time.time() * 1000.0
                    rtt = t1 - t0
                    t_mid = (t0 + t1) / 2.0
                    self.clock_offset_ms = round(t_mid - server_time_ms, 2)
                    self.clock_uncertainty_ms = round(rtt / 2.0, 2)
                    self.last_clock_sync_ts = time.time()
                    logger.info(f"[CLOCK CALIBRATION] Tokyo <-> Binance Offset: {self.clock_offset_ms:+.2f}ms "
                                f"(Uncertainty: +/-{self.clock_uncertainty_ms:.2f}ms, RTT: {rtt:.2f}ms)")
        except Exception as e:
            logger.warning(f"Clock calibration failed: {e}")

    async def discover_nearest_1h_market(self) -> Optional[Dict[str, Any]]:
        """Enforces: series_slug == self.series_slug and market_duration == 3600s."""
        session = await self.get_session()
        try:
            now = datetime.now(timezone.utc)
            now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            url = (
                f"{GAMMA_API_URL}/events?series_slug={self.series_slug}"
                f"&limit=20&closed=false&end_date_min={now_iso}&order=endDate&ascending=true"
            )
            async with session.get(url) as resp:
                if resp.status == 200:
                    events = await resp.json()
                    now = datetime.now(timezone.utc)
                    candidates = []
                    for event in events:
                        markets = event.get("markets", [])
                        if not markets:
                            continue
                        m = markets[0]
                        m_end_str = m.get("endDate") or event.get("endDate")
                        if not m_end_str:
                            continue
                        end_dt = datetime.fromisoformat(m_end_str.replace("Z", "+00:00"))
                        secs_left = (end_dt - now).total_seconds()
                        if 0 < secs_left <= 7200:  # within next 2 hours
                            candidates.append((secs_left, event, m, end_dt, m_end_str))

                    if not candidates:
                        return None

                    candidates.sort(key=lambda x: x[0])
                    secs_left, event, m, end_dt, m_end_str = candidates[0]

                    m_id = str(m.get("id"))
                    condition_id = str(m.get("conditionId") or "")
                    tokens_raw = m.get("clobTokenIds")
                    tokens = json.loads(tokens_raw) if isinstance(tokens_raw, str) else tokens_raw
                    outcomes_raw = m.get("outcomes", '["Up", "Down"]')
                    outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw

                    candle_open_ts = int(end_dt.timestamp() - 3600)
                    candle_close_ts = int(end_dt.timestamp())

                    # Check dynamic fee parameters from market metadata
                    fee_schedule = m.get("feeSchedule", {})
                    if isinstance(fee_schedule, dict) and "rate" in fee_schedule:
                        self.fee_rate_market = float(fee_schedule["rate"])
                        self.fee_exponent = float(fee_schedule.get("exponent", 1.0))
                        self.fee_source = f"gamma_feeSchedule_{m.get('feeType', 'crypto_fees_v2')}"
                    elif m.get("takerBaseFee") is not None:
                        raw_taker = float(m.get("takerBaseFee"))
                        self.fee_rate_market = raw_taker / 10000.0 if raw_taker > 1.0 else raw_taker
                        self.fee_exponent = 1.0
                        self.fee_source = "gamma_takerBaseFee"
                    else:
                        self.fee_rate_market = DEFAULT_FEE_RATE
                        self.fee_exponent = 1.0
                        self.fee_source = "polymarket_crypto_schedule_v1"

                    self.fee_enabled = bool(m.get("feesEnabled", True))
                    self.fee_formula_version = str(m.get("feeType", "crypto_fees_v2"))

                    # Pre-populate spot and futures price via REST
                    url_spot = f"{BINANCE_REST_URL}/api/v3/ticker/price?symbol={self.binance_symbol}"
                    url_fut = f"{BINANCE_FUTURES_REST_URL}/fapi/v1/ticker/price?symbol={self.binance_symbol}"
                    try:
                        if not self.futures_only_ref:
                            async with session.get(url_spot) as resp_spot:
                                if resp_spot.status == 200:
                                    data_spot = await resp_spot.json()
                                    self.spot_price = float(data_spot["price"])
                        async with session.get(url_fut) as resp_fut:
                            if resp_fut.status == 200:
                                data_fut = await resp_fut.json()
                                self.futures_price = float(data_fut["price"])
                                if self.futures_only_ref and self.futures_price > 0:
                                    self.spot_price = self.futures_price
                                self.update_basis()
                    except Exception:
                        pass

                    return {
                        "market_id": m_id,
                        "condition_id": condition_id,
                        "title": event.get("title"),
                        "question": m.get("question"),
                        "slug": event.get("slug"),
                        "resolution_source": str(m.get("resolutionSource") or event.get("resolutionSource") or ""),
                        "end_date_iso": m_end_str,
                        "end_dt": end_dt,
                        "candle_open_ts": candle_open_ts,
                        "candle_close_ts": candle_close_ts,
                        "tokens": {
                            "UP": tokens[0],
                            "DOWN": tokens[1]
                        },
                        "outcomes": outcomes,
                        "fee_metadata": {
                            "fee_rate_market": self.fee_rate_market,
                            "fee_exponent": self.fee_exponent,
                            "fee_source": self.fee_source,
                            "fee_enabled": self.fee_enabled,
                            "fee_formula_version": self.fee_formula_version,
                            "condition_id": condition_id,
                            "timestamp_utc": time.time(),
                        }
                    }
        except Exception as e:
            logger.error(f"Error discovering 1H market: {e}")
        return None

    async def discover_nearest_twap_market(self, horizon: str = "15m") -> Optional[Dict[str, Any]]:
        """
        Discovers active 5m, 15m, or 4h Chainlink-TWAP candle market from Gamma API.
        Fetches finalized Binance candle open + 60s TWAP + authoritative 15-digit Chainlink openPrice.
        """
        hz = str(horizon).lower()
        dur_sec = {"5m": 300, "15m": 900, "4h": 14400}.get(hz, 900)
        max_secs = {"5m": 600, "15m": 1800, "4h": 28800}.get(hz, 1800)
        session = await self.get_session()
        asset_lower = self.asset.lower()
        slug_candidates = [
            f"{asset_lower}-up-or-down-{hz}",
            f"{asset_lower}-{hz}",
        ]
        now = datetime.now(timezone.utc)
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        for s_slug in slug_candidates:
            try:
                url = (
                    f"{GAMMA_API_URL}/events?series_slug={s_slug}"
                    f"&limit=10&closed=false&end_date_min={now_iso}&order=endDate&ascending=true"
                )
                async with session.get(url) as resp:
                    if resp.status != 200:
                        continue
                    events = await resp.json()
                    candidates = []
                    for event in events:
                        markets = event.get("markets", [])
                        if not markets:
                            continue
                        m = markets[0]
                        m_end_str = m.get("endDate") or event.get("endDate")
                        if not m_end_str:
                            continue
                        end_dt = datetime.fromisoformat(m_end_str.replace("Z", "+00:00"))
                        secs_left = (end_dt - now).total_seconds()
                        if 0 < secs_left <= max_secs:
                            candidates.append((secs_left, event, m, end_dt, m_end_str))
                    if not candidates:
                        continue
                    candidates.sort(key=lambda x: x[0])
                    secs_left, event, m, end_dt, m_end_str = candidates[0]
                    m_id = str(m.get("id"))
                    condition_id = str(m.get("conditionId") or "")
                    tokens_raw = m.get("clobTokenIds")
                    tokens = json.loads(tokens_raw) if isinstance(tokens_raw, str) else tokens_raw
                    outcomes_raw = m.get("outcomes", '["Up", "Down"]')
                    outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw

                    candle_open_ts = int(end_dt.timestamp() - dur_sec)
                    candle_close_ts = int(end_dt.timestamp())

                    fee_schedule = m.get("feeSchedule", {})
                    fee_rate = DEFAULT_FEE_RATE
                    fee_exp = 1.0
                    if isinstance(fee_schedule, dict) and "rate" in fee_schedule:
                        fee_rate = float(fee_schedule["rate"])
                        fee_exp = float(fee_schedule.get("exponent", 1.0))
                    elif m.get("takerBaseFee") is not None:
                        raw_taker = float(m.get("takerBaseFee"))
                        fee_rate = raw_taker / 10000.0 if raw_taker > 1.0 else raw_taker

                    open_px, _ = await self.fetch_finalized_binance_candle(candle_open_ts, interval=hz)
                    twap_60s_px = await self.fetch_binance_60s_twap_open(candle_open_ts)
                    auth_cl_open = await self.fetch_authoritative_chainlink_open(candle_open_ts, candle_close_ts, horizon=hz)
                    cl_open = auth_cl_open if auth_cl_open > 0.0 else 0.0
                    if cl_open <= 0.0 and abs(time.time() - candle_open_ts) <= 35.0:
                        cl_open = await self.fetch_polygon_chainlink_spot()

                    return {
                        "market_id": m_id,
                        "condition_id": condition_id,
                        "horizon": hz,
                        "title": event.get("title"),
                        "question": m.get("question"),
                        "slug": event.get("slug"),
                        "series_slug": s_slug,
                        "resolution_source": str(m.get("resolutionSource") or event.get("resolutionSource") or ""),
                        "end_date_iso": m_end_str,
                        "end_dt": end_dt,
                        "candle_open_ts": candle_open_ts,
                        "candle_close_ts": candle_close_ts,
                        "tokens": {
                            "UP": tokens[0],
                            "DOWN": tokens[1]
                        },
                        "outcomes": outcomes,
                        "finalized_open": open_px,
                        "finalized_15m_open": open_px,
                        "twap_60s_open": twap_60s_px,
                        "authoritative_chainlink_open": auth_cl_open or None,
                        "chainlink_open_spot": cl_open or None,
                        "fee_metadata": {
                            "fee_rate_market": fee_rate,
                            "fee_exponent": fee_exp,
                            "fee_source": f"gamma_{hz}_crypto_fees",
                            "fee_enabled": True,
                            "fee_formula_version": "crypto_fees_v2",
                            "condition_id": condition_id,
                            "timestamp_utc": time.time(),
                        }
                    }
            except Exception as e:
                logger.debug(f"{hz} discovery notice for {s_slug}: {e}")
        return None

    async def discover_nearest_15m_market(self) -> Optional[Dict[str, Any]]:
        return await self.discover_nearest_twap_market("15m")

    async def discover_nearest_5m_market(self) -> Optional[Dict[str, Any]]:
        return await self.discover_nearest_twap_market("5m")

    async def discover_nearest_4h_market(self) -> Optional[Dict[str, Any]]:
        return await self.discover_nearest_twap_market("4h")

    async def fetch_authoritative_chainlink_open(
        self, candle_open_ts: int, candle_close_ts: int, horizon: str = "15m"
    ) -> float:
        """
        Queries Polymarket's exact 60s-TWAP endpoint (`twapEnabled=true&twapLookbackSeconds=60`)
        for `5m` (`fiveminute`), `15m` (`fifteen`), or `4h` (`fourhour`) to lock the 15-digit
        Chainlink `priceToBeat` at `t = +2s`, with finalized preceding-5m Gamma `finalPrice` fallback.
        """
        now_t = time.time()
        if now_t < float(candle_open_ts) + 2.0:
            return 0.0
        variant = {"5m": "fiveminute", "15m": "fifteen", "4h": "fourhour"}.get(str(horizon).lower(), "fifteen")
        session = await self.get_session()
        start_iso = datetime.fromtimestamp(int(candle_open_ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = datetime.fromtimestamp(int(candle_close_ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        twap_url = (
            f"https://polymarket.com/api/crypto/crypto-price"
            f"?symbol={self.asset.upper()}&eventStartTime={start_iso}"
            f"&variant={variant}&endDate={end_iso}&twapEnabled=true&twapLookbackSeconds=60"
        )
        try:
            async with session.get(twap_url, timeout=aiohttp.ClientTimeout(total=3.5)) as resp:
                if resp.status == 200:
                    payload = await resp.json()
                    if isinstance(payload, dict) and (payload.get("cached") is True or payload.get("completed") is True):
                        if payload.get("openPrice") is not None:
                            val = float(payload["openPrice"])
                            if math.isfinite(val) and val > 0.0:
                                return val
        except Exception as e:
            logger.debug(f"[{self.asset}] Authoritative {horizon} TWAP query note: {e}")
        if now_t >= float(candle_open_ts) + 35.0:
            try:
                g_url = f"{GAMMA_API_URL}/events?slug={self.asset.lower()}-updown-5m-{int(candle_open_ts) - 300}"
                async with session.get(g_url, timeout=aiohttp.ClientTimeout(total=3.5)) as resp:
                    if resp.status == 200:
                        payload = await resp.json()
                        ev = payload[0] if isinstance(payload, list) and payload else payload
                        if isinstance(ev, dict) and ev.get("closed") is True:
                            meta = ev.get("eventMetadata")
                            meta = json.loads(meta) if isinstance(meta, str) else meta
                            if isinstance(meta, dict) and meta.get("finalPrice") is not None:
                                val = float(meta["finalPrice"])
                                if math.isfinite(val) and val > 0.0:
                                    return val
            except Exception:
                pass
        return 0.0

    async def fetch_authoritative_chainlink_open_15m(self, candle_open_ts: int, candle_close_ts: int) -> float:
        return await self.fetch_authoritative_chainlink_open(candle_open_ts, candle_close_ts, "15m")

    async def fetch_binance_60s_twap_open(self, candle_open_ts: int) -> float:
        """
        Pulls the 60 finalized 1-second Binance Spot klines over [candle_open_ts - 60, candle_open_ts)
        (with 1-minute OHLC/4 fallback) to compute the exact 60-second time-weighted average price
        matching Chainlink's 60s TWAP reference strike on 15m Up/Down markets.
        """
        session = await self.get_session()
        start_ms = (int(candle_open_ts) - 60) * 1000
        if not self.futures_only_ref:
            try:
                url_1s = (
                    f"{BINANCE_REST_URL}/api/v3/klines"
                    f"?symbol={self.binance_symbol}&interval=1s&startTime={start_ms}&limit=60"
                )
                async with session.get(url_1s) as resp_1s:
                    if resp_1s.status == 200:
                        data_1s = await resp_1s.json()
                        if isinstance(data_1s, list) and len(data_1s) >= 30:
                            twap = sum((float(k[1]) + float(k[4])) / 2.0 for k in data_1s) / len(data_1s)
                            return round(twap, 4)
            except Exception as e_1s:
                logger.debug(f"1s TWAP fetch fallback notice for {self.binance_symbol}: {e_1s}")
        try:
            kline_base = f"{BINANCE_FUTURES_REST_URL}/fapi/v1/klines" if self.futures_only_ref else f"{BINANCE_REST_URL}/api/v3/klines"
            url = (
                f"{kline_base}"
                f"?symbol={self.binance_symbol}&interval=1m&startTime={start_ms}&limit=1"
            )
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        o_px = float(data[0][1])
                        h_px = float(data[0][2])
                        l_px = float(data[0][3])
                        c_px = float(data[0][4])
                        return round((o_px + h_px + l_px + c_px) / 4.0, 4)
        except Exception as e:
            logger.debug(f"Failed to fetch 60s TWAP open for {self.binance_symbol}: {e}")
        return 0.0

    async def fetch_finalized_binance_candle(
        self, candle_open_ts: int, interval: str = "1h"
    ) -> Tuple[float, float]:
        """Pulls exact finalized Binance Spot (or Futures when futures_only_ref) 5m, 15m, 1h, or 4h candle open and close prices."""
        session = await self.get_session()
        iv_low = str(interval).lower()
        if iv_low in ("5m", "300s"):
            binance_interval = "5m"
        elif iv_low in ("15m", "900s"):
            binance_interval = "15m"
        elif iv_low in ("4h", "14400s"):
            binance_interval = "4h"
        else:
            binance_interval = "1h"
        try:
            start_ms = int(candle_open_ts) * 1000
            kline_base = f"{BINANCE_FUTURES_REST_URL}/fapi/v1/klines" if self.futures_only_ref else f"{BINANCE_REST_URL}/api/v3/klines"
            url = (
                f"{kline_base}"
                f"?symbol={self.binance_symbol}&interval={binance_interval}&startTime={start_ms}&limit=1"
            )
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        open_px = float(data[0][1])
                        close_px = float(data[0][4])
                        return open_px, close_px
        except Exception as e:
            logger.error(f"Failed to fetch Binance {binance_interval} candle for {self.binance_symbol}: {e}")
        return 0.0, 0.0

    async def verify_and_log_resolution(self, market: Dict[str, Any], max_polls: int = 60, poll_interval_sec: float = 30.0):
        """
        Polls official Polymarket Gamma API (`outcomePrices`) up to 30 minutes (`60 * 30s`)
        so Chainlink 60s-TWAP / UMA oracle settlements are captured authoritatively without
        contaminating ground-truth labels with Binance 1s spot mismatches.
        """
        m_id_str = str(market.get("market_id") or "")
        logged_set = getattr(self, "_logged_resolution_market_ids", None)
        if logged_set is None:
            logged_set = set()
            self._logged_resolution_market_ids = logged_set
        if not m_id_str or m_id_str in logged_set:
            return
        logged_set.add(m_id_str)
        duration = int(market.get("candle_close_ts", 0)) - int(market.get("candle_open_ts", 0))
        default_hz = "5m" if 0 < duration <= 300 else ("15m" if 0 < duration <= 900 else ("4h" if duration >= 10800 else "1h"))
        horizon = str(market.get("horizon") or default_hz)
        logger.info(f"[*] Awaiting finalized {horizon} resolution for market {market['market_id']} ({market['title']})...")
        await asyncio.sleep(6.0)
        open_px, close_px = await self.fetch_finalized_binance_candle(market["candle_open_ts"], interval=horizon)
        binance_y_up = (1 if close_px >= open_px else 0) if (open_px > 0 and close_px > 0) else None
        binance_winner = ("UP" if binance_y_up == 1 else "DOWN") if binance_y_up is not None else None
        ret_pct = (((close_px - open_px) / open_px) * 100.0) if (open_px > 0 and close_px > 0) else 0.0

        gamma_winner = None
        res_source = str(market.get("resolution_source") or "")
        for attempt in range(max_polls):
            try:
                session = await self.get_session()
                async with session.get(f"{GAMMA_API_URL}/markets/{m_id_str}") as g_resp:
                    if g_resp.status == 200:
                        g_data = await g_resp.json()
                        if isinstance(g_data, dict):
                            if not res_source and g_data.get("resolutionSource"):
                                res_source = str(g_data.get("resolutionSource"))
                            raw_prices = g_data.get("outcomePrices")
                            raw_outcomes = g_data.get("outcomes", '["Up", "Down"]')
                            prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices
                            outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
                            if isinstance(prices, list) and len(prices) >= 2:
                                p0, p1 = float(prices[0]), float(prices[1])
                                o0 = str(outcomes[0]).upper() if isinstance(outcomes, list) and len(outcomes) >= 2 else "UP"
                                o1 = str(outcomes[1]).upper() if isinstance(outcomes, list) and len(outcomes) >= 2 else "DOWN"
                                if p0 >= 0.99 and p1 <= 0.01:
                                    gamma_winner = "UP" if "UP" in o0 or "YES" in o0 else ("DOWN" if "DOWN" in o0 or "NO" in o0 else o0)
                                    break
                                elif p1 >= 0.99 and p0 <= 0.01:
                                    gamma_winner = "UP" if "UP" in o1 or "YES" in o1 else ("DOWN" if "DOWN" in o1 or "NO" in o1 else o1)
                                    break
            except Exception as g_err:
                logger.debug(f"Gamma resolution check notice for {m_id_str}: {g_err}")
            if attempt + 1 < max_polls:
                await asyncio.sleep(poll_interval_sec)

        # Authoritative winner is strictly Gamma/Chainlink when available; never silently masquerade Binance as Gamma
        final_winner = gamma_winner
        y_up = (1 if final_winner == "UP" else 0) if final_winner in ("UP", "DOWN") else None
        y_down = (1 if final_winner == "DOWN" else 0) if final_winner in ("UP", "DOWN") else None
        oracle_mismatch = bool(gamma_winner and binance_winner and gamma_winner != binance_winner)
        if oracle_mismatch:
            logger.warning(
                f"[ORACLE MISMATCH ALERT] {market['title']} ({horizon}, m_id={m_id_str}): "
                f"Binance Spot={binance_winner} (${open_px:,.2f}->${close_px:,.2f}, {ret_pct:+.4f}%) "
                f"vs Official Gamma Settlement={gamma_winner} (source={res_source or 'unknown'})!"
            )

        res_record = {
            "timestamp_resolved": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "asset": self.asset,
            "horizon": horizon,
            "market_id": str(market["market_id"]),
            "title": market["title"],
            "candle_open_ts": market["candle_open_ts"],
            "candle_close_ts": market["candle_close_ts"],
            "authoritative_chainlink_open": market.get("authoritative_chainlink_open"),
            "binance_spot_open": open_px,
            "binance_spot_close": close_px,
            "candle_return_pct": round(ret_pct, 4),
            "Y_UP": y_up,
            "Y_DOWN": y_down,
            "winning_outcome": final_winner,
            "binance_winning_outcome": binance_winner,
            "gamma_winning_outcome": gamma_winner,
            "oracle_mismatch": oracle_mismatch,
            "resolution_source": res_source,
            "ground_truth_rule": "Official Polymarket Gamma/Chainlink Settlement (outcomePrices)",
        }
        _atomic_append_jsonl(RESOLUTIONS_FILE, json.dumps(res_record))
        logger.info(
            f"[GROUND TRUTH RESOLUTION LOGGED] {market['title']} ({horizon}) | "
            f"Gamma={gamma_winner} | BinanceDiag={binance_winner} ({ret_pct:+.3f}%)"
        )

    def update_basis(self):
        if self.spot_price > 0 and self.futures_price > 0:
            self.basis_usd = self.futures_price - self.spot_price
            self.basis_bps = (self.basis_usd / self.spot_price) * 10000.0
            self.basis_history.append((time.monotonic_ns(), self.basis_bps))

    def get_delta_basis_100ms(self) -> float:
        """Computes signed basis change over the last 100ms."""
        now_ns = time.monotonic_ns()
        cutoff_ns = now_ns - 100_000_000
        for t_ns, b_bps in self.basis_history:
            if t_ns >= cutoff_ns:
                return round(self.basis_bps - b_bps, 2)
        return 0.0

    async def stream_binance_spot(self):
        """Tokyo-latency microsecond Binance Spot aggTrade stream (Polymarket Settlement Ref)."""
        if self.futures_only_ref or not self.binance_spot_ws:
            logger.info(f"[{self.asset}] futures_only_ref active; skipping Binance Spot WS (using Binance Futures + Coinbase USD).")
            return
        while self.running:
            try:
                logger.info(f"Connecting to Binance Spot aggTrade ({self.binance_spot_ws})...")
                async with websockets.connect(self.binance_spot_ws, ping_interval=20, ping_timeout=10) as ws:
                    logger.info(f"[+] Subscribed to Binance Spot aggTrade stream ({self.binance_symbol}).")
                    async for msg_str in ws:
                        if not self.running:
                            break
                        recv_mono_ns = time.monotonic_ns()
                        msg = _orjson.loads(msg_str) if _orjson is not None else json.loads(msg_str)
                        px = float(msg.get("p", 0))
                        sz = float(msg.get("q", 0))
                        is_buyer = not msg.get("m", False)  # True = taker buy
                        e_ts = int(msg.get("E", 0))
                        t_ts = int(msg.get("T", 0))
                        notional = px * sz

                        self.spot_price = px
                        self._update_rolling_sigma(px)
                        self.update_basis()
                        self.spot_trades.append((recv_mono_ns, e_ts, t_ts, notional, is_buyer, px))

                        # Evaluate Spot 100ms volume shock with strictly anchored t0
                        self.evaluate_shock(recv_mono_ns, e_ts, source="SPOT")
                        self._maybe_write_fast_tick()
            except Exception as e:
                logger.warning(f"Binance Spot feed disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    async def stream_binance_futures(self):
        """Tokyo-latency microsecond Binance USDⓈ-M Futures aggTrade stream (Routed /market endpoint)."""
        while self.running:
            try:
                logger.info(f"Connecting to Binance Futures aggTrade ({self.binance_futures_ws})...")
                async with websockets.connect(self.binance_futures_ws, ping_interval=20, ping_timeout=10) as ws:
                    logger.info(f"[+] Subscribed to Binance Futures aggTrade stream ({self.binance_symbol} routed /market).")
                    async for msg_str in ws:
                        if not self.running:
                            break
                        recv_mono_ns = time.monotonic_ns()
                        msg = _orjson.loads(msg_str) if _orjson is not None else json.loads(msg_str)
                        px = float(msg.get("p", 0))
                        sz = float(msg.get("q", 0))
                        is_buyer = not msg.get("m", False)
                        e_ts = int(msg.get("E", 0))
                        t_ts = int(msg.get("T", 0))
                        notional = px * sz

                        self.futures_price = px
                        if self.futures_only_ref:
                            self.spot_price = px
                            self._update_rolling_sigma(px)
                        self.update_basis()
                        self.futures_trades.append((recv_mono_ns, e_ts, t_ts, notional, is_buyer, px))

                        # Evaluate Futures 100ms volume shock with strictly anchored t0
                        self.evaluate_shock(recv_mono_ns, e_ts, source="FUTURES")
                        self._maybe_write_fast_tick()
            except Exception as e:
                logger.warning(f"Binance Futures feed disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    # ------------------------------------------------------------------
    # v3.4 Adaptive session-volume threshold + BTC -> ETH lead-state bridge
    # ------------------------------------------------------------------
    def _record_volume(self, notional: float, now_sec: Optional[float] = None) -> None:
        sec = int(now_sec if now_sec is not None else time.time())
        if self._vol_first_sec is None:
            self._vol_first_sec = sec
        if self._vol_buckets and self._vol_buckets[-1][0] == sec:
            self._vol_buckets[-1][1] += notional
        else:
            self._vol_buckets.append([sec, float(notional)])

    def get_avg_100ms_vol_5m(self, now_sec: Optional[float] = None) -> Optional[float]:
        """Rolling 5-minute mean 100ms dollar volume (spot + futures); None with < 60s of coverage."""
        now_sec = now_sec if now_sec is not None else time.time()
        if self._vol_first_sec is None or (now_sec - self._vol_first_sec) < ADAPTIVE_THRESH_MIN_COVERAGE_SEC:
            return None
        cutoff = now_sec - ADAPTIVE_THRESH_WINDOW_SEC
        total = sum(v for s, v in self._vol_buckets if s >= cutoff)
        window = min(float(ADAPTIVE_THRESH_WINDOW_SEC), now_sec - self._vol_first_sec)
        if window <= 0:
            return None
        return total / (window * 10.0)

    def get_effective_shock_threshold(self, now_sec: Optional[float] = None) -> float:
        """Adaptive threshold in [0.65x, 1.35x] of base, recomputed at most once per second."""
        now_sec = now_sec if now_sec is not None else time.time()
        computed_at, val = self._adaptive_cache
        if now_sec - computed_at >= 1.0:
            val = compute_adaptive_shock_threshold(float(self.shock_threshold_usd), self.get_avg_100ms_vol_5m(now_sec))
            self._adaptive_cache = (now_sec, val)
        return val

    def _publish_btc_lead_state(self, vol_100ms: float, ofi_100ms: float, delta_basis: float,
                                flow_dir: str, z_btc: float, force: bool = False) -> None:
        """BTC recorder only: throttled (25ms, forced on trigger) RAM publish of live shock state."""
        if self.asset != "BTC" or not self._fast_tick_enabled:
            return
        now = time.time()
        if not force and (now - self._last_lead_state_write) < LEAD_STATE_THROTTLE_SEC:
            return
        self._last_lead_state_write = now
        state = {
            "asset": "BTC",
            "ts_ns": time.time_ns(),
            "t0_unix": now,
            "spot_px": self.spot_price,
            "spot_price": self.spot_price,
            "basis_bps": round(self.basis_bps, 2),
            "vol_100ms": round(vol_100ms, 0),
            "ofi_100ms": round(ofi_100ms, 3),
            "delta_basis_100ms": delta_basis,
            "shock_dir": flow_dir,
            "btc_shock_direction": flow_dir,
            "btc_target_token": "UP" if flow_dir in ("BUY", "UP") else "DOWN",
            "z_btc": round(z_btc, 4),
        }
        state.update(self._last_btc_shock)
        write_lead_state(state, self.lead_state_file)

    def evaluate_shock(self, recv_mono_ns: int, event_ts_ms: int, source: str):
        """
        Evaluates volume sweeps strictly over [t0 - 100ms, t0].
        t0 is anchored as the end of the qualifying shock window.
        Enforces both local receipt monotonicity AND exchange trade/event timestamp windowing
        plus a 1000ms live exchange-lag ceiling so socket burst-drains never fire phantom shocks.
        """
        trade_queue = self.spot_trades if source == "SPOT" else self.futures_trades
        if trade_queue:
            self._record_volume(float(trade_queue[-1][3]))

        now_wall_sec = time.time()
        exch_lag_ms = (now_wall_sec * 1000.0 - float(event_ts_ms)) if event_ts_ms > 0 else 0.0
        if event_ts_ms > 1_600_000_000_000 and 1000.0 < exch_lag_ms < 86_400_000.0:
            last_warn = float(getattr(self, "_last_stale_exch_warn_ts", 0.0) or 0.0)
            if now_wall_sec - last_warn >= 5.0:
                self._last_stale_exch_warn_ts = now_wall_sec
                logger.warning(
                    f"[STALE_EXCHANGE_EVENT_VETO] Dropping stale {source} {self.asset} packet "
                    f"(exch_lag_ms={exch_lag_ms:.1f}ms > 1000ms ceiling) to prevent burst-drain phantom shock."
                )
            return

        base_threshold = float(self.shock_threshold_usd)
        eff_threshold = self.get_effective_shock_threshold()
        cutoff_ns = recv_mono_ns - 100_000_000  # 100ms rolling window
        cutoff_40_ns = recv_mono_ns - 40_000_000  # 40ms fast-track impulse window
        vol_100ms = 0.0
        buy_vol = 0.0
        sell_vol = 0.0

        vol_40ms = 0.0
        buy_40ms = 0.0
        sell_40ms = 0.0

        vol_250ms = 0.0
        buy_250ms = 0.0
        sell_250ms = 0.0
        cutoff_250_ns = recv_mono_ns - 250_000_000  # 250ms institutional sweep window
        anchor_exch_ms = int((trade_queue[-1][2] or trade_queue[-1][1]) if trade_queue else 0) or int(event_ts_ms or 0)
        for t_mono, e_ts_i, t_ts_i, ntl, buyer, _ in reversed(trade_queue):
            if t_mono < cutoff_250_ns:
                break
            ts_i_ms = int(t_ts_i or e_ts_i or 0)
            if anchor_exch_ms > 0 and ts_i_ms > 0:
                dt_exch_ms = anchor_exch_ms - ts_i_ms
                if dt_exch_ms > 250:
                    break
                if dt_exch_ms < -50:
                    continue
                in_100ms = (dt_exch_ms <= 100) and (t_mono >= cutoff_ns)
                in_40ms = (dt_exch_ms <= 40) and (t_mono >= cutoff_40_ns)
            else:
                in_100ms = (t_mono >= cutoff_ns)
                in_40ms = (t_mono >= cutoff_40_ns)
            vol_250ms += ntl
            if buyer:
                buy_250ms += ntl
            else:
                sell_250ms += ntl
            if in_100ms:
                vol_100ms += ntl
                if buyer:
                    buy_vol += ntl
                else:
                    sell_vol += ntl
            if in_40ms:
                vol_40ms += ntl
                if buyer:
                    buy_40ms += ntl
                else:
                    sell_40ms += ntl

        # Cross-venue 100ms synchronized flow check (Spot + Futures) with early break & directional aggregation
        other_queue = self.futures_trades if source == "SPOT" else self.spot_trades
        other_100ms = 0.0
        other_buy_100ms = 0.0
        other_sell_100ms = 0.0
        for t_m, o_e_ts, o_t_ts, ntl, buyer, _ in reversed(other_queue):
            if t_m < cutoff_ns:
                break
            o_ts_ms = int(o_t_ts or o_e_ts or 0)
            if anchor_exch_ms > 0 and o_ts_ms > 0 and abs(anchor_exch_ms - o_ts_ms) > 120:
                if (anchor_exch_ms - o_ts_ms) > 120:
                    break
                continue
            other_100ms += ntl
            if buyer:
                other_buy_100ms += ntl
            else:
                other_sell_100ms += ntl
        combined_100ms = vol_100ms + 0.75 * other_100ms

        # v3.4 directional flow state (pre-trigger) for the BTC lead bridge / ETH sympathy
        flow_dir = "BUY" if buy_vol >= sell_vol else "SELL"
        ofi_raw_100ms = (buy_vol - sell_vol) / vol_100ms if vol_100ms > 0 else 0.0
        lead = None
        sympathy = False
        if self.asset in ("ETH", "SOL", "XRP"):
            lead = read_lead_state(self.lead_state_file, max_age_ms=LEAD_STATE_MAX_AGE_MS)
            if lead is not None:
                tgt_book = self.books.get("UP" if flow_dir == "BUY" else "DOWN")
                tgt_age = tgt_book.top_of_book().get("age_ask_ms") if tgt_book else None
                sympathy = evaluate_btc_sympathy(lead, flow_dir, tgt_age)
                if sympathy:
                    eff_threshold = min(eff_threshold, SYMPATHY_THRESHOLD_MULT * base_threshold)
        elif self.asset == "BTC":
            z_now = (1.0 if flow_dir == "BUY" else -1.0) * abs(ofi_raw_100ms) * (vol_100ms / max(base_threshold, 1.0))
            self._publish_btc_lead_state(vol_100ms, ofi_raw_100ms, self.get_delta_basis_100ms(), flow_dir, z_now)

        # 40ms Fast-Track Impulse Trigger (Institutional Sweeps)
        ofi_40ms = (buy_40ms - sell_40ms) / max(vol_40ms, 1e-6) if vol_40ms > 0 else 0.0
        is_40ms_fast_track = bool(vol_40ms >= 0.75 * eff_threshold and abs(ofi_40ms) >= 0.90)

        if is_40ms_fast_track:
            vol_100ms = vol_40ms
            buy_vol = buy_40ms
            sell_vol = sell_40ms
        elif vol_100ms < eff_threshold and vol_250ms >= (eff_threshold * 1.45):
            vol_100ms, buy_vol, sell_vol = vol_250ms, buy_250ms, sell_250ms
        elif vol_100ms < eff_threshold and combined_100ms >= (eff_threshold * 1.20):
            vol_100ms = vol_100ms + other_100ms
            buy_vol = buy_vol + other_buy_100ms
            sell_vol = sell_vol + other_sell_100ms

        now_sec = time.time()
        should_trigger = (is_40ms_fast_track or vol_100ms >= eff_threshold)
        if should_trigger and (now_sec - self.last_shock_ts > 2.5):
            up_book = self.books.get("UP")
            down_book = self.books.get("DOWN")
            if not up_book or not down_book or not self.current_market:
                return

            self.last_shock_ts_by_source[source] = now_sec
            self.last_shock_ts = now_sec
            shock_dir = "BUY" if buy_vol >= sell_vol else "SELL"
            ofi = (buy_vol - sell_vol) / vol_100ms if vol_100ms > 0 else 0.0
            trigger_px = self.spot_price if source == "SPOT" else self.futures_price
            shock_z = (1.0 if shock_dir == "BUY" else -1.0) * abs(ofi) * (vol_100ms / max(base_threshold, 1.0))
            if self.asset == "BTC":
                self._last_btc_shock = {
                    "last_shock_ts_ns": time.time_ns(),
                    "last_shock_vol_100ms": round(vol_100ms, 0),
                    "last_shock_ofi_100ms": round(ofi, 3),
                    "last_shock_dir": shock_dir,
                    "last_shock_z_btc": round(shock_z, 4),
                }

            # v3.4 cross-asset fields. BTC direction / z_btc are only attached when BTC actually fired a
            # shock within LEAD_STATE_MAX_AGE_MS (fail-open otherwise, so 100ms BTC noise never vetoes ETH).
            cross_fields: Dict[str, Any] = {
                "effective_shock_threshold": round(eff_threshold, 0),
                "btc_shock_direction": None,
                "z_btc": None,
            }
            if self.asset in ("ETH", "SOL", "XRP"):
                cross_fields["shock_z"] = round(shock_z, 4)
                cross_fields["sympathy_trigger"] = bool(sympathy)
                if lead is not None:
                    btc_shock_ns = int(lead.get("last_shock_ts_ns") or 0)
                    if btc_shock_ns > 0 and (time.time_ns() - btc_shock_ns) / 1e6 <= LEAD_STATE_MAX_AGE_MS:
                        cross_fields["btc_shock_direction"] = "UP" if str(lead.get("last_shock_dir")).upper() == "BUY" else "DOWN"
                        cross_fields["z_btc"] = float(lead.get("last_shock_z_btc") or 0.0)
                        cross_fields["btc_shock_age_ms"] = round((time.time_ns() - btc_shock_ns) / 1e6, 1)
            elif self.asset == "BTC":
                cross_fields["shock_z"] = round(shock_z, 4)
                cross_fields["btc_shock_direction"] = shock_dir
                cross_fields["z_btc"] = round(shock_z, 4)

            # Strict Causal Anchor: t0 = end of the qualifying 100-ms shock window
            t0_sec = now_sec
            t0_mono_ns = recv_mono_ns
            delta_basis_100ms = self.get_delta_basis_100ms()

            # SYNCHRONOUS IMMUTABLE CAUSAL SNAPSHOT AT t0 (Strict zero post-t0 leakage)
            pre_shock_up = up_book.get_metrics(obs_ts=t0_sec, fee_rate=self.fee_rate_market)
            pre_shock_down = down_book.get_metrics(obs_ts=t0_sec, fee_rate=self.fee_rate_market)
            if self.current_market and "tokens" in self.current_market:
                pre_shock_up["token_id"] = self.current_market["tokens"].get("UP")
                pre_shock_down["token_id"] = self.current_market["tokens"].get("DOWN")
            pre_shock_basis_signed = self.basis_bps
            pre_shock_basis_abs = abs(self.basis_bps)

            t0_secs_left = (self.current_market["end_dt"] - datetime.now(timezone.utc)).total_seconds()
            t0_dist_pct = ((self.spot_price - self.finalized_1h_open) / self.finalized_1h_open * 100.0) if self.finalized_1h_open > 0 else 0.0
            t0_spot = self.spot_price
            t0_futures = self.futures_price
            m_id = self.current_market["market_id"]
            condition_id = self.current_market.get("condition_id", "")
            m_title = self.current_market["title"]
            fee_meta = dict(self.current_market.get("fee_metadata", {}))
            horizon_str = str(self.current_market.get("horizon", "1h"))
            candle_sigma = self.get_rolling_sigma(horizon_str)
            tau_frac = max(0.001, t0_secs_left / float(self.current_market.get("duration_s", 3600.0)))
            signed_z = (t0_dist_pct / 100.0) / max(candle_sigma * math.sqrt(tau_frac), 1e-6)

            btc_lead_dir = cross_fields.get("btc_shock_direction")
            z_btc_val = cross_fields.get("z_btc")
            z_eth_val = round(signed_z, 4) if self.asset in ("ETH", "SOL", "XRP") else None

            shock_id_str = f"{m_id}_{t0_sec:.6f}"
            immediate_trigger = {
                "shock_id": shock_id_str,
                "event_id": shock_id_str,
                "timestamp": datetime.fromtimestamp(t0_sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "t0_unix": t0_sec,
                "t0_mono_ns": t0_mono_ns,
                "t0_definition": "local_receipt_boundary",
                "exchange_event_ts_ms": event_ts_ms,
                "clob_ws_connected": bool(getattr(self, "clob_ws_connected", True)),
                "shock_source": source,
                "asset": self.asset,
                "horizon": horizon_str,
                "candle_interval": horizon_str,
                "series_slug": self.series_slug,
                "slug": self.current_market.get("slug", ""),
                "resolution_source": self.current_market.get("resolution_source", ""),
                "market_id": m_id,
                "condition_id": condition_id,
                "title": m_title,
                "seconds_to_expiry": round(t0_secs_left, 1),
                "expiry_ts": float(self.current_market.get("candle_close_ts") or (t0_sec + t0_secs_left)),
                "candle_expiry_ts": float(self.current_market.get("candle_close_ts") or (t0_sec + t0_secs_left)),
                "candle_open_ts": int(self.current_market.get("candle_open_ts") or (int(self.current_market["end_dt"].timestamp()) - 3600)),
                "candle_sigma": candle_sigma,
                "shock_volume_100ms": round(vol_100ms, 0),
                "is_40ms_fast_track": is_40ms_fast_track,
                "shock_direction": shock_dir,
                "btc_shock_direction": btc_lead_dir,
                "z_val": round(abs(signed_z), 4),
                "z_score": round(signed_z, 4),
                "z_btc": z_btc_val,
                "z_eth": z_eth_val,
                "shock_ofi": round(ofi, 3),
                "trigger_price": trigger_px,
                "spot_at_t0": t0_spot,
                "futures_at_t0": t0_futures,
                "basis_signed_bps_t0": round(pre_shock_basis_signed, 2),
                "basis_abs_bps_t0": round(pre_shock_basis_abs, 2),
                "delta_basis_100ms": delta_basis_100ms,
                "coinbase_spot": self.get_coinbase_spot(t0_sec),
                "chainlink_proxy_spot": self.get_chainlink_proxy_spot(t0_sec),
                "chainlink_twap_60s": self.get_chainlink_twap_60s(t0_sec),
                "venue_divergence_bps": self.get_venue_divergence_bps(t0_sec),
                "venue_divergence_centered_bps": self.get_venue_divergence_centered_bps(t0_sec),
                "coinbase_move_bps_2s": self.get_coinbase_move_bps(2.0, t0_sec),
                **cross_fields,
                "finalized_1h_open": self.finalized_1h_open if horizon_str == "1h" else None,
                "candle_open_spot": self.finalized_1h_open,
                "twap_60s_open": float(getattr(self, "twap_60s_1h_open", 0.0) or 0.0) or None,
                "chainlink_open_spot": float(getattr(self, "chainlink_1h_open", 0.0) or 0.0) or None,
                "candle_distance_pct": round(t0_dist_pct, 4),
                "fee_metadata": fee_meta,
                "pre_shock_features_t0": {
                    "UP": pre_shock_up,
                    "DOWN": pre_shock_down
                }
            }
            # Pillar 5B: Emit 15m sub-hourly shock trigger FIRST (fastest decay, primary live sleeve) BEFORE 1h & disk writes
            line_15m = ""
            if getattr(self, "market_15m", None) and "UP_15M" in self.books and "DOWN_15M" in self.books:
                try:
                    m15 = self.market_15m
                    open_15m = float(m15.get("finalized_15m_open", 0.0) or 0.0)
                    auth_cl_15m = float(m15.get("authoritative_chainlink_open", 0.0) or 0.0)
                    cl_spot_15m = float(self.get_chainlink_proxy_spot(t0_sec) or 0.0)
                    t0_15m_secs = (m15["end_dt"] - datetime.now(timezone.utc)).total_seconds()
                    if 0 < t0_15m_secs <= 900.0:
                        if auth_cl_15m > 0.0 and cl_spot_15m > 0.0:
                            dist_15m = ((cl_spot_15m - auth_cl_15m) / auth_cl_15m * 100.0)
                        else:
                            dist_15m = ((self.spot_price - open_15m) / open_15m * 100.0) if open_15m > 0 else 0.0
                        tau_frac_15m = max(0.001, t0_15m_secs / float(m15.get("duration_s", 900.0)))
                        candle_sigma_15m = self.get_rolling_sigma("15m")
                        signed_z_15m = (dist_15m / 100.0) / max(candle_sigma_15m * math.sqrt(tau_frac_15m), 1e-6)
                        up_15_metrics = self.books["UP_15M"].get_metrics(obs_ts=t0_sec, fee_rate=m15.get("fee_metadata", {}).get("fee_rate_market", 0.07))
                        down_15_metrics = self.books["DOWN_15M"].get_metrics(obs_ts=t0_sec, fee_rate=m15.get("fee_metadata", {}).get("fee_rate_market", 0.07))
                        up_15_metrics["token_id"] = m15["tokens"].get("UP")
                        down_15_metrics["token_id"] = m15["tokens"].get("DOWN")
                        shock_id_15m = f"{m15['market_id']}_{t0_sec:.6f}"
                        trigger_15m = {
                            "shock_id": shock_id_15m,
                            "event_id": shock_id_15m,
                            "timestamp": datetime.fromtimestamp(t0_sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "t0_unix": t0_sec,
                            "t0_mono_ns": t0_mono_ns,
                            "t0_definition": "local_receipt_boundary",
                            "exchange_event_ts_ms": event_ts_ms,
                            "clob_ws_connected": bool(getattr(self, "clob_ws_connected", True)),
                            "shock_source": source,
                            "asset": self.asset,
                            "horizon": "15m",
                            "candle_interval": "15m",
                            "series_slug": m15.get("series_slug", f"{self.asset.lower()}-up-or-down-15m"),
                            "slug": m15.get("slug", ""),
                            "resolution_source": m15.get("resolution_source", ""),
                            "market_id": m15["market_id"],
                            "condition_id": m15.get("condition_id", ""),
                            "title": m15["title"],
                            "seconds_to_expiry": round(t0_15m_secs, 1),
                            "expiry_ts": float(m15.get("candle_close_ts") or (t0_sec + t0_15m_secs)),
                            "candle_expiry_ts": float(m15.get("candle_close_ts") or (t0_sec + t0_15m_secs)),
                            "candle_open_ts": int(m15.get("candle_open_ts") or (int(m15["end_dt"].timestamp()) - 900)),
                            "candle_sigma": candle_sigma_15m,
                            "shock_volume_100ms": round(vol_100ms, 0),
                            "is_40ms_fast_track": is_40ms_fast_track,
                            "shock_direction": shock_dir,
                            "btc_shock_direction": btc_lead_dir,
                            "z_val": round(abs(signed_z_15m), 4),
                            "z_score": round(signed_z_15m, 4),
                            "z_btc": z_btc_val,
                            "z_eth": z_eth_val,
                            "shock_ofi": round(ofi, 3),
                            "trigger_price": trigger_px,
                            "spot_at_t0": t0_spot,
                            "futures_at_t0": t0_futures,
                            "basis_signed_bps_t0": round(pre_shock_basis_signed, 2),
                            "basis_abs_bps_t0": round(pre_shock_basis_abs, 2),
                            "delta_basis_100ms": delta_basis_100ms,
                            "coinbase_spot": self.get_coinbase_spot(t0_sec),
                            "chainlink_proxy_spot": self.get_chainlink_proxy_spot(t0_sec),
                            "chainlink_twap_60s": self.get_chainlink_twap_60s(t0_sec),
                            "venue_divergence_bps": self.get_venue_divergence_bps(t0_sec),
                            "venue_divergence_centered_bps": self.get_venue_divergence_centered_bps(t0_sec),
                            "coinbase_move_bps_2s": self.get_coinbase_move_bps(2.0, t0_sec),
                            **cross_fields,
                            "finalized_1h_open": open_15m,
                            "candle_open_spot": open_15m,
                            "twap_60s_open": float(m15.get("twap_60s_open", 0.0) or 0.0) or None,
                            "authoritative_chainlink_open": float(m15.get("authoritative_chainlink_open", 0.0) or 0.0) or None,
                            "chainlink_open_spot": float(m15.get("chainlink_open_spot", 0.0) or 0.0) or None,
                            "candle_distance_pct": round(dist_15m, 4),
                            "fee_metadata": dict(m15.get("fee_metadata", {})),
                            "pre_shock_features_t0": {
                                "UP": up_15_metrics,
                                "DOWN": down_15_metrics
                            }
                        }
                        _, line_15m = _dispatch_trigger_fast(TRIGGER_FILE, trigger_15m)
                except Exception as ex_15m:
                    logger.debug(f"Notice: 15m shock emit skipped: {ex_15m}")

            line_1h = ""
            try:
                _, line_1h = _dispatch_trigger_fast(TRIGGER_FILE, immediate_trigger)
            except Exception as trig_err:
                logger.error(f"Failed to broadcast 1h trigger: {trig_err}")

            if self.asset == "BTC":
                self._publish_btc_lead_state(vol_100ms, ofi, delta_basis_100ms, shock_dir, shock_z, force=True)

            if line_1h:
                try:
                    _persist_trigger_nonblocking(TRIGGER_FILE, line_1h)
                except Exception as trig_err:
                    logger.error(f"Failed to persist zero-latency trigger: {trig_err}")
            if line_15m:
                try:
                    _persist_trigger_nonblocking(TRIGGER_FILE, line_15m)
                except Exception as ex_p15:
                    logger.debug(f"Notice: 15m trigger persist skipped: {ex_p15}")

            log_prefix = "40ms FAST-TRACK" if is_40ms_fast_track else "100ms"
            logger.info(f"\n[!!! {source} SHOCK TRIGGERED ({log_prefix}) !!!] Vol=${vol_100ms:,.0f} | Dir={shock_dir} | "
                        f"OFI={ofi:+.2f} | Spot=${self.spot_price:,.1f} | Fut=${self.futures_price:,.1f} | "
                        f"Basis={self.basis_bps:+.1f}bps | DeltaBasis100ms={delta_basis_100ms:+.1f}bps")

            if len(self.active_burst_tasks) < 5:
                task = asyncio.create_task(self.capture_shock_burst(
                    t0_sec, t0_mono_ns, source, vol_100ms, shock_dir, ofi, trigger_px, delta_basis_100ms,
                    pre_shock_up, pre_shock_down, pre_shock_basis_signed, pre_shock_basis_abs,
                    t0_secs_left, t0_dist_pct, t0_spot, t0_futures, m_id, m_title, fee_meta
                ))
                self.active_burst_tasks.add(task)
                task.add_done_callback(self.active_burst_tasks.discard)
            else:
                logger.warning(f"Concurrent burst tasks throttle reached ({len(self.active_burst_tasks)}). Skipping telemetry capture.")

    async def capture_shock_burst(
        self,
        t0: float,
        t0_mono_ns: int,
        source: str,
        shock_vol: float,
        shock_dir: str,
        ofi: float,
        trigger_px: float,
        delta_basis_100ms: float,
        pre_shock_up: Dict[str, Any],
        pre_shock_down: Dict[str, Any],
        pre_shock_basis_signed: float,
        pre_shock_basis_abs: float,
        t0_secs_left: float,
        t0_dist_pct: float,
        t0_spot: float,
        t0_futures: float,
        m_id: str,
        m_title: str,
        fee_meta: Dict[str, Any]
    ):
        """
        Captures the Probability Repricing Impulse-Response Function IRF(tau) = E[Delta_q(tau)].
        Strict Causal Separation:
          - Predictor features frozen strictly at t <= t0 via deep-copied synchronous snapshot.
          - Repricing measurements occur strictly after t0 + epsilon.
        """
        up_book = self.books.get("UP")
        down_book = self.books.get("DOWN")
        if not up_book or not down_book or not self.current_market:
            return

        ladder_delays = [0.10, 0.15, 0.25, 0.50, 4.0, 25.0]
        ladder_labels = ["100ms", "250ms", "500ms", "1s", "5s", "30s"]
        response_snapshots = {}

        for delay, label in zip(ladder_delays, ladder_labels):
            await asyncio.sleep(delay)
            t_sample = time.time()
            up_m = up_book.get_metrics(obs_ts=t_sample, fee_rate=self.fee_rate_market)
            down_m = down_book.get_metrics(obs_ts=t_sample, fee_rate=self.fee_rate_market)
            response_snapshots[label] = {
                "elapsed_sec": round(t_sample - t0, 3),
                "up_mid": up_m["q_mid"],
                "up_ask": up_m["best_ask"],
                "up_delta_q_ask": round(up_m["best_ask"] - pre_shock_up["best_ask"], 4),
                "up_delta_q_mid": round(up_m["q_mid"] - pre_shock_up["q_mid"], 4),
                "up_obi_l1": up_m["obi_l1"],
                "up_obi_depth": up_m["obi_depth"],
                "down_mid": down_m["q_mid"],
                "down_ask": down_m["best_ask"],
                "down_delta_q_ask": round(down_m["best_ask"] - pre_shock_down["best_ask"], 4),
                "down_delta_q_mid": round(down_m["q_mid"] - pre_shock_down["q_mid"], 4),
                "binance_spot": self.spot_price,
                "binance_futures": self.futures_price,
                "basis_bps": round(self.basis_bps, 2),
                "delta_basis_bps": round(self.basis_bps - pre_shock_basis_signed, 2)
            }

        cond_id = self.current_market.get("condition_id", "") if self.current_market else ""
        shock_record = {
            "timestamp": datetime.fromtimestamp(t0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "t0_unix": t0,
            "t0_mono_ns": t0_mono_ns,
            "shock_source": source,
            "market_id": m_id,
            "condition_id": cond_id,
            "title": m_title,
            "seconds_to_expiry": round(t0_secs_left, 1),
            "shock_volume_100ms": round(shock_vol, 0),
            "shock_direction": shock_dir,
            "shock_ofi": round(ofi, 3),
            "trigger_price": trigger_px,
            "spot_at_t0": t0_spot,
            "futures_at_t0": t0_futures,
            "basis_signed_bps_t0": round(pre_shock_basis_signed, 2),
            "basis_abs_bps_t0": round(pre_shock_basis_abs, 2),
            "delta_basis_100ms": delta_basis_100ms,
            "finalized_1h_open": self.finalized_1h_open,
            "candle_distance_pct": round(t0_dist_pct, 4),
            "fee_metadata": fee_meta,
            "pre_shock_features_t0": {
                "UP": pre_shock_up,
                "DOWN": pre_shock_down
            },
            "impulse_response": response_snapshots,
            "pre_registered_models": {
                "model_a_spot": "Y = f(q_mid, X_spot, TTE, dist)",
                "model_b_futures": "Y = f(q_mid, X_futures, TTE, dist)",
                "model_c_joint": "Y = f(q_mid, X_spot, X_futures, basis, delta_basis, TTE, dist)",
                "model_d_incremental": "Y = f(q_mid, X_spot, TTE, dist) + g(X_futures | X_spot) -> test beta_{F|S} = 0",
                "oos_training_invariant": "T_train_end < t0 (model trained strictly on completed prior markets)"
            },
            "clock_metadata": {
                "clock_offset_ms": self.clock_offset_ms,
                "clock_uncertainty_ms": self.clock_uncertainty_ms,
                "timestamp_designation": "exchange_to_local_delta_with_calibrated_offset"
            },
            "statistical_clustering": {
                "cluster_market_hour": m_id,
                "cluster_shock_episode": f"{m_id}_{int(t0)}",
                "variance_estimator": "IRF: shock-episode block bootstrap | Regressions: market-hour cluster-robust SE"
            }
        }

        _atomic_append_jsonl(self.shock_file, json.dumps(shock_record))

        up_30s_delta = response_snapshots["30s"]["up_delta_q_ask"]
        age_up_val = float(pre_shock_up.get("age_ask_ms") or 0.0)
        logger.info(f"[SHOCK BURST CAPTURED] Market {m_id} | Source={source} | "
                    f"AgeAsk(UP)={age_up_val:.0f}ms | UP ask={pre_shock_up['best_ask']:.3f} -> 30s Delta: {up_30s_delta:+.3f} | "
                    f"Basis={pre_shock_basis_signed:+.1f}bps (Observational episode, not yet evidence of persistent structural lag)")

    async def stream_polymarket_clob(self):
        """Streams real-time L2 orderbook updates from Polymarket CLOB WebSocket with strict market_id rollover binding."""
        while self.running:
            if not self.current_market:
                await asyncio.sleep(0.5)
                continue

            subscribed_market = self.current_market
            subscribed_market_id = str(subscribed_market["market_id"])
            subscribed_end_dt = subscribed_market["end_dt"]
            up_token = str(subscribed_market["tokens"]["UP"])
            down_token = str(subscribed_market["tokens"]["DOWN"])
            # Preserve existing 1H L2OrderBook across 15m rollovers so age_ask_ms is not reset to 0ms
            if "UP" not in self.books or getattr(self.books["UP"], "token_id", None) != up_token:
                self.books["UP"] = L2OrderBook(up_token)
            if "DOWN" not in self.books or getattr(self.books["DOWN"], "token_id", None) != down_token:
                self.books["DOWN"] = L2OrderBook(down_token)

            subscribed_tokens: Dict[str, str] = {up_token: "UP", down_token: "DOWN"}
            for hz, attr_n, up_k, dn_k in (
                ("5m", "market_5m", "UP_5M", "DOWN_5M"),
                ("15m", "market_15m", "UP_15M", "DOWN_15M"),
                ("4h", "market_4h", "UP_4H", "DOWN_4H"),
            ):
                if not getattr(self, attr_n, None):
                    try:
                        setattr(self, attr_n, await self.discover_nearest_twap_market(hz))
                    except Exception:
                        pass
                mh = getattr(self, attr_n, None)
                if mh and "tokens" in mh:
                    up_h = str(mh["tokens"]["UP"])
                    dn_h = str(mh["tokens"]["DOWN"])
                    if up_k not in self.books or getattr(self.books[up_k], "token_id", None) != up_h:
                        self.books[up_k] = L2OrderBook(up_h)
                    if dn_k not in self.books or getattr(self.books[dn_k], "token_id", None) != dn_h:
                        self.books[dn_k] = L2OrderBook(dn_h)
                    subscribed_tokens[up_h] = up_k
                    subscribed_tokens[dn_h] = dn_k

            try:
                sub_assets = list(subscribed_tokens.keys())
                logger.info(
                    f"Connecting to Polymarket CLOB WS ({CLOB_WS_URL}) for market {subscribed_market_id} "
                    f"tokens ({list(subscribed_tokens.values())})..."
                )
                # Proactively seed any empty L2OrderBook from REST /book so SHM never has one-sided books
                try:
                    session = await self.get_session()
                    for tok_id, role_name in subscribed_tokens.items():
                        bk_obj = self.books.get(role_name)
                        if bk_obj is not None and (not bk_obj.bids or not bk_obj.asks):
                            async with session.get(f"https://clob.polymarket.com/book?token_id={tok_id}", timeout=2.0) as r_bk:
                                if r_bk.status == 200:
                                    b_json = await r_bk.json()
                                    if isinstance(b_json, dict):
                                        bk_obj.apply_snapshot(b_json.get("bids", []), b_json.get("asks", []))
                except Exception as seed_err:
                    logger.debug(f"Initial REST book seed notice: {seed_err}")

                async with websockets.connect(CLOB_WS_URL, ping_interval=20, ping_timeout=10) as ws:
                    sub_msg = {"assets_ids": sub_assets, "type": "market"}
                    await ws.send(json.dumps(sub_msg))
                    logger.info(f"[+] Subscribed to Polymarket L2 orderbooks for market {subscribed_market_id}.")
                    self._reconnect_clob = False
                    last_ws_msg_ts = time.time()
                    self.clob_ws_connected = True
                    self.last_clob_ws_msg_ts = last_ws_msg_ts

                    while self.running:
                        now_utc = datetime.now(timezone.utc)
                        # Check against the BOUND market's expiry AND detect if telemetry_logger_loop rotated current_market
                        if (
                            (subscribed_end_dt - now_utc).total_seconds() <= 0
                            or not self.current_market
                            or str(self.current_market.get("market_id")) != subscribed_market_id
                            or getattr(self, "_reconnect_clob", False)
                        ):
                            logger.info(
                                f"[*] Market {subscribed_market_id} expired or rotated to "
                                f"{(self.current_market or {}).get('market_id')}. Re-subscribing CLOB WS immediately."
                            )
                            self.clob_ws_connected = False
                            break

                        # Check if any 5m, 15m, or 4h TWAP market reached expiry
                        expired_twap = False
                        for hz, attr_n, up_k, dn_k in (
                            ("5m", "market_5m", "UP_5M", "DOWN_5M"),
                            ("15m", "market_15m", "UP_15M", "DOWN_15M"),
                            ("4h", "market_4h", "UP_4H", "DOWN_4H"),
                        ):
                            mh = getattr(self, attr_n, None)
                            if mh and (mh["end_dt"] - now_utc).total_seconds() <= 0:
                                logger.info(f"[*] {hz.upper()} Market {mh['market_id']} reached expiry. Cycling to next.")
                                asyncio.create_task(self.verify_and_log_resolution(mh))
                                setattr(self, attr_n, None)
                                self.books.pop(up_k, None)
                                self.books.pop(dn_k, None)
                                expired_twap = True
                        if expired_twap:
                            self.clob_ws_connected = False
                            break

                        if time.time() - last_ws_msg_ts > 25.0:
                            logger.warning(f"[*] CLOB WS silent for >25s on market {subscribed_market_id}. Reconnecting...")
                            self.clob_ws_connected = False
                            break

                        try:
                            msg_str = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            last_ws_msg_ts = time.time()
                            self.last_clob_ws_msg_ts = last_ws_msg_ts
                        except asyncio.TimeoutError:
                            self._maybe_emit_boundary_lock_trigger()
                            continue

                        data = _orjson.loads(msg_str) if _orjson is not None else json.loads(msg_str)
                        if isinstance(data, list):
                            for item in data:
                                asset_id = str(item.get("asset_id") or "")
                                role = subscribed_tokens.get(asset_id)
                                if role and role in self.books:
                                    self.books[role].apply_snapshot(item.get("bids", []), item.get("asks", []))
                        elif isinstance(data, dict):
                            event_type = data.get("event_type")
                            if event_type == "price_change":
                                pcs_by_role = defaultdict(list)
                                for pc in data.get("price_changes", []):
                                    role = subscribed_tokens.get(str(pc.get("asset_id") or ""))
                                    if role:
                                        pcs_by_role[role].append(pc)
                                for role, pcs in pcs_by_role.items():
                                    if role in self.books:
                                        self.books[role].apply_price_changes(pcs)
                            elif event_type == "book":
                                asset_id = str(data.get("asset_id") or "")
                                role = subscribed_tokens.get(asset_id)
                                if role and role in self.books:
                                    self.books[role].apply_snapshot(data.get("bids", []), data.get("asks", []))

                        # HIGH-02: single 25ms-throttled writer (complete schema incl. raw_top_bids/asks).
                        self._maybe_write_fast_tick()
                        self._maybe_emit_boundary_lock_trigger()
            except Exception as e:
                self.clob_ws_connected = False
                logger.warning(f"Polymarket CLOB WS disconnected: {e}. Reconnecting in 1s...")
                await asyncio.sleep(1.0)

    def _maybe_emit_boundary_lock_trigger(self) -> None:
        """Rank #4: Emits a BOUNDARY_LOCK trigger when TTE in [12s, 75s], |z_strike| >= 3.0, and discounted retail asks (<=0.94) offer >=2.5c net edge."""
        if self.spot_price <= 0:
            return
        now_sec = time.time()
        if now_sec - getattr(self, "_last_boundary_check_ts", 0.0) < 0.25:
            return
        self._last_boundary_check_ts = now_sec
        cooldowns = getattr(self, "_boundary_lock_cooldowns", None)
        if cooldowns is None:
            cooldowns = {}
            self._boundary_lock_cooldowns = cooldowns

        now_utc = datetime.now(timezone.utc)
        candidates = []
        if self.current_market and self.finalized_1h_open > 0 and "UP" in self.books and "DOWN" in self.books:
            candidates.append((self.current_market, float(self.finalized_1h_open), "UP", "DOWN", "1h", 3600.0))
        if getattr(self, "market_15m", None) and "UP_15M" in self.books and "DOWN_15M" in self.books:
            open_15m = float(self.market_15m.get("finalized_15m_open", 0.0) or 0.0)
            if open_15m > 0:
                candidates.append((self.market_15m, open_15m, "UP_15M", "DOWN_15M", "15m", 900.0))

        for mkt, open_px, up_key, down_key, horizon, dur_s in candidates:
            m_id = str(mkt.get("market_id") or "")
            if not m_id or (now_sec - cooldowns.get(m_id, 0.0)) < 15.0:
                continue
            secs_left = (mkt["end_dt"] - now_utc).total_seconds()
            if not (12.0 <= secs_left <= 75.0):
                continue
            dist_pct = ((self.spot_price - open_px) / open_px) * 100.0
            min_req_dist = 0.08 if horizon == "15m" else 0.12
            if abs(dist_pct) < min_req_dist:
                continue
            sigma = (0.0035 if self.asset == "BTC" else 0.0050) if horizon == "15m" else (0.0050 if self.asset == "BTC" else 0.0075)
            tau_frac = max(0.001, secs_left / dur_s)
            signed_z = (dist_pct / 100.0) / max(sigma * math.sqrt(tau_frac), 1e-6)
            if abs(signed_z) < 3.0:
                continue

            win_side = "UP" if dist_pct > 0 else "DOWN"
            win_book = self.books[up_key if win_side == "UP" else down_key]
            if not win_book.asks or not win_book.bids:
                continue
            best_ask = min(win_book.asks.keys())
            if not (0.62 <= best_ask <= 0.94):
                continue
            fee_meta = dict(mkt.get("fee_metadata", {}))
            fee_rate = float(fee_meta.get("fee_rate_market", self.fee_rate_market) or 0.07)
            fee_per_share = fee_rate * best_ask * (1.0 - best_ask)
            net_edge = (1.0 - best_ask) - fee_per_share
            if net_edge < 0.025:
                continue

            cooldowns[m_id] = now_sec
            up_m = self.books[up_key].get_metrics(obs_ts=now_sec, fee_rate=fee_rate)
            down_m = self.books[down_key].get_metrics(obs_ts=now_sec, fee_rate=fee_rate)
            up_m["token_id"] = mkt["tokens"].get("UP")
            down_m["token_id"] = mkt["tokens"].get("DOWN")
            shock_dir = "BUY" if win_side == "UP" else "SELL"
            shock_id = f"BOUNDARY_{m_id}_{now_sec:.6f}"
            cross_fields = self._read_cross_asset_fields(now_sec, signed_z, shock_dir) if hasattr(self, "_read_cross_asset_fields") else {}
            trig = {
                "shock_id": shock_id,
                "event_id": shock_id,
                "timestamp": datetime.fromtimestamp(now_sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "t0_unix": now_sec,
                "t0_mono_ns": time.monotonic_ns(),
                "t0_definition": "boundary_lock_scanner",
                "shock_source": "BOUNDARY_LOCK",
                "regime_override": "REGIME_D_BOUNDARY_LOCK",
                "asset": self.asset,
                "horizon": horizon,
                "candle_interval": horizon,
                "series_slug": mkt.get("series_slug", self.series_slug),
                "slug": mkt.get("slug", ""),
                "market_id": m_id,
                "condition_id": mkt.get("condition_id", ""),
                "title": mkt.get("title", ""),
                "seconds_to_expiry": round(secs_left, 1),
                "expiry_ts": float(mkt.get("candle_close_ts") or (now_sec + secs_left)),
                "candle_expiry_ts": float(mkt.get("candle_close_ts") or (now_sec + secs_left)),
                "candle_open_ts": int(mkt.get("candle_open_ts") or (int(mkt["end_dt"].timestamp()) - int(dur_s))),
                "candle_sigma": sigma,
                "shock_volume_100ms": 2_000_000.0,
                "is_40ms_fast_track": True,
                "shock_direction": shock_dir,
                "btc_shock_direction": shock_dir if self.asset == "BTC" else cross_fields.get("btc_shock_direction", shock_dir),
                "z_val": round(abs(signed_z), 4),
                "z_score": round(signed_z, 4),
                "z_btc": round(signed_z, 4) if self.asset == "BTC" else cross_fields.get("z_btc", round(signed_z, 4)),
                "z_eth": round(signed_z, 4) if self.asset == "ETH" else None,
                "p_model": 0.985,
                "shock_ofi": 0.90 if win_side == "UP" else -0.90,
                "trigger_price": self.spot_price,
                "spot_at_t0": self.spot_price,
                "futures_at_t0": self.futures_price or self.spot_price,
                "basis_signed_bps_t0": round(self.basis_bps, 2),
                "basis_abs_bps_t0": round(abs(self.basis_bps), 2),
                "delta_basis_100ms": max(0.0, self.get_delta_basis_100ms()) if win_side == "UP" else min(0.0, self.get_delta_basis_100ms()),
                "coinbase_spot": self.get_coinbase_spot(now_sec),
                "chainlink_proxy_spot": self.get_chainlink_proxy_spot(now_sec),
                "chainlink_twap_60s": self.get_chainlink_twap_60s(now_sec),
                "resolution_source": mkt.get("resolution_source", ""),
                "authoritative_chainlink_open": mkt.get("authoritative_chainlink_open") if horizon == "15m" else None,
                "venue_divergence_bps": self.get_venue_divergence_bps(now_sec),
                "coinbase_move_bps_2s": self.get_coinbase_move_bps(2.0, now_sec),
                "finalized_1h_open": open_px,
                "candle_open_spot": open_px,
                "candle_distance_pct": round(dist_pct, 4),
                "fee_metadata": fee_meta,
                "pre_shock_features_t0": {"UP": up_m, "DOWN": down_m},
            }
            try:
                _, line_bl = _dispatch_trigger_fast(TRIGGER_FILE, trig)
                if line_bl:
                    _persist_trigger_nonblocking(TRIGGER_FILE, line_bl)
                logger.info(
                    f"[BOUNDARY LOCK TRIGGER] {self.asset} ({horizon}) {win_side} | TTE={secs_left:.1f}s | "
                    f"z={signed_z:+.2f} | dist={dist_pct:+.2f}% | BestAsk=${best_ask:.3f} | NetEdge=+{net_edge*100:.2f}c"
                )
            except Exception as e:
                logger.debug(f"Boundary lock emit error: {e}")

    def compute_leadlag_cross_correlation(self, spot_trades=None, futures_trades=None):
        """
        Pre-registered Lead/Lag cross-correlation estimation:
          Estimates Corr(epsilon_F(t), epsilon_S(t + Delta)) over Delta in CORRELATION_LAGS_MS
          using flow innovations (Point 2: do not perform primary lead/lag on raw levels).

        `spot_trades` / `futures_trades` are optional list snapshots taken on the event-loop thread
        (the live deques are mutated by WS coroutines, so iterating them from a worker thread can
        raise "deque mutated during iteration"). Defaults to the live deques for backward compatibility.
        """
        if spot_trades is None:
            spot_trades = self.spot_trades
        if futures_trades is None:
            futures_trades = self.futures_trades
        if len(spot_trades) < 200 or len(futures_trades) < 200:
            return

        now_ns = time.monotonic_ns()
        window_ns = 300_000_000_000  # 5-minute rolling analysis window
        t_start_ns = now_ns - window_ns

        # Bin signed order flow into 25ms time buckets
        bucket_size_ns = 25_000_000
        num_buckets = int(window_ns // bucket_size_ns)
        spot_bins = np.zeros(num_buckets, dtype=np.float64)
        fut_bins = np.zeros(num_buckets, dtype=np.float64)

        for t_mono, _, _, ntl, buyer, _ in spot_trades:
            if t_mono >= t_start_ns:
                idx = min(int((t_mono - t_start_ns) // bucket_size_ns), num_buckets - 1)
                spot_bins[idx] += (ntl if buyer else -ntl)

        for t_mono, _, _, ntl, buyer, _ in futures_trades:
            if t_mono >= t_start_ns:
                idx = min(int((t_mono - t_start_ns) // bucket_size_ns), num_buckets - 1)
                fut_bins[idx] += (ntl if buyer else -ntl)

        # De-autocorrelate: compute first-difference flow innovations epsilon_t = flow_t - flow_{t-1}
        spot_innovations = np.diff(spot_bins)
        fut_innovations = np.diff(fut_bins)

        corrs = {}
        for lag_ms in CORRELATION_LAGS_MS:
            shift_buckets = int(lag_ms * 1_000_000 / bucket_size_ns)
            if shift_buckets == 0:
                s = spot_innovations
                f = fut_innovations
            elif shift_buckets > 0:
                f = fut_innovations[:-shift_buckets]
                s = spot_innovations[shift_buckets:]
            else:
                shift = abs(shift_buckets)
                f = fut_innovations[shift:]
                s = spot_innovations[:-shift]

            if len(s) > 10 and np.std(s) > 1e-6 and np.std(f) > 1e-6:
                corr_val = float(np.corrcoef(f, s)[0, 1])
                corrs[str(lag_ms)] = round(corr_val, 4)
            else:
                corrs[str(lag_ms)] = 0.0

        max_lag = max(corrs.items(), key=lambda x: x[1]) if corrs else ("0", 0.0)

        record = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "timestamp_unix": time.time(),
            "market_id": self.current_market["market_id"] if self.current_market else "none",
            "correlation_grid_lags_ms": corrs,
            "peak_correlation_lag_ms": int(max_lag[0]),
            "peak_correlation_val": max_lag[1],
            "metric_evaluated": "flow_innovations_cross_correlation (diff(signed_dollar_flow_25ms))",
            "telemetry_classification": "illustrative live telemetry, not evidence of persistent lead/lag",
            "null_hypothesis": "H0: no stable lead/lag structure across pre-registered grid",
            "clock_metadata": {
                "calibrated_offset_ms": self.clock_offset_ms,
                "clock_uncertainty_ms": self.clock_uncertainty_ms,
                "resolution_caveat": "Lags <= 50ms are within RTT uncertainty (+/-21.6ms) and must be evaluated strictly under pooled bootstrap bands."
            }
        }

        _atomic_append_jsonl(self.correlations_file, _dumps_compact(record), broadcast_ipc=False)

        logger.info(f"[LEAD/LAG INNOVATION TELEMETRY] Peak Lag: {max_lag[0]}ms (r={max_lag[1]:+.3f}) | Status: Illustrative telemetry (H0: no stable lead/lag)")

    async def telemetry_logger_loop(self):
        """Periodic 10s baseline telemetry logger, cross-correlation estimator, and rollover manager."""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                if not self.current_market or (self.current_market["end_dt"] - now).total_seconds() <= 0:
                    expired_market = self.current_market
                    if expired_market:
                        # Ground truth verification of finalized candle
                        asyncio.create_task(self.verify_and_log_resolution(expired_market))

                    market = getattr(self, "_cached_next_market", None)
                    if not market or (expired_market and market.get("market_id") == expired_market.get("market_id")):
                        market = await self.discover_nearest_1h_market()
                    self._cached_next_market = None

                    if market:
                        self.current_market = market
                        open_px, _ = await self.fetch_finalized_binance_candle(market["candle_open_ts"])
                        self.twap_60s_1h_open = await self.fetch_binance_60s_twap_open(market["candle_open_ts"])
                        self.chainlink_1h_open = (
                            await self.fetch_polygon_chainlink_spot()
                            if abs(time.time() - float(market["candle_open_ts"])) <= 35.0
                            else 0.0
                        )
                        self._open_1h_provisional = False
                        if open_px <= 0.0 and self.spot_price > 0.0:
                            open_px = self.spot_price
                            self._open_1h_provisional = True
                        self.finalized_1h_open = open_px
                        logger.info(f"\n==============================================================================="
                                    f"\n[ACTIVE 1H PRODUCT LOADED: {self.asset}] {market['title']}"
                                    f"\n  Market ID: {market['market_id']} | End: {market['end_date_iso']}"
                                    f"\n  UP Token: {market['tokens']['UP']}"
                                    f"\n  DOWN Token: {market['tokens']['DOWN']}"
                                    f"\n  Binance Spot 1H Finalized Open: ${self.finalized_1h_open:,.2f}"
                                    f"\n  Fee Rate: {self.fee_rate_market * 100:.1f}% ({self.fee_source})"
                                    f"\n===============================================================================\n")

                # Pillar 5B: Discover, refresh, and lock Chainlink opens for 5m, 15m, and 4h TWAP markets
                for hz, attr_n in (("5m", "market_5m"), ("15m", "market_15m"), ("4h", "market_4h")):
                    mh_cur = getattr(self, attr_n, None)
                    if not mh_cur or (mh_cur["end_dt"] - now).total_seconds() <= 0:
                        if mh_cur and (mh_cur["end_dt"] - now).total_seconds() <= 0:
                            asyncio.create_task(self.verify_and_log_resolution(mh_cur))
                        try:
                            mh_new = await self.discover_nearest_twap_market(hz)
                            if mh_new:
                                prev_id = mh_cur.get("market_id") if mh_cur else None
                                setattr(self, attr_n, mh_new)
                                mh_cur = mh_new
                                if mh_new.get("market_id") != prev_id:
                                    logger.info(
                                        f"[ACTIVE {hz.upper()} PRODUCT LOADED: {self.asset}] {mh_new['title']} "
                                        f"(ID: {mh_new['market_id']}, Open: ${mh_new.get('finalized_open', 0.0):,.4f})"
                                    )
                                    self._reconnect_clob = True
                        except Exception as e:
                            logger.debug(f"{hz} discovery cycle note: {e}")

                if self.current_market and (self.finalized_1h_open <= 0.0 or getattr(self, "_open_1h_provisional", False)):
                    open_px, _ = await self.fetch_finalized_binance_candle(self.current_market["candle_open_ts"])
                    if open_px > 0.0:
                        self.finalized_1h_open = open_px
                        self._open_1h_provisional = False
                        if float(getattr(self, "twap_60s_1h_open", 0.0) or 0.0) <= 0.0:
                            self.twap_60s_1h_open = await self.fetch_binance_60s_twap_open(self.current_market["candle_open_ts"])
                        logger.info(f"[{self.asset} FINALIZED OPEN RECOVERED] Binance Spot 1H Open: ${self.finalized_1h_open:,.2f}")

                now_ts_int = int(datetime.now(timezone.utc).timestamp())
                for hz, attr_n, dur_s in (("5m", "market_5m", 300), ("15m", "market_15m", 900), ("4h", "market_4h", 14400)):
                    mh = getattr(self, attr_n, None)
                    if not mh:
                        continue
                    open_ts_h = int(mh.get("candle_open_ts", 0))
                    if now_ts_int < open_ts_h:
                        continue
                    if float(mh.get("finalized_open") or mh.get("finalized_15m_open") or 0.0) <= 0.0 or mh.get("_provisional_open", False):
                        open_h_px, _ = await self.fetch_finalized_binance_candle(open_ts_h, interval=hz)
                        if open_h_px > 0.0:
                            mh["finalized_open"] = open_h_px
                            mh["finalized_15m_open"] = open_h_px
                            mh["_provisional_open"] = False
                        elif float(mh.get("finalized_open") or 0.0) <= 0.0 and self.spot_price > 0.0:
                            mh["finalized_open"] = self.spot_price
                            mh["finalized_15m_open"] = self.spot_price
                            mh["_provisional_open"] = True
                    if float(mh.get("twap_60s_open") or 0.0) <= 0.0:
                        twap_h_px = await self.fetch_binance_60s_twap_open(open_ts_h)
                        if twap_h_px > 0.0:
                            mh["twap_60s_open"] = twap_h_px
                    if float(mh.get("authoritative_chainlink_open") or 0.0) <= 0.0:
                        close_ts_h = int(mh.get("candle_close_ts", open_ts_h + dur_s))
                        if (now_ts_int - float(mh.get("_last_auth_open_try", 0.0))) >= 5.0:
                            mh["_last_auth_open_try"] = float(now_ts_int)
                            auth_px = await self.fetch_authoritative_chainlink_open(open_ts_h, close_ts_h, horizon=hz)
                            if auth_px > 0.0:
                                mh["authoritative_chainlink_open"] = auth_px
                                mh["chainlink_open_spot"] = auth_px
                                logger.info(f"[{self.asset} {hz.upper()} AUTHORITATIVE CHAINLINK OPEN LOCKED] Polymarket openPrice: ${auth_px:,.6f}")

                if self.current_market and "UP" in self.books and "DOWN" in self.books:
                    now_ts_u = round(now.timestamp(), 3)
                    up_metrics = self.books["UP"].get_metrics(fee_rate=self.fee_rate_market, compact=True)
                    down_metrics = self.books["DOWN"].get_metrics(fee_rate=self.fee_rate_market, compact=True)
                    secs_left = (self.current_market["end_dt"] - now).total_seconds()

                    # Upgrade 4: Proactive pre-warming at TTE <= 120s: pre-fetch next candle market
                    if 0 < secs_left <= 120.0 and getattr(self, "_prewarmed_market_id", None) != self.current_market["market_id"]:
                        self._prewarmed_market_id = self.current_market["market_id"]
                        logger.info(f"[PREWARM TTE={secs_left:.0f}s] Pre-fetching next 1H market from Gamma API to eliminate :00 open delay...")
                        try:
                            prewarmed = await self.discover_nearest_1h_market()
                            if prewarmed and prewarmed["market_id"] != self.current_market["market_id"]:
                                self._cached_next_market = prewarmed
                                logger.info(f"[PREWARM READY] Next market pre-cached: {prewarmed['title']} ({prewarmed['market_id']}).")
                        except Exception as e:
                            logger.debug(f"Prewarm error: {e}")
                    dist_pct = ((self.spot_price - self.finalized_1h_open) / self.finalized_1h_open * 100.0) if self.finalized_1h_open > 0 else 0.0

                    delta_basis_100ms = self.get_delta_basis_100ms()
                    bbo_1h = (
                        self.current_market["market_id"],
                        up_metrics["best_bid"],
                        up_metrics["best_ask"],
                        down_metrics["best_bid"],
                        down_metrics["best_ask"],
                    )
                    prev_1h = self._last_telem_bbo_by_hz.get("1h")
                    if (
                        prev_1h is None
                        or prev_1h[1] != bbo_1h
                        or secs_left <= 900.0
                        or (now_ts_u - prev_1h[0]) >= 19.0
                    ):
                        self._last_telem_bbo_by_hz["1h"] = (now_ts_u, bbo_1h)
                        record = {
                            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "timestamp_unix": now_ts_u,
                            "asset": self.asset,
                            "market_id": self.current_market["market_id"],
                            "title": self.current_market["title"],
                            "seconds_to_expiry": round(secs_left, 1),
                            "binance_spot": self.spot_price,
                            "binance_futures": self.futures_price,
                            "basis_signed_usd": round(self.basis_usd, 2),
                            "basis_signed_bps": round(self.basis_bps, 2),
                            "basis_abs_bps": round(abs(self.basis_bps), 2),
                            "delta_basis_100ms": delta_basis_100ms,
                            "binance_1h_open": self.finalized_1h_open,
                            "candle_distance_pct": round(dist_pct, 4),
                            "clock_metadata": {
                                "clock_offset_ms": round(self.clock_offset_ms, 2),
                                "clock_uncertainty_ms": round(self.clock_uncertainty_ms, 2),
                            },
                            "fee_metadata": {"fee_rate_market": self.fee_rate_market},
                            "UP": up_metrics,
                            "DOWN": down_metrics,
                        }
                        _atomic_append_jsonl(self.telemetry_file, _dumps_compact(record), broadcast_ipc=False)

                    cb_now = self.get_coinbase_spot(now_ts_u)
                    cl_now = self.get_chainlink_proxy_spot(now_ts_u)
                    for hz, attr_n, up_k, dn_k, out_f in (
                        ("5m", "market_5m", "UP_5M", "DOWN_5M", self.telemetry_5m_file),
                        ("15m", "market_15m", "UP_15M", "DOWN_15M", self.telemetry_15m_file),
                        ("4h", "market_4h", "UP_4H", "DOWN_4H", self.telemetry_4h_file),
                    ):
                        mh = getattr(self, attr_n, None)
                        if mh and up_k in self.books and dn_k in self.books:
                            secs_h = (mh["end_dt"] - now).total_seconds()
                            if secs_h > 0:
                                f_h = float(mh.get("fee_metadata", {}).get("fee_rate_market", 0.07) or 0.07)
                                uph_m = self.books[up_k].get_metrics(fee_rate=f_h, compact=True)
                                dnh_m = self.books[dn_k].get_metrics(fee_rate=f_h, compact=True)
                                bbo_h = (
                                    mh["market_id"],
                                    uph_m["best_bid"],
                                    uph_m["best_ask"],
                                    dnh_m["best_bid"],
                                    dnh_m["best_ask"],
                                )
                                prev_h = self._last_telem_bbo_by_hz.get(hz)
                                if hz == "4h" and secs_h > 1800.0 and prev_h is not None and prev_h[1] == bbo_h and (now_ts_u - prev_h[0]) < 58.0:
                                    continue
                                if hz == "15m" and secs_h > 360.0 and prev_h is not None and prev_h[1] == bbo_h and (now_ts_u - prev_h[0]) < 28.0:
                                    continue
                                self._last_telem_bbo_by_hz[hz] = (now_ts_u, bbo_h)
                                open_h = float(mh.get("finalized_open") or mh.get("finalized_15m_open") or 0.0)
                                auth_cl_h = mh.get("authoritative_chainlink_open")
                                usd_ref_h = cl_now if cl_now > 0 else cb_now
                                dist_h = ((self.spot_price - open_h) / open_h * 100.0) if open_h > 0 else 0.0
                                cl_dist_h = (
                                    round(((usd_ref_h - float(auth_cl_h)) / float(auth_cl_h)) * 100.0, 4)
                                    if auth_cl_h and float(auth_cl_h) > 0 and usd_ref_h > 0
                                    else None
                                )
                                rec_h: Dict[str, Any] = {
                                    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                                    "timestamp_unix": now_ts_u,
                                    "asset": self.asset,
                                    "horizon": hz,
                                    "market_id": mh["market_id"],
                                    "title": mh["title"],
                                    "seconds_to_expiry": round(secs_h, 1),
                                    "binance_spot": self.spot_price,
                                    "binance_futures": self.futures_price,
                                    "coinbase_usd_spot": round(cb_now, 6) if cb_now > 0 else 0.0,
                                    "chainlink_proxy_usd_spot": round(cl_now, 6) if cl_now > 0 else 0.0,
                                    "binance_open": open_h,
                                    "candle_distance_pct": round(dist_h, 4),
                                    "fee_metadata": {"fee_rate_market": f_h},
                                    "UP": uph_m,
                                    "DOWN": dnh_m,
                                }
                                if hz == "15m":
                                    rec_h["binance_15m_open"] = open_h
                                twap_h = mh.get("twap_60s_open")
                                if twap_h is not None:
                                    rec_h["twap_60s_open"] = twap_h
                                if auth_cl_h is not None:
                                    rec_h["authoritative_chainlink_open"] = auth_cl_h
                                if cl_dist_h is not None:
                                    rec_h["chainlink_usd_distance_pct"] = cl_dist_h
                                _atomic_append_jsonl(out_f, _dumps_compact(rec_h), broadcast_ipc=False)

                    logger.info(
                        f"[1H TELEMETRY: {self.asset}] {self.current_market['title'][:32]} | Tau: {secs_left/60.0:.1f}m ({secs_left:.0f}s) | "
                        f"UP ask={up_metrics['best_ask']:.3f} (mid={up_metrics['q_mid']:.3f}, hurdle={up_metrics['executable_hurdle']:.4f}) | "
                        f"Spot=${self.spot_price:,.1f} | Fut=${self.futures_price:,.1f} | Basis={self.basis_bps:+.1f}bp | dist={dist_pct:+.2f}%"
                    )

                # Periodic 60s cross-correlation estimation on flow innovations (offloaded from WS event loop)
                if time.time() - self.last_cross_corr_ts > 60.0:
                    self.last_cross_corr_ts = time.time()
                    # Snapshot deques on the loop thread (WS coroutines mutate them concurrently)
                    spot_snap = list(self.spot_trades)
                    fut_snap = list(self.futures_trades)
                    await asyncio.to_thread(self.compute_leadlag_cross_correlation, spot_snap, fut_snap)

                # Periodic 300s clock synchronization
                if time.time() - self.last_clock_sync_ts > 300.0:
                    asyncio.create_task(self.calibrate_binance_clock_offset())

                await asyncio.sleep(10.0)
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}", exc_info=True)
                await asyncio.sleep(10.0)

    async def run(self):
        logger.info("===============================================================================")
        logger.info(f"   ROUTE 3: FUTURES/SPOT -> POLYMARKET 1H RECORDER ({self.asset}) (v2.8)       ")
        logger.info(f"   Asset: {self.asset} | Binance: {self.binance_symbol} | Shock: ${self.shock_threshold_usd:,.0f} ")
        logger.info("   Dual Feeds: Binance Spot (Settlement Ref) + Futures (Routed /market)        ")
        logger.info("   Invariants: OBI/q_micro Reconciled + Invariant Assertions Enforced          ")
        logger.info("   Quote Ages: Tripartite (Age_book, Age_bid, Age_ask)                         ")
        logger.info("   Clock Sync: Cristian's Algorithm Calibrated Offset (Tokyo <-> Binance)      ")
        logger.info("   Econometrics: Strict Causal t0 Anchor + Lead/Lag Innovation Grid            ")
        logger.info("   Capacity Surface: Fill-Level Fees & Crossing Cost [$1, $5, $20, $50, $100]  ")
        logger.info("   Resolution Truth: Finalized Binance Spot 1H Candle Open & Close             ")
        logger.info("   Operational: Read-Only (Does not circumvent geographic restrictions)        ")
        logger.info("===============================================================================")

        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        # Initial clock offset calibration
        await self.calibrate_binance_clock_offset()

        await asyncio.gather(
            self.stream_binance_spot(),
            self.stream_binance_futures(),
            self.stream_polymarket_clob(),
            self.telemetry_logger_loop(),
            self._coinbase_stream_worker(),
        )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Polymarket Dual Feed 1H Telemetry Recorder")
    parser.add_argument(
        "--asset",
        choices=list(ASSET_CONFIGS.keys()),
        default="BTC",
        help=f"Asset to record ({', '.join(ASSET_CONFIGS.keys())}, default: BTC)",
    )
    parser.add_argument("--shock-threshold", type=float, default=None, help="Volume shock threshold in USD over 100ms")
    args = parser.parse_args()

    setup_logging(args.asset)
    if os.name != "nt":
        try:
            import uvloop
            uvloop.install()
        except Exception:
            pass
    recorder = PolymarketDualFeed1HRecorder(asset=args.asset, shock_threshold=args.shock_threshold)
    try:
        asyncio.run(recorder.run())
    except KeyboardInterrupt:
        recorder.running = False
        logger.info("Stopped by user.")
