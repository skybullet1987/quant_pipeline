#!/usr/bin/env python3
"""
Hyperliquid Reconnect-Resilient In-Memory WebSocket L2 & Asset-Context Cache
============================================================================
Provides sub-millisecond (<0.05 ms), staleness-guarded access to:
  1. `l2Book` Top-5 Orderbook Microstructure (BBO, Mid, Microprice, Decay-Weighted OBI_5)
  2. `activeAssetCtx` Real-Time Oracle Price (`oraclePx`), Funding, Premium & Open Interest
  3. `allMids` Exchange-Wide Mid Prices

Safety & Reliability Guarantees:
  - Uses strictly `daemon=True` worker threads so CLI scripts and `pytest` never hang.
  - Auto-reconnects with jittered exponential backoff (1s -> 10s) on CloudFlare/TCP drops
    (fixing `hyperliquid.websocket_manager.WebsocketManager`'s single-shot non-reconnecting loop).
  - Enforces strict `time.monotonic()` freshness TTLs (`l2_staleness_sec=4.0`, `ctx_staleness_sec=6.0`)
    and immediately invalidates cached timestamps on socket disconnect so stale books are never read;
    callers fall back seamlessly to REST when `None` is returned.
"""
from __future__ import annotations

import json
import math
import random
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import websocket  # type: ignore
except ImportError:  # pragma: no cover
    websocket = None

DEFAULT_WS_MAJORS: Tuple[str, ...] = (
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "HYPE",
    "DOGE",
    "SUI",
    "BNB",
    "AAVE",
    "ADA",
    "LINK",
    "AVAX",
    "LIT",
    "LTC",
    "NEAR",
    "UNI",
    "ARB",
    "OP",
    "TIA",
    "APT",
)

_DECAY_WEIGHTS_5: Tuple[float, ...] = tuple(math.exp(-0.5 * k) for k in range(5))


def compute_l2_microstructure(
    bids: List[Dict[str, Any]],
    asks: List[Dict[str, Any]],
    tick_sz: float = 0.0,
) -> Optional[Dict[str, float]]:
    """
    Computes top-of-book and top-5 queue microstructure metrics from Hyperliquid L2 levels.
    Works identically on WebSocket `l2Book` frames and REST `l2_snapshot` responses.
    """
    if not bids or not asks:
        return None
    try:
        best_bid = float(bids[0]["px"])
        best_ask = float(asks[0]["px"])
        if best_bid <= 0.0 or best_ask <= 0.0:
            return None
        mid = 0.5 * (best_bid + best_ask)
        spread = max(0.0, best_ask - best_bid)
        spread_bps = (spread / mid * 10000.0) if mid > 0.0 else 0.0
        spread_ticks = (spread / tick_sz) if tick_sz > 0.0 else 1.0

        bid_sz_1 = max(0.0, float(bids[0].get("sz", 0.0)))
        ask_sz_1 = max(0.0, float(asks[0].get("sz", 0.0)))
        top_sum = bid_sz_1 + ask_sz_1
        microprice = ((best_bid * ask_sz_1 + best_ask * bid_sz_1) / top_sum) if top_sum > 1e-12 else mid

        w_bid = 0.0
        for idx, lvl in enumerate(bids[:5]):
            w_bid += _DECAY_WEIGHTS_5[idx] * max(0.0, float(lvl.get("sz", 0.0)))
        w_ask = 0.0
        for idx, lvl in enumerate(asks[:5]):
            w_ask += _DECAY_WEIGHTS_5[idx] * max(0.0, float(lvl.get("sz", 0.0)))

        denom = w_bid + w_ask
        obi_5 = ((w_bid - w_ask) / denom) if denom > 1e-12 else 0.0

        return {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid": mid,
            "microprice": microprice,
            "obi_5": float(max(-1.0, min(1.0, obi_5))),
            "spread": spread,
            "spread_bps": spread_bps,
            "spread_ticks": spread_ticks,
            "bid_sz_1": bid_sz_1,
            "ask_sz_1": ask_sz_1,
        }
    except (KeyError, ValueError, TypeError, IndexError):
        return None


