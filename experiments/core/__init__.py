"""Core telemetry watchdogs and realistic shadow-trading execution modules."""

from experiments.core.poly_watchdog_ws import (
    PolymarketDualSocketWatchdog,
    PolymarketSessionPool,
    OrderSessionManager,
    TelemetrySessionManager,
)
from experiments.core.hl_mark_replicator import (
    HyperCoreMarkPriceReplicator,
    ContinuousTimeEMA,
    weighted_median,
)
from experiments.core.shadow_broker import (
    RealisticShadowBroker,
    ShadowOrder,
    ShadowFill,
    ShadowMarkout,
    OrderType,
    OrderStatus,
    Side,
)

__all__ = [
    "PolymarketDualSocketWatchdog",
    "PolymarketSessionPool",
    "OrderSessionManager",
    "TelemetrySessionManager",
    "HyperCoreMarkPriceReplicator",
    "ContinuousTimeEMA",
    "weighted_median",
    "RealisticShadowBroker",
    "ShadowOrder",
    "ShadowFill",
    "ShadowMarkout",
    "OrderType",
    "OrderStatus",
    "Side",
]
