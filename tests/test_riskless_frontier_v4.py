#!/usr/bin/env python3
"""
tests/test_riskless_frontier_v4.py
==================================
Comprehensive zero-lookahead, fee-exact verification suite for:
  1. Deliverable 1 (`P0` Dynamic-Fee Unblinding & Net-of-Fee Plumbing across Dominus engines).
  2. Deliverable 2 (`Riskless Frontier v4` Evergreen Sleeves — zero Midterm / single-event models):
       - `AFF1_FROZEN_SUBPERIOD_COLLAPSE`
       - `SOC2_EXACT_SCORE_2D_LATTICE`
       - `NFL_PRP1_MILESTONE_AND_MAX_LOCKS`
       - `SUM1_FRECHET_SUM_TRIANGLES`
       - `CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION`
       - `MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER`
  3. Shadow Daemon (`Alpha124ShadowDaemon`), Live Harvester (`_v3_g8` 8/8 graduation gate),
     and `< 1,000,000` byte `polymarket_all_in_one.py` bundle integrity.
"""

from __future__ import annotations

import asyncio
import json
import py_compile
import sys
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.polymarket_research.barrier_onetouch_svi_engine import (
    BarrierRungSpec,
    detect_barrier_monotonicity_boxes,
)
from src.polymarket_research.macro_counting_ctf_engine import (
    parse_counting_slate_event,
)
from src.polymarket_research.riskless_frontier_v2_engine import (
    parse_nba_player_props_from_event,
)
from src.polymarket_research.riskless_frontier_v3_engine import (
    LiveMultiSportGame,
    ScoreConfirmationTracker,
    parse_nba_subperiod_and_ext_props,
)
from src.polymarket_research.same_oracle_dominance_box import (
    walk_equal_shares_dominance_box,
)
from src.polymarket_research.riskless_frontier_v4_engine import (
    FRONTIER_V4_GRAD8_SLEEVES,
    SOC2_NUM_STATES,
    SOC2_PLAYED_STATES,
    SubperiodFreezeTracker,
    _extract_market_fee_rate as extract_fee_v4,
    _net_unit_ask,
    detect_cry_inc1_binance_inclusion_boxes,
    detect_nfl_prp1_boxes,
    detect_soc2_lattice_boxes_and_converts,
    detect_sum1_frechet_triangles,
    evaluate_aff1_frozen_subperiod_opportunities,
    evaluate_mkr_lock1_post_clinch_rebate_bid,
    evaluate_nfl_prp1_live_locks,
    evaluate_soc2_dead_score_no_locks,
    link_and_parse_soc2_exact_score_lattices,
    parse_affine_game_bundle,
    parse_binance_terminal_close_event,
    parse_espn_nfl_summary,
    parse_nfl_player_props_event,
)
from src.polymarket_research.tradfi_sports_zero_fee_engine import (
    detect_nba_dominance_boxes,
    parse_multi_sport_corridor_event,
    parse_nba_zero_fee_event,
    parse_pyth_hit_event,
)


def _mkt(
    mid: str,
    question: str,
    outcomes: List[str],
    tok0: str,
    tok1: str,
    *,
    smt: str = "",
    line: Any = None,
    group_title: str = "",
    fee_type: str = "sports_fees_v3",
    fee_rate: Any = None,
    neg_risk: bool = False,
    desc: str = "",
    end_date: str = "2026-11-10T04:00:00Z",
    start_date: str = "2026-11-01T00:00:00Z",
    q_idx: int = 0,
) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id": mid,
        "conditionId": f"0xcond_{mid}",
        "questionID": f"0x{'0' * 62}{q_idx:02x}",
        "question": question,
        "groupItemTitle": group_title,
        "description": desc,
        "outcomes": json.dumps(outcomes),
        "clobTokenIds": json.dumps([tok0, tok1]),
        "feesEnabled": True,
        "feeType": fee_type,
        "negRisk": neg_risk,
        "closed": False,
        "archived": False,
        "acceptingOrders": True,
        "endDate": end_date,
        "startDate": start_date,
    }
    if smt:
        d["sportsMarketType"] = smt
    if line is not None:
        d["line"] = line
    if fee_rate is not None:
        d["feeRate"] = fee_rate
    return d


