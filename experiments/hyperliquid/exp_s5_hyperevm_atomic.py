#!/usr/bin/env python3
"""
Experiment S5: HyperEVM Precompile (0x0808) to CoreWriter (0x333...333) Simulator (exp_s5_hyperevm_atomic.py)
==========================================================================================================
Hyperliquid L1 & HyperEVM Microstructure Experiment S5:
Simulates atomic cross-venue arbitrage and liquidation between HyperEVM 1-second Small Blocks
(Hyperswap AMM reserves & Felix Protocol CDPs) and HyperCore L1 CLOB orderbooks.

Microstructure Invariants Modeled:
  1. Precompile 0x0808 Staticcall:
     - Gas formula: 2000 + 65 * (in_bytes + out_bytes)
     - Strict `gas: 5000` sub-frame cap preventing 100% gas burn on unmapped/invalid asset index.
     - Decodes L1 state: (best_bid, best_ask, mid_px, mark_px) scaled by 1e8.
  2. Decimal Rounding Strip:
     - Strips fractional dust prior to HyperEVM -> HyperCore bridge transfers (~200,000 gas).
  3. CoreWriter System Contract (0x333...333):
     - Action header: 0x01000001 (Action ID 1: Limit Order, Version 1).
     - Scaled parameters: limitPx and sz scaled by 1e8.
     - encodedTif = 3 (IOC) for immediate execution or cancel.
     - Cost: ~47,000 gas.
  4. Hyperswap Pool Reserves & Felix CDP Health:
     - Constant-product AMM reserves (x * y = k).
     - Felix Protocol CDP collateral ratio monitoring (CR < 110% liquidation bonus).
  5. Net Profit Guarantee:
     - Net Profit = Gross Profit - EVM Gas (Precompile + Bridge + CoreWriter + Swap) - AMM Fees - L1 CLOB Fees.
     - Reverts atomicity if Net Profit < min_profit_usdc.
"""

from __future__ import annotations

import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from experiments.core.shadow_broker import (
    L2Book,
    OrderType,
    RealisticShadowBroker,
    ShadowOrder,
    Side,
)

logger = logging.getLogger("ExpS5HyperEVM")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [S5-HYPEREVM] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Hyperliquid Authoritative Precompile & System Addresses
PRECOMPILE_0808_ADDRESS = "0x0000000000000000000000000000000000000808"
CORE_WRITER_ADDRESS    = "0x3333333333333333333333333333333333333333"

# System Constants
CORE_WRITER_LIMIT_ORDER_HEADER = "0x01000001"
PRECOMPILE_SUBFRAME_GAS_CAP = 5000
HYPERCORE_SCALE = 100_000_000  # 1e8 fixed point

# Standard Gas Costs on HyperEVM
GAS_COST_BRIDGE_TRANSFER = 200_000
GAS_COST_CORE_WRITER     = 47_000
GAS_COST_HYPERSWAP_SWAP  = 110_000
DEFAULT_GAS_PRICE_GWEI   = 0.20  # 0.2 Gwei on HyperEVM
DEFAULT_HYPE_USD_PRICE   = 25.0  # Gas token price ($25/HYPE)


# ==============================================================================
# 1. HARDWARE & EVM GAS FORMULAS
# ==============================================================================

def calculate_precompile_gas(in_bytes: int = 32, out_bytes: int = 128) -> int:
    """
    Exact HyperEVM precompile gas formula:
        Gas = 2000 + 65 * (in_bytes + out_bytes)
    """
    return 2000 + 65 * (in_bytes + out_bytes)


def calculate_evm_gas_usd(
    total_gas: int,
    gas_price_gwei: float = DEFAULT_GAS_PRICE_GWEI,
    hype_usd_price: float = DEFAULT_HYPE_USD_PRICE,
) -> float:
    """Calculates total dollar gas cost on HyperEVM."""
    eth_cost = (total_gas * gas_price_gwei * 1e-9)
    return eth_cost * hype_usd_price


