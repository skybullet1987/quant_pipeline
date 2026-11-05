#!/usr/bin/env python3
"""
DOMINUS — RISKLESS PAA COMMAND CENTER v6.1 (24/7 Zero-Overhead Local Web Dashboard & CLI).

Replaces heavy VM Chrome Remote Desktop (which consumed ~1.74 GB RAM + ~45% CPU on
kraken-finland) with an institutional local command center at http://127.0.0.1:8787 that
fetches bounded read-only JSON snapshots over SSH using 0 MB persistent VM RAM.

v6.1 Architecture:
  - Penny-Exact Wallet-to-PnL Reconciliation ($60.92 Pure Riskless Lock Start + Post-Lock Cash Gain == Live Polygon pUSD)
  - 100% Riskless-First KPIs: Pure Riskless Live W/L, Post-Lock Zero-Loss Streak, On-Chain Cash & CLOB Quoting Utilization
  - Hero #1: Live Working CLOB Orders (with Cloudflare-safe Gamma title resolution & 1s live order-age tick) + Active Positions
  - Hero #2: Live Riskless Opportunity Radar (Live Harvester IPC, Machine-Gun Auto-Discovery, BOND1 UMA Carry, MKR_LOCK1 Clinch, Locked Rewards, NegRisk Slate Arbs)
  - Active-Riskless vs Historical-Legacy Filters on Strategy Breakdown & Closed Trades (with cached Gamma Market Questions)
  - RISKLESS PAA Zero-Trust OS Telemetry (7/7 Active Fleet + 9 RTDS/SHM Feeds, 1s timer/TTL countdowns, Tier-A/B/C memory, 5-Gate Verifier)

Usage:
  # Launch 24/7 auto-refreshing browser dashboard on Windows:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" scripts/dominus_command_center.py

  # Instant one-shot terminal summary:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" scripts/dominus_command_center.py --once
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

REMOTE_PROBE_PY = r"""# -*- coding: utf-8 -*-
import calendar, json, os, pathlib, re, sqlite3, statistics, subprocess, sys, time, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_OTTAWA_TZ = ZoneInfo("America/Toronto")
_HTTP_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def _to_ottawa_dt(val):
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        v = float(val)
        if v <= 0:
            return None
        return datetime.fromtimestamp(v / 1000.0 if v > 1e12 else v, tz=timezone.utc).astimezone(_OTTAWA_TZ)
    s = str(val).strip()
    if not s:
        return None
    try:
        v = float(s)
        if v > 1e8:
            return datetime.fromtimestamp(v / 1000.0 if v > 1e12 else v, tz=timezone.utc).astimezone(_OTTAWA_TZ)
    except Exception:
        pass
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

def _is_raw_stub_title(t):
    s = str(t or "").strip()
    return (not s) or s.startswith("Token ") or s.startswith("SPORTS_") or s.startswith("SINGLE_LEG_")