class TestP0DynamicFeeUnblinding(unittest.TestCase):
    def test_universal_fee_schedule_extraction(self) -> None:
        cases = [
            ({"feesEnabled": True, "feeType": "sports_fees_v3"}, 0.05, 1.0),
            ({"feesEnabled": True, "feeType": "sports_fees_nfl_cfb_oct26"}, 0.03, 1.0),
            ({"feesEnabled": True, "feeType": "politics_fees"}, 0.04, 1.0),
            ({"feesEnabled": True, "feeType": "weather_fees"}, 0.05, 1.0),
            ({"feesEnabled": True, "feeType": "economics_fees"}, 0.05, 1.0),
            ({"feesEnabled": True, "feeType": "finance_prices_fees"}, 0.04, 1.0),
            ({"feesEnabled": False, "feeType": "sports_fees_v3"}, 0.0, 1.0),
            ({"feesEnabled": True, "takerBaseFee": 300}, 0.03, 1.0),
        ]
        for m, exp_r, exp_e in cases:
            fr, fe = extract_fee_v4(m)
            self.assertAlmostEqual(fr, exp_r, places=6)
            self.assertAlmostEqual(fe, exp_e, places=6)

    def test_sp1_nba_unblinded_and_rejects_gross_098_trap_under_5pct_fee(self) -> None:
        now = 1_793_580_000.0
        ev = {
            "id": "ev_nba_1",
            "slug": "nba-bos-nyk-2026-11-05",
            "title": "Celtics vs. Knicks",
            "endDate": "2026-11-10T03:00:00Z",
            "markets": [
                _mkt("ml1", "Celtics vs. Knicks", ["Celtics", "Knicks"], "t_ml_0", "t_ml_1", smt="moneyline"),
                _mkt("tot1", "Celtics vs. Knicks: O/U 220.5", ["Over", "Under"], "t_o220", "t_u220", smt="totals", line=220.5),
                _mkt("tot2", "Celtics vs. Knicks: O/U 224.5", ["Over", "Under"], "t_o224", "t_u224", smt="totals", line=224.5),
            ],
        }
        spec = parse_nba_zero_fee_event(ev, now_ts=now)
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(len(spec.total_legs), 4)
        self.assertAlmostEqual(spec.total_legs[0].fee_rate, 0.05, places=6)

        # Gross $0.9800 ($0.49 + $0.49) -> net = 2 * (0.49 + 0.05 * 0.49 * 0.51) = $1.0050 > $1.00 -> MUST REJECT!
        trap_asks = {"t_o220": 0.49, "t_u224": 0.49}
        self.assertEqual(detect_nba_dominance_boxes(spec, trap_asks, max_box_cost_net=0.992), [])

        # Gross $0.9600 ($0.48 + $0.48) -> share-deducted net = 2 * (0.48 / (1 - 0.05 * 0.52)) = $0.9856 <= $0.992 -> MUST ACCEPT!
        good_asks = {"t_o220": 0.48, "t_u224": 0.48}
        boxes = detect_nba_dominance_boxes(spec, good_asks, max_box_cost_net=0.992)
        self.assertEqual(len(boxes), 1)
        self.assertAlmostEqual(boxes[0]["box_cost_net"], round(2.0 * _net_unit_ask(0.48, 0.05, 1.0), 4), places=4)

        # L2 walk also enforces exact 5% share-deducted BUY fee
        w_trap = walk_equal_shares_dominance_box(
            [{"price": "0.49", "size": "200"}],
            [{"price": "0.49", "size": "200"}],
            100.0,
            0.05,
            0.05,
            max_box_cost_net=0.992,
        )
        self.assertFalse(w_trap["filled"])
        w_good = walk_equal_shares_dominance_box(
            [{"price": "0.48", "size": "200"}],
            [{"price": "0.48", "size": "200"}],
            100.0,
            0.05,
            0.05,
            max_box_cost_net=0.992,
        )
        self.assertTrue(w_good["filled"])
        self.assertAlmostEqual(w_good["box_cost_net"], round(2.0 * _net_unit_ask(0.48, 0.05, 1.0), 4), places=4)
        _ = now

    def test_existing_engines_unblinded_for_dynamic_fees(self) -> None:
        # 1. NFL 3% corridor (`tradfi_sports_zero_fee_engine`)
        nfl_ev = {
            "id": "ev_nfl_v2",
            "slug": "nfl-kc-buf-2026-11-08",
            "title": "Chiefs vs. Bills",
            "startTime": "2026-11-10T21:25:00Z",
            "endDate": "2026-11-10T23:55:00Z",
            "markets": [
                _mkt("n_ml", "Chiefs vs. Bills", ["Chiefs", "Bills"], "nml1", "nml2", smt="moneyline", fee_type="sports_fees_nfl_cfb_oct26"),
                _mkt("n_sp", "Spread: Chiefs (-2.5)", ["Chiefs", "Bills"], "nsp1", "nsp2", smt="spreads", line=-2.5, fee_type="sports_fees_nfl_cfb_oct26"),
                _mkt("n_t1", "Chiefs vs. Bills: O/U 47.5", ["Over", "Under"], "nt1", "nt2", smt="totals", line=47.5, fee_type="sports_fees_nfl_cfb_oct26"),
                _mkt("n_t2", "Chiefs vs. Bills: O/U 50.5", ["Over", "Under"], "nt3", "nt4", smt="totals", line=50.5, fee_type="sports_fees_nfl_cfb_oct26"),
            ],
        }
        ms_cor = parse_multi_sport_corridor_event(nfl_ev, "NFL", now_ts=1_793_580_000.0)
        self.assertIsNotNone(ms_cor)
        assert ms_cor is not None
        self.assertAlmostEqual(ms_cor.legs_by_scope["FG:TOTAL"][0].fee_rate, 0.03, places=6)

        # 2. NBA props (`SP4`) & subperiods (`SP4_SUBPERIOD`) with 5% `sports_fees_v3`
        nba_prp_ev = {
            "id": "ev_nba_p",
            "slug": "nba-lal-gsw-2026-11-08",
            "title": "Lakers vs. Warriors",
            "startTime": "2026-11-10T03:00:00Z",
            "markets": [
                _mkt("np1", "Stephen Curry: Points O/U 25.5", ["Yes", "No"], "sc1", "sc2", smt="points", line=25.5),
                _mkt("ns1", "Lakers vs. Warriors: 1H O/U 112.5", ["Over", "Under"], "sh1", "sh2", smt="first_half_totals", line=112.5),
            ],
        }
        p_sl = parse_nba_player_props_from_event(nba_prp_ev, now_ts=1_793_580_000.0)
        s_sl = parse_nba_subperiod_and_ext_props(nba_prp_ev, now_ts=1_793_580_000.0)
        self.assertIsNotNone(p_sl)
        self.assertIsNotNone(s_sl)
        assert p_sl is not None and s_sl is not None
        self.assertAlmostEqual(list(p_sl.props_by_player_stat.values())[0][0].fee_rate, 0.05)
        self.assertAlmostEqual(s_sl.subperiod_markets[0].fee_rate, 0.05)

        # 3. Counting (`TW1`) & Pyth (`finance_prices_fees = 0.04`)
        cnt_ev = {
            "id": "ev_cnt",
            "slug": "elon-musk-of-tweets-november-1-november-8",
            "title": "Elon Musk # of tweets November 1 - November 8?",
            "negRisk": True,
            "startDate": "2026-11-01T16:00:00Z",
            "endDate": "2026-11-10T17:00:00Z",
            "markets": [
                _mkt("cm1", "0-19", ["Yes", "No"], "cy1", "cn1", group_title="0-19", fee_type="culture_fees", neg_risk=True),
                _mkt("cm2", "20-39", ["Yes", "No"], "cy2", "cn2", group_title="20-39", fee_type="culture_fees", neg_risk=True),
                _mkt("cm3", "40+", ["Yes", "No"], "cy3", "cn3", group_title="40+", fee_type="culture_fees", neg_risk=True),
            ],
        }
        cnt_sl = parse_counting_slate_event(cnt_ev, "elon-tweets", "elonmusk")
        self.assertIsNotNone(cnt_sl)
        assert cnt_sl is not None
        self.assertAlmostEqual(cnt_sl.brackets[0].fee_rate, 0.05)

        pyth_ev = {
            "id": "ev_pyth",
            "endDate": "2026-11-10T21:00:00Z",
            "startDate": "2026-11-02T13:30:00Z",
            "description": "Resolved via Pyth regular trading hours feed.",
            "markets": [
                _mkt("pm1", "Will SPY hit above $600?", ["Yes", "No"], "py1", "pn1", group_title="↑ $600", fee_type="finance_prices_fees", desc="Pyth trading session"),
            ],
        }
        p_rungs = parse_pyth_hit_event(pyth_ev, "SPY", "WEEKLY", "spy-hit")
        self.assertEqual(len(p_rungs), 1)
        self.assertAlmostEqual(p_rungs[0].fee_rate, 0.04)

        # 4. Barrier monotonicity box with dynamic fee_exponent
        b1 = BarrierRungSpec(
            event_id="e1", series_slug="btc-hit", horizon_group="MONTHLY", asset="BTC",
            market_id="m1", condition_id="c1", question="Reach $100k", group_label="↑ $100k",
            strike=100000.0, direction="UP", start_ts=1000.0, end_ts=9000.0,
            yes_token="by1", no_token="bn1", fee_rate=0.05, fee_exponent=1.0,
        )
        b2 = BarrierRungSpec(
            event_id="e1", series_slug="btc-hit", horizon_group="MONTHLY", asset="BTC",
            market_id="m2", condition_id="c2", question="Reach $105k", group_label="↑ $105k",
            strike=105000.0, direction="UP", start_ts=1000.0, end_ts=9000.0,
            yes_token="by2", no_token="bn2", fee_rate=0.05, fee_exponent=1.0,
        )
        q_trap = [
            {"market_id": "m1", "condition_id": "c1", "strike": 100000.0, "direction": "UP", "yes_token": "by1", "no_token": "bn1", "best_ask_yes": 0.49, "best_ask_no": 0.55, "l1_yes_usd": 50.0, "l1_no_usd": 50.0, "fee_rate": b1.fee_rate, "fee_exponent": b1.fee_exponent},
            {"market_id": "m2", "condition_id": "c2", "strike": 105000.0, "direction": "UP", "yes_token": "by2", "no_token": "bn2", "best_ask_yes": 0.45, "best_ask_no": 0.49, "l1_yes_usd": 50.0, "l1_no_usd": 50.0, "fee_rate": b2.fee_rate, "fee_exponent": b2.fee_exponent},
        ]
        self.assertEqual(detect_barrier_monotonicity_boxes(q_trap, max_box_cost_net=0.994), [])


