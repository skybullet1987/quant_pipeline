#!/usr/bin/env python3
"""
Experiment S10: Polygon OrderFilled Calibrated Insider Shadowing (exp_s10_insider_shadow.py)
========================================================================================
Institutional On-Chain Smart Money & Calibrated Insider Shadow Engine.

Key Architectural Capabilities:
  Part A: Historical Indexing & Wallet Calibration DB:
    - Decodes true direction from Polygon `OrderFilled` events across:
        CTFExchange (0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E)
        NegRisk_CTFExchange (0xC5d563A36AE78145C45a50134d48A1215220f80a)
    - Direction Decoding Rule:
        makerAssetId == 0 -> Maker buying conditional tokens with USDC (Maker is BUYER)
        makerAssetId != 0 -> Maker selling conditional tokens for USDC (Maker is SELLER, Taker is BUYER)
    - Automatically excludes Market Makers / Arbitrageurs emitting:
        PositionsConverted (NegRiskAdapter 0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296)
        PositionSplit / PositionsMerge (CTF)
    - Categorizes markets into domains (Politics, Macro, Sports, Crypto, Tech/Corp).
    - Computes each wallet's exact Murphy (1973) Brier Score Decomposition:
        BS = Reliability - Resolution + Uncertainty
        ECE = Expected Calibration Error

  Part B: Live Shadow Listener & Mandatory Sybil Wash-Trade Kill-Switch:
    - Shadow BUY FOK Trigger 1:
        Wallet in top-0.5% domain Resolution buys >$10,000 net in p in [0.02, 0.35].
    - Shadow BUY FOK Trigger 2:
        Fresh proxy wallet (Gnosis Safe 0xaacfee... <72h, funded >$25k) sweeps >$15,000 into a non-crypto contract.
    - Mandatory Wash-Trade Filter:
        Aborts if seller shares an upstream funding EOA cluster with buyer, OR
        seller minted the tokens via splitPosition within the last 24h.
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
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("ExpS10Insider")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [S10-INSIDER] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Authoritative Contract Addresses
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEGRISK_CTF_EXCHANGE = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
NEGRISK_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
GNOSIS_SAFE_FACTORY = "0xaacfeea03eb1561c4e67d661e40682bd20e3541b"
MAGIC_LINK_FACTORY = "0xaB45c5A4B0c941a2F231C04C3f49182e1A254052"
USDC_E_POLYGON = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"

# Domain Classifiers
DOMAIN_REGEXES = {
    "POLITICS": re.compile(r"\b(election|president|presidential|senate|house|congress|trump|biden|harris|vance|cabinet|governor|democrat|republican|poll|vote|parliament|minister)\b", re.I),
    "MACRO": re.compile(r"\b(cpi|inflation|fed|fomc|interest\s*rate|gdp|unemployment|recession|treasury|yield|jobs|payroll|rate\s*cut)\b", re.I),
    "SPORTS": re.compile(r"\b(nfl|nba|mlb|nhl|super\s*bowl|world\s*cup|premier\s*league|ucl|champions\s*league|fifa|tennis|ufc|touchdown|goal)\b", re.I),
    "CRYPTO": re.compile(r"\b(btc|eth|sol|bitcoin|ethereum|solana|halving|etf|binance|coinbase|crypto|stablecoin|sec)\b", re.I),
    "TECH_CORP": re.compile(r"\b(openai|ai|apple|tesla|nvidia|google|spacex|microsoft|meta|earnings|ceo|ipo|antitrust|stock)\b", re.I),
}


# ==============================================================================
# 1. DATA CONTRACTS
# ==============================================================================

@dataclass
class OrderFilledTrade:
    """Decoded Polygon OrderFilled trade event."""
    tx_hash: str
    block_number: int
    timestamp: float
    exchange_address: str
    order_hash: str
    maker: str
    taker: str
    maker_asset_id: int
    taker_asset_id: int
    maker_amount: float
    taker_amount: float
    fee: float
    buyer: str
    seller: str
    price: float
    size: float
    usd_notional: float
    token_id: str
    domain: str = "POLITICS"
    question: str = ""
    resolved_outcome: Optional[int] = None  # 1 if WIN, 0 if LOSE


@dataclass
class MurphyBrierDecomposition:
    """
    Exact mathematical decomposition of Brier Score (Murphy, 1973):
        BS = Reliability - Resolution + Uncertainty
    """
    sample_count: int
    brier_score: float
    reliability: float       # Lower is better (calibration error)
    resolution: float        # Higher is better (insider signal / discriminative ability)
    uncertainty: float       # Base rate entropy o_bar * (1 - o_bar)
    ece: float               # Expected Calibration Error
    base_rate: float


@dataclass
class WalletCalibrationRecord:
    """Historical accuracy, calibration, and insider scoring per wallet."""
    wallet_address: str
    domain: str
    trades_count: int
    total_volume_usd: float
    decomposition: MurphyBrierDecomposition
    is_proxy_wallet: bool
    proxy_factory: Optional[str] = None
    proxy_creation_ts: Optional[float] = None
    upstream_funding_eoa: Optional[str] = None
    is_excluded_mm: bool = False
    domain_resolution_rank_pct: float = 100.0


@dataclass
class ShadowSignal:
    """Triggered copy/insider shadow trading signal."""
    signal_id: str
    timestamp: float
    trigger_rule: str
    wallet_address: str
    domain: str
    market_question: str
    token_id: str
    trade_price: float
    trade_notional_usd: float
    wallet_resolution_score: float
    wash_trade_flagged: bool
    wash_trade_reason: Optional[str]
    action: str  # "SHADOW_BUY_FOK" or "ABORT_WASH_TRADE"


# ==============================================================================
# 2. MURPHY BRIER SCORE DECOMPOSER
# ==============================================================================

def compute_murphy_brier_decomposition(
    predictions_and_outcomes: List[Tuple[float, int]],
    num_bins: int = 10,
) -> MurphyBrierDecomposition:
    """
    Computes exact Murphy (1973) Brier Score Decomposition across K probability bins:
        Reliability = Sum_{k=1..K} (n_k / N) * (f_k - o_bar_k)^2
        Resolution  = Sum_{k=1..K} (n_k / N) * (o_bar_k - o_bar)^2
        Uncertainty = o_bar * (1 - o_bar)
        BS          = Reliability - Resolution + Uncertainty
        ECE         = Sum_{k=1..K} (n_k / N) * |f_k - o_bar_k|
    """
    n = len(predictions_and_outcomes)
    if n == 0:
        return MurphyBrierDecomposition(
            sample_count=0,
            brier_score=0.0,
            reliability=0.0,
            resolution=0.0,
            uncertainty=0.0,
            ece=0.0,
            base_rate=0.0,
        )

    # Base rate o_bar
    base_rate = sum(o for _, o in predictions_and_outcomes) / n

    # Group into K bins
    bins: Dict[int, List[Tuple[float, int]]] = collections.defaultdict(list)
    for p, o in predictions_and_outcomes:
        # Clamp to [0, 1]
        clamped_p = max(0.0, min(1.0, float(p)))
        bin_idx = min(num_bins - 1, int(clamped_p * num_bins))
        bins[bin_idx].append((clamped_p, o))

    reliability = 0.0
    resolution = 0.0
    ece = 0.0
    raw_brier_sum = sum((p - o) ** 2 for p, o in predictions_and_outcomes)
    raw_bs = raw_brier_sum / n

    for k in range(num_bins):
        items = bins[k]
        n_k = len(items)
        if n_k == 0:
            continue

        weight = n_k / n
        f_k = sum(p for p, _ in items) / n_k
        o_bar_k = sum(o for _, o in items) / n_k

        reliability += weight * ((f_k - o_bar_k) ** 2)
        resolution += weight * ((o_bar_k - base_rate) ** 2)
        ece += weight * abs(f_k - o_bar_k)

    uncertainty = base_rate * (1.0 - base_rate)
    decomp_bs = reliability - resolution + uncertainty

    return MurphyBrierDecomposition(
        sample_count=n,
        brier_score=round(decomp_bs, 6),
        reliability=round(reliability, 6),
        resolution=round(resolution, 6),
        uncertainty=round(uncertainty, 6),
        ece=round(ece, 6),
        base_rate=round(base_rate, 4),
    )


# ==============================================================================
# 3. POLYGON INSIDER SHADOW ENGINE
# ==============================================================================

class PolygonInsiderShadowEngine:
    """
    On-chain trade decoder, MM/Arb filter, wallet calibration database,
    and Sybil wash-trade defense engine.
    """

    def __init__(
        self,
        min_insider_trades: int = 5,
        resolution_percentile_cutoff: float = 0.50,  # Top 0.5% resolution
    ):
        self.min_insider_trades = min_insider_trades
        self.resolution_percentile_cutoff = resolution_percentile_cutoff

        # Market Maker / Arbitrageur exclusion set
        self.excluded_mm_wallets: Set[str] = set()

        # Upstream funding cluster registry: wallet -> parent_eoa
        self.wallet_funding_eoa: Dict[str, str] = {}

        # Proxy wallet registry: wallet -> (factory_address, creation_timestamp, initial_funding_usd)
        self.proxy_registry: Dict[str, Tuple[str, float, float]] = {}

        # Split position tracking: wallet -> last_split_timestamp
        self.wallet_last_split_ts: Dict[str, float] = {}

        # Historical trades by wallet & domain: wallet -> domain -> [(pred, outcome)]
        self.wallet_domain_history: Dict[str, Dict[str, List[Tuple[float, int]]]] = collections.defaultdict(
            lambda: collections.defaultdict(list)
        )
        self.wallet_trade_counts: Dict[str, int] = collections.defaultdict(int)
        self.wallet_volume_usd: Dict[str, float] = collections.defaultdict(float)

        # Calibrated wallets registry
        self.calibrated_wallets: Dict[str, Dict[str, WalletCalibrationRecord]] = {}

        # Emitted shadow signals
        self.signals: List[ShadowSignal] = []

    # --------------------------------------------------------------------------
    # DIRECTION DECODING & LOG INGESTION
    # --------------------------------------------------------------------------

    @staticmethod
    def decode_order_filled(
        log_event: Dict[str, Any],
        question: str = "",
        timestamp: Optional[float] = None,
    ) -> OrderFilledTrade:
        """
        Decodes true trade direction from Polygon OrderFilled logs.

        Rule:
          makerAssetId == 0: Maker buying conditional tokens with USDC.
                             -> Maker is BUYER, Taker is SELLER.
                             -> Price = makerAmount / takerAmount.
          makerAssetId != 0: Maker selling conditional tokens for USDC (takerAssetId == 0).
                             -> Maker is SELLER, Taker is BUYER.
                             -> Price = takerAmount / makerAmount.
        """
        maker = str(log_event.get("maker", "")).lower()
        taker = str(log_event.get("taker", "")).lower()
        maker_asset = int(log_event.get("makerAssetId", 0))
        taker_asset = int(log_event.get("takerAssetId", 0))
        maker_amount = float(log_event.get("makerAmountFilled", 0.0))
        taker_amount = float(log_event.get("takerAmountFilled", 0.0))
        fee = float(log_event.get("fee", 0.0))

        if maker_amount <= 0 or taker_amount <= 0:
            raise ValueError(f"Invalid OrderFilled amounts: maker={maker_amount}, taker={taker_amount}")

        # Normalization (Polymarket USDC.e and CTF shares use 6 decimals)
        m_amt = maker_amount / 1e6
        t_amt = taker_amount / 1e6

        if maker_asset == 0:
            # Maker buying conditional tokens with USDC
            buyer = maker
            seller = taker
            price = m_amt / t_amt
            size = t_amt
            usd_notional = m_amt
            token_id = str(taker_asset)
        else:
            # Maker selling conditional tokens for USDC
            buyer = taker
            seller = maker
            price = t_amt / m_amt
            size = m_amt
            usd_notional = t_amt
            token_id = str(maker_asset)

        # Domain classification
        domain = "POLITICS"
        for d_name, d_regex in DOMAIN_REGEXES.items():
            if d_regex.search(question):
                domain = d_name
                break

        now_ts = timestamp or time.time()
        return OrderFilledTrade(
            tx_hash=str(log_event.get("txHash", f"0x{uuid.uuid4().hex}")),
            block_number=int(log_event.get("blockNumber", 0)),
            timestamp=now_ts,
            exchange_address=str(log_event.get("exchangeAddress", CTF_EXCHANGE)).lower(),
            order_hash=str(log_event.get("orderHash", "")),
            maker=maker,
            taker=taker,
            maker_asset_id=maker_asset,
            taker_asset_id=taker_asset,
            maker_amount=m_amt,
            taker_amount=t_amt,
            fee=fee,
            buyer=buyer,
            seller=seller,
            price=round(price, 4),
            size=round(size, 2),
            usd_notional=round(usd_notional, 2),
            token_id=token_id,
            domain=domain,
            question=question,
        )

    # --------------------------------------------------------------------------
    # MARKET MAKER & ARBITRAGEUR FILTER
    # --------------------------------------------------------------------------

    def register_mm_exclusion_event(self, event_type: str, wallet: str) -> None:
        """
        Flags and excludes any wallet calling:
          - PositionsConverted (NegRiskAdapter)
          - PositionSplit (CTF)
          - PositionsMerge (CTF)
        """
        w = wallet.lower()
        self.excluded_mm_wallets.add(w)
        logger.debug(f"[MM EXCLUSION] Wallet {w} flagged as MM/Arb via {event_type}")

    def record_split_position(self, wallet: str, timestamp: float) -> None:
        """Records splitPosition timestamp to enforce wash-trade inventory filter."""
        w = wallet.lower()
        self.wallet_last_split_ts[w] = timestamp
        self.register_mm_exclusion_event("PositionSplit", w)

    def register_proxy_wallet(
        self,
        wallet: str,
        factory: str,
        creation_ts: float,
        initial_funding_usd: float,
        upstream_funding_eoa: Optional[str] = None,
    ) -> None:
        """Registers proxy wallets (Gnosis Safe or MagicLink)."""
        w = wallet.lower()
        self.proxy_registry[w] = (factory.lower(), creation_ts, initial_funding_usd)
        if upstream_funding_eoa:
            self.wallet_funding_eoa[w] = upstream_funding_eoa.lower()

    # --------------------------------------------------------------------------
    # HISTORICAL CALIBRATION ENGINE
    # --------------------------------------------------------------------------

    def record_resolved_trade(
        self,
        trade: OrderFilledTrade,
        outcome: int,  # 1 if WIN, 0 if LOSE
    ) -> None:
        """Ingests historical trade paired with ground-truth resolution."""
        w = trade.buyer
        self.wallet_trade_counts[w] += 1
        self.wallet_volume_usd[w] += trade.usd_notional
        self.wallet_domain_history[w][trade.domain].append((trade.price, outcome))

    def recompute_all_calibrations(self) -> None:
        """Computes Murphy Brier Decomposition for all non-MM wallets by domain."""
        logger.info("[CALIBRATION] Recomputing Murphy Brier scores across domains...")
        self.calibrated_wallets.clear()

        # Track domain resolution pools for percentile ranking
        domain_resolutions: Dict[str, List[float]] = collections.defaultdict(list)

        for wallet, domain_data in self.wallet_domain_history.items():
            if wallet in self.excluded_mm_wallets:
                continue

            for domain, history in domain_data.items():
                if len(history) < self.min_insider_trades:
                    continue
                decomp = compute_murphy_brier_decomposition(history)
                domain_resolutions[domain].append(decomp.resolution)

        # Sort domain resolution values
        for d in domain_resolutions:
            domain_resolutions[d].sort(reverse=True)

        for wallet, domain_data in self.wallet_domain_history.items():
            if wallet in self.excluded_mm_wallets:
                continue

            is_proxy = wallet in self.proxy_registry
            proxy_info = self.proxy_registry.get(wallet)
            is_mm = False

            for domain, history in domain_data.items():
                decomp = compute_murphy_brier_decomposition(history)

                # Compute percentile rank in domain (lower rank number = higher resolution)
                pool = domain_resolutions.get(domain, [])
                if pool and not is_mm:
                    # Rank where 0.0 is the best (top resolution)
                    idx = pool.index(decomp.resolution) if decomp.resolution in pool else len(pool)
                    pct = (idx / len(pool)) * 100.0
                else:
                    pct = 100.0

                record = WalletCalibrationRecord(
                    wallet_address=wallet,
                    domain=domain,
                    trades_count=len(history),
                    total_volume_usd=self.wallet_volume_usd[wallet],
                    decomposition=decomp,
                    is_proxy_wallet=is_proxy,
                    proxy_factory=proxy_info[0] if proxy_info else None,
                    proxy_creation_ts=proxy_info[1] if proxy_info else None,
                    upstream_funding_eoa=self.wallet_funding_eoa.get(wallet),
                    is_excluded_mm=is_mm,
                    domain_resolution_rank_pct=round(pct, 2),
                )
                if wallet not in self.calibrated_wallets:
                    self.calibrated_wallets[wallet] = {}
                self.calibrated_wallets[wallet][domain] = record

    # --------------------------------------------------------------------------
    # LIVE SHADOW LISTENER & SYBIL WASH-TRADE DEFENSE
    # --------------------------------------------------------------------------

    def process_live_order_filled(
        self,
        trade: OrderFilledTrade,
        current_ts: Optional[float] = None,
    ) -> Optional[ShadowSignal]:
        """
        Evaluates incoming OrderFilled event against insider shadowing criteria:
          Trigger 1: Top-0.5% domain Resolution wallet buys >$10k in p in [0.02, 0.35].
          Trigger 2: Fresh Gnosis Safe proxy (<72h, funded >$25k) sweeps >$15k into non-crypto.
          Wash-Trade Filter: Aborts if counterparty shares upstream EOA cluster or split tokens <24h.
        """
        now = current_ts or time.time()
        buyer = trade.buyer
        seller = trade.seller

        # MM/Arb Wallets are NEVER shadowed
        if buyer in self.excluded_mm_wallets:
            return None

        trigger_rule: Optional[str] = None
        resolution_score: float = 0.0

        # Check Trigger 1: Top-0.5% Domain Resolution Insider
        wallet_records = self.calibrated_wallets.get(buyer, {})
        domain_rec = wallet_records.get(trade.domain)
        if domain_rec and domain_rec.domain_resolution_rank_pct <= self.resolution_percentile_cutoff:
            if trade.usd_notional >= 10_000.0 and 0.02 <= trade.price <= 0.35:
                trigger_rule = f"TOP_RESOLUTION_INSIDER (Rank: {domain_rec.domain_resolution_rank_pct}%, Res: {domain_rec.decomposition.resolution:.4f})"
                resolution_score = domain_rec.decomposition.resolution

        # Check Trigger 2: Fresh Gnosis Safe Proxy Whale
        if not trigger_rule and buyer in self.proxy_registry:
            factory, create_ts, initial_funding = self.proxy_registry[buyer]
            age_hours = (now - create_ts) / 3600.0
            is_gnosis = (factory.lower() == GNOSIS_SAFE_FACTORY.lower())

            if is_gnosis and age_hours <= 72.0 and initial_funding >= 25_000.0:
                if trade.usd_notional >= 15_000.0 and trade.domain != "CRYPTO":
                    trigger_rule = f"FRESH_GNOSIS_SAFE_WHALE (Age: {age_hours:.1f}h, Funded: ${initial_funding:,.0f})"
                    resolution_score = 0.999

        if not trigger_rule:
            return None

        # ----------------------------------------------------------------------
        # MANDATORY SYBIL WASH-TRADE DEFENSE
        # ----------------------------------------------------------------------
        wash_trade_flagged = False
        wash_trade_reason: Optional[str] = None

        # Check A: Shared upstream funding EOA cluster
        buyer_parent = self.wallet_funding_eoa.get(buyer)
        seller_parent = self.wallet_funding_eoa.get(seller)
        if buyer_parent and seller_parent and buyer_parent == seller_parent:
            wash_trade_flagged = True
            wash_trade_reason = f"COUNTERPARTY_SHARED_FUNDING_EOA ({buyer_parent})"
        elif buyer == seller:
            wash_trade_flagged = True
            wash_trade_reason = "SELF_TRADING_SAME_ADDRESS"

        # Check B: Counterparty minted tokens via splitPosition within 24h
        if not wash_trade_flagged:
            last_split = self.wallet_last_split_ts.get(seller, 0.0)
            if (now - last_split) <= 86400.0:  # 24 hours
                wash_trade_flagged = True
                wash_trade_reason = f"SELLER_MINTED_VIA_SPLIT_POSITION_LAST_24H ({now - last_split:.0f}s ago)"

        action = "ABORT_WASH_TRADE" if wash_trade_flagged else "SHADOW_BUY_FOK"

        signal = ShadowSignal(
            signal_id=f"sig_{uuid.uuid4().hex[:8]}",
            timestamp=now,
            trigger_rule=trigger_rule,
            wallet_address=buyer,
            domain=trade.domain,
            market_question=trade.question,
            token_id=trade.token_id,
            trade_price=trade.price,
            trade_notional_usd=trade.usd_notional,
            wallet_resolution_score=resolution_score,
            wash_trade_flagged=wash_trade_flagged,
            wash_trade_reason=wash_trade_reason,
            action=action,
        )

        self.signals.append(signal)
        if wash_trade_flagged:
            logger.warning(
                f"[WASH-TRADE ABORT] Signal {signal.signal_id} on {buyer}: {wash_trade_reason}"
            )
        else:
            logger.info(
                f"[SHADOW TRIGGER] {action} {trade.token_id[:10]}... "
                f"at {trade.price} (${trade.usd_notional:,.0f}) via {trigger_rule}"
            )

        return signal
