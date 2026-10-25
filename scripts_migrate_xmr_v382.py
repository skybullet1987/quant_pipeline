"""One-off v3.8.2 migration: adopt the v3.8.1 XMR satellite into the registry at 0.10x with a BTC/ETH hedge.
Run ONLY while production_apex_daemon.py is stopped (single journal writer)."""
import numpy as np
from src.execution.production_apex_daemon import ProductionApexExecutor, EXP109_SLOT_WEIGHT, round_sz, log

ex = ProductionApexExecutor(testnet=False, dry_run=True, acquire_lock=False)
assert ex.virtual_paper
nav, _, positions = ex.reconcile_ledger_events_and_reconstruct_nav()
sym = "XMR"
cur = float(ex.state.paper_positions.get(sym, {}).get("size", 0.0))
if sym in ex.state.satellites or cur >= 0:
    print(f"NOTHING_TO_MIGRATE satellites={list(ex.state.satellites)} {sym}_size={cur}")
    raise SystemExit(0)

mid = float(ex.gateway.get_mid_price(sym))
dec = ex.gateway.sz_decimals.get(sym, 2)
target_sz = abs(round_sz(EXP109_SLOT_WEIGHT * nav / mid, dec))
excess = round(abs(cur) - target_sz, 6)
log("INFO", f"[MIGRATION v3.8.2] {sym} size={cur} (${abs(cur)*mid:.2f}, {abs(cur)*mid/nav:.2%} NAV) -> target {target_sz} (0.10x)")
if excess > 0:
    ex._route_satellite_order(sym, True, excess, "SAT_RESIZE", reduce=True)

close_mat, atr_mat, funding_rates, valid_mask, symbols, btc_idx, eth_idx, _ = ex.load_latest_market_data()
rets = np.zeros_like(close_mat)
rets[1:] = np.diff(close_mat, axis=0) / np.maximum(close_mat[:-1], 1e-8)

old_lock = int(ex.state.holding_locks.get(sym, ex.state.total_micro_bars + 6))
ex.state.frozen_target_weights.pop(sym, None)  # drop v3.8.1 -14.39% target; registry re-adds -0.10
new_sz = abs(float(ex.state.paper_positions[sym]["size"]))
ex._open_satellite(sym, -EXP109_SLOT_WEIGHT, nav, rets, symbols, btc_idx, eth_idx, exit_bar=old_lock, adopt_existing_size=new_sz)
ex._commit_satellite_targets()
nav2, _, pos2 = ex.reconcile_ledger_events_and_reconstruct_nav()
ex.last_telemetry_audit = ex.audit_distributional_telemetry()
ex.save_materialized_state_cache(pos2, {})
print("MIGRATED", ex.state.satellites, "NAV", round(nav, 2), "->", round(nav2, 2))
