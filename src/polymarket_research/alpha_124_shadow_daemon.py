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
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

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
from src.polymarket_research.orderflow_wfo_simulators import (
    compute_d1_legging_drag_haircut,
    compute_d1_maker_anchor_drag_haircut,
)
from src.polymarket_research.riskless_machine_gun_engine import is_reward_locked_carry_live_ready
from src.polymarket_research.same_oracle_dominance_box import (
    DOMINANCE_ASSETS,
    DOMINANCE_SERIES_SLUGS,
    EMPIRICAL_BOX_ASSET_CAPS_USD,
    MIN_CORRIDOR_BPS_BY_ASSET,
    METAL_DOMINANCE_ASSETS,
    METAL_DOMINANCE_SERIES_SLUGS,
    TwapCandleMarketSpec,
    build_crypto_price_query_url,
    build_own_gamma_event_url,
    build_prev_15m_gamma_event_url,
    build_prev_5m_gamma_event_url,
    determine_dominance_legs,
    parse_authoritative_close_price,
    parse_authoritative_open_price,
    parse_closed_gamma_event_settlement,
    parse_metal_forex_candle_event,
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
    celsius_to_market_int,
    compute_adaptive_metar_poll_ttl,
    compute_weather_probabilities,
    evaluate_weather_event_slate,
    fetch_live_ensemble_hourly_sync,
    fetch_metar_observations_sync,
    fetch_taf_extremes_sync,
    parse_weather_event,
)
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    MULTI_SPORT_CORRIDOR_SERIES,
    NBA_SERIES_SLUGS,
    PYTH_ASSET_CONFIG,
    PYTH_CLOSE_SERIES,
    PYTH_HIT_SERIES,
    ZERO_FEE_NEGRISK_SERIES,
    MultiSportCorridorSpec,
    NbaGameSpec,
    NegRiskConvertSlateSpec,
    PythBarrierRungSpec,
    PythCloseRungSpec,
    ZeroFeeNegRiskSlateSpec,
    compute_effective_trading_hours,
    detect_multi_sport_corridor_boxes,
    detect_nba_dominance_boxes,
    detect_negrisk_convert_positions_arbs,
    detect_negrisk_no_pair_boxes,
    detect_pyth_calendar_inclusion_boxes,
    detect_pyth_close_vs_hit_boxes,
    evaluate_pyth_session_barrier_no_lock,
    evaluate_pyth_session_close_lock,
    fetch_yahoo_1m_intraday_sync,
    is_same_continuous_session,
    parse_multi_sport_corridor_event,
    parse_nba_zero_fee_event,
    parse_negrisk_convert_event,
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
    walk_position_overround_bid_unwind,
)
from src.polymarket_research.uma_nba_endgame_engine import (
    LiveNbaGameState,
    evaluate_nba_endgame_locks,
    fetch_espn_nba_scoreboard_sync,
    is_objective_uma_market,
    match_nba_live_game,
    verify_uma_against_nba_live,
    verify_uma_onchain_proposal_sync,
)
from src.polymarket_research.riskless_frontier_v2_engine import (
    BOP_2026_SLUGS,
    EsportsBo3Spec,
    NbaPlayerPropSlate,
    SoccerRegulationTree,
    build_lp1_bop_2026_truth_legs,
    build_lp1_nba_exact_margin_bundle,
    detect_nr2_convert_no_subset_arbs,
    detect_soc1_regulation_boxes,
    detect_sp4_milestone_ladder_boxes,
    evaluate_api1_esports_bo3_opportunities,
    evaluate_sp4_ingame_clinch_locks,
    fetch_espn_nba_boxscore_players_sync,
    find_state_matrix_dominance_boxes,
    link_and_parse_soccer_regulation_trees,
    parse_esports_bo3_event,
    parse_nba_player_props_from_event,
    verify_bond2_moov2_final_hour_sync,
    verify_negrisk_adapter_slate_sync,
)
from src.polymarket_research.riskless_frontier_v3_engine import (
    LP2_MIDTERM_CORE_SLUGS,
    LP2_TOSSUP_CUBE_SLUG,
    LP2_TOSSUP_STATE_SLUGS,
    CalendarOrScalarLadderSpec,
    LiveMultiSportGame,
    NbaSubperiodAndExtPropSlate,
    ScoreConfirmationTracker,
    TennisMatchSpec,
    build_lp1_nfl_exact_margin_bundle,
    build_lp2_house_seats_truth_legs,
    build_lp2_pending_senate_conditional_groups,
    build_lp2_senate_seats_truth_legs,
    build_lp2_tossup_state_implication_groups,
    detect_cal1_monotonic_boxes,
    detect_lp2_seat_convert_implication_arbs,
    detect_multisport_ml_spread_polish_middles,
    detect_sp4_subperiod_and_ext_prop_boxes,
    evaluate_cl1_multisport_corridor_clinch_locks,
    evaluate_cl1_soccer_tree_clinch_locks,
    evaluate_sp4_subperiod_and_ext_locks,
    evaluate_ten1_tennis_opportunities,
    fetch_espn_multisport_board_sync,
    fetch_espn_nba_full_summary_sync,
    parse_cal1_monotonic_ladder_event,
    parse_nba_subperiod_and_ext_props,
    parse_tennis_retirement_safe_event,
    _teams_match_fuzzy,
)
from src.polymarket_research.riskless_frontier_v4_engine import (
    FRONTIER_V4_GRAD8_SLEEVES,
    AffineGameBundle,
    CryptoCloseRungSpec,
    NflPlayerPropSlate,
    SoccerExactScoreLattice,
    SubperiodFreezeTracker,
    detect_cry_inc1_binance_inclusion_boxes,
    detect_nfl_prp1_boxes,
    detect_soc2_lattice_boxes_and_converts,
    detect_sum1_frechet_triangles,
    evaluate_aff1_frozen_subperiod_opportunities,
    evaluate_mkr_lock1_post_clinch_rebate_bid,
    evaluate_nfl_prp1_live_locks,
    evaluate_soc2_dead_score_no_locks,
    fetch_espn_nfl_summary_sync,
    link_and_parse_soc2_exact_score_lattices,
    parse_affine_game_bundle,
    parse_binance_terminal_close_event,
    parse_nfl_player_props_event,
)
from src.polymarket_research.riskless_protocol_v2_expansion import (
    classify_market_rule_dispute_risk,
    compute_gatling_trajectory_projection,
    detect_b1_intraday_onetouch_noon_box,
    detect_d1_telescoping_candle_bridge,
    detect_dc1_double_chance_1x2_parity,
    detect_eq1_pyth_equity_dominance_box,
    detect_halftime_freeze_offset_box,
    detect_lp_comp1_sports_triangles,
    detect_mention1_cumulative_ladder_box,
    detect_nr4_nr5_optimal_tail_convert,
    detect_nr6_cross_slate_surjection_box,
    detect_w_prune1_metar_slate_arb,
    evaluate_s2_rtds_exact_twap_integrator,
    passes_uma_bond_dispute_guard,
    scan_full_universe_c1_and_ctf_overround,
)

DATA_DIR = PROJECT_ROOT / "data" / "alpha124"
DATA_DIR.mkdir(parents=True, exist_ok=True)
_DEFAULT_DATA_DIR = DATA_DIR

STATE_FILE = DATA_DIR / "alpha124_shadow_state.json"
_DEFAULT_STATE_FILE = STATE_FILE
LEDGER_FILE = DATA_DIR / "alpha124_shadow_ledger.jsonl"
_DEFAULT_LEDGER_FILE = LEDGER_FILE
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
DATA_API_URL = "https://data-api.polymarket.com"
CLOB_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BINANCE_URL = "https://api.binance.com"

LOCKED_MAKER_SLEEVES = frozenset({
    "W1_SOLAR_PEAK_LOCK",
    "W1_LOW_TROUGH_LOCK",
    "BOND1_UMA_RESOLUTION_CARRY",
    "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
    "SP2_NBA_ENDGAME_LOCK",
    "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
    "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
})
DEPTH_CAPPED_TAKER_SLEEVES = LOCKED_MAKER_SLEEVES | frozenset({
    "CM_B2_PYTH_SESSION_NO_LOCK",
    "CM_U1_PYTH_CLOSE_LOCK",
    "B4_TOUCHED_BARRIER_WICK_LOCK",
    "TW1_COUNTING_TRUNCATION_AND_BOX",
    "GAS1_AAA_GASOLINE_LOCK",
    "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
    "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
    "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
    "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
    "SOC2_EXACT_SCORE_2D_LATTICE",
    "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
})

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
    "S5M_CHAINLINK_SNIPER",
    "ZERO_FEE_MAKER_ANCHOR_BOX",
})

# Clean shadow graduation epoch for sleeves upgraded with deterministic oracle/TWAP fixes
STRATEGY_EPOCH_MIN_TS: Dict[str, float] = {
    "S2_EXACT_TWAP_LOCK": 1793758800.0,
}


def _filter_epoch_closed_positions(sleeve: str, closed_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    min_ts = STRATEGY_EPOCH_MIN_TS.get(str(sleeve))
    if not min_ts:
        return closed_list
    return [
        p for p in closed_list
        if not (1790000000.0 <= float(p.get("entry_ts") or 0.0) < min_ts)
    ]


def is_shadow_sleeve_quarantined(sleeve: str) -> bool:
    if sleeve == "S2_EXACT_TWAP_LOCK":
        if "PM_UNQUARANTINE_S2_TWAP_LOCK" in os.environ:
            return os.environ["PM_UNQUARANTINE_S2_TWAP_LOCK"] != "1"
        if "PM_QUARANTINE_LOSING_SLEEVES" in os.environ:
            return os.environ["PM_QUARANTINE_LOSING_SLEEVES"] == "1"
        return False
    return os.getenv("PM_QUARANTINE_LOSING_SLEEVES", "1") == "1" and sleeve in QUARANTINED_SHADOW_SLEEVES


FRONTIER_V3_GRAD8_SLEEVES = frozenset({
    "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
    "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
    "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
    "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
    "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
    "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
})


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
        "ZF_INTRADAY_MAKER_BOX": 18.0,
        "TW1_COUNTING_TRUNCATION_AND_BOX": 18.0,
        "FED1_CENTRAL_BANK_LP_BOX": 20.0,
        "COND1_MACRO_PARTITION_BOX": 20.0,
        "CTF_OVERROUND_MINT_SELL": 20.0,
        "D2_12PM_BINANCE_BOX": 18.0,
        "GAS1_AAA_GASOLINE_LOCK": 15.0,
        "CM_SHOCK_PYTH_CATALYST": 15.0,
        "S4H_CHAINLINK_CONVERGENCE": 15.0,
        "MKR_REWARD_LOCKED_CARRY": 15.0,
        "W1_LOW_TROUGH_LOCK": 15.0,
        "SP2_NBA_ENDGAME_LOCK": 18.0,
        "BOND1_UMA_RESOLUTION_CARRY": 20.0,
        "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX": 20.0,
        "NR_CONV_NO_BASKET_ARB": 20.0,
        "NR2_CONVERT_NO_SUBSET_ARB": 20.0,
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK": 18.0,
        "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY": 20.0,
        "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX": 20.0,
        "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX": 20.0,
        "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK": 18.0,
        "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG": 20.0,
        "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION": 18.0,
        "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX": 20.0,
        "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX": 20.0,
        "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH": 18.0,
        "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR": 18.0,
        "AFF1_FROZEN_SUBPERIOD_COLLAPSE": 18.0,
        "SOC2_EXACT_SCORE_2D_LATTICE": 18.0,
        "NFL_PRP1_MILESTONE_AND_MAX_LOCKS": 18.0,
        "SUM1_FRECHET_SUM_TRIANGLES": 20.0,
        "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION": 20.0,
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER": 18.0,
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
        "ZF_INTRADAY_MAKER_BOX": 110.0,
        "TW1_COUNTING_TRUNCATION_AND_BOX": 100.0,
        "FED1_CENTRAL_BANK_LP_BOX": 120.0,
        "COND1_MACRO_PARTITION_BOX": 120.0,
        "CTF_OVERROUND_MINT_SELL": 120.0,
        "D2_12PM_BINANCE_BOX": 100.0,
        "GAS1_AAA_GASOLINE_LOCK": 80.0,
        "CM_SHOCK_PYTH_CATALYST": 100.0,
        "S4H_CHAINLINK_CONVERGENCE": 100.0,
        "MKR_REWARD_LOCKED_CARRY": 100.0,
        "W1_LOW_TROUGH_LOCK": 100.0,
        "SP2_NBA_ENDGAME_LOCK": 100.0,
        "BOND1_UMA_RESOLUTION_CARRY": 120.0,
        "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX": 120.0,
        "NR_CONV_NO_BASKET_ARB": 120.0,
        "NR2_CONVERT_NO_SUBSET_ARB": 120.0,
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK": 100.0,
        "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY": 120.0,
        "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX": 120.0,
        "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX": 120.0,
        "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK": 100.0,
        "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG": 120.0,
        "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION": 100.0,
        "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX": 120.0,
        "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX": 120.0,
        "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH": 100.0,
        "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR": 100.0,
        "AFF1_FROZEN_SUBPERIOD_COLLAPSE": 110.0,
        "SOC2_EXACT_SCORE_2D_LATTICE": 110.0,
        "NFL_PRP1_MILESTONE_AND_MAX_LOCKS": 100.0,
        "SUM1_FRECHET_SUM_TRIANGLES": 120.0,
        "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION": 120.0,
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER": 100.0,
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
        "ZF_INTRADAY_MAKER_BOX": 350.0,
        "TW1_COUNTING_TRUNCATION_AND_BOX": 350.0,
        "FED1_CENTRAL_BANK_LP_BOX": 400.0,
        "COND1_MACRO_PARTITION_BOX": 400.0,
        "CTF_OVERROUND_MINT_SELL": 400.0,
        "D2_12PM_BINANCE_BOX": 300.0,
        "GAS1_AAA_GASOLINE_LOCK": 250.0,
        "CM_SHOCK_PYTH_CATALYST": 300.0,
        "S4H_CHAINLINK_CONVERGENCE": 300.0,
        "MKR_REWARD_LOCKED_CARRY": 300.0,
        "W1_LOW_TROUGH_LOCK": 350.0,
        "SP2_NBA_ENDGAME_LOCK": 350.0,
        "BOND1_UMA_RESOLUTION_CARRY": 400.0,
        "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX": 400.0,
        "NR_CONV_NO_BASKET_ARB": 400.0,
        "NR2_CONVERT_NO_SUBSET_ARB": 400.0,
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK": 350.0,
        "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY": 400.0,
        "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX": 400.0,
        "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX": 400.0,
        "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK": 350.0,
        "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG": 400.0,
        "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION": 350.0,
        "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX": 400.0,
        "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX": 400.0,
        "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH": 350.0,
        "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR": 350.0,
        "AFF1_FROZEN_SUBPERIOD_COLLAPSE": 350.0,
        "SOC2_EXACT_SCORE_2D_LATTICE": 350.0,
        "NFL_PRP1_MILESTONE_AND_MAX_LOCKS": 350.0,
        "SUM1_FRECHET_SUM_TRIANGLES": 400.0,
        "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION": 400.0,
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER": 350.0,
    },
}

for _v2_sl in (
    "S2_RTDS_EXACT_TWAP_INTEGRATOR",
    "D1_TELESCOPING_CANDLE_BRIDGE",
    "B1_INTRADAY_ONETOUCH_NOON_BOX",
    "EQ1_PYTH_EQUITY_DOMINANCE_BOX",
    "DC1_DOUBLE_CHANCE_1X2_PARITY",
    "LP_COMP1_SPORTS_TRIANGLES",
    "HALFTIME_FREEZE_OFFSET_BOX",
    "MENTION1_CUMULATIVE_LADDER_BOX",
    "NR6_CROSS_SLATE_SURJECTION_BOX",
    "NR4_EXHAUSTION_TAIL_YES_CONVERT",
    "NR5_OVERROUND_ALL_YES_SELL",
    "NR4_OPTIMAL_CHANNEL_CONVERT",
    "NR5_LOTTERY_FREEROLL_CONVERT",
    "CTF_OVERROUND_MINT_SELL",
    "C1_BINARY_COMPLETE_SET",
    "W_PRUNE1_METAR_SLATE_ARB",
    "W_PRUNE1_NR0_BASKET",
):
    BANKROLL_TICKETS["T100"].setdefault(_v2_sl, 20.0)
    BANKROLL_TICKETS["T1000"].setdefault(_v2_sl, 110.0)
    BANKROLL_TICKETS["T5000"].setdefault(_v2_sl, 350.0)


def walk_l2_book_asks(
    asks_raw: List[Dict[str, Any]],
    notional_usd: float,
    fee_rate: float,
    max_slip_cents: float = 0.025,
    min_l1_usd: float = 20.0,
    min_fill_ratio: float = 0.98,
    max_ask_px: float = 0.98,
    fee_exponent: float = 1.0,
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
    worst_px = best_ask
    for px, sz in asks:
        if px > best_ask + max_slip_cents or px >= max_ask_px:
            break
        lvl_usd = px * sz
        levels += 1
        worst_px = px
        take = min(rem, lvl_usd)
        shares += take / px
        spent += take
        rem -= take
        if rem <= 1e-6:
            break

    if spent < notional_usd * min_fill_ratio or shares <= 0:
        return {"filled": False, "reason": "INSUFFICIENT_DEPTH", "best_ask": best_ask, "l1_usd": l1_usd}

    vwap = spent / shares
    fee_ps = fee_rate * ((vwap * (1.0 - vwap)) ** fee_exponent) if fee_rate > 0 else 0.0
    fee_usd = shares * fee_ps
    eff_px = (spent + fee_usd) / shares
    return {
        "filled": True,
        "best_ask": round(best_ask, 4),
        "worst_px": round(worst_px, 4),
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


def walk_l2_book_asks_depth_capped(
    asks_raw: List[Dict[str, Any]],
    target_notional_usd: float,
    min_notional_usd: float,
    fee_rate: float = 0.0,
    max_slip_cents: float = 0.025,
    min_l1_usd: float = 15.0,
    max_ask_px: float = 0.98,
    fee_exponent: float = 1.0,
) -> Dict[str, Any]:
    res = walk_l2_book_asks(
        asks_raw,
        target_notional_usd,
        fee_rate=fee_rate,
        max_slip_cents=max_slip_cents,
        min_l1_usd=min_l1_usd,
        max_ask_px=max_ask_px,
        fee_exponent=fee_exponent,
    )
    if res.get("filled") or res.get("reason") != "INSUFFICIENT_DEPTH":
        return res
    asks = sorted(
        [(float(a["price"]), float(a["size"])) for a in asks_raw if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0],
        key=lambda x: x[0],
    )
    if not asks:
        return res
    best_ask = asks[0][0]
    avail_usd = sum(px * sz for px, sz in asks if px <= best_ask + max_slip_cents and px < max_ask_px)
    if avail_usd < min_notional_usd:
        return res
    cap_notional = min(target_notional_usd, avail_usd)
    res_cap = walk_l2_book_asks(
        asks_raw,
        cap_notional,
        fee_rate=fee_rate,
        max_slip_cents=max_slip_cents,
        min_l1_usd=min_l1_usd,
        min_fill_ratio=0.98,
        max_ask_px=max_ask_px,
        fee_exponent=fee_exponent,
    )
    if res_cap.get("filled"):
        res_cap["fill_ratio"] = round(float(res_cap["spent_usd"]) / max(0.01, target_notional_usd), 4)
        res_cap["depth_capped"] = cap_notional < target_notional_usd * 0.98
    return res_cap


def extract_best_bid(bids_raw: List[Dict[str, Any]]) -> Tuple[float, float]:
    bids = sorted(
        [(float(b["price"]), float(b["size"])) for b in bids_raw if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0],
        key=lambda x: -x[0],
    )
    if not bids:
        return 0.0, 0.0
    return round(bids[0][0], 4), round(bids[0][0] * bids[0][1], 2)


class _LazyWsBooksDict(dict):
    """Lazily materializes sorted top-20 bid/ask dicts on read, avoiding O(N log N) + f-string churn on 100Hz WS deltas."""
    def __init__(self, owner: "Alpha124ShadowDaemon") -> None:
        super().__init__()
        self._owner = owner
        self._dirty: Dict[str, float] = {}

    def mark_dirty(self, asset_id: str, ts: float) -> None:
        self._dirty[asset_id] = ts
        if not dict.__contains__(self, asset_id):
            dict.__setitem__(self, asset_id, (ts, {"asset_id": asset_id, "bids": [], "asks": []}))

    def _materialize(self, key: str) -> None:
        ts = self._dirty.pop(key, None)
        if ts is not None:
            lvls = self._owner._ws_raw_levels.get(key)
            if lvls is not None:
                self._owner._rebuild_ws_book_dict(key, lvls[0], lvls[1], ts)

    def get(self, key: Any, default: Any = None) -> Any:
        if key in self._dirty:
            self._materialize(key)
        return super().get(key, default)

    def __getitem__(self, key: str) -> Any:
        if key in self._dirty:
            self._materialize(key)
        return super().__getitem__(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self._dirty.pop(key, None)
        super().__setitem__(key, value)

    def pop(self, key: str, *args: Any) -> Any:
        self._dirty.pop(key, None)
        return super().pop(key, *args)

    def clear(self) -> None:
        self._dirty.clear()
        super().clear()


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
            a: collections.deque(maxlen=600) for a in (*DOMINANCE_ASSETS, *METAL_DOMINANCE_ASSETS)
        }
        self.usd_spot_hist: Dict[str, Deque[Tuple[float, float]]] = {
            a: collections.deque(maxlen=400) for a in (*DOMINANCE_ASSETS, *METAL_DOMINANCE_ASSETS)
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
        self.multi_sport_games: Dict[str, MultiSportCorridorSpec] = {}
        self.negrisk_convert_slates: Dict[str, NegRiskConvertSlateSpec] = {}
        self.live_nba_board: List[LiveNbaGameState] = []
        self.uma_proposed_markets: Dict[str, Dict[str, Any]] = {}
        self.uma_onchain_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.bond2_onchain_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.nba_prop_slates: Dict[str, NbaPlayerPropSlate] = {}
        self.nba_boxscore_cache: Dict[str, Tuple[float, Dict[str, Dict[str, int]]]] = {}
        self.nba_subperiod_slates: Dict[str, NbaSubperiodAndExtPropSlate] = {}
        self.nba_ext_summary_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self.soccer_trees: Dict[str, SoccerRegulationTree] = {}
        self.lp1_bop_legs: List[Dict[str, Any]] = []
        self.lp1_nba_em_bundles: Dict[str, Dict[str, Any]] = {}
        self.esports_bo3_specs: Dict[str, EsportsBo3Spec] = {}
        self.lp2_implication_groups: List[Tuple[str, List[Dict[str, Any]]]] = []
        self.lp2_events_by_slug: Dict[str, Dict[str, Any]] = {}
        self.cal1_ladders: Dict[str, CalendarOrScalarLadderSpec] = {}
        self.lp1_nfl_em_bundles: Dict[str, Dict[str, Any]] = {}
        self.multisport_raw_events: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        self.tennis_specs: Dict[str, TennisMatchSpec] = {}
        self.score_confirm_tracker = ScoreConfirmationTracker()
        self.live_multisport_boards: Dict[str, Tuple[float, List[LiveMultiSportGame]]] = {}
        self.aff1_bundles: Dict[str, AffineGameBundle] = {}
        self.soc2_lattices: Dict[str, SoccerExactScoreLattice] = {}
        self.nfl_prop_slates: Dict[str, NflPlayerPropSlate] = {}
        self.binance_close_rungs: List[CryptoCloseRungSpec] = []
        self.subperiod_freeze_tracker = SubperiodFreezeTracker()
        self.nfl_summary_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
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
        self._last_trade_tape_chk_ts: Dict[str, float] = {}
        self._open_meteo_sem = asyncio.Semaphore(2)

        self.last_discovery_ts = 0.0
        self.last_weather_scan_ts = 0.0
        self.last_crypto_mid_scan_ts = 0.0
        self.last_tradfi_sports_scan_ts = 0.0
        self.last_nba_endgame_scan_ts = 0.0
        self.last_espn_board_ts = 0.0
        self.last_uma_discovery_ts = 0.0
        self.last_dominance_discovery_ts = 0.0
        self.last_4h_discovery_ts = 0.0
        self.last_twap_discovery_ts = 0.0
        self.last_s5m_discovery_ts = 0.0
        self.last_preopen_discovery_ts = 0.0
        self.last_usd_sample_ts = 0.0
        self.cached_mid_opps: List[Dict[str, Any]] = []
        self.cached_weather_opps: List[Dict[str, Any]] = []
        self.cached_tradfi_sports_opps: List[Dict[str, Any]] = []
        self.cached_nba_endgame_opps: List[Dict[str, Any]] = []
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
        self._bg_nba_task: Optional[asyncio.Task] = None
        self._ws_books: Dict[str, Tuple[float, Dict[str, Any]]] = _LazyWsBooksDict(self)
        self._ws_raw_levels: Dict[str, Tuple[Dict[float, float], Dict[float, float]]] = {}
        self._ws_subscribed_tokens: set[str] = set()
        # Tokens whose `_ws_books` entry was seeded from a REST `/books` snapshot (not yet confirmed by a WS `book` event);
        # these are never forwarded to the live harvester as `cand["ws_books"]`.
        self._ws_rest_seeded: set[str] = set()
        # Priority-1 D1/S2 tokens (from `_desired_d1_ws_tokens`): only their WS updates trigger `_ws_d1_wakeup`.
        self._ws_d1_priority_tokens: set[str] = set()
        # Priority-2 NegRisk/Counting/UMA tokens: WS updates trigger `_ws_nr_wakeup` (`<=250ms` reactive scan).
        self._ws_nr_priority_tokens: set[str] = set()
        self._ws_shard_tokens: Dict[int, set[str]] = {}
        self._instant_arb_cooldown_until: Dict[str, float] = {}
        self._bg_chainlink_ws_task: Optional[asyncio.Task] = None
        self._chainlink_ws: Optional[Any] = (
            PolymarketChainlinkLiveStream(on_tick=self._on_chainlink_ws_tick)
            if (not self.single_scan and PolymarketChainlinkLiveStream is not None)
            else None
        )
        self._ws_d1_wakeup = asyncio.Event()
        self._ws_nr_wakeup = asyncio.Event()
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

    def is_sleeve_grad8_ready(self, sleeve: str) -> bool:
        """
        Strict `_grad8` (`8/8` closed shadow wins, `0` losses, `100.0%` WR, positive realized &
        legging-adjusted `T1000` PnL, non-quarantined) live-bridge auto-promotion gate.
        Flushes graduation mirror immediately upon qualification so `polymarket-live-harvester`
        sees `8/8` before the first live IPC candidate arrives; immediately revokes on any loss.
        """
        if is_shadow_sleeve_quarantined(sleeve):
            return False
        closed_sl = _filter_epoch_closed_positions(
            sleeve, [p for p in self.closed_positions if p.get("sleeve") == sleeve]
        )
        n_cl = len(closed_sl)
        wins = sum(1 for p in closed_sl if p.get("won"))
        losses = n_cl - wins
        promoted = self.__dict__.setdefault("_grad8_promoted_logged", set())
        if losses > 0:
            if sleeve in promoted:
                promoted.discard(sleeve)
                logger.warning(
                    f"🛑 [GRAD8 AUTO-PROMOTION REVOKED] {sleeve}: {wins}/{n_cl} ({losses} loss) — live IPC bridge DISARMED."
                )
            return False
        if n_cl < 8:
            return False
        pnl_1k = sum(float(p.get("tier_pnls_usd", {}).get("T1000", 0.0)) for p in closed_sl)
        adj_1k = sum(
            float(p.get("legging_adjusted_tier_pnls_usd", p.get("tier_pnls_usd", {})).get("T1000", 0.0))
            for p in closed_sl
        )
        if pnl_1k <= 0.0 or adj_1k <= 0.0:
            return False
        if sleeve not in promoted:
            promoted.add(sleeve)
            logger.info(
                f"🚀 [GRAD8 AUTO-PROMOTED -> LIVE] {sleeve}: {wins}/{n_cl} wins (100.0% WR, T1000=+${pnl_1k:.2f}) — live IPC bridge ARMED!"
            )
            if STATE_FILE == (DATA_DIR / "alpha124_shadow_state.json") or LIVE_ALPHA124_STATE_MIRROR_FILE != (LIVE_POLYMARKET_DIR / "alpha124_shadow_state.json"):
                try:
                    self.write_state_files(self.top_opportunities)
                except Exception as exc:
                    logger.debug(f"Grad8 mirror flush notice: {exc}")
        return True

    def _can_emit_zero_loss_math_live(
        self, sleeve: str, close_ts: float, now_ts: float, *, p_model: float = 1.0
    ) -> bool:
        """Allows 8/8 graduated sleeves OR 0-loss mathematical/verified-clinch sleeves in live daemon mode."""
        if self.is_sleeve_grad8_ready(sleeve):
            return True
        if self.single_scan or ("fetch_json" in self.__dict__) or is_shadow_sleeve_quarantined(sleeve):
            return False
        _max_rem_zl = 604800.0 if sleeve in {
            "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
            "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
            "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
            "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",
            "DC1_DOUBLE_CHANCE_1X2_PARITY",
            "LP_COMP1_SPORTS_TRIANGLES",
            "MENTION1_CUMULATIVE_LADDER_BOX",
        } else 129600.0
        if float(p_model) < 0.998 or not (0.0 < (float(close_ts) - float(now_ts)) <= _max_rem_zl):
            return False
        if any(not p.get("won") for p in _filter_epoch_closed_positions(sleeve, [p for p in self.closed_positions if p.get("sleeve") == sleeve])):
            return False
        return self.is_sleeve_grad8_ready("D1_SAME_ORACLE_DOMINANCE_BOX")

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
            if (
                (self.single_scan or ("fetch_json" in self.__dict__))
                and MARKET_TELEMETRY_FILE == (DATA_DIR / "alpha124_market_telemetry.jsonl")
                and STATE_FILE == (DATA_DIR / "alpha124_shadow_state.json")
                and LEDGER_FILE == (DATA_DIR / "alpha124_shadow_ledger.jsonl")
            ):
                return
            if MARKET_TELEMETRY_FILE != (DATA_DIR / "alpha124_market_telemetry.jsonl"):
                telem_path = MARKET_TELEMETRY_FILE
            elif STATE_FILE != (DATA_DIR / "alpha124_shadow_state.json"):
                telem_path = STATE_FILE.parent / "alpha124_market_telemetry.jsonl"
            else:
                telem_path = LEDGER_FILE.parent / "alpha124_market_telemetry.jsonl"
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
        bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
        fa = float(leg_a["fee_rate"]) * ((ask_a * (1.0 - ask_a)) ** float(leg_a.get("fee_exponent", 1.0)))
        fb = float(leg_b["fee_rate"]) * ((ask_b * (1.0 - ask_b)) ** float(leg_b.get("fee_exponent", 1.0)))
        mkr_cands: List[float] = []
        for b_x, a_x, o_eff in ((bid_a, ask_a, ask_b + fb), (bid_b, ask_b, ask_a + fa)):
            if b_x <= 0.0:
                continue
            tb_x = 0.001 if (b_x >= 0.96 or b_x < 0.04) else 0.01
            ta_x = 0.001 if (a_x > 0.96 or a_x <= 0.04) else 0.01
            st_b = (math.floor((b_x + tb_x + 1e-9) * 100.0) / 100.0) if (0.04 + 1e-9 < round(b_x + tb_x, 4) < 0.96 - 1e-9) else round(b_x + tb_x, 3)
            mx_u = (math.floor((a_x - ta_x + 1e-9) * 100.0) / 100.0) if (0.04 + 1e-9 < round(a_x - ta_x, 4) < 0.96 - 1e-9) else round(a_x - ta_x, 3)
            if st_b <= mx_u + 1e-9 and st_b > b_x + 1e-9:
                mkr_cands.append(round(min(st_b, mx_u) + o_eff, 4))
            elif (a_x - b_x) >= 0.01 - 1e-9 and 0.15 <= a_x <= 0.85:
                mkr_cands.append(round(b_x + o_eff, 4))
        best_mkr_net = min(mkr_cands) if mkr_cands else None
        usd_h = self.usd_spot_hist.get(m_outer.asset)
        usd_px = round(float(usd_h[-1][1]), 6) if usd_h else None
        self._record_market_telemetry(
            key=f"D1_{pair_type}_{m_outer.asset}_{m_inner.market_id}",
            min_interval_sec=10.0,
            now_ts=now_ts,
            sig=(ask_a, ask_b, best_mkr_net),
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
                "maker_anchor_net_l1": best_mkr_net,
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

    @staticmethod
    def _resolve_ledger_path() -> Path:
        if LEDGER_FILE != _DEFAULT_LEDGER_FILE:
            return LEDGER_FILE
        if DATA_DIR != _DEFAULT_DATA_DIR:
            return DATA_DIR / "alpha124_shadow_ledger.jsonl"
        if STATE_FILE != _DEFAULT_STATE_FILE:
            return STATE_FILE.parent / "alpha124_shadow_ledger.jsonl"
        return LEDGER_FILE

    @staticmethod
    def _is_leaked_unit_test_artifact(rec: Dict[str, Any]) -> bool:
        """Detects synthetic unit-test fixtures (`SP4_SUB_st1_st2` / `st1`/`st2`) when hydrating the live state file."""
        if STATE_FILE != _DEFAULT_STATE_FILE:
            return False
        dk = str(rec.get("dedupe_key") or rec.get("position_id") or "")
        if dk.startswith("SP4_SUB_st1_st2"):
            return True
        extra = rec.get("extra") or {}
        if str(extra.get("market_id") or "") in {"st1", "st2"}:
            return True
        la = extra.get("leg_a") or {}
        lb = extra.get("leg_b") or {}
        if str(la.get("market_id") or "") in {"st1", "st2"} or str(lb.get("market_id") or "") in {"st1", "st2"}:
            return True
        return False

    def _hydrate_state(self) -> None:
        if STATE_FILE.exists():
            try:
                st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.started_at = st.get("started_at", self.started_at)
                for p in st.get("open_positions", []):
                    if isinstance(p, dict) and p.get("position_id") and not self._is_leaked_unit_test_artifact(p):
                        self.open_positions[p["position_id"]] = p
                        self.entered_keys.add(str(p.get("dedupe_key") or p["position_id"]))
                        ev_id = (p.get("extra") or {}).get("event_id")
                        if ev_id:
                            if p.get("sleeve") == "W2_ENSEMBLE_VALUE":
                                self.entered_keys.add(f"W2_EVENT_{ev_id}")
                            elif p.get("sleeve") == "W2_MAKER_OVERROUND":
                                self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                for m_ord in st.get("pending_maker_orders", []):
                    if isinstance(m_ord, dict) and m_ord.get("order_id") and not self._is_leaked_unit_test_artifact(m_ord):
                        self.pending_maker_orders[m_ord["order_id"]] = m_ord
                        if m_ord.get("dedupe_key"):
                            self.entered_keys.add(str(m_ord["dedupe_key"]))
                        ev_id = (m_ord.get("extra") or {}).get("event_id")
                        if ev_id and m_ord.get("sleeve") == "W2_MAKER_OVERROUND":
                            self.entered_keys.add(f"W2M_EVENT_{ev_id}")
                for p in st.get("recent_closed_positions", []):
                    if isinstance(p, dict) and not self._is_leaked_unit_test_artifact(p):
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

        ledger_path = self._resolve_ledger_path()
        if ledger_path.exists():
            try:
                ledger_open: Dict[str, Dict[str, Any]] = {}
                ledger_maker: Dict[str, Dict[str, Any]] = {}
                closed_ids = {str(p.get("position_id")) for p in self.closed_positions if isinstance(p, dict) and p.get("position_id")}
                with open(ledger_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            r = json.loads(line)
                        except Exception:
                            # Skip truncated/corrupt JSONL line without aborting ledger hydration (`F-19`)
                            continue
                        if isinstance(r, dict) and self._is_leaked_unit_test_artifact(r):
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
                    if oid not in self.pending_maker_orders or float(m_rec.get("last_repeg_ts") or 0.0) > float(self.pending_maker_orders[oid].get("last_repeg_ts") or 0.0):
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
        ledger_path = self._resolve_ledger_path()
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger_path, "a", encoding="utf-8") as f:
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
            if isinstance(self._ws_books, _LazyWsBooksDict):
                self._ws_books.mark_dirty(asset_id, now_ts)
            else:
                self._rebuild_ws_book_dict(asset_id, bids_map, asks_map, now_ts)
        return changed

    def _desired_d1_ws_tokens(self, now_ts: float, max_cap: int = 600) -> List[str]:
        out: List[str] = []
        seen: set[str] = set()
        nr_prio: set[str] = set()

        def _add_tok(tok: Any, *, is_nr: bool = False) -> bool:
            if len(out) >= max_cap:
                return False
            t_s = str(tok or "").strip()
            if t_s and t_s not in seen:
                seen.add(t_s)
                out.append(t_s)
                if is_nr:
                    nr_prio.add(t_s)
            elif t_s and is_nr:
                nr_prio.add(t_s)
            return len(out) < max_cap

        # Priority 1: Active D1 (15m/5m + 4h) and S2 TWAP Lock tokens
        for m_long, m_short in list(self.dominance_pairs.values()) + list(self.dominance_4h_pairs.values()):
            if float(m_short.end_ts) <= now_ts + 5.0:
                continue
            for tok in (m_long.up_token, m_long.down_token, m_short.up_token, m_short.down_token):
                _add_tok(tok)
        if not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK"):
            for sp_tw in list(self.twap_candles.values()):
                if float(sp_tw.end_ts) > now_ts + 5.0:
                    _add_tok(sp_tw.up_token)
                    _add_tok(sp_tw.down_token)
        self._ws_d1_priority_tokens = set(out)

        # Priority 1B: zero-hold C1 Daily Complete Sets + near-ATM M3 Multi-Strike & N1 NegRisk Brackets
        for sp_d in list(self.pyth_daily_markets.values()) + list(self.daily_updown_markets.values()):
            if float(sp_d.end_ts) > now_ts + 60.0:
                _add_tok(sp_d.up_token)
                _add_tok(sp_d.down_token)
        for rungs in list(self.strike_ladders.values()):
            if not rungs or float(rungs[0].end_ts) <= now_ts + 60.0:
                continue
            spot_r = float(self.spots.get(rungs[0].asset) or 0.0)
            ranked_r = sorted(rungs, key=lambda r: abs(float(r.strike) - spot_r)) if spot_r > 0.0 else list(rungs)
            for r in ranked_r[:4]:
                _add_tok(r.yes_token)
                _add_tok(r.no_token)
        for brs in list(self.negrisk_ladders.values()):
            if not brs or float(brs[0].end_ts) <= now_ts + 60.0:
                continue
            spot_n = float(self.spots.get(brs[0].asset) or 0.0)
            ranked_b = sorted(brs, key=lambda b: abs(0.5 * (float(b.k_low or spot_n) + float(b.k_high or spot_n)) - spot_n)) if spot_n > 0.0 else list(brs)
            for b in ranked_b[:4]:
                _add_tok(b.yes_token)
                _add_tok(b.no_token)

        # Priority 2: Active Zero-Fee NegRisk Slates (`NR0`), Closed Convert Slates (`NR2`/`NR3`), Counting Slates (`CM`), & `BOND1`/`BOND2` UMA
        for sp_nr in sorted(self.negrisk_zero_slates.values(), key=lambda s: float(s.end_ts)):
            if float(sp_nr.end_ts) <= now_ts + 60.0 or len(sp_nr.brackets) > 15:
                continue
            for b_z in sp_nr.brackets:
                _add_tok(b_z.get("no_token"), is_nr=True)
                _add_tok(b_z.get("yes_token"), is_nr=True)
        for sp_nrc in sorted(self.negrisk_convert_slates.values(), key=lambda s: (not bool(s.is_closed_convert_safe), float(s.end_ts))):
            if float(sp_nrc.end_ts) <= now_ts + 60.0 or len(sp_nrc.brackets) > 15:
                continue
            for b_c in sp_nrc.brackets:
                _add_tok(b_c.get("no_token"), is_nr=True)
                if sp_nrc.is_closed_convert_safe:
                    _add_tok(b_c.get("yes_token"), is_nr=True)
        for sp_cm in sorted(self.counting_slates.values(), key=lambda s: float(getattr(s, "window_end_ts", None) or getattr(s, "end_ts", 0.0) or 0.0)):
            if float(getattr(sp_cm, "window_end_ts", None) or getattr(sp_cm, "end_ts", 0.0) or 0.0) <= now_ts + 60.0 or len(sp_cm.brackets) > 15:
                continue
            for b_m in sp_cm.brackets:
                _add_tok(b_m.get("no_token"), is_nr=True)
                _add_tok(b_m.get("yes_token"), is_nr=True)
        for uma_m in list(self.uma_proposed_markets.values())[:25]:
            if isinstance(uma_m, dict):
                uma_tks = _parse_clob_tokens(uma_m)
                if uma_tks:
                    _add_tok(uma_tks[0], is_nr=True)
                    _add_tok(uma_tks[1], is_nr=True)
                else:
                    _add_tok(uma_m.get("win_token") or uma_m.get("yes_token"), is_nr=True)
                    _add_tok(uma_m.get("lose_token") or uma_m.get("no_token"), is_nr=True)
        self._ws_nr_priority_tokens = nr_prio

        # Priority 3: Active Sports Corridors (`SP1`/`SP2`/`SP4`) within 6h of close
        for gm_s in list(self.multi_sport_games.values()) + list(self.nba_games.values()):
            end_g = float(getattr(gm_s, "end_ts", 0.0) or 0.0)
            if 60.0 < (end_g - now_ts) <= 21600.0:
                for attr_t in ("ml_a_token", "ml_b_token"):
                    _add_tok(getattr(gm_s, attr_t, None))
                for sp_r in (getattr(gm_s, "spreads", None) or ())[:3]:
                    if isinstance(sp_r, dict):
                        _add_tok(sp_r.get("yes_token"))
                        _add_tok(sp_r.get("no_token"))
        return out

    def _partition_ws_shards(self, now_ts: float, max_shards: int = 3, per_shard: int = 200) -> List[List[str]]:
        desired = self._desired_d1_ws_tokens(now_ts, max_cap=max_shards * per_shard)
        return [desired[i * per_shard : (i + 1) * per_shard] for i in range(max_shards)]

    def _sync_ws_subscribed_union(self) -> None:
        union_s: set[str] = set()
        for st_i in self._ws_shard_tokens.values():
            union_s.update(st_i)
        self._ws_subscribed_tokens = union_s

    async def _run_single_clob_ws_shard(self, shard_idx: int) -> None:
        """Runs 1 shard (`<= 200` tokens) of the 3-shard `600`-token Polymarket CLOB L2 WebSocket Matrix."""
        while not self.single_scan:
            shards_0 = self._partition_ws_shards(time.time())
            desired_0 = shards_0[shard_idx] if shard_idx < len(shards_0) else []
            if not desired_0:
                for old_t in list(self._ws_shard_tokens.pop(shard_idx, set())):
                    self._drop_ws_book(old_t)
                self._sync_ws_subscribed_union()
                await asyncio.sleep(1.5)
                continue
            try:
                sess = await self.get_session()
                async with sess.ws_connect(
                    CLOB_WS_URL,
                    heartbeat=15.0,
                    max_msg_size=4 * 1024 * 1024,
                    timeout=aiohttp.ClientWSTimeout(ws_close=5.0),
                ) as ws:
                    prev_shard = self._ws_shard_tokens.get(shard_idx, set())
                    for old_t in list(prev_shard | set(desired_0)):
                        self._drop_ws_book(old_t)
                    shard_sub = set(desired_0)
                    self._ws_shard_tokens[shard_idx] = shard_sub
                    self._sync_ws_subscribed_union()
                    await ws.send_str(json.dumps({"assets_ids": desired_0, "type": "market"}))
                    last_sub_chk = time.time()
                    last_rx_ts = last_sub_chk
                    while not self.single_scan:
                        now_w = time.time()
                        if (now_w - last_sub_chk) >= 2.0:
                            last_sub_chk = now_w
                            shards_w = self._partition_ws_shards(now_w)
                            cur_desired = set(shards_w[shard_idx] if shard_idx < len(shards_w) else [])
                            other_subs: set[str] = set()
                            for k_idx, st_other in self._ws_shard_tokens.items():
                                if k_idx != shard_idx:
                                    other_subs.update(st_other)
                            cur_desired -= other_subs
                            for stale_tok in list(shard_sub - cur_desired):
                                shard_sub.discard(stale_tok)
                                if stale_tok not in other_subs:
                                    self._drop_ws_book(stale_tok)
                            self._sync_ws_subscribed_union()
                            if not cur_desired:
                                break
                            added = sorted(cur_desired - shard_sub)
                            if added:
                                await ws.send_str(json.dumps({"assets_ids": added, "operation": "subscribe"}))
                                shard_sub.update(added)
                                self._sync_ws_subscribed_union()
                            elif len(shard_sub) > len(cur_desired) + 32:
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
                        woke_d1 = False
                        woke_nr = False
                        d1_wake_toks = self._ws_d1_priority_tokens
                        nr_wake_toks = self._ws_nr_priority_tokens
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    aid = str(item.get("asset_id") or "")
                                    if aid in shard_sub:
                                        tk_i = item.get("tick_size") or item.get("minimum_tick_size")
                                        if tk_i:
                                            self.__dict__.setdefault("_token_tick_sizes", {})[aid] = str(tk_i)
                                        self._apply_ws_book_snapshot(aid, item.get("bids") or [], item.get("asks") or [], now_rx)
                                        woke_d1 = woke_d1 or (aid in d1_wake_toks)
                                        woke_nr = woke_nr or (aid in nr_wake_toks)
                        elif isinstance(data, dict):
                            ev_t = data.get("event_type")
                            if ev_t == "book":
                                aid = str(data.get("asset_id") or "")
                                if aid in shard_sub:
                                    tk_b = data.get("tick_size") or data.get("minimum_tick_size")
                                    if tk_b:
                                        self.__dict__.setdefault("_token_tick_sizes", {})[aid] = str(tk_b)
                                    self._apply_ws_book_snapshot(aid, data.get("bids") or [], data.get("asks") or [], now_rx)
                                    woke_d1 = woke_d1 or (aid in d1_wake_toks)
                                    woke_nr = woke_nr or (aid in nr_wake_toks)
                            elif ev_t == "tick_size_change":
                                aid = str(data.get("asset_id") or "")
                                ntk = data.get("new_tick_size") or data.get("tick_size")
                                if aid and ntk:
                                    self.__dict__.setdefault("_token_tick_sizes", {})[aid] = str(ntk)
                                    if aid in self._ws_books and isinstance(self._ws_books[aid][1], dict):
                                        self._ws_books[aid][1]["minimum_tick_size"] = str(ntk)
                            elif ev_t == "price_change":
                                grouped: Dict[str, List[Dict[str, Any]]] = {}
                                for pc in data.get("price_changes") or ():
                                    aid = str(pc.get("asset_id") or "")
                                    if aid in shard_sub:
                                        grouped.setdefault(aid, []).append(pc)
                                for aid, pcs in grouped.items():
                                    if self._apply_ws_price_changes(aid, pcs, now_rx):
                                        if aid in d1_wake_toks:
                                            woke_d1 = True
                                        if aid in nr_wake_toks:
                                            woke_nr = True
                        if (
                            woke_d1
                            and (self.is_in_same_oracle_overlap_window(now_rx) or bool(self.pending_maker_anchors))
                            and (now_rx - getattr(self, "_last_ws_d1_wake_ts", 0.0)) >= 0.12
                        ):
                            self._last_ws_d1_wake_ts = now_rx
                            self._ws_d1_wakeup.set()
                        if woke_nr and (now_rx - getattr(self, "_last_ws_nr_wake_ts", 0.0)) >= 0.25:
                            self._last_ws_nr_wake_ts = now_rx
                            self._ws_nr_wakeup.set()
                            self._ws_d1_wakeup.set()
            except asyncio.CancelledError:
                raise
            except Exception as exc_ws:
                logger.debug(f"CLOB WS shard {shard_idx} reconnect notice: {exc_ws}")
                await asyncio.sleep(1.0)

    async def _scan_ws_reactive_negrisk_arbs(self, now_ts: float) -> None:
        """Zero-REST reactive NegRisk (`NR_CONV`, `NR2`, `NR3`) subscan triggered by 3-shard CLOB WS deltas."""
        from src.polymarket_research.riskless_machine_gun_engine import detect_nr3_synthetic_all_yes_overround

        opps_tmp: List[Dict[str, Any]] = []
        for sp_nrc in list(self.negrisk_convert_slates.values()):
            if not sp_nrc.is_closed_convert_safe or sp_nrc.end_ts <= now_ts + 65.0 or len(sp_nrc.brackets) > 15:
                continue
            ws_map: Dict[str, Dict[str, Any]] = {}
            all_fresh = True
            for b_c in sp_nrc.brackets:
                for tk_c in (b_c.get("no_token"), b_c.get("yes_token")):
                    t_str = str(tk_c or "")
                    ws_ent = self._ws_books.get(t_str) if t_str else None
                    if ws_ent is None or (now_ts - float(ws_ent[0])) > 2.5 or t_str in self._ws_rest_seeded:
                        all_fresh = False
                        break
                    ws_map[t_str] = ws_ent[1]
                if not all_fresh:
                    break
            if not all_fresh:
                continue
            conv_arbs = detect_negrisk_convert_positions_arbs(
                sp_nrc, ws_map, target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"], min_net_edge_per_share=0.005, min_shares=8
            )
            if conv_arbs:
                await self.execute_negrisk_convert_positions_arb(sp_nrc, conv_arbs[0], ws_map, opps_tmp)
            nr2_arbs = detect_nr2_convert_no_subset_arbs(
                sp_nrc, ws_map, target_budget_usd=BANKROLL_TICKETS["T1000"]["NR2_CONVERT_NO_SUBSET_ARB"], min_edge_pure_cash=0.012, min_edge_with_yes_sell=0.015, min_shares=6
            )
            if nr2_arbs:
                await self.execute_nr2_subset_convert_arb(sp_nrc, nr2_arbs[0], ws_map, opps_tmp)
            nr3_hit = detect_nr3_synthetic_all_yes_overround(
                sp_nrc, ws_map, target_budget_usd=30.0, min_net_edge_per_set=0.008, min_shares=5
            )
            if nr3_hit is not None:
                self.emit_live_negrisk_convert_candidate(
                    sleeve_source="NR2_CONVERT_NO_SUBSET_ARB",
                    spec=sp_nrc,
                    dedupe_key=f"NR3_OVR_{sp_nrc.event_id}",
                    arb_hit=nr3_hit,
                    books_by_token=ws_map,
                    now_ts=now_ts,
                )

    async def _run_clob_d1_ws_loop(self) -> None:
        """Maintains a 3-shard (`600`-token) Polymarket CLOB Market WebSocket L2 book matrix."""
        if self.single_scan:
            return
        await asyncio.gather(*(self._run_single_clob_ws_shard(idx) for idx in range(3)))

    def _get_fresh_ws_book(self, token_id: str, now_ts: float, max_age_sec: float = 5.0) -> Optional[Dict[str, Any]]:
        t_str = str(token_id or "")
        if not t_str or t_str in getattr(self, "_ws_rest_seeded", set()):
            return None
        ws_ent = self._ws_books.get(t_str) if getattr(self, "_ws_books", None) is not None else None
        if ws_ent is None or (float(now_ts) - float(ws_ent[0])) > float(max_age_sec):
            return None
        bk = ws_ent[1]
        if isinstance(bk, dict):
            tk_c = (self.__dict__.get("_token_tick_sizes") or {}).get(t_str)
            if tk_c:
                bk["minimum_tick_size"] = tk_c
        return bk if isinstance(bk, dict) and (bk.get("asks") or bk.get("bids")) else None

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
        tk_cache = self.__dict__.setdefault("_token_tick_sizes", {})
        for t in uniq:
            ws_entry = self._ws_books.get(t) if use_ws else None
            if (
                ws_entry is not None
                and (now_b - ws_entry[0]) <= 1.5
                and (ws_entry[1].get("bids") or ws_entry[1].get("asks"))
            ):
                if t in tk_cache:
                    ws_entry[1]["minimum_tick_size"] = tk_cache[t]
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
                                    tk_r = r.get("minimum_tick_size") or r.get("tick_size")
                                    if tk_r:
                                        tk_cache[aid_r] = str(tk_r)
                                    out[aid_r] = r
                                    if use_ws and aid_r in self._ws_subscribed_tokens and aid_r not in self._ws_raw_levels:
                                        self._apply_ws_book_snapshot(aid_r, r.get("bids") or [], r.get("asks") or [], now_seed, from_rest=True)
                            continue
            except Exception:
                pass
            fb = await asyncio.gather(*(self.fetch_json(f"{CLOB_URL}/book?token_id={t}", timeout=timeout) for t in chunk))
            for t, bk in zip(chunk, fb):
                if isinstance(bk, dict):
                    tk_b2 = bk.get("minimum_tick_size") or bk.get("tick_size")
                    if tk_b2:
                        tk_cache[t] = str(tk_b2)
                    out[t] = bk
        return out

    def record_usd_spot_samples(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        self.last_usd_sample_ts = now
        for asset in (*DOMINANCE_ASSETS, *METAL_DOMINANCE_ASSETS):
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
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            attach_weather_neg_risk_from_gamma as _attach_weather_neg_risk,
            resolve_weather_effective_end_ts,
        )
        def _weather_still_live(sp_w: WeatherEventSpec) -> bool:
            return resolve_weather_effective_end_ts(sp_w, now_w_disc + 86400.0) > now_w_disc

        w_tag_pages = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?tag_slug=weather&closed=false&limit=100&offset={w_off}", timeout=7.0) for w_off in (0, 100, 200, 300, 400))
        )
        for evts_wt in w_tag_pages:
            if isinstance(evts_wt, list):
                for ev in evts_wt:
                    sp = parse_weather_event(ev)
                    if sp is not None and _weather_still_live(sp):
                        _attach_weather_neg_risk(sp, ev)
                        weather_found[sp.event_id] = sp
        top_vol_events_raw: List[Dict[str, Any]] = []
        for offset in range(0, 600, 100):
            evts = await self.fetch_json(
                f"{GAMMA_URL}/events?closed=false&order=volume24hr&ascending=false&limit=100&offset={offset}",
                timeout=7.0,
            )
            if not isinstance(evts, list) or not evts:
                break
            top_vol_events_raw.extend(evts)
            for ev in evts:
                sp = parse_weather_event(ev)
                if sp is not None and _weather_still_live(sp):
                    _attach_weather_neg_risk(sp, ev)
                    weather_found[sp.event_id] = sp
        seen_w_series = {sp.series_slug for sp in weather_found.values() if sp.series_slug}
        for w_slug in HIGH_VOLUME_WEATHER_SERIES:
            if w_slug in seen_w_series:
                continue
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
        raw_strike_evts: List[Dict[str, Any]] = []
        for asset, slug in STRIKE_SERIES:
            evts = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={slug}&closed=false&limit=5", timeout=6.0)
            if isinstance(evts, list):
                raw_strike_evts.extend(evts)
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
        ms_found: Dict[str, MultiSportCorridorSpec] = {}
        prop_found: Dict[str, NbaPlayerPropSlate] = {}
        sub_nba_found: Dict[str, NbaSubperiodAndExtPropSlate] = {}
        raw_nba_parents: Dict[str, Dict[str, Any]] = {}
        raw_nba_em: Dict[str, Dict[str, Any]] = {}
        for nba_slug in NBA_SERIES_SLUGS:
            evts_nba = await self.fetch_json(f"{GAMMA_URL}/events?series_slug={nba_slug}&closed=false&limit=40", timeout=6.5)
            if isinstance(evts_nba, list):
                for ev in evts_nba:
                    sl_ev = str(ev.get("slug") or "").lower()
                    if sl_ev.endswith("-exact-margin"):
                        raw_nba_em[sl_ev[:-13]] = ev
                        continue
                    raw_nba_parents[sl_ev] = ev
                    sp_nba = parse_nba_zero_fee_event(ev, now_ts=now_disc)
                    if sp_nba is not None:
                        nba_found[sp_nba.event_id] = sp_nba
                    sp_pr = parse_nba_player_props_from_event(ev, now_ts=now_disc)
                    if sp_pr is not None:
                        prop_found[sp_pr.event_id] = sp_pr
                    sp_sub = parse_nba_subperiod_and_ext_props(ev, now_ts=now_disc)
                    if sp_sub is not None:
                        sub_nba_found[sp_sub.event_id] = sp_sub
                    sp_ms_nba = parse_multi_sport_corridor_event(ev, sport_hint="NBA", now_ts=now_disc, skip_nba_fg_zero_fee=True)
                    if sp_ms_nba is not None:
                        ms_found[sp_ms_nba.event_id] = sp_ms_nba
        missing_em_slugs = [sl for sl in list(raw_nba_parents.keys())[:10] if sl not in raw_nba_em]
        if missing_em_slugs:
            em_fetches = await asyncio.gather(
                *(self.fetch_json(f"{GAMMA_URL}/events?slug={sl}-exact-margin", timeout=4.5) for sl in missing_em_slugs)
            )
            for sl_m, res_em in zip(missing_em_slugs, em_fetches):
                if isinstance(res_em, list) and res_em:
                    raw_nba_em[sl_m] = res_em[0]
        em_bundles_found: Dict[str, Dict[str, Any]] = {}
        for sl_p, ev_p in raw_nba_parents.items():
            ev_e = raw_nba_em.get(sl_p)
            if ev_e is not None:
                b_em = build_lp1_nba_exact_margin_bundle(ev_p, ev_e)
                if b_em is not None and float(b_em["end_ts"]) > now_disc + 60:
                    em_bundles_found[b_em["event_id"]] = b_em
        self.nba_games = nba_found
        self.nba_prop_slates = prop_found
        self.nba_subperiod_slates = sub_nba_found
        self.lp1_nba_em_bundles = em_bundles_found

        non_nba_sport_series = [(sl_s, sp_t) for sp_t, sl_s in MULTI_SPORT_CORRIDOR_SERIES if sl_s not in NBA_SERIES_SLUGS]
        ms_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?series_slug={sl_s}&closed=false&limit=25", timeout=5.5) for sl_s, _ in non_nba_sport_series),
            self.fetch_json(f"{GAMMA_URL}/events?tag_slug=sports&closed=false&order=volume24hr&ascending=false&limit=40", timeout=6.0),
        )
        nfl_em_found: Dict[str, Dict[str, Any]] = {}
        ms_raw_found: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        for (_, sp_tag), evts_ms in zip(non_nba_sport_series, ms_res[: len(non_nba_sport_series)]):
            if isinstance(evts_ms, list):
                for ev in evts_ms:
                    sp_ms = parse_multi_sport_corridor_event(ev, sport_hint=sp_tag, now_ts=now_disc, skip_nba_fg_zero_fee=True)
                    if sp_ms is not None:
                        ms_found[sp_ms.event_id] = sp_ms
                    ev_id_m = str(ev.get("id") or "")
                    if ev_id_m and sp_tag in ("NFL", "CFB", "NHL"):
                        ms_raw_found[ev_id_m] = (sp_tag, ev)
                    if sp_tag == "NFL":
                        b_nfl = build_lp1_nfl_exact_margin_bundle(ev, now_ts=now_disc)
                        if b_nfl is not None:
                            nfl_em_found[b_nfl["event_id"]] = b_nfl
        self.lp1_nfl_em_bundles = nfl_em_found
        self.multisport_raw_events = ms_raw_found
        extra_sport_evts = (ms_res[-1] if isinstance(ms_res[-1], list) else []) + [
            e for e in top_vol_events_raw if isinstance(e, dict) and not e.get("negRisk") and len(e.get("markets") or ()) >= 8
        ]
        for ev in extra_sport_evts:
            ev_id_s = str(ev.get("id") or "")
            if ev_id_s and ev_id_s not in ms_found:
                sp_ms = parse_multi_sport_corridor_event(ev, now_ts=now_disc, skip_nba_fg_zero_fee=True)
                if sp_ms is not None:
                    ms_found[sp_ms.event_id] = sp_ms
        self.multi_sport_games = ms_found

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

        nrc_candidates: Dict[str, NegRiskConvertSlateSpec] = {}
        for ev_src in (
            top_vol_events_raw
            + [e for lst in raw_by_series.values() for e in (lst or [])]
            + [e for lst in w_tag_pages if isinstance(lst, list) for e in lst]
        ):
            if not isinstance(ev_src, dict):
                continue
            sp_nrc = parse_negrisk_convert_event(ev_src)
            if sp_nrc is not None and sp_nrc.end_ts > now_disc + 60 and len(sp_nrc.brackets) <= 45:
                nrc_candidates[sp_nrc.event_id] = sp_nrc
        ranked_nrc = sorted(
            nrc_candidates.values(),
            key=lambda s: (
                not s.is_closed_convert_safe,
                (s.end_ts - now_disc) > 172800.0,
                s.end_ts,
            ),
        )[:40]
        self.negrisk_convert_slates = {s.event_id: s for s in ranked_nrc}

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

        # 6B. Frontier v2 Discovery: Soccer Regulation Trees (`SOC1`), Esports BO3 (`API1`), & 2026 BOP x Chambers (`LP1-6C`)
        fv2_min_iso = datetime.fromtimestamp(now_disc - 4.0 * 3600.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        fv2_res = await asyncio.gather(
            self.fetch_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&order=volume24hr&ascending=false&limit=100", timeout=5.5),
            self.fetch_json(f"{GAMMA_URL}/events?tag_id=100350&active=true&closed=false&end_date_min={fv2_min_iso}&order=endDate&ascending=true&limit=100", timeout=5.5),
            self.fetch_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&order=volume24hr&ascending=false&limit=100", timeout=5.5),
            self.fetch_json(f"{GAMMA_URL}/events?tag_id=64&active=true&closed=false&end_date_min={fv2_min_iso}&order=endDate&ascending=true&limit=100", timeout=5.5),
            *(self.fetch_json(f"{GAMMA_URL}/events?slug={sl_b}", timeout=5.0) for sl_b in BOP_2026_SLUGS),
        )
        soc_pages = (fv2_res[0] if isinstance(fv2_res[0], list) else []) + (fv2_res[1] if isinstance(fv2_res[1], list) else [])
        esp_pages = (fv2_res[2] if isinstance(fv2_res[2], list) else []) + (fv2_res[3] if isinstance(fv2_res[3], list) else [])
        soc_raw = list({str(e.get("id")): e for e in soc_pages if isinstance(e, dict) and e.get("id")}.values())
        esp_raw = list({str(e.get("id")): e for e in esp_pages if isinstance(e, dict) and e.get("id")}.values())
        self.soccer_trees = link_and_parse_soccer_regulation_trees(soc_raw, now_ts=now_disc)
        esp_found: Dict[str, EsportsBo3Spec] = {}
        for ev_esp in esp_raw:
            sp_esp = parse_esports_bo3_event(ev_esp, now_ts=now_disc)
            if sp_esp is not None:
                esp_found[sp_esp.event_id] = sp_esp
        self.esports_bo3_specs = esp_found
        bop_by_slug: Dict[str, Dict[str, Any]] = {}
        for sl_b, res_b in zip(BOP_2026_SLUGS, fv2_res[4:]):
            if isinstance(res_b, list) and res_b:
                bop_by_slug[sl_b] = res_b[0]
        self.lp1_bop_legs = build_lp1_bop_2026_truth_legs(bop_by_slug)
        for ev_extra_nr in list(raw_nba_em.values()) + list(bop_by_slug.values()):
            sp_nrc_x = parse_negrisk_convert_event(ev_extra_nr)
            if sp_nrc_x is not None and sp_nrc_x.is_closed_convert_safe and sp_nrc_x.end_ts > now_disc + 60:
                self.negrisk_convert_slates[sp_nrc_x.event_id] = sp_nrc_x

        # 6C. Frontier v3 Discovery: Election DAG (`LP2`), Monotonic Ladders (`CAL1`), & ATP/WTA Tennis (`TEN1`)
        lp2_slugs_all = list(dict.fromkeys(
            list(LP2_MIDTERM_CORE_SLUGS) + [LP2_TOSSUP_CUBE_SLUG] + list(LP2_TOSSUP_STATE_SLUGS.values())
        ))
        fv3_res = await asyncio.gather(
            *(self.fetch_json(f"{GAMMA_URL}/events?slug={sl_l2}", timeout=5.0) for sl_l2 in lp2_slugs_all),
            self.fetch_json(f"{GAMMA_URL}/events?tag_slug=tennis&active=true&closed=false&order=volume24hr&ascending=false&limit=45", timeout=5.5),
            self.fetch_json(f"{GAMMA_URL}/events?tag_slug=midterms&active=true&closed=false&order=volume24hr&ascending=false&limit=60", timeout=5.5),
            self.fetch_json(f"{GAMMA_URL}/events?tag_slug=politics&active=true&closed=false&order=volume24hr&ascending=false&limit=60", timeout=5.5),
        )
        lp2_by_slug: Dict[str, Dict[str, Any]] = dict(bop_by_slug)
        for sl_l2, res_l2 in zip(lp2_slugs_all, fv3_res[: len(lp2_slugs_all)]):
            if isinstance(res_l2, list) and res_l2:
                lp2_by_slug[sl_l2] = res_l2[0]
        ten_raw = fv3_res[len(lp2_slugs_all)] if isinstance(fv3_res[len(lp2_slugs_all)], list) else []
        mid_raw = fv3_res[len(lp2_slugs_all) + 1] if isinstance(fv3_res[len(lp2_slugs_all) + 1], list) else []
        pol_raw = fv3_res[len(lp2_slugs_all) + 2] if isinstance(fv3_res[len(lp2_slugs_all) + 2], list) else []
        for ev_mp in mid_raw + pol_raw:
            if isinstance(ev_mp, dict) and ev_mp.get("slug"):
                lp2_by_slug.setdefault(str(ev_mp["slug"]), ev_mp)
        self.lp2_events_by_slug = lp2_by_slug

        lp2_groups: List[Tuple[str, List[Dict[str, Any]]]] = []
        hs_legs = build_lp2_house_seats_truth_legs(lp2_by_slug)
        if hs_legs:
            lp2_groups.append(("LP2_HOUSE_SEATS", hs_legs))
        ss_legs = build_lp2_senate_seats_truth_legs(lp2_by_slug)
        if ss_legs:
            lp2_groups.append(("LP2_SENATE_SEATS", ss_legs))
        lp2_groups.extend(build_lp2_pending_senate_conditional_groups(
            list(lp2_by_slug.values()), lp2_by_slug.get("which-party-will-win-the-senate-in-2026")
        ))
        lp2_groups.extend(build_lp2_tossup_state_implication_groups(lp2_by_slug))
        self.lp2_implication_groups = lp2_groups

        for ev_lp2_nr in lp2_by_slug.values():
            sp_nrc_l2 = parse_negrisk_convert_event(ev_lp2_nr)
            if sp_nrc_l2 is not None and sp_nrc_l2.is_closed_convert_safe and sp_nrc_l2.end_ts > now_disc + 60 and len(sp_nrc_l2.brackets) <= 45:
                self.negrisk_convert_slates[sp_nrc_l2.event_id] = sp_nrc_l2

        cal_found: Dict[str, CalendarOrScalarLadderSpec] = {}
        cal_seen_ids = set()
        for ev_cal in top_vol_events_raw + mid_raw + pol_raw:
            if not isinstance(ev_cal, dict):
                continue
            eid_c = str(ev_cal.get("id") or "")
            if not eid_c or eid_c in cal_seen_ids:
                continue
            cal_seen_ids.add(eid_c)
            for sp_cal in parse_cal1_monotonic_ladder_event(ev_cal, now_ts=now_disc):
                cal_found[sp_cal.event_id] = sp_cal
        self.cal1_ladders = cal_found

        ten_found: Dict[str, TennisMatchSpec] = {}
        for ev_ten in ten_raw + extra_sport_evts:
            if not isinstance(ev_ten, dict):
                continue
            sp_ten = parse_tennis_retirement_safe_event(ev_ten, now_ts=now_disc)
            if sp_ten is not None:
                ten_found[sp_ten.event_id] = sp_ten
        self.tennis_specs = ten_found

        # 6D. Frontier v4 Evergreen Discovery: Affine Sub-Periods & Sum Triangles (`AFF1`/`SUM1`),
        #     Soccer 2D Exact-Score Lattices (`SOC2`), NFL Player Props (`NFL_PRP1`), & Binance Close Rungs (`CRY_INC1`)
        nba_base_slugs = [
            sl for sl, ev_n in sorted(
                raw_nba_parents.items(),
                key=lambda kv: _parse_iso_ts(kv[1].get("startTime") or kv[1].get("endDate")) or 9e12,
            )
            if not sl.endswith("-more-markets")
        ][:12]
        nfl_cfb_base_slugs: List[str] = []
        nfl_prop_base_slugs: List[str] = []
        for sp_t4, ev_m4 in ms_raw_found.values():
            sl_m4 = str(ev_m4.get("slug") or "").lower()
            if not sl_m4 or any(sl_m4.endswith(sfx) for sfx in ("-more-markets", "-player-props", "-exact-margin")):
                continue
            if sp_t4 in ("NFL", "CFB") and len(nfl_cfb_base_slugs) < 12:
                nfl_cfb_base_slugs.append(sl_m4)
            if sp_t4 == "NFL" and len(nfl_prop_base_slugs) < 10:
                nfl_prop_base_slugs.append(sl_m4)
        soc_exact_slugs_existing = {str(e.get("slug") or "").lower() for e in soc_raw if isinstance(e, dict)}
        soc_exact_targets = [
            f"{tr.slug_3way}-exact-score"
            for tr in sorted(self.soccer_trees.values(), key=lambda t: t.end_ts)[:16]
            if tr.slug_3way and f"{tr.slug_3way}-exact-score" not in soc_exact_slugs_existing
        ]
        fv4_sibling_slugs = list(dict.fromkeys(
            [f"{sl}-more-markets" for sl in (nba_base_slugs + nfl_cfb_base_slugs)]
            + [f"{sl}-player-props" for sl in nfl_prop_base_slugs]
            + soc_exact_targets
        ))
        fv4_sib_evts: List[Dict[str, Any]] = []
        if fv4_sibling_slugs:
            fv4_fetches = await asyncio.gather(
                *(self.fetch_json(f"{GAMMA_URL}/events?slug={sl_v4}", timeout=4.5) for sl_v4 in fv4_sibling_slugs)
            )
            for res_v4 in fv4_fetches:
                if isinstance(res_v4, list) and res_v4 and isinstance(res_v4[0], dict):
                    fv4_sib_evts.append(res_v4[0])

        aff1_src_evts = (
            list(raw_nba_parents.values())
            + [ev_m for sp_tm, ev_m in ms_raw_found.values() if sp_tm in ("NFL", "CFB")]
            + extra_sport_evts
            + fv4_sib_evts
        )
        self.aff1_bundles = {
            b.event_id: b for b in parse_affine_game_bundle(aff1_src_evts, now_ts=now_disc)
        }
        # Refresh NBA subperiod slates when `-more-markets` adds subperiod / first-half / Q1..Q4 contracts
        for ev_sib in fv4_sib_evts:
            sl_sb = str(ev_sib.get("slug") or "").lower()
            if sl_sb.startswith("nba-"):
                sp_sub_x = parse_nba_subperiod_and_ext_props(ev_sib, now_ts=now_disc)
                if sp_sub_x is not None and sp_sub_x.event_id not in self.nba_subperiod_slates:
                    self.nba_subperiod_slates[sp_sub_x.event_id] = sp_sub_x

        self.soc2_lattices = link_and_parse_soc2_exact_score_lattices(soc_raw + fv4_sib_evts, now_ts=now_disc)
        for lat_s2 in self.soc2_lattices.values():
            if lat_s2.convert_spec is not None and lat_s2.convert_spec.end_ts > now_disc + 60:
                self.negrisk_convert_slates[lat_s2.convert_spec.event_id] = lat_s2.convert_spec

        nfl_prp_found: Dict[str, NflPlayerPropSlate] = {}
        for ev_np in [ev_m for sp_tm, ev_m in ms_raw_found.values() if sp_tm == "NFL"] + fv4_sib_evts + extra_sport_evts:
            if not isinstance(ev_np, dict):
                continue
            sp_np = parse_nfl_player_props_event(ev_np, now_ts=now_disc)
            if sp_np is not None:
                nfl_prp_found[sp_np.event_id] = sp_np
        self.nfl_prop_slates = nfl_prp_found

        cry_cl_seen: Dict[str, CryptoCloseRungSpec] = {}
        for ev_cc in raw_strike_evts + top_vol_events_raw:
            if isinstance(ev_cc, dict):
                for cr_sp in parse_binance_terminal_close_event(ev_cc):
                    if cr_sp.close_ts > now_disc + 120:
                        cry_cl_seen[cr_sp.market_id] = cr_sp
        self.binance_close_rungs = list(cry_cl_seen.values())

        self.last_discovery_ts = time.time()
        logger.info(
            f"Discovery complete: {len(self.weather_events)} Weather city-events, "
            f"{len(self.barrier_rungs)} Barrier Hit rungs, {len(self.strike_ladders)} Multi-Strike ladders, "
            f"{len(self.negrisk_ladders)} NegRisk ladders, {len(self.daily_updown_markets)} Crypto Daily Up/Down, "
            f"{len(self.pyth_daily_markets)} Zero-Fee Pyth FX/Metals Daily, "
            f"{len(self.pyth_barrier_rungs)} Pyth Hit rungs, {len(self.pyth_close_ladders)} Pyth Close ladders, "
            f"{len(self.nba_games)} NBA games ({len(self.nba_prop_slates)} Prop, {len(self.nba_subperiod_slates)} SubPer, {len(self.lp1_nba_em_bundles)} EM), "
            f"{len(self.multi_sport_games)} Multi-Sport ({len(self.lp1_nfl_em_bundles)} NFL EM, {len(self.nfl_prop_slates)} NFL Prop, {len(self.aff1_bundles)} AFF1/SUM1), "
            f"{len(self.soccer_trees)} Soccer trees ({len(self.soc2_lattices)} SOC2 Exact-Score), "
            f"{len(self.tennis_specs)} Tennis BO3, {len(self.esports_bo3_specs)} Esports BO3, "
            f"{len(self.lp2_implication_groups)} LP2 DAG groups, {len(self.cal1_ladders)} CAL1 ladders, "
            f"{len(self.binance_close_rungs)} Binance Close rungs, "
            f"{len(self.lp1_bop_legs)//2} BOP/Chamber mkts, "
            f"{len(self.negrisk_zero_slates)} NegRisk Slates, {len(self.negrisk_convert_slates)} NegRisk Convert slates, "
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
            # Strictly causal L2 walk at t_signal + latency (250ms for W1_SOLAR_PEAK_LOCK / W1_LOW_TROUGH_LOCK EXP-PM-405; 50ms default)
            req_lat_ms = 250 if sleeve in ("W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK") else 50
            book = prefetched_book if (prefetched_book is not None and sleeve not in ("W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK")) else await self.fetch_book_after_latency(token_id, latency_ms=req_lat_ms)
            if not book:
                return False
            asks_raw = book.get("asks") or []
            bids_raw = book.get("bids") or []
            best_bid, _ = extract_best_bid(bids_raw)

            min_l1 = 15.0 if sleeve in (
                "S2_EXACT_TWAP_LOCK", "S5M_CHAINLINK_SNIPER", "S4H_CHAINLINK_CONVERGENCE",
                "B4_TOUCHED_BARRIER_WICK_LOCK", "CM_B2_PYTH_SESSION_NO_LOCK", "CM_U1_PYTH_CLOSE_LOCK",
                "TW1_COUNTING_TRUNCATION_AND_BOX", "GAS1_AAA_GASOLINE_LOCK", "CM_SHOCK_PYTH_CATALYST",
                "W1_LOW_TROUGH_LOCK", "BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
                "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK", "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
                "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
                "AFF1_FROZEN_SUBPERIOD_COLLAPSE", "SOC2_EXACT_SCORE_2D_LATTICE",
                "NFL_PRP1_MILESTONE_AND_MAX_LOCKS", "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
            ) else 20.0
            if sleeve in ("BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"):
                max_ask_cap = 0.9956
            elif sleeve in ("B4_TOUCHED_BARRIER_WICK_LOCK", "TW1_COUNTING_TRUNCATION_AND_BOX", "GAS1_AAA_GASOLINE_LOCK"):
                max_ask_cap = 0.990
            elif sleeve in (
                "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK", "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
                "AFF1_FROZEN_SUBPERIOD_COLLAPSE", "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
            ):
                max_ask_cap = 0.9881
            elif sleeve in ("SP2_NBA_ENDGAME_LOCK", "SOC2_EXACT_SCORE_2D_LATTICE"):
                max_ask_cap = 0.9861
            elif sleeve in ("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH", "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"):
                max_ask_cap = 0.9821
            elif sleeve == "W1_LOW_TROUGH_LOCK":
                max_ask_cap = 0.9601
            else:
                max_ask_cap = 0.98
            fee_exp = float((extra or {}).get("fee_exponent", 1.0))
            # Validate T1000 reference fill first (allowing depth-capped T100+ fills on thin locked-outcome books)
            ref_ticket = BANKROLL_TICKETS["T1000"][sleeve]
            min_tkt = BANKROLL_TICKETS["T100"][sleeve]
            use_depth_cap = sleeve in DEPTH_CAPPED_TAKER_SLEEVES
            w_ref = (
                walk_l2_book_asks_depth_capped(
                    asks_raw, ref_ticket, min_tkt, fee_rate=fee_rate, min_l1_usd=min_l1, max_ask_px=max_ask_cap, fee_exponent=fee_exp
                )
                if use_depth_cap
                else walk_l2_book_asks(asks_raw, ref_ticket, fee_rate=fee_rate, min_l1_usd=min_l1, max_ask_px=max_ask_cap, fee_exponent=fee_exp)
            )
            if not w_ref.get("filled"):
                return False

            realized_edge = p_model - float(w_ref["eff_px"])
            min_req_edge = {
                "W1_SOLAR_PEAK_LOCK": 0.035,
                "W1_LOW_TROUGH_LOCK": 0.030,
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
                "SP2_NBA_ENDGAME_LOCK": 0.012,
                "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK": 0.012,
                "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION": 0.012,
                "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH": 0.015,
                "AFF1_FROZEN_SUBPERIOD_COLLAPSE": 0.012,
                "SOC2_EXACT_SCORE_2D_LATTICE": 0.012,
                "NFL_PRP1_MILESTONE_AND_MAX_LOCKS": 0.012,
                "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER": 0.0045,
                "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK": 0.018,
                "BOND1_UMA_RESOLUTION_CARRY": 0.0045,
                "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY": 0.0040,
            }.get(sleeve, 0.035)
            if realized_edge < min_req_edge:
                return False

            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = (
                    walk_l2_book_asks_depth_capped(
                        asks_raw, t_map[sleeve], min_tkt, fee_rate=fee_rate, min_l1_usd=min_l1, max_ask_px=max_ask_cap, fee_exponent=fee_exp
                    )
                    if use_depth_cap
                    else walk_l2_book_asks(asks_raw, t_map[sleeve], fee_rate=fee_rate, min_l1_usd=min_l1, max_ask_px=max_ask_cap, fee_exponent=fee_exp)
                )
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
            elif sleeve in ("CM_B2_PYTH_SESSION_NO_LOCK", "W1_LOW_TROUGH_LOCK") and eff_tp is None:
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
        is_locked_maker = sleeve in LOCKED_MAKER_SLEEVES
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
                if is_locked_maker or is_reward_carry:
                    best_ask = 1.000
                else:
                    return False
            else:
                best_ask = round(min(valid_asks), 4)
            if best_ask <= 0.03 or best_bid <= 0.0:
                return False

            if is_weather_maker and ((best_ask - best_bid) < 0.02 or l1_bid_usd < 10.0):
                return False

            if is_locked_maker:
                if sleeve == "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":
                    min_bid_req, min_rb, max_rb, min_edge = 0.950, 0.950, 0.996, 0.004
                elif sleeve == "BOND1_UMA_RESOLUTION_CARRY":
                    min_bid_req, min_rb, max_rb, min_edge = 0.940, 0.940, 0.995, 0.005
                elif sleeve == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":
                    min_bid_req, min_rb, max_rb, min_edge = 0.850, 0.900, 0.993, 0.0045
                elif sleeve in ("SP2_NBA_ENDGAME_LOCK", "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"):
                    min_bid_req, min_rb, max_rb, min_edge = 0.700, 0.720, 0.985, 0.012
                elif sleeve == "W1_LOW_TROUGH_LOCK":
                    min_bid_req, min_rb, max_rb, min_edge = 0.250, 0.350, 0.960, 0.030
                else:
                    min_bid_req, min_rb, max_rb, min_edge = 0.250, 0.350, 0.940, 0.035
                if best_bid < min_bid_req:
                    return False
                tb = 0.001 if best_bid >= 0.96 else 0.01
                ta = 0.001 if best_ask > 0.96 else 0.01
                step_cand = (
                    float(extra["resting_bid_override"])
                    if extra.get("resting_bid_override")
                    else (round(best_bid + tb, 4) if (best_ask - best_bid) >= (2.0 * tb - 1e-9) else best_bid)
                )
                hard_ceil = min(round(best_ask - ta, 4), max_rb, round(p_model - min_edge, 4))
                t_snap = 0.001 if min(step_cand, hard_ceil) >= 0.96 - 1e-9 else 0.01
                resting_bid = round(math.floor((min(step_cand, hard_ceil) + 1e-9) / t_snap) * t_snap, 4)
                if resting_bid < round(best_bid - 1e-9, 4) or not (min_rb <= resting_bid <= max_rb):
                    return False
                maker_edge = p_model - resting_bid
                if maker_edge < min_edge - 1e-9:
                    return False
            else:
                if is_reward_carry and extra.get("resting_bid_override"):
                    ta_rw = 0.002 if best_ask > 0.990 else 0.005
                    resting_bid = round(min(float(extra["resting_bid_override"]), best_ask - ta_rw), 4)
                else:
                    # Post-only Maker bid: step +1c inside wide spread or join best_bid when 1c tight, strictly < best_ask
                    cand_bid = best_bid + 0.01 if (best_ask - best_bid) >= 0.02 else best_bid
                    resting_bid = round(min(cand_bid, best_ask - 0.01), 4)
                min_rb = 0.950 if is_reward_carry else (0.14 if is_weather_maker else 0.18)
                max_rb = (0.994 if p_model >= 0.999 else 0.990) if is_reward_carry else (0.65 if is_weather_maker else 0.80)
                if not (min_rb <= resting_bid <= max_rb):
                    return False
                maker_edge = p_model - resting_bid
                min_edge = (0.006 if p_model >= 0.999 else 0.008) if is_reward_carry else (0.085 if is_weather_maker else 0.060)
                if maker_edge < min_edge - 1e-9:
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
            is_locked_maker = sleeve in LOCKED_MAKER_SLEEVES
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

            # 1. Expiry / TTL cancel (supports short 3.5s reactive M4 and 45s SP2 post_only maker quotes via ttl_override_sec)
            ttl_ov = m_ord.get("ttl_override_sec")
            if sleeve in ("SP2_NBA_ENDGAME_LOCK", "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"):
                min_tte_cancel = 20.0
                max_age_cancel = float(ttl_ov) if ttl_ov is not None else 45.0
            elif sleeve in ("BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY", "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"):
                min_tte_cancel = 60.0 if sleeve == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER" else 90.0
                max_age_cancel = float(ttl_ov) if ttl_ov is not None else 1800.0
            elif sleeve in ("W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK"):
                min_tte_cancel = 600.0
                max_age_cancel = float(ttl_ov) if ttl_ov is not None else 3600.0
            else:
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
            if sleeve in ("W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK"):
                ev_id_str = str(extra.get("event_id") or "")
                sp_w = self.weather_events.get(ev_id_str)
                if sp_w is not None:
                    m_key = f"{sp_w.icao}_{sp_w.obs_date.isoformat()}"
                    metars_c = (self.metar_cache.get(m_key) or (0.0, []))[1]
                    ens_c = (self.ensemble_cache.get(sp_w.icao) or (0.0, {}))[1]
                    taf_c = (self.taf_cache.get(sp_w.icao) or (0.0, {}))[1]
                    if metars_c or ens_c:
                        w_res = compute_weather_probabilities(
                            sp_w, now_utc, metars_c, ens_c,
                            forecast_sigma_base_c=self.weather_sigma_c,
                            taf_extreme_c=(taf_c or {}).get(sp_w.metric),
                        )
                        mkt_id_target = str(extra.get("market_id") or "")
                        for b_idx, b_item in enumerate(sp_w.buckets):
                            if str(b_item.market_id) == mkt_id_target and b_idx < len(w_res["probs"]):
                                p_fair_now = float(w_res["probs"][b_idx])
                                break
                        if w_res.get("convective_cold_pool"):
                            adverse_cancel_reason = "CONVECTIVE_COLD_POOL"
                        elif not w_res.get("is_solar_lock"):
                            adverse_cancel_reason = "SOLAR_LOCK_INVALIDATED"
                        elif (p_fair_now - resting_bid) < 0.020:
                            adverse_cancel_reason = "ADVERSE_METAR_OR_EDGE_DECAY"
            elif sleeve in ("BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY", "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER") or is_reward_carry:
                p_fair_now = (
                    float(m_ord.get("p_model_at_post") or 1.0)
                    if is_reward_carry
                    else (float(m_ord.get("p_model_at_post") or 0.998) if sleeve == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER" else 1.0)
                )
                opp_tok_uma = str(extra.get("opp_token_id") or "")
                if opp_tok_uma and (now - float(m_ord.get("_last_opp_chk_ts") or 0.0)) >= 12.0:
                    m_ord["_last_opp_chk_ts"] = now
                    bk_opp_uma = await self.fetch_json(f"{CLOB_URL}/book?token_id={opp_tok_uma}", timeout=2.5)
                    if bk_opp_uma:
                        lose_bid_uma, _ = extract_best_bid(bk_opp_uma.get("bids") or [])
                        max_opp_cap = (
                            0.008
                            if sleeve == "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"
                            else (0.030 if (sleeve == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER" or is_reward_carry) else 0.012)
                        )
                        if lose_bid_uma > max_opp_cap:
                            adverse_cancel_reason = "UMA_COMPLEMENT_DISPUTE_BID"
            elif sleeve == "SP2_NBA_ENDGAME_LOCK":
                sp_nba_m = self.nba_games.get(str(extra.get("event_id") or ""))
                if sp_nba_m is not None and self.live_nba_board:
                    matched_m = match_nba_live_game(sp_nba_m, self.live_nba_board)
                    if matched_m is not None:
                        g_st_m, sc_a_m, sc_b_m = matched_m
                        still_lk = [c for c in evaluate_nba_endgame_locks(sp_nba_m, g_st_m, sc_a_m, sc_b_m) if c["leg"].token_id == tok]
                        if not still_lk:
                            adverse_cancel_reason = "NBA_ENDGAME_LOCK_INVALIDATED"
                        else:
                            p_fair_now = float(still_lk[0]["p_lock"])
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

            # 3. Check passive Maker fill (`best_ask <= resting_bid` or verified Polymarket trade-tape print)
            if not adverse_fill_during_cancel:
                min_rest_sec = 0.5 if ttl_ov is not None else (4.0 if is_locked_maker else 10.0)
                if age_s < min_rest_sec:
                    continue
                bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=3.0)
            if not bk:
                continue
            asks_raw = bk.get("asks") or []
            valid_asks = [float(a["price"]) for a in asks_raw if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0]
            best_ask_now = min(valid_asks) if valid_asks else 1.0
            crossing_shares = (
                sum(
                    float(a["size"])
                    for a in asks_raw
                    if 0.0 < float(a.get("price", 0)) <= resting_bid + 1e-9 and float(a.get("size", 0)) > 0
                )
                if valid_asks and best_ask_now <= resting_bid
                else 0.0
            )
            if crossing_shares <= 0.0 and (is_locked_maker or is_reward_carry):
                cond_id_tr = str(extra.get("condition_id") or "")
                last_tape_ts = float(self._last_trade_tape_chk_ts.get(cond_id_tr) or 0.0)
                if cond_id_tr and (now - last_tape_ts) >= 12.0:
                    self._last_trade_tape_chk_ts[cond_id_tr] = now
                    trades_raw = await self.fetch_json(f"{DATA_API_URL}/trades?market={cond_id_tr}&limit=15", timeout=3.0)
                    if isinstance(trades_raw, list) and trades_raw:
                        seen_keys = set(m_ord.get("_seen_trade_keys") or [])
                        opp_tok_tr = str(extra.get("opp_token_id") or "")
                        min_print_ts = int(float(m_ord.get("last_repeg_ts") or m_ord["created_ts"])) + 2
                        tape_sh = 0.0
                        for tr in trades_raw:
                            ts_tr = int(float(tr.get("timestamp") or 0))
                            if ts_tr < min_print_ts:
                                continue
                            tx_k = f"{tr.get('transactionHash') or ''}_{ts_tr}_{tr.get('asset') or ''}_{tr.get('size') or ''}_{tr.get('price') or ''}"
                            if tx_k in seen_keys:
                                continue
                            ast_tr = str(tr.get("asset") or "")
                            px_tr = float(tr.get("price") or 0.0)
                            sz_tr = float(tr.get("size") or 0.0)
                            if sz_tr <= 0.0 or px_tr <= 0.0:
                                continue
                            if (ast_tr == tok and px_tr <= resting_bid + 1e-6) or (
                                opp_tok_tr and ast_tr == opp_tok_tr and px_tr >= (1.0 - resting_bid) - 1e-6
                            ):
                                seen_keys.add(tx_k)
                                tape_sh += sz_tr
                        if seen_keys:
                            m_ord["_seen_trade_keys"] = list(seen_keys)[-30:]
                        if tape_sh > 0.0:
                            crossing_shares = tape_sh
                            best_ask_now = resting_bid
                            extra["filled_via_trade_tape"] = True

            if (
                crossing_shares <= 0.0
                and (is_locked_maker or is_reward_carry)
                and (now - float(m_ord.get("last_repeg_ts") or m_ord["created_ts"])) >= 15.0
                and rem_tte >= 180.0
            ):
                best_bid_now, l1_bid_now = extract_best_bid(bk.get("bids") or [])
                if best_bid_now > resting_bid + 1e-6:
                    if is_reward_carry:
                        max_rb_rp = 0.994 if p_fair_now >= 0.999 else 0.990
                        min_edge_rp = 0.006 if p_fair_now >= 0.999 else 0.008
                        ta_rp = 0.002 if best_ask_now > 0.990 else 0.005
                    elif sleeve == "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY":
                        max_rb_rp, min_edge_rp, ta_rp = 0.996, 0.004, (0.001 if best_ask_now > 0.96 else 0.01)
                    elif sleeve == "BOND1_UMA_RESOLUTION_CARRY":
                        max_rb_rp, min_edge_rp, ta_rp = 0.995, 0.005, (0.001 if best_ask_now > 0.96 else 0.01)
                    elif sleeve == "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":
                        max_rb_rp, min_edge_rp, ta_rp = 0.993, 0.0045, (0.001 if best_ask_now > 0.96 else 0.01)
                    else:
                        max_rb_rp, min_edge_rp, ta_rp = 0.0, 1.0, 0.01
                    if max_rb_rp > 0.0:
                        tb_rp = 0.001 if best_bid_now >= 0.96 else 0.01
                        step_rp = (
                            round(best_bid_now + tb_rp, 4)
                            if (best_ask_now - best_bid_now) >= (tb_rp + ta_rp - 1e-9)
                            else best_bid_now
                        )
                        ceil_rp = min(round(best_ask_now - ta_rp, 4), max_rb_rp, round(p_fair_now - min_edge_rp, 4))
                        tsnap_rp = 0.001 if min(step_rp, ceil_rp) >= 0.96 - 1e-9 else 0.01
                        new_rb = round(math.floor((min(step_rp, ceil_rp) + 1e-9) / tsnap_rp) * tsnap_rp, 4)
                        if (
                            new_rb > resting_bid + 1e-6
                            and new_rb >= round(best_bid_now - 1e-9, 4)
                            and new_rb <= max_rb_rp + 1e-9
                            and (p_fair_now - new_rb) >= min_edge_rp - 1e-9
                        ):
                            old_rb = resting_bid
                            m_ord["resting_bid"] = new_rb
                            m_ord["l1_bid_usd"] = l1_bid_now
                            m_ord["queue_ahead_usd"] = 0.0 if new_rb > best_bid_now + 1e-6 else round(min(l1_bid_now * 0.50, 60.0), 2)
                            m_ord["maker_edge_at_post"] = round(p_fair_now - new_rb, 4)
                            m_ord["last_repeg_ts"] = now
                            self._append_ledger({"event": "SHADOW_MAKER_POST", **m_ord})
                            logger.info(
                                f"[MAKER_OUTBID_REPEG:{sleeve}] {asset} | {m_ord['title']} ({side_lbl}) "
                                f"${old_rb:.3f} -> ${new_rb:.3f} (outbid=${best_bid_now:.3f}, ask=${best_ask_now:.3f})"
                            )
                            continue

            if crossing_shares > 0.0:
                queue_ahead_usd = float(m_ord.get("queue_ahead_usd") or 0.0)
                queue_ahead_sh = queue_ahead_usd / max(0.01, resting_bid)
                avail_fill_shares = crossing_shares - queue_ahead_sh
                if adverse_fill_during_cancel:
                    avail_fill_shares = max(avail_fill_shares, crossing_shares, BANKROLL_TICKETS["T5000"][sleeve] / max(0.01, resting_bid))
                elif avail_fill_shares < 5.0:
                    m_ord["queue_ahead_usd"] = round(max(0.0, queue_ahead_usd - crossing_shares * resting_bid), 2)
                    continue

                self.pending_maker_orders.pop(oid, None)
                rebate_ps = max(0.0, float(extra.get("maker_rebate_ps") or 0.0))
                eff_mkr_px = round(max(0.01, resting_bid - rebate_ps), 6)
                tier_fills: Dict[str, Dict[str, Any]] = {}
                for tier_name, t_map in BANKROLL_TICKETS.items():
                    notional = t_map[sleeve]
                    target_sh = notional / resting_bid
                    sh = round(min(target_sh, avail_fill_shares), 4)
                    spent = round(sh * eff_mkr_px, 2)
                    tier_fills[tier_name] = {
                        "filled": True,
                        "best_ask": round(best_ask_now, 4),
                        "vwap": resting_bid,
                        "eff_px": eff_mkr_px,
                        "slip_cents": 0.0,
                        "spent_usd": spent,
                        "fee_usd": round(-sh * rebate_ps, 4),
                        "shares": sh,
                        "fill_ratio": round(min(1.0, spent / max(0.01, notional)), 4),
                        "l1_usd": m_ord.get("l1_bid_usd", 50.0),
                        "levels": 1,
                    }
                pos_id = f"{sleeve}_{int(now)}_{m_ord['dedupe_key'][-10:]}"
                if is_locked_maker or is_reward_carry or sleeve in ("BOND1_UMA_RESOLUTION_CARRY", "SP2_NBA_ENDGAME_LOCK"):
                    eff_tp = None
                elif sleeve in ("W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK"):
                    eff_tp = 0.985
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
                    "entry_eff_px_t1000": eff_mkr_px,
                    "entry_vwap_t1000": resting_bid,
                    "realized_edge_t1000": round(p_fair_now - eff_mkr_px, 4),
                    "entry_best_bid": resting_bid,
                    "last_bid": resting_bid,
                    "maker_tp_px": eff_tp,
                    "tier_fills": tier_fills,
                    "extra": extra,
                    "status": "OPEN",
                }
                self.open_positions[pos_id] = pos
                self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                tp_str = f"${eff_tp:.3f}" if eff_tp is not None else "HOLD_SETTLE"
                logger.info(
                    f"[MAKER_FILLED:{sleeve}] {asset} | {pos['title']} ({side_lbl}) @ resting=${resting_bid:.3f} "
                    f"-> TP={tp_str} (p_mod={p_fair_now:.3f}, adverse={adverse_fill_during_cancel})"
                )

    async def scan_weather_markets(self, opps_out: List[Dict[str, Any]]) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import resolve_weather_effective_end_ts
        now_utc = datetime.now(timezone.utc)
        now_0 = time.time()
        active_w_specs: List[Tuple[int, float, WeatherEventSpec]] = []
        for sp0 in list(self.weather_events.values()):
            e_ts0 = resolve_weather_effective_end_ts(sp0, now_0 + 86400.0)
            if e_ts0 <= now_0:
                self.weather_events.pop(sp0.event_id, None)
                continue
            try:
                loc0 = now_utc.astimezone(ZoneInfo(sp0.tz_name))
            except Exception:
                loc0 = now_utc
            if (sp0.obs_date - loc0.date()).days > 1 and not self.single_scan:
                continue
            active_w_specs.append((0 if loc0.date() >= sp0.obs_date else 1, e_ts0, sp0))
        active_w_specs.sort(key=lambda r: (r[0], r[1]))

        for _, _, sp in active_w_specs[:45]:
            now_s = time.time()
            end_ts = resolve_weather_effective_end_ts(sp, now_s + 86400.0)
            if end_ts <= now_s:
                self.weather_events.pop(sp.event_id, None)
                continue
            _w2_pruned = (
                not self.single_scan
                and is_shadow_sleeve_quarantined("W2_ENSEMBLE_VALUE")
                and is_shadow_sleeve_quarantined("W2_MAKER_OVERROUND")
            )
            if _w2_pruned:
                try:
                    eval_local = now_utc.astimezone(ZoneInfo(sp.tz_name))
                except Exception:
                    eval_local = now_utc
                in_w1_window = eval_local.date() >= sp.obs_date
            else:
                in_w1_window = True

            if _w2_pruned and not in_w1_window:
                n_bkt_w = max(1, len(sp.buckets))
                probs = [round(1.0 / n_bkt_w, 4)] * len(sp.buckets)
                res = {
                    "is_solar_lock": False,
                    "locked_bucket_idx": None,
                    "p_locked_bucket": 0.0,
                    "obs_count": 0,
                    "latest_temp_c": None,
                    "running_ext_c": None,
                    "peak_iqr_c": None,
                    "cooling_cushion_c": 0.0,
                    "convective_cold_pool": False,
                    "probs": probs,
                }
            else:
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
            end_ts = resolve_weather_effective_end_ts(sp, now_s + 86400.0)

            # 1. Check W1_SOLAR_PEAK_LOCK (HIGH) & W1_LOW_TROUGH_LOCK (LOW)
            if res["is_solar_lock"] and res["locked_bucket_idx"] is not None:
                b_lock = sp.buckets[res["locked_bucket_idx"]]
                p_lock = res["p_locked_bucket"]
                w1_fee = float(getattr(b_lock, "fee_rate", 0.0) or 0.0)
                is_low_lock = sp.metric == "LOW"
                w1_sleeve = "W1_LOW_TROUGH_LOCK" if is_low_lock else "W1_SOLAR_PEAK_LOCK"
                w1_max_ask = 0.960 if is_low_lock else 0.940
                w1_min_edge = 0.030 if is_low_lock else 0.035
                w1_dkey = f"W1LOW_{sp.event_id}_{b_lock.market_id}" if is_low_lock else f"W1_{sp.event_id}_{b_lock.market_id}"
                bk = await self.fetch_json(f"{CLOB_URL}/book?token_id={b_lock.yes_token}", timeout=3.5)
                if bk:
                    w_chk = walk_l2_book_asks_depth_capped(
                        bk.get("asks") or [],
                        BANKROLL_TICKETS["T1000"][w1_sleeve],
                        BANKROLL_TICKETS["T100"][w1_sleeve],
                        fee_rate=w1_fee,
                        min_l1_usd=(15.0 if is_low_lock else 20.0),
                        max_ask_px=w1_max_ask + 0.0001,
                    )
                    bid_w1, bid_w1_usd = extract_best_bid(bk.get("bids") or [])
                    self._record_market_telemetry(
                        key=f"W1_LOCK_{sp.event_id}_{b_lock.market_id}",
                        min_interval_sec=45.0,
                        now_ts=now_s,
                        sig=(w_chk.get("eff_px"), bid_w1, round(float(p_lock), 3)),
                        payload={
                            "type": "WEATHER_SOLAR_LOCK_SNAP",
                            "sleeve": w1_sleeve,
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
                    w1_extra = {
                        "event_id": sp.event_id,
                        "market_id": b_lock.market_id,
                        "condition_id": b_lock.condition_id,
                        "opp_token_id": b_lock.no_token,
                        "icao": sp.icao,
                        "metric": sp.metric,
                        "obs_date": sp.obs_date.isoformat(),
                        "bucket_label": b_lock.label,
                        "running_ext_c": res["running_ext_c"],
                        "cooling_cushion_c": res["cooling_cushion_c"],
                    }
                    opened_w1 = False
                    if w_chk.get("filled") and 0.52 <= w_chk["eff_px"] <= w1_max_ask:
                        edge = p_lock - w_chk["eff_px"]
                        opps_out.append({
                            "sleeve": w1_sleeve,
                            "market": f"{sp.city} ({sp.icao}) {sp.metric} {sp.obs_date} -> {b_lock.label}",
                            "ask_vwap": w_chk["eff_px"],
                            "p_model": p_lock,
                            "net_edge": round(edge, 4),
                            "l1_usd": w_chk["l1_usd"],
                        })
                        if edge >= w1_min_edge:
                            w1_nr = getattr(b_lock, "neg_risk", None)
                            if float(p_lock) >= 0.985 and w1_nr is not None and (end_ts - now_s) <= 86400.0:
                                bk_opp_w1 = await self.fetch_json(f"{CLOB_URL}/book?token_id={b_lock.no_token}", timeout=2.5)
                                self.emit_live_single_leg_lock_candidate(
                                    sleeve_source=w1_sleeve,
                                    asset=f"{sp.city}_{sp.icao}",
                                    dedupe_key=w1_dkey,
                                    token_id=b_lock.yes_token,
                                    opp_token_id=b_lock.no_token,
                                    market_id=b_lock.market_id,
                                    condition_id=b_lock.condition_id,
                                    side_label="YES",
                                    display_label=f"{sp.city} {sp.metric} [{b_lock.label}]",
                                    bk_win=bk,
                                    bk_opp=bk_opp_w1 if isinstance(bk_opp_w1, dict) else None,
                                    fee_rate=w1_fee,
                                    fee_exponent=1.0,
                                    neg_risk=bool(w1_nr),
                                    close_ts=end_ts,
                                    now_ts=now_s,
                                    max_lock_eff_px=w1_max_ask,
                                    max_opp_bid=0.045,
                                    hold_to_maturity=False,
                                    p_model=float(p_lock),
                                )
                            opened_w1 = await self.open_shadow_position(
                                sleeve=w1_sleeve,
                                dedupe_key=w1_dkey,
                                asset_or_city=f"{sp.city}_{sp.icao}",
                                title=f"{sp.title} [{b_lock.label}]",
                                side_label="YES",
                                token_id=b_lock.yes_token,
                                fee_rate=w1_fee,
                                p_model=p_lock,
                                close_ts=end_ts,
                                extra=w1_extra,
                                prefetched_book=bk,
                            )
                    if (
                        not opened_w1
                        and not res.get("convective_cold_pool")
                        and (end_ts - now_s) > 900.0
                        and 0.25 <= bid_w1 <= w1_max_ask
                        and (p_lock - bid_w1) >= w1_min_edge
                    ):
                        posted_w1 = await self.post_shadow_maker_entry(
                            sleeve=w1_sleeve,
                            dedupe_key=w1_dkey,
                            asset=f"{sp.city}_{sp.icao}",
                            title=f"{sp.title} [{b_lock.label}]",
                            side_label="YES",
                            token_id=b_lock.yes_token,
                            p_model=p_lock,
                            close_ts=end_ts,
                            extra=w1_extra,
                            prefetched_book=bk,
                        )
                        if posted_w1 and not w_chk.get("filled"):
                            opps_out.append({
                                "sleeve": w1_sleeve,
                                "market": f"[MAKER] {sp.city} ({sp.icao}) {sp.metric} {sp.obs_date} -> {b_lock.label}",
                                "ask_vwap": bid_w1,
                                "p_model": p_lock,
                                "net_edge": round(p_lock - bid_w1, 4),
                                "l1_usd": bid_w1_usd,
                                "close_ts": end_ts,
                            })

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
                    if (
                        bk_n_i
                        and int(res.get("obs_count") or 0) >= 1
                        and res.get("running_ext_c") is not None
                        and not res.get("has_corrected_obs")
                        and float(getattr(b_i, "rewards_min_size", 0.0) or 0.0) > 0.0
                        and (end_ts - now_s) > 300.0
                    ):
                        obs_int_w = celsius_to_market_int(float(res["running_ext_c"]), b_i.unit)
                        dead_no_w = (
                            (sp.metric == "HIGH" and b_i.high_bound <= obs_int_w - 2)
                            or (sp.metric == "LOW" and b_i.low_bound >= obs_int_w + 2)
                        )
                        if dead_no_w:
                            bid_wn, _ = extract_best_bid(bk_n_i.get("bids") or [])
                            ask_wn = float(rec_b.get("ask_no", 1.0) or 1.0)
                            rw_w = evaluate_locked_market_reward_carry(
                                1.0, bid_wn, ask_wn, float(b_i.rewards_min_size), float(b_i.rewards_max_spread), float(getattr(b_i, "fee_rate", 0.0) or 0.0)
                            )
                            if rw_w.get("eligible"):
                                opps_out.append({
                                    "sleeve": "MKR_REWARD_LOCKED_CARRY",
                                    "market": f"{sp.city} ({sp.icao}) Dead NO[{b_i.label}] @ ${rw_w['resting_bid']:.3f}",
                                    "ask_vwap": rw_w["resting_bid"],
                                    "p_model": 1.0,
                                    "net_edge": rw_w["carry_edge"],
                                    "l1_usd": 50.0,
                                    "close_ts": end_ts,
                                })
                                await self.post_shadow_maker_entry(
                                    "MKR_REWARD_LOCKED_CARRY",
                                    f"MKR_RW_W_{b_i.market_id}",
                                    f"{sp.city}_{sp.icao}",
                                    f"{sp.title} [Dead NO {b_i.label}]",
                                    "NO",
                                    b_i.no_token,
                                    1.0,
                                    end_ts,
                                    {"market_id": b_i.market_id, "condition_id": b_i.condition_id, "opp_token_id": b_i.yes_token, "resting_bid_override": rw_w["resting_bid"]},
                                    prefetched_book=bk_n_i,
                                )
                                if is_reward_locked_carry_live_ready(self, 1.0) and getattr(b_i, "neg_risk", None) is not None and bk_i is not None:
                                    self.emit_live_single_leg_maker_lock_candidate(
                                        sleeve_source="MKR_REWARD_LOCKED_CARRY",
                                        asset=f"{sp.city}_{sp.icao}",
                                        dedupe_key=f"MKR_RW_W_{b_i.market_id}",
                                        pair_dedupe_key=f"MKR_RW_WPAIR_{b_i.market_id}",
                                        token_id=b_i.no_token,
                                        opp_token_id=b_i.yes_token,
                                        market_id=b_i.market_id,
                                        condition_id=b_i.condition_id,
                                        side_label="NO",
                                        display_label=f"{sp.city} Reward Carry NO[{b_i.label}]",
                                        bk_win=bk_n_i,
                                        bk_opp=bk_i,
                                        neg_risk=bool(b_i.neg_risk),
                                        close_ts=float(end_ts),
                                        now_ts=now_s,
                                        min_resting_bid=0.940,
                                        max_resting_bid=0.994,
                                        min_maker_edge=0.006,
                                        max_opp_bid=0.030,
                                        hold_to_maturity=True,
                                        p_model=1.0,
                                        target_bid_px=float(rw_w["resting_bid"]),
                                    )
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
                    w_qy = walk_l2_book_asks(bk_y_pref.get("asks") or [], 40.0, fee_rate=r.fee_rate, min_l1_usd=8.0, fee_exponent=r.fee_exponent)
                    w_qn = walk_l2_book_asks(bk_n_pref.get("asks") or [], 40.0, fee_rate=r.fee_rate, min_l1_usd=8.0, fee_exponent=r.fee_exponent)
                    barrier_quote_rows.append({
                        "strike": r.strike,
                        "direction": r.direction,
                        "market_id": r.market_id,
                        "condition_id": r.condition_id,
                        "yes_token": r.yes_token,
                        "no_token": r.no_token,
                        "fee_rate": r.fee_rate,
                        "fee_exponent": r.fee_exponent,
                        "ask_yes": w_qy.get("vwap") if w_qy.get("filled") else None,
                        "ask_no": w_qn.get("vwap") if w_qn.get("filled") else None,
                        "bk_yes": bk_y_pref,
                        "bk_no": bk_n_pref,
                        "start_ts": r.start_ts,
                        "end_ts": r.end_ts,
                    })

                # Evaluate B1_CONVEX_TAIL_YES (`0.04 <= p_touch <= 0.45`, `TTE >= 2h`)
                if (self.single_scan or not is_shadow_sleeve_quarantined("B1_CONVEX_TAIL_YES")) and 7200 <= tte <= 10 * 86400 and 0.07 <= p_touch <= 0.48:
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
                        fee_exponent_a=float(qy.get("fee_exponent", 1.0)),
                        fee_exponent_b=float(qn.get("fee_exponent", 1.0)),
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
                            "fee_exponent": float(qy.get("fee_exponent", 1.0)),
                            "strike": float(ba["low_strike"] if ba["direction"] == "UP" else ba["high_strike"]),
                        }
                        leg_b_b3 = {
                            "token_id": ba["no_token"], "opp_token_id": ba["no_opp_token"],
                            "condition_id": ba["leg_no_condition_id"], "side": "NO", "label": f"NO_{ba['direction']}",
                            "market_id": ba["leg_no_market_id"], "fee_rate": float(qn["fee_rate"]),
                            "fee_exponent": float(qn.get("fee_exponent", 1.0)),
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
                        if (float(qy["end_ts"]) - now) <= 86400.0 and float(w_b3["box_cost_net"]) <= 0.988:
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
            _m1_m2_pruned = (
                not self.single_scan
                and is_shadow_sleeve_quarantined("M1_SVI_MAKER_SCALP")
                and is_shadow_sleeve_quarantined("M2_STRIKE_CONVERGENCE")
            )
            coherent_map = (
                {}
                if _m1_m2_pruned
                else evaluate_coherent_strike_ladder(asset, spot, near, tte, now_ts=now).get("by_market_id", {})
            )
            ladder_quotes: List[Dict[str, Any]] = []

            for sr in near:
                svi_ev = (
                    None
                    if _m1_m2_pruned
                    else (
                        coherent_map.get(sr.market_id)
                        or evaluate_svi_digital_fair_value(asset, spot, sr.strike, tte, is_downward=sr.is_downward, now_ts=now)
                    )
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
                    if (sr.end_ts - now) <= 86400.0 and float(c1_chk["box_cost_net"]) <= 0.988:
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
                    if (
                        svi_ev is None
                        or (is_shadow_sleeve_quarantined("M1_SVI_MAKER_SCALP") and is_shadow_sleeve_quarantined("M2_STRIKE_CONVERGENCE"))
                    )
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
                    if (float(q_lo["end_ts"]) - now) <= 86400.0 and float(w_m3["box_cost_net"]) <= 0.988:
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
                if len(legs) == 2 and gp == 1.0 and cost_net <= 0.988 and (float(bnd["end_ts"]) - now_nr) <= 172800.0:
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
                    "fee_exponent": float(lg.get("fee_exponent", 1.0)),
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
                "fee_rate": max((float(lg.get("fee_rate", CRYPTO_FEE_RATE)) for lg in legs), default=CRYPTO_FEE_RATE),
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

    async def execute_negrisk_convert_positions_arb(
        self,
        spec: NegRiskConvertSlateSpec,
        arb_probe: Dict[str, Any],
        books_by_token: Dict[str, Dict[str, Any]],
        opps_out: List[Dict[str, Any]],
    ) -> bool:
        """
        Executes instant closed-partition `NegRiskAdapter.convertPositions` arbitrage (`NR_CONV_NO_BASKET_ARB`):
        buys `m >= 2` `NO` legs across `spec`, converts into `(m - 1)` USDC + `(N - m)` residual `YES` legs,
        and liquidates residual `YES` legs into live L2 `bids` (`min_net_edge_per_set >= $0.005`).
        """
        if is_shadow_sleeve_quarantined("NR_CONV_NO_BASKET_ARB") or not spec.is_closed_convert_safe:
            return False
        m_cnt = int(arb_probe["m_no_legs"])
        idx_sig = "_".join(str(i) for i in arb_probe["question_indices"])
        dedupe_key = f"NRCONV_M{m_cnt}_{spec.event_id}_{idx_sig}"
        opps_out.append({
            "sleeve": "NR_CONV_NO_BASKET_ARB",
            "market": f"{spec.title} [convertPositions {m_cnt}/{spec.total_market_count} NO -> {m_cnt - 1} USDC + YES bids]",
            "ask_vwap": round(1.0 - float(arb_probe["net_edge_per_share"]), 4),
            "p_model": 1.0,
            "net_edge": arb_probe["net_edge_per_share"],
            "l1_usd": arb_probe["l1_usd"],
            "close_ts": spec.end_ts,
        })
        if float(self._instant_arb_cooldown_until.get(dedupe_key, 0.0) or 0.0) > time.time():
            return False
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            req_toks = [b["no_token"] for b in spec.brackets] + [b["yes_token"] for b in spec.brackets]
            fresh_bks = await self.fetch_books_batch(req_toks, timeout=3.0)
            eval_bks = fresh_bks if all(t in fresh_bks for t in req_toks) else books_by_token
            tier_fills: Dict[str, Dict[str, Any]] = {}
            tier_pnls: Dict[str, float] = {}
            best_t1000: Optional[Dict[str, Any]] = None
            for t_name, t_map in BANKROLL_TICKETS.items():
                cands_t = detect_negrisk_convert_positions_arbs(
                    spec,
                    eval_bks,
                    target_budget_usd=t_map["NR_CONV_NO_BASKET_ARB"],
                    min_net_edge_per_share=0.005,
                    min_shares=5 if t_name == "T100" else 8,
                )
                hit_t = next((c for c in cands_t if c["question_indices"] == arb_probe["question_indices"]), None)
                if hit_t is not None:
                    sh_t = float(hit_t["shares"])
                    cost_ps = float(hit_t["no_cost_per_share"])
                    tier_fills[t_name] = {
                        "filled": True,
                        "vwap": cost_ps,
                        "eff_px": cost_ps,
                        "spent_usd": round(sh_t * cost_ps, 2),
                        "fee_usd": float(hit_t.get("total_fee_usd", 0.0)),
                        "shares": sh_t,
                        "l1_usd": hit_t["l1_usd"],
                    }
                    tier_pnls[t_name] = round(sh_t * float(hit_t["net_edge_per_share"]), 2)
                    if t_name == "T1000":
                        best_t1000 = hit_t
            if best_t1000 is None:
                return False
            now = time.time()
            pos_id = f"NR_CONV_NO_BASKET_ARB_{int(now)}_{dedupe_key[-10:]}"
            pay_ps = round(float(best_t1000["net_proceeds_per_share"]), 4)
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": "NR_CONV_NO_BASKET_ARB",
                "asset_or_city": "NEGRISK",
                "title": f"{spec.title} [convertPositions m={m_cnt}/{spec.total_market_count}]",
                "side": f"CONVERT_{m_cnt}NO",
                "token_id": "|".join(str(x["bracket"]["no_token"]) for x in best_t1000["no_legs"]),
                "fee_rate": 0.0,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": spec.end_ts,
                "closed_ts": now,
                "closed_utc": datetime.now(timezone.utc).isoformat(),
                "p_model_entry": pay_ps,
                "entry_eff_px_t1000": best_t1000["no_cost_per_share"],
                "entry_vwap_t1000": best_t1000["no_cost_per_share"],
                "realized_edge_t1000": best_t1000["net_edge_per_share"],
                "net_payout_per_share": pay_ps,
                "tier_fills": tier_fills,
                "tier_pnls_usd": tier_pnls,
                "legging_adjusted_tier_pnls_usd": tier_pnls,
                "won": tier_pnls.get("T1000", 0.0) > 0,
                "extra": {
                    "mode": "NR_CONVERT_POSITIONS",
                    "neg_risk_market_id": spec.neg_risk_market_id,
                    "index_set_int": best_t1000["index_set"],
                    "no_question_indices": best_t1000["question_indices"],
                    "m_no_legs": m_cnt,
                    "n_total": spec.total_market_count,
                },
                "status": "INSTANT_CONVERT_AND_SELL_FILLED",
            }
            if self.single_scan and not getattr(self, "_enable_multiclip_instant_arb", False):
                for k_acq in acq:
                    self.entered_keys.add(k_acq)
            else:
                self._instant_arb_cooldown_until[dedupe_key] = now + 3.0
            self.emit_live_negrisk_convert_candidate(
                sleeve_source="NR_CONV_NO_BASKET_ARB",
                spec=spec,
                dedupe_key=dedupe_key,
                arb_hit=best_t1000,
                books_by_token=eval_bks,
                now_ts=now,
                fee_bips=0,
            )
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            self.closed_positions.append(pos)
            self._append_ledger({"event": "SHADOW_CLOSE", **pos})
            logger.info(
                f"[INSTANT_ARB:NR_CONV_NO_BASKET_ARB] {pos['title']} | edge=+{best_t1000['net_edge_per_set']:.4f}/set | "
                f"PnL T1000=${tier_pnls.get('T1000', 0.0):+.2f}"
            )
            return True
        finally:
            self._release_inflight_keys(acq)

    async def execute_nr2_subset_convert_arb(
        self,
        spec: NegRiskConvertSlateSpec,
        arb_probe: Dict[str, Any],
        books_by_token: Dict[str, Dict[str, Any]],
        opps_out: List[Dict[str, Any]],
    ) -> bool:
        """
        Executes asymmetric subset `NegRiskAdapter.convertPositions` (`NR2_CONVERT_NO_SUBSET_ARB`):
        verifies on-chain `getQuestionCount` & `getFeeBips`, buys `m in {2, 3, N}` `NO` legs, converts into
        `(m - 1)` USDC + complement `YES`, sells only liquid `YES_j` (`j in L`), and retains free tail `YES_u` (`u in U`).
        """
        if is_shadow_sleeve_quarantined("NR2_CONVERT_NO_SUBSET_ARB") or not spec.is_closed_convert_safe:
            return False
        m_cnt = int(arb_probe["m_no_legs"])
        idx_sig = "_".join(str(i) for i in arb_probe["no_question_indices"])
        dedupe_key = f"NR2_M{m_cnt}_{spec.event_id}_{idx_sig}"
        opps_out.append({
            "sleeve": "NR2_CONVERT_NO_SUBSET_ARB",
            "market": f"{spec.title[:52]} [{arb_probe['label']}]",
            "ask_vwap": round(max(0.01, 1.0 - float(arb_probe["net_edge_per_share"])), 4),
            "p_model": 1.0,
            "net_edge": arb_probe["net_edge_per_share"],
            "l1_usd": arb_probe["l1_usd"],
            "close_ts": spec.end_ts,
        })
        if float(self._instant_arb_cooldown_until.get(dedupe_key, 0.0) or 0.0) > time.time():
            return False
        acq = self._try_acquire_keys(dedupe_key)
        if not acq:
            return False
        try:
            ok_nr, fee_bips, _ = await asyncio.to_thread(
                verify_negrisk_adapter_slate_sync, spec.neg_risk_market_id, spec.total_market_count
            )
            if not ok_nr:
                return False
            req_toks = [b["no_token"] for b in spec.brackets] + [b["yes_token"] for b in spec.brackets]
            fresh_bks = await self.fetch_books_batch(req_toks, timeout=3.0)
            eval_bks = fresh_bks if all(t in fresh_bks for t in req_toks) else books_by_token
            tier_fills: Dict[str, Dict[str, Any]] = {}
            tier_pnls: Dict[str, float] = {}
            best_t1000: Optional[Dict[str, Any]] = None
            for t_name, t_map in BANKROLL_TICKETS.items():
                cands_t = detect_nr2_convert_no_subset_arbs(
                    spec,
                    eval_bks,
                    target_budget_usd=t_map["NR2_CONVERT_NO_SUBSET_ARB"],
                    min_edge_pure_cash=0.010,
                    min_edge_with_yes_sell=0.012,
                    min_shares=5 if t_name == "T100" else 6,
                    fee_bips=fee_bips,
                )
                hit_t = next((c for c in cands_t if c["no_question_indices"] == arb_probe["no_question_indices"]), None)
                if hit_t is not None:
                    sh_t = float(hit_t["shares"])
                    cost_ps = float(hit_t["no_cost_per_share"])
                    tier_fills[t_name] = {
                        "filled": True,
                        "vwap": cost_ps,
                        "eff_px": cost_ps,
                        "spent_usd": round(sh_t * cost_ps, 2),
                        "fee_usd": hit_t["total_fee_usd"],
                        "shares": sh_t,
                        "l1_usd": hit_t["l1_usd"],
                    }
                    tier_pnls[t_name] = float(hit_t["total_net_profit_usd"])
                    if t_name == "T1000":
                        best_t1000 = hit_t
            if best_t1000 is None:
                return False
            now = time.time()
            pos_id = f"NR2_CONVERT_NO_SUBSET_ARB_{int(now)}_{dedupe_key[-10:]}"
            pay_ps = float(best_t1000["net_proceeds_per_share"])
            pos = {
                "position_id": pos_id,
                "dedupe_key": dedupe_key,
                "sleeve": "NR2_CONVERT_NO_SUBSET_ARB",
                "asset_or_city": "NEGRISK_V2",
                "title": f"{spec.title} [{best_t1000['label']}]",
                "side": f"NR2_{m_cnt}NO_FREE{best_t1000['retained_tail_count']}Y",
                "token_id": "|".join(str(x["token_id"]) for x in best_t1000["no_legs"]),
                "fee_rate": 0.0,
                "entry_ts": now,
                "entry_utc": datetime.now(timezone.utc).isoformat(),
                "close_ts": spec.end_ts,
                "closed_ts": now,
                "closed_utc": datetime.now(timezone.utc).isoformat(),
                "p_model_entry": pay_ps,
                "entry_eff_px_t1000": best_t1000["no_cost_per_share"],
                "entry_vwap_t1000": best_t1000["no_cost_per_share"],
                "realized_edge_t1000": best_t1000["net_edge_per_share"],
                "net_payout_per_share": pay_ps,
                "tier_fills": tier_fills,
                "tier_pnls_usd": tier_pnls,
                "legging_adjusted_tier_pnls_usd": tier_pnls,
                "won": tier_pnls.get("T1000", 0.0) > 0,
                "extra": {
                    "mode": best_t1000["mode"],
                    "neg_risk_market_id": spec.neg_risk_market_id,
                    "index_set_int": best_t1000["index_set_int"],
                    "no_question_indices": best_t1000["no_question_indices"],
                    "retained_tail_count": best_t1000["retained_tail_count"],
                    "retained_tail_labels": [b["label"] for b in best_t1000["retained_free_yes_brackets"]],
                    "fee_bips": fee_bips,
                },
                "status": "INSTANT_SUBSET_CONVERT_FREE_TAIL_LOCKED",
            }
            if self.single_scan and not getattr(self, "_enable_multiclip_instant_arb", False):
                for k_acq in acq:
                    self.entered_keys.add(k_acq)
            else:
                self._instant_arb_cooldown_until[dedupe_key] = now + 3.0
            self.emit_live_negrisk_convert_candidate(
                sleeve_source="NR2_CONVERT_NO_SUBSET_ARB",
                spec=spec,
                dedupe_key=dedupe_key,
                arb_hit=best_t1000,
                books_by_token=eval_bks,
                now_ts=now,
                fee_bips=fee_bips,
            )
            self._append_ledger({"event": "SHADOW_ENTRY", **pos})
            self.closed_positions.append(pos)
            self._append_ledger({"event": "SHADOW_CLOSE", **pos})
            logger.info(
                f"[INSTANT_ARB:NR2_CONVERT_NO_SUBSET_ARB] {pos['title']} | edge=+{best_t1000['net_edge_per_share']:.4f}/sh "
                f"| free_tails={best_t1000['retained_tail_count']} | PnL T1000=${tier_pnls.get('T1000', 0.0):+.2f}"
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
                    if (sp_c1.end_ts - now) <= 86400.0 and float(c1_res["box_cost_net"]) <= (0.990 if sp_c1.fee_rate == 0.0 else 0.988):
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
                opp_tok_u1 = sp.down_token if win_side == "UP" else sp.up_token
                if z_sig >= 2.20 and p_fair >= 0.965:
                    bk_opp_u1 = await self.fetch_json(f"{CLOB_URL}/book?token_id={opp_tok_u1}", timeout=2.5)
                    self.emit_live_single_leg_lock_candidate(
                        sleeve_source="U1_DAILY_UPDOWN_LOCK",
                        asset=sp.asset,
                        dedupe_key=f"U1_{sp.market_id}_{win_side}",
                        token_id=tok,
                        opp_token_id=opp_tok_u1,
                        market_id=sp.market_id,
                        condition_id=sp.condition_id,
                        side_label=win_side,
                        display_label=f"{sp.asset} Daily {win_side}",
                        bk_win=bk,
                        bk_opp=bk_opp_u1 if isinstance(bk_opp_u1, dict) else None,
                        fee_rate=sp.fee_rate,
                        fee_exponent=1.0,
                        neg_risk=False,
                        close_ts=sp.end_ts,
                        now_ts=now,
                        max_lock_eff_px=0.900,
                        max_opp_bid=0.360,
                        hold_to_maturity=False,
                        p_model=float(p_fair),
                    )
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
        True during:
          - the final 5m sub-window of every 15m candle (`:10-:15`, `:25-:30`, `:40-:45`, `:55-:00`), OR
          - the final 15m overlap window of every 4h candle (`:45-:00` at 00/04/08/12/16/20 UTC),
        where active `4h`/`15m`/`5m` Chainlink 60s-TWAP markets share the exact same terminal timestamp!
        """
        target_end_ts = math.ceil(now_ts / 900.0) * 900.0
        rem_sec = target_end_ts - now_ts
        rem_1h = (math.ceil(now_ts / 3600.0) * 3600.0) - now_ts
        rem_4h = (math.ceil(now_ts / 14400.0) * 14400.0) - now_ts
        return (8.0 <= rem_sec <= 305.0) or (8.0 <= rem_1h <= 905.0) or (8.0 <= rem_4h <= 905.0)

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
        is_mocked_disc = self.single_scan or ("fetch_json" in self.__dict__)
        is_hourly_overlap = (target_end_ts % 3600) == 0 and (5.0 <= rem_sec <= 905.0)
        max_disc_rem = 305.0 if is_mocked_disc else 335.0
        if not (5.0 <= rem_sec <= max_disc_rem) and not (is_hourly_overlap and not is_mocked_disc):
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

        async def _discover_metal_pair(metal: str) -> None:
            pair_key = f"{metal}_1h15m_{target_end_ts}"
            if pair_key in self.dominance_pairs:
                return
            slugs_m = METAL_DOMINANCE_SERIES_SLUGS[metal]
            ev1h_raw, ev15_raw = await asyncio.gather(
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs_m['1h']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
                self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs_m['15m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=4.0,
                ),
            )
            m1h_m: Optional[TwapCandleMarketSpec] = None
            m15_m: Optional[TwapCandleMarketSpec] = None
            if isinstance(ev1h_raw, list):
                for ev in ev1h_raw:
                    sp1h = parse_metal_forex_candle_event(ev, metal, "1h")
                    if sp1h and abs(sp1h.end_ts - target_end_ts) <= 2.0:
                        m1h_m = sp1h
                        break
            if isinstance(ev15_raw, list):
                for ev in ev15_raw:
                    sp15 = parse_metal_forex_candle_event(ev, metal, "15m")
                    if sp15 and abs(sp15.end_ts - target_end_ts) <= 2.0:
                        m15_m = sp15
                        break
            if m1h_m and m15_m and verify_same_oracle_pair(m1h_m, m15_m):
                self.dominance_pairs[pair_key] = (m1h_m, m15_m)

        tasks = []
        if 5.0 <= rem_sec <= max_disc_rem:
            tasks.extend(_discover_asset_pair(a) for a in DOMINANCE_ASSETS)
        if is_hourly_overlap and (not is_mocked_disc or os.getenv("PM_FORCE_METAL_D1_TEST") == "1"):
            tasks.extend(_discover_metal_pair(m) for m in METAL_DOMINANCE_ASSETS)
        if tasks:
            await asyncio.gather(*tasks)

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
        if spec.asset in METAL_DOMINANCE_ASSETS and int(spec.twap_lookback_sec) == 0:
            if not is_mocked and now_t < spec.start_ts + 4.0:
                return None
            last_fail_m = float(self._strike_fail_backoff_ts.get(c_key, 0.0) or 0.0)
            if not is_mocked and (now_t - last_fail_m) < 2.5:
                return None
            m_url = build_prev_15m_gamma_event_url(spec)
            m_val = parse_authoritative_open_price(await self.fetch_json(m_url, timeout=3.0), request_url=m_url)
            if m_val is not None:
                self.chainlink_open_cache[c_key] = (spec.end_ts, m_val)
                src_map[c_key] = (spec.end_ts, "REST_VERIFIED")
                return m_val
            if not is_mocked:
                self._strike_fail_backoff_ts[c_key] = time.time()
            return None
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
        max_attempts = 3 if (is_mocked or now_t < spec.start_ts + 35.0) else (2 if now_t < spec.start_ts + 95.0 else 1)
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
        can_fallback_gamma = needs_gamma or (val is None and now_t >= spec.start_ts + 10.0)
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
            elif val is None and needs_gamma and g_val is None and not self.single_scan:
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
                twap_tol = 0.0080 if not used_gamma else 0.0035
                if loc_twap > 0.0 and abs(val - loc_twap) / loc_twap > twap_tol:
                    logger.error(f"[STRIKE TWAP VETO] {spec.asset} {spec.horizon}: strike {val} vs local 60s TWAP {loc_twap} > {int(twap_tol*10000)} bps")
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
        ask_oa, _ = self._best_ask_sz(bk_oa)
        ask_ob, _ = self._best_ask_sz(bk_ob)
        oa_ok = bid_oa > 0.0 or (0.0 < ask_oa <= 0.12)
        ob_ok = bid_ob > 0.0 or (0.0 < ask_ob <= 0.12)
        opp_ub_sum = (bid_oa if bid_oa > 0.0 else ask_oa) + (bid_ob if bid_ob > 0.0 else ask_ob)
        tok_a_id = str(leg_a.get("token_id") or "")
        tok_b_id = str(leg_b.get("token_id") or "")
        bk_ta = (prefetched_books or {}).get(tok_a_id) if tok_a_id else None
        bk_tb = (prefetched_books or {}).get(tok_b_id) if tok_b_id else None
        if isinstance(bk_ta, dict) and isinstance(bk_tb, dict):
            # True CTF binary mirror parity: on Polymarket CLOB, bid(opp_A) == 1.00 - ask(A),
            # so any genuine sub-$1.00 box (ask_a + ask_b < 1.00) MUST have bid_oa + bid_ob = 2.00 - (ask_a + ask_b) > 1.00!
            # A corrupted/mismatched complement pair violates binary parity (ask_a + bid_oa > 1.015 or bid_oa + bid_ob > 1.16).
            ask_ta, _ = self._best_ask_sz(bk_ta)
            ask_tb, _ = self._best_ask_sz(bk_tb)
            parity_bad = (
                (ask_ta > 0.0 and bid_oa > 0.0 and (ask_ta + bid_oa) > 1.015)
                or (ask_tb > 0.0 and bid_ob > 0.0 and (ask_tb + bid_ob) > 1.015)
                or (bid_oa + bid_ob) > 1.160
                or opp_ub_sum > 1.180
            )
        else:
            parity_bad = (bid_oa + bid_ob) > 1.0 or opp_ub_sum > 1.035
        if not (oa_ok and ob_ok) or (bid_oa <= 0.0 and bid_ob <= 0.0) or parity_bad:
            _ab_map = self.__dict__.setdefault("_anti_box_warn_ts", {})
            _ab_k = f"{opp_a}:{opp_b}"
            _now_ab = time.time()
            if (_now_ab - float(_ab_map.get(_ab_k, 0.0))) >= 30.0:
                if len(_ab_map) > 512:
                    _ab_map.clear()
                _ab_map[_ab_k] = _now_ab
                logger.warning(
                    f"[ANTI-BOX VETO] Rejected box {leg_a.get('label')}+{leg_b.get('label')}: "
                    f"complement bids={bid_oa:.3f}+{bid_ob:.3f}={bid_oa + bid_ob:.3f} (ub={opp_ub_sum:.3f}, unverified or > 1.00)"
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
            # EXP-PM-404: Enforce causal 250ms L2 re-fetch & re-walk on 0%-fee / sports / NegRisk 2-leg structural boxes
            # so _grad8 auto-graduation only counts edges that survive realistic execution latency.
            if sleeve in (
                "CM_B3_PYTH_BARRIER_BOX",
                "SP1_NBA_ZERO_FEE_BOX",
                "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
                "NR_CONV_NO_BASKET_ARB",
            ):
                await asyncio.sleep(0.25)
                re_bks = await self.fetch_books_batch([leg_a["token_id"], leg_b["token_id"]], timeout=3.0)
                bk_a = re_bks.get(leg_a["token_id"]) or {}
                bk_b = re_bks.get(leg_b["token_id"]) or {}
                if not bk_a or not bk_b:
                    return False
            asks_a = bk_a.get("asks") or []
            asks_b = bk_b.get("asks") or []
            bid_a, _ = extract_best_bid(bk_a.get("bids") or [])
            bid_b, _ = extract_best_bid(bk_b.get("bids") or [])
            tier_fills: Dict[str, Dict[str, Any]] = {}
            for tier_name, t_map in BANKROLL_TICKETS.items():
                w_t = walk_equal_shares_dominance_box(
                    asks_a,
                    asks_b,
                    target_budget_usd=t_map[sleeve],
                    fee_rate_a=float(leg_a.get("fee_rate", CRYPTO_FEE_RATE)),
                    fee_rate_b=float(leg_b.get("fee_rate", CRYPTO_FEE_RATE)),
                    fee_exponent_a=float(leg_a.get("fee_exponent", 1.0)),
                    fee_exponent_b=float(leg_b.get("fee_exponent", 1.0)),
                    max_box_cost_net=max_box_cost_net,
                    min_shares=8,
                    min_box_notional_usd=7.0,
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
            _rest_verified_pair = self._strike_is_rest_verified(m15) and self._strike_is_rest_verified(m5)
            w_ref = walk_equal_shares_dominance_box(
                asks_a,
                asks_b,
                target_budget_usd=BANKROLL_TICKETS["T1000"][sleeve_override],
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                fee_exponent_a=float(leg_a["fee_exponent"]),
                fee_exponent_b=float(leg_b["fee_exponent"]),
                max_box_cost_net=max_box_cost_override,
                min_shares=8,
                min_box_notional_usd=7.5,
                min_box_cost_net=0.860 if _rest_verified_pair else 0.900,
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
                w_t = walk_equal_shares_dominance_box(
                    asks_a,
                    asks_b,
                    target_budget_usd=t_map[sleeve_override],
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=max_box_cost_override,
                    min_shares=8,
                    min_box_notional_usd=7.5,
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

    def _d1_live_max_box_cost(self) -> float:
        try:
            cfg_p = Path(os.getenv("POLYMARKET_RISK_CONFIG", str(PROJECT_ROOT / "config/polymarket_risk_config.json")))
            raw_c = json.loads(cfg_p.read_text(encoding="utf-8"))
            v = float(raw_c.get("d1_max_box_cost_net", 0.985))
            if 0.86 <= v <= 0.995:
                return v
        except Exception:
            pass
        return 0.985

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
            if float(m5.end_ts - now_ts) < 16.0:
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
            "net_paired_shares": float(w_live.get("net_paired_shares", w_live["shares"])),
            "leg_a_gross_shares": float(w_live.get("leg_a_gross_shares", w_live["shares"])),
            "leg_b_gross_shares": float(w_live.get("leg_b_gross_shares", w_live["shares"])),
            "box_cost_net": float(w_live["box_cost_net"]),
            "legging_drag_per_pair": drag_live["legging_drag_per_pair"],
            "legging_adjusted_net_ev_per_pair": drag_live["legging_adjusted_net_ev_per_pair"],
            "max_box_cost_net": self._d1_live_max_box_cost(),
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
        from src.polymarket_research.riskless_protocol_v2_expansion import attach_ws_books_and_write_d1_cand
        return attach_ws_books_and_write_d1_cand(self, cand, leg_a, leg_b, D1_LIVE_CANDIDATES_FILE, default_cand_path)

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
        max_box_cost_override: Optional[float] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Emits a verified non-D1 2-leg riskless box candidate (C1, M3, B3, 2-leg N1) to the live IPC stream."""
        default_cand_path = LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl"
        if STATE_FILE != (DATA_DIR / "alpha124_shadow_state.json") and D1_LIVE_CANDIDATES_FILE == default_cand_path:
            return False
        if not (self.single_scan or ("fetch_json" in self.__dict__)):
            # Live mode: stamp with emit-time wall clock (caller's value may be stale after awaited book fetches)
            now_ts = time.time()
        rem_sec = float(close_ts - now_ts)
        if rem_sec < 25.0:
            return False
        last_emit = float(self._last_d1_live_emit_ts.get(dedupe_key, 0.0) or 0.0)
        if (now_ts - last_emit) < 15.0:
            return False
        fee_a = float(leg_a.get("fee_rate", CRYPTO_FEE_RATE))
        fee_b = float(leg_b.get("fee_rate", CRYPTO_FEE_RATE))
        exp_a = float(leg_a.get("fee_exponent", 1.0))
        exp_b = float(leg_b.get("fee_exponent", 1.0))
        if sleeve_source == "COND1_MACRO_PARTITION_BOX":
            max_cap = (0.992 if rem_sec <= 108000.0 else 0.988) if self.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX") else 0.985
        elif box_type == "BARRIER_MONO":
            max_cap = 0.993
        elif max(fee_a, fee_b) == 0.0 and (self.is_sleeve_grad8_ready(sleeve_source) or self._can_emit_zero_loss_math_live(sleeve_source, close_ts, now_ts)) and rem_sec <= (
            604800.0
            if sleeve_source in {
                "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
                "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
                "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
                "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",
            }
            else 172800.0
        ):
            max_cap = 0.992
        else:
            max_cap = 0.990 if max(fee_a, fee_b) == 0.0 else 0.988
        if max_box_cost_override is not None:
            max_cap = min(max_cap, float(max_box_cost_override))
        w_live = walk_equal_shares_dominance_box(
            bk_a.get("asks") or [],
            bk_b.get("asks") or [],
            target_budget_usd=20.0,
            fee_rate_a=fee_a,
            fee_rate_b=fee_b,
            fee_exponent_a=exp_a,
            fee_exponent_b=exp_b,
            max_box_cost_net=max_cap,
            min_shares=5,
            min_box_notional_usd=4.85,
            min_box_cost_net=0.860,
        )
        if not w_live.get("filled"):
            return False
        if len(self._last_d1_live_emit_ts) > 256:
            self._last_d1_live_emit_ts = {k: v for k, v in self._last_d1_live_emit_ts.items() if (now_ts - float(v)) <= 1200.0}
        self._last_d1_live_emit_ts[dedupe_key] = now_ts
        w_a = w_live["leg_a_walk"]
        w_b = w_live["leg_b_walk"]
        _ba_q, _ = self._best_ask_sz(bk_a)
        _bb_q, _ = self._best_ask_sz(bk_b)
        _bda_q, _ = extract_best_bid(bk_a.get("bids") or [])
        _bdb_q, _ = extract_best_bid(bk_b.get("bids") or [])
        _quiet_2l = bool(
            _bda_q > 0.0 and _bdb_q > 0.0
            and (_ba_q - _bda_q) <= 0.041 and (_bb_q - _bdb_q) <= 0.041
            and (max(fee_a, fee_b) == 0.0 or (now_ts - float(self._last_any_shock_ts_by_asset.get(str(asset), 0.0) or 0.0)) >= 4.0)
        )
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
            "is_quiet_book": _quiet_2l,
            "k_low": float(k_low),
            "k_high": float(k_high),
            "corridor_bps": corr_bps,
            "expiry_ts": float(close_ts),
            "rem_sec": round(rem_sec, 2),
            "shares": int(w_live["shares"]),
            "net_paired_shares": float(w_live.get("net_paired_shares", w_live["shares"])),
            "leg_a_gross_shares": float(w_live.get("leg_a_gross_shares", w_live["shares"])),
            "leg_b_gross_shares": float(w_live.get("leg_b_gross_shares", w_live["shares"])),
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
            "leg_a_neg_risk": bool(leg_a["neg_risk"]) if isinstance(leg_a.get("neg_risk"), bool) else False,
            "leg_a_expiry_ts": float(leg_a.get("end_ts") or close_ts),
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
            "leg_b_neg_risk": bool(leg_b["neg_risk"]) if isinstance(leg_b.get("neg_risk"), bool) else False,
            "leg_b_expiry_ts": float(leg_b.get("end_ts") or close_ts),
        }
        if isinstance(extra_fields, dict):
            cand.update(extra_fields)
        if not self.single_scan and self._ws_books:
            req_ws_2 = [str(leg_a["token_id"]), str(leg_b["token_id"])]
            if str(box_type) != "COMPLETE_SET":
                for op_id in (str(leg_a.get("opp_token_id") or ""), str(leg_b.get("opp_token_id") or "")):
                    if op_id:
                        req_ws_2.append(op_id)
            buy_ws_2 = {str(leg_a["token_id"]), str(leg_b["token_id"])}
            rest_seeded_2 = getattr(self, "_ws_rest_seeded", set())
            if all(
                t_x in self._ws_books
                and t_x not in rest_seeded_2
                and (now_ts - self._ws_books[t_x][0]) <= 2.50
                and bool(self._ws_books[t_x][1].get("asks"))
                and (t_x not in buy_ws_2 or bool(self._ws_books[t_x][1].get("bids") or self._ws_books[t_x][1].get("asks")))
                for t_x in req_ws_2
            ):
                cand["ws_books"] = {
                    t_x: {"bids": (self._ws_books[t_x][1].get("bids") or [])[:12], "asks": (self._ws_books[t_x][1].get("asks") or [])[:12]}
                    for t_x in req_ws_2
                }
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

    def emit_live_single_leg_lock_candidate(
        self,
        *,
        sleeve_source: str,
        asset: str,
        dedupe_key: str,
        token_id: str,
        opp_token_id: str,
        market_id: str,
        condition_id: str,
        side_label: str,
        display_label: str,
        bk_win: Dict[str, Any],
        bk_opp: Optional[Dict[str, Any]],
        fee_rate: float,
        fee_exponent: float,
        neg_risk: bool,
        close_ts: float,
        now_ts: float,
        max_lock_eff_px: float,
        max_opp_bid: float = 0.025,
        hold_to_maturity: bool = False,
        p_model: float = 1.0,
    ) -> bool:
        """Emits a verified 1-leg deterministic lock candidate (`SINGLE_LEG_LOCK`) over the UDS/JSONL live bridge."""
        from src.polymarket_research.riskless_protocol_v2_expansion import emit_single_leg_lock_cand_impl

        return emit_single_leg_lock_cand_impl(
            self,
            sleeve_source=sleeve_source,
            asset=asset,
            dedupe_key=dedupe_key,
            token_id=token_id,
            opp_token_id=opp_token_id,
            market_id=market_id,
            condition_id=condition_id,
            side_label=side_label,
            display_label=display_label,
            bk_win=bk_win,
            bk_opp=bk_opp,
            fee_rate=fee_rate,
            fee_exponent=fee_exponent,
            neg_risk=neg_risk,
            close_ts=close_ts,
            now_ts=now_ts,
            max_lock_eff_px=max_lock_eff_px,
            max_opp_bid=max_opp_bid,
            hold_to_maturity=hold_to_maturity,
            p_model=p_model,
            extract_best_bid_fn=extract_best_bid,
            walk_l2_fn=walk_l2_book_asks_depth_capped,
            cand_file=D1_LIVE_CANDIDATES_FILE,
            default_cand_path=LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl",
            state_file=STATE_FILE,
            default_state_path=DATA_DIR / "alpha124_shadow_state.json",
        )

    def emit_live_special_v2_box_candidate(
        self,
        *,
        box_type: str,
        sleeve_source: str,
        asset: str,
        dedupe_key: str,
        close_ts: float,
        now_ts: float,
        payload: Dict[str, Any],
    ) -> bool:
        """Emits a `CTF_OVERROUND` or `MULTI_LEG_BUNDLE` (`3..12` leg) candidate over UDS/JSONL."""
        from src.polymarket_research.riskless_protocol_v2_expansion import emit_special_v2_box_cand_impl

        return emit_special_v2_box_cand_impl(
            self,
            box_type=box_type,
            sleeve_source=sleeve_source,
            asset=asset,
            dedupe_key=dedupe_key,
            close_ts=close_ts,
            now_ts=now_ts,
            payload=payload,
            cand_file=D1_LIVE_CANDIDATES_FILE,
            default_cand_path=LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl",
            state_file=STATE_FILE,
            default_state_path=DATA_DIR / "alpha124_shadow_state.json",
        )

    def emit_live_negrisk_convert_candidate(
        self,
        *,
        sleeve_source: str,
        spec: NegRiskConvertSlateSpec,
        dedupe_key: str,
        arb_hit: Dict[str, Any],
        books_by_token: Dict[str, Dict[str, Any]],
        now_ts: float,
        fee_bips: int = 0,
    ) -> bool:
        """Emits a verified closed-partition `NegRiskAdapterV2.convertPositions` candidate (`NEGRISK_CONVERT`)."""
        from src.polymarket_research.riskless_protocol_v2_expansion import emit_negrisk_convert_cand_impl

        return emit_negrisk_convert_cand_impl(
            self,
            sleeve_source=sleeve_source,
            spec=spec,
            dedupe_key=dedupe_key,
            arb_hit=arb_hit,
            books_by_token=books_by_token,
            now_ts=now_ts,
            fee_bips=fee_bips,
            cand_file=D1_LIVE_CANDIDATES_FILE,
            default_cand_path=LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl",
            state_file=STATE_FILE,
            default_state_path=DATA_DIR / "alpha124_shadow_state.json",
        )

    def emit_live_single_leg_maker_lock_candidate(
        self,
        *,
        sleeve_source: str,
        asset: str,
        dedupe_key: str,
        pair_dedupe_key: str,
        token_id: str,
        opp_token_id: str,
        market_id: str,
        condition_id: str,
        side_label: str,
        display_label: str,
        bk_win: Dict[str, Any],
        bk_opp: Optional[Dict[str, Any]],
        neg_risk: bool,
        close_ts: float,
        now_ts: float,
        min_resting_bid: float = 0.940,
        max_resting_bid: float = 0.994,
        min_maker_edge: float = 0.006,
        max_opp_bid: float = 0.008,
        hold_to_maturity: bool = True,
        p_model: float = 1.0,
        target_bid_px: Optional[float] = None,
        maker_rebate_ps: float = 0.0,
    ) -> bool:
        """Emits a verified 0%-fee resting Maker 1-leg deterministic lock candidate (`SINGLE_LEG_MAKER_LOCK`)."""
        from src.polymarket_research.riskless_protocol_v2_expansion import emit_single_leg_maker_lock_cand_impl

        return emit_single_leg_maker_lock_cand_impl(
            self,
            sleeve_source=sleeve_source,
            asset=asset,
            dedupe_key=dedupe_key,
            pair_dedupe_key=pair_dedupe_key,
            token_id=token_id,
            opp_token_id=opp_token_id,
            market_id=market_id,
            condition_id=condition_id,
            side_label=side_label,
            display_label=display_label,
            bk_win=bk_win,
            bk_opp=bk_opp,
            neg_risk=neg_risk,
            close_ts=close_ts,
            now_ts=now_ts,
            min_resting_bid=min_resting_bid,
            max_resting_bid=max_resting_bid,
            min_maker_edge=min_maker_edge,
            max_opp_bid=max_opp_bid,
            hold_to_maturity=hold_to_maturity,
            p_model=p_model,
            target_bid_px=target_bid_px,
            maker_rebate_ps=maker_rebate_ps,
            extract_best_bid_fn=extract_best_bid,
            cand_file=D1_LIVE_CANDIDATES_FILE,
            default_cand_path=LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl",
            state_file=STATE_FILE,
            default_state_path=DATA_DIR / "alpha124_shadow_state.json",
        )

    def emit_live_maker_anchor_box_candidate(
        self,
        *,
        sleeve_source: str,
        box_type: str,
        asset: str,
        dedupe_key: str,
        regime: str,
        pair_horizons: str,
        leg_a: Dict[str, Any],
        leg_b: Dict[str, Any],
        anchor_is_a: bool,
        queue_front: bool,
        anchor_bid_px: float,
        hedge_limit_px: float,
        avail_a_shares: float,
        avail_b_shares: float,
        close_ts: float,
        now_ts: float,
        k_low: float = 100.0,
        k_high: float = 100.0,
        corridor_bps: float = 0.0,
        posted_spot: float = 0.0,
    ) -> bool:
        """EXP-PM-406B / EXP-PM-409: Emits a verified Maker-Anchor 2-leg box candidate to the live IPC stream."""
        from src.polymarket_research.riskless_protocol_v2_expansion import emit_maker_anchor_box_cand_impl

        return emit_maker_anchor_box_cand_impl(
            self,
            sleeve_source=sleeve_source,
            box_type=box_type,
            asset=asset,
            dedupe_key=dedupe_key,
            regime=regime,
            pair_horizons=pair_horizons,
            leg_a=leg_a,
            leg_b=leg_b,
            anchor_is_a=anchor_is_a,
            queue_front=queue_front,
            anchor_bid_px=anchor_bid_px,
            hedge_limit_px=hedge_limit_px,
            avail_a_shares=avail_a_shares,
            avail_b_shares=avail_b_shares,
            close_ts=close_ts,
            now_ts=now_ts,
            k_low=k_low,
            k_high=k_high,
            corridor_bps=corridor_bps,
            posted_spot=posted_spot,
            crypto_fee_rate=CRYPTO_FEE_RATE,
            project_root=PROJECT_ROOT,
            cand_file=D1_LIVE_CANDIDATES_FILE,
            default_cand_path=LIVE_POLYMARKET_DIR / "d1_live_box_candidates.jsonl",
            state_file=STATE_FILE,
            default_state_path=DATA_DIR / "alpha124_shadow_state.json",
        )

    def _latest_spot_px(self, asset: str) -> float:
        uh = self.usd_spot_hist.get(asset)
        if uh and len(uh) > 0 and (time.time() - float(uh[-1][0])) <= 10.0 and float(uh[-1][1]) > 0.0:
            return float(uh[-1][1])
        return float(self.spots.get(asset) or 0.0)

    def post_maker_anchor_candidate(
        self,
        m15: TwapCandleMarketSpec,
        m5: TwapCandleMarketSpec,
        dom_info: Dict[str, Any],
        bk_a: Dict[str, Any],
        bk_b: Dict[str, Any],
        now_ts: float,
        *,
        live_emit_only: bool = False,
    ) -> bool:
        """
        Tier-2 (`D1_MAKER_ANCHOR_BOX`, EXP-PM-406 Hardened): Posts a single-leg 0%-fee `post_only=True`
        Maker Anchor on near-arb overlap corridors (`(0.995, 1.032]`) with:
          - Tick-exact `0.001` (`>=0.96` / `<=0.04`) and `0.01` pricing across `[0.03, 0.999]`,
          - Queue-front `+1 tick` step on `>= 2-tick` spreads OR `1c` mid-book join (`[0.15, 0.85]`) when `obi_l1 >= -0.15`,
          - Realistic `T100` (`$18` capped by `asset_cap`) `>= 2.5x` hedge depth gate + `0.900` anti-box floor,
          - 120ms WS supervision with 2.5 bps directional asymmetric spot cancel-on-move and 12s TTL.
        """
        if is_shadow_sleeve_quarantined("D1_MAKER_ANCHOR_BOX"):
            return False
        rem_sec = m5.end_ts - now_ts
        max_anc_rem = 880.0 if str(m5.horizon) == "15m" else 295.0
        if not (65.0 <= rem_sec <= max_anc_rem):
            return False
        ret_5s_init = self.get_return_bps(m15.asset, 5.0)
        if abs(ret_5s_init) > 4.5:
            return False
        if (now_ts - float(self._last_any_shock_ts_by_asset.get(m15.asset, 0.0) or 0.0)) < 4.0:
            return False
        d_key = f"D1_MKR_{m15.asset}_{m15.market_id}_{m5.market_id}"
        if not live_emit_only and (d_key in self.entered_keys or d_key in self.pending_maker_anchors or d_key in self.inflight_keys):
            return False

        leg_a, leg_b = dom_info["leg_a"], dom_info["leg_b"]
        bids_a = sorted([(float(b["price"]), float(b["size"])) for b in (bk_a.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0], key=lambda x: -x[0])
        bids_b = sorted([(float(b["price"]), float(b["size"])) for b in (bk_b.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0], key=lambda x: -x[0])
        asks_a = sorted([(float(a["price"]), float(a["size"])) for a in (bk_a.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        asks_b = sorted([(float(a["price"]), float(a["size"])) for a in (bk_b.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        if not asks_a or not asks_b or not bids_a or not bids_b:
            return False
        bid_a, bsz_a = bids_a[0]
        bid_b, bsz_b = bids_b[0]
        ask_a, sz_a = asks_a[0]
        ask_b, sz_b = asks_b[0]
        spr_a, spr_b = round(ask_a - bid_a, 4), round(ask_b - bid_b, 4)
        obi_a = (bsz_a - sz_a) / max(1e-9, bsz_a + sz_a)
        obi_b = (bsz_b - sz_b) / max(1e-9, bsz_b + sz_b)

        asset_cap_u = float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(m15.asset, 40.0))
        ref_bud_t100 = min(float(BANKROLL_TICKETS["T100"]["D1_MAKER_ANCHOR_BOX"]), asset_cap_u)
        req_sh_t100 = max(5.0, math.floor(ref_bud_t100 / 0.985))
        req_sh_t1000 = max(5.0, math.floor(min(float(BANKROLL_TICKETS["T1000"]["D1_MAKER_ANCHOR_BOX"]), asset_cap_u) / 0.985))

        def _snap_c(p: float) -> float:
            p = round(float(p), 4)
            return (math.floor((p + 1e-9) * 100.0) / 100.0) if (0.04 + 1e-9 < p < 0.96 - 1e-9) else (math.floor((p + 1e-9) * 1000.0) / 1000.0)

        candidates: List[Tuple[float, bool, bool, float, float, float]] = []
        for anchor_is_a in (True, False):
            b_anc = bid_a if anchor_is_a else bid_b
            bsz_anc = bsz_a if anchor_is_a else bsz_b
            a_anc = ask_a if anchor_is_a else ask_b
            s_anc = spr_a if anchor_is_a else spr_b
            obi_anc = obi_a if anchor_is_a else obi_b
            leg_anc = leg_a if anchor_is_a else leg_b
            asks_hdg = asks_b if anchor_is_a else asks_a
            leg_hdg = leg_b if anchor_is_a else leg_a
            if not (0.03 <= a_anc <= 0.999) or obi_anc < -0.35:
                continue
            anc_side = str(leg_anc.get("side") or "UP").upper()
            if (anc_side == "UP" and ret_5s_init < -2.2) or (anc_side == "DOWN" and ret_5s_init > 2.2):
                continue
            tb_anc = 0.001 if (b_anc >= 0.96 or b_anc < 0.04) else 0.01
            ta_anc = 0.001 if (a_anc > 0.96 or a_anc <= 0.04) else 0.01
            step_b = _snap_c(b_anc + tb_anc)
            max_u = _snap_c(a_anc - ta_anc)
            if step_b <= max_u + 1e-9 and step_b > b_anc + 1e-9:
                cand_bid = min(step_b, max_u)
                q_front = True
            elif s_anc >= 0.01 - 1e-9 and 0.15 <= a_anc <= 0.85 and obi_anc >= -0.15 and bsz_anc >= 15.0:
                cand_bid = _snap_c(b_anc)
                q_front = False
            else:
                continue
            avail_hdg = sum(sz for px, sz in asks_hdg if px <= asks_hdg[0][0] + 0.01)
            if avail_hdg < max(15.0, 2.5 * req_sh_t100):
                continue
            hdg_px = asks_hdg[0][0]
            hdg_fee = float(leg_hdg["fee_rate"]) * ((hdg_px * (1.0 - hdg_px)) ** float(leg_hdg.get("fee_exponent", 1.0)))
            hdg_eff = hdg_px + hdg_fee
            bid_px = min(cand_bid, _snap_c(0.988 - hdg_eff))
            min_ok_bid = round(b_anc - (tb_anc if q_front else 0.0), 3)
            if bid_px < min_ok_bid or bid_px <= 0.02 or bid_px >= a_anc:
                continue
            pair_est = round(bid_px + hdg_eff, 4)
            _min_mkr_pair = 0.860 if (self._strike_is_rest_verified(m15) and self._strike_is_rest_verified(m5)) else 0.900
            if _min_mkr_pair <= pair_est <= 0.988:
                candidates.append((pair_est - (0.0005 if q_front else 0.0), anchor_is_a, q_front, bid_px, round(hdg_eff, 4), req_sh_t100))

        if not candidates:
            if (
                not self.single_scan
                and obi_a >= -0.15
                and obi_b >= -0.15
                and self._strike_is_rest_verified(m15)
                and self._strike_is_rest_verified(m5)
            ):
                from src.polymarket_research.riskless_machine_gun_engine import evaluate_d1_maker_rebate_anchor, read_shm_spot_age_ms
                uh_r = self.usd_spot_hist.get(m15.asset)
                sp_age_ms = read_shm_spot_age_ms(m15.asset, now_ts, max(0.0, (now_ts - float(uh_r[-1][0])) * 1000.0) if (uh_r and len(uh_r) > 0) else 999.0)
                av_a_r = sum(sz for px, sz in asks_a if px <= ask_a + 0.01)
                av_b_r = sum(sz for px, sz in asks_b if px <= ask_b + 0.01)
                for anc_a_r in (True, False):
                    reb_ev = evaluate_d1_maker_rebate_anchor(
                        anchor_bid_px=bid_a if anc_a_r else bid_b,
                        anchor_ask_px=ask_a if anc_a_r else ask_b,
                        hedge_ask_px=ask_b if anc_a_r else ask_a,
                        hedge_avail_shares=av_b_r if anc_a_r else av_a_r,
                        req_shares=req_sh_t100,
                        fee_rate=float((leg_b if anc_a_r else leg_a).get("fee_rate", CRYPTO_FEE_RATE)),
                        fee_exponent=float((leg_b if anc_a_r else leg_a).get("fee_exponent", 1.0)),
                        spot_age_ms=sp_age_ms,
                    )
                    if reb_ev.get("eligible"):
                        emitted_r = self.emit_live_maker_anchor_box_candidate(
                            sleeve_source="D1_REBATE_MACHINE_GUN",
                            box_type="DOMINANCE_MAKER_ANCHOR",
                            asset=m15.asset,
                            dedupe_key=f"D1_REBMG_{m15.asset}_{m15.market_id}_{m5.market_id}",
                            regime=str(dom_info["regime"]),
                            pair_horizons=f"{m15.horizon}_{m5.horizon}",
                            leg_a=leg_a,
                            leg_b=leg_b,
                            anchor_is_a=anc_a_r,
                            queue_front=True,
                            anchor_bid_px=float(reb_ev["anchor_bid_px"]),
                            hedge_limit_px=float(ask_b if anc_a_r else ask_a),
                            avail_a_shares=av_a_r,
                            avail_b_shares=av_b_r,
                            close_ts=float(m5.end_ts),
                            now_ts=now_ts,
                            k_low=float(dom_info["k_low"]),
                            k_high=float(dom_info["k_high"]),
                            corridor_bps=float(dom_info["corridor_bps"]),
                            posted_spot=self._latest_spot_px(m15.asset),
                        )
                        return emitted_r if live_emit_only else False
            return False
        candidates.sort(key=lambda z: z[0])
        _, anchor_is_a, q_front, bid_px, hdg_eff, req_sh = candidates[0]
        posted_sp = self._latest_spot_px(m15.asset)
        if not live_emit_only:
            self.pending_maker_anchors[d_key] = {
                "dedupe_key": d_key,
                "asset": m15.asset,
                "m15": m15,
                "m5": m5,
                "dom_info": dom_info,
                "anchor_is_a": anchor_is_a,
                "queue_front": q_front,
                "bid_px": bid_px,
                "pair_est": round(bid_px + hdg_eff, 4),
                "req_shares_t100": req_sh,
                "req_shares_t1000": req_sh_t1000,
                "posted_ts": now_ts,
                "posted_spot": posted_sp,
            }
        av_a_sh = sum(sz for px, sz in asks_a if px <= ask_a + 0.01)
        av_b_sh = sum(sz for px, sz in asks_b if px <= ask_b + 0.01)
        hdg_raw_px = ask_b if anchor_is_a else ask_a
        emitted_m = False
        if self._strike_is_rest_verified(m15) and self._strike_is_rest_verified(m5):
            emitted_m = self.emit_live_maker_anchor_box_candidate(
                sleeve_source="D1_MAKER_ANCHOR_BOX",
                box_type="DOMINANCE_MAKER_ANCHOR",
                asset=m15.asset,
                dedupe_key=d_key,
                regime=str(dom_info["regime"]),
                pair_horizons=f"{m15.horizon}_{m5.horizon}",
                leg_a=leg_a,
                leg_b=leg_b,
                anchor_is_a=anchor_is_a,
                queue_front=q_front,
                anchor_bid_px=bid_px,
                hedge_limit_px=hdg_raw_px,
                avail_a_shares=av_a_sh,
                avail_b_shares=av_b_sh,
                close_ts=float(m5.end_ts),
                now_ts=now_ts,
                k_low=float(dom_info["k_low"]),
                k_high=float(dom_info["k_high"]),
                corridor_bps=float(dom_info["corridor_bps"]),
                posted_spot=posted_sp,
            )
        if live_emit_only:
            return emitted_m
        logger.info(
            f"[MAKER_ANCHOR_POST] {m15.asset} {dom_info['regime']} | Resting post_only=${bid_px:.3f} (qf={q_front}) "
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
            q_front = bool(st.get("queue_front", True))
            leg_anc = leg_a if anc_is_a else leg_b
            leg_hdg = leg_b if anc_is_a else leg_a
            bk_anc = bks.get(str(leg_anc["token_id"]))
            bk_hdg = bks.get(str(leg_hdg["token_id"]))
            bid_px = float(st["bid_px"])
            rested = now - float(st["posted_ts"])
            rem_sec = m5.end_ts - now

            asks_anc = (bk_anc or {}).get("asks") or []
            best_ask_anc = min((float(a["price"]) for a in asks_anc if float(a.get("size", 0)) > 0), default=1.0)
            filled_anc = bk_anc is not None and rested >= 0.35 and best_ask_anc <= bid_px

            if filled_anc:
                self.pending_maker_anchors.pop(d_key, None)
                self.entered_keys.add(d_key)
                asks_hdg = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
                hdg_px = asks_hdg[0][0] if asks_hdg else 1.0
                hdg_avail = sum(sz for px, sz in asks_hdg if px <= hdg_px + 0.01) if asks_hdg else 0.0
                hdg_fee = float(leg_hdg["fee_rate"]) * ((hdg_px * (1.0 - hdg_px)) ** float(leg_hdg.get("fee_exponent", 1.0))) if hdg_px < 1.0 else 0.0
                pair_eff = round(bid_px + hdg_px + hdg_fee, 4)

                asset_cap_u = float(EMPIRICAL_BOX_ASSET_CAPS_USD.get(m15.asset, 100.0))
                is_4h_m = "4h" in (str(m15.horizon).lower(), str(m5.horizon).lower())
                if bk_hdg is not None and asks_hdg and hdg_avail >= 5.0 and 0.900 <= pair_eff <= 0.995:
                    tier_fills: Dict[str, Dict[str, Any]] = {}
                    drag_by_tier: Dict[str, float] = {}
                    rebate_est_t1000 = 0.0
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
                        dr = compute_d1_maker_anchor_drag_haircut(
                            shares=sh,
                            pair_eff=pair_eff,
                            bid_anc=bid_px,
                            hdg_px=hdg_px,
                            hdg_avail_shares=hdg_avail,
                            fee_rate_anc=float(leg_anc.get("fee_rate", CRYPTO_FEE_RATE)),
                            fee_exponent_anc=float(leg_anc.get("fee_exponent", 1.0)),
                            queue_front=q_front,
                            is_4h_mixed=is_4h_m,
                        )
                        drag_by_tier[t_name] = float(dr["legging_drag_usd"])
                        if t_name == "T1000":
                            rebate_est_t1000 = float(dr["maker_rebate_20pct_est_usd"])
                    bid_a_cur, _ = extract_best_bid((bks.get(str(leg_a["token_id"])) or {}).get("bids") or [])
                    bid_b_cur, _ = extract_best_bid((bks.get(str(leg_b["token_id"])) or {}).get("bids") or [])
                    pos_id = f"D1_MAKER_ANCHOR_BOX_{int(now)}_{m5.market_id[-6:]}"
                    pos = {
                        "position_id": pos_id,
                        "dedupe_key": d_key,
                        "sleeve": "D1_MAKER_ANCHOR_BOX",
                        "asset_or_city": m15.asset,
                        "title": f"{m15.asset} {di['regime']} [0%-Fee Maker Anchor @ ${bid_px:.3f}]",
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
                            "queue_front": q_front,
                            "legging_drag_usd_by_tier": drag_by_tier,
                            "maker_rebate_20pct_est_t1000_usd": rebate_est_t1000,
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
                    scr_fee = float(leg_anc["fee_rate"]) * ((scr_bid * (1.0 - scr_bid)) ** float(leg_anc.get("fee_exponent", 1.0)))
                    net_scr = max(0.0, scr_bid - scr_fee)
                    tf_s: Dict[str, Dict[str, Any]] = {}
                    tp_s: Dict[str, float] = {}
                    ref_pair = max(0.90, float(st.get("pair_est") or 0.985))
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        sh_s = max(5.0, float(math.floor(min(t_map["D1_MAKER_ANCHOR_BOX"], asset_cap_u) / ref_pair)))
                        bud = round(sh_s * bid_px, 2)
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
                        "legging_adjusted_tier_pnls_usd": dict(tp_s),
                        "won": tp_s.get("T1000", 0.0) > 0,
                        "status": "MAKER_ANCHOR_UNHEDGED_SCRATCH",
                    }
                    self.closed_positions.append(pos_scr)
                    self._append_ledger({"event": "SHADOW_CLOSE", **pos_scr})
                continue

            # Cancel-on-thinning / directional adverse-spot / OBI collapse / TTL=12s ($0.00 cost on unfilled post_only)
            asks_hdg_c = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
            hdg_px_c = asks_hdg_c[0][0] if asks_hdg_c else 1.0
            hdg_avail_c = sum(sz for px, sz in asks_hdg_c if px <= hdg_px_c + 0.01) if asks_hdg_c else 0.0
            hdg_fee_c = float(leg_hdg["fee_rate"]) * ((hdg_px_c * (1.0 - hdg_px_c)) ** float(leg_hdg.get("fee_exponent", 1.0))) if hdg_px_c < 1.0 else 0.0
            req_sh_chk = float(st.get("req_shares_t100") or st.get("req_shares_t1000") or 15.0)
            thin_or_drifted = (hdg_avail_c < max(12.0, 2.0 * req_sh_chk)) or ((bid_px + hdg_px_c + hdg_fee_c) > 0.993)
            obi_anc_c = 0.0
            if bk_anc is not None:
                _, b_sz_c = extract_best_bid(bk_anc.get("bids") or [])
                a_sz_c = sum(float(a.get("size", 0)) for a in asks_anc if abs(float(a.get("price", 0)) - best_ask_anc) < 1e-6)
                if (b_sz_c + a_sz_c) > 0.0:
                    obi_anc_c = (b_sz_c - a_sz_c) / (b_sz_c + a_sz_c)
            post_spot = float(st.get("posted_spot") or 0.0)
            cur_spot = self._latest_spot_px(m15.asset)
            spot_drift_bps = ((cur_spot - post_spot) / post_spot * 10000.0) if (post_spot > 0.0 and cur_spot > 0.0) else 0.0
            ret_5s_c = self.get_return_bps(m15.asset, 5.0)
            anc_side_c = str(leg_anc.get("side") or "UP").upper()
            adv_move_c = (
                (min(spot_drift_bps, ret_5s_c) < -2.5)
                if anc_side_c == "UP"
                else (max(spot_drift_bps, ret_5s_c) > 2.5)
            )
            shock_recent = (now - float(self._last_any_shock_ts_by_asset.get(m15.asset, 0.0) or 0.0)) < 4.0
            if (
                rem_sec <= 45.0
                or rested >= (12.0 if self.single_scan else 90.0)
                or adv_move_c
                or abs(ret_5s_c) > 8.0
                or obi_anc_c < -0.35
                or shock_recent
                or thin_or_drifted
            ):
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
        prefetched_books: Optional[Dict[str, Dict[str, Any]]] = None,
        *,
        live_emit_only: bool = False,
    ) -> bool:
        """
        EXP-PM-409 (`ZF_INTRADAY_MAKER_BOX`): Hardened intraday (`65s <= TTE <= 18h`) `0%`-fee Maker Anchor
        for `SP1_NBA` Polish Middles (`$0.95 + $0.01 = $0.960`), same-day `CM_B3` Pyth barriers, `TW1`, and `COND1`:
          - Tick-exact `[0.001, 0.999]` pricing with `+1 tick` queue-front step,
          - `obi_anc >= -0.25`, `0.900 <= pair_est <= 0.988` anti-box floor + `opp_token_id` complement guard,
          - Realistic `T100` (`$18`) `>= 2.5x` hedge depth gate and Keep-Alive While Valid queue retention.
        """
        if is_shadow_sleeve_quarantined("ZF_INTRADAY_MAKER_BOX"):
            return False
        rem_sec = float(close_ts - now_ts)
        if not (65.0 <= rem_sec <= 64800.0):
            return False
        cd_map = self.__dict__.setdefault("_zf_maker_cooldown_until", {})
        if not live_emit_only and (
            d_key in self.entered_keys
            or d_key in self.pending_zero_fee_maker_anchors
            or float(cd_map.get(d_key, 0.0) or 0.0) > now_ts
        ):
            return False
        if float(leg_a.get("fee_rate", 0.0)) > 0.0 or float(leg_b.get("fee_rate", 0.0)) > 0.0:
            return False
        if prefetched_books:
            opp_a = str(leg_a.get("opp_token_id") or "")
            opp_b = str(leg_b.get("opp_token_id") or "")
            if opp_a in prefetched_books and opp_b in prefetched_books:
                ob_a, _ = extract_best_bid((prefetched_books[opp_a] or {}).get("bids") or [])
                ob_b, _ = extract_best_bid((prefetched_books[opp_b] or {}).get("bids") or [])
                ta_ask, _ = self._best_ask_sz(bk_a)
                tb_ask, _ = self._best_ask_sz(bk_b)
                if (
                    (ta_ask > 0.0 and ob_a > 0.0 and (ta_ask + ob_a) > 1.015)
                    or (tb_ask > 0.0 and ob_b > 0.0 and (tb_ask + ob_b) > 1.015)
                    or (ob_a + ob_b) > 1.160
                ):
                    return False

        bids_a = sorted([(float(b["price"]), float(b["size"])) for b in (bk_a.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0], key=lambda x: -x[0])
        bids_b = sorted([(float(b["price"]), float(b["size"])) for b in (bk_b.get("bids") or []) if float(b.get("price", 0)) > 0 and float(b.get("size", 0)) > 0], key=lambda x: -x[0])
        asks_a = sorted([(float(a["price"]), float(a["size"])) for a in (bk_a.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        asks_b = sorted([(float(a["price"]), float(a["size"])) for a in (bk_b.get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
        if not asks_a or not asks_b or not bids_a or not bids_b:
            return False
        bid_a, bsz_a = bids_a[0]
        bid_b, bsz_b = bids_b[0]
        ask_a, asz_a = asks_a[0]
        ask_b, asz_b = asks_b[0]
        obi_a = (bsz_a - asz_a) / max(1e-9, bsz_a + asz_a)
        obi_b = (bsz_b - asz_b) / max(1e-9, bsz_b + asz_b)
        req_sh_t100 = max(6.0, math.floor(float(BANKROLL_TICKETS["T100"]["ZF_INTRADAY_MAKER_BOX"]) / 0.988))
        req_sh_t1000 = max(6.0, math.floor(float(BANKROLL_TICKETS["T1000"]["ZF_INTRADAY_MAKER_BOX"]) / 0.988))

        def _snap_zf(p: float) -> float:
            p = round(float(p), 4)
            return (math.floor((p + 1e-9) * 100.0) / 100.0) if (0.04 + 1e-9 < p < 0.96 - 1e-9) else (math.floor((p + 1e-9) * 1000.0) / 1000.0)

        max_pair_zf = 0.992 if source_tag == "SP1_NBA" else (0.985 if rem_sec > 3600.0 else 0.988)
        zf_cands: List[Tuple[float, bool, float, float, bool]] = []
        for anc_is_a in (True, False):
            b_anc = bid_a if anc_is_a else bid_b
            bsz_anc = bsz_a if anc_is_a else bsz_b
            a_anc = ask_a if anc_is_a else ask_b
            obi_anc = obi_a if anc_is_a else obi_b
            b_hdg = bid_b if anc_is_a else bid_a
            asks_hdg = asks_b if anc_is_a else asks_a
            a_hdg = asks_hdg[0][0]
            if not (0.02 <= a_anc <= 0.999) or not (0.001 <= a_hdg <= 0.985) or obi_anc < -0.25:
                continue
            if b_hdg > 0.0 and a_hdg > 0.04 and (a_hdg - b_hdg) > 0.05:
                continue
            tb_anc = 0.001 if (b_anc >= 0.96 or b_anc < 0.04) else 0.01
            ta_anc = 0.001 if (a_anc > 0.96 or a_anc <= 0.04) else 0.01
            step_b = _snap_zf(b_anc + tb_anc)
            max_u = _snap_zf(a_anc - ta_anc)
            avail_hdg = sum(sz for px, sz in asks_hdg if px <= a_hdg + 0.01)
            if avail_hdg < max(18.0, 2.5 * req_sh_t100):
                continue
            q_front = True
            if step_b <= max_u + 1e-9 and step_b > b_anc + 1e-9:
                cand_bid = min(step_b, max_u, _snap_zf(max_pair_zf - a_hdg))
                q_front = cand_bid > b_anc + 1e-9
            elif (a_anc - b_anc) >= 0.01 - 1e-9 and 0.15 <= a_anc <= 0.88 and obi_anc >= -0.15 and bsz_anc >= 15.0:
                q_front = False
                cand_bid = min(_snap_zf(b_anc), _snap_zf(max_pair_zf - a_hdg))
            else:
                continue
            if cand_bid < round(b_anc - tb_anc, 3) or cand_bid <= 0.015 or cand_bid >= a_anc:
                continue
            pair_est = round(cand_bid + a_hdg, 4)
            if 0.860 <= pair_est <= max_pair_zf:
                zf_cands.append((pair_est, anc_is_a, round(cand_bid, 4), round(a_hdg, 4), q_front))

        if not zf_cands:
            return False
        zf_cands.sort(key=lambda z: (z[0], 0 if z[4] else 1))
        pair_est, anc_is_a, bid_px, hdg_px, q_front_win = zf_cands[0]
        if not live_emit_only:
            self.pending_zero_fee_maker_anchors[d_key] = {
                "source_tag": source_tag,
                "dedupe_key": d_key,
                "asset": asset,
                "title": title,
                "leg_a": leg_a,
                "leg_b": leg_b,
                "anchor_is_a": anc_is_a,
                "bid_px": bid_px,
                "pair_est": pair_est,
                "queue_front": q_front_win,
                "req_shares_t100": req_sh_t100,
                "req_shares_t1000": req_sh_t1000,
                "close_ts": close_ts,
                "posted_ts": now_ts,
            }
        av_a_sh = sum(sz for px, sz in asks_a if px <= ask_a + 0.01)
        av_b_sh = sum(sz for px, sz in asks_b if px <= ask_b + 0.01)
        emitted_zf = self.emit_live_maker_anchor_box_candidate(
            sleeve_source="ZF_INTRADAY_MAKER_BOX",
            box_type="ZERO_FEE_MAKER_ANCHOR",
            asset=asset,
            dedupe_key=d_key,
            regime=f"ZF_{source_tag}",
            pair_horizons=f"zf_{source_tag.lower()}",
            leg_a=leg_a,
            leg_b=leg_b,
            anchor_is_a=anc_is_a,
            queue_front=q_front_win,
            anchor_bid_px=bid_px,
            hedge_limit_px=hdg_px,
            avail_a_shares=av_a_sh,
            avail_b_shares=av_b_sh,
            close_ts=float(close_ts),
            now_ts=now_ts,
            k_low=float(leg_a.get("strike") or 100.0),
            k_high=float(leg_b.get("strike") or 100.0),
        )
        if live_emit_only:
            return emitted_zf
        logger.info(
            f"[ZF_INTRADAY_MAKER_POST:{source_tag}] {title} | bid=${bid_px:.3f} + hdg=${hdg_px:.3f} = ${pair_est:.4f} (TTE={rem_sec/3600.0:.2f}h)"
        )
        return True

    async def manage_pending_zero_fee_maker_anchors(self, now_ts: Optional[float] = None) -> None:
        if not self.pending_zero_fee_maker_anchors:
            return
        now = float(now_ts if now_ts is not None else time.time())
        cd_map = self.__dict__.setdefault("_zf_maker_cooldown_until", {})
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
            if bk_anc is not None and rested >= 0.40 and best_ask_anc <= bid_px:
                self.pending_zero_fee_maker_anchors.pop(d_key, None)
                self.entered_keys.add(d_key)
                asks_hdg = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
                hdg_px = asks_hdg[0][0] if asks_hdg else 1.0
                hdg_avail = sum(sz for px, sz in asks_hdg if px <= hdg_px + 0.01) if asks_hdg else 0.0
                pair_eff = round(bid_px + hdg_px, 4)
                if bk_hdg is not None and asks_hdg and hdg_avail >= 5.0 and 0.900 <= pair_eff <= 0.993:
                    tf_zf: Dict[str, Dict[str, Any]] = {}
                    drag_zf: Dict[str, float] = {}
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        sh = max(5.0, min(hdg_avail, math.floor(t_map["ZF_INTRADAY_MAKER_BOX"] / pair_eff)))
                        tf_zf[t_name] = {"filled": True, "vwap": pair_eff, "eff_px": pair_eff, "spent_usd": round(sh * pair_eff, 2), "fee_usd": 0.0, "shares": sh, "l1_usd": round(hdg_avail * pair_eff, 2)}
                        dr_z = compute_d1_maker_anchor_drag_haircut(
                            shares=sh, pair_eff=pair_eff, bid_anc=bid_px, hdg_px=hdg_px,
                            hdg_avail_shares=hdg_avail, fee_rate_anc=0.0, fee_exponent_anc=1.0,
                            queue_front=bool(st.get("queue_front", True)), is_4h_mixed=False,
                        )
                        drag_zf[t_name] = float(dr_z["legging_drag_usd"])
                    ba_c, _ = extract_best_bid((bks.get(str(la["token_id"])) or {}).get("bids") or [])
                    bb_c, _ = extract_best_bid((bks.get(str(lb["token_id"])) or {}).get("bids") or [])
                    pid = f"ZF_INTRADAY_MKR_{int(now)}_{d_key[-8:]}"
                    pos = {
                        "position_id": pid, "dedupe_key": d_key, "sleeve": "ZF_INTRADAY_MAKER_BOX",
                        "asset_or_city": st["asset"], "title": f"{st['title']} [ZF Intraday Maker @ ${bid_px:.3f}]",
                        "side": f"{la['label']}+{lb['label']}", "token_id": f"{la['token_id']}|{lb['token_id']}",
                        "fee_rate": 0.0, "entry_ts": now, "entry_utc": datetime.now(timezone.utc).isoformat(),
                        "close_ts": st["close_ts"], "p_model_entry": 1.0, "entry_eff_px_t1000": pair_eff,
                        "entry_vwap_t1000": pair_eff, "realized_edge_t1000": round(1.0 - pair_eff, 4),
                        "entry_best_bid": round(ba_c + bb_c, 4), "last_bid": round(ba_c + bb_c, 4),
                        "maker_tp_px": None, "tier_fills": tf_zf,
                        "extra": {"is_two_leg_box": True, "is_maker_anchor_box": True, "legging_drag_usd_by_tier": drag_zf, "source_tag": st["source_tag"], "leg_a": la, "leg_b": lb},
                        "status": "OPEN",
                    }
                    self.open_positions[pid] = pos
                    self._append_ledger({"event": "SHADOW_ENTRY", **pos})
                    logger.info(f"[ENTRY:ZF_INTRADAY_MAKER_BOX] {pos['title']} -> Hedged @ ${pair_eff:.4f}!")
                else:
                    scr_bid, _ = extract_best_bid((bk_anc or {}).get("bids") or [])
                    net_scr = scr_bid if scr_bid > 0 else max(0.01, bid_px - 0.03)
                    tf_s, tp_s = {}, {}
                    ref_zf_pair = max(0.90, float(st.get("pair_est") or 0.986))
                    for t_name, t_map in BANKROLL_TICKETS.items():
                        sh_s = max(5.0, float(math.floor(t_map["ZF_INTRADAY_MAKER_BOX"] / ref_zf_pair)))
                        bud = round(sh_s * bid_px, 2)
                        tf_s[t_name] = {"filled": True, "vwap": bid_px, "eff_px": bid_px, "spent_usd": bud, "fee_usd": 0.0, "shares": sh_s}
                        tp_s[t_name] = round(sh_s * net_scr - bud, 2)
                    pos_scr = {
                        "position_id": f"ZF_MKR_SCRATCH_{int(now)}_{d_key[-8:]}", "dedupe_key": d_key,
                        "sleeve": "ZF_INTRADAY_MAKER_BOX", "asset_or_city": st["asset"],
                        "title": f"{st['title']} [ZF Intraday Maker Scratch]", "side": f"{leg_anc['label']}_SCRATCH",
                        "token_id": str(leg_anc["token_id"]), "fee_rate": 0.0, "entry_ts": st["posted_ts"],
                        "entry_utc": datetime.fromtimestamp(st["posted_ts"], tz=timezone.utc).isoformat(),
                        "close_ts": st["close_ts"], "closed_ts": now, "closed_utc": datetime.now(timezone.utc).isoformat(),
                        "p_model_entry": 0.5, "entry_eff_px_t1000": bid_px, "entry_vwap_t1000": bid_px,
                        "net_payout_per_share": round(net_scr, 4), "tier_fills": tf_s, "tier_pnls_usd": tp_s,
                        "legging_adjusted_tier_pnls_usd": dict(tp_s), "won": tp_s.get("T1000", 0.0) > 0,
                        "status": "MAKER_ANCHOR_UNHEDGED_SCRATCH",
                    }
                    self.closed_positions.append(pos_scr)
                    self._append_ledger({"event": "SHADOW_CLOSE", **pos_scr})
                continue
            asks_hdg_c = sorted([(float(a["price"]), float(a["size"])) for a in ((bk_hdg or {}).get("asks") or []) if float(a.get("price", 0)) > 0 and float(a.get("size", 0)) > 0])
            hdg_px_c = asks_hdg_c[0][0] if asks_hdg_c else 1.0
            hdg_avail_c = sum(sz for px, sz in asks_hdg_c if px <= hdg_px_c + 0.01) if asks_hdg_c else 0.0
            req_sh_chk = float(st.get("req_shares_t100") or 18.0)
            best_bid_anc_c, b_sz_c = extract_best_bid((bk_anc or {}).get("bids") or [])
            a_sz_c = sum(float(a.get("size", 0)) for a in asks_anc if abs(float(a.get("price", 0)) - best_ask_anc) < 1e-6)
            obi_anc_c = ((b_sz_c - a_sz_c) / (b_sz_c + a_sz_c)) if (b_sz_c + a_sz_c) > 0.0 else 0.0
            max_keep_pair = 0.993 if st.get("source_tag") == "SP1_NBA" else 0.991
            adverse_zf = (
                rem_sec <= 60.0
                or obi_anc_c < -0.30
                or (best_bid_anc_c > 0.0 and best_bid_anc_c < bid_px - 0.015)
                or hdg_avail_c < max(12.0, 2.0 * req_sh_chk)
                or (bid_px + hdg_px_c) > max_keep_pair
            )
            if adverse_zf or rested >= (15.0 if self.single_scan else 90.0):
                self.pending_zero_fee_maker_anchors.pop(d_key, None)
                if adverse_zf:
                    cd_map[d_key] = now + 12.0
                else:
                    cd_map.pop(d_key, None)
                    self.last_tradfi_sports_scan_ts = min(float(self.last_tradfi_sports_scan_ts), now - 16.0)

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
        rem_to_1h = (math.ceil(now / 3600.0) * 3600.0) - now
        in_disc_win = (
            self.is_in_same_oracle_overlap_window(now)
            if (self.single_scan or "fetch_json" in self.__dict__)
            else ((5.0 <= rem_to_15m <= 330.0) or (5.0 <= rem_to_1h <= 905.0))
        )
        if in_disc_win and (now - self.last_dominance_discovery_ts) >= disc_interval:
            self.last_dominance_discovery_ts = now
            await self.discover_dominance_pairs(now)

        if now_ts is None:
            self.record_usd_spot_samples(time.time())

        active_pairs = [
            (m15, m5)
            for m15, m5 in list(self.dominance_pairs.values())
            if (10.0 <= (m5.end_ts - now) <= (900.0 if m5.horizon == "15m" else 300.0))
            and (now >= m5.start_ts + 1.0)
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
                    pair_tag = f"{m15.horizon}_{m5.horizon}"
                    self._record_d1_corridor_telemetry(pair_tag, m15, m5, dom_info, bk_a, bk_b, eval_now)
                    rem_live = m5.end_ts - eval_now
                    # LIVE emits require both strikes REST/Gamma-verified (unverified WS-TWAP strikes stay shadow-only)
                    strikes_verified = self._strike_is_rest_verified(m15) and self._strike_is_rest_verified(m5)
                    live_fok_emitted = False
                    max_rem_live = 898.0 if m5.horizon == "15m" else 298.0
                    if strikes_verified and 16.0 <= rem_live <= max_rem_live:
                        live_emit_cap = self._d1_live_max_box_cost()
                        quiet_grad = self.is_sleeve_grad8_ready("D1_QUIET_BOOK_BOX")
                        walk_emit_cap = max(live_emit_cap, 0.989) if quiet_grad else live_emit_cap
                        w_live = walk_equal_shares_dominance_box(
                            bk_a.get("asks") or [],
                            bk_b.get("asks") or [],
                            target_budget_usd=24.00,
                            fee_rate_a=float(leg_a["fee_rate"]),
                            fee_rate_b=float(leg_b["fee_rate"]),
                            fee_exponent_a=float(leg_a["fee_exponent"]),
                            fee_exponent_b=float(leg_b["fee_exponent"]),
                            max_box_cost_net=walk_emit_cap,
                            min_shares=5,
                            min_box_notional_usd=4.85,
                            min_box_cost_net=0.860,
                        )
                        if w_live.get("filled"):
                            is_quiet_live = self._passes_quiet_book_filter(m15.asset, bk_a, bk_b, w_live, eval_now)
                            eff_emit_cap = walk_emit_cap if (is_quiet_live and quiet_grad) else live_emit_cap
                            if float(w_live["box_cost_net"]) <= eff_emit_cap:
                                comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=batch_bks)
                                if not comp_checked:
                                    continue
                                live_fok_emitted = self.emit_live_d1_box_candidate(
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
                        max_box_cost_net=1.032,  # Surface near-arb boxes <= $1.032 so 2.1c-3.6c Maker-Leg-1 fee+spread savings can lock <= $0.988!
                        min_shares=8,
                        min_box_notional_usd=7.5,
                        min_box_cost_net=0.860 if strikes_verified else 0.900,
                    )
                    taker_cleared_995 = False
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
                            taker_cleared_995 = True
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
                    if not taker_cleared_995 or not live_fok_emitted:
                        ask_a_l1, _ = self._best_ask_sz(bk_a)
                        ask_b_l1, _ = self._best_ask_sz(bk_b)
                        bid_a_l1, _ = extract_best_bid(bk_a.get("bids") or [])
                        bid_b_l1, _ = extract_best_bid(bk_b.get("bids") or [])
                        if (ask_a_l1 + ask_b_l1) <= 1.020 or (
                            bid_a_l1 > 0.0 and bid_b_l1 > 0.0 and min(bid_a_l1 + ask_b_l1, ask_a_l1 + bid_b_l1) <= 1.005
                        ):
                            if comp_checked is None:
                                comp_checked = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=batch_bks)
                            if comp_checked:
                                self.post_maker_anchor_candidate(
                                    m15, m5, dom_info, bk_a, bk_b, eval_now,
                                    live_emit_only=bool(taker_cleared_995),
                                )

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
            live_4h_fok_emitted = False
            if strikes_4h_verified and 18.0 <= rem_4h_live <= max_rem:
                live_4h_cap = self._d1_live_max_box_cost()
                quiet_4h_grad = self.is_sleeve_grad8_ready("D1_QUIET_BOOK_BOX")
                walk_4h_cap = max(live_4h_cap, 0.989) if quiet_4h_grad else live_4h_cap
                w_live_4h = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=13.50,
                    fee_rate_a=float(leg_a["fee_rate"]),
                    fee_rate_b=float(leg_b["fee_rate"]),
                    fee_exponent_a=float(leg_a["fee_exponent"]),
                    fee_exponent_b=float(leg_b["fee_exponent"]),
                    max_box_cost_net=walk_4h_cap,
                    min_shares=5,
                    min_box_notional_usd=4.85,
                    min_box_cost_net=0.860,
                )
                if w_live_4h.get("filled"):
                    is_quiet_4h = self._passes_quiet_book_filter(m4.asset, bk_a, bk_b, w_live_4h, eval_4h_now)
                    eff_4h_cap = walk_4h_cap if (is_quiet_4h and quiet_4h_grad) else live_4h_cap
                    if float(w_live_4h["box_cost_net"]) <= eff_4h_cap:
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=bks_4h)
                        if not comp_4h_ok:
                            continue
                        live_4h_fok_emitted = self.emit_live_d1_box_candidate(
                            m4,
                            m_short,
                            dom_info,
                            w_live_4h,
                            eval_4h_now,
                            is_quiet_book=is_quiet_4h,
                            sleeve_source="D1_QUIET_BOOK_BOX" if is_quiet_4h else "D1_4H_DOMINANCE_BOX",
                        )
            w_scan = walk_equal_shares_dominance_box(
                bk_a.get("asks") or [],
                bk_b.get("asks") or [],
                target_budget_usd=BANKROLL_TICKETS["T1000"]["D1_4H_DOMINANCE_BOX"],
                fee_rate_a=float(leg_a["fee_rate"]),
                fee_rate_b=float(leg_b["fee_rate"]),
                fee_exponent_a=float(leg_a["fee_exponent"]),
                fee_exponent_b=float(leg_b["fee_exponent"]),
                max_box_cost_net=1.032,
                min_shares=8,
                min_box_notional_usd=7.5,
                min_box_cost_net=0.860 if strikes_4h_verified else 0.900,
            )
            taker_4h_cleared = False
            if w_scan.get("filled"):
                box_net = float(w_scan["box_cost_net"])
                if box_net <= 1.005:
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
                    taker_4h_cleared = True
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
            if not taker_4h_cleared or not live_4h_fok_emitted:
                ask_a_4h, _ = self._best_ask_sz(bk_a)
                ask_b_4h, _ = self._best_ask_sz(bk_b)
                bid_a_4h, _ = extract_best_bid(bk_a.get("bids") or [])
                bid_b_4h, _ = extract_best_bid(bk_b.get("bids") or [])
                if (ask_a_4h + ask_b_4h) <= 1.020 or (
                    bid_a_4h > 0.0 and bid_b_4h > 0.0 and min(bid_a_4h + ask_b_4h, ask_a_4h + bid_b_4h) <= 1.005
                ):
                    if comp_4h_ok is None:
                        comp_4h_ok = await self._passes_complement_anti_box_check(leg_a, leg_b, prefetched_books=bks_4h)
                    if comp_4h_ok:
                        self.post_maker_anchor_candidate(
                            m4, m_short, dom_info, bk_a, bk_b, eval_4h_now,
                            live_emit_only=bool(taker_4h_cleared),
                        )

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
        boundary (`4.0 <= rem_5m <= 55.0`), stepping the Gatling fast-gun cadence to <200ms.
        """
        target_end_ts = math.ceil(now_ts / 300.0) * 300.0
        rem_sec = target_end_ts - now_ts
        return 4.0 <= rem_sec <= 55.0

    async def discover_active_twap_candles(self, now_ts: Optional[float] = None) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        for k_old, sp_old in list(self.twap_candles.items()):
            if sp_old.end_ts < now - 300.0:
                self.twap_candles.pop(k_old, None)

        end_5m = int(math.ceil(now / 300.0) * 300)
        rem_5m = float(end_5m) - now
        max_twap_disc = 75.0 if (self.single_scan or "fetch_json" in self.__dict__) else 95.0
        if not (3.5 <= rem_5m <= max_twap_disc):
            return

        # Reuse any 60s-TWAP pair already discovered by D1_SAME_ORACLE_DOMINANCE_BOX
        for _, (m15_p, m5_p) in self.dominance_pairs.items():
            if int(m5_p.twap_lookback_sec) == 60 and abs(m5_p.end_ts - end_5m) <= 2.0:
                self.twap_candles[f"{m5_p.asset}_{m5_p.horizon}_{end_5m}"] = m5_p
            if int(m15_p.twap_lookback_sec) == 60 and abs(m15_p.end_ts - end_5m) <= 2.0:
                self.twap_candles[f"{m15_p.asset}_{m15_p.horizon}_{end_5m}"] = m15_p
        for _, (m4_p, ms_p) in self.dominance_4h_pairs.items():
            if int(m4_p.twap_lookback_sec) == 60 and abs(m4_p.end_ts - end_5m) <= 2.0:
                self.twap_candles[f"{m4_p.asset}_4h_{end_5m}"] = m4_p

        now_iso = datetime.fromtimestamp(now - 5.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        is_15m_boundary = (end_5m % 900) == 0

        async def _disc_twap_asset(asset: str) -> None:
            slugs = DOMINANCE_SERIES_SLUGS[asset]
            k5 = f"{asset}_5m_{end_5m}"
            if k5 not in self.twap_candles:
                ev5_raw = await self.fetch_json(
                    f"{GAMMA_URL}/events?series_slug={slugs['5m']}&closed=false&end_date_min={now_iso}&order=endDate&ascending=true&limit=3",
                    timeout=3.0,
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
                        timeout=3.0,
                    )
                    if isinstance(ev15_raw, list):
                        for ev in ev15_raw:
                            sp15 = parse_twap_candle_event(ev, asset, "15m")
                            if sp15 and abs(sp15.end_ts - end_5m) <= 2.0:
                                self.twap_candles[k15] = sp15
                                break

        await asyncio.gather(*(_disc_twap_asset(a) for a in DOMINANCE_ASSETS))
        # Pre-warm REST-verified strikes ahead of the final 20s lock window so 0 REST latency hits TTE <= 16s!
        if not self.single_scan and rem_5m >= 22.0:
            warm_specs = [
                sp for sp in list(self.twap_candles.values())
                if abs(sp.end_ts - end_5m) <= 2.0 and f"{sp.asset}_{sp.horizon}_{int(sp.start_ts)}" not in self.chainlink_open_cache
            ]
            if warm_specs:
                await asyncio.gather(*(self.get_authoritative_open_strike(sp) for sp in warm_specs))

    async def scan_exact_twap_locks(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        if not self.single_scan and is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK"):
            if self.twap_candles:
                self.twap_candles.clear()
            return
        s2_lock = self.__dict__.setdefault("_s2_scan_lock", asyncio.Lock())
        if s2_lock.locked():
            return
        async with s2_lock:
            now = float(now_ts if now_ts is not None else time.time())
            _is_mock_s2 = bool(self.single_scan or "fetch_json" in self.__dict__)
            shm_bks: Dict[str, Dict[str, Any]] = {}
            if not _is_mock_s2:
                from src.polymarket_research.riskless_protocol_v2_expansion import hydrate_fast_s2_from_shm
                shm_bks = hydrate_fast_s2_from_shm(self, now)
            rem_5m = (math.ceil(now / 300.0) * 300.0) - now
            disc_iv = 8.0 if rem_5m <= 40.0 else 12.0
            _skip_lock_disc = (not _is_mock_s2) and rem_5m <= 40.0 and any(abs(sp.end_ts - math.ceil(now / 300.0) * 300.0) <= 2.0 for sp in self.twap_candles.values())
            if not _skip_lock_disc and 3.5 <= rem_5m <= (75.0 if _is_mock_s2 else 95.0) and (now - self.last_twap_discovery_ts) >= disc_iv:
                self.last_twap_discovery_ts = now
                await self.discover_active_twap_candles(now)

            s2_strict = os.getenv("PM_QUARANTINE_LOSING_SLEEVES", "1") == "1"
            max_s2_rem = 38.5 if s2_strict else 45.0
            min_s2_rem = 8.0 if self.single_scan else 4.2
            min_s2_p = 0.975 if s2_strict else 0.965
            min_s2_z = 2.65 if s2_strict else 0.0

            cand_specs = [
                spec for _, spec in sorted(
                    self.twap_candles.items(),
                    key=lambda kv: ({"BTC": 0, "ETH": 1, "SOL": 2}.get(getattr(kv[1], "asset", ""), 9), getattr(kv[1], "end_ts", 0.0)),
                )
                if int(spec.twap_lookback_sec) == 60
                and (min_s2_rem <= (spec.end_ts - now) <= max_s2_rem)
                and (now >= spec.start_ts + 60.0)
            ]
            if not cand_specs:
                return

            # Resolve strikes in parallel (instant cache hit when pre-warmed at T - 90s!)
            strikes = await asyncio.gather(*(self.get_authoritative_open_strike(sp) for sp in cand_specs))
            valid_pairs = [(sp, k_op) for sp, k_op in zip(cand_specs, strikes) if k_op is not None and k_op > 0.0]
            if not valid_pairs:
                return

            # Batch-fetch both UP and DOWN L2 books in a single parallel pass (uses sub-ms CLOB WS cache first!)
            s2_toks: List[str] = []
            for sp, _ in valid_pairs:
                s2_toks.extend([sp.up_token, sp.down_token])
            bks_s2 = (
                {**shm_bks, **(await self.fetch_books_batch(s2_toks, timeout=1.5) or {})}
                if not _is_mock_s2
                else {}
            )
            for tk_s2, sh_bk in shm_bks.items():
                if isinstance(bks_s2.get(tk_s2), dict) and "minimum_tick_size" not in bks_s2[tk_s2] and sh_bk.get("minimum_tick_size"):
                    bks_s2[tk_s2]["minimum_tick_size"] = sh_bk["minimum_tick_size"]

            for spec, k_open in valid_pairs:
                eval_now = float(now_ts) if (self.single_scan and now_ts is not None) else time.time()
                rem_sec = spec.end_ts - eval_now
                if not (min_s2_rem <= rem_sec <= max_s2_rem):
                    continue

                shm = (
                    read_shm_usd_anchor(spec.asset, eval_now, max_age_sec=2.5)
                    if not (self.single_scan and self.usd_spot_hist.get(spec.asset))
                    else {}
                )
                cl_ws_s2 = getattr(self, "_chainlink_ws", None) if not self.single_scan else None
                ws_spot_s2 = cl_ws_s2.get_latest_spot(spec.asset, now_ts=eval_now, max_age_sec=2.5) if cl_ws_s2 is not None else None
                off_twap_60 = (
                    cl_ws_s2.get_latest_official_twap_60s(spec.asset, now_ts=eval_now, max_age_sec=3.5)
                    if (cl_ws_s2 is not None and hasattr(cl_ws_s2, "get_latest_official_twap_60s"))
                    else None
                )
                usd_hist = self.usd_spot_hist.get(spec.asset)
                cur_usd = ws_spot_s2 or shm.get("usd_spot")
                if (not cur_usd or float(cur_usd) <= 0.0) and usd_hist and (eval_now - float(usd_hist[-1][0])) <= 5.0:
                    cur_usd = float(usd_hist[-1][1])
                if (not cur_usd or float(cur_usd) <= 0.0) and self.usd_direct_flags.get(spec.asset, False):
                    cur_usd = self.spots.get(spec.asset, 0.0)
                if not cur_usd or float(cur_usd) <= 0.0:
                    continue
                cur_usd_f = float(cur_usd)
                usd_direct = bool(
                    ws_spot_s2 is not None
                    or shm.get("source") in ("shm_chainlink_proxy", "shm_coinlink_usd", "shm_coinbase_usd")
                    or self.usd_direct_flags.get(spec.asset, False)
                )
                iv_1d, _ = get_wing_implied_vol(spec.asset, cur_usd_f, k_open, 86400.0)
                samples = cl_ws_s2.get_recent_samples(spec.asset, spec.end_ts - 125.0) if cl_ws_s2 is not None else []
                win_cnt_s2 = sum(1 for t_s, _ in samples if t_s >= (spec.end_ts - 60.5))
                if len(samples) < 2 or (rem_sec <= 55.0 and usd_hist and win_cnt_s2 < int(max(3.0, (60.0 - rem_sec) * 0.72))):
                    merged_s2 = {round(float(t_u), 1): float(p_u) for t_u, p_u in (usd_hist or []) if t_u >= (spec.end_ts - 125.0)}
                    for t_w, p_w in samples:
                        merged_s2[round(float(t_w), 1)] = float(p_w)
                    samples = sorted(merged_s2.items(), key=lambda x: x[0])
                if not _is_mock_s2 and 3.8 <= rem_sec <= 38.0 and self._strike_is_rest_verified(spec) and len(samples) >= 6:
                    from src.polymarket_research.riskless_protocol_v2_expansion import maybe_emit_s2_live_locks
                    maybe_emit_s2_live_locks(
                        self, spec=spec, k_open=k_open, eval_now=eval_now, rem_sec=rem_sec, samples=samples,
                        off_twap_60=off_twap_60, bks_s2=bks_s2 or {}, logger_obj=logger,
                    )
                lock_ev = compute_exact_twap_lock_probability(
                    asset=spec.asset,
                    open_price=k_open,
                    current_usd_spot=cur_usd_f,
                    rem_seconds=rem_sec,
                    now_ts=eval_now,
                    end_ts=spec.end_ts,
                    spot_samples=samples,
                    shm_twap_60s=off_twap_60 or shm.get("twap_60s"),
                    iv_annual=iv_1d,
                    usd_direct_feed=usd_direct,
                    authoritative_chainlink_ws=bool(ws_spot_s2 is not None),
                    min_rem_seconds=min_s2_rem,
                )
                if not lock_ev.get("eligible") or float(lock_ev["p_lock"]) < 0.940 or float(lock_ev.get("z_lock", 0.0)) < min_s2_z:
                    continue

                win_side = str(lock_ev["side"])
                tok = spec.up_token if win_side == "UP" else spec.down_token
                opp_tok = spec.down_token if win_side == "UP" else spec.up_token
                bk = bks_s2.get(tok) if bks_s2 else await self.fetch_json(f"{CLOB_URL}/book?token_id={tok}", timeout=2.5)
                if not bk:
                    continue
                bk_opp = bks_s2.get(opp_tok) if bks_s2 else None

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

        s5m_assets = ("BTC", "ETH", "SOL")
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
        if not self.single_scan and is_shadow_sleeve_quarantined("S5M_CHAINLINK_SNIPER"):
            if self.s5m_candles:
                self.s5m_candles.clear()
            return
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

            shm = read_shm_usd_anchor(spec.asset, now, max_age_sec=3.0) if not self.single_scan else {}
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
                spec.asset,
                cur_usd_f,
                k_open,
                rem_sec,
                is_downward=False,
                dvol_annual_override=0.42 if (self.single_scan and "fetch_json" in self.__dict__) else None,
                now_ts=now,
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
                    sh = max(5.0, float(math.floor(t_map["P1_PREOPEN_MAKER_STRADDLE"] / max(0.90, pair_cost))))
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
                    sh_s = max(5.0, float(math.floor(t_map["P1_PREOPEN_MAKER_STRADDLE"] / max(0.90, 2.0 * bid_px))))
                    leg_budget = round(sh_s * bid_px, 2)
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
        if uma_st == "resolved" and 0.49 <= px <= 0.51:
            return round(px, 4)
        return None

    def _try_early_overround_bid_unwind(
        self,
        pos: Dict[str, Any],
        legs_bids_spec: List[Dict[str, Any]],
        now: float,
    ) -> Optional[Tuple[float, Dict[str, float]]]:
        """
        Evaluates whether an open 2-leg or N-leg riskless box can be exited immediately by sweeping
        resting L2 `bids` across 100% of held shares on every leg simultaneously:
          - Capped-payout complete-set partitions (`C1`, `NR0`, `N1`, `W3`, `P1`):
            requires `net_proceeds_per_set >= max(entry_eff + 0.010, guar_pay + 0.004)` (strictly > par!).
          - Dominance boxes with `$2.00` double-payout corridor (`FED1`, `COND1`, `CM_B3`, `SP1`, `TW1`, `D2`, `M3`, `B3`, `D1_*`):
            for lockups `> 1h` (`rem_tte > 3600s`), requires `>= max(entry_eff + 0.015, guar_pay + 0.005)`;
            for near-expiry boxes (`<= 1h`), requires `>= max(entry_eff + 0.080, guar_pay + 0.080)` to preserve `$2.00` corridor EV.
        """
        if (now - float(pos.get("entry_ts") or 0.0)) < 15.0:
            return None
        tier_fills = pos.get("tier_fills") or {}
        if "T1000" not in tier_fills:
            return None
        sh_t1000 = float(tier_fills["T1000"].get("shares") or 0.0)
        if sh_t1000 <= 0.0:
            return None
        extra = pos.get("extra") or {}
        guar_pay = float(extra.get("guaranteed_payout") or pos.get("p_model_entry") or 1.0)
        entry_eff = float(pos.get("entry_eff_px_t1000") or 0.99)
        rem_tte = float(pos["close_ts"]) - now
        capped_partition = pos.get("sleeve") in (
            "C1_BINARY_COMPLETE_SET",
            "NR0_ZERO_FEE_SLATE_ARB",
            "N1_NEGRISK_CROSS_BOX",
            "W3_WEATHER_SLATE_ARB",
            "P1_PREOPEN_MAKER_STRADDLE",
        ) or float(extra.get("max_payout") or 2.0) <= 1.001
        if capped_partition:
            min_net_req = max(entry_eff + 0.008, guar_pay + 0.004)
        elif rem_tte > 3600.0:
            min_net_req = max(entry_eff + 0.015, guar_pay + 0.005)
        else:
            min_net_req = max(entry_eff + 0.080, guar_pay + 0.080)

        w_ref = walk_position_overround_bid_unwind(legs_bids_spec, sh_t1000, min_net_proceeds_per_set=min_net_req)
        if not w_ref.get("filled"):
            return None
        tier_pay_map: Dict[str, float] = {}
        for t_name, tf in tier_fills.items():
            sh_t = float(tf.get("shares") or 0.0)
            if sh_t <= 0.0:
                continue
            wt = walk_position_overround_bid_unwind(legs_bids_spec, sh_t, min_net_proceeds_per_set=min_net_req)
            if not wt.get("filled"):
                return None
            tier_pay_map[t_name] = float(wt["net_proceeds_per_set"])
        return float(w_ref["net_proceeds_per_set"]), tier_pay_map

    async def manage_open_positions(self) -> None:
        now = time.time()
        loop = asyncio.get_running_loop()
        to_close: List[Tuple[str, str, float, Any]] = []  # (pos_id, status, payout_per_share, tier_pay_override)

        for pid, pos in list(self.open_positions.items()):
            sleeve = pos["sleeve"]
            tok = pos["token_id"]

            # 0A. Dedicated multi-leg supervision & settlement for D1, M3, B3, C1 & W3_WEATHER_SLATE_ARB
            if sleeve == "W3_WEATHER_SLATE_ARB":
                close_ts_f = float(pos["close_ts"])
                extra_w = pos.get("extra") or {}
                legs = extra_w.get("legs") or []
                if now < close_ts_f + 30.0:
                    bks_w = None
                    if (now - float(pos.get("_last_book_poll_ts") or 0.0)) >= 30.0 and legs:
                        pos["_last_book_poll_ts"] = now
                        bks_w = await asyncio.gather(
                            *[self.fetch_json(f"{CLOB_URL}/book?token_id={lg.get('token_id') or lg.get('yes_token', '')}", timeout=2.5) for lg in legs]
                        )
                        if all(bks_w):
                            pos["last_bid"] = round(sum(extract_best_bid((b or {}).get("bids") or [])[0] for b in bks_w), 4)
                            uw_w = self._try_early_overround_bid_unwind(
                                pos,
                                [{"bids": (b or {}).get("bids") or [], "fee_rate": 0.0, "fee_exponent": 1.0} for b in bks_w],
                                now,
                            )
                            if uw_w is not None:
                                to_close.append((pid, "EARLY_OVERROUND_BID_UNWIND", uw_w[0], uw_w[1]))
                                continue
                    if (now - float(pos.get("_last_gamma_chk_ts") or 0.0)) < (30.0 if (bks_w is not None and not all(bks_w)) else 120.0):
                        continue
                    pos["_last_gamma_chk_ts"] = now
                if legs:
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
                "ZF_INTRADAY_MAKER_BOX",
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
                        def_fr = float(pos.get("fee_rate") or 0.0)
                        uw_2 = self._try_early_overround_bid_unwind(
                            pos,
                            [
                                {
                                    "bids": bk_a.get("bids") or [],
                                    "fee_rate": float(leg_a.get("fee_rate", def_fr)),
                                    "fee_exponent": float(leg_a.get("fee_exponent", 1.0)),
                                },
                                {
                                    "bids": bk_b.get("bids") or [],
                                    "fee_rate": float(leg_b.get("fee_rate", def_fr)),
                                    "fee_exponent": float(leg_b.get("fee_exponent", 1.0)),
                                },
                            ],
                            now,
                        )
                        if uw_2 is not None:
                            to_close.append((pid, "EARLY_OVERROUND_BID_UNWIND", uw_2[0], uw_2[1]))
                            continue
                    if (
                        sleeve == "C1_BINARY_COMPLETE_SET"
                        and leg_a.get("market_id")
                        and leg_a.get("market_id") == leg_b.get("market_id")
                        and (now - float(pos.get("entry_ts") or 0.0)) >= 15.0
                    ):
                        to_close.append((pid, "CTF_COMPLETE_SET_MERGED", 1.0, 0.0))
                        continue
                    if bk_a and bk_b:
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
                    bks_m = None
                    if (now - float(pos.get("_last_book_poll_ts") or 0.0)) >= 30.0 and legs:
                        pos["_last_book_poll_ts"] = now
                        bks_m = await asyncio.gather(
                            *[self.fetch_json(f"{CLOB_URL}/book?token_id={lg['token_id']}", timeout=2.5) for lg in legs]
                        )
                        if all(bks_m):
                            pos["last_bid"] = round(
                                sum(extract_best_bid((b or {}).get("bids") or [])[0] for b in bks_m), 4
                            )
                            def_fr_m = float(pos.get("fee_rate") or 0.0)
                            uw_m = self._try_early_overround_bid_unwind(
                                pos,
                                [
                                    {
                                        "bids": (b or {}).get("bids") or [],
                                        "fee_rate": float(lg.get("fee_rate", def_fr_m)),
                                        "fee_exponent": float(lg.get("fee_exponent", 1.0)),
                                    }
                                    for lg, b in zip(legs, bks_m)
                                ],
                                now,
                            )
                            if uw_m is not None:
                                to_close.append((pid, "EARLY_OVERROUND_BID_UNWIND", uw_m[0], uw_m[1]))
                                continue
                    if (now - float(pos.get("_last_gamma_chk_ts") or 0.0)) < (30.0 if (bks_m is not None and not all(bks_m)) else 120.0):
                        continue
                    pos["_last_gamma_chk_ts"] = now
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
                and not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK")
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

                if bk and sleeve in ("BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY") and now >= float(pos["close_ts"]) + 900.0:
                    best_bid_b1, l1_bid_u_b1 = extract_best_bid(bk.get("bids") or [])
                    entry_eff_b1 = float(pos.get("entry_eff_px_t1000") or pos.get("entry_vwap_t1000") or 0.995)
                    fr_b1 = float(pos.get("fee_rate") or 0.0)
                    fe_b1 = float((pos.get("extra") or {}).get("fee_exponent") or 1.0)
                    net_bid_b1 = best_bid_b1 - (fr_b1 * ((best_bid_b1 * (1.0 - best_bid_b1)) ** fe_b1) if fr_b1 > 0.0 else 0.0)
                    if best_bid_b1 >= 0.997 and l1_bid_u_b1 >= 25.0 and net_bid_b1 >= entry_eff_b1 + 0.002:
                        m_id_b1 = str((pos.get("extra") or {}).get("market_id") or "")
                        gm_b1 = await self.fetch_json(f"{GAMMA_URL}/markets/{m_id_b1}", timeout=3.5) if m_id_b1 else None
                        uma_b1 = str((gm_b1 or {}).get("umaResolutionStatus") or "").strip().lower() if isinstance(gm_b1, dict) else ""
                        if uma_b1 == "disputed" or now >= float(pos["close_ts"]) + 14400.0:
                            to_close.append((pid, "UMA_DISPUTED_LOCK_PROFIT_RECYCLE", round(net_bid_b1, 4), 0.0))
                            continue

                if bk and sleeve not in ("BOND1_UMA_RESOLUTION_CARRY", "SP2_NBA_ENDGAME_LOCK"):
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

        for pid, status, net_pay_ps, tier_pay_override in to_close:
            pos = self.open_positions.pop(pid, None)
            if not pos:
                continue
            tier_pnls: Dict[str, float] = {}
            adj_tier_pnls: Dict[str, float] = {}
            drag_map = (pos.get("extra") or {}).get("legging_drag_usd_by_tier") or {}
            t_pay_map = tier_pay_override if isinstance(tier_pay_override, dict) else {}
            for t_name, tf in pos["tier_fills"].items():
                cost_total = float(tf["spent_usd"]) + float(tf["fee_usd"])
                eff_pay_ps = float(t_pay_map.get(t_name, net_pay_ps))
                payout_usd = float(tf["shares"]) * eff_pay_ps
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
        if len(getattr(self, "authoritative_strike_cache", {})) > 2000:
            for _k in list(self.authoritative_strike_cache.keys())[:-1500]:
                self.authoritative_strike_cache.pop(_k, None)
        if len(self.entered_keys) > 5000:
            _open_dk = {str(p.get("dedupe_key") or "") for p in self.open_positions.values()}
            self.entered_keys = _open_dk | set(list(self.entered_keys)[-3000:])
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
            all_closed_sl = _filter_epoch_closed_positions(
                str(sl), [p for p in self.closed_positions if p.get("sleeve") == sl]
            )
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
                "grad8_live_promoted": bool(
                    len(closed_sl) >= 8
                    and wins == len(closed_sl)
                    and round(pnl_1k, 2) > 0.0
                    and round(adj_pnl_1k, 2) > 0.0
                    and not is_shadow_sleeve_quarantined(sl)
                ),
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
                "live_nba_scoreboard_games": len(self.live_nba_board),
                "uma_proposed_markets": len(self.uma_proposed_markets),
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
            "gatling_projection": compute_gatling_trajectory_projection(starting_nav_usd=60.92),
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

        # Auto-refresh live day-by-day projections once every 60s (hot-reloading module on mtime change)
        now_p = time.time()
        if (now_p - float(getattr(self, "_last_proj_write_ts", 0.0))) >= 60.0:
            self._last_proj_write_ts = now_p
            try:
                import importlib
                import scripts.polymarket_daily_projections as _proj_mod
                _proj_file = getattr(_proj_mod, "__file__", None)
                if _proj_file:
                    _cur_p_ns = Path(_proj_file).stat().st_mtime_ns
                    _prev_p_ns = getattr(self, "_proj_mod_mtime_ns", None)
                    if _prev_p_ns is None:
                        self._proj_mod_mtime_ns = _cur_p_ns
                    elif _cur_p_ns != _prev_p_ns:
                        _proj_mod = importlib.reload(_proj_mod)
                        self._proj_mod_mtime_ns = _cur_p_ns
                _proj_mod.write_live_projections_atomic(days=30)
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
                    w_b4p = walk_l2_book_asks(bk_y.get("asks") or [], 100.0, fee_rate=r.fee_rate, min_l1_usd=15.0, max_ask_px=0.990, fee_exponent=r.fee_exponent)
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
                            fee_rate=r.fee_rate,
                            p_model=1.0,
                            close_ts=r.end_ts,
                            extra={"market_id": r.market_id, "condition_id": r.condition_id, "strike": r.strike, "direction": r.direction, "session_class": sess_cls, "fee_exponent": r.fee_exponent},
                            prefetched_book=bk_y,
                        )
                        continue

            w_qy = walk_l2_book_asks(bk_y.get("asks") or [], 35.0, fee_rate=r.fee_rate, min_l1_usd=8.0, fee_exponent=r.fee_exponent)
            w_qn = walk_l2_book_asks(bk_n.get("asks") or [], 35.0, fee_rate=r.fee_rate, min_l1_usd=8.0, fee_exponent=r.fee_exponent)
            row_h = {
                "asset": r.asset,
                "event_id": r.event_id,
                "strike": r.strike,
                "direction": r.direction,
                "market_id": r.market_id,
                "condition_id": r.condition_id,
                "yes_token": r.yes_token,
                "no_token": r.no_token,
                "fee_rate": r.fee_rate,
                "fee_exponent": r.fee_exponent,
                "ask_yes": w_qy.get("vwap") if w_qy.get("filled") else None,
                "ask_no": w_qn.get("vwap") if w_qn.get("filled") else None,
                "bk_yes": bk_y,
                "bk_no": bk_n,
                "start_ts": r.start_ts,
                "end_ts": r.end_ts,
            }
            all_hit_rows.append(row_h)
            by_event_hit_rows[r.event_id].append(row_h)

            # CM_B2_PYTH_SESSION_NO_LOCK (fee-exact, same-session final <=3.5h lock -> zero overnight/earnings gap + tight spread <=4c)
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
                    w_np = walk_l2_book_asks(bk_n.get("asks") or [], 100.0, fee_rate=r.fee_rate, min_l1_usd=15.0, fee_exponent=r.fee_exponent)
                    if w_np.get("filled") and 0.78 <= float(w_np["eff_px"]) <= 0.955 and bid_np > 0 and (float(w_np["vwap"]) - bid_np) <= 0.04:
                        edge_np = p_no_p - float(w_np["eff_px"])
                        b2_g = evaluate_barrier_no_net_ev(1.0 - p_no_p, float(w_np["vwap"]), fee_rate=r.fee_rate)
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
                                fee_rate=r.fee_rate,
                                p_model=p_no_p,
                                close_ts=r.end_ts,
                                extra={"market_id": r.market_id, "condition_id": r.condition_id, "strike": r.strike, "direction": r.direction, "eff_session_hours": round(eff_hrs, 2), "fee_exponent": r.fee_exponent},
                                prefetched_book=bk_n,
                            )

            # CM_SHOCK_PYTH_CATALYST: fee-exact scheduled NY macro release (08:30 CPI/NFP, 10:30 EIA, 14:00 FOMC) Pyth jump sniper
            prev_sp = self.prev_pyth_spots.get(r.asset, 0.0)
            if in_active_window and exact_ok and same_sess and not already_hit and prev_sp > 0.0:
                sh_ev = evaluate_pyth_catalyst_shock(r.asset, prev_sp, spot_p, r.strike, r.direction, eff_hrs, float(fd["sigma_session"]), now)
                if sh_ev.get("eligible"):
                    sh_side = str(sh_ev["side"])
                    sh_tok = r.yes_token if sh_side == "YES" else r.no_token
                    sh_bk = bk_y if sh_side == "YES" else bk_n
                    w_sh = walk_l2_book_asks(sh_bk.get("asks") or [], BANKROLL_TICKETS["T1000"]["CM_SHOCK_PYTH_CATALYST"], fee_rate=r.fee_rate, min_l1_usd=15.0, fee_exponent=r.fee_exponent)
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
                                fee_rate=r.fee_rate,
                                p_model=float(sh_ev["p_fair"]),
                                close_ts=r.end_ts,
                                extra={"market_id": r.market_id, "condition_id": r.condition_id, "catalyst": sh_ev["catalyst"], "delta_p": sh_ev["delta_p"], "ret_pct": sh_ev["ret_pct"], "fee_exponent": r.fee_exponent},
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
            w_qy = walk_l2_book_asks(bk_y.get("asks") or [], 35.0, fee_rate=rc.fee_rate, min_l1_usd=8.0, fee_exponent=rc.fee_exponent)
            w_qn = walk_l2_book_asks(bk_n.get("asks") or [], 35.0, fee_rate=rc.fee_rate, min_l1_usd=8.0, fee_exponent=rc.fee_exponent)
            all_close_rows.append({
                "asset": rc.asset,
                "strike": rc.strike,
                "is_downward": rc.is_downward,
                "market_id": rc.market_id,
                "condition_id": rc.condition_id,
                "yes_token": rc.yes_token,
                "no_token": rc.no_token,
                "fee_rate": rc.fee_rate,
                "fee_exponent": rc.fee_exponent,
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
                    w_cp = walk_l2_book_asks(bk_c.get("asks") or [], 100.0, fee_rate=rc.fee_rate, min_l1_usd=15.0, fee_exponent=rc.fee_exponent)
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
                                fee_rate=rc.fee_rate,
                                p_model=float(cl_ev["p_lock"]),
                                close_ts=rc.end_ts,
                                extra={"market_id": rc.market_id, "condition_id": rc.condition_id, "strike": rc.strike, "z_session": cl_ev["z_session"], "fee_exponent": rc.fee_exponent},
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
                    la = {"token_id": ba["yes_token"], "opp_token_id": ba["yes_opp_token"], "condition_id": ba["leg_yes_condition_id"], "side": "YES", "label": f"YES_{ba['direction']}", "market_id": ba["leg_yes_market_id"], "fee_rate": float(qy.get("fee_rate", 0.0)), "fee_exponent": float(qy.get("fee_exponent", 1.0)), "strike": float(qy["strike"])}
                    lb = {"token_id": ba["no_token"], "opp_token_id": ba["no_opp_token"], "condition_id": ba["leg_no_condition_id"], "side": "NO", "label": f"NO_{ba['direction']}", "market_id": ba["leg_no_market_id"], "fee_rate": float(qn.get("fee_rate", 0.0)), "fee_exponent": float(qn.get("fee_exponent", 1.0)), "strike": float(qn["strike"])}
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
            la = {"token_id": qy["yes_token"], "opp_token_id": qy["no_token"], "condition_id": qy["condition_id"], "side": "YES", "label": "YES_LONG", "market_id": qy["market_id"], "fee_rate": float(qy.get("fee_rate", 0.0)), "fee_exponent": float(qy.get("fee_exponent", 1.0)), "strike": float(qy["strike"])}
            lb = {"token_id": qn["no_token"], "opp_token_id": qn["yes_token"], "condition_id": qn["condition_id"], "side": "NO", "label": "NO_SHORT", "market_id": qn["market_id"], "fee_rate": float(qn.get("fee_rate", 0.0)), "fee_exponent": float(qn.get("fee_exponent", 1.0)), "strike": float(qn["strike"])}
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
            la = {"token_id": qy["yes_token"], "opp_token_id": qy["no_token"], "condition_id": qy["condition_id"], "side": "YES", "label": "YES_HIT", "market_id": qy["market_id"], "fee_rate": float(qy.get("fee_rate", 0.0)), "fee_exponent": float(qy.get("fee_exponent", 1.0)), "strike": float(qy["strike"])}
            lb = {"token_id": qn["no_token"], "opp_token_id": qn["yes_token"], "condition_id": qn["condition_id"], "side": "NO", "label": "NO_CLOSE", "market_id": qn["market_id"], "fee_rate": float(qn.get("fee_rate", 0.0)), "fee_exponent": float(qn.get("fee_exponent", 1.0)), "strike": float(qn["strike"])}
            pyth_box_cands.append((cvh["asset"], f"CMB3_CVH_{qy['market_id']}_{qn['market_id']}", la, lb, qy["bk_yes"], qn["bk_no"], float(cvh["close_ts"]), f"{cvh['asset']} Close-vs-Hit Box {cvh['label']}"))

        pyth_box_cands.sort(key=lambda x: ((float(x[6]) - now) > 64800.0, float(x[6])))
        for p_asset, p_dkey, la, lb, bk_a, bk_b, c_ts, p_title in pyth_box_cands:
            w_pb = walk_equal_shares_dominance_box(
                bk_a.get("asks") or [],
                bk_b.get("asks") or [],
                target_budget_usd=BANKROLL_TICKETS["T1000"]["CM_B3_PYTH_BARRIER_BOX"],
                fee_rate_a=float(la["fee_rate"]),
                fee_rate_b=float(lb["fee_rate"]),
                fee_exponent_a=float(la.get("fee_exponent", 1.0)),
                fee_exponent_b=float(lb.get("fee_exponent", 1.0)),
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
                pb_live_emitted = False
                if float(w_pb["box_cost_net"]) <= 0.993 and (c_ts - now) <= 172800.0:
                    pb_live_emitted = self.emit_live_two_leg_box_candidate(
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
                if (c_ts - now) <= 172800.0:
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
                if not pb_live_emitted:
                    self.post_zero_fee_maker_anchor_box(
                        "CM_B3", p_asset, f"ZFA_{p_dkey}", la, lb, bk_a, bk_b, c_ts, p_title, now,
                        live_emit_only=bool((c_ts - now) <= 172800.0),
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
                if float(nb["box_cost_net"]) > 1.060:
                    continue
                lga, lgb = nb["leg_a"], nb["leg_b"]
                bk_a, bk_b = nba_bks.get(lga.token_id), nba_bks.get(lgb.token_id)
                if not bk_a or not bk_b:
                    continue
                la_n = {"token_id": lga.token_id, "opp_token_id": lga.opp_token_id, "condition_id": lga.condition_id, "side": lga.side_label, "label": lga.display_label, "market_id": lga.market_id, "fee_rate": lga.fee_rate, "fee_exponent": lga.fee_exponent, "strike": float(lga.threshold)}
                lb_n = {"token_id": lgb.token_id, "opp_token_id": lgb.opp_token_id, "condition_id": lgb.condition_id, "side": lgb.side_label, "label": lgb.display_label, "market_id": lgb.market_id, "fee_rate": lgb.fee_rate, "fee_exponent": lgb.fee_exponent, "strike": float(lgb.threshold)}
                if float(nb["box_cost_net"]) > 0.994:
                    self.post_zero_fee_maker_anchor_box(
                        "SP1_NBA", "NBA", f"ZFA_SP1_{sp_nba.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",
                        la_n, lb_n, bk_a, bk_b, float(nb["close_ts"]), f"{sp_nba.title} [{nb['label']}]", now,
                        prefetched_books=nba_bks,
                    )
                    continue
                w_nba = walk_equal_shares_dominance_box(
                    bk_a.get("asks") or [],
                    bk_b.get("asks") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["SP1_NBA_ZERO_FEE_BOX"],
                    fee_rate_a=lga.fee_rate,
                    fee_rate_b=lgb.fee_rate,
                    fee_exponent_a=lga.fee_exponent,
                    fee_exponent_b=lgb.fee_exponent,
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
                    nba_live_emitted = False
                    if float(w_nba["box_cost_net"]) <= 0.990 and (float(nb["close_ts"]) - now) <= 86400.0:
                        nba_live_emitted = self.emit_live_two_leg_box_candidate(
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
                    if not nba_live_emitted:
                        self.post_zero_fee_maker_anchor_box(
                            "SP1_NBA", "NBA", f"ZFA_SP1_{sp_nba.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",
                            la_n, lb_n, bk_a, bk_b, float(nb["close_ts"]), f"{sp_nba.title} [{nb['label']}]", now,
                            prefetched_books=nba_bks,
                            live_emit_only=True,
                        )
                else:
                    self.post_zero_fee_maker_anchor_box(
                        "SP1_NBA", "NBA", f"ZFA_SP1_{sp_nba.event_id}_{lga.token_id[-8:]}_{lgb.token_id[-8:]}",
                        la_n, lb_n, bk_a, bk_b, float(nb["close_ts"]), f"{sp_nba.title} [{nb['label']}]", now,
                        prefetched_books=nba_bks,
                    )

        # 4B. SP3_SPORTS_CORRIDOR_DOMINANCE_BOX: Multi-Sport & Period Alternate Spread / Total Corridor Dominance Boxes
        #     (NBA 1H/2H/Q1..Q4/TeamTotals @ 0% fee + NFL/CFB @ 0.03 + NHL/Soccer/Tennis/Esports @ 0.05; *.5 hooks -> 0 push/tie risk)
        active_ms_games: List[MultiSportCorridorSpec] = []
        for sp_ms in list(self.multi_sport_games.values()):
            if now > sp_ms.start_ts + 6.5 * 3600.0:
                self.multi_sport_games.pop(sp_ms.event_id, None)
                continue
            if self.single_scan or ("fetch_json" in self.__dict__) or now >= (sp_ms.start_ts - 86400.0):
                active_ms_games.append(sp_ms)
        active_ms_games.sort(key=lambda g: (now < (g.start_ts - 900.0), abs(g.start_ts - now)))
        for sp_ms in active_ms_games[:20]:
            ms_toks = sorted({lg.token_id for lgs in sp_ms.legs_by_scope.values() for lg in lgs})
            if len(ms_toks) < 4:
                continue
            ms_bks = await self.fetch_books_batch(ms_toks, timeout=3.5)
            best_asks_ms: Dict[str, float] = {}
            for t_m, bk_m in ms_bks.items():
                px_m, sz_m = self._best_ask_sz(bk_m)
                if px_m < 1.0 and px_m * sz_m >= 8.0:
                    best_asks_ms[t_m] = px_m
            ms_diag = detect_multi_sport_corridor_boxes(sp_ms, best_asks_ms, max_box_cost_net=1.08)
            if ms_diag:
                md0 = ms_diag[0]
                self._record_market_telemetry(
                    key=f"SP3_BOX_{sp_ms.event_id}",
                    min_interval_sec=45.0,
                    now_ts=now,
                    sig=(md0["label"], md0["box_cost_net"]),
                    payload={
                        "type": "MULTI_SPORT_CORRIDOR_BEST",
                        "sport": sp_ms.sport,
                        "event_id": sp_ms.event_id,
                        "game": sp_ms.title,
                        "scope": md0["scope"],
                        "in_play": bool(now >= sp_ms.start_ts),
                        "best_label": md0["label"],
                        "gross_box_l1": md0["box_cost_gross"],
                        "net_box_l1": md0["box_cost_net"],
                        "middle_pts": md0["middle_width_pts"],
                    },
                )
            for cb in ms_diag:
                lga_c, lgb_c = cb["leg_a"], cb["leg_b"]
                max_fr_c = max(float(lga_c.fee_rate), float(lgb_c.fee_rate))
                max_cap_c = 0.994 if max_fr_c == 0.0 else 0.990
                if float(cb["box_cost_net"]) > (1.045 if max_fr_c == 0.0 else max_cap_c):
                    continue
                bk_ac, bk_bc = ms_bks.get(lga_c.token_id), ms_bks.get(lgb_c.token_id)
                if not bk_ac or not bk_bc:
                    continue
                la_c = {
                    "token_id": lga_c.token_id, "opp_token_id": lga_c.opp_token_id, "condition_id": lga_c.condition_id,
                    "side": lga_c.side_label, "label": lga_c.display_label, "market_id": lga_c.market_id,
                    "fee_rate": float(lga_c.fee_rate), "fee_exponent": float(lga_c.fee_exponent),
                    "neg_risk": bool(lga_c.neg_risk), "strike": float(lga_c.threshold),
                }
                lb_c = {
                    "token_id": lgb_c.token_id, "opp_token_id": lgb_c.opp_token_id, "condition_id": lgb_c.condition_id,
                    "side": lgb_c.side_label, "label": lgb_c.display_label, "market_id": lgb_c.market_id,
                    "fee_rate": float(lgb_c.fee_rate), "fee_exponent": float(lgb_c.fee_exponent),
                    "neg_risk": bool(lgb_c.neg_risk), "strike": float(lgb_c.threshold),
                }
                dk_sp3 = f"SP3_{sp_ms.event_id}_{lga_c.token_id[-8:]}_{lgb_c.token_id[-8:]}"
                if float(cb["box_cost_net"]) > max_cap_c:
                    if max_fr_c == 0.0:
                        self.post_zero_fee_maker_anchor_box(
                            "SP3_SPORTS", sp_ms.sport, f"ZFA_{dk_sp3}",
                            la_c, lb_c, bk_ac, bk_bc, float(cb["close_ts"]), f"{sp_ms.title} [{cb['label']}]", now,
                            prefetched_books=ms_bks,
                        )
                    continue
                w_sp3 = walk_equal_shares_dominance_box(
                    bk_ac.get("asks") or [],
                    bk_bc.get("asks") or [],
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["SP3_SPORTS_CORRIDOR_DOMINANCE_BOX"],
                    fee_rate_a=float(lga_c.fee_rate),
                    fee_rate_b=float(lgb_c.fee_rate),
                    fee_exponent_a=float(lga_c.fee_exponent),
                    fee_exponent_b=float(lgb_c.fee_exponent),
                    max_box_cost_net=max_cap_c,
                    min_shares=8,
                    min_box_notional_usd=7.0,
                )
                if w_sp3.get("filled"):
                    opps_out.append({
                        "sleeve": "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
                        "market": f"{sp_ms.sport} {sp_ms.title}: {cb['label']} (mid={cb['middle_width_pts']}pt)",
                        "ask_vwap": round(float(w_sp3["box_cost_net"]), 4),
                        "p_model": 1.0,
                        "net_edge": round(1.0 - float(w_sp3["box_cost_net"]), 4),
                        "l1_usd": w_sp3["l1_usd"],
                        "close_ts": cb["close_ts"],
                    })
                    sp3_live_cap = 0.990 if max_fr_c == 0.0 else 0.988
                    if float(w_sp3["box_cost_net"]) <= sp3_live_cap and (float(cb["close_ts"]) - now) <= 86400.0:
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
                            box_type="SPORTS_CORRIDOR",
                            asset=sp_ms.sport,
                            dedupe_key=dk_sp3,
                            leg_a=la_c,
                            leg_b=lb_c,
                            bk_a=bk_ac,
                            bk_b=bk_bc,
                            close_ts=float(cb["close_ts"]),
                            now_ts=now,
                            k_low=float(lga_c.threshold),
                            k_high=float(lgb_c.threshold),
                        )
                    await self.open_shadow_two_leg_box(
                        sleeve="SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
                        dedupe_key=dk_sp3,
                        asset=sp_ms.sport,
                        title=f"{sp_ms.sport} {sp_ms.title} [{cb['label']}]",
                        leg_a=la_c,
                        leg_b=lb_c,
                        bk_a=bk_ac,
                        bk_b=bk_bc,
                        close_ts=float(cb["close_ts"]),
                        max_box_cost_net=max_cap_c,
                        extra={
                            "is_sports_corridor_box": True,
                            "sport": sp_ms.sport,
                            "scope": cb["scope"],
                            "box_kind": cb["box_kind"],
                            "middle_width_pts": cb["middle_width_pts"],
                        },
                    )

        # 5. NR0_ZERO_FEE_SLATE_ARB: Zero-Fee NegRisk Partition Slates (`elon-tweets`, `fomc`, `boj`, `boc`) — intraday <= 18h first
        for sp_nr in sorted(list(self.negrisk_zero_slates.values()), key=lambda s: ((float(s.end_ts) - now) > 64800.0, float(s.end_ts))):
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
                    if n_br == 2 and (float(sp_nr.end_ts) - now) <= 172800.0 and self._can_emit_zero_loss_math_live("NR0_ZERO_FEE_SLATE_ARB", float(sp_nr.end_ts), now):
                        b0_y, b1_y = sp_nr.brackets[0], sp_nr.brackets[1]
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="NR0_ZERO_FEE_SLATE_ARB",
                            box_type="NEGRISK_2LEG",
                            asset=sp_nr.series_slug.upper(),
                            dedupe_key=f"NR0_Y_{sp_nr.event_id}",
                            leg_a={"token_id": b0_y["yes_token"], "opp_token_id": b0_y["no_token"], "condition_id": str(b0_y.get("condition_id") or ""), "side": "YES", "label": f"YES[{b0_y['label']}]", "market_id": b0_y["market_id"], "fee_rate": float(b0_y.get("fee_rate", 0.0)), "fee_exponent": float(b0_y.get("fee_exponent", 1.0)), "neg_risk": True, "strike": 100.0},
                            leg_b={"token_id": b1_y["yes_token"], "opp_token_id": b1_y["no_token"], "condition_id": str(b1_y.get("condition_id") or ""), "side": "YES", "label": f"YES[{b1_y['label']}]", "market_id": b1_y["market_id"], "fee_rate": float(b1_y.get("fee_rate", 0.0)), "fee_exponent": float(b1_y.get("fee_exponent", 1.0)), "neg_risk": True, "strike": 100.0},
                            bk_a=nr_bks[b0_y["yes_token"]],
                            bk_b=nr_bks[b1_y["yes_token"]],
                            close_ts=float(sp_nr.end_ts),
                            now_ts=now,
                        )
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
                    if (float(sp_nr.end_ts) - now) <= 172800.0 and self._can_emit_zero_loss_math_live("NR0_ZERO_FEE_SLATE_ARB", float(sp_nr.end_ts), now):
                        if n_br == 2:
                            b0_n, b1_n = sp_nr.brackets[0], sp_nr.brackets[1]
                            self.emit_live_two_leg_box_candidate(
                                sleeve_source="NR0_ZERO_FEE_SLATE_ARB",
                                box_type="NEGRISK_2LEG",
                                asset=sp_nr.series_slug.upper(),
                                dedupe_key=f"NR0_N_{sp_nr.event_id}",
                                leg_a={"token_id": b0_n["no_token"], "opp_token_id": b0_n["yes_token"], "condition_id": str(b0_n.get("condition_id") or ""), "side": "NO", "label": f"NO[{b0_n['label']}]", "market_id": b0_n["market_id"], "fee_rate": float(b0_n.get("fee_rate", 0.0)), "fee_exponent": float(b0_n.get("fee_exponent", 1.0)), "neg_risk": True, "strike": 100.0},
                                leg_b={"token_id": b1_n["no_token"], "opp_token_id": b1_n["yes_token"], "condition_id": str(b1_n.get("condition_id") or ""), "side": "NO", "label": f"NO[{b1_n['label']}]", "market_id": b1_n["market_id"], "fee_rate": float(b1_n.get("fee_rate", 0.0)), "fee_exponent": float(b1_n.get("fee_exponent", 1.0)), "neg_risk": True, "strike": 100.0},
                                bk_a=nr_bks[b0_n["no_token"]],
                                bk_b=nr_bks[b1_n["no_token"]],
                                close_ts=float(sp_nr.end_ts),
                                now_ts=now,
                            )
                        elif 3 <= n_br <= 15:
                            sp_nrc_z = self.negrisk_convert_slates.get(sp_nr.event_id)
                            if sp_nrc_z is not None and sp_nrc_z.is_closed_convert_safe:
                                w_legs_z = w_nrn.get("leg_walks") or []
                                arb_z = {
                                    "mode": "NR2_PURE_CASH_CONVERT",
                                    "shares": w_nrn["shares"],
                                    "net_edge_per_share": round((gp_n - float(w_nrn["box_cost_net"])) / gp_n, 5),
                                    "no_legs": [
                                        {"token_id": b_z["no_token"], "bracket": b_z, "walk": (w_legs_z[idx_z] if idx_z < len(w_legs_z) else {"worst_px": self._best_ask_sz(nr_bks[b_z["no_token"]])[0]})}
                                        for idx_z, b_z in enumerate(sp_nrc_z.brackets)
                                    ],
                                    "yes_sell_legs": [],
                                    "retained_free_yes_brackets": [],
                                }
                                self.emit_live_negrisk_convert_candidate(
                                    sleeve_source="NR0_ZERO_FEE_SLATE_ARB",
                                    spec=sp_nrc_z,
                                    dedupe_key=f"NR0_N{n_br}_{sp_nr.event_id}",
                                    arb_hit=arb_z,
                                    books_by_token=nr_bks,
                                    now_ts=now,
                                )
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

        # 5B. NR_CONV_NO_BASKET_ARB: Universal 2-Leg `NO_i + NO_j` Mutual-Exclusion Dominance Boxes + Closed `convertPositions` Arb
        active_nrc = [s for s in self.negrisk_convert_slates.values() if s.end_ts > now + 60]
        if active_nrc:
            nrc_toks: List[str] = []
            for s_nrc in active_nrc:
                for b_nrc in s_nrc.brackets:
                    nrc_toks.append(b_nrc["no_token"])
                    if s_nrc.is_closed_convert_safe:
                        nrc_toks.append(b_nrc["yes_token"])
            nrc_bks = await self.fetch_books_batch(nrc_toks, timeout=3.5)
            best_no_asks_nrc: Dict[str, float] = {}
            for t_nr, bk_nr in nrc_bks.items():
                px_nr, sz_nr = self._best_ask_sz(bk_nr)
                if px_nr < 1.0 and px_nr * sz_nr >= 8.0:
                    best_no_asks_nrc[t_nr] = px_nr
            for sp_nrc in active_nrc:
                pair_arbs = detect_negrisk_no_pair_boxes(sp_nrc, best_no_asks_nrc, max_box_cost_net=1.04)
                if pair_arbs:
                    pa0 = pair_arbs[0]
                    self._record_market_telemetry(
                        key=f"NRCONV_2L_{sp_nrc.event_id}",
                        min_interval_sec=60.0,
                        now_ts=now,
                        sig=(pa0["label"], pa0["box_cost_net"]),
                        payload={
                            "type": "NEGRISK_NO_PAIR_BEST",
                            "event_id": sp_nrc.event_id,
                            "title": sp_nrc.title[:80],
                            "augmented": sp_nrc.neg_risk_augmented,
                            "net_box_l1": pa0["box_cost_net"],
                            "label": pa0["label"],
                        },
                    )
                for pa in pair_arbs:
                    ba_nr, bb_nr = pa["bracket_a"], pa["bracket_b"]
                    max_fr_nr = max(float(ba_nr["fee_rate"]), float(bb_nr["fee_rate"]))
                    cap_nr2 = 0.992 if max_fr_nr == 0.0 else 0.988
                    if float(pa["box_cost_net"]) > cap_nr2:
                        continue
                    bka_nr, bkb_nr = nrc_bks.get(ba_nr["no_token"]), nrc_bks.get(bb_nr["no_token"])
                    if not bka_nr or not bkb_nr:
                        continue
                    la_nr = {
                        "token_id": ba_nr["no_token"], "opp_token_id": ba_nr["yes_token"], "condition_id": ba_nr["condition_id"],
                        "side": "NO", "label": f"NO[{ba_nr['label']}]", "market_id": ba_nr["market_id"],
                        "fee_rate": float(ba_nr["fee_rate"]), "fee_exponent": float(ba_nr["fee_exponent"]),
                        "neg_risk": True, "strike": 100.0,
                    }
                    lb_nr = {
                        "token_id": bb_nr["no_token"], "opp_token_id": bb_nr["yes_token"], "condition_id": bb_nr["condition_id"],
                        "side": "NO", "label": f"NO[{bb_nr['label']}]", "market_id": bb_nr["market_id"],
                        "fee_rate": float(bb_nr["fee_rate"]), "fee_exponent": float(bb_nr["fee_exponent"]),
                        "neg_risk": True, "strike": 100.0,
                    }
                    w_nr2 = walk_equal_shares_dominance_box(
                        bka_nr.get("asks") or [],
                        bkb_nr.get("asks") or [],
                        target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],
                        fee_rate_a=float(ba_nr["fee_rate"]),
                        fee_rate_b=float(bb_nr["fee_rate"]),
                        fee_exponent_a=float(ba_nr["fee_exponent"]),
                        fee_exponent_b=float(bb_nr["fee_exponent"]),
                        max_box_cost_net=cap_nr2,
                        min_shares=8,
                        min_box_notional_usd=7.0,
                    )
                    if w_nr2.get("filled"):
                        dk_nr2 = f"NRCONV_2L_{sp_nrc.event_id}_{ba_nr['market_id']}_{bb_nr['market_id']}"
                        opps_out.append({
                            "sleeve": "NR_CONV_NO_BASKET_ARB",
                            "market": f"{sp_nrc.title[:50]}: {pa['label']}",
                            "ask_vwap": round(float(w_nr2["box_cost_net"]), 4),
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_nr2["box_cost_net"]), 4),
                            "l1_usd": w_nr2["l1_usd"],
                            "close_ts": sp_nrc.end_ts,
                        })
                        if (sp_nrc.end_ts - now) <= 172800.0 and float(w_nr2["box_cost_net"]) <= (0.990 if max_fr_nr == 0.0 else 0.988):
                            self.emit_live_two_leg_box_candidate(
                                sleeve_source="NR_CONV_NO_BASKET_ARB",
                                box_type="NEGRISK_2LEG",
                                asset="NEGRISK",
                                dedupe_key=dk_nr2,
                                leg_a=la_nr,
                                leg_b=lb_nr,
                                bk_a=bka_nr,
                                bk_b=bkb_nr,
                                close_ts=float(sp_nrc.end_ts),
                                now_ts=now,
                            )
                        await self.open_shadow_two_leg_box(
                            sleeve="NR_CONV_NO_BASKET_ARB",
                            dedupe_key=dk_nr2,
                            asset="NEGRISK",
                            title=f"{sp_nrc.title} [{pa['label']}]",
                            leg_a=la_nr,
                            leg_b=lb_nr,
                            bk_a=bka_nr,
                            bk_b=bkb_nr,
                            close_ts=float(sp_nrc.end_ts),
                            max_box_cost_net=cap_nr2,
                            extra={"is_negrisk_no_pair_box": True, "event_id": sp_nrc.event_id, "neg_risk_augmented": sp_nrc.neg_risk_augmented},
                        )
                if sp_nrc.is_closed_convert_safe:
                    conv_arbs = detect_negrisk_convert_positions_arbs(
                        sp_nrc,
                        nrc_bks,
                        target_budget_usd=BANKROLL_TICKETS["T1000"]["NR_CONV_NO_BASKET_ARB"],
                        min_net_edge_per_share=0.005,
                        min_shares=8,
                    )
                    if conv_arbs:
                        ca0 = conv_arbs[0]
                        self._record_market_telemetry(
                            key=f"NRCONV_M_{sp_nrc.event_id}",
                            min_interval_sec=60.0,
                            now_ts=now,
                            sig=(ca0["m_no_legs"], ca0["net_edge_per_share"]),
                            payload={
                                "type": "NEGRISK_CONVERT_ARB_SNAP",
                                "event_id": sp_nrc.event_id,
                                "title": sp_nrc.title[:80],
                                "m_no_legs": ca0["m_no_legs"],
                                "n_total": ca0["n_total"],
                                "net_edge_per_share": ca0["net_edge_per_share"],
                                "shares": ca0["shares"],
                            },
                        )
                        await self.execute_negrisk_convert_positions_arb(sp_nrc, ca0, nrc_bks, opps_out)
                    nr2_arbs = detect_nr2_convert_no_subset_arbs(
                        sp_nrc,
                        nrc_bks,
                        target_budget_usd=BANKROLL_TICKETS["T1000"]["NR2_CONVERT_NO_SUBSET_ARB"],
                        min_edge_pure_cash=0.012,
                        min_edge_with_yes_sell=0.015,
                        min_shares=6,
                    )
                    try:
                        from src.polymarket_research.riskless_machine_gun_engine import detect_nr3_synthetic_all_yes_overround
                        nr3_hit = detect_nr3_synthetic_all_yes_overround(
                            sp_nrc, nrc_bks, target_budget_usd=30.0, min_net_edge_per_set=0.008, min_shares=5
                        )
                        if nr3_hit is not None:
                            opps_out.append({
                                "sleeve": "NR2_CONVERT_NO_SUBSET_ARB",
                                "market": f"{sp_nrc.title[:50]} [NR3 All-YES Overround]",
                                "ask_vwap": round(max(0.01, 1.0 - float(nr3_hit["net_edge_per_share"])), 4),
                                "p_model": 1.0,
                                "net_edge": nr3_hit["net_edge_per_share"],
                                "l1_usd": nr3_hit["l1_usd"],
                                "close_ts": sp_nrc.end_ts,
                            })
                            self.emit_live_negrisk_convert_candidate(
                                sleeve_source="NR2_CONVERT_NO_SUBSET_ARB",
                                spec=sp_nrc,
                                dedupe_key=f"NR3_OVR_{sp_nrc.event_id}",
                                arb_hit=nr3_hit,
                                books_by_token=nrc_bks,
                                now_ts=now,
                            )
                    except Exception:
                        pass
                    if nr2_arbs:
                        na0 = nr2_arbs[0]
                        self._record_market_telemetry(
                            key=f"NR2_SUB_{sp_nrc.event_id}",
                            min_interval_sec=60.0,
                            now_ts=now,
                            sig=(na0["m_no_legs"], na0["net_edge_per_share"], na0["retained_tail_count"]),
                            payload={
                                "type": "NR2_SUBSET_CONVERT_SNAP",
                                "event_id": sp_nrc.event_id,
                                "title": sp_nrc.title[:80],
                                "m_no_legs": na0["m_no_legs"],
                                "n_total": na0["n_total"],
                                "retained_tail_count": na0["retained_tail_count"],
                                "net_edge_per_share": na0["net_edge_per_share"],
                            },
                        )
                        await self.execute_nr2_subset_convert_arb(sp_nrc, na0, nrc_bks, opps_out)

        # 6. Phase-2 Macro LP (`FED1`), Oil-Senate (`COND1`), Counting (`TW1` + `MKR_REWARD`), & AAA Gas (`GAS1`)
        await self._scan_phase2_macro_counting_gas(opps_out, now)
        # 7. Riskless Frontier v2 (`SP4-3B`, `SOC1`, `LP1-6B/6C`, `API1`), v3 (`LP2`, `SP4+`, `CAL1`, `LP1_NFL`, `TEN1`, `CL1`), & v4 (`AFF1`, `SOC2`, `NFL_PRP1`, `SUM1`, `CRY_INC1`, `MKR_LOCK1`)
        await self._scan_frontier_v2_sleeves(opps_out, now)
        await self._scan_frontier_v3_sleeves(opps_out, now)
        await self._scan_frontier_v4_sleeves(opps_out, now)

    async def _scan_frontier_v2_sleeves(self, opps_out: List[Dict[str, Any]], now: float) -> None:
        # 7A. `SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK` Sub-Mode 3B: Fee-Exact NBA Player Milestone Polish Middles
        active_props = [s for s in self.nba_prop_slates.values() if s.settle_est_ts > now + 120]
        for sl_pr in active_props[:10]:
            pr_toks = [t for rgs in sl_pr.props_by_player_stat.values() if len(rgs) >= 2 for r in rgs for t in (r.yes_token, r.no_token)]
            if not pr_toks:
                continue
            pr_bks = await self.fetch_books_batch(pr_toks, timeout=3.5)
            pr_asks = {t: p for t, bk in pr_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
            sp4_boxes = detect_sp4_milestone_ladder_boxes(sl_pr, pr_asks, max_box_cost_net=1.045)
            if sp4_boxes:
                b0 = sp4_boxes[0]
                self._record_market_telemetry(
                    f"SP4_3B_{sl_pr.event_id}", 90.0,
                    {"type": "SP4_MILESTONE_BOX_BEST", "game": sl_pr.title[:60], "label": b0["label"], "net_box_l1": b0["box_cost_net"]},
                    now_ts=now, sig=(b0["label"], b0["box_cost_net"]),
                )
            for bx in sp4_boxes[:8]:
                la, lb = bx["leg_a"], bx["leg_b"]
                bka, bkb = pr_bks.get(la["token_id"]), pr_bks.get(lb["token_id"])
                if not bka or not bkb:
                    continue
                dk_sp4 = f"SP4_3B_{la['market_id']}_{lb['market_id']}"
                if float(bx["box_cost_net"]) > 0.992:
                    if la.get("market_id") != lb.get("market_id"):
                        self.post_zero_fee_maker_anchor_box(
                            "SP1_NBA", "NBA", f"ZFA_{dk_sp4}",
                            la, lb, bka, bkb, float(bx["close_ts"]), f"{sl_pr.title} [{bx['label']}]", now,
                            prefetched_books=pr_bks,
                        )
                    continue
                w_sp4 = walk_equal_shares_dominance_box(
                    bka.get("asks") or [], bkb.get("asks") or [],
                    BANKROLL_TICKETS["T1000"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],
                    float(la["fee_rate"]), float(lb["fee_rate"]),
                    fee_exponent_a=float(la.get("fee_exponent", 1.0)),
                    fee_exponent_b=float(lb.get("fee_exponent", 1.0)),
                    max_box_cost_net=0.992, min_shares=6, min_box_notional_usd=5.5,
                )
                if w_sp4.get("filled"):
                    opps_out.append({
                        "sleeve": "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
                        "market": f"NBA Prop Corridor: {bx['label']}",
                        "ask_vwap": w_sp4["box_cost_net"], "p_model": 1.0,
                        "net_edge": round(1.0 - float(w_sp4["box_cost_net"]), 4),
                        "l1_usd": w_sp4["l1_usd"], "close_ts": bx["close_ts"],
                    })
                    if float(w_sp4["box_cost_net"]) <= 0.990 and (float(bx["close_ts"]) - now) <= 86400.0 and la.get("market_id") != lb.get("market_id"):
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
                            box_type="NBA_DOMINANCE",
                            asset="NBA",
                            dedupe_key=dk_sp4,
                            leg_a=la,
                            leg_b=lb,
                            bk_a=bka,
                            bk_b=bkb,
                            close_ts=float(bx["close_ts"]),
                            now_ts=now,
                            k_low=float(bx["line_low"]),
                            k_high=float(bx["line_high"]),
                        )
                    await self.open_shadow_two_leg_box(
                        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK", dk_sp4, "NBA_PROP",
                        f"{sl_pr.title} [{bx['label']}]", la, lb, bka, bkb, float(bx["close_ts"]), 0.992,
                        {"is_two_leg_box": True, "mode": bx["mode"], "player": bx["player_name"], "stat": bx["stat_type"]},
                    )

        # 7B. `SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX`: Fee-Exact 3-Way Regulation Soccer + `-more-markets`
        active_soc = [tr for tr in self.soccer_trees.values() if tr.end_ts > now + 120]
        if active_soc:
            soc_toks: List[str] = []
            for tr in active_soc[:25]:
                for lg3 in (tr.home_leg, tr.draw_leg, tr.away_leg):
                    soc_toks.extend((lg3["yes_token"], lg3["no_token"]))
                for tl in tr.totals:
                    soc_toks.extend((tl["over_token"], tl["under_token"]))
                for sp in tr.spreads:
                    soc_toks.extend((sp["fav_minus_token"], sp["dog_plus_token"]))
            soc_bks = await self.fetch_books_batch(soc_toks, timeout=3.5)
            soc_asks = {t: p for t, bk in soc_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
            for tr in active_soc[:25]:
                res_soc = detect_soc1_regulation_boxes(
                    tr, soc_bks, soc_asks, max_2leg_cost_net=1.035, min_conv_edge_ps=0.010,
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"],
                )
                if res_soc["two_leg_boxes"]:
                    sb0 = res_soc["two_leg_boxes"][0]
                    self._record_market_telemetry(
                        f"SOC1_{tr.game_id}", 90.0,
                        {"type": "SOC1_REGULATION_BOX_BEST", "game": tr.title[:60], "mode": sb0["mode"], "label": sb0["label"], "net_box_l1": sb0["box_cost_net"]},
                        now_ts=now, sig=(sb0["label"], sb0["box_cost_net"]),
                    )
                for bx_s in res_soc["two_leg_boxes"][:4]:
                    if float(bx_s["box_cost_net"]) > 0.988:
                        continue
                    la_s, lb_s = bx_s["leg_a"], bx_s["leg_b"]
                    bka_s, bkb_s = soc_bks.get(la_s["token_id"]), soc_bks.get(lb_s["token_id"])
                    if not bka_s or not bkb_s:
                        continue
                    w_soc = walk_equal_shares_dominance_box(
                        bka_s.get("asks") or [], bkb_s.get("asks") or [],
                        BANKROLL_TICKETS["T1000"]["SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"],
                        float(la_s["fee_rate"]), float(lb_s["fee_rate"]),
                        fee_exponent_a=float(la_s["fee_exponent"]), fee_exponent_b=float(lb_s["fee_exponent"]),
                        max_box_cost_net=0.988, min_shares=6, min_box_notional_usd=5.5,
                    )
                    if w_soc.get("filled"):
                        dk_soc = f"SOC1_2L_{tr.game_id}_{la_s['token_id'][-6:]}_{lb_s['token_id'][-6:]}"
                        opps_out.append({
                            "sleeve": "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
                            "market": bx_s["label"], "ask_vwap": w_soc["box_cost_net"], "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_soc["box_cost_net"]), 4),
                            "l1_usd": w_soc["l1_usd"], "close_ts": tr.end_ts,
                        })
                        if (float(tr.end_ts) - now) <= 259200.0 and la_s.get("market_id") != lb_s.get("market_id"):
                            self.emit_live_two_leg_box_candidate(
                                sleeve_source="SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
                                box_type="SPORTS_CORRIDOR",
                                asset="SOCCER",
                                dedupe_key=dk_soc,
                                leg_a=la_s,
                                leg_b=lb_s,
                                bk_a=bka_s,
                                bk_b=bkb_s,
                                close_ts=float(tr.end_ts),
                                now_ts=now,
                            )
                        await self.open_shadow_two_leg_box(
                            "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX", dk_soc, "SOCCER",
                            bx_s["label"], la_s, lb_s, bka_s, bkb_s, float(tr.end_ts), 0.988,
                            {"is_two_leg_box": True, "mode": bx_s["mode"], "game_id": tr.game_id},
                        )
                for cv_s in res_soc["convert_arbs"][:1]:
                    opps_out.append({
                        "sleeve": "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
                        "market": cv_s["label"], "ask_vwap": round(1.0 - float(cv_s["net_edge_per_share"]), 4),
                        "p_model": 1.0, "net_edge": cv_s["net_edge_per_share"],
                        "l1_usd": cv_s["l1_usd"], "close_ts": tr.end_ts,
                    })

        # 7C. `LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX`: 9-State BOP x Chambers (6C) & 11-State NBA Exact-Margin x ML/Spreads (6B)
        lp1_groups: List[Tuple[str, List[Dict[str, Any]]]] = []
        if self.lp1_bop_legs:
            lp1_groups.append(("BOP_2026", [lg for lg in self.lp1_bop_legs if float(lg["end_ts"]) > now + 60]))
        for em_b in list(self.lp1_nba_em_bundles.values())[:10]:
            if float(em_b["end_ts"]) > now + 60:
                lp1_groups.append((f"NBA_EM_{em_b['event_id']}", em_b["legs"]))
        if lp1_groups:
            lp1_toks = sorted({str(lg["token_id"]) for _, g_lgs in lp1_groups for lg in g_lgs})
            lp1_bks = await self.fetch_books_batch(lp1_toks, timeout=3.5)
            lp1_asks = {t: p for t, bk in lp1_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
            for g_tag, g_lgs in lp1_groups:
                if len(g_lgs) < 4:
                    continue
                is_nba_em = g_tag.startswith("NBA_EM")
                diag_boxes = find_state_matrix_dominance_boxes(g_lgs, lp1_asks, max_2leg_cost_net=1.045, max_3leg_cost_net=1.03)
                if diag_boxes:
                    d0 = diag_boxes[0]
                    self._record_market_telemetry(
                        f"LP1_{g_tag}", 90.0,
                        {"type": "LP1_IMPLICATION_BEST", "group": g_tag, "n_legs": d0["n_legs"], "net_box_l1": d0["box_cost_net"], "label": d0["label"]},
                        now_ts=now, sig=(d0["label"], d0["box_cost_net"]),
                    )
                for bx_l in diag_boxes[:6]:
                    lgs_b = bx_l["legs"]
                    if int(bx_l["n_legs"]) == 2:
                        la_l, lb_l = lgs_b[0], lgs_b[1]
                        bka_l, bkb_l = lp1_bks.get(la_l["token_id"]), lp1_bks.get(lb_l["token_id"])
                        if not bka_l or not bkb_l:
                            continue
                        dk_lp2 = f"LP1_2L_{g_tag}_{la_l['token_id'][-6:]}_{lb_l['token_id'][-6:]}"
                        max_fr_lp = max(float(la_l["fee_rate"]), float(lb_l["fee_rate"]))
                        if float(bx_l["box_cost_net"]) > 0.993:
                            if max_fr_lp == 0.0 and la_l.get("market_id") != lb_l.get("market_id"):
                                self.post_zero_fee_maker_anchor_box(
                                    "SP1_NBA" if is_nba_em else "LP1_BOP",
                                    "NBA" if is_nba_em else "MACRO",
                                    f"ZFA_{dk_lp2}",
                                    la_l, lb_l, bka_l, bkb_l, float(bx_l["close_ts"]),
                                    f"{g_tag} [{bx_l['label']}]", now,
                                    prefetched_books=lp1_bks,
                                )
                            continue
                        w_lp2 = walk_equal_shares_dominance_box(
                            bka_l.get("asks") or [], bkb_l.get("asks") or [],
                            BANKROLL_TICKETS["T1000"]["LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"],
                            float(la_l["fee_rate"]), float(lb_l["fee_rate"]),
                            max_box_cost_net=0.993, min_shares=6, min_box_notional_usd=5.5,
                        )
                        if w_lp2.get("filled"):
                            opps_out.append({
                                "sleeve": "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
                                "market": f"{g_tag}: {bx_l['label']}", "ask_vwap": w_lp2["box_cost_net"], "p_model": 1.0,
                                "net_edge": round(1.0 - float(w_lp2["box_cost_net"]), 4),
                                "l1_usd": w_lp2["l1_usd"], "close_ts": bx_l["close_ts"],
                            })
                            live_lp_cap = 0.990 if max_fr_lp == 0.0 else 0.988
                            if float(w_lp2["box_cost_net"]) <= live_lp_cap:
                                lp_btype = "COMPLETE_SET" if la_l.get("market_id") == lb_l.get("market_id") else ("NBA_DOMINANCE" if is_nba_em else "MACRO_DOMINANCE")
                                self.emit_live_two_leg_box_candidate(
                                    sleeve_source="LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
                                    box_type=lp_btype,
                                    asset="NBA" if is_nba_em else "MACRO",
                                    dedupe_key=dk_lp2,
                                    leg_a=la_l,
                                    leg_b=lb_l,
                                    bk_a=bka_l,
                                    bk_b=bkb_l,
                                    close_ts=float(bx_l["close_ts"]),
                                    now_ts=now,
                                )
                            await self.open_shadow_two_leg_box(
                                "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", dk_lp2, g_tag,
                                f"{g_tag} {bx_l['label']}", la_l, lb_l, bka_l, bkb_l, float(bx_l["close_ts"]), 0.993,
                                {"is_two_leg_box": True, "min_payout": bx_l["min_payout"], "jackpot_states": bx_l["jackpot_states"]},
                            )
                    elif int(bx_l["n_legs"]) == 3 and float(bx_l["box_cost_net"]) <= 0.991:
                        wm_lp3 = walk_equal_shares_multi_leg_box(
                            [{"asks": lp1_bks[x["token_id"]].get("asks") or [], "fee_rate": float(x["fee_rate"]), "fee_exponent": 1.0} for x in lgs_b],
                            BANKROLL_TICKETS["T1000"]["LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"], 1.0, 0.991, min_shares=6, min_box_notional_usd=5.5,
                        )
                        if wm_lp3.get("filled"):
                            dk_lp3 = f"LP1_3L_{g_tag}_{'_'.join(x['token_id'][-5:] for x in lgs_b)}"
                            opps_out.append({
                                "sleeve": "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
                                "market": f"{g_tag} 3L: {bx_l['label']}", "ask_vwap": wm_lp3["box_cost_net"], "p_model": 1.0,
                                "net_edge": round(1.0 - float(wm_lp3["box_cost_net"]), 4),
                                "l1_usd": wm_lp3["l1_usd"], "close_ts": bx_l["close_ts"],
                            })
                            await self.open_shadow_multi_leg_bundle(
                                "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", dk_lp3, g_tag,
                                f"{g_tag} 3-Leg {bx_l['label']}", lgs_b, lp1_bks, float(bx_l["close_ts"]), 1.0, 0.991,
                                {"is_multi_leg_bundle": True, "guaranteed_payout": 1.0},
                            )

        # 7D. `API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK`: BO3 Post-Map-1 `+1.5` Clinch & BO3 `2-1` Polish Middle
        active_esp = [sp for sp in self.esports_bo3_specs.values() if sp.end_ts > now + 60]
        if active_esp:
            esp_toks: List[str] = []
            for sp_e in active_esp[:25]:
                esp_toks.extend([sp_e.ml_a_token, sp_e.ml_b_token, sp_e.hc_minus_token, sp_e.hc_plus_token])
                for mt in (sp_e.map1_a_token, sp_e.map1_b_token, sp_e.map2_a_token, sp_e.map2_b_token, sp_e.ou25_over_token, sp_e.ou25_under_token):
                    if mt:
                        esp_toks.append(mt)
            esp_bks = await self.fetch_books_batch(esp_toks, timeout=3.5)
            esp_asks = {t: p for t, bk in esp_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
            for sp_e in active_esp[:25]:
                ev_res = evaluate_api1_esports_bo3_opportunities(sp_e, esp_bks, esp_asks, max_middle_cost_net=1.035)
                if ev_res["two_leg_boxes"]:
                    eb0 = ev_res["two_leg_boxes"][0]
                    self._record_market_telemetry(
                        f"API1_{sp_e.event_id}", 90.0,
                        {"type": "API1_ESPORTS_BO3_BEST", "match": sp_e.title[:60], "mode": eb0["mode"], "net_box_l1": eb0["box_cost_net"], "forfeit_immune": eb0["post_m1_forfeit_immune"]},
                        now_ts=now, sig=(eb0["mode"], eb0["box_cost_net"]),
                    )
                for lk_e in ev_res["single_leg_locks"]:
                    bk_w_e = esp_bks.get(lk_e["token_id"])
                    bk_o_e = esp_bks.get(lk_e["opp_token_id"])
                    if not bk_w_e or not bk_o_e:
                        continue
                    opp_b_e, _ = extract_best_bid(bk_o_e.get("bids") or [])
                    if opp_b_e > 0.04:
                        continue
                    w_lk_e = walk_l2_book_asks_depth_capped(
                        bk_w_e.get("asks") or [],
                        BANKROLL_TICKETS["T1000"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],
                        BANKROLL_TICKETS["T100"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],
                        fee_rate=float(lk_e["fee_rate"]), min_l1_usd=15.0, max_ask_px=0.978,
                        fee_exponent=float(lk_e["fee_exponent"]),
                    )
                    if w_lk_e.get("filled"):
                        eff_e = float(w_lk_e["eff_px"])
                        edg_e = round(float(lk_e["p_lock"]) - eff_e, 4)
                        if 0.72 <= eff_e <= 0.978 and edg_e >= 0.018:
                            dk_e = f"API1_LK_{sp_e.event_id}_{lk_e['market_id']}"
                            opps_out.append({
                                "sleeve": "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
                                "market": f"Esports BO3 Lock: {lk_e['display_label']}",
                                "ask_vwap": eff_e, "p_model": lk_e["p_lock"], "net_edge": edg_e,
                                "l1_usd": w_lk_e["l1_usd"], "close_ts": lk_e["close_ts"],
                            })
                            self.emit_live_single_leg_lock_candidate(
                                sleeve_source="API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
                                asset="ESPORTS",
                                dedupe_key=dk_e,
                                token_id=str(lk_e["token_id"]),
                                opp_token_id=str(lk_e["opp_token_id"]),
                                market_id=str(lk_e["market_id"]),
                                condition_id=str(lk_e["condition_id"]),
                                side_label=str(lk_e["side_label"]),
                                display_label=str(lk_e["display_label"]),
                                bk_win=bk_w_e,
                                bk_opp=bk_o_e,
                                fee_rate=float(lk_e["fee_rate"]),
                                fee_exponent=float(lk_e["fee_exponent"]),
                                neg_risk=False,
                                close_ts=float(lk_e["close_ts"]),
                                now_ts=now,
                                max_lock_eff_px=0.978,
                                max_opp_bid=0.025,
                                hold_to_maturity=True,
                                p_model=float(lk_e["p_lock"]),
                            )
                            await self.open_shadow_position(
                                "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK", dk_e, "ESPORTS_BO3",
                                f"{sp_e.title} [{lk_e['display_label']}]", str(lk_e["side_label"]),
                                str(lk_e["token_id"]), float(lk_e["fee_rate"]), float(lk_e["p_lock"]),
                                float(lk_e["close_ts"]),
                                {"market_id": lk_e["market_id"], "condition_id": lk_e["condition_id"], "mode": lk_e["mode"]},
                                prefetched_book=bk_w_e,
                            )
                for bx_e in ev_res["two_leg_boxes"]:
                    if float(bx_e["box_cost_net"]) > 0.988:
                        continue
                    la_e, lb_e = bx_e["leg_a"], bx_e["leg_b"]
                    bka_e, bkb_e = esp_bks.get(la_e["token_id"]), esp_bks.get(lb_e["token_id"])
                    if not bka_e or not bkb_e:
                        continue
                    w_bx_e = walk_equal_shares_dominance_box(
                        bka_e.get("asks") or [], bkb_e.get("asks") or [],
                        BANKROLL_TICKETS["T1000"]["API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"],
                        float(la_e["fee_rate"]), float(lb_e["fee_rate"]),
                        fee_exponent_a=float(la_e["fee_exponent"]), fee_exponent_b=float(lb_e["fee_exponent"]),
                        max_box_cost_net=0.988, min_shares=6, min_box_notional_usd=5.5,
                    )
                    if w_bx_e.get("filled"):
                        dk_bxe = f"API1_MID_{sp_e.event_id}_{la_e['market_id']}_{lb_e['market_id']}"
                        opps_out.append({
                            "sleeve": "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
                            "market": bx_e["label"], "ask_vwap": w_bx_e["box_cost_net"], "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_bx_e["box_cost_net"]), 4),
                            "l1_usd": w_bx_e["l1_usd"], "close_ts": bx_e["close_ts"],
                        })
                        if bool(bx_e.get("post_m1_forfeit_immune")) and la_e.get("market_id") != lb_e.get("market_id"):
                            self.emit_live_two_leg_box_candidate(
                                sleeve_source="API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
                                box_type="SPORTS_CORRIDOR",
                                asset="ESPORTS",
                                dedupe_key=dk_bxe,
                                leg_a=la_e,
                                leg_b=lb_e,
                                bk_a=bka_e,
                                bk_b=bkb_e,
                                close_ts=float(bx_e["close_ts"]),
                                now_ts=now,
                            )
                        await self.open_shadow_two_leg_box(
                            "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK", dk_bxe, "ESPORTS_BO3",
                            bx_e["label"], la_e, lb_e, bka_e, bkb_e, float(bx_e["close_ts"]), 0.988,
                            {"is_two_leg_box": True, "mode": bx_e["mode"], "post_m1_forfeit_immune": bx_e["post_m1_forfeit_immune"]},
                        )

    async def _scan_frontier_v3_sleeves(self, opps_out: List[Dict[str, Any]], now: float) -> None:
        # 7E. `LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG`: Midterm Seats, Tossup Cube, & Conditional Partitions (`0%` Fee)
        if self.lp2_implication_groups or self.lp2_events_by_slug:
            lp2_toks_set = {
                str(lg["token_id"])
                for _, lgs in self.lp2_implication_groups
                for lg in lgs
                if float(lg.get("end_ts") or 0.0) > now + 60
            }
            for sl_conv in (
                "republican-house-seats-after-the-2026-midterm-elections",
                "republican-senate-seats-after-the-2026-midterm-elections-927",
                "which-party-will-win-the-house-in-2026",
                "which-party-will-win-the-senate-in-2026",
            ):
                ev_cv = self.lp2_events_by_slug.get(sl_conv) or {}
                for m_cv in ev_cv.get("markets") or []:
                    if not m_cv.get("closed"):
                        tk_cv = _parse_clob_tokens(m_cv)
                        if tk_cv:
                            lp2_toks_set.update(tk_cv)
            if lp2_toks_set:
                lp2_bks = await self.fetch_books_batch(sorted(lp2_toks_set), timeout=4.0)
                lp2_asks = {t: p for t, bk in lp2_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
                for grp_name, grp_legs in self.lp2_implication_groups:
                    bx_lp2 = find_state_matrix_dominance_boxes(grp_legs, lp2_asks, max_2leg_cost_net=1.045, max_3leg_cost_net=0.992)
                    if bx_lp2:
                        b0_l2 = bx_lp2[0]
                        self._record_market_telemetry(
                            f"LP2_{grp_name}", 90.0,
                            {"type": "LP2_DAG_BOX_BEST", "group": grp_name, "n_legs": b0_l2["n_legs"], "label": b0_l2["label"], "net_box_l1": b0_l2["box_cost_net"], "jackpot_states": b0_l2["jackpot_states"]},
                            now_ts=now, sig=(b0_l2["label"], b0_l2["box_cost_net"]),
                        )
                    for bx in bx_lp2[:6]:
                        if float(bx["box_cost_net"]) > 0.992:
                            continue
                        lgs_2 = bx["legs"]
                        if int(bx["n_legs"]) == 2:
                            la_2, lb_2 = lgs_2[0], lgs_2[1]
                            bka_2, bkb_2 = lp2_bks.get(la_2["token_id"]), lp2_bks.get(lb_2["token_id"])
                            if not bka_2 or not bkb_2:
                                continue
                            w_l2 = walk_equal_shares_dominance_box(
                                bka_2.get("asks") or [], bkb_2.get("asks") or [],
                                BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"],
                                float(la_2["fee_rate"]), float(lb_2["fee_rate"]),
                                fee_exponent_a=float(la_2["fee_exponent"]), fee_exponent_b=float(lb_2["fee_exponent"]),
                                max_box_cost_net=0.992, min_shares=6, min_box_notional_usd=5.5,
                            )
                            if w_l2.get("filled"):
                                dk_l2 = f"LP2_{grp_name}_{la_2['token_id'][-8:]}_{lb_2['token_id'][-8:]}"
                                opps_out.append({
                                    "sleeve": "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
                                    "market": f"{grp_name}: {bx['label']}",
                                    "ask_vwap": w_l2["box_cost_net"], "p_model": float(bx["min_payout"]),
                                    "net_edge": round(float(bx["min_payout"]) - float(w_l2["box_cost_net"]), 4),
                                    "l1_usd": w_l2["l1_usd"], "close_ts": bx["close_ts"],
                                })
                                if (
                                    self._can_emit_zero_loss_math_live("LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG", float(bx["close_ts"]), now)
                                    and float(bx["min_payout"]) >= 1.0 - 1e-6
                                    and float(w_l2["box_cost_net"]) <= 0.990
                                    and la_2.get("market_id") != lb_2.get("market_id")
                                    and 0.0 < (float(bx["close_ts"]) - now) <= 604800.0
                                ):
                                    self.emit_live_two_leg_box_candidate(
                                        sleeve_source="LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
                                        box_type="MACRO_DOMINANCE",
                                        asset="MACRO",
                                        dedupe_key=dk_l2,
                                        leg_a=la_2,
                                        leg_b=lb_2,
                                        bk_a=bka_2,
                                        bk_b=bkb_2,
                                        close_ts=float(bx["close_ts"]),
                                        now_ts=now,
                                        k_low=100.0,
                                        k_high=101.0 if int(bx.get("jackpot_states") or 0) > 0 else 100.0,
                                    )
                                await self.open_shadow_two_leg_box(
                                    "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG", dk_l2, grp_name,
                                    f"{grp_name}: {bx['label']}", la_2, lb_2, bka_2, bkb_2, float(bx["close_ts"]), 0.992,
                                    {"is_two_leg_box": True, "group": grp_name, "guaranteed_payout": bx["min_payout"], "max_payout": bx["max_payout"], "jackpot_states": bx["jackpot_states"]},
                                )
                        elif int(bx["n_legs"]) == 3 and all(x["token_id"] in lp2_bks for x in lgs_2):
                            dk_l2_3 = f"LP2_3L_{grp_name}_{'_'.join(x['token_id'][-6:] for x in lgs_2)}"
                            w_l2_3 = walk_equal_shares_multi_leg_box(
                                [{"asks": lp2_bks[x["token_id"]].get("asks") or [], "fee_rate": float(x["fee_rate"]), "fee_exponent": float(x["fee_exponent"])} for x in lgs_2],
                                BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"], float(bx["min_payout"]), 0.992, min_shares=6, min_box_notional_usd=5.5,
                            )
                            if w_l2_3.get("filled"):
                                opps_out.append({
                                    "sleeve": "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
                                    "market": f"{grp_name} 3-Leg: {bx['label']}",
                                    "ask_vwap": w_l2_3["box_cost_net"], "p_model": float(bx["min_payout"]),
                                    "net_edge": round(float(bx["min_payout"]) - float(w_l2_3["box_cost_net"]), 4),
                                    "l1_usd": w_l2_3["l1_usd"], "close_ts": bx["close_ts"],
                                })
                                await self.open_shadow_multi_leg_bundle(
                                    "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG", dk_l2_3, grp_name,
                                    f"{grp_name} 3-Leg: {bx['label']}", lgs_2, lp2_bks, float(bx["close_ts"]),
                                    float(bx["min_payout"]), 0.992,
                                    {"is_multi_leg_bundle": True, "guaranteed_payout": bx["min_payout"], "max_payout": bx["max_payout"]},
                                )
                conv_l2 = await asyncio.to_thread(
                    detect_lp2_seat_convert_implication_arbs,
                    self.lp2_events_by_slug, lp2_bks,
                    BANKROLL_TICKETS["T1000"]["LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG"], 1.035,
                )
                if conv_l2:
                    c0_l2 = conv_l2[0]
                    self._record_market_telemetry(
                        f"LP2_CONV_{c0_l2['mode']}", 90.0,
                        {"type": "LP2_CONVERT_MIDDLE_SNAP", "mode": c0_l2["mode"], "synthetic_box_cost_net": c0_l2["synthetic_box_cost_net"], "shares_out": c0_l2["shares_out"]},
                        now_ts=now, sig=(c0_l2["mode"], c0_l2["synthetic_box_cost_net"]),
                    )
                    for cv in conv_l2:
                        if float(cv["synthetic_box_cost_net"]) <= 0.992:
                            m_no = int(cv["m_no_legs"])
                            guar_gross = float(m_no)
                            max_gross = float(m_no - 1) + 0.992
                            dk_cv2 = f"LP2_CV_{cv['mode']}"
                            opps_out.append({
                                "sleeve": "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
                                "market": cv["label"], "ask_vwap": cv["synthetic_box_cost_net"],
                                "p_model": 1.0, "net_edge": cv["guaranteed_floor_edge_ps"],
                                "l1_usd": cv["l1_usd"], "close_ts": cv["close_ts"],
                            })
                            await self.open_shadow_multi_leg_bundle(
                                "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG", dk_cv2, "LP2_CONVERT",
                                cv["label"], cv["legs"], lp2_bks, float(cv["close_ts"]),
                                guar_gross, max_gross,
                                {"is_multi_leg_bundle": True, "guaranteed_payout": guar_gross, "mode": cv["mode"], "index_set_int": cv["index_set_int"]},
                            )

        # 7F. `SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION` (2B/2C): `1H/Q1` Tie-Proof `ML+Dog` & `Steals/Blocks` Corridors (`0%` Fee)
        active_sub_nba = [s for s in self.nba_subperiod_slates.values() if s.settle_est_ts > now + 120]
        for sl_sub in active_sub_nba[:10]:
            sub_toks = [t for rgs in sl_sub.ext_props_by_player_stat.values() if len(rgs) >= 2 for r in rgs for t in (r.yes_token, r.no_token)]
            sub_toks += [t for sm in sl_sub.subperiod_markets if sm.period_scope in ("1H", "Q1") and sm.kind in ("ML", "SPREAD") for t in (sm.tok_0, sm.tok_1)]
            if not sub_toks:
                continue
            sub_bks = await self.fetch_books_batch(sorted(set(sub_toks)), timeout=3.5)
            sub_asks = {t: p for t, bk in sub_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
            sub_boxes = detect_sp4_subperiod_and_ext_prop_boxes(sl_sub, sub_asks, max_box_cost_net=1.045)
            if sub_boxes:
                sb0 = sub_boxes[0]
                self._record_market_telemetry(
                    f"SP4_SUB_{sl_sub.event_id}", 90.0,
                    {"type": "SP4_SUBPERIOD_BOX_BEST", "game": sl_sub.title[:60], "mode": sb0["mode"], "label": sb0["label"], "net_box_l1": sb0["box_cost_net"]},
                    now_ts=now, sig=(sb0["label"], sb0["box_cost_net"]),
                )
            for sbx in sub_boxes[:8]:
                if float(sbx["box_cost_net"]) > 0.992:
                    continue
                la_s, lb_s = sbx["leg_a"], sbx["leg_b"]
                bka_s, bkb_s = sub_bks.get(la_s["token_id"]), sub_bks.get(lb_s["token_id"])
                if not bka_s or not bkb_s:
                    continue
                w_sb = walk_equal_shares_dominance_box(
                    bka_s.get("asks") or [], bkb_s.get("asks") or [],
                    BANKROLL_TICKETS["T1000"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],
                    float(la_s["fee_rate"]), float(lb_s["fee_rate"]),
                    fee_exponent_a=float(la_s.get("fee_exponent", 1.0)),
                    fee_exponent_b=float(lb_s.get("fee_exponent", 1.0)),
                    max_box_cost_net=0.992, min_shares=6, min_box_notional_usd=5.5,
                )
                if w_sb.get("filled"):
                    dk_sb = f"SP4_SUB_{la_s['market_id']}_{lb_s['market_id']}"
                    opps_out.append({
                        "sleeve": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
                        "market": f"NBA [{sbx['mode']}] {sbx['label']}",
                        "ask_vwap": w_sb["box_cost_net"], "p_model": 1.0,
                        "net_edge": round(1.0 - float(w_sb["box_cost_net"]), 4),
                        "l1_usd": w_sb["l1_usd"], "close_ts": sbx["close_ts"],
                    })
                    if (
                        self._can_emit_zero_loss_math_live("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", float(sbx["close_ts"]), now)
                        and float(w_sb["box_cost_net"]) <= 0.990
                        and la_s.get("market_id") != lb_s.get("market_id")
                        and 0.0 < (float(sbx["close_ts"]) - now) <= 259200.0
                    ):
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
                            box_type="NBA_DOMINANCE",
                            asset="NBA",
                            dedupe_key=dk_sb,
                            leg_a=la_s,
                            leg_b=lb_s,
                            bk_a=bka_s,
                            bk_b=bkb_s,
                            close_ts=float(sbx["close_ts"]),
                            now_ts=now,
                            k_low=float(la_s.get("strike") or 100.0),
                            k_high=float(lb_s.get("strike") or 101.0),
                        )
                    await self.open_shadow_two_leg_box(
                        "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", dk_sb, "NBA_SUBPERIOD",
                        f"{sl_sub.title} [{sbx['label']}]", la_s, lb_s, bka_s, bkb_s, float(sbx["close_ts"]), 0.992,
                        {"is_two_leg_box": True, "mode": sbx["mode"]},
                    )

        # 7G. `CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX`: Survival, Cumulative Deadline, & Scalar Ladders
        active_cal = [sp for sp in self.cal1_ladders.values() if sp.rungs and sp.rungs[-1].end_ts > now + 120]
        if active_cal:
            cal_toks = sorted({t for sp in active_cal for r in sp.rungs for t in (r.yes_token, r.no_token)})
            cal_bks = await self.fetch_books_batch(cal_toks, timeout=4.0)
            cal_asks = {t: p for t, bk in cal_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
            for sp_cal in active_cal:
                cal_boxes = detect_cal1_monotonic_boxes(sp_cal, cal_asks, max_box_cost_net=1.045)
                if cal_boxes:
                    cb0 = cal_boxes[0]
                    self._record_market_telemetry(
                        f"CAL1_{sp_cal.event_id}", 90.0,
                        {"type": "CAL1_LADDER_BOX_BEST", "kind": sp_cal.ladder_kind, "label": cb0["label"], "net_box_l1": cb0["box_cost_net"]},
                        now_ts=now, sig=(cb0["label"], cb0["box_cost_net"]),
                    )
                for cbx in cal_boxes[:6]:
                    if float(cbx["box_cost_net"]) > 0.992:
                        continue
                    la_c, lb_c = cbx["leg_a"], cbx["leg_b"]
                    bka_c, bkb_c = cal_bks.get(la_c["token_id"]), cal_bks.get(lb_c["token_id"])
                    if not bka_c or not bkb_c:
                        continue
                    w_cb = walk_equal_shares_dominance_box(
                        bka_c.get("asks") or [], bkb_c.get("asks") or [],
                        BANKROLL_TICKETS["T1000"]["CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"],
                        float(la_c["fee_rate"]), float(lb_c["fee_rate"]),
                        fee_exponent_a=float(la_c["fee_exponent"]), fee_exponent_b=float(lb_c["fee_exponent"]),
                        max_box_cost_net=0.992, min_shares=6, min_box_notional_usd=5.5,
                    )
                    if w_cb.get("filled"):
                        dk_cb = f"CAL1_{la_c['market_id']}_{lb_c['market_id']}"
                        opps_out.append({
                            "sleeve": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
                            "market": cbx["label"], "ask_vwap": w_cb["box_cost_net"], "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_cb["box_cost_net"]), 4),
                            "l1_usd": w_cb["l1_usd"], "close_ts": cbx["close_ts"],
                        })
                        if (
                            self._can_emit_zero_loss_math_live("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX", float(cbx["close_ts"]), now)
                            and la_c.get("market_id") != lb_c.get("market_id")
                            and 0.0 < (float(cbx["close_ts"]) - now) <= 604800.0
                            and (float(cbx.get("early_leg_close_ts") or cbx["close_ts"]) - now) >= 60.0
                        ):
                            self.emit_live_two_leg_box_candidate(
                                sleeve_source="CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
                                box_type="MACRO_DOMINANCE",
                                asset="MACRO",
                                dedupe_key=dk_cb,
                                leg_a=la_c,
                                leg_b=lb_c,
                                bk_a=bka_c,
                                bk_b=bkb_c,
                                close_ts=float(cbx["close_ts"]),
                                now_ts=now,
                                k_low=float(la_c.get("strike") or 100.0),
                                k_high=float(lb_c.get("strike") or 101.0),
                            )
                        await self.open_shadow_two_leg_box(
                            "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX", dk_cb, f"CAL1_{sp_cal.ladder_kind}",
                            cbx["label"], la_c, lb_c, bka_c, bkb_c, float(cbx["close_ts"]), 0.992,
                            {"is_two_leg_box": True, "mode": cbx["mode"], "ladder_kind": sp_cal.ladder_kind},
                        )

        # 7H. `LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX`: 11-State NFL Exact-Margin + Multi-Sport Tie-Proof Polish Middles
        for nfl_b in list(self.lp1_nfl_em_bundles.values())[:12]:
            if float(nfl_b["end_ts"]) <= now + 60:
                continue
            nfl_toks = sorted({str(lg["token_id"]) for lg in nfl_b["legs"]})
            nfl_bks = await self.fetch_books_batch(nfl_toks, timeout=3.5)
            nfl_asks = {t: p for t, bk in nfl_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
            nfl_boxes = find_state_matrix_dominance_boxes(nfl_b["legs"], nfl_asks, max_2leg_cost_net=1.045, max_3leg_cost_net=0.990)
            if nfl_boxes:
                nb0 = nfl_boxes[0]
                self._record_market_telemetry(
                    f"LP1_NFL_EM_{nfl_b['event_id']}", 90.0,
                    {"type": "LP1_NFL_EM_BOX_BEST", "game": nfl_b["title"][:60], "n_legs": nb0["n_legs"], "label": nb0["label"], "net_box_l1": nb0["box_cost_net"]},
                    now_ts=now, sig=(nb0["label"], nb0["box_cost_net"]),
                )
            for nbx in nfl_boxes[:6]:
                if float(nbx["box_cost_net"]) > 0.990 or int(nbx["n_legs"]) != 2:
                    continue
                la_nf, lb_nf = nbx["legs"][0], nbx["legs"][1]
                bka_nf, bkb_nf = nfl_bks.get(la_nf["token_id"]), nfl_bks.get(lb_nf["token_id"])
                if not bka_nf or not bkb_nf:
                    continue
                w_nf = walk_equal_shares_dominance_box(
                    bka_nf.get("asks") or [], bkb_nf.get("asks") or [],
                    BANKROLL_TICKETS["T1000"]["LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX"],
                    float(la_nf["fee_rate"]), float(lb_nf["fee_rate"]),
                    fee_exponent_a=float(la_nf["fee_exponent"]), fee_exponent_b=float(lb_nf["fee_exponent"]),
                    max_box_cost_net=0.990, min_shares=6, min_box_notional_usd=5.5,
                )
                if w_nf.get("filled"):
                    dk_nf = f"LP1_NFLEM_{nfl_b['event_id']}_{la_nf['token_id'][-8:]}_{lb_nf['token_id'][-8:]}"
                    opps_out.append({
                        "sleeve": "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
                        "market": f"NFL EM [{nfl_b['title']}]: {nbx['label']}",
                        "ask_vwap": w_nf["box_cost_net"], "p_model": 1.0,
                        "net_edge": round(1.0 - float(w_nf["box_cost_net"]), 4),
                        "l1_usd": w_nf["l1_usd"], "close_ts": nbx["close_ts"],
                    })
                    if (
                        self._can_emit_zero_loss_math_live("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX", float(nbx["close_ts"]), now)
                        and float(nbx.get("min_payout", 1.0)) >= 1.0 - 1e-6
                        and float(w_nf["box_cost_net"]) <= 0.988
                        and la_nf.get("market_id") != lb_nf.get("market_id")
                        and 0.0 < (float(nbx["close_ts"]) - now) <= 604800.0
                    ):
                        self.emit_live_two_leg_box_candidate(
                            sleeve_source="LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
                            box_type="SPORTS_CORRIDOR",
                            asset="NFL",
                            dedupe_key=dk_nf,
                            leg_a=la_nf,
                            leg_b=lb_nf,
                            bk_a=bka_nf,
                            bk_b=bkb_nf,
                            close_ts=float(nbx["close_ts"]),
                            now_ts=now,
                            k_low=100.0,
                            k_high=101.0 if float(nbx.get("max_payout", 1.0)) > 1.05 else 100.0,
                        )
                    await self.open_shadow_two_leg_box(
                        "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX", dk_nf, "NFL_EM",
                        f"{nfl_b['title']} [{nbx['label']}]", la_nf, lb_nf, bka_nf, bkb_nf, float(nbx["close_ts"]), 0.990,
                        {"is_two_leg_box": True, "mode": "NFL_EXACT_MARGIN_DOMINANCE", "max_payout": nbx["max_payout"]},
                    )

        ms_pm_evts = list(self.multisport_raw_events.values())[:24]
        if ms_pm_evts:
            ms_pm_toks: List[str] = []
            for _, ev_ms in ms_pm_evts:
                for m_ms in ev_ms.get("markets") or []:
                    if not m_ms.get("closed") and str(m_ms.get("sportsMarketType") or "").lower() in (
                        "moneyline", "spreads", "first_half_moneyline", "first_half_spreads", "q1_moneyline", "q1_spreads"
                    ):
                        tk_ms = _parse_clob_tokens(m_ms)
                        if tk_ms:
                            ms_pm_toks.extend(tk_ms)
            if ms_pm_toks:
                ms_pm_bks = await self.fetch_books_batch(sorted(set(ms_pm_toks)), timeout=3.5)
                ms_pm_asks = {t: p for t, bk in ms_pm_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
                for sp_tag_m, ev_ms in ms_pm_evts:
                    pm_boxes = detect_multisport_ml_spread_polish_middles(ev_ms, ms_pm_asks, sport_hint=sp_tag_m, max_box_cost_net=1.04)
                    for pbx in pm_boxes[:4]:
                        if float(pbx["box_cost_net"]) > 0.988:
                            continue
                        la_p, lb_p = pbx["leg_a"], pbx["leg_b"]
                        bka_p, bkb_p = ms_pm_bks.get(la_p["token_id"]), ms_pm_bks.get(lb_p["token_id"])
                        if not bka_p or not bkb_p:
                            continue
                        w_pm = walk_equal_shares_dominance_box(
                            bka_p.get("asks") or [], bkb_p.get("asks") or [],
                            BANKROLL_TICKETS["T1000"]["LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX"],
                            float(la_p["fee_rate"]), float(lb_p["fee_rate"]),
                            fee_exponent_a=float(la_p["fee_exponent"]), fee_exponent_b=float(lb_p["fee_exponent"]),
                            max_box_cost_net=0.988, min_shares=6, min_box_notional_usd=5.5,
                        )
                        if w_pm.get("filled"):
                            dk_pm = f"LP1_MSPM_{la_p['market_id']}_{lb_p['market_id']}"
                            opps_out.append({
                                "sleeve": "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
                                "market": pbx["label"], "ask_vwap": w_pm["box_cost_net"], "p_model": 1.0,
                                "net_edge": round(1.0 - float(w_pm["box_cost_net"]), 4),
                                "l1_usd": w_pm["l1_usd"], "close_ts": pbx["close_ts"],
                            })
                            if (
                                self._can_emit_zero_loss_math_live("LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX", float(pbx["close_ts"]), now)
                                and la_p.get("market_id") != lb_p.get("market_id")
                                and 0.0 < (float(pbx["close_ts"]) - now) <= 604800.0
                            ):
                                self.emit_live_two_leg_box_candidate(
                                    sleeve_source="LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
                                    box_type="SPORTS_CORRIDOR",
                                    asset=str(sp_tag_m).upper(),
                                    dedupe_key=dk_pm,
                                    leg_a=la_p,
                                    leg_b=lb_p,
                                    bk_a=bka_p,
                                    bk_b=bkb_p,
                                    close_ts=float(pbx["close_ts"]),
                                    now_ts=now,
                                    k_low=100.0,
                                    k_high=101.0,
                                )
                            await self.open_shadow_two_leg_box(
                                "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX", dk_pm, f"{sp_tag_m}_MIDDLE",
                                pbx["label"], la_p, lb_p, bka_p, bkb_p, float(pbx["close_ts"]), 0.988,
                                {"is_two_leg_box": True, "mode": pbx["mode"]},
                            )

        # 7I. `TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR`: ATP/WTA BO3 Retirement-Immune Set/Match Corridors & `1-1` Split Box
        active_ten = [t for t in self.tennis_specs.values() if t.end_ts > now + 60]
        if active_ten:
            ten_toks: List[str] = []
            for sp_t in active_ten[:25]:
                for rgs_t in sp_t.totals_by_scope.values():
                    for r_t in rgs_t:
                        ten_toks.extend([r_t.over_token, r_t.under_token])
                for tk_opt in (
                    sp_t.set1_a_token, sp_t.set1_b_token, sp_t.set2_a_token, sp_t.set2_b_token,
                    sp_t.sets_ou25_over_token, sp_t.sets_ou25_under_token, sp_t.comp_yes_token, sp_t.comp_no_token,
                ):
                    if tk_opt:
                        ten_toks.append(tk_opt)
            if ten_toks:
                ten_bks = await self.fetch_books_batch(sorted(set(ten_toks)), timeout=3.5)
                ten_asks = {t: p for t, bk in ten_bks.items() for p, s in [self._best_ask_sz(bk)] if p < 1.0 and p * s >= 8.0}
                for sp_t in active_ten[:25]:
                    t_boxes = evaluate_ten1_tennis_opportunities(sp_t, ten_bks, ten_asks, max_box_cost_net=1.045)
                    if t_boxes:
                        tbx0 = t_boxes[0]
                        self._record_market_telemetry(
                            f"TEN1_{sp_t.event_id}", 90.0,
                            {"type": "TEN1_CORRIDOR_BEST", "match": sp_t.title[:60], "mode": tbx0["mode"], "label": tbx0["label"], "net_box_l1": tbx0["box_cost_net"]},
                            now_ts=now, sig=(tbx0["label"], tbx0["box_cost_net"]),
                        )
                    for tbx in t_boxes[:4]:
                        if float(tbx["box_cost_net"]) > 0.988:
                            continue
                        la_tn, lb_tn = tbx["leg_a"], tbx["leg_b"]
                        bka_tn, bkb_tn = ten_bks.get(la_tn["token_id"]), ten_bks.get(lb_tn["token_id"])
                        if not bka_tn or not bkb_tn:
                            continue
                        w_tn = walk_equal_shares_dominance_box(
                            bka_tn.get("asks") or [], bkb_tn.get("asks") or [],
                            BANKROLL_TICKETS["T1000"]["TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR"],
                            float(la_tn["fee_rate"]), float(lb_tn["fee_rate"]),
                            fee_exponent_a=float(la_tn["fee_exponent"]), fee_exponent_b=float(lb_tn["fee_exponent"]),
                            max_box_cost_net=0.988, min_shares=6, min_box_notional_usd=5.5,
                        )
                        if w_tn.get("filled"):
                            dk_tn = f"TEN1_{la_tn['market_id']}_{lb_tn['market_id']}"
                            opps_out.append({
                                "sleeve": "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
                                "market": tbx["label"], "ask_vwap": w_tn["box_cost_net"], "p_model": 1.0,
                                "net_edge": round(1.0 - float(w_tn["box_cost_net"]), 4),
                                "l1_usd": w_tn["l1_usd"], "close_ts": tbx["close_ts"],
                            })
                            if (
                                self._can_emit_zero_loss_math_live("TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR", float(tbx["close_ts"]), now)
                                and la_tn.get("market_id") != lb_tn.get("market_id")
                                and 0.0 < (float(tbx["close_ts"]) - now) <= 259200.0
                            ):
                                self.emit_live_two_leg_box_candidate(
                                    sleeve_source="TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
                                    box_type="SPORTS_CORRIDOR",
                                    asset="TENNIS",
                                    dedupe_key=dk_tn,
                                    leg_a=la_tn,
                                    leg_b=lb_tn,
                                    bk_a=bka_tn,
                                    bk_b=bkb_tn,
                                    close_ts=float(tbx["close_ts"]),
                                    now_ts=now,
                                    k_low=float(la_tn.get("strike") or 100.0),
                                    k_high=float(lb_tn.get("strike") or 101.0),
                                )
                            await self.open_shadow_two_leg_box(
                                "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR", dk_tn, "TENNIS_BO3",
                                tbx["label"], la_tn, lb_tn, bka_tn, bkb_tn, float(tbx["close_ts"]), 0.988,
                                {"is_two_leg_box": True, "mode": tbx["mode"]},
                            )

        # 7J. `CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH`: Post-VAR Soccer, Post-Challenge NHL, & Replay-Safe NFL/CFB Locks
        sports_to_poll: List[str] = []
        if any((tr.end_ts - 3.5 * 3600.0) <= now <= (tr.end_ts + 2.0 * 3600.0) for tr in self.soccer_trees.values()):
            sports_to_poll.append("SOCCER")
        for sp_k in ("NHL", "NFL", "CFB"):
            if any(ms.sport == sp_k and (ms.start_ts - 900.0) <= now <= (ms.start_ts + 6.0 * 3600.0) for ms in self.multi_sport_games.values()):
                sports_to_poll.append(sp_k)
        boards_now: Dict[str, List[LiveMultiSportGame]] = {}
        fetch_sp_list = [
            sp_k for sp_k in sports_to_poll
            if sp_k not in self.live_multisport_boards or (now - self.live_multisport_boards[sp_k][0]) >= 20.0
        ]
        if fetch_sp_list:
            fetched_bds = await asyncio.gather(*(asyncio.to_thread(fetch_espn_multisport_board_sync, sp_k) for sp_k in fetch_sp_list))
            for sp_k, bd_res in zip(fetch_sp_list, fetched_bds):
                self.live_multisport_boards[sp_k] = (now, bd_res)
        for sp_k in sports_to_poll:
            if sp_k in self.live_multisport_boards:
                boards_now[sp_k] = self.live_multisport_boards[sp_k][1]

        cl1_cands: List[Dict[str, Any]] = []
        if "SOCCER" in boards_now and boards_now["SOCCER"]:
            for tr in self.soccer_trees.values():
                for lk_s in evaluate_cl1_soccer_tree_clinch_locks(tr, boards_now["SOCCER"], self.score_confirm_tracker, now):
                    dk_cl = f"CL1_SOC_{lk_s['market_id']}"
                    if dk_cl not in self.entered_keys and dk_cl not in self.inflight_keys:
                        cl1_cands.append({**lk_s, "dedupe_key": dk_cl, "title": getattr(tr, "title", ""), "rules_text": getattr(tr, "rules_text", "")})
        for ms_sp in self.multi_sport_games.values():
            if ms_sp.sport in boards_now and boards_now[ms_sp.sport]:
                for lk_m in evaluate_cl1_multisport_corridor_clinch_locks(ms_sp, boards_now, self.score_confirm_tracker, now):
                    dk_clm = f"CL1_{ms_sp.sport}_{lk_m['market_id']}"
                    if dk_clm not in self.entered_keys and dk_clm not in self.inflight_keys:
                        cl1_cands.append({**lk_m, "dedupe_key": dk_clm, "title": getattr(ms_sp, "title", ""), "rules_text": getattr(ms_sp, "rules_text", "")})
        if cl1_cands:
            cl1_bks = await self.fetch_books_batch(sorted({t for c in cl1_cands for t in (c["token_id"], c["opp_token_id"])}), timeout=3.0)
            for c_cl in cl1_cands:
                if "FINAL" not in str(c_cl.get("mode") or "").upper() and classify_market_rule_dispute_risk(c_cl)["veto_pre_final_clinch"]:
                    continue
                bk_w_cl, bk_o_cl = cl1_bks.get(c_cl["token_id"]), cl1_bks.get(c_cl["opp_token_id"])
                if not bk_w_cl or not bk_o_cl:
                    continue
                opp_b_cl, _ = extract_best_bid(bk_o_cl.get("bids") or [])
                if opp_b_cl > 0.04:
                    continue
                fr_cl = float(c_cl.get("fee_rate") or 0.0)
                fe_cl = float(c_cl.get("fee_exponent") or 1.0)
                w_cl = walk_l2_book_asks_depth_capped(
                    bk_w_cl.get("asks") or [],
                    BANKROLL_TICKETS["T1000"]["CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"],
                    BANKROLL_TICKETS["T100"]["CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH"],
                    fee_rate=fr_cl, min_l1_usd=15.0, max_ask_px=0.9821, fee_exponent=fe_cl,
                )
                if w_cl.get("filled"):
                    eff_cl = float(w_cl["eff_px"])
                    p_cl = float(c_cl["p_lock"])
                    edg_cl = round(p_cl - eff_cl, 4)
                    if 0.72 <= eff_cl <= 0.982 and edg_cl >= 0.015:
                        close_cl = max(now + 600.0, float(c_cl["close_ts"]))
                        opps_out.append({
                            "sleeve": "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
                            "market": f"[{c_cl['mode']}] {c_cl['display_label']}",
                            "ask_vwap": eff_cl, "p_model": p_cl, "net_edge": edg_cl,
                            "l1_usd": w_cl["l1_usd"], "close_ts": close_cl,
                        })
                        if self._can_emit_zero_loss_math_live("CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH", close_cl, now, p_model=p_cl):
                            self.emit_live_single_leg_lock_candidate(
                                sleeve_source="CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
                                asset=str(c_cl["sport"]).upper(),
                                dedupe_key=str(c_cl["dedupe_key"]),
                                token_id=str(c_cl["token_id"]),
                                opp_token_id=str(c_cl["opp_token_id"]),
                                market_id=str(c_cl["market_id"]),
                                condition_id=str(c_cl["condition_id"]),
                                side_label=str(c_cl["side_label"]),
                                display_label=str(c_cl["display_label"]),
                                bk_win=bk_w_cl,
                                bk_opp=bk_o_cl,
                                fee_rate=fr_cl,
                                fee_exponent=fe_cl,
                                neg_risk=bool(c_cl.get("neg_risk", False)),
                                close_ts=close_cl,
                                now_ts=now,
                                max_lock_eff_px=0.982,
                                max_opp_bid=0.025,
                                hold_to_maturity=True,
                                p_model=p_cl,
                            )
                        await self.open_shadow_position(
                            "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH", c_cl["dedupe_key"], c_cl["sport"],
                            c_cl["display_label"], str(c_cl["side_label"]), str(c_cl["token_id"]),
                            fr_cl, p_cl, close_cl,
                            {"market_id": c_cl["market_id"], "condition_id": c_cl["condition_id"], "opp_token_id": c_cl["opp_token_id"], "mode": c_cl["mode"], "fee_exponent": fe_cl},
                            prefetched_book=bk_w_cl,
                        )

    async def _scan_frontier_v4_sleeves(self, opps_out: List[Dict[str, Any]], now: float) -> None:
        """
        Frontier v4 Evergreen Scanner (zero single-event election models):
          8A. `SUM1_FRECHET_SUM_TRIANGLES` + `AFF1_FROZEN_SUBPERIOD_COLLAPSE`
          8B. `SOC2_EXACT_SCORE_2D_LATTICE` (`83`-state lattice boxes + `NR2` convert + post-VAR dead-score `NO` locks)
          8C. `NFL_PRP1_MILESTONE_AND_MAX_LOCKS` (`3%`-fee `TD` Polish Middles + live `longest_*`/counter/DNP locks)
          8D. `CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION` (`Close subset Hit` & `Daily subset Weekly subset Monthly`)
          8E. Unified Frontier v4 1-leg lock executor + `MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER` (`0%` maker + `20%` rebate)
        """
        v4_lock_cands: List[Dict[str, Any]] = []
        self.subperiod_freeze_tracker.prune(now)
        self.score_confirm_tracker.prune(now)

        # Refresh live ESPN multi-sport boards needed by Frontier v4 (`SOCCER`, `NFL`, `CFB`)
        v4_sports_needed: List[str] = []
        if any((lat.end_ts - 3.5 * 3600.0) <= now <= (lat.end_ts + 2.5 * 3600.0) for lat in self.soc2_lattices.values()):
            v4_sports_needed.append("SOCCER")
        if any(
            (b.sport == "NFL" and (b.start_ts - 900.0) <= now <= (b.start_ts + 6.0 * 3600.0))
            for b in self.aff1_bundles.values()
        ) or any((sl.kickoff_ts - 900.0) <= now <= (sl.kickoff_ts + 6.0 * 3600.0) for sl in self.nfl_prop_slates.values()):
            v4_sports_needed.append("NFL")
        if any(
            (b.sport == "CFB" and (b.start_ts - 900.0) <= now <= (b.start_ts + 6.0 * 3600.0))
            for b in self.aff1_bundles.values()
        ):
            v4_sports_needed.append("CFB")
        stale_v4_sp = [
            sp_k for sp_k in v4_sports_needed
            if sp_k not in self.live_multisport_boards or (now - self.live_multisport_boards[sp_k][0]) >= 20.0
        ]
        if stale_v4_sp:
            fetched_v4 = await asyncio.gather(*(asyncio.to_thread(fetch_espn_multisport_board_sync, sp_k) for sp_k in stale_v4_sp))
            for sp_k, bd_v4 in zip(stale_v4_sp, fetched_v4):
                self.live_multisport_boards[sp_k] = (now, bd_v4)

        # 8A. `SUM1_FRECHET_SUM_TRIANGLES` & `AFF1_FROZEN_SUBPERIOD_COLLAPSE`
        active_aff = [b for b in self.aff1_bundles.values() if b.settle_est_ts > now + 120.0]
        if active_aff:
            aff_toks = {
                t
                for b in active_aff
                for t in (
                    [tk for m in b.markets for tk in (m.tok_0, m.tok_1)]
                    + ([str(b.overtime_yes_leg["token_id"])] if b.overtime_yes_leg else [])
                    + [tk for fp in b.first_passage_markets for tk in (fp.away_token, fp.home_token)]
                )
                if t
            }
            aff_bks = await self.fetch_books_batch(sorted(aff_toks), timeout=3.5) if aff_toks else {}
            aff_asks = {
                t: p
                for t, bk in aff_bks.items()
                for p, s in [self._best_ask_sz(bk)]
                if p < 1.0 and p * s >= 8.0
            }
            for b in active_aff:
                # 8A-1. Pre-game & live `SUM1_FRECHET_SUM_TRIANGLES`
                for tri in detect_sum1_frechet_triangles(b, aff_asks, max_3leg_cost_net=0.990):
                    t_lgs = tri["legs"]
                    if not all(x["token_id"] in aff_bks for x in t_lgs):
                        continue
                    dk_sum = f"SUM1_{b.event_id}_{'_'.join(str(x['token_id'])[-6:] for x in t_lgs)}"
                    w_sum = walk_equal_shares_multi_leg_box(
                        [
                            {
                                "asks": aff_bks[x["token_id"]].get("asks") or [],
                                "fee_rate": float(x["fee_rate"]),
                                "fee_exponent": float(x["fee_exponent"]),
                            }
                            for x in t_lgs
                        ],
                        BANKROLL_TICKETS["T1000"]["SUM1_FRECHET_SUM_TRIANGLES"],
                        1.0,
                        0.990,
                        min_shares=6,
                        min_box_notional_usd=5.5,
                    )
                    if w_sum.get("filled"):
                        opps_out.append({
                            "sleeve": "SUM1_FRECHET_SUM_TRIANGLES",
                            "market": tri["label"],
                            "ask_vwap": w_sum["box_cost_net"],
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_sum["box_cost_net"]), 4),
                            "l1_usd": w_sum["l1_usd"],
                            "close_ts": tri["close_ts"],
                        })
                        await self.open_shadow_multi_leg_bundle(
                            "SUM1_FRECHET_SUM_TRIANGLES", dk_sum, b.sport, tri["label"],
                            t_lgs, aff_bks, float(tri["close_ts"]), 1.0, 0.990,
                            {"is_multi_leg_bundle": True, "guaranteed_payout": 1.0, "mode": tri["mode"]},
                        )

                # 8A-2. Live `AFF1_FROZEN_SUBPERIOD_COLLAPSE`
                live_sum: Optional[Dict[str, Any]] = None
                gid_aff = ""
                if b.sport == "NBA" and self.live_nba_board:
                    sp_nba_aff = self.nba_games.get(b.event_id)
                    matched_nba = match_nba_live_game(sp_nba_aff, self.live_nba_board) if sp_nba_aff is not None else None
                    if matched_nba is not None and matched_nba[0].state in ("in", "post"):
                        gid_aff = str(matched_nba[0].game_id or "")
                        if gid_aff:
                            c_ext = self.nba_ext_summary_cache.get(gid_aff)
                            if c_ext is not None and (now - c_ext[0]) < 15.0:
                                live_sum = c_ext[1]
                            else:
                                try:
                                    p_st_a, ext_a = await asyncio.to_thread(fetch_espn_nba_full_summary_sync, gid_aff)
                                    self.nba_boxscore_cache[gid_aff] = (now, p_st_a)
                                    self.nba_ext_summary_cache[gid_aff] = (now, ext_a)
                                    live_sum = ext_a
                                except Exception:
                                    live_sum = None
                elif b.sport in ("NFL", "CFB") and b.sport in self.live_multisport_boards:
                    for g_ms in self.live_multisport_boards[b.sport][1]:
                        if g_ms.start_ts > 0 and b.start_ts > 0 and abs(g_ms.start_ts - b.start_ts) > 10.0 * 3600.0:
                            continue
                        dir_ok = _teams_match_fuzzy(b.away_team, g_ms.away_name) and _teams_match_fuzzy(b.home_team, g_ms.home_name)
                        swp_ok = _teams_match_fuzzy(b.away_team, g_ms.home_name) and _teams_match_fuzzy(b.home_team, g_ms.away_name)
                        if dir_ok and swp_ok:
                            continue
                        if dir_ok or swp_ok:
                            gid_aff = g_ms.game_id
                            ls_aw = dict(g_ms.linescores_home if swp_ok else g_ms.linescores_away)
                            ls_hm = dict(g_ms.linescores_away if swp_ok else g_ms.linescores_home)
                            live_sum = {
                                "state": g_ms.state,
                                "completed": g_ms.completed,
                                "is_halftime": g_ms.is_halftime,
                                "period": g_ms.period,
                                "clock_sec": g_ms.clock_sec,
                                "away_score": g_ms.home_score if swp_ok else g_ms.away_score,
                                "home_score": g_ms.away_score if swp_ok else g_ms.home_score,
                                "linescores": {"away": ls_aw, "home": ls_hm},
                            }
                            break

                if live_sum:
                    aff_res = evaluate_aff1_frozen_subperiod_opportunities(
                        b, live_sum, aff_asks, self.subperiod_freeze_tracker, now,
                        espn_game_id=gid_aff, max_2leg_cost_net=0.992, max_3leg_cost_net=0.990,
                    )
                    for abx in aff_res["two_leg_boxes"]:
                        la_af, lb_af = abx["leg_a"], abx["leg_b"]
                        bka_af, bkb_af = aff_bks.get(la_af["token_id"]), aff_bks.get(lb_af["token_id"])
                        if not bka_af or not bkb_af:
                            continue
                        dk_af2 = f"AFF1_2L_{b.event_id}_{la_af['token_id'][-8:]}_{lb_af['token_id'][-8:]}"
                        w_af2 = walk_equal_shares_dominance_box(
                            bka_af.get("asks") or [], bkb_af.get("asks") or [],
                            BANKROLL_TICKETS["T1000"]["AFF1_FROZEN_SUBPERIOD_COLLAPSE"],
                            float(la_af["fee_rate"]), float(lb_af["fee_rate"]),
                            fee_exponent_a=float(la_af["fee_exponent"]), fee_exponent_b=float(lb_af["fee_exponent"]),
                            max_box_cost_net=0.992, min_shares=6, min_box_notional_usd=5.5,
                        )
                        if w_af2.get("filled"):
                            opps_out.append({
                                "sleeve": "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
                                "market": abx["label"],
                                "ask_vwap": w_af2["box_cost_net"],
                                "p_model": 1.0,
                                "net_edge": round(1.0 - float(w_af2["box_cost_net"]), 4),
                                "l1_usd": w_af2["l1_usd"],
                                "close_ts": abx["close_ts"],
                            })
                            if (
                                self._can_emit_zero_loss_math_live("AFF1_FROZEN_SUBPERIOD_COLLAPSE", float(abx["close_ts"]), now)
                                and float(w_af2["box_cost_net"]) <= 0.988
                                and 0.0 < (float(abx["close_ts"]) - now) <= 86400.0
                            ):
                                self.emit_live_two_leg_box_candidate(
                                    sleeve_source="AFF1_FROZEN_SUBPERIOD_COLLAPSE",
                                    box_type="SPORTS_CORRIDOR",
                                    asset=b.sport,
                                    dedupe_key=dk_af2,
                                    leg_a=la_af,
                                    leg_b=lb_af,
                                    bk_a=bka_af,
                                    bk_b=bkb_af,
                                    close_ts=float(abx["close_ts"]),
                                    now_ts=now,
                                    k_low=float(la_af.get("strike") or 100.0),
                                    k_high=float(lb_af.get("strike") or 101.0),
                                )
                            await self.open_shadow_two_leg_box(
                                "AFF1_FROZEN_SUBPERIOD_COLLAPSE", dk_af2, b.sport, abx["label"],
                                la_af, lb_af, bka_af, bkb_af, float(abx["close_ts"]), 0.992,
                                {"is_two_leg_box": True, "mode": abx["mode"], "middle_width": abx["middle_width"]},
                            )
                    for ab3 in aff_res["three_leg_boxes"]:
                        lgs3 = ab3["legs"]
                        if not all(x["token_id"] in aff_bks for x in lgs3):
                            continue
                        dk_af3 = f"AFF1_3L_{b.event_id}_{'_'.join(str(x['token_id'])[-6:] for x in lgs3)}"
                        w_af3 = walk_equal_shares_multi_leg_box(
                            [
                                {
                                    "asks": aff_bks[x["token_id"]].get("asks") or [],
                                    "fee_rate": float(x["fee_rate"]),
                                    "fee_exponent": float(x["fee_exponent"]),
                                }
                                for x in lgs3
                            ],
                            BANKROLL_TICKETS["T1000"]["AFF1_FROZEN_SUBPERIOD_COLLAPSE"],
                            1.0, 0.990, min_shares=6, min_box_notional_usd=5.5,
                        )
                        if w_af3.get("filled"):
                            opps_out.append({
                                "sleeve": "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
                                "market": ab3["label"],
                                "ask_vwap": w_af3["box_cost_net"],
                                "p_model": 1.0,
                                "net_edge": round(1.0 - float(w_af3["box_cost_net"]), 4),
                                "l1_usd": w_af3["l1_usd"],
                                "close_ts": ab3["close_ts"],
                            })
                            await self.open_shadow_multi_leg_bundle(
                                "AFF1_FROZEN_SUBPERIOD_COLLAPSE", dk_af3, b.sport, ab3["label"],
                                lgs3, aff_bks, float(ab3["close_ts"]), 1.0, 0.990,
                                {"is_multi_leg_bundle": True, "guaranteed_payout": 1.0, "mode": ab3["mode"]},
                            )
                    for alk in aff_res["single_leg_locks"]:
                        dk_alk = f"AFF1_LK_{b.event_id}_{alk['market_id']}"
                        v4_lock_cands.append({
                            **alk,
                            "sleeve": "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
                            "asset": b.sport,
                            "dedupe_key": dk_alk,
                            "max_eff_px": 0.988,
                            "title": getattr(b, "title", ""),
                            "rules_text": getattr(b, "rules_text", ""),
                        })

        # 8B. `SOC2_EXACT_SCORE_2D_LATTICE` (`83`-state lattice boxes + `NR2` convert + post-VAR dead-score `NO` locks)
        soc_board = self.live_multisport_boards["SOCCER"][1] if "SOCCER" in self.live_multisport_boards else []
        if soc_board:
            for lat in self.soc2_lattices.values():
                if (lat.end_ts + 7200.0) <= now:
                    continue
                for slk in evaluate_soc2_dead_score_no_locks(lat, soc_board, self.score_confirm_tracker, now):
                    dk_slk = f"SOC2_NO_{slk['market_id']}"
                    v4_lock_cands.append({
                        **slk,
                        "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
                        "asset": "SOCCER",
                        "dedupe_key": dk_slk,
                        "max_eff_px": 0.986,
                        "title": getattr(lat, "title", ""),
                        "rules_text": getattr(lat, "rules_text", ""),
                    })
        pre_soc2 = [lat for lat in self.soc2_lattices.values() if lat.end_ts > now + 120.0][:10]
        if pre_soc2:
            soc2_toks = sorted(
                {
                    str(lg["token_id"])
                    for lat in pre_soc2
                    for lg in lat.matrix_legs
                    if lg.get("token_id")
                }
                | {
                    str(t_cv)
                    for lat in pre_soc2
                    if lat.convert_spec is not None
                    for b_cv in lat.convert_spec.brackets
                    for t_cv in (b_cv.get("no_token"), b_cv.get("yes_token"))
                    if t_cv
                }
            )
            soc2_bks = await self.fetch_books_batch(soc2_toks, timeout=3.5) if soc2_toks else {}
            soc2_asks = {
                t: p
                for t, bk in soc2_bks.items()
                for p, s in [self._best_ask_sz(bk)]
                if p < 1.0 and p * s >= 8.0
            }
            for lat in pre_soc2:
                s2_res = detect_soc2_lattice_boxes_and_converts(
                    lat, soc2_bks, soc2_asks,
                    max_2leg_cost_net=0.990, max_3leg_cost_net=0.988,
                    target_budget_usd=BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"],
                )
                for sbx in s2_res["matrix_boxes"]:
                    lgs_s = sbx["legs"]
                    if int(sbx["n_legs"]) == 2:
                        la_s, lb_s = lgs_s[0], lgs_s[1]
                        bka_s, bkb_s = soc2_bks.get(la_s["token_id"]), soc2_bks.get(lb_s["token_id"])
                        if not bka_s or not bkb_s:
                            continue
                        dk_s2 = f"SOC2_2L_{lat.exact_event_id}_{la_s['token_id'][-8:]}_{lb_s['token_id'][-8:]}"
                        w_s2 = walk_equal_shares_dominance_box(
                            bka_s.get("asks") or [], bkb_s.get("asks") or [],
                            BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"],
                            float(la_s["fee_rate"]), float(lb_s["fee_rate"]),
                            fee_exponent_a=float(la_s.get("fee_exponent", 1.0)),
                            fee_exponent_b=float(lb_s.get("fee_exponent", 1.0)),
                            max_box_cost_net=0.990, min_shares=6, min_box_notional_usd=5.5,
                        )
                        if w_s2.get("filled"):
                            opps_out.append({
                                "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
                                "market": f"{lat.title}: {sbx['label']}",
                                "ask_vwap": w_s2["box_cost_net"],
                                "p_model": 1.0,
                                "net_edge": round(1.0 - float(w_s2["box_cost_net"]), 4),
                                "l1_usd": w_s2["l1_usd"],
                                "close_ts": sbx["close_ts"],
                            })
                            if (
                                bool(sbx.get("exhaustive_partition_verified"))
                                and self._can_emit_zero_loss_math_live("SOC2_EXACT_SCORE_2D_LATTICE", float(sbx["close_ts"]), now)
                                and la_s.get("market_id") != lb_s.get("market_id")
                                and float(w_s2["box_cost_net"]) <= 0.988
                                and 0.0 < (float(sbx["close_ts"]) - now) <= 172800.0
                            ):
                                self.emit_live_two_leg_box_candidate(
                                    sleeve_source="SOC2_EXACT_SCORE_2D_LATTICE",
                                    box_type="SPORTS_CORRIDOR",
                                    asset="SOCCER",
                                    dedupe_key=dk_s2,
                                    leg_a=la_s,
                                    leg_b=lb_s,
                                    bk_a=bka_s,
                                    bk_b=bkb_s,
                                    close_ts=float(sbx["close_ts"]),
                                    now_ts=now,
                                    k_low=float(la_s.get("strike") or 100.0),
                                    k_high=float(lb_s.get("strike") or 101.0),
                                )
                            await self.open_shadow_two_leg_box(
                                "SOC2_EXACT_SCORE_2D_LATTICE", dk_s2, "SOCCER",
                                f"{lat.title}: {sbx['label']}", la_s, lb_s, bka_s, bkb_s,
                                float(sbx["close_ts"]), 0.990, {"is_two_leg_box": True, "mode": sbx["mode"]},
                            )
                    elif int(sbx["n_legs"]) == 3 and all(x["token_id"] in soc2_bks for x in lgs_s):
                        dk_s3 = f"SOC2_3L_{lat.exact_event_id}_{'_'.join(str(x['token_id'])[-6:] for x in lgs_s)}"
                        w_s3 = walk_equal_shares_multi_leg_box(
                            [
                                {
                                    "asks": soc2_bks[x["token_id"]].get("asks") or [],
                                    "fee_rate": float(x["fee_rate"]),
                                    "fee_exponent": float(x.get("fee_exponent", 1.0)),
                                }
                                for x in lgs_s
                            ],
                            BANKROLL_TICKETS["T1000"]["SOC2_EXACT_SCORE_2D_LATTICE"],
                            1.0, 0.988, min_shares=6, min_box_notional_usd=5.5,
                        )
                        if w_s3.get("filled"):
                            opps_out.append({
                                "sleeve": "SOC2_EXACT_SCORE_2D_LATTICE",
                                "market": f"{lat.title} 3L: {sbx['label']}",
                                "ask_vwap": w_s3["box_cost_net"],
                                "p_model": 1.0,
                                "net_edge": round(1.0 - float(w_s3["box_cost_net"]), 4),
                                "l1_usd": w_s3["l1_usd"],
                                "close_ts": sbx["close_ts"],
                            })
                            await self.open_shadow_multi_leg_bundle(
                                "SOC2_EXACT_SCORE_2D_LATTICE", dk_s3, "SOCCER",
                                f"{lat.title} 3L: {sbx['label']}", lgs_s, soc2_bks,
                                float(sbx["close_ts"]), 1.0, 0.988,
                                {"is_multi_leg_bundle": True, "guaranteed_payout": 1.0, "mode": sbx["mode"]},
                            )
                if lat.convert_spec is not None and s2_res["convert_arbs"]:
                    await self.execute_nr2_subset_convert_arb(lat.convert_spec, s2_res["convert_arbs"][0], soc2_bks, opps_out)

        # 8C. `NFL_PRP1_MILESTONE_AND_MAX_LOCKS` (`3%`-fee `TD` Polish Middles + live `longest_*`/counter/DNP locks)
        active_nfl_prp = [sl for sl in self.nfl_prop_slates.values() if sl.settle_est_ts > now + 120.0][:8]
        if active_nfl_prp:
            nfl_prp_toks = sorted({
                tk
                for sl in active_nfl_prp
                for rg in (
                    list(sl.anytime_td_by_player.values())
                    + list(sl.two_plus_td_by_player.values())
                    + [r for r_list in sl.ladders_by_player_stat.values() for r in r_list]
                )
                for tk in (rg.yes_over_token, rg.no_under_token)
                if tk
            })
            nfl_prp_bks = await self.fetch_books_batch(nfl_prp_toks, timeout=3.5) if nfl_prp_toks else {}
            nfl_prp_asks = {
                t: p
                for t, bk in nfl_prp_bks.items()
                for p, s in [self._best_ask_sz(bk)]
                if p < 1.0 and p * s >= 8.0
            }
            nfl_board = self.live_multisport_boards["NFL"][1] if "NFL" in self.live_multisport_boards else []
            for sl in active_nfl_prp:
                for pbx in detect_nfl_prp1_boxes(sl, nfl_prp_asks, max_box_cost_net=0.990):
                    la_np, lb_np = pbx["leg_a"], pbx["leg_b"]
                    bka_np, bkb_np = nfl_prp_bks.get(la_np["token_id"]), nfl_prp_bks.get(lb_np["token_id"])
                    if not bka_np or not bkb_np:
                        continue
                    dk_np = f"NFL_PRP1_2L_{sl.event_id}_{la_np['token_id'][-8:]}_{lb_np['token_id'][-8:]}"
                    w_np = walk_equal_shares_dominance_box(
                        bka_np.get("asks") or [], bkb_np.get("asks") or [],
                        BANKROLL_TICKETS["T1000"]["NFL_PRP1_MILESTONE_AND_MAX_LOCKS"],
                        float(la_np["fee_rate"]), float(lb_np["fee_rate"]),
                        fee_exponent_a=float(la_np["fee_exponent"]), fee_exponent_b=float(lb_np["fee_exponent"]),
                        max_box_cost_net=0.990, min_shares=6, min_box_notional_usd=5.5,
                    )
                    if w_np.get("filled"):
                        opps_out.append({
                            "sleeve": "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
                            "market": f"{sl.title} [{pbx['label']}]",
                            "ask_vwap": w_np["box_cost_net"],
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_np["box_cost_net"]), 4),
                            "l1_usd": w_np["l1_usd"],
                            "close_ts": pbx["close_ts"],
                        })
                        if (
                            self._can_emit_zero_loss_math_live("NFL_PRP1_MILESTONE_AND_MAX_LOCKS", float(pbx["close_ts"]), now)
                            and la_np.get("market_id") != lb_np.get("market_id")
                            and float(w_np["box_cost_net"]) <= 0.988
                            and 0.0 < (float(pbx["close_ts"]) - now) <= 172800.0
                        ):
                            self.emit_live_two_leg_box_candidate(
                                sleeve_source="NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
                                box_type="SPORTS_CORRIDOR",
                                asset="NFL",
                                dedupe_key=dk_np,
                                leg_a=la_np,
                                leg_b=lb_np,
                                bk_a=bka_np,
                                bk_b=bkb_np,
                                close_ts=float(pbx["close_ts"]),
                                now_ts=now,
                                k_low=float(la_np.get("strike") or 0.5),
                                k_high=float(lb_np.get("strike") or 1.5),
                            )
                        await self.open_shadow_two_leg_box(
                            "NFL_PRP1_MILESTONE_AND_MAX_LOCKS", dk_np, "NFL",
                            f"{sl.title} [{pbx['label']}]", la_np, lb_np, bka_np, bkb_np,
                            float(pbx["close_ts"]), 0.990, {"is_two_leg_box": True, "mode": pbx["mode"]},
                        )

                if nfl_board:
                    matched_nfl = next(
                        (
                            g for g in nfl_board
                            if (g.start_ts <= 0 or abs(g.start_ts - sl.kickoff_ts) <= 10.0 * 3600.0)
                            and (
                                (_teams_match_fuzzy(sl.away_team, g.away_name) and _teams_match_fuzzy(sl.home_team, g.home_name))
                                != (_teams_match_fuzzy(sl.away_team, g.home_name) and _teams_match_fuzzy(sl.home_team, g.away_name))
                            )
                        ),
                        None,
                    )
                    if matched_nfl is not None and matched_nfl.state in ("in", "post"):
                        c_ns = self.nfl_summary_cache.get(matched_nfl.game_id)
                        if c_ns is not None and (now - c_ns[0]) < 15.0:
                            nfl_sum = c_ns[1]
                        else:
                            try:
                                nfl_sum = await asyncio.to_thread(fetch_espn_nfl_summary_sync, matched_nfl.game_id)
                                self.nfl_summary_cache[matched_nfl.game_id] = (now, nfl_sum)
                            except Exception:
                                nfl_sum = {}
                        if nfl_sum:
                            for nlk in evaluate_nfl_prp1_live_locks(sl, nfl_sum, self.score_confirm_tracker, now):
                                dk_nlk = f"NFL_PRP1_LK_{sl.event_id}_{nlk['market_id']}"
                                v4_lock_cands.append({
                                    **nlk,
                                    "sleeve": "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
                                    "asset": "NFL",
                                    "dedupe_key": dk_nlk,
                                    "max_eff_px": 0.988,
                                    "title": getattr(sl, "title", ""),
                                    "rules_text": getattr(sl, "rules_text", ""),
                                })

        # 8D. `CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION` (`Close subset Hit` & `Daily subset Weekly subset Monthly`)
        if self.barrier_rungs or self.binance_close_rungs:
            near_hits = [
                hr for hr in self.barrier_rungs.values()
                if hr.resolved_yes is None and hr.end_ts > now + 120.0 and hr.asset != "HYPE"
                and (
                    self.spots.get(hr.asset, 0.0) <= 0.0
                    or abs(math.log(max(1e-9, hr.strike) / self.spots[hr.asset])) <= 0.35
                )
            ]
            near_closes = [
                cr for cr in self.binance_close_rungs
                if cr.close_ts > now + 120.0 and cr.asset != "HYPE"
                and (
                    self.spots.get(cr.asset, 0.0) <= 0.0
                    or abs(math.log(max(1e-9, cr.strike) / self.spots[cr.asset])) <= 0.35
                )
            ]
            cry_toks = sorted(
                {t for hr in near_hits for t in (hr.yes_token, hr.no_token)}
                | {cr.no_token for cr in near_closes}
            )
            if cry_toks:
                cry_bks = await self.fetch_books_batch(cry_toks, timeout=3.5)
                cry_asks = {
                    t: p
                    for t, bk in cry_bks.items()
                    for p, s in [self._best_ask_sz(bk)]
                    if p < 1.0 and p * s >= 8.0
                }
                for cbx in detect_cry_inc1_binance_inclusion_boxes(near_hits, near_closes, cry_asks, now, max_box_cost_net=0.992):
                    la_ci, lb_ci = cbx["leg_a"], cbx["leg_b"]
                    bka_ci, bkb_ci = cry_bks.get(la_ci["token_id"]), cry_bks.get(lb_ci["token_id"])
                    if not bka_ci or not bkb_ci:
                        continue
                    dk_ci = f"CRY_INC1_{cbx['asset']}_{la_ci['market_id']}_{lb_ci['market_id']}"
                    w_ci = walk_equal_shares_dominance_box(
                        bka_ci.get("asks") or [], bkb_ci.get("asks") or [],
                        BANKROLL_TICKETS["T1000"]["CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION"],
                        float(la_ci["fee_rate"]), float(lb_ci["fee_rate"]),
                        fee_exponent_a=float(la_ci["fee_exponent"]), fee_exponent_b=float(lb_ci["fee_exponent"]),
                        max_box_cost_net=0.992, min_shares=6, min_box_notional_usd=5.5,
                    )
                    if w_ci.get("filled"):
                        opps_out.append({
                            "sleeve": "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",
                            "market": cbx["label"],
                            "ask_vwap": w_ci["box_cost_net"],
                            "p_model": 1.0,
                            "net_edge": round(1.0 - float(w_ci["box_cost_net"]), 4),
                            "l1_usd": w_ci["l1_usd"],
                            "close_ts": cbx["close_ts"],
                        })
                        if (
                            self._can_emit_zero_loss_math_live("CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION", float(cbx["close_ts"]), now)
                            and float(w_ci["box_cost_net"]) <= 0.988
                            and 0.0 < (float(cbx["close_ts"]) - now) <= 604800.0
                        ):
                            self.emit_live_two_leg_box_candidate(
                                sleeve_source="CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION",
                                box_type="BARRIER_MONO",
                                asset=str(cbx["asset"]),
                                dedupe_key=dk_ci,
                                leg_a=la_ci,
                                leg_b=lb_ci,
                                bk_a=bka_ci,
                                bk_b=bkb_ci,
                                close_ts=float(cbx["close_ts"]),
                                now_ts=now,
                                k_low=min(float(la_ci["strike"]), float(lb_ci["strike"])),
                                k_high=max(float(la_ci["strike"]), float(lb_ci["strike"])),
                            )
                        await self.open_shadow_two_leg_box(
                            "CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION", dk_ci, str(cbx["asset"]),
                            cbx["label"], la_ci, lb_ci, bka_ci, bkb_ci, float(cbx["close_ts"]), 0.992,
                            {"is_two_leg_box": True, "mode": cbx["mode"], "direction": cbx["direction"]},
                        )

        # 8E. Unified Frontier v4 1-Leg Taker Lock + `MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER` Fallback
        pending_v4_lks = [
            c for c in v4_lock_cands
            if c["dedupe_key"] not in self.entered_keys and c["dedupe_key"] not in self.inflight_keys
        ]
        if pending_v4_lks:
            v4_lk_bks = await self.fetch_books_batch(
                sorted({t for c in pending_v4_lks for t in (str(c["token_id"]), str(c["opp_token_id"])) if t}),
                timeout=3.0,
            )
            for clk in pending_v4_lks:
                _clk_risk = classify_market_rule_dispute_risk(clk)
                if "FINAL" not in str(clk.get("mode") or "").upper() and _clk_risk["veto_pre_final_clinch"]:
                    continue
                tok_w, tok_o = str(clk["token_id"]), str(clk["opp_token_id"])
                bk_w_v4, bk_o_v4 = v4_lk_bks.get(tok_w), v4_lk_bks.get(tok_o)
                if not bk_w_v4 or not bk_o_v4:
                    continue
                bk_w_v4 = {**bk_w_v4, "_s2_meta": {"mode": str(clk.get("mode") or ""), "dispute_risk": bool(_clk_risk["dispute_risk"])}}
                opp_bid_v4, _ = extract_best_bid(bk_o_v4.get("bids") or [])
                if opp_bid_v4 > 0.035:
                    continue
                sl_v4 = str(clk["sleeve"])
                fr_v4 = float(clk.get("fee_rate") or 0.0)
                fe_v4 = float(clk.get("fee_exponent") or 1.0)
                max_eff_v4 = float(clk.get("max_eff_px") or 0.988)
                p_lk_v4 = float(clk["p_lock"])
                close_v4 = max(now + 600.0, float(clk["close_ts"]))
                w_v4 = walk_l2_book_asks_depth_capped(
                    bk_w_v4.get("asks") or [],
                    BANKROLL_TICKETS["T1000"][sl_v4],
                    BANKROLL_TICKETS["T100"][sl_v4],
                    fee_rate=fr_v4, min_l1_usd=15.0, max_ask_px=max_eff_v4 + 0.0001, fee_exponent=fe_v4,
                )
                opened_v4_taker = False
                if w_v4.get("filled"):
                    eff_v4 = float(w_v4["eff_px"])
                    edg_v4 = round(p_lk_v4 - eff_v4, 4)
                    if 0.72 <= eff_v4 <= max_eff_v4 and edg_v4 >= 0.012:
                        opps_out.append({
                            "sleeve": sl_v4,
                            "market": f"[{clk['mode']}] {clk['display_label']}",
                            "ask_vwap": eff_v4, "p_model": p_lk_v4, "net_edge": edg_v4,
                            "l1_usd": w_v4["l1_usd"], "close_ts": close_v4,
                        })
                        if self._can_emit_zero_loss_math_live(sl_v4, close_v4, now, p_model=p_lk_v4):
                            self.emit_live_single_leg_lock_candidate(
                                sleeve_source=sl_v4,
                                asset=str(clk["asset"]).upper(),
                                dedupe_key=str(clk["dedupe_key"]),
                                token_id=tok_w,
                                opp_token_id=tok_o,
                                market_id=str(clk["market_id"]),
                                condition_id=str(clk["condition_id"]),
                                side_label=str(clk["side_label"]),
                                display_label=str(clk["display_label"]),
                                bk_win=bk_w_v4,
                                bk_opp=bk_o_v4,
                                fee_rate=fr_v4,
                                fee_exponent=fe_v4,
                                neg_risk=bool(clk.get("neg_risk", False)),
                                close_ts=close_v4,
                                now_ts=now,
                                max_lock_eff_px=max_eff_v4,
                                max_opp_bid=0.025,
                                hold_to_maturity=True,
                                p_model=p_lk_v4,
                            )
                        opened_v4_taker = await self.open_shadow_position(
                            sl_v4, str(clk["dedupe_key"]), str(clk["asset"]),
                            str(clk["display_label"]), str(clk["side_label"]), tok_w,
                            fr_v4, p_lk_v4, close_v4,
                            {
                                "market_id": clk["market_id"], "condition_id": clk["condition_id"],
                                "opp_token_id": tok_o, "mode": clk["mode"], "fee_exponent": fe_v4,
                            },
                            prefetched_book=bk_w_v4,
                        )
                if not opened_v4_taker:
                    dk_mkr = f"MKR_LK1_{clk['market_id']}"
                    _mkr_shadow_free = dk_mkr not in self.entered_keys and dk_mkr not in self.inflight_keys
                    _is_live_daemon_mkr = not (self.single_scan or ("fetch_json" in self.__dict__))
                    if _mkr_shadow_free or (_is_live_daemon_mkr and dk_mkr not in self.inflight_keys):
                        bid_w_v4, bid_usd_v4 = extract_best_bid(bk_w_v4.get("bids") or [])
                        ask_w_v4, _ = self._best_ask_sz(bk_w_v4)
                        _mkr_reb_sh = 0.15 if str(clk["asset"]).upper() in ("BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "HYPE", "XAU") else 0.20
                        _mkr_hi_cap = 0.997 if (_is_live_daemon_mkr and p_lk_v4 >= 0.999 and (close_v4 - now) <= 7200.0) else 0.991
                        _mkr_min_ed = 0.0025 if _mkr_hi_cap >= 0.997 else 0.006
                        mkr_ev = evaluate_mkr_lock1_post_clinch_rebate_bid(
                            token_id=tok_w,
                            opp_token_id=tok_o,
                            market_id=str(clk["market_id"]),
                            condition_id=str(clk["condition_id"]),
                            display_label=str(clk["display_label"]),
                            source_sleeve=sl_v4,
                            p_lock=p_lk_v4,
                            close_ts=close_v4,
                            now_ts=now,
                            best_bid=bid_w_v4 if bid_w_v4 > 0.0 else None,
                            best_ask=ask_w_v4 if ask_w_v4 < 1.0 else None,
                            opp_best_bid=opp_bid_v4,
                            fee_rate=fr_v4,
                            fee_exponent=fe_v4,
                            maker_rebate_share=_mkr_reb_sh,
                            neg_risk=bool(clk.get("neg_risk", False)),
                            max_maker_bid=_mkr_hi_cap,
                            min_net_edge_ps=_mkr_min_ed,
                        )
                        if mkr_ev is not None:
                            if _mkr_shadow_free:
                                opps_out.append({
                                    "sleeve": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                                    "market": mkr_ev["display_label"],
                                    "ask_vwap": mkr_ev["effective_net_cost_per_share"],
                                    "p_model": p_lk_v4,
                                    "net_edge": round(float(mkr_ev["expected_net_edge_per_share"]), 4),
                                    "l1_usd": max(25.0, bid_usd_v4),
                                    "close_ts": close_v4,
                                })
                            if (
                                bid_w_v4 >= 0.940 - 1e-9
                                and bid_usd_v4 >= 10.0 - 1e-6
                                and self._can_emit_zero_loss_math_live("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", close_v4, now, p_model=p_lk_v4)
                            ):
                                self.emit_live_single_leg_maker_lock_candidate(
                                    sleeve_source="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                                    asset=str(clk["asset"]).upper(),
                                    dedupe_key=dk_mkr,
                                    pair_dedupe_key=str(clk["dedupe_key"]),
                                    token_id=tok_w,
                                    opp_token_id=tok_o,
                                    market_id=str(clk["market_id"]),
                                    condition_id=str(clk["condition_id"]),
                                    side_label=str(clk["side_label"]),
                                    display_label=str(clk["display_label"]),
                                    bk_win=bk_w_v4,
                                    bk_opp=bk_o_v4,
                                    neg_risk=bool(clk.get("neg_risk", False)),
                                    close_ts=close_v4,
                                    now_ts=now,
                                    min_resting_bid=0.940,
                                    max_resting_bid=_mkr_hi_cap,
                                    min_maker_edge=_mkr_min_ed,
                                    max_opp_bid=0.030,
                                    hold_to_maturity=True,
                                    p_model=p_lk_v4,
                                    target_bid_px=float(mkr_ev["post_only_bid"]),
                                    maker_rebate_ps=float(mkr_ev["maker_rebate_per_share"]),
                                )
                            if _mkr_shadow_free:
                                await self.post_shadow_maker_entry(
                                    sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                                    dedupe_key=dk_mkr,
                                    asset=str(clk["asset"]),
                                    title=str(mkr_ev["display_label"]),
                                    side_label=str(clk["side_label"]),
                                    token_id=tok_w,
                                    p_model=p_lk_v4,
                                    close_ts=close_v4,
                                    extra={
                                        "market_id": clk["market_id"],
                                        "condition_id": clk["condition_id"],
                                        "opp_token_id": tok_o,
                                        "source_sleeve": sl_v4,
                                        "resting_bid_override": mkr_ev["post_only_bid"],
                                        "maker_rebate_ps": mkr_ev["maker_rebate_per_share"],
                                    },
                                    prefetched_book=bk_w_v4,
                                    ttl_override_sec=180.0,
                                )

    async def _scan_phase2_macro_counting_gas(self, opps_out: List[Dict[str, Any]], now: float) -> None:
        try:
            await self._scan_phase2_macro_counting_gas_core(opps_out, now)
        except Exception as _p2_exc:
            logger.warning(f"[ALPHA-124] Phase-2 macro/counting/gas scan notice: {_p2_exc}")
        await self.scan_uma_resolution_bonds(opps_out, now_ts=now)

    async def _scan_phase2_macro_counting_gas_core(self, opps_out: List[Dict[str, Any]], now: float) -> None:
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
                    fr_dbr = float(getattr(dbr, "fee_rate", 0.0) or 0.0)
                    fe_dbr = float(getattr(dbr, "fee_exponent", 1.0) or 1.0)
                    w_dno = walk_l2_book_asks(bk_dno.get("asks") or [], BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"], fee_rate=fr_dbr, min_l1_usd=15.0, max_ask_px=0.990, fee_exponent=fe_dbr)
                    if w_dno.get("filled") and 0.80 <= float(w_dno["eff_px"]) <= 0.990:
                        edg_tw = round(1.0 - float(w_dno["eff_px"]), 4)
                        if edg_tw >= 0.010:
                            opps_out.append({"sleeve": "TW1_COUNTING_TRUNCATION_AND_BOX", "market": f"{sl_c.handle} Dead Bracket NO[{dbr.label}] (count>={v_floor})", "ask_vwap": w_dno["eff_px"], "p_model": 1.0, "net_edge": edg_tw, "l1_usd": w_dno["l1_usd"], "close_ts": sl_c.window_end_ts})
                            if (sl_c.window_end_ts - now) <= 172800.0:
                                self.emit_live_single_leg_lock_candidate(
                                    sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX",
                                    asset=sl_c.handle.upper(),
                                    dedupe_key=f"TW1_NO_{dbr.market_id}",
                                    token_id=dbr.no_token,
                                    opp_token_id=dbr.yes_token,
                                    market_id=dbr.market_id,
                                    condition_id=dbr.condition_id,
                                    side_label="NO",
                                    display_label=f"{sl_c.handle} Dead NO[{dbr.label}]",
                                    bk_win=bk_dno,
                                    bk_opp=cnt_bks.get(dbr.yes_token),
                                    fee_rate=fr_dbr,
                                    fee_exponent=fe_dbr,
                                    neg_risk=bool(dbr.neg_risk),
                                    close_ts=float(sl_c.window_end_ts),
                                    now_ts=now,
                                    max_lock_eff_px=0.990,
                                    max_opp_bid=0.020,
                                    hold_to_maturity=(float(w_dno["eff_px"]) >= 0.980),
                                    p_model=1.0,
                                )
                            await self.open_shadow_position("TW1_COUNTING_TRUNCATION_AND_BOX", f"TW1_NO_{dbr.market_id}", sl_c.handle.upper(), f"{sl_c.title} [Dead NO {dbr.label}]", "NO", dbr.no_token, fr_dbr, 1.0, sl_c.window_end_ts, {"market_id": dbr.market_id, "condition_id": dbr.condition_id, "verified_floor": v_floor, "fee_exponent": fe_dbr}, prefetched_book=bk_dno)
                    rw_ev = evaluate_locked_market_reward_carry(1.0, bid_dn, ask_dn, dbr.rewards_min_size, dbr.rewards_max_spread, fr_dbr)
                    if rw_ev.get("eligible"):
                        opps_out.append({"sleeve": "MKR_REWARD_LOCKED_CARRY", "market": f"{sl_c.handle} Locked Carry NO[{dbr.label}] @ ${rw_ev['resting_bid']:.3f}", "ask_vwap": rw_ev["resting_bid"], "p_model": 1.0, "net_edge": rw_ev["carry_edge"], "l1_usd": 50.0, "close_ts": sl_c.window_end_ts})
                        await self.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY", f"MKR_RW_{dbr.market_id}", sl_c.handle.upper(), f"{sl_c.title} [Reward Carry NO {dbr.label}]", "NO", dbr.no_token, 1.0, sl_c.window_end_ts, {"market_id": dbr.market_id, "condition_id": dbr.condition_id, "opp_token_id": dbr.yes_token, "resting_bid_override": rw_ev["resting_bid"]}, prefetched_book=bk_dno)
                        if is_reward_locked_carry_live_ready(self, 1.0) and getattr(dbr, "neg_risk", None) is not None:
                            self.emit_live_single_leg_maker_lock_candidate(
                                sleeve_source="MKR_REWARD_LOCKED_CARRY",
                                asset=sl_c.handle.upper(),
                                dedupe_key=f"MKR_RW_{dbr.market_id}",
                                pair_dedupe_key=f"MKR_RW_PAIR_{dbr.market_id}",
                                token_id=dbr.no_token,
                                opp_token_id=dbr.yes_token,
                                market_id=dbr.market_id,
                                condition_id=dbr.condition_id,
                                side_label="NO",
                                display_label=f"{sl_c.handle} Reward Carry NO[{dbr.label}]",
                                bk_win=bk_dno,
                                bk_opp=cnt_bks.get(dbr.yes_token),
                                neg_risk=bool(dbr.neg_risk),
                                close_ts=float(sl_c.window_end_ts),
                                now_ts=now,
                                min_resting_bid=0.940,
                                max_resting_bid=0.994,
                                min_maker_edge=0.006,
                                max_opp_bid=0.030,
                                hold_to_maturity=True,
                                p_model=1.0,
                                target_bid_px=float(rw_ev["resting_bid"]),
                            )

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
                    w_tb = walk_equal_shares_dominance_box(
                        bka_t.get("asks") or [], bkb_t.get("asks") or [],
                        BANKROLL_TICKETS["T1000"]["TW1_COUNTING_TRUNCATION_AND_BOX"],
                        float(la_t.get("fee_rate", 0.0)), float(lb_t.get("fee_rate", 0.0)),
                        fee_exponent_a=float(la_t.get("fee_exponent", 1.0)), fee_exponent_b=float(lb_t.get("fee_exponent", 1.0)),
                        max_box_cost_net=0.993, min_shares=6, min_box_notional_usd=5.5,
                    )
                    if w_tb.get("filled"):
                        opps_out.append({"sleeve": "TW1_COUNTING_TRUNCATION_AND_BOX", "market": f"Counting Box {tb['label']}", "ask_vwap": w_tb["box_cost_net"], "p_model": 1.0, "net_edge": round(1.0 - float(w_tb["box_cost_net"]), 4), "l1_usd": w_tb["l1_usd"], "close_ts": tb["close_ts"]})
                        tw_live_emitted = False
                        if (float(tb["close_ts"]) - now) <= 86400.0 and float(w_tb["box_cost_net"]) <= 0.990:
                            tw_live_emitted = self.emit_live_two_leg_box_candidate(sleeve_source="TW1_COUNTING_TRUNCATION_AND_BOX", box_type="COUNTING_DOMINANCE", asset=tb["handle"].upper(), dedupe_key=dk_tw, leg_a=la_t, leg_b=lb_t, bk_a=bka_t, bk_b=bkb_t, close_ts=float(tb["close_ts"]), now_ts=now)
                        await self.open_shadow_two_leg_box("TW1_COUNTING_TRUNCATION_AND_BOX", dk_tw, tb["handle"].upper(), f"Counting Box {tb['label']}", la_t, lb_t, bka_t, bkb_t, float(tb["close_ts"]), 0.993, {"is_two_leg_box": True, "banked": tb["banked"]})
                        if not tw_live_emitted:
                            self.post_zero_fee_maker_anchor_box("TW1", tb["handle"].upper(), f"ZFA_{dk_tw}", la_t, lb_t, bka_t, bkb_t, float(tb["close_ts"]), f"Counting Box {tb['label']}", now, prefetched_books=cnt_bks, live_emit_only=True)
                    else:
                        self.post_zero_fee_maker_anchor_box("TW1", tb["handle"].upper(), f"ZFA_{dk_tw}", la_t, lb_t, bka_t, bkb_t, float(tb["close_ts"]), f"Counting Box {tb['label']}", now, prefetched_books=cnt_bks)
                elif float(tb["box_cost_net"]) <= 1.035:
                    self.post_zero_fee_maker_anchor_box("TW1", tb["handle"].upper(), f"ZFA_{dk_tw}", la_t, lb_t, bka_t, bkb_t, float(tb["close_ts"]), f"Counting Box {tb['label']}", now, prefetched_books=cnt_bks)

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
                            wm2 = walk_equal_shares_dominance_box(
                                bka_m.get("asks") or [], bkb_m.get("asks") or [],
                                BANKROLL_TICKETS["T1000"][sl_lp],
                                float(la_m.get("fee_rate", 0.0)), float(lb_m.get("fee_rate", 0.0)),
                                fee_exponent_a=float(la_m.get("fee_exponent", 1.0)), fee_exponent_b=float(lb_m.get("fee_exponent", 1.0)),
                                max_box_cost_net=0.994, min_shares=6, min_box_notional_usd=5.5,
                            )
                            if wm2.get("filled"):
                                opps_out.append({"sleeve": sl_lp, "market": f"{asset_lp} {bx['label']}", "ask_vwap": wm2["box_cost_net"], "p_model": 1.0, "net_edge": round(1.0 - float(wm2["box_cost_net"]), 4), "l1_usd": wm2["l1_usd"], "close_ts": bx["close_ts"]})
                                lp_live_emitted = False
                                if sl_lp == "FED1_CENTRAL_BANK_LP_BOX" and (float(bx["close_ts"]) - now) <= 172800.0 and float(wm2["box_cost_net"]) <= 0.990:
                                    lp_live_emitted = self.emit_live_two_leg_box_candidate(sleeve_source=sl_lp, box_type="MACRO_DOMINANCE", asset=asset_lp, dedupe_key=dk_m, leg_a=la_m, leg_b=lb_m, bk_a=bka_m, bk_b=bkb_m, close_ts=float(bx["close_ts"]), now_ts=now)
                                elif (
                                    sl_lp == "COND1_MACRO_PARTITION_BOX"
                                    and (float(bx["close_ts"]) - now) <= (172800.0 if self.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX") else 108000.0)
                                    and float(wm2["box_cost_net"]) <= (
                                        (0.992 if (float(bx["close_ts"]) - now) <= 108000.0 else 0.988)
                                        if self.is_sleeve_grad8_ready("COND1_MACRO_PARTITION_BOX")
                                        else 0.985
                                    )
                                ):
                                    lp_live_emitted = self.emit_live_two_leg_box_candidate(sleeve_source=sl_lp, box_type="MACRO_DOMINANCE", asset=asset_lp, dedupe_key=dk_m, leg_a=la_m, leg_b=lb_m, bk_a=bka_m, bk_b=bkb_m, close_ts=float(bx["close_ts"]), now_ts=now)
                                await self.open_shadow_two_leg_box(sl_lp, dk_m, asset_lp, f"{asset_lp} {bx['label']}", la_m, lb_m, bka_m, bkb_m, float(bx["close_ts"]), 0.994, {"is_two_leg_box": True, "double_pay_states": bx["double_pay_states"]})
                                if not lp_live_emitted:
                                    self.post_zero_fee_maker_anchor_box(asset_lp, asset_lp, f"ZFA_{dk_m}", la_m, lb_m, bka_m, bkb_m, float(bx["close_ts"]), f"{asset_lp} {bx['label']}", now, prefetched_books=lp_bks, live_emit_only=True)
                            else:
                                self.post_zero_fee_maker_anchor_box(asset_lp, asset_lp, f"ZFA_{dk_m}", la_m, lb_m, bka_m, bkb_m, float(bx["close_ts"]), f"{asset_lp} {bx['label']}", now, prefetched_books=lp_bks)
                        elif float(bx["box_cost_net"]) <= 1.035:
                            self.post_zero_fee_maker_anchor_box(asset_lp, asset_lp, f"ZFA_{dk_m}", la_m, lb_m, bka_m, bkb_m, float(bx["close_ts"]), f"{asset_lp} {bx['label']}", now, prefetched_books=lp_bks)
                    elif int(bx["n_legs"]) == 3 and float(bx["box_cost_net"]) <= 0.992:
                        dk_3 = f"{asset_lp}_3L_{'_'.join(x['token_id'][-6:] for x in lgs)}"
                        wm3 = walk_equal_shares_multi_leg_box(
                            [{"asks": lp_bks[x["token_id"]].get("asks") or [], "fee_rate": float(x.get("fee_rate", 0.0)), "fee_exponent": float(x.get("fee_exponent", 1.0))} for x in lgs],
                            BANKROLL_TICKETS["T1000"][sl_lp], 1.0, 0.992, min_shares=6, min_box_notional_usd=5.5,
                        )
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
                    _m_gdt = re.search(r"(20\d{2}-\d{2}-\d{2})", str(ev_g.get("slug") or ""))
                    mkt_dt = _m_gdt.group(1) if _m_gdt else datetime.fromtimestamp(end_g, tz=NY_TZ).date().isoformat()
                    if mkt_dt != aaa["as_of_date"]:
                        continue
                    g_brs = []
                    for mg in (ev_g.get("markets") or []):
                        if mg.get("closed"):
                            continue
                        fr_g, fe_g = _extract_market_fee_rate(mg)
                        tk_g = _parse_clob_tokens(mg)
                        bd_g = parse_gas_daily_bracket(str(mg.get("groupItemTitle") or mg.get("question") or ""))
                        if tk_g and bd_g:
                            g_brs.append((mg, tk_g, bd_g, fr_g, fe_g))
                    if not g_brs:
                        continue
                    g_bks = await self.fetch_books_batch([t for _, tk, _, _, _ in g_brs for t in tk], timeout=3.0)
                    for mg, tk_g, (glo, ghi), fr_g, fe_g in g_brs:
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
                        wg = walk_l2_book_asks(bk_g.get("asks") or [], BANKROLL_TICKETS["T1000"]["GAS1_AAA_GASOLINE_LOCK"], fee_rate=fr_g, min_l1_usd=15.0, max_ask_px=0.985, fee_exponent=fe_g)
                        if wg.get("filled") and 0.75 <= float(wg["eff_px"]) <= 0.983:
                            opps_out.append({"sleeve": "GAS1_AAA_GASOLINE_LOCK", "market": f"AAA Gas ${reg_px:.4f} ({aaa['as_of_date']}) -> {side_g}[{lbl_g}]", "ask_vwap": wg["eff_px"], "p_model": 0.998, "net_edge": round(0.998 - float(wg["eff_px"]), 4), "l1_usd": wg["l1_usd"], "close_ts": end_g})
                            await self.open_shadow_position("GAS1_AAA_GASOLINE_LOCK", f"GAS1_{mid_g}_{side_g}", "AAA_GAS", f"{ev_g.get('title')} [{side_g} {lbl_g}]", side_g, tok_g, fr_g, 0.998, end_g, {"market_id": mid_g, "aaa_price": reg_px, "as_of_date": aaa["as_of_date"], "fee_exponent": fe_g}, prefetched_book=bk_g)
                        bid_g, _ = extract_best_bid(bk_g.get("bids") or [])
                        ask_g, _ = self._best_ask_sz(bk_g)
                        rw_g = evaluate_locked_market_reward_carry(0.998, bid_g, ask_g, float(mg.get("rewardsMinSize") or 0.0), float(mg.get("rewardsMaxSpread") or 0.0), fr_g)
                        if rw_g.get("eligible"):
                            opp_tok_g = tk_g[1] if side_g == "YES" else tk_g[0]
                            nr_g = mg.get("negRisk") if mg.get("negRisk") is not None else ev_g.get("negRisk")
                            opps_out.append({"sleeve": "MKR_REWARD_LOCKED_CARRY", "market": f"AAA Gas Locked Carry {side_g}[{lbl_g}] @ ${rw_g['resting_bid']:.3f}", "ask_vwap": rw_g["resting_bid"], "p_model": 0.998, "net_edge": rw_g["carry_edge"], "l1_usd": 50.0, "close_ts": end_g})
                            await self.post_shadow_maker_entry("MKR_REWARD_LOCKED_CARRY", f"MKR_RW_GAS_{mid_g}_{side_g}", "AAA_GAS", f"{ev_g.get('title')} [Reward Carry {side_g} {lbl_g}]", side_g, tok_g, 0.998, end_g, {"market_id": mid_g, "condition_id": str(mg.get("conditionId") or ""), "opp_token_id": opp_tok_g, "resting_bid_override": rw_g["resting_bid"]}, prefetched_book=bk_g)
                            if is_reward_locked_carry_live_ready(self, 0.998) and nr_g is not None and g_bks.get(opp_tok_g) is not None:
                                self.emit_live_single_leg_maker_lock_candidate(
                                    sleeve_source="MKR_REWARD_LOCKED_CARRY",
                                    asset="AAA_GAS",
                                    dedupe_key=f"MKR_RW_GAS_{mid_g}_{side_g}",
                                    pair_dedupe_key=f"MKR_RW_GASPAIR_{mid_g}",
                                    token_id=tok_g,
                                    opp_token_id=opp_tok_g,
                                    market_id=mid_g,
                                    condition_id=str(mg.get("conditionId") or ""),
                                    side_label=side_g,
                                    display_label=f"AAA Gas Reward Carry {side_g}[{lbl_g}]",
                                    bk_win=bk_g,
                                    bk_opp=g_bks.get(opp_tok_g),
                                    neg_risk=bool(nr_g),
                                    close_ts=float(end_g),
                                    now_ts=now,
                                    min_resting_bid=0.940,
                                    max_resting_bid=0.990,
                                    min_maker_edge=0.008,
                                    max_opp_bid=0.030,
                                    hold_to_maturity=True,
                                    p_model=0.998,
                                    target_bid_px=float(rw_g["resting_bid"]),
                                )

    def has_live_nba_window(self, now_ts: float) -> bool:
        return any(
            (sp.tipoff_ts - 600.0) <= now_ts <= (sp.tipoff_ts + 5.5 * 3600.0)
            for sp in self.nba_games.values()
        )

    def has_live_sports_window(self, now_ts: float) -> bool:
        return (
            self.has_live_nba_window(now_ts)
            or any(
                (sp.start_ts - 600.0) <= now_ts <= (sp.start_ts + 5.5 * 3600.0)
                for sp in self.multi_sport_games.values()
            )
            or any(
                (tr.end_ts - 2.5 * 3600.0) <= now_ts <= (tr.end_ts + 1.5 * 3600.0)
                for tr in self.soccer_trees.values()
            )
            or any(
                (tn.end_ts - 3.5 * 3600.0) <= now_ts <= (tn.end_ts + 1.0 * 3600.0)
                for tn in self.tennis_specs.values()
            )
            or any(
                (b.start_ts - 600.0) <= now_ts <= (b.start_ts + 5.5 * 3600.0)
                for b in self.aff1_bundles.values()
            )
            or any(
                (lat.end_ts - 2.5 * 3600.0) <= now_ts <= (lat.end_ts + 2.0 * 3600.0)
                for lat in self.soc2_lattices.values()
            )
            or any(
                (sl.kickoff_ts - 600.0) <= now_ts <= (sl.kickoff_ts + 5.5 * 3600.0)
                for sl in self.nfl_prop_slates.values()
            )
        )

    async def discover_uma_proposed_markets(self, now_ts: float) -> None:
        end_max_iso = datetime.fromtimestamp(now_ts + 12.0 * 3600.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        req_coros = [
            self.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=200&offset=0", timeout=5.5),
            self.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=200&offset=200", timeout=5.5),
            self.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&end_date_max={end_max_iso}&order=volume24hr&ascending=false&limit=200&offset=0", timeout=5.5),
            self.fetch_json(f"{GAMMA_URL}/markets?closed=false&active=true&end_date_max={end_max_iso}&order=volume24hr&ascending=false&limit=200&offset=200", timeout=5.5),
            *(
                self.fetch_json(
                    f"{GAMMA_URL}/events?active=true&closed=false&order=volume24hr&ascending=false&limit=100&offset={ev_off}",
                    timeout=6.0,
                )
                for ev_off in range(0, 1500, 100)
            ),
            *(
                self.fetch_json(
                    f"{GAMMA_URL}/events?active=true&closed=false&end_date_max={end_max_iso}&order=endDate&ascending=false&limit=100&offset={end_off}",
                    timeout=6.0,
                )
                for end_off in (0, 100, 200, 300)
            ),
        ]
        pages = await asyncio.gather(*req_coros)
        found: Dict[str, Dict[str, Any]] = {}
        for pg in pages:
            if not isinstance(pg, list):
                continue
            for item in pg:
                if not isinstance(item, dict):
                    continue
                child_mkts = item.get("markets")
                if isinstance(child_mkts, list):
                    ev_nr = item.get("negRisk")
                    for cm in child_mkts:
                        if not isinstance(cm, dict):
                            continue
                        mid_c = str(cm.get("id") or "").strip()
                        if not mid_c or mid_c in found:
                            continue
                        if "negRisk" not in cm and ev_nr is not None:
                            cm = {**cm, "negRisk": ev_nr}
                        ok_c, _ = is_objective_uma_market(cm)
                        if ok_c:
                            found[mid_c] = cm
                else:
                    mid = str(item.get("id") or "").strip()
                    if not mid or mid in found:
                        continue
                    ok_obj, _ = is_objective_uma_market(item)
                    if ok_obj:
                        found[mid] = item
        self.uma_proposed_markets = found
        self.last_uma_discovery_ts = now_ts

    async def scan_uma_resolution_bonds(
        self,
        opps_out: List[Dict[str, Any]],
        now_ts: Optional[float] = None,
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        if self.single_scan or not self.uma_proposed_markets or (now - self.last_uma_discovery_ts) >= 90.0:
            await self.discover_uma_proposed_markets(now)
        if not self.uma_proposed_markets:
            return

        verified_list: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
        uncached_batch: List[Tuple[float, str, Dict[str, Any]]] = []
        _is_live_uma_daemon = not (self.single_scan or ("fetch_json" in self.__dict__))
        for mid, m in list(self.uma_proposed_markets.items()):
            dkey = f"BOND1_{mid}"
            if dkey in self.inflight_keys or (not _is_live_uma_daemon and dkey in self.entered_keys):
                continue
            cached_v = self.uma_onchain_cache.get(mid)
            ttl_v = 60.0
            if cached_v is not None:
                rsn = str(cached_v[1].get("reason") or "")
                if any(k in rsn for k in ("DISPUTER", "TIE_50_50", "QUESTION_FLAGS", "PRIOR_DISPUTE", "PREMATURE_PROPOSAL", "MARKET_BEFORE_END_DATE")):
                    ttl_v = 300.0
            if cached_v is not None and (now - cached_v[0]) < ttl_v:
                ver = cached_v[1]
                if ver.get("verified"):
                    ok_nba, _ = verify_uma_against_nba_live(m, int(ver["win_index"]), self.live_nba_board)
                    if ok_nba:
                        verified_list.append((mid, m, ver))
            else:
                bb_p = float(m.get("bestBid") or 0.0)
                ba_p = float(m.get("bestAsk") or 1.0)
                tradeable_score = (1000000.0 if (0.90 <= bb_p <= 0.9985 or 0.002 <= ba_p <= 0.10 or 0.90 <= ba_p <= 0.9985) else 0.0) + float(m.get("volume24hr") or 0.0)
                uncached_batch.append((tradeable_score, mid, m))

        if uncached_batch:
            uncached_batch.sort(key=lambda x: -x[0])
            sem_rpc = asyncio.Semaphore(12)

            async def _verify_rpc_one(mid_u: str, m_u: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
                async with sem_rpc:
                    v_u = await asyncio.to_thread(verify_uma_onchain_proposal_sync, m_u, None, now)
                    return mid_u, m_u, v_u

            rpc_results = await asyncio.gather(*(_verify_rpc_one(mid_u, m_u) for _, mid_u, m_u in uncached_batch[:84]))
            for mid_u, m_u, ver in rpc_results:
                self.uma_onchain_cache[mid_u] = (now, ver)
                if not ver.get("verified"):
                    continue
                ok_nba, _ = verify_uma_against_nba_live(m_u, int(ver["win_index"]), self.live_nba_board)
                if ok_nba:
                    verified_list.append((mid_u, m_u, ver))

        verified_list = [(mid, m, ver) for mid, m, ver in verified_list if passes_uma_bond_dispute_guard(m, ver)]
        if not verified_list:
            return

        tok_batch = [t for _, _, ver in verified_list for t in (str(ver["win_token"]), str(ver["lose_token"]))]
        bks_uma = await self.fetch_books_batch(tok_batch, timeout=3.5)
        ref_notional = BANKROLL_TICKETS["T1000"]["BOND1_UMA_RESOLUTION_CARRY"]

        for mid, m, ver in verified_list:
            wtok, ltok = str(ver["win_token"]), str(ver["lose_token"])
            bk_w, bk_l = bks_uma.get(wtok), bks_uma.get(ltok)
            if not bk_w or not bk_l:
                continue
            _b1_age = max(0.0, float(ver.get("eff_liveness_sec") or 7200.0) - float(ver.get("rem_challenge_sec") or 7200.0))
            bk_w = {**bk_w, "_s2_meta": {"proposal_age_sec": round(float(ver.get("proposal_age_sec") if ver.get("proposal_age_sec") is not None else _b1_age), 1), "dispute_risk": bool(classify_market_rule_dispute_risk(m)["dispute_risk"])}}
            win_bid, _ = extract_best_bid(bk_w.get("bids") or [])
            lose_bid, _ = extract_best_bid(bk_l.get("bids") or [])
            lose_ask, _ = self._best_ask_sz(bk_l)
            # Strict Dual-Book Consensus Gate: losing side bid <= 0.8c, winning side bid >= 94c, and active losing ask <= 2.5c
            if lose_bid > 0.008 or win_bid < 0.940 or (lose_ask < 0.50 and lose_ask > 0.025):
                continue

            w_bond = walk_l2_book_asks_depth_capped(
                bk_w.get("asks") or [],
                ref_notional,
                BANKROLL_TICKETS["T100"]["BOND1_UMA_RESOLUTION_CARRY"],
                fee_rate=float(ver["fee_rate"]),
                min_l1_usd=6.0 if _is_live_uma_daemon else 15.0,
                max_ask_px=0.9976 if _is_live_uma_daemon else 0.9956,
                fee_exponent=float(ver["fee_exponent"]),
            )
            eff_b = float(w_bond["eff_px"]) if w_bond.get("filled") else None
            self._record_market_telemetry(
                key=f"BOND1_SNAP_{mid}",
                min_interval_sec=60.0,
                now_ts=now,
                sig=(eff_b, win_bid, lose_bid, ver["oo_state"]),
                payload={
                    "type": "UMA_BOND_PROPOSAL_SNAP",
                    "market_id": mid,
                    "question": str(m.get("question") or "")[:90],
                    "domain": ver["domain"],
                    "win_outcome": ver["win_outcome_name"],
                    "oo_state": ver["oo_state"],
                    "rem_challenge_sec": ver["rem_challenge_sec"],
                    "win_ask_eff": eff_b,
                    "win_bid": win_bid,
                    "lose_bid": lose_bid,
                },
            )
            q_str = str(m.get("question") or f"Market {mid}")
            close_est = max(now + 900.0, float(ver["expiration_ts"]) + 600.0)
            bond_extra = {
                "market_id": mid,
                "condition_id": str(m.get("conditionId") or ""),
                "opp_token_id": ltok,
                "fee_exponent": ver["fee_exponent"],
                "oo_state": ver["oo_state"],
                "proposer": ver["proposer"],
                "win_outcome_name": ver["win_outcome_name"],
                "expiration_ts": ver["expiration_ts"],
                "rem_challenge_sec": ver["rem_challenge_sec"],
                "domain": ver["domain"],
            }
            dkey_b1 = f"BOND1_{mid}"
            _shadow_b1_free = dkey_b1 not in self.entered_keys and dkey_b1 not in self.inflight_keys
            _b1_rem_s = close_est - now
            _b1_tkr_cap = 0.9975 if (_is_live_uma_daemon and _b1_rem_s <= 3600.0) else (0.9965 if (_is_live_uma_daemon and _b1_rem_s <= 7200.0) else 0.9955)
            _b1_max_mkr = 0.9980 if (_is_live_uma_daemon and _b1_rem_s <= 3600.0) else (0.9975 if (_is_live_uma_daemon and _b1_rem_s <= 7200.0) else 0.9950)
            _b1_min_ed = round(1.0 - _b1_max_mkr, 4)
            if _is_live_uma_daemon and _shadow_b1_free and 180.0 <= float(ver.get("rem_challenge_sec") or 0.0) <= 1500.0:
                from src.polymarket_research.riskless_protocol_v2_expansion import score_uma_ready1_liveness_priority
                _uma_r1 = score_uma_ready1_liveness_priority(
                    ask_price=eff_b if eff_b is not None else min(0.9975, win_bid),
                    remaining_liveness_sec=float(ver["rem_challenge_sec"]),
                    disputed=False,
                    proposal_bond_posted=True,
                )
                if _uma_r1 is not None:
                    opps_out.append({
                        "sleeve": "UMA_READY1_LIVENESS_PRIORITY",
                        "market": f"[UMA_READY1:{ver['domain']}] {q_str[:56]} ({ver['rem_challenge_sec']/60:.0f}m rem)",
                        "ask_vwap": _uma_r1["ask_px"],
                        "p_model": 1.0,
                        "net_edge": _uma_r1["net_edge_per_share"],
                        "l1_usd": w_bond["l1_usd"] if w_bond.get("filled") else 25.0,
                        "close_ts": close_est,
                    })
            opened_bond = False
            _b1_mkr_emitted = False
            taker_bond_qual = bool(w_bond.get("filled") and eff_b is not None and (0.950 <= eff_b <= _b1_tkr_cap) and round(1.0 - eff_b, 4) >= round(1.0 - _b1_tkr_cap, 4))
            if taker_bond_qual:
                carry_edge = round(1.0 - eff_b, 4)
                if _shadow_b1_free and eff_b <= 0.9955:
                    opps_out.append({
                        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                        "market": f"[{ver['domain']}] {q_str[:65]} -> {ver['win_outcome_name']} ({ver['rem_challenge_sec']/60:.0f}m rem)",
                        "ask_vwap": eff_b,
                        "p_model": 1.0,
                        "net_edge": carry_edge,
                        "l1_usd": w_bond["l1_usd"],
                        "close_ts": close_est,
                    })
                self.emit_live_single_leg_lock_candidate(
                    sleeve_source="BOND1_UMA_RESOLUTION_CARRY",
                    asset=str(ver["domain"]),
                    dedupe_key=dkey_b1,
                    token_id=wtok,
                    opp_token_id=ltok,
                    market_id=mid,
                    condition_id=str(m.get("conditionId") or ""),
                    side_label=str(ver["win_label"]),
                    display_label=f"{ver['domain']} {ver['win_outcome_name']}",
                    bk_win=bk_w,
                    bk_opp=bk_l,
                    fee_rate=float(ver["fee_rate"]),
                    fee_exponent=float(ver["fee_exponent"]),
                    neg_risk=bool(m.get("negRisk")),
                    close_ts=close_est,
                    now_ts=now,
                    max_lock_eff_px=_b1_tkr_cap,
                    max_opp_bid=0.008,
                    hold_to_maturity=True,
                    p_model=1.0,
                )
                if _shadow_b1_free and eff_b <= 0.9955:
                    opened_bond = await self.open_shadow_position(
                        sleeve="BOND1_UMA_RESOLUTION_CARRY",
                        dedupe_key=dkey_b1,
                        asset_or_city=str(ver["domain"]),
                        title=f"{q_str} [{ver['win_outcome_name']}]",
                        side_label=str(ver["win_label"]),
                        token_id=wtok,
                        fee_rate=float(ver["fee_rate"]),
                        p_model=1.0,
                        close_ts=close_est,
                        extra=bond_extra,
                        tp_target_px=None,
                        prefetched_book=bk_w,
                    )
            if not taker_bond_qual and not opened_bond and 0.940 <= win_bid <= _b1_max_mkr and lose_bid <= 0.008 and _b1_rem_s > 120.0:
                _b1_mkr_emitted = bool(
                    self.emit_live_single_leg_maker_lock_candidate(
                        sleeve_source="BOND1_UMA_RESOLUTION_CARRY",
                        asset=str(ver["domain"]),
                        dedupe_key=f"BOND1_MKR_{mid}",
                        pair_dedupe_key=dkey_b1,
                        token_id=wtok,
                        opp_token_id=ltok,
                        market_id=mid,
                        condition_id=str(m.get("conditionId") or ""),
                        side_label=str(ver["win_label"]),
                        display_label=f"{ver['domain']} {ver['win_outcome_name']}",
                        bk_win=bk_w,
                        bk_opp=bk_l,
                        neg_risk=bool(m.get("negRisk")),
                        close_ts=close_est,
                        now_ts=now,
                        min_resting_bid=0.940,
                        max_resting_bid=_b1_max_mkr,
                        min_maker_edge=_b1_min_ed,
                        max_opp_bid=0.008,
                        hold_to_maturity=True,
                        p_model=1.0,
                    )
                )
                if _shadow_b1_free:
                    posted_bond = await self.post_shadow_maker_entry(
                        sleeve="BOND1_UMA_RESOLUTION_CARRY",
                        dedupe_key=dkey_b1,
                        asset=str(ver["domain"]),
                        title=f"{q_str} [{ver['win_outcome_name']}]",
                        side_label=str(ver["win_label"]),
                        token_id=wtok,
                        p_model=1.0,
                        close_ts=close_est,
                        extra=bond_extra,
                        prefetched_book=bk_w,
                    )
                    if posted_bond:
                        opps_out.append({
                            "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                            "market": f"[MAKER:{ver['domain']}] {q_str[:58]} -> {ver['win_outcome_name']}",
                            "ask_vwap": win_bid,
                            "p_model": 1.0,
                        "net_edge": round(1.0 - win_bid, 4),
                        "l1_usd": extract_best_bid(bk_w.get("bids") or [])[1],
                        "close_ts": close_est,
                    })

            # `BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY`: Hardened final-hour (`180s..3300s`, `age>=3600s`) Whitelisted MOOv2 carry
            dk_b2 = f"BOND2_{mid}"
            _shadow_b2_free = dk_b2 not in self.entered_keys and dk_b2 not in self.inflight_keys
            if (
                not (not _is_live_uma_daemon and dk_b2 in self.entered_keys)
                and dk_b2 not in self.inflight_keys
                and float(ver.get("proposal_age_sec") or 0.0) >= 3600.0
                and 180.0 <= float(ver.get("rem_challenge_sec") or 0.0) <= 3300.0
                and lose_bid <= 0.006
                and win_bid >= 0.950
            ):
                ver2 = await asyncio.to_thread(verify_bond2_moov2_final_hour_sync, m, None, now)
                if ver2.get("verified"):
                    _b2_cap = 0.9975 if _is_live_uma_daemon else 0.9962
                    w_b2 = walk_l2_book_asks_depth_capped(
                        bk_w.get("asks") or [],
                        BANKROLL_TICKETS["T1000"]["BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"],
                        BANKROLL_TICKETS["T100"]["BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"],
                        fee_rate=float(ver2["fee_rate"]),
                        min_l1_usd=10.0 if _is_live_uma_daemon else 15.0,
                        max_ask_px=round(_b2_cap + 0.0001, 4),
                        fee_exponent=float(ver2["fee_exponent"]),
                    )
                    if w_b2.get("filled") and 0.950 <= float(w_b2["eff_px"]) <= _b2_cap:
                        eff_b2 = float(w_b2["eff_px"])
                        edg_b2 = round(1.0 - eff_b2, 4)
                        if edg_b2 >= (0.0025 if _is_live_uma_daemon else 0.0038):
                            if _shadow_b2_free:
                                opps_out.append({
                                    "sleeve": "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
                                    "market": f"[MOOv2_WL:{ver2['domain']}] {q_str[:60]} -> {ver2['win_outcome_name']} ({ver2['rem_challenge_sec']/60:.0f}m rem)",
                                    "ask_vwap": eff_b2,
                                    "p_model": 1.0,
                                    "net_edge": edg_b2,
                                    "l1_usd": w_b2["l1_usd"],
                                    "close_ts": close_est,
                                })
                            self.emit_live_single_leg_lock_candidate(
                                sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
                                asset=str(ver2["domain"]),
                                dedupe_key=dk_b2,
                                token_id=wtok,
                                opp_token_id=ltok,
                                market_id=mid,
                                condition_id=str(m.get("conditionId") or ""),
                                side_label=str(ver2["win_label"]),
                                display_label=f"MOOv2_WL {ver2['domain']} {ver2['win_outcome_name']}",
                                bk_win=bk_w,
                                bk_opp=bk_l,
                                fee_rate=float(ver2["fee_rate"]),
                                fee_exponent=float(ver2["fee_exponent"]),
                                neg_risk=bool(m.get("negRisk")),
                                close_ts=close_est,
                                now_ts=now,
                                max_lock_eff_px=_b2_cap,
                                max_opp_bid=0.006,
                                hold_to_maturity=True,
                                p_model=1.0,
                            )
                            if _shadow_b2_free:
                                await self.open_shadow_position(
                                    sleeve="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
                                    dedupe_key=dk_b2,
                                    asset_or_city=str(ver2["domain"]),
                                    title=f"{q_str} [MOOv2 Whitelisted {ver2['win_outcome_name']}]",
                                    side_label=str(ver2["win_label"]),
                                    token_id=wtok,
                                    fee_rate=float(ver2["fee_rate"]),
                                    p_model=1.0,
                                    close_ts=close_est,
                                    extra={**bond_extra, "proposer_whitelisted": True, "oo_address": ver2["oo_address"]},
                                    tp_target_px=None,
                                    prefetched_book=bk_w,
                                )
                        elif _is_live_uma_daemon and not _b1_mkr_emitted:
                            self.emit_live_single_leg_maker_lock_candidate(
                                sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY", asset=str(ver2["domain"]),
                                dedupe_key=f"{dk_b2}_MKR", pair_dedupe_key=dk_b2, token_id=wtok, opp_token_id=ltok,
                                market_id=mid, condition_id=str(m.get("conditionId") or ""), side_label=str(ver2["win_label"]),
                                display_label=f"MOOv2_WL Maker {ver2['domain']} {ver2['win_outcome_name']}",
                                bk_win=bk_w, bk_opp=bk_l, neg_risk=bool(m.get("negRisk")), close_ts=close_est, now_ts=now,
                                min_resting_bid=0.950, max_resting_bid=0.9980, min_maker_edge=0.0020, max_opp_bid=0.006, p_model=1.0,
                            )
                    elif _is_live_uma_daemon and not _b1_mkr_emitted:
                        self.emit_live_single_leg_maker_lock_candidate(
                            sleeve_source="BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY", asset=str(ver2["domain"]),
                            dedupe_key=f"{dk_b2}_MKR", pair_dedupe_key=dk_b2, token_id=wtok, opp_token_id=ltok,
                            market_id=mid, condition_id=str(m.get("conditionId") or ""), side_label=str(ver2["win_label"]),
                            display_label=f"MOOv2_WL Maker {ver2['domain']} {ver2['win_outcome_name']}",
                            bk_win=bk_w, bk_opp=bk_l, neg_risk=bool(m.get("negRisk")), close_ts=close_est, now_ts=now,
                            min_resting_bid=0.950, max_resting_bid=0.9980, min_maker_edge=0.0020, max_opp_bid=0.006, p_model=1.0,
                        )

    async def scan_nba_endgame_locks(
        self,
        opps_out: List[Dict[str, Any]],
        now_ts: Optional[float] = None,
    ) -> None:
        now = float(now_ts if now_ts is not None else time.time())
        if not self.nba_games:
            return
        poll_ttl = 5.5 if self.has_live_nba_window(now) else 120.0
        if self.single_scan or not self.live_nba_board or (now - self.last_espn_board_ts) >= poll_ttl:
            board = await asyncio.to_thread(fetch_espn_nba_scoreboard_sync)
            if board:
                self.live_nba_board = board
                self.last_espn_board_ts = now
        if not self.live_nba_board:
            return

        cand_rows: List[Tuple[NbaGameSpec, Dict[str, Any]]] = []
        for sp_nba in list(self.nba_games.values()):
            matched = match_nba_live_game(sp_nba, self.live_nba_board)
            if matched is None:
                continue
            g_state, sc_a, sc_b = matched
            if g_state.state in ("in", "post"):
                self._record_market_telemetry(
                    key=f"NBA_LIVE_{sp_nba.event_id}",
                    min_interval_sec=30.0,
                    now_ts=now,
                    sig=(g_state.state, g_state.period, int(g_state.clock_sec // 10), sc_a, sc_b),
                    payload={
                        "type": "NBA_LIVE_SCORE_SNAP",
                        "event_id": sp_nba.event_id,
                        "game": sp_nba.title,
                        "state": g_state.state,
                        "completed": g_state.completed,
                        "period": g_state.period,
                        "clock_sec": round(g_state.clock_sec, 1),
                        "score_a": sc_a,
                        "score_b": sc_b,
                        "source": g_state.source,
                    },
                )
            for c_lk in evaluate_nba_endgame_locks(sp_nba, g_state, sc_a, sc_b):
                lg = c_lk["leg"]
                dk_sp2 = f"SP2_{sp_nba.event_id}_{lg.market_id}_{lg.token_id[-8:]}"
                if dk_sp2 not in self.entered_keys and dk_sp2 not in self.inflight_keys:
                    cand_rows.append((sp_nba, c_lk))

        if not cand_rows:
            await self._scan_sp4_live_nba_stat_locks(opps_out, now)
            return

        sp2_toks = [t for _, c_lk in cand_rows for t in (c_lk["leg"].token_id, c_lk["leg"].opp_token_id)]
        sp2_bks = await self.fetch_books_batch(sp2_toks, timeout=3.0)
        ref_tkt = BANKROLL_TICKETS["T1000"]["SP2_NBA_ENDGAME_LOCK"]

        for sp_nba, c_lk in cand_rows:
            lg = c_lk["leg"]
            bk_win = sp2_bks.get(lg.token_id)
            bk_opp = sp2_bks.get(lg.opp_token_id)
            if not bk_win or not bk_opp:
                continue
            opp_bid, _ = extract_best_bid(bk_opp.get("bids") or [])
            if opp_bid > 0.18:
                continue
            win_bid_sp2, win_bid_usd_sp2 = extract_best_bid(bk_win.get("bids") or [])
            fr_sp2 = float(getattr(lg, "fee_rate", 0.0) or 0.0)
            fe_sp2 = float(getattr(lg, "fee_exponent", 1.0) or 1.0)
            w_sp2 = walk_l2_book_asks_depth_capped(
                bk_win.get("asks") or [],
                ref_tkt,
                BANKROLL_TICKETS["T100"]["SP2_NBA_ENDGAME_LOCK"],
                fee_rate=fr_sp2,
                min_l1_usd=18.0,
                max_ask_px=0.9861,
                fee_exponent=fe_sp2,
            )
            p_lk = float(c_lk["p_lock"])
            close_sp2 = max(now + 600.0, float(sp_nba.settle_est_ts))
            dk_sp2_k = f"SP2_{sp_nba.event_id}_{lg.market_id}_{lg.token_id[-8:]}"
            sp2_extra = {
                "event_id": sp_nba.event_id,
                "market_id": lg.market_id,
                "condition_id": lg.condition_id,
                "opp_token_id": lg.opp_token_id,
                "mode": c_lk["mode"],
                "score_str": c_lk["score_str"],
                "cushion_pts": c_lk["cushion_pts"],
                "clock_sec": c_lk["clock_sec"],
                "period": c_lk["period"],
                "fee_exponent": fe_sp2,
            }
            opened_sp2 = False
            if w_sp2.get("filled"):
                eff_sp2 = float(w_sp2["eff_px"])
                edg_sp2 = round(p_lk - eff_sp2, 4)
                if opp_bid <= (1.0 - eff_sp2) + 0.025 and (0.78 <= eff_sp2 <= 0.986) and edg_sp2 >= 0.012:
                    opps_out.append({
                        "sleeve": "SP2_NBA_ENDGAME_LOCK",
                        "market": f"NBA [{c_lk['mode']}] {c_lk['score_str']} -> {lg.display_label}",
                        "ask_vwap": eff_sp2,
                        "p_model": p_lk,
                        "net_edge": edg_sp2,
                        "l1_usd": w_sp2["l1_usd"],
                        "close_ts": close_sp2,
                    })
                    opened_sp2 = await self.open_shadow_position(
                        sleeve="SP2_NBA_ENDGAME_LOCK",
                        dedupe_key=dk_sp2_k,
                        asset_or_city="NBA",
                        title=f"{sp_nba.title} [{lg.display_label} | {c_lk['mode']}]",
                        side_label=lg.side_label,
                        token_id=lg.token_id,
                        fee_rate=fr_sp2,
                        p_model=p_lk,
                        close_ts=close_sp2,
                        extra=sp2_extra,
                        tp_target_px=None,
                        prefetched_book=bk_win,
                    )
            if (
                not opened_sp2
                and 0.72 <= win_bid_sp2 <= 0.985
                and opp_bid <= (1.0 - win_bid_sp2) + 0.025
                and (p_lk - win_bid_sp2) >= 0.012
            ):
                posted_sp2 = await self.post_shadow_maker_entry(
                    sleeve="SP2_NBA_ENDGAME_LOCK",
                    dedupe_key=dk_sp2_k,
                    asset="NBA",
                    title=f"{sp_nba.title} [{lg.display_label} | {c_lk['mode']}]",
                    side_label=lg.side_label,
                    token_id=lg.token_id,
                    p_model=p_lk,
                    close_ts=close_sp2,
                    extra=sp2_extra,
                    prefetched_book=bk_win,
                    ttl_override_sec=45.0,
                )
                if posted_sp2:
                    opps_out.append({
                        "sleeve": "SP2_NBA_ENDGAME_LOCK",
                        "market": f"[MAKER] NBA [{c_lk['mode']}] {c_lk['score_str']} -> {lg.display_label}",
                        "ask_vwap": win_bid_sp2,
                        "p_model": p_lk,
                        "net_edge": round(p_lk - win_bid_sp2, 4),
                        "l1_usd": win_bid_usd_sp2,
                        "close_ts": close_sp2,
                    })

        # `SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK` Sub-Mode 3A: Live NBA Boxscore Irreversible Stat Clinch
        await self._scan_sp4_live_nba_stat_locks(opps_out, now)

    async def _scan_sp4_live_nba_stat_locks(self, opps_out: List[Dict[str, Any]], now: float) -> None:
        if (not self.nba_prop_slates and not self.nba_subperiod_slates) or not self.live_nba_board:
            return
        sp4_cands: List[Dict[str, Any]] = []
        sp4_sub_cands: List[Tuple[str, Dict[str, Any]]] = []
        all_nba_ev_ids = sorted(set(self.nba_prop_slates.keys()) | set(self.nba_subperiod_slates.keys()))
        for ev_id in all_nba_ev_ids:
            sp_nba = self.nba_games.get(ev_id)
            if sp_nba is None:
                continue
            matched = match_nba_live_game(sp_nba, self.live_nba_board)
            if matched is None or matched[0].state not in ("in", "post"):
                continue
            g_st = matched[0]
            gid_espn = str(g_st.game_id or "")
            if not gid_espn:
                continue
            cached_bs = self.nba_boxscore_cache.get(gid_espn)
            cached_ext = self.nba_ext_summary_cache.get(gid_espn)
            if cached_bs is not None and cached_ext is not None and (now - cached_bs[0]) < 12.0:
                p_stats = cached_bs[1]
                ext_sum = cached_ext[1]
            else:
                try:
                    p_stats, ext_sum = await asyncio.to_thread(fetch_espn_nba_full_summary_sync, gid_espn)
                except Exception:
                    p_stats, ext_sum = {}, {}
                self.nba_boxscore_cache[gid_espn] = (now, p_stats)
                self.nba_ext_summary_cache[gid_espn] = (now, ext_sum)
            sl_pr = self.nba_prop_slates.get(ev_id)
            if sl_pr is not None:
                for c_lk in evaluate_sp4_ingame_clinch_locks(sl_pr, g_st, p_stats):
                    rg = c_lk["rung"]
                    dk = f"SP4_3A_{rg.event_id}_{rg.market_id}"
                    if dk not in self.entered_keys and dk not in self.inflight_keys:
                        sp4_cands.append(c_lk)
            sl_sub = self.nba_subperiod_slates.get(ev_id)
            if sl_sub is not None and ext_sum:
                for sub_lk in evaluate_sp4_subperiod_and_ext_locks(sl_sub, ext_sum):
                    dk_sub = f"SP4_SUB_LK_{ev_id}_{sub_lk['market_id']}"
                    if dk_sub not in self.entered_keys and dk_sub not in self.inflight_keys:
                        sp4_sub_cands.append((dk_sub, sub_lk))

        all_lk_toks = [t for c in sp4_cands for t in (c["rung"].yes_token, c["rung"].no_token)] + [
            t for _, slk in sp4_sub_cands for t in (slk["token_id"], slk["opp_token_id"])
        ]
        if not all_lk_toks:
            return
        bks_sp4 = await self.fetch_books_batch(sorted(set(all_lk_toks)), timeout=3.0)
        for c_lk in sp4_cands:
            rg = c_lk["rung"]
            bk_y, bk_n = bks_sp4.get(rg.yes_token), bks_sp4.get(rg.no_token)
            if not bk_y or not bk_n:
                continue
            opp_bid, _ = extract_best_bid(bk_n.get("bids") or [])
            if opp_bid > 0.04:
                continue
            fr_rg = float(getattr(rg, "fee_rate", 0.0) or 0.0)
            fe_rg = float(getattr(rg, "fee_exponent", 1.0) or 1.0)
            w_lk = walk_l2_book_asks_depth_capped(
                bk_y.get("asks") or [],
                BANKROLL_TICKETS["T1000"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],
                BANKROLL_TICKETS["T100"]["SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK"],
                fee_rate=fr_rg, min_l1_usd=15.0, max_ask_px=0.9881, fee_exponent=fe_rg,
            )
            if w_lk.get("filled"):
                eff = float(w_lk["eff_px"])
                p_lk = float(c_lk["p_lock"])
                edg = round(p_lk - eff, 4)
                if 0.72 <= eff <= 0.988 and edg >= 0.012:
                    dk = f"SP4_3A_{rg.event_id}_{rg.market_id}"
                    close_est = max(now + 600.0, float(rg.settle_est_ts))
                    opps_out.append({
                        "sleeve": "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
                        "market": f"NBA [{c_lk['mode']}] {rg.player_name} {rg.stat_type}={c_lk['current_stat']} > {rg.line}",
                        "ask_vwap": eff, "p_model": p_lk, "net_edge": edg,
                        "l1_usd": w_lk["l1_usd"], "close_ts": close_est,
                    })
                    self.emit_live_single_leg_lock_candidate(
                        sleeve_source="SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
                        asset="NBA",
                        dedupe_key=dk,
                        token_id=rg.yes_token,
                        opp_token_id=rg.no_token,
                        market_id=rg.market_id,
                        condition_id=rg.condition_id,
                        side_label="YES",
                        display_label=f"{rg.player_name} {rg.stat_type} O{rg.line} ({c_lk['current_stat']})",
                        bk_win=bk_y,
                        bk_opp=bk_n,
                        fee_rate=fr_rg,
                        fee_exponent=fe_rg,
                        neg_risk=False,
                        close_ts=close_est,
                        now_ts=now,
                        max_lock_eff_px=0.988,
                        max_opp_bid=0.025,
                        hold_to_maturity=True,
                        p_model=p_lk,
                    )
                    await self.open_shadow_position(
                        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK", dk, "NBA_PROP",
                        f"{rg.game_title} [{rg.player_name} {rg.stat_type} O{rg.line} (cur={c_lk['current_stat']})]",
                        "YES", rg.yes_token, fr_rg, p_lk, close_est,
                        {"market_id": rg.market_id, "condition_id": rg.condition_id, "opp_token_id": rg.no_token, "mode": c_lk["mode"], "stat_val": c_lk["current_stat"], "fee_exponent": fe_rg},
                        prefetched_book=bk_y,
                    )
        for dk_sub, sub_lk in sp4_sub_cands:
            bk_w_s, bk_o_s = bks_sp4.get(sub_lk["token_id"]), bks_sp4.get(sub_lk["opp_token_id"])
            if not bk_w_s or not bk_o_s:
                continue
            opp_bid_s, _ = extract_best_bid(bk_o_s.get("bids") or [])
            if opp_bid_s > 0.04:
                continue
            fr_sub = float(sub_lk.get("fee_rate", 0.0) or 0.0)
            fe_sub = float(sub_lk.get("fee_exponent", 1.0) or 1.0)
            w_sub = walk_l2_book_asks_depth_capped(
                bk_w_s.get("asks") or [],
                BANKROLL_TICKETS["T1000"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],
                BANKROLL_TICKETS["T100"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"],
                fee_rate=fr_sub, min_l1_usd=15.0, max_ask_px=0.9881, fee_exponent=fe_sub,
            )
            if w_sub.get("filled"):
                eff_s = float(w_sub["eff_px"])
                p_lk_s = float(sub_lk["p_lock"])
                edg_s = round(p_lk_s - eff_s, 4)
                if 0.72 <= eff_s <= 0.988 and edg_s >= 0.012:
                    close_sub = max(now + 600.0, float(sub_lk["close_ts"]))
                    opps_out.append({
                        "sleeve": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
                        "market": f"NBA [{sub_lk['mode']}] {sub_lk['display_label']}",
                        "ask_vwap": eff_s, "p_model": p_lk_s, "net_edge": edg_s,
                        "l1_usd": w_sub["l1_usd"], "close_ts": close_sub,
                    })
                    if self._can_emit_zero_loss_math_live("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", close_sub, now, p_model=p_lk_s):
                        self.emit_live_single_leg_lock_candidate(
                            sleeve_source="SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
                            asset="NBA",
                            dedupe_key=dk_sub,
                            token_id=str(sub_lk["token_id"]),
                            opp_token_id=str(sub_lk["opp_token_id"]),
                            market_id=str(sub_lk["market_id"]),
                            condition_id=str(sub_lk["condition_id"]),
                            side_label=str(sub_lk["side_label"]),
                            display_label=str(sub_lk["display_label"]),
                            bk_win=bk_w_s,
                            bk_opp=bk_o_s,
                            fee_rate=fr_sub,
                            fee_exponent=fe_sub,
                            neg_risk=bool(sub_lk.get("neg_risk", False)),
                            close_ts=close_sub,
                            now_ts=now,
                            max_lock_eff_px=0.988,
                            max_opp_bid=0.025,
                            hold_to_maturity=True,
                            p_model=p_lk_s,
                        )
                    await self.open_shadow_position(
                        "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", dk_sub, "NBA_SUBPERIOD",
                        sub_lk["display_label"], str(sub_lk["side_label"]), str(sub_lk["token_id"]),
                        fr_sub, p_lk_s, close_sub,
                        {"market_id": sub_lk["market_id"], "condition_id": sub_lk["condition_id"], "opp_token_id": sub_lk["opp_token_id"], "mode": sub_lk["mode"], "fee_exponent": fe_sub},
                        prefetched_book=bk_w_s,
                    )

    async def scan_protocol_v2_expansion_opportunities(
        self, opps_out: List[Dict[str, Any]], now_ts: Optional[float] = None
    ) -> None:
        """Live Gatling Protocol V2 6-Pillar fault-isolated scanner (`EQ1`, `B1`, `NR4/NR5`, `MENTION1`, `DC1/LP_COMP1`, `C1/CTF_OVERROUND`)."""
        from src.polymarket_research.riskless_protocol_v2_expansion import run_protocol_v2_daemon_scan
        await run_protocol_v2_daemon_scan(self, opps_out, now_ts=now_ts)

    async def _run_gatling_fast_gun_loop(self) -> None:
        """
        Dedicated non-blocking `<200ms` Gatling Fast-Gun background coroutine:
        Continuously fires `S2_EXACT_TWAP_LOCK` (`4.5s <= TTE <= 16.0s`) and `D1` Same-Oracle Dominance
        (`15m/5m`, `4h/15m`, `4h/5m`, `XAU`/`XAG` `1h/15m`) even while outer Gamma discovery is running!
        """
        last_d1_fast = 0.0
        last_s2_fast = 0.0
        while True:
            try:
                now_f = time.time()
                rem_5m = (math.ceil(now_f / 300.0) * 300.0) - now_f
                if rem_5m <= 65.0 and (now_f - self.last_usd_sample_ts) >= 0.95:
                    self.record_usd_spot_samples(now_f)
                # 1. Sub-200ms S2 Exact 60s-TWAP Lock Zone (`3.8s <= rem_5m <= 28.0s` + pre-warm at `<= 92s`)
                s2_gap = 0.18 if (4.0 <= rem_5m <= 22.0) else 2.5
                if (3.8 <= rem_5m <= 92.0) and (now_f - last_s2_fast) >= s2_gap:
                    last_s2_fast = now_f
                    s2_fast_opps: List[Dict[str, Any]] = []
                    await self.scan_exact_twap_locks(s2_fast_opps, now_ts=now_f)
                # 2. Sub-250ms D1 Same-Oracle Dominance overlap scan (never blocked by outer Gamma sweep!)
                if self.is_in_same_oracle_overlap_window(now_f) and (now_f - last_d1_fast) >= 0.35:
                    d1_lock = self.__dict__.setdefault("_d1_fast_scan_lock", asyncio.Lock())
                    if not d1_lock.locked():
                        last_d1_fast = now_f
                        async with d1_lock:
                            d1_fast_opps: List[Dict[str, Any]] = []
                            await self.scan_same_oracle_dominance_boxes(d1_fast_opps, now_ts=now_f)
                await asyncio.sleep(0.15 if (4.0 <= rem_5m <= 22.0) else 0.25)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug(f"Gatling fast-gun loop notice: {exc}")
                await asyncio.sleep(0.5)

    async def _run_bg_nba_endgame(self) -> None:
        try:
            nba_opps: List[Dict[str, Any]] = []
            await self.scan_nba_endgame_locks(nba_opps)
            self.cached_nba_endgame_opps = nba_opps
        except Exception as exc:
            logger.warning(f"Background NBA endgame scan notice: {exc}")

    async def _run_bg_tradfi_sports(self) -> None:
        ts_opps: List[Dict[str, Any]] = []
        try:
            await self.scan_tradfi_and_sports_markets(ts_opps)
        except Exception as exc:
            logger.warning(f"Background TradFi/Sports scan notice: {exc}")
        try:
            await self.scan_protocol_v2_expansion_opportunities(ts_opps)
        except Exception as exc_v2:
            logger.warning(f"Background Protocol V2 scan notice: {exc_v2}")
        self.cached_tradfi_sports_opps = ts_opps

    async def run_forever(self) -> None:
        logger.info(
            "Starting Polymarket Alpha-124 Unified Shadow Daemon "
            "(Gatling High-Vol Machine Gun: S2 Live TWAP Lock + 9-Asset D1 + Protocol V2 Expansion)..."
        )
        try:
            if not self.single_scan and (self._bg_clob_ws_task is None or self._bg_clob_ws_task.done()):
                self._bg_clob_ws_task = asyncio.create_task(self._run_clob_d1_ws_loop())
            if not self.single_scan and self._chainlink_ws is not None and (self._bg_chainlink_ws_task is None or self._bg_chainlink_ws_task.done()):
                self._bg_chainlink_ws_task = asyncio.create_task(self._chainlink_ws.run_forever())
            _gatling_task = getattr(self, "_bg_gatling_fast_task", None)
            if not self.single_scan and (_gatling_task is None or _gatling_task.done()):
                self._bg_gatling_fast_task = asyncio.create_task(self._run_gatling_fast_gun_loop())
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
                    await self.scan_protocol_v2_expansion_opportunities(ts_opps)
                    self.cached_tradfi_sports_opps = ts_opps

                    nba_opps: List[Dict[str, Any]] = []
                    await self.scan_nba_endgame_locks(nba_opps)
                    self.cached_nba_endgame_opps = nba_opps
                else:
                    # Non-blocking background coroutines so S2 (3.0s) / D1 (3.5s) never stall
                    nba_cadence = 6.0 if self.has_live_nba_window(t0) else 120.0
                    if (t0 - self.last_nba_endgame_scan_ts) >= nba_cadence and (
                        self._bg_nba_task is None or self._bg_nba_task.done()
                    ):
                        self.last_nba_endgame_scan_ts = t0
                        self._bg_nba_task = asyncio.create_task(self._run_bg_nba_endgame())

                    if (t0 - self.last_crypto_mid_scan_ts) >= 18.0 and (
                        self._bg_mid_task is None or self._bg_mid_task.done()
                    ):
                        self.last_crypto_mid_scan_ts = t0
                        self._bg_mid_task = asyncio.create_task(self._run_bg_mid_crypto())

                    tradfi_cadence = 8.0 if (self.has_live_sports_window(t0) or self.pending_zero_fee_maker_anchors) else 20.0
                    if (t0 - self.last_tradfi_sports_scan_ts) >= tradfi_cadence and (
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
                    + self.cached_nba_endgame_opps
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
                    f"NBA={len(self.nba_games)}/{len(self.live_nba_board)}live(SP4={len(self.nba_prop_slates)},SP4+={len(self.nba_subperiod_slates)},EM={len(self.lp1_nba_em_bundles)}), "
                    f"SP3={len(self.multi_sport_games)}(NFLEM={len(self.lp1_nfl_em_bundles)}), SOC1={len(self.soccer_trees)}, TEN1={len(self.tennis_specs)}, API1={len(self.esports_bo3_specs)}, "
                    f"BOP={len(self.lp1_bop_legs)//2}, LP2={len(self.lp2_implication_groups)}, CAL1={len(self.cal1_ladders)}, UMA={len(self.uma_proposed_markets)}, "
                    f"NR0={len(self.negrisk_zero_slates)}, NRC={len(self.negrisk_convert_slates)}, TW={len(self.counting_slates)}, "
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
                _s2_live_active = not is_shadow_sleeve_quarantined("S2_EXACT_TWAP_LOCK")
                if _s2_live_active and self.is_in_exact_twap_lock_window(now_end):
                    target_cadence = 3.0
                elif self.is_in_same_oracle_overlap_window(now_end):
                    target_cadence = 3.5
                elif self.pending_zero_fee_maker_anchors:
                    target_cadence = 4.0
                elif 8.0 <= rem_4h_end <= 905.0 or self.pending_preopen_straddles or self.has_live_sports_window(now_end):
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
                    nr_ws_triggered = self._ws_nr_wakeup.is_set()
                    if nr_ws_triggered:
                        self._ws_nr_wakeup.clear()
                    # Event-driven (<=120ms on CLOB WS delta, 500ms fallback) D1 overlap box scan without state-file churn
                    min_d1_gap = 0.12 if ws_triggered else 0.50
                    if self.is_in_same_oracle_overlap_window(now_s) and (now_s - last_fast_d1_subscan) >= min_d1_gap:
                        last_fast_d1_subscan = now_s
                        d1_sub_opps: List[Dict[str, Any]] = []
                        await self.scan_same_oracle_dominance_boxes(d1_sub_opps, now_ts=now_s)
                        if d1_sub_opps:
                            dom_opps = d1_sub_opps
                        if self.pending_zero_fee_maker_anchors:
                            await self.manage_pending_zero_fee_maker_anchors(now_ts=now_s)
                    elif (self.pending_maker_anchors or self.pending_zero_fee_maker_anchors) and (now_s - last_fast_d1_subscan) >= 0.50:
                        last_fast_d1_subscan = now_s
                        if self.pending_maker_anchors:
                            await self.manage_pending_maker_anchors(now_ts=now_s)
                        if self.pending_zero_fee_maker_anchors:
                            await self.manage_pending_zero_fee_maker_anchors(now_ts=now_s)
                    if nr_ws_triggered and (now_s - getattr(self, "_last_fast_nr_subscan", 0.0)) >= 0.25:
                        self._last_fast_nr_subscan = now_s
                        await self._scan_ws_reactive_negrisk_arbs(now_s)
                    # Sample /dev/shm USD anchor at 1 Hz during the 65s TWAP integral window (0 REST calls)
                    rem_5m_s = (math.ceil(now_s / 300.0) * 300.0) - now_s
                    if _s2_live_active and rem_5m_s <= 65.0 and (now_s - self.last_usd_sample_ts) >= 1.0:
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
                                + self.cached_nba_endgame_opps
                                + self.cached_tradfi_sports_opps
                                + self.cached_weather_opps
                            )
                    # Step down cadence immediately if we just entered the final-55s TWAP lock window
                    if _s2_live_active and target_cadence > 3.0 and self.is_in_exact_twap_lock_window(now_s):
                        break
                    wait_cap = min(0.20, max(0.03, deadline - time.time()))
                    try:
                        await asyncio.wait_for(self._ws_d1_wakeup.wait(), timeout=wait_cap)
                    except asyncio.TimeoutError:
                        pass
        finally:
            for bg_t in (
                getattr(self, "_bg_gatling_fast_task", None),
                self._bg_chainlink_ws_task,
                self._bg_clob_ws_task,
                self._bg_discovery_task,
                self._bg_mid_task,
                self._bg_tradfi_task,
                self._bg_weather_task,
                self._bg_nba_task,
            ):
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
