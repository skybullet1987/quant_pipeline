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
    BINANCE_FAPI_URL,
    HIT_SERIES,
    BarrierRungSpec,
    detect_barrier_monotonicity_boxes,
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
    ZERO_FEE_PYTH_DAILY_SERIES,
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
from src.polymarket_research.orderflow_wfo_simulators import compute_d1_legging_drag_haircut
from src.polymarket_research.same_oracle_dominance_box import (
    DOMINANCE_ASSETS,
    DOMINANCE_SERIES_SLUGS,
    EMPIRICAL_BOX_ASSET_CAPS_USD,
    MIN_CORRIDOR_BPS_BY_ASSET,
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
try:
    from src.polymarket_research.polymarket_ws_streams import PolymarketChainlinkLiveStream
except ImportError:
    try:
        from polymarket_ws_streams import PolymarketChainlinkLiveStream  # type: ignore
    except ImportError:
        PolymarketChainlinkLiveStream = None  # type: ignore
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
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    NBA_SERIES_SLUGS,
    PYTH_ASSET_CONFIG,
    PYTH_CLOSE_SERIES,
    PYTH_HIT_SERIES,
    ZERO_FEE_NEGRISK_SERIES,
    NbaGameSpec,
    PythBarrierRungSpec,
    PythCloseRungSpec,
    ZeroFeeNegRiskSlateSpec,
    compute_effective_trading_hours,
    detect_nba_dominance_boxes,
    detect_pyth_calendar_inclusion_boxes,
    detect_pyth_close_vs_hit_boxes,
    evaluate_pyth_session_barrier_no_lock,
    evaluate_pyth_session_close_lock,
    fetch_yahoo_1m_intraday_sync,
    is_same_continuous_session,
    parse_nba_zero_fee_event,
    parse_pyth_close_event,
    parse_pyth_hit_event,
    parse_zero_fee_negrisk_slate,
    window_extremes_from_bars,
    _extract_market_fee_rate,
    _parse_clob_tokens,
    _parse_iso_ts,
)
from src.polymarket_research.macro_counting_ctf_engine import (
    ALL_FOMC_MASK,
    ALL_OIL_SENATE_MASK,
    COUNTING_SERIES_HANDLES,
    FOMC_PARLAY_SERIES,
    GAS_SERIES_SLUGS,
    HOURLY_BINANCE_SERIES,
    NY_TZ,
    OIL_SENATE_SLUGS,
    CountingSlateSpec,
    build_fomc_truth_table_legs,
    build_oil_senate_truth_table_legs,
    detect_counting_subwindow_boxes,
    detect_d2_12pm_binance_boxes,
    evaluate_counting_dead_no_locks,
    evaluate_locked_market_reward_carry,
    evaluate_pyth_catalyst_shock,
    fetch_aaa_national_gas_sync,
    fetch_xtracker_user_stats_sync,
    find_cross_event_bitmask_boxes,
    parse_counting_slate_event,
    parse_gas_daily_bracket,
    walk_equal_shares_overround_bids,
)

DATA_DIR = PROJECT_ROOT / "data" / "alpha124"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = DATA_DIR / "alpha124_shadow_state.json"
LEDGER_FILE = DATA_DIR / "alpha124_shadow_ledger.jsonl"
MARKET_TELEMETRY_FILE = DATA_DIR / "alpha124_market_telemetry.jsonl"
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
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BINANCE_URL = "https://api.binance.com"

try:
    import orjson as _orjson
except Exception:
    _orjson = None

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
    "B1_CONVEX_TAIL_YES",
    "S2_EXACT_TWAP_LOCK",
    "ZERO_FEE_MAKER_ANCHOR_BOX",
    "CTF_OVERROUND_MINT_SELL",
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
        "B3_BARRIER_MONO_BOX": 18.0,
        "M1_SVI_MAKER_SCALP": 15.0,
        "M2_STRIKE_CONVERGENCE": 15.0,
        "M3_LADDER_MONO_BOX": 20.0,
        "M4_SHOCK_STRIKE_CATCHUP": 15.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 20.0,
        "D1_4H_DOMINANCE_BOX": 20.0,
        "D1_QUIET_BOOK_BOX": 20.0,
        "D1_MAKER_ANCHOR_BOX": 18.0,
        "S5M_CHAINLINK_SNIPER": 15.0,
        "N1_NEGRISK_CROSS_BOX": 20.0,
        "P1_PREOPEN_MAKER_STRADDLE": 16.0,
        "U1_DAILY_UPDOWN_LOCK": 15.0,
        "C1_BINARY_COMPLETE_SET": 20.0,
        "S2_EXACT_TWAP_LOCK": 15.0,
        "CM_B3_PYTH_BARRIER_BOX": 20.0,
        "CM_B2_PYTH_SESSION_NO_LOCK": 15.0,
        "CM_U1_PYTH_CLOSE_LOCK": 15.0,
        "B4_TOUCHED_BARRIER_WICK_LOCK": 20.0,
        "SP1_NBA_ZERO_FEE_BOX": 20.0,
        "NR0_ZERO_FEE_SLATE_ARB": 15.0,
        "ZERO_FEE_MAKER_ANCHOR_BOX": 18.0,
        "TW1_COUNTING_TRUNCATION_AND_BOX": 18.0,
        "FED1_CENTRAL_BANK_LP_BOX": 20.0,
        "COND1_MACRO_PARTITION_BOX": 20.0,
        "CTF_OVERROUND_MINT_SELL": 20.0,
        "D2_12PM_BINANCE_BOX": 18.0,
        "GAS1_AAA_GASOLINE_LOCK": 15.0,
        "CM_SHOCK_PYTH_CATALYST": 15.0,
        "S4H_CHAINLINK_CONVERGENCE": 15.0,
        "MKR_REWARD_LOCKED_CARRY": 15.0,
    },
    "T1000": {
        "W1_SOLAR_PEAK_LOCK": 100.0,
        "W2_ENSEMBLE_VALUE": 50.0,
        "W2_MAKER_OVERROUND": 50.0,
        "W3_WEATHER_SLATE_ARB": 80.0,
        "B1_CONVEX_TAIL_YES": 25.0,
        "B2_BARRIER_NO_LOCK": 100.0,
        "B3_BARRIER_MONO_BOX": 120.0,
        "M1_SVI_MAKER_SCALP": 100.0,
        "M2_STRIKE_CONVERGENCE": 100.0,
        "M3_LADDER_MONO_BOX": 150.0,
        "M4_SHOCK_STRIKE_CATCHUP": 100.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 100.0,
        "D1_4H_DOMINANCE_BOX": 100.0,
        "D1_QUIET_BOOK_BOX": 100.0,
        "D1_MAKER_ANCHOR_BOX": 100.0,
        "S5M_CHAINLINK_SNIPER": 100.0,
        "N1_NEGRISK_CROSS_BOX": 150.0,
        "P1_PREOPEN_MAKER_STRADDLE": 96.0,
        "U1_DAILY_UPDOWN_LOCK": 100.0,
        "C1_BINARY_COMPLETE_SET": 150.0,
        "S2_EXACT_TWAP_LOCK": 100.0,
        "CM_B3_PYTH_BARRIER_BOX": 120.0,
        "CM_B2_PYTH_SESSION_NO_LOCK": 100.0,
        "CM_U1_PYTH_CLOSE_LOCK": 100.0,
        "B4_TOUCHED_BARRIER_WICK_LOCK": 120.0,
        "SP1_NBA_ZERO_FEE_BOX": 120.0,
        "NR0_ZERO_FEE_SLATE_ARB": 100.0,
        "ZERO_FEE_MAKER_ANCHOR_BOX": 100.0,
        "TW1_COUNTING_TRUNCATION_AND_BOX": 100.0,
        "FED1_CENTRAL_BANK_LP_BOX": 120.0,
        "COND1_MACRO_PARTITION_BOX": 120.0,
        "CTF_OVERROUND_MINT_SELL": 120.0,
        "D2_12PM_BINANCE_BOX": 100.0,
        "GAS1_AAA_GASOLINE_LOCK": 80.0,
        "CM_SHOCK_PYTH_CATALYST": 100.0,
        "S4H_CHAINLINK_CONVERGENCE": 100.0,
        "MKR_REWARD_LOCKED_CARRY": 100.0,
    },
    "T5000": {
        "W1_SOLAR_PEAK_LOCK": 350.0,
        "W2_ENSEMBLE_VALUE": 175.0,
        "W2_MAKER_OVERROUND": 175.0,
        "W3_WEATHER_SLATE_ARB": 250.0,
        "B1_CONVEX_TAIL_YES": 75.0,
        "B2_BARRIER_NO_LOCK": 350.0,
        "B3_BARRIER_MONO_BOX": 400.0,
        "M1_SVI_MAKER_SCALP": 350.0,
        "M2_STRIKE_CONVERGENCE": 350.0,
        "M3_LADDER_MONO_BOX": 500.0,
        "M4_SHOCK_STRIKE_CATCHUP": 350.0,
        "D1_SAME_ORACLE_DOMINANCE_BOX": 300.0,
        "D1_4H_DOMINANCE_BOX": 300.0,
        "D1_QUIET_BOOK_BOX": 300.0,
        "D1_MAKER_ANCHOR_BOX": 300.0,
        "S5M_CHAINLINK_SNIPER": 300.0,
        "N1_NEGRISK_CROSS_BOX": 500.0,
        "P1_PREOPEN_MAKER_STRADDLE": 288.0,
        "U1_DAILY_UPDOWN_LOCK": 350.0,
        "C1_BINARY_COMPLETE_SET": 500.0,
        "S2_EXACT_TWAP_LOCK": 300.0,
        "CM_B3_PYTH_BARRIER_BOX": 400.0,
        "CM_B2_PYTH_SESSION_NO_LOCK": 350.0,
        "CM_U1_PYTH_CLOSE_LOCK": 350.0,
        "B4_TOUCHED_BARRIER_WICK_LOCK": 400.0,
        "SP1_NBA_ZERO_FEE_BOX": 400.0,
        "NR0_ZERO_FEE_SLATE_ARB": 300.0,
        "ZERO_FEE_MAKER_ANCHOR_BOX": 350.0,
        "TW1_COUNTING_TRUNCATION_AND_BOX": 350.0,
        "FED1_CENTRAL_BANK_LP_BOX": 400.0,
        "COND1_MACRO_PARTITION_BOX": 400.0,
        "CTF_OVERROUND_MINT_SELL": 400.0,
        "D2_12PM_BINANCE_BOX": 300.0,
        "GAS1_AAA_GASOLINE_LOCK": 250.0,
        "CM_SHOCK_PYTH_CATALYST": 300.0,
        "S4H_CHAINLINK_CONVERGENCE": 300.0,
        "MKR_REWARD_LOCKED_CARRY": 300.0,
    },
}


