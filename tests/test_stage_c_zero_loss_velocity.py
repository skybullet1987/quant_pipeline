"""
Unit & Integration Tests for Stage C Pure-Riskless Velocity Recycling, Hard Pre-Split Quarantine,
and Clinched Dead-Leg On-Demand Split-to-Sell (`src/polymarket_research/stage_c_zero_loss_velocity.py`).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import requests as _requests_mod  # noqa: F401
except ModuleNotFoundError:
    sys.modules.setdefault("requests", types.ModuleType("requests"))

from src.paa_os.permissions import PermissionGate
from src.polymarket_research.holistic_strategy_governance import (
    DEFAULT_HOLISTIC_CONFIG,
    HotReloadConfigManager,
)
from src.polymarket_research.riskless_machine_gun_engine import PreSplitInventoryGun
from src.polymarket_research.stage_c_zero_loss_velocity import (
    ceil_to_tick_price,
    check_strict_pure_riskless_candidate_gate,
    evaluate_clinched_dead_leg_split_arb,
    execute_clinched_dead_leg_split_arb,
    find_recyclable_zero_loss_open_carries,
    is_strict_riskless_pre_split_blocked,
    is_unmocked_live_clob_harvester,
    recycle_open_zero_loss_carry_for_fast_arb,
)


class TestStageCZeroLossVelocity(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_telem = tempfile.TemporaryDirectory()
        self._env_patch = patch.dict(os.environ, {"PM_TELEMETRY_DIR": self._tmp_telem.name})
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()
        self._tmp_telem.cleanup()

    def test_01_strict_riskless_pre_split_quarantine_across_all_equities(self) -> None:
        cfg_path = REPO_ROOT / "config" / "polymarket_strategy_and_risk.json"
        raw_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        rb = raw_cfg["riskless_boxes"]
        self.assertTrue(bool(rb["strict_zero_legging_pre_split_lock"]))
        self.assertFalse(bool(rb["enable_pre_split_overround_gun"]))
        self.assertTrue(is_strict_riskless_pre_split_blocked(rb))

        mgr = HotReloadConfigManager(config_path=cfg_path)
        self.assertTrue(bool(mgr.snapshot["riskless_boxes"]["strict_zero_legging_pre_split_lock"]))

        # Verify strict production Harvester stays 100% blocked at $75, $145, $250, and $1,000 equity!
        gun = PreSplitInventoryGun()
        reader_calls = []
        for eq in (75.0, 145.0, 250.0, 1000.0):
            h_live = types.SimpleNamespace(
                dry_run=False,
                holistic_v5_live_mode=True,
                _startup_reconciled=True,
                _last_known_collateral=eq,
                active_positions={},
                pending_entry_intents={},
                pre_split_inventory_state={},
                executor=types.SimpleNamespace(dry_run=False, client=object()),
            )
            res = asyncio.run(
                gun.tick(h_live, time.time() + eq, fast_tick_reader=lambda a: (reader_calls.append(a) or None))
            )
            self.assertIsNone(res)
            self.assertEqual(len(reader_calls), 0)
            self.assertFalse(bool(h_live.pre_split_inventory_state.get("active")))

    def test_02_ceil_to_tick_never_rounds_below_breakeven(self) -> None:
        # 0.001-tick market: $0.992005 + $0.001 = $0.993005 -> MUST round UP to $0.994
        self.assertAlmostEqual(ceil_to_tick_price(0.993005, 0.001), 0.994, places=5)
        self.assertAlmostEqual(ceil_to_tick_price(0.993000, 0.001), 0.993, places=5)
        # 0.01-tick market: $0.992 + $0.001 = $0.993 -> rounds UP to $1.00 (rejected cleanly as > 0.999)
        self.assertAlmostEqual(ceil_to_tick_price(0.993, 0.01), 1.0, places=5)
        self.assertAlmostEqual(ceil_to_tick_price(0.0081, 0.001), 0.009, places=5)

    def test_03_zero_loss_open_carry_velocity_recycler_invariants(self) -> None:
        now_u = 1_794_115_000.0
        unwind_calls = []
        cancel_calls = []
        closed_records = []

        class _Exec:
            def get_token_tick_size(self, token_id: str, price_hint: float = 0.99) -> float:
                return 0.001 if token_id != "TOK_CENT_GRID" else 0.01

            def cancel_order(self, order_id: str, token_id: str = "") -> dict:
                cancel_calls.append((order_id, token_id))
                if order_id == "OID_ALREADY_FILLED":
                    return {"is_canceled": False, "outcome": "FILLED", "matched": 10.0}
                return {"is_canceled": True, "outcome": "CANCELED", "matched": 0.0}

            def execute_unwind_order(
                self, token_id: str, size: float, side: str = "SELL", min_price: float = 0.01, neg_risk: bool = False
            ) -> dict:
                unwind_calls.append((token_id, size, side, min_price, neg_risk))
                return {
                    "success": True,
                    "orderID": f"UW_{token_id}",
                    "matched_size": size,
                    "taking_amount": round(size * min_price, 4),
                    "fee_usd": 0.0,
                }

            def get_collateral_balance(self) -> float:
                return 28.45

        books = {
            # Recyclable 0%-fee BOND1 carry: bought @ $0.992 ($19.84 / 20 sh), live bid @ $0.994 x 25 sh -> +$0.04 gain
            "TOK_BOND_OK": {"bids": [{"price": "0.994", "size": "25"}], "asks": [{"price": "0.998", "size": "30"}]},
            # Bid below cost ($0.991 < $0.992) -> MUST NOT recycle (zero-loss rule!)
            "TOK_BELOW_COST": {"bids": [{"price": "0.991", "size": "50"}], "asks": [{"price": "0.996", "size": "30"}]},
            # Resting exit order already filled on CLOB -> MUST abort before unwind!
            "TOK_EXIT_FILLED": {"bids": [{"price": "0.995", "size": "20"}], "asks": [{"price": "0.999", "size": "20"}]},
            # 0.01-tick market at $0.992 cost -> ceil_to_tick = $1.00 > $0.999 -> MUST skip!
            "TOK_CENT_GRID": {"bids": [{"price": "0.99", "size": "50"}], "asks": [{"price": "1.00", "size": "50"}]},
        }

        harv = types.SimpleNamespace(
            dry_run=False,
            executor=_Exec(),
            _last_known_collateral=8.50,
            active_positions={
                # 1. Protected 2-leg dominance box leg -> MUST NEVER touch
                "D1_BOX_LEG_A": {
                    "trade_id": "D1_BOX_LEG_A",
                    "box_id": "BOX_1",
                    "box_partner_trade_id": "D1_BOX_LEG_B",
                    "is_dominance_box": True,
                    "is_single_leg_lock": False,
                    "box_type": "DOMINANCE",
                    "token_id": "TOK_BOND_OK",
                    "inventory_reconciled": True,
                    "status": "POSITION_CONFIRMED",
                    "fee_rate_applied": 0.0,
                    "remaining_shares": 20.0,
                    "remaining_cost_basis": 10.0,
                    "candle_expiry_ts": now_u + 14400.0,
                },
                # 2. Bid below cost -> MUST skip
                "BOND_BELOW": {
                    "trade_id": "BOND_BELOW",
                    "box_id": "BOND_BELOW",
                    "is_dominance_box": False,
                    "is_single_leg_lock": True,
                    "box_type": "SINGLE_LEG_MAKER_LOCK",
                    "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                    "token_id": "TOK_BELOW_COST",
                    "inventory_reconciled": True,
                    "status": "POSITION_CONFIRMED",
                    "fee_rate_applied": 0.0,
                    "remaining_shares": 20.0,
                    "remaining_cost_basis": 19.84,
                    "candle_expiry_ts": now_u + 14400.0,
                },
                # 3. Resting exit ask already filled on cancel -> MUST abort safely
                "BOND_EXIT_MATCHED": {
                    "trade_id": "BOND_EXIT_MATCHED",
                    "box_id": "BOND_EXIT_MATCHED",
                    "is_dominance_box": False,
                    "is_single_leg_lock": True,
                    "box_type": "SINGLE_LEG_MAKER_LOCK",
                    "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                    "token_id": "TOK_EXIT_FILLED",
                    "exit_order_id": "OID_ALREADY_FILLED",
                    "inventory_reconciled": True,
                    "status": "POSITION_CONFIRMED",
                    "fee_rate_applied": 0.0,
                    "remaining_shares": 10.0,
                    "remaining_cost_basis": 9.91,
                    "candle_expiry_ts": now_u + 18000.0,
                },
                # 4. Valid recyclable slow BOND1 carry -> cancels OID_RESTING_OK & sells @ >= $0.993 (+$0.02 net profit)
                "BOND_RECYCLE_OK": {
                    "trade_id": "BOND_RECYCLE_OK",
                    "box_id": "BOND_RECYCLE_OK",
                    "is_dominance_box": False,
                    "is_single_leg_lock": True,
                    "box_type": "SINGLE_LEG_MAKER_LOCK",
                    "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                    "token_id": "TOK_BOND_OK",
                    "exit_order_id": "OID_RESTING_OK",
                    "inventory_reconciled": True,
                    "status": "POSITION_CONFIRMED",
                    "fee_rate_applied": 0.0,
                    "remaining_shares": 20.0,
                    "remaining_cost_basis": 19.84,
                    "candle_expiry_ts": now_u + 14400.0,
                },
                # 5. 0.01-tick grid carry -> cannot place >$0.992 sell below $1.00 -> MUST skip
                "BOND_CENT_GRID": {
                    "trade_id": "BOND_CENT_GRID",
                    "box_id": "BOND_CENT_GRID",
                    "is_dominance_box": False,
                    "is_single_leg_lock": True,
                    "box_type": "SINGLE_LEG_MAKER_LOCK",
                    "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                    "token_id": "TOK_CENT_GRID",
                    "inventory_reconciled": True,
                    "status": "POSITION_CONFIRMED",
                    "fee_rate_applied": 0.0,
                    "remaining_shares": 20.0,
                    "remaining_cost_basis": 19.84,
                    "candle_expiry_ts": now_u + 14400.0,
                },
            },
            save_state=lambda: None,
        )

        def _fake_close(tid: str, pos: dict, status: str, reason: str, won: bool = True) -> float:
            pnl = round(float(pos["confirmed_realized_cash"]) - 19.84, 4)
            closed_records.append((tid, reason, pnl, pos["exit_cash_estimated"]))
            harv.active_positions.pop(tid, None)
            return pnl

        harv._close_position = _fake_close

        cands = find_recyclable_zero_loss_open_carries(
            harv,
            challenger_net_cost=0.975,  # +250 bps D1 box
            challenger_rem_tte_sec=900.0,  # 15m = 1,000 bps/hr
            book_lookup_fn=lambda t: books.get(t),
            now_ts=now_u,
        )
        self.assertEqual([c["trade_id"] for c in cands], ["BOND_EXIT_MATCHED", "BOND_RECYCLE_OK"])

        res = recycle_open_zero_loss_carry_for_fast_arb(
            harv,
            needed_cash_gap_usd=15.0,
            challenger_net_cost=0.975,
            challenger_rem_tte_sec=900.0,
            challenger_sleeve="D1_SAME_ORACLE_DOMINANCE_BOX",
            book_lookup_fn=lambda t: books.get(t),
            now_ts=now_u,
        )
        self.assertEqual(res["recycled_count"], 1)
        self.assertEqual(res["trades"], ["BOND_RECYCLE_OK"])
        self.assertGreater(res["realized_pnl_usd"], 0.0)
        self.assertAlmostEqual(res["freed_cash_usd"], 20.0 * 0.993, places=3)
        self.assertEqual(len(unwind_calls), 1)
        self.assertEqual(unwind_calls[0][0], "TOK_BOND_OK")
        self.assertAlmostEqual(unwind_calls[0][3], 0.993, places=4)
        self.assertEqual(closed_records[0][0], "BOND_RECYCLE_OK")
        self.assertFalse(closed_records[0][3])  # exit_cash_estimated MUST be False
        self.assertAlmostEqual(harv._last_known_collateral, 28.45, places=2)
        # Protected D1 box leg & already-matched exit position remain untouched
        self.assertIn("D1_BOX_LEG_A", harv.active_positions)
        self.assertIn("BOND_EXIT_MATCHED", harv.active_positions)

    def test_04_clinched_dead_leg_split_to_sell_and_raced_merge_recovery(self) -> None:
        now_u = 1_794_115_000.0
        cid = "0x" + ("ab" * 32)
        cand = {
            "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
            "asset": "KMIA",
            "p_model": 1.0,
            "leg_a_fee_rate": 0.0,
            "leg_a_neg_risk": True,
            "condition_id": cid,
            "leg_a_market_id": "20119999",
            "leg_a_token_id": "TOK_WIN_NO",
            "opp_token_id": "TOK_DEAD_YES",
            "leg_a_side_label": "NO",
            "expiry_ts": now_u + 3600.0,
        }
        bk_dead = {"bids": [{"price": "0.015", "size": "18"}], "asks": [{"price": "0.030", "size": "25"}]}

        # Rejects non-clinched (`p_model < 0.9999`) or fee-bearing markets
        self.assertIsNone(evaluate_clinched_dead_leg_split_arb({**cand, "p_model": 0.98}, bk_dead, budget_usd=15.0, now_ts=now_u))
        self.assertIsNone(evaluate_clinched_dead_leg_split_arb({**cand, "leg_a_fee_rate": 0.07}, bk_dead, budget_usd=15.0, now_ts=now_u))

        plan = evaluate_clinched_dead_leg_split_arb(cand, bk_dead, budget_usd=12.5, now_ts=now_u)
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan["shares"], 12)
        self.assertAlmostEqual(plan["min_dead_sell_px"], 0.008, places=4)

        # Case A: Dead leg FOK/FAK SELL fills 12 shares @ $0.015 -> registers 12 guaranteed NO shares @ $11.82 net cost (+$0.18 locked!)
        class _ExecFill:
            def get_conditional_balance(self, tok: str) -> float:
                return 0.0

            def execute_unwind_order(self, tok: str, size: float, side: str = "SELL", min_price: float = 0.01, neg_risk: bool = False) -> dict:
                return {"success": True, "orderID": "DEAD_SELL_1", "matched_size": size, "taking_amount": round(size * 0.015, 4), "fee_usd": 0.0}

            def get_collateral_balance(self) -> float:
                return 14.32

        harv_fill = types.SimpleNamespace(
            dry_run=False,
            executor=_ExecFill(),
            active_positions={},
            _last_known_collateral=26.14,
            save_state=lambda: None,
            _make_single_leg_lock_pos=lambda lid, bt, sl, ast, hz, mid, c, tok, sd, nr, sh, not_u, *rest, **kw: {
                "trade_id": lid,
                "box_type": bt,
                "sleeve": sl,
                "token_id": tok,
                "entry_shares": sh,
                "remaining_shares": sh,
                "notional_usd": not_u,
                "remaining_cost_basis": not_u,
                "hold_to_maturity_lock": True,
            },
        )
        with patch(
            "src.polymarket_research.riskless_machine_gun_engine.attempt_onchain_split_position",
            return_value={"success": True, "tx_hash": "0xsplit_ok"},
        ), patch(
            "src.polymarket_research.riskless_machine_gun_engine.wait_for_erc1155_delivery",
            return_value=True,
        ):
            r_ok = execute_clinched_dead_leg_split_arb(harv_fill, cand, plan, now_ts=now_u)
        self.assertTrue(r_ok["executed"])
        self.assertAlmostEqual(r_ok["dead_cash_usd"], 0.18, places=4)
        self.assertAlmostEqual(r_ok["net_cost_usd"], 11.82, places=4)
        self.assertAlmostEqual(r_ok["locked_profit_usd"], 0.18, places=4)
        self.assertEqual(len(harv_fill.active_positions), 1)

        # Case B: Dead-leg bid is raced (`matched_size == 0`) -> merges all 12 pairs right back into $12.00 cash ($0.00 loss!)
        merge_calls = []

        class _ExecRaced:
            def get_conditional_balance(self, tok: str) -> float:
                return 0.0

            def execute_unwind_order(self, tok: str, size: float, side: str = "SELL", min_price: float = 0.01, neg_risk: bool = False) -> dict:
                return {"success": False, "orderID": None, "matched_size": 0.0, "taking_amount": 0.0, "fee_usd": 0.0}

            def attempt_onchain_complete_set_merge(self, c_id: str, min_pairs: float, max_pairs: float, neg_risk: bool = False):
                merge_calls.append((c_id, min_pairs, max_pairs, neg_risk))
                return (True, max_pairs)

        harv_raced = types.SimpleNamespace(
            dry_run=False,
            executor=_ExecRaced(),
            active_positions={},
            save_state=lambda: None,
        )
        with patch(
            "src.polymarket_research.riskless_machine_gun_engine.attempt_onchain_split_position",
            return_value={"success": True, "tx_hash": "0xsplit_raced"},
        ), patch(
            "src.polymarket_research.riskless_machine_gun_engine.wait_for_erc1155_delivery",
            return_value=True,
        ):
            r_raced = execute_clinched_dead_leg_split_arb(harv_raced, cand, plan, now_ts=now_u)
        self.assertFalse(r_raced["executed"])
        self.assertEqual(r_raced["reason"], "DEAD_BID_RACED_MERGED_FLAT_ZERO_LOSS")
        self.assertEqual(len(merge_calls), 1)
        self.assertEqual(merge_calls[0][1], 12.0)
        self.assertEqual(len(harv_raced.active_positions), 0)

    def test_05_zero_trust_permission_gate_audit(self) -> None:
        gate = PermissionGate()
        stage_c_files = [
            "config/polymarket_strategy_and_risk.json",
            "src/polymarket_research/stage_c_zero_loss_velocity.py",
            "src/polymarket_research/holistic_strategy_governance.py",
            "src/polymarket_research/polymarket_live_harvester.py",
            "src/polymarket_research/riskless_protocol_v2_expansion.py",
            "tests/test_stage_c_zero_loss_velocity.py",
        ]
        cand_cfg = json.loads((REPO_ROOT / "config/polymarket_strategy_and_risk.json").read_text(encoding="utf-8"))
        base_cfg = json.loads(json.dumps(cand_cfg))
        base_cfg["riskless_boxes"]["paused_riskless_sleeves"] = [
            "SOC2_EXACT_SCORE_2D_LATTICE",
            "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
            "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
        ]
        base_cfg["riskless_boxes"]["enable_s2_twap_lock_live"] = True
        base_cfg["riskless_boxes"]["enable_reward_locked_carry_live_bridge"] = True
        base_cfg["riskless_boxes"]["enable_nr3_synthetic_overround"] = True
        base_cfg["riskless_boxes"].pop("strict_zero_legging_pre_split_lock", None)
        base_cfg["riskless_boxes"].pop("strict_pure_riskless_mode", None)
        base_cfg["riskless_boxes"].pop("enable_zero_loss_open_carry_velocity_recycle", None)
        base_cfg["riskless_boxes"].pop("enable_clinched_dead_leg_split_sell", None)

        synth_diff = "\n".join(
            "+" + ln
            for rel in stage_c_files[:3]
            for ln in (REPO_ROOT / rel).read_text(encoding="utf-8").splitlines()
        )
        ok, violations = gate.inspect_candidate_diff(
            stage_c_files, synth_diff, baseline_cfg=base_cfg, candidate_cfg=cand_cfg
        )
        self.assertTrue(ok, f"Pure-Riskless Lockdown violated Zero-Trust PermissionGate: {violations}")
        self.assertIn("strict_zero_legging_pre_split_lock", DEFAULT_HOLISTIC_CONFIG["riskless_boxes"])
        self.assertIn("strict_pure_riskless_mode", DEFAULT_HOLISTIC_CONFIG["riskless_boxes"])

    def test_06_pure_riskless_lockdown_blocks_all_probabilistic_and_multileg_loopholes(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            evaluate_clinched_ws_book_snipe_impl,
            finish_protocol_v2_special_box_sync,
            register_clinched_ws_watch_cand_impl,
        )

        cfg = json.loads((REPO_ROOT / "config/polymarket_strategy_and_risk.json").read_text(encoding="utf-8"))
        self.assertTrue(bool(cfg["directional"]["riskless_only_mode"]))
        rb = cfg["riskless_boxes"]
        self.assertTrue(bool(rb["strict_pure_riskless_mode"]))
        self.assertFalse(bool(rb["enable_s2_twap_lock_live"]))
        self.assertFalse(bool(rb["enable_nr3_synthetic_overround"]))
        self.assertFalse(bool(rb["enable_pre_split_overround_gun"]))
        self.assertFalse(bool(rb["enable_two_leg_maker_anchor_boxes"]))
        self.assertFalse(bool(rb["enable_d1_rebate_maker_canary"]))
        self.assertTrue(bool(rb["enable_single_leg_maker_bond1"]))
        self.assertTrue(bool(rb["enable_ungraduated_v3_math_live"]))
        self.assertTrue(bool(rb["enable_clinched_dead_leg_split_sell"]))
        self.assertFalse(bool(rb["enable_cross_condition_complement_merge"]))

        paused = set(rb["paused_riskless_sleeves"])
        for must_pause in (
            "S2_EXACT_TWAP_LOCK",
            "S2_RTDS_EXACT_TWAP_INTEGRATOR",
            "W_PRUNE1_NR0_BASKET",
            "NR0_ALL_YES_COMPLETE_SET",
            "NR0_ZERO_FEE_SLATE_ARB",
            "LP_COMP1_SPORTS_TRIANGLES",
            "DC1_DOUBLE_CHANCE_1X2_PARITY",
            "CTF_OVERROUND_MINT_SELL",
            "W_SOLAR1_POST_2351_LOCK",
            "MKR_REWARD_LOCKED_CARRY",
            "SOC2_EXACT_SCORE_2D_LATTICE",
            "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
            "CM_B3_PYTH_BARRIER_BOX",
        ):
            self.assertIn(must_pause, paused)
        for row2_unpaused in (
            "BOND1_UMA_RESOLUTION_CARRY",
            "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
            "UMA_READY1_LIVENESS_PRIORITY",
            "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
            "W_PRUNE1_DEAD_NO_BOND",
            "SP2_NBA_ENDGAME_LOCK",
            "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
            "NR_M1_DEAD_SEED_OVERROUND",
        ):
            self.assertNotIn(row2_unpaused, paused)

        class _UnmockedLiveExecutor:
            def __init__(self) -> None:
                self.dry_run = False
                self.auth_mode = "LIVE"
                self.client = object()

        live_harv = types.SimpleNamespace(
            dry_run=False,
            executor=_UnmockedLiveExecutor(),
            active_positions={},
            closed_positions=[],
        )
        self.assertTrue(is_unmocked_live_clob_harvester(live_harv))

        # 1. Blocks pre-expiry S2 crypto TWAP across Taker, Maker & WS Clinch Sniper
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "S2_EXACT_TWAP_LOCK", "p_model": 0.9995},
                rb,
            )
        )
        now_w = time.time()
        self.assertFalse(
            register_clinched_ws_watch_cand_impl(
                live_harv,
                {
                    "sleeve_source": "S2_EXACT_TWAP_LOCK",
                    "p_model": 0.9995,
                    "expiry_ts": now_w + 12.0,
                    "leg_a_token_id": "1" * 28,
                    "leg_a_opp_token_id": "2" * 28,
                    "leg_a_market_id": "991122",
                },
                now_ts=now_w,
            )
        )
        live_harv._clinched_ws_watchlist = {
            "1" * 28: {
                "sleeve_source": "S2_EXACT_TWAP_LOCK",
                "p_model": 0.9995,
                "expiry_ts": now_w + 12.0,
                "max_box_cost_net": 0.99,
                "leg_a_token_id": "1" * 28,
                "leg_a_opp_token_id": "2" * 28,
            }
        }
        self.assertIsNone(
            evaluate_clinched_ws_book_snipe_impl(
                live_harv,
                "1" * 28,
                {"asks": [{"price": "0.97", "size": "20"}]},
                now_ts=now_w,
            )
        )

        # 2. Blocks 3..12-leg MULTI_LEG_BUNDLE (`W_PRUNE1_NR0_BASKET`), CTF_OVERROUND, NR3, and m>=3 NR2
        out_ml = finish_protocol_v2_special_box_sync(
            live_harv,
            {
                "box_type": "MULTI_LEG_BUNDLE",
                "sleeve_source": "W_PRUNE1_NR0_BASKET",
                "legs": [{"token_id": "1"}, {"token_id": "2"}, {"token_id": "3"}],
            },
            dedupe_k="K1",
            retry_cd={},
            now_ts=now_w,
            rcfg={},
        )
        self.assertFalse(out_ml["executed"])
        self.assertIn("PURE_RISKLESS", out_ml["reason"])

        out_ovr = finish_protocol_v2_special_box_sync(
            live_harv,
            {"box_type": "CTF_OVERROUND", "sleeve_source": "CTF_OVERROUND_MINT_SELL", "condition_id": "0x" + "a" * 64},
            dedupe_k="K2",
            retry_cd={},
            now_ts=now_w,
            rcfg={},
        )
        self.assertFalse(out_ovr["executed"])
        self.assertIn("PURE_RISKLESS", out_ovr["reason"])

        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "NEGRISK_CONVERT", "convert_mode": "NR2_PURE_CASH_CONVERT", "no_legs": [{}, {}, {}]},
                rb,
            )
        )
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "NEGRISK_CONVERT", "convert_mode": "NR3_SYNTHETIC_ALL_YES_OVERROUND", "yes_sell_legs": [{}, {}]},
                rb,
            )
        )

        # 3. Blocks Q4 in-game NBA Brownian-bridge (`p_model=0.997`), pre-midnight solar, and missing p_model
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "SP2_NBA_ENDGAME_LOCK", "p_model": 0.997},
                rb,
            )
        )
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "W_SOLAR1_POST_2351_LOCK", "p_model": 0.9995},
                rb,
            )
        )
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "SINGLE_LEG_MAKER_LOCK", "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"},
                rb,
                is_maker=True,
            )
        )
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "SINGLE_LEG_MAKER_LOCK", "sleeve_source": "MKR_REWARD_LOCKED_CARRY", "p_model": 1.0},
                rb,
                is_maker=True,
            )
        )

        # 4. BLOCKS Row-1 directional / cross-question NLP corridors & inverted strikes:
        for non_riskless_cand in (
            {"box_type": "DOMINANCE", "sleeve_source": "SOC2_SCORE_TOTAL_BTTS_LATTICE"},
            {"box_type": "DOMINANCE", "sleeve_source": "CM_B3_PYTH_BARRIER_BOX"},
            {"box_type": "DOMINANCE", "sleeve_source": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"},
            {"box_type": "DOMINANCE_MAKER_ANCHOR", "sleeve_source": "D1_MAKER_ANCHOR_BOX"},
            {"box_type": "COMPLETE_SET", "sleeve_source": "C1_BINARY_COMPLETE_SET", "leg_a_condition_id": "0x11", "leg_b_condition_id": "0x22"},
            {"box_type": "DOMINANCE", "sleeve_source": "D1_SAME_ORACLE_DOMINANCE_BOX", "k_low": 96000.0, "k_high": 95000.0},
        ):
            self.assertIsNotNone(
                check_strict_pure_riskless_candidate_gate(live_harv, non_riskless_cand, rb),
                f"Expected non-riskless candidate to be BLOCKED: {non_riskless_cand}",
            )

        # 4b. BLOCKS intraday unclinched W1 solar, ALL single-leg W1_LOW_TROUGH_LOCK (evening cold-pool hazard),
        # and non-invariant single-leg SP4 pre-settlement stat/subperiod clinches, while permitting post-day
        # W1_SOLAR_PEAK_LOCK (p_model==1.0, rem_hours_count==0) and 2-leg .5-hook SP4 corridors:
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "W1_SOLAR_PEAK_LOCK", "p_model": 0.9992},
                rb,
            )
        )
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "W1_LOW_TROUGH_LOCK", "p_model": 1.0, "rem_hours_count": 0},
                rb,
            )
        )
        self.assertIsNotNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", "p_model": 0.9995},
                rb,
            )
        )
        self.assertIsNone(
            check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "W1_SOLAR_PEAK_LOCK", "p_model": 1.0, "rem_hours_count": 0},
                rb,
            )
        )

        # 5. PERMITS Row-2 zero-loss post-clinch / UMA / METAR-locked carries + 2-leg D1 / C1 / SP4(.5-hook) / NR2 / m=1 NR_M1:
        for clean_cand in (
            {"box_type": "SINGLE_LEG_MAKER_LOCK", "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY"},
            {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY", "p_model": 1.0},
            {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "UMA_READY1_LIVENESS_PRIORITY", "p_model": 1.0},
            {"box_type": "CLINCH_WATCHLIST_REG", "sleeve_source": "W_PRUNE1_DEAD_NO_BOND", "p_model": 1.0},
            {"box_type": "SINGLE_LEG_MAKER_LOCK", "sleeve_source": "W_PRUNE1_DEAD_NO_BOND", "p_model": 1.0},
            {"box_type": "SINGLE_LEG_MAKER_LOCK", "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "p_model": 1.0},
            {"box_type": "SINGLE_LEG_LOCK", "sleeve_source": "SP2_NBA_ENDGAME_LOCK", "p_model": 1.0},
            {"box_type": "DOMINANCE", "sleeve_source": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", "k_low": 0.5, "k_high": 1.5},
            {"box_type": "NEGRISK_CONVERT", "sleeve_source": "NR_M1_DEAD_SEED_OVERROUND", "convert_mode": "NR_M1_DEAD_SEED_OVERROUND", "no_legs": [{}]},
            {"box_type": "DOMINANCE", "sleeve_source": "D1_SAME_ORACLE_DOMINANCE_BOX", "k_low": 94500.0, "k_high": 95000.0},
            {"box_type": "DOMINANCE", "sleeve_source": "D1_QUIET_BOOK_BOX", "k_low": 2400.0, "k_high": 2410.0},
            {
                "box_type": "COMPLETE_SET",
                "sleeve_source": "C1_BINARY_COMPLETE_SET",
                "leg_a_condition_id": "0xabc",
                "leg_b_condition_id": "0xabc",
                "leg_a_market_id": "555",
                "leg_b_market_id": "555",
                "leg_a_token_id": "111",
                "leg_b_token_id": "222",
            },
            {"box_type": "NEGRISK_CONVERT", "sleeve_source": "NR2_CONVERT_NO_SUBSET_ARB", "convert_mode": "NR2_PURE_CASH_CONVERT", "no_legs": [{}, {}]},
        ):
            self.assertIsNone(
                check_strict_pure_riskless_candidate_gate(live_harv, clean_cand, rb),
                f"Expected pure-riskless / Row-2 candidate to be allowed: {clean_cand}",
            )

    def test_07_frozen_uma_lock_isolation_preserves_open_positions_and_unchokes_liquid_pusd(self) -> None:
        from scripts.paa_flat_harvester_redeploy_once import _safe_to_restart
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            compute_sll_entry_budget,
            is_post_expiry_uma_frozen_lock,
        )

        now_u = 1_794_245_000.0
        kmia_exp = 1_794_113_999.0  # >36h past market expiry, UMA disputed
        kmia_positions = {
            "WS_SNIPE_Miami_KMIA_242960": {
                "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                "is_single_leg_lock": True,
                "hold_to_maturity_lock": True,
                "status": "POSITION_CONFIRMED",
                "umaResolutionStatus": "disputed",
                "candle_expiry_ts": kmia_exp,
                "entry_ts": kmia_exp - 1800.0,
                "notional_usd": 19.54,
                "remaining_shares": 20.0,
                "exit_order_id": None,
            },
            "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898",
                "box_type": "MULTI_LEG_RESIDUAL",
                "sleeve": "W_PRUNE1_NR0_BASKET",
                "is_single_leg_lock": True,
                "hold_to_maturity_lock": True,
                "status": "POSITION_CONFIRMED",
                "umaResolutionStatus": "disputed",
                "candle_expiry_ts": kmia_exp,
                "entry_ts": kmia_exp - 2100.0,
                "notional_usd": 16.32,
                "remaining_shares": 17.0,
                "exit_order_id": None,
            },
            "WS_SNIPE_Miami_KMIA_688670": {
                "trade_id": "WS_SNIPE_Miami_KMIA_688670",
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                "is_single_leg_lock": True,
                "hold_to_maturity_lock": True,
                "status": "POSITION_CONFIRMED",
                "umaResolutionStatus": "disputed",
                "candle_expiry_ts": kmia_exp,
                "entry_ts": kmia_exp - 1500.0,
                "notional_usd": 9.77,
                "remaining_shares": 10.0,
                "exit_order_id": None,
            },
            "WS_SNIPE_Miami_KMIA_837595": {
                "trade_id": "WS_SNIPE_Miami_KMIA_837595",
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                "is_single_leg_lock": True,
                "hold_to_maturity_lock": True,
                "status": "POSITION_CONFIRMED",
                "umaResolutionStatus": "disputed",
                "candle_expiry_ts": kmia_exp,
                "entry_ts": kmia_exp - 1200.0,
                "notional_usd": 4.88,
                "remaining_shares": 5.0,
                "exit_order_id": None,
            },
        }
        for tid, pos in kmia_positions.items():
            self.assertTrue(is_post_expiry_uma_frozen_lock(pos, now_u), f"Expected {tid} to be UMA-frozen")

        # Fresh (<4h) 2h-liveness BOND1 proposed carry, pre-expiry lock, or active exit_order_id MUST return False:
        fresh_b1 = {
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "is_single_leg_lock": True,
            "hold_to_maturity_lock": True,
            "status": "POSITION_CONFIRMED",
            "umaResolutionStatus": "proposed",
            "candle_expiry_ts": now_u - 1800.0,
            "entry_ts": now_u - 900.0,
            "notional_usd": 8.93,
            "exit_order_id": None,
        }
        self.assertFalse(is_post_expiry_uma_frozen_lock(fresh_b1, now_u))
        self.assertFalse(is_post_expiry_uma_frozen_lock({**fresh_b1, "umaResolutionStatus": "disputed", "exit_order_id": "OID_1"}, now_u))
        self.assertFalse(is_post_expiry_uma_frozen_lock({**fresh_b1, "umaResolutionStatus": "disputed", "candle_expiry_ts": now_u + 600.0}, now_u))

        # Verify `$47.07` free cash + `$50.51` frozen KMIA unlocks all 5 concurrent Maker slots (`>= 5` shares on slot #5):
        cfg = json.loads((REPO_ROOT / "config/polymarket_strategy_and_risk.json").read_text(encoding="utf-8"))
        b1_gov = cfg["riskless_boxes"]
        four_resting_intents = {
            f"INT_{i}": {
                "inflight_key": f"K_{i}",
                "live_maker_anchor_inflight": True,
                "cash_reserved_on_exchange": False,
                "notional_usd": 8.92,
                "market_id": f"MKT_{i}",
                "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
            }
            for i in range(4)
        }
        harv = types.SimpleNamespace(
            dry_run=False,
            max_exposure=100.0,
            enforce_seed_zero_loss_focus=True,
            enforce_gatling_sizing=True,
            active_positions=dict(kmia_positions),
            pending_entry_intents=four_resting_intents,
            executor=types.SimpleNamespace(dry_run=False, client=object()),
            _is_v5_unleashed_active=lambda: True,
        )
        budget_slot5, _, sll_pct = compute_sll_entry_budget(
            harv,
            "W_PRUNE1_DEAD_NO_BOND",
            "MKT_5",
            47.07,
            False,
            True,
            b1_gov,
            {},
            cfg,
            18000.0,
            now_u,
        )
        self.assertGreaterEqual(sll_pct, 0.92)
        self.assertGreaterEqual(budget_slot5, 5.0 * 0.994, f"5th Maker slot starved: ${budget_slot5:.2f}")

        # Verify flat-redeploy watcher treats restart-safe frozen UMA locks + Maker-only intents as safe,
        # while blocking on any active pre-expiry / fresh live lock:
        self.assertTrue(
            _safe_to_restart(
                {"active_positions": kmia_positions, "pending_entry_intents": four_resting_intents},
                now_ts=now_u,
            )
        )
        self.assertFalse(
            _safe_to_restart(
                {"active_positions": {**kmia_positions, "LIVE_B1": fresh_b1}, "pending_entry_intents": {}},
                now_ts=now_u,
            )
        )


if __name__ == "__main__":
    unittest.main()