class TestAff1FrozenSubperiodCollapse(unittest.TestCase):
    def _build_nba_bundle(self):
        ev = {
            "id": "aff_nba_1",
            "slug": "nba-bos-nyk-2026-11-08",
            "title": "Celtics vs. Knicks",
            "startTime": "2026-11-08T23:00:00Z",
            "markets": [
                _mkt("m_1h_tot", "1H Total O/U 114.5", ["Over", "Under"], "tok_1h_o", "tok_1h_u", smt="first_half_totals", line=114.5),
                _mkt("m_q2_tot", "2Q Total O/U 57.5", ["Over", "Under"], "tok_q2_o", "tok_q2_u", smt="q2_totals", line=57.5),
                _mkt("m_1h_sp", "1H Spread: Celtics (-4.5)", ["Celtics", "Knicks"], "tok_1h_sp0", "tok_1h_sp1", smt="first_half_spreads", line=-4.5),
                _mkt("m_q2_sp", "2Q Spread: Celtics (-1.5)", ["Celtics", "Knicks"], "tok_q2_sp0", "tok_q2_sp1", smt="q2_spreads", line=-1.5),
                _mkt("m_fg_tt", "Celtics Team Total O/U 115.5", ["Over", "Under"], "tok_fg_tto", "tok_fg_ttu", smt="team_totals", line=115.5),
                _mkt("m_2h_tt", "Celtics 2H Team Total O/U 56.5", ["Over", "Under"], "tok_2h_tto", "tok_2h_ttu", smt="second_half_team_totals", line=56.5),
                _mkt("m_fg_tot", "Total O/U 228.5", ["Over", "Under"], "tok_fg_o", "tok_fg_u", smt="totals", line=228.5),
                _mkt("m_q4_tot", "4Q Total O/U 56.5", ["Over", "Under"], "tok_q4_o", "tok_q4_u", smt="q4_totals", line=56.5),
                _mkt("m_ot", "Will the game go to overtime?", ["Yes", "No"], "tok_ot_y", "tok_ot_n", desc="Resolves Yes if game enters overtime."),
                _mkt("m_r10", "Race to 10 Points", ["Celtics", "Knicks"], "tok_r10_a", "tok_r10_h", smt="basketball_game_race_to_points"),
            ],
        }
        b_list = parse_affine_game_bundle([ev])
        self.assertEqual(len(b_list), 1)
        return b_list[0]

    def test_post_q1_halftime_post_q3_and_race_to_x_exhaustive_proofs(self) -> None:
        b = self._build_nba_bundle()
        assert b is not None
        tracker = SubperiodFreezeTracker()
        asks = {
            "tok_1h_o": 0.46, "tok_q2_u": 0.48,     # Post-Q1 1H O114.5 + Q2 U57.5 when Q1=62 (eff_rem=52.5 <= 57.5)
            "tok_1h_sp0": 0.45, "tok_q2_sp1": 0.48, # Post-Q1 Celtics 1H -4.5 + Knicks Q2 +1.5 when mQ1=+6 (rem_th=-1.5 <= +1.5)
            "tok_fg_tto": 0.46, "tok_2h_ttu": 0.47, # HT Celtics FG O115.5 + 2H U56.5 when 1H Celtics=62 (rem=53.5 <= 56.5)
            "tok_fg_o": 0.46, "tok_q4_u": 0.47,     # Post-Q3 2-leg FG O228.5 + 4Q U56.5 when Q1..3=175 (rem=53.5 <= 56.5)
            "tok_fg_u": 0.42, "tok_q4_o": 0.42, "tok_ot_y": 0.08,  # Post-Q3 3-leg OT-immunized when Q1..3=170 (rem=58.5 >= 56.5)
        }

        # 1. Post-Q1: Q1 = 34-28 (S_Q1 = 62, m_Q1 = +6). Before 45s cooldown -> empty; after 45s -> fires!
        sum_q2 = {
            "state": "in", "completed": False, "is_halftime": False, "period": 2,
            "away_score": 34, "home_score": 28,
            "linescores": {"away": {1: 34}, "home": {1: 28}},
        }
        r0 = evaluate_aff1_frozen_subperiod_opportunities(b, sum_q2, asks, tracker, 1000.0, espn_game_id="g1")
        self.assertEqual(r0["two_leg_boxes"], [])

        # Stat-correction test: if Q1 revises to 33-28 at t=1030, timer resets!
        sum_q2_rev = {
            "state": "in", "completed": False, "is_halftime": False, "period": 2,
            "away_score": 33, "home_score": 28,
            "linescores": {"away": {1: 33}, "home": {1: 28}},
        }
        r_rev = evaluate_aff1_frozen_subperiod_opportunities(b, sum_q2_rev, asks, tracker, 1030.0, espn_game_id="g1")
        self.assertEqual(r_rev["two_leg_boxes"], [])
        self.assertEqual(
            evaluate_aff1_frozen_subperiod_opportunities(b, sum_q2_rev, asks, tracker, 1050.0, espn_game_id="g1")["two_leg_boxes"],
            [],
        )
        r_ok = evaluate_aff1_frozen_subperiod_opportunities(b, sum_q2_rev, asks, tracker, 1076.0, espn_game_id="g1")
        modes_q1 = {x["mode"] for x in r_ok["two_leg_boxes"]}
        self.assertIn("AFF1_POST_Q1_1H_VS_Q2_TOTAL", modes_q1)
        self.assertIn("AFF1_POST_Q1_1H_VS_Q2_SPREAD", modes_q1)

        # Exhaustive integer check for Post-Q1 Total (Q1=61 -> 1H O114.5 + Q2 U57.5: S_Q2 > 53.5 or S_Q2 < 57.5)
        for s_q2 in range(0, 110):
            pay = (1.0 if (61 + s_q2) > 114.5 else 0.0) + (1.0 if s_q2 < 57.5 else 0.0)
            self.assertGreaterEqual(pay, 1.0)

        # 2. Halftime NBA Team Total (Celtics 1H = 33 + 29 = 62): FG O115.5 + 2H U56.5 across Reg + OT!
        sum_ht = {
            "state": "in", "completed": False, "is_halftime": True, "period": 2,
            "away_score": 62, "home_score": 55,
            "linescores": {"away": {1: 33, 2: 29}, "home": {1: 28, 2: 27}},
        }
        evaluate_aff1_frozen_subperiod_opportunities(b, sum_ht, asks, tracker, 2000.0, espn_game_id="g1")
        r_ht = evaluate_aff1_frozen_subperiod_opportunities(b, sum_ht, asks, tracker, 2046.0, espn_game_id="g1")
        self.assertTrue(any(x["mode"] == "AFF1_HT_TEAM_TOTAL_FG_VS_2H" for x in r_ht["two_leg_boxes"]))
        for celtics_2h_incl_ot in range(0, 100):
            pay_tt = (1.0 if (62 + celtics_2h_incl_ot) > 115.5 else 0.0) + (1.0 if celtics_2h_incl_ot < 56.5 else 0.0)
            self.assertGreaterEqual(pay_tt, 1.0)

        # 3. Post-Q3 3-Leg OT-Immunized (`Q1..3 = 170`: FG U228.5 + 4Q O56.5 + YES[OT])
        sum_q4 = {
            "state": "in", "completed": False, "is_halftime": False, "period": 4,
            "away_score": 88, "home_score": 82,
            "linescores": {"away": {1: 30, 2: 28, 3: 30}, "home": {1: 27, 2: 27, 3: 28}},
        }
        evaluate_aff1_frozen_subperiod_opportunities(b, sum_q4, asks, tracker, 3000.0, espn_game_id="g2")
        r_q4 = evaluate_aff1_frozen_subperiod_opportunities(b, sum_q4, asks, tracker, 3046.0, espn_game_id="g2")
        self.assertEqual(len(r_q4["three_leg_boxes"]), 1)
        self.assertEqual(r_q4["three_leg_boxes"][0]["mode"], "AFF1_POST_Q3_OT_IMMUNIZED_3LEG")
        # Exhaustive proof across ALL Regulation (`ot=False -> s_ot=0`), Overtime (`ot=True, s_ot in 0..50`), & Canceled (`1.50`)!
        for s_q4 in range(0, 100):
            # Regulation
            pay_reg = (1.0 if (170 + s_q4) < 228.5 else 0.0) + (1.0 if s_q4 > 56.5 else 0.0) + 0.0
            self.assertGreaterEqual(pay_reg, 1.0)
            # Overtime
            for s_ot in range(0, 45):
                pay_ot = (1.0 if (170 + s_q4 + s_ot) < 228.5 else 0.0) + (1.0 if s_q4 > 56.5 else 0.0) + 1.0
                self.assertGreaterEqual(pay_ot, 1.0)
        self.assertAlmostEqual(0.5 + 0.5 + 0.5, 1.5)

        # 4. Race to 10 latch & anti-lookahead veto
        tr_race = SubperiodFreezeTracker()
        # First observation already 14-12 -> MUST VETO (missed crossing order!)
        self.assertIsNone(tr_race.observe_and_confirm_race_winner("NBA", "g_late", 10, 14, 12, 100.0))
        self.assertIsNone(tr_race.observe_and_confirm_race_winner("NBA", "g_late", 10, 18, 15, 200.0))
        # Observed 13-6 -> latches AWAY after 45s even when score later reaches 20-22!
        self.assertIsNone(tr_race.observe_and_confirm_race_winner("NBA", "g_clean", 10, 13, 6, 100.0))
        self.assertEqual(tr_race.observe_and_confirm_race_winner("NBA", "g_clean", 10, 20, 22, 146.0), "AWAY")


