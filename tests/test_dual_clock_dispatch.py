import pytest
from unittest.mock import patch, MagicMock
from src.execution.papertrade_daemon import PaperTradeDaemon

@pytest.fixture
def daemon():
    with patch("src.execution.papertrade_daemon.HyperliquidExecutionEngine"):
        d = PaperTradeDaemon(dry_run=True)
        d._run_macro_cycle = MagicMock()
        d._run_micro_risk_check = MagicMock()
        return d

@pytest.mark.parametrize("hour,expected_macro,expected_micro", [
    (0, True, False),
    (1, False, True),
    (3, False, True),
    (4, True, False),
    (8, True, False),
    (15, False, True),
    (20, True, False),
    (23, False, True),
])
def test_dual_clock_hourly_dispatch(daemon, hour, expected_macro, expected_micro):
    daemon.dispatch_hourly_tick(hour=hour)
    assert daemon._run_macro_cycle.called == expected_macro
    assert daemon._run_micro_risk_check.called == expected_micro
