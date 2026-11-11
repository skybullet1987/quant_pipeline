#!/usr/bin/env python3
"""
Phase 4 (Requirement R4 & Section 8) — End-to-End 13-Stage Polymarket Latency Benchmark
=======================================================================================
Safe, strictly read-only & non-destructive microbenchmark + historical telemetry analyzer.

Safety Guarantees:
  1. Monkeypatches `dotenv.load_dotenv` to a no-op BEFORE importing any project modules
     so `.env` is NEVER opened or read.
  2. Purges all credential-like environment variables (`PRIVATE`, `SECRET`, `PASSPHRASE`,
     `API_KEY`, `BUILDER`, `MNEMONIC`) in-process at startup.
  3. Uses ONLY ephemeral random keys generated in memory (`secrets.token_hex(32)`) for
     Stage 9 EIP-712 cryptographic signing benchmarks.
  4. Network probes (when not `--skip-network`) execute ONLY unauthenticated read-only
     `GET https://clob.polymarket.com/time`, `/cdn-cgi/trace`, and WebSocket `PING` frames.
     NEVER submits orders or touches live daemons / state files.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import platform
import re
import secrets
import socket
import ssl
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

# 1. HARD CREDENTIAL HYGIENE: Block .env loading and scrub env vars before any project imports.
for _env_k in list(os.environ.keys()):
    if any(
        _tok in _env_k.upper()
        for _tok in ("PRIVATE", "SECRET", "PASSPHRASE", "API_KEY", "BUILDER", "MNEMONIC")
    ):
        os.environ.pop(_env_k, None)

try:
    import dotenv as _dotenv_mod

    _dotenv_mod.load_dotenv = lambda *args, **kwargs: False  # type: ignore[assignment]
except Exception:
    pass

if "__file__" in globals() and "<stdin>" not in str(__file__):
    REPO_ROOT = Path(__file__).resolve().parent.parent
else:
    REPO_ROOT = Path.cwd().resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import orjson
except ImportError:
    orjson = None  # type: ignore[assignment]

try:
    import msgspec
except ImportError:
    msgspec = None  # type: ignore[assignment]


def pcts(vals: List[float], digits: int = 4) -> Dict[str, Any]:
    if not vals:
        return {
            "n": 0,
            "p50": None,
            "p95": None,
            "p99": None,
            "mean": None,
            "min": None,
            "max": None,
        }
    s = sorted(float(x) for x in vals)
    n = len(s)

    def _q(p: float) -> float:
        idx = p * (n - 1)
        lo = int(math.floor(idx))
        hi = min(n - 1, lo + 1)
        w = idx - lo
        return s[lo] * (1.0 - w) + s[hi] * w

    return {
        "n": n,
        "p50": round(_q(0.50), digits),
        "p95": round(_q(0.95), digits),
        "p99": round(_q(0.99), digits),
        "mean": round(sum(s) / n, digits),
        "min": round(s[0], digits),
        "max": round(s[-1], digits),
    }


def bench_us(fn: Callable[[], Any], iters: int = 2000, warmup: int = 100) -> Dict[str, Any]:
    for _ in range(warmup):
        fn()
    samples_us: List[float] = []
    perf_ns = time.perf_counter_ns
    for _ in range(iters):
        t0 = perf_ns()
        fn()
        samples_us.append((perf_ns() - t0) / 1000.0)
    return pcts(samples_us, digits=3)


def _fast_json_loads(raw: bytes | str) -> Any:
    if orjson is not None:
        return orjson.loads(raw)
    return json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))


def _fast_json_dumps_bytes(obj: Any, indent2: bool = False) -> bytes:
    if orjson is not None:
        return orjson.dumps(obj, option=orjson.OPT_INDENT_2 if indent2 else 0)
    if indent2:
        return json.dumps(obj, indent=2).encode("utf-8")
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def collect_host_telemetry() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count_logical": os.cpu_count(),
        "orjson_version": getattr(orjson, "__version__", None),
        "msgspec_version": getattr(msgspec, "__version__", None),
    }
    loadavg_p = Path("/proc/loadavg")
    if loadavg_p.exists():
        try:
            parts = loadavg_p.read_text(encoding="utf-8").split()
            info["linux_loadavg_1_5_15"] = [float(parts[0]), float(parts[1]), float(parts[2])]
        except Exception:
            pass
    meminfo_p = Path("/proc/meminfo")
    if meminfo_p.exists():
        try:
            kv: Dict[str, int] = {}
            for ln in meminfo_p.read_text(encoding="utf-8").splitlines():
                if ":" in ln:
                    k, v = ln.split(":", 1)
                    num = v.strip().split()[0]
                    if num.isdigit():
                        kv[k.strip()] = int(num)
            info["mem_total_mb"] = round(kv.get("MemTotal", 0) / 1024.0, 1)
            info["mem_available_mb"] = round(kv.get("MemAvailable", 0) / 1024.0, 1)
            info["swap_used_mb"] = round(
                (kv.get("SwapTotal", 0) - kv.get("SwapFree", 0)) / 1024.0, 1
            )
        except Exception:
            pass
    return info


def analyze_historical_telemetry(data_dir: Path) -> Dict[str, Any]:
    res: Dict[str, Any] = {}

    # 1. Stage 1 -> 2 from live_shock_triggers.jsonl
    trig_p = data_dir / "live_shock_triggers.jsonl"
    exch_to_rx_ms: List[float] = []
    clob_ws_age_ms: List[float] = []
    if trig_p.exists():
        with open(trig_p, "rb") as f:
            f.seek(0, 2)
            sz = f.tell()
            f.seek(max(0, sz - 6 * 1024 * 1024))
            raw_chunk = f.read()
        lines = raw_chunk.splitlines()
        if sz > 6 * 1024 * 1024 and lines:
            lines = lines[1:]
        for ln in lines[-4000:]:
            try:
                r = _fast_json_loads(ln)
                t0 = float(r.get("t0_unix") or 0.0)
                ets = float(r.get("exchange_event_ts_ms") or 0.0)
                if t0 > 1.7e9 and ets > 1.7e12:
                    lag = t0 * 1000.0 - ets
                    if -50.0 <= lag <= 2000.0:
                        exch_to_rx_ms.append(lag)
                ca = r.get("clob_ws_rx_age_ms")
                if ca is not None and 0.0 <= float(ca) <= 10000.0:
                    clob_ws_age_ms.append(float(ca))
            except Exception:
                pass
    res["stage1_2_triggers"] = {
        "binance_event_to_recorder_rx_ms": pcts(exch_to_rx_ms, 3),
        "clob_ws_rx_age_at_trigger_ms": pcts(clob_ws_age_ms, 3),
    }

    # 2. Stage 11 & thread_hop_ms from latency_trace.jsonl + shock_attempt_forensics.jsonl + live_orders.jsonl
    lt_p = data_dir / "latency_trace.jsonl"
    lt_stages: Dict[str, List[float]] = {
        "trigger_to_consume_wall_ms": [],
        "ws_book_age_ms": [],
        "qualify_ms": [],
        "thread_hop_ms": [],
        "sign_ms": [],
        "clob_http_post_ms": [],
        "total_trigger_to_ack_ms": [],
        "fok_box_ms": [],
        "book_walk_ms": [],
        "ipc_age_ms": [],
    }
    if lt_p.exists():
        for ln in lt_p.read_bytes().splitlines():
            if not ln.strip():
                continue
            try:
                r = _fast_json_loads(ln)
                st = r.get("stages_ms") if isinstance(r.get("stages_ms"), dict) else r
                for k in lt_stages:
                    v = st.get(k)
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v) >= 0.0:
                        lt_stages[k].append(float(v))
            except Exception:
                pass
    res["latency_trace_stages_ms"] = {k: pcts(v, 3) for k, v in lt_stages.items()}

    saf_p = data_dir / "shock_attempt_forensics.jsonl"
    saf_http_ms: List[float] = []
    saf_sign_ms: List[float] = []
    saf_e2e_ms: List[float] = []
    saf_ttl_ms: List[float] = []
    if saf_p.exists():
        for ln in saf_p.read_bytes().splitlines():
            if not ln.strip():
                continue
            try:
                r = _fast_json_loads(ln)
                if isinstance(r.get("http_ms"), (int, float)) and float(r["http_ms"]) > 0:
                    saf_http_ms.append(float(r["http_ms"]))
                if isinstance(r.get("sign_ms"), (int, float)) and float(r["sign_ms"]) >= 0:
                    saf_sign_ms.append(float(r["sign_ms"]))
                if isinstance(r.get("e2e_ms"), (int, float)) and 0 < float(r["e2e_ms"]) < 10000:
                    saf_e2e_ms.append(float(r["e2e_ms"]))
                if isinstance(r.get("ttl_ms"), (int, float)) and float(r["ttl_ms"]) > 0:
                    saf_ttl_ms.append(float(r["ttl_ms"]))
            except Exception:
                pass
    res["shock_attempt_forensics_ms"] = {
        "http_ms": pcts(saf_http_ms, 3),
        "sign_ms": pcts(saf_sign_ms, 3),
        "e2e_ms": pcts(saf_e2e_ms, 3),
        "ttl_ms": pcts(saf_ttl_ms, 3),
    }

    orders_p = data_dir / "live_orders.jsonl"
    maker_lat_ms: List[float] = []
    maker_post_ms: List[float] = []
    maker_sign_ms: List[float] = []
    taker_post_ms: List[float] = []
    taker_e2e_ms: List[float] = []
    taker_sign_ms: List[float] = []
    taker_hop_ms: List[float] = []
    post_ack_fill_confirm_ms: List[float] = []
    fak_killed_lat_ms: List[float] = []
    unwind_lat_ms: List[float] = []
    mode_counts: Dict[str, int] = {}
    if orders_p.exists():
        for ln in orders_p.read_bytes().splitlines():
            if not ln.strip():
                continue
            try:
                r = _fast_json_loads(ln)
                mode = str(r.get("mode") or "UNKNOWN")
                mode_counts[mode] = mode_counts.get(mode, 0) + 1
                lat = float(r.get("latency_ms") or 0.0)
                det = r.get("details") if isinstance(r.get("details"), dict) else {}
                lt_sub = (
                    det.get("latency_telemetry")
                    if isinstance(det.get("latency_telemetry"), dict)
                    else {}
                )
                if mode == "LIVE_MAKER_ENTRY":
                    if lat > 0:
                        maker_lat_ms.append(lat)
                    if isinstance(det.get("post_ms"), (int, float)) and float(det["post_ms"]) > 0:
                        maker_post_ms.append(float(det["post_ms"]))
                    if isinstance(det.get("sign_ms"), (int, float)) and float(det["sign_ms"]) >= 0:
                        maker_sign_ms.append(float(det["sign_ms"]))
                elif mode == "LIVE_CLOB":
                    if lat > 0:
                        taker_e2e_ms.append(lat)
                    p_ms = lt_sub.get("clob_http_post_ms") or det.get("post_ms")
                    s_ms = lt_sub.get("sign_ms") if lt_sub.get("sign_ms") is not None else det.get("sign_ms")
                    h_ms = lt_sub.get("thread_hop_ms")
                    if isinstance(p_ms, (int, float)) and float(p_ms) > 0:
                        taker_post_ms.append(float(p_ms))
                        if lat > float(p_ms):
                            post_ack_fill_confirm_ms.append(
                                lat - float(p_ms) - float(s_ms or 0.0)
                            )
                    if isinstance(s_ms, (int, float)) and float(s_ms) >= 0:
                        taker_sign_ms.append(float(s_ms))
                    if isinstance(h_ms, (int, float)) and float(h_ms) >= 0:
                        taker_hop_ms.append(float(h_ms))
                elif mode in ("FAK_KILLED_NO_MATCH", "LIVE_CLOB_FAK_KILLED_NO_MATCH") and lat > 0:
                    fak_killed_lat_ms.append(lat)
                elif mode == "LIVE_UNWIND" and lat > 0:
                    unwind_lat_ms.append(lat)
            except Exception:
                pass
    res["live_orders_ack_ms"] = {
        "mode_counts": mode_counts,
        "maker_post_only_ack_ms": pcts(maker_lat_ms, 3),
        "maker_detail_post_ms": pcts(maker_post_ms, 3),
        "maker_detail_sign_ms": pcts(maker_sign_ms, 3),
        "taker_clob_http_post_ack_ms": pcts(taker_post_ms, 3),
        "taker_end_to_end_exec_ms": pcts(taker_e2e_ms, 3),
        "taker_post_ack_fill_confirm_ms": pcts(post_ack_fill_confirm_ms, 3),
        "taker_sign_ms": pcts(taker_sign_ms, 3),
        "taker_thread_hop_ms": pcts(taker_hop_ms, 3),
        "taker_fak_killed_no_match_ms": pcts(fak_killed_lat_ms, 3),
        "live_unwind_ack_ms": pcts(unwind_lat_ms, 3),
    }

    # 3. Stage 12 Fill Confirmation & ERC-1155 Settlement visibility from state + harvester logs
    state_p = data_dir / "live_harvester_state.json"
    closed_pos: List[Dict[str, Any]] = []
    sub_to_entry_ms: List[float] = []
    maker_resting_fill_wait_ms: List[float] = []
    if state_p.exists():
        try:
            st_obj = _fast_json_loads(state_p.read_bytes())
            closed_pos = st_obj.get("closed_positions") or []
            for cp in closed_pos:
                if not isinstance(cp, dict):
                    continue
                s_ts = float(cp.get("submitted_at_ts") or 0.0)
                e_ts = float(cp.get("entry_ts") or 0.0)
                if s_ts > 1.7e9 and e_ts >= s_ts:
                    diff_ms = (e_ts - s_ts) * 1000.0
                    if diff_ms <= 5000.0:
                        sub_to_entry_ms.append(diff_ms)
                    elif diff_ms <= 900_000.0:
                        maker_resting_fill_wait_ms.append(diff_ms)
        except Exception:
            pass

    harv_log = data_dir / "live_harvester.log"
    maker_async_post_ms: List[float] = []
    maker_async_sign_ms: List[float] = []
    ws_user_match_to_confirm_ms: List[float] = []
    fast_confirm_tp_ms: List[float] = []
    ts_re = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:[.,](\d+))?(?: UTC)?\]")
    if harv_log.exists():
        with open(harv_log, "rb") as f:
            f.seek(0, 2)
            sz = f.tell()
            f.seek(max(0, sz - 20 * 1024 * 1024))
            log_txt = f.read().decode("utf-8", errors="ignore")
        for m in re.finditer(
            r"\[LIVE MAKER ENTRY ASYNC\].*?post=([0-9.]+)ms sign=([0-9.]+)ms", log_txt
        ):
            maker_async_post_ms.append(float(m.group(1)))
            maker_async_sign_ms.append(float(m.group(2)))

        exec_ts_by_tid: Dict[str, float] = {}
        matched_ts_by_oid: Dict[str, float] = {}
        for ln in log_txt.splitlines():
            m_t = ts_re.match(ln)
            if not m_t:
                continue
            frac_s = float("0." + m_t.group(2)) if m_t.group(2) else 0.0
            dt_u = (
                datetime.strptime(m_t.group(1), "%Y-%m-%d %H:%M:%S")
                .replace(tzinfo=timezone.utc)
                .timestamp()
                + frac_s
            )
            if "[LIVE ORDER EXECUTED]" in ln or "[LIVE ENTRY]" in ln or "SINGLE-LEG LOCK" in ln:
                m_tid = re.search(r"\b((?:LIVE|SLL|DBOX|C1|MKR)_[A-Za-z0-9_]+)\b", ln)
                if m_tid and m_tid.group(1) not in exec_ts_by_tid:
                    exec_ts_by_tid[m_tid.group(1)] = dt_u
            if "[FAST CONFIRM]" in ln:
                m_fc = re.search(r"\[FAST CONFIRM\]\s+([^\s:]+)", ln)
                if m_fc and m_fc.group(1) in exec_ts_by_tid:
                    lag_s = dt_u - exec_ts_by_tid[m_fc.group(1)]
                    if 0.0 <= lag_s <= 60.0:
                        fast_confirm_tp_ms.append(lag_s * 1000.0)
            if "MATCHED" in ln and "0x" in ln:
                m_ox = re.search(r"(0x[a-fA-F0-9]{16,})", ln)
                if m_ox and "CONFIRMED" not in ln and m_ox.group(1) not in matched_ts_by_oid:
                    matched_ts_by_oid[m_ox.group(1)] = dt_u
            if "CONFIRMED" in ln and "0x" in ln:
                m_ox = re.search(r"(0x[a-fA-F0-9]{16,})", ln)
                if m_ox and m_ox.group(1) in matched_ts_by_oid:
                    lag_c = dt_u - matched_ts_by_oid.pop(m_ox.group(1))
                    if 0.0 <= lag_c <= 120.0:
                        ws_user_match_to_confirm_ms.append(lag_c * 1000.0)

    res["stage12_fill_confirmation_ms"] = {
        "closed_positions_sampled": len(closed_pos),
        "immediate_fill_booking_lag_ms": pcts(sub_to_entry_ms, 3),
        "resting_maker_queue_fill_time_ms": pcts(maker_resting_fill_wait_ms, 2),
        "log_maker_async_post_ms": pcts(maker_async_post_ms, 3),
        "log_maker_async_sign_ms": pcts(maker_async_sign_ms, 3),
        "erc1155_fast_confirm_tp_posted_ms": pcts(fast_confirm_tp_ms, 2),
        "ws_user_matched_to_onchain_confirmed_ms": pcts(ws_user_match_to_confirm_ms, 2),
    }
    return res


async def run_network_probes(live_ws_toks: List[str]) -> Dict[str, Any]:
    import aiohttp
    import httpx
    import requests
    import websockets

    cf_trace = ""
    try:
        r_tr = httpx.get("https://clob.polymarket.com/cdn-cgi/trace", timeout=5.0)
        cf_trace = r_tr.text
    except Exception as exc:
        cf_trace = f"ERR:{exc}"

    warm_httpx_ms: List[float] = []
    cf_rays = set()
    with httpx.Client(http2=False, timeout=5.0) as hcli:
        for _ in range(2):
            r0 = hcli.get("https://clob.polymarket.com/time")
            if "cf-ray" in r0.headers:
                cf_rays.add(r0.headers["cf-ray"].split("-")[-1])
        for _ in range(30):
            t0 = time.perf_counter()
            r = hcli.get("https://clob.polymarket.com/time")
            dt = (time.perf_counter() - t0) * 1000.0
            if r.status_code == 200:
                warm_httpx_ms.append(dt)
                if "cf-ray" in r.headers:
                    cf_rays.add(r.headers["cf-ray"].split("-")[-1])

    warm_req_ms: List[float] = []
    with requests.Session() as rses:
        rses.get("https://clob.polymarket.com/time", timeout=5.0)
        for _ in range(25):
            t0 = time.perf_counter()
            r = rses.get("https://clob.polymarket.com/time", timeout=5.0)
            dt = (time.perf_counter() - t0) * 1000.0
            if r.status_code == 200:
                warm_req_ms.append(dt)

    cold_tls_ms: List[float] = []
    for _ in range(10):
        t0 = time.perf_counter()
        with httpx.Client(http2=False, timeout=5.0) as ccli:
            r = ccli.get("https://clob.polymarket.com/time")
        dt = (time.perf_counter() - t0) * 1000.0
        if r.status_code == 200:
            cold_tls_ms.append(dt)

    tcp_connect_ms: List[float] = []
    tls_hs_ms: List[float] = []
    resolved_ips = sorted(
        {
            ai[4][0]
            for ai in socket.getaddrinfo(
                "clob.polymarket.com", 443, socket.AF_INET, socket.SOCK_STREAM
            )
        }
    )
    ctx = ssl.create_default_context()
    for _ in range(10):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5.0)
        t0 = time.perf_counter()
        s.connect((resolved_ips[0], 443))
        t1 = time.perf_counter()
        ss = ctx.wrap_socket(s, server_hostname="clob.polymarket.com")
        t2 = time.perf_counter()
        tcp_connect_ms.append((t1 - t0) * 1000.0)
        tls_hs_ms.append((t2 - t1) * 1000.0)
        ss.close()

    aio_ms: List[float] = []
    async with aiohttp.ClientSession() as ases:
        async with ases.get("https://clob.polymarket.com/time") as _:
            pass
        for _ in range(25):
            t0 = time.perf_counter()
            async with ases.get("https://clob.polymarket.com/time") as r:
                await r.read()
            aio_ms.append((time.perf_counter() - t0) * 1000.0)

    ws_ping_ms: List[float] = []
    clob_ws_event_lag_ms: List[float] = []
    ws_conn_ms: Any = None
    try:
        t_c0 = time.perf_counter()
        async with websockets.connect(
            "wss://ws-subscriptions-clob.polymarket.com/ws/market",
            open_timeout=5.0,
            compression=None,
        ) as ws:
            ws_conn_ms = round((time.perf_counter() - t_c0) * 1000.0, 3)
            for _ in range(15):
                t_p0 = time.perf_counter()
                pong_waiter = await ws.ping()
                await pong_waiter
                ws_ping_ms.append((time.perf_counter() - t_p0) * 1000.0)
            if live_ws_toks:
                await ws.send(json.dumps({"assets_ids": live_ws_toks, "type": "market"}))
                t_end_w = time.monotonic() + 3.0
                while time.monotonic() < t_end_w and len(clob_ws_event_lag_ms) < 25:
                    try:
                        raw_m = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        rx_ms = time.time() * 1000.0
                        parsed_m = _fast_json_loads(raw_m)
                        items_m = parsed_m if isinstance(parsed_m, list) else [parsed_m]
                        for it_m in items_m:
                            if isinstance(it_m, dict) and it_m.get("timestamp"):
                                ts_m = float(it_m["timestamp"])
                                if ts_m > 1.7e12:
                                    clob_ws_event_lag_ms.append(rx_ms - ts_m)
                    except Exception:
                        break
    except Exception as exc:
        ws_conn_ms = f"ERR:{exc}"

    bn_ping_ms: List[float] = []
    try:
        async with websockets.connect(
            "wss://fstream.binance.com:443/ws/btcusdt@aggTrade", open_timeout=5.0
        ) as bws:
            for _ in range(10):
                t_p0 = time.perf_counter()
                pw = await bws.ping()
                await pw
                bn_ping_ms.append((time.perf_counter() - t_p0) * 1000.0)
    except Exception:
        pass

    return {
        "cf_trace": {
            ln.split("=", 1)[0]: ln.split("=", 1)[1]
            for ln in cf_trace.splitlines()
            if "=" in ln
        },
        "cf_ray_colos": sorted(cf_rays),
        "clob_resolved_ips": resolved_ips,
        "tcp_connect_clob_ms": pcts(tcp_connect_ms, 3),
        "tls13_handshake_clob_ms": pcts(tls_hs_ms, 3),
        "warm_httpx_keepalive_get_time_ms": pcts(warm_httpx_ms, 3),
        "warm_requests_session_get_time_ms": pcts(warm_req_ms, 3),
        "warm_aiohttp_keepalive_get_time_ms": pcts(aio_ms, 3),
        "cold_fresh_tls_httpx_get_time_ms": pcts(cold_tls_ms, 3),
        "clob_ws_connect_ms": ws_conn_ms,
        "clob_ws_ping_rtt_ms": pcts(ws_ping_ms, 3),
        "clob_ws_event_to_rx_ms": pcts(clob_ws_event_lag_ms, 3),
        "binance_futures_ws_ping_rtt_ms": pcts(bn_ping_ms, 3),
    }


def _install_minimal_offline_stubs_if_needed() -> None:
    """Allows `--skip-network` execution on stdlib-only Python (e.g., LibreOffice Python on Windows)."""
    import importlib.util
    import types

    def _missing(mod_name: str) -> bool:
        return mod_name not in sys.modules and importlib.util.find_spec(mod_name) is None

    class _StubAny:
        def __init__(self, *a: Any, **kw: Any) -> None:
            self.is_closed = False

        def close(self) -> None:
            self.is_closed = True

    class _AttrStubModule(types.ModuleType):
        def __getattr__(self, name: str) -> Any:
            return _StubAny

    if _missing("dotenv"):
        m = types.ModuleType("dotenv")
        m.load_dotenv = lambda *a, **kw: False  # type: ignore[attr-defined]
        sys.modules["dotenv"] = m
    if _missing("aiohttp"):
        sys.modules["aiohttp"] = _AttrStubModule("aiohttp")
    if _missing("websockets"):
        sys.modules["websockets"] = _AttrStubModule("websockets")
    if _missing("numpy"):
        np_stub = _AttrStubModule("numpy")
        np_stub.ndarray = list  # type: ignore[attr-defined]
        np_stub.float64 = float  # type: ignore[attr-defined]
        sys.modules["numpy"] = np_stub
    if _missing("urllib3"):
        u3 = _AttrStubModule("urllib3")
        u3_conn = _AttrStubModule("urllib3.connection")

        class _StubHTTPConnection:
            default_socket_options: list = []

        u3_conn.HTTPConnection = _StubHTTPConnection  # type: ignore[attr-defined]
        u3.connection = u3_conn  # type: ignore[attr-defined]
        sys.modules["urllib3"] = u3
        sys.modules["urllib3.connection"] = u3_conn
    if _missing("requests"):
        sys.modules["requests"] = _AttrStubModule("requests")
    if _missing("httpx"):
        hx = _AttrStubModule("httpx")
        for _err_n in ("HTTPError", "RequestError", "ConnectError", "ConnectTimeout", "PoolTimeout"):
            setattr(hx, _err_n, Exception)
        sys.modules["httpx"] = hx


def run_benchmark(
    iters: int = 1500,
    skip_network: bool = False,
    data_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    if skip_network:
        _install_minimal_offline_stubs_if_needed()
    resolved_data_dir = data_dir or (REPO_ROOT / "data" / "polymarket")
    warmup = max(10, min(100, iters // 10))
    out: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": collect_host_telemetry(),
        "historical": analyze_historical_telemetry(resolved_data_dir),
    }

    # --- Synthetic / Representative Payloads ---
    tok_id = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
    book_snap_obj = {
        "market": "0x" + "ab" * 32,
        "asset_id": tok_id,
        "timestamp": "1762819200123",
        "hash": "0x" + "cd" * 20,
        "bids": [
            {"price": f"{0.65 - i * 0.01:.2f}", "size": f"{120.5 + i * 15.2:.2f}"}
            for i in range(30)
        ],
        "asks": [
            {"price": f"{0.66 + i * 0.01:.2f}", "size": f"{110.0 + i * 12.8:.2f}"}
            for i in range(30)
        ],
    }
    book_snap_bytes = _fast_json_dumps_bytes(book_snap_obj)
    book_snap_str = book_snap_bytes.decode("utf-8")

    delta_obj = {
        "event_type": "price_change",
        "market": "0x" + "ab" * 32,
        "timestamp": "1762819200456",
        "price_changes": [
            {
                "asset_id": tok_id,
                "price": "0.66",
                "size": "185.0",
                "side": "SELL",
                "best_bid": "0.65",
                "best_ask": "0.66",
            },
            {
                "asset_id": tok_id,
                "price": "0.65",
                "size": "210.0",
                "side": "BUY",
                "best_bid": "0.65",
                "best_ask": "0.66",
            },
        ],
    }
    delta_bytes = _fast_json_dumps_bytes(delta_obj)
    delta_str = delta_bytes.decode("utf-8")

    shm_btc_path = Path("/dev/shm/pm_fast_tick_BTC.json")
    has_real_shm = shm_btc_path.exists()
    real_shm_bytes = (
        shm_btc_path.read_bytes()
        if has_real_shm
        else _fast_json_dumps_bytes({"asset": "BTC", "spot": 95000.0, "markets": {}})
    )

    # --- Stage 3: Market-Data JSON Parsing ---
    s3: Dict[str, Any] = {
        "book_snap_size_bytes": len(book_snap_bytes),
        "delta_size_bytes": len(delta_bytes),
        "shm_tick_size_bytes": len(real_shm_bytes),
        "book_json_loads": bench_us(lambda: json.loads(book_snap_str), iters=iters, warmup=warmup),
        "delta_json_loads": bench_us(lambda: json.loads(delta_str), iters=iters, warmup=warmup),
    }
    if orjson is not None:
        s3["book_orjson_loads"] = bench_us(
            lambda: orjson.loads(book_snap_bytes), iters=iters, warmup=warmup
        )
        s3["delta_orjson_loads"] = bench_us(
            lambda: orjson.loads(delta_bytes), iters=iters, warmup=warmup
        )
    if msgspec is not None:
        msg_dec = msgspec.json.Decoder()
        s3["book_msgspec_decode"] = bench_us(
            lambda: msg_dec.decode(book_snap_bytes), iters=iters, warmup=warmup
        )
        s3["delta_msgspec_decode"] = bench_us(
            lambda: msg_dec.decode(delta_bytes), iters=iters, warmup=warmup
        )
    if has_real_shm:
        shm_iters = max(50, min(1000, iters))
        s3["shm_json_loads_read_text"] = bench_us(
            lambda: json.loads(shm_btc_path.read_text(encoding="utf-8")),
            iters=shm_iters,
            warmup=warmup,
        )
        if orjson is not None:
            s3["shm_orjson_loads_read_bytes"] = bench_us(
                lambda: orjson.loads(shm_btc_path.read_bytes()),
                iters=shm_iters,
                warmup=warmup,
            )
    out["stage3_json_us"] = s3

    # --- Stage 4: L2 Orderbook Reconstruction ---
    from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook
    from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker

    l2b = L2OrderBook(tok_id)
    l2b.apply_snapshot(book_snap_obj["bids"], book_snap_obj["asks"])
    ws_tr = PolymarketClobMarketWsTracker()
    ws_tr.set_desired_tokens([tok_id])
    ws_tr.process_ws_payload(book_snap_obj)

    out["stage4_book_us"] = {
        "l2_apply_snapshot_30lvl": bench_us(
            lambda: l2b.apply_snapshot(book_snap_obj["bids"], book_snap_obj["asks"]),
            iters=iters,
            warmup=warmup,
        ),
        "l2_apply_price_changes_2lvl": bench_us(
            lambda: l2b.apply_price_changes(
                [
                    {"price": "0.66", "size": "190.0", "side": "SELL"},
                    {"price": "0.65", "size": "215.0", "side": "BUY"},
                ]
            ),
            iters=iters,
            warmup=warmup,
        ),
        "l2_top_of_book": bench_us(
            lambda: (setattr(l2b, "_dirty", True), l2b.top_of_book()),
            iters=iters,
            warmup=warmup,
        ),
        "l2_get_metrics_full": bench_us(
            lambda: (setattr(l2b, "_dirty", True), l2b.get_metrics()),
            iters=iters,
            warmup=warmup,
        ),
        "l2_get_metrics_compact": bench_us(
            lambda: (setattr(l2b, "_dirty", True), l2b.get_metrics(compact=True)),
            iters=iters,
            warmup=warmup,
        ),
        "ws_tracker_delta_raw_bytes": bench_us(
            lambda: ws_tr.process_ws_payload(delta_bytes),
            iters=iters,
            warmup=warmup,
        ),
    }

    # --- Stage 5, 6, 7, 8, 9 ---
    try:
        from eth_account import Account as _EthAccount
    except ImportError:
        _EthAccount = None  # type: ignore[assignment]
    from src.polymarket_research.net_alpha_opportunity_engine import (
        compute_smart_maker_bid,
        estimate_quote_survival_and_net_alpha,
        inspect_microstructure_feature_completeness,
        publish_global_positions_shm,
        rank_microbatch_shock_tournament,
        rank_opportunities_capital_auction,
        read_global_positions_shm,
    )
    from src.polymarket_research.polymarket_live_executor import (
        FastV2OrderSigner,
        OrderArgsV2,
        OrderType,
        PartialCreateOrderOptions,
        PolymarketLiveExecutor,
        PreSignedOrderLadderCache,
        quantize_fok_buy_leg_size,
    )
    from src.polymarket_research.polymarket_live_harvester import (
        EmergencyRiskController,
        compute_composite_edge_score,
        compute_max_acceptable_ask,
        evaluate_coinbase_venue_veto,
        read_fast_tick,
    )
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        check_per_event_concentration_cap,
    )

    sample_shock: Dict[str, Any] = {
        "shock_id": "BENCH_SHK_1",
        "event_id": "BENCH_SHK_1",
        "t0_unix": time.time(),
        "asset": "BTC",
        "horizon": "15m",
        "candle_interval": "15m",
        "market_id": "6280100",
        "condition_id": "0x" + "11" * 32,
        "title": "Bitcoin Up or Down - 15m",
        "seconds_to_expiry": 320.0,
        "shock_direction": "BUY",
        "shock_ofi": 0.88,
        "shock_volume_100ms": 1_850_000.0,
        "delta_basis_100ms": 2.1,
        "candle_distance_pct": 0.14,
        "candle_sigma": 0.0025,
        "authoritative_chainlink_open": 95000.0,
        "chainlink_proxy_spot": 95133.0,
        "coinbase_spot": 95132.5,
        "venue_divergence_centered_bps": 1.2,
        "coinbase_move_bps_2s": 4.5,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": tok_id,
                "age_ask_ms": 420.0,
                "obi_l1": 0.22,
                "obi_depth": 0.18,
                "spread": 0.01,
                "best_ask": 0.66,
                "best_bid": 0.65,
                "ask_size_l1": 120.0,
                "bid_size_l1": 150.0,
                "vwap_$25": 0.66,
                "effective_price_$25": 0.675,
                "raw_top_asks": [[0.66 + i * 0.01, 110.0] for i in range(10)],
                "raw_top_bids": [[0.65 - i * 0.01, 120.0] for i in range(10)],
            }
        },
    }

    def stage5_eval() -> None:
        inspect_microstructure_feature_completeness(sample_shock, "UP", tok_id)
        evaluate_coinbase_venue_veto(sample_shock, "UP")
        compute_composite_edge_score(sample_shock)
        compute_max_acceptable_ask(
            0.14,
            320.0,
            asset="BTC",
            shock_ofi=0.88,
            shock_vol_usd=1_850_000.0,
            delta_basis_bps=2.1,
            age_ask_ms=420.0,
            is_subhourly_15m=True,
            candle_sigma=0.0025,
        )
        estimate_quote_survival_and_net_alpha(
            0.84, 0.66, 0.68, 0.72, clob_rtt_ms=260.0, age_ask_ms=420.0
        )

    shocks_4 = [
        dict(sample_shock, asset=a, shock_id=f"S_{i}")
        for i, a in enumerate(["BTC", "ETH", "SOL", "XRP"])
    ]
    opps_4 = [
        {
            "asset": "BTC",
            "side": "UP",
            "expiry_ts": time.time() + 300,
            "strike": 95000.0,
            "net_edge": 0.035,
            "ask_vwap": 0.66,
            "p_model": 0.78,
            "tte_sec": 300.0,
        },
        {
            "asset": "ETH",
            "side": "UP",
            "expiry_ts": time.time() + 300,
            "strike": 2500.0,
            "net_edge": 0.028,
            "ask_vwap": 0.64,
            "p_model": 0.74,
            "tte_sec": 300.0,
        },
    ]
    active_pos_sim = [
        {
            "asset": "BTC",
            "side": "DOWN",
            "expiry_ts": time.time() + 300,
            "strike": 95150.0,
            "notional_usd": 12.0,
        }
    ]

    def stage6_select() -> None:
        rank_microbatch_shock_tournament(shocks_4, active_positions=active_pos_sim)
        rank_opportunities_capital_auction(opps_4, active_global_positions=active_pos_sim)
        compute_smart_maker_bid(0.65, 0.67, max_cap_px=0.68, obi_l1=0.15, tick_size=0.01)

    # Strictly ephemeral random test key in memory (NEVER touches .env)
    ephem_pk = "0x" + secrets.token_hex(32)
    ephem_addr = (
        _EthAccount.from_key(ephem_pk).address
        if _EthAccount is not None
        else ("0x" + secrets.token_hex(20))
    )
    mock_harv_conc = SimpleNamespace(
        active_positions={
            "p1": {
                "trade_id": "p1",
                "event_id": "999",
                "market_id": "999",
                "notional_usd": 12.0,
                "question": "BTC 1h",
            }
        },
        pending_entry_intents={},
        _last_known_collateral=47.38,
        enforce_event_concentration_cap=True,
        dry_run=False,
    )
    conc_cand = {
        "box_type": "SINGLE_LEG_LOCK",
        "event_id": "6280100",
        "leg_a_market_id": "6280100",
        "question": "Bitcoin Up or Down - 15m",
    }

    with tempfile.TemporaryDirectory(prefix="pm_lat_exec_") as exec_tmp:
        exec_tmp_p = Path(exec_tmp)
        exec_dry = PolymarketLiveExecutor(
            private_key=ephem_pk,
            funder_address=ephem_addr,
            signature_type=0,
            dry_run=True,
            ledger_path=str(exec_tmp_p / "noop_ledger.jsonl"),
        )
        rc = EmergencyRiskController()
        rc.kill_file = exec_tmp_p / "nonexistent_kill_switch"
        exp_chk = time.time() + 300.0
        act_pos_list = [{"asset": "BTC", "target_token": "UP", "candle_expiry_ts": exp_chk}]

        def stage7_risk() -> None:
            rc.is_halted()
            rc.check_equity_drawdown(97.89)
            exec_dry.verify_pre_trade_depth(
                book_snap_obj,
                15.0,
                side="BUY",
                depth_hurdle_ratio=1.2,
                max_price_ceiling=0.75,
                min_price_floor=0.52,
                return_adjusted=True,
            )
            exec_dry.simulate_fok_sweep(
                book_snap_obj,
                15.0,
                side="BUY",
                max_acceptable_price=0.75,
                min_acceptable_price=0.52,
            )
            check_per_event_concentration_cap(mock_harv_conc, cand=conc_cand)
            exec_dry.validate_cross_asset_directional_conflict(
                "ETH",
                "UP",
                exp_chk,
                active_positions=act_pos_list,
                candidate_duration_s=900.0,
            )

        out["stage5_signal_us"] = bench_us(stage5_eval, iters=iters, warmup=warmup)
        out["stage6_strategy_us"] = bench_us(stage6_select, iters=iters, warmup=warmup)
        out["stage7_risk_cpu_us"] = bench_us(stage7_risk, iters=iters, warmup=warmup)
        out["stage7_read_fast_tick_us"] = (
            bench_us(
                lambda: read_fast_tick("BTC", max_age_sec=5.0),
                iters=max(50, min(1000, iters)),
                warmup=warmup,
            )
            if has_real_shm
            else None
        )

        # Benchmark SHM Global Position Bus in isolated temp dir
        prev_shm_env = os.environ.get("PM_FAST_TICK_DIR")
        os.environ["PM_FAST_TICK_DIR"] = str(exec_tmp_p)
        try:
            publish_global_positions_shm("bench_daemon", active_pos_sim)
            out["shm_global_positions_bus_us"] = {
                "publish_us": bench_us(
                    lambda: publish_global_positions_shm("bench_daemon", active_pos_sim),
                    iters=max(50, min(500, iters)),
                    warmup=10,
                ),
                "read_us": bench_us(
                    lambda: read_global_positions_shm(max_age_sec=120.0),
                    iters=max(50, min(500, iters)),
                    warmup=10,
                ),
            }
        finally:
            if prev_shm_env is None:
                os.environ.pop("PM_FAST_TICK_DIR", None)
            else:
                os.environ["PM_FAST_TICK_DIR"] = prev_shm_env

        # Stage 8 & 9: Payload Construction + Ephemeral EIP-712 Signing
        exec_dry._fast_l2_secret_bytes = os.urandom(32)
        exec_dry._fast_l2_signer_addr = ephem_addr
        exec_dry._fast_l2_api_key = "00000000-0000-0000-0000-000000000000"
        exec_dry._fast_l2_passphrase = "bench_dummy_passphrase"

        try:
            from py_clob_client_v2.client import ClobClient

            clob_eoa = ClobClient(
                "https://clob.polymarket.com",
                chain_id=137,
                key=ephem_pk,
                signature_type=0,
                funder=ephem_addr,
            )
            fast_signer_eoa = FastV2OrderSigner(clob_eoa)
            dummy_safe = "0x" + "22" * 20
            clob_safe = ClobClient(
                "https://clob.polymarket.com",
                chain_id=137,
                key=ephem_pk,
                signature_type=3,
                funder=dummy_safe,
            )
            fast_signer_safe = FastV2OrderSigner(clob_safe)

            for _cli in (clob_eoa, clob_safe):
                getattr(_cli, "_ClobClient__tick_sizes", {})[tok_id] = "0.01"
                getattr(_cli, "_ClobClient__neg_risk", {})[tok_id] = False
                getattr(_cli, "_ClobClient__fee_rates", {})[tok_id] = 0
                setattr(_cli, "_ClobClient__order_version", 2)

            o_args = OrderArgsV2(price=0.66, size=22.0, side="BUY", token_id=tok_id)
            c_opts = PartialCreateOrderOptions(tick_size="0.01", neg_risk=False, version=2)
            sample_signed = fast_signer_safe.create_order(o_args, c_opts)
            has_clob_sdk = True
        except ImportError:
            has_clob_sdk = False
            sample_signed = {"mock_signed_order": True, "tokenId": tok_id}

        ladder = PreSignedOrderLadderCache(ttl_seconds=1800.0)
        for _li in range(iters + warmup + 8):
            ladder.store_presigned_order(
                f"{tok_id}_{_li}",
                0.66,
                22.0,
                sample_signed,
                tick_size="0.01",
                neg_risk=False,
            )
        _ladder_idx = [0]

        def _pop_ladder_hit() -> Any:
            i_cur = _ladder_idx[0]
            _ladder_idx[0] = i_cur + 1
            return ladder.get_presigned_order(
                f"{tok_id}_{i_cur}", 0.66, 22.0, tick_size="0.01", neg_risk=False
            )

        if has_clob_sdk:
            def stage8_payload() -> None:
                quantize_fok_buy_leg_size(22.0, 0.66)
                p_dict = exec_dry._serialize_signed_order_payload(
                    sample_signed, OrderType.FAK, post_only=False, defer_exec=True
                )
                exec_dry._encode_fast_l2_request("/order", p_dict)

            out["stage8_payload_us"] = bench_us(stage8_payload, iters=iters, warmup=warmup)
            sdk_iters = max(40, min(400, iters // 3))
            out["stage9_signing_us"] = {
                "sdk_order_builder_v2_eoa": bench_us(
                    lambda: clob_eoa.create_order(o_args, c_opts),
                    iters=sdk_iters,
                    warmup=min(20, warmup),
                ),
                "sdk_order_builder_v2_poly1271_safe": bench_us(
                    lambda: clob_safe.create_order(o_args, c_opts),
                    iters=sdk_iters,
                    warmup=min(20, warmup),
                ),
                "fast_v2_coincurve_eoa": bench_us(
                    lambda: fast_signer_eoa.create_order(o_args, c_opts),
                    iters=iters,
                    warmup=warmup,
                ),
                "fast_v2_coincurve_poly1271_safe": bench_us(
                    lambda: fast_signer_safe.create_order(o_args, c_opts),
                    iters=iters,
                    warmup=warmup,
                ),
                "presigned_ladder_cache_hit": bench_us(
                    _pop_ladder_hit,
                    iters=iters,
                    warmup=warmup,
                ),
            }
        else:
            def stage8_offline_payload() -> None:
                quantize_fok_buy_leg_size(22.0, 0.66)
                exec_dry._encode_fast_l2_request("/order", sample_signed)

            out["stage8_payload_us"] = bench_us(stage8_offline_payload, iters=iters, warmup=warmup)
            out["stage9_signing_us"] = {
                "sdk_unavailable_in_stdlib_only_env": True,
                "presigned_ladder_cache_hit": bench_us(
                    _pop_ladder_hit,
                    iters=iters,
                    warmup=warmup,
                ),
            }

    # --- Stage 2 Local Abstract AF_UNIX IPC Datagram Loopback (Linux) ---
    if hasattr(socket, "AF_UNIX") and sys.platform.startswith("linux"):
        s_rx = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        bench_ipc_addr = b"\x00pm_lat_bench_" + secrets.token_hex(6).encode()
        s_rx.bind(bench_ipc_addr)
        s_tx = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        ipc_payload = _fast_json_dumps_bytes(sample_shock) + b"\n"

        def bench_ipc_once() -> None:
            s_tx.sendto(ipc_payload, bench_ipc_addr)
            s_rx.recv(65536)

        out["stage2_af_unix_ipc_us"] = bench_us(
            bench_ipc_once, iters=min(1000, iters), warmup=min(50, warmup)
        )
        s_rx.close()
        s_tx.close()
    else:
        out["stage2_af_unix_ipc_us"] = None

    # --- Stage 10: Read-Only Network / Keep-Alive / TLS / WS RTT ---
    if skip_network:
        out["stage10_network_ms"] = {"skipped": True}
    else:
        live_ws_toks: List[str] = []
        if has_real_shm:
            try:
                d_btc = _fast_json_loads(real_shm_bytes)
                for side_k in ("UP", "DOWN"):
                    tid_x = (d_btc.get(side_k) or {}).get("token_id")
                    if tid_x:
                        live_ws_toks.append(str(tid_x))
            except Exception:
                pass
        out["stage10_network_ms"] = asyncio.run(run_network_probes(live_ws_toks))

    # --- Stage 13: save_state() Serialization & Atomic fsync Scaling ---
    live_state_p = resolved_data_dir / "live_harvester_state.json"
    if live_state_p.exists():
        base_state = _fast_json_loads(live_state_p.read_bytes())
    else:
        base_state = {
            "state_version": "2.0.0",
            "live_bankroll": 47.38,
            "total_account_equity": 97.89,
            "active_positions": {},
            "seen_shock_ids": [f"SHK_{i}" for i in range(1000)],
            "closed_positions": [],
        }
    existing_closed = base_state.get("closed_positions") or []
    sample_closed_item = (
        dict(existing_closed[-1])
        if existing_closed and isinstance(existing_closed[-1], dict)
        else {
            "trade_id": "T_SAMPLE",
            "asset": "BTC",
            "market_id": "6280100",
            "token_id": tok_id,
            "entry_price": 0.65,
            "exit_price": 0.75,
            "shares": 20.0,
            "notional_usd": 13.0,
            "realized_pnl": 2.0,
            "submitted_at_ts": 1762819200.123,
            "entry_ts": 1762819200.195,
            "exit_ts": 1762819320.450,
            "exit_reason": "MAKER_SCALP_TP",
        }
    )

    disk_parent = "/var/tmp" if Path("/var/tmp").exists() and os.name != "nt" else None
    tmpfs_parent = "/tmp" if Path("/tmp").exists() and os.name != "nt" else None
    io_iters = max(10, min(25, iters // 50))
    cpu_iters = max(15, min(40, iters // 30))

    stage13_res: Dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="pm_lat_disk_", dir=disk_parent) as d_dir:
        d_path = Path(d_dir)
        t_ctx = (
            tempfile.TemporaryDirectory(prefix="pm_lat_tmpfs_", dir=tmpfs_parent)
            if tmpfs_parent
            else tempfile.TemporaryDirectory(prefix="pm_lat_tmp2_")
        )
        with t_ctx as t_dir:
            t_path = Path(t_dir)
            for n_closed in (50, 136, 500):
                st_obj = dict(base_state)
                st_obj["closed_positions"] = [
                    dict(sample_closed_item, trade_id=f"T_{i}") for i in range(n_closed)
                ]
                st_obj["closed_positions_count"] = n_closed
                raw_j_indent = json.dumps(st_obj, indent=2).encode("utf-8")
                raw_oj_indent = _fast_json_dumps_bytes(st_obj, indent2=True)
                raw_oj_compact = _fast_json_dumps_bytes(st_obj, indent2=False)

                c_j: List[float] = []
                c_oi: List[float] = []
                c_oc: List[float] = []
                for _ in range(cpu_iters):
                    t0 = time.perf_counter()
                    _ = json.dumps(st_obj, indent=2)
                    c_j.append((time.perf_counter() - t0) * 1000.0)
                    if orjson is not None:
                        t0 = time.perf_counter()
                        _ = orjson.dumps(st_obj, option=orjson.OPT_INDENT_2)
                        c_oi.append((time.perf_counter() - t0) * 1000.0)
                        t0 = time.perf_counter()
                        _ = orjson.dumps(st_obj)
                        c_oc.append((time.perf_counter() - t0) * 1000.0)

                io_disk_j: List[float] = []
                io_disk_oi: List[float] = []
                io_tmpfs_oi: List[float] = []
                target_disk = d_path / f"state_{n_closed}.json"
                target_tmpfs = t_path / f"state_{n_closed}.json"
                for i in range(io_iters):
                    tmp_e = d_path / f"state_{n_closed}.tmp.{i}"
                    t0 = time.perf_counter()
                    with open(tmp_e, "w", encoding="utf-8") as f:
                        json.dump(st_obj, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp_e, target_disk)
                    if os.name != "nt":
                        dfd = os.open(str(d_path), os.O_RDONLY)
                        try:
                            os.fsync(dfd)
                        finally:
                            os.close(dfd)
                    io_disk_j.append((time.perf_counter() - t0) * 1000.0)

                    if orjson is not None:
                        t0 = time.perf_counter()
                        payload_b = orjson.dumps(st_obj, option=orjson.OPT_INDENT_2)
                        fd = os.open(str(tmp_e), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                        try:
                            os.write(fd, payload_b)
                            os.fsync(fd)
                        finally:
                            os.close(fd)
                        os.replace(tmp_e, target_disk)
                        if os.name != "nt":
                            dfd = os.open(str(d_path), os.O_RDONLY)
                            try:
                                os.fsync(dfd)
                            finally:
                                os.close(dfd)
                        io_disk_oi.append((time.perf_counter() - t0) * 1000.0)

                        tmp_t = t_path / f"state_{n_closed}.tmp.{i}"
                        t0 = time.perf_counter()
                        payload_b2 = orjson.dumps(st_obj, option=orjson.OPT_INDENT_2)
                        fd2 = os.open(str(tmp_t), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                        try:
                            os.write(fd2, payload_b2)
                            os.fsync(fd2)
                        finally:
                            os.close(fd2)
                        os.replace(tmp_t, target_tmpfs)
                        io_tmpfs_oi.append((time.perf_counter() - t0) * 1000.0)

                stage13_res[f"n_{n_closed}"] = {
                    "bytes_json_indent2": len(raw_j_indent),
                    "bytes_orjson_indent2": len(raw_oj_indent),
                    "bytes_orjson_compact": len(raw_oj_compact),
                    "cpu_only_json_dumps_indent2_ms": pcts(c_j, 3),
                    "cpu_only_orjson_indent2_ms": pcts(c_oi, 3),
                    "cpu_only_orjson_compact_ms": pcts(c_oc, 3),
                    "disk_atomic_fsync_json_dump_indent2_ms": pcts(io_disk_j, 3),
                    "disk_atomic_fsync_orjson_indent2_ms": pcts(io_disk_oi, 3),
                    "tmpfs_atomic_orjson_indent2_ms": pcts(io_tmpfs_oi, 3),
                }

    out["stage13_save_state"] = stage13_res
    return out


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="13-Stage Polymarket Latency Benchmark")
    parser.add_argument("--iters", type=int, default=1500, help="Iterations per CPU microbenchmark")
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="Skip read-only CLOB HTTP/WS network RTT probes",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="",
        help="Optional path to data/polymarket directory for historical log analysis",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default="",
        help="Optional output JSON path",
    )
    args = parser.parse_args(argv)
    ddir = Path(args.data_dir) if args.data_dir else None
    results = run_benchmark(iters=args.iters, skip_network=args.skip_network, data_dir=ddir)
    rendered = json.dumps(results, indent=2)
    if args.json_out:
        out_p = Path(args.json_out)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