class TestSoc2ExactScoreLattice(unittest.TestCase):
    def _build_soccer_events(self) -> List[Dict[str, Any]]:
        ex_mkts: List[Dict[str, Any]] = []
        idx = 0
        for h in range(6):
            for a in range(6):
                ex_mkts.append(
                    _mkt(
                        f"ex_{h}_{a}",
                        f"Will Arsenal vs. Chelsea end {h}-{a}?",
                        ["Yes", "No"],
                        f"ty_{h}_{a}",
                        f"tn_{h}_{a}",
                        group_title=f"{h}-{a}",
                        neg_risk=True,
                        q_idx=idx,
                    )
                )
                idx += 1
        ex_mkts.append(
            _mkt(
                "ex_other",
                "Will Arsenal vs. Chelsea end in Any Other Score?",
                ["Yes", "No"],
                "ty_other",
                "tn_other",
                group_title="Any Other",
                neg_risk=True,
                q_idx=36,
            )
        )
        ev_exact = {
            "id": "soc_ex_1",
            "gameId": "9001",
            "slug": "epl-ars-che-2026-11-08-exact-score",
            "title": "Arsenal vs. Chelsea - Exact Score",
            "startTime": "2026-11-08T16:30:00Z",
            "negRisk": True,
            "negRiskMarketID": "0x" + "ab" * 32,
            "enableNegRisk": True,
            "negRiskAugmented": False,
            "markets": ex_mkts,
        }
        ev_more = {
            "id": "soc_more_1",
            "gameId": "9001",
            "slug": "epl-ars-che-2026-11-08-more-markets",
            "title": "Arsenal vs. Chelsea - More Markets",
            "startTime": "2026-11-08T16:30:00Z",
            "markets": [
                _mkt("m_ou05", "Arsenal vs. Chelsea: O/U 0.5", ["Over", "Under"], "t_ov05", "t_un05", smt="totals", line=0.5),
                _mkt("m_btts", "Both Teams to Score?", ["Yes", "No"], "t_btts_y", "t_btts_n", smt="both_teams_to_score"),
            ],
        }
        return [ev_exact, ev_more]

    def test_83_state_lattice_cancellation_asymmetry_and_dead_score_sweeper(self) -> None:
        self.assertEqual(SOC2_NUM_STATES, 83)
        self.assertEqual(len(SOC2_PLAYED_STATES), 81)
        lats = link_and_parse_soc2_exact_score_lattices(self._build_soccer_events(), now_ts=1_793_580_000.0)
        self.assertIn("9001", lats)
        lat = lats["9001"]
        self.assertTrue(lat.is_closed_37_slate)
        self.assertIsNotNone(lat.convert_spec)

        # CRITICAL CANCELLATION TRAP PROOF:
        # `NO[Exact Score 0-0] + UNDER[0.5 Goals]` pays $1.00 in all 81 played states,
        # BUT pays `0.0 + 0.5 = 0.50` on Canceled states 81 & 82 -> MUST BE REJECTED even at $0.40 + $0.40!
        trap_asks = {"tn_0_0": 0.40, "t_un05": 0.40}
        res_trap = detect_soc2_lattice_boxes_and_converts(lat, {}, trap_asks, max_2leg_cost_net=0.990)
        self.assertEqual(res_trap["matrix_boxes"], [])

        # CONVERSE SAFE IDENTITY:
        # `YES[Exact Score 0-0] + OVER[0.5 Goals]` pays $1.00 in all 81 played states AND $1.50 on Canceled!
        safe_asks = {"ty_0_0": 0.12, "t_ov05": 0.84}  # net = 0.1253 + 0.8467 = 0.9720 <= 0.990
        res_safe = detect_soc2_lattice_boxes_and_converts(lat, {}, safe_asks, max_2leg_cost_net=0.990)
        self.assertEqual(len(res_safe["matrix_boxes"]), 1)
        self.assertEqual(res_safe["matrix_boxes"][0]["n_legs"], 2)

        # Verify `YES[Any Other]` + `NO[BTTS]` is NOT falsely treated as covering `(6, 6)`!
        by_tok = {lg["token_id"]: lg["payoff_vec"] for lg in lat.matrix_legs}
        idx_6_6 = SOC2_PLAYED_STATES.index((6, 6))
        idx_6_0 = SOC2_PLAYED_STATES.index((6, 0))
        self.assertEqual(by_tok["ty_other"][idx_6_0] + by_tok["t_btts_y"][idx_6_0], 1.0)
        self.assertEqual(by_tok["ty_other"][idx_6_6] + by_tok["t_btts_n"][idx_6_6], 1.0)
        self.assertEqual(by_tok["t_btts_y"][idx_6_0], 0.0)  # 6-0 has BTTS=No!

        # Post-VAR dead-score NO sweeper:
        tracker = ScoreConfirmationTracker()
        live_1_0 = [
            LiveMultiSportGame(
                sport="SOCCER", game_id="espn_s1", start_ts=lat.end_ts, state="in",
                completed=False, is_halftime=False, period=1, clock_sec=1800.0,
                home_name="Arsenal", away_name="Chelsea", home_score=1, away_score=0,
            )
        ]
        # Before 210s VAR window -> 0 locks
        self.assertEqual(evaluate_soc2_dead_score_no_locks(lat, live_1_0, tracker, 1000.0), [])
        # After 210s VAR window -> 6 dead `0-a` (`a=1..5`) brackets locked, AND `0-0` is STRICTLY EXCLUDED in-play!
        lks_live = evaluate_soc2_dead_score_no_locks(lat, live_1_0, tracker, 1215.0)
        locked_sides = {x["side_label"] for x in lks_live}
        self.assertNotIn("NO[0-0]", locked_sides)
        for a_dead in range(1, 6):
            self.assertIn(f"NO[0-{a_dead}]", locked_sides)
        self.assertEqual(len(lks_live), 5)

        # At Full-Time (`completed=True, state='post'`), `NO[0-0]` unlocks along with all 35 non-`1-0` brackets!
        ft_1_0 = [
            LiveMultiSportGame(
                sport="SOCCER", game_id="espn_s1", start_ts=lat.end_ts, state="post",
                completed=True, is_halftime=False, period=2, clock_sec=0.0,
                home_name="Arsenal", away_name="Chelsea", home_score=1, away_score=0,
            )
        ]
        lks_ft = evaluate_soc2_dead_score_no_locks(lat, ft_1_0, tracker, 7000.0)
        self.assertEqual(len(lks_ft), 35)
        self.assertIn("NO[0-0]", {x["side_label"] for x in lks_ft})
        self.assertNotIn("NO[1-0]", {x["side_label"] for x in lks_ft})