root = pathlib.Path("/home/skybullet1987/quant_pipeline")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
_now_et = datetime.now(_OTTAWA_TZ)
out = {
    "fetched_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    "fetched_at_et": _now_et.strftime("%Y-%m-%d %H:%M:%S %Z"),
    "ottawa_tz_abbr": _now_et.strftime("%Z"),
    "unix_ts": time.time(),
    "dashboard_version": "6.1.0",
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

# 2. Services (single batched systemctl call for consolidated Riskless PAA 7-unit topology)
svcs = [
    "polymarket-live-harvester.service",
    "polymarket-alpha124-shadow.service",
    "polymarket-recorder.service",
    "polymarket-telemetry-compactor.timer",
    "polymarket-paa-monitor.timer",
    "polymarket-paa-director.timer",
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
    _sup_p = subprocess.run(["systemctl", "is-active", "paa-system-supervisor.timer"], capture_output=True, text=True, timeout=2)
    svc_map["paa-system-supervisor.timer"] = _sup_p.stdout.strip() or ("active" if _sup_p.returncode == 0 else "inactive")
except Exception:
    svc_map["paa-system-supervisor.timer"] = "unknown"
out["services"] = svc_map

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
    _onchain_cash = None
    if _wallet_addr.startswith("0x") and len(_wallet_addr) == 42:
        _call_d = "0x70a08231" + _wallet_addr[2:].lower().rjust(64, "0")
        _batch = json.dumps([
            {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB", "data": _call_d}, "latest"], "id": 1},
            {"jsonrpc": "2.0", "method": "eth_call", "params": [{"to": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", "data": _call_d}, "latest"], "id": 2},
        ]).encode("utf-8")
        for _rpc_u in ("https://polygon-bor-rpc.publicnode.com", "https://polygon-rpc.com", "https://1rpc.io/matic"):
            try:
                _req = urllib.request.Request(_req_u := _rpc_u, data=_batch, headers={"Content-Type": "application/json", "User-Agent": _HTTP_UA})
                with urllib.request.urlopen(_req, timeout=1.8) as _resp:
                    _rj = json.loads(_resp.read().decode("utf-8"))
                if isinstance(_rj, list) and len(_rj) == 2 and all(isinstance(x, dict) and str(x.get("result") or "").startswith("0x") for x in _rj):
                    _onchain_cash = sum(int(x["result"], 16) / 1e6 for x in _rj)
                    break
            except Exception:
                continue

    _state_cash = float(s.get("live_bankroll", 0.0) or 0.0)
    _wallet_cash = float(_onchain_cash) if _onchain_cash is not None else _state_cash

    # Authoritative live open orders directly from Polymarket CLOB L2 (cached 12s in /tmp)
    resting_orders = []
    _clob_buy_quoting_usd = 0.0
    _resting_redeem_edge_usd = 0.0
    _clob_orders_ok = False
    try:
        import contextlib, io as _io
        _ord_cache_p = pathlib.Path("/tmp/dominus_clob_open_orders_cache.json")
        _tok_meta_cache_p = pathlib.Path("/tmp/dominus_clob_tok_meta_cache.json")
        _raw_ords = None
        if _ord_cache_p.exists() and (time.time() - _ord_cache_p.stat().st_mtime) <= 12.0:
            try:
                _raw_ords = json.loads(_ord_cache_p.read_text(encoding="utf-8"))
            except Exception:
                _raw_ords = None
        if _raw_ords is None:
            _buf_out, _buf_err = _io.StringIO(), _io.StringIO()
            with contextlib.redirect_stdout(_buf_out), contextlib.redirect_stderr(_buf_err):
                if str(root) not in sys.path:
                    sys.path.insert(0, str(root))
                if str(root / "src/polymarket_research") not in sys.path:
                    sys.path.insert(0, str(root / "src/polymarket_research"))
                from dotenv import load_dotenv as _ld_env
                _ld_env(root / ".env")
                from polymarket_live_executor import PolymarketLiveExecutor as _PLExec
                _ex_ro = _PLExec(dry_run=False)
                _raw_ords = _ex_ro.get_open_orders() or []
            try:
                _ord_cache_p.write_text(json.dumps(_raw_ords), encoding="utf-8")
            except Exception:
                pass
        if isinstance(_raw_ords, list):
            _clob_orders_ok = True
        _tok_meta = {}
        if _tok_meta_cache_p.exists():
            try:
                _tok_meta = json.loads(_tok_meta_cache_p.read_text(encoding="utf-8"))
            except Exception:
                _tok_meta = {}
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
                        "fallback_label": _fb_lbl,
                    }
            except Exception:
                pass
        _meta_dirty = False
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
            if _is_raw_stub_title(_ttl_o):
                try:
                    _gurl = (
                        f"https://gamma-api.polymarket.com/markets/{_mid_o}"
                        if _mid_o.isdigit()
                        else f"https://gamma-api.polymarket.com/markets?clob_token_ids={_aid}"
                    )
                    _rq_o = urllib.request.Request(_gurl, headers={"User-Agent": _HTTP_UA, "Accept": "application/json"})
                    with urllib.request.urlopen(_rq_o, timeout=1.5) as _ro:
                        _gj = json.loads(_ro.read().decode("utf-8"))
                    if isinstance(_gj, list) and _gj:
                        _gj = _gj[0]
                    if isinstance(_gj, dict):
                        _q_txt = str(_gj.get("question") or _gj.get("title") or "").strip()
                        if not _mid_o and _gj.get("id"):
                            _mid_o = str(_gj.get("id"))
                        if _q_txt:
                            _ttl_o = _q_txt
                            _tok_meta[_aid] = {**_m_info, "market_id": _mid_o, "title": _ttl_o}
                            _meta_dirty = True
                except Exception:
                    pass
            if _is_raw_stub_title(_ttl_o):
                _ttl_o = str(_m_info.get("fallback_label") or "") or f"Market #{_mid_o or _aid[:10]}"
            _exp_o = float(_m_info.get("expiry_ts") or 0.0)
            _rem_min = round((_exp_o - time.time()) / 60.0, 1) if _exp_o > time.time() else None
            _slv_o = str(_m_info.get("sleeve") or "BOND1_UMA_RESOLUTION_CARRY")
            _uma_floor_hr = 0.35 if "MKR_LOCK1" in _slv_o else 1.25
            _hold_hr = max(_uma_floor_hr, (_rem_min / 60.0) if (_rem_min is not None and _rem_min > 0) else 1.5)
            _edge_bps = round(max(0.0, (1.0 - _px_o) * 10000.0), 1)
            _bps_hr = round(_edge_bps / max(0.25, _hold_hr), 1)
            resting_orders.append({
                "order_id": _oid_cc,
                "market_id": _mid_o,
                "title": _ttl_o,
                "sleeve": _slv_o,
                "side": _side_o,
                "outcome": str(_o.get("outcome") or ""),
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
    _act_map = s.get("active_positions") or {}
    _active_book_usd = round(sum(float(p.get("remaining_cost_basis", p.get("notional_usd", 0.0)) or 0.0) for p in _act_map.values() if isinstance(p, dict)), 2)
    _live_equity_usd = round(_wallet_cash + _active_book_usd, 2) if _onchain_cash is not None else round(float(s.get("total_account_equity", 0.0) or 0.0), 2)
    _box_groups = {}
    for _p_act in _act_map.values():
        if isinstance(_p_act, dict) and _p_act.get("is_dominance_box") and _p_act.get("box_id"):
            _box_groups.setdefault(str(_p_act["box_id"]), []).append(_p_act)
    _paired_box_ids = {
        bid for bid, legs in _box_groups.items()
        if len(legs) == 2 and all(float(lg.get("custom_maker_exit_price") or 0.99) >= 0.95 for lg in legs)
    }
    _redeem_floor_positions = sum(
        min(float(lg.get("remaining_shares", lg.get("entry_shares", 0.0)) or 0.0) for lg in _box_groups[bid])
        for bid in _paired_box_ids
    ) + sum(
        float(p.get("remaining_cost_basis", p.get("notional_usd", 0.0)) or 0.0)
        for p in _act_map.values()
        if isinstance(p, dict) and str(p.get("box_id") or "") not in _paired_box_ids
    )
    _guaranteed_redeem_equity_usd = round(_wallet_cash + _redeem_floor_positions, 2)
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
            try:
                _rq_m = urllib.request.Request(f"https://gamma-api.polymarket.com/markets/{_mid_a}", headers={"User-Agent": _HTTP_UA, "Accept": "application/json"})
                with urllib.request.urlopen(_rq_m, timeout=1.4) as _rm:
                    _title_a = str(json.loads(_rm.read().decode("utf-8")).get("question") or "")
            except Exception:
                _title_a = ""
        _bbid_a, _bask_a = None, None
        if _tok_a:
            try:
                _rq_b = urllib.request.Request(f"https://clob.polymarket.com/book?token_id={_tok_a}", headers={"User-Agent": _HTTP_UA})
                with urllib.request.urlopen(_rq_b, timeout=1.2) as _rb:
                    _bk_j = json.loads(_rb.read().decode("utf-8"))
                _bds = [float(b["price"]) for b in (_bk_j.get("bids") or []) if float(b.get("size", 0) or 0) > 0]
                _aks = [float(a["price"]) for a in (_bk_j.get("asks") or []) if float(a.get("size", 0) or 0) > 0]
                if _bds:
                    _bbid_a = round(max(_bds), 4)
                if _aks:
                    _bask_a = round(min(_aks), 4)
            except Exception:
                pass
        _mtm_b_u = round(_sh_a * _bbid_a, 2) if (_bbid_a is not None and _sh_a > 0) else _not_a
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
            if _is_raw_stub_title(_q_c) and _mid_c.isdigit() and locals().get("_closed_g_fetches", 0) < 4:
                _closed_g_fetches = locals().get("_closed_g_fetches", 0) + 1
                try:
                    _rq_mc = urllib.request.Request(f"https://gamma-api.polymarket.com/markets/{_mid_c}", headers={"User-Agent": _HTTP_UA, "Accept": "application/json"})
                    with urllib.request.urlopen(_rq_mc, timeout=1.0) as _rmc:
                        _gj_c = json.loads(_rmc.read().decode("utf-8"))
                    if isinstance(_gj_c, dict) and _gj_c.get("question"):
                        _q_c = str(_gj_c["question"]).strip()
                        _tok_meta[f"mid:{_mid_c}"] = {"market_id": _mid_c, "title": _q_c}
                        if _tok_c:
                            _tok_meta[_tok_c] = {"market_id": _mid_c, "title": _q_c}
                        _meta_dirty = True
                except Exception:
                    pass
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
    _b1_pool_pct = int(round(100.0 * float(_bcfg.get("bond1_max_pool_fraction", 0.78) or 0.78)))
    _b1_mkt_cap = int(round(float(_bcfg.get("bond1_max_notional_per_market_usd", 45.0) or 45.0)))
    live_strat_meta = [
        ("BOND1_UMA_RESOLUTION_CARRY", f"LIVE ACTIVE — 0%-Fee UMA Resolution Carry ({_b1_pool_pct}% Pool Cap, <=${_b1_mkt_cap}/mkt, Preemptable)"),
        ("D1_SAME_ORACLE_DOMINANCE_BOX", f"LIVE ACTIVE — 32/32 Same-Oracle Crypto Dominance Box (<=${float(_bcfg.get('d1_max_box_cost_net', 0.985)):.3f} net)"),
        ("CM_B3_PYTH_BARRIER_BOX", f"LIVE ACTIVE — 0%-Fee Pyth Commodity Barrier Box (<=${float(_bcfg.get('cm_b3_max_walk_cap', 0.982)):.3f})"),
        ("S2_RTDS_EXACT_TWAP_INTEGRATOR", "LIVE ACTIVE — PolyBolt V2 1Hz Chainlink Final-45s Exact TWAP Lock"),
        ("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "LIVE ACTIVE — 0%-Fee Post-Clinch Maker Sweeper (p>=99.9%, <=$22, Preemptable)"),
        ("MKR_REWARD_LOCKED_CARRY", "LIVE ACTIVE — 100% Dead-NO Weather & Monotonic Counter Top-Queue Carry (<=$12)"),
        ("NR2_CONVERT_NO_SUBSET_ARB", "LIVE ACTIVE — NegRisk NR2/NR3 Atomic Convert & Synthetic All-YES Overround"),
        ("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX", "LIVE ACTIVE — 12/12 Deadline & Scalar Dominance Box (<=24h Fast-Recycle)"),
        ("COND1_MACRO_PARTITION_BOX", "LIVE ACTIVE — 9/9 Macro Partition Dominance Box (<=24h, <=$0.985 net)"),
        ("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", "LIVE ACTIVE — 0%-Fee Cross-Market Implication Box"),
        ("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK", "LIVE ACTIVE — 0%-Fee In-Game Milestone Irreversible Lock"),
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
            and (sl_k != "PRE_SPLIT_OVERROUND_MACHINE_GUN" or _ps_en)
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
    _post_lock_cash_delta = round(_live_equity_usd - _lock_start_eq, 2)
    out["polymarket_live"] = {
        "bankroll_usd": round(_wallet_cash, 2),
        "riskless_lock_start_usd": _lock_start_eq,
        "post_lock_cash_delta_usd": _post_lock_cash_delta,
        "post_lock_cash_pct": round(100.0 * _post_lock_cash_delta / _lock_start_eq, 1),
        "open_book_usd": _active_book_usd,
        "free_cash_usd": _free_cash_usd,
        "quoting_cash_usd": round(_inflight_intents_usd, 2),
        "quoting_utilization_pct": _quoting_util_pct,
        "resting_redeem_edge_usd": round(_resting_redeem_edge_usd, 2),
        "wallet_cash_usd": round(_wallet_cash, 2),
        "state_bankroll_usd": round(_state_cash, 2),
        "onchain_verified": _onchain_cash is not None,
        "clob_orders_verified": _clob_orders_ok,
        "equity_usd": _live_equity_usd,
        "mtm_bid_equity_usd": round(_wallet_cash + _mtm_bid_total, 2),
        "tp_target_equity_usd": round(_wallet_cash + _tp_val_total, 2),
        "guaranteed_redemption_equity_usd": _guaranteed_redeem_equity_usd,
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
else:
    out["polymarket_live"] = {}

# Recent notable live log lines (bounded 256 KB tail seek)
log_path = root / "data/polymarket/live_harvester.log"
if not log_path.exists():
    alt_lp = root / "logs/polymarket_live_harvester.log"
    if alt_lp.exists():
        log_path = alt_lp
log_events = []
maker_post_cnt = 0
_tail_lines = []
if log_path.exists():
    try:
        _pat_core = re.compile(r"\[CLOSED\]|\[LIVE FILL\]|\[LIVE PHASE 3A|\[CEILING -> PHASE 3A|\[AUTO-REDEEMER\]|\[RECONCILIATION\] Live collateral|\[D1 BOX|\[D1 LIVE|\[D1 FRESH BOOK|\[ATOMIC OVERROUND|\[MAKER ANCHOR|\[SINGLE-LEG LOCK|\[SINGLE-LEG MAKER LOCK|\[BOND1|GRAD8 AUTO|\[CONFIG_HOT_RELOAD\]|\[EV_SUPERVISOR|MACHINE_GUN")
        _pat_mkr = re.compile(r"\[LIVE MAKER ENTRY POSTED\]")
        with open(log_path, "rb") as _lf:
            _sz = log_path.stat().st_size
            _off = max(0, _sz - 262144)
            _lf.seek(_off)
            _tail_lines = _lf.read().decode("utf-8", errors="replace").splitlines()
        if _off > 0 and _tail_lines:
            _tail_lines = _tail_lines[1:]
        _core_hits = [x for x in _tail_lines if _pat_core.search(x)]
        _mkr_hits = [x for x in _tail_lines if _pat_mkr.search(x)]
        maker_post_cnt = len(_mkr_hits)
        _merged = sorted(set(_core_hits[-10:] + _mkr_hits[-5:]), key=lambda ln: ln[:23])
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
out["live_log_events"] = list(reversed(log_events))

# 3b. Shock & Order Attempt Forensics (Speed vs Gate Attribution + Historical Backfill)
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

# 4. Alpha-124 Riskless Frontier v1/v2/v3, _grad8 Auto-Promotion & Machine-Gun Auto-Discovery
a_path = root / "data/alpha124/alpha124_shadow_state.json"
mir_path = root / "data/polymarket/alpha124_shadow_state.json"
mir_by_slv = {}
if mir_path.exists():
    try:
        mir_by_slv = (json.loads(mir_path.read_text()).get("by_sleeve") or {})
    except Exception:
        mir_by_slv = {}
if a_path.exists():
    a = json.loads(a_path.read_text())
    by_slv = dict(a.get("by_sleeve") or {})
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
    ]
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
        g8_prom = (not _is_paused_rb) and bool(mm.get("grad8_live_promoted") or m.get("grad8_live_promoted") or (c_n >= 8 and l_n == 0 and float(m.get("realized_pnl_t1000_usd", 0.0) or 0.0) > 0))
        if g8_prom:
            promoted_cnt += 1
        elif (not _is_paused_rb) and 4 <= w_n < 8 and l_n == 0:
            near_grad8_cnt += 1
        is_v3 = slv in frontier_v3_grad8 or _is_mg
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
    out["alpha124"] = {
        "state_age_sec": round(now_u - a_path.stat().st_mtime, 1),
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
    "counts": {"LIVE_IPC": 0, "MACHINE_GUN": 0, "UMA_CARRY": 0, "POST_CLINCH": 0, "LOCKED_REWARD": 0, "SLATE_ARB": 0},
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

# Real-time Live IPC candidates (most recent first)
for _cd in reversed(_recent_ipc_cands[-45:]):
    try:
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
        _rem_hr_c = max(0.0, (float(_cd.get("expiry_ts") or 0.0) - time.time()) / 3600.0) if float(_cd.get("expiry_ts") or 0.0) > 0 else None
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
        _age_c = max(0, int(time.time() - float(_cd.get("ts_unix") or time.time())))
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
        radar_summary["scanned_at_et"] = _fmt_et(rk.get("scanned_at_utc"), "%H:%M:%S")
        radar_summary["age_sec"] = round(max(0.0, time.time() - rk_path.stat().st_mtime), 1)
        radar_summary["active_markets_scanned"] = int(rk.get("active_markets_scanned", 0) or 0)
        radar_summary["events_scanned"] = int(rk.get("events_scanned", 0) or 0)
        radar_summary["fee_free_markets"] = int(rk.get("fee_free_markets", 0) or 0)
        radar_summary["fee_enabled_markets"] = int(rk.get("fee_enabled_markets", 0) or 0)
        for _rt in (rk.get("alpha124_realtime_top_opportunities") or [])[:6]:
            _epx = float(_rt.get("ask_vwap") or 0.99)
            _eb = round(float(_rt.get("net_edge") or max(0.0, 1.0 - _epx)) * 10000.0, 1)
            _bhr = round(float(_rt.get("ev_per_dollar_hour") or 0.0) * 10000.0, 1)
            _cts = float(_rt.get("close_ts") or 0.0)
            _rhr = (_cts - time.time()) / 3600.0 if _cts > time.time() else 0.5
            _rt_lbl = re.sub(r"^\[[A-Z0-9_]+\]\s*", "", str(_rt.get("market") or "").strip())
            _push_radar("LIVE_IPC", str(_rt.get("sleeve") or "ALPHA124_RT"), "", _rt_lbl, "MAKER", _epx, _eb, _bhr, _rt.get("l1_usd", 0), _rhr, True, "A124 RT")
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
            if float(_rwq.get("p_model_at_post") or 0.0) < 0.999 or float(_rwq.get("best_bid_at_post") or 1.0) > 0.995:
                continue
            _rpx = float(_rwq.get("resting_bid") or 0.993)
            _reb = round(max(0.0, 1.0 - _rpx) * 10000.0, 1)
            _rrem = max(0.25, (float(_rwq.get("close_ts") or 0.0) - time.time()) / 3600.0)
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
        for _lr in (rk.get("ranked_locked_clob_rewards") or [])[:6]:
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

radar_opps.sort(
    key=lambda x: (
        0 if x.get("authorized_live") else 1,
        0 if x["bucket"] in ("LIVE_IPC", "MACHINE_GUN") else 1,
        -float(x.get("bps_per_hr") or 0.0),
    )
)
out["riskless_radar"] = {
    "summary": radar_summary,
    "opportunities": radar_opps[:36],
}
out["apex_testnet"] = {}

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
            if "polymarket-paa-" not in _u:
                continue
            _nxt_us = _t.get("next")
            _lst_us = _t.get("last")
            _nxt_s = (_nxt_us / 1e6) if isinstance(_nxt_us, (int, float)) and _nxt_us > 0 else None
            _lst_s = (_lst_us / 1e6) if isinstance(_lst_us, (int, float)) and _lst_us > 0 else None
            paa_out["systemd_timers"].append({
                "unit": _u.replace("polymarket-paa-", "").replace(".timer", ""),
                "full_unit": _u,
                "next_in_sec": round(max(0.0, _nxt_s - now_probe_u), 1) if _nxt_s else None,
                "last_ago_sec": round(max(0.0, now_probe_u - _lst_s), 1) if _lst_s else None,
                "last_et": _fmt_et(_lst_s, "%H:%M:%S") if _lst_s else "-",
                "next_et": _fmt_et(_nxt_s, "%H:%M:%S") if _nxt_s else "-",
            })
    _sys_sup = subprocess.run(["systemctl", "is-active", "paa-system-supervisor.timer"], capture_output=True, text=True, timeout=2.0)
    paa_out["pid1_supervisor_timer"] = _sys_sup.stdout.strip() or "unknown"
except Exception:
    paa_out["pid1_supervisor_timer"] = "unknown"

if paa_db_p.exists():
    try:
        _conn = sqlite3.connect(f"file:{paa_db_p}?mode=ro", uri=True, timeout=3.0)
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
                "SELECT recorded_at_utc, free_cash_pusd, open_cost_basis_usd, nav_mark_to_bid_usd FROM financial_snapshots WHERE recorded_at_utc <= ? ORDER BY snapshot_id DESC LIMIT 1",
                (_cut_24h_iso,),
            ).fetchone()
            if not _fs_24h:
                _fs_24h = _conn.execute(
                    "SELECT recorded_at_utc, free_cash_pusd, open_cost_basis_usd, nav_mark_to_bid_usd FROM financial_snapshots ORDER BY snapshot_id ASC LIMIT 1"
                ).fetchone()
            if _fs_24h and out.get("polymarket_live"):
                _eq_24h_ago = round(float(_fs_24h["free_cash_pusd"] or 0.0) + float(_fs_24h["open_cost_basis_usd"] or 0.0), 2)
                if _eq_24h_ago > 0:
                    _cur_eq = float(out["polymarket_live"].get("equity_usd") or 0.0)
                    _d24 = round(_cur_eq - _eq_24h_ago, 2)
                    out["polymarket_live"]["equity_24h_ago_usd"] = _eq_24h_ago
                    out["polymarket_live"]["equity_24h_delta_usd"] = _d24
                    out["polymarket_live"]["equity_24h_pct"] = round(100.0 * _d24 / _eq_24h_ago, 2)
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
        _conn.close()
    except Exception as _db_exc:
        paa_out["db_probe_warning"] = str(_db_exc)[:200]
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

print(json.dumps(out))
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>DOMINUS — RISKLESS PAA COMMAND CENTER v6.1</title>
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
      <span class="lock-badge" id="hdr_mode_badge">100% PURE RISKLESS LOCK &bull; v6.1</span>
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
  <button class="tab-btn" id="tab_orders" onclick="setViewTab('orders')">Live Orders &amp; Portfolio</button>
  <button class="tab-btn" id="tab_radar" onclick="setViewTab('radar')">Riskless Opportunity Radar</button>
  <button class="tab-btn" id="tab_a124" onclick="setViewTab('a124')">Alpha-124 &amp; Machine-Gun Grad-8</button>
  <button class="tab-btn" id="tab_paa" onclick="setViewTab('paa')">RISKLESS PAA Zero-Trust OS</button>
  <button class="tab-btn" id="tab_forensics" onclick="setViewTab('forensics')">Execution &amp; Fleet Diagnostics</button>
</div>

<div class="grid" id="kpis"></div>

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
      <h2 style="margin:0;">Consolidated Riskless Systemd Fleet (7/7) &amp; Multiplexed RTDS/SHM Oracle Feeds</h2>
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
  ['all', 'orders', 'radar', 'a124', 'paa', 'forensics'].forEach(k => {
    const b = document.getElementById('tab_' + k);
    if (b) b.className = 'tab-btn' + (k === tab ? ' active' : '');
  });
  const show = (id, cond) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('sec-hidden', !cond);
  };
  show('sec_live_orders', tab === 'all' || tab === 'orders');
  show('sec_radar', tab === 'all' || tab === 'radar');
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

function setRadarFilter(f) {
  _radarFilter = f;
  ['ALL', 'LIVE_IPC', 'MACHINE_GUN', 'UMA_CARRY', 'POST_CLINCH', 'LOCKED_REWARD', 'SLATE_ARB'].forEach(k => {
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
  ['focus', 'all'].forEach(k => {
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
    strip.innerHTML =
      `<span class="sf-chip">5m Universe Scan: <b>${(s.active_markets_scanned || 0).toLocaleString()}</b> Active Markets (<b>${(s.fee_free_markets || 0).toLocaleString()}</b> 0%-Fee &bull; ${s.age_sec ?? '-'}s old)</span>` +
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
    const curEq = Number(pm.equity_usd || pm.bankroll_usd || 0);
    const postCash = Number(pm.post_lock_cash_delta_usd ?? (curEq - lockStart));
    if (sparkLbl) sparkLbl.innerHTML = `All-Time Riskless: <b class="pos">+$${Number(pm.pure_riskless_pnl_usd || 0).toFixed(2)}</b> (${pm.pure_riskless_wins ?? 0}W/${pm.pure_riskless_losses ?? 0}L &bull; ${Number(pm.pure_riskless_wr_pct ?? 100).toFixed(1)}% WR) &bull; Post-Lock Cash: <b class="pos">${postCash >= 0 ? '+' : ''}$${postCash.toFixed(2)}</b> ($${lockStart.toFixed(2)} &rarr; $${curEq.toFixed(2)})`;
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
  const rows = _a124Filter === 'focus'
    ? sleeves.filter(s => !s.is_paused && (s.is_live || s.is_machine_gun || (s.losses === 0 && (s.wins > 0 || s.open > 0 || s.pending_quotes > 0))))
    : sleeves;
  const tb = document.getElementById('a124_sleeves');
  if (!tb) return;
  tb.innerHTML = rows.map(s => {
    const qBadge = s.pending_quotes ? ` <span class="warn">(${s.pending_quotes}q)</span>` : '';
    const mgBadge = s.is_machine_gun ? ` <span class="pill pill-mg" style="font-size:9.5px;padding:1px 5px;">MG</span>` : '';
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
    pulseEl.innerHTML = `VM SQLite Live Probe: <b>${esc(paa.live_probed_at_et || '-')} ET</b> (${Math.round(elapsedSec)}s ago &bull; Poll #${_pollSeq}) &bull; PID-1 Sup: <b class="${paa.pid1_supervisor_timer === 'active' ? 'pos' : 'warn'}">${esc(paa.pid1_supervisor_timer || 'active')}</b>`;
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
    stripEl.innerHTML =
      `<span class="sf-chip">Mode: <b class="${rlOn ? 'pos' : 'warn'}">${rlOn ? '100% RISKLESS LOCK' : 'HYBRID'}</b> (Pure Live <b class="${pureL === 0 ? 'pos' : 'warn'}">${pureW}W/${pureL}L</b> ${purePnl >= 0 ? '+' : ''}$${purePnl.toFixed(2)})</span>` +
      `<span class="sf-chip">Director: <b class="${dirHb.status === 'OK' || dirHb.status === 'RUNNING_CYCLE' ? 'pos' : 'warn'}">${esc(dirHb.status || 'INIT')}</b> (#${dirHb.cycle_count ?? 0}, ${fmtSecCompact(dirAge)})</span>` +
      `<span class="sf-chip">1m Monitor: <b class="${monHb.status === 'OK' ? 'pos' : 'warn'}">${esc(monHb.status || 'INIT')}</b> (${fmtSecCompact(monAge)}) &bull; 2m Sup: <b>${fmtSecCompact(supAge)}</b></span>` +
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
      modeBadge.textContent = risklessOnly ? '100% PURE RISKLESS LOCK • v6.1' : `HYBRID MODE v${cfgVer}`;
    }

    const syncEt = d.fetched_at_et || fmtOttawa(d.unix_ts || d.fetched_at_utc, 'full');
    _pollSeq += 1;
    _lastSyncClientMs = Date.now();
    _lastMetaPrefix = `Synced: ${syncEt} (Ottawa) | Load: ${la[0]} (${la[1]}, ${la[2]}) | RAM Free: ${mem.available || '?'} / ${mem.total || '?'} MB`;
    document.getElementById('meta').textContent = `${_lastMetaPrefix} | Live Poll #${_pollSeq} (0s ago)`;

    _lastPaaData = paa;
    renderPaaAutonomy(paa, 0);
    renderRisklessRadar(rad);
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
    const lockStartEq = Number(pm.riskless_lock_start_usd || 60.92);
    const postLockDelta = Number(pm.post_lock_cash_delta_usd ?? (totalEq - lockStartEq));
    const postLockPct = Number(pm.post_lock_cash_pct ?? (100.0 * postLockDelta / Math.max(0.01, lockStartEq)));
    const d24Usd = pm.equity_24h_delta_usd !== undefined && pm.equity_24h_delta_usd !== null ? Number(pm.equity_24h_delta_usd) : null;
    const lockBadge = `<span class="pill ${postLockDelta >= 0 ? 'pill-ok' : 'pill-warn'}" style="font-size:11px;vertical-align:middle;margin-left:4px;" title="Exact wallet gain since $${lockStartEq.toFixed(2)} Pure Riskless Lock">$${lockStartEq.toFixed(2)} &rarr; ${postLockDelta >= 0 ? '+' : ''}$${postLockDelta.toFixed(2)} (${postLockPct >= 0 ? '+' : ''}${postLockPct.toFixed(1)}%)</span>`;
    const quoteCash = Number(pm.quoting_cash_usd ?? 0);
    const freeCash = Number(pm.free_cash_usd ?? cash);
    const utilPct = Number(pm.quoting_utilization_pct ?? (cash > 0 ? (100 * quoteCash / cash) : 0));
    const ruinFloor = Number(rcfg.hard_ruin_floor_usd || 42.0);
    const restOrds = pm.resting_orders || [];
    const restEdge = Number(pm.resting_redeem_edge_usd ?? 0);
    const openCnt = (pm.active_positions || []).length;

    const prW = Number(pm.pure_riskless_wins ?? 0);
    const prL = Number(pm.pure_riskless_losses ?? 0);
    const prWr = Number(pm.pure_riskless_wr_pct ?? 100).toFixed(1);
    const prPnl = Number(pm.pure_riskless_pnl_usd ?? 0);
    const plW = Number(pm.post_lock_wins ?? 0);
    const plL = Number(pm.post_lock_losses ?? 0);
    const d24Sub = d24Usd !== null ? ` (24h: <b class="${d24Usd >= 0 ? 'pos' : 'warn'}">${d24Usd >= 0 ? '+' : ''}$${d24Usd.toFixed(2)}</b>)` : '';
    const openSub = openBook > 0.005 ? ` &bull; Open: <b>$${openBook.toFixed(2)}</b>` : '';

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
        <div class="label">On-Chain Cash &amp; Account Equity</div>
        <div class="val pos">$${totalEq.toFixed(2)} ${lockBadge}</div>
        <div class="util-bar"><div class="util-fill" style="width:${Math.min(100, utilPct)}%;"></div></div>
        <div class="sub">Cash: <b>$${cash.toFixed(2)}</b>${d24Sub}${openSub} &bull; Quoting: <b class="pos">$${quoteCash.toFixed(2)}</b> (${utilPct.toFixed(0)}%) &bull; Free: <b>$${freeCash.toFixed(2)}</b></div>
      </div>
      <div class="card">
        <div class="label">Pure Riskless Live Record</div>
        <div class="val ${prL === 0 ? 'pos' : 'warn'}">${prW}W / ${prL}L (${prWr}%)</div>
        <div class="sub">Post-Lock Cash: <b class="pos">${postLockDelta >= 0 ? '+' : ''}$${postLockDelta.toFixed(2)}</b> (${plW}W/${plL}L) &bull; All-Time Riskless: <b class="pos">${prPnl >= 0 ? '+' : ''}$${prPnl.toFixed(2)}</b> &bull; Losses: <b class="${plL === 0 ? 'pos' : 'neg'}">${plL}</b></div>
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
    const shmPills = Object.entries(shmAges).map(([sym, age]) => {
      const ok = age !== null && age !== undefined && Number(age) < 10.0;
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
setInterval(() => refreshNow(false), 6000);
</script>
</body>
</html>
"""


class SnapshotCache:
    def __init__(self, host: str, ttl_sec: float = 5.0, start_bg: bool = False) -> None:
        self.host = host
        self.ttl_sec = ttl_sec
        self._fetch_lock = threading.Lock()
        self._last_ts = 0.0
        self._last_data: Dict[str, Any] = {}
        if start_bg:
            t = threading.Thread(target=self._bg_loop, name="DominusSnapshotPoller", daemon=True)
            t.start()

    def _probe_once(self) -> Dict[str, Any]:
        try:
            proc = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=6",
                    self.host,
                    "/home/skybullet1987/quant_pipeline/venv/bin/python3 -",
                ],
                input=REMOTE_PROBE_PY,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=14,
            )
            if proc.returncode != 0:
                return {"error": (proc.stderr or proc.stdout).strip()[:400]}
            lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
            if not lines:
                return {"error": f"Unexpected SSH output: {proc.stdout[:200]}"}
            data = json.loads(lines[-1])
            self._last_data = data
            self._last_ts = time.time()
            return data
        except Exception as exc:
            return {"error": str(exc)}

    def _bg_loop(self) -> None:
        while True:
            with self._fetch_lock:
                self._probe_once()
            time.sleep(self.ttl_sec)

    def get(self, force: bool = False) -> Dict[str, Any]:
        if not force and self._last_data:
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


def print_cli_summary(d: Dict[str, Any]) -> None:
    if d.get("error"):
        print(f"[ERROR] Could not fetch telemetry: {d['error']}")
        return
    pm = d.get("polymarket_live") or {}
    mem = d.get("mem_mb") or {}
    la = d.get("load_avg") or [0, 0, 0]
    rad = d.get("riskless_radar") or {}
    rad_s = rad.get("summary") or {}
    a124 = d.get("alpha124") or {}
    print("=" * 84)
    print(f" DOMINUS RISKLESS PAA COMMAND CENTER v6.0  |  {d.get('fetched_at_et') or d.get('fetched_at_utc')}")
    print("=" * 84)
    print(
        f" Host Load (2 vCPU) : {la[0]} ({la[1]}, {la[2]})  |  "
        f"RAM Available: {mem.get('available')} / {mem.get('total')} MB  |  "
        f"Halt={pm.get('risk_halt')}"
    )
    _d24_s = (
        f" [{pm.get('equity_24h_delta_usd', 0):+.2f} USD / {pm.get('equity_24h_pct', 0):+.1f}% 24h]"
        if pm.get("equity_24h_delta_usd") is not None
        else ""
    )
    print(
        f" Equity & Wallet    : ${pm.get('equity_usd', 0):.2f} Total Equity{_d24_s}  |  "
        f"${pm.get('bankroll_usd', 0):.2f} Cash + ${pm.get('open_book_usd', 0):.2f} Open Book"
    )
    print(
        f" CLOB Maker Quoting : Quoting ${pm.get('quoting_cash_usd', 0):.2f} [{pm.get('quoting_utilization_pct', 0):.1f}%] across {len(pm.get('resting_orders') or [])} CLOB orders "
        f"| Free ${pm.get('free_cash_usd', 0):.2f} | Locked Redeem Edge +${pm.get('resting_redeem_edge_usd', 0):.2f}"
    )
    _flat_s = f", +{pm.get('pure_riskless_flat_merges', 0)} flat merges" if pm.get("pure_riskless_flat_merges") else ""
    print(
        f" Pure Riskless Live : {pm.get('pure_riskless_wins', 0)}W / {pm.get('pure_riskless_losses', 0)}L{_flat_s} "
        f"({pm.get('pure_riskless_wr_pct', 100.0):.1f}% WR | {pm.get('pure_riskless_pnl_usd', 0):+.2f} USD)  |  "
        f"Post-Lock Losses: {pm.get('post_lock_losses', 0)}  |  "
        f"All-Time Epoch (incl. paused legacy): {pm.get('epoch_wins', 0)}W/{pm.get('epoch_losses', 0)}L ({pm.get('epoch_net_pnl_usd', 0):+.2f} USD)"
    )
    for ro in (pm.get("resting_orders") or [])[:6]:
        print(
            f"   [LIVE CLOB ORDER] {ro.get('side')} ({ro.get('outcome')}) x {ro.get('shares'):.2f} @ ${ro.get('price'):.4f} "
            f"(${ro.get('notional_usd'):.2f} -> +${ro.get('redeem_edge_usd', 0):.2f} edge, ~{ro.get('est_bps_per_hr', 0):.0f} bps/hr) | {str(ro.get('title'))[:62]}"
        )
    print("-" * 84)
    print(
        f" Riskless Opportunity Radar ({rad_s.get('active_markets_scanned', 0):,} Active Mkts | "
        f"{rad_s.get('fee_free_markets', 0):,} 0%-Fee | Peak {rad_s.get('top_bps_per_hr', 0):.0f} bps/hr):"
    )
    for op in (rad.get("opportunities") or [])[:6]:
        print(
            f"   [{op.get('bucket', ''):13s}] ${op.get('entry_px', 0):.3f} (+{op.get('edge_bps', 0):4.0f} bps | {op.get('bps_per_hr', 0):5.0f} bps/hr) | "
            f"{str(op.get('title', ''))[:58]}"
        )
    print("-" * 84)
    print(
        f" Alpha-124 & _grad8 : {a124.get('promoted_count', 0)} Live 8/8 | "
        f"Zero-Loss T1000 Shadow: +{a124.get('zero_loss_t1000_pnl_usd', 0):.2f} USD ({a124.get('zero_loss_wins_total', 0)}W/0L) | "
        f"Near-Grad8: {a124.get('near_grad8_count', 0)} | Machine-Gun: {len(a124.get('machine_gun_sleeves') or [])} sleeves"
    )
    for s in (a124.get("sleeves") or [])[:12]:
        print(
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
            f"{t['unit']}={t['next_in_sec']}s"
            for t in sorted(paa.get("systemd_timers") or [], key=lambda x: x.get("next_in_sec") or 999999)[:4]
        )
        rl = paa.get("riskless_kpis") or {}
        print("-" * 84)
        print(
            f" RISKLESS PAA OS    : Lock={rl.get('riskless_only_mode', True)} (Pure Live {rl.get('pure_riskless_live_wins', 0)}W/{rl.get('pure_riskless_live_losses', 0)}L "
            f"{float(rl.get('pure_riskless_realized_pnl_usd', 0.0) or 0.0):+.2f} USD) | "
            f"Director={dh.get('status', 'INIT')} (Cycle #{dh.get('cycle_count', 0)}, age={dh.get('age_sec')}s) | "
            f"Monitor={mh.get('status', 'INIT')} (age={mh.get('age_sec')}s) | "
            f"AI=${br.get('daily_ai_cost_usd', 0.0):.4f}/{br.get('max_daily_ai_cost_usd', 2.50):.2f}"
        )
        print(
            f" Zero-Trust State   : Policies={paa.get('tier_a_intact_count', 0)}/5 | "
            f"Facts(Fresh={zt.get('verified_facts_fresh', 0)}, Stale={zt.get('verified_facts_stale', 0)}, Contra={zt.get('verified_facts_contradicted', 0)}) | "
            f"Sessions={zt.get('sessions_total', 0)} ({zt.get('fresh_session_pct', 100.0)}% fresh, peak_ctx={zt.get('max_context_pct', 0.0)}%/60%) | "
            f"Tasks={json.dumps(tc)}"
        )
        print(f" Schedules & TierC  : Next=[{tm_short}] | Ladder={json.dumps(lad)}")
    print("=" * 84)


def main() -> None:
    parser = argparse.ArgumentParser(description="DOMINUS — RISKLESS PAA Command Center v6.1")
    parser.add_argument("--host", default="kraken-finland", help="SSH host alias")
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

    cache = SnapshotCache(host=args.host, start_bg=True)

    class Handler(BaseHTTPRequestHandler):
        def _safe_send(self, code: int, content_type: str, body: bytes, no_store: bool = False) -> None:
            try:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                if no_store:
                    self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
                return

        def do_GET(self) -> None:
            host_hdr = (self.headers.get("Host") or "").split(":")[0].strip().lower()
            if host_hdr and host_hdr not in ("127.0.0.1", "localhost"):
                try:
                    self.send_error(403, "Forbidden Host")
                except OSError:
                    pass
                return
            if self.path.startswith("/api/snapshot"):
                force = "force=1" in self.path
                payload = json.dumps(cache.get(force=force)).encode("utf-8")
                self._safe_send(200, "application/json; charset=utf-8", payload, no_store=True)
            else:
                self._safe_send(200, "text/html; charset=utf-8", HTML_PAGE.encode("utf-8"), no_store=True)

        def log_message(self, fmt: str, *a: Any) -> None:
            return

    class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
        allow_reuse_address = os.name != "nt"

    url = f"http://127.0.0.1:{args.port}"
    srv = ExclusiveThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    srv.daemon_threads = True
    print(f"Dominus Riskless PAA Command Center v6.1 running locally at {url} (Background SSH cache=5s, Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped Dominus Riskless PAA Command Center.")


if __name__ == "__main__":
    main()