def walk_l2_book_asks(
    asks_raw: List[Dict[str, Any]],
    notional_usd: float,
    fee_rate: float,
    max_slip_cents: float = 0.025,
    min_l1_usd: float = 20.0,
    min_fill_ratio: float = 0.98,
    max_ask_px: float = 0.98,
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
        if px > best_ask + max_slip_cents or px >= max_ask_px:
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
            a: collections.deque(maxlen=600) for a in DOMINANCE_ASSETS
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
        self.pyth_daily_markets: Dict[str, DailyUpDownSpec] = {}
        self.pyth_barrier_rungs: Dict[str, PythBarrierRungSpec] = {}
        self.pyth_close_ladders: Dict[str, List[PythCloseRungSpec]] = {}
        self.nba_games: Dict[str, NbaGameSpec] = {}
        self.negrisk_zero_slates: Dict[str, ZeroFeeNegRiskSlateSpec] = {}
        self.counting_slates: Dict[str, CountingSlateSpec] = {}
        self.fomc_truth_legs: List[Dict[str, Any]] = []
        self.oil_senate_truth_legs: List[Dict[str, Any]] = []
        self.gas_events_raw: Dict[str, List[Dict[str, Any]]] = {}
        self.hourly_12pm_markets: Dict[str, DailyUpDownSpec] = {}
        self.s4h_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.pending_zero_fee_maker_anchors: Dict[str, Dict[str, Any]] = {}
        self.prev_pyth_spots: Dict[str, float] = {}
        self.pyth_intraday_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.dominance_pairs: Dict[str, Tuple[TwapCandleMarketSpec, TwapCandleMarketSpec]] = {}
        self.dominance_4h_pairs: Dict[str, Tuple[TwapCandleMarketSpec, TwapCandleMarketSpec]] = {}
        self.twap_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.s5m_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.preopen_15m_candles: Dict[str, TwapCandleMarketSpec] = {}
        self.pending_preopen_straddles: Dict[str, Dict[str, Any]] = {}
        self.pending_maker_anchors: Dict[str, Dict[str, Any]] = {}
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
        self.last_tradfi_sports_scan_ts = 0.0
        self.last_dominance_discovery_ts = 0.0
        self.last_4h_discovery_ts = 0.0
        self.last_twap_discovery_ts = 0.0
        self.last_s5m_discovery_ts = 0.0
        self.last_preopen_discovery_ts = 0.0
        self.last_usd_sample_ts = 0.0
        self.cached_mid_opps: List[Dict[str, Any]] = []
        self.cached_weather_opps: List[Dict[str, Any]] = []
        self.cached_tradfi_sports_opps: List[Dict[str, Any]] = []
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
        self._bg_tradfi_task: Optional[asyncio.Task] = None
        self._ws_books: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._ws_raw_levels: Dict[str, Tuple[Dict[float, float], Dict[float, float]]] = {}
        self._ws_subscribed_tokens: set[str] = set()
        # Tokens whose `_ws_books` entry was seeded from a REST `/books` snapshot (not yet confirmed by a WS `book` event);
        # these are never forwarded to the live harvester as `cand["ws_books"]`.
        self._ws_rest_seeded: set[str] = set()
        # Priority-1 D1/S2 tokens (from `_desired_d1_ws_tokens`): only their WS updates trigger `_ws_d1_wakeup`.
        self._ws_d1_priority_tokens: set[str] = set()
        self._bg_chainlink_ws_task: Optional[asyncio.Task] = None
        self._chainlink_ws: Optional[Any] = (
            PolymarketChainlinkLiveStream(on_tick=self._on_chainlink_ws_tick)
            if (not self.single_scan and PolymarketChainlinkLiveStream is not None)
            else None
        )
        self._ws_d1_wakeup = asyncio.Event()
        self._bg_clob_ws_task: Optional[asyncio.Task] = None
        self._strike_fail_backoff_ts: Dict[str, float] = {}
        self._last_telem_ts_by_key: Dict[str, float] = {}
        self._last_telem_sig_by_key: Dict[str, Any] = {}

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

    def _record_market_telemetry(
        self,
        key: str,
        min_interval_sec: float,
        payload: Dict[str, Any],
        now_ts: Optional[float] = None,
        sig: Optional[Any] = None,
        unchanged_heartbeat_sec: float = 600.0,
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        last_ts = float(self._last_telem_ts_by_key.get(key) or 0.0)
        if (now - last_ts) < min_interval_sec:
            return
        if sig is not None and self._last_telem_sig_by_key.get(key) == sig and (now - last_ts) < unchanged_heartbeat_sec:
            return
        self._last_telem_ts_by_key[key] = now
        if sig is not None:
            self._last_telem_sig_by_key[key] = sig
        if len(self._last_telem_ts_by_key) > 5000:
            # Bound memory: drop telemetry throttle keys idle for > 2h (market keys are per-expiry and never recur)
            for k_old, ts_old in list(self._last_telem_ts_by_key.items()):
                if (now - float(ts_old or 0.0)) > 7200.0:
                    self._last_telem_ts_by_key.pop(k_old, None)
                    self._last_telem_sig_by_key.pop(k_old, None)
            for k_old in list(self._last_telem_sig_by_key.keys()):
                if k_old not in self._last_telem_ts_by_key:
                    self._last_telem_sig_by_key.pop(k_old, None)
        row = {
            "ts": round(now, 3),
            "utc": datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            **payload,
        }
        try:
            telem_path = (
                MARKET_TELEMETRY_FILE
                if MARKET_TELEMETRY_FILE.parent != DATA_DIR
                else (LEDGER_FILE.parent / "alpha124_market_telemetry.jsonl")
            )
            line_b = (json.dumps(row, separators=(",", ":")) + "\n").encode("utf-8")
            fd = os.open(str(telem_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o664)
            try:
                try:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX)
                except Exception:
                    pass
                os.write(fd, line_b)
            finally:
                try:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except Exception:
                    pass
                os.close(fd)
        except Exception:
            pass

    @staticmethod
    def _best_ask_sz(bk: Dict[str, Any]) -> Tuple[float, float]:
        best_p, best_s = 1.0, 0.0
        for a in (bk.get("asks") or []):
            try:
                p, s = float(a.get("price", 0)), float(a.get("size", 0))
                if p > 0 and s > 0 and p < best_p:
                    best_p, best_s = p, s
            except Exception:
                continue
        return best_p, best_s

    def _record_d1_corridor_telemetry(
        self,
        pair_type: str,
        m_outer: TwapCandleMarketSpec,
        m_inner: TwapCandleMarketSpec,
        dom_info: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        now_ts: float,
    ) -> None:
        leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
        ask_a, sz_a = self._best_ask_sz(bk_a)
        ask_b, sz_b = self._best_ask_sz(bk_b)
        if ask_a >= 1.0 or ask_b >= 1.0:
            return
        bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
        fa = float(leg_a["fee_rate"]) * ((ask_a * (1.0 - ask_a)) ** float(leg_a.get("fee_exponent", 1.0)))
        fb = float(leg_b["fee_rate"]) * ((ask_b * (1.0 - ask_b)) ** float(leg_b.get("fee_exponent", 1.0)))
        mkr_bid_a = round(min(bid_a + 0.01, ask_a - 0.01), 4) if bid_a > 0 and (ask_a - bid_a) >= 0.02 else None
        usd_h = self.usd_spot_hist.get(m_outer.asset)
        usd_px = round(float(usd_h[-1][1]), 6) if usd_h else None
        self._record_market_telemetry(
            key=f"D1_{pair_type}_{m_outer.asset}_{m_inner.market_id}",
            min_interval_sec=10.0,
            now_ts=now_ts,
            sig=(ask_a, ask_b, mkr_bid_a),
            unchanged_heartbeat_sec=60.0,
            payload={
                "type": "D1_CORRIDOR",
                "pair_type": pair_type,
                "asset": m_outer.asset,
                "regime": dom_info["regime"],
                "m_outer_id": m_outer.market_id,
                "m_inner_id": m_inner.market_id,
                "end_ts": int(m_inner.end_ts),
                "tte_sec": round(m_inner.end_ts - now_ts, 1),
                "k_low": dom_info["k_low"],
                "k_high": dom_info["k_high"],
                "corridor_bps": dom_info["corridor_bps"],
                "usd_spot": usd_px,
                "leg_a_ask": ask_a,
                "leg_b_ask": ask_b,
                "gross_box_l1": round(ask_a + ask_b, 4),
                "net_box_l1": round(ask_a + fa + ask_b + fb, 4),
                "maker_anchor_net_l1": round(mkr_bid_a + ask_b + fb, 4) if mkr_bid_a is not None else None,
                "l1_min_shares": round(min(sz_a, sz_b), 2),
            },
        )

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
        if is_shadow_sleeve_quarantined("ZERO_FEE_MAKER_ANCHOR_BOX"):
            self.pending_zero_fee_maker_anchors.clear()

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

    def _on_chainlink_ws_tick(self, asset: str, ts_sec: float, price_usd: float) -> None:
        if price_usd <= 0.0 or not math.isfinite(price_usd):
            return
        self.spots[asset] = price_usd
        self.usd_direct_flags[asset] = True
        dq = self.usd_spot_hist.get(asset)
        if dq is None:
            dq = collections.deque(maxlen=450)
            self.usd_spot_hist[asset] = dq
        if dq and abs(ts_sec - float(dq[-1][0])) < 0.05:
            dq[-1] = (ts_sec, price_usd)
        elif dq and ts_sec < float(dq[-1][0]):
            return  # out-of-order (older) tick: never append behind newer samples (keeps history time-monotonic)
        else:
            dq.append((ts_sec, price_usd))

    async def fetch_json(self, url: str, timeout: float = 5.0) -> Any:
        if not self.single_scan and self._ws_books and "/book?token_id=" in str(url):
            tok_q = str(url).split("token_id=", 1)[1].split("&", 1)[0].strip()
            ws_ent = self._ws_books.get(tok_q)
            if ws_ent is not None and (time.time() - ws_ent[0]) <= 1.5:
                bk_ws = ws_ent[1]
                if bk_ws.get("asks") or bk_ws.get("bids"):
                    return bk_ws
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

    def _rebuild_ws_book_dict(
        self,
        asset_id: str,
        bids_map: Dict[float, float],
        asks_map: Dict[float, float],
        now_ts: float,
    ) -> None:
        bids_sorted = [
            {"price": f"{px:.4f}", "size": f"{sz:.4f}"}
            for px, sz in sorted(bids_map.items(), key=lambda kv: -kv[0])[:20]
            if px > 0.0 and sz > 0.0
        ]
        asks_sorted = [
            {"price": f"{px:.4f}", "size": f"{sz:.4f}"}
            for px, sz in sorted(asks_map.items(), key=lambda kv: kv[0])[:20]
            if px > 0.0 and sz > 0.0
        ]
        self._ws_books[asset_id] = (
            now_ts,
            {"asset_id": asset_id, "bids": bids_sorted, "asks": asks_sorted},
        )

    def _apply_ws_book_snapshot(
        self,
        asset_id: str,
        bids_raw: List[Dict[str, Any]],
        asks_raw: List[Dict[str, Any]],
        now_ts: float,
        from_rest: bool = False,
    ) -> None:
        if not asset_id:
            return
        bids_map: Dict[float, float] = {}
        asks_map: Dict[float, float] = {}
        for row in bids_raw or ():
            try:
                px = round(float(row.get("price", 0.0)), 4)
                sz = float(row.get("size", 0.0))
                if px > 0.0 and sz > 0.0:
                    bids_map[px] = sz
            except Exception:
                continue
        for row in asks_raw or ():
            try:
                px = round(float(row.get("price", 0.0)), 4)
                sz = float(row.get("size", 0.0))
                if px > 0.0 and sz > 0.0:
                    asks_map[px] = sz
            except Exception:
                continue
        self._ws_raw_levels[asset_id] = (bids_map, asks_map)
        self._rebuild_ws_book_dict(asset_id, bids_map, asks_map, now_ts)
        if from_rest:
            self._ws_rest_seeded.add(asset_id)
        else:
            self._ws_rest_seeded.discard(asset_id)

    def _drop_ws_book(self, asset_id: str) -> None:
        self._ws_books.pop(asset_id, None)
        self._ws_raw_levels.pop(asset_id, None)
        self._ws_rest_seeded.discard(asset_id)

    def _apply_ws_price_changes(
        self,
        asset_id: str,
        changes: List[Dict[str, Any]],
        now_ts: float,
    ) -> bool:
        lvls = self._ws_raw_levels.get(asset_id)
        if lvls is None:
            return False
        bids_map, asks_map = lvls
        changed = False
        for pc in changes or ():
            try:
                px = round(float(pc.get("price", 0.0)), 4)
                sz = float(pc.get("size", 0.0))
                side = str(pc.get("side") or "").upper()
                if px <= 0.0:
                    continue
                target_map = bids_map if side == "BUY" else asks_map
                if sz <= 0.0:
                    if px in target_map:
                        target_map.pop(px, None)
                        changed = True
                else:
                    target_map[px] = sz
                    changed = True
            except Exception:
                continue
        # Integrity check: reconstructed book must not be crossed/locked and must agree with Polymarket's
        # own post-change `best_bid`/`best_ask` fields; otherwise drop the book so it is never used for live orders.
        best_bid_r = max(bids_map.keys()) if bids_map else 0.0
        best_ask_r = min(asks_map.keys()) if asks_map else 0.0
        book_bad = bool(bids_map and asks_map and best_bid_r >= best_ask_r)
        if not book_bad:
            pc_last_bb: Optional[float] = None
            pc_last_ba: Optional[float] = None
            for pc in changes or ():
                try:
                    if pc.get("best_bid") not in (None, ""):
                        pc_last_bb = float(pc.get("best_bid"))
                    if pc.get("best_ask") not in (None, ""):
                        pc_last_ba = float(pc.get("best_ask"))
                except Exception:
                    continue
            if pc_last_bb is not None and 0.0 < pc_last_bb < 1.0 and abs(pc_last_bb - best_bid_r) > 1e-6:
                book_bad = True
            if pc_last_ba is not None and 0.0 < pc_last_ba < 1.0 and abs(pc_last_ba - best_ask_r) > 1e-6:
                book_bad = True
        if book_bad:
            logger.debug(
                f"[WS BOOK INTEGRITY] {asset_id[:12]}: reconstructed bb={best_bid_r} ba={best_ask_r} "
                f"crossed or mismatched vs price_change best_bid/best_ask -> book dropped"
            )
            self._drop_ws_book(asset_id)
            return False
        if changed:
            self._rebuild_ws_book_dict(asset_id, bids_map, asks_map, now_ts)
        return changed

    def _desired_d1_ws_tokens(self, now_ts: float) -> List[str]:
        out: List[str] = []
        seen: set[str] = set()

        def _add_tok(tok: Any, max_cap: int = 220) -> bool:
            if len(out) >= max_cap:
                return False
            t_s = str(tok or "").strip()
            if t_s and t_s not in seen:
                seen.add(t_s)
                out.append(t_s)
            return len(out) < max_cap

        # Priority 1: Active D1 (15m/5m + 4h) and S2 TWAP Lock tokens
        for m_long, m_short in list(self.dominance_pairs.values()) + list(self.dominance_4h_pairs.values()):
            if float(m_short.end_ts) <= now_ts + 5.0:
                continue
            for tok in (m_long.up_token, m_long.down_token, m_short.up_token, m_short.down_token):
                _add_tok(tok)
        for sp_tw in list(self.twap_candles.values()):
            if float(sp_tw.end_ts) > now_ts + 5.0:
                _add_tok(sp_tw.up_token)
                _add_tok(sp_tw.down_token)
        self._ws_d1_priority_tokens = set(out)

        # Priority 2: itode=None zero-hold C1 Daily Complete Sets + near-ATM M3 Multi-Strike & N1 NegRisk Brackets + W3 Weather
        for sp_d in list(self.pyth_daily_markets.values()) + list(self.daily_updown_markets.values()):
            if float(sp_d.end_ts) > now_ts + 60.0:
                _add_tok(sp_d.up_token)
                _add_tok(sp_d.down_token)
        for rungs in list(self.strike_ladders.values()):
            if not rungs or float(rungs[0].end_ts) <= now_ts + 60.0:
                continue
            spot_r = float(self.spots.get(rungs[0].asset) or 0.0)
            ranked_r = sorted(rungs, key=lambda r: abs(float(r.strike) - spot_r)) if spot_r > 0.0 else list(rungs)
            for r in ranked_r[:6]:
                _add_tok(r.yes_token)
                _add_tok(r.no_token)
        for brs in list(self.negrisk_ladders.values()):
            if not brs or float(brs[0].end_ts) <= now_ts + 60.0:
                continue
            spot_n = float(self.spots.get(brs[0].asset) or 0.0)
            ranked_b = sorted(brs, key=lambda b: abs(0.5 * (float(b.k_low or spot_n) + float(b.k_high or spot_n)) - spot_n)) if spot_n > 0.0 else list(brs)
            for b in ranked_b[:6]:
                _add_tok(b.yes_token)
                _add_tok(b.no_token)
        for w_ev in list(self.weather_events.values()):
            for bkt in getattr(w_ev, "buckets", ()) or ():
                if not _add_tok(getattr(bkt, "yes_token", None)):
                    break
                _add_tok(getattr(bkt, "no_token", None))
        return out

    async def _run_clob_d1_ws_loop(self) -> None:
        """Maintains a live Polymarket CLOB Market WebSocket L2 book cache for active D1 pairs."""
        while not self.single_scan:
            now_0 = time.time()
            desired_0 = self._desired_d1_ws_tokens(now_0)
            if not desired_0:
                self._ws_subscribed_tokens.clear()
                await asyncio.sleep(1.0)
                continue
            try:
                sess = await self.get_session()
                async with sess.ws_connect(
                    CLOB_WS_URL,
                    heartbeat=15.0,
                    max_msg_size=4 * 1024 * 1024,
                    timeout=aiohttp.ClientWSTimeout(ws_close=5.0),
                ) as ws:
                    # Fresh connection: discard every book reconstructed on the previous socket (deltas may have been missed)
                    self._ws_books.clear()
                    self._ws_raw_levels.clear()
                    self._ws_rest_seeded.clear()
                    self._ws_subscribed_tokens = set(desired_0)
                    await ws.send_str(json.dumps({"assets_ids": desired_0, "type": "market"}))
                    last_sub_chk = time.time()
                    last_rx_ts = last_sub_chk
                    while not self.single_scan:
                        now_w = time.time()
                        if (now_w - last_sub_chk) >= 2.0:
                            last_sub_chk = now_w
                            cur_desired = set(self._desired_d1_ws_tokens(now_w))
                            for stale_tok in list(self._ws_books.keys()):
                                if stale_tok not in cur_desired:
                                    self._drop_ws_book(stale_tok)
                            if not cur_desired:
                                break
                            added = sorted(cur_desired - self._ws_subscribed_tokens)
                            if added:
                                await ws.send_str(json.dumps({"assets_ids": added, "operation": "subscribe"}))
                                self._ws_subscribed_tokens.update(added)
                            elif len(self._ws_subscribed_tokens) > len(cur_desired) + 28:
                                break
                        if (now_w - last_rx_ts) > 30.0:
                            break
                        try:
                            msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                        except asyncio.TimeoutError:
                            continue
                        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                            break
                        if msg.type not in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                            continue
                        raw_payload = msg.data
                        if not raw_payload or raw_payload in ("PONG", b"PONG"):
                            last_rx_ts = time.time()
                            continue
                        now_rx = time.time()
                        last_rx_ts = now_rx
                        data = _orjson.loads(raw_payload) if _orjson is not None else json.loads(raw_payload)
                        woke = False
                        d1_wake_toks = self._ws_d1_priority_tokens
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    aid = str(item.get("asset_id") or "")
                                    if aid in self._ws_subscribed_tokens:
                                        self._apply_ws_book_snapshot(aid, item.get("bids") or [], item.get("asks") or [], now_rx)
                                        woke = woke or (aid in d1_wake_toks)
                        elif isinstance(data, dict):
                            ev_t = data.get("event_type")
                            if ev_t == "book":
                                aid = str(data.get("asset_id") or "")
                                if aid in self._ws_subscribed_tokens:
                                    self._apply_ws_book_snapshot(aid, data.get("bids") or [], data.get("asks") or [], now_rx)
                                    woke = woke or (aid in d1_wake_toks)
                            elif ev_t == "price_change":
                                grouped: Dict[str, List[Dict[str, Any]]] = {}
                                for pc in data.get("price_changes") or ():
                                    aid = str(pc.get("asset_id") or "")
                                    if aid in self._ws_subscribed_tokens:
                                        grouped.setdefault(aid, []).append(pc)
                                for aid, pcs in grouped.items():
                                    if self._apply_ws_price_changes(aid, pcs, now_rx) and aid in d1_wake_toks:
                                        woke = True
                        # Only D1 overlap-window token updates wake the fast D1 sub-scan (throttled to <=8.3 Hz; eliminates idle spin)
                        if (
                            woke
                            and self.is_in_same_oracle_overlap_window(now_rx)
                            and (now_rx - getattr(self, "_last_ws_d1_wake_ts", 0.0)) >= 0.12
                        ):
                            self._last_ws_d1_wake_ts = now_rx
                            self._ws_d1_wakeup.set()
            except asyncio.CancelledError:
                raise
            except Exception as exc_ws:
                logger.debug(f"D1 CLOB WS reconnect notice: {exc_ws}")
                await asyncio.sleep(1.0)

    async def fetch_books_batch(self, token_ids: List[str], timeout: float = 3.0) -> Dict[str, Dict[str, Any]]:
        uniq = list(dict.fromkeys(str(t) for t in token_ids if t))
        if not uniq:
            return {}
        if "fetch_json" in self.__dict__:
            res_list = await asyncio.gather(*(self.fetch_json(f"{CLOB_URL}/book?token_id={t}", timeout=timeout) for t in uniq))
            return {t: bk for t, bk in zip(uniq, res_list) if isinstance(bk, dict)}
        out: Dict[str, Dict[str, Any]] = {}
        missing: List[str] = []
        now_b = time.time()
        use_ws = not self.single_scan
        for t in uniq:
            ws_entry = self._ws_books.get(t) if use_ws else None
            if (
                ws_entry is not None
                and (now_b - ws_entry[0]) <= 1.5
                and ws_entry[1].get("bids")
                and ws_entry[1].get("asks")
            ):
                out[t] = ws_entry[1]
            else:
                missing.append(t)
        if not missing:
            return out
        sess = await self.get_session()
        for idx in range(0, len(missing), 50):
            chunk = missing[idx : idx + 50]
            try:
                async with sess.post(
                    f"{CLOB_URL}/books",
                    json=[{"token_id": t} for t in chunk],
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status == 200:
                        raw_bytes = await resp.read()
                        rows = _orjson.loads(raw_bytes) if _orjson is not None else json.loads(raw_bytes)
                        if isinstance(rows, list):
                            now_seed = time.time()
                            for r in rows:
                                if isinstance(r, dict) and r.get("asset_id"):
                                    aid_r = str(r["asset_id"])
                                    out[aid_r] = r
                                    if use_ws and aid_r in self._ws_subscribed_tokens and aid_r not in self._ws_raw_levels:
                                        self._apply_ws_book_snapshot(aid_r, r.get("bids") or [], r.get("asks") or [], now_seed, from_rest=True)
                            continue
            except Exception:
                pass
            fb = await asyncio.gather(*(self.fetch_json(f"{CLOB_URL}/book?token_id={t}", timeout=timeout) for t in chunk))
            for t, bk in zip(chunk, fb):
                if isinstance(bk, dict):
                    out[t] = bk
        return out

    def record_usd_spot_samples(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        self.last_usd_sample_ts = now
        for asset in DOMINANCE_ASSETS:
            shm = read_shm_usd_anchor(asset, now, max_age_sec=2.5)
            usd_px = shm.get("usd_spot")
            src = str(shm.get("source") or "")
            if usd_px and float(usd_px) > 0:
                self.usd_spot_hist.setdefault(asset, collections.deque(maxlen=400)).append((now, float(usd_px)))
                self.usd_direct_flags[asset] = src in ("shm_chainlink_proxy", "shm_coinbase_usd")

    async def update_crypto_spots(self) -> None:
        now = time.time()
        syms_json = "%5B" + ",".join(f"%22{s}%22" for s in sorted(set(ASSET_BINANCE_SYMBOL.values()))) + "%5D"
        data = await self.fetch_json(f"{BINANCE_URL}/api/v3/ticker/price?symbols={syms_json}", timeout=3.5)
        if isinstance(data, list):
            sym_map = {v: k for k, v in ASSET_BINANCE_SYMBOL.items()}
            for item in data:
                sym = item.get("symbol")
                if sym in sym_map:
                    asset = sym_map[sym]
                    px = float(item["price"])
                    self.spots[asset] = px
                    self.spot_hist.setdefault(asset, collections.deque(maxlen=600)).append((now, px))
        fapi_hype = await self.fetch_json(f"{BINANCE_FAPI_URL}/fapi/v1/ticker/price?symbol=HYPEUSDT", timeout=2.5)
        if isinstance(fapi_hype, dict) and fapi_hype.get("price"):
            px_h = float(fapi_hype["price"])
            if px_h > 0:
                self.spots["HYPE"] = px_h
                self.spot_hist.setdefault("HYPE", collections.deque(maxlen=600)).append((now, px_h))
        self.record_usd_spot_samples(now)
        missing_usd_assets = [
            a
            for a in DOMINANCE_ASSETS
            if a != "HYPE"
            and (
                not self.usd_direct_flags.get(a, False)
                or not self.usd_spot_hist.get(a)
                or (now - float(self.usd_spot_hist[a][-1][0])) > 3.0
            )
        ]
        if missing_usd_assets:
            cb_rows = await asyncio.gather(
                *(
                    self.fetch_json(f"https://api.exchange.coinbase.com/products/{a}-USD/ticker", timeout=2.0)
                    for a in missing_usd_assets
                )
            )
            now_cb = time.time()
            for a, cb in zip(missing_usd_assets, cb_rows):
                if isinstance(cb, dict) and cb.get("price"):
                    try:
                        px_cb = float(cb["price"])
                        if px_cb > 0:
                            self.usd_spot_hist.setdefault(a, collections.deque(maxlen=400)).append((now_cb, px_cb))
                            self.usd_direct_flags[a] = True
                    except Exception:
                        pass

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
        now_w_disc = time.time()
        def _weather_still_live(sp_w: WeatherEventSpec) -> bool:
            try:
                return datetime.fromisoformat(sp_w.end_date_iso.replace("Z", "+00:00")).timestamp() > now_w_disc
            except Exception:
                return True

        def _parse_neg_risk_flag(v: Any) -> Optional[bool]:
            if isinstance(v, bool):
                return v
            if isinstance(v, str) and v.strip().lower() in ("true", "false"):
                return v.strip().lower() == "true"
            return None

        def _attach_weather_neg_risk(sp_w: WeatherEventSpec, ev_raw: Any) -> None:
            # Gamma `negRisk` (market-level overrides event-level) -> `bucket.neg_risk`; unknown stays None (blocks LIVE C1 emits)
            if not isinstance(ev_raw, dict):
                return
            ev_nr = _parse_neg_risk_flag(ev_raw.get("negRisk"))
            nr_by_id: Dict[str, Optional[bool]] = {}
            for mk in ev_raw.get("markets") or ():
                if not isinstance(mk, dict):
                    continue
                mk_nr = _parse_neg_risk_flag(mk.get("negRisk"))
                if mk_nr is None:
                    mk_nr = ev_nr
                for id_k in (mk.get("id"), mk.get("conditionId")):
                    if id_k not in (None, ""):
                        nr_by_id[str(id_k)] = mk_nr
            for bkt in sp_w.buckets:
                nr_v = nr_by_id.get(str(bkt.market_id))
                if nr_v is None:
                    nr_v = nr_by_id.get(str(bkt.condition_id))
                if nr_v is None and getattr(bkt, "neg_risk", None) is not None:
                    continue  # keep a value already parsed upstream (e.g. by `parse_weather_event`)
                try:
                    setattr(bkt, "neg_risk", nr_v)
                except Exception:
                    pass

        for offset in range(0, 600, 100):
            evts = await self.fetch_json(
                f"{GAMMA_URL}/events?closed=false&order=volume24hr&ascending=false&limit=100&offset={offset}",
                timeout=7.0,
            )
            if not isinstance(evts, list) or not evts:
                break
            for ev in evts:
                sp = parse_weather_event(ev)
                if sp is not None and _weather_still_live(sp):
                    _attach_weather_neg_risk(sp, ev)
                    weather_found[sp.event_id] = sp
        for w_slug in HIGH_VOLUME_WEATHER_SERIES:
            evts_w = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={w_slug}&closed=false&limit=3", timeout=5.0)
            if isinstance(evts_w, list):
                for ev in evts_w:
                    sp = parse_weather_event(ev, series_slug_hint=w_slug)
                    if sp is not None and _weather_still_live(sp):
                        _attach_weather_neg_risk(sp, ev)
                        weather_found[sp.event_id] = sp
        self.weather_events = weather_found

        # 2. Discover active Hit/Barrier series (#2)
        barrier_found: Dict[str, BarrierRungSpec] = {}
        for asset, h_grp, slug in HIT_SERIES:
            evts = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5", timeout=6.0)
            if isinstance(evts, list):
                for ev in evts:
                    for r in parse_hit_event(ev, asset, h_grp, slug):
                        if r.resolved_yes is None and r.end_ts > time.time() + 60:
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

        # 4. Discover active Daily Up/Down series (`U1_DAILY_UPDOWN_LOCK` + `0%`-fee Pyth FX/Metals `C1_BINARY_COMPLETE_SET`)
        updown_found: Dict[str, DailyUpDownSpec] = {}
        for asset, slug in DAILY_UPDOWN_SERIES:
            evts_ud = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3", timeout=5.0)
            if isinstance(evts_ud, list):
                for ev in evts_ud:
                    sp_ud = parse_daily_updown_event(ev, asset, slug)
                    if sp_ud is not None and sp_ud.end_ts > time.time() + 60:
                        updown_found[sp_ud.market_id] = sp_ud
        self.daily_updown_markets = updown_found

        pyth_found: Dict[str, DailyUpDownSpec] = {}
        for asset, slug in ZERO_FEE_PYTH_DAILY_SERIES:
            evts_py = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=2", timeout=5.0)
            if isinstance(evts_py, list):
                for ev in evts_py:
                    sp_py = parse_daily_updown_event(ev, asset, slug)
                    if sp_py is not None and sp_py.end_ts > time.time() + 60:
                        pyth_found[sp_py.market_id] = sp_py
        self.pyth_daily_markets = pyth_found

        # 5. Discover Zero-Fee Pyth Commodities/Metals/Equities Hit & Close Ladders, NBA Games, and Zero-Fee NegRisk Slates
        pyth_hit_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3", timeout=5.0) for _, _, slug in PYTH_HIT_SERIES)
        )
        pyth_hit_found: Dict[str, PythBarrierRungSpec] = {}
        now_disc = time.time()
        for (asset_p, h_grp_p, slug_p), evts_ph in zip(PYTH_HIT_SERIES, pyth_hit_res):
            if isinstance(evts_ph, list):
                for ev in evts_ph:
                    for rp in parse_pyth_hit_event(ev, asset_p, h_grp_p, slug_p):
                        if rp.end_ts > now_disc + 60:
                            pyth_hit_found[rp.market_id] = rp
        self.pyth_barrier_rungs = pyth_hit_found

        pyth_cl_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=3", timeout=5.0) for _, slug in PYTH_CLOSE_SERIES)
        )
        pyth_cl_found: Dict[str, List[PythCloseRungSpec]] = {}
        for (asset_c, slug_c), evts_pc in zip(PYTH_CLOSE_SERIES, pyth_cl_res):
            if isinstance(evts_pc, list):
                for ev in evts_pc:
                    rc_list = parse_pyth_close_event(ev, asset_c, slug_c)
                    if rc_list and rc_list[0].end_ts > now_disc + 60:
                        pyth_cl_found[f"{asset_c}_{ev.get('id')}"] = rc_list
        self.pyth_close_ladders = pyth_cl_found

        nba_found: Dict[str, NbaGameSpec] = {}
        for nba_slug in NBA_SERIES_SLUGS:
            evts_nba = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={nba_slug}&closed=false&limit=25", timeout=6.0)
            if isinstance(evts_nba, list):
                for ev in evts_nba:
                    sp_nba = parse_nba_zero_fee_event(ev, now_ts=now_disc)
                    if sp_nba is not None:
                        nba_found[sp_nba.event_id] = sp_nba
        self.nba_games = nba_found

        nr0_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=4", timeout=5.0) for slug in ZERO_FEE_NEGRISK_SERIES)
        )
        nr0_found: Dict[str, ZeroFeeNegRiskSlateSpec] = {}
        raw_by_series: Dict[str, List[Dict[str, Any]]] = {}
        for slug_n, evts_n0 in zip(ZERO_FEE_NEGRISK_SERIES, nr0_res):
            if isinstance(evts_n0, list):
                raw_by_series[slug_n] = evts_n0
                mixed_ok = slug_n in ("best-ai-company", "chinese-ai-1")
                for ev in evts_n0:
                    sp_n0 = parse_zero_fee_negrisk_slate(ev, slug_n, allow_mixed_fees=mixed_ok)
                    if sp_n0 is not None and sp_n0.end_ts > now_disc + 60:
                        nr0_found[sp_n0.event_id] = sp_n0
        self.negrisk_zero_slates = nr0_found

        # 6. Phase-2 Discovery: Counting Slates (`TW1`), FOMC LP (`FED1`), Oil-Senate (`COND1`), AAA Gas (`GAS1`), & 12PM Hourly (`D2`)
        cnt_found: Dict[str, CountingSlateSpec] = {}
        for c_slug, c_handle in COUNTING_SERIES_HANDLES:
            for ev_c in (raw_by_series.get(c_slug) or []):
                sp_c = parse_counting_slate_event(ev_c, c_slug, c_handle)
                if sp_c is not None and sp_c.window_end_ts > now_disc + 60:
                    cnt_found[sp_c.event_id] = sp_c
        self.counting_slates = cnt_found

        self.fomc_truth_legs = build_fomc_truth_table_legs(
            raw_by_series.get("fomc") or [],
            raw_by_series.get("fed-3-parlay") or [],
            sep_2026_realized_action=(os.getenv("PM_SEP_2026_FOMC_ACTION") or "").strip().upper() or None,
        )

        os_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?slug={sl_os}", timeout=5.0) for sl_os in OIL_SENATE_SLUGS),
            self.fetch_json(f"{GAMMA_URL}/events?series_slug=gas-price-hits-weekly&closed=false&limit=2", timeout=5.0),
        )
        os_by_slug: Dict[str, Dict[str, Any]] = {}
        for sl_os, res_os in zip(OIL_SENATE_SLUGS, os_res[:len(OIL_SENATE_SLUGS)]):
            if isinstance(res_os, list) and res_os:
                ev_o = res_os[0]
                os_by_slug[sl_os] = ev_o
                if "pending-oil" in sl_os:
                    sp_os_nr = parse_zero_fee_negrisk_slate(ev_o, sl_os)
                    if sp_os_nr is not None and sp_os_nr.end_ts > now_disc + 60:
                        self.negrisk_zero_slates[sp_os_nr.event_id] = sp_os_nr
        self.oil_senate_truth_legs = build_oil_senate_truth_table_legs(os_by_slug)
        self.gas_events_raw = {
            "us-gas-price-daily": raw_by_series.get("us-gas-price-daily") or [],
            "gas-price-hits-weekly": os_res[-1] if isinstance(os_res[-1], list) else [],
        }

        # Discover active 1h Binance candles that terminate at a Daily/Multi-Strike 12:00 PM ET timestamp (`D2_12PM_BINANCE_BOX`)
        target_12pm_ends = {int(round(sp.end_ts)) for sp in self.daily_updown_markets.values()} | {
            int(round(rgs[0].end_ts)) for rgs in self.strike_ladders.values() if rgs
        }
        hr_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?series_slug={h_slug}&closed=false&limit=6", timeout=4.5) for h_slug in HOURLY_BINANCE_SERIES.values())
        )
        h12_found: Dict[str, DailyUpDownSpec] = {}
        for (h_asset, h_slug), evts_h in zip(HOURLY_BINANCE_SERIES.items(), hr_res):
            if isinstance(evts_h, list):
                for ev_h in evts_h:
                    sp_h = parse_daily_updown_event(ev_h, h_asset, h_slug)
                    if sp_h is not None and sp_h.end_ts > now_disc + 30 and any(abs(sp_h.end_ts - te) <= 5.0 for te in target_12pm_ends):
                        h12_found[sp_h.market_id] = sp_h
        self.hourly_12pm_markets = h12_found

        self.last_discovery_ts = time.time()
        logger.info(
            f"Discovery complete: {len(self.weather_events)} Weather city-events, "
            f"{len(self.barrier_rungs)} Barrier Hit rungs, {len(self.strike_ladders)} Multi-Strike ladders, "
            f"{len(self.negrisk_ladders)} NegRisk ladders, {len(self.daily_updown_markets)} Crypto Daily Up/Down, "
            f"{len(self.pyth_daily_markets)} Zero-Fee Pyth FX/Metals Daily, "
            f"{len(self.pyth_barrier_rungs)} Pyth Zero-Fee Hit rungs, {len(self.pyth_close_ladders)} Pyth Close ladders, "
            f"{len(self.nba_games)} NBA Zero-Fee games, {len(self.negrisk_zero_slates)} NegRisk slates, "
            f"{len(self.counting_slates)} Counting slates, {len(self.fomc_truth_legs)//2} FOMC LP mkts, "
            f"{len(self.oil_senate_truth_legs)//2} Oil-Senate mkts, {len(self.hourly_12pm_markets)} 12PM 1h pairs."
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

            min_l1 = 15.0 if sleeve in (
                "S2_EXACT_TWAP_LOCK", "S5M_CHAINLINK_SNIPER", "S4H_CHAINLINK_CONVERGENCE",
                "B4_TOUCHED_BARRIER_WICK_LOCK", "CM_B2_PYTH_SESSION_NO_LOCK", "CM_U1_PYTH_CLOSE_LOCK",
                "TW1_COUNTING_TRUNCATION_AND_BOX", "GAS1_AAA_GASOLINE_LOCK", "CM_SHOCK_PYTH_CATALYST",
            ) else 20.0
            max_ask_cap = 0.990 if sleeve in ("B4_TOUCHED_BARRIER_WICK_LOCK", "TW1_COUNTING_TRUNCATION_AND_BOX", "GAS1_AAA_GASOLINE_LOCK") else 0.98
            # Validate T1000 reference fill first
            ref_ticket = BANKROLL_TICKETS["T1000"][sleeve]
            w_ref = walk_l2_book_asks(asks_raw, ref_ticket, fee_rate=fee_rate, min_l1_usd=min_l1, max_ask_px=max_ask_cap)
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
                "S4H_CHAINLINK_CONVERGENCE": 0.042,
                "U1_DAILY_UPDOWN_LOCK": 0.040,
                "S2_EXACT_TWAP_LOCK": 0.030,
                "B4_TOUCHED_BARRIER_WICK_LOCK": 0.012,
                "TW1_COUNTING_TRUNCATION_AND_BOX": 0.010,
                "GAS1_AAA_GASOLINE_LOCK": 0.015,
                "CM_SHOCK_PYTH_CATALYST": 0.045,
                "CM_B2_PYTH_SESSION_NO_LOCK": 0.035,
                "CM_U1_PYTH_CLOSE_LOCK": 0.030,
            }.get(sleeve, 0.035)
            if realized_edge < min_req_edge:
                return False

            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = walk_l2_book_asks(asks_raw, t_map[sleeve], fee_rate=fee_rate, min_l1_usd=min_l1, max_ask_px=max_ask_cap)
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
            elif sleeve == "CM_B2_PYTH_SESSION_NO_LOCK" and eff_tp is None:
                eff_tp = 0.985
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
        is_reward_carry = sleeve == "MKR_REWARD_LOCKED_CARRY"
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

            if is_reward_carry and extra.get("resting_bid_override"):
                resting_bid = round(min(float(extra["resting_bid_override"]), best_ask - 0.005), 4)
            else:
                # Post-only Maker bid: step +1c inside wide spread or join best_bid when 1c tight, strictly < best_ask
                cand_bid = best_bid + 0.01 if (best_ask - best_bid) >= 0.02 else best_bid
                resting_bid = round(min(cand_bid, best_ask - 0.01), 4)
            min_rb = 0.950 if is_reward_carry else (0.14 if is_weather_maker else 0.18)
            max_rb = 0.990 if is_reward_carry else (0.65 if is_weather_maker else 0.80)
            if not (min_rb <= resting_bid <= max_rb):
                return False
            maker_edge = p_model - resting_bid
            min_edge = 0.008 if is_reward_carry else (0.085 if is_weather_maker else 0.060)
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
            is_reward_carry = sleeve == "MKR_REWARD_LOCKED_CARRY"
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
            min_tte_cancel = 600.0 if is_reward_carry else (900.0 if ttl_ov is not None else (3600.0 if is_weather_maker else 7200.0))
            max_age_cancel = float(ttl_ov) if ttl_ov is not None else (7200.0 if is_reward_carry else (2700.0 if is_weather_maker else 1800.0))
            if rem_tte <= min_tte_cancel or age_s >= max_age_cancel:
                self.pending_maker_orders.pop(oid, None)
                _discard_maker_keys(m_ord)
                self._append_ledger({"event": "SHADOW_MAKER_CANCEL", "reason": "TTL_OR_EXPIRY", **m_ord})
                continue

            # 2. Evaluate adverse-selection triggers (`F-03` / `M-04`: verify CLOB didn't already sweep us during cancel RTT!)
            adverse_cancel_reason: Optional[str] = None
            p_fair_now = float(m_ord["p_model_at_post"])
            if is_reward_carry:
                pass
            elif is_weather_maker:
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
                if is_reward_carry:
                    eff_tp = None
                elif is_weather_maker:
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
            now_s = time.time()
            try:
                end_ts = datetime.fromisoformat(sp.end_date_iso.replace("Z", "+00:00")).timestamp()
            except Exception:
                end_ts = now_s + 86400.0
            if end_ts <= now_s:
                self.weather_events.pop(sp.event_id, None)
                continue
            # Adaptive METAR poll cadence (`Gemini #11`): 10s inside station release window, 300s outside!
            m_key = f"{sp.icao}_{sp.obs_date.isoformat()}"
            cached_m = self.metar_cache.get(m_key)
            metar_ttl = compute_adaptive_metar_poll_ttl(sp.icao, cached_m[1] if cached_m else None, now_utc)
            if cached_m is None or (now_s - cached_m[0]) >= metar_ttl:
                metars = await asyncio.to_thread(
                    fetch_metar_observations_sync, sp.icao, sp.obs_date, sp.tz_name
                )
                self.metar_cache[m_key] = (now_s, metars)
            else:
                metars = cached_m[1]

            # Official AviationWeather TAF TX/TN prior (`Gemini #11`, refreshed every 30m)
            cached_taf = self.taf_cache.get(m_key)
            if cached_taf is None or (now_s - cached_taf[0]) >= 1800.0:
                taf_ext = await asyncio.to_thread(
                    fetch_taf_extremes_sync, sp.icao, sp.obs_date, sp.tz_name
                )
                self.taf_cache[m_key] = (now_s, taf_ext)
            else:
                taf_ext = cached_taf[1]

            # Refresh 71-member Ensemble cache every 25 minutes per ICAO (throttled; never cache empty failures for 25m)
            cached_e = self.ensemble_cache.get(sp.icao)
            ens_ttl = 1500.0 if (cached_e and cached_e[1]) else 60.0
            if cached_e is None or (now_s - cached_e[0]) >= ens_ttl:
                async with self._open_meteo_sem:
                    ens_h = await asyncio.to_thread(fetch_live_ensemble_hourly_sync, sp.lat, sp.lon)
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
                    bid_w1, _ = extract_best_bid(bk.get("bids") or [])
                    self._record_market_telemetry(
                        key=f"W1_LOCK_{sp.event_id}_{b_lock.market_id}",
                        min_interval_sec=45.0,
                        now_ts=now_s,
                        sig=(w_chk.get("eff_px"), bid_w1, round(float(p_lock), 3)),
                        payload={
                            "type": "WEATHER_SOLAR_LOCK_SNAP",
                            "event_id": sp.event_id,
                            "city": sp.city,
                            "icao": sp.icao,
                            "metric": sp.metric,
                            "obs_date": sp.obs_date.isoformat(),
                            "bucket": b_lock.label,
                            "obs_count": res["obs_count"],
                            "running_ext_c": res["running_ext_c"],
                            "cushion_c": res["cooling_cushion_c"],
                            "p_lock": p_lock,
                            "ask_eff": w_chk.get("eff_px") if w_chk.get("filled") else None,
                            "bid": bid_w1 if bid_w1 > 0 else None,
                            "l1_usd": w_chk.get("l1_usd", 0.0),
                        },
                    )
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

            # 1B. Event-Level Weather Slate Arbitrage (`W3_WEATHER_SLATE_ARB` YES/NO) + 0%-Fee Weather `C1_BINARY_COMPLETE_SET`
            slate_key = f"W3_SLATE_{sp.event_id}"
            last_w3_chk = float(self._last_w3_slate_chk_ts.get(sp.event_id) or 0.0)
            w3_interval = 45.0 if (sp.series_slug in HIGH_VOLUME_WEATHER_SERIES or (end_ts - now_s) <= 21600.0) else 120.0
            if (
                slate_key not in self.entered_keys
                and slate_key not in self.inflight_keys
                and len(sp.buckets) >= 3
                and (self.single_scan or (now_s - last_w3_chk) >= w3_interval)
            ):
                self._last_w3_slate_chk_ts[sp.event_id] = now_s
                w_toks = [b_i.yes_token for b_i in sp.buckets] + [b_i.no_token for b_i in sp.buckets]
                w_bk_map = await self.fetch_books_batch(w_toks, timeout=3.0)
                bucket_book_map: Dict[str, Dict[str, Any]] = {}
                raw_bk_by_mkt: Dict[str, Dict[str, Any]] = {}
                for b_i in sp.buckets:
                    bk_i = w_bk_map.get(b_i.yes_token)
                    bk_n_i = w_bk_map.get(b_i.no_token)
                    rec_b: Dict[str, Any] = {}
                    if bk_i:
                        raw_bk_by_mkt[b_i.market_id] = bk_i
                        asks_i = sorted(
                            [(float(a["price"]), float(a["size"])) for a in (bk_i.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
                            key=lambda x: x[0],
                        )
                        if asks_i:
                            rec_b["ask_yes"] = asks_i[0][0]
                            rec_b["ask_yes_shares"] = asks_i[0][1]
                    if bk_n_i:
                        asks_n = sorted(
                            [(float(a["price"]), float(a["size"])) for a in (bk_n_i.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
                            key=lambda x: x[0],
                        )
                        if asks_n:
                            rec_b["ask_no"] = asks_n[0][0]
                            rec_b["ask_no_shares"] = asks_n[0][1]
                    if rec_b:
                        bucket_book_map[b_i.market_id] = rec_b
                    if bk_i and bk_n_i and float(getattr(b_i, "fee_rate", 0.0) or 0.0) == 0.0:
                        c1_w = scan_binary_complete_set_arb(
                            market_id=b_i.market_id,
                            condition_id=b_i.condition_id,
                            yes_token=b_i.yes_token,
                            no_token=b_i.no_token,
                            asks_yes_raw=bk_i.get("asks") or [],
                            asks_no_raw=bk_n_i.get("asks") or [],
                            target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],
                            fee_rate=0.0,
                            max_box_cost_net=0.995,
                        )
                        if c1_w.get("filled"):
                            opps_out.append({
                                "sleeve": "C1_BINARY_COMPLETE_SET",
                                "market": f"{sp.city} ({sp.icao}) Complete-Set [{b_i.label}]",
                                "ask_vwap": c1_w["box_cost_net"],
                                "p_model": 1.0,
                                "net_edge": c1_w["riskless_floor_per_pair"],
                                "l1_usd": c1_w["l1_usd"],
                                "close_ts": end_ts,
                            })
                            w_neg_risk = getattr(b_i, "neg_risk", None)
                            leg_w_y = {"token_id": b_i.yes_token, "opp_token_id": b_i.no_token, "condition_id": b_i.condition_id, "side": "YES", "label": "YES", "market_id": b_i.market_id, "fee_rate": 0.0, "strike": 100.0, "neg_risk": bool(w_neg_risk)}
                            leg_w_n = {"token_id": b_i.no_token, "opp_token_id": b_i.yes_token, "condition_id": b_i.condition_id, "side": "NO", "label": "NO", "market_id": b_i.market_id, "fee_rate": 0.0, "strike": 100.0, "neg_risk": bool(w_neg_risk)}
                            await self.open_shadow_two_leg_box(
                                sleeve="C1_BINARY_COMPLETE_SET",
                                dedupe_key=f"C1_W_{b_i.market_id}",
                                asset=f"{sp.city}_{sp.icao}",
                                title=f"{sp.city} YES+NO Complete Set [{b_i.label}]",
                                leg_a=leg_w_y,
                                leg_b=leg_w_n,
                                bk_a=bk_i,
                                bk_b=bk_n_i,
                                close_ts=end_ts,
                                max_box_cost_net=0.995,
                                extra={"is_complete_set": True, "market_id": b_i.market_id, "condition_id": b_i.condition_id},
                            )
                            # LIVE only when Gamma `negRisk` is known (wrong neg_risk -> wrong exchange contract / order signing)
                            if w_neg_risk is not None and (end_ts - now_s) <= 86400.0 and float(c1_w["box_cost_net"]) <= 0.990:
                                self.emit_live_two_leg_box_candidate(
                                    sleeve_source="C1_BINARY_COMPLETE_SET",
                                    box_type="COMPLETE_SET",
                                    asset=f"{sp.city}_{sp.icao}",
                                    dedupe_key=f"C1_W_{b_i.market_id}",
                                    leg_a=leg_w_y,
                                    leg_b=leg_w_n,
                                    bk_a=bk_i,
                                    bk_b=bk_n_i,
                                    close_ts=float(end_ts),
                                    now_ts=now_s,
                                )
                slate_ev = evaluate_weather_event_slate(
                    sp, probs, bucket_book_map, target_budget_usd=BANKROLL_TICKETS["T1000"]["W3_WEATHER_SLATE_ARB"]
                )
                full_arb = slate_ev.get("full_slate_arb")
                if len(bucket_book_map) == len(sp.buckets):
                    has_all_y = all(bucket_book_map[b.market_id].get("ask_yes", 0) > 0 for b in sp.buckets)
                    has_all_n = all(bucket_book_map[b.market_id].get("ask_no", 0) > 0 for b in sp.buckets)
                    sum_y_l1 = round(sum(float(bucket_book_map[b.market_id]["ask_yes"]) for b in sp.buckets), 4) if has_all_y else None
                    sum_n_l1 = round(sum(float(bucket_book_map[b.market_id]["ask_no"]) for b in sp.buckets), 4) if has_all_n else None
                    top_idx = max(range(len(sp.buckets)), key=lambda idx_b: float(probs[idx_b])) if probs else 0
                    top_bkt = sp.buckets[top_idx] if sp.buckets else None
                    top_ask_y = float(bucket_book_map[top_bkt.market_id].get("ask_yes") or 0.0) if top_bkt else 0.0
                    self._record_market_telemetry(
                        key=f"W_SLATE_{sp.event_id}",
                        min_interval_sec=45.0 if (end_ts - now_s) <= 7200.0 else 90.0,
                        now_ts=now_s,
                        sig=(sum_y_l1, sum_n_l1, res["running_ext_c"], round(top_ask_y, 3), (full_arb or {}).get("mode")),
                        payload={
                            "type": "WEATHER_SLATE",
                            "event_id": sp.event_id,
                            "city": sp.city,
                            "icao": sp.icao,
                            "metric": sp.metric,
                            "obs_date": sp.obs_date.isoformat(),
                            "n_buckets": len(sp.buckets),
                            "tte_sec": round(end_ts - now_s, 0),
                            "obs_count": res["obs_count"],
                            "latest_c": res["latest_temp_c"],
                            "running_ext_c": res["running_ext_c"],
                            "ens_iqr_c": res["peak_iqr_c"],
                            "solar_lock": res["is_solar_lock"],
                            "top_bucket": top_bkt.label if top_bkt else None,
                            "top_p": round(float(probs[top_idx]), 4) if probs else None,
                            "top_ask_yes": round(top_ask_y, 4) if top_ask_y > 0 else None,
                            "sum_yes_l1": sum_y_l1,
                            "sum_no_l1": sum_n_l1,
                            "no_payout": len(sp.buckets) - 1,
                            "arb_mode": (full_arb or {}).get("mode"),
                        },
                    )
                if full_arb:
                    gp_w = float(full_arb.get("guaranteed_payout_per_set") or 1.0)
                    opps_out.append({
                        "sleeve": "W3_WEATHER_SLATE_ARB",
                        "market": f"{sp.city} ({sp.icao}) {sp.obs_date} Full-Slate ({len(sp.buckets)} buckets, {full_arb.get('side','ALL_BUCKETS_YES')})",
                        "ask_vwap": round(float(full_arb["sum_asks"]) / gp_w, 4),
                        "p_model": 1.0,
                        "net_edge": round(float(full_arb["guaranteed_edge_per_set"]) / gp_w, 4),
                        "l1_usd": full_arb["total_cost_usd"],
                    })
                    await self.open_shadow_weather_slate(sp, full_arb, end_ts)
                if all(b.market_id in raw_bk_by_mkt for b in sp.buckets):
                    await self.execute_ctf_overround_mint_sell(
                        dedupe_key=f"CTF_OVR_W_{sp.event_id}",
                        asset=f"{sp.city}_{sp.icao}",
                        title=f"{sp.city} {sp.obs_date} Weather NegRisk Overround Mint-Sell",
                        legs_bids_spec=[
                            {
                                "bids": raw_bk_by_mkt[b.market_id].get("bids") or [],
                                "fee_rate": float(getattr(b, "fee_rate", 0.0) or 0.0),
                                "fee_exponent": 1.0,
                            }
                            for b in sp.buckets
                        ],
                        close_ts=end_ts,
                        min_net_proceeds_per_set=1.004,
                        opps_out=opps_out,
                        extra={"overround_kind": "WEATHER_NEGRISK", "event_id": sp.event_id},
                    )
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

            ext_by_start: Dict[int, Optional[Tuple[float, float, float]]] = {}
            ev_seed = self.barrier_ext_cache.get(ev_id)
            for st_min in sorted({int(r.start_ts // 60) for r in rungs}):
                ck = f"{r0.asset}_{st_min}"
                ext_cached = self.barrier_ext_cache.get(ck) or ev_seed
                if ext_cached is None or (now - ext_cached[0]) >= 90.0:
                    ext_val = await asyncio.to_thread(
                        fetch_binance_window_extremes_sync, r0.asset, float(st_min * 60), now, "1m"
                    )
                    if ext_val:
                        self.barrier_ext_cache[ck] = (now, ext_val)
                    ext_by_start[st_min] = ext_val
                else:
                    ext_by_start[st_min] = ext_cached[1]

            # B4_TOUCHED_BARRIER_WICK_LOCK: sweep lingering YES asks on rungs ALREADY deterministically
            # breached AFTER that specific rung's creation (`r.start_ts`) AND confirmed by live book (`bid>=0.78`, `eff_px in [0.85, 0.984]`)!
            touched_rungs: List[Tuple[BarrierRungSpec, float, float]] = []
            for r in rungs:
                if f"B4_{r.market_id}" in self.entered_keys:
                    continue
                ext_r = ext_by_start.get(int(r.start_ts // 60))
                if ext_r is None:
                    continue
                fh_r, fl_r = float(ext_r[0]), float(ext_r[1])
                if (r.direction == "UP" and fh_r >= r.strike * 1.0005) or (r.direction == "DOWN" and fl_r <= r.strike * 0.9995):
                    touched_rungs.append((r, fh_r, fl_r))
            if touched_rungs:
                b4_bks = await self.fetch_books_batch([rt[0].yes_token for rt in touched_rungs], timeout=2.5)
                for rb4, fin_h, fin_l in touched_rungs:
                    bk_b4 = b4_bks.get(rb4.yes_token)
                    if not bk_b4:
                        continue
                    bid_b4, _ = extract_best_bid(bk_b4.get("bids") or [])
                    w_b4 = walk_l2_book_asks(bk_b4.get("asks") or [], 100.0, fee_rate=rb4.fee_rate, min_l1_usd=15.0, max_ask_px=0.990)
                    if w_b4.get("filled") and bid_b4 >= 0.78 and 0.85 <= float(w_b4["eff_px"]) <= 0.984:
                        opps_out.append({
                            "sleeve": "B4_TOUCHED_BARRIER_WICK_LOCK",
                            "market": f"{rb4.asset} Breached 1m Wick Lock: {rb4.question}",
                            "ask_vwap": w_b4["eff_px"],
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_b4["eff_px"]), 4),
                            "l1_usd": w_b4["l1_usd"],
                        })
                        await self.open_shadow_position(
                            sleeve="B4_TOUCHED_BARRIER_WICK_LOCK",
                            dedupe_key=f"B4_{rb4.market_id}",
                            asset_or_city=rb4.asset,
                            title=rb4.question,
                            side_label="YES",
                            token_id=rb4.yes_token,
                            fee_rate=rb4.fee_rate,
                            p_model=1.0,
                            close_ts=rb4.end_ts,
                            extra={"market_id": rb4.market_id, "condition_id": rb4.condition_id, "strike": rb4.strike, "direction": rb4.direction, "fin_high": fin_h, "fin_low": fin_l},
                            prefetched_book=bk_b4,
                        )

            # Only poll CLOB books for rungs within sensible distance of spot (|ln(K/S)| <= 0.14) using per-rung window extremes
            near_rungs: List[BarrierRungSpec] = []
            for r in rungs:
                if abs(math.log(r.strike / spot)) > 0.14:
                    continue
                ext_r = ext_by_start.get(int(r.start_ts // 60))
                mh_r = max(spot, ext_r[0]) if ext_r else spot
                ml_r = min(spot, ext_r[1]) if ext_r else spot
                if (r.direction == "UP" and mh_r >= r.strike) or (r.direction == "DOWN" and ml_r <= r.strike):
                    continue
                near_rungs.append(r)
            ev_tte = r0.end_ts - now
            b_bk_map = (
                await self.fetch_books_batch(
                    [r.yes_token for r in near_rungs] + [r.no_token for r in near_rungs],
                    timeout=3.0,
                )
                if near_rungs and ev_tte <= 3 * 86400
                else {}
            )
            barrier_quote_rows: List[Dict[str, Any]] = []
            for r in near_rungs:
                tte = r.end_ts - now
                iv_w, iv_src = get_wing_implied_vol(r.asset, spot, r.strike, tte)
                p_touch = first_passage_touch_prob(
                    spot, r.strike, tte, iv_w, r.direction, wick_vol_multiplier=self.barrier_wick_mult
                )
                bk_y_pref = b_bk_map.get(r.yes_token)
                bk_n_pref = b_bk_map.get(r.no_token)
                if bk_y_pref and bk_n_pref and tte <= 3 * 86400:
                    w_qy = walk_l2_book_asks(bk_y_pref.get("asks") or [], 40.0, fee_rate=r.fee_rate, min_l1_usd=8.0)
                    w_qn = walk_l2_book_asks(bk_n_pref.get("asks") or [], 40.0, fee_rate=r.fee_rate, min_l1_usd=8.0)
                    barrier_quote_rows.append({
                        "strike": r.strike,
                        "direction": r.direction,
                        "market_id": r.market_id,
                        "condition_id": r.condition_id,
                        "yes_token": r.yes_token,
                        "no_token": r.no_token,
                        "fee_rate": r.fee_rate,
                        "ask_yes": w_qy.get("vwap") if w_qy.get("filled") else None,
                        "ask_no": w_qn.get("vwap") if w_qn.get("filled") else None,
                        "bk_yes": bk_y_pref,
                        "bk_no": bk_n_pref,
                        "start_ts": r.start_ts,
                        "end_ts": r.end_ts,
                    })

                # Evaluate B1_CONVEX_TAIL_YES (`0.04 <= p_touch <= 0.45`, `TTE >= 2h`)
                if 7200 <= tte <= 10 * 86400 and 0.07 <= p_touch <= 0.48:
                    bk_y = bk_y_pref or await self.fetch_json(f"{CLOB_URL}/book?token_id={r.yes_token}", timeout=3.0)
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
                    bk_n = bk_n_pref or await self.fetch_json(f"{CLOB_URL}/book?token_id={r.no_token}", timeout=3.0)
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

            if len(barrier_quote_rows) >= 2:
                b3_diag = detect_barrier_monotonicity_boxes(barrier_quote_rows, fee_rate=CRYPTO_FEE_RATE, max_box_cost_net=1.20)
                if b3_diag:
                    bd0 = b3_diag[0]
                    self._record_market_telemetry(
                        key=f"B3_DIAG_{ev_id}",
                        min_interval_sec=60.0,
                        now_ts=now,
                        sig=(bd0["direction"], bd0["low_strike"], bd0["high_strike"], bd0["box_cost_gross"], bd0["box_cost_net"]),
                        payload={
                            "type": "BARRIER_MONO_BEST",
                            "asset": r0.asset,
                            "event_id": ev_id,
                            "spot": spot,
                            "direction": bd0["direction"],
                            "low_strike": bd0["low_strike"],
                            "high_strike": bd0["high_strike"],
                            "gross_box_l1": bd0["box_cost_gross"],
                            "net_box_l1": bd0["box_cost_net"],
                        },
                    )
                b3_arbs = [b for b in b3_diag if float(b["box_cost_net"]) <= 0.995]
                by_yes_t = {str(q["yes_token"]): q for q in barrier_quote_rows}
                by_no_t = {str(q["no_token"]): q for q in barrier_quote_rows}
                for ba in b3_arbs:
                    qy = by_yes_t.get(ba["yes_token"])
                    qn = by_no_t.get(ba["no_token"])
                    if not qy or not qn:
                        continue
                    w_b3 = walk_equal_shares_dominance_box(
                        qy["bk_yes"].get("asks") or [],
                        qn["bk_no"].get("asks") or [],
                        target_budget_usd=BANKROLL_TICKETS["T1000"]["B3_BARRIER_MONO_BOX"],
                        fee_rate_a=float(qy["fee_rate"]),
                        fee_rate_b=float(qn["fee_rate"]),
                        max_box_cost_net=0.995,
                        min_shares=6,
                        min_box_notional_usd=5.5,
                    )
                    if w_b3.get("filled"):
                        opps_out.append({
                            "sleeve": "B3_BARRIER_MONO_BOX",
                            "market": f"{r0.asset} Barrier Box {ba['label']}",
                            "ask_vwap": round(float(w_b3["box_cost_net"]), 4),
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_b3["box_cost_net"]), 4),
                            "l1_usd": w_b3["l1_usd"],
                            "close_ts": qy["end_ts"],
                        })
                        leg_a_b3 = {
                            "token_id": ba["yes_token"], "opp_token_id": ba["yes_opp_token"],
                            "condition_id": ba["leg_yes_condition_id"], "side": "YES", "label": f"YES_{ba['direction']}",
                            "market_id": ba["leg_yes_market_id"], "fee_rate": float(qy["fee_rate"]),
                            "strike": float(ba["low_strike"] if ba["direction"] == "UP" else ba["high_strike"]),
                        }
                        leg_b_b3 = {
                            "token_id": ba["no_token"], "opp_token_id": ba["no_opp_token"],
                            "condition_id": ba["leg_no_condition_id"], "side": "NO", "label": f"NO_{ba['direction']}",
                            "market_id": ba["leg_no_market_id"], "fee_rate": float(qn["fee_rate"]),
                            "strike": float(ba["high_strike"] if ba["direction"] == "UP" else ba["low_strike"]),
                        }
                        await self.open_shadow_two_leg_box(
                            sleeve="B3_BARRIER_MONO_BOX",
                            dedupe_key=f"B3_{r0.asset}_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",
                            asset=r0.asset,
                            title=f"{r0.asset} Barrier Box {ba['label']}",
                            leg_a=leg_a_b3,
                            leg_b=leg_b_b3,
                            bk_a=qy["bk_yes"],
                            bk_b=qn["bk_no"],
                            close_ts=float(qy["end_ts"]),
                            max_box_cost_net=0.995,
                            extra={
                                "is_barrier_mono_box": True,
                                "direction": ba["direction"],
                                "low_strike": ba["low_strike"],
                                "high_strike": ba["high_strike"],
                            },
                        )
                        if (float(qy["end_ts"]) - now) <= 86400.0 and float(w_b3["box_cost_net"]) <= 0.985:
                            self.emit_live_two_leg_box_candidate(
                                sleeve_source="B3_BARRIER_MONO_BOX",
                                box_type="BARRIER_MONO",
                                asset=r0.asset,
                                dedupe_key=f"B3_{r0.asset}_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}",
                                leg_a=leg_a_b3,
                                leg_b=leg_b_b3,
                                bk_a=qy["bk_yes"],
                                bk_b=qn["bk_no"],
                                close_ts=float(qy["end_ts"]),
                                now_ts=now,
                                k_low=float(ba["low_strike"]),
                                k_high=float(ba["high_strike"]),
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
                    leg_a_c1 = {"token_id": sr.yes_token, "opp_token_id": sr.no_token, "condition_id": sr.condition_id, "side": "YES", "label": "YES", "market_id": sr.market_id, "fee_rate": CRYPTO_FEE_RATE, "strike": float(sr.strike)}
                    leg_b_c1 = {"token_id": sr.no_token, "opp_token_id": sr.yes_token, "condition_id": sr.condition_id, "side": "NO", "label": "NO", "market_id": sr.market_id, "fee_rate": CRYPTO_FEE_RATE, "strike": float(sr.strike)}
                    await self.open_shadow_two_leg_box(
                        sleeve="C1_BINARY_COMPLETE_SET",
                        dedupe_key=f"C1_{sr.market_id}",
                        asset=asset,
                        title=f"{asset} YES+NO Complete Set: {sr.question}",
                        leg_a=leg_a_c1,
                        leg_b=leg_b_c1,
                        bk_a=bk_y,
                        bk_b=bk_n,
                        close_ts=sr.end_ts,
                        max_box_cost_net=0.994,
                        extra={"is_complete_set": True, "market_id": sr.market_id, "condition_id": sr.condition_id},
                    )
                    if (sr.end_ts - now) <= 86400.0 and float(c1_chk["box_cost_net"]) <= 0.985:
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="C1_BINARY_COMPLETE_SET",
                            box_type="COMPLETE_SET",
                            asset=asset,
                            dedupe_key=f"C1_{sr.market_id}",
                            leg_a=leg_a_c1,
                            leg_b=leg_b_c1,
                            bk_a=bk_y,
                            bk_b=bk_n,
                            close_ts=float(sr.end_ts),
                            now_ts=now,
                            k_low=float(sr.strike),
                            k_high=float(sr.strike),
                        )

                w_y = walk_l2_book_asks(bk_y.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)
                w_n = walk_l2_book_asks(bk_n.get("asks") or [], 100.0, fee_rate=CRYPTO_FEE_RATE)

                ladder_quotes.append({
                    "strike": sr.strike,
                    "is_downward": sr.is_downward,
                    "market_id": sr.market_id,
                    "condition_id": sr.condition_id,
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
            if len(ladder_quotes) >= 2:
                sq_l = sorted([q for q in ladder_quotes if not q.get("is_downward")], key=lambda x: x["strike"])
                best_m3_net: Optional[Tuple[float, float, float, float]] = None
                for i_l in range(len(sq_l) - 1):
                    ya_l, nh_l = float(sq_l[i_l].get("ask_yes") or 1.0), float(sq_l[i_l + 1].get("ask_no") or 1.0)
                    if 0 < ya_l < 1.0 and 0 < nh_l < 1.0:
                        gn_l = ya_l + nh_l + CRYPTO_FEE_RATE * (ya_l * (1.0 - ya_l) + nh_l * (1.0 - nh_l))
                        if best_m3_net is None or gn_l < best_m3_net[0]:
                            best_m3_net = (round(gn_l, 4), round(ya_l + nh_l, 4), float(sq_l[i_l]["strike"]), float(sq_l[i_l + 1]["strike"]))
                if best_m3_net is not None:
                    self._record_market_telemetry(
                        key=f"M3_DIAG_{ladder_key}",
                        min_interval_sec=60.0,
                        now_ts=now,
                        sig=best_m3_net,
                        payload={
                            "type": "LADDER_MONO_BEST",
                            "asset": asset,
                            "ladder_key": ladder_key,
                            "spot": spot,
                            "tte_sec": round(tte, 0),
                            "low_strike": best_m3_net[2],
                            "high_strike": best_m3_net[3],
                            "gross_box_l1": best_m3_net[1],
                            "net_box_l1": best_m3_net[0],
                        },
                    )
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
                    leg_a_m3 = {
                        "token_id": ma["yes_token_low"], "opp_token_id": str(q_lo["no_token"]),
                        "condition_id": str(q_lo.get("condition_id") or ""), "side": "YES", "label": f"YES>{ma['low_strike']}",
                        "market_id": ma["low_market_id"], "fee_rate": CRYPTO_FEE_RATE, "strike": float(ma["low_strike"]),
                    }
                    leg_b_m3 = {
                        "token_id": ma["no_token_high"], "opp_token_id": str(q_hi["yes_token"]),
                        "condition_id": str(q_hi.get("condition_id") or ""), "side": "NO", "label": f"NO>{ma['high_strike']}",
                        "market_id": ma["high_market_id"], "fee_rate": CRYPTO_FEE_RATE, "strike": float(ma["high_strike"]),
                    }
                    await self.open_shadow_two_leg_box(
                        sleeve="M3_LADDER_MONO_BOX",
                        dedupe_key=f"M3_{asset}_{ma['low_market_id']}_{ma['high_market_id']}",
                        asset=asset,
                        title=f"{asset} Ladder Box YES>{ma['low_strike']} + NO>{ma['high_strike']}",
                        leg_a=leg_a_m3,
                        leg_b=leg_b_m3,
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
                    if (float(q_lo["end_ts"]) - now) <= 86400.0 and float(w_m3["box_cost_net"]) <= 0.985:
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="M3_LADDER_MONO_BOX",
                            box_type="LADDER_MONO",
                            asset=asset,
                            dedupe_key=f"M3_{asset}_{ma['low_market_id']}_{ma['high_market_id']}",
                            leg_a=leg_a_m3,
                            leg_b=leg_b_m3,
                            bk_a=q_lo["bk_yes"],
                            bk_b=q_hi["bk_no"],
                            close_ts=float(q_lo["end_ts"]),
                            now_ts=now,
                            k_low=float(ma["low_strike"]),
                            k_high=float(ma["high_strike"]),
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
        bundles = build_negrisk_cross_box_bundles(rungs, nr_brackets, spot=spot, max_strike_dist_log=0.10, tail_max_strike_dist_log=0.22)
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
            local_bk_cache.update(await self.fetch_books_batch(needed_toks, timeout=3.0))

        best_nr_diag: Optional[Tuple[float, str, float, float]] = None
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
            l1_sum = sum(
                p0 + float(lg.get("fee_rate", CRYPTO_FEE_RATE)) * p0 * (1.0 - p0)
                for lg in legs
                for p0 in [self._best_ask_sz(local_bk_cache[str(lg["token_id"])])[0]]
            )
            ratio_l1 = round(l1_sum / max(1.0, gp), 4)
            if ratio_l1 <= 1.15 and (best_nr_diag is None or ratio_l1 < best_nr_diag[0]):
                best_nr_diag = (ratio_l1, str(bnd["label"]), gp, float(bnd["end_ts"]))
            w_nr = walk_equal_shares_multi_leg_box(
                legs_spec,
                target_budget_usd=BANKROLL_TICKETS["T1000"]["N1_NEGRISK_CROSS_BOX"],
                guaranteed_payout_per_bundle=gp,
                max_bundle_cost_net=round(gp * 1.005, 4),
                min_shares=6,
                min_box_notional_usd=5.5,
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
                now_nr = time.time()
                if len(legs) == 2 and gp == 1.0 and cost_net <= 0.985 and (float(bnd["end_ts"]) - now_nr) <= 172800.0:
                    k_ref = float(legs[0].get("strike") or spot or 100.0)
                    self.emit_live_two_leg_box_candidate(
                        sleeve_source="N1_NEGRISK_CROSS_BOX",
                        box_type="NEGRISK_2LEG",
                        asset=asset,
                        dedupe_key=f"N1_{asset}_{bnd['bundle_id']}",
                        leg_a=legs[0],
                        leg_b=legs[1],
                        bk_a=local_bk_cache[str(legs[0]["token_id"])],
                        bk_b=local_bk_cache[str(legs[1]["token_id"])],
                        close_ts=float(bnd["end_ts"]),
                        now_ts=now_nr,
                        k_low=k_ref,
                        k_high=k_ref,
                    )
        if best_nr_diag is not None:
            now_d = time.time()
            self._record_market_telemetry(
                key=f"N1_BEST_{asset}_{int(best_nr_diag[3])}",
                min_interval_sec=90.0,
                now_ts=now_d,
                sig=(best_nr_diag[0], best_nr_diag[1]),
                payload={
                    "type": "NEGRISK_CRYPTO_CROSS_BEST",
                    "asset": asset,
                    "spot": round(spot, 4),
                    "tte_sec": round(best_nr_diag[3] - now_d, 0),
                    "payout": best_nr_diag[2],
                    "net_bundle_ratio_l1": best_nr_diag[0],
                    "label": best_nr_diag[1],
                },
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

    async def execute_ctf_overround_mint_sell(
        self,
        dedupe_key: str,
        asset: str,
        title: str,
        legs_bids_spec: List[Dict[str, Any]],
        close_ts: float,
        min_net_proceeds_per_set: float,
        opps_out: List[Dict[str, Any]],
        extra: Dict[str, Any],
    ) -> bool:
        """
        Executes instant zero-hold `CTF_OVERROUND_MINT_SELL`: mints equal complete sets at `$1.00`
        (`splitPosition`) and sweeps resting L2 `bids` across all `N` mutually exclusive outcomes.
        """
        if is_shadow_sleeve_quarantined("CTF_OVERROUND_MINT_SELL"):
            return False
        w_probe = walk_equal_shares_overround_bids(
            legs_bids_spec,
            target_mint_budget_usd=BANKROLL_TICKETS["T1000"]["CTF_OVERROUND_MINT_SELL"],
            min_net_proceeds_per_set=min_net_proceeds_per_set,
            min_shares=8.0,
        )
        if not w_probe.get("filled"):
            return False
        opps_out.append({
            "sleeve": "CTF_OVERROUND_MINT_SELL",
            "market": title,
            "ask_vwap": round(2.0 - float(w_probe["net_proceeds_per_set"]), 4),
            "p_model": 1.0,
            "net_edge": w_probe["net_edge_per_set"],
            "l1_usd": w_probe["l1_usd"],
            "close_ts": close_ts,
        })
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            tier_fills: Dict[str, Dict[str, Any]] = {}
            tier_pnls: Dict[str, float] = {}
            for t_name, t_map in BANKROLL_TICKETS.items():
                wt = walk_equal_shares_overround_bids(
                    legs_bids_spec,
                    target_mint_budget_usd=t_map["CTF_OVERROUND_MINT_SELL"],
                    min_net_proceeds_per_set=min_net_proceeds_per_set,
                    min_shares=5.0 if t_name == "T100" else 8.0,
                )
                if wt.get("filled"):
                    sh_t = float(wt["shares"])
                    tier_fills[t_name] = {
                        "filled": True,
                        "vwap": 1.0,
                        "eff_px": 1.0,
                        "spent_usd": round(sh_t, 2),
                        "fee_usd": wt["fee_usd"],
                        "shares": sh_t,
                        "l1_usd": wt["l1_usd"],
                    }
                    tier_pnls[t_name] = round(sh_t * float(wt["net_edge_per_set"]), 2)
            if "T1000" not in tier_fills:
                return False
            now = time.time()
            pos_id = f"CTF_OVERROUND_MINT_SELL_{int(now)}_{dedupe_key[-10:]}"
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": "CTF_OVERROUND_MINT_SELL",
                "asset_or_city": asset,
                "title": title,
                "side": f"MINT_SELL_{len(legs_bids_spec)}L",
                "token_id": dedupe_key,
                "fee_rate": 0.0,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "closed_ts": now,
                "closed_utc": datetime.now(timezone.utc).isoformat(),
                "p_model_entry": round(float(w_probe["net_proceeds_per_set"]), 4),
                "entry_eff_px_t1000": 1.0,
                "entry_vwap_t1000": 1.0,
                "realized_edge_t1000": w_probe["net_edge_per_set"],
                "net_payout_per_share": w_probe["gross_proceeds_per_set"],
                "tier_fills": tier_fills,
                "tier_pnls_usd": tier_pnls,
                "legging_adjusted_tier_pnls_usd": tier_pnls,
                "won": tier_pnls.get("T1000", 0.0) > 0,
                "extra": {**extra, "n_legs": len(legs_bids_spec)},
                "status": "INSTANT_MINT_AND_SELL_FILLED",
            }
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            self.closed_positions.append(pos)
            self._append_ledger({"event": "SHADOW_CLOSE", **pos})
            logger.info(
                f"[INSTANT_ARB:CTF_OVERROUND_MINT_SELL] {title} | net_proceeds=${w_probe['net_proceeds_per_set']:.4f} "
                f"(+{w_probe['net_edge_per_set']:.4f}/set) | PnL T1000=${tier_pnls.get('T1000', 0.0):+.2f}"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    async def scan_daily_updown_locks(self, opps_out: List[Dict[str, Any]]) -> None:
        """
        Addition #6 (`U1_DAILY_UPDOWN_LOCK` + Zero-Fee Pyth FX/Metals & Crypto Daily `C1_BINARY_COMPLETE_SET`).
        """
        now = time.time()
        loop = asyncio.get_running_loop()

        # 0. Scan all Daily Crypto + Zero-Fee Pyth FX/Metals Up/Down markets in 1 batch RTT for C1 Complete-Set arb
        c1_daily_specs = [
            sp for sp in [*self.daily_updown_markets.values(), *self.pyth_daily_markets.values()]
            if sp.end_ts > now + 60.0
        ]
        if c1_daily_specs:
            c1_bks = await self.fetch_books_batch(
                [sp.up_token for sp in c1_daily_specs] + [sp.down_token for sp in c1_daily_specs],
                timeout=3.0,
            )
            for sp_c1 in c1_daily_specs:
                bk_u = c1_bks.get(sp_c1.up_token)
                bk_d = c1_bks.get(sp_c1.down_token)
                if not bk_u or not bk_d:
                    continue
                ua_d, us_d = self._best_ask_sz(bk_u)
                da_d, ds_d = self._best_ask_sz(bk_d)
                if ua_d < 1.0 and da_d < 1.0:
                    f_d = float(sp_c1.fee_rate)
                    self._record_market_telemetry(
                        key=f"DAILY_C1_{sp_c1.market_id}",
                        min_interval_sec=60.0,
                        now_ts=now,
                        sig=(ua_d, da_d),
                        payload={
                            "type": "DAILY_COMPLETE_SET",
                            "asset": sp_c1.asset,
                            "market_id": sp_c1.market_id,
                            "title": sp_c1.title,
                            "fee_rate": f_d,
                            "tte_sec": round(sp_c1.end_ts - now, 0),
                            "up_ask": ua_d,
                            "down_ask": da_d,
                            "gross_sum_l1": round(ua_d + da_d, 4),
                            "net_sum_l1": round(ua_d + da_d + f_d * (ua_d * (1.0 - ua_d) + da_d * (1.0 - da_d)), 4),
                            "l1_min_shares": round(min(us_d, ds_d), 2),
                        },
                    )
                cap_c1 = 0.995 if sp_c1.fee_rate == 0.0 else 0.994
                c1_res = scan_binary_complete_set_arb(
                    market_id=sp_c1.market_id,
                    condition_id=sp_c1.condition_id,
                    yes_token=sp_c1.up_token,
                    no_token=sp_c1.down_token,
                    asks_yes_raw=bk_u.get("asks") or [],
                    asks_no_raw=bk_d.get("asks") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["C1_BINARY_COMPLETE_SET"],
                    fee_rate=sp_c1.fee_rate,
                    max_box_cost_net=cap_c1,
                )
                if c1_res.get("filled"):
                    opps_out.append({
                        "sleeve": "C1_BINARY_COMPLETE_SET",
                        "market": f"{sp_c1.asset} Complete-Set {sp_c1.title}",
                        "ask_vwap": c1_res["box_cost_net"],
                        "p_model": 1.0,
                        "net_edge": c1_res["riskless_floor_per_pair"],
                        "l1_usd": c1_res["l1_usd"],
                        "close_ts": sp_c1.end_ts,
                    })
                    leg_u = {"token_id": sp_c1.up_token, "opp_token_id": sp_c1.down_token, "condition_id": sp_c1.condition_id, "side": "UP", "label": "UP", "market_id": sp_c1.market_id, "fee_rate": sp_c1.fee_rate, "strike": 100.0}
                    leg_d = {"token_id": sp_c1.down_token, "opp_token_id": sp_c1.up_token, "condition_id": sp_c1.condition_id, "side": "DOWN", "label": "DOWN", "market_id": sp_c1.market_id, "fee_rate": sp_c1.fee_rate, "strike": 100.0}
                    await self.open_shadow_two_leg_box(
                        sleeve="C1_BINARY_COMPLETE_SET",
                        dedupe_key=f"C1_D_{sp_c1.market_id}",
                        asset=sp_c1.asset,
                        title=f"{sp_c1.asset} UP+DOWN Complete Set: {sp_c1.title}",
                        leg_a=leg_u,
                        leg_b=leg_d,
                        bk_a=bk_u,
                        bk_b=bk_d,
                        close_ts=sp_c1.end_ts,
                        max_box_cost_net=cap_c1,
                        extra={"is_complete_set": True, "market_id": sp_c1.market_id, "condition_id": sp_c1.condition_id},
                    )
                    if (sp_c1.end_ts - now) <= 86400.0 and float(c1_res["box_cost_net"]) <= (0.990 if sp_c1.fee_rate == 0.0 else 0.985):
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="C1_BINARY_COMPLETE_SET",
                            box_type="COMPLETE_SET",
                            asset=sp_c1.asset,
                            dedupe_key=f"C1_D_{sp_c1.market_id}",
                            leg_a=leg_u,
                            leg_b=leg_d,
                            bk_a=bk_u,
                            bk_b=bk_d,
                            close_ts=float(sp_c1.end_ts),
                            now_ts=now,
                        )
                await self.execute_ctf_overround_mint_sell(
                    dedupe_key=f"CTF_OVR_D_{sp_c1.market_id}",
                    asset=sp_c1.asset,
                    title=f"{sp_c1.asset} Binary Overround Mint-Sell: {sp_c1.title}",
                    legs_bids_spec=[
                        {"bids": bk_u.get("bids") or [], "fee_rate": sp_c1.fee_rate, "fee_exponent": 1.0},
                        {"bids": bk_d.get("bids") or [], "fee_rate": sp_c1.fee_rate, "fee_exponent": 1.0},
                    ],
                    close_ts=sp_c1.end_ts,
                    min_net_proceeds_per_set=1.003 if sp_c1.fee_rate == 0.0 else 1.004,
                    opps_out=opps_out,
                    extra={"overround_kind": "BINARY_DAILY", "market_id": sp_c1.market_id, "condition_id": sp_c1.condition_id},
                )

        # 0B. `D2_12PM_BINANCE_BOX`: 11:00-12:00 PM ET `1h` vs `12:00 PM ET` Daily/Multi-Strike Same-Binance Boxes
        for _, sp_h in list(self.hourly_12pm_markets.items()):
            tte_h = sp_h.end_ts - now
            if not (60.0 <= tte_h <= 3540.0) or now < sp_h.start_ts + 20.0:
                continue
            hk_key = f"H1_{sp_h.asset}_{int(sp_h.start_ts)}"
            c_ho = self.daily_open_cache.get(hk_key)
            if c_ho is None:
                ext_ho = await loop.run_in_executor(
                    None, fetch_binance_window_extremes_sync, sp_h.asset, sp_h.start_ts - 60.0, sp_h.start_ts + 60.0, "1m"
                )
                if ext_ho is not None and ext_ho[2] > 0:
                    self.daily_open_cache[hk_key] = (sp_h.end_ts, float(ext_ho[2]))
                    k_1h = float(ext_ho[2])
                else:
                    continue
            else:
                k_1h = c_ho[1]

            term_specs: List[Dict[str, Any]] = []
            for sp_d in self.daily_updown_markets.values():
                if sp_d.asset == sp_h.asset and abs(sp_d.end_ts - sp_h.end_ts) <= 5.0:
                    dk_key = f"{sp_d.asset}_{int(sp_d.start_ts)}"
                    c_do = self.daily_open_cache.get(dk_key)
                    if c_do is None:
                        ext_do = await loop.run_in_executor(
                            None, fetch_binance_window_extremes_sync, sp_d.asset, sp_d.start_ts - 60.0, sp_d.start_ts + 60.0, "1m"
                        )
                        if ext_do is not None and ext_do[2] > 0:
                            self.daily_open_cache[dk_key] = (sp_d.end_ts, float(ext_do[2]))
                            k_d = float(ext_do[2])
                        else:
                            k_d = 0.0
                    else:
                        k_d = c_do[1]
                    if k_d > 0:
                        term_specs.append({
                            "market_id": sp_d.market_id, "condition_id": sp_d.condition_id, "end_ts": sp_d.end_ts,
                            "strike": k_d, "is_downward": False, "yes_token": sp_d.up_token, "no_token": sp_d.down_token,
                            "yes_label": "UP", "no_label": "DOWN", "fee_rate": sp_d.fee_rate,
                        })
            for rungs_d2 in self.strike_ladders.values():
                if rungs_d2 and rungs_d2[0].asset == sp_h.asset and abs(rungs_d2[0].end_ts - sp_h.end_ts) <= 5.0:
                    for sr_d2 in rungs_d2:
                        if not sr_d2.is_downward:
                            term_specs.append({
                                "market_id": sr_d2.market_id, "condition_id": sr_d2.condition_id, "end_ts": sr_d2.end_ts,
                                "strike": sr_d2.strike, "is_downward": False, "yes_token": sr_d2.yes_token, "no_token": sr_d2.no_token,
                                "yes_label": "YES", "no_label": "NO", "fee_rate": CRYPTO_FEE_RATE,
                            })
            d2_cands = detect_d2_12pm_binance_boxes(
                {"asset": sp_h.asset, "market_id": sp_h.market_id, "condition_id": sp_h.condition_id, "end_ts": sp_h.end_ts, "up_token": sp_h.up_token, "down_token": sp_h.down_token, "fee_rate": sp_h.fee_rate},
                k_1h,
                term_specs,
            )
            if d2_cands:
                d2_toks = sorted({str(c["leg_a"]["token_id"]) for c in d2_cands} | {str(c["leg_b"]["token_id"]) for c in d2_cands})
                d2_bks = await self.fetch_books_batch(d2_toks, timeout=3.0)
                for dc in d2_cands:
                    la2, lb2 = dc["leg_a"], dc["leg_b"]
                    bka2, bkb2 = d2_bks.get(str(la2["token_id"])), d2_bks.get(str(lb2["token_id"]))
                    if not bka2 or not bkb2:
                        continue
                    aa2, _ = self._best_ask_sz(bka2)
                    ab2, _ = self._best_ask_sz(bkb2)
                    if aa2 < 1.0 and ab2 < 1.0:
                        self._record_market_telemetry(
                            key=f"D2_12PM_{la2['market_id']}_{lb2['market_id']}",
                            min_interval_sec=30.0,
                            now_ts=now,
                            sig=(aa2, ab2),
                            payload={
                                "type": "D2_12PM_CORRIDOR",
                                "asset": sp_h.asset,
                                "tte_sec": round(tte_h, 0),
                                "k_low": dc["k_low"],
                                "k_high": dc["k_high"],
                                "corridor_bps": dc["corridor_bps"],
                                "gross_box_l1": round(aa2 + ab2, 4),
                                "label": dc["label"],
                            },
                        )
                    w_d2 = walk_equal_shares_dominance_box(
                        bka2.get("asks") or [],
                        bkb2.get("asks") or [],
                        target_budget_usd=BANKROLL_TICKETS["T1000"]["D2_12PM_BINANCE_BOX"],
                        fee_rate_a=float(la2["fee_rate"]),
                        fee_rate_b=float(lb2["fee_rate"]),
                        max_box_cost_net=0.990,
                        min_shares=6,
                        min_box_notional_usd=5.5,
                    )
                    if w_d2.get("filled"):
                        opps_out.append({
                            "sleeve": "D2_12PM_BINANCE_BOX",
                            "market": f"{sp_h.asset} 12PM Box {dc['label']}",
                            "ask_vwap": round(float(w_d2["box_cost_net"]), 4),
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_d2["box_cost_net"]), 4),
                            "l1_usd": w_d2["l1_usd"],
                            "close_ts": dc["close_ts"],
                        })
                        await self.open_shadow_two_leg_box(
                            sleeve="D2_12PM_BINANCE_BOX",
                            dedupe_key=f"D2_{la2['market_id']}_{lb2['market_id']}",
                            asset=sp_h.asset,
                            title=f"{sp_h.asset} 12PM Binance Box {dc['label']}",
                            leg_a=la2,
                            leg_b=lb2,
                            bk_a=bka2,
                            bk_b=bkb2,
                            close_ts=float(dc["close_ts"]),
                            max_box_cost_net=0.990,
                            extra={"is_d2_12pm_box": True, "k_low": dc["k_low"], "k_high": dc["k_high"], "corridor_bps": dc["corridor_bps"]},
                        )

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
        _src_m = self.__dict__.get("_strike_source") or {}
        for c_key, (end_old, _) in list(_src_m.items()):
            if end_old < now - 600.0:
                _src_m.pop(c_key, None)
        for c_key, bo_ts in list(self._strike_fail_backoff_ts.items()):
            if float(bo_ts or 0.0) < now - 7200.0:
                self._strike_fail_backoff_ts.pop(c_key, None)

        target_end_ts = int(math.ceil(now / 900.0) * 900)
        rem_sec = float(target_end_ts) - now
        max_disc_rem = 305.0 if (self.single_scan or "fetch_json" in self.__dict__) else 335.0
        if not (5.0 <= rem_sec <= max_disc_rem):
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

    def _strike_is_rest_verified(self, spec: TwapCandleMarketSpec) -> bool:
        """False if the last strike returned for `spec` came from the unverified Chainlink-WS TWAP fallback.

        `get_authoritative_open_strike` tags every lookup (`PENDING` -> `WS_TWAP` / `REST_VERIFIED`), so in production
        a missing tag only occurs when the lookup is stubbed in tests.
        """
        c_key = f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}"
        src_ent = (self.__dict__.get("_strike_source") or {}).get(c_key)
        return bool(src_ent is None or src_ent[1] == "REST_VERIFIED")

    async def get_authoritative_open_strike(self, spec: TwapCandleMarketSpec) -> Optional[float]:
        c_key = f"{spec.asset}_{spec.horizon}_{int(spec.start_ts)}"
        # Source of the last returned strike: "WS_TWAP" (unverified Chainlink-WS boundary TWAP) or "REST_VERIFIED".
        # LIVE D1 emits require REST_VERIFIED strikes on both legs; shadow entries may still use WS TWAP.
        src_map: Dict[str, Tuple[float, str]] = self.__dict__.setdefault("_strike_source", {})
        cached = self.chainlink_open_cache.get(c_key)
        if cached is not None:
            src_map[c_key] = (spec.end_ts, "REST_VERIFIED")
            return cached[1]
        src_map[c_key] = (spec.end_ts, "PENDING")  # fail-closed for LIVE until a verified value is returned
        now_t = time.time()
        is_mocked = self.single_scan or ("fetch_json" in self.__dict__)
        cl_ws = getattr(self, "_chainlink_ws", None) if not is_mocked else None
        ws_twap_val = cl_ws.get_boundary_twap_60s(spec.asset, spec.start_ts, min_ticks=52) if cl_ws is not None else None
        if not self.single_scan and now_t < spec.start_ts + (0.20 if ws_twap_val is not None else 2.0):
            return None
        if not is_mocked and now_t < spec.start_ts + 2.0 and ws_twap_val is not None:
            src_map[c_key] = (spec.end_ts, "WS_TWAP")
            return ws_twap_val
        if not is_mocked:
            last_fail_ts = float(self._strike_fail_backoff_ts.get(c_key, 0.0) or 0.0)
            if (now_t - last_fail_ts) < 2.5:
                if ws_twap_val is not None:
                    src_map[c_key] = (spec.end_ts, "WS_TWAP")
                return ws_twap_val
        twap_url = build_crypto_price_query_url(spec)
        # Polymarket's crypto-price endpoint intermittently answers HTTP 400 {"error":"Chainlink API error 429"};
        # when prev_5m Gamma (`start_ts + 35s`) is already settled on CDN in live mode, skip multi-second retry sleeps!
        val: Optional[float] = None
        max_attempts = 3 if (is_mocked or now_t < spec.start_ts + 35.0) else 1
        retry_base = 0.3 if is_mocked else 0.12
        for _attempt in range(max_attempts):
            payload = await self.fetch_json(twap_url, timeout=4.0 if is_mocked else 2.5)
            val = parse_authoritative_open_price(payload, request_url=twap_url)
            if val is not None:
                break
            if _attempt + 1 < max_attempts:
                await asyncio.sleep(retry_base * (_attempt + 1))
        # prev_5m (`start_ts - 300`) closes AT `start_ts`: fallback as soon as `t >= start_ts + 35s` on upstream 429s,
        # and always cross-check once `t >= start_ts + 335s` (`needs_gamma`).
        needs_gamma = self.single_scan or now_t >= spec.start_ts + 335.0
        can_fallback_gamma = needs_gamma or (val is None and now_t >= spec.start_ts + 35.0)
        used_gamma = False
        if can_fallback_gamma:
            g_url = build_prev_5m_gamma_event_url(spec)
            g_val = parse_authoritative_open_price(await self.fetch_json(g_url, timeout=4.0 if is_mocked else 2.5), request_url=g_url)
            if val is None and g_val is not None:
                val = g_val
                used_gamma = True
            elif needs_gamma and g_val is not None and abs(val - g_val) / max(1e-9, g_val) > 1e-6:
                logger.error(
                    f"[CRITICAL TWAP MISMATCH VETO] {spec.asset} {spec.horizon}: "
                    f"crypto-price TWAP={val} != Gamma prev_5m finalPrice={g_val}!"
                )
                return None
            elif needs_gamma and g_val is None and not self.single_scan:
                if not is_mocked:
                    self._strike_fail_backoff_ts[c_key] = time.time()
                return None  # unverifiable while verification is possible -> fail closed, never cache
        if val is None:
            if not is_mocked:
                self._strike_fail_backoff_ts[c_key] = time.time()
                if ws_twap_val is not None and now_t < spec.start_ts + 335.0:
                    src_map[c_key] = (spec.end_ts, "WS_TWAP")
                    return ws_twap_val
            _fl = self.__dict__.setdefault("_strike_fail_log_ts", {})
            if (now_t - float(_fl.get(c_key, 0.0))) >= 60.0:
                _fl[c_key] = now_t
                logger.warning(
                    f"[STRIKE LOOKUP FAILED] {spec.asset} {spec.horizon}: crypto-price + prev_5m Gamma returned no usable openPrice -> skipped (fail-closed)."
                )
        if val is not None:
            hist_w = [px for ts_s, px in self.usd_spot_hist.get(spec.asset, ()) if (spec.start_ts - 60.0) <= ts_s <= (spec.start_ts + 5.0)]
            if len(hist_w) >= 3 and not self.single_scan:
                loc_twap = sum(hist_w) / len(hist_w)
                if loc_twap > 0.0 and abs(val - loc_twap) / loc_twap > 0.0035:
                    logger.error(f"[STRIKE TWAP VETO] {spec.asset} {spec.horizon}: strike {val} vs local 60s TWAP {loc_twap} > 35 bps")
                    return None
            elif not (needs_gamma or used_gamma):
                spot_ref = float(self.spots.get(spec.asset) or 0.0)
                if spot_ref > 0.0 and abs(val - spot_ref) / spot_ref > 0.015:
                    logger.error(f"[STRIKE SANITY VETO] {spec.asset} {spec.horizon}: strike {val} vs spot {spot_ref} > 150 bps")
                    return None
            self.chainlink_open_cache[c_key] = (spec.end_ts, val)
            src_map[c_key] = (spec.end_ts, "REST_VERIFIED")
        return val

    async def _passes_complement_anti_box_check(
        self,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        prefetched_books: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> bool:
        opp_a = str(leg_a.get("opp_token_id") or "")
        opp_b = str(leg_b.get("opp_token_id") or "")
        if not opp_a or not opp_b:
            return False
        bk_oa = (prefetched_books or {}).get(opp_a)
        bk_ob = (prefetched_books or {}).get(opp_b)
        if not (isinstance(bk_oa, dict) and isinstance(bk_ob, dict)):
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
        slate_side = str(slate_info.get("side") or "ALL_BUCKETS_YES")
        guar_pay = float(slate_info.get("guaranteed_payout_per_set") or 1.0)
        dedupe_key = f"W3_SLATE_{spec.event_id}" if slate_side == "ALL_BUCKETS_YES" else f"W3_SLATE_NO_{spec.event_id}"
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            sum_asks = float(slate_info["sum_asks"])
            legs = slate_info["legs"]
            min_avail_sh = min(float(lg.get("ask_shares", lg.get("ask_yes_shares", 0.0))) for lg in legs)
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
                "title": f"{spec.title} [Full-Slate {len(legs)} Buckets {slate_side}]",
                "side": slate_side,
                "token_id": "|".join(str(lg.get("token_id") or lg.get("yes_token")) for lg in legs),
                "fee_rate": 0.0,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": close_ts,
                "p_model_entry": round(guar_pay, 4),
                "entry_eff_px_t1000": round(sum_asks, 4),
                "entry_vwap_t1000": round(sum_asks, 4),
                "realized_edge_t1000": round(guar_pay - sum_asks, 4),
                "entry_best_bid": round(sum_asks, 4),
                "last_bid": round(sum_asks, 4),
                "maker_tp_px": None,
                "tier_fills": tier_fills,
                "extra": {"event_id": spec.event_id, "icao": spec.icao, "guaranteed_payout": guar_pay, "legs": legs},
                "status": "OPEN",
            }
            self.open_positions[pos_id] = pos
            for k_acq in acq:
                self.entered_keys.add(k_acq)
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            logger.info(f"[ENTRY:W3_WEATHER_SLATE_ARB] {pos['title']} @ sum_asks=${sum_asks:.4f} (payout=${guar_pay:.2f})")
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

            is_4h_mixed = ("4h" in (str(m15.horizon).lower(), str(m5.horizon).lower())) and (
                str(m15.horizon).lower() != str(m5.horizon).lower()
            )
            drag_ref = compute_d1_legging_drag_haircut(
                shares=float(w_ref["shares"]),
                box_cost_net=float(w_ref["box_cost_net"]),
                avail_a_shares=float(w_ref["avail_a_shares"]),
                avail_b_shares=float(w_ref["avail_b_shares"]),
                px_a=float(w_ref["leg_a_walk"]["worst_px"]),
                px_b=float(w_ref["leg_b_walk"]["worst_px"]),
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                is_4h_mixed=is_4h_mixed,
            )
            if drag_ref["legging_adjusted_net_ev_per_pair"] <= 0.0:
                logger.info(
                    f"[SHADOW LEGGING PARITY REJECT] {asset} {sleeve_override}: box_net=${w_ref['box_cost_net']:.4f} "
                    f"depth_mult={drag_ref['min_depth_mult']:.2f}x drag={drag_ref['legging_drag_per_pair']:.4f}/pair "
                    f"-> adj_ev={drag_ref['legging_adjusted_net_ev_per_pair']:+.4f}/pair <= 0"
                )
                return False

            tier_fills: Dict[str, Dict[str, Any]] = {}
            legging_drag_by_tier: Dict[str, float] = {}
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
                    dt_info = compute_d1_legging_drag_haircut(
                        shares=float(w_t["shares"]),
                        box_cost_net=float(w_t["box_cost_net"]),
                        avail_a_shares=float(w_t["avail_a_shares"]),
                        avail_b_shares=float(w_t["avail_b_shares"]),
                        px_a=float(w_t["leg_a_walk"]["worst_px"]),
                        px_b=float(w_t["leg_b_walk"]["worst_px"]),
                        fee_rate_a=float(leg_a["fee_rate"]),
                        fee_rate_b=float(leg_b["fee_rate"]),
                        is_4h_mixed=is_4h_mixed,
                    )
                    legging_drag_by_tier[tier_name] = float(dt_info["legging_drag_usd"])

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
                "legging_adjusted_edge_t1000": drag_ref["legging_adjusted_net_ev_per_pair"],
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
                    "legging_drag_ref": drag_ref,
                    "legging_drag_usd_by_tier": legging_drag_by_tier,
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
        if not (self.single_scan or ("fetch_json" in self.__dict__)):
            # Live mode: stamp with emit-time wall clock (caller's value may be stale after awaited book fetches)
            now_ts = time.time()
            if float(m5.end_ts - now_ts) < 38.0:
                return False
        pair_key = f"{m15.asset}_{m15.market_id}_{m5.market_id}"
        last_emit = float(self._last_d1_live_emit_ts.get(pair_key, 0.0) or 0.0)
        if (now_ts - last_emit) < 10.0:
            return False

        leg_a = dom_info["leg_a"]
        leg_b = dom_info["leg_b"]
        w_a = w_live["leg_a_walk"]
        w_b = w_live["leg_b_walk"]
        is_4h_live = ("4h" in (str(m15.horizon).lower(), str(m5.horizon).lower())) and (
            str(m15.horizon).lower() != str(m5.horizon).lower()
        )
        drag_live = compute_d1_legging_drag_haircut(
            shares=float(w_live["shares"]),
            box_cost_net=float(w_live["box_cost_net"]),
            avail_a_shares=float(w_live["avail_a_shares"]),
            avail_b_shares=float(w_live["avail_b_shares"]),
            px_a=float(w_a["worst_px"]),
            px_b=float(w_b["worst_px"]),
            fee_rate_a=float(leg_a["fee_rate"]),
            fee_rate_b=float(leg_b["fee_rate"]),
            is_4h_mixed=is_4h_live,
        )
        if drag_live["legging_adjusted_net_ev_per_pair"] <= 0.0:
            return False

        self._last_d1_live_emit_ts[pair_key] = now_ts
        for k_old, ts_old in list(self._last_d1_live_emit_ts.items()):
            if (now_ts - ts_old) > 1200.0:
                self._last_d1_live_emit_ts.pop(k_old, None)

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
            "legging_drag_per_pair": drag_live["legging_drag_per_pair"],
            "legging_adjusted_net_ev_per_pair": drag_live["legging_adjusted_net_ev_per_pair"],
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
        if not self.single_scan and self._ws_books:
            req_ws_toks = [
                t_id
                for t_id in (
                    str(leg_a["token_id"]),
                    str(leg_b["token_id"]),
                    str(leg_a.get("opp_token_id") or ""),
                    str(leg_b.get("opp_token_id") or ""),
                )
                if t_id
            ]
            now_ws_emit = time.time()
            rest_seeded = getattr(self, "_ws_rest_seeded", set())
            ws_entries = [None if t_id in rest_seeded else self._ws_books.get(t_id) for t_id in req_ws_toks]
            if len(req_ws_toks) >= 2 and all(
                e is not None and (now_ws_emit - e[0]) <= 0.50 and e[1].get("bids") and e[1].get("asks")
                for e in ws_entries
            ):
                cand["ws_books_ts"] = round(min(float(e[0]) for e in ws_entries if e is not None), 4)
                cand["ws_books"] = {
                    t_id: {
                        "bids": (e[1].get("bids") or [])[:12],
                        "asks": (e[1].get("asks") or [])[:12],
                    }
                    for t_id, e in zip(req_ws_toks, ws_entries)
                    if e is not None
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

    def emit_live_two_leg_box_candidate(
        self,
        *,
        sleeve_source: str,
        box_type: str,
        asset: str,
        dedupe_key: str,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        close_ts: float,
        now_ts: float,
        k_low: float = 100.0,
        k_high: float = 100.0,
    ) -> bool:
        """Emits a verified non-D1 2-leg riskless box candidate (C1, M3, B3, 2-leg N1) to the live IPC stream."""
        default_cand_path = LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl"
        if STATE_FILE != (DATA_DIR / "alpha124_shadow_state.json") and D1_LIVE_CANDIDATES_FILE == default_cand_path:
            return False
        if not (self.single_scan or ("fetch_json" in self.__dict__)):
            # Live mode: stamp with emit-time wall clock (caller's value may be stale after awaited book fetches)
            now_ts = time.time()
        rem_sec = float(close_ts - now_ts)
        if rem_sec < 45.0:
            return False
        last_emit = float(self._last_d1_live_emit_ts.get(dedupe_key, 0.0) or 0.0)
        if (now_ts - last_emit) < 15.0:
            return False
        fee_a = float(leg_a.get("fee_rate", CRYPTO_FEE_RATE))
        fee_b = float(leg_b.get("fee_rate", CRYPTO_FEE_RATE))
        exp_a = float(leg_a.get("fee_exponent", 1.0))
        exp_b = float(leg_b.get("fee_exponent", 1.0))
        max_cap = 0.990 if max(fee_a, fee_b) == 0.0 else 0.985
        w_live = walk_equal_shares_dominance_box(
            bk_a.get("asks") or [],
            bk_b.get("asks") or [],
            target_budget_usd=13.50,
            fee_rate_a=fee_a,
            fee_rate_b=fee_b,
            fee_exponent_a=exp_a,
            fee_exponent_b=exp_b,
            max_box_cost_net=max_cap,
            min_shares=5,
            min_box_notional_usd=4.85,
        )
        if not w_live.get("filled"):
            return False
        self._last_d1_live_emit_ts[dedupe_key] = now_ts
        w_a = w_live["leg_a_walk"]
        w_b = w_live["leg_b_walk"]
        corr_bps = round(abs(k_high - k_low) / max(1e-9, k_low) * 10000.0, 2) if k_low > 0 else 0.0
        cand = {
            "box_id": f"{box_type}_LIVE_{asset}_{int(close_ts)}_{str(leg_a.get('market_id','0'))[-5:]}",
            "dedupe_key": dedupe_key,
            "box_type": str(box_type),
            "ts_unix": round(now_ts, 3),
            "asset": str(asset),
            "regime": f"{box_type}_{leg_a.get('label','A')}_PLUS_{leg_b.get('label','B')}",
            "pair_horizons": str(box_type).lower(),
            "sleeve_source": str(sleeve_source),
            "is_quiet_book": True,
            "k_low": float(k_low),
            "k_high": float(k_high),
            "corridor_bps": corr_bps,
            "expiry_ts": float(close_ts),
            "rem_sec": round(rem_sec, 2),
            "shares": int(w_live["shares"]),
            "box_cost_net": float(w_live["box_cost_net"]),
            "max_box_cost_net": max_cap,
            "leg_a_token_id": str(leg_a["token_id"]),
            "leg_a_opp_token_id": str(leg_a.get("opp_token_id") or ""),
            "leg_a_label": str(leg_a.get("label") or leg_a.get("side") or "YES"),
            "leg_a_side": str(leg_a.get("side") or "YES"),
            "leg_a_horizon": str(leg_a.get("horizon") or box_type.lower()),
            "leg_a_market_id": str(leg_a.get("market_id") or ""),
            "leg_a_condition_id": str(leg_a.get("condition_id") or ""),
            "leg_a_strike": float(leg_a.get("strike") or k_low),
            "leg_a_limit_price": float(w_a["worst_px"]),
            "leg_a_avail_shares": float(w_live["avail_a_shares"]),
            "leg_a_fee_rate": fee_a,
            "leg_a_fee_exponent": exp_a,
            "leg_a_neg_risk": bool(leg_a.get("neg_risk", False)),
            "leg_b_token_id": str(leg_b["token_id"]),
            "leg_b_opp_token_id": str(leg_b.get("opp_token_id") or ""),
            "leg_b_label": str(leg_b.get("label") or leg_b.get("side") or "NO"),
            "leg_b_side": str(leg_b.get("side") or "NO"),
            "leg_b_horizon": str(leg_b.get("horizon") or box_type.lower()),
            "leg_b_market_id": str(leg_b.get("market_id") or ""),
            "leg_b_condition_id": str(leg_b.get("condition_id") or ""),
            "leg_b_strike": float(leg_b.get("strike") or k_high),
            "leg_b_limit_price": float(w_b["worst_px"]),
            "leg_b_avail_shares": float(w_live["avail_b_shares"]),
            "leg_b_fee_rate": fee_b,
            "leg_b_fee_exponent": exp_b,
            "leg_b_neg_risk": bool(leg_b.get("neg_risk", False)),
        }
        if not self.single_scan and self._ws_books:
            req_ws_2 = [str(leg_a["token_id"]), str(leg_b["token_id"])]
            if str(box_type) != "COMPLETE_SET":
                for op_id in (str(leg_a.get("opp_token_id") or ""), str(leg_b.get("opp_token_id") or "")):
                    if op_id:
                        req_ws_2.append(op_id)
            rest_seeded_2 = getattr(self, "_ws_rest_seeded", set())
            if all(
                t_x in self._ws_books and t_x not in rest_seeded_2 and (now_ts - self._ws_books[t_x][0]) <= 1.0
                for t_x in req_ws_2
            ):
                cand["ws_books"] = {t_x: self._ws_books[t_x][1] for t_x in req_ws_2}
                cand["ws_books_ts"] = round(min(self._ws_books[t_x][0] for t_x in req_ws_2), 3)
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
            logger.debug(f"2-leg box live candidate write notice: {exc}")
            return False

    def post_maker_anchor_candidate(
        self,
        m15: TwapCandleMarketSpec,
        m5: TwapCandleMarketSpec,
        dom_info: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        now_ts: float,
    ) -> bool:
        """
        Tier-2 (`D1_MAKER_ANCHOR_BOX`): Posts a single-leg 0%-fee `post_only=True` Maker Anchor
        on near-arb overlap corridors (`(0.995, 1.015]`) ONLY when the opposite hedge leg has >= 3.0x
        share depth and calm spot (`|ret_5s| <= 4.5 bps`). Supervised every 0.5s with $0 cancel-on-thinning.
        """
        if is_shadow_sleeve_quarantined("D1_MAKER_ANCHOR_BOX"):
            return False
        rem_sec = m5.end_ts - now_ts
        max_anc_rem = 880.0 if str(m5.horizon) == "15m" else 295.0
        if not (65.0 <= rem_sec <= max_anc_rem):
            return False
        if abs(self.get_return_bps(m15.asset, 5.0)) > 4.5:
            return False
        if (now_ts - float(self._last_any_shock_ts_by_asset.get(m15.asset, 0.0) or 0.0)) < 4.0:
            return False
        d_key = f"D1_MKR_{m15.asset}_{m15.market_id}_{m5.market_id}"
        if d_key in self.entered_keys or d_key in self.pending_maker_anchors or d_key in self.inflight_keys:
            return False

        leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
        bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
        bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
        asks_a = sorted([(float(a["price"]), float(a["size"])) for a in (bk_a.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        asks_b = sorted([(float(a["price"]), float(a["size"])) for a in (bk_b.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        if not asks_a or not asks_b or bid_a <= 0.0 or bid_b <= 0.0:
            return False
        ask_a, sz_a = asks_a[0]
        ask_b, sz_b = asks_b[0]
        spr_a, spr_b = round(ask_a - bid_a, 4), round(ask_b - bid_b, 4)

        best_choice: Optional[Tuple[bool, float, float, float]] = None  # (anchor_is_a, bid_anchor, hedge_eff, req_sh)
        for anchor_is_a in (True, False):
            b_anc = bid_a if anchor_is_a else bid_b
            a_anc = ask_a if anchor_is_a else ask_b
            s_anc = spr_a if anchor_is_a else spr_b
            asks_hdg = asks_b if anchor_is_a else asks_a
            leg_hdg = leg_b if anchor_is_a else leg_a
            if s_anc < 0.02 or not (0.12 <= a_anc <= 0.88):
                continue
            cand_bid = round(min(b_anc + 0.01, a_anc - 0.01), 2)
            asset_cap_u = float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(m15.asset, 40.0))
            ref_bud = min(float(BANKROLL_TICKETS["T1000"]["D1_MAKER_ANCHOR_BOX"]), asset_cap_u)
            req_sh = max(5.0, math.floor(ref_bud / 0.985))
            avail_hdg = sum(sz for px, sz in asks_hdg if px <= asks_hdg[0][0] + 0.01)
            if avail_hdg < max(15.0, 3.0 * req_sh):
                continue
            hdg_px = asks_hdg[0][0]
            hdg_fee = float(leg_hdg["fee_rate"]) * ((hdg_px * (1.0 - hdg_px)) ** float(leg_hdg.get("fee_exponent", 1.0)))
            hdg_eff = hdg_px + hdg_fee
            max_anc_bid = math.floor((0.988 - hdg_eff) * 100.0 + 1e-9) / 100.0
            bid_px = min(cand_bid, max_anc_bid)
            if bid_px < round(b_anc - 0.01, 2) or bid_px <= 0.04 or bid_px >= a_anc:
                continue
            if (bid_px + hdg_eff) <= 0.988:
                best_choice = (anchor_is_a, round(bid_px, 2), round(hdg_eff, 4), req_sh)
                break
        if best_choice is None:
            return False

        anchor_is_a, bid_px, hdg_eff, req_sh = best_choice
        self.pending_maker_anchors[d_key] = {
            "dedupe_key": d_key,
            "asset": m15.asset,
            "m15": m15,
            "m5": m5,
            "dom_info": dom_info,
            "anchor_is_a": anchor_is_a,
            "bid_px": bid_px,
            "req_shares_t1000": req_sh,
            "posted_ts": now_ts,
            "posted_spot": float(self.spots.get(m15.asset) or 0.0),
        }
        logger.info(
            f"[MAKER_ANCHOR_POST] {m15.asset} {dom_info['regime']} | Resting post_only=${bid_px:.2f} "
            f"+ hedge_eff=${hdg_eff:.4f} = ${bid_px + hdg_eff:.4f} (TTE={rem_sec:.0f}s)"
        )
        return True

    async def manage_pending_maker_anchors(self, now_ts: Optional[float] = None) -> None:
        if not self.pending_maker_anchors:
            return
        now = float(now_ts if now_ts is not None else time.time())
        needed_toks: List[str] = []
        for st in self.pending_maker_anchors.values():
            di = st["dom_info"]
            needed_toks.extend([str(di["leg_a"]["token_id"]), str(di["leg_b"]["token_id"])])
        bks = await self.fetch_books_batch(needed_toks, timeout=2.5)

        for d_key, st in list(self.pending_maker_anchors.items()):
            m15: TwapCandleMarketSpec = st["m15"]
            m5: TwapCandleMarketSpec = st["m5"]
            di = st["dom_info"]
            leg_a, leg_b = di["leg_a"], di["leg_b"]
            anc_is_a = bool(st["anchor_is_a"])
            leg_anc = leg_a if anc_is_a else leg_b
            leg_hdg = leg_b if anc_is_a else leg_a
            bk_anc = bks.get(str(leg_anc["token_id"]))
            bk_hdg = bks.get(str(leg_hdg["token_id"]))
            bid_px = float(st["bid_px"])
            rested = now - float(st["posted_ts"])
            rem_sec = m5.end_ts - now

            asks_anc = (bk_anc or {}).get("asks") or []
            best_ask_anc = min((float(a["price"]) for a in asks_anc if float(a.get("size", 0)) > 0), default=1.0)
            filled_anc = bk_anc is not None and rested >= 0.50 and best_ask_anc <= bid_px

            if filled_anc and bk_hdg is not None:
                self.pending_maker_anchors.pop(d_key, None)
                self.entered_keys.add(d_key)
                asks_hdg = sorted([(float(a["price"]), float(a["size"])) for a in (bk_hdg.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
                hdg_px = asks_hdg[0][0] if asks_hdg else 1.0
                hdg_avail = sum(sz for px, sz in asks_hdg if px <= hdg_px + 0.01) if asks_hdg else 0.0
                hdg_fee = float(leg_hdg["fee_rate"]) * ((hdg_px * (1.0 - hdg_px)) ** float(leg_hdg.get("fee_exponent", 1.0))) if hdg_px < 1.0 else 0.0
                pair_eff = round(bid_px + hdg_px + hdg_fee, 4)

                asset_cap_u = float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(m15.asset, 100.0))
                if asks_hdg and hdg_avail >= 5.0 and pair_eff <= 0.996:
                    tier_fills: Dict[str, Dict[str, Any]] = {}
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        sh = max(5.0, min(hdg_avail, math.floor(min(t_map["D1_MAKER_ANCHOR_BOX"], asset_cap_u) / pair_eff)))
                        fee_u = round(sh * hdg_fee, 4)
                        spent_u = round(sh * (bid_px + hdg_px), 2)
                        tier_fills[t_name] = {
                            "filled": True,
                            "vwap": round(bid_px + hdg_px, 4),
                            "eff_px": pair_eff,
                            "spent_usd": spent_u,
                            "fee_usd": fee_u,
                            "shares": sh,
                            "l1_usd": round(hdg_avail * pair_eff, 2),
                        }
                    bid_a_cur, _ = extract_best_bid((bks.get(str(leg_a["token_id"])) or {}).get("bids") or [])
                    bid_b_cur, _ = extract_best_bid((bks.get(str(leg_b["token_id"])) or {}).get("bids") or [])
                    pos_id = f"D1_MAKER_ANCHOR_BOX_{int(now)}_{m5.market_id[-6:]}"
                    pos = {
                        "position_id": pos_id,
                        "dedupe_key": d_key,
                        "sleeve": "D1_MAKER_ANCHOR_BOX",
                        "asset_or_city": m15.asset,
                        "title": f"{m15.asset} {di['regime']} [0%-Fee Maker Anchor @ ${bid_px:.2f}]",
                        "side": f"{leg_a['label']}+{leg_b['label']}",
                        "token_id": f"{leg_a['token_id']}|{leg_b['token_id']}",
                        "fee_rate": float(leg_hdg["fee_rate"]),
                        "entry_ts": now,
                        "entry_utc": datetime.now(timezone.utc).isoformat(),
                        "close_ts": m5.end_ts,
                        "p_model_entry": 1.0,
                        "entry_eff_px_t1000": pair_eff,
                        "entry_vwap_t1000": round(bid_px + hdg_px, 4),
                        "realized_edge_t1000": round(1.0 - pair_eff, 4),
                        "entry_best_bid": round(bid_a_cur + bid_b_cur, 4),
                        "last_bid": round(bid_a_cur + bid_b_cur, 4),
                        "maker_tp_px": None,
                        "tier_fills": tier_fills,
                        "extra": {
                            "is_dominance_box": True,
                            "is_maker_anchor_box": True,
                            "regime": di["regime"],
                            "k_low": di["k_low"],
                            "k_high": di["k_high"],
                            "corridor_bps": di["corridor_bps"],
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
                    self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                    logger.info(f"[ENTRY:D1_MAKER_ANCHOR_BOX] {pos['title']} -> Hedged @ net=${pair_eff:.4f}!")
                else:
                    # Honest adverse-fill scratch accounting (zero survivorship bias)
                    scr_bid, _ = extract_best_bid((bk_anc or {}).get("bids") or [])
                    if scr_bid <= 0.0:
                        scr_bid = max(0.01, bid_px - 0.03)
                    scr_fee = float(leg_anc["fee_rate"]) * scr_bid * (1.0 - scr_bid)
                    net_scr = max(0.0, scr_bid - scr_fee)
                    tf_s: Dict[str, Dict[str, Any]] = {}
                    tp_s: Dict[str, float] = {}
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        bud = round(0.5 * min(t_map["D1_MAKER_ANCHOR_BOX"], asset_cap_u), 2)
                        sh_s = round(bud / bid_px, 4)
                        tf_s[t_name] = {"filled": True, "vwap": bid_px, "eff_px": bid_px, "spent_usd": bud, "fee_usd": 0.0, "shares": sh_s}
                        tp_s[t_name] = round(sh_s * net_scr - bud, 2)
                    pos_scr = {
                        "position_id": f"D1_MKR_SCRATCH_{int(now)}_{m5.market_id[-6:]}",
                        "dedupe_key": d_key,
                        "sleeve": "D1_MAKER_ANCHOR_BOX",
                        "asset_or_city": m15.asset,
                        "title": f"{m15.asset} {di['regime']} [Maker Anchor Unhedged Scratch]",
                        "side": f"{leg_anc['label']}_SCRATCH",
                        "token_id": str(leg_anc["token_id"]),
                        "fee_rate": 0.0,
                        "entry_ts": st["posted_ts"],
                        "entry_utc": datetime.fromtimestamp(st["posted_ts"], tz=timezone.utc).isoformat(),
                        "close_ts": m5.end_ts,
                        "closed_ts": now,
                        "closed_utc": datetime.now(timezone.utc).isoformat(),
                        "p_model_entry": 0.5,
                        "entry_eff_px_t1000": bid_px,
                        "entry_vwap_t1000": bid_px,
                        "net_payout_per_share": round(net_scr, 4),
                        "tier_fills": tf_s,
                        "tier_pnls_usd": tp_s,
                        "won": tp_s.get("T1000", 0.0) > 0,
                        "status": "MAKER_ANCHOR_UNHEDGED_SCRATCH",
                    }
                    self.closed_positions.append(pos_scr)
                    self._append_ledger({"event": "SHADOW_CLOSE", **pos_scr})
                continue

            # Cancel-on-thinning / impulse / TTE / TTL supervision ($0.00 cost on unfilled post_only Maker quote)
            asks_hdg_c = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
            hdg_px_c = asks_hdg_c[0][0] if asks_hdg_c else 1.0
            hdg_avail_c = sum(sz for px, sz in asks_hdg_c if px <= hdg_px_c + 0.01) if asks_hdg_c else 0.0
            hdg_fee_c = float(leg_hdg["fee_rate"]) * ((hdg_px_c * (1.0 - hdg_px_c)) ** float(leg_hdg.get("fee_exponent", 1.0))) if hdg_px_c < 1.0 else 0.0
            thin_or_drifted = (hdg_avail_c < 2.0 * float(st["req_shares_t1000"])) or ((bid_px + hdg_px_c + hdg_fee_c) > 0.993)
            shock_recent = (now - float(self._last_any_shock_ts_by_asset.get(m15.asset, 0.0) or 0.0)) < 4.0
            if rem_sec <= 45.0 or rested >= 25.0 or abs(self.get_return_bps(m15.asset, 5.0)) > 5.0 or shock_recent or thin_or_drifted:
                self.pending_maker_anchors.pop(d_key, None)

    def post_zero_fee_maker_anchor_box(
        self,
        source_tag: str,
        asset: str,
        d_key: str,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        close_ts: float,
        title: str,
        now_ts: float,
    ) -> bool:
        """
        Posts a passive `post_only=True` `0%`-fee Maker Anchor quote on the wider-spread leg of a
        `0%`-fee 2-leg dominance box (`SP1` NBA, `CM_B3` Pyth, `TW1`, `FED1`, `COND1`) when Taker
        sum is `(0.994, 1.035]` and `bid_anc + ask_hdg <= $0.986`.
        """
        if is_shadow_sleeve_quarantined("ZERO_FEE_MAKER_ANCHOR_BOX"):
            return False
        if d_key in self.entered_keys or d_key in self.pending_zero_fee_maker_anchors or (close_ts - now_ts) < 300.0:
            return False
        if float(leg_a.get("fee_rate", 0.0)) > 0.0 or float(leg_b.get("fee_rate", 0.0)) > 0.0:
            return False
        bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
        bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
        asks_a = sorted([(float(a["price"]), float(a["size"])) for a in (bk_a.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        asks_b = sorted([(float(a["price"]), float(a["size"])) for a in (bk_b.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        if not asks_a or not asks_b or bid_a <= 0.0 or bid_b <= 0.0:
            return False
        ask_a, ask_b = asks_a[0][0], asks_b[0][0]
        req_sh = max(6.0, math.floor(float(BANKROLL_TICKETS["T1000"]["ZERO_FEE_MAKER_ANCHOR_BOX"]) / 0.986))
        best_c: Optional[Tuple[bool, float, float]] = None
        for anc_is_a in (True, False):
            b_anc = bid_a if anc_is_a else bid_b
            a_anc = ask_a if anc_is_a else ask_b
            b_hdg = bid_b if anc_is_a else bid_a
            asks_hdg = asks_b if anc_is_a else asks_a
            if (a_anc - b_anc) < 0.02 or not (0.04 <= a_anc <= 0.94):
                continue
            a_hdg = asks_hdg[0][0]
            if (a_hdg - b_hdg) > 0.045:
                continue
            avail_hdg = sum(sz for px, sz in asks_hdg if px <= a_hdg + 0.01)
            if avail_hdg < max(15.0, 2.5 * req_sh):
                continue
            cand_bid = min(round(min(b_anc + 0.01, a_anc - 0.01), 3), math.floor((0.986 - a_hdg) * 1000.0 + 1e-9) / 1000.0)
            if cand_bid < round(b_anc - 0.01, 3) or cand_bid <= 0.02 or cand_bid >= a_anc:
                continue
            if (cand_bid + a_hdg) <= 0.986:
                best_c = (anc_is_a, round(cand_bid, 3), round(a_hdg, 4))
                break
        if best_c is None:
            return False
        anc_is_a, bid_px, hdg_px = best_c
        self.pending_zero_fee_maker_anchors[d_key] = {
            "source_tag": source_tag,
            "dedupe_key": d_key,
            "asset": asset,
            "title": title,
            "leg_a": leg_a,
            "leg_b": leg_b,
            "anchor_is_a": anc_is_a,
            "bid_px": bid_px,
            "req_shares_t1000": req_sh,
            "close_ts": close_ts,
            "posted_ts": now_ts,
        }
        logger.info(
            f"[ZF_MAKER_ANCHOR_POST:{source_tag}] {title} | bid=${bid_px:.3f} + hdg=${hdg_px:.3f} = ${bid_px + hdg_px:.3f}"
        )
        return True

    async def manage_pending_zero_fee_maker_anchors(self, now_ts: Optional[float] = None) -> None:
        if not self.pending_zero_fee_maker_anchors:
            return
        now = float(now_ts if now_ts is not None else time.time())
        toks = [t for st in self.pending_zero_fee_maker_anchors.values() for t in (str(st["leg_a"]["token_id"]), str(st["leg_b"]["token_id"]))]
        bks = await self.fetch_books_batch(toks, timeout=3.0)
        for d_key, st in list(self.pending_zero_fee_maker_anchors.items()):
            la, lb = st["leg_a"], st["leg_b"]
            anc_is_a = bool(st["anchor_is_a"])
            leg_anc = la if anc_is_a else lb
            leg_hdg = lb if anc_is_a else la
            bk_anc = bks.get(str(leg_anc["token_id"]))
            bk_hdg = bks.get(str(leg_hdg["token_id"]))
            bid_px = float(st["bid_px"])
            rested = now - float(st["posted_ts"])
            rem_sec = float(st["close_ts"]) - now
            asks_anc = (bk_anc or {}).get("asks") or []
            best_ask_anc = min((float(a["price"]) for a in asks_anc if float(a.get("size", 0)) > 0), default=1.0)
            if bk_anc is not None and rested >= 0.50 and best_ask_anc <= bid_px and bk_hdg is not None:
                self.pending_zero_fee_maker_anchors.pop(d_key, None)
                self.entered_keys.add(d_key)
                asks_hdg = sorted([(float(a["price"]), float(a["size"])) for a in (bk_hdg.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
                hdg_px = asks_hdg[0][0] if asks_hdg else 1.0
                hdg_avail = sum(sz for px, sz in asks_hdg if px <= hdg_px + 0.01) if asks_hdg else 0.0
                pair_eff = round(bid_px + hdg_px, 4)
                if asks_hdg and hdg_avail >= 5.0 and pair_eff <= 0.994:
                    tf_zf: Dict[str, Dict[str, Any]] = {}
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        sh = max(5.0, min(hdg_avail, math.floor(t_map["ZERO_FEE_MAKER_ANCHOR_BOX"] / pair_eff)))
                        tf_zf[t_name] = {"filled": True, "vwap": pair_eff, "eff_px": pair_eff, "spent_usd": round(sh * pair_eff, 2), "fee_usd": 0.0, "shares": sh, "l1_usd": round(hdg_avail * pair_eff, 2)}
                    ba_c, _ = extract_best_bid((bks.get(str(la["token_id"])) or {}).get("bids") or [])
                    bb_c, _ = extract_best_bid((bks.get(str(lb["token_id"])) or {}).get("bids") or [])
                    pid = f"ZF_MAKER_ANCHOR_{int(now)}_{d_key[-8:]}"
                    pos = {
                        "position_id": pid, "dedupe_key": d_key, "sleeve": "ZERO_FEE_MAKER_ANCHOR_BOX",
                        "asset_or_city": st["asset"], "title": f"{st['title']} [ZF Maker Anchor @ ${bid_px:.3f}]",
                        "side": f"{la['label']}+{lb['label']}", "token_id": f"{la['token_id']}|{lb['token_id']}",
                        "fee_rate": 0.0, "entry_ts": now, "entry_utc": datetime.now(timezone.utc).isoformat(),
                        "close_ts": st["close_ts"], "p_model_entry": 1.0, "entry_eff_px_t1000": pair_eff,
                        "entry_vwap_t1000": pair_eff, "realized_edge_t1000": round(1.0 - pair_eff, 4),
                        "entry_best_bid": round(ba_c + bb_c, 4), "last_bid": round(ba_c + bb_c, 4),
                        "maker_tp_px": None, "tier_fills": tf_zf,
                        "extra": {"is_two_leg_box": True, "source_tag": st["source_tag"], "leg_a": la, "leg_b": lb},
                        "status": "OPEN",
                    }
                    self.open_positions[pid] = pos
                    self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                    logger.info(f"[ENTRY:ZERO_FEE_MAKER_ANCHOR_BOX] {pos['title']} -> Hedged @ ${pair_eff:.4f}!")
                else:
                    scr_bid, _ = extract_best_bid((bk_anc or {}).get("bids") or [])
                    net_scr = scr_bid if scr_bid > 0 else max(0.01, bid_px - 0.03)
                    tf_s, tp_s = {}, {}
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        bud = round(0.5 * t_map["ZERO_FEE_MAKER_ANCHOR_BOX"], 2)
                        sh_s = round(bud / bid_px, 4)
                        tf_s[t_name] = {"filled": True, "vwap": bid_px, "eff_px": bid_px, "spent_usd": bud, "fee_usd": 0.0, "shares": sh_s}
                        tp_s[t_name] = round(sh_s * net_scr - bud, 2)
                    pos_scr = {
                        "position_id": f"ZF_MKR_SCRATCH_{int(now)}_{d_key[-8:]}", "dedupe_key": d_key,
                        "sleeve": "ZERO_FEE_MAKER_ANCHOR_BOX", "asset_or_city": st["asset"],
                        "title": f"{st['title']} [ZF Maker Anchor Scratch]", "side": f"{leg_anc['label']}_SCRATCH",
                        "token_id": str(leg_anc["token_id"]), "fee_rate": 0.0, "entry_ts": st["posted_ts"],
                        "entry_utc": datetime.fromtimestamp(st["posted_ts"], tz=timezone.utc).isoformat(),
                        "close_ts": st["close_ts"], "closed_ts": now, "closed_utc": datetime.now(timezone.utc).isoformat(),
                        "p_model_entry": 0.5, "entry_eff_px_t1000": bid_px, "entry_vwap_t1000": bid_px,
                        "net_payout_per_share": round(net_scr, 4), "tier_fills": tf_s, "tier_pnls_usd": tp_s,
                        "legging_adjusted_tier_pnls_usd": tp_s, "won": tp_s.get("T1000", 0.0) > 0,
                        "status": "MAKER_ANCHOR_UNHEDGED_SCRATCH",
                    }
                    self.closed_positions.append(pos_scr)
                    self._append_ledger({"event": "SHADOW_CLOSE", **pos_scr})
                continue
            asks_hdg_c = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
            hdg_px_c = asks_hdg_c[0][0] if asks_hdg_c else 1.0
            hdg_avail_c = sum(sz for px, sz in asks_hdg_c if px <= hdg_px_c + 0.01) if asks_hdg_c else 0.0
            if rem_sec <= 180.0 or rested >= 900.0 or hdg_avail_c < 8.0 or (bid_px + hdg_px_c) > 0.996:
                self.pending_zero_fee_maker_anchors.pop(d_key, None)

    async def scan_same_oracle_dominance_boxes(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        if self.pending_maker_anchors:
            await self.manage_pending_maker_anchors(now)
        target_end_ts = int(math.ceil(now / 900.0) * 900)
        cur_window_pairs = sum(1 for k in self.dominance_pairs if str(k).endswith(f"_{target_end_ts}"))
        disc_interval = 7.0 if cur_window_pairs < len(DOMINANCE_ASSETS) else 12.0
        rem_to_15m = float(target_end_ts) - now
        in_disc_win = (
            self.is_in_same_oracle_overlap_window(now)
            if (self.single_scan or "fetch_json" in self.__dict__)
            else (5.0 <= rem_to_15m <= 330.0)
        )
        if in_disc_win and (now - self.last_dominance_discovery_ts) >= disc_interval:
            self.last_dominance_discovery_ts = now
            await self.discover_dominance_pairs(now)

        if now_ts is None:
            self.record_usd_spot_samples(time.time())

        active_pairs = [
            (m15, m5)
            for m15, m5 in list(self.dominance_pairs.values())
            if (10.0 <= (m5.end_ts - now) <= 300.0) and (now >= m5.start_ts + 1.0)
        ]
        if active_pairs:
            async def _resolve_dom(m15: TwapCandleMarketSpec, m5: TwapCandleMarketSpec):
                k_15m, k_5m = await asyncio.gather(
                    self.get_authoritative_open_strike(m15),
                    self.get_authoritative_open_strike(m5),
                )
                if k_15m is None or k_5m is None:
                    return None
                min_corr = float(MIN_CORRIDOR_BPS_BY_ASSET.get(m15.asset, 3.0))
                di = determine_dominance_legs(m15, k_15m, m5, k_5m, min_corridor_bps=min_corr)
                return (m15, m5, di) if di is not None else None

            resolved_rows = [r for r in await asyncio.gather(*(_resolve_dom(m15, m5) for m15, m5 in active_pairs)) if r is not None]
            if resolved_rows:
                batch_toks: List[str] = []
                for _, _, di in resolved_rows:
                    la, lb = di["leg_a"], di["leg_b"]
                    batch_toks.extend([
                        str(la["token_id"]),
                        str(lb["token_id"]),
                        str(la.get("opp_token_id") or ""),
                        str(lb.get("opp_token_id") or ""),
                    ])
                batch_bks = await self.fetch_books_batch(batch_toks, timeout=3.0)

                for m15, m5, dom_info in resolved_rows:
                    rem_sec = m5.end_ts - now
                    leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
                    bk_a = batch_bks.get(str(leg_a["token_id"]))
                    bk_b = batch_bks.get(str(leg_b["token_id"]))
                    if not bk_a or not bk_b:
                        continue
                    comp_checked: Optional[bool] = None
                    eval_now = float(now_ts) if now_ts is not None else time.time()
                    self._record_d1_corridor_telemetry("15m_5m", m15, m5, dom_info, bk_a, bk_b, eval_now)
                    rem_live = m5.end_ts - eval_now
                    # LIVE emits require both strikes REST/Gamma-verified (unverified WS-TWAP strikes stay shadow-only)
                    strikes_verified = self._strike_is_rest_verified(m15) and self._strike_is_rest_verified(m5)
                    if strikes_verified and 38.0 <= rem_live <= 298.0:
                        w_live = walk_equal_shares_dominance_box(
                            bk_a.get("asks") or [],
                            bk_b.get("asks") or [],
                            target_budget_usd=13.50,
                            fee_rate_a=float(leg_a["fee_rate"]),
                            fee_rate_b=float(leg_b["fee_rate"]),
                            fee_exponent_a=float(leg_a["fee_exponent"]),
                            fee_exponent_b=float(leg_b["fee_exponent"]),
                            max_box_cost_net=0.985,
                            min_shares=5,
                            min_box_notional_usd=4.85,
                        )
                        if w_live.get("filled"):
                            is_quiet_live = self._passes_quiet_book_filter(m15.asset, bk_a, bk_b, w_live, eval_now)
                            live_emit_cap = 0.985 if is_quiet_live else 0.980
                            if float(w_live["box_cost_net"]) <= live_emit_cap:
                                comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=batch_bks)
                                if not comp_checked:
                                    continue
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
                        max_box_cost_net=1.015,  # Surface near-arb boxes <= $1.015; enter Taker <= $0.995 or Maker Anchor in (0.995, 1.015]!
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
                                comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=batch_bks)
                            if not comp_checked:
                                continue
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
                        elif 0.995 < box_net <= 1.015:
                            if comp_checked is None:
                                comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=batch_bks)
                            if comp_checked:
                                self.post_maker_anchor_candidate(m15, m5, dom_info, bk_a, bk_b, eval_now)

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
        for k_s4, sp_s4 in list(self.s4h_candles.items()):
            if sp_s4.end_ts < now_ts - 600.0:
                self.s4h_candles.pop(k_s4, None)

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
                        self.s4h_candles[f"{asset}_4h_{target_end_ts}"] = sp4
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
            min_corr_4h = float(MIN_CORRIDOR_BPS_BY_ASSET.get(m4.asset, 3.0))
            dom_info = determine_dominance_legs(m4, k_4h, m_short, k_sh, min_corridor_bps=min_corr_4h)
            if dom_info is None:
                continue
            leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
            bks_4h = await self.fetch_books_batch(
                [
                    str(leg_a["token_id"]),
                    str(leg_b["token_id"]),
                    str(leg_a.get("opp_token_id") or ""),
                    str(leg_b.get("opp_token_id") or ""),
                ],
                timeout=3.0,
            )
            bk_a = bks_4h.get(str(leg_a["token_id"]))
            bk_b = bks_4h.get(str(leg_b["token_id"]))
            if not bk_a or not bk_b:
                continue
            comp_4h_ok: Optional[bool] = None
            eval_4h_now = float(now_ts) if now_ts is not None else time.time()
            self._record_d1_corridor_telemetry(f"4h_{m_short.horizon}", m4, m_short, dom_info, bk_a, bk_b, eval_4h_now)
            if now_ts is None:
                self.record_usd_spot_samples(eval_4h_now)
            rem_4h_live = m_short.end_ts - eval_4h_now
            # LIVE emits require both strikes REST/Gamma-verified (unverified WS-TWAP strikes stay shadow-only)
            strikes_4h_verified = self._strike_is_rest_verified(m4) and self._strike_is_rest_verified(m_short)
            if strikes_4h_verified and 38.0 <= rem_4h_live <= max_rem:
                w_live_4h = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=13.50,
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=0.985,
                    min_shares=5,
                    min_box_notional_usd=4.85,
                )
                if w_live_4h.get("filled"):
                    is_quiet_4h = self._passes_quiet_book_filter(m4.asset, bk_a, bk_b, w_live_4h, eval_4h_now)
                    if float(w_live_4h["box_cost_net"]) <= (0.985 if is_quiet_4h else 0.980):
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=bks_4h)
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
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=bks_4h)
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
                elif box_net <= 1.015:
                    self.post_maker_anchor_candidate(m4, m_short, dom_info, bk_a, bk_b, eval_4h_now)

        # `S4H_CHAINLINK_CONVERGENCE`: Final-15m (`180s <= rem_4h <= 900s`) 4h Chainlink SVI z>=2.30 convergence sniper
        for _, sp4 in list(self.s4h_candles.items()):
            rem_s4 = sp4.end_ts - now_4h
            if not (180.0 <= rem_s4 <= 900.0) or now_4h < sp4.start_ts + 3600.0:
                continue
            k_4h_s = await self.get_authoritative_open_strike(sp4)
            if k_4h_s is None or k_4h_s <= 0.0:
                continue
            shm4 = read_shm_usd_anchor(sp4.asset, now_4h, max_age_sec=3.0)
            uh4 = self.usd_spot_hist.get(sp4.asset)
            cur_u4 = shm4.get("usd_spot") or (float(uh4[-1][1]) if uh4 and (now_4h - float(uh4[-1][0])) <= 5.0 else self.spots.get(sp4.asset, 0.0))
            if not cur_u4 or float(cur_u4) <= 0.0:
                continue
            cur_u4_f = float(cur_u4)
            win_s4 = "UP" if cur_u4_f > k_4h_s else "DOWN"
            ret_30s = self.get_return_bps(sp4.asset, 30.0)
            if (win_s4 == "UP" and ret_30s < -6.0) or (win_s4 == "DOWN" and ret_30s > 6.0):
                continue
            svi4 = evaluate_svi_digital_fair_value(sp4.asset, cur_u4_f, k_4h_s, rem_s4, is_downward=False, now_ts=now_4h)
            pf4 = float(svi4["p_yes"] if win_s4 == "UP" else svi4["p_no"])
            zs4 = abs(float(svi4.get("z_sigma") or 0.0))
            if zs4 < 2.30 or pf4 < 0.940:
                continue
            tok4 = sp4.up_token if win_s4 == "UP" else sp4.down_token
            bk4 = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok4}", timeout=2.5)
            if not bk4:
                continue
            w4 = walk_l2_book_asks(bk4.get("asks") or [], BANKROLL_TICKETS["T1000"]["S4H_CHAINLINK_CONVERGENCE"], fee_rate=sp4.fee_rate, min_l1_usd=18.0)
            if not w4.get("filled"):
                continue
            epx4 = float(w4["eff_px"])
            edg4 = pf4 - epx4
            if 0.62 <= epx4 <= 0.89 and edg4 >= 0.030:
                opps_out.append({"sleeve": "S4H_CHAINLINK_CONVERGENCE", "market": f"{sp4.asset} 4h {win_s4} (TTE={rem_s4/60:.1f}m, z={zs4:.2f})", "ask_vwap": epx4, "p_model": round(pf4, 4), "net_edge": round(edg4, 4), "l1_usd": w4["l1_usd"], "close_ts": sp4.end_ts})
            if 0.62 <= epx4 <= 0.89 and edg4 >= 0.045:
                await self.open_shadow_position(
                    sleeve="S4H_CHAINLINK_CONVERGENCE",
                    dedupe_key=f"S4H_{sp4.asset}_{sp4.market_id}",
                    asset_or_city=sp4.asset,
                    title=f"{sp4.title} [4h Chainlink Convergence]",
                    side_label=win_s4,
                    token_id=tok4,
                    fee_rate=sp4.fee_rate,
                    p_model=pf4,
                    close_ts=sp4.end_ts,
                    extra={"market_id": sp4.market_id, "condition_id": sp4.condition_id, "horizon": "4h", "start_iso": sp4.start_iso, "end_iso": sp4.end_iso, "open_price": k_4h_s, "z_sigma": zs4},
                    tp_target_px=0.96,
                    prefetched_book=bk4,
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
                if asset not in DOMINANCE_ASSETS:
                    continue
                t0_u = float(trig.get("t0_unix") or 0.0)
                if t0_u <= 0.0 or (now - t0_u) > max_age_sec:
                    continue
                spot_t0 = float(trig.get("spot_at_t0") or trig.get("trigger_price") or 0.0)
                if spot_t0 > 0.0:
                    self.spots[asset] = spot_t0
                    self.spot_hist.setdefault(asset, collections.deque(maxlen=600)).append((now, spot_t0))
                cl_px = trig.get("chainlink_proxy_spot") or trig.get("coinbase_spot")
                if cl_px and float(cl_px) > 0.0:
                    self.usd_spot_hist.setdefault(asset, collections.deque(maxlen=400)).append((now, float(cl_px)))
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
        # Step 1: Defensive <250ms adverse-selection cancellation on resting Maker bids & Maker Anchors
        if self.pending_maker_orders:
            await self.manage_pending_maker_orders()
        if self.pending_maker_anchors:
            await self.manage_pending_maker_anchors(now)

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
            cl_ws_s2 = getattr(self, "_chainlink_ws", None) if not self.single_scan else None
            ws_spot_s2 = cl_ws_s2.get_latest_spot(spec.asset, now_ts=now, max_age_sec=2.5) if cl_ws_s2 is not None else None
            usd_hist = self.usd_spot_hist.get(spec.asset)
            cur_usd = ws_spot_s2 or shm.get("usd_spot")
            if (not cur_usd or float(cur_usd) <= 0.0) and usd_hist and (now - float(usd_hist[-1][0])) <= 5.0:
                cur_usd = float(usd_hist[-1][1])
            if (not cur_usd or float(cur_usd) <= 0.0) and self.usd_direct_flags.get(spec.asset, False):
                cur_usd = self.spots.get(spec.asset, 0.0)
            if not cur_usd or float(cur_usd) <= 0.0:
                continue
            cur_usd_f = float(cur_usd)
            usd_direct = bool(
                ws_spot_s2 is not None
                or shm.get("source") in ("shm_chainlink_proxy", "shm_coinbase_usd")
                or self.usd_direct_flags.get(spec.asset, False)
            )
            iv_1d, _ = get_wing_implied_vol(spec.asset, cur_usd_f, k_open, 86400.0)
            samples = cl_ws_s2.get_recent_samples(spec.asset, spec.end_ts - 62.0) if cl_ws_s2 is not None else []
            if len(samples) < 2:
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

        s5m_assets = ("BTC", "ETH", "SOL", "BNB", "HYPE")
        for _, (_, m5_p) in self.dominance_pairs.items():
            if m5_p.asset in s5m_assets and abs(m5_p.end_ts - end_5m) <= 2.0:
                self.s5m_candles[f"{m5_p.asset}_5m_{end_5m}"] = m5_p
        for k_tw, sp_tw in self.twap_candles.items():
            if sp_tw.asset in s5m_assets and sp_tw.horizon == "5m" and abs(sp_tw.end_ts - end_5m) <= 2.0:
                self.s5m_candles[k_tw] = sp_tw

        now_iso = datetime.fromtimestamp(now_ts - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for asset in s5m_assets:
            if asset not in DOMINANCE_SERIES_SLUGS or "5m" not in DOMINANCE_SERIES_SLUGS[asset]:
                continue
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
            if (not cur_usd or float(cur_usd) <= 0.0) and self.usd_direct_flags.get(spec.asset, False):
                cur_usd = self.spots.get(spec.asset, 0.0)
            if not cur_usd or float(cur_usd) <= 0.0:
                continue
            cur_usd_f = float(cur_usd)

            is_alt_5m = spec.asset not in ("BTC", "ETH")
            dist_pct = abs(cur_usd_f - k_open) / k_open * 100.0
            if dist_pct < (0.140 if is_alt_5m else 0.085):
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
            if z_sig < (2.25 if is_alt_5m else 1.35) or p_fair < (0.935 if is_alt_5m else 0.905):
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
            if 0.58 <= eff_px <= 0.86 and edge >= (0.055 if is_alt_5m else 0.045):
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

            # 0A. Dedicated multi-leg supervision & settlement for D1, M3, B3, C1 & W3_WEATHER_SLATE_ARB
            if sleeve == "W3_WEATHER_SLATE_ARB":
                close_ts_f = float(pos["close_ts"])
                if now >= close_ts_f + 30.0:
                    extra_w = pos.get("extra") or {}
                    legs = extra_w.get("legs") or []
                    guar_pay_w = float(extra_w.get("guaranteed_payout") or 1.0)
                    resolved_vals = await asyncio.gather(
                        *[
                            self.resolve_via_gamma_market(
                                {
                                    "token_id": lg.get("token_id") or lg.get("yes_token", ""),
                                    "side": lg.get("side", "YES"),
                                    "extra": {"market_id": lg["market_id"]},
                                }
                            )
                            for lg in legs
                        ]
                    )
                    if resolved_vals and all(v is not None for v in resolved_vals):
                        total_pay = round(sum(float(v) for v in resolved_vals if v is not None), 4)
                        st_w = "SETTLED_WEATHER_SLATE_1X" if guar_pay_w <= 1.01 else "SETTLED_WEATHER_SLATE_NX"
                        to_close.append((pid, st_w, max(guar_pay_w, total_pay), 0.0))
                continue

            extra_chk = pos.get("extra") or {}
            if sleeve in (
                "D1_SAME_ORACLE_DOMINANCE_BOX",
                "D1_4H_DOMINANCE_BOX",
                "D1_QUIET_BOOK_BOX",
                "D1_MAKER_ANCHOR_BOX",
                "M3_LADDER_MONO_BOX",
                "B3_BARRIER_MONO_BOX",
                "C1_BINARY_COMPLETE_SET",
                "CM_B3_PYTH_BARRIER_BOX",
                "SP1_NBA_ZERO_FEE_BOX",
                "ZERO_FEE_MAKER_ANCHOR_BOX",
                "D2_12PM_BINANCE_BOX",
            ) or (extra_chk.get("leg_a") and extra_chk.get("leg_b")):
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
                    if bk_a or bk_b or (now - float(pos.get("_last_gamma_chk_ts") or 0.0)) < 60.0:
                        continue
                    pos["_last_gamma_chk_ts"] = now

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

                if sleeve == "B3_BARRIER_MONO_BOX" and now >= close_ts_f + 900.0:
                    d_b3 = str(extra.get("direction") or "UP").upper()
                    ext_b3 = await loop.run_in_executor(
                        None, fetch_binance_window_extremes_sync, pos["asset_or_city"], float(pos["entry_ts"]), close_ts_f, "1m"
                    )
                    if ext_b3 is not None:
                        max_h, min_l, _ = ext_b3
                        k_a_b3 = float(leg_a.get("strike") or 0.0)
                        k_b_b3 = float(leg_b.get("strike") or 0.0)
                        t_a = (d_b3 == "UP" and max_h >= k_a_b3) or (d_b3 == "DOWN" and min_l <= k_a_b3)
                        t_b = (d_b3 == "UP" and max_h >= k_b_b3) or (d_b3 == "DOWN" and min_l <= k_b_b3)
                        total_pay = (1.0 if t_a else 0.0) + (0.0 if t_b else 1.0)
                        to_close.append((pid, "SETTLED_BARRIER_MONO_2X" if total_pay >= 1.99 else "SETTLED_BARRIER_MONO_1X", total_pay, 0.0))
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

            if sleeve in ("N1_NEGRISK_CROSS_BOX", "P1_PREOPEN_MAKER_STRADDLE", "NR0_ZERO_FEE_SLATE_ARB") or bool(extra_chk.get("legs")):
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

                # Authoritative Chainlink 60s-TWAP fallback for S5M_CHAINLINK_SNIPER / S4H_CHAINLINK_CONVERGENCE if Gamma lags >= 120s
                if sleeve in ("S5M_CHAINLINK_SNIPER", "S4H_CHAINLINK_CONVERGENCE") and now >= float(pos["close_ts"]) + 120.0:
                    extra = pos.get("extra") or {}
                    if extra.get("start_iso"):
                        cp_url = build_own_gamma_event_url(pos["asset_or_city"], str(extra.get("horizon") or "5m"), extra["start_iso"])
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
            adj_tier_pnls: Dict[str, float] = {}
            drag_map = (pos.get("extra") or {}).get("legging_drag_usd_by_tier") or {}
            for t_name, tf in pos["tier_fills"].items():
                cost_total = float(tf["spent_usd"]) + float(tf["fee_usd"])
                payout_usd = float(tf["shares"]) * net_pay_ps
                raw_p = round(payout_usd - cost_total, 2)
                tier_pnls[t_name] = raw_p
                adj_tier_pnls[t_name] = round(raw_p - float(drag_map.get(t_name, 0.0) or 0.0), 2)

            won_t1000 = tier_pnls.get("T1000", 0.0) > 0
            pos.update({
                "status": status,
                "closed_ts": now,
                "closed_utc": datetime.now(timezone.utc).isoformat(),
                "net_payout_per_share": round(net_pay_ps, 4),
                "tier_pnls_usd": tier_pnls,
                "legging_adjusted_tier_pnls_usd": adj_tier_pnls,
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
            # Maker-anchor unhedged scratches record a single-leg bid (~$0.40) as entry_eff_px: they are real losses,
            # never anti-box entries, so they must never be dropped (survivorship bias in graduation stats).
            closed_sl = [
                p for p in all_closed_sl
                if not (
                    is_d1_sl
                    and p.get("status") != "MAKER_ANCHOR_UNHEDGED_SCRATCH"
                    and float(p.get("entry_eff_px_t1000") or 1.0) < 0.900
                )
            ]
            excluded_anti = len(all_closed_sl) - len(closed_sl)
            open_sl = [p for p in self.open_positions.values() if p.get("sleeve") == sl]
            wins = sum(1 for p in closed_sl if p.get("won"))
            pnl_1k = sum(float(p.get("tier_pnls_usd", {}).get("T1000", 0.0)) for p in closed_sl)
            adj_pnl_1k = sum(
                float(p.get("legging_adjusted_tier_pnls_usd", p.get("tier_pnls_usd", {})).get("T1000", 0.0))
                for p in closed_sl
            )
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
                "legging_adjusted_pnl_t1000_usd": round(adj_pnl_1k, 2),
                "excluded_anti_box": excluded_anti,
                "quarantined": is_shadow_sleeve_quarantined(sl),
            }

        # Graduation by-asset stats cover only the taker dominance-box sleeves (maker-anchor tracked in by_sleeve)
        D1_GRAD_SLEEVES = {"D1_SAME_ORACLE_DOMINANCE_BOX", "D1_4H_DOMINANCE_BOX", "D1_QUIET_BOOK_BOX"}
        by_d1_asset: Dict[str, Dict[str, Any]] = {}
        for a_dom in DOMINANCE_ASSETS:
            cl_a = [
                p for p in self.closed_positions
                if str(p.get("sleeve") or "") in D1_GRAD_SLEEVES
                and str(p.get("asset_or_city") or "").upper() == a_dom
                and (
                    p.get("status") == "MAKER_ANCHOR_UNHEDGED_SCRATCH"
                    or float(p.get("entry_eff_px_t1000") or 1.0) >= 0.900
                )
            ]
            op_a = [
                p for p in self.open_positions.values()
                if str(p.get("sleeve") or "") in D1_GRAD_SLEEVES
                and str(p.get("asset_or_city") or "").upper() == a_dom
            ]
            w_a_cnt = sum(1 for p in cl_a if p.get("won"))
            pnl_a_1k = sum(float(p.get("tier_pnls_usd", {}).get("T1000", 0.0)) for p in cl_a)
            adj_pnl_a_1k = sum(
                float(p.get("legging_adjusted_tier_pnls_usd", p.get("tier_pnls_usd", {})).get("T1000", 0.0))
                for p in cl_a
            )
            by_d1_asset[a_dom] = {
                "open": len(op_a),
                "closed": len(cl_a),
                "wins": w_a_cnt,
                "losses": len(cl_a) - w_a_cnt,
                "win_rate_pct": round(100.0 * w_a_cnt / len(cl_a), 2) if cl_a else 0.0,
                "realized_pnl_t1000_usd": round(pnl_a_1k, 2),
                "legging_adjusted_pnl_t1000_usd": round(adj_pnl_a_1k, 2),
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
                "pyth_daily_markets": len(self.pyth_daily_markets),
                "pyth_barrier_rungs": len(self.pyth_barrier_rungs),
                "pyth_close_ladders": len(self.pyth_close_ladders),
                "nba_zero_fee_games": len(self.nba_games),
                "negrisk_zero_fee_slates": len(self.negrisk_zero_slates),
                "counting_slates": len(self.counting_slates),
                "fomc_lp_markets": len(self.fomc_truth_legs) // 2,
                "oil_senate_markets": len(self.oil_senate_truth_legs) // 2,
                "hourly_12pm_pairs": len(self.hourly_12pm_markets),
                "same_oracle_dominance_pairs": len(self.dominance_pairs),
                "dominance_4h_pairs": len(self.dominance_4h_pairs),
                "exact_twap_lock_candles": len(self.twap_candles),
                "s5m_sniper_candles": len(self.s5m_candles),
                "s4h_candles": len(self.s4h_candles),
                "preopen_15m_candles": len(self.preopen_15m_candles),
            },
            "portfolio_realized_pnl_by_bankroll_usd": tier_totals,
            "by_sleeve": by_sleeve,
            "per_strategy": by_sleeve,
            "by_d1_asset": by_d1_asset,
            "open_positions_count": len(self.open_positions),
            "pending_maker_orders_count": len(self.pending_maker_orders),
            "pending_maker_anchors_count": len(self.pending_maker_anchors),
            "pending_zero_fee_maker_anchors_count": len(self.pending_zero_fee_maker_anchors),
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
                            "by_d1_asset": by_d1_asset,
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

    async def _get_pyth_intraday(self, asset: str, now_ts: float) -> Optional[Dict[str, Any]]:
        cfg = PYTH_ASSET_CONFIG.get(asset.upper())
        if not cfg:
            return None
        yh_sym, _, _, _, vol_floor = cfg
        cached = self.pyth_intraday_cache.get(yh_sym)
        if cached is not None and (now_ts - cached[0]) < 90.0:
            return cached[1]
        res = await asyncio.to_thread(fetch_yahoo_1m_intraday_sync, yh_sym, vol_floor)
        if res is not None:
            self.pyth_intraday_cache[yh_sym] = (now_ts, res)
        return res

    async def scan_tradfi_and_sports_markets(self, opps_out: List[Dict[str, Any]]) -> None:
        """
        Scans `0.00%`-fee Pyth Commodities/Metals/Equities (`CM_B3`, `CM_B2`, `CM_U1`, `B4`),
        NBA Full-Game Dominance Boxes (`SP1_NBA_ZERO_FEE_BOX`), and Zero-Fee NegRisk Slates (`NR0`).
        """
        now = time.time()

        # 1. Refresh Yahoo 1m intraday anchors across active Pyth assets
        active_pyth_assets = sorted(
            {r.asset for r in self.pyth_barrier_rungs.values() if r.end_ts > now + 120}
            | {rgs[0].asset for rgs in self.pyth_close_ladders.values() if rgs and rgs[0].end_ts > now + 120}
        )
        feed_by_asset: Dict[str, Dict[str, Any]] = {}
        for a_p in active_pyth_assets:
            fd = await self._get_pyth_intraday(a_p, now)
            if fd:
                feed_by_asset[a_p] = fd

        # 2. Batch-fetch near-ATM Pyth Hit & Close books (`0%` fee)
        near_hit: List[PythBarrierRungSpec] = []
        for r in self.pyth_barrier_rungs.values():
            if r.end_ts <= now + 120 or r.asset not in feed_by_asset:
                continue
            sp_px = float(feed_by_asset[r.asset]["spot"])
            if sp_px > 0 and abs(math.log(r.strike / sp_px)) <= 0.25:
                near_hit.append(r)

        near_close: List[PythCloseRungSpec] = []
        for rgs in self.pyth_close_ladders.values():
            for rc in rgs:
                if rc.end_ts <= now + 120 or rc.asset not in feed_by_asset:
                    continue
                sp_px = float(feed_by_asset[rc.asset]["spot"])
                if sp_px > 0 and abs(math.log(rc.strike / sp_px)) <= 0.14:
                    near_close.append(rc)

        pyth_toks = (
            [r.yes_token for r in near_hit] + [r.no_token for r in near_hit]
            + [rc.yes_token for rc in near_close] + [rc.no_token for rc in near_close]
        )
        pyth_bks = await self.fetch_books_batch(pyth_toks, timeout=3.5) if pyth_toks else {}

        all_hit_rows: List[Dict[str, Any]] = []
        by_event_hit_rows: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
        for r in near_hit:
            bk_y, bk_n = pyth_bks.get(r.yes_token), pyth_bks.get(r.no_token)
            if not bk_y or not bk_n:
                continue
            cfg = PYTH_ASSET_CONFIG[r.asset]
            _, sess_cls, exact_ok, basis_buf, _ = cfg
            fd = feed_by_asset[r.asset]
            spot_p = float(fd["spot"])
            in_active_window = now >= r.start_ts
            ext_p = window_extremes_from_bars(fd["bars"], r.start_ts, now) if in_active_window else None

            # Check B4_TOUCHED_BARRIER_WICK_LOCK ONLY inside active observation window (`now >= r.start_ts + 300s`)
            # with wider CME roll/venue cushion (`>= 0.80%` + `bid >= 0.88`) to eliminate NYMEX-vs-ICE basis ticks
            if in_active_window and now >= r.start_ts + 300.0 and exact_ok and sess_cls in ("EQUITY_RTH", "CME_23H") and ext_p is not None and f"B4_PYTH_{r.market_id}" not in self.entered_keys:
                fh_p, fl_p = ext_p
                b4_buf = 0.0015 if sess_cls == "EQUITY_RTH" else max(0.0080, 2.5 * basis_buf)
                min_b4_bid = 0.78 if sess_cls == "EQUITY_RTH" else 0.88
                if (r.direction == "UP" and fh_p >= r.strike * (1.0 + b4_buf)) or (r.direction == "DOWN" and fl_p <= r.strike * (1.0 - b4_buf)):
                    bid_b4p, _ = extract_best_bid(bk_y.get("bids") or [])
                    w_b4p = walk_l2_book_asks(bk_y.get("asks") or [], 100.0, fee_rate=0.0, min_l1_usd=15.0, max_ask_px=0.990)
                    if w_b4p.get("filled") and bid_b4p >= min_b4_bid and 0.85 <= float(w_b4p["eff_px"]) <= 0.986:
                        opps_out.append({
                            "sleeve": "B4_TOUCHED_BARRIER_WICK_LOCK",
                            "market": f"{r.asset} Pyth Breached Wick Lock: {r.question}",
                            "ask_vwap": w_b4p["eff_px"],
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_b4p["eff_px"]), 4),
                            "l1_usd": w_b4p["l1_usd"],
                        })
                        await self.open_shadow_position(
                            sleeve="B4_TOUCHED_BARRIER_WICK_LOCK",
                            dedupe_key=f"B4_PYTH_{r.market_id}",
                            asset_or_city=r.asset,
                            title=r.question,
                            side_label="YES",
                            token_id=r.yes_token,
                            fee_rate=0.0,
                            p_model=1.0,
                            close_ts=r.end_ts,
                            extra={"market_id": r.market_id, "condition_id": r.condition_id, "strike": r.strike, "direction": r.direction, "session_class": sess_cls},
                            prefetched_book=bk_y,
                        )
                        continue

            w_qy = walk_l2_book_asks(bk_y.get("asks") or [], 35.0, fee_rate=0.0, min_l1_usd=8.0)
            w_qn = walk_l2_book_asks(bk_n.get("asks") or [], 35.0, fee_rate=0.0, min_l1_usd=8.0)
            row_h = {
                "asset": r.asset,
                "event_id": r.event_id,
                "strike": r.strike,
                "direction": r.direction,
                "market_id": r.market_id,
                "condition_id": r.condition_id,
                "yes_token": r.yes_token,
                "no_token": r.no_token,
                "fee_rate": 0.0,
                "ask_yes": w_qy.get("vwap") if w_qy.get("filled") else None,
                "ask_no": w_qn.get("vwap") if w_qn.get("filled") else None,
                "bk_yes": bk_y,
                "bk_no": bk_n,
                "start_ts": r.start_ts,
                "end_ts": r.end_ts,
            }
            all_hit_rows.append(row_h)
            by_event_hit_rows[r.event_id].append(row_h)

            # CM_B2_PYTH_SESSION_NO_LOCK (`0%` fee, same-session final <=3.5h lock -> zero overnight/earnings gap + tight spread <=4c)
            eff_hrs = compute_effective_trading_hours(now, r.end_ts, sess_cls)
            same_sess = is_same_continuous_session(now, r.end_ts, sess_cls)
            already_hit = ext_p is not None and (
                (r.direction == "UP" and ext_p[0] >= r.strike * (1.0 - basis_buf))
                or (r.direction == "DOWN" and ext_p[1] <= r.strike * (1.0 + basis_buf))
            )
            if in_active_window and exact_ok and same_sess and not already_hit and 0.25 <= eff_hrs <= 3.5:
                ev_no = evaluate_pyth_session_barrier_no_lock(spot_p, r.strike, r.direction, eff_hrs, float(fd["sigma_session"]), basis_buf)
                p_no_p = float(ev_no["p_no"])
                if p_no_p >= 0.94:
                    bid_np, _ = extract_best_bid(bk_n.get("bids") or [])
                    w_np = walk_l2_book_asks(bk_n.get("asks") or [], 100.0, fee_rate=0.0, min_l1_usd=15.0)
                    if w_np.get("filled") and 0.78 <= float(w_np["eff_px"]) <= 0.955 and bid_np > 0 and (float(w_np["vwap"]) - bid_np) <= 0.04:
                        edge_np = p_no_p - float(w_np["eff_px"])
                        b2_g = evaluate_barrier_no_net_ev(1.0 - p_no_p, float(w_np["vwap"]), fee_rate=0.0)
                        if edge_np >= 0.025:
                            opps_out.append({
                                "sleeve": "CM_B2_PYTH_SESSION_NO_LOCK",
                                "market": f"{r.asset} Pyth NO ({eff_hrs:.1f}h sess): {r.question}",
                                "ask_vwap": w_np["eff_px"],
                                "p_model": p_no_p,
                                "net_edge": round(edge_np, 4),
                                "l1_usd": w_np["l1_usd"],
                            })
                        if edge_np >= 0.035 and b2_g["eligible"]:
                            await self.open_shadow_position(
                                sleeve="CM_B2_PYTH_SESSION_NO_LOCK",
                                dedupe_key=f"CMB2_{r.market_id}",
                                asset_or_city=r.asset,
                                title=r.question,
                                side_label="NO",
                                token_id=r.no_token,
                                fee_rate=0.0,
                                p_model=p_no_p,
                                close_ts=r.end_ts,
                                extra={"market_id": r.market_id, "condition_id": r.condition_id, "strike": r.strike, "direction": r.direction, "eff_session_hours": round(eff_hrs, 2)},
                                prefetched_book=bk_n,
                            )

            # CM_SHOCK_PYTH_CATALYST: 0%-fee scheduled NY macro release (08:30 CPI/NFP, 10:30 EIA, 14:00 FOMC) Pyth jump sniper
            prev_sp = self.prev_pyth_spots.get(r.asset, 0.0)
            if in_active_window and exact_ok and same_sess and not already_hit and prev_sp > 0.0:
                sh_ev = evaluate_pyth_catalyst_shock(r.asset, prev_sp, spot_p, r.strike, r.direction, eff_hrs, float(fd["sigma_session"]), now)
                if sh_ev.get("eligible"):
                    sh_side = str(sh_ev["side"])
                    sh_tok = r.yes_token if sh_side == "YES" else r.no_token
                    sh_bk = bk_y if sh_side == "YES" else bk_n
                    w_sh = walk_l2_book_asks(sh_bk.get("asks") or [], BANKROLL_TICKETS["T1000"]["CM_SHOCK_PYTH_CATALYST"], fee_rate=0.0, min_l1_usd=15.0)
                    if w_sh.get("filled") and 0.18 <= float(w_sh["eff_px"]) <= 0.88:
                        sh_edge = float(sh_ev["p_fair"]) - float(w_sh["eff_px"])
                        if sh_edge >= 0.045:
                            opps_out.append({"sleeve": "CM_SHOCK_PYTH_CATALYST", "market": f"{r.asset} [{sh_ev['catalyst']}] {sh_side}: {r.question}", "ask_vwap": w_sh["eff_px"], "p_model": sh_ev["p_fair"], "net_edge": round(sh_edge, 4), "l1_usd": w_sh["l1_usd"], "close_ts": r.end_ts})
                            await self.open_shadow_position(
                                sleeve="CM_SHOCK_PYTH_CATALYST",
                                dedupe_key=f"CMSHK_{r.market_id}_{sh_side}_{int(now // 900)}",
                                asset_or_city=r.asset,
                                title=f"{r.question} [{sh_ev['catalyst']}]",
                                side_label=sh_side,
                                token_id=sh_tok,
                                fee_rate=0.0,
                                p_model=float(sh_ev["p_fair"]),
                                close_ts=r.end_ts,
                                extra={"market_id": r.market_id, "condition_id": r.condition_id, "catalyst": sh_ev["catalyst"], "delta_p": sh_ev["delta_p"], "ret_pct": sh_ev["ret_pct"]},
                                tp_target_px=min(0.95, round(float(w_sh["eff_px"]) + 0.06, 3)),
                                prefetched_book=sh_bk,
                            )

        for a_p, fd_p in feed_by_asset.items():
            self.prev_pyth_spots[a_p] = float(fd_p["spot"])

        all_close_rows: List[Dict[str, Any]] = []
        for rc in near_close:
            bk_y, bk_n = pyth_bks.get(rc.yes_token), pyth_bks.get(rc.no_token)
            if not bk_y or not bk_n:
                continue
            w_qy = walk_l2_book_asks(bk_y.get("asks") or [], 35.0, fee_rate=0.0, min_l1_usd=8.0)
            w_qn = walk_l2_book_asks(bk_n.get("asks") or [], 35.0, fee_rate=0.0, min_l1_usd=8.0)
            all_close_rows.append({
                "asset": rc.asset,
                "strike": rc.strike,
                "is_downward": rc.is_downward,
                "market_id": rc.market_id,
                "condition_id": rc.condition_id,
                "yes_token": rc.yes_token,
                "no_token": rc.no_token,
                "fee_rate": 0.0,
                "ask_yes": w_qy.get("vwap") if w_qy.get("filled") else None,
                "ask_no": w_qn.get("vwap") if w_qn.get("filled") else None,
                "bk_yes": bk_y,
                "bk_no": bk_n,
                "end_ts": rc.end_ts,
            })
            cfg = PYTH_ASSET_CONFIG[rc.asset]
            _, sess_cls, exact_ok, basis_buf, _ = cfg
            fd = feed_by_asset[rc.asset]
            eff_hrs_c = compute_effective_trading_hours(now, rc.end_ts, sess_cls)
            if exact_ok and is_same_continuous_session(now, rc.end_ts, sess_cls) and 0.08 <= eff_hrs_c <= 0.75:
                cl_ev = evaluate_pyth_session_close_lock(float(fd["spot"]), rc.strike, rc.is_downward, eff_hrs_c, float(fd["sigma_session"]), basis_buf)
                if cl_ev["eligible"]:
                    side_c = str(cl_ev["side"])
                    tok_c = rc.yes_token if side_c == "YES" else rc.no_token
                    bk_c = bk_y if side_c == "YES" else bk_n
                    bid_cp, _ = extract_best_bid(bk_c.get("bids") or [])
                    w_cp = walk_l2_book_asks(bk_c.get("asks") or [], 100.0, fee_rate=0.0, min_l1_usd=15.0)
                    if w_cp.get("filled") and 0.78 <= float(w_cp["eff_px"]) <= 0.955 and bid_cp > 0 and (float(w_cp["vwap"]) - bid_cp) <= 0.04:
                        edge_cp = float(cl_ev["p_lock"]) - float(w_cp["eff_px"])
                        if edge_cp >= 0.020:
                            opps_out.append({
                                "sleeve": "CM_U1_PYTH_CLOSE_LOCK",
                                "market": f"{rc.asset} Close Lock ({side_c}, z={cl_ev['z_session']:.2f}): {rc.question}",
                                "ask_vwap": w_cp["eff_px"],
                                "p_model": cl_ev["p_lock"],
                                "net_edge": round(edge_cp, 4),
                                "l1_usd": w_cp["l1_usd"],
                            })
                        if edge_cp >= 0.030:
                            await self.open_shadow_position(
                                sleeve="CM_U1_PYTH_CLOSE_LOCK",
                                dedupe_key=f"CMU1_{rc.market_id}_{side_c}",
                                asset_or_city=rc.asset,
                                title=rc.question,
                                side_label=side_c,
                                token_id=tok_c,
                                fee_rate=0.0,
                                p_model=float(cl_ev["p_lock"]),
                                close_ts=rc.end_ts,
                                extra={"market_id": rc.market_id, "condition_id": rc.condition_id, "strike": rc.strike, "z_session": cl_ev["z_session"]},
                                prefetched_book=bk_c,
                            )

        # 3. CM_B3_PYTH_BARRIER_BOX: Same-Event Monotonicity + Calendar Inclusion + Close-vs-Hit Inclusion (`0%` fee)
        # Also record per-asset TradFi/Commodities/Metals session telemetry (`PYTH_ASSET_SESSION_SNAP`)
        for a_snap, fd_snap in feed_by_asset.items():
            cfg_s = PYTH_ASSET_CONFIG.get(a_snap)
            if not cfg_s:
                continue
            _, sess_s, exact_s, _, _ = cfg_s
            asset_rows = [rh for rh in all_hit_rows if rh["asset"] == a_snap and rh.get("ask_no") is not None]
            if not asset_rows:
                continue
            nearest_r = min(asset_rows, key=lambda x: (float(x["end_ts"]), abs(math.log(float(x["strike"]) / max(1e-6, float(fd_snap["spot"]))))))
            eff_h_s = compute_effective_trading_hours(now, float(nearest_r["end_ts"]), sess_s)
            same_s = is_same_continuous_session(now, float(nearest_r["end_ts"]), sess_s)
            bid_no_s, sz_no_s = extract_best_bid(nearest_r["bk_no"].get("bids") or [])
            ask_no_s, asz_no_s = self._best_ask_sz(nearest_r["bk_no"])
            self._record_market_telemetry(
                key=f"PYTH_SNAP_{a_snap}",
                min_interval_sec=120.0,
                now_ts=now,
                sig=(round(float(fd_snap["spot"]), 3), round(ask_no_s, 3), round(bid_no_s, 3)),
                payload={
                    "type": "PYTH_ASSET_SESSION_SNAP",
                    "asset": a_snap,
                    "session_class": sess_s,
                    "exact_directional_ok": exact_s,
                    "spot": round(float(fd_snap["spot"]), 4),
                    "sigma_session": fd_snap["sigma_session"],
                    "eff_session_hours": round(eff_h_s, 2),
                    "same_session": same_s,
                    "near_strike": nearest_r["strike"],
                    "near_dir": nearest_r["direction"],
                    "near_ask_no": round(ask_no_s, 4) if ask_no_s < 1.0 else None,
                    "near_bid_no": round(bid_no_s, 4) if bid_no_s > 0 else None,
                    "near_ask_l1_usd": round(ask_no_s * asz_no_s, 2) if ask_no_s < 1.0 else 0.0,
                },
            )

        pyth_box_cands: List[Tuple[str, str, Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], float, str]] = []
        for ev_id_p, ev_rows in by_event_hit_rows.items():
            if len(ev_rows) < 2:
                continue
            p_diag = detect_barrier_monotonicity_boxes(ev_rows, fee_rate=0.0, max_box_cost_net=1.15)
            if p_diag:
                pd0 = p_diag[0]
                self._record_market_telemetry(
                    key=f"CMB3_DIAG_{ev_id_p}",
                    min_interval_sec=90.0,
                    now_ts=now,
                    sig=(pd0["direction"], pd0["low_strike"], pd0["high_strike"], pd0["box_cost_net"]),
                    payload={"type": "PYTH_BARRIER_MONO_BEST", "asset": ev_rows[0]["asset"], "event_id": ev_id_p, "net_box_l1": pd0["box_cost_net"], "label": pd0["label"]},
                )
            by_yt = {str(q["yes_token"]): q for q in ev_rows}
            by_nt = {str(q["no_token"]): q for q in ev_rows}
            for ba in p_diag:
                if float(ba["box_cost_net"]) > 1.035:
                    continue
                qy, qn = by_yt.get(ba["yes_token"]), by_nt.get(ba["no_token"])
                if qy and qn:
                    la = {"token_id": ba["yes_token"], "opp_token_id": ba["yes_opp_token"], "condition_id": ba["leg_yes_condition_id"], "side": "YES", "label": f"YES_{ba['direction']}", "market_id": ba["leg_yes_market_id"], "fee_rate": 0.0, "strike": float(qy["strike"])}
                    lb = {"token_id": ba["no_token"], "opp_token_id": ba["no_opp_token"], "condition_id": ba["leg_no_condition_id"], "side": "NO", "label": f"NO_{ba['direction']}", "market_id": ba["leg_no_market_id"], "fee_rate": 0.0, "strike": float(qn["strike"])}
                    pyth_box_cands.append((qy["asset"], f"CMB3_MONO_{ba['leg_yes_market_id']}_{ba['leg_no_market_id']}", la, lb, qy["bk_yes"], qn["bk_no"], float(qy["end_ts"]), f"{qy['asset']} Pyth Box {ba['label']}"))

        cal_diag = detect_pyth_calendar_inclusion_boxes(all_hit_rows, max_box_cost_net=1.15)
        if cal_diag:
            cd0 = cal_diag[0]
            self._record_market_telemetry(
                key=f"CMB3_CAL_BEST_{cd0['asset']}",
                min_interval_sec=90.0,
                now_ts=now,
                sig=(cd0["direction"], cd0["strike"], cd0["box_cost_net"]),
                payload={"type": "PYTH_CALENDAR_BEST", "asset": cd0["asset"], "net_box_l1": cd0["box_cost_net"], "label": cd0["label"]},
            )
        for cal in cal_diag:
            if float(cal["box_cost_net"]) > 1.035:
                continue
            qy, qn = cal["yes_row"], cal["no_row"]
            la = {"token_id": qy["yes_token"], "opp_token_id": qy["no_token"], "condition_id": qy["condition_id"], "side": "YES", "label": "YES_LONG", "market_id": qy["market_id"], "fee_rate": 0.0, "strike": float(qy["strike"])}
            lb = {"token_id": qn["no_token"], "opp_token_id": qn["yes_token"], "condition_id": qn["condition_id"], "side": "NO", "label": "NO_SHORT", "market_id": qn["market_id"], "fee_rate": 0.0, "strike": float(qn["strike"])}
            pyth_box_cands.append((cal["asset"], f"CMB3_CAL_{qy['market_id']}_{qn['market_id']}", la, lb, qy["bk_yes"], qn["bk_no"], float(cal["close_ts"]), f"{cal['asset']} Calendar Box {cal['label']}"))

        cvh_diag = detect_pyth_close_vs_hit_boxes(all_close_rows, all_hit_rows, now_ts=now, max_box_cost_net=1.15)
        if cvh_diag:
            vd0 = cvh_diag[0]
            self._record_market_telemetry(
                key=f"CMB3_CVH_BEST_{vd0['asset']}",
                min_interval_sec=90.0,
                now_ts=now,
                sig=(vd0["strike_hit"], vd0["strike_close"], vd0["box_cost_net"]),
                payload={"type": "PYTH_CLOSE_VS_HIT_BEST", "asset": vd0["asset"], "net_box_l1": vd0["box_cost_net"], "label": vd0["label"]},
            )
        for cvh in cvh_diag:
            if float(cvh["box_cost_net"]) > 1.035:
                continue
            qy, qn = cvh["yes_row"], cvh["no_row"]
            la = {"token_id": qy["yes_token"], "opp_token_id": qy["no_token"], "condition_id": qy["condition_id"], "side": "YES", "label": "YES_HIT", "market_id": qy["market_id"], "fee_rate": 0.0, "strike": float(qy["strike"])}
            lb = {"token_id": qn["no_token"], "opp_token_id": qn["yes_token"], "condition_id": qn["condition_id"], "side": "NO", "label": "NO_CLOSE", "market_id": qn["market_id"], "fee_rate": 0.0, "strike": float(qn["strike"])}
            pyth_box_cands.append((cvh["asset"], f"CMB3_CVH_{qy['market_id']}_{qn['market_id']}", la, lb, qy["bk_yes"], qn["bk_no"], float(cvh["close_ts"]), f"{cvh['asset']} Close-vs-Hit Box {cvh['label']}"))

        for p_asset, p_dkey, la, lb, bk_a, bk_b, c_ts, p_title in pyth_box_cands:
            w_pb = walk_equal_shares_dominance_box(
                bk_a.get("asks") or [],
                bk_b.get("asks") or [],
                target_budget_usd=BANKROLL_TICKETS["T1000"]["CM_B3_PYTH_BARRIER_BOX"],
                fee_rate_a=0.0,
                fee_rate_b=0.0,
                max_box_cost_net=0.994,
                min_shares=6,
                min_box_notional_usd=5.5,
            )
            if w_pb.get("filled"):
                opps_out.append({
                    "sleeve": "CM_B3_PYTH_BARRIER_BOX",
                    "market": p_title,
                    "ask_vwap": round(float(w_pb["box_cost_net"]), 4),
                    "p_model": 1.0,
                    "net_edge": round(1.0 - float(w_pb["box_cost_net"]), 4),
                    "l1_usd": w_pb["l1_usd"],
                    "close_ts": c_ts,
                })
                await self.open_shadow_two_leg_box(
                    sleeve="CM_B3_PYTH_BARRIER_BOX",
                    dedupe_key=p_dkey,
                    asset=p_asset,
                    title=p_title,
                    leg_a=la,
                    leg_b=lb,
                    bk_a=bk_a,
                    bk_b=bk_b,
                    close_ts=c_ts,
                    max_box_cost_net=0.994,
                    extra={"is_pyth_zero_fee_box": True},
                )
                if float(w_pb["box_cost_net"]) <= 0.990 and (c_ts - now) <= 86400.0:
                    self.emit_live_two_leg_box_candidate(
                        sleeve_source="CM_B3_PYTH_BARRIER_BOX",
                        box_type="BARRIER_MONO",
                        asset=p_asset,
                        dedupe_key=p_dkey,
                        leg_a=la,
                        leg_b=lb,
                        bk_a=bk_a,
                        bk_b=bk_b,
                        close_ts=c_ts,
                        now_ts=now,
                        k_low=min(float(la.get("strike") or 100.0), float(lb.get("strike") or 100.0)),
                        k_high=max(float(la.get("strike") or 100.0), float(lb.get("strike") or 100.0)),
                    )
            else:
                self.post_zero_fee_maker_anchor_box("CM_B3", p_asset, f"ZFA_{p_dkey}", la, lb, bk_a, bk_b, c_ts, p_title, now)

        # 4. SP1_NBA_ZERO_FEE_BOX: NBA Full-Game Polish Middle (ML vs +Spread), Spread vs Spread & Total O/U Boxes (`0%` fee)
        for sp_nba in list(self.nba_games.values()):
            if now > sp_nba.tipoff_ts + 6.0 * 3600.0:
                self.nba_games.pop(sp_nba.event_id, None)
                continue
            nba_legs = sp_nba.margin_legs + sp_nba.total_legs
            nba_toks = sorted({lg.token_id for lg in nba_legs})
            if len(nba_toks) < 4:
                continue
            nba_bks = await self.fetch_books_batch(nba_toks, timeout=3.5)
            best_asks_nba: Dict[str, float] = {}
            for t_n, bk_n in nba_bks.items():
                px_n, sz_n = self._best_ask_sz(bk_n)
                if px_n < 1.0 and sz_n * px_n >= 8.0:
                    best_asks_nba[t_n] = px_n
            nba_diag = detect_nba_dominance_boxes(sp_nba, best_asks_nba, max_box_cost_net=1.12)
            if nba_diag:
                nd0 = nba_diag[0]
                lga0, lgb0 = nd0["leg_a"], nd0["leg_b"]
                bka0 = nba_bks.get(lga0.token_id) or {}
                bkb0 = nba_bks.get(lgb0.token_id) or {}
                aa0, sa0 = self._best_ask_sz(bka0)
                ab0, sb0 = self._best_ask_sz(bkb0)
                ba0, _ = extract_best_bid(bka0.get("bids") or [])
                bb0, _ = extract_best_bid(bkb0.get("bids") or [])
                mkr_cands = []
                if ba0 > 0 and (aa0 - ba0) >= 0.02:
                    mkr_cands.append(round(min(ba0 + 0.01, aa0 - 0.01) + ab0, 4))
                if bb0 > 0 and (ab0 - bb0) >= 0.02:
                    mkr_cands.append(round(aa0 + min(bb0 + 0.01, ab0 - 0.01), 4))
                mkr_box_n = min(mkr_cands) if mkr_cands else None
                self._record_market_telemetry(
                    key=f"NBA_BOX_{sp_nba.event_id}",
                    min_interval_sec=45.0,
                    now_ts=now,
                    sig=(nd0["label"], nd0["box_cost_net"], mkr_box_n),
                    payload={
                        "type": "NBA_ZERO_FEE_BOX_BEST",
                        "event_id": sp_nba.event_id,
                        "game": sp_nba.title,
                        "box_kind": nd0["box_kind"],
                        "in_play": bool(now >= sp_nba.tipoff_ts),
                        "sec_from_tipoff": round(now - sp_nba.tipoff_ts, 0),
                        "best_label": nd0["label"],
                        "leg_a_ask": round(aa0, 4),
                        "leg_a_bid": round(ba0, 4) if ba0 > 0 else None,
                        "leg_b_ask": round(ab0, 4),
                        "leg_b_bid": round(bb0, 4) if bb0 > 0 else None,
                        "net_box_l1": nd0["box_cost_net"],
                        "maker_anchor_box_l1": mkr_box_n,
                        "l1_min_usd": round(min(aa0 * sa0, ab0 * sb0), 2),
                        "middle_pts": nd0["middle_width_pts"],
                    },
                )
            for nb in nba_diag:
                if float(nb["box_cost_net"]) > 1.035:
                    continue
                lga, lgb = nb["leg_a"], nb["leg_b"]
                bk_a, bk_b = nba_bks.get(lga.token_id), nba_bks.get(lgb.token_id)
                if not bk_a or not bk_b:
                    continue
                la_n = {"token_id": lga.token_id, "opp_token_id": lga.opp_token_id, "condition_id": lga.condition_id, "side": lga.side_label, "label": lga.display_label, "market_id": lga.market_id, "fee_rate": 0.0, "strike": float(lga.threshold)}
                lb_n = {"token_id": lgb.token_id, "opp_token_id": lgb.opp_token_id, "condition_id": lgb.condition_id, "side": lgb.side_label, "label": lgb.display_label, "market_id": lgb.market_id, "fee_rate": 0.0, "strike": float(lgb.threshold)}
                if float(nb["box_cost_net"]) > 0.994:
                    self.post_zero_fee_maker_anchor_box(
                        "SP1_NBA", "NBA", f"ZFA_SP1_{sp_nba.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",
                        la_n, lb_n, bk_a, bk_b, float(nb["close_ts"]), f"{sp_nba.title} [{nb['label']}]", now,
                    )
                    continue
                w_nba = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["SP1_NBA_ZERO_FEE_BOX"],
                    fee_rate_a=0.0,
                    fee_rate_b=0.0,
                    max_box_cost_net=0.994,
                    min_shares=8,
                    min_box_notional_usd=7.0,
                )
                if w_nba.get("filled"):
                    opps_out.append({
                        "sleeve": "SP1_NBA_ZERO_FEE_BOX",
                        "market": f"NBA {sp_nba.title}: {nb['label']} (mid={nb['middle_width_pts']}pt)",
                        "ask_vwap": round(float(w_nba["box_cost_net"]), 4),
                        "p_model": 1.0,
                        "net_edge": round(1.0 - float(w_nba["box_cost_net"]), 4),
                        "l1_usd": w_nba["l1_usd"],
                        "close_ts": nb["close_ts"],
                    })
                    await self.open_shadow_two_leg_box(
                        sleeve="SP1_NBA_ZERO_FEE_BOX",
                        dedupe_key=f"SP1_{sp_nba.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",
                        asset="NBA",
                        title=f"{sp_nba.title} [{nb['label']}]",
                        leg_a=la_n,
                        leg_b=lb_n,
                        bk_a=bk_a,
                        bk_b=bk_b,
                        close_ts=float(nb["close_ts"]),
                        max_box_cost_net=0.994,
                        extra={"is_nba_zero_fee_box": True, "box_kind": nb["box_kind"], "middle_width_pts": nb["middle_width_pts"]},
                    )
                    if float(w_nba["box_cost_net"]) <= 0.990 and (float(nb["close_ts"]) - now) <= 86400.0:
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="SP1_NBA_ZERO_FEE_BOX",
                            box_type="NBA_DOMINANCE",
                            asset="NBA",
                            dedupe_key=f"SP1_{sp_nba.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",
                            leg_a=la_n,
                            leg_b=lb_n,
                            bk_a=bk_a,
                            bk_b=bk_b,
                            close_ts=float(nb["close_ts"]),
                            now_ts=now,
                        )

        # 5. NR0_ZERO_FEE_SLATE_ARB: Zero-Fee NegRisk Partition Slates (`elon-tweets`, `fomc`, `boj`, `boc`)
        for sp_nr in list(self.negrisk_zero_slates.values()):
            if sp_nr.end_ts <= now + 60:
                self.negrisk_zero_slates.pop(sp_nr.event_id, None)
                continue
            nr_toks = [b["yes_token"] for b in sp_nr.brackets] + [b["no_token"] for b in sp_nr.brackets]
            nr_bks = await self.fetch_books_batch(nr_toks, timeout=3.5)
            if not all(b["yes_token"] in nr_bks and b["no_token"] in nr_bks for b in sp_nr.brackets):
                continue
            y_l1_pairs = [self._best_ask_sz(nr_bks[b["yes_token"]]) for b in sp_nr.brackets]
            n_l1_pairs = [self._best_ask_sz(nr_bks[b["no_token"]]) for b in sp_nr.brackets]
            sum_y = sum(p for p, _ in y_l1_pairs)
            sum_n = sum(p for p, _ in n_l1_pairs)
            min_y_usd = round(min(p * s for p, s in y_l1_pairs), 2)
            min_n_usd = round(min(p * s for p, s in n_l1_pairs), 2)
            sum_y_bids = round(sum(extract_best_bid(nr_bks[b["yes_token"]].get("bids") or [])[0] for b in sp_nr.brackets), 4)
            sum_n_bids = round(sum(extract_best_bid(nr_bks[b["no_token"]].get("bids") or [])[0] for b in sp_nr.brackets), 4)
            n_br = len(sp_nr.brackets)
            self._record_market_telemetry(
                key=f"NR0_SLATE_{sp_nr.event_id}",
                min_interval_sec=60.0,
                now_ts=now,
                sig=(round(sum_y, 3), round(sum_n, 3)),
                payload={
                    "type": "ZERO_FEE_NEGRISK_SLATE",
                    "series": sp_nr.series_slug,
                    "title": sp_nr.title,
                    "tte_sec": round(sp_nr.end_ts - now, 0),
                    "n_open": n_br,
                    "sum_yes_l1": round(sum_y, 4),
                    "sum_yes_bids": sum_y_bids,
                    "min_yes_l1_usd": min_y_usd,
                    "sum_no_l1": round(sum_n, 4),
                    "sum_no_bids": sum_n_bids,
                    "min_no_l1_usd": min_n_usd,
                    "no_payout": n_br - 1,
                },
            )
            if sum_y <= 0.990:
                legs_y = [{"token_id": b["yes_token"], "side": "YES", "label": f"YES[{b['label']}]", "market_id": b["market_id"], "fee_rate": float(b.get("fee_rate", 0.0))} for b in sp_nr.brackets]
                w_nry = walk_equal_shares_multi_leg_box(
                    [{"asks": nr_bks[b["yes_token"]].get("asks") or [], "fee_rate": float(b.get("fee_rate", 0.0)), "fee_exponent": float(b.get("fee_exponent", 1.0))} for b in sp_nr.brackets],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],
                    guaranteed_payout_per_bundle=1.0,
                    max_bundle_cost_net=0.988,
                    min_shares=6,
                    min_box_notional_usd=5.5,
                )
                if w_nry.get("filled"):
                    opps_out.append({"sleeve": "NR0_ZERO_FEE_SLATE_ARB", "market": f"{sp_nr.title} (ALL {n_br} YES)", "ask_vwap": round(float(w_nry["box_cost_net"]), 4), "p_model": 1.0, "net_edge": round(1.0 - float(w_nry["box_cost_net"]), 4), "l1_usd": w_nry["l1_usd"], "close_ts": sp_nr.end_ts})
                    await self.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB", f"NR0_Y_{sp_nr.event_id}", sp_nr.series_slug.upper(), f"{sp_nr.title} [All-YES Partition]", legs_y, nr_bks, sp_nr.end_ts, 1.0, 0.988, {"is_multi_leg_bundle": True, "guaranteed_payout": 1.0})
            elif sum_n <= (n_br - 1) - 0.010:
                gp_n = float(n_br - 1)
                legs_n = [{"token_id": b["no_token"], "side": "NO", "label": f"NO[{b['label']}]", "market_id": b["market_id"], "fee_rate": float(b.get("fee_rate", 0.0))} for b in sp_nr.brackets]
                w_nrn = walk_equal_shares_multi_leg_box(
                    [{"asks": nr_bks[b["no_token"]].get("asks") or [], "fee_rate": float(b.get("fee_rate", 0.0)), "fee_exponent": float(b.get("fee_exponent", 1.0))} for b in sp_nr.brackets],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["NR0_ZERO_FEE_SLATE_ARB"],
                    guaranteed_payout_per_bundle=gp_n,
                    max_bundle_cost_net=round(gp_n - 0.012, 4),
                    min_shares=6,
                    min_box_notional_usd=5.5,
                )
                if w_nrn.get("filled"):
                    opps_out.append({"sleeve": "NR0_ZERO_FEE_SLATE_ARB", "market": f"{sp_nr.title} (ALL {n_br} NO)", "ask_vwap": round(float(w_nrn["box_cost_net"]) / gp_n, 4), "p_model": 1.0, "net_edge": round((gp_n - float(w_nrn["box_cost_net"])) / gp_n, 4), "l1_usd": w_nrn["l1_usd"], "close_ts": sp_nr.end_ts})
                    await self.open_shadow_multi_leg_bundle("NR0_ZERO_FEE_SLATE_ARB", f"NR0_N_{sp_nr.event_id}", sp_nr.series_slug.upper(), f"{sp_nr.title} [All-NO Partition]", legs_n, nr_bks, sp_nr.end_ts, gp_n, round(gp_n - 0.012, 4), {"is_multi_leg_bundle": True, "guaranteed_payout": gp_n})
            if sum_y_bids >= 1.004:
                await self.execute_ctf_overround_mint_sell(
                    dedupe_key=f"CTF_OVR_NR_{sp_nr.event_id}",
                    asset=sp_nr.series_slug.upper(),
                    title=f"{sp_nr.title} NegRisk Overround Mint-Sell",
                    legs_bids_spec=[
                        {"bids": nr_bks[b["yes_token"]].get("bids") or [], "fee_rate": float(b.get("fee_rate", 0.0)), "fee_exponent": float(b.get("fee_exponent", 1.0))}
                        for b in sp_nr.brackets
                    ],
                    close_ts=sp_nr.end_ts,
                    min_net_proceeds_per_set=1.004,
                    opps_out=opps_out,
                    extra={"overround_kind": "NEGRISK_SLATE", "series": sp_nr.series_slug, "event_id": sp_nr.event_id},
                )

        # 6. Phase-2 Macro LP (`FED1`), Oil-Senate (`COND1`), Counting (`TW1` + `MKR_REWARD`), & AAA Gas (`GAS1`)
        await self._scan_phase2_macro_counting_gas(opps_out, now)

    async def _scan_phase2_macro_counting_gas(self, opps_out: List[Dict[str, Any]], now: float) -> None:
        # 6A. `TW1_COUNTING_TRUNCATION_AND_BOX` + `MKR_REWARD_LOCKED_CARRY`
        active_cnt = [s for s in self.counting_slates.values() if s.window_end_ts > now + 60]
        if active_cnt:
            handles = sorted({s.handle for s in active_cnt})
            xt_res = await asyncio.gather(*(asyncio.to_thread(fetch_xtracker_user_stats_sync, h) for h in handles))
            xt_by_handle = dict(zip(handles, xt_res))
            cnt_toks = [t for s in active_cnt for b in s.brackets for t in (b.yes_token, b.no_token)]
            cnt_bks = await self.fetch_books_batch(cnt_toks, timeout=3.5)
            best_asks_cnt: Dict[str, float] = {}
            for t_c, bk_c in cnt_bks.items():
                px_c, sz_c = self._best_ask_sz(bk_c)
                if px_c < 1.0 and px_c * sz_c >= 8.0:
                    best_asks_cnt[t_c] = px_c
            for sl_c in active_cnt:
                v_floor, dead_brs = evaluate_counting_dead_no_locks(sl_c, xt_by_handle.get(sl_c.handle) or {})
                self._record_market_telemetry(
                    key=f"TW1_SNAP_{sl_c.event_id}",
                    min_interval_sec=120.0,
                    now_ts=now,
                    sig=(v_floor, len(dead_brs)),
                    payload={"type": "COUNTING_TRACKER_SNAP", "slug": sl_c.slug, "handle": sl_c.handle, "verified_floor": v_floor, "dead_open_brackets": len(dead_brs), "tte_sec": round(sl_c.window_end_ts - now, 0)},
                )
                for dbr in dead_brs:
                    bk_dno = cnt_bks.get(dbr.no_token)
                    if not bk_dno:
                        continue
                    bid_dn, _ = extract_best_bid(bk_dno.get("bids") or [])
                    ask_dn, _ = self._best_ask_sz(bk_dno)
                    w_dno = walk_l2_book_asks(bk_dno.get("asks") or [], BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"], fee_rate=0.0, min_l1_usd=15.0, max_ask_px=0.990)
                    if w_dno.get("filled") and 0.80 <= float(w_dno["eff_px"]) <= 0.990:
                        edg_tw = round(1.0 - float(w_dno["eff_px"]), 4)
                        if edg_tw >= 0.010:
                            opps_out.append({"sleeve": "TW1_COUNTING_TRUNCATION_AND_BOX", "market": f"{sl_c.handle} Dead Bracket NO[{dbr.label}] (count>={v_floor})", "ask_vwap": w_dno["eff_px"], "p_model": 1.0, "net_edge": edg_tw, "l1_usd": w_dno["l1_usd"], "close_ts": sl_c.window_end_ts})
                            await self.open_shadow_position("TW1_COUNTING_TRUNCATION_AND_BOX", f"TW1_NO_{dbr.market_id}", sl_c.handle.upper(), f"{sl_c.title} [Dead NO {dbr.label}]", "NO", dbr.no_token, 0.0, 1.0, sl_c.window_end_ts, {"market_id": dbr.market_id, "condition_id": dbr.condition_id, "verified_floor": v_floor}, prefetched_book=bk_dno)
                    rw_ev = evaluate_locked_market_reward_carry(1.0, bid_dn, ask_dn, dbr.rewards_min_size, dbr.rewards_max_spread, 0.0)
                    if rw_ev.get("eligible"):
                        opps_out.append({"sleeve": "MKR_REWARD_LOCKED_CARRY", "market": f"{sl_c.handle} Locked Carry NO[{dbr.label}] @ ${rw_ev['resting_bid']:.3f}", "ask_vwap": rw_ev["resting_bid"], "p_model": 1.0, "net_edge": rw_ev["carry_edge"], "l1_usd": 50.0, "close_ts": sl_c.window_end_ts})
                        await self.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY", f"MKR_RW_{dbr.market_id}", sl_c.handle.upper(), f"{sl_c.title} [Reward Carry NO {dbr.label}]", "NO", dbr.no_token, 1.0, sl_c.window_end_ts, {"market_id": dbr.market_id, "condition_id": dbr.condition_id, "resting_bid_override": rw_ev["resting_bid"]}, prefetched_book=bk_dno)

            tw_boxes = detect_counting_subwindow_boxes(active_cnt, best_asks_cnt, xt_by_handle, max_box_cost_net=1.05)
            if tw_boxes:
                tb0 = tw_boxes[0]
                self._record_market_telemetry(f"TW1_BOX_{tb0['handle']}", 90.0, {"type": "COUNTING_SUBWINDOW_BEST", "handle": tb0["handle"], "net_box_l1": tb0["box_cost_net"], "label": tb0["label"]}, now_ts=now, sig=(tb0["label"], tb0["box_cost_net"]))
            for tb in tw_boxes:
                la_t, lb_t = tb["leg_a"], tb["leg_b"]
                bka_t, bkb_t = cnt_bks.get(la_t["token_id"]), cnt_bks.get(lb_t["token_id"])
                if not bka_t or not bkb_t:
                    continue
                dk_tw = f"TW1_BOX_{la_t['market_id']}_{lb_t['market_id']}"
                if float(tb["box_cost_net"]) <= 0.993:
                    w_tb = walk_equal_shares_dominance_box(bka_t.get("asks") or [], bkb_t.get("asks") or [], BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"], 0.0, 0.0, max_box_cost_net=0.993, min_shares=6, min_box_notional_usd=5.5)
                    if w_tb.get("filled"):
                        opps_out.append({"sleeve": "TW1_COUNTING_TRUNCATION_AND_BOX", "market": f"Counting Box {tb['label']}", "ask_vwap": w_tb["box_cost_net"], "p_model": 1.0, "net_edge": round(1.0 - float(w_tb["box_cost_net"]), 4), "l1_usd": w_tb["l1_usd"], "close_ts": tb["close_ts"]})
                        await self.open_shadow_two_leg_box("TW1_COUNTING_TRUNCATION_AND_BOX", dk_tw, tb["handle"].upper(), f"Counting Box {tb['label']}", la_t, lb_t, bka_t, bkb_t, float(tb["close_ts"]), 0.993, {"is_two_leg_box": True, "banked": tb["banked"]})
                elif float(tb["box_cost_net"]) <= 1.035:
                    self.post_zero_fee_maker_anchor_box("TW1", tb["handle"].upper(), f"ZFA_{dk_tw}", la_t, lb_t, bka_t, bkb_t, float(tb["close_ts"]), f"Counting Box {tb['label']}", now)

        # 6B. `FED1_CENTRAL_BANK_LP_BOX` (125-state FOMC) & `COND1_MACRO_PARTITION_BOX` (9-state Oil x Senate)
        lp_legs = [lg for lg in (self.fomc_truth_legs + self.oil_senate_truth_legs) if float(lg["end_ts"]) > now + 60]
        if lp_legs:
            lp_bks = await self.fetch_books_batch(sorted({str(lg["token_id"]) for lg in lp_legs}), timeout=3.5)
            lp_asks = {t: p for t, bk in lp_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
            for sl_lp, asset_lp, legs_src, mask_all, t_type in (
                ("FED1_CENTRAL_BANK_LP_BOX", "FOMC", self.fomc_truth_legs, ALL_FOMC_MASK, "FOMC_LP_BEST"),
                ("COND1_MACRO_PARTITION_BOX", "OIL_SENATE", self.oil_senate_truth_legs, ALL_OIL_SENATE_MASK, "OIL_SENATE_PARTITION_BEST"),
            ):
                if not legs_src:
                    continue
                bx_list = find_cross_event_bitmask_boxes(legs_src, lp_asks, mask_all, max_2leg_cost=1.05, max_3leg_cost=1.03)
                if bx_list:
                    b0 = bx_list[0]
                    self._record_market_telemetry(f"{t_type}_DIAG", 90.0, {"type": t_type, "n_legs": b0["n_legs"], "net_box_l1": b0["box_cost_net"], "label": b0["label"]}, now_ts=now, sig=(b0["label"], b0["box_cost_net"]))
                for bx in bx_list:
                    lgs = bx["legs"]
                    if int(bx["n_legs"]) == 2:
                        la_m, lb_m = lgs[0], lgs[1]
                        bka_m, bkb_m = lp_bks.get(la_m["token_id"]), lp_bks.get(lb_m["token_id"])
                        if not bka_m or not bkb_m:
                            continue
                        dk_m = f"{asset_lp}_2L_{la_m['token_id'][-8:]}_{lb_m['token_id'][-8:]}"
                        if float(bx["box_cost_net"]) <= 0.994:
                            wm2 = walk_equal_shares_dominance_box(bka_m.get("asks") or [], bkb_m.get("asks") or [], BANKROLL_TICKETS["T1000"][sl_lp], 0.0, 0.0, max_box_cost_net=0.994, min_shares=6, min_box_notional_usd=5.5)
                            if wm2.get("filled"):
                                opps_out.append({"sleeve": sl_lp, "market": f"{asset_lp} {bx['label']}", "ask_vwap": wm2["box_cost_net"], "p_model": 1.0, "net_edge": round(1.0 - float(wm2["box_cost_net"]), 4), "l1_usd": wm2["l1_usd"], "close_ts": bx["close_ts"]})
                                await self.open_shadow_two_leg_box(sl_lp, dk_m, asset_lp, f"{asset_lp} {bx['label']}", la_m, lb_m, bka_m, bkb_m, float(bx["close_ts"]), 0.994, {"is_two_leg_box": True, "double_pay_states": bx["double_pay_states"]})
                        elif float(bx["box_cost_net"]) <= 1.035:
                            self.post_zero_fee_maker_anchor_box(asset_lp, asset_lp, f"ZFA_{dk_m}", la_m, lb_m, bka_m, bkb_m, float(bx["close_ts"]), f"{asset_lp} {bx['label']}", now)
                    elif int(bx["n_legs"]) == 3 and float(bx["box_cost_net"]) <= 0.992:
                        dk_3 = f"{asset_lp}_3L_{'_'.join(x['token_id'][-6:] for x in lgs)}"
                        wm3 = walk_equal_shares_multi_leg_box([{"asks": lp_bks[x["token_id"]].get("asks") or [], "fee_rate": 0.0, "fee_exponent": 1.0} for x in lgs], BANKROLL_TICKETS["T1000"][sl_lp], 1.0, 0.992, min_shares=6, min_box_notional_usd=5.5)
                        if wm3.get("filled"):
                            opps_out.append({"sleeve": sl_lp, "market": f"{asset_lp} 3-Leg {bx['label']}", "ask_vwap": wm3["box_cost_net"], "p_model": 1.0, "net_edge": round(1.0 - float(wm3["box_cost_net"]), 4), "l1_usd": wm3["l1_usd"], "close_ts": bx["close_ts"]})
                            await self.open_shadow_multi_leg_bundle(sl_lp, dk_3, asset_lp, f"{asset_lp} 3-Leg {bx['label']}", lgs, lp_bks, float(bx["close_ts"]), 1.0, 0.992, {"is_multi_leg_bundle": True, "guaranteed_payout": 1.0})

        # 6C. `GAS1_AAA_GASOLINE_LOCK`: Same-day published 4-decimal AAA National Regular lock
        daily_gas_evs = [e for e in (self.gas_events_raw.get("us-gas-price-daily") or []) if not e.get("closed")]
        if daily_gas_evs:
            aaa = await asyncio.to_thread(fetch_aaa_national_gas_sync)
            if aaa:
                self._record_market_telemetry("AAA_GAS_SNAP", 300.0, {"type": "AAA_GAS_SNAP", **aaa}, now_ts=now, sig=(aaa["as_of_date"], aaa["current_regular"]))
                reg_px = float(aaa["current_regular"])
                for ev_g in daily_gas_evs:
                    end_g = _parse_iso_ts(ev_g.get("endDate")) or 0.0
                    if not (60.0 < (end_g - now) <= 57600.0):
                        continue
                    mkt_dt = datetime.fromtimestamp(end_g, tz=NY_TZ).date().isoformat()
                    if mkt_dt != aaa["as_of_date"]:
                        continue
                    g_brs = []
                    for mg in (ev_g.get("markets") or []):
                        if mg.get("closed"):
                            continue
                        fr_g, _ = _extract_market_fee_rate(mg)
                        tk_g = _parse_clob_tokens(mg)
                        bd_g = parse_gas_daily_bracket(str(mg.get("groupItemTitle") or mg.get("question") or ""))
                        if fr_g == 0.0 and tk_g and bd_g:
                            g_brs.append((mg, tk_g, bd_g))
                    if not g_brs:
                        continue
                    g_bks = await self.fetch_books_batch([t for _, tk, _ in g_brs for t in tk], timeout=3.0)
                    for mg, tk_g, (glo, ghi) in g_brs:
                        mid_g = str(mg.get("id") or "")
                        lbl_g = str(mg.get("groupItemTitle") or "")
                        if (glo == 0.0 or reg_px >= glo + 0.0015) and (not math.isfinite(ghi) or reg_px <= ghi - 0.0015):
                            side_g, tok_g = "YES", tk_g[0]
                        elif reg_px <= glo - 0.0020 or (math.isfinite(ghi) and reg_px >= ghi + 0.0020):
                            side_g, tok_g = "NO", tk_g[1]
                        else:
                            continue
                        bk_g = g_bks.get(tok_g)
                        if not bk_g:
                            continue
                        wg = walk_l2_book_asks(bk_g.get("asks") or [], BANKROLL_TICKETS["T1000"]["GAS1_AAA_GASOLINE_LOCK"], fee_rate=0.0, min_l1_usd=15.0, max_ask_px=0.985)
                        if wg.get("filled") and 0.75 <= float(wg["eff_px"]) <= 0.983:
                            opps_out.append({"sleeve": "GAS1_AAA_GASOLINE_LOCK", "market": f"AAA Gas ${reg_px:.4f} ({aaa['as_of_date']}) -> {side_g}[{lbl_g}]", "ask_vwap": wg["eff_px"], "p_model": 0.998, "net_edge": round(0.998 - float(wg["eff_px"]), 4), "l1_usd": wg["l1_usd"], "close_ts": end_g})
                            await self.open_shadow_position("GAS1_AAA_GASOLINE_LOCK", f"GAS1_{mid_g}_{side_g}", "AAA_GAS", f"{ev_g.get('title')} [{side_g} {lbl_g}]", side_g, tok_g, 0.0, 0.998, end_g, {"market_id": mid_g, "aaa_price": reg_px, "as_of_date": aaa["as_of_date"]}, prefetched_book=bk_g)

    async def _run_bg_tradfi_sports(self) -> None:
        try:
            ts_opps: List[Dict[str, Any]] = []
            await self.scan_tradfi_and_sports_markets(ts_opps)
            self.cached_tradfi_sports_opps = ts_opps
        except Exception as exc:
            logger.warning(f"Background TradFi/Sports scan notice: {exc}")

    async def run_forever(self) -> None:
        logger.info(
            "Starting Polymarket Alpha-124 Unified Shadow Daemon "
            "(W1/W3 + Asian METAR + B1/B2 + M3/N1 NegRisk + U1 Daily + D1/4h/QuietBook + S5M + P1 PreOpen + S2)..."
        )
        try:
            if not self.single_scan and (self._bg_clob_ws_task is None or self._bg_clob_ws_task.done()):
                self._bg_clob_ws_task = asyncio.create_task(self._run_clob_d1_ws_loop())
            if not self.single_scan and self._chainlink_ws is not None and (self._bg_chainlink_ws_task is None or self._bg_chainlink_ws_task.done()):
                self._bg_chainlink_ws_task = asyncio.create_task(self._chainlink_ws.run_forever())
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

                    ts_opps: List[Dict[str, Any]] = []
                    await self.scan_tradfi_and_sports_markets(ts_opps)
                    self.cached_tradfi_sports_opps = ts_opps
                else:
                    # Non-blocking background coroutines so S2 (3.0s) / D1 (3.5s) never stall
                    if (t0 - self.last_crypto_mid_scan_ts) >= 18.0 and (
                        self._bg_mid_task is None or self._bg_mid_task.done()
                    ):
                        self.last_crypto_mid_scan_ts = t0
                        self._bg_mid_task = asyncio.create_task(self._run_bg_mid_crypto())

                    if (t0 - self.last_tradfi_sports_scan_ts) >= 45.0 and (
                        self._bg_tradfi_task is None or self._bg_tradfi_task.done()
                    ):
                        self.last_tradfi_sports_scan_ts = t0
                        self._bg_tradfi_task = asyncio.create_task(self._run_bg_tradfi_sports())

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
                    + self.cached_tradfi_sports_opps
                    + self.cached_weather_opps
                )

                await self.manage_pending_maker_orders()
                await self.manage_pending_zero_fee_maker_anchors()
                await self.manage_open_positions()
                await self.write_state_files_async(opps)

                logger.info(
                    f"[Cycle {self.cycle_count}] BTC=${self.spots.get('BTC',0):,.1f} ETH=${self.spots.get('ETH',0):,.1f} | "
                    f"Monitored(W={len(self.weather_events)}, B={len(self.barrier_rungs)}, M={len(self.strike_ladders)}, "
                    f"NR={len(self.negrisk_ladders)}, PythH={len(self.pyth_barrier_rungs)}, PythC={len(self.pyth_close_ladders)}, "
                    f"NBA={len(self.nba_games)}, NR0={len(self.negrisk_zero_slates)}, TW={len(self.counting_slates)}, "
                    f"FOMC={len(self.fomc_truth_legs)//2}, OS={len(self.oil_senate_truth_legs)//2}, D2={len(self.hourly_12pm_markets)}, "
                    f"U1={len(self.daily_updown_markets)}, D={len(self.dominance_pairs)}, "
                    f"D4h={len(self.dominance_4h_pairs)}, S5m={len(self.s5m_candles)}, P1={len(self.preopen_15m_candles)}, S2={len(self.twap_candles)}) | "
                    f"MakerPend={len(self.pending_maker_orders)} ZFAncPend={len(self.pending_zero_fee_maker_anchors)} PreOpenPend={len(self.pending_preopen_straddles)} "
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
                    ws_triggered = self._ws_d1_wakeup.is_set()
                    if ws_triggered:
                        self._ws_d1_wakeup.clear()
                    # Event-driven (<=120ms on CLOB WS delta, 500ms fallback) D1 overlap box scan without state-file churn
                    min_d1_gap = 0.12 if ws_triggered else 0.50
                    if self.is_in_same_oracle_overlap_window(now_s) and (now_s - last_fast_d1_subscan) >= min_d1_gap:
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
                        prev_mkr_keys = set(self.pending_maker_orders)
                        prev_open_n = len(self.open_positions)
                        s_opps: List[Dict[str, Any]] = []
                        await self.handle_shock_triggers(shocks_w, s_opps, now_ts=now_s)
                        if s_opps:
                            self.cached_shock_opps = s_opps
                        if s_opps or set(self.pending_maker_orders) != prev_mkr_keys or len(self.open_positions) != prev_open_n:
                            await self.write_state_files_async(
                                twap_opps
                                + dom_opps
                                + s5m_opps
                                + p1_opps
                                + self.cached_shock_opps
                                + self.cached_mid_opps
                                + self.cached_tradfi_sports_opps
                                + self.cached_weather_opps
                            )
                    # Step down cadence immediately if we just entered the final-55s TWAP lock window
                    if target_cadence > 3.0 and self.is_in_exact_twap_lock_window(now_s):
                        break
                    wait_cap = min(0.20, max(0.03, deadline - time.time()))
                    try:
                        await asyncio.wait_for(self._ws_d1_wakeup.wait(), timeout=wait_cap)
                    except asyncio.TimeoutError:
                        pass
        finally:
            for bg_t in (self._bg_chainlink_ws_task, self._bg_clob_ws_task, self._bg_discovery_task, self._bg_mid_task, self._bg_tradfi_task, self._bg_weather_task):
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
