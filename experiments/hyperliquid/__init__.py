"""
Hyperliquid L1 & HyperEVM Microstructure Experiments (S4, S6, S5)
================================================================
Modules:
  - exp_s4_hl_wick_catcher: Stage-1 30s Partial-Liquidation Cooldown Wick Catcher
  - exp_s6_hip2_hyperp: HIP-2 Geometric Grid Exhaustion & Hyperp 8h EMA Squeeze
  - exp_s5_hyperevm_atomic: HyperEVM Precompile (0x0808) to CoreWriter Simulator
"""

from experiments.hyperliquid.exp_s4_hl_wick_catcher import (
    CooldownState,
    ExpS4WickCatcher,
    S4Config,
    Stage1LiquidationEvent,
    WhalePosition,
    calculate_equity_cushion_to_mmr,
    calculate_exact_liq_price,
)
from experiments.hyperliquid.exp_s6_hip2_hyperp import (
    ExpS6Runner,
    HIP2GenesisParams,
    HIP2SpotTracker,
    Hyperp8hEMATracker,
)
from experiments.hyperliquid.exp_s5_hyperevm_atomic import (
    CORE_WRITER_ADDRESS,
    CORE_WRITER_LIMIT_ORDER_HEADER,
    PRECOMPILE_0808_ADDRESS,
    PRECOMPILE_SUBFRAME_GAS_CAP,
    FelixCDP,
    HyperCoreAtomicArbSimulator,
    HyperswapReserves,
    PrecompileCallResult,
    calculate_evm_gas_usd,
    calculate_precompile_gas,
    strip_dust,
)

__all__ = [
    # Experiment S4
    "CooldownState",
    "ExpS4WickCatcher",
    "S4Config",
    "Stage1LiquidationEvent",
    "WhalePosition",
    "calculate_equity_cushion_to_mmr",
    "calculate_exact_liq_price",
    # Experiment S6
    "ExpS6Runner",
    "HIP2GenesisParams",
    "HIP2SpotTracker",
    "Hyperp8hEMATracker",
    # Experiment S5
    "CORE_WRITER_ADDRESS",
    "CORE_WRITER_LIMIT_ORDER_HEADER",
    "PRECOMPILE_0808_ADDRESS",
    "PRECOMPILE_SUBFRAME_GAS_CAP",
    "FelixCDP",
    "HyperCoreAtomicArbSimulator",
    "HyperswapReserves",
    "PrecompileCallResult",
    "calculate_evm_gas_usd",
    "calculate_precompile_gas",
    "strip_dust",
]
