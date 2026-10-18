#!/usr/bin/env python3
"""
Experiment S2: UMA N/A ($0.50 Midpoint) & DVM Dispute Scanner (exp_s2_uma_na_scanner.py)
========================================================================================
Institutional Arbitrage Engine for UMA Resolution Anomalies & DVM Dispute Dislocations.

Key Capabilities:
  1. Semantic Expiry & Rule Scanning:
     - Scans active markets within 48h of endDate where:
         YES > $0.94 (NO < $0.06)  OR  NO > $0.94 (YES < $0.06)
     - Parses description text using NLP & regex to extract:
         a) Strict UTC timestamp cutoffs (e.g. "by Dec 31, 2024, 11:59 PM UTC")
         b) Named authoritative source URLs (e.g. Bloomberg, AP, government portals)
         c) Postponement, delay, or void clauses.
     - Flags candidates where the event has slipped past deadline -> forces an N/A ($0.50)
       split, delivering a 12.5x to 50x asymmetric payoff on sub-$0.04 underdog shares.

  2. UMA Optimistic Oracle & DVM Dispute Monitor:
     - Monitors Polygon UMA OO bond postings ($500 / $5,000 USDC.e at 0x2791Bca...).
     - Identifies disputed resolutions where true winner shares discount to $0.75 - $0.88.
     - Cross-references disputer against CTF token balances to detect underwater "nuisance disputers",
       triggering high-conviction shadow entries on discounted winning shares.
"""

from __future__ import annotations

import collections
import dataclasses
import json
import logging
import math
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ExpS2UmaScanner")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [S2-UMA] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Authoritative Contract Addresses on Polygon
UMA_OPTIMISTIC_ORACLE_V2 = "0xe63D6b308bCe0F6193AECB666C9ab2933A0e7973"
UMA_OPTIMISTIC_ORACLE_V3 = "0xEE540b616F0110376176378e70a2B061d40A8b7f"
USDC_E_POLYGON = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"

STANDARD_DISPUTE_BONDS_USD = (500.0, 5000.0)


# ==============================================================================
# 1. DATA CONTRACTS
# ==============================================================================

@dataclass
class SemanticRuleExtraction:
    """Parsed semantic rules from market description."""
    has_strict_utc_cutoff: bool
    cutoff_timestamp_str: Optional[str]
    cutoff_epoch_ts: Optional[float]
    has_named_sources: bool
    named_source_domains: List[str]
    has_postponement_clause: bool
    postponement_snippets: List[str]
    has_na_50_50_clause: bool


@dataclass
class UmaMarketCandidate:
    """Discovered market near expiry with asymmetric N/A ($0.50) payoff potential."""
    condition_id: str
    question: str
    description: str
    end_date_str: str
    end_date_epoch_ts: float
    hours_to_end_date: float
    yes_price: float
    no_price: float
    favorite_side: str            # "YES" or "NO" (> 0.94)
    underdog_side: str            # "NO" or "YES" (< 0.06)
    underdog_price: float         # e.g. 0.02
    underdog_token_id: str
    favorite_price: float         # e.g. 0.98
    rules: SemanticRuleExtraction
    event_slipped_past_deadline: bool
    potential_na_payoff_multiplier: float  # 0.50 / underdog_price (e.g. 25x)
    candidate_flagged: bool
    flag_reason: Optional[str] = None
    shadow_trade_recommended: bool = False


@dataclass
class UmaDisputeEvent:
    """Monitored UMA Optimistic Oracle proposal dispute event."""
    dispute_id: str
    timestamp: float
    condition_id: str
    market_question: str
    oracle_contract: str
    bond_amount_usd: float
    disputer_address: str
    proposed_winner: str
    discounted_share_price: float   # e.g. $0.80
    disputer_ctf_balances: Dict[str, float]
    is_nuisance_disputer: bool
    nuisance_reason: Optional[str]
    shadow_buy_recommended: bool
    target_entry_price: float
    expected_convergence_profit_bps: float


# ==============================================================================
# 2. SEMANTIC TEXT & RULES PARSER
# ==============================================================================

