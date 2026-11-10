"""
Stage G Read-Only Multi-Venue Pure-Riskless Shadow Probe & Honest Graduation Engine
(`src/polymarket_research/cross_venue_riskless_shadow.py`).

Strictly 100% READ-ONLY (zero private keys, zero wallet secrets, zero order-placement routes).
Pairs `Predict.fun` (BNB Chain), `SX Bet` (SX Rollup OBv3), and `Limitless Exchange` (Base)
against `Polymarket` (Polygon) under Dominus's non-negotiable pure-riskless invariant:

    min_{omega in Omega} V_T(omega) > Total Cost + All Venue Fees + Gas + Relay.link Bridge Drag

Enforces:
  1. Exact live-verified venue microstructure & fee equations:
       - Polymarket: dynamic per-token `fee_rate_bps` (`0%` macro/weather/NBA, `0.07*p*(1-p)` crypto,
         `0.0175*p*(1-p)` fee-bearing sports).
       - Predict.fun: `FeeModuleV2` linear tent `BaseFee * min(p, 1 - p) * C` (`1.8%` w/ 10% invite
         discount or `2.0%` standard -> `1.8 bps` at `$0.99`), `0%` maker + `25%` crypto up/down
         estimated unsettled rebate (never booked as realized cash PnL).
       - SX Bet (OBv3): `0.00%` Maker & `0.00%` Taker on single sports bets; enforces peer-to-peer
         `10^20` complement invariant (`yes_ask = 1 - bestOddsOutcomeTwo/1e20`,
         `no_ask = 1 - bestOddsOutcomeOne/1e20`) so `o1 + o2 < 1` never creates phantom arbs.
       - Limitless Exchange: `0.05 * C * p * (1 - p)` on `COLLATERAL` fee-enabled venues (`0%` maker),
         `10^6` USDC share scaling, `limit <= 25` pagination, and `settings.takerDelayMs` speed-bumps.
       - Relay.link cross-chain treasury rebalance drag (`2.75 bps` = `$0.055` per `$200` clip).
  2. All 5 Programmatic "Double-Zero" Verification Gates (`CrossVenueRuleVerifier`):
       - Gate 1: Strict Oracle, Timestamp & Rule-Hash Identity (`chainlink_60s_twap` != `binance_spot_candle`).
       - Gate 2: Cross-Oracle Strike Dominance Corridor (`K_high - K_low >= B_max` when indices differ).
       - Gate 3: `50-50` Walkover Windfall Ceiling (`p_50_50 <= $0.48` vs `VOID` venue; blocks unlisted 3-way Draws).
       - Gate 4: Tennis Set-2+ Convergence (`completed_sets >= 1` when `ONE_BALL` meets `ONE_SET`).
       - Gate 5: Live Participation Prop & Listed-Pitcher Gate (`game_live and player_participated`).
  3. Honest Post-Latency (`Wire RTT + takerDelayMs`) L2 Re-Verification, Queue-Ahead Maker Trade-Through,
     Raced-Hedge Unwind Bleed Accounting, Multi-Cycle `competitor_decay_ms`, and the 5 Mandatory
     7-Day Shadow Graduation Gates (`G1`–`G5`).
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import shutil
import time
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import urllib.error
import urllib.parse
import urllib.request

from src.polymarket_research.economic_attribution_ledger import classify_decay_bucket

try:
    import aiohttp as _aiohttp  # type: ignore
except ImportError:  # pragma: no cover
    _aiohttp = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Latency / Bridge Calibration
# ---------------------------------------------------------------------------

POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_URL = "https://clob.polymarket.com"
LIMITLESS_API_URL = "https://api.limitless.exchange"
SX_BET_API_URL = "https://api.sx.bet"
PREDICT_FUN_MAINNET_URL = "https://api.predict.fun/v1"
PREDICT_FUN_TESTNET_URL = "https://api-testnet.predict.fun/v1"

# Empirical one-way / order-ack latency defaults from quant-pipeline-finland (europe-north1-b)
DEFAULT_WIRE_LATENCY_MS: Dict[str, float] = {
    "polymarket": 72.39,     # Verified live Finland POST /order p50
    "limitless": 115.0,      # Finland -> Cloudflare -> AWS us-east-1 (Base sequencer)
    "sx_bet": 95.0,          # Finland -> SX Rollup edge API
    "predict_fun": 246.0,    # Finland -> AWS ap-northeast-1 Tokyo (~1.74 ms w/ Tokyo relay)
    "forecastex": 65.0,      # Direct North America / IBKR Gateway
    "stx_ontario": 35.0,     # Direct Ontario / AGCO gateway
}

DEFAULT_RELAY_BRIDGE_DRAG_BPS = 2.75   # Relay.link ~$0.055 on $200 cross-L2 rebalance
DEFAULT_POLYGON_GAS_USD = 0.002        # Gasless Relayer V2 / amortized Polygon tx
DEFAULT_EXTERNAL_GAS_USD: Dict[str, float] = {
    "polymarket": 0.002,
    "predict_fun": 0.008,    # BNB Chain CTF split/merge or approval amortization
    "sx_bet": 0.000,         # Gasless EIP-2612 + off-chain OBv3 matching/cancel
    "limitless": 0.005,      # Base L2 CTF split/merge amortization
    "forecastex": 0.000,     # Off-chain CFTC/CIRO clearinghouse
    "stx_ontario": 0.000,    # Off-chain AGCO/iGO P2P matching
}

WALKOVER_50_50_MAX_PRICE = 0.48        # Guarantees >= +$0.02/sh windfall on cancel vs VOID venue
MIN_MAKER_ANCHOR_DEPTH_MULT = 4.0      # Polymarket L2 hedge depth >= 4.0x passive clip notional
MIN_NET_PROFIT_USD = 0.02              # Strict floor above zero after all fees/bridge/gas
SX_ODDS_SCALE = 10**20                 # SX Bet 10^20 = 100% implied probability scale
LIMITLESS_SHARE_SCALE = 1_000_000.0    # Limitless 6-decimal USDC / CTF share scale


# ---------------------------------------------------------------------------
# Exact Multi-Venue Fee, Rebate & L2 Walk Math
# ---------------------------------------------------------------------------

def polymarket_taker_fee_usd(
    shares: float,
    price: float,
    fee_rate_bps: float = 0.0,
    category: str = "",
) -> float:
    """
    Computes exact Polymarket taker fee in USD.
    Uses dynamic per-token `fee_rate_bps` from CLOB/Gamma (`0` on NBA/macro/weather/geopolitics;
    parabolic `rate * p * (1 - p)` on fee-enabled crypto `700 bps` and sports `175 bps`).
    """
    if shares <= 0.0 or price <= 0.0 or price >= 1.0:
        return 0.0
    bps = float(fee_rate_bps or 0.0)
    if bps <= 0.0:
        return 0.0
    rate = bps / 10_000.0
    # Polymarket 2026 parabolic fee curve: fee_usd = shares * rate * p * (1 - p)
    return max(0.0, shares * rate * price * (1.0 - price))


def predict_fun_taker_fee_usd(
    shares: float,
    price: float,
    fee_rate_bps: float = 200.0,
    invite_discount: bool = True,
) -> float:
    """
    Predict.fun `FeeModuleV2` linear tent taker fee:
        Fee_USD = shares * BaseFee * min(p, 1 - p)
    With `feeRateBps = 200` (2.0%) and 10% invite discount -> `BaseFee = 0.018`
    (only `1.8 bps` = `$0.00018/sh` at `p = $0.99`!).
    """
    if shares <= 0.0 or price <= 0.0 or price >= 1.0:
        return 0.0
    base_rate = max(0.0, float(fee_rate_bps) / 10_000.0)
    if invite_discount:
        base_rate *= 0.90
    return max(0.0, shares * base_rate * min(price, 1.0 - price))


def predict_fun_est_maker_rebate_usd(
    shares: float,
    price: float,
    fee_rate_bps: float = 200.0,
    is_crypto_updown: bool = False,
) -> float:
    """
    Predict.fun `0%` maker fee + `25%` instant maker rebate on crypto up/down markets.
    Tracked strictly as `est_unsettled_rebate_usd` — NEVER added to realized cash PnL.
    """
    if not is_crypto_updown or shares <= 0.0 or price <= 0.0 or price >= 1.0:
        return 0.0
    cpty_taker_fee = predict_fun_taker_fee_usd(shares, price, fee_rate_bps=fee_rate_bps, invite_discount=False)
    return 0.25 * cpty_taker_fee


def limitless_taker_fee_usd(
    shares: float,
    price: float,
    fee_enabled: bool = True,
    fee_module_type: str = "COLLATERAL",
) -> float:
    """
    Limitless Exchange taker fee:
      - New `COLLATERAL` fee module (`fee == True`): `0.05 * shares * p * (1 - p)` in USDC.
      - Legacy flat fee module (`fee == True`): `0.03 * shares * p`.
      - Maker (`postOnly`) or `fee == False`: `$0.00`.
    """
    if not fee_enabled or shares <= 0.0 or price <= 0.0 or price >= 1.0:
        return 0.0
    mod = (fee_module_type or "COLLATERAL").strip().upper()
    if mod == "FLAT_LEGACY":
        return max(0.0, 0.03 * shares * price)
    return max(0.0, 0.05 * shares * price * (1.0 - price))


def sx_bet_taker_fee_usd(shares: float, price: float) -> float:
    """SX Bet charges 0.00% Maker and 0.00% Taker commission on all single sports bets."""
    return 0.0


def forecastex_taker_fee_usd(shares: float, price: float, fee_per_contract_usd: float = 0.01) -> float:
    """
    ForecastEx (via Interactive Brokers Canada — CIRO-regulated in Ontario) fee model:
    conservative `$0.01` per `$1.00`-par binary contract (`$0.00` exchange fee + `$0.01` IBKR/clearing cap).
    """
    if shares <= 0.0 or price <= 0.0 or price >= 1.0:
        return 0.0
    return max(0.0, shares * float(fee_per_contract_usd))


def stx_ontario_win_commission_usd(shares: float, price: float, win_commission_rate: float = 0.02) -> float:
    """
    STX (`stxapp.ca` — AGCO / iGaming Ontario licensed P2P sports exchange) worst-case winning-leg
    commission (`2.0%` default on net profit `shares * (1 - p)`), deducted up front in pure-riskless
    worst-case state accounting so `min_omega V_T(omega)` never overstates payout if the STX leg wins.
    """
    if shares <= 0.0 or price <= 0.0 or price >= 1.0 or win_commission_rate <= 0.0:
        return 0.0
    return max(0.0, shares * (1.0 - price) * float(win_commission_rate))


def relay_bridge_drag_usd(notional_usd: float, bridge_bps: float = DEFAULT_RELAY_BRIDGE_DRAG_BPS) -> float:
    """Amortized cross-L2 Relay.link intent rebalance drag (`2.75 bps` = `$0.055` per `$200`)."""
    if notional_usd <= 0.0 or bridge_bps <= 0.0:
        return 0.0
    return notional_usd * (bridge_bps / 10_000.0)


def compute_venue_taker_fee_usd(market: "NormalizedBinaryMarket", shares: float, price: float) -> float:
    v = market.venue.lower()
    if v == "polymarket":
        return polymarket_taker_fee_usd(shares, price, fee_rate_bps=market.fee_rate_bps, category=market.category)
    if v == "predict_fun":
        return predict_fun_taker_fee_usd(
            shares,
            price,
            fee_rate_bps=market.fee_rate_bps,
            invite_discount=market.invite_fee_discount,
        )
    if v == "limitless":
        return limitless_taker_fee_usd(
            shares,
            price,
            fee_enabled=market.fee_enabled,
            fee_module_type=market.fee_module_type,
        )
    if v == "sx_bet":
        return sx_bet_taker_fee_usd(shares, price)
    if v == "forecastex":
        return forecastex_taker_fee_usd(shares, price)
    if v == "stx_ontario":
        rate = (float(market.fee_rate_bps) / 10_000.0) if market.fee_rate_bps > 0.0 else 0.02
        return stx_ontario_win_commission_usd(shares, price, win_commission_rate=rate)
    return 0.0


# ---------------------------------------------------------------------------
# Normalized Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderLevel:
    price: float
    size: float  # In shares ($1.00 par payout per share)


@dataclass
class L2WalkFill:
    filled: bool
    requested_shares: float
    filled_shares: float
    gross_cost_usd: float
    vwap_price: float
    worst_price: float
    taker_fee_usd: float
    total_book_shares: float
    total_book_notional_usd: float


def walk_asks_for_shares(
    asks: Sequence[OrderLevel],
    target_shares: float,
    market: "NormalizedBinaryMarket",
) -> L2WalkFill:
    """Walks sorted ask levels to buy exact `target_shares`, computing exact per-level taker fees."""
    clean = sorted(
        [lvl for lvl in asks if 0.0001 < lvl.price < 0.9999 and lvl.size > 1e-6],
        key=lambda x: x.price,
    )
    total_sh = sum(x.size for x in clean)
    total_notional = sum(x.price * x.size for x in clean)
    if target_shares <= 0.0 or not clean:
        return L2WalkFill(False, target_shares, 0.0, 0.0, 1.0, 1.0, 0.0, total_sh, total_notional)

    rem = target_shares
    cost = 0.0
    fees = 0.0
    worst = clean[0].price
    for lvl in clean:
        take = min(rem, lvl.size)
        cost += take * lvl.price
        fees += compute_venue_taker_fee_usd(market, take, lvl.price)
        worst = lvl.price
        rem -= take
        if rem <= 1e-7:
            break

    filled_sh = target_shares - max(0.0, rem)
    if rem > 1e-5 or filled_sh <= 0.0:
        return L2WalkFill(False, target_shares, filled_sh, cost, cost / max(filled_sh, 1e-9), worst, fees, total_sh, total_notional)

    return L2WalkFill(
        filled=True,
        requested_shares=target_shares,
        filled_shares=filled_sh,
        gross_cost_usd=cost,
        vwap_price=cost / filled_sh,
        worst_price=worst,
        taker_fee_usd=fees,
        total_book_shares=total_sh,
        total_book_notional_usd=total_notional,
    )


def walk_bids_for_unwind(
    bids: Sequence[OrderLevel],
    shares_to_sell: float,
    market: "NormalizedBinaryMarket",
) -> Tuple[float, float]:
    """
    Walks sorted bid levels to immediately unwind a raced single-leg fill.
    Returns `(net_proceeds_usd, taker_fee_paid_usd)`.
    """
    clean = sorted(
        [lvl for lvl in bids if 0.0001 < lvl.price < 0.9999 and lvl.size > 1e-6],
        key=lambda x: x.price,
        reverse=True,
    )
    if shares_to_sell <= 0.0:
        return (0.0, 0.0)
    if not clean:
        return (0.0, 0.0)

    rem = shares_to_sell
    proceeds = 0.0
    fees = 0.0
    for lvl in clean:
        sell = min(rem, lvl.size)
        fee = compute_venue_taker_fee_usd(market, sell, lvl.price)
        proceeds += sell * lvl.price - fee
        fees += fee
        rem -= sell
        if rem <= 1e-7:
            break
    # Any residual shares beyond L2 bids suffer conservative 5c emergency haircut below lowest bid
    if rem > 1e-7:
        floor_px = max(0.01, clean[-1].price - 0.05)
        fee = compute_venue_taker_fee_usd(market, rem, floor_px)
        proceeds += rem * floor_px - fee
        fees += fee
    return (max(0.0, proceeds), fees)


@dataclass
class NormalizedBinaryMarket:
    venue: str                        # "polymarket" | "predict_fun" | "sx_bet" | "limitless"
    market_id: str
    slug: str
    title: str
    category: str                     # "crypto" | "sports" | "politics" | "macro" | "other"
    yes_label: str = "YES"
    no_label: str = "NO"
    yes_asks: List[OrderLevel] = field(default_factory=list)
    yes_bids: List[OrderLevel] = field(default_factory=list)
    no_asks: List[OrderLevel] = field(default_factory=list)
    no_bids: List[OrderLevel] = field(default_factory=list)
    # Fee & execution metadata
    fee_rate_bps: float = 0.0
    fee_enabled: bool = True
    fee_module_type: str = "COLLATERAL"
    invite_fee_discount: bool = True
    taker_delay_ms: float = 0.0
    min_shares: float = 5.0
    supports_split_merge: bool = True
    is_yield_bearing: bool = False
    # Oracle & Double-Zero Gate metadata
    asset: str = ""                   # e.g. "BTC", "ETH", "SOL", "BNB", or canonical sports matchup key
    horizon: str = ""                 # e.g. "5m", "15m", "1h", "4h", "daily", "match"
    oracle_family: str = ""           # e.g. "chainlink_60s_twap", "binance_spot_candle", "cf_brti", "official_boxscore", "uma"
    oracle_stream_url: str = ""       # e.g. "https://data.chain.link/streams/btc-usd-twap-60s-streams"
    spot_reference_usd: float = 0.0
    strike_price: Optional[float] = None
    start_ts: Optional[int] = None
    end_ts: Optional[int] = None
    cancel_rule: str = "50_50"        # "50_50" (Polymarket) vs "VOID" (SX Bet / Betfair / Matchbook)
    tennis_retirement_rule: str = "NA"  # "ONE_BALL" (Polymarket/Kalshi) vs "ONE_SET" (SX Bet/Exchanges)
    sport: str = ""                   # "nba", "nfl", "tennis", "soccer", "nhl", "mlb", ...
    completed_sets: int = 0
    is_player_prop: bool = False
    is_listed_pitcher: bool = False
    game_live: bool = False
    player_participated: bool = False
    has_unlisted_draw: bool = False   # True on 2-way regulation markets where regulation tie loses/splits mismatch
    # Native cross-venue linking metadata
    condition_id: str = ""
    polymarket_condition_ids: List[str] = field(default_factory=list)
    is_poly_arbitrage: bool = False
    external_slug: str = ""
    rules_hash: str = ""
    clarification_count: int = 0
    yes_token_id: str = ""
    no_token_id: str = ""
    # Production microstructure, multi-leg partition & telemetry provenance metadata
    tick_size: float = 0.001
    lot_size: float = 0.01
    quote_ts_ms: int = 0
    collateral_asset: str = "USDC"    # "USDC.e" | "USDC" | "USDT" | "vUSDT" | "USD" | "CAD"
    settlement_delay_hours: float = 2.0
    suspended: bool = False
    expired: bool = False
    neg_risk: bool = False
    partition_group_id: str = ""      # Shared event/slate ID for 2..6-leg exhaustive partitions
    partition_label: str = ""         # Canonical mutually-exclusive outcome label within partition
    partition_expected_legs: int = 0  # Expected total mutually-exclusive outcomes in exhaustive slate
    data_origin: str = "LIVE_VERIFIED"  # "LIVE_VERIFIED" | "OFFLINE_SYNTHETIC" | "REGULATORY_PUBLIC_DELAYED"
    outcomes_canonicalized: bool = False

    def has_crossed_or_invalid_book(self) -> bool:
        """Returns True if either YES or NO L2 book has crossed prices (`best_bid >= best_ask`) or out-of-bounds quotes."""
        for asks, bids in ((self.yes_asks, self.yes_bids), (self.no_asks, self.no_bids)):
            for lvl in (*asks, *bids):
                if not (0.0 < lvl.price < 1.0) or lvl.size <= 0.0:
                    return True
            if asks and bids and bids[0].price >= asks[0].price - 1e-9:
                return True
        return False

    def canonicalize_outcomes_idempotent(self) -> "NormalizedBinaryMarket":
        """
        Deterministically and idempotently aligns binary `(yes_label, no_label)` polarity:
          - Generic pairs (`yes/no`, `up/down`, `over/under`, `true/false`) ensure the affirmative token is `YES`.
          - Non-generic two-sided pairs (sports teams, dual-barrier races like `$1,000` vs `$3,000`, named candidates)
            sort canonically by `(normalize_team_token(label), label.lower())`.
          - Calling this method 1, 2, or N times yields the exact same state (`idempotent`).
        """
        y_low = (self.yes_label or "").strip().lower()
        n_low = (self.no_label or "").strip().lower()
        generic_pos = {"yes", "up", "over", "true"}
        generic_neg = {"no", "down", "under", "false"}
        should_swap = False
        if y_low in generic_pos and n_low in generic_neg:
            should_swap = False
        elif y_low in generic_neg and n_low in generic_pos:
            should_swap = True
        elif y_low not in (generic_pos | generic_neg) and n_low not in (generic_pos | generic_neg) and y_low != n_low:
            ky = (normalize_team_token(self.yes_label), y_low)
            kn = (normalize_team_token(self.no_label), n_low)
            should_swap = ky > kn
        if should_swap:
            self.yes_label, self.no_label = self.no_label, self.yes_label
            self.yes_token_id, self.no_token_id = self.no_token_id, self.yes_token_id
            self.yes_asks, self.no_asks = self.no_asks, self.yes_asks
            self.yes_bids, self.no_bids = self.no_bids, self.yes_bids
        self.outcomes_canonicalized = True
        return self

    def compute_book_metrics(self) -> Dict[str, float]:
        """Computes spread, top-of-book mid, and total L2 depth in USD across YES and NO ladders."""
        y_best_ask = self.yes_asks[0].price if self.yes_asks else None
        y_best_bid = self.yes_bids[0].price if self.yes_bids else None
        n_best_ask = self.no_asks[0].price if self.no_asks else None
        n_best_bid = self.no_bids[0].price if self.no_bids else None
        y_spread_bps = (
            max(0.0, (y_best_ask - y_best_bid) * 10_000.0)
            if (y_best_ask is not None and y_best_bid is not None)
            else 10_000.0
        )
        n_spread_bps = (
            max(0.0, (n_best_ask - n_best_bid) * 10_000.0)
            if (n_best_ask is not None and n_best_bid is not None)
            else 10_000.0
        )
        y_depth_usd = sum(lvl.price * lvl.size for lvl in self.yes_asks) + sum(
            lvl.price * lvl.size for lvl in self.yes_bids
        )
        n_depth_usd = sum(lvl.price * lvl.size for lvl in self.no_asks) + sum(
            lvl.price * lvl.size for lvl in self.no_bids
        )
        return {
            "yes_spread_bps": round(y_spread_bps, 2),
            "no_spread_bps": round(n_spread_bps, 2),
            "yes_depth_usd": round(y_depth_usd, 4),
            "no_depth_usd": round(n_depth_usd, 4),
            "total_depth_usd": round(y_depth_usd + n_depth_usd, 4),
        }


# ---------------------------------------------------------------------------
# Oracle, Sport & Rule Extraction Helpers
# ---------------------------------------------------------------------------

_CHAINLINK_URL_RE = re.compile(r"https://data\.chain\.link/streams/[a-z0-9\-]+", re.IGNORECASE)
_PRICE_NUM_RE = re.compile(r"\$([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]{2,7}(?:\.[0-9]+)?)")
_UNIX_TAIL_RE = re.compile(r"-(\d{10})$")


def normalize_rules_sha256(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    if not cleaned:
        return ""
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


_US_PRO_MASCOTS: Tuple[str, ...] = (
    "trail blazers", "red sox", "white sox", "blue jays", "maple leafs", "golden knights", "blue jackets", "red wings",
    "celtics", "bucks", "lakers", "clippers", "warriors", "knicks", "nets", "76ers", "sixers", "raptors", "bulls",
    "cavaliers", "pistons", "pacers", "hawks", "heat", "magic", "wizards", "hornets", "nuggets", "timberwolves",
    "thunder", "jazz", "suns", "kings", "mavericks", "rockets", "grizzlies", "pelicans", "spurs",
    "seahawks", "cardinals", "49ers", "rams", "cowboys", "eagles", "giants", "commanders", "packers", "bears",
    "lions", "vikings", "falcons", "panthers", "saints", "buccaneers", "bills", "dolphins", "patriots", "jets",
    "ravens", "bengals", "browns", "steelers", "texans", "colts", "jaguars", "titans", "broncos", "chiefs",
    "raiders", "chargers",
    "canucks", "flyers", "bruins", "rangers", "oilers", "flames", "penguins", "capitals", "lightning",
    "hurricanes", "devils", "islanders", "senators", "canadiens", "sabres", "blackhawks", "wild", "blues",
    "predators", "stars", "avalanche", "kraken", "ducks", "sharks", "mammoth",
    "yankees", "dodgers", "mets", "braves", "phillies", "astros", "cubs", "padres", "mariners", "orioles",
    "guardians", "tigers", "twins", "royals", "angels", "athletics", "brewers", "reds", "pirates", "marlins",
    "nationals", "diamondbacks", "rockies",
)


def normalize_team_token(name: str) -> str:
    s = (name or "").lower().strip()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for mascot in _US_PRO_MASCOTS:
        if s == mascot or s.endswith(" " + mascot):
            return "76ers" if mascot == "sixers" else mascot
    return s


def canonical_matchup_key(team_a: str, team_b: str, game_ts: Optional[int] = None) -> str:
    ta = normalize_team_token(team_a)
    tb = normalize_team_token(team_b)
    if not ta or not tb:
        return ""
    pair = "::".join(sorted([ta, tb]))
    if game_ts and game_ts > 0:
        day_bucket = int(game_ts) // 86400
        return f"{pair}@{day_bucket}"
    return pair


def infer_crypto_oracle_signature(title: str, description: str, slug: str = "") -> Tuple[str, str, str, str]:
    """
    Infers `(asset, horizon, oracle_family, oracle_stream_url)` from market text/slug.
    Crucially distinguishes Chainlink 60s-TWAP (`5m/15m/4h`) from Binance 1m/1h spot candle closes!
    """
    title_slug = f"{title} {slug}".lower()
    blob = f"{title} {slug} {description}".lower()
    asset = ""
    for sym, tok, usdt_tok in (
        ("BTC", ("bitcoin", "btc-", "btc/", "btcusdt", "btc "), "btcusdt"),
        ("ETH", ("ethereum", "eth-", "eth/", "ethusdt", "eth "), "ethusdt"),
        ("SOL", ("solana", "sol-", "sol/", "solusdt", "sol "), "solusdt"),
        ("BNB", ("bnb-", "bnb/", "bnbusdt", "bnb "), "bnbusdt"),
        ("XRP", ("xrp-", "xrp/", "xrpusdt", "xrp "), "xrpusdt"),
        ("DOGE", ("dogecoin", "doge-", "doge/", "dogeusdt", "doge "), "dogeusdt"),
        ("HYPE", ("hyperliquid", "hype-", "hype/", "hypeusdt", "hype "), "hypeusdt"),
    ):
        if any(t in title_slug for t in tok) or usdt_tok in blob:
            asset = sym
            break

    horizon = ""
    if "15-min" in blob or "15m-" in blob or "15 min" in blob:
        horizon = "15m"
    elif "5-min" in blob or "5m-" in blob or "5 min" in blob:
        horizon = "5m"
    elif "4h" in blob or "4 hour" in blob or "4-hour" in blob:
        horizon = "4h"
    elif "hourly" in blob or "1 hour" in blob or "1h" in blob or "pm-et" in blob or "am-et" in blob:
        horizon = "1h"
    elif "daily" in blob or "-on-" in slug.lower():
        horizon = "daily"

    m_url = _CHAINLINK_URL_RE.search(description or "")
    stream_url = m_url.group(0).lower() if m_url else ""
    if not asset and not stream_url:
        return ("", "", "", "")
    if stream_url or "chainlink" in blob or "60-second twap" in blob or "twap-60s" in blob:
        return (asset, horizon, "chainlink_60s_twap", stream_url)
    if "binance" in blob:
        return (asset, horizon, "binance_spot_candle", "")
    if "brti" in blob or "cf benchmarks" in blob:
        return (asset, horizon, "cf_brti_60s", "")
    if "deribit" in blob:
        return (asset, horizon, "deribit_30m_twap", "")
    return (asset, horizon, "", "")


# ---------------------------------------------------------------------------
# 5 Programmatic "Double-Zero" Verification Gates (`CrossVenueRuleVerifier`)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RuleVerificationResult:
    passed: bool
    gate_failures: Tuple[str, ...]
    corridor_width_usd: float = 0.0
    cancel_windfall_per_share: float = 0.0
    reason: str = "ALL_5_GATES_PASSED"


class CrossVenueRuleVerifier:
    """
    Programmatically enforces Dominus's 5 Zero-Double-Zero Cross-Venue Settlement Gates.
    If ANY gate fails, the pair is hard-quarantined before reaching Stage 2 (`EXECUTABLE_NET_L2`).
    """

    def __init__(
        self,
        *,
        min_cross_oracle_basis_pct: float = 0.0050,  # 0.50% spot corridor buffer (Chainlink vs BRTI/Binance)
        walkover_50_50_max_px: float = WALKOVER_50_50_MAX_PRICE,
    ) -> None:
        self.min_cross_oracle_basis_pct = float(min_cross_oracle_basis_pct)
        self.walkover_50_50_max_px = float(walkover_50_50_max_px)

    def verify_pair(
        self,
        leg_a: NormalizedBinaryMarket,
        leg_b: NormalizedBinaryMarket,
        *,
        side_a: str,      # "YES" or "NO" bought on leg_a
        side_b: str,      # "YES" or "NO" bought on leg_b
        price_a: float,
        price_b: float,
        max_end_ts_skew_sec: int = 60,
    ) -> RuleVerificationResult:
        failures: List[str] = []
        corridor_width = 0.0
        cancel_windfall = 0.0

        # Ensure opposite logical outcomes unless strike corridor super-replication is used
        same_strike = (
            leg_a.strike_price is None
            or leg_b.strike_price is None
            or abs(float(leg_a.strike_price) - float(leg_b.strike_price)) < 1e-6
        )
        if same_strike and side_a.upper() == side_b.upper():
            failures.append("GATE1_IDENTICAL_SIDE_NOT_HEDGED")

        # -------------------------------------------------------------------
        # GATE 1: Strict Oracle, Timestamp & Rule-Hash Identity
        # -------------------------------------------------------------------
        _generic_labels = {"yes", "no", "up", "down", "over", "under", "true", "false"}
        if (
            leg_a.yes_label.strip().lower() not in _generic_labels
            and leg_b.yes_label.strip().lower() not in _generic_labels
        ):
            if normalize_team_token(leg_a.yes_label) != normalize_team_token(leg_b.yes_label):
                failures.append(
                    f"GATE1_TEAM_OUTCOME_ORDER_MISMATCH({leg_a.yes_label}!={leg_b.yes_label})"
                )

        if leg_a.end_ts and leg_b.end_ts:
            skew = abs(int(leg_a.end_ts) - int(leg_b.end_ts))
            if leg_a.category == "crypto" or leg_b.category == "crypto":
                allowed_skew = 0
            elif leg_a.category == "sports" and leg_b.category == "sports":
                # Sports venues report tip-off (`gameStartTime`) vs +24h expiration buffer
                allowed_skew = 36 * 3600
            else:
                allowed_skew = max_end_ts_skew_sec
            if skew > allowed_skew:
                failures.append(f"GATE1_TIMESTAMP_MISMATCH({skew}s>{allowed_skew}s)")

        if leg_a.clarification_count > 0 or leg_b.clarification_count > 0:
            if not (leg_a.rules_hash and leg_b.rules_hash and leg_a.rules_hash == leg_b.rules_hash):
                failures.append("GATE1_UMA_CLARIFICATION_DRIFT")

        explicitly_linked_cond = bool(
            (leg_a.condition_id and leg_a.condition_id.lower() in {c.lower() for c in leg_b.polymarket_condition_ids})
            or (leg_b.condition_id and leg_b.condition_id.lower() in {c.lower() for c in leg_a.polymarket_condition_ids})
        )
        if leg_a.venue == "polymarket" and leg_a.condition_id and leg_b.polymarket_condition_ids:
            if leg_a.condition_id.lower() not in {c.lower() for c in leg_b.polymarket_condition_ids}:
                failures.append("GATE1_CONDITION_ID_STRIKE_MISMATCH")
        if leg_b.venue == "polymarket" and leg_b.condition_id and leg_a.polymarket_condition_ids:
            if leg_b.condition_id.lower() not in {c.lower() for c in leg_a.polymarket_condition_ids}:
                failures.append("GATE1_CONDITION_ID_STRIKE_MISMATCH")
        if leg_a.polymarket_condition_ids and leg_b.polymarket_condition_ids:
            if not ({c.lower() for c in leg_a.polymarket_condition_ids} & {c.lower() for c in leg_b.polymarket_condition_ids}):
                failures.append("GATE1_CONDITION_ID_STRIKE_MISMATCH")
        same_rules_sha256 = bool(leg_a.rules_hash and leg_b.rules_hash and leg_a.rules_hash == leg_b.rules_hash)

        both_crypto = leg_a.category == "crypto" or leg_b.category == "crypto"
        if both_crypto:
            if leg_a.asset and leg_b.asset and leg_a.asset != leg_b.asset:
                failures.append(f"GATE1_ASSET_MISMATCH({leg_a.asset}!={leg_b.asset})")
            if leg_a.horizon and leg_b.horizon and leg_a.horizon != leg_b.horizon:
                failures.append(f"GATE1_HORIZON_MISMATCH({leg_a.horizon}!={leg_b.horizon})")
            if not leg_a.oracle_family or not leg_b.oracle_family:
                if not (explicitly_linked_cond and same_rules_sha256 and leg_a.clarification_count == 0 and leg_b.clarification_count == 0):
                    failures.append("GATE1_UNKNOWN_CRYPTO_ORACLE")
            elif leg_a.oracle_family == leg_b.oracle_family:
                if (
                    leg_a.oracle_stream_url
                    and leg_b.oracle_stream_url
                    and leg_a.oracle_stream_url != leg_b.oracle_stream_url
                ):
                    failures.append("GATE1_CHAINLINK_STREAM_URL_MISMATCH")
            else:
                # ---------------------------------------------------------------
                # GATE 2: Cross-Oracle Strike Dominance Corridor (`dK >= B_max`)
                # ---------------------------------------------------------------
                if leg_a.strike_price is None or leg_b.strike_price is None:
                    failures.append(
                        f"GATE1_CROSS_ORACLE_NO_STRIKE_CORRIDOR({leg_a.oracle_family}!={leg_b.oracle_family})"
                    )
                else:
                    # Must buy YES (> K_low) on one venue and NO (< K_high) on the other with K_high - K_low >= B_max
                    yes_strike = leg_a.strike_price if side_a.upper() == "YES" else leg_b.strike_price
                    no_strike = leg_b.strike_price if side_b.upper() == "NO" else leg_a.strike_price
                    if side_a.upper() == side_b.upper():
                        failures.append("GATE2_CORRIDOR_REQUIRES_YES_LOW_AND_NO_HIGH")
                    else:
                        corridor_width = float(no_strike) - float(yes_strike)
                        ref_spot = max(leg_a.spot_reference_usd, leg_b.spot_reference_usd, float(yes_strike))
                        b_max = self.min_cross_oracle_basis_pct * ref_spot
                        if corridor_width + 1e-9 < b_max:
                            failures.append(
                                f"GATE2_INSUFFICIENT_ORACLE_CORRIDOR(dK={corridor_width:.2f}<B_max={b_max:.2f})"
                            )
        else:
            # Non-crypto markets: verify explicit cross-link, deterministic sports box-score, or exact rules_hash + strike parity
            explicitly_linked = (
                (leg_a.is_poly_arbitrage and bool(leg_a.rules_hash))
                or (leg_b.is_poly_arbitrage and bool(leg_b.rules_hash))
                or explicitly_linked_cond
            )
            same_rules_hash = bool(leg_a.rules_hash and leg_b.rules_hash and leg_a.rules_hash == leg_b.rules_hash)
            both_official_sports = leg_a.category == "sports" and leg_b.category == "sports" and bool(leg_a.asset and leg_a.asset == leg_b.asset)
            if not (explicitly_linked or same_rules_hash or both_official_sports):
                failures.append("GATE1_UNVERIFIED_NON_CRYPTO_RULES")
            elif same_rules_hash and not explicitly_linked and not both_official_sports:
                nums_a = re.findall(r"\d+(?:\.\d+)?", (leg_a.title or "").replace(",", ""))
                nums_b = re.findall(r"\d+(?:\.\d+)?", (leg_b.title or "").replace(",", ""))
                if nums_a != nums_b:
                    failures.append(f"GATE1_BOILERPLATE_RULES_STRIKE_MISMATCH({nums_a}!={nums_b})")
            if leg_a.category == "sports" and leg_b.category == "sports":
                if (leg_a.horizon or "match") != (leg_b.horizon or "match"):
                    failures.append(f"GATE1_SPORTS_LINE_TYPE_MISMATCH({leg_a.horizon}!={leg_b.horizon})")

        # -------------------------------------------------------------------
        # GATE 3: 50-50 Cancellation / Walkover Windfall Ceiling & 3-Way Draw Guard
        # -------------------------------------------------------------------
        if leg_a.has_unlisted_draw or leg_b.has_unlisted_draw:
            failures.append("GATE3_UNHEDGED_REGULATION_DRAW_PARTITION")

        if leg_a.cancel_rule != leg_b.cancel_rule:
            if leg_a.cancel_rule == "50_50" and leg_b.cancel_rule == "VOID":
                px_50_50 = float(price_a)
            elif leg_b.cancel_rule == "50_50" and leg_a.cancel_rule == "VOID":
                px_50_50 = float(price_b)
            else:
                px_50_50 = 1.0

            cancel_windfall = 0.50 - px_50_50
            if px_50_50 > self.walkover_50_50_max_px + 1e-9:
                failures.append(
                    f"GATE3_50_50_WALKOVER_FAVORITE_EXPOSURE(p_50_50={px_50_50:.3f}>{self.walkover_50_50_max_px:.2f})"
                )

        # -------------------------------------------------------------------
        # GATE 4: Tennis Set-2+ Retirement Convergence (`completed_sets >= 1`)
        # -------------------------------------------------------------------
        is_tennis = leg_a.sport.lower() == "tennis" or leg_b.sport.lower() == "tennis"
        if is_tennis and leg_a.tennis_retirement_rule != leg_b.tennis_retirement_rule:
            completed_sets = min(int(leg_a.completed_sets), int(leg_b.completed_sets))
            if completed_sets < 1:
                failures.append(f"GATE4_TENNIS_PRE_SET2_RETIREMENT_TRAP(completed_sets={completed_sets}<1)")

        # -------------------------------------------------------------------
        # GATE 5: Live Participation Player-Prop & MLB Listed-Pitcher Gate
        # -------------------------------------------------------------------
        if leg_a.is_player_prop or leg_b.is_player_prop or leg_a.is_listed_pitcher or leg_b.is_listed_pitcher:
            live_confirmed = (
                leg_a.game_live
                and leg_b.game_live
                and leg_a.player_participated
                and leg_b.player_participated
            )
            if not live_confirmed:
                failures.append("GATE5_PREGAME_PROP_OR_LISTED_PITCHER_VOID_TRAP")

        if failures:
            return RuleVerificationResult(
                passed=False,
                gate_failures=tuple(failures),
                corridor_width_usd=corridor_width,
                cancel_windfall_per_share=cancel_windfall,
                reason=";".join(failures),
            )
        return RuleVerificationResult(
            passed=True,
            gate_failures=(),
            corridor_width_usd=corridor_width,
            cancel_windfall_per_share=cancel_windfall,
            reason="ALL_5_GATES_PASSED",
        )


# ---------------------------------------------------------------------------
# Read-Only Async HTTP Transport (`aiohttp` primary, `urllib` stdlib fallback)
# ---------------------------------------------------------------------------

JsonFetcher = Callable[[str, Optional[Mapping[str, str]], float], Awaitable[Tuple[int, Any, float]]]


class ReadOnlyHttpClient:
    """
    Strictly GET-only HTTP JSON client. Never exposes POST/PUT/DELETE methods,
    enforcing read-only shadow safety at the transport layer.
    """

    def __init__(
        self,
        user_agent: str = "DominusCrossVenueShadowProbe/1.0",
        *,
        network_disabled: bool = False,
    ) -> None:
        self.user_agent = user_agent
        self.network_disabled = bool(network_disabled)
        self._session: Any = None

    async def __aenter__(self) -> "ReadOnlyHttpClient":
        if (
            not self.network_disabled
            and _aiohttp is not None
            and hasattr(_aiohttp, "ClientTimeout")
            and self._session is None
        ):
            timeout = _aiohttp.ClientTimeout(total=10.0)
            self._session = _aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def get_json(
        self,
        url: str,
        headers: Optional[Mapping[str, str]] = None,
        timeout_sec: float = 8.0,
    ) -> Tuple[int, Any, float]:
        if self.network_disabled:
            raise RuntimeError(f"NETWORK_DISABLED_MODE_ACTIVE: blocked outbound GET {url}")
        merged = {"User-Agent": self.user_agent, "Accept": "application/json"}
        if headers:
            merged.update(headers)
        t0 = time.perf_counter()
        if self._session is not None:
            try:
                async with self._session.get(url, headers=merged, timeout=timeout_sec) as resp:
                    raw = await resp.text()
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    data = json.loads(raw) if raw else None
                    return (int(resp.status), data, elapsed_ms)
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                logger.debug("GET failed %s: %s", url, exc)
                return (0, {"error": str(exc)}, elapsed_ms)

        def _sync_get() -> Tuple[int, Any, float]:
            s0 = time.perf_counter()
            req = urllib.request.Request(url, headers=merged, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                    body = resp.read().decode("utf-8")
                    ms = (time.perf_counter() - s0) * 1000.0
                    return (int(resp.status), json.loads(body) if body else None, ms)
            except urllib.error.HTTPError as he:
                ms = (time.perf_counter() - s0) * 1000.0
                try:
                    err_body = json.loads(he.read().decode("utf-8"))
                except Exception:
                    err_body = {"error": str(he)}
                return (int(he.code), err_body, ms)
            except Exception as exc:
                ms = (time.perf_counter() - s0) * 1000.0
                return (0, {"error": str(exc)}, ms)

        return await asyncio.to_thread(_sync_get)


# ---------------------------------------------------------------------------
# Read-Only Venue Adapters (Limitless, SX Bet OBv3, Predict.fun, Polymarket)
# ---------------------------------------------------------------------------

_SPORTS_DERIVATIVE_SLUG_TOKENS: Tuple[str, ...] = (
    "-spread-", "-total-", "-1h-", "-2h-", "-1p-", "-2p-", "-3p-",
    "-q1-", "-q2-", "-q3-", "-q4-", "-f5-", "-set1", "-set2", "-map1", "-map2",
    "-handicap", "-puckline", "-runline", "-over-", "-under-",
)
_SPORTS_DERIVATIVE_TITLE_TOKENS: Tuple[str, ...] = (
    "spread:", "handicap", "1st half", "2nd half", "first half",
    "1st period", "2nd period", "3rd period", "1st quarter", "1st 5 innings",
    "set 1", "set 2", "map 1", "map 2", "o/u ", "over/under", "(-", "(+",
)


def is_sports_derivative_line(slug: str, title: str) -> bool:
    """Detects point spreads, pucklines, runlines, totals, and partial-period/set markets so they never pair with full-game moneylines."""
    s_low = (slug or "").lower()
    t_low = (title or "").lower()
    return any(tok in s_low for tok in _SPORTS_DERIVATIVE_SLUG_TOKENS) or any(
        tok in t_low for tok in _SPORTS_DERIVATIVE_TITLE_TOKENS
    )


def parse_limitless_market(raw: Mapping[str, Any], orderbook: Optional[Mapping[str, Any]] = None) -> Optional[NormalizedBinaryMarket]:
    """Parses a live Limitless `/markets/active` item + optional `/markets/{slug}/orderbook`."""
    slug = str(raw.get("slug") or "").strip()
    if not slug or raw.get("expired") is True:
        return None
    if str(raw.get("tradeType") or "clob").lower() != "clob":
        return None

    title = str(raw.get("title") or slug)
    desc = str(raw.get("description") or "")
    meta = raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {}
    settings = raw.get("settings") if isinstance(raw.get("settings"), Mapping) else {}
    venue_info = raw.get("venue") if isinstance(raw.get("venue"), Mapping) else {}
    oracle_meta = raw.get("priceOracleMetadata") if isinstance(raw.get("priceOracleMetadata"), Mapping) else {}
    rules_watch = (
        meta.get("externalRulesWatch")
        if isinstance(meta.get("externalRulesWatch"), Mapping)
        else (raw.get("externalRulesWatch") if isinstance(raw.get("externalRulesWatch"), Mapping) else {})
    )
    cl_stream = meta.get("chainlinkDataStream") if isinstance(meta.get("chainlinkDataStream"), Mapping) else {}

    cats = [str(c).lower() for c in (raw.get("categories") or [])]
    asset, horizon, oracle_family, stream_url = infer_crypto_oracle_signature(title, desc, slug)
    if not asset and oracle_meta.get("ticker"):
        asset = str(oracle_meta["ticker"]).strip().upper()
    category = (
        "crypto"
        if ("crypto" in cats or str(oracle_meta.get("assetType") or "").upper() == "CRYPTO" or bool(asset))
        else ("sports" if "sports" in cats else "other")
    )
    if oracle_meta.get("chainlinkStreamUrl") or cl_stream.get("streamUrl"):
        stream_url = str(oracle_meta.get("chainlinkStreamUrl") or cl_stream.get("streamUrl")).lower()
        oracle_family = "chainlink_60s_twap"
    elif str(oracle_meta.get("chartSource") or "").lower() == "binance" and not oracle_family:
        oracle_family = "binance_spot_candle"

    exp_raw = raw.get("expirationTimestamp")
    end_ts = int(float(exp_raw) / 1000.0) if exp_raw and float(exp_raw) > 1e11 else (int(float(exp_raw)) if exp_raw else None)

    min_size_raw = float(meta.get("minSize") or settings.get("minSize") or 5_000_000)
    min_shares = max(1.0, min_size_raw / LIMITLESS_SHARE_SCALE)
    taker_delay_ms = float(
        meta.get("takerDelayMs") if meta.get("takerDelayMs") is not None else (settings.get("takerDelayMs") or 0.0)
    )
    strike_price: Optional[float] = None
    if meta.get("openPrice") not in (None, ""):
        try:
            strike_price = float(meta["openPrice"])
        except (TypeError, ValueError):
            strike_price = None
    fee_enabled = bool(meta.get("fee", True))
    fee_module_type = str(venue_info.get("feeModuleType") or "COLLATERAL")

    yes_asks: List[OrderLevel] = []
    yes_bids: List[OrderLevel] = []
    no_asks: List[OrderLevel] = []
    no_bids: List[OrderLevel] = []

    if isinstance(orderbook, Mapping):
        for a in orderbook.get("asks") or []:
            px = float(a.get("price") or 0.0)
            sz = float(a.get("size") or 0.0) / LIMITLESS_SHARE_SCALE
            if 0.0 < px < 1.0 and sz > 0.0:
                yes_asks.append(OrderLevel(px, sz))
                no_bids.append(OrderLevel(round(1.0 - px, 6), sz))
        for b in orderbook.get("bids") or []:
            px = float(b.get("price") or 0.0)
            sz = float(b.get("size") or 0.0) / LIMITLESS_SHARE_SCALE
            if 0.0 < px < 1.0 and sz > 0.0:
                yes_bids.append(OrderLevel(px, sz))
                no_asks.append(OrderLevel(round(1.0 - px, 6), sz))
    else:
        tp_buy = ((raw.get("tradePrices") or {}).get("buy") or {}).get("market") or []
        if len(tp_buy) >= 2:
            p_yes, p_no = float(tp_buy[0]), float(tp_buy[1])
            if 0.0 < p_yes < 1.0:
                yes_asks.append(OrderLevel(p_yes, min_shares))
            if 0.0 < p_no < 1.0:
                no_asks.append(OrderLevel(p_no, min_shares))
        tp_sell = ((raw.get("tradePrices") or {}).get("sell") or {}).get("market") or []
        if len(tp_sell) >= 2:
            b_yes, b_no = float(tp_sell[0]), float(tp_sell[1])
            if 0.0 < b_yes < 1.0:
                yes_bids.append(OrderLevel(b_yes, min_shares))
            if 0.0 < b_no < 1.0:
                no_bids.append(OrderLevel(b_no, min_shares))

    tokens = raw.get("tokens") if isinstance(raw.get("tokens"), Mapping) else {}
    clarifications = rules_watch.get("clarificationIds") or []
    y_asks = sorted(yes_asks, key=lambda x: x.price)
    y_bids = sorted(yes_bids, key=lambda x: x.price, reverse=True)
    n_asks = sorted(no_asks, key=lambda x: x.price)
    n_bids = sorted(no_bids, key=lambda x: x.price, reverse=True)
    yes_lbl, no_lbl = "YES", "NO"
    y_tok, n_tok = str(tokens.get("yes") or ""), str(tokens.get("no") or "")
    sport = ""

    if category == "sports":
        blob = f"{slug} {title} {desc} {meta.get('externalSlug') or ''}".lower()
        for sp_tok, sp_val in (
            ("nba-", "nba"), ("nfl-", "nfl"), ("nhl-", "nhl"), ("mlb-", "mlb"),
            ("wta", "tennis"), ("atp", "tennis"), ("tennis", "tennis"),
            ("epl-", "soccer"), ("ucl-", "soccer"), ("soccer", "soccer"),
        ):
            if sp_tok in blob:
                sport = sp_val
                break
        parts = re.split(r"\s+vs\.?\s+", title, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            yes_lbl, no_lbl = parts[0].strip(), parts[1].strip()
            base_mk = canonical_matchup_key(yes_lbl, no_lbl, end_ts)
            if is_sports_derivative_line(slug, title):
                asset = f"DERIVATIVE::{slug}::{base_mk}"
                horizon = "spread_or_period"
            else:
                asset = base_mk
                horizon = "match"
            canon_pair = sorted([normalize_team_token(yes_lbl), normalize_team_token(no_lbl)])
            if normalize_team_token(yes_lbl) != canon_pair[0]:
                yes_lbl, no_lbl = no_lbl, yes_lbl
                y_tok, n_tok = n_tok, y_tok
                y_asks, n_asks = n_asks, y_asks
                y_bids, n_bids = n_bids, y_bids

    return NormalizedBinaryMarket(
        venue="limitless",
        market_id=str(raw.get("id") or slug),
        slug=slug,
        title=title,
        category=category,
        yes_label=yes_lbl,
        no_label=no_lbl,
        yes_asks=y_asks,
        yes_bids=y_bids,
        no_asks=n_asks,
        no_bids=n_bids,
        fee_enabled=fee_enabled,
        fee_module_type=fee_module_type,
        taker_delay_ms=taker_delay_ms,
        min_shares=min_shares,
        supports_split_merge=True,
        asset=asset,
        horizon=horizon,
        oracle_family=oracle_family or ("official_boxscore" if category == "sports" else ""),
        oracle_stream_url=stream_url,
        end_ts=end_ts,
        strike_price=strike_price,
        cancel_rule="50_50",
        tennis_retirement_rule="ONE_BALL" if sport == "tennis" else "NA",
        sport=sport,
        condition_id=str(raw.get("conditionId") or ""),
        is_poly_arbitrage=bool(meta.get("isPolyArbitrage")),
        external_slug=str(meta.get("externalSlug") or raw.get("externalSlug") or ""),
        rules_hash=str(rules_watch.get("rulesHash") or normalize_rules_sha256(desc)),
        clarification_count=len(clarifications) if isinstance(clarifications, Sequence) else 0,
        yes_token_id=y_tok,
        no_token_id=n_tok,
    )


def parse_sx_bet_summary_fixture(
    fixture: Mapping[str, Any],
    *,
    sport_label: str = "",
    sport_id: int = 0,
    league_label: str = "",
    betting_delay_ms: float = 0.0,
    synthetic_top_shares: float = 100.0,
) -> List[NormalizedBinaryMarket]:
    """
    Parses a live SX Bet OBv3 `/summary-v3/{popular,upcoming,inplay}` fixture.
    CRITICAL INVARIANT (Verified Live Nov 2026):
      `o1 = int(bestOddsOutcomeOne) / 10^20` is the highest resting Maker BID on Outcome 1 (`o1 + o2 < 1.0`).
      Therefore:
        - Taker Ask on Outcome 1 (`YES`) = `1.0 - o2`
        - Taker Ask on Outcome 2 (`NO`)  = `1.0 - o1`
        - Maker Bid on Outcome 1 (`YES`) = `o1`
        - Maker Bid on Outcome 2 (`NO`)  = `o2`
    """
    out: List[NormalizedBinaryMarket] = []
    team_one = str(fixture.get("teamOne") or fixture.get("teamOneName") or "").strip()
    team_two = str(fixture.get("teamTwo") or fixture.get("teamTwoName") or "").strip()
    if not team_one or not team_two:
        return out

    # Parse gameTime ISO or unix day
    end_ts: Optional[int] = None
    gt = fixture.get("gameTime") or fixture.get("startDate")
    if isinstance(gt, (int, float)) and gt > 0:
        end_ts = int(gt)
    elif isinstance(gt, str) and gt:
        try:
            dt = datetime.fromisoformat(gt.replace("Z", "+00:00"))
            end_ts = int(dt.timestamp())
        except ValueError:
            end_ts = None
    if end_ts is None and fixture.get("day"):
        end_ts = int(fixture["day"])

    status_code = int(fixture.get("status") or 1)
    game_live = status_code == 2
    score_obj = fixture.get("score") if isinstance(fixture.get("score"), Mapping) else {}
    periods = score_obj.get("periods") if isinstance(score_obj.get("periods"), list) else []
    completed_sets = sum(1 for p in periods if isinstance(p, Mapping) and p.get("isFinished") is True)

    lg_low = (league_label or str(fixture.get("leagueLabel") or "")).lower()
    sp_low = sport_label.lower()
    eff_sport_id = int(sport_id or fixture.get("sportId") or 0)
    sport = "other"
    if eff_sport_id == 5 or "soccer" in sp_low or "premier" in lg_low or "uefa" in lg_low or "mls" in lg_low or "la liga" in lg_low or "serie a" in lg_low or "bundesliga" in lg_low or "ligue 1" in lg_low:
        sport = "soccer"
    elif eff_sport_id == 6 or "tennis" in sp_low or "atp" in lg_low or "wta" in lg_low or "itf" in lg_low:
        sport = "tennis"
    elif eff_sport_id == 1 or "nba" in lg_low or "basketball" in sp_low:
        sport = "nba"
    elif eff_sport_id == 8 or "nfl" in lg_low or "football" in sp_low:
        sport = "nfl"
    elif eff_sport_id == 2 or "nhl" in lg_low or "hockey" in sp_low:
        sport = "nhl"
    elif eff_sport_id == 3 or "mlb" in lg_low or "baseball" in sp_low:
        sport = "mlb"

    match_key = canonical_matchup_key(team_one, team_two, end_ts)
    canon_pair = sorted([normalize_team_token(team_one), normalize_team_token(team_two)])

    for m in fixture.get("markets") or []:
        mtype = str(m.get("marketType") or "").upper()
        mtype_id = int(m.get("type") or 0)
        if mtype != "MONEY_LINE" and mtype_id not in (1, 52, 226):
            continue
        best_obj = m.get("bestOrders") if isinstance(m.get("bestOrders"), Mapping) else m
        o1_raw = best_obj.get("bestOddsOutcomeOne") or m.get("bestOddsOutcomeOne")
        o2_raw = best_obj.get("bestOddsOutcomeTwo") or m.get("bestOddsOutcomeTwo")
        if not o1_raw or not o2_raw:
            continue
        o1 = int(str(o1_raw)) / SX_ODDS_SCALE
        o2 = int(str(o2_raw)) / SX_ODDS_SCALE
        if not (0.0 < o1 < 1.0 and 0.0 < o2 < 1.0):
            continue

        ask_1 = round(1.0 - o2, 6)
        ask_2 = round(1.0 - o1, 6)
        bid_1 = round(o1, 6)
        bid_2 = round(o2, 6)

        # Canonicalize YES = alphabetically first normalized team so cross-venue team order never flips sides!
        out1_norm = normalize_team_token(str(m.get("outcomeOneName") or team_one))
        if out1_norm == canon_pair[0]:
            yes_lbl, no_lbl = str(m.get("outcomeOneName") or team_one), str(m.get("outcomeTwoName") or team_two)
            y_ask, y_bid, n_ask, n_bid = ask_1, bid_1, ask_2, bid_2
        else:
            yes_lbl, no_lbl = str(m.get("outcomeTwoName") or team_two), str(m.get("outcomeOneName") or team_one)
            y_ask, y_bid, n_ask, n_bid = ask_2, bid_2, ask_1, bid_1

        has_unlisted_draw = sport == "soccer"
        out.append(
            NormalizedBinaryMarket(
                venue="sx_bet",
                market_id=str(m.get("marketHash") or fixture.get("id")),
                slug=str(m.get("marketHash") or fixture.get("id")),
                title=f"{team_one} vs {team_two}",
                category="sports",
                yes_label=yes_lbl,
                no_label=no_lbl,
                yes_asks=[OrderLevel(y_ask, synthetic_top_shares)] if 0.0 < y_ask < 1.0 else [],
                yes_bids=[OrderLevel(y_bid, synthetic_top_shares)] if 0.0 < y_bid < 1.0 else [],
                no_asks=[OrderLevel(n_ask, synthetic_top_shares)] if 0.0 < n_ask < 1.0 else [],
                no_bids=[OrderLevel(n_bid, synthetic_top_shares)] if 0.0 < n_bid < 1.0 else [],
                fee_rate_bps=0.0,
                fee_enabled=False,
                taker_delay_ms=betting_delay_ms if game_live else 0.0,
                min_shares=5.0,
                supports_split_merge=False,
                asset=match_key,
                horizon="match",
                oracle_family="official_boxscore",
                end_ts=end_ts,
                cancel_rule="VOID",
                tennis_retirement_rule="ONE_SET" if sport == "tennis" else "NA",
                sport=sport,
                completed_sets=completed_sets,
                is_player_prop=str(m.get("betGroup") or "") == "player-props",
                is_listed_pitcher=False,
                game_live=game_live,
                player_participated=game_live,
                has_unlisted_draw=has_unlisted_draw,
            )
        )
    return out


def parse_predict_fun_market(
    raw: Mapping[str, Any],
    orderbook: Optional[Mapping[str, Any]] = None,
) -> Optional[NormalizedBinaryMarket]:
    """Parses a Predict.fun `/v1/markets` item + optional `/v1/markets/{id}/orderbook`."""
    if str(raw.get("tradingStatus") or "OPEN").upper() != "OPEN":
        return None
    outcomes = raw.get("outcomes") or []
    if len(outcomes) != 2:
        return None

    mid = str(raw.get("id") or "")
    title = str(raw.get("question") or raw.get("title") or mid)
    desc = str(raw.get("description") or "")
    cat_slug = str(raw.get("categorySlug") or "").strip()
    if cat_slug and mid and not cat_slug.endswith(f"-{mid}"):
        slug = f"{cat_slug}-{mid}"
    else:
        slug = cat_slug or mid
    asset, horizon, oracle_family, stream_url = infer_crypto_oracle_signature(title, desc, slug)
    category = "crypto" if asset else "other"
    sport = ""
    yes_lbl = str(outcomes[0].get("name") or "Yes")
    no_lbl = str(outcomes[1].get("name") or "No")
    _generic = {"yes", "no", "up", "down", "over", "under", "true", "false"}
    if not asset:
        blob = f"{cat_slug} {title} {desc}".lower()
        for sp_tok, sp_val in (
            ("nba", "nba"), ("nfl", "nfl"), ("nhl", "nhl"), ("mlb", "mlb"),
            ("atp", "tennis"), ("wta", "tennis"), ("tennis", "tennis"),
            ("epl", "soccer"), ("ucl", "soccer"), ("premier league", "soccer"), ("soccer", "soccer"),
        ):
            if sp_tok in blob and yes_lbl.lower() not in _generic and no_lbl.lower() not in _generic:
                category = "sports"
                sport = sp_val
                asset = canonical_matchup_key(yes_lbl, no_lbl, None)
                horizon = "match"
                break

    yes_asks: List[OrderLevel] = []
    yes_bids: List[OrderLevel] = []
    no_asks: List[OrderLevel] = []
    no_bids: List[OrderLevel] = []

    if isinstance(orderbook, Mapping):
        ob_data = orderbook.get("data") if isinstance(orderbook.get("data"), Mapping) else orderbook
        for row in ob_data.get("asks") or []:
            if isinstance(row, Sequence) and len(row) >= 2:
                px, sz = float(row[0]), float(row[1])
                if 0.0 < px < 1.0 and sz > 0.0:
                    yes_asks.append(OrderLevel(px, sz))
                    no_bids.append(OrderLevel(round(1.0 - px, 6), sz))
        for row in ob_data.get("bids") or []:
            if isinstance(row, Sequence) and len(row) >= 2:
                px, sz = float(row[0]), float(row[1])
                if 0.0 < px < 1.0 and sz > 0.0:
                    yes_bids.append(OrderLevel(px, sz))
                    no_asks.append(OrderLevel(round(1.0 - px, 6), sz))
    else:
        o_yes, o_no = outcomes[0], outcomes[1]
        for target_list, obj in (
            (yes_asks, o_yes.get("bestAsk")),
            (yes_bids, o_yes.get("bestBid")),
            (no_asks, o_no.get("bestAsk")),
            (no_bids, o_no.get("bestBid")),
        ):
            if isinstance(obj, Mapping) and obj.get("price") is not None and obj.get("size") is not None:
                px, sz = float(obj["price"]), float(obj["size"])
                if 0.0 < px < 1.0 and sz > 0.0:
                    target_list.append(OrderLevel(px, sz))

    pm_conds = [str(c).lower() for c in (raw.get("polymarketConditionIds") or []) if c]
    mkt = NormalizedBinaryMarket(
        venue="predict_fun",
        market_id=mid,
        slug=slug,
        title=title,
        category=category,
        yes_label=yes_lbl,
        no_label=no_lbl,
        yes_asks=sorted(yes_asks, key=lambda x: x.price),
        yes_bids=sorted(yes_bids, key=lambda x: x.price, reverse=True),
        no_asks=sorted(no_asks, key=lambda x: x.price),
        no_bids=sorted(no_bids, key=lambda x: x.price, reverse=True),
        fee_rate_bps=float(raw.get("feeRateBps") or 200.0),
        fee_enabled=float(raw.get("feeRateBps") or 0.0) > 0.0,
        taker_delay_ms=0.0,
        min_shares=5.0,
        supports_split_merge=True,
        is_yield_bearing=bool(raw.get("isYieldBearing")),
        asset=asset,
        horizon=horizon,
        oracle_family=oracle_family or ("official_boxscore" if category == "sports" else ("uma" if pm_conds else "")),
        oracle_stream_url=stream_url,
        cancel_rule="50_50",
        sport=sport,
        has_unlisted_draw=(sport == "soccer"),
        condition_id=str(raw.get("conditionId") or "").lower(),
        polymarket_condition_ids=pm_conds,
        rules_hash=normalize_rules_sha256(desc),
        neg_risk=bool(raw.get("isNegRisk")),
        partition_group_id=cat_slug if raw.get("isNegRisk") else "",
        partition_label=str(raw.get("title") or title),
    )
    return mkt.canonicalize_outcomes_idempotent()


def parse_forecastex_contract(raw: Mapping[str, Any]) -> Optional[NormalizedBinaryMarket]:
    """
    Normalizes an Interactive Brokers Canada / ForecastEx (`CIRO`-regulated in Ontario) binary
    event contract (`$1.00` par payout, `3.38%` APY daily incentive coupon, `$0.01` fee cap).
    """
    cid = str(raw.get("conid") or raw.get("contract_id") or "").strip()
    if not cid:
        return None
    title = str(raw.get("title") or raw.get("description") or cid)
    slug = str(raw.get("symbol") or cid)
    desc = str(raw.get("rules_text") or title)

    def _lvls(rows: Any, desc_sort: bool = False) -> List[OrderLevel]:
        out_l: List[OrderLevel] = []
        for r in rows or []:
            px = float(r.get("price") if isinstance(r, Mapping) else r[0])
            sz = float(r.get("size") if isinstance(r, Mapping) else r[1])
            if px > 1.0:
                px = px / 100.0
            if 0.0 < px < 1.0 and sz > 0.0:
                out_l.append(OrderLevel(round(px, 6), sz))
        return sorted(out_l, key=lambda x: x.price, reverse=desc_sort)

    return NormalizedBinaryMarket(
        venue="forecastex",
        market_id=cid,
        slug=slug,
        title=title,
        category=str(raw.get("category") or "macro"),
        yes_label="YES",
        no_label="NO",
        yes_asks=_lvls(raw.get("yes_asks"), False),
        yes_bids=_lvls(raw.get("yes_bids"), True),
        no_asks=_lvls(raw.get("no_asks"), False),
        no_bids=_lvls(raw.get("no_bids"), True),
        fee_rate_bps=100.0,
        fee_enabled=True,
        min_shares=1.0,
        supports_split_merge=False,
        is_yield_bearing=True,
        asset=str(raw.get("asset") or slug),
        horizon=str(raw.get("horizon") or "event"),
        oracle_family=str(raw.get("oracle_family") or "official_release"),
        end_ts=int(raw["end_ts"]) if raw.get("end_ts") else None,
        cancel_rule="VOID",
        rules_hash=normalize_rules_sha256(desc),
    )


def parse_stx_ontario_market(raw: Mapping[str, Any]) -> Optional[NormalizedBinaryMarket]:
    """
    Normalizes an STX (`stxapp.ca` — AGCO & iGaming Ontario licensed) peer-to-peer binary
    sports orderbook (`$0`–`$100` scale normalized to `$0.00`–`$1.00` per share).
    Supports both direct fixture dicts (`team_a`/`team_b`) and live STX Phoenix WebSocket /
    REST `/api/v1/markets` payloads (`participants`, `rules="home_winner"`, `ob={"b": [...], "o": [...]}`).
    """
    status_val = str(raw.get("status") or "").strip().lower()
    if status_val and status_val not in ("active", "open"):
        return None
    rules_val = str(raw.get("rules") or "").strip().lower()
    if rules_val and rules_val not in ("home_winner", "moneyline", "binary"):
        return None

    mid = str(raw.get("market_id") or raw.get("id") or raw.get("symbol") or "").strip()
    team_a = str(raw.get("team_a") or raw.get("home_team") or "").strip()
    team_b = str(raw.get("team_b") or raw.get("away_team") or "").strip()

    participants = raw.get("participants")
    if (not team_a or not team_b) and isinstance(participants, Sequence):
        home_name = ""
        away_name = ""
        for p in participants:
            if not isinstance(p, Mapping):
                continue
            role = str(p.get("role") or p.get("position") or "").strip().lower()
            pname = str(p.get("name") or p.get("short_name") or "").strip()
            if role == "home" and pname:
                home_name = pname
            elif role == "away" and pname:
                away_name = pname
        if home_name and away_name:
            team_a = team_a or home_name
            team_b = team_b or away_name

    if not mid or not team_a or not team_b:
        return None

    end_ts: Optional[int] = int(raw["game_ts"]) if raw.get("game_ts") else None
    if end_ts is None and raw.get("event_start"):
        ev_raw = raw.get("event_start")
        if isinstance(ev_raw, (int, float)) and ev_raw > 0:
            val_i = int(ev_raw)
            if val_i > 10**14:
                end_ts = val_i // 1_000_000
            elif val_i > 10**11:
                end_ts = val_i // 1_000
            else:
                end_ts = val_i
        else:
            ev_str = str(ev_raw or "").strip()
            try:
                from datetime import datetime
                if ev_str.endswith("Z"):
                    ev_str = ev_str[:-1] + "+00:00"
                end_ts = int(datetime.fromisoformat(ev_str).timestamp())
            except Exception:
                end_ts = None

    match_key = canonical_matchup_key(team_a, team_b, end_ts)
    canon_pair = sorted([normalize_team_token(team_a), normalize_team_token(team_b)])

    def _norm_book(rows: Any, desc_sort: bool = False) -> List[OrderLevel]:
        out_l: List[OrderLevel] = []
        for r in rows or []:
            if isinstance(r, Mapping):
                p_raw = r.get("price") if r.get("price") is not None else r.get("p")
                s_raw = r.get("size") if r.get("size") is not None else r.get("q")
                if p_raw is None or s_raw is None:
                    continue
                px = float(p_raw)
                sz = float(s_raw)
            else:
                px = float(r[0])
                sz = float(r[1])
            if px > 100.0:
                px = px / 10000.0
            elif px > 1.0:
                px = px / 100.0
            if 0.0 < px < 1.0 and sz > 0.0:
                out_l.append(OrderLevel(round(px, 6), sz))
        return sorted(out_l, key=lambda x: x.price, reverse=desc_sort)

    ob = raw.get("ob") if isinstance(raw.get("ob"), Mapping) else {}
    a_asks = _norm_book(raw.get("team_a_asks") if raw.get("team_a_asks") is not None else ob.get("o"), False)
    a_bids = _norm_book(raw.get("team_a_bids") if raw.get("team_a_bids") is not None else ob.get("b"), True)

    if raw.get("team_b_asks") is not None:
        b_asks = _norm_book(raw.get("team_b_asks"), False)
    else:
        b_asks = sorted(
            [
                OrderLevel(round(1.0 - lvl.price, 6), lvl.size)
                for lvl in a_bids
                if 0.0 < round(1.0 - lvl.price, 6) < 1.0
            ],
            key=lambda x: x.price,
        )

    if raw.get("team_b_bids") is not None:
        b_bids = _norm_book(raw.get("team_b_bids"), True)
    else:
        b_bids = sorted(
            [
                OrderLevel(round(1.0 - lvl.price, 6), lvl.size)
                for lvl in a_asks
                if 0.0 < round(1.0 - lvl.price, 6) < 1.0
            ],
            key=lambda x: x.price,
            reverse=True,
        )

    if normalize_team_token(team_a) == canon_pair[0]:
        yes_lbl, no_lbl = team_a, team_b
        y_asks, y_bids, n_asks, n_bids = a_asks, a_bids, b_asks, b_bids
    else:
        yes_lbl, no_lbl = team_b, team_a
        y_asks, y_bids, n_asks, n_bids = b_asks, b_bids, a_asks, a_bids

    raw_sport = str(raw.get("sport") or "").strip().lower()
    raw_comp = str(raw.get("competition") or raw.get("comp_name") or "").strip().lower()
    if raw_sport in ("basketball", "nba") or raw_comp == "nba":
        sport = "nba"
    elif raw_sport in ("hockey", "ice_hockey", "nhl") or raw_comp == "nhl":
        sport = "nhl"
    elif raw_sport in ("baseball", "mlb") or raw_comp == "mlb":
        sport = "mlb"
    elif raw_sport in ("football", "american_football", "nfl") or raw_comp == "nfl":
        sport = "nfl"
    elif raw_sport in ("soccer", "football_soccer") or raw_comp in ("epl", "mls", "ucl", "laliga", "bundesliga", "seriea", "ligue1"):
        sport = "soccer"
    elif raw_sport == "tennis":
        sport = "tennis"
    else:
        sport = raw_sport or raw_comp or "nba"

    slug_val = str(raw.get("slug") or raw.get("symbol") or mid)
    title_val = str(raw.get("title") or raw.get("name") or f"{team_a} vs {team_b}")
    is_live = bool(raw.get("game_live", False)) or (end_ts is not None and end_ts <= int(time.time()))

    return NormalizedBinaryMarket(
        venue="stx_ontario",
        market_id=mid,
        slug=slug_val,
        title=title_val,
        category="sports",
        yes_label=yes_lbl,
        no_label=no_lbl,
        yes_asks=y_asks,
        yes_bids=y_bids,
        no_asks=n_asks,
        no_bids=n_bids,
        fee_rate_bps=float(raw.get("win_commission_bps") or 200.0),
        fee_enabled=True,
        taker_delay_ms=float(raw.get("inplay_delay_ms") or 0.0),
        min_shares=1.0,
        supports_split_merge=False,
        asset=match_key,
        horizon="match",
        oracle_family="official_boxscore",
        end_ts=end_ts,
        cancel_rule="VOID",
        tennis_retirement_rule="ONE_SET" if sport == "tennis" else "NA",
        sport=sport,
        completed_sets=int(raw.get("completed_sets") or 0),
        game_live=is_live,
        has_unlisted_draw=(sport == "soccer"),
    )


def parse_polymarket_gamma_market(
    raw: Mapping[str, Any],
    *,
    yes_book: Optional[Mapping[str, Any]] = None,
    no_book: Optional[Mapping[str, Any]] = None,
    books_by_token_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
    fee_rate_bps_override: Optional[float] = None,
    allow_outcome_prices_fallback: bool = True,
) -> Optional[NormalizedBinaryMarket]:
    """Parses a Polymarket Gamma market dict + optional CLOB `/book` snapshots."""
    if raw.get("closed") is True or raw.get("active") is False:
        return None
    raw_tokens = raw.get("clobTokenIds")
    tokens: List[str] = json.loads(raw_tokens) if isinstance(raw_tokens, str) else list(raw_tokens or [])
    if len(tokens) != 2:
        return None

    raw_outcomes = raw.get("outcomes")
    outcomes: List[str] = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else list(raw_outcomes or ["Yes", "No"])
    if len(outcomes) != 2:
        outcomes = ["Yes", "No"]

    slug = str(raw.get("slug") or "")
    title = str(raw.get("question") or raw.get("title") or slug)
    desc = str(raw.get("description") or "")
    res_src = str(raw.get("resolutionSource") or "")
    asset, horizon, oracle_family, stream_url = infer_crypto_oracle_signature(title, f"{desc} {res_src}", slug)

    end_ts: Optional[int] = None
    # Prefer `gameStartTime` on sports markets because Gamma `endDate` includes a 7-14d resolution buffer
    end_iso = raw.get("gameStartTime") if (not asset and raw.get("gameStartTime")) else (raw.get("endDate") or raw.get("endDateIso"))
    if isinstance(end_iso, str) and end_iso:
        try:
            iso_norm = end_iso.strip().replace(" ", "T")
            if iso_norm.endswith("+00"):
                iso_norm = iso_norm + ":00"
            dt = datetime.fromisoformat(iso_norm.replace("Z", "+00:00"))
            end_ts = int(dt.timestamp())
        except ValueError:
            end_ts = None

    category = "crypto" if asset else "other"
    sport = ""
    match_key = ""
    # Sports team matchup detection (e.g., "Seahawks vs. Cardinals" or outcome names = teams)
    if not asset and outcomes[0].lower() not in ("yes", "no", "up", "down", "over", "under"):
        category = "sports"
        base_mk = canonical_matchup_key(outcomes[0], outcomes[1], end_ts)
        if is_sports_derivative_line(slug, title):
            match_key = f"DERIVATIVE::{slug}::{base_mk}"
            horizon = "spread_or_period"
        else:
            match_key = base_mk
            horizon = "match"
        blob = f"{slug} {title} {desc}".lower()
        for sp_tok, sp_val in (
            ("nba-", "nba"),
            ("nfl-", "nfl"),
            ("nhl-", "nhl"),
            ("mlb-", "mlb"),
            ("atp-", "tennis"),
            ("wta-", "tennis"),
            ("tennis", "tennis"),
            ("epl-", "soccer"),
            ("ucl-", "soccer"),
            ("soccer", "soccer"),
        ):
            if sp_tok in blob:
                sport = sp_val
                break

    # Dynamic fee_rate_bps extraction (never hardcode blanket category fees!)
    if fee_rate_bps_override is not None:
        fee_bps = float(fee_rate_bps_override)
    elif raw.get("takerBaseFee") is not None:
        tb = float(raw["takerBaseFee"])
        fee_bps = tb if tb >= 1.0 else tb * 10_000.0
    elif raw.get("feesEnabled") is True and category == "crypto":
        fee_bps = 700.0
    else:
        fee_bps = 0.0

    def _levels(book: Optional[Mapping[str, Any]], key: str, desc_sort: bool) -> List[OrderLevel]:
        if not isinstance(book, Mapping):
            return []
        lvls: List[OrderLevel] = []
        for item in book.get(key) or []:
            px = float(item.get("price") or 0.0)
            sz = float(item.get("size") or 0.0)
            if 0.0 < px < 1.0 and sz > 0.0:
                lvls.append(OrderLevel(px, sz))
        return sorted(lvls, key=lambda x: x.price, reverse=desc_sort)

    eff_yes_book = books_by_token_id.get(str(tokens[0])) if books_by_token_id is not None else yes_book
    eff_no_book = books_by_token_id.get(str(tokens[1])) if books_by_token_id is not None else no_book
    y_asks = _levels(eff_yes_book, "asks", False)
    y_bids = _levels(eff_yes_book, "bids", True)
    n_asks = _levels(eff_no_book, "asks", False)
    n_bids = _levels(eff_no_book, "bids", True)

    if (
        not y_asks
        and not n_asks
        and allow_outcome_prices_fallback
        and books_by_token_id is None
        and yes_book is None
        and no_book is None
    ):
        raw_px = raw.get("outcomePrices")
        px_list = json.loads(raw_px) if isinstance(raw_px, str) else list(raw_px or [])
        if len(px_list) == 2:
            p0, p1 = float(px_list[0]), float(px_list[1])
            if 0.0 < p0 < 1.0:
                y_asks = [OrderLevel(p0, 25.0)]
            if 0.0 < p1 < 1.0:
                n_asks = [OrderLevel(p1, 25.0)]

    yes_lbl, no_lbl = str(outcomes[0]), str(outcomes[1])
    y_tok, n_tok = str(tokens[0]), str(tokens[1])

    mkt = NormalizedBinaryMarket(
        venue="polymarket",
        market_id=str(raw.get("id") or slug),
        slug=slug,
        title=title,
        category=category,
        yes_label=yes_lbl,
        no_label=no_lbl,
        yes_asks=y_asks,
        yes_bids=y_bids,
        no_asks=n_asks,
        no_bids=n_bids,
        fee_rate_bps=fee_bps,
        fee_enabled=fee_bps > 0.0,
        taker_delay_ms=0.0,
        min_shares=float(raw.get("orderMinSize") or 5.0),
        supports_split_merge=True,
        asset=asset or match_key,
        horizon=horizon or ("match" if category == "sports" else ""),
        oracle_family=oracle_family or ("official_boxscore" if category == "sports" else "uma"),
        oracle_stream_url=stream_url,
        end_ts=end_ts,
        cancel_rule="50_50",
        tennis_retirement_rule="ONE_BALL" if sport == "tennis" else "NA",
        sport=sport,
        condition_id=str(raw.get("conditionId") or "").lower(),
        rules_hash=normalize_rules_sha256(desc),
        yes_token_id=y_tok,
        no_token_id=n_tok,
    )
    return mkt.canonicalize_outcomes_idempotent()


# ---------------------------------------------------------------------------
# Shadow Candidates, Honest Latency/Queue Simulation & Graduation Metrics
# ---------------------------------------------------------------------------

@dataclass
class ShadowArbitrageCandidate:
    family: str                       # "XV_INTRA_SPLIT_MERGE" | "XV_TAKER_BOX_OR_CORRIDOR" | "XV_PASSIVE_MAKER_ANCHOR"
    candidate_key: str
    venue_a: str
    venue_b: str
    market_a_slug: str
    market_b_slug: str
    side_a: str                       # "YES" or "NO"
    side_b: str                       # "YES" or "NO"
    shares: float
    gross_cost_usd: float
    fees_usd: float
    gas_usd: float
    bridge_drag_usd: float
    guaranteed_min_payout_usd: float
    expected_net_profit_usd: float
    net_edge_bps: float
    est_unsettled_rebate_usd: float
    effective_delay_ms: float
    rule_check: RuleVerificationResult
    leg_a_entry_cost_usd: float = 0.0
    leg_b_entry_cost_usd: float = 0.0


@dataclass
class HonestShadowExecutionOutcome:
    candidate: ShadowArbitrageCandidate
    survived_latency_recheck: bool
    maker_queue_filled: bool
    locked_complete_basket: bool
    unwind_bleed_usd: float
    realized_shadow_net_pnl_usd: float
    reason: str


@dataclass
class GraduationReport:
    generated_at_utc: str
    cycles_completed: int
    venue_health: Dict[str, Dict[str, Any]]
    gross_candidates_seen: int
    rule_gate_rejections: int
    rule_gate_rejection_reasons: Dict[str, int]
    executable_net_l2_count: int
    locked_complete_baskets: int
    raced_unwinds: int
    shadow_fill_realism_ratio: float
    double_zero_incidents: int
    gross_structural_capture_usd: float
    total_unwind_bleed_usd: float
    unwind_bleed_pct_of_gross: float
    observed_p99_latency_ms: float
    total_realized_shadow_net_pnl_usd: float
    est_unsettled_rebates_usd: float
    projected_daily_net_gain_usd: float
    competitor_decay_buckets: Dict[str, int]
    gates: Dict[str, bool]
    overall_graduated: bool


class HonestCrossVenueShadowEngine:
    """
    Core pure-riskless cross-venue scanner, Double-Zero verifier, honest post-delay simulator,
    competitor-decay tracker, and 5-Gate 7-Day Graduation evaluator.
    """

    def __init__(
        self,
        *,
        clip_notional_usd: float = 25.0,
        bridge_drag_bps: float = DEFAULT_RELAY_BRIDGE_DRAG_BPS,
        incremental_daily_vm_cost_usd: float = 0.25,  # ~$7.50/mo Tokyo micro-relay delta
        wire_latency_ms: Optional[Mapping[str, float]] = None,
        data_dir: Optional[Path] = None,
        enable_durable_store: bool = True,
    ) -> None:
        self.clip_notional_usd = max(5.0, float(clip_notional_usd))
        self.bridge_drag_bps = float(bridge_drag_bps)
        self.incremental_daily_vm_cost_usd = float(incremental_daily_vm_cost_usd)
        self.wire_latency_ms: Dict[str, float] = dict(DEFAULT_WIRE_LATENCY_MS)
        self.wire_latency_ms.setdefault("forecastex", 65.0)
        self.wire_latency_ms.setdefault("stx_ontario", 35.0)
        if wire_latency_ms:
            for k, v in wire_latency_ms.items():
                self.wire_latency_ms[k] = float(v)

        self.verifier = CrossVenueRuleVerifier()
        self.data_dir = Path(data_dir) if data_dir is not None else Path("data") / "cross_venue_shadow"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.funnel_path = self.data_dir / "cross_venue_funnel.jsonl"
        self.report_path = self.data_dir / "shadow_graduation_report.json"

        # Cumulative shadow ledger state (restorable across restarts via ShadowTelemetryStore)
        self.cycles_completed = 0
        self.start_monotonic = time.monotonic()
        self.gross_candidates_seen = 0
        self.rule_gate_rejections = 0
        self.rule_gate_rejection_reasons: Dict[str, int] = {}
        self.executable_net_l2_count = 0
        self.outcomes: List[HonestShadowExecutionOutcome] = []
        self.double_zero_incidents = 0
        self.latency_samples_ms: List[float] = []
        self.venue_health: Dict[str, Dict[str, Any]] = {}
        self._active_decay_watches: Dict[str, float] = {}
        self.competitor_decay_buckets: Dict[str, int] = {
            "lt_5ms": 0,
            "5_15ms": 0,
            "15_40ms": 0,
            "gt_40ms": 0,
        }
        # Historical outcome accumulators restored from prior checkpoint before current process start
        self._restored_takers_attempted: int = 0
        self._restored_locked_baskets: int = 0
        self._restored_raced_unwinds: int = 0
        self._restored_gross_capture_usd: float = 0.0
        self._restored_unwind_bleed_usd: float = 0.0
        self._restored_net_pnl_usd: float = 0.0
        self._restored_rebates_usd: float = 0.0
        self.reconciled_from_corrupt_checkpoint: bool = False
        self.telemetry_store: Any = None

        if enable_durable_store:
            from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowTelemetryStore

            self.telemetry_store = ShadowTelemetryStore(self.data_dir)
            saved, reconciled = self.telemetry_store.load_or_reconcile_engine_checkpoint()
            self.reconciled_from_corrupt_checkpoint = reconciled
            cur_net_mode = (os.environ.get("DOMINUS_NETWORK_MODE") or "").strip().lower()
            saved_scope = str((saved or {}).get("checkpoint_data_scope") or "")
            # Prevent offline synthetic fixture checkpoints from contaminating live shadow graduation runs
            skip_synthetic_in_live = (
                cur_net_mode in {"live_public", "live_authenticated"}
                and saved_scope == "OFFLINE_SYNTHETIC"
            )
            if saved and not skip_synthetic_in_live:
                self.cycles_completed = int(saved.get("cycles_completed", 0))
                self.gross_candidates_seen = int(saved.get("gross_candidates_seen", 0))
                self.rule_gate_rejections = int(saved.get("rule_gate_rejections", 0))
                self.rule_gate_rejection_reasons = {
                    str(k): int(v) for k, v in (saved.get("rule_gate_rejection_reasons") or {}).items()
                }
                self.executable_net_l2_count = int(saved.get("executable_net_l2_count", 0))
                self.double_zero_incidents = int(saved.get("double_zero_incidents", 0))
                for bk, bv in (saved.get("competitor_decay_buckets") or {}).items():
                    if bk in self.competitor_decay_buckets:
                        self.competitor_decay_buckets[bk] = int(bv)
                self._restored_takers_attempted = int(saved.get("takers_attempted", 0))
                self._restored_locked_baskets = int(saved.get("locked_complete_baskets", 0))
                self._restored_raced_unwinds = int(saved.get("raced_unwinds", 0))
                self._restored_gross_capture_usd = float(saved.get("gross_structural_capture_usd", 0.0))
                self._restored_unwind_bleed_usd = float(saved.get("total_unwind_bleed_usd", 0.0))
                self._restored_net_pnl_usd = float(saved.get("total_realized_shadow_net_pnl_usd", 0.0))
                self._restored_rebates_usd = float(saved.get("est_unsettled_rebates_usd", 0.0))

    def _append_funnel_event(self, stage: str, payload: Mapping[str, Any]) -> None:
        now_u = time.time()
        rec: Dict[str, Any] = {
            "ts_unix": round(now_u, 4),
            "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_u)),
            "stage": stage,
        }
        rec.update(payload)
        with open(self.funnel_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")

    # -----------------------------------------------------------------------
    # 1. Intra-Venue Complete-Set `Split` / `Merge` Scanner (`Predict` & `Limitless`)
    # -----------------------------------------------------------------------
    def scan_intra_venue_complete_sets(
        self,
        markets: Sequence[NormalizedBinaryMarket],
    ) -> List[ShadowArbitrageCandidate]:
        found: List[ShadowArbitrageCandidate] = []
        for m in markets:
            if not m.supports_split_merge or m.venue == "polymarket":
                continue
            if not m.yes_asks or not m.no_asks or m.has_crossed_or_invalid_book():
                continue
            best_sum = m.yes_asks[0].price + m.no_asks[0].price
            if best_sum >= 1.0:
                continue

            self.gross_candidates_seen += 1
            ckey = f"INTRA::{m.venue}::{m.slug}"
            self._append_funnel_event(
                "GROSS_ARB_SEEN",
                {
                    "sleeve": "XV_INTRA_SPLIT_MERGE",
                    "candidate_key": ckey,
                    "box_type": "INTRA_MERGE",
                    "asset": m.asset or m.slug[:16].upper(),
                    "net_edge_bps": round((1.0 - best_sum) * 10_000.0, 2),
                },
            )
            shares = max(m.min_shares, math.floor(self.clip_notional_usd / max(best_sum, 0.10)))
            w_yes = walk_asks_for_shares(m.yes_asks, shares, m)
            w_no = walk_asks_for_shares(m.no_asks, shares, m)
            if not (w_yes.filled and w_no.filled):
                continue

            gross_cost = w_yes.gross_cost_usd + w_no.gross_cost_usd
            fees = w_yes.taker_fee_usd + w_no.taker_fee_usd
            gas = DEFAULT_EXTERNAL_GAS_USD.get(m.venue, 0.005)
            payout = shares * 1.0
            net_profit = payout - (gross_cost + fees + gas)
            if net_profit < MIN_NET_PROFIT_USD:
                continue

            eff_delay = self.wire_latency_ms.get(m.venue, 120.0) + m.taker_delay_ms
            cand = ShadowArbitrageCandidate(
                family="XV_INTRA_SPLIT_MERGE",
                candidate_key=ckey,
                venue_a=m.venue,
                venue_b=m.venue,
                market_a_slug=m.slug,
                market_b_slug=m.slug,
                side_a="YES",
                side_b="NO",
                shares=shares,
                gross_cost_usd=gross_cost,
                fees_usd=fees,
                gas_usd=gas,
                bridge_drag_usd=0.0,  # Single-chain atomic mergePositions() -> 0 bridge drag!
                guaranteed_min_payout_usd=payout,
                expected_net_profit_usd=net_profit,
                net_edge_bps=(net_profit / gross_cost) * 10_000.0,
                est_unsettled_rebate_usd=0.0,
                effective_delay_ms=eff_delay,
                rule_check=RuleVerificationResult(True, ()),
            )
            self.executable_net_l2_count += 1
            found.append(cand)
        return found

    # -----------------------------------------------------------------------
    # 2. Cross-Venue Taker-Taker Super-Replicating Boxes & Passive Maker Anchors
    # -----------------------------------------------------------------------
    def scan_cross_venue_pairs(
        self,
        pairs: Sequence[Tuple[NormalizedBinaryMarket, NormalizedBinaryMarket]],
    ) -> List[ShadowArbitrageCandidate]:
        found: List[ShadowArbitrageCandidate] = []
        now_mono = time.monotonic()
        still_gross_keys: set[str] = set()

        for poly_m, ext_m in pairs:
            if poly_m.has_crossed_or_invalid_book() or ext_m.has_crossed_or_invalid_book():
                if self.telemetry_store is not None:
                    origin = (
                        "OFFLINE_SYNTHETIC"
                        if "OFFLINE_SYNTHETIC" in (poly_m.data_origin, ext_m.data_origin)
                        else poly_m.data_origin
                    )
                    self.telemetry_store.record_rejection(
                        candidate_key=f"XV::{poly_m.venue}:{poly_m.slug}__vs__{ext_m.venue}:{ext_m.slug}",
                        stage="BOOK_INTEGRITY",
                        reason="STAGE1_CROSSED_OR_INVALID_BOOK",
                        venues=[poly_m.venue, ext_m.venue],
                        gross_edge_bps=0.0,
                        data_origin=origin,
                    )
                continue
            # Test both orientations:
            #   Orientation 1: Buy YES on Polymarket + Buy NO on External Venue
            #   Orientation 2: Buy NO on Polymarket  + Buy YES on External Venue
            orientations = (
                ("YES", "NO", poly_m.yes_asks, ext_m.no_asks, ext_m.no_bids),
                ("NO", "YES", poly_m.no_asks, ext_m.yes_asks, ext_m.yes_bids),
            )
            for side_p, side_e, p_asks, e_asks, e_bids in orientations:
                ckey = f"XV::{poly_m.venue}:{poly_m.slug}:{side_p}__vs__{ext_m.venue}:{ext_m.slug}:{side_e}"

                # --- (A) Cross-Venue Taker-Taker Complete Box / Corridor ---
                if p_asks and e_asks:
                    l1_sum = p_asks[0].price + e_asks[0].price
                    if l1_sum < 1.0:
                        still_gross_keys.add(ckey)
                        if ckey not in self._active_decay_watches:
                            self._active_decay_watches[ckey] = now_mono
                        self.gross_candidates_seen += 1
                        self._append_funnel_event(
                            "GROSS_ARB_SEEN",
                            {
                                "sleeve": "XV_TAKER_BOX_OR_CORRIDOR",
                                "candidate_key": ckey,
                                "box_type": f"{poly_m.venue.upper()}_{ext_m.venue.upper()}",
                                "asset": poly_m.asset or ext_m.asset or "MULTI",
                                "net_edge_bps": round((1.0 - l1_sum) * 10_000.0, 2),
                            },
                        )

                        rc = self.verifier.verify_pair(
                            poly_m,
                            ext_m,
                            side_a=side_p,
                            side_b=side_e,
                            price_a=p_asks[0].price,
                            price_b=e_asks[0].price,
                        )
                        if not rc.passed:
                            self.rule_gate_rejections += 1
                            for gf in rc.gate_failures:
                                tag = gf.split("(")[0]
                                self.rule_gate_rejection_reasons[tag] = self.rule_gate_rejection_reasons.get(tag, 0) + 1
                            if self.telemetry_store is not None:
                                origin = (
                                    "OFFLINE_SYNTHETIC"
                                    if "OFFLINE_SYNTHETIC" in (poly_m.data_origin, ext_m.data_origin)
                                    else poly_m.data_origin
                                )
                                self.telemetry_store.record_rejection(
                                    candidate_key=ckey,
                                    stage="RULE_GATE",
                                    reason=rc.gate_failures[0].split("(")[0] if rc.gate_failures else rc.reason,
                                    venues=[poly_m.venue, ext_m.venue],
                                    gross_edge_bps=(1.0 - l1_sum) * 10_000.0,
                                    data_origin=origin,
                                )
                            continue

                        min_sh = max(poly_m.min_shares, ext_m.min_shares)
                        shares = max(min_sh, math.floor(self.clip_notional_usd / max(l1_sum, 0.10)))
                        wp = walk_asks_for_shares(p_asks, shares, poly_m)
                        we = walk_asks_for_shares(e_asks, shares, ext_m)
                        if wp.filled and we.filled:
                            # Re-verify Gate 3 on worst L2 price paid on the 50-50 venue
                            rc_vwap = self.verifier.verify_pair(
                                poly_m,
                                ext_m,
                                side_a=side_p,
                                side_b=side_e,
                                price_a=wp.vwap_price,
                                price_b=we.vwap_price,
                            )
                            if rc_vwap.passed:
                                gross_cost = wp.gross_cost_usd + we.gross_cost_usd
                                fees = wp.taker_fee_usd + we.taker_fee_usd
                                gas = DEFAULT_EXTERNAL_GAS_USD.get(poly_m.venue, 0.002) + DEFAULT_EXTERNAL_GAS_USD.get(ext_m.venue, 0.005)
                                bridge = relay_bridge_drag_usd(gross_cost, self.bridge_drag_bps)
                                payout = shares * 1.0
                                net_profit = payout - (gross_cost + fees + gas + bridge)
                                if net_profit >= MIN_NET_PROFIT_USD:
                                    eff_delay = max(
                                        self.wire_latency_ms.get(poly_m.venue, 72.39) + poly_m.taker_delay_ms,
                                        self.wire_latency_ms.get(ext_m.venue, 120.0) + ext_m.taker_delay_ms,
                                    )
                                    cand = ShadowArbitrageCandidate(
                                        family="XV_TAKER_BOX_OR_CORRIDOR",
                                        candidate_key=ckey,
                                        venue_a=poly_m.venue,
                                        venue_b=ext_m.venue,
                                        market_a_slug=poly_m.slug,
                                        market_b_slug=ext_m.slug,
                                        side_a=side_p,
                                        side_b=side_e,
                                        shares=shares,
                                        gross_cost_usd=gross_cost,
                                        fees_usd=fees,
                                        gas_usd=gas,
                                        bridge_drag_usd=bridge,
                                        guaranteed_min_payout_usd=payout,
                                        expected_net_profit_usd=net_profit,
                                        net_edge_bps=(net_profit / gross_cost) * 10_000.0,
                                        est_unsettled_rebate_usd=0.0,
                                        effective_delay_ms=eff_delay,
                                        rule_check=rc_vwap,
                                        leg_a_entry_cost_usd=wp.gross_cost_usd,
                                        leg_b_entry_cost_usd=we.gross_cost_usd,
                                    )
                                    self.executable_net_l2_count += 1
                                    self._append_funnel_event(
                                        "EXECUTABLE_NET_L2",
                                        {
                                            "sleeve": cand.family,
                                            "candidate_key": ckey,
                                            "box_type": f"{poly_m.venue.upper()}_{ext_m.venue.upper()}",
                                            "asset": poly_m.asset or ext_m.asset or "MULTI",
                                            "net_edge_bps": round(cand.net_edge_bps, 2),
                                            "est_profit_usd": round(cand.expected_net_profit_usd, 4),
                                            "notional_usd": round(cand.gross_cost_usd, 4),
                                        },
                                    )
                                    found.append(cand)

                # --- (B) Cross-Venue Passive 0%-Maker on External -> Polymarket FOK Anchor ---
                # Rest a postOnly Maker bid at `best_bid + $0.005` (or inside wide spread) on Predict/SX/Limitless
                # (0% maker fee, 0ms takerDelayMs on Limitless!) backed by >= 4.0x L2 depth on Polymarket!
                if p_asks and e_bids and e_asks and (e_asks[0].price - e_bids[0].price) >= 0.025:
                    maker_px = round(min(e_asks[0].price - 0.005, e_bids[0].price + 0.005), 4)
                    if 0.01 < maker_px < 0.99 and (p_asks[0].price + maker_px) < 0.992:
                        rc_m = self.verifier.verify_pair(
                            poly_m,
                            ext_m,
                            side_a=side_p,
                            side_b=side_e,
                            price_a=p_asks[0].price,
                            price_b=maker_px,
                        )
                        if rc_m.passed:
                            min_sh = max(poly_m.min_shares, ext_m.min_shares)
                            shares = max(min_sh, math.floor(self.clip_notional_usd / max(p_asks[0].price + maker_px, 0.10)))
                            wp = walk_asks_for_shares(p_asks, shares, poly_m)
                            # Anchor safety rule: Polymarket L2 book must hold >= 4.0x our hedge notional!
                            if wp.filled and wp.total_book_notional_usd >= MIN_MAKER_ANCHOR_DEPTH_MULT * wp.gross_cost_usd:
                                maker_cost = shares * maker_px
                                gross_cost = wp.gross_cost_usd + maker_cost
                                fees = wp.taker_fee_usd  # External leg is 0% postOnly Maker!
                                gas = DEFAULT_EXTERNAL_GAS_USD.get(poly_m.venue, 0.002) + DEFAULT_EXTERNAL_GAS_USD.get(ext_m.venue, 0.005)
                                bridge = relay_bridge_drag_usd(gross_cost, self.bridge_drag_bps)
                                payout = shares * 1.0
                                net_profit = payout - (gross_cost + fees + gas + bridge)
                                if net_profit >= MIN_NET_PROFIT_USD:
                                    est_rebate = (
                                        predict_fun_est_maker_rebate_usd(
                                            shares,
                                            maker_px,
                                            fee_rate_bps=ext_m.fee_rate_bps,
                                            is_crypto_updown=(ext_m.category == "crypto"),
                                        )
                                        if ext_m.venue == "predict_fun"
                                        else 0.0
                                    )
                                    mkey = f"MKR::{ckey}"
                                    cand_m = ShadowArbitrageCandidate(
                                        family="XV_PASSIVE_MAKER_ANCHOR",
                                        candidate_key=mkey,
                                        venue_a=poly_m.venue,
                                        venue_b=ext_m.venue,
                                        market_a_slug=poly_m.slug,
                                        market_b_slug=ext_m.slug,
                                        side_a=side_p,
                                        side_b=side_e,
                                        shares=shares,
                                        gross_cost_usd=gross_cost,
                                        fees_usd=fees,
                                        gas_usd=gas,
                                        bridge_drag_usd=bridge,
                                        guaranteed_min_payout_usd=payout,
                                        expected_net_profit_usd=net_profit,
                                        net_edge_bps=(net_profit / gross_cost) * 10_000.0,
                                        est_unsettled_rebate_usd=est_rebate,
                                        effective_delay_ms=self.wire_latency_ms.get(poly_m.venue, 72.39),  # postOnly bypasses takerDelayMs!
                                        rule_check=rc_m,
                                        leg_a_entry_cost_usd=wp.gross_cost_usd,
                                        leg_b_entry_cost_usd=maker_cost,
                                    )
                                    self.executable_net_l2_count += 1
                                    found.append(cand_m)

        # Observe cleared arbs for Competitor Decay Telemetry
        cleared = [k for k in self._active_decay_watches if k not in still_gross_keys]
        for k in cleared:
            t0 = self._active_decay_watches.pop(k)
            decay_ms = max(0.0, (now_mono - t0) * 1000.0)
            bucket = classify_decay_bucket(decay_ms)
            self.competitor_decay_buckets[bucket] = self.competitor_decay_buckets.get(bucket, 0) + 1
            self._append_funnel_event(
                "COMPETITOR_DECAY_OBSERVED",
                {
                    "sleeve": "XV_TAKER_BOX_OR_CORRIDOR",
                    "candidate_key": k,
                    "competitor_decay_ms": round(decay_ms, 2),
                    "decay_bucket": bucket,
                },
            )

        return found

    # -----------------------------------------------------------------------
    # 3. Honest Post-Latency & Queue-Ahead Fill Simulator
    # -----------------------------------------------------------------------
    def simulate_honest_execution(
        self,
        candidate: ShadowArbitrageCandidate,
        *,
        post_delay_market_a: Optional[NormalizedBinaryMarket],
        post_delay_market_b: Optional[NormalizedBinaryMarket],
        observed_trade_through_shares: float = 0.0,
        queue_ahead_shares: float = 0.0,
    ) -> HonestShadowExecutionOutcome:
        """
        Evaluates whether a candidate STILL locks a pure-riskless basket AFTER wire RTT + `takerDelayMs`:
          - For `XV_PASSIVE_MAKER_ANCHOR`: requires `observed_trade_through_shares >= queue_ahead_shares + shares`
            before triggering the Polymarket FOK hedge; if Polymarket's book moved adversely during hedge RTT,
            simulates immediate unwind of the filled passive leg!
          - For `XV_TAKER_BOX_OR_CORRIDOR` / `XV_INTRA_SPLIT_MERGE`: re-walks BOTH post-delay L2 books.
            If Leg A filled (fast venue) while Leg B vanished during `takerDelayMs` (e.g. Limitless 500ms delay),
            records exact `PARTIAL_BASKET_UNWOUND` bleed by selling Leg A back into post-delay bids!
        """
        self._append_funnel_event(
            "ORDER_SUBMITTED",
            {
                "sleeve": candidate.family,
                "candidate_key": candidate.candidate_key,
                "notional_usd": round(candidate.gross_cost_usd, 4),
            },
        )

        if post_delay_market_a is None or post_delay_market_b is None:
            outcome = HonestShadowExecutionOutcome(
                candidate=candidate,
                survived_latency_recheck=False,
                maker_queue_filled=False,
                locked_complete_basket=False,
                unwind_bleed_usd=0.0,
                realized_shadow_net_pnl_usd=0.0,
                reason="POST_DELAY_BOOK_UNAVAILABLE",
            )
            self.outcomes.append(outcome)
            return outcome

        asks_a = post_delay_market_a.yes_asks if candidate.side_a == "YES" else post_delay_market_a.no_asks
        bids_a = post_delay_market_a.yes_bids if candidate.side_a == "YES" else post_delay_market_a.no_bids
        asks_b = post_delay_market_b.yes_asks if candidate.side_b == "YES" else post_delay_market_b.no_asks
        bids_b = post_delay_market_b.yes_bids if candidate.side_b == "YES" else post_delay_market_b.no_bids

        if candidate.family == "XV_PASSIVE_MAKER_ANCHOR":
            needed_flow = queue_ahead_shares + candidate.shares
            if observed_trade_through_shares + 1e-7 < needed_flow:
                outcome = HonestShadowExecutionOutcome(
                    candidate=candidate,
                    survived_latency_recheck=True,
                    maker_queue_filled=False,
                    locked_complete_basket=False,
                    unwind_bleed_usd=0.0,
                    realized_shadow_net_pnl_usd=0.0,
                    reason="PASSIVE_QUEUE_NOT_TRADED_THROUGH",
                )
                self.outcomes.append(outcome)
                return outcome

            # Passive maker filled on Venue B -> fire immediate FOK Taker hedge on Polymarket (Venue A)
            wp_after = walk_asks_for_shares(asks_a, candidate.shares, post_delay_market_a)
            maker_paid_usd = (
                candidate.leg_b_entry_cost_usd
                if candidate.leg_b_entry_cost_usd > 0.0
                else max(0.01, candidate.gross_cost_usd - (wp_after.gross_cost_usd if wp_after.filled else 0.0))
            )
            if wp_after.filled:
                total_cost = wp_after.gross_cost_usd + maker_paid_usd
                total_fees = wp_after.taker_fee_usd
                bridge = relay_bridge_drag_usd(total_cost, self.bridge_drag_bps)
                net_pnl = candidate.guaranteed_min_payout_usd - (total_cost + total_fees + candidate.gas_usd + bridge)
                if net_pnl > 0.0:
                    outcome = HonestShadowExecutionOutcome(
                        candidate=candidate,
                        survived_latency_recheck=True,
                        maker_queue_filled=True,
                        locked_complete_basket=True,
                        unwind_bleed_usd=0.0,
                        realized_shadow_net_pnl_usd=net_pnl,
                        reason="MAKER_FILLED_AND_POLY_FOK_HEDGED",
                    )
                    self._append_funnel_event(
                        "COMPLETE_BASKET_LOCKED",
                        {
                            "sleeve": candidate.family,
                            "candidate_key": candidate.candidate_key,
                            "est_profit_usd": round(net_pnl, 4),
                        },
                    )
                    self.outcomes.append(outcome)
                    return outcome

            # Polymarket anchor moved adversely -> unwind filled Venue B leg into Venue B bids
            proceeds_b, _ = walk_bids_for_unwind(bids_b, candidate.shares, post_delay_market_b)
            bleed = max(0.0, maker_paid_usd - proceeds_b)
            outcome = HonestShadowExecutionOutcome(
                candidate=candidate,
                survived_latency_recheck=False,
                maker_queue_filled=True,
                locked_complete_basket=False,
                unwind_bleed_usd=bleed,
                realized_shadow_net_pnl_usd=-bleed,
                reason="ANCHOR_MOVED_PASSIVE_LEG_UNWOUND",
            )
            self._append_funnel_event(
                "PARTIAL_BASKET_UNWOUND",
                {
                    "sleeve": candidate.family,
                    "candidate_key": candidate.candidate_key,
                    "est_profit_usd": round(-bleed, 4),
                },
            )
            self.outcomes.append(outcome)
            return outcome

        # Taker-Taker Box or Intra-Venue Complete-Set
        wa_after = walk_asks_for_shares(asks_a, candidate.shares, post_delay_market_a)
        wb_after = walk_asks_for_shares(asks_b, candidate.shares, post_delay_market_b)

        if wa_after.filled and wb_after.filled:
            total_cost = wa_after.gross_cost_usd + wb_after.gross_cost_usd
            total_fees = wa_after.taker_fee_usd + wb_after.taker_fee_usd
            bridge = 0.0 if candidate.venue_a == candidate.venue_b else relay_bridge_drag_usd(total_cost, self.bridge_drag_bps)
            net_pnl = candidate.guaranteed_min_payout_usd - (total_cost + total_fees + candidate.gas_usd + bridge)
            if net_pnl > 0.0:
                outcome = HonestShadowExecutionOutcome(
                    candidate=candidate,
                    survived_latency_recheck=True,
                    maker_queue_filled=False,
                    locked_complete_basket=True,
                    unwind_bleed_usd=0.0,
                    realized_shadow_net_pnl_usd=net_pnl,
                    reason="POST_DELAY_BOTH_LEGS_LOCKED",
                )
                self._append_funnel_event(
                    "COMPLETE_BASKET_LOCKED",
                    {
                        "sleeve": candidate.family,
                        "candidate_key": candidate.candidate_key,
                        "est_profit_usd": round(net_pnl, 4),
                    },
                )
                self.outcomes.append(outcome)
                return outcome

        # Route fragile/delayed leg FIRST (`fragile-leg-first FOK` rule):
        # If delayed Leg B rejected FOK cleanly before Leg A was sent, unwind bleed = $0.00!
        # Only if fast Leg A filled while delayed Leg B slipped past max_price do we incur unwind bleed.
        if not wb_after.filled:
            outcome = HonestShadowExecutionOutcome(
                candidate=candidate,
                survived_latency_recheck=False,
                maker_queue_filled=False,
                locked_complete_basket=False,
                unwind_bleed_usd=0.0,
                realized_shadow_net_pnl_usd=0.0,
                reason="FRAGILE_FIRST_FOK_REJECTED_CLEANLY",
            )
            self.outcomes.append(outcome)
            return outcome

        # Delayed Leg B filled, then fast Leg A raced -> unwind Leg B into post-delay bids_b
        proceeds_b, _ = walk_bids_for_unwind(bids_b, candidate.shares, post_delay_market_b)
        bleed = max(0.0, (wb_after.gross_cost_usd + wb_after.taker_fee_usd) - proceeds_b)
        outcome = HonestShadowExecutionOutcome(
            candidate=candidate,
            survived_latency_recheck=False,
            maker_queue_filled=False,
            locked_complete_basket=False,
            unwind_bleed_usd=bleed,
            realized_shadow_net_pnl_usd=-bleed,
            reason="SECOND_LEG_RACED_UNWOUND",
        )
        self._append_funnel_event(
            "PARTIAL_BASKET_UNWOUND",
            {
                "sleeve": candidate.family,
                "candidate_key": candidate.candidate_key,
                "est_profit_usd": round(-bleed, 4),
            },
        )
        self.outcomes.append(outcome)
        return outcome

    def record_settled_box_payout(
        self,
        unit_combined_payout_usd: float,
        *,
        candidate_key: str = "",
        winning_outcome: str = "SETTLED",
        simulated_realized_pnl_usd: float = 0.0,
        data_origin: str = "OFFLINE_SYNTHETIC",
    ) -> None:
        """Records post-resolution payout check for Gate G2 (`double_zero_incidents == 0`)."""
        if unit_combined_payout_usd + 1e-6 < 1.0:
            self.double_zero_incidents += 1
        if self.telemetry_store is not None and candidate_key:
            self.telemetry_store.record_resolution(
                candidate_key=candidate_key,
                winning_outcome=winning_outcome,
                settled_unit_payout_usd=unit_combined_payout_usd,
                simulated_realized_pnl_usd=simulated_realized_pnl_usd,
                data_origin=data_origin,
            )

    # -----------------------------------------------------------------------
    # 4. 5 Mandatory 7-Day Honest Shadow Graduation Gates (`G1`–`G5`)
    # -----------------------------------------------------------------------
    def _compact_memory_buffers(self) -> None:
        if len(self.outcomes) > 512:
            evict_n = len(self.outcomes) - 256
            older = self.outcomes[:evict_n]
            self.outcomes = self.outcomes[evict_n:]
            for o in older:
                if o.candidate.family != "XV_PASSIVE_MAKER_ANCHOR" or o.maker_queue_filled:
                    self._restored_takers_attempted += 1
                    if o.locked_complete_basket:
                        self._restored_locked_baskets += 1
                if o.locked_complete_basket:
                    self._restored_gross_capture_usd += max(0.0, o.realized_shadow_net_pnl_usd)
                    self._restored_rebates_usd += o.candidate.est_unsettled_rebate_usd
                self._restored_unwind_bleed_usd += o.unwind_bleed_usd
                self._restored_net_pnl_usd += o.realized_shadow_net_pnl_usd
                if o.unwind_bleed_usd > 0:
                    self._restored_raced_unwinds += 1
        if len(self.latency_samples_ms) > 4096:
            self.latency_samples_ms = self.latency_samples_ms[-2048:]
        if len(self._active_decay_watches) > 512:
            cutoff_m = time.monotonic() - 600.0
            for k_old in [k for k, t_m in self._active_decay_watches.items() if t_m < cutoff_m]:
                self._active_decay_watches.pop(k_old, None)

    def build_graduation_report(self, simulated_days: Optional[float] = None) -> GraduationReport:
        self._compact_memory_buffers()
        takers_attempted_session = [
            o for o in self.outcomes if o.candidate.family != "XV_PASSIVE_MAKER_ANCHOR" or o.maker_queue_filled
        ]
        survived_session = [o for o in takers_attempted_session if o.locked_complete_basket]

        total_attempted = self._restored_takers_attempted + len(takers_attempted_session)
        total_locked = self._restored_locked_baskets + len(survived_session)
        realism_ratio = (total_locked / total_attempted) if total_attempted else 0.0

        gross_capture = self._restored_gross_capture_usd + sum(
            max(0.0, o.realized_shadow_net_pnl_usd) for o in self.outcomes if o.locked_complete_basket
        )
        unwind_bleed = self._restored_unwind_bleed_usd + sum(o.unwind_bleed_usd for o in self.outcomes)
        bleed_pct = (unwind_bleed / gross_capture * 100.0) if gross_capture > 1e-9 else (100.0 if unwind_bleed > 0 else 0.0)

        lat_sorted = sorted(self.latency_samples_ms)
        p99_ms = lat_sorted[min(len(lat_sorted) - 1, int(0.99 * len(lat_sorted)))] if lat_sorted else 0.0

        total_net_pnl = self._restored_net_pnl_usd + sum(o.realized_shadow_net_pnl_usd for o in self.outcomes)
        est_rebates = self._restored_rebates_usd + sum(
            o.candidate.est_unsettled_rebate_usd for o in self.outcomes if o.locked_complete_basket
        )
        total_raced_unwinds = self._restored_raced_unwinds + sum(
            1 for o in self.outcomes if o.unwind_bleed_usd > 0
        )

        elapsed_days = (
            float(simulated_days)
            if simulated_days is not None and simulated_days > 0
            else max((time.monotonic() - self.start_monotonic) / 86400.0, 1.0 / 1440.0)
        )
        # Project conservative daily gain only when at least 1 hour (or explicit `simulated_days`) is observed
        scale_days = float(simulated_days) if simulated_days is not None else max(elapsed_days, 1.0)
        daily_net_gain = (total_net_pnl / scale_days) - self.incremental_daily_vm_cost_usd

        gates = {
            "G1_shadow_fill_realism_ge_85pct": bool(total_attempted >= 1 and realism_ratio >= 0.85),
            "G2_zero_double_zero_incidents": self.double_zero_incidents == 0,
            "G3_unwind_bleed_le_8pct_of_gross": bleed_pct <= 8.0,
            "G4_p99_cancel_latency_lt_350ms": (0.0 < p99_ms < 350.0) if lat_sorted else True,
            "G5_net_daily_gain_gt_0_50_usd": daily_net_gain > 0.50,
        }
        report = GraduationReport(
            generated_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            cycles_completed=self.cycles_completed,
            venue_health=dict(self.venue_health),
            gross_candidates_seen=self.gross_candidates_seen,
            rule_gate_rejections=self.rule_gate_rejections,
            rule_gate_rejection_reasons=dict(self.rule_gate_rejection_reasons),
            executable_net_l2_count=self.executable_net_l2_count,
            locked_complete_baskets=total_locked,
            raced_unwinds=total_raced_unwinds,
            shadow_fill_realism_ratio=round(realism_ratio, 4),
            double_zero_incidents=self.double_zero_incidents,
            gross_structural_capture_usd=round(gross_capture, 4),
            total_unwind_bleed_usd=round(unwind_bleed, 4),
            unwind_bleed_pct_of_gross=round(bleed_pct, 2),
            observed_p99_latency_ms=round(p99_ms, 2),
            total_realized_shadow_net_pnl_usd=round(total_net_pnl, 4),
            est_unsettled_rebates_usd=round(est_rebates, 4),
            projected_daily_net_gain_usd=round(daily_net_gain, 4),
            competitor_decay_buckets=dict(self.competitor_decay_buckets),
            gates=gates,
            overall_graduated=all(gates.values()),
        )
        tmp_rep = self.data_dir / f".shadow_graduation_report.json.tmp.{os.getpid()}"
        tmp_rep.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
        os.replace(str(tmp_rep), str(self.report_path))

        if self.telemetry_store is not None:
            all_offline = bool(self.venue_health) and all(
                str((vh or {}).get("status") or "") in {"OK_OFFLINE_FIXTURE", "OFFLINE_FENCED"}
                for vh in self.venue_health.values()
            )
            cur_mode = (os.environ.get("DOMINUS_NETWORK_MODE") or "").strip().lower()
            ckpt_scope = "OFFLINE_SYNTHETIC" if (all_offline or cur_mode == "offline") else "LIVE_VERIFIED"
            self.telemetry_store.save_engine_checkpoint(
                {
                    "checkpoint_data_scope": ckpt_scope,
                    "cycles_completed": self.cycles_completed,
                    "gross_candidates_seen": self.gross_candidates_seen,
                    "rule_gate_rejections": self.rule_gate_rejections,
                    "rule_gate_rejection_reasons": dict(self.rule_gate_rejection_reasons),
                    "executable_net_l2_count": self.executable_net_l2_count,
                    "double_zero_incidents": self.double_zero_incidents,
                    "competitor_decay_buckets": dict(self.competitor_decay_buckets),
                    "takers_attempted": total_attempted,
                    "locked_complete_baskets": total_locked,
                    "raced_unwinds": total_raced_unwinds,
                    "gross_structural_capture_usd": round(gross_capture, 6),
                    "total_unwind_bleed_usd": round(unwind_bleed, 6),
                    "total_realized_shadow_net_pnl_usd": round(total_net_pnl, 6),
                    "est_unsettled_rebates_usd": round(est_rebates, 6),
                }
            )
        return report


# ---------------------------------------------------------------------------
# Live Read-Only Multi-Venue Poll & Cross-Matcher Orchestrator
# ---------------------------------------------------------------------------

def verify_cross_venue_pair_opportunity(
    pm: NormalizedBinaryMarket,
    ext: NormalizedBinaryMarket,
    *,
    clip_notional_usd: float = 15.0,
    bridge_drag_bps: float = 15.0,
    verifier: Optional[CrossVenueRuleVerifier] = None,
) -> Dict[str, Any]:
    """
    Section 8 Cross-Venue Opportunity Verification:
    Audits contract equivalence, resolution rules, expiry alignment, underlying oracle source,
    full-depth L2 executable VWAP costs, fees + slippage + bridge drag, partial-fill/legging risk
    (`takerDelayMs` + non-atomic cross-chain settlement), and theoretical vs executable net edge!
    """
    rv = verifier or CrossVenueRuleVerifier()
    target_sh = max(pm.min_shares, ext.min_shares, round(float(clip_notional_usd), 2))

    combos: List[Dict[str, Any]] = []
    for side_a, asks_a, side_b, asks_b in (
        ("YES", pm.yes_asks, "NO", ext.no_asks),
        ("NO", pm.no_asks, "YES", ext.yes_asks),
    ):
        top_a = asks_a[0].price if asks_a else 1.0
        top_b = asks_b[0].price if asks_b else 1.0
        theo_sum = top_a + top_b
        theo_edge_bps = round((1.0 - theo_sum) * 10_000.0, 2)

        walk_a = walk_asks_for_shares(asks_a, target_sh, pm)
        walk_b = walk_asks_for_shares(asks_b, target_sh, ext)
        rule_res = rv.verify_pair(pm, ext, side_a=side_a, side_b=side_b, price_a=top_a, price_b=top_b)

        both_filled = walk_a.filled and walk_b.filled
        fee_a_ps = (walk_a.taker_fee_usd / walk_a.filled_shares) if walk_a.filled_shares > 0 else compute_venue_taker_fee_usd(pm, 1.0, top_a)
        fee_b_ps = (walk_b.taker_fee_usd / walk_b.filled_shares) if walk_b.filled_shares > 0 else compute_venue_taker_fee_usd(ext, 1.0, top_b)
        vwap_a = walk_a.vwap_price if walk_a.filled_shares > 0 else top_a
        vwap_b = walk_b.vwap_price if walk_b.filled_shares > 0 else top_b
        slip_ps = max(0.0, (vwap_a - top_a) + (vwap_b - top_b))
        bridge_ps = (bridge_drag_bps / 10_000.0) if pm.venue != ext.venue else 0.0
        max_delay_ms = max(float(pm.taker_delay_ms or 0.0), float(ext.taker_delay_ms or 0.0))
        legging_bps = round((max_delay_ms / 250.0) * 8.0 + (12.0 if pm.venue != ext.venue else 0.0), 2)
        legging_ps = legging_bps / 10_000.0

        exec_all_in_ps = vwap_a + vwap_b + fee_a_ps + fee_b_ps + bridge_ps + legging_ps
        exec_net_edge_bps = round((1.0 - exec_all_in_ps) * 10_000.0, 2) if (asks_a and asks_b) else -10_000.0
        combos.append(
            {
                "direction": f"BUY_{side_a}_{pm.venue.upper()}__BUY_{side_b}_{ext.venue.upper()}",
                "side_a": side_a,
                "side_b": side_b,
                "top_ask_a": round(top_a, 6) if asks_a else None,
                "top_ask_b": round(top_b, 6) if asks_b else None,
                "vwap_ask_a": round(vwap_a, 6) if asks_a else None,
                "vwap_ask_b": round(vwap_b, 6) if asks_b else None,
                "book_shares_a": round(walk_a.total_book_shares, 2),
                "book_shares_b": round(walk_b.total_book_shares, 2),
                "depth_filled_for_clip": both_filled,
                "fee_a_bps": round(fee_a_ps * 10_000.0, 2),
                "fee_b_bps": round(fee_b_ps * 10_000.0, 2),
                "l2_slippage_bps": round(slip_ps * 10_000.0, 2),
                "bridge_drag_bps": round(bridge_ps * 10_000.0, 2),
                "legging_risk_bps": legging_bps,
                "theoretical_gross_edge_bps": theo_edge_bps if (asks_a and asks_b) else None,
                "executable_net_edge_bps": exec_net_edge_bps,
                "rule_verification": rule_res,
            }
        )

    best = max(combos, key=lambda c: float(c["executable_net_edge_bps"]))
    rver: RuleVerificationResult = best["rule_verification"]
    skew_sec = abs(int(pm.end_ts) - int(ext.end_ts)) if (pm.end_ts and ext.end_ts) else None
    actionable = bool(
        rver.passed
        and best["depth_filled_for_clip"]
        and float(best["executable_net_edge_bps"]) > 0.0
    )
    if not rver.passed:
        verdict = f"REJECTED_RULE_EQUIVALENCE:{','.join(rver.gate_failures)}"
    elif not best["depth_filled_for_clip"]:
        verdict = "REJECTED_INSUFFICIENT_L2_DEPTH"
    elif float(best["executable_net_edge_bps"]) <= 0.0:
        verdict = (
            f"REJECTED_NEGATIVE_EXECUTABLE_EDGE(theoretical={best['theoretical_gross_edge_bps']}bps,"
            f"executable_net={best['executable_net_edge_bps']}bps)"
        )
    else:
        verdict = f"ACTIONABLE_SHADOW_CANDIDATE(net={best['executable_net_edge_bps']}bps)"

    return {
        "pair_id": f"{pm.venue}:{pm.slug}<->{ext.venue}:{ext.slug}",
        "venue_a": pm.venue,
        "slug_a": pm.slug,
        "venue_b": ext.venue,
        "slug_b": ext.slug,
        "best_direction": best["direction"],
        "contract_equivalence": {
            "passed": rver.passed,
            "gate_failures": list(rver.gate_failures),
            "reason": rver.reason,
        },
        "resolution_rules": {
            "cancel_rule_a": pm.cancel_rule,
            "cancel_rule_b": ext.cancel_rule,
            "tennis_rule_a": pm.tennis_retirement_rule,
            "tennis_rule_b": ext.tennis_retirement_rule,
            "has_unlisted_draw": bool(pm.has_unlisted_draw or ext.has_unlisted_draw),
            "rules_hash_match": bool(pm.rules_hash and ext.rules_hash and pm.rules_hash == ext.rules_hash),
        },
        "expiry_alignment": {
            "end_ts_a": pm.end_ts,
            "end_ts_b": ext.end_ts,
            "expiry_skew_sec": skew_sec,
            "aligned": "GATE1_TIMESTAMP_MISMATCH" not in ",".join(rver.gate_failures),
        },
        "underlying_price_source": {
            "oracle_a": pm.oracle_family or "native_rules",
            "oracle_b": ext.oracle_family or "native_rules",
            "spot_ref_usd_a": pm.spot_reference_usd,
            "spot_ref_usd_b": ext.spot_reference_usd,
            "corridor_width_usd": rver.corridor_width_usd,
        },
        "full_depth_executable_costs": {
            "target_shares": target_sh,
            "top_ask_a": best["top_ask_a"],
            "top_ask_b": best["top_ask_b"],
            "vwap_ask_a": best["vwap_ask_a"],
            "vwap_ask_b": best["vwap_ask_b"],
            "book_shares_a": best["book_shares_a"],
            "book_shares_b": best["book_shares_b"],
            "depth_filled_for_clip": best["depth_filled_for_clip"],
        },
        "fees_and_slippage_bps": {
            "taker_fee_a_bps": best["fee_a_bps"],
            "taker_fee_b_bps": best["fee_b_bps"],
            "l2_slippage_bps": best["l2_slippage_bps"],
            "bridge_drag_bps": best["bridge_drag_bps"],
        },
        "partial_fill_and_legging_risk": {
            "taker_delay_ms_a": pm.taker_delay_ms,
            "taker_delay_ms_b": ext.taker_delay_ms,
            "non_atomic_cross_chain": pm.venue != ext.venue,
            "legging_risk_bps": best["legging_risk_bps"],
        },
        "theoretical_gross_edge_bps": best["theoretical_gross_edge_bps"],
        "executable_net_edge_bps": best["executable_net_edge_bps"],
        "actionable": actionable,
        "verdict_reason": verdict,
    }


class LiveCrossVenueShadowCollector:
    """
    Polls live public/read-only endpoints across all 6 Stage G venues (`Polymarket`, `Limitless`,
    `SX Bet OBv3`, `Predict.fun`, `ForecastEx / IBKR`, `STX Ontario`), isolates per-venue
    authorization/circuit-breaker states so restricted or faulted venues never halt authorized
    collectors, evaluates pairwise + 2–6 leg complete baskets via 3-tier L2 simulation, and
    persists restart-safe SQLite WAL telemetry + watchdog health metrics.
    """

    ALL_VENUES: Tuple[str, ...] = (
        "polymarket",
        "limitless",
        "sx_bet",
        "predict_fun",
        "forecastex",
        "stx_ontario",
    )

    def __init__(
        self,
        engine: HonestCrossVenueShadowEngine,
        *,
        limitless_pages: int = 12,
        limitless_orderbook_top_n: int = 48,
        predict_testnet_smoke: bool = False,
        authorized_venues: Optional[Iterable[str]] = None,
        blocked_venue_reasons: Optional[Mapping[str, str]] = None,
        env: Optional[Mapping[str, str]] = None,
        transport: Any = None,
    ) -> None:
        from src.polymarket_research.cross_venue_connectors import (
            ForecastExIBKRConnector,
            LimitlessConnector,
            PolymarketConnector,
            PredictFunConnector,
            STXOntarioConnector,
            SXBetOBv3Connector,
        )
        from src.polymarket_research.cross_venue_l2_and_baskets import (
            Level2ExecutionSimulator,
            MultiVenueArbitrageAnalyzer,
        )
        from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowRuntimeWatchdog

        self.engine = engine
        self.limitless_pages = max(1, int(limitless_pages))
        self.limitless_orderbook_top_n = max(2, int(limitless_orderbook_top_n))
        self.predict_testnet_smoke = bool(predict_testnet_smoke)
        self.env: Dict[str, str] = dict(env) if env is not None else dict(os.environ)
        self._injected_transport = transport
        self.authorized_venues: Optional[set[str]] = (
            {str(v).strip().lower() for v in authorized_venues}
            if authorized_venues is not None
            else None
        )
        self.blocked_venue_reasons: Dict[str, str] = (
            {str(k).strip().lower(): str(v) for k, v in blocked_venue_reasons.items()}
            if blocked_venue_reasons is not None
            else {}
        )

        self.connectors: Dict[str, Any] = {
            "polymarket": PolymarketConnector(max_pages=2, page_limit=100, max_hydrated_markets=140, env=self.env),
            "limitless": LimitlessConnector(
                max_pages=self.limitless_pages,
                orderbook_top_n=self.limitless_orderbook_top_n,
                env=self.env,
            ),
            "sx_bet": SXBetOBv3Connector(max_market_pages=2, max_order_batches=2, env=self.env),
            "predict_fun": PredictFunConnector(
                max_pages=3,
                page_size=100,
                orderbook_top_n=80,
                testnet_smoke=self.predict_testnet_smoke,
                env=self.env,
            ),
            "forecastex": ForecastExIBKRConnector(env=self.env),
            "stx_ontario": STXOntarioConnector(env=self.env),
        }
        self.analyzer = MultiVenueArbitrageAnalyzer(
            simulator=Level2ExecutionSimulator(bridge_drag_bps=self.engine.bridge_drag_bps),
            rule_verifier=self.engine.verifier,
            clip_notional_usd=self.engine.clip_notional_usd,
        )
        self.watchdog = (
            ShadowRuntimeWatchdog(self.engine.telemetry_store)
            if self.engine.telemetry_store is not None
            else None
        )
        from src.polymarket_research.cross_venue_unblock_and_certification import (
            CredentialLifecycleManager,
            PersistentBlockerRegistry,
            RestrictionRegistry,
            VenueCertificationTracker,
        )

        self.credential_manager = CredentialLifecycleManager()
        self.blocker_registry = PersistentBlockerRegistry(self.engine.data_dir)
        self.restriction_registry = RestrictionRegistry(self.engine.data_dir)
        self.certification_tracker = VenueCertificationTracker(self.engine.data_dir)

    async def aclose(self) -> None:
        """Cleanly stops all background realtime WebSocket clients across all connectors."""
        for conn in self.connectors.values():
            if hasattr(conn, "aclose"):
                await conn.aclose()
            elif hasattr(conn, "stop_background_ws"):
                conn.stop_background_ws()

    def _is_venue_authorized(self, venue: str) -> bool:
        v = venue.strip().lower()
        conn = self.connectors.get(v)
        if self.authorized_venues is None:
            if conn is not None:
                conn.snapshot.authorization_state = "AUTHORIZED_LIVE"
            return True
        if v in self.authorized_venues:
            if conn is not None and conn.snapshot.authorization_state not in ("AUTH_FAILED_PERMANENT",):
                conn.snapshot.authorization_state = "AUTHORIZED_LIVE"
            return True
        reason = self.blocked_venue_reasons.get(v, "P0_GATE_0_NOT_AUTHORIZED")
        if conn is not None:
            if reason == "DISABLED_BY_CONFIG":
                conn.snapshot.authorization_state = "DISABLED_BY_CONFIG"
            elif reason.startswith("CREDENTIALS_REQUIRED"):
                conn.snapshot.authorization_state = "MISSING_CREDENTIALS"
            elif reason.startswith("APPROVAL_PENDING"):
                conn.snapshot.authorization_state = "APPROVAL_PENDING"
            else:
                conn.snapshot.authorization_state = "BLOCKED_JURISDICTION"
            conn.snapshot.connectivity_state = "DISCONNECTED"
            conn.snapshot.health_state = "IDLE"
            conn.snapshot.permanent_halt_reason = reason
            conn.breaker.record_permanent_halt(reason)
        self.engine.venue_health[v] = {
            "status": "AUTH_BLOCKED",
            "markets_parsed": 0,
            "reason": reason,
        }
        return False

    async def fetch_limitless(self, http: ReadOnlyHttpClient) -> List[NormalizedBinaryMarket]:
        raw_items: List[Mapping[str, Any]] = []
        latencies: List[float] = []
        for page in range(1, self.limitless_pages + 1):
            # Hard Limitless pagination rule: limit MUST NOT exceed 25 (`HTTP 400` above 25)
            url = f"{LIMITLESS_API_URL}/markets/active?limit=25&page={page}"
            status, payload, ms = await http.get_json(url)
            latencies.append(ms)
            if status != 200 or not payload:
                break
            batch = payload.get("data") if isinstance(payload, Mapping) else payload
            if not isinstance(batch, list) or not batch:
                break
            raw_items.extend(batch)

        # Prioritize Polymarket-linked (`isPolyArbitrage`) and active short-horizon crypto markets for L2 orderbooks
        prioritized = sorted(
            raw_items,
            key=lambda r: (
                0 if ((r.get("metadata") or {}).get("isPolyArbitrage")) else 1,
                0 if "up-or-down" in str(r.get("slug") or "") else 1,
            ),
        )
        book_slugs = [str(r.get("slug")) for r in prioritized[: self.limitless_orderbook_top_n] if r.get("slug")]
        book_tasks = [http.get_json(f"{LIMITLESS_API_URL}/markets/{s}/orderbook") for s in book_slugs]
        book_results = await asyncio.gather(*book_tasks) if book_tasks else []
        books_by_slug: Dict[str, Mapping[str, Any]] = {}
        for slug, (st, ob, ms) in zip(book_slugs, book_results):
            latencies.append(ms)
            if st == 200 and isinstance(ob, Mapping):
                books_by_slug[slug] = ob

        markets: List[NormalizedBinaryMarket] = []
        for item in raw_items:
            slug = str(item.get("slug") or "")
            parsed = parse_limitless_market(item, books_by_slug.get(slug))
            if parsed is not None:
                markets.append(parsed)

        self.engine.latency_samples_ms.extend([x for x in latencies if x > 0])
        self.engine.venue_health["limitless"] = {
            "status": "OK" if markets else "EMPTY",
            "markets_parsed": len(markets),
            "l2_books_fetched": len(books_by_slug),
            "poly_arb_linked": sum(1 for m in markets if m.is_poly_arbitrage),
            "median_http_ms": round(sorted(latencies)[len(latencies) // 2], 2) if latencies else None,
        }
        return markets

    async def fetch_sx_bet(self, http: ReadOnlyHttpClient) -> List[NormalizedBinaryMarket]:
        latencies: List[float] = []
        st_meta, meta_payload, ms_meta = await http.get_json(f"{SX_BET_API_URL}/metadata/obv3")
        latencies.append(ms_meta)
        betting_delay_ms = 0.0
        if st_meta == 200 and isinstance(meta_payload, Mapping):
            bd = (meta_payload.get("data") or {}).get("bettingDelay")
            if isinstance(bd, (int, float)):
                betting_delay_ms = float(bd) * 1000.0

        endpoints = (
            f"{SX_BET_API_URL}/summary-v3/popular",
            f"{SX_BET_API_URL}/summary-v3/inplay",
            f"{SX_BET_API_URL}/summary-v3/upcoming",
        )
        res_list = await asyncio.gather(*(http.get_json(u) for u in endpoints))
        by_hash: Dict[str, NormalizedBinaryMarket] = {}
        for st, payload, ms in res_list:
            latencies.append(ms)
            if st != 200 or not isinstance(payload, Mapping):
                continue
            sports = (payload.get("data") or {}).get("sports") or []
            for sp in sports:
                sp_label = str(sp.get("sportLabel") or "")
                for lg in sp.get("leagues") or []:
                    lg_label = str(lg.get("leagueLabel") or "")
                    for fx in lg.get("fixtures") or []:
                        for m in parse_sx_bet_summary_fixture(
                            fx,
                            sport_label=sp_label,
                            league_label=lg_label,
                            betting_delay_ms=betting_delay_ms,
                        ):
                            by_hash[m.market_id] = m

        self.engine.latency_samples_ms.extend([x for x in latencies if x > 0])
        self.engine.venue_health["sx_bet"] = {
            "status": "OK" if by_hash else "EMPTY",
            "markets_parsed": len(by_hash),
            "protocol": "OBv3_PUBLIC_SUMMARY_COMPLEMENT_VERIFIED",
            "api_key_configured": bool(os.environ.get("SX_BET_API_KEY")),
            "median_http_ms": round(sorted(latencies)[len(latencies) // 2], 2) if latencies else None,
        }
        return list(by_hash.values())

    async def fetch_predict_fun(self, http: ReadOnlyHttpClient) -> List[NormalizedBinaryMarket]:
        api_key = os.environ.get("PREDICT_FUN_API_KEY", "").strip()
        if not api_key and not self.predict_testnet_smoke:
            self.engine.venue_health["predict_fun"] = {
                "status": "SKIPPED_NO_API_KEY",
                "markets_parsed": 0,
                "note": "Set PREDICT_FUN_API_KEY (developers.predict.fun) for mainnet, or pass --predict-testnet-smoke",
            }
            return []

        base_url = PREDICT_FUN_MAINNET_URL if api_key else PREDICT_FUN_TESTNET_URL
        headers = {"x-api-key": api_key} if api_key else None
        st, payload, ms = await http.get_json(f"{base_url}/markets?first=25", headers=headers)
        if st != 200 or not isinstance(payload, Mapping):
            self.engine.venue_health["predict_fun"] = {
                "status": f"HTTP_{st}",
                "markets_parsed": 0,
                "mode": "mainnet" if api_key else "testnet_smoke",
            }
            return []

        items = payload.get("data") or []
        top_ids = [str(it.get("id")) for it in items[:8] if it.get("id") is not None]
        ob_res = await asyncio.gather(
            *(http.get_json(f"{base_url}/markets/{mid}/orderbook", headers=headers) for mid in top_ids)
        )
        obs: Dict[str, Mapping[str, Any]] = {}
        for mid, (ost, opayload, oms) in zip(top_ids, ob_res):
            if ost == 200 and isinstance(opayload, Mapping):
                obs[mid] = opayload

        markets: List[NormalizedBinaryMarket] = []
        for it in items:
            m = parse_predict_fun_market(it, obs.get(str(it.get("id"))))
            if m is not None:
                markets.append(m)

        self.engine.venue_health["predict_fun"] = {
            "status": "OK_MAINNET" if api_key else "OK_TESTNET_SMOKE",
            "markets_parsed": len(markets),
            "l2_books_fetched": len(obs),
            "polymarket_linked": sum(1 for m in markets if m.polymarket_condition_ids),
            "http_ms": round(ms, 2),
        }
        return markets

    async def fetch_polymarket_anchors(
        self,
        http: ReadOnlyHttpClient,
        external_markets: Sequence[NormalizedBinaryMarket],
    ) -> List[NormalizedBinaryMarket]:
        """
        Fetches targeted Polymarket Gamma markets matching:
          1. Limitless `external_slug` (`isPolyArbitrage == True`)
          2. Limitless `5m` / `15m` Chainlink TWAP Unix slugs (`btc-updown-15m-{ts}`)
          3. Active Polymarket sports & crypto slates
        Then hydrates CLOB `/book` + `/fee-rate` for matched tokens!
        """
        target_slugs: List[str] = []
        for em in external_markets:
            if em.external_slug:
                target_slugs.append(em.external_slug)
            m_ts = _UNIX_TAIL_RE.search(em.slug)
            if m_ts and em.asset in ("BTC", "ETH", "SOL", "XRP") and em.horizon in ("5m", "15m"):
                ts_str = m_ts.group(1)
                target_slugs.append(f"{em.asset.lower()}-updown-{em.horizon}-{ts_str}")

        dedup_slugs = list(dict.fromkeys(target_slugs))[:18]
        slug_tasks = [
            http.get_json(f"{POLYMARKET_GAMMA_URL}/markets?slug={urllib.parse.quote(s)}")
            for s in dedup_slugs
        ]
        general_tasks = [
            http.get_json(f"{POLYMARKET_GAMMA_URL}/markets?active=true&closed=false&limit=60&order=volume24hr&ascending=false"),
        ]
        results = await asyncio.gather(*slug_tasks, *general_tasks)

        raw_by_id: Dict[str, Mapping[str, Any]] = {}
        latencies: List[float] = []
        for st, payload, ms in results:
            latencies.append(ms)
            if st == 200 and isinstance(payload, list):
                for item in payload:
                    if isinstance(item, Mapping) and item.get("id"):
                        raw_by_id[str(item["id"])] = item

        prelim: List[Tuple[Mapping[str, Any], NormalizedBinaryMarket]] = []
        ext_matchups = {m.asset for m in external_markets if m.category == "sports" and m.asset}
        ext_conds = {cid for m in external_markets for cid in m.polymarket_condition_ids}
        slug_set = set(dedup_slugs)

        for raw in raw_by_id.values():
            pm = parse_polymarket_gamma_market(raw)
            if pm is None:
                continue
            is_matched = (
                pm.slug in slug_set
                or (pm.condition_id and pm.condition_id in ext_conds)
                or (pm.category == "sports" and pm.asset in ext_matchups)
            )
            prelim.append((raw, pm if is_matched else pm))

        # Hydrate real CLOB L2 orderbooks + dynamic fee_rate_bps for matched Polymarket markets
        matched_rows = [
            (raw, pm)
            for raw, pm in prelim
            if pm.slug in slug_set
            or (pm.condition_id and pm.condition_id in ext_conds)
            or (pm.category == "sports" and pm.asset in ext_matchups)
        ][:16]

        token_ids: List[str] = []
        for _, pm in matched_rows:
            token_ids.extend([pm.yes_token_id, pm.no_token_id])
        token_ids = list(dict.fromkeys([t for t in token_ids if t]))

        book_res = await asyncio.gather(
            *(http.get_json(f"{POLYMARKET_CLOB_URL}/book?token_id={urllib.parse.quote(tid)}") for tid in token_ids)
        )
        fee_res = await asyncio.gather(
            *(http.get_json(f"{POLYMARKET_CLOB_URL}/fee-rate?token_id={urllib.parse.quote(tid)}") for tid in token_ids[:16])
        )
        books_by_tok: Dict[str, Mapping[str, Any]] = {}
        for tid, (bst, bpay, bms) in zip(token_ids, book_res):
            latencies.append(bms)
            if bst == 200 and isinstance(bpay, Mapping):
                books_by_tok[tid] = bpay

        fees_by_tok: Dict[str, float] = {}
        for tid, (fst, fpay, _) in zip(token_ids[:16], fee_res):
            if fst == 200 and isinstance(fpay, Mapping) and fpay.get("base_fee") is not None:
                bf = float(fpay["base_fee"])
                fees_by_tok[tid] = bf if bf >= 1.0 else bf * 10_000.0

        final_markets: List[NormalizedBinaryMarket] = []
        hydrated_ids = {str(raw.get("id")) for raw, _ in matched_rows}
        for raw, pm in matched_rows:
            re_parsed = parse_polymarket_gamma_market(
                raw,
                yes_book=books_by_tok.get(pm.yes_token_id),
                no_book=books_by_tok.get(pm.no_token_id),
                fee_rate_bps_override=fees_by_tok.get(pm.yes_token_id),
            )
            if re_parsed is not None:
                final_markets.append(re_parsed)

        for raw, pm in prelim:
            if str(raw.get("id")) not in hydrated_ids:
                final_markets.append(pm)

        self.engine.latency_samples_ms.extend([x for x in latencies if x > 0])
        self.engine.venue_health["polymarket"] = {
            "status": "OK" if final_markets else "EMPTY",
            "markets_parsed": len(final_markets),
            "matched_l2_hydrated": len(matched_rows),
            "median_http_ms": round(sorted(latencies)[len(latencies) // 2], 2) if latencies else None,
        }
        return final_markets

    @staticmethod
    def match_pairs(
        poly_markets: Sequence[NormalizedBinaryMarket],
        external_markets: Sequence[NormalizedBinaryMarket],
    ) -> List[Tuple[NormalizedBinaryMarket, NormalizedBinaryMarket]]:
        by_slug = {m.slug: m for m in poly_markets if m.slug}
        by_cond = {m.condition_id: m for m in poly_markets if m.condition_id}
        by_sports_key = {m.asset: m for m in poly_markets if m.category == "sports" and m.asset}
        by_crypto_sig = {
            (m.asset, m.horizon, m.end_ts): m
            for m in poly_markets
            if m.category == "crypto" and m.asset and m.horizon and m.end_ts
        }

        pairs: List[Tuple[NormalizedBinaryMarket, NormalizedBinaryMarket]] = []
        seen: set[Tuple[str, str]] = set()

        for ext in external_markets:
            pm: Optional[NormalizedBinaryMarket] = None
            if ext.external_slug and ext.external_slug in by_slug:
                pm = by_slug[ext.external_slug]
            if pm is None:
                m_ts = _UNIX_TAIL_RE.search(ext.slug)
                if m_ts and ext.asset and ext.horizon in ("5m", "15m"):
                    cand_slug = f"{ext.asset.lower()}-updown-{ext.horizon}-{m_ts.group(1)}"
                    pm = by_slug.get(cand_slug)
            if pm is None and ext.polymarket_condition_ids:
                for cid in ext.polymarket_condition_ids:
                    if cid in by_cond:
                        pm = by_cond[cid]
                        break
            if pm is None and ext.category == "sports" and ext.asset in by_sports_key:
                pm = by_sports_key[ext.asset]
            if pm is None and ext.category == "crypto" and ext.asset and ext.horizon and ext.end_ts:
                pm = by_crypto_sig.get((ext.asset, ext.horizon, ext.end_ts))

            if pm is not None:
                key = (pm.slug, f"{ext.venue}:{ext.slug}")
                if key not in seen:
                    seen.add(key)
                    pairs.append((pm, ext))
        return pairs

    async def _poll_connector_isolated(
        self,
        venue: str,
        transport: Any,
        *,
        hint_markets: Sequence[NormalizedBinaryMarket] = (),
    ) -> List[NormalizedBinaryMarket]:
        """Polls a single authorized venue connector with complete fault isolation."""
        if not self._is_venue_authorized(venue):
            return []
        conn = self.connectors[venue]
        prev_err = conn.snapshot.last_error
        try:
            mkts = await conn.poll_markets(transport, hint_markets=hint_markets)
        except Exception as exc:
            logger.warning("Isolated connector fault on %s: %s", venue, exc)
            conn.snapshot.health_state = "FAULTED"
            conn.snapshot.last_error = f"UNHANDLED_CONNECTOR_ERR:{exc}"
            mkts = []

        self.engine.venue_health[venue] = conn.snapshot.to_health_dict()
        if conn.snapshot.median_latency_ms and conn.snapshot.median_latency_ms > 0:
            self.engine.latency_samples_ms.append(conn.snapshot.median_latency_ms)

        store = self.engine.telemetry_store
        if store is not None and conn.snapshot.last_error and conn.snapshot.last_error != prev_err:
            fclass = (
                "AUTH_PERMANENT"
                if conn.snapshot.authorization_state in ("AUTH_FAILED_PERMANENT", "MISSING_CREDENTIALS")
                else ("RATE_LIMIT" if conn.snapshot.health_state == "RATE_LIMITED" else "TRANSIENT")
            )
            store.record_api_event(
                venue=venue,
                event_type="POLL_FAULT",
                fault_class=fclass,
                downtime_sec=conn.snapshot.downtime_accumulated_sec,
                detail=conn.snapshot.last_error,
            )
        return mkts

    async def run_single_cycle(self) -> Dict[str, Any]:
        from src.polymarket_research.cross_venue_connectors import ResilientReadOnlyTransport
        from src.polymarket_research.cross_venue_l2_and_baskets import LegSpec

        allow_self_signed = str(self.env.get("IBKR_ALLOW_LOCALHOST_SELF_SIGNED", "")).strip().lower() in {"1", "true", "yes"}
        own_transport = self._injected_transport is None
        transport = (
            ResilientReadOnlyTransport(allow_localhost_self_signed=allow_self_signed)
            if own_transport
            else self._injected_transport
        )

        async def _execute_with_transport(tr: Any) -> Dict[str, Any]:
            primary_ext_venues = ("limitless", "sx_bet", "predict_fun", "forecastex")
            primary_lists = await asyncio.gather(
                *(self._poll_connector_isolated(v, tr) for v in primary_ext_venues)
            )
            by_venue: Dict[str, List[NormalizedBinaryMarket]] = dict(zip(primary_ext_venues, primary_lists))

            live_external: List[NormalizedBinaryMarket] = []
            for v_name in ("limitless", "sx_bet", "forecastex"):
                live_external.extend(by_venue[v_name])
            # Strictly exclude Predict.fun TESTNET_SANDBOX markets from mainnet cross-venue matching;
            # include ONLY verified mainnet markets (`LIVE_VERIFIED` with `PREDICT_FUN_API_KEY` present).
            sandbox_markets: List[NormalizedBinaryMarket] = [
                m for m in by_venue["predict_fun"] if m.data_origin == "TESTNET_SANDBOX"
            ]
            if (self.env.get("PREDICT_FUN_API_KEY") or os.environ.get("PREDICT_FUN_API_KEY") or "").strip():
                live_external.extend(
                    m for m in by_venue["predict_fun"] if m.data_origin == "LIVE_VERIFIED"
                )

            stx_markets = await self._poll_connector_isolated("stx_ontario", tr, hint_markets=live_external)
            by_venue["stx_ontario"] = stx_markets
            live_external.extend(stx_markets)

            poly_markets = await self._poll_connector_isolated("polymarket", tr, hint_markets=live_external)
            by_venue["polymarket"] = poly_markets
            all_live_markets = list(poly_markets) + list(live_external)

            pairs = self.analyzer.pair_all_venues(all_live_markets)
            intra_cands = self.engine.scan_intra_venue_complete_sets(all_live_markets)
            cross_cands = self.engine.scan_cross_venue_pairs(pairs)
            multi_baskets, multi_rejects = self.analyzer.scan_multi_leg_complete_baskets(all_live_markets)
            all_cands = intra_cands + cross_cands

            # Determine honest session data provenance (`LIVE_VERIFIED` vs `REGULATORY_PUBLIC_DELAYED`)
            origins_seen = {m.data_origin for m in all_live_markets}
            session_origin = (
                "LIVE_VERIFIED"
                if "LIVE_VERIFIED" in origins_seen
                else ("REGULATORY_PUBLIC_DELAYED" if "REGULATORY_PUBLIC_DELAYED" in origins_seen else "NONE")
            )

            store = self.engine.telemetry_store
            if store is not None:
                if session_origin != "NONE":
                    if store.current_session_id is None:
                        store.start_session(
                            network_mode=self.env.get("DOMINUS_NETWORK_MODE", "live_public"),
                            data_origin=session_origin,
                        )
                    else:
                        store.heartbeat_session()
                disk_free_mb = shutil.disk_usage(str(self.engine.data_dir)).free / (1024.0 * 1024.0)
                markets_to_persist = all_live_markets + sandbox_markets
                if markets_to_persist:
                    store.ingest_markets(markets_to_persist, store_l2_json=(disk_free_mb >= 256.0))
                for ma, mb in pairs:
                    store.record_pairing(ma, mb, rule_passed=True)
                for mb_ev in multi_baskets:
                    store.record_signal(mb_ev, data_origin=session_origin if session_origin != "NONE" else "LIVE_VERIFIED")
                for rj in multi_rejects:
                    store.record_rejection(
                        candidate_key=rj["group_id"],
                        stage="MULTI_LEG_PARTITION",
                        reason=rj["reason"],
                        venues=["multi"],
                        gross_edge_bps=0.0,
                        data_origin=session_origin if session_origin != "NONE" else "LIVE_VERIFIED",
                    )

            three_tier_previews: List[Dict[str, Any]] = [asdict(ev) for ev in multi_baskets[:4]]

            # Honest post-delay L2 re-verification batched ONCE per cycle across all non-maker candidates
            # (prevents O(N) sequential full-venue HTTP/WS polls when multiple pairs fire simultaneously).
            pre_by_venue_slug: Dict[Tuple[str, str], NormalizedBinaryMarket] = {
                (m.venue, m.slug): m for m in all_live_markets
            }
            taker_cands = [c for c in all_cands if c.family != "XV_PASSIVE_MAKER_ANCHOR"]
            refetched_by_venue_slug: Dict[Tuple[str, str], NormalizedBinaryMarket] = {}
            if taker_cands:
                max_delay_s = min(
                    2.0,
                    max(0.05, max(c.effective_delay_ms for c in taker_cands) / 1000.0),
                )
                await asyncio.sleep(max_delay_s)
                involved = list(
                    dict.fromkeys(v for c in taker_cands for v in (c.venue_a, c.venue_b))
                )
                cand_slugs = {(c.venue_a, c.market_a_slug) for c in taker_cands} | {
                    (c.venue_b, c.market_b_slug) for c in taker_cands
                }
                cand_hints = [m for m in all_live_markets if (m.venue, m.slug) in cand_slugs]
                non_poly_inv = [v for v in involved if v != "polymarket"]
                refetched_lists = (
                    await asyncio.gather(
                        *(self._poll_connector_isolated(inv_v, tr, hint_markets=cand_hints) for inv_v in non_poly_inv)
                    )
                    if non_poly_inv
                    else []
                )
                for inv_v, mkts_v in zip(non_poly_inv, refetched_lists):
                    for m_v in mkts_v:
                        refetched_by_venue_slug[(inv_v, m_v.slug)] = m_v
                if "polymarket" in involved:
                    hints = [
                        *cand_hints,
                        *(m_v for sub in refetched_lists for m_v in sub),
                    ] or live_external
                    poly_refetched = await self._poll_connector_isolated("polymarket", tr, hint_markets=hints)
                    for m_p in poly_refetched:
                        refetched_by_venue_slug[("polymarket", m_p.slug)] = m_p

            for cand in all_cands:
                ma_pre = pre_by_venue_slug.get((cand.venue_a, cand.market_a_slug))
                mb_pre = pre_by_venue_slug.get((cand.venue_b, cand.market_b_slug))

                if cand.family == "XV_PASSIVE_MAKER_ANCHOR":
                    self.engine.simulate_honest_execution(
                        cand,
                        post_delay_market_a=ma_pre,
                        post_delay_market_b=mb_pre,
                        observed_trade_through_shares=0.0,
                        queue_ahead_shares=50.0,
                    )
                    ma_after, mb_after = ma_pre, mb_pre
                else:
                    ma_after = refetched_by_venue_slug.get((cand.venue_a, cand.market_a_slug))
                    mb_after = (
                        ma_after
                        if cand.venue_a == cand.venue_b
                        else refetched_by_venue_slug.get((cand.venue_b, cand.market_b_slug))
                    )
                    self.engine.simulate_honest_execution(
                        cand,
                        post_delay_market_a=ma_after,
                        post_delay_market_b=mb_after,
                    )

                if ma_pre is not None and mb_pre is not None:
                    maker_limit_px = (
                        round(cand.leg_b_entry_cost_usd / max(cand.shares, 1.0), 6)
                        if (cand.family == "XV_PASSIVE_MAKER_ANCHOR" and cand.leg_b_entry_cost_usd > 0.0)
                        else None
                    )
                    ev2 = self.analyzer.simulator.evaluate_basket(
                        basket_id=cand.candidate_key,
                        basket_type="COMPLETE_SET_2LEG" if cand.venue_a == cand.venue_b else "CROSS_VENUE_2LEG",
                        legs=[
                            LegSpec(market=ma_pre, side=cand.side_a),
                            LegSpec(
                                market=mb_pre,
                                side=cand.side_b,
                                execution_style="PASSIVE_MAKER" if cand.family == "XV_PASSIVE_MAKER_ANCHOR" else "TAKER",
                                limit_price=maker_limit_px,
                            ),
                        ],
                        target_notional_usd=self.engine.clip_notional_usd,
                        post_delay_legs=[ma_after, mb_after],
                        observed_trade_through_shares=0.0 if cand.family == "XV_PASSIVE_MAKER_ANCHOR" else None,
                    )
                    if store is not None:
                        if ev2.simulated_executable.executable:
                            store.record_signal(ev2, data_origin=ma_pre.data_origin)
                        else:
                            store.record_rejection(
                                candidate_key=cand.candidate_key,
                                stage="L2_SIMULATOR",
                                reason=ev2.simulated_executable.status,
                                venues=ev2.venues,
                                gross_edge_bps=ev2.theoretical.gross_theoretical_edge_bps,
                                data_origin=ma_pre.data_origin,
                            )
                    if len(three_tier_previews) < 8:
                        three_tier_previews.append(asdict(ev2))

            self.engine.cycles_completed += 1
            if store is not None and (self.engine.cycles_completed == 1 or self.engine.cycles_completed % 20 == 0):
                await asyncio.to_thread(store.prune_expired_telemetry)
            report = self.engine.build_graduation_report()
            op_snaps = {v: self.connectors[v].snapshot for v in self.ALL_VENUES}
            wd_dict = asdict(self.watchdog.evaluate(op_snaps)) if self.watchdog is not None else None
            win_dict = (
                await asyncio.to_thread(store.build_campaign_window_summaries)
                if store is not None
                else None
            )

            from src.polymarket_research.cross_venue_shadow_deployment_gates import evaluate_all_venues_authorization

            eff_mode = (self.env.get("DOMINUS_NETWORK_MODE") or "live_public").strip().lower()
            cur_auth = evaluate_all_venues_authorization(self.env, network_mode_override=eff_mode)
            for v_k, dec_v in cur_auth.items():
                if v_k in op_snaps:
                    op_snaps[v_k].verified_outcome_state = dec_v.verified_outcome_state
                    op_snaps[v_k].scope_permissions = dict(dec_v.scope_permissions)
            await asyncio.to_thread(
                self.certification_tracker.record_cycle_observation,
                connector_snapshots=op_snaps,
                network_mode=eff_mode,
            )
            cert_dict = await asyncio.to_thread(
                self.certification_tracker.build_certification_report,
                auth_decisions=cur_auth,
            )
            blk_dict = await asyncio.to_thread(
                self.blocker_registry.sync_from_runtime_state,
                env=self.env,
                auth_decisions=cur_auth,
                connector_snapshots=op_snaps,
                collector=self,
                cred_manager=self.credential_manager,
            )
            rest_dict = await asyncio.to_thread(
                self.restriction_registry.sync_and_persist,
                env=self.env,
                auth_decisions=cur_auth,
                connector_snapshots=op_snaps,
            )
            if store is not None:
                store.drop_clean_file_page_cache()

            verified_pair_audits = [
                verify_cross_venue_pair_opportunity(
                    pm,
                    ext,
                    clip_notional_usd=self.engine.clip_notional_usd,
                    bridge_drag_bps=self.engine.bridge_drag_bps,
                    verifier=self.engine.verifier,
                )
                for pm, ext in pairs[:20]
            ]

            return {
                "cycle": self.engine.cycles_completed,
                "data_origin": session_origin,
                "matched_cross_venue_pairs": len(pairs),
                "multi_leg_complete_baskets_found": len(multi_baskets),
                "matched_pair_Previews": [
                    {
                        "polymarket": pm.slug,
                        "venue_a": pm.venue,
                        "external_venue": ext.venue,
                        "external_slug": ext.slug,
                        "oracle_a": pm.oracle_family,
                        "oracle_b": ext.oracle_family,
                        "poly_yes_ask": pm.yes_asks[0].price if pm.yes_asks else None,
                        "poly_no_ask": pm.no_asks[0].price if pm.no_asks else None,
                        "ext_yes_ask": ext.yes_asks[0].price if ext.yes_asks else None,
                        "ext_no_ask": ext.no_asks[0].price if ext.no_asks else None,
                    }
                    for pm, ext in pairs[:10]
                ],
                "verified_pair_audits": verified_pair_audits,
                "three_tier_evaluations": three_tier_previews,
                "intra_candidates": len(intra_cands),
                "cross_candidates": len(cross_cands),
                "connector_states": {k: asdict(v) for k, v in op_snaps.items()},
                "watchdog": wd_dict,
                "campaign_windows": win_dict,
                "certification": cert_dict,
                "blocker_registry": blk_dict,
                "restriction_registry": rest_dict,
                "graduation_report": asdict(report),
            }

        if own_transport:
            async with transport as tr:
                return await _execute_with_transport(tr)
        return await _execute_with_transport(transport)
