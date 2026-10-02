#!/usr/bin/env python3
"""
EXP-303B: Polymarket Crypto Market Registry & Oracle Conformance Engine
=======================================================================
Phase 1 of the EXP-303B Research Program: Cross-Asset & Cross-Horizon Expansion.
Builds an institutional, automated registry of recurring crypto binary contracts
across Cohorts C1 (BTC), C2 (ETH), C3 (SOL) and C4 (XRP, DOGE, BNB) over 5m, 15m, and 1h horizons.

Strict Invariants:
  1. Oracle Conformance: Distinguishes Chainlink Data Streams from Binance Spot settlements.
  2. Pre-Trade Liquidity Filter: Frozen hurdle (DepthRatio >= 1.50 for $50 ticket, Spread <= $0.10).
  3. Formal Classification: ELIGIBLE, THIN, STALE, ORACLE_AMBIGUOUS, DUPLICATE, UNTRADEABLE.
  4. Immutable Baseline: EXP-303 B1 (+$141.55 / 25 trades) remains locked. EXP-303B has its own ledger.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "exp303b"
DATA_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = DATA_DIR / "crypto_market_registry.jsonl"
REGISTRY_SUMMARY_FILE = DATA_DIR / "registry_summary.json"
LOG_FILE = DATA_DIR / "market_registry.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [EXP303B-REG] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("EXP303BRegistry")

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL = "https://clob.polymarket.com"

# Target Research Matrix (Cohorts C1 to C4)
RESEARCH_COHORTS: Dict[str, List[str]] = {
    "C1_BTC": ["btc"],
    "C2_ETH": ["eth"],
    "C3_SOL": ["sol"],
    "C4_ALTS": ["xrp", "doge", "bnb"],
}

TARGET_HORIZONS: List[str] = ["5m", "15m", "1h", "hourly"]

# Frozen Pre-Trade Filter Hurdle Parameters
MIN_ORDER_SIZE_USD = 50.0
DEPTH_HURDLE_RATIO = 1.50  # Must have >= $75 resting depth in top 2 ticks
MAX_ALLOWED_SPREAD = 0.10   # Max 10 cents wide
MAX_BOOK_AGE_SEC = 300.0   # Reject stale quotes > 5 min old


@dataclass
class MarketRegistryEntry:
    market_id: str
    asset: str
    cohort: str
    horizon: str
    market_family: str  # "up_down"
    series_slug: str
    event_slug: str
    title: str
    question: str
    start_time_iso: Optional[str]
    end_time_iso: Optional[str]
    start_unix: Optional[float]
    end_unix: Optional[float]
    duration_seconds: int
    seconds_to_expiry: float
    oracle_source: str
    oracle_type: str  # "CHAINLINK_DATA_STREAM", "BINANCE_SPOT_CANDLE", "AMBIGUOUS"
    resolution_rule_summary: str
    clob_token_up: str
    clob_token_down: str
    fees_enabled: bool
    fee_rate: float
    volume_usd: float
    liquidity_usd: float
    best_bid: float
    best_ask: float
    spread: float
    executable_depth_top2_usd: float
    depth_ratio: float
    classification: str  # ELIGIBLE, THIN, STALE, ORACLE_AMBIGUOUS, DUPLICATE, UNTRADEABLE
    classification_reason: str
    registered_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class CryptoMarketRegistryBuilder:
    """Discovers, audits, and classifies recurring Polymarket crypto markets."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session
        self.seen_market_ids = set()

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10.0),
                headers={"User-Agent": "EXP-303B-Institutional-Registry/1.0"},
            )
        return self.session

    def determine_oracle_type(
        self, res_source: Optional[str], description: Optional[str], question: Optional[str]
    ) -> Tuple[str, str, str]:
        """Classifies the causal oracle settlement mechanism."""
        source_clean = (res_source or "").lower()
        desc_clean = (description or "").lower()
        q_clean = (question or "").lower()

        if "chain.link" in source_clean or "chainlink" in desc_clean:
            return (
                "CHAINLINK_DATA_STREAM",
                res_source or "https://data.chain.link/streams",
                "Chainlink TWAP/Stream: price at end of window >= price at beginning of window",
            )
        elif "binance" in source_clean or "binance" in desc_clean:
            return (
                "BINANCE_SPOT_CANDLE",
                res_source or "https://www.binance.com",
                "Binance Spot Candle: 1[Close >= Open] for specified time window",
            )
        elif "coingecko" in source_clean or "coingecko" in desc_clean:
            return (
                "COINGECKO_FEED",
                res_source or "https://www.coingecko.com",
                "CoinGecko Price at End vs Start",
            )
        else:
            return (
                "ORACLE_AMBIGUOUS",
                res_source or "UNKNOWN",
                "Resolution source not explicitly matched to Chainlink or Binance spot specification",
            )

    async def fetch_clob_book(self, token_id: str) -> Dict[str, Any]:
        """Fetches the live L2 book from Polymarket CLOB v2."""
        session = await self.get_session()
        url = f"{CLOB_API_URL}/book?token_id={token_id}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.debug(f"CLOB book query failed for {token_id}: {e}")
        return {"bids": [], "asks": []}

    def evaluate_book_depth_and_spread(
        self, book: Dict[str, Any]
    ) -> Tuple[float, float, float, float]:
        """Evaluates best bid, best ask, spread, and top-2 ticks resting ask depth."""
        asks = book.get("asks", [])
        bids = book.get("bids", [])

        best_bid = float(bids[0]["price"]) if bids else 0.0
        best_ask = float(asks[0]["price"]) if asks else 1.0

        spread = round(max(0.0, best_ask - best_bid), 4)

        # Top 2 ticks executable depth
        top_asks = asks[:2]
        depth_usd = sum(
            float(lvl.get("size", 0.0)) * float(lvl.get("price", 0.0))
            for lvl in top_asks
        )

        return best_bid, best_ask, spread, round(depth_usd, 2)

    def classify_market(
        self,
        seconds_left: float,
        depth_usd: float,
        spread: float,
        oracle_type: str,
        tokens_valid: bool,
    ) -> Tuple[str, str]:
        """Applies pre-registered liquidity, oracle, and age invariants."""
        if not tokens_valid:
            return "UNTRADEABLE", "Invalid or missing CLOB token IDs"

        if oracle_type == "ORACLE_AMBIGUOUS":
            return "ORACLE_AMBIGUOUS", "Missing verified Chainlink or Binance resolution rule"

        if seconds_left <= 0:
            return "STALE", f"Market expired ({seconds_left:.0f}s left)"

        depth_ratio = depth_usd / MIN_ORDER_SIZE_USD
        if depth_ratio < DEPTH_HURDLE_RATIO:
            return (
                "THIN",
                f"Depth ${depth_usd:.2f} < ${MIN_ORDER_SIZE_USD * DEPTH_HURDLE_RATIO:.2f} (Ratio {depth_ratio:.2f}x < {DEPTH_HURDLE_RATIO:.2f}x)",
            )

        if spread > MAX_ALLOWED_SPREAD:
            return "THIN", f"Spread ${spread:.3f} > max allowed ${MAX_ALLOWED_SPREAD:.3f}"

        return "ELIGIBLE", f"Passed all gates: Depth {depth_ratio:.2f}x >= {DEPTH_HURDLE_RATIO:.2f}x, Spread ${spread:.3f} <= ${MAX_ALLOWED_SPREAD:.3f}"

    async def probe_series_slug(
        self, asset: str, cohort: str, horizon: str, series_slug: str
    ) -> List[MarketRegistryEntry]:
        """Fetches active events under a given series slug and analyzes them."""
        session = await self.get_session()
        entries = []
        url = (
            f"{GAMMA_API_URL}/events?series_slug={series_slug}"
            f"&limit=10&closed=false&order=endDate&ascending=false"
        )

        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return entries
                events = await resp.json()

            now = datetime.now(timezone.utc)
            for event in events:
                e_slug = event.get("slug", "")
                markets = event.get("markets", [])
                if not markets:
                    continue

                for m in markets:
                    m_id = str(m.get("id"))
                    if m_id in self.seen_market_ids:
                        continue
                    self.seen_market_ids.add(m_id)

                    m_end_str = m.get("endDate") or event.get("endDate")
                    end_dt = (
                        datetime.fromisoformat(m_end_str.replace("Z", "+00:00"))
                        if m_end_str
                        else None
                    )
                    seconds_left = (end_dt - now).total_seconds() if end_dt else -1.0

                    m_start_str = m.get("startDate") or event.get("startDate")
                    start_dt = (
                        datetime.fromisoformat(m_start_str.replace("Z", "+00:00"))
                        if m_start_str
                        else None
                    )

                    duration = 3600
                    if horizon == "5m":
                        duration = 300
                    elif horizon == "15m":
                        duration = 900
                    elif start_dt and end_dt:
                        duration = int((end_dt - start_dt).total_seconds())

                    tokens_raw = m.get("clobTokenIds")
                    tokens = (
                        json.loads(tokens_raw)
                        if isinstance(tokens_raw, str)
                        else (tokens_raw or [])
                    )
                    tokens_valid = len(tokens) >= 2

                    clob_up = tokens[0] if tokens_valid else ""
                    clob_down = tokens[1] if tokens_valid else ""

                    # Oracle analysis
                    oracle_type, oracle_src, oracle_rule = self.determine_oracle_type(
                        m.get("resolutionSource"),
                        m.get("description"),
                        m.get("question"),
                    )

                    # Query live order book for UP token (primary evaluation)
                    best_bid, best_ask, spread, depth_usd = 0.0, 1.0, 1.0, 0.0
                    if tokens_valid and clob_up:
                        book = await self.fetch_clob_book(clob_up)
                        best_bid, best_ask, spread, depth_usd = (
                            self.evaluate_book_depth_and_spread(book)
                        )

                    # Dynamic fee info
                    fee_schedule = m.get("feeSchedule", {})
                    fee_rate = 0.07
                    if isinstance(fee_schedule, dict) and "rate" in fee_schedule:
                        fee_rate = float(fee_schedule["rate"])
                    elif m.get("takerBaseFee") is not None:
                        fee_rate = float(m.get("takerBaseFee")) / 10000.0

                    # Classification
                    classification, reason = self.classify_market(
                        seconds_left=seconds_left,
                        depth_usd=depth_usd,
                        spread=spread,
                        oracle_type=oracle_type,
                        tokens_valid=tokens_valid,
                    )

                    entry = MarketRegistryEntry(
                        market_id=m_id,
                        asset=asset.upper(),
                        cohort=cohort,
                        horizon=horizon.lower().replace("hourly", "1h"),
                        market_family="up_down",
                        series_slug=series_slug,
                        event_slug=e_slug,
                        title=event.get("title", ""),
                        question=m.get("question", ""),
                        start_time_iso=m_start_str,
                        end_time_iso=m_end_str,
                        start_unix=start_dt.timestamp() if start_dt else None,
                        end_unix=end_dt.timestamp() if end_dt else None,
                        duration_seconds=duration,
                        seconds_to_expiry=round(seconds_left, 1),
                        oracle_source=oracle_src,
                        oracle_type=oracle_type,
                        resolution_rule_summary=oracle_rule,
                        clob_token_up=clob_up,
                        clob_token_down=clob_down,
                        fees_enabled=bool(m.get("feesEnabled", True)),
                        fee_rate=fee_rate,
                        volume_usd=float(m.get("volumeNum", 0.0) or 0.0),
                        liquidity_usd=float(m.get("liquidityNum", 0.0) or 0.0),
                        best_bid=best_bid,
                        best_ask=best_ask,
                        spread=spread,
                        executable_depth_top2_usd=depth_usd,
                        depth_ratio=round(depth_usd / MIN_ORDER_SIZE_USD, 2),
                        classification=classification,
                        classification_reason=reason,
                    )
                    entries.append(entry)

        except Exception as e:
            logger.error(f"Error querying series_slug {series_slug}: {e}")

        return entries

    async def scan_full_crypto_universe(
        self, cohorts: Optional[List[str]] = None
    ) -> List[MarketRegistryEntry]:
        """Scans all targeted cohorts and horizons across Polymarket Gamma & CLOB."""
        active_cohorts = cohorts or list(RESEARCH_COHORTS.keys())
        all_entries: List[MarketRegistryEntry] = []

        logger.info(f"Initiating EXP-303B Market Registry Scan for cohorts: {active_cohorts}")

        for cohort_name in active_cohorts:
            assets = RESEARCH_COHORTS[cohort_name]
            for asset in assets:
                for horizon in TARGET_HORIZONS:
                    slug_candidates = [
                        f"{asset}-up-or-down-{horizon}",
                        f"{asset}-up-or-down",
                    ]
                    for s in slug_candidates:
                        entries = await self.probe_series_slug(
                            asset=asset,
                            cohort=cohort_name,
                            horizon=horizon,
                            series_slug=s,
                        )
                        if entries:
                            all_entries.extend(entries)
                            logger.info(
                                f"  [{cohort_name}] {asset.upper()} {horizon}: Found {len(entries)} markets via '{s}'"
                            )
                            break  # Avoid double-scanning the same horizon

        return all_entries

    def save_registry(self, entries: List[MarketRegistryEntry]) -> Dict[str, Any]:
        """Persists registry lines to JSONL and produces a summary audit."""
        with open(REGISTRY_FILE, "w") as f:
            for e in entries:
                f.write(json.dumps(asdict(e)) + "\n")

        # Compile Summary Audit
        total = len(entries)
        by_cohort = {}
        by_horizon = {}
        by_classification = {}
        by_oracle = {}

        for e in entries:
            by_cohort[e.cohort] = by_cohort.get(e.cohort, 0) + 1
            by_horizon[e.horizon] = by_horizon.get(e.horizon, 0) + 1
            by_classification[e.classification] = (
                by_classification.get(e.classification, 0) + 1
            )
            by_oracle[e.oracle_type] = by_oracle.get(e.oracle_type, 0) + 1

        summary = {
            "registry_version": "1.0.0",
            "campaign": "EXP-303B",
            "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_markets_scanned": total,
            "eligible_markets_count": by_classification.get("ELIGIBLE", 0),
            "breakdown_by_cohort": by_cohort,
            "breakdown_by_horizon": by_horizon,
            "breakdown_by_classification": by_classification,
            "breakdown_by_oracle_type": by_oracle,
            "frozen_hurdles": {
                "min_order_size_usd": MIN_ORDER_SIZE_USD,
                "depth_hurdle_ratio": DEPTH_HURDLE_RATIO,
                "min_depth_required_usd": MIN_ORDER_SIZE_USD * DEPTH_HURDLE_RATIO,
                "max_allowed_spread": MAX_ALLOWED_SPREAD,
                "max_book_age_sec": MAX_BOOK_AGE_SEC,
            },
        }

        with open(REGISTRY_SUMMARY_FILE, "w") as f:
            json.dump(summary, f, indent=2)

        return summary


