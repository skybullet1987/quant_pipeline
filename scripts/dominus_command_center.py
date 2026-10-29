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
import json, os, pathlib, re, subprocess, time

root = pathlib.Path("/home/skybullet1987/quant_pipeline")
out = {"fetched_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()), "unix_ts": time.time()}

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

# 2. Services
svcs = [
    "polymarket-live-harvester.service",
    "polymarket-alpha124-shadow.service",
    "polymarket-recorder.service",
    "polymarket-recorder-eth.service",
    "polymarket-recorder-sol.service",
    "polymarket-recorder-xrp.service",
    "polymarket-trader.service",
    "polymarket-exp316-shadow.service",
    "apex-perp.service",
]
svc_map = {}
for sv in svcs:
    try:
        r = subprocess.run(["systemctl", "--user", "is-active", sv], capture_output=True, text=True, timeout=2)
        svc_map[sv.replace(".service", "")] = r.stdout.strip() or "unknown"
    except Exception:
        svc_map[sv.replace(".service", "")] = "unknown"
try:
    ap = subprocess.run(["pgrep", "-f", "production_apex_daemon.py"], capture_output=True, text=True, timeout=2)
    svc_map["hyperliquid-apex-testnet"] = "active" if ap.returncode == 0 and ap.stdout.strip() else "inactive"
except Exception:
    svc_map["hyperliquid-apex-testnet"] = "unknown"
out["services"] = svc_map

# 3. Polymarket Live Harvester + Live Log Events
lh_path = root / "data/polymarket/live_harvester_state.json"
if lh_path.exists():
    s = json.loads(lh_path.read_text())
    closed = s.get("closed_positions") or []
    wins = sum(1 for c in closed if float(c.get("net_pnl_usd", 0.0)) > 0)
    tot_pnl = round(sum(float(c.get("net_pnl_usd", 0.0)) for c in closed), 2)
    tot_fees = round(sum(float(c.get("fee_usd", 0.0)) for c in closed), 2)
    act_list = []
    for tid, p in (s.get("active_positions") or {}).items():
        act_list.append({
            "trade_id": tid,
            "asset": p.get("asset"),
            "horizon": p.get("horizon"),
            "sleeve": p.get("sleeve"),
            "side": p.get("target_token"),
            "entry_px": p.get("entry_price"),
            "target_tp": p.get("target_exit_price"),
            "notional_usd": round(float(p.get("notional_usd", 0.0) or 0.0), 2),
            "status": p.get("exit_order_status") or p.get("status"),
        })
    recent_closed = []
    cum = round(float(s.get("live_bankroll", 0.0) or 0.0) - tot_pnl, 2)
    equity_curve = [cum]
    for c in closed:
        cum = round(cum + float(c.get("net_pnl_usd", 0.0)), 2)
        equity_curve.append(cum)
    for c in reversed(closed[-12:]):
        recent_closed.append({
            "time_utc": str(c.get("entry_time_utc", ""))[:19].replace("T", " "),
            "trade_id": c.get("trade_id"),
            "asset": f"{c.get('asset','')} {c.get('horizon','')} {c.get('target_token','')}".strip(),
            "sleeve": c.get("sleeve"),
            "entry_px": c.get("entry_price"),
            "exit_px": c.get("average_exit_price"),
            "notional_usd": round(float(c.get("notional_usd", 0.0) or 0.0), 2),
            "fee_usd": round(float(c.get("fee_usd", 0.0) or 0.0), 2),
            "net_pnl_usd": round(float(c.get("net_pnl_usd", 0.0) or 0.0), 2),
            "reason": c.get("close_reason") or c.get("status"),
        })
    out["polymarket_live"] = {
        "bankroll_usd": round(float(s.get("live_bankroll", 0.0) or 0.0), 2),
        "equity_usd": round(float(s.get("total_account_equity", 0.0) or 0.0), 2),
        "hwm_usd": round(float(s.get("high_water_mark_equity", 0.0) or 0.0), 2),
        "tier": s.get("current_equity_tier") or s.get("equity_tier"),
        "risk_halt": bool(s.get("risk_halt", False)),
        "halt_reasons": s.get("global_halt_reasons") or [],
        "epoch_closed_count": len(closed),
        "epoch_wins": wins,
        "epoch_losses": len(closed) - wins,
        "epoch_net_pnl_usd": tot_pnl,
        "epoch_fees_usd": tot_fees,
        "trades_this_hour": s.get("trades_this_hour", 0),
        "equity_curve": equity_curve,
        "active_positions": act_list,
        "recent_closed": recent_closed,
    }
else:
    out["polymarket_live"] = {}

# Recent notable live log lines (bounded 256 KB tail seek - zero full-file scan)
log_path = root / "data/polymarket/live_harvester.log"
log_events = []
if log_path.exists():
    try:
        _pat = re.compile(r"\[CLOSED\]|\[LIVE FILL\]|\[LIVE PHASE 3A|\[AUTO-REDEEMER\]|\[RECONCILIATION\] Live collateral|\[D1 BOX")
        with open(log_path, "rb") as _lf:
            _sz = log_path.stat().st_size
            _off = max(0, _sz - 262144)
            _lf.seek(_off)
            _tail_lines = _lf.read().decode("utf-8", errors="replace").splitlines()
        if _off > 0 and _tail_lines:
            _tail_lines = _tail_lines[1:]
        for ln in [x for x in _tail_lines if _pat.search(x)][-8:]:
            log_events.append(ln[-150:])
    except Exception:
        pass
out["live_log_events"] = list(reversed(log_events))

# 4. Alpha-124 Shadow & _grad8 progress + live spots
a_path = root / "data/alpha124/alpha124_shadow_state.json"
if a_path.exists():
    a = json.loads(a_path.read_text())
    by_slv = a.get("by_sleeve") or {}
    open_p = a.get("open_positions") or []
    spots = {k: round(float(v), 4 if float(v) < 10 else 2) for k, v in (a.get("spots") or {}).items() if k in ("BTC", "ETH", "SOL", "XRP")}
    watch_sleeves = [
        "D1_SAME_ORACLE_DOMINANCE_BOX",
        "D1_QUIET_BOOK_BOX",
        "CM_B3_PYTH_BARRIER_BOX",
        "SP1_NBA_ZERO_FEE_BOX",
        "NR0_ZERO_FEE_SLATE_ARB",
        "W1_SOLAR_PEAK_LOCK",
        "U1_DAILY_UPDOWN_LOCK",
    ]
    slv_rows = []
    for slv in watch_sleeves:
        m = by_slv.get(slv) or {}
        c_n = int(m.get("closed", 0) or 0)
        slv_rows.append({
            "sleeve": slv,
            "open": int(m.get("open", 0) or 0),
            "closed": c_n,
            "wins": int(m.get("wins", 0) or 0),
            "losses": int(m.get("losses", 0) or 0),
            "t1000_pnl_usd": round(float(m.get("realized_pnl_t1000_usd", 0.0) or 0.0), 2),
            "grad8_progress": f"{min(c_n, 8)}/8",
        })
    open_boxes = []
    for p in open_p[:8]:
        open_boxes.append({
            "sleeve": p.get("sleeve"),
            "title": str(p.get("title") or "")[:54],
            "eff_px": p.get("entry_eff_px_t1000"),
            "last_bid": p.get("last_bid"),
        })
    out["alpha124"] = {
        "spots": spots,
        "open_total": len(open_p),
        "closed_total": sum(int(v.get("closed", 0) or 0) for v in by_slv.values()),
        "by_d1_asset": a.get("by_d1_asset") or {},
        "sleeves": slv_rows,
        "open_positions": open_boxes,
    }
else:
    out["alpha124"] = {}

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
            "symbol": x.get("symbol"),
            "side": x.get("side"),
            "order_type": x.get("order_type"),
            "px": x.get("actual_fill_price"),
            "sz": x.get("filled_size"),
            "shortfall_bps": round(float(x.get("total_shortfall_bps", 0.0)), 2),
        })
    st_path = root / "data/papertrade_state.json"
    st_obj = json.loads(st_path.read_text(encoding="utf-8")) if st_path.exists() else {}
    sh_path = root / "data/apex/champion_challenger_shadow.json"
    sh_obj = json.loads(sh_path.read_text(encoding="utf-8")) if sh_path.exists() else {}
    sh_hist = sh_obj.get("history") or []
    latest_regime = (sh_hist[-1].get("regime") or {}).get("regime", "UNKNOWN") if sh_hist else "UNKNOWN"
    out["apex_testnet"] = {
        "version": st_obj.get("version", "v5.1.0"),
        "nav_usd": round(float(st_obj.get("current_strategy_equity", hwm_nav) or hwm_nav), 2),
        "reconciliation_status": (st_obj.get("last_reconciliation") or {}).get("status") or st_obj.get("reconciliation_status", "EXACT"),
        "regime": latest_regime,
        "circuit_breaker": st_obj.get("circuit_breaker", cb_state),
        "halt_reason": cb_reason if cb_state != "RUNNING" else "",
        "hwm_nav_usd": round(float(st_obj.get("high_water_mark", hwm_nav) or hwm_nav), 2),
        "gate2_fills": f"{audit_total}/500",
        "maker_pct": round(100.0 * maker_n / len(audits), 1) if audits else 0.0,
        "recent_fills": recent_hl,
    }
