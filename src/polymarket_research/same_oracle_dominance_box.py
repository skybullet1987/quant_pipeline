#!/usr/bin/env python3
r"""
Same-Oracle Riskless Dominance Box Engine (Option #7: 15m vs 5m Chainlink 60s-TWAP)
===================================================================================
Captures deterministic, zero-basis cross-horizon dominance arbitrage between overlapping
Polymarket `15m` and `5m` Up/Down crypto markets sharing the exact same terminal timestamp
(`:10-:15`, `:25-:30`, `:40-:45`, `:55-:00` of every clock hour) across `BTC`, `ETH`, `SOL`, `XRP`.

Mathematical Dominance Invariant:
  Both `15m` and `5m` resolve on the identical Chainlink `60s` USD TWAP `eventMetadata.finalPrice`
  $S_T$ (`*-usd-twap-60s-streams`), with `"Up"` iff $S_T \ge K$ and `"Down"` iff $S_T < K$, where
  $K$ (`eventMetadata.priceToBeat`) equals the finalized `eventMetadata.finalPrice` of the
  immediately preceding `5m` Gamma event (`{asset}-updown-5m-{start_ts - 300}`).

  Let $K_{\text{low}} < K_{\text{high}}$ be the two opening Chainlink strikes:
    - Leg A: `UP` on the market with strike $K_{\text{low}}$   (pays $1 iff $S_T \ge K_{\text{low}}$)
    - Leg B: `DOWN` on the market with strike $K_{\text{high}}$ (pays $1 iff $S_T < K_{\text{high}}$)

  State-by-state terminal payout per 1-share pair (`Q_A == Q_B == 1`):
    1. $S_T < K_{\text{low}}$               -> Leg A = $0, Leg B = $1 -> Total = $1.00
    2. $K_{\text{low}} \le S_T < K_{\text{high}}$ -> Leg A = $1, Leg B = $1 -> Total = $2.00 (Double Payout)
    3. $S_T \ge K_{\text{high}}$            -> Leg A = $1, Leg B = $0 -> Total = $1.00

  Whenever all-in equal-share L2 VWAP + both V2 taker fees (`7% * p * (1 - p)`) <= $0.995,
  the trade locks in a riskless floor >= +$0.005/pair plus a free $1.00 corridor lottery.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

CORE_LIVE_DOMINANCE_ASSETS: Tuple[str, ...] = ("BTC", "ETH", "SOL", "XRP")
EXPANSION_DOMINANCE_ASSETS: Tuple[str, ...] = ("BNB", "DOGE", "HYPE")
DOMINANCE_ASSETS: Tuple[str, ...] = CORE_LIVE_DOMINANCE_ASSETS + EXPANSION_DOMINANCE_ASSETS

DOMINANCE_SERIES_SLUGS: Dict[str, Dict[str, str]] = {
    "BTC": {"4h": "btc-up-or-down-4h", "15m": "btc-up-or-down-15m", "5m": "btc-up-or-down-5m"},
    "ETH": {"4h": "eth-up-or-down-4h", "15m": "eth-up-or-down-15m", "5m": "eth-up-or-down-5m"},
    "SOL": {"4h": "sol-up-or-down-4h", "15m": "sol-up-or-down-15m", "5m": "sol-up-or-down-5m"},
    "XRP": {"4h": "xrp-up-or-down-4h", "15m": "xrp-up-or-down-15m", "5m": "xrp-up-or-down-5m"},
    "BNB": {"4h": "bnb-up-or-down-4h", "15m": "bnb-up-or-down-15m", "5m": "bnb-up-or-down-5m"},
    "DOGE": {"4h": "doge-up-or-down-4h", "15m": "doge-up-or-down-15m", "5m": "doge-up-or-down-5m"},
    "HYPE": {"4h": "hype-up-or-down-4h", "15m": "hype-up-or-down-15m", "5m": "hype-up-or-down-5m"},
}

METAL_DOMINANCE_ASSETS: Tuple[str, ...] = ("XAU", "XAG")
METAL_DOMINANCE_SERIES_SLUGS: Dict[str, Dict[str, str]] = {
    "XAU": {"1h": "gold-up-or-down-1h", "15m": "gold-up-or-down-15m"},
    "XAG": {"1h": "silver-up-or-down-1h", "15m": "silver-up-or-down-15m"},
}

EMPIRICAL_BOX_ASSET_CAPS_USD: Dict[str, float] = {
    "BTC": 150.0,
    "ETH": 75.0,
    "SOL": 22.0,
    "XRP": 22.0,
    "BNB": 22.0,
    "HYPE": 15.0,
    "DOGE": 15.0,
    "XAU": 22.0,
    "XAG": 22.0,
}

MIN_CORRIDOR_BPS_BY_ASSET: Dict[str, float] = {
    "BTC": 3.0,
    "ETH": 3.0,
    "SOL": 3.0,
    "XRP": 3.0,
    "BNB": 5.0,
    "DOGE": 5.0,
    "HYPE": 5.0,
    "XAU": 4.0,
    "XAG": 4.0,
}

POLYMARKET_CRYPTO_PRICE_URL = "https://polymarket.com/api/crypto/crypto-price"
GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"
HORIZON_TO_VARIANT: Dict[str, str] = {
    "4h": "fourhour",
    "1h": "hourly",
    "15m": "fifteen",
    "5m": "fiveminute",
}
HORIZON_TO_DURATION_SEC: Dict[str, float] = {
    "4h": 14400.0,
    "1h": 3600.0,
    "15m": 900.0,
    "5m": 300.0,
}


@dataclass(frozen=True)
class TwapCandleMarketSpec:
    asset: str
    horizon: str  # "15m" or "5m"
    market_id: str
    condition_id: str
    title: str
    start_iso: str
    end_iso: str
    start_ts: float
    end_ts: float
    up_token: str
    down_token: str
    fee_rate: float
    fee_exponent: float
    neg_risk: bool
    twap_lookback_sec: int
    resolution_source: str


def _parse_iso_ts(iso_str: str) -> float:
    dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def parse_twap_candle_event(event: Dict[str, Any], asset: str, horizon: str) -> Optional[TwapCandleMarketSpec]:
    """
    Parses a Polymarket Gamma `5m` or `15m` Up/Down event and enforces strict
    Chainlink 60s-TWAP oracle verification (`twapEnabled=True`, `twapLookbackSeconds=60`).
    Returns None if oracle rules do not match the canonical Chainlink 60s TWAP stream.
    """
    if horizon not in HORIZON_TO_VARIANT:
        return None
    markets = event.get("markets") or []
    if not markets or not isinstance(markets[0], dict):
        return None
    m = markets[0]
    if m.get("closed") or m.get("acceptingOrders") is False:
        return None

    start_iso = str(m.get("eventStartTime") or "").strip()
    end_iso = str(m.get("endDate") or event.get("endDate") or "").strip()
    if not start_iso or not end_iso:
        return None
    try:
        start_ts = _parse_iso_ts(start_iso)
        end_ts = _parse_iso_ts(end_iso)
    except Exception:
        return None

    expected_dur = HORIZON_TO_DURATION_SEC[horizon]
    if abs((end_ts - start_ts) - expected_dur) > 5.0:
        return None

    # Enforce strict Chainlink 60s TWAP oracle config
    cfg = m.get("cryptoMarketConfig") or {}
    res_src = str(m.get("resolutionSource") or "").strip().lower()
    desc = str(m.get("description") or "").lower()
    twap_enabled = bool(cfg.get("twapEnabled")) or ("twap-60s-streams" in res_src) or ("twap-60s-streams" in desc)
    lookback = int(cfg.get("twapLookbackSeconds") or (60 if "twap-60s" in (res_src + desc) else 0))
    if not twap_enabled or lookback != 60:
        return None

    toks = m.get("clobTokenIds")
    if isinstance(toks, str):
        try:
            toks = json.loads(toks)
        except Exception:
            toks = []
    outcomes = m.get("outcomes")
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []
    if not isinstance(toks, list) or len(toks) < 2:
        return None

    # Map "Up" and "Down" explicitly by outcome label
    up_idx, dn_idx = 0, 1
    if isinstance(outcomes, list) and len(outcomes) >= 2:
        norm_out = [str(o).strip().upper() for o in outcomes]
        if "UP" in norm_out and "DOWN" in norm_out:
            up_idx = norm_out.index("UP")
            dn_idx = norm_out.index("DOWN")

    fee_sched = m.get("feeSchedule") or {}
    fee_rate = float(fee_sched.get("rate", 0.07) if m.get("feesEnabled", True) else 0.0)
    fee_exp = float(fee_sched.get("exponent", 1.0))

    return TwapCandleMarketSpec(
        asset=asset.upper(),
        horizon=horizon,
        market_id=str(m.get("id") or ""),
        condition_id=str(m.get("conditionId") or ""),
        title=str(m.get("question") or event.get("title") or ""),
        start_iso=start_iso,
        end_iso=end_iso,
        start_ts=start_ts,
        end_ts=end_ts,
        up_token=str(toks[up_idx]),
        down_token=str(toks[dn_idx]),
        fee_rate=fee_rate,
        fee_exponent=fee_exp,
        neg_risk=bool(m.get("negRisk", False)),
        twap_lookback_sec=lookback,
        resolution_source=res_src,
    )


def parse_metal_forex_candle_event(event: Dict[str, Any], asset: str, horizon: str) -> Optional[TwapCandleMarketSpec]:
    """
    Parses a Polymarket Gamma `1h` or `15m` Up/Down event for `XAU`/`XAG` (`forexprice-streams`).
    Both `1h` and `15m` settle on the identical Chainlink point-in-time stream (`twap_lookback_sec=0`),
    enabling exact co-expiring `D1` Same-Oracle Dominance Boxes while keeping `S2` 60s-TWAP excluded.
    """
    sym = str(asset or "").strip().upper()
    if sym not in METAL_DOMINANCE_ASSETS or horizon not in ("1h", "15m"):
        return None
    markets = event.get("markets") or []
    if not markets or not isinstance(markets[0], dict):
        return None
    m = markets[0]
    if m.get("closed") or m.get("acceptingOrders") is False:
        return None
    start_iso = str(m.get("eventStartTime") or "").strip()
    end_iso = str(m.get("endDate") or event.get("endDate") or "").strip()
    if not start_iso or not end_iso:
        return None
    try:
        start_ts = _parse_iso_ts(start_iso)
        end_ts = _parse_iso_ts(end_iso)
    except Exception:
        return None
    if abs((end_ts - start_ts) - HORIZON_TO_DURATION_SEC[horizon]) > 5.0:
        return None
    res_src = str(m.get("resolutionSource") or "").strip().lower()
    desc = str(m.get("description") or "").lower()
    expected_stream = f"{sym.lower()}-usd-forexprice-streams"
    if expected_stream not in res_src and expected_stream not in desc:
        return None
    toks = m.get("clobTokenIds")
    if isinstance(toks, str):
        try:
            toks = json.loads(toks)
        except Exception:
            toks = []
    outcomes = m.get("outcomes")
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []
    if not isinstance(toks, list) or len(toks) < 2:
        return None
    up_idx, dn_idx = 0, 1
    if isinstance(outcomes, list) and len(outcomes) >= 2:
        norm_out = [str(o).strip().upper() for o in outcomes]
        if "UP" in norm_out and "DOWN" in norm_out:
            up_idx = norm_out.index("UP")
            dn_idx = norm_out.index("DOWN")
    fee_sched = m.get("feeSchedule") or {}
    fee_rate = float(fee_sched.get("rate", 0.07) if m.get("feesEnabled", True) else 0.0)
    fee_exp = float(fee_sched.get("exponent", 1.0))
    return TwapCandleMarketSpec(
        asset=sym,
        horizon=horizon,
        market_id=str(m.get("id") or ""),
        condition_id=str(m.get("conditionId") or ""),
        title=str(m.get("question") or event.get("title") or ""),
        start_iso=start_iso,
        end_iso=end_iso,
        start_ts=start_ts,
        end_ts=end_ts,
        up_token=str(toks[up_idx]),
        down_token=str(toks[dn_idx]),
        fee_rate=fee_rate,
        fee_exponent=fee_exp,
        neg_risk=bool(m.get("negRisk", False)),
        twap_lookback_sec=0,
        resolution_source=res_src or f"https://data.chain.link/streams/{expected_stream}",
    )


def verify_same_oracle_pair(m_long: TwapCandleMarketSpec, m_short: TwapCandleMarketSpec) -> bool:
    """
    Verifies two distinct Chainlink candle markets belong to the same asset, share the exact same
    terminal settlement timestamp (`end_ts` within 2s), and settle on the identical Chainlink stream
    (`twapLookbackSeconds == 60` for crypto, or `*-usd-forexprice-streams` for `XAU`/`XAG` `1h` vs `15m`).
    """
    if m_long.asset != m_short.asset:
        return False
    if m_long.horizon not in HORIZON_TO_VARIANT or m_short.horizon not in HORIZON_TO_VARIANT:
        return False
    if m_long.horizon == m_short.horizon:
        return False
    if HORIZON_TO_DURATION_SEC[m_long.horizon] <= HORIZON_TO_DURATION_SEC[m_short.horizon]:
        return False
    if abs(m_long.end_ts - m_short.end_ts) > 2.0:
        return False
    s_l = str(m_long.resolution_source or "").strip().lower()
    s_s = str(m_short.resolution_source or "").strip().lower()
    if not s_l or not s_s or s_l != s_s:
        return False
    if m_long.asset in METAL_DOMINANCE_ASSETS:
        return (
            m_long.twap_lookback_sec == 0
            and m_short.twap_lookback_sec == 0
            and f"{m_long.asset.lower()}-usd-forexprice-streams" in s_l
        )
    if m_long.twap_lookback_sec != 60 or m_short.twap_lookback_sec != 60:
        return False
    return True


def build_prev_15m_gamma_event_url(spec: TwapCandleMarketSpec) -> str:
    """Returns the Gamma event URL for the immediately preceding 15m candle (`start_ts - 900`)."""
    prev_15m_start = int(round(spec.start_ts)) - 900
    return f"{GAMMA_EVENTS_URL}?slug={spec.asset.lower()}-updown-15m-{prev_15m_start}"


def build_prev_5m_gamma_event_url(spec: TwapCandleMarketSpec) -> str:
    """
    Returns the Gamma event URL for the immediately preceding 5m candle (`start_ts - 300`).
    Once finalized (`closed == True`), its `eventMetadata.finalPrice` equals `spec`'s exact
    60s-TWAP `eventMetadata.priceToBeat` across `5m`, `15m`, and `4h` horizons.
    """
    prev_5m_start = int(round(spec.start_ts)) - 300
    return f"{GAMMA_EVENTS_URL}?slug={spec.asset.lower()}-updown-5m-{prev_5m_start}"


def build_own_gamma_event_url(asset: str, horizon: str, start_ts_or_iso: Any) -> str:
    start_ts = _parse_iso_ts(start_ts_or_iso) if isinstance(start_ts_or_iso, str) else float(start_ts_or_iso)
    return f"{GAMMA_EVENTS_URL}?slug={str(asset).lower()}-updown-{str(horizon).lower()}-{int(round(start_ts))}"


def build_crypto_price_query_url(spec: TwapCandleMarketSpec) -> str:
    """
    Builds Polymarket's exact 60s-TWAP `crypto-price` query URL (`twapEnabled=true&twapLookbackSeconds=60`).
    Matches Polymarket's frontend query key `["crypto-prices", ..., true, 60]` and Gamma's
    `eventMetadata.priceToBeat` / `finalPrice` to all 15 significant digits with zero lag (`t = +1s`).
    """
    if int(spec.twap_lookback_sec) != 60:
        raise ValueError(f"60s Chainlink TWAP required, got twap_lookback_sec={spec.twap_lookback_sec}")
    variant = HORIZON_TO_VARIANT[spec.horizon]
    return (
        f"{POLYMARKET_CRYPTO_PRICE_URL}?symbol={spec.asset}"
        f"&eventStartTime={spec.start_iso}&variant={variant}&endDate={spec.end_iso}"
        f"&twapEnabled=true&twapLookbackSeconds=60"
    )


def _is_verified_twap60_url(request_url: Optional[str]) -> bool:
    u = str(request_url or "")
    return ("twapEnabled=true" in u) and ("twapLookbackSeconds=60" in u)


def _extract_closed_gamma_meta_field(payload: Any, field: str, request_url: Optional[str] = None) -> Optional[float]:
    ev = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(ev, dict) or ev.get("closed") is not True:
        return None
    if request_url and "slug=" in str(request_url):
        expected_slug = str(request_url).split("slug=", 1)[1].split("&", 1)[0]
        if str(ev.get("slug") or "") != expected_slug:
            return None
    meta = ev.get("eventMetadata")
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            return None
    if not isinstance(meta, dict):
        return None
    raw_val = meta.get(field)
    if raw_val is None:
        return None
    try:
        val = float(raw_val)
    except (TypeError, ValueError):
        return None
    return val if (math.isfinite(val) and val > 0.0) else None


def parse_authoritative_open_price(payload: Any, *, request_url: Optional[str] = None) -> Optional[float]:
    """
    Extracts the authoritative Chainlink 60s-TWAP opening strike (`priceToBeat`):
      1. Closed preceding-5m Gamma event (`closed is True` -> `eventMetadata.finalPrice`), OR
      2. Polymarket `crypto-price` ONLY when `request_url` explicitly carries
         `twapEnabled=true&twapLookbackSeconds=60` AND `cached is True` (or `completed is True`).
    Strictly rejects legacy un-TWAP'd `crypto-price` spot responses (`request_url` missing TWAP flags).
    """
    g_val = _extract_closed_gamma_meta_field(payload, "finalPrice", request_url)
    if g_val is not None:
        return g_val
    if not isinstance(payload, dict) or not _is_verified_twap60_url(request_url):
        return None
    if payload.get("cached") is not True and payload.get("completed") is not True:
        return None
    raw_open = payload.get("openPrice")
    if raw_open is None:
        return None
    try:
        val = float(raw_open)
    except (TypeError, ValueError):
        return None
    return val if (math.isfinite(val) and val > 0.0) else None


def parse_authoritative_close_price(payload: Any, *, request_url: Optional[str] = None) -> Optional[float]:
    """
    Extracts finalized Chainlink 60s-TWAP `finalPrice` / `closePrice` from a closed Gamma
    event (`eventMetadata.finalPrice`) or a completed `twapEnabled=true&twapLookbackSeconds=60` response.
    """
    g_val = _extract_closed_gamma_meta_field(payload, "finalPrice", request_url)
    if g_val is not None:
        return g_val
    if not isinstance(payload, dict) or payload.get("completed") is not True or not _is_verified_twap60_url(request_url):
        return None
    raw_close = payload.get("closePrice")
    if raw_close is None:
        return None
    try:
        val = float(raw_close)
    except (TypeError, ValueError):
        return None
    return val if (math.isfinite(val) and val > 0.0) else None


def parse_closed_gamma_event_settlement(payload: Any, side: str, request_url: Optional[str] = None) -> Optional[float]:
    """
    Evaluates actual binary leg payout (`1.0` or `0.0`) directly from a closed Gamma event's
    authoritative `(priceToBeat, finalPrice)` pair without trusting cached entry strikes.
    """
    k_beat = _extract_closed_gamma_meta_field(payload, "priceToBeat", request_url)
    s_fin = _extract_closed_gamma_meta_field(payload, "finalPrice", request_url)
    if k_beat is None or s_fin is None:
        return None
    up_won = s_fin >= k_beat
    won = up_won if str(side).strip().upper() == "UP" else (not up_won)
    return 1.0 if won else 0.0


def determine_dominance_legs(
    m15: TwapCandleMarketSpec,
    k_15m: float,
    m5: TwapCandleMarketSpec,
    k_5m: float,
    min_corridor_bps: float = 2.5,
) -> Optional[Dict[str, Any]]:
    """
    Given authoritative Chainlink opening strikes `k_15m` (longer horizon: `4h` or `15m`) and
    `k_5m` (shorter horizon: `15m` or `5m`), returns the exact riskless dominance leg pairing
    (`UP` at `K_low` + `DOWN` at `K_high`) plus each leg's `opp_token_id` complement.
    Rejects pairs with < `min_corridor_bps` strike separation to eliminate any tie ambiguity.
    """
    if not verify_same_oracle_pair(m15, m5):
        return None
    if not (math.isfinite(k_15m) and k_15m > 0.0 and math.isfinite(k_5m) and k_5m > 0.0):
        return None

    k_low = min(k_15m, k_5m)
    k_high = max(k_15m, k_5m)
    corridor_bps = ((k_high - k_low) / k_low) * 10000.0
    if corridor_bps < min_corridor_bps:
        return None

    h_long_u = m15.horizon.upper()
    h_short_u = m5.horizon.upper()

    if k_15m < k_5m:
        return {
            "regime": f"{h_long_u}_UP_PLUS_{h_short_u}_DOWN",
            "k_low": k_15m,
            "k_high": k_5m,
            "corridor_bps": round(corridor_bps, 3),
            "leg_a": {
                "horizon": m15.horizon,
                "side": "UP",
                "label": f"{h_long_u}_UP",
                "market_id": m15.market_id,
                "condition_id": m15.condition_id,
                "token_id": m15.up_token,
                "opp_token_id": m15.down_token,
                "strike": k_15m,
                "fee_rate": m15.fee_rate,
                "fee_exponent": m15.fee_exponent,
                "neg_risk": m15.neg_risk,
            },
            "leg_b": {
                "horizon": m5.horizon,
                "side": "DOWN",
                "label": f"{h_short_u}_DOWN",
                "market_id": m5.market_id,
                "condition_id": m5.condition_id,
                "token_id": m5.down_token,
                "opp_token_id": m5.up_token,
                "strike": k_5m,
                "fee_rate": m5.fee_rate,
                "fee_exponent": m5.fee_exponent,
                "neg_risk": m5.neg_risk,
            },
        }
    else:
        return {
            "regime": f"{h_short_u}_UP_PLUS_{h_long_u}_DOWN",
            "k_low": k_5m,
            "k_high": k_15m,
            "corridor_bps": round(corridor_bps, 3),
            "leg_a": {
                "horizon": m5.horizon,
                "side": "UP",
                "label": f"{h_short_u}_UP",
                "market_id": m5.market_id,
                "condition_id": m5.condition_id,
                "token_id": m5.up_token,
                "opp_token_id": m5.down_token,
                "strike": k_5m,
                "fee_rate": m5.fee_rate,
                "fee_exponent": m5.fee_exponent,
                "neg_risk": m5.neg_risk,
            },
            "leg_b": {
                "horizon": m15.horizon,
                "side": "DOWN",
                "label": f"{h_long_u}_DOWN",
                "market_id": m15.market_id,
                "condition_id": m15.condition_id,
                "token_id": m15.down_token,
                "opp_token_id": m15.up_token,
                "strike": k_15m,
                "fee_rate": m15.fee_rate,
                "fee_exponent": m15.fee_exponent,
                "neg_risk": m15.neg_risk,
            },
        }


def _sorted_asks(asks_raw: List[Dict[str, Any]], max_slip_cents: float) -> Tuple[List[Tuple[float, float]], float, float]:
    asks = sorted(
        [
            (float(a["price"]), float(a["size"]))
            for a in (asks_raw or [])
            if float(a.get("price", 0)) > 0.0 and float(a.get("size", 0)) > 0.0
        ],
        key=lambda x: x[0],
    )
    if not asks:
        return [], 1.0, 0.0
    best_ask = asks[0][0]
    capped = [(px, sz) for px, sz in asks if px <= best_ask + max_slip_cents + 1e-9 and px < 0.99]
    avail_shares = sum(sz for _, sz in capped)
    return capped, best_ask, avail_shares


def _buy_share_haircut(px: float, fee_rate: float, fee_exponent: float = 1.0) -> float:
    """
    Polymarket CLOB V2 deducts BUY taker fees in conditional shares:
    buying 1 gross share at price `p` delivers `1 - h(p)` net shares where
    `h(p) = (r * (p * (1 - p))**e) / p`.
    """
    p = float(px)
    r = float(fee_rate or 0.0)
    if r <= 0.0 or p <= 0.0 or p >= 1.0:
        return 0.0
    fee_usdc_eq = r * ((p * (1.0 - p)) ** float(fee_exponent or 1.0))
    return min(0.50, max(0.0, fee_usdc_eq / p))


def _net_unit_cost_buy(px: float, fee_rate: float, fee_exponent: float = 1.0) -> float:
    """Exact USDC cost required to acquire 1.0000 net share on-chain after V2 share-deducted BUY fees."""
    p = float(px)
    h = _buy_share_haircut(p, fee_rate, fee_exponent)
    return p / (1.0 - h) if h > 0.0 else p


def _walk_exact_shares(
    asks_capped: List[Tuple[float, float]],
    shares_qty: int,
    fee_rate: float,
    fee_exponent: float = 1.0,
) -> Optional[Dict[str, Any]]:
    if shares_qty <= 0 or not asks_capped:
        return None
    rem = float(shares_qty)
    spent = 0.0
    worst_px = asks_capped[0][0]
    levels = 0
    for px, sz in asks_capped:
        take_sh = min(rem, sz)
        if take_sh <= 0:
            continue
        spent += take_sh * px
        worst_px = px
        levels += 1
        rem -= take_sh
        if rem <= 1e-8:
            break
    if rem > 1e-5:
        return None
    vwap = spent / float(shares_qty)
    h_vwap = _buy_share_haircut(vwap, fee_rate, fee_exponent)
    eff_px = vwap / (1.0 - h_vwap) if h_vwap > 0.0 else vwap
    fee_ps = eff_px - vwap
    fee_usd = float(shares_qty) * fee_ps
    net_shares_delivered = float(shares_qty) * (1.0 - h_vwap)
    return {
        "shares": int(shares_qty),
        "net_shares": round(net_shares_delivered, 4),
        "share_haircut": round(h_vwap, 6),
        "best_ask": round(asks_capped[0][0], 4),
        "vwap": round(vwap, 5),
        "worst_px": round(worst_px, 4),
        "spent_usd": round(spent, 4),
        "fee_usd": round(fee_usd, 4),
        "eff_px": round(eff_px, 5),
        "levels": levels,
    }


def walk_equal_shares_dominance_box(
    asks_a_raw: List[Dict[str, Any]],
    asks_b_raw: List[Dict[str, Any]],
    target_budget_usd: float,
    fee_rate_a: float = 0.07,
    fee_rate_b: float = 0.07,
    fee_exponent_a: float = 1.0,
    fee_exponent_b: float = 1.0,
    max_box_cost_net: float = 0.995,
    max_slip_cents: float = 0.025,
    min_shares: int = 5,
    min_box_notional_usd: float = 4.85,
    min_box_cost_net: float = 0.900,
) -> Dict[str, Any]:
    """
    Walks BOTH L2 ask books for an IDENTICAL whole-integer share count `Q` (`Q_A == Q_B == Q`),
    guaranteeing zero unhedged directional delta outside `[K_low, K_high)`.
    Caps `Q` to available visible ask depth within `max_slip_cents` on the thinner leg,
    enforces all-in net box cost in `[min_box_cost_net, max_box_cost_net]` (vetoing inverted
    anti-boxes `< 0.900`), and includes both V2 taker fees.
    """
    capped_a, best_a, avail_a = _sorted_asks(asks_a_raw, max_slip_cents)
    capped_b, best_b, avail_b = _sorted_asks(asks_b_raw, max_slip_cents)
    if not capped_a or not capped_b:
        return {"filled": False, "reason": "EMPTY_BOOK", "best_sum": round(best_a + best_b, 4)}

    min_possible_unit_cost = _net_unit_cost_buy(best_a, fee_rate_a, fee_exponent_a) + _net_unit_cost_buy(best_b, fee_rate_b, fee_exponent_b)
    if min_possible_unit_cost < min_box_cost_net - 0.025 or (best_a + best_b) < 0.855:
        return {
            "filled": False,
            "reason": "SUSPECT_INVERTED_ANTI_BOX",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
        }
    if min_possible_unit_cost > max_box_cost_net + 0.015:
        return {
            "filled": False,
            "reason": "BOX_TOO_EXPENSIVE_L1",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": int(math.floor(min(avail_a, avail_b))),
        }

    max_avail_pairs = int(math.floor(min(avail_a, avail_b)))
    if max_avail_pairs < max(5, min_shares):
        return {
            "filled": False,
            "reason": "INSUFFICIENT_PAIR_SHARES",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": max_avail_pairs,
        }

    desired_pairs = int(math.floor(float(target_budget_usd) / max(0.10, min_possible_unit_cost)))
    q_pairs = min(desired_pairs, max_avail_pairs)
    if q_pairs < max(5, min_shares):
        return {
            "filled": False,
            "reason": "BUDGET_BELOW_MIN_SHARES",
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": max_avail_pairs,
        }

    w_a = _walk_exact_shares(capped_a, q_pairs, fee_rate_a, fee_exponent_a)
    w_b = _walk_exact_shares(capped_b, q_pairs, fee_rate_b, fee_exponent_b)
    if w_a is None or w_b is None:
        return {"filled": False, "reason": "WALK_FAILED", "avail_pair_shares": max_avail_pairs}

    spent_total = w_a["spent_usd"] + w_b["spent_usd"]
    fee_total = w_a["fee_usd"] + w_b["fee_usd"]
    all_in_total = spent_total + fee_total
    box_cost_net = all_in_total / float(q_pairs)

    # If budget slightly exceeded due to multi-level walk, trim Q by 1-2 shares to fit target_budget_usd
    if all_in_total > target_budget_usd * 1.02:
        q_trim = int(math.floor(float(target_budget_usd) / box_cost_net))
        if q_trim < max(5, min_shares):
            return {"filled": False, "reason": "TRIMMED_BELOW_MIN_SHARES", "box_cost_net": round(box_cost_net, 5)}
        q_pairs = q_trim
        w_a = _walk_exact_shares(capped_a, q_pairs, fee_rate_a, fee_exponent_a)
        w_b = _walk_exact_shares(capped_b, q_pairs, fee_rate_b, fee_exponent_b)
        if w_a is None or w_b is None:
            return {"filled": False, "reason": "WALK_TRIM_FAILED"}
        spent_total = w_a["spent_usd"] + w_b["spent_usd"]
        fee_total = w_a["fee_usd"] + w_b["fee_usd"]
        all_in_total = spent_total + fee_total
        box_cost_net = all_in_total / float(q_pairs)

    # Trim multi-level spills when worst_px_a + worst_px_b + fees exceeds max_box_cost_net
    # so FOK limit orders never self-veto on WORST_LIMIT_BOX_COST_EXCEEDS_CAP when L1 size >= min_shares.
    def _worst_limit_net(wa_d: Dict[str, Any], wb_d: Dict[str, Any]) -> float:
        pa, pb = float(wa_d["worst_px"]), float(wb_d["worst_px"])
        return round(_net_unit_cost_buy(pa, fee_rate_a, fee_exponent_a) + _net_unit_cost_buy(pb, fee_rate_b, fee_exponent_b), 6)

    if _worst_limit_net(w_a, w_b) > max_box_cost_net + 1e-6:
        min_q = max(5, int(min_shares))
        bp_set = set()
        for lvl_list in (capped_a, capped_b):
            cum_sz = 0.0
            for _, sz_lvl in lvl_list:
                cum_sz += sz_lvl
                q_bp = int(math.floor(cum_sz + 1e-9))
                if min_q <= q_bp < q_pairs:
                    bp_set.add(q_bp)
        trimmed_ok = False
        for q_cand in sorted(bp_set, reverse=True):
            wa_c = _walk_exact_shares(capped_a, q_cand, fee_rate_a, fee_exponent_a)
            wb_c = _walk_exact_shares(capped_b, q_cand, fee_rate_b, fee_exponent_b)
            if wa_c is None or wb_c is None:
                continue
            sp_c = wa_c["spent_usd"] + wb_c["spent_usd"]
            if sp_c < min_box_notional_usd:
                continue
            if _worst_limit_net(wa_c, wb_c) <= max_box_cost_net + 1e-6:
                q_pairs = q_cand
                w_a, w_b = wa_c, wb_c
                spent_total = sp_c
                fee_total = w_a["fee_usd"] + w_b["fee_usd"]
                all_in_total = spent_total + fee_total
                box_cost_net = all_in_total / float(q_pairs)
                trimmed_ok = True
                break
        if not trimmed_ok:
            return {
                "filled": False,
                "reason": "WORST_LIMIT_COST_ABOVE_CAP",
                "best_a": round(best_a, 4),
                "best_b": round(best_b, 4),
                "box_cost_net": round(box_cost_net, 5),
                "worst_limit_cost_net": _worst_limit_net(w_a, w_b),
                "l1_box_cost_net": round(min_possible_unit_cost, 5),
                "avail_pair_shares": max_avail_pairs,
            }

    # Polymarket rejects marketable orders below $1 notional: compute exact gross leg sizes
    # to deliver identical post-fee net shares on both legs (`Q` whole net pairs whenever depth
    # & worst_px allow gross-up; otherwise haircut-matched `<= q_pairs` when capped by L1 depth).
    h_a_w = float(w_a.get("share_haircut") or 0.0)
    h_b_w = float(w_b.get("share_haircut") or 0.0)
    h_max_w = max(h_a_w, h_b_w)
    cand_gross_a = math.ceil((float(q_pairs) / max(1e-6, 1.0 - h_a_w)) * 100.0 - 1e-9) / 100.0
    cand_gross_b = math.ceil((float(q_pairs) / max(1e-6, 1.0 - h_b_w)) * 100.0 - 1e-9) / 100.0

    def _fits_at_worst_px(asks_cap: List[Tuple[float, float]], req_sh: float, lim_px: float) -> Tuple[bool, float]:
        rem_g = req_sh
        sp_g = 0.0
        for px_l, sz_l in asks_cap:
            if px_l > lim_px + 1e-9:
                break
            tk_g = min(rem_g, sz_l)
            if tk_g > 0.0:
                sp_g += tk_g * px_l
                rem_g -= tk_g
                if rem_g <= 1e-8:
                    return True, sp_g
        return False, sp_g

    ok_ga, sp_ga = _fits_at_worst_px(capped_a, cand_gross_a, float(w_a["worst_px"]))
    ok_gb, sp_gb = _fits_at_worst_px(capped_b, cand_gross_b, float(w_b["worst_px"]))
    if ok_ga and ok_gb and (sp_ga + sp_gb) <= float(target_budget_usd) * 1.02 + 1e-6:
        net_paired_sh = float(q_pairs)
        gross_sh_a = cand_gross_a
        gross_sh_b = cand_gross_b
    else:
        net_paired_sh = math.floor(float(q_pairs) * (1.0 - h_max_w) * 100.0 + 1e-9) / 100.0
        gross_sh_a = min(float(q_pairs), math.ceil((net_paired_sh / max(1e-6, 1.0 - h_a_w)) * 100.0 - 1e-9) / 100.0)
        gross_sh_b = min(float(q_pairs), math.ceil((net_paired_sh / max(1e-6, 1.0 - h_b_w)) * 100.0 - 1e-9) / 100.0)
    min_leg_px = min(best_a, best_b)
    q_floor = int(math.ceil(1.0 / max(min_leg_px, 0.01) - 1e-9))
    if q_pairs < q_floor or (gross_sh_a * best_a) < 1.0 - 1e-6 or (gross_sh_b * best_b) < 1.0 - 1e-6:
        return {
            "filled": False,
            "reason": "LEG_BELOW_1USD_MIN",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": max_avail_pairs,
        }

    if spent_total < min_box_notional_usd:
        return {
            "filled": False,
            "reason": "BELOW_MIN_BOX_NOTIONAL",
            "box_cost_net": round(box_cost_net, 5),
            "spent_usd": round(spent_total, 2),
        }

    if box_cost_net < min_box_cost_net:
        return {
            "filled": False,
            "reason": "SUSPECT_INVERTED_ANTI_BOX",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "box_cost_net": round(box_cost_net, 5),
        }

    if box_cost_net > max_box_cost_net:
        return {
            "filled": False,
            "reason": "BOX_COST_ABOVE_CAP",
            "best_a": round(best_a, 4),
            "best_b": round(best_b, 4),
            "box_cost_net": round(box_cost_net, 5),
            "l1_box_cost_net": round(min_possible_unit_cost, 5),
            "avail_pair_shares": max_avail_pairs,
        }

    riskless_floor = 1.0 - box_cost_net
    l1_pair_usd = round(min(avail_a, avail_b) * (best_a + best_b), 2)
    return {
        "filled": True,
        "shares": int(q_pairs),
        "net_paired_shares": round(net_paired_sh, 4),
        "leg_a_gross_shares": round(gross_sh_a, 2),
        "leg_b_gross_shares": round(gross_sh_b, 2),
        "best_ask": round(best_a + best_b, 4),
        "vwap": round(spent_total / float(q_pairs), 5),
        "eff_px": round(box_cost_net, 5),
        "box_cost_net": round(box_cost_net, 5),
        "riskless_floor_per_pair": round(riskless_floor, 5),
        "guaranteed_min_profit_usd": round(net_paired_sh * riskless_floor, 4),
        "corridor_bonus_profit_usd": round(net_paired_sh * (2.0 - box_cost_net), 4),
        "slip_cents": round(((spent_total / float(q_pairs)) - (best_a + best_b)) * 100.0, 2),
        "spent_usd": round(spent_total, 4),
        "fee_usd": round(fee_total, 4),
        "fill_ratio": round(min(1.0, all_in_total / max(1e-6, float(target_budget_usd))), 4),
        "l1_usd": l1_pair_usd,
        "avail_pair_shares": max_avail_pairs,
        "avail_a_shares": round(avail_a, 2),
        "avail_b_shares": round(avail_b, 2),
        "leg_a_walk": w_a,
        "leg_b_walk": w_b,
        "levels": max(w_a["levels"], w_b["levels"]),
    }


def compute_dominance_box_payout_from_close(close_px: float, k_low: float, k_high: float) -> float:
    """
    Exact terminal payout per 1-share dominance pair (`UP(k_low) + DOWN(k_high)`)
    given finalized Chainlink 60s-TWAP `closePrice`. Always returns 1.0 or 2.0.
    """
    leg_a_pay = 1.0 if close_px >= k_low else 0.0
    leg_b_pay = 1.0 if close_px < k_high else 0.0
    return leg_a_pay + leg_b_pay


def walk_equal_shares_multi_leg_box(
    legs_spec: List[Dict[str, Any]],
    target_budget_usd: float,
    guaranteed_payout_per_bundle: float = 1.0,
    max_bundle_cost_net: float = 0.992,
    max_slip_cents: float = 0.025,
    min_shares: int = 5,
    min_box_notional_usd: float = 4.85,
) -> Dict[str, Any]:
    """
    Walks N L2 ask books (`N >= 2`, e.g., 2-leg tail equivalence or 3-leg Multi-Strike vs
    NegRisk Bracket partition/complement) for an IDENTICAL integer share count `Q` across all legs.
    Each item in `legs_spec` must contain `{"asks": [...], "fee_rate": float, "fee_exponent": float}`.
    Normalizes `eff_px` per `$1.00` of guaranteed payout so `payout_per_share = 1.0` at settlement
    for `$1.00`-floor bundles (and `2.0` for `$2.00`-floor complement bundles).
    """
    if len(legs_spec) < 2 or guaranteed_payout_per_bundle <= 0.0:
        return {"filled": False, "reason": "INVALID_BUNDLE_SPEC"}

    capped_list: List[List[Tuple[float, float]]] = []
    best_asks: List[float] = []
    avails: List[float] = []
    min_unit_cost = 0.0

    for lg in legs_spec:
        capped, best_a, avail_a = _sorted_asks(lg.get("asks") or [], max_slip_cents)
        if not capped:
            return {"filled": False, "reason": "EMPTY_LEG_BOOK"}
        fr = float(lg.get("fee_rate", 0.07))
        fe = float(lg.get("fee_exponent", 1.0))
        capped_list.append(capped)
        best_asks.append(best_a)
        avails.append(avail_a)
        min_unit_cost += _net_unit_cost_buy(best_a, fr, fe)

    if min_unit_cost > max_bundle_cost_net + 0.015:
        return {
            "filled": False,
            "reason": "BUNDLE_TOO_EXPENSIVE_L1",
            "l1_bundle_cost_net": round(min_unit_cost, 5),
        }

    max_avail_sh = int(math.floor(min(avails)))
    if max_avail_sh < max(5, min_shares):
        return {
            "filled": False,
            "reason": "INSUFFICIENT_BUNDLE_SHARES",
            "avail_bundle_shares": max_avail_sh,
        }

    desired_sh = int(math.floor(float(target_budget_usd) / max(0.10, min_unit_cost)))
    q_sh = min(desired_sh, max_avail_sh)
    if q_sh < max(5, min_shares):
        return {"filled": False, "reason": "BUDGET_BELOW_MIN_SHARES"}

    walks: List[Dict[str, Any]] = []
    for lg, capped in zip(legs_spec, capped_list):
        w_i = _walk_exact_shares(capped, q_sh, float(lg.get("fee_rate", 0.07)), float(lg.get("fee_exponent", 1.0)))
        if w_i is None:
            return {"filled": False, "reason": "LEG_WALK_FAILED"}
        walks.append(w_i)

    spent_total = sum(w["spent_usd"] for w in walks)
    fee_total = sum(w["fee_usd"] for w in walks)
    all_in_total = spent_total + fee_total
    bundle_cost_net = all_in_total / float(q_sh)

    if all_in_total > target_budget_usd * 1.02:
        q_trim = int(math.floor(float(target_budget_usd) / bundle_cost_net))
        if q_trim < max(5, min_shares):
            return {"filled": False, "reason": "TRIMMED_BELOW_MIN_SHARES"}
        q_sh = q_trim
        walks = []
        for lg, capped in zip(legs_spec, capped_list):
            w_i = _walk_exact_shares(capped, q_sh, float(lg.get("fee_rate", 0.07)), float(lg.get("fee_exponent", 1.0)))
            if w_i is None:
                return {"filled": False, "reason": "LEG_TRIM_WALK_FAILED"}
            walks.append(w_i)
        spent_total = sum(w["spent_usd"] for w in walks)
        fee_total = sum(w["fee_usd"] for w in walks)
        all_in_total = spent_total + fee_total
        bundle_cost_net = all_in_total / float(q_sh)

    # Polymarket $1 min marketable order: every leg must clear $1 at the final Q (else one-legged bundle).
    min_leg_px = min(best_asks)
    q_floor = int(math.ceil(1.0 / max(min_leg_px, 0.01) - 1e-9))
    if q_sh < q_floor:
        return {
            "filled": False,
            "reason": "LEG_BELOW_1USD_MIN",
            "avail_bundle_shares": max_avail_sh,
        }

    if spent_total < min_box_notional_usd:
        return {"filled": False, "reason": "BELOW_MIN_BOX_NOTIONAL", "spent_usd": round(spent_total, 2)}
    if bundle_cost_net > max_bundle_cost_net:
        return {
            "filled": False,
            "reason": "BUNDLE_COST_ABOVE_CAP",
            "bundle_cost_net": round(bundle_cost_net, 5),
            "l1_bundle_cost_net": round(min_unit_cost, 5),
        }

    floor_per_bundle = guaranteed_payout_per_bundle - bundle_cost_net
    l1_bundle_usd = round(min(avails) * sum(best_asks), 2)
    return {
        "filled": True,
        "shares": int(q_sh),
        "best_ask": round(sum(best_asks), 4),
        "vwap": round(spent_total / float(q_sh), 5),
        "eff_px": round(bundle_cost_net, 5),
        "box_cost_net": round(bundle_cost_net, 5),
        "guaranteed_payout_per_bundle": round(guaranteed_payout_per_bundle, 4),
        "riskless_floor_per_pair": round(floor_per_bundle, 5),
        "guaranteed_min_profit_usd": round(float(q_sh) * floor_per_bundle, 4),
        "spent_usd": round(spent_total, 4),
        "fee_usd": round(fee_total, 4),
        "l1_usd": l1_bundle_usd,
        "avail_bundle_shares": max_avail_sh,
        "leg_walks": walks,
    }
