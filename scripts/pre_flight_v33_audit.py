#!/usr/bin/env python3
"""
Polymarket v3.3 7-Point Pre-Flight Forensic Audit.

  1. Historical replay (v3.2-equivalent vs v3.3 gates) on data/polymarket/live_shock_triggers.jsonl
  2. Hot-path latency benchmark (single-hop sign+post w/ PreSignedOrderLadderCache, orjson, /dev/shm)
  3. Adversarial salvage & anti-wick simulation (4 paths) through check_resolutions_and_manage_positions()
  4. Correlated multi-asset Kelly sizing table on a $91.67 bankroll
  5. Live Gamma 15m market discovery + 3s Coinbase/Binance venue probe
  6. Full pytest suite
  7. Live process safety check

SAFETY: read-only on data/polymarket (replay/telemetry). No order is ever sent: the latency benchmark
replaces client.post_order with an in-process stub BEFORE any call, and the salvage simulation uses a
dry-run harvester with a mocked executor writing state to a temp directory.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import socket
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

import orjson  # noqa: E402

DATA = PIPELINE_ROOT / "data" / "polymarket"
TRIGGERS = DATA / "live_shock_triggers.jsonl"
RESOLUTIONS = DATA / "finalized_market_resolutions.jsonl"
TELEMETRY = {"BTC": DATA / "polymarket_hourly_telemetry.jsonl", "ETH": DATA / "polymarket_hourly_telemetry_eth.jsonl"}

RESULTS: Dict[str, str] = {}


def hdr(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def verdict(key: str, ok: bool, note: str = "") -> None:
    RESULTS[key] = ("PASS" if ok else "FAIL") + (f" - {note}" if note else "")
    print(f"  >> [{RESULTS[key]}]")


# ======================================================================================
# 1. HISTORICAL REPLAY
# ======================================================================================
def _classify(shock: Dict[str, Any]):
    title = str(shock.get("title") or "").lower()
    horizon = str(shock.get("horizon") or "").lower()
    slug = str(shock.get("series_slug") or "").lower()
    is_sub = any(x in horizon or x in slug or x in title for x in ("5m", "15m", "300s", "900s"))
    is_1h = (not is_sub) and (horizon == "1h" or "hourly" in slug or "am et" in title or "pm et" in title or "up or down" in title)
    return is_1h, is_sub


def _regime_band(is_1h: bool, is_sub: bool, tte: float, dist: float, target: str, z_eff: float, unlock: bool):
    """Mirrors the live v3.2 cushion-to-price matrix. Returns (regime, lo, hi) or (None, reason, None)."""
    sgn = dist if target == "UP" else -dist
    if is_1h:
        if 900.0 < tte <= 2700.0:
            if sgn < 0.15:
                return None, "RegimeA cushion<0.15%", None
            return "A", 0.55, 0.78
        lo_tte = 30.0 if (unlock and z_eff >= 2.2) else 120.0
        if lo_tte <= tte <= 900.0:
            if sgn < 0.10:
                return None, "RegimeB cushion<0.10%", None
            c = abs(dist)
            if c < 0.15:
                return "B1", 0.55, 0.75
            if c < 0.22:
                return "B2", 0.58, 0.80
            return "B3", 0.62, 0.84
        return None, "1h TTE window", None
    if is_sub:
        if 90.0 <= tte <= 540.0:
            if sgn < 0.08:
                return None, "RegimeC cushion<0.08%", None
            return "C", 0.58, 0.82
        return None, "15m TTE window", None
    return None, "unknown horizon", None


def _entry_vwap(tf: Dict[str, Any]) -> Optional[float]:
    v = tf.get("vwap_$25") or tf.get("vwap_$20")
    if v:
        return float(v)
    asks = tf.get("raw_top_asks") or []
    return float(asks[0][0]) if asks else None


def run_replay() -> Dict[str, Any]:
    from src.polymarket_research.polymarket_live_harvester import (
        compute_composite_edge_score,
        compute_max_acceptable_ask,
        compute_correlated_truncated_kelly_size,
    )

    hdr("1. HISTORICAL REPLAY BACKTEST  (v3.2-equivalent gates vs v3.3 gates)  on live_shock_triggers.jsonl")
    res_map: Dict[str, str] = {}
    with open(RESOLUTIONS, "rb") as f:
        for line in f:
            try:
                r = orjson.loads(line)
                res_map[str(r["market_id"])] = str(r.get("winning_outcome") or "").upper()
            except Exception:
                continue

    shocks = []
    with open(TRIGGERS, "rb") as f:
        for line in f:
            try:
                shocks.append(orjson.loads(line))
            except Exception:
                continue
    shocks.sort(key=lambda s: float(s.get("t0_unix") or 0.0))

    books = {"v3.2": [], "v3.3": []}
    seen = {"v3.2": set(), "v3.3": set()}
    hour_counts = {"v3.2": defaultdict(int), "v3.3": defaultdict(int)}
    rejects = {"v3.2": defaultdict(int), "v3.3": defaultdict(int)}
    tiers = defaultdict(int)

    for s in shocks:
        asset = str(s.get("asset") or "").upper()
        if not asset:
            t = str(s.get("title") or "").lower()
            asset = "BTC" if "bitcoin" in t else ("ETH" if "ethereum" in t else "")
        if asset not in ("BTC", "ETH"):
            continue
        sd = str(s.get("shock_direction") or "").upper()
        target = "UP" if sd in ("BUY", "UP") else "DOWN"
        tte = float(s.get("seconds_to_expiry") or 0.0)
        dist = float(s.get("candle_distance_pct") or 0.0)
        tf = (s.get("pre_shock_features_t0") or {}).get(target) or {}
        vwap = _entry_vwap(tf)
        first_ask = float((tf.get("raw_top_asks") or [[0]])[0][0] or 0.0)
        m_id = str(s.get("market_id"))
        is_1h, is_sub = _classify(s)
        t0 = float(s.get("t0_unix") or 0.0)
        hour = int(t0 // 3600)
        if not vwap or first_ask <= 0:
            continue
        ofi = float(s.get("shock_ofi") if s.get("shock_ofi") is not None else 1.0)
        dbasis = float(s.get("delta_basis_100ms") or 0.0)
        dir_db = dbasis if target == "UP" else -dbasis

        # ---- v3.2-equivalent: OFI>=0.60 + cushion matrix + price band, flat $22 ticket ----
        key = (m_id, target)
        if key not in seen["v3.2"] and hour_counts["v3.2"][hour] < 4:
            reason = None
            if abs(ofi) < 0.60:
                reason = "OFI<0.60"
            elif not (120.0 <= tte <= 2700.0 or (is_sub and 90.0 <= tte <= 540.0)):
                reason = "TTE window"
            else:
                reg, lo, hi = _regime_band(is_1h, is_sub, tte, dist, target, 0.0, unlock=False)
                if reg is None:
                    reason = lo
                elif not (lo <= first_ask <= hi and lo <= vwap <= hi):
                    reason = f"price band {reg}"
            if reason:
                rejects["v3.2"][reason] += 1
            else:
                seen["v3.2"].add(key)
                hour_counts["v3.2"][hour] += 1
                books["v3.2"].append(dict(shock=s, asset=asset, target=target, vwap=vwap, ticket=22.0, tier="n/a", tte=tte))

        # ---- v3.3: composite edge + matrix (30s unlock) + p_max (directional basis) + Kelly ----
        if key not in seen["v3.3"] and hour_counts["v3.3"][hour] < 4:
            edge = compute_composite_edge_score(s)
            reason = None
            pm = None
            if edge["veto"]:
                reason = "P1 " + ("score<50" if "e_score" in str(edge.get("veto_reason")) else str(edge.get("veto_reason")).split(" ")[0] + " veto")
            else:
                pm = compute_max_acceptable_ask(
                    dist_pct=dist, tte_sec=tte, asset=asset, shock_ofi=ofi,
                    shock_vol_usd=float(s.get("shock_volume_100ms") or 1_500_000.0),
                    delta_basis_bps=dir_db, age_ask_ms=float(tf.get("age_ask_ms") or 350.0),
                    is_subhourly_15m=is_sub,
                )
                reg, lo, hi = _regime_band(is_1h, is_sub, tte, dist, target, pm["z_eff"], unlock=True)
                if reg is None:
                    reason = lo
                elif not (lo <= first_ask <= hi and lo <= vwap <= hi):
                    reason = f"price band {reg}"
                elif pm["p_max"] <= 0.0 or vwap > pm["p_max"]:
                    reason = "p_max"
            if reason:
                rejects["v3.3"][reason] += 1
            else:
                seen["v3.3"].add(key)
                hour_counts["v3.3"][hour] += 1
                tiers[edge["tier"]] += 1
                ticket = compute_correlated_truncated_kelly_size(
                    live_equity=91.67, entry_px=vwap, p_win=pm["p_true"],
                    kelly_multiplier=edge["kelly_multiplier"], min_lot_usd=12.0, max_ticket_cap=50.0,
                )
                books["v3.3"].append(dict(shock=s, asset=asset, target=target, vwap=vwap, ticket=ticket, tier=edge["tier"], tte=tte))

    # ---- outcome + salvage path simulation from 10s telemetry (resolved 1h markets only) ----
    need = defaultdict(set)
    for ver in books:
        for tr in books[ver]:
            need[tr["asset"]].add(str(tr["shock"].get("market_id")))
    paths: Dict[str, List] = defaultdict(list)
    for asset, fpath in TELEMETRY.items():
        if not fpath.exists() or not need[asset]:
            continue
        wanted = need[asset]
        with open(fpath, "rb") as f:
            for line in f:
                i = line.find(b'"market_id": "')
                if i < 0:
                    continue
                mid = line[i + 14: line.find(b'"', i + 14)].decode()
                if mid not in wanted:
                    continue
                try:
                    r = orjson.loads(line)
                    paths[mid].append((float(r["timestamp_unix"]), float(r.get("binance_spot") or 0.0),
                                       float(r.get("binance_1h_open") or 0.0),
                                       float((r.get("UP") or {}).get("best_bid") or 0.0),
                                       float((r.get("DOWN") or {}).get("best_bid") or 0.0),
                                       float(r.get("seconds_to_expiry") or 0.0)))
                except Exception:
                    continue
    for v in paths.values():
        v.sort()

    def simulate(tr, v33: bool):
        s = tr["shock"]
        mid = str(s.get("market_id"))
        win = res_map.get(mid)
        if win not in ("UP", "DOWN"):
            return None
        entry = tr["vwap"]
        shares = math.floor(tr["ticket"] / entry)
        if shares <= 0:
            return None
        fee_in = shares * 0.07 * entry * (1 - entry)
        cost = shares * entry + fee_in
        t0 = float(s.get("t0_unix") or 0.0)
        target = tr["target"]
        start = None
        vel_hist = []
        max_bid = 0.0
        trail_start = None
        for (ts, spot, open_px, ub, db, tte_rem) in paths.get(mid, []):
            if ts <= t0 or spot <= 0 or open_px <= 0:
                continue
            bid = ub if target == "UP" else db
            disp = (spot - open_px) if target == "UP" else (open_px - spot)
            wrong = (-disp / open_px) * 100.0
            vel_hist = [p for p in vel_hist if ts - p[0] <= 15.0] + [(ts, spot)]
            o = vel_hist[0][1]
            vel = ((spot - o) / o * 100.0) * (1 if target == "UP" else -1) if len(vel_hist) >= 2 else 0.0
            max_bid = max(max_bid, bid)
            # trailing ratchet (v3.3 only)
            if v33 and max_bid >= max(0.82, entry + 0.12):
                floor_px = max_bid - (0.05 if max_bid >= 0.90 else 0.07)
                if bid <= floor_px and tte_rem >= 25.0 and bid >= entry + 0.04:
                    trail_start = trail_start or ts
                    if ts - trail_start >= 4.0:
                        px = max(0.01, bid - 0.02)
                        proceeds = shares * px - shares * 0.07 * px * (1 - px)
                        return dict(pnl=proceeds - cost, won=None, exit="RATCHET", cost=cost)
                else:
                    trail_start = None
            if wrong <= 0.0:
                start = None
                continue
            if tte_rem > 900:
                ini, sus, dur, mb = 0.16, 0.14, 40.0, 0.08
            elif tte_rem > 180:
                ini, sus, dur, mb = 0.11, 0.09, 18.0, 0.08
            elif tte_rem >= 25:
                ini, sus, dur, mb = 0.06, 0.04, 8.0, 0.06
            else:
                continue
            if v33 and vel <= -0.08 and bid <= 0.42:
                dur *= 0.5
            if start is None:
                if wrong >= ini:
                    start = ts
                continue
            if wrong < sus:
                start = None
                continue
            if v33 and vel >= 0.03:
                continue
            if ts - start >= dur and bid >= mb:
                px = max(0.01, bid - 0.02)
                proceeds = shares * px - shares * 0.07 * px * (1 - px)
                return dict(pnl=proceeds - cost, won=None, exit="SALVAGE", cost=cost, recovered=proceeds)
        won = (win == target)
        return dict(pnl=(shares * 1.0 if won else 0.0) - cost, won=won, exit="EXPIRY", cost=cost)

    summary = {}
    for ver in ("v3.2", "v3.3"):
        sims = [x for x in (simulate(t, ver == "v3.3") for t in books[ver]) if x]
        settled = [x for x in sims if x["exit"] == "EXPIRY"]
        salv = [x for x in sims if x["exit"] == "SALVAGE"]
        rat = [x for x in sims if x["exit"] == "RATCHET"]
        wins = sum(1 for x in sims if x["pnl"] > 0)
        summary[ver] = dict(
            qualified=len(books[ver]), simulated=len(sims),
            avg_entry=mean([t["vwap"] for t in books[ver]]) if books[ver] else 0.0,
            win_rate=(wins / len(sims) * 100.0) if sims else 0.0,
            expiry_wr=(sum(1 for x in settled if x["won"]) / len(settled) * 100.0) if settled else 0.0,
            salvages=len(salv), salvage_recovered=sum(x.get("recovered", 0.0) for x in salv),
            ratchets=len(rat), net_pnl=sum(x["pnl"] for x in sims),
            deployed=sum(x["cost"] for x in sims),
        )

    print(f"  Shocks scanned (BTC/ETH, full file): {len(shocks)}  |  span: "
          f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(float(shocks[0].get('t0_unix') or 0)))} -> "
          f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(float(shocks[-1].get('t0_unix') or 0)))} UTC")
    print(f"  Resolved markets available: {len(res_map)}  |  telemetry paths loaded: {len(paths)} markets")
    print(f"\n  {'Metric':<44}{'v3.2-equiv':>16}{'v3.3':>16}")
    rows = [
        ("Qualified trades (1/market-dir, <=4/hr)", "qualified", "{:d}"),
        ("Simulated (resolved + priced)", "simulated", "{:d}"),
        ("Average entry price (VWAP)", "avg_entry", "${:.4f}"),
        ("Simulated win rate (pnl>0)", "win_rate", "{:.1f}%"),
        ("Held-to-expiry win rate", "expiry_wr", "{:.1f}%"),
        ("Salvage exits", "salvages", "{:d}"),
        ("Salvage cash recovered", "salvage_recovered", "${:.2f}"),
        ("Trailing-ratchet exits", "ratchets", "{:d}"),
        ("Capital deployed", "deployed", "${:.2f}"),
        ("Net PnL (after taker fees)", "net_pnl", "${:+.2f}"),
    ]
    for label, k, fmt in rows:
        print(f"  {label:<44}{fmt.format(summary['v3.2'][k]):>16}{fmt.format(summary['v3.3'][k]):>16}")
    print("\n  v3.3 tier breakdown (qualified):")
    for t in ("TIER_A_PLUS_STALE_SNIPE", "TIER_B_STANDARD"):
        print(f"    - {t}: {tiers.get(t, 0)}")
    c_rej = sum(v for k, v in rejects["v3.3"].items() if k.startswith("P1"))
    print(f"    - TIER_C_REJECT (Pillar-1 vetoes incl. hard vetoes): {c_rej}")
    for ver in ("v3.2", "v3.3"):
        top = sorted(rejects[ver].items(), key=lambda x: -x[1])[:6]
        print(f"  Top {ver} reject reasons: " + "; ".join(f"{k}={v}" for k, v in top))
    print("  NOTE: exits simulated on 10s telemetry snapshots (durations quantized to 10s); win/loss uses"
          " finalized Binance 1h resolutions; 15m trades have no resolution file and are excluded from PnL.")
    ok = summary["v3.3"]["qualified"] > 0
    verdict("1_replay", ok, f"v3.3 qualified {summary['v3.3']['qualified']} vs v3.2 {summary['v3.2']['qualified']} (no starvation)" if ok else "v3.3 filter starvation")
    return summary


# ======================================================================================
# 2. HOT-PATH LATENCY BENCHMARK
# ======================================================================================
def run_latency() -> None:
    hdr("2. HOT-PATH LATENCY BENCHMARK  (100 iterations each; post_order is an in-process stub - NOTHING is sent)")
    from urllib3.connection import HTTPConnection
    import src.polymarket_research.polymarket_live_executor as ex

    opts = HTTPConnection.default_socket_options
    nodelay = (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) in opts
    keep = (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1) in opts
    print(f"  TCP_NODELAY in HTTPConnection.default_socket_options: {nodelay} | SO_KEEPALIVE: {keep}")

    # Real EIP-712 signing with a real (offline) ClobClient; post_order is stubbed BEFORE any use.
    from dotenv import load_dotenv
    load_dotenv(PIPELINE_ROOT / ".env")
    from py_clob_client_v2.client import ClobClient
    from py_clob_client_v2.clob_types import PartialCreateOrderOptions, OrderType
    pk = os.getenv("POLYGON_PRIVATE_KEY", "").strip()
    funder = os.getenv("POLYGON_FUNDER_ADDRESS", "").strip()
    client = ClobClient("https://clob.polymarket.com", key=pk, chain_id=137, signature_type=3, funder=funder)
    posted = []

    def _stub_post(order, order_type=None, post_only=False, defer_exec=False):
        posted.append(order)
        return {"orderID": f"STUB_{len(posted)}", "status": "matched", "success": True}

    client.post_order = _stub_post  # instance-level override: real network POST is impossible
    assert client.post_order is _stub_post

    token = None
    try:
        with open(TRIGGERS, "rb") as f:
            f.seek(max(0, TRIGGERS.stat().st_size - 400_000))
            for line in f.read().splitlines()[1:]:
                try:
                    token = orjson.loads(line)["pre_shock_features_t0"]["UP"]["token_id"] or token
                except Exception:
                    pass
    except Exception:
        pass
    token = token or "1" * 70
    opts_v2 = PartialCreateOrderOptions(tick_size="0.01", neg_risk=False, version=2)
    # warm-up (resolves any one-time client version/metadata caches)
    try:
        ex._sign_and_post_single_hop(client, None, token, 0.70, 31.0, "BUY", OrderType.FAK, opts_v2, {})
    except Exception as e:
        print(f"  [WARN] warm-up sign failed ({e}); latency numbers may be unavailable")

    cold, hot, hits = [], [], 0
    for _ in range(100):
        t = time.perf_counter()
        ex._sign_and_post_single_hop(client, None, token, 0.70, 31.0, "BUY", OrderType.FAK, opts_v2, {})
        cold.append((time.perf_counter() - t) * 1000.0)
    cache = ex.PreSignedOrderLadderCache(ttl_seconds=300.0)
    for i in range(100):
        signed = ex._safe_create_order(client.create_order, ex.OrderArgsV2(price=0.70, size=31.0, side="BUY", token_id=token), opts_v2)
        cache.store_presigned_order(token, 0.70, 31.0, signed)
        t = time.perf_counter()
        r = ex._sign_and_post_single_hop(client, cache, token, 0.70, 31.0, "BUY", OrderType.FAK, opts_v2, {})
        hot.append((time.perf_counter() - t) * 1000.0)
        hits += int(r["cache_hit"])
    reuse_blocked = cache.get_presigned_order(token, 0.70, 31.0) is None
    frac_blocked = cache.get_presigned_order(token, 0.70, 31.43) is None and not cache.store_presigned_order(token, 0.70, 31.43, {"x": 1})
    print(f"  single-hop cold_sign_ms : mean {mean(cold):.3f} | p50 {median(cold):.3f} | p99 {sorted(cold)[98]:.3f}")
    print(f"  single-hop presigned_ms : mean {mean(hot):.4f} | p50 {median(hot):.4f} | p99 {sorted(hot)[98]:.4f}  (hits {hits}/100)")
    print(f"  Signed-order single-use enforced (no re-post of consumed order): {reuse_blocked}")
    print(f"  Fractional-size orders never cached/served (integer-share invariant): {frac_blocked}")
    print(f"  Stubbed posts captured: {len(posted)} (0 network orders)")

    sample = TRIGGERS.open("rb").readline()
    obj = json.loads(sample)
    n = 2000
    t = time.perf_counter(); [json.loads(sample) for _ in range(n)]; jl = (time.perf_counter() - t) / n * 1000
    t = time.perf_counter(); [orjson.loads(sample) for _ in range(n)]; ol = (time.perf_counter() - t) / n * 1000
    t = time.perf_counter(); [json.dumps(obj) for _ in range(n)]; jd = (time.perf_counter() - t) / n * 1000
    t = time.perf_counter(); [orjson.dumps(obj) for _ in range(n)]; od = (time.perf_counter() - t) / n * 1000
    print(f"  trigger parse  json {jl:.4f}ms vs orjson {ol:.4f}ms ({jl / max(ol, 1e-9):.1f}x) | "
          f"serialize json {jd:.4f}ms vs orjson {od:.4f}ms ({jd / max(od, 1e-9):.1f}x)  [{len(sample)} B line]")

    from src.polymarket_research.polymarket_live_harvester import read_fast_tick
    with tempfile.TemporaryDirectory(dir="/dev/shm" if Path("/dev/shm").is_dir() else None) as td:
        os.environ["PM_FAST_TICK_DIR"] = td
        snap = {"ts": time.time() + 3600, "spot": 1.0, "UP": {"best_bid": 0.5, "best_ask": 0.51, "token_id": "x"}, "DOWN": {}}
        Path(td, "pm_fast_tick_BTC.json").write_bytes(orjson.dumps(snap))
        lat = []
        for _ in range(1000):
            t = time.perf_counter()
            assert read_fast_tick("BTC", max_age_sec=1e9) is not None
            lat.append((time.perf_counter() - t) * 1000.0)
        os.environ.pop("PM_FAST_TICK_DIR", None)
    shm_mean = mean(lat)
    shm_p50 = sorted(lat)[500]
    print(f"  /dev/shm read_fast_tick: mean {shm_mean:.4f}ms | p50 {shm_p50:.4f}ms | p99 {sorted(lat)[989]:.4f}ms (target p50 < 0.05ms)")
    ok = nodelay and keep and hits == 100 and reuse_blocked and frac_blocked and mean(hot) < mean(cold) and shm_p50 < 0.05
    verdict("2_latency", ok, f"presigned {mean(hot):.3f}ms vs cold {mean(cold):.3f}ms; shm p50 {shm_p50:.4f}ms (mean {shm_mean:.4f}ms)")


# ======================================================================================
# 3. ADVERSARIAL SALVAGE PATHS
# ======================================================================================
def _mk_pos(now_ts, **kw):
    base = {
        "trade_id": kw.get("tid", "POS"), "market_id": "MKT", "token_id": "TOK_UP", "target_token": "UP",
        "asset": "BTC", "entry_price": 0.65, "entry_shares": 30.0, "remaining_shares": 30.0,
        "candle_open_spot": 60000.0, "candle_expiry_ts": now_ts + 600.0, "exit_order_id": "order_tp",
        "target_exit_price": 0.98, "status": "EXIT_RESTING", "notional_usd": 19.5,
    }
    base.update(kw.get("extra", {}))
    return base


async def _run_path(name, pos, spot, book, unwind_px, now_ts, tmp, maker_fill=None):
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    with patch("src.polymarket_research.polymarket_live_harvester.DATA_DIR", tmp), \
         patch("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp / "state.json"):
        h = PolymarketLiveHarvester(dry_run=True)
        h.state_file = tmp / "state.json"
        h.active_positions = {pos["trade_id"]: pos}
        h.get_reference_spot_price = MagicMock(return_value=spot)
        ex = h.executor
        ex.get_market_book_async = AsyncMock(return_value=book)
        ex.cancel_order = MagicMock(return_value={"success": True})
        ex.release_inventory = MagicMock()
        ex.post_maker_exit_order = MagicMock(return_value={"success": True, "orderID": "MAKER_3S"})
        ex.get_order_fill_summary = MagicMock(return_value=maker_fill)
        ex.execute_unwind_order = MagicMock(return_value={
            "order_id": "FAK_UNWIND", "status": "FILLED", "filled_shares": pos["remaining_shares"],
            "avg_fill_price": unwind_px, "success": True})
        ex.invalidate_collateral_cache = MagicMock()
        real_sleep = asyncio.sleep

        async def fast_sleep(d, *a, **k):
            return await real_sleep(0)
        with patch("time.time", return_value=now_ts), patch("asyncio.sleep", side_effect=fast_sleep):
            await h.check_resolutions_and_manage_positions()
        return h, ex


def run_salvage() -> None:
    hdr("3. ADVERSARIAL SALVAGE & ANTI-WICK SIMULATION  (dry-run harvester, mocked executor, temp state dir)")
    os.environ.pop("PYTEST_CURRENT_TEST", None)
    now = 1_800_000_000.0
    results = {}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # (A) Stop-hunt wick: wrong side 0.10% for 25s > 18s, but spot rebounding +0.05% over 15s -> HOLD
        pos = _mk_pos(now, tid="A_WICK", extra={"opposite_breakout_start_ts": now - 25.0,
                                                 "spot_vel_history": [[now - 15.0, 59910.0]]})
        h, ex = asyncio.run(_run_path("A", pos, 59940.0, {"bids": [{"price": "0.40", "size": "100"}], "asks": [{"price": "0.42", "size": "100"}]}, 0.40, now, tmp))
        a_ok = (not ex.execute_unwind_order.called) and (not ex.cancel_order.called)
        print(f"  (A) Stop-hunt wick  v15s=+0.050%  wrong-side=0.10% for 25s (Zone2 base 18s): unwind_called={ex.execute_unwind_order.called} -> {'HELD (0 false stops)' if a_ok else 'FALSE STOP'}")
        results["A"] = a_ok

        # (B) Fast breakdown: v15s=-0.12%, bid 0.38<=0.42, 10s elapsed >= 9s halved Zone2 timer -> SALVAGE
        pos = _mk_pos(now, tid="B_CRASH", extra={"opposite_breakout_start_ts": now - 10.0,
                                                  "spot_vel_history": [[now - 15.0, 59952.0]]})
        h, ex = asyncio.run(_run_path("B", pos, 59880.0, {"bids": [{"price": "0.38", "size": "100"}], "asks": [{"price": "0.40", "size": "100"}]}, 0.38, now, tmp))
        b_ok = ex.execute_unwind_order.called
        print(f"  (B) Fast breakdown  v15s=-0.120%  bid=0.38  elapsed 10s vs halved 9s: unwind_called={b_ok} -> {'FAST SALVAGE' if b_ok else 'NOT TRIGGERED'}")
        results["B"] = b_ok

        # (C) Wide spread 0.10 >= 0.04, TTE 600 > 60: 3.0s post_only maker -> unfilled -> cancel -> FAK
        pos = _mk_pos(now, tid="C_MAKER", extra={"opposite_breakout_start_ts": now - 30.0,
                                                  "spot_vel_history": [[now - 15.0, 59940.0]]})
        h, ex = asyncio.run(_run_path("C", pos, 59930.0, {"bids": [{"price": "0.36", "size": "100"}], "asks": [{"price": "0.46", "size": "100"}]}, 0.36, now, tmp,
                                      maker_fill=None))
        maker_args = ex.post_maker_exit_order.call_args
        maker_px = maker_args.kwargs.get("price") if maker_args else None
        exp_px = round(min(0.46 - 0.01, 0.36 + max(0.01, 0.40 * 0.10)), 2)
        cancelled_maker = any(c.args and c.args[0] == "MAKER_3S" for c in ex.cancel_order.call_args_list)
        c_ok = bool(maker_args) and maker_px == exp_px and cancelled_maker and ex.execute_unwind_order.called
        print(f"  (C) Wide spread 0.10: maker posted @ {maker_px} (expected {exp_px}), held 3.0s, cancelled={cancelled_maker}, FAK escalation={ex.execute_unwind_order.called}")
        results["C"] = c_ok

        # (D) Peak-bid ratchet: entry 0.66, peak 0.92 -> floor 0.87; bid 0.85 for >=4s -> lock +19c
        pos = _mk_pos(now, tid="D_RATCHET", extra={"entry_price": 0.66, "max_seen_bid": 0.92,
                                                    "trail_stop_detected_ts": now - 5.0,
                                                    "trailing_ratchet_detected_ts": now - 5.0,
                                                    "candle_open_spot": 59800.0,
                                                    "spot_vel_history": [[now - 15.0, 59950.0]]})
        h, ex = asyncio.run(_run_path("D", pos, 59950.0, {"bids": [{"price": "0.85", "size": "100"}], "asks": [{"price": "0.87", "size": "100"}]}, 0.85, now, tmp))
        d_ok = ex.execute_unwind_order.called
        print(f"  (D) Trailing ratchet: peak 0.92 -> floor 0.87, bid 0.85 for 5s>=4s: unwind_called={d_ok} -> locks {0.85 - 0.66:+.2f}/share at $0.85")
        results["D"] = d_ok
    verdict("3_salvage", all(results.values()), " ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in results.items()))


# ======================================================================================
# 4. KELLY SIZING TABLE
# ======================================================================================
def run_kelly() -> None:
    hdr("4. CORRELATED MULTI-ASSET KELLY SIZING TABLE  ($91.67 bankroll, p_true=0.74, entry=$0.65)")
    from src.polymarket_research.polymarket_live_harvester import compute_correlated_truncated_kelly_size as K
    exp = 1_800_003_600.0
    base = dict(live_equity=91.67, p_win=0.74, entry_px=0.65, cand_expiry_ts=exp, min_lot_usd=12.0, max_ticket_cap=50.0)
    b = K(**base, kelly_multiplier=1.00, active_positions={}, cand_direction="UP")
    a = K(**base, kelly_multiplier=1.15, active_positions={}, cand_direction="UP")
    other_up = {"BTC1": {"target_token": "UP", "candle_expiry_ts": exp, "remaining_shares": 33.0, "status": "FILLED"}}
    c_b = K(**base, kelly_multiplier=1.00, active_positions=other_up, cand_direction="UP")
    c_a = K(**base, kelly_multiplier=1.15, active_positions=other_up, cand_direction="UP")
    opp = K(**base, kelly_multiplier=1.00, active_positions=other_up, cand_direction="DOWN")
    print(f"  (1) Standalone Tier B                          : ${b:6.2f}   (spec ~$22.00)")
    print(f"  (2) Standalone Tier A+ (1.15x)                 : ${a:6.2f}   (spec ~$24.50)")
    print(f"  (3) Correlated 2nd pos same hour, Tier B       : ${c_b:6.2f}   (raw {91.67 * 0.24 * 0.5405:.2f} -> $12 min-lot floor)")
    print(f"      Correlated 2nd pos same hour, Tier A+      : ${c_a:6.2f}   (spec ~$12.50-$13.50; haircut x{1 / 1.85:.4f})")
    print(f"  (4) Opposing cross-asset direction, same hour  : ${opp:6.2f}   (spec $0.00 vetoed)")
    ok = abs(b - 22.0) < 0.01 and 24.0 <= a <= 26.0 and 12.0 <= c_b <= 13.7 and 12.0 <= c_a <= 14.0 and opp == 0.0
    verdict("4_kelly", ok, f"B ${b:.2f} | A+ ${a:.2f} | corr ${c_b:.2f}/${c_a:.2f} | opposing ${opp:.2f}")


# ======================================================================================
# 5. LIVE PROBE
# ======================================================================================
async def _probe():
    import aiohttp
    import websockets
    from src.polymarket_research import polymarket_terminal_recorder as rec
    out = {}
    for asset in ("BTC", "ETH"):
        r = rec.PolymarketDualFeed1HRecorder.__new__(rec.PolymarketDualFeed1HRecorder)
        r.asset, r.session = asset, None
        r.binance_symbol = rec.ASSET_CONFIGS[asset]["binance_symbol"]
        try:
            m = await asyncio.wait_for(r.discover_nearest_15m_market(), timeout=15)
        finally:
            if r.session:
                await r.session.close()
        out[f"15m_{asset}"] = m
    cb = {}
    try:
        async with websockets.connect(rec.COINBASE_WS_URL, ping_interval=20) as ws:
            await ws.send(json.dumps({"type": "subscribe", "product_ids": ["BTC-USD", "ETH-USD"], "channels": ["ticker"]}))
            end = time.time() + 3.0
            while time.time() < end and len(cb) < 2 or time.time() < end:
                try:
                    d = json.loads(await asyncio.wait_for(ws.recv(), timeout=max(0.05, end - time.time())))
                except asyncio.TimeoutError:
                    break
                if d.get("type") == "ticker":
                    cb[d["product_id"]] = float(d["price"])
    except Exception as e:
        out["cb_err"] = str(e)
    out["cb"] = cb
    bn = {}
    async with aiohttp.ClientSession() as s:
        for sym in ("BTCUSDT", "ETHUSDT"):
            try:
                async with s.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    bn[sym] = float((await resp.json())["price"])
            except Exception as e:
                bn[sym] = None
                out["bn_err"] = str(e)
    out["bn"] = bn
    return out


def run_probe() -> None:
    hdr("5. LIVE GAMMA 15m MARKET DISCOVERY + 3s COINBASE / BINANCE VENUE PROBE")
    out = asyncio.run(_probe())
    ok15 = 0
    for asset in ("BTC", "ETH"):
        m = out.get(f"15m_{asset}")
        if m:
            ok15 += 1
            secs = (m["end_dt"].timestamp() - time.time())
            print(f"  15m {asset}: {m['title']!r} id={m['market_id']} slug={m['series_slug']} TTE={secs:.0f}s "
                  f"open=${m.get('finalized_15m_open', 0):,.2f} fee={m['fee_metadata']['fee_rate_market']}")
        else:
            print(f"  15m {asset}: NOT FOUND via btc/eth-up-or-down-15m or btc/eth-15m series slugs")
    cb, bn = out.get("cb", {}), out.get("bn", {})
    div_ok = 0
    for a, prod, sym in (("BTC", "BTC-USD", "BTCUSDT"), ("ETH", "ETH-USD", "ETHUSDT")):
        c, b = cb.get(prod), bn.get(sym)
        if c and b:
            div_ok += 1
            print(f"  {a}: Coinbase {prod} ${c:,.2f} | Binance {sym} ${b:,.2f} | venue_divergence_bps = {(b - c) / c * 1e4:+.2f}")
        else:
            print(f"  {a}: Coinbase={c} Binance={b} (fail-open: veto disabled when Coinbase is unavailable) {out.get('cb_err', '')}")
    verdict("5_probe", ok15 == 2 and div_ok == 2, f"15m markets {ok15}/2, venue prices {div_ok}/2")


# ======================================================================================
# 6. PYTEST + 7. PROCESS SAFETY
# ======================================================================================
def run_pytest() -> None:
    hdr("6. COMPLETE PYTEST SUITE  (venv/bin/pytest -q tests/)")
    p = subprocess.run([str(PIPELINE_ROOT / "venv/bin/pytest"), "-q", "-p", "no:cacheprovider", "tests/",
                        # these 3 modules import code committed as *.py.disabled (negrisk_scanner, hl_isolated_ratchet_shadow)
                        "--ignore=tests/test_audit_remediation_v2.py",
                        "--ignore=tests/test_institutional_expansion_sandbox.py",
                        "--ignore=tests/test_v31_conformance.py"],
                       cwd=PIPELINE_ROOT, capture_output=True, text=True)
    tail = [l for l in p.stdout.strip().splitlines() if l.strip()][-6:]
    for l in tail:
        print("  " + l)
    verdict("6_pytest", p.returncode == 0, tail[-1] if tail else "no output")


def run_process_check() -> None:
    hdr("7. LIVE PROCESS SAFETY CHECK")
    out = subprocess.run(["ps", "-eo", "pid,lstart,cmd"], capture_output=True, text=True).stdout.splitlines()
    rows = [l for l in out if any(k in l for k in ("polymarket_live_harvester.py", "run_polymarket_harvester.sh",
                                                     "polymarket_paper_trader.py", "polymarket_terminal_recorder.py"))
            and "grep" not in l]
    for r in rows:
        print("  " + r[:170])
    ks = (DATA / "KILL_SWITCH").exists()
    st = json.loads((DATA / "live_harvester_state.json").read_text())
    print(f"  KILL_SWITCH present: {ks} | live active_positions: {len(st.get('active_positions', {}))} | "
          f"pending_entry_intents: {len(st.get('pending_entry_intents', {}) or {})}")
    harv = any("polymarket_live_harvester.py" in r for r in rows)
    verdict("7_process", harv and ks, "harvester running (halted by KILL_SWITCH), untouched by audit")


def main():
    sections = sys.argv[1:] or ["1", "2", "3", "4", "5", "6", "7"]
    fns = {"1": run_replay, "2": run_latency, "3": run_salvage, "4": run_kelly, "5": run_probe, "6": run_pytest, "7": run_process_check}
    for s in sections:
        try:
            fns[s]()
        except Exception as e:
            import traceback
            traceback.print_exc()
            RESULTS[s] = f"FAIL - exception: {e}"
    hdr("PRE-FLIGHT AUDIT SUMMARY")
    for k, v in RESULTS.items():
        print(f"  {k:<12} {v}")
    sys.exit(0 if all(v.startswith("PASS") for v in RESULTS.values()) else 1)


if __name__ == "__main__":
    main()