else:
    out["apex_testnet"] = {}

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
  @media (max-width: 1000px) { .two-col { grid-template-columns: 1fr; } }
  h2 { font-size: 13px; margin: 0 0 10px 0; color: var(--blue); text-transform: uppercase; letter-spacing: 0.5px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 600; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
  .pill-ok { background: rgba(46,160,67,0.2); color: var(--green-bright); border: 1px solid rgba(63,185,80,0.4); }
  .pill-bad { background: rgba(248,81,73,0.2); color: var(--red); border: 1px solid rgba(248,81,73,0.4); }
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
    <h2 style="margin:0;">Daemon Fleet &amp; D1 Overlap Window Countdown (0 MB VM Browser Overhead)</h2>
    <div class="sub" id="d1_timer" style="margin:0;color:var(--amber);font-weight:600;"></div>
  </div>
  <div class="svc-wrap" id="svcs"></div>
</div>

<div class="two-col">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <h2>Polymarket Real-Money Live Harvester</h2>
      <svg id="spark" width="160" height="32"></svg>
    </div>
    <div id="active_box" style="margin-bottom:10px;font-size:12px;"></div>
    <table>
      <thead><tr><th>UTC</th><th>Market</th><th>In &rarr; Out</th><th>Notional</th><th>Net PnL</th><th>Exit</th></tr></thead>
      <tbody id="pm_trades"></tbody>
    </table>
    <h2 style="margin-top:16px;">Live Execution Event Stream</h2>
    <div class="log-box" id="log_events"></div>
  </div>
  <div class="card">
    <h2>Alpha-124 Shadow &amp; _grad8 Auto-Promotion</h2>
    <table>
      <thead><tr><th>Sleeve</th><th>Open</th><th>W / L</th><th>Grad8</th><th>T1000 PnL</th></tr></thead>
      <tbody id="a124_sleeves"></tbody>
    </table>
    <h2 style="margin-top:14px;">Open Shadow Structural Boxes</h2>
    <table>
      <thead><tr><th>Sleeve</th><th>Market</th><th>Cost</th><th>Bid</th></tr></thead>
      <tbody id="a124_open"></tbody>
    </table>
    <h2 style="margin-top:16px;">Hyperliquid APEX v5.0 (Testnet — $0 Mainnet)</h2>
    <div id="apex_meta" style="font-size:12px;margin-bottom:8px;"></div>
    <table>
      <thead><tr><th>UTC</th><th>Asset</th><th>Side</th><th>Type</th><th>Shortfall</th></tr></thead>
      <tbody id="apex_fills"></tbody>
    </table>
  </div>
</div>

<script>
function esc(v) {
  return String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
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

async function refreshNow(force=false) {
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
    document.getElementById('meta').textContent =
      `Synced: ${d.fetched_at_utc} | Load: ${la[0]} (${la[1]}, ${la[2]}) | RAM Avail: ${mem.available || '?'} / ${mem.total || '?'} MB | Auto-refresh: 15s`;

    const spots = a124.spots || {};
    document.getElementById('spots').innerHTML = Object.entries(spots).map(([k, v]) =>
      `<span class="spot-chip"><b>${k}</b> $${v}</span>`
    ).join('');

    const pnlCls = (pm.epoch_net_pnl_usd || 0) >= 0 ? 'pos' : 'neg';
    const wr = pm.epoch_closed_count ? ((100 * pm.epoch_wins / pm.epoch_closed_count).toFixed(1) + '%') : 'N/A';
    document.getElementById('kpis').innerHTML = `
      <div class="card"><div class="label">Polymarket Live Cash</div><div class="val pos">$${(pm.bankroll_usd ?? 0).toFixed(2)}</div><div class="sub">Equity: $${(pm.equity_usd ?? 0).toFixed(2)} | Tier: ${pm.tier || '-'}</div></div>
      <div class="card"><div class="label">Current Epoch Net PnL</div><div class="val ${pnlCls}">${(pm.epoch_net_pnl_usd ?? 0) >= 0 ? '+' : ''}$${(pm.epoch_net_pnl_usd ?? 0).toFixed(2)}</div><div class="sub">Fees paid: $${(pm.epoch_fees_usd ?? 0).toFixed(2)}</div></div>
      <div class="card"><div class="label">Live Win Rate (Epoch)</div><div class="val">${pm.epoch_wins ?? 0}W / ${pm.epoch_losses ?? 0}L (${wr})</div><div class="sub">Open now: ${(pm.active_positions || []).length} | This hr: ${pm.trades_this_hour ?? 0}</div></div>
      <div class="card"><div class="label">VM Load &amp; Avail RAM</div><div class="val">${la[0]} / ${mem.available || 0} MB</div><div class="sub">Risk Halt: ${pm.risk_halt ? 'HALTED' : 'CLEAR'}</div></div>
      <div class="card"><div class="label">APEX v5.0 Testnet</div><div class="val ${ap.circuit_breaker === 'RUNNING' ? 'pos' : 'neg'}">${ap.circuit_breaker || '?'}</div><div class="sub">Gate 2: ${ap.gate2_fills || '-'} | Maker: ${ap.maker_pct ?? 0}%</div></div>
    `;

    drawSpark(pm.equity_curve || []);

    const svcs = d.services || {};
    document.getElementById('svcs').innerHTML = Object.entries(svcs).map(([k, v]) =>
      `<span class="pill ${v === 'active' ? 'pill-ok' : 'pill-bad'}">${k}: ${v}</span>`
    ).join('');

    const acts = pm.active_positions || [];
    document.getElementById('active_box').innerHTML = acts.length === 0
      ? '<span class="sub">Active live positions: 0 (Flat &amp; scanning shocks + Phase 3A maker rescues + D1 boxes)</span>'
      : '<b>LIVE OPEN POSITION:</b> ' + acts.map(a => `<span class="pos">${esc(a.asset)} ${esc(a.horizon)} ${esc(a.side)}</span> ($${Number(a.notional_usd || 0).toFixed(2)} @ ${esc(a.entry_px)} &rarr; TP ${esc(a.target_tp)}) [${esc(a.status)}]`).join(' | ');

    document.getElementById('pm_trades').innerHTML = (pm.recent_closed || []).map(c => `
      <tr>
        <td>${esc((c.time_utc || '').slice(11))}</td>
        <td><b>${esc(c.asset)}</b></td>
        <td>${esc(c.entry_px)} &rarr; ${esc(c.exit_px)}</td>
        <td>$${Number(c.notional_usd || 0).toFixed(2)}</td>
        <td class="${c.net_pnl_usd >= 0 ? 'pos' : 'neg'}"><b>${c.net_pnl_usd >= 0 ? '+' : ''}$${Number(c.net_pnl_usd || 0).toFixed(2)}</b></td>
        <td>${esc(c.reason)}</td>
      </tr>
    `).join('');

    document.getElementById('log_events').innerHTML = (d.live_log_events || []).map(l =>
      `<div>${esc(l)}</div>`
    ).join('') || '<div class="sub">No recent log events.</div>';

    document.getElementById('a124_sleeves').innerHTML = (a124.sleeves || []).map(s => `
      <tr>
        <td>${esc(s.sleeve.replace('_DOMINANCE_BOX','').replace('_ZERO_FEE_','_'))}</td>
        <td>${esc(s.open)}</td>
        <td>${esc(s.wins)}W / ${esc(s.losses)}L</td>
        <td>${esc(s.grad8_progress)}</td>
        <td class="${s.t1000_pnl_usd >= 0 ? 'pos' : 'neg'}">${s.t1000_pnl_usd >= 0 ? '+' : ''}$${Number(s.t1000_pnl_usd || 0).toFixed(2)}</td>
      </tr>
    `).join('');

    document.getElementById('a124_open').innerHTML = (a124.open_positions || []).map(p => `
      <tr>
        <td>${esc((p.sleeve || '').slice(0,14))}</td>
        <td>${esc(p.title || '')}</td>
        <td>$${Number(p.eff_px || 0).toFixed(3)}</td>
        <td>$${Number(p.last_bid || 0).toFixed(3)}</td>
      </tr>
    `).join('') || '<tr><td colspan="4" class="sub">No open shadow boxes</td></tr>';

    document.getElementById('apex_meta').innerHTML =
      `State: <b>${ap.circuit_breaker || '-'}</b> | Gate 2 Fills: <b>${ap.gate2_fills || '-'}</b> | Maker Share: <b>${ap.maker_pct ?? 0}%</b>`;
    document.getElementById('apex_fills').innerHTML = (ap.recent_fills || []).map(f => `
      <tr>
        <td>${(f.time_utc || '').slice(11,19)}</td>
        <td>${f.symbol}</td>
        <td>${f.side}</td>
        <td>${f.order_type}</td>
        <td class="${f.shortfall_bps <= 5 ? 'pos' : 'warn'}">${f.shortfall_bps} bps</td>
      </tr>
    `).join('');
  } catch (e) {
    document.getElementById('meta').textContent = 'Dashboard fetch error: ' + e;
  }
}
updateD1Countdown();
refreshNow();
setInterval(() => refreshNow(false), 15000);
</script>
</body>
</html>
"""


class SnapshotCache:
    def __init__(self, host: str, ttl_sec: float = 8.0) -> None:
        self.host = host
        self.ttl_sec = ttl_sec
        self._lock = threading.Lock()
        self._last_ts = 0.0
        self._last_data: Dict[str, Any] = {}

    def get(self, force: bool = False) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            if not force and self._last_data and (now - self._last_ts) < self.ttl_sec:
                return self._last_data
            try:
                proc = subprocess.run(
                    [
                        "ssh",
                        "-o",
                        "BatchMode=yes",
                        "-o",
                        "ConnectTimeout=7",
                        self.host,
                        "/home/skybullet1987/quant_pipeline/venv/bin/python3 -",
                    ],
                    input=REMOTE_PROBE_PY,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                )
                if proc.returncode != 0:
                    return {"error": (proc.stderr or proc.stdout).strip()[:400]}
                lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
                if not lines:
                    return {"error": f"Unexpected SSH output: {proc.stdout[:200]}"}
                self._last_data = json.loads(lines[-1])
                self._last_ts = now
                return self._last_data
            except Exception as exc:
                return {"error": str(exc)}


def print_cli_summary(d: Dict[str, Any]) -> None:
    if d.get("error"):
        print(f"[ERROR] Could not fetch telemetry: {d['error']}")
        return
    pm = d.get("polymarket_live") or {}
    mem = d.get("mem_mb") or {}
    la = d.get("load_avg") or [0, 0, 0]
    ap = d.get("apex_testnet") or {}
    print("=" * 78)
    print(f" DOMINUS LIVE COMMAND CENTER  |  {d.get('fetched_at_utc')}")
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
        f" APEX {ap.get('version', 'v5.1.0')} : {ap.get('circuit_breaker')} ({ap.get('reconciliation_status')})  |  "
        f"NAV: ${ap.get('nav_usd', 0):.2f} (HWM ${ap.get('hwm_nav_usd', 0):.2f})  |  Regime: {ap.get('regime')}  |  "
        f"Gate 2: {ap.get('gate2_fills')} ({ap.get('maker_pct')}% Maker)  |  Mainnet: $0.00"
    )
    print("-" * 78)
    print(" Recent Real-Money Polymarket Closed Trades:")
    for c in (pm.get("recent_closed") or [])[:8]:
        print(
            f"   {c['time_utc']} | {c['asset']:14s} | {c['entry_px']} -> {c['exit_px']} | "
            f"${c['notional_usd']:6.2f} | Net {c['net_pnl_usd']:+6.2f} USD | {c['reason']}"
        )
    print("-" * 78)
    print(" Alpha-124 Shadow & _grad8 Auto-Promotion Tracker:")
    for s in (d.get("alpha124") or {}).get("sleeves") or []:
        print(
            f"   {s['sleeve']:30s} | Open={s['open']} | {s['wins']:2d}W/{s['losses']:2d}L | "
            f"Grad8={s['grad8_progress']} | T1000={s['t1000_pnl_usd']:+7.2f} USD"
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

    cache = SnapshotCache(host=args.host)
    if args.json:
        print(json.dumps(cache.get(force=True), indent=2))
        return
    if args.once:
        print_cli_summary(cache.get(force=True))
        return

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            host_hdr = (self.headers.get("Host") or "").split(":")[0].strip().lower()
            if host_hdr and host_hdr not in ("127.0.0.1", "localhost"):
                self.send_error(403, "Forbidden Host")
                return
            if self.path.startswith("/api/snapshot"):
                force = "force=1" in self.path
                payload = json.dumps(cache.get(force=force)).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(payload)
            else:
                body = HTML_PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, fmt: str, *a: Any) -> None:
            return

    url = f"http://127.0.0.1:{args.port}"
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Dominus Live Command Center running locally at {url} (Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped Dominus Live Command Center.")


if __name__ == "__main__":
    main()