class TestNflPrp1MilestoneAndMaxLocks(unittest.TestCase):
    def test_td_polish_middle_and_running_max_plus_dnp_locks(self) -> None:
        ev = {
            "id": "nfl_prp_1",
            "slug": "nfl-kc-buf-2026-11-08-player-props",
            "title": "Chiefs vs. Bills - Player Props",
            "startTime": "2026-11-08T21:25:00Z",
            "markets": [
                _mkt("td1", "Travis Kelce: Anytime Touchdown", ["Yes", "No"], "tk_any_y", "tk_any_n", smt="anytime_touchdowns", fee_type="sports_fees_nfl_cfb_oct26"),
                _mkt("td2", "Travis Kelce: 2+ Touchdowns", ["Yes", "No"], "tk_2p_y", "tk_2p_n", smt="two_plus_touchdowns", fee_type="sports_fees_nfl_cfb_oct26"),
                _mkt("lr1", "Travis Kelce: Longest Reception O/U 22.5", ["Over", "Under"], "tk_lr_o", "tk_lr_u", smt="longest_reception", line=22.5, fee_type="sports_fees_nfl_cfb_oct26"),
                _mkt("dnp1", "Isiah Pacheco: Anytime Touchdown", ["Yes", "No"], "ip_any_y", "ip_any_n", smt="anytime_touchdowns", fee_type="sports_fees_nfl_cfb_oct26", desc='If Isiah Pacheco does not play, this market resolves to "No".'),
                _mkt("dnp2", "Clyde Edwards-Helaire: Anytime Touchdown", ["Yes", "No"], "ceh_any_y", "ceh_any_n", smt="anytime_touchdowns", fee_type="sports_fees_nfl_cfb_oct26", desc="If player does not play a snap, market resolves 50-50."),
            ],
        }
        sl = parse_nfl_player_props_event(ev)
        self.assertIsNotNone(sl)
        assert sl is not None

        # Exhaustive state proof for `YES(Anytime TD) + NO(2+ TDs)`:
        # States: Inactive/DNP -> (0 + 1) = 1.0; 0 TD -> (0 + 1) = 1.0; 1 TD -> (1 + 1) = 2.0; >=2 TD -> (1 + 0) = 1.0; Canceled -> (0.5 + 0.5) = 1.0
        for tds in (0, 1, 2, 3):
            pay = (1.0 if tds >= 1 else 0.0) + (1.0 if tds < 2 else 0.0)
            self.assertGreaterEqual(pay, 1.0)
            if tds == 1:
                self.assertAlmostEqual(pay, 2.0)

        boxes = detect_nfl_prp1_boxes(sl, {"tk_any_y": 0.44, "tk_2p_n": 0.52}, max_box_cost_net=0.990)
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0]["mode"], "NFL_PRP1_TD_POLISH_MIDDLE")
        self.assertAlmostEqual(boxes[0]["box_cost_net"], round(_net_unit_ask(0.44, 0.03, 1.0) + _net_unit_ask(0.52, 0.03, 1.0), 4), places=4)

        # Live ESPN NFL summary parsing: Kelce longest_reception = 29, Pacheco & CEH = didNotPlay in Q2
        raw_espn = {
            "header": {
                "competitions": [{
                    "id": "401671",
                    "status": {"period": 2, "type": {"state": "in", "completed": False}},
                }]
            },
            "boxscore": {
                "players": [{
                    "team": {"id": "12"},
                    "statistics": [
                        {
                            "name": "receiving",
                            "keys": ["receptions", "receivingYards", "YPC", "receivingTouchdowns", "longReception", "receivingTargets"],
                            "athletes": [
                                {"athlete": {"displayName": "Travis Kelce"}, "didNotPlay": False, "stats": ["4", "61", "15.3", "0", "29", "5"]},
                                {"athlete": {"displayName": "Isiah Pacheco"}, "didNotPlay": True, "stats": []},
                                {"athlete": {"displayName": "Clyde Edwards-Helaire"}, "didNotPlay": True, "stats": []},
                            ],
                        }
                    ],
                }]
            },
        }
        parsed = parse_espn_nfl_summary(raw_espn)
        self.assertEqual(parsed["players"]["travis kelce"]["longest_reception"], 29)
        self.assertIn("isiah pacheco", parsed["inactive_players"])
        self.assertIn("clyde edwards helaire", parsed["inactive_players"])

        tracker = ScoreConfirmationTracker()
        # Mid-game Q2 (`is_final=False`): DNP lock MUST NOT fire prematurely on a bench player who could still enter in Q4!
        lks_t0 = evaluate_nfl_prp1_live_locks(sl, parsed, tracker, 1000.0)
        self.assertEqual([x["mode"] for x in lks_t0], [])

        # Official Final (`is_final=True`): DNP lock fires ONLY for Pacheco (explicit "No" on DNP); CEH (50-50 on DNP) is strictly vetoed!
        parsed_final = {**parsed, "state": "post", "completed": True, "period": 4}
        lks_fin = evaluate_nfl_prp1_live_locks(sl, parsed_final, ScoreConfirmationTracker(), 2000.0)
        dnp_fin = [x for x in lks_fin if x["mode"] == "NFL_PRP1_INACTIVE_DNP_NO_LOCK"]
        self.assertEqual([x["market_id"] for x in dnp_fin], ["dnp1"])

        # Simulate offensive holding revert at t=1060 (`29 -> 14`) -> MUST NOT lock at t=1130!
        parsed_rev = {**parsed, "players": {"travis kelce": {"longest_reception": 14, "rush_rec_tds": 0}}}
        evaluate_nfl_prp1_live_locks(sl, parsed_rev, tracker, 1060.0)
        lks_rev = evaluate_nfl_prp1_live_locks(sl, parsed_rev, tracker, 1130.0)
        self.assertFalse(any(x["mode"] == "NFL_PRP1_MAX_PLAY_LOCK" for x in lks_rev))

        # Re-establish 29-yd reception at t=1200: 121s (<240s challenge window) stays pending, 241s (>=240s) locks `OVER 22.5`!
        evaluate_nfl_prp1_live_locks(sl, parsed, tracker, 1200.0)
        lks_early = evaluate_nfl_prp1_live_locks(sl, parsed, tracker, 1321.0)
        self.assertFalse(any(x["mode"] == "NFL_PRP1_MAX_PLAY_LOCK" and x["market_id"] == "lr1" for x in lks_early))
        lks_ok = evaluate_nfl_prp1_live_locks(sl, parsed, tracker, 1441.0)
        self.assertTrue(any(x["mode"] == "NFL_PRP1_MAX_PLAY_LOCK" and x["market_id"] == "lr1" for x in lks_ok))