def select_queue_aware_alo_price(
    is_buy: bool,
    best_bid: float,
    best_ask: float,
    tick_sz: float,
    obi_5: float,
    penny_spread_ticks: float = 2.5,
    penny_obi_threshold: float = 0.20,
    retreat_obi_threshold: float = -0.60,
) -> Tuple[float, str]:
    """
    Queue-aware strictly post-only (`Alo`) limit price selector:
      1. PENNY_INSIDE (+1 tick inside wide spread >= 2.5 ticks when Top-5 OBI >= +0.20 supports our side):
         Captures #1 queue priority while strictly remaining passive (`< best_ask` for Buy, `> best_bid` for Sell).
      2. ADVERSE_RETREAT (-1 tick behind BBO when Top-5 OBI <= -0.60 opposes our side):
         Shields against imminent queue wipeout / toxic adverse selection.
      3. JOIN_BBO (exact `best_bid` / `best_ask` in normal tight or balanced books).

    Returns:
        `(raw_limit_price, regime_label)`
    """
    if tick_sz <= 0.0 or best_bid <= 0.0 or best_ask <= 0.0 or best_ask <= best_bid:
        return (best_bid if is_buy else best_ask), "JOIN_BBO"

    spread = best_ask - best_bid
    spread_ticks = spread / tick_sz
    signed_obi = obi_5 if is_buy else -obi_5

    # Case 1: Wide spread + supporting queue imbalance -> step 1 tick inside BBO without crossing
    if spread_ticks >= penny_spread_ticks and signed_obi >= penny_obi_threshold:
        if is_buy:
            cand = best_bid + tick_sz
            if cand < best_ask - 0.25 * tick_sz:
                return cand, "PENNY_INSIDE"
        else:
            cand = best_ask - tick_sz
            if cand > best_bid + 0.25 * tick_sz:
                return cand, "PENNY_INSIDE"

    # Case 2: Severe opposing queue pressure -> retreat 1 tick behind BBO
    if signed_obi <= retreat_obi_threshold:
        if is_buy:
            return max(tick_sz, best_bid - tick_sz), "ADVERSE_RETREAT"
        return best_ask + tick_sz, "ADVERSE_RETREAT"

    # Case 3: Balanced or 1-tick tight book -> join inside BBO
    return (best_bid if is_buy else best_ask), "JOIN_BBO"


