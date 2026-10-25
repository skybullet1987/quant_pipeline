"""
APEX v3.8.2 Review Fix Regression Tests
=======================================
Covers defects found in the v3.8.1 review:
  1. Core-book shorts carrying holding locks must never be treated as EXP-109 satellites.
  2. Always-On satellites are fixed 0.10x slots, BTC/ETH beta-hedged, and exits unwind only the hedge they added.
  3. Simulated (DRY_RUN) fills never count toward Gate 2.
  4. Virtual paper mode is an explicit flag (never inferred from the real wallet balance).
  5. The validated fl0 recycler allocation is restored to 0.15 and the registry survives journal replay.
"""

import time
import numpy as np
from unittest.mock import MagicMock

from src.execution.production_apex_daemon import (
    ProductionApexExecutor,
    CircuitBreakerState,
    EXP109_SATELLITE_ALLOC,
    EXP109_SLOT_WEIGHT,
    EXP109_ALWAYS_ON_MAX_SLOTS,
)


def _paper_executor(tmp_path):
    ex = ProductionApexExecutor(
        testnet=False,
        dry_run=True,
        acquire_lock=False,
        journal_path=tmp_path / "journal.jsonl",
        state_path=tmp_path / "state.json",
    )
    assert ex.virtual_paper is True
    return ex


def _seed_fill(ex, coin, side, sz, px):
    now_ms = int(time.time() * 1000)
    ex.journal.append_event("FILL_RECONCILED", {
        "fill_key": f"DRY_SEED_{coin}_{now_ms}_{side}",
        "coin": coin, "oid": now_ms, "tid": now_ms, "time_ms": now_ms,
        "closed_pnl": 0.0, "fee": 0.0, "px": px, "sz": sz, "side": side,
    })


def _mock_gateway(mids):
    gw = MagicMock()
    gw.sz_decimals = {"BTC": 5, "ETH": 4, "XMR": 2, "MON": 0}
    gw.get_mid_price.side_effect = lambda s: mids[s]
    gw.get_account_state.return_value = (5000.0, 5000.0, {})
    gw.info.user_state.return_value = {"assetPositions": []}
    gw.info.user_fills_by_time.return_value = []
    gw.info.post.return_value = []
    gw.info.meta_and_asset_ctxs.return_value = ({"universe": [{"name": "MON"}, {"name": "XMR"}]}, [{"funding": "0.0"}, {"funding": "0.0002"}])
    return gw


def test_fl0_recycler_allocation_restored_and_slot_constants():
    assert EXP109_SATELLITE_ALLOC == 0.15
    assert EXP109_SLOT_WEIGHT == 0.10
    assert EXP109_ALWAYS_ON_MAX_SLOTS == 3


def test_core_locked_short_is_not_exited_as_satellite(tmp_path):
    ex = _paper_executor(tmp_path)
    _seed_fill(ex, "MON", "SELL", 2641.0, 0.0215)
    ex.state = ex.journal.replay_and_project()
    ex.state.holding_locks["MON"] = ex.state.total_micro_bars + 7  # core-book lock, NOT a satellite
    ex.gateway = _mock_gateway({"MON": 0.0216})
    events_before = ex.journal.last_event_id

    # Cushion well below 25% -> no entries; funding for MON is 0% APR (< +25%) which the old code treated as an exit
    ex._evaluate_fast_satellite_and_hedge_clock(chain_equity=0.86 * ex.state.historical_hwm, current_positions=dict(ex.state.paper_positions))

    assert "MON" in ex.state.paper_positions
    assert abs(ex.state.paper_positions["MON"]["size"] + 2641.0) < 1e-9
    assert ex.journal.last_event_id == events_before


def _beta_returns(n=120, seed=3):
    rng = np.random.default_rng(seed)
    btc = rng.normal(0, 0.01, n)
    eth = rng.normal(0, 0.01, n)
    xmr = 1.0 * btc + rng.normal(0, 0.002, n)
    return np.column_stack([btc, eth, xmr]), ["BTC", "ETH", "XMR"]