def strip_dust(raw_amount: int, dust_factor: int) -> Tuple[int, int]:
    """
    Decimal rounding strip prior to HyperEVM -> HyperCore bridge transfer.
    Returns (clean_amount, dust).
    """
    if dust_factor <= 1:
        return raw_amount, 0
    clean = (raw_amount // dust_factor) * dust_factor
    dust = raw_amount - clean
    return clean, dust


# ==============================================================================
# 2. DATA STRUCTURES & PROTOCOL STATE
# ==============================================================================

@dataclass
class PrecompileCallResult:
    success: bool
    gas_used: int
    best_bid: float  # Unscaled ($)
    best_ask: float  # Unscaled ($)
    mid_px: float    # Unscaled ($)
    mark_px: float   # Unscaled ($)
    error_msg: Optional[str] = None


@dataclass
class HyperswapReserves:
    pair_address: str
    token0_symbol: str
    token1_symbol: str
    reserve0: float  # Base tokens (e.g. PURR or HYPE)
    reserve1: float  # Quote USDC
    fee_bps: float = 30.0  # 0.30% swap fee

    @property
    def spot_price(self) -> float:
        """Spot price of token0 in terms of token1 (USDC)."""
        return self.reserve1 / self.reserve0 if self.reserve0 > 0 else 0.0

    def get_amount_out(self, amount_in: float, is_in_token0: bool) -> float:
        """Standard Uniswap V2 constant product output with 0.3% fee."""
        fee_mult = 1.0 - (self.fee_bps / 10_000.0)
        in_with_fee = amount_in * fee_mult
        if is_in_token0:
            return (in_with_fee * self.reserve1) / (self.reserve0 + in_with_fee)
        else:
            return (in_with_fee * self.reserve0) / (self.reserve1 + in_with_fee)


@dataclass
class FelixCDP:
    cdp_id: str
    user_address: str
    collateral_symbol: str
    collateral_amount: float
    debt_usdc: float
    min_collateral_ratio: float = 1.10  # 110% MCR
    liquidation_bonus: float = 0.08    # 8% liquidation incentive

    def get_collateral_ratio(self, collateral_price_usd: float) -> float:
        if self.debt_usdc <= 0:
            return 999.0
        return (self.collateral_amount * collateral_price_usd) / self.debt_usdc

    def is_liquidatable(self, collateral_price_usd: float) -> bool:
        return self.get_collateral_ratio(collateral_price_usd) < self.min_collateral_ratio


# ==============================================================================
# 3. HYPEREVM TO COREWRITER SIMULATOR
# ==============================================================================

class HyperCoreAtomicArbSimulator:
    """
    Simulates HyperEVM 1-second small block cross-venue arbitrage and liquidation.
    """

    def __init__(
        self,
        shadow_broker: Optional[RealisticShadowBroker] = None,
        min_profit_usdc: float = 15.0,  # $15 minimum net profit
        gas_price_gwei: float = DEFAULT_GAS_PRICE_GWEI,
        hype_usd_price: float = DEFAULT_HYPE_USD_PRICE,
    ):
        self.shadow_broker = shadow_broker or RealisticShadowBroker(default_latency_ms=50.0)
        self.min_profit_usdc = min_profit_usdc
        self.gas_price_gwei = gas_price_gwei
        self.hype_usd_price = hype_usd_price

        # Internal state
        self.hyperswap_pools: Dict[str, HyperswapReserves] = {}
        self.felix_cdps: Dict[str, FelixCDP] = {}
        self.l1_books: Dict[int, L2Book] = {}  # asset_index -> L2Book
        self.asset_index_to_symbol: Dict[int, str] = {}

    def register_asset(self, asset_index: int, symbol: str, book: Optional[L2Book] = None) -> None:
        sym = symbol.upper()
        self.asset_index_to_symbol[asset_index] = sym
        self.l1_books[asset_index] = book or L2Book(symbol=sym)

    def register_hyperswap_pool(self, pair: HyperswapReserves) -> None:
        self.hyperswap_pools[pair.pair_address] = pair

    def register_felix_cdp(self, cdp: FelixCDP) -> None:
        self.felix_cdps[cdp.cdp_id] = cdp

    # --------------------------------------------------------------------------
    # 1. PRECOMPILE 0x0808 EMULATION (WITH SUB-FRAME 5000 GAS CAP)
    # --------------------------------------------------------------------------

    def query_precompile_0808(self, asset_index: int) -> PrecompileCallResult:
        """
        Emulates raw staticcall to precompile 0x0808:
          - Gas formula: 2000 + 65 * (in + out)
          - If asset is unknown/unmapped, sub-frame gas cap (5000) prevents 100% tx drain.
        """
        in_bytes = 32
        out_bytes = 128
        formula_gas = calculate_precompile_gas(in_bytes, out_bytes)

        if asset_index not in self.l1_books:
            # Revert in precompile sub-frame: consumes exactly PRECOMPILE_SUBFRAME_GAS_CAP
            return PrecompileCallResult(
                success=False,
                gas_used=PRECOMPILE_SUBFRAME_GAS_CAP,
                best_bid=0.0,
                best_ask=0.0,
                mid_px=0.0,
                mark_px=0.0,
                error_msg=f"AssetIndex {asset_index} unmapped on HyperCore. Sub-frame capped at {PRECOMPILE_SUBFRAME_GAS_CAP} gas.",
            )

        book = self.l1_books[asset_index]
        bid = book.best_bid() or 0.0
        ask = book.best_ask() or 0.0
        mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else (bid or ask or 0.0)

        return PrecompileCallResult(
            success=True,
            gas_used=formula_gas,
            best_bid=bid,
            best_ask=ask,
            mid_px=mid,
            mark_px=mid,
        )

    # --------------------------------------------------------------------------
    # 2. COREWRITER CALL ENCODING (0x333...333)
    # --------------------------------------------------------------------------

    @staticmethod
    def encode_core_writer_limit_order(
        asset_index: int,
        is_buy: bool,
        limit_px: float,
        size: float,
        reduce_only: bool = False,
        encoded_tif: int = 3,  # 3 = IOC
    ) -> Dict[str, Any]:
        """
        Models Action ID 1: Limit Order with header 0x01000001.
        Scales price and size by 1e8 fixed point.
        """
        px_scaled = int(round(limit_px * HYPERCORE_SCALE))
        sz_scaled = int(round(size * HYPERCORE_SCALE))

        return {
            "target": CORE_WRITER_ADDRESS,
            "header": CORE_WRITER_LIMIT_ORDER_HEADER,
            "asset_index": asset_index,
            "is_buy": is_buy,
            "limit_px_1e8": px_scaled,
            "size_1e8": sz_scaled,
            "reduce_only": reduce_only,
            "encoded_tif": encoded_tif,
            "gas_cost": GAS_COST_CORE_WRITER,
        }

    # --------------------------------------------------------------------------
    # 3. ATOMIC ARBITRAGE SIMULATION
    # --------------------------------------------------------------------------

    def evaluate_atomic_arbitrage(
        self,
        asset_index: int,
        pair_address: str,
        trade_size_usdc: float,
        dust_factor: int = 10_000_000_000,  # 1e10 (18 -> 8 decimal strip)
    ) -> Tuple[bool, Dict[str, Any], Optional[ShadowOrder]]:
        """
        Simulates atomic trade across Hyperswap and HyperCore L1:
          - Queries precompile 0x0808 with 5000 gas cap.
          - Determines direction (Buy Hyperswap -> Sell Core OR Buy Core -> Sell Hyperswap).
          - Strips fractional dust prior to bridge transfer.
          - Calculates net PnL after all EVM gas (Precompile, Bridge 200k, CoreWriter 47k, Swap 110k).
          - Asserts net_profit >= min_profit_usdc.
        """
        # Step 1: Precompile staticcall to 0x0808
        l1_res = self.query_precompile_0808(asset_index)
        if not l1_res.success:
            return False, {"error": l1_res.error_msg, "gas_used": l1_res.gas_used}, None

        pair = self.hyperswap_pools.get(pair_address)
        if not pair:
            return False, {"error": f"Pair {pair_address} not registered"}, None

        symbol = self.asset_index_to_symbol[asset_index]
        hyperswap_price = pair.spot_price
        bid_core = l1_res.best_bid
        ask_core = l1_res.best_ask

        # Direction 0: Hyperswap cheap -> Buy Hyperswap, Sell Core L1
        # Direction 1: Core cheap -> Buy Core L1, Sell Hyperswap
        dir0_edge = bid_core - hyperswap_price
        dir1_edge = hyperswap_price - ask_core

        if dir0_edge <= 0 and dir1_edge <= 0:
            return False, {
                "status": "NO_SPREAD",
                "hyperswap_price": hyperswap_price,
                "core_bid": bid_core,
                "core_ask": ask_core,
            }, None

        direction = 0 if dir0_edge > dir1_edge else 1

        # Calculate EVM gas budget:
        # Precompile (~10k) + Bridge (~200k) + CoreWriter (~47k) + Hyperswap (~110k)
        total_evm_gas = (
            l1_res.gas_used
            + GAS_COST_BRIDGE_TRANSFER
            + GAS_COST_CORE_WRITER
            + GAS_COST_HYPERSWAP_SWAP
        )
        gas_cost_usd = calculate_evm_gas_usd(
            total_gas=total_evm_gas,
            gas_price_gwei=self.gas_price_gwei,
            hype_usd_price=self.hype_usd_price,
        )

        gross_profit = 0.0
        net_profit = 0.0
        shadow_order: Optional[ShadowOrder] = None

        if direction == 0:
            # Buy token on Hyperswap with USDC
            tokens_out = pair.get_amount_out(trade_size_usdc, is_in_token0=False)
            raw_tokens_18d = int(tokens_out * 1e18)
            clean_tokens_18d, dust_burned = strip_dust(raw_tokens_18d, dust_factor)
            clean_tokens = clean_tokens_18d / 1e18

            # Sell clean tokens on HyperCore L1 at bid_core
            core_proceeds = clean_tokens * bid_core
            l1_taker_fee = core_proceeds * 0.00045  # 4.5 bps taker fee
            gross_profit = core_proceeds - trade_size_usdc
            net_profit = gross_profit - gas_cost_usd - l1_taker_fee

            if net_profit >= self.min_profit_usdc:
                shadow_order = self.shadow_broker.submit_order(
                    symbol=symbol,
                    side=Side.SELL,
                    order_type=OrderType.TAKER_IOC,
                    price=bid_core,
                    size=clean_tokens,
                    venue="hyperliquid",
                    current_ts=time.time(),
                )

        else:
            # Buy tokens on HyperCore L1 at ask_core
            tokens_to_buy = trade_size_usdc / ask_core
            core_cost = tokens_to_buy * ask_core
            l1_taker_fee = core_cost * 0.00045

            # Bridge tokens to EVM, strip dust, sell on Hyperswap for USDC
            raw_tokens_18d = int(tokens_to_buy * 1e18)
            clean_tokens_18d, dust_burned = strip_dust(raw_tokens_18d, dust_factor)
            clean_tokens = clean_tokens_18d / 1e18

            usdc_out = pair.get_amount_out(clean_tokens, is_in_token0=True)
            gross_profit = usdc_out - trade_size_usdc
            net_profit = gross_profit - gas_cost_usd - l1_taker_fee

            if net_profit >= self.min_profit_usdc:
                shadow_order = self.shadow_broker.submit_order(
                    symbol=symbol,
                    side=Side.BUY,
                    order_type=OrderType.TAKER_IOC,
                    price=ask_core,
                    size=clean_tokens,
                    venue="hyperliquid",
                    current_ts=time.time(),
                )

        is_profitable = net_profit >= self.min_profit_usdc

        telemetry = {
            "asset_index": asset_index,
            "symbol": symbol,
            "direction": "BUY_HYPERSWAP_SELL_CORE" if direction == 0 else "BUY_CORE_SELL_HYPERSWAP",
            "trade_size_usdc": trade_size_usdc,
            "hyperswap_spot": round(hyperswap_price, 4),
            "core_bid": round(bid_core, 4),
            "core_ask": round(ask_core, 4),
            "total_evm_gas": total_evm_gas,
            "gas_cost_usd": round(gas_cost_usd, 4),
            "gross_profit_usd": round(gross_profit, 2),
            "net_profit_usd": round(net_profit, 2),
            "min_profit_threshold": self.min_profit_usdc,
            "is_profitable": is_profitable,
        }

        if is_profitable:
            logger.info(
                f"[+] ATOMIC ARB EXECUTED: Symbol={symbol} Dir={telemetry['direction']} "
                f"Gross=${gross_profit:.2f} Gas=${gas_cost_usd:.2f} Net=${net_profit:.2f} "
                f"CoreOrder={shadow_order.order_id if shadow_order else None}"
            )
        else:
            logger.debug(
                f"[-] Arb rejected: Net=${net_profit:.2f} < ${self.min_profit_usdc:.2f}"
            )

        return is_profitable, telemetry, shadow_order

    # --------------------------------------------------------------------------
    # 4. FELIX CDP LIQUIDATION MONITOR
    # --------------------------------------------------------------------------

    def evaluate_felix_cdp_liquidation(
        self,
        cdp_id: str,
        asset_index: int,
    ) -> Tuple[bool, Dict[str, Any], Optional[ShadowOrder]]:
        """
        Monitors Felix Protocol CDP:
          - If CR < 110%, liquidate collateral at 8% bonus.
          - Read L1 state via precompile 0x0808 to immediately hedge/dump collateral on HyperCore CLOB.
        """
        cdp = self.felix_cdps.get(cdp_id)
        if not cdp:
            return False, {"error": f"CDP {cdp_id} not found"}, None

        l1_res = self.query_precompile_0808(asset_index)
        if not l1_res.success:
            return False, {"error": l1_res.error_msg}, None

        collateral_px = l1_res.best_bid
        cr = cdp.get_collateral_ratio(collateral_px)

        is_liq = cr < cdp.min_collateral_ratio
        if not is_liq:
            return False, {"cdp_id": cdp_id, "cr": round(cr * 100.0, 2), "status": "SOLVENT"}, None

        # Liquidate: cover debt, receive collateral + bonus
        collateral_received = (cdp.debt_usdc / collateral_px) * (1.0 + cdp.liquidation_bonus)
        gross_value = collateral_received * collateral_px
        bonus_profit = gross_value - cdp.debt_usdc

        # EVM gas for liquidation call + bridge + corewriter sell
        total_gas = l1_res.gas_used + 150_000 + GAS_COST_BRIDGE_TRANSFER + GAS_COST_CORE_WRITER
        gas_usd = calculate_evm_gas_usd(total_gas, self.gas_price_gwei, self.hype_usd_price)
        net_profit = bonus_profit - gas_usd

        shadow_order: Optional[ShadowOrder] = None
        if net_profit > self.min_profit_usdc:
            symbol = self.asset_index_to_symbol[asset_index]
            shadow_order = self.shadow_broker.submit_order(
                symbol=symbol,
                side=Side.SELL,
                order_type=OrderType.TAKER_IOC,
                price=collateral_px,
                size=collateral_received,
                venue="hyperliquid",
                current_ts=time.time(),
            )

        telemetry = {
            "cdp_id": cdp_id,
            "cr_pct": round(cr * 100.0, 2),
            "debt_covered_usdc": cdp.debt_usdc,
            "collateral_received": round(collateral_received, 4),
            "bonus_profit_usd": round(bonus_profit, 2),
            "gas_cost_usd": round(gas_usd, 4),
            "net_profit_usd": round(net_profit, 2),
            "liquidated": net_profit > self.min_profit_usdc,
        }

        return net_profit > self.min_profit_usdc, telemetry, shadow_order


# ==============================================================================
# 5. DEMO & SELF-TEST EXECUTION
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Hyperliquid Experiment S5: HyperEVM Precompile to CoreWriter Simulator ===")

    sim = HyperCoreAtomicArbSimulator()

    # Register L1 book for PURR (AssetIndex = 100)
    purr_book = L2Book(symbol="PURR")
    purr_book.set_level(0.1250, 500_000.0, Side.BUY)
    purr_book.set_level(0.1260, 500_000.0, Side.SELL)
    sim.register_asset(asset_index=100, symbol="PURR", book=purr_book)

    # Register Hyperswap PURR/USDC Pool with lower price ($0.1180)
    hyperswap_purr = HyperswapReserves(
        pair_address="0xHyperswapPurrPool11111111111111111111",
        token0_symbol="PURR",
        token1_symbol="USDC",
        reserve0=1_000_000.0,
        reserve1=118_000.0,  # Spot = 0.1180
    )
    sim.register_hyperswap_pool(hyperswap_purr)

    # 1. Test Precompile 0x0808 Gas Formula & Error Subframe Cap
    valid_call = sim.query_precompile_0808(100)
    print(f"[Precompile Valid] Gas: {valid_call.gas_used} | Bid: ${valid_call.best_bid:.4f} | Ask: ${valid_call.best_ask:.4f}")

    invalid_call = sim.query_precompile_0808(9999)  # Invalid asset index
    print(f"[Precompile Invalid] Success: {invalid_call.success} | Capped Gas: {invalid_call.gas_used} | Msg: {invalid_call.error_msg}")

    # 2. Test Atomic Cross-Venue Arbitrage (Buy Hyperswap @ 0.118 -> Sell Core @ 0.125)
    is_arb, telem_arb, ord_arb = sim.evaluate_atomic_arbitrage(
        asset_index=100,
        pair_address="0xHyperswapPurrPool11111111111111111111",
        trade_size_usdc=5000.0,
    )
    print(f"[Atomic Arb] Profitable: {is_arb} | Direction: {telem_arb['direction']} | Net Profit: ${telem_arb['net_profit_usd']:.2f}")

    # 3. Test Felix CDP Liquidation
    cdp = FelixCDP(
        cdp_id="cdp_user_42",
        user_address="0xUnderwaterBorrower11111111111111111",
        collateral_symbol="PURR",
        collateral_amount=100_000.0,  # At $0.125 = $12,500 collateral
        debt_usdc=12_000.0,          # CR = 12500 / 12000 = 104.1% < 110%
    )
    sim.register_felix_cdp(cdp)

    is_liq, telem_liq, ord_liq = sim.evaluate_felix_cdp_liquidation("cdp_user_42", asset_index=100)
    print(f"[Felix Liquidation] Triggered: {is_liq} | CR: {telem_liq['cr_pct']}% | Net Profit: ${telem_liq['net_profit_usd']:.2f}")
