#!/usr/bin/env python3
"""
Dominus Zero-Overhead Live Command Center (24/7 Constant Local Web Dashboard & CLI).

Replaces heavy VM Chrome Remote Desktop (which consumed ~1.74 GB RAM + ~45% CPU on
kraken-finland) with a constant local dashboard at http://127.0.0.1:8787 that
fetches <12 KB read-only JSON snapshots over SSH using 0 MB persistent VM RAM.

Usage:
  # Launch 24/7 auto-refreshing browser dashboard on Windows:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" scripts/dominus_command_center.py

  # Instant one-shot terminal summary:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" scripts/dominus_command_center.py --once
"""

from __future__ import annotations

import argparse
import json
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

root = pathlib.Path("/home/skybullet1987/quant_pipeline")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
_now_et = datetime.now(_OTTAWA_TZ)
out = {
    "fetched_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    "fetched_at_et": _now_et.strftime("%Y-%m-%d %H:%M:%S %Z"),
    "ottawa_tz_abbr": _now_et.strftime("%Z"),
    "unix_ts": time.time(),
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

# 2. Services (single batched systemctl call for consolidated v5.0 + PAA topology)
svcs = [
    "polymarket-live-harvester.service",
    "polymarket-alpha124-shadow.service",
    "polymarket-recorder.service",
    "polymarket-telemetry-compactor.timer",
    "polymarket-trader.service",
    "apex-perp.service",
    "apex-oversight-audit.timer",
    "polymarket-paa-monitor.timer",
    "polymarket-paa-supervisor.timer",
    "polymarket-paa-watchdog.timer",
    "polymarket-paa-director.timer",
    "polymarket-paa-director-event.path",
]
shm_ages = {}
shm_spots = {}
shm_anchored = {}
for _sym in ("BTC", "ETH", "SOL", "XAU"):
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
    else:
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
    "schema_version": strat_cfg.get("schema_version", "5.1.0"),
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
    ap = subprocess.run(["pgrep", "-f", "production_apex_daemon.py"], capture_output=True, text=True, timeout=2)
    svc_map["hyperliquid-apex-testnet"] = "active" if ap.returncode == 0 and ap.stdout.strip() else "inactive"
except Exception:
    svc_map["hyperliquid-apex-testnet"] = "unknown"
out["services"] = svc_map

# 3. Polymarket Live Harvester + Per-Strategy Real W/L + Live Log Events
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

    # Authoritative live Polygon wallet cash (pUSD + USDC.e) so pre-indexer state snapshots never drift
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
                _req = urllib.request.Request(_rpc_u, data=_batch, headers={"Content-Type": "application/json", "User-Agent": "DominusCommandCenter/1.0"})
                with urllib.request.urlopen(_req, timeout=1.8) as _resp:
                    _rj = json.loads(_resp.read().decode("utf-8"))
                if isinstance(_rj, list) and len(_rj) == 2 and all(isinstance(x, dict) and str(x.get("result") or "").startswith("0x") for x in _rj):
                    _onchain_cash = sum(int(x["result"], 16) / 1e6 for x in _rj)
                    break
            except Exception:
                continue

    _state_cash = float(s.get("live_bankroll", 0.0) or 0.0)
    _wallet_cash = float(_onchain_cash) if _onchain_cash is not None else _state_cash
    _inflight_intents_usd = sum(
        float(i.get("notional_usd", 0.0) or 0.0)
        for i in (s.get("pending_entry_intents") or {}).values()
        if isinstance(i, dict)
    )
    _free_cash_usd = round(max(0.0, _wallet_cash - _inflight_intents_usd), 2)
    _act_map = s.get("active_positions") or {}
    _active_book_usd = sum(float(p.get("remaining_cost_basis", p.get("notional_usd", 0.0)) or 0.0) for p in _act_map.values() if isinstance(p, dict))
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
    # Reconcile actual wallet cash PnL on zero-fee boxes + pre-fix Phase 3A partial-WS/REST-lag fill truncation
    _ONCHAIN_WALLET_RECON = {
        "LIVE_6399804_1793391806_DOWN": {"pnl": -18.63, "notional": 18.63, "entry_px": 0.81},
    }
    def _true_pnl(c: dict) -> tuple[float, float, bool]:
        raw = round(float(c.get("net_pnl_usd", 0.0) or 0.0), 2)
        ovr = _ONCHAIN_WALLET_RECON.get(str(c.get("trade_id") or ""))
        if ovr is not None:
            return ovr["pnl"], raw, True
        if (
            c.get("is_dominance_box")
            and float(c.get("fee_rate_applied", 0.07) or 0.0) == 0.0
            and c.get("exit_fee_estimated")
            and float(c.get("payout_usd", 0.0) or 0.0) > float(c.get("notional_usd", 0.0) or 0.0)
        ):
            wallet_pnl = round(float(c.get("payout_usd", 0.0)) - float(c.get("notional_usd", 0.0)) - float(c.get("fee_usd", 0.0) or 0.0), 2)
            return wallet_pnl, raw, True
        return raw, raw, False

    wins_raw = sum(1 for c in closed if float(c.get("net_pnl_usd", 0.0)) > 0)
    tot_pnl_raw = round(sum(float(c.get("net_pnl_usd", 0.0)) for c in closed), 2)
    tot_fees = round(sum(float(c.get("fee_usd", 0.0)) for c in closed), 2)
    wins_wallet = 0
    tot_pnl_wallet = 0.0
    today_utc_date = time.strftime("%Y-%m-%d", time.gmtime())
    today_et_date = _now_et.strftime("%Y-%m-%d")
    today_cut = f"{today_utc_date}T00:00:00"
    v51_cut = "2026-11-01T01:22:00"
    today_w, today_l, today_pnl = 0, 0, 0.0
    v51_w, v51_l, v51_pnl = 0, 0, 0.0
    strat_stats = {}
    for c in closed:
        wp, rp, adj = _true_pnl(c)
        tot_pnl_wallet = round(tot_pnl_wallet + wp, 2)
        is_w = wp > 0
        if is_w:
            wins_wallet += 1
        sl = str(c.get("sleeve") or "UNKNOWN")
        rec_s = strat_stats.setdefault(sl, {"sleeve": sl, "open": 0, "today_w": 0, "today_l": 0, "today_pnl": 0.0, "v51_w": 0, "v51_l": 0, "v51_pnl": 0.0, "epoch_w": 0, "epoch_l": 0, "epoch_pnl": 0.0})
        if is_w:
            rec_s["epoch_w"] += 1
        else:
            rec_s["epoch_l"] += 1
        rec_s["epoch_pnl"] = round(rec_s["epoch_pnl"] + wp, 2)
        ts_e = str(c.get("entry_time_utc") or "")
        if ts_e >= today_cut:
            if is_w:
                today_w += 1
                rec_s["today_w"] += 1
            else:
                today_l += 1
                rec_s["today_l"] += 1
            today_pnl = round(today_pnl + wp, 2)
            rec_s["today_pnl"] = round(rec_s["today_pnl"] + wp, 2)
        if ts_e >= v51_cut:
            if is_w:
                v51_w += 1
                rec_s["v51_w"] += 1
            else:
                v51_l += 1
                rec_s["v51_l"] += 1
            v51_pnl = round(v51_pnl + wp, 2)
            rec_s["v51_pnl"] = round(rec_s["v51_pnl"] + wp, 2)

    act_list = []
    _mtm_bid_total = 0.0
    _tp_val_total = 0.0
    for tid, p in (s.get("active_positions") or {}).items():
        sl_a = str(p.get("sleeve") or "UNKNOWN")
        strat_stats.setdefault(sl_a, {"sleeve": sl_a, "open": 0, "today_w": 0, "today_l": 0, "today_pnl": 0.0, "v51_w": 0, "v51_l": 0, "v51_pnl": 0.0, "epoch_w": 0, "epoch_l": 0, "epoch_pnl": 0.0})["open"] += 1
        _sh_a = float(p.get("remaining_shares", p.get("entry_shares", 0.0)) or 0.0)
        _not_a = round(float(p.get("remaining_cost_basis", p.get("notional_usd", 0.0)) or 0.0), 2)
        _tp_a = float(p.get("target_exit_price") or 0.0)
        _mid_a = str(p.get("market_id") or "")
        _tok_a = str(p.get("token_id") or "")
        _title_a = str(p.get("title") or p.get("question") or "")
        if not _title_a and _mid_a.isdigit():
            try:
                _rq_m = urllib.request.Request(f"https://gamma-api.polymarket.com/markets/{_mid_a}", headers={"User-Agent": "DominusCommandCenter/1.0"})
                with urllib.request.urlopen(_rq_m, timeout=1.2) as _rm:
                    _title_a = str(json.loads(_rm.read().decode("utf-8")).get("question") or "")
            except Exception:
                _title_a = ""
        _bbid_a, _bask_a = None, None
        if _tok_a:
            try:
                _rq_b = urllib.request.Request(f"https://clob.polymarket.com/book?token_id={_tok_a}", headers={"User-Agent": "DominusCommandCenter/1.0"})
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
    for c in closed:
        wp, _, _ = _true_pnl(c)
        cum = round(cum + wp, 2)
        equity_curve.append(cum)
    for c in reversed(closed[-14:]):
        wp, rp, adj = _true_pnl(c)
        ovr_c = _ONCHAIN_WALLET_RECON.get(str(c.get("trade_id") or "")) or {}
        _raw_ts_c = c.get("exit_time_utc") or c.get("settled_at_utc") or c.get("closed_at_ts") or c.get("exit_ts") or c.get("entry_time_utc") or c.get("entry_ts") or ""
        _ex_px_c = c.get("average_exit_price")
        if not _ex_px_c:
            _ex_px_c = c.get("exit_price")
        recent_closed.append({
            "time_utc": str(c.get("exit_time_utc") or c.get("settled_at_utc") or c.get("entry_time_utc") or "")[:19].replace("T", " "),
            "time_et": _fmt_et(_raw_ts_c, "%m-%d %H:%M:%S"),
            "unix_ts": float(c.get("exit_ts") or c.get("closed_at_ts") or c.get("entry_ts") or 0.0),
            "trade_id": c.get("trade_id"),
            "asset": f"{c.get('asset','')} {c.get('horizon','')} {c.get('target_token','')}".strip(),
            "sleeve": c.get("sleeve"),
            "entry_px": ovr_c.get("entry_px", c.get("entry_price")),
            "exit_px": _ex_px_c,
            "notional_usd": round(float(ovr_c.get("notional", c.get("notional_usd", 0.0)) or 0.0), 2),
            "fee_usd": round(float(c.get("fee_usd", 0.0) or 0.0), 2),
            "net_pnl_usd": wp,
            "raw_pnl_usd": rp,
            "fee_reconciled": adj,
            "reason": c.get("close_reason") or c.get("status"),
        })
    _dcfg = strat_cfg.get("directional") or {}
    _bcfg = strat_cfg.get("riskless_boxes") or {}
    _a1h = "/".join(_dcfg.get("allowed_assets_1h") or ["BTC", "ETH", "SOL"])
    _a15 = "/".join(_dcfg.get("allowed_assets_15m_taker") or _dcfg.get("allowed_assets_15m_maker") or ["BTC", "ETH", "SOL"])
    _tk1h = float(_dcfg.get("max_taker_price_1h", 0.82) or 0.82)
    _mk1h = float(_dcfg.get("max_maker_price_1h", 0.76) or 0.76)
    _mk1h_on = bool(_dcfg.get("enable_1h_shielded_maker", False))
    _mk15 = float(_dcfg.get("max_maker_price_15m", 0.72) or 0.72)
    _mk15_on = bool(_dcfg.get("enable_15m_subordinate_maker", False))
    _tk15_on = bool(_dcfg.get("enable_15m_taker", True))
    _tk15_px = float(_dcfg.get("max_taker_price_15m", 0.82) or 0.82)
    _t15_lo = int(float(_dcfg.get("min_tte_15m_taker_sec", 120) or 120))
    _t15_hi = int(float(_dcfg.get("max_tte_15m_taker_sec", 510) or 510))
    _z1h = float(_dcfg.get("min_z_1h_regime_b", _dcfg.get("min_z_1h", 1.00)) or 1.00)
    _z15 = float(_dcfg.get("min_z_15m_taker", 1.20) or 1.20)
    _s1h_desc = (
        f"{_a1h} 1h Core (Taker <=${_tk1h:.2f} + Maker <=${_mk1h:.2f}, Z>={_z1h:.2f}, $0.93 MFE Lock)"
        if _mk1h_on
        else f"{_a1h} 1h Taker-Only ([150-900s] <=${_tk1h:.2f}, Z>={_z1h:.2f}, 0 Maker, $0.93 MFE Lock)"
    )
    if _tk15_on and _mk15_on:
        _s15_desc = f"{_a15} 15m Taker [{_t15_lo}-{_t15_hi}s <=${_tk15_px:.2f}] + 0%-Fee Maker (<=${_mk15:.2f})"
    elif _tk15_on:
        _s15_desc = f"{_a15} 15m Taker-Only ([{_t15_lo}-{_t15_hi}s] <=${_tk15_px:.2f}, Z>={_z15:.2f}, 0 Maker)"
    else:
        _s15_desc = f"{_a15} 15m Subordinate Maker-Only (<=${_mk15:.2f}, 0.80x; Taker OFF)"
    live_strat_meta = [
        ("SLEEVE_1_CORE_302", _s1h_desc),
        ("SLEEVE_1_SUBHOURLY_15M", _s15_desc),
        ("BOND1_UMA_RESOLUTION_CARRY", "Live 23/23 0%-Fee UMA Carry (Maker + Post-End Taker <=$25, Disputed Recycle)"),
        ("COND1_MACRO_PARTITION_BOX", "Live 9/9 Macro Partition Dominance Box (<=24h, <=$0.985 net)"),
        ("CM_B3_PYTH_BARRIER_BOX", f"Live 0%-Fee Pyth Commodity Box (<=${float(_bcfg.get('cm_b3_max_walk_cap', 0.982)):.3f})"),
        ("D1_SAME_ORACLE_DOMINANCE_BOX", f"Live 32/32 Same-Oracle Crypto Box (<=${float(_bcfg.get('d1_max_box_cost_net', 0.985)):.3f} net)"),
        ("LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", "Live 0%-Fee Cross-Market Implication Box"),
        ("SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX", "Live Fee-Exact Soccer 3-Way Synthetic Box"),
        ("SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK", "Live 0%-Fee In-Game Milestone Lock"),
    ]
    live_strategies = []
    seen_ls = set()
    for sl_k, desc_s in live_strat_meta:
        seen_ls.add(sl_k)
        st_d = strat_stats.get(sl_k) or {"sleeve": sl_k, "open": 0, "today_w": 0, "today_l": 0, "today_pnl": 0.0, "v51_w": 0, "v51_l": 0, "v51_pnl": 0.0, "epoch_w": 0, "epoch_l": 0, "epoch_pnl": 0.0}
        live_strategies.append({**st_d, "desc": desc_s})
    for sl_k, st_d in strat_stats.items():
        if sl_k not in seen_ls:
            live_strategies.append({**st_d, "desc": "Live Harvester Sleeve"})

    _rk_st = s.get("risk_state") or {}
    out["polymarket_live"] = {
        "bankroll_usd": round(_wallet_cash, 2),
        "free_cash_usd": _free_cash_usd,
        "quoting_cash_usd": round(_inflight_intents_usd, 2),
        "wallet_cash_usd": round(_wallet_cash, 2),
        "state_bankroll_usd": round(_state_cash, 2),
        "onchain_verified": _onchain_cash is not None,
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
        "today_utc_date": today_utc_date,
        "today_et_date": today_et_date,
        "today_wins": today_w,
        "today_losses": today_l,
        "today_net_pnl_usd": today_pnl,
        "v51_wins": v51_w,
        "v51_losses": v51_l,
        "v51_net_pnl_usd": v51_pnl,
        "epoch_closed_count": len(closed),
        "epoch_wins": wins_wallet,
        "epoch_losses": len(closed) - wins_wallet,
        "epoch_wins_raw": wins_raw,
        "epoch_net_pnl_usd": tot_pnl_wallet,
        "epoch_net_pnl_raw_usd": tot_pnl_raw,
        "epoch_fees_usd": tot_fees,
        "trades_this_hour": s.get("trades_this_hour", 0),
        "equity_curve": equity_curve,
        "active_positions": act_list,
        "live_strategies": live_strategies,
        "recent_closed": recent_closed,
    }
else:
    out["polymarket_live"] = {}

# Recent notable live log lines (bounded 256 KB tail seek - zero full-file scan)
log_path = root / "data/polymarket/live_harvester.log"
if not log_path.exists():
    alt_lp = root / "logs/polymarket_live_harvester.log"
    if alt_lp.exists():
        log_path = alt_lp
log_events = []
maker_post_cnt = 0
if log_path.exists():
    try:
        _pat_core = re.compile(r"\[CLOSED\]|\[LIVE FILL\]|\[LIVE PHASE 3A|\[CEILING -> PHASE 3A|\[AUTO-REDEEMER\]|\[RECONCILIATION\] Live collateral|\[D1 BOX|\[D1 LIVE|\[D1 FRESH BOOK|\[ATOMIC OVERROUND|\[MAKER ANCHOR|\[SINGLE-LEG LOCK|\[SINGLE-LEG MAKER LOCK|\[BOND1|GRAD8 AUTO|\[TAKER ASYMMETRY VETO\]|\[WFO Z-CUSHION REJECT\]|\[COMPOSITE_EDGE_VETO\]|\[SHADOW_ETH_COLLECTED\]|\[CONFIG_HOT_RELOAD\]|\[EV_SUPERVISOR")
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
        _merged = sorted(set(_core_hits[-9:] + _mkr_hits[-4:]), key=lambda ln: ln[:23])
        _re_log_utc = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3} UTC\]\s*")
        for ln in _merged[-11:]:
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

