#!/usr/bin/env python3
"""
HONEST ZERO-LOOKAHEAD PURGED WALK-FORWARD OPTIMIZER (WFO) — POLYMARKET v3.7
===========================================================================
Addresses all historical backtest-to-live parity & domain-selection flaws:
  1. Official Gamma / Chainlink UMA ground-truth (`verified_gamma_resolutions.json`, 2,199 markets)
     — zero reliance on recorder's 36s Binance-spot fallback (`60` proven oracle mismatches eliminated).
  2. Real Finland `+500ms` CLOB execution latency (`424ms` measured median RTT) + `+1000ms` stress test,
     enforcing `FAK_KILLED_NO_MATCH` when `ask_exec > limit_px` (preserving adverse selection).
  3. Exact V2 taker fee (`shares * 0.07 * p * (1 - p)`) on every taker leg and `0%` on passive GTC maker legs.
  4. Real L2 bid-book walking (`vwap_$20` / top-5 bids) on stop/salvage/ratchet exits — ZERO `$0.40` magic floor,
     plus dense `impulse_response` (`100ms, 250ms, 500ms, 1s, 5s, 30s`) + hourly L2 + `exp306` boundary paths.
  5. Two-sided book check for passive Maker GTC exits (`bid >= tp_px` with valid spread).
  6. Strictly causal rolling volatility & de-meaned Coinbase-Binance venue divergence.
  7. Chronological Purged Walk-Forward Split:
       Train (50%) -> 2h Purge -> Validation (25%) -> 2h Purge -> Sealed Holdout (25%)
     Selection uses ONLY Train + Validation + 4 Internal Purged Dev Sub-Folds (worst-split Sharpe/t-stat/PF
     objective, preventing trade-spam volume bias). Sealed Holdout is evaluated ONCE after selection.
"""

from __future__ import annotations

import bisect
import collections
import gzip
import json
import math
import multiprocessing as mp
import os
import pickle
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from src.polymarket_research.orderflow_wfo_simulators import calibrate_d1_box_wfo, simulate_microclip_cascade_entry
except ImportError:
    calibrate_d1_box_wfo = None  # type: ignore
    simulate_microclip_cascade_entry = None  # type: ignore

try:
    import orjson as _orjson

    def _loads(line: str) -> Any:
        return _orjson.loads(line)
except ImportError:
    def _loads(line: str) -> Any:
        return json.loads(line)

PIPELINE_ROOT = Path("/home/skybullet1987/quant_pipeline")
DATA_DIR = PIPELINE_ROOT / "data" / "polymarket"
OUT_JSON = DATA_DIR / "honest_wfo_results.json"
CACHE_PKL = Path("/tmp/pm_wfo_v40_dataset.pkl")

FEE_RATE = 0.07


def taker_fee_per_share(px: float, fee_rate: float = FEE_RATE) -> float:
    px_c = max(0.001, min(0.999, px))
    return fee_rate * px_c * (1.0 - px_c)


def walk_bids_vwap(raw_bids: List[Any], best_bid: float, target_shares: float = 22.0) -> float:
    """Walks real L2 top-5 bids for `target_shares`; falls back conservatively if depth is thin."""
    if not raw_bids:
        return max(0.0, best_bid - 0.01) if best_bid > 0.02 else best_bid
    rem = target_shares
    cash = 0.0
    filled = 0.0
    for lvl in raw_bids:
        if not isinstance(lvl, (list, tuple)) or len(lvl) < 2:
            continue
        px, sz = float(lvl[0]), float(lvl[1])
        if px <= 0 or sz <= 0:
            continue
        take = min(rem, sz)
        cash += take * px
        filled += take
        rem -= take
        if rem <= 1e-6:
            break
    if filled <= 0:
        return 0.0
    if rem > 1e-6:
        tail_px = max(0.01, float(raw_bids[-1][0]) - 0.03)
        cash += rem * tail_px
        filled += rem
    return round(cash / filled, 4)


def infer_asset_and_horizon(d: Dict[str, Any]) -> Tuple[str, str]:
    title = str(d.get("title") or "")
    asset = str(d.get("asset") or "").upper()
    if not asset:
        if "Ethereum" in title or "ETH" in title:
            asset = "ETH"
        elif "Solana" in title or "SOL" in title:
            asset = "SOL"
        else:
            asset = "BTC"
    hz = str(d.get("horizon") or d.get("candle_interval") or "").lower()
    if not hz:
        if "above" in title.lower() or "strike" in title.lower():
            hz = "daily"
        elif "-" in title.split("ET")[0].split(",")[-1]:
            hz = "15m"
        else:
            hz = "1h"
    if "15" in hz:
        hz = "15m"
    elif "1h" in hz or "hour" in hz or "60" in hz:
        hz = "1h"
    return asset, hz


def iter_jsonl_lines_with_archives(data_dir: Path, filename: str) -> Iterator[str]:
    """Streams chronological `<stem>__20*.jsonl.gz` cold archives followed by the live hot `.jsonl` tail."""
    stem = Path(filename).stem
    arch_dir = data_dir / "archive"
    prefix = f"{stem}__20"
    if arch_dir.is_dir():
        for gz_path in sorted(arch_dir.glob(f"{stem}__*.jsonl.gz")):
            if not gz_path.name.startswith(prefix):
                continue
            try:
                with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as gf:
                    for line in gf:
                        yield line
            except Exception:
                continue
    hot_path = data_dir / filename
    if hot_path.exists():
        with open(hot_path, "r", encoding="utf-8", errors="replace") as hf:
            for line in hf:
                yield line


