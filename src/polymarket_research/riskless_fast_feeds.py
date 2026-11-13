"""
Dominus v6.2 Riskless Fast Feeds (`$0/mo` Native, Push & Scoped Public Feeds)
(`src/polymarket_research/riskless_fast_feeds.py`).

Provides lightweight, memory-bounded (`D-010`: `< 20 MiB` combined on 3,907 MiB swapless host),
`100%` read-only (`D-008`), `D-001`-compliant fast data feeds exported cleanly for optional
`try/except ImportError` integration across the Dominus riskless pipeline:

  1. `PythHermesStream` & `fetch_pyth_hermes_latest_sync` (`~$0/mo`):
     Official Pyth Hermes SSE/WS stream (`https://hermes.pyth.network/v2/updates/price/stream`
     & `wss://hermes.pyth.network/ws`) + persistent REST latest snapshot for commodities, equities,
     FX, and crypto (`price`, `conf`, `expo`, `publish_time`) — replacing `90s` Yahoo Finance polls.
  2. `PolygonScopedLogsWs` (`$0/mo`):
     Scoped Polygon PoS `eth_subscribe("logs", ...)` WebSocket listener targeting ONLY
     `ProposePrice` / `DisputePrice` / `Settle` (`MOOV2`, `OOV2`), `ConditionResolution` (`CTF_V1`),
     and optional funder-indexed `PayoutRedemption` (`CTF_V1`, `NEG_RISK_ADAPTER_V2`).
     Strictly quarantines `D-001` disputed `KMIA` markets (`6707503`, `6707502`).
  3. `HyperliquidCoinbaseWs` (`$0/mo`, read-only public market data):
     Hyperliquid public WS (`wss://api.hyperliquid.xyz/ws`, `allMids` / `trades` for `HYPE` & spot-perp
     discovery) + Coinbase Advanced public WS (`wss://advanced-trade-ws.coinbase.com`, `ticker`).
  4. `DeribitPublicWs` (`$0/mo`, read-only public market data):
     Deribit v2 public WS (`wss://www.deribit.com/ws/api/v2`, bounded option `ticker`/`book` cache)
     for `DERIBIT_VERTICAL_SUPER_REP`.
  5. `MacroEventFeedClient` (`$0/mo`):
     Catalyst-window gated Fed monetary RSS, SEC EDGAR submissions (with compliant `User-Agent`),
     and optional BLS v2 (strict keyless daily quota guard when `BLS_API_KEY` is unset).
  6. `fetch_live_cad_usd_sync` (`$0/mo`):
     Live intraday `CAD/USD` resolver (IBKR `CAD.USD` -> Pyth Hermes `FX.USD/CAD` -> Coinbase `USD-CAD`)
     for `XV_FX_INVARIANT_CAD_USD_BOX`, never silently using once-daily Bank of Canada closing rates.
"""

from __future__ import annotations

import asyncio
from collections import deque
import json
import logging
import math
import os
import re
import threading
import time
from typing import Any, Callable, Deque, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Tuple
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

try:
    import orjson as _orjson  # type: ignore
except ImportError:  # pragma: no cover
    _orjson = None

try:
    import requests as _requests  # type: ignore
except ImportError:  # pragma: no cover
    _requests = None

try:
    import aiohttp as _aiohttp  # type: ignore
except ImportError:  # pragma: no cover
    _aiohttp = None

try:
    import websockets as _websockets  # type: ignore
except ImportError:  # pragma: no cover
    _websockets = None

logger = logging.getLogger("RisklessFastFeeds")

# `D-001`: Absolute non-interference on disputed KMIA markets
FROZEN_KMIA_MARKET_IDS: FrozenSet[str] = frozenset({"6707503", "6707502"})

# Official Endpoints (`$0/mo` public read-only)
PYTH_HERMES_BASE_URL = "https://hermes.pyth.network"
PYTH_HERMES_WS_URL = "wss://hermes.pyth.network/ws"
POLYGON_PUBLIC_WSS_URLS: Tuple[str, ...] = (
    "wss://polygon-bor-rpc.publicnode.com",
    "wss://1rpc.io/matic",
)
HYPERLIQUID_PUBLIC_WS_URL = "wss://api.hyperliquid.xyz/ws"
COINBASE_ADVANCED_WS_URL = "wss://advanced-trade-ws.coinbase.com"
DERIBIT_PUBLIC_WS_URL = "wss://www.deribit.com/ws/api/v2"
FED_PRESS_MONETARY_RSS_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"
SEC_EDGAR_SUBMISSIONS_TMPL = "https://data.sec.gov/submissions/CIK{cik10}.json"
BLS_PUBLIC_API_V2_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
COINBASE_SPOT_USDCAD_URL = "https://api.coinbase.com/v2/prices/USD-CAD/spot"

# Verified Polygon Contracts (`riskless_protocol_v2_expansion.py:11675-11680` & `POLYMARKET_ONCHAIN_MOF_AUDIT.md:45-50`)
POLYGON_MOOV2_ADDR = "0x2c0367a9db231ddebd88a94b4f6461a6e47c58b1"
POLYGON_OOV2_ADDR = "0xee3afe347d5c74317041e2618c49534daf887c24"
POLYGON_CTF_V1_ADDR = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
POLYGON_NEG_RISK_ADAPTER_V2_ADDR = "0xada2005600dec949baf300f4c6120000bdb6eaab"

TOPIC_OO_PROPOSE_PRICE = "0x6e51dd00371aabffa82cd401592f76ed51e98a9ea4b58751c70463a2c78b5ca1"
TOPIC_OO_DISPUTE_PRICE = "0x5165909c3d1c01c5d1e121ac6f6d01dda1ba24bc9e1f975b5a375339c15be7f3"

_ANC_MARKET_ID_RE = re.compile(r"market_id:\s*(\d{5,9})")