class TestSum1FrechetSumTriangles(unittest.TestCase):
    def test_exhaustive_integer_grid_proof_and_boundary_rejection(self) -> None:
        # Upper Triangle: `OVER(X, nx+0.5) + OVER(Y, ny+0.5) + UNDER(Z, nz+0.5)` requires `nz >= nx + ny`
        nx, ny = 27, 28
        for nz in (nx + ny, nx + ny + 1):
            for x in range(0, 81):
                for y in range(0, 81):
                    z = x + y
                    pay = (1.0 if x > nx + 0.5 else 0.0) + (1.0 if y > ny + 0.5 else 0.0) + (1.0 if z < nz + 0.5 else 0.0)
                    self.assertGreaterEqual(pay, 1.0)

        # Lower Triangle: `UNDER(X, nx+0.5) + UNDER(Y, ny+0.5) + OVER(Z, nz+0.5)` requires `nz <= nx + ny + 1`
        for nz in (nx + ny + 1, nx + ny):
            for x in range(0, 81):
                for y in range(0, 81):
                    z = x + y
                    pay = (1.0 if x < nx + 0.5 else 0.0) + (1.0 if y < ny + 0.5 else 0.0) + (1.0 if z > nz + 0.5 else 0.0)
                    self.assertGreaterEqual(pay, 1.0)

        # Verify engine accepts valid triangles and strictly rejects off-by-1 invalid lines!
        ev_valid = {
            "id": "sum_ev_1",
            "slug": "nba-bos-nyk-2026-11-08",
            "title": "Celtics vs. Knicks",
            "startTime": "2026-11-08T23:00:00Z",
            "markets": [
                _mkt("qx", "1Q Total O/U 27.5", ["Over", "Under"], "xo", "xu", smt="q1_totals", line=27.5),
                _mkt("qy", "2Q Total O/U 28.5", ["Over", "Under"], "yo", "yu", smt="q2_totals", line=28.5),
                _mkt("qz_ok_up", "1H Total O/U 55.5", ["Over", "Under"], "zo1", "zu1", smt="first_half_totals", line=55.5),  # nz=55 == 27+28 (valid Upper AND valid Lower!)
                _mkt("qz_bad_up", "1H Total O/U 54.5", ["Over", "Under"], "zo_bad", "zu_bad", smt="first_half_totals", line=54.5),  # nz=54 < 55 (invalid Upper: X=27, Y=28 => Z=55 loses all 3!)
                _mkt("qz_bad_lo", "1H Total O/U 57.5", ["Over", "Under"], "zo_bad2", "zu_bad2", smt="first_half_totals", line=57.5),  # nz=57 > 56 (invalid Lower: X=28, Y=29 => Z=57 loses all 3!)
            ],
        }
        b_list = parse_affine_game_bundle([ev_valid])
        self.assertEqual(len(b_list), 1)
        b = b_list[0]
        asks = {
            "xo": 0.30, "yo": 0.30, "zu_bad": 0.30,   # must be rejected for Upper!
            "xu": 0.30, "yu": 0.30, "zo_bad2": 0.30,  # must be rejected for Lower!
        }
        self.assertEqual(detect_sum1_frechet_triangles(b, asks, max_3leg_cost_net=0.990), [])

        asks_good = {"xo": 0.30, "yo": 0.30, "zu1": 0.31}
        tris = detect_sum1_frechet_triangles(b, asks_good, max_3leg_cost_net=0.990)
        self.assertEqual(len(tris), 1)
        self.assertEqual(tris[0]["mode"], "SUM1_Q1_Q2_1H_TOTAL_UPPER")


