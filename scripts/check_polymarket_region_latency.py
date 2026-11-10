#!/usr/bin/env python3
"""
check_polymarket_region_latency.py
==================================
Polymarket 3-tier jurisdiction classifier, Cloudflare Anycast PoP + Leg-1/Leg-2
TLS 1.3 latency profiler, WebSocket + upstream crypto feed lag probe, and warm
`py_clob_client_v2` (`POLYGON_SIGNATURE_TYPE=3`) `postOnly` canary verifier.

Usage on any candidate cloud VM (e.g. GCP `europe-west4` NL or `europe-north1` FI):
    python3 scripts/check_polymarket_region_latency.py --samples 30 --ws-probe --feed-probe
    venv/bin/python scripts/check_polymarket_region_latency.py --samples 30 --ws-probe --feed-probe --verify-post-only

Key 2026 Polymarket Geoblock Architecture:
  * `GET https://polymarket.com/api/geoblock` reflects consumer **Web UI** (`polymarket.com`)
    restrictions, NOT necessarily `https://clob.polymarket.com` (`POST /order`) API restrictions.
  * Group 1 (Web UI + CLOB API Open): e.g. Finland (`FI`, GCP `europe-north1`), Sweden (`SE`, `europe-north2`).
  * Group 2 (Frontend Close-Only, CLOB API Open): e.g. Netherlands (`NL`, GCP `europe-west4`, ~8ms RTT to London),
    Ireland (`IE`, AWS `eu-west-1`, ~11ms RTT), Japan (`JP`), South Korea (`KR`), Malta (`MT`).
    `/api/geoblock` returns `{"blocked": true}`, while `POST https://clob.polymarket.com/order` returns `200 OK`.
  * Group 3 (CLOB API Blocked / Close-Only unless KYC/KYB whitelisted): e.g. UK (`GB`, `eu-west-2`),
    Germany (`DE`), France (`FR`), US, Canada (`CA`), etc.

Always run `--verify-post-only` directly from the candidate VM IP (never via proxy/VPN) before
cutting over live capital so actual `POST /order` + `DELETE /order` behavior is cryptographically verified.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import http.client
import json
import shutil
import socket
import ssl
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
    if "__file__" in globals() and Path(__file__).exists()
    else Path.cwd().resolve()
)

# Jurisdictions documented as Web-UI close-only (`geoblock.blocked == True`) where
# programmatic CLOB REST (`POST https://clob.polymarket.com/order`) remains open;
# always confirm live on the target host with `--verify-post-only`.
GROUP_2_API_OPEN_COUNTRIES = frozenset({"NL", "IE", "JP", "KR", "MT"})


def summarize_rtt_samples(rtts: List[float]) -> Dict[str, float]:
    """ Backward-compatible summary (`min_ms`, `p50_ms`, `p95_ms`) tested by unit suite. """
    if not rtts:
        return {"min_ms": -1.0, "p50_ms": -1.0, "p95_ms": -1.0}
    s_rtts = sorted(float(x) for x in rtts)
    p95_idx = min(len(s_rtts) - 1, int(round(0.95 * (len(s_rtts) - 1))))
    return {
        "min_ms": round(s_rtts[0], 2),
        "p50_ms": round(statistics.median(s_rtts), 2),
        "p95_ms": round(s_rtts[p95_idx], 2),
    }


def summarize_rtt_extended(rtts: List[float]) -> Dict[str, float]:
    base = summarize_rtt_samples(rtts)
    if not rtts:
        return {**base, "p99_ms": -1.0, "max_ms": -1.0, "jitter_iqr_ms": -1.0}
    s_rtts = sorted(float(x) for x in rtts)
    n = len(s_rtts)
    p99_idx = min(n - 1, int(round(0.99 * (n - 1))))
    p25_idx = min(n - 1, int(round(0.25 * (n - 1))))
    p75_idx = min(n - 1, int(round(0.75 * (n - 1))))
    return {
        **base,
        "p99_ms": round(s_rtts[p99_idx], 2),
        "max_ms": round(s_rtts[-1], 2),
        "jitter_iqr_ms": round(s_rtts[p75_idx] - s_rtts[p25_idx], 2),
    }


def _extract_cf_pop(cf_ray: Optional[str]) -> Optional[str]:
    if not cf_ray or "-" not in cf_ray:
        return None
    pop = cf_ray.rsplit("-", 1)[-1].strip().upper()
    return pop or None


def check_geoblock(timeout: float = 6.0) -> Dict[str, Any]:
    req = urllib.request.Request(
        "https://polymarket.com/api/geoblock",
        headers={"User-Agent": "DominusRegionCheck/2.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        cf_ray = resp.headers.get("cf-ray")
        data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, dict) and cf_ray:
            data.setdefault("web_cf_ray", cf_ray)
            data.setdefault("web_cf_pop", _extract_cf_pop(cf_ray))
        return data


def classify_jurisdiction_tier(geo: Dict[str, Any]) -> Dict[str, Any]:
    blocked = bool(geo.get("blocked", True))
    country = str(geo.get("country") or "").strip().upper()
    region = str(geo.get("region") or "").strip()
    if not blocked:
        return {
            "tier": "GROUP_1_WEB_AND_API_OPEN",
            "country": country,
            "region": region,
            "web_ui_eligible": True,
            "clob_api_candidate": True,
            "note": "Unrestricted for both polymarket.com Web UI and clob.polymarket.com REST/WS.",
        }
    if country in GROUP_2_API_OPEN_COUNTRIES:
        return {
            "tier": "GROUP_2_FRONTEND_CLOSE_ONLY_CLOB_API_OPEN",
            "country": country,
            "region": region,
            "web_ui_eligible": False,
            "clob_api_candidate": True,
            "note": (
                f"{country} is Web-UI close-only (`geoblock.blocked=true`), while programmatic "
                "CLOB REST (`POST /order`) is Group-2 API-open. Run `--verify-post-only` to "
                "cryptographically confirm live order placement on this exact IP/ASN."
            ),
        }
    return {
        "tier": "GROUP_3_RESTRICTED_UNLESS_WHITELISTED",
        "country": country,
        "region": region,
        "web_ui_eligible": False,
        "clob_api_candidate": False,
        "note": (
            f"{country or 'UNKNOWN'} is geoblocked (`geoblock.blocked=true`). Pass `--verify-post-only --force-canary` "
            "only if testing a Polymarket KYC/KYB IP-whitelisted account."
        ),
    }


def measure_clob_http_profile(samples: int = 12, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Profiles DNS -> TCP Leg-1 (`TCP_NODELAY=1`) -> TLS 1.3 handshake -> warm HTTP/1.1
    keep-alive `GET /time` against `clob.polymarket.com`, including Cloudflare edge PoP (`cf-ray`).
    """
    host = "clob.polymarket.com"
    t_dns0 = time.perf_counter()
    infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    dns_ms = round((time.perf_counter() - t_dns0) * 1000.0, 2)
    af, socktype, proto, _, sockaddr = infos[0]
    edge_ip = str(sockaddr[0])

    raw_sock = socket.socket(af, socktype, proto)
    raw_sock.settimeout(timeout)
    try:
        raw_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        raw_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    except OSError:
        pass

    ctx = ssl.create_default_context()
    tls_sock: Optional[ssl.SSLSocket] = None
    conn: Optional[http.client.HTTPSConnection] = None
    rtts: List[float] = []
    cf_ray: Optional[str] = None
    tls_ver: Optional[str] = None
    try:
        t_tcp0 = time.perf_counter()
        raw_sock.connect(sockaddr)
        tcp_connect_ms = round((time.perf_counter() - t_tcp0) * 1000.0, 2)

        t_tls0 = time.perf_counter()
        tls_sock = ctx.wrap_socket(raw_sock, server_hostname=host)
        tls_handshake_ms = round((time.perf_counter() - t_tls0) * 1000.0, 2)
        tls_ver = tls_sock.version()

        conn = http.client.HTTPSConnection(host, 443, timeout=timeout, context=ctx)
        conn.sock = tls_sock

        # Warm-up request (primes Cloudflare worker/origin tunnel; excluded from steady-state samples)
        conn.request(
            "GET",
            "/time",
            headers={"Connection": "keep-alive", "Accept": "application/json", "User-Agent": "DominusRegionCheck/2.0"},
        )
        w_resp = conn.getresponse()
        w_resp.read()
        cf_ray = w_resp.getheader("cf-ray")

        for _ in range(max(3, int(samples))):
            t0 = time.perf_counter()
            conn.request(
                "GET",
                "/time",
                headers={"Connection": "keep-alive", "Accept": "application/json", "User-Agent": "DominusRegionCheck/2.0"},
            )
            resp = conn.getresponse()
            resp.read()
            dt_ms = (time.perf_counter() - t0) * 1000.0
            if not cf_ray:
                cf_ray = resp.getheader("cf-ray")
            if resp.status == 200:
                rtts.append(dt_ms)
            time.sleep(0.03)

        stats_ext = summarize_rtt_extended(rtts)
        est_leg2_origin_ms = (
            round(max(0.0, stats_ext["p50_ms"] - tcp_connect_ms), 2) if stats_ext["p50_ms"] >= 0 else -1.0
        )
        return {
            **stats_ext,
            "samples_ok": len(rtts),
            "edge_ip": edge_ip,
            "cf_ray": cf_ray,
            "cf_pop": _extract_cf_pop(cf_ray),
            "tls_version": tls_ver,
            "dns_ms": dns_ms,
            "leg1_tcp_edge_rtt_ms": tcp_connect_ms,
            "tls_handshake_ms": tls_handshake_ms,
            "est_leg2_edge_to_london_ms": est_leg2_origin_ms,
        }
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        elif tls_sock is not None:
            try:
                tls_sock.close()
            except Exception:
                pass
        else:
            try:
                raw_sock.close()
            except Exception:
                pass


