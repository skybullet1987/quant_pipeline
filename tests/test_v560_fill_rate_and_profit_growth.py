"""
v5.6.0 Riskless Fill-Rate, Profit-Growth & Production Bug-Fix Verification Suite.

Exercises end-to-end production code paths, boundary conditions, and adversarial inputs across:
  1. End-to-End `NR_M1_DEAD_SEED_OVERROUND` (`len(no_legs) == 1`) execution through
     `PolymarketLiveHarvester.maybe_execute_graduated_d1_box` (`nr2_pure_cash_bridge` fix)
     for ungraduated `TW1_COUNTING_TRUNCATION_AND_BOX` and `W_PRUNE1_DEAD_NO_BOND`, plus
     strict rejection of forged `nr_m1_zero_loss_verified=False` or `len(no_legs) == 0`.
  2. `_desired_market_ws_tokens` preserving resting Maker `pending_entry_intents` (`[tok_a, opp_a]`)
     and `_clinched_ws_watchlist` across 1.0s position supervision cycles (fixing the WS subscription
     wipe bug), plus sub-50ms `register_clinched_ws_watch_cand` -> `evaluate_clinched_ws_book_snipe`
     Partial-FAK sniping (`>= 5.0` shares) and dual-book / velocity / expiry vetoes.
  3. Pre-expiry Maker queue survival (`is_sll_pre_expiry_exempt` + `compute_sll_maker_keep_and_renew`)
     holding `W_PRUNE1_DEAD_NO_BOND`, `MKR_REWARD_LOCKED_CARRY`, `UMA_READY1_LIVENESS_PRIORITY`,
     and `MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER` (`posted_px >= 0.990`) through `TTE < 60s`, while
     preserving the `<= 60s` cancel on `< 0.990` `MKR_LOCK1` bids.
  4. Sticky `#1` FIFO Queue Protection (`eval_sll_live_book_poll` `_fifo_rank1_verified` tracking,
     `select_sll_velocity_preempt_target` `900s` hold unless `>= 8x` / `+400 bps/hr`, and
     configurable `_max_outbid_repegs=3` cap).
  5. Exact 2026 Maker Rebate Pool Shares (`0.25` Finance/Metals/Weather/Macro/Tweets, `0.20` Crypto
     incl. `ZEC`, `0.15` Sports/Esports), `compute_live_8e_clinch_max_eff_px`, and `0%`-fee Short-TTE
     `D1` `0.9925` walk ceiling (`XAU`/`XAG` `TTE <= 180s`) while preserving `0.985` on `7%`-fee Crypto.
  6. `MULTI_LEG_BUNDLE` Seed Capital-Velocity Hurdle enforcement inside `finish_protocol_v2_special_box_sync`
     (accepting `<= 8h` high-velocity bundles while blocking `72h` seed-freezing bundles) and strict
     governance bounds validation in `_deep_merge_validated`.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

for _opt_mod, _attrs in (
    ("dotenv", {"load_dotenv": lambda *a, **kw: False}),
    ("requests", {"Session": object, "get": None, "post": None}),
    ("httpx", {"AsyncClient": object, "Client": object}),
    ("urllib3", {}),
    ("urllib3.connection", {"HTTPConnection": type("HTTPConnection", (), {"default_socket_options": []})}),
):
    try:
        __import__(_opt_mod)
    except ModuleNotFoundError:
        _m = types.ModuleType(_opt_mod)
        for _k, _v in _attrs.items():
            setattr(_m, _k, _v)
        sys.modules[_opt_mod] = _m


class TestV560FillRateAndProfitGrowth(unittest.TestCase):
    def test_01_governance_additive_keys_and_strict_bounds_validation(self) -> None:
        from src.polymarket_research.holistic_strategy_governance import (
            DEFAULT_HOLISTIC_CONFIG,
            HotReloadConfigManager,
            _deep_merge_validated,
        )

        cfg_path = PROJECT_ROOT / "config" / "polymarket_strategy_and_risk.json"
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], "5.5.0")
        rb = raw["riskless_boxes"]
        self.assertAlmostEqual(float(rb["d1_short_tte_max_box_cost_net"]), 0.9925, places=4)
        self.assertAlmostEqual(float(rb["d1_short_tte_threshold_sec"]), 180.0, places=2)
        self.assertAlmostEqual(float(rb["sll_sticky_fifo_rank1_min_hold_sec"]), 900.0, places=2)
        self.assertEqual(int(rb["bond1_max_outbid_repegs"]), 3)
        self.assertTrue(bool(rb["enable_ws_clinch_sniper"]))
        self.assertEqual(int(rb["ws_clinch_watchlist_max_tokens"]), 900)

        mgr = HotReloadConfigManager(config_path=cfg_path)
        self.assertEqual(mgr.snapshot["riskless_boxes"]["bond1_max_outbid_repegs"], 3)

        # Adversarial out-of-bounds overrides must raise ValueError in _deep_merge_validated
        for bad_override in (
            {"d1_short_tte_max_box_cost_net": 1.02},
            {"d1_short_tte_threshold_sec": 9999.0},
            {"bond1_max_outbid_repegs": 0},
            {"ws_clinch_watchlist_max_tokens": 2000},
        ):
            with self.assertRaises(ValueError):
                _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, {"riskless_boxes": bad_override})

        merged = _deep_merge_validated(
            DEFAULT_HOLISTIC_CONFIG,
            {"riskless_boxes": {"sll_sticky_fifo_rank1_min_hold_sec": 600.0}},
        )
        self.assertAlmostEqual(float(merged["riskless_boxes"]["sll_sticky_fifo_rank1_min_hold_sec"]), 600.0, places=2)

        # HotReloadConfigManager must fail closed (preserving last valid snapshot) when disk JSON is out-of-bounds
        with tempfile.TemporaryDirectory() as tmp_cfg_dir:
            tmp_cfg = Path(tmp_cfg_dir) / "gov.json"
            tmp_cfg.write_text(json.dumps(raw), encoding="utf-8")
            mgr_tmp = HotReloadConfigManager(config_path=tmp_cfg)
            self.assertEqual(mgr_tmp.snapshot["riskless_boxes"]["bond1_max_outbid_repegs"], 3)
            bad_raw = json.loads(json.dumps(raw))
            bad_raw["riskless_boxes"]["d1_short_tte_max_box_cost_net"] = 1.05
            tmp_cfg.write_text(json.dumps(bad_raw), encoding="utf-8")
            mgr_tmp._last_check_mono = 0.0
            self.assertAlmostEqual(float(mgr_tmp.snapshot["riskless_boxes"]["d1_short_tte_max_box_cost_net"]), 0.9925, places=4)

    def test_02_maker_ws_subscription_preservation_and_sub50ms_clinch_sniper(self) -> None:
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

        now_ts = time.time()
        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.dry_run = False
        h._last_known_collateral = 65.0
        h.active_positions = {
            "POS_1": {"token_id": "111" * 9, "status": "POSITION_CONFIRMED", "notional_usd": 10.0}
        }
        h.pending_entry_intents = {
            "MKR_INT_1": {
                "token_id": "222" * 9,
                "opp_token_id": "333" * 9,
                "market_id": "9001",
                "live_maker_anchor_inflight": True,
                "notional_usd": 12.0,
            }
        }
        h._clinched_ws_watchlist = {}
        h._seen_d1_box_keys = set()
        h._d1_retry_cooldown_until = {}
        h._pos_market_ws = None

        # Register a clinched token watch (`p_model = 1.0`, `max_box_cost_net = 0.994`)
        ok_reg = h.register_clinched_ws_watch_cand(
            {
                "box_type": "CLINCH_WATCHLIST_REG",
                "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
                "asset": "NYC",
                "dedupe_key": "W_PRUNE_NO_5001",
                "leg_a_token_id": "444" * 9,
                "leg_a_opp_token_id": "555" * 9,
                "leg_a_market_id": "5001",
                "leg_a_condition_id": "0x" + "a" * 64,
                "leg_a_side": "NO",
                "leg_a_label": "NYC High 72-73F Dead NO",
                "leg_a_fee_rate": 0.0,
                "leg_a_fee_exponent": 1.0,
                "leg_a_neg_risk": True,
                "expiry_ts": now_ts + 3600.0,
                "max_box_cost_net": 0.994,
                "max_opp_bid": 0.020,
                "p_model": 1.0,
            },
            now_ts=now_ts,
        )
        self.assertTrue(ok_reg)

        # Verify 1s supervision desired tokens NEVER wipe resting Maker `[tok_a, opp_a]` or clinched watchlist tokens
        desired = h._desired_market_ws_tokens(now_ts=now_ts)
        self.assertIn("111" * 9, desired)
        self.assertIn("222" * 9, desired)
        self.assertIn("333" * 9, desired)
        self.assertIn("444" * 9, desired)
        self.assertIn("555" * 9, desired)

        # Adversarial: < 0.999 p_model must NEVER be registered on clinched WS watchlist
        bad_reg = h.register_clinched_ws_watch_cand(
            {
                "box_type": "CLINCH_WATCHLIST_REG",
                "sleeve_source": "W1_SOLAR_PEAK_LOCK",
                "leg_a_token_id": "666" * 9,
                "leg_a_opp_token_id": "777" * 9,
                "leg_a_market_id": "6001",
                "expiry_ts": now_ts + 3600.0,
                "p_model": 0.995,
            },
            now_ts=now_ts,
        )
        self.assertFalse(bad_reg)

        # Mock `_pos_market_ws` with shallow 6-share ($5.95) ask at $0.992 and opposite bid at $0.005
        ws_books = {
            "444" * 9: {
                "asks": [{"price": 0.992, "size": 6.0}],
                "bids": [{"price": 0.985, "size": 25.0}],
            },
            "555" * 9: {
                "asks": [{"price": 0.015, "size": 20.0}],
                "bids": [{"price": 0.005, "size": 10.0}],
            },
        }
        h._pos_market_ws = types.SimpleNamespace(
            get_book=lambda tid, max_age_s=1.5: ws_books.get(tid),
            set_desired_tokens=lambda toks: None,
        )

        # Case A: Adverse opposite bid (`0.030 > max_opp_bid=0.020`) must VETO snipe
        ws_books["555" * 9]["bids"] = [{"price": 0.030, "size": 10.0}]
        self.assertIsNone(h.evaluate_clinched_ws_book_snipe("444" * 9, now_ts=now_ts))

        # Case B: Sub-minimum depth (`4.0 < 5.0` shares) must VETO snipe
        ws_books["555" * 9]["bids"] = [{"price": 0.005, "size": 10.0}]
        ws_books["444" * 9]["asks"] = [{"price": 0.992, "size": 4.0}]
        self.assertIsNone(h.evaluate_clinched_ws_book_snipe("444" * 9, now_ts=now_ts))

        # Case C: Valid 6-share ($5.95) ask at $0.992 (`80 bps / 1h = 80 bps/hr >= 15 bps/hr`) synthesizes SINGLE_LEG_LOCK
        ws_books["444" * 9]["asks"] = [{"price": 0.992, "size": 6.0}]
        snipe_cand = h.evaluate_clinched_ws_book_snipe("444" * 9, now_ts=now_ts)
        self.assertIsNotNone(snipe_cand)
        assert snipe_cand is not None
        self.assertEqual(snipe_cand["box_type"], "SINGLE_LEG_LOCK")
        self.assertEqual(snipe_cand["sleeve_source"], "W_PRUNE1_DEAD_NO_BOND")
        self.assertEqual(snipe_cand["shares"], 6)
        self.assertAlmostEqual(float(snipe_cand["box_cost_net"]), 0.992, places=4)
        self.assertTrue(bool(snipe_cand["allow_partial_fak"]))
        self.assertIn("444" * 9, snipe_cand["ws_books"])

        # Immediate second WS tick within 1.5s throttle must return None (anti-spam)
        self.assertIsNone(h.evaluate_clinched_ws_book_snipe("444" * 9, now_ts=now_ts + 0.2))

    def test_03_pre_expiry_maker_exemption_and_sticky_fifo_rank1_protection(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            compute_sll_maker_keep_and_renew,
            eval_sll_live_book_poll,
            is_sll_pre_expiry_exempt,
            select_sll_velocity_preempt_target,
        )

        now_ts = 1_780_000_000.0
        exp_30s = now_ts + 30.0  # 30s before scheduled close (< 60s!)

        # 1. `W_PRUNE1_DEAD_NO_BOND`, `MKR_REWARD_LOCKED_CARRY`, `UMA_READY1_LIVENESS_PRIORITY` hold through TTE=30s
        for sl_ex in ("W_PRUNE1_DEAD_NO_BOND", "MKR_REWARD_LOCKED_CARRY", "UMA_READY1_LIVENESS_PRIORITY"):
            self.assertTrue(is_sll_pre_expiry_exempt(sl_ex, 0.985))
            _, _, cancel_near = compute_sll_maker_keep_and_renew(
                sl_ex, exp_ts=exp_30s, now_ts=now_ts, created_mono=100.0, now_mono=220.0, posted_px=0.985
            )
            self.assertFalse(cancel_near, f"{sl_ex} must not self-cancel at TTE=30s")

        # 2. `MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER`: exempt when `posted_px >= 0.990`, cancels at `<= 60s` when `< 0.990`
        _, _, cancel_hi = compute_sll_maker_keep_and_renew(
            "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
            exp_ts=exp_30s,
            now_ts=now_ts,
            created_mono=100.0,
            now_mono=160.0,
            posted_px=0.994,
        )
        self.assertFalse(cancel_hi)
        _, _, cancel_lo = compute_sll_maker_keep_and_renew(
            "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
            exp_ts=exp_30s,
            now_ts=now_ts,
            created_mono=100.0,
            now_mono=160.0,
            posted_px=0.961,
        )
        self.assertTrue(cancel_lo)

        # 3. `eval_sll_live_book_poll` sets `_fifo_rank1_verified = True` when at top-of-book with `ahead_q <= 5.0`
        #    and enforces `_max_outbid_repegs = 3`
        live_exp = time.time() + 3600.0
        cand_box = {
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "expiry_ts": live_exp,
            "p_model": 1.0,
            "min_maker_edge": 0.004,
            "_posted_notional_usd": 14.775,
            "_max_outbid_repegs": 3,
        }
        bk_rank1 = {
            "bids": [{"price": "0.985", "size": "15"}],  # our 15 shares alone -> ahead_q = 0 <= 5.0
            "asks": [{"price": "0.995", "size": "20"}],
        }
        bk_opp = {"bids": [{"price": "0.005", "size": "10"}], "asks": [{"price": "0.020", "size": "10"}]}
        act_r1, repeg_r1, _, _ = eval_sll_live_book_poll(
            bk_opp, bk_rank1, cand_box, 0.985, 0.940, 0.994, 0.010, 0.001,
            True, False, 0, 350.0, 15.0, live_exp, None, collat_usd=70.0,
        )
        self.assertEqual(act_r1, "OK")
        self.assertIsNone(repeg_r1)
        self.assertTrue(cand_box.get("_fifo_rank1_verified"))

        # Entering behind $500 whale (`ahead_q > 5.0`) -> `_fifo_rank1_verified = False`
        cand_box["_init_l1_q_usd"] = None
        bk_buried = {
            "bids": [{"price": "0.985", "size": "550"}],
            "asks": [{"price": "0.995", "size": "20"}],
        }
        eval_sll_live_book_poll(
            bk_opp, bk_buried, cand_box, 0.985, 0.940, 0.994, 0.010, 0.001,
            True, False, 0, 350.0, 15.0, live_exp, None, collat_usd=70.0,
        )
        self.assertFalse(cand_box.get("_fifo_rank1_verified"))

        # Outbid below cap (`repost_n_in=2 < 3`) repegs; AT cap (`repost_n_in=3 >= 3`) blocks repeg and marks BURIED
        bk_outbid = {
            "bids": [{"price": "0.986", "size": "25"}],
            "asks": [{"price": "0.995", "size": "20"}],
        }
        act_rp, px_rp, _, _ = eval_sll_live_book_poll(
            bk_opp, bk_outbid, cand_box, 0.985, 0.940, 0.994, 0.010, 0.001,
            True, False, 2, 350.0, 15.0, live_exp, None, collat_usd=70.0,
        )
        self.assertEqual(act_rp, "REPEG")
        self.assertAlmostEqual(float(px_rp or 0.0), 0.987, places=4)

        act_cap, px_cap, _, reason_cap = eval_sll_live_book_poll(
            bk_opp, bk_outbid, cand_box, 0.985, 0.940, 0.994, 0.010, 0.001,
            True, False, 3, 350.0, 15.0, live_exp, time.monotonic() - 20.0, collat_usd=70.0,
        )
        self.assertEqual(act_cap, "BURIED")
        self.assertIsNone(px_cap)
        self.assertIn("outbid", str(reason_cap))

        # 4. `select_sll_velocity_preempt_target` protects `fifo_rank1_verified=True` for `900s` against 4x velocity,
        #    allows `>= 8x` & `+400 bps/hr` override, and preempts non-rank1 (`fifo_rank1_verified=False`) normally!
        import threading

        harv_p = types.SimpleNamespace(
            _maker_anchor_preempt_events={"IK_R1": threading.Event()},
            _claimed_velocity_preempts=set(),
            active_positions={},
            pending_entry_intents={
                "INT_RANK1": {
                    "inflight_key": "IK_R1",
                    "live_maker_anchor_inflight": True,
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "anchor_bid_px": 0.994,  # 60 bps over 1.5h = 40.0 bps/hr
                    "expiry_ts": now_ts + 5400.0,
                    "notional_usd": 18.0,
                    "fifo_rank1_verified": True,
                    "ts": now_ts - 240.0,  # 240s >= 180s normal hold, but < 900s sticky Rank-1 hold!
                }
            },
        )
        # 4x (`160 bps/hr`) cannot evict `#1` FIFO rank within 900s
        _, ik_4x = select_sll_velocity_preempt_target(
            harv_p, 160.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now_ts, cand_sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"
        )
        self.assertEqual(ik_4x, "")
        # Extreme 12x (`480 bps/hr >= max(320, 440)`) CAN evict `#1` FIFO rank
        _, ik_12x = select_sll_velocity_preempt_target(
            harv_p, 480.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now_ts, cand_sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"
        )
        self.assertEqual(ik_12x, "IK_R1")
        # Non-rank1 (`fifo_rank1_verified=False`) IS evicted at 4x (`160 bps/hr`)
        harv_p.pending_entry_intents["INT_RANK1"]["fifo_rank1_verified"] = False
        _, ik_non_r1 = select_sll_velocity_preempt_target(
            harv_p, 160.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now_ts, cand_sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"
        )
        self.assertEqual(ik_non_r1, "IK_R1")

    def test_04_end_to_end_nr_m1_dead_seed_harvester_bridge_and_w_prune1_fanout(self) -> None:
        import src.polymarket_research.alpha_124_shadow_daemon as a124
        import src.polymarket_research.polymarket_live_harvester as hv_mod
        from src.polymarket_research.riskless_protocol_v2_expansion import detect_nr_m1_dead_seed_fanout
        from src.polymarket_research.tradfi_sports_zero_fee_engine import NegRiskConvertSlateSpec

        now_ts = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            st_file = tmp_p / "alpha124_shadow_state.json"
            cand_file = tmp_p / "nr_m1_cands.jsonl"
            st_file.write_text(
                json.dumps(
                    {
                        "by_sleeve": {
                            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                                "closed": 12,
                                "losses": 0,
                                "win_rate_pct": 100.0,
                                "realized_pnl_t1000_usd": 42.5,
                                "legging_adjusted_pnl_t1000_usd": 38.0,
                            },
                            # Ungraduated (0 closed) TW1 & W_PRUNE1 must bridge via `nr2_pure_cash_bridge`!
                            "TW1_COUNTING_TRUNCATION_AND_BOX": {"closed": 0, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 0.0},
                            "W_PRUNE1_DEAD_NO_BOND": {"closed": 0, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 0.0},
                        },
                        "by_d1_asset": {},
                    }
                ),
                encoding="utf-8",
            )

            spec = NegRiskConvertSlateSpec(
                event_id="88001",
                slug="nyc-high-temp-closed",
                title="NYC High Temp Closed NegRisk Slate",
                neg_risk_market_id="0x" + "ef" * 32,
                neg_risk_augmented=False,
                total_market_count=3,
                is_closed_convert_safe=True,
                end_ts=now_ts + 7200.0,
                brackets=[
                    {
                        "market_id": "880010",
                        "condition_id": "0x" + "11" * 32,
                        "question_id": "0x" + "11" * 32,
                        "question_index": 0,
                        "label": "70-71F (Dead)",
                        "yes_token": "1" * 28,
                        "no_token": "2" * 28,
                        "fee_rate": 0.0,
                        "fee_exponent": 1.0,
                    },
                    {
                        "market_id": "880011",
                        "condition_id": "0x" + "22" * 32,
                        "question_id": "0x" + "22" * 32,
                        "question_index": 1,
                        "label": "72-73F (Live Liquid Bid)",
                        "yes_token": "3" * 28,
                        "no_token": "4" * 28,
                        "fee_rate": 0.0,
                        "fee_exponent": 1.0,
                    },
                    {
                        "market_id": "880012",
                        "condition_id": "0x" + "33" * 32,
                        "question_id": "0x" + "33" * 32,
                        "question_index": 2,
                        "label": "74F or higher (Freeroll Tail)",
                        "yes_token": "5" * 28,
                        "no_token": "6" * 28,
                        "fee_rate": 0.0,
                        "fee_exponent": 1.0,
                    },
                ],
            )
            books = {
                "1" * 28: {"asks": [{"price": "0.02", "size": "50"}], "bids": []},
                "2" * 28: {"asks": [{"price": "0.975", "size": "40"}], "bids": [{"price": "0.970", "size": "40"}]},
                "3" * 28: {"asks": [{"price": "0.992", "size": "40"}], "bids": [{"price": "0.986", "size": "40"}]},
                "4" * 28: {"asks": [{"price": "0.03", "size": "40"}], "bids": []},
                "5" * 28: {"asks": [{"price": "0.05", "size": "40"}], "bids": [{"price": "0.01", "size": "40"}]},
                "6" * 28: {"asks": [{"price": "0.98", "size": "40"}], "bids": []},
            }
            m1_hit = detect_nr_m1_dead_seed_fanout(spec, {0}, books, fee_bips=0, min_shares=5.0, min_net_edge_usd=0.0035)
            self.assertIsNotNone(m1_hit)
            assert m1_hit is not None
            self.assertEqual(m1_hit["mode"], "NR_M1_DEAD_SEED_OVERROUND")
            self.assertTrue(m1_hit["nr_m1_zero_loss_verified"])

            with mock.patch.object(a124, "D1_LIVE_CANDIDATES_FILE", cand_file), mock.patch.object(
                hv_mod, "DATA_DIR", tmp_p
            ):
                d_nr = a124.Alpha124ShadowDaemon(single_scan=True)
                emitted_ok = d_nr.emit_live_negrisk_convert_candidate(
                    sleeve_source="W_PRUNE1_DEAD_NO_BOND",
                    spec=spec,
                    dedupe_key="NRM1_WPRUNE_88001_Q0",
                    arb_hit=m1_hit,
                    books_by_token=books,
                    now_ts=now_ts,
                    fee_bips=0,
                )
                self.assertTrue(emitted_ok)
                cand_m1 = json.loads(cand_file.read_text(encoding="utf-8").strip())
                self.assertEqual(len(cand_m1["no_legs"]), 1)
                self.assertTrue(cand_m1["nr_m1_zero_loss_verified"])

                h_nr = hv_mod.PolymarketLiveHarvester(
                    dry_run=True,
                    dynamic_sizing=True,
                    hold_to_maturity=False,
                    exit_policy="hold_98",
                    ticket_notional=16.50,
                    max_price_ceiling=0.82,
                    max_concurrent=4,
                    allow_cli_concurrency=True,
                )
                h_nr._last_known_collateral = 85.0
                h_nr.executor.get_market_book = lambda tid: books.get(tid, {"asks": [], "bids": []})

                # Previously failed at L6331 with `SLEEVE_NOT_YET_8_OF_8_GRADUATED:W_PRUNE1_DEAD_NO_BOND`!
                out_m1 = h_nr.maybe_execute_graduated_d1_box(cand_m1)
                self.assertTrue(out_m1["executed"], f"NR_M1 live bridge failed: {out_m1}")
                self.assertGreater(float(h_nr.closed_positions[-1]["net_pnl_usd"]), 0.05)

                # Adversarial: forged `nr_m1_zero_loss_verified=False` with 1 leg MUST be rejected immediately
                forged = dict(cand_m1, dedupe_key="FORGED_M1", nr_m1_zero_loss_verified=False)
                out_forged = h_nr.maybe_execute_graduated_d1_box(forged)
                self.assertFalse(out_forged["executed"])
                self.assertEqual(out_forged["reason"], "INVALID_NEGRISK_CONVERT_INVARIANTS")

    def test_05_2026_maker_rebates_and_zero_fee_short_tte_d1_cap(self) -> None:
        from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon

        # 1. Exact March 30, 2026 Maker Rebate Pool Shares
        self.assertAlmostEqual(Alpha124ShadowDaemon.resolve_2026_maker_rebate_share("XAU", "CM_U1_PYTH_CLOSE_LOCK"), 0.25)
        self.assertAlmostEqual(Alpha124ShadowDaemon.resolve_2026_maker_rebate_share("XAG", "CM_B2_PYTH_SESSION_NO_LOCK"), 0.25)
        self.assertAlmostEqual(Alpha124ShadowDaemon.resolve_2026_maker_rebate_share("NYC", "W_PRUNE1_DEAD_NO_BOND"), 0.25)
        self.assertAlmostEqual(Alpha124ShadowDaemon.resolve_2026_maker_rebate_share("ELONMUSK", "TW1_COUNTING_TRUNCATION_AND_BOX"), 0.25)
        self.assertAlmostEqual(Alpha124ShadowDaemon.resolve_2026_maker_rebate_share("BTC", "B4_TOUCHED_BARRIER_WICK_LOCK"), 0.20)
        self.assertAlmostEqual(Alpha124ShadowDaemon.resolve_2026_maker_rebate_share("ZEC", "U1_DAILY_UPDOWN_LOCK"), 0.20)
        self.assertAlmostEqual(Alpha124ShadowDaemon.resolve_2026_maker_rebate_share("NBA", "SP2_NBA_ENDGAME_LOCK"), 0.15)
        self.assertAlmostEqual(Alpha124ShadowDaemon.resolve_2026_maker_rebate_share("CS2", "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK"), 0.15)

        # 2. Velocity-aware 8E clinch max_eff_px
        self.assertAlmostEqual(Alpha124ShadowDaemon.compute_live_8e_clinch_max_eff_px(0.988, 0.999, 1800.0), 0.994)
        self.assertAlmostEqual(Alpha124ShadowDaemon.compute_live_8e_clinch_max_eff_px(0.988, 0.999, 7200.0), 0.992)
        self.assertAlmostEqual(Alpha124ShadowDaemon.compute_live_8e_clinch_max_eff_px(0.988, 0.998, 1800.0), 0.988)

        # 3. `0%`-fee Short-TTE `D1` (`XAU`/`XAG`) unlocks `0.9925` (`<= 180s`) & `0.990` (`> 180s`) while `7%`-fee Crypto stays `0.985`
        d = Alpha124ShadowDaemon(single_scan=True)
        self.assertAlmostEqual(d._d1_live_max_box_cost(zero_fee=False, rem_tte_sec=65.0), 0.985, places=4)
        self.assertAlmostEqual(d._d1_live_max_box_cost(zero_fee=True, rem_tte_sec=65.0), 0.9925, places=4)
        self.assertAlmostEqual(d._d1_live_max_box_cost(zero_fee=True, rem_tte_sec=240.0), 0.990, places=4)

    def test_06_multi_leg_bundle_seed_capital_velocity_enforcement(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import finish_protocol_v2_special_box_sync

        now_ts = time.time()
        t1, t2, t3 = "7" * 28, "8" * 28, "9" * 28
        books = {
            t1: {"asks": [{"price": "0.32", "size": "40"}], "bids": []},
            t2: {"asks": [{"price": "0.33", "size": "40"}], "bids": []},
            t3: {"asks": [{"price": "0.338", "size": "40"}], "bids": []},  # sum = 0.988 (120 bps edge)
        }
        snipe_calls = []

        def _place_fok(token_id: str, side: str, size: float, price: float, neg_risk: bool = True) -> dict:
            snipe_calls.append((token_id, size, price, neg_risk))
            return {"success": True, "size": size, "making_amount": round(size * price, 4), "fee_usd": 0.0}

        harv = types.SimpleNamespace(
            dry_run=False,
            _last_known_collateral=62.0,  # Seed equity (< $95) -> max lockup 8.0h, min 15.0 bps/hr
            max_exposure=100.0,
            active_positions={},
            closed_positions=[],
            pending_entry_intents={},
            executor=types.SimpleNamespace(
                get_market_book=lambda tid: books[tid],
                place_fok_order=_place_fok,
                invalidate_collateral_cache=lambda: None,
            ),
            save_state=lambda: None,
        )
        base_legs = [
            {"token_id": t1, "market_id": "301", "condition_id": "0x" + "1" * 64, "side": "YES", "neg_risk": False},
            {"token_id": t2, "market_id": "302", "condition_id": "0x" + "2" * 64, "side": "YES", "neg_risk": False},
            {"token_id": t3, "market_id": "303", "condition_id": "0x" + "3" * 64, "side": "NO", "neg_risk": False},
        ]

        # Adversarial: 72-hour lockup on $62 seed equity (`120 bps / 72h = 1.67 bps/hr`) MUST be blocked!
        out_slow = finish_protocol_v2_special_box_sync(
            harv,
            {
                "box_id": "ML_SLOW_72H",
                "box_type": "MULTI_LEG_BUNDLE",
                "sleeve_source": "FED1_CENTRAL_BANK_LP_BOX",
                "asset": "FOMC",
                "neg_risk": False,
                "expiry_ts": now_ts + 72.0 * 3600.0,
                "max_box_cost_net": 0.990,
                "legs": base_legs,
            },
            dedupe_k="FED1_3L_SLOW",
            retry_cd={},
            now_ts=now_ts,
            rcfg={},
            own_grad=False,
        )
        self.assertFalse(out_slow["executed"])
        self.assertIn("LOW_CAPITAL_VELOCITY_LONG_TTE", str(out_slow["reason"]).upper())
        self.assertEqual(len(snipe_calls), 0)

        # Valid: 4-hour lockup on $62 seed equity (`120 bps / 4h = 30.0 bps/hr >= 15.0 bps/hr`) EXECUTES cleanly!
        out_fast = finish_protocol_v2_special_box_sync(
            harv,
            {
                "box_id": "ML_FAST_4H",
                "box_type": "MULTI_LEG_BUNDLE",
                "sleeve_source": "COND1_MACRO_PARTITION_BOX",
                "asset": "OIL_SENATE",
                "neg_risk": False,
                "expiry_ts": now_ts + 4.0 * 3600.0,
                "max_box_cost_net": 0.990,
                "legs": base_legs,
            },
            dedupe_k="COND1_3L_FAST",
            retry_cd={},
            now_ts=now_ts,
            rcfg={},
            own_grad=False,
        )
        self.assertTrue(out_fast["executed"], f"Expected fast 4h MULTI_LEG_BUNDLE to execute, got: {out_fast}")
        self.assertEqual(len(snipe_calls), 3)

    def test_07_single_leg_lock_zero_fee_and_clinch_cap_end_to_end(self) -> None:
        import src.polymarket_research.polymarket_live_harvester as hv_mod

        now_ts = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            (tmp_p / "alpha124_shadow_state.json").write_text(
                json.dumps(
                    {
                        "by_sleeve": {
                            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                                "closed": 12,
                                "losses": 0,
                                "win_rate_pct": 100.0,
                                "realized_pnl_t1000_usd": 45.0,
                                "legging_adjusted_pnl_t1000_usd": 40.0,
                            },
                            "W_PRUNE1_DEAD_NO_BOND": {"closed": 0, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 0.0},
                            "SP2_NBA_ENDGAME_LOCK": {"closed": 0, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 0.0},
                            "TW1_COUNTING_TRUNCATION_AND_BOX": {"closed": 0, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 0.0},
                        },
                        "by_d1_asset": {},
                    }
                ),
                encoding="utf-8",
            )
            books = {
                "101" * 9: {"asks": [{"price": "0.994", "size": "25"}], "bids": [{"price": "0.990", "size": "25"}]},
                "102" * 9: {"asks": [{"price": "0.015", "size": "25"}], "bids": [{"price": "0.004", "size": "25"}]},
                "201" * 9: {"asks": [{"price": "0.993", "size": "25"}], "bids": [{"price": "0.989", "size": "25"}]},
                "202" * 9: {"asks": [{"price": "0.015", "size": "25"}], "bids": [{"price": "0.004", "size": "25"}]},
                "301" * 9: {"asks": [{"price": "0.9945", "size": "25"}], "bids": [{"price": "0.990", "size": "25"}]},
                "302" * 9: {"asks": [{"price": "0.015", "size": "25"}], "bids": [{"price": "0.003", "size": "25"}]},
            }
            with mock.patch.object(hv_mod, "DATA_DIR", tmp_p):
                h = hv_mod.PolymarketLiveHarvester(
                    dry_run=True,
                    dynamic_sizing=True,
                    hold_to_maturity=False,
                    exit_policy="hold_98",
                    ticket_notional=12.0,
                    max_price_ceiling=0.82,
                    max_concurrent=6,
                    allow_cli_concurrency=True,
                )
                h.dry_run = False
                h.holistic_v5_live_mode = True
                h._startup_reconciled = True
                h._last_known_collateral = 80.0
                h._wallet_token_balance = lambda tid: (0.0, True)
                h.executor.get_market_book = lambda tid: books.get(tid, {"asks": [], "bids": []})
                h.executor.get_token_tick_size = lambda tid, price_hint=None: 0.001
                h.executor.execute_snipe_order = lambda **kw: types.SimpleNamespace(
                    success=True,
                    size=round(kw["notional_usd"] / kw["target_price"], 4),
                    price=kw["target_price"],
                    notional_usd=kw["notional_usd"],
                    fee_usd=0.0,
                    order_id=f"OID_{kw['trade_id']}",
                    execution_status="MATCHED_PENDING_SETTLEMENT",
                    error="",
                    details={"trade_ids": ["TR_SLL"]},
                )

                # 1. 0%-fee SINGLE_LEG_LOCK (no leg_b_fee_rate key!) at 0.994 (TTE=1800s) must classify zero_fee_box=True and execute
                out_zf = h.maybe_execute_graduated_d1_box(
                    {
                        "box_id": "SLL_ZF_0994",
                        "box_type": "SINGLE_LEG_LOCK",
                        "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
                        "asset": "NYC",
                        "dedupe_key": "SLL_ZF_0994_K",
                        "shares": 10,
                        "box_cost_net": 0.994,
                        "max_box_cost_net": 0.996,
                        "ts_unix": now_ts,
                        "expiry_ts": now_ts + 1800.0,
                        "p_model": 1.0,
                        "leg_a_token_id": "101" * 9,
                        "leg_a_opp_token_id": "102" * 9,
                        "leg_a_market_id": "71001",
                        "leg_a_condition_id": "0x" + "a1" * 32,
                        "leg_a_side": "NO",
                        "leg_a_fee_rate": 0.0,
                        "leg_a_fee_exponent": 1.0,
                        "leg_a_neg_risk": True,
                    }
                )
                self.assertTrue(out_zf["executed"], f"0%-fee SLL at 0.994 failed: {out_zf}")

                # 2. Fee-bearing SP2_NBA_ENDGAME_LOCK (p_model=0.999, TTE=1800s) at 0.9932 <= 0.994 must execute
                out_sp2 = h.maybe_execute_graduated_d1_box(
                    {
                        "box_id": "SLL_SP2_0993",
                        "box_type": "SINGLE_LEG_LOCK",
                        "sleeve_source": "SP2_NBA_ENDGAME_LOCK",
                        "asset": "NBA",
                        "dedupe_key": "SLL_SP2_0993_K",
                        "shares": 10,
                        "box_cost_net": 0.9932,
                        "max_box_cost_net": 0.994,
                        "ts_unix": now_ts,
                        "expiry_ts": now_ts + 1800.0,
                        "p_model": 0.999,
                        "leg_a_token_id": "201" * 9,
                        "leg_a_opp_token_id": "202" * 9,
                        "leg_a_market_id": "71002",
                        "leg_a_condition_id": "0x" + "a2" * 32,
                        "leg_a_side": "YES",
                        "leg_a_fee_rate": 0.03,
                        "leg_a_fee_exponent": 1.0,
                        "leg_a_neg_risk": False,
                    }
                )
                self.assertTrue(out_sp2["executed"], f"Clinched SP2 SLL at 0.9932 failed: {out_sp2}")

                # 3. Adversarial: non-clinched (p_model=0.995) fee-bearing SP2 at 0.9932 (> 0.992) must be rejected
                out_bad = h.maybe_execute_graduated_d1_box(
                    {
                        "box_id": "SLL_SP2_NONCLINCH",
                        "box_type": "SINGLE_LEG_LOCK",
                        "sleeve_source": "SP2_NBA_ENDGAME_LOCK",
                        "asset": "NBA",
                        "dedupe_key": "SLL_SP2_NONCLINCH_K",
                        "shares": 10,
                        "box_cost_net": 0.9932,
                        "max_box_cost_net": 0.994,
                        "ts_unix": now_ts,
                        "expiry_ts": now_ts + 1800.0,
                        "p_model": 0.995,
                        "leg_a_token_id": "201" * 9,
                        "leg_a_opp_token_id": "202" * 9,
                        "leg_a_market_id": "71003",
                        "leg_a_condition_id": "0x" + "a3" * 32,
                        "leg_a_side": "YES",
                        "leg_a_fee_rate": 0.03,
                        "leg_a_fee_exponent": 1.0,
                        "leg_a_neg_risk": False,
                    }
                )
                self.assertFalse(out_bad["executed"])
                self.assertIn("SLEEVE_NOT_YET_8_OF_8_GRADUATED", str(out_bad["reason"]))

                # 4. Clinched TW1_COUNTING_TRUNCATION_AND_BOX (p_model=0.9999, 0.9945 <= 0.995) executes cleanly
                out_tw1 = h.maybe_execute_graduated_d1_box(
                    {
                        "box_id": "SLL_TW1_09945",
                        "box_type": "SINGLE_LEG_LOCK",
                        "sleeve_source": "TW1_COUNTING_TRUNCATION_AND_BOX",
                        "asset": "ELONMUSK",
                        "dedupe_key": "SLL_TW1_09945_K",
                        "shares": 10,
                        "box_cost_net": 0.9945,
                        "max_box_cost_net": 0.995,
                        "ts_unix": now_ts,
                        "expiry_ts": now_ts + 1800.0,
                        "p_model": 0.9999,
                        "leg_a_token_id": "301" * 9,
                        "leg_a_opp_token_id": "302" * 9,
                        "leg_a_market_id": "71004",
                        "leg_a_condition_id": "0x" + "a4" * 32,
                        "leg_a_side": "NO",
                        "leg_a_fee_rate": 0.0,
                        "leg_a_fee_exponent": 1.0,
                        "leg_a_neg_risk": True,
                    }
                )
                self.assertTrue(out_tw1["executed"], f"Clinched TW1 SLL at 0.9945 failed: {out_tw1}")

    def test_08_ws_clinch_sniper_mkr_lock1_and_mkr_reward_end_to_end_execution(self) -> None:
        import src.polymarket_research.polymarket_live_harvester as hv_mod

        now_ts = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            (tmp_p / "alpha124_shadow_state.json").write_text(
                json.dumps(
                    {
                        "by_sleeve": {
                            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                                "closed": 12,
                                "losses": 0,
                                "win_rate_pct": 100.0,
                                "realized_pnl_t1000_usd": 45.0,
                                "legging_adjusted_pnl_t1000_usd": 40.0,
                            },
                            "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER": {"closed": 0, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 0.0},
                            "MKR_REWARD_LOCKED_CARRY": {"closed": 0, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 0.0},
                        },
                        "by_d1_asset": {},
                    }
                ),
                encoding="utf-8",
            )
            ws_books = {
                "411" * 9: {"asks": [{"price": 0.993, "size": 7.0}], "bids": [{"price": 0.988, "size": 20.0}]},
                "412" * 9: {"asks": [{"price": 0.015, "size": 20.0}], "bids": [{"price": 0.004, "size": 10.0}]},
                "421" * 9: {"asks": [{"price": 0.993, "size": 7.0}], "bids": [{"price": 0.988, "size": 20.0}]},
                "422" * 9: {"asks": [{"price": 0.015, "size": 20.0}], "bids": [{"price": 0.004, "size": 10.0}]},
                "431" * 9: {"asks": [{"price": 0.995, "size": 7.0}], "bids": [{"price": 0.990, "size": 20.0}]},
                "432" * 9: {"asks": [{"price": 0.015, "size": 20.0}], "bids": [{"price": 0.003, "size": 10.0}]},
            }
            with mock.patch.object(hv_mod, "DATA_DIR", tmp_p):
                h = hv_mod.PolymarketLiveHarvester(
                    dry_run=True,
                    dynamic_sizing=True,
                    hold_to_maturity=False,
                    exit_policy="hold_98",
                    ticket_notional=12.0,
                    max_price_ceiling=0.82,
                    max_concurrent=6,
                    allow_cli_concurrency=True,
                )
                h.dry_run = False
                h.holistic_v5_live_mode = True
                h._startup_reconciled = True
                h._last_known_collateral = 65.0
                h._wallet_token_balance = lambda tid: (0.0, True)
                h._pos_market_ws = types.SimpleNamespace(
                    get_book=lambda tid, max_age_s=1.5: ws_books.get(tid),
                    set_desired_tokens=lambda toks: None,
                )
                h.executor.get_market_book = lambda tid: ws_books.get(tid, {"asks": [], "bids": []})
                h.executor.get_token_tick_size = lambda tid, price_hint=None: 0.001
                h.executor.execute_snipe_order = lambda **kw: types.SimpleNamespace(
                    success=True,
                    size=round(kw["notional_usd"] / kw["target_price"], 4),
                    price=kw["target_price"],
                    notional_usd=kw["notional_usd"],
                    fee_usd=0.0,
                    order_id=f"OID_{kw['trade_id']}",
                    execution_status="MATCHED_PENDING_SETTLEMENT",
                    error="",
                    details={"trade_ids": ["TR_WS"]},
                )

                for idx, (slv, tok_a, tok_b, p_m) in enumerate(
                    (
                        ("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "411" * 9, "412" * 9, 0.9995),
                        ("MKR_REWARD_LOCKED_CARRY", "421" * 9, "422" * 9, 1.0),
                    )
                ):
                    ok_w = h.register_clinched_ws_watch_cand(
                        {
                            "box_type": "SINGLE_LEG_MAKER_LOCK",
                            "sleeve_source": slv,
                            "asset": "XAU",
                            "dedupe_key": f"MKR_WS_{idx}",
                            "leg_a_token_id": tok_a,
                            "leg_a_opp_token_id": tok_b,
                            "leg_a_market_id": f"8200{idx}",
                            "leg_a_condition_id": "0x" + f"b{idx}" * 32,
                            "leg_a_side": "YES",
                            "leg_a_label": f"Clinched {slv}",
                            "leg_a_fee_rate": 0.0,
                            "leg_a_fee_exponent": 1.0,
                            "leg_a_neg_risk": False,
                            "expiry_ts": now_ts + 1800.0,
                            "max_box_cost_net": 0.994,
                            "max_opp_bid": 0.020,
                            "p_model": p_m,
                            "hold_to_maturity": True,
                        },
                        now_ts=now_ts,
                    )
                    self.assertTrue(ok_w)
                    snipe_c = h.evaluate_clinched_ws_book_snipe(tok_a, now_ts=now_ts)
                    self.assertIsNotNone(snipe_c)
                    assert snipe_c is not None
                    out_exec = h.maybe_execute_graduated_d1_box(snipe_c)
                    self.assertTrue(out_exec["executed"], f"WS clinch snipe failed for {slv}: {out_exec}")

                # Adversarial 0: MKR_LOCK1 with p_model=0.995 (< 0.999) MUST be rejected by maybe_execute_graduated_d1_box
                out_low_pm = h.maybe_execute_graduated_d1_box(
                    {
                        "box_id": "MKR_LOW_PM",
                        "box_type": "SINGLE_LEG_LOCK",
                        "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                        "asset": "XAU",
                        "dedupe_key": "MKR_LOW_PM_K",
                        "shares": 6,
                        "box_cost_net": 0.993,
                        "max_box_cost_net": 0.994,
                        "ts_unix": now_ts,
                        "expiry_ts": now_ts + 1800.0,
                        "p_model": 0.995,
                        "leg_a_token_id": "411" * 9,
                        "leg_a_opp_token_id": "412" * 9,
                        "leg_a_market_id": "82055",
                        "leg_a_condition_id": "0x" + "b5" * 32,
                        "leg_a_side": "YES",
                        "leg_a_fee_rate": 0.0,
                        "leg_a_fee_exponent": 1.0,
                        "leg_a_neg_risk": False,
                    }
                )
                self.assertFalse(out_low_pm["executed"])
                self.assertIn("SLEEVE_NOT_YET_8_OF_8_GRADUATED", str(out_low_pm["reason"]))

                # Adversarial 1: HTM 20-hour lockup on $65 Seed equity MUST be vetoed by passes_capital_velocity_hurdle
                ok_slow = h.register_clinched_ws_watch_cand(
                    {
                        "box_type": "SINGLE_LEG_MAKER_LOCK",
                        "sleeve_source": "MKR_REWARD_LOCKED_CARRY",
                        "asset": "XAU",
                        "dedupe_key": "MKR_WS_SLOW_20H",
                        "leg_a_token_id": "431" * 9,
                        "leg_a_opp_token_id": "432" * 9,
                        "leg_a_market_id": "82099",
                        "leg_a_condition_id": "0x" + "b9" * 32,
                        "leg_a_side": "YES",
                        "leg_a_fee_rate": 0.0,
                        "leg_a_fee_exponent": 1.0,
                        "leg_a_neg_risk": False,
                        "expiry_ts": now_ts + 20.0 * 3600.0,
                        "max_box_cost_net": 0.996,
                        "max_opp_bid": 0.020,
                        "p_model": 1.0,
                        "hold_to_maturity": True,
                    },
                    now_ts=now_ts,
                )
                self.assertTrue(ok_slow)
                self.assertIsNone(h.evaluate_clinched_ws_book_snipe("431" * 9, now_ts=now_ts))

                # Adversarial 2: TTE < 25.5s must not register or synthesize doomed <25s snipe candidates
                self.assertFalse(
                    h.register_clinched_ws_watch_cand(
                        {
                            "box_type": "CLINCH_WATCHLIST_REG",
                            "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
                            "leg_a_token_id": "441" * 9,
                            "leg_a_opp_token_id": "442" * 9,
                            "leg_a_market_id": "82100",
                            "expiry_ts": now_ts + 22.0,
                            "p_model": 1.0,
                        },
                        now_ts=now_ts,
                    )
                )

    def test_09_zerofee1_mergeable_c1_complete_set_7day_0994_end_to_end(self) -> None:
        import src.polymarket_research.alpha_124_shadow_daemon as a124
        import src.polymarket_research.polymarket_live_harvester as hv_mod

        now_ts = time.time()
        exp_7d = now_ts + 7.0 * 86400.0
        cid_shared = "0x" + "cd" * 32
        tok_yes = "511" * 9
        tok_no = "512" * 9
        books = {
            tok_yes: {"asks": [{"price": "0.497", "size": "60"}], "bids": [{"price": "0.492", "size": "60"}]},
            tok_no: {"asks": [{"price": "0.497", "size": "60"}], "bids": [{"price": "0.492", "size": "60"}]},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            cand_file = tmp_p / "zf1_c1.jsonl"
            (tmp_p / "alpha124_shadow_state.json").write_text(
                json.dumps(
                    {
                        "by_sleeve": {
                            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                                "closed": 12,
                                "losses": 0,
                                "win_rate_pct": 100.0,
                                "realized_pnl_t1000_usd": 45.0,
                                "legging_adjusted_pnl_t1000_usd": 40.0,
                            },
                            "C1_BINARY_COMPLETE_SET": {"closed": 0, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 0.0},
                        },
                        "by_d1_asset": {},
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(a124, "D1_LIVE_CANDIDATES_FILE", cand_file), mock.patch.object(
                hv_mod, "DATA_DIR", tmp_p
            ):
                d = a124.Alpha124ShadowDaemon(single_scan=True)
                ok_emit = d.emit_live_two_leg_box_candidate(
                    sleeve_source="C1_BINARY_COMPLETE_SET",
                    box_type="COMPLETE_SET",
                    asset="POLITICS",
                    dedupe_key="ZF1_C1_7D_99001",
                    leg_a={
                        "token_id": tok_yes,
                        "opp_token_id": tok_no,
                        "market_id": "99001",
                        "condition_id": cid_shared,
                        "side": "YES",
                        "label": "Geopolitics Binary YES",
                        "fee_rate": 0.0,
                        "fee_exponent": 1.0,
                        "neg_risk": False,
                    },
                    leg_b={
                        "token_id": tok_no,
                        "opp_token_id": tok_yes,
                        "market_id": "99001",
                        "condition_id": cid_shared,
                        "side": "NO",
                        "label": "Geopolitics Binary NO",
                        "fee_rate": 0.0,
                        "fee_exponent": 1.0,
                        "neg_risk": False,
                    },
                    bk_a=books[tok_yes],
                    bk_b=books[tok_no],
                    close_ts=exp_7d,
                    now_ts=now_ts,
                    max_box_cost_override=0.9955,
                )
                self.assertTrue(ok_emit, "7-day 0%-fee mergeable C1_BINARY_COMPLETE_SET at 0.994 must emit!")
                cand_c1 = json.loads(cand_file.read_text(encoding="utf-8").strip())
                self.assertAlmostEqual(float(cand_c1["max_box_cost_net"]), 0.9955, places=4)
                self.assertAlmostEqual(float(cand_c1["box_cost_net"]), 0.994, places=4)

                h = hv_mod.PolymarketLiveHarvester(
                    dry_run=True,
                    dynamic_sizing=True,
                    hold_to_maturity=False,
                    exit_policy="hold_98",
                    ticket_notional=15.0,
                    max_price_ceiling=0.82,
                    max_concurrent=6,
                    allow_cli_concurrency=True,
                )
                h.dry_run = False
                h._startup_reconciled = True
                h._last_known_collateral = 75.0
                h._wallet_token_balance = lambda tid: (0.0, True)
                h.executor.auth_mode = "AUTHENTICATED_L2"
                h.executor.signature_type = 2
                h.executor.get_market_book = lambda tid: books.get(tid, {"asks": [], "bids": []})
                h.executor.execute_atomic_dominance_box = lambda **kw: {
                    "success": True,
                    "shares": kw["shares"],
                    "net_paired_shares": kw["shares"],
                    "box_cost_net": 0.994,
                    "leg_1": {
                        "token_id": kw["leg_a_token_id"],
                        "matched_shares": kw["shares"],
                        "price": 0.497,
                        "fee_usd": 0.0,
                        "orderID": "OID_C1_YES",
                    },
                    "leg_2": {
                        "token_id": kw["leg_b_token_id"],
                        "matched_shares": kw["shares"],
                        "price": 0.497,
                        "fee_usd": 0.0,
                        "orderID": "OID_C1_NO",
                    },
                }

                out_c1 = h.maybe_execute_graduated_d1_box(cand_c1)
                self.assertTrue(out_c1["executed"], f"7-day mergeable ZEROFEE1 C1 execution failed: {out_c1}")

                # Adversarial: non-mergeable 2-condition DOMINANCE box at 7 days & 0.994 MUST still be blocked!
                non_merge = dict(
                    cand_c1,
                    box_id="NON_MERGE_7D",
                    dedupe_key="NON_MERGE_7D_K",
                    sleeve_source="D1_SAME_ORACLE_DOMINANCE_BOX",
                    box_type="DOMINANCE",
                    leg_b_condition_id="0x" + "ef" * 32,
                )
                out_nm = h.maybe_execute_graduated_d1_box(non_merge)
                self.assertFalse(out_nm["executed"])

    def test_10_nr_m1_complete_set_bundle_consolidation_seed_horizon_and_fok_reconcile(self) -> None:
        import audit_losing_trades as alt
        import src.polymarket_research.polymarket_live_harvester as hv_mod
        from src.polymarket_research.riskless_machine_gun_engine import (
            execute_negrisk_subset_convert_arb_impl,
            finish_nr2_subset_convert_arb,
        )

        now_ts = time.time()
        books = {
            "601" * 9: {"asks": [{"price": "0.970", "size": "40"}], "bids": [{"price": "0.965", "size": "40"}]},
            "611" * 9: {"asks": [{"price": "0.990", "size": "40"}], "bids": [{"price": "0.985", "size": "40"}]},
        }
        base_m1_cand = {
            "box_id": "NRM1_HOLD_SET_901",
            "box_type": "NEGRISK_CONVERT",
            "convert_mode": "NR_M1_DEAD_SEED_OVERROUND",
            "nr_m1_zero_loss_verified": True,
            "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
            "asset": "NYC",
            "dedupe_key": "NRM1_HOLD_SET_K",
            "neg_risk_market_id": "0x" + "aa" * 32,
            "fee_bips": 0,
            "shares": 10,
            "expiry_ts": now_ts + 7200.0,
            "no_legs": [
                {
                    "token_id": "601" * 9,
                    "no_token": "601" * 9,
                    "market_id": "9010",
                    "condition_id": "0x" + "10" * 32,
                    "question_index": 0,
                    "ask_vwap": 0.970,
                    "max_ask_price": 0.970,
                    "limit_price": 0.970,
                    "fee_rate": 0.0,
                    "fee_exponent": 1.0,
                }
            ],
            "liquid_yes_sells": [
                {
                    "yes_token": "611" * 9,
                    "market_id": "9011",
                    "condition_id": "0x" + "11" * 32,
                    "question_index": 1,
                    "bid_vwap": 0.985,
                    "min_bid_price": 0.985,
                    "fee_rate": 0.0,
                    "fee_exponent": 1.0,
                }
            ],
            "surviving_yes_legs": [
                {"yes_token": "611" * 9, "market_id": "9011", "condition_id": "0x" + "11" * 32, "question_index": 1, "label": "72-73F"},
                {"yes_token": "612" * 9, "market_id": "9012", "condition_id": "0x" + "12" * 32, "question_index": 2, "label": "74-75F"},
                {"yes_token": "613" * 9, "market_id": "9013", "condition_id": "0x" + "13" * 32, "question_index": 3, "label": "76F+"},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            with mock.patch.object(hv_mod, "DATA_DIR", tmp_p):
                h = hv_mod.PolymarketLiveHarvester(
                    dry_run=True,
                    dynamic_sizing=True,
                    hold_to_maturity=False,
                    exit_policy="hold_98",
                    ticket_notional=15.0,
                    max_price_ceiling=0.82,
                    max_concurrent=6,
                    allow_cli_concurrency=True,
                )
                h.dry_run = False  # Exercise real non-dry-run Seed equity ($75 < $95 -> 24h max_lockup_hours)
                h._last_known_collateral = 75.0
                h.executor.get_market_book = lambda tid: books.get(tid, {"asks": [], "bids": []})
                h.executor.invalidate_collateral_cache = lambda: None
                h.executor.release_inventory = lambda tid, sh: None

                # (a) 48-hour lockup on $75 Seed equity (> 24h tier horizon) MUST be rejected!
                slow_m1 = dict(base_m1_cand, expiry_ts=now_ts + 48.0 * 3600.0)
                out_slow = finish_nr2_subset_convert_arb(
                    h,
                    slow_m1,
                    sleeve_src="W_PRUNE1_DEAD_NO_BOND",
                    nrm_id="0x" + "aa" * 32,
                    dedupe_k="NRM1_SLOW_48H",
                    retry_cd={},
                    budget=15.0,
                    fee_bips=0,
                    exp_ts=slow_m1["expiry_ts"],
                    now_ts=now_ts,
                )
                self.assertFalse(out_slow["executed"])
                self.assertIn("LOW_CAPITAL_VELOCITY_LONG_TTE", str(out_slow["reason"]))

                # (b) Complete-set fallback (`held_guaranteed_complete_set=True`) consolidates 3 surviving YES legs
                #     into ONE winning MULTI_LEG_BUNDLE box (`+$0.30`, `won=True`, `0` forensic losses)!
                h.executor.execute_negrisk_subset_convert_arb = lambda **kw: {
                    "success": True,
                    "convert_id": kw["convert_id"],
                    "shares": 10.0,
                    "spent_usd": 9.70,
                    "payout_floor_usd": 10.0,
                    "yes_salvage_usd": 0.0,
                    "net_locked_profit_usd": 0.30,
                    "convert_executed": True,
                    "held_guaranteed_complete_set": True,
                    "held_surviving_yes_legs": [
                        {**dict(sv), "shares": 10.0} for sv in kw["surviving_yes_legs"]
                    ],
                }
                out_hold = finish_nr2_subset_convert_arb(
                    h,
                    base_m1_cand,
                    sleeve_src="W_PRUNE1_DEAD_NO_BOND",
                    nrm_id="0x" + "aa" * 32,
                    dedupe_k="NRM1_HOLD_2H",
                    retry_cd={},
                    budget=15.0,
                    fee_bips=0,
                    exp_ts=base_m1_cand["expiry_ts"],
                    now_ts=now_ts,
                )
                self.assertTrue(out_hold["executed"], f"NR_M1 complete-set fallback failed: {out_hold}")
                self.assertEqual(len(h.active_positions), 3)

                leg_ids = sorted(h.active_positions.keys())
                total_basis = sum(float(h.active_positions[k]["notional_usd"]) for k in leg_ids)
                self.assertAlmostEqual(total_basis, 9.70, places=4)
                for k in leg_ids:
                    p_sv = h.active_positions[k]
                    self.assertEqual(p_sv["box_type"], "MULTI_LEG_BUNDLE")
                    self.assertTrue(p_sv["is_dominance_box"])
                    self.assertFalse(p_sv["is_single_leg_lock"])
                    self.assertEqual(p_sv["box_id"], "NRM1_HOLD_SET_901")
                    self.assertEqual(p_sv["box_expected_legs"], 3)
                    p_sv["inventory_reconciled"] = True

                # Close 2 OTM legs ($0.00) and 1 ITM leg ($10.00): must produce 1 winning closed record (+$0.30)
                for otm_k in leg_ids[:2]:
                    otm_pos = h.active_positions[otm_k]
                    otm_pos["confirmed_realized_cash"] = 0.0
                    otm_pos["realized_exit_cash"] = 0.0
                    h._close_position(otm_k, otm_pos, status="RESOLVED", reason="MARKET_RESOLVED_LOSS", won=False)
                self.assertEqual(len(h.closed_positions), 0, "OTM bundle legs must fold into sibling, NEVER emit standalone losses!")

                itm_k = leg_ids[2]
                itm_pos = h.active_positions[itm_k]
                itm_pos["confirmed_realized_cash"] = 10.0
                itm_pos["realized_exit_cash"] = 10.0
                itm_pos["filled_exit_shares"] = 10.0
                h._close_position(itm_k, itm_pos, status="RESOLVED", reason="ONCHAIN_REDEMPTION", won=True)

                self.assertEqual(len(h.active_positions), 0)
                self.assertEqual(len(h.closed_positions), 1)
                closed_box = h.closed_positions[0]
                self.assertTrue(closed_box["won"])
                self.assertAlmostEqual(float(closed_box["net_pnl_usd"]), 0.30, places=2)

                # Verify autonomous forensic auditor (`audit_losing_trades.scan_trades`) reports ZERO losses!
                fake_live_state = {
                    "service_status": "active",
                    "state": {
                        "status": "RUNNING",
                        "risk_halt": False,
                        "active_positions": {},
                        "closed_positions": list(h.closed_positions),
                    },
                }
                with mock.patch.object(alt, "DATA_DIR", tmp_p), mock.patch.object(
                    alt, "AUDIT_STATE_FILE", tmp_p / "forensic_audit_state.json"
                ), mock.patch.object(
                    alt, "AUDIT_LEDGER_FILE", tmp_p / "forensic_audit_ledger.jsonl"
                ), mock.patch.object(
                    alt, "fetch_kraken_live_state", return_value=fake_live_state
                ):
                    scan_res = alt.scan_trades()
                    self.assertEqual(scan_res["status"], "ALL_GOOD")
                    self.assertEqual(scan_res["uninspected_losses_count"], 0)
                    self.assertEqual(scan_res["newly_cleared_wins"], 1)

        # (c) FOK SELL HTTP timeout after on-chain match (`get_onchain_erc1155_balance == 0.0`) reconciles as swept!
        class _TimeoutSellClient:
            def create_order(self, order_args, _opts=None):
                return {"side": order_args.side, "token_id": order_args.token_id, "price": order_args.price, "size": order_args.size}

            def post_order(self, signed, _order_type, *args):
                if signed["side"] == "BUY":
                    return {"orderID": "OID_BUY_NO0", "status": "matched", "takingAmount": str(signed["size"])}
                raise TimeoutError("CLOB HTTP read timed out after matching")

        fake_exec = types.SimpleNamespace(
            dry_run=False,
            is_authenticated=True,
            auth_mode="LIVE",
            client=_TimeoutSellClient(),
            quantize_order_price=lambda px, _tok, rounding=None: round(float(px), 3),
            get_token_tick_size=lambda _tok, price_hint=None: "0.001",
            get_token_neg_risk=lambda _tok, default=True: True,
            _extract_fok_matched_shares=lambda resp, req_sh: float(req_sh) if isinstance(resp, dict) and resp.get("orderID") else 0.0,
            get_token_balance=lambda _tok: 10.0,
            attempt_negrisk_convert_positions=lambda _nrm, _q_idxs, _sh, prefer_v2_pusd_adapter=True: {
                "success": True,
                "tx_hash": "0x" + "dd" * 32,
            },
            get_market_book=lambda tid: books.get(tid, {"asks": [], "bids": []}),
            get_onchain_erc1155_balance=lambda tok: 0.0,  # 0.0 shares left -> FOK SELL actually settled on-chain!
            invalidate_collateral_cache=lambda: None,
        )
        res_to = execute_negrisk_subset_convert_arb_impl(
            fake_exec,
            convert_id="NRM1_TIMEOUT_RECON",
            neg_risk_market_id="0x" + "aa" * 32,
            no_legs=base_m1_cand["no_legs"],
            shares=10.0,
            max_no_cost_per_share=0.972,
            liquid_yes_sells=base_m1_cand["liquid_yes_sells"],
            fee_bips=0,
            nr_m1_zero_loss_verified=True,
            nr_m1_mode="NR_M1_DEAD_SEED_OVERROUND",
            surviving_yes_legs=base_m1_cand["surviving_yes_legs"],
        )
        self.assertTrue(res_to["success"])
        self.assertFalse(res_to["held_guaranteed_complete_set"], "Settled FOK timeout must NOT double-register complete-set legs!")
        self.assertGreater(float(res_to["yes_sell_net_usd"]), 9.70)

    def test_11_deploy_manifest_completeness_and_sub_1mb_bundles(self) -> None:
        from scripts.deploy_polymarket_live import (
            DEPLOY_MANIFEST,
            REMOTE_PYTEST_GATE,
            verify_local_manifest,
        )

        manifest_set = set(DEPLOY_MANIFEST)
        for required_rel in (
            "polymarket_all_in_one.py",
            "polymarket_all_in_one.txt",
            "polymarket_alpha124_all_in_one.py",
            "polymarket_alpha124_all_in_one.txt",
            "systemd/polymarket-recorder.service",
            "scripts/bundle_polymarket_all_in_one.py",
            "scripts/bundle_polymarket_full_codebase.py",
            "tests/test_polymarket_wfo_5fixes.py",
            "tests/test_v50_holistic_overhaul.py",
            "tests/test_zero_trust_forensic_audit.py",
            "tests/test_v560_fill_rate_and_profit_growth.py",
        ):
            self.assertIn(required_rel, manifest_set)

        gate_set = set(REMOTE_PYTEST_GATE)
        for required_gate in (
            "tests/test_v50_holistic_overhaul.py",
            "tests/test_polymarket_wfo_5fixes.py",
            "tests/test_zero_trust_forensic_audit.py",
            "tests/test_v560_fill_rate_and_profit_growth.py",
        ):
            self.assertIn(required_gate, gate_set)
        self.assertTrue(
            gate_set.issubset(manifest_set),
            f"Every REMOTE_PYTEST_GATE suite must be in DEPLOY_MANIFEST; missing={sorted(gate_set - manifest_set)}",
        )

        validated = verify_local_manifest()
        self.assertEqual(len(validated), len(DEPLOY_MANIFEST))

        for bundle_name in ("polymarket_all_in_one.py", "polymarket_alpha124_all_in_one.py"):
            b_size = (PROJECT_ROOT / bundle_name).stat().st_size
            self.assertLess(b_size, 1_000_000, f"{bundle_name} exceeded 1,000,000-byte invariant: {b_size}")
            self.assertLess(b_size, 990_000, f"{bundle_name} lacks >=10 KB safety margin below 1 MB cap: {b_size}")

    def test_12_builder_hmac_sync_hook_and_v2_attribution_verify(self) -> None:
        import base64
        import os
        import threading
        from src.polymarket_research.polymarket_live_executor import (
            PolymarketLiveExecutor,
            encode_builder_code_bytes32_hex,
        )

        class _FakeSyncClobClient:
            def _l2_headers(self, method: str, endpoint: str, body=None, serialized_body=None):
                return {
                    "POLY_ADDRESS": "0x1111111111111111111111111111111111111111",
                    "POLY_SIGNATURE": "l2_sig",
                    "POLY_TIMESTAMP": "1760000123",
                    "POLY_API_KEY": "l2_key",
                    "POLY_PASSPHRASE": "l2_pass",
                }

        ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
        ex._thread_local = threading.local()
        ex.CLOB_HOST = "https://clob.polymarket.com"
        ex.funder_address = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9"
        ex.client = mock.MagicMock()
        self.assertFalse(ex._install_sync_client_builder_headers_hook(), "MagicMock client must not be wrapped")

        ex.client = _FakeSyncClobClient()
        self.assertTrue(ex._install_sync_client_builder_headers_hook())
        self.assertFalse(ex._install_sync_client_builder_headers_hook(), "Second install must be idempotent no-op")

        valid_secret = base64.urlsafe_b64encode(b"0123456789abcdef0123456789abcdef").decode("ascii").rstrip("=")
        b_uuid = "019d7eef-23df-75d3-b9ab-3150df68ad2b"
        env_valid = {
            "POLY_BUILDER_API_KEY": b_uuid,
            "POLY_BUILDER_SECRET": valid_secret,
            "POLY_BUILDER_PASSPHRASE": "builder_passphrase_hex",
            "POLY_BUILDER_CODE": "",
            "BUILDER_CODE": "",
        }
        with mock.patch.dict(os.environ, env_valid, clear=False):
            h_order = ex.client._l2_headers("POST", "/order", body={"a": 1}, serialized_body='{"a":1}')
            self.assertEqual(h_order.get("POLY_BUILDER_API_KEY"), b_uuid)
            self.assertEqual(h_order.get("POLY_BUILDER_TIMESTAMP"), "1760000123")
            self.assertEqual(h_order.get("POLY_BUILDER_PASSPHRASE"), "builder_passphrase_hex")
            expected_b = ex.build_relayer_builder_headers(
                api_key=b_uuid,
                secret=valid_secret + "=",
                passphrase="builder_passphrase_hex",
                method="POST",
                request_path="/order",
                body='{"a":1}',
                timestamp=1760000123,
            )
            self.assertEqual(h_order.get("POLY_BUILDER_SIGNATURE"), expected_b["POLY_BUILDER_SIGNATURE"])

            h_orders = ex.client._l2_headers("POST", "/orders", body=[{"a": 1}])
            self.assertIn("POLY_BUILDER_SIGNATURE", h_orders)

            h_get = ex.client._l2_headers("GET", "/data/orders")
            self.assertNotIn("POLY_BUILDER_SIGNATURE", h_get)

            seen_calls = []

            class _FakeSession:
                def __init__(self, status_clob: int = 200):
                    self.status_clob = status_clob

                def get(self, url: str, headers=None, timeout=None):
                    seen_calls.append((url, dict(headers or {}), timeout))
                    if "relayer-v2.polymarket.com" in url:
                        return types.SimpleNamespace(status_code=200, content=b'{"deployed":false}', text='{"deployed":false}', json=lambda: {"deployed": False})
                    if self.status_clob != 200:
                        return types.SimpleNamespace(status_code=self.status_clob, content=b'{"error":"bad"}', text='{"error":"bad"}', json=lambda: {"error": "bad"})
                    return types.SimpleNamespace(
                        status_code=200,
                        content=b'{"data":[{"id":"t1"}],"count":1}',
                        text='{"data":[{"id":"t1"}],"count":1}',
                        json=lambda: {"data": [{"id": "t1"}], "count": 1},
                    )

            ex._sync_session = _FakeSession(status_clob=200)
            res_v2 = ex.verify_builder_attribution_trades(limit=5, check_relayer=True)
            self.assertTrue(res_v2["ok"])
            self.assertFalse(res_v2["builder_code_configured"])
            self.assertTrue(res_v2["hmac_headers_armed"])
            self.assertTrue(res_v2["sync_client_hook_armed"])
            self.assertTrue(res_v2["relayer_v2_auth_ok"])
            self.assertEqual(res_v2["count"], 1)
            self.assertEqual(len(seen_calls), 2)
            self.assertIn("relayer-v2.polymarket.com/deployed?address=", seen_calls[0][0])
            self.assertIn("/builder/trades?builder_code=0x", seen_calls[1][0])
            self.assertIn("&limit=5", seen_calls[1][0])
            self.assertIn("POLY_BUILDER_SIGNATURE", seen_calls[1][1])

            ex._sync_session = _FakeSession(status_clob=503)
            res_err = ex.verify_builder_attribution_trades(limit=3, builder_code="dominus")
            self.assertFalse(res_err["ok"])
            self.assertEqual(res_err["status_code"], 503)
            self.assertTrue(res_err["builder_code_configured"])
            self.assertEqual(res_err["builder_code"], encode_builder_code_bytes32_hex("dominus"))

        with mock.patch.dict(
            os.environ,
            {"POLY_BUILDER_API_KEY": "", "BUILDER_API_KEY": "", "POLY_BUILDER_SECRET": "%%%invalid%%%", "POLY_BUILDER_PASSPHRASE": ""},
            clear=False,
        ):
            h_clean = ex.client._l2_headers("POST", "/order", serialized_body='{"a":1}')
            self.assertNotIn("POLY_BUILDER_SIGNATURE", h_clean)
            res_missing = ex.verify_builder_attribution_trades()
            self.assertFalse(res_missing["ok"])
            self.assertEqual(res_missing["reason"], "missing_or_invalid_builder_hmac_creds")

    def test_13_zero_undefined_globals_and_relayer_limiter(self) -> None:
        import ast
        import builtins
        import src.polymarket_research.riskless_protocol_v2_expansion as rpv2
        from src.polymarket_research.polymarket_live_executor import RelayerRateLimiter

        self.assertTrue(hasattr(rpv2, "GLOBAL_GOVERNANCE_MANAGER"))
        rl = RelayerRateLimiter(max_per_min=2, window_sec=60.0)
        ok1, _ = rl.allow_and_record(100.0)
        ok2, _ = rl.allow_and_record(101.0)
        ok3, retry3 = rl.allow_and_record(102.0)
        self.assertTrue(ok1 and ok2)
        self.assertFalse(ok3)
        self.assertGreater(retry3, 50.0)
        self.assertEqual(rl.recent_count(160.5), 1)
        self.assertEqual(rl.recent_count(161.0), 0)

        builtin_names = set(dir(builtins)) | {
            "__file__", "__name__", "__doc__", "__package__", "__spec__", "__annotations__", "WindowsError",
        }

        def _collect_targets(node: ast.AST, out_s: set) -> None:
            if isinstance(node, ast.Name):
                out_s.add(node.id)
            elif isinstance(node, (ast.Tuple, ast.List)):
                for elt in node.elts:
                    _collect_targets(elt, out_s)
            elif isinstance(node, ast.Starred):
                _collect_targets(node.value, out_s)

        def _find_undefined(py_file: Path) -> list:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            has_fut_ann = any(
                isinstance(s, ast.ImportFrom) and s.module == "__future__" and any(a.name == "annotations" for a in s.names)
                for s in tree.body
            )
            undef = []

            def _check_scope(nd: ast.AST, enc: list, is_cls: bool = False) -> None:
                bound: set = set()
                glob_d: set = set()
                has_star = False
                if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    ag = nd.args
                    for a in ag.posonlyargs + ag.args + ag.kwonlyargs:
                        bound.add(a.arg)
                    if ag.vararg:
                        bound.add(ag.vararg.arg)
                    if ag.kwarg:
                        bound.add(ag.kwarg.arg)
                elif isinstance(nd, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    for gen in nd.generators:
                        _collect_targets(gen.target, bound)
                body_ns = nd.body if hasattr(nd, "body") and isinstance(nd.body, list) else list(ast.iter_child_nodes(nd))
                stk = list(body_ns)
                while stk:
                    cur = stk.pop()
                    if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        bound.add(cur.name)
                        continue
                    if isinstance(cur, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                        continue
                    if isinstance(cur, ast.Global):
                        glob_d.update(cur.names)
                        continue
                    if isinstance(cur, ast.Nonlocal):
                        continue
                    if isinstance(cur, (ast.Import, ast.ImportFrom)):
                        for al in cur.names:
                            if al.name == "*":
                                has_star = True
                            else:
                                bound.add(al.asname or al.name.split(".")[0])
                        continue
                    if isinstance(cur, ast.ExceptHandler) and cur.name:
                        bound.add(cur.name)
                    elif isinstance(cur, ast.NamedExpr):
                        _collect_targets(cur.target, bound)
                    elif isinstance(cur, ast.Name) and isinstance(cur.ctx, ast.Store):
                        bound.add(cur.id)
                    stk.extend(ast.iter_child_nodes(cur))
                if has_star:
                    return
                vis = set(builtin_names)
                for sc in enc:
                    vis |= sc
                vis |= bound
                nxt = enc if is_cls else (enc + [bound])

                def _walk_loads(sub: ast.AST) -> None:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for dec in sub.decorator_list:
                            _walk_loads(dec)
                        for df in list(sub.args.defaults) + [d for d in sub.args.kw_defaults if d is not None]:
                            _walk_loads(df)
                        if not has_fut_ann:
                            if sub.returns:
                                _walk_loads(sub.returns)
                            for a in sub.args.posonlyargs + sub.args.args + sub.args.kwonlyargs + ([sub.args.vararg] if sub.args.vararg else []) + ([sub.args.kwarg] if sub.args.kwarg else []):
                                if a.annotation:
                                    _walk_loads(a.annotation)
                        _check_scope(sub, nxt, is_cls=False)
                        return
                    if isinstance(sub, ast.ClassDef):
                        for dec in sub.decorator_list:
                            _walk_loads(dec)
                        for b in sub.bases:
                            _walk_loads(b)
                        for kw in sub.keywords:
                            _walk_loads(kw)
                        _check_scope(sub, nxt, is_cls=True)
                        return
                    if isinstance(sub, ast.Lambda):
                        for df in list(sub.args.defaults) + [d for d in sub.args.kw_defaults if d is not None]:
                            _walk_loads(df)
                        _check_scope(sub, nxt, is_cls=False)
                        return
                    if isinstance(sub, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                        _walk_loads(sub.generators[0].iter)
                        _check_scope(sub, nxt, is_cls=False)
                        return
                    if isinstance(sub, ast.AnnAssign) and has_fut_ann:
                        if isinstance(sub.target, ast.Attribute):
                            _walk_loads(sub.target.value)
                        elif isinstance(sub.target, ast.Subscript):
                            _walk_loads(sub.target)
                        if sub.value:
                            _walk_loads(sub.value)
                        return
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        if sub.id not in vis and sub.id not in glob_d:
                            undef.append((sub.lineno, sub.id))
                        return
                    for ch in ast.iter_child_nodes(sub):
                        _walk_loads(ch)

                for st in body_ns:
                    _walk_loads(st)

            _check_scope(tree, [])
            return undef

        targets = sorted((PROJECT_ROOT / "src" / "polymarket_research").glob("*.py")) + [
            PROJECT_ROOT / "audit_losing_trades.py",
            PROJECT_ROOT / "scripts" / "deploy_polymarket_live.py",
            PROJECT_ROOT / "scripts" / "bundle_polymarket_all_in_one.py",
            PROJECT_ROOT / "scripts" / "bundle_polymarket_full_codebase.py",
        ]
        found_errors = {}
        for tp in targets:
            if tp.exists():
                u_list = _find_undefined(tp)
                if u_list:
                    found_errors[str(tp.relative_to(PROJECT_ROOT))] = u_list
        self.assertEqual(found_errors, {}, f"Undefined global names detected: {found_errors}")

    def test_14_reviewer_round3_bundle_closure_ws_preempt_and_nr2_fixes(self) -> None:
        import asyncio
        import importlib.util
        import os
        import symtable
        import audit_losing_trades as alt
        import src.polymarket_research.polymarket_live_harvester as hv_mod
        from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor, RelayerRateLimiter
        from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker
        from src.polymarket_research.riskless_machine_gun_engine import (
            execute_negrisk_subset_convert_arb_impl,
            finish_nr2_subset_convert_arb,
        )
        from src.polymarket_research.riskless_protocol_v2_expansion import maybe_preempt_mlk1_if_bond1_starved

        # 1. Bundle AST local-variable minifier MUST preserve nested closure captures & recursive helpers
        bundler_path = PROJECT_ROOT / "scripts" / "bundle_polymarket_all_in_one.py"
        if bundler_path.exists():
            spec_b = importlib.util.spec_from_file_location("_test_bundler_mod", bundler_path)
            assert spec_b is not None and spec_b.loader is not None
            b_mod = importlib.util.module_from_spec(spec_b)
            spec_b.loader.exec_module(b_mod)
            sample_src = (
                "from dataclasses import dataclass, field\n"
                "from typing import Any, Dict, Optional\n"
                "@dataclass\n"
                "class SampleOrderResult:\n"
                "    success: bool\n"
                "    confirmed_onchain: bool = False\n"
                "    details: Dict[str, Any] = field(default_factory=dict)\n"
                "    error: Optional[str] = None\n"
                "class DemoHook:\n"
                "    def install(self, client_obj):\n"
                "        orig_l2 = getattr(client_obj, '_l2_headers', None)\n"
                "        if orig_l2 is None:\n"
                "            return client_obj\n"
                "        seen_acc = []\n"
                "        def _wrapped_l2_headers(method_name, path_str, body=None):\n"
                "            base_headers = dict(orig_l2(method_name, path_str, body=body))\n"
                "            extra_hdrs = self.extra_headers(method_name, path_str)\n"
                "            base_headers.update(extra_hdrs)\n"
                "            return base_headers\n"
                "        def _walk_nested(items):\n"
                "            local_buf = []\n"
                "            for elem in items:\n"
                "                if isinstance(elem, list):\n"
                "                    _walk_nested(elem)\n"
                "                else:\n"
                "                    seen_acc.append(elem)\n"
                "                    local_buf.append(elem)\n"
                "            return len(local_buf)\n"
                "        client_obj._l2_headers = _wrapped_l2_headers\n"
                "        client_obj._walk = _walk_nested\n"
                "        return seen_acc\n"
                "    def extra_headers(self, m, p):\n"
                "        return {'X-Builder': f'{m}:{p}'}\n"
            )
            comp_src = b_mod.transform_module("demo_hook.py", sample_src)
            ns_exec: dict = {}
            exec(compile(comp_src, "demo_hook.py", "exec"), ns_exec)
            dc_inst = ns_exec["SampleOrderResult"](True, confirmed_onchain=True, details={"k": 1}, error="ok")
            self.assertTrue(dc_inst.confirmed_onchain)
            self.assertEqual(dc_inst.details, {"k": 1})
            self.assertEqual(dc_inst.error, "ok")
            cli_dummy = types.SimpleNamespace(_l2_headers=lambda m, p, body=None: {"Base": "1"})
            acc_out = ns_exec["DemoHook"]().install(cli_dummy)
            hdr_out = cli_dummy._l2_headers("POST", "/order", body="{}")
            self.assertEqual(hdr_out, {"Base": "1", "X-Builder": "POST:/order"})
            cli_dummy._walk([1, [2, 3]])
            self.assertEqual(acc_out, [1, 2, 3])

            exec_py = (PROJECT_ROOT / "src" / "polymarket_research" / "polymarket_live_executor.py").read_text(encoding="utf-8")
            comp_exec = "from __future__ import annotations\n" + b_mod.transform_module(
                "src/polymarket_research/polymarket_live_executor.py", exec_py
            )
            st_orig = symtable.symtable(exec_py, "orig_exec.py", "exec")
            st_comp = symtable.symtable(comp_exec, "comp_exec.py", "exec")

            def _hook_nested_frees(st_mod) -> list[int]:
                cls_e = next(c for c in st_mod.get_children() if c.get_name() == "PolymarketLiveExecutor")
                fn_h = next(c for c in cls_e.get_children() if c.get_name() == "_install_sync_client_builder_headers_hook")
                return [len(ch.get_frees()) for ch in fn_h.get_children() if isinstance(ch, symtable.Function)]

            self.assertEqual(_hook_nested_frees(st_orig), [2])
            self.assertEqual(_hook_nested_frees(st_comp), [2])

        # 2. Real `PolymarketClobMarketWsTracker`: fail closed on missing `opp_tok` & retain quiet dead-side WS book >15s
        now_ts = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            (tmp_p / "alpha124_shadow_state.json").write_text(
                json.dumps(
                    {
                        "by_sleeve": {
                            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                                "closed": 12,
                                "losses": 0,
                                "win_rate_pct": 100.0,
                                "realized_pnl_t1000_usd": 45.0,
                                "legging_adjusted_pnl_t1000_usd": 40.0,
                            },
                            "BOND1_UMA_RESOLUTION_CARRY": {
                                "closed": 12,
                                "losses": 0,
                                "win_rate_pct": 100.0,
                                "realized_pnl_t1000_usd": 35.0,
                                "legging_adjusted_pnl_t1000_usd": 35.0,
                            },
                        },
                        "by_d1_asset": {},
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(hv_mod, "DATA_DIR", tmp_p):
                h = hv_mod.PolymarketLiveHarvester(
                    dry_run=True,
                    dynamic_sizing=True,
                    hold_to_maturity=False,
                    exit_policy="hold_98",
                    ticket_notional=15.0,
                    max_price_ceiling=0.82,
                    max_concurrent=6,
                    allow_cli_concurrency=True,
                )
                h.dry_run = False
                h.holistic_v5_live_mode = True
                h._startup_reconciled = True
                h._last_known_collateral = 75.0
                h._wallet_token_balance = lambda tid: (0.0, True)

                real_ws = PolymarketClobMarketWsTracker()
                tok_win = "711" * 9
                tok_opp = "712" * 9
                h._pos_market_ws = real_ws
                self.assertTrue(
                    h.register_clinched_ws_watch_cand(
                        {
                            "box_type": "SINGLE_LEG_MAKER_LOCK",
                            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                            "asset": "BTC",
                            "dedupe_key": "BOND1_WS_711",
                            "leg_a_token_id": tok_win,
                            "leg_a_opp_token_id": tok_opp,
                            "leg_a_market_id": "MKT_BOND1_902",
                            "leg_a_condition_id": "0x" + "71" * 32,
                            "leg_a_side": "YES",
                            "leg_a_label": "BTC clinched above strike",
                            "leg_a_fee_rate": 0.0,
                            "leg_a_fee_exponent": 1.0,
                            "leg_a_neg_risk": False,
                            "expiry_ts": now_ts + 1800.0,
                            "max_box_cost_net": 0.994,
                            "max_opp_bid": 0.020,
                            "p_model": 1.0,
                            "hold_to_maturity": True,
                        },
                        now_ts=now_ts,
                    )
                )
                mono_now = time.monotonic()
                real_ws._apply_snapshot_locked(
                    tok_win,
                    [{"price": "0.988", "size": "25"}],
                    [{"price": "0.992", "size": "8"}],
                    mono_now,
                )
                # Missing `tok_opp` book on live WS MUST fail closed (`None`)
                self.assertIsNone(h.evaluate_clinched_ws_book_snipe(tok_win, now_ts=now_ts))

                # Quiet dead-side `tok_opp` book received 120s ago (>15s) with adverse 0.030 bid MUST veto
                real_ws._apply_snapshot_locked(
                    tok_opp,
                    [{"price": "0.030", "size": "15"}],
                    [{"price": "0.045", "size": "20"}],
                    mono_now - 120.0,
                )
                self.assertIsNone(h.evaluate_clinched_ws_book_snipe(tok_win, now_ts=now_ts))

                # Quiet dead-side `tok_opp` book received 120s ago with clean 0.004 bid MUST succeed & attach `ws_books`
                real_ws._apply_snapshot_locked(
                    tok_opp,
                    [{"price": "0.004", "size": "15"}],
                    [{"price": "0.045", "size": "20"}],
                    mono_now - 120.0,
                )
                snipe_b1 = h.evaluate_clinched_ws_book_snipe(tok_win, now_ts=now_ts)
                self.assertIsNotNone(snipe_b1)
                assert snipe_b1 is not None
                self.assertIn("ws_books", snipe_b1)
                self.assertIn(tok_opp, snipe_b1["ws_books"])

                # 3. `_finish_single_leg_lock` MUST NOT mass-cancel unrelated `#1` FIFO resting Maker orders across markets
                ev_other = asyncio.Event()
                ev_same = asyncio.Event()
                hb_now = time.time()
                h._maker_anchor_preempt_events = {"IK_OTHER": ev_other, "IK_SAME": ev_same}
                h._inflight_maker_anchor_keys = {"IK_OTHER", "IK_SAME"}
                h.pending_entry_intents = {
                    "INT_OTHER": {
                        "inflight_key": "IK_OTHER",
                        "market_id": "MKT_OTHER_901",
                        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                        "live_maker_anchor_inflight": True,
                        "notional_usd": 12.0,
                        "fifo_rank1_verified": True,
                        "ts": hb_now - 10.0,
                        "heartbeat_ts": hb_now,
                    },
                    "INT_SAME": {
                        "inflight_key": "IK_SAME",
                        "market_id": "MKT_BOND1_902",
                        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                        "live_maker_anchor_inflight": True,
                        "notional_usd": 12.0,
                        "ts": hb_now - 10.0,
                        "heartbeat_ts": hb_now,
                    },
                }

                def _fake_preempt(reason: str = "TACTICAL_PREEMPT", market_ids=None) -> int:
                    cnt = 0
                    for it_p in list(h.pending_entry_intents.values()):
                        if market_ids is None or str(it_p.get("market_id") or "") in market_ids:
                            ik_p = str(it_p["inflight_key"])
                            h._maker_anchor_preempt_events[ik_p].set()
                            h._inflight_maker_anchor_keys.discard(ik_p)
                            h.pending_entry_intents.pop(
                                next(k for k, v in h.pending_entry_intents.items() if v is it_p), None
                            )
                            cnt += 1
                    return cnt

                h._preempt_resting_maker_anchors = _fake_preempt
                h.executor.get_collateral_balance = lambda: 75.0
                h.executor.get_token_tick_size = lambda tid, price_hint=None: 0.001
                h.executor.execute_snipe_order = lambda **kw: types.SimpleNamespace(
                    success=True,
                    size=round(kw["notional_usd"] / kw["target_price"], 4),
                    price=kw["target_price"],
                    notional_usd=kw["notional_usd"],
                    fee_usd=0.0,
                    order_id=f"OID_{kw['trade_id']}",
                    execution_status="MATCHED_PENDING_SETTLEMENT",
                    error="",
                    details={"trade_ids": ["TR_B1_WS"]},
                )
                out_b1_ws = h.maybe_execute_graduated_d1_box(snipe_b1)
                self.assertTrue(out_b1_ws["executed"], f"BOND1 WS snipe execution failed: {out_b1_ws}")
                self.assertTrue(ev_same.is_set(), "Same-market resting Maker MUST be preempted")
                self.assertFalse(ev_other.is_set(), "Unrelated market #1 FIFO resting Maker MUST NOT be preempted by BOND1 SLL!")
                self.assertIn("INT_OTHER", h.pending_entry_intents)

                # 4. `maybe_preempt_mlk1_if_bond1_starved`: sticky FIFO rank-1 900s hold & single-clip fanout eviction
                ev_mlk_rank1 = asyncio.Event()
                ev_mlk_slow = asyncio.Event()
                ev_mlk_fast = asyncio.Event()
                h._maker_anchor_preempt_events = {
                    "IK_MLK_R1": ev_mlk_rank1,
                    "IK_MLK_SLOW": ev_mlk_slow,
                    "IK_MLK_FAST": ev_mlk_fast,
                }
                h.enforce_gatling_sizing = True
                h.active_positions.clear()
                h.pending_entry_intents = {
                    "MLK_R1": {
                        "inflight_key": "IK_MLK_R1",
                        "market_id": "MKT_MLK_1",
                        "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                        "live_maker_anchor_inflight": True,
                        "notional_usd": 12.0,
                        "anchor_bid_px": 0.992,
                        "expiry_ts": now_ts + 7200.0,
                        "fifo_rank1_verified": True,
                        "ts": now_ts - 120.0,
                    }
                }
                gsn = GLOBAL_GOVERNANCE_MANAGER.snapshot
                b1_gov = gsn.get("riskless_boxes", {})
                rcfg_sll = gsn.get("sleeves", {}).get("BOND1_UMA_RESOLUTION_CARRY", {})
                asyncio.run(
                    maybe_preempt_mlk1_if_bond1_starved(
                        h,
                        "BOND1_UMA_RESOLUTION_CARRY",
                        0.0,
                        14.0,
                        True,
                        True,
                        b1_gov,
                        rcfg_sll,
                        gsn,
                        0.0,
                        3600.0,
                        now_ts,
                        cand_bid_px=0.990,
                    )
                )
                self.assertFalse(ev_mlk_rank1.is_set(), "Sticky FIFO rank-1 MKR_LOCK1 (<900s) MUST NOT be evicted by modest BOND1!")

                # With two non-rank1 MKR_LOCK1 clips on Seed wallet ($75 < $150), fanout evicts ONLY the slowest single clip
                h.pending_entry_intents = {
                    "MLK_SLOW": {
                        "inflight_key": "IK_MLK_SLOW",
                        "market_id": "MKT_MLK_2",
                        "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                        "live_maker_anchor_inflight": True,
                        "notional_usd": 12.0,
                        "anchor_bid_px": 0.994,
                        "expiry_ts": now_ts + 7200.0,
                        "fifo_rank1_verified": False,
                        "ts": now_ts - 120.0,
                    },
                    "MLK_FAST": {
                        "inflight_key": "IK_MLK_FAST",
                        "market_id": "MKT_MLK_3",
                        "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                        "live_maker_anchor_inflight": True,
                        "notional_usd": 12.0,
                        "anchor_bid_px": 0.991,
                        "expiry_ts": now_ts + 7200.0,
                        "fifo_rank1_verified": False,
                        "ts": now_ts - 120.0,
                    },
                }

                async def _run_single_evict() -> None:
                    async def _clear_on_set() -> None:
                        await asyncio.sleep(0.01)
                        if ev_mlk_slow.is_set():
                            h.pending_entry_intents.pop("MLK_SLOW", None)

                    await asyncio.gather(
                        maybe_preempt_mlk1_if_bond1_starved(
                            h,
                            "BOND1_UMA_RESOLUTION_CARRY",
                            0.0,
                            30.0,
                            True,
                            True,
                            b1_gov,
                            rcfg_sll,
                            gsn,
                            0.0,
                            3600.0,
                            now_ts,
                            cand_bid_px=0.985,
                        ),
                        _clear_on_set(),
                    )

                asyncio.run(_run_single_evict())
                self.assertTrue(ev_mlk_slow.is_set(), "Slowest non-rank1 MKR_LOCK1 MUST be evicted when BOND1 is starved")
                self.assertFalse(ev_mlk_fast.is_set(), "Faster MKR_LOCK1 sibling MUST be preserved under Seed fanout!")

                # 5. NR2 Relayer V2 precheck, 24th-slot recycle reservation, and m>=2 unconverted NO MULTI_LEG_BUNDLE
                ex_rl = PolymarketLiveExecutor(dry_run=True)
                ex_rl.dry_run = False
                ex_rl.is_authenticated = True
                ex_rl.auth_mode = "AUTHENTICATED_L2"
                ex_rl.signature_type = 3
                ex_rl.funder = "0x" + "11" * 20
                ex_rl._relayer_rate_limiter = RelayerRateLimiter(max_per_min=3, window_sec=60.0)
                ex_rl._relayer_rate_limiter.allow_and_record()
                ex_rl._relayer_rate_limiter.allow_and_record()  # Now at 2/3 (max_per_min - 1)

                posted_relayer_bodies = []
                ex_rl._sync_session = types.SimpleNamespace(
                    post=lambda url, **kw: (
                        posted_relayer_bodies.append(url)
                        or types.SimpleNamespace(status_code=200, content=b'{"transactionHash":"0xabc","state":"STATE_MINED"}', json=lambda: {"transactionHash": "0xabc", "state": "STATE_MINED"})
                    )
                )
                ex_rl._rpc = lambda method, params: {"status": "0x1"}
                ex_rl.build_deposit_wallet_relayer_batch = lambda **kw: {"calls": []}
                ex_rl.build_relayer_builder_headers = lambda **kw: {"POLY_BUILDER_API_KEY": "k"}

                with mock.patch.dict(
                    os.environ,
                    {
                        "POLY_PRIVATE_KEY": "0x" + "22" * 32,
                        "POLY_BUILDER_API_KEY": "k",
                        "POLY_BUILDER_SECRET": "c2VjcmV0",
                        "POLY_BUILDER_PASSPHRASE": "p",
                    },
                    clear=False,
                ):
                    # Passive redemption at 2/3 MUST be deferred so 3rd slot stays reserved for post-fill recycle ops
                    tx_passive = ex_rl._submit_deposit_wallet_relayer_redemption(
                        pk="0x" + "22" * 32,
                        funder_cs=ex_rl.funder,
                        nonce=1,
                        calls=[{"to": "0x" + "33" * 20, "data": "0x00"}],
                        condition_id="0x" + "44" * 32,
                    )
                    self.assertIsNone(tx_passive)
                    self.assertEqual(len(posted_relayer_bodies), 0)
                    # Urgent post-fill `nrconv:` op MUST be permitted to consume the reserved 3/3 slot!
                    tx_urgent = ex_rl._submit_deposit_wallet_relayer_redemption(
                        pk="0x" + "22" * 32,
                        funder_cs=ex_rl.funder,
                        nonce=1,
                        calls=[{"to": "0x" + "33" * 20, "data": "0x00"}],
                        condition_id="nrconv:0x" + "55" * 32,
                    )
                    self.assertEqual(tx_urgent, "0xabc")
                    self.assertEqual(len(posted_relayer_bodies), 1)

                # Now at 3/3 cap: `execute_negrisk_subset_convert_arb_impl` MUST abort BEFORE posting any CLOB FOK orders!
                clob_orders_posted = []
                ex_rl.client = types.SimpleNamespace(
                    create_order=lambda *a, **kw: clob_orders_posted.append("CREATED"),
                    post_order=lambda *a, **kw: clob_orders_posted.append("POSTED"),
                )
                ex_rl.get_market_book = lambda tid: {"asks": [{"price": "0.65", "size": "30"}], "bids": [{"price": "0.64", "size": "30"}]}
                ex_rl.get_token_tick_size = lambda tid, price_hint=None: 0.01
                pre_abort = execute_negrisk_subset_convert_arb_impl(
                    ex_rl,
                    convert_id="NR2_RL_CAP",
                    neg_risk_market_id="0x" + "66" * 32,
                    no_legs=[
                        {"token_id": "801" * 9, "question_index": 0, "max_ask_price": 0.66, "limit_price": 0.66},
                        {"token_id": "802" * 9, "question_index": 1, "max_ask_price": 0.66, "limit_price": 0.66},
                        {"token_id": "803" * 9, "question_index": 2, "max_ask_price": 0.66, "limit_price": 0.66},
                    ],
                    shares=10,
                    max_no_cost_per_share=1.99,
                    fee_bips=0,
                )
                self.assertFalse(pre_abort["success"])
                self.assertEqual(pre_abort.get("stage"), "RELAYER_RATE_LIMIT_PRECHECK")
                self.assertEqual(clob_orders_posted, [])

                # Unconverted m=3 NO legs (`convert_executed=False`) MUST consolidate as MULTI_LEG_BUNDLE (`0` forensic losses)
                h.active_positions.clear()
                h.closed_positions.clear()
                h.pending_entry_intents.clear()
                h._inflight_maker_anchor_keys.clear()
                nr2_books = {
                    "801" * 9: {"asks": [{"price": "0.70", "size": "40"}], "bids": [{"price": "0.69", "size": "40"}]},
                    "802" * 9: {"asks": [{"price": "0.68", "size": "40"}], "bids": [{"price": "0.67", "size": "40"}]},
                    "803" * 9: {"asks": [{"price": "0.58", "size": "40"}], "bids": [{"price": "0.57", "size": "40"}]},
                }
                h.executor.get_market_book = lambda tid: nr2_books.get(tid, {"asks": [], "bids": []})
                h.executor.invalidate_collateral_cache = lambda: None
                h.executor.release_inventory = lambda tid, sh: None
                h.executor.execute_negrisk_subset_convert_arb = lambda **kw: {
                    "success": True,
                    "convert_id": kw["convert_id"],
                    "m_no_legs": 3,
                    "shares": 10.0,
                    "spent_usd": 19.60,
                    "payout_floor_usd": 20.00,
                    "net_locked_profit_usd": 0.40,
                    "convert_executed": False,
                    "leg_fills": [
                        {"token_id": "801" * 9, "market_id": "9801", "condition_id": "0x" + "81" * 32, "price": 0.70, "matched_shares": 10.0, "orderID": "O1"},
                        {"token_id": "802" * 9, "market_id": "9802", "condition_id": "0x" + "82" * 32, "price": 0.68, "matched_shares": 10.0, "orderID": "O2"},
                        {"token_id": "803" * 9, "market_id": "9803", "condition_id": "0x" + "83" * 32, "price": 0.58, "matched_shares": 10.0, "orderID": "O3"},
                    ],
                }
                nr2_cand = {
                    "box_id": "NR2_HOLD_NO_BUNDLE_99",
                    "box_type": "NEGRISK_CONVERT",
                    "sleeve_source": "NR2_SUBSET_NO_CONVERT",
                    "asset": "ETH",
                    "dedupe_key": "NR2_HOLD_NO_K",
                    "neg_risk_market_id": "0x" + "66" * 32,
                    "fee_bips": 0,
                    "shares": 10,
                    "expiry_ts": now_ts + 3600.0,
                    "no_legs": [
                        {"token_id": "801" * 9, "market_id": "9801", "condition_id": "0x" + "81" * 32, "question_index": 0, "ask_vwap": 0.70, "max_ask_price": 0.70, "limit_price": 0.70},
                        {"token_id": "802" * 9, "market_id": "9802", "condition_id": "0x" + "82" * 32, "question_index": 1, "ask_vwap": 0.68, "max_ask_price": 0.68, "limit_price": 0.68},
                        {"token_id": "803" * 9, "market_id": "9803", "condition_id": "0x" + "83" * 32, "question_index": 2, "ask_vwap": 0.58, "max_ask_price": 0.58, "limit_price": 0.58},
                    ],
                }
                out_nr2 = finish_nr2_subset_convert_arb(
                    h,
                    nr2_cand,
                    sleeve_src="NR2_SUBSET_NO_CONVERT",
                    nrm_id="0x" + "66" * 32,
                    dedupe_k="NR2_HOLD_NO_K",
                    retry_cd={},
                    budget=22.0,
                    fee_bips=0,
                    exp_ts=nr2_cand["expiry_ts"],
                    now_ts=now_ts,
                )
                self.assertTrue(out_nr2["executed"], f"NR2 fallback hold failed: {out_nr2}")
                self.assertEqual(len(h.active_positions), 3)
                no_ids = sorted(h.active_positions.keys())
                for nk in no_ids:
                    p_no = h.active_positions[nk]
                    self.assertEqual(p_no["box_type"], "MULTI_LEG_BUNDLE")
                    self.assertEqual(p_no["box_id"], "NR2_HOLD_NO_BUNDLE_99")
                    self.assertEqual(p_no["box_expected_legs"], 3)
                    self.assertTrue(p_no["is_dominance_box"])
                    self.assertFalse(p_no["is_single_leg_lock"])
                    p_no["inventory_reconciled"] = True

                # 1 NO leg resolves OTM ($0.00) and 2 NO legs resolve ITM ($10.00 + $10.00 = $20.00): net +$0.40, 0 losses!
                p0 = h.active_positions[no_ids[0]]
                p0["confirmed_realized_cash"] = 0.0
                p0["realized_exit_cash"] = 0.0
                h._close_position(no_ids[0], p0, status="RESOLVED", reason="MARKET_RESOLVED_LOSS", won=False)
                self.assertEqual(len(h.closed_positions), 0)

                for itm_nk in no_ids[1:]:
                    p_i = h.active_positions[itm_nk]
                    p_i["confirmed_realized_cash"] = 10.0
                    p_i["realized_exit_cash"] = 10.0
                    p_i["filled_exit_shares"] = 10.0
                    h._close_position(itm_nk, p_i, status="RESOLVED", reason="ONCHAIN_REDEMPTION", won=True)

                self.assertEqual(len(h.active_positions), 0)
                self.assertEqual(len(h.closed_positions), 1)
                self.assertTrue(h.closed_positions[0]["won"])
                self.assertAlmostEqual(float(h.closed_positions[0]["net_pnl_usd"]), 0.40, places=2)
                with (
                    mock.patch.object(alt, "DATA_DIR", tmp_p),
                    mock.patch.object(alt, "AUDIT_STATE_FILE", tmp_p / "forensic_audit_state.json"),
                    mock.patch.object(alt, "AUDIT_LEDGER_FILE", tmp_p / "forensic_audit_ledger.jsonl"),
                    mock.patch.object(
                        alt,
                        "fetch_kraken_live_state",
                        return_value={
                            "service_status": "active",
                            "state": {
                                "status": "RUNNING",
                                "risk_halt": False,
                                "active_positions": {},
                                "closed_positions": list(h.closed_positions),
                            },
                        },
                    ),
                ):
                    rep_nr2 = alt.scan_trades()
                self.assertEqual(rep_nr2["status"], "ALL_GOOD")
                self.assertEqual(rep_nr2["newly_cleared_wins"], 1)
                self.assertEqual(rep_nr2["uninspected_losses_count"], 0)

    def test_15_live_zero_fill_forensics_tick_poisoning_stalk_guard_and_clinch_makers(self) -> None:
        import asyncio
        import math
        from datetime import datetime, timezone
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
        from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker
        from src.polymarket_research.riskless_machine_gun_engine import is_reward_locked_carry_live_ready
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            compute_sll_and_carry_gatling_budget,
            emit_single_leg_maker_lock_cand_impl,
            eval_sll_fresh_book_and_peg,
            eval_sll_live_book_poll,
            prepare_sll_stalk_guard,
            record_sll_exit_cooldown,
            resolve_harvester_sll_tick_size,
            run_protocol_v2_daemon_scan,
        )

        now_ts = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            cand_p = tmp_p / "d1_live_box_candidates.jsonl"
            st_p = tmp_p / "alpha124_shadow_state.json"

            # 1. Pre-boundary 0.01 WS tick-size poisoning on clinched >= $0.96 S2 5m candles:
            #    Must strip stale `_token_tick_sizes[tok] == "0.01"` and step 1 mill to $0.991 (#1 FIFO, $0 queue ahead)
            #    instead of pegging $0.990 behind $57,934.80!
            tok_s2 = "9191919191919191919191919191919191919191"
            opp_s2 = "9292929292929292929292929292929292929292"
            live_dm_s2 = types.SimpleNamespace(
                single_scan=False,
                _last_d1_live_emit_ts={},
                _token_tick_sizes={tok_s2: "0.01"},
            )
            ok_s2 = emit_single_leg_maker_lock_cand_impl(
                live_dm_s2,
                sleeve_source="S2_RTDS_EXACT_TWAP_INTEGRATOR",
                asset="XRP",
                dedupe_key="S2MKR_XRP_5m_6709978",
                pair_dedupe_key="S2_XRP_5m_6709978",
                token_id=tok_s2,
                opp_token_id=opp_s2,
                market_id="6709978",
                condition_id="0x" + "78" * 32,
                side_label="YES",
                display_label="XRP 5m Up",
                bk_win={"bids": [{"price": "0.99", "size": "58520"}], "asks": []},
                bk_opp={"bids": [{"price": "0.001", "size": "1200"}], "asks": [{"price": "0.01", "size": "500"}]},
                neg_risk=False,
                close_ts=now_ts + 25.0,
                now_ts=now_ts,
                min_resting_bid=0.900,
                max_resting_bid=0.997,
                min_maker_edge=0.0025,
                max_opp_bid=0.025,
                hold_to_maturity=True,
                p_model=0.9999,
                target_bid_px=None,
                maker_rebate_ps=0.0004,
                extract_best_bid_fn=a124_mod.extract_best_bid,
                cand_file=cand_p,
                default_cand_path=cand_p,
                state_file=st_p,
                default_state_path=st_p,
            )
            self.assertTrue(ok_s2)
            row_s2 = json.loads(cand_p.read_text(encoding="utf-8").splitlines()[-1])
            self.assertAlmostEqual(float(row_s2["anchor_bid_px"]), 0.991, places=4)
            self.assertAlmostEqual(float(row_s2["leg_a_tick_size"]), 0.001, places=4)
            self.assertNotIn("leg_a_ws_tick_size", row_s2)
            self.assertTrue(bool(row_s2["queue_front"]))
            self.assertAlmostEqual(float(row_s2["queue_ahead_usd"]), 0.0, places=2)

            # Explicit minimum_tick_size="0.01" on non-subcent book still preserves 0.01 while stripping stale leg_a_ws_tick_size
            ok_s2_01 = emit_single_leg_maker_lock_cand_impl(
                live_dm_s2,
                sleeve_source="S2_RTDS_EXACT_TWAP_INTEGRATOR",
                asset="BNB",
                dedupe_key="S2MKR_BNB_5m_EXPLICIT_01",
                pair_dedupe_key="S2_BNB_5m_EXPLICIT_01",
                token_id=tok_s2,
                opp_token_id=opp_s2,
                market_id="6709979",
                condition_id="0x" + "79" * 32,
                side_label="YES",
                display_label="BNB 5m Up",
                bk_win={"minimum_tick_size": "0.01", "bids": [{"price": "0.97", "size": "800"}], "asks": [{"price": "0.99", "size": "40"}]},
                bk_opp={"bids": [{"price": "0.01", "size": "50"}], "asks": [{"price": "0.03", "size": "50"}]},
                neg_risk=False,
                close_ts=now_ts + 25.0,
                now_ts=now_ts,
                min_resting_bid=0.500,
                max_resting_bid=0.985,
                min_maker_edge=0.010,
                max_opp_bid=0.020,
                hold_to_maturity=True,
                p_model=0.999,
                target_bid_px=0.984,
                maker_rebate_ps=0.0,
                extract_best_bid_fn=a124_mod.extract_best_bid,
                cand_file=cand_p,
                default_cand_path=cand_p,
                state_file=st_p,
                default_state_path=st_p,
            )
            self.assertTrue(ok_s2_01)
            row_s2_01 = json.loads(cand_p.read_text(encoding="utf-8").splitlines()[-1])
            self.assertAlmostEqual(float(row_s2_01["anchor_bid_px"]), 0.98, places=4)
            self.assertAlmostEqual(float(row_s2_01["leg_a_tick_size"]), 0.01, places=4)
            self.assertNotIn("leg_a_ws_tick_size", row_s2_01)

            ex_tk = PolymarketLiveExecutor(dry_run=True)
            ws_tk = PolymarketClobMarketWsTracker(on_tick_size_change=ex_tk.update_ws_tick_size)
            ws_tk.set_desired_tokens([tok_s2])
            ws_tk.process_ws_payload(
                {
                    "event_type": "book",
                    "asset_id": tok_s2,
                    "tick_size": "0.01",
                    "bids": [{"price": "0.52", "size": "100"}],
                    "asks": [{"price": "0.53", "size": "100"}],
                }
            )
            # At >= 0.96 and <= 0.04 boundaries, stale WS 0.01 MUST return 0.0 to force SDK /tick-size verification
            self.assertAlmostEqual(
                resolve_harvester_sll_tick_size(
                    ex_tk, tok_s2, {"leg_a_tick_size": 0.001}, bk_win={"minimum_tick_size": "0.01"}, mkt_ws=ws_tk, real_clob=True, price_hint=0.991
                ),
                0.0,
                places=6,
            )
            self.assertAlmostEqual(
                resolve_harvester_sll_tick_size(
                    ex_tk, tok_s2, {"leg_a_tick_size": 0.001}, bk_win={"minimum_tick_size": "0.01"}, mkt_ws=ws_tk, real_clob=True, price_hint=0.040
                ),
                0.0,
                places=6,
            )
            # Away from sub-cent boundary (0.95), WS 0.01 returns 0.01 without redundant HTTP call
            self.assertAlmostEqual(
                resolve_harvester_sll_tick_size(
                    ex_tk, tok_s2, {"leg_a_tick_size": 0.01}, bk_win={"minimum_tick_size": "0.01"}, mkt_ws=ws_tk, real_clob=True, price_hint=0.950
                ),
                0.01,
                places=6,
            )
            # Once WS or SDK updates to 0.001, WS 0.001 wins immediately over stale REST 0.01
            ws_tk._tick_sizes[tok_s2] = 0.001
            self.assertAlmostEqual(
                resolve_harvester_sll_tick_size(
                    ex_tk, tok_s2, {"leg_a_tick_size": 0.01}, bk_win={"minimum_tick_size": "0.01"}, mkt_ws=ws_tk, real_clob=True, price_hint=0.991
                ),
                0.001,
                places=6,
            )

            # 2. Anti-stalker repeg guard & escalating exit cooldowns on automated penny-jumper markets
            h_stk = types.SimpleNamespace()
            c_clean = {"sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "p_model": 1.0, "min_maker_edge": 0.003}
            # (a) Undisturbed poll at t=5s after repeg (#1 FIFO intact): keeps _max_outbid_repegs=3 and 35s buried hold
            hold_clean = prepare_sll_stalk_guard(h_stk, "BOND1_MKR_CLEAN", c_clean, 1, 5.0, 3, 35.0, now_ts, is_outbid_now=False, buried_since_mono=None)
            self.assertEqual(c_clean["_max_outbid_repegs"], 3)
            self.assertAlmostEqual(hold_clean, 35.0, places=2)
            # (b) Already-buried poll (`buried_since_mono` set) does NOT retroactively mutate _max_outbid_repegs
            c_alr = {"sleeve_source": "BOND1_UMA_RESOLUTION_CARRY"}
            _ = prepare_sll_stalk_guard(h_stk, "BOND1_MKR_ALR", c_alr, 1, 5.0, 3, 35.0, now_ts, is_outbid_now=True, buried_since_mono=100.0)
            self.assertEqual(c_alr["_max_outbid_repegs"], 3)
            # (c) Sub-12s penny-jumper outbid after repeg #1 caps _max_outbid_repegs=1 and shortens buried hold to 12s
            c_stalk = {"sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "p_model": 1.0, "min_maker_edge": 0.003}
            hold_stalk = prepare_sll_stalk_guard(h_stk, "BOND1_MKR_6698646", c_stalk, 1, 4.5, 3, 35.0, now_ts, is_outbid_now=True, buried_since_mono=None)
            self.assertEqual(c_stalk["_max_outbid_repegs"], 1)
            self.assertTrue(bool(c_stalk.get("_fast_stalk_detected")))
            self.assertAlmostEqual(hold_stalk, 12.0, places=2)
            act_st, rp_st, bur_m, _ = eval_sll_live_book_poll(
                {"bids": [{"price": "0.001", "size": "100"}]},
                {"bids": [{"price": "0.995", "size": "200"}], "asks": []},
                c_stalk,
                posted_px=0.994,
                min_rb=0.985,
                max_rb=0.997,
                max_opp=0.008,
                tk_wf=0.001,
                enforce_b1_v53=True,
                is_s2_mkr=False,
                repost_n_in=1,
                b1_q_cap=350.0,
                b1_buried_s=hold_stalk,
                exp_ts=now_ts + 1800.0,
                buried_since_mono=None,
                collat_usd=75.58,
            )
            self.assertEqual(act_st, "OK")
            self.assertIsNone(rp_st)
            self.assertIsNotNone(bur_m)

            # (d) Cooldown escalation & decay
            self.assertAlmostEqual(record_sll_exit_cooldown(h_stk, "BOND1_ONCE", True, False, False, 0, now_ts), 45.0, places=2)
            self.assertAlmostEqual(record_sll_exit_cooldown(h_stk, "BOND1_MKR_6698646", True, False, False, 1, now_ts), 180.0, places=2)
            c_reenter = {"sleeve_source": "BOND1_UMA_RESOLUTION_CARRY"}
            hold_re = prepare_sll_stalk_guard(h_stk, "BOND1_MKR_6698646", c_reenter, 0, 1.0, 3, 35.0, now_ts + 185.0)
            self.assertEqual(c_reenter["_max_outbid_repegs"], 1)
            self.assertAlmostEqual(hold_re, 15.0, places=2)
            self.assertAlmostEqual(record_sll_exit_cooldown(h_stk, "BOND1_MKR_6698646", True, False, False, 0, now_ts + 200.0), 360.0, places=2)
            self.assertAlmostEqual(record_sll_exit_cooldown(h_stk, "BOND1_MKR_6698646", True, False, False, 0, now_ts + 600.0), 720.0, places=2)
            self.assertAlmostEqual(record_sll_exit_cooldown(h_stk, "BOND1_MKR_6698646", True, False, False, 0, now_ts + 1350.0), 720.0, places=2)
            # Decay after >1800s back to 45s on clean single buried exit
            self.assertAlmostEqual(record_sll_exit_cooldown(h_stk, "BOND1_MKR_6698646", True, False, False, 0, now_ts + 3300.0), 45.0, places=2)
            # S2 fast-gun never records stalk strikes
            self.assertAlmostEqual(record_sll_exit_cooldown(h_stk, "S2MKR_BTC", True, False, True, 1, now_ts), 45.0, places=2)
            self.assertAlmostEqual(record_sll_exit_cooldown(h_stk, "S2MKR_BTC", False, False, True, 0, now_ts), 2.0, places=2)
            # Fresh-book outbid-above-cap cooldown escalates from 30s (initial) to 180s (after repeg)
            veto_0, cd_0, _, _, _ = eval_sll_fresh_book_and_peg(
                {"bids": [{"price": "0.998", "size": "200"}], "asks": []},
                {"bids": [{"price": "0.001", "size": "100"}]},
                {"p_model": 1.0, "min_maker_edge": 0.003},
                0.992, 0.985, 0.997, 0.008, 7.96, 0.001, True, True, False, False, 0, 350.0,
            )
            veto_1, cd_1, _, _, _ = eval_sll_fresh_book_and_peg(
                {"bids": [{"price": "0.998", "size": "200"}], "asks": []},
                {"bids": [{"price": "0.001", "size": "100"}]},
                {"p_model": 1.0, "min_maker_edge": 0.003},
                0.992, 0.985, 0.997, 0.008, 7.96, 0.001, True, True, False, False, 1, 350.0,
            )
            self.assertIn("BOND1_OUTBID_ABOVE_CAP", str(veto_0))
            self.assertAlmostEqual(cd_0, 30.0, places=2)
            self.assertIn("BOND1_OUTBID_ABOVE_CAP", str(veto_1))
            self.assertAlmostEqual(cd_1, 180.0, places=2)

            # 3. MKR_REWARD_LOCKED_CARRY $12.00 Seed cap + 8h horizon + GAS1 deep-margin MKR_LOCK1 fallback
            dm_rw = types.SimpleNamespace(
                is_sleeve_grad8_ready=lambda sl: sl == "D1_SAME_ORACLE_DOMINANCE_BOX",
                per_strategy_stats={},
            )
            self.assertTrue(is_reward_locked_carry_live_ready(dm_rw, 0.999, min_reward_shares=10.0, resting_bid_px=0.990))
            self.assertFalse(is_reward_locked_carry_live_ready(dm_rw, 0.999, min_reward_shares=20.0, resting_bid_px=0.990))
            self.assertFalse(is_reward_locked_carry_live_ready(dm_rw, 0.995, min_reward_shares=5.0, resting_bid_px=0.990))

            gsn = GLOBAL_GOVERNANCE_MANAGER.snapshot
            b1_gov = gsn.get("riskless_boxes", {})
            h_gat = types.SimpleNamespace(
                enforce_gatling_sizing=True,
                active_positions={},
                pending_entry_intents={},
                _prepost_sll_reserved_usd={},
            )
            bud_rw = compute_sll_and_carry_gatling_budget(
                h_gat,
                12.0,
                75.58,
                0.0,
                "SINGLE_LEG_MAKER_LOCK",
                "MKR_REWARD_LOCKED_CARRY",
                False,
                b1_gov,
                rem_tte_sec=1800.0,
                now_ts=now_ts,
                cap_usd=12.0,
            )
            bud_b1 = compute_sll_and_carry_gatling_budget(
                h_gat,
                12.0,
                75.58,
                0.0,
                "SINGLE_LEG_MAKER_LOCK",
                "BOND1_UMA_RESOLUTION_CARRY",
                False,
                b1_gov,
                rem_tte_sec=1800.0,
                now_ts=now_ts,
                cap_usd=12.0,
            )
            self.assertAlmostEqual(bud_rw, 12.0, places=2)
            self.assertGreaterEqual(int(bud_rw // 0.990), 10)
            self.assertAlmostEqual(bud_b1, 7.96, places=2)

            # 2h (7200s <= 28800s) p_model=0.999 zero-fee reward carry emits in live mode; 10h (36000s) and p_model=0.998 2h reject
            ok_rw_2h = emit_single_leg_maker_lock_cand_impl(
                live_dm_s2,
                sleeve_source="MKR_REWARD_LOCKED_CARRY",
                asset="W1",
                dedupe_key="MKR_RW_2H_OK",
                pair_dedupe_key="PAIR_RW_2H_OK",
                token_id="1" * 40,
                opp_token_id="2" * 40,
                market_id="70001",
                condition_id="0x" + "70" * 32,
                side_label="NO",
                display_label="Weather Dead NO 2h",
                bk_win={"bids": [{"price": "0.989", "size": "50"}], "asks": [{"price": "0.999", "size": "20"}]},
                bk_opp={"bids": [], "asks": [{"price": "0.01", "size": "50"}]},
                neg_risk=True,
                close_ts=now_ts + 7200.0,
                now_ts=now_ts,
                min_resting_bid=0.940,
                max_resting_bid=0.993,
                min_maker_edge=0.006,
                max_opp_bid=0.030,
                hold_to_maturity=True,
                p_model=0.999,
                target_bid_px=0.990,
                maker_rebate_ps=0.0,
                extract_best_bid_fn=a124_mod.extract_best_bid,
                cand_file=cand_p,
                default_cand_path=cand_p,
                state_file=st_p,
                default_state_path=st_p,
            )
            self.assertTrue(ok_rw_2h)
            self.assertFalse(
                emit_single_leg_maker_lock_cand_impl(
                    live_dm_s2,
                    sleeve_source="MKR_REWARD_LOCKED_CARRY",
                    asset="W1",
                    dedupe_key="MKR_RW_10H_BLK",
                    pair_dedupe_key="PAIR_RW_10H_BLK",
                    token_id="1" * 40,
                    opp_token_id="2" * 40,
                    market_id="70002",
                    condition_id="0x" + "71" * 32,
                    side_label="NO",
                    display_label="Weather Dead NO 10h",
                    bk_win={"bids": [{"price": "0.989", "size": "50"}], "asks": [{"price": "0.999", "size": "20"}]},
                    bk_opp={"bids": [], "asks": [{"price": "0.01", "size": "50"}]},
                    neg_risk=True,
                    close_ts=now_ts + 36000.0,
                    now_ts=now_ts,
                    min_resting_bid=0.940,
                    max_resting_bid=0.993,
                    min_maker_edge=0.006,
                    max_opp_bid=0.030,
                    hold_to_maturity=True,
                    p_model=0.999,
                    target_bid_px=0.990,
                    maker_rebate_ps=0.0,
                    extract_best_bid_fn=a124_mod.extract_best_bid,
                    cand_file=cand_p,
                    default_cand_path=cand_p,
                    state_file=st_p,
                    default_state_path=st_p,
                )
            )
            self.assertFalse(
                emit_single_leg_maker_lock_cand_impl(
                    live_dm_s2,
                    sleeve_source="MKR_REWARD_LOCKED_CARRY",
                    asset="W1",
                    dedupe_key="MKR_RW_998_2H_BLK",
                    pair_dedupe_key="PAIR_RW_998_2H_BLK",
                    token_id="1" * 40,
                    opp_token_id="2" * 40,
                    market_id="70003",
                    condition_id="0x" + "72" * 32,
                    side_label="NO",
                    display_label="Gas 0.998 2h",
                    bk_win={"bids": [{"price": "0.989", "size": "50"}], "asks": [{"price": "0.999", "size": "20"}]},
                    bk_opp={"bids": [], "asks": [{"price": "0.01", "size": "50"}]},
                    neg_risk=True,
                    close_ts=now_ts + 7200.0,
                    now_ts=now_ts,
                    min_resting_bid=0.940,
                    max_resting_bid=0.990,
                    min_maker_edge=0.008,
                    max_opp_bid=0.030,
                    hold_to_maturity=True,
                    p_model=0.998,
                    target_bid_px=0.990,
                    maker_rebate_ps=0.0,
                    extract_best_bid_fn=a124_mod.extract_best_bid,
                    cand_file=cand_p,
                    default_cand_path=cand_p,
                    state_file=st_p,
                    default_state_path=st_p,
                )
            )

            # End-to-end GAS1_AAA_GASOLINE_LOCK scan: deep-margin AAA $4.0688 < $4.0800 with rewardsMinSize=20 emits MKR_GAS1_6712562_YES @ $0.990
            gas_cand_p = tmp_p / "gas_cands.jsonl"
            with (
                mock.patch.object(a124_mod, "DATA_DIR", tmp_p),
                mock.patch.object(a124_mod, "STATE_FILE", tmp_p / "gas_st.json"),
                mock.patch.object(a124_mod, "D1_LIVE_CANDIDATES_FILE", gas_cand_p),
            ):
                d_gas = a124_mod.Alpha124ShadowDaemon(single_scan=False)
                d_gas.is_sleeve_grad8_ready = lambda sl: sl == "D1_SAME_ORACLE_DOMINANCE_BOX"
                as_of_str = datetime.fromtimestamp(now_ts + 7200.0, tz=a124_mod.NY_TZ).date().isoformat()
                end_iso = datetime.fromtimestamp(now_ts + 7200.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                tok_gy, tok_gn = "51" * 20, "52" * 20
                d_gas.gas_events_raw = {
                    "us-gas-price-daily": [
                        {
                            "slug": f"us-gas-price-on-{as_of_str}",
                            "title": f"US Gas Price on {as_of_str}",
                            "endDate": end_iso,
                            "closed": False,
                            "negRisk": False,
                            "markets": [
                                {
                                    "id": "6712562",
                                    "conditionId": "0x" + "67" * 32,
                                    "groupItemTitle": "<$4.0800",
                                    "question": "Will AAA national gas price be <$4.0800?",
                                    "clobTokenIds": json.dumps([tok_gy, tok_gn]),
                                    "negRisk": False,
                                    "rewardsMinSize": 20,
                                    "rewardsMaxSpread": 3.5,
                                    "closed": False,
                                }
                            ],
                        }
                    ]
                }

                async def _mock_gas_books(toks, timeout=3.0):
                    return {
                        tok_gy: {"bids": [{"price": "0.989", "size": "60"}], "asks": [{"price": "0.999", "size": "15"}]},
                        tok_gn: {"bids": [], "asks": [{"price": "0.011", "size": "60"}]},
                    }

                d_gas.fetch_books_batch = _mock_gas_books
                with mock.patch.object(a124_mod, "fetch_aaa_national_gas_sync", return_value={"as_of_date": as_of_str, "current_regular": 4.0688}):
                    asyncio.run(d_gas._scan_phase2_macro_counting_gas_core([], now_ts))
                gas_rows = [json.loads(ln) for ln in gas_cand_p.read_text(encoding="utf-8").splitlines() if ln.strip()]
                gas_mkr = [r for r in gas_rows if r.get("dedupe_key") == "MKR_GAS1_6712562_YES"]
                self.assertEqual(len(gas_mkr), 1)
                self.assertEqual(gas_mkr[0]["sleeve_source"], "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER")
                self.assertAlmostEqual(float(gas_mkr[0]["anchor_bid_px"]), 0.990, places=4)
                self.assertTrue(bool(gas_mkr[0]["queue_front"]))

                # Shallow margin (4.0783 vs 4.0800 -> 0.0017 < 0.0020 -> _p_gas_lk=0.998) MUST NOT emit MKR_GAS1_
                gas_cand_p.unlink()
                d_gas._last_d1_live_emit_ts.clear()
                with mock.patch.object(a124_mod, "fetch_aaa_national_gas_sync", return_value={"as_of_date": as_of_str, "current_regular": 4.0783}):
                    asyncio.run(d_gas._scan_phase2_macro_counting_gas_core([], now_ts))
                shallow_rows = (
                    [json.loads(ln) for ln in gas_cand_p.read_text(encoding="utf-8").splitlines() if ln.strip()]
                    if gas_cand_p.exists()
                    else []
                )
                self.assertEqual([r for r in shallow_rows if str(r.get("dedupe_key", "")).startswith("MKR_GAS1_")], [])

            # 4. W_PRUNE1_DEAD_NO_BOND: >200 tokens (25 cities * 5 brackets * 2 = 250 tokens) without [:200] truncation
            #    AND V2 fee_rate=0.07 Maker quote emitted with positive 25%-share maker_rebate_ps!
            wp_cand_p = tmp_p / "wp_cands.jsonl"
            with (
                mock.patch.object(a124_mod, "DATA_DIR", tmp_p),
                mock.patch.object(a124_mod, "STATE_FILE", tmp_p / "wp_st.json"),
                mock.patch.object(a124_mod, "D1_LIVE_CANDIDATES_FILE", wp_cand_p),
            ):
                d_wp = a124_mod.Alpha124ShadowDaemon(single_scan=False)
                d_wp.is_sleeve_grad8_ready = lambda sl: sl == "D1_SAME_ORACLE_DOMINANCE_BOX"
                now_w_ts = time.time()
                obs_dt = datetime.fromtimestamp(now_w_ts, tz=timezone.utc).date()
                d_wp.weather_events = {}
                d_wp.metar_cache = {}
                wp_books = {}
                target_no_tok = ""
                for idx in range(25):
                    icao = f"EG{idx:02d}"
                    bkts = []
                    for b_i in range(5):
                        yt = f"7{idx:02d}{b_i}1" * 8
                        nt = f"7{idx:02d}{b_i}2" * 8
                        lo_b = -math.inf if b_i == 0 else float(18 + b_i * 2)
                        hi_b = math.inf if b_i == 4 else float(19 + b_i * 2)
                        bkts.append(
                            types.SimpleNamespace(
                                label=f"{b_i}",
                                market_id=f"99{idx:02d}{b_i}",
                                condition_id=f"0x99{idx:02d}{b_i:02d}" + "00" * 29,
                                yes_token=yt,
                                no_token=nt,
                                low_bound=lo_b,
                                high_bound=hi_b,
                                neg_risk=True,
                                fee_rate=0.07,
                                fee_exponent=1.0,
                            )
                        )
                        if idx == 23 and b_i == 0:
                            # Token index > 230 (past old [:200] truncation!) with V2 feesEnabled=True (fee_rate=0.07)
                            target_no_tok = nt
                            wp_books[yt] = {"bids": [], "asks": [{"price": "0.01", "size": "50"}]}
                            wp_books[nt] = {"bids": [{"price": "0.989", "size": "40"}], "asks": [{"price": "0.998", "size": "25"}]}
                        else:
                            wp_books[yt] = {"bids": [{"price": "0.24", "size": "30"}], "asks": [{"price": "0.27", "size": "30"}]}
                            wp_books[nt] = {"bids": [{"price": "0.72", "size": "30"}], "asks": [{"price": "0.76", "size": "30"}]}
                    end_w_iso = datetime.fromtimestamp(now_w_ts + 3637.0 + idx, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    d_wp.weather_events[f"ev_{idx}"] = types.SimpleNamespace(
                        event_id=f"ev_{idx}",
                        city=f"City{idx}",
                        icao=icao,
                        tz_name="UTC",
                        obs_date=obs_dt,
                        unit="C",
                        metric="HIGH",
                        end_date_iso=end_w_iso,
                        end_ts=now_w_ts + 3637.0 + idx,
                        rules_text="Wunderground station",
                        buckets=bkts,
                    )
                    d_wp.metar_cache[f"{icao}_{obs_dt.isoformat()}"] = (
                        now_w_ts,
                        [
                            types.SimpleNamespace(
                                raw_line=f"METAR {icao} 061550Z 25010KT 9999 FEW040 24/12 Q1018",
                                temp_c=24.0,
                                has_t_remark=False,
                                is_corrected=False,
                            )
                        ],
                    )

                seen_batch_lens = []

                async def _mock_wp_books(toks, timeout=3.0):
                    seen_batch_lens.append(len(toks))
                    return {t: wp_books[t] for t in toks if t in wp_books}

                d_wp.fetch_books_batch = _mock_wp_books
                asyncio.run(run_protocol_v2_daemon_scan(d_wp, [], now_ts=now_w_ts))
                self.assertIn(250, seen_batch_lens)
                wp_rows = [json.loads(ln) for ln in wp_cand_p.read_text(encoding="utf-8").splitlines() if ln.strip()]
                wp_hit = [r for r in wp_rows if r.get("leg_a_token_id") == target_no_tok]
                self.assertEqual(len(wp_hit), 1)
                self.assertEqual(wp_hit[0]["sleeve_source"], "W_PRUNE1_DEAD_NO_BOND")
                self.assertAlmostEqual(float(wp_hit[0]["anchor_bid_px"]), 0.990, places=4)
                self.assertGreater(float(wp_hit[0]["maker_rebate_ps"]), 0.0)

                # 6. Executor _ClobClient__tick_sizes prewarm ('0.01' at $0.50) must be popped on >=0.96 recheck
                from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

                exec_tk = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
                exec_tk.dry_run = False
                exec_tk._tick_size_cache = {"tok_prewarm": 0.01}
                exec_tk._enforced_tick_overrides = {}

                class _FakeClobSdk:
                    def __init__(self):
                        self._ClobClient__tick_sizes = {"tok_prewarm": "0.01"}
                        self.http_calls = 0

                    def get_tick_size(self, tid: str) -> str:
                        if tid in self._ClobClient__tick_sizes:
                            return self._ClobClient__tick_sizes[tid]
                        self.http_calls += 1
                        self._ClobClient__tick_sizes[tid] = "0.001"
                        return "0.001"

                exec_tk.client = _FakeClobSdk()
                self.assertAlmostEqual(exec_tk.get_token_tick_size("tok_prewarm", price_hint=0.50), 0.01, places=4)
                self.assertEqual(exec_tk.client.http_calls, 0)
                self.assertAlmostEqual(exec_tk.get_token_tick_size("tok_prewarm", price_hint=0.992), 0.001, places=4)
                self.assertEqual(exec_tk.client.http_calls, 1)
                self.assertAlmostEqual(exec_tk.quantize_order_price(0.992, "tok_prewarm"), 0.992, places=4)

                # Live S2MKR skips joining >$1,200 L1 wall when unable to step ahead, while stepping ahead on 0.98/0.99
                live_s2_p = tmp_p / "live_s2_wall.jsonl"
                now_wall = time.time()
                d_wall = types.SimpleNamespace(
                    single_scan=False,
                    _last_d1_live_emit_ts={},
                    _get_fresh_ws_book=lambda *_a, **_k: None,
                )
                self.assertFalse(
                    emit_single_leg_maker_lock_cand_impl(
                        d_wall,
                        sleeve_source="S2_RTDS_EXACT_TWAP_INTEGRATOR",
                        asset="SOL",
                        dedupe_key="S2MKR_SOL_WALL",
                        pair_dedupe_key="S2LIVE_SOL_WALL",
                        token_id="tok_sol_wall",
                        opp_token_id="tok_sol_opp",
                        market_id="6711555",
                        condition_id="0x" + "ab" * 32,
                        side_label="DOWN",
                        display_label="SOL 5m DOWN",
                        bk_win={"bids": [{"price": "0.99", "size": "5800"}], "asks": [], "minimum_tick_size": "0.01"},
                        bk_opp={"bids": [], "asks": []},
                        neg_risk=False,
                        close_ts=now_wall + 20.0,
                        now_ts=now_wall,
                        min_resting_bid=0.80,
                        max_resting_bid=0.994,
                        min_maker_edge=0.005,
                        max_opp_bid=0.08,
                        hold_to_maturity=True,
                        p_model=0.9999,
                        target_bid_px=None,
                        maker_rebate_ps=0.00014,
                        extract_best_bid_fn=a124_mod.extract_best_bid,
                        cand_file=live_s2_p,
                        default_cand_path=live_s2_p,
                        state_file=st_p,
                        default_state_path=st_p,
                    )
                )
                self.assertTrue(
                    emit_single_leg_maker_lock_cand_impl(
                        d_wall,
                        sleeve_source="S2_RTDS_EXACT_TWAP_INTEGRATOR",
                        asset="ETH",
                        dedupe_key="S2MKR_ETH_STEP",
                        pair_dedupe_key="S2LIVE_ETH_STEP",
                        token_id="tok_eth_step",
                        opp_token_id="tok_eth_opp",
                        market_id="6711543",
                        condition_id="0x" + "cd" * 32,
                        side_label="DOWN",
                        display_label="ETH 5m DOWN",
                        bk_win={"bids": [{"price": "0.98", "size": "5800"}], "asks": [], "minimum_tick_size": "0.01"},
                        bk_opp={"bids": [], "asks": []},
                        neg_risk=False,
                        close_ts=now_wall + 20.0,
                        now_ts=now_wall,
                        min_resting_bid=0.80,
                        max_resting_bid=0.994,
                        min_maker_edge=0.005,
                        max_opp_bid=0.08,
                        hold_to_maturity=True,
                        p_model=0.9999,
                        target_bid_px=None,
                        maker_rebate_ps=0.00014,
                        extract_best_bid_fn=a124_mod.extract_best_bid,
                        cand_file=live_s2_p,
                        default_cand_path=live_s2_p,
                        state_file=st_p,
                        default_state_path=st_p,
                    )
                )

    def test_16_adversarial_review_regressions_tick_dust_none_book_s2_repeg_and_batch_maker(self) -> None:
        import asyncio
        import collections
        import os
        from unittest import mock
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            cap_bond1_maker_for_gatling_reserve,
            emit_single_leg_maker_lock_cand_impl,
            eval_sll_fresh_book_and_peg,
            eval_sll_live_book_poll,
            extract_top_bid_from_book,
            hydrate_fast_s2_from_shm,
            prepare_sll_stalk_guard,
            record_sll_exit_cooldown,
        )

        now_ts = time.time()

        # 1. Empty-bid live book (`extract_top_bid_from_book -> None`) must NOT crash with `NoneType > float`
        empty_bk = {"bids": [], "asks": [{"price": "0.999", "size": "40"}]}
        cur_top = extract_top_bid_from_book(empty_bk)
        self.assertIsNone(cur_top)
        is_outbid_now = (cur_top is not None) and (float(cur_top) > 0.998 + 1e-6)
        self.assertFalse(is_outbid_now)
        c_emp = {"sleeve_source": "BOND1_UMA_RESOLUTION_CARRY"}
        hold_emp = prepare_sll_stalk_guard(types.SimpleNamespace(), "BOND1_EMP", c_emp, 1, 3.0, 3, 35.0, now_ts, is_outbid_now=is_outbid_now, buried_since_mono=None)
        self.assertAlmostEqual(hold_emp, 35.0, places=2)

        # 2. Legacy <= $0.04 ($0.001) bottom-of-book dust MUST NOT overwrite authoritative 0.01 tick size (fixes live ZEC/HYPE HTTP 400!)
        bk_dust_01 = {
            "minimum_tick_size": "0.01",
            "bids": [{"price": "0.001", "size": "250"}, {"price": "0.015", "size": "100"}, {"price": "0.99", "size": "400"}],
            "asks": [{"price": "1.00", "size": "50"}],
        }
        veto_d, _, peg_d, sh_d, tk_d = eval_sll_fresh_book_and_peg(
            bk_dust_01,
            {"bids": [{"price": "0.005", "size": "100"}]},
            {"p_model": 0.9999, "min_maker_edge": 0.005, "maker_rebate_ps": 0.0002},
            0.990, 0.800, 0.992, 0.080, 12.0, 0.01, True, True, False, True, 0, 350.0,
        )
        self.assertIsNone(veto_d)
        self.assertAlmostEqual(tk_d, 0.01, places=4)
        self.assertAlmostEqual(peg_d, 0.99, places=4)
        self.assertGreaterEqual(sh_d, 10)

        # Once a real >= 0.95 sub-cent level ($0.991) appears on L2, eval_sll_fresh_book_and_peg unlocks 0.001 immediately!
        bk_real_001 = {
            "bids": [{"price": "0.001", "size": "250"}, {"price": "0.991", "size": "50"}],
            "asks": [],
        }
        veto_r, _, peg_r, _, tk_r = eval_sll_fresh_book_and_peg(
            bk_real_001,
            {"bids": [{"price": "0.005", "size": "100"}]},
            {"p_model": 0.9999, "min_maker_edge": 0.005, "maker_rebate_ps": 0.0002},
            0.990, 0.800, 0.994, 0.080, 12.0, 0.01, True, True, False, True, 0, 350.0,
        )
        self.assertIsNone(veto_r)
        self.assertAlmostEqual(tk_r, 0.001, places=4)
        self.assertAlmostEqual(peg_r, 0.992, places=4)

        with tempfile.TemporaryDirectory() as tmp_d:
            tmp_p = Path(tmp_d)
            cand_f = tmp_p / "cands.jsonl"
            st_f = tmp_p / "state.json"
            dm_d = types.SimpleNamespace(single_scan=False, _last_d1_live_emit_ts={}, _token_tick_sizes={})
            ok_emit_d = emit_single_leg_maker_lock_cand_impl(
                dm_d,
                sleeve_source="S2_RTDS_EXACT_TWAP_INTEGRATOR",
                asset="ZEC",
                dedupe_key="S2MKR_ZEC_DUST_01",
                pair_dedupe_key="S2_ZEC_DUST_01",
                token_id="tok_zec_d",
                opp_token_id="tok_zec_o",
                market_id="6712027",
                condition_id="0x" + "ab" * 32,
                side_label="UP",
                display_label="ZEC 5m Up",
                bk_win=bk_dust_01,
                bk_opp={"bids": [{"price": "0.005", "size": "50"}], "asks": []},
                neg_risk=False,
                close_ts=now_ts + 22.0,
                now_ts=now_ts,
                min_resting_bid=0.80,
                max_resting_bid=0.992,
                min_maker_edge=0.005,
                max_opp_bid=0.08,
                hold_to_maturity=True,
                p_model=0.9999,
                target_bid_px=None,
                maker_rebate_ps=0.0002,
                extract_best_bid_fn=a124_mod.extract_best_bid,
                cand_file=cand_f,
                default_cand_path=cand_f,
                state_file=st_f,
                default_state_path=st_f,
            )
            self.assertTrue(ok_emit_d)
            emitted_d = json.loads(cand_f.read_text(encoding="utf-8").splitlines()[-1])
            self.assertAlmostEqual(float(emitted_d["anchor_bid_px"]), 0.99, places=4)
            self.assertAlmostEqual(float(emitted_d["leg_a_tick_size"]), 0.01, places=4)

            shm_p = tmp_p / "pm_fast_tick_ZEC.json"
            shm_p.write_text(
                json.dumps(
                    {
                        "timestamp_unix": now_ts,
                        "chainlink_proxy_spot": 35.25,
                        "m5": {
                            "expiry_ts": now_ts + 25.0,
                            "authoritative_chainlink_open": 34.50,
                            "UP": {
                                "token_id": "tok_zec_shm",
                                "age_book_ms": 50.0,
                                "best_bid": 0.99,
                                "best_ask": 0.0,
                                "raw_top_bids": [[0.99, 400.0], [0.001, 150.0]],
                                "raw_top_asks": [],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            dummy_shm_d = types.SimpleNamespace(chainlink_open_cache={}, usd_spot_hist={"ZEC": collections.deque(maxlen=64)})
            with mock.patch.dict(os.environ, {"PM_FAST_TICK_DIR": str(tmp_p)}):
                shm_bks = hydrate_fast_s2_from_shm(dummy_shm_d, now_ts)
            self.assertIn("tok_zec_shm", shm_bks)
            self.assertNotEqual(shm_bks["tok_zec_shm"].get("minimum_tick_size"), "0.001")

        # 3. S2MKR fast #1 FIFO repeg in eval_sll_live_book_poll (when TTE >= 7.5s, capped at 2 repegs)
        c_s2_poll = {
            "sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
            "p_model": 0.9999,
            "min_maker_edge": 0.005,
            "maker_rebate_ps": 0.0002,
            "_posted_notional_usd": 11.88,
        }
        # (a) Outbid at $0.991 with TTE=18s -> REPEG to $0.992!
        act_s2_ob, rp_s2_ob, _, _ = eval_sll_live_book_poll(
            {"bids": [{"price": "0.002", "size": "50"}]},
            {"bids": [{"price": "0.991", "size": "100"}], "asks": []},
            c_s2_poll, 0.990, 0.80, 0.992, 0.08, 0.01, True, True, 0, 350.0, 15.0, now_ts + 18.0, None,
        )
        self.assertEqual(act_s2_ob, "REPEG")
        self.assertAlmostEqual(float(rp_s2_ob or 0.0), 0.992, places=4)
        # (b) TTE=4.0s (< 7.5s) -> does NOT repeg right before candle close!
        act_s2_late, _, _, _ = eval_sll_live_book_poll(
            {"bids": [{"price": "0.002", "size": "50"}]},
            {"bids": [{"price": "0.991", "size": "100"}], "asks": []},
            c_s2_poll, 0.990, 0.80, 0.992, 0.08, 0.001, True, True, 0, 350.0, 15.0, now_ts + 4.0, None,
        )
        self.assertEqual(act_s2_late, "OK")
        # (c) 0.01 -> 0.001 tick flip while buried behind $400 at $0.990 -> micro-steps to $0.991 after 1.0s!
        c_s2_q = dict(c_s2_poll)
        act_q1, _, _, _ = eval_sll_live_book_poll(
            {"bids": []}, {"bids": [{"price": "0.990", "size": "400"}], "asks": []},
            c_s2_q, 0.990, 0.80, 0.992, 0.08, 0.001, True, True, 0, 350.0, 15.0, now_ts + 18.0, None,
        )
        self.assertEqual(act_q1, "OK")
        c_s2_q["_whale_q_since_mono"] = time.monotonic() - 1.2
        act_q2, rp_q2, _, _ = eval_sll_live_book_poll(
            {"bids": []}, {"bids": [{"price": "0.990", "size": "400"}], "asks": []},
            c_s2_q, 0.990, 0.80, 0.992, 0.08, 0.001, True, True, 0, 350.0, 15.0, now_ts + 18.0, None,
        )
        self.assertEqual(act_q2, "REPEG")
        self.assertAlmostEqual(float(rp_q2 or 0.0), 0.991, places=4)

        # 4. py_clob_client_v2 _ClobClient__token_condition_map poisoning fix
        ex_cond = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
        ex_cond.dry_run = False
        ex_cond._tick_size_cache = {}
        ex_cond._neg_risk_cache = {}
        ex_cond._fee_cache = {}

        class _StrictV2ClobClient:
            def __init__(self):
                self._ClobClient__tick_sizes = {}
                self._ClobClient__neg_risk = {}
                self._ClobClient__fee_rates = {}
                self._ClobClient__fee_infos = {}
                self._ClobClient__token_condition_map = {}
                self.tick_endpoint_calls = 0

            def get_clob_market_info(self, cond_id: str):
                raise RuntimeError(f"PolyException: unexpected get_clob_market_info({cond_id}) during get_tick_size!")

            def get_tick_size(self, tid: str) -> str:
                if tid in self._ClobClient__tick_sizes:
                    return self._ClobClient__tick_sizes[tid]
                if tid in self._ClobClient__token_condition_map:
                    self.get_clob_market_info(self._ClobClient__token_condition_map[tid])
                self.tick_endpoint_calls += 1
                self._ClobClient__tick_sizes[tid] = "0.001"
                return "0.001"

        ex_cond.client = _StrictV2ClobClient()
        # Numeric market_id or None must NEVER enter _ClobClient__token_condition_map
        ex_cond.prewarm_token_market_cache("tok_num", tick_size=0.01, neg_risk=False, fee_rate_bps=0, condition_id="6712027")
        self.assertNotIn("tok_num", ex_cond.client._ClobClient__token_condition_map)
        # Valid 0x condition_id IS stored, temporarily popped during get_token_tick_size, and restored cleanly!
        valid_cid = "0x" + "ab" * 32
        ex_cond.prewarm_token_market_cache("tok_hex", tick_size=0.01, neg_risk=False, fee_rate_bps=0, condition_id=valid_cid)
        self.assertEqual(ex_cond.client._ClobClient__token_condition_map.get("tok_hex"), valid_cid)
        self.assertAlmostEqual(ex_cond.get_token_tick_size("tok_hex", price_hint=0.992), 0.001, places=4)
        self.assertEqual(ex_cond.client.tick_endpoint_calls, 1)
        self.assertEqual(ex_cond.client._ClobClient__token_condition_map.get("tok_hex"), valid_cid)

        # 5. Alpha124 fetch_books_batch 8s boundary cooldown + manage_pending_maker_orders batching
        with tempfile.TemporaryDirectory() as tmp_a:
            tmp_ap = Path(tmp_a)
            with (
                mock.patch.object(a124_mod, "DATA_DIR", tmp_ap),
                mock.patch.object(a124_mod, "STATE_FILE", tmp_ap / "st.json"),
            ):
                d_b = a124_mod.Alpha124ShadowDaemon(single_scan=False)
                tok_ws = "88" * 20
                now_b = time.time()
                d_b._ws_books[tok_ws] = (now_b, {"bids": [{"price": "0.99", "size": "100"}], "asks": [{"price": "1.00", "size": "50"}]})
                d_b._token_tick_sizes = {tok_ws: "0.01"}
                d_b._token_tick_boundary_ts = {tok_ws: now_b}
                # Within 8s cooldown, fetch_books_batch MUST serve <1ms WS book with 0 HTTP calls!
                res_ws = asyncio.run(d_b.fetch_books_batch([tok_ws]))
                self.assertIn(tok_ws, res_ws)

                # manage_pending_maker_orders with 60 MKR_REWARD_LOCKED_CARRY orders batches books in 1 call & caps /trades <= 16!
                batch_calls = []
                tape_calls = []

                async def _spy_batch(toks, timeout=3.0):
                    batch_calls.append(len(toks))
                    return {
                        t: (
                            {"bids": [{"price": "0.005", "size": "50"}], "asks": []}
                            if str(t).startswith("opp_")
                            else {"bids": [{"price": "0.99", "size": "50"}], "asks": [{"price": "0.999", "size": "50"}]}
                        )
                        for t in toks
                    }

                orig_fj = a124_mod.Alpha124ShadowDaemon.fetch_json

                async def _cls_fj(self_d, url, timeout=3.0):
                    tape_calls.append(url)
                    return []

                d_b.fetch_books_batch = _spy_batch
                d_b.pending_maker_orders.clear()
                for i in range(60):
                    d_b.pending_maker_orders[f"oid_{i}"] = {
                        "sleeve": "MKR_REWARD_LOCKED_CARRY",
                        "asset_or_city": "RKSI",
                        "token_id": f"tok_w_{i}",
                        "resting_bid": 0.994,
                        "close_ts": now_b + 3600.0,
                        "created_ts": now_b - 30.0,
                        "p_model_at_post": 1.0,
                        "side": "NO",
                        "dedupe_key": f"MKR_RW_{i}",
                        "title": f"RKSI {i}",
                        "extra": {"opp_token_id": f"opp_w_{i}", "condition_id": f"0x{i + 1:064x}"},
                    }
                with mock.patch.object(a124_mod.Alpha124ShadowDaemon, "fetch_json", _cls_fj):
                    asyncio.run(d_b.manage_pending_maker_orders())
                self.assertEqual(len(batch_calls), 1)
                self.assertEqual(batch_calls[0], 120)
                self.assertEqual(len(tape_calls), 16)
                self.assertEqual(len(d_b.pending_maker_orders), 60)
                _ = orig_fj

        # 6. Dedicated MKR_REWARD_LOCKED_CARRY slot protected against MKR_LOCK1 / W_PRUNE1 + stalker strike pruning
        rb_slot = {
            "gatling_enabled": True,
            "gatling_fast_gun_reserve_usd": 20.0,
            "enable_reward_locked_carry_live_bridge": True,
            "reward_reserved_slot_usd_seed": 7.96,
            "reward_harvester_cap_usd_seed": 12.0,
        }
        h_sl = types.SimpleNamespace(
            dry_run=False,
            enforce_gatling_fast_gun_reserve=True,
            enforce_reward_slot_reserve=True,
            _is_v5_unleashed_active=lambda: True,
            active_positions={},
            pending_entry_intents={},
        )
        self.assertAlmostEqual(
            cap_bond1_maker_for_gatling_reserve(h_sl, 20.0, 29.12, 46.44, rb_slot, sleeve_src="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"),
            0.0,
            places=2,
        )
        self.assertAlmostEqual(
            cap_bond1_maker_for_gatling_reserve(h_sl, 20.0, 29.12, 46.44, rb_slot, sleeve_src="W_PRUNE1_DEAD_NO_BOND"),
            0.0,
            places=2,
        )
        h_pr = types.SimpleNamespace(_sll_stalk_strikes={f"OLD_{i}": (2, now_ts - 3600.0) for i in range(515)})
        h_pr._sll_stalk_strikes["ACTIVE_STALKER"] = (2, now_ts - 30.0)
        _ = record_sll_exit_cooldown(h_pr, "NEW_BURIED", True, False, False, 1, now_ts)
        self.assertIn("ACTIVE_STALKER", h_pr._sll_stalk_strikes)
        self.assertLess(len(h_pr._sll_stalk_strikes), 64)


if __name__ == "__main__":
    unittest.main()