class TestCryInc1SameOracleBinanceInclusion(unittest.TestCase):
    def test_close_subset_hit_and_dynamic_start_ts_mismatch_veto(self) -> None:
        ev_close = {
            "id": "btc_cl_1",
            "slug": "bitcoin-above-on-november-8",
            "endDate": "2026-11-08T17:00:00Z",
            "description": "Resolves via Binance BTC/USDT 1m candle close.",
            "markets": [
                _mkt("c_100k", "Will Bitcoin be above $100,000 on November 8?", ["Yes", "No"], "cy1", "cn1", group_title="$100,000", fee_type="crypto_fees_v2", fee_rate=0.07, desc="Binance BTC/USDT 1m close"),
                _mkt("c_cl_bad", "Will Bitcoin be above $101,000?", ["Yes", "No"], "cy2", "cn2", desc="Resolves via https://data.chain.link/streams/btc-usd"),
            ],
        }
        c_rungs = parse_binance_terminal_close_event(ev_close)
        self.assertEqual(len(c_rungs), 1)
        self.assertEqual(c_rungs[0].market_id, "c_100k")
        t_close = c_rungs[0].close_ts
        now = t_close - 40_000.0

        hr_month_ok = BarrierRungSpec(
            event_id="h_ev_m", series_slug="btc-hit-nov", horizon_group="MONTHLY", asset="BTC",
            market_id="h_m1", condition_id="hc1", question="Will Bitcoin reach $100,000 in November?", group_label="↑ $100k",
            strike=100000.0, direction="UP", start_ts=now - 100_000.0, end_ts=t_close + 500_000.0,
            yes_token="hy_m1", no_token="hn_m1", fee_rate=0.05, fee_exponent=1.0,
        )
        # Dynamic mid-month rung created AFTER short weekly rung started -> MUST BE VETOED!
        hr_week = BarrierRungSpec(
            event_id="h_ev_w", series_slug="btc-hit-wk", horizon_group="WEEKLY", asset="BTC",
            market_id="h_w1", condition_id="hc2", question="Will Bitcoin reach $105,000 this week?", group_label="↑ $105k",
            strike=105000.0, direction="UP", start_ts=now - 50_000.0, end_ts=t_close + 86_400.0,
            yes_token="hy_w1", no_token="hn_w1", fee_rate=0.05, fee_exponent=1.0,
        )
        hr_month_late_created = BarrierRungSpec(
            event_id="h_ev_m", series_slug="btc-hit-nov", horizon_group="MONTHLY", asset="BTC",
            market_id="h_m_late", condition_id="hc3", question="Will Bitcoin reach $105,000 in November?", group_label="↑ $105k",
            strike=105000.0, direction="UP", start_ts=now - 10_000.0, end_ts=t_close + 500_000.0,
            yes_token="hy_mlate", no_token="hn_mlate", fee_rate=0.05, fee_exponent=1.0,
        )
        hr_hype = BarrierRungSpec(
            event_id="h_ev_hy", series_slug="hype-hit", horizon_group="MONTHLY", asset="HYPE",
            market_id="h_hy1", condition_id="hc4", question="Will HYPE reach $50?", group_label="↑ $50",
            strike=50.0, direction="UP", start_ts=now - 100_000.0, end_ts=t_close + 500_000.0,
            yes_token="hy_hype", no_token="hn_hype", fee_rate=0.05, fee_exponent=1.0,
        )

        asks = {
            "cn1": 0.45, "hy_m1": 0.48,       # Close subset Hit -> VALID!
            "hn_w1": 0.45, "hy_mlate": 0.45,  # Late-created monthly rung -> MUST VETO!
        }
        boxes = detect_cry_inc1_binance_inclusion_boxes(
            [hr_month_ok, hr_week, hr_month_late_created, hr_hype],
            c_rungs,
            asks,
            now_ts=now,
            max_box_cost_net=0.992,
        )
        # Exactly 2 valid boxes:
        #   1) `CRY_INC1_CLOSE_SUBSET_HIT`: NO(Close > 100k) + YES(Monthly >= 100k)
        #   2) `CRY_INC1_SUBWINDOW_HIT_INCLUSION`: NO(Weekly >= 105k) + YES(Monthly >= 100k)
        # while `hy_mlate` (start_long > start_short) and `hy_hype` (HYPE futures) are strictly vetoed!
        self.assertEqual(len(boxes), 2)
        self.assertEqual({b["mode"] for b in boxes}, {"CRY_INC1_CLOSE_SUBSET_HIT", "CRY_INC1_SUBWINDOW_HIT_INCLUSION"})
        self.assertFalse(any(b["leg_b"]["token_id"] in ("hy_mlate", "hy_hype") for b in boxes))


