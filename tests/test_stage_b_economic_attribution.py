"""
Unit & Integration Tests for Stage B Institutional Economic Attribution, 6-Stage Opportunity Funnel,
Sub-Millisecond Competitor Decay Tracker, and Post-Fill Maker Markout Sampler.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.paa_os.optimizer import group_closed_positions_by_box
from src.paa_os.permissions import PermissionGate
from src.polymarket_research.economic_attribution_ledger import (
    CompetitorDecayTracker,
    MakerMarkoutSampler,
    classify_decay_bucket,
    compute_signed_markout_cents,
    compute_stage_b_attribution_report,
    emit_funnel_event,
    flush_stage_b_telemetry,
    load_external_cashflows_summary,
    register_candidate_funnel_and_decay_watch,
)


class TestStageBEconomicAttribution(unittest.TestCase):
    def test_zero_double_counting_and_exact_additive_identity(self) -> None:
        now_u = 1794114000.0  # Fixed UTC timestamp after 2026-11-04T02:05:00Z lock
        closed = [
            # 1. Fee-bearing D1 win with BOTH settled rebate ($0.05) and unsettled est rebate ($0.14)
            {
                "trade_id": "D1_WIN_1",
                "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "notional_usd": 19.60,
                "entry_shares": 20.0,
                "box_cost_net": 0.980,
                "fee_usd": 0.18,
                "paid_maker_rebate_usd": 0.05,
                "est_maker_rebate_usd": 0.14,  # MUST NOT be added to realized cash PnL
                "gas_usd": 0.01,
                "net_pnl_usd": 0.42,
                "entry_ts": now_u - 900.0,
                "exit_ts": now_u - 300.0,
                "close_reason": "BOX_MULTI_LEG_SETTLED",
            },
            # 2. 0%-fee BOND1 carry win with paid liquidity reward
            {
                "trade_id": "BOND1_WIN_1",
                "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                "notional_usd": 29.72,
                "entry_shares": 30.0,
                "hold_to_maturity_lock": True,
                "fee_usd": 0.0,
                "paid_liquidity_reward_usd": 0.03,
                "net_pnl_usd": 0.31,
                "entry_ts": now_u - 7200.0,
                "exit_ts": now_u - 1800.0,
                "close_reason": "SETTLED_WIN",
            },
            # 3. Benign flat merge ($0.00 PnL -> counted in flat_merges, not wins/losses)
            {
                "trade_id": "MERGE_FLAT_1",
                "sleeve": "PRE_SPLIT_OVERROUND_MACHINE_GUN",
                "notional_usd": 12.00,
                "fee_usd": 0.0,
                "net_pnl_usd": 0.0,
                "entry_ts": now_u - 600.0,
                "exit_ts": now_u - 525.0,
                "close_reason": "COMPLETE_SET_ONCHAIN_MERGED",
            },
            # 4. Inline legged-out partial-basket unwind loss (-$0.11 net, with $0.02 paid rebate & $0.01 gas)
            {
                "trade_id": "D1_UNWIND_1_LEG_INLINE_UNWIND",
                "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "notional_usd": 9.85,
                "fee_usd": 0.04,
                "paid_maker_rebate_usd": 0.02,
                "gas_usd": 0.01,
                "net_pnl_usd": -0.11,
                "is_legged_out_residual": True,
                "entry_ts": now_u - 400.0,
                "exit_ts": now_u - 392.0,
                "close_reason": "D1_INLINE_LEGGED_OUT_UNWIND",
            },
            # 5. Pre-lock directional trade (excluded from pure-riskless totals, included in all-time)
            {
                "trade_id": "HIST_DIR_1",
                "sleeve": "SLEEVE_1_CORE_302",
                "notional_usd": 12.00,
                "fee_usd": 0.15,
                "net_pnl_usd": -3.50,
                "entry_ts": now_u - 500000.0,
                "exit_ts": now_u - 498000.0,
                "close_reason": "STOP_LOSS",
            },
        ]

        rep = compute_stage_b_attribution_report(
            grouped_closed=closed,
            active_positions={},
            reconciled_equity_usd=76.81,
            starting_lock_equity_usd=60.92,
            net_deposits_post_lock_usd=0.0,
            riskless_epoch_start_utc="2026-11-04T02:05:00Z",
            equity_24h_delta_usd=2.75,
            vm_hourly_cost_usd=0.0730,
            all_time_ai_cost_usd=0.25,
            daily_ai_cost_usd=0.05,
            accounting_discrepancy_usd=0.0,
            orphan_orders_count=0,
            paused_sleeves={"PRE_SPLIT_OVERROUND_MACHINE_GUN"},
            now_unix=now_u,
        )

        gov = rep["governing_identity"]
        kpis = rep["north_star_kpis"]
        pt = rep["portfolio_totals"]

        # Exact penny additive identity across pure-riskless sleeves (D1 + BOND1; PRE_SPLIT is paused; CORE_302 is directional)
        self.assertEqual(gov["internal_identity_gap_usd"], 0.0)
        self.assertEqual(kpis["kpi_10_internal_identity_gap_usd"], 0.0)
        self.assertAlmostEqual(pt["pure_riskless_net_pnl_usd"], 0.42 + 0.31 - 0.11, places=4)
        self.assertAlmostEqual(pt["all_time_reconciled_strategy_pnl_usd"] if "all_time_reconciled_strategy_pnl_usd" in pt else gov["all_time_reconciled_strategy_pnl_usd"], 0.62 - 3.50, places=4)

        # Unsettled rebates must NEVER leak into realized net PnL
        self.assertAlmostEqual(pt["pure_riskless_est_unsettled_rebates_usd"], 0.14, places=4)
        self.assertAlmostEqual(pt["pure_riskless_paid_rebates_usd"], 0.07, places=4)

        # Governing Wallet-to-Wallet identity: ($76.81 - $60.92 - $0.00) - prorated ops cost
        self.assertAlmostEqual(gov["wallet_equity_delta_usd"], 15.89, places=4)
        expected_net_econ = round(15.89 - gov["prorated_vm_infra_cost_usd"] - 0.25, 4)
        self.assertAlmostEqual(gov["net_economic_pnl_usd"], expected_net_econ, places=4)
        self.assertEqual(kpis["kpi_4_partial_basket_unwind_count"], 1)
        self.assertGreater(kpis["kpi_4_partial_basket_unwind_loss_usd"], 0.0)

        # Flat merge recorded as flat_merges, not win/loss
        sl_map = {r["sleeve"]: r for r in rep["by_sleeve"]}
        self.assertEqual(sl_map["PRE_SPLIT_OVERROUND_MACHINE_GUN"]["flat_merges"], 1)
        self.assertEqual(sl_map["PRE_SPLIT_OVERROUND_MACHINE_GUN"]["trades"], 0)

    def test_box_grouping_parity_and_capital_hour_metrics(self) -> None:
        now_u = 1794114000.0
        raw_closed = [
            {
                "trade_id": "LEG_A_1",
                "box_id": "BOX_ETH_99",
                "box_partner_trade_id": "LEG_B_1",
                "is_dominance_box": True,
                "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "notional_usd": 9.60,
                "payout_usd": 20.00,
                "fee_usd": 0.10,
                "realized_exit_fee": 0.06,
                "net_pnl_usd": 10.24,
                "entry_shares": 20.0,
                "box_cost_net": 0.975,
                "entry_ts": now_u - 1800.0,
                "exit_ts": now_u - 900.0,
                "entry_time_utc": "2026-11-08T04:00:00Z",
                "settled_at_utc": "2026-11-08T04:15:00Z",
            },
            {
                "trade_id": "LEG_B_1",
                "box_id": "BOX_ETH_99",
                "box_partner_trade_id": "LEG_A_1",
                "is_dominance_box": True,
                "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "notional_usd": 9.90,
                "payout_usd": 0.0,
                "fee_usd": 0.08,
                "realized_exit_fee": 0.0,
                "net_pnl_usd": -9.98,
                "entry_shares": 20.0,
                "box_cost_net": 0.975,
                "entry_ts": now_u - 1800.0,
                "exit_ts": now_u - 900.0,
                "entry_time_utc": "2026-11-08T04:00:00Z",
                "settled_at_utc": "2026-11-08T04:15:00Z",
            },
            # Settled leg whose sibling is STILL OPEN in active_positions -> must be held back
            {
                "trade_id": "OPEN_BOX_LEG_A",
                "box_id": "BOX_OPEN_77",
                "box_partner_trade_id": "OPEN_BOX_LEG_B",
                "is_dominance_box": True,
                "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "notional_usd": 5.0,
                "net_pnl_usd": -5.0,
            },
        ]
        active = {
            "OPEN_BOX_LEG_B": {
                "trade_id": "OPEN_BOX_LEG_B",
                "box_id": "BOX_OPEN_77",
                "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                "remaining_cost_basis": 5.0,
                "entry_ts": now_u - 300.0,
            }
        }
        grouped = group_closed_positions_by_box(raw_closed, active)
        self.assertEqual(len(grouped), 1)

        rep = compute_stage_b_attribution_report(
            grouped_closed=grouped,
            active_positions=active,
            reconciled_equity_usd=77.10,
            starting_lock_equity_usd=60.92,
            now_unix=now_u,
        )
        self.assertEqual(rep["governing_identity"]["internal_identity_gap_usd"], 0.0)
        d1 = rep["by_sleeve"][0]
        self.assertEqual(d1["trades"], 1)
        self.assertEqual(d1["wins"], 1)
        self.assertEqual(d1["losses"], 0)
        # Verify realized_exit_fee ($0.06) was NOT double-counted after box collapse ($0.10 + $0.06 + $0.08 = $0.24)
        self.assertAlmostEqual(d1["taker_fees_usd"], 0.24, places=4)
        self.assertAlmostEqual(d1["net_pnl_usd"], 0.26, places=4)
        # Hold duration = 900s = 0.25h; notional = $19.50 -> occupied_capital_hours = 4.875 cap-hrs
        self.assertAlmostEqual(d1["occupied_capital_hours"], 19.50 * 0.25, places=3)
        self.assertAlmostEqual(d1["net_pnl_per_1000_usd"], round(1000.0 * 0.26 / 19.50, 2), places=2)
        self.assertAlmostEqual(d1["bps_per_capital_hour"], round(10000.0 * 0.26 / (19.50 * 0.25), 1), places=1)

    def test_competitor_decay_4_buckets_self_fill_suppression_and_rung2_gate(self) -> None:
        self.assertEqual(classify_decay_bucket(2.1), "lt_5ms")
        self.assertEqual(classify_decay_bucket(11.4), "5_15ms")
        self.assertEqual(classify_decay_bucket(27.8), "15_40ms")
        self.assertEqual(classify_decay_bucket(55.0), "gt_40ms")

        with tempfile.TemporaryDirectory() as tmp:
            t_dir = Path(tmp)
            f_path = t_dir / "opportunity_funnel.jsonl"
            trk = CompetitorDecayTracker()

            # Register 4 competitor-swept candidates across all 4 latency buckets + 1 self-filled candidate
            base_ns = 1_000_000_000_000
            cases = [
                ("CAND_LT5", "TOK_1", 2_400_000, "lt_5ms", 0.30),
                ("CAND_5_15", "TOK_2", 9_500_000, "5_15ms", 0.45),
                ("CAND_15_40", "TOK_3", 24_000_000, "15_40ms", 0.80),
                ("CAND_GT40", "TOK_4", 68_000_000, "gt_40ms", 0.50),
            ]
            for key, tok, delta_ns, exp_bkt, prof in cases:
                ok = trk.register_watch(
                    candidate_key=key,
                    sleeve="D1_SAME_ORACLE_DOMINANCE_BOX",
                    token_ids=(tok, f"{tok}_B"),
                    initial_asks={tok: 0.48, f"{tok}_B": 0.49},
                    max_sum_ask=0.985,
                    min_shares=5.0,
                    net_edge_bps=150.0,
                    est_profit_usd=prof,
                    detected_mono_ns=base_ns,
                )
                self.assertTrue(ok)
                fired = trk.on_top_of_book_tick(
                    tok,
                    0.52,  # Sum asks = 0.52 + 0.49 = 1.01 > 0.985 -> swept!
                    12.0,
                    now_mono_ns=base_ns + delta_ns,
                    dest_path=f_path,
                )
                self.assertEqual(len(fired), 1)
                self.assertEqual(fired[0]["decay_bucket"], exp_bkt)

            # Register self-filled candidate and suppress before book clears
            register_candidate_funnel_and_decay_watch(
                {
                    "box_id": "SELF_FILLED_BOX",
                    "sleeve_source": "D1_SAME_ORACLE_DOMINANCE_BOX",
                    "box_type": "DOMINANCE",
                    "asset": "BTC",
                    "leg_a_token_id": "TOK_SELF_A",
                    "leg_b_token_id": "TOK_SELF_B",
                    "leg_a_limit_price": 0.47,
                    "leg_b_limit_price": 0.50,
                    "box_cost_net": 0.975,
                    "net_paired_shares": 10.0,
                },
                dest_path=f_path,
                tracker=trk,
            )
            trk.mark_our_fill_or_cancel("SELF_FILLED_BOX")
            suppressed = trk.on_top_of_book_tick(
                "TOK_SELF_A", 0.55, 0.0, now_mono_ns=base_ns + 10_000_000, dest_path=f_path
            )
            self.assertEqual(suppressed, [])

            flush_stage_b_telemetry(timeout=2.0)
            rep_small = compute_stage_b_attribution_report(
                grouped_closed=[],
                data_dir=t_dir,
                eu_vm_monthly_delta_usd=12.0,
            )
            db_small = rep_small["opportunity_funnel"]["decay_buckets"]
            self.assertEqual(db_small["counts"], {"lt_5ms": 1, "5_15ms": 1, "15_40ms": 1, "gt_40ms": 1})
            self.assertEqual(db_small["gt_40ms_capturable_pct"], 25.0)
            self.assertFalse(db_small["rung2_migration_justified"])

            # Now simulate >= 25 decay observations over 2 days with >$60/mo projected 15-40ms missed profit
            synth_funnel = []
            for i in range(26):
                emit_ok = {
                    "ts_unix": 1794000000.0 + i * 3600.0,
                    "stage": "COMPETITOR_DECAY_OBSERVED",
                    "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                    "competitor_decay_ms": 22.5,
                    "decay_bucket": "15_40ms",
                    "est_profit_usd": 0.35,
                }
                synth_funnel.append(emit_ok)
            rep_rung2 = compute_stage_b_attribution_report(
                grouped_closed=[],
                funnel_records=synth_funnel,
                eu_vm_monthly_delta_usd=12.0,
            )
            self.assertTrue(rep_rung2["opportunity_funnel"]["decay_buckets"]["rung2_migration_justified"])

    def test_maker_markout_sampler_buy_and_sell_horizons(self) -> None:
        self.assertAlmostEqual(compute_signed_markout_cents("BUY", 0.50, 0.48), -2.0, places=3)
        self.assertAlmostEqual(compute_signed_markout_cents("SELL", 0.60, 0.57), 3.0, places=3)

        with tempfile.TemporaryDirectory() as tmp:
            t_dir = Path(tmp)
            m_path = t_dir / "maker_markouts.jsonl"
            sampler = MakerMarkoutSampler()

            books = {
                "TOK_BUY": {"bids": [{"price": "0.47", "size": "20"}], "asks": [{"price": "0.49", "size": "20"}]},
                "TOK_SELL": {"bids": [{"price": "0.56", "size": "20"}], "asks": [{"price": "0.58", "size": "20"}]},
            }
            ok_b = sampler.schedule_maker_fill(
                order_id="ORD_BUY_1",
                token_id="TOK_BUY",
                sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                side="BUY",
                fill_px=0.50,
                shares=10.0,
                book_lookup_fn=lambda tid: books.get(tid),
                mid_at_fill=0.50,
                horizons_sec=(0.02, 0.05, 0.08),
                dest_path=m_path,
            )
            ok_s = sampler.schedule_maker_fill(
                order_id="ORD_SELL_1",
                token_id="TOK_SELL",
                sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                side="SELL",
                fill_px=0.60,
                shares=10.0,
                book_lookup_fn=lambda tid: books.get(tid),
                mid_at_fill=0.60,
                horizons_sec=(0.02, 0.05, 0.08),
                dest_path=m_path,
            )
            self.assertTrue(ok_b)
            self.assertTrue(ok_s)

            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                flush_stage_b_telemetry(timeout=0.2)
                if m_path.exists() and len(m_path.read_text(encoding="utf-8").strip().splitlines()) >= 2:
                    break
                time.sleep(0.03)

            lines = [json.loads(x) for x in m_path.read_text(encoding="utf-8").strip().splitlines() if x.strip()]
            self.assertEqual(len(lines), 2)

            rep = compute_stage_b_attribution_report(grouped_closed=[], data_dir=t_dir)
            mm = rep["maker_markouts"]
            self.assertEqual(mm["samples_count"], 2)
            # BUY markout = -2.0c (-$0.20 adverse), SELL markout = +3.0c ($0.00 adverse) -> avg = +0.5c
            self.assertAlmostEqual(mm["avg_5s_cents"], 0.5, places=2)
            self.assertAlmostEqual(mm["adverse_markout_5s_usd"], -0.20, places=4)

    def test_command_center_probe_and_zero_trust_permission_gate(self) -> None:
        from scripts import dominus_command_center as dcc

        compile(dcc.REMOTE_PROBE_PY, "<remote_probe_stage_b>", "exec")
        self.assertIn("sec_stageb", dcc.HTML_PAGE)
        self.assertIn("renderStageBAttribution", dcc.HTML_PAGE)
        self.assertIn("stage_b_attribution", dcc.REMOTE_PROBE_PY)

        # Verify Zero-Trust PermissionGate diff inspection passes cleanly on Stage B modules
        gate = PermissionGate()
        stage_b_files = [
            "config/polymarket_external_cashflows.json",
            "src/polymarket_research/economic_attribution_ledger.py",
            "scripts/dominus_command_center.py",
            "tests/test_stage_b_economic_attribution.py",
        ]
        synth_diff_lines = []
        for rel in stage_b_files:
            txt = (REPO_ROOT / rel).read_text(encoding="utf-8")
            for ln in txt.splitlines():
                synth_diff_lines.append("+" + ln)
        ok_diff, violations = gate.inspect_candidate_diff(stage_b_files, "\n".join(synth_diff_lines))
        self.assertTrue(ok_diff, f"Stage B violated Zero-Trust PermissionGate: {violations}")

    def test_external_cashflows_deposit_reconciliation_zero_principal_inflation(self) -> None:
        cf_before = load_external_cashflows_summary(REPO_ROOT, since_utc="2026-11-08T17:15:00Z")
        self.assertEqual(cf_before["starting_lock_equity_usd"], 60.92)
        self.assertEqual(cf_before["net_deposits_post_lock_usd"], 20.00)
        self.assertEqual(cf_before["contributed_capital_basis_usd"], 80.92)
        self.assertEqual(cf_before["net_deposits_since_window_usd"], 20.00)

        # Once the 24h snapshot anchor moves past 17:14:25Z, net_deposits_since_window_usd drops to $0.00 seamlessly
        cf_after = load_external_cashflows_summary(REPO_ROOT, since_utc="2026-11-09T17:15:00Z")
        self.assertEqual(cf_after["net_deposits_since_window_usd"], 0.00)

        rep = compute_stage_b_attribution_report(
            grouped_closed=[],
            reconciled_equity_usd=97.58,
            starting_lock_equity_usd=cf_before["starting_lock_equity_usd"],
            net_deposits_post_lock_usd=cf_before["net_deposits_post_lock_usd"],
            now_unix=1794244800.0,
        )
        gid = rep["governing_identity"]
        self.assertEqual(gid["contributed_capital_basis_usd"], 80.92)
        self.assertEqual(gid["net_deposits_usd"], 20.00)
        self.assertAlmostEqual(gid["wallet_equity_delta_usd"], 16.66, places=2)
        self.assertAlmostEqual(rep["north_star_kpis"]["kpi_1_wallet_gain_before_ops_usd"], 16.66, places=2)


if __name__ == "__main__":
    unittest.main()