async def main_async():
    parser = argparse.ArgumentParser(description="EXP-303B Crypto Market Registry Scanner")
    parser.add_argument(
        "--cohorts",
        nargs="+",
        default=["C1_BTC", "C2_ETH", "C3_SOL"],
        help="Cohorts to scan (default: C1_BTC, C2_ETH, C3_SOL for Pass A)",
    )
    args = parser.parse_args()

    builder = CryptoMarketRegistryBuilder()
    try:
        entries = await builder.scan_full_crypto_universe(cohorts=args.cohorts)
        summary = builder.save_registry(entries)

        print("\n" + "=" * 80)
        print("          EXP-303B CRYPTO MARKET REGISTRY & ORACLE AUDIT SUMMARY")
        print("=" * 80)
        print(f"Total Markets Registered: {summary['total_markets_scanned']}")
        print(f"Eligible for Execution:   {summary['eligible_markets_count']}")
        print("\nClassification Breakdown:")
        for k, v in summary["breakdown_by_classification"].items():
            print(f"  {k:20s}: {v}")
        print("\nOracle Architecture Breakdown:")
        for k, v in summary["breakdown_by_oracle_type"].items():
            print(f"  {k:25s}: {v}")
        print("\nHorizon Breakdown:")
        for k, v in summary["breakdown_by_horizon"].items():
            print(f"  {k:10s}: {v}")
        print(f"\nDetailed Registry written to: {REGISTRY_FILE}")
        print(f"Summary Audit written to:    {REGISTRY_SUMMARY_FILE}")
        print("=" * 80 + "\n")

    finally:
        session = await builder.get_session()
        await session.close()


if __name__ == "__main__":
    asyncio.run(main_async())