def measure_warm_clob_rtt_ms(samples: int = 12, timeout: float = 5.0) -> Dict[str, float]:
    prof = measure_clob_http_profile(samples=samples, timeout=timeout)
    return {
        "min_ms": prof["min_ms"],
        "p50_ms": prof["p50_ms"],
        "p95_ms": prof["p95_ms"],
    }


async def _measure_ws_ping_rtt_async(
    samples: int = 8, timeout: float = 6.0, token_id: Optional[str] = None
) -> Dict[str, Any]:
    try:
        import websockets
    except ImportError:
        return {"available": False, "reason": "WEBSOCKETS_NOT_INSTALLED"}
    tok_id = str(token_id or "").strip()
    if not tok_id:
        tok_id = str(pick_any_active_ws_token(timeout=timeout) or "").strip()
    if not tok_id:
        cand = pick_liquid_zero_fee_token(timeout=timeout)
        tok_id = str((cand or {}).get("token_id") or "").strip()
    if not tok_id:
        return {"available": False, "reason": "NO_TOKEN_ID_FOR_WS_SUBSCRIPTION"}
    rtts: List[float] = []
    t_conn0 = time.perf_counter()
    polybolt_v2_handshake_ms: Optional[float] = None
    try:
        async with websockets.connect(
            "wss://ws-subscriptions-clob.polymarket.com/ws/market",
            open_timeout=timeout,
            close_timeout=2.0,
            ping_interval=None,
            compression=None,
        ) as ws:
            handshake_ms = round((time.perf_counter() - t_conn0) * 1000.0, 2)
            resp_hdrs = getattr(getattr(ws, "response", None), "headers", None) or getattr(ws, "response_headers", None)
            ws_cf_ray = resp_hdrs.get("cf-ray") if resp_hdrs and hasattr(resp_hdrs, "get") else None
            # Polymarket `/ws/market` requires an initial market subscription frame before `PING`.
            await ws.send(json.dumps({"assets_ids": [tok_id], "type": "market"}))
            await asyncio.wait_for(ws.recv(), timeout=timeout)
            for _ in range(max(2, int(samples))):
                t0 = time.perf_counter()
                await ws.send("PING")
                deadline = t0 + timeout
                while True:
                    rem = max(0.05, deadline - time.perf_counter())
                    msg = await asyncio.wait_for(ws.recv(), timeout=rem)
                    if msg in ("PONG", b"PONG"):
                        rtts.append((time.perf_counter() - t0) * 1000.0)
                        break
                await asyncio.sleep(0.03)
        try:
            t_pb0 = time.perf_counter()
            async with websockets.connect(
                "wss://ws-live-v2.polymarket.com/ws",
                open_timeout=4.0,
                close_timeout=1.5,
                ping_interval=None,
                compression=None,
            ):
                polybolt_v2_handshake_ms = round((time.perf_counter() - t_pb0) * 1000.0, 2)
        except Exception:
            polybolt_v2_handshake_ms = None
        return {
            "available": True,
            "handshake_ms": handshake_ms,
            "ws_cf_pop": _extract_cf_pop(ws_cf_ray),
            "polybolt_v2_handshake_ms": polybolt_v2_handshake_ms,
            **summarize_rtt_extended(rtts),
        }
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


