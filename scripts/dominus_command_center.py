#!/usr/bin/env python3
"""
DOMINUS — RISKLESS PAA COMMAND CENTER v6.3 (24/7 Zero-Overhead Local Web Dashboard & CLI).

Replaces heavy VM Chrome Remote Desktop (which consumed ~1.74 GB RAM + ~45% CPU on
kraken-finland) with an institutional local command center at http://127.0.0.1:8787 that
fetches bounded read-only JSON snapshots over SSH using 0 MB persistent VM RAM (<20 MiB transient probe RSS).

v6.3 Full-Throttle Architecture:
  - Explicit 3-NAV Triad ($48.70 Guaranteed Floor NAV, $48.83 Mark-to-Bid NAV, $99.21 Book Equity incl. $50.51 frozen KMIA), 4/4 Disputed KMIA D-001 Non-Interference Gate, & 7.04 bps/hr ($0.822/d) Finland VM Hurdle
  - Full-Throttle 14-Family (A..N) Universe Census & Sweep Telemetry (polymarket-full-throttle-sweep.{service,timer}, 19k+ events / 375k+ markets / 401k+ tokens, CLASS_A..E, Rule Traps Blocked, <=50 bps Dormant Watchlist)
  - Strict Principle-8 Non-Conflated Strategy Performance Matrix: Real On-Chain Wallet Trading vs Realistic Forward Shadow across FT_* Live Bridge, Family L Hedged Maker, BOND1, CAL1, COND1, C1, D1, NR_M1/NR2, MKR_LOCK1 & Stage G Cross-Venue
  - Alpha-124 v5.2 Live Catalog & IPC Funnel + Empirical P25 / P50 / P75 Daily Compounding Projections & Milestone ETAs ($150, $253, $500, $5,000)

Usage:
  # Launch 24/7 auto-refreshing browser dashboard on Windows:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" scripts/dominus_command_center.py

  # Instant one-shot terminal summary:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" scripts/dominus_command_center.py --once
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import queue
import subprocess
import threading
import time
import webbrowser
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

REMOTE_PROBE_PY = r"""# -*- coding: utf-8 -*-
import calendar, ctypes, gc, json, math, os, pathlib, re, sqlite3, statistics, subprocess, sys, time
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
    _OTTAWA_TZ = ZoneInfo("America/Toronto")
except Exception:
    _OTTAWA_TZ = timezone(timedelta(hours=-5), "EST")
_HTTP_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def _http_get_json(url, timeout=1.5, data=None, headers=None):
    import urllib.request as _ur
    hdrs = {"User-Agent": _HTTP_UA, "Accept": "application/json", "Connection": "close"}
    if headers:
        hdrs.update(headers)
    req = _ur.Request(url, data=data, headers=hdrs)
    with _ur.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _to_ottawa_dt(val):
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        v = float(val)
        if v <= 0:
            return None
        return datetime.fromtimestamp(v / 1000.0 if v > 1e12 else v, tz=timezone.utc).astimezone(_OTTAWA_TZ)
    s = str(val).strip()
    if not s or s.lower() in ("n/a", "none", "null", "-"):
        return None
    try:
        v = float(s)
        if v > 1e8:
            return datetime.fromtimestamp(v / 1000.0 if v > 1e12 else v, tz=timezone.utc).astimezone(_OTTAWA_TZ)
    except Exception:
        pass
    s = re.sub(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+", "", s, flags=re.IGNORECASE)
    s_norm = s.replace(" UTC", "Z").replace(",", ".")
    if " " in s_norm and "T" not in s_norm:
        s_norm = s_norm.replace(" ", "T", 1)
    if not s_norm.endswith("Z") and "+" not in s_norm[10:] and "-" not in s_norm[10:]:
        s_norm += "Z"
    try:
        return datetime.fromisoformat(s_norm.replace("Z", "+00:00")).astimezone(_OTTAWA_TZ)
    except Exception:
        return None

def _fmt_et(val, fmt="%m-%d %H:%M:%S"):
    dt = _to_ottawa_dt(val)
    return dt.strftime(fmt) if dt is not None else ""

def _to_unix(val):
    dt = _to_ottawa_dt(val)
    return dt.timestamp() if dt is not None else None

def _is_raw_stub_title(t):
    s = str(t or "").strip()
    return (not s) or s.startswith("Token ") or s.startswith("SPORTS_") or s.startswith("SINGLE_LEG_")

root = pathlib.Path(os.environ.get("DOMINUS_QUANT_ROOT") or "/home/skybullet1987/quant_pipeline")
_OFFLINE_PROBE = os.environ.get("DOMINUS_OFFLINE_PROBE") == "1"
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
_now_et = datetime.now(_OTTAWA_TZ)
out = {
    "fetched_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    "fetched_at_et": _now_et.strftime("%Y-%m-%d %H:%M:%S %Z"),
    "ottawa_tz_abbr": _now_et.strftime("%Z"),
    "unix_ts": time.time(),
    "dashboard_version": "6.3.0",
}

# 1. Host load & memory
try:
    la = os.getloadavg()
    out["load_avg"] = [round(la[0], 2), round(la[1], 2), round(la[2], 2)]
except Exception:
    out["load_avg"] = [0.0, 0.0, 0.0]

mem = {}
try:
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            mem[parts[0].rstrip(":")] = int(parts[1]) // 1024
    out["mem_mb"] = {
        "total": mem.get("MemTotal", 0),
        "available": mem.get("MemAvailable", 0),
        "used": max(0, mem.get("MemTotal", 0) - mem.get("MemAvailable", 0)),
        "swap_free": mem.get("SwapFree", 0),
        "swap_total": mem.get("SwapTotal", 0),
    }
except Exception:
    out["mem_mb"] = {}

# 2. Services (single batched systemctl call for consolidated Riskless PAA + Full-Throttle + Stage G Cross-Venue topology)
svcs = [
    "polymarket-live-harvester.service",
    "polymarket-alpha124-shadow.service",
    "polymarket-cross-venue-shadow.service",
    "polymarket-cross-venue-shadow-watchdog.timer",
    "polymarket-recorder.service",
    "polymarket-telemetry-compactor.timer",
    "polymarket-paa-monitor.timer",
    "polymarket-paa-director.timer",
    "polymarket-full-throttle-sweep.timer",
]
shm_ages = {}
shm_spots = {}
shm_anchored = {}
for _sym in ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "HYPE", "XAU", "XAG"):
    _fp = pathlib.Path(f"/dev/shm/pm_fast_tick_{_sym}.json")
    if _fp.exists():
        shm_ages[_sym] = round(time.time() - _fp.stat().st_mtime, 2)
        try:
            _fd = json.loads(_fp.read_text())
            _px = float(_fd.get("chainlink_proxy_spot") or _fd.get("spot") or 0.0)
            if _px > 0:
                shm_spots[_sym] = round(_px, 4 if _px < 10 else 2)
            shm_anchored[_sym] = bool(_fd.get("chainlink_basis_anchored", False))
        except Exception:
            pass
    elif _sym in ("BTC", "ETH", "SOL", "XAU"):
        shm_ages[_sym] = None
out["shm_fast_tick_age_sec"] = shm_ages
out["shm_spots"] = shm_spots
out["shm_anchored"] = shm_anchored

strat_cfg = {}
cfg_path = root / "config/polymarket_strategy_and_risk.json"
if cfg_path.exists():
    try:
        strat_cfg = json.loads(cfg_path.read_text())
    except Exception:
        strat_cfg = {}
out["strategy_config"] = {
    "schema_version": strat_cfg.get("schema_version", "5.4.1"),
    "directional": strat_cfg.get("directional") or {},
    "routing": strat_cfg.get("routing") or {},
    "exit_supervisor": strat_cfg.get("exit_supervisor") or {},
    "risk_controller": strat_cfg.get("risk_controller") or {},
    "sizing_tiers": strat_cfg.get("sizing_tiers") or {},
    "riskless_boxes": strat_cfg.get("riskless_boxes") or {},
}
svc_map = {}
_ft_sysd = {
    "service_unit": "polymarket-full-throttle-sweep.service",
    "timer_unit": "polymarket-full-throttle-sweep.timer",
    "service_active_state": "unknown",
    "service_sub_state": "unknown",
    "result": "unknown",
    "exec_main_status": None,
    "memory_peak_mib": None,
    "memory_max_mib": 220.0,
    "cgroup_memory_ok": True,
    "swapless_180mib_ok": True,
    "last_start_utc": "",
    "last_exit_utc": "",
    "last_exit_et": "",
    "timer_active_state": "unknown",
    "last_trigger_et": "-",
    "last_trigger_ago_sec": None,
    "next_trigger_et": "-",
    "next_trigger_in_sec": None,
}
if not _OFFLINE_PROBE:
    try:
        r = subprocess.run(["systemctl", "--user", "is-active", *svcs], capture_output=True, text=True, timeout=3)
        statuses = [ln.strip() for ln in r.stdout.splitlines()]
        for idx, sv in enumerate(svcs):
            key = sv.replace(".service", "")
            svc_map[key] = statuses[idx] if idx < len(statuses) and statuses[idx] else "unknown"
    except Exception:
        for sv in svcs:
            svc_map[sv.replace(".service", "")] = "unknown"
    try:
        _ft_sh = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                "polymarket-full-throttle-sweep.service",
                "polymarket-full-throttle-sweep.timer",
                "--no-pager",
                "-p",
                "Id,ActiveState,SubState,Result,ExecMainStatus,MemoryPeak,MemoryMax,ExecMainStartTimestamp,ExecMainStartTimestampUTC,ExecMainExitTimestamp,ExecMainExitTimestampUTC,LastTriggerUSec,LastTriggerUSecRealtime,NextElapseUSecRealtime",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if _ft_sh.returncode == 0 and _ft_sh.stdout.strip():
            _blks = [b for b in _ft_sh.stdout.strip().split("\n\n") if b.strip()]
            _now_ft_u = time.time()
            for _blk in _blks:
                _kv = {}
                for _ln_b in _blk.splitlines():
                    if "=" in _ln_b:
                        _k_b, _v_b = _ln_b.split("=", 1)
                        _kv[_k_b.strip()] = _v_b.strip()
                _uid = _kv.get("Id") or ""
                if _uid.endswith(".service"):
                    _ft_sysd["service_active_state"] = _kv.get("ActiveState") or "unknown"
                    _ft_sysd["service_sub_state"] = _kv.get("SubState") or "unknown"
                    _ft_sysd["result"] = _kv.get("Result") or "unknown"
                    try:
                        _ft_sysd["exec_main_status"] = int(_kv["ExecMainStatus"]) if _kv.get("ExecMainStatus", "").lstrip("-").isdigit() else None
                    except Exception:
                        pass
                    try:
                        _mm_raw = int(_kv.get("MemoryMax") or "0")
                        if 0 < _mm_raw < (1 << 60):
                            _ft_sysd["memory_max_mib"] = round(_mm_raw / (1024.0 * 1024.0), 1)
                    except Exception:
                        pass
                    try:
                        _mp_raw = int(_kv.get("MemoryPeak") or "0")
                        if 0 < _mp_raw < (1 << 60):
                            _mp_mib = round(_mp_raw / (1024.0 * 1024.0), 1)
                            _ft_sysd["memory_peak_mib"] = _mp_mib
                            _ft_sysd["cgroup_memory_ok"] = _mp_mib <= float(_ft_sysd["memory_max_mib"] or 220.0)
                            _ft_sysd["swapless_180mib_ok"] = _mp_mib <= 180.0
                    except Exception:
                        pass
                    _ft_sysd["last_start_utc"] = _kv.get("ExecMainStartTimestampUTC") or _kv.get("ExecMainStartTimestamp") or ""
                    _ft_sysd["last_exit_utc"] = _kv.get("ExecMainExitTimestampUTC") or _kv.get("ExecMainExitTimestamp") or ""
                    if _ft_sysd["last_exit_utc"]:
                        _ft_sysd["last_exit_et"] = _fmt_et(_ft_sysd["last_exit_utc"], "%m-%d %H:%M:%S")
                    # Reflect healthy oneshot status in services map
                    if _ft_sysd["service_active_state"] == "active" or (_ft_sysd["result"] == "success" and _ft_sysd["exec_main_status"] in (0, None)):
                        svc_map["polymarket-full-throttle-sweep"] = "active"
                    elif _ft_sysd["result"] not in ("", "unknown"):
                        svc_map["polymarket-full-throttle-sweep"] = f"{_ft_sysd['result']}({_ft_sysd['exec_main_status']})"
                elif _uid.endswith(".timer"):
                    _ft_sysd["timer_active_state"] = _kv.get("ActiveState") or "unknown"
                    for _tks, _ek, _sk, _is_future in (
                        (("LastTriggerUSecRealtime", "LastTriggerUSec"), "last_trigger_et", "last_trigger_ago_sec", False),
                        (("NextElapseUSecRealtime",), "next_trigger_et", "next_trigger_in_sec", True),
                    ):
                        _tv = ""
                        for _tk_c in _tks:
                            if _kv.get(_tk_c):
                                _tv = _kv[_tk_c]
                                break
                        _tu = None
                        if _tv.isdigit() and int(_tv) > 0 and int(_tv) < (1 << 62):
                            _tu = int(_tv) / 1e6
                        elif _tv:
                            _tu = _to_unix(_tv)
                        if _tu is not None and _tu > 0:
                            _ft_sysd[_ek] = _fmt_et(_tu, "%H:%M:%S")
                            _ft_sysd[_sk] = round(max(0.0, (_tu - _now_ft_u) if _is_future else (_now_ft_u - _tu)), 1)
    except Exception:
        pass
    try:
        _sup_p = subprocess.run(["systemctl", "is-active", "paa-system-supervisor.timer"], capture_output=True, text=True, timeout=2)
        if _sup_p.returncode == 0 and _sup_p.stdout.strip() == "active":
            svc_map["paa-system-supervisor.timer"] = "active"
    except Exception:
        pass
else:
    for sv in svcs:
        svc_map[sv.replace(".service", "")] = "active"
    svc_map["polymarket-full-throttle-sweep"] = "active"
    _ft_sysd.update({"service_active_state": "inactive", "result": "success", "exec_main_status": 0, "timer_active_state": "active"})
out["services"] = svc_map
out["full_throttle_systemd"] = _ft_sysd

_UNHEDGED_DIR_SLEEVES = {
    "SLEEVE_1_CORE_302",
    "SLEEVE_1_SUBHOURLY_15M",
    "DIRECTIONAL_1H",
    "DIRECTIONAL_15M",
}
_PAUSED_RB_SET = {
    str(x).strip().upper()
    for x in (((strat_cfg.get("riskless_boxes") or {}).get("paused_riskless_sleeves")) or [])
    if str(x).strip()
}

def _is_pure_riskless_sleeve(slv_name):
    su = str(slv_name or "").strip().upper()
    if not su or su == "UNKNOWN":
        return False
    if su in _UNHEDGED_DIR_SLEEVES or su in _PAUSED_RB_SET:
        return False
    return True

# Collect recent live IPC candidates once (used for both resting CLOB order metadata AND Riskless Radar)
_recent_ipc_cands = []
_cand_p = root / "data/polymarket/d1_live_box_candidates.jsonl"
if _cand_p.exists():
    try:
        with open(_cand_p, "rb") as _cf:
            _csz = _cand_p.stat().st_size
            _cf.seek(max(0, _csz - 262144))
            _clines = _cf.read().decode("utf-8", errors="replace").splitlines()[1 if _csz > 262144 else 0 :]
        for _cl in _clines:
            if _cl.strip():
                try:
                    _recent_ipc_cands.append(json.loads(_cl))
                except Exception:
                    pass
    except Exception:
        pass

# 3. Polymarket Live Harvester + Per-Strategy Real W/L + Live Working CLOB Orders
lh_path = root / "data/polymarket/live_harvester_state.json"
if lh_path.exists():
    s = json.loads(lh_path.read_text())
    def _is_phantom_unexecuted(c: dict) -> bool:
        if str(c.get("status") or "").upper() == "NOT_EXECUTED":
            return True
        if (
            str(c.get("exit_order_status") or "").upper() == "ENTRY_OUTCOME_UNKNOWN"
            and not bool(c.get("inventory_reconciled", True))
            and str(c.get("close_reason") or "").upper() == "MARKET_RESOLVED_NO_INVENTORY"
        ):
            return True
        return False

    closed_all = s.get("closed_positions") or []
    closed = [c for c in closed_all if not _is_phantom_unexecuted(c)]

    # Authoritative live Polygon wallet cash (pUSD + USDC.e)
    _wallet_addr = ""
    _env_p = root / ".env"
    if _env_p.exists():
        for _eln in _env_p.read_text(errors="ignore").splitlines():
            if _eln.startswith("POLYGON_FUNDER_ADDRESS="):
                _wallet_addr = _eln.split("=", 1)[1].strip().strip('"').strip("'")
                break
    _p_state = globals().get("_PERSIST") if isinstance(globals().get("_PERSIST"), dict) else None
    _onchain_cash = None
    _oc_cache_p = pathlib.Path("/tmp/dominus_onchain_cash_cache.json")
    _oc_cached = (_p_state.get("onchain_cash_cache") if _p_state is not None else None)
    if isinstance(_oc_cached, tuple) and len(_oc_cached) == 2 and (time.time() - float(_oc_cached[0])) <= 20.0:
        _onchain_cash = _oc_cached[1]
    elif _OFFLINE_PROBE and s.get("_mock_onchain_cash") is not None:
        _onchain_cash = float(s["_mock_onchain_cash"])
    elif (not _OFFLINE_PROBE) and _oc_cache_p.exists() and (time.time() - _oc_cache_p.stat().st_mtime) <= 30.0:
        try:
            _onchain_cash = float(json.loads(_oc_cache_p.read_text(encoding="utf-8")).get("cash"))
        except Exception:
            _onchain_cash = None
    if _onchain_cash is None and (not _OFFLINE_PROBE) and _wallet_addr.startswith("0x") and len(_wallet_addr) == 42:
        _call_d = "0x70a08231" + _wallet_addr[2:].lower().rjust(64, "0")
        _batch = json.dumps([
            {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB", "data": _call_d}, "latest"], "id": 1},
            {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", "data": _call_d}, "latest"], "id": 2},
        ]).encode("utf-8")
        for _rpc_u in ("https://polygon-bor-rpc.publicnode.com", "https://polygon-rpc.com", "https://1rpc.io/matic"):
            try:
                _rj = _http_get_json(_rpc_u, timeout=1.8, data=_batch, headers={"Content-Type": "application/json"})
                if isinstance(_rj, list) and len(_rj) == 2 and all(isinstance(x, dict) and str(x.get("result") or "").startswith("0x") for x in _rj):
                    _onchain_cash = sum(int(x["result"], 16) / 1e6 for x in _rj)
                    if _p_state is not None:
                        _p_state["onchain_cash_cache"] = (time.time(), _onchain_cash)
                    try:
                        _oc_cache_p.write_text(json.dumps({"ts": time.time(), "cash": _onchain_cash}), encoding="utf-8")
                    except Exception:
                        pass
                    break
            except Exception:
                continue

    _state_cash = float(s.get("live_bankroll", 0.0) or 0.0)
    _wallet_cash = float(_onchain_cash) if _onchain_cash is not None else _state_cash

    # Zero-credential (<20 MiB RSS, D-002/D-003 MODE 1/2) live open orders from /tmp cache or Harvester pending_entry_intents
    resting_orders = []
    _clob_buy_quoting_usd = 0.0
    _resting_redeem_edge_usd = 0.0
    _clob_orders_ok = False
    _orphan_orders_cnt = 0
    _fifo_rank1_live_cnt = 0
    try:
        _ord_cache_p = pathlib.Path("/tmp/dominus_clob_open_orders_cache.json")
        _tok_meta_cache_p = pathlib.Path("/tmp/dominus_clob_tok_meta_cache.json")
        _tok_meta = {}
        _tok_meta_trimmed = False
        if (not _OFFLINE_PROBE) and _tok_meta_cache_p.exists():
            try:
                if _tok_meta_cache_p.stat().st_size <= 262144:
                    _tok_meta = json.loads(_tok_meta_cache_p.read_text(encoding="utf-8"))
                else:
                    _raw_tm = json.loads(_tok_meta_cache_p.read_text(encoding="utf-8"))
                    if isinstance(_raw_tm, dict):
                        _keep_tm = [(_k, _v) for _k, _v in _raw_tm.items() if isinstance(_v, dict) and _v.get("title")]
                        for _k, _v in _keep_tm[-240:]:
                            _tok_meta[_k] = _v
                    del _raw_tm
                    _tok_meta_trimmed = True
            except Exception:
                _tok_meta = {}
        if len(_tok_meta) > 350:
            _tok_meta = dict(list(_tok_meta.items())[-250:])
            _tok_meta_trimmed = True
        _intent_vel_by_oid = {}
        _synth_intent_ords = []
        _now_pi = time.time()
        for _ik_p, _iv_p in (s.get("pending_entry_intents") or {}).items():
            if not isinstance(_iv_p, dict):
                continue
            if bool(_iv_p.get("fifo_rank1_verified")):
                _fifo_rank1_live_cnt += 1
            _hb_p = max(float(_iv_p.get("heartbeat_ts") or 0.0), float(_iv_p.get("ts", _iv_p.get("created_ts", 0.0)) or 0.0))
            if (not _OFFLINE_PROBE) and _hb_p > 0.0 and (_now_pi - _hb_p) > 300.0 and not bool(_iv_p.get("live_maker_anchor_inflight")):
                continue
            _oid_p = str(_iv_p.get("entry_order_id") or _iv_p.get("maker_order_id") or _iv_p.get("order_id") or _ik_p).strip()
            _aid_p = str(_iv_p.get("token_id") or _iv_p.get("asset_id") or "").strip()
            _px_p = float(_iv_p.get("anchor_bid_px") or _iv_p.get("limit_price") or _iv_p.get("price") or 0.0)
            _not_p = float(_iv_p.get("posted_notional_usd") or _iv_p.get("notional_usd") or 0.0)
            _sh_p = float(_iv_p.get("posted_shares") or _iv_p.get("shares") or (_not_p / _px_p if _px_p > 0 else 0.0))
            _m_not_p = float(_iv_p.get("matched_notional_usd") or 0.0)
            _m_sh_p = round(_m_not_p / _px_p, 4) if (_px_p > 0 and _m_not_p > 0) else float(_iv_p.get("matched_shares") or 0.0)
            _vel_p = float(_iv_p.get("effective_velocity_bps_hr") or _iv_p.get("velocity_bps_hr") or 0.0)
            if _oid_p and _vel_p > 0:
                _intent_vel_by_oid[_oid_p] = _vel_p
            if _aid_p:
                _prev_mp = _tok_meta.get(_aid_p) or {}
                _prev_tp = str(_prev_mp.get("title") or "")
                _tok_meta[_aid_p] = {
                    "market_id": str(_iv_p.get("market_id") or _prev_mp.get("market_id") or ""),
                    "sleeve": str(_iv_p.get("sleeve_source") or _iv_p.get("sleeve") or _prev_mp.get("sleeve") or "BOND1_UMA_RESOLUTION_CARRY"),
                    "expiry_ts": float(_iv_p.get("expiry_ts") or _prev_mp.get("expiry_ts") or 0.0),
                    "title": "" if _is_raw_stub_title(_prev_tp) else _prev_tp,
                    "outcome": str(_iv_p.get("outcome") or _iv_p.get("target_token") or _prev_mp.get("outcome") or ""),
                    "fallback_label": str(_iv_p.get("title") or _iv_p.get("asset") or _prev_mp.get("fallback_label") or ""),
                    "neg_ts": float(_prev_mp.get("neg_ts") or 0.0),
                }
            if _px_p > 0 and _sh_p > 0.001:
                _synth_intent_ords.append({
                    "id": _oid_p,
                    "status": "LIVE",
                    "asset_id": _aid_p,
                    "side": str(_iv_p.get("side") or "BUY").upper(),
                    "price": _px_p,
                    "original_size": _sh_p,
                    "size_matched": _m_sh_p,
                    "outcome": str(_iv_p.get("outcome") or _iv_p.get("target_token") or (_tok_meta.get(_aid_p) or {}).get("outcome") or ""),
                    "order_type": "GTC",
                    "created_at": float(_iv_p.get("ts") or _iv_p.get("created_ts") or _hb_p or 0.0),
                })
        _raw_ords = None
        if _OFFLINE_PROBE:
            _raw_ords = s.get("_mock_open_orders") if isinstance(s.get("_mock_open_orders"), list) else _synth_intent_ords
        elif _ord_cache_p.exists() and (time.time() - _ord_cache_p.stat().st_mtime) <= 15.0:
            try:
                _raw_ords = json.loads(_ord_cache_p.read_text(encoding="utf-8"))
            except Exception:
                _raw_ords = None
        if _raw_ords is None:
            _raw_ords = _synth_intent_ords
        if isinstance(_raw_ords, list):
            _clob_orders_ok = True
        for _cd in _recent_ipc_cands:
            try:
                _tid_c = str(_cd.get("leg_a_token_id") or "")
                if _tid_c:
                    _prev_m = _tok_meta.get(_tid_c) or {}
                    _prev_ttl = str(_prev_m.get("title") or "")
                    _fb_lbl = str(_cd.get("leg_a_label") or _cd.get("regime") or _prev_m.get("fallback_label") or "").replace("SINGLE_LEG_MAKER_LOCK_", "")
                    _tok_meta[_tid_c] = {
                        "market_id": str(_cd.get("leg_a_market_id") or _prev_m.get("market_id") or ""),
                        "sleeve": str(_cd.get("sleeve_source") or _prev_m.get("sleeve") or "BOND1_UMA_RESOLUTION_CARRY"),
                        "expiry_ts": float(_cd.get("expiry_ts") or _prev_m.get("expiry_ts") or 0.0),
                        "title": "" if _is_raw_stub_title(_prev_ttl) else _prev_ttl,
                        "outcome": str(_prev_m.get("outcome") or _cd.get("leg_a_side") or ""),
                        "fallback_label": _fb_lbl,
                        "neg_ts": float(_prev_m.get("neg_ts") or 0.0),
                    }
            except Exception:
                pass
        _meta_dirty = bool(locals().get("_tok_meta_trimmed", False))
        _tracked_oids_cc = {
            str(_v_id).strip()
            for _d_rec in (*(s.get("pending_entry_intents") or {}).values(), *(s.get("active_positions") or {}).values())
            if isinstance(_d_rec, dict)
            for _v_id in (
                _d_rec.get("entry_order_id"),
                _d_rec.get("order_id"),
                _d_rec.get("exit_order_id"),
                _d_rec.get("unwind_order_id"),
                _d_rec.get("maker_order_id"),
            )
            if _v_id
        }
        for _o in (_raw_ords or []):
            if not isinstance(_o, dict) or str(_o.get("status") or "").upper() not in ("LIVE", "OPEN"):
                continue
            _oid_cc = str(_o.get("id") or _o.get("orderID") or "").strip()
            _cts_dt = _to_ottawa_dt(_o.get("created_at"))
            _cts_o = _cts_dt.timestamp() if _cts_dt is not None else 0.0
            if _cts_o > 0.0 and (time.time() - _cts_o) > 3600.0 and (not _oid_cc or _oid_cc not in _tracked_oids_cc):
                _orphan_orders_cnt += 1
                continue
            _aid = str(_o.get("asset_id") or "")
            _side_o = str(_o.get("side") or "BUY").upper()
            _px_o = float(_o.get("price") or 0.0)
            _osz_o = float(_o.get("original_size") or 0.0)
            _msz_o = float(_o.get("size_matched") or 0.0)
            _rem_sz = max(0.0, _osz_o - _msz_o)
            if _rem_sz <= 0.001:
                continue
            _not_o = round(_rem_sz * _px_o, 2)
            _edge_u = round(max(0.0, _rem_sz * 1.0 - _not_o), 2) if _side_o == "BUY" else 0.0
            if _side_o == "BUY":
                _clob_buy_quoting_usd += _not_o
                _resting_redeem_edge_usd += _edge_u
            _m_info = _tok_meta.get(_aid) or {}
            _mid_o = str(_m_info.get("market_id") or "")
            _ttl_o = str(_m_info.get("title") or "")
            _outc_o = str(_o.get("outcome") or _m_info.get("outcome") or "")
            if (not _OFFLINE_PROBE) and (_is_raw_stub_title(_ttl_o) or not _outc_o) and (time.time() - float(_m_info.get("neg_ts") or 0.0)) >= 3600.0:
                _resolved_o = False
                try:
                    _gurl = (
                        f"https://gamma-api.polymarket.com/markets/{_mid_o}"
                        if _mid_o.isdigit()
                        else f"https://gamma-api.polymarket.com/markets?clob_token_ids={_aid}"
                    )
                    _gj = _http_get_json(_gurl, timeout=1.5)
                    if isinstance(_gj, list) and _gj:
                        _gj = _gj[0]
                    if isinstance(_gj, dict):
                        _q_txt = str(_gj.get("question") or _gj.get("title") or "").strip()
                        if not _mid_o and _gj.get("id"):
                            _mid_o = str(_gj.get("id"))
                        if not _outc_o and _aid:
                            try:
                                _g_tids = json.loads(_gj["clobTokenIds"]) if isinstance(_gj.get("clobTokenIds"), str) else (_gj.get("clobTokenIds") or [])
                                _g_outs = json.loads(_gj["outcomes"]) if isinstance(_gj.get("outcomes"), str) else (_gj.get("outcomes") or [])
                                if _aid in _g_tids:
                                    _idx_gt = _g_tids.index(_aid)
                                    if _idx_gt < len(_g_outs):
                                        _outc_o = str(_g_outs[_idx_gt])
                            except Exception:
                                pass
                        if _q_txt and not _is_raw_stub_title(_q_txt):
                            _ttl_o = _q_txt
                            _tok_meta[_aid] = {**_m_info, "market_id": _mid_o, "title": _ttl_o, "outcome": _outc_o or _m_info.get("outcome") or "", "neg_ts": 0.0}
                            _meta_dirty = True
                            _resolved_o = True
                except Exception:
                    pass
                if not _resolved_o:
                    _tok_meta[_aid] = {**_m_info, "market_id": _mid_o, "outcome": _outc_o or _m_info.get("outcome") or "", "neg_ts": time.time()}
                    _meta_dirty = True
            if _is_raw_stub_title(_ttl_o):
                _ttl_o = str(_m_info.get("fallback_label") or "") or f"Market #{_mid_o or _aid[:10]}"
            _exp_o = float(_m_info.get("expiry_ts") or 0.0)
            _rem_min = round((_exp_o - time.time()) / 60.0, 1) if _exp_o > time.time() else None
            _slv_o = str(_m_info.get("sleeve") or "BOND1_UMA_RESOLUTION_CARRY")
            _uma_floor_hr = 0.35 if "MKR_LOCK1" in _slv_o else 1.25
            _hold_hr = max(_uma_floor_hr, (_rem_min / 60.0) if (_rem_min is not None and _rem_min > 0) else 1.5)
            _edge_bps = round(max(0.0, (1.0 - _px_o) * 10000.0), 1)
            _bps_hr = round(_intent_vel_by_oid.get(_oid_cc) or (_edge_bps / max(0.25, _hold_hr)), 1)
            resting_orders.append({
                "order_id": _oid_cc,
                "market_id": _mid_o,
                "title": _ttl_o,
                "sleeve": _slv_o,
                "side": _side_o,
                "outcome": _outc_o or "YES",
                "price": _px_o,
                "shares": round(_rem_sz, 2),
                "matched_shares": round(_msz_o, 2),
                "notional_usd": _not_o,
                "redeem_edge_usd": _edge_u,
                "edge_bps": _edge_bps,
                "est_bps_per_hr": _bps_hr,
                "order_type": str(_o.get("order_type") or "GTC"),
                "status": str(_o.get("status") or "LIVE"),
                "age_sec": max(0, int(time.time() - _cts_o)) if _cts_o > 0 else 0,
                "rem_min": _rem_min,
            })
        if _meta_dirty:
            try:
                _tok_meta_cache_p.write_text(json.dumps(_tok_meta), encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass

    if _clob_orders_ok:
        _inflight_intents_usd = round(_clob_buy_quoting_usd, 2)
    else:
        _now_int = time.time()
        _inflight_intents_usd = round(
            sum(
                float(i.get("notional_usd", 0.0) or 0.0)
                for i in (s.get("pending_entry_intents") or {}).values()
                if isinstance(i, dict)
                and (_now_int - max(float(i.get("heartbeat_ts") or 0.0), float(i.get("ts", i.get("created_ts", 0.0)) or 0.0))) <= 90.0
            ),
            2,
        )
    _free_cash_usd = round(max(0.0, _wallet_cash - _inflight_intents_usd), 2)
    _quoting_util_pct = round(min(100.0, 100.0 * _inflight_intents_usd / max(0.01, _wallet_cash)), 1) if _wallet_cash > 0 else 0.0
    def _compute_cc_valuations(s_doc: dict, wallet_cash_v: float, onchain_cash_v) -> tuple[dict, float, float, float]:
        act_m = s_doc.get("active_positions") or {}

        def _pos_live_book_val(p: dict) -> float:
            if not isinstance(p, dict):
                return 0.0
            if onchain_cash_v is not None:
                if bool(p.get("_pre_redeemed_onchain")):
                    return 0.0
                if str(p.get("pending_settlement_close_reason") or "").upper() in {"MARKET_RESOLVED_LOSS", "EXPIRED_OUT_OF_MONEY"}:
                    return 0.0
            return float(p.get("remaining_cost_basis", p.get("notional_usd", 0.0)) or 0.0)

        def _is_unhedged_resid_cc(p: dict) -> bool:
            return (
                isinstance(p, dict)
                and (
                    bool(p.get("is_legged_out_residual"))
                    or str(p.get("box_type") or "").upper() == "MULTI_LEG_RESIDUAL"
                    or "_UNWRESID_" in str(p.get("trade_id") or "")
                )
            )

        def _is_uma_disputed_cc(p: dict) -> bool:
            if not isinstance(p, dict):
                return False
            if bool(p.get("uma_disputed") or p.get("is_uma_disputed") or p.get("disputed")):
                return True
            for k_st in ("umaResolutionStatus", "uma_resolution_status", "uma_status", "resolution_status"):
                if "disput" in str(p.get(k_st) or "").strip().lower():
                    return True
            return False

        def _is_floor_zero_cc(p: dict) -> bool:
            return _is_unhedged_resid_cc(p) or _is_uma_disputed_cc(p)

        def _intent_synced_eq_cc(i: dict) -> float:
            if not isinstance(i, dict):
                return 0.0
            explicit_sync = max(0.0, float(i.get("synced_equity_usd", 0.0) or 0.0))
            if explicit_sync > 0.0:
                return explicit_sync
            if not i.get("live_maker_anchor_inflight"):
                return 0.0
            matched_u = max(0.0, float(i.get("matched_notional_usd", 0.0) or 0.0))
            drop_u = max(0.0, float(i.get("collat_drop_usd", 0.0) or 0.0))
            posted_cap = max(matched_u, float(i.get("posted_notional_usd", i.get("notional_usd", 0.0)) or 0.0))
            return min(posted_cap, drop_u) if drop_u > 0.0 else 0.0

        pending_synced = (
            sum(
                _intent_synced_eq_cc(i)
                for i in (s_doc.get("pending_entry_intents") or {}).values()
                if isinstance(i, dict)
            )
            if onchain_cash_v is not None
            else 0.0
        )
        active_book_u = round(sum(_pos_live_book_val(p) for p in act_m.values() if isinstance(p, dict)) + pending_synced, 2)
        live_eq_u = (
            round(wallet_cash_v + active_book_u, 2)
            if onchain_cash_v is not None
            else round(float(s_doc.get("total_account_equity", 0.0) or 0.0), 2)
        )
        box_grps = {}
        for p_act in act_m.values():
            if (
                isinstance(p_act, dict)
                and p_act.get("is_dominance_box")
                and p_act.get("box_id")
                and not (onchain_cash_v is not None and p_act.get("_pre_redeemed_onchain"))
            ):
                box_grps.setdefault(str(p_act["box_id"]), []).append(p_act)
        paired_ids = {
            bid
            for bid, legs in box_grps.items()
            if len(legs) == 2
            and not any(_is_floor_zero_cc(lg) for lg in legs)
            and all(float(lg.get("custom_maker_exit_price") or 0.99) >= 0.95 for lg in legs)
        }
        redeem_floor_pos = (
            sum(
                min(float(lg.get("remaining_shares", lg.get("entry_shares", 0.0)) or 0.0) for lg in box_grps[bid])
                for bid in paired_ids
            )
            + sum(
                0.0 if _is_floor_zero_cc(p) else _pos_live_book_val(p)
                for p in act_m.values()
                if isinstance(p, dict) and str(p.get("box_id") or "") not in paired_ids
            )
            + pending_synced
        )
        guar_floor_u = round(wallet_cash_v + redeem_floor_pos, 2)
        return act_m, active_book_u, live_eq_u, guar_floor_u

    _act_map, _active_book_usd, _live_equity_usd, _guaranteed_redeem_equity_usd = _compute_cc_valuations(
        s, _wallet_cash, _onchain_cash
    )
    _ONCHAIN_WALLET_RECON = {
        "LIVE_6399804_1793391806_DOWN": {"pnl": -18.63, "notional": 18.63, "entry_px": 0.81},
    }
    def _reconcile_closed_leg(c: dict) -> tuple[float, float, bool, dict]:
        raw = round(float(c.get("net_pnl_usd", 0.0) or 0.0), 2)
        cn = dict(c)
        ovr = _ONCHAIN_WALLET_RECON.get(str(c.get("trade_id") or ""))
        if ovr is not None:
            cn["net_pnl_usd"] = ovr["pnl"]
            cn["realized_pnl_usd"] = ovr["pnl"]
            cn["notional_usd"] = ovr["notional"]
            cn["entry_price"] = ovr["entry_px"]
            cn["wallet_reconciled"] = True
            return ovr["pnl"], raw, True, cn
        _tgt_t = str(c.get("target_token") or "").strip().upper()
        _res_w = str(c.get("resolved_winning_outcome") or "").strip().upper()
        _ent_sh = float(c.get("entry_shares", 0.0) or 0.0)
        _fill_ex_sh = float(c.get("filled_exit_shares", 0.0) or 0.0)
        if (
            str(c.get("close_reason") or "") == "MARKET_RESOLVED_NO_INVENTORY"
            and bool(c.get("inventory_reconciled", False))
            and str(c.get("exit_order_status") or "").upper() == "DETERMINISTIC_TERMINAL_HOLD"
            and _fill_ex_sh <= 0.0
            and _ent_sh > 0.0
            and _tgt_t != ""
            and _tgt_t == _res_w
        ):
            _pay_u = round(_ent_sh * 1.0, 4)
            _fee_u = float(c.get("entry_fee_cash_usd", c.get("fee_usd", 0.0)) or 0.0) + float(c.get("realized_exit_fee", 0.0) or 0.0)
            wallet_pnl = round(_pay_u - float(c.get("notional_usd", 0.0) or 0.0) - _fee_u, 2)
            cn["payout_usd"] = _pay_u
            cn["net_pnl_usd"] = wallet_pnl
            cn["realized_pnl_usd"] = wallet_pnl
            cn["won"] = True
            cn["average_exit_price"] = 1.0
            cn["exit_price"] = 1.0
            cn["close_reason"] = "ONCHAIN_AUTO_REDEEMED_RECONCILED"
            cn["wallet_reconciled"] = True
            return wallet_pnl, raw, True, cn
        if (
            _ent_sh > 0.0
            and _fill_ex_sh > _ent_sh + 0.05
            and not (c.get("box_legs_summary") or [])
            and str(c.get("exit_order_status") or "").upper() == "DETERMINISTIC_TERMINAL_HOLD"
            and _tgt_t != ""
            and _tgt_t == _res_w
        ):
            _pay_u = round(_ent_sh * 1.0, 4)
            _fee_u = float(c.get("entry_fee_cash_usd", c.get("fee_usd", 0.0)) or 0.0)
            wallet_pnl = round(_pay_u - float(c.get("notional_usd", 0.0) or 0.0) - _fee_u, 2)
            cn["filled_exit_shares"] = 0.0
            cn["realized_exit_cash"] = 0.0
            cn["confirmed_realized_cash"] = _pay_u
            cn["payout_usd"] = _pay_u
            cn["net_pnl_usd"] = wallet_pnl
            cn["realized_pnl_usd"] = wallet_pnl
            cn["won"] = True
            cn["average_exit_price"] = 1.0
            cn["exit_price"] = 1.0
            cn["close_reason"] = "ONCHAIN_AUTOREDEEM_CONFIRMED"
            cn["wallet_reconciled"] = True
            return wallet_pnl, raw, True, cn
        if (
            c.get("is_dominance_box")
            and float(c.get("fee_rate_applied", 0.07) or 0.0) == 0.0
            and c.get("exit_fee_estimated")
            and float(c.get("payout_usd", 0.0) or 0.0) > float(c.get("notional_usd", 0.0) or 0.0)
        ):
            wallet_pnl = round(float(c.get("payout_usd", 0.0)) - float(c.get("notional_usd", 0.0)) - float(c.get("fee_usd", 0.0) or 0.0), 2)
            cn["net_pnl_usd"] = wallet_pnl
            cn["realized_pnl_usd"] = wallet_pnl
            cn["wallet_reconciled"] = True
            return wallet_pnl, raw, True, cn
        cn["net_pnl_usd"] = raw
        return raw, raw, False, cn

    wins_raw = sum(1 for c in closed if float(c.get("net_pnl_usd", 0.0)) > 0)
    tot_pnl_raw = round(sum(float(c.get("net_pnl_usd", 0.0)) for c in closed), 2)
    tot_fees = round(sum(float(c.get("fee_usd", 0.0)) for c in closed), 2)
    closed_norm = []
    tot_pnl_wallet = 0.0
    for c in closed:
        wp_c, rp_c, adj_c, cn_c = _reconcile_closed_leg(c)
        cn_c["_raw_pnl_usd"] = rp_c
        cn_c["_fee_reconciled"] = adj_c
        tot_pnl_wallet = round(tot_pnl_wallet + wp_c, 2)
        closed_norm.append(cn_c)

    try:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from src.paa_os.optimizer import group_closed_positions_by_box as _grp_boxes
        grouped_closed = _grp_boxes(closed_norm, _act_map)
    except Exception:
        grouped_closed = closed_norm

    wins_wallet = 0
    losses_wallet = 0
    pure_rl_w, pure_rl_l, pure_rl_flat, pure_rl_pnl = 0, 0, 0, 0.0
    pure_rl_curve = [0.0]
    post_lock_cut = "2026-11-04T02:05:00"
    post_lock_w, post_lock_l, post_lock_pnl = 0, 0, 0.0
    today_utc_date = time.strftime("%Y-%m-%d", time.gmtime())
    today_et_date = _now_et.strftime("%Y-%m-%d")
    today_cut = f"{today_utc_date}T00:00:00"
    v51_cut = "2026-11-01T01:22:00"
    today_w, today_l, today_pnl = 0, 0, 0.0
    v51_w, v51_l, v51_pnl = 0, 0, 0.0
    strat_stats = {}
    for g in grouped_closed:
        wp = round(float(g.get("net_pnl_usd", g.get("realized_pnl_usd", 0.0)) or 0.0), 2)
        rsn_g = str(g.get("close_reason") or "").upper()
        is_flat = abs(wp) <= 1e-6 and (bool(g.get("won")) or "MERGED" in rsn_g)
        is_w = (not is_flat) and (wp > 0 or bool(g.get("won")))
        is_l = (not is_flat) and (wp < -0.01)
        if is_w:
            wins_wallet += 1
        elif is_l:
            losses_wallet += 1
        sl = str(g.get("sleeve") or "UNKNOWN")
        is_pure_rl = _is_pure_riskless_sleeve(sl)
        if is_pure_rl:
            if is_flat:
                pure_rl_flat += 1
            elif is_w:
                pure_rl_w += 1
            elif is_l:
                pure_rl_l += 1
            pure_rl_pnl = round(pure_rl_pnl + wp, 2)
            if not is_flat:
                pure_rl_curve.append(pure_rl_pnl)
        rec_s = strat_stats.setdefault(sl, {"sleeve": sl, "open": 0, "flat_merges": 0, "today_w": 0, "today_l": 0, "today_pnl": 0.0, "v51_w": 0, "v51_l": 0, "v51_pnl": 0.0, "epoch_w": 0, "epoch_l": 0, "epoch_pnl": 0.0})
        if is_flat:
            rec_s["flat_merges"] += 1
        elif is_w:
            rec_s["epoch_w"] += 1
        elif is_l:
            rec_s["epoch_l"] += 1
        rec_s["epoch_pnl"] = round(rec_s["epoch_pnl"] + wp, 2)
        ts_e = str(g.get("entry_time_utc") or "")
        ts_x = str(g.get("exit_time_utc") or g.get("settled_at_utc") or ts_e)
        if ts_e >= post_lock_cut and is_pure_rl:
            if is_w:
                post_lock_w += 1
            elif is_l:
                post_lock_l += 1
            post_lock_pnl = round(post_lock_pnl + wp, 2)
        if ts_e >= today_cut:
            if is_w:
                today_w += 1
                rec_s["today_w"] += 1
            elif is_l:
                today_l += 1
                rec_s["today_l"] += 1
            today_pnl = round(today_pnl + wp, 2)
            rec_s["today_pnl"] = round(rec_s["today_pnl"] + wp, 2)
        if ts_e >= v51_cut:
            if is_w:
                v51_w += 1
                rec_s["v51_w"] += 1
            elif is_l:
                v51_l += 1
                rec_s["v51_l"] += 1
            v51_pnl = round(v51_pnl + wp, 2)
            rec_s["v51_pnl"] = round(rec_s["v51_pnl"] + wp, 2)

    act_list = []
    _mtm_bid_total = 0.0
    _tp_val_total = 0.0
    _ab_disk_p = pathlib.Path("/tmp/dominus_act_book_cache.json")
    _ab_disk = {}
    if (not _OFFLINE_PROBE) and _ab_disk_p.exists():
        try:
            _ab_disk = json.loads(_ab_disk_p.read_text(encoding="utf-8"))
        except Exception:
            _ab_disk = {}
    _ab_dirty = False
    for tid, p in (s.get("active_positions") or {}).items():
        sl_a = str(p.get("sleeve") or "UNKNOWN")
        strat_stats.setdefault(sl_a, {"sleeve": sl_a, "open": 0, "flat_merges": 0, "today_w": 0, "today_l": 0, "today_pnl": 0.0, "v51_w": 0, "v51_l": 0, "v51_pnl": 0.0, "epoch_w": 0, "epoch_l": 0, "epoch_pnl": 0.0})["open"] += 1
        _sh_a = float(p.get("remaining_shares", p.get("entry_shares", 0.0)) or 0.0)
        _not_a = round(float(p.get("remaining_cost_basis", p.get("notional_usd", 0.0)) or 0.0), 2)
        _tp_a = float(p.get("target_exit_price") or 0.0)
        _mid_a = str(p.get("market_id") or "")
        _tok_a = str(p.get("token_id") or "")
        _title_a = str(p.get("title") or p.get("question") or "")
        if _is_raw_stub_title(_title_a) and _mid_a.isdigit():
            _tm_a = (_tok_meta.get(f"mid:{_mid_a}") or _tok_meta.get(_tok_a) or {}) if '_tok_meta' in locals() else {}
            _cached_ta = str(_tm_a.get("title") or "").strip()
            if _cached_ta and not _is_raw_stub_title(_cached_ta):
                _title_a = _cached_ta
            elif (not _OFFLINE_PROBE) and (time.time() - float(_tm_a.get("neg_ts") or 0.0)) >= 3600.0:
                try:
                    _title_a = str(_http_get_json(f"https://gamma-api.polymarket.com/markets/{_mid_a}", timeout=1.4).get("question") or "").strip()
                except Exception:
                    _title_a = ""
                if '_tok_meta' in locals():
                    if _title_a and not _is_raw_stub_title(_title_a):
                        _tok_meta[f"mid:{_mid_a}"] = {"market_id": _mid_a, "title": _title_a, "neg_ts": 0.0}
                    else:
                        _tok_meta[f"mid:{_mid_a}"] = {"market_id": _mid_a, "neg_ts": time.time()}
                    _meta_dirty = True
        _bbid_raw = p.get("best_bid") if p.get("best_bid") is not None else p.get("last_observed_bid")
        _bask_raw = p.get("best_ask") if p.get("best_ask") is not None else p.get("last_observed_ask")
        _bbid_a = float(_bbid_raw) if _bbid_raw is not None else None
        _bask_a = float(_bask_raw) if _bask_raw is not None else None
        if _tok_a and not _OFFLINE_PROBE:
            _ab_cache = _p_state.setdefault("act_book_cache", {}) if _p_state is not None else _ab_disk
            _ab_ent = _ab_cache.get(_tok_a) or _ab_disk.get(_tok_a)
            if isinstance(_ab_ent, (list, tuple)) and len(_ab_ent) == 3 and (time.time() - float(_ab_ent[0])) <= 30.0:
                _bbid_a, _bask_a = _ab_ent[1], _ab_ent[2]
            else:
                try:
                    _bk_j = _http_get_json(f"https://clob.polymarket.com/book?token_id={_tok_a}", timeout=1.2)
                    _bds = [float(b["price"]) for b in (_bk_j.get("bids") or []) if float(b.get("size", 0) or 0) > 0]
                    _aks = [float(a["price"]) for a in (_bk_j.get("asks") or []) if float(a.get("size", 0) or 0) > 0]
                    if _bds:
                        _bbid_a = round(max(_bds), 4)
                    if _aks:
                        _bask_a = round(min(_aks), 4)
                    _ab_cache[_tok_a] = [time.time(), _bbid_a, _bask_a]
                    _ab_disk[_tok_a] = [time.time(), _bbid_a, _bask_a]
                    _ab_dirty = True
                except Exception:
                    pass
        _is_disp_pos_a = (
            bool(p.get("uma_disputed") or p.get("is_uma_disputed") or p.get("disputed") or p.get("is_legged_out_residual"))
            or str(p.get("box_type") or "").upper() == "MULTI_LEG_RESIDUAL"
            or "_UNWRESID_" in str(tid)
            or any("disput" in str(p.get(_ks) or "").strip().lower() for _ks in ("umaResolutionStatus", "uma_resolution_status", "uma_status", "resolution_status"))
        )
        # Disputed/unhedged-residual positions without a live bid mark at $0.00 liquidation (never frozen cost basis!)
        _mtm_b_u = round(_sh_a * _bbid_a, 2) if (_bbid_a is not None and _sh_a > 0) else (0.0 if _is_disp_pos_a else _not_a)
        _tp_v_u = round(_sh_a * _tp_a, 2) if (_tp_a > 0 and _sh_a > 0) else _mtm_b_u
        _mtm_bid_total += _mtm_b_u
        _tp_val_total += _tp_v_u
        act_list.append({
            "trade_id": tid,
            "market_id": _mid_a,
            "title": _title_a,
            "asset": p.get("asset"),
            "horizon": p.get("horizon"),
            "sleeve": sl_a,
            "side": p.get("target_token"),
            "shares": round(_sh_a, 2),
            "entry_px": p.get("entry_price"),
            "target_tp": p.get("target_exit_price"),
            "best_bid": _bbid_a,
            "best_ask": _bask_a,
            "notional_usd": _not_a,
            "mtm_bid_usd": _mtm_b_u,
            "tp_val_usd": _tp_v_u,
            "unreal_bid_pnl_usd": round(_mtm_b_u - _not_a, 2),
            "unreal_tp_pnl_usd": round(_tp_v_u - _not_a, 2),
            "status": p.get("exit_order_status") or p.get("status"),
        })
    recent_closed = []
    cum = round(_live_equity_usd - tot_pnl_wallet, 2)
    equity_curve = [cum]
    for c in closed_norm:
        cum = round(cum + float(c.get("net_pnl_usd", 0.0) or 0.0), 2)
        equity_curve.append(cum)
    _BENIGN_BOX_UNWINDS = {
        "PRE_SPLIT_PRE_EXPIRY_MERGED",
        "COMPLETE_SET_ONCHAIN_MERGED",
        "SYNTHETIC_COMPLEMENT_MERGED",
        "CROSS_CONDITION_COMPLEMENT_MERGED",
        "CTF_COMPLETE_SET_MERGED",
        "OVERROUND_SWEEP_REJECTED_MERGED_BACK",
    }
    for c in reversed(grouped_closed):
        _pnl_v = float(c.get("net_pnl_usd", c.get("realized_pnl_usd", 0.0)) or 0.0)
        _rsn_c = str(c.get("close_reason") or c.get("status") or "").strip().upper()
        if abs(_pnl_v) < 0.005 and (_rsn_c in _BENIGN_BOX_UNWINDS or "MERGED" in _rsn_c):
            continue
        wp = round(_pnl_v, 2)
        rp = round(float(c.get("_raw_pnl_usd", wp) or 0.0), 2)
        adj = bool(c.get("wallet_reconciled") or c.get("_fee_reconciled"))
        _raw_ts_c = c.get("exit_time_utc") or c.get("settled_at_utc") or c.get("closed_at_ts") or c.get("exit_ts") or c.get("entry_time_utc") or c.get("entry_ts") or ""
        _is_mleg = int(c.get("box_leg_count") or 1) > 1
        _ex_px_c = "BOX" if _is_mleg else (c.get("average_exit_price") or c.get("exit_price"))
        _en_px_c = round(float(c.get("notional_usd") or 0.0) / max(0.01, float(c.get("entry_shares") or 1.0)), 3) if _is_mleg else c.get("entry_price")
        _sl_c = str(c.get("sleeve") or "")
        _asset_lbl = f"{c.get('asset','')} BOX ({c.get('box_leg_count')}L)".strip() if _is_mleg else f"{c.get('asset','')} {c.get('horizon','')} {c.get('target_token','')}".strip()
        _tok_c = str(c.get("token_id") or "")
        _mid_c = str(c.get("market_id") or "")
        _q_c = str(c.get("title") or c.get("question") or "").strip()
        if _is_raw_stub_title(_q_c) and '_tok_meta' in locals():
            _tm_c = _tok_meta.get(_tok_c) or _tok_meta.get(f"mid:{_mid_c}") or {}
            _q_c = str(_tm_c.get("title") or "").strip()
            if (
                (not _OFFLINE_PROBE)
                and _is_raw_stub_title(_q_c)
                and _mid_c.isdigit()
                and (time.time() - float(_tm_c.get("neg_ts") or 0.0)) >= 3600.0
                and locals().get("_closed_g_fetches", 0) < 4
            ):
                _closed_g_fetches = locals().get("_closed_g_fetches", 0) + 1
                _resolved_c = False
                try:
                    _gj_c = _http_get_json(f"https://gamma-api.polymarket.com/markets/{_mid_c}", timeout=1.0)
                    if isinstance(_gj_c, dict) and _gj_c.get("question"):
                        _cand_qc = str(_gj_c["question"]).strip()
                        if _cand_qc and not _is_raw_stub_title(_cand_qc):
                            _q_c = _cand_qc
                            _tok_meta[f"mid:{_mid_c}"] = {"market_id": _mid_c, "title": _q_c, "neg_ts": 0.0}
                            if _tok_c:
                                _tok_meta[_tok_c] = {**_tm_c, "market_id": _mid_c, "title": _q_c, "neg_ts": 0.0}
                            _meta_dirty = True
                            _resolved_c = True
                except Exception:
                    pass
                if not _resolved_c:
                    _tok_meta[f"mid:{_mid_c}"] = {**_tm_c, "market_id": _mid_c, "neg_ts": time.time()}
                    if _tok_c:
                        _tok_meta[_tok_c] = {**_tm_c, "market_id": _mid_c, "neg_ts": time.time()}
                    _meta_dirty = True
        recent_closed.append({
            "time_utc": str(c.get("exit_time_utc") or c.get("settled_at_utc") or c.get("entry_time_utc") or "")[:19].replace("T", " "),
            "time_et": _fmt_et(_raw_ts_c, "%m-%d %H:%M:%S"),
            "unix_ts": float(c.get("exit_ts") or c.get("closed_at_ts") or c.get("entry_ts") or 0.0),
            "trade_id": c.get("trade_id"),
            "market_id": _mid_c,
            "title": "" if _is_raw_stub_title(_q_c) else _q_c,
            "side_tag": f"{c.get('target_token','')} ({'Maker' if 'maker' in str(c.get('horizon','')).lower() else ('Box' if _is_mleg else 'Lock')})".strip(),
            "asset": _asset_lbl or str(c.get("trade_id") or "")[:20],
            "sleeve": _sl_c,
            "is_active_riskless": _is_pure_riskless_sleeve(_sl_c),
            "entry_px": _en_px_c,
            "exit_px": _ex_px_c,
            "notional_usd": round(float(c.get("notional_usd", 0.0) or 0.0), 2),
            "fee_usd": round(float(c.get("fee_usd", 0.0) or 0.0), 2),
            "net_pnl_usd": wp,
            "raw_pnl_usd": rp,
            "fee_reconciled": adj,
            "reason": c.get("close_reason") or c.get("status"),
        })
        if len(recent_closed) >= 24:
            break
    if locals().get("_ab_dirty") and '_ab_disk_p' in locals():
        try:
            _ab_disk_p.write_text(json.dumps(_ab_disk), encoding="utf-8")
        except Exception:
            pass
    if locals().get("_meta_dirty") and '_tok_meta_cache_p' in locals():
        try:
            _tok_meta_cache_p.write_text(json.dumps(_tok_meta), encoding="utf-8")
        except Exception:
            pass
    _dcfg = strat_cfg.get("directional") or {}
    _bcfg = strat_cfg.get("riskless_boxes") or {}
    _ps_en = bool(_bcfg.get("enable_pre_split_overround_gun", False))
    _min_dir_eq_d = float(_dcfg.get("min_live_equity_for_unhedged_directional_usd", 0.0) or 0.0)
    _riskless_only_d = bool(_dcfg.get("riskless_only_mode", False))
    if _riskless_only_d:
        _s1h_desc = "PAUSED — 100% Riskless-Only Lock (Shadow Only; Zero Unhedged Exposure)"
        _s15_desc = "PAUSED — 100% Riskless-Only Lock (Shadow Only; Zero Unhedged Exposure)"
    elif _min_dir_eq_d > 0.0 and _live_equity_usd < _min_dir_eq_d:
        _s1h_desc = f"SHADOW-ONLY (<${_min_dir_eq_d:.0f} Rebuild Gate — 100% Capital in 0-Loss Arb & Carry)"
        _s15_desc = f"SHADOW-ONLY (<${_min_dir_eq_d:.0f} Rebuild Gate — 100% Capital in 0-Loss Arb & Carry)"
    else:
        _s1h_desc = "Live 1h Crypto Directional"
        _s15_desc = "Live 15m Crypto Directional"
    _b1_pool_pct = int(
        round(
            100.0
            * float(
                _bcfg.get("seed_zero_loss_focus_bond1_pool_pct")
                or _bcfg.get("bond1_max_pool_fraction", 0.80)
                or 0.80
            )
        )
    )
    _b1_mkt_cap = int(round(float(_bcfg.get("bond1_per_market_cap_usd_seed") or _bcfg.get("bond1_max_notional_per_market_usd", 45.0) or 45.0)))
    _strict_pure_rl_d = bool(_bcfg.get("strict_pure_riskless_mode", False))
    _rw_unlock_eq_d = float(_bcfg.get("reward_dynamic_unlock_equity_usd", 125.0) or 125.0)
    _PURE_RL_BLOCKED_D = {
        "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        "S2_EXACT_TWAP_LOCK",
        "CM_B3_PYTH_BARRIER_BOX",
        "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
    }

    def _fmt_rl_desc(sl_id: str, live_desc: str, paused_reason: str = "Fee/Legging Quarantine (Shadow Only; Zero Live Exposure)") -> str:
        su = sl_id.strip().upper()
        if su in _PAUSED_RB_SET:
            return f"PAUSED — {paused_reason}"
        if _strict_pure_rl_d and su in _PURE_RL_BLOCKED_D:
            return "PAUSED — Strict Pure-Riskless Lock (Shadow Only; Zero Live Exposure)"
        if su == "MKR_REWARD_LOCKED_CARRY" and (not bool(_bcfg.get("enable_reward_locked_carry_live_bridge", False)) or _live_equity_usd < _rw_unlock_eq_d):
            return f"GATED (<${_rw_unlock_eq_d:.0f} Equity Gate — Zero Capital Squatting)"
        return live_desc

    live_strat_meta = [
        ("BOND1_UMA_RESOLUTION_CARRY", _fmt_rl_desc("BOND1_UMA_RESOLUTION_CARRY", f"LIVE ACTIVE — 0%-Fee UMA Resolution Carry ({_b1_pool_pct}% Pool Cap, <=${_b1_mkt_cap}/mkt, Preemptable)")),
        ("D1_SAME_ORACLE_DOMINANCE_BOX", _fmt_rl_desc("D1_SAME_ORACLE_DOMINANCE_BOX", f"LIVE ACTIVE — 32/32 Same-Oracle Crypto Dominance Box (<=${float(_bcfg.get('d1_max_box_cost_net', 0.985)):.3f} net)")),
        ("CM_B3_PYTH_BARRIER_BOX", _fmt_rl_desc("CM_B3_PYTH_BARRIER_BOX", f"LIVE ACTIVE — 0%-Fee Pyth Commodity Barrier Box (<=${float(_bcfg.get('cm_b3_max_walk_cap', 0.982)):.3f})", "Pyth Barrier Basis Quarantine (Shadow Only; Zero Live Exposure)")),
        ("S2_RTDS_EXACT_TWAP_INTEGRATOR", _fmt_rl_desc("S2_RTDS_EXACT_TWAP_INTEGRATOR", "LIVE ACTIVE — PolyBolt V2 1Hz Chainlink Final-45s Exact TWAP Lock", "Oracle TWAP Basis Quarantine (Shadow Only; Zero Live Exposure)")),
        ("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", _fmt_rl_desc("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "LIVE ACTIVE — 0%-Fee Post-Clinch Maker Sweeper (p>=99.9%, <=$22, Preemptable)")),
        ("W_PRUNE1_DEAD_NO_BOND", _fmt_rl_desc("W_PRUNE1_DEAD_NO_BOND", "LIVE ACTIVE — 0%-Fee Station-Verified Dead-NO Weather Sweeper")),
        ("MKR_REWARD_LOCKED_CARRY", _fmt_rl_desc("MKR_REWARD_LOCKED_CARRY", "LIVE ACTIVE — 100% Dead-NO Weather & Monotonic Counter Top-Queue Carry (<=$12)", "Reward Carry Slot Quarantine (Zero Capital Squatting)")),
        ("C1_BINARY_COMPLETE_SET", _fmt_rl_desc("C1_BINARY_COMPLETE_SET", "LIVE ACTIVE — Binary YES/NO Complete-Set & Inventory-Backed Completion")),
        ("NR_M1_DEAD_SEED_OVERROUND", _fmt_rl_desc("NR_M1_DEAD_SEED_OVERROUND", "LIVE ACTIVE — NegRisk Dead-Seed Overround & Slate Sweep")),
        ("NR2_CONVERT_NO_SUBSET_ARB", _fmt_rl_desc("NR2_CONVERT_NO_SUBSET_ARB", "LIVE ACTIVE — NegRisk NR2/NR3 Atomic Convert & Synthetic All-YES Overround")),
        ("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX", _fmt_rl_desc("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX", "LIVE ACTIVE — 12/12 Deadline & Scalar Dominance Box (<=24h Fast-Recycle)")),
        ("COND1_MACRO_PARTITION_BOX", _fmt_rl_desc("COND1_MACRO_PARTITION_BOX", "LIVE ACTIVE — 9/9 Macro Partition Dominance Box (<=24h, <=$0.985 net)")),
        ("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", _fmt_rl_desc("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", "LIVE ACTIVE — 0%-Fee Cross-Market Implication Box")),
        ("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK", _fmt_rl_desc("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK", "LIVE ACTIVE — 0%-Fee In-Game Milestone Irreversible Lock")),
        (
            "PRE_SPLIT_OVERROUND_MACHINE_GUN",
            "LIVE ACTIVE — $12 BTC 15m/5m Atomic Complete-Set Overround Sweeper + 75s Merge"
            if _ps_en
            else "PAUSED — 7% Crypto Fee & Split-Latency Quarantine (Zero Capital Lockup)",
        ),
        (
            "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
            "PAUSED — Fee-Sports Legging Guard (Shadow Only; Zero Live Exposure)"
            if "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX" in _PAUSED_RB_SET
            else "Live Fee-Exact Soccer 3-Way Synthetic Box",
        ),
        (
            "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
            "PAUSED — Sports Corridor Legging Guard (Shadow Only; Zero Live Exposure)"
            if "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX" in _PAUSED_RB_SET
            else "Live Sports Corridor Box",
        ),
        ("SLEEVE_1_CORE_302", _s1h_desc),
        ("SLEEVE_1_SUBHOURLY_15M", _s15_desc),
    ]
    live_strategies = []
    seen_ls = set()
    for sl_k, desc_s in live_strat_meta:
        seen_ls.add(sl_k)
        st_d = strat_stats.get(sl_k) or {"sleeve": sl_k, "open": 0, "flat_merges": 0, "today_w": 0, "today_l": 0, "today_pnl": 0.0, "v51_w": 0, "v51_l": 0, "v51_pnl": 0.0, "epoch_w": 0, "epoch_l": 0, "epoch_pnl": 0.0}
        _act_rl = (
            _is_pure_riskless_sleeve(sl_k)
            and (not (_riskless_only_d and sl_k.upper() in _UNHEDGED_DIR_SLEEVES))
            and (not (_strict_pure_rl_d and sl_k.upper() in _PURE_RL_BLOCKED_D))
            and (sl_k != "PRE_SPLIT_OVERROUND_MACHINE_GUN" or _ps_en)
            and (sl_k != "MKR_REWARD_LOCKED_CARRY" or (bool(_bcfg.get("enable_reward_locked_carry_live_bridge", False)) and _live_equity_usd >= _rw_unlock_eq_d))
        )
        live_strategies.append({**st_d, "desc": desc_s, "is_active_riskless": _act_rl})
    for sl_k, st_d in strat_stats.items():
        if sl_k not in seen_ls:
            _is_p = str(sl_k).strip().upper() in _PAUSED_RB_SET or (_riskless_only_d and str(sl_k).strip().upper() in _UNHEDGED_DIR_SLEEVES)
            _extra_desc = (
                "PAUSED — Fee-Sports Legging Guard (Shadow Only; Zero Live Exposure)"
                if str(sl_k).strip().upper() in _PAUSED_RB_SET
                else ("PAUSED — 100% Riskless-Only Lock" if _is_p else "LIVE ACTIVE — Graduated Riskless Harvester Sleeve")
            )
            live_strategies.append({**st_d, "desc": _extra_desc, "is_active_riskless": not _is_p})

    _rk_st = s.get("risk_state") or {}
    _pure_tot = pure_rl_w + pure_rl_l
    _lock_start_eq = 60.92
    _net_deposits_usd = 0.0
    _cf_rows = []
    _cf_path = root / "config/polymarket_external_cashflows.json"
    if _cf_path.exists():
        try:
            _cf_raw = json.loads(_cf_path.read_text(encoding="utf-8"))
            if isinstance(_cf_raw, dict):
                _lock_start_eq = round(float(_cf_raw.get("riskless_lock_start_equity_usd") or 60.92), 2)
                for _c in (_cf_raw.get("cashflows") or []):
                    if isinstance(_c, dict) and float(_c.get("amount_usd") or 0.0) > 0:
                        _cf_rows.append(_c)
                        _sgn = -1.0 if str(_c.get("type") or "DEPOSIT").strip().upper() in ("WITHDRAWAL", "WITHDRAW", "OUTFLOW") else 1.0
                        _net_deposits_usd += _sgn * abs(float(_c.get("amount_usd") or 0.0))
        except Exception:
            pass
    _net_deposits_usd = round(_net_deposits_usd, 2)
    _contributed_basis_usd = round(_lock_start_eq + _net_deposits_usd, 2)
    _post_lock_cash_delta = round(_live_equity_usd - _contributed_basis_usd, 2)

    # Explicit 3-NAV Triad, D-001 Disputed KMIA Non-Interference Gate & Finland VM Breakeven Hurdle
    _KMIA_MIDS = {"6707503", "6707502"}
    _disputed_uma_cost_usd = 0.0
    _disputed_positions_count = 0
    _kmia_disputed_count = 0
    _kmia_disputed_shares = 0.0
    _kmia_frozen_cost_usd = 0.0
    _kmia_mtm_bid_usd = 0.0
    _kmia_exit_or_unwind_orders = 0
    for _tid_k, _pk in (s.get("active_positions") or {}).items():
        if not isinstance(_pk, dict):
            continue
        _mid_k = str(_pk.get("market_id") or "")
        _is_kmia = _mid_k in _KMIA_MIDS or "KMIA" in str(_tid_k).upper()
        _is_disp = (
            bool(_pk.get("uma_disputed") or _pk.get("is_uma_disputed") or _pk.get("disputed") or _pk.get("is_legged_out_residual"))
            or str(_pk.get("box_type") or "").upper() == "MULTI_LEG_RESIDUAL"
            or "_UNWRESID_" in str(_tid_k)
            or any("disput" in str(_pk.get(_ks) or "").strip().lower() for _ks in ("umaResolutionStatus", "uma_resolution_status", "uma_status", "resolution_status"))
        )
        _cost_k = float(_pk.get("remaining_cost_basis", _pk.get("notional_usd", 0.0)) or 0.0)
        _sh_k = float(_pk.get("remaining_shares", _pk.get("entry_shares", 0.0)) or 0.0)
        if _is_disp:
            _disputed_positions_count += 1
            _disputed_uma_cost_usd = round(_disputed_uma_cost_usd + _cost_k, 2)
        if _is_kmia:
            _kmia_disputed_count += 1
            _kmia_disputed_shares = round(_kmia_disputed_shares + _sh_k, 2)
            _kmia_frozen_cost_usd = round(_kmia_frozen_cost_usd + _cost_k, 2)
            if _pk.get("exit_order_id") or _pk.get("unwind_order_id"):
                _kmia_exit_or_unwind_orders += 1
    for _ap_row in act_list:
        if str(_ap_row.get("market_id") or "") in _KMIA_MIDS or "KMIA" in str(_ap_row.get("trade_id") or "").upper():
            _kmia_mtm_bid_usd = round(_kmia_mtm_bid_usd + float(_ap_row.get("mtm_bid_usd") or 0.0), 2)
    for _ro_k in resting_orders:
        if str(_ro_k.get("market_id") or "") in _KMIA_MIDS:
            _kmia_exit_or_unwind_orders += 1
    _kmia_untouched_ok = (_kmia_exit_or_unwind_orders == 0)

    _mtm_bid_nav_usd = round(_wallet_cash + _mtm_bid_total, 2)
    _vm_monthly_usd = 24.67
    _vm_daily_usd = round(_vm_monthly_usd / 30.0, 4)  # $0.8223/day
    _vm_hourly_usd = _vm_monthly_usd / (30.0 * 24.0)  # $0.034264/hr
    _vm_hurdle_bps_hr = round((_vm_hourly_usd / max(1.0, _guaranteed_redeem_equity_usd)) * 10000.0, 2)
    _vm_hurdle_bps_day = round(_vm_hurdle_bps_hr * 24.0, 1)
    _live_quote_weighted_bps_hr = 0.0
    if _inflight_intents_usd > 0 and resting_orders:
        _live_quote_weighted_bps_hr = round(
            sum(float(o.get("notional_usd") or 0.0) * float(o.get("est_bps_per_hr") or 0.0) for o in resting_orders)
            / max(0.01, _inflight_intents_usd),
            2,
        )
    _nav_triad = {
        "reconciled_floor_nav_usd": _guaranteed_redeem_equity_usd,
        "mtm_liquidation_nav_usd": _mtm_bid_nav_usd,
        "persisted_book_equity_usd": _live_equity_usd,
        "sizing_nav_basis": "reconciled_floor_nav_usd",
        "book_equity_sizing_forbidden": _disputed_uma_cost_usd > 0.0,
        "disputed_positions_count": _disputed_positions_count,
        "disputed_uma_cost_usd": _disputed_uma_cost_usd,
        "kmia_disputed_count": _kmia_disputed_count,
        "kmia_disputed_shares": _kmia_disputed_shares,
        "kmia_frozen_cost_usd": _kmia_frozen_cost_usd,
        "kmia_mtm_bid_usd": _kmia_mtm_bid_usd,
        "kmia_untouched_ok": _kmia_untouched_ok,
        "kmia_exit_or_unwind_orders": _kmia_exit_or_unwind_orders,
        "vm_monthly_cost_usd": _vm_monthly_usd,
        "vm_daily_cost_usd": _vm_daily_usd,
        "vm_breakeven_bps_per_hr": _vm_hurdle_bps_hr,
        "vm_breakeven_bps_per_day": _vm_hurdle_bps_day,
        "live_quoting_bps_per_hr": _live_quote_weighted_bps_hr,
        "portfolio_quoting_bps_per_hr": round(_live_quote_weighted_bps_hr * (_inflight_intents_usd / max(1.0, _guaranteed_redeem_equity_usd)), 2),
    }

    # Ingest Harvester FT_* / Sleeve Real-Trading Funnel (supports Wave-3 ft_live_funnel + live_riskless_funnel.ft_bridge_stats + IPC tail)
    _raw_rl_fn = s.get("live_riskless_funnel") or {}
    _raw_ft_st = (
        s.get("ft_live_funnel")
        or (_raw_rl_fn.get("ft_bridge_stats") if isinstance(_raw_rl_fn, dict) else None)
        or s.get("ft_bridge_stats")
        or s.get("candidate_funnel")
        or {}
    )
    _ipc_by_slv = {}
    _ipc_ft_cnt = 0
    for _ic in _recent_ipc_cands:
        if not isinstance(_ic, dict):
            continue
        _islv = str(_ic.get("sleeve_source") or _ic.get("sleeve") or _ic.get("strategy_id") or "UNKNOWN")
        _ipc_by_slv[_islv] = _ipc_by_slv.get(_islv, 0) + 1
        if _islv.upper().startswith("FT_") or str(_ic.get("box_id") or "").upper().startswith("FT_") or str(_ic.get("candidate_source") or "").lower() == "full_throttle":
            _ipc_ft_cnt += 1
    _by_slv_fn = dict(_raw_ft_st.get("by_sleeve") or s.get("sleeve_funnel") or {})
    _ft_slv_exec_sum = 0
    _ft_slv_rej_sum = 0
    for _fsk, _fsv in _by_slv_fn.items():
        if isinstance(_fsv, dict) and (str(_fsk).upper().startswith("FT_") or int(_fsv.get("ft_bridge", 0) or 0) > 0):
            _ft_slv_exec_sum += int(_fsv.get("executed", int(_fsv.get("taker_executed", 0) or 0) + int(_fsv.get("maker_filled", 0) or 0)) or 0)
            _ft_slv_rej_sum += int(_fsv.get("rejected", 0) or 0)
    _harvester_funnel = {
        "updated_at_utc": str(_raw_ft_st.get("updated_at_utc") or ""),
        "candidates_received_total": int(_raw_ft_st.get("candidates_received", _raw_ft_st.get("received", len(_recent_ipc_cands))) or 0),
        "ft_received": int(_raw_ft_st.get("ft_bridge_received", _raw_ft_st.get("ft_received", _raw_ft_st.get("received", _ipc_ft_cnt))) or 0),
        "ft_executed": int(_raw_ft_st.get("ft_executed", _raw_ft_st.get("executed", _ft_slv_exec_sum)) or 0),
        "ft_rejected": int(_raw_ft_st.get("ft_rejected", _raw_ft_st.get("rejected", _ft_slv_rej_sum or _raw_ft_st.get("rejected_total", 0))) or 0),
        "clinch_watchlist_registered": int(_raw_ft_st.get("clinch_watchlist_registered", 0) or 0),
        "taker_evaluated": int(_raw_ft_st.get("taker_evaluated", 0) or 0),
        "taker_executed": int(_raw_ft_st.get("taker_executed", 0) or 0),
        "maker_spawned": int(_raw_ft_st.get("maker_spawned", 0) or 0),
        "maker_posted": int(_raw_ft_st.get("maker_posted", 0) or 0),
        "maker_filled": int(_raw_ft_st.get("maker_filled", 0) or 0),
        "rejected_total": int(_raw_ft_st.get("rejected_total", _raw_ft_st.get("rejected", 0)) or 0),
        "ft_rejection_reasons": dict(_raw_ft_st.get("ft_rejection_reasons") or _raw_ft_st.get("reject_reasons") or _raw_ft_st.get("skipped_by_reason") or {}),
        "per_sleeve_funnel": _by_slv_fn,
        "recent_candidates": list((_raw_ft_st.get("recent_candidates") or [])[:15]),
        "ipc_tail_total": len(_recent_ipc_cands),
        "ipc_tail_by_sleeve": _ipc_by_slv,
        "resting_maker_slots": max(len(resting_orders), int(_raw_ft_st.get("resting_maker_slots", 0) or 0)),
        "fifo_rank1_slots": max(int(_raw_rl_fn.get("fifo_rank1_slots", 0) or 0), _fifo_rank1_live_cnt),
        "outbid_repegs": int(_raw_rl_fn.get("outbid_repegs", 0) or 0),
        "uma_early_recycles": int(_raw_rl_fn.get("uma_early_recycles", 0) or 0),
        "taker_skip_counts": dict(_raw_ft_st.get("taker_skip_counts") or {}),
        "maker_skip_counts": dict(_raw_ft_st.get("maker_skip_counts") or {}),
    }

    _active_undisputed_open_usd = round(max(0.0, _active_book_usd - _disputed_uma_cost_usd), 2)
    _reconciled_undisputed_equity_usd = round(_wallet_cash + _active_undisputed_open_usd, 2)

    out["polymarket_live"] = {
        "bankroll_usd": round(_wallet_cash, 2),
        "riskless_lock_start_usd": _lock_start_eq,
        "net_deposits_post_lock_usd": _net_deposits_usd,
        "contributed_capital_basis_usd": _contributed_basis_usd,
        "post_lock_cash_delta_usd": _post_lock_cash_delta,
        "post_lock_cash_pct": round(100.0 * _post_lock_cash_delta / max(0.01, _contributed_basis_usd), 1),
        "open_book_usd": _active_book_usd,
        "active_undisputed_open_usd": _active_undisputed_open_usd,
        "frozen_disputed_open_usd": round(_disputed_uma_cost_usd, 2),
        "reconciled_undisputed_equity_usd": _reconciled_undisputed_equity_usd,
        "free_cash_usd": _free_cash_usd,
        "quoting_cash_usd": round(_inflight_intents_usd, 2),
        "quoting_utilization_pct": _quoting_util_pct,
        "resting_redeem_edge_usd": round(_resting_redeem_edge_usd, 2),
        "wallet_cash_usd": round(_wallet_cash, 2),
        "state_bankroll_usd": round(_state_cash, 2),
        "onchain_verified": _onchain_cash is not None,
        "clob_orders_verified": _clob_orders_ok,
        "orphan_orders_count": _orphan_orders_cnt,
        "equity_usd": _live_equity_usd,
        "mtm_bid_equity_usd": _mtm_bid_nav_usd,
        "tp_target_equity_usd": round(_wallet_cash + _tp_val_total, 2),
        "guaranteed_redemption_equity_usd": _guaranteed_redeem_equity_usd,
        "disputed_uma_cost_usd": _disputed_uma_cost_usd,
        "nav_triad": _nav_triad,
        "harvester_funnel": _harvester_funnel,
        "hwm_usd": round(float(s.get("high_water_mark_equity", 0.0) or 0.0), 2),
        "tier": s.get("current_equity_tier") or s.get("equity_tier"),
        "max_concurrent_positions": int(s.get("max_total_portfolio_slots") or s.get("max_concurrent_positions") or 99),
        "unlimited_slots": bool(s.get("unlimited_slots", False)) or int(s.get("max_concurrent_positions") or 0) >= 50 or int(s.get("max_total_portfolio_slots") or 0) >= 50,
        "max_exposure_usd": round(float(s.get("max_exposure", 0.0) or 0.0), 2),
        "risk_halt": bool(s.get("risk_halt", False) or _rk_st.get("halted", False)),
        "halt_reasons": s.get("global_halt_reasons") or ([_rk_st.get("halt_reason")] if _rk_st.get("halt_reason") else []),
        "daily_realized_loss_usd": round(float(_rk_st.get("daily_realized_loss", 0.0) or 0.0), 2),
        "pure_riskless_wins": pure_rl_w,
        "pure_riskless_losses": pure_rl_l,
        "pure_riskless_flat_merges": pure_rl_flat,
        "pure_riskless_wr_pct": round(100.0 * pure_rl_w / _pure_tot, 1) if _pure_tot > 0 else 100.0,
        "pure_riskless_pnl_usd": pure_rl_pnl,
        "pure_riskless_curve": pure_rl_curve,
        "post_lock_wins": post_lock_w,
        "post_lock_losses": post_lock_l,
        "post_lock_pnl_usd": post_lock_pnl,
        "today_utc_date": today_utc_date,
        "today_et_date": today_et_date,
        "today_wins": today_w,
        "today_losses": today_l,
        "today_net_pnl_usd": today_pnl,
        "v51_wins": v51_w,
        "v51_losses": v51_l,
        "v51_net_pnl_usd": v51_pnl,
        "epoch_closed_count": len(grouped_closed),
        "epoch_wins": wins_wallet,
        "epoch_losses": losses_wallet,
        "epoch_wins_raw": wins_raw,
        "epoch_net_pnl_usd": tot_pnl_wallet,
        "epoch_net_pnl_raw_usd": tot_pnl_raw,
        "epoch_fees_usd": tot_fees,
        "trades_this_hour": s.get("trades_this_hour", 0),
        "equity_curve": equity_curve,
        "active_positions": act_list,
        "resting_orders": resting_orders,
        "live_strategies": live_strategies,
        "recent_closed": recent_closed,
    }
    _act_sb_saved = dict(s.get("active_positions") or {})
    for _k_early in ("s", "closed_all", "closed", "closed_norm"):
        globals().pop(_k_early, None)
    gc.collect()
else:
    _act_sb_saved = {}
    out["polymarket_live"] = {}

# Recent notable live log lines (bounded 256 KB tail seek across live_harvester_stdout.log & live_harvester.log)
_cand_lps = [
    p_lp for p_lp in (
        root / "data/polymarket/live_harvester_stdout.log",
        root / "data/polymarket/live_harvester.log",
        root / "logs/polymarket_live_harvester.log",
    ) if p_lp.exists()
]
log_path = max(_cand_lps, key=lambda p_lp: p_lp.stat().st_mtime) if _cand_lps else (root / "data/polymarket/live_harvester.log")
log_events = []
maker_post_cnt = 0
_tail_lines = []
_log_taker_skips = {}
_log_maker_skips = {}
if log_path.exists():
    try:
        _pat_core = re.compile(r"\[STARTUP\]|\[SHUTDOWN\]|\[RECONCILIATION\] Exchange state reconciled|\[CLOSED\]|\[LIVE FILL\]|\[LIVE PHASE 3A|\[CEILING -> PHASE 3A|\[AUTO-REDEEMER\]|\[RECONCILIATION\] Live collateral|\[D1 BOX|\[D1 LIVE|\[D1 FRESH BOOK|\[ATOMIC OVERROUND|\[MAKER ANCHOR|\[SINGLE-LEG LOCK|\[SINGLE-LEG MAKER LOCK|\[BOND1|\[MAKER TTL|GRAD8 AUTO|\[CONFIG_HOT_RELOAD\]|\[EV_SUPERVISOR|MACHINE_GUN|FT_")
        _pat_mkr = re.compile(r"\[LIVE MAKER ENTRY POSTED\]|\[LIVE MAKER ENTRY ASYNC\]")
        with open(log_path, "rb") as _lf:
            _sz = log_path.stat().st_size
            _off = max(0, _sz - 262144)
            _lf.seek(_off)
            _tail_lines = _lf.read().decode("utf-8", errors="replace").splitlines()
        if _off > 0 and _tail_lines:
            _tail_lines = _tail_lines[1:]
        for _sk_ln in _tail_lines[-1200:]:
            for _tk_k in ("WORST_LIMIT_COST_ABOVE_CAP", "BOX_TOO_EXPENSIVE_L1", "LEG_BELOW_1USD_MIN", "ANTI_BOX_COMPLEMENT_UNVERIFIED", "STALE_IPC_CANDIDATE"):
                if _tk_k in _sk_ln:
                    _log_taker_skips[_tk_k] = _log_taker_skips.get(_tk_k, 0) + 1
            for _mk_k in ("INSUFFICIENT_MAKER_COLLATERAL", "BOND1_OUTBID_REPEGGED", "BOND1_MAKER_OUTBID_RELEASED", "BOND1_MAKER_EXPIRED_UNFILLED", "MAKER TTL QUIET"):
                if _mk_k in _sk_ln:
                    _nk = _mk_k.replace(" ", "_")
                    _log_maker_skips[_nk] = _log_maker_skips.get(_nk, 0) + 1
        _last_boot_idx = -1
        for _ti, _tln in enumerate(_tail_lines):
            if "[RECONCILIATION] Exchange state reconciled" in _tln or "[STARTUP] PolymarketLiveHarvester" in _tln:
                _last_boot_idx = _ti
        _core_hits = []
        for _ti, _tln in enumerate(_tail_lines):
            if not _pat_core.search(_tln):
                continue
            if _last_boot_idx >= 0 and _ti < _last_boot_idx and "'NoneType' object is not callable" in _tln:
                continue
            _core_hits.append(_tln)
        _mkr_hits = [x for x in _tail_lines if _pat_mkr.search(x)]
        maker_post_cnt = len(_mkr_hits)
        # Collapse consecutive identical [ERROR] payloads so a burst does not push out surrounding events
        _dedup_core = []
        for _cln in _core_hits:
            _msg_key = _cln[29:] if _cln.startswith("[20") and len(_cln) > 29 else _cln
            if _dedup_core and "[ERROR]" in _cln and _dedup_core[-1][1] == _msg_key:
                _dedup_core[-1] = (_cln, _msg_key, _dedup_core[-1][2] + 1)
            else:
                _dedup_core.append((_cln, _msg_key, 1))
        _core_Comp = [
            (f"{_raw_ln} (x{_cnt})" if _cnt > 1 else _raw_ln)
            for _raw_ln, _, _cnt in _dedup_core
        ]
        _merged = sorted(set(_core_Comp[-10:] + _mkr_hits[-5:]), key=lambda ln: ln[:23])
        _re_log_utc = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3} UTC\]\s*")
        for ln in _merged[-12:]:
            _m_lu = _re_log_utc.match(ln)
            if _m_lu:
                _et_p = _fmt_et(_m_lu.group(1), "%m-%d %H:%M:%S %Z")
                _rest = ln[_m_lu.end():]
                log_events.append(f"[{_et_p}] {_rest[:155]}")
            else:
                log_events.append(ln[-160:])
    except Exception:
        pass
if out.get("polymarket_live"):
    out["polymarket_live"]["live_maker_posts_tail"] = maker_post_cnt
    _hf_ref = out["polymarket_live"].get("harvester_funnel")
    if isinstance(_hf_ref, dict):
        if not _hf_ref.get("taker_skip_counts") and _log_taker_skips:
            _hf_ref["taker_skip_counts"] = _log_taker_skips
        if not _hf_ref.get("maker_skip_counts") and _log_maker_skips:
            _hf_ref["maker_skip_counts"] = _log_maker_skips
out["live_log_events"] = list(reversed(log_events))

# 3b. Shock & Order Attempt Forensics (Speed vs Gate Attribution + Historical Backfill; 30s /tmp cache on live host)
_sf_cache_p = pathlib.Path("/tmp/dominus_shock_forensics_cache.json")
_sf_cached_ok = False
if not _OFFLINE_PROBE and _sf_cache_p.exists():
    try:
        if (time.time() - _sf_cache_p.stat().st_mtime) <= 30.0:
            _sf_cj = json.loads(_sf_cache_p.read_text(encoding="utf-8"))
            if isinstance(_sf_cj, dict) and "summary" in _sf_cj and "rows" in _sf_cj:
                out["shock_forensics"] = _sf_cj
                _sf_cached_ok = True
    except Exception:
        pass
if not _OFFLINE_PROBE and not _sf_cached_ok:
    try:
        _sf_sub_py = (
            "import json, pathlib, statistics, sys, time\n"
            f"root = pathlib.Path({str(root)!r})\n"
            "sys.path.insert(0, str(root))\n"
            "from src.polymarket_research.latency_trace import classify_shock_attempt as _cls\n"
            "rows, seen = [], set()\n"
            "p = root / 'data/polymarket/shock_attempt_forensics.jsonl'\n"
            "if p.exists():\n"
            "    with open(p, 'rb') as f:\n"
            "        sz = p.stat().st_size; off = max(0, sz - 262144); f.seek(off)\n"
            "        lns = f.read().decode('utf-8', errors='replace').splitlines()[1 if off > 0 else 0:]\n"
            "    for ln in lns[-140:]:\n"
            "        if ln.strip():\n"
            "            try:\n"
            "                ri = json.loads(ln)\n"
            "                r = _cls(ri) if ('speed_verdict' not in ri or str(ri.get('path_type') or '').upper() == 'PRE_EVAL') else dict(ri)\n"
            "                if 'speed_verdict' in r:\n"
            "                    k = (str(r.get('trade_id') or r.get('shock_id') or str(r.get('ts_utc') or '')[:19]), str(r.get('path_type') or ''))\n"
            "                    if k not in seen: seen.add(k); rows.append(r)\n"
            "            except Exception: pass\n"
            "rows.sort(key=lambda x: float(x.get('unix_ts') or 0.0), reverse=True)\n"
            "ipcs = [float(r['ipc_ms']) for r in rows if r.get('ipc_ms') is not None and 0 <= float(r['ipc_ms']) < 10000]\n"
            "sgns = [float(r['sign_ms']) for r in rows if r.get('sign_ms') is not None and 0 <= float(r['sign_ms']) < 5000]\n"
            "htps = [float(r['http_ms']) for r in rows if r.get('http_ms') is not None and 0 <= float(r['http_ms']) < 15000]\n"
            "e2es = [float(r['e2e_ms']) for r in rows if r.get('e2e_ms') is not None and 0 <= float(r['e2e_ms']) < 20000]\n"
            "sm = {'total_tracked': len(rows), 'attempts': sum(1 for r in rows if r.get('is_order_attempt')), 'filled': sum(1 for r in rows if r.get('speed_verdict')=='FILLED'), 'speed_misses': sum(1 for r in rows if r.get('is_speed_miss')), 'flight_kills': sum(1 for r in rows if r.get('speed_verdict')=='TOO_SLOW_FLIGHT'), 'pre_eval_repriced': sum(1 for r in rows if r.get('speed_verdict')=='TOO_SLOW_PRE_EVAL'), 'maker_left_behind': sum(1 for r in rows if r.get('speed_verdict')=='LEFT_BEHIND_MAKER'), 'feed_lags': sum(1 for r in rows if r.get('speed_verdict')=='TOO_SLOW_FEED_LAG'), 'shield_saves': sum(1 for r in rows if r.get('speed_verdict')=='SHIELD_SAVED'), 'maker_quiet': sum(1 for r in rows if r.get('speed_verdict')=='MAKER_TTL_QUIET'), 'clob_rejects': sum(1 for r in rows if r.get('speed_verdict')=='CLOB_REJECT'), 'already_priced': sum(1 for r in rows if r.get('speed_verdict')=='ALREADY_PRICED_IN'), 'settled_99c': sum(1 for r in rows if r.get('badge')=='SETTLED 99c+'), 'alpha_vetoes': sum(1 for r in rows if r.get('speed_verdict')=='ALPHA_GATE_VETO'), 'med_ipc_ms': round(statistics.median(ipcs),2) if ipcs else None, 'med_sign_ms': round(statistics.median(sgns),3) if sgns else None, 'med_http_ms': round(statistics.median(htps),1) if htps else None, 'med_e2e_ms': round(statistics.median(e2es),1) if e2es else None, 'last_shock_utc': str(rows[0].get('ts_utc') or '') if rows else '', 'last_shock_age_s': round(max(0.0, time.time()-float(rows[0].get('unix_ts') or time.time())),1) if rows else None}\n"
            "pathlib.Path('/tmp/dominus_shock_forensics_cache.json').write_text(json.dumps({'summary': sm, 'rows': rows[:56]}), encoding='utf-8')\n"
        )
        subprocess.run([sys.executable, "-c", _sf_sub_py], check=True, timeout=4, capture_output=True)
        _sf_cj = json.loads(_sf_cache_p.read_text(encoding="utf-8"))
        for _r_sf in (_sf_cj.get("rows") or []):
            _r_sf["ts_et"] = _fmt_et(_r_sf.get("unix_ts") or _r_sf.get("ts_utc"), "%m-%d %H:%M:%S")
        out["shock_forensics"] = _sf_cj
        _sf_cached_ok = True
    except Exception:
        pass

if not _sf_cached_ok:
    try:
        from src.polymarket_research.latency_trace import classify_shock_attempt as _cls_sa
    except Exception:
        _cls_sa = None

    _sf_rows = []
    _sf_seen = set()

    def _add_sf(rec_in):
        if not isinstance(rec_in, dict):
            return
        r = _cls_sa(rec_in) if (_cls_sa is not None and ("speed_verdict" not in rec_in or str(rec_in.get("path_type") or "").upper() == "PRE_EVAL")) else dict(rec_in)
        if "speed_verdict" not in r:
            return
        tid = str(r.get("trade_id") or "")
        sid = str(r.get("shock_id") or "")
        pt = str(r.get("path_type") or "")
        dedup_k = (tid, pt) if tid else ((sid, pt) if sid else (str(r.get("ts_utc") or "")[:19], str(r.get("asset") or ""), str(r.get("side") or ""), pt, str(r.get("gate_code") or "")))
        if dedup_k in _sf_seen:
            return
        _sf_seen.add(dedup_k)
        _sf_rows.append(r)

    sf_path = root / "data/polymarket/shock_attempt_forensics.jsonl"
    if sf_path.exists():
        try:
            with open(sf_path, "rb") as _sff:
                _sfsz = sf_path.stat().st_size
                _sfoff = max(0, _sfsz - 393216)
                _sff.seek(_sfoff)
                _sflines = _sff.read().decode("utf-8", errors="replace").splitlines()
            if _sfoff > 0 and _sflines:
                _sflines = _sflines[1:]
            for _ln in _sflines[-160:]:
                if _ln.strip():
                    try:
                        _add_sf(json.loads(_ln))
                    except Exception:
                        pass
        except Exception:
            pass

    if _cls_sa is not None and sum(1 for _x in _sf_rows if _x.get("is_order_attempt")) < 16:
        _lo_by_tid = {}
        lo_path = root / "data/polymarket/live_orders.jsonl"
        if lo_path.exists():
            try:
                with open(lo_path, "rb") as _lof:
                    _losz = lo_path.stat().st_size
                    _lof.seek(max(0, _losz - 98304))
                    _lolines = _lof.read().decode("utf-8", errors="replace").splitlines()[1 if _losz > 98304 else 0:]
                for _ln in _lolines[-80:]:
                    try:
                        _oj = json.loads(_ln)
                        if _oj.get("side") == "BUY" and _oj.get("trade_id"):
                            _lo_by_tid[str(_oj["trade_id"])] = _oj
                    except Exception:
                        pass
            except Exception:
                pass
        lt_path = root / "data/polymarket/latency_trace.jsonl"
        if lt_path.exists():
            try:
                with open(lt_path, "rb") as _ltf:
                    _ltsz = lt_path.stat().st_size
                    _ltf.seek(max(0, _ltsz - 131072))
                    _ltlines = _ltf.read().decode("utf-8", errors="replace").splitlines()[1 if _ltsz > 131072 else 0:]
                for _ln in _ltlines[-18:]:
                    try:
                        _tj = json.loads(_ln)
                        _tid = str(_tj.get("trade_id") or "")
                        _oj = _lo_by_tid.get(_tid) or {}
                        _wn = float(_tj.get("created_wall_ns") or 0.0)
                        _uts = (_wn / 1e9) if _wn > 1e15 else float(_tj.get("src_t0_unix") or time.time())
                        _outc = str(_tj.get("outcome") or "").lower()
                        _rst = str(_tj.get("resp_status") or "").lower()
                        _stg = "FILLED_TAKER" if (_outc == "posted" and (_rst in ("matched", "filled") or _oj.get("success") is True)) else ("CLOB_HTTP_400_REJECTION" if "400" in _outc else "FAK_KILLED")
                        _m_m = re.search(r"_(\d+)_(\d+)_(UP|DOWN|YES|NO)$", _tid)
                        _sd = str(_oj.get("target_token") or (_m_m.group(3) if _m_m else "")).upper()
                        _slv = str(_tj.get("sleeve") or "")
                        _hz = "15m" if ("15M" in _slv.upper() or "SUBHOURLY" in _slv.upper()) else ("1h" if _slv else "")
                        _add_sf({
                            "unix_ts": _uts,
                            "shock_id": _tj.get("shock_id") or "",
                            "trade_id": _tid,
                            "asset": _tj.get("asset") or "",
                            "horizon": _hz,
                            "side": _sd,
                            "sleeve": _slv,
                            "path_type": "TAKER_FOK",
                            "stage_outcome": _stg,
                            "target_px": _tj.get("target_limit_px") or _oj.get("price"),
                            "fill_px": _oj.get("price") if _stg == "FILLED_TAKER" else None,
                            "notional_usd": _tj.get("effective_notional_usd") or _oj.get("notional_usd"),
                            "ipc_ms": _tj.get("trigger_to_consume_wall_ms"),
                            "ws_book_age_ms": _tj.get("ws_book_age_ms"),
                            "book_age_ms": _tj.get("ws_book_age_ms"),
                            "gate_ms": _tj.get("qualify_ms"),
                            "sign_ms": _tj.get("sign_ms"),
                            "http_ms": _tj.get("clob_http_post_ms"),
                            "presign_cache_hit": _tj.get("presign_cache_hit", False),
                            "gate_detail": _tj.get("resp_error") or _oj.get("error") or "",
                        })
                    except Exception:
                        pass
            except Exception:
                pass
        if _tail_lines:
            try:
                _pending_p3a = {}
                for _ln in _tail_lines[-2500:]:
                    _ts_m = re.match(r"^\[?(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}),(\d{3})", _ln)
                    if not _ts_m:
                        continue
                    _iso = f"{_ts_m.group(1)}T{_ts_m.group(2)}Z"
                    try:
                        _u = float(calendar.timegm(time.strptime(f"{_ts_m.group(1)} {_ts_m.group(2)}", "%Y-%m-%d %H:%M:%S"))) + int(_ts_m.group(3)) / 1000.0
                    except Exception:
                        _u = time.time()
                    if "[CEILING -> PHASE 3A MAKER RESCUE]" in _ln:
                        _m = re.search(r"\] (LIVE_\S+): ask=\$([0-9.]+) > \+EV ceiling=\$([0-9.]+)", _ln)
                        if _m:
                            _pending_p3a[_m.group(1)] = {"eval_ask": float(_m.group(2)), "cap_px": float(_m.group(3))}
                    elif "[LIVE MAKER ENTRY ASYNC]" in _ln:
                        _m = re.search(r"OID=(\S+) \| BUY ([0-9.]+) sh @ \$([0-9.]+) \| post=([0-9.]+)ms sign=([0-9.]+)ms", _ln)
                        if _m:
                            _pending_p3a[_m.group(1)] = {"sh": float(_m.group(2)), "px": float(_m.group(3)), "http_ms": float(_m.group(4)), "sign_ms": float(_m.group(5))}
                    elif "[LIVE PHASE 3A EXPIRED CLEAN]" in _ln or "[LIVE PHASE 3A ADVERSE SHIELD]" in _ln:
                        _m = re.search(r"\] (LIVE_(\d+)_\d+_(UP|DOWN)): (\S+) canceled \(([0-9.]+)s\)", _ln)
                        if _m:
                            _tid = _m.group(1)
                            _oid = _m.group(4)
                            _meta = _pending_p3a.get(_tid, {})
                            _ometa = _pending_p3a.get(_oid, {})
                            _px_m = _ometa.get("px") or _meta.get("cap_px", 0.76)
                            _add_sf({
                                "unix_ts": _u, "ts_utc": _iso, "trade_id": _tid, "market_id": _m.group(2),
                                "asset": "SOL" if _m.group(2) == "6405955" else ("BTC" if "BTC" in _ln else "CRYPTO"),
                                "horizon": "1h", "side": _m.group(3), "path_type": "MAKER_P3A",
                                "target_px": _px_m, "eval_ask": _meta.get("eval_ask"),
                                "notional_usd": round(_ometa["sh"] * _px_m, 2) if _ometa.get("sh") else None,
                                "sign_ms": _ometa.get("sign_ms"), "http_ms": _ometa.get("http_ms"),
                                "ttl_ms": float(_m.group(5)) * 1000.0,
                                "stage_outcome": "SHIELD_ADVERSE_TTL" if "ADVERSE SHIELD" in _ln else "MAKER_TTL_EXPIRED",
                            })
                    elif "[LIVE MAKER ENTRY POSTED]" in _ln:
                        _m = re.search(r"OID=(\S+) \| BUY ([0-9.]+) shares @ \$([0-9.]+)", _ln)
                        if _m and float(_m.group(3)) >= 0.95:
                            _oid = _m.group(1)
                            _sh_b = float(_m.group(2))
                            _px_b = float(_m.group(3))
                            _add_sf({
                                "unix_ts": _u, "ts_utc": _iso, "trade_id": f"BOND1_{_oid[:10]}",
                                "asset": "BOND1", "horizon": "carry", "side": "YES", "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                                "path_type": "MAKER_BOX", "target_px": _px_b, "notional_usd": round(_sh_b * _px_b, 2),
                                "ttl_ms": 12000.0, "stage_outcome": "BOND1_MAKER_EXPIRED_UNFILLED",
                            })
                    elif "[SINGLE-LEG MAKER LOCK]" in _ln and ("expired unfilled" in _ln or "adverse mid-TTL" in _ln):
                        _m = re.search(r"\] (\S+) (\S+) (YES|NO|UP|DOWN) Maker @ \$([0-9.]+)", _ln)
                        if _m:
                            _add_sf({
                                "unix_ts": _u, "ts_utc": _iso, "trade_id": f"BOX_{_m.group(2)}_{int(_u)}",
                                "asset": "BOND1", "horizon": "box", "side": _m.group(3), "sleeve": _m.group(1),
                                "path_type": "MAKER_BOX", "target_px": float(_m.group(4)), "ttl_ms": 12000.0,
                                "stage_outcome": "BOND1_MAKER_ADVERSE_CANCELLED" if "adverse" in _ln else "BOND1_MAKER_EXPIRED_UNFILLED",
                            })
                    elif "[LIVE MAKER ENTRY] Post failed" in _ln and "status_code=400" in _ln:
                        _em = re.search(r"error_message=(\{[^\}]+\}|.+)$", _ln)
                        _pxm = re.search(r"@ \$([0-9.]+)", _ln)
                        _add_sf({
                            "unix_ts": _u, "ts_utc": _iso, "trade_id": f"MKR400_{int(_u*10)}",
                            "asset": "BOND1", "horizon": "box", "side": "BUY", "path_type": "MAKER_BOX",
                            "target_px": float(_pxm.group(1)) if _pxm else None,
                            "stage_outcome": "BOND1_MAKER_POST_FAILED",
                            "gate_detail": (_em.group(1) if _em else _ln[-110:]),
                        })
            except Exception:
                pass

    _sf_rows.sort(key=lambda x: float(x.get("unix_ts") or 0.0), reverse=True)
    _ipcs = [float(r["ipc_ms"]) for r in _sf_rows if r.get("ipc_ms") is not None and 0.0 <= float(r["ipc_ms"]) < 10000.0]
    _sgns = [float(r["sign_ms"]) for r in _sf_rows if r.get("sign_ms") is not None and 0.0 <= float(r["sign_ms"]) < 5000.0]
    _htps = [float(r["http_ms"]) for r in _sf_rows if r.get("http_ms") is not None and 0.0 <= float(r["http_ms"]) < 15000.0]
    _e2es = [float(r["e2e_ms"]) for r in _sf_rows if r.get("e2e_ms") is not None and 0.0 <= float(r["e2e_ms"]) < 20000.0]
    _sf_summary = {
        "total_tracked": len(_sf_rows),
        "attempts": sum(1 for r in _sf_rows if r.get("is_order_attempt")),
        "filled": sum(1 for r in _sf_rows if r.get("speed_verdict") == "FILLED"),
        "speed_misses": sum(1 for r in _sf_rows if r.get("is_speed_miss")),
        "flight_kills": sum(1 for r in _sf_rows if r.get("speed_verdict") == "TOO_SLOW_FLIGHT"),
        "pre_eval_repriced": sum(1 for r in _sf_rows if r.get("speed_verdict") == "TOO_SLOW_PRE_EVAL"),
        "maker_left_behind": sum(1 for r in _sf_rows if r.get("speed_verdict") == "LEFT_BEHIND_MAKER"),
        "feed_lags": sum(1 for r in _sf_rows if r.get("speed_verdict") == "TOO_SLOW_FEED_LAG"),
        "shield_saves": sum(1 for r in _sf_rows if r.get("speed_verdict") == "SHIELD_SAVED"),
        "maker_quiet": sum(1 for r in _sf_rows if r.get("speed_verdict") == "MAKER_TTL_QUIET"),
        "clob_rejects": sum(1 for r in _sf_rows if r.get("speed_verdict") == "CLOB_REJECT"),
        "already_priced": sum(1 for r in _sf_rows if r.get("speed_verdict") == "ALREADY_PRICED_IN"),
        "settled_99c": sum(1 for r in _sf_rows if r.get("badge") == "SETTLED 99c+"),
        "alpha_vetoes": sum(1 for r in _sf_rows if r.get("speed_verdict") == "ALPHA_GATE_VETO"),
        "med_ipc_ms": round(statistics.median(_ipcs), 2) if _ipcs else None,
        "med_sign_ms": round(statistics.median(_sgns), 3) if _sgns else None,
        "med_http_ms": round(statistics.median(_htps), 1) if _htps else None,
        "med_e2e_ms": round(statistics.median(_e2es), 1) if _e2es else None,
        "last_shock_utc": str(_sf_rows[0].get("ts_utc") or "") if _sf_rows else "",
        "last_shock_age_s": round(max(0.0, time.time() - float(_sf_rows[0].get("unix_ts") or time.time())), 1) if _sf_rows else None,
    }
    _noise_codes = {"1H_TTE_WINDOW", "15M_TTE_WINDOW", "TTE_OUT_OF_RANGE", "CUSHION_TOO_SMALL"}
    _prio_rows = [r for r in _sf_rows if r.get("is_order_attempt") or r.get("is_speed_miss") or r.get("speed_verdict") in ("SHIELD_SAVED", "CLOB_REJECT")]
    _prio_ids = {id(r) for r in _prio_rows[:24]}
    _other_meaningful = [r for r in _sf_rows if r.get("meaningful") and r.get("gate_code") not in _noise_codes and id(r) not in _prio_ids]
    _noise_rows = [r for r in _sf_rows if (not r.get("meaningful") or r.get("gate_code") in _noise_codes) and id(r) not in _prio_ids]
    _picked_sf = _prio_rows[:24] + _other_meaningful[:22] + _noise_rows[:10]
    _picked_sf.sort(key=lambda x: float(x.get("unix_ts") or 0.0), reverse=True)
    for _r_sf in _picked_sf[:56]:
        _r_sf["ts_et"] = _fmt_et(_r_sf.get("unix_ts") or _r_sf.get("ts_utc"), "%m-%d %H:%M:%S")
    out["shock_forensics"] = {
        "summary": _sf_summary,
        "rows": _picked_sf[:56],
    }
    if not _OFFLINE_PROBE:
        try:
            _sf_cache_p.write_text(json.dumps(out["shock_forensics"]), encoding="utf-8")
        except Exception:
            pass

# 4. Alpha-124 Riskless Frontier v1/v2/v3/v5.2, _grad8 Auto-Promotion & Machine-Gun Auto-Discovery
a_path = root / "data/alpha124/alpha124_shadow_state.json"
mir_path = root / "data/polymarket/alpha124_shadow_state.json"
_a_raw_doc = {}
_mir_raw_doc = {}
if a_path.exists():
    try:
        _a_raw_doc = json.loads(a_path.read_text(encoding="utf-8"))
    except Exception:
        _a_raw_doc = {}
if mir_path.exists():
    try:
        _mir_raw_doc = json.loads(mir_path.read_text(encoding="utf-8"))
    except Exception:
        _mir_raw_doc = {}
mir_by_slv = dict(_mir_raw_doc.get("by_sleeve") or {})
_a_mtime = a_path.stat().st_mtime if a_path.exists() else 0.0
_mir_mtime = mir_path.stat().st_mtime if mir_path.exists() else 0.0
_best_a124_mtime = max(_a_mtime, _mir_mtime)
if _a_raw_doc or _mir_raw_doc:
    # Merge primary (newer mtime) over secondary so both v5.2 catalog_counts & legacy open_positions survive
    by_slv = {**(_a_raw_doc.get("by_sleeve") or {}), **(_mir_raw_doc.get("by_sleeve") or {})}
    if _mir_mtime >= _a_mtime and _mir_raw_doc:
        a = _a_raw_doc
        a.update(_mir_raw_doc)
    else:
        a = _mir_raw_doc
        a.update(_a_raw_doc)
    if isinstance(a.get("by_sleeve"), dict):
        by_slv.update(a["by_sleeve"])
    _a_raw_doc = None
    _mir_raw_doc = None
    raw_open_p = a.get("open_positions") or []
    open_p = list(raw_open_p.values()) if isinstance(raw_open_p, dict) else list(raw_open_p)
    raw_rc_p = a.get("recent_closed_positions") or []
    rc_p = list(raw_rc_p) if isinstance(raw_rc_p, list) else []
    pend_d1_mkr = len(a.get("pending_maker_anchors") or {})
    pend_zf_mkr = len(a.get("pending_zero_fee_maker_anchors") or {})
    raw_pmo = a.get("pending_maker_orders") or []
    pmo_list = list(raw_pmo.values()) if isinstance(raw_pmo, dict) else list(raw_pmo)
    pend_by_slv = {}
    for q in pmo_list:
        if isinstance(q, dict) and q.get("sleeve"):
            pend_by_slv[str(q["sleeve"])] = pend_by_slv.get(str(q["sleeve"]), 0) + 1
    spots = {k: round(float(v), 4 if float(v) < 10 else 2) for k, v in (a.get("spots") or {}).items() if k in ("BTC", "ETH", "SOL", "XRP", "XAU")}
    frontier_v3_grad8 = {
        "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
        "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
        "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
        "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
        "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
        "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
        "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
        "SOC2_EXACT_SCORE_2D_LATTICE",
        "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
        "SUM1_FRECHET_SUM_TRIANGLES",
        "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
    }
    live_bridged_sleeves = {
        "D1_SAME_ORACLE_DOMINANCE_BOX",
        "D1_QUIET_BOOK_BOX",
        "D1_MAKER_ANCHOR_BOX",
        "ZF_INTRADAY_MAKER_BOX",
        "CM_B3_PYTH_BARRIER_BOX",
        "COND1_MACRO_PARTITION_BOX",
        "FED1_CENTRAL_BANK_LP_BOX",
        "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
        "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
        "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
        "SP1_NBA_ZERO_FEE_BOX",
        "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
        "BOND1_UMA_RESOLUTION_CARRY",
        "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
        "MKR_REWARD_LOCKED_CARRY",
        "NR2_CONVERT_NO_SUBSET_ARB",
        "PRE_SPLIT_OVERROUND_MACHINE_GUN",
    }
    watch_sleeves = [
        "BOND1_UMA_RESOLUTION_CARRY",
        "MKR_REWARD_LOCKED_CARRY",
        "PRE_SPLIT_OVERROUND_MACHINE_GUN",
        "CM_B3_PYTH_BARRIER_BOX",
        "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
        "COND1_MACRO_PARTITION_BOX",
        "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
        "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
        "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
        "NR2_CONVERT_NO_SUBSET_ARB",
        "SP1_NBA_ZERO_FEE_BOX",
        "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
        "FED1_CENTRAL_BANK_LP_BOX",
        "D1_SAME_ORACLE_DOMINANCE_BOX",
        "D1_QUIET_BOOK_BOX",
        "D1_MAKER_ANCHOR_BOX",
        "ZF_INTRADAY_MAKER_BOX",
        "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
        "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
        "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
        "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
        "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
        "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
        "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
        "SOC2_EXACT_SCORE_2D_LATTICE",
        "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
        "SUM1_FRECHET_SUM_TRIANGLES",
        "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "NR0_ZERO_FEE_SLATE_ARB",
        "NR_CONV_NO_BASKET_ARB",
        "N1_NEGRISK_CROSS_BOX",
        "U1_DAILY_UPDOWN_LOCK",
        "W1_SOLAR_PEAK_LOCK",
        "XV_SUBSET_NO_BOX",
        "TAIL_BOUNDARY_001_ARB",
        "BOND3_MULTISOURCE_DEAD_SPLIT",
        "XV_FX_INVARIANT_CAD_USD_BOX",
        "DERIBIT_VERTICAL_SUPER_REP",
        "XV_HALFTIME_FREEZE_CORRIDOR",
        "HEDGED_PRESPLIT_CONV_GUN",
        "YIELD_STACKED_CARRY_BOX",
    ]
    v6_expansion_sleeves = {
        "XV_SUBSET_NO_BOX",
        "TAIL_BOUNDARY_001_ARB",
        "BOND3_MULTISOURCE_DEAD_SPLIT",
        "XV_FX_INVARIANT_CAD_USD_BOX",
        "DERIBIT_VERTICAL_SUPER_REP",
        "XV_HALFTIME_FREEZE_CORRIDOR",
        "HEDGED_PRESPLIT_CONV_GUN",
        "YIELD_STACKED_CARRY_BOX",
    }
    by_slv = dict(by_slv)
    try:
        _v6_xv_pre_p = root / "data/cross_venue_shadow/v6_expansion_telemetry.json"
        if _v6_xv_pre_p.exists():
            _v6_xv_pre = json.loads(_v6_xv_pre_p.read_text(encoding="utf-8"))
            if isinstance(_v6_xv_pre, dict):
                for _vk, _vv in (_v6_xv_pre.get("by_sleeve") or {}).items():
                    if _vk in v6_expansion_sleeves and isinstance(_vv, dict):
                        _cur_v = dict(by_slv.get(_vk) or {})
                        _tot_cl = int(_cur_v.get("closed", 0) or 0) + int(_vv.get("closed", 0) or 0)
                        _tot_wn = int(_cur_v.get("wins", 0) or 0) + int(_vv.get("wins", 0) or 0)
                        _tot_ls = int(_cur_v.get("losses", 0) or 0) + int(_vv.get("losses", 0) or 0)
                        by_slv[_vk] = {
                            **_cur_v,
                            "open": int(_cur_v.get("open", 0) or 0) + int(_vv.get("open", 0) or 0),
                            "closed": _tot_cl,
                            "wins": _tot_wn,
                            "losses": _tot_ls,
                            "win_rate_pct": round(100.0 * _tot_wn / _tot_cl, 2) if _tot_cl else 0.0,
                            "realized_pnl_t1000_usd": round(
                                float(_cur_v.get("realized_pnl_t1000_usd", 0.0) or 0.0)
                                + float(_vv.get("realized_pnl_t1000_usd", 0.0) or 0.0),
                                2,
                            ),
                            "grad8_live_promoted": False,
                        }
                for _xv_op in (_v6_xv_pre.get("open_positions") or []):
                    if isinstance(_xv_op, dict):
                        open_p.append(_xv_op)
        _v6_a124_pre_p = root / "data/polymarket/v6_expansion_alpha124_telemetry.json"
        if _v6_a124_pre_p.exists():
            _v6_a124_pre = json.loads(_v6_a124_pre_p.read_text(encoding="utf-8"))
            if isinstance(_v6_a124_pre, dict):
                _pmk_cnt = int(_v6_a124_pre.get("pending_maker_asks", 0) or 0)
                if _pmk_cnt > 0:
                    pend_by_slv["HEDGED_PRESPLIT_CONV_GUN"] = pend_by_slv.get("HEDGED_PRESPLIT_CONV_GUN", 0) + _pmk_cnt
    except Exception:
        pass
    machine_gun_sleeves = []
    for _mg_pat in ("*machine_gun*.json", "*mg_riskless*.json"):
        for _mg_fp in sorted((root / "data/polymarket").glob(_mg_pat)):
            try:
                _mg_j = json.loads(_mg_fp.read_text(encoding="utf-8"))
                if isinstance(_mg_j, dict):
                    _mg_sub = _mg_j.get("by_sleeve") or _mg_j.get("per_strategy") or {}
                    if isinstance(_mg_sub, dict) and _mg_sub:
                        for _mk, _mv in _mg_sub.items():
                            if isinstance(_mv, dict):
                                by_slv.setdefault(_mk, _mv)
                                if _mk not in machine_gun_sleeves:
                                    machine_gun_sleeves.append(_mk)
                    elif "wins" in _mg_j or "closed" in _mg_j:
                        _mk = str(_mg_j.get("sleeve") or _mg_fp.stem.upper())
                        by_slv.setdefault(_mk, _mg_j)
                        if _mk not in machine_gun_sleeves:
                            machine_gun_sleeves.append(_mk)
            except Exception:
                pass
    _watch_set = set(watch_sleeves)
    for _extra_slv, _extra_m in sorted(by_slv.items()):
        if not isinstance(_extra_m, dict):
            continue
        _up_slv = str(_extra_slv).upper()
        if "MACHINE_GUN" in _up_slv or _up_slv.startswith("MG_"):
            if _extra_slv not in machine_gun_sleeves:
                machine_gun_sleeves.append(_extra_slv)
        if _extra_slv not in _watch_set and (("MACHINE_GUN" in _up_slv or _up_slv.startswith("MG_") or int(_extra_m.get("wins", 0) or 0) >= 4) and int(_extra_m.get("losses", 0) or 0) == 0):
            watch_sleeves.append(_extra_slv)
            _watch_set.add(_extra_slv)
    slv_rows = []
    promoted_cnt = 0
    near_grad8_cnt = 0
    zero_loss_t1000_pnl = 0.0
    zero_loss_wins = 0
    for _all_sk, _all_sm in by_slv.items():
        if isinstance(_all_sm, dict):
            _aw = int(_all_sm.get("wins", 0) or 0)
            _al = int(_all_sm.get("losses", 0) or 0)
            _apnl = float(_all_sm.get("realized_pnl_t1000_usd", 0.0) or 0.0)
            if _aw > 0 and _al == 0 and _apnl >= 0.0 and str(_all_sk).upper() not in _PAUSED_RB_SET:
                zero_loss_t1000_pnl = round(zero_loss_t1000_pnl + _apnl, 2)
                zero_loss_wins += _aw
    for slv in watch_sleeves:
        m = by_slv.get(slv) or {}
        mm = mir_by_slv.get(slv) or {}
        c_n = int(m.get("closed", 0) or 0)
        w_n = int(m.get("wins", 0) or 0)
        l_n = int(m.get("losses", 0) or 0)
        o_n = int(m.get("open", 0) or 0)
        pend_n = (
            pend_d1_mkr if slv == "D1_MAKER_ANCHOR_BOX"
            else pend_zf_mkr if slv == "ZF_INTRADAY_MAKER_BOX"
            else pend_by_slv.get(slv, 0)
        )
        _is_paused_rb = slv.upper() in _PAUSED_RB_SET or (
            slv.upper() == "PRE_SPLIT_OVERROUND_MACHINE_GUN"
            and not bool((strat_cfg.get("riskless_boxes") or {}).get("enable_pre_split_overround_gun", False))
        )
        _is_mg = ("MACHINE_GUN" in slv.upper()) or slv.upper().startswith("MG_") or (slv in machine_gun_sleeves)
        is_v3 = slv in frontier_v3_grad8 or _is_mg
        is_v6 = slv in v6_expansion_sleeves
        g8_prom = (
            (not _is_paused_rb)
            and (not is_v6)
            and bool(
                mm.get("grad8_live_promoted")
                or m.get("grad8_live_promoted")
                or (c_n >= 8 and l_n == 0 and float(m.get("realized_pnl_t1000_usd", 0.0) or 0.0) > 0)
            )
        )
        if g8_prom:
            promoted_cnt += 1
        elif (not _is_paused_rb) and 4 <= w_n < 8 and l_n == 0:
            near_grad8_cnt += 1
        is_bridged = (not _is_paused_rb) and (slv in live_bridged_sleeves) and (l_n == 0 or g8_prom)
        is_live_slv = bool(g8_prom or is_bridged)
        if _is_paused_rb:
            grad_lbl = f"PAUSED ({w_n}/{l_n})"
            tier_tag = "PAUSED"
        elif g8_prom:
            grad_lbl = f"LIVE 8/8 ({w_n}/0)"
            tier_tag = "PROMOTED"
        elif _is_mg:
            grad_lbl = f"MG G8 ({min(w_n, 8)}/8)" if l_n == 0 else f"REVOKED ({w_n}/{l_n})"
            tier_tag = "MACHINE_GUN"
        elif is_v6:
            grad_lbl = (f"V6 READY ({w_n}/0)" if w_n >= 8 else f"V6 G8 ({min(w_n, 8)}/8)") if l_n == 0 else f"REVOKED ({w_n}/{l_n})"
            tier_tag = "V6_RISKLESS"
        elif is_v3:
            grad_lbl = f"V3 G8 ({min(w_n, 8)}/8)" if l_n == 0 else f"REVOKED ({w_n}/{l_n})"
            tier_tag = "V3_AUTO_G8"
        elif is_bridged:
            grad_lbl = f"BRIDGE ({min(c_n, 8)}/8)"
            tier_tag = "BRIDGE"
        else:
            grad_lbl = f"SHDW ({min(c_n, 8)}/8)"
            tier_tag = "SHADOW"
        slv_rows.append({
            "sleeve": slv,
            "open": o_n,
            "pending_quotes": pend_n,
            "closed": c_n,
            "wins": w_n,
            "losses": l_n,
            "grad8_pct": min(100, int(round(100.0 * min(w_n, 8) / 8.0))) if l_n == 0 else 0,
            "t1000_pnl_usd": round(float(m.get("realized_pnl_t1000_usd", 0.0) or 0.0), 2),
            "grad8_progress": grad_lbl,
            "tier_tag": tier_tag,
            "is_live": is_live_slv,
            "is_machine_gun": _is_mg,
            "is_v6": is_v6,
            "is_paused": _is_paused_rb,
        })
    # Sort sleeves so PROMOTED & high-win zero-loss sleeves surface at the top
    slv_rows.sort(key=lambda r: (
        0 if r["tier_tag"] == "PROMOTED" else (1 if r["tier_tag"] == "MACHINE_GUN" else (2 if r["is_live"] else (4 if r["is_paused"] else 3))),
        -(r["wins"] if r["losses"] == 0 else -100),
        -r["t1000_pnl_usd"],
    ))
    now_u = time.time()
    open_boxes = []
    for p in open_p[:18]:
        cts = float(p.get("close_ts") or p.get("expiry_ts") or 0.0)
        if cts > now_u:
            rem_s = cts - now_u
            tte_lbl = f"{rem_s/86400.0:.1f}d" if rem_s >= 86400.0 else (f"{rem_s/3600.0:.1f}h" if rem_s >= 3600.0 else f"{int(rem_s//60)}m")
        elif cts > 0:
            tte_lbl = "settle"
        else:
            tte_lbl = "-"
        open_boxes.append({
            "sleeve": p.get("sleeve"),
            "title": str(p.get("title") or "")[:54],
            "eff_px": p.get("entry_eff_px_t1000"),
            "last_bid": p.get("last_bid"),
            "tte": tte_lbl,
        })
    recent_shadow_closed = []
    for p in reversed(rc_p[-12:]):
        tpnl = p.get("legging_adjusted_tier_pnls_usd") or p.get("tier_pnls_usd") or {}
        recent_shadow_closed.append({
            "closed_utc": str(p.get("closed_utc") or p.get("entry_utc") or "")[:19].replace("T", " "),
            "closed_et": _fmt_et(p.get("closed_utc") or p.get("entry_utc"), "%m-%d %H:%M"),
            "sleeve": p.get("sleeve"),
            "title": str(p.get("title") or "")[:48],
            "eff_px": p.get("entry_eff_px_t1000"),
            "payout_px": p.get("net_payout_per_share"),
            "won": bool(p.get("won")),
            "status": p.get("status"),
            "t100_pnl": round(float(tpnl.get("T100", 0.0) or 0.0), 2),
            "t1000_pnl": round(float(tpnl.get("T1000", 0.0) or 0.0), 2),
        })
    # Extract v5.2 Alpha-124 live catalog & IPC bridge telemetry (state keys + 32 KB stdout log fallback)
    _cat_c = dict(a.get("catalog_counts") or a.get("v52_catalog") or {})
    _mm_c = dict(a.get("markets_monitored") or {})
    _a124_log_kv = {}
    for _alp in (
        root / "data/polymarket/alpha124_shadow_stdout.log",
        root / "data/alpha124/alpha124_shadow.log",
        root / "logs/polymarket_alpha124_shadow.log",
    ):
        if _alp.exists():
            try:
                with open(_alp, "rb") as _af:
                    _asz = _alp.stat().st_size
                    _af.seek(max(0, _asz - 32768))
                    _alines = _af.read().decode("utf-8", errors="replace").splitlines()
                for _aln in reversed(_alines):
                    if "UMA=" in _aln or "NRC=" in _aln or "MakerPend=" in _aln:
                        for _mk_m in re.finditer(r"\b(UMA|NRC|CAL1|W|B|PythH|SP3|SOC1|TEN1|API1|FOMC|S2|MakerPend|TopOpps|WS|Binaries)=(\d+)", _aln):
                            _a124_log_kv.setdefault(_mk_m.group(1), int(_mk_m.group(2)))
                        if _a124_log_kv:
                            break
            except Exception:
                pass
            if _a124_log_kv:
                break
    _bin_cnt = int(
        _cat_c.get("zerofee_binaries")
        or _cat_c.get("binaries_total")
        or _cat_c.get("binaries")
        or _a124_log_kv.get("Binaries")
        or (
            int(_mm_c.get("weather_city_events", 0) or _a124_log_kv.get("W", 0))
            + int(_mm_c.get("barrier_hit_rungs", 0) or _a124_log_kv.get("B", 0))
            + int(_mm_c.get("pyth_barrier_rungs", 0) or _a124_log_kv.get("PythH", 0))
            + int(_mm_c.get("uma_proposed_markets", 0) or _a124_log_kv.get("UMA", 0))
        )
        or 0
    )
    _uma_cnt = int(_cat_c.get("uma_proposed") or _cat_c.get("uma_proposed_markets") or _mm_c.get("uma_proposed_markets") or _a124_log_kv.get("UMA") or 0)
    _uma_hot_cnt = int(_cat_c.get("uma_hot_bonds") or 0)
    _nrc_cnt = int(_cat_c.get("negrisk_convert_slates") or _cat_c.get("negrisk_slates") or _mm_c.get("negrisk_zero_fee_slates") or _a124_log_kv.get("NRC") or 0)
    _cal1_cnt = int(_cat_c.get("cal1_ladders") or _mm_c.get("multistrike_ladders") or _a124_log_kv.get("CAL1") or 0)
    _ws_cnt = int(_cat_c.get("ws_subscribed_tokens") or _cat_c.get("ws_tokens") or a.get("ws_subscribed_tokens") or _a124_log_kv.get("WS") or 0)
    _ws_shards = int(_cat_c.get("ws_shards_active") or 0)
    _dorm_pin = int(_cat_c.get("dormant_ws_pinned_tokens") or 0)
    _lbt = dict(a.get("live_bridge_telemetry") or {})
    _mkr_pend_tot = int(_cat_c.get("maker_pending") or _lbt.get("pending_maker_orders_count") or (pend_d1_mkr + pend_zf_mkr + len(pmo_list)) or _a124_log_kv.get("MakerPend") or 0)
    _ipc_slv_map = {}
    for _rc_i in _recent_ipc_cands:
        if isinstance(_rc_i, dict):
            _s_i = str(_rc_i.get("sleeve_source") or _rc_i.get("sleeve") or "UNKNOWN")
            _ipc_slv_map[_s_i] = _ipc_slv_map.get(_s_i, 0) + 1
    if isinstance(_lbt.get("emitted_by_sleeve"), dict):
        for _lsk, _lsv in _lbt["emitted_by_sleeve"].items():
            _ipc_slv_map[str(_lsk)] = max(int(_ipc_slv_map.get(str(_lsk), 0)), int(_lsv or 0))
    _best_a124_ts = max(float(a.get("updated_ts") or 0.0), _best_a124_mtime)
    _v52_catalog = {
        "cycle_count": int(a.get("cycle_count", 0) or 0),
        "binaries_monitored": _bin_cnt,
        "uma_proposed_count": _uma_cnt,
        "uma_hot_bonds_count": _uma_hot_cnt,
        "negrisk_slates_count": _nrc_cnt,
        "cal1_ladders_count": _cal1_cnt,
        "ws_subscribed_tokens": _ws_cnt,
        "ws_shards_active": _ws_shards,
        "dormant_ws_pinned_tokens": _dorm_pin,
        "maker_pending_shadow": _mkr_pend_tot,
        "bridge_emitted_total": int(_lbt.get("emitted_total") or _cat_c.get("bridge_emitted_total") or a.get("d1_bridge_emitted") or len(_recent_ipc_cands)),
        "ipc_tail_by_sleeve": _ipc_slv_map,
        "live_bridge_telemetry": _lbt,
    }
    out["alpha124"] = {
        "updated_ts": round(_best_a124_ts, 3) if _best_a124_ts > 0 else None,
        "state_age_sec": round(max(0.0, now_u - _best_a124_ts), 1) if _best_a124_ts > 0 else None,
        "cycle_count": int(a.get("cycle_count", 0) or 0),
        "v52_catalog": _v52_catalog,
        "spots": spots,
        "promoted_count": promoted_cnt,
        "near_grad8_count": near_grad8_cnt,
        "machine_gun_sleeves": machine_gun_sleeves,
        "zero_loss_t1000_pnl_usd": zero_loss_t1000_pnl,
        "zero_loss_wins_total": zero_loss_wins,
        "v3_armed_count": len(frontier_v3_grad8),
        "bridged_count": len(live_bridged_sleeves),
        "open_total": len(open_p),
        "pending_d1_mkr": pend_d1_mkr,
        "pending_zf_mkr": pend_zf_mkr,
        "pending_pmo": len(pmo_list),
        "closed_total": sum(int(v.get("closed", 0) or 0) for v in by_slv.values() if isinstance(v, dict)),
        "by_d1_asset": a.get("by_d1_asset") or {},
        "sleeves": slv_rows,
        "open_positions": open_boxes,
        "recent_closed": recent_shadow_closed,
    }
else:
    out["alpha124"] = {}

# 4b. Directional OOS Paper Trader + Phase 3A Shadow Maker Tracker
pt_path = root / "data/polymarket/paper_trader_state.json"
p34_path = root / "data/polymarket/shadow_phase3_4_tracker.jsonl"
dir_shadow = {}
if pt_path.exists():
    try:
        pt = json.loads(pt_path.read_text())
        vo = pt.get("validation_oos_epoch") or {}
        dir_shadow = {
            "status": pt.get("status", "UNKNOWN"),
            "spec_version": (pt.get("governance") or {}).get("specification_version", "v3.1"),
            "oos_equity_usd": round(float(vo.get("paper_portfolio_equity", 1000.0) or 1000.0), 2),
            "oos_pnl_usd": round(float(vo.get("cumulative_realized_pnl", 0.0) or 0.0), 2),
            "oos_wins": int(vo.get("winning_trades", 0) or 0),
            "oos_losses": int(vo.get("losing_trades", 0) or 0),
            "oos_wr_pct": round(float(vo.get("win_rate_pct", 0.0) or 0.0), 1),
            "open_count": int(pt.get("active_open_positions_count", 0) or 0),
        }
    except Exception:
        pass
if p34_path.exists():
    try:
        with open(p34_path, "rb") as _pf:
            _psz = p34_path.stat().st_size
            _pf.seek(max(0, _psz - 131072))
            _plines = _pf.read().decode("utf-8", errors="replace").splitlines()[1 if _psz > 131072 else 0:]
        p3a_reg = sum(1 for x in _plines if '"SHADOW_PHASE3A_MAKER_IN_REGISTERED"' in x)
        p3a_fill = sum(1 for x in _plines if '"SHADOW_PHASE3A_MAKER_FILLED"' in x)
        p3a_res = [json.loads(x) for x in _plines if '"SHADOW_PHASE3A_MAKER_RESOLVED"' in x]
        p3a_w = sum(1 for r in p3a_res if float(r.get("pnl_usd", r.get("net_pnl_usd", 0.0)) or 0.0) > 0 or r.get("won") is True)
        dir_shadow["p3a_registered_tail"] = p3a_reg
        dir_shadow["p3a_filled_tail"] = p3a_fill
        dir_shadow["p3a_resolved_w"] = p3a_w
        dir_shadow["p3a_resolved_n"] = len(p3a_res)
    except Exception:
        pass
for _ck, _cf in (
    ("cand_a_zsplit", "data/polymarket/state_shadow_hybrid_zsplit.json"),
    ("xau_15m", "data/polymarket/state_shadow_xau_15m.json"),
    ("cand_b_btc5m", "data/polymarket/state_shadow_btc_5m.json"),
    ("sol_v395", "data/polymarket/state_shadow_sol_v392.json"),
):
    _cp = root / _cf
    if _cp.exists():
        try:
            _cj = json.loads(_cp.read_text())
            _fc = _cj.get("funnel_counters") or {}
            dir_shadow[_ck] = {
                "status": _cj.get("status", "UNKNOWN"),
                "wins": int(_cj.get("winning_trades", 0) or 0),
                "losses": int(_cj.get("losing_trades", 0) or 0),
                "open": int(_cj.get("active_open_positions_count", 0) or 0),
                "pending_orders": int(_cj.get("pending_orders_count", 0) or 0),
                "pnl_usd": round(float(_cj.get("realized_pnl", 0.0) or 0.0), 2),
                "ready": bool(_cj.get("ready_for_live_graduation", False)),
                "signals_seen": int(_fc.get("signals_seen", _fc.get("ticks_scanned", 0)) or 0),
                "maker_queued": int(_fc.get("maker_queued", 0) or 0),
                "v395_clean": int(_cj.get("v395_clean_trades_settled", 0) or 0),
            }
        except Exception:
            pass
out["directional_shadow"] = dir_shadow

# 4c. Live Riskless Arbitrage & Carry Radar (5m Universe Ranker + Real-Time Live Harvester IPC + Machine-Gun Auto-Discovery)
radar_opps = []
radar_seen = set()
radar_summary = {
    "scanned_at_et": "-",
    "age_sec": None,
    "active_markets_scanned": 0,
    "events_scanned": 0,
    "fee_free_markets": 0,
    "fee_enabled_markets": 0,
    "counts": {"LIVE_IPC": 0, "MACHINE_GUN": 0, "V6_EXPANSION": 0, "UMA_CARRY": 0, "POST_CLINCH": 0, "LOCKED_REWARD": 0, "SLATE_ARB": 0},
    "top_bps_per_hr": 0.0,
}

def _push_radar(bucket, sleeve_lbl, mkt_id, title, side_lbl, entry_px, edge_bps, bps_hr, liq_usd, rem_hr, auth_live, extra_tag=""):
    key = (bucket, str(mkt_id or title)[:48])
    if key in radar_seen:
        return
    radar_seen.add(key)
    radar_summary["counts"][bucket] = radar_summary["counts"].get(bucket, 0) + 1
    if auth_live and bps_hr and float(bps_hr) > radar_summary["top_bps_per_hr"]:
        radar_summary["top_bps_per_hr"] = round(float(bps_hr), 1)
    radar_opps.append({
        "bucket": bucket,
        "sleeve": sleeve_lbl,
        "market_id": str(mkt_id or ""),
        "title": str(title or "")[:88],
        "side": str(side_lbl or "BUY"),
        "entry_px": round(float(entry_px or 0.0), 4),
        "edge_bps": round(float(edge_bps or 0.0), 1),
        "bps_per_hr": round(float(bps_hr or 0.0), 1),
        "liquidity_usd": round(float(liq_usd or 0.0), 0),
        "rem_hours": round(float(rem_hr), 2) if rem_hr is not None else None,
        "authorized_live": bool(auth_live),
        "extra": str(extra_tag or ""),
    })

# Real-time Live IPC candidates (most recent first; skip stale >30m or expired markets)
_now_rad_u = time.time()
for _cd in reversed(_recent_ipc_cands[-45:]):
    try:
        _ts_cd = float(_cd.get("ts_unix") or 0.0)
        if _ts_cd > 0 and (_now_rad_u - _ts_cd) > 1800.0:
            continue
        _exp_cd = float(_cd.get("expiry_ts") or 0.0)
        if _exp_cd > 0 and _exp_cd < (_now_rad_u - 300.0):
            continue
        _slv_c = str(_cd.get("sleeve_source") or _cd.get("box_type") or "BOND1_UMA_RESOLUTION_CARRY")
        if _slv_c.upper() in _PAUSED_RB_SET:
            continue
        _is_mg_c = "MACHINE_GUN" in _slv_c.upper() or _slv_c.upper().startswith("MG_")
        _bkt_c = "MACHINE_GUN" if _is_mg_c else "LIVE_IPC"
        if radar_summary["counts"].get(_bkt_c, 0) >= 6:
            continue
        _mid_c = str(_cd.get("leg_a_market_id") or _cd.get("dedupe_key") or "")
        _px_c = float(_cd.get("box_cost_net") or _cd.get("anchor_bid_px") or _cd.get("leg_a_limit_price") or 0.99)
        _ebps_c = max(0.0, (1.0 - _px_c) * 10000.0)
        _rem_hr_c = max(0.0, (_exp_cd - _now_rad_u) / 3600.0) if _exp_cd > 0 else None
        _hold_c = max(0.5, _rem_hr_c if (_rem_hr_c is not None and _rem_hr_c > 0) else 1.25)
        _bhr_c = _ebps_c / _hold_c
        _lbl_c = str(_cd.get("question") or _cd.get("leg_a_label") or _cd.get("regime") or _mid_c).replace("SINGLE_LEG_MAKER_LOCK_", "")
        # Enrich from cached Gamma title when available
        _tid_lu = str(_cd.get("leg_a_token_id") or "")
        if _tid_lu and '_tok_meta' in locals() and isinstance(_tok_meta.get(_tid_lu), dict) and _tok_meta[_tid_lu].get("title"):
            _lbl_c = _tok_meta[_tid_lu]["title"]
        elif _lbl_c.startswith("SPORTS_"):
            _sp_parts = _lbl_c.split(" ", 1)
            _cat_pretty = _sp_parts[0].replace("SPORTS_", "").replace("_", " ").title()
            _lbl_c = f"{_cat_pretty}: {_sp_parts[1]}" if len(_sp_parts) > 1 else _cat_pretty
        _age_c = max(0, int(_now_rad_u - (_ts_cd if _ts_cd > 0 else _now_rad_u)))
        _push_radar(
            _bkt_c,
            _slv_c,
            _mid_c,
            _lbl_c,
            f"{_cd.get('leg_a_side') or 'YES'} (0% Mkr)",
            _px_c,
            _ebps_c,
            _bhr_c,
            float(_cd.get("shares") or 20) * _px_c,
            _rem_hr_c,
            True,
            f"IPC {_age_c}s ago",
        )
    except Exception:
        pass

# Auto-discover any dedicated *machine_gun* candidate jsonl streams
for _mg_cf in sorted((root / "data/polymarket").glob("*machine_gun*.jsonl")):
    try:
        for _mln in _mg_cf.read_text(errors="replace").splitlines()[-15:]:
            if not _mln.strip():
                continue
            _mc = json.loads(_mln)
            _mpx = float(_mc.get("box_cost_net") or _mc.get("entry_px") or _mc.get("price") or 0.985)
            _meb = float(_mc.get("edge_bps") or max(0.0, (1.0 - _mpx) * 10000.0))
            _push_radar(
                "MACHINE_GUN",
                str(_mc.get("sleeve") or "MACHINE_GUN_RISKLESS"),
                str(_mc.get("market_id") or ""),
                str(_mc.get("question") or _mc.get("title") or "Machine-Gun Candidate"),
                str(_mc.get("side") or "BOX"),
                _mpx,
                _meb,
                float(_mc.get("est_bps_per_hour") or _meb * 2.0),
                float(_mc.get("liquidity_usd") or 100.0),
                0.25,
                bool(_mc.get("authorized_live", False)),
                "MG Stream",
            )
    except Exception:
        pass

rk_path = root / "data/polymarket/paa/market_opportunity_ranking.json"
if rk_path.exists():
    try:
        rk = json.loads(rk_path.read_text(encoding="utf-8"))
        _rk_age_s = round(max(0.0, _now_rad_u - rk_path.stat().st_mtime), 1)
        radar_summary["scanned_at_et"] = _fmt_et(rk.get("scanned_at_utc"), "%H:%M:%S")
        radar_summary["age_sec"] = _rk_age_s
        radar_summary["active_markets_scanned"] = int(rk.get("active_markets_scanned", 0) or 0)
        radar_summary["events_scanned"] = int(rk.get("events_scanned", 0) or 0)
        radar_summary["fee_free_markets"] = int(rk.get("fee_free_markets", 0) or 0)
        radar_summary["fee_enabled_markets"] = int(rk.get("fee_enabled_markets", 0) or 0)
        if _rk_age_s <= 900.0:
            for _rt in (rk.get("alpha124_realtime_top_opportunities") or [])[:6]:
                _cts = float(_rt.get("close_ts") or 0.0)
                if _cts > 0 and _cts < (_now_rad_u - 300.0):
                    continue
                _epx = float(_rt.get("ask_vwap") or 0.99)
                _eb = round(float(_rt.get("net_edge") or max(0.0, 1.0 - _epx)) * 10000.0, 1)
                _bhr = round(float(_rt.get("ev_per_dollar_hour") or 0.0) * 10000.0, 1)
                _rhr = (_cts - _now_rad_u) / 3600.0 if _cts > _now_rad_u else 0.5
                _rt_lbl = re.sub(r"^\[[A-Z0-9_]+\]\s*", "", str(_rt.get("market") or "").strip())
                _push_radar("LIVE_IPC", str(_rt.get("sleeve") or "ALPHA124_RT"), "", _rt_lbl, "MAKER", _epx, _eb, _bhr, _rt.get("l1_usd", 0), _rhr, True, "A124 RT")
        if _rk_age_s <= 7200.0:
            for _u in (rk.get("ranked_uma_proposed_carries") or [])[:8]:
                _push_radar(
                    "UMA_CARRY",
                    "BOND1_UMA_CARRY",
                    _u.get("market_id"),
                    _u.get("question"),
                    "PROPOSED (0% Mkr)",
                    _u.get("est_maker_entry_px", 0.985),
                    _u.get("net_edge_bps_maker_0pct", 0),
                    _u.get("est_bps_per_hour", 0),
                    _u.get("liquidity_usd", 0),
                    1.5,
                    _u.get("authorized_live", True),
                    str(_u.get("category") or ""),
                )
            for _pc in (rk.get("ranked_post_clinch_sweepers") or [])[:8]:
                _push_radar(
                    "POST_CLINCH",
                    "MKR_LOCK1_SWEEPER",
                    _pc.get("market_id"),
                    _pc.get("question"),
                    f"{_pc.get('side', 'YES')} Clinch",
                    _pc.get("maker_bid_px", 0.993),
                    _pc.get("net_edge_bps_maker_0pct", 0),
                    _pc.get("est_bps_per_hour", 0),
                    _pc.get("liquidity_usd", 0),
                    0.5,
                    _pc.get("authorized_live", True),
                    str(_pc.get("category") or ""),
                )
        for _rwq in (a.get("pending_maker_orders") if 'a' in locals() and isinstance(a, dict) else []) or []:
            if not isinstance(_rwq, dict) or _rwq.get("sleeve") != "MKR_REWARD_LOCKED_CARRY":
                continue
            _rw_cts = float(_rwq.get("close_ts") or 0.0)
            if _rw_cts > 0 and _rw_cts < (_now_rad_u - 300.0):
                continue
            if float(_rwq.get("p_model_at_post") or 0.0) < 0.999 or float(_rwq.get("best_bid_at_post") or 1.0) > 0.995:
                continue
            _rpx = float(_rwq.get("resting_bid") or 0.993)
            _reb = round(max(0.0, 1.0 - _rpx) * 10000.0, 1)
            _rrem = max(0.25, (_rw_cts - _now_rad_u) / 3600.0) if _rw_cts > _now_rad_u else 0.5
            _rmid = str((_rwq.get("extra") or {}).get("market_id") or "")
            _push_radar(
                "LOCKED_REWARD",
                "MKR_REWARD_LOCKED_CARRY",
                _rmid,
                _rwq.get("title") or _rwq.get("asset_or_city"),
                f"{_rwq.get('side', 'NO')} (100% Dead)",
                _rpx,
                _reb,
                round(_reb / max(1.25, _rrem), 1),
                float(_rwq.get("l1_bid_usd") or 25.0),
                _rrem,
                True,
                f"Queue ${float(_rwq.get('queue_ahead_usd') or 0.0):.0f}",
            )
        if _rk_age_s <= 7200.0:
            for _lr in (rk.get("ranked_locked_clob_rewards") or [])[:6]:
                _lr_rem = float(_lr.get("rem_hours", 1.0) or 0.0)
                if _lr_rem <= 0.0 and (_rk_age_s > 900.0):
                    continue
                _lr_locked = bool(_lr.get("uma_locked") or float(_lr.get("p_lock") or 0.0) >= 0.999)
                _push_radar(
                    "LOCKED_REWARD",
                    "MKR_LOCKED_REWARD",
                    _lr.get("market_id"),
                    _lr.get("question"),
                    f"{_lr.get('side', 'NO')} + Pool",
                    _lr.get("locked_maker_bid_px", 0.97),
                    _lr.get("carry_edge_bps", 0),
                    _lr.get("est_bps_per_hour", 0),
                    _lr.get("book_liquidity_usd", 0),
                    _lr.get("rem_hours", 1.0),
                    _lr_locked,
                    f"${int(float(_lr.get('daily_reward_pool_usd') or 0))}/d ({'Locked' if _lr_locked else 'Uncalled'})",
                )
            for _na in ((rk.get("ranked_negrisk_slate_arbs") or []) + (rk.get("ranked_maker_anchor_slate_arbs") or []))[:6]:
                _push_radar(
                    "SLATE_ARB",
                    "NR0_SLATE_ARB",
                    _na.get("event_id") or "",
                    _na.get("title") or _na.get("question"),
                    f"{_na.get('legs', '?')}-Leg YES",
                    _na.get("sum_yes_ask") or _na.get("maker_box_cost") or 0.99,
                    _na.get("net_edge_bps", 0),
                    _na.get("est_bps_per_hour", 0),
                    _na.get("min_leg_liquidity_usd", 0),
                    _na.get("rem_hours"),
                    False,
                    "0%-Fee Slate",
                )
    except Exception:
        pass

# 4d. Stage G Cross-Venue Shadow + 8 v6 Riskless Expansion Engines + CompactCandidateL2Recorder Telemetry
_xv_dir = root / "data/cross_venue_shadow"
_xv_health = {}
_xv_grad = {}
_v6_xv = {}
_v6_a124 = {}
for _jp, _jd in (
    (_xv_dir / "shadow_service_health.json", "_xv_health"),
    (_xv_dir / "shadow_graduation_report.json", "_xv_grad"),
    (_xv_dir / "v6_expansion_telemetry.json", "_v6_xv"),
    (root / "data/polymarket/v6_expansion_alpha124_telemetry.json", "_v6_a124"),
):
    if _jp.exists():
        try:
            locals()[_jd] = json.loads(_jp.read_text(encoding="utf-8"))
        except Exception:
            pass
if not _v6_a124 and isinstance(out.get("alpha124"), dict):
    try:
        if 'a' in locals() and isinstance(a, dict) and isinstance(a.get("v6_expansion"), dict):
            _v6_a124 = a["v6_expansion"]
    except Exception:
        pass

_l2_bytes_total = 0
_l2_files_cnt = 0
_l2_cache_p = pathlib.Path("/tmp/dominus_l2_stats_cache.json")
_l2_cached_ok = False
if not _OFFLINE_PROBE and _l2_cache_p.exists():
    try:
        if (time.time() - _l2_cache_p.stat().st_mtime) <= 60.0:
            _l2_cj = json.loads(_l2_cache_p.read_text(encoding="utf-8"))
            _l2_files_cnt = int(_l2_cj.get("files", 0) or 0)
            _l2_bytes_total = int(_l2_cj.get("bytes", 0) or 0)
            _l2_cached_ok = True
    except Exception:
        pass
if not _l2_cached_ok:
    for _l2_root in (root / "data/polymarket/candidate_l2", _xv_dir / "candidate_l2"):
        if _l2_root.exists():
            try:
                for _dirpath, _, _fnames in os.walk(str(_l2_root)):
                    _l2_files_cnt += len(_fnames)
                    for _fn in _fnames:
                        try:
                            _l2_bytes_total += os.path.getsize(os.path.join(_dirpath, _fn))
                        except OSError:
                            pass
            except Exception:
                pass
    if not _OFFLINE_PROBE:
        try:
            _l2_cache_p.write_text(json.dumps({"files": _l2_files_cnt, "bytes": _l2_bytes_total}), encoding="utf-8")
        except Exception:
            pass

_v6_meta = [
    ("XV_SUBSET_NO_BOX", "Cross-Venue m=2 Subset NO Box (Cancel-Safe +$1 Outsider)"),
    ("TAIL_BOUNDARY_001_ARB", "Polymarket 0.001-Tick Sub-Penny Parabolic Fee Collapse"),
    ("BOND3_MULTISOURCE_DEAD_SPLIT", "Multi-Source MOOV2 Carry + Stage C2 Dead-Leg Split"),
    ("XV_FX_INVARIANT_CAD_USD_BOX", "CA-ON Legal STX Ontario (CAD 0% Mkr) <-> ForecastEx (USD)"),
    ("DERIBIT_VERTICAL_SUPER_REP", "Keyless Deribit Linear USDC 08:00 UTC Vertical Super-Rep"),
    ("XV_HALFTIME_FREEZE_CORRIDOR", "Cross-Venue .5-Hook Halftime Freeze FG = S_1H + 2H"),
    ("HEDGED_PRESPLIT_CONV_GUN", "Closed NegRisk NR3 Pre-Converted Overround + Shadow Split"),
    ("YIELD_STACKED_CARRY_BOX", "Contractual Coupon Carry Box (ForecastEx 3.8% / vUSDT)"),
]
_v6_rows = []
_v6_eval_tot = 0
_v6_found_tot = 0
_by_slv_ref = (a.get("by_sleeve") if ('a' in locals() and isinstance(a, dict)) else None) or {}
_by_slv_xv_ref = (_v6_xv.get("by_sleeve") if isinstance(_v6_xv, dict) else None) or {}
for _sid, _sdesc in _v6_meta:
    _ps_a = ((_v6_a124.get("per_sleeve") or {}).get(_sid)) or {}
    _ps_x = ((_v6_xv.get("per_sleeve") or {}).get(_sid)) or {}
    _ev_c = int(_ps_a.get("evaluated", 0) or 0) + int(_ps_x.get("evaluated", 0) or 0)
    _fn_c = int(_ps_a.get("opportunities_found", 0) or 0) + int(_ps_x.get("opportunities_found", 0) or 0)
    _cy_c = int(_ps_a.get("cycle_hits", 0) or 0) + int(_ps_x.get("cycle_hits", 0) or 0)
    _sm = _by_slv_ref.get(_sid) or {}
    _sm_x = _by_slv_xv_ref.get(_sid) or {}
    _v6_eval_tot += _ev_c
    _v6_found_tot += _fn_c
    _v6_rows.append({
        "strategy_id": _sid,
        "desc": _sdesc,
        "evaluated": _ev_c,
        "opportunities_found": _fn_c,
        "cycle_hits": _cy_c,
        "shadow_open": int(_sm.get("open", 0) or 0) + int(_sm_x.get("open", 0) or 0),
        "shadow_wins": int(_sm.get("wins", 0) or 0) + int(_sm_x.get("wins", 0) or 0),
        "shadow_losses": int(_sm.get("losses", 0) or 0) + int(_sm_x.get("losses", 0) or 0),
        "t1000_pnl_usd": round(
            float(_sm.get("realized_pnl_t1000_usd", 0.0) or 0.0)
            + float(_sm_x.get("realized_pnl_t1000_usd", 0.0) or 0.0),
            2,
        ),
    })

for _vhit in ((_v6_xv.get("top_opportunities") or []) + (_v6_a124.get("top_opportunities") or []))[:12]:
    if not isinstance(_vhit, dict):
        continue
    _push_radar(
        "V6_EXPANSION",
        str(_vhit.get("strategy_id") or "V6_RISKLESS"),
        str(_vhit.get("opportunity_id") or ""),
        str(_vhit.get("title") or "v6 Verified Riskless Box"),
        "+".join(_vhit.get("venues") or ["POLY"]),
        float(_vhit.get("unit_cost") or 0.985),
        float(_vhit.get("guaranteed_net_edge_bps") or 0.0),
        float(_vhit.get("bps_per_hr") or 0.0),
        float(_vhit.get("all_in_cost_usd") or 50.0),
        _vhit.get("rem_hours", 1.0),
        False,
        ",".join(_vhit.get("jurisdiction_tags") or ["SHADOW_V6"]),
    )

_rec_a = _v6_a124.get("candidate_l2_recorder") or {}
_rec_x = _v6_xv.get("candidate_l2_recorder") or {}
_xv_age = round(max(0.0, _now_rad_u - float(_xv_health.get("checked_at_unix") or 0.0)), 1) if _xv_health.get("checked_at_unix") else None
out["v6_expansion"] = {
    "a124_cycles": int(_v6_a124.get("cycles_scanned", 0) or 0),
    "cross_venue_cycles": int(_v6_xv.get("cycles_scanned", _xv_health.get("cycles_completed", 0)) or 0),
    "evaluated_total": _v6_eval_tot,
    "opportunities_total": _v6_found_tot,
    "deribit_usdc_quotes": int(_v6_xv.get("deribit_usdc_quotes_cached", 0) or 0),
    "engines": _v6_rows,
    "l2_recorder": {
        "archive_files": _l2_files_cnt,
        "archive_mb": round(_l2_bytes_total / (1024.0 * 1024.0), 3),
        "bytes_today": int(_rec_a.get("bytes_today", 0) or 0) + int(_rec_x.get("bytes_today", 0) or 0),
        "daily_cap_mb": 12.0,
        "frames_recorded": int(_rec_a.get("frames_recorded", 0) or 0) + int(_rec_x.get("frames_recorded", 0) or 0),
        "budget_drops": int(_rec_a.get("budget_drops", 0) or 0) + int(_rec_x.get("budget_drops", 0) or 0),
    },
    "cross_venue_shadow": {
        "service_healthy": bool(_xv_health.get("service_healthy", False)),
        "network_mode": str(_xv_health.get("network_mode") or _v6_xv.get("network_mode") or "init"),
        "data_origin": str(_xv_health.get("data_origin") or "-"),
        "age_sec": _xv_age,
        "cycles_completed": int(_xv_health.get("cycles_completed", 0) or 0),
        "live_markets_seen": int(_v6_xv.get("live_markets_seen", 0) or 0),
        "matched_pairs_seen": int(_v6_xv.get("matched_pairs_seen", 0) or 0),
        "venue_health": (_xv_grad.get("venue_health") or _xv_health.get("venue_health") or {}),
    },
}

radar_opps.sort(
    key=lambda x: (
        0 if x.get("authorized_live") else 1,
        0 if x["bucket"] in ("LIVE_IPC", "MACHINE_GUN", "V6_EXPANSION") else 1,
        -float(x.get("bps_per_hr") or 0.0),
    )
)
out["riskless_radar"] = {
    "summary": radar_summary,
    "opportunities": radar_opps[:36],
}
out["apex_testnet"] = {}
for _k_mid in (
    "_a_raw_doc", "_mir_raw_doc", "a", "by_slv", "mir_by_slv", "open_p", "rc_p",
    "pmo_list", "raw_open_p", "raw_rc_p", "raw_pmo", "rk", "_v6_xv", "_v6_a124",
    "radar_opps", "_tail_lines", "_tok_meta", "_sf_rows", "log_events",
):
    globals().pop(_k_mid, None)
gc.collect()

# 6. PAA Autonomous Operating System & Zero-Trust Live SQLite + Systemd Telemetry
paa_dir = root / "data/polymarket/paa"
paa_db_p = paa_dir / "paa_tasks.db"
paa_dash_p = paa_dir / "paa_dashboard.json"
now_probe_u = time.time()

def _parse_utc_epoch(ts_val):
    if not ts_val:
        return None
    try:
        s = str(ts_val).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None

paa_out = {
    "live_probed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_probe_u)),
    "live_probed_at_et": _fmt_et(now_probe_u, "%Y-%m-%d %H:%M:%S"),
    "master_stop_engaged": (paa_dir / "PAA_MASTER_STOP").exists(),
    "accounting_safeguard_active": (paa_dir / "ACCOUNTING_SAFEGUARD_ACTIVE.json").exists(),
    "tier_a_policies": [],
    "tier_a_intact_count": 0,
    "heartbeats": {},
    "systemd_timers": [],
    "task_counts_by_state": {},
    "recent_tasks": [],
    "recent_events": [],
    "zero_trust": {
        "verified_facts_fresh": 0,
        "verified_facts_stale": 0,
        "verified_facts_contradicted": 0,
        "sessions_total": 0,
        "fresh_session_pct": 100.0,
        "max_context_pct": 0.0,
        "avg_context_pct": 0.0,
        "context_rotations": 0,
        "context_cap_pct": 60.0,
    },
    "verified_facts": [],
    "recent_sessions": [],
    "research_ladder": {"HYPOTHESIS": 0, "BACKTESTED": 0, "OOS_TESTED": 0, "SHADOW_VALIDATED": 0, "LIVE_VERIFIED": 0},
    "recent_findings": [],
    "deployments": [],
    "operating_mode": "RISKLESS_PAA",
    "riskless_kpis": {
        "riskless_only_mode": bool((strat_cfg.get("directional") or {}).get("riskless_only_mode", True)),
        "paused_riskless_sleeves": list((strat_cfg.get("riskless_boxes") or {}).get("paused_riskless_sleeves") or []),
    },
    "verified_financial_performance": {},
    "budget_and_resources": {"daily_ai_calls": 0, "daily_ai_cost_usd": 0.0, "max_daily_ai_cost_usd": 2.50, "max_daily_ai_calls": 96},
}

pol_dir = root / "config/policies"
for _pf in ("PAA_MISSION.md", "PAA_AUTONOMY_POLICY.md", "PAA_RISK_POLICY.md", "PAA_DEPLOYMENT_POLICY.md", "PAA_VERIFICATION_POLICY.md"):
    _ok = (pol_dir / _pf).exists()
    paa_out["tier_a_policies"].append({"file": _pf, "present": _ok})
    if _ok:
        paa_out["tier_a_intact_count"] += 1

if not _OFFLINE_PROBE:
    try:
        _tm_proc = subprocess.run(
            ["systemctl", "--user", "list-timers", "--all", "--no-pager", "--output=json"],
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if _tm_proc.returncode == 0 and _tm_proc.stdout.strip().startswith("["):
            for _t in json.loads(_tm_proc.stdout):
                _u = str(_t.get("unit") or "")
                if "polymarket-paa-" not in _u and "polymarket-full-throttle-" not in _u:
                    continue
                _nxt_us = _t.get("next")
                _lst_us = _t.get("last")
                _nxt_s = (_nxt_us / 1e6) if isinstance(_nxt_us, (int, float)) and _nxt_us > 0 else None
                _lst_s = (_lst_us / 1e6) if isinstance(_lst_us, (int, float)) and _lst_us > 0 else None
                _tm_rec = {
                    "unit": _u.replace("polymarket-paa-", "").replace("polymarket-", "").replace(".timer", ""),
                    "full_unit": _u,
                    "next_in_sec": round(max(0.0, _nxt_s - now_probe_u), 1) if _nxt_s else None,
                    "last_ago_sec": round(max(0.0, now_probe_u - _lst_s), 1) if _lst_s else None,
                    "last_et": _fmt_et(_lst_s, "%H:%M:%S") if _lst_s else "-",
                    "next_et": _fmt_et(_nxt_s, "%H:%M:%S") if _nxt_s else "-",
                }
                paa_out["systemd_timers"].append(_tm_rec)
                if "full-throttle-sweep" in _u:
                    if _ft_sysd.get("next_trigger_in_sec") is None and _tm_rec["next_in_sec"] is not None:
                        _ft_sysd["next_trigger_in_sec"] = _tm_rec["next_in_sec"]
                        _ft_sysd["next_trigger_et"] = _tm_rec["next_et"]
                    if _ft_sysd.get("last_trigger_ago_sec") is None and _tm_rec["last_ago_sec"] is not None:
                        _ft_sysd["last_trigger_ago_sec"] = _tm_rec["last_ago_sec"]
                        _ft_sysd["last_trigger_et"] = _tm_rec["last_et"]
        _sys_sup = subprocess.run(["systemctl", "is-active", "paa-system-supervisor.timer"], capture_output=True, text=True, timeout=2.0)
        paa_out["pid1_supervisor_timer"] = _sys_sup.stdout.strip() or "unknown"
    except Exception:
        paa_out["pid1_supervisor_timer"] = "unknown"
else:
    paa_out["pid1_supervisor_timer"] = "active"

if paa_db_p.exists():
    _conn = None
    try:
        _conn = sqlite3.connect(f"file:{paa_db_p}?mode=ro", uri=True, timeout=3.0)
        _conn.execute("PRAGMA cache_size = -256")
        _conn.execute("PRAGMA mmap_size = 0")
        _conn.execute("PRAGMA temp_store = MEMORY")
        _conn.row_factory = sqlite3.Row
        _tables = {r["name"] for r in _conn.execute("PRAGMA main.table_info(paa_tasks)").fetchall()}
        _all_tbls = {r[0] for r in _conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        if "heartbeats" in _all_tbls:
            for r in _conn.execute("SELECT * FROM heartbeats").fetchall():
                _ts = _parse_utc_epoch(r["last_seen_utc"])
                _age = round(max(0.0, now_probe_u - _ts), 1) if _ts else None
                try:
                    _det = json.loads(r["details_json"] or "{}")
                except Exception:
                    _det = {}
                paa_out["heartbeats"][r["component"]] = {
                    "component": r["component"],
                    "status": r["status"],
                    "cycle_count": int(r["cycle_count"] or 0),
                    "pid": r["pid"],
                    "last_seen_utc": r["last_seen_utc"],
                    "last_seen_et": _fmt_et(r["last_seen_utc"], "%H:%M:%S"),
                    "age_sec": _age,
                    "details": _det,
                }
        paa_out["director_heartbeat"] = paa_out["heartbeats"].get("paa_director") or {}
        paa_out["monitoring_health"] = {
            "paa_monitor": paa_out["heartbeats"].get("paa_monitor") or {},
            "paa_supervisor": paa_out["heartbeats"].get("paa_supervisor") or {},
            "accounting_safeguard_active": paa_out["accounting_safeguard_active"],
        }

        for r in _conn.execute("SELECT execution_state, COUNT(*) AS cnt FROM paa_tasks GROUP BY execution_state").fetchall():
            paa_out["task_counts_by_state"][r["execution_state"]] = int(r["cnt"])

        _has_zt_cols = "epistemic_status" in _tables and "session_count" in _tables
        _t_sql = (
            "SELECT task_id, category, priority_label, execution_state, epistemic_status, session_count, title, next_action, last_error, updated_at_utc FROM paa_tasks ORDER BY updated_at_utc DESC LIMIT 10"
            if _has_zt_cols else
            "SELECT task_id, category, priority_label, execution_state, 'VERIFIED_FACT' AS epistemic_status, 1 AS session_count, title, next_action, last_error, updated_at_utc FROM paa_tasks ORDER BY updated_at_utc DESC LIMIT 10"
        )
        for r in _conn.execute(_t_sql).fetchall():
            paa_out["recent_tasks"].append({
                "task_id": r["task_id"],
                "category": r["category"],
                "priority": r["priority_label"],
                "state": r["execution_state"],
                "epistemic_status": r["epistemic_status"],
                "sessions": int(r["session_count"] or 0),
                "title": str(r["title"] or "")[:72],
                "next_action": str(r["next_action"] or "")[:40],
                "last_error": str(r["last_error"] or "")[:80],
                "updated_et": _fmt_et(r["updated_at_utc"], "%m-%d %H:%M:%S"),
            })

        if "task_events" in _all_tbls:
            for r in _conn.execute("SELECT timestamp_utc, task_id, component, event_type, details_json FROM task_events ORDER BY event_id DESC LIMIT 10").fetchall():
                paa_out["recent_events"].append({
                    "ts_et": _fmt_et(r["timestamp_utc"], "%H:%M:%S"),
                    "task_id": r["task_id"] or "-",
                    "component": r["component"],
                    "event_type": r["event_type"],
                    "details": str(r["details_json"] or "")[:95],
                })

        if "verified_facts" in _all_tbls:
            _fresh_n, _stale_n, _contra_n = 0, 0, 0
            _vis_f = 0
            for r in _conn.execute("SELECT * FROM verified_facts ORDER BY observed_at_utc DESC LIMIT 50").fetchall():
                _obs_u = _parse_utc_epoch(r["observed_at_utc"])
                _exp_u = _parse_utc_epoch(r["expires_at_utc"])
                _rem_s = round(_exp_u - now_probe_u, 1) if _exp_u else -1.0
                if str(r["fact_key"] or "").startswith("cert.") and _rem_s < -3600.0:
                    continue
                _age_s = round(max(0.0, now_probe_u - _obs_u), 1) if _obs_u else None
                _epi = str(r["epistemic_status"] or "UNKNOWN")
                if _epi == "CONTRADICTED":
                    _eff = "CONTRADICTED"
                    _contra_n += 1
                elif _rem_s <= 0:
                    _eff = "STALE_REVALIDATION_REQUIRED"
                    _stale_n += 1
                else:
                    _eff = _epi
                    _fresh_n += 1
                if _vis_f < 10:
                    _vis_f += 1
                    try:
                        _val = json.loads(r["value_json"])
                    except Exception:
                        _val = r["value_json"]
                    paa_out["verified_facts"].append({
                        "fact_key": r["fact_key"],
                        "category": r["category"],
                        "value": _val,
                        "effective_status": _eff,
                        "age_sec": _age_s,
                        "ttl_remaining_sec": _rem_s,
                        "source_ref": str(r["source_ref"] or "")[:44],
                        "verified_by": r["verified_by"],
                    })
            paa_out["zero_trust"]["verified_facts_fresh"] = _fresh_n
            paa_out["zero_trust"]["verified_facts_stale"] = _stale_n
            paa_out["zero_trust"]["verified_facts_contradicted"] = _contra_n

        if "session_runs" in _all_tbls:
            _sr = _conn.execute(
                "SELECT COUNT(*) AS n, SUM(CASE WHEN fresh_session=1 THEN 1 ELSE 0 END) AS fn, MAX(context_utilization_pct) AS mx, AVG(context_utilization_pct) AS av, SUM(CASE WHEN checkpoint_triggered=1 THEN 1 ELSE 0 END) AS rot FROM session_runs"
            ).fetchone()
            if _sr and int(_sr["n"] or 0) > 0:
                _tot_s = int(_sr["n"] or 0)
                paa_out["zero_trust"]["sessions_total"] = _tot_s
                paa_out["zero_trust"]["fresh_session_pct"] = round(100.0 * int(_sr["fn"] or 0) / max(1, _tot_s), 1)
                paa_out["zero_trust"]["max_context_pct"] = round(float(_sr["mx"] or 0.0), 2)
                paa_out["zero_trust"]["avg_context_pct"] = round(float(_sr["av"] or 0.0), 2)
                paa_out["zero_trust"]["context_rotations"] = int(_sr["rot"] or 0)
            for r in _conn.execute("SELECT * FROM session_runs ORDER BY created_at_utc DESC LIMIT 6").fetchall():
                paa_out["recent_sessions"].append({
                    "session_id": r["session_id"],
                    "task_id": r["task_id"],
                    "stage_role": r["stage_role"],
                    "fresh_session": bool(r["fresh_session"]),
                    "model_name": r["model_name"],
                    "context_pct": round(float(r["context_utilization_pct"] or 0.0), 2),
                    "status": r["status"],
                    "created_et": _fmt_et(r["created_at_utc"], "%H:%M:%S"),
                })

        if "research_findings" in _all_tbls:
            _rf_cols = {r["name"] for r in _conn.execute("PRAGMA main.table_info(research_findings)").fetchall()}
            if "evidence_stage" in _rf_cols:
                for r in _conn.execute("SELECT COALESCE(evidence_stage,'HYPOTHESIS') AS stg, COUNT(*) AS cnt FROM research_findings GROUP BY COALESCE(evidence_stage,'HYPOTHESIS')").fetchall():
                    if r["stg"] in paa_out["research_ladder"]:
                        paa_out["research_ladder"][r["stg"]] = int(r["cnt"])
                _rf_q = "SELECT finding_id, category, evidence_stage, epistemic_status, expected_net_ev_usd_per_day, succeeded, verdict, hypothesis, created_at_utc FROM research_findings ORDER BY created_at_utc DESC LIMIT 8"
            else:
                _rf_q = "SELECT finding_id, category, 'HYPOTHESIS' AS evidence_stage, 'HYPOTHESIS' AS epistemic_status, expected_net_ev_usd_per_day, succeeded, verdict, hypothesis, created_at_utc FROM research_findings ORDER BY created_at_utc DESC LIMIT 8"
            for r in _conn.execute(_rf_q).fetchall():
                paa_out["recent_findings"].append({
                    "finding_id": r["finding_id"],
                    "category": r["category"],
                    "evidence_stage": r["evidence_stage"],
                    "epistemic_status": r["epistemic_status"],
                    "ev_day": round(float(r["expected_net_ev_usd_per_day"] or 0.0), 4),
                    "succeeded": bool(r["succeeded"]),
                    "verdict": r["verdict"],
                    "hypothesis": str(r["hypothesis"] or "")[:74],
                    "created_et": _fmt_et(r["created_at_utc"], "%H:%M:%S"),
                })

        if "deployments" in _all_tbls:
            for r in _conn.execute("SELECT release_id, candidate_sha, target_env, state, qa_passed, canary_passed, rolled_back, rollback_reason, updated_at_utc FROM deployments ORDER BY updated_at_utc DESC LIMIT 6").fetchall():
                paa_out["deployments"].append({
                    "release_id": r["release_id"],
                    "sha": str(r["candidate_sha"] or "")[:8],
                    "env": r["target_env"],
                    "state": r["state"],
                    "qa_passed": bool(r["qa_passed"]),
                    "canary_passed": bool(r["canary_passed"]),
                    "rolled_back": bool(r["rolled_back"]),
                    "rollback_reason": str(r["rollback_reason"] or "")[:50],
                    "updated_et": _fmt_et(r["updated_at_utc"], "%m-%d %H:%M:%S"),
                })

        if "financial_snapshots" in _all_tbls:
            _fs = _conn.execute("SELECT * FROM financial_snapshots ORDER BY snapshot_id DESC LIMIT 1").fetchone()
            _cut_24h_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now_probe_u - 86400.0))
            _fs_24h = _conn.execute(
                "SELECT recorded_at_utc, free_cash_pusd, open_cost_basis_usd, nav_mark_to_bid_usd, verified_realized_net_pnl_usd FROM financial_snapshots WHERE recorded_at_utc <= ? AND accounting_ok = 1 ORDER BY snapshot_id DESC LIMIT 1",
                (_cut_24h_iso,),
            ).fetchone()
            if not _fs_24h:
                _fs_24h = _conn.execute(
                    "SELECT recorded_at_utc, free_cash_pusd, open_cost_basis_usd, nav_mark_to_bid_usd, verified_realized_net_pnl_usd FROM financial_snapshots WHERE accounting_ok = 1 ORDER BY snapshot_id ASC LIMIT 1"
                ).fetchone()
            if _fs_24h and out.get("polymarket_live"):
                _cash_24h = float(_fs_24h["free_cash_pusd"] or 0.0)
                _open_cb_24h = float(_fs_24h["open_cost_basis_usd"] or 0.0)
                _nav_24h = float(_fs_24h["nav_mark_to_bid_usd"] or 0.0)
                _frozen_disp_now = float(out["polymarket_live"].get("frozen_disputed_open_usd") or 0.0)
                _raw_undisp_open_24h = max(0.0, _open_cb_24h - _frozen_disp_now)
                # Guard against pre-reconciliation redemption snapshots where an already-redeemed lock
                # was counted in free_cash_pusd while still present in open_cost_basis_usd (zero ERC-1155 MTM on-chain).
                if _raw_undisp_open_24h > 0.50 and _nav_24h > 0.0 and (_nav_24h - _cash_24h) < 0.25 * _raw_undisp_open_24h:
                    _undisp_open_24h = 0.0
                else:
                    _undisp_open_24h = _raw_undisp_open_24h
                _cur_eq = float(
                    out["polymarket_live"].get("reconciled_undisputed_equity_usd")
                    or out["polymarket_live"].get("guaranteed_redemption_equity_usd")
                    or out["polymarket_live"].get("bankroll_usd")
                    or 0.0
                )
                _fs_24h_unix = _to_unix(_fs_24h["recorded_at_utc"])
                _dep_24h = 0.0
                for _c in (locals().get("_cf_rows") or []):
                    _c_unix = _to_unix(_c.get("recorded_at_utc") or _c.get("ts_utc"))
                    if _fs_24h_unix is not None and _c_unix is not None and _c_unix > _fs_24h_unix:
                        _sgn = -1.0 if str(_c.get("type") or "DEPOSIT").strip().upper() in ("WITHDRAWAL", "WITHDRAW", "OUTFLOW") else 1.0
                        _dep_24h += _sgn * abs(float(_c.get("amount_usd") or 0.0))
                _has_realized_pair = (
                    _fs is not None
                    and "verified_realized_net_pnl_usd" in _fs.keys()
                    and _fs["verified_realized_net_pnl_usd"] is not None
                    and "verified_realized_net_pnl_usd" in _fs_24h.keys()
                    and _fs_24h["verified_realized_net_pnl_usd"] is not None
                )
                if _has_realized_pair and _cur_eq > 0:
                    _d24 = round(float(_fs["verified_realized_net_pnl_usd"]) - float(_fs_24h["verified_realized_net_pnl_usd"]), 2)
                    _eq_24h_ago = round(max(0.01, _cur_eq - _d24 - _dep_24h), 2)
                else:
                    _eq_24h_ago = round(_cash_24h + _undisp_open_24h, 2) if _cash_24h > 0 else round(_nav_24h, 2)
                    _d24 = round(_cur_eq - _eq_24h_ago - _dep_24h, 2)
                if _eq_24h_ago > 0:
                    _denom_24h = max(0.01, _eq_24h_ago + max(0.0, _dep_24h))
                    out["polymarket_live"]["equity_24h_ago_usd"] = _eq_24h_ago
                    out["polymarket_live"]["deposits_24h_usd"] = round(_dep_24h, 2)
                    out["polymarket_live"]["equity_24h_delta_usd"] = _d24
                    out["polymarket_live"]["equity_24h_pct"] = round(100.0 * _d24 / _denom_24h, 2)
                    out["polymarket_live"]["equity_24h_since_et"] = _fmt_et(_fs_24h["recorded_at_utc"], "%m-%d %H:%M")
            if _fs:
                try:
                    _fs_det = json.loads(_fs["details_json"] or "{}") if "details_json" in _fs.keys() else {}
                except Exception:
                    _fs_det = {}
                _sim_b = _fs_det.get("simulated_benchmarks") if isinstance(_fs_det, dict) else {}
                _rl_m = _fs_det.get("riskless_metrics") if isinstance(_fs_det, dict) else {}
                _ex_m = _fs_det.get("execution_metrics") if isinstance(_fs_det, dict) else {}
                if isinstance(_rl_m, dict) and _rl_m:
                    paa_out["riskless_kpis"].update(_rl_m)
                paa_out["verified_financial_performance"] = {
                    "recorded_et": _fmt_et(_fs["recorded_at_utc"], "%H:%M:%S"),
                    "free_cash_pusd": round(float(_fs["free_cash_pusd"] or 0.0), 2),
                    "nav_mark_to_bid_usd": round(float(_fs["nav_mark_to_bid_usd"] or 0.0), 2),
                    "realized_onchain_net_pnl_usd": round(float(_fs["verified_realized_net_pnl_usd"] or 0.0), 2),
                    "raw_state_ledger_pnl_usd": round(float(_fs["raw_ledger_pnl_usd"] or 0.0), 2),
                    "non_cash_unfilled_artifact_adj_usd": round(float(_fs["phantom_adjustment_usd"] or 0.0), 2),
                    "realized_fees_usd": round(float(_fs["realized_fees_usd"] or 0.0), 2),
                    "research_ai_cost_usd": round(float(_fs["research_ai_cost_usd"] or 0.0), 4),
                    "daily_infra_vm_cost_usd": round(float(_fs["infra_cost_usd"] or 0.0), 4),
                    "net_economic_profit_after_ops_usd": round(float(_fs["net_economic_profit_usd"] or 0.0), 2),
                    "accounting_ok": bool(_fs["accounting_ok"]),
                    "accounting_discrepancy_usd": round(float(_fs["accounting_discrepancy_usd"] or 0.0), 4),
                    "clob_post_p50_ms": (_ex_m or {}).get("clob_post_p50_ms"),
                    "clob_post_p90_ms": (_ex_m or {}).get("clob_post_p90_ms"),
                    "simulated_shadow_t1000_pnl_usd": round(float(_fs["simulated_shadow_t1000_pnl_usd"] or 0.0), 2),
                    "zero_loss_shadow_t1000_pnl_usd": round(float((_sim_b or {}).get("zero_loss_shadow_t1000_pnl_usd", 0.0) or 0.0), 2),
                    "zero_loss_shadow_wins": int((_sim_b or {}).get("zero_loss_shadow_wins", 0) or 0),
                    "simulated_paper_oos_pnl_usd": round(float(_fs["simulated_paper_oos_pnl_usd"] or 0.0), 2),
                }
        if "budget_ledger" in _all_tbls:
            _today_utc = time.strftime("%Y-%m-%d", time.gmtime(now_probe_u))
            _hr_utc = time.strftime("%Y-%m-%dT%H", time.gmtime(now_probe_u))
            _br = _conn.execute(
                "SELECT COUNT(*) AS calls, COALESCE(SUM(estimated_cost_usd), 0.0) AS usd, COALESCE(SUM(input_tokens), 0) AS in_tok, COALESCE(SUM(output_tokens), 0) AS out_tok FROM budget_ledger WHERE date_utc = ? AND cost_type IN ('AI_AGENT_CALL', 'AI_CLI_CALL')",
                (_today_utc,),
            ).fetchone()
            _hr_r = _conn.execute(
                "SELECT COUNT(*) AS calls FROM budget_ledger WHERE hour_utc = ? AND cost_type IN ('AI_AGENT_CALL', 'AI_CLI_CALL')",
                (_hr_utc,),
            ).fetchone()
            if _br:
                paa_out["budget_and_resources"] = {
                    "daily_ai_calls": int(_br["calls"] or 0),
                    "hourly_ai_calls": int(_hr_r["calls"] or 0) if _hr_r else 0,
                    "daily_ai_cost_usd": round(float(_br["usd"] or 0.0), 4),
                    "daily_input_tokens": int(_br["in_tok"] or 0),
                    "daily_output_tokens": int(_br["out_tok"] or 0),
                    "max_daily_ai_cost_usd": 2.50,
                    "max_daily_ai_calls": 96,
                    "max_hourly_ai_calls": 8,
                }
    except Exception as _db_exc:
        paa_out["db_probe_warning"] = str(_db_exc)[:200]
    finally:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
elif paa_dash_p.exists():
    try:
        pd_j = json.loads(paa_dash_p.read_text(encoding="utf-8"))
        paa_out["director_heartbeat"] = pd_j.get("director_heartbeat") or {}
        paa_out["task_counts_by_state"] = pd_j.get("task_counts_by_state") or {}
        paa_out["verified_financial_performance"] = pd_j.get("verified_financial_performance") or {}
        paa_out["budget_and_resources"] = pd_j.get("budget_and_resources") or paa_out["budget_and_resources"]
    except Exception:
        pass

_vf_sync = paa_out.get("verified_financial_performance") or {}
if out.get("polymarket_live") and "realized_onchain_net_pnl_usd" in _vf_sync:
    out["polymarket_live"]["epoch_net_pnl_usd"] = round(float(_vf_sync["realized_onchain_net_pnl_usd"]), 2)
out["paa_autonomy"] = paa_out

# 7. Stage B Institutional Economic Attribution, 6-Stage Opportunity Funnel & 10 North-Star KPIs (45s /tmp cache + isolated helper on live host)
_sb_cache_p = pathlib.Path("/tmp/dominus_stageb_cache.json")
_sb_cached_ok = False
if not _OFFLINE_PROBE and _sb_cache_p.exists():
    try:
        if (time.time() - _sb_cache_p.stat().st_mtime) <= 45.0:
            _sb_cj = json.loads(_sb_cache_p.read_text(encoding="utf-8"))
            if isinstance(_sb_cj, dict) and not _sb_cj.get("error"):
                out["stage_b_attribution"] = _sb_cj
                _sb_cached_ok = True
    except Exception:
        pass
if not _OFFLINE_PROBE and not _sb_cached_ok:
    try:
        _pm_sb = out.get("polymarket_live") or {}
        _br_sb = paa_out.get("budget_and_resources") or {}
        _sb_in_p = pathlib.Path("/tmp/dominus_stageb_in.json")
        _sb_in_p.write_text(json.dumps({
            "grouped_closed": locals().get("grouped_closed") or [],
            "active_positions": locals().get("_act_sb_saved") or {},
            "reconciled_equity_usd": float(_pm_sb.get("equity_usd") or 0.0),
            "starting_lock_equity_usd": float(_pm_sb.get("riskless_lock_start_usd") or 60.92),
            "net_deposits_post_lock_usd": float(_pm_sb.get("net_deposits_post_lock_usd") or 0.0),
            "equity_24h_delta_usd": _pm_sb.get("equity_24h_delta_usd"),
            "daily_infra_cost_usd": float(_vf_sync.get("daily_infra_vm_cost_usd") or (24.0 * 0.0730)),
            "all_time_ai_cost_usd": float(_vf_sync.get("research_ai_cost_usd") or 0.0),
            "daily_ai_cost_usd": float(_br_sb.get("daily_ai_cost_usd") or 0.0),
            "accounting_discrepancy_usd": float(_vf_sync.get("accounting_discrepancy_usd") or 0.0),
            "orphan_orders_count": int(_pm_sb.get("orphan_orders_count") or 0),
            "paused_sleeves": sorted(locals().get("_PAUSED_RB_SET") or set()),
            "now_unix": now_probe_u,
        }), encoding="utf-8")
        _sb_sub_py = (
            "import json, pathlib, sys\n"
            f"root = pathlib.Path({str(root)!r})\n"
            "sys.path.insert(0, str(root))\n"
            "from src.polymarket_research.economic_attribution_ledger import compute_stage_b_attribution_report as _comp_sb\n"
            "kw = json.loads(pathlib.Path('/tmp/dominus_stageb_in.json').read_text(encoding='utf-8'))\n"
            "kw['paused_sleeves'] = set(kw.get('paused_sleeves') or [])\n"
            "kw['vm_hourly_cost_usd'] = 0.0730\n"
            "kw['data_dir'] = root / 'data/polymarket'\n"
            "res = _comp_sb(**kw)\n"
            "pathlib.Path('/tmp/dominus_stageb_cache.json').write_text(json.dumps(res), encoding='utf-8')\n"
        )
        subprocess.run([sys.executable, "-c", _sb_sub_py], check=True, timeout=5, capture_output=True)
        out["stage_b_attribution"] = json.loads(_sb_cache_p.read_text(encoding="utf-8"))
        _sb_cached_ok = True
    except Exception:
        pass
if not _sb_cached_ok:
    try:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from src.polymarket_research.economic_attribution_ledger import compute_stage_b_attribution_report as _comp_sb
        _pm_sb = out.get("polymarket_live") or {}
        _br_sb = paa_out.get("budget_and_resources") or {}
        _act_sb = locals().get("_act_sb_saved") or (s.get("active_positions") if ("s" in locals() and isinstance(s, dict)) else {})
        _grp_sb = locals().get("grouped_closed") or []
        _paus_sb = locals().get("_PAUSED_RB_SET") or set()
        out["stage_b_attribution"] = _comp_sb(
            grouped_closed=_grp_sb,
            active_positions=_act_sb,
            reconciled_equity_usd=float(_pm_sb.get("equity_usd") or 0.0),
            starting_lock_equity_usd=float(_pm_sb.get("riskless_lock_start_usd") or 60.92),
            net_deposits_post_lock_usd=float(_pm_sb.get("net_deposits_post_lock_usd") or 0.0),
            equity_24h_delta_usd=_pm_sb.get("equity_24h_delta_usd"),
            vm_hourly_cost_usd=0.0730,
            daily_infra_cost_usd=float(_vf_sync.get("daily_infra_vm_cost_usd") or (24.0 * 0.0730)),
            all_time_ai_cost_usd=float(_vf_sync.get("research_ai_cost_usd") or 0.0),
            daily_ai_cost_usd=float(_br_sb.get("daily_ai_cost_usd") or 0.0),
            accounting_discrepancy_usd=float(_vf_sync.get("accounting_discrepancy_usd") or 0.0),
            orphan_orders_count=int(_pm_sb.get("orphan_orders_count") or 0),
            paused_sleeves=_paus_sb,
            data_dir=root / "data/polymarket",
            now_unix=now_probe_u,
        )
    except Exception as _sb_exc:
        out["stage_b_attribution"] = {"error": str(_sb_exc)[:200]}

for _k_s7 in ("grouped_closed", "_act_sb_saved", "_grp_sb", "_act_sb", "paa_out", "_fs_det"):
    globals().pop(_k_s7, None)
gc.collect()

# 8. Full-Throttle 14-Family (A..N) Universe Census, Family L Maker Shadow, HarvesterBridge, Projections & Non-Conflated Matrix
_ft_out = {
    "available": False,
    "systemd": out.get("full_throttle_systemd") or {},
    "universe_census": {},
    "opportunity_metrics": {},
    "family_matrix": [],
    "harvester_bridge": {},
    "family_l_maker_shadow": {},
    "segregated_economics": {},
    "top_executable": [],
    "top_dormant_near_arbs": [],
}
_ft_dash_p = root / "data/full_throttle/pipeline/dashboard_latest.json"
if _ft_dash_p.exists() and _ft_dash_p.stat().st_size <= 10 * 1024 * 1024:
    try:
        _ft_raw = None
        if not _OFFLINE_PROBE and _ft_dash_p.stat().st_size > 131072:
            _ft_slim_p = pathlib.Path("/tmp/dominus_ft_dash_slim_cache.json")
            _ft_st = _ft_dash_p.stat()
            _ft_sig = f"{_ft_st.st_mtime_ns}:{_ft_st.st_size}"
            if _ft_slim_p.exists():
                try:
                    _ft_cj = json.loads(_ft_slim_p.read_text(encoding="utf-8"))
                    if isinstance(_ft_cj, dict) and _ft_cj.get("_src_sig") == _ft_sig:
                        _ft_raw = _ft_cj
                except Exception:
                    _ft_raw = None
            if _ft_raw is None:
                try:
                    _ft_sub_py = (
                        "import json, os, pathlib\n"
                        f"src = pathlib.Path({str(_ft_dash_p)!r}); dst = pathlib.Path('/tmp/dominus_ft_dash_slim_cache.json')\n"
                        "st = src.stat(); raw = json.loads(src.read_text(encoding='utf-8'))\n"
                        "s2c = dict(raw.get('section_2c_dormant_opportunity_store') or {}); s2c['closest_near_misses'] = list((s2c.get('closest_near_misses') or [])[:12])\n"
                        "s2d = dict(raw.get('section_2d_hedged_maker_shadow_quoter') or {}); s2d['top_resting_quotes'] = list((s2d.get('top_resting_quotes') or [])[:8]); s2d.pop('resting_quotes', None); s2d.pop('filled_quotes', None)\n"
                        "s2e = dict(raw.get('section_2e_harvester_candidate_bridge') or {}); s2e['emitted_box_ids'] = list((s2e.get('emitted_box_ids') or [])[:12]); s2e.pop('emitted_candidates', None)\n"
                        "slim = {'_src_sig': f'{st.st_mtime_ns}:{st.st_size}', 'schema_version': raw.get('schema_version'), 'generated_at_utc': raw.get('generated_at_utc'), 'execution_mode': raw.get('execution_mode'), 'jurisdiction_gate': raw.get('jurisdiction_gate'), 'campaign_summary': raw.get('campaign_summary'), 'section_1_universe_coverage': raw.get('section_1_universe_coverage'), 'section_1b_proposition_graph': raw.get('section_1b_proposition_graph'), 'section_1c_detector_coverage_by_family': raw.get('section_1c_detector_coverage_by_family'), 'section_2_opportunity_metrics': raw.get('section_2_opportunity_metrics'), 'section_2b_persistence_and_forward_validation': raw.get('section_2b_persistence_and_forward_validation'), 'section_2c_dormant_opportunity_store': s2c, 'section_2d_hedged_maker_shadow_quoter': s2d, 'section_2e_harvester_candidate_bridge': s2e, 'section_3_segregated_economics': raw.get('section_3_segregated_economics'), 'section_3b_portfolio_allocation_48_70_pusd': raw.get('section_3b_portfolio_allocation_48_70_pusd'), 'top_executable_opportunities': list((raw.get('top_executable_opportunities') or [])[:10])}\n"
                        "tmp = pathlib.Path('/tmp/dominus_ft_dash_slim_cache.json.tmp'); tmp.write_text(json.dumps(slim), encoding='utf-8'); os.replace(tmp, dst)\n"
                    )
                    subprocess.run([sys.executable, "-c", _ft_sub_py], check=True, timeout=4, capture_output=True)
                    _ft_raw = json.loads(_ft_slim_p.read_text(encoding="utf-8"))
                except Exception:
                    _ft_raw = None
        if _ft_raw is None:
            _ft_raw = json.loads(_ft_dash_p.read_text(encoding="utf-8"))
        if isinstance(_ft_raw, dict):
            _s1 = _ft_raw.get("section_1_universe_coverage") or {}
            _s1b = _ft_raw.get("section_1b_proposition_graph") or {}
            _s1c = _ft_raw.get("section_1c_detector_coverage_by_family") or {}
            _s2 = _ft_raw.get("section_2_opportunity_metrics") or {}
            _s2b = _ft_raw.get("section_2b_persistence_and_forward_validation") or {}
            _s2c = _ft_raw.get("section_2c_dormant_opportunity_store") or {}
            _s2d = _ft_raw.get("section_2d_hedged_maker_shadow_quoter") or {}
            _s2e = _ft_raw.get("section_2e_harvester_candidate_bridge") or {}
            _s3 = _ft_raw.get("section_3_segregated_economics") or {}
            _s3b = _ft_raw.get("section_3b_portfolio_allocation_48_70_pusd") or {}
            _cs = _ft_raw.get("campaign_summary") or {}
            _gen_u = _parse_utc_epoch(_ft_raw.get("generated_at_utc"))
            _dorm_by_fam = _s2c.get("by_family") or {}
            _fam_rows = []
            for _fc in ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"):
                _fd = _s1c.get(_fc) or {}
                _ca = int(_fd.get("CLASS_A", 0) or 0)
                _cb = int(_fd.get("CLASS_B", 0) or 0)
                _fam_rows.append({
                    "family_code": _fc,
                    "family_name": str(_fd.get("family_name") or f"Family {_fc}"),
                    "owner_track": str(_fd.get("owner_track") or ""),
                    "inspected": int(_fd.get("structures_or_markets_inspected", 0) or 0),
                    "candidates_emitted": int(_fd.get("candidates_emitted", 0) or 0),
                    "class_a": _ca,
                    "class_b": _cb,
                    "class_a_b": _ca + _cb,
                    "class_c": int(_fd.get("CLASS_C", 0) or 0),
                    "rule_traps_blocked": int(_fd.get("CLASS_D", 0) or 0),
                    "class_e": int(_fd.get("CLASS_E", 0) or 0),
                    "dormant_near_misses": int(_fd.get("dormant_near_misses", 0) or 0),
                    "dormant_store_count": int(_dorm_by_fam.get(_fc, 0) or 0),
                    "proven_arbs": int(_fd.get("mathematically_proven_arbs", 0) or 0),
                })
            _c1_p = _s3.get("column_1_paper_theoretical") or {}
            _c2_s = _s3.get("column_2_realistic_forward_shadow") or {}
            _c3_l = _s3.get("column_3_verified_live_wallet_cash") or {}
            _ft_out = {
                "available": True,
                "schema_version": str(_ft_raw.get("schema_version") or "1.0"),
                "generated_at_utc": str(_ft_raw.get("generated_at_utc") or ""),
                "generated_at_et": _fmt_et(_ft_raw.get("generated_at_utc"), "%Y-%m-%d %H:%M:%S"),
                "age_sec": round(max(0.0, now_probe_u - _gen_u), 1) if _gen_u else round(max(0.0, now_probe_u - _ft_dash_p.stat().st_mtime), 1),
                "execution_mode": str(_ft_raw.get("execution_mode") or "SHADOW_ONLY"),
                "jurisdiction_gate": str(_ft_raw.get("jurisdiction_gate") or "CA-ON"),
                "systemd": out.get("full_throttle_systemd") or {},
                "campaign_summary": {
                    "total_cycles_executed": int(_cs.get("total_cycles_executed", 0) or 0),
                    "avg_fast_cycle_wall_sec": round(float(_cs.get("avg_fast_cycle_wall_sec", 0.0) or 0.0), 2),
                    "full_universe_discovery_sweep_sec": round(float(_cs.get("full_universe_discovery_sweep_sec", 0.0) or 0.0), 2),
                    "listing_to_evaluation_latency_ms": round(float(_cs.get("listing_to_evaluation_latency_ms", 0.0) or 0.0), 2),
                    "peak_rss_mib": round(float(_cs.get("peak_rss_mib", 0.0) or 0.0), 2),
                    "swapless_180mib_budget_ok": bool(_cs.get("swapless_180mib_budget_ok", True)),
                    "batched_book_tokens_polled": int(_cs.get("total_batched_book_tokens_polled_across_cycles", 0) or 0),
                },
                "universe_census": {
                    "total_observable_events": int(_s1.get("total_observable_events", 0) or 0),
                    "total_observable_markets": int(_s1.get("total_observable_markets", 0) or 0),
                    "active_unclosed_markets": int(_s1.get("active_unclosed_markets", 0) or 0),
                    "orderbook_enabled_markets": int(_s1.get("orderbook_enabled_markets", 0) or 0),
                    "total_tradable_outcome_tokens": int(_s1.get("total_tradable_outcome_tokens", 0) or 0),
                    "retained_working_events": int(_s1.get("retained_working_events", 0) or 0),
                    "negrisk_events": int(_s1.get("negrisk_events", 0) or 0),
                    "augmented_negrisk_events": int(_s1.get("augmented_negrisk_events", 0) or 0),
                    "fees_enabled_markets": int(_s1.get("fees_enabled_markets", 0) or 0),
                    "uma_status_breakdown": dict(_s1.get("uma_status_breakdown") or {}),
                    "skip_counts": dict(_s1.get("unresolved_or_ineligible_skip_counts") or {}),
                    "d001_frozen_kmia_holdings_quarantined": int(_s1.get("d001_frozen_kmia_holdings_quarantined", 0) or 0),
                    "graph_total_edges": int(_s1b.get("total_edges", 0) or 0),
                    "graph_cross_market_edges": int(_s1b.get("cross_market_edges", 0) or 0),
                    "verified_multi_market_components": int(_s1b.get("verified_multi_market_components", 0) or 0),
                },
                "opportunity_metrics": {
                    "total_candidates_evaluated": int(_s2.get("total_candidates_evaluated", 0) or 0),
                    "mathematically_valid_proofs": int(_s2.get("mathematically_valid_proofs", 0) or 0),
                    "class_counts": dict(_s2.get("class_counts") or {}),
                    "d007_quarantined_3plus_leg_count": int(_s2.get("d007_quarantined_3plus_leg_count", 0) or 0),
                    "rule_mismatch_rejections_prevented": int(_s2.get("rule_mismatch_rejections_prevented", 0) or 0),
                    "forward_validations_completed": int(_s2b.get("forward_validations_completed", 0) or 0),
                    "forward_validations_survived": int(_s2b.get("forward_validations_survived", 0) or 0),
                    "forward_survival_rate": round(float(_s2b.get("forward_survival_rate", 0.0) or 0.0), 4),
                    "forward_validated_net_pnl_usd": round(float(_s2b.get("forward_validated_net_pnl_usd", 0.0) or 0.0), 4),
                    "dormant_active_count": int(_s2c.get("active_dormant_count", 0) or 0),
                    "dormant_within_50_bps_count": int(_s2c.get("within_50_bps_count", 0) or 0),
                    "dormant_within_150_bps_count": int(_s2c.get("within_150_bps_count", 0) or 0),
                    "dormant_rescans_triggered": int(_s2c.get("total_rescans_triggered", 0) or 0),
                    "dormant_promotions": int(_s2c.get("total_promotions_to_executable", 0) or 0),
                },
                "family_matrix": _fam_rows,
                "harvester_bridge": {
                    "enabled": bool(_s2e.get("enabled", False)),
                    "candidates_emitted_this_cycle": int(_s2e.get("candidates_emitted_this_cycle", 0) or 0),
                    "total_emitted_across_campaign": int(_s2e.get("total_emitted_across_campaign", 0) or 0),
                    "total_dedupe_suppressed": int(_s2e.get("total_dedupe_suppressed", 0) or 0),
                    "reconciled_nav_used_usd": round(float(_s2e.get("reconciled_nav_used_usd", 0.0) or 0.0), 2),
                    "d007_15pct_concentration_cap_usd": round(float(_s2e.get("d007_15pct_concentration_cap_usd", 0.0) or 0.0), 2),
                    "skipped_by_reason": dict(_s2e.get("skipped_by_reason") or {}),
                    "emitted_box_ids": list((_s2e.get("emitted_box_ids") or [])[:12]),
                },
                "family_l_maker_shadow": {
                    "resting_passive_quotes_count": int(_s2d.get("resting_passive_quotes_count", 0) or 0),
                    "total_quotes_posted": int(_s2d.get("total_quotes_posted", 0) or 0),
                    "total_quotes_evaluated_next_cycle": int(_s2d.get("total_quotes_evaluated_next_cycle", 0) or 0),
                    "filled_hedged_locks_count": int(_s2d.get("filled_hedged_locks_count", 0) or 0),
                    "adverse_selected_fills_count": int(_s2d.get("adverse_selected_fills_count", 0) or 0),
                    "expired_unfilled_count": int(_s2d.get("expired_unfilled_count", 0) or 0),
                    "maker_fee_bps": float(_s2d.get("maker_fee_bps", 0.0) or 0.0),
                    "locked_spread_shadow_pnl_ex_rebate_usd": round(float(_s2d.get("locked_spread_shadow_pnl_ex_rebate_usd", 0.0) or 0.0), 4),
                    "adverse_selection_unwind_bleed_usd": round(float(_s2d.get("adverse_selection_unwind_bleed_usd", 0.0) or 0.0), 4),
                    "net_post_adverse_shadow_pnl_ex_rebate_usd": round(float(_s2d.get("net_post_adverse_shadow_pnl_ex_rebate_usd", 0.0) or 0.0), 4),
                    "estimated_maker_rebate_15_to_25pct_usd": round(float(_s2d.get("estimated_maker_rebate_15_to_25pct_usd", 0.0) or 0.0), 4),
                    "strictly_segregated_from_locked_cash": True,
                    "top_resting_quotes": [
                        {
                            "quote_id": str(q.get("quote_id") or ""),
                            "source_family": str(q.get("source_family") or "L"),
                            "title_summary": str(q.get("title_summary") or "")[:72],
                            "quote_bid_px": round(float(q.get("quote_bid_px", 0.0) or 0.0), 4),
                            "hedge_ask_px": round(float(q.get("initial_hedge_ask_net_px", 0.0) or 0.0), 4),
                            "locked_edge_bps": round(float(q.get("locked_edge_bps_if_filled", 0.0) or 0.0), 1),
                            "shares": round(float(q.get("shares", 0.0) or 0.0), 2),
                        }
                        for q in (_s2d.get("top_resting_quotes") or [])[:8]
                        if isinstance(q, dict)
                    ],
                },
                "segregated_economics": {
                    "paper_class_a_b_usd": round(float(_c1_p.get("proven_class_a_b_paper_usd", 0.0) or 0.0), 2),
                    "paper_class_c_ev_usd": round(float(_c1_p.get("class_c_conditional_ev_sum_usd", 0.0) or 0.0), 2),
                    "realistic_l2_executable_sum_usd": round(float(_c2_s.get("unallocated_l2_executable_sum_usd", 0.0) or 0.0), 2),
                    "realistic_post_latency_sum_usd": round(float(_c2_s.get("unallocated_post_latency_sum_usd", 0.0) or 0.0), 2),
                    "portfolio_allocated_on_floor_nav_usd": round(float(_s3b.get("total_allocated_capital_usd", 0.0) or 0.0), 2),
                    "portfolio_guaranteed_l2_net_usd": round(float(_s3b.get("portfolio_guaranteed_l2_net_usd", 0.0) or 0.0), 4),
                    "portfolio_realizable_bps_per_hr": round(float(_s3b.get("portfolio_realizable_bps_per_hr", 0.0) or 0.0), 2),
                    "verified_live_wallet_cash_usd": round(float(_c3_l.get("liquid_pusd_cash_usd", (out.get("polymarket_live") or {}).get("wallet_cash_usd", 0.0)) or 0.0), 2),
                },
                "top_executable": [
                    {
                        "candidate_id": str(o.get("candidate_id") or ""),
                        "family_code": str(o.get("family_code") or ""),
                        "opportunity_class": str(o.get("opportunity_class") or ""),
                        "title_summary": str(o.get("title_summary") or "")[:78],
                        "net_edge_bps": round(float(o.get("l2_net_edge_bps", o.get("net_edge_bps", 0.0)) or 0.0), 1),
                        "bps_per_hr": round(float(o.get("bps_per_hr", 0.0) or 0.0), 1),
                        "max_notional_usd": round(float(o.get("max_executable_notional_usd", o.get("notional_usd", 0.0)) or 0.0), 2),
                    }
                    for o in (_ft_raw.get("top_executable_opportunities") or [])[:10]
                    if isinstance(o, dict)
                ],
                "top_dormant_near_arbs": [
                    {
                        "candidate_id": str(nm.get("candidate_id") or ""),
                        "family_code": str(nm.get("family_code") or ""),
                        "title_summary": str(nm.get("title_summary") or "")[:72],
                        "gap_to_breakeven_bps": round(float(nm.get("gap_to_breakeven_bps", 0.0) or 0.0), 1),
                        "dormant_reason": str(nm.get("dormant_reason") or ""),
                        "times_observed": int(nm.get("times_observed", 0) or 0),
                        "times_rescanned_on_shift": int(nm.get("times_rescanned_on_shift", 0) or 0),
                    }
                    for nm in (_s2c.get("closest_near_misses") or [])[:12]
                    if isinstance(nm, dict)
                ],
            }
        for _k_ft in ("_ft_raw", "_s1", "_s1b", "_s1c", "_s2", "_s2b", "_s2c", "_s2d", "_s2e", "_s3", "_s3b", "_cs"):
            globals().pop(_k_ft, None)
        gc.collect()
    except Exception as _ft_exc:
        _ft_out["error"] = str(_ft_exc)[:200]
out["full_throttle"] = _ft_out

# Daily Projections (P25 Conservative / P50 Base Finland VM / P75 Upside + $150/$253/$500/$5,000 Milestones — Non-Cash Model)
_proj_out = {"available": False, "strictly_projected_non_cash": True}
_proj_p = root / "data/polymarket/live_daily_projections.json"
if _proj_p.exists() and _proj_p.stat().st_size <= 4 * 1024 * 1024:
    try:
        _pr_j = json.loads(_proj_p.read_text(encoding="utf-8"))
        if isinstance(_pr_j, dict):
            _sh_u = _pr_j.get("summary_horizons_usd") or {}
            _ms_raw = _pr_j.get("milestone_eta_days") or {}
            _sched = _pr_j.get("day_by_day_schedule") or []
            _anch = _pr_j.get("anchor_live_state") or {}
            _gen_pu = _parse_utc_epoch(_pr_j.get("generated_at_utc"))

            _anchor_nav_m = float(
                _anch.get("reconciled_floor_nav_usd")
                or _anch.get("liquid_working_cash_usd")
                or (out.get("polymarket_live") or {}).get("guaranteed_redemption_equity_usd")
                or 48.70
            )
            _hz_knots = (
                (1, "day_1"),
                (7, "day_7"),
                (14, "day_14"),
                (30, "day_30"),
                (60, "day_60"),
                (90, "day_90"),
                (180, "day_180"),
                (365, "day_365"),
            )

            def _resolve_milestone_eta(target_usd: float, alias_keys: tuple) -> dict:
                _res_m = {"target_usd": target_usd, "p25_day": None, "p25_date_utc": None, "p50_day": None, "p50_date_utc": None, "p75_day": None, "p75_date_utc": None}
                for _ak in alias_keys:
                    if isinstance(_ms_raw.get(_ak), dict) and _ms_raw[_ak]:
                        _d_m = dict(_ms_raw[_ak])
                        for _pk in ("p25", "p50", "p75"):
                            if _d_m.get(f"{_pk}_day") is not None:
                                _res_m[f"{_pk}_day"] = int(_d_m[f"{_pk}_day"])
                                _res_m[f"{_pk}_date_utc"] = _d_m.get(f"{_pk}_date_utc")
                        break
                for _row_d in _sched:
                    if not isinstance(_row_d, dict):
                        continue
                    _dy = _row_d.get("day")
                    _dt_u = _row_d.get("date_utc")
                    for _pk, _ek in (("p25", "p25_end_equity_usd"), ("p50", "p50_end_equity_usd"), ("p75", "p75_end_equity_usd")):
                        if _res_m[f"{_pk}_day"] is None and float(_row_d.get(_ek) or 0.0) >= target_usd:
                            _res_m[f"{_pk}_day"] = int(_dy) if _dy is not None else None
                            _res_m[f"{_pk}_date_utc"] = str(_dt_u or "")
                # Interpolate across summary_horizons_usd (day_1..day_365) for milestones reached after day_by_day_schedule window
                for _pk in ("p25", "p50", "p75"):
                    if _res_m[f"{_pk}_day"] is not None:
                        continue
                    _prev_d, _prev_eq = 0, max(0.01, _anchor_nav_m)
                    for _kd, _kk in _hz_knots:
                        _kh = _sh_u.get(_kk)
                        if not isinstance(_kh, dict):
                            continue
                        _keq = float(_kh.get(f"{_pk}_equity") or 0.0)
                        if _keq <= 0.0:
                            continue
                        if _keq >= target_usd:
                            if _prev_eq >= target_usd or _keq <= _prev_eq:
                                _est_d = _kd
                            else:
                                _frac = math.log(target_usd / max(0.01, _prev_eq)) / max(1e-9, math.log(_keq / max(0.01, _prev_eq)))
                                _est_d = max(1, int(round(_prev_d + min(1.0, max(0.0, _frac)) * (_kd - _prev_d))))
                            _res_m[f"{_pk}_day"] = _est_d
                            if _gen_pu:
                                _res_m[f"{_pk}_date_utc"] = datetime.fromtimestamp(_gen_pu + _est_d * 86400.0, tz=timezone.utc).strftime("%Y-%m-%d")
                            break
                        _prev_d, _prev_eq = _kd, _keq
                return _res_m

            _horizons_clean = {}
            for _hk in ("day_1", "day_7", "day_14", "day_30", "day_60", "day_90", "day_180", "day_365"):
                if isinstance(_sh_u.get(_hk), dict):
                    _hd = _sh_u[_hk]
                    _horizons_clean[_hk] = {
                        "date_utc": str(_hd.get("date_utc") or ""),
                        "p25_equity": round(float(_hd.get("p25_equity", 0.0) or 0.0), 2),
                        "p50_equity": round(float(_hd.get("p50_equity", 0.0) or 0.0), 2),
                        "p75_equity": round(float(_hd.get("p75_equity", 0.0) or 0.0), 2),
                        "p50_daily_pnl": round(float(_hd.get("p50_daily_pnl", 0.0) or 0.0), 2),
                        "p50_net_profit": round(float(_hd.get("p50_net_profit", 0.0) or 0.0), 2),
                        "vm_cost_cum_usd": round(float(_hd.get("vm_cost_cum_usd", 0.0) or 0.0), 2),
                        "p25_net_after_vm_usd": round(float(_hd.get("p25_net_after_vm_usd", 0.0) or 0.0), 2) if _hd.get("p25_net_after_vm_usd") is not None else None,
                        "p50_net_after_vm_usd": round(float(_hd.get("p50_net_after_vm_usd", 0.0) or 0.0), 2) if _hd.get("p50_net_after_vm_usd") is not None else None,
                        "p75_net_after_vm_usd": round(float(_hd.get("p75_net_after_vm_usd", 0.0) or 0.0), 2) if _hd.get("p75_net_after_vm_usd") is not None else None,
                    }
            _d1_row = _sched[0] if (_sched and isinstance(_sched[0], dict)) else {}
            _proj_out = {
                "available": True,
                "strictly_projected_non_cash": True,
                "model_version": str(_pr_j.get("model_version") or "v5.2"),
                "generated_at_utc": str(_pr_j.get("generated_at_utc") or ""),
                "generated_at_et": _fmt_et(_pr_j.get("generated_at_utc"), "%Y-%m-%d %H:%M:%S"),
                "age_sec": round(max(0.0, now_probe_u - _gen_pu), 1) if _gen_pu else round(max(0.0, now_probe_u - _proj_p.stat().st_mtime), 1),
                "anchor_floor_nav_usd": round(float(_anch.get("reconciled_floor_nav_usd") or _anch.get("liquid_working_cash_usd") or (out.get("polymarket_live") or {}).get("guaranteed_redemption_equity_usd") or 0.0), 2),
                "day1_rates": {
                    "p25_daily_usd": round(float(_d1_row.get("p25_daily_pnl_usd", 0.0) or 0.0), 2),
                    "p50_daily_usd": round(float(_d1_row.get("p50_daily_pnl_usd", 0.0) or 0.0), 2),
                    "p75_daily_usd": round(float(_d1_row.get("p75_daily_pnl_usd", 0.0) or 0.0), 2),
                },
                "horizons": _horizons_clean,
                "milestones": {
                    "usd_150": _resolve_milestone_eta(150.0, ("usd_150",)),
                    "usd_253": _resolve_milestone_eta(253.0, ("usd_253", "usd_250")),
                    "usd_500": _resolve_milestone_eta(500.0, ("usd_500",)),
                    "usd_5000": _resolve_milestone_eta(5000.0, ("usd_5000",)),
                },
                "floor_48_70_reference": dict(_pr_j.get("production_reconciled_48_70_floor_reference_usd") or {}),
                "post_kmia_scenarios": dict(_pr_j.get("post_nov14_miami_scenarios_usd") or _pr_j.get("kmia_settlement_scenarios_usd") or {}),
                "compliance_note": str(_pr_j.get("p75_jurisdiction_compliance_note") or "CA-ON legal regulated cross-venue only; 0% proxy/spoofing."),
            }
        for _k_pr in ("_pr_j", "_sh_u", "_ms_raw", "_sched", "_anch", "_d1_row"):
            globals().pop(_k_pr, None)
        gc.collect()
    except Exception as _pr_exc:
        _proj_out["error"] = str(_pr_exc)[:200]
out["daily_projections"] = _proj_out

# Build Unified Real-Trading vs Realistic-Shadow Strategy Performance Matrix (Principle 8 Strict Non-Conflation)
_pm_m = out.get("polymarket_live") or {}
_hf_m = _pm_m.get("harvester_funnel") or {}
_ps_f_m = _hf_m.get("per_sleeve_funnel") or {}
_ipc_s_m = _hf_m.get("ipc_tail_by_sleeve") or {}
_ls_by_id = {str(x.get("sleeve") or ""): x for x in (_pm_m.get("live_strategies") or []) if isinstance(x, dict)}
_ro_by_slv = {}
for _ro_x in (_pm_m.get("resting_orders") or []):
    if isinstance(_ro_x, dict):
        _rsk = str(_ro_x.get("sleeve") or "BOND1_UMA_RESOLUTION_CARRY")
        _ro_by_slv[_rsk] = _ro_by_slv.get(_rsk, 0) + 1
_a124_by_id = {str(x.get("sleeve") or ""): x for x in ((out.get("alpha124") or {}).get("sleeves") or []) if isinstance(x, dict)}
_fam_by_c = {str(x.get("family_code") or ""): x for x in (_ft_out.get("family_matrix") or []) if isinstance(x, dict)}
_fl_mkr = _ft_out.get("family_l_maker_shadow") or {}
_hb_ft = _ft_out.get("harvester_bridge") or {}
_xv_m = ((out.get("v6_expansion") or {}).get("cross_venue_shadow")) or {}

def _agg_real_sleeves(slv_keys, default_gate="LIVE ARMED"):
    _op, _rc, _ew, _el, _ep, _rec, _exe, _rej = 0, 0, 0, 0, 0.0, 0, 0, 0
    _gates = []
    for _sk in slv_keys:
        _st = _ls_by_id.get(_sk)
        if _st:
            _op += int(_st.get("open", 0) or 0)
            _ew += int(_st.get("epoch_w", 0) or 0)
            _el += int(_st.get("epoch_l", 0) or 0)
            _ep = round(_ep + float(_st.get("epoch_pnl", 0.0) or 0.0), 2)
            _dsc = str(_st.get("desc") or "")
            if _dsc:
                _gates.append("PAUSED" if _dsc.startswith("PAUSED") else ("GATED" if _dsc.startswith("GATED") else "LIVE ACTIVE"))
        _rc += int(_ro_by_slv.get(_sk, 0) or 0)
        _psf = _ps_f_m.get(_sk) if isinstance(_ps_f_m.get(_sk), dict) else {}
        _rec += max(int(_ipc_s_m.get(_sk, 0) or 0), int(_psf.get("received", 0) or 0))
        if _psf:
            _exe += int(_psf.get("executed", int(_psf.get("taker_executed", 0) or 0) + int(_psf.get("maker_filled", 0) or 0)) or 0)
            _rej += int(_psf.get("rejected", 0) or 0)
    # Also sweep any FT_* live_strategies / per_sleeve_funnel rows when aggregating FT_BRIDGE
    if "FT_*" in slv_keys:
        for _k_ls, _v_ls in _ls_by_id.items():
            if _k_ls.upper().startswith("FT_"):
                _op += int(_v_ls.get("open", 0) or 0)
                _ew += int(_v_ls.get("epoch_w", 0) or 0)
                _el += int(_v_ls.get("epoch_l", 0) or 0)
                _ep = round(_ep + float(_v_ls.get("epoch_pnl", 0.0) or 0.0), 2)
        _ft_rec_sum, _ft_exe_sum, _ft_rej_sum = 0, 0, 0
        for _k_ps, _v_ps in _ps_f_m.items():
            if isinstance(_v_ps, dict) and (_k_ps.upper().startswith("FT_") or int(_v_ps.get("ft_bridge", 0) or 0) > 0):
                _ft_rec_sum += int(_v_ps.get("ft_bridge", _v_ps.get("received", 0)) or 0)
                _ft_exe_sum += int(_v_ps.get("executed", int(_v_ps.get("taker_executed", 0) or 0) + int(_v_ps.get("maker_filled", 0) or 0)) or 0)
                _ft_rej_sum += int(_v_ps.get("rejected", 0) or 0)
        _rec = max(_rec + _ft_rec_sum, int(_hf_m.get("ft_received", 0) or 0))
        _exe = max(_exe + _ft_exe_sum, int(_hf_m.get("ft_executed", 0) or 0))
        _rej = max(_rej + _ft_rej_sum, int(_hf_m.get("ft_rejected", 0) or 0))
    _gate_lbl = "LIVE ACTIVE" if "LIVE ACTIVE" in _gates else (_gates[0] if _gates else default_gate)
    return {
        "gate": _gate_lbl,
        "open_positions": _op,
        "resting_clob_orders": _rc,
        "candidates_received": _rec,
        "executed": _exe,
        "rejected": _rej,
        "wins": _ew,
        "losses": _el,
        "realized_wallet_pnl_usd": _ep,
    }

def _agg_shadow_sleeves(slv_keys, fam_codes=()):
    _so, _sw, _sl, _spnl, _insp, _c_ab, _traps = 0, 0, 0, 0.0, 0, 0, 0
    for _sk in slv_keys:
        _sa = _a124_by_id.get(_sk)
        if _sa:
            _so += int(_sa.get("open", 0) or 0) + int(_sa.get("pending_quotes", 0) or 0)
            _sw += int(_sa.get("wins", 0) or 0)
            _sl += int(_sa.get("losses", 0) or 0)
            _spnl = round(_spnl + float(_sa.get("t1000_pnl_usd", 0.0) or 0.0), 2)
    for _fc in fam_codes:
        _fm = _fam_by_c.get(_fc)
        if _fm:
            _insp += int(_fm.get("inspected", 0) or 0)
            _c_ab += int(_fm.get("class_a_b", 0) or 0)
            _traps += int(_fm.get("rule_traps_blocked", 0) or 0)
    return {
        "inspected": _insp,
        "proven_class_a_b": _c_ab,
        "rule_traps_blocked": _traps,
        "shadow_open_or_resting": _so,
        "shadow_wins": _sw,
        "shadow_losses": _sl,
        "shadow_net_pnl_usd": _spnl,
    }

out["strategy_comparison_matrix"] = {
    "strictly_non_conflated": True,
    "rows": [
        {
            "strategy_key": "FT_LIVE_BRIDGE",
            "label": "FT_* Full-Throttle Live Bridge (Families A..K -> Harvester)",
            "real_trading": _agg_real_sleeves(("FT_*",), default_gate="BRIDGE ARMED" if _hb_ft.get("enabled") else "SHADOW ONLY"),
            "realistic_shadow": {
                "inspected": sum(int(x.get("inspected", 0) or 0) for x in (_ft_out.get("family_matrix") or [])),
                "proven_class_a_b": sum(int(x.get("class_a_b", 0) or 0) for x in (_ft_out.get("family_matrix") or [])),
                "rule_traps_blocked": int((_ft_out.get("opportunity_metrics") or {}).get("rule_mismatch_rejections_prevented", 0) or 0),
                "shadow_open_or_resting": int(_hb_ft.get("total_emitted_across_campaign", 0) or 0),
                "shadow_wins": int((_ft_out.get("opportunity_metrics") or {}).get("forward_validations_survived", 0) or 0),
                "shadow_losses": max(0, int((_ft_out.get("opportunity_metrics") or {}).get("forward_validations_completed", 0) or 0) - int((_ft_out.get("opportunity_metrics") or {}).get("forward_validations_survived", 0) or 0)),
                "shadow_net_pnl_usd": round(float((_ft_out.get("opportunity_metrics") or {}).get("forward_validated_net_pnl_usd", 0.0) or 0.0), 2),
                "note": f"Dormant <=50bps: {(_ft_out.get('opportunity_metrics') or {}).get('dormant_within_50_bps_count', 0)}",
            },
        },
        {
            "strategy_key": "FAMILY_L_MAKER",
            "label": "Family L Hedged Passive Maker (0 bps + 15-25% Rebate)",
            "real_trading": _agg_real_sleeves(("D1_MAKER_ANCHOR_BOX", "ZF_INTRADAY_MAKER_BOX"), default_gate="SHADOW VALIDATING"),
            "realistic_shadow": {
                "inspected": int((_fam_by_c.get("L") or {}).get("inspected", 0) or _fl_mkr.get("total_quotes_posted", 0) or 0),
                "proven_class_a_b": int((_fam_by_c.get("L") or {}).get("class_a_b", 0) or 0),
                "rule_traps_blocked": int((_fam_by_c.get("L") or {}).get("rule_traps_blocked", 0) or 0),
                "shadow_open_or_resting": int(_fl_mkr.get("resting_passive_quotes_count", 0) or 0),
                "shadow_wins": int(_fl_mkr.get("filled_hedged_locks_count", 0) or 0),
                "shadow_losses": int(_fl_mkr.get("adverse_selected_fills_count", 0) or 0),
                "shadow_net_pnl_usd": round(float(_fl_mkr.get("net_post_adverse_shadow_pnl_ex_rebate_usd", 0.0) or 0.0), 2),
                "note": f"Ex-rebate +${float(_fl_mkr.get('net_post_adverse_shadow_pnl_ex_rebate_usd', 0.0) or 0.0):.2f} (+${float(_fl_mkr.get('estimated_maker_rebate_15_to_25pct_usd', 0.0) or 0.0):.2f} est. rebate)",
            },
        },
        {
            "strategy_key": "BOND1_CARRY",
            "label": "BOND1 / BOND2 UMA Resolution Carry (0% Maker Fee, Fam K)",
            "real_trading": _agg_real_sleeves(("BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"), default_gate="LIVE ACTIVE"),
            "realistic_shadow": _agg_shadow_sleeves(("BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"), fam_codes=("K",)),
        },
        {
            "strategy_key": "MKR_LOCK1_CLINCH",
            "label": "MKR_LOCK1 / W_PRUNE1 Post-Clinch & Weather Prune (Fam H/K)",
            "real_trading": _agg_real_sleeves(("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "MKR_REWARD_LOCKED_CARRY", "W_PRUNE1_DEAD_NO_BOND", "W_PRUNE1_DEAD_NO_SWEEPER"), default_gate="LIVE ACTIVE"),
            "realistic_shadow": _agg_shadow_sleeves(("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "MKR_REWARD_LOCKED_CARRY", "W_PRUNE1_DEAD_NO_BOND", "W1_SOLAR_PEAK_LOCK"), fam_codes=("H",)),
        },
        {
            "strategy_key": "CAL1_TEMPORAL",
            "label": "CAL1 Deadline Survival & Temporal Dominance (Fam E)",
            "real_trading": _agg_real_sleeves(("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",), default_gate="LIVE ACTIVE"),
            "realistic_shadow": _agg_shadow_sleeves(("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",), fam_codes=("E",)),
        },
        {
            "strategy_key": "COND1_LOGICAL",
            "label": "COND1 / LP1 Macro & Cross-Market Implication (Fam D)",
            "real_trading": _agg_real_sleeves(("COND1_MACRO_PARTITION_BOX", "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", "FED1_CENTRAL_BANK_LP_BOX"), default_gate="LIVE ACTIVE"),
            "realistic_shadow": _agg_shadow_sleeves(("COND1_MACRO_PARTITION_BOX", "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", "FED1_CENTRAL_BANK_LP_BOX", "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"), fam_codes=("D", "I")),
        },
        {
            "strategy_key": "C1_COMPLETE_SET",
            "label": "C1 Binary Complete-Set & Split/Merge Recycling (Fam A/J)",
            "real_trading": _agg_real_sleeves(("C1_BINARY_COMPLETE_SET", "PRE_SPLIT_OVERROUND_MACHINE_GUN", "C1_BINARY_COMPLEMENT_BOX"), default_gate="LIVE ACTIVE"),
            "realistic_shadow": _agg_shadow_sleeves(("C1_BINARY_COMPLETE_SET", "PRE_SPLIT_OVERROUND_MACHINE_GUN", "HEDGED_PRESPLIT_CONV_GUN"), fam_codes=("A", "J")),
        },
        {
            "strategy_key": "D1_STRIKE_ORACLE",
            "label": "D1 Same-Oracle & Strike-Ladder Dominance (Fam F)",
            "real_trading": _agg_real_sleeves(("D1_SAME_ORACLE_DOMINANCE_BOX", "D1_QUIET_BOOK_BOX"), default_gate="LIVE ACTIVE"),
            "realistic_shadow": _agg_shadow_sleeves(("D1_SAME_ORACLE_DOMINANCE_BOX", "D1_QUIET_BOOK_BOX", "CM_B3_PYTH_BARRIER_BOX"), fam_codes=("F",)),
        },
        {
            "strategy_key": "NR_M1_NR2_SLATE",
            "label": "NR_M1 / NR2 NegRisk Slate & Convert-NO Subset (Fam B/C)",
            "real_trading": _agg_real_sleeves(("NR2_CONVERT_NO_SUBSET_ARB", "NR_M1_DEAD_SEED_OVERROUND", "NR_M1_NEGRISK_SLATE_SWEEP"), default_gate="LIVE ACTIVE"),
            "realistic_shadow": _agg_shadow_sleeves(("NR2_CONVERT_NO_SUBSET_ARB", "NR_M1_DEAD_SEED_OVERROUND", "NR0_ZERO_FEE_SLATE_ARB", "NR_CONV_NO_BASKET_ARB", "N1_NEGRISK_CROSS_BOX"), fam_codes=("B", "C")),
        },
        {
            "strategy_key": "STAGE_G_CROSS_VENUE",
            "label": "Stage G 6-Venue Cross-Venue Shadow (Fam N: STX CAD / ForecastEx)",
            "real_trading": {
                "gate": "SHADOW GATING (<$253)",
                "open_positions": 0,
                "resting_clob_orders": 0,
                "candidates_received": 0,
                "executed": 0,
                "rejected": 0,
                "wins": 0,
                "losses": 0,
                "realized_wallet_pnl_usd": 0.0,
            },
            "realistic_shadow": {
                "inspected": int(_xv_m.get("live_markets_seen", 0) or 0) + int((_fam_by_c.get("N") or {}).get("inspected", 0) or 0),
                "proven_class_a_b": int(_xv_m.get("matched_pairs_seen", 0) or 0),
                "rule_traps_blocked": int((_fam_by_c.get("N") or {}).get("rule_traps_blocked", 0) or 0),
                "shadow_open_or_resting": 0,
                "shadow_wins": sum(int(e.get("shadow_wins", 0) or 0) for e in ((out.get("v6_expansion") or {}).get("engines") or []) if isinstance(e, dict) and str(e.get("strategy_id") or "").startswith("XV_")),
                "shadow_losses": sum(int(e.get("shadow_losses", 0) or 0) for e in ((out.get("v6_expansion") or {}).get("engines") or []) if isinstance(e, dict) and str(e.get("strategy_id") or "").startswith("XV_")),
                "shadow_net_pnl_usd": 0.0,
                "note": f"Cycle #{_xv_m.get('cycles_completed', 0)} ({_xv_m.get('network_mode', 'init')})",
            },
        },
    ],
}

for _tmp_k in ("s", "_a_raw_doc", "_mir_raw_doc", "a", "closed_all", "closed", "closed_norm", "grouped_closed", "_tail_lines", "_recent_ipc_cands", "_sf_rows"):
    globals().pop(_tmp_k, None)
gc.collect()
try:
    ctypes.CDLL("libc.so.6").malloc_trim(0)
except Exception:
    pass
_probe_rss_mib = None
_probe_rss_anon_mib = None
try:
    for _sln in pathlib.Path("/proc/self/status").read_text().splitlines():
        if _sln.startswith("VmRSS:"):
            _probe_rss_mib = round(int(_sln.split()[1]) / 1024.0, 2)
        elif _sln.startswith("RssAnon:"):
            _probe_rss_anon_mib = round(int(_sln.split()[1]) / 1024.0, 2)
except Exception:
    pass
out["probe_rss_anon_mib"] = _probe_rss_anon_mib
out["probe_rss_mib"] = _probe_rss_anon_mib if _probe_rss_anon_mib is not None else _probe_rss_mib
out["probe_vmrss_total_mib"] = _probe_rss_mib

print(json.dumps(out))
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>DOMINUS — RISKLESS PAA COMMAND CENTER v6.3</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  :root {
    --bg: #070b12;
    --bg-elev: #0d1421;
    --panel: #111927;
    --panel-hi: #152033;
    --border: #22314a;
    --border-hi: #2f4b73;
    --text: #e6edf3;
    --muted: #8b9bb4;
    --green: #2ea043;
    --green-bright: #3fb950;
    --cyan: #39d0d8;
    --red: #f85149;
    --amber: #d29922;
    --blue: #58a6ff;
    --purple: #bc8cff;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 16px 20px 28px 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, monospace;
    background: radial-gradient(circle at 15% 0%, #0e192d 0%, var(--bg) 42%);
    color: var(--text);
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(180deg, rgba(21,32,51,0.92), rgba(13,20,33,0.92));
    border: 1px solid var(--border-hi);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 10px;
    box-shadow: 0 6px 22px rgba(0,0,0,0.32);
  }
  h1 { font-size: 17px; margin: 0; letter-spacing: 0.5px; display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--green-bright); box-shadow: 0 0 10px var(--green-bright); display: inline-block; }
  .lock-badge {
    font-size: 11px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 999px;
    background: rgba(63,185,80,0.16);
    color: var(--green-bright);
    border: 1px solid rgba(63,185,80,0.48);
    letter-spacing: 0.4px;
  }
  .sub { color: var(--muted); font-size: 11.5px; margin-top: 3px; }
  .spots { display: flex; gap: 8px; align-items: center; font-size: 12px; flex-wrap: wrap; }
  .spot-chip { background: #141e30; border: 1px solid var(--border); border-radius: 6px; padding: 5px 9px; }
  .nav-tabs {
    display: flex;
    gap: 7px;
    flex-wrap: wrap;
    margin-bottom: 14px;
    padding-bottom: 4px;
  }
  .tab-btn {
    background: #121b2b;
    color: var(--muted);
    border: 1px solid var(--border);
    padding: 6px 13px;
    font-size: 11.5px;
    font-weight: 600;
    border-radius: 7px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .tab-btn:hover { color: var(--text); border-color: var(--border-hi); background: #18243a; }
  .tab-btn.active {
    background: linear-gradient(180deg, #1f6feb, #1856b8);
    color: #fff;
    border-color: #58a6ff;
    box-shadow: 0 0 12px rgba(31,111,235,0.35);
  }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(225px, 1fr)); gap: 12px; margin-bottom: 15px; }
  .card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 9px;
    padding: 13px 15px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.22);
  }
  .card-hero {
    background: linear-gradient(180deg, #132034 0%, #101928 100%);
    border: 1px solid #2b4a70;
  }
  .card .label { color: var(--muted); font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.65px; font-weight: 600; }
  .card .val { font-size: 22px; font-weight: 700; margin-top: 5px; line-height: 1.2; }
  .pos { color: var(--green-bright); }
  .cyan { color: var(--cyan); }
  .neg { color: var(--red); }
  .warn { color: var(--amber); }
  .two-col { display: grid; grid-template-columns: 1.28fr 1fr; gap: 15px; margin-bottom: 15px; }
  .three-col { display: grid; grid-template-columns: 1fr 1.15fr 1.25fr; gap: 14px; }
  @media (max-width: 1180px) { .three-col { grid-template-columns: 1fr; } }
  @media (max-width: 1020px) { .two-col { grid-template-columns: 1fr; } }
  .ctx-bar-bg { display: inline-block; width: 72px; height: 8px; background: #1a2436; border-radius: 4px; overflow: hidden; vertical-align: middle; margin-left: 5px; border: 1px solid var(--border); }
  .ctx-bar-fg { height: 100%; background: var(--green-bright); transition: width 0.3s ease; }
  .util-bar { width: 100%; height: 6px; background: #192336; border-radius: 4px; overflow: hidden; margin-top: 6px; border: 1px solid var(--border); }
  .util-fill { height: 100%; background: linear-gradient(90deg, #2ea043, #39d0d8); transition: width 0.35s ease; }
  .g8-bar { display: inline-block; width: 44px; height: 6px; background: #1b2538; border-radius: 3px; overflow: hidden; vertical-align: middle; margin-right: 5px; }
  .g8-fill { height: 100%; background: var(--green-bright); }
  h2 { font-size: 12.5px; margin: 0 0 9px 0; color: var(--blue); text-transform: uppercase; letter-spacing: 0.55px; }
  table { width: 100%; border-collapse: collapse; font-size: 11.8px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid rgba(34,49,74,0.75); }
  th { color: var(--muted); font-weight: 600; font-size: 11px; background: #0d1421; position: sticky; top: 0; z-index: 3; box-shadow: inset 0 -1px 0 var(--border); }
  tbody tr:hover { background: rgba(88,166,255,0.045); }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10.8px; font-weight: 600; white-space: nowrap; }
  .pill-ok { background: rgba(46,160,67,0.2); color: var(--green-bright); border: 1px solid rgba(63,185,80,0.45); }
  .pill-bad { background: rgba(248,81,73,0.2); color: var(--red); border: 1px solid rgba(248,81,73,0.42); }
  .pill-warn { background: rgba(210,153,34,0.2); color: var(--amber); border: 1px solid rgba(210,153,34,0.45); }
  .pill-info { background: rgba(88,166,255,0.16); color: var(--blue); border: 1px solid rgba(88,166,255,0.38); }
  .pill-mg { background: rgba(188,140,255,0.18); color: var(--purple); border: 1px solid rgba(188,140,255,0.45); }
  .pill-muted { background: rgba(139,155,180,0.14); color: var(--muted); border: 1px solid rgba(139,155,180,0.3); }
  .flt-btn { background: #162032; color: var(--muted); border: 1px solid var(--border); padding: 4px 9px; font-size: 11px; border-radius: 6px; cursor: pointer; font-weight: 600; }
  .flt-btn:hover { color: var(--text); border-color: var(--border-hi); }
  .flt-btn.active { background: #1f6feb; color: #fff; border-color: #388bfd; }
  .sf-strip { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 10px; font-size: 11.4px; }
  .sf-chip { background: #0c1320; border: 1px solid var(--border); border-radius: 6px; padding: 5px 10px; }
  .btn-primary { background: #238636; color: #fff; border: 1px solid rgba(63,185,80,0.5); border-radius: 6px; padding: 7px 13px; cursor: pointer; font-weight: 600; font-size: 12px; }
  .btn-primary:hover { background: #2ea043; }
  .svc-wrap { display: flex; flex-wrap: wrap; gap: 6px; }
  .log-box { font-size: 11.3px; color: #b6c2d4; line-height: 1.5; max-height: 155px; overflow-y: auto; background: #0b111d; padding: 9px 11px; border-radius: 6px; border: 1px solid var(--border); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
  .sec-hidden { display: none !important; }
  code { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; }
</style>
</head>
<body>
<header>
  <div>
    <h1>
      <span class="dot" id="live_dot"></span>
      <span>DOMINUS &mdash; RISKLESS PAA COMMAND CENTER</span>
      <span class="lock-badge" id="hdr_mode_badge">100% PURE RISKLESS LOCK &bull; v6.3</span>
    </h1>
    <div class="sub" id="meta">Connecting to kraken-finland over zero-RAM SSH pipe...</div>
  </div>
  <div class="spots" id="spots"></div>
  <div style="display:flex;gap:8px;align-items:center;">
    <button class="btn-primary" id="refresh_btn" onclick="refreshNow(true)">Refresh Now</button>
  </div>
</header>

<div class="nav-tabs">
  <button class="tab-btn active" id="tab_all" onclick="setViewTab('all')">Command Overview (All)</button>
  <button class="tab-btn" id="tab_ft" onclick="setViewTab('ft')">Full-Throttle A..N &amp; Projections (v6.3)</button>
  <button class="tab-btn" id="tab_stageb" onclick="setViewTab('stageb')">Institutional Attribution &amp; Funnel</button>
  <button class="tab-btn" id="tab_orders" onclick="setViewTab('orders')">Live Orders &amp; Portfolio</button>
  <button class="tab-btn" id="tab_radar" onclick="setViewTab('radar')">Riskless Opportunity Radar</button>
  <button class="tab-btn" id="tab_v6" onclick="setViewTab('v6')">v6 Expansion &amp; Cross-Venue (8)</button>
  <button class="tab-btn" id="tab_a124" onclick="setViewTab('a124')">Alpha-124 &amp; Machine-Gun Grad-8</button>
  <button class="tab-btn" id="tab_paa" onclick="setViewTab('paa')">RISKLESS PAA Zero-Trust OS</button>
  <button class="tab-btn" id="tab_forensics" onclick="setViewTab('forensics')">Execution &amp; Fleet Diagnostics</button>
</div>

<div class="grid" id="kpis"></div>

<!-- v6.3 AUTHORITATIVE 3-NAV TRIAD, D-001 KMIA NON-INTERFERENCE & FINLAND VM BREAKEVEN BANNER -->
<div class="card card-hero" id="sec_nav_triad" style="margin-bottom:15px;border-color:#2f5580;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <div>
      <h2 style="margin:0;color:var(--green-bright);">Authoritative 3-NAV Triad, <code>D-001</code> Disputed KMIA Safeguard &amp; Finland VM Breakeven Hurdle</h2>
      <div class="sub" style="margin-top:2px;">Sizing &amp; 15% Concentration Caps Strictly Anchored to Reconciled Floor NAV (Never Persisted Book Equity While KMIA Disputed)</div>
    </div>
    <span class="pill pill-ok" id="kmia_guard_pill">D-001 KMIA 4/4 Untouched</span>
  </div>
  <div class="sf-strip" id="nav_triad_strip" style="margin-bottom:0;"></div>
</div>

<!-- v6.3 FULL-THROTTLE 14-FAMILY (A..N) UNIVERSE CENSUS, NON-CONFLATED REAL VS SHADOW MATRIX & DAILY PROJECTIONS -->
<div class="card" id="sec_full_throttle" style="margin-bottom:15px;border-color:#2d507a;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <div>
      <h2 style="margin:0;color:var(--cyan);">Full-Throttle 14-Family (<code>A..N</code>) Universe Census, Real vs Shadow Strategy Matrix &amp; Empirical Projections (v6.3)</h2>
      <div class="sub" id="ft_sub" style="margin-top:2px;">Principle 8 Strict Non-Conflation: Real On-Chain Wallet pUSD vs Realistic Depth-Walked Forward Shadow &bull; <code>polymarket-full-throttle-sweep.{service,timer}</code></div>
    </div>
    <span class="pill pill-info" id="ft_sweep_pill">Full-Throttle Sweep Armed</span>
  </div>
  <div class="sf-strip" id="ft_census_strip"></div>

  <h2 style="margin-top:8px;color:var(--green-bright);">Unified Strategy Performance Matrix &mdash; Real Trading (Wallet Cash) vs Realistic Shadow (Non-Cash, Strictly Segregated)</h2>
  <div style="max-height:305px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;margin-bottom:12px;">
    <table>
      <thead>
        <tr>
          <th>Strategy / Engine</th>
          <th>Real Gate</th>
          <th>Real Open / Quoting</th>
          <th>Real Funnel (Recv / Exec / Rej)</th>
          <th>Real Wallet W/L &amp; PnL</th>
          <th>Shadow Inspected / Proven</th>
          <th>Shadow Open / Resting</th>
          <th>Shadow W/L &amp; Net PnL (<i>Non-Cash</i>)</th>
        </tr>
      </thead>
      <tbody id="ft_comp_rows"></tbody>
    </table>
  </div>

  <div class="two-col" style="margin-bottom:12px;">
    <div>
      <h2 style="margin-top:2px;">14-Family (<code>A..N</code>) Full-Universe Coverage &amp; Rule-Trap Firewall</h2>
      <div style="max-height:285px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead>
            <tr>
              <th>Fam</th>
              <th>Detector Family</th>
              <th>Inspected</th>
              <th>CLASS A/B</th>
              <th>CLASS C</th>
              <th>Rule Traps (D)</th>
              <th>Dormant (&le;50bps)</th>
            </tr>
          </thead>
          <tbody id="ft_family_rows"></tbody>
        </table>
      </div>
    </div>
    <div>
      <h2 style="margin-top:2px;"><code>Family L</code> Hedged Maker Shadow, <code>FT_*</code> Bridge &amp; Top &le;50 bps Dormant Near-Arbs</h2>
      <div class="sf-strip" id="ft_bridge_maker_strip" style="margin-bottom:6px;"></div>
      <div style="max-height:230px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead>
            <tr>
              <th>Type / Fam</th>
              <th>Candidate / Resting Quote</th>
              <th>Edge / Gap</th>
              <th>Status / Reason</th>
            </tr>
          </thead>
          <tbody id="ft_dormant_maker_rows"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div style="border-top:1px solid var(--border);padding-top:10px;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;">
      <h2 style="margin:0;color:var(--purple);">Empirical Compounding Projections (<code>P25</code> Conservative / <code>P50</code> Base Finland VM / <code>P75</code> Upside) &amp; Milestone ETAs</h2>
      <span class="pill pill-mg" id="proj_model_pill">PROJECTED MODEL (NON-CASH)</span>
    </div>
    <div class="sf-strip" id="proj_milestone_strip"></div>
    <div style="max-height:195px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead>
          <tr>
            <th>Horizon</th>
            <th>Date (UTC)</th>
            <th>P25 Conservative</th>
            <th>P50 Base (Finland VM)</th>
            <th>P50 Daily Velocity</th>
            <th>P75 Upside (CA-ON Legal XV)</th>
          </tr>
        </thead>
        <tbody id="proj_horizon_rows"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- STAGE B: INSTITUTIONAL 10 NORTH-STAR KPIS, 6-STAGE OPPORTUNITY FUNNEL & CAPITAL-HOUR LEDGER -->
<div class="card" id="sec_stageb" style="margin-bottom:15px;border-color:#2b4a70;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <div>
      <h2 style="margin:0;color:var(--cyan);">Institutional Economic Attribution, 6-Stage Opportunity Funnel &amp; 10 North-Star KPIs (Stage B v3.0)</h2>
      <div class="sub" id="stageb_sub" style="margin-top:2px;">Wallet-to-Wallet Net Economic Identity (Zero Double-Counting) &bull; Sub-ms Competitor Decay Curve (&lt;5ms / 5-15ms / 15-40ms / &gt;40ms) &bull; $/Occupied Capital-Hour</div>
    </div>
    <span class="pill pill-info" id="stageb_rung_pill">Rung 1 Active (Finland e2-custom-2-4096)</span>
  </div>
  <div class="sf-strip" id="stageb_kpis_strip"></div>
  <div class="two-col" style="margin-bottom:0;">
    <div>
      <h2 style="margin-top:4px;">6-Stage Opportunity Funnel &amp; 4-Bucket Competitor Decay</h2>
      <div class="sf-strip" id="stageb_funnel_strip" style="margin-bottom:6px;"></div>
      <div style="max-height:205px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>Latency Bucket</th><th>Target Institutional Rung</th><th>Observed</th><th>Missed $</th><th>Action Gate</th></tr></thead>
          <tbody id="stageb_decay_rows"></tbody>
        </table>
      </div>
    </div>
    <div>
      <h2 style="margin-top:4px;">Per-Sleeve Capital-Hour &amp; Net $/1k Attribution (Reconciled)</h2>
      <div style="max-height:240px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>Sleeve</th><th>Tr</th><th>Gross</th><th>Fees / Unwind</th><th>Net PnL</th><th>Net/$1k</th><th>Cap-Hrs (bps/hr)</th></tr></thead>
          <tbody id="stageb_sleeve_rows"></tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- HERO #1: LIVE WORKING CLOB ORDERS & ACTIVE RISKLESS POSITIONS -->
<div class="card card-hero" id="sec_live_orders" style="margin-bottom:15px;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <div>
      <h2 style="margin:0;color:var(--green-bright);">Live Working CLOB Orders &amp; Active Riskless Book (Real-Money Polygon L2)</h2>
      <div class="sub" id="live_book_banner" style="margin-top:2px;">Probing live Polymarket CLOB open orders &amp; on-chain pUSD collateral...</div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
      <span class="sub" id="d1_timer" style="margin:0;color:var(--amber);font-weight:600;"></span>
      <span class="pill pill-ok" id="clob_quote_pill">0% Maker Fee</span>
    </div>
  </div>
  <div id="active_box" style="font-size:12px;"></div>
</div>

<!-- HERO #2: LIVE RISKLESS ARBITRAGE & CARRY RADAR -->
<div class="card" id="sec_radar" style="margin-bottom:15px;border-color:#264063;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <div>
      <h2 style="margin:0;color:var(--cyan);">Live Riskless Arbitrage &amp; Carry Opportunity Radar</h2>
      <div class="sub" id="radar_sub" style="margin-top:2px;">Real-time Harvester IPC emissions + 5m Full-Universe Scanner (0%-Fee UMA Carry, Post-Clinch Sweepers, Locked Rewards &amp; NegRisk Slate Arbs)</div>
    </div>
    <div style="display:flex;gap:5px;flex-wrap:wrap;">
      <button class="flt-btn active" id="rad_flt_ALL" onclick="setRadarFilter('ALL')">All Riskless</button>
      <button class="flt-btn" id="rad_flt_LIVE_IPC" onclick="setRadarFilter('LIVE_IPC')">Live Harvester IPC</button>
      <button class="flt-btn" id="rad_flt_MACHINE_GUN" onclick="setRadarFilter('MACHINE_GUN')">Machine-Gun</button>
      <button class="flt-btn" id="rad_flt_V6_EXPANSION" onclick="setRadarFilter('V6_EXPANSION')">v6 &amp; Cross-Venue</button>
      <button class="flt-btn" id="rad_flt_UMA_CARRY" onclick="setRadarFilter('UMA_CARRY')">UMA Carry (BOND1)</button>
      <button class="flt-btn" id="rad_flt_POST_CLINCH" onclick="setRadarFilter('POST_CLINCH')">Post-Clinch (LOCK1)</button>
      <button class="flt-btn" id="rad_flt_LOCKED_REWARD" onclick="setRadarFilter('LOCKED_REWARD')">Locked Rewards</button>
      <button class="flt-btn" id="rad_flt_SLATE_ARB" onclick="setRadarFilter('SLATE_ARB')">NegRisk Slate Arb</button>
    </div>
  </div>
  <div class="sf-strip" id="radar_strip"></div>
  <div style="max-height:270px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
    <table>
      <thead>
        <tr>
          <th>Category / Sleeve</th>
          <th>Market / Question</th>
          <th>Side / Structure</th>
          <th>Bid / Box Cost</th>
          <th>Net Carry / Box Edge</th>
          <th>Est. Velocity</th>
          <th>Book Liq</th>
          <th>Gate</th>
        </tr>
      </thead>
      <tbody id="radar_rows"></tbody>
    </table>
  </div>
</div>

<!-- STAGE G CROSS-VENUE SHADOW + 8 v6 RISKLESS EXPANSION ENGINES + COMPACT CANDIDATE L2 RECORDER -->
<div class="card" id="sec_v6_expansion" style="margin-bottom:15px;border-color:#2b4a70;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <div>
      <h2 style="margin:0;color:var(--cyan);">v6 Riskless Expansion Matrix (8 State-Dominance Engines) &amp; Stage G Cross-Venue Shadow</h2>
      <div class="sub" style="margin-top:2px;">Strict Worst-Case State Dominance (<code>min V_T(&omega;) &gt; All-In Cost</code>) &bull; CA-ON Legal <code>STX CAD &harr; ForecastEx USD</code> &bull; Keyless Deribit <code>USDC</code> &bull; Bounded <code>&le;12 MB/day</code> Candidate L2 Recorder</div>
    </div>
    <span class="pill pill-info" id="v6_health_pill">Stage G + Alpha-124 Shadow Armed</span>
  </div>
  <div class="sf-strip" id="v6_strip"></div>
  <div style="max-height:265px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
    <table>
      <thead>
        <tr>
          <th>v6 Engine Sleeve</th>
          <th>Mathematical Invariant &amp; Venue Scope</th>
          <th>Evaluated</th>
          <th>Verified Hits</th>
          <th>Shadow W / L</th>
          <th>Gate Status</th>
        </tr>
      </thead>
      <tbody id="v6_engine_rows"></tbody>
    </table>
  </div>
</div>

<!-- TWO-COLUMN: REAL-MONEY PORTFOLIO W/L + ALPHA-124 GRAD-8 MATRIX -->
<div class="two-col" id="sec_portfolio_a124">
  <div class="card" id="sec_portfolio_card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
      <div>
        <h2 id="pm_harvester_hdr" style="margin:0;">Polymarket Live Harvester &mdash; Riskless Strategy W/L</h2>
        <div class="sub" id="spark_lbl">Pure Riskless Realized Curve (100% Win Rate)</div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <svg id="spark" width="150" height="30"></svg>
        <button class="flt-btn active" id="pm_flt_riskless" onclick="setPmFilter('riskless')">Active Riskless Only</button>
        <button class="flt-btn" id="pm_flt_all" onclick="setPmFilter('all')">All Historical</button>
      </div>
    </div>
    <div style="max-height:265px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead><tr><th>Strategy Sleeve</th><th>Live Routing / Gate</th><th>Open</th><th>Session W/L</th><th>Session PnL</th><th>All-Time W/L</th><th>All-Time PnL</th></tr></thead>
        <tbody id="pm_strats"></tbody>
      </table>
    </div>
    <h2 style="margin-top:13px;">Recent Real-Money Closed Trades (Wallet-Reconciled)</h2>
    <div style="max-height:235px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead><tr><th>Ottawa (ET)</th><th>Market</th><th>Sleeve</th><th>In &rarr; Out</th><th>Notional</th><th>Real PnL</th><th>Exit</th></tr></thead>
        <tbody id="pm_trades"></tbody>
      </table>
    </div>
    <h2 style="margin-top:13px;">Live Harvester Execution Stream</h2>
    <div class="log-box" id="log_events"></div>
  </div>

  <div class="card" id="sec_a124_card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:8px;">
      <div>
        <h2 style="margin:0;">Alpha-124 &amp; Machine-Gun <code>_grad8</code> Matrix</h2>
        <div class="sub" id="a124_sync">Auto-promotes at 8/8 Shadow Wins, 0 Losses</div>
      </div>
      <div style="display:flex;gap:5px;">
        <button class="flt-btn active" id="a124_flt_focus" onclick="setA124Filter('focus')">Live &amp; Zero-Loss</button>
        <button class="flt-btn" id="a124_flt_v6" onclick="setA124Filter('v6')">v6 Expansion (8)</button>
        <button class="flt-btn" id="a124_flt_all" onclick="setA124Filter('all')">All Sleeves</button>
      </div>
    </div>
    <div style="max-height:310px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead><tr><th>Sleeve</th><th>Open</th><th>W / L</th><th>8/8 Gate Progress</th><th>T1000 PnL</th></tr></thead>
        <tbody id="a124_sleeves"></tbody>
      </table>
    </div>
    <h2 style="margin-top:13px;">Open Shadow Structural Boxes (<span id="a124_open_cnt">0</span> Active)</h2>
    <div style="max-height:190px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead><tr><th>Sleeve</th><th>Market</th><th>Cost</th><th>Bid</th><th>TTE</th></tr></thead>
        <tbody id="a124_open"></tbody>
      </table>
    </div>
    <h2 style="margin-top:13px;">Recent Closed Zero-Loss Shadow Boxes</h2>
    <div style="max-height:215px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead><tr><th>Closed (ET)</th><th>Sleeve</th><th>Market</th><th>In&rarr;Out</th><th>T100 / T1000</th></tr></thead>
        <tbody id="a124_closed"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- RISKLESS PAA ZERO-TRUST AUTONOMOUS OS -->
<div class="card" id="sec_paa" style="margin-bottom:15px;border-color:#2f4668;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <div>
      <h2 style="margin:0;">RISKLESS PAA &mdash; Autonomous Zero-Loss Profit &amp; Verification OS</h2>
      <div class="sub" style="margin-top:2px;">100% Pure Riskless Live Lock &bull; Stateless Short-Lived AI Sessions (60% Ctx Cap) &bull; Tier-A/B/C Memory &bull; 5-Gate Non-AI Verifier (<code>NO EVIDENCE = NO VERIFIED CLAIM</code>)</div>
    </div>
    <div class="sub" id="paa_live_pulse" style="margin:0;color:var(--green-bright);font-weight:600;"></div>
  </div>
  <div class="sf-strip" id="paa_strip"></div>
  <div class="three-col">
    <div>
      <h2 style="margin-top:4px;">Live Schedules &amp; Heartbeats (1s Tick)</h2>
      <div style="max-height:240px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>Cadence Unit</th><th>Last (ET)</th><th>Age</th><th>Next Fire</th></tr></thead>
          <tbody id="paa_timers"></tbody>
        </table>
      </div>
      <h2 style="margin-top:10px;">Recent Releases &amp; Rollbacks</h2>
      <div style="max-height:125px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>Release</th><th>SHA</th><th>Gates</th><th>State</th></tr></thead>
          <tbody id="paa_deploys"></tbody>
        </table>
      </div>
    </div>
    <div>
      <h2 style="margin-top:4px;">Tier-B Verified Facts (Live TTL Revalidation)</h2>
      <div style="max-height:240px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>Fact Key</th><th>Value</th><th>Status</th><th>TTL Left</th></tr></thead>
          <tbody id="paa_facts"></tbody>
        </table>
      </div>
      <h2 style="margin-top:10px;">Stateless AI Sessions (&le;60% Context Cap)</h2>
      <div style="max-height:125px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>ET</th><th>Stage Role</th><th>Fresh</th><th>Ctx %</th></tr></thead>
          <tbody id="paa_sessions"></tbody>
        </table>
      </div>
    </div>
    <div>
      <h2 style="margin-top:4px;">Durable Zero-Trust Tasks &amp; 5-Stage Ladder</h2>
      <div id="paa_ladder" style="font-size:11.4px;margin-bottom:6px;"></div>
      <div style="max-height:210px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>Prio</th><th>Task / Category</th><th>Ses</th><th>Zero-Trust State</th></tr></thead>
          <tbody id="paa_tasks"></tbody>
        </table>
      </div>
      <h2 style="margin-top:10px;">Live Verification &amp; Supervisor Audit Trail</h2>
      <div class="log-box" id="paa_events" style="max-height:125px;"></div>
    </div>
  </div>
</div>

<!-- SYSTEM DAEMONS & MAKER/ORDER EXECUTION DIAGNOSTICS -->
<div id="sec_forensics">
  <div class="card" style="margin-bottom:15px;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
      <h2 style="margin:0;">Consolidated Riskless Systemd Fleet &amp; Multiplexed RTDS/SHM Oracle Feeds</h2>
      <span class="sub" id="vm_foot_note">Zero-RAM Local SSH Probe</span>
    </div>
    <div class="svc-wrap" id="svcs"></div>
  </div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
      <div>
        <h2 style="margin:0;">Order Attempt &amp; Maker Queue Diagnostics (CLOB Latency &amp; TTL Telemetry)</h2>
        <div class="sub" style="margin-top:2px;">Tracks BOND1 / LOCK1 / S2 Maker postings, FIFO queue lifecycle &amp; hot-path CLOB execution latency</div>
      </div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;">
        <button class="flt-btn active" id="sf_flt_attempts" onclick="setSfFilter('attempts')">Order Attempts</button>
        <button class="flt-btn" id="sf_flt_meaningful" onclick="setSfFilter('meaningful')">Meaningful</button>
        <button class="flt-btn" id="sf_flt_slow" onclick="setSfFilter('slow')">Speed Misses</button>
        <button class="flt-btn" id="sf_flt_all" onclick="setSfFilter('all')">All</button>
      </div>
    </div>
    <div class="sf-strip" id="sf_summary"></div>
    <div style="max-height:260px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead><tr><th>Ottawa (ET)</th><th>Market / Sleeve</th><th>Path</th><th>Verdict</th><th>Quote / Limit</th><th>Latency</th><th>Diagnosis</th></tr></thead>
        <tbody id="sf_rows"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const _ET_FMT_FULL = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZoneName: 'short' });
const _ET_FMT_MDHMS = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
const _ET_FMT_MDHM = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
const _ET_FMT_HMS = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

function fmtOttawa(val, mode='md_hms') {
  if (val === null || val === undefined || val === '') return '-';
  let dt = null;
  if (typeof val === 'number' && val > 1e8) {
    dt = new Date(val > 1e12 ? val : val * 1000);
  } else {
    let s = String(val).trim().replace(' UTC', 'Z');
    if (!s) return '-';
    const asNum = Number(s);
    if (!Number.isNaN(asNum) && asNum > 1e8) {
      dt = new Date(asNum > 1e12 ? asNum : asNum * 1000);
    } else {
      if (s.includes(' ') && !s.includes('T')) s = s.replace(' ', 'T');
      if (!s.endsWith('Z') && !/[+-]\\d{2}:?\\d{2}$/.test(s)) s += 'Z';
      dt = new Date(s);
    }
  }
  if (!dt || Number.isNaN(dt.getTime())) return String(val);
  const f = mode === 'full' ? _ET_FMT_FULL : (mode === 'md_hm' ? _ET_FMT_MDHM : (mode === 'hms' ? _ET_FMT_HMS : _ET_FMT_MDHMS));
  return f.format(dt).replace(',', '');
}

function esc(v) {
  return String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function shortSlv(s) {
  return String(s || '')
    .replace('_DOMINANCE_BOX', '')
    .replace('_ZERO_FEE_', '_')
    .replace('_CROSS_MARKET_PARTITION_IMPLICATION_BOX', '_PARTITION_IMPL')
    .replace('_EXACT_MARGIN_AND_ML_SPREAD_BOX', '_NFL_EM_SPREAD')
    .replace('_SUBPERIOD_CLINCH_AND_PROP_EXPANSION', '_CLINCH_PROP')
    .replace('_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX', '_DEADLINE_LADDER')
    .replace('_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR', '_TENNIS_CORR')
    .replace('_MULTISPORT_POST_REVIEW_SCORE_CLINCH', '_POST_REVIEW_CLINCH')
    .replace('_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG', '_ELECTION_DAG')
    .replace('_THREE_WAY_REGULATION_SYNTHETIC_BOX', '_3WAY_SYNTH')
    .replace('_INGAME_MILESTONE_IRREVERSIBLE_LOCK', '_INGAME_LOCK')
    .replace('_POST_CLINCH_REBATE_SWEEPER', '_POST_CLINCH_SWEEPER');
}

function next4hCountdown() {
  const now = new Date();
  const h = now.getUTCHours(), m = now.getUTCMinutes(), s = now.getUTCSeconds();
  const remSec = ((4 - (h % 4)) * 3600) - (m * 60) - s;
  const rh = Math.floor(remSec / 3600), rm = Math.floor((remSec % 3600) / 60);
  return `${rh}h ${rm}m`;
}

function updateD1Countdown() {
  const now = new Date();
  const min = now.getUTCMinutes();
  const sec = now.getUTCSeconds();
  const secIn15m = (min % 15) * 60 + sec;
  const el = document.getElementById('d1_timer');
  if (!el) return;
  if (secIn15m >= 600 && secIn15m <= 884) {
    const rem = 884 - secIn15m;
    el.style.color = '#3fb950';
    el.textContent = `D1 15m/5m Same-Oracle Overlap ACTIVE NOW (${rem}s left)`;
  } else {
    const wait = secIn15m < 600 ? (600 - secIn15m) : (900 - secIn15m + 600);
    const m = Math.floor(wait / 60), s = wait % 60;
    el.style.color = '#d29922';
    el.textContent = `Next D1 Same-Oracle Overlap in ${m}m ${s}s`;
  }
}
setInterval(updateD1Countdown, 1000);

function drawSpark(pts) {
  const svg = document.getElementById('spark');
  if (!svg || !pts || pts.length < 2) return;
  const mn = Math.min(...pts), mx = Math.max(...pts);
  const rng = Math.max(0.01, mx - mn);
  const w = 146, h = 24;
  const coords = pts.map((v, i) => {
    const x = 2 + (i / (pts.length - 1)) * w;
    const y = 3 + h - ((v - mn) / rng) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const rising = pts[pts.length - 1] >= pts[0];
  const col = rising ? '#3fb950' : '#d29922';
  svg.innerHTML = `<polyline fill="none" stroke="${col}" stroke-width="2.2" points="${coords}"/>`;
}

let _inFlight = false;
let _viewTab = 'all';
let _radarFilter = 'ALL';
let _pmFilter = 'riskless';
let _a124Filter = 'focus';
let _sfFilter = 'attempts';
let _lastSnapshot = null;
let _lastSfData = null;
let _lastPaaData = null;
let _lastRadarData = null;
let _lastSyncClientMs = 0;
let _pollSeq = 0;
let _lastMetaPrefix = '';

function setViewTab(tab) {
  _viewTab = tab;
  ['all', 'ft', 'stageb', 'orders', 'radar', 'v6', 'a124', 'paa', 'forensics'].forEach(k => {
    const b = document.getElementById('tab_' + k);
    if (b) b.className = 'tab-btn' + (k === tab ? ' active' : '');
  });
  const show = (id, cond) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('sec-hidden', !cond);
  };
  show('sec_nav_triad', tab === 'all' || tab === 'ft' || tab === 'orders');
  show('sec_full_throttle', tab === 'all' || tab === 'ft');
  show('sec_stageb', tab === 'all' || tab === 'stageb');
  show('sec_live_orders', tab === 'all' || tab === 'orders');
  show('sec_radar', tab === 'all' || tab === 'radar');
  show('sec_v6_expansion', tab === 'all' || tab === 'v6' || tab === 'radar');
  show('sec_portfolio_a124', tab === 'all' || tab === 'orders' || tab === 'a124');
  show('sec_portfolio_card', tab === 'all' || tab === 'orders');
  show('sec_a124_card', tab === 'all' || tab === 'a124');
  const twoCol = document.getElementById('sec_portfolio_a124');
  if (twoCol) {
    twoCol.style.gridTemplateColumns = (tab === 'orders' || tab === 'a124') ? '1fr' : '';
  }
  show('sec_paa', tab === 'all' || tab === 'paa');
  show('sec_forensics', tab === 'all' || tab === 'forensics');
}

function renderNavTriadAndFullThrottle(d) {
  const pm = d.polymarket_live || {};
  const nt = pm.nav_triad || {};
  const hf = pm.harvester_funnel || {};
  const ft = d.full_throttle || {};
  const fts = ft.systemd || d.full_throttle_systemd || {};
  const uc = ft.universe_census || {};
  const om = ft.opportunity_metrics || {};
  const hb = ft.harvester_bridge || {};
  const fl = ft.family_l_maker_shadow || {};
  const a124 = d.alpha124 || {};
  const v52 = a124.v52_catalog || {};
  const sb = d.stage_b_attribution || {};
  const sbKpi = sb.north_star_kpis || {};
  const proj = d.daily_projections || {};
  const comp = (d.strategy_comparison_matrix || {}).rows || [];

  const floorNav = Number(nt.reconciled_floor_nav_usd ?? pm.guaranteed_redemption_equity_usd ?? pm.wallet_cash_usd ?? 0);
  const mtmNav = Number(nt.mtm_liquidation_nav_usd ?? pm.mtm_bid_equity_usd ?? floorNav);
  const bookNav = Number(nt.persisted_book_equity_usd ?? pm.equity_usd ?? floorNav);
  const kmiaCnt = Number(nt.kmia_disputed_count ?? 0);
  const kmiaCost = Number(nt.kmia_frozen_cost_usd ?? nt.disputed_uma_cost_usd ?? 0);
  const kmiaBid = Number(nt.kmia_mtm_bid_usd ?? 0);
  const kmiaOk = nt.kmia_untouched_ok !== false;
  const vmHurdleHr = Number(nt.vm_breakeven_bps_per_hr ?? 7.04);
  const vmDaily = Number(nt.vm_daily_cost_usd ?? 0.8223);
  const quoteBpsHr = Number(nt.live_quoting_bps_per_hr ?? 0);
  const realCapBpsHr = Number(sbKpi.kpi_3_bps_per_capital_hour ?? 0);

  const kmiaPill = document.getElementById('kmia_guard_pill');
  if (kmiaPill) {
    kmiaPill.className = 'pill ' + (kmiaOk ? 'pill-ok' : 'pill-bad');
    kmiaPill.textContent = kmiaOk
      ? `D-001 KMIA ${kmiaCnt}/4 Untouched ($${kmiaCost.toFixed(2)} Frozen, 0 Orders)`
      : `ALERT: KMIA ORDER DETECTED (${nt.kmia_exit_or_unwind_orders})`;
  }
  const ntStrip = document.getElementById('nav_triad_strip');
  if (ntStrip) {
    ntStrip.innerHTML =
      `<span class="sf-chip">1. Guaranteed Floor NAV (Sizing): <b class="pos">$${floorNav.toFixed(2)}</b> <span class="sub">(KMIA = $0.00)</span></span>` +
      `<span class="sf-chip">2. Mark-to-Bid Liquidation NAV: <b class="cyan">$${mtmNav.toFixed(2)}</b> <span class="sub">(KMIA Bid $${kmiaBid.toFixed(2)})</span></span>` +
      `<span class="sf-chip">3. Persisted Book Equity: <b class="warn">$${bookNav.toFixed(2)}</b> <span class="sub">(Incl. $${kmiaCost.toFixed(2)} Disputed KMIA &mdash; Non-Sizing)</span></span>` +
      `<span class="sf-chip">VM Breakeven Hurdle: <b class="amber">${vmHurdleHr.toFixed(2)} bps/hr</b> ($${vmDaily.toFixed(3)}/d = $24.67/mo) vs Quoting <b class="${quoteBpsHr >= vmHurdleHr ? 'pos' : 'cyan'}">${quoteBpsHr.toFixed(1)} bps/hr</b> &bull; Realized Cap-Hr <b class="pos">+${realCapBpsHr.toFixed(1)} bps/hr</b></span>`;
  }

  const swPill = document.getElementById('ft_sweep_pill');
  if (swPill) {
    const mp = fts.memory_peak_mib !== null && fts.memory_peak_mib !== undefined ? `${Number(fts.memory_peak_mib).toFixed(1)} MiB` : `${Number((ft.campaign_summary || {}).peak_rss_mib || 0).toFixed(1)} MiB`;
    const mm = `${Number(fts.memory_max_mib || 220).toFixed(0)}MiB`;
    const nxt = fts.next_trigger_in_sec !== null && fts.next_trigger_in_sec !== undefined ? `next ${fmtSecCompact(fts.next_trigger_in_sec)}` : (fts.timer_active_state || 'armed');
    const ok = (fts.result === 'success' || fts.result === 'unknown') && fts.cgroup_memory_ok !== false;
    swPill.className = 'pill ' + (ok ? 'pill-ok' : 'pill-warn');
    swPill.textContent = `Sweep: ${fts.result || 'armed'} (exit=${fts.exec_main_status ?? 0}, Peak=${mp}/${mm}, ${nxt})`;
  }

  const cStrip = document.getElementById('ft_census_strip');
  if (cStrip) {
    const sk = uc.skip_counts || {};
    const skTxt = Object.entries(sk).slice(0, 3).map(([k, v]) => `${k}:${Number(v).toLocaleString()}`).join(', ') || 'none';
    cStrip.innerHTML =
      `<span class="sf-chip">Universe Census: <b>${Number(uc.total_observable_events || 0).toLocaleString()}</b> Events &bull; <b>${Number(uc.total_observable_markets || 0).toLocaleString()}</b> Total Mkts &bull; <b class="pos">${Number(uc.active_unclosed_markets || 0).toLocaleString()}</b> Active &bull; <b class="cyan">${Number(uc.total_tradable_outcome_tokens || 0).toLocaleString()}</b> Tokens</span>` +
      `<span class="sf-chip">Structures: NegRisk <b>${Number(uc.negrisk_events || 0).toLocaleString()}</b> (+Aug <b>${Number(uc.augmented_negrisk_events || 0)}</b>) &bull; Graph Edges <b>${Number(uc.graph_total_edges || 0).toLocaleString()}</b> &bull; Skips: <span class="sub">${esc(skTxt)}</span></span>` +
      `<span class="sf-chip">Alpha-124 v5.2 Catalog: Binaries <b>${Number(v52.binaries_monitored || 0).toLocaleString()}</b> &bull; UMA Proposed <b class="cyan">${Number(v52.uma_proposed_count || 0)}</b> (Hot <b>${Number(v52.uma_hot_bonds_count || 0)}</b>) &bull; NegRisk Slates <b>${Number(v52.negrisk_slates_count || 0)}</b> &bull; CAL1 <b>${Number(v52.cal1_ladders_count || 0)}</b> &bull; WS Tokens <b>${Number(v52.ws_subscribed_tokens || 0)}</b> (${Number(v52.ws_shards_active || 0)} shards, Pin ${Number(v52.dormant_ws_pinned_tokens || 0)}) &bull; MakerPend <b>${Number(v52.maker_pending_shadow || 0)}</b> &bull; BridgeEmit <b class="pos">${Number(v52.bridge_emitted_total || 0)}</b></span>` +
      `<span class="sf-chip">Firewall: Proven <b>${Number(om.mathematically_valid_proofs || 0)}</b> &bull; Rule Traps Blocked (CLASS_D): <b class="pos">${Number(om.rule_mismatch_rejections_prevented || 0).toLocaleString()}</b> &bull; D-007 &ge;3-Leg Quarantined: <b>${Number(om.d007_quarantined_3plus_leg_count || 0)}</b></span>`;
  }

  const compTb = document.getElementById('ft_comp_rows');
  if (compTb) {
    compTb.innerHTML = comp.map(r => {
      const rl = r.real_trading || {};
      const sh = r.realistic_shadow || {};
      const rpnl = Number(rl.realized_wallet_pnl_usd || 0);
      const spnl = Number(sh.shadow_net_pnl_usd || 0);
      const gStr = String(rl.gate || '');
      const gCls = gStr.includes('ACTIVE') || gStr.includes('ARMED') ? 'pill-ok' : (gStr.includes('PAUSED') ? 'pill-muted' : 'pill-info');
      const noteHtml = sh.note ? ` <span class="sub">(${esc(sh.note)})</span>` : '';
      return `<tr>
        <td><b>${esc(r.label)}</b></td>
        <td><span class="pill ${gCls}">${esc(gStr)}</span></td>
        <td><b>${rl.open_positions || 0}</b> open &bull; <b class="cyan">${rl.resting_clob_orders || 0}</b> CLOB</td>
        <td>${rl.candidates_received || 0} / <b class="pos">${rl.executed || 0}</b> / <span class="${(rl.rejected || 0) > 0 ? 'warn' : 'sub'}">${rl.rejected || 0}</span></td>
        <td><b>${rl.wins || 0}W/${rl.losses || 0}L</b> (<b class="${rpnl >= 0 ? 'pos' : 'neg'}">${rpnl >= 0 ? '+' : ''}$${rpnl.toFixed(2)}</b>)</td>
        <td>${Number(sh.inspected || 0).toLocaleString()} / <b class="cyan">${sh.proven_class_a_b || 0}</b> A+B <span class="sub">(${sh.rule_traps_blocked || 0} D-blocked)</span></td>
        <td><b>${sh.shadow_open_or_resting || 0}</b></td>
        <td><b>${sh.shadow_wins || 0}W/${sh.shadow_losses || 0}L</b> (<b class="${spnl >= 0 ? 'cyan' : 'warn'}">${spnl >= 0 ? '+' : ''}$${spnl.toFixed(2)}</b> <i>sim</i>)${noteHtml}</td>
      </tr>`;
    }).join('') || '<tr><td colspan="8" class="sub">Awaiting Full-Throttle &amp; Harvester telemetry...</td></tr>';
  }

  const famTb = document.getElementById('ft_family_rows');
  if (famTb) {
    famTb.innerHTML = (ft.family_matrix || []).map(f => `<tr>
      <td><span class="pill pill-info">${esc(f.family_code)}</span></td>
      <td><b>${esc(f.family_name)}</b></td>
      <td>${Number(f.inspected || 0).toLocaleString()}</td>
      <td class="${(f.class_a_b || 0) > 0 ? 'pos' : 'sub'}"><b>${f.class_a_b || 0}</b> (${f.class_a || 0}/${f.class_b || 0})</td>
      <td>${f.class_c || 0}</td>
      <td class="${(f.rule_traps_blocked || 0) > 0 ? 'warn' : 'sub'}"><b>${f.rule_traps_blocked || 0}</b></td>
      <td class="cyan"><b>${f.dormant_store_count || f.dormant_near_misses || 0}</b></td>
    </tr>`).join('') || '<tr><td colspan="7" class="sub">No dashboard_latest.json family matrix found yet.</td></tr>';
  }

  const bmStrip = document.getElementById('ft_bridge_maker_strip');
  if (bmStrip) {
    const hbSkips = Object.entries(hb.skipped_by_reason || {}).map(([k, v]) => `${k}:${v}`).join(', ') || '0';
    const hvSkips = Object.entries(Object.assign({}, hf.taker_skip_counts || {}, hf.maker_skip_counts || {})).slice(0, 3).map(([k, v]) => `${k}:${v}`).join(', ') || '0';
    bmStrip.innerHTML =
      `<span class="sf-chip">FT Bridge: Emitted <b class="pos">${hb.total_emitted_across_campaign ?? 0}</b> (Skips: ${esc(hbSkips)})</span>` +
      `<span class="sf-chip">Harvester Skips: <span class="sub">${esc(hvSkips)}</span></span>` +
      `<span class="sf-chip">Fam L Maker Shadow: <b>${fl.resting_passive_quotes_count ?? 0}</b> Resting &bull; <b class="pos">${fl.filled_hedged_locks_count ?? 0}</b> Hedged Locks / ${fl.adverse_selected_fills_count ?? 0} Adv &bull; Net <b class="cyan">+$${Number(fl.net_post_adverse_shadow_pnl_ex_rebate_usd || 0).toFixed(2)}</b> (+$${Number(fl.estimated_maker_rebate_15_to_25pct_usd || 0).toFixed(3)} reb, <i>non-cash</i>)</span>` +
      `<span class="sf-chip">Dormant Store: <b>${om.dormant_within_50_bps_count ?? 0}</b> &le;50bps (${om.dormant_rescans_triggered ?? 0} rescans)</span>`;
  }

  const dmTb = document.getElementById('ft_dormant_maker_rows');
  if (dmTb) {
    const rowsHtml = [];
    (ft.top_executable || []).slice(0, 4).forEach(x => {
      rowsHtml.push(`<tr><td><span class="pill pill-ok">EXEC ${esc(x.family_code)}</span></td><td><b>${esc(x.title_summary)}</b></td><td class="pos"><b>+${Number(x.net_edge_bps || 0).toFixed(1)} bps</b></td><td>${esc(x.opportunity_class)} ($${Number(x.max_notional_usd || 0).toFixed(2)})</td></tr>`);
    });
    (fl.top_resting_quotes || []).slice(0, 5).forEach(q => {
      rowsHtml.push(`<tr><td><span class="pill pill-mg">FAM L (${esc(q.source_family)})</span></td><td><b>${esc(q.title_summary)}</b></td><td class="cyan"><b>+${Number(q.locked_edge_bps || 0).toFixed(1)} bps</b></td><td>Bid $${Number(q.quote_bid_px || 0).toFixed(3)} + Hedge $${Number(q.hedge_ask_px || 0).toFixed(3)}</td></tr>`);
    });
    (ft.top_dormant_near_arbs || []).slice(0, 6).forEach(nm => {
      rowsHtml.push(`<tr><td><span class="pill pill-warn">DORM ${esc(nm.family_code)}</span></td><td><b>${esc(nm.title_summary)}</b></td><td>Gap ${Number(nm.gap_to_breakeven_bps || 0).toFixed(1)} bps</td><td class="sub">${esc(nm.dormant_reason)} (obs ${nm.times_observed})</td></tr>`);
    });
    dmTb.innerHTML = rowsHtml.join('') || '<tr><td colspan="4" class="sub">No dormant or Family L quotes recorded yet.</td></tr>';
  }

  const pPill = document.getElementById('proj_model_pill');
  if (pPill) {
    pPill.textContent = `PROJECTED MODEL (${proj.model_version || 'v5.2'} • NON-CASH)`;
  }
  const msStrip = document.getElementById('proj_milestone_strip');
  if (msStrip) {
    const ms = proj.milestones || {};
    const fmtMs = (lbl, obj) => {
      const o = obj || {};
      const p50 = o.p50_day !== null && o.p50_day !== undefined ? `P50: <b>${o.p50_day}d</b> (${esc(o.p50_date_utc || '')})` : 'P50: >365d';
      const p75 = o.p75_day !== null && o.p75_day !== undefined ? `P75: <b class="pos">${o.p75_day}d</b>` : 'P75: >365d';
      const p25 = o.p25_day !== null && o.p25_day !== undefined ? `P25: ${o.p25_day}d` : 'P25: >365d';
      return `<span class="sf-chip">Milestone <b>${lbl}</b>: ${p50} &bull; ${p75} &bull; <span class="sub">${p25}</span></span>`;
    };
    msStrip.innerHTML =
      fmtMs('$150 (M3.2)', ms.usd_150) +
      fmtMs('$253 (Stage G)', ms.usd_253) +
      fmtMs('$500 (Multi-Leg)', ms.usd_500) +
      fmtMs('$5,000 (Auto-Promo)', ms.usd_5000);
  }
  const hzTb = document.getElementById('proj_horizon_rows');
  if (hzTb) {
    const hz = proj.horizons || {};
    const order = [['day_1', 'Day 1'], ['day_7', 'Day 7 (1w)'], ['day_14', 'Day 14 (2w)'], ['day_30', 'Day 30 (1m)'], ['day_60', 'Day 60 (2m)'], ['day_90', 'Day 90 (3m)'], ['day_180', 'Day 180 (6m)'], ['day_365', 'Day 365 (1y)']];
    hzTb.innerHTML = order.filter(([k]) => hz[k]).map(([k, lbl]) => {
      const r = hz[k];
      const netAfterVm = (r.p50_net_after_vm_usd !== null && r.p50_net_after_vm_usd !== undefined) ? Number(r.p50_net_after_vm_usd) : Number(r.p50_net_profit || 0);
      const vmSub = Number(r.vm_cost_cum_usd || 0) > 0 ? `, net post-VM ${netAfterVm >= 0 ? '+' : ''}$${netAfterVm.toFixed(2)}` : '';
      return `<tr>
        <td><b>${esc(lbl)}</b></td>
        <td class="sub">${esc(r.date_utc)}</td>
        <td>$${Number(r.p25_equity || 0).toFixed(2)}</td>
        <td class="cyan"><b>$${Number(r.p50_equity || 0).toFixed(2)}</b> <span class="sub">(+$${Number(r.p50_net_profit || 0).toFixed(2)}${vmSub})</span></td>
        <td class="pos">+$${Number(r.p50_daily_pnl || 0).toFixed(2)}/d</td>
        <td class="pos"><b>$${Number(r.p75_equity || 0).toFixed(2)}</b></td>
      </tr>`;
    }).join('') || '<tr><td colspan="6" class="sub">No live_daily_projections.json horizons loaded.</td></tr>';
  }
}

function renderV6Expansion(v6) {
  const d = v6 || {};
  const xv = d.cross_venue_shadow || {};
  const l2 = d.l2_recorder || {};
  const pill = document.getElementById('v6_health_pill');
  if (pill) {
    const ok = Boolean(xv.service_healthy) || Number(d.a124_cycles || 0) > 0;
    pill.className = 'pill ' + (ok ? 'pill-ok' : 'pill-warn');
    pill.textContent = `Stage G (${xv.network_mode || 'init'}) #${xv.cycles_completed || 0} • A124 v6 #${d.a124_cycles || 0}`;
  }
  const strip = document.getElementById('v6_strip');
  if (strip) {
    const vh = xv.venue_health || {};
    const vBadges = ['polymarket', 'stx_ontario', 'forecastex', 'limitless', 'sx_bet', 'predict_fun'].map(vn => {
      const info = vh[vn] || {};
      const st = String(info.status || info.verified_outcome_state || 'IDLE');
      const cls = st.startsWith('OK') || st.includes('AUTHORIZED') ? 'pos' : 'sub';
      return `<span class="${cls}">${esc(vn.replace('_ontario', ' CAD'))}:${esc(st.slice(0, 12))}</span>`;
    }).join(' &bull; ');
    const todayMb = (Number(l2.bytes_today || 0) / (1024 * 1024)).toFixed(2);
    strip.innerHTML =
      `<span class="sf-chip">Evaluated Pairs/Slates: <b>${(d.evaluated_total || 0).toLocaleString()}</b> &bull; Verified Hits: <b class="pos">${d.opportunities_total || 0}</b></span>` +
      `<span class="sf-chip">Stage G Live Mkts: <b>${xv.live_markets_seen || 0}</b> (Matched Pairs: <b class="cyan">${xv.matched_pairs_seen || 0}</b> &bull; Deribit USDC Opts: <b>${d.deribit_usdc_quotes || 0}</b>)</span>` +
      `<span class="sf-chip">Candidate L2 Recorder: <b class="pos">${todayMb} / ${Number(l2.daily_cap_mb || 12).toFixed(1)} MB/d</b> (${l2.frames_recorded || 0} frames &bull; ${Number(l2.archive_mb || 0).toFixed(2)} MB disk)</span>` +
      `<span class="sf-chip">Venues: ${vBadges}</span>`;
  }
  const tb = document.getElementById('v6_engine_rows');
  if (tb) {
    const rows = d.engines || [];
    tb.innerHTML = rows.map(r => {
      const hitCls = r.opportunities_found > 0 ? 'pos' : 'sub';
      return `<tr>
        <td><b>${esc(r.strategy_id)}</b></td>
        <td class="sub">${esc(r.desc)}</td>
        <td><b>${Number(r.evaluated || 0).toLocaleString()}</b></td>
        <td class="${hitCls}"><b>${r.opportunities_found || 0}</b>${r.cycle_hits > 0 ? ` <span class="cyan">(+${r.cycle_hits} now)</span>` : ''}</td>
        <td><b>${r.shadow_wins || 0}W</b> / <span class="${r.shadow_losses > 0 ? 'neg' : 'sub'}">${r.shadow_losses || 0}L</span>${r.shadow_open > 0 ? ` <span class="cyan">(${r.shadow_open} open)</span>` : ''}</td>
        <td><span class="pill ${r.shadow_wins >= 8 && r.shadow_losses === 0 ? 'pill-ok' : 'pill-info'}">${r.shadow_wins >= 8 && r.shadow_losses === 0 ? 'GRAD-8 READY' : 'SHADOW ARMED'}</span></td>
      </tr>`;
    }).join('') || '<tr><td colspan="6" class="sub">Awaiting first v6 daemon scan cycle...</td></tr>';
  }
}

function renderStageBAttribution(sb) {
  if (!sb || sb.error) return;
  const k = sb.north_star_kpis || {};
  const fn = sb.opportunity_funnel || {};
  const stg = fn.stages || {};
  const db = fn.decay_buckets || {};
  const dCnt = db.counts || {};
  const dUsd = db.missed_profit_usd || {};
  const strip = document.getElementById('stageb_kpis_strip');
  if (strip) {
    const gId = sb.governing_identity || {};
    const cBas = Number(gId.contributed_capital_basis_usd ?? ((Number(gId.starting_reconciled_equity_usd || 60.92)) + Number(gId.net_deposits_usd || 0)));
    const nDep = Number(gId.net_deposits_usd || 0);
    const depTip = nDep !== 0 ? `Contributed Basis $${cBas.toFixed(2)} ($${Number(gId.starting_reconciled_equity_usd || 60.92).toFixed(2)} lock + $${nDep.toFixed(2)} deposit) -> ` : '';
    const netEc = Number(k.kpi_1_net_economic_pnl_usd ?? 0);
    const wGain = Number(k.kpi_1_wallet_gain_before_ops_usd ?? 0);
    const opsBurn = Number(k.kpi_1_prorated_ops_cost_usd ?? 0);
    const p1k = Number(k.kpi_2_net_pnl_per_1000_usd ?? 0);
    const capHr = Number(k.kpi_3_net_pnl_per_capital_hour_usd ?? 0);
    const bpsHr = Number(k.kpi_3_bps_per_capital_hour ?? 0);
    const uwLoss = Number(k.kpi_4_partial_basket_unwind_loss_usd ?? 0);
    const m5 = k.kpi_5_maker_markout_5s_cents !== null && k.kpi_5_maker_markout_5s_cents !== undefined ? `${Number(k.kpi_5_maker_markout_5s_cents).toFixed(2)}c` : 'armed';
    const m30 = k.kpi_5_maker_markout_30s_cents !== null && k.kpi_5_maker_markout_30s_cents !== undefined ? `${Number(k.kpi_5_maker_markout_30s_cents).toFixed(2)}c` : 'armed';
    const lat50 = k.kpi_6_signal_to_ack_p50_ms ?? k.kpi_6_http_post_p50_ms;
    const lat95 = k.kpi_6_signal_to_ack_p95_ms;
    const lat99 = k.kpi_6_signal_to_ack_p99_ms;
    const latTxt = lat50 !== null && lat50 !== undefined ? `${Number(lat50).toFixed(0)}/${lat95 ? Number(lat95).toFixed(0) : '-'}/${lat99 ? Number(lat99).toFixed(0) : '-'}ms` : '-';
    const capPct = k.kpi_7_expected_vs_realized_capture_pct !== null && k.kpi_7_expected_vs_realized_capture_pct !== undefined ? `${Number(k.kpi_7_expected_vs_realized_capture_pct).toFixed(1)}%` : '100.0%';
    const infPct = k.kpi_8_infra_burn_to_gross_profit_pct !== null && k.kpi_8_infra_burn_to_gross_profit_pct !== undefined ? `${Number(k.kpi_8_infra_burn_to_gross_profit_pct).toFixed(1)}%` : '-';
    const decMed = k.kpi_9_competitor_decay_median_ms !== null && k.kpi_9_competitor_decay_median_ms !== undefined ? `${Number(k.kpi_9_competitor_decay_median_ms).toFixed(1)}ms` : 'collecting';
    const gt40 = k.kpi_9_finland_capturable_gt40ms_pct !== null && k.kpi_9_finland_capturable_gt40ms_pct !== undefined ? ` (${Number(k.kpi_9_finland_capturable_gt40ms_pct).toFixed(0)}% >40ms)` : '';
    const acctGap = Number(k.kpi_10_wallet_accounting_discrepancy_usd ?? 0);
    strip.innerHTML =
      `<span class="sf-chip" title="${depTip}Pure Trading Gain ($${wGain.toFixed(2)}) minus Pro-Rated VM + AI Burn ($${opsBurn.toFixed(2)})">1. Net Econ PnL: <b class="${netEc >= 0 ? 'pos' : 'warn'}">${netEc >= 0 ? '+' : ''}$${netEc.toFixed(2)}</b> <span class="sub">(Trading ${wGain >= 0 ? '+' : ''}$${wGain.toFixed(2)} - Ops $${opsBurn.toFixed(2)})</span></span>` +
      `<span class="sf-chip">2. Net/$1k: <b class="pos">+$${p1k.toFixed(2)}</b></span>` +
      `<span class="sf-chip">3. $/Cap-Hr: <b class="cyan">$${capHr.toFixed(4)}/$-hr</b> (<b class="pos">+${bpsHr.toFixed(1)} bps/hr</b>)</span>` +
      `<span class="sf-chip">4. Unwind Bleed: <b class="${uwLoss <= 0.01 ? 'pos' : 'warn'}">$${uwLoss.toFixed(2)}</b> (${k.kpi_4_partial_basket_unwind_count ?? 0})</span>` +
      `<span class="sf-chip">5. Maker Markout (5s/30s): <b>${m5} / ${m30}</b> (N=${k.kpi_5_markout_samples ?? 0})</span>` +
      `<span class="sf-chip">6. Sig&rarr;Ack (p50/95/99): <b>${latTxt}</b></span>` +
      `<span class="sf-chip">7. Edge Capture: <b class="pos">${capPct}</b></span>` +
      `<span class="sf-chip">8. Infra/Gross: <b>${infPct}</b> ($${Number(k.kpi_8_daily_infra_burn_usd ?? 1.752).toFixed(2)}/d)</span>` +
      `<span class="sf-chip">9. Decay Med: <b>${decMed}</b>${gt40}</span>` +
      `<span class="sf-chip">10. Acct Diff: <b class="${acctGap <= 0.01 ? 'pos' : 'neg'}">$${acctGap.toFixed(4)}</b> (${k.kpi_10_orphan_orders_count ?? 0} orphans)</span>`;
  }
  const fStrip = document.getElementById('stageb_funnel_strip');
  if (fStrip) {
    fStrip.innerHTML =
      `<span class="sf-chip">Seen: <b>${stg.GROSS_ARB_SEEN ?? 0}</b></span>` +
      `<span class="sf-chip">Net L2 Valid: <b class="cyan">${stg.EXECUTABLE_NET_L2 ?? 0}</b></span>` +
      `<span class="sf-chip">Submitted: <b>${stg.ORDER_SUBMITTED ?? 0}</b></span>` +
      `<span class="sf-chip">Locked: <b class="pos">${stg.COMPLETE_BASKET_LOCKED ?? 0}</b></span>` +
      `<span class="sf-chip">Unwound: <b class="${(stg.PARTIAL_BASKET_UNWOUND || 0) > 0 ? 'warn' : 'pos'}">${stg.PARTIAL_BASKET_UNWOUND ?? 0}</b></span>` +
      `<span class="sf-chip">Competitor Swept: <b>${stg.COMPETITOR_DECAY_OBSERVED ?? 0}</b></span>`;
  }
  const rungPill = document.getElementById('stageb_rung_pill');
  if (rungPill) {
    if (db.rung2_migration_justified) {
      rungPill.className = 'pill pill-warn';
      rungPill.textContent = `Rung 2 EU Proximity Triggered ($${Number(db.rung2_eu_proximity_missed_15_40ms_monthly_proj_usd || 0).toFixed(0)}/mo > $${Number(db.rung2_trigger_threshold_usd || 60).toFixed(0)})`;
    } else {
      rungPill.className = 'pill pill-ok';
      rungPill.textContent = `Rung 1 Optimal (15-40ms Missed $${Number(db.rung2_eu_proximity_missed_15_40ms_monthly_proj_usd || 0).toFixed(2)}/mo < $${Number(db.rung2_trigger_threshold_usd || 60).toFixed(0)} Gate)`;
    }
  }
  const dTb = document.getElementById('stageb_decay_rows');
  if (dTb) {
    const bMeta = [
      ['lt_5ms', '< 5 ms (Sub-5ms)', 'Rung 4 Rust + eu-west-2 / #1 FIFO Maker', 'Quote Passive Maker #1 FIFO'],
      ['5_15ms', '5 - 15 ms', 'Rung 4 AWS eu-west-2 Co-Lo ($25k+ KYB)', 'Hold until $25k + KYB'],
      ['15_40ms', '15 - 40 ms', 'Rung 2 <12ms EU Proximity VM ($500+)', db.rung2_migration_justified ? 'TRIGGER RUNG 2 CUTOVER' : 'Monitor (>5x VM Delta Gate)'],
      ['gt_40ms', '> 40 ms', 'Rung 1 Finland e2-custom-2-4096 (NOW)', 'Capturable Live Now'],
    ];
    dTb.innerHTML = bMeta.map(([bk, lbl, rung, act]) => `<tr>
      <td><b>${esc(lbl)}</b></td>
      <td class="sub">${esc(rung)}</td>
      <td><b>${Number(dCnt[bk] || 0)}</b></td>
      <td>$${Number(dUsd[bk] || 0).toFixed(2)}</td>
      <td><span class="pill ${bk === 'gt_40ms' ? 'pill-ok' : 'pill-muted'}">${esc(act)}</span></td>
    </tr>`).join('');
  }
  const sTb = document.getElementById('stageb_sleeve_rows');
  if (sTb) {
    const sRows = (sb.by_sleeve || []).filter(x => x.is_active_riskless && (x.trades > 0 || x.open_positions > 0));
    sTb.innerHTML = sRows.slice(0, 12).map(s => {
      const fric = Number(s.taker_fees_usd || 0) + Number(s.partial_basket_unwind_loss_usd || 0);
      const np = Number(s.net_pnl_usd || 0);
      return `<tr>
        <td><b>${esc(shortSlv(s.sleeve))}</b></td>
        <td>${s.wins}W/${s.losses}L${s.open_positions > 0 ? ` <span class="cyan">(+${s.open_positions} open)</span>` : ''}</td>
        <td>+$${Number(s.gross_capture_usd || 0).toFixed(2)}</td>
        <td class="${fric > 0.01 ? 'warn' : 'sub'}">-$${fric.toFixed(2)}</td>
        <td class="${np >= 0 ? 'pos' : 'neg'}"><b>${np >= 0 ? '+' : ''}$${np.toFixed(2)}</b></td>
        <td class="pos"><b>+$${Number(s.net_pnl_per_1000_usd || 0).toFixed(2)}</b></td>
        <td class="cyan">${Number(s.occupied_capital_hours || 0).toFixed(1)}h (<b>+${Number(s.bps_per_capital_hour || 0).toFixed(0)} bps/h</b>)</td>
      </tr>`;
    }).join('') || '<tr><td colspan="7" class="sub">Awaiting settled active-riskless sleeve trades.</td></tr>';
  }
}

function setRadarFilter(f) {
  _radarFilter = f;
  ['ALL', 'LIVE_IPC', 'MACHINE_GUN', 'V6_EXPANSION', 'UMA_CARRY', 'POST_CLINCH', 'LOCKED_REWARD', 'SLATE_ARB'].forEach(k => {
    const b = document.getElementById('rad_flt_' + k);
    if (b) b.className = 'flt-btn' + (k === f ? ' active' : '');
  });
  if (_lastRadarData) renderRisklessRadar(_lastRadarData);
}

function setPmFilter(f) {
  _pmFilter = f;
  ['riskless', 'all'].forEach(k => {
    const b = document.getElementById('pm_flt_' + k);
    if (b) b.className = 'flt-btn' + (k === f ? ' active' : '');
  });
  if (_lastSnapshot) renderPmTables(_lastSnapshot.polymarket_live || {});
}

function setA124Filter(f) {
  _a124Filter = f;
  ['focus', 'v6', 'all'].forEach(k => {
    const b = document.getElementById('a124_flt_' + k);
    if (b) b.className = 'flt-btn' + (k === f ? ' active' : '');
  });
  if (_lastSnapshot) renderA124Sleeves((_lastSnapshot.alpha124 || {}).sleeves || []);
}

function fmtSecCompact(sec) {
  if (sec === null || sec === undefined || Number.isNaN(Number(sec))) return '-';
  const s = Math.max(0, Math.round(Number(sec)));
  if (s >= 86400) return `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h`;
  if (s >= 3600) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
  if (s >= 60) return `${Math.floor(s / 60)}m ${s % 60}s`;
  return `${s}s`;
}

function ztPillClass(st) {
  const s = String(st || '').toUpperCase();
  if (s === 'VERIFIED_COMPLETE' || s === 'COMPLETED' || s === 'VERIFIED_FACT' || s === 'DEPLOYED_VERIFIED') return 'pill-ok';
  if (s === 'OBSERVATION' || s === 'PENDING_VERIFICATION' || s === 'RUNNING' || s === 'CLAIMED') return 'pill-info';
  if (s === 'STALE_REVALIDATION_REQUIRED' || s === 'CHECKPOINTED' || s === 'PENDING' || s === 'READY' || s === 'BLOCKED' || s === 'BLOCKED_AUTHORIZATION') return 'pill-warn';
  if (s === 'CONTRADICTED' || s === 'REJECTED' || s === 'FAILED' || s === 'FAILED_PERMANENT' || s === 'ROLLED_BACK' || s === 'ESCALATED') return 'pill-bad';
  return 'pill-muted';
}

function radarPill(bucket) {
  if (bucket === 'LIVE_IPC') return ['pill-ok', 'LIVE IPC'];
  if (bucket === 'MACHINE_GUN') return ['pill-mg', 'MACHINE-GUN'];
  if (bucket === 'V6_EXPANSION') return ['pill-info', 'V6 / X-VENUE'];
  if (bucket === 'UMA_CARRY') return ['pill-info', 'UMA CARRY'];
  if (bucket === 'POST_CLINCH') return ['pill-ok', 'POST-CLINCH'];
  if (bucket === 'LOCKED_REWARD') return ['pill-warn', 'LOCKED + POOL'];
  if (bucket === 'SLATE_ARB') return ['pill-info', 'SLATE ARB'];
  return ['pill-muted', bucket || 'RADAR'];
}

function renderRisklessRadar(rad) {
  _lastRadarData = rad || {};
  const s = _lastRadarData.summary || {};
  const cnts = s.counts || {};
  const strip = document.getElementById('radar_strip');
  if (strip) {
    const mgCnt = Number(cnts.MACHINE_GUN || 0);
    const mgBadge = mgCnt > 0
      ? `<b style="color:var(--purple);">${mgCnt} Live MG Streams</b>`
      : `<span class="sub">Armed (Auto-discovers on deploy)</span>`;
    const scanAgeCls = (s.age_sec !== null && s.age_sec !== undefined && Number(s.age_sec) > 5400) ? 'warn' : '';
    strip.innerHTML =
      `<span class="sf-chip">Universe Scan: <b>${(s.active_markets_scanned || 0).toLocaleString()}</b> Active Markets (<b>${(s.fee_free_markets || 0).toLocaleString()}</b> 0%-Fee &bull; <span class="${scanAgeCls}">${fmtSecCompact(s.age_sec)} old</span>)</span>` +
      `<span class="sf-chip">Live Harvester IPC: <b class="pos">${cnts.LIVE_IPC || 0}</b></span>` +
      `<span class="sf-chip">Machine-Gun: ${mgBadge}</span>` +
      `<span class="sf-chip">UMA Carries: <b class="cyan">${cnts.UMA_CARRY || 0}</b> &bull; Post-Clinch: <b class="pos">${cnts.POST_CLINCH || 0}</b> &bull; Locked+Pool: <b class="warn">${cnts.LOCKED_REWARD || 0}</b> &bull; Slate Arbs: <b>${cnts.SLATE_ARB || 0}</b></span>` +
      `<span class="sf-chip">Peak Carry Velocity: <b class="pos">${Number(s.top_bps_per_hr || 0).toFixed(0)} bps/hr</b></span>`;
  }
  const allOpps = _lastRadarData.opportunities || [];
  const rows = allOpps.filter(o => _radarFilter === 'ALL' ? !(o.bucket === 'LOCKED_REWARD' && !o.authorized_live) : o.bucket === _radarFilter);
  const tb = document.getElementById('radar_rows');
  if (!tb) return;
  if (!rows.length) {
    const emptyMsg = _radarFilter === 'MACHINE_GUN'
      ? 'Awaiting parallel Machine-Gun Riskless stream deployment — auto-discovery armed on *machine_gun*.json / .jsonl & MG_* sleeves.'
      : `No opportunities in bucket "${esc(_radarFilter)}" right now.`;
    tb.innerHTML = `<tr><td colspan="8" class="sub">${emptyMsg}</td></tr>`;
    return;
  }
  tb.innerHTML = rows.slice(0, 24).map(o => {
    const [pCls, pTxt] = radarPill(o.bucket);
    const remTxt = (o.rem_hours !== null && o.rem_hours !== undefined)
      ? (Number(o.rem_hours) < 1 ? `${Math.max(1, Math.round(Number(o.rem_hours) * 60))}m` : `${Number(o.rem_hours).toFixed(1)}h`)
      : '';
    const extraBits = [shortSlv(o.sleeve), o.market_id ? `Mkt #${o.market_id}` : '', o.extra || '', remTxt ? `Win ~${remTxt}` : ''].filter(Boolean).join(' • ');
    const gatePill = o.authorized_live
      ? '<span class="pill pill-ok">LIVE ARMED</span>'
      : '<span class="pill pill-warn">SHADOW G8</span>';
    return `<tr>
      <td><span class="pill ${pCls}">${esc(pTxt)}</span></td>
      <td><b>${esc(o.title)}</b><div class="sub">${esc(extraBits)}</div></td>
      <td><code>${esc(o.side)}</code></td>
      <td><b>$${Number(o.entry_px || 0).toFixed(3)}</b></td>
      <td class="pos"><b>+${Number(o.edge_bps || 0).toFixed(0)} bps</b></td>
      <td class="cyan"><b>${Number(o.bps_per_hr || 0).toFixed(0)} bps/hr</b></td>
      <td>$${Number(o.liquidity_usd || 0).toLocaleString()}</td>
      <td>${gatePill}</td>
    </tr>`;
  }).join('');
}

function renderLiveBook(pm, dcfg, cfgVer, elapsedSec=0) {
  const acts = pm.active_positions || [];
  const restOrds = pm.resting_orders || [];
  const quoteNotional = restOrds.reduce((s, x) => s + Number(x.notional_usd || 0), 0);
  const quoteEdge = restOrds.reduce((s, x) => s + Number(x.redeem_edge_usd ?? Math.max(0, Number(x.shares || 0) - Number(x.notional_usd || 0))), 0);
  const risklessOnly = dcfg.riskless_only_mode !== false;
  const pillEl = document.getElementById('clob_quote_pill');
  if (pillEl) {
    pillEl.textContent = restOrds.length > 0
      ? `${restOrds.length} Working @ 0% Maker Fee ($${quoteNotional.toFixed(2)} | +$${quoteEdge.toFixed(2)} Redeem Edge)`
      : `0% Maker Fee Scanner Armed`;
  }
  const bannerEl = document.getElementById('live_book_banner');
  if (bannerEl) {
    bannerEl.innerHTML = risklessOnly
      ? `<b>100% Pure Riskless Lock Active</b> &bull; Unhedged Crypto Directional &amp; Fee-Sports Legging OFF &bull; Filled Positions: <b>${acts.length}</b> &bull; Resting CLOB Maker Orders: <b class="pos">${restOrds.length}</b> (<b>${Number(pm.quoting_utilization_pct || 0).toFixed(1)}%</b> cash deployed)`
      : `<b>Hybrid Mode v${esc(cfgVer)}</b> &bull; Filled Positions: <b>${acts.length}</b> &bull; Resting CLOB Orders: <b>${restOrds.length}</b>`;
  }

  let html = '';
  if (restOrds.length > 0) {
    html += `<table>
      <thead>
        <tr>
          <th>Resolved Market Question &amp; Order ID</th>
          <th>Side / Outcome &times; Shares</th>
          <th>Limit Bid (Notional)</th>
          <th>Guaranteed $1.00 Redeem Edge</th>
          <th>Est. Window &amp; Velocity</th>
          <th>CLOB L2 Status (Live Age)</th>
        </tr>
      </thead>
      <tbody>` +
      restOrds.map(o => {
        const px = Number(o.price || 0);
        const sh = Number(o.shares || 0);
        const nt = Number(o.notional_usd || 0);
        const edgeUsd = Number(o.redeem_edge_usd ?? Math.max(0, sh * 1.0 - nt));
        const edgeBps = Number(o.edge_bps ?? ((1 - px) * 10000));
        const bpsHr = Number(o.est_bps_per_hr || 0);
        const remMin = (o.rem_min !== null && o.rem_min !== undefined) ? Math.max(0, Number(o.rem_min) - elapsedSec / 60.0) : null;
        const remTxt = remMin !== null
          ? `${remMin.toFixed(0)}m (${bpsHr.toFixed(0)} bps/hr)`
          : `UMA / Settle (~${bpsHr.toFixed(0)} bps/hr)`;
        const oidShort = String(o.order_id || '').slice(0, 14) + '...';
        const outLbl = o.outcome ? `${o.side} (${o.outcome})` : o.side;
        const liveAge = Math.max(0, Math.round(Number(o.age_sec || 0) + elapsedSec));
        return `<tr>
          <td><b>${esc(o.title)}</b><div class="sub">${esc(shortSlv(o.sleeve))} &bull; Mkt #${esc(o.market_id || '-')} &bull; <code>${esc(oidShort)}</code></div></td>
          <td><b class="pos">${esc(outLbl)}</b> &times; <b>${sh.toFixed(2)}</b>${Number(o.matched_shares || 0) > 0 ? ` <span class="cyan">(${Number(o.matched_shares).toFixed(1)} filled)</span>` : ''}</td>
          <td><b>$${px.toFixed(4)}</b> <span class="sub">($${nt.toFixed(2)})</span></td>
          <td class="pos"><b>+$${edgeUsd.toFixed(2)}</b> <span class="sub">(+${edgeBps.toFixed(0)} bps @ 0% fee)</span></td>
          <td class="cyan">${esc(remTxt)}</td>
          <td><span class="pill pill-ok">${esc(o.status || 'LIVE')} ON CLOB</span> <span class="sub">${fmtSecCompact(liveAge)}</span></td>
        </tr>`;
      }).join('') + `</tbody></table>`;
  } else {
    html += `<div class="sub" style="padding:8px 4px;">0 resting orders on CLOB at this exact second &mdash; Harvester is actively scanning live IPC &amp; rotating 0%-fee Maker quotes.</div>`;
  }

  if (acts.length > 0) {
    html += `<div style="margin:10px 0 5px 0;font-weight:700;color:var(--cyan);">FILLED ACTIVE POSITIONS (${acts.length} Open &mdash; Cost Basis $${acts.reduce((s, x) => s + Number(x.notional_usd || 0), 0).toFixed(2)} &bull; MTM Bid $${acts.reduce((s, x) => s + Number(x.mtm_bid_usd || 0), 0).toFixed(2)}):</div>
      <table><thead><tr><th>Market</th><th>Side / Shares</th><th>Entry / Cost</th><th>Live Bid / Ask</th><th>Resting Exit</th><th>MTM Bid (uPnL)</th></tr></thead><tbody>` +
      acts.map(a => {
        const nm = a.title ? a.title : `${a.asset || ''} ${a.horizon || ''}`.trim();
        const upnl = Number(a.unreal_bid_pnl_usd || 0);
        const uCls = upnl >= 0 ? 'pos' : 'neg';
        const ba = (a.best_bid !== null && a.best_bid !== undefined) ? `$${Number(a.best_bid).toFixed(3)} / $${Number(a.best_ask ?? 1).toFixed(3)}` : '-';
        return `<tr>
          <td><b>${esc(nm)}</b><div class="sub">${esc(shortSlv(a.sleeve))} &bull; Mkt #${esc(a.market_id || '')}</div></td>
          <td><b class="pos">${esc(a.side)}</b> &times; ${Number(a.shares || 0).toFixed(2)}</td>
          <td>$${Number(a.entry_px || 0).toFixed(4)} ($${Number(a.notional_usd || 0).toFixed(2)})</td>
          <td>${ba}</td>
          <td>SELL @ <b>$${Number(a.target_tp || 0).toFixed(3)}</b> ($${Number(a.tp_val_usd || 0).toFixed(2)}) [${esc(a.status)}]</td>
          <td><b>$${Number(a.mtm_bid_usd || 0).toFixed(2)}</b> <span class="${uCls}">(${upnl >= 0 ? '+' : ''}$${upnl.toFixed(2)})</span></td>
        </tr>`;
      }).join('') + `</tbody></table>`;
  }
  const ab = document.getElementById('active_box');
  if (ab) ab.innerHTML = html;
}

function renderPmTables(pm) {
  const restOrds = pm.resting_orders || [];
  const restBySlv = {};
  restOrds.forEach(o => { const k = o.sleeve || 'BOND1_UMA_RESOLUTION_CARRY'; restBySlv[k] = (restBySlv[k] || 0) + 1; });

  const sparkLbl = document.getElementById('spark_lbl');
  if (_pmFilter === 'riskless') {
    const curve = (pm.pure_riskless_curve && pm.pure_riskless_curve.length >= 2) ? pm.pure_riskless_curve : [0, Number(pm.pure_riskless_pnl_usd || 0)];
    drawSpark(curve);
    const lockStart = Number(pm.riskless_lock_start_usd || 60.92);
    const netDep = Number(pm.net_deposits_post_lock_usd || 0);
    const basisEq = Number(pm.contributed_capital_basis_usd ?? (lockStart + netDep));
    const curEq = Number(pm.equity_usd || pm.bankroll_usd || 0);
    const frozenDispSpark = Number(pm.frozen_disputed_open_usd ?? Number((pm.nav_triad || {}).disputed_uma_cost_usd || 0));
    const reconEqSpark = Number(pm.reconciled_undisputed_equity_usd ?? Math.max(0, curEq - frozenDispSpark));
    const postCash = Number(pm.post_lock_cash_delta_usd ?? (curEq - basisEq));
    const eqTargetNote = frozenDispSpark > 0.005 ? `$${reconEqSpark.toFixed(2)} liquid + $${frozenDispSpark.toFixed(2)} disputed KMIA` : `$${curEq.toFixed(2)}`;
    const depNote = netDep > 0 ? ` ($${lockStart.toFixed(2)} + $${netDep.toFixed(2)} dep = $${basisEq.toFixed(2)} basis &rarr; ${eqTargetNote})` : ` ($${lockStart.toFixed(2)} &rarr; ${eqTargetNote})`;
    if (sparkLbl) sparkLbl.innerHTML = `All-Time Riskless: <b class="pos">+$${Number(pm.pure_riskless_pnl_usd || 0).toFixed(2)}</b> (${pm.pure_riskless_wins ?? 0}W/${pm.pure_riskless_losses ?? 0}L &bull; ${Number(pm.pure_riskless_wr_pct ?? 100).toFixed(1)}% WR) &bull; Post-Lock Trading Gain (ex-KMIA dispute): <b class="pos">${postCash >= 0 ? '+' : ''}$${postCash.toFixed(2)}</b>${depNote}`;
  } else {
    drawSpark(pm.equity_curve || []);
    if (sparkLbl) sparkLbl.innerHTML = `All-Time Account Curve (Incl. Paused Legacy Directional): <b>${Number(pm.epoch_net_pnl_usd || 0) >= 0 ? '+' : ''}$${Number(pm.epoch_net_pnl_usd || 0).toFixed(2)}</b>`;
  }

  const allStrats = pm.live_strategies || [];
  const strats = (_pmFilter === 'riskless' ? allStrats.filter(s => s.is_active_riskless) : allStrats).slice().sort((a, b) => {
    const qa = Number(a.open || 0) * 100 + (restBySlv[a.sleeve] || 0) * 10 + (Number(a.epoch_w || 0) > 0 ? 5 : 0);
    const qb = Number(b.open || 0) * 100 + (restBySlv[b.sleeve] || 0) * 10 + (Number(b.epoch_w || 0) > 0 ? 5 : 0);
    if (qb !== qa) return qb - qa;
    return Number(b.epoch_pnl || 0) - Number(a.epoch_pnl || 0);
  });
  const stEl = document.getElementById('pm_strats');
  if (stEl) {
    stEl.innerHTML = strats.map(st => {
      const vp = Number(st.v51_pnl || 0), ep = Number(st.epoch_pnl || 0);
      const rCnt = restBySlv[st.sleeve] || 0;
      const openCell = rCnt > 0 ? `${st.open || 0} <span class="pill pill-ok" style="padding:1px 6px;font-size:10px;">${rCnt} quoting</span>` : `${st.open || 0}`;
      const stBadge = st.is_active_riskless ? '' : ' <span class="pill pill-muted" style="font-size:9.5px;padding:1px 5px;">PAUSED</span>';
      const flCnt = Number(st.flat_merges || 0);
      const flTag = flCnt > 0 ? ` <span class="sub" title="${flCnt} pre-expiry $0.00 complete-set merge(s)">(${flCnt} flat)</span>` : '';
      return `<tr>
        <td><b>${esc(shortSlv(st.sleeve))}</b>${stBadge}</td>
        <td class="sub">${esc(st.desc || '')}</td>
        <td>${openCell}</td>
        <td><b>${st.v51_w || 0}W / ${st.v51_l || 0}L</b>${flTag}</td>
        <td class="${vp >= 0 ? 'pos' : 'neg'}">${vp >= 0 ? '+' : ''}$${vp.toFixed(2)}</td>
        <td>${st.epoch_w || 0}W / ${st.epoch_l || 0}L${flTag}</td>
        <td class="${ep >= 0 ? 'pos' : 'neg'}"><b>${ep >= 0 ? '+' : ''}$${ep.toFixed(2)}</b></td>
      </tr>`;
    }).join('') || '<tr><td colspan="7" class="sub">No strategy rows match filter.</td></tr>';
  }

  const allTrades = pm.recent_closed || [];
  const trades = _pmFilter === 'riskless' ? allTrades.filter(c => c.is_active_riskless) : allTrades;
  const trEl = document.getElementById('pm_trades');
  if (trEl) {
    trEl.innerHTML = trades.slice(0, 14).map(c => {
      const recBadge = c.fee_reconciled ? ` <span class="cyan" title="On-chain wallet +$${Number(c.net_pnl_usd).toFixed(2)} (raw JSON $${Number(c.raw_pnl_usd).toFixed(2)})">*wallet</span>` : '';
      const tsClosed = c.time_et || fmtOttawa(c.unix_ts || c.time_utc, 'md_hms');
      const mktHtml = c.title
        ? `<b>${esc(c.title.length > 54 ? c.title.slice(0, 52) + '…' : c.title)}</b><div class="sub">${esc(c.side_tag || c.asset)}${c.market_id ? ` • #${esc(c.market_id)}` : ''}</div>`
        : `<b>${esc(c.asset)}</b>`;
      const exPxTxt = (c.exit_px !== null && c.exit_px !== undefined && c.exit_px !== '') ? esc(c.exit_px) : '1.000';
      return `<tr>
        <td style="white-space:nowrap;">${esc(tsClosed)}</td>
        <td>${mktHtml}</td>
        <td class="sub">${esc(shortSlv(c.sleeve || '').slice(0, 20))}</td>
        <td>${esc(c.entry_px)} &rarr; ${exPxTxt}</td>
        <td>$${Number(c.notional_usd || 0).toFixed(2)}</td>
        <td class="${c.net_pnl_usd >= 0 ? 'pos' : 'neg'}"><b>${c.net_pnl_usd >= 0 ? '+' : ''}$${Number(c.net_pnl_usd || 0).toFixed(2)}</b>${recBadge}</td>
        <td>${esc((c.reason || '').slice(0, 26))}</td>
      </tr>`;
    }).join('') || '<tr><td colspan="7" class="sub">No closed trades in current filter (click "All Historical" to view legacy paused sleeves).</td></tr>';
  }
}

function renderA124Sleeves(sleeves) {
  const rows = _a124Filter === 'v6'
    ? sleeves.filter(s => Boolean(s.is_v6))
    : (_a124Filter === 'focus'
      ? sleeves.filter(s => !s.is_paused && (s.is_live || s.is_machine_gun || (s.losses === 0 && (s.wins > 0 || s.open > 0 || s.pending_quotes > 0))))
      : sleeves);
  const tb = document.getElementById('a124_sleeves');
  if (!tb) return;
  tb.innerHTML = rows.map(s => {
    const qBadge = s.pending_quotes ? ` <span class="warn">(${s.pending_quotes}q)</span>` : '';
    const mgBadge = s.is_machine_gun ? ` <span class="pill pill-mg" style="font-size:9.5px;padding:1px 5px;">MG</span>` : (s.is_v6 ? ` <span class="pill pill-info" style="font-size:9.5px;padding:1px 5px;">V6</span>` : '');
    const gCls = s.tier_tag === 'PROMOTED' ? 'pos' : (s.tier_tag === 'MACHINE_GUN' ? 'cyan' : (s.tier_tag === 'PAUSED' ? 'neg' : (s.losses === 0 && s.wins >= 4 ? 'warn' : (s.is_live ? 'pos' : 'sub'))));
    const pct = Number(s.grad8_pct ?? (s.losses === 0 ? Math.min(100, Math.round(100 * Math.min(s.wins || 0, 8) / 8)) : 0));
    const barCol = s.tier_tag === 'PROMOTED' ? '#3fb950' : (s.losses > 0 ? '#f85149' : '#39d0d8');
    const barHtml = `<span class="g8-bar"><span class="g8-fill" style="width:${pct}%;background:${barCol};"></span></span>`;
    return `<tr>
      <td><b>${esc(shortSlv(s.sleeve))}</b>${mgBadge}${qBadge}</td>
      <td>${esc(s.open)}</td>
      <td><b>${esc(s.wins)}W</b> / <span class="${s.losses > 0 ? 'neg' : 'sub'}">${esc(s.losses)}L</span></td>
      <td class="${gCls}">${barHtml}<b>${esc(s.grad8_progress)}</b></td>
      <td class="${s.t1000_pnl_usd >= 0 ? 'pos' : 'neg'}"><b>${s.t1000_pnl_usd >= 0 ? '+' : ''}$${Number(s.t1000_pnl_usd || 0).toFixed(2)}</b></td>
    </tr>`;
  }).join('') || '<tr><td colspan="5" class="sub">No shadow sleeves match filter.</td></tr>';
}

function renderPaaAutonomy(paa, elapsedSec=0) {
  if (!paa) return;
  const hbs = paa.heartbeats || {};
  const dirHb = hbs.paa_director || paa.director_heartbeat || {};
  const monHb = hbs.paa_monitor || ((paa.monitoring_health || {}).paa_monitor) || {};
  const supHb = hbs.paa_supervisor || ((paa.monitoring_health || {}).paa_supervisor) || {};
  const zt = paa.zero_trust || {};
  const tc = paa.task_counts_by_state || {};
  const vf = paa.verified_financial_performance || {};
  const br = paa.budget_and_resources || {};
  const lad = paa.research_ladder || {};

  const dirAge = dirHb.age_sec !== undefined && dirHb.age_sec !== null ? (Number(dirHb.age_sec) + elapsedSec) : null;
  const monAge = monHb.age_sec !== undefined && monHb.age_sec !== null ? (Number(monHb.age_sec) + elapsedSec) : null;
  const supAge = supHb.age_sec !== undefined && supHb.age_sec !== null ? (Number(supHb.age_sec) + elapsedSec) : null;

  const pulseEl = document.getElementById('paa_live_pulse');
  if (pulseEl) {
    const supTag = paa.pid1_supervisor_timer === 'active'
      ? ` &bull; PID-1 Sup: <b class="pos">active</b>`
      : ` &bull; Monitor+Director: <b class="pos">ACTIVE</b>`;
    pulseEl.innerHTML = `VM SQLite Live Probe: <b>${esc(paa.live_probed_at_et || '-')} ET</b> (${Math.round(elapsedSec)}s ago &bull; Poll #${_pollSeq})${supTag}`;
  }

  const verDone = (tc.VERIFIED_COMPLETE || 0) + (tc.COMPLETED || 0);
  const pendVer = tc.PENDING_VERIFICATION || 0;
  const rejCnt = tc.REJECTED || 0;
  const blkCnt = (tc.BLOCKED || 0) + (tc.BLOCKED_AUTHORIZATION || 0);
  const runCnt = (tc.RUNNING || 0) + (tc.CLAIMED || 0) + (tc.PENDING || 0) + (tc.READY || 0) + (tc.CHECKPOINTED || 0);
  const maxCtx = Number(zt.max_context_pct || 0);
  const ctxCap = Number(zt.context_cap_pct || 60);
  const ctxFillW = Math.min(100, Math.round((maxCtx / Math.max(1, ctxCap)) * 100));
  const ctxColor = maxCtx >= ctxCap ? '#d29922' : '#3fb950';

  const stripEl = document.getElementById('paa_strip');
  if (stripEl) {
    const stopOk = !paa.master_stop_engaged && !paa.accounting_safeguard_active;
    const rl = paa.riskless_kpis || {};
    const rlOn = rl.riskless_only_mode !== false;
    const pureW = Number(rl.pure_riskless_live_wins ?? 0);
    const pureL = Number(rl.pure_riskless_live_losses ?? 0);
    const purePnl = Number(rl.pure_riskless_realized_pnl_usd ?? 0);
    const zlShdw = Number(vf.zero_loss_shadow_t1000_pnl_usd || 0);
    const zlWins = Number(vf.zero_loss_shadow_wins || 0);
    const simLbl = zlWins > 0
      ? `Zero-Loss Shadow <b class="pos">+$${zlShdw.toFixed(0)}</b> (${zlWins}W/0L <i>non-cash</i>)`
      : `Sim Shadow +$${Number(vf.simulated_shadow_t1000_pnl_usd || 0).toFixed(0)} <i>non-cash</i>`;
    const supSuffix = (supAge !== null && supAge <= 3600) ? ` &bull; 2m Sup: <b>${fmtSecCompact(supAge)}</b>` : '';
    stripEl.innerHTML =
      `<span class="sf-chip">Mode: <b class="${rlOn ? 'pos' : 'warn'}">${rlOn ? '100% RISKLESS LOCK' : 'HYBRID'}</b> (Pure Live <b class="${pureL === 0 ? 'pos' : 'warn'}">${pureW}W/${pureL}L</b> ${purePnl >= 0 ? '+' : ''}$${purePnl.toFixed(2)})</span>` +
      `<span class="sf-chip">Director: <b class="${dirHb.status === 'OK' || dirHb.status === 'RUNNING_CYCLE' ? 'pos' : 'warn'}">${esc(dirHb.status || 'INIT')}</b> (#${dirHb.cycle_count ?? 0}, ${fmtSecCompact(dirAge)})</span>` +
      `<span class="sf-chip">1m Monitor: <b class="${monHb.status === 'OK' ? 'pos' : 'warn'}">${esc(monHb.status || 'INIT')}</b> (${fmtSecCompact(monAge)})${supSuffix}</span>` +
      `<span class="sf-chip">Safeguards: <b class="${stopOk ? 'pos' : 'neg'}">${paa.master_stop_engaged ? 'MASTER STOP' : (paa.accounting_safeguard_active ? 'ACCT FREEZE' : 'CLEAR')}</b></span>` +
      `<span class="sf-chip">Tier-A Policies: <b class="${(paa.tier_a_intact_count || 0) >= 5 ? 'pos' : 'neg'}">${paa.tier_a_intact_count ?? 0}/5 IMMUTABLE</b></span>` +
      `<span class="sf-chip">Tier-B Facts: <b class="pos">${zt.verified_facts_fresh ?? 0} Fresh</b> &bull; <span class="warn">${zt.verified_facts_stale ?? 0} Stale</span> &bull; <b class="${(zt.verified_facts_contradicted || 0) > 0 ? 'neg' : 'sub'}">${zt.verified_facts_contradicted ?? 0} Contradicted</b></span>` +
      `<span class="sf-chip">Stateless Sessions: <b class="pos">${zt.fresh_session_pct ?? 100}% Fresh</b> (N=${zt.sessions_total ?? 0}) &bull; Peak Ctx <b>${maxCtx.toFixed(1)}%</b>/${ctxCap}%<span class="ctx-bar-bg"><span class="ctx-bar-fg" style="width:${ctxFillW}%;background:${ctxColor};"></span></span></span>` +
      `<span class="sf-chip">Tasks: <b class="pos">${verDone} Verified</b> &bull; <span class="warn">${runCnt} Queue/Run</span> &bull; <b>${pendVer} PendVerif</b> &bull; <span class="${rejCnt ? 'neg' : 'sub'}">${rejCnt} Rej</span> &bull; <span class="${blkCnt ? 'warn' : 'sub'}">${blkCnt} Blocked</span></span>` +
      `<span class="sf-chip">AI Spend Today: <b>$${Number(br.daily_ai_cost_usd || 0).toFixed(4)}</b> / $${Number(br.max_daily_ai_cost_usd || 2.5).toFixed(2)} (${br.daily_ai_calls ?? 0}/${br.max_daily_ai_calls ?? 96} calls)</span>` +
      `<span class="sf-chip">Wallet vs Sim: <b>$${Number(vf.free_cash_pusd || 0).toFixed(2)} pUSD</b> (Acct Diff <b class="pos">$${Number(vf.accounting_discrepancy_usd || 0).toFixed(4)}</b> &bull; ${simLbl})</span>`;
  }

  const timersEl = document.getElementById('paa_timers');
  if (timersEl) {
    const tRows = (paa.systemd_timers || []).slice().sort((a, b) => (a.next_in_sec ?? 999999) - (b.next_in_sec ?? 999999));
    timersEl.innerHTML = tRows.map(t => {
      const nxtRem = t.next_in_sec !== null && t.next_in_sec !== undefined ? Math.max(0, Number(t.next_in_sec) - elapsedSec) : null;
      const lstAgo = t.last_ago_sec !== null && t.last_ago_sec !== undefined ? (Number(t.last_ago_sec) + elapsedSec) : null;
      const fireCls = nxtRem !== null && nxtRem <= 15 ? 'pos' : 'warn';
      return `<tr>
        <td><b>${esc(t.unit)}</b></td>
        <td style="white-space:nowrap;">${esc(t.last_et || '-')}</td>
        <td class="sub">${fmtSecCompact(lstAgo)}</td>
        <td class="${fireCls}"><b>${nxtRem !== null && nxtRem <= 0.5 ? 'FIRING...' : fmtSecCompact(nxtRem)}</b></td>
      </tr>`;
    }).join('') || '<tr><td colspan="4" class="sub">No systemd PAA timers found</td></tr>';
  }

  const depEl = document.getElementById('paa_deploys');
  if (depEl) {
    depEl.innerHTML = (paa.deployments || []).map(d => {
      const gatesLbl = `${d.qa_passed ? 'QA✓' : 'QA✗'} ${d.canary_passed ? 'Canary✓' : 'Canary✗'}`;
      return `<tr>
        <td title="${esc(d.updated_et)}"><b>${esc(String(d.release_id || '').slice(0, 18))}</b></td>
        <td><code>${esc(d.sha || '-')}</code></td>
        <td class="sub">${esc(gatesLbl)}</td>
        <td><span class="pill ${ztPillClass(d.state)}">${esc(d.state)}</span></td>
      </tr>`;
    }).join('') || '<tr><td colspan="4" class="sub">No releases recorded yet</td></tr>';
  }

  const factsEl = document.getElementById('paa_facts');
  if (factsEl) {
    factsEl.innerHTML = (paa.verified_facts || []).map(f => {
      const rem = f.ttl_remaining_sec !== null && f.ttl_remaining_sec !== undefined ? (Number(f.ttl_remaining_sec) - elapsedSec) : -1;
      const effSt = f.effective_status === 'CONTRADICTED' ? 'CONTRADICTED' : (rem <= 0 ? 'STALE_REVALIDATION_REQUIRED' : f.effective_status);
      const valStr = typeof f.value === 'object' ? JSON.stringify(f.value).slice(0, 34) : String(f.value);
      return `<tr>
        <td title="Source: ${esc(f.source_ref)} (${esc(f.verified_by)})"><b>${esc(f.fact_key)}</b></td>
        <td><code>${esc(valStr)}</code></td>
        <td><span class="pill ${ztPillClass(effSt)}">${esc(effSt === 'STALE_REVALIDATION_REQUIRED' ? 'STALE_TTL' : effSt)}</span></td>
        <td class="${rem <= 0 ? 'warn' : 'pos'}">${rem <= 0 ? 'expired' : fmtSecCompact(rem)}</td>
      </tr>`;
    }).join('') || '<tr><td colspan="4" class="sub">Awaiting next Monitor/Accountant cycle</td></tr>';
  }

  const sesEl = document.getElementById('paa_sessions');
  if (sesEl) {
    sesEl.innerHTML = (paa.recent_sessions || []).map(s => `
      <tr>
        <td style="white-space:nowrap;">${esc(s.created_et || '-')}</td>
        <td title="${esc(s.task_id)}"><b>${esc(String(s.stage_role || '').slice(0, 24))}</b></td>
        <td class="${s.fresh_session ? 'pos' : 'warn'}"><b>${s.fresh_session ? 'FRESH' : 'CONT'}</b></td>
        <td>${Number(s.context_pct || 0).toFixed(1)}%</td>
      </tr>
    `).join('') || '<tr><td colspan="4" class="sub">0 stateless AI sessions invoked yet</td></tr>';
  }

  const ladEl = document.getElementById('paa_ladder');
  if (ladEl) {
    ladEl.innerHTML =
      `Tier-C Evidence Ladder: <span class="pill pill-muted">HYPOTHESIS: ${lad.HYPOTHESIS ?? 0}</span> &rarr; ` +
      `<span class="pill pill-muted">BACKTEST: ${lad.BACKTESTED ?? 0}</span> &rarr; ` +
      `<span class="pill pill-info">OOS: ${lad.OOS_TESTED ?? 0}</span> &rarr; ` +
      `<span class="pill pill-warn">SHADOW: ${lad.SHADOW_VALIDATED ?? 0}</span> &rarr; ` +
      `<span class="pill pill-ok">LIVE_VERIFIED: ${lad.LIVE_VERIFIED ?? 0}</span>`;
  }

  const tskEl = document.getElementById('paa_tasks');
  if (tskEl) {
    tskEl.innerHTML = (paa.recent_tasks || []).map(t => `
      <tr>
        <td><b>${esc(t.priority)}</b></td>
        <td title="${esc(t.task_id)} | ${esc(t.last_error || t.next_action)}"><b>${esc(t.category)}</b>: ${esc(t.title)}</td>
        <td>${esc(t.sessions)}</td>
        <td><span class="pill ${ztPillClass(t.state)}">${esc(t.state)}</span></td>
      </tr>
    `).join('') || '<tr><td colspan="4" class="sub">No tasks in SQLite queue</td></tr>';
  }

  const evEl = document.getElementById('paa_events');
  if (evEl) {
    evEl.innerHTML = (paa.recent_events || []).map(e =>
      `<div><span class="sub">${esc(e.ts_et)}</span> [<b>${esc(e.component)}</b>] <span class="pos">${esc(e.event_type)}</span> ${esc(e.details)}</div>`
    ).join('') || '<div class="sub">No task events logged yet</div>';
  }
}

function tickPaaLiveCounters() {
  if (!_lastSyncClientMs) return;
  const elapsed = Math.max(0, (Date.now() - _lastSyncClientMs) / 1000.0);
  if (_lastMetaPrefix) {
    const mEl = document.getElementById('meta');
    if (mEl) mEl.textContent = `${_lastMetaPrefix} | Live Poll #${_pollSeq} (${Math.floor(elapsed)}s ago)`;
  }
  if (_lastSnapshot) {
    const scfg = _lastSnapshot.strategy_config || {};
    renderLiveBook(_lastSnapshot.polymarket_live || {}, scfg.directional || {}, scfg.schema_version || '5.4.1', elapsed);
  }
  if (_lastPaaData) {
    renderPaaAutonomy(_lastPaaData, elapsed);
  }
}
setInterval(tickPaaLiveCounters, 1000);

function setSfFilter(mode) {
  _sfFilter = mode;
  ['meaningful', 'attempts', 'slow', 'all'].forEach(k => {
    const b = document.getElementById('sf_flt_' + k);
    if (b) b.className = 'flt-btn' + (k === mode ? ' active' : '');
  });
  if (_lastSfData) renderShockForensics(_lastSfData);
}

function sfPillClass(v) {
  if (v === 'FILLED' || v === 'SHIELD_SAVED') return 'pill-ok';
  if (v === 'TOO_SLOW_FLIGHT' || v === 'TOO_SLOW_PRE_EVAL' || v === 'TOO_SLOW_FEED_LAG') return 'pill-bad';
  if (v === 'LEFT_BEHIND_MAKER' || v === 'CLOB_REJECT') return 'pill-warn';
  if (v === 'ALREADY_PRICED_IN' || v === 'MAKER_TTL_QUIET') return 'pill-info';
  return 'pill-muted';
}

function fmtPxDrift(r) {
  const parts = [];
  if (r.t0_ask !== null && r.t0_ask !== undefined) parts.push(`t0 $${Number(r.t0_ask).toFixed(2)}`);
  if (r.eval_ask !== null && r.eval_ask !== undefined) parts.push(`ev $${Number(r.eval_ask).toFixed(2)}`);
  else if (r.target_px !== null && r.target_px !== undefined) parts.push(`lim $${Number(r.target_px).toFixed(3).replace(/0$/, '')}`);
  if (r.fill_px !== null && r.fill_px !== undefined) parts.push(`<b class="pos">fill $${Number(r.fill_px).toFixed(3).replace(/0$/, '')}</b>`);
  else if (r.post_ask !== null && r.post_ask !== undefined) parts.push(`post $${Number(r.post_ask).toFixed(2)}`);
  let sub = '';
  if (r.ask_drift_flight_c !== null && r.ask_drift_flight_c !== undefined && Math.abs(Number(r.ask_drift_flight_c)) >= 0.5) {
    const d = Number(r.ask_drift_flight_c);
    sub = ` <span class="${d > 0 ? 'neg' : 'pos'}">(${d > 0 ? '+' : ''}${d.toFixed(1)}c)</span>`;
  }
  return (parts.length ? parts.join(' &rarr; ') : '<span class="sub">-</span>') + sub;
}

function fmtStageLat(r) {
  const b = [];
  if (r.ipc_ms !== null && r.ipc_ms !== undefined) b.push(`IPC:${Number(r.ipc_ms).toFixed(1)}`);
  if (r.sign_ms !== null && r.sign_ms !== undefined) b.push(`Sg:${Number(r.sign_ms).toFixed(2)}`);
  if (r.http_ms !== null && r.http_ms !== undefined) b.push(`<b>HTTP:${Number(r.http_ms).toFixed(0)}</b>`);
  if (r.ttl_ms !== null && r.ttl_ms !== undefined) b.push(`TTL:${(Number(r.ttl_ms)/1000).toFixed(0)}s`);
  return b.length ? b.join(' &bull; ') : '<span class="sub">-</span>';
}

function renderShockForensics(sf) {
  _lastSfData = sf || {};
  const s = _lastSfData.summary || {};
  const allRows = _lastSfData.rows || [];
  const sumEl = document.getElementById('sf_summary');
  if (sumEl) {
    const medIpc = s.med_ipc_ms !== null && s.med_ipc_ms !== undefined ? `${s.med_ipc_ms}ms` : '-';
    const medHtp = s.med_http_ms !== null && s.med_http_ms !== undefined ? `${s.med_http_ms}ms` : '-';
    sumEl.innerHTML =
      `<span class="sf-chip">Attempts: <b>${s.attempts ?? 0}</b> (<span class="pos">${s.filled ?? 0} Filled</span>, ${s.maker_quiet ?? 0} Maker TTL)</span>` +
      `<span class="sf-chip">Shield Saves: <b class="pos">${s.shield_saves ?? 0}</b> &bull; Speed Misses: <b>${s.speed_misses ?? 0}</b></span>` +
      `<span class="sf-chip">Median Hot Path: IPC <b>${medIpc}</b> &bull; HTTP <b>${medHtp}</b></span>`;
  }
  const rows = allRows.filter(r => {
    if (_sfFilter === 'attempts') return Boolean(r.is_order_attempt);
    if (_sfFilter === 'slow') return Boolean(r.is_speed_miss);
    if (_sfFilter === 'meaningful') return r.meaningful !== false && !['1H_TTE_WINDOW', '15M_TTE_WINDOW', 'TTE_OUT_OF_RANGE', 'CUSHION_TOO_SMALL'].includes(r.gate_code);
    return true;
  });
  const tb = document.getElementById('sf_rows');
  if (!tb) return;
  if (!rows.length) {
    tb.innerHTML = `<tr><td colspan="7" class="sub">No events match filter "${esc(_sfFilter)}".</td></tr>`;
    return;
  }
  tb.innerHTML = rows.slice(0, 24).map(r => {
    const ts = r.ts_et || fmtOttawa(r.unix_ts || r.ts_utc, 'md_hms');
    const mkt = `${r.asset || '?'} ${r.horizon || ''} ${r.side || ''}`.trim();
    const pLbl = String(r.path_type || 'PRE_EVAL').replace('MAKER_P3A', 'P3A MAKER').replace('TAKER_FOK', 'TAKER FOK').replace('MAKER_BOX', 'BOX MAKER');
    return `<tr>
      <td style="white-space:nowrap;">${esc(ts)}</td>
      <td><b>${esc(mkt)}</b></td>
      <td><code>${esc(pLbl)}</code></td>
      <td><span class="pill ${sfPillClass(r.speed_verdict)}">${esc(r.badge || r.speed_verdict)}</span></td>
      <td style="white-space:nowrap;">${fmtPxDrift(r)}</td>
      <td style="white-space:nowrap;font-size:11px;">${fmtStageLat(r)}</td>
      <td>${esc((r.diagnosis || '').slice(0, 95))}</td>
    </tr>`;
  }).join('');
}

async function refreshNow(force=false) {
  if (_inFlight && !force) return;
  _inFlight = true;
  const btn = document.getElementById('refresh_btn');
  if (force && btn) { btn.textContent = 'Refreshing...'; btn.disabled = true; }
  try {
    const r = await fetch('/api/snapshot?t=' + Date.now() + (force ? '&force=1' : ''));
    const d = await r.json();
    const dot = document.getElementById('live_dot');
    if (d.error) {
      dot.style.background = '#f85149';
      document.getElementById('meta').textContent = 'SSH Error: ' + d.error;
      return;
    }
    dot.style.background = '#3fb950';
    _lastSnapshot = d;
    const pm = d.polymarket_live || {};
    const mem = d.mem_mb || {};
    const la = d.load_avg || [0,0,0];
    const ap = d.apex_testnet || {};
    const a124 = d.alpha124 || {};
    const ds = d.directional_shadow || {};
    const rad = d.riskless_radar || {};
    const radSum = rad.summary || {};
    const paa = d.paa_autonomy || {};
    const vf = paa.verified_financial_performance || {};
    const scfg = d.strategy_config || {};
    const dcfg = scfg.directional || {};
    const rcfg = scfg.risk_controller || {};
    const cfgVer = scfg.schema_version || '5.4.1';
    const risklessOnly = dcfg.riskless_only_mode !== false;

    const modeBadge = document.getElementById('hdr_mode_badge');
    if (modeBadge) {
      modeBadge.textContent = risklessOnly ? '100% PURE RISKLESS LOCK • v6.3' : `HYBRID MODE v${cfgVer}`;
    }

    const syncEt = d.fetched_at_et || fmtOttawa(d.unix_ts || d.fetched_at_utc, 'full');
    _pollSeq += 1;
    _lastSyncClientMs = Date.now();
    _lastMetaPrefix = `Synced: ${syncEt} (Ottawa) | Load: ${la[0]} (${la[1]}, ${la[2]}) | RAM Free: ${mem.available || '?'} / ${mem.total || '?'} MB`;
    document.getElementById('meta').textContent = `${_lastMetaPrefix} | Live Poll #${_pollSeq} (0s ago)`;

    _lastPaaData = paa;
    renderNavTriadAndFullThrottle(d);
    renderStageBAttribution(d.stage_b_attribution || {});
    renderPaaAutonomy(paa, 0);
    renderRisklessRadar(rad);
    renderV6Expansion(d.v6_expansion || {});
    renderLiveBook(pm, dcfg, cfgVer, 0);
    renderPmTables(pm);

    const pmHdr = document.getElementById('pm_harvester_hdr');
    if (pmHdr) pmHdr.textContent = `Polymarket Riskless Harvester — Wallet-Reconciled W/L`;

    const spots = Object.assign({}, a124.spots || {}, d.shm_spots || {});
    const shmAnc = d.shm_anchored || {};
    document.getElementById('spots').innerHTML = ['BTC', 'ETH', 'SOL', 'XRP', 'HYPE', 'XAU', 'XAG'].filter(k => spots[k] !== undefined && Number(spots[k]) > 0).map(k => {
      const ancTag = shmAnc[k] ? ' <span class="pos" title="Chainlink Basis Anchored">CL</span>' : '';
      return `<span class="spot-chip"><b>${esc(k)}</b> $${spots[k]}${ancTag}</span>`;
    }).join('');

    // 6 Institutional Riskless-First KPI Cards (Penny-Exact Wallet-to-PnL Reconciliation)
    const cash = Number(pm.bankroll_usd ?? 0);
    const openBook = Number(pm.open_book_usd ?? 0);
    const totalEq = Number(pm.equity_usd ?? (cash + openBook));
    const frozenDisp = Number(pm.frozen_disputed_open_usd ?? Number((pm.nav_triad || {}).disputed_uma_cost_usd || 0));
    const activeOpen = Number(pm.active_undisputed_open_usd ?? Math.max(0, openBook - frozenDisp));
    const reconEq = Number(pm.reconciled_undisputed_equity_usd ?? (cash + activeOpen));
    const lockStartEq = Number(pm.riskless_lock_start_usd || 60.92);
    const netDepUsd = Number(pm.net_deposits_post_lock_usd || 0);
    const basisEq = Number(pm.contributed_capital_basis_usd ?? (lockStartEq + netDepUsd));
    const postLockDelta = Number(pm.post_lock_cash_delta_usd ?? (totalEq - basisEq));
    const postLockPct = Number(pm.post_lock_cash_pct ?? (100.0 * postLockDelta / Math.max(0.01, basisEq)));
    const d24Usd = pm.equity_24h_delta_usd !== undefined && pm.equity_24h_delta_usd !== null ? Number(pm.equity_24h_delta_usd) : null;
    const d24Pct = pm.equity_24h_pct !== undefined && pm.equity_24h_pct !== null ? Number(pm.equity_24h_pct) : null;
    const eq24Ago = pm.equity_24h_ago_usd !== undefined && pm.equity_24h_ago_usd !== null ? Number(pm.equity_24h_ago_usd) : (d24Usd !== null ? (reconEq - d24Usd) : reconEq);
    const badgeTitle = netDepUsd > 0
      ? `Out-of-pocket principal: $${lockStartEq.toFixed(2)} lock start + $${netDepUsd.toFixed(2)} manual deposit = $${basisEq.toFixed(2)} basis -> ${postLockDelta >= 0 ? '+' : ''}$${postLockDelta.toFixed(2)} pure trading gain`
      : `Exact wallet gain since $${lockStartEq.toFixed(2)} Pure Riskless Lock`;
    const badgeLbl = netDepUsd > 0 ? `$${basisEq.toFixed(2)} basis` : `$${lockStartEq.toFixed(2)}`;
    const lockBadge = `<span class="pill ${postLockDelta >= 0 ? 'pill-ok' : 'pill-warn'}" style="font-size:11px;vertical-align:middle;margin-left:4px;" title="${badgeTitle}">${badgeLbl} &rarr; ${postLockDelta >= 0 ? '+' : ''}$${postLockDelta.toFixed(2)} (${postLockPct >= 0 ? '+' : ''}${postLockPct.toFixed(1)}%)</span>`;
    const d24Badge = d24Usd !== null
      ? `<span class="pill ${d24Usd >= 0 ? 'pill-ok' : 'pill-warn'}" style="font-size:11px;vertical-align:middle;margin-left:4px;" title="24h reconciled undisputed NAV change ($${eq24Ago.toFixed(2)} -> $${reconEq.toFixed(2)})">24h: ${d24Usd >= 0 ? '+' : ''}$${d24Usd.toFixed(2)}${d24Pct !== null ? ` (${d24Pct >= 0 ? '+' : ''}${d24Pct.toFixed(1)}%)` : ''}</span>`
      : '';
    const bookBadge = frozenDisp > 0.005
      ? `<span class="pill pill-info" style="font-size:11px;vertical-align:middle;margin-left:4px;" title="$${basisEq.toFixed(2)} basis -> ${postLockDelta >= 0 ? '+' : ''}$${postLockDelta.toFixed(2)} (${postLockPct >= 0 ? '+' : ''}${postLockPct.toFixed(1)}%) book gain if $${frozenDisp.toFixed(2)} disputed KMIA recovers cost; $${reconEq.toFixed(2)} worst-case floor if KMIA = $0">Book w/ KMIA: $${totalEq.toFixed(2)}</span>`
      : lockBadge;
    const quoteCash = Number(pm.quoting_cash_usd ?? 0);
    const freeCash = Number(pm.free_cash_usd ?? cash);
    const utilPct = Number(pm.quoting_utilization_pct ?? (cash > 0 ? (100 * quoteCash / cash) : 0));
    const ruinFloor = Number(rcfg.hard_ruin_floor_usd || 62.0);
    const restOrds = pm.resting_orders || [];
    const restEdge = Number(pm.resting_redeem_edge_usd ?? 0);
    const openCnt = (pm.active_positions || []).length;

    const prW = Number(pm.pure_riskless_wins ?? 0);
    const prL = Number(pm.pure_riskless_losses ?? 0);
    const prWr = Number(pm.pure_riskless_wr_pct ?? 100).toFixed(1);
    const prPnl = Number(pm.pure_riskless_pnl_usd ?? 0);
    const plW = Number(pm.post_lock_wins ?? 0);
    const plL = Number(pm.post_lock_losses ?? 0);
    const frozenSub = frozenDisp > 0.005 ? ` &bull; Frozen KMIA Dispute: <b class="warn">$${frozenDisp.toFixed(2)}</b>` : '';

    const zlPnl = Number(a124.zero_loss_t1000_pnl_usd || vf.zero_loss_shadow_t1000_pnl_usd || 0);
    const zlWins = Number(a124.zero_loss_wins_total || vf.zero_loss_shadow_wins || 0);
    const mgSlvs = a124.machine_gun_sleeves || [];
    const mgTxt = mgSlvs.length > 0 ? `<b style="color:var(--purple);">${mgSlvs.length} MG Live</b>` : `MG Auto-Discover Armed`;

    const svcs = d.services || {};
    const svcEntries = Object.entries(svcs);
    const svcOkCnt = svcEntries.filter(([, v]) => v === 'active').length;
    const acctDiff = Number(vf.accounting_discrepancy_usd ?? 0);
    const p50Ms = vf.clob_post_p50_ms !== undefined && vf.clob_post_p50_ms !== null ? `${Number(vf.clob_post_p50_ms).toFixed(0)}ms` : '-';

    document.getElementById('kpis').innerHTML = `
      <div class="card">
        <div class="label">On-Chain Cash &amp; Reconciled NAV</div>
        <div class="val pos">$${reconEq.toFixed(2)} ${d24Badge}${bookBadge}</div>
        <div class="util-bar"><div class="util-fill" style="width:${Math.min(100, utilPct)}%;"></div></div>
        <div class="sub">Cash: <b>$${cash.toFixed(2)}</b> &bull; Active Open: <b>$${activeOpen.toFixed(2)}</b> &bull; Quoting: <b class="pos">$${quoteCash.toFixed(2)}</b> (${utilPct.toFixed(0)}%) &bull; Free: <b>$${freeCash.toFixed(2)}</b>${frozenSub}</div>
      </div>
      <div class="card">
        <div class="label">Pure Riskless Live Record</div>
        <div class="val ${prL === 0 ? 'pos' : 'warn'}">${prW}W / ${prL}L (${prWr}%)</div>
        <div class="sub">Post-Lock Realized: <b class="pos">${postLockDelta >= 0 ? '+' : ''}$${postLockDelta.toFixed(2)}</b> (${plW}W/${plL}L${frozenDisp > 0.005 ? ', ex-KMIA' : ''}) &bull; All-Time Riskless: <b class="pos">${prPnl >= 0 ? '+' : ''}$${prPnl.toFixed(2)}</b> &bull; Losses: <b class="${plL === 0 ? 'pos' : 'neg'}">${plL}</b></div>
      </div>
      <div class="card">
        <div class="label">Working CLOB Orders &amp; Book</div>
        <div class="val cyan">${restOrds.length} Resting &bull; ${openCnt} Filled</div>
        <div class="sub">Locked Redeem Edge: <b class="pos">+$${restEdge.toFixed(2)}</b> (@ $1.00) &bull; Floor: $${ruinFloor.toFixed(0)} &bull; Posts: <b>${pm.live_maker_posts_tail ?? 0}</b></div>
      </div>
      <div class="card">
        <div class="label">Live Riskless Radar (5m Scan)</div>
        <div class="val pos">${(radSum.active_markets_scanned || 0).toLocaleString()} Mkts</div>
        <div class="sub">0%-Fee: <b>${(radSum.fee_free_markets || 0).toLocaleString()}</b> &bull; Peak Carry: <b class="cyan">${Number(radSum.top_bps_per_hr || 0).toFixed(0)} bps/hr</b> &bull; IPC: <b>${(radSum.counts || {}).LIVE_IPC || 0}</b></div>
      </div>
      <div class="card">
        <div class="label">Grad-8 Fleet &amp; 0-Loss Shadow</div>
        <div class="val pos">${a124.promoted_count ?? 0} Live 8/8 &bull; +$${zlPnl.toFixed(0)}</div>
        <div class="sub">Zero-Loss T1000: <b>${zlWins}W/0L</b> &bull; Near-G8: <b>${a124.near_grad8_count ?? 0}</b> &bull; ${mgTxt}</div>
      </div>
      <div class="card">
        <div class="label">RISKLESS PAA OS &amp; Fleet Health</div>
        <div class="val ${!pm.risk_halt && svcOkCnt >= svcEntries.length ? 'pos' : 'warn'}">${svcOkCnt}/${svcEntries.length} Active</div>
        <div class="sub">Acct Diff: <b class="pos">$${acctDiff.toFixed(4)}</b> &bull; CLOB p50: <b>${p50Ms}</b> &bull; Halt: <b class="${pm.risk_halt ? 'neg' : 'pos'}">${pm.risk_halt ? 'HALTED' : 'CLEAR'}</b></div>
      </div>
    `;

    const shmAges = d.shm_fast_tick_age_sec || {};
    const svcPills = svcEntries.map(([k, v]) =>
      `<span class="pill ${v === 'active' ? 'pill-ok' : 'pill-bad'}">${esc(k)}: ${esc(v)}</span>`
    );
    const nowUtc = new Date();
    const uDay = nowUtc.getUTCDay();
    const uHr = nowUtc.getUTCHours();
    const metalsWkndClosed = (uDay === 5 && uHr >= 21) || uDay === 6 || (uDay === 0 && uHr < 22);
    const shmPills = Object.entries(shmAges).map(([sym, age]) => {
      const ok = age !== null && age !== undefined && Number(age) < 10.0;
      if (!ok && (sym === 'XAU' || sym === 'XAG') && metalsWkndClosed) {
        return `<span class="pill pill-muted" title="CME/Pyth metals market closed for weekend (Fri 21:00–Sun 22:00 UTC)">SHM ${esc(sym)}: wknd closed</span>`;
      }
      const lbl = age !== null && age !== undefined ? `${Number(age).toFixed(2)}s` : 'down';
      return `<span class="pill ${ok ? 'pill-ok' : 'pill-bad'}">SHM ${esc(sym)}: ${lbl}</span>`;
    });
    document.getElementById('svcs').innerHTML = svcPills.concat(shmPills).join('');

    document.getElementById('log_events').innerHTML = (d.live_log_events || []).map(l =>
      `<div>${esc(l)}</div>`
    ).join('') || '<div class="sub">No recent log events.</div>';

    renderShockForensics(d.shock_forensics || {});

    const syncEl = document.getElementById('a124_sync');
    if (syncEl) {
      syncEl.textContent = `Age: ${a124.state_age_sec ?? '?'}s | Resting Shadow Quotes: ${(a124.pending_d1_mkr || 0) + (a124.pending_zf_mkr || 0) + (a124.pending_pmo || 0)} | Closed Shadow: ${a124.closed_total ?? 0}`;
    }
    const ocEl = document.getElementById('a124_open_cnt');
    if (ocEl) ocEl.textContent = String(a124.open_total ?? 0);

    renderA124Sleeves(a124.sleeves || []);

    document.getElementById('a124_open').innerHTML = (a124.open_positions || []).map(p => `
      <tr>
        <td><b>${esc(shortSlv(p.sleeve || '').slice(0, 18))}</b></td>
        <td>${esc(p.title || '')}</td>
        <td>$${Number(p.eff_px || 0).toFixed(3)}</td>
        <td>$${Number(p.last_bid || 0).toFixed(3)}</td>
        <td class="warn">${esc(p.tte || '-')}</td>
      </tr>
    `).join('') || '<tr><td colspan="5" class="sub">No open shadow boxes</td></tr>';

    document.getElementById('a124_closed').innerHTML = (a124.recent_closed || []).map(p => `
      <tr>
        <td style="white-space:nowrap;">${esc(p.closed_et || fmtOttawa(p.closed_utc, 'md_hm'))}</td>
        <td><b>${esc(shortSlv(p.sleeve || '').slice(0, 18))}</b></td>
        <td>${esc(p.title || '')}</td>
        <td>$${Number(p.eff_px || 0).toFixed(3)}&rarr;$${Number(p.payout_px || 0).toFixed(2)}</td>
        <td class="${p.won ? 'pos' : 'neg'}"><b>${p.t100_pnl >= 0 ? '+' : ''}$${Number(p.t100_pnl || 0).toFixed(2)}</b> / ${p.t1000_pnl >= 0 ? '+' : ''}$${Number(p.t1000_pnl || 0).toFixed(2)}</td>
      </tr>
    `).join('') || '<tr><td colspan="5" class="sub">No closed shadow boxes recorded yet</td></tr>';
  } catch (e) {
    document.getElementById('meta').textContent = 'Dashboard fetch error: ' + e;
  } finally {
    _inFlight = false;
    if (btn) { btn.textContent = 'Refresh Now'; btn.disabled = false; }
  }
}

updateD1Countdown();
refreshNow();
setInterval(() => { if (!document.hidden) refreshNow(false); }, 6000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshNow(false); });
</script>
</body>
</html>
"""


def _build_compressed_oneshot_py(probe_src: str) -> str:
    b64_src = base64.b64encode(zlib.compress(probe_src.encode("utf-8"), 6)).decode("ascii")
    sha12 = hashlib.sha256(probe_src.encode("utf-8")).hexdigest()[:12]
    return (
        "import base64, gc, io, marshal, os, subprocess, sys, zlib\n"
        "os.environ['PM_ENABLE_TLS_KEEPALIVE'] = '0'\n"
        "os.environ['PM_ENABLE_USER_WS'] = '0'\n"
        "os.environ['PM_DISABLE_FAST_V2_SIGNER'] = '1'\n"
        f"_MP = f'/tmp/dominus_cc_probe_{{sys.hexversion:x}}_{sha12}.marsh'\n"
        "if not os.path.exists(_MP):\n"
        f"    _SRC = zlib.decompress(base64.b64decode('{b64_src}')).decode('utf-8')\n"
        "    subprocess.run([sys.executable, '-c', \"import marshal, os, sys; p=sys.argv[1]; b=marshal.dumps(compile(sys.stdin.read(), '<dominus_probe>', 'exec')); open(p+'.tmp','wb').write(b); os.replace(p+'.tmp', p)\", _MP], input=_SRC, text=True, check=True, timeout=8)\n"
        "    del _SRC\n"
        "    gc.collect()\n"
        "    try:\n"
        "        import ctypes; ctypes.CDLL('libc.so.6').malloc_trim(0)\n"
        "    except Exception:\n"
        "        pass\n"
        "_CODE = marshal.loads(open(_MP, 'rb').read())\n"
        "_buf = io.StringIO()\n"
        "_real_out = sys.stdout\n"
        "sys.stdout = _buf\n"
        "try:\n"
        "    exec(_CODE, {'__name__': '__main__', '_PERSIST': {}})\n"
        "finally:\n"
        "    sys.stdout = _real_out\n"
        "_lines = [ln.strip() for ln in _buf.getvalue().splitlines() if ln.strip().startswith('{')]\n"
        "if _lines:\n"
        "    _gz = base64.b64encode(zlib.compress(_lines[-1].encode('utf-8'), 6)).decode('ascii')\n"
        "    _real_out.write('GZ:' + _gz + '\\n')\n"
        "    _real_out.flush()\n"
    )


def _build_persistent_daemon_py(probe_src: str) -> str:
    b64_src = base64.b64encode(zlib.compress(probe_src.encode("utf-8"), 6)).decode("ascii")
    sha12 = hashlib.sha256(probe_src.encode("utf-8")).hexdigest()[:12]
    return (
        "import base64, ctypes, gc, io, json, marshal, os, subprocess, sys, traceback, zlib\n"
        "os.environ['PM_ENABLE_TLS_KEEPALIVE'] = '0'\n"
        "os.environ['PM_ENABLE_USER_WS'] = '0'\n"
        "os.environ['PM_DISABLE_FAST_V2_SIGNER'] = '1'\n"
        f"_MP = f'/tmp/dominus_cc_probe_{{sys.hexversion:x}}_{sha12}.marsh'\n"
        "if not os.path.exists(_MP):\n"
        f"    _SRC = zlib.decompress(base64.b64decode('{b64_src}')).decode('utf-8')\n"
        "    subprocess.run([sys.executable, '-c', \"import marshal, os, sys; p=sys.argv[1]; b=marshal.dumps(compile(sys.stdin.read(), '<dominus_probe>', 'exec')); open(p+'.tmp','wb').write(b); os.replace(p+'.tmp', p)\", _MP], input=_SRC, text=True, check=True, timeout=8)\n"
        "    del _SRC\n"
        "    gc.collect()\n"
        "    try:\n"
        "        import ctypes; ctypes.CDLL('libc.so.6').malloc_trim(0)\n"
        "    except Exception:\n"
        "        pass\n"
        "_CODE = marshal.loads(open(_MP, 'rb').read())\n"
        "_PERSIST = {}\n"
        "_real_in = sys.stdin\n"
        "_real_out = sys.stdout\n"
        "_real_out.write('READY\\n')\n"
        "_real_out.flush()\n"
        "for _cmd in _real_in:\n"
        "    _c = _cmd.strip()\n"
        "    if not _c:\n"
        "        continue\n"
        "    if _c == 'QUIT':\n"
        "        break\n"
        "    _buf = io.StringIO()\n"
        "    sys.stdout = _buf\n"
        "    try:\n"
        "        exec(_CODE, {'__name__': '__main__', '_PERSIST': _PERSIST})\n"
        "        _lines = [ln.strip() for ln in _buf.getvalue().splitlines() if ln.strip().startswith('{')]\n"
        "        _payload = _lines[-1] if _lines else json.dumps({'error': 'Empty probe output'})\n"
        "    except Exception as _exc:\n"
        "        _payload = json.dumps({'error': f'Remote probe exception: {_exc}'})\n"
        "    finally:\n"
        "        sys.stdout = _real_out\n"
        "    _gz = base64.b64encode(zlib.compress(_payload.encode('utf-8'), 6)).decode('ascii')\n"
        "    _real_out.write('GZ:' + _gz + '\\n')\n"
        "    _real_out.flush()\n"
        "    gc.collect()\n"
        "    try:\n"
        "        ctypes.CDLL('libc.so.6').malloc_trim(0)\n"
        "    except Exception:\n"
        "        pass\n"
    )


def _decode_wire_line(line: str) -> Optional[Dict[str, Any]]:
    s = line.strip()
    if s.startswith("GZ:"):
        raw = zlib.decompress(base64.b64decode(s[3:])).decode("utf-8")
        return json.loads(raw)
    if s.startswith("{"):
        return json.loads(s)
    return None


class SnapshotCache:
    def __init__(
        self,
        host: str,
        ttl_sec: float = 5.0,
        start_bg: bool = False,
        idle_pause_sec: float = 45.0,
        idle_disconnect_sec: float = 300.0,
    ) -> None:
        self.host = host
        self.ttl_sec = ttl_sec
        self.idle_pause_sec = idle_pause_sec
        self.idle_disconnect_sec = idle_disconnect_sec
        self._fetch_lock = threading.Lock()
        self._last_ts = 0.0
        self._last_data: Dict[str, Any] = {}
        self._last_viewer_mono = time.monotonic()
        self._wake_event = threading.Event()
        self._stream_proc: Optional[subprocess.Popen[str]] = None
        self._stream_q: "queue.Queue[Optional[str]]" = queue.Queue()
        self._use_persistent = start_bg
        if start_bg:
            t = threading.Thread(target=self._bg_loop, name="DominusSnapshotPoller", daemon=True)
            t.start()

    def touch_viewer(self) -> None:
        self._last_viewer_mono = time.monotonic()
        self._wake_event.set()

    def close_stream(self) -> None:
        p = self._stream_proc
        self._stream_proc = None
        if p is not None:
            try:
                if p.stdin:
                    p.stdin.write("QUIT\n")
                    p.stdin.flush()
                    p.stdin.close()
            except Exception:
                pass
            try:
                p.kill()
            except Exception:
                pass
            try:
                p.wait(timeout=1.5)
            except Exception:
                pass

    def _ensure_persistent_stream(self, timeout: float = 12.0) -> bool:
        if self._stream_proc is not None and self._stream_proc.poll() is None:
            return True
        self.close_stream()
        q: "queue.Queue[Optional[str]]" = queue.Queue()
        self._stream_q = q
        # Zero-quote-escaping remote bootstrap: reads 1 base64-zlib daemon script line on stdin, compiles REMOTE_PROBE_PY once, loops on POLL\n
        proc = subprocess.Popen(
            [
                "ssh",
                "-C",
                "-T",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=6",
                "-o",
                "ServerAliveInterval=20",
                "-o",
                "ServerAliveCountMax=3",
                self.host,
                "/home/skybullet1987/quant_pipeline/venv/bin/python3 -u -c \"import base64,sys,zlib;exec(zlib.decompress(base64.b64decode(sys.stdin.readline())).decode())\"",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self._stream_proc = proc

        def _reader() -> None:
            try:
                assert proc.stdout is not None
                for ln in proc.stdout:
                    q.put(ln.rstrip("\r\n"))
            except Exception:
                pass
            finally:
                q.put(None)

        threading.Thread(target=_reader, name="DominusSshStreamReader", daemon=True).start()
        try:
            assert proc.stdin is not None
            daemon_src = _build_persistent_daemon_py(REMOTE_PROBE_PY)
            b64_daemon = base64.b64encode(zlib.compress(daemon_src.encode("utf-8"), 6)).decode("ascii")
            proc.stdin.write(b64_daemon + "\n")
            proc.stdin.flush()
            ready_ln = q.get(timeout=timeout)
            if ready_ln != "READY":
                self.close_stream()
                return False
            return True
        except Exception:
            self.close_stream()
            return False

    def _probe_via_persistent_stream(self) -> Optional[Dict[str, Any]]:
        try:
            if not self._ensure_persistent_stream(timeout=10.0):
                return None
            assert self._stream_proc is not None and self._stream_proc.stdin is not None
            while not self._stream_q.empty():
                try:
                    self._stream_q.get_nowait()
                except queue.Empty:
                    break
            self._stream_proc.stdin.write("POLL\n")
            self._stream_proc.stdin.flush()
            line = self._stream_q.get(timeout=14.0)
            if not line:
                self.close_stream()
                return None
            data = _decode_wire_line(line)
            if data is not None:
                self._last_data = data
                self._last_ts = time.time()
            return data
        except Exception:
            self.close_stream()
            return None

    def _probe_once(self) -> Dict[str, Any]:
        if self._use_persistent:
            stream_res = self._probe_via_persistent_stream()
            if stream_res is not None:
                return stream_res
        try:
            proc = subprocess.run(
                [
                    "ssh",
                    "-C",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=6",
                    self.host,
                    "/home/skybullet1987/quant_pipeline/venv/bin/python3 -",
                ],
                input=_build_compressed_oneshot_py(REMOTE_PROBE_PY),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=14,
            )
            if proc.returncode != 0:
                return {"error": (proc.stderr or proc.stdout).strip()[:400]}
            for ln in reversed(proc.stdout.splitlines()):
                decoded = _decode_wire_line(ln)
                if decoded is not None:
                    self._last_data = decoded
                    self._last_ts = time.time()
                    return decoded
            return {"error": f"Unexpected SSH output: {proc.stdout[:200]}"}
        except Exception as exc:
            return {"error": str(exc)}

    def _bg_loop(self) -> None:
        while True:
            idle_sec = time.monotonic() - self._last_viewer_mono
            if idle_sec > self.idle_pause_sec:
                if idle_sec > self.idle_disconnect_sec and self._stream_proc is not None:
                    with self._fetch_lock:
                        self.close_stream()
                self._wake_event.wait(timeout=5.0)
                self._wake_event.clear()
                continue
            with self._fetch_lock:
                self._probe_once()
            self._wake_event.wait(timeout=self.ttl_sec)
            self._wake_event.clear()

    def get(self, force: bool = False) -> Dict[str, Any]:
        self.touch_viewer()
        if not force and self._last_data and (time.time() - self._last_ts) < max(self.ttl_sec * 2.5, 12.0):
            return self._last_data
        acquired = self._fetch_lock.acquire(timeout=0.15 if (not force and self._last_data) else 14.0)
        if not acquired:
            return self._last_data or {"error": "SSH refresh in progress"}
        try:
            if not force and self._last_data and (time.time() - self._last_ts) < self.ttl_sec:
                return self._last_data
            res = self._probe_once()
            if res.get("error") and self._last_data and not force:
                return self._last_data
            return res
        finally:
            self._fetch_lock.release()


def format_cli_summary(d: Dict[str, Any]) -> str:
    if d.get("error"):
        return f"[ERROR] Could not fetch telemetry: {d['error']}"
    out_lines = []
    _p = out_lines.append
    pm = d.get("polymarket_live") or {}
    nt = pm.get("nav_triad") or {}
    hf = pm.get("harvester_funnel") or {}
    mem = d.get("mem_mb") or {}
    la = d.get("load_avg") or [0, 0, 0]
    rad = d.get("riskless_radar") or {}
    rad_s = rad.get("summary") or {}
    a124 = d.get("alpha124") or {}
    v52 = a124.get("v52_catalog") or {}
    ft = d.get("full_throttle") or {}
    fts = ft.get("systemd") or d.get("full_throttle_systemd") or {}
    uc = ft.get("universe_census") or {}
    om = ft.get("opportunity_metrics") or {}
    hb = ft.get("harvester_bridge") or {}
    fl = ft.get("family_l_maker_shadow") or {}
    proj = d.get("daily_projections") or {}
    comp_rows = (d.get("strategy_comparison_matrix") or {}).get("rows") or []

    _p("=" * 96)
    _p(f" DOMINUS RISKLESS PAA COMMAND CENTER v6.3 (FULL-THROTTLE)  |  {d.get('fetched_at_et') or d.get('fetched_at_utc')}")
    _p("=" * 96)
    _rss_s = f"  |  ProbeRSS={d['probe_rss_mib']:.2f} MiB (<20 MiB)" if d.get("probe_rss_mib") is not None else ""
    _p(
        f" Host Load (2 vCPU) : {la[0]} ({la[1]}, {la[2]})  |  "
        f"RAM Available: {mem.get('available')} / {mem.get('total')} MB (SwapTotal={mem.get('swap_total', 0)} MB){_rss_s}  |  "
        f"Halt={pm.get('risk_halt')}"
    )

    # 1. Explicit 3-NAV Triad, KMIA (D-001) Non-Interference & Finland VM Breakeven Hurdle
    _floor_nav = float(nt.get("reconciled_floor_nav_usd") or pm.get("guaranteed_redemption_equity_usd") or pm.get("bankroll_usd") or 0.0)
    _mtm_nav = float(nt.get("mtm_liquidation_nav_usd") or pm.get("mtm_bid_equity_usd") or _floor_nav)
    _book_nav = float(nt.get("persisted_book_equity_usd") or pm.get("equity_usd") or _floor_nav)
    _kmia_cnt = int(nt.get("kmia_disputed_count", 0) or 0)
    _kmia_cost = float(nt.get("kmia_frozen_cost_usd") or nt.get("disputed_uma_cost_usd") or 0.0)
    _kmia_bid = float(nt.get("kmia_mtm_bid_usd") or 0.0)
    _kmia_ok = bool(nt.get("kmia_untouched_ok", True))
    _vm_hurdle = float(nt.get("vm_breakeven_bps_per_hr") or 7.04)
    _vm_daily = float(nt.get("vm_daily_cost_usd") or 0.8223)
    _q_bps = float(nt.get("live_quoting_bps_per_hr") or 0.0)
    _p(
        f" 3-NAV Triad (Auth) : [1] Guaranteed Floor NAV=${_floor_nav:.2f} (Sizing Basis; KMIA=$0.00)  |  "
        f"[2] Mark-to-Bid NAV=${_mtm_nav:.2f} (KMIA Bid=${_kmia_bid:.2f})  |  "
        f"[3] Persisted Book Equity=${_book_nav:.2f} (Incl. ${_kmia_cost:.2f} Frozen KMIA — NON-SIZING)"
    )
    _p(
        f" D-001 KMIA & Hurdle: KMIA Disputed={_kmia_cnt}/4 Untouched={_kmia_ok} (Exit/Unwind Orders={nt.get('kmia_exit_or_unwind_orders', 0)})  |  "
        f"VM Hurdle={_vm_hurdle:.2f} bps/hr (${_vm_daily:.3f}/d = $24.67/mo) vs Live Quoting={_q_bps:.2f} bps/hr"
    )
    _p(
        f" CLOB Maker Quoting : Quoting ${pm.get('quoting_cash_usd', 0):.2f} [{pm.get('quoting_utilization_pct', 0):.1f}%] across {len(pm.get('resting_orders') or [])} CLOB orders "
        f"| Free ${pm.get('free_cash_usd', 0):.2f} | Locked Redeem Edge +${pm.get('resting_redeem_edge_usd', 0):.2f}"
    )
    _flat_s = f", +{pm.get('pure_riskless_flat_merges', 0)} flat merges" if pm.get("pure_riskless_flat_merges") else ""
    _p(
        f" Pure Riskless Live : {pm.get('pure_riskless_wins', 0)}W / {pm.get('pure_riskless_losses', 0)}L{_flat_s} "
        f"({pm.get('pure_riskless_wr_pct', 100.0):.1f}% WR | {pm.get('pure_riskless_pnl_usd', 0):+.2f} USD Wallet Cash)  |  "
        f"Post-Lock Losses: {pm.get('post_lock_losses', 0)}  |  "
        f"All-Time Epoch (incl. paused legacy): {pm.get('epoch_wins', 0)}W/{pm.get('epoch_losses', 0)}L ({pm.get('epoch_net_pnl_usd', 0):+.2f} USD)"
    )
    for ro in (pm.get("resting_orders") or [])[:6]:
        _p(
            f"   [LIVE CLOB ORDER] {ro.get('side')} ({ro.get('outcome')}) x {ro.get('shares'):.2f} @ ${ro.get('price'):.4f} "
            f"(${ro.get('notional_usd'):.2f} -> +${ro.get('redeem_edge_usd', 0):.2f} edge, ~{ro.get('est_bps_per_hr', 0):.0f} bps/hr) | {str(ro.get('title'))[:62]}"
        )

    # 2. Full-Throttle Systemd Units, 100% Universe Census & Alpha-124 v5.2 Catalog
    _p("-" * 96)
    _mp_s = f"{fts['memory_peak_mib']:.1f} MiB" if fts.get("memory_peak_mib") is not None else f"{float((ft.get('campaign_summary') or {}).get('peak_rss_mib', 0.0) or 0.0):.1f} MiB"
    _mm_s = f"{float(fts.get('memory_max_mib') or 220.0):.0f}MiB"
    _nxt_s_fmt = f"{float(fts['next_trigger_in_sec']):.0f}s" if fts.get("next_trigger_in_sec") is not None else "-"
    _p(
        f" Full-Throttle Unit : polymarket-full-throttle-sweep.service Result={fts.get('result', 'unknown')} "
        f"ExecMainStatus={fts.get('exec_main_status')} MemoryPeak={_mp_s}/{_mm_s} LastExit={fts.get('last_exit_et') or '-'}  |  "
        f".timer Active={fts.get('timer_active_state', 'unknown')} NextIn={_nxt_s_fmt}"
    )
    _p(
        f" Universe Census    : Events={uc.get('total_observable_events', 0):,} | TotalMkts={uc.get('total_observable_markets', 0):,} | "
        f"Active={uc.get('active_unclosed_markets', 0):,} | Tokens={uc.get('total_tradable_outcome_tokens', 0):,} | "
        f"NegRisk={uc.get('negrisk_events', 0):,}(+Aug {uc.get('augmented_negrisk_events', 0)}) | Edges={uc.get('graph_total_edges', 0):,}"
    )
    _p(
        f" Alpha-124 v5.2 Cat : Cycle=#{v52.get('cycle_count', 0)} | Binaries={v52.get('binaries_monitored', 0):,} | "
        f"UMA_Proposed={v52.get('uma_proposed_count', 0)}(Hot={v52.get('uma_hot_bonds_count', 0)}) | NegRisk_Slates={v52.get('negrisk_slates_count', 0)} | "
        f"CAL1={v52.get('cal1_ladders_count', 0)} | WS_Tokens={v52.get('ws_subscribed_tokens', 0)}(Shards={v52.get('ws_shards_active', 0)},Pin={v52.get('dormant_ws_pinned_tokens', 0)}) | "
        f"MakerPend={v52.get('maker_pending_shadow', 0)} | BridgeEmit={v52.get('bridge_emitted_total', 0)}"
    )

    # 3. 14-Family (A..N) Matrix + HarvesterBridge + Family L Maker Shadow
    if ft.get("family_matrix"):
        _p("-" * 96)
        _p(
            f" 14-Family Matrix   : Evaluated={om.get('total_candidates_evaluated', 0):,} | Proven={om.get('mathematically_valid_proofs', 0)} | "
            f"RuleTrapsBlocked(CLASS_D)={om.get('rule_mismatch_rejections_prevented', 0):,} | "
            f"Dormant(<=50bps)={om.get('dormant_within_50_bps_count', 0)} / {om.get('dormant_active_count', 0)}"
        )
        for fm in ft.get("family_matrix") or []:
            _p(
                f"   [Fam {fm['family_code']}] {fm['family_name'][:36]:36s} | Inspected={fm['inspected']:7,d} | "
                f"CLASS_A/B={fm['class_a_b']:3d} | CLASS_C={fm['class_c']:3d} | RuleTraps(D)={fm['rule_traps_blocked']:5d} | "
                f"Dormant={fm.get('dormant_store_count') or fm.get('dormant_near_misses', 0):4d}"
            )
    _p(
        f" FT_* Bridge & MkrL : Bridge(Enabled={hb.get('enabled')}, Emitted={hb.get('total_emitted_across_campaign', 0)}, Skips={json.dumps(hb.get('skipped_by_reason') or {})})  |  "
        f"HarvesterFunnel(AllRecv={hf.get('candidates_received_total', 0)}, FT_Recv={hf.get('ft_received', 0)}, TkrExec={hf.get('taker_executed', 0)}, MkrPost={hf.get('maker_posted', 0)}, MkrFill={hf.get('maker_filled', 0)}, Rej={hf.get('ft_rejected', 0)}, FIFO#1={hf.get('fifo_rank1_slots', 0)})"
    )
    _p(
        f" Family L Maker Sim : Resting={fl.get('resting_passive_quotes_count', 0)} | HedgedFills={fl.get('filled_hedged_locks_count', 0)} "
        f"(Adv={fl.get('adverse_selected_fills_count', 0)}) | ExRebateShadowPnL=+{fl.get('net_post_adverse_shadow_pnl_ex_rebate_usd', 0.0):.2f} USD "
        f"(+RebateEst=${fl.get('estimated_maker_rebate_15_to_25pct_usd', 0.0):.3f} — STRICTLY NON-CASH SHADOW)"
    )

    # 4. Principle-8 Strictly Non-Conflated Strategy Performance Matrix (Real Trading vs Realistic Shadow)
    if comp_rows:
        _p("-" * 96)
        _p(" REAL TRADING (WALLET pUSD) vs REALISTIC SHADOW (NON-CASH SIMULATED) — STRICTLY NON-CONFLATED:")
        for r in comp_rows:
            rl = r.get("real_trading") or {}
            sh = r.get("realistic_shadow") or {}
            _p(
                f"   {r['strategy_key']:20s} | REAL[{rl.get('gate', ''):17s} Open={rl.get('open_positions', 0)} CLOB={rl.get('resting_clob_orders', 0)} "
                f"R/E/X={rl.get('candidates_received', 0)}/{rl.get('executed', 0)}/{rl.get('rejected', 0)} "
                f"{rl.get('wins', 0)}W/{rl.get('losses', 0)}L {float(rl.get('realized_wallet_pnl_usd', 0.0)):+6.2f} USD]  ||  "
                f"SHADOW[Insp={sh.get('inspected', 0):6,d} A/B={sh.get('proven_class_a_b', 0):2d} Open={sh.get('shadow_open_or_resting', 0):2d} "
                f"{sh.get('shadow_wins', 0)}W/{sh.get('shadow_losses', 0)}L {float(sh.get('shadow_net_pnl_usd', 0.0)):+7.2f} USD sim]"
            )

    # 5. Empirical P25 / P50 / P75 Daily Projections & Milestone ETAs ($150 / $253 / $500 / $5,000)
    if proj.get("available"):
        _ms = proj.get("milestones") or {}
        _hz = proj.get("horizons") or {}
        _p("-" * 96)
        _d30 = _hz.get("day_30") or {}
        _d90 = _hz.get("day_90") or {}
        _n30_s = f" (NetPostVM={_d30['p50_net_after_vm_usd']:+.2f})" if _d30.get("p50_net_after_vm_usd") is not None else ""
        _n90_s = f" (NetPostVM={_d90['p50_net_after_vm_usd']:+.2f})" if _d90.get("p50_net_after_vm_usd") is not None else ""
        _p(
            f" Daily Projections  : Model={proj.get('model_version')} (SIMULATED/PROJECTED — NOT WALLET CASH) | "
            f"30d[P25=${_d30.get('p25_equity', 0):.2f} / P50=${_d30.get('p50_equity', 0):.2f}{_n30_s} / P75=${_d30.get('p75_equity', 0):.2f}] | "
            f"90d[P25=${_d90.get('p25_equity', 0):.2f} / P50=${_d90.get('p50_equity', 0):.2f}{_n90_s} / P75=${_d90.get('p75_equity', 0):.2f}]"
        )
        _fmt_eta = lambda v: f"{int(v)}d" if v is not None else ">365d"
        _p(
            f" Milestone ETAs     : "
            f"$150(P50={_fmt_eta((_ms.get('usd_150') or {}).get('p50_day'))}, P75={_fmt_eta((_ms.get('usd_150') or {}).get('p75_day'))}, P25={_fmt_eta((_ms.get('usd_150') or {}).get('p25_day'))}) | "
            f"$253(P50={_fmt_eta((_ms.get('usd_253') or {}).get('p50_day'))}, P75={_fmt_eta((_ms.get('usd_253') or {}).get('p75_day'))}, P25={_fmt_eta((_ms.get('usd_253') or {}).get('p25_day'))}) | "
            f"$500(P50={_fmt_eta((_ms.get('usd_500') or {}).get('p50_day'))}, P75={_fmt_eta((_ms.get('usd_500') or {}).get('p75_day'))}, P25={_fmt_eta((_ms.get('usd_500') or {}).get('p25_day'))}) | "
            f"$5,000(P50={_fmt_eta((_ms.get('usd_5000') or {}).get('p50_day'))}, P75={_fmt_eta((_ms.get('usd_5000') or {}).get('p75_day'))}, P25={_fmt_eta((_ms.get('usd_5000') or {}).get('p25_day'))})"
        )

    _p("-" * 96)
    _p(
        f" Riskless Opportunity Radar ({rad_s.get('active_markets_scanned', 0):,} Active Mkts | "
        f"{rad_s.get('fee_free_markets', 0):,} 0%-Fee | Peak {rad_s.get('top_bps_per_hr', 0):.0f} bps/hr):"
    )
    for op in (rad.get("opportunities") or [])[:5]:
        _p(
            f"   [{op.get('bucket', ''):13s}] ${op.get('entry_px', 0):.3f} (+{op.get('edge_bps', 0):4.0f} bps | {op.get('bps_per_hr', 0):5.0f} bps/hr) | "
            f"{str(op.get('title', ''))[:58]}"
        )
    _p("-" * 96)
    _p(
        f" Alpha-124 & _grad8 : {a124.get('promoted_count', 0)} Live 8/8 | "
        f"Zero-Loss T1000 Shadow: +{a124.get('zero_loss_t1000_pnl_usd', 0):.2f} USD ({a124.get('zero_loss_wins_total', 0)}W/0L) | "
        f"Near-Grad8: {a124.get('near_grad8_count', 0)} | Machine-Gun: {len(a124.get('machine_gun_sleeves') or [])} sleeves"
    )
    for s in (a124.get("sleeves") or [])[:8]:
        _p(
            f"   {s['sleeve']:42s} | Open={s['open']} | {s['wins']:2d}W/{s['losses']:2d}L | "
            f"{s['grad8_progress']:16s} | T1000={s['t1000_pnl_usd']:+7.2f} USD"
        )
    paa = d.get("paa_autonomy") or {}
    if paa:
        dh = paa.get("director_heartbeat") or {}
        mh = (paa.get("monitoring_health") or {}).get("paa_monitor") or {}
        tc = paa.get("task_counts_by_state") or {}
        br = paa.get("budget_and_resources") or {}
        zt = paa.get("zero_trust") or {}
        lad = paa.get("research_ladder") or {}
        tm_short = ", ".join(
            f"{t['unit']}={t['next_in_sec']}s" if t.get("next_in_sec") is not None else f"{t['unit']}=-"
            for t in sorted(paa.get("systemd_timers") or [], key=lambda x: x.get("next_in_sec") if x.get("next_in_sec") is not None else 999999)[:5]
        )
        rl = paa.get("riskless_kpis") or {}
        _dh_age_s = f"{dh['age_sec']}s" if dh.get("age_sec") is not None else "-"
        _mh_age_s = f"{mh['age_sec']}s" if mh.get("age_sec") is not None else "-"
        _p("-" * 96)
        _p(
            f" RISKLESS PAA OS    : Lock={rl.get('riskless_only_mode', True)} (Pure Live {rl.get('pure_riskless_live_wins', 0)}W/{rl.get('pure_riskless_live_losses', 0)}L "
            f"{float(rl.get('pure_riskless_realized_pnl_usd', 0.0) or 0.0):+.2f} USD) | "
            f"Director={dh.get('status', 'INIT')} (Cycle #{dh.get('cycle_count', 0)}, age={_dh_age_s}) | "
            f"Monitor={mh.get('status', 'INIT')} (age={_mh_age_s}) | "
            f"AI=${br.get('daily_ai_cost_usd', 0.0):.4f}/{br.get('max_daily_ai_cost_usd', 2.50):.2f}"
        )
        _p(
            f" Zero-Trust State   : Policies={paa.get('tier_a_intact_count', 0)}/5 | "
            f"Facts(Fresh={zt.get('verified_facts_fresh', 0)}, Stale={zt.get('verified_facts_stale', 0)}, Contra={zt.get('verified_facts_contradicted', 0)}) | "
            f"Sessions={zt.get('sessions_total', 0)} ({zt.get('fresh_session_pct', 100.0)}% fresh, peak_ctx={zt.get('max_context_pct', 0.0)}%/60%) | "
            f"Tasks={json.dumps(tc)}"
        )
        _p(f" Schedules & TierC  : Next=[{tm_short}] | Ladder={json.dumps(lad)}")
    sb = d.get("stage_b_attribution") or {}
    if sb and not sb.get("error"):
        nsk = sb.get("north_star_kpis") or {}
        fn_s = (sb.get("opportunity_funnel") or {}).get("stages") or {}
        db_s = (sb.get("opportunity_funnel") or {}).get("decay_buckets") or {}
        dc_s = db_s.get("counts") or {}
        _p("-" * 96)
        _p(
            f" STAGE B 10 KPIs    : [1] NetEcon={nsk.get('kpi_1_net_economic_pnl_usd', 0):+.2f} USD "
            f"(Wallet {nsk.get('kpi_1_wallet_gain_before_ops_usd', 0):+.2f} - Ops ${nsk.get('kpi_1_prorated_ops_cost_usd', 0):.2f}) | "
            f"[2] Net/$1k=+{nsk.get('kpi_2_net_pnl_per_1000_usd', 0):.2f} USD | "
            f"[3] CapHr=+{nsk.get('kpi_3_bps_per_capital_hour', 0):.1f} bps/hr ({nsk.get('kpi_3_occupied_capital_hours', 0):.1f} $h)"
        )
        _p(
            f" Funnel & [9] Decay : Seen={fn_s.get('GROSS_ARB_SEEN', 0)} -> L2={fn_s.get('EXECUTABLE_NET_L2', 0)} -> "
            f"Sub={fn_s.get('ORDER_SUBMITTED', 0)} -> Locked={fn_s.get('COMPLETE_BASKET_LOCKED', 0)} "
            f"(Unw={fn_s.get('PARTIAL_BASKET_UNWOUND', 0)}) | "
            f"Decay[<5ms={dc_s.get('lt_5ms', 0)}, 5-15ms={dc_s.get('5_15ms', 0)}, 15-40ms={dc_s.get('15_40ms', 0)}, >40ms={dc_s.get('gt_40ms', 0)}] "
            f"Rung2Gate={db_s.get('rung2_migration_justified', False)}"
        )
    v6 = d.get("v6_expansion") or {}
    if v6:
        xv_s = v6.get("cross_venue_shadow") or {}
        l2_s = v6.get("l2_recorder") or {}
        _p("-" * 96)
        _p(
            f" v6 EXPANSION & XV  : 8 Engines Evaluated={v6.get('evaluated_total', 0)} (Hits={v6.get('opportunities_total', 0)}) | "
            f"StageG={xv_s.get('network_mode', 'init')} (Healthy={xv_s.get('service_healthy')}, Cycle #{xv_s.get('cycles_completed', 0)}, Pairs={xv_s.get('matched_pairs_seen', 0)}) | "
            f"L2Recorder={l2_s.get('frames_recorded', 0)} frames ({l2_s.get('archive_mb', 0.0):.2f} MB / 12.0 MB cap)"
        )
    _p("=" * 96)
    return "\n".join(out_lines)


def print_cli_summary(d: Dict[str, Any]) -> None:
    print(format_cli_summary(d))


def _reclaim_existing_dashboard_port(port: int) -> None:
    """If an older Dominus Command Center instance is holding 127.0.0.1:<port>, stop it cleanly before binding."""
    import socket
    import urllib.request

    def _port_in_use() -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            return s.connect_ex(("127.0.0.1", port)) == 0

    if not _port_in_use():
        return

    print(f"Detected existing listener on 127.0.0.1:{port} -- reclaiming previous Dominus Command Center...", flush=True)
    # 1. Try graceful localhost shutdown endpoint first (supported by v6.1+)
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/shutdown",
            data=b"",
            headers={"Host": f"127.0.0.1:{port}", "X-Dominus-Shutdown": "1"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=1.0):
            pass
    except Exception:
        pass

    for _ in range(10):
        if not _port_in_use():
            return
        time.sleep(0.1)

    # 2. Fallback on Windows/Linux for older background instances without /api/shutdown
    if os.name == "nt":
        try:
            ps_cmd = (
                f"$conns = Get-NetTCPConnection -LocalPort {int(port)} -State Listen -ErrorAction SilentlyContinue; "
                f"foreach ($c in $conns) {{ "
                f"  $proc = Get-CimInstance Win32_Process -Filter \"ProcessId=$($c.OwningProcess)\" -ErrorAction SilentlyContinue; "
                f"  if ($proc -and $proc.ProcessId -ne {os.getpid()} -and $proc.CommandLine -like '*dominus_command_center*') {{ "
                f"    Write-Output $proc.ProcessId; "
                f"    if ($proc.ParentProcessId) {{ "
                f"      $parent = Get-CimInstance Win32_Process -Filter \"ProcessId=$($proc.ParentProcessId)\" -ErrorAction SilentlyContinue; "
                f"      if ($parent -and $parent.CommandLine -like '*dominus_command_center*') {{ Write-Output $parent.ProcessId }} "
                f"    }} "
                f"  }} "
                f"}}"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=6.0,
            )
            pids = []
            for line in (res.stdout or "").splitlines():
                line = line.strip()
                if line.isdigit() and int(line) not in pids and int(line) != os.getpid():
                    pids.append(int(line))
            for pid in reversed(pids):
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                )
        except Exception:
            pass

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if not _port_in_use():
            return
        time.sleep(0.15)


def main() -> None:
    parser = argparse.ArgumentParser(description="DOMINUS — RISKLESS PAA Command Center v6.3")
    parser.add_argument(
        "--host",
        default=os.environ.get("DOMINUS_SSH_HOST", "kraken-finland"),
        help="SSH host alias (default: DOMINUS_SSH_HOST env or kraken-finland; set to kraken-nl after cutover)",
    )
    parser.add_argument("--port", type=int, default=8787, help="Local HTTP dashboard port")
    parser.add_argument("--once", action="store_true", help="Print CLI summary once and exit")
    parser.add_argument("--json", action="store_true", help="Print raw JSON snapshot once and exit")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser tab")
    args = parser.parse_args()

    if args.json:
        cache = SnapshotCache(host=args.host, start_bg=False)
        print(json.dumps(cache.get(force=True), indent=2))
        return
    if args.once:
        cache = SnapshotCache(host=args.host, start_bg=False)
        print_cli_summary(cache.get(force=True))
        return

    _reclaim_existing_dashboard_port(args.port)
    cache = SnapshotCache(host=args.host, start_bg=True)
    srv_ref: Dict[str, Any] = {"srv": None}

    class Handler(BaseHTTPRequestHandler):
        def _safe_send(self, code: int, content_type: str, body: bytes, no_store: bool = False, use_gzip: bool = False) -> None:
            try:
                out_body = gzip.compress(body, compresslevel=5) if use_gzip and len(body) > 1024 else body
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                if out_body is not body:
                    self.send_header("Content-Encoding", "gzip")
                self.send_header("Content-Length", str(len(out_body)))
                if no_store:
                    self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(out_body)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
                return

        def _is_allowed_local(self) -> bool:
            host_hdr = (self.headers.get("Host") or "").split(":")[0].strip().lower()
            if host_hdr and host_hdr not in ("127.0.0.1", "localhost"):
                try:
                    self.send_error(403, "Forbidden Host")
                except OSError:
                    pass
                return False
            return True

        def do_POST(self) -> None:
            if not self._is_allowed_local():
                return
            if (
                self.path == "/api/shutdown"
                and (self.client_address[0] in ("127.0.0.1", "::1"))
                and str(self.headers.get("X-Dominus-Shutdown") or "").strip() == "1"
            ):
                self._safe_send(200, "application/json; charset=utf-8", b'{"status":"shutting_down"}', no_store=True)
                def _stop() -> None:
                    cache.close_stream()
                    if srv_ref["srv"] is not None:
                        srv_ref["srv"].shutdown()
                threading.Thread(target=_stop, daemon=True).start()
                return
            try:
                self.send_error(404, "Not Found")
            except OSError:
                pass

        def do_GET(self) -> None:
            if not self._is_allowed_local():
                return
            accept_gz = "gzip" in (self.headers.get("Accept-Encoding") or "").lower()
            if self.path.startswith("/api/snapshot") or self.path.startswith("/api/state"):
                cache.touch_viewer()
                force = "force=1" in self.path
                payload = json.dumps(cache.get(force=force)).encode("utf-8")
                self._safe_send(200, "application/json; charset=utf-8", payload, no_store=True, use_gzip=accept_gz)
            elif self.path in ("/", "/index.html") or self.path.startswith("/?"):
                cache.touch_viewer()
                self._safe_send(200, "text/html; charset=utf-8", HTML_PAGE.encode("utf-8"), no_store=True, use_gzip=accept_gz)
            else:
                self._safe_send(204, "text/plain; charset=utf-8", b"", no_store=True, use_gzip=False)

        def log_message(self, fmt: str, *a: Any) -> None:
            return

    class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
        allow_reuse_address = os.name != "nt"

    url = f"http://127.0.0.1:{args.port}"
    srv = ExclusiveThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    srv_ref["srv"] = srv
    srv.daemon_threads = True
    print(
        f"Dominus Riskless PAA Command Center v6.3 running locally at {url} "
        f"(host={args.host}, persistent gzipped SSH stream=5s, auto-sleep after 45s idle, Ctrl+C to stop)",
        flush=True,
    )
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        cache.close_stream()
        try:
            srv.server_close()
        except Exception:
            pass
        print("\nStopped Dominus Riskless PAA Command Center.")


if __name__ == "__main__":
    main()
