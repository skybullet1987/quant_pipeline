"""
IRONCORE QUANTITATIVE BACKTESTING FRAMEWORK
"""

from src.backtesting.ironcore_config import IronCoreConfig_v1, DEFAULT_CONFIG
from src.backtesting.ironcore_engine import IronCoreEngine
from src.backtesting.trial_registry_dsr import TrialRegistryDSR
from src.backtesting.multi_split_regime import MultiSplitRegimeAnalyzer
from src.backtesting.ruin_and_leverage_frontier import RuinAndLeverageFrontier
from src.backtesting.adversarial_suite import AdversarialPlaceboSuite

__all__ = [
    "IronCoreConfig_v1",
    "DEFAULT_CONFIG",
    "IronCoreEngine",
    "TrialRegistryDSR",
    "MultiSplitRegimeAnalyzer",
    "RuinAndLeverageFrontier",
    "AdversarialPlaceboSuite"
]
