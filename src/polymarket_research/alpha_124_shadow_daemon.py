#!/usr/bin/env python3
"""
Polymarket Alpha-124 Unified Shadow-Trading Daemon (Options #1, #2, and #4)
===========================================================================
Runs three orthogonal, non-HFT Polymarket engines concurrently in strict
zero-lookahead shadow mode (walking live CLOB L2 orderbooks at t_signal + 50ms):

  - Option #1 (Weather METAR + 71-Member NWP Ensemble):
      * W1_SOLAR_PEAK_LOCK: Post-diurnal-peak routine METAR cooling lock (target ~90% WR)
      * W2_ENSEMBLE_VALUE: Pre-peak MOS-corrected 71-member ensemble value brackets (Taker)
      * W2_MAKER_OVERROUND: 0%-fee `post_only=True` Maker quoting inside ~1.07 Weather overrounds

  - Option #2 (Crypto One-Touch Barrier "Hit/Dip" Jump-SVI):
      * B1_CONVEX_TAIL_YES: Underpriced OTM `YES` barrier tails ($0.04-$0.32) with 2x Maker TP
      * B2_BARRIER_NO_LOCK: Final-window (1h-10h) untouched barrier `NO` convergence

  - Option #4 (Multi-Strike SVI Breeden-Litzenberger Maker-Scalper & Convergence):
      * M1_SVI_MAKER_SCALP: Intra-day SVI BL mispricing with +4.5c 0%-fee Maker TP & SVI stop
      * M2_STRIKE_CONVERGENCE: Final-window (20m-3.5h) high-z ITM digital convergence
      * M3_LADDER_MONO_BOX: Deterministic cross-strike monotonicity arbitrage (< $0.996)
      * M4_SHOCK_STRIKE_CATCHUP: <250ms Binance impulse wakeup sniping lagging daily SVI rungs

  - Option #7 & #8 (Chainlink 60s-TWAP Exact-Strike Microstructure):
      * D1_SAME_ORACLE_DOMINANCE_BOX: Equal-share `UP(K_low) + DOWN(K_high)` <= $0.995 net
        during `:10-:15`, `:25-:30`, `:40-:45`, `:55-:00` across BTC, ETH, SOL, XRP.
      * S2_EXACT_TWAP_LOCK: Final-45s (8s-45s) banked 60s-TWAP integral mathematical lock
        across 5m + 15m BTC, ETH, SOL, XRP (64 expiries/hr) using 14-digit Chainlink `openPrice`.

Simulates 3 bankroll sizing profiles simultaneously (`T100`, `T1000`, `T5000`) with exact
Polymarket `zero_fees` (Weather) and `crypto_fees_v2` (Crypto) accounting.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import aiohttp

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.polymarket_research.barrier_onetouch_svi_engine import (
    ASSET_BINANCE_SYMBOL,
    HIT_SERIES,
    BarrierRungSpec,
    evaluate_barrier_no_net_ev,
    fetch_binance_window_extremes_sync,
    first_passage_touch_prob,
    get_wing_implied_vol,
    parse_hit_event,
)
from src.polymarket_research.multistrike_svi_scalper import (
    DAILY_UPDOWN_SERIES,
    NEGRISK_SERIES,
    STRIKE_SERIES,
    DailyUpDownSpec,
    NegRiskBracketSpec,
    StrikeRungSpec,
    _fast_norm_cdf,
    build_negrisk_cross_box_bundles,
    detect_ladder_monotonicity_boxes,
    evaluate_coherent_strike_ladder,
    evaluate_svi_digital_fair_value,
    parse_daily_updown_event,
    parse_multistrike_event,
    parse_negrisk_bracket_event,
)
from src.polymarket_research.net_alpha_opportunity_engine import (
    publish_global_positions_shm,
    rank_opportunities_capital_auction,
    read_global_positions_shm,
    scan_binary_complete_set_arb,
)
from src.polymarket_research.same_oracle_dominance_box import (
    DOMINANCE_ASSETS,
    DOMINANCE_SERIES_SLUGS,
    TwapCandleMarketSpec,
    build_crypto_price_query_url,
    build_own_gamma_event_url,
    build_prev_5m_gamma_event_url,
    determine_dominance_legs,
    parse_authoritative_close_price,
    parse_authoritative_open_price,
    parse_closed_gamma_event_settlement,
    parse_twap_candle_event,
    verify_same_oracle_pair,
    walk_equal_shares_dominance_box,
    walk_equal_shares_multi_leg_box,
)
from src.polymarket_research.exact_twap_lock_engine import (
    compute_exact_twap_lock_probability,
    read_shm_usd_anchor,
)
from src.polymarket_research.weather_metar_engine import (
    HIGH_VOLUME_WEATHER_SERIES,
    MetarObservation,
    WeatherEventSpec,
    compute_adaptive_metar_poll_ttl,
    compute_weather_probabilities,
    evaluate_weather_event_slate,
    fetch_live_ensemble_hourly_sync,
    fetch_metar_observations_sync,
    fetch_taf_extremes_sync,
    parse_weather_event,
)

DATA_DIR = PROJECT_ROOT / "data" / "alpha124"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "alpha124_shadow_state.json"
LEDGER_FILE = DATA_DIR / "alpha124_shadow_ledger.jsonl"
OPPS_FILE = DATA_DIR / "alpha124_live_opportunities.json"
LOG_FILE = DATA_DIR / "alpha124_shadow.log"
BACKTEST_CAL_FILE = DATA_DIR / "backtest_alpha_124_results.json"
LIVE_POLYMARKET_DIR = PROJECT_ROOT / "data" / "polymarket"
SHOCK_TRIGGER_FILE = LIVE_POLYMARKET_DIR / "live_shock_triggers.jsonl"
LIVE_ALPHA124_STATE_MIRROR_FILE = LIVE_POLYMARKET_DIR / "alpha124_shadow_state.json"
D1_LIVE_CANDIDATES_FILE = LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [ALPHA-124] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("Alpha124Shadow")

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL = "https://clob.polymarket.com"
BINANCE_URL = "https://api.binance.com"

CRYPTO_FEE_RATE = 0.07

# Proven negative-EV / redundant shadow sleeves quarantined in production (`PM_QUARANTINE_LOSING_SLEEVES=1`)
# Documented in `docs/POLYMARKET_EXPERIMENT_GRAVEYARD_AND_LEDGER.md`.
QUARANTINED_SHADOW_SLEEVES = frozenset({
    "M4_SHOCK_STRIKE_CATCHUP",
    "W2_ENSEMBLE_VALUE",
    "W2_MAKER_OVERROUND",
    "M1_SVI_MAKER_SCALP",
    "M2_STRIKE_CONVERGENCE",
    "P1_PREOPEN_MAKER_STRADDLE",
})


def is_shadow_sleeve_quarantined(sleeve: str) -> bool:
    return os.getenv("PM_QUARANTINE_LOSING_SLEEVES", "1") == "1" and sleeve in QUARANTINED_SHADOW_SLEEVES


# Ticket sizing matrix across $100, $1,000, and $5,000 bankrolls (strictly enforces 1.5%-4% cap on B1 tails!)
BANKROLL_TICKETS: Dict[str, Dict[str, float]] = {
    "T100": {
        "W1_SOLAR_PEAK_LOCK": 15.0,
        "W2_ENSEMBLE_VALUE": 10.0,
        "W2_MAKER_OVERROUND": 10.0,
        "W3_WEATHER_SLATE_ARB": 12.0,
        "B1_CONVEX_TAIL_YES": 4.0,
        "B2_BARRIER_NO_LOCK": 15.0,
        "M1_SVI_MAKER_SCALP": 15.0,
        "M2_STRIKE_CONVERGENCE": 15.0,
        "M3_LADDER_MONO_BOX": 20.0,
        "M4_SHOCK_STRIKE_CATCHUP": 15.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 20.0,
        "D1_4H_DOMINANCE_BOX": 20.0,
        "D1_QUIET_BOOK_BOX": 20.0,
        "S5M_CHAINLINK_SNIPER": 15.0,
        "N1_NEGRISK_CROSS_BOX": 20.0,
        "P1_PREOPEN_MAKER_STRADDLE": 16.0,
        "U1_DAILY_UPDOWN_LOCK": 15.0,
        "C1_BINARY_COMPLETE_SET": 20.0,
        "S2_EXACT_TWAP_LOCK": 15.0,
    },
    "T1000": {
        "W1_SOLAR_PEAK_LOCK": 100.0,
        "W2_ENSEMBLE_VALUE": 50.0,
        "W2_MAKER_OVERROUND": 50.0,
        "W3_WEATHER_SLATE_ARB": 80.0,
        "B1_CONVEX_TAIL_YES": 25.0,
        "B2_BARRIER_NO_LOCK": 100.0,
        "M1_SVI_MAKER_SCALP": 100.0,
        "M2_STRIKE_CONVERGENCE": 100.0,
        "M3_LADDER_MONO_BOX": 150.0,
        "M4_SHOCK_STRIKE_CATCHUP": 100.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 100.0,
        "D1_4H_DOMINANCE_BOX": 100.0,
        "D1_QUIET_BOOK_BOX": 100.0,
        "S5M_CHAINLINK_SNIPER": 100.0,
        "N1_NEGRISK_CROSS_BOX": 150.0,
        "P1_PREOPEN_MAKER_STRADDLE": 96.0,
        "U1_DAILY_UPDOWN_LOCK": 100.0,
        "C1_BINARY_COMPLETE_SET": 150.0,
        "S2_EXACT_TWAP_LOCK": 100.0,
    },
    "T5000": {
        "W1_SOLAR_PEAK_LOCK": 350.0,
        "W2_ENSEMBLE_VALUE": 175.0,
        "W2_MAKER_OVERROUND": 175.0,
        "W3_WEATHER_SLATE_ARB": 250.0,
        "B1_CONVEX_TAIL_YES": 75.0,
        "B2_BARRIER_NO_LOCK": 350.0,
        "M1_SVI_MAKER_SCALP": 350.0,
        "M2_STRIKE_CONVERGENCE": 350.0,
        "M3_LADDER_MONO_BOX": 500.0,
        "M4_SHOCK_STRIKE_CATCHUP": 350.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 300.0,
        "D1_4H_DOMINANCE_BOX": 300.0,
        "D1_QUIET_BOOK_BOX": 300.0,
        "S5M_CHAINLINK_SNIPER": 300.0,
        "N1_NEGRISK_CROSS_BOX": 500.0,
        "P1_PREOPEN_MAKER_STRADDLE": 288.0,
        "U1_DAILY_UPDOWN_LOCK": 350.0,
        "C1_BINARY_COMPLETE_SET": 500.0,
        "S2_EXACT_TWAP_LOCK": 300.0,
    },
}


def walk_l2_book_asks(
    asks_raw: List[Dict[str, Any]],
    notional_usd: float,
    fee_rate: float,
    max_slip_cents: float = 0.025,
    min_l1_usd: float = 20.0,
    min_fill_ratio: float = 0.98,
) -> Dict[str, Any]:
    asks = sorted(
        [(float(a["price"]), float(a["size"])) for a in asks_raw if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
        key=lambda x: x[0],
    )
    if not asks:
        return {"filled": False, "reason": "EMPTY_ASK_BOOK", "best_ask": 1.0}
    best_ask = asks[0][0]
    l1_usd = round(best_ask * asks[0][1], 2)
    if l1_usd < min_l1_usd:
        return {"filled": False, "reason": "THIN_L1_DEPTH", "best_ask": best_ask, "l1_usd": l1_usd}
    rem = notional_usd
    spent = 0.0
    shares = 0.0
    levels = 0
    for px, sz in asks:
        if px > best_ask + max_slip_cents or px >= 0.98:
            break
        lvl_usd = px * sz
        levels += 1
        take = min(rem, lvl_usd)
        shares += take / px
        spent += take
        rem -= take
        if rem <= 1e-6:
            break

    if spent < notional_usd * min_fill_ratio or shares <= 0:
        return {"filled": False, "reason": "INSUFFICIENT_DEPTH", "best_ask": best_ask, "l1_usd": l1_usd}

    vwap = spent / shares
    fee_ps = fee_rate * vwap * (1.0 - vwap) if fee_rate > 0 else 0.0
    fee_usd = shares * fee_ps
    eff_px = (spent + fee_usd) / shares
    return {
        "filled": True,
        "best_ask": round(best_ask, 4),
        "vwap": round(vwap, 4),
        "eff_px": round(eff_px, 4),
        "slip_cents": round((vwap - best_ask) * 100.0, 2),
        "spent_usd": round(spent, 2),
        "fee_usd": round(fee_usd, 4),
        "shares": round(shares, 4),
        "fill_ratio": round(spent / notional_usd, 4),
        "l1_usd": l1_usd,
        "levels": levels,
    }


def extract_best_bid(bids_raw: List[Dict[str, Any]]) -> Tuple[float, float]:
    bids = sorted(
        [(float(b["price"]), float(b["size"])) for b in bids_raw if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
        key=lambda x: -x[0],
    )
    if not bids:
        return 0.0, 0.0
    return round(bids[0][0], 4), round(bids[0][0] * bids[0][1], 2)


class Alpha124ShadowDaemon:
    def __init__(self, single_scan: bool = False):
        self.single_scan = single_scan
        self.session: Optional[aiohttp.ClientSession] = None
        self.started_at = datetime.now(timezone.utc).isoformat()

        # Load calibrated parameters from backtest if available
        self.weather_sigma_c = 1.05
        self.barrier_wick_mult = 1.12
        self._load_calibration()

        # Live spot & rolling history
        self.spots: Dict[str, float] = {}
        self.spot_hist: Dict[str, Deque[Tuple[float, float]]] = {
            a: collections.deque(maxlen=600) for a in ("BTC", "ETH", "SOL", "XRP")
        }
        self.usd_spot_hist: Dict[str, Deque[Tuple[float, float]]] = {
            a: collections.deque(maxlen=400) for a in DOMINANCE_ASSETS
        }
        self.usd_direct_flags: Dict[str, bool] = {}

        # Discovered market registries & caches
        self.weather_events: Dict[str, WeatherEventSpec] = {}
        self.barrier_rungs: Dict[str, BarrierRungSpec] = {}
        self.strike_ladders: Dict[str, List[StrikeRungSpec]] = {}
        self.negrisk_ladders: Dict[str, List[NegRiskBracketSpec]] = {}
        self.daily_updown_markets: Dict[str, DailyUpDownSpec] = {}
        self.dominance_pairs: Dict[str, Tuple[TwapCandleMarketSpec, TwapCandleMarketSpec]] = {}
        self.dominance_4h_pairs: Dict[str, Tuple[TwapCandleMarketSpec, TwapCandleMarketSpec]] = {}
        self.twap_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.s5m_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.preopen_15m_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.pending_preopen_straddles: Dict[str, Dict[str, Any]] = {}
        self.chainlink_open_cache: Dict[str, Tuple[float, float]] = {}  # key -> (end_ts, openPrice)
        self.daily_open_cache: Dict[str, Tuple[float, float]] = {}  # key -> (end_ts, binance_open)

        self.metar_cache: Dict[str, Tuple[float, List[MetarObservation]]] = {}
        self.taf_cache: Dict[str, Tuple[float, Dict[str, float]]] = {}
        self.ensemble_cache: Dict[str, Tuple[float, Dict[int, List[float]]]] = {}
        self.barrier_ext_cache: Dict[str, Tuple[float, Tuple[float, float, float]]] = {}
        self._last_w3_slate_chk_ts: Dict[str, float] = {}
        self._open_meteo_sem = asyncio.Semaphore(2)

        self.last_discovery_ts = 0.0
        self.last_weather_scan_ts = 0.0
        self.last_crypto_mid_scan_ts = 0.0
        self.last_dominance_discovery_ts = 0.0
        self.last_4h_discovery_ts = 0.0
        self.last_twap_discovery_ts = 0.0
        self.last_s5m_discovery_ts = 0.0
        self.last_preopen_discovery_ts = 0.0
        self.last_usd_sample_ts = 0.0
        self.cached_mid_opps: List[Dict[str, Any]] = []
        self.cached_weather_opps: List[Dict[str, Any]] = []
        self.cached_shock_opps: List[Dict[str, Any]] = []
        self.cycle_count = 0

        # Reactive <250ms Shock-Trigger Tailer State (M4 + Adverse Maker Cancel + D1 Quiet-Book Gate)
        try:
            self._shock_file_offset: int = SHOCK_TRIGGER_FILE.stat().st_size if SHOCK_TRIGGER_FILE.exists() else 0
        except Exception:
            self._shock_file_offset = 0
        self._seen_shock_ids: Deque[str] = collections.deque(maxlen=256)
        self._last_m4_shock_ts_by_asset: Dict[str, float] = {}
        self._last_any_shock_ts_by_asset: Dict[str, float] = {}
        self._last_d1_live_emit_ts: Dict[str, float] = {}
        self._bg_discovery_task: Optional[asyncio.Task] = None
        self._bg_weather_task: Optional[asyncio.Task] = None
        self._bg_mid_task: Optional[asyncio.Task] = None

        # Shadow Portfolio State (keyed by trade_key)
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.pending_maker_orders: Dict[str, Dict[str, Any]] = {}
        self.closed_positions: List[Dict[str, Any]] = []
        self.entered_keys: set[str] = set()
        self.inflight_keys: set[str] = set()
        self.top_opportunities: List[Dict[str, Any]] = []
        self._hydrate_state()

    def _try_acquire_keys(self, *keys: str) -> List[str]:
        """Synchronously reserves dedupe/event keys before any async `await` (`C-02` / `F-10`)."""
        valid = [str(k) for k in keys if k]
        if not valid:
            return []
        for k in valid:
            if k in self.entered_keys or k in self.inflight_keys:
                return []
        for k in valid:
            self.inflight_keys.add(k)
        return valid

    def _release_inflight_keys(self, keys: List[str]) -> None:
        for k in keys:
            self.inflight_keys.discard(k)

    def _load_calibration(self) -> None:
        if not BACKTEST_CAL_FILE.exists():
            return
        try:
            d = json.loads(BACKTEST_CAL_FILE.read_text(encoding="utf-8"))
            w_sig = d.get("option_1_weather", {}).get("calibrated_sigma_c")
            b_mult = d.get("option_2_barrier_onetouch", {}).get("calibrated_wick_vol_mult")
            if w_sig:
                self.weather_sigma_c = float(w_sig)
            if b_mult:
                self.barrier_wick_mult = float(b_mult)
            logger.info(f"Loaded WFO calibration: weather_sigma_c={self.weather_sigma_c}, barrier_wick_mult={self.barrier_wick_mult}")
        except Exception as exc:
            logger.warning(f"Calibration load notice: {exc}")

    def _hydrate_state(self) -> None:
        if STATE_FILE.exists():
            try:
                st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.started_at = st.get("started_at", self.started_at)
                for p in st.get("open_positions", []):
                    if isinstance(p, dict) and p.get("position_id"):
                        self.open_positions[p["position_id"]] = p
                        self.entered_keys.add(str(p.get("dedupe_key") or p["position_id"]))
                        ev_id = (p.get("extra") or {}).get("event_id")
                        if ev_id:
                            if p.get("sleeve") == "W2_ENSEMBLE_VALUE":
                                self.entered_keys.add(f"W2_EVENT_{ev_id}")
                            elif p.get("sleeve") == "W2_MAKER_OVERROUND":
                                self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                for m_ord in st.get("pending_maker_orders", []):
                    if isinstance(m_ord, dict) and m_ord.get("order_id"):
                        self.pending_maker_orders[m_ord["order_id"]] = m_ord
                        if m_ord.get("dedupe_key"):
                            self.entered_keys.add(str(m_ord["dedupe_key"]))
                        ev_id = (m_ord.get("extra") or {}).get("event_id")
                        if ev_id and m_ord.get("sleeve") == "W2_MAKER_OVERROUND":
                            self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                for p in st.get("recent_closed_positions", []):
                    if isinstance(p, dict):
                        self.closed_positions.append(p)
                        if p.get("dedupe_key"):
                            self.entered_keys.add(str(p["dedupe_key"]))
                        ev_id = (p.get("extra") or {}).get("event_id")
                        if ev_id:
                            if p.get("sleeve") == "W2_ENSEMBLE_VALUE":
                                self.entered_keys.add(f"W2_EVENT_{ev_id}")
                            elif p.get("sleeve") == "W2_MAKER_OVERROUND":
                                self.entered_keys.add(f"W2M_EVENT_{ev_id}")
            except Exception as exc:
                logger.warning(f"State hydrate notice: {exc}")

        if LEDGER_FILE.exists():
            try:
                ledger_open: Dict[str, Dict[str, Any]] = {}
                ledger_maker: Dict[str, Dict[str, Any]] = {}
                closed_ids = {str(p.get("position_id")) for p in self.closed_positions if isinstance(p, dict) and p.get("position_id")}
                with open(LEDGER_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            r = json.loads(line)
                        except Exception:
                            # Skip truncated/corrupt JSONL line without aborting ledger hydration (`F-19`)
                            continue
                        ev = r.get("event")
                        if ev in ("SHADOW_ENTRY", "SHADOW_CLOSE") and r.get("dedupe_key"):
                            self.entered_keys.add(str(r["dedupe_key"]))
                        if ev == "SHADOW_ENTRY":
                            pid = str(r.get("position_id") or "")
                            if pid:
                                pos_rec = {k: v for k, v in r.items() if k != "event"}
                                ledger_open[pid] = pos_rec
                            d_key = str(r.get("dedupe_key") or "")
                            if d_key:
                                for oid_k, m_v in list(ledger_maker.items()):
                                    if str(m_v.get("dedupe_key") or "") == d_key:
                                        ledger_maker.pop(oid_k, None)
                            ev_id = (r.get("extra") or {}).get("event_id")
                            if ev_id:
                                if r.get("sleeve") == "W2_ENSEMBLE_VALUE":
                                    self.entered_keys.add(f"W2_EVENT_{ev_id}")
                                elif r.get("sleeve") == "W2_MAKER_OVERROUND":
                                    self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                        elif ev == "SHADOW_CLOSE":
                            pid = str(r.get("position_id") or "")
                            if pid:
                                ledger_open.pop(pid, None)
                                self.open_positions.pop(pid, None)
                                if pid not in closed_ids:
                                    closed_ids.add(pid)
                                    self.closed_positions.append({k: v for k, v in r.items() if k != "event"})
                        elif ev == "SHADOW_MAKER_POST":
                            oid = str(r.get("order_id") or "")
                            if oid:
                                ledger_maker[oid] = {k: v for k, v in r.items() if k != "event"}
                                if r.get("dedupe_key"):
                                    self.entered_keys.add(str(r["dedupe_key"]))
                                ev_id = (r.get("extra") or {}).get("event_id")
                                if ev_id and r.get("sleeve") == "W2_MAKER_OVERROUND":
                                    self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                        elif ev == "SHADOW_MAKER_CANCEL":
                            oid = str(r.get("order_id") or "")
                            if oid:
                                m_old = ledger_maker.pop(oid, None)
                                self.pending_maker_orders.pop(oid, None)
                                if m_old and m_old.get("dedupe_key"):
                                    self.entered_keys.discard(str(m_old["dedupe_key"]))
                                ev_id = ((m_old or r).get("extra") or {}).get("event_id")
                                if ev_id and (m_old or r).get("sleeve") == "W2_MAKER_OVERROUND":
                                    self.entered_keys.discard(f"W2M_EVENT_{ev_id}")

                for pid, pos_rec in ledger_open.items():
                    if pid not in self.open_positions and pid not in closed_ids:
                        self.open_positions[pid] = pos_rec
                for oid, m_rec in ledger_maker.items():
                    if oid not in self.pending_maker_orders:
                        self.pending_maker_orders[oid] = m_rec
            except Exception as exc:
                logger.warning(f"Ledger hydrate notice: {exc}")

        if self.closed_positions:
            self.closed_positions.sort(key=lambda p: float(p.get("closed_ts") or 0.0))

        # Evict any lingering resting Maker orders belonging to quarantined losing sleeves
        for oid_q, m_q in list(self.pending_maker_orders.items()):
            if is_shadow_sleeve_quarantined(str(m_q.get("sleeve") or "")):
                self.pending_maker_orders.pop(oid_q, None)
                self._append_ledger({"event": "SHADOW_MAKER_CANCEL", "reason": "SLEEVE_QUARANTINED", **m_q})
        if is_shadow_sleeve_quarantined("P1_PREOPEN_MAKER_STRADDLE"):
            self.pending_preopen_straddles.clear()

    def _append_ledger(self, rec: Dict[str, Any]) -> None:
        with open(LEDGER_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=40),
                headers={"User-Agent": "DominusAlpha124Shadow/1.0", "Accept": "application/json"},
                max_line_size=65536,
                max_field_size=65536,
            )
        return self.session

    async def fetch_json(self, url: str, timeout: float = 5.0) -> Any:
        sess = await self.get_session()
        try:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            return None
        return None

    async def fetch_book_after_latency(self, token_id: str, latency_ms: int = 50) -> Optional[Dict[str, Any]]:
        if latency_ms > 0:
            await asyncio.sleep(latency_ms / 1000.0)
        return await self.fetch_json(f"{CLOB_URL}/book?token_id={token_id}", timeout=3.5)

    def record_usd_spot_samples(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        self.last_usd_sample_ts = now
        for asset in DOMINANCE_ASSETS:
            shm = read_shm_usd_anchor(asset, now, max_age_sec=2.5)
            usd_px = shm.get("usd_spot")
            src = str(shm.get("source") or "")
            if usd_px and float(usd_px) > 0:
                self.usd_spot_hist[asset].append((now, float(usd_px)))
                self.usd_direct_flags[asset] = src in ("shm_chainlink_proxy", "shm_coinbase_usd")

    async def update_crypto_spots(self) -> None:
        now = time.time()
        data = await self.fetch_json(f"{BINANCE_URL}/api/v3/ticker/price", timeout=3.5)
        if isinstance(data, list):
            sym_map = {v: k for k, v in ASSET_BINANCE_SYMBOL.items()}
            for item in data:
                sym = item.get("symbol")
                if sym in sym_map:
                    asset = sym_map[sym]
                    px = float(item["price"])
                    self.spots[asset] = px
                    self.spot_hist[asset].append((now, px))
        self.record_usd_spot_samples(now)

    @staticmethod
    def _hist_return_bps(hist: Optional[Deque[Tuple[float, float]]], lookback_sec: float) -> float:
        if not hist or len(hist) < 2:
            return 0.0
        now, cur = hist[-1]
        # Never compare hist[-1] against itself when prior samples are > lookback_sec apart!
        ref = hist[-2][1]
        for idx in range(len(hist) - 1):
            ts, px = hist[idx]
            if now - ts <= lookback_sec:
                ref = px
                break
        return ((cur - ref) / ref) * 10000.0 if ref > 0 else 0.0

    def get_return_bps(self, asset: str, lookback_sec: float) -> float:
        r_spot = self._hist_return_bps(self.spot_hist.get(asset), lookback_sec)
        r_usd = self._hist_return_bps(self.usd_spot_hist.get(asset), lookback_sec)
        return r_usd if abs(r_usd) > abs(r_spot) else r_spot

    async def discover_all_markets(self) -> None:
        logger.info("Discovering active Weather (#1), Barrier Hit (#2), Multi-Strike (#4), NegRisk, and Daily Up/Down markets...")
        # 1. Scan top 600 active events by 24h volume + explicit high-volume Asian/Global METAR series (`Chengdu`, `Beijing`, `Seoul`)
        weather_found: Dict[str, WeatherEventSpec] = {}
        for offset in range(0, 600, 100):
            evts = await self.fetch_json(
                f"{GAMMA_URL}/events?closed=false&order=volume24hr&ascending=false&limit=100&offset={offset}",
                timeout=7.0,
            )
            if not isinstance(evts, list) or not evts:
                break
            for ev in evts:
                sp = parse_weather_event(ev)
                if sp is not None:
                    weather_found[sp.event_id] = sp
        for w_slug in HIGH_VOLUME_WEATHER_SERIES:
            evts_w = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={w_slug}&closed=false&limit=3", timeout=5.0)
            if isinstance(evts_w, list):
                for ev in evts_w:
                    sp = parse_weather_event(ev, series_slug_hint=w_slug)
                    if sp is not None:
                        weather_found[sp.event_id] = sp
        self.weather_events = weather_found

        # 2. Discover active Hit/Barrier series (#2)
        barrier_found: Dict[str, BarrierRungSpec] = {}
        for asset, h_grp, slug in HIT_SERIES:
            evts = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5", timeout=6.0)
            if isinstance(evts, list):
                for ev in evts:
                    for r in parse_hit_event(ev, asset, h_grp, slug):
                        if r.end_ts > time.time() + 60:
                            barrier_found[r.market_id] = r
        self.barrier_rungs = barrier_found

        # 3. Discover active Multi-Strike series (#4) + NegRisk Bracket series (`N1_NEGRISK_CROSS_BOX`)
        strike_found: Dict[str, List[StrikeRungSpec]] = {}
        for asset, slug in STRIKE_SERIES:
            evts = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5", timeout=6.0)
            if isinstance(evts, list):
                for ev in evts:
                    rungs = parse_multistrike_event(ev, asset, slug)
                    if rungs and rungs[0].end_ts > time.time() + 60:
                        strike_found[f"{asset}_{ev.get('id')}"] = rungs
        self.strike_ladders = strike_found

        negrisk_found: Dict[str, List[NegRiskBracketSpec]] = {}
        for asset, slug in NEGRISK_SERIES:
            evts_nr = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4", timeout=6.0)
            if isinstance(evts_nr, list):
                for ev in evts_nr:
                    brs = parse_negrisk_bracket_event(ev, asset, slug)
                    if brs and brs[0].end_ts > time.time() + 60:
                        negrisk_found[f"{asset}_{int(brs[0].end_ts)}"] = brs
        self.negrisk_ladders = negrisk_found

        # 4. Discover active Daily Up/Down series (`U1_DAILY_UPDOWN_LOCK`)
        updown_found: Dict[str, DailyUpDownSpec] = {}
        for asset, slug in DAILY_UPDOWN_SERIES:
            evts_ud = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3", timeout=5.0)
            if isinstance(evts_ud, list):
                for ev in evts_ud:
                    sp_ud = parse_daily_updown_event(ev, asset, slug)
                    if sp_ud is not None and sp_ud.end_ts > time.time() + 60:
                        updown_found[sp_ud.market_id] = sp_ud
        self.daily_updown_markets = updown_found

        self.last_discovery_ts = time.time()
        logger.info(
            f"Discovery complete: {len(self.weather_events)} Weather city-events, "
            f"{len(self.barrier_rungs)} Barrier Hit rungs, {len(self.strike_ladders)} Multi-Strike ladders, "
            f"{len(self.negrisk_ladders)} NegRisk ladders, {len(self.daily_updown_markets)} Daily Up/Down markets."
        )

    async def open_shadow_position(
        self,
        sleeve: str,
        dedupe_key: str,
        asset_or_city: str,
        title: str,
        side_label: str,
        token_id: str,
        fee_rate: float,
        p_model: float,
        close_ts: float,
        extra: Dict[str, Any],
        tp_target_px: Optional[float] = None,
        prefetched_book: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if is_shadow_sleeve_quarantined(sleeve):
            return False
        lock_keys = [dedupe_key]
        if sleeve == "W2_ENSEMBLE_VALUE" and extra.get("event_id"):
            lock_keys.append(f"W2_EVENT_{extra['event_id']}")
        acq = self._try_acquire_keys(*lock_keys)
        if not acq:
            return False

        try:
            # Strictly causal L2 walk at t_signal + 50ms (or single-RTT book already fetched on M4 wakeup)
            book = prefetched_book if prefetched_book is not None else await self.fetch_book_after_latency(token_id, latency_ms=50)
            if not book:
                return False
            asks_raw = book.get("asks") or []
            bids_raw = book.get("bids") or []
            best_bid, _ = extract_best_bid(bids_raw)

            min_l1 = 15.0 if sleeve in ("S2_EXACT_TWAP_LOCK", "S5M_CHAINLINK_SNIPER") else 20.0
            # Validate T1000 reference fill first
            ref_ticket = BANKROLL_TICKETS["T1000"][sleeve]
            w_ref = walk_l2_book_asks(asks_raw, ref_ticket, fee_rate=fee_rate, min_l1_usd=min_l1)
            if not w_ref.get("filled"):
                return False

            realized_edge = p_model - float(w_ref["eff_px"])
            min_req_edge = {
                "W1_SOLAR_PEAK_LOCK": 0.035,
                "W2_ENSEMBLE_VALUE": 0.095,
                "B1_CONVEX_TAIL_YES": 0.060,
                "B2_BARRIER_NO_LOCK": 0.035,
                "M1_SVI_MAKER_SCALP": 0.050,
                "M2_STRIKE_CONVERGENCE": 0.038,
                "M4_SHOCK_STRIKE_CATCHUP": 0.065,
                "S5M_CHAINLINK_SNIPER": 0.042,
                "U1_DAILY_UPDOWN_LOCK": 0.040,
                "S2_EXACT_TWAP_LOCK": 0.030,
            }.get(sleeve, 0.035)
            if realized_edge < min_req_edge:
                return False

            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = walk_l2_book_asks(asks_raw, t_map[sleeve], fee_rate=fee_rate, min_l1_usd=min_l1)
                if w_t.get("filled"):
                    tier_fills[tier_name] = w_t

            if not tier_fills:
                return False

            now = time.time()
            pos_id = f"{sleeve}_{int(now)}_{dedupe_key[-10:]}"
            eff_tp = tp_target_px
            if sleeve == "M1_SVI_MAKER_SCALP" and eff_tp is None:
                eff_tp = min(0.96, round(float(w_ref["eff_px"]) + 0.050, 4))
            elif sleeve == "M4_SHOCK_STRIKE_CATCHUP" and eff_tp is None:
                eff_tp = min(0.96, round(float(w_ref["eff_px"]) + 0.060, 4))
            elif sleeve == "B1_CONVEX_TAIL_YES" and eff_tp is None:
                eff_tp = min(0.88, round(2.0 * float(w_ref["vwap"]), 4))
            elif sleeve == "S5M_CHAINLINK_SNIPER" and eff_tp is None:
                eff_tp = 0.96
            elif sleeve in ("W1_SOLAR_PEAK_LOCK", "B2_BARRIER_NO_LOCK", "M2_STRIKE_CONVERGENCE", "U1_DAILY_UPDOWN_LOCK") and eff_tp is None:
                eff_tp = 0.98

            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve,
                "asset_or_city": asset_or_city,
                "title": title,
                "side": side_label,
                "token_id": token_id,
                "fee_rate": fee_rate,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": round(p_model, 4),
                "entry_eff_px_t1000": w_ref["eff_px"],
                "entry_vwap_t1000": w_ref["vwap"],
                "realized_edge_t1000": round(realized_edge, 4),
                "entry_best_bid": best_bid,
                "last_bid": best_bid,
                "maker_tp_px": eff_tp,
                "tier_fills": tier_fills,
                "extra": extra,
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(
                f"[ENTRY:{sleeve}] {asset_or_city} | {title} ({side_label}) @ eff=${w_ref['eff_px']:.3f} "
                f"vs p_mod={p_model:.3f} (edge={realized_edge:+.3f}, L1=${w_ref['l1_usd']:.0f})"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    async def post_shadow_maker_entry(
        self,
        sleeve: str,
        dedupe_key: str,
        asset: str,
        title: str,
        side_label: str,
        token_id: str,
        p_model: float,
        close_ts: float,
        extra: Dict[str, Any],
        prefetched_book: Optional[Dict[str, Any]] = None,
        ttl_override_sec: Optional[float] = None,
    ) -> bool:
        """
        Places a realistic resting `post_only=True` 0%-fee Maker limit bid on the CLOB.
        Models L1 queue priority (`queue_ahead_usd`) and adverse-selection fills during
        the cancel-reaction latency window (`F-03` / `M-04`).
        """
        if is_shadow_sleeve_quarantined(sleeve):
            return False
        is_weather_maker = sleeve == "W2_MAKER_OVERROUND"
        lock_keys = [dedupe_key]
        if is_weather_maker and extra.get("event_id"):
            lock_keys.append(f"W2M_EVENT_{extra['event_id']}")
        acq = self._try_acquire_keys(*lock_keys)
        if not acq:
            return False

        try:
            book = prefetched_book if prefetched_book is not None else await self.fetch_book_after_latency(token_id, latency_ms=50)
            if not book:
                return False
            asks_raw = book.get("asks") or []
            bids_raw = book.get("bids") or []
            best_bid, l1_bid_usd = extract_best_bid(bids_raw)
            valid_asks = [float(a["price"]) for a in asks_raw if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0]
            if not valid_asks:
                return False
            best_ask = round(min(valid_asks), 4)
            if best_ask <= 0.03 or best_bid <= 0.0:
                return False

            if is_weather_maker and ((best_ask - best_bid) < 0.02 or l1_bid_usd < 10.0):
                return False

            # Post-only Maker bid: step +1c inside wide spread or join best_bid when 1c tight, strictly < best_ask
            cand_bid = best_bid + 0.01 if (best_ask - best_bid) >= 0.02 else best_bid
            resting_bid = round(min(cand_bid, best_ask - 0.01), 4)
            min_rb = 0.14 if is_weather_maker else 0.18
            max_rb = 0.65 if is_weather_maker else 0.80
            if not (min_rb <= resting_bid <= max_rb):
                return False
            maker_edge = p_model - resting_bid
            min_edge = 0.085 if is_weather_maker else 0.060
            if maker_edge < min_edge:
                return False

            # Price-improving +1c establishes top-of-queue (`0.0` ahead); joining existing best_bid sits behind L1 queue
            queue_ahead_usd = 0.0 if resting_bid > best_bid else round(min(l1_bid_usd * 0.50, 60.0), 2)

            now = time.time()
            order_id = f"MKR_{sleeve}_{int(now)}_{dedupe_key[-10:]}"
            spot_now = self.spots.get(asset, 0.0)
            m_ord = {
                "order_id": order_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve,
                "asset_or_city": asset,
                "title": title,
                "side": side_label,
                "token_id": token_id,
                "resting_bid": resting_bid,
                "best_bid_at_post": best_bid,
                "best_ask_at_post": best_ask,
                "l1_bid_usd": l1_bid_usd,
                "queue_ahead_usd": queue_ahead_usd,
                "p_model_at_post": round(p_model, 4),
                "maker_edge_at_post": round(maker_edge, 4),
                "spot_at_post": spot_now,
                "created_ts": now,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "ttl_override_sec": ttl_override_sec,
                "extra": extra,
            }
            self.pending_maker_orders[order_id] = m_ord
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_MAKER_POST", **m_ord})
            logger.info(
                f"[MAKER_POST:{sleeve}] {asset} | {title} ({side_label}) resting_bid=${resting_bid:.3f} "
                f"(ask=${best_ask:.3f}, q_ahead=${queue_ahead_usd:.0f}, p_mod={p_model:.3f}, edge={maker_edge:+.3f})"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    async def manage_pending_maker_orders(self) -> None:
        now = time.time()
        now_utc = datetime.now(timezone.utc)
        for oid, m_ord in list(self.pending_maker_orders.items()):
            sleeve = m_ord["sleeve"]
            is_weather_maker = sleeve == "W2_MAKER_OVERROUND"
            asset = m_ord["asset_or_city"]
            tok = m_ord["token_id"]
            resting_bid = float(m_ord["resting_bid"])
            close_ts = float(m_ord["close_ts"])
            rem_tte = close_ts - now
            age_s = now - float(m_ord["created_ts"])
            extra = dict(m_ord.get("extra") or {})
            strike = float(extra.get("strike") or 0.0)
            is_down = bool(extra.get("is_downward"))
            side_lbl = m_ord["side"]
            wins_up = (side_lbl == "YES" and not is_down) or (side_lbl == "NO" and is_down)

            def _discard_maker_keys(ord_obj: Dict[str, Any]) -> None:
                self.entered_keys.discard(ord_obj["dedupe_key"])
                ev_id = (ord_obj.get("extra") or {}).get("event_id")
                if ev_id and ord_obj.get("sleeve") == "W2_MAKER_OVERROUND":
                    self.entered_keys.discard(f"W2M_EVENT_{ev_id}")

            # 1. Expiry / TTL cancel (supports short 3.5s reactive M4 post_only maker quotes via ttl_override_sec)
            ttl_ov = m_ord.get("ttl_override_sec")
            min_tte_cancel = 900.0 if ttl_ov is not None else (3600.0 if is_weather_maker else 7200.0)
            max_age_cancel = float(ttl_ov) if ttl_ov is not None else (2700.0 if is_weather_maker else 1800.0)
            if rem_tte <= min_tte_cancel or age_s >= max_age_cancel:
                self.pending_maker_orders.pop(oid, None)
                _discard_maker_keys(m_ord)
                self._append_ledger({"event": "SHADOW_MAKER_CANCEL", "reason": "TTL_OR_EXPIRY", **m_ord})
                continue

            # 2. Evaluate adverse-selection triggers (`F-03` / `M-04`: verify CLOB didn't already sweep us during cancel RTT!)
            adverse_cancel_reason: Optional[str] = None
            p_fair_now = float(m_ord["p_model_at_post"])
            if is_weather_maker:
                ev_id_str = str(extra.get("event_id") or "")
                sp_w = self.weather_events.get(ev_id_str)
                if sp_w is not None:
                    m_key = f"{sp_w.icao}_{sp_w.obs_date.isoformat()}"
                    metars_c = (self.metar_cache.get(m_key) or (0.0, []))[1]
                    ens_c = (self.ensemble_cache.get(sp_w.icao) or (0.0, {}))[1]
                    if metars_c or ens_c:
                        w_res = compute_weather_probabilities(
                            sp_w, now_utc, metars_c, ens_c, forecast_sigma_base_c=self.weather_sigma_c
                        )
                        mkt_id_target = str(extra.get("market_id") or "")
                        for b_idx, b_item in enumerate(sp_w.buckets):
                            if str(b_item.market_id) == mkt_id_target and b_idx < len(w_res["probs"]):
                                p_fair_now = float(w_res["probs"][b_idx])
                                break
                        if w_res.get("convective_cold_pool"):
                            adverse_cancel_reason = "CONVECTIVE_COLD_POOL"
                        elif (p_fair_now - resting_bid) < 0.045:
                            adverse_cancel_reason = "ADVERSE_METAR_OR_EDGE_DECAY"
            else:
                spot_now = self.spots.get(asset, 0.0)
                spot_post = float(m_ord.get("spot_at_post") or 0.0)
                if spot_now > 0 and strike > 0:
                    svi_ev = evaluate_svi_digital_fair_value(asset, spot_now, strike, rem_tte, is_downward=is_down, now_ts=now)
                    p_fair_now = float(svi_ev["p_yes"] if side_lbl == "YES" else svi_ev["p_no"])
                if spot_now > 0 and spot_post > 0:
                    move_bps = ((spot_now - spot_post) / spot_post) * 10000.0
                    if (wins_up and move_bps < -20.0) or ((not wins_up) and move_bps > 20.0):
                        adverse_cancel_reason = "ADVERSE_SPOT_IMPULSE"
                if adverse_cancel_reason is None and spot_now > 0 and strike > 0 and (p_fair_now - resting_bid) < 0.035:
                    adverse_cancel_reason = "SVI_EDGE_DECAY"

            bk: Optional[Dict[str, Any]] = None
            adverse_fill_during_cancel = False
            if adverse_cancel_reason is not None:
                if age_s >= 0.35:
                    bk_adv = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=2.5)
                    if bk_adv:
                        adv_asks = [
                            float(a["price"])
                            for a in (bk_adv.get("asks") or [])
                            if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0
                        ]
                        if adv_asks and min(adv_asks) <= resting_bid:
                            # Fast taker swept through our resting bid before our cancel arrived!
                            bk = bk_adv
                            adverse_fill_during_cancel = True
                if not adverse_fill_during_cancel:
                    self.pending_maker_orders.pop(oid, None)
                    _discard_maker_keys(m_ord)
                    self._append_ledger({"event": "SHADOW_MAKER_CANCEL", "reason": adverse_cancel_reason, **m_ord})
                    continue

            # 3. Check passive Maker fill (`best_ask <= resting_bid` after min resting time, or adverse cancel-race sweep)
            if not adverse_fill_during_cancel:
                min_rest_sec = 0.5 if ttl_ov is not None else 10.0
                if age_s < min_rest_sec:
                    continue
                bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=3.0)
            if not bk:
                continue
            asks_raw = bk.get("asks") or []
            valid_asks = [float(a["price"]) for a in asks_raw if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0]
            if not valid_asks:
                continue
            best_ask_now = min(valid_asks)
            if best_ask_now <= resting_bid:
                crossing_shares = sum(
                    float(a["size"])
                    for a in asks_raw
                    if 0.0 < float(a.get("price", 0)) <= resting_bid + 1e-9 and float(a.get("size", 0)) > 0
                )
                queue_ahead_usd = float(m_ord.get("queue_ahead_usd") or 0.0)
                queue_ahead_sh = queue_ahead_usd / max(0.01, resting_bid)
                avail_fill_shares = crossing_shares - queue_ahead_sh
                if adverse_fill_during_cancel:
                    avail_fill_shares = max(avail_fill_shares, crossing_shares, BANKROLL_TICKETS["T5000"][sleeve] / max(0.01, resting_bid))
                elif avail_fill_shares < 5.0:
                    m_ord["queue_ahead_usd"] = round(max(0.0, queue_ahead_usd - crossing_shares * resting_bid), 2)
                    continue

                self.pending_maker_orders.pop(oid, None)
                tier_fills: Dict[str, Dict[str, Any]] = {}
                for tier_name, t_map in BANKROLL_TICKETS.items():
                    notional = t_map[sleeve]
                    target_sh = notional / resting_bid
                    sh = round(min(target_sh, avail_fill_shares), 4)
                    spent = round(sh * resting_bid, 2)
                    tier_fills[tier_name] = {
                        "filled": True,
                        "best_ask": round(best_ask_now, 4),
                        "vwap": resting_bid,
                        "eff_px": resting_bid,
                        "slip_cents": 0.0,
                        "spent_usd": spent,
                        "fee_usd": 0.0,
                        "shares": sh,
                        "fill_ratio": round(min(1.0, spent / max(0.01, notional)), 4),
                        "l1_usd": m_ord.get("l1_bid_usd", 50.0),
                        "levels": 1,
                    }
                pos_id = f"{sleeve}_{int(now)}_{m_ord['dedupe_key'][-10:]}"
                if is_weather_maker:
                    eff_tp = min(0.95, round(max(resting_bid + 0.070, p_fair_now - 0.015), 4))
                else:
                    eff_tp = min(0.96, round(resting_bid + 0.050, 4))
                if adverse_fill_during_cancel:
                    extra["adverse_fill_during_cancel_window"] = True
                    extra["adverse_trigger"] = adverse_cancel_reason
                pos = {
                    "position_id": pos_id,
                    "dedupe_key": m_ord["dedupe_key"],
                    "sleeve": sleeve,
                    "asset_or_city": asset,
                    "title": m_ord["title"],
                    "side": side_lbl,
                    "token_id": tok,
                    "fee_rate": 0.0,
                    "entry_ts": now,
                    "entry_utc": datetime.now(timezone.utc).isoformat(),
                    "close_ts": close_ts,
                    "p_model_entry": round(p_fair_now, 4),
                    "entry_eff_px_t1000": resting_bid,
                    "entry_vwap_t1000": resting_bid,
                    "realized_edge_t1000": round(p_fair_now - resting_bid, 4),
                    "entry_best_bid": resting_bid,
                    "last_bid": resting_bid,
                    "maker_tp_px": eff_tp,
                    "tier_fills": tier_fills,
                    "extra": extra,
                    "status": "OPEN",
                }
                self.open_positions[pos_id] = pos
                self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                logger.info(
                    f"[MAKER_FILLED:{sleeve}] {asset} | {pos['title']} ({side_lbl}) @ resting=${resting_bid:.3f} "
                    f"-> TP=${eff_tp:.3f} (p_mod={p_fair_now:.3f}, adverse={adverse_fill_during_cancel})"
                )

    async def scan_weather_markets(self, opps_out: List[Dict[str, Any]]) -> None:
        now_utc = datetime.now(timezone.utc)
        loop = asyncio.get_running_loop()

        for sp in list(self.weather_events.values()):
            # Adaptive METAR poll cadence (`Gemini #11`): 10s inside station release window, 300s outside!
            m_key = f"{sp.icao}_{sp.obs_date.isoformat()}"
            now_s = time.time()
            cached_m = self.metar_cache.get(m_key)
            metar_ttl = compute_adaptive_metar_poll_ttl(sp.icao, cached_m[1] if cached_m else None, now_utc)
            if cached_m is None or (now_s - cached_m[0]) >= metar_ttl:
                metars = await loop.run_in_executor(
                    None, fetch_metar_observations_sync, sp.icao, sp.obs_date, sp.tz_name
                )
                self.metar_cache[m_key] = (now_s, metars)
            else:
                metars = cached_m[1]

            # Official AviationWeather TAF TX/TN prior (`Gemini #11`, refreshed every 30m)
            cached_taf = self.taf_cache.get(m_key)
            if cached_taf is None or (now_s - cached_taf[0]) >= 1800.0:
                taf_ext = await loop.run_in_executor(
                    None, fetch_taf_extremes_sync, sp.icao, sp.obs_date, sp.tz_name
                )
                self.taf_cache[m_key] = (now_s, taf_ext)
            else:
                taf_ext = cached_taf[1]

            # Refresh 71-member Ensemble cache every 25 minutes per ICAO (throttled; never cache empty failures for 25m)
            cached_e = self.ensemble_cache.get(sp.icao)
            ens_ttl = 1500.0 if (cached_e and cached_e[1]) else 60.0
            if cached_e is None or (now_s - cached_e[0]) >= ens_ttl:
                async with self._open_meteo_sem:
                    ens_h = await loop.run_in_executor(None, fetch_live_ensemble_hourly_sync, sp.lat, sp.lon)
                    await asyncio.sleep(0.18)
                self.ensemble_cache[sp.icao] = (now_s, ens_h)
            else:
                ens_h = cached_e[1]

            if not ens_h and not metars:
                continue

            res = compute_weather_probabilities(
                sp,
                now_utc,
                metars,
                ens_h,
                forecast_sigma_base_c=self.weather_sigma_c,
                taf_extreme_c=(taf_ext or {}).get(sp.metric),
            )
            probs = res["probs"]
            try:
                end_ts = datetime.fromisoformat(sp.end_date_iso.replace("Z", "+00:00")).timestamp()
            except Exception:
                end_ts = now_s + 86400.0

            # 1. Check W1_SOLAR_PEAK_LOCK
            if res["is_solar_lock"] and res["locked_bucket_idx"] is not None:
                b_lock = sp.buckets[res["locked_bucket_idx"]]
                p_lock = res["p_locked_bucket"]
                w1_fee = float(getattr(b_lock, "fee_rate", 0.0) or 0.0)
                bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={b_lock.yes_token}", timeout=3.5)
                if bk:
                    w_chk = walk_l2_book_asks(bk.get("asks") or [], 100.0, fee_rate=w1_fee)
                    if w_chk.get("filled") and 0.52 <= w_chk["eff_px"] <= 0.94:
                        edge = p_lock - w_chk["eff_px"]
                        opps_out.append({
                            "sleeve": "W1_SOLAR_PEAK_LOCK",
                            "market": f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b_lock.label}",
                            "ask_vwap": w_chk["eff_px"],
                            "p_model": p_lock,
                            "net_edge": round(edge, 4),
                            "l1_usd": w_chk["l1_usd"],
                        })
                        if edge >= 0.035:
                            await self.open_shadow_position(
                                sleeve="W1_SOLAR_PEAK_LOCK",
                                dedupe_key=f"W1_{sp.event_id}_{b_lock.market_id}",
                                asset_or_city=f"{sp.city}_{sp.icao}",
                                title=f"{sp.title} [{b_lock.label}]",
                                side_label="YES",
                                token_id=b_lock.yes_token,
                                fee_rate=w1_fee,
                                p_model=p_lock,
                                close_ts=end_ts,
                                extra={
                                    "event_id": sp.event_id,
                                    "market_id": b_lock.market_id,
                                    "condition_id": b_lock.condition_id,
                                    "icao": sp.icao,
                                    "obs_date": sp.obs_date.isoformat(),
                                    "bucket_label": b_lock.label,
                                    "running_ext_c": res["running_ext_c"],
                                    "cooling_cushion_c": res["cooling_cushion_c"],
                                },
                                prefetched_book=bk,
                            )

            # 1B. Event-Level Weather Slate Arbitrage (`W3_WEATHER_SLATE_ARB`, `Gemini #10` + `ChatGPT #5`)
            # Throttled to once per 300s per event_id so 77+ city slates don't trigger 800+ HTTP calls/cycle.
            slate_key = f"W3_SLATE_{sp.event_id}"
            last_w3_chk = float(self._last_w3_slate_chk_ts.get(sp.event_id) or 0.0)
            if (
                slate_key not in self.entered_keys
                and slate_key not in self.inflight_keys
                and len(sp.buckets) >= 4
                and (self.single_scan or (now_s - last_w3_chk) >= 300.0)
            ):
                self._last_w3_slate_chk_ts[sp.event_id] = now_s
                all_bks = await asyncio.gather(
                    *[self.fetch_json(f"{CLOB_URL}/book?token_id={b_i.yes_token}", timeout=2.5) for b_i in sp.buckets]
                )
                bucket_book_map: Dict[str, Dict[str, Any]] = {}
                raw_bk_by_mkt: Dict[str, Dict[str, Any]] = {}
                for b_i, bk_i in zip(sp.buckets, all_bks):
                    if bk_i:
                        raw_bk_by_mkt[b_i.market_id] = bk_i
                        asks_i = sorted(
                            [(float(a["price"]), float(a["size"])) for a in (bk_i.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
                            key=lambda x: x[0],
                        )
                        if asks_i:
                            bucket_book_map[b_i.market_id] = {"ask_yes": asks_i[0][0], "ask_yes_shares": asks_i[0][1]}
                slate_ev = evaluate_weather_event_slate(
                    sp, probs, bucket_book_map, target_budget_usd=BANKROLL_TICKETS["T1000"]["W3_WEATHER_SLATE_ARB"]
                )
                full_arb = slate_ev.get("full_slate_arb")
                if full_arb:
                    opps_out.append({
                        "sleeve": "W3_WEATHER_SLATE_ARB",
                        "market": f"{sp.city} ({sp.icao}) {sp.obs_date} Full-Slate ({len(sp.buckets)} buckets)",
                        "ask_vwap": full_arb["sum_asks"],
                        "p_model": 1.0,
                        "net_edge": full_arb["guaranteed_edge_per_set"],
                        "l1_usd": full_arb["total_cost_usd"],
                    })
                    await self.open_shadow_weather_slate(sp, full_arb, end_ts)
            else:
                raw_bk_by_mkt = {}

            if is_shadow_sleeve_quarantined("W2_ENSEMBLE_VALUE") and is_shadow_sleeve_quarantined("W2_MAKER_OVERROUND"):
                continue

            # 2. Check W2_ENSEMBLE_VALUE (Taker) & W2_MAKER_OVERROUND (0%-fee Post-Only Maker inside ~1.07 overround):
            #    require full >= 50-member ensemble, tight IQR <= 2.2°C, and max 1 W2 exposure per event_id!
            ens_members_n = int(res.get("ensemble_member_count") or 0)
            peak_iqr_c = float(res.get("peak_iqr_c") or 0.0)
            event_w2_taken = f"W2_EVENT_{sp.event_id}" in self.entered_keys or f"W2_EVENT_{sp.event_id}" in self.inflight_keys
            event_w2m_taken = f"W2M_EVENT_{sp.event_id}" in self.entered_keys or f"W2M_EVENT_{sp.event_id}" in self.inflight_keys
            best_w2_cand: Optional[Tuple[float, float, float, Any, Dict[str, Any]]] = None  # (edge, p_mod, eff_px, bucket, bk)
            best_w2m_cand: Optional[Tuple[float, float, float, Any, Dict[str, Any]]] = None  # (maker_edge, p_mod, resting_bid, bucket, bk)

            top_indices = sorted(range(len(probs)), key=lambda i: -probs[i])[:2]
            for idx in top_indices:
                p_mod = probs[idx]
                if p_mod < 0.24:
                    continue
                b = sp.buckets[idx]
                b_fee = float(getattr(b, "fee_rate", 0.0) or 0.0)
                bk = raw_bk_by_mkt.get(b.market_id) or await self.fetch_json(f"{CLOB_URL}/book?token_id={b.yes_token}", timeout=3.5)
                if not bk:
                    continue

                # 2A. Evaluate 0%-fee resting Maker quote inside multi-cent Weather spread (`F-12`: strictly zero-fee markets)
                asks_raw_b = bk.get("asks") or []
                bids_raw_b = bk.get("bids") or []
                best_bid_b, l1_bid_usd_b = extract_best_bid(bids_raw_b)
                valid_asks_b = [
                    float(a["price"]) for a in asks_raw_b if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0
                ]
                if b_fee == 0.0 and valid_asks_b and best_bid_b > 0 and (min(valid_asks_b) - best_bid_b) >= 0.02:
                    best_ask_b = round(min(valid_asks_b), 4)
                    resting_bid_b = round(min(best_bid_b + 0.01, best_ask_b - 0.01), 4)
                    maker_edge_b = p_mod - resting_bid_b
                    if 0.14 <= resting_bid_b <= 0.65 and maker_edge_b >= 0.055 and ens_members_n >= 50 and l1_bid_usd_b >= 10.0:
                        opps_out.append({
                            "sleeve": "W2_MAKER_OVERROUND",
                            "market": f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label} [MakerBid]",
                            "ask_vwap": resting_bid_b,
                            "p_model": round(p_mod, 4),
                            "net_edge": round(maker_edge_b, 4),
                            "l1_usd": l1_bid_usd_b,
                        })
                    if (
                        not event_w2_taken
                        and not event_w2m_taken
                        and (end_ts - now_s) >= 5400.0
                        and ens_members_n >= 50
                        and peak_iqr_c <= 2.2
                        and not res.get("convective_cold_pool")
                        and l1_bid_usd_b >= 10.0
                        and 0.14 <= resting_bid_b <= 0.62
                        and p_mod >= 0.30
                        and maker_edge_b >= 0.085
                    ):
                        if best_w2m_cand is None or maker_edge_b > best_w2m_cand[0]:
                            best_w2m_cand = (maker_edge_b, p_mod, resting_bid_b, b, bk)

                # 2B. Evaluate Taker fill when Ask itself offers >= 9.5c MOS ensemble edge (accounting for b_fee if enabled)
                w_chk = walk_l2_book_asks(asks_raw_b, 50.0, fee_rate=b_fee)
                if not w_chk.get("filled"):
                    continue
                eff_px = w_chk["eff_px"]
                edge = p_mod - eff_px
                if 0.10 <= eff_px <= 0.62 and edge >= 0.04 and ens_members_n >= 50:
                    opps_out.append({
                        "sleeve": "W2_ENSEMBLE_VALUE",
                        "market": f"{sp.city} ({sp.icao}) {sp.obs_date} -> {b.label}",
                        "ask_vwap": eff_px,
                        "p_model": round(p_mod, 4),
                        "net_edge": round(edge, 4),
                        "l1_usd": w_chk["l1_usd"],
                    })
                if (
                    not event_w2_taken
                    and not event_w2m_taken
                    and ens_members_n >= 50
                    and peak_iqr_c <= 2.2
                    and not res.get("convective_cold_pool")
                    and 0.16 <= eff_px <= 0.62
                    and p_mod >= 0.34
                    and edge >= 0.095
                ):
                    if best_w2_cand is None or edge > best_w2_cand[0]:
                        best_w2_cand = (edge, p_mod, eff_px, b, bk)

            if best_w2_cand is not None and os.getenv("PM_DISABLE_SHADOW_W2_TAKER", "0") != "1":
                _, p_mod_best, _, b_best, bk_best = best_w2_cand
                await self.open_shadow_position(
                    sleeve="W2_ENSEMBLE_VALUE",
                    dedupe_key=f"W2_{sp.event_id}_{b_best.market_id}",
                    asset_or_city=f"{sp.city}_{sp.icao}",
                    title=f"{sp.title} [{b_best.label}]",
                    side_label="YES",
                    token_id=b_best.yes_token,
                    fee_rate=float(getattr(b_best, "fee_rate", 0.0) or 0.0),
                    p_model=p_mod_best,
                    close_ts=end_ts,
                    extra={
                        "event_id": sp.event_id,
                        "market_id": b_best.market_id,
                        "condition_id": b_best.condition_id,
                        "icao": sp.icao,
                        "obs_date": sp.obs_date.isoformat(),
                        "bucket_label": b_best.label,
                        "bias_c": res["bias_c"],
                        "ensemble_members": ens_members_n,
                        "peak_iqr_c": peak_iqr_c,
                    },
                    prefetched_book=bk_best,
                )
            elif best_w2m_cand is not None:
                _, p_mod_mkr, _, b_mkr, bk_mkr = best_w2m_cand
                await self.post_shadow_maker_entry(
                    sleeve="W2_MAKER_OVERROUND",
                    dedupe_key=f"W2M_{sp.event_id}_{b_mkr.market_id}",
                    asset=f"{sp.city}_{sp.icao}",
                    title=f"{sp.title} [{b_mkr.label}]",
                    side_label="YES",
                    token_id=b_mkr.yes_token,
                    p_model=p_mod_mkr,
                    close_ts=end_ts,
                    extra={
                        "execution_mode": "POST_ONLY_WEATHER_MAKER_ZERO_FEE",
                        "event_id": sp.event_id,
                        "market_id": b_mkr.market_id,
                        "condition_id": b_mkr.condition_id,
                        "icao": sp.icao,
                        "obs_date": sp.obs_date.isoformat(),
                        "bucket_label": b_mkr.label,
                        "bias_c": res["bias_c"],
                        "ensemble_members": ens_members_n,
                        "peak_iqr_c": peak_iqr_c,
                    },
                    prefetched_book=bk_mkr,
                )

    async def scan_barrier_markets(self, opps_out: List[Dict[str, Any]]) -> None:
        now = time.time()
        loop = asyncio.get_running_loop()

        # Group rungs by event_id so we fetch Binance window extremes once per event
        by_event: Dict[str, List[BarrierRungSpec]] = collections.defaultdict(list)
        for r in self.barrier_rungs.values():
            if r.end_ts > now + 300:
                by_event[r.event_id].append(r)

        for ev_id, rungs in by_event.items():
            r0 = rungs[0]
            spot = self.spots.get(r0.asset, 0.0)
            if spot <= 0:
                continue

            ext_cached = self.barrier_ext_cache.get(ev_id)
            if ext_cached is None or (now - ext_cached[0]) >= 90.0:
                ext = await loop.run_in_executor(
                    None, fetch_binance_window_extremes_sync, r0.asset, r0.start_ts, now, "1m"
                )
                if ext:
                    self.barrier_ext_cache[ev_id] = (now, ext)
            else:
                ext = ext_cached[1]

            max_h = max(spot, ext[0]) if ext else spot
            min_l = min(spot, ext[1]) if ext else spot

            # Only poll CLOB books for rungs within sensible distance of spot (|ln(K/S)| <= 0.14)
            near_rungs = [
                r for r in rungs
                if abs(math.log(r.strike / spot)) <= 0.14
                and not (r.direction == "UP" and max_h >= r.strike)
                and not (r.direction == "DOWN" and min_l <= r.strike)
            ]
            for r in near_rungs:
                tte = r.end_ts - now
                iv_w, iv_src = get_wing_implied_vol(r.asset, spot, r.strike, tte)
                p_touch = first_passage_touch_prob(
                    spot, r.strike, tte, iv_w, r.direction, wick_vol_multiplier=self.barrier_wick_mult
                )

                # Evaluate B1_CONVEX_TAIL_YES (`0.04 <= p_touch <= 0.45`, `TTE >= 2h`)
                if 7200 <= tte <= 10 * 86400 and 0.07 <= p_touch <= 0.48:
                    bk_y = await self.fetch_json(f"{CLOB_URL}/book?token_id={r.yes_token}", timeout=3.0)
                    if bk_y:
                        w_y = walk_l2_book_asks(bk_y.get("asks") or [], 25.0, fee_rate=CRYPTO_FEE_RATE)
                        if w_y.get("filled") and 0.04 <= w_y["vwap"] <= 0.32:
                            edge_y = p_touch - w_y["eff_px"]
                            if edge_y >= 0.03:
                                opps_out.append({
                                    "sleeve": "B1_CONVEX_TAIL_YES",
                                    "market": f"{r.asset} {r.question}",
                                    "ask_vwap": w_y["eff_px"],
                                    "p_model": round(p_touch, 4),
                                    "net_edge": round(edge_y, 4),
                                    "l1_usd": w_y["l1_usd"],
                                })
                            # WFO Governance Gate: Taker B1 disabled (Favorite-Longshot Bias + VRP yielded OOS PF < 1.0);
                            # only log extreme >= 12c dislocations for research telemetry while trading B2_BARRIER_NO_LOCK (93.8% WR, 100% OOS).
                            if edge_y >= 0.12 and (p_touch / w_y["eff_px"]) >= 1.75 and w_y["vwap"] <= 0.20:
                                logger.info(f"[TELEMETRY_ONLY:B1_EXTREME_DISLOCATION] {r.asset} {r.question} ask={w_y['eff_px']:.3f} p={p_touch:.3f}")

                # Evaluate B2_BARRIER_NO_LOCK (`1h <= TTE <= 10h`, `p_no >= 0.88`)
                p_no = 1.0 - p_touch
                if 3600 <= tte <= 36000 and p_no >= 0.88:
                    bk_n = await self.fetch_json(f"{CLOB_URL}/book?token_id={r.no_token}", timeout=3.0)
                    if bk_n:
                        w_n = walk_l2_book_asks(bk_n.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)
                        if w_n.get("filled") and 0.65 <= w_n["vwap"] <= 0.91:
                            edge_n = p_no - w_n["eff_px"]
                            b2_gate = evaluate_barrier_no_net_ev(p_touch, w_n["vwap"], fee_rate=CRYPTO_FEE_RATE)
                            if edge_n >= 0.025:
                                opps_out.append({
                                    "sleeve": "B2_BARRIER_NO_LOCK",
                                    "market": f"{r.asset} NO: {r.question}",
                                    "ask_vwap": w_n["eff_px"],
                                    "p_model": round(p_no, 4),
                                    "net_edge": round(edge_n, 4),
                                    "l1_usd": w_n["l1_usd"],
                                })
                            if edge_n >= 0.038 and b2_gate["eligible"]:
                                await self.open_shadow_position(
                                    sleeve="B2_BARRIER_NO_LOCK",
                                    dedupe_key=f"B2_{r.market_id}",
                                    asset_or_city=r.asset,
                                    title=r.question,
                                    side_label="NO",
                                    token_id=r.no_token,
                                    fee_rate=CRYPTO_FEE_RATE,
                                    p_model=p_no,
                                    close_ts=r.end_ts,
                                    extra={
                                        "market_id": r.market_id,
                                        "condition_id": r.condition_id,
                                        "start_ts": r.start_ts,
                                        "strike": r.strike,
                                        "direction": r.direction,
                                        "iv_wing": round(iv_w, 4),
                                        "loss_to_gain_ratio": b2_gate["loss_to_gain_ratio"],
                                    },
                                    prefetched_book=bk_n,
                                )

    async def scan_multistrike_markets(self, opps_out: List[Dict[str, Any]]) -> None:
        now = time.time()
        for ladder_key, rungs in list(self.strike_ladders.items()):
            if not rungs:
                continue
            asset = rungs[0].asset
            spot = self.spots.get(asset, 0.0)
            if spot <= 0:
                continue
            tte = rungs[0].end_ts - now
            if tte <= 900:
                continue

            ret_60s_bps = self.get_return_bps(asset, 60.0)
            near = [r for r in rungs if abs(math.log(r.strike / spot)) <= 0.08]
            coherent_map = evaluate_coherent_strike_ladder(asset, spot, near, tte, now_ts=now).get("by_market_id", {})
            ladder_quotes: List[Dict[str, Any]] = []

            for sr in near:
                svi_ev = coherent_map.get(sr.market_id) or evaluate_svi_digital_fair_value(
                    asset, spot, sr.strike, tte, is_downward=sr.is_downward, now_ts=now
                )
                bk_y, bk_n = await asyncio.gather(
                    self.fetch_json(f"{CLOB_URL}/book?token_id={sr.yes_token}", timeout=3.0),
                    self.fetch_json(f"{CLOB_URL}/book?token_id={sr.no_token}", timeout=3.0),
                )
                if not bk_y or not bk_n:
                    continue

                # C1_BINARY_COMPLETE_SET (`ChatGPT #4`): equal-share YES + NO <= $0.994 net underround arb!
                c1_chk = scan_binary_complete_set_arb(
                    market_id=sr.market_id,
                    condition_id=sr.condition_id,
                    yes_token=sr.yes_token,
                    no_token=sr.no_token,
                    asks_yes_raw=bk_y.get("asks") or [],
                    asks_no_raw=bk_n.get("asks") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],
                    fee_rate=CRYPTO_FEE_RATE,
                )
                if c1_chk.get("filled"):
                    opps_out.append({
                        "sleeve": "C1_BINARY_COMPLETE_SET",
                        "market": f"{asset} Complete-Set {sr.question}",
                        "ask_vwap": c1_chk["box_cost_net"],
                        "p_model": 1.0,
                        "net_edge": c1_chk["riskless_floor_per_pair"],
                        "l1_usd": c1_chk["l1_usd"],
                        "close_ts": sr.end_ts,
                    })
                    await self.open_shadow_two_leg_box(
                        sleeve="C1_BINARY_COMPLETE_SET",
                        dedupe_key=f"C1_{sr.market_id}",
                        asset=asset,
                        title=f"{asset} YES+NO Complete Set: {sr.question}",
                        leg_a={"token_id": sr.yes_token, "side": "YES", "market_id": sr.market_id, "fee_rate": CRYPTO_FEE_RATE},
                        leg_b={"token_id": sr.no_token, "side": "NO", "market_id": sr.market_id, "fee_rate": CRYPTO_FEE_RATE},
                        bk_a=bk_y,
                        bk_b=bk_n,
                        close_ts=sr.end_ts,
                        max_box_cost_net=0.994,
                        extra={"is_complete_set": True, "market_id": sr.market_id, "condition_id": sr.condition_id},
                    )

                w_y = walk_l2_book_asks(bk_y.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)
                w_n = walk_l2_book_asks(bk_n.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)

                ladder_quotes.append({
                    "strike": sr.strike,
                    "is_downward": sr.is_downward,
                    "market_id": sr.market_id,
                    "yes_token": sr.yes_token,
                    "no_token": sr.no_token,
                    "ask_yes": w_y.get("vwap") if w_y.get("filled") else None,
                    "ask_no": w_n.get("vwap") if w_n.get("filled") else None,
                    "asks_yes": bk_y.get("asks") or [],
                    "asks_no": bk_n.get("asks") or [],
                    "bk_yes": bk_y,
                    "bk_no": bk_n,
                    "end_ts": sr.end_ts,
                })

                for side_lbl, tok, w_side, p_fair, bk_side in (
                    []
                    if (is_shadow_sleeve_quarantined("M1_SVI_MAKER_SCALP") and is_shadow_sleeve_quarantined("M2_STRIKE_CONVERGENCE"))
                    else [
                        ("YES", sr.yes_token, w_y, svi_ev["p_yes"], bk_y),
                        ("NO", sr.no_token, w_n, svi_ev["p_no"], bk_n),
                    ]
                ):
                    if not w_side.get("filled"):
                        continue
                    eff_px = w_side["eff_px"]
                    edge = p_fair - eff_px
                    wins_up = (side_lbl == "YES" and not sr.is_downward) or (side_lbl == "NO" and sr.is_downward)
                    if (wins_up and ret_60s_bps < -12.0) or ((not wins_up) and ret_60s_bps > 12.0):
                        continue

                    if 0.14 <= eff_px <= 0.90 and edge >= 0.025:
                        opps_out.append({
                            "sleeve": "M1_OR_M2_STRIKE_SVI",
                            "market": f"{asset} {sr.question} ({side_lbl})",
                            "ask_vwap": eff_px,
                            "p_model": p_fair,
                            "net_edge": round(edge, 4),
                            "l1_usd": w_side["l1_usd"],
                        })

                    # M1_SVI_MAKER_SCALP: WFO proved 7% crypto_fees_v2 taker drag near 50c eats scalp EV;
                    # strictly enter via resting `post_only=True` 0%-fee Maker limit bid (never faking an instant Ask fill!)
                    maker_edge_est = p_fair - (float(w_side["best_ask"]) - 0.01)
                    if 10800 <= tte <= 86400 and 0.19 <= w_side["best_ask"] <= 0.81 and maker_edge_est >= 0.060:
                        await self.post_shadow_maker_entry(
                            sleeve="M1_SVI_MAKER_SCALP",
                            dedupe_key=f"M1_{sr.market_id}_{side_lbl}",
                            asset=asset,
                            title=sr.question,
                            side_label=side_lbl,
                            token_id=tok,
                            p_model=p_fair,
                            close_ts=sr.end_ts,
                            extra={
                                "execution_mode": "POST_ONLY_MAKER_ZERO_FEE",
                                "market_id": sr.market_id,
                                "condition_id": sr.condition_id,
                                "strike": sr.strike,
                                "is_downward": sr.is_downward,
                                "iv_annual": svi_ev["iv_annual"],
                                "z_sigma": svi_ev["z_sigma"],
                            },
                            prefetched_book=bk_side,
                        )

                    # M2_STRIKE_CONVERGENCE (Post-NYSE-Open 20m <= TTE <= 105m, high-cushion z_sigma >= 1.75)
                    if (
                        1200 <= tte <= 6300
                        and 0.68 <= w_side["vwap"] <= 0.90
                        and svi_ev["z_sigma"] >= 1.75
                        and p_fair >= 0.93
                        and edge >= 0.045
                    ):
                        await self.open_shadow_position(
                            sleeve="M2_STRIKE_CONVERGENCE",
                            dedupe_key=f"M2_{sr.market_id}_{side_lbl}",
                            asset_or_city=asset,
                            title=sr.question,
                            side_label=side_lbl,
                            token_id=tok,
                            fee_rate=CRYPTO_FEE_RATE,
                            p_model=p_fair,
                            close_ts=sr.end_ts,
                            extra={
                                "market_id": sr.market_id,
                                "condition_id": sr.condition_id,
                                "strike": sr.strike,
                                "is_downward": sr.is_downward,
                                "iv_annual": svi_ev["iv_annual"],
                                "z_sigma": svi_ev["z_sigma"],
                            },
                            prefetched_book=bk_side,
                        )

            # Check cross-strike monotonicity boxes (#4/#7 bonus — verified with equal-share L2 book walk, `M-03` / `F-20` + `Gemini #8` execution)
            mono_arbs = detect_ladder_monotonicity_boxes(ladder_quotes, fee_rate=CRYPTO_FEE_RATE)
            quotes_by_yes = {str(q["yes_token"]): q for q in ladder_quotes}
            quotes_by_no = {str(q["no_token"]): q for q in ladder_quotes}
            for ma in mono_arbs:
                q_lo = quotes_by_yes.get(str(ma.get("yes_token_low") or ""))
                q_hi = quotes_by_no.get(str(ma.get("no_token_high") or ""))
                if not q_lo or not q_hi:
                    continue
                w_m3 = walk_equal_shares_dominance_box(
                    q_lo.get("asks_yes") or [],
                    q_hi.get("asks_no") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["M3_LADDER_MONO_BOX"],
                    fee_rate_a=CRYPTO_FEE_RATE,
                    fee_rate_b=CRYPTO_FEE_RATE,
                    max_box_cost_net=0.996,
                    min_shares=10,
                    min_box_notional_usd=9.0,
                )
                if w_m3.get("filled"):
                    opps_out.append({
                        "sleeve": "M3_LADDER_MONO_BOX",
                        "market": f"{asset} Box YES>{ma['low_strike']} + NO>{ma['high_strike']}",
                        "ask_vwap": round(float(w_m3["box_cost_net"]), 4),
                        "p_model": 1.0,
                        "net_edge": round(1.0 - float(w_m3["box_cost_net"]), 4),
                        "l1_usd": w_m3["l1_usd"],
                        "close_ts": q_lo["end_ts"],
                    })
                    await self.open_shadow_two_leg_box(
                        sleeve="M3_LADDER_MONO_BOX",
                        dedupe_key=f"M3_{asset}_{ma['low_market_id']}_{ma['high_market_id']}",
                        asset=asset,
                        title=f"{asset} Ladder Box YES>{ma['low_strike']} + NO>{ma['high_strike']}",
                        leg_a={"token_id": ma["yes_token_low"], "side": "YES", "market_id": ma["low_market_id"], "fee_rate": CRYPTO_FEE_RATE},
                        leg_b={"token_id": ma["no_token_high"], "side": "NO", "market_id": ma["high_market_id"], "fee_rate": CRYPTO_FEE_RATE},
                        bk_a=q_lo["bk_yes"],
                        bk_b=q_hi["bk_no"],
                        close_ts=float(q_lo["end_ts"]),
                        max_box_cost_net=0.996,
                        extra={
                            "is_mono_box": True,
                            "low_strike": ma["low_strike"],
                            "high_strike": ma["high_strike"],
                            "low_market_id": ma["low_market_id"],
                            "high_market_id": ma["high_market_id"],
                        },
                    )

            # Check Cross-Contract `Multi-Strike` vs `NegRisk Bracket` Synthetic Box Arbitrage (`N1_NEGRISK_CROSS_BOX`)
            nr_key = f"{asset}_{int(rungs[0].end_ts)}"
            nr_brackets = self.negrisk_ladders.get(nr_key) or []
            if nr_brackets:
                await self._scan_negrisk_bundles_for_ladder(
                    asset=asset,
                    spot=spot,
                    rungs=rungs,
                    nr_brackets=nr_brackets,
                    ms_book_cache={
                        **{str(q["yes_token"]): q["bk_yes"] for q in ladder_quotes},
                        **{str(q["no_token"]): q["bk_no"] for q in ladder_quotes},
                    },
                    opps_out=opps_out,
                )

    async def _scan_negrisk_bundles_for_ladder(
        self,
        asset: str,
        spot: float,
        rungs: List[StrikeRungSpec],
        nr_brackets: List[NegRiskBracketSpec],
        ms_book_cache: Dict[str, Dict[str, Any]],
        opps_out: List[Dict[str, Any]],
    ) -> None:
        bundles = build_negrisk_cross_box_bundles(rungs, nr_brackets, spot=spot, max_strike_dist_log=0.10)
        if not bundles:
            return
        local_bk_cache = dict(ms_book_cache)
        needed_toks = sorted({
            str(lg["token_id"])
            for bnd in bundles
            for lg in bnd["legs"]
            if str(lg["token_id"]) not in local_bk_cache
        })
        if needed_toks:
            fetched_bks = await asyncio.gather(
                *[self.fetch_json(f"{CLOB_URL}/book?token_id={t_id}", timeout=3.0) for t_id in needed_toks]
            )
            for t_id, bk_obj in zip(needed_toks, fetched_bks):
                if bk_obj:
                    local_bk_cache[t_id] = bk_obj

        for bnd in bundles:
            legs = bnd["legs"]
            if not all(str(lg["token_id"]) in local_bk_cache for lg in legs):
                continue
            gp = float(bnd["guaranteed_payout"])
            max_cost = round(gp * 0.992, 4)
            legs_spec = [
                {
                    "asks": local_bk_cache[str(lg["token_id"])].get("asks") or [],
                    "fee_rate": float(lg.get("fee_rate", CRYPTO_FEE_RATE)),
                    "fee_exponent": 1.0,
                }
                for lg in legs
            ]
            w_nr = walk_equal_shares_multi_leg_box(
                legs_spec,
                target_budget_usd=BANKROLL_TICKETS["T1000"]["N1_NEGRISK_CROSS_BOX"],
                guaranteed_payout_per_bundle=gp,
                max_bundle_cost_net=round(gp * 1.005, 4),
                min_shares=8,
                min_box_notional_usd=9.0,
            )
            if not w_nr.get("filled"):
                continue
            cost_net = float(w_nr["box_cost_net"])
            floor_edge = round(gp - cost_net, 4)
            opps_out.append({
                "sleeve": "N1_NEGRISK_CROSS_BOX",
                "market": f"{asset} {bnd['label']}",
                "ask_vwap": round(cost_net / gp, 4),
                "p_model": 1.0,
                "net_edge": round(floor_edge / gp, 4),
                "l1_usd": w_nr["l1_usd"],
                "close_ts": bnd["end_ts"],
            })
            if cost_net <= max_cost:
                await self.open_shadow_multi_leg_bundle(
                    sleeve="N1_NEGRISK_CROSS_BOX",
                    dedupe_key=f"N1_{asset}_{bnd['bundle_id']}",
                    asset=asset,
                    title=f"{asset} NegRisk Cross-Box: {bnd['label']}",
                    legs=legs,
                    books_by_token=local_bk_cache,
                    close_ts=float(bnd["end_ts"]),
                    guaranteed_payout=gp,
                    max_bundle_cost_net=max_cost,
                    extra={"is_multi_leg_bundle": True, "bundle_id": bnd["bundle_id"], "guaranteed_payout": gp, "legs": legs},
                )

    async def open_shadow_multi_leg_bundle(
        self,
        sleeve: str,
        dedupe_key: str,
        asset: str,
        title: str,
        legs: List[Dict[str, Any]],
        books_by_token: Dict[str, Dict[str, Any]],
        close_ts: float,
        guaranteed_payout: float,
        max_bundle_cost_net: float,
        extra: Dict[str, Any],
    ) -> bool:
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            legs_spec = [
                {
                    "asks": books_by_token[str(lg["token_id"])].get("asks") or [],
                    "fee_rate": float(lg.get("fee_rate", CRYPTO_FEE_RATE)),
                    "fee_exponent": 1.0,
                }
                for lg in legs
            ]
            sum_bids = sum(
                extract_best_bid(books_by_token[str(lg["token_id"])].get("bids") or [])[0]
                for lg in legs
            )
            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = walk_equal_shares_multi_leg_box(
                    legs_spec,
                    target_budget_usd=t_map[sleeve],
                    guaranteed_payout_per_bundle=guaranteed_payout,
                    max_bundle_cost_net=max_bundle_cost_net,
                    min_shares=6 if tier_name == "T100" else 8,
                    min_box_notional_usd=7.0 if tier_name == "T100" else 9.0,
                )
                if w_t.get("filled"):
                    tier_fills[tier_name] = w_t
            if "T1000" not in tier_fills:
                return False
            w_ref = tier_fills["T1000"]
            now = time.time()
            pos_id = f"{sleeve}_{int(now)}_{dedupe_key[-10:]}"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve,
                "asset_or_city": asset,
                "title": title,
                "side": "+".join(str(lg.get("label", lg.get("side", "YES"))) for lg in legs),
                "token_id": "|".join(str(lg["token_id"]) for lg in legs),
                "fee_rate": CRYPTO_FEE_RATE,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": round(guaranteed_payout, 4),
                "entry_eff_px_t1000": w_ref["eff_px"],
                "entry_vwap_t1000": w_ref["vwap"],
                "realized_edge_t1000": w_ref["riskless_floor_per_pair"],
                "entry_best_bid": round(sum_bids, 4),
                "last_bid": round(sum_bids, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {**extra, "legs": legs},
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(
                f"[ENTRY:{sleeve}] {title} | {w_ref['shares']} bundles @ net=${w_ref['eff_px']:.4f} "
                f"(guaranteed=${guaranteed_payout:.2f}, floor=${w_ref['riskless_floor_per_pair']:+.4f}/bundle)"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    async def scan_daily_updown_locks(self, opps_out: List[Dict[str, Any]]) -> None:
        """
        Addition #6 (`U1_DAILY_UPDOWN_LOCK`): Final-90-minute SVI convergence sniper on
        `btc-up-or-down-daily` ($67k/24h) and `eth-up-or-down-daily` ($25k/24h).
        """
        now = time.time()
        loop = asyncio.get_running_loop()
        for _, sp in list(self.daily_updown_markets.items()):
            tte = sp.end_ts - now
            if not (120.0 <= tte <= 5400.0):
                continue
            spot = self.spots.get(sp.asset, 0.0)
            if spot <= 0.0:
                continue

            c_key = f"{sp.asset}_{int(sp.start_ts)}"
            cached_o = self.daily_open_cache.get(c_key)
            if cached_o is None:
                ext_o = await loop.run_in_executor(
                    None, fetch_binance_window_extremes_sync, sp.asset, sp.start_ts - 60.0, sp.start_ts + 60.0, "1m"
                )
                if ext_o is not None and ext_o[2] > 0:
                    self.daily_open_cache[c_key] = (sp.end_ts, float(ext_o[2]))
                    k_open = float(ext_o[2])
                else:
                    continue
            else:
                k_open = cached_o[1]

            svi_ev = evaluate_svi_digital_fair_value(sp.asset, spot, k_open, tte, is_downward=False, now_ts=now)
            win_side = "UP" if spot > k_open else "DOWN"
            p_fair = float(svi_ev["p_yes"] if win_side == "UP" else svi_ev["p_no"])
            z_sig = abs(float(svi_ev.get("z_sigma") or 0.0))
            if z_sig < 1.80 or p_fair < 0.93:
                continue

            ret_60s = self.get_return_bps(sp.asset, 60.0)
            if (win_side == "UP" and ret_60s < -10.0) or (win_side == "DOWN" and ret_60s > 10.0):
                continue

            tok = sp.up_token if win_side == "UP" else sp.down_token
            bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=3.0)
            if not bk:
                continue
            w_chk = walk_l2_book_asks(bk.get("asks") or [], BANKROLL_TICKETS["T1000"]["U1_DAILY_UPDOWN_LOCK"], fee_rate=sp.fee_rate)
            if not w_chk.get("filled"):
                continue
            eff_px = float(w_chk["eff_px"])
            edge = p_fair - eff_px
            if 0.66 <= w_chk["vwap"] <= 0.90 and edge >= 0.025:
                opps_out.append({
                    "sleeve": "U1_DAILY_UPDOWN_LOCK",
                    "market": f"{sp.asset} {sp.title} ({win_side}, TTE={tte/60:.0f}m, z={z_sig:.2f})",
                    "ask_vwap": eff_px,
                    "p_model": round(p_fair, 4),
                    "net_edge": round(edge, 4),
                    "l1_usd": w_chk["l1_usd"],
                    "close_ts": sp.end_ts,
                })
            if 0.66 <= w_chk["vwap"] <= 0.90 and edge >= 0.042:
                await self.open_shadow_position(
                    sleeve="U1_DAILY_UPDOWN_LOCK",
                    dedupe_key=f"U1_{sp.market_id}_{win_side}",
                    asset_or_city=sp.asset,
                    title=sp.title,
                    side_label=win_side,
                    token_id=tok,
                    fee_rate=sp.fee_rate,
                    p_model=p_fair,
                    close_ts=sp.end_ts,
                    extra={
                        "market_id": sp.market_id,
                        "condition_id": sp.condition_id,
                        "strike": k_open,
                        "is_downward": (win_side == "DOWN"),
                        "z_sigma": z_sig,
                    },
                    tp_target_px=0.98,
                    prefetched_book=bk,
                )

    @staticmethod
    def is_in_same_oracle_overlap_window(now_ts: float) -> bool:
        """
        True during the final 5m sub-window of every 15m candle (`:10-:15`, `:25-:30`,
        `:40-:45`, `:55-:00`), where the active `15m` and `5m` Chainlink 60s-TWAP markets
        share the exact same terminal timestamp `target_end_ts`.
        """
        target_end_ts = math.ceil(now_ts / 900.0) * 900.0
        rem_sec = target_end_ts - now_ts
        return 8.0 <= rem_sec <= 305.0

    async def discover_dominance_pairs(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        # Prune expired pairs and opening strike caches
        for k_old, (m15_old, _) in list(self.dominance_pairs.items()):
            if m15_old.end_ts < now - 600.0:
                self.dominance_pairs.pop(k_old, None)
        for c_key, (end_old, _) in list(self.chainlink_open_cache.items()):
            if end_old < now - 600.0:
                self.chainlink_open_cache.pop(c_key, None)

        target_end_ts = int(math.ceil(now / 900.0) * 900)
        rem_sec = float(target_end_ts) - now
        if not (5.0 <= rem_sec <= 305.0):
            return

        now_iso = datetime.fromtimestamp(now - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        async def _discover_asset_pair(asset: str) -> None:
            pair_key = f"{asset}_{target_end_ts}"
            if pair_key in self.dominance_pairs:
                return
            slugs = DOMINANCE_SERIES_SLUGS[asset]
            ev15_raw, ev5_raw = await asyncio.gather(
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['15m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['5m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
            )
            m15_match: Optional[TwapCandleMarketSpec] = None
            m5_match: Optional[TwapCandleMarketSpec] = None
            if isinstance(ev15_raw, list):
                for ev in ev15_raw:
                    sp15 = parse_twap_candle_event(ev, asset, "15m")
                    if sp15 and abs(sp15.end_ts - target_end_ts) <= 2.0:
                        m15_match = sp15
                        break
            if isinstance(ev5_raw, list):
                for ev in ev5_raw:
                    sp5 = parse_twap_candle_event(ev, asset, "5m")
                    if sp5 and abs(sp5.end_ts - target_end_ts) <= 2.0:
                        m5_match = sp5
                        break
            if m15_match and m5_match and verify_same_oracle_pair(m15_match, m5_match):
                self.dominance_pairs[pair_key] = (m15_match, m5_match)

        await asyncio.gather(*(_discover_asset_pair(a) for a in DOMINANCE_ASSETS))

    async def get_authoritative_open_strike(self, spec: TwapCandleMarketSpec) -> Optional[float]:
        c_key = f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}"
        cached = self.chainlink_open_cache.get(c_key)
        if cached is not None:
            return cached[1]
        now_t = time.time()
        if not self.single_scan and now_t < spec.start_ts + 2.0:
            return None
        twap_url = build_crypto_price_query_url(spec)
        # Polymarket's crypto-price endpoint intermittently answers HTTP 400 {"error":"Chainlink API error 429"};
        # fetch_json returns None on any non-200, so retry briefly (idempotent GET) before failing closed.
        val: Optional[float] = None
        for _attempt in range(3):
            payload = await self.fetch_json(twap_url, timeout=4.0)
            val = parse_authoritative_open_price(payload, request_url=twap_url)
            if val is not None:
                break
            await asyncio.sleep(0.3 * (_attempt + 1))
        if val is None:
            _fl = self.__dict__.setdefault("_strike_fail_log_ts", {})
            if (now_t - float(_fl.get(c_key, 0.0))) >= 60.0:
                _fl[c_key] = now_t
                logger.warning(
                    f"[STRIKE LOOKUP FAILED] {spec.asset} {spec.horizon}: crypto-price returned no usable openPrice "
                    f"after 3 attempts (upstream 429/non-200?) -> candidate skipped (fail-closed)."
                )
        # Gamma prev-5m `finalPrice` is published ~340s after the boundary: cross-check whenever it can exist.
        needs_gamma = self.single_scan or now_t >= spec.start_ts + 335.0
        if needs_gamma:
            g_url = build_prev_5m_gamma_event_url(spec)
            g_val = parse_authoritative_open_price(await self.fetch_json(g_url, timeout=4.0), request_url=g_url)
            if val is None:
                val = g_val
            elif g_val is not None and abs(val - g_val) / max(1e-9, g_val) > 1e-6:
                logger.error(
                    f"[CRITICAL TWAP MISMATCH VETO] {spec.asset} {spec.horizon}: "
                    f"crypto-price TWAP={val} != Gamma prev_5m finalPrice={g_val}!"
                )
                return None
            elif g_val is None and not self.single_scan:
                return None  # unverifiable while verification is possible -> fail closed, never cache
        if val is not None:
            hist_w = [px for ts_s, px in self.usd_spot_hist.get(spec.asset, ()) if (spec.start_ts - 60.0) <= ts_s <= (spec.start_ts + 5.0)]
            if len(hist_w) >= 3 and not self.single_scan:
                loc_twap = sum(hist_w) / len(hist_w)
                if loc_twap > 0.0 and abs(val - loc_twap) / loc_twap > 0.0035:
                    logger.error(f"[STRIKE TWAP VETO] {spec.asset} {spec.horizon}: strike {val} vs local 60s TWAP {loc_twap} > 35 bps")
                    return None
            elif not needs_gamma:
                spot_ref = float(self.spots.get(spec.asset) or 0.0)
                if spot_ref > 0.0 and abs(val - spot_ref) / spot_ref > 0.015:
                    logger.error(f"[STRIKE SANITY VETO] {spec.asset} {spec.horizon}: strike {val} vs spot {spot_ref} > 150 bps")
                    return None
            self.chainlink_open_cache[c_key] = (spec.end_ts, val)
        return val

    async def _passes_complement_anti_box_check(self, leg_a: Dict[str, Any], leg_b: Dict[str, Any]) -> bool:
        opp_a = str(leg_a.get("opp_token_id") or "")
        opp_b = str(leg_b.get("opp_token_id") or "")
        if not opp_a or not opp_b:
            return False
        bk_oa, bk_ob = await asyncio.gather(
            self.fetch_json(f"{CLOB_URL}/book?token_id={opp_a}", timeout=3.0),
            self.fetch_json(f"{CLOB_URL}/book?token_id={opp_b}", timeout=3.0),
        )
        if not (isinstance(bk_oa, dict) and isinstance(bk_ob, dict)):
            return False
        bid_oa, _ = extract_best_bid(bk_oa.get("bids") or [])
        bid_ob, _ = extract_best_bid(bk_ob.get("bids") or [])
        if bid_oa <= 0.0 or bid_ob <= 0.0 or (bid_oa + bid_ob) > 1.0:
            logger.warning(
                f"[ANTI-BOX VETO] Rejected box {leg_a.get('label')}+{leg_b.get('label')}: "
                f"complement bids={bid_oa:.3f}+{bid_ob:.3f}={bid_oa + bid_ob:.3f} (unverified or > 1.03)"
            )
            return False
        return True

    async def open_shadow_two_leg_box(
        self,
        sleeve: str,
        dedupe_key: str,
        asset: str,
        title: str,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        close_ts: float,
        max_box_cost_net: float,
        extra: Dict[str, Any],
    ) -> bool:
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            asks_a = bk_a.get("asks") or []
            asks_b = bk_b.get("asks") or []
            bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
            bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                min_sh = 8 if tier_name == "T100" else 10
                w_t = walk_equal_shares_dominance_box(
                    asks_a,
                    asks_b,
                    target_budget_usd=t_map[sleeve],
                    fee_rate_a=float(leg_a.get("fee_rate", CRYPTO_FEE_RATE)),
                    fee_rate_b=float(leg_b.get("fee_rate", CRYPTO_FEE_RATE)),
                    max_box_cost_net=max_box_cost_net,
                    min_shares=min_sh,
                    min_box_notional_usd=7.0 if tier_name == "T100" else 9.0,
                )
                if w_t.get("filled"):
                    tier_fills[tier_name] = w_t
            if "T1000" not in tier_fills:
                return False
            w_ref = tier_fills["T1000"]
            now = time.time()
            pos_id = f"{sleeve}_{int(now)}_{dedupe_key[-10:]}"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve,
                "asset_or_city": asset,
                "title": title,
                "side": f"{leg_a.get('side','YES')}+{leg_b.get('side','NO')}",
                "token_id": f"{leg_a['token_id']}|{leg_b['token_id']}",
                "fee_rate": float(leg_a.get("fee_rate", CRYPTO_FEE_RATE)),
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": 1.0,
                "entry_eff_px_t1000": w_ref["eff_px"],
                "entry_vwap_t1000": w_ref["vwap"],
                "realized_edge_t1000": w_ref["riskless_floor_per_pair"],
                "entry_best_bid": round(bid_a + bid_b, 4),
                "last_bid": round(bid_a + bid_b, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {**extra, "leg_a": leg_a, "leg_b": leg_b},
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(f"[ENTRY:{sleeve}] {title} | {w_ref['shares']} pairs @ net=${w_ref['eff_px']:.4f}")
            return True
        finally:
            self._release_inflight_keys(acq)

    async def open_shadow_weather_slate(
        self,
        spec: WeatherEventSpec,
        slate_info: Dict[str, Any],
        close_ts: float,
    ) -> bool:
        dedupe_key = f"W3_SLATE_{spec.event_id}"
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            sum_asks = float(slate_info["sum_asks"])
            legs = slate_info["legs"]
            min_avail_sh = min(float(lg["ask_yes_shares"]) for lg in legs)
            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                sh = max(5.0, min(min_avail_sh, math.floor(t_map["W3_WEATHER_SLATE_ARB"] / max(0.10, sum_asks))))
                spent = round(sh * sum_asks, 2)
                if sh >= 5.0 and spent <= t_map["W3_WEATHER_SLATE_ARB"] * 1.25:
                    tier_fills[tier_name] = {
                        "filled": True,
                        "vwap": round(sum_asks, 4),
                        "eff_px": round(sum_asks, 4),
                        "spent_usd": spent,
                        "fee_usd": 0.0,
                        "shares": sh,
                        "l1_usd": round(min_avail_sh * sum_asks, 2),
                    }
            if "T1000" not in tier_fills:
                return False
            now = time.time()
            pos_id = f"W3_WEATHER_SLATE_ARB_{int(now)}_{spec.event_id[-6:]}"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": "W3_WEATHER_SLATE_ARB",
                "asset_or_city": f"{spec.city}_{spec.icao}",
                "title": f"{spec.title} [Full-Slate {len(legs)} Buckets]",
                "side": "ALL_BUCKETS_YES",
                "token_id": "|".join(str(lg["yes_token"]) for lg in legs),
                "fee_rate": 0.0,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": 1.0,
                "entry_eff_px_t1000": round(sum_asks, 4),
                "entry_vwap_t1000": round(sum_asks, 4),
                "realized_edge_t1000": round(1.0 - sum_asks, 4),
                "entry_best_bid": round(sum_asks, 4),
                "last_bid": round(sum_asks, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {"event_id": spec.event_id, "icao": spec.icao, "legs": legs},
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(f"[ENTRY:W3_WEATHER_SLATE_ARB] {pos['title']} @ sum_asks=${sum_asks:.4f}")
            return True
        finally:
            self._release_inflight_keys(acq)

    async def open_shadow_dominance_box(
        self,
        asset: str,
        m15: TwapCandleMarketSpec,
        m5: TwapCandleMarketSpec,
        dom_info: Dict[str, Any],
        prefetched_books: Optional[Tuple[Dict[str, Any], Dict[str, Any]]] = None,
        sleeve_override: str = "D1_SAME_ORACLE_DOMINANCE_BOX",
        max_box_cost_override: float = 0.995,
    ) -> bool:
        prefix = "D1" if sleeve_override == "D1_SAME_ORACLE_DOMINANCE_BOX" else sleeve_override.split("_")[0] + "_" + sleeve_override.split("_")[1]
        dedupe_key = f"{prefix}_{asset}_{m15.market_id}_{m5.market_id}"
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False

        try:
            leg_a = dom_info["leg_a"]
            leg_b = dom_info["leg_b"]

            # Strictly causal 2-leg L2 walk (reuses prefetched books when scanned after latency, `Gemini #7`)
            if prefetched_books is not None:
                bk_a, bk_b = prefetched_books
            else:
                await asyncio.sleep(0.050)
                bk_a, bk_b = await asyncio.gather(
                    self.fetch_json(f"{CLOB_URL}/book?token_id={leg_a['token_id']}", timeout=3.0),
                    self.fetch_json(f"{CLOB_URL}/book?token_id={leg_b['token_id']}", timeout=3.0),
                )
            if not bk_a or not bk_b:
                return False

            asks_a = bk_a.get("asks") or []
            asks_b = bk_b.get("asks") or []
            bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
            bid_b, _ = extract_best_bid(bk_b.get("bids") or [])

            # Validate T1000 reference equal-share box (`box_cost_net <= max_box_cost_override`)
            w_ref = walk_equal_shares_dominance_box(
                asks_a,
                asks_b,
                target_budget_usd=BANKROLL_TICKETS["T1000"][sleeve_override],
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                fee_exponent_a=float(leg_a["fee_exponent"]),
                fee_exponent_b=float(leg_b["fee_exponent"]),
                max_box_cost_net=max_box_cost_override,
                min_shares=12,
                min_box_notional_usd=11.0,
            )
            if not w_ref.get("filled"):
                return False

            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                min_sh = 8 if tier_name == "T100" else 12
                min_notional = 7.5 if tier_name == "T100" else 11.0
                w_t = walk_equal_shares_dominance_box(
                    asks_a,
                    asks_b,
                    target_budget_usd=t_map[sleeve_override],
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=max_box_cost_override,
                    min_shares=min_sh,
                    min_box_notional_usd=min_notional,
                )
                if w_t.get("filled"):
                    tier_fills[tier_name] = w_t

            if "T1000" not in tier_fills:
                return False

            now = time.time()
            pos_id = f"{sleeve_override}_{int(now)}_{m5.market_id[-6:]}"
            title = f"{asset} {dom_info['regime']} [{dom_info['k_low']:.4f} .. {dom_info['k_high']:.4f}]"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": sleeve_override,
                "asset_or_city": asset,
                "title": title,
                "side": f"{leg_a['label']}+{leg_b['label']}",
                "token_id": f"{leg_a['token_id']}|{leg_b['token_id']}",
                "fee_rate": float(leg_a["fee_rate"]),
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": m5.end_ts,
                "p_model_entry": 1.0,
                "entry_eff_px_t1000": w_ref["eff_px"],
                "entry_vwap_t1000": w_ref["vwap"],
                "realized_edge_t1000": w_ref["riskless_floor_per_pair"],
                "entry_best_bid": round(bid_a + bid_b, 4),
                "last_bid": round(bid_a + bid_b, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {
                    "is_dominance_box": True,
                    "regime": dom_info["regime"],
                    "k_low": dom_info["k_low"],
                    "k_high": dom_info["k_high"],
                    "corridor_bps": dom_info["corridor_bps"],
                    "m15_horizon": m15.horizon,
                    "m15_market_id": m15.market_id,
                    "m15_start_iso": m15.start_iso,
                    "m15_end_iso": m15.end_iso,
                    "m5_horizon": m5.horizon,
                    "m5_market_id": m5.market_id,
                    "leg_a": leg_a,
                    "leg_b": leg_b,
                },
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(
                f"[ENTRY:{sleeve_override}] {title} | {w_ref['shares']} pairs @ net=${w_ref['eff_px']:.4f} "
                f"(floor=${w_ref['riskless_floor_per_pair']:+.4f}/pair, min_profit=${w_ref['guaranteed_min_profit_usd']:+.2f})"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    def emit_live_d1_box_candidate(
        self,
        m15: TwapCandleMarketSpec,
        m5: TwapCandleMarketSpec,
        dom_info: Dict[str, Any],
        w_live: Dict[str, Any],
        now_ts: float,
        *,
        is_quiet_book: bool = False,
        sleeve_source: str = "D1_SAME_ORACLE_DOMINANCE_BOX",
    ) -> bool:
        """Emits a verified D1 Same-Oracle Dominance Box candidate (15m/5m, QuietBook, or 4h/15m) to the live IPC stream."""
        default_cand_path = LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl"
        if STATE_FILE != (DATA_DIR / "alpha124_shadow_state.json") and D1_LIVE_CANDIDATES_FILE == default_cand_path:
            return False
        pair_key = f"{m15.asset}_{m15.market_id}_{m5.market_id}"
        last_emit = float(self._last_d1_live_emit_ts.get(pair_key, 0.0) or 0.0)
        if (now_ts - last_emit) < 10.0:
            return False
        self._last_d1_live_emit_ts[pair_key] = now_ts
        for k_old, ts_old in list(self._last_d1_live_emit_ts.items()):
            if (now_ts - ts_old) > 1200.0:
                self._last_d1_live_emit_ts.pop(k_old, None)

        leg_a = dom_info["leg_a"]
        leg_b = dom_info["leg_b"]
        w_a = w_live["leg_a_walk"]
        w_b = w_live["leg_b_walk"]
        id_pfx = "D1_4H_LIVE" if str(m15.horizon).lower() == "4h" else "D1_LIVE"
        cand = {
            "box_id": f"{id_pfx}_{m15.asset}_{int(m5.end_ts)}_{m5.market_id[-5:]}",
            "dedupe_key": f"D1_{m15.asset}_{m15.market_id}_{m5.market_id}",
            "ts_unix": round(now_ts, 3),
            "asset": m15.asset,
            "regime": dom_info["regime"],
            "pair_horizons": f"{m15.horizon}_{m5.horizon}",
            "sleeve_source": str(sleeve_source),
            "is_quiet_book": bool(is_quiet_book),
            "k_low": dom_info["k_low"],
            "k_high": dom_info["k_high"],
            "corridor_bps": dom_info["corridor_bps"],
            "expiry_ts": float(m5.end_ts),
            "rem_sec": round(float(m5.end_ts - now_ts), 2),
            "shares": int(w_live["shares"]),
            "box_cost_net": float(w_live["box_cost_net"]),
            "max_box_cost_net": 0.985 if is_quiet_book else 0.980,
            "leg_a_token_id": str(leg_a["token_id"]),
            "leg_a_opp_token_id": str(leg_a.get("opp_token_id") or ""),
            "leg_a_label": str(leg_a["label"]),
            "leg_a_side": str(leg_a["side"]),
            "leg_a_horizon": str(leg_a["horizon"]),
            "leg_a_market_id": str(leg_a["market_id"]),
            "leg_a_condition_id": str(leg_a["condition_id"]),
            "leg_a_strike": float(leg_a["strike"]),
            "leg_a_limit_price": float(w_a["worst_px"]),
            "leg_a_avail_shares": float(w_live["avail_a_shares"]),
            "leg_a_fee_rate": float(leg_a["fee_rate"]),
            "leg_a_fee_exponent": float(leg_a["fee_exponent"]),
            "leg_a_neg_risk": bool(leg_a["neg_risk"]),
            "leg_b_token_id": str(leg_b["token_id"]),
            "leg_b_opp_token_id": str(leg_b.get("opp_token_id") or ""),
            "leg_b_label": str(leg_b["label"]),
            "leg_b_side": str(leg_b["side"]),
            "leg_b_horizon": str(leg_b["horizon"]),
            "leg_b_market_id": str(leg_b["market_id"]),
            "leg_b_condition_id": str(leg_b["condition_id"]),
            "leg_b_strike": float(leg_b["strike"]),
            "leg_b_limit_price": float(w_b["worst_px"]),
            "leg_b_avail_shares": float(w_live["avail_b_shares"]),
            "leg_b_fee_rate": float(leg_b["fee_rate"]),
            "leg_b_fee_exponent": float(leg_b["fee_exponent"]),
            "leg_b_neg_risk": bool(leg_b["neg_risk"]),
        }
        try:
            try:
                import orjson as _orj
                raw_b = _orj.dumps(cand) + b"\n"
                line_s = raw_b.decode("utf-8")
            except Exception:
                line_s = json.dumps(cand, separators=(",", ":")) + "\n"
                raw_b = line_s.encode("utf-8")
            if os.name != "nt" and D1_LIVE_CANDIDATES_FILE == default_cand_path:
                try:
                    import socket
                    s_ipc = getattr(self, "_d1_ipc_sock", None)
                    if s_ipc is None:
                        s_ipc = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                        s_ipc.setblocking(False)
                        self._d1_ipc_sock = s_ipc
                    ipc_nm = os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME", "polymarket_d1_box_notify")
                    s_ipc.sendto(raw_b, f"\x00{ipc_nm}".encode("utf-8"))
                except Exception:
                    pass
            D1_LIVE_CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(D1_LIVE_CANDIDATES_FILE, "a", encoding="utf-8") as fp:
                fp.write(line_s)
            return True
        except Exception as exc:
            logger.debug(f"D1 live candidate write notice: {exc}")
            return False

    async def scan_same_oracle_dominance_boxes(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        target_end_ts = int(math.ceil(now / 900.0) * 900)
        cur_window_pairs = sum(1 for k in self.dominance_pairs if str(k).endswith(f"_{target_end_ts}"))
        disc_interval = 7.0 if cur_window_pairs < len(DOMINANCE_ASSETS) else 12.0
        if self.is_in_same_oracle_overlap_window(now) and (now - self.last_dominance_discovery_ts) >= disc_interval:
            self.last_dominance_discovery_ts = now
            await self.discover_dominance_pairs(now)

        if now_ts is None:
            self.record_usd_spot_samples(time.time())

        async def _scan_single_d1_pair(m15: TwapCandleMarketSpec, m5: TwapCandleMarketSpec) -> None:
            rem_sec = m5.end_ts - now
            if not (10.0 <= rem_sec <= 300.0):
                return
            if now < m5.start_ts + 1.0:
                return

            k_15m, k_5m = await asyncio.gather(
                self.get_authoritative_open_strike(m15),
                self.get_authoritative_open_strike(m5),
            )
            if k_15m is None or k_5m is None:
                return

            dom_info = determine_dominance_legs(m15, k_15m, m5, k_5m, min_corridor_bps=3.0)
            if dom_info is None:
                return

            leg_a = dom_info["leg_a"]
            leg_b = dom_info["leg_b"]
            bk_a, bk_b = await asyncio.gather(
                self.fetch_json(f"{CLOB_URL}/book?token_id={leg_a['token_id']}", timeout=3.0),
                self.fetch_json(f"{CLOB_URL}/book?token_id={leg_b['token_id']}", timeout=3.0),
            )
            if not bk_a or not bk_b:
                return
            comp_checked: Optional[bool] = None

            eval_now = float(now_ts) if now_ts is not None else time.time()
            rem_live = m5.end_ts - eval_now
            if 38.0 <= rem_live <= 298.0:
                w_live = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=13.50,
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=0.985,
                    min_shares=8,
                    min_box_notional_usd=7.0,
                )
                if w_live.get("filled"):
                    is_quiet_live = self._passes_quiet_book_filter(m15.asset, bk_a, bk_b, w_live, eval_now)
                    live_emit_cap = 0.985 if is_quiet_live else 0.980
                    if float(w_live["box_cost_net"]) <= live_emit_cap:
                        comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b)
                        if not comp_checked:
                            return
                        self.emit_live_d1_box_candidate(
                            m15,
                            m5,
                            dom_info,
                            w_live,
                            eval_now,
                            is_quiet_book=is_quiet_live,
                            sleeve_source="D1_QUIET_BOOK_BOX" if is_quiet_live else "D1_SAME_ORACLE_DOMINANCE_BOX",
                        )

            w_scan = walk_equal_shares_dominance_box(
                bk_a.get("asks") or [],
                bk_b.get("asks") or [],
                target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_SAME_ORACLE_DOMINANCE_BOX"],
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                fee_exponent_a=float(leg_a["fee_exponent"]),
                fee_exponent_b=float(leg_b["fee_exponent"]),
                max_box_cost_net=1.010,  # Surface near-arb boxes <= $1.010 in live telemetry; enter ONLY <= $0.995!
                min_shares=12,
                min_box_notional_usd=11.0,
            )
            if w_scan.get("filled"):
                box_net = float(w_scan["box_cost_net"])
                floor_edge = round(1.0 - box_net, 4)
                if box_net <= 1.005:
                    opps_out.append({
                        "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                        "market": f"{m15.asset} {dom_info['regime']} (TTE={rem_sec:.0f}s, {dom_info['corridor_bps']:.1f}bps)",
                        "ask_vwap": round(box_net, 4),
                        "p_model": 1.0,
                        "net_edge": floor_edge,
                        "l1_usd": w_scan["l1_usd"],
                    })
                if box_net <= 0.995:
                    if comp_checked is None:
                        comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b)
                    if not comp_checked:
                        return
                    await self.open_shadow_dominance_box(m15.asset, m15, m5, dom_info, prefetched_books=(bk_a, bk_b))
                    if self._passes_quiet_book_filter(m15.asset, bk_a, bk_b, w_scan, eval_now):
                        await self.open_shadow_dominance_box(
                            m15.asset,
                            m15,
                            m5,
                            dom_info,
                            prefetched_books=(bk_a, bk_b),
                            sleeve_override="D1_QUIET_BOOK_BOX",
                            max_box_cost_override=0.992,
                        )

        pairs_snapshot = list(self.dominance_pairs.values())
        if pairs_snapshot:
            await asyncio.gather(*(_scan_single_d1_pair(m15, m5) for m15, m5 in pairs_snapshot))

        # Addition #1 (`D1_4H_DOMINANCE_BOX`): 4h vs 15m & 4h vs 5m Same-Oracle Chainlink 60s-TWAP Boxes
        await self._scan_4h_dominance_boxes(opps_out, now_ts)

    def _passes_quiet_book_filter(
        self,
        asset: str,
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        w_scan: Dict[str, Any],
        now_ts: float,
    ) -> bool:
        """
        Addition #2 (`D1_QUIET_BOOK_BOX`): Blocks box FOK entries during active Binance impulses
        or wide/sweeping L1 spreads (`<= 4c` per leg, `>= 1.5x` share depth) to eliminate legging friction.
        """
        if abs(self.get_return_bps(asset, 5.0)) > 4.5:
            return False
        if (now_ts - float(self._last_any_shock_ts_by_asset.get(asset, 0.0) or 0.0)) < 4.0:
            return False
        bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
        bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
        best_a = float((w_scan.get("leg_a_walk") or {}).get("best_ask") or 1.0)
        best_b = float((w_scan.get("leg_b_walk") or {}).get("best_ask") or 1.0)
        if bid_a <= 0.0 or bid_b <= 0.0:
            return False
        if (best_a - bid_a) > 0.041 or (best_b - bid_b) > 0.041:
            return False
        req_sh = float(w_scan.get("shares") or 12.0)
        avail_min = min(float(w_scan.get("avail_a_shares") or 0.0), float(w_scan.get("avail_b_shares") or 0.0))
        return avail_min >= 1.5 * req_sh

    async def discover_4h_dominance_pairs(self, now_ts: float) -> None:
        for k_old, (m4_old, _) in list(self.dominance_4h_pairs.items()):
            if m4_old.end_ts < now_ts - 600.0:
                self.dominance_4h_pairs.pop(k_old, None)

        # Polymarket 4h ET candles close at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC (aligned on 14400s UTC epoch!)
        target_end_ts = int(math.ceil(now_ts / 14400.0) * 14400)
        rem_4h = float(target_end_ts) - now_ts
        if not (8.0 <= rem_4h <= 905.0):
            return
        now_iso = datetime.fromtimestamp(now_ts - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        need_5m = rem_4h <= 305.0

        for asset in DOMINANCE_ASSETS:
            slugs = DOMINANCE_SERIES_SLUGS[asset]
            slug_4h = slugs.get("4h")
            if not slug_4h:
                continue
            p15_k = f"{asset}_4h15m_{target_end_ts}"
            p5_k = f"{asset}_4h5m_{target_end_ts}"
            if p15_k in self.dominance_4h_pairs and ((not need_5m) or p5_k in self.dominance_4h_pairs):
                continue

            ev4_raw, ev15_raw = await asyncio.gather(
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slug_4h}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['15m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
            )
            m4_match: Optional[TwapCandleMarketSpec] = None
            m15_match: Optional[TwapCandleMarketSpec] = None
            if isinstance(ev4_raw, list):
                for ev in ev4_raw:
                    sp4 = parse_twap_candle_event(ev, asset, "4h")
                    if sp4 and abs(sp4.end_ts - target_end_ts) <= 2.0:
                        m4_match = sp4
                        break
            if isinstance(ev15_raw, list):
                for ev in ev15_raw:
                    sp15 = parse_twap_candle_event(ev, asset, "15m")
                    if sp15 and abs(sp15.end_ts - target_end_ts) <= 2.0:
                        m15_match = sp15
                        break
            if m4_match and m15_match and verify_same_oracle_pair(m4_match, m15_match):
                self.dominance_4h_pairs[p15_k] = (m4_match, m15_match)

            if m4_match and need_5m and p5_k not in self.dominance_4h_pairs:
                ev5_raw = await self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['5m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                )
                if isinstance(ev5_raw, list):
                    for ev in ev5_raw:
                        sp5 = parse_twap_candle_event(ev, asset, "5m")
                        if sp5 and abs(sp5.end_ts - target_end_ts) <= 2.0 and verify_same_oracle_pair(m4_match, sp5):
                            self.dominance_4h_pairs[p5_k] = (m4_match, sp5)
                            break

    async def _scan_4h_dominance_boxes(self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None) -> None:
        now_4h = float(now_ts if now_ts is not None else time.time())
        rem_4h = (math.ceil(now_4h / 14400.0) * 14400.0) - now_4h
        if 8.0 <= rem_4h <= 905.0 and (now_4h - self.last_4h_discovery_ts) >= 12.0:
            self.last_4h_discovery_ts = now_4h
            await self.discover_4h_dominance_pairs(now_4h)

        for _, (m4, m_short) in list(self.dominance_4h_pairs.items()):
            rem_sec = m_short.end_ts - now_4h
            max_rem = 895.0 if m_short.horizon == "15m" else 298.0
            if not (10.0 <= rem_sec <= max_rem) or now_4h < m_short.start_ts + 1.0:
                continue
            k_4h, k_sh = await asyncio.gather(
                self.get_authoritative_open_strike(m4),
                self.get_authoritative_open_strike(m_short),
            )
            if k_4h is None or k_sh is None:
                continue
            dom_info = determine_dominance_legs(m4, k_4h, m_short, k_sh, min_corridor_bps=3.0)
            if dom_info is None:
                continue
            leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
            bk_a, bk_b = await asyncio.gather(
                self.fetch_json(f"{CLOB_URL}/book?token_id={leg_a['token_id']}", timeout=3.0),
                self.fetch_json(f"{CLOB_URL}/book?token_id={leg_b['token_id']}", timeout=3.0),
            )
            if not bk_a or not bk_b:
                continue
            comp_4h_ok: Optional[bool] = None
            eval_4h_now = float(now_ts) if now_ts is not None else time.time()
            if now_ts is None:
                self.record_usd_spot_samples(eval_4h_now)
            rem_4h_live = m_short.end_ts - eval_4h_now
            if 38.0 <= rem_4h_live <= max_rem:
                w_live_4h = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=13.50,
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=0.985,
                    min_shares=8,
                    min_box_notional_usd=7.0,
                )
                if w_live_4h.get("filled"):
                    is_quiet_4h = self._passes_quiet_book_filter(m4.asset, bk_a, bk_b, w_live_4h, eval_4h_now)
                    if float(w_live_4h["box_cost_net"]) <= (0.985 if is_quiet_4h else 0.980):
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b)
                        if not comp_4h_ok:
                            continue
                        self.emit_live_d1_box_candidate(
                            m4,
                            m_short,
                            dom_info,
                            w_live_4h,
                            eval_4h_now,
                            is_quiet_book=is_quiet_4h,
                            sleeve_source="D1_4H_DOMINANCE_BOX",
                        )
            w_scan = walk_equal_shares_dominance_box(
                bk_a.get("asks") or [],
                bk_b.get("asks") or [],
                target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_4H_DOMINANCE_BOX"],
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                fee_exponent_a=float(leg_a["fee_exponent"]),
                fee_exponent_b=float(leg_b["fee_exponent"]),
                max_box_cost_net=1.005,
                min_shares=10,
                min_box_notional_usd=9.0,
            )
            if w_scan.get("filled"):
                box_net = float(w_scan["box_cost_net"])
                opps_out.append({
                    "sleeve": "D1_4H_DOMINANCE_BOX",
                    "market": f"{m4.asset} {dom_info['regime']} (TTE={rem_sec:.0f}s, {dom_info['corridor_bps']:.1f}bps)",
                    "ask_vwap": round(box_net, 4),
                    "p_model": 1.0,
                    "net_edge": round(1.0 - box_net, 4),
                    "l1_usd": w_scan["l1_usd"],
                })
                if box_net <= 0.992:
                    if comp_4h_ok is None:
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b)
                    if not comp_4h_ok:
                        continue
                    await self.open_shadow_dominance_box(
                        m4.asset,
                        m4,
                        m_short,
                        dom_info,
                        prefetched_books=(bk_a, bk_b),
                        sleeve_override="D1_4H_DOMINANCE_BOX",
                        max_box_cost_override=0.992,
                    )
                    if self._passes_quiet_book_filter(m4.asset, bk_a, bk_b, w_scan, eval_4h_now):
                        await self.open_shadow_dominance_box(
                            m4.asset,
                            m4,
                            m_short,
                            dom_info,
                            prefetched_books=(bk_a, bk_b),
                            sleeve_override="D1_QUIET_BOOK_BOX",
                            max_box_cost_override=0.992,
                        )

    def poll_fresh_shock_triggers(
        self, now_ts: Optional[float] = None, max_age_sec: float = 4.5
    ) -> List[Dict[str, Any]]:
        """
        Reads newly appended institutional Binance sweeps from `live_shock_triggers.jsonl`
        in <250ms so Alpha-124 immediately cancels adverse resting Maker bids and snipes
        lagging daily multi-strike SVI rungs (`M4_SHOCK_STRIKE_CATCHUP`).
        """
        if not SHOCK_TRIGGER_FILE.exists():
            return []
        now = float(now_ts if now_ts is not None else time.time())
        fresh: List[Dict[str, Any]] = []
        try:
            st_size = SHOCK_TRIGGER_FILE.stat().st_size
            if st_size < self._shock_file_offset:
                self._shock_file_offset = 0
            if st_size == self._shock_file_offset:
                return []
            with open(SHOCK_TRIGGER_FILE, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._shock_file_offset)
                raw_chunk = f.read()
                self._shock_file_offset = f.tell()
            for line in raw_chunk.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    trig = json.loads(line)
                except Exception:
                    continue
                sid = str(trig.get("shock_id") or trig.get("event_id") or "")
                if not sid or sid in self._seen_shock_ids:
                    continue
                self._seen_shock_ids.append(sid)
                if str(trig.get("shock_source") or "").upper() == "BOUNDARY_LOCK":
                    continue
                asset = str(trig.get("asset") or "").upper()
                if asset not in ("BTC", "ETH", "SOL", "XRP"):
                    continue
                t0_u = float(trig.get("t0_unix") or 0.0)
                if t0_u <= 0.0 or (now - t0_u) > max_age_sec:
                    continue
                spot_t0 = float(trig.get("spot_at_t0") or trig.get("trigger_price") or 0.0)
                if spot_t0 > 0.0:
                    self.spots[asset] = spot_t0
                    self.spot_hist[asset].append((now, spot_t0))
                cl_px = trig.get("chainlink_proxy_spot") or trig.get("coinbase_spot")
                if cl_px and float(cl_px) > 0.0:
                    self.usd_spot_hist[asset].append((now, float(cl_px)))
                    self.usd_direct_flags[asset] = True
                if abs(float(trig.get("shock_ofi") or 0.0)) >= 0.55:
                    self._last_any_shock_ts_by_asset[asset] = now
                    fresh.append(trig)
        except Exception as exc:
            logger.debug(f"Shock tailer notice: {exc}")
        return fresh

    async def handle_shock_triggers(
        self,
        triggers: List[Dict[str, Any]],
        opps_out: List[Dict[str, Any]],
        now_ts: Optional[float] = None,
    ) -> None:
        if not triggers:
            return
        now = float(now_ts if now_ts is not None else time.time())
        for trig_s in triggers:
            a_up = str(trig_s.get("asset") or "").upper()
            if a_up:
                self._last_any_shock_ts_by_asset[a_up] = now
        # Step 1: Defensive <250ms adverse-selection cancellation on resting Maker bids
        if self.pending_maker_orders:
            await self.manage_pending_maker_orders()

        if os.getenv("PM_DISABLE_SHADOW_M4_CATCHUP", "0") == "1" or is_shadow_sleeve_quarantined("M4_SHOCK_STRIKE_CATCHUP"):
            return

        # Step 2: Offensive M4_SHOCK_STRIKE_CATCHUP across lagging <=24h near-ATM multi-strike ladders
        for trig in triggers:
            asset = str(trig.get("asset") or "").upper()
            if (now - self._last_m4_shock_ts_by_asset.get(asset, 0.0)) < 6.0:
                continue
            shock_ofi = float(trig.get("shock_ofi") or 0.0)
            shock_vol = float(trig.get("shock_volume_100ms") or 0.0)
            min_shock_vol = 750_000.0 if asset in ("BTC", "ETH") else 250_000.0
            if abs(shock_ofi) < 0.70 or shock_vol < min_shock_vol:
                continue
            spot = float(self.spots.get(asset) or trig.get("spot_at_t0") or 0.0)
            if spot <= 0.0:
                continue
            shock_up = str(trig.get("shock_direction") or "").upper() in ("BUY", "UP")
            cand_rungs: List[Tuple[StrikeRungSpec, str, str, float, Dict[str, Any]]] = []
            for _, rungs in list(self.strike_ladders.items()):
                if not rungs or rungs[0].asset != asset:
                    continue
                tte = rungs[0].end_ts - now
                if not (1800.0 <= tte <= 86400.0):
                    continue
                for sr in rungs:
                    if abs(math.log(sr.strike / spot)) > 0.035:
                        continue
                    svi_ev = evaluate_svi_digital_fair_value(
                        asset, spot, sr.strike, tte, is_downward=sr.is_downward, now_ts=now
                    )
                    if sr.is_downward:
                        side_lbl = "NO" if shock_up else "YES"
                    else:
                        side_lbl = "YES" if shock_up else "NO"
                    tok = sr.yes_token if side_lbl == "YES" else sr.no_token
                    p_fair = float(svi_ev["p_yes"] if side_lbl == "YES" else svi_ev["p_no"])
                    cand_rungs.append((sr, side_lbl, tok, p_fair, svi_ev))

            if not cand_rungs:
                continue
            self._last_m4_shock_ts_by_asset[asset] = now
            # Causal 50ms latency simulation once before parallel single-RTT book gather (no double book RTT!)
            await asyncio.sleep(0.050)
            books = await asyncio.gather(
                *[self.fetch_json(f"{CLOB_URL}/book?token_id={c[2]}", timeout=2.5) for c in cand_rungs]
            )
            best_m4: Optional[Tuple[float, StrikeRungSpec, str, str, float, Dict[str, Any], Dict[str, Any]]] = None
            best_m4_maker: Optional[Tuple[float, StrikeRungSpec, str, str, float, Dict[str, Any], Dict[str, Any]]] = None
            for (sr, side_lbl, tok, p_fair, svi_ev), bk in zip(cand_rungs, books):
                if not bk:
                    continue
                w_side = walk_l2_book_asks(bk.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)
                if not w_side.get("filled"):
                    continue
                vwap_px = float(w_side["vwap"])
                eff_px = float(w_side["eff_px"])
                edge = p_fair - eff_px
                best_bid_m4, _ = extract_best_bid(bk.get("bids") or [])
                best_ask_m4 = float(w_side["best_ask"])
                if 0.20 <= eff_px <= 0.86 and edge >= 0.035:
                    opps_out.append({
                        "sleeve": "M4_SHOCK_STRIKE_CATCHUP",
                        "market": f"{asset} {sr.question} ({side_lbl}) [ShockWakeup]",
                        "ask_vwap": eff_px,
                        "p_model": round(p_fair, 4),
                        "net_edge": round(edge, 4),
                        "l1_usd": w_side["l1_usd"],
                    })
                if 0.22 <= vwap_px <= 0.82 and 0.24 <= eff_px <= 0.84 and edge >= 0.065:
                    if best_m4 is None or edge > best_m4[0]:
                        best_m4 = (edge, sr, side_lbl, tok, p_fair, svi_ev, bk)
                elif best_bid_m4 > 0.0 and (best_ask_m4 - best_bid_m4) >= 0.02:
                    # Gemini #9 / ChatGPT #2: 0%-fee 3.5s `post_only=True` reactive maker bid when 7% taker fee eats the snipe!
                    mkr_px = round(min(best_bid_m4 + 0.01, best_ask_m4 - 0.01), 4)
                    mkr_edge = p_fair - mkr_px
                    if 0.20 <= mkr_px <= 0.80 and mkr_edge >= 0.065:
                        if best_m4_maker is None or mkr_edge > best_m4_maker[0]:
                            best_m4_maker = (mkr_edge, sr, side_lbl, tok, p_fair, svi_ev, bk)

            if best_m4 is not None:
                _, sr_b, side_b, tok_b, p_fair_b, svi_b, bk_b = best_m4
                await self.open_shadow_position(
                    sleeve="M4_SHOCK_STRIKE_CATCHUP",
                    dedupe_key=f"M4_{sr_b.market_id}_{side_b}_{int(now // 300)}",
                    asset_or_city=asset,
                    title=sr_b.question,
                    side_label=side_b,
                    token_id=tok_b,
                    fee_rate=CRYPTO_FEE_RATE,
                    p_model=p_fair_b,
                    close_ts=sr_b.end_ts,
                    extra={
                        "market_id": sr_b.market_id,
                        "condition_id": sr_b.condition_id,
                        "strike": sr_b.strike,
                        "is_downward": sr_b.is_downward,
                        "iv_annual": svi_b["iv_annual"],
                        "z_sigma": svi_b["z_sigma"],
                        "shock_id": trig.get("shock_id"),
                        "shock_ofi": trig.get("shock_ofi"),
                        "shock_vol_usd": trig.get("shock_volume_100ms"),
                    },
                    prefetched_book=bk_b,
                )
            elif best_m4_maker is not None:
                _, sr_m, side_m, tok_m, p_fair_m, svi_m, bk_m = best_m4_maker
                await self.post_shadow_maker_entry(
                    sleeve="M4_SHOCK_STRIKE_CATCHUP",
                    dedupe_key=f"M4MKR_{sr_m.market_id}_{side_m}_{int(now // 60)}",
                    asset=asset,
                    title=sr_m.question,
                    side_label=side_m,
                    token_id=tok_m,
                    p_model=p_fair_m,
                    close_ts=sr_m.end_ts,
                    extra={
                        "execution_mode": "REACTIVE_POST_ONLY_3P5S",
                        "market_id": sr_m.market_id,
                        "condition_id": sr_m.condition_id,
                        "strike": sr_m.strike,
                        "is_downward": sr_m.is_downward,
                        "iv_annual": svi_m["iv_annual"],
                        "z_sigma": svi_m["z_sigma"],
                        "shock_id": trig.get("shock_id"),
                    },
                    prefetched_book=bk_m,
                    ttl_override_sec=3.5,
                )

    @staticmethod
    def is_in_exact_twap_lock_window(now_ts: float) -> bool:
        """
        True during the final 55s of every 5-minute (and 15-minute) Chainlink 60s-TWAP
        boundary (`5.0 <= rem_5m <= 55.0`), stepping the daemon cadence to 3.0s.
        """
        target_end_ts = math.ceil(now_ts / 300.0) * 300.0
        rem_sec = target_end_ts - now_ts
        return 5.0 <= rem_sec <= 55.0

    async def discover_active_twap_candles(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        for k_old, sp_old in list(self.twap_candles.items()):
            if sp_old.end_ts < now - 300.0:
                self.twap_candles.pop(k_old, None)

        end_5m = int(math.ceil(now / 300.0) * 300)
        rem_5m = float(end_5m) - now
        if not (5.0 <= rem_5m <= 75.0):
            return

        # Reuse any pair already discovered by D1_SAME_ORACLE_DOMINANCE_BOX
        for _, (m15_p, m5_p) in self.dominance_pairs.items():
            if abs(m5_p.end_ts - end_5m) <= 2.0:
                self.twap_candles[f"{m5_p.asset}_5m_{end_5m}"] = m5_p
            if abs(m15_p.end_ts - end_5m) <= 2.0:
                self.twap_candles[f"{m15_p.asset}_15m_{end_5m}"] = m15_p

        now_iso = datetime.fromtimestamp(now - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        is_15m_boundary = (end_5m % 900) == 0
        for asset in DOMINANCE_ASSETS:
            slugs = DOMINANCE_SERIES_SLUGS[asset]
            k5 = f"{asset}_5m_{end_5m}"
            if k5 not in self.twap_candles:
                ev5_raw = await self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['5m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=3.5,
                )
                if isinstance(ev5_raw, list):
                    for ev in ev5_raw:
                        sp5 = parse_twap_candle_event(ev, asset, "5m")
                        if sp5 and abs(sp5.end_ts - end_5m) <= 2.0:
                            self.twap_candles[k5] = sp5
                            break
            if is_15m_boundary:
                k15 = f"{asset}_15m_{end_5m}"
                if k15 not in self.twap_candles:
                    ev15_raw = await self.fetch_json(
                        f"{GAMMA_URL}/events?series_slug={slugs['15m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                        timeout=3.5,
                    )
                    if isinstance(ev15_raw, list):
                        for ev in ev15_raw:
                            sp15 = parse_twap_candle_event(ev, asset, "15m")
                            if sp15 and abs(sp15.end_ts - end_5m) <= 2.0:
                                self.twap_candles[k15] = sp15
                                break

    async def scan_exact_twap_locks(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        rem_5m = (math.ceil(now / 300.0) * 300.0) - now
        if 5.0 <= rem_5m <= 75.0 and (now - self.last_twap_discovery_ts) >= 12.0:
            self.last_twap_discovery_ts = now
            await self.discover_active_twap_candles(now)

        s2_strict = os.getenv("PM_QUARANTINE_LOSING_SLEEVES", "1") == "1"
        max_s2_rem = 28.0 if s2_strict else 45.0
        min_s2_p = 0.975 if s2_strict else 0.965
        min_s2_z = 2.65 if s2_strict else 0.0

        for _, spec in list(self.twap_candles.items()):
            rem_sec = spec.end_ts - now
            if not (8.0 <= rem_sec <= max_s2_rem):
                continue
            if now < spec.start_ts + 60.0:
                continue

            k_open = await self.get_authoritative_open_strike(spec)
            if k_open is None or k_open <= 0.0:
                continue

            shm = read_shm_usd_anchor(spec.asset, now, max_age_sec=2.5)
            usd_hist = self.usd_spot_hist.get(spec.asset)
            cur_usd = shm.get("usd_spot")
            if (not cur_usd or float(cur_usd) <= 0.0) and usd_hist and (now - float(usd_hist[-1][0])) <= 5.0:
                cur_usd = float(usd_hist[-1][1])
            if (not cur_usd or float(cur_usd) <= 0.0) and self.usd_direct_flags.get(spec.asset, False):
                cur_usd = self.spots.get(spec.asset, 0.0)
            if not cur_usd or float(cur_usd) <= 0.0:
                continue
            cur_usd_f = float(cur_usd)
            usd_direct = bool(
                shm.get("source") in ("shm_chainlink_proxy", "shm_coinbase_usd")
                or self.usd_direct_flags.get(spec.asset, False)
            )
            iv_1d, _ = get_wing_implied_vol(spec.asset, cur_usd_f, k_open, 86400.0)
            samples = list(usd_hist or [])
            lock_ev = compute_exact_twap_lock_probability(
                asset=spec.asset,
                open_price=k_open,
                current_usd_spot=cur_usd_f,
                rem_seconds=rem_sec,
                now_ts=now,
                end_ts=spec.end_ts,
                spot_samples=samples,
                shm_twap_60s=shm.get("twap_60s"),
                iv_annual=iv_1d,
                usd_direct_feed=usd_direct,
            )
            if not lock_ev.get("eligible") or float(lock_ev["p_lock"]) < 0.940 or float(lock_ev.get("z_lock", 0.0)) < min_s2_z:
                continue

            win_side = str(lock_ev["side"])
            tok = spec.up_token if win_side == "UP" else spec.down_token
            bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=2.5)
            if not bk:
                continue
            w_chk = walk_l2_book_asks(
                bk.get("asks") or [],
                BANKROLL_TICKETS["T1000"]["S2_EXACT_TWAP_LOCK"],
                fee_rate=spec.fee_rate,
                min_l1_usd=15.0,
            )
            if not w_chk.get("filled"):
                continue
            eff_px = float(w_chk["eff_px"])
            p_lock = float(lock_ev["p_lock"])
            edge = p_lock - eff_px
            if 0.74 <= eff_px <= 0.955 and edge >= 0.015:
                opps_out.append({
                    "sleeve": "S2_EXACT_TWAP_LOCK",
                    "market": f"{spec.asset} {spec.horizon} {win_side} (TTE={rem_sec:.0f}s, alpha={lock_ev['eff_alpha']:.2f}, z={lock_ev['z_lock']:.2f})",
                    "ask_vwap": eff_px,
                    "p_model": p_lock,
                    "net_edge": round(edge, 4),
                    "l1_usd": w_chk["l1_usd"],
                })
            if p_lock >= min_s2_p and 0.76 <= eff_px <= 0.950 and edge >= 0.030:
                await self.open_shadow_position(
                    sleeve="S2_EXACT_TWAP_LOCK",
                    dedupe_key=f"S2_{spec.asset}_{spec.horizon}_{spec.market_id}",
                    asset_or_city=spec.asset,
                    title=f"{spec.title} [{spec.horizon} TWAP Lock]",
                    side_label=win_side,
                    token_id=tok,
                    fee_rate=spec.fee_rate,
                    p_model=p_lock,
                    close_ts=spec.end_ts,
                    extra={
                        "market_id": spec.market_id,
                        "condition_id": spec.condition_id,
                        "horizon": spec.horizon,
                        "start_iso": spec.start_iso,
                        "end_iso": spec.end_iso,
                        "open_price": k_open,
                        "mu_twap": lock_ev["mu_twap"],
                        "eff_alpha": lock_ev["eff_alpha"],
                        "z_lock": lock_ev["z_lock"],
                        "cushion_bps": lock_ev["cushion_bps"],
                        "rem_seconds_at_entry": lock_ev["rem_seconds"],
                    },
                    tp_target_px=None,
                    prefetched_book=bk,
                )

    async def discover_s5m_candles(self, now_ts: float) -> None:
        for k_old, sp_old in list(self.s5m_candles.items()):
            if sp_old.end_ts < now_ts - 300.0:
                self.s5m_candles.pop(k_old, None)

        end_5m = int(math.ceil(now_ts / 300.0) * 300)
        rem_5m = float(end_5m) - now_ts
        if not (35.0 <= rem_5m <= 185.0):
            return

        for _, (_, m5_p) in self.dominance_pairs.items():
            if m5_p.asset in ("BTC", "ETH") and abs(m5_p.end_ts - end_5m) <= 2.0:
                self.s5m_candles[f"{m5_p.asset}_5m_{end_5m}"] = m5_p
        for k_tw, sp_tw in self.twap_candles.items():
            if sp_tw.asset in ("BTC", "ETH") and sp_tw.horizon == "5m" and abs(sp_tw.end_ts - end_5m) <= 2.0:
                self.s5m_candles[k_tw] = sp_tw

        now_iso = datetime.fromtimestamp(now_ts - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for asset in ("BTC", "ETH"):
            k5 = f"{asset}_5m_{end_5m}"
            if k5 in self.s5m_candles:
                continue
            slug_5m = DOMINANCE_SERIES_SLUGS[asset]["5m"]
            ev5_raw = await self.fetch_json(
                f"{GAMMA_URL}/events?series_slug={slug_5m}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                timeout=3.5,
            )
            if isinstance(ev5_raw, list):
                for ev in ev5_raw:
                    sp5 = parse_twap_candle_event(ev, asset, "5m")
                    if sp5 and abs(sp5.end_ts - end_5m) <= 2.0:
                        self.s5m_candles[k5] = sp5
                        break

    async def scan_s5m_chainlink_sniper(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        """
        Addition #3 (`S5M_CHAINLINK_SNIPER`): Standalone `5m` BTC & ETH directional Chainlink sniper
        across all `288` daily 5m windows (`45s <= rem_sec <= 165s`), using authoritative Chainlink
        `openPrice` + SVI z-cushion + `0%`-fee `$0.96` Maker TP.
        """
        now = float(now_ts if now_ts is not None else time.time())
        rem_5m = (math.ceil(now / 300.0) * 300.0) - now
        if 40.0 <= rem_5m <= 180.0 and (now - self.last_s5m_discovery_ts) >= 20.0:
            self.last_s5m_discovery_ts = now
            await self.discover_s5m_candles(now)

        last_scan = float(getattr(self, "_last_s5m_book_scan_ts", 0.0) or 0.0)
        if not self.single_scan and (now - last_scan) < 9.5:
            return
        self._last_s5m_book_scan_ts = now

        for _, spec in list(self.s5m_candles.items()):
            rem_sec = spec.end_ts - now
            if not (45.0 <= rem_sec <= 165.0) or now < spec.start_ts + 25.0:
                continue
            k_open = await self.get_authoritative_open_strike(spec)
            if k_open is None or k_open <= 0.0:
                continue

            shm = read_shm_usd_anchor(spec.asset, now, max_age_sec=3.0)
            usd_hist = self.usd_spot_hist.get(spec.asset)
            cur_usd = shm.get("usd_spot")
            if (not cur_usd or float(cur_usd) <= 0.0) and usd_hist and (now - float(usd_hist[-1][0])) <= 5.0:
                cur_usd = float(usd_hist[-1][1])
            if not cur_usd or float(cur_usd) <= 0.0:
                cur_usd = self.spots.get(spec.asset, 0.0)
            if not cur_usd or float(cur_usd) <= 0.0:
                continue
            cur_usd_f = float(cur_usd)

            dist_pct = abs(cur_usd_f - k_open) / k_open * 100.0
            if dist_pct < 0.085:
                continue

            win_side = "UP" if cur_usd_f > k_open else "DOWN"
            ret_15s = self.get_return_bps(spec.asset, 15.0)
            if (win_side == "UP" and ret_15s < -4.0) or (win_side == "DOWN" and ret_15s > 4.0):
                continue

            svi_ev = evaluate_svi_digital_fair_value(
                spec.asset, cur_usd_f, k_open, rem_sec, is_downward=False, now_ts=now
            )
            p_fair = float(svi_ev["p_yes"] if win_side == "UP" else svi_ev["p_no"])
            z_sig = abs(float(svi_ev.get("z_sigma") or 0.0))
            if z_sig < 1.35 or p_fair < 0.905:
                continue

            tok = spec.up_token if win_side == "UP" else spec.down_token
            bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=2.5)
            if not bk:
                continue
            w_chk = walk_l2_book_asks(
                bk.get("asks") or [],
                BANKROLL_TICKETS["T1000"]["S5M_CHAINLINK_SNIPER"],
                fee_rate=spec.fee_rate,
                min_l1_usd=18.0,
            )
            if not w_chk.get("filled"):
                continue
            eff_px = float(w_chk["eff_px"])
            edge = p_fair - eff_px
            if 0.58 <= eff_px <= 0.86 and edge >= 0.025:
                opps_out.append({
                    "sleeve": "S5M_CHAINLINK_SNIPER",
                    "market": f"{spec.asset} 5m {win_side} (TTE={rem_sec:.0f}s, dist={dist_pct:.3f}%, z={z_sig:.2f})",
                    "ask_vwap": eff_px,
                    "p_model": round(p_fair, 4),
                    "net_edge": round(edge, 4),
                    "l1_usd": w_chk["l1_usd"],
                    "close_ts": spec.end_ts,
                })
            if 0.58 <= eff_px <= 0.86 and edge >= 0.045:
                await self.open_shadow_position(
                    sleeve="S5M_CHAINLINK_SNIPER",
                    dedupe_key=f"S5M_{spec.asset}_{spec.market_id}",
                    asset_or_city=spec.asset,
                    title=f"{spec.title} [5m Chainlink Sniper]",
                    side_label=win_side,
                    token_id=tok,
                    fee_rate=spec.fee_rate,
                    p_model=p_fair,
                    close_ts=spec.end_ts,
                    extra={
                        "market_id": spec.market_id,
                        "condition_id": spec.condition_id,
                        "horizon": "5m",
                        "start_iso": spec.start_iso,
                        "end_iso": spec.end_iso,
                        "open_price": k_open,
                        "dist_pct": round(dist_pct, 4),
                        "z_sigma": z_sig,
                    },
                    tp_target_px=0.96,
                    prefetched_book=bk,
                )

    async def discover_upcoming_15m_candles(self, now_ts: float) -> None:
        for k_old, sp_old in list(self.preopen_15m_candles.items()):
            if sp_old.start_ts <= now_ts + 5.0:
                self.preopen_15m_candles.pop(k_old, None)

        next_start_ts = int(math.ceil(now_ts / 900.0) * 900)
        sec_to_open = float(next_start_ts) - now_ts
        if not (25.0 <= sec_to_open <= 250.0):
            return

        now_iso = datetime.fromtimestamp(now_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for asset in ("BTC", "ETH"):
            k_pre = f"{asset}_pre15m_{next_start_ts}"
            if k_pre in self.preopen_15m_candles:
                continue
            slug_15m = DOMINANCE_SERIES_SLUGS[asset]["15m"]
            ev15_raw = await self.fetch_json(
                f"{GAMMA_URL}/events?series_slug={slug_15m}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=5",
                timeout=3.5,
            )
            if isinstance(ev15_raw, list):
                for ev in ev15_raw:
                    sp15 = parse_twap_candle_event(ev, asset, "15m")
                    if sp15 and abs(sp15.start_ts - next_start_ts) <= 2.0:
                        self.preopen_15m_candles[k_pre] = sp15
                        break

    async def scan_and_manage_preopen_maker_straddles(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        """
        Addition #5 (`P1_PREOPEN_MAKER_STRADDLE`): Posts passive `0%`-fee `$0.48` UP + `$0.48` DOWN
        Maker bids (`$0.96` combined cost -> guaranteed `$1.00` payout) during the `30s..240s` window
        BEFORE an upcoming `15m` BTC/ETH candle fixes `openPrice`. Explicitly tracks both:
          - 2-leg fills -> locked `$0.96 -> $1.00` complete-set position (`+4.17%` riskless)
          - 1-leg unhedged fills -> immediate taker scratch at `start_ts - 10s` or `>18bps` impulse
            recorded into `closed_positions` so shadow expectancy has zero survivorship bias!
        """
        if is_shadow_sleeve_quarantined("P1_PREOPEN_MAKER_STRADDLE"):
            if self.pending_preopen_straddles:
                self.pending_preopen_straddles.clear()
            return
        now = float(now_ts if now_ts is not None else time.time())
        next_start_ts = int(math.ceil(now / 900.0) * 900)
        sec_to_open = float(next_start_ts) - now
        if 25.0 <= sec_to_open <= 250.0 and (now - self.last_preopen_discovery_ts) >= 20.0:
            self.last_preopen_discovery_ts = now
            await self.discover_upcoming_15m_candles(now)

        last_p1 = float(getattr(self, "_last_p1_manage_ts", 0.0) or 0.0)
        if not self.single_scan and not self.pending_preopen_straddles and not (30.0 <= sec_to_open <= 245.0):
            return
        if not self.single_scan and (now - last_p1) < 8.0:
            return
        self._last_p1_manage_ts = now

        # 1. Manage existing pending pre-open straddles first
        for d_key, st in list(self.pending_preopen_straddles.items()):
            spec: TwapCandleMarketSpec = st["spec"]
            bk_up, bk_dn = await asyncio.gather(
                self.fetch_json(f"{CLOB_URL}/book?token_id={spec.up_token}", timeout=2.5),
                self.fetch_json(f"{CLOB_URL}/book?token_id={spec.down_token}", timeout=2.5),
            )
            bid_px = float(st["bid_px"])
            rested_sec = now - float(st["posted_ts"])
            if bk_up and rested_sec >= 4.0:
                asks_up = bk_up.get("asks") or []
                best_ask_up = min((float(a["price"]) for a in asks_up if float(a.get("size", 0)) > 0), default=1.0)
                if best_ask_up <= bid_px:
                    st["up_filled"] = True
            if bk_dn and rested_sec >= 4.0:
                asks_dn = bk_dn.get("asks") or []
                best_ask_dn = min((float(a["price"]) for a in asks_dn if float(a.get("size", 0)) > 0), default=1.0)
                if best_ask_dn <= bid_px:
                    st["dn_filled"] = True

            # Outcome A: Both legs filled passively -> lock guaranteed $0.96 -> $1.00 complete set!
            if st["up_filled"] and st["dn_filled"]:
                self.pending_preopen_straddles.pop(d_key, None)
                pair_cost = round(2.0 * bid_px, 4)
                tier_fills: Dict[str, Dict[str, Any]] = {}
                for t_name, t_map in BANKROLL_TICKETS.items():
                    sh = round(t_map["P1_PREOPEN_MAKER_STRADDLE"] / pair_cost, 4)
                    spent = round(sh * pair_cost, 2)
                    tier_fills[t_name] = {
                        "filled": True,
                        "vwap": pair_cost,
                        "eff_px": pair_cost,
                        "spent_usd": spent,
                        "fee_usd": 0.0,
                        "shares": sh,
                        "l1_usd": 100.0,
                    }
                pos_id = f"P1_PREOPEN_MAKER_STRADDLE_{int(now)}_{spec.market_id[-6:]}"
                legs = [
                    {"token_id": spec.up_token, "side": "UP", "market_id": spec.market_id, "label": "PRE_UP"},
                    {"token_id": spec.down_token, "side": "DOWN", "market_id": spec.market_id, "label": "PRE_DOWN"},
                ]
                pos = {
                    "position_id": pos_id,
                    "dedupe_key": d_key,
                    "sleeve": "P1_PREOPEN_MAKER_STRADDLE",
                    "asset_or_city": spec.asset,
                    "title": f"{spec.title} [Pre-Open Maker $0.48+$0.48]",
                    "side": "PRE_UP+PRE_DOWN",
                    "token_id": f"{spec.up_token}|{spec.down_token}",
                    "fee_rate": 0.0,
                    "entry_ts": now,
                    "entry_utc": datetime.now(timezone.utc).isoformat(),
                    "close_ts": spec.end_ts,
                    "p_model_entry": 1.0,
                    "entry_eff_px_t1000": pair_cost,
                    "entry_vwap_t1000": pair_cost,
                    "realized_edge_t1000": round(1.0 - pair_cost, 4),
                    "entry_best_bid": pair_cost,
                    "last_bid": pair_cost,
                    "maker_tp_px": None,
                    "tier_fills": tier_fills,
                    "extra": {
                        "is_multi_leg_bundle": True,
                        "guaranteed_payout": 1.0,
                        "market_id": spec.market_id,
                        "legs": legs,
                    },
                    "status": "OPEN",
                }
                self.open_positions[pos_id] = pos
                self.entered_keys.add(d_key)
                self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                logger.info(
                    f"[ENTRY:P1_PREOPEN_MAKER_STRADDLE] {pos['title']} | BOTH LEGS FILLED @ ${pair_cost:.2f} -> $1.00 lock!"
                )
                continue

            # Outcome B: Pre-open cutoff (`start_ts - 10s`) or >18 bps spot move -> cancel or scratch single leg!
            cur_spot = float(self.spots.get(spec.asset) or st["posted_spot"] or 0.0)
            posted_spot = float(st["posted_spot"] or cur_spot or 1.0)
            move_bps = abs(cur_spot - posted_spot) / max(1e-9, posted_spot) * 10000.0
            if now >= (spec.start_ts - 10.0) or move_bps > 18.0:
                self.pending_preopen_straddles.pop(d_key, None)
                self.entered_keys.add(d_key)
                if not st["up_filled"] and not st["dn_filled"]:
                    continue
                filled_up = bool(st["up_filled"])
                bk_scr = bk_up if filled_up else bk_dn
                scr_bid, _ = extract_best_bid((bk_scr or {}).get("bids") or [])
                if scr_bid <= 0.0:
                    scr_bid = max(0.01, bid_px - 0.03)
                taker_fee_ps = spec.fee_rate * scr_bid * (1.0 - scr_bid)
                net_scr_ps = max(0.0, scr_bid - taker_fee_ps)
                tier_fills_s: Dict[str, Dict[str, Any]] = {}
                tier_pnls_s: Dict[str, float] = {}
                for t_name, t_map in BANKROLL_TICKETS.items():
                    leg_budget = round(0.5 * t_map["P1_PREOPEN_MAKER_STRADDLE"], 2)
                    sh_s = round(leg_budget / bid_px, 4)
                    tier_fills_s[t_name] = {
                        "filled": True,
                        "vwap": bid_px,
                        "eff_px": bid_px,
                        "spent_usd": leg_budget,
                        "fee_usd": 0.0,
                        "shares": sh_s,
                    }
                    tier_pnls_s[t_name] = round(sh_s * net_scr_ps - leg_budget, 2)
                pos_scr = {
                    "position_id": f"P1_SCRATCH_{int(now)}_{spec.market_id[-6:]}",
                    "dedupe_key": d_key,
                    "sleeve": "P1_PREOPEN_MAKER_STRADDLE",
                    "asset_or_city": spec.asset,
                    "title": f"{spec.title} [Pre-Open 1-Leg Scratch]",
                    "side": "PRE_UP_SCRATCH" if filled_up else "PRE_DOWN_SCRATCH",
                    "token_id": spec.up_token if filled_up else spec.down_token,
                    "fee_rate": 0.0,
                    "entry_ts": st["posted_ts"],
                    "entry_utc": datetime.fromtimestamp(st["posted_ts"], tz=timezone.utc).isoformat(),
                    "close_ts": spec.end_ts,
                    "closed_ts": now,
                    "closed_utc": datetime.now(timezone.utc).isoformat(),
                    "p_model_entry": 0.5,
                    "entry_eff_px_t1000": bid_px,
                    "entry_vwap_t1000": bid_px,
                    "net_payout_per_share": round(net_scr_ps, 4),
                    "tier_fills": tier_fills_s,
                    "tier_pnls_usd": tier_pnls_s,
                    "won": tier_pnls_s.get("T1000", 0.0) > 0,
                    "status": "PREOPEN_ONE_LEG_SCRATCH",
                }
                self.closed_positions.append(pos_scr)
                self._append_ledger({"event": "SHADOW_CLOSE", **pos_scr})
                logger.info(
                    f"[CLOSE:P1_PREOPEN_MAKER_STRADDLE] {pos_scr['title']} -> PREOPEN_ONE_LEG_SCRATCH | "
                    f"bid_exit=${scr_bid:.3f} net=${net_scr_ps:.4f} | PnL T1000=${tier_pnls_s.get('T1000', 0.0):+.2f}"
                )

        # 2. Post fresh passive $0.48 + $0.48 Maker straddles on upcoming symmetric 15m books
        for _, spec in list(self.preopen_15m_candles.items()):
            sec_rem_open = spec.start_ts - now
            if not (40.0 <= sec_rem_open <= 240.0):
                continue
            d_key = f"P1_{spec.asset}_{spec.market_id}"
            if d_key in self.entered_keys or d_key in self.pending_preopen_straddles:
                continue
            if abs(self.get_return_bps(spec.asset, 15.0)) > 8.0:
                continue
            bk_up, bk_dn = await asyncio.gather(
                self.fetch_json(f"{CLOB_URL}/book?token_id={spec.up_token}", timeout=2.5),
                self.fetch_json(f"{CLOB_URL}/book?token_id={spec.down_token}", timeout=2.5),
            )
            if not bk_up or not bk_dn:
                continue
            bid_up, _ = extract_best_bid(bk_up.get("bids") or [])
            bid_dn, _ = extract_best_bid(bk_dn.get("bids") or [])
            asks_up = bk_up.get("asks") or []
            asks_dn = bk_dn.get("asks") or []
            ask_up = min((float(a["price"]) for a in asks_up if float(a.get("size", 0)) > 0), default=1.0)
            ask_dn = min((float(a["price"]) for a in asks_dn if float(a.get("size", 0)) > 0), default=1.0)
            if ask_up >= 0.49 and ask_dn >= 0.49 and 0.44 <= bid_up <= 0.51 and 0.44 <= bid_dn <= 0.51:
                opps_out.append({
                    "sleeve": "P1_PREOPEN_MAKER_STRADDLE",
                    "market": f"{spec.asset} Pre-Open 15m Straddle (T-{sec_rem_open:.0f}s, asks={ask_up:.2f}/{ask_dn:.2f})",
                    "ask_vwap": 0.96,
                    "p_model": 1.0,
                    "net_edge": 0.04,
                    "l1_usd": 100.0,
                    "close_ts": spec.end_ts,
                })
                self.pending_preopen_straddles[d_key] = {
                    "spec": spec,
                    "bid_px": 0.48,
                    "posted_ts": now,
                    "posted_spot": float(self.spots.get(spec.asset) or 0.0),
                    "up_filled": False,
                    "dn_filled": False,
                }
                logger.info(
                    f"[MAKER_POST:P1_PREOPEN_MAKER_STRADDLE] {spec.title} | Resting $0.48 UP + $0.48 DOWN (T-{sec_rem_open:.0f}s)"
                )

    async def resolve_via_gamma_market(self, pos: Dict[str, Any]) -> Optional[float]:
        """
        Queries Polymarket Gamma API `/markets/{market_id}` (or `?clob_token_ids=`) to resolve
        closed markets whose CLOB `/book` endpoint returns 404 after resolution (e.g. Weather W1/W2,
        Barrier B1/B2, Multi-Strike M1/M2). Matches `pos['token_id']` against `clobTokenIds`.
        Returns 1.0 (won), 0.0 (lost), or None (not yet resolved).
        """
        extra = pos.get("extra") or {}
        m_id = str(extra.get("market_id") or "")
        tok = str(pos.get("token_id") or "")
        gm: Optional[Dict[str, Any]] = None
        if m_id:
            res = await self.fetch_json(f"{GAMMA_URL}/markets/{m_id}", timeout=4.0)
            if isinstance(res, dict):
                gm = res
        if gm is None and tok:
            res_list = await self.fetch_json(f"{GAMMA_URL}/markets?clob_token_ids={tok}", timeout=4.0)
            if isinstance(res_list, list) and res_list:
                gm = res_list[0]
        if not isinstance(gm, dict) or not gm.get("closed"):
            return None

        uma_st = str(gm.get("umaResolutionStatus") or "").strip().lower()
        if uma_st and uma_st != "resolved":
            return None

        toks = gm.get("clobTokenIds")
        if isinstance(toks, str):
            try:
                toks = json.loads(toks)
            except Exception:
                toks = []
        op = gm.get("outcomePrices")
        if isinstance(op, str):
            try:
                op = json.loads(op)
            except Exception:
                op = []
        if not isinstance(op, list) or len(op) < 2:
            return None

        idx_match = -1
        if isinstance(toks, list) and tok in [str(t) for t in toks]:
            idx_match = [str(t) for t in toks].index(tok)
        else:
            idx_match = 0 if str(pos.get("side", "YES")).upper() in ("YES", "UP") else 1

        if idx_match < 0 or idx_match >= len(op):
            return None
        try:
            px = float(op[idx_match])
        except Exception:
            return None
        if px >= 0.99:
            return 1.0
        if px <= 0.01:
            return 0.0
        return None

    async def manage_open_positions(self) -> None:
        now = time.time()
        loop = asyncio.get_running_loop()
        to_close: List[Tuple[str, str, float, float]] = []  # (pos_id, status, payout_per_share, exit_fee_rate)

        for pid, pos in list(self.open_positions.items()):
            sleeve = pos["sleeve"]
            tok = pos["token_id"]

            # 0A. Dedicated multi-leg supervision & settlement for D1, M3_LADDER_MONO_BOX, C1_BINARY_COMPLETE_SET & W3_WEATHER_SLATE_ARB
            if sleeve == "W3_WEATHER_SLATE_ARB":
                close_ts_f = float(pos["close_ts"])
                if now >= close_ts_f + 30.0:
                    legs = (pos.get("extra") or {}).get("legs") or []
                    resolved_vals = await asyncio.gather(
                        *[
                            self.resolve_via_gamma_market(
                                {"token_id": lg["yes_token"], "side": "YES", "extra": {"market_id": lg["market_id"]}}
                            )
                            for lg in legs
                        ]
                    )
                    if resolved_vals and all(v is not None for v in resolved_vals):
                        total_pay = round(sum(float(v) for v in resolved_vals if v is not None), 4)
                        to_close.append((pid, "SETTLED_WEATHER_SLATE_1X", max(1.0, total_pay), 0.0))
                continue

            if sleeve in (
                "D1_SAME_ORACLE_DOMINANCE_BOX",
                "D1_4H_DOMINANCE_BOX",
                "D1_QUIET_BOOK_BOX",
                "M3_LADDER_MONO_BOX",
                "C1_BINARY_COMPLETE_SET",
            ):
                extra = pos.get("extra") or {}
                leg_a = extra.get("leg_a") or {}
                leg_b = extra.get("leg_b") or {}
                close_ts_f = float(pos["close_ts"])
                if now < close_ts_f + 10.0:
                    bk_a, bk_b = await asyncio.gather(
                        self.fetch_json(f"{CLOB_URL}/book?token_id={leg_a.get('token_id', '')}", timeout=2.5),
                        self.fetch_json(f"{CLOB_URL}/book?token_id={leg_b.get('token_id', '')}", timeout=2.5),
                    )
                    if bk_a and bk_b:
                        bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
                        bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
                        pos["last_bid"] = round(bid_a + bid_b, 4)
                    continue

                pay_a, pay_b = await asyncio.gather(
                    self.resolve_via_gamma_market(
                        {"token_id": leg_a.get("token_id", ""), "side": leg_a.get("side", "UP"), "extra": {"market_id": leg_a.get("market_id", "")}}
                    ),
                    self.resolve_via_gamma_market(
                        {"token_id": leg_b.get("token_id", ""), "side": leg_b.get("side", "DOWN"), "extra": {"market_id": leg_b.get("market_id", "")}}
                    ),
                )
                if pay_a is not None and pay_b is not None:
                    total_pay = round(float(pay_a) + float(pay_b), 4)
                    st_lbl = "SETTLED_DOMINANCE_DOUBLE_2X" if total_pay >= 1.99 else "SETTLED_DOMINANCE_FLOOR_1X"
                    to_close.append((pid, st_lbl, total_pay, 0.0))
                    continue

                if now >= close_ts_f + 360.0 and extra.get("m15_start_iso"):
                    dur_a = 14400.0 if str(leg_a.get("horizon")) == "4h" else (900.0 if str(leg_a.get("horizon")) == "15m" else 300.0)
                    dur_b = 14400.0 if str(leg_b.get("horizon")) == "4h" else (900.0 if str(leg_b.get("horizon")) == "15m" else 300.0)
                    ev_a_url = build_own_gamma_event_url(pos["asset_or_city"], str(leg_a.get("horizon") or "15m"), close_ts_f - dur_a)
                    ev_b_url = build_own_gamma_event_url(pos["asset_or_city"], str(leg_b.get("horizon") or "5m"), close_ts_f - dur_b)
                    ev_a_raw, ev_b_raw = await asyncio.gather(
                        self.fetch_json(ev_a_url, timeout=4.0),
                        self.fetch_json(ev_b_url, timeout=4.0),
                    )
                    pa_ev = parse_closed_gamma_event_settlement(ev_a_raw, str(leg_a.get("side") or "UP"), ev_a_url)
                    pb_ev = parse_closed_gamma_event_settlement(ev_b_raw, str(leg_b.get("side") or "DOWN"), ev_b_url)
                    if pa_ev is not None and pb_ev is not None:
                        total_pay = round(pa_ev + pb_ev, 4)
                        st_lbl = (
                            "SETTLED_ORACLE_DOUBLE_2X"
                            if total_pay >= 1.99
                            else ("SETTLED_ORACLE_FLOOR_1X" if total_pay >= 0.99 else "SETTLED_ORACLE_LOSS_0X")
                        )
                        to_close.append((pid, st_lbl, total_pay, 0.0))
                continue

            if sleeve in ("N1_NEGRISK_CROSS_BOX", "P1_PREOPEN_MAKER_STRADDLE"):
                extra = pos.get("extra") or {}
                legs = extra.get("legs") or []
                close_ts_f = float(pos["close_ts"])
                if now < close_ts_f + 20.0:
                    if (now - float(pos.get("_last_book_poll_ts") or 0.0)) >= 30.0 and legs:
                        pos["_last_book_poll_ts"] = now
                        bks_m = await asyncio.gather(
                            *[self.fetch_json(f"{CLOB_URL}/book?token_id={lg['token_id']}", timeout=2.5) for lg in legs]
                        )
                        if all(bks_m):
                            pos["last_bid"] = round(
                                sum(extract_best_bid((b or {}).get("bids") or [])[0] for b in bks_m), 4
                            )
                    continue
                resolved_vals = await asyncio.gather(
                    *[
                        self.resolve_via_gamma_market(
                            {
                                "token_id": lg["token_id"],
                                "side": lg.get("side", "YES"),
                                "extra": {"market_id": lg.get("market_id", "")},
                            }
                        )
                        for lg in legs
                    ]
                )
                if resolved_vals and all(v is not None for v in resolved_vals):
                    total_pay = round(sum(float(v) for v in resolved_vals if v is not None), 4)
                    to_close.append((pid, "SETTLED_MULTI_LEG_ARB", total_pay, 0.0))
                elif sleeve == "P1_PREOPEN_MAKER_STRADDLE" and now >= close_ts_f + 900.0:
                    to_close.append((pid, "SETTLED_COMPLETE_SET_1X", 1.0, 0.0))
                continue

            # 0B. Dedicated hold-to-expiry & authoritative Chainlink TWAP settlement for S2_EXACT_TWAP_LOCK
            if sleeve == "S2_EXACT_TWAP_LOCK":
                extra = pos.get("extra") or {}
                close_ts_f = float(pos["close_ts"])
                if now < close_ts_f + 12.0:
                    bk_s2 = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=2.5)
                    if bk_s2:
                        bid_s2, _ = extract_best_bid(bk_s2.get("bids") or [])
                        pos["last_bid"] = bid_s2
                    continue
                g_pay = await self.resolve_via_gamma_market(pos)
                if g_pay is not None:
                    st_lbl = "SETTLED_GAMMA_WIN" if g_pay >= 0.99 else "SETTLED_GAMMA_LOSS"
                    to_close.append((pid, st_lbl, g_pay, 0.0))
                    continue
                if now >= close_ts_f + 120.0 and extra.get("start_iso"):
                    cp_url = build_own_gamma_event_url(
                        pos["asset_or_city"],
                        str(extra.get("horizon") or "15m"),
                        extra["start_iso"],
                    )
                    cp_payload = await self.fetch_json(cp_url, timeout=4.0)
                    close_px = parse_authoritative_close_price(cp_payload)
                    open_px = float(extra.get("open_price") or 0.0)
                    if close_px is not None and open_px > 0.0:
                        up_won = close_px >= open_px
                        won = up_won if str(pos.get("side")).upper() == "UP" else (not up_won)
                        st_lbl = "SETTLED_ORACLE_TWAP_WIN" if won else "SETTLED_ORACLE_TWAP_LOSS"
                        to_close.append((pid, st_lbl, 1.0 if won else 0.0, 0.0))
                continue

            # 1. Check finalized 1m Binance candle wicks on B1/B2 (exact Polymarket Hit-Price oracle rule!)
            # Note: Polymarket Hit markets resolve on FINALIZED 1m candle High/Low, NOT unclosed transient ticks,
            # AND a sub-15s wick inside a finalized 1m candle breaches the barrier even if spot mean-reverted!
            if sleeve in ("B1_CONVEX_TAIL_YES", "B2_BARRIER_NO_LOCK"):
                asset = pos["asset_or_city"]
                k = float(pos["extra"].get("strike") or 0.0)
                d = pos["extra"].get("direction")
                last_w_chk = float(pos.get("_last_wick_chk_ts") or 0.0)
                if k > 0 and (now - last_w_chk) >= 60.0:
                    pos["_last_wick_chk_ts"] = now
                    w_start = float(pos["extra"].get("start_ts") or pos["entry_ts"])
                    w_end = min(now, float(pos["close_ts"]))
                    ext_1m = await loop.run_in_executor(
                        None, fetch_binance_window_extremes_sync, asset, w_start, w_end, "1m"
                    )
                    if ext_1m is not None:
                        max_h, min_l, _ = ext_1m
                        touched = (d == "UP" and max_h >= k) or (d == "DOWN" and min_l <= k)
                        if touched:
                            pay_ps = 1.0 if pos["side"] == "YES" else 0.0
                            to_close.append((pid, "BARRIER_1M_WICK_SETTLED", pay_ps, 0.0))
                            continue

            # 2. Poll live CLOB book for Maker TP fills or SVI invalidation stop
            # Throttle non-expiring 24h position book polls during final-55s S2 TWAP lock window
            if (
                not self.single_scan
                and self.is_in_exact_twap_lock_window(now)
                and float(pos["close_ts"]) > now + 120.0
                and (now - float(pos.get("_last_book_poll_ts") or 0.0)) < 20.0
            ):
                continue
            pos["_last_book_poll_ts"] = now
            bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=3.0)
            if bk:
                best_bid, _ = extract_best_bid(bk.get("bids") or [])
                pos["last_bid"] = best_bid
                tp_px = pos.get("maker_tp_px")
                # Conservative passive Maker fill: require live best_bid >= tp_px
                if tp_px and best_bid >= float(tp_px) and (now - pos["entry_ts"]) >= 15.0:
                    to_close.append((pid, "MAKER_TP_FILLED", float(tp_px), 0.0))
                    continue

                # Check Hard Stop and Time-Stop on M1_SVI_MAKER_SCALP & M4_SHOCK_STRIKE_CATCHUP
                if sleeve in ("M1_SVI_MAKER_SCALP", "M4_SHOCK_STRIKE_CATCHUP") and best_bid > 0 and (now - pos["entry_ts"]) >= 30.0:
                    entry_vwap = float(pos["entry_vwap_t1000"])
                    rem_tte = float(pos["close_ts"]) - now
                    stop_drop = 0.085 if sleeve == "M4_SHOCK_STRIKE_CATCHUP" else 0.075
                    min_tte_stop = 900.0 if sleeve == "M4_SHOCK_STRIKE_CATCHUP" else 3600.0
                    if best_bid <= entry_vwap - stop_drop:
                        exit_fee_ps = CRYPTO_FEE_RATE * best_bid * (1.0 - best_bid)
                        to_close.append((pid, "HARD_STOP_SVI", max(0.0, best_bid - exit_fee_ps), 0.0))
                        continue
                    if rem_tte <= min_tte_stop:
                        exit_fee_ps = CRYPTO_FEE_RATE * best_bid * (1.0 - best_bid)
                        to_close.append((pid, "TIME_STOP", max(0.0, best_bid - exit_fee_ps), 0.0))
                        continue

                # Check Salvage Stop (-22c) on M2_STRIKE_CONVERGENCE
                if sleeve == "M2_STRIKE_CONVERGENCE" and best_bid > 0 and (now - pos["entry_ts"]) >= 30.0:
                    entry_vwap = float(pos["entry_vwap_t1000"])
                    if best_bid <= max(0.25, entry_vwap - 0.22):
                        exit_fee_ps = CRYPTO_FEE_RATE * best_bid * (1.0 - best_bid)
                        to_close.append((pid, "SALVAGE_STOP", max(0.0, best_bid - exit_fee_ps), 0.0))
                        continue
            else:
                # CLOB /book returned None (404 happens immediately when Polymarket closes/resolves a market early, e.g. Weather!)
                last_g_chk = float(pos.get("_last_gamma_chk_ts") or 0.0)
                if (now - last_g_chk) >= 60.0:
                    pos["_last_gamma_chk_ts"] = now
                    g_pay = await self.resolve_via_gamma_market(pos)
                    if g_pay is not None:
                        st_lbl = "SETTLED_GAMMA_WIN" if g_pay >= 0.99 else "SETTLED_GAMMA_LOSS"
                        to_close.append((pid, st_lbl, g_pay, 0.0))
                        continue

            # 3. Check authoritative Gamma resolution (and verified oracle fallback) if past close_ts
            if now >= float(pos["close_ts"]) + 30.0:
                g_pay = await self.resolve_via_gamma_market(pos)
                if g_pay is not None:
                    st_lbl = "SETTLED_GAMMA_WIN" if g_pay >= 0.99 else "SETTLED_GAMMA_LOSS"
                    to_close.append((pid, st_lbl, g_pay, 0.0))
                    continue

                if bk:
                    best_bid, _ = extract_best_bid(bk.get("bids") or [])
                    asks = bk.get("asks") or []
                    best_ask = min((float(a["price"]) for a in asks if float(a.get("size", 0)) > 0), default=1.0)
                    if best_bid >= 0.99:
                        to_close.append((pid, "SETTLED_WIN", 1.0, 0.0))
                        continue
                    if best_ask <= 0.01:
                        to_close.append((pid, "SETTLED_LOSS", 0.0, 0.0))
                        continue

                # Authoritative Chainlink 60s-TWAP fallback for S5M_CHAINLINK_SNIPER if Gamma lags >= 120s
                if sleeve == "S5M_CHAINLINK_SNIPER" and now >= float(pos["close_ts"]) + 120.0:
                    extra = pos.get("extra") or {}
                    if extra.get("start_iso"):
                        cp_url = build_own_gamma_event_url(pos["asset_or_city"], "5m", extra["start_iso"])
                        cp_payload = await self.fetch_json(cp_url, timeout=4.0)
                        close_px = parse_authoritative_close_price(cp_payload)
                        open_px = float(extra.get("open_price") or 0.0)
                        if close_px is not None and open_px > 0.0:
                            up_won = close_px >= open_px
                            won = up_won if str(pos.get("side")).upper() == "UP" else (not up_won)
                            st_lbl = "SETTLED_ORACLE_TWAP_WIN" if won else "SETTLED_ORACLE_TWAP_LOSS"
                            to_close.append((pid, st_lbl, 1.0 if won else 0.0, 0.0))
                            continue

                # Verified 1m-kline fallback if Gamma lags > 15 minutes past close_ts on Crypto sleeves
                if now >= float(pos["close_ts"]) + 900.0:
                    if sleeve in ("B1_CONVEX_TAIL_YES", "B2_BARRIER_NO_LOCK"):
                        asset = pos["asset_or_city"]
                        k = float(pos["extra"].get("strike") or 0.0)
                        d = pos["extra"].get("direction")
                        w_start = float(pos["extra"].get("start_ts") or pos["entry_ts"])
                        ext_fin = await loop.run_in_executor(
                            None, fetch_binance_window_extremes_sync, asset, w_start, float(pos["close_ts"]), "1m"
                        )
                        if ext_fin is not None and k > 0:
                            max_h, min_l, _ = ext_fin
                            touched = (d == "UP" and max_h >= k) or (d == "DOWN" and min_l <= k)
                            pay_ps = (1.0 if touched else 0.0) if pos["side"] == "YES" else (0.0 if touched else 1.0)
                            to_close.append((pid, "SETTLED_VERIFIED_1M_ORACLE", pay_ps, 0.0))
                            continue
                    elif sleeve == "U1_DAILY_UPDOWN_LOCK":
                        asset = pos["asset_or_city"]
                        k = float(pos["extra"]["strike"])
                        close_ts_f = float(pos["close_ts"])
                        ext_exp = await loop.run_in_executor(
                            None, fetch_binance_window_extremes_sync, asset, close_ts_f - 120.0, close_ts_f, "1m"
                        )
                        if ext_exp is not None and k > 0:
                            exp_close = ext_exp[2]
                            won = (exp_close >= k) if str(pos["side"]).upper() == "UP" else (exp_close < k)
                            to_close.append((pid, "SETTLED_VERIFIED_1M_CLOSE", 1.0 if won else 0.0, 0.0))
                            continue
                    elif sleeve in ("M1_SVI_MAKER_SCALP", "M2_STRIKE_CONVERGENCE", "M4_SHOCK_STRIKE_CATCHUP"):
                        asset = pos["asset_or_city"]
                        k = float(pos["extra"]["strike"])
                        is_dn = bool(pos["extra"].get("is_downward"))
                        close_ts_f = float(pos["close_ts"])
                        ext_exp = await loop.run_in_executor(
                            None, fetch_binance_window_extremes_sync, asset, close_ts_f - 120.0, close_ts_f, "1m"
                        )
                        if ext_exp is not None and k > 0:
                            exp_close = ext_exp[2]
                            yes_won = (exp_close < k) if is_dn else (exp_close > k)
                            won = yes_won if pos["side"] == "YES" else (not yes_won)
                            to_close.append((pid, "SETTLED_VERIFIED_1M_CLOSE", 1.0 if won else 0.0, 0.0))
                            continue

        for pid, status, net_pay_ps, _ in to_close:
            pos = self.open_positions.pop(pid, None)
            if not pos:
                continue
            tier_pnls: Dict[str, float] = {}
            for t_name, tf in pos["tier_fills"].items():
                cost_total = float(tf["spent_usd"]) + float(tf["fee_usd"])
                payout_usd = float(tf["shares"]) * net_pay_ps
                tier_pnls[t_name] = round(payout_usd - cost_total, 2)

            won_t1000 = tier_pnls.get("T1000", 0.0) > 0
            pos.update({
                "status": status,
                "closed_ts": now,
                "closed_utc": datetime.now(timezone.utc).isoformat(),
                "net_payout_per_share": round(net_pay_ps, 4),
                "tier_pnls_usd": tier_pnls,
                "won": won_t1000,
            })
            self.closed_positions.append(pos)
            self._append_ledger({"event": "SHADOW_CLOSE", **pos})
            logger.info(
                f"[CLOSE:{pos['sleeve']}] {pos['title']} ({pos['side']}) -> {status} | "
                f"PnL T100=${tier_pnls.get('T100',0):+.2f} T1000=${tier_pnls.get('T1000',0):+.2f} T5000=${tier_pnls.get('T5000',0):+.2f}"
            )

    def write_state_files(self, opps: List[Dict[str, Any]]) -> None:
        global_bus = read_global_positions_shm()
        ext_positions = [
            p
            for d_name, d_rec in (global_bus.get("daemons") or {}).items()
            if d_name != "alpha124_shadow" and isinstance(d_rec, dict)
            for p in (d_rec.get("positions") or [])
        ]
        opps_sorted = rank_opportunities_capital_auction(
            opps, active_global_positions=list(self.open_positions.values()) + ext_positions
        )[:25]
        self.top_opportunities = opps_sorted
        publish_global_positions_shm("alpha124_shadow", self.open_positions.values())

        by_sleeve: Dict[str, Dict[str, Any]] = {}
        tier_totals = {"T100": 0.0, "T1000": 0.0, "T5000": 0.0}

        for sl in BANKROLL_TICKETS["T1000"].keys():
            is_d1_sl = str(sl).startswith("D1_")
            all_closed_sl = [p for p in self.closed_positions if p.get("sleeve") == sl]
            # Graduation stats must never count pre-fix inverted anti-box entries (net < $0.900): lucky wins there are not validation
            closed_sl = [
                p for p in all_closed_sl
                if not (is_d1_sl and float(p.get("entry_eff_px_t1000") or 1.0) < 0.900)
            ]
            excluded_anti = len(all_closed_sl) - len(closed_sl)
            open_sl = [p for p in self.open_positions.values() if p.get("sleeve") == sl]
            wins = sum(1 for p in closed_sl if p.get("won"))
            pnl_1k = sum(float(p.get("tier_pnls_usd", {}).get("T1000", 0.0)) for p in closed_sl)
            for t_k in tier_totals:
                tier_totals[t_k] = round(
                    tier_totals[t_k] + sum(float(p.get("tier_pnls_usd", {}).get(t_k, 0.0)) for p in closed_sl), 2
                )
            by_sleeve[sl] = {
                "open": len(open_sl),
                "closed": len(closed_sl),
                "wins": wins,
                "losses": len(closed_sl) - wins,
                "win_rate_pct": round(100.0 * wins / len(closed_sl), 2) if closed_sl else 0.0,
                "realized_pnl_t1000_usd": round(pnl_1k, 2),
                "excluded_anti_box": excluded_anti,
                "quarantined": is_shadow_sleeve_quarantined(sl),
            }

        state = {
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "started_at": self.started_at,
            "cycle_count": self.cycle_count,
            "calibration": {
                "weather_sigma_c": self.weather_sigma_c,
                "barrier_wick_mult": self.barrier_wick_mult,
            },
            "spots": self.spots,
            "markets_monitored": {
                "weather_city_events": len(self.weather_events),
                "barrier_hit_rungs": len(self.barrier_rungs),
                "multistrike_ladders": len(self.strike_ladders),
                "negrisk_bracket_ladders": len(self.negrisk_ladders),
                "daily_updown_markets": len(self.daily_updown_markets),
                "same_oracle_dominance_pairs": len(self.dominance_pairs),
                "dominance_4h_pairs": len(self.dominance_4h_pairs),
                "exact_twap_lock_candles": len(self.twap_candles),
                "s5m_sniper_candles": len(self.s5m_candles),
                "preopen_15m_candles": len(self.preopen_15m_candles),
            },
            "portfolio_realized_pnl_by_bankroll_usd": tier_totals,
            "by_sleeve": by_sleeve,
            "per_strategy": by_sleeve,
            "open_positions_count": len(self.open_positions),
            "pending_maker_orders_count": len(self.pending_maker_orders),
            "pending_preopen_straddles_count": len(self.pending_preopen_straddles),
            "pending_maker_orders": list(self.pending_maker_orders.values()),
            "open_positions": list(self.open_positions.values()),
            "recent_closed_positions": self.closed_positions[-30:],
        }

        tmp_s = STATE_FILE.with_suffix(".tmp")
        tmp_s.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp_s, STATE_FILE)

        # Mirror lightweight graduation summary into data/polymarket/alpha124_shadow_state.json for live harvester
        if STATE_FILE == (DATA_DIR / "alpha124_shadow_state.json") or LIVE_ALPHA124_STATE_MIRROR_FILE != (LIVE_POLYMARKET_DIR / "alpha124_shadow_state.json"):
            try:
                LIVE_ALPHA124_STATE_MIRROR_FILE.parent.mkdir(parents=True, exist_ok=True)
                tmp_m = LIVE_ALPHA124_STATE_MIRROR_FILE.with_suffix(".tmp")
                tmp_m.write_text(
                    json.dumps(
                        {
                            "updated_at_utc": state["updated_at_utc"],
                            "by_sleeve": by_sleeve,
                            "per_strategy": by_sleeve,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                os.replace(tmp_m, LIVE_ALPHA124_STATE_MIRROR_FILE)
            except Exception as exc:
                logger.debug(f"Graduation mirror write notice: {exc}")

        tmp_o = OPPS_FILE.with_suffix(".tmp")
        tmp_o.write_text(
            json.dumps({"updated_at_utc": state["updated_at_utc"], "top_opportunities": opps_sorted}, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp_o, OPPS_FILE)

        # Auto-refresh live day-by-day projections once every 60s
        now_p = time.time()
        if (now_p - float(getattr(self, "_last_proj_write_ts", 0.0))) >= 60.0:
            self._last_proj_write_ts = now_p
            try:
                from scripts.polymarket_daily_projections import write_live_projections_atomic
                write_live_projections_atomic(days=30)
            except Exception as exc:
                logger.debug(f"Live daily projections refresh notice: {exc}")

    async def write_state_files_async(self, opps: List[Dict[str, Any]]) -> None:
        """Offloads synchronous JSON serialization & atomic disk renames from the <250ms event loop (`H-07`)."""
        await asyncio.to_thread(self.write_state_files, opps)

    async def _run_bg_discovery(self) -> None:
        try:
            await self.discover_all_markets()
        except Exception as exc:
            logger.warning(f"Background discovery notice: {exc}")

    async def _run_bg_mid_crypto(self) -> None:
        try:
            mid_opps: List[Dict[str, Any]] = []
            await self.scan_multistrike_markets(mid_opps)
            await self.scan_daily_updown_locks(mid_opps)
            await self.scan_barrier_markets(mid_opps)
            self.cached_mid_opps = mid_opps
        except Exception as exc:
            logger.warning(f"Background mid-crypto scan notice: {exc}")

    async def _run_bg_weather(self) -> None:
        try:
            w_opps: List[Dict[str, Any]] = []
            await self.scan_weather_markets(w_opps)
            self.cached_weather_opps = w_opps
        except Exception as exc:
            logger.warning(f"Background weather scan notice: {exc}")

    async def run_forever(self) -> None:
        logger.info(
            "Starting Polymarket Alpha-124 Unified Shadow Daemon "
            "(W1/W3 + Asian METAR + B1/B2 + M3/N1 NegRisk + U1 Daily + D1/4h/QuietBook + S5M + P1 PreOpen + S2)..."
        )
        try:
            while True:
                t0 = time.time()
                self.cycle_count += 1
                await self.update_crypto_spots()

                if not self.weather_events or self.single_scan:
                    await self.discover_all_markets()
                elif (t0 - self.last_discovery_ts) >= 300.0 and (
                    self._bg_discovery_task is None or self._bg_discovery_task.done()
                ):
                    self.last_discovery_ts = t0
                    self._bg_discovery_task = asyncio.create_task(self._run_bg_discovery())

                # Reactive drain of any fresh Binance shock triggers before periodic scans
                fresh_shocks = self.poll_fresh_shock_triggers(now_ts=t0)
                if fresh_shocks:
                    shock_opps: List[Dict[str, Any]] = []
                    await self.handle_shock_triggers(fresh_shocks, shock_opps, now_ts=t0)
                    self.cached_shock_opps = shock_opps

                # Fast-loop scanners: D1 (15m/5m + 4h + QuietBook), S2 TWAP Lock, S5M Sniper, P1 Pre-Open Maker Straddle
                dom_opps: List[Dict[str, Any]] = []
                twap_opps: List[Dict[str, Any]] = []
                s5m_opps: List[Dict[str, Any]] = []
                p1_opps: List[Dict[str, Any]] = []
                await self.scan_same_oracle_dominance_boxes(dom_opps)
                await self.scan_exact_twap_locks(twap_opps)
                await self.scan_s5m_chainlink_sniper(s5m_opps)
                await self.scan_and_manage_preopen_maker_straddles(p1_opps)

                if self.single_scan:
                    mid_opps: List[Dict[str, Any]] = []
                    await self.scan_multistrike_markets(mid_opps)
                    await self.scan_daily_updown_locks(mid_opps)
                    await self.scan_barrier_markets(mid_opps)
                    self.cached_mid_opps = mid_opps

                    w_opps: List[Dict[str, Any]] = []
                    await self.scan_weather_markets(w_opps)
                    self.cached_weather_opps = w_opps
                else:
                    # Non-blocking background coroutines so S2 (3.0s) / D1 (3.5s) never stall
                    if (t0 - self.last_crypto_mid_scan_ts) >= 18.0 and (
                        self._bg_mid_task is None or self._bg_mid_task.done()
                    ):
                        self.last_crypto_mid_scan_ts = t0
                        self._bg_mid_task = asyncio.create_task(self._run_bg_mid_crypto())

                    if (t0 - self.last_weather_scan_ts) >= 90.0 and (
                        self._bg_weather_task is None or self._bg_weather_task.done()
                    ):
                        self.last_weather_scan_ts = t0
                        self._bg_weather_task = asyncio.create_task(self._run_bg_weather())

                opps = (
                    twap_opps
                    + dom_opps
                    + s5m_opps
                    + p1_opps
                    + self.cached_shock_opps
                    + self.cached_mid_opps
                    + self.cached_weather_opps
                )

                await self.manage_pending_maker_orders()
                await self.manage_open_positions()
                await self.write_state_files_async(opps)

                logger.info(
                    f"[Cycle {self.cycle_count}] BTC=${self.spots.get('BTC',0):,.1f} ETH=${self.spots.get('ETH',0):,.1f} | "
                    f"Monitored(W={len(self.weather_events)}, B={len(self.barrier_rungs)}, M={len(self.strike_ladders)}, "
                    f"NR={len(self.negrisk_ladders)}, U1={len(self.daily_updown_markets)}, D={len(self.dominance_pairs)}, "
                    f"D4h={len(self.dominance_4h_pairs)}, S5m={len(self.s5m_candles)}, P1={len(self.preopen_15m_candles)}, S2={len(self.twap_candles)}) | "
                    f"MakerPend={len(self.pending_maker_orders)} PreOpenPend={len(self.pending_preopen_straddles)} "
                    f"OpenPos={len(self.open_positions)} ClosedPos={len(self.closed_positions)} | TopOpps={len(self.top_opportunities)}"
                )

                if self.single_scan:
                    break
                now_end = time.time()
                rem_4h_end = (math.ceil(now_end / 14400.0) * 14400.0) - now_end
                if self.is_in_exact_twap_lock_window(now_end):
                    target_cadence = 3.0
                elif self.is_in_same_oracle_overlap_window(now_end):
                    target_cadence = 3.5
                elif 8.0 <= rem_4h_end <= 905.0 or self.pending_preopen_straddles:
                    target_cadence = 6.0
                else:
                    target_cadence = 12.0
                deadline = t0 + max(2.0, target_cadence)
                last_fast_d1_subscan = t0
                while True:
                    now_s = time.time()
                    if now_s >= deadline:
                        break
                    # Sub-second (0.50s / 2 Hz) D1 overlap box scan without full state-file rewrite churn
                    if self.is_in_same_oracle_overlap_window(now_s) and (now_s - last_fast_d1_subscan) >= 0.50:
                        last_fast_d1_subscan = now_s
                        d1_sub_opps: List[Dict[str, Any]] = []
                        await self.scan_same_oracle_dominance_boxes(d1_sub_opps, now_ts=now_s)
                        if d1_sub_opps:
                            dom_opps = d1_sub_opps
                    # Sample /dev/shm USD anchor at 1 Hz during the 65s TWAP integral window (0 REST calls)
                    rem_5m_s = (math.ceil(now_s / 300.0) * 300.0) - now_s
                    if rem_5m_s <= 65.0 and (now_s - self.last_usd_sample_ts) >= 1.0:
                        self.record_usd_spot_samples(now_s)
                    # Wake immediately (<250ms) if a live Binance shock arrives
                    shocks_w = self.poll_fresh_shock_triggers(now_ts=now_s)
                    if shocks_w:
                        s_opps: List[Dict[str, Any]] = []
                        await self.handle_shock_triggers(shocks_w, s_opps, now_ts=now_s)
                        if s_opps:
                            self.cached_shock_opps = s_opps
                        await self.write_state_files_async(
                            twap_opps
                            + dom_opps
                            + s5m_opps
                            + p1_opps
                            + self.cached_shock_opps
                            + self.cached_mid_opps
                            + self.cached_weather_opps
                        )
                    # Step down cadence immediately if we just entered the final-55s TWAP lock window
                    if target_cadence > 3.0 and self.is_in_exact_twap_lock_window(now_s):
                        break
                    await asyncio.sleep(min(0.25, max(0.05, deadline - now_s)))
        finally:
            for bg_t in (self._bg_discovery_task, self._bg_mid_task, self._bg_weather_task):
                if bg_t is not None and not bg_t.done():
                    bg_t.cancel()
                    try:
                        await bg_t
                    except BaseException:
                        pass
            if self.session and not self.session.closed:
                await self.session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket Alpha-124 Shadow Daemon")
    parser.add_argument("--single-scan", action="store_true", help="Run one full scan cycle and exit")
    args = parser.parse_args()
    if os.name != "nt":
        try:
            import uvloop
            uvloop.install()
        except Exception:
            pass
    daemon = Alpha124ShadowDaemon(single_scan=args.single_scan)
    asyncio.run(daemon.run_forever())


if __name__ == "__main__":
    main()