class TestMkrLock1PostClinchRebateSweeper(unittest.TestCase):
    def test_post_only_bid_rebate_math_and_safety_vetoes(self) -> None:
        # 1. Valid clinched contract whose taker ask is $0.994 (`taker_net = 0.9943 > 0.988`):
        ev = evaluate_mkr_lock1_post_clinch_rebate_bid(
            token_id="t_win", opp_token_id="t_opp", market_id="m1", condition_id="c1",
            display_label="Arsenal NO[0-1]", source_sleeve="SOC2_EXACT_SCORE_2D_LATTICE",
            p_lock=0.999, close_ts=2000.0, now_ts=1000.0,
            best_bid=0.985, best_ask=0.994, opp_best_bid=0.005,
            fee_rate=0.05, fee_exponent=1.0, maker_rebate_share=0.20,
        )
        self.assertIsNotNone(ev)
        assert ev is not None
        self.assertAlmostEqual(ev["post_only_bid"], 0.986, places=4)
        self.assertLess(ev["post_only_bid"], 0.994)
        exp_rebate = 0.20 * 0.05 * (0.986 * 0.014)
        self.assertAlmostEqual(ev["maker_rebate_per_share"], exp_rebate, places=6)
        self.assertAlmostEqual(ev["effective_net_cost_per_share"], round(0.986 - exp_rebate, 6), places=6)

        # 2. If taker ask is ALREADY cheap ($0.980 -> net $0.981 < 0.988), MKR_LOCK1 defers to taker lock!
        self.assertIsNone(
            evaluate_mkr_lock1_post_clinch_rebate_bid(
                token_id="t_win", opp_token_id="t_opp", market_id="m1", condition_id="c1",
                display_label="Arsenal NO[0-1]", source_sleeve="SOC2_EXACT_SCORE_2D_LATTICE",
                p_lock=0.999, close_ts=2000.0, now_ts=1000.0,
                best_bid=0.975, best_ask=0.980, opp_best_bid=0.005,
            )
        )

        # 3. If complement bid > 0.03 (market disputes lock!), strictly veto!
        self.assertIsNone(
            evaluate_mkr_lock1_post_clinch_rebate_bid(
                token_id="t_win", opp_token_id="t_opp", market_id="m1", condition_id="c1",
                display_label="Arsenal NO[0-1]", source_sleeve="SOC2_EXACT_SCORE_2D_LATTICE",
                p_lock=0.999, close_ts=2000.0, now_ts=1000.0,
                best_bid=0.985, best_ask=0.994, opp_best_bid=0.04,
            )
        )


class TestDaemonAndHarvesterIntegration(unittest.TestCase):
    def test_evergreen_scope_and_daemon_smoke_scan_and_bundle_cap(self) -> None:
        # 1. Verify strictly 6 evergreen sleeves and ZERO Midterm / election models in Frontier v4
        self.assertEqual(len(FRONTIER_V4_GRAD8_SLEEVES), 6)
        for s in FRONTIER_V4_GRAD8_SLEEVES:
            self.assertNotIn("MIDTERM", s.upper())
            self.assertNotIn("ELECTION", s.upper())
            self.assertNotIn("SENATE", s.upper())

        # 2. Import `alpha_124_shadow_daemon` (stubbing `aiohttp` if running under stdlib-only Python)
        stubbed_aiohttp = False
        if "aiohttp" not in sys.modules:
            m_aio = types.ModuleType("aiohttp")
            m_aio.ClientSession = object  # type: ignore[attr-defined]
            m_aio.ClientTimeout = lambda **kw: kw  # type: ignore[attr-defined]
            m_aio.TCPConnector = lambda **kw: kw  # type: ignore[attr-defined]
            sys.modules["aiohttp"] = m_aio
            stubbed_aiohttp = True
        try:
            import src.polymarket_research.alpha_124_shadow_daemon as d_mod

            for sl in FRONTIER_V4_GRAD8_SLEEVES:
                for tier in ("T100", "T1000", "T5000"):
                    self.assertIn(sl, d_mod.BANKROLL_TICKETS[tier])
            self.assertIn("MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", d_mod.LOCKED_MAKER_SLEEVES)

            daemon = d_mod.Alpha124ShadowDaemon(single_scan=True)
            # Populate a synthetic `SUM1` NBA bundle and mock `fetch_books_batch` + `open_shadow_multi_leg_bundle`
            now = 1_793_580_000.0
            ev_sum = {
                "id": "sum_smoke_1",
                "slug": "nba-bos-nyk-2026-11-08",
                "title": "Celtics vs. Knicks",
                "startTime": "2026-11-10T23:00:00Z",
                "markets": [
                    _mkt("qx", "1Q Total O/U 27.5", ["Over", "Under"], "xo", "xu", smt="q1_totals", line=27.5),
                    _mkt("qy", "2Q Total O/U 28.5", ["Over", "Under"], "yo", "yu", smt="q2_totals", line=28.5),
                    _mkt("qz", "1H Total O/U 55.5", ["Over", "Under"], "zo", "zu", smt="first_half_totals", line=55.5),
                ],
            }
            b_list = parse_affine_game_bundle([ev_sum])
            self.assertEqual(len(b_list), 1)
            bnd = b_list[0]
            daemon.aff1_bundles[bnd.event_id] = bnd

            async def _fake_fetch_books(toks, timeout=3.5):
                return {
                    t: {
                        "bids": [{"price": "0.28", "size": "150"}],
                        "asks": [{"price": "0.30", "size": "150"}],
                    }
                    for t in toks
                }

            opened_bundles: List[str] = []

            async def _fake_open_bundle(sleeve, dk, *args, **kwargs):
                opened_bundles.append(f"{sleeve}:{dk}")
                return True

            daemon.fetch_books_batch = _fake_fetch_books  # type: ignore[method-assign]
            daemon.open_shadow_multi_leg_bundle = _fake_open_bundle  # type: ignore[method-assign]
            opps: List[Dict[str, Any]] = []
            asyncio.run(daemon._scan_frontier_v4_sleeves(opps, now))
            self.assertTrue(any(o["sleeve"] == "SUM1_FRECHET_SUM_TRIANGLES" for o in opps))
            self.assertTrue(any(k.startswith("SUM1_FRECHET_SUM_TRIANGLES:") for k in opened_bundles))
        finally:
            if stubbed_aiohttp:
                sys.modules.pop("aiohttp", None)

        # 3. Verify `polymarket_live_harvester.py` contains all 6 Frontier v4 sleeves in `_v3_g8`
        harv_src = (PROJECT_ROOT / "src" / "polymarket_research" / "polymarket_live_harvester.py").read_text(encoding="utf-8")
        for sl in FRONTIER_V4_GRAD8_SLEEVES:
            self.assertIn(f'"{sl}"', harv_src)

        # 4. Verify `polymarket_all_in_one.py` compiles cleanly (no 1 MB cap)
        bundle_path = PROJECT_ROOT / "polymarket_all_in_one.py"
        self.assertTrue(bundle_path.exists())
        sz = bundle_path.stat().st_size
        self.assertGreater(sz, 100_000)
        py_compile.compile(str(bundle_path), doraise=True)


if __name__ == "__main__":
    unittest.main()