def _read_chrony_clock_sync() -> Dict[str, Any]:
    chronyc = shutil.which("chronyc")
    if not chronyc:
        return {"available": False, "reason": "CHRONYC_NOT_FOUND"}
    try:
        proc = subprocess.run([chronyc, "tracking"], capture_output=True, text=True, timeout=3.0)
        if proc.returncode != 0:
            return {"available": False, "reason": (proc.stderr or proc.stdout).strip()[:160]}
        info: Dict[str, Any] = {"available": True}
        for ln in proc.stdout.splitlines():
            if ":" not in ln:
                continue
            k, v = [p.strip() for p in ln.split(":", 1)]
            kl = k.lower()
            if kl == "system time":
                parts = v.split()
                if parts:
                    val_ms = float(parts[0]) * 1000.0
                    if "slow" in v.lower():
                        val_ms = -val_ms
                    info["system_time_offset_ms"] = round(val_ms, 4)
            elif kl == "rms offset":
                parts = v.split()
                if parts:
                    info["rms_offset_ms"] = round(float(parts[0]) * 1000.0, 4)
            elif kl == "stratum":
                try:
                    info["stratum"] = int(v)
                except ValueError:
                    pass
        return info
    except Exception as exc:
        return {"available": False, "reason": str(exc)}


async def _probe_single_crypto_feed(name: str, url: str, sub_msg: Optional[Dict[str, Any]], duration_sec: float) -> Dict[str, Any]:
    try:
        import websockets
    except ImportError:
        return {"available": False, "reason": "WEBSOCKETS_NOT_INSTALLED"}
    lags_ms: List[float] = []
    t0 = time.perf_counter()
    try:
        async with websockets.connect(url, open_timeout=4.5, close_timeout=1.5, ping_interval=None) as ws:
            hs_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            if sub_msg is not None:
                await ws.send(json.dumps(sub_msg))
            deadline = time.perf_counter() + duration_sec
            while time.perf_counter() < deadline and len(lags_ms) < 40:
                rem = deadline - time.perf_counter()
                if rem <= 0:
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=rem)
                except asyncio.TimeoutError:
                    break
                recv_wall_ms = time.time() * 1000.0
                d = json.loads(raw)
                if not isinstance(d, dict):
                    continue
                if name == "binance_futures_btcusdt":
                    ev_ms = d.get("E") or d.get("T")
                    if ev_ms:
                        lags_ms.append(recv_wall_ms - float(ev_ms))
                elif name == "coinbase_spot_btcusd":
                    ts_iso = d.get("time")
                    if isinstance(ts_iso, str) and d.get("type") == "ticker":
                        dt = _dt.datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
                        lags_ms.append(recv_wall_ms - (dt.timestamp() * 1000.0))
        if not lags_ms:
            return {"available": False, "handshake_ms": hs_ms, "reason": "NO_TIMED_TICKS_WITHIN_WINDOW"}
        return {
            "available": True,
            "handshake_ms": hs_ms,
            "tick_count": len(lags_ms),
            "one_way_lag_ms_note": "wall_recv_ms - exchange_event_ms (verify chrony system_time_offset_ms ~= 0)",
            **summarize_rtt_extended(lags_ms),
        }
    except Exception as exc:
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}".rstrip(": ")[:220]}


