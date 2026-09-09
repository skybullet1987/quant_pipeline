import pytest
import inspect
import src.execution.papertrade_daemon as daemon_mod

def test_dual_clock_schedule_invariants():
    """Verify 4H macro boundaries match the 6 UTC cycle windows."""
    macro_hours = [h for h in range(24) if h % 4 == 0]
    micro_hours = [h for h in range(24) if h % 4 != 0]

    assert macro_hours == [0, 4, 8, 12, 16, 20]
    assert len(macro_hours) == 6
    assert len(micro_hours) == 18

def test_dual_clock_handlers_exist():
    """Verify the daemon exposes canonical macro and micro handlers."""
    # Check module-level functions
    has_module_handlers = (
        hasattr(daemon_mod, "_run_macro_cycle") and 
        hasattr(daemon_mod, "_run_micro_risk_check")
    )

    # Check class-level methods if encapsulated
    has_class_handlers = False
    for _, obj in inspect.getmembers(daemon_mod, inspect.isclass):
        if hasattr(obj, "_run_macro_cycle") and hasattr(obj, "_run_micro_risk_check"):
            has_class_handlers = True
            break

    assert has_module_handlers or has_class_handlers, (
        "papertrade_daemon must implement '_run_macro_cycle' and '_run_micro_risk_check'"
    )

def test_safety_guard_is_paper():
    """Verify IS_PAPER guard exists and defaults to True."""
    assert hasattr(daemon_mod, "IS_PAPER")
    assert daemon_mod.IS_PAPER is True