# Verified Pyth Network v2 Price Feed IDs (64-hex lowercase, `0x` stripped for uniform lookup)
DEFAULT_PYTH_FEED_IDS: Dict[str, str] = {
    "BTC": "e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
    "ETH": "ff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",
    "SOL": "ef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d",
    "XRP": "ec5d399846a9209f3fe5881d70aae9268c94339ff9817e8d18ff19fa05eea1c8",
    "BNB": "2f95862b045670cd22bee3114c39763a4a08beeb663b145d283c31d7d1101c4f",
    "DOGE": "dcef50dd0a4cd2dcc17e45df1676dcb336a11a61c69df7a0299b0150c672d25c",
    "XAU": "765d2ba906dbc32ca17cc11f5310a89e9ee1f6420508c63861f2f8ba4ee34bb2",
    "XAG": "f2fb02c32b055c805e7238d628e5e9dadef274376114eb1f012337cabe93871e",
    "SPY": "19e09bb805456ada3979a7d1cbb4b6d63babc3a0f8e8a9509f6804c4e1d611f5",
    "QQQ": "9695e2b96ea7b3859da9ed25b7a46a920a776e2fdae19a7bcfdf2b219230452d",
    "NVDA": "b1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593",
    "TSLA": "16dad506d7db8da01c87581c87ca897a012a153557d4d578c3b9c9e1bc0632f1",
    "AAPL": "49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688",
    "MSFT": "d0ca23c1cc005e004ccf1db5bf76aeb6a49218f43dac3d4b275e92de12ded4d1",
    "AMZN": "b5d0e0fa58a1f8b81498ae670ce22c8759140f2a5db4b0715e8a588cfd970a75",
    "GOOGL": "5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6",
    "META": "78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe",
    "NFLX": "8376cfd7ca8bcdf372ced05307b24dced1f15b1afafdeff715664598f15a3dd2",
    "COIN": "f0524891463a2f2e59f96d8be982a9df07cf3807a323502264fa52604b04c9a3",
    "USDCAD": "3112b03a41c910ed446852aacf67118cb1bec67b2cd0b9a214c58cc0eaa2ecca",
}
DEFAULT_PYTH_FEED_ALIASES: Dict[str, str] = {
    "XAUUSD": "XAU",
    "GC": "XAU",
    "GC=F": "XAU",
    "XAGUSD": "XAG",
    "SI": "XAG",
    "SI=F": "XAG",
    "FX.USD/CAD": "USDCAD",
    "USD/CAD": "USDCAD",
}


def _fast_loads(raw: Any) -> Any:
    if isinstance(raw, (bytes, bytearray, str)):
        if _orjson is not None:
            return _orjson.loads(raw)
        return json.loads(raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else raw)
    return raw


def _fast_dumps(obj: Any) -> str:
    if _orjson is not None:
        return _orjson.dumps(obj).decode("utf-8")
    return json.dumps(obj, separators=(",", ":"))


def _sf(val: Any, default: float = 0.0) -> float:
    if val is None or isinstance(val, bool) or val == "":
        return default
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _normalize_feed_id(fid: str) -> str:
    s = str(fid or "").strip().lower()
    return s[2:] if s.startswith("0x") else s


# ---------------------------------------------------------------------------
# Pure-Python Keccak-256 fallback (for environments without `eth_utils`/`pycryptodome`)
# ---------------------------------------------------------------------------
_KECCAK_RC = (
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
)
_KECCAK_ROT = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)
_MASK64 = 0xFFFFFFFFFFFFFFFF


