#!/usr/bin/env python3
"""
Regression suite for:
  1. `Alpha124ShadowDaemon` dedicated 1-thread `_state_io_executor` isolation so
     `write_state_files_async` never stalls behind saturated `asyncio.to_thread` RPC queues,
     plus bounded `Semaphore(3)` / `[:32]` UMA RPC concurrency, `BOND2` 60s RPC caching,
     and `_rpc_post` `<=4.5s` failover budget (`STALE_ALPHA124_RESTART` elimination).
  2. `BOND1` `rem_challenge_sec` liveness tier unclamp (`+600s` `close_est` buffer fix) and
     sub-60m (`<=4200s` to `expiry_ts`) `$0.9960` 2-repeg bluff-call ceiling inside
     `prepare_sll_stalk_guard` + `eval_sll_live_book_poll` (verified against
     `passes_capital_velocity_hurdle`).
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
import src.polymarket_research.uma_nba_endgame_engine as uee_mod
from src.polymarket_research.holistic_strategy_governance import passes_capital_velocity_hurdle
from src.polymarket_research.riskless_protocol_v2_expansion import (
    eval_sll_fresh_book_and_peg,
    eval_sll_live_book_poll,
    prepare_sll_stalk_guard,
)


class TestV50Alpha124ThreadpoolAndBond1StalkFix(unittest.TestCase):
    def test_01_write_state_files_async_bypasses_saturated_default_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_p = Path(tmpdir)
            st_file = tmp_p / "alpha124_shadow_state.json"
            mir_file = tmp_p / "mirror_alpha124_shadow_state.json"
            opps_file = tmp_p / "alpha124_top_opps.json"

            async def _run_check() -> float:
                loop = asyncio.get_running_loop()
                small_default = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="sat-def")
                loop.set_default_executor(small_default)
                gate = threading.Event()
                d = a124_mod.Alpha124ShadowDaemon(single_scan=True, riskless_bridge_only=True)
                d._last_proj_write_ts = time.time()
                try:
                    blockers = [
                        asyncio.create_task(asyncio.to_thread(gate.wait, 2.5))
                        for _ in range(4)
                    ]
                    await asyncio.sleep(0.05)
                    t0 = time.monotonic()
                    await d.write_state_files_async([])
                    elapsed = time.monotonic() - t0
                    gate.set()
                    await asyncio.gather(*blockers)
                    return elapsed
                finally:
                    gate.set()
                    st_ex = d.__dict__.pop("_state_io_executor", None)
                    if st_ex is not None:
                        st_ex.shutdown(wait=True)
                    small_default.shutdown(wait=True)

            with (
                mock.patch.object(a124_mod, "STATE_FILE", st_file),
                mock.patch.object(a124_mod, "DATA_DIR", tmp_p),
                mock.patch.object(a124_mod, "LIVE_ALPHA124_STATE_MIRROR_FILE", mir_file),
                mock.patch.object(a124_mod, "OPPS_FILE", opps_file),
            ):
                elapsed_s = asyncio.run(_run_check())
                self.assertLess(elapsed_s, 0.75, f"State write blocked on default executor: {elapsed_s:.3f}s")
                self.assertTrue(st_file.exists())
                self.assertTrue(mir_file.exists())

    def test_02_rpc_post_failover_budget_and_uma_concurrency_cap(self) -> None:
        seen_timeouts: list[float] = []

        def _fake_urlopen(_req, timeout=0.0):
            seen_timeouts.append(float(timeout))
            time.sleep(0.05)
            raise TimeoutError("simulated public RPC timeout")

        t0 = time.monotonic()
        with mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            with self.assertRaises(TimeoutError):
                uee_mod._rpc_post(uee_mod.DEFAULT_POLYGON_RPC, [{"id": 1}], timeout=2.5)
        dt = time.monotonic() - t0
        self.assertGreaterEqual(len(seen_timeouts), 2)
        self.assertTrue(all(t <= 2.5 + 1e-6 for t in seen_timeouts))
        self.assertLess(dt, 4.5)

        with tempfile.TemporaryDirectory() as tmpdir:
            cand_file = Path(tmpdir) / "d1_live_box_candidates.jsonl"
            d = a124_mod.Alpha124ShadowDaemon(single_scan=False, riskless_bridge_only=True)
            now = time.time()
            d.last_uma_discovery_ts = now
            d.uma_proposed_markets = {
                f"m_{i}": {
                    "id": f"m_{i}",
                    "conditionId": f"0xcond_{i}",
                    "question": f"Match {i} winner?",
                    "bestBid": 0.992 if i == 39 else 0.0,
                    "bestAsk": 0.998 if i == 39 else 1.0,
                    "volume24hr": float(i),
                    "negRisk": False,
                }
                for i in range(40)
            }
            lock = threading.Lock()
            active = {"cur": 0, "peak": 0, "total": 0, "hot_checked": False}

            def _fake_verify(mkt, _rpc, _now):
                with lock:
                    active["cur"] += 1
                    active["total"] += 1
                    if mkt.get("id") == "m_39":
                        active["hot_checked"] = True
                    active["peak"] = max(active["peak"], active["cur"])
                time.sleep(0.015)
                with lock:
                    active["cur"] -= 1
                return {"verified": False, "reason": "NO_PROPOSAL"}

            with (
                mock.patch.object(a124_mod, "D1_LIVE_CANDIDATES_FILE", cand_file),
                mock.patch.object(a124_mod, "verify_uma_onchain_proposal_sync", side_effect=_fake_verify),
            ):
                asyncio.run(d.scan_uma_resolution_bonds([], now_ts=now))

            self.assertLessEqual(active["peak"], 3)
            self.assertEqual(active["total"], 32)
            self.assertTrue(active["hot_checked"], "Tradeable 0.992 market must sort ahead of cold markets")

    def test_03_uma_rem_challenge_sec_unclamps_early_2h_and_1h_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cand_file = Path(tmpdir) / "d1_live_box_candidates.jsonl"
            d = a124_mod.Alpha124ShadowDaemon(single_scan=False, riskless_bridge_only=True)
            now = time.time()
            d.last_uma_discovery_ts = now
            d.uma_proposed_markets = {
                "m_fresh2h": {"id": "m_fresh2h", "conditionId": "0xc1", "question": "Game A?", "negRisk": False},
                "m_sub1h": {"id": "m_sub1h", "conditionId": "0xc2", "question": "Game B?", "negRisk": False},
            }
            # Fresh 2h proposal (7080s left -> close_est = now + 7680s > 7200s) and 58m proposal (3480s left -> close_est = now + 4080s > 3600s)
            d.uma_onchain_cache["m_fresh2h"] = (
                now,
                {
                    "verified": True,
                    "win_index": 0,
                    "win_token": "tok_2h_w",
                    "lose_token": "tok_2h_l",
                    "win_label": "YES",
                    "win_outcome_name": "Yes",
                    "domain": "SPORTS",
                    "oo_state": 1,
                    "proposer": "0xp1",
                    "expiration_ts": now + 7080.0,
                    "rem_challenge_sec": 7080.0,
                    "proposal_age_sec": 120.0,
                    "eff_liveness_sec": 7200.0,
                    "fee_rate": 0.0,
                    "fee_exponent": 1.0,
                },
            )
            d.uma_onchain_cache["m_sub1h"] = (
                now,
                {
                    "verified": True,
                    "win_index": 0,
                    "win_token": "tok_1h_w",
                    "lose_token": "tok_1h_l",
                    "win_label": "YES",
                    "win_outcome_name": "Yes",
                    "domain": "SPORTS",
                    "oo_state": 1,
                    "proposer": "0xp2",
                    "expiration_ts": now + 3480.0,
                    "rem_challenge_sec": 3480.0,
                    "proposal_age_sec": 3720.0,
                    "eff_liveness_sec": 7200.0,
                    "fee_rate": 0.0,
                    "fee_exponent": 1.0,
                },
            )

            async def _fake_books(_toks, timeout=3.5):
                return {
                    "tok_2h_w": {"bids": [{"price": "0.996", "size": "40"}], "asks": [{"price": "0.999", "size": "40"}]},
                    "tok_2h_l": {"bids": [{"price": "0.001", "size": "40"}], "asks": [{"price": "0.005", "size": "40"}]},
                    "tok_1h_w": {"bids": [{"price": "0.997", "size": "40"}], "asks": [{"price": "0.999", "size": "40"}]},
                    "tok_1h_l": {"bids": [{"price": "0.001", "size": "40"}], "asks": [{"price": "0.005", "size": "40"}]},
                }

            d.entered_keys.update({"BOND1_m_fresh2h", "BOND1_m_sub1h", "BOND2_m_fresh2h", "BOND2_m_sub1h"})
            with (
                mock.patch.object(a124_mod, "D1_LIVE_CANDIDATES_FILE", cand_file),
                mock.patch.object(d, "fetch_books_batch", side_effect=_fake_books),
                mock.patch("src.polymarket_research.riskless_protocol_v2_expansion.augment_uma_proposed_from_universe_and_polygon", new=mock.AsyncMock(return_value={"added": 0, "disputed_evicted": 0})),
            ):
                asyncio.run(d.scan_uma_resolution_bonds([], now_ts=now))

            rows = {
                r["leg_a_market_id"]: r
                for r in (json.loads(ln) for ln in cand_file.read_text(encoding="utf-8").splitlines() if ln.strip())
            }
            self.assertIn("m_fresh2h", rows)
            self.assertAlmostEqual(float(rows["m_fresh2h"]["max_box_cost_net"]), 0.9975, places=4)
            self.assertIn("m_sub1h", rows)
            self.assertAlmostEqual(float(rows["m_sub1h"]["max_box_cost_net"]), 0.9980, places=4)

    def test_04_sub60m_bond1_stalk_guard_calls_bluffs_up_to_0996_and_passes_velocity(self) -> None:
        for rem_s in (1800.0, 3600.0, 7200.0):
            ok_v, rsn_v = passes_capital_velocity_hurdle(
                box_type="SINGLE_LEG_MAKER_LOCK",
                sleeve_src="BOND1_UMA_RESOLUTION_CARRY",
                collat_usd=48.70,
                rem_tte_sec=rem_s,
                box_cost_net=0.9960,
                fast_recycle_eligible=True,
            )
            self.assertTrue(ok_v, f"$0.9960 BOND1 failed velocity hurdle at rem={rem_s}s: {rsn_v}")

        now_ts = time.time()
        h_stk = types.SimpleNamespace(_sll_stalk_strikes={}, _sll_event_stalk_until={})
        cand_sub30m = {
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "expiry_ts": now_ts + 1800.0,
            "p_model": 1.0,
            "min_maker_edge": 0.0020,
            "event_id": "90901",
        }
        # Repeg #1 outbid in 1.3s at $0.995 (posted $0.994): allows 2nd repeg up to $0.9960!
        hold_1 = prepare_sll_stalk_guard(
            h_stk, "BOND1_MKR_6915600", cand_sub30m, 1, 1.3, 3, 90.0, now_ts, is_outbid_now=True, buried_since_mono=None
        )
        self.assertEqual(cand_sub30m["_max_outbid_repegs"], 2)
        self.assertAlmostEqual(float(cand_sub30m["_stalk_price_cap"]), 0.9960, places=4)
        self.assertLessEqual(hold_1, 12.0)

        act_1, rp_1, bur_1, _ = eval_sll_live_book_poll(
            {"bids": [{"price": "0.001", "size": "100"}]},
            {"bids": [{"price": "0.995", "size": "80"}], "asks": [{"price": "0.999", "size": "50"}]},
            cand_sub30m,
            posted_px=0.994,
            min_rb=0.940,
            max_rb=0.998,
            max_opp=0.008,
            tk_wf=0.001,
            enforce_b1_v53=True,
            is_s2_mkr=False,
            repost_n_in=1,
            b1_q_cap=350.0,
            b1_buried_s=hold_1,
            exp_ts=now_ts + 1800.0,
            buried_since_mono=None,
            collat_usd=48.70,
        )
        self.assertEqual(act_1, "REPEG")
        self.assertAlmostEqual(float(rp_1 or 0.0), 0.9960, places=4)
        self.assertIsNone(bur_1)

        # If penny-jumper immediately jumps $0.996 -> $0.997 on repeg #2, refuses to step to $0.998!
        hold_2 = prepare_sll_stalk_guard(
            h_stk, "BOND1_MKR_6915600", cand_sub30m, 2, 0.8, 3, 90.0, now_ts + 2.0, is_outbid_now=True, buried_since_mono=None
        )
        act_2, rp_2, bur_2, _ = eval_sll_live_book_poll(
            {"bids": [{"price": "0.001", "size": "100"}]},
            {"bids": [{"price": "0.997", "size": "80"}], "asks": [{"price": "0.999", "size": "50"}]},
            cand_sub30m,
            posted_px=0.996,
            min_rb=0.940,
            max_rb=0.998,
            max_opp=0.008,
            tk_wf=0.001,
            enforce_b1_v53=True,
            is_s2_mkr=False,
            repost_n_in=2,
            b1_q_cap=350.0,
            b1_buried_s=hold_2,
            exp_ts=now_ts + 1800.0,
            buried_since_mono=None,
            collat_usd=48.70,
        )
        self.assertEqual(act_2, "OK")
        self.assertIsNone(rp_2)
        self.assertIsNotNone(bur_2)

        # Fresh-book re-entry under stalk cap also clamps peg at <= $0.9960
        veto_f, _, peg_f, _, _ = eval_sll_fresh_book_and_peg(
            {"bids": [{"price": "0.997", "size": "80"}], "asks": [{"price": "0.999", "size": "50"}]},
            {"bids": [{"price": "0.001", "size": "100"}]},
            cand_sub30m,
            anc_bid_px=0.997,
            min_rb=0.940,
            max_rb=0.998,
            max_opp=0.008,
            budget=15.0,
            tk_wf=0.001,
            real_clob_sll=True,
            enforce_b1_v53=True,
            is_mlk1=False,
            is_s2_mkr=False,
            repost_n_in=1,
            b1_q_cap=350.0,
        )
        self.assertIsNotNone(veto_f)
        self.assertLessEqual(peg_f, 0.9960)

        # Long-TTE (>4200s) BOND1 carry still caps _max_outbid_repegs=1 on <12s stalk
        cand_long = {"sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "expiry_ts": now_ts + 6000.0, "p_model": 1.0, "min_maker_edge": 0.0025}
        _ = prepare_sll_stalk_guard(h_stk, "BOND1_LONG", cand_long, 1, 2.0, 3, 90.0, now_ts, is_outbid_now=True, buried_since_mono=None)
        self.assertEqual(cand_long["_max_outbid_repegs"], 1)


if __name__ == "__main__":
    unittest.main()