class HyperliquidWsMarketCache:
    """Thread-safe, auto-reconnecting Hyperliquid WebSocket cache with monotonic TTL guards."""

    MAX_SUBSCRIBED_COINS = 45

    def __init__(
        self,
        base_url: str,
        initial_coins: Optional[List[str]] = None,
        allowed_coins: Optional[Set[str]] = None,
        l2_staleness_sec: float = 4.0,
        ctx_staleness_sec: float = 6.0,
        mid_staleness_sec: float = 4.0,
        auto_start: bool = True,
    ) -> None:
        if base_url.startswith("https://"):
            self.ws_url = "wss://" + base_url[len("https://") :].rstrip("/") + "/ws"
        elif base_url.startswith("http://"):
            self.ws_url = "ws://" + base_url[len("http://") :].rstrip("/") + "/ws"
        else:
            self.ws_url = base_url

        self.l2_staleness_sec = float(l2_staleness_sec)
        self.ctx_staleness_sec = float(ctx_staleness_sec)
        self.mid_staleness_sec = float(mid_staleness_sec)

        self._lock = threading.Lock()
        self._allowed_coins: Optional[Set[str]] = set(allowed_coins) if allowed_coins is not None else None
        raw_init = set(initial_coins or DEFAULT_WS_MAJORS)
        if self._allowed_coins is not None:
            raw_init = {c for c in raw_init if c in self._allowed_coins}
        self._subscribed_coins: Set[str] = raw_init
        self._l2_books: Dict[str, Tuple[float, List[Dict[str, Any]], List[Dict[str, Any]]]] = {}
        self._asset_ctxs: Dict[str, Tuple[float, Dict[str, float]]] = {}
        self._all_mids: Dict[str, float] = {}
        self._all_mids_ts: float = 0.0

        self._connected: bool = False
        self._stop_event = threading.Event()
        self._ws_app: Any = None
        self._runner_thread: Optional[threading.Thread] = None
        self._ping_thread: Optional[threading.Thread] = None

        # Telemetry counters
        self.messages_received: int = 0
        self.reconnect_count: int = 0
        self.ws_hits_l2: int = 0
        self.ws_misses_l2: int = 0
        self.ws_hits_oracle: int = 0
        self.ws_misses_oracle: int = 0
        self.ws_hits_mid: int = 0
        self.ws_misses_mid: int = 0

        if auto_start and websocket is not None:
            self.start()

    def start(self) -> None:
        if websocket is None:
            return
        with self._lock:
            if self._runner_thread is not None and self._runner_thread.is_alive():
                return
            self._stop_event.clear()
            self._runner_thread = threading.Thread(
                target=self._run_reconnect_loop,
                name="hl-ws-market-cache",
                daemon=True,
            )
            self._ping_thread = threading.Thread(
                target=self._run_ping_loop,
                name="hl-ws-ping",
                daemon=True,
            )
            self._runner_thread.start()
            self._ping_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        ws = self._ws_app
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        self._invalidate_on_disconnect()

    def _invalidate_on_disconnect(self) -> None:
        with self._lock:
            self._connected = False
            self._all_mids_ts = 0.0
            self._l2_books.clear()
            self._asset_ctxs.clear()

    def _send_coin_subscriptions(self, ws: Any, coin: str) -> None:
        try:
            ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "l2Book", "coin": coin}}))
            ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "activeAssetCtx", "coin": coin}}))
        except Exception:
            pass

    def ensure_subscribed(self, coin: str) -> None:
        if not coin or coin.startswith("#") or coin.startswith("@"):
            return
        ws_to_send = None
        with self._lock:
            if self._allowed_coins is not None and coin not in self._allowed_coins:
                return
            if coin in self._subscribed_coins or len(self._subscribed_coins) >= self.MAX_SUBSCRIBED_COINS:
                return
            self._subscribed_coins.add(coin)
            if self._connected and self._ws_app is not None:
                ws_to_send = self._ws_app
        if ws_to_send is not None:
            self._send_coin_subscriptions(ws_to_send, coin)

    def _on_open(self, ws: Any) -> None:
        with self._lock:
            self._connected = True
            coins = sorted(self._subscribed_coins)
        try:
            ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "allMids"}}))
            for coin in coins:
                self._send_coin_subscriptions(ws, coin)
        except Exception:
            pass

    def _on_message(self, _ws: Any, raw_msg: str) -> None:
        if not raw_msg or not raw_msg.startswith("{"):
            return
        try:
            msg = json.loads(raw_msg)
        except Exception:
            return
        channel = msg.get("channel")
        data = msg.get("data")
        now_m = time.monotonic()

        if channel == "l2Book" and isinstance(data, dict):
            coin = data.get("coin")
            levels = data.get("levels")
            if isinstance(coin, str) and isinstance(levels, list) and len(levels) >= 2:
                bids, asks = levels[0], levels[1]
                if bids and asks:
                    with self._lock:
                        self.messages_received += 1
                        self._l2_books[coin] = (now_m, bids[:5], asks[:5])
        elif channel == "activeAssetCtx" and isinstance(data, dict):
            coin = data.get("coin")
            ctx = data.get("ctx")
            if isinstance(coin, str) and isinstance(ctx, dict):
                try:
                    parsed_ctx = {
                        "oraclePx": float(ctx.get("oraclePx") or 0.0),
                        "markPx": float(ctx.get("markPx") or 0.0),
                        "midPx": float(ctx.get("midPx") or 0.0),
                        "funding": float(ctx.get("funding") or 0.0),
                        "openInterest": float(ctx.get("openInterest") or 0.0),
                        "premium": float(ctx.get("premium") or 0.0),
                        "dayNtlVlm": float(ctx.get("dayNtlVlm") or 0.0),
                    }
                    with self._lock:
                        self.messages_received += 1
                        self._asset_ctxs[coin] = (now_m, parsed_ctx)
                except (ValueError, TypeError):
                    pass
        elif channel == "allMids" and isinstance(data, dict):
            mids = data.get("mids")
            if isinstance(mids, dict):
                parsed_mids: Dict[str, float] = {}
                for k, v in mids.items():
                    if isinstance(k, str) and not k.startswith("#") and not k.startswith("@"):
                        try:
                            px = float(v)
                            if px > 0.0:
                                parsed_mids[k] = px
                        except (ValueError, TypeError):
                            continue
                with self._lock:
                    self.messages_received += 1
                    self._all_mids.update(parsed_mids)
                    self._all_mids_ts = now_m

    def _on_error(self, _ws: Any, _err: Any) -> None:
        self._invalidate_on_disconnect()

    def _on_close(self, _ws: Any, _code: Any, _msg: Any) -> None:
        self._invalidate_on_disconnect()

    def _run_ping_loop(self) -> None:
        while not self._stop_event.wait(30.0):
            ws = self._ws_app
            if self._connected and ws is not None:
                try:
                    ws.send(json.dumps({"method": "ping"}))
                except Exception:
                    pass

    def _run_reconnect_loop(self) -> None:
        backoff = 1.0
        while not self._stop_event.is_set():
            t0 = time.monotonic()
            try:
                ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self._ws_app = ws
                ws.run_forever()
            except Exception:
                pass
            finally:
                self._invalidate_on_disconnect()

            if self._stop_event.is_set():
                break
            with self._lock:
                self.reconnect_count += 1
            if (time.monotonic() - t0) > 20.0:
                backoff = 1.0
            sleep_s = min(10.0, backoff) + random.uniform(0.05, 0.35)
            backoff = min(10.0, backoff * 2.0)
            self._stop_event.wait(sleep_s)

    # --- Fast Thread-Safe Readers (Return None when cold/stale so caller falls back to REST) ---

    def get_fresh_l2_levels(self, coin: str) -> Optional[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]]:
        self.ensure_subscribed(coin)
        now_m = time.monotonic()
        with self._lock:
            entry = self._l2_books.get(coin)
            if entry is not None and (now_m - entry[0]) <= self.l2_staleness_sec:
                self.ws_hits_l2 += 1
                return entry[1], entry[2]
            self.ws_misses_l2 += 1
            return None

    def get_fresh_mid(self, coin: str) -> Optional[float]:
        self.ensure_subscribed(coin)
        now_m = time.monotonic()
        with self._lock:
            l2_entry = self._l2_books.get(coin)
            if l2_entry is not None and (now_m - l2_entry[0]) <= self.l2_staleness_sec:
                bids, asks = l2_entry[1], l2_entry[2]
                if bids and asks:
                    self.ws_hits_mid += 1
                    return 0.5 * (float(bids[0]["px"]) + float(asks[0]["px"]))
            if self._all_mids_ts > 0.0 and (now_m - self._all_mids_ts) <= self.mid_staleness_sec:
                px = self._all_mids.get(coin)
                if px is not None and px > 0.0:
                    self.ws_hits_mid += 1
                    return px
            self.ws_misses_mid += 1
            return None

    def get_fresh_oracle_price(self, coin: str) -> Optional[float]:
        self.ensure_subscribed(coin)
        now_m = time.monotonic()
        with self._lock:
            entry = self._asset_ctxs.get(coin)
            if entry is not None and (now_m - entry[0]) <= self.ctx_staleness_sec:
                opx = float(entry[1].get("oraclePx", 0.0))
                if opx > 0.0:
                    self.ws_hits_oracle += 1
                    return opx
            self.ws_misses_oracle += 1
            return None

    def get_fresh_asset_ctx(self, coin: str) -> Optional[Dict[str, float]]:
        self.ensure_subscribed(coin)
        now_m = time.monotonic()
        with self._lock:
            entry = self._asset_ctxs.get(coin)
            if entry is not None and (now_m - entry[0]) <= self.ctx_staleness_sec:
                return dict(entry[1])
            return None

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            tot_l2 = self.ws_hits_l2 + self.ws_misses_l2
            tot_or = self.ws_hits_oracle + self.ws_misses_oracle
            tot_md = self.ws_hits_mid + self.ws_misses_mid
            return {
                "connected": self._connected,
                "subscribed_coins": len(self._subscribed_coins),
                "cached_l2_coins": len(self._l2_books),
                "cached_ctx_coins": len(self._asset_ctxs),
                "messages_received": self.messages_received,
                "reconnect_count": self.reconnect_count,
                "l2_hit_rate_pct": round(100.0 * self.ws_hits_l2 / tot_l2, 1) if tot_l2 > 0 else 0.0,
                "oracle_hit_rate_pct": round(100.0 * self.ws_hits_oracle / tot_or, 1) if tot_or > 0 else 0.0,
                "mid_hit_rate_pct": round(100.0 * self.ws_hits_mid / tot_md, 1) if tot_md > 0 else 0.0,
            }
