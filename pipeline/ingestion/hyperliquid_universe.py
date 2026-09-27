"""
Dynamic Hyperliquid DEX Universe Discovery & Specification Manager.
Fetches active assets, szDecimals, asset indices (a), and 24h volume filters.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
HYPERLIQUID_TESTNET_INFO_URL = "https://api.hyperliquid-testnet.xyz/info"


@dataclass(frozen=True)
class AssetSpec:
    symbol: str
    asset_id: int
    sz_decimals: int
    max_leverage: int
    only_isolated: bool
    day_ntl_volume: float
    funding_rate_hourly: float
    mark_price: float


class HyperliquidUniverse:
    def __init__(self, is_testnet: bool = False):
        self.url = HYPERLIQUID_TESTNET_INFO_URL if is_testnet else HYPERLIQUID_INFO_URL
        self._assets: dict[str, AssetSpec] = {}
        self._asset_map: dict[str, int] = {}
        self.refresh_universe()

    def refresh_universe(self) -> dict[str, AssetSpec]:
        """Fetches the complete active perpetual universe from Hyperliquid."""
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(self.url, json={"type": "metaAndAssetCtxs"})
            resp.raise_for_status()
            data = resp.json()

        universe_meta = data[0]["universe"]
        asset_contexts = data[1]

        specs: dict[str, AssetSpec] = {}
        asset_map: dict[str, int] = {}

        for idx, (meta, ctx) in enumerate(zip(universe_meta, asset_contexts)):
            name = meta["name"]
            spec = AssetSpec(
                symbol=name,
                asset_id=idx,
                sz_decimals=int(meta.get("szDecimals", 0)),
                max_leverage=int(meta.get("maxLeverage", 1)),
                only_isolated=bool(meta.get("onlyIsolated", False)),
                day_ntl_volume=float(ctx.get("dayNtlVlm", 0.0)),
                funding_rate_hourly=float(ctx.get("funding", 0.0)),
                mark_price=float(ctx.get("markPx", 0.0)),
            )
            specs[name] = spec
            asset_map[name] = idx

        self._assets = specs
        self._asset_map = asset_map
        logger.info("Loaded %d active perps from Hyperliquid DEX.", len(self._assets))
        return self._assets

    @property
    def asset_map(self) -> dict[str, int]:
        """Returns symbol -> integer asset index 'a' mapping for EIP-712 payloads."""
        return self._asset_map

    def get_symbols(self, min_daily_volume_usd: float = 0.0) -> list[str]:
        """Returns symbols, optionally filtered by minimum 24-hour notional volume."""
        return [
            sym for sym, spec in self._assets.items()
            if spec.day_ntl_volume >= min_daily_volume_usd
        ]

    def round_size(self, symbol: str, raw_size: float) -> float:
        """Rounds size to the contract's allowed szDecimals increment."""
        decimals = self._assets[symbol].sz_decimals if symbol in self._assets else 4
        return round(float(raw_size), decimals)