async def _measure_upstream_feeds_async(duration_sec: float = 3.5) -> Dict[str, Any]:
    chrony = _read_chrony_clock_sync()
    bin_task = _probe_single_crypto_feed(
        "binance_futures_btcusdt",
        "wss://data-stream.binance.vision/ws/btcusdt@aggTrade",
        None,
        duration_sec,
    )
    cb_task = _probe_single_crypto_feed(
        "coinbase_spot_btcusd",
        "wss://ws-feed.exchange.coinbase.com",
        {"type": "subscribe", "product_ids": ["BTC-USD"], "channels": ["ticker"]},
        duration_sec,
    )
    bin_res, cb_res = await asyncio.gather(bin_task, cb_task)
    return {
        "chrony_clock_sync": chrony,
        "binance_futures_btcusdt": bin_res,
        "coinbase_spot_btcusd": cb_res,
    }


def pick_any_active_ws_token(timeout: float = 6.0) -> Optional[str]:
    req = urllib.request.Request(
        "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=30&order=volume24hr&ascending=false",
        headers={"User-Agent": "DominusRegionCheck/2.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        mkts = json.loads(resp.read().decode("utf-8"))
    for m in mkts or []:
        if not isinstance(m, dict) or bool(m.get("closed")) or not bool(m.get("enableOrderBook", True)):
            continue
        raw_toks = m.get("clobTokenIds")
        toks = json.loads(raw_toks) if isinstance(raw_toks, str) else raw_toks
        if isinstance(toks, list) and toks and str(toks[0]).strip():
            return str(toks[0]).strip()
    return None


def pick_liquid_zero_fee_token(timeout: float = 6.0) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(
        "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=120&order=volume24hr&ascending=false",
        headers={"User-Agent": "DominusRegionCheck/2.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        mkts = json.loads(resp.read().decode("utf-8"))
    for m in mkts or []:
        if not isinstance(m, dict) or bool(m.get("closed")) or not bool(m.get("enableOrderBook", True)):
            continue
        if bool(m.get("feesEnabled")) or bool(m.get("negRisk")):
            continue
        tick_f = float(m.get("orderPriceMinTickSize") or 0.01)
        if tick_f > 0.01:
            continue
        raw_toks = m.get("clobTokenIds")
        toks = json.loads(raw_toks) if isinstance(raw_toks, str) else raw_toks
        if not isinstance(toks, list) or len(toks) != 2:
            continue
        raw_px = m.get("outcomePrices")
        pxs = json.loads(raw_px) if isinstance(raw_px, str) else raw_px
        if isinstance(pxs, list) and len(pxs) == 2:
            try:
                p0 = float(pxs[0])
                p1 = float(pxs[1])
                idx = 0 if 0.25 <= p0 <= 0.92 else (1 if 0.25 <= p1 <= 0.92 else -1)
                if idx >= 0:
                    return {
                        "market_id": str(m.get("id") or ""),
                        "token_id": str(toks[idx]),
                        "mid_hint": p0 if idx == 0 else p1,
                        "tick_size": tick_f,
                    }
            except Exception:
                continue
    return None


def _format_tick_str(tick_f: float) -> str:
    for s in ("0.1", "0.01", "0.001", "0.0001"):
        if abs(float(s) - float(tick_f)) < 1e-7:
            return s
    return "0.01"


def verify_post_only_not_close_only(trials: int = 3) -> Dict[str, Any]:
    """
    Authenticates with `PolymarketLiveExecutor(dry_run=False)` (`py_clob_client_v2`,
    `POLYGON_SIGNATURE_TYPE=3` deposit-wallet funder), pre-warms the pooled TLS 1.3
    socket + tick/neg-risk caches outside the timer, then runs `trials` cycles of
    `$5.00` (`500` shares `@ $0.01`, `postOnly=True`) BUY + immediate `DELETE /order`.

    Proves with `$0.00` fill risk:
      1. Host IP + Cloud ASN are NOT close-only or WAF-blocked on `POST /order`.
      2. True warm `sign_ms`, `post_ms`, and `cancel_ms` (unpolluted by cold TLS or metadata GETs).
    """
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from dotenv import load_dotenv
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    load_dotenv(PROJECT_ROOT / ".env")
    cand = pick_liquid_zero_fee_token()
    if not cand:
        return {"verified": False, "reason": "NO_LIQUID_TEST_MARKET_FOUND"}
    ex = PolymarketLiveExecutor(dry_run=False)
    if getattr(ex, "client", None) is None:
        return {"verified": False, "reason": "CLOB_CLIENT_UNAVAILABLE"}

    tok = str(cand["token_id"])
    tick_str = _format_tick_str(float(cand.get("tick_size") or 0.01))
    px = 0.01
    shares = 500.0  # 500 * $0.01 = $5.00 exact CLOB minimum notional far below >= $0.25 market bid!

    # Pre-seed metadata caches & warm HTTP/1.1 TLS 1.3 pool OUTSIDE timed section
    try:
        if hasattr(ex, "_neg_risk_cache") and isinstance(ex._neg_risk_cache, dict):
            ex._neg_risk_cache[tok] = False
        if hasattr(ex, "_tick_size_cache") and isinstance(ex._tick_size_cache, dict):
            ex._tick_size_cache[tok] = tick_str
        if hasattr(ex, "ping_clob_keepalive"):
            ex.ping_clob_keepalive()
    except Exception:
        pass

    try:
        from py_clob_client_v2.clob_types import OrderArgsV2 as _OrderArgsCls, OrderType, PartialCreateOrderOptions
        from py_clob_client_v2.order_builder.constants import BUY
        import py_clob_client_v2.http_helpers.helpers as _hh_mod
        create_opts = PartialCreateOrderOptions(tick_size=tick_str, neg_risk=False, version=2)
    except ImportError:
        from py_clob_client.clob_types import OrderArgs as _OrderArgsCls, OrderType, PartialCreateOrderOptions  # type: ignore
        from py_clob_client.order_builder.constants import BUY  # type: ignore
        _hh_mod = None  # type: ignore
        create_opts = PartialCreateOrderOptions(tick_size=tick_str, neg_risk=False)  # type: ignore

    sign_rtts: List[float] = []
    post_rtts: List[float] = []
    cancel_rtts: List[float] = []
    last_order_id: Optional[str] = None
    last_cf_ray: Optional[str] = None

    for _ in range(max(1, int(trials))):
        active_order_id: Optional[str] = None
        try:
            t_s0 = time.perf_counter()
            try:
                o_args = _OrderArgsCls(price=px, size=shares, side=BUY, token_id=tok, fee_rate_bps=0)
            except TypeError:
                o_args = _OrderArgsCls(price=px, size=shares, side=BUY, token_id=tok)
            try:
                signed = ex.client.create_order(o_args, create_opts)
            except TypeError:
                signed = ex.client.create_order(o_args)
            sign_ms = (time.perf_counter() - t_s0) * 1000.0

            t_p0 = time.perf_counter()
            try:
                resp = ex.client.post_order(signed, OrderType.GTC, True)
            except TypeError:
                resp = ex.client.post_order(signed, OrderType.GTC)
            post_ms = (time.perf_counter() - t_p0) * 1000.0

            try:
                http_cli = getattr(_hh_mod, "_http_client", None) if _hh_mod is not None else None
                if http_cli is not None and hasattr(http_cli, "get_last_response_meta"):
                    last_cf_ray = (http_cli.get_last_response_meta() or {}).get("cf_ray") or last_cf_ray
            except Exception:
                pass

            active_order_id = str((resp or {}).get("orderID") or (resp or {}).get("id") or "").strip() or None
            err_msg = str((resp or {}).get("errorMsg") or (resp or {}).get("error") or "")
            if not active_order_id:
                return {
                    "verified": False,
                    "post_ms": round(post_ms, 2),
                    "cf_ray": last_cf_ray,
                    "cf_pop": _extract_cf_pop(last_cf_ray),
                    "close_only_suspected": any(
                        w in err_msg.lower() for w in ("close", "geoblock", "region", "restricted", "country")
                    ),
                    "reason": err_msg or "NO_ORDER_ID_RETURNED",
                }

            last_order_id = active_order_id
            t_c0 = time.perf_counter()
            ex.cancel_order(active_order_id, token_id=tok)
            cancel_ms = (time.perf_counter() - t_c0) * 1000.0
            active_order_id = None

            sign_rtts.append(sign_ms)
            post_rtts.append(post_ms)
            cancel_rtts.append(cancel_ms)
            time.sleep(0.08)
        except Exception as exc:
            msg = str(exc)
            if active_order_id:
                try:
                    ex.cancel_order(active_order_id, token_id=tok)
                except Exception:
                    pass
            return {
                "verified": False,
                "cf_ray": last_cf_ray,
                "cf_pop": _extract_cf_pop(last_cf_ray),
                "close_only_suspected": any(
                    w in msg.lower() for w in ("close-only", "close only", "geoblock", "restricted", "403")
                ),
                "reason": msg,
            }

    post_summary = summarize_rtt_samples(post_rtts)
    cancel_summary = summarize_rtt_samples(cancel_rtts)
    sign_summary = summarize_rtt_samples(sign_rtts)
    return {
        "verified": True,
        "close_only": False,
        "trials_completed": len(post_rtts),
        "order_id": last_order_id,
        "cf_ray": last_cf_ray,
        "cf_pop": _extract_cf_pop(last_cf_ray),
        "post_ms": post_summary["p50_ms"],
        "cancel_ms": cancel_summary["p50_ms"],
        "sign_ms_stats": sign_summary,
        "warm_post_ms_stats": post_summary,
        "warm_cancel_ms_stats": cancel_summary,
        "canceled": True,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Polymarket 3-tier geoblock, Cloudflare PoP/TLS RTT, upstream feed lag, and warm v2 postOnly verifier."
    )
    ap.add_argument("--samples", type=int, default=20, help="Keep-alive HTTPS RTT sample count (default: 20)")
    ap.add_argument("--ws-probe", action="store_true", help="Measure CLOB Market WS + PolyBolt v2 WS handshake & PING/PONG RTT")
    ap.add_argument(
        "--feed-probe",
        action="store_true",
        help="Check chrony clock sync and measure Binance Futures + Coinbase Spot BTC WebSocket arrival lag",
    )
    ap.add_argument(
        "--verify-post-only",
        action="store_true",
        help="Post & immediately cancel warm $5.00 @ $0.01 postOnly BUYs (Type-3 v2) to prove host IP is 100%% open",
    )
    ap.add_argument("--canary-trials", type=int, default=3, help="Number of warm post+cancel canary cycles (default: 3)")
    ap.add_argument(
        "--force-canary",
        action="store_true",
        help="Run --verify-post-only even if Group-3 geoblocked (e.g. testing KYC/KYB whitelisted eu-west-2 IP)",
    )
    args = ap.parse_args(argv)

    geo = check_geoblock()
    tier_info = classify_jurisdiction_tier(geo)
    http_prof = measure_clob_http_profile(samples=args.samples)

    report: Dict[str, Any] = {
        "geoblock": geo,
        "jurisdiction_tier": tier_info,
        "web_ui_eligible": tier_info["web_ui_eligible"],
        "eligible_for_live_trading": tier_info["clob_api_candidate"],
        "clob_keepalive_rtt_ms": {
            "min_ms": http_prof["min_ms"],
            "p50_ms": http_prof["p50_ms"],
            "p95_ms": http_prof["p95_ms"],
        },
        "clob_http_profile": http_prof,
    }
    if args.ws_probe:
        report["clob_ws_rtt_ms"] = asyncio.run(_measure_ws_ping_rtt_async())
    if args.feed_probe:
        report["upstream_feed_lag"] = asyncio.run(_measure_upstream_feeds_async())
    if args.verify_post_only:
        if not tier_info["clob_api_candidate"] and not args.force_canary:
            report["post_only_probe"] = {
                "verified": False,
                "reason": (
                    f"SKIPPED_GROUP3_GEOBLOCKED_IP ({tier_info['country']}). "
                    "Pass --force-canary only if testing a whitelisted institutional IP."
                ),
            }
            report["eligible_for_live_trading"] = False
        else:
            report["post_only_probe"] = verify_post_only_not_close_only(trials=args.canary_trials)
            report["eligible_for_live_trading"] = bool(report["post_only_probe"].get("verified"))
    print(json.dumps(report, indent=2))
    return 0 if report["eligible_for_live_trading"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
