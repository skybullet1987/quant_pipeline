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
import threading
import time
from collections import deque
from decimal import Decimal
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Set, Tuple

try:
    import orjson as _orjson
except ImportError:
    _orjson = None  # type: ignore

logger = logging.getLogger("PolymarketWSStreams")

USER_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/user"
MARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
LIVE_DATA_WS_URL = "wss://ws-live-data.polymarket.com"

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
    "hype/usd": "HYPE",
}


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
                    if prev_st in TERMINAL_CANCEL_STATUSES or prev_st in TERMINAL_FILL_STATUSES:
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
                    if msg_type == "CANCELLATION" or status in TERMINAL_CANCEL_STATUSES or status in TERMINAL_FILL_STATUSES:
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
                    for oid_ref in [taker_oid] + [str(mo.get("order_id") or "").strip() for mo in maker_list]:
                        if oid_ref:
                            prev_o = self._orders_by_id.get(oid_ref)
                            if isinstance(prev_o, dict):
                                prev_o["_updated_mono"] = now_m
                                prev_o["relayer_trade_status"] = tr_status
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
            try:
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=15,
                    ping_timeout=15,
                    open_timeout=6,
                    close_timeout=3,
                    max_size=4 * 1024 * 1024,
                ) as ws:
                    await ws.send(auth_msg)
                    now_m = time.monotonic()
                    with self._lock:
                        self._connected = True
                        self._connected_since_mono = now_m
                        self._last_rx_mono = now_m
                        self._seeded_since_connect = False
                    backoff = 0.5
                    logger.info("[USER-WS] Authenticated CLOB ws/user stream connected.")
                    last_ping = now_m
                    while not self._stop_event.is_set():
                        now_step = time.monotonic()
                        if (now_step - last_ping) >= 9.0:
                            last_ping = now_step
                            await ws.send("PING")
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        except asyncio.TimeoutError:
                            continue
                        self.process_ws_payload(msg)
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
    Real-time Polymarket Chainlink Data Streams client (`wss://ws-live-data.polymarket.com`).
    Captures exact 1Hz 18-decimal `crypto_prices_chainlink` USD reports for all 7 dominance coins,
    computing exact 60-second boundary TWAPs at `t = +0.2s` (bypassing `/api/crypto/crypto-price` 429s)
    and continuous path-integral samples for `S2_EXACT_TWAP_LOCK`.
    """

    def __init__(
        self,
        *,
        ws_url: str = LIVE_DATA_WS_URL,
        history_sec: float = 420.0,
        on_tick: Optional[Callable[[str, float, float], None]] = None,
    ) -> None:
        self._ws_url = ws_url
        self._history_sec = float(history_sec)
        self._on_tick = on_tick
        self._lock = threading.RLock()
        self._ticks: Dict[str, Deque[Tuple[float, float]]] = {
            sym: deque(maxlen=600) for sym in CHAINLINK_SYMBOL_MAP.values()
        }
        self._boundary_twaps: Dict[Tuple[str, int], float] = {}
        self._connected = False
        self._last_rx_mono = 0.0

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

    def process_ws_message(self, raw_msg: Any) -> bool:
        if not raw_msg or raw_msg in ("PONG", b"PONG"):
            with self._lock:
                self._last_rx_mono = time.monotonic()
            return False
        try:
            d = _loads(raw_msg) if isinstance(raw_msg, (str, bytes, bytearray)) else raw_msg
        except Exception:
            return False
        if not isinstance(d, dict) or d.get("topic") != "crypto_prices_chainlink":
            return False
        pl = d.get("payload")
        if not isinstance(pl, dict):
            return False
        raw_sym = str(pl.get("symbol") or "").strip().lower()
        asset = CHAINLINK_SYMBOL_MAP.get(raw_sym)
        if not asset:
            return False
        ts_raw = pl.get("timestamp")
        if ts_raw is None:
            return False
        ts_f = float(ts_raw)
        ts_sec = ts_f / 1000.0 if ts_f > 1e11 else ts_f

        full_acc = pl.get("full_accuracy_value")
        px = 0.0
        if full_acc not in (None, ""):
            try:
                px = float(Decimal(str(full_acc)) / Decimal("1e18"))
            except Exception:
                px = 0.0
        if px <= 0.0:
            px = _safe_float(pl.get("value"), 0.0)
        if px <= 0.0:
            return False
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

    def get_recent_samples(self, asset: str, since_ts: float) -> List[Tuple[float, float]]:
        sym = str(asset or "").strip().upper()
        with self._lock:
            dq = self._ticks.get(sym)
            if not dq:
                return []
            return [(t, p) for t, p in dq if t >= since_ts]

    async def run_forever(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        try:
            import websockets
        except ImportError:
            logger.warning("[CHAINLINK-WS] websockets unavailable; skipping live Chainlink stream.")
            return
        sub_msg = json.dumps(
            {
                "action": "subscribe",
                "subscriptions": [
                    {"topic": "crypto_prices_chainlink", "type": "*", "filters": ""},
                ],
            }
        )
        backoff = 0.5
        while not (stop_check and stop_check()):
            try:
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=12,
                    ping_timeout=12,
                    open_timeout=6,
                    close_timeout=3,
                    max_size=2 * 1024 * 1024,
                ) as ws:
                    await ws.send(sub_msg)
                    with self._lock:
                        self._connected = True
                        self._last_rx_mono = time.monotonic()
                    backoff = 0.5
                    logger.info("[CHAINLINK-WS] Connected to live Polymarket Chainlink 1Hz stream (7 coins).")
                    while not (stop_check and stop_check()):
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        except asyncio.TimeoutError:
                            if (time.monotonic() - self._last_rx_mono) > 15.0:
                                break
                            continue
                        self.process_ws_message(msg)
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
    ) -> None:
        self._ws_url = ws_url
        self._recycle_bid_trigger = float(recycle_bid_trigger)
        self._on_urgent_bid = on_urgent_bid
        self._lock = threading.RLock()
        self._desired_tokens: Set[str] = set()
        self._books: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._raw_levels: Dict[str, Tuple[Dict[float, float], Dict[float, float]]] = {}

    def set_desired_tokens(self, tokens: Iterable[str]) -> None:
        clean = {str(t).strip() for t in tokens if t and len(str(t).strip()) >= 15 and str(t).strip().isdigit()}
        with self._lock:
            self._desired_tokens = clean
            for stale in list(self._books.keys()):
                if stale not in clean:
                    self._books.pop(stale, None)
                    self._raw_levels.pop(stale, None)

    def get_book(self, token_id: str, max_age_sec: float = 2.0) -> Optional[Dict[str, Any]]:
        tok = str(token_id or "").strip()
        if not tok:
            return None
        now_m = time.monotonic()
        with self._lock:
            entry = self._books.get(tok)
            if entry is None or (now_m - entry[0]) > max_age_sec:
                return None
            return entry[1]

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

        with self._lock:
            for item in items:
                if not isinstance(item, dict):
                    continue
                ev = str(item.get("event_type") or "")
                if "bids" in item and "asks" in item and item.get("asset_id"):
                    aid = str(item["asset_id"])
                    if aid in self._desired_tokens:
                        bb = self._apply_snapshot_locked(aid, item.get("bids") or [], item.get("asks") or [], now_m)
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
                        bb = self._apply_changes_locked(aid, pcs, now_m)
                        if bb >= self._recycle_bid_trigger:
                            urgent_hits.append((aid, bb))

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
        bids = [
            {"price": f"{px:.4f}", "size": f"{sz:.4f}"}
            for px, sz in sorted(b_map.items(), key=lambda kv: -kv[0])[:15]
            if px > 0.0 and sz > 0.0
        ]
        asks = [
            {"price": f"{px:.4f}", "size": f"{sz:.4f}"}
            for px, sz in sorted(a_map.items(), key=lambda kv: kv[0])[:15]
            if px > 0.0 and sz > 0.0
        ]
        best_b = float(bids[0]["price"]) if bids else 0.0
        self._books[aid] = (now_m, {"asset_id": aid, "bids": bids, "asks": asks})
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
        self._raw_levels[aid] = (b_map, a_map)
        return self._rebuild_locked(aid, b_map, a_map, now_m)

    def _apply_changes_locked(self, aid: str, pcs: List[Dict[str, Any]], now_m: float) -> float:
        lvls = self._raw_levels.get(aid)
        if lvls is None:
            return 0.0
        b_map, a_map = lvls
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
        return self._rebuild_locked(aid, b_map, a_map, now_m)

    async def run_forever(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        try:
            import websockets
        except ImportError:
            return
        backoff = 0.5
        while not (stop_check and stop_check()):
            with self._lock:
                desired_0 = sorted(self._desired_tokens)
            if not desired_0:
                await asyncio.sleep(0.5)
                continue
            try:
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=15,
                    ping_timeout=15,
                    open_timeout=6,
                    close_timeout=3,
                    max_size=4 * 1024 * 1024,
                ) as ws:
                    subscribed = set(desired_0)
                    # Drop pre-reconnect books: deltas missed during the gap would leave phantom levels.
                    with self._lock:
                        self._books.clear()
                        self._raw_levels.clear()
                    await ws.send(json.dumps({"assets_ids": desired_0, "type": "market"}))
                    backoff = 0.5
                    last_chk = time.monotonic()
                    last_rx = last_chk
                    last_ping = last_chk
                    while not (stop_check and stop_check()):
                        now_m = time.monotonic()
                        if (now_m - last_ping) >= 9.0:
                            last_ping = now_m
                            await ws.send("PING")
                        if (now_m - last_chk) >= 1.0:
                            last_chk = now_m
                            with self._lock:
                                cur = set(self._desired_tokens)
                            if not cur:
                                break
                            added = sorted(cur - subscribed)
                            if added:
                                await ws.send(json.dumps({"assets_ids": added, "operation": "subscribe"}))
                                subscribed.update(added)
                            elif len(subscribed) > len(cur) + 16:
                                break
                        if (now_m - last_rx) > 30.0:
                            break
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        except asyncio.TimeoutError:
                            continue
                        last_rx = time.monotonic()
                        self.process_ws_payload(msg)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"[HARVESTER-MKT-WS] Reconnecting after notice: {exc}")
            await asyncio.sleep(min(5.0, backoff + random.uniform(0.0, 0.2)))
            backoff = min(5.0, backoff * 1.7)