# Backfill historical Taker traces & recent log attempts/vetoes whenever live forensics has < 16 real order attempts
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
    if log_path.exists():
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
                elif "[TAKER ASYMMETRY VETO]" in _ln:
                    _m = re.search(r"'([^']+)' (UP|DOWN): first_ask \$([0-9.]+) > \$([0-9.]+).*<= \$([0-9.]+) \(bid=\$([0-9.]+), TTE=([0-9.]+)s, z_strike=([0-9.-]+)\)", _ln)
                    if _m:
                        _ttl = _m.group(1)
                        _as = "BTC" if "Bitcoin" in _ttl else ("SOL" if "Solana" in _ttl else ("ETH" if "Ethereum" in _ttl else "CRYPTO"))
                        _add_sf({
                            "unix_ts": _u, "ts_utc": _iso, "title": _ttl, "asset": _as,
                            "horizon": "15m" if ("15" in _ttl or ":15" in _ttl or ":30" in _ttl or ":45" in _ttl) else "1h",
                            "side": _m.group(2), "path_type": "PRE_EVAL", "gate_code": "TAKER_ASYMMETRY_VETO",
                            "eval_ask": float(_m.group(3)), "cap_px": float(_m.group(5)), "eval_bid": float(_m.group(6)),
                            "tte_s": float(_m.group(7)), "z_strike": float(_m.group(8)),
                        })
                elif "[V5_15M_TAKER_DISABLED_MAKER_VETO]" in _ln:
                    _m = re.search(r"'([^']+)' (UP|DOWN):.*<= \$([0-9.]+) \(ask=\$([0-9.]+), bid=\$([0-9.]+)\)", _ln)
                    if _m:
                        _ttl = _m.group(1)
                        _as = "BTC" if "Bitcoin" in _ttl else ("SOL" if "Solana" in _ttl else ("ETH" if "Ethereum" in _ttl else "CRYPTO"))
                        _add_sf({
                            "unix_ts": _u, "ts_utc": _iso, "title": _ttl, "asset": _as, "horizon": "15m",
                            "side": _m.group(2), "path_type": "PRE_EVAL", "gate_code": "15M_MAKER_INELIGIBLE",
                            "cap_px": float(_m.group(3)), "eval_ask": float(_m.group(4)), "eval_bid": float(_m.group(5)),
                        })
                elif "[CLOB_WS_DISCONNECTED_REJECT]" in _ln:
                    _m = re.search(r"'([^']+)': ([A-Z]+) recorder Polymarket CLOB WS disconnected", _ln)
                    if _m:
                        _add_sf({
                            "unix_ts": _u, "ts_utc": _iso, "title": _m.group(1), "asset": _m.group(2),
                            "path_type": "PRE_EVAL", "gate_code": "CLOB_WS_DISCONNECTED",
                            "gate_detail": f"{_m.group(2)} recorder CLOB WS disconnected (fixed in US-DST patch)",
                        })
                elif "[COMPOSITE_EDGE_VETO]" in _ln:
                    _m = re.search(r"'([^']+)' (UP|DOWN): ([^\)]+\)?)", _ln)
                    if _m:
                        _ttl = _m.group(1)
                        _as = "BTC" if "Bitcoin" in _ttl else ("SOL" if "Solana" in _ttl else ("ETH" if "Ethereum" in _ttl else ("XAU" if "Gold" in _ttl else "CRYPTO")))
                        _add_sf({
                            "unix_ts": _u, "ts_utc": _iso, "title": _ttl, "asset": _as, "side": _m.group(2),
                            "path_type": "PRE_EVAL", "gate_code": "COMPOSITE_EDGE_VETO", "gate_detail": _m.group(3),
                        })
                elif "[WFO Z-CUSHION REJECT]" in _ln:
                    _m = re.search(r"'([^']+)' (UP|DOWN): z_strike=([0-9.-]+) < ([0-9.]+) floor \(dist=([0-9.+-]+)%, TTE=([0-9.]+)s\)", _ln)
                    if _m:
                        _ttl = _m.group(1)
                        _as = "BTC" if "Bitcoin" in _ttl else ("SOL" if "Solana" in _ttl else ("ETH" if "Ethereum" in _ttl else ("XAU" if "Gold" in _ttl else "CRYPTO")))
                        _add_sf({
                            "unix_ts": _u, "ts_utc": _iso, "title": _ttl, "asset": _as, "side": _m.group(2),
                            "path_type": "PRE_EVAL", "gate_code": "WFO_Z_CUSHION",
                            "z_strike": float(_m.group(3)), "dist_pct": float(_m.group(5)), "tte_s": float(_m.group(6)),
                            "gate_detail": f"z_strike={_m.group(3)} < {_m.group(4)} floor (dist={_m.group(5)}%, TTE={_m.group(6)}s)",
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

# 4. Alpha-124 Riskless Frontier v1/v2/v3, _grad8 Auto-Promotion & Shadow Trades + Directional Paper-Trader
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
    by_slv = a.get("by_sleeve") or {}
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
        "NR2_CONVERT_NO_SUBSET_ARB",
    }
    watch_sleeves = [
        # Promoted 8/8 & Active Live-Bridged Frontier v1/v2
        "BOND1_UMA_RESOLUTION_CARRY",
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
        # Frontier v3 + v4 Auto-Grad8 Sleeves (strictly require 8/8 shadow wins, 0 losses -> auto-promote to live IPC)
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
        # Active Shadow Research Sleeves
        "NR0_ZERO_FEE_SLATE_ARB",
        "NR_CONV_NO_BASKET_ARB",
        "N1_NEGRISK_CROSS_BOX",
        "U1_DAILY_UPDOWN_LOCK",
        "W1_SOLAR_PEAK_LOCK",
    ]
    slv_rows = []
    promoted_cnt = 0
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
        g8_prom = bool(mm.get("grad8_live_promoted") or m.get("grad8_live_promoted") or (c_n >= 8 and l_n == 0 and float(m.get("realized_pnl_t1000_usd", 0.0) or 0.0) > 0))
        if g8_prom:
            promoted_cnt += 1
        is_v3 = slv in frontier_v3_grad8
        is_bridged = (slv in live_bridged_sleeves) and (l_n == 0 or g8_prom)
        is_live_slv = bool(g8_prom or is_bridged)
        if g8_prom:
            grad_lbl = f"LIVE 8/8 ({w_n}/0)"
            tier_tag = "PROMOTED"
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
            "t1000_pnl_usd": round(float(m.get("realized_pnl_t1000_usd", 0.0) or 0.0), 2),
            "grad8_progress": grad_lbl,
            "tier_tag": tier_tag,
            "is_live": is_live_slv,
        })
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
            "title": str(p.get("title") or "")[:48],
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
            "title": str(p.get("title") or "")[:44],
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
        "v3_armed_count": len(frontier_v3_grad8),
        "bridged_count": len(live_bridged_sleeves),
        "open_total": len(open_p),
        "pending_d1_mkr": pend_d1_mkr,
        "pending_zf_mkr": pend_zf_mkr,
        "pending_pmo": len(pmo_list),
        "closed_total": sum(int(v.get("closed", 0) or 0) for v in by_slv.values()),
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

