#!/usr/bin/env python3
"""
Directional WFO Shadow Sleeves (Zero Real-Money Risk Out-of-Sample Validation)
==============================================================================
Implements the two Purged-WFO shadow experiments approved on 2026-10-30 inside
`polymarket_paper_trader.py` (`polymarket-trader.service`), completely isolated
from real-money `polymarket-live-harvester.service`:

  1. Shadow Candidate A (`SLEEVE_HYBRID_ZSPLIT_SHADOW`):
     BTC & ETH (`15m` [90s, 480s] + `1h` [150s, 600s]) Hybrid z-Split routing:
       - `0.78 <= z_strike < 1.20`: Routed strictly to `Shielded Maker-First`
         (`postOnly`, `0%` fee, `6.0s` TTL, `100ms` `/dev/shm` adverse-spot shield
         canceling immediately on `<= 0` cushion or `> 50%` cushion decay).
       - `z_strike >= 1.20`: Routed to `Taker + Phase 3A Shielded Maker Rescue`
         (`Smart FAK` -> `$12` Elastic Down-Snap -> `6.0s` Phase 3A `postOnly` rescue).
       - Exits: `hold_98` Maker TP (`$0.98`, `0%` fee) + 3-Zone `spot_only_9bps_18s` salvage.

  2. Shadow Candidate B (`SLEEVE_BTC_5M_SNIPER_SHADOW`):
     BTC-Only `5m` Final-TWAP Sniper (`ETH 5m` & `SOL 5m` hard-excluded):
       - Tails `polymarket_5m_telemetry_btc.jsonl` + `/dev/shm/pm_fast_tick_BTC.json`.
       - `TTE in [60s, 180s]`, `0.55 <= ask <= 0.85`, `spread <= $0.03`, `L1 >= $15.0`.
       - Strict currency-matched dual-strike cushion (`USDT` Binance spot vs
         `max/min(binance_open, twap_60s_open)` AND `USD` Chainlink proxy vs
         `authoritative_chainlink_open`), `cush_eff >= 0.03%`, `z_strike >= 0.80`.
       - `+500ms` real-time transit verification + `hold_98` Maker TP + `spot_only_9bps_18s` salvage.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from src.polymarket_research.exact_twap_lock_engine import should_suppress_final60s_twap_salvage
from src.polymarket_research.polymarket_live_executor import calculate_taker_fee
from src.polymarket_research.polymarket_live_harvester import evaluate_coinbase_venue_veto

from src.polymarket_research.riskless_protocol_v2_expansion import get_us_eastern_tz

SHADOW_INITIAL_CAPITAL = 500.0
SHADOW_TICKET_USD = 15.0
SHADOW_ELASTIC_USD = 12.0
XAU_TICKET_USD = 12.0
MAX_MAKER_JOIN_QUEUE_USD = 350.0
TRANSIT_LATENCY_SEC = 0.50
MAKER_TTL_SEC = 6.0
SHIELD_DECAY_FRAC = 0.50
Z_TAKER_CUT = 1.20
_NY_TZ = get_us_eastern_tz()


def compute_synthetic_xau_usd_anchor(
    binance_xau_usdt: float,
    coinbase_usdt_usd: float,
    swissquote_bid: float = 0.0,
    swissquote_ask: float = 0.0,
    max_basis_bps: float = 2.5,
) -> Dict[str, Any]:
    """
    Computes currency-matched synthetic `XAU/USD` anchor (`binance_xau_usdt * coinbase_usdt_usd`,
    rounded to 3-decimal Chainlink strike precision) and enforces <= `max_basis_bps` cross-check
    against Swissquote institutional `XAU/USD` mid when provided (Graveyard Rule #5 / Trap #4).
    """
    xau_u = float(binance_xau_usdt or 0.0)
    usdt_r = float(coinbase_usdt_usd or 0.0)
    if xau_u <= 0.0:
        return {"valid": False, "reason": "INVALID_BINANCE_XAUUSDT", "xau_usd": 0.0}
    if not (0.9800 <= usdt_r <= 1.0200):
        return {"valid": False, "reason": "MISSING_OR_DEPEGGED_USDT_USD_RATE", "xau_usd": 0.0}
    synth_usd = round(xau_u * usdt_r, 3)
    sq_b, sq_a = float(swissquote_bid or 0.0), float(swissquote_ask or 0.0)
    basis_bps = 0.0
    if sq_b > 0.0 and sq_a >= sq_b:
        sq_mid = 0.5 * (sq_b + sq_a)
        basis_bps = round(abs(synth_usd - sq_mid) / sq_mid * 10000.0, 4)
        if basis_bps > float(max_basis_bps) + 1e-6:
            return {
                "valid": False,
                "reason": "SWISSQUOTE_BASIS_DIVERGENCE",
                "xau_usd": synth_usd,
                "swissquote_mid": round(sq_mid, 3),
                "basis_bps": basis_bps,
            }
    return {"valid": True, "reason": "OK", "xau_usd": synth_usd, "basis_bps": basis_bps}


def is_xau_cme_blackout_or_inactive_session(ts_unix: float, enforce_active_session: bool = True) -> Tuple[bool, str]:
    """
    Blocks XAU 15m entries during CME Globex maintenance (`17:00-18:15 ET` Mon-Thu), weekend closure
    (`Fri >= 17:00 ET` through `Sun < 18:15 ET`), and outside London/COMEX peak liquidity windows
    (`03:00-05:00 ET` and `08:00-13:30 ET`) when `enforce_active_session` is enabled.
    """
    dt_et = datetime.fromtimestamp(float(ts_unix), tz=_NY_TZ)
    wd = dt_et.weekday()  # Mon=0 .. Sun=6
    mins = dt_et.hour * 60 + dt_et.minute
    if wd == 5 or (wd == 4 and mins >= 17 * 60) or (wd == 6 and mins < 18 * 60 + 15):
        return True, "CME_WEEKEND_CLOSURE"
    if 17 * 60 <= mins < 18 * 60 + 15:
        return True, "CME_GLOBEX_MAINTENANCE_BLACKOUT"
    if enforce_active_session and os.environ.get("PM_DISABLE_XAU_SESSION_FILTER") != "1":
        in_london_open = (3 * 60 <= mins <= 5 * 60)
        in_comex_overlap = (8 * 60 <= mins <= 13 * 60 + 30)
        if not (in_london_open or in_comex_overlap):
            return True, "OUTSIDE_LONDON_COMEX_ACTIVE_SESSION"
    return False, "OK"


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _maker_rebate_20pct_usd(shares: float, px: float, fee_rate: float = 0.07) -> float:
    px_c = max(0.01, min(0.99, float(px)))
    return round(shares * 0.20 * fee_rate * px_c * (1.0 - px_c), 4)


def _walk_bids_vwap(raw_bids: Any, target_shares: float, fallback_bid: float) -> float:
    if not raw_bids or target_shares <= 0:
        return fallback_bid
    rem = target_shares
    cash = 0.0
    for lvl in raw_bids:
        if not isinstance(lvl, (list, tuple)) or len(lvl) < 2:
            continue
        px, sz = float(lvl[0] or 0.0), float(lvl[1] or 0.0)
        if px <= 0 or sz <= 0:
            continue
        take = min(rem, sz)
        cash += take * px
        rem -= take
        if rem <= 1e-6:
            break
    if rem > 1e-6:
        cash += rem * max(0.01, fallback_bid - 0.02)
    return round(cash / target_shares, 4)


def _bootstrap_prob_positive(pnls: List[float], n_boot: int = 1000) -> Tuple[float, List[float]]:
    n = len(pnls)
    if n < 3:
        s = round(sum(pnls), 2)
        return (1.0 if s > 0 else 0.0), [s, s]
    rng = random.Random(20261030)
    totals = []
    for _ in range(n_boot):
        totals.append(sum(pnls[rng.randrange(n)] for _ in range(n)))
    totals.sort()
    lo = round(totals[int(0.025 * n_boot)], 2)
    hi = round(totals[int(0.975 * n_boot)], 2)
    p_pos = round(sum(1 for x in totals if x > 0) / n_boot, 4)
    return p_pos, [lo, hi]


class DirectionalWfoShadowManager:
    """Manages non-blocking shadow execution, 100ms shield supervision, and graduation ledgers."""

    def __init__(self, data_dir: Path, latency_sec: float = TRANSIT_LATENCY_SEC, production_mode: bool = False):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.latency_sec = max(0.0, float(latency_sec))
        self.production_mode = bool(production_mode)

        # Sleeve A: Hybrid z-Split (`BTC` + `ETH`, `15m` & `1h`)
        self.hz_ledger_file = self.data_dir / "ledger_shadow_hybrid_zsplit.jsonl"
        self.hz_state_file = self.data_dir / "state_shadow_hybrid_zsplit.json"
        self.hz_trades: List[Dict[str, Any]] = []
        self.hz_settled_ids: Set[str] = set()
        self.hz_settled_markets: Set[str] = set()
        self.hz_open: Dict[str, Dict[str, Any]] = {}  # market_id -> pos
        self.hz_pending: Dict[str, Dict[str, Any]] = {}  # market_id -> pending order
        self.hz_funnel: Dict[str, int] = {
            "signals_seen": 0,
            "signals_evaluated": 0,
            "maker_branch_queued": 0,
            "taker_branch_queued": 0,
            "maker_filled": 0,
            "taker_fak_filled": 0,
            "phase3a_rescue_filled": 0,
            "shield_canceled": 0,
            "complement_shield_canceled": 0,
            "queue_depth_rejected": 0,
            "ttl_expired_unfilled": 0,
            "post_only_or_collapse_rejected": 0,
        }

        # Sleeve B: BTC-Only 5m Final-TWAP Sniper
        self.b5_ledger_file = self.data_dir / "ledger_shadow_btc_5m.jsonl"
        self.b5_state_file = self.data_dir / "state_shadow_btc_5m.json"
        self.b5_telem_file = self.data_dir / "polymarket_5m_telemetry_btc.jsonl"
        self.b5_trades: List[Dict[str, Any]] = []
        self.b5_settled_ids: Set[str] = set()
        self.b5_settled_markets: Set[str] = set()
        self.b5_open: Dict[str, Dict[str, Any]] = {}
        self.b5_pending: Dict[str, Dict[str, Any]] = {}
        self.b5_funnel: Dict[str, int] = {
            "ticks_scanned": 0,
            "candidates_queued": 0,
            "taker_filled": 0,
            "transit_swept_or_shielded": 0,
        }

        # Sleeve C: SOL 5m Isolated Canary Shadow (`sqrt(12)` vol, `[60s, 180s]` TTE, separate from BTC 5m!)
        self.s5_ledger_file = self.data_dir / "ledger_shadow_sol_5m.jsonl"
        self.s5_state_file = self.data_dir / "state_shadow_sol_5m.json"
        self.s5_telem_file = self.data_dir / "polymarket_5m_telemetry_sol.jsonl"
        self.s5_trades: List[Dict[str, Any]] = []
        self.s5_settled_ids: Set[str] = set()
        self.s5_settled_markets: Set[str] = set()
        self.s5_open: Dict[str, Dict[str, Any]] = {}
        self.s5_pending: Dict[str, Dict[str, Any]] = {}
        self.s5_funnel: Dict[str, int] = {
            "ticks_scanned": 0,
            "candidates_queued": 0,
            "taker_filled": 0,
            "transit_swept_or_shielded": 0,
        }

        # Sleeve D: Corrected XAU 15m Shielded Maker-First Shadow (3-dec USD anchor, single-spot diffusion, 0% fee/0% rebate)
        self.xau_ledger_file = self.data_dir / "ledger_shadow_xau_15m.jsonl"
        self.xau_state_file = self.data_dir / "state_shadow_xau_15m.json"
        self.xau_telem_file = self.data_dir / "polymarket_15m_telemetry_xau.jsonl"
        self.xau_trades: List[Dict[str, Any]] = []
        self.xau_settled_ids: Set[str] = set()
        self.xau_settled_markets: Set[str] = set()
        self.xau_open: Dict[str, Dict[str, Any]] = {}
        self.xau_pending: Dict[str, Dict[str, Any]] = {}
        self.xau_funnel: Dict[str, int] = {
            "ticks_scanned": 0,
            "cme_or_session_blocked": 0,
            "basis_or_anchor_rejected": 0,
            "maker_queued": 0,
            "maker_filled": 0,
            "shield_or_comp_canceled": 0,
            "queue_depth_rejected": 0,
            "ttl_expired_unfilled": 0,
        }

        # Incremental file offsets for 5m BTC/SOL + 15m XAU + 15m/1h BTC/ETH telemetry
        self.b5_file_pos: int = self.b5_telem_file.stat().st_size if self.b5_telem_file.exists() else 0
        self.s5_file_pos: int = self.s5_telem_file.stat().st_size if self.s5_telem_file.exists() else 0
        self.xau_file_pos: int = self.xau_telem_file.stat().st_size if self.xau_telem_file.exists() else 0
        self.t15_btc_file = self.data_dir / "polymarket_15m_telemetry_btc.jsonl"
        self.t15_eth_file = self.data_dir / "polymarket_15m_telemetry_eth.jsonl"
        self.t1h_btc_file = self.data_dir / "polymarket_hourly_telemetry.jsonl"
        self.t1h_eth_file = self.data_dir / "polymarket_hourly_telemetry_eth.jsonl"
        self.t15_btc_pos: int = self.t15_btc_file.stat().st_size if self.t15_btc_file.exists() else 0
        self.t15_eth_pos: int = self.t15_eth_file.stat().st_size if self.t15_eth_file.exists() else 0
        self.t1h_btc_pos: int = self.t1h_btc_file.stat().st_size if self.t1h_btc_file.exists() else 0
        self.t1h_eth_pos: int = self.t1h_eth_file.stat().st_size if self.t1h_eth_file.exists() else 0

        # Causal rolling 1m EWMA sigma_1h per asset
        self._btc_sigma_1h: float = 0.0048
        self._btc_last_1m_bkt: int = 0
        self._btc_last_1m_spot: float = 0.0
        self._sol_sigma_1h: float = 0.0090
        self._sol_last_1m_bkt: int = 0
        self._sol_last_1m_spot: float = 0.0
        self._xau_sigma_1h: float = 0.0022
        self._xau_last_1m_bkt: int = 0
        self._xau_last_1m_spot: float = 0.0
        self._last_state_flush_ts: float = 0.0

        self._load_ledgers()
        self.save_states()

    def _load_ledgers(self) -> None:
        for path, trades_out, id_set, mkt_set in (
            (self.hz_ledger_file, self.hz_trades, self.hz_settled_ids, self.hz_settled_markets),
            (self.b5_ledger_file, self.b5_trades, self.b5_settled_ids, self.b5_settled_markets),
            (self.s5_ledger_file, self.s5_trades, self.s5_settled_ids, self.s5_settled_markets),
            (self.xau_ledger_file, self.xau_trades, self.xau_settled_ids, self.xau_settled_markets),
        ):
            if not path.exists():
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for ln in f:
                        if not ln.strip():
                            continue
                        row = json.loads(ln)
                        tid = str(row.get("trade_id") or "")
                        mid = str(row.get("market_id") or "")
                        if tid and tid not in id_set:
                            id_set.add(tid)
                            trades_out.append(row)
                            if mid:
                                mkt_set.add(mid)
            except Exception:
                pass
        # Restore funnel counters and any in-flight open positions if state files exist
        for st_path, funnel_dict, open_map, settled_ids in (
            (self.hz_state_file, self.hz_funnel, self.hz_open, self.hz_settled_ids),
            (self.b5_state_file, self.b5_funnel, self.b5_open, self.b5_settled_ids),
            (self.s5_state_file, self.s5_funnel, self.s5_open, self.s5_settled_ids),
            (self.xau_state_file, self.xau_funnel, self.xau_open, self.xau_settled_ids),
        ):
            if st_path.exists():
                try:
                    saved = json.loads(st_path.read_text(encoding="utf-8"))
                    for k, v in (saved.get("funnel_counters") or {}).items():
                        if k in funnel_dict and isinstance(v, int):
                            funnel_dict[k] = max(funnel_dict[k], v)
                    for m_id, pos in (saved.get("open_positions") or {}).items():
                        if isinstance(pos, dict) and pos.get("status") == "OPEN" and pos.get("trade_id") not in settled_ids:
                            open_map[str(m_id)] = pos
                except Exception:
                    pass

    def _read_shm_asset(self, asset: str) -> Optional[Dict[str, Any]]:
        shm_dir = os.environ.get("PM_FAST_TICK_DIR", "/dev/shm")
        if not shm_dir:
            return None
        p = Path(shm_dir) / f"pm_fast_tick_{asset.upper()}.json"
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            ts = float(d.get("timestamp_unix") or d.get("ts") or 0.0)
            if ts > 0 and (time.time() - ts) <= 5.0:
                return d
        except Exception:
            pass
        return None

    def _extract_market_view(self, asset: str, market_id: str, horizon: str) -> Optional[Dict[str, Any]]:
        """Extracts fresh (<=5s) orderbook + spot view for `market_id` from `/dev/shm/pm_fast_tick_{asset}.json`."""
        shm = self._read_shm_asset(asset)
        if not shm:
            return None
        mkts = shm.get("markets") or {}
        m = mkts.get(str(market_id))
        snap_block = None
        if horizon == "5m" and isinstance(shm.get("m5"), dict) and str(shm["m5"].get("market_id")) == str(market_id):
            snap_block = shm["m5"]
        elif horizon == "15m" and isinstance(shm.get("m15"), dict) and str(shm["m15"].get("market_id")) == str(market_id):
            snap_block = shm["m15"]
        if m is None and snap_block is None:
            return None
        src = m or snap_block or {}
        return {
            "timestamp_unix": float(src.get("timestamp_unix") or shm.get("timestamp_unix") or shm.get("ts") or time.time()),
            "binance_spot": float(src.get("spot_price") or shm.get("spot_price") or shm.get("spot") or 0.0),
            "chainlink_proxy_usd_spot": float(shm.get("chainlink_proxy_spot") or 0.0),
            "chainlink_twap_60s": float(shm.get("chainlink_twap_60s") or 0.0),
            "authoritative_chainlink_open": float((snap_block or {}).get("authoritative_chainlink_open") or 0.0),
            "twap_locked_mean": (snap_block or src).get("twap_locked_mean"),
            "twap_locked_weight": (snap_block or src).get("twap_locked_weight"),
            "coinbase_usdt_usd": float(shm.get("coinbase_usdt_usd") or 0.0),
            "swissquote_bid": float(shm.get("swissquote_bid") or 0.0),
            "swissquote_ask": float(shm.get("swissquote_ask") or 0.0),
            "UP": src.get("UP") or {},
            "DOWN": src.get("DOWN") or {},
        }

    @staticmethod
    def _compute_signed_cushion(
        side: str,
        horizon: str,
        binance_spot: float,
        open_usdt: float,
        twap_open_usdt: float = 0.0,
        cl_usd_spot: float = 0.0,
        auth_cl_open_usd: float = 0.0,
    ) -> Optional[float]:
        """Strict currency-matched signed cushion fraction (`USDT`-to-`USDT` and `USD`-to-`USD`)."""
        sign = 1.0 if side == "UP" else -1.0
        vals: List[float] = []
        if binance_spot > 0 and open_usdt > 0:
            if horizon in ("15m", "5m") and twap_open_usdt > 0:
                strike_u = max(open_usdt, twap_open_usdt) if side == "UP" else min(open_usdt, twap_open_usdt)
            else:
                strike_u = open_usdt
            vals.append(sign * (binance_spot - strike_u) / strike_u)
        if horizon in ("15m", "5m") and cl_usd_spot > 0 and auth_cl_open_usd > 0:
            vals.append(sign * (cl_usd_spot - auth_cl_open_usd) / auth_cl_open_usd)
        if not vals:
            return None
        return min(vals)

    # =========================================================================
    # CANDIDATE A: HYBRID Z-SPLIT (`BTC` + `ETH`, `15m` & `1h`)
    # =========================================================================
    def on_shock_signal(self, shock: Dict[str, Any], historical: bool = False) -> bool:
        """Evaluates incoming live shock trigger for `SLEEVE_HYBRID_ZSPLIT_SHADOW`."""
        if historical:
            return False
        if self.production_mode:
            from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER
            if not bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("shadow_governance", {}).get("enable_hybrid_zsplit_shadow", True)):
                return False
        m_id = str(shock.get("market_id") or "")
        if not m_id or m_id in self.hz_open or m_id in self.hz_pending or m_id in self.hz_settled_markets:
            return False
        if len(self.hz_open) + len(self.hz_pending) >= 2:
            return False

        title = str(shock.get("title") or "")
        title_l = title.lower()
        asset = str(shock.get("asset") or "").upper()
        if not asset:
            asset = "BTC" if ("bitcoin" in title_l or "btc" in title_l) else ("ETH" if ("ethereum" in title_l or "eth" in title_l) else "")
        if asset not in ("BTC", "ETH"):
            return False

        hz_raw = str(shock.get("horizon") or shock.get("candle_interval") or "").lower()
        slug = str(shock.get("series_slug") or shock.get("slug") or "").lower()
        tag_blob = f"{hz_raw} {slug} {title_l}"
        if re.search(r"(?<![0-9])5m(?![0-9a-z])|(?<![0-9])300s(?![0-9a-z])", tag_blob):
            return False
        # Match explicit 15m/900s tags OR Polymarket's standard 15-minute title range (e.g. "2:00pm-2:15pm et")
        _has_15m_range = False
        _rng_m = re.search(r"(\d{1,2}):(\d{2})\s*(?:am|pm)?\s*-\s*(\d{1,2}):(\d{2})\s*(?:am|pm)", title_l)
        if _rng_m:
            _m1, _m2 = int(_rng_m.group(2)), int(_rng_m.group(4))
            _diff_m = (_m2 - _m1) % 60
            if _diff_m == 15:
                _has_15m_range = True
            elif _diff_m == 5:
                return False
        is_15m = bool(re.search(r"(?<![0-9])15m(?![0-9a-z])|(?<![0-9])900s(?![0-9a-z])", tag_blob)) or _has_15m_range
        is_1h = not is_15m and (
            bool(re.search(r"(?<![0-9])(?:1h|60m)(?![0-9a-z])|hourly", tag_blob))
            or ("am et" in title_l or "pm et" in title_l)
        )
        if not (is_15m or is_1h):
            return False
        hz = "15m" if is_15m else "1h"
        self.hz_funnel["signals_seen"] = int(self.hz_funnel.get("signals_seen", 0)) + 1

        t0_unix = float(shock.get("t0_unix") or time.time())
        if os.environ.get("PM_DISABLE_NYSE_BLACKOUT") != "1":
            dt = datetime.fromtimestamp(t0_unix, tz=timezone.utc)
            if dt.hour == 13 and dt.minute >= 30:
                return False

        tte = float(shock.get("seconds_to_expiry") or 0.0)
        if hz == "15m" and not ((180.0 <= tte <= 390.0) if self.production_mode else (90.0 <= tte <= 480.0)):
            return False
        if hz == "1h" and not ((150.0 <= tte <= 2400.0) if self.production_mode else (150.0 <= tte <= 600.0)):
            return False

        shock_dir = str(shock.get("shock_direction") or "").upper()
        if shock_dir not in ("BUY", "SELL"):
            return False
        side = "UP" if shock_dir == "BUY" else "DOWN"

        cb_veto, _ = evaluate_coinbase_venue_veto(shock, side)
        if cb_veto:
            return False

        shock_ofi = abs(float(shock.get("shock_ofi") if shock.get("shock_ofi") is not None else 1.0))
        if shock_ofi < 0.60:
            return False

        spot_t0 = float(shock.get("spot_at_t0") or shock.get("trigger_price") or 0.0)
        open_sp = float(shock.get("candle_open_spot") or shock.get("finalized_1h_open") or 0.0)
        twap_open = float(shock.get("twap_60s_open") or 0.0)
        cl_spot = float(shock.get("chainlink_proxy_usd_spot") or 0.0)
        auth_cl = float(shock.get("authoritative_chainlink_open") or 0.0)
        cush_t0 = self._compute_signed_cushion(side, hz, spot_t0, open_sp, twap_open, cl_spot, auth_cl)
        if cush_t0 is None or cush_t0 < 0.0004:
            return False

        rec_sig = float(shock.get("candle_sigma") or 0.0)
        sigma_1h = (rec_sig * 2.0 if is_15m else rec_sig) if rec_sig > 0.0 else (0.0050 if asset == "BTC" else 0.0068)
        sigma_rem = max(0.00025, sigma_1h * math.sqrt(max(tte, 30.0) / 3600.0))
        z_strike = cush_t0 / sigma_rem
        if z_strike < 0.78:
            return False

        pre = (shock.get("pre_shock_features_t0") or {}).get(side) or {}
        raw_asks = pre.get("raw_top_asks") or []
        raw_bids = pre.get("raw_top_bids") or []
        ask_t0 = float(pre.get("best_ask") or (raw_asks[0][0] if raw_asks else 1.0))
        bid_t0 = float(pre.get("best_bid") or (raw_bids[0][0] if raw_bids else 0.0))
        ask_sz = float(pre.get("ask_size_l1") or (raw_asks[0][1] if raw_asks else 0.0))
        spread_t0 = round(ask_t0 - bid_t0, 4) if bid_t0 > 0 else 0.99
        l1_usd = ask_t0 * ask_sz

        _hz_px_cap = (0.72 if is_15m else 0.76) if self.production_mode else 0.82
        if not (0.55 <= ask_t0 <= _hz_px_cap) or bid_t0 <= 0.0 or spread_t0 > 0.03 or l1_usd < 20.0:
            return False

        self.hz_funnel["signals_evaluated"] += 1
        branch = "TAKER_PLUS_P3A" if z_strike >= Z_TAKER_CUT else "SHIELDED_MAKER_FIRST"
        if branch == "SHIELDED_MAKER_FIRST":
            self.hz_funnel["maker_branch_queued"] += 1
        else:
            self.hz_funnel["taker_branch_queued"] += 1

        now_u = time.time()
        self.hz_pending[m_id] = {
            "sleeve": "SLEEVE_HYBRID_ZSPLIT_SHADOW",
            "trade_id": f"HZSHDW_{m_id}_{int(t0_unix)}_{side}",
            "market_id": m_id,
            "title": title,
            "asset": asset,
            "horizon": hz,
            "target_token": side,
            "t0_unix": t0_unix,
            "queued_mono": now_u,
            "arrival_mono": now_u + self.latency_sec,
            "expiry_unix": float(shock.get("candle_expiry_ts") or shock.get("expiry_ts") or (t0_unix + tte)),
            "tte_t0": tte,
            "ask_t0": ask_t0,
            "bid_t0": bid_t0,
            "l1_usd_t0": round(l1_usd, 2),
            "cush_t0": cush_t0,
            "z_strike": round(z_strike, 4),
            "open_usdt": open_sp,
            "twap_open_usdt": twap_open,
            "auth_cl_open_usd": auth_cl,
            "branch": branch,
            "phase": "IN_TRANSIT",
            "maker_px": None,
            "deadline_mono": None,
        }
        return True

    # =========================================================================
    # CANDIDATE B: BTC-ONLY 5M FINAL-TWAP SNIPER
    # =========================================================================
    def _ingest_btc_5m_telemetry_tick(self, d: Dict[str, Any]) -> None:
        """Evaluates a single live `BTC 5m` telemetry row for `SLEEVE_BTC_5M_SNIPER_SHADOW`."""
        asset = str(d.get("asset") or "").upper()
        hz = str(d.get("horizon") or "").lower()
        # Hard guard: strictly BTC 5m ONLY (ETH 5m and SOL 5m are explicitly excluded)
        if asset != "BTC" or hz != "5m":
            return

        self.b5_funnel["ticks_scanned"] += 1
        ts = float(d.get("timestamp_unix") or time.time())
        sp = float(d.get("binance_spot") or 0.0)
        if sp > 0:
            b1 = int(ts // 60)
            if b1 > self._btc_last_1m_bkt:
                if self._btc_last_1m_spot > 0:
                    r1 = math.log(sp / self._btc_last_1m_spot)
                    self._btc_sigma_1h = max(
                        0.0020,
                        min(0.0200, math.sqrt(0.94 * (self._btc_sigma_1h ** 2) + 0.06 * (60.0 * r1 * r1))),
                    )
                self._btc_last_1m_spot = sp
                self._btc_last_1m_bkt = b1

        m_id = str(d.get("market_id") or "")
        if not m_id:
            return
        if m_id in self.b5_open:
            self._check_open_position_exit(self.b5_open, m_id, d, is_btc_5m=True)
            return
        if m_id in self.b5_pending or m_id in self.b5_settled_markets:
            return
        if len(self.b5_open) + len(self.b5_pending) >= 2:
            return

        if os.environ.get("PM_DISABLE_NYSE_BLACKOUT") != "1":
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            if dt.hour == 13 and dt.minute >= 30:
                return

        tte = float(d.get("seconds_to_expiry") or 0.0)
        if not (60.0 <= tte <= 180.0):
            return

        open_b = float(d.get("binance_open") or 0.0)
        twap_o = float(d.get("twap_60s_open") or 0.0)
        cl_sp = float(d.get("chainlink_proxy_usd_spot") or 0.0)
        auth_cl = float(d.get("authoritative_chainlink_open") or 0.0)
        if sp <= 0 or open_b <= 0:
            return

        sigma_rem = max(0.00025, self._btc_sigma_1h * math.sqrt(max(tte, 15.0) / 3600.0))

        for side in ("UP", "DOWN"):
            bk = d.get(side) or {}
            bid = float(bk.get("best_bid") or 0.0)
            ask = float(bk.get("best_ask") or 1.0)
            asz = float(bk.get("ask_size_l1") or 0.0)
            if bk.get("is_crossed") or bid <= 0.0 or ask >= 0.99 or bid >= ask:
                continue
            spread = round(ask - bid, 4)
            l1_usd = ask * asz
            if not (0.55 <= ask <= 0.85) or spread > 0.03 or l1_usd < 15.0:
                continue

            cush_eff = self._compute_signed_cushion(side, "5m", sp, open_b, twap_o, cl_sp, auth_cl)
            if cush_eff is None or cush_eff < 0.0003:
                continue
            z_strike = cush_eff / sigma_rem
            if z_strike < 0.80:
                continue

            now_u = time.time()
            self.b5_funnel["candidates_queued"] += 1
            self.b5_pending[m_id] = {
                "sleeve": "SLEEVE_BTC_5M_SNIPER_SHADOW",
                "trade_id": f"BTC5M_{m_id}_{int(ts)}_{side}",
                "market_id": m_id,
                "title": str(d.get("title") or f"BTC 5m {m_id}"),
                "asset": "BTC",
                "horizon": "5m",
                "target_token": side,
                "t0_unix": ts,
                "queued_mono": now_u,
                "arrival_mono": now_u + self.latency_sec,
                "expiry_unix": ts + tte,
                "tte_t0": tte,
                "ask_t0": ask,
                "bid_t0": bid,
                "l1_usd_t0": round(l1_usd, 2),
                "cush_t0": cush_eff,
                "z_strike": round(z_strike, 4),
                "open_usdt": open_b,
                "twap_open_usdt": twap_o,
                "auth_cl_open_usd": auth_cl,
                "latest_tick": d,
            }
            break

    # =========================================================================
    # CANDIDATE C: SOL 5M ISOLATED CANARY SHADOW (`[60s, 180s]`, `sqrt(12)` vol)
    # =========================================================================
    def _ingest_sol_5m_telemetry_tick(self, d: Dict[str, Any]) -> None:
        """Evaluates a single live `SOL 5m` telemetry row for `SLEEVE_SOL_5M_CANARY_SHADOW`."""
        asset = str(d.get("asset") or "").upper()
        hz = str(d.get("horizon") or "").lower()
        if asset != "SOL" or hz != "5m":
            return

        self.s5_funnel["ticks_scanned"] += 1
        ts = float(d.get("timestamp_unix") or time.time())
        sp = float(d.get("binance_spot") or 0.0)
        if sp > 0:
            b1 = int(ts // 60)
            if b1 > self._sol_last_1m_bkt:
                if self._sol_last_1m_spot > 0:
                    r1 = math.log(sp / self._sol_last_1m_spot)
                    self._sol_sigma_1h = max(
                        0.0040,
                        min(0.0300, math.sqrt(0.94 * (self._sol_sigma_1h ** 2) + 0.06 * (60.0 * r1 * r1))),
                    )
                self._sol_last_1m_spot = sp
                self._sol_last_1m_bkt = b1

        m_id = str(d.get("market_id") or "")
        if not m_id:
            return
        if m_id in self.s5_open:
            self._check_open_position_exit(self.s5_open, m_id, d, sleeve_tag="s5")
            return
        if m_id in self.s5_pending or m_id in self.s5_settled_markets:
            return
        if len(self.s5_open) + len(self.s5_pending) >= 2:
            return

        if os.environ.get("PM_DISABLE_NYSE_BLACKOUT") != "1":
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            if dt.hour == 13 and dt.minute >= 30:
                return

        tte = float(d.get("seconds_to_expiry") or 0.0)
        if not (60.0 <= tte <= 180.0):
            return

        open_b = float(d.get("binance_open") or 0.0)
        twap_o = float(d.get("twap_60s_open") or 0.0)
        cl_sp = float(d.get("chainlink_proxy_usd_spot") or 0.0)
        auth_cl = float(d.get("authoritative_chainlink_open") or 0.0)
        if sp <= 0 or open_b <= 0:
            return

        rec_sig_5m = float(d.get("candle_sigma") or 0.0)
        sig_1h = (rec_sig_5m * math.sqrt(12.0)) if rec_sig_5m > 0.0 else self._sol_sigma_1h
        sigma_rem = max(0.00035, sig_1h * math.sqrt(max(tte, 15.0) / 3600.0))

        for side in ("UP", "DOWN"):
            bk = d.get(side) or {}
            bid = float(bk.get("best_bid") or 0.0)
            ask = float(bk.get("best_ask") or 1.0)
            asz = float(bk.get("ask_size_l1") or 0.0)
            if bk.get("is_crossed") or bid <= 0.0 or ask >= 0.99 or bid >= ask:
                continue
            spread = round(ask - bid, 4)
            l1_usd = ask * asz
            if not (0.55 <= ask <= 0.85) or spread > 0.03 or l1_usd < 15.0:
                continue

            cush_eff = self._compute_signed_cushion(side, "5m", sp, open_b, twap_o, cl_sp, auth_cl)
            if cush_eff is None or cush_eff < 0.0004:
                continue
            z_strike = cush_eff / sigma_rem
            if z_strike < 0.80:
                continue

            now_u = time.time()
            self.s5_funnel["candidates_queued"] += 1
            self.s5_pending[m_id] = {
                "sleeve": "SLEEVE_SOL_5M_CANARY_SHADOW",
                "trade_id": f"SOL5M_{m_id}_{int(ts)}_{side}",
                "market_id": m_id,
                "title": str(d.get("title") or f"SOL 5m {m_id}"),
                "asset": "SOL",
                "horizon": "5m",
                "target_token": side,
                "t0_unix": ts,
                "queued_mono": now_u,
                "arrival_mono": now_u + self.latency_sec,
                "expiry_unix": ts + tte,
                "tte_t0": tte,
                "ask_t0": ask,
                "bid_t0": bid,
                "l1_usd_t0": round(l1_usd, 2),
                "cush_t0": cush_eff,
                "z_strike": round(z_strike, 4),
                "open_usdt": open_b,
                "twap_open_usdt": twap_o,
                "auth_cl_open_usd": auth_cl,
                "latest_tick": d,
            }
            break

    # =========================================================================
    # CANDIDATE D: CORRECTED XAU 15M SHIELDED MAKER-FIRST SHADOW
    # =========================================================================
    def ingest_xau_15m_tick(self, d: Dict[str, Any]) -> bool:
        """
        Evaluates a live `XAU 15m` tick enforcing:
          1. Currency-matched synthetic `XAU/USD` (`binance_xau_usdt * coinbase_usdt_usd`, 3-decimal strike precision)
             + Swissquote `<= 2.5 bps` basis guard (Graveyard Rule #5; never raw USDT, never Pyth Hermes V2).
          2. CME Globex `17:00-18:15 ET` + weekend blackout + London/COMEX active-session filter.
          3. Single-spot Brownian diffusion (`sigma_rem = sigma_1h * sqrt(tte / 3600)` — NO 60s TWAP collapse).
          4. Strictly `0%`-fee Shielded Maker-First (`spread <= $0.02`, `L1 >= $50`, `$12` max clip, `0%` maker rebate).
        """
        asset = str(d.get("asset") or "").upper()
        hz = str(d.get("horizon") or "").lower()
        if asset not in ("XAU", "GOLD") or hz != "15m":
            return False

        self.xau_funnel["ticks_scanned"] += 1
        ts = float(d.get("timestamp_unix") or time.time())
        blocked, _ = is_xau_cme_blackout_or_inactive_session(ts)
        if blocked:
            self.xau_funnel["cme_or_session_blocked"] += 1
            return False

        anchor = compute_synthetic_xau_usd_anchor(
            binance_xau_usdt=float(d.get("binance_xau_usdt") or d.get("binance_spot") or 0.0),
            coinbase_usdt_usd=float(d.get("coinbase_usdt_usd") or 0.0),
            swissquote_bid=float(d.get("swissquote_bid") or 0.0),
            swissquote_ask=float(d.get("swissquote_ask") or 0.0),
            max_basis_bps=2.5,
        )
        if not anchor["valid"]:
            self.xau_funnel["basis_or_anchor_rejected"] += 1
            return False
        xau_usd = float(anchor["xau_usd"])

        b1 = int(ts // 60)
        if b1 > self._xau_last_1m_bkt:
            if self._xau_last_1m_spot > 0:
                r1 = math.log(xau_usd / self._xau_last_1m_spot)
                self._xau_sigma_1h = max(
                    0.0010,
                    min(0.0120, math.sqrt(0.94 * (self._xau_sigma_1h ** 2) + 0.06 * (60.0 * r1 * r1))),
                )
            self._xau_last_1m_spot = xau_usd
            self._xau_last_1m_bkt = b1

        m_id = str(d.get("market_id") or "")
        if not m_id:
            return False
        if m_id in self.xau_open:
            d_usd = dict(d, chainlink_proxy_usd_spot=xau_usd)
            self._check_open_position_exit(self.xau_open, m_id, d_usd, sleeve_tag="xau")
            return False
        if m_id in self.xau_pending or m_id in self.xau_settled_markets:
            return False
        if len(self.xau_open) + len(self.xau_pending) >= 1:
            return False

        tte = float(d.get("seconds_to_expiry") or 0.0)
        if not (90.0 <= tte <= 480.0):
            return False

        raw_k = d.get("authoritative_chainlink_open") or d.get("strike_usd")
        if raw_k is None or float(raw_k) <= 0.0:
            self.xau_funnel["basis_or_anchor_rejected"] += 1
            return False
        strike_usd = round(float(raw_k), 3)

        rec_sig = float(d.get("candle_sigma") or 0.0)
        sig_1h = (rec_sig * 2.0) if rec_sig > 0.0 else self._xau_sigma_1h
        # Single-spot Chainlink close at T_end: standard Brownian sqrt(tte / 3600), NO 60s TWAP variance collapse!
        sigma_rem = max(0.00018, sig_1h * math.sqrt(tte / 3600.0))

        for side in ("UP", "DOWN"):
            bk = d.get(side) or {}
            opp_bk = d.get("DOWN" if side == "UP" else "UP") or {}
            bid = float(bk.get("best_bid") or 0.0)
            ask = float(bk.get("best_ask") or 1.0)
            asz = float(bk.get("ask_size_l1") or 0.0)
            bsz = float(bk.get("bid_size_l1") or 0.0)
            opp_bid = float(opp_bk.get("best_bid") or 0.0)
            if bk.get("is_crossed") or bid <= 0.0 or ask >= 0.99 or bid >= ask:
                continue
            spread = round(ask - bid, 4)
            l1_usd = ask * asz
            if not (0.56 <= ask <= 0.83) or spread > 0.02 or l1_usd < 50.0:
                continue

            sign = 1.0 if side == "UP" else -1.0
            cush = sign * (xau_usd - strike_usd) / strike_usd
            if cush < 0.00025:
                continue
            z_strike = cush / sigma_rem
            if z_strike < 0.85:
                continue

            maker_px = round(min(0.82, ask - 0.01, bid + (0.01 if spread >= 0.02 else 0.0)), 2)
            if maker_px < 0.55 or maker_px >= ask - 1e-6:
                continue
            if maker_px <= bid + 1e-6 and (bid * bsz) > MAX_MAKER_JOIN_QUEUE_USD:
                self.xau_funnel["queue_depth_rejected"] += 1
                continue
            if opp_bid > 0.0 and round(1.0 - opp_bid, 4) <= maker_px + 1e-6:
                self.xau_funnel["shield_or_comp_canceled"] += 1
                continue

            now_u = time.time()
            self.xau_funnel["maker_queued"] += 1
            self.xau_pending[m_id] = {
                "sleeve": "SLEEVE_XAU_15M_MAKER_SHADOW",
                "trade_id": f"XAU15M_{m_id}_{int(ts)}_{side}",
                "market_id": m_id,
                "title": str(d.get("title") or f"XAU/USD 15m {m_id}"),
                "asset": "XAU",
                "horizon": "15m",
                "target_token": side,
                "t0_unix": ts,
                "queued_mono": now_u,
                "arrival_mono": now_u + self.latency_sec,
                "expiry_unix": ts + tte,
                "tte_t0": tte,
                "ask_t0": ask,
                "bid_t0": bid,
                "maker_px": maker_px,
                "deadline_mono": now_u + self.latency_sec + MAKER_TTL_SEC,
                "l1_usd_t0": round(l1_usd, 2),
                "cush_t0": cush,
                "z_strike": round(z_strike, 4),
                "open_usdt": 0.0,
                "twap_open_usdt": 0.0,
                "auth_cl_open_usd": strike_usd,
                "latest_tick": d,
            }
            return True
        return False

    # =========================================================================
    # 100MS NON-BLOCKING ORDER SUPERVISION & EXIT ENGINE
    # =========================================================================
    def _step_hz_pending(self, now_u: float) -> None:
        for m_id, p in list(self.hz_pending.items()):
            if now_u < p["arrival_mono"]:
                continue
            view = self._extract_market_view(p["asset"], m_id, p["horizon"])
            if view is None:
                if now_u > p["arrival_mono"] + MAKER_TTL_SEC + 2.0:
                    self.hz_pending.pop(m_id, None)
                continue

            side = p["target_token"]
            opp_side = "DOWN" if side == "UP" else "UP"
            bk = view.get(side) or {}
            opp_bk = view.get(opp_side) or {}
            raw_asks = bk.get("raw_top_asks") or []
            raw_bids = bk.get("raw_top_bids") or []
            ask_now = float(bk.get("best_ask") or (raw_asks[0][0] if raw_asks else 1.0))
            bid_now = float(bk.get("best_bid") or (raw_bids[0][0] if raw_bids else 0.0))
            asz_now = float(bk.get("ask_size_l1") or (raw_asks[0][1] if raw_asks else 0.0))
            bsz_now = float(bk.get("bid_size_l1") or (raw_bids[0][1] if raw_bids else 0.0))
            opp_bid = float(opp_bk.get("best_bid") or 0.0)
            l1_now = ask_now * asz_now

            cush_now = self._compute_signed_cushion(
                side,
                p["horizon"],
                float(view.get("binance_spot") or 0.0),
                p["open_usdt"],
                p["twap_open_usdt"],
                float(view.get("chainlink_proxy_usd_spot") or 0.0),
                p["auth_cl_open_usd"],
            )
            # 100ms Adverse-Spot Cushion Shield (cancels immediately on <=0 or >50% decay)
            if cush_now is not None and (cush_now <= 0.0 or cush_now < p["cush_t0"] * (1.0 - SHIELD_DECAY_FRAC)):
                self.hz_funnel["shield_canceled"] += 1
                self.hz_pending.pop(m_id, None)
                continue

            if p["phase"] == "IN_TRANSIT":
                if (p["ask_t0"] - ask_now) >= 0.04:
                    self.hz_funnel["post_only_or_collapse_rejected"] += 1
                    self.hz_pending.pop(m_id, None)
                    continue

                if p["branch"] == "TAKER_PLUS_P3A":
                    limit_px = min(0.81, round(p["ask_t0"] + 0.02, 4))
                    if 0.0 < ask_now <= limit_px and l1_now >= SHADOW_ELASTIC_USD:
                        notional = SHADOW_TICKET_USD if l1_now >= SHADOW_TICKET_USD else SHADOW_ELASTIC_USD
                        step_tag = "STEP1_SMART_FAK" if notional >= SHADOW_TICKET_USD else "STEP2_ELASTIC_DOWNSNAP"
                        self.hz_funnel["taker_fak_filled"] += 1
                        self._open_shadow_position(self.hz_open, p, ask_now, notional, is_maker=False, step_tag=step_tag, entry_ts=float(view.get("timestamp_unix") or now_u))
                        self.hz_pending.pop(m_id, None)
                        continue
                    # Transition to Phase 3A Shielded Maker Rescue
                    p["branch_step_tag"] = "STEP4_PHASE3A_MAKER_RESCUE"
                else:
                    p["branch_step_tag"] = "SHIELDED_MAKER_FIRST"

                base_bid = bid_now if bid_now > 0.0 else max(0.01, ask_now - 0.02)
                maker_px = round(min(0.82, ask_now - 0.01, max(base_bid, p["ask_t0"] - 0.01)), 2)
                if maker_px < 0.55 or maker_px >= ask_now - 1e-6:
                    self.hz_funnel["post_only_or_collapse_rejected"] += 1
                    self.hz_pending.pop(m_id, None)
                    continue
                if maker_px <= bid_now + 1e-6 and (bid_now * bsz_now) > MAX_MAKER_JOIN_QUEUE_USD:
                    self.hz_funnel["queue_depth_rejected"] += 1
                    self.hz_pending.pop(m_id, None)
                    continue
                if opp_bid > 0.0 and round(1.0 - opp_bid, 4) <= maker_px + 1e-6:
                    self.hz_funnel["complement_shield_canceled"] += 1
                    self.hz_pending.pop(m_id, None)
                    continue
                p["phase"] = "RESTING_MAKER"
                p["maker_px"] = maker_px
                p["deadline_mono"] = now_u + MAKER_TTL_SEC
                continue

            # RESTING_MAKER supervision at 100ms
            maker_px = float(p["maker_px"])
            if opp_bid > 0.0:
                comp_ask = round(1.0 - opp_bid, 4)
                if comp_ask <= maker_px - 1e-6 or (ask_now > maker_px + 1e-6 and comp_ask <= maker_px + 1e-6):
                    self.hz_funnel["complement_shield_canceled"] += 1
                    self.hz_pending.pop(m_id, None)
                    continue
            if 0.0 < ask_now <= maker_px:
                step_tag = str(p.get("branch_step_tag") or "SHIELDED_MAKER_FIRST")
                if step_tag == "STEP4_PHASE3A_MAKER_RESCUE":
                    self.hz_funnel["phase3a_rescue_filled"] += 1
                else:
                    self.hz_funnel["maker_filled"] += 1
                self._open_shadow_position(self.hz_open, p, maker_px, SHADOW_TICKET_USD, is_maker=True, step_tag=step_tag, entry_ts=float(view.get("timestamp_unix") or now_u))
                self.hz_pending.pop(m_id, None)
            elif now_u >= float(p["deadline_mono"] or 0.0):
                self.hz_funnel["ttl_expired_unfilled"] += 1
                self.hz_pending.pop(m_id, None)

    def _step_b5_pending(self, now_u: float) -> None:
        self._step_5m_sniper_pending("BTC", self.b5_pending, self.b5_open, self.b5_funnel, "BTC5M_TAKER_FAK", now_u)

    def _step_s5_pending(self, now_u: float) -> None:
        self._step_5m_sniper_pending("SOL", self.s5_pending, self.s5_open, self.s5_funnel, "SOL5M_TAKER_FAK", now_u)

    def _step_5m_sniper_pending(
        self,
        asset_sym: str,
        pending_map: Dict[str, Dict[str, Any]],
        open_map: Dict[str, Dict[str, Any]],
        funnel_map: Dict[str, int],
        step_tag: str,
        now_u: float,
    ) -> None:
        for m_id, p in list(pending_map.items()):
            if now_u < p["arrival_mono"]:
                continue
            view = self._extract_market_view(asset_sym, m_id, "5m")
            if view is None:
                lt = p.get("latest_tick") or {}
                if float(lt.get("timestamp_unix") or 0.0) >= p["t0_unix"] + 0.35:
                    view = lt
                elif now_u > p["arrival_mono"] + 2.5:
                    funnel_map["transit_swept_or_shielded"] += 1
                    pending_map.pop(m_id, None)
                    continue
                else:
                    continue

            side = p["target_token"]
            bk = view.get(side) or {}
            raw_asks = bk.get("raw_top_asks") or []
            ask_now = float(bk.get("best_ask") or (raw_asks[0][0] if raw_asks else 1.0))
            asz_now = float(bk.get("ask_size_l1") or (raw_asks[0][1] if raw_asks else 0.0))
            l1_now = ask_now * asz_now

            cush_now = self._compute_signed_cushion(
                side,
                "5m",
                float(view.get("binance_spot") or 0.0),
                p["open_usdt"],
                p["twap_open_usdt"],
                float(view.get("chainlink_proxy_usd_spot") or 0.0),
                p["auth_cl_open_usd"],
            )
            limit_px = min(0.85, round(p["ask_t0"] + 0.02, 4))
            if (
                cush_now is not None
                and cush_now > 0.0
                and 0.0 < ask_now <= limit_px
                and (p["ask_t0"] - ask_now) < 0.04
                and l1_now >= SHADOW_ELASTIC_USD
            ):
                funnel_map["taker_filled"] += 1
                self._open_shadow_position(open_map, p, ask_now, SHADOW_TICKET_USD, is_maker=False, step_tag=step_tag, entry_ts=float(view.get("timestamp_unix") or now_u))
            else:
                funnel_map["transit_swept_or_shielded"] += 1
            pending_map.pop(m_id, None)

    def _step_xau_pending(self, now_u: float) -> None:
        for m_id, p in list(self.xau_pending.items()):
            if now_u < p["arrival_mono"]:
                continue
            view = self._extract_market_view("XAU", m_id, "15m")
            if view is None:
                lt = p.get("latest_tick") or {}
                if float(lt.get("timestamp_unix") or 0.0) >= p["t0_unix"] + 0.10:
                    view = lt
                elif now_u > float(p.get("deadline_mono") or (p["arrival_mono"] + MAKER_TTL_SEC)):
                    self.xau_funnel["ttl_expired_unfilled"] += 1
                    self.xau_pending.pop(m_id, None)
                    continue
                else:
                    continue

            anchor = compute_synthetic_xau_usd_anchor(
                binance_xau_usdt=float(view.get("binance_xau_usdt") or view.get("binance_spot") or 0.0),
                coinbase_usdt_usd=float(view.get("coinbase_usdt_usd") or 0.0),
                swissquote_bid=float(view.get("swissquote_bid") or 0.0),
                swissquote_ask=float(view.get("swissquote_ask") or 0.0),
                max_basis_bps=2.5,
            )
            if not anchor["valid"]:
                self.xau_funnel["shield_or_comp_canceled"] += 1
                self.xau_pending.pop(m_id, None)
                continue
            xau_usd = float(anchor["xau_usd"])
            side = p["target_token"]
            sign = 1.0 if side == "UP" else -1.0
            cush_now = sign * (xau_usd - float(p["auth_cl_open_usd"])) / float(p["auth_cl_open_usd"])
            if cush_now <= 0.0 or cush_now < p["cush_t0"] * (1.0 - SHIELD_DECAY_FRAC):
                self.xau_funnel["shield_or_comp_canceled"] += 1
                self.xau_pending.pop(m_id, None)
                continue

            bk = view.get(side) or {}
            opp_bk = view.get("DOWN" if side == "UP" else "UP") or {}
            ask_now = float(bk.get("best_ask") or 1.0)
            opp_bid = float(opp_bk.get("best_bid") or 0.0)
            maker_px = float(p["maker_px"])
            if opp_bid > 0.0:
                comp_ask = round(1.0 - opp_bid, 4)
                if comp_ask <= maker_px - 1e-6 or (ask_now > maker_px + 1e-6 and comp_ask <= maker_px + 1e-6):
                    self.xau_funnel["shield_or_comp_canceled"] += 1
                    self.xau_pending.pop(m_id, None)
                    continue
            if 0.0 < ask_now <= maker_px:
                self.xau_funnel["maker_filled"] += 1
                self._open_shadow_position(
                    self.xau_open, p, maker_px, XAU_TICKET_USD, is_maker=True, step_tag="XAU_SHIELDED_MAKER_FIRST",
                    entry_ts=float(view.get("timestamp_unix") or now_u),
                )
                self.xau_pending.pop(m_id, None)
            elif now_u >= float(p.get("deadline_mono") or 0.0):
                self.xau_funnel["ttl_expired_unfilled"] += 1
                self.xau_pending.pop(m_id, None)

    def _open_shadow_position(
        self,
        open_map: Dict[str, Dict[str, Any]],
        p: Dict[str, Any],
        fill_px: float,
        notional_usd: float,
        is_maker: bool,
        step_tag: str,
        entry_ts: Optional[float] = None,
    ) -> None:
        shares = round(notional_usd / fill_px, 4)
        is_metals = str(p.get("asset") or "").upper() in ("XAU", "GOLD", "XAG")
        if is_maker:
            entry_fee = 0.0
            # Metals have 0% maker fee and 0% maker rebate; crypto has 20% maker rebate estimate
            rebate_est = 0.0 if is_metals else _maker_rebate_20pct_usd(shares, fill_px)
        else:
            _, entry_fee = calculate_taker_fee(notional_usd, fill_px, fee_rate=0.07, fee_exponent=1.0)
            rebate_est = 0.0
        now_u = float(entry_ts) if entry_ts is not None else time.time()
        open_map[p["market_id"]] = {
            "sleeve": p["sleeve"],
            "trade_id": p["trade_id"],
            "market_id": p["market_id"],
            "title": p["title"],
            "asset": p["asset"],
            "horizon": p["horizon"],
            "target_token": p["target_token"],
            "branch": p.get("branch", step_tag),
            "entry_step": step_tag,
            "is_maker_entry": is_maker,
            "entry_time": _utc_now_str(),
            "entry_unix": now_u,
            "t0_unix": p["t0_unix"],
            "expiry_unix": p["expiry_unix"],
            "tte_at_t0": round(p["tte_t0"], 1),
            "z_strike": p["z_strike"],
            "cush_t0_pct": round(p["cush_t0"] * 100.0, 4),
            "open_usdt": p["open_usdt"],
            "twap_open_usdt": p["twap_open_usdt"],
            "auth_cl_open_usd": p["auth_cl_open_usd"],
            "entry_price": round(fill_px, 4),
            "shares_bought": shares,
            "notional_usd": round(notional_usd, 2),
            "taker_fee_usd": round(entry_fee, 4),
            "maker_rebate_20pct_est_usd": rebate_est,
            "take_profit_maker_limit_px": 0.98,
            "status": "OPEN",
        }
        self.save_states()

    def _check_open_position_exit(
        self,
        open_map: Dict[str, Dict[str, Any]],
        m_id: str,
        view: Dict[str, Any],
        is_btc_5m: bool = False,
        sleeve_tag: Optional[str] = None,
    ) -> None:
        pos = open_map.get(m_id)
        if not pos or pos.get("status") != "OPEN":
            return
        eff_tag = sleeve_tag or ("b5" if is_btc_5m else "hz")
        now_ts = float(view.get("timestamp_unix") or time.time())
        elapsed = now_ts - float(pos.get("entry_unix") or 0.0)
        tte_rem = float(view.get("seconds_to_expiry") or max(0.0, float(pos["expiry_unix"]) - now_ts))

        side = pos["target_token"]
        bk = view.get(side) or {}
        raw_bids = bk.get("raw_top_bids") or []
        raw_asks = bk.get("raw_top_asks") or []
        best_b = float(bk.get("best_bid") or (raw_bids[0][0] if raw_bids else 0.0))
        best_a = float(bk.get("best_ask") or (raw_asks[0][0] if raw_asks else 1.0))

        two_sided = (not bk.get("is_crossed")) and (
            (0.01 <= best_b < best_a <= 0.999) or (best_b >= 0.98 and best_a > best_b)
        )
        tp_px = float(pos.get("take_profit_maker_limit_px") or 0.98)
        is_metals = str(pos.get("asset") or "").upper() in ("XAU", "GOLD", "XAG")

        # 1. `hold_98` Maker TP (`$0.98` passive limit, 0% exit fee, >=4.0s settlement guard)
        if elapsed >= 4.0 and tte_rem >= 15.0 and two_sided and best_b >= tp_px and (best_b >= tp_px + 0.01 or best_a > tp_px):
            payout = round(pos["shares_bought"] * tp_px, 4)
            exit_reb = 0.0 if is_metals else _maker_rebate_20pct_usd(pos["shares_bought"], tp_px)
            self._finalize_closed_trade(
                pos=pos,
                exit_px=tp_px,
                payout_usd=payout,
                exit_fee_usd=0.0,
                exit_rebate_est_usd=exit_reb,
                exit_reason="MAKER_TP_98_FILLED",
                sleeve_tag=eff_tag,
            )
            open_map.pop(m_id, None)
            return

        # 2. 3-Zone `spot_only_9bps_18s` Salvage (`polymarket_live_harvester.py` parity + Final-60s TWAP lock shield)
        if tte_rem >= 25.0 and best_b >= 0.12:
            if not is_metals and 0.0 < tte_rem < 60.0 and pos.get("horizon") in ("15m", "5m"):
                cl_sp_now = float(view.get("chainlink_proxy_usd_spot") or view.get("binance_spot") or 0.0)
                k_open = float(pos.get("auth_cl_open_usd") or pos.get("open_usdt") or 0.0)
                sig_1h = (
                    self._sol_sigma_1h if pos.get("asset") == "SOL"
                    else (self._btc_sigma_1h if pos.get("asset") == "BTC" else 0.0068)
                )
                tw_sup, _ = should_suppress_final60s_twap_salvage(
                    side=side,
                    strike_open=k_open,
                    current_spot=cl_sp_now,
                    twap_locked_mean=view.get("twap_locked_mean"),
                    tte_sec=tte_rem,
                    sigma_1h=sig_1h,
                    twap_locked_weight=view.get("twap_locked_weight"),
                )
                if tw_sup:
                    pos.pop("wrong_side_start_ts", None)
                    return

            cush_now = self._compute_signed_cushion(
                side,
                pos["horizon"],
                float(view.get("binance_spot") or 0.0),
                pos["open_usdt"],
                pos["twap_open_usdt"],
                float(view.get("chainlink_proxy_usd_spot") or 0.0),
                pos["auth_cl_open_usd"],
            )
            if cush_now is not None:
                if cush_now >= 0.0:
                    pos.pop("wrong_side_start_ts", None)
                else:
                    if tte_rem > 900.0:
                        w_arm, w_sustain, req_dur = 0.0014, 0.0011, 22.0
                    elif tte_rem > 180.0:
                        w_arm, w_sustain, req_dur = 0.0011, 0.0009, 18.0
                    else:
                        w_arm, w_sustain, req_dur = 0.0009, 0.00075, 10.0

                    wrong_mag = -cush_now
                    ws_start = pos.get("wrong_side_start_ts")
                    if ws_start is None:
                        if wrong_mag >= w_arm:
                            pos["wrong_side_start_ts"] = now_ts
                    elif wrong_mag >= w_sustain:
                        if (now_ts - float(ws_start)) >= req_dur:
                            exec_b = min(best_b, _walk_bids_vwap(raw_bids, pos["shares_bought"], best_b))
                            exec_b = max(0.01, exec_b)
                            payout = round(pos["shares_bought"] * exec_b, 4)
                            ex_fee = 0.0 if is_metals else calculate_taker_fee(payout, exec_b, fee_rate=0.07, fee_exponent=1.0)[1]
                            self._finalize_closed_trade(
                                pos=pos,
                                exit_px=exec_b,
                                payout_usd=payout,
                                exit_fee_usd=ex_fee,
                                exit_rebate_est_usd=0.0,
                                exit_reason="SALVAGE_SPOT_ONLY_3ZONE",
                                sleeve_tag=eff_tag,
                            )
                            open_map.pop(m_id, None)
                    else:
                        pos.pop("wrong_side_start_ts", None)

    def on_telemetry_tick(self, m_id: str, telem: Dict[str, Any]) -> None:
        if m_id in self.hz_open:
            self._check_open_position_exit(self.hz_open, m_id, telem, sleeve_tag="hz")
        if m_id in self.b5_open:
            self._check_open_position_exit(self.b5_open, m_id, telem, sleeve_tag="b5")
        if m_id in self.s5_open:
            self._check_open_position_exit(self.s5_open, m_id, telem, sleeve_tag="s5")
        if m_id in self.xau_open:
            self._check_open_position_exit(self.xau_open, m_id, telem, sleeve_tag="xau")

    def on_market_resolution(self, m_id: str, resolution: Dict[str, Any]) -> None:
        winner = str(
            resolution.get("gamma_winning_outcome")
            or resolution.get("winning_outcome")
            or resolution.get("winner")
            or ""
        ).upper()
        if winner not in ("UP", "DOWN"):
            return
        m_str = str(m_id)
        for open_map, tag in (
            (self.hz_open, "hz"),
            (self.b5_open, "b5"),
            (self.s5_open, "s5"),
            (self.xau_open, "xau"),
        ):
            pos = open_map.pop(m_str, None)
            if not pos or pos.get("status") != "OPEN":
                continue
            won = (pos["target_token"] == winner)
            payout = round(pos["shares_bought"] * 1.0, 4) if won else 0.0
            pos["oracle_mismatch"] = bool(resolution.get("oracle_mismatch", False))
            pos["winning_outcome"] = winner
            self._finalize_closed_trade(
                pos=pos,
                exit_px=1.0 if won else 0.0,
                payout_usd=payout,
                exit_fee_usd=0.0,
                exit_rebate_est_usd=0.0,
                exit_reason="RESOLVED_WIN" if won else "RESOLVED_LOSS_WIPEOUT",
                sleeve_tag=tag,
            )

    def _finalize_closed_trade(
        self,
        pos: Dict[str, Any],
        exit_px: float,
        payout_usd: float,
        exit_fee_usd: float,
        exit_rebate_est_usd: float,
        exit_reason: str,
        is_btc_5m: bool = False,
        sleeve_tag: Optional[str] = None,
    ) -> None:
        eff_tag = sleeve_tag or ("b5" if is_btc_5m else "hz")
        net_pnl = round(payout_usd - pos["notional_usd"] - pos["taker_fee_usd"] - exit_fee_usd, 2)
        tot_reb = round(float(pos.get("maker_rebate_20pct_est_usd") or 0.0) + exit_rebate_est_usd, 4)
        pos.update({
            "status": "CLOSED",
            "exit_reason": exit_reason,
            "exit_price": round(exit_px, 4),
            "exit_fee_usd": round(exit_fee_usd, 4),
            "payout_usd": round(payout_usd, 2),
            "net_pnl_usd": net_pnl,
            "net_pnl_with_20pct_rebate_usd": round(net_pnl + tot_reb, 2),
            "won": bool(net_pnl > 0),
            "settle_time": _utc_now_str(),
        })
        routing = {
            "hz": (self.hz_settled_ids, self.hz_settled_markets, self.hz_trades, self.hz_ledger_file),
            "b5": (self.b5_settled_ids, self.b5_settled_markets, self.b5_trades, self.b5_ledger_file),
            "s5": (self.s5_settled_ids, self.s5_settled_markets, self.s5_trades, self.s5_ledger_file),
            "xau": (self.xau_settled_ids, self.xau_settled_markets, self.xau_trades, self.xau_ledger_file),
        }
        id_set, mkt_set, trades_list, ledger_file = routing[eff_tag]
        if pos["trade_id"] in id_set:
            return
        id_set.add(pos["trade_id"])
        mkt_set.add(pos["market_id"])
        trades_list.append(pos)

        with open(ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(pos) + "\n")
        self.save_states()

    def _tail_jsonl_file(self, path: Path, pos_attr: str) -> List[Dict[str, Any]]:
        if not path.exists():
            return []
        out: List[Dict[str, Any]] = []
        try:
            cur_sz = path.stat().st_size
            last_pos = getattr(self, pos_attr)
            if cur_sz < last_pos:
                setattr(self, pos_attr, cur_sz)
                last_pos = cur_sz
            if cur_sz > last_pos:
                with open(path, "rb") as f:
                    f.seek(last_pos)
                    chunk = f.read()
                end_nl = chunk.rfind(b"\n") + 1
                if end_nl > 0:
                    setattr(self, pos_attr, last_pos + end_nl)
                    for ln in chunk[:end_nl].decode("utf-8", errors="ignore").splitlines():
                        if ln.strip():
                            try:
                                out.append(json.loads(ln))
                            except Exception:
                                pass
        except Exception:
            pass
        return out

    def poll_tick(self, shutdown_requested: bool = False) -> None:
        """Called every 100ms by `PolymarketForwardPaperTrader.live_loop`."""
        if shutdown_requested:
            self.save_states()
            return
        now_u = time.time()

        _sg_poll = {}
        if self.production_mode:
            from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER
            _sg_poll = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("shadow_governance", {}) or {}

        # 1a/1b. Tail BTC & SOL 5m telemetry in non-production test mode or when explicitly enabled in shadow_governance
        _b5_on = bool(_sg_poll.get("enable_btc_5m_sniper_shadow", _sg_poll.get("enable_btc_5m_shadow", False)))
        _s5_on = bool(_sg_poll.get("enable_sol_5m_canary_shadow", _sg_poll.get("enable_sol_5m_shadow", False)))
        if (not self.production_mode) or _b5_on:
            for row in self._tail_jsonl_file(self.b5_telem_file, "b5_file_pos"):
                self._ingest_btc_5m_telemetry_tick(row)
                m_id = str(row.get("market_id") or "")
                if m_id in self.b5_pending:
                    self.b5_pending[m_id]["latest_tick"] = row
        if (not self.production_mode) or _s5_on:
            for row in self._tail_jsonl_file(self.s5_telem_file, "s5_file_pos"):
                self._ingest_sol_5m_telemetry_tick(row)
                m_id = str(row.get("market_id") or "")
                if m_id in self.s5_pending:
                    self.s5_pending[m_id]["latest_tick"] = row

        # 1c. Tail XAU 15m telemetry (when recorded) for Candidate D entries + exits
        if (not self.production_mode) or bool(_sg_poll.get("enable_xau_15m_maker_shadow", True)):
            for row in self._tail_jsonl_file(self.xau_telem_file, "xau_file_pos"):
                self.ingest_xau_15m_tick(row)
                m_id = str(row.get("market_id") or "")
                if m_id in self.xau_pending:
                    self.xau_pending[m_id]["latest_tick"] = row

        # 2. Tail 15m + 1h BTC/ETH telemetry so open Hybrid z-Split positions get continuous exit ticks
        hz_telem_streams = (
            (self.t15_btc_file, "t15_btc_pos"),
            (self.t15_eth_file, "t15_eth_pos"),
            (self.t1h_btc_file, "t1h_btc_pos"),
            (self.t1h_eth_file, "t1h_eth_pos"),
        )
        if self.hz_open:
            for t_file, p_attr in hz_telem_streams:
                for row in self._tail_jsonl_file(t_file, p_attr):
                    m_id = str(row.get("market_id") or "")
                    if m_id in self.hz_open:
                        self._check_open_position_exit(self.hz_open, m_id, row, sleeve_tag="hz")
        else:
            for t_file, p_attr in hz_telem_streams:
                if t_file.exists():
                    setattr(self, p_attr, t_file.stat().st_size)

        # 3. Step pending orders & open-position SHM checks at 100ms resolution
        step_u = time.time()
        if self.hz_pending:
            self._step_hz_pending(step_u)
        if self.b5_pending:
            self._step_b5_pending(step_u)
        if self.s5_pending:
            self._step_s5_pending(step_u)
        if self.xau_pending:
            self._step_xau_pending(step_u)

        for m_id, pos in list(self.hz_open.items()):
            view = self._extract_market_view(pos["asset"], m_id, pos["horizon"])
            if view is not None:
                self._check_open_position_exit(self.hz_open, m_id, view, sleeve_tag="hz")
        for m_id, pos in list(self.b5_open.items()):
            view = self._extract_market_view("BTC", m_id, "5m")
            if view is not None:
                self._check_open_position_exit(self.b5_open, m_id, view, sleeve_tag="b5")
        for m_id, pos in list(self.s5_open.items()):
            view = self._extract_market_view("SOL", m_id, "5m")
            if view is not None:
                self._check_open_position_exit(self.s5_open, m_id, view, sleeve_tag="s5")
        for m_id, pos in list(self.xau_open.items()):
            view = self._extract_market_view("XAU", m_id, "15m")
            if view is not None:
                self._check_open_position_exit(self.xau_open, m_id, view, sleeve_tag="xau")

        if (now_u - self._last_state_flush_ts) >= 15.0:
            self.save_states()

    def _build_sleeve_state(
        self,
        sleeve_id: str,
        strategy_desc: str,
        min_grad_trades: int,
        trades: List[Dict[str, Any]],
        open_map: Dict[str, Dict[str, Any]],
        pending_map: Dict[str, Dict[str, Any]],
        funnel: Dict[str, int],
        ledger_path: Path,
        ticket_usd: float = SHADOW_TICKET_USD,
    ) -> Dict[str, Any]:
        n = len(trades)
        pnls = [float(t.get("net_pnl_usd") or 0.0) for t in trades]
        reb_pnls = [float(t.get("net_pnl_with_20pct_rebate_usd") or t.get("net_pnl_usd") or 0.0) for t in trades]
        wins = sum(1 for x in pnls if x > 0)
        wr = round((wins / n) * 100.0, 2) if n > 0 else 0.0
        gw = sum(x for x in pnls if x > 0)
        gl = abs(sum(x for x in pnls if x <= 0))
        pf = round(gw / gl, 3) if gl > 1e-6 else (99.0 if gw > 0 else 0.0)
        realized = round(sum(pnls), 2)
        fees = round(sum(float(t.get("taker_fee_usd") or 0.0) + float(t.get("exit_fee_usd") or 0.0) for t in trades), 2)
        p_pos, ci95 = _bootstrap_prob_positive(pnls)
        ready = bool(n >= min_grad_trades and pf >= 1.50 and ci95[0] > 0.0 and p_pos >= 0.95)
        return {
            "timestamp": _utc_now_str(),
            "sleeve_id": sleeve_id,
            "strategy": strategy_desc,
            "graduation_criteria": f"trades >= {min_grad_trades}, PF >= 1.50, bootstrap_95ci_lo > $0.00 (P(>0) >= 95%)",
            "ready_for_live_graduation": ready,
            "initial_capital": SHADOW_INITIAL_CAPITAL,
            "ticket_notional_usd": ticket_usd,
            "current_equity": round(SHADOW_INITIAL_CAPITAL + realized, 2),
            "realized_pnl": realized,
            "realized_pnl_with_20pct_maker_rebate": round(sum(reb_pnls), 2),
            "profit_factor": pf,
            "win_rate_pct": wr,
            "bootstrap_prob_positive": p_pos,
            "bootstrap_95ci_total_pnl": ci95,
            "total_fees_paid": fees,
            "total_trades_settled": n,
            "winning_trades": wins,
            "losing_trades": n - wins,
            "active_open_positions_count": len(open_map),
            "open_positions": dict(open_map),
            "pending_orders_count": len(pending_map),
            "funnel_counters": dict(funnel),
            "status": "RUNNING",
            "ledger_file": str(ledger_path),
        }

    def save_states(self) -> None:
        self._last_state_flush_ts = time.time()
        hz_state = self._build_sleeve_state(
            sleeve_id="SLEEVE_HYBRID_ZSPLIT_SHADOW",
            strategy_desc="BTC/ETH 15m+1h Hybrid z-Split (0.78<=z<1.20 Shielded Maker 0% Fee + Comp-Book Shield + <=45$ Queue Cap, z>=1.20 Taker+P3A)",
            min_grad_trades=50,
            trades=self.hz_trades,
            open_map=self.hz_open,
            pending_map=self.hz_pending,
            funnel=self.hz_funnel,
            ledger_path=self.hz_ledger_file,
        )
        b5_state = self._build_sleeve_state(
            sleeve_id="SLEEVE_BTC_5M_SNIPER_SHADOW",
            strategy_desc="BTC-Only 5m Final-TWAP Sniper (TTE 60-180s, USD Chainlink + USDT Dual-Strike Cush>=3bps, z>=0.80, px<=0.85, ETH/SOL Excluded)",
            min_grad_trades=60,
            trades=self.b5_trades,
            open_map=self.b5_open,
            pending_map=self.b5_pending,
            funnel=self.b5_funnel,
            ledger_path=self.b5_ledger_file,
        )
        s5_state = self._build_sleeve_state(
            sleeve_id="SLEEVE_SOL_5M_CANARY_SHADOW",
            strategy_desc="SOL-Only 5m Isolated Canary Shadow (TTE 60-180s, sqrt(12) vol, Dual-Strike Cush>=4bps, z>=0.80, px<=0.85)",
            min_grad_trades=60,
            trades=self.s5_trades,
            open_map=self.s5_open,
            pending_map=self.s5_pending,
            funnel=self.s5_funnel,
            ledger_path=self.s5_ledger_file,
        )
        xau_state = self._build_sleeve_state(
            sleeve_id="SLEEVE_XAU_15M_MAKER_SHADOW",
            strategy_desc="XAU/USD 15m Shielded Maker-First (3-dec synth USD + Swissquote <=2.5bps, single-spot diffusion, CME/Session gated, 0% fee/0% rebate, $12 clip)",
            min_grad_trades=40,
            trades=self.xau_trades,
            open_map=self.xau_open,
            pending_map=self.xau_pending,
            funnel=self.xau_funnel,
            ledger_path=self.xau_ledger_file,
            ticket_usd=XAU_TICKET_USD,
        )
        for st_obj, target_path in (
            (hz_state, self.hz_state_file),
            (b5_state, self.b5_state_file),
            (s5_state, self.s5_state_file),
            (xau_state, self.xau_state_file),
        ):
            tmp = target_path.with_suffix(f".tmp.{os.getpid()}")
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(st_obj, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, target_path)
            except Exception:
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except Exception:
                        pass
