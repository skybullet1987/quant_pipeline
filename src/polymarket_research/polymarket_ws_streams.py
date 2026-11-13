#!/usr/bin/env python3
"""
polymarket_ws_streams.py
========================
Low-latency real-time WebSocket stream hub for Polymarket live execution & alpha discovery:
  1. PolymarketUserWsCache:
     Authenticated L2 User WebSocket (`wss://ws-subscriptions-clob.polymarket.com/ws/user`)
     tracking live open orders, deterministic order fill/cancel state transitions, and
     confirmed share deltas with <5 ms event wakeups (cutting REST `/data/orders` polling >85%).
  2. PolymarketChainlinkLiveStream:
     Real-time Chainlink Data Streams feed (`wss://ws-live-data.polymarket.com`,
     topic `crypto_prices_chainlink`) capturing 18-decimal 1Hz USD ticks across
     `BTC, ETH, SOL, XRP, BNB, DOGE, HYPE` for instant 0s candle-boundary 60s-TWAP
     strikes and continuous `S2_EXACT_TWAP_LOCK` path-integral tracking.
  3. PolymarketClobMarketWsTracker:
     Dynamic CLOB Market L2 WebSocket (`wss://ws-subscriptions-clob.polymarket.com/ws/market`)
     watching active Harvester position tokens (`D1`, `C1`, `M3`, `N1`, `4h`, `5m`) and firing
     an immediate wakeup when a winning leg's bid crosses the `$0.985-$0.99` cash-recycle trigger.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import socket
import threading
import time
from collections import deque
from decimal import Decimal
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Set, Tuple


def _enable_ws_nodelay(ws: Any) -> bool:
    try:
        tr = getattr(ws, "transport", None)
        sock = tr.get_extra_info("socket") if tr is not None else None
        if sock is not None:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            return True
    except Exception:
        pass
    return False

try:
    import orjson as _orjson
except ImportError:
    _orjson = None  # type: ignore

logger = logging.getLogger("PolymarketWSStreams")

import os
from pathlib import Path

USER_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
MARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
CLOB_MARKET_WS_URL = MARKET_WS_URL
LIVE_DATA_WS_URL = "wss://ws-live-data.polymarket.com"
POLYBOLT_V2_WS_URL = "wss://ws-live-v2.polymarket.com/ws"
PERPS_WS_URL = "wss://ws.perpetuals.polymarket.com/v1/ws"

POLYBOLT_CRYPTO_SYMBOLS: Tuple[str, ...] = (
    "btcusd",
    "ethusd",
    "solusd",
    "xrpusd",
    "dogeusd",
    "bnbusd",
    "zecusd",
    "hypeusd",
    "xauusd",
    "xagusd",
)

POLYBOLT_EQUITY_SYMBOLS: Tuple[str, ...] = (
    "SPY",
    "QQQ",
    "NVDA",
    "TSLA",
    "AAPL",
    "MSFT",
    "META",
    "AMZN",
    "GOOGL",
    "NFLX",
    "PLTR",
    "HOOD",
    "COIN",
)

OPEN_ORDER_STATUSES = {"LIVE", "OPEN", "DELAYED", "UNMATCHED"}
TERMINAL_CANCEL_STATUSES = {"CANCELED", "CANCELLED", "EXPIRED", "REJECTED", "CANCELLATION"}
TERMINAL_FILL_STATUSES = {"MATCHED", "FILLED"}

CHAINLINK_SYMBOL_MAP: Dict[str, str] = {
    "btc/usd": "BTC",
    "eth/usd": "ETH",
    "sol/usd": "SOL",
    "xrp/usd": "XRP",
    "bnb/usd": "BNB",
    "doge/usd": "DOGE",
    "zec/usd": "ZEC",
    "hype/usd": "HYPE",
    "xau/usd": "XAU",
    "xag/usd": "XAG",
    "btcusd": "BTC",
    "ethusd": "ETH",
    "solusd": "SOL",
    "xrpusd": "XRP",
    "bnbusd": "BNB",
    "dogeusd": "DOGE",
    "zecusd": "ZEC",
    "hypeusd": "HYPE",
    "xauusd": "XAU",
    "xagusd": "XAG",
}

_CACHED_POLYBOLT_CREDS: Optional[Tuple[str, str, str]] = None
_CREDS_LOCK = threading.Lock()


def invalidate_polybolt_l2_creds() -> None:
    global _CACHED_POLYBOLT_CREDS
    with _CREDS_LOCK:
        _CACHED_POLYBOLT_CREDS = None


def resolve_polybolt_l2_creds(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    api_passphrase: Optional[str] = None,
    *,
    force_refresh: bool = False,
    stale_creds: Optional[Tuple[str, str, str]] = None,
) -> Optional[Tuple[str, str, str]]:
    """
    Resolves Polymarket CLOB L2 `(api_key, api_secret, api_passphrase)` for PolyBolt V2 authentication:
      1. Explicit arguments if supplied
      2. Explicit environment variables (`POLY_API_KEY` / `CLOB_API_KEY`, etc., loading `.env` if present)
      3. Deterministic L2 derivation from `POLYGON_PRIVATE_KEY` via `ClobClient.create_or_derive_api_creds()`
    """
    global _CACHED_POLYBOLT_CREDS
    ak = str(api_key or "").strip()
    sec = str(api_secret or "").strip()
    pp = str(api_passphrase or "").strip()
    if ak and sec and pp:
        return (ak, sec, pp)
    with _CREDS_LOCK:
        if force_refresh:
            _CACHED_POLYBOLT_CREDS = None
        if _CACHED_POLYBOLT_CREDS is not None:
            return _CACHED_POLYBOLT_CREDS
        try:
            from dotenv import load_dotenv

            repo_env = Path(__file__).resolve().parents[2] / ".env"
            if repo_env.exists():
                load_dotenv(repo_env, override=bool(force_refresh))
        except Exception:
            pass
        ak = (os.environ.get("POLY_API_KEY") or os.environ.get("CLOB_API_KEY") or "").strip()
        sec = (
            os.environ.get("POLY_SECRET")
            or os.environ.get("POLY_API_SECRET")
            or os.environ.get("CLOB_SECRET")
            or ""
        ).strip()
        pp = (
            os.environ.get("POLY_PASSPHRASE")
            or os.environ.get("POLY_API_PASSPHRASE")
            or os.environ.get("CLOB_PASS_PHRASE")
            or ""
        ).strip()
        env_creds = (ak, sec, pp) if (ak and sec and pp) else None
        if env_creds is not None and (not force_refresh or env_creds != stale_creds):
            _CACHED_POLYBOLT_CREDS = env_creds
            return _CACHED_POLYBOLT_CREDS
        pk = (os.environ.get("POLYGON_PRIVATE_KEY") or os.environ.get("POLY_PRIVATE_KEY") or "").strip()
        if pk and os.environ.get("PM_DISABLE_POLYBOLT_CRED_DERIVE", "0") != "1":
            try:
                from py_clob_client.client import ClobClient

                funder = (
                    os.environ.get("POLYGON_FUNDER_ADDRESS")
                    or os.environ.get("POLYGON_PROXY_ADDRESS")
                    or None
                )
                sig_type = int(os.environ.get("POLYGON_SIGNATURE_TYPE") or 1)
                c = ClobClient(
                    "https://clob.polymarket.com",
                    key=pk,
                    chain_id=137,
                    signature_type=sig_type,
                    funder=funder,
                )
                creds = c.create_or_derive_api_creds()
                d_ak = str(getattr(creds, "api_key", "") or "").strip()
                d_sec = str(getattr(creds, "api_secret", "") or "").strip()
                d_pp = str(getattr(creds, "api_passphrase", "") or "").strip()
                if d_ak and d_sec and d_pp:
                    _CACHED_POLYBOLT_CREDS = (d_ak, d_sec, d_pp)
                    return _CACHED_POLYBOLT_CREDS
            except Exception as exc:
                logger.debug(f"[POLYBOLT-V2] L2 credential derivation skipped: {exc}")
        if env_creds is not None:
            _CACHED_POLYBOLT_CREDS = env_creds
            return _CACHED_POLYBOLT_CREDS
        return None


def _loads(raw: Any) -> Any:
    if _orjson is not None and isinstance(raw, (bytes, bytearray, str)):
        return _orjson.loads(raw)
    return json.loads(raw)


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val in (None, ""):
        return default
    try:
        out = float(val)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


class PolymarketUserWsCache:
    """
    Thread-safe authenticated CLOB User WebSocket cache (`ws/user`).
    Maintains open-order snapshots, per-order matched share totals, and token activity timestamps,
    with strict fail-closed REST fallback whenever the socket is disconnected or unseeded.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        api_passphrase: str,
        *,
        ws_url: str = USER_WS_URL,
        on_fill_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self._api_key = str(api_key or "").strip()
        self._api_secret = str(api_secret or "").strip()
        self._api_passphrase = str(api_passphrase or "").strip()
        self._ws_url = ws_url
        self._on_fill_callback = on_fill_callback

        self._lock = threading.RLock()
        self._state_cv = threading.Condition(self._lock)
        self._stop_event = threading.Event()
        self._fill_event = threading.Event()
        self._async_waiters: List[Tuple[asyncio.AbstractEventLoop, asyncio.Event]] = []
        self._thread: Optional[threading.Thread] = None

        self._connected = False
        self._connected_since_mono = 0.0
        self._last_rx_mono = 0.0
        self._seeded_since_connect = False
        self._last_rest_seed_mono = 0.0

        self._open_orders: Dict[str, Dict[str, Any]] = {}
        self._orders_by_id: Dict[str, Dict[str, Any]] = {}
        self._seen_trade_stages: Dict[Tuple[str, str], float] = {}
        self._token_last_fill_ts: Dict[str, float] = {}
        self._confirmed_token_deltas: Dict[str, float] = {}
        self._fill_seq = 0

    def start(self) -> bool:
        if not (self._api_key and self._api_secret and self._api_passphrase):
            return False
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return True
            self._stop_event.clear()
            t = threading.Thread(target=self._run_thread, name="pm-user-ws", daemon=True)
            self._thread = t
            t.start()
            return True

    def stop(self) -> None:
        self._stop_event.set()
        self._fill_event.set()
        with self._lock:
            self._state_cv.notify_all()
        self._notify_async_waiters()

    def _notify_async_waiters(self) -> None:
        with self._lock:
            if not self._async_waiters:
                return
            waiters = list(self._async_waiters)
            self._async_waiters.clear()
        for loop, ev in waiters:
            try:
                if not loop.is_closed():
                    loop.call_soon_threadsafe(ev.set)
            except Exception:
                pass

    def is_healthy(self, max_silence_sec: float = 25.0) -> bool:
        with self._lock:
            if not self._connected:
                return False
            return (time.monotonic() - self._last_rx_mono) <= max_silence_sec

    @property
    def fill_sequence(self) -> int:
        with self._lock:
            return self._fill_seq

    def seed_open_orders(self, orders: List[Dict[str, Any]]) -> None:
        """Seeds authoritative open-order baseline from a REST `get_open_orders` response."""
        now_m = time.monotonic()
        with self._lock:
            new_open: Dict[str, Dict[str, Any]] = {}
            for raw in orders or ():
                if not isinstance(raw, dict):
                    continue
                oid = str(raw.get("id") or raw.get("orderID") or "").strip()
                if not oid:
                    continue
                rec = dict(raw)
                rec.setdefault("id", oid)
                new_open[oid] = rec
                self._orders_by_id[oid] = {**rec, "_updated_mono": now_m}
            self._open_orders = new_open
            self._last_rest_seed_mono = now_m
            if self._connected:
                self._seeded_since_connect = True

    def get_open_orders_snapshot(self, max_age_sec: float = 15.0) -> Optional[List[Dict[str, Any]]]:
        """
        Returns cached open orders ONLY when the WS session is live, active, AND seeded within
        `max_age_sec` (preserving periodic REST reconciliation while eliminating >85% of polls).
        """
        now_m = time.monotonic()
        with self._lock:
            if (
                not self._connected
                or not self._seeded_since_connect
                or (now_m - self._last_rx_mono) > 22.0
                or (now_m - self._last_rest_seed_mono) > max_age_sec
            ):
                return None
            return [dict(v) for v in self._open_orders.values()]

    def get_order_snapshot(self, order_id: str, max_age_sec: float = 8.0) -> Optional[Dict[str, Any]]:
        oid = str(order_id or "").strip()
        if not oid:
            return None
        now_m = time.monotonic()
        with self._lock:
            if not self._connected or (now_m - self._last_rx_mono) > 22.0:
                return None
            rec = self._orders_by_id.get(oid)
            if not isinstance(rec, dict):
                return None
            upd_m = float(rec.get("_updated_mono", 0.0) or 0.0)
            if self._connected_since_mono > 0.0 and upd_m < self._connected_since_mono and not self._seeded_since_connect:
                return None
            if (now_m - upd_m) > max_age_sec:
                return None
            out = dict(rec)
            out.pop("_updated_mono", None)
            return out

    def wait_for_order_terminal_sync(
        self,
        order_id: str,
        timeout_sec: float = 0.035,
        max_age_sec: float = 10.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Blocks synchronously up to `timeout_sec` (<0.2ms condvar wakeup on `/ws/user` frame)
        for `order_id` to reach a terminal state (`CANCELED`, `CANCELLED`, `MATCHED`, `FILLED`, `INVALID`).
        Returns the latest fresh snapshot (terminal or non-terminal), or None if WS is unhealthy/unknown.
        """
        oid = str(order_id or "").strip()
        if not oid:
            return None
        deadline = time.monotonic() + max(0.0, float(timeout_sec))
        with self._lock:
            if not self._connected or (time.monotonic() - self._last_rx_mono) > 22.0:
                return None
            while True:
                now_m = time.monotonic()
                rec = self._orders_by_id.get(oid)
                if isinstance(rec, dict):
                    upd_m = float(rec.get("_updated_mono", 0.0) or 0.0)
                    fresh_ok = not (
                        self._connected_since_mono > 0.0
                        and upd_m < self._connected_since_mono
                        and not self._seeded_since_connect
                    ) and (now_m - upd_m) <= max_age_sec
                    if fresh_ok:
                        st = str(rec.get("status") or "").strip().upper()
                        orig_sz = _safe_float(rec.get("original_size"), 0.0)
                        matched_sz = _safe_float(rec.get("size_matched"), 0.0)
                        is_term = (
                            st in TERMINAL_CANCEL_STATUSES
                            or (st == "INVALID" and matched_sz <= 1e-6)
                            or (
                                st in TERMINAL_FILL_STATUSES
                                and (orig_sz <= 0.0 or matched_sz >= orig_sz - 1e-4)
                            )
                        )
                        if is_term:
                            out = dict(rec)
                            out.pop("_updated_mono", None)
                            return out
                rem = deadline - time.monotonic()
                if rem <= 0.0 or self._stop_event.is_set() or not self._connected:
                    break
                self._state_cv.wait(timeout=rem)
            return self.get_order_snapshot(oid, max_age_sec=max_age_sec)

    def has_token_fill_since(self, token_id: str, since_unix_ts: float) -> bool:
        tok = str(token_id or "").strip()
        if not tok:
            return False
        with self._lock:
            last_ts = float(self._token_last_fill_ts.get(tok, 0.0) or 0.0)
            return last_ts >= (float(since_unix_ts) - 0.5)

    async def wait_for_fill_or_timeout(self, timeout_sec: float, prev_seq: Optional[int] = None) -> int:
        """Waits asynchronously (<0.1ms event-driven wakeup) for the next user WS fill/order wakeup or `timeout_sec`."""
        deadline = time.monotonic() + max(0.001, float(timeout_sec))
        base_seq = self.fill_sequence if prev_seq is None else int(prev_seq)
        loop = asyncio.get_running_loop()
        while True:
            ev = asyncio.Event()
            with self._lock:
                cur_seq = self._fill_seq
                if cur_seq != base_seq or self._stop_event.is_set():
                    return cur_seq
                self._async_waiters.append((loop, ev))
            rem = deadline - time.monotonic()
            if rem <= 0.0:
                with self._lock:
                    try:
                        self._async_waiters.remove((loop, ev))
                    except ValueError:
                        pass
                    return self._fill_seq
            try:
                await asyncio.wait_for(ev.wait(), timeout=rem)
            except asyncio.TimeoutError:
                with self._lock:
                    try:
                        self._async_waiters.remove((loop, ev))
                    except ValueError:
                        pass
                    return self._fill_seq

    def process_ws_payload(self, raw_payload: Any, now_unix: Optional[float] = None) -> int:
        """Parses a raw or decoded WS message (public for deterministic unit testing)."""
        now_u = float(time.time() if now_unix is None else now_unix)
        now_m = time.monotonic()
        if raw_payload in (None, "", b"", "PONG", b"PONG"):
            with self._lock:
                self._last_rx_mono = now_m
            return 0
        try:
            data = _loads(raw_payload) if isinstance(raw_payload, (str, bytes, bytearray)) else raw_payload
        except Exception:
            return 0

        items = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        events_applied = 0
        fire_callbacks: List[Dict[str, Any]] = []

        with self._lock:
            self._last_rx_mono = now_m
            if len(self._orders_by_id) > 600:
                cutoff = now_m - 600.0
                for k_old, v_old in list(self._orders_by_id.items()):
                    if k_old not in self._open_orders and float(v_old.get("_updated_mono", 0.0)) < cutoff:
                        self._orders_by_id.pop(k_old, None)
            if len(self._seen_trade_stages) > 1000:
                t_cut = now_m - 600.0
                self._seen_trade_stages = {k: ts for k, ts in self._seen_trade_stages.items() if ts >= t_cut}

            for item in items:
                if not isinstance(item, dict):
                    continue
                ev_type = str(item.get("event_type") or item.get("type") or "").strip().lower()
                if ev_type == "order" or ("original_size" in item and ("id" in item or "orderID" in item)):
                    oid = str(item.get("id") or item.get("orderID") or "").strip()
                    if not oid:
                        continue
                    msg_type = str(item.get("type") or "").strip().upper()
                    status = str(item.get("status") or "").strip().upper()
                    if not status:
                        if msg_type == "CANCELLATION":
                            status = "CANCELED"
                        elif msg_type in ("PLACEMENT", "UPDATE"):
                            status = "LIVE"
                    prev_rec = self._orders_by_id.get(oid)
                    prev_st = str((prev_rec or {}).get("status") or "").strip().upper()
                    prev_matched = _safe_float((prev_rec or {}).get("size_matched"), 0.0)
                    orig_sz = _safe_float(item.get("original_size") or item.get("size"), _safe_float((prev_rec or {}).get("original_size"), 0.0))
                    matched_sz = max(prev_matched, _safe_float(item.get("size_matched") or item.get("matched_size"), 0.0))
                    ord_type = str(item.get("order_type") or (prev_rec or {}).get("order_type") or "").strip().upper()
                    if status in TERMINAL_FILL_STATUSES and orig_sz > 0.0 and matched_sz < orig_sz - 1e-6 and ord_type not in ("FAK", "FOK") and msg_type != "CANCELLATION":
                        status = "LIVE"
                    prev_term_fill = prev_st in TERMINAL_FILL_STATUSES and (orig_sz <= 0.0 or prev_matched >= orig_sz - 1e-6 or ord_type in ("FAK", "FOK"))
                    if prev_st in TERMINAL_CANCEL_STATUSES or prev_term_fill:
                        status = prev_st
                    elif orig_sz > 0.0 and matched_sz >= orig_sz - 1e-6 and status not in TERMINAL_CANCEL_STATUSES:
                        status = "MATCHED"
                    norm = {
                        **(prev_rec or {}),
                        **item,
                        "id": oid,
                        "orderID": oid,
                        "status": status or "LIVE",
                        "original_size": orig_sz,
                        "size_matched": matched_sz,
                        "_updated_mono": now_m,
                    }
                    self._orders_by_id[oid] = norm
                    if msg_type == "CANCELLATION" or status in TERMINAL_CANCEL_STATUSES or status in TERMINAL_FILL_STATUSES or status == "INVALID":
                        self._open_orders.pop(oid, None)
                    elif status in OPEN_ORDER_STATUSES:
                        clean_open = dict(norm)
                        clean_open.pop("_updated_mono", None)
                        self._open_orders[oid] = clean_open
                    if matched_sz > 0.0:
                        aid = str(item.get("asset_id") or norm.get("asset_id") or "").strip()
                        if aid:
                            self._token_last_fill_ts[aid] = now_u
                    self._fill_seq += 1
                    self._fill_event.set()
                    events_applied += 1

                elif ev_type == "trade" or ("taker_order_id" in item and "status" in item):
                    tr_id = str(item.get("id") or item.get("trade_id") or "").strip()
                    tr_status = str(item.get("status") or "").strip().upper()
                    if not tr_id or not tr_status:
                        continue
                    stage_key = (tr_id, tr_status)
                    if stage_key in self._seen_trade_stages:
                        continue
                    self._seen_trade_stages[stage_key] = now_m

                    top_aid = str(item.get("asset_id") or "").strip()
                    top_side = str(item.get("side") or "").strip().upper()
                    top_sz = _safe_float(item.get("size"), 0.0)
                    trader_side = str(item.get("trader_side") or "").strip().upper()
                    maker_list = [mo for mo in (item.get("maker_orders") or ()) if isinstance(mo, dict)]
                    attrib_legs: List[Tuple[str, str, float]] = []
                    if trader_side == "MAKER" and maker_list:
                        matched_mos = [
                            mo for mo in maker_list
                            if str(mo.get("order_id") or "").strip() in self._orders_by_id
                            or (self._api_key and str(mo.get("api_key") or "").strip() == self._api_key)
                        ] or (maker_list if len(maker_list) == 1 else [])
                        for mo in matched_mos:
                            mo_oid = str(mo.get("order_id") or "").strip()
                            prev_mo = self._orders_by_id.get(mo_oid) or {}
                            m_aid = str(mo.get("asset_id") or prev_mo.get("asset_id") or top_aid).strip()
                            m_side = str(mo.get("side") or prev_mo.get("side") or top_side).strip().upper()
                            m_sz = _safe_float(mo.get("matched_amount") or mo.get("size"), top_sz if len(matched_mos) == 1 else 0.0)
                            if m_aid and m_sz > 0.0:
                                attrib_legs.append((m_aid, m_side, m_sz))
                    elif trader_side != "TAKER" and maker_list:
                        for mo in maker_list:
                            mo_oid = str(mo.get("order_id") or "").strip()
                            if mo_oid and mo_oid in self._orders_by_id and mo_oid != str(item.get("taker_order_id") or "").strip():
                                prev_mo = self._orders_by_id.get(mo_oid) or {}
                                m_aid = str(mo.get("asset_id") or prev_mo.get("asset_id") or top_aid).strip()
                                m_side = str(mo.get("side") or prev_mo.get("side") or top_side).strip().upper()
                                m_sz = _safe_float(mo.get("matched_amount") or mo.get("size"), top_sz if len(maker_list) == 1 else 0.0)
                                if m_aid and m_sz > 0.0:
                                    attrib_legs.append((m_aid, m_side, m_sz))
                    if not attrib_legs and top_aid and top_sz > 0.0:
                        attrib_legs.append((top_aid, top_side, top_sz))

                    if tr_status in ("MATCHED", "MINED", "CONFIRMED"):
                        for l_aid, _, _ in attrib_legs:
                            self._token_last_fill_ts[l_aid] = now_u
                        if tr_status in ("MINED", "CONFIRMED") and (tr_id, "DELTA_APPLIED") not in self._seen_trade_stages:
                            self._seen_trade_stages[(tr_id, "DELTA_APPLIED")] = now_m
                            for l_aid, l_side, l_sz in attrib_legs:
                                signed_sh = l_sz if l_side == "BUY" else -l_sz
                                self._confirmed_token_deltas[l_aid] = self._confirmed_token_deltas.get(l_aid, 0.0) + signed_sh
                    elif tr_status == "FAILED" and (tr_id, "DELTA_APPLIED") in self._seen_trade_stages and (tr_id, "DELTA_REVERTED") not in self._seen_trade_stages:
                        self._seen_trade_stages[(tr_id, "DELTA_REVERTED")] = now_m
                        for l_aid, l_side, l_sz in attrib_legs:
                            signed_sh = l_sz if l_side == "BUY" else -l_sz
                            self._confirmed_token_deltas[l_aid] = self._confirmed_token_deltas.get(l_aid, 0.0) - signed_sh

                    taker_oid = str(item.get("taker_order_id") or "").strip()
                    matched_sz_by_oid: Dict[str, float] = {}
                    if taker_oid and top_sz > 0.0:
                        matched_sz_by_oid[taker_oid] = top_sz
                    for mo in maker_list:
                        mo_oid = str(mo.get("order_id") or "").strip()
                        if mo_oid:
                            mo_sz = _safe_float(mo.get("matched_amount") or mo.get("size"), top_sz if len(maker_list) == 1 else 0.0)
                            if mo_sz > 0.0:
                                matched_sz_by_oid[mo_oid] = matched_sz_by_oid.get(mo_oid, 0.0) + mo_sz
                    for oid_ref in [taker_oid] + [str(mo.get("order_id") or "").strip() for mo in maker_list]:
                        if oid_ref:
                            prev_o = self._orders_by_id.get(oid_ref)
                            if isinstance(prev_o, dict):
                                prev_o["_updated_mono"] = now_m
                                prev_o["relayer_trade_status"] = tr_status
                                inc_sz = matched_sz_by_oid.get(oid_ref, 0.0)
                                if tr_id and tr_status in ("MATCHED", "MINED", "CONFIRMED") and inc_sz > 0.0:
                                    t_map = prev_o.setdefault("_trade_fill_by_id", {})
                                    t_map[tr_id] = max(_safe_float(t_map.get(tr_id), 0.0), inc_sz)
                                    trade_sum = sum(float(v) for v in t_map.values())
                                    cur_m = _safe_float(prev_o.get("size_matched"), 0.0)
                                    orig_s = _safe_float(prev_o.get("original_size"), 0.0)
                                    new_m = max(cur_m, min(orig_s, trade_sum) if orig_s > 0.0 else trade_sum)
                                    prev_o["size_matched"] = new_m
                                    if orig_s > 0.0 and new_m >= orig_s - 1e-4:
                                        prev_o["status"] = "MATCHED"
                                elif tr_id and tr_status == "FAILED" and isinstance(prev_o.get("_trade_fill_by_id"), dict):
                                    prev_o["_trade_fill_by_id"].pop(tr_id, None)
                                if tr_status in ("MATCHED", "MINED", "CONFIRMED") and item.get("transaction_hash"):
                                    txs = list(prev_o.get("transactions_hashes") or [])
                                    tx_h = str(item["transaction_hash"])
                                    if tx_h not in txs:
                                        txs.append(tx_h)
                                    prev_o["transactions_hashes"] = txs

                    self._fill_seq += 1
                    self._fill_event.set()
                    events_applied += 1
                    if tr_status in ("MATCHED", "MINED", "CONFIRMED", "FAILED", "RETRYING"):
                        fire_callbacks.append(dict(item))

            if events_applied > 0:
                self._state_cv.notify_all()

        if events_applied > 0:
            self._notify_async_waiters()
        if self._on_fill_callback is not None:
            for ev in fire_callbacks:
                try:
                    self._on_fill_callback(ev)
                except Exception:
                    pass
        return events_applied

    def _run_thread(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._ws_forever())
        finally:
            try:
                loop.close()
            except Exception:
                pass

    async def _user_ping_loop(self, ws: Any, interval_sec: float = 12.0) -> None:
        step_s = max(0.02, min(0.5, interval_sec * 0.25))
        while not self._stop_event.is_set():
            elapsed = 0.0
            while elapsed < interval_sec and not self._stop_event.is_set():
                await asyncio.sleep(min(step_s, interval_sec - elapsed))
                elapsed += step_s
            if self._stop_event.is_set():
                try:
                    await ws.close()
                except Exception:
                    pass
                return
            try:
                await ws.send("PING")
            except Exception:
                return

    async def _ws_forever(self) -> None:
        try:
            import websockets
        except ImportError:
            logger.warning("[USER-WS] websockets package unavailable; falling back to REST.")
            return

        backoff = 0.5
        auth_msg = json.dumps(
            {
                "auth": {
                    "apiKey": self._api_key,
                    "secret": self._api_secret,
                    "passphrase": self._api_passphrase,
                },
                "markets": [],
                "type": "user",
            }
        )
        while not self._stop_event.is_set():
            ping_task: Optional[asyncio.Task[Any]] = None
            try:
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=15,
                    ping_timeout=15,
                    open_timeout=6,
                    close_timeout=3,
                    max_size=4 * 1024 * 1024,
                    max_queue=512,
                    compression=None,
                ) as ws:
                    _enable_ws_nodelay(ws)
                    await ws.send(auth_msg)
                    now_m = time.monotonic()
                    with self._lock:
                        self._connected = True
                        self._connected_since_mono = now_m
                        self._last_rx_mono = now_m
                        self._seeded_since_connect = False
                    backoff = 0.5
                    logger.info("[USER-WS] Authenticated CLOB ws/user stream connected.")
                    ping_task = asyncio.create_task(self._user_ping_loop(ws, interval_sec=12.0))
                    try:
                        rx_to = float(getattr(self, "_rx_timeout_sec", 28.0) or 28.0)
                        while not self._stop_event.is_set():
                            msg = await asyncio.wait_for(ws.recv(), timeout=rx_to)
                            self.process_ws_payload(msg)
                    finally:
                        if ping_task is not None:
                            ping_task.cancel()
                            try:
                                await ping_task
                            except (asyncio.CancelledError, Exception):
                                pass
            except Exception as exc:
                if not self._stop_event.is_set():
                    logger.debug(f"[USER-WS] Reconnecting after notice: {exc}")
            finally:
                with self._lock:
                    self._connected = False
                    self._seeded_since_connect = False
            if not self._stop_event.is_set():
                await asyncio.sleep(min(5.0, backoff + random.uniform(0.0, 0.25)))
                backoff = min(5.0, backoff * 1.7)


class PolymarketChainlinkLiveStream:
    """
    Real-time Polymarket Chainlink Data Streams client supporting PolyBolt V2
    (`wss://ws-live-v2.polymarket.com/ws`, `price.crypto` 120s 1Hz snapshot + live 1Hz ticks)
    with automatic fallback to legacy RTDS (`wss://ws-live-data.polymarket.com`).
    """

    def __init__(
        self,
        *,
        ws_url: str = LIVE_DATA_WS_URL,
        prefer_polybolt_v2: bool = True,
        l2_creds: Optional[Tuple[str, str, str]] = None,
        history_sec: float = 420.0,
        on_tick: Optional[Callable[[str, float, float], None]] = None,
    ) -> None:
        self._ws_url = ws_url
        self._prefer_polybolt_v2 = bool(
            prefer_polybolt_v2 and ws_url in (LIVE_DATA_WS_URL, POLYBOLT_V2_WS_URL)
        )
        self._l2_creds = l2_creds
        self._history_sec = float(history_sec)
        self._on_tick = on_tick
        self._lock = threading.RLock()
        self._ticks: Dict[str, Deque[Tuple[float, float]]] = {
            sym: deque(maxlen=600) for sym in set(CHAINLINK_SYMBOL_MAP.values())
        }
        self._official_twap_ticks: Dict[str, Deque[Tuple[float, float]]] = {
            sym: deque(maxlen=180) for sym in set(CHAINLINK_SYMBOL_MAP.values())
        }
        self._boundary_twaps: Dict[Tuple[str, int], float] = {}
        self._connected = False
        self._last_rx_mono = 0.0
        self._active_source: str = "none"
        self._dropped_frames: int = 0

    @property
    def active_source(self) -> str:
        with self._lock:
            return self._active_source

    def is_healthy(self, max_silence_sec: float = 8.0) -> bool:
        with self._lock:
            return self._connected and (time.monotonic() - self._last_rx_mono) <= max_silence_sec

    def ingest_tick(self, asset: str, ts_sec: float, price_usd: float) -> None:
        sym = str(asset or "").strip().upper()
        if not sym or price_usd <= 0.0 or not math.isfinite(price_usd) or ts_sec <= 0.0:
            return
        with self._lock:
            self._last_rx_mono = time.monotonic()
            dq = self._ticks.setdefault(sym, deque(maxlen=600))
            if dq and abs(ts_sec - dq[-1][0]) < 1e-4:
                dq[-1] = (ts_sec, price_usd)
            elif not dq or ts_sec > dq[-1][0]:
                dq.append((ts_sec, price_usd))
            else:
                pts = sorted(list(dq) + [(ts_sec, price_usd)], key=lambda x: x[0])
                dedup: List[Tuple[float, float]] = []
                for t_x, p_x in pts:
                    if dedup and abs(t_x - dedup[-1][0]) < 1e-4:
                        dedup[-1] = (t_x, p_x)
                    else:
                        dedup.append((t_x, p_x))
                dq.clear()
                dq.extend(dedup[-600:])
            cutoff = ts_sec - self._history_sec
            while dq and dq[0][0] < cutoff:
                dq.popleft()

            b_cand = int(round(ts_sec / 300.0) * 300)
            if 0.0 <= (ts_sec - b_cand) <= 3.0 and (sym, b_cand) not in self._boundary_twaps:
                tw = self._compute_twap_locked(sym, float(b_cand), min_ticks=52)
                if tw is not None:
                    self._boundary_twaps[(sym, b_cand)] = tw
                    if len(self._boundary_twaps) > 140:
                        oldest_k = min(self._boundary_twaps.keys(), key=lambda k: k[1])
                        self._boundary_twaps.pop(oldest_k, None)

        if self._on_tick is not None:
            try:
                self._on_tick(sym, ts_sec, price_usd)
            except Exception:
                pass

    @staticmethod
    def _parse_polybolt_price(item: Dict[str, Any]) -> float:
        full_acc = item.get("full_accuracy_value")
        px = 0.0
        if full_acc not in (None, ""):
            try:
                dec_v = Decimal(str(full_acc))
                # Live PolyBolt V2 `price.crypto` emits unscaled decimal strings (e.g. "80496.97358448358");
                # guard > 1e12 so any 1e18-scaled integer string is also normalized safely.
                if dec_v > Decimal("1e12"):
                    dec_v = dec_v / Decimal("1e18")
                px = float(dec_v)
            except Exception:
                px = 0.0
        if px <= 0.0:
            px = _safe_float(item.get("value"), 0.0)
        return px

    def process_ws_message(self, raw_msg: Any) -> bool:
        if not raw_msg or raw_msg in ("PONG", b"PONG"):
            with self._lock:
                self._last_rx_mono = time.monotonic()
            return False
        try:
            d = _loads(raw_msg) if isinstance(raw_msg, (str, bytes, bytearray)) else raw_msg
        except Exception:
            return False
        if not isinstance(d, dict):
            return False

        # PolyBolt V2 (`wss://ws-live-v2.polymarket.com/ws`) `price.crypto` & `price.equity` frames
        if d.get("channel") in ("price.crypto", "price.equity"):
            dropped = int(d.get("dropped") or 0)
            if dropped > 0:
                with self._lock:
                    self._dropped_frames += dropped
                logger.warning(f"[POLYBOLT-V2] Server reported dropped={dropped} frames on {d.get('channel')}")
                return False
            pl = d.get("payload")
            if not isinstance(pl, dict):
                return False
            raw_sym = str(pl.get("symbol") or "").strip().lower()
            asset = CHAINLINK_SYMBOL_MAP.get(raw_sym) or (
                raw_sym.upper() if raw_sym.upper() in POLYBOLT_EQUITY_SYMBOLS else None
            )
            if not asset:
                return False
            if bool(d.get("snapshot")) or isinstance(pl.get("data"), list):
                ingested = 0
                for pt in pl.get("data") or ():
                    if not isinstance(pt, dict):
                        continue
                    ts_raw = pt.get("timestamp")
                    if ts_raw is None:
                        continue
                    ts_f = _safe_float(ts_raw, 0.0)
                    ts_sec = ts_f / 1000.0 if ts_f > 1e11 else ts_f
                    px = self._parse_polybolt_price(pt)
                    if ts_sec > 0.0 and px > 0.0:
                        self.ingest_tick(asset, ts_sec, px)
                        ingested += 1
                if ingested > 0:
                    with self._lock:
                        self._active_source = "polybolt_v2"
                    return True
                return False
            ts_raw = pl.get("timestamp") if pl.get("timestamp") is not None else d.get("ts")
            if ts_raw is None:
                return False
            ts_f = _safe_float(ts_raw, 0.0)
            ts_sec = ts_f / 1000.0 if ts_f > 1e11 else ts_f
            px = self._parse_polybolt_price(pl)
            if ts_sec <= 0.0 or px <= 0.0:
                return False
            with self._lock:
                self._active_source = "polybolt_v2"
            self.ingest_tick(asset, ts_sec, px)
            return True

        if d.get("op") in ("authed", "subscribed", "pong"):
            with self._lock:
                self._last_rx_mono = time.monotonic()
            return False

        if d.get("topic") not in (
            "crypto_prices_chainlink",
            "crypto_prices_twap_sixty",
            "crypto_prices",
            "equity_prices",
            "forex_prices_chainlink",
            "metals_prices_chainlink",
        ):
            return False
        topic = str(d.get("topic"))
        pl = d.get("payload")
        if not isinstance(pl, dict):
            return False
        raw_sym = str(pl.get("symbol") or "").strip().lower()
        asset = CHAINLINK_SYMBOL_MAP.get(raw_sym) or (
            raw_sym.upper() if (topic == "equity_prices" and raw_sym.upper() in POLYBOLT_EQUITY_SYMBOLS) else None
        )
        if not asset:
            return False
        ts_raw = pl.get("timestamp")
        if ts_raw is None:
            return False
        ts_f = float(ts_raw)
        ts_sec = ts_f / 1000.0 if ts_f > 1e11 else ts_f

        px = self._parse_polybolt_price(pl)
        if px <= 0.0:
            return False
        with self._lock:
            self._active_source = "rtds"
        if topic == "crypto_prices_twap_sixty":
            with self._lock:
                self._last_rx_mono = time.monotonic()
                dq_tw = self._official_twap_ticks.setdefault(asset, deque(maxlen=180))
                dq_tw.append((ts_sec, px))
                b_cand = int(round(ts_sec / 300.0) * 300)
                if 0.0 <= abs(ts_sec - b_cand) <= 1.5:
                    self._boundary_twaps[(asset, b_cand)] = px
            return True
        self.ingest_tick(asset, ts_sec, px)
        return True

    def _compute_twap_locked(self, sym: str, boundary_ts: float, min_ticks: int = 52) -> Optional[float]:
        dq = self._ticks.get(sym)
        if not dq:
            return None
        w_start = boundary_ts - 60.0
        pts = [(t, p) for t, p in dq if (w_start - 0.05) <= t <= (boundary_ts + 0.05)]
        if len(pts) < min_ticks:
            return None
        if (pts[0][0] - w_start) > 3.0 or (boundary_ts - pts[-1][0]) > 2.0:
            return None
        max_gap = max((pts[i + 1][0] - pts[i][0]) for i in range(len(pts) - 1)) if len(pts) >= 2 else 99.0
        if max_gap > 5.0:
            return None
        # Chainlink 60s TWAP stream averages 1Hz ticks across the 60s window (exclude duplicate boundary endpoint if 61 ticks)
        ticks_60 = [p for t, p in pts if (w_start + 0.5) <= t <= (boundary_ts + 0.05)]
        if len(ticks_60) >= min_ticks:
            return sum(ticks_60) / len(ticks_60)
        return sum(p for _, p in pts) / len(pts)

    def get_boundary_twap_60s(self, asset: str, boundary_ts: float, min_ticks: int = 52) -> Optional[float]:
        sym = str(asset or "").strip().upper()
        b_int = int(round(float(boundary_ts)))
        with self._lock:
            cached = self._boundary_twaps.get((sym, b_int))
            if cached is not None:
                return cached
            val = self._compute_twap_locked(sym, float(b_int), min_ticks=min_ticks)
            if val is not None:
                # Only cache once a tick at/after the boundary exists; earlier values may still change.
                dq_b = self._ticks.get(sym)
                if dq_b and float(dq_b[-1][0]) >= float(b_int):
                    self._boundary_twaps[(sym, b_int)] = val
            return val

    def get_latest_spot(self, asset: str, now_ts: Optional[float] = None, max_age_sec: float = 3.0) -> Optional[float]:
        sym = str(asset or "").strip().upper()
        now_f = float(time.time() if now_ts is None else now_ts)
        with self._lock:
            dq = self._ticks.get(sym)
            if not dq:
                return None
            t_last, p_last = dq[-1]
            age = now_f - t_last
            if -2.0 <= age <= max_age_sec:
                return p_last
            return None

    def get_rolling_twap_60s(
        self,
        asset: str,
        now_ts: Optional[float] = None,
        max_age_sec: float = 4.5,
    ) -> Optional[float]:
        """Authoritative 60-second rolling USD TWAP from 1Hz Chainlink reports (warm from t=0s via PolyBolt 120s snapshot)."""
        sym = str(asset or "").strip().upper()
        now_f = float(time.time() if now_ts is None else now_ts)
        with self._lock:
            dq = self._ticks.get(sym)
            if dq:
                t_last, p_last = dq[-1]
                if -2.0 <= (now_f - t_last) <= max_age_sec:
                    pts = [p for t, p in dq if (now_f - 60.0) <= t <= (now_f + 1.0) and p > 0.0]
                    if len(pts) >= 2:
                        return round(sum(pts) / len(pts), 4)
                    return round(p_last, 4)
        return self.get_latest_official_twap_60s(sym, now_ts=now_f, max_age_sec=max_age_sec)

    def get_settlement_twap_slice(
        self,
        asset: str,
        end_ts: float,
        now_ts: Optional[float] = None,
        max_age_sec: float = 4.5,
    ) -> Optional[Tuple[float, float]]:
        """Authoritative `[end_ts - 60, now]` banked 1Hz Chainlink TWAP slice `(mean_usd, locked_weight)`."""
        sym = str(asset or "").strip().upper()
        now_f = float(time.time() if now_ts is None else now_ts)
        rem = float(end_ts) - now_f
        if not (0.0 < rem < 60.0):
            return None
        with self._lock:
            dq = self._ticks.get(sym)
            if not dq:
                return None
            t_last, _ = dq[-1]
            if not (-2.0 <= (now_f - t_last) <= max_age_sec):
                return None
            w0 = float(end_ts) - 60.0
            pts = [p for t, p in dq if (w0 - 0.5) <= t <= (now_f + 0.5) and p > 0.0]
            if not pts:
                return None
            return round(sum(pts) / len(pts), 4), round((60.0 - rem) / 60.0, 4)

    def get_recent_samples(self, asset: str, since_ts: float) -> List[Tuple[float, float]]:
        sym = str(asset or "").strip().upper()
        with self._lock:
            dq = self._ticks.get(sym)
            if not dq:
                return []
            return [(t, p) for t, p in dq if t >= since_ts]

    def _ingest_official_twap(self, raw_sym_or_asset: str, price_usd: float, ts_ms_or_sec: float) -> bool:
        raw_s = str(raw_sym_or_asset or "").strip()
        asset = CHAINLINK_SYMBOL_MAP.get(raw_s.lower()) or raw_s.upper()
        if not asset or float(price_usd) <= 0.0:
            return False
        ts_f = float(ts_ms_or_sec)
        ts_sec = ts_f / 1000.0 if ts_f > 1e11 else ts_f
        with self._lock:
            self._last_rx_mono = time.monotonic()
            dq_tw = self._official_twap_ticks.setdefault(asset, deque(maxlen=180))
            dq_tw.append((ts_sec, float(price_usd)))
            b_cand = int(round(ts_sec / 300.0) * 300)
            if 0.0 <= abs(ts_sec - b_cand) <= 1.5:
                self._boundary_twaps[(asset, b_cand)] = float(price_usd)
        return True

    def get_latest_official_twap_60s(self, asset: str, now_ts: Optional[float] = None, max_age_sec: float = 5.0) -> Optional[float]:
        sym = str(asset or "").strip().upper()
        now_f = float(time.time() if now_ts is None else now_ts)
        with self._lock:
            dq = self._official_twap_ticks.get(sym)
            if not dq:
                return None
            t_last, p_last = dq[-1]
            if -2.0 <= (now_f - t_last) <= max_age_sec:
                return p_last
            return None

    async def _stream_polybolt_v2_once(
        self,
        websockets_mod: Any,
        creds: Tuple[str, str, str],
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> bool:
        pb_url = self._ws_url if self._ws_url == POLYBOLT_V2_WS_URL else POLYBOLT_V2_WS_URL
        ak, sec, pp = creds
        auth_msg = json.dumps(
            {
                "op": "auth",
                "rid": "a1",
                "auth": {"apiKey": ak, "secret": sec, "passphrase": pp},
            }
        )
        got_ticks = False
        async with websockets_mod.connect(
            pb_url,
            ping_interval=12,
            ping_timeout=12,
            open_timeout=6,
            close_timeout=3,
            max_size=4 * 1024 * 1024,
            max_queue=512,
            compression=None,
        ) as ws:
            _enable_ws_nodelay(ws)
            await ws.send(auth_msg)
            auth_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            auth_resp = _loads(auth_raw) if isinstance(auth_raw, (str, bytes, bytearray)) else auth_raw
            if not isinstance(auth_resp, dict) or auth_resp.get("op") != "authed":
                raise RuntimeError(f"PolyBolt V2 auth rejected: {auth_resp}")
            for idx, sym in enumerate(POLYBOLT_CRYPTO_SYMBOLS):
                await ws.send(
                    json.dumps(
                        {
                            "op": "subscribe",
                            "rid": f"s_{idx}",
                            "subscriptions": [{"channel": "price.crypto", "filter": {"symbol": sym}}],
                        }
                    )
                )
            for idx_e, eq_sym in enumerate(POLYBOLT_EQUITY_SYMBOLS):
                await ws.send(
                    json.dumps(
                        {
                            "op": "subscribe",
                            "rid": f"eq_{idx_e}",
                            "subscriptions": [{"channel": "price.equity", "filter": {"symbol": eq_sym}}],
                        }
                    )
                )
            with self._lock:
                self._connected = True
                self._active_source = "polybolt_v2"
                self._last_rx_mono = time.monotonic()
            logger.info(
                f"[CHAINLINK-WS] Connected to PolyBolt V2 1Hz authoritative stream ({len(POLYBOLT_CRYPTO_SYMBOLS)} symbols, 120s snapshot)."
            )
            while not (stop_check and stop_check()):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    if (time.monotonic() - self._last_rx_mono) > 15.0:
                        break
                    continue
                if self.process_ws_message(msg):
                    got_ticks = True
        return got_ticks

    async def _stream_rtds_once(
        self,
        websockets_mod: Any,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> None:
        rtds_url = LIVE_DATA_WS_URL if self._ws_url == POLYBOLT_V2_WS_URL else self._ws_url
        sub_msg = json.dumps(
            {
                "action": "subscribe",
                "subscriptions": [
                    {"topic": "crypto_prices_chainlink", "type": "*", "filters": ""},
                    {"topic": "crypto_prices_twap_sixty", "type": "*", "filters": ""},
                    {"topic": "crypto_prices", "type": "*", "filters": ""},
                    {"topic": "equity_prices", "type": "*", "filters": ""},
                ],
            }
        )
        async with websockets_mod.connect(
            rtds_url,
            ping_interval=12,
            ping_timeout=12,
            open_timeout=6,
            close_timeout=3,
            max_size=2 * 1024 * 1024,
            max_queue=512,
            compression=None,
        ) as ws:
            _enable_ws_nodelay(ws)
            await ws.send(sub_msg)
            with self._lock:
                self._connected = True
                self._active_source = "rtds"
                self._last_rx_mono = time.monotonic()
            logger.info(
                f"[CHAINLINK-WS] Connected to RTDS fallback Chainlink 1Hz stream ({len(set(CHAINLINK_SYMBOL_MAP.values()))} symbols)."
            )
            while not (stop_check and stop_check()):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    if (time.monotonic() - self._last_rx_mono) > 15.0:
                        break
                    continue
                self.process_ws_message(msg)

    async def run_forever(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        try:
            import websockets
        except ImportError:
            logger.warning("[CHAINLINK-WS] websockets unavailable; skipping live Chainlink stream.")
            return
        backoff = 0.5
        creds = self._l2_creds
        force_cred_refresh = False
        while not (stop_check and stop_check()):
            used_pb_ok = False
            if self._prefer_polybolt_v2:
                if creds is None or force_cred_refresh:
                    try:
                        creds = await asyncio.to_thread(
                            resolve_polybolt_l2_creds,
                            force_refresh=force_cred_refresh,
                            stale_creds=creds,
                        )
                    except Exception:
                        creds = None
                    force_cred_refresh = False
                if creds is not None:
                    try:
                        used_pb_ok = await self._stream_polybolt_v2_once(websockets, creds, stop_check)
                        if used_pb_ok:
                            backoff = 0.5
                    except asyncio.CancelledError:
                        break
                    except Exception as exc:
                        err_l = str(exc).lower()
                        if any(k in err_l for k in ("auth", "401", "403", "unauthorized", "forbidden", "invalid api")):
                            invalidate_polybolt_l2_creds()
                            force_cred_refresh = True
                        logger.debug(f"[POLYBOLT-V2] Falling back to RTDS after notice: {exc}")
                    finally:
                        with self._lock:
                            self._connected = False
            if stop_check and stop_check():
                break
            if not used_pb_ok:
                try:
                    await self._stream_rtds_once(websockets, stop_check)
                    backoff = 0.5
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug(f"[CHAINLINK-WS] Reconnecting after notice: {exc}")
                finally:
                    with self._lock:
                        self._connected = False
            if stop_check and stop_check():
                break
            await asyncio.sleep(min(5.0, backoff + random.uniform(0.0, 0.2)))
            backoff = min(5.0, backoff * 1.7)


_SHARED_CHAINLINK_LOCK = threading.RLock()
_SHARED_CHAINLINK_STREAM: Optional[PolymarketChainlinkLiveStream] = None
_SHARED_CHAINLINK_TASK: Optional[asyncio.Task] = None


def get_shared_chainlink_stream() -> PolymarketChainlinkLiveStream:
    global _SHARED_CHAINLINK_STREAM
    with _SHARED_CHAINLINK_LOCK:
        if _SHARED_CHAINLINK_STREAM is None:
            _SHARED_CHAINLINK_STREAM = PolymarketChainlinkLiveStream()
        return _SHARED_CHAINLINK_STREAM


def ensure_shared_chainlink_stream_started() -> PolymarketChainlinkLiveStream:
    global _SHARED_CHAINLINK_TASK
    stream = get_shared_chainlink_stream()
    with _SHARED_CHAINLINK_LOCK:
        if _SHARED_CHAINLINK_TASK is None or _SHARED_CHAINLINK_TASK.done():
            try:
                loop = asyncio.get_running_loop()
                _SHARED_CHAINLINK_TASK = loop.create_task(stream.run_forever())
            except RuntimeError:
                pass
    return stream


class PolymarketClobMarketWsTracker:
    """
    Lightweight dynamic CLOB Market L2 WebSocket watcher for active Harvester positions.
    Eliminates 1s REST `/book` polling lag for `D1`, `C1`, `M3`, `N1`, `4h`, and `5m` positions,
    and fires an immediate wakeup when a winning position's bid reaches `>= $0.985` for instant
    pre-expiry capital recycling.
    """

    def __init__(
        self,
        *,
        ws_url: str = MARKET_WS_URL,
        recycle_bid_trigger: float = 0.985,
        on_urgent_bid: Optional[Callable[[str, float], None]] = None,
        on_book_change: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tick_size_change: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        self._ws_url = ws_url
        self._recycle_bid_trigger = float(recycle_bid_trigger)
        self._on_urgent_bid = on_urgent_bid
        self._on_book_change = on_book_change
        self._on_tick_size_change = on_tick_size_change
        self._lock = threading.RLock()
        self._desired_tokens: Set[str] = set()
        self._desired_tokens_ordered: List[str] = []
        self._books: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._raw_levels: Dict[str, Tuple[Dict[float, float], Dict[float, float]]] = {}
        self._numeric_books: Dict[str, Tuple[float, List[Tuple[float, float]], List[Tuple[float, float]]]] = {}
        self._dirty_tokens: Set[str] = set()
        self._last_rx_by_aid: Dict[str, float] = {}
        self._lifecycle_events: Deque[Dict[str, Any]] = deque(maxlen=256)
        self._snapshot_tokens: Set[str] = set()
        self._tick_sizes: Dict[str, float] = {}
        self._sub_wakeup: Optional[asyncio.Event] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_connected: bool = False
        self._connected_since_mono: float = 0.0
        self._last_ws_rx_mono: float = 0.0

    _FROZEN_KMIA_IDS = frozenset({"6707503", "6707502"})

    def drain_lifecycle_events(self, max_items: int = 64) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        with self._lock:
            while self._lifecycle_events and len(out) < max_items:
                out.append(self._lifecycle_events.popleft())
        return out

    def get_tick_size(self, token_id: str) -> Optional[float]:
        tok = str(token_id or "").strip()
        if not tok:
            return None
        with self._lock:
            return self._tick_sizes.get(tok)

    def set_desired_tokens(self, tokens: Iterable[str]) -> None:
        ordered: List[str] = []
        seen_c: Set[str] = set()
        for t in tokens:
            s = str(t or "").strip()
            if len(s) >= 15 and s.isdigit() and s not in seen_c:
                seen_c.add(s)
                ordered.append(s)
                if len(ordered) >= 490:
                    break
        clean = set(ordered)
        added = False
        with self._lock:
            if clean == self._desired_tokens and ordered == self._desired_tokens_ordered:
                return
            if clean - self._desired_tokens:
                added = True
            self._desired_tokens_ordered = ordered
            self._desired_tokens = clean
            for stale in list(set(self._books.keys()) | set(self._last_rx_by_aid.keys())):
                if stale not in clean:
                    self._books.pop(stale, None)
                    self._raw_levels.pop(stale, None)
                    self._numeric_books.pop(stale, None)
                    self._dirty_tokens.discard(stale)
                    self._last_rx_by_aid.pop(stale, None)
                    self._snapshot_tokens.discard(stale)
        if added:
            self._signal_sub_wakeup()

    def subscribe_tokens_immediate(self, tokens: Iterable[str]) -> None:
        urgent = [str(t).strip() for t in tokens if t and len(str(t).strip()) >= 15 and str(t).strip().isdigit()]
        if not urgent:
            return
        added = False
        with self._lock:
            if set(urgent) - self._desired_tokens:
                added = True
            prev_ord = getattr(self, "_desired_tokens_ordered", None) or sorted(self._desired_tokens)
            merged = list(dict.fromkeys(urgent + list(prev_ord)))[:490]
            self._desired_tokens_ordered = merged
            self._desired_tokens = set(merged)
        if added:
            self._signal_sub_wakeup()

    def _signal_sub_wakeup(self) -> None:
        ev = self._sub_wakeup
        lp = self._loop
        if ev is not None and lp is not None and not lp.is_closed():
            try:
                lp.call_soon_threadsafe(ev.set)
            except Exception:
                pass

    def _materialize_book_locked(self, aid: str, build_dict: bool = True) -> Optional[Dict[str, Any]]:
        lvls = self._raw_levels.get(aid)
        now_m = self._last_rx_by_aid.get(aid, time.monotonic())
        if lvls is None:
            entry = self._books.get(aid)
            return entry[1] if entry is not None else None
        b_map, a_map = lvls
        num_entry = self._numeric_books.get(aid)
        if aid in self._dirty_tokens or num_entry is None:
            b_tups = sorted(
                ((px, sz) for px, sz in b_map.items() if px > 0.0 and sz > 0.0),
                key=lambda kv: -kv[0],
            )[:15]
            a_tups = sorted(
                ((px, sz) for px, sz in a_map.items() if px > 0.0 and sz > 0.0),
                key=lambda kv: kv[0],
            )[:15]
            self._numeric_books[aid] = (now_m, b_tups, a_tups)
            self._dirty_tokens.discard(aid)
        else:
            _, b_tups, a_tups = num_entry
        if not build_dict:
            return None
        bk_dict: Dict[str, Any] = {
            "asset_id": aid,
            "bids": [{"price": f"{px:.4f}", "size": f"{sz:.4f}"} for px, sz in b_tups],
            "asks": [{"price": f"{px:.4f}", "size": f"{sz:.4f}"} for px, sz in a_tups],
            "is_partial_delta": (aid not in self._snapshot_tokens),
        }
        if aid in self._tick_sizes:
            bk_dict["minimum_tick_size"] = self._tick_sizes[aid]
        self._books[aid] = (now_m, bk_dict)
        return bk_dict

    def _is_live_quiet_book_fresh_locked(self, tok: str, eff_ts: Optional[float], now_m: float, max_age_sec: float) -> bool:
        if eff_ts is None:
            return False
        age_s = now_m - eff_ts
        if age_s <= max_age_sec:
            return True
        return (
            self._ws_connected
            and tok in self._snapshot_tokens
            and tok in self._desired_tokens
            and eff_ts >= self._connected_since_mono
            and (now_m - self._last_ws_rx_mono) <= 15.0
            and age_s <= max(max_age_sec, 120.0)
        )

    def get_numeric_book(self, token_id: str, max_age_sec: float = 2.0) -> Optional[Dict[str, Any]]:
        tok = str(token_id or "").strip()
        if not tok:
            return None
        now_m = time.monotonic()
        with self._lock:
            ts_rx = self._last_rx_by_aid.get(tok)
            if not self._is_live_quiet_book_fresh_locked(tok, ts_rx, now_m, max_age_sec):
                return None
            self._materialize_book_locked(tok, build_dict=False)
            num_e = self._numeric_books.get(tok)
            if num_e is None:
                return None
            return {"asset_id": tok, "bids": num_e[1], "asks": num_e[2], "is_partial_delta": (tok not in self._snapshot_tokens)}

    def get_book(self, token_id: str, max_age_sec: float = 2.0) -> Optional[Dict[str, Any]]:
        tok = str(token_id or "").strip()
        if not tok:
            return None
        now_m = time.monotonic()
        with self._lock:
            ts_rx = self._last_rx_by_aid.get(tok)
            entry = self._books.get(tok)
            eff_ts = ts_rx if ts_rx is not None else (entry[0] if entry is not None else None)
            if not self._is_live_quiet_book_fresh_locked(tok, eff_ts, now_m, max_age_sec):
                return None
            if tok in self._dirty_tokens or entry is None:
                return self._materialize_book_locked(tok, build_dict=True)
            return entry[1]

    def seed_book(self, token_id: str, book: Any, *, max_existing_age_sec: float = 2.0) -> bool:
        tok = str(token_id or "").strip()
        if not tok or not isinstance(book, dict):
            return False
        b_raw = book.get("bids") if isinstance(book.get("bids"), list) else []
        a_raw = book.get("asks") if isinstance(book.get("asks"), list) else []
        now_m = time.monotonic()
        with self._lock:
            existing = self._books.get(tok)
            if existing is not None and tok in self._snapshot_tokens and (now_m - existing[0]) <= max_existing_age_sec:
                return False
            self._apply_snapshot_locked(tok, b_raw, a_raw, now_m)
            tk_s = _safe_float(book.get("minimum_tick_size") or book.get("tick_size"), 0.0)
            if 0.0001 <= tk_s <= 0.1:
                self._tick_sizes.setdefault(tok, tk_s)
                if tok in self._books:
                    self._books[tok][1]["minimum_tick_size"] = self._tick_sizes[tok]
            return True

    def process_ws_payload(self, raw_payload: Any) -> bool:
        if not raw_payload or raw_payload in ("PONG", b"PONG"):
            return False
        try:
            data = _loads(raw_payload) if isinstance(raw_payload, (str, bytes, bytearray)) else raw_payload
        except Exception:
            return False
        now_m = time.monotonic()
        urgent_hits: List[Tuple[str, float]] = []
        items = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])

        changed_books: List[Tuple[str, Dict[str, Any]]] = []
        changed_aids: List[str] = []
        tick_changes: List[Tuple[str, float]] = []
        matched_any = False
        with self._lock:
            if self._ws_connected:
                self._last_ws_rx_mono = now_m
            for item in items:
                if not isinstance(item, dict):
                    continue
                ev = str(item.get("event_type") or "")
                if ev in ("market_resolved", "new_market"):
                    m_id = str(item.get("market") or item.get("market_id") or "").strip()
                    if m_id in self._FROZEN_KMIA_IDS:
                        continue
                    self._lifecycle_events.append(
                        {
                            "event_type": ev,
                            "market": m_id,
                            "condition_id": str(item.get("condition_id") or item.get("market") or "").strip(),
                            "asset_id": str(item.get("asset_id") or "").strip(),
                            "winning_outcome": item.get("winning_outcome"),
                            "winning_asset_id": item.get("winning_asset_id"),
                            "assets_ids": item.get("assets_ids") or [],
                            "rx_ts": time.time(),
                        }
                    )
                    matched_any = True
                    continue
                if ev == "best_bid_ask":
                    aid_b = str(item.get("asset_id") or "").strip()
                    if aid_b and aid_b in self._desired_tokens:
                        bb_f = _safe_float(item.get("best_bid"), 0.0)
                        if aid_b in self._raw_levels or aid_b in self._books:
                            self._last_rx_by_aid[aid_b] = now_m
                        matched_any = True
                        if bb_f >= self._recycle_bid_trigger:
                            urgent_hits.append((aid_b, bb_f))
                    continue
                if ev == "tick_size_change" or "new_tick_size" in item:
                    aid = str(item.get("asset_id") or "").strip()
                    tk_f = _safe_float(
                        item.get("new_tick_size") or item.get("tick_size") or item.get("minimum_tick_size"),
                        0.0,
                    )
                    if aid and 0.0001 <= tk_f <= 0.1 and (not self._desired_tokens or aid in self._desired_tokens):
                        self._tick_sizes[aid] = tk_f
                        if aid in self._books:
                            self._books[aid][1]["minimum_tick_size"] = tk_f
                        tick_changes.append((aid, tk_f))
                        matched_any = True
                    continue
                if "bids" in item and "asks" in item and item.get("asset_id"):
                    aid = str(item["asset_id"])
                    if aid in self._desired_tokens:
                        matched_any = True
                        bb = self._apply_snapshot_locked(aid, item.get("bids") or [], item.get("asks") or [], now_m)
                        snap_tk = _safe_float(item.get("minimum_tick_size") or item.get("tick_size"), 0.0)
                        if 0.0001 <= snap_tk <= 0.1:
                            prev_tk = self._tick_sizes.get(aid)
                            self._tick_sizes[aid] = snap_tk
                            if prev_tk is None or abs(prev_tk - snap_tk) > 1e-7:
                                tick_changes.append((aid, snap_tk))
                        if self._on_book_change is not None:
                            changed_aids.append(aid)
                        if bb >= self._recycle_bid_trigger:
                            urgent_hits.append((aid, bb))
                elif ev == "price_change" or "price_changes" in item:
                    by_aid: Dict[str, List[Dict[str, Any]]] = {}
                    for pc in item.get("price_changes") or ():
                        if isinstance(pc, dict):
                            aid = str(pc.get("asset_id") or "")
                            if aid in self._desired_tokens:
                                by_aid.setdefault(aid, []).append(pc)
                    for aid, pcs in by_aid.items():
                        matched_any = True
                        bb = self._apply_changes_locked(aid, pcs, now_m)
                        if self._on_book_change is not None and aid in self._last_rx_by_aid:
                            changed_aids.append(aid)
                        if bb >= self._recycle_bid_trigger:
                            urgent_hits.append((aid, bb))
            if self._on_book_change is not None and changed_aids:
                for aid in dict.fromkeys(changed_aids):
                    bk_m = self._materialize_book_locked(aid, build_dict=True)
                    if bk_m is not None:
                        changed_books.append((aid, bk_m))
        self._last_payload_matched = matched_any

        if self._on_tick_size_change is not None and tick_changes:
            for aid, tk_f in tick_changes:
                try:
                    self._on_tick_size_change(aid, tk_f)
                except Exception:
                    pass

        if self._on_book_change is not None and changed_books:
            for aid, bk_snap in changed_books:
                try:
                    self._on_book_change(aid, bk_snap)
                except Exception:
                    pass

        if self._on_urgent_bid is not None:
            # Debounce per token (<= 1 wakeup / 2s) so a winner parked at >= $0.985 doesn't pin 5 Hz REST supervision.
            last_fire = self.__dict__.setdefault("_urgent_last_fire", {})
            now_f = time.monotonic()
            for aid, bb in urgent_hits:
                if (now_f - float(last_fire.get(aid, 0.0))) < 2.0:
                    continue
                last_fire[aid] = now_f
                try:
                    self._on_urgent_bid(aid, bb)
                except Exception:
                    pass
            if len(last_fire) > 512:
                for k in [k for k, t in last_fire.items() if (now_f - t) > 60.0]:
                    last_fire.pop(k, None)
        return bool(urgent_hits)

    def _rebuild_locked(self, aid: str, b_map: Dict[float, float], a_map: Dict[float, float], now_m: float) -> float:
        # Lazy sort/materialization (`v6.2`): mark token dirty instead of sorting & allocating 30 dicts + 60 strings per delta.
        self._dirty_tokens.add(aid)
        self._last_rx_by_aid[aid] = now_m
        self._books.pop(aid, None)
        best_b = max((px for px, sz in b_map.items() if px > 0.0 and sz > 0.0), default=0.0)
        return best_b

    def _apply_snapshot_locked(self, aid: str, b_raw: List[Any], a_raw: List[Any], now_m: float) -> float:
        b_map: Dict[float, float] = {}
        a_map: Dict[float, float] = {}
        for r in b_raw:
            if isinstance(r, dict):
                px, sz = round(_safe_float(r.get("price")), 4), _safe_float(r.get("size"))
                if px > 0.0 and sz > 0.0:
                    b_map[px] = sz
        for r in a_raw:
            if isinstance(r, dict):
                px, sz = round(_safe_float(r.get("price")), 4), _safe_float(r.get("size"))
                if px > 0.0 and sz > 0.0:
                    a_map[px] = sz
        self._snapshot_tokens.add(aid)
        self._raw_levels[aid] = (b_map, a_map)
        return self._rebuild_locked(aid, b_map, a_map, now_m)

    def _apply_changes_locked(self, aid: str, pcs: List[Dict[str, Any]], now_m: float) -> float:
        b_map, a_map = self._raw_levels.setdefault(aid, ({}, {}))
        for pc in pcs:
            px = round(_safe_float(pc.get("price")), 4)
            sz = _safe_float(pc.get("size"))
            side = str(pc.get("side") or "").upper()
            if px <= 0.0:
                continue
            tgt = b_map if side == "BUY" else a_map
            if sz <= 0.0:
                tgt.pop(px, None)
            else:
                tgt[px] = sz
        if aid not in self._snapshot_tokens and not b_map and not a_map:
            self._raw_levels.pop(aid, None)
            return 0.0
        return self._rebuild_locked(aid, b_map, a_map, now_m)

    async def run_forever(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        try:
            import websockets
        except ImportError:
            return
        self._loop = asyncio.get_running_loop()
        self._sub_wakeup = asyncio.Event()
        backoff = 0.5
        while not (stop_check and stop_check()):
            with self._lock:
                desired_0 = list(getattr(self, "_desired_tokens_ordered", None) or sorted(self._desired_tokens))[:490]
            if not desired_0:
                try:
                    await asyncio.wait_for(self._sub_wakeup.wait(), timeout=0.5)
                    self._sub_wakeup.clear()
                except asyncio.TimeoutError:
                    pass
                continue
            try:
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=15,
                    ping_timeout=15,
                    open_timeout=6,
                    close_timeout=3,
                    max_size=4 * 1024 * 1024,
                    max_queue=512,
                    compression=None,
                ) as ws:
                    _enable_ws_nodelay(ws)
                    subscribed = set(desired_0)
                    # Drop pre-reconnect books: deltas missed during the gap would leave phantom levels.
                    conn_m = time.monotonic()
                    with self._lock:
                        self._books.clear()
                        self._raw_levels.clear()
                        self._numeric_books.clear()
                        self._dirty_tokens.clear()
                        self._last_rx_by_aid.clear()
                        self._snapshot_tokens.clear()
                        self._connected_since_mono = conn_m
                        self._last_ws_rx_mono = conn_m
                        self._ws_connected = True
                    await ws.send(json.dumps({"assets_ids": desired_0, "type": "market", "custom_feature_enabled": True}))
                    backoff = 0.5
                    last_chk = conn_m
                    last_rx = conn_m
                    last_ping = conn_m
                    recv_t: Optional[asyncio.Future[Any]] = None
                    try:
                        while not (stop_check and stop_check()):
                            now_m = time.monotonic()
                            if (now_m - last_ping) >= 9.0:
                                last_ping = now_m
                                await ws.send("PING")
                            woke_sub = bool(self._sub_wakeup and self._sub_wakeup.is_set())
                            if woke_sub or (now_m - last_chk) >= 1.0:
                                if woke_sub and self._sub_wakeup is not None:
                                    self._sub_wakeup.clear()
                                last_chk = now_m
                                with self._lock:
                                    cur_ord = list(getattr(self, "_desired_tokens_ordered", None) or sorted(self._desired_tokens))[:490]
                                    cur = set(cur_ord)
                                if not cur:
                                    break
                                removed = sorted(subscribed - cur)
                                if removed:
                                    for i_rm in range(0, len(removed), 100):
                                        await ws.send(json.dumps({"assets_ids": removed[i_rm : i_rm + 100], "operation": "unsubscribe"}))
                                    subscribed.difference_update(removed)
                                missing_sub = [t for t in cur_ord if t not in subscribed]
                                room_sub = max(0, 495 - len(subscribed))
                                added = missing_sub[:room_sub]
                                if added:
                                    await ws.send(json.dumps({"assets_ids": added, "operation": "subscribe", "custom_feature_enabled": True}))
                                    subscribed.update(added)
                                elif bool(missing_sub):
                                    break
                            if (now_m - last_rx) > 30.0:
                                break
                            if recv_t is None:
                                recv_t = asyncio.ensure_future(ws.recv())
                            wake_t = asyncio.ensure_future(self._sub_wakeup.wait()) if self._sub_wakeup is not None else None
                            wait_set = {recv_t, wake_t} if wake_t is not None else {recv_t}
                            done, pending = await asyncio.wait(wait_set, timeout=1.0, return_when=asyncio.FIRST_COMPLETED)
                            if wake_t is not None and wake_t in pending:
                                wake_t.cancel()
                                await asyncio.gather(wake_t, return_exceptions=True)
                            if recv_t in done:
                                msg = recv_t.result()
                                recv_t = None
                                last_rx = time.monotonic()
                                self._last_ws_rx_mono = last_rx
                                self.process_ws_payload(msg)
                            else:
                                continue
                    finally:
                        self._ws_connected = False
                        if recv_t is not None:
                            if not recv_t.done():
                                recv_t.cancel()
                            await asyncio.gather(recv_t, return_exceptions=True)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"[HARVESTER-MKT-WS] Reconnecting after notice: {exc}")
            await asyncio.sleep(min(5.0, backoff + random.uniform(0.0, 0.2)))
            backoff = min(5.0, backoff * 1.7)


class PolymarketShardedClobMarketWsTracker:
    """
    4-Shard concurrent Polymarket CLOB Market WebSocket pool (`4 x 485 = 1,940` live tokens).
    Uses sticky token->shard routing so active positions and resting maker/watchlist tokens
    NEVER bounce across shards or lose their L2 snapshot delta state when low-priority tokens churn.
    """

    def __init__(
        self,
        num_shards: int = 4,
        per_shard_max: int = 485,
        per_shard_max_tokens: Optional[int] = None,
        ws_url: str = CLOB_MARKET_WS_URL,
        recycle_bid_trigger: float = 0.985,
        on_urgent_bid: Optional[Callable[[str, float], None]] = None,
        on_book_change: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_book_event: Optional[Callable[[str], None]] = None,
        on_tick_size_change: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        self.num_shards = max(1, min(8, int(num_shards)))
        eff_shard_max = per_shard_max_tokens if per_shard_max_tokens is not None else per_shard_max
        self.per_shard_max = max(16, min(490, int(eff_shard_max)))
        self.max_tokens = self.num_shards * self.per_shard_max
        self._lock = threading.Lock()
        self._token_to_shard: Dict[str, int] = {}
        self._desired_tokens_ordered: List[str] = []
        self._desired_tokens: Set[str] = set()
        if on_book_change is not None and on_book_event is not None:
            def _combined_book_cb(aid: str, bk: Dict[str, Any]) -> None:
                on_book_change(aid, bk)
                on_book_event(aid)
            eff_book_cb: Optional[Callable[[str, Dict[str, Any]], None]] = _combined_book_cb
        elif on_book_event is not None:
            eff_book_cb = lambda aid, _bk: on_book_event(aid)
        else:
            eff_book_cb = on_book_change
        self._shards: List[PolymarketClobMarketWsTracker] = [
            PolymarketClobMarketWsTracker(
                ws_url=ws_url,
                recycle_bid_trigger=recycle_bid_trigger,
                on_urgent_bid=on_urgent_bid,
                on_book_change=eff_book_cb,
                on_tick_size_change=on_tick_size_change,
            )
            for _ in range(self.num_shards)
        ]

    def _rebalance_shards_locked(self, ordered: List[str]) -> List[List[str]]:
        clean = set(ordered)
        for stale in list(self._token_to_shard.keys()):
            if stale not in clean:
                self._token_to_shard.pop(stale, None)
        buckets: List[List[str]] = [[] for _ in range(self.num_shards)]
        # Pass 1: preserve existing sticky shard assignments up to per_shard_max
        unassigned: List[str] = []
        for tok in ordered:
            sh_idx = self._token_to_shard.get(tok)
            if sh_idx is not None and 0 <= sh_idx < self.num_shards and len(buckets[sh_idx]) < self.per_shard_max:
                buckets[sh_idx].append(tok)
            else:
                unassigned.append(tok)
        # Pass 2: place newly added tokens onto the least-loaded shard with capacity
        for tok in unassigned:
            best_idx = min(range(self.num_shards), key=lambda idx: len(buckets[idx]))
            if len(buckets[best_idx]) < self.per_shard_max:
                buckets[best_idx].append(tok)
                self._token_to_shard[tok] = best_idx
        self._desired_tokens_ordered = [t for b in buckets for t in b]
        self._desired_tokens = set(self._desired_tokens_ordered)
        return buckets

    def set_desired_tokens(self, tokens: Iterable[str]) -> None:
        ordered: List[str] = []
        seen_c: Set[str] = set()
        for t in tokens:
            s = str(t or "").strip()
            if len(s) >= 15 and s.isdigit() and s not in seen_c:
                seen_c.add(s)
                ordered.append(s)
                if len(ordered) >= self.max_tokens:
                    break
        with self._lock:
            if ordered == self._desired_tokens_ordered:
                return
            buckets = self._rebalance_shards_locked(ordered)
        for idx, sh in enumerate(self._shards):
            if buckets[idx] != sh._desired_tokens_ordered:
                sh.set_desired_tokens(buckets[idx])

    def subscribe_tokens_immediate(self, tokens: Iterable[str]) -> None:
        urgent = [str(t).strip() for t in tokens if t and len(str(t).strip()) >= 15 and str(t).strip().isdigit()]
        if not urgent:
            return
        with self._lock:
            if all(t in self._desired_tokens for t in urgent):
                return
            merged = list(dict.fromkeys(urgent + list(self._desired_tokens_ordered)))[: self.max_tokens]
            buckets = self._rebalance_shards_locked(merged)
        for idx, sh in enumerate(self._shards):
            if buckets[idx] != sh._desired_tokens_ordered:
                sh.set_desired_tokens(buckets[idx])

    def get_book(self, token_id: str, max_age_sec: float = 2.0) -> Optional[Dict[str, Any]]:
        tok = str(token_id or "").strip()
        if not tok:
            return None
        with self._lock:
            sh_idx = self._token_to_shard.get(tok)
        if sh_idx is not None and 0 <= sh_idx < self.num_shards:
            bk = self._shards[sh_idx].get_book(tok, max_age_sec=max_age_sec)
            if bk is not None:
                return bk
        for sh in self._shards:
            bk = sh.get_book(tok, max_age_sec=max_age_sec)
            if bk is not None:
                return bk
        return None

    def seed_book(self, token_id: str, book: Any, *, max_existing_age_sec: float = 2.0) -> bool:
        tok = str(token_id or "").strip()
        if not tok:
            return False
        with self._lock:
            sh_idx = self._token_to_shard.get(tok)
            if sh_idx is None:
                sh_idx = min(range(self.num_shards), key=lambda i: len(self._shards[i]._desired_tokens))
                if len(tok) >= 15 and tok.isdigit():
                    self._token_to_shard[tok] = sh_idx
        return self._shards[sh_idx].seed_book(tok, book, max_existing_age_sec=max_existing_age_sec)

    def get_tick_size(self, token_id: str) -> Optional[float]:
        tok = str(token_id or "").strip()
        if not tok:
            return None
        with self._lock:
            sh_idx = self._token_to_shard.get(tok)
        if sh_idx is not None and 0 <= sh_idx < self.num_shards:
            tk = self._shards[sh_idx].get_tick_size(tok)
            if tk is not None:
                return tk
        for sh in self._shards:
            tk = sh.get_tick_size(tok)
            if tk is not None:
                return tk
        return None

    def process_ws_payload(self, raw_payload: Any) -> bool:
        hit = False
        for sh in self._shards:
            sh._last_payload_matched = False
            if sh.process_ws_payload(raw_payload) or bool(getattr(sh, "_last_payload_matched", False)):
                hit = True
        return hit

    def shard_token_counts(self) -> List[int]:
        return [len(sh._desired_tokens) for sh in self._shards]

    def drain_lifecycle_events(self, max_items: int = 64) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        seen: Set[Tuple[str, str, str, str]] = set()
        for sh in self._shards:
            for ev in sh.drain_lifecycle_events(max_items):
                sig = (
                    str(ev.get("event_type") or ""),
                    str(ev.get("market") or ""),
                    str(ev.get("condition_id") or ""),
                    str(ev.get("asset_id") or ""),
                )
                if sig in seen:
                    continue
                seen.add(sig)
                out.append(ev)
                if len(out) >= max_items:
                    return out
        return out

    def get_numeric_book(self, token_id: str, max_age_sec: float = 2.0) -> Optional[Dict[str, Any]]:
        tok = str(token_id or "").strip()
        if not tok:
            return None
        with self._lock:
            sh_idx = self._token_to_shard.get(tok)
        if sh_idx is not None and 0 <= sh_idx < self.num_shards:
            bk = self._shards[sh_idx].get_numeric_book(tok, max_age_sec=max_age_sec)
            if bk is not None:
                return bk
        for sh in self._shards:
            bk = sh.get_numeric_book(tok, max_age_sec=max_age_sec)
            if bk is not None:
                return bk
        return None

    async def run_forever(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        await asyncio.gather(*(sh.run_forever(stop_check) for sh in self._shards))


class PolymarketPerpsLeadLagStream:
    """
    Read-only `$0`-collateral lead-lag microstructure sensor connected to Polymarket Perpetuals
    (`wss://ws.perpetuals.polymarket.com/v1/ws`, unauthenticated `bbo` + `tickers` channels).
    Strictly used ONLY for sub-50ms maker pre-cancel protection (`PERP1` Mode `6A`) — NEVER for
    delta-hedging binary payoffs with linear perpetuals!
    """

    PERP_SYMBOL_MAP: Dict[str, str] = {
        "BTC-PERP": "BTC",
        "BTC-USD-PERP": "BTC",
        "BTCUSD-PERP": "BTC",
        "BTC": "BTC",
        "ETH-PERP": "ETH",
        "ETH-USD-PERP": "ETH",
        "ETHUSD-PERP": "ETH",
        "ETH": "ETH",
        "SOL-PERP": "SOL",
        "SOL-USD-PERP": "SOL",
        "SOL": "SOL",
        "XRP-PERP": "XRP",
        "XRP-USD-PERP": "XRP",
        "XRP": "XRP",
        "HYPE-PERP": "HYPE",
        "DOGE-PERP": "DOGE",
        "BNB-PERP": "BNB",
        "ZEC-PERP": "ZEC",
    }

    def __init__(self, ws_url: str = PERPS_WS_URL) -> None:
        self._ws_url = str(ws_url or PERPS_WS_URL)
        self._lock = threading.Lock()
        self._bbo_hist: Dict[str, deque] = {}
        self._latest_bbo: Dict[str, Tuple[float, float, float, float]] = {}  # (ts_s, bid, ask, mid)
        self._connected = False
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False

    def process_ws_frame(self, raw_msg: Any, now_ts: Optional[float] = None) -> bool:
        try:
            d = _loads(raw_msg) if isinstance(raw_msg, (str, bytes, bytearray)) else raw_msg
        except Exception:
            return False
        if not isinstance(d, dict):
            return False
        pl = d.get("data") if isinstance(d.get("data"), dict) else (d.get("payload") if isinstance(d.get("payload"), dict) else d)
        raw_sym = str(
            pl.get("symbol") or pl.get("market") or pl.get("instrument") or d.get("symbol") or ""
        ).strip().upper()
        asset = self.PERP_SYMBOL_MAP.get(raw_sym) or (raw_sym.split("-")[0] if "-PERP" in raw_sym else "")
        if not asset:
            return False
        bid = _safe_float(pl.get("bestBid") or pl.get("bidPrice") or pl.get("bid") or pl.get("b"), 0.0)
        ask = _safe_float(pl.get("bestAsk") or pl.get("askPrice") or pl.get("ask") or pl.get("a"), 0.0)
        mark = _safe_float(pl.get("markPrice") or pl.get("indexPrice") or pl.get("midPrice") or pl.get("lastPrice"), 0.0)
        mid = 0.5 * (bid + ask) if (bid > 0.0 and ask > 0.0 and ask >= bid) else mark
        if mid <= 0.0:
            return False
        ts_raw = _safe_float(pl.get("timestamp") or pl.get("ts") or d.get("ts"), 0.0)
        ts_s = (ts_raw / 1000.0 if ts_raw > 1e11 else ts_raw) if ts_raw > 0.0 else float(time.time() if now_ts is None else now_ts)
        with self._lock:
            self._latest_bbo[asset] = (ts_s, bid if bid > 0 else mid, ask if ask > 0 else mid, mid)
            dq = self._bbo_hist.setdefault(asset, deque(maxlen=256))
            dq.append((ts_s, mid))
        return True

    def get_latest_mid(self, asset: str, now_ts: Optional[float] = None, max_age_sec: float = 2.0) -> Optional[float]:
        sym = str(asset or "").strip().upper()
        now_f = float(time.time() if now_ts is None else now_ts)
        with self._lock:
            rec = self._latest_bbo.get(sym)
            if not rec:
                return None
            if -2.0 <= (now_f - rec[0]) <= max_age_sec:
                return rec[3]
            return None

    def get_adverse_velocity_bps(
        self, asset: str, window_ms: float = 300.0, now_ts: Optional[float] = None
    ) -> Optional[float]:
        """
        Returns signed Perps BBO mid return `(mid_now - mid_t0) / mid_t0 * 10,000` (in bps)
        over the trailing `window_ms` window (`None` if stale or insufficient ticks).
        Used strictly to pre-cancel resting binary maker quotes before adverse takers arrive.
        """
        sym = str(asset or "").strip().upper()
        now_f = float(time.time() if now_ts is None else now_ts)
        win_s = max(0.05, float(window_ms) / 1000.0)
        with self._lock:
            dq = self._bbo_hist.get(sym)
            if not dq or len(dq) < 2:
                return None
            t_now, p_now = dq[-1]
            if (now_f - t_now) > 2.0 or p_now <= 0.0:
                return None
            cutoff = t_now - win_s
            p_ref = None
            for t_i, p_i in dq:
                if t_i >= cutoff and p_i > 0.0:
                    p_ref = p_i
                    break
            if p_ref is None or p_ref <= 0.0:
                p_ref = dq[0][1]
            if p_ref <= 0.0:
                return None
            return round(((p_now - p_ref) / p_ref) * 10000.0, 4)

    def should_precancel_binary_maker(
        self,
        asset: str,
        maker_direction: str,
        *,
        threshold_bps: float = 8.0,
        window_ms: float = 300.0,
        now_ts: Optional[float] = None,
    ) -> bool:
        """
        True when Polymarket Perps BBO jumps adversely against a resting binary Maker BUY:
        - Buying `UP`/`YES`: adverse when Perps mid drops `<= -threshold_bps`
        - Buying `DOWN`/`NO`: adverse when Perps mid spikes `>= +threshold_bps`
        """
        vel = self.get_adverse_velocity_bps(asset, window_ms=window_ms, now_ts=now_ts)
        if vel is None:
            return False
        side_u = str(maker_direction or "").strip().upper()
        if side_u in ("UP", "YES", "LONG"):
            return vel <= -abs(float(threshold_bps))
        if side_u in ("DOWN", "NO", "SHORT"):
            return vel >= abs(float(threshold_bps))
        return abs(vel) >= abs(float(threshold_bps))

    async def _run_loop(self) -> None:
        try:
            import websockets
        except ImportError:
            return
        backoff = 1.0
        sub_frames = [
            {"op": "subscribe", "channel": "bbo", "symbols": ["BTC-PERP", "ETH-PERP", "SOL-PERP", "XRP-PERP"]},
            {"type": "subscribe", "channels": ["bbo", "tickers"], "markets": ["BTC-PERP", "ETH-PERP", "SOL-PERP", "XRP-PERP"]},
        ]
        while not self._stop_flag:
            try:
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=15,
                    ping_timeout=10,
                    open_timeout=5,
                    compression=None,
                ) as ws:
                    self._connected = True
                    backoff = 1.0
                    for sf in sub_frames:
                        try:
                            await ws.send(json.dumps(sf))
                        except Exception:
                            pass
                    while not self._stop_flag:
                        raw = await asyncio.wait_for(ws.recv(), timeout=20.0)
                        self.process_ws_frame(raw)
            except Exception:
                self._connected = False
            if not self._stop_flag:
                await asyncio.sleep(min(10.0, backoff))
                backoff = min(10.0, backoff * 1.7)

    def start_background(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_flag = False
        self._thread = threading.Thread(target=lambda: asyncio.run(self._run_loop()), name="pm-perps-bbo-ws", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag = True