# 5. Hyperliquid APEX v5.0 Testnet (bounded 512 KB tail read; total count fast-scanned)
j_path = root / "data/papertrade_journal.jsonl"
if j_path.exists():
    audits = []
    audit_total = 0
    cb_state = "RUNNING"
    cb_reason = ""
    hwm_nav = 609.0
    _jsz = j_path.stat().st_size
    with open(j_path, "rb") as _jf:
        if _jsz > 524288:
            while True:
                _blk = _jf.read(262144)
                if not _blk:
                    break
                audit_total += _blk.count(b'"IMPLEMENTATION_AUDIT_RECORD"')
            _jf.seek(max(0, _jsz - 524288))
            _jlines = _jf.read().decode("utf-8", errors="replace").splitlines()[1:]
        else:
            _jlines = _jf.read().decode("utf-8", errors="replace").splitlines()
    for ln in _jlines:
        if not ln.strip():
            continue
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        et = ev.get("event_type")
        pl = ev.get("payload") or {}
        if et == "CIRCUIT_BREAKER":
            cb_state = pl.get("state", cb_state)
            cb_reason = pl.get("reason", "")
        elif et == "HWM_UPDATE":
            hwm_nav = float(pl.get("hwm", hwm_nav))
        elif et == "IMPLEMENTATION_AUDIT_RECORD":
            audits.append(pl)
    if _jsz <= 524288:
        audit_total = len(audits)
    maker_n = sum(1 for x in audits if x.get("order_type") == "RESTING_ALO")
    recent_hl = []
    for x in reversed(audits[-6:]):
        recent_hl.append({
            "time_utc": x.get("timestamp_utc", ""),
            "time_et": _fmt_et(x.get("timestamp_utc"), "%H:%M:%S"),
            "symbol": x.get("symbol"),
            "side": x.get("side"),
            "order_type": x.get("order_type"),
            "px": x.get("actual_fill_price"),
            "sz": x.get("filled_size"),
            "shortfall_bps": round(float(x.get("total_shortfall_bps", 0.0)), 2),
        })
    st_path = root / "data/papertrade_state.json"
    st_obj = json.loads(st_path.read_text(encoding="utf-8")) if st_path.exists() else {}
    eq_obj = st_obj.get("equity") or {}
    acct_obj = st_obj.get("accounting_ledger") or {}
    ws_obj = st_obj.get("ws_market_cache") or {}
    sh_path = root / "data/apex/champion_challenger_shadow.json"
    sh_obj = json.loads(sh_path.read_text(encoding="utf-8")) if sh_path.exists() else {}
    sh_hist = sh_obj.get("history") or []
    latest_regime = (sh_hist[-1].get("regime") or {}).get("regime", "UNKNOWN") if sh_hist else "UNKNOWN"
    post_v51_n = sum(1 for x in audits if str(x.get("timestamp_utc", "")) >= "2026-10-29T02:06:00Z")
    out["apex_testnet"] = {
        "version": st_obj.get("version", "v5.2.0"),
        "nav_usd": round(float(eq_obj.get("current_strategy_equity") or st_obj.get("current_strategy_equity") or hwm_nav), 2),
        "reconciliation_status": acct_obj.get("reconciliation_status") or (st_obj.get("last_reconciliation") or {}).get("status") or "EXACT",
        "regime": latest_regime,
        "ws_connected": bool(ws_obj.get("connected", False)),
        "ws_msgs": int(ws_obj.get("messages_received", 0) or 0),
        "circuit_breaker": st_obj.get("circuit_breaker", cb_state),
        "halt_reason": cb_reason if cb_state != "RUNNING" else "",
        "hwm_nav_usd": round(float(eq_obj.get("historical_hwm") or st_obj.get("high_water_mark") or hwm_nav), 2),
        "canary_fills": f"{post_v51_n}/100",
        "gate2_fills": f"{audit_total}/500",
        "maker_pct": round(100.0 * maker_n / len(audits), 1) if audits else 0.0,
        "shadow_tracks": {k: round(float(v.get("nav", 1000.0)), 2) for k, v in (sh_obj.get("tracks") or {}).items()},
        "recent_fills": recent_hl,
    }
else:
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
    "verified_financial_performance": {},
    "budget_and_resources": {"daily_ai_calls": 0, "daily_ai_cost_usd": 0.0, "max_daily_ai_cost_usd": 2.50, "max_daily_ai_calls": 96},
}

# 6a. Tier-A Immutable Policy Files Check
pol_dir = root / "config/policies"
for _pf in ("PAA_MISSION.md", "PAA_AUTONOMY_POLICY.md", "PAA_RISK_POLICY.md", "PAA_DEPLOYMENT_POLICY.md", "PAA_VERIFICATION_POLICY.md"):
    _ok = (pol_dir / _pf).exists()
    paa_out["tier_a_policies"].append({"file": _pf, "present": _ok})
    if _ok:
        paa_out["tier_a_intact_count"] += 1

# 6b. Live systemd timer countdowns (`NEXT` / `LAST` microsecond timestamps)
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