def test_satellite_slot_sizing_hedge_and_exact_unwind(tmp_path):
    ex = _paper_executor(tmp_path)
    _seed_fill(ex, "BTC", "BUY", 0.006, 80000.0)  # pre-existing core BTC long
    ex.state = ex.journal.replay_and_project()
    mids = {"BTC": 80000.0, "ETH": 2400.0, "XMR": 600.0}
    ex.gateway = _mock_gateway(mids)
    rets, syms = _beta_returns()

    ok = ex._open_satellite("XMR", -EXP109_SLOT_WEIGHT, 1000.0, rets, syms, 0, 1)
    assert ok
    xmr_sz = ex.state.paper_positions["XMR"]["size"]
    assert xmr_sz < 0
    assert abs(abs(xmr_sz) * 600.0 - 100.0) <= 6.0  # ~0.10x of $1,000 NAV (lot rounding)
    sat = ex.state.satellites["XMR"]
    assert sat["hedges"].get("BTC", 0.0) > 0  # long BTC beta hedge against the short
    assert ex.state.paper_positions["BTC"]["size"] > 0.006
    assert abs(ex.state.frozen_target_weights["XMR"] + EXP109_SLOT_WEIGHT) < 1e-9

    ok = ex._exit_satellite("XMR", "test", {})
    assert ok
    assert "XMR" not in ex.state.paper_positions
    assert abs(ex.state.paper_positions["BTC"]["size"] - 0.006) < 1e-9  # core leg restored exactly
    assert "XMR" not in ex.state.satellites
    assert "XMR" not in ex.state.frozen_target_weights


def test_satellite_registry_survives_replay(tmp_path):
    ex = _paper_executor(tmp_path)
    ex.gateway = _mock_gateway({"BTC": 80000.0, "ETH": 2400.0, "XMR": 600.0})
    rets, syms = _beta_returns()
    assert ex._open_satellite("XMR", -EXP109_SLOT_WEIGHT, 1000.0, rets, syms, 0, 1)
    ex._commit_satellite_targets()
    replayed = ex.journal.replay_and_project()
    assert "XMR" in replayed.satellites
    assert replayed.satellites["XMR"]["weight"] == -EXP109_SLOT_WEIGHT
    assert "XMR" in replayed.frozen_target_weights


def test_gate2_excludes_paper_fills(tmp_path):
    ex = _paper_executor(tmp_path)
    for i in range(8):
        ex.journal.append_event("IMPLEMENTATION_AUDIT_RECORD", {
            "symbol": "BTC-USDC", "side": "BUY" if i % 2 else "SELL", "actual_fill_price": 1.0,
            "filled_size": 1.0, "order_type": "RESTING_ALO", "total_shortfall_bps": 1.5, "mode": "DRY_RUN",
        })
    tel = ex.audit_distributional_telemetry()
    assert tel["total_lifetime_fills"] == 0
    assert tel["paper_fills_excluded_from_gate2"] == 8
    assert tel["gate2_attained"] is False
    assert tel["status"] == "PAPER_SIMULATED_NOT_GATE2_ELIGIBLE"


def test_virtual_paper_ignores_funded_real_wallet(tmp_path):
    ex = _paper_executor(tmp_path)
    ex.gateway = _mock_gateway({})  # real wallet reports $5,000 and no paper positions exist
    nav, disc, pos = ex.reconcile_ledger_events_and_reconstruct_nav()
    assert abs(nav - ex.state.initial_strategy_equity) < 1e-6
    assert disc == 0.0
    assert ex.state.circuit_breaker != CircuitBreakerState.HALTED


