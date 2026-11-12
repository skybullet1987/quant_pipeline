import asyncio
import json
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock


class TestV52DaytimeRisklessTurnover(unittest.TestCase):
    def test_01_null_volume_ghost_market_with_deep_competing_bid_rejected(self) -> None:
        """
        Regression test for the 2026-11-11 daytime stall:
        Gamma returns `volume24hr: None, volumeNum: None` on $0-volume tennis/esports sub-props
        where 0 shares exist on Polygon, yet automated bots post $198 competing bids (`200 sh @ $0.990`).
        Both `emit_single_leg_maker_lock_cand_impl` and `scan_uma_resolution_bonds` must reject $0-volume
        zero-ask ghost markets while admitting genuine traded riskless markets (`p_model = 1.0`).
        """
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            emit_single_leg_maker_lock_cand_impl,
        )

        now_ts = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            cand_sink = tmp_p / "d1_cands.jsonl"
            state_sink = tmp_p / "a124_state.json"

            class _DaemonStub:
                single_scan = False

                def __init__(self) -> None:
                    self._last_d1_live_emit_ts = {}
                    self._token_tick_sizes = {}

                def _can_emit_zero_loss_math_live(self, *args, **kwargs) -> bool:
                    return True

            stub = _DaemonStub()
            bk_opp = {"bids": [{"price": "0.001", "size": "100"}], "asks": [{"price": "0.004", "size": "100"}]}

            # $0-volume market with $198 competing buyer bid (`l1_bid_usd >= 75`) and empty asks -> MUST REJECT
            ghost_bk_win = {
                "bids": [{"price": "0.990", "size": "200.0"}],
                "asks": [],
                "_s2_meta": {
                    "volume24hr": 0.0,
                    "total_volume_usd": 0.0,
                    "question": "Challenger Lyon: Piros vs Tabur O/U 22.5",
                },
            }
            ok_ghost = emit_single_leg_maker_lock_cand_impl(
                stub,
                sleeve_source="BOND1_UMA_RESOLUTION_CARRY",
                asset="SPORTS_TOTAL",
                dedupe_key="BOND1_MKR_6942577",
                pair_dedupe_key="BOND1_6942577",
                token_id="tok_ghost_w",
                opp_token_id="tok_ghost_l",
                market_id="6942577",
                condition_id="0x" + "aa" * 32,
                side_label="NO",
                display_label="Ghost Tennis O/U",
                bk_win=ghost_bk_win,
                bk_opp=bk_opp,
                neg_risk=False,
                close_ts=now_ts + 1200.0,
                now_ts=now_ts,
                min_resting_bid=0.940,
                max_resting_bid=0.998,
                min_maker_edge=0.002,
                max_opp_bid=0.008,
                hold_to_maturity=True,
                p_model=1.0,
                target_bid_px=None,
                maker_rebate_ps=0.0,
                extract_best_bid_fn=a124_mod.extract_best_bid,
                cand_file=cand_sink,
                state_file=state_sink,
                default_cand_path=tmp_p / "prod_d1.jsonl",
                default_state_path=tmp_p / "prod_state.json",
            )
            self.assertFalse(ok_ghost)

            # Real $4,910-volume market (`volume24hr=None` after midnight rollover, `total_volume_usd=4910`) -> ACCEPTED!
            real_bk_win = {
                "bids": [{"price": "0.991", "size": "50.0"}],
                "asks": [],
                "_s2_meta": {
                    "volume24hr": 0.0,
                    "total_volume_usd": 4910.0,
                    "question": "NCAA Basketball: Duke vs UNC Moneyline",
                },
            }
            ok_real = emit_single_leg_maker_lock_cand_impl(
                stub,
                sleeve_source="BOND1_UMA_RESOLUTION_CARRY",
                asset="SPORTS_MONEYLINE",
                dedupe_key="BOND1_MKR_6961434",
                pair_dedupe_key="BOND1_6961434",
                token_id="tok_real_w",
                opp_token_id="tok_real_l",
                market_id="6961434",
                condition_id="0x" + "bb" * 32,
                side_label="YES",
                display_label="NCAA Duke YES",
                bk_win=real_bk_win,
                bk_opp=bk_opp,
                neg_risk=False,
                close_ts=now_ts + 1200.0,
                now_ts=now_ts,
                min_resting_bid=0.940,
                max_resting_bid=0.998,
                min_maker_edge=0.002,
                max_opp_bid=0.008,
                hold_to_maturity=True,
                p_model=1.0,
                target_bid_px=None,
                maker_rebate_ps=0.0,
                extract_best_bid_fn=a124_mod.extract_best_bid,
                cand_file=cand_sink,
                state_file=state_sink,
                default_cand_path=tmp_p / "prod_d1.jsonl",
                default_state_path=tmp_p / "prod_state.json",
            )
            self.assertTrue(ok_real)
            emitted_row = json.loads(cand_sink.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(emitted_row["p_model"], 1.0)
            self.assertAlmostEqual(emitted_row["total_volume_usd"], 4910.0)

            # End-to-end `scan_uma_resolution_bonds` with Gamma `volume24hr=None, volumeNum=None` vs `$5,200` volume
            cand_uma = tmp_p / "uma_cands.jsonl"
            d = a124_mod.Alpha124ShadowDaemon(single_scan=False)
            d.last_uma_discovery_ts = now_ts
            d.uma_proposed_markets = {
                "m_ghost": {
                    "id": "m_ghost",
                    "conditionId": "0xcond_ghost",
                    "question": "Challenger O/U 21.5?",
                    "negRisk": False,
                    "volume24hr": None,
                    "volumeNum": None,
                    "acceptingOrders": True,
                },
                "m_real": {
                    "id": "m_real",
                    "conditionId": "0xcond_real",
                    "question": "ATP Rome: Alcaraz vs Sinner winner?",
                    "negRisk": False,
                    "volume24hr": 5200.0,
                    "volumeNum": 5200.0,
                    "acceptingOrders": True,
                },
            }
            for mid_k, w_tok, l_tok in (("m_ghost", "tw_g", "tl_g"), ("m_real", "tw_r", "tl_r")):
                d.uma_onchain_cache[mid_k] = (
                    now_ts,
                    {
                        "verified": True,
                        "win_index": 0,
                        "win_token": w_tok,
                        "lose_token": l_tok,
                        "win_label": "YES",
                        "win_outcome_name": "Yes",
                        "domain": "SPORTS_MONEYLINE",
                        "oo_state": 1,
                        "proposer": "0xprop",
                        "expiration_ts": now_ts + 900.0,
                        "rem_challenge_sec": 900.0,
                        "proposal_age_sec": 6300.0,
                        "eff_liveness_sec": 7200.0,
                        "fee_rate": 0.0,
                        "fee_exponent": 1.0,
                    },
                )

            async def _fake_books(_toks, timeout=3.5):
                return {
                    "tw_g": {"bids": [{"price": "0.990", "size": "200"}], "asks": []},
                    "tl_g": {"bids": [{"price": "0.001", "size": "50"}], "asks": [{"price": "0.004", "size": "50"}]},
                    "tw_r": {"bids": [{"price": "0.992", "size": "60"}], "asks": []},
                    "tl_r": {"bids": [{"price": "0.001", "size": "50"}], "asks": [{"price": "0.004", "size": "50"}]},
                }

            d.entered_keys.update({"BOND1_m_ghost", "BOND1_m_real"})
            with (
                mock.patch.object(a124_mod, "D1_LIVE_CANDIDATES_FILE", cand_uma),
                mock.patch.object(a124_mod, "STATE_FILE", tmp_p / "st_uma.json"),
                mock.patch.object(a124_mod, "passes_uma_bond_dispute_guard", return_value=True),
                mock.patch.object(d, "fetch_books_batch", side_effect=_fake_books),
            ):
                asyncio.run(d.scan_uma_resolution_bonds([], now_ts=now_ts))

            uma_rows = [json.loads(ln) for ln in cand_uma.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertEqual([r["dedupe_key"] for r in uma_rows], ["BOND1_MKR_m_real"])

    def test_02_velocity_ranking_and_preemption_monotonic_in_real_holder_supply(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            score_live_candidate_velocity_ev,
            select_sll_velocity_preempt_target,
        )

        now_ts = 1_794_390_000.0
        sc_ghost = score_live_candidate_velocity_ev(
            {
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "box_cost_net": 0.990,
                "shares": 10,
                "expiry_ts": now_ts + 1200.0,
                "queue_ahead_usd": 0.0,
                "ask_depth_usd": 0.0,
                "volume_24h_usd": 0.0,
                "total_volume_usd": 0.0,
            },
            True,
            now_ts=now_ts,
        )
        sc_mid = score_live_candidate_velocity_ev(
            {
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "box_cost_net": 0.992,
                "shares": 10,
                "expiry_ts": now_ts + 1200.0,
                "queue_ahead_usd": 0.0,
                "ask_depth_usd": 0.0,
                "volume_24h_usd": 620.0,
                "total_volume_usd": 620.0,
            },
            True,
            now_ts=now_ts,
        )
        sc_high = score_live_candidate_velocity_ev(
            {
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "box_cost_net": 0.993,
                "shares": 10,
                "expiry_ts": now_ts + 1200.0,
                "queue_ahead_usd": 0.0,
                "ask_depth_usd": 35.0,
                "volume_24h_usd": 4910.0,
                "total_volume_usd": 4910.0,
            },
            True,
            now_ts=now_ts,
        )
        self.assertLess(sc_ghost, sc_mid)
        self.assertLess(sc_mid, sc_high)

        # Preemption check: a resting dry low-volume order (`effective_velocity_bps_hr=27.0`) at age 600s (>=540s)
        # CAN be upgraded by a real two-sided 220 bps/hr market, while a $0-volume ghost (`8 bps/hr`) CANNOT preempt anything.
        harv = types.SimpleNamespace(
            _maker_anchor_preempt_events={"BOND1_LOWVOL": threading.Event(), "BOND1_REAL": threading.Event()},
            _claimed_velocity_preempts=set(),
            active_positions={},
            pending_entry_intents={
                "I_LOW": {
                    "inflight_key": "BOND1_LOWVOL",
                    "live_maker_anchor_inflight": True,
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "anchor_bid_px": 0.991,
                    "expiry_ts": now_ts + 1800.0,
                    "matched_notional_usd": 0.0,
                    "ask_depth_usd": 0.0,
                    "volume_24h_usd": 380.0,
                    "effective_velocity_bps_hr": 27.0,
                    "fifo_rank1_verified": True,
                    "ts": now_ts - 600.0,
                },
                "I_REAL": {
                    "inflight_key": "BOND1_REAL",
                    "live_maker_anchor_inflight": True,
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "anchor_bid_px": 0.992,
                    "expiry_ts": now_ts + 1200.0,
                    "matched_notional_usd": 0.0,
                    "ask_depth_usd": 45.0,
                    "volume_24h_usd": 4910.0,
                    "effective_velocity_bps_hr": 264.0,
                    "fifo_rank1_verified": True,
                    "ts": now_ts - 600.0,
                },
            },
        )
        # Ghost candidate (8 bps/hr) cannot preempt anything
        self.assertEqual(
            select_sll_velocity_preempt_target(
                harv, 8.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now_ts, cand_sleeve="BOND1_UMA_RESOLUTION_CARRY"
            ),
            (0.0, ""),
        )
        # Real high-velocity market (220 bps/hr) preempts dry low-volume `BOND1_LOWVOL` after 600s (>= 540s)
        self.assertEqual(
            select_sll_velocity_preempt_target(
                harv, 220.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now_ts, cand_sleeve="BOND1_UMA_RESOLUTION_CARRY"
            ),
            (27.0, "BOND1_LOWVOL"),
        )

    def test_03_compute_sll_maker_keep_and_renew_caps_empty_ask_squatting(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            compute_sll_maker_keep_and_renew,
        )

        # Dry zero-ask <$500-vol book with 0 matched notional caps at 900s instead of renewing to 7200s
        mk_dry, dl_dry, _ = compute_sll_maker_keep_and_renew(
            "BOND1_UMA_RESOLUTION_CARRY",
            uws_ok=True,
            exp_ts=10_000.0,
            now_ts=1_000.0,
            created_mono=100.0,
            now_mono=950.0,
            deadline_mono=1_000.0,
            posted_px=0.992,
            cur_best_bid=0.992,
            buried_since_mono=None,
            has_active_asks=False,
            matched_notional_usd=0.0,
            volume_24h_usd=380.0,
        )
        self.assertAlmostEqual(mk_dry, 900.0)
        self.assertAlmostEqual(dl_dry, 1_000.0)  # origin_mono(100) + 900 = 1000 (no 2h squatting!)

        # Two-sided active market (`has_active_asks=True`) OR partial fill (`matched_notional_usd > 0`) still renews cleanly!
        mk_act, dl_act, _ = compute_sll_maker_keep_and_renew(
            "BOND1_UMA_RESOLUTION_CARRY",
            uws_ok=True,
            exp_ts=10_000.0,
            now_ts=1_000.0,
            created_mono=100.0,
            now_mono=1_600.0,
            deadline_mono=1_900.0,
            posted_px=0.992,
            cur_best_bid=0.992,
            buried_since_mono=None,
            has_active_asks=True,
            matched_notional_usd=0.0,
            volume_24h_usd=380.0,
        )
        self.assertAlmostEqual(mk_act, 1_800.0)
        self.assertAlmostEqual(dl_act, 2_500.0)

    def test_04_pure_riskless_and_kmia_non_interference_invariants_intact(self) -> None:
        from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER
        from src.polymarket_research.riskless_protocol_v2_expansion import is_post_expiry_uma_frozen_lock
        from src.polymarket_research.stage_c_zero_loss_velocity import (
            PURE_RISKLESS_ALLOWED_LIVE_SLEEVES,
            check_strict_pure_riskless_candidate_gate,
        )

        snap = GLOBAL_GOVERNANCE_MANAGER.snapshot
        self.assertTrue(bool(snap.get("directional", {}).get("riskless_only_mode")))
        self.assertTrue(bool(snap.get("riskless_boxes", {}).get("strict_pure_riskless_mode")))
        live_harv = types.SimpleNamespace(dry_run=False, executor=types.SimpleNamespace(client=object()))

        # Directional / lattice sleeves remain strictly barred
        for banned in ("SLEEVE_1_SUBHOURLY_15M", "SLEEVE_1_CORE_302", "SOC2_EXACT_SCORE_2D_LATTICE"):
            self.assertNotIn(banned, PURE_RISKLESS_ALLOWED_LIVE_SLEEVES)
            veto = check_strict_pure_riskless_candidate_gate(
                live_harv,
                {"sleeve_source": banned, "box_type": "SINGLE_LEG_MAKER_LOCK", "p_model": 0.92, "box_cost_net": 0.90},
                snap.get("riskless_boxes", {}),
                is_maker=True,
            )
            self.assertIsNotNone(veto)

        # Sub-1.0 `p_model` on post-clinch single-leg lock is strictly vetoed (`PURE_RISKLESS`)
        veto_sub1 = check_strict_pure_riskless_candidate_gate(
            live_harv,
            {
                "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "p_model": 0.995,
                "box_cost_net": 0.990,
            },
            snap.get("riskless_boxes", {}),
            is_maker=True,
        )
        self.assertIn("PURE_RISKLESS", str(veto_sub1))

        # Disputed KMIA post-expiry lock remains recognized as frozen (`D-001`)
        kmia_pos = {
            "market_id": "6707503",
            "sleeve": "WS_SNIPE_WEATHER",
            "is_single_leg_lock": True,
            "umaResolutionStatus": "disputed",
            "candle_expiry_ts": 1_794_050_000.0,
            "notional_usd": 12.60,
        }
        self.assertTrue(is_post_expiry_uma_frozen_lock(kmia_pos, 1_794_390_000.0))


if __name__ == "__main__":
    unittest.main()