# 6c. Direct read-only SQLite WAL query against `paa_tasks.db` for 0-lag live accuracy
if paa_db_p.exists():
    try:
        _conn = sqlite3.connect(f"file:{paa_db_p}?mode=ro", uri=True, timeout=3.0)
        _conn.row_factory = sqlite3.Row
        _tables = {r["name"] for r in _conn.execute("PRAGMA main.table_info(paa_tasks)").fetchall()}
        _all_tbls = {r[0] for r in _conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        # Heartbeats (with exact real-time age_sec!)
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

        # Task counts & recent tasks
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

        # Recent task events audit trail
        if "task_events" in _all_tbls:
            for r in _conn.execute("SELECT timestamp_utc, task_id, component, event_type, details_json FROM task_events ORDER BY event_id DESC LIMIT 10").fetchall():
                paa_out["recent_events"].append({
                    "ts_et": _fmt_et(r["timestamp_utc"], "%H:%M:%S"),
                    "task_id": r["task_id"] or "-",
                    "component": r["component"],
                    "event_type": r["event_type"],
                    "details": str(r["details_json"] or "")[:95],
                })

        # Tier-B Verified Facts (with live TTL countdown & stale detection!)
        if "verified_facts" in _all_tbls:
            _fresh_n, _stale_n, _contra_n = 0, 0, 0
            for idx_f, r in enumerate(_conn.execute("SELECT * FROM verified_facts ORDER BY observed_at_utc DESC LIMIT 50").fetchall()):
                _obs_u = _parse_utc_epoch(r["observed_at_utc"])
                _exp_u = _parse_utc_epoch(r["expires_at_utc"])
                _rem_s = round(_exp_u - now_probe_u, 1) if _exp_u else -1.0
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
                if idx_f < 10:
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

        # Stateless Session Runs & Context Utilization (% vs 60% ceiling)
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

        # Tier-C Research Findings & 5-Stage Evidence Ladder
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

        # Deployments & Rollbacks
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

        # Authoritative Financial Snapshot & Today's Budget Ledger
        if "financial_snapshots" in _all_tbls:
            _fs = _conn.execute("SELECT * FROM financial_snapshots ORDER BY snapshot_id DESC LIMIT 1").fetchone()
            if _fs:
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
                    "simulated_shadow_t1000_pnl_usd": round(float(_fs["simulated_shadow_t1000_pnl_usd"] or 0.0), 2),
                    "simulated_paper_oos_pnl_usd": round(float(_fs["simulated_paper_oos_pnl_usd"] or 0.0), 2),
                }
        if "budget_ledger" in _all_tbls:
            _today_utc = time.strftime("%Y-%m-%d", time.gmtime(now_probe_u))
            _br = _conn.execute(
                "SELECT COUNT(*) AS calls, COALESCE(SUM(estimated_cost_usd), 0.0) AS usd, COALESCE(SUM(input_tokens), 0) AS in_tok, COALESCE(SUM(output_tokens), 0) AS out_tok FROM budget_ledger WHERE date_utc = ? AND cost_type = 'AI_CLI_CALL'",
                (_today_utc,),
            ).fetchone()
            if _br:
                paa_out["budget_and_resources"] = {
                    "daily_ai_calls": int(_br["calls"] or 0),
                    "daily_ai_cost_usd": round(float(_br["usd"] or 0.0), 4),
                    "daily_input_tokens": int(_br["in_tok"] or 0),
                    "daily_output_tokens": int(_br["out_tok"] or 0),
                    "max_daily_ai_cost_usd": 2.50,
                    "max_daily_ai_calls": 96,
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

out["paa_autonomy"] = paa_out

print(json.dumps(out))
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>DOMINUS — 24/7 Live Quantitative Command Center</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  :root {
    --bg: #0b0f17; --panel: #131a26; --border: #233044;
    --text: #e6edf3; --muted: #8b9bb4; --green: #2ea043; --green-bright: #3fb950;
    --red: #f85149; --amber: #d29922; --blue: #58a6ff;
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; background: var(--bg); color: var(--text); }
  header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
  h1 { font-size: 18px; margin: 0; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--green-bright); box-shadow: 0 0 8px var(--green-bright); display: inline-block; }
  .sub { color: var(--muted); font-size: 12px; margin-top: 3px; }
  .spots { display: flex; gap: 12px; align-items: center; font-size: 12px; flex-wrap: wrap; }
  .spot-chip { background: #192233; border: 1px solid var(--border); border-radius: 6px; padding: 5px 10px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }
  .card .label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; }
  .card .val { font-size: 24px; font-weight: 700; margin-top: 6px; }
  .pos { color: var(--green-bright); }
  .neg { color: var(--red); }
  .warn { color: var(--amber); }
  .two-col { display: grid; grid-template-columns: 1.35fr 1fr; gap: 16px; margin-bottom: 16px; }
  .three-col { display: grid; grid-template-columns: 1fr 1.15fr 1.25fr; gap: 14px; }
  @media (max-width: 1150px) { .three-col { grid-template-columns: 1fr; } }
  @media (max-width: 1000px) { .two-col { grid-template-columns: 1fr; } }
  .ctx-bar-bg { display: inline-block; width: 72px; height: 8px; background: #1c2638; border-radius: 4px; overflow: hidden; vertical-align: middle; margin-left: 5px; border: 1px solid var(--border); }
  .ctx-bar-fg { height: 100%; background: var(--green-bright); transition: width 0.3s ease; }
  h2 { font-size: 13px; margin: 0 0 10px 0; color: var(--blue); text-transform: uppercase; letter-spacing: 0.5px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 600; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap; }
  .pill-ok { background: rgba(46,160,67,0.2); color: var(--green-bright); border: 1px solid rgba(63,185,80,0.4); }
  .pill-bad { background: rgba(248,81,73,0.2); color: var(--red); border: 1px solid rgba(248,81,73,0.4); }
  .pill-warn { background: rgba(210,153,34,0.2); color: var(--amber); border: 1px solid rgba(210,153,34,0.45); }
  .pill-info { background: rgba(88,166,255,0.16); color: var(--blue); border: 1px solid rgba(88,166,255,0.38); }
  .pill-muted { background: rgba(139,155,180,0.14); color: var(--muted); border: 1px solid rgba(139,155,180,0.3); }
  .flt-btn { background: #192233; color: var(--muted); border: 1px solid var(--border); padding: 4px 10px; font-size: 11px; border-radius: 6px; cursor: pointer; }
  .flt-btn.active { background: #1f6feb; color: #fff; border-color: #388bfd; }
  .sf-strip { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; font-size: 11.5px; }
  .sf-chip { background: #0e1420; border: 1px solid var(--border); border-radius: 6px; padding: 5px 10px; }
  button { background: #1f6feb; color: #fff; border: none; border-radius: 6px; padding: 7px 13px; cursor: pointer; font-weight: 600; font-size: 12px; }
  button:hover { background: #388bfd; }
  .svc-wrap { display: flex; flex-wrap: wrap; gap: 6px; }
  .log-box { font-size: 11.5px; color: #b6c2d4; line-height: 1.5; max-height: 150px; overflow-y: auto; background: #0e1420; padding: 10px; border-radius: 6px; border: 1px solid var(--border); }
</style>
</head>
<body>
<header>
  <div>
    <h1><span class="dot" id="live_dot"></span> DOMINUS — 24/7 QUANTITATIVE COMMAND CENTER</h1>
    <div class="sub" id="meta">Connecting to kraken-finland over zero-RAM SSH pipe...</div>
  </div>
  <div class="spots" id="spots"></div>
  <div>
    <button onclick="refreshNow(true)">Refresh Now</button>
  </div>
</header>

<div class="grid" id="kpis"></div>

<div class="card" style="margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <h2 style="margin:0;">Consolidated v5.1 Daemon Fleet, Multiplexed SHM Feeds &amp; D1 Overlap Window</h2>
    <div class="sub" id="d1_timer" style="margin:0;color:var(--amber);font-weight:600;"></div>
  </div>
  <div class="svc-wrap" id="svcs"></div>
</div>

<div class="card" style="margin-bottom:16px;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <div>
      <h2 style="margin:0;">Shock &amp; Order Attempt Forensics &mdash; Speed vs Gate Attribution</h2>
      <div class="sub" style="margin-top:2px;">Explicitly separates <b>Too Slow (Flight / MM Beat Shock / Feed Lag)</b> &amp; <b>Maker Left Behind</b> from <b>Already Priced In</b>, <b>Shield Saves</b> &amp; <b>WFO Alpha Vetoes</b></div>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;">
      <button class="flt-btn active" id="sf_flt_meaningful" onclick="setSfFilter('meaningful')">Meaningful</button>
      <button class="flt-btn" id="sf_flt_attempts" onclick="setSfFilter('attempts')">Order Attempts Only</button>
      <button class="flt-btn" id="sf_flt_slow" onclick="setSfFilter('slow')">Too Slow / Left Behind</button>
      <button class="flt-btn" id="sf_flt_all" onclick="setSfFilter('all')">All Shocks</button>
    </div>
  </div>
  <div class="sf-strip" id="sf_summary"></div>
  <div style="max-height:310px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
    <table>
      <thead><tr><th>Ottawa (ET)</th><th>Market / Shock</th><th>Path</th><th>Attribution Verdict</th><th>Quote Drift (t0 &rarr; Eval &rarr; Post)</th><th>Stage Latency (ms)</th><th>Why / Root-Cause Diagnosis</th></tr></thead>
      <tbody id="sf_rows"></tbody>
    </table>
  </div>
</div>

<div class="card" style="margin-bottom:16px;border-color:#2f4668;">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">
    <div>
      <h2 style="margin:0;">PAA Autonomous Operating System &amp; Zero-Trust Verification Center</h2>
      <div class="sub" style="margin-top:2px;">Stateless Short-Lived AI Sessions (60% Context Cap) &bull; Tier-A/B/C Separated Memory &bull; 5-Gate Non-AI Verification Controller (<code>NO EVIDENCE = NO VERIFIED CLAIM</code>)</div>
    </div>
    <div class="sub" id="paa_live_pulse" style="margin:0;color:var(--green-bright);font-weight:600;"></div>
  </div>
  <div class="sf-strip" id="paa_strip"></div>
  <div class="three-col">
    <div>
      <h2 style="margin-top:4px;">Live Schedules &amp; Heartbeats (1s Tick)</h2>
      <div style="max-height:245px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>Cadence Unit</th><th>Last (ET)</th><th>Age</th><th>Next Fire</th></tr></thead>
          <tbody id="paa_timers"></tbody>
        </table>
      </div>
      <h2 style="margin-top:10px;">Recent Releases &amp; Rollbacks</h2>
      <div style="max-height:130px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>Release</th><th>SHA</th><th>Gates</th><th>State</th></tr></thead>
          <tbody id="paa_deploys"></tbody>
        </table>
      </div>
    </div>
    <div>
      <h2 style="margin-top:4px;">Tier-B Verified Facts (Live TTL Revalidation)</h2>
      <div style="max-height:245px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>Fact Key</th><th>Value</th><th>Status</th><th>TTL Left</th></tr></thead>
          <tbody id="paa_facts"></tbody>
        </table>
      </div>
      <h2 style="margin-top:10px;">Stateless AI Sessions (&le;60% Context Cap)</h2>
      <div style="max-height:130px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
        <table>
          <thead><tr><th>ET</th><th>Stage Role</th><th>Fresh</th><th>Ctx %</th></tr></thead>
          <tbody id="paa_sessions"></tbody>
        </table>
      </div>
    </div>
    <div>
      <h2 style="margin-top:4px;">Durable Zero-Trust Tasks &amp; 5-Stage Ladder</h2>
      <div id="paa_ladder" style="font-size:11.5px;margin-bottom:6px;"></div>
      <div style="max-height:215px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
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

<div class="two-col">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <h2 id="pm_harvester_hdr">Polymarket v5.4.1 Live Harvester &amp; Hot-Reload Strategy W/L</h2>
      <svg id="spark" width="160" height="32"></svg>
    </div>
    <div id="active_box" style="margin-bottom:10px;font-size:12px;"></div>
    <h2 style="margin-top:8px;">Real-Money Live Strategy Breakdown (Wallet-Reconciled W/L)</h2>
    <table>
      <thead><tr><th>Strategy Sleeve</th><th>Live Routing / Gate</th><th>Open</th><th>Today W/L</th><th>Today PnL</th><th>All-Time W/L</th><th>All-Time PnL</th></tr></thead>
      <tbody id="pm_strats"></tbody>
    </table>
    <h2 style="margin-top:14px;">Recent Real-Money Closed Trades</h2>
    <table>
      <thead><tr><th>Ottawa (ET)</th><th>Market</th><th>Sleeve</th><th>In &rarr; Out</th><th>Notional</th><th>Real PnL</th><th>Exit</th></tr></thead>
      <tbody id="pm_trades"></tbody>
    </table>
    <h2 style="margin-top:16px;">Live Execution Event Stream</h2>
    <div class="log-box" id="log_events"></div>
  </div>
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
      <h2>Alpha-124 Riskless Frontier v1 / v2 / v3 &amp; _grad8 Matrix</h2>
      <span class="sub" id="a124_sync"></span>
    </div>
    <div style="max-height:340px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead><tr><th>Sleeve</th><th>Open</th><th>W / L</th><th>Gate / Grad8</th><th>T1000 PnL</th></tr></thead>
        <tbody id="a124_sleeves"></tbody>
      </table>
    </div>
    <h2 style="margin-top:14px;">Open Shadow Structural Trades (<span id="a124_open_cnt">0</span> Active)</h2>
    <div style="max-height:220px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead><tr><th>Sleeve</th><th>Market</th><th>Cost</th><th>Bid</th><th>TTE</th></tr></thead>
        <tbody id="a124_open"></tbody>
      </table>
    </div>
    <h2 style="margin-top:14px;">Recent Closed Shadow Trades (Alpha-124 Riskless + Directional OOS)</h2>
    <div id="dir_shdw_meta" style="font-size:11.5px;color:var(--muted);margin-bottom:6px;"></div>
    <div style="max-height:220px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;">
      <table>
        <thead><tr><th>Closed (ET)</th><th>Sleeve</th><th>Market</th><th>In&rarr;Out</th><th>T100 / T1000</th></tr></thead>
        <tbody id="a124_closed"></tbody>
      </table>
    </div>
    <h2 style="margin-top:16px;" id="apex_hdr">Hyperliquid APEX (Testnet — $0 Mainnet, 4H Rebalance)</h2>
    <div id="apex_meta" style="font-size:12px;margin-bottom:8px;"></div>
    <table>
      <thead><tr><th>Ottawa (ET)</th><th>Asset</th><th>Side</th><th>Type</th><th>Shortfall</th></tr></thead>
      <tbody id="apex_fills"></tbody>
    </table>
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
    .replace('_INGAME_MILESTONE_IRREVERSIBLE_LOCK', '_INGAME_LOCK');
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
    el.textContent = `D1 15m/5m Same-Oracle Overlap ACTIVE NOW (${rem}s remaining)`;
  } else {
    const wait = secIn15m < 600 ? (600 - secIn15m) : (900 - secIn15m + 600);
    const m = Math.floor(wait / 60), s = wait % 60;
    el.style.color = '#d29922';
    el.textContent = `Next D1 Same-Oracle Overlap Window in ${m}m ${s}s`;
  }
}
setInterval(updateD1Countdown, 1000);

function drawSpark(pts) {
  const svg = document.getElementById('spark');
  if (!svg || !pts || pts.length < 2) return;
  const mn = Math.min(...pts), mx = Math.max(...pts);
  const rng = Math.max(0.01, mx - mn);
  const w = 156, h = 26;
  const coords = pts.map((v, i) => {
    const x = 2 + (i / (pts.length - 1)) * w;
    const y = 3 + h - ((v - mn) / rng) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  svg.innerHTML = `<polyline fill="none" stroke="#3fb950" stroke-width="2" points="${coords}"/>`;
}

let _inFlight = false;
let _sfFilter = 'meaningful';
let _lastSfData = null;
let _lastPaaData = null;
let _lastSyncClientMs = 0;
let _pollSeq = 0;
let _lastMetaPrefix = '';

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
    stripEl.innerHTML =
      `<span class="sf-chip">Director: <b class="${dirHb.status === 'OK' || dirHb.status === 'RUNNING_CYCLE' ? 'pos' : 'warn'}">${esc(dirHb.status || 'INIT')}</b> (#${dirHb.cycle_count ?? 0}, ${fmtSecCompact(dirAge)})</span>` +
      `<span class="sf-chip">1m Monitor: <b class="${monHb.status === 'OK' ? 'pos' : 'warn'}">${esc(monHb.status || 'INIT')}</b> (${fmtSecCompact(monAge)}) &bull; 2m Sup: <b>${fmtSecCompact(supAge)}</b></span>` +
      `<span class="sf-chip">Safeguards: <b class="${stopOk ? 'pos' : 'neg'}">${paa.master_stop_engaged ? 'MASTER STOP' : (paa.accounting_safeguard_active ? 'ACCT FREEZE' : 'CLEAR')}</b></span>` +
      `<span class="sf-chip">Tier-A Policies: <b class="${(paa.tier_a_intact_count || 0) >= 5 ? 'pos' : 'neg'}">${paa.tier_a_intact_count ?? 0}/5 IMMUTABLE</b></span>` +
      `<span class="sf-chip">Tier-B Facts: <b class="pos">${zt.verified_facts_fresh ?? 0} Fresh</b> &bull; <span class="warn">${zt.verified_facts_stale ?? 0} Stale</span> &bull; <b class="${(zt.verified_facts_contradicted || 0) > 0 ? 'neg' : 'sub'}">${zt.verified_facts_contradicted ?? 0} Contradicted</b></span>` +
      `<span class="sf-chip">Stateless Sessions: <b class="pos">${zt.fresh_session_pct ?? 100}% Fresh</b> (N=${zt.sessions_total ?? 0}) &bull; Peak Ctx <b>${maxCtx.toFixed(1)}%</b>/${ctxCap}%<span class="ctx-bar-bg"><span class="ctx-bar-fg" style="width:${ctxFillW}%;background:${ctxColor};"></span></span></span>` +
      `<span class="sf-chip">Tasks: <b class="pos">${verDone} Verified</b> &bull; <span class="warn">${runCnt} Queue/Run</span> &bull; <b>${pendVer} PendVerif</b> &bull; <span class="${rejCnt ? 'neg' : 'sub'}">${rejCnt} Rej</span> &bull; <span class="${blkCnt ? 'warn' : 'sub'}">${blkCnt} Blocked</span></span>` +
      `<span class="sf-chip">AI Spend Today: <b>$${Number(br.daily_ai_cost_usd || 0).toFixed(4)}</b> / $${Number(br.max_daily_ai_cost_usd || 2.5).toFixed(2)} (${br.daily_ai_calls ?? 0}/${br.max_daily_ai_calls ?? 96} calls)</span>` +
      `<span class="sf-chip">Reconciled Cash vs Sim: <b>$${Number(vf.free_cash_pusd || 0).toFixed(2)} pUSD</b> (Realized <b class="${Number(vf.realized_onchain_net_pnl_usd || 0) >= 0 ? 'pos' : 'neg'}">${Number(vf.realized_onchain_net_pnl_usd || 0) >= 0 ? '+' : ''}$${Number(vf.realized_onchain_net_pnl_usd || 0).toFixed(2)}</b> vs Sim Shadow +$${Number(vf.simulated_shadow_t1000_pnl_usd || 0).toFixed(0)} <i>non-cash</i>)</span>`;
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
    sub = ` <span class="${d > 0 ? 'neg' : 'pos'}">(${d > 0 ? '+' : ''}${d.toFixed(1)}c flight)</span>`;
  } else if (r.ask_drift_pre_c !== null && r.ask_drift_pre_c !== undefined && Math.abs(Number(r.ask_drift_pre_c)) >= 0.5) {
    const d = Number(r.ask_drift_pre_c);
    sub = ` <span class="${d > 0 ? 'warn' : 'pos'}">(${d > 0 ? '+' : ''}${d.toFixed(1)}c pre)</span>`;
  } else if (r.cap_px !== null && r.cap_px !== undefined && !r.is_order_attempt) {
    sub = ` <span class="sub">(cap $${Number(r.cap_px).toFixed(2)})</span>`;
  }
  return (parts.length ? parts.join(' &rarr; ') : '<span class="sub">-</span>') + sub;
}

function fmtStageLat(r) {
  const b = [];
  if (r.exch_lag_ms !== null && r.exch_lag_ms !== undefined) b.push(`Ex:${Number(r.exch_lag_ms).toFixed(0)}`);
  if (r.ipc_ms !== null && r.ipc_ms !== undefined) b.push(`IPC:${Number(r.ipc_ms).toFixed(1)}`);
  if (r.book_age_ms !== null && r.book_age_ms !== undefined && Number(r.book_age_ms) < 9000) b.push(`Bk:${Number(r.book_age_ms).toFixed(0)}`);
  if (r.sign_ms !== null && r.sign_ms !== undefined) b.push(`Sg:${Number(r.sign_ms).toFixed(2)}${r.presign_hit ? '*' : ''}`);
  if (r.http_ms !== null && r.http_ms !== undefined) b.push(`<b>HTTP:${Number(r.http_ms).toFixed(0)}</b>`);
  if (r.ttl_ms !== null && r.ttl_ms !== undefined) b.push(`TTL:${(Number(r.ttl_ms)/1000).toFixed(1)}s`);
  return b.length ? b.join(' &bull; ') : '<span class="sub">-</span>';
}

function renderShockForensics(sf) {
  _lastSfData = sf || {};
  const s = _lastSfData.summary || {};
  const allRows = _lastSfData.rows || [];
  const sumEl = document.getElementById('sf_summary');
  if (sumEl) {
    const medIpc = s.med_ipc_ms !== null && s.med_ipc_ms !== undefined ? `${s.med_ipc_ms}ms` : '-';
    const medSgn = s.med_sign_ms !== null && s.med_sign_ms !== undefined ? `${s.med_sign_ms}ms` : '-';
    const medHtp = s.med_http_ms !== null && s.med_http_ms !== undefined ? `${s.med_http_ms}ms` : '-';
    const slowCls = (s.speed_misses || 0) > 0 ? 'neg' : 'pos';
    const liveAge = s.last_shock_age_s !== null && s.last_shock_age_s !== undefined ? `${s.last_shock_age_s}s ago` : 'waiting';
    sumEl.innerHTML = `
      <span class="sf-chip"><span class="pos">&#9679; LIVE STREAM</span> (Last shock: <b>${esc(liveAge)}</b>)</span>
      <span class="sf-chip">Order Attempts: <b>${s.attempts ?? 0}</b> (<span class="pos">${s.filled ?? 0} Filled</span>, ${s.maker_quiet ?? 0} Quiet TTL)</span>
      <span class="sf-chip">Too Slow / Speed Misses: <b class="${slowCls}">${s.speed_misses ?? 0}</b> (Flight 0-Fill: <b>${s.flight_kills ?? 0}</b> &bull; Pre-Eval MM Beat: <b>${s.pre_eval_repriced ?? 0}</b> &bull; Maker Left Behind: <b>${s.maker_left_behind ?? 0}</b> &bull; Feed/WS Lag: <b>${s.feed_lags ?? 0}</b>)</span>
      <span class="sf-chip">Shield Saved: <b class="pos">${s.shield_saves ?? 0}</b> &bull; Already Priced In (Not Slow): <b style="color:var(--blue);">${s.already_priced ?? 0}</b>${s.settled_99c ? ` <span class="sub">(${s.settled_99c} Settled 99c+)</span>` : ''} &bull; WFO/Alpha Vetoes: <b>${s.alpha_vetoes ?? 0}</b></span>
      <span class="sf-chip">Median Hot Path: IPC <b>${medIpc}</b> &bull; Sign <b>${medSgn}</b> &bull; CLOB HTTP <b>${medHtp}</b></span>
    `;
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
    tb.innerHTML = `<tr><td colspan="7" class="sub">No events match filter "${esc(_sfFilter)}" in recent window. Click "All Shocks" or "Meaningful" to inspect all evaluated triggers.</td></tr>`;
    return;
  }
  tb.innerHTML = rows.slice(0, 32).map(r => {
    const ts = r.ts_et || fmtOttawa(r.unix_ts || r.ts_utc, 'md_hms');
    const mkt = `${r.asset || '?'} ${r.horizon || ''} ${r.side || ''}`.trim();
    const subBits = [];
    if (r.dist_pct !== null && r.dist_pct !== undefined) subBits.push(`${Number(r.dist_pct) >= 0 ? '+' : ''}${Number(r.dist_pct).toFixed(2)}%`);
    if (r.tte_s !== null && r.tte_s !== undefined) subBits.push(`TTE ${Math.round(Number(r.tte_s))}s`);
    const subMkt = subBits.length ? `<div class="sub">${esc(subBits.join(' | '))}</div>` : '';
    const pLbl = String(r.path_type || 'PRE_EVAL').replace('MAKER_P3A', 'P3A MAKER').replace('TAKER_FOK', 'TAKER FOK').replace('MAKER_BOX', 'BOX MAKER');
    return `<tr>
      <td style="white-space:nowrap;">${esc(ts)}</td>
      <td><b>${esc(mkt)}</b>${subMkt}</td>
      <td><code>${esc(pLbl)}</code></td>
      <td><span class="pill ${sfPillClass(r.speed_verdict)}">${esc(r.badge || r.speed_verdict)}</span></td>
      <td style="white-space:nowrap;">${fmtPxDrift(r)}</td>
      <td style="white-space:nowrap;font-size:11px;">${fmtStageLat(r)}</td>
      <td>${esc(r.diagnosis || '')}</td>
    </tr>`;
  }).join('');
}
async function refreshNow(force=false) {
  if (_inFlight && !force) return;
  _inFlight = true;
  const btn = document.querySelector('header button');
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
    const pm = d.polymarket_live || {};
    const mem = d.mem_mb || {};
    const la = d.load_avg || [0,0,0];
    const ap = d.apex_testnet || {};
    const a124 = d.alpha124 || {};
    const ds = d.directional_shadow || {};
    const scfg = d.strategy_config || {};
    const dcfg = scfg.directional || {};
    const stcfg = scfg.sizing_tiers || {};
    const rcfg = scfg.risk_controller || {};
    const bcfg = scfg.riskless_boxes || {};
    const cfgVer = scfg.schema_version || '5.4.1';
    const syncEt = d.fetched_at_et || fmtOttawa(d.unix_ts || d.fetched_at_utc, 'full');
    _pollSeq += 1;
    _lastSyncClientMs = Date.now();
    _lastMetaPrefix = `Synced: ${syncEt} (Ottawa) | Schema v${cfgVer} Hot-Reload | Load: ${la[0]} (${la[1]}, ${la[2]}) | RAM Avail: ${mem.available || '?'} / ${mem.total || '?'} MB`;
    document.getElementById('meta').textContent = `${_lastMetaPrefix} | Live Poll #${_pollSeq} (0s ago)`;
    _lastPaaData = d.paa_autonomy || null;
    if (_lastPaaData) renderPaaAutonomy(_lastPaaData, 0);
    const pmHdr = document.getElementById('pm_harvester_hdr');
    if (pmHdr) pmHdr.textContent = `Polymarket v${cfgVer} Live Harvester & Hot-Reload Strategy W/L`;

    const spots = Object.assign({}, a124.spots || {}, d.shm_spots || {});
    const shmAnc = d.shm_anchored || {};
    document.getElementById('spots').innerHTML = ['BTC', 'SOL', 'ETH', 'XAU'].filter(k => spots[k] !== undefined).map(k => {
      const ancTag = shmAnc[k] ? ' <span class="pos" title="Chainlink Basis Anchored">CL</span>' : '';
      const pausedTag = (dcfg.paused_directional_assets || []).includes(k) ? ' <span class="warn" title="Live Directional Paused (Shadow Only)">SHDW</span>' : '';
      return `<span class="spot-chip"><b>${esc(k)}</b> $${spots[k]}${ancTag}${pausedTag}</span>`;
    }).join('');

    const pnlCls = (pm.epoch_net_pnl_usd || 0) >= 0 ? 'pos' : 'neg';
    const v51Pnl = Number(pm.v51_net_pnl_usd ?? 0);
    const v51Cls = v51Pnl >= 0 ? 'pos' : 'neg';
    const v51Tot = (pm.v51_wins || 0) + (pm.v51_losses || 0);
    const v51Wr = v51Tot ? ((100 * (pm.v51_wins || 0) / v51Tot).toFixed(0) + '%') : 'ARMED';
    const wr = pm.epoch_closed_count ? ((100 * pm.epoch_wins / pm.epoch_closed_count).toFixed(1) + '%') : 'N/A';
    const apVer = ap.version || 'v5.2.0';
    const eqNow = Number(pm.equity_usd ?? 0);
    const dirSlotsCfg = eqNow >= Number(stcfg.growth_max_equity || 1000) ? (stcfg.dir_slots_scale || 4)
      : eqNow >= Number(stcfg.recovery_max_equity || 250) ? (stcfg.dir_slots_growth || 4)
      : eqNow >= Number(stcfg.seed_survival_max_equity || 100) ? (stcfg.dir_slots_recovery || 3)
      : (stcfg.dir_slots_seed || 2);
    const kellyF = eqNow >= Number(stcfg.seed_survival_max_equity || 100) ? (stcfg.kelly_fraction_recovery || 0.45) : (stcfg.kelly_fraction_seed || 0.48);
    const boxSlots = Number(bcfg.max_concurrent_riskless_boxes || 6);
    const dailyCap = Number(rcfg.max_daily_directional_loss_usd || 16.57);
    const ruinFloor = Number(rcfg.hard_ruin_floor_usd || 42.0);
    const slotDesc = `${kellyF}x Kelly | ${dirSlotsCfg} Dir + ${boxSlots} Box`;
    const redeemEq = Number(pm.guaranteed_redemption_equity_usd ?? eqNow);
    const mtmBidEq = Number(pm.mtm_bid_equity_usd ?? eqNow);
    const tpTgtEq = Number(pm.tp_target_equity_usd ?? eqNow);
    const quoteCash = Number(pm.quoting_cash_usd ?? 0);
    const freeCash = Number(pm.free_cash_usd ?? pm.bankroll_usd ?? 0);
    const openCnt = (pm.active_positions || []).length;
    const cashSubTag = quoteCash > 0.01 ? ` <span class="sub" style="font-size:12px;">(Free $${freeCash.toFixed(2)} | Quoting $${quoteCash.toFixed(2)})</span>` : '';
    const eqBreakdown = openCnt > 0
      ? (redeemEq > eqNow + 0.05
          ? `Book: $${eqNow.toFixed(2)} (Redeem &ge;$${redeemEq.toFixed(2)})`
          : `MTM Bid: <b>$${mtmBidEq.toFixed(2)}</b> &bull; @TP: <b>$${tpTgtEq.toFixed(2)}</b> &bull; Book: $${eqNow.toFixed(2)}`)
      : `Equity: $${eqNow.toFixed(2)}`;
    const xauSh = ds.xau_15m || {};
    document.getElementById('kpis').innerHTML = `
      <div class="card"><div class="label">Polymarket Live Cash</div><div class="val pos">$${(pm.bankroll_usd ?? 0).toFixed(2)}${cashSubTag}</div><div class="sub">${eqBreakdown} | ${esc(pm.tier || '-')} (${slotDesc})</div></div>
      <div class="card"><div class="label">v${esc(cfgVer)} Live (${esc(pm.today_et_date || pm.today_utc_date || 'ET')} Ottawa)</div><div class="val ${v51Cls}">${pm.v51_wins ?? 0}W / ${pm.v51_losses ?? 0}L (${v51Wr})</div><div class="sub">Session Net: <b class="${v51Cls}">${v51Pnl >= 0 ? '+' : ''}$${v51Pnl.toFixed(2)}</b> | Stop: $${Number(pm.daily_realized_loss_usd || 0).toFixed(2)}/$${dailyCap.toFixed(2)} (Floor $${ruinFloor.toFixed(0)}) | Open: <b>${openCnt}</b></div></div>
      <div class="card"><div class="label">All-Time Epoch Real W/L</div><div class="val">${pm.epoch_wins ?? 0}W / ${pm.epoch_losses ?? 0}L (${wr})</div><div class="sub">Epoch Net: <span class="${pnlCls}">${(pm.epoch_net_pnl_usd ?? 0) >= 0 ? '+' : ''}$${(pm.epoch_net_pnl_usd ?? 0).toFixed(2)}</span> | Fees: $${(pm.epoch_fees_usd ?? 0).toFixed(2)} | Live Quotes: <b>${pm.live_maker_posts_tail ?? 0}</b></div></div>
      <div class="card"><div class="label">Riskless _grad8 &amp; Shadow</div><div class="val pos">${a124.promoted_count ?? 0} Live 8/8 &bull; ${a124.v3_armed_count ?? 6} V3</div><div class="sub">Open Shadow Boxes: <b>${a124.open_total ?? 0}</b> | Closed Shadow: <b>${a124.closed_total ?? 0}</b></div></div>
      <div class="card"><div class="label">Directional &amp; XAU Shadow</div><div class="val pos">$${Number(ds.oos_equity_usd || 1000).toFixed(0)}</div><div class="sub">${ds.oos_wins ?? 0}W/${ds.oos_losses ?? 0}L (${ds.oos_wr_pct ?? 0}%) | XAU 15m: <b>${(xauSh.wins || 0) + (xauSh.losses || 0)}/40</b> (${esc(xauSh.status || 'IDLE')})</div></div>
      <div class="card"><div class="label">APEX ${esc(apVer)} &amp; VM</div><div class="val ${ap.circuit_breaker === 'RUNNING' ? 'pos' : 'neg'}">$${Number(ap.nav_usd || 0).toFixed(2)}</div><div class="sub">Load ${la[0]} (${mem.available || 0}MB free) | Halt: <b class="${pm.risk_halt ? 'neg' : 'pos'}">${pm.risk_halt ? 'HALTED' : 'CLEAR'}</b></div></div>
    `;

    drawSpark(pm.equity_curve || []);

    const svcs = d.services || {};
    const shmAges = d.shm_fast_tick_age_sec || {};
    const svcPills = Object.entries(svcs).map(([k, v]) =>
      `<span class="pill ${v === 'active' ? 'pill-ok' : 'pill-bad'}">${esc(k)}: ${esc(v)}</span>`
    );
    const shmPills = Object.entries(shmAges).map(([sym, age]) => {
      const ok = age !== null && age !== undefined && Number(age) < 10.0;
      const lbl = age !== null && age !== undefined ? `${Number(age).toFixed(2)}s` : 'down';
      return `<span class="pill ${ok ? 'pill-ok' : 'pill-bad'}">SHM ${esc(sym)}: ${lbl}</span>`;
    });
    document.getElementById('svcs').innerHTML = svcPills.concat(shmPills).join('');

    const acts = pm.active_positions || [];
    const liveAssets1h = (dcfg.allowed_assets_1h || ['BTC', 'ETH', 'SOL']).join('/');
    const pausedDir = (dcfg.paused_directional_assets || ['XRP']).join('/');
    const exitPol = (scfg.exit_supervisor || {}).policy || 'ev_terminal_twap_t5';
    const mk1hOn = Boolean(dcfg.enable_1h_shielded_maker);
    const mk15On = Boolean(dcfg.enable_15m_subordinate_maker);
    const t15Lo = Math.round(Number(dcfg.min_tte_15m_taker_sec || 120));
    const t15Hi = Math.round(Number(dcfg.max_tte_15m_taker_sec || 510));
    const z1h = Number(dcfg.min_z_1h_regime_b || dcfg.min_z_1h || 1.00).toFixed(2);
    const h1Desc = mk1hOn
      ? `1h Taker/Maker (&le;$${Number(dcfg.max_taker_price_1h || 0.81).toFixed(2)}/&le;$${Number(dcfg.max_maker_price_1h || 0.76).toFixed(2)})`
      : `1h Taker-Only [150-900s &le;$${Number(dcfg.max_taker_price_1h || 0.81).toFixed(2)}, Z&ge;${z1h}]`;
    const m15Desc = dcfg.enable_15m_taker
      ? (mk15On ? `15m Taker [${t15Lo}-${t15Hi}s &le;$${Number(dcfg.max_taker_price_15m || 0.78).toFixed(2)}] + Maker` : `15m Taker-Only [${t15Lo}-${t15Hi}s &le;$${Number(dcfg.max_taker_price_15m || 0.78).toFixed(2)}, Z&ge;${Number(dcfg.min_z_15m_taker || 1.20).toFixed(2)}]`)
      : `15m Maker-Only (&le;$${Number(dcfg.max_maker_price_15m || 0.72).toFixed(2)})`;
    document.getElementById('active_box').innerHTML = acts.length === 0
      ? `<span class="sub">Active live positions: <b>0</b> &mdash; <b>v${esc(cfgVer)} Armed</b>: <code>${esc(liveAssets1h)}</code> ${h1Desc} + ${m15Desc} + <code>${esc(exitPol)}</code> ($0.93 MFE Lock) | <code>${esc(pausedDir)}</code> Dir Paused (Shadow) | BOND1/COND1/D1/CM_B3 Boxes Live</span>`
      : `<div style="margin-bottom:4px;"><b>LIVE OPEN POSITIONS (${acts.length} Active &mdash; Cost Basis $${acts.reduce((s, x) => s + Number(x.notional_usd || 0), 0).toFixed(2)} &bull; Live Bid Value $${acts.reduce((s, x) => s + Number(x.mtm_bid_usd || 0), 0).toFixed(2)} &bull; @Resting TP $${acts.reduce((s, x) => s + Number(x.tp_val_usd || 0), 0).toFixed(2)}):</b></div>
         <table><thead><tr><th>Market</th><th>Side / Shares</th><th>Entry / Cost</th><th>Live Bid / Ask</th><th>Resting Exit</th><th>MTM Bid (uPnL)</th></tr></thead><tbody>` +
        acts.map(a => {
          const nm = a.title ? a.title : `${a.asset || ''} ${a.horizon || ''}`.trim();
          const upnl = Number(a.unreal_bid_pnl_usd || 0);
          const uCls = upnl >= 0 ? 'pos' : 'neg';
          const ba = (a.best_bid !== null && a.best_bid !== undefined) ? `$${Number(a.best_bid).toFixed(2)} / $${Number(a.best_ask ?? 1).toFixed(2)}` : '-';
          return `<tr>
            <td><b>${esc(nm)}</b><div class="sub">${esc(shortSlv(a.sleeve))} &bull; Mkt ${esc(a.market_id || '')}</div></td>
            <td><b class="pos">${esc(a.side)}</b> &times; ${Number(a.shares || 0).toFixed(2)}</td>
            <td>$${Number(a.entry_px || 0).toFixed(4)} ($${Number(a.notional_usd || 0).toFixed(2)})</td>
            <td>${ba}</td>
            <td>SELL @ <b>$${Number(a.target_tp || 0).toFixed(2)}</b> ($${Number(a.tp_val_usd || 0).toFixed(2)}) [${esc(a.status)}]</td>
            <td><b>$${Number(a.mtm_bid_usd || 0).toFixed(2)}</b> <span class="${uCls}">(${upnl >= 0 ? '+' : ''}$${upnl.toFixed(2)})</span></td>
          </tr>`;
        }).join('') + `</tbody></table>`;

    document.getElementById('pm_strats').innerHTML = (pm.live_strategies || []).map(st => {
      const vp = Number(st.v51_pnl || 0), ep = Number(st.epoch_pnl || 0);
      return `<tr>
        <td><b>${esc(shortSlv(st.sleeve))}</b></td>
        <td class="sub">${esc(st.desc || '')}</td>
        <td>${st.open || 0}</td>
        <td><b>${st.v51_w || 0}W / ${st.v51_l || 0}L</b></td>
        <td class="${vp >= 0 ? 'pos' : 'neg'}">${vp >= 0 ? '+' : ''}$${vp.toFixed(2)}</td>
        <td>${st.epoch_w || 0}W / ${st.epoch_l || 0}L</td>
        <td class="${ep >= 0 ? 'pos' : 'neg'}">${ep >= 0 ? '+' : ''}$${ep.toFixed(2)}</td>
      </tr>`;
    }).join('');

    document.getElementById('pm_trades').innerHTML = (pm.recent_closed || []).map(c => {
      const recBadge = c.fee_reconciled ? ` <span class="sub" title="On-chain wallet +$${Number(c.net_pnl_usd).toFixed(2)} (raw JSON $${Number(c.raw_pnl_usd).toFixed(2)} pre-fix est fee)">*wallet</span>` : '';
      const tsClosed = c.time_et || fmtOttawa(c.unix_ts || c.time_utc, 'md_hms');
      return `
      <tr>
        <td style="white-space:nowrap;">${esc(tsClosed)}</td>
        <td><b>${esc(c.asset)}</b></td>
        <td class="sub">${esc(shortSlv(c.sleeve || '').slice(0, 18))}</td>
        <td>${esc(c.entry_px)} &rarr; ${esc(c.exit_px)}</td>
        <td>$${Number(c.notional_usd || 0).toFixed(2)}</td>
        <td class="${c.net_pnl_usd >= 0 ? 'pos' : 'neg'}"><b>${c.net_pnl_usd >= 0 ? '+' : ''}$${Number(c.net_pnl_usd || 0).toFixed(2)}</b>${recBadge}</td>
        <td>${esc((c.reason || '').slice(0, 28))}</td>
      </tr>`;
    }).join('');

    document.getElementById('log_events').innerHTML = (d.live_log_events || []).map(l =>
      `<div>${esc(l)}</div>`
    ).join('') || '<div class="sub">No recent log events.</div>';

    renderShockForensics(d.shock_forensics || {});

    const syncEl = document.getElementById('a124_sync');
    if (syncEl) {
      syncEl.textContent = `Age: ${a124.state_age_sec ?? '?'}s | Resting Shadow Quotes: ${(a124.pending_d1_mkr || 0) + (a124.pending_zf_mkr || 0) + (a124.pending_pmo || 0)}`;
    }
    const ocEl = document.getElementById('a124_open_cnt');
    if (ocEl) ocEl.textContent = String(a124.open_total ?? 0);

    document.getElementById('a124_sleeves').innerHTML = (a124.sleeves || []).map(s => {
      const qBadge = s.pending_quotes ? ` <span class="warn">(${s.pending_quotes}q)</span>` : '';
      const gCls = s.tier_tag === 'PROMOTED' ? 'pos' : (s.tier_tag === 'V3_AUTO_G8' ? 'warn' : (s.is_live ? 'pos' : 'sub'));
      return `
      <tr>
        <td><b>${esc(shortSlv(s.sleeve))}</b>${qBadge}</td>
        <td>${esc(s.open)}</td>
        <td>${esc(s.wins)}W / ${esc(s.losses)}L</td>
        <td class="${gCls}"><b>${esc(s.grad8_progress)}</b></td>
        <td class="${s.t1000_pnl_usd >= 0 ? 'pos' : 'neg'}">${s.t1000_pnl_usd >= 0 ? '+' : ''}$${Number(s.t1000_pnl_usd || 0).toFixed(2)}</td>
      </tr>`;
    }).join('');

    document.getElementById('a124_open').innerHTML = (a124.open_positions || []).map(p => `
      <tr>
        <td><b>${esc(shortSlv(p.sleeve || '').slice(0, 16))}</b></td>
        <td>${esc(p.title || '')}</td>
        <td>$${Number(p.eff_px || 0).toFixed(3)}</td>
        <td>$${Number(p.last_bid || 0).toFixed(3)}</td>
        <td class="warn">${esc(p.tte || '-')}</td>
      </tr>
    `).join('') || '<tr><td colspan="5" class="sub">No open shadow boxes</td></tr>';

    const dsmEl = document.getElementById('dir_shdw_meta');
    if (dsmEl) {
      const ca = ds.cand_a_zsplit || {}, xau = ds.xau_15m || {}, sl = ds.sol_v395 || {};
      const caPnl = Number(ca.pnl_usd || 0), xauPnl = Number(xau.pnl_usd || 0), slPnl = Number(sl.pnl_usd || 0);
      dsmEl.innerHTML = `Directional OOS (${esc(ds.spec_version || 'v3.1')}): <b>+$${Number(ds.oos_pnl_usd || 0).toFixed(2)}</b> (${ds.oos_wins ?? 0}W/${ds.oos_losses ?? 0}L, ${ds.oos_wr_pct ?? 0}%) &bull; P3A Maker: ${ds.p3a_resolved_w ?? 0}/${ds.p3a_resolved_n ?? 0} W<br>` +
        `v5.1 Shadow Gates &mdash; <b>XAU 15m Maker</b>: <b>${xau.wins ?? 0}W/${xau.losses ?? 0}L</b> (<span class="${xauPnl >= 0 ? 'pos' : 'neg'}">${xauPnl >= 0 ? '+' : ''}$${xauPnl.toFixed(2)}</span>, ${xau.status || 'IDLE'}) &bull; ` +
        `<b>Hybrid z-Split</b>: <b>${ca.wins ?? 0}W/${ca.losses ?? 0}L</b> (sig=${ca.signals_seen ?? 0}) &bull; ` +
        `<b>SOL Canary</b>: <b>LIVE 0.85x</b> (shadow: ${sl.wins ?? 0}W/${sl.losses ?? 0}L, <span class="${slPnl >= 0 ? 'pos' : 'neg'}">+$${slPnl.toFixed(0)}</span>)`;
    }

    document.getElementById('a124_closed').innerHTML = (a124.recent_closed || []).map(p => `
      <tr>
        <td style="white-space:nowrap;">${esc(p.closed_et || fmtOttawa(p.closed_utc, 'md_hm'))}</td>
        <td><b>${esc(shortSlv(p.sleeve || '').slice(0, 16))}</b></td>
        <td>${esc(p.title || '')}</td>
        <td>$${Number(p.eff_px || 0).toFixed(3)}&rarr;$${Number(p.payout_px || 0).toFixed(2)}</td>
        <td class="${p.won ? 'pos' : 'neg'}"><b>${p.t100_pnl >= 0 ? '+' : ''}$${Number(p.t100_pnl || 0).toFixed(2)}</b> / ${p.t1000_pnl >= 0 ? '+' : ''}$${Number(p.t1000_pnl || 0).toFixed(2)}</td>
      </tr>
    `).join('') || '<tr><td colspan="5" class="sub">No closed shadow boxes recorded yet</td></tr>';

    const apHdr = document.getElementById('apex_hdr');
    if (apHdr) apHdr.textContent = `Hyperliquid APEX ${apVer} (Testnet — $0 Mainnet, 4H Bar Cadence)`;
    document.getElementById('apex_meta').innerHTML =
      `State: <b>${esc(ap.circuit_breaker || '-')}</b> (${esc(ap.reconciliation_status || '-')}) | Regime: <b>${esc(ap.regime || '-')}</b> | WS: <b>${ap.ws_connected ? 'LIVE' : 'IDLE'}</b> | Gate 2: <b>${esc(ap.gate2_fills || '-')}</b> (${ap.maker_pct ?? 0}% Maker) | Next 4H Bar: <b>${next4hCountdown()}</b>`;
    document.getElementById('apex_fills').innerHTML = (ap.recent_fills || []).map(f => `
      <tr>
        <td style="white-space:nowrap;">${esc(f.time_et || fmtOttawa(f.time_utc, 'hms'))}</td>
        <td>${f.symbol}</td>
        <td>${f.side}</td>
        <td>${f.order_type}</td>
        <td class="${f.shortfall_bps <= 5 ? 'pos' : 'warn'}">${f.shortfall_bps} bps</td>
      </tr>
    `).join('');
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
                timeout=12,
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
        # Fast non-blocking RAM read whenever cached snapshot exists and force is False
        if not force and self._last_data:
            return self._last_data
        # Coalesce concurrent forced/initial refreshes on _fetch_lock
        acquired = self._fetch_lock.acquire(timeout=0.15 if (not force and self._last_data) else 12.0)
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
    ap = d.get("apex_testnet") or {}
    print("=" * 78)
    print(f" DOMINUS LIVE COMMAND CENTER  |  {d.get('fetched_at_et') or d.get('fetched_at_utc')} (Ottawa)")
    print("=" * 78)
    print(
        f" Host Load (2 vCPU): {la[0]} ({la[1]}, {la[2]})  |  "
        f"RAM Available: {mem.get('available')} / {mem.get('total')} MB"
    )
    print(
        f" Polymarket Live   : ${pm.get('bankroll_usd', 0):.2f} Cash  |  "
        f"Epoch: {pm.get('epoch_wins', 0)}W/{pm.get('epoch_losses', 0)}L "
        f"({pm.get('epoch_net_pnl_usd', 0):+.2f} USD net, fees ${pm.get('epoch_fees_usd', 0):.2f})  |  "
        f"Halt={pm.get('risk_halt')}"
    )
    print(
        f" APEX {ap.get('version', 'v5.2.0')} : {ap.get('circuit_breaker')} ({ap.get('reconciliation_status')})  |  "
        f"NAV: ${ap.get('nav_usd', 0):.2f} (HWM ${ap.get('hwm_nav_usd', 0):.2f})  |  Regime: {ap.get('regime')}  |  "
        f"WS={ap.get('ws_connected')} ({ap.get('ws_msgs')} msgs)  |  Canary: {ap.get('canary_fills')} (Gate2: {ap.get('gate2_fills')}, {ap.get('maker_pct')}% Maker)"
    )
    print("-" * 78)
    print(" Recent Real-Money Polymarket Closed Trades (Ottawa ET):")
    for c in (pm.get("recent_closed") or [])[:8]:
        print(
            f"   {c.get('time_et') or c['time_utc']} | {c['asset']:14s} | {c['entry_px']} -> {c['exit_px']} | "
            f"${c['notional_usd']:6.2f} | Net {c['net_pnl_usd']:+6.2f} USD | {c['reason']}"
        )
    print("-" * 78)
    sf = d.get("shock_forensics") or {}
    sfs = sf.get("summary") or {}
    print(
        f" Shock & Attempt Forensics : Attempts={sfs.get('attempts', 0)} (Filled={sfs.get('filled', 0)}) | "
        f"TooSlow={sfs.get('speed_misses', 0)} (Flight={sfs.get('flight_kills', 0)}, PreEval={sfs.get('pre_eval_repriced', 0)}, "
        f"MakerLeft={sfs.get('maker_left_behind', 0)}, FeedLag={sfs.get('feed_lags', 0)}) | "
        f"AlreadyPriced={sfs.get('already_priced', 0)} | Med HTTP={sfs.get('med_http_ms')}ms"
    )
    for r in (sf.get("rows") or [])[:6]:
        print(
            f"   {str(r.get('ts_et') or str(r.get('ts_utc',''))[5:19])} | {str(r.get('asset',''))+' '+str(r.get('horizon',''))+' '+str(r.get('side','')):12s} | "
            f"{str(r.get('badge','')):19s} | {str(r.get('diagnosis',''))[:76]}"
        )
    print("-" * 78)
    print(" Alpha-124 Shadow & _grad8 Auto-Promotion Tracker:")
    for s in (d.get("alpha124") or {}).get("sleeves") or []:
        print(
            f"   {s['sleeve']:30s} | Open={s['open']} | {s['wins']:2d}W/{s['losses']:2d}L | "
            f"Grad8={s['grad8_progress']} | T1000={s['t1000_pnl_usd']:+7.2f} USD"
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
        print("-" * 78)
        print(
            f" PAA Autonomy OS  : Director={dh.get('status', 'INIT')} (Cycle #{dh.get('cycle_count', 0)}, age={dh.get('age_sec')}s) | "
            f"Monitor={mh.get('status', 'INIT')} (age={mh.get('age_sec')}s) | Stop={paa.get('master_stop_engaged')} | "
            f"AI Cost Today=${br.get('daily_ai_cost_usd', 0.0):.4f}/{br.get('max_daily_ai_cost_usd', 2.50):.2f}"
        )
        print(
            f" Zero-Trust State : Policies={paa.get('tier_a_intact_count', 0)}/5 | "
            f"Facts(Fresh={zt.get('verified_facts_fresh', 0)}, Stale={zt.get('verified_facts_stale', 0)}, Contra={zt.get('verified_facts_contradicted', 0)}) | "
            f"Sessions={zt.get('sessions_total', 0)} ({zt.get('fresh_session_pct', 100.0)}% fresh, peak_ctx={zt.get('max_context_pct', 0.0)}%/60%) | "
            f"Tasks={json.dumps(tc)}"
        )
        print(
            f" Schedules & TierC: Next=[{tm_short}] | Ladder={json.dumps(lad)}"
        )
    print("=" * 78)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dominus Zero-Overhead Live Command Center")
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
                # Browser canceled an earlier tab fetch or reloaded mid-write (WinError 10053) — benign
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
                self._safe_send(200, "text/html; charset=utf-8", HTML_PAGE.encode("utf-8"))

        def log_message(self, fmt: str, *a: Any) -> None:
            return

    url = f"http://127.0.0.1:{args.port}"
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    srv.daemon_threads = True
    print(f"Dominus Live Command Center running locally at {url} (Background SSH cache=7s, Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped Dominus Live Command Center.")


if __name__ == "__main__":
    main()