def load_dataset(use_cache: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if use_cache and CACHE_PKL.exists():
        try:
            t0_c = time.time()
            with open(CACHE_PKL, "rb") as f:
                cands, meta = pickle.load(f)
            meta["cache_hit_sec"] = round(time.time() - t0_c, 2)
            return cands, meta
        except Exception:
            pass

    t_start = time.time()
    ver_path = DATA_DIR / "verified_gamma_resolutions.json"
    verified: Dict[str, Dict[str, Any]] = json.loads(ver_path.read_text(encoding="utf-8"))

    # Market trajectory store: mid -> list of (ts, spot, up_bid, up_ask, dn_bid, dn_ask, up_bid_vwap, dn_bid_vwap)
    market_paths: Dict[str, List[Tuple[float, float, float, float, float, float, float, float]]] = collections.defaultdict(list)
    market_expiry: Dict[str, float] = {}

    # 1. Load shock_responses (BTC, ETH, SOL) for exact +500ms / +1000ms quotes + full impulse trajectory points
    sr_index: Dict[str, List[Tuple[float, Dict[str, Any]]]] = collections.defaultdict(list)
    sr_count = 0
    ir_offsets = {"100ms": 0.1, "250ms": 0.25, "500ms": 0.5, "1s": 1.0, "5s": 5.0, "30s": 30.0}
    for sr_name in ("shock_responses.jsonl", "shock_responses_eth.jsonl", "shock_responses_sol.jsonl"):
        for line in iter_jsonl_lines_with_archives(DATA_DIR, sr_name):
            if not line.strip():
                continue
            try:
                d = _loads(line)
            except Exception:
                continue
            mid = str(d.get("market_id") or "")
            if mid not in verified:
                continue
            t0 = float(d.get("t0_unix") or 0.0)
            ir = d.get("impulse_response") or {}
            if t0 > 0 and ir:
                sr_index[mid].append((t0, ir))
                sr_count += 1
                base_sp = float(d.get("spot_at_t0") or d.get("spot_at_shock") or 0.0)
                for h_key, def_dt in ir_offsets.items():
                    step = ir.get(h_key)
                    if not step:
                        continue
                    dt = float(step.get("elapsed_sec") or def_dt)
                    u_ask = float(step.get("up_ask") or 1.0)
                    u_mid = float(step.get("up_mid") or 0.0)
                    u_bid = max(0.0, round(2.0 * u_mid - u_ask, 3)) if (u_mid > 0 and u_ask < 1.0) else 0.0
                    d_ask = float(step.get("down_ask") or 1.0)
                    d_mid = float(step.get("down_mid") or 0.0)
                    d_bid = max(0.0, round(2.0 * d_mid - d_ask, 3)) if (d_mid > 0 and d_ask < 1.0) else 0.0
                    sp = float(step.get("binance_spot") or base_sp)
                    market_paths[mid].append((
                        t0 + dt, sp, u_bid, u_ask, d_bid, d_ask,
                        max(0.0, u_bid - 0.005), max(0.0, d_bid - 0.005)
                    ))

    for mid in sr_index:
        sr_index[mid].sort(key=lambda x: x[0])

    # 2. Load 1s hourly L2 telemetry (downsample to 2s to keep RAM compact & fast while preserving peaks/stops)
    telem_rows = 0
    for t_name in ("polymarket_hourly_telemetry.jsonl", "polymarket_hourly_telemetry_eth.jsonl", "polymarket_hourly_telemetry_sol.jsonl"):
        last_ts_by_mid: Dict[str, float] = {}
        for line in iter_jsonl_lines_with_archives(DATA_DIR, t_name):
            if not line.strip():
                continue
            try:
                d = _loads(line)
            except Exception:
                continue
            mid = str(d.get("market_id") or "")
            if mid not in verified:
                continue
            ts = float(d.get("timestamp_unix") or 0.0)
            if ts - last_ts_by_mid.get(mid, 0.0) < 2.0 and float(d.get("seconds_to_expiry") or 999) > 90.0:
                continue
            last_ts_by_mid[mid] = ts
            tte = float(d.get("seconds_to_expiry") or 0.0)
            if tte > 0:
                market_expiry[mid] = ts + tte
            sp = float(d.get("binance_spot") or 0.0)
            up = d.get("UP") or {}
            dn = d.get("DOWN") or {}
            u_bid = float(up.get("best_bid") or 0.0)
            u_ask = float(up.get("best_ask") or 1.0)
            d_bid = float(dn.get("best_bid") or 0.0)
            d_ask = float(dn.get("best_ask") or 1.0)
            u_vwap = walk_bids_vwap(up.get("raw_top_bids") or [], u_bid)
            d_vwap = walk_bids_vwap(dn.get("raw_top_bids") or [], d_bid)
            market_paths[mid].append((ts, sp, u_bid, u_ask, d_bid, d_ask, u_vwap, d_vwap))
            telem_rows += 1

    # 3. Load exp306_realtime_boundary_merge.jsonl (dense final-60s quotes for 15m and 1h!)
    for line in iter_jsonl_lines_with_archives(DATA_DIR, "exp306_realtime_boundary_merge.jsonl"):
        if not line.strip():
            continue
        try:
            d = _loads(line)
        except Exception:
            continue
        mid = str(d.get("market_id") or "")
        if mid not in verified:
            continue
        ts = float(d.get("timestamp_unix") or 0.0)
        u_ask = float(d.get("ask_up") or 1.0)
        d_ask = float(d.get("ask_down") or 1.0)
        # v3.8 F-12a Fix: Never fabricate u_ask - 0.01 synthetic bids when complement ask is missing (1.0)
        u_bid = max(0.0, round(1.0 - d_ask, 3)) if d_ask < 1.0 else 0.0
        d_bid = max(0.0, round(1.0 - u_ask, 3)) if u_ask < 1.0 else 0.0
        market_paths[mid].append((ts, 0.0, u_bid, u_ask, d_bid, d_ask, max(0.0, u_bid - 0.01), max(0.0, d_bid - 0.01)))

    # 4. Load all raw triggers from live_shock_triggers.jsonl (adds L2 snapshots + builds candidate list)
    raw_triggers: List[Tuple[float, str, str, str, float, Dict[str, Any]]] = []
    for line in iter_jsonl_lines_with_archives(DATA_DIR, "live_shock_triggers.jsonl"):
        if not line.strip():
            continue
        try:
            d = _loads(line)
        except Exception:
            continue
        mid = str(d.get("market_id") or "")
        if mid not in verified:
            continue
        asset, hz = infer_asset_and_horizon(d)
        if hz not in ("15m", "1h") or asset not in ("BTC", "ETH", "SOL"):
            continue
        t0 = float(d.get("t0_unix") or 0.0)
        tte = float(d.get("seconds_to_expiry") or 0.0)
        if t0 <= 0 or tte <= 5.0:
            continue
        exp_ts = float(d.get("candle_expiry_ts") or d.get("expiry_ts") or (t0 + tte))
        market_expiry[mid] = exp_ts
        pre = d.get("pre_shock_features_t0") or {}
        up = pre.get("UP") or {}
        dn = pre.get("DOWN") or {}
        sp = float(d.get("spot_at_t0") or 0.0)
        u_bid = float(up.get("best_bid") or 0.0)
        u_ask = float(up.get("best_ask") or 1.0)
        d_bid = float(dn.get("best_bid") or 0.0)
        d_ask = float(dn.get("best_ask") or 1.0)
        u_vwap_b = walk_bids_vwap(up.get("raw_top_bids") or [], u_bid)
        d_vwap_b = walk_bids_vwap(dn.get("raw_top_bids") or [], d_bid)
        market_paths[mid].append((t0, sp, u_bid, u_ask, d_bid, d_ask, u_vwap_b, d_vwap_b))
        raw_triggers.append((t0, asset, hz, mid, exp_ts, d))

    raw_triggers.sort(key=lambda x: x[0])

    # Sort & deduplicate market_paths, forward-filling spot where 0.0 (from exp306 rows)
    market_ts_index: Dict[str, List[float]] = {}
    for mid, pts in market_paths.items():
        pts.sort(key=lambda x: x[0])
        cleaned = []
        last_sp = 0.0
        last_t = -1.0
        for pt in pts:
            ts, sp, ub, ua, db, da, uvb, dvb = pt
            if sp > 0:
                last_sp = sp
            else:
                sp = last_sp
            if ts - last_t < 0.05 and cleaned:
                cleaned[-1] = (ts, sp, ub, ua, db, da, uvb, dvb)
            else:
                cleaned.append((ts, sp, ub, ua, db, da, uvb, dvb))
                last_t = ts
        market_paths[mid] = cleaned
        market_ts_index[mid] = [p[0] for p in cleaned]

    # Causal rolling trackers per asset
    venue_hist: Dict[str, collections.deque] = {a: collections.deque(maxlen=200) for a in ("BTC", "ETH", "SOL")}
    spot_5m_hist: Dict[str, collections.deque] = {a: collections.deque(maxlen=60) for a in ("BTC", "ETH", "SOL")}
    last_5m_bucket: Dict[str, int] = {a: 0 for a in ("BTC", "ETH", "SOL")}
    rolling_sigma_1h: Dict[str, float] = {"BTC": 0.0048, "ETH": 0.0062, "SOL": 0.0090}

    candidates: List[Dict[str, Any]] = []
    for t0, asset, hz, mid, exp_ts, d in raw_triggers:
        sp = float(d.get("spot_at_t0") or 0.0)
        if sp <= 0:
            continue

        b5 = int(t0 // 300)
        if b5 > last_5m_bucket[asset]:
            if spot_5m_hist[asset]:
                prev_sp = spot_5m_hist[asset][-1]
                ret_5m = math.log(sp / prev_sp)
                var_1h_obs = 12.0 * (ret_5m ** 2)
                cur_var = rolling_sigma_1h[asset] ** 2
                new_var = 0.94 * cur_var + 0.06 * var_1h_obs
                rolling_sigma_1h[asset] = max(0.0020, min(0.0250, math.sqrt(new_var)))
            spot_5m_hist[asset].append(sp)
            last_5m_bucket[asset] = b5

        raw_vdiv = d.get("venue_divergence_bps")
        vdiv_centered = 0.0
        if raw_vdiv is not None:
            rv = float(raw_vdiv)
            if len(venue_hist[asset]) >= 20:
                med_v = statistics.median(venue_hist[asset])
                vdiv_centered = rv - med_v
            venue_hist[asset].append(rv)

        shock_dir = str(d.get("shock_direction") or "").upper()
        if shock_dir not in ("BUY", "SELL"):
            continue
        side = "UP" if shock_dir == "BUY" else "DOWN"
        sign = 1.0 if side == "UP" else -1.0

        open_sp = float(d.get("candle_open_spot") or d.get("finalized_1h_open") or 0.0)
        if open_sp <= 0:
            continue
        twap_open = float(d.get("twap_60s_open") or open_sp)
        if twap_open <= 0:
            twap_open = open_sp

        pre = (d.get("pre_shock_features_t0") or {}).get(side) or {}
        ask_t0 = float(pre.get("best_ask") or 1.0)
        bid_t0 = float(pre.get("best_bid") or 0.0)
        if not (0.35 <= ask_t0 <= 0.96) or bid_t0 <= 0.0:
            continue
        spread_t0 = round(ask_t0 - bid_t0, 4)
        if spread_t0 < -0.001 or spread_t0 > 0.12:
            continue

        ask_sz = float(pre.get("ask_size_l1") or pre.get("ask_size") or 0.0)
        bid_sz = float(pre.get("bid_size_l1") or pre.get("bid_size") or 0.0)
        obi_l1 = float(pre.get("obi_l1") if pre.get("obi_l1") is not None else (pre.get("obi") or 0.0))
        age_ask_ms = float(pre.get("age_ask_ms") if pre.get("age_ask_ms") is not None else (pre.get("quote_age_ms") or 50.0))
        vwap20_t0 = float(pre.get("vwap_$20") or ask_t0)
        slip20_t0 = max(0.0, vwap20_t0 - ask_t0)

        tte = float(d.get("seconds_to_expiry") or (exp_ts - t0))
        sigma_1h = rolling_sigma_1h[asset]
        sigma_rem = max(0.00025, sigma_1h * math.sqrt(max(tte, 1.0) / 3600.0))

        cushion_open = sign * (sp - open_sp) / open_sp
        cushion_twap = sign * (sp - twap_open) / twap_open
        cushion_min = min(cushion_open, cushion_twap)
        # v3.8 F-11 / Blueprint 3 + v3.9 R07 Contract-Accurate Settlement Oracle:
        # - 1h Polymarket contracts settle strictly on Binance USDT 1H Open & Close (binance.com)
        # - 15m Polymarket contracts settle strictly on Chainlink USD 60s TWAP Data Stream (data.chain.link)
        vdiv_clamped_bps = max(-50.0, min(50.0, vdiv_centered))
        sp_cl_proxy = sp * (1.0 - 0.5 * (vdiv_clamped_bps / 10000.0))
        cushion_cl_proxy = min(
            sign * (sp_cl_proxy - open_sp) / open_sp,
            sign * (sp_cl_proxy - twap_open) / twap_open,
        )
        cushion_oracle = cushion_open if hz == "1h" else min(cushion_min, cushion_cl_proxy)
        z_cushion = cushion_min / sigma_rem
        z_cushion_cl = cushion_cl_proxy / sigma_rem
        z_oracle = cushion_oracle / sigma_rem

        shock_vol = float(d.get("shock_volume_100ms") or 0.0)
        shock_ofi = abs(float(d.get("shock_ofi") or 0.0))
        cb_move_2s = float(d.get("coinbase_move_bps_2s") or 0.0) * sign

        ask_500ms = None
        ask_1000ms = None
        sr_list = sr_index.get(mid)
        if sr_list:
            idx_sr = bisect.bisect_left(sr_list, (t0 - 0.30, {}))
            for j in range(idx_sr, min(len(sr_list), idx_sr + 3)):
                if abs(sr_list[j][0] - t0) <= 0.35:
                    ir = sr_list[j][1]
                    k_ask = "up_ask" if side == "UP" else "down_ask"
                    if ir.get("500ms") and ir["500ms"].get(k_ask):
                        ask_500ms = float(ir["500ms"][k_ask])
                    if ir.get("1s") and ir["1s"].get(k_ask):
                        ask_1000ms = float(ir["1s"][k_ask])
                    break

        pts = market_paths[mid]
        ts_list = market_ts_index[mid]
        idx_next = bisect.bisect_right(ts_list, t0 + 0.12)

        if ask_500ms is None:
            if idx_next < len(pts) and (pts[idx_next][0] - t0) <= 2.0:
                ask_500ms = pts[idx_next][3] if side == "UP" else pts[idx_next][5]
            else:
                jump = 0.01 if shock_vol >= 350_000 else 0.0
                if obi_l1 < -0.35:
                    jump += 0.01
                if ask_sz * ask_t0 < 25.0:
                    jump += 0.01
                ask_500ms = min(0.99, round(ask_t0 + jump, 4))

        if ask_1000ms is None:
            ask_1000ms = min(0.99, round(ask_500ms + (0.01 if shock_vol >= 500_000 else 0.0), 4))

        idx_p0 = bisect.bisect_right(ts_list, t0 + 0.45)
        raw_post = pts[idx_p0:]
        if len(raw_post) > 90:
            stride = max(1, len(raw_post) // 65)
            keep_idx = set(range(0, len(raw_post), stride))
            for k_i, p_row in enumerate(raw_post):
                if exp_ts - p_row[0] <= 75.0 or (p_row[0] - t0) <= 35.0:
                    keep_idx.add(k_i)
            b_col = 2 if side == "UP" else 4
            keep_idx.add(max(range(len(raw_post)), key=lambda i: raw_post[i][b_col]))
            keep_idx.add(min(range(len(raw_post)), key=lambda i: raw_post[i][b_col]))
            raw_post = [raw_post[i] for i in sorted(keep_idx)]

        compact_path = []
        strike_worst = open_sp if hz == "1h" else (max(open_sp, twap_open) if side == "UP" else min(open_sp, twap_open))
        idx_mc0 = bisect.bisect_right(ts_list, t0 + 0.04)
        idx_mc1 = bisect.bisect_right(ts_list, t0 + 5.50)
        micro_clips = [
            (
                round(p_ts - t0, 3),
                sign * (p_sp - strike_worst) / strike_worst if p_sp > 0 else cushion_oracle,
                ub if side == "UP" else db,
                ua if side == "UP" else da,
            )
            for p_ts, p_sp, ub, ua, db, da, _, _ in pts[idx_mc0:idx_mc1]
        ]
        for p_ts, p_sp, ub, ua, db, da, uvb, dvb in raw_post:
            tte_i = max(0.0, exp_ts - p_ts)
            b_i = ub if side == "UP" else db
            a_i = ua if side == "UP" else da
            vb_i = uvb if side == "UP" else dvb
            cush_i = sign * (p_sp - strike_worst) / strike_worst if p_sp > 0 else cushion_oracle
            compact_path.append((tte_i, cush_i, b_i, a_i, vb_i))

        gamma_winner = verified[mid]["winner"]
        gamma_won = (gamma_winner == side)
        oracle_mismatch = bool(verified[mid].get("oracle_mismatch", False))

        candidates.append({
            "event_id": str(d.get("event_id") or d.get("shock_id") or f"{mid}_{t0}"),
            "t0": t0,
            "exp_ts": exp_ts,
            "tte": tte,
            "asset": asset,
            "hz": hz,
            "mid": mid,
            "side": side,
            "ask_t0": ask_t0,
            "bid_t0": bid_t0,
            "spread_t0": spread_t0,
            "slip20_t0": slip20_t0,
            "l1_ask_usd": ask_t0 * ask_sz,
            "depth_ratio": (ask_t0 * ask_sz + bid_t0 * bid_sz) / 20.0,
            "obi_l1": obi_l1,
            "age_ask_ms": age_ask_ms,
            "cushion_open": cushion_open,
            "cushion_min": cushion_min,
            "cushion_cl_proxy": cushion_cl_proxy,
            "cushion_oracle": cushion_oracle,
            "z_cushion": z_cushion,
            "z_cushion_cl": z_cushion_cl,
            "z_oracle": z_oracle,
            "sigma_rem": sigma_rem,
            "shock_vol": shock_vol,
            "shock_ofi": shock_ofi,
            "vdiv_centered": vdiv_centered,
            "cb_move_2s": cb_move_2s,
            "ask_500ms": ask_500ms,
            "ask_1000ms": ask_1000ms,
            "micro_clips": micro_clips,
            "path": compact_path,
            "won": gamma_won,
            "oracle_mismatch": oracle_mismatch,
        })

    meta = {
        "verified_markets": len(verified),
        "shock_responses_indexed": sr_count,
        "telemetry_rows_loaded": telem_rows,
        "total_candidates": len(candidates),
        "load_sec": round(time.time() - t_start, 2),
    }
    if use_cache:
        try:
            with open(CACHE_PKL, "wb") as f:
                pickle.dump((candidates, meta), f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass
    return candidates, meta


def simulate_single_trade(cand: Dict[str, Any], cfg: Dict[str, Any], latency_mode: str = "500ms") -> Optional[Tuple[float, str, bool]]:
    res = simulate_single_trade_ex(cand, cfg, latency_mode=latency_mode)
    if res is None:
        return None
    return res[0], res[1], res[2]


def simulate_single_trade_ex(cand: Dict[str, Any], cfg: Dict[str, Any], latency_mode: str = "500ms") -> Optional[Tuple[float, str, bool, float]]:
    """
    Returns (pnl_per_dollar_notional, exit_reason, won_flag, release_ts) or None if filtered/unfilled.
    Models exact $20 reference ticket mechanics, V2 fees, 2-sided Maker TP, Ratchet, and Salvage.
    """
    if cand["asset"] not in cfg["assets"]:
        return None
    hz = cand["hz"]
    if hz not in cfg["horizons"]:
        return None
    tte = cand["tte"]
    if hz == "15m":
        if not (cfg["min_tte_15m"] <= tte <= cfg["max_tte_15m"]):
            return None
    else:
        if not (cfg["min_tte_1h"] <= tte <= cfg["max_tte_1h"]):
            return None

    ask_t0 = cand["ask_t0"]
    if not (cfg["min_px"] <= ask_t0 <= cfg["max_px"]):
        return None
    if cand["spread_t0"] > cfg["max_spread"]:
        return None
    if cand["l1_ask_usd"] < cfg["min_l1_usd"]:
        return None

    eff_cush = cand.get("cushion_oracle", cand["cushion_min"]) if cfg.get("use_cl_proxy", True) else cand["cushion_min"]
    eff_z = cand.get("z_oracle", cand["z_cushion"]) if cfg.get("use_cl_proxy", True) else cand["z_cushion"]
    if eff_cush < cfg["min_cushion"]:
        return None
    if eff_z < cfg["min_z"]:
        return None
    if cand["shock_ofi"] < cfg["min_ofi"]:
        return None

    if cfg["use_venue_veto"]:
        sign = 1.0 if cand["side"] == "UP" else -1.0
        if sign * cand["vdiv_centered"] > 12.0 or cand["cb_move_2s"] < -4.0:
            return None

    entry_mode = cfg["entry_mode"]
    size_mult = 1.0
    cascade_tag = ""
    if entry_mode == "maker_in":
        maker_px = round(min(ask_t0 - 0.01, cand["bid_t0"] + (0.01 if cand["spread_t0"] >= 0.02 else 0.0)), 2)
        if maker_px < cfg["min_px"]:
            return None
        filled_maker = False
        fill_idx = 0
        for idx_p, (tte_i, cush_i, b_i, a_i, vb_i) in enumerate(cand["path"]):
            if (cand["tte"] - tte_i) > 20.0:
                break
            # Patch C (v3.9): Resting passive BUY only fills when ask crosses <= maker_px (never on a falling bid!)
            if a_i <= maker_px:
                filled_maker = True
                fill_idx = idx_p
                break
        if not filled_maker:
            return None
        fill_px = maker_px
        entry_fee_ps = 0.0
        active_path = cand["path"][fill_idx + 1 :]
    elif entry_mode == "cascade_v4" and simulate_microclip_cascade_entry is not None:
        casc = simulate_microclip_cascade_entry(cand, cfg, latency_mode=latency_mode)
        if casc is None:
            return None
        fill_px, entry_fee_ps, fill_el_s, size_mult, cascade_tag = casc
        active_path = [r for r in cand["path"] if (cand["tte"] - r[0]) > fill_el_s]
    else:
        ask_lat = cand["ask_500ms"] if latency_mode == "500ms" else cand["ask_1000ms"]
        limit_px = min(cfg["max_px"] + 0.01, round(ask_t0 + cfg["fak_buffer"], 4))
        if ask_lat > limit_px or ask_lat <= 0.0 or ask_lat >= 0.99:
            return None
        fill_px = round(max(ask_lat, ask_t0 + min(0.02, cand["slip20_t0"])), 4)
        if fill_px > limit_px:
            return None
        entry_fee_ps = taker_fee_per_share(fill_px)
        active_path = cand["path"]

    shares = 1.0 / fill_px
    total_cost = 1.0 + shares * entry_fee_ps

    exit_policy = cfg["exit_policy"]
    tp1_px = 0.98
    tp1_frac = 0.0
    tp2_px = 0.98
    if exit_policy == "hold_98":
        tp2_px = 0.98
    elif exit_policy == "single_95":
        tp2_px = 0.95
    elif exit_policy == "single_plus14":
        tp2_px = min(0.97, round(fill_px + 0.14, 2))
    elif exit_policy == "two_tranche_10_98":
        tp1_px = min(0.95, round(fill_px + 0.10, 2))
        tp1_frac = 0.50
        tp2_px = 0.98
    elif exit_policy == "two_tranche_12_98":
        tp1_px = min(0.96, round(fill_px + 0.12, 2))
        tp1_frac = 0.50
        tp2_px = 0.98
    elif exit_policy == "two_tranche_14_98":
        tp1_px = min(0.96, round(fill_px + 0.14, 2))
        tp1_frac = 0.50
        tp2_px = 0.98
    elif exit_policy == "two_tranche_95_98":
        tp1_px = 0.95
        tp1_frac = 0.50
        tp2_px = 0.98
    elif exit_policy == "dynamic_95_98":
        # Upgrade 2 (v3.9): Deep-ITM probability-aware resting Maker exit
        tp1_px = 0.95 if eff_z >= 1.35 else min(0.95, round(fill_px + 0.14, 2))
        tp1_frac = 0.50
        tp2_px = 0.98

    rem_frac = 1.0
    tp1_done = (tp1_frac <= 0.0)
    realized_cash = 0.0
    max_seen_bid = cand["bid_t0"]
    ratchet_arm_delta = cfg["ratchet_arm"]
    ratchet_drop = cfg["ratchet_drop"]
    salvage_mode = cfg["salvage_mode"]
    wrong_thresh = cfg["wrong_side_thresh"]
    salvage_persist_s = cfg.get("salvage_persist_s", 15.0)
    clob_drop = cfg["clob_drop_thresh"]

    wrong_start_tte: Optional[float] = None
    clob_low_start_tte: Optional[float] = None
    ratchet_start_tte: Optional[float] = None

    settle_delay_s = float(cfg.get("settle_delay_s", 4.0))
    t2_post_lag_s = float(cfg.get("t2_post_lag_s", 0.5))
    buggy_f01_lock_300s = bool(cfg.get("buggy_f01_lock_300s", False))
    tp1_filled_elapsed: Optional[float] = None if tp1_frac > 0.0 else 0.0
    tp2_blocked_by_f01 = False

    exit_reason = "HOLD_RESOLUTION"
    exit_elapsed_s: Optional[float] = None
    for tte_i, cush_i, b_i, a_i, vb_i in active_path:
        elapsed_s = max(0.0, cand["tte"] - tte_i)
        two_sided = (0.01 <= b_i < a_i <= 0.999) or (b_i >= 0.98 and a_i > b_i)
        if b_i > max_seen_bid and two_sided:
            max_seen_bid = b_i

        # v3.8 F-12b: Maker GTC exits can only fill after Polygon ERC-1155 settlement delay (4.0s)
        # AND strict FIFO queue-clear (bid crosses TP + 1c OR all asks at TP are cleared: a_i > tp_px)
        maker_settled = (elapsed_s >= settle_delay_s) and (tte_i >= 15.0)
        if not tp1_done and maker_settled and two_sided and b_i >= tp1_px and (b_i >= tp1_px + 0.01 or a_i > tp1_px):
            realized_cash += (shares * tp1_frac) * tp1_px
            rem_frac -= tp1_frac
            tp1_done = True
            tp1_filled_elapsed = elapsed_s
            if buggy_f01_lock_300s and tte_i <= 300.0:
                tp2_blocked_by_f01 = True

        t2_ready = (
            tp1_done
            and not tp2_blocked_by_f01
            and maker_settled
            and (tp1_filled_elapsed is None or tp1_frac <= 0.0 or (elapsed_s - tp1_filled_elapsed) >= t2_post_lag_s)
        )
        if rem_frac > 1e-6 and t2_ready and two_sided and b_i >= tp2_px and (b_i >= tp2_px + 0.01 or a_i > tp2_px):
            realized_cash += (shares * rem_frac) * tp2_px
            rem_frac = 0.0
            exit_reason = "MAKER_TP_FULL"
            exit_elapsed_s = elapsed_s
            break

        if rem_frac > 1e-6 and ratchet_arm_delta is not None:
            arm_lvl = max(0.84, fill_px + ratchet_arm_delta)
            if max_seen_bid >= arm_lvl and b_i > 0.05 and b_i <= (max_seen_bid - ratchet_drop) and tte_i >= 25.0 and b_i >= (fill_px + 0.04):
                if ratchet_start_tte is None:
                    ratchet_start_tte = tte_i
                elif (ratchet_start_tte - tte_i) >= 4.0:
                    exec_b = max(0.01, min(b_i, vb_i))
                    fee_b = taker_fee_per_share(exec_b)
                    realized_cash += (shares * rem_frac) * max(0.0, exec_b - fee_b)
                    rem_frac = 0.0
                    exit_reason = "PROFIT_RATCHET"
                    exit_elapsed_s = elapsed_s
                    break
            else:
                ratchet_start_tte = None

        if rem_frac > 1e-6 and salvage_mode != "none" and tte_i >= 25.0 and b_i >= 0.18:
            if cush_i >= 0.0:
                wrong_start_tte = None
            elif cush_i <= -wrong_thresh:
                if wrong_start_tte is None:
                    wrong_start_tte = tte_i
            spot_wrong = (wrong_start_tte is not None) and ((wrong_start_tte - tte_i) >= salvage_persist_s) and (cush_i <= -(wrong_thresh * 0.8))

            clob_collapsed = False
            if salvage_mode == "hybrid_persist":
                if (b_i <= fill_px - clob_drop) and (cush_i <= -0.0002):
                    if clob_low_start_tte is None:
                        clob_low_start_tte = tte_i
                    elif (clob_low_start_tte - tte_i) >= max(8.0, salvage_persist_s * 0.6):
                        clob_collapsed = True
                else:
                    clob_low_start_tte = None

            if spot_wrong or clob_collapsed:
                exec_b = max(0.01, min(b_i, vb_i))
                fee_b = taker_fee_per_share(exec_b)
                realized_cash += (shares * rem_frac) * max(0.0, exec_b - fee_b)
                rem_frac = 0.0
                exit_reason = "SALVAGE_SPOT" if spot_wrong else "SALVAGE_CLOB_COLLAPSE"
                exit_elapsed_s = elapsed_s
                break

        if rem_frac > 1e-6 and cfg.get("final_45s_unwind", False) and 10.0 <= tte_i <= 45.0 and b_i >= 0.05:
            exec_b = max(0.01, min(b_i, vb_i))
            fee_b = taker_fee_per_share(exec_b)
            realized_cash += (shares * rem_frac) * max(0.0, exec_b - fee_b)
            rem_frac = 0.0
            exit_reason = "FINAL_45S_UNWIND"
            exit_elapsed_s = elapsed_s
            break

    if rem_frac > 1e-6:
        if cand["won"]:
            realized_cash += (shares * rem_frac) * 1.0
            exit_reason = "TP1_PLUS_WIN" if tp1_done and tp1_frac > 0 else "RESOLVED_WIN"
        else:
            exit_reason = "TP1_PLUS_LOSS" if tp1_done and tp1_frac > 0 else "RESOLVED_LOSS_WIPEOUT"

    net_pnl = (realized_cash - total_cost) * size_mult
    if cascade_tag:
        exit_reason = f"{cascade_tag}:{exit_reason}"
    rel_ts = (cand["t0"] + exit_elapsed_s + 4.0) if exit_elapsed_s is not None else cand["exp_ts"]
    return net_pnl, exit_reason, (net_pnl > 0), rel_ts


def evaluate_portfolio_on_slice(
    cands: List[Dict[str, Any]],
    cfg: Dict[str, Any],
    latency_mode: str = "500ms",
    max_concurrent: int = 2,
    ticket_usd: float = 15.0,
) -> Dict[str, Any]:
    seen_markets = set()
    # Vector 6 F-12a: Track (actual_release_ts, candle_exp_ts, hz) so early Maker TP / salvage releases
    # capital realistically while enforcing Live WFO #2 Same-Window Correlation Filter!
    active_slots: List[Tuple[float, float, str]] = []
    legacy_slots = bool(cfg.get("legacy_candle_end_slots", False))
    pnls: List[float] = []
    reasons = collections.Counter()
    wipeouts = 0

    eq = 0.0
    peak_eq = 0.0
    max_dd = 0.0

    for c in cands:
        mid = c["mid"]
        if mid in seen_markets:
            continue
        t0 = c["t0"]
        active_slots = [s for s in active_slots if s[0] > t0]
        if len(active_slots) >= max_concurrent:
            continue
        if not legacy_slots:
            # Live WFO #2 Same-Window Correlation Filter Parity:
            same_win = [s for s in active_slots if abs(s[1] - c["exp_ts"]) <= 300.0 and s[2] == c["hz"]]
            if same_win:
                if c["hz"] == "1h":
                    continue
                c_corr = c.get("cushion_oracle", c["cushion_min"]) if cfg.get("use_cl_proxy", True) else c["cushion_min"]
                if c["hz"] == "15m" and c_corr < 0.0009:
                    continue

        res = simulate_single_trade_ex(c, cfg, latency_mode=latency_mode)
        if res is None:
            continue

        pnl_unit, reason, _, rel_ts = res
        pnl_usd = pnl_unit * ticket_usd
        seen_markets.add(mid)
        slot_end_ts = c["exp_ts"] if legacy_slots else rel_ts
        active_slots.append((slot_end_ts, c["exp_ts"], c["hz"]))
        pnls.append(pnl_usd)
        reasons[reason] += 1
        if reason == "RESOLVED_LOSS_WIPEOUT":
            wipeouts += 1

        eq += pnl_usd
        if eq > peak_eq:
            peak_eq = eq
        dd = peak_eq - eq
        if dd > max_dd:
            max_dd = dd

    n = len(pnls)
    if n == 0:
        return {
            "trades": 0, "total_pnl": 0.0, "ev_per_trade": 0.0, "win_rate": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0, "profit_factor": 0.0, "sharpe": -99.0,
            "max_dd": 0.0, "wipeout_count": 0, "wipeout_rate": 0.0, "reasons": {}, "pnls": [],
        }

    total_pnl = sum(pnls)
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_win / gross_loss if gross_loss > 1e-6 else (99.0 if gross_win > 0 else 0.0)
    mean_p = total_pnl / n
    std_p = statistics.stdev(pnls) if n > 1 else 1e-6
    sharpe = (mean_p / max(std_p, 1e-6)) * math.sqrt(n)

    return {
        "trades": n,
        "total_pnl": round(total_pnl, 2),
        "ev_per_trade": round(mean_p, 4),
        "win_rate": round(len(wins) / n, 4),
        "avg_win": round(gross_win / len(wins), 3) if wins else 0.0,
        "avg_loss": round(-gross_loss / len(losses), 3) if losses else 0.0,
        "profit_factor": round(pf, 3),
        "sharpe": round(sharpe, 3),
        "max_dd": round(max_dd, 2),
        "wipeout_count": wipeouts,
        "wipeout_rate": round(wipeouts / n, 4),
        "reasons": dict(reasons),
        "pnls": pnls,
    }


def prefilter_entry_slice(slice_cands: List[Dict[str, Any]], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    assets_set = set(cfg["assets"])
    hz_set = set(cfg["horizons"])
    min_t15, max_t15 = cfg["min_tte_15m"], cfg["max_tte_15m"]
    min_t1h, max_t1h = cfg["min_tte_1h"], cfg["max_tte_1h"]
    min_px, max_px = cfg["min_px"], cfg["max_px"]
    max_sp = cfg["max_spread"]
    min_l1 = cfg["min_l1_usd"]
    min_cush = cfg["min_cushion"]
    min_z = cfg["min_z"]
    min_ofi = cfg["min_ofi"]
    use_vv = cfg["use_venue_veto"]
    out = []
    for c in slice_cands:
        if c["asset"] not in assets_set:
            continue
        hz = c["hz"]
        if hz not in hz_set:
            continue
        tte = c["tte"]
        if hz == "15m":
            if not (min_t15 <= tte <= max_t15):
                continue
        else:
            if not (min_t1h <= tte <= max_t1h):
                continue
        if not (min_px <= c["ask_t0"] <= max_px):
            continue
        if c["spread_t0"] > max_sp or c["l1_ask_usd"] < min_l1:
            continue
        # Keep superset safe across cushion_oracle (1h Binance / 15m Chainlink TWAP), cushion_min, and cushion_cl_proxy
        max_c = max(c["cushion_min"], c.get("cushion_oracle", c["cushion_min"]), c.get("cushion_cl_proxy", c["cushion_min"]))
        max_z = max(c["z_cushion"], c.get("z_oracle", c["z_cushion"]), c.get("z_cushion_cl", c["z_cushion"]))
        if max_c < min_cush:
            continue
        if max_z < min_z or c["shock_ofi"] < min_ofi:
            continue
        if use_vv:
            sign = 1.0 if c["side"] == "UP" else -1.0
            if sign * c["vdiv_centered"] > 12.0 or c["cb_move_2s"] < -4.0:
                continue
        out.append(c)
    return out


def compute_wfo_dev_score(
    r_tr: Dict[str, Any],
    r_vl: Dict[str, Any],
    r_vl_1000: Optional[Dict[str, Any]] = None,
    subfold_pnls: Optional[List[float]] = None,
) -> float:
    """
    Institutional Risk-Adjusted Walk-Forward Objective strictly on Train + Val:
    - Uses worst-split Sharpe (`min(tr_sharpe, vl_sharpe)`), worst-split capped PF (`min(tr_pf, vl_pf, 3.5)`),
      and worst-split EV * sqrt(N) (t-stat scaling, preventing low-conviction volume spam from dominating!).
    - Penalizes worst drawdown and worst wipeout rate heavily.
    """
    min_sharpe = min(r_tr["sharpe"], r_vl["sharpe"])
    min_pf = min(r_tr["profit_factor"], r_vl["profit_factor"], 3.5)
    min_ev = min(r_tr["ev_per_trade"], r_vl["ev_per_trade"])
    n_tot = r_tr["trades"] + r_vl["trades"]
    n_scale = math.sqrt(min(max(n_tot, 1), 130) / 130.0)
    t_ev_term = min_ev * math.sqrt(min(n_tot, 180))
    worst_dd = max(r_tr["max_dd"], r_vl["max_dd"])
    worst_wipe = max(r_tr["wipeout_rate"], r_vl["wipeout_rate"])

    score = (
        25.0 * min_sharpe
        + 35.0 * (min_pf * n_scale)
        + 12.0 * t_ev_term
        + 0.16 * min(r_tr["total_pnl"] + r_vl["total_pnl"], 300.0)
        - 0.55 * worst_dd
        - 90.0 * worst_wipe
    )
    if r_vl_1000 is not None:
        score += 10.0 * min(r_vl_1000["sharpe"], 2.5)
    if subfold_pnls:
        pos_folds = sum(1 for x in subfold_pnls if x > 0)
        score += 12.0 * pos_folds
    return score


# Global fork-shared pools for fast zero-copy Linux multiprocessing
_G_TR_POOL: List[Dict[str, Any]] = []
_G_VL_POOL: List[Dict[str, Any]] = []
_G_DEV_SUBFOLDS: List[List[Dict[str, Any]]] = []


def _eval_s1_batch(batch_cfgs: List[Dict[str, Any]]) -> List[Tuple[float, Dict[str, Any], Dict[str, Any], Dict[str, Any]]]:
    out = []
    for cfg in batch_cfgs:
        # Under strict WFO #2 same-window cross-asset deduplication, simultaneous BTC+ETH triggers in the
        # same clock hour count as 1 independent slot rather than 2 correlated duplicates.
        min_tr_n = 40
        min_vl_n = 20
        r_tr = evaluate_portfolio_on_slice(_G_TR_POOL, cfg, latency_mode="500ms")
        if r_tr["trades"] < min_tr_n or r_tr["total_pnl"] <= 0 or r_tr["profit_factor"] < 1.30:
            continue
        r_vl = evaluate_portfolio_on_slice(_G_VL_POOL, cfg, latency_mode="500ms")
        if r_vl["trades"] < min_vl_n or r_vl["total_pnl"] <= 0 or r_vl["profit_factor"] < 1.30:
            continue
        sc = compute_wfo_dev_score(r_tr, r_vl)
        r_tr_s = {k: v for k, v in r_tr.items() if k != "pnls"}
        r_vl_s = {k: v for k, v in r_vl.items() if k != "pnls"}
        out.append((sc, cfg, r_tr_s, r_vl_s))
    return out


def bootstrap_ci(pnls: List[float], n_boot: int = 1000, seed: int = 42) -> Dict[str, float]:
    if len(pnls) < 5:
        return {"p05_total_pnl": 0.0, "p50_total_pnl": 0.0, "p95_total_pnl": 0.0, "prob_positive": 0.0}
    rng = random.Random(seed)
    n = len(pnls)
    totals = []
    pos_cnt = 0
    for _ in range(n_boot):
        s = sum(pnls[rng.randrange(n)] for _ in range(n))
        totals.append(s)
        if s > 0:
            pos_cnt += 1
    totals.sort()
    return {
        "p05_total_pnl": round(totals[int(0.05 * n_boot)], 2),
        "p50_total_pnl": round(totals[int(0.50 * n_boot)], 2),
        "p95_total_pnl": round(totals[int(0.95 * n_boot)], 2),
        "prob_positive": round(pos_cnt / n_boot, 4),
    }


def compute_quarter_kelly(pnls: List[float], ticket_usd: float = 15.0) -> Dict[str, float]:
    if len(pnls) < 10:
        return {"full_kelly_pct": 0.0, "quarter_kelly_pct": 0.08}
    rets = [p / ticket_usd for p in pnls]
    mu = statistics.mean(rets)
    var = statistics.variance(rets)
    if mu <= 0 or var <= 1e-6:
        return {"full_kelly_pct": 0.0, "quarter_kelly_pct": 0.05}
    f_full = min(0.80, mu / var)
    f_quarter = round(max(0.08, min(0.20, 0.25 * f_full)), 4)
    return {"full_kelly_pct": round(f_full, 4), "quarter_kelly_pct": f_quarter}


def main():
    global _G_TR_POOL, _G_VL_POOL, _G_DEV_SUBFOLDS
    print("=" * 80)
    print("RUNNING HONEST ZERO-LOOKAHEAD PURGED WALK-FORWARD OPTIMIZER (v3.7)")
    print("=" * 80, flush=True)
    cands, meta = load_dataset(use_cache=True)
    print(f"Loaded dataset: {meta}", flush=True)

    PURGE_SEC = 7200.0  # 2 full hours embargo between splits
    train_cands: List[Dict[str, Any]] = []
    val_cands: List[Dict[str, Any]] = []
    holdout_cands: List[Dict[str, Any]] = []
    horizon_split_bounds: Dict[str, Any] = {}

    for hz_key in ("15m", "1h"):
        hz_list = [c for c in cands if c["hz"] == hz_key]
        if not hz_list:
            continue
        hz_t0 = sorted(c["t0"] for c in hz_list)
        t_tr_end = hz_t0[int(0.50 * len(hz_t0))]
        t_vl_end = hz_t0[int(0.75 * len(hz_t0))]
        tr_h = [c for c in hz_list if c["exp_ts"] <= t_tr_end]
        vl_h = [c for c in hz_list if c["t0"] >= (t_tr_end + PURGE_SEC) and c["exp_ts"] <= t_vl_end]
        ho_h = [c for c in hz_list if c["t0"] >= (t_vl_end + PURGE_SEC)]
        train_cands.extend(tr_h)
        val_cands.extend(vl_h)
        holdout_cands.extend(ho_h)
        horizon_split_bounds[hz_key] = {
            "train_n": len(tr_h),
            "val_n": len(vl_h),
            "holdout_n": len(ho_h),
            "train_end_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(t_tr_end)),
            "val_end_utc": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(t_vl_end)),
        }

    train_cands.sort(key=lambda x: x["t0"])
    val_cands.sort(key=lambda x: x["t0"])
    holdout_cands.sort(key=lambda x: x["t0"])

    # Build 4 chronological Purged Development Sub-Folds strictly inside (Train + Val)
    dev_cands = sorted(train_cands + val_cands, key=lambda x: x["t0"])
    n_dev = len(dev_cands)
    dev_subfolds: List[List[Dict[str, Any]]] = []
    for q_idx in range(4):
        i0 = int((q_idx * 0.25) * n_dev)
        i1 = int(((q_idx + 1) * 0.25) * n_dev) - 1
        t_start_q = dev_cands[i0]["t0"] + (PURGE_SEC if q_idx > 0 else 0.0)
        t_end_q = dev_cands[max(i0, i1)]["t0"]
        dev_subfolds.append([c for c in dev_cands if t_start_q <= c["t0"] <= t_end_q])

    print(f"Purged Splits -> Train: {len(train_cands)} | Val: {len(val_cands)} | Sealed Holdout: {len(holdout_cands)}", flush=True)

    # Evaluate the BUGGY LIVE BASELINE (Oct 23 hot-patch config) across all 3 splits for exact comparison
    buggy_live_cfg = {
        "name": "BUGGY_OCT23_HOTPATCH_BASELINE",
        "assets": ("BTC", "ETH"),
        "horizons": ("15m", "1h"),
        "min_tte_15m": 150.0, "max_tte_15m": 825.0,
        "min_tte_1h": 150.0, "max_tte_1h": 600.0,
        "min_px": 0.55, "max_px": 0.88,
        "max_spread": 0.04, "min_l1_usd": 15.0,
        "min_cushion": 0.0002, "min_z": 0.25, "min_ofi": 0.50,
        "use_venue_veto": False,
        "entry_mode": "taker_fak", "fak_buffer": 0.02,
        "exit_policy": "hold_98",
        "ratchet_arm": 0.16, "ratchet_drop": 0.06,
        "salvage_mode": "none", "wrong_side_thresh": 0.0006, "clob_drop_thresh": 0.30,
        "final_45s_unwind": False,
    }
    base_train = evaluate_portfolio_on_slice(train_cands, buggy_live_cfg)
    base_val = evaluate_portfolio_on_slice(val_cands, buggy_live_cfg)
    base_hold = evaluate_portfolio_on_slice(holdout_cands, buggy_live_cfg)
    print(f"[BASELINE BUGGY LIVE] Train PnL=${base_train['total_pnl']} (WR={base_train['win_rate']}, Wipeout={base_train['wipeout_rate']}) | "
          f"Val PnL=${base_val['total_pnl']} | Holdout PnL=${base_hold['total_pnl']} (Wipeout={base_hold['wipeout_rate']})", flush=True)

    # Stage 1: Production-Parity Sweep on ("BTC", "ETH") x ("15m", "1h") Taker-FAK with N_train>=45, N_val>=22
    # (Eliminates small-N single-asset or 11-trade zero-loss PF=99 flukes and matches live execute_snipe_order_async!)
    asset_sets = [("BTC", "ETH")]
    horizon_sets = [("15m", "1h")]
    px_bands = [
        (0.52, 0.74),
        (0.55, 0.75),
        (0.55, 0.78),
        (0.55, 0.80),
        (0.55, 0.82),
        (0.58, 0.78),
        (0.58, 0.80),
        (0.58, 0.82),
        (0.60, 0.80),
        (0.55, 0.85),
    ]
    z_thresholds = [0.45, 0.65, 0.72, 0.75, 0.85, 1.05, 1.25, 1.50]
    cushion_thresholds = [0.0004, 0.0006, 0.0008, 0.0010, 0.0012]
    tte_configs = [
        (60.0, 420.0, 120.0, 600.0),
        (90.0, 480.0, 120.0, 600.0),
        (90.0, 540.0, 150.0, 900.0),
        (120.0, 600.0, 150.0, 900.0),
        (90.0, 480.0, 150.0, 1200.0),
    ]
    s1_entry_modes = [("taker_fak", 0.02), ("maker_in", 0.0)]

    # Broad superset pre-filter for Stage 1 (mathematically exact superset of all Stage 1 configs)
    s1_superset_cfg = {
        "assets": ("BTC", "ETH"),
        "horizons": ("15m", "1h"),
        "min_tte_15m": 60.0, "max_tte_15m": 600.0,
        "min_tte_1h": 120.0, "max_tte_1h": 1200.0,
        "min_px": 0.52, "max_px": 0.85,
        "max_spread": 0.03, "min_l1_usd": 20.0,
        "min_cushion": 0.0004, "min_z": 0.45, "min_ofi": 0.60,
        "use_venue_veto": True, "use_cl_proxy": True,
    }
    _G_TR_POOL = prefilter_entry_slice(train_cands, s1_superset_cfg)
    _G_VL_POOL = prefilter_entry_slice(val_cands, s1_superset_cfg)
    _G_DEV_SUBFOLDS = dev_subfolds

    s1_exit_probes = [
        (None, "none"),
        (0.12, "hybrid_persist"),
    ]
    s1_all_cfgs: List[Dict[str, Any]] = []
    for assets in asset_sets:
        for horizons in horizon_sets:
            for min_px, max_px in px_bands:
                for min_z in z_thresholds:
                    for min_cush in cushion_thresholds:
                        for t15_min, t15_max, t1h_min, t1h_max in tte_configs:
                            for e_mode, f_buf in s1_entry_modes:
                                for r_probe, s_probe in s1_exit_probes:
                                    s1_all_cfgs.append({
                                        "assets": assets,
                                        "horizons": horizons,
                                        "min_tte_15m": t15_min, "max_tte_15m": t15_max,
                                        "min_tte_1h": t1h_min, "max_tte_1h": t1h_max,
                                        "min_px": min_px, "max_px": max_px,
                                        "max_spread": 0.03, "min_l1_usd": 20.0,
                                        "min_cushion": min_cush, "min_z": min_z, "min_ofi": 0.60,
                                        "use_venue_veto": True, "use_cl_proxy": True,
                                        "entry_mode": e_mode, "fak_buffer": f_buf,
                                        "exit_policy": "two_tranche_12_98",
                                        "ratchet_arm": r_probe, "ratchet_drop": 0.06,
                                        "salvage_mode": s_probe,
                                        "wrong_side_thresh": 0.0006, "salvage_persist_s": 15.0, "clob_drop_thresh": 0.22,
                                        "final_45s_unwind": False,
                                    })

    n_workers = max(1, min(8, (os.cpu_count() or 4)))
    chunk_sz = 250
    batches = [s1_all_cfgs[i : i + chunk_sz] for i in range(0, len(s1_all_cfgs), chunk_sz)]
    t_s1 = time.time()
    stage1_results = []
    with mp.get_context("fork").Pool(processes=n_workers) as pool:
        for res_batch in pool.imap_unordered(_eval_s1_batch, batches):
            stage1_results.extend(res_batch)

    stage1_results.sort(key=lambda x: x[0], reverse=True)
    print(
        f"Stage 1 evaluated {len(s1_all_cfgs)} configs across {n_workers} workers in {time.time() - t_s1:.1f}s | "
        f"Passed Train+Val PF>=1.25: {len(stage1_results)}",
        flush=True,
    )

    # Select top 24 diverse Stage-1 cores (ensuring taker_fak, maker_in, multi-asset BTC+ETH, and dual-horizon 15m+1h all compete!)
    top_cores: List[Dict[str, Any]] = []
    seen_core_keys = set()
    strata = [
        lambda c: True,
        lambda c: c["assets"] == ("BTC", "ETH") and c["horizons"] == ("15m", "1h"),
        lambda c: c["assets"] == ("BTC", "ETH") and c["entry_mode"] == "taker_fak",
        lambda c: c["entry_mode"] == "maker_in",
    ]
    for pred in strata:
        added_in_stratum = 0
        for _, cfg, _, _ in stage1_results:
            if not pred(cfg):
                continue
            ck = (
                cfg["assets"], cfg["horizons"], cfg["min_px"], cfg["max_px"],
                cfg["min_z"], cfg["min_cushion"], cfg["min_tte_15m"], cfg["max_tte_15m"],
                cfg["min_tte_1h"], cfg["max_tte_1h"], cfg["entry_mode"],
            )
            if ck not in seen_core_keys:
                seen_core_keys.add(ck)
                top_cores.append(cfg)
                added_in_stratum += 1
            if added_in_stratum >= 6 or len(top_cores) >= 24:
                break

    exit_policies = ["hold_98", "single_95", "single_plus14", "two_tranche_10_98", "two_tranche_12_98", "two_tranche_14_98", "two_tranche_95_98", "dynamic_95_98"]
    ratchet_arms = [None, 0.10, 0.12, 0.16]
    salvage_configs = [
        ("none", 0.0006, 15.0, 0.30),
        ("spot_persist", 0.0006, 15.0, 0.30),
        ("spot_persist", 0.0008, 20.0, 0.30),
        ("hybrid_persist", 0.0006, 15.0, 0.22),
        ("hybrid_persist", 0.0008, 20.0, 0.25),
    ]

    stage2_results = []
    total_tested = len(s1_all_cfgs)

    for base_c in top_cores:
        e_mode = base_c["entry_mode"]
        buf_variants = [0.01, 0.02, 0.03]
        tr_sub = prefilter_entry_slice(train_cands, base_c)
        vl_sub = prefilter_entry_slice(val_cands, base_c)
        min_tr_n = 40
        min_vl_n = 20

        for f_buf in buf_variants:
            entry_probe_cfg = dict(base_c)
            entry_probe_cfg.update({
                "entry_mode": e_mode, "fak_buffer": f_buf,
                "exit_policy": "hold_98", "ratchet_arm": None, "ratchet_drop": 0.06,
                "salvage_mode": "none", "wrong_side_thresh": 0.0006, "salvage_persist_s": 15.0, "clob_drop_thresh": 0.30,
            })

            def _select_fillable(sub_cands: List[Dict[str, Any]], lat: str) -> List[Dict[str, Any]]:
                # Filter strictly by entry fillability (do NOT pre-prune by hold_98 candle-end exp_ts so
                # early Maker TP / salvage slot release in evaluate_portfolio_on_slice is 100% exact!)
                return [
                    c_item for c_item in sub_cands
                    if simulate_single_trade_ex(c_item, entry_probe_cfg, latency_mode=lat) is not None
                ]

            tr_entered_500 = _select_fillable(tr_sub, "500ms")
            if len(tr_entered_500) < min_tr_n:
                total_tested += len(exit_policies) * len(ratchet_arms) * len(salvage_configs)
                continue
            vl_entered_500 = _select_fillable(vl_sub, "500ms")
            if len(vl_entered_500) < min_vl_n:
                total_tested += len(exit_policies) * len(ratchet_arms) * len(salvage_configs)
                continue
            vl_entered_1000 = _select_fillable(vl_sub, "1000ms")
            subfold_entered = [_select_fillable(prefilter_entry_slice(sf, base_c), "500ms") for sf in dev_subfolds]

            for ex_pol in exit_policies:
                for r_arm in ratchet_arms:
                    for s_mode, w_th, s_pers, c_drop in salvage_configs:
                        total_tested += 1
                        cfg = dict(base_c)
                        cfg.update({
                            "entry_mode": e_mode, "fak_buffer": f_buf,
                            "exit_policy": ex_pol,
                            "ratchet_arm": r_arm, "ratchet_drop": 0.06,
                            "salvage_mode": s_mode,
                            "wrong_side_thresh": w_th,
                            "salvage_persist_s": s_pers,
                            "clob_drop_thresh": c_drop,
                        })
                        r_tr = evaluate_portfolio_on_slice(tr_entered_500, cfg, latency_mode="500ms")
                        if r_tr["trades"] < min_tr_n or r_tr["total_pnl"] <= 0 or r_tr["profit_factor"] < 1.25:
                            continue
                        r_vl = evaluate_portfolio_on_slice(vl_entered_500, cfg, latency_mode="500ms")
                        if r_vl["trades"] < min_vl_n or r_vl["total_pnl"] <= 0 or r_vl["profit_factor"] < 1.25:
                            continue
                        r_vl_1000 = evaluate_portfolio_on_slice(vl_entered_1000, cfg, latency_mode="1000ms")
                        if r_vl_1000["total_pnl"] <= 0 or r_vl_1000["profit_factor"] < 1.15:
                            continue

                        sf_pnls = [
                            evaluate_portfolio_on_slice(sf_e, cfg, latency_mode="500ms")["total_pnl"]
                            for sf_e in subfold_entered
                        ]
                        pos_subfolds = sum(1 for x in sf_pnls if x > 0)
                        if pos_subfolds < 3:
                            continue

                        score = compute_wfo_dev_score(r_tr, r_vl, r_vl_1000, sf_pnls)
                        stage2_results.append((score, cfg, r_tr, r_vl, r_vl_1000))

    stage2_results.sort(key=lambda x: x[0], reverse=True)
    print(f"Total grid evaluations: {total_tested} | Stage 2 passed Train+Val+1000ms+SubFolds: {len(stage2_results)}", flush=True)

    if not stage2_results:
        raise RuntimeError("No configuration passed strict Train+Val+1000ms+SubFolds WFO gates!")

    # Select winner strictly from Train + Validation + Dev Sub-Folds (ZERO look at Holdout!)
    best_score, best_cfg, best_tr, best_vl, best_vl_1000 = stage2_results[0]

    # Controlled Ablation Table on Train + Val + Holdout for every single mechanism
    def eval_ablation(label: str, mod: Dict[str, Any]) -> Dict[str, Any]:
        c = dict(best_cfg)
        c.update(mod)
        tr = evaluate_portfolio_on_slice(train_cands, c)
        vl = evaluate_portfolio_on_slice(val_cands, c)
        ho = evaluate_portfolio_on_slice(holdout_cands, c)
        return {
            "label": label,
            "train_pnl": tr["total_pnl"], "train_trades": tr["trades"], "train_pf": tr["profit_factor"], "train_wipeout": tr["wipeout_rate"],
            "val_pnl": vl["total_pnl"], "val_trades": vl["trades"], "val_pf": vl["profit_factor"], "val_wipeout": vl["wipeout_rate"],
            "holdout_pnl": ho["total_pnl"], "holdout_trades": ho["trades"], "holdout_pf": ho["profit_factor"], "holdout_wipeout": ho["wipeout_rate"],
        }

    # NOW — AND ONLY ONCE — UNSEAL THE HOLDOUT SET!
    best_hold_500 = evaluate_portfolio_on_slice(holdout_cands, best_cfg, latency_mode="500ms")
    best_hold_1000 = evaluate_portfolio_on_slice(holdout_cands, best_cfg, latency_mode="1000ms")
    best_hold_seed_12_c1 = evaluate_portfolio_on_slice(holdout_cands, best_cfg, latency_mode="500ms", max_concurrent=1, ticket_usd=12.0)

    ablations = [
        eval_ablation("SELECTED_WFO_OPTIMAL (v3.9 Contract-Oracle + WFO#2 Corr + Exact Parity)", {}),
        eval_ablation("ABLATE_LEGACY_CANDLE_END_NO_CORR_FILTER (Vector 6 F-12a)", {"legacy_candle_end_slots": True}),
        eval_ablation("ABLATE_CONTRACT_ORACLE_PROXY (R07 + F-11)", {"use_cl_proxy": not best_cfg.get("use_cl_proxy", True)}),
        eval_ablation("ABLATE_BUGGY_F01_T2_LOCKED_300S_5S_LAG (v3.7 F-01+F-07 bug)", {"buggy_f01_lock_300s": True, "t2_post_lag_s": 5.0}),
        eval_ablation("ABLATE_HIGH_PX_085_THIN_CUSHION (Oct23 overpay bug)", {"max_px": 0.85, "min_cushion": 0.0002, "min_z": 0.35}),
        eval_ablation("ABLATE_TO_SINGLE_HOLD_98 (15m wipeout bug)", {"exit_policy": "hold_98"}),
        eval_ablation("ABLATE_RATCHET_TO_+16c (pytest-divergence bug)", {"ratchet_arm": 0.16}),
        eval_ablation("ABLATE_NO_SALVAGE (dead boolean bug)", {"salvage_mode": "none"}),
        eval_ablation("ABLATE_ENABLE_FINAL_45S_TAKER_UNWIND", {"final_45s_unwind": True}),
        eval_ablation("ABLATE_NO_VENUE_VETO", {"use_venue_veto": False}),
        eval_ablation("ABLATE_ALT_ENTRY_MODE (maker_in vs taker_fak)", {"entry_mode": "maker_in" if best_cfg["entry_mode"] != "maker_in" else "taker_fak"}),
        eval_ablation("ABLATE_CASCADE_V4_4STEP_ENTRY", {"entry_mode": "cascade_v4"}),
    ]

    # v3.9 Patch E (R05): Genuine Out-of-Sample Refit CPCV(N=6, k=2) -> 15 Zero-Leakage Splits
    # Uses an a-priori structural grid (zero Stage-1 leakage) and refits fitted_cfg strictly on the 4
    # purged+embargoed non-test groups before scoring the 2 held-out test groups!
    import itertools
    all_sorted = sorted(cands, key=lambda x: x["t0"])
    n_all = len(all_sorted)
    n_groups = 6
    group_bounds: List[Tuple[float, float]] = []
    for g_idx in range(n_groups):
        g_i0 = int((g_idx / n_groups) * n_all)
        g_i1 = int(((g_idx + 1) / n_groups) * n_all) - 1
        t_g0 = all_sorted[g_i0]["t0"]
        t_g1 = all_sorted[max(g_i0, g_i1)]["t0"]
        group_bounds.append((t_g0, t_g1))

    apriori_cpcv_grid: List[Dict[str, Any]] = []
    for px_lo, px_hi in [(0.55, 0.80), (0.55, 0.82), (0.55, 0.85)]:
        for z_th in [0.65, 0.85, 1.05]:
            for c_th in [0.0004, 0.0006]:
                for f_b in [0.01, 0.02]:
                    for ex_p in ["single_95", "two_tranche_14_98", "two_tranche_95_98", "hold_98"]:
                        for s_m, r_a in [("spot_persist", None), ("hybrid_persist", 0.12)]:
                            apriori_cpcv_grid.append({
                                "assets": ("BTC", "ETH"), "horizons": ("15m", "1h"),
                                "min_tte_15m": 90.0, "max_tte_15m": 480.0,
                                "min_tte_1h": 150.0, "max_tte_1h": 1200.0,
                                "min_px": px_lo, "max_px": px_hi,
                                "max_spread": 0.03, "min_l1_usd": 20.0,
                                "min_cushion": c_th, "min_z": z_th, "min_ofi": 0.60,
                                "use_venue_veto": True, "use_cl_proxy": True,
                                "entry_mode": "taker_fak", "fak_buffer": f_b,
                                "exit_policy": ex_p, "ratchet_arm": r_a, "ratchet_drop": 0.06,
                                "salvage_mode": s_m, "wrong_side_thresh": 0.0006,
                                "salvage_persist_s": 15.0, "clob_drop_thresh": 0.22,
                                "final_45s_unwind": False,
                            })
    apriori_superset = prefilter_entry_slice(all_sorted, {
        "assets": ("BTC", "ETH"), "horizons": ("15m", "1h"),
        "min_tte_15m": 90.0, "max_tte_15m": 480.0,
        "min_tte_1h": 150.0, "max_tte_1h": 1200.0,
        "min_px": 0.55, "max_px": 0.85, "max_spread": 0.03, "min_l1_usd": 20.0,
        "min_cushion": 0.0004, "min_z": 0.65, "min_ofi": 0.60,
        "use_venue_veto": True, "use_cl_proxy": True,
    })

    cpcv_splits = []
    for g_a, g_b in itertools.combinations(range(n_groups), 2):
        test_intervals = [group_bounds[g_a], group_bounds[g_b]]
        train_cpcv = [
            c for c in apriori_superset
            if all(
                (c["exp_ts"] < (ts_i - PURGE_SEC)) or (c["t0"] > (te_i + PURGE_SEC))
                for ts_i, te_i in test_intervals
            )
        ]
        oos_cpcv = []
        for g_t in (g_a, g_b):
            t_s, t_e = group_bounds[g_t]
            purge_left = PURGE_SEC if (g_t > 0 and (g_t - 1) not in (g_a, g_b)) else 0.0
            purge_right = PURGE_SEC if (g_t < n_groups - 1 and (g_t + 1) not in (g_a, g_b)) else 0.0
            eff_s = t_s + purge_left
            eff_e = t_e - (purge_right * 0.25)
            oos_cpcv.extend(c for c in apriori_superset if eff_s <= c["t0"] <= eff_e and c["exp_ts"] <= t_e)
        oos_cpcv.sort(key=lambda x: x["t0"])

        # Split the 4 purged training groups 70/30 into inner_tr + inner_vl and refit strictly on train_cpcv!
        n_tc = len(train_cpcv)
        t_cut_inner = train_cpcv[int(0.70 * n_tc)]["t0"] if n_tc >= 20 else 0.0
        in_tr = [c for c in train_cpcv if c["exp_ts"] <= t_cut_inner]
        in_vl = [c for c in train_cpcv if c["t0"] >= (t_cut_inner + PURGE_SEC)]
        fitted_cfg = apriori_cpcv_grid[0]
        best_cpcv_sc = -1e9
        for cand_cfg in apriori_cpcv_grid:
            ri_tr = evaluate_portfolio_on_slice(in_tr, cand_cfg, latency_mode="500ms")
            if ri_tr["trades"] < 20 or ri_tr["total_pnl"] <= 0 or ri_tr["profit_factor"] < 1.20:
                continue
            ri_vl = evaluate_portfolio_on_slice(in_vl, cand_cfg, latency_mode="500ms")
            if ri_vl["trades"] < 8 or ri_vl["total_pnl"] <= 0 or ri_vl["profit_factor"] < 1.15:
                continue
            sc_i = compute_wfo_dev_score(ri_tr, ri_vl)
            if sc_i > best_cpcv_sc:
                best_cpcv_sc = sc_i
                fitted_cfg = cand_cfg
        if best_cpcv_sc <= -1e8:
            # Fallback if inner 30% slice is sparse: rank across full 4-group purged train_cpcv
            for cand_cfg in apriori_cpcv_grid:
                ri_all = evaluate_portfolio_on_slice(train_cpcv, cand_cfg, latency_mode="500ms")
                if ri_all["trades"] >= 25 and ri_all["total_pnl"] > 0:
                    sc_i = compute_wfo_dev_score(ri_all, ri_all)
                    if sc_i > best_cpcv_sc:
                        best_cpcv_sc = sc_i
                        fitted_cfg = cand_cfg

        r_cpcv = evaluate_portfolio_on_slice(oos_cpcv, fitted_cfg, latency_mode="500ms")
        r_cpcv_seed = evaluate_portfolio_on_slice(oos_cpcv, fitted_cfg, latency_mode="500ms", max_concurrent=1, ticket_usd=12.0)
        cpcv_splits.append({
            "test_groups": [g_a, g_b],
            "fitted_exit_policy": fitted_cfg["exit_policy"],
            "fitted_min_z": fitted_cfg["min_z"],
            "trades": r_cpcv["trades"],
            "total_pnl": r_cpcv["total_pnl"],
            "seed_12_c1_pnl": r_cpcv_seed["total_pnl"],
            "win_rate": r_cpcv["win_rate"],
            "profit_factor": r_cpcv["profit_factor"],
            "sharpe": r_cpcv["sharpe"],
            "wipeout_rate": r_cpcv["wipeout_rate"],
            "pnls": r_cpcv["pnls"],
        })

    cpcv_pnls_list = [s["total_pnl"] for s in cpcv_splits]
    cpcv_seed_pnls = [s["seed_12_c1_pnl"] for s in cpcv_splits]
    cpcv_pfs_list = [s["profit_factor"] for s in cpcv_splits]
    cpcv_sharpes_list = [s["sharpe"] for s in cpcv_splits]
    cpcv_summary = {
        "mode": "GENUINE_OUT_OF_SAMPLE_REFIT_CPCV_6_2",
        "n_groups": 6,
        "k_test_groups": 2,
        "apriori_grid_size": len(apriori_cpcv_grid),
        "total_combinations": len(cpcv_splits),
        "positive_combinations": sum(1 for x in cpcv_pnls_list if x > 0),
        "positive_rate": round(sum(1 for x in cpcv_pnls_list if x > 0) / max(len(cpcv_splits), 1), 4),
        "seed_12_c1_positive_combinations": sum(1 for x in cpcv_seed_pnls if x > 0),
        "median_oos_trades": int(statistics.median(s["trades"] for s in cpcv_splits)),
        "median_oos_pnl_usd": round(statistics.median(cpcv_pnls_list), 2),
        "mean_oos_pnl_usd": round(statistics.mean(cpcv_pnls_list), 2),
        "median_seed_12_c1_oos_pnl_usd": round(statistics.median(cpcv_seed_pnls), 2),
        "min_oos_pnl_usd": round(min(cpcv_pnls_list), 2),
        "median_oos_pf": round(statistics.median(cpcv_pfs_list), 3),
        "median_oos_sharpe": round(statistics.median(cpcv_sharpes_list), 3),
        "splits": [{k: v for k, v in s.items() if k != "pnls"} for s in cpcv_splits],
    }

    # v3.8 F-11 + Blueprint 3: Enrich oracle_mismatch from verified_gamma_resolutions.json + ground_truth_resolutions.jsonl
    mismatch_mids = set()
    ver_p = DATA_DIR / "verified_gamma_resolutions.json"
    if ver_p.exists():
        try:
            ver_map = json.loads(ver_p.read_text(encoding="utf-8"))
            for k_m, v_m in ver_map.items():
                if isinstance(v_m, dict) and (
                    v_m.get("oracle_mismatch")
                    or v_m.get("mismatch")
                    or (v_m.get("binance_winner") and v_m.get("winner") and v_m.get("binance_winner") != v_m.get("winner"))
                ):
                    mismatch_mids.add(str(k_m))
        except Exception:
            pass
    for gt_name in ("ground_truth_resolutions.jsonl", "ground_truth_resolutions_eth.jsonl", "ground_truth_resolutions_sol.jsonl"):
        gt_p = DATA_DIR / gt_name
        if gt_p.exists():
            try:
                for ln in gt_p.read_text(encoding="utf-8", errors="replace").splitlines():
                    if not ln.strip():
                        continue
                    row_g = json.loads(ln)
                    if row_g.get("oracle_mismatch") or (
                        row_g.get("binance_winning_outcome")
                        and row_g.get("gamma_winning_outcome")
                        and row_g.get("binance_winning_outcome") != row_g.get("gamma_winning_outcome")
                    ):
                        mismatch_mids.add(str(row_g.get("market_id")))
            except Exception:
                pass
    for c_item in all_sorted:
        if c_item["path"]:
            tte_end_i, cush_end_i, _, _, _ = c_item["path"][-1]
            if tte_end_i <= 30.0 and abs(cush_end_i) >= 0.00001 and ((cush_end_i > 0) != bool(c_item["won"])):
                mismatch_mids.add(str(c_item.get("mid")))
        if str(c_item.get("mid")) in mismatch_mids:
            c_item["oracle_mismatch"] = True

    mismatch_cands = [c for c in all_sorted if c.get("oracle_mismatch")]
    cfg_no_cl = dict(best_cfg, use_cl_proxy=False)
    cfg_with_cl = dict(best_cfg, use_cl_proxy=True)
    mm_raw = evaluate_portfolio_on_slice(mismatch_cands, cfg_no_cl, latency_mode="500ms")
    mm_cl = evaluate_portfolio_on_slice(mismatch_cands, cfg_with_cl, latency_mode="500ms")
    full_no_cl = evaluate_portfolio_on_slice(all_sorted, cfg_no_cl, latency_mode="500ms")
    full_with_cl = evaluate_portfolio_on_slice(all_sorted, cfg_with_cl, latency_mode="500ms")

    # Blueprint 1 Evaluation on Two-Tranche Policy: Inline (<50ms) vs Concurrent (0.0s lag) vs Delayed (5.0s lag) vs Buggy F-01 Lock
    bp1_base = dict(best_cfg)
    if not str(bp1_base.get("exit_policy", "")).startswith("two_tranche"):
        bp1_base["exit_policy"] = "two_tranche_12_98"
    bp1_buggy = evaluate_portfolio_on_slice(all_sorted, dict(bp1_base, t2_post_lag_s=5.0, buggy_f01_lock_300s=True), latency_mode="500ms")
    bp1_delayed = evaluate_portfolio_on_slice(all_sorted, dict(bp1_base, t2_post_lag_s=5.0), latency_mode="500ms")
    bp1_inline = evaluate_portfolio_on_slice(all_sorted, dict(bp1_base, t2_post_lag_s=0.05), latency_mode="500ms")
    bp1_concurrent = evaluate_portfolio_on_slice(all_sorted, dict(bp1_base, t2_post_lag_s=0.0), latency_mode="500ms")

    chainlink_proxy_audit = {
        "mismatch_markets_identified": len(mismatch_mids),
        "mismatch_candidates_total": len(mismatch_cands),
        "mismatch_raw_trades": mm_raw["trades"],
        "mismatch_raw_pnl": mm_raw["total_pnl"],
        "mismatch_cl_proxy_trades": mm_cl["trades"],
        "mismatch_cl_proxy_pnl": mm_cl["total_pnl"],
        "full_dataset_raw_pnl": full_no_cl["total_pnl"],
        "full_dataset_raw_pf": full_no_cl["profit_factor"],
        "full_dataset_cl_proxy_pnl": full_with_cl["total_pnl"],
        "full_dataset_cl_proxy_pf": full_with_cl["profit_factor"],
        "blueprint1_tranche2_comparison": {
            "delayed_5s_pnl": bp1_delayed["total_pnl"],
            "delayed_5s_pf": bp1_delayed["profit_factor"],
            "inline_50ms_pnl": bp1_inline["total_pnl"],
            "inline_50ms_pf": bp1_inline["profit_factor"],
            "concurrent_0ms_pnl": bp1_concurrent["total_pnl"],
            "concurrent_0ms_pf": bp1_concurrent["profit_factor"],
        },
    }

    # v3.8 F-02: 10,000-Path 50-Trade Monte Carlo Bankroll & Halt-Floor Simulation from $76.49 Live Equity
    oos_unit_rets = [p / 15.0 for p in (best_vl["pnls"] + best_hold_500["pnls"])]
    if len(oos_unit_rets) < 20:
        oos_unit_rets = [p / 15.0 for p in best_tr["pnls"]]

    def sim_bankroll_policy(
        label: str,
        start_eq: float,
        base_pct: float,
        min_ticket: float,
        floor_usd: float,
        seed_cap_eq: float = 0.0,
        seed_ticket: float = 12.0,
        corr_pair_prob: float = 0.0,
        n_paths: int = 10000,
        n_trades: int = 50,
    ) -> Dict[str, Any]:
        rng_mc = random.Random(20261025)
        halted_cnt = 0
        end_eqs = []
        max_dds = []
        n_r = len(oos_unit_rets)
        for _ in range(n_paths):
            eq = start_eq
            pk = start_eq
            mdd = 0.0
            halted = False
            t_done = 0
            while t_done < n_trades:
                if eq < floor_usd:
                    halted = True
                    break
                if seed_cap_eq > 0.0 and eq < seed_cap_eq:
                    tkt = min(eq, seed_ticket)
                    r = oos_unit_rets[rng_mc.randrange(n_r)]
                    eq += tkt * r
                    t_done += 1
                else:
                    tkt = min(eq, max(min_ticket, round(eq * base_pct, 2)))
                    if corr_pair_prob > 0.0 and rng_mc.random() < corr_pair_prob and (t_done + 1) < n_trades:
                        # Simultaneous correlated window pair (same sign draw with 75% prob)
                        r1 = oos_unit_rets[rng_mc.randrange(n_r)]
                        r2 = r1 if rng_mc.random() < 0.75 else oos_unit_rets[rng_mc.randrange(n_r)]
                        eq += tkt * r1 + (tkt * 0.54) * r2
                        t_done += 2
                    else:
                        r = oos_unit_rets[rng_mc.randrange(n_r)]
                        eq += tkt * r
                        t_done += 1
                if eq > pk:
                    pk = eq
                if (pk - eq) > mdd:
                    mdd = pk - eq
                if eq < floor_usd:
                    halted = True
                    break
            if halted:
                halted_cnt += 1
            end_eqs.append(eq)
            max_dds.append(mdd)
        end_eqs.sort()
        max_dds.sort()
        return {
            "policy": label,
            "start_equity_usd": start_eq,
            "floor_usd": floor_usd,
            "halt_prob_50_trades": round(halted_cnt / n_paths, 4),
            "median_terminal_equity_usd": round(end_eqs[int(0.50 * n_paths)], 2),
            "p05_terminal_equity_usd": round(end_eqs[int(0.05 * n_paths)], 2),
            "p95_terminal_equity_usd": round(end_eqs[int(0.95 * n_paths)], 2),
            "p95_max_drawdown_usd": round(max_dds[int(0.95 * n_paths)], 2),
        }

    bankroll_mc = [
        sim_bankroll_policy("v3.7_UNPATCHED_22PCT_FLOOR65_CONC2", 76.49, 0.22, 12.0, 65.00, corr_pair_prob=0.25),
        sim_bankroll_policy("CENTRAL_CFG_18PCT_FLOOR66.67_CONC2", 76.49, 0.18, 12.0, 66.67, corr_pair_prob=0.25),
        sim_bankroll_policy("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR48", 76.49, 0.18, 12.0, 48.00, seed_cap_eq=88.0, seed_ticket=12.0, corr_pair_prob=0.15),
        sim_bankroll_policy("v3.8_SEED_SURVIVAL_$12_CONC1_BELOW88_FLOOR52", 76.49, 0.18, 12.0, 52.00, seed_cap_eq=88.0, seed_ticket=12.0, corr_pair_prob=0.15),
    ]

    ci_train = bootstrap_ci(best_tr["pnls"])
    ci_val = bootstrap_ci(best_vl["pnls"])
    ci_hold = bootstrap_ci(best_hold_500["pnls"])
    kelly = compute_quarter_kelly(best_tr["pnls"] + best_vl["pnls"], ticket_usd=15.0)

    top5_summary = []
    seen_top5_cores = set()
    for sc, c_i, tr_i, vl_i, _ in stage2_results:
        ck_i = (c_i["assets"], c_i["horizons"], c_i["min_px"], c_i["max_px"], c_i["min_z"], c_i["min_cushion"], c_i["entry_mode"], c_i["exit_policy"])
        if ck_i in seen_top5_cores:
            continue
        seen_top5_cores.add(ck_i)
        ho_i = evaluate_portfolio_on_slice(holdout_cands, c_i, latency_mode="500ms")
        c_clean = {k: (list(v) if isinstance(v, tuple) else v) for k, v in c_i.items()}
        top5_summary.append({
            "score": round(sc, 2),
            "config": c_clean,
            "train": {k: v for k, v in tr_i.items() if k != "pnls"},
            "val": {k: v for k, v in vl_i.items() if k != "pnls"},
            "holdout": {k: v for k, v in ho_i.items() if k != "pnls"},
        })
        if len(top5_summary) >= 5:
            break

    # Counterfactual Replay on Closed Live Positions in live_harvester_state.json
    live_counterfactual = {}
    st_path = DATA_DIR / "live_harvester_state.json"
    if st_path.exists():
        st = json.loads(st_path.read_text(encoding="utf-8"))
        closed_live = st.get("closed_positions", [])
        cand_by_eid = {c["event_id"]: c for c in cands}
        actual_total = 0.0
        cf_total = 0.0
        matched_live = 0
        filtered_out_losses = 0
        filtered_out_wins = 0
        post_rebate_traces = []

        for pos in closed_live:
            act_pnl = float(pos.get("net_pnl_usd") or 0.0)
            actual_total += act_pnl
            eid = str(pos.get("event_id") or "")
            tid = str(pos.get("trade_id") or "")
            c_match = cand_by_eid.get(eid)
            if not c_match:
                continue
            matched_live += 1
            sim = simulate_single_trade(c_match, best_cfg, latency_mode="500ms")
            notional = float(pos.get("notional_usd") or 15.0)
            if sim is None:
                cf_pnl = 0.0
                cf_reason = "VETOED_AT_ENTRY"
                if act_pnl < 0:
                    filtered_out_losses += 1
                else:
                    filtered_out_wins += 1
            else:
                cf_pnl = round(sim[0] * notional, 2)
                cf_reason = sim[1]
            cf_total += cf_pnl
            if "6076647" in tid or "6082720" in tid or act_pnl <= -15.0:
                post_rebate_traces.append({
                    "trade_id": tid,
                    "entry_price": pos.get("entry_price"),
                    "max_seen_bid": pos.get("max_seen_bid"),
                    "actual_pnl_usd": round(act_pnl, 2),
                    "actual_close_reason": pos.get("close_reason"),
                    "wfo_counterfactual_pnl_usd": cf_pnl,
                    "wfo_counterfactual_action": cf_reason,
                })
        live_counterfactual = {
            "total_live_closed_trades": len(closed_live),
            "matched_to_trigger_dataset": matched_live,
            "actual_matched_subset_pnl_usd": round(sum(float(p.get("net_pnl_usd") or 0.0) for p in closed_live if str(p.get("event_id") or "") in cand_by_eid), 2),
            "wfo_optimal_counterfactual_pnl_usd": round(cf_total, 2),
            "filtered_out_losing_trades": filtered_out_losses,
            "filtered_out_winning_trades": filtered_out_wins,
            "wipeout_trades_counterfactual": post_rebate_traces,
        }

    # 4-Fold Expanding Purged Cross-Validation across chronological Dev dataset (with 2h embargo per fold)
    cv_folds = []
    if len(dev_cands) >= 100:
        fold_fracs = [(0.25, 0.43), (0.43, 0.62), (0.62, 0.81), (0.81, 1.00)]
        for fold_idx, (tr_f, te_f) in enumerate(fold_fracs, start=1):
            t_cut = dev_cands[int(tr_f * n_dev)]["t0"]
            t_end = dev_cands[min(n_dev - 1, int(te_f * n_dev) - 1)]["t0"]
            oos_fold = [c for c in dev_cands if (t_cut + PURGE_SEC) <= c["t0"] <= t_end]
            r_fold = evaluate_portfolio_on_slice(oos_fold, best_cfg, latency_mode="500ms")
            cv_folds.append({
                "fold": fold_idx,
                "oos_candidates": len(oos_fold),
                "trades": r_fold["trades"],
                "total_pnl": r_fold["total_pnl"],
                "win_rate": r_fold["win_rate"],
                "profit_factor": r_fold["profit_factor"],
                "wipeout_rate": r_fold["wipeout_rate"],
            })

    report = {
        "generated_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "wfo_version": "3.9",
        "dataset_meta": meta,
        "total_grid_configs_evaluated": total_tested,
        "purged_splits": {
            "purge_embargo_seconds": PURGE_SEC,
            "train_candidates": len(train_cands),
            "val_candidates": len(val_cands),
            "holdout_candidates": len(holdout_cands),
            "per_horizon": horizon_split_bounds,
        },
        "cpcv_6_2_validation": cpcv_summary,
        "chainlink_proxy_audit": chainlink_proxy_audit,
        "bankroll_50trade_monte_carlo": bankroll_mc,
        "expanding_4fold_purged_cv": cv_folds,
        "buggy_oct23_live_baseline": {
            "train": {k: v for k, v in base_train.items() if k != "pnls"},
            "val": {k: v for k, v in base_val.items() if k != "pnls"},
            "holdout": {k: v for k, v in base_hold.items() if k != "pnls"},
        },
        "selected_optimal_config": {k: (list(v) if isinstance(v, tuple) else v) for k, v in best_cfg.items()},
        "selected_optimal_performance": {
            "train_500ms": {k: v for k, v in best_tr.items() if k != "pnls"},
            "val_500ms": {k: v for k, v in best_vl.items() if k != "pnls"},
            "val_1000ms_stress": {k: v for k, v in best_vl_1000.items() if k != "pnls"},
            "sealed_holdout_500ms": {k: v for k, v in best_hold_500.items() if k != "pnls"},
            "sealed_holdout_seed_12_conc1": {k: v for k, v in best_hold_seed_12_c1.items() if k != "pnls"},
            "sealed_holdout_1000ms_stress": {k: v for k, v in best_hold_1000.items() if k != "pnls"},
            "bootstrap_95ci": {
                "train": ci_train,
                "val": ci_val,
                "sealed_holdout": ci_hold,
            },
            "kelly_sizing": kelly,
        },
        "controlled_ablations": ablations,
        "d1_box_wfo_calibration": calibrate_d1_box_wfo(data_dir=DATA_DIR) if calibrate_d1_box_wfo is not None else {},
        "top_5_configs": top5_summary,
        "live_105_trades_counterfactual": live_counterfactual,
    }

    tmp = OUT_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2), encoding="utf-8")
    tmp.replace(OUT_JSON)

    print("\n" + "=" * 80)
    print("OPTIMAL WFO v3.7 CONFIG SELECTED (STRICTLY ON TRAIN + VAL + DEV SUB-FOLDS):")
    print(json.dumps(report["selected_optimal_config"], indent=2))
    print("\nSEALED HOLDOUT PERFORMANCE (+500ms Finland RTT):")
    print(json.dumps(report["selected_optimal_performance"]["sealed_holdout_500ms"], indent=2))
    print("\nSEALED HOLDOUT (+1000ms SEVERE LATENCY STRESS):")
    print(json.dumps(report["selected_optimal_performance"]["sealed_holdout_1000ms_stress"], indent=2))
    print("\nSEALED HOLDOUT BOOTSTRAP 95% CI:")
    print(json.dumps(ci_hold, indent=2))
    print("\nCONTROLLED ABLATIONS:")
    for ab in ablations:
        print(f"  - {ab['label']}: Train=${ab['train_pnl']} | Val=${ab['val_pnl']} | Holdout=${ab['holdout_pnl']} (PF={ab['holdout_pf']}, Wipeout={ab['holdout_wipeout']})")
    print("\nCPCV(6, 2) 15-SPLIT OUT-OF-SAMPLE SUMMARY:")
    print(json.dumps({k: v for k, v in cpcv_summary.items() if k != "splits"}, indent=2))
    print("\nCHAINLINK PROXY ORACLE-MISMATCH AUDIT:")
    print(json.dumps(chainlink_proxy_audit, indent=2))
    print("\n50-TRADE MONTE CARLO BANKROLL SURVIVAL FROM $76.49:")
    print(json.dumps(bankroll_mc, indent=2))
    print("\nLIVE COUNTERFACTUAL:")
    print(json.dumps(live_counterfactual, indent=2))
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