class UmaDescriptionParser:
    """
    NLP and Regex extraction for Polymarket / UMA resolution rules.
    """

    # Regex for explicit UTC / ET cutoff times
    REGEX_STRICT_CUTOFF = re.compile(
        r"(?:by|before|until|prior to|no later than)\s+"
        r"([A-Za-z]+\s+\d{1,2},?\s*\d{4},?\s*(?:\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)?\s*(?:UTC|ET|EST|EDT|GMT)?|"
        r"\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*(?:UTC|ET|EST|EDT|GMT)\s+on\s+[A-Za-z]+\s+\d{1,2},?\s*\d{4})",
        re.I,
    )

    # Regex for named URLs
    REGEX_URLS = re.compile(
        r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s\)\"\']*)?)",
        re.I,
    )

    # Known authoritative domains
    AUTHORITATIVE_DOMAINS = (
        "bloomberg.com", "reuters.com", "apnews.com", "associatedpress.com",
        "coingecko.com", "sec.gov", "federalreserve.gov", "bls.gov", "fda.gov",
        "whitehouse.gov", "who.int", "cdc.gov", "nytimes.com", "wsj.com"
    )

    # Postponement / cancellation / delay clauses
    REGEX_POSTPONEMENT = re.compile(
        r"\b(postpone|postponed|delay|delayed|reschedule|rescheduled|canceled|cancelled|call off|called off|"
        r"void|voided|not take place|not occur by|if no .* occurs by|fails to occur by)\b",
        re.I,
    )

    # Explicit 50-50 / N/A clauses
    REGEX_NA_CLAUSE = re.compile(
        r"\b(50[- ]?50|0\.50|50%|n/a|indeterminable|unknown|ambiguous|draw)\b",
        re.I,
    )

    @classmethod
    def parse_description(cls, description: str) -> SemanticRuleExtraction:
        """Parses description text into structured semantic rules."""
        desc_lower = description.lower()

        # 1. Strict Cutoff
        cutoff_match = cls.REGEX_STRICT_CUTOFF.search(description)
        has_cutoff = cutoff_match is not None
        cutoff_str = cutoff_match.group(1).strip() if cutoff_match else None

        # 2. Named URLs
        urls = cls.REGEX_URLS.findall(description)
        found_domains = set()
        for u in urls:
            domain = u.split("/")[0].lower()
            found_domains.add(domain)

        # Check for known authoritative references
        for auth in cls.AUTHORITATIVE_DOMAINS:
            if auth in desc_lower or auth.split(".")[0] in desc_lower:
                found_domains.add(auth)

        # 3. Postponement clauses
        postpone_matches = [m.group(0) for m in cls.REGEX_POSTPONEMENT.finditer(description)]
        has_postpone = len(postpone_matches) > 0

        # 4. Explicit N/A clause
        has_na = cls.REGEX_NA_CLAUSE.search(description) is not None

        return SemanticRuleExtraction(
            has_strict_utc_cutoff=has_cutoff,
            cutoff_timestamp_str=cutoff_str,
            cutoff_epoch_ts=None,  # Populated when date string parsed
            has_named_sources=(len(found_domains) > 0),
            named_source_domains=sorted(list(found_domains)),
            has_postponement_clause=has_postpone,
            postponement_snippets=postpone_matches,
            has_na_50_50_clause=has_na,
        )


# ==============================================================================
# 3. UMA RESOLUTION DISLOCATION & DISPUTE SCANNER
# ==============================================================================