def test_whipsaw_and_adv_floor_exclusions_and_selected_only_locks(tmp_path):
    ex = _paper_executor(tmp_path)
    n_bars = 60
    syms = [
        "BTC", "ETH", "SOL", "INJ", "SUI", "AVAX", "LINK", "NEAR",
        "AAVE", "UNI", "DOT", "ADA", "FARTCOIN", "ILLIQ_MICRO1", "ILLIQ_MICRO2"
    ]
    n_syms = len(syms)
    rng = np.random.default_rng(123)
    close_mat = np.zeros((n_bars, n_syms))
    vol_mat = np.zeros((n_bars, n_syms))
    for j, s in enumerate(syms):
        drift = 0.008 if j % 2 == 0 else -0.008
        rets = drift + rng.normal(0.0, 0.002, n_bars)
        close_mat[:, j] = 100.0 * np.exp(np.cumsum(rets))
        if s in ("ILLIQ_MICRO1", "ILLIQ_MICRO2"):
            vol_mat[:, j] = 1.0  # Bottom 15% dollar volume
        else:
            vol_mat[:, j] = 100000.0 + j * 5000.0
    atr_mat = close_mat * 0.02
    funding_rates = np.zeros(n_syms)
    valid_mask = np.ones((n_bars, n_syms), dtype=bool)

    weights, _, _, longs, shorts, locks = ex.compute_exp103_signals_and_weights(
        close_mat=close_mat,
        atr_mat=atr_mat,
        funding_rates=funding_rates,
        valid_mask=valid_mask,
        symbols=syms,
        btc_idx=0,
        eth_idx=1,
        vol_mat=vol_mat,
    )
    selected_all = set(longs) | set(shorts)
    assert "FARTCOIN" not in selected_all
    assert "ILLIQ_MICRO1" not in selected_all
    assert "ILLIQ_MICRO2" not in selected_all
    # Only selected core positions receive holding_locks
    assert set(locks.keys()) == selected_all


def test_v40_exp115_atr_bracket_and_ratchet(tmp_path):
    ex = _paper_executor(tmp_path)
    ex.latest_atr_map = {"SOL": 2.0}
    ex.position_hwm_map = {}

    # Stage 0: initial entry ($100) with ATR = $2.00 (2%) -> SL = 100 - 2.20*2 = $95.60, TP = 100 + 8.0*2 = $116.00
    sl0, tp0, st0 = ex.compute_exp115_atr_bracket_and_ratchet(
        sym="SOL", entry_px=100.0, mark_px=100.0, is_long=True, existing_sl_px=None
    )
    assert st0 == "STAGE0_INIT"
    assert abs(sl0 - 95.60) < 1e-6
    assert abs(tp0 - 116.00) < 1e-6

    # Stage 1: +1.6 ATR ($103.20) -> SL locks entry*1.0020 + 0.35*ATR = 100.20 + 0.70 = $100.90
    sl1, tp1, st1 = ex.compute_exp115_atr_bracket_and_ratchet(
        sym="SOL", entry_px=100.0, mark_px=103.20, is_long=True, existing_sl_px=sl0
    )
    assert st1 == "STAGE1_BE_PLUS"
    assert abs(sl1 - 100.90) < 1e-6

    # Stage 2: +3.0 ATR ($106.00) -> SL trails 1.15*ATR below HWM = 106.00 - 2.30 = $103.70
    sl2, tp2, st2 = ex.compute_exp115_atr_bracket_and_ratchet(
        sym="SOL", entry_px=100.0, mark_px=106.00, is_long=True, existing_sl_px=sl1
    )
    assert st2 == "STAGE2_LOOSE_TRAIL"
    assert abs(sl2 - 103.70) < 1e-6

    # Stage 3: +4.5 ATR ($109.00) -> SL trails 0.75*ATR below HWM = 109.00 - 1.50 = $107.50
    sl3, tp3, st3 = ex.compute_exp115_atr_bracket_and_ratchet(
        sym="SOL", entry_px=100.0, mark_px=109.00, is_long=True, existing_sl_px=sl2
    )
    assert st3 == "STAGE3_PARABOLIC_TRAIL"
    assert abs(sl3 - 107.50) < 1e-6

    # Monotonic non-regression if mark price pulls back to $108.00 while HWM remains $109.00
    sl_pullback, _, _ = ex.compute_exp115_atr_bracket_and_ratchet(
        sym="SOL", entry_px=100.0, mark_px=108.00, is_long=True, existing_sl_px=sl3
    )
    assert abs(sl_pullback - sl3) < 1e-6



