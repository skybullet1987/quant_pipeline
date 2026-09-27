import os
import yaml
from pathlib import Path
from dataclasses import dataclass

CONFIG_PATH = Path.home() / "quant_pipeline" / "config" / "strategy_config.yaml"

@dataclass(frozen=True)
class PortfolioConfig:
    target_gross_leverage: float = 4.00
    max_bull_leverage: float = 8.00
    max_drawdown_limit: float = 0.22
    grossman_zhou_curvature: float = 1.35
    s0_short_multiplier: float = 0.25
    target_carry_leverage: float = 0.35
    top_k_conviction: int = 4
    max_individual_weight: float = 2.00
    min_weight_threshold: float = 0.050

@dataclass(frozen=True)
class ExecutionConfig:
    min_turnover_deadband: float = 0.080
    min_delta_usd: float = 10.0
    min_margin_buffer: float = 0.15
    post_only_alo: bool = True
    dry_run: bool = False

@dataclass(frozen=True)
class RiskBracketsConfig:
    stop_loss_atr_mult: float = 1.40
    stop_loss_min_pct: float = 0.020
    take_profit_atr_mult: float = 2.00
    take_profit_min_pct: float = 0.045
    tranche_a_tp_atr_mult: float = 2.00
    initial_sl_atr_mult: float = 1.40
    tranche_b_ratchet_mult: float = 0.20
    volumetric_chandelier_mult: float = 3.0
    max_horizon_holding_bars: int = 18

@dataclass(frozen=True)
class RegimeModelConfig:
    covariance_lookback_bars: int = 240
    retrain_step_bars: int = 18
    min_universe_depth: int = 15
    rmt_denoising: bool = True
    market_detoning: bool = True

@dataclass(frozen=True)
class UniverseConfig:
    min_adv_usd: float = 300_000.0       # Microstructure floor for $1,000 canary account ($300k)
    min_order_notional: float = 12.0     # Hyperliquid minimum order size ($10 - $12)
    max_participation_pct: float = 0.01  # Maximum 1% of hourly volume
    target_positions: int = 20           # Target cross-sectional breadth (15-20 positions)
    testnet_top_n: int = 20              # Top N testnet assets by simulated volume
    testnet_min_adv: float = 5_000.0     # Simulated testnet volume floor

    def compute_dynamic_min_adv(
        self,
        account_equity: float,
        gross_leverage: float = 1.5,
    ) -> float:
        """
        Dynamically scales the ADV hurdle as account equity compounds:
        OrderSize = (AccountEquity * GrossLeverage) / TargetPositions
        ADV_target = (OrderSize / MaxParticipationRate) * 24
        ADV_min = max(min_adv_usd, ADV_target)
        """
        order_size = (max(1.0, account_equity) * gross_leverage) / max(1, self.target_positions)
        adv_target = (order_size / max(1e-4, self.max_participation_pct)) * 24.0
        return max(self.min_adv_usd, adv_target)

@dataclass(frozen=True)
class StrategyConfig:
    portfolio: PortfolioConfig
    execution: ExecutionConfig
    risk_brackets: RiskBracketsConfig
    regime_model: RegimeModelConfig
    universe: UniverseConfig = UniverseConfig()

def load_strategy_config(config_file: Path = CONFIG_PATH) -> StrategyConfig:
    if not config_file.exists():
        return StrategyConfig(
            portfolio=PortfolioConfig(),
            execution=ExecutionConfig(),
            risk_brackets=RiskBracketsConfig(),
            regime_model=RegimeModelConfig(),
            universe=UniverseConfig(),
        )

    with open(config_file, "r") as f:
        raw = yaml.safe_load(f)

    # Allow environment variable override for dry_run
    env_live = os.getenv("EXECUTION_LIVE_CONFIRMED", "false").lower() == "true"
    dry_run_val = False if env_live else raw.get("execution", {}).get("dry_run", False)

    port_raw = raw.get("portfolio", {})
    exec_raw = raw.get("execution", {})
    risk_raw = raw.get("risk_brackets", raw.get("two_tranche_runner", {}))
    regime_raw = raw.get("regime_model", {})
    univ_raw = raw.get("universe", {})

    return StrategyConfig(
        portfolio=PortfolioConfig(**{k: v for k, v in port_raw.items() if hasattr(PortfolioConfig, k)}),
        execution=ExecutionConfig(
            min_turnover_deadband=float(exec_raw.get("min_turnover_deadband", 0.08)),
            min_delta_usd=float(exec_raw.get("min_delta_usd", 10.0)),
            min_margin_buffer=float(exec_raw.get("min_margin_buffer", 0.15)),
            post_only_alo=bool(exec_raw.get("post_only_alo", True)),
            dry_run=dry_run_val,
        ),
        risk_brackets=RiskBracketsConfig(**{k: v for k, v in risk_raw.items() if hasattr(RiskBracketsConfig, k)}),
        regime_model=RegimeModelConfig(**{k: v for k, v in regime_raw.items() if hasattr(RegimeModelConfig, k)}),
        universe=UniverseConfig(**{k: v for k, v in univ_raw.items() if hasattr(UniverseConfig, k)}),
    )

# Global singleton
STRATEGY_CONFIG = load_strategy_config()