def keccak256_hex(text: str) -> str:
    """Computes `0x`-prefixed Keccak-256 digest of an Ethereum event signature using `eth_utils` or stdlib fallback."""
    try:
        from eth_utils import keccak  # type: ignore

        return "0x" + keccak(text=text).hex().replace("0x", "")
    except Exception:
        pass

    data = bytearray(text.encode("utf-8"))
    rate = 136  # 1088 bits for keccak-256
    data.append(0x01)
    while len(data) % rate != 0:
        data.append(0x00)
    data[-1] ^= 0x80

    state = [[0] * 5 for _ in range(5)]
    for off in range(0, len(data), rate):
        blk = data[off : off + rate]
        for i in range(17):
            lane = int.from_bytes(blk[i * 8 : (i + 1) * 8], "little")
            state[i % 5][i // 5] ^= lane
        for rc in _KECCAK_RC:
            c = [state[x][0] ^ state[x][1] ^ state[x][2] ^ state[x][3] ^ state[x][4] for x in range(5)]
            d = [c[(x - 1) % 5] ^ (((c[(x + 1) % 5] << 1) | (c[(x + 1) % 5] >> 63)) & _MASK64) for x in range(5)]
            for x in range(5):
                for y in range(5):
                    state[x][y] ^= d[x]
            b = [[0] * 5 for _ in range(5)]
            for x in range(5):
                for y in range(5):
                    r = _KECCAK_ROT[x][y]
                    v = state[x][y]
                    b[y][(2 * x + 3 * y) % 5] = ((v << r) | (v >> (64 - r))) & _MASK64 if r else v
            for x in range(5):
                for y in range(5):
                    state[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y])
            state[0][0] ^= rc

    out = bytearray()
    for i in range(4):
        out.extend(state[i % 5][i // 5].to_bytes(8, "little"))
    return "0x" + out.hex()


TOPIC_CTF_CONDITION_RESOLUTION = keccak256_hex("ConditionResolution(bytes32,address,bytes32,uint256,uint256[])")
TOPIC_CTF_PAYOUT_REDEMPTION = keccak256_hex("PayoutRedemption(address,address,bytes32,bytes32,uint256[],uint256)")
TOPIC_NEGRISK_PAYOUT_REDEMPTION = keccak256_hex("PayoutRedemption(address,bytes32,uint256[],uint256)")
TOPIC_OO_SETTLE = keccak256_hex("Settle(address,address,address,bytes32,uint256,bytes,int256)")


def _make_requests_session(user_agent: str = "DominusRisklessFeeds/1.0") -> Any:
    if _requests is None:
        return None
    sess = _requests.Session()
    sess.headers.update({"User-Agent": user_agent, "Accept": "application/json", "Connection": "keep-alive"})
    return sess


_SYNC_HTTP_LOCAL = threading.local()


def _get_sync_session() -> Any:
    sess = getattr(_SYNC_HTTP_LOCAL, "session", None)
    if sess is None:
        sess = _make_requests_session()
        _SYNC_HTTP_LOCAL.session = sess
    return sess


def _http_get_json_sync(url: str, *, timeout: float = 2.5, session: Any = None, headers: Optional[Mapping[str, str]] = None) -> Any:
    sess = session or _get_sync_session()
    if sess is not None:
        resp = sess.get(url, timeout=timeout, headers=dict(headers or {}))
        if int(getattr(resp, "status_code", 0)) != 200:
            return None
        return _fast_loads(resp.content)
    req_headers = {"User-Agent": "DominusRisklessFeeds/1.0", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return _fast_loads(resp.read())


# ---------------------------------------------------------------------------
# 1. Pyth Hermes Real-Time SSE/WS Stream & Sync Snapshot (`$0/mo`)
# ---------------------------------------------------------------------------

def _parse_pyth_parsed_entries(
    payload: Any,
    id_to_symbol: Mapping[str, str],
    rx_ts: Optional[float] = None,
) -> Dict[str, Dict[str, Any]]:
    now_f = float(time.time() if rx_ts is None else rx_ts)
    if not isinstance(payload, Mapping):
        return {}
    rows = payload.get("parsed")
    if not isinstance(rows, list):
        # Hermes WS emits `{"type": "price_update", "price_feed": {...}}`
        pf = payload.get("price_feed")
        rows = [pf] if isinstance(pf, Mapping) else []
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        fid = _normalize_feed_id(str(row.get("id") or ""))
        if not fid:
            continue
        pr = row.get("price")
        if not isinstance(pr, Mapping):
            continue
        raw_p = _sf(pr.get("price"), 0.0)
        raw_c = _sf(pr.get("conf"), 0.0)
        expo = int(_sf(pr.get("expo"), 0))
        pub_ts = _sf(pr.get("publish_time"), now_f)
        scale = 10.0 ** expo
        px = raw_p * scale
        conf = abs(raw_c * scale)
        if px <= 0.0 or not math.isfinite(px):
            continue
        sym = id_to_symbol.get(fid, fid)
        out[sym] = {
            "symbol": sym,
            "feed_id": fid,
            "price": px,
            "conf": conf,
            "expo": expo,
            "publish_time": pub_ts,
            "rx_ts": now_f,
            "source": "pyth_hermes",
        }
    return out


def fetch_pyth_hermes_latest_sync(
    symbols_or_feed_ids: Sequence[str],
    *,
    symbol_to_feed_id: Optional[Mapping[str, str]] = None,
    timeout: float = 2.5,
    session: Any = None,
    base_url: str = PYTH_HERMES_BASE_URL,
) -> Dict[str, Dict[str, Any]]:
    """
    Fetches latest Pyth Hermes prices + confidence intervals via persistent REST
    (`GET /v2/updates/price/latest?ids[]=...&parsed=true`, `$0/mo`).
    """
    feed_map = dict(DEFAULT_PYTH_FEED_IDS)
    if symbol_to_feed_id:
        for k, v in symbol_to_feed_id.items():
            feed_map[str(k).strip().upper()] = _normalize_feed_id(v)

    id_to_sym: Dict[str, str] = {}
    ids_q: List[str] = []
    for item in symbols_or_feed_ids:
        raw = str(item or "").strip()
        if not raw:
            continue
        up = raw.upper()
        canon = DEFAULT_PYTH_FEED_ALIASES.get(up, up)
        if canon in feed_map:
            fid = _normalize_feed_id(feed_map[canon])
            sym_lbl = canon
        else:
            fid = _normalize_feed_id(raw)
            sym_lbl = raw
        if len(fid) == 64:
            ids_q.append(fid)
            id_to_sym[fid] = sym_lbl

    if not ids_q:
        return {}
    qs = "&".join(f"ids[]={urllib.parse.quote(fid)}" for fid in dict.fromkeys(ids_q))
    url = f"{base_url.rstrip('/')}/v2/updates/price/latest?{qs}&parsed=true"
    try:
        data = _http_get_json_sync(url, timeout=timeout, session=session)
        return _parse_pyth_parsed_entries(data, id_to_sym)
    except Exception as exc:
        logger.debug(f"Pyth Hermes latest sync notice: {exc}")
        return {}


class PythHermesStream:
    """
    Lightweight `$0/mo` streaming Pyth Hermes client (SSE `/v2/updates/price/stream`
    or WS `wss://hermes.pyth.network/ws`) maintaining bounded latest quotes + `conf` bands.
    """

    def __init__(
        self,
        symbols_or_feed_ids: Sequence[str] = ("BTC", "ETH", "SOL", "XAU", "XAG", "SPY", "QQQ", "NVDA", "TSLA", "USDCAD"),
        *,
        symbol_to_feed_id: Optional[Mapping[str, str]] = None,
        prefer_sse: bool = True,
        base_url: str = PYTH_HERMES_BASE_URL,
        ws_url: str = PYTH_HERMES_WS_URL,
        on_quote: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._ws_url = ws_url
        self._prefer_sse = bool(prefer_sse)
        self._on_quote = on_quote
        self._lock = threading.RLock()
        self._feed_map: Dict[str, str] = dict(DEFAULT_PYTH_FEED_IDS)
        if symbol_to_feed_id:
            for k, v in symbol_to_feed_id.items():
                self._feed_map[str(k).strip().upper()] = _normalize_feed_id(v)
        self._id_to_sym: Dict[str, str] = {}
        self._feed_ids: List[str] = []
        self.set_symbols(symbols_or_feed_ids)
        self._quotes: Dict[str, Dict[str, Any]] = {}
        self._connected: bool = False
        self._last_rx_mono: float = 0.0
        self._stop_event = threading.Event()
        self._bg_thread: Optional[threading.Thread] = None

    def set_symbols(self, symbols_or_feed_ids: Sequence[str]) -> None:
        ids_new: List[str] = []
        id_map: Dict[str, str] = {}
        for item in symbols_or_feed_ids:
            raw = str(item or "").strip()
            if not raw:
                continue
            up = raw.upper()
            canon = DEFAULT_PYTH_FEED_ALIASES.get(up, up)
            fid = _normalize_feed_id(self._feed_map.get(canon, raw))
            if len(fid) == 64:
                ids_new.append(fid)
                id_map[fid] = canon if canon in self._feed_map else raw
        with self._lock:
            self._feed_ids = list(dict.fromkeys(ids_new))
            self._id_to_sym = id_map

    def process_payload(self, raw_payload: Any, rx_ts: Optional[float] = None) -> int:
        if isinstance(raw_payload, (str, bytes, bytearray)):
            txt = raw_payload.decode("utf-8", errors="ignore") if isinstance(raw_payload, (bytes, bytearray)) else raw_payload
            s = txt.strip()
            if not s or s.startswith(":"):
                return 0
            if s.startswith("data:"):
                s = s[5:].strip()
            if not s:
                return 0
            data = _fast_loads(s)
        else:
            data = raw_payload
        with self._lock:
            id_map = dict(self._id_to_sym)
        parsed = _parse_pyth_parsed_entries(data, id_map, rx_ts=rx_ts)
        if not parsed:
            return 0
        with self._lock:
            self._last_rx_mono = time.monotonic()
            for sym, q in parsed.items():
                self._quotes[sym] = q
        if self._on_quote is not None:
            for sym, q in parsed.items():
                try:
                    self._on_quote(sym, q)
                except Exception:
                    pass
        return len(parsed)

    def get_latest(self, symbol: str, max_age_sec: float = 5.0) -> Optional[Dict[str, Any]]:
        up = DEFAULT_PYTH_FEED_ALIASES.get(str(symbol or "").strip().upper(), str(symbol or "").strip().upper())
        now_f = time.time()
        with self._lock:
            q = self._quotes.get(up)
            if q is None:
                return None
            if (now_f - float(q.get("rx_ts") or 0.0)) > max_age_sec:
                return None
            return dict(q)

    def get_price(self, symbol: str, max_age_sec: float = 5.0) -> Optional[float]:
        q = self.get_latest(symbol, max_age_sec=max_age_sec)
        return float(q["price"]) if q is not None else None

    def is_healthy(self, max_silence_sec: float = 10.0) -> bool:
        with self._lock:
            return self._connected and (time.monotonic() - self._last_rx_mono) <= max_silence_sec

    async def _run_sse_once(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        if _aiohttp is None:
            raise RuntimeError("aiohttp unavailable")
        with self._lock:
            ids = list(self._feed_ids)
        if not ids:
            await asyncio.sleep(1.0)
            return
        qs = "&".join(f"ids[]={urllib.parse.quote(fid)}" for fid in ids)
        url = f"{self._base_url}/v2/updates/price/stream?{qs}&parsed=true"
        timeout = _aiohttp.ClientTimeout(total=None, sock_connect=6.0, sock_read=15.0)
        async with _aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url, headers={"Accept": "text/event-stream", "User-Agent": "DominusPyth/1.0"}) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Pyth SSE status={resp.status}")
                with self._lock:
                    self._connected = True
                    self._last_rx_mono = time.monotonic()
                while not (stop_check and stop_check()) and not self._stop_event.is_set():
                    line_b = await resp.content.readline()
                    if not line_b:
                        break
                    self.process_payload(line_b)

    async def _run_ws_once(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        if _websockets is None:
            raise RuntimeError("websockets unavailable")
        with self._lock:
            ids = list(self._feed_ids)
        if not ids:
            await asyncio.sleep(1.0)
            return
        async with _websockets.connect(self._ws_url, ping_interval=15, ping_timeout=10, compression=None) as ws:
            await ws.send(_fast_dumps({"type": "subscribe", "ids": [f"0x{fid}" for fid in ids]}))
            with self._lock:
                self._connected = True
                self._last_rx_mono = time.monotonic()
            while not (stop_check and stop_check()) and not self._stop_event.is_set():
                msg = await asyncio.wait_for(ws.recv(), timeout=12.0)
                self.process_payload(msg)

    async def run_forever(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        backoff = 0.5
        while not (stop_check and stop_check()) and not self._stop_event.is_set():
            try:
                if self._prefer_sse and _aiohttp is not None:
                    await self._run_sse_once(stop_check)
                elif _websockets is not None:
                    await self._run_ws_once(stop_check)
                else:
                    # Graceful periodic sync fallback when neither aiohttp nor websockets is available
                    with self._lock:
                        syms = list(self._id_to_sym.values())
                    snap = fetch_pyth_hermes_latest_sync(syms, symbol_to_feed_id=self._feed_map, base_url=self._base_url)
                    if snap:
                        with self._lock:
                            self._connected = True
                            self._last_rx_mono = time.monotonic()
                            self._quotes.update(snap)
                    await asyncio.sleep(1.5)
                backoff = 0.5
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"PythHermesStream reconnect notice: {exc}")
                with self._lock:
                    self._connected = False
                await asyncio.sleep(backoff)
                backoff = min(10.0, backoff * 1.8)

    def start_background(self) -> None:
        if self._bg_thread is not None and self._bg_thread.is_alive():
            return
        self._stop_event.clear()
        self._bg_thread = threading.Thread(
            target=lambda: asyncio.run(self.run_forever()),
            name="PythHermesStream",
            daemon=True,
        )
        self._bg_thread.start()

    def stop(self) -> None:
        self._stop_event.set()


# ---------------------------------------------------------------------------
# 2. Polygon Scoped `eth_subscribe("logs")` WebSocket (`$0/mo`, `D-001` Safe)
# ---------------------------------------------------------------------------

def _pad_topic_address(addr: str) -> str:
    clean = str(addr or "").strip().lower()
    if clean.startswith("0x"):
        clean = clean[2:]
    if len(clean) != 40:
        return ""
    return "0x" + clean.zfill(64)


class PolygonScopedLogsWs:
    """
    Scoped Polygon PoS `eth_subscribe("logs", ...)` WebSocket listener (`$0/mo`).
      - Subscription 1: `ProposePrice`, `DisputePrice`, `Settle` (`MOOV2`, `OOV2`) + `ConditionResolution` (`CTF_V1`).
      - Subscription 2 (when `funder_address` set): funder-indexed `PayoutRedemption` on `[CTF_V1, NEG_RISK_ADAPTER_V2]`.
    Strictly enforces `D-001` non-interference on disputed `KMIA` markets (`6707503`, `6707502`).
    """

    def __init__(
        self,
        *,
        wss_urls: Optional[Sequence[str]] = None,
        funder_address: str = "",
        quarantined_market_ids: FrozenSet[str] = FROZEN_KMIA_MARKET_IDS,
        max_events: int = 256,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        env_wss = os.environ.get("POLYGON_WSS_URL", "").strip()
        urls = [env_wss] if env_wss else []
        urls.extend(wss_urls or POLYGON_PUBLIC_WSS_URLS)
        self._wss_urls: Tuple[str, ...] = tuple(dict.fromkeys(u for u in urls if u))
        self._funder_topic = _pad_topic_address(funder_address)
        self._quarantined_ids = frozenset(str(x) for x in quarantined_market_ids)
        self._on_event = on_event
        self._lock = threading.RLock()
        self._events: Deque[Dict[str, Any]] = deque(maxlen=max(32, int(max_events)))
        self._oo_status_by_mid: Dict[str, Dict[str, Any]] = {}
        self._condition_resolutions: Dict[str, Dict[str, Any]] = {}
        self._connected: bool = False
        self._last_rx_mono: float = 0.0
        self._stop_event = threading.Event()
        self._bg_thread: Optional[threading.Thread] = None

    def build_subscribe_payloads(self) -> List[Dict[str, Any]]:
        reqs: List[Dict[str, Any]] = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": [
                    "logs",
                    {
                        "address": [POLYGON_MOOV2_ADDR, POLYGON_OOV2_ADDR, POLYGON_CTF_V1_ADDR],
                        "topics": [
                            [
                                TOPIC_OO_PROPOSE_PRICE,
                                TOPIC_OO_DISPUTE_PRICE,
                                TOPIC_OO_SETTLE,
                                TOPIC_CTF_CONDITION_RESOLUTION,
                            ]
                        ],
                    },
                ],
            }
        ]
        if self._funder_topic:
            reqs.append(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "eth_subscribe",
                    "params": [
                        "logs",
                        {
                            "address": [POLYGON_CTF_V1_ADDR, POLYGON_NEG_RISK_ADAPTER_V2_ADDR],
                            "topics": [
                                [TOPIC_CTF_PAYOUT_REDEMPTION, TOPIC_NEGRISK_PAYOUT_REDEMPTION],
                                self._funder_topic,
                            ],
                        },
                    ],
                }
            )
        return reqs

    @staticmethod
    def _extract_market_ids_from_hex_data(data_hex: str) -> List[str]:
        if not data_hex or not str(data_hex).startswith("0x") or len(data_hex) < 10:
            return []
        try:
            raw_bytes = bytes.fromhex(str(data_hex)[2:])
            txt = raw_bytes.decode("utf-8", errors="ignore")
            return list(dict.fromkeys(_ANC_MARKET_ID_RE.findall(txt)))
        except Exception:
            return []

    def process_ws_message(self, raw_msg: Any) -> Optional[Dict[str, Any]]:
        try:
            msg = _fast_loads(raw_msg) if isinstance(raw_msg, (str, bytes, bytearray)) else raw_msg
        except Exception:
            return None
        if not isinstance(msg, Mapping):
            return None
        with self._lock:
            self._last_rx_mono = time.monotonic()
        if msg.get("method") != "eth_subscription":
            return None
        params = msg.get("params")
        log_obj = params.get("result") if isinstance(params, Mapping) else None
        if not isinstance(log_obj, Mapping):
            return None

        topics = [str(t).lower() for t in (log_obj.get("topics") or [])]
        if not topics:
            return None
        t0 = topics[0]
        addr = str(log_obj.get("address") or "").lower()
        data_hex = str(log_obj.get("data") or "")
        tx_hash = str(log_obj.get("transactionHash") or "")
        blk_raw = log_obj.get("blockNumber")
        block_num = int(blk_raw, 16) if isinstance(blk_raw, str) and blk_raw.startswith("0x") else int(_sf(blk_raw, 0))
        now_f = time.time()

        event_kind = ""
        if t0 == TOPIC_OO_PROPOSE_PRICE:
            event_kind = "OO_PROPOSE_PRICE"
        elif t0 == TOPIC_OO_DISPUTE_PRICE:
            event_kind = "OO_DISPUTE_PRICE"
        elif t0 == TOPIC_OO_SETTLE:
            event_kind = "OO_SETTLE"
        elif t0 == TOPIC_CTF_CONDITION_RESOLUTION:
            event_kind = "CTF_CONDITION_RESOLUTION"
        elif t0 in (TOPIC_CTF_PAYOUT_REDEMPTION, TOPIC_NEGRISK_PAYOUT_REDEMPTION):
            event_kind = "CTF_PAYOUT_REDEMPTION"
        else:
            return None

        mids = self._extract_market_ids_from_hex_data(data_hex)
        quarantined = any(m in self._quarantined_ids for m in mids)
        cond_id = topics[1] if (event_kind == "CTF_CONDITION_RESOLUTION" and len(topics) > 1) else ""

        evt = {
            "event_kind": event_kind,
            "address": addr,
            "block_number": block_num,
            "tx_hash": tx_hash,
            "market_ids": mids,
            "condition_id": cond_id,
            "quarantined_d001": quarantined,
            "rx_ts": now_f,
        }

        with self._lock:
            if event_kind in ("OO_PROPOSE_PRICE", "OO_DISPUTE_PRICE", "OO_SETTLE"):
                st = "DISPUTED" if event_kind == "OO_DISPUTE_PRICE" else ("SETTLED" if event_kind == "OO_SETTLE" else "PROPOSED")
                for mid in mids:
                    self._oo_status_by_mid[mid] = {
                        "status": st,
                        "event_kind": event_kind,
                        "block_number": block_num,
                        "tx_hash": tx_hash,
                        "quarantined_d001": mid in self._quarantined_ids,
                        "rx_ts": now_f,
                    }
                if len(self._oo_status_by_mid) > 512:
                    oldest = sorted(self._oo_status_by_mid.items(), key=lambda kv: kv[1]["rx_ts"])[:128]
                    for k_o, _ in oldest:
                        self._oo_status_by_mid.pop(k_o, None)
            elif event_kind == "CTF_CONDITION_RESOLUTION" and cond_id:
                self._condition_resolutions[cond_id] = evt
                if len(self._condition_resolutions) > 512:
                    oldest_c = sorted(self._condition_resolutions.items(), key=lambda kv: kv[1]["rx_ts"])[:128]
                    for k_c, _ in oldest_c:
                        self._condition_resolutions.pop(k_c, None)

            if not quarantined:
                self._events.append(evt)

        if not quarantined and self._on_event is not None:
            try:
                self._on_event(evt)
            except Exception:
                pass
        return evt

    def drain_events(self, max_items: int = 64) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        with self._lock:
            while self._events and len(out) < max_items:
                ev = self._events.popleft()
                if not ev.get("quarantined_d001"):
                    out.append(ev)
        return out

    def get_market_oo_status(self, market_id: str, max_age_sec: float = 3600.0) -> Optional[Dict[str, Any]]:
        mid = str(market_id or "").strip()
        if not mid:
            return None
        now_f = time.time()
        with self._lock:
            row = self._oo_status_by_mid.get(mid)
            if row is None or (now_f - float(row["rx_ts"])) > max_age_sec:
                return None
            return dict(row)

    def get_condition_resolution(self, condition_id: str) -> Optional[Dict[str, Any]]:
        cid = str(condition_id or "").strip().lower()
        if not cid:
            return None
        with self._lock:
            row = self._condition_resolutions.get(cid)
            return dict(row) if row is not None else None

    async def run_forever(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        if _websockets is None or not self._wss_urls:
            return
        idx = 0
        backoff = 1.0
        while not (stop_check and stop_check()) and not self._stop_event.is_set():
            url = self._wss_urls[idx % len(self._wss_urls)]
            idx += 1
            try:
                async with _websockets.connect(url, ping_interval=20, ping_timeout=15, compression=None) as ws:
                    for req in self.build_subscribe_payloads():
                        await ws.send(_fast_dumps(req))
                    with self._lock:
                        self._connected = True
                        self._last_rx_mono = time.monotonic()
                    backoff = 1.0
                    while not (stop_check and stop_check()) and not self._stop_event.is_set():
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        except asyncio.TimeoutError:
                            await ws.send('{"jsonrpc":"2.0","id":99,"method":"eth_blockNumber","params":[]}')
                            continue
                        self.process_ws_message(msg)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"PolygonScopedLogsWs reconnect ({url}): {exc}")
                with self._lock:
                    self._connected = False
                await asyncio.sleep(backoff)
                backoff = min(15.0, backoff * 1.8)

    def start_background(self) -> None:
        if self._bg_thread is not None and self._bg_thread.is_alive():
            return
        self._stop_event.clear()
        self._bg_thread = threading.Thread(
            target=lambda: asyncio.run(self.run_forever()),
            name="PolygonScopedLogsWs",
            daemon=True,
        )
        self._bg_thread.start()

    def stop(self) -> None:
        self._stop_event.set()


# ---------------------------------------------------------------------------
# 3. Hyperliquid + Coinbase Advanced Read-Only Public WS (`$0/mo`, `D-008`)
# ---------------------------------------------------------------------------

class HyperliquidCoinbaseWs:
    """
    Bounded read-only public market data client (`$0/mo`, zero auth/trading):
      - Hyperliquid `wss://api.hyperliquid.xyz/ws` (`allMids` / `trades` for `HYPE`, `BTC`, `ETH`, `SOL`)
      - Coinbase Advanced `wss://advanced-trade-ws.coinbase.com` (`ticker` for `BTC-USD`, `ETH-USD`, `SOL-USD`, `ZEC-USD`, `USDT-USD`)
    """

    def __init__(
        self,
        *,
        hl_coins: Sequence[str] = ("HYPE", "BTC", "ETH", "SOL"),
        coinbase_products: Sequence[str] = ("BTC-USD", "ETH-USD", "SOL-USD", "ZEC-USD", "USDT-USD"),
    ) -> None:
        self._hl_coins = tuple(str(c).upper() for c in hl_coins)
        self._cb_products = tuple(str(p).upper() for p in coinbase_products)
        self._lock = threading.RLock()
        self._hl_prices: Dict[str, Tuple[float, float]] = {}
        self._cb_prices: Dict[str, Tuple[float, float]] = {}
        self._stop_event = threading.Event()
        self._bg_thread: Optional[threading.Thread] = None

    def process_hyperliquid_message(self, raw_msg: Any, rx_ts: Optional[float] = None) -> int:
        now_f = float(time.time() if rx_ts is None else rx_ts)
        try:
            d = _fast_loads(raw_msg) if isinstance(raw_msg, (str, bytes, bytearray)) else raw_msg
        except Exception:
            return 0
        if not isinstance(d, Mapping):
            return 0
        ch = str(d.get("channel") or "")
        data = d.get("data")
        updates = 0
        with self._lock:
            if ch == "allMids" and isinstance(data, Mapping):
                mids = data.get("mids") if isinstance(data.get("mids"), Mapping) else data
                for coin in self._hl_coins:
                    px = _sf(mids.get(coin), 0.0)
                    if px > 0.0:
                        self._hl_prices[coin] = (px, now_f)
                        updates += 1
            elif ch == "trades" and isinstance(data, list):
                for tr in data:
                    if not isinstance(tr, Mapping):
                        continue
                    coin = str(tr.get("coin") or "").upper()
                    px = _sf(tr.get("px"), 0.0)
                    if coin in self._hl_coins and px > 0.0:
                        self._hl_prices[coin] = (px, now_f)
                        updates += 1
        return updates

    def process_coinbase_message(self, raw_msg: Any, rx_ts: Optional[float] = None) -> int:
        now_f = float(time.time() if rx_ts is None else rx_ts)
        try:
            d = _fast_loads(raw_msg) if isinstance(raw_msg, (str, bytes, bytearray)) else raw_msg
        except Exception:
            return 0
        if not isinstance(d, Mapping):
            return 0
        updates = 0
        if d.get("channel") == "ticker" and isinstance(d.get("events"), list):
            with self._lock:
                for ev in d["events"]:
                    if not isinstance(ev, Mapping):
                        continue
                    for tk in ev.get("tickers") or ():
                        if not isinstance(tk, Mapping):
                            continue
                        pid = str(tk.get("product_id") or "").upper()
                        px = _sf(tk.get("price"), 0.0)
                        if px > 0.0 and pid:
                            self._cb_prices[pid] = (px, now_f)
                            updates += 1
        elif d.get("type") == "ticker":
            pid = str(d.get("product_id") or "").upper()
            px = _sf(d.get("price"), 0.0)
            if px > 0.0 and pid:
                with self._lock:
                    self._cb_prices[pid] = (px, now_f)
                updates += 1
        return updates

    def get_price(self, symbol: str, *, venue: Optional[str] = None, max_age_sec: float = 5.0) -> Optional[float]:
        sym = str(symbol or "").strip().upper()
        now_f = time.time()
        with self._lock:
            if venue == "hyperliquid":
                row = self._hl_prices.get(sym)
                return row[0] if (row and (now_f - row[1]) <= max_age_sec) else None
            if venue == "coinbase":
                pid = sym if "-" in sym else f"{sym}-USD"
                row = self._cb_prices.get(pid)
                return row[0] if (row and (now_f - row[1]) <= max_age_sec) else None
            pid = sym if "-" in sym else f"{sym}-USD"
            cb_row = self._cb_prices.get(pid)
            if cb_row and (now_f - cb_row[1]) <= max_age_sec:
                return cb_row[0]
            hl_row = self._hl_prices.get(sym.split("-")[0])
            if hl_row and (now_f - hl_row[1]) <= max_age_sec:
                return hl_row[0]
        return None

    async def _run_hl(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        if _websockets is None:
            return
        backoff = 1.0
        while not (stop_check and stop_check()) and not self._stop_event.is_set():
            try:
                async with _websockets.connect(HYPERLIQUID_PUBLIC_WS_URL, ping_interval=20, ping_timeout=10, compression=None) as ws:
                    await ws.send(_fast_dumps({"method": "subscribe", "subscription": {"type": "allMids"}}))
                    backoff = 1.0
                    while not (stop_check and stop_check()) and not self._stop_event.is_set():
                        msg = await asyncio.wait_for(ws.recv(), timeout=25.0)
                        self.process_hyperliquid_message(msg)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"Hyperliquid WS reconnect: {exc}")
                await asyncio.sleep(backoff)
                backoff = min(15.0, backoff * 1.8)

    async def _run_cb(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        if _websockets is None:
            return
        backoff = 1.0
        while not (stop_check and stop_check()) and not self._stop_event.is_set():
            try:
                async with _websockets.connect(COINBASE_ADVANCED_WS_URL, ping_interval=20, ping_timeout=10, compression=None) as ws:
                    await ws.send(_fast_dumps({"type": "subscribe", "product_ids": list(self._cb_products), "channel": "ticker"}))
                    backoff = 1.0
                    while not (stop_check and stop_check()) and not self._stop_event.is_set():
                        msg = await asyncio.wait_for(ws.recv(), timeout=25.0)
                        self.process_coinbase_message(msg)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"Coinbase Advanced WS reconnect: {exc}")
                await asyncio.sleep(backoff)
                backoff = min(15.0, backoff * 1.8)

    async def run_forever(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        await asyncio.gather(self._run_hl(stop_check), self._run_cb(stop_check))

    def start_background(self) -> None:
        if self._bg_thread is not None and self._bg_thread.is_alive():
            return
        self._stop_event.clear()
        self._bg_thread = threading.Thread(
            target=lambda: asyncio.run(self.run_forever()),
            name="HyperliquidCoinbaseWs",
            daemon=True,
        )
        self._bg_thread.start()

    def stop(self) -> None:
        self._stop_event.set()


# ---------------------------------------------------------------------------
# 4. Deribit v2 Read-Only Public WebSocket (`$0/mo`, Shadow / Gate G)
# ---------------------------------------------------------------------------

class DeribitPublicWs:
    """Bounded read-only Deribit v2 WS quote cache for `DERIBIT_VERTICAL_SUPER_REP`."""

    def __init__(self, instruments: Sequence[str] = (), *, ws_url: str = DERIBIT_PUBLIC_WS_URL) -> None:
        self._ws_url = ws_url
        self._lock = threading.RLock()
        self._instruments: List[str] = list(dict.fromkeys(str(i).strip() for i in instruments if i))[:64]
        self._quotes: Dict[str, Dict[str, Any]] = {}
        self._stop_event = threading.Event()
        self._bg_thread: Optional[threading.Thread] = None

    def set_instruments(self, instruments: Sequence[str]) -> None:
        clean = list(dict.fromkeys(str(i).strip() for i in instruments if i))[:64]
        with self._lock:
            self._instruments = clean

    @staticmethod
    def build_subscribe_frame(instruments: Sequence[str], *, channel_prefix: str = "ticker", interval: str = "100ms") -> str:
        channels = [f"{channel_prefix}.{str(inst).strip()}.{interval}" for inst in instruments if inst]
        return _fast_dumps(
            {
                "jsonrpc": "2.0",
                "id": 42,
                "method": "public/subscribe",
                "params": {"channels": channels[:64]},
            }
        )

    def process_ws_message(self, raw_msg: Any, rx_ts: Optional[float] = None) -> bool:
        now_f = float(time.time() if rx_ts is None else rx_ts)
        try:
            d = _fast_loads(raw_msg) if isinstance(raw_msg, (str, bytes, bytearray)) else raw_msg
        except Exception:
            return False
        if not isinstance(d, Mapping) or d.get("method") != "subscription":
            return False
        params = d.get("params")
        data = params.get("data") if isinstance(params, Mapping) else None
        if not isinstance(data, Mapping):
            return False
        inst = str(data.get("instrument_name") or "").strip()
        if not inst:
            return False
        quote = {
            "instrument_name": inst,
            "best_bid_price": _sf(data.get("best_bid_price"), 0.0),
            "best_bid_amount": _sf(data.get("best_bid_amount"), 0.0),
            "best_ask_price": _sf(data.get("best_ask_price"), 0.0),
            "best_ask_amount": _sf(data.get("best_ask_amount"), 0.0),
            "mark_price": _sf(data.get("mark_price"), 0.0),
            "underlying_price": _sf(data.get("underlying_price"), 0.0),
            "rx_ts": now_f,
        }
        with self._lock:
            self._quotes[inst] = quote
            if len(self._quotes) > 128:
                oldest = sorted(self._quotes.items(), key=lambda kv: kv[1]["rx_ts"])[:32]
                for k_o, _ in oldest:
                    self._quotes.pop(k_o, None)
        return True

    def get_option_quote(self, instrument_name: str, max_age_sec: float = 5.0) -> Optional[Dict[str, Any]]:
        now_f = time.time()
        with self._lock:
            q = self._quotes.get(str(instrument_name or "").strip())
            if q is None or (now_f - float(q["rx_ts"])) > max_age_sec:
                return None
            return dict(q)

    def get_quotes_by_currency(self, currency: str, max_age_sec: float = 5.0) -> Dict[str, Dict[str, Any]]:
        prefix = f"{str(currency or '').strip().upper()}-"
        now_f = time.time()
        with self._lock:
            return {
                k: dict(v)
                for k, v in self._quotes.items()
                if k.startswith(prefix) and (now_f - float(v["rx_ts"])) <= max_age_sec
            }

    async def run_forever(self, stop_check: Optional[Callable[[], bool]] = None) -> None:
        if _websockets is None:
            return
        backoff = 1.0
        while not (stop_check and stop_check()) and not self._stop_event.is_set():
            with self._lock:
                insts = list(self._instruments)
            if not insts:
                await asyncio.sleep(2.0)
                continue
            try:
                async with _websockets.connect(self._ws_url, ping_interval=20, ping_timeout=10, compression=None) as ws:
                    await ws.send(self.build_subscribe_frame(insts))
                    backoff = 1.0
                    while not (stop_check and stop_check()) and not self._stop_event.is_set():
                        msg = await asyncio.wait_for(ws.recv(), timeout=20.0)
                        self.process_ws_message(msg)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"DeribitPublicWs reconnect: {exc}")
                await asyncio.sleep(backoff)
                backoff = min(15.0, backoff * 1.8)

    def start_background(self) -> None:
        if self._bg_thread is not None and self._bg_thread.is_alive():
            return
        self._stop_event.clear()
        self._bg_thread = threading.Thread(
            target=lambda: asyncio.run(self.run_forever()),
            name="DeribitPublicWs",
            daemon=True,
        )
        self._bg_thread.start()

    def stop(self) -> None:
        self._stop_event.set()


# ---------------------------------------------------------------------------
# 5. Macro / Official Catalyst Feed Client (`$0/mo`, Window-Gated)
# ---------------------------------------------------------------------------

class MacroEventFeedClient:
    """
    Catalyst-window gated official macro & corporate trigger client (`$0/mo`):
      - Fed Monetary Policy RSS (`federalreserve.gov/feeds/press_monetary.xml`)
      - SEC EDGAR Submissions (`data.sec.gov/submissions/CIK{cik10}.json`, compliant `User-Agent`)
      - Optional BLS Public API v2 (`BLS_API_KEY` env; hard keyless cap `<= 20/day` vs 25/day limit)
    """

    def __init__(self, *, sec_user_agent: Optional[str] = None, bls_api_key: Optional[str] = None) -> None:
        self._sec_ua = str(
            sec_user_agent
            or os.environ.get("SEC_EDGAR_USER_AGENT")
            or "DominusRisklessResearch/1.0 contact@dominus-research.local"
        ).strip()
        self._bls_key = str(bls_api_key or os.environ.get("BLS_API_KEY") or "").strip()
        self._lock = threading.RLock()
        self._etags: Dict[str, str] = {}
        self._last_modified: Dict[str, str] = {}
        self._bls_day_str: str = ""
        self._bls_daily_calls: int = 0
        self._recent_releases: Deque[Dict[str, str]] = deque(maxlen=64)

    @staticmethod
    def parse_fed_rss_xml(xml_text: str) -> List[Dict[str, str]]:
        if not xml_text or not str(xml_text).strip():
            return []
        root = ET.fromstring(xml_text)
        items: List[Dict[str, str]] = []
        for it in root.findall(".//item")[:20]:
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub = (it.findtext("pubDate") or "").strip()
            if title:
                items.append({"title": title, "link": link, "pub_date": pub})
        return items

    def fetch_fed_rss_sync(self, *, in_window: bool = True, timeout: float = 3.0) -> List[Dict[str, str]]:
        if not in_window:
            return []
        try:
            sess = _get_sync_session()
            hdrs = {"User-Agent": self._sec_ua, "Accept": "application/rss+xml, application/xml"}
            with self._lock:
                if FED_PRESS_MONETARY_RSS_URL in self._etags:
                    hdrs["If-None-Match"] = self._etags[FED_PRESS_MONETARY_RSS_URL]
                if FED_PRESS_MONETARY_RSS_URL in self._last_modified:
                    hdrs["If-Modified-Since"] = self._last_modified[FED_PRESS_MONETARY_RSS_URL]
            if sess is not None:
                resp = sess.get(FED_PRESS_MONETARY_RSS_URL, headers=hdrs, timeout=timeout)
                if resp.status_code == 304 or resp.status_code != 200:
                    return []
                with self._lock:
                    if resp.headers.get("ETag"):
                        self._etags[FED_PRESS_MONETARY_RSS_URL] = resp.headers["ETag"]
                    if resp.headers.get("Last-Modified"):
                        self._last_modified[FED_PRESS_MONETARY_RSS_URL] = resp.headers["Last-Modified"]
                xml_txt = resp.text
            else:
                req = urllib.request.Request(FED_PRESS_MONETARY_RSS_URL, headers=hdrs)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    xml_txt = resp.read().decode("utf-8", errors="ignore")
            items = self.parse_fed_rss_xml(xml_txt)
            with self._lock:
                self._recent_releases.extend(items[:5])
            return items
        except Exception as exc:
            logger.debug(f"Fed RSS fetch notice: {exc}")
            return []

    def fetch_sec_submissions_sync(self, cik: str, *, in_window: bool = True, timeout: float = 3.0) -> Optional[Dict[str, Any]]:
        if not in_window:
            return None
        digits = re.sub(r"\D", "", str(cik or ""))
        if not digits:
            return None
        url = SEC_EDGAR_SUBMISSIONS_TMPL.format(cik10=digits.zfill(10))
        try:
            data = _http_get_json_sync(url, timeout=timeout, headers={"User-Agent": self._sec_ua})
            return dict(data) if isinstance(data, Mapping) else None
        except Exception as exc:
            logger.debug(f"SEC EDGAR fetch notice ({cik}): {exc}")
            return None

    def can_query_bls_today(self) -> bool:
        today_s = time.strftime("%Y-%m-%d", time.gmtime())
        with self._lock:
            if self._bls_day_str != today_s:
                self._bls_day_str = today_s
                self._bls_daily_calls = 0
            cap = 450 if self._bls_key else 20
            return self._bls_daily_calls < cap

    def fetch_bls_series_sync(
        self,
        series_ids: Sequence[str],
        *,
        in_window: bool = True,
        timeout: float = 3.5,
    ) -> Optional[Dict[str, Any]]:
        if not in_window or not series_ids or not self.can_query_bls_today():
            return None
        body: Dict[str, Any] = {"seriesid": [str(s) for s in series_ids[:10]]}
        if self._bls_key:
            body["registrationkey"] = self._bls_key
        try:
            with self._lock:
                self._bls_daily_calls += 1
            sess = _get_sync_session()
            if sess is not None:
                resp = sess.post(BLS_PUBLIC_API_V2_URL, json=body, timeout=timeout)
                if resp.status_code != 200:
                    return None
                return _fast_loads(resp.content)
            req = urllib.request.Request(
                BLS_PUBLIC_API_V2_URL,
                data=_fast_dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": self._sec_ua},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return _fast_loads(resp.read())
        except Exception as exc:
            logger.debug(f"BLS v2 fetch notice: {exc}")
            return None


# ---------------------------------------------------------------------------
# 6. Live Intraday CAD/USD Rate Resolver (`$0/mo`, Never Daily BoC Rate)
# ---------------------------------------------------------------------------

def fetch_live_cad_usd_sync(
    *,
    ibkr_quote: Optional[Mapping[str, Any]] = None,
    pyth_stream: Optional[PythHermesStream] = None,
    timeout: float = 2.5,
    session: Any = None,
    fallback_bid: float = 0.7230,
    fallback_ask: float = 0.7250,
) -> Dict[str, Any]:
    """
    Resolves live intraday `CAD -> USD` FX bid/ask for `XV_FX_INVARIANT_CAD_USD_BOX`:
      1. Caller-supplied live IBKR `CAD.USD` quote (`ibkr_quote`)
      2. Live `PythHermesStream` `USDCAD` (or Pyth REST `USDCAD`) inverted cleanly (`1 / USDCAD`)
      3. Coinbase live `USD-CAD` spot inverted cleanly (`1 / amount`)
      4. Conservative stale fallback (`stale=True`) — NEVER silently substitutes a daily-only reference!
    """
    now_f = time.time()
    if isinstance(ibkr_quote, Mapping):
        bid_i = _sf(ibkr_quote.get("bid"), 0.0)
        ask_i = _sf(ibkr_quote.get("ask"), 0.0)
        if 0.50 <= bid_i <= ask_i <= 1.10:
            return {
                "bid": round(bid_i, 6),
                "ask": round(ask_i, 6),
                "mid": round(0.5 * (bid_i + ask_i), 6),
                "ts": _sf(ibkr_quote.get("ts"), now_f),
                "source": "ibkr_idealpro",
                "stale": False,
                "is_daily_ref": False,
            }

    pyth_q = pyth_stream.get_latest("USDCAD", max_age_sec=10.0) if pyth_stream is not None else None
    if pyth_q is None:
        pyth_rest = fetch_pyth_hermes_latest_sync(["USDCAD"], timeout=timeout, session=session)
        pyth_q = pyth_rest.get("USDCAD")
    if isinstance(pyth_q, Mapping):
        usdcad = _sf(pyth_q.get("price"), 0.0)
        conf = max(0.0, _sf(pyth_q.get("conf"), 0.0))
        if 1.0 <= usdcad <= 2.0:
            cad_bid = 1.0 / (usdcad + max(conf, usdcad * 0.0005))
            cad_ask = 1.0 / max(1e-6, usdcad - max(conf, usdcad * 0.0005))
            return {
                "bid": round(cad_bid, 6),
                "ask": round(cad_ask, 6),
                "mid": round(1.0 / usdcad, 6),
                "ts": _sf(pyth_q.get("publish_time"), now_f),
                "source": "pyth_usdcad",
                "stale": False,
                "is_daily_ref": False,
            }

    try:
        cb = _http_get_json_sync(COINBASE_SPOT_USDCAD_URL, timeout=timeout, session=session)
        amt = _sf(((cb or {}).get("data") or {}).get("amount"), 0.0) if isinstance(cb, Mapping) else 0.0
        if 1.0 <= amt <= 2.0:
            mid_c = 1.0 / amt
            return {
                "bid": round(mid_c * 0.9993, 6),
                "ask": round(mid_c * 1.0007, 6),
                "mid": round(mid_c, 6),
                "ts": now_f,
                "source": "coinbase_usdcad_spot",
                "stale": False,
                "is_daily_ref": False,
            }
    except Exception as exc:
        logger.debug(f"Coinbase USD-CAD fallback notice: {exc}")

    return {
        "bid": float(fallback_bid),
        "ask": float(fallback_ask),
        "mid": round(0.5 * (float(fallback_bid) + float(fallback_ask)), 6),
        "ts": now_f,
        "source": "stale_fallback",
        "stale": True,
        "is_daily_ref": False,
    }


__all__ = [
    "FROZEN_KMIA_MARKET_IDS",
    "PythHermesStream",
    "fetch_pyth_hermes_latest_sync",
    "PolygonScopedLogsWs",
    "HyperliquidCoinbaseWs",
    "DeribitPublicWs",
    "MacroEventFeedClient",
    "fetch_live_cad_usd_sync",
    "keccak256_hex",
    "TOPIC_CTF_CONDITION_RESOLUTION",
    "TOPIC_CTF_PAYOUT_REDEMPTION",
    "TOPIC_NEGRISK_PAYOUT_REDEMPTION",
    "TOPIC_OO_PROPOSE_PRICE",
    "TOPIC_OO_DISPUTE_PRICE",
    "TOPIC_OO_SETTLE",
]