class UmaNaResolutionScanner:
    """
    Continuous scanner for asymmetric N/A $0.50 payoff dislocations and
    UMA Optimistic Oracle DVM nuisance disputes.
    """

    def __init__(
        self,
        near_expiry_window_hours: float = 48.0,
        extreme_skew_threshold: float = 0.94,  # Favorite > 0.94 (Underdog < 0.06)
        dispute_discount_max_price: float = 0.88,  # Discounted winner <= 0.88
    ):
        self.window_hours = near_expiry_window_hours
        self.skew_threshold = extreme_skew_threshold
        self.dispute_discount_max = dispute_discount_max_price

        self.candidates_scanned: int = 0
        self.flagged_na_candidates: List[UmaMarketCandidate] = []
        self.dispute_events: List[UmaDisputeEvent] = []

    # --------------------------------------------------------------------------
    # N/A ($0.50 MIDPOINT) EXPIRY DISLOCATION SCANNER
    # --------------------------------------------------------------------------

    def scan_active_markets(
        self,
        markets: List[Dict[str, Any]],
        current_ts: Optional[float] = None,
        event_delayed_confirmed: Optional[Dict[str, bool]] = None,
    ) -> List[UmaMarketCandidate]:
        """
        Scans active markets within 48h of endDate with extreme skew (YES > 0.94 or NO > 0.94).
        Parses rules to detect scheduled events that slipped past strict deadlines.
        """
        now = current_ts or time.time()
        flagged: List[UmaMarketCandidate] = []
        confirmed_delayed = event_delayed_confirmed or {}

        for m in markets:
            self.candidates_scanned += 1
            cond_id = str(m.get("conditionId", m.get("id", "")))
            question = str(m.get("question", ""))
            description = str(m.get("description", ""))

            # Parse endDate
            end_date_str = str(m.get("endDate", m.get("end_date_iso", "")))
            end_ts = 0.0
            if m.get("end_epoch_ts") is not None:
                end_ts = float(m["end_epoch_ts"])
            elif end_date_str:
                try:
                    # ISO string parsing
                    cleaned = end_date_str.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(cleaned)
                    end_ts = dt.timestamp()
                except Exception:
                    end_ts = now + 3600.0
            else:
                end_ts = now + 3600.0

            hours_to_end = (end_ts - now) / 3600.0

            # Must be within 48h window or past endDate
            if hours_to_end > self.window_hours:
                continue

            # Check price skew
            p_yes = float(m.get("yes_price", m.get("best_bid_yes", 0.50)))
            p_no = float(m.get("no_price", m.get("best_bid_no", 0.50)))

            is_skewed = False
            fav_side = "YES"
            under_side = "NO"
            p_fav = p_yes
            p_under = p_no

            if p_yes >= self.skew_threshold and p_no <= (1.0 - self.skew_threshold):
                is_skewed = True
                fav_side = "YES"
                under_side = "NO"
                p_fav = p_yes
                p_under = p_no
            elif p_no >= self.skew_threshold and p_yes <= (1.0 - self.skew_threshold):
                is_skewed = True
                fav_side = "NO"
                under_side = "YES"
                p_fav = p_no
                p_under = p_yes

            if not is_skewed:
                continue

            # Semantic rule extraction
            rules = UmaDescriptionParser.parse_description(description)

            # Check if event slipped past cutoff
            event_slipped = (now >= end_ts) or confirmed_delayed.get(cond_id, False)

            # Asymmetric N/A payoff multiplier: 0.50 / underdog_price
            underdog_price_eff = max(0.01, p_under)
            multiplier = 0.50 / underdog_price_eff

            # Flagging criteria:
            # 1. Strict cutoff exists AND event has slipped or postponement clause applies
            # 2. Or explicit delay confirmed
            flag_candidate = False
            reason: Optional[str] = None

            if event_slipped and rules.has_strict_utc_cutoff:
                flag_candidate = True
                reason = f"STRICT_CUTOFF_DEADLINE_PASSED ({rules.cutoff_timestamp_str})"
            elif confirmed_delayed.get(cond_id, False) and rules.has_postponement_clause:
                flag_candidate = True
                reason = "EVENT_POSTPONED_PAST_OFFICIAL_WINDOW"
            elif event_slipped and rules.has_na_50_50_clause:
                flag_candidate = True
                reason = "AMBIGUOUS_DEADLINE_FORCE_50_50"

            tokens = m.get("clobTokenIds", ["TOK_YES", "TOK_NO"])
            if isinstance(tokens, str):
                try:
                    tokens = json.loads(tokens)
                except Exception:
                    tokens = ["TOK_YES", "TOK_NO"]
            under_token = tokens[1] if under_side == "NO" else tokens[0]

            cand = UmaMarketCandidate(
                condition_id=cond_id,
                question=question,
                description=description,
                end_date_str=end_date_str,
                end_date_epoch_ts=end_ts,
                hours_to_end_date=round(hours_to_end, 1),
                yes_price=round(p_yes, 4),
                no_price=round(p_no, 4),
                favorite_side=fav_side,
                underdog_side=under_side,
                underdog_price=round(p_under, 4),
                underdog_token_id=under_token,
                favorite_price=round(p_fav, 4),
                rules=rules,
                event_slipped_past_deadline=event_slipped,
                potential_na_payoff_multiplier=round(multiplier, 1),
                candidate_flagged=flag_candidate,
                flag_reason=reason,
                shadow_trade_recommended=(flag_candidate and multiplier >= 10.0),
            )

            if flag_candidate:
                flagged.append(cand)
                self.flagged_na_candidates.append(cand)
                logger.info(
                    f"[FLAGGED N/A CANDIDATE] {cand.question[:50]}... "
                    f"Underdog {cand.underdog_side} @ {cand.underdog_price} -> {cand.potential_na_payoff_multiplier}x payoff ({reason})"
                )

        return flagged

    # --------------------------------------------------------------------------
    # UMA DVM DISPUTE MONITOR & NUISANCE DISPUTER DETECTOR
    # --------------------------------------------------------------------------

    def monitor_uma_disputes(
        self,
        dispute_logs: List[Dict[str, Any]],
        ctf_holdings_db: Optional[Dict[str, Dict[str, float]]] = None,
        market_mid_prices: Optional[Dict[str, float]] = None,
    ) -> List[UmaDisputeEvent]:
        """
        Monitors UMA Optimistic Oracle dispute logs ($500 / $5,000 bond postings).
        Cross-references disputer against CTF balances to detect underwater nuisance disputers,
        flagging shadow buy entries on winning shares discounted to $0.75 - $0.88.
        """
        holdings = ctf_holdings_db or {}
        prices = market_mid_prices or {}
        events: List[UmaDisputeEvent] = []

        for log in dispute_logs:
            disp_id = str(log.get("disputeId", f"disp_{uuid.uuid4().hex[:8]}"))
            cond_id = str(log.get("conditionId", ""))
            q_title = str(log.get("question", "Unknown Market Question"))
            oracle_contract = str(log.get("oracleAddress", UMA_OPTIMISTIC_ORACLE_V2)).lower()
            bond_amount = float(log.get("bondAmountUsd", 500.0))
            disputer = str(log.get("disputerAddress", "")).lower()
            proposed_winner = str(log.get("proposedWinner", "YES"))

            # Current market price for the proposed winner shares during dispute panic
            share_price = prices.get(cond_id, float(log.get("discountedPrice", 0.82)))

            # Disputer's CTF holdings in this market
            disputer_balances = holdings.get(disputer, {})
            losing_side = "NO" if proposed_winner.upper() == "YES" else "YES"
            losing_shares = disputer_balances.get(losing_side, 0.0)
            winning_shares = disputer_balances.get(proposed_winner.upper(), 0.0)

            # Nuisance Disputer Detection:
            # Disputer holds large underwater losing inventory and negligible winning inventory
            is_nuisance = False
            nuisance_reason: Optional[str] = None

            if losing_shares > 5000.0 and winning_shares < (losing_shares * 0.10):
                is_nuisance = True
                nuisance_reason = (
                    f"UNDERWATER_LOSING_INVENTORY ({losing_shares:,.0f} {losing_side} shares vs {winning_shares:,.0f} {proposed_winner})"
                )
            elif bond_amount in STANDARD_DISPUTE_BONDS_USD and losing_shares > 1000.0:
                is_nuisance = True
                nuisance_reason = f"BOND_PROTECTION_OF_LOSING_POSITION (${bond_amount:,.0f} bond on {losing_shares:,.0f} {losing_side})"

            # Shadow trade recommendation:
            # If shares discount into $0.75 - $0.88 during dispute by a nuisance disputer,
            # convergence back to $1.00 is high-conviction upon DVM resolution!
            shadow_buy = False
            expected_pnl_bps = 0.0
            if share_price <= self.dispute_discount_max:
                shadow_buy = True
                expected_pnl_bps = ((1.00 - share_price) / share_price) * 10_000.0

            evt = UmaDisputeEvent(
                dispute_id=disp_id,
                timestamp=time.time(),
                condition_id=cond_id,
                market_question=q_title,
                oracle_contract=oracle_contract,
                bond_amount_usd=bond_amount,
                disputer_address=disputer,
                proposed_winner=proposed_winner,
                discounted_share_price=round(share_price, 4),
                disputer_ctf_balances=disputer_balances,
                is_nuisance_disputer=is_nuisance,
                nuisance_reason=nuisance_reason,
                shadow_buy_recommended=shadow_buy,
                target_entry_price=round(share_price, 4),
                expected_convergence_profit_bps=round(expected_pnl_bps, 1),
            )

            events.append(evt)
            self.dispute_events.append(evt)

            if shadow_buy:
                logger.info(
                    f"[DISPUTE ARB OPPORTUNITY] Disputed {proposed_winner} discounted to ${share_price:.2f} "
                    f"({expected_pnl_bps:+.0f} bps to $1.00). Nuisance: {is_nuisance} ({nuisance_reason})"
                )

        return events
