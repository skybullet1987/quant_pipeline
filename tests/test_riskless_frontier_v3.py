#!/usr/bin/env python3
r"""
Unit & Exhaustive State-Payoff Tests for Riskless Frontier v3 (`#1–#6`)
=======================================================================
Proves $\min_{\omega \in \Omega} V_T(\omega) \ge \$1.00$ across ALL 6 Riskless Frontier v3 sleeves:
  1. `LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG`
  2. `SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION`
  3. `CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX`
  4. `LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX`
  5. `CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH`
  6. `TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR`
"""

from __future__ import annotations

import json
import pytest

from src.polymarket_research.alpha_124_shadow_daemon import (
    BANKROLL_TICKETS,
    DEPTH_CAPPED_TAKER_SLEEVES,
)
from src.polymarket_research.riskless_frontier_v2_engine import (
    SoccerRegulationTree,
    find_state_matrix_dominance_boxes,
)
from src.polymarket_research.riskless_frontier_v3_engine import (
    LP2_TOSSUP_CUBE_SLUG,
    LiveMultiSportGame,
    ScoreConfirmationTracker,
    build_lp1_nfl_exact_margin_bundle,
    build_lp2_house_seats_truth_legs,
    build_lp2_pending_senate_conditional_groups,
    build_lp2_senate_seats_truth_legs,
    build_lp2_tossup_state_implication_groups,
    detect_cal1_monotonic_boxes,
    detect_lp2_seat_convert_implication_arbs,
    detect_multisport_ml_spread_polish_middles,
    detect_sp4_subperiod_and_ext_prop_boxes,
    evaluate_cl1_multisport_corridor_clinch_locks,
    evaluate_cl1_soccer_tree_clinch_locks,
    evaluate_sp4_subperiod_and_ext_locks,
    evaluate_ten1_tennis_opportunities,
    parse_cal1_monotonic_ladder_event,
    parse_espn_multisport_scoreboard,
    parse_espn_nba_extended_summary,
    parse_nba_subperiod_and_ext_props,
    parse_tennis_retirement_safe_event,
)
from src.polymarket_research.tradfi_sports_zero_fee_engine import parse_multi_sport_corridor_event

V3_SLEEVES = (
    "LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG",
    "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
    "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
    "LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX",
    "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
    "TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR",
)


def _mk_mkt(
    mid: str,
    group_title: str,
    tok0: str,
    tok1: str,
    outcomes=("Yes", "No"),
    smt: str = "",
    line=None,
    fee_enabled: bool = False,
    fee_rate: float = 0.0,
    question: str = "",
    description: str = "",
    end_date: str = "2026-11-10T00:00:00Z",
    neg_risk: bool = False,
):
    return {
        "id": mid,
        "conditionId": f"0xcond_{mid}",
        "groupItemTitle": group_title,
        "question": question or group_title,
        "description": description,
        "clobTokenIds": json.dumps([tok0, tok1]),
        "outcomes": json.dumps(list(outcomes)),
        "sportsMarketType": smt,
        "line": line,
        "feesEnabled": fee_enabled,
        "feeType": "sports_fees_v2" if (fee_enabled and abs(fee_rate - 0.03) < 1e-4) else ("sports_fees_v3" if fee_enabled else ""),
        "endDate": end_date,
        "negRisk": neg_risk,
        "active": True,
        "closed": False,
        "acceptingOrders": True,
    }


def test_daemon_registries_include_all_six_v3_sleeves():
    for tier in ("T100", "T1000", "T5000"):
        for sl in V3_SLEEVES:
            assert sl in BANKROLL_TICKETS[tier], f"{sl} missing from {tier}"
            assert BANKROLL_TICKETS[tier][sl] > 0.0
    assert "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION" in DEPTH_CAPPED_TAKER_SLEEVES
    assert "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH" in DEPTH_CAPPED_TAKER_SLEEVES


def test_lp2_house_and_senate_zero_assumption_implication_matrices(monkeypatch):
    house_brs = ["Below 190", "190-194", "195-199", "200-204", "205-209", "210-214", "215-219", "220-224", "225-229", "230+"]
    ev_h_seats = {
        "slug": "republican-house-seats-after-the-2026-midterm-elections",
        "negRisk": True,
        "negRiskAugmented": False,
        "negRiskMarketID": "0x" + "11" * 32,
        "endDate": "2026-11-10T00:00:00Z",
        "markets": [_mk_mkt(f"hs_{i}", b, f"hs_y_{i}", f"hs_n_{i}", neg_risk=True) for i, b in enumerate(house_brs)],
    }
    ev_h_ctrl = {
        "slug": "which-party-will-win-the-house-in-2026",
        "negRisk": True,
        "markets": [
            _mk_mkt("hc_d", "Democratic Party", "hc_dy", "hc_dn", neg_risk=True),
            _mk_mkt("hc_r", "Republican Party", "hc_ry", "hc_rn", neg_risk=True),
        ],
    }
    h_legs = build_lp2_house_seats_truth_legs({
        ev_h_seats["slug"]: ev_h_seats,
        ev_h_ctrl["slug"]: ev_h_ctrl,
    })
    assert len(h_legs) == 24
    # In 215-219 (`b=6`), neither `NO[215-219] + YES[House:Rep]` nor `YES[215-219] + YES[House:Dem]` dominates!
    # Whereas `YES[220-224]` implies `YES[House:Rep]`, so `NO[House:Rep] + YES[220-224]` is NOT >=1,
    # while `YES[House:Rep] + NO[220-224]` IS >= $1.00 across all 18 states (including D, R, Other on 215-219)!
    asks_h = {"hc_ry": 0.22, "hs_n_7": 0.76, "hs_y_6": 0.10, "hc_dy": 0.75}
    boxes_h = find_state_matrix_dominance_boxes(h_legs, asks_h, max_2leg_cost_net=0.995)
    assert any(b["n_legs"] == 2 and b["legs"][0]["token_id"] in ("hc_ry", "hs_n_7") and b["min_payout"] >= 1.0 for b in boxes_h)
    for b in boxes_h:
        v_sum = [sum(lg["payoff_vec"][s] for lg in b["legs"]) for s in range(len(b["legs"][0]["payoff_vec"]))]
        assert min(v_sum) >= 1.0 - 1e-9

    # Test Convert + YES[House:Rep] Polish Middle (`3 x NO` on `{220-224, 225-229, 230+}` + `YES[House:Rep]`)
    monkeypatch.setattr(
        "src.polymarket_research.riskless_frontier_v3_engine.verify_negrisk_adapter_slate_sync",
        lambda nr_id, exp_n, rpc_url=None: (True, 0, "ok_mock"),
    )
    bks_conv = {
        "hs_n_7": {"asks": [{"price": "0.91", "size": "100"}]},
        "hs_n_8": {"asks": [{"price": "0.93", "size": "100"}]},
        "hs_n_9": {"asks": [{"price": "0.92", "size": "100"}]},
        "hc_ry": {"asks": [{"price": "0.22", "size": "100"}]},
    }
    # NO sum = 2.76 -> minus $2.00 released = 0.76 + 0.22 = $0.9800 synthetic Polish Middle!
    cv_arbs = detect_lp2_seat_convert_implication_arbs(
        {ev_h_seats["slug"]: ev_h_seats, ev_h_ctrl["slug"]: ev_h_ctrl},
        bks_conv,
        max_synthetic_box_cost_net=0.992,
    )
    assert len(cv_arbs) == 1
    assert abs(cv_arbs[0]["synthetic_box_cost_net"] - 0.98) < 1e-4

    # Senate 18-state check (including 49 R and 50 R split across D/R/Other + Trifecta 57+ split)
    sen_brs = ["≤47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57+"]
    ev_s_seats = {
        "slug": "republican-senate-seats-after-the-2026-midterm-elections-927",
        "negRisk": True,
        "negRiskAugmented": False,
        "markets": [_mk_mkt(f"ss_{i}", b, f"ss_y_{i}", f"ss_n_{i}", neg_risk=True) for i, b in enumerate(sen_brs)],
    }
    ev_s_ctrl = {
        "slug": "which-party-will-win-the-senate-in-2026",
        "markets": [
            _mk_mkt("sc_d", "Democratic Party", "sc_dy", "sc_dn", neg_risk=True),
            _mk_mkt("sc_r", "Republican Party", "sc_ry", "sc_rn", neg_risk=True),
        ],
    }
    ev_tri = {
        "slug": "republican-trifecta-with-supermajority-in-the-senate",
        "markets": [_mk_mkt("tri", "Trifecta 60", "tri_y", "tri_n")],
    }
    s_legs = build_lp2_senate_seats_truth_legs({
        ev_s_seats["slug"]: ev_s_seats,
        ev_s_ctrl["slug"]: ev_s_ctrl,
        ev_tri["slug"]: ev_tri,
    })
    assert len(s_legs) == 28
    # `NO[Trifecta60] + YES[57+]` pays >= $1.00 across all states (and $2.00 when R gets 57-59 seats without Trifecta60!)
    asks_s = {"tri_n": 0.94, "ss_y_10": 0.04}
    bx_s = find_state_matrix_dominance_boxes(s_legs, asks_s, max_2leg_cost_net=0.99)
    assert len(bx_s) == 1
    assert bx_s[0]["min_payout"] == 1.0 and bx_s[0]["max_payout"] == 2.0


def test_lp2_pending_hormuz_and_tossup_write_in_safety():
    ev_sen = {
        "slug": "which-party-will-win-the-senate-in-2026",
        "markets": [
            _mk_mkt("sc_d", "Democratic Party", "sc_dy", "sc_dn"),
            _mk_mkt("sc_r", "Republican Party", "sc_ry", "sc_rn"),
        ],
    }
    ev_hormuz = {
        "slug": "who-wins-the-senate-pending-hormuz-agreement-before-the-midterms",
        "negRisk": True,
        "negRiskAugmented": False,
        "markets": [
            _mk_mkt("hz_r", "Hormuz agreement; R Senate", "hz_ry", "hz_rn", neg_risk=True),
            _mk_mkt("hz_d", "Hormuz agreement; D Senate", "hz_dy", "hz_dn", neg_risk=True),
            _mk_mkt("hz_n", "No Hormuz agreement", "hz_ny", "hz_nn", neg_risk=True),
        ],
    }
    grps = build_lp2_pending_senate_conditional_groups([ev_hormuz], ev_sen)
    assert len(grps) == 1
    _, legs = grps[0]
    # `NO[Hormuz; R Senate] + YES[Sen:Rep]` MUST pay >= $1.00 even if Hormuz=1 and Senate=Other!
    bx = find_state_matrix_dominance_boxes(legs, {"hz_rn": 0.42, "sc_ry": 0.56}, max_2leg_cost_net=0.99)
    assert len(bx) == 1
    assert bx[0]["min_payout"] == 1.0 and bx[0]["max_payout"] == 2.0

    # Tossup write-in Republican safety: `NO[Sullivan (R)] + YES[All 7]` MUST NOT be treated as a riskless box
    # because an unnamed write-in Republican in AK + all other 6 tossups R would pay `0 + 0` if `NO[All 7] + YES[Sullivan]`!
    ev_cube = {
        "slug": LP2_TOSSUP_CUBE_SLUG,
        "markets": [
            _mk_mkt("cb_all7", "All 7", "all7_y", "all7_n", neg_risk=True),
            _mk_mkt("cb_6noak", "IA, KS, ME, MI, OH, TX", "noak_y", "noak_n", neg_risk=True),
        ],
    }
    ev_ak = {
        "slug": "alaska-senate-election-winner",
        "markets": [
            _mk_mkt("ak_r", "Dan Sullivan (R)", "ak_ry", "ak_rn", neg_risk=True),
            _mk_mkt("ak_d", "Mary Peltola (D)", "ak_dy", "ak_dn", neg_risk=True),
        ],
    }
    t_grps = build_lp2_tossup_state_implication_groups({LP2_TOSSUP_CUBE_SLUG: ev_cube, "alaska-senate-election-winner": ev_ak})
    assert len(t_grps) == 1
    _, t_legs = t_grps[0]
    # `YES[Sullivan (R)] + NO[All 7]` fails on `(OTHER_R, True)` -> must return 0 boxes!
    bad_bx = find_state_matrix_dominance_boxes(t_legs, {"ak_ry": 0.45, "all7_n": 0.45}, max_2leg_cost_net=0.99)
    assert len(bad_bx) == 0
    # `NO[NoAK_6] + NO[Sullivan (R)]` pays >= $1.00 across all 8 states!
    good_bx = find_state_matrix_dominance_boxes(t_legs, {"noak_n": 0.48, "ak_rn": 0.49}, max_2leg_cost_net=0.99)
    assert len(good_bx) == 1
    assert good_bx[0]["min_payout"] == 1.0


def test_sp4_subperiod_polish_middles_and_settled_locks():
    ev_nba = {
        "id": "nba1",
        "slug": "nba-bos-nyk-2026-10-30",
        "title": "Celtics vs. Knicks",
        "startTime": "2026-10-30T23:30:00Z",
        "markets": [
            _mk_mkt("m_1h_ml", "1H Moneyline", "ml_bos", "ml_nyk", outcomes=("Celtics", "Knicks"), smt="first_half_moneyline"),
            _mk_mkt("m_1h_sp", "1H Spread: Celtics (-3.5)", "sp_bos", "sp_nyk", outcomes=("Celtics", "Knicks"), smt="first_half_spreads", line=-3.5, question="1H Spread: Celtics (-3.5)"),
            _mk_mkt("m_q1_tot", "Q1 O/U 56.5", "q1_ov", "q1_un", outcomes=("Over", "Under"), smt="q1_totals", line=56.5),
            _mk_mkt("m_stl_1", "Derrick White: Steals O/U 0.5", "dw_y1", "dw_n1", smt="steals", line=0.5),
            _mk_mkt("m_stl_2", "Derrick White: Steals O/U 1.5", "dw_y2", "dw_n2", smt="steals", line=1.5),
        ],
    }
    slate = parse_nba_subperiod_and_ext_props(ev_nba)
    assert slate is not None
    boxes = detect_sp4_subperiod_and_ext_prop_boxes(
        slate,
        {"ml_bos": 0.58, "sp_nyk": 0.40, "dw_y1": 0.55, "dw_n2": 0.43},
        max_box_cost_net=0.992,
    )
    modes = {b["mode"] for b in boxes}
    assert "SP4_1H_ML_SPREAD_MIDDLE" in modes
    assert "SP4_EXT_PROP_POLISH_MIDDLE" in modes

    # Live Q2 (clock 8:00 <= 600s) -> Q1 total (31 + 29 = 60 > 56.5) is officially settled!
    # Steals (cur = 4) MUST NOT lock while game is still in-progress (`completed=False`)!
    ext_in_q2 = {
        "state": "in", "completed": False, "is_halftime": False, "period": 2, "clock_sec": 480.0,
        "home_score": 45, "away_score": 48,
        "linescores": {"away": {1: 31, 2: 17}, "home": {1: 29, 2: 16}},
        "player_ext": {"derrick white": {"steals": 4}},
    }
    lks_q2 = evaluate_sp4_subperiod_and_ext_locks(slate, ext_in_q2)
    assert any(x["mode"] == "SP4_Q1_SETTLED_TOTAL_LOCK" and x["token_id"] == "q1_ov" for x in lks_q2)
    assert not any(x["mode"] == "SP4_FINAL_EXT_STAT_LOCK" for x in lks_q2)

    # Halftime tie (`55 - 55`) on 1H ML MUST NOT lock (50-50 resolution!)
    ext_ht_tie = {
        "state": "in", "completed": False, "is_halftime": True, "period": 2, "clock_sec": 0.0,
        "home_score": 55, "away_score": 55,
        "linescores": {"away": {1: 30, 2: 25}, "home": {1: 28, 2: 27}},
        "player_ext": {"derrick white": {"steals": 4}},
    }
    lks_ht = evaluate_sp4_subperiod_and_ext_locks(slate, ext_ht_tie)
    assert not any(x["mode"] == "SP4_1H_SETTLED_ML_LOCK" for x in lks_ht)
    # Whereas 1H Knicks (+3.5) at 55-55 has margin_fav = 0, |0 - 3.5| = 3.5 >= 1.5 -> Knicks +3.5 IS locked!
    assert any(x["mode"] == "SP4_1H_SETTLED_SPREAD_LOCK" and x["token_id"] == "sp_nyk" for x in lks_ht)

    # Final -> Steals >= floor(1.5)+2 = 3 locks!
    ext_final = {**ext_ht_tie, "state": "post", "completed": True, "home_score": 110, "away_score": 114}
    lks_fin = evaluate_sp4_subperiod_and_ext_locks(slate, ext_final)
    assert any(x["mode"] == "SP4_FINAL_EXT_STAT_LOCK" and x["market_id"] == "m_stl_2" for x in lks_fin)


def test_cal1_survival_deadline_scalar_and_vetoes():
    desc_surv_t1 = 'This market will resolve to "No" if the ceasefire ends by the specified date November 15, 2026, 11:59 PM ET. Otherwise resolves Yes if it remains in effect through November 15, 2026.'
    desc_surv_t2 = 'This market will resolve to "No" if the ceasefire ends by the specified date December 31, 2026, 11:59 PM ET. Otherwise resolves Yes if it remains in effect through December 31, 2026.'
    ev_surv = {
        "id": "cal_s1", "slug": "ceasefire-continues-through-2026", "title": "Ceasefire continues through...",
        "negRisk": False,
        "markets": [
            _mk_mkt("s1", "November 15, 2026", "s1_y", "s1_n", description=desc_surv_t1, end_date="2026-11-16T04:59:00Z"),
            _mk_mkt("s2", "December 31, 2026", "s2_y", "s2_n", description=desc_surv_t2, end_date="2026-12-31T23:59:00Z"),
        ],
    }
    specs_s = parse_cal1_monotonic_ladder_event(ev_surv)
    assert len(specs_s) == 1 and specs_s[0].ladder_kind == "SURVIVAL"
    # SURVIVAL: YES(T1) + NO(T2)!
    bx_s = detect_cal1_monotonic_boxes(specs_s[0], {"s1_y": 0.62, "s2_n": 0.36}, max_box_cost_net=0.992)
    assert len(bx_s) == 1 and bx_s[0]["leg_a"]["token_id"] == "s1_y" and bx_s[0]["leg_b"]["token_id"] == "s2_n"

    # Reset-window veto (`"in November"`) MUST return []!
    ev_reset = {
        "id": "cal_bad", "slug": "strike-in-november-by-region", "title": "Strike in November before midnight?",
        "negRisk": False,
        "markets": [
            _mk_mkt("b1", "Nov 10", "b1_y", "b1_n", description=desc_surv_t1, end_date="2026-11-10T00:00:00Z"),
            _mk_mkt("b2", "Nov 20", "b2_y", "b2_n", description=desc_surv_t2, end_date="2026-11-20T00:00:00Z"),
        ],
    }
    assert parse_cal1_monotonic_ladder_event(ev_reset) == []

    # Scalar Above MUST reject downward `"Below $500M"` rungs!
    desc_fdv = "This market resolves to Yes if the token FDV is above $1B 24 hours after launch on Coingecko."
    ev_fdv = {
        "id": "cal_fdv", "slug": "mega-fdv-above-launch", "title": "Mega FDV above ___ one day after launch?",
        "negRisk": False,
        "markets": [
            _mk_mkt("f0", "Below $500M", "f0_y", "f0_n", description=desc_fdv.replace("$1B", "$500M")),
            _mk_mkt("f1", "$1B", "f1_y", "f1_n", description=desc_fdv),
            _mk_mkt("f2", "$2B", "f2_y", "f2_n", description=desc_fdv.replace("$1B", "$2B")),
        ],
    }
    specs_f = parse_cal1_monotonic_ladder_event(ev_fdv)
    assert len(specs_f) == 1 and len(specs_f[0].rungs) == 2
    assert [r.order_val for r in specs_f[0].rungs] == [1e9, 2e9]
    bx_f = detect_cal1_monotonic_boxes(specs_f[0], {"f1_y": 0.58, "f2_n": 0.40}, max_box_cost_net=0.992)
    assert len(bx_f) == 1 and bx_f[0]["leg_a"]["token_id"] == "f1_y" and bx_f[0]["leg_b"]["token_id"] == "f2_n"


def test_lp1_nfl_exact_margin_11_states_and_multisport_tie_safety():
    fav_bands = [("1-6", 1, 6), ("7-12", 7, 12), ("13-18", 13, 18), ("19-24", 19, 24), ("25+", 25, None)]
    dog_bands = [("1-6", 1, 6), ("7-13", 7, 13), ("14-20", 14, 20), ("21+", 21, None)]
    mkts = [
        _mk_mkt("ml", "Moneyline", "ml_buf", "ml_mia", outcomes=("Bills", "Dolphins"), smt="moneyline", fee_enabled=True, fee_rate=0.03),
        _mk_mkt("sp_65", "Spread: Bills (-6.5)", "sp_buf65", "sp_mia65", outcomes=("Bills", "Dolphins"), smt="spreads", line=-6.5, fee_enabled=True, fee_rate=0.03, question="Spread: Bills (-6.5)"),
        _mk_mkt("sp_35", "Spread: Bills (-3.5)", "sp_buf35", "sp_mia35", outcomes=("Bills", "Dolphins"), smt="spreads", line=-3.5, fee_enabled=True, fee_rate=0.03, question="Spread: Bills (-3.5)"),
        _mk_mkt("em_tie", "Exact Margin: Tie", "emt_y", "emt_n", smt="exact_margin", fee_enabled=True, fee_rate=0.03),
    ]
    for lbl, *_ in fav_bands:
        mkts.append(_mk_mkt(f"emf_{lbl}", f"Exact Margin: Bills by {lbl}", f"emf_y_{lbl}", f"emf_n_{lbl}", smt="exact_margin", fee_enabled=True, fee_rate=0.03))
    for lbl, *_ in dog_bands:
        mkts.append(_mk_mkt(f"emd_{lbl}", f"Exact Margin: Dolphins by {lbl}", f"emd_y_{lbl}", f"emd_n_{lbl}", smt="exact_margin", fee_enabled=True, fee_rate=0.03))

    ev_nfl = {"id": "nfl1", "slug": "nfl-mia-buf-2026-11-01", "title": "Dolphins vs. Bills", "startTime": "2026-11-01T18:00:00Z", "markets": mkts}
    bundle = build_lp1_nfl_exact_margin_bundle(ev_nfl)
    assert bundle is not None
    # `-3.5` splits `Bills by 1-6`, so it MUST be excluded from Exact-Margin truth legs, whereas `-6.5` IS an exact boundary!
    tok_set = {lg["token_id"] for lg in bundle["legs"]}
    assert "sp_buf65" in tok_set and "sp_buf35" not in tok_set
    # Verify `Bills(-6.5) + EM_Y[Bills by 1-6] + ML[Dolphins]` or 2-leg `Dolphins(+6.5) + Bills(-6.5)`...
    # Cross-market 2-leg: `Bills(-6.5)` + `NO[...]`? Wait: `Dolphins(+6.5)` covers Tie, Dolphins win, AND Bills 1-6!
    # So `Dolphins(+6.5)` + `ML[Bills]` pays:
    #   Bills >= 7: 0 + 1 = $1.00; Bills 1-6: 1 + 1 = $2.00; Tie: 1 + 0.5 = $1.50; Dolphins win: 1 + 0 = $1.00; Canceled: 0.5 + 0.5 = $1.00!
    bx = find_state_matrix_dominance_boxes(bundle["legs"], {"sp_mia65": 0.52, "ml_buf": 0.44}, max_2leg_cost_net=0.990)
    assert len(bx) == 1
    assert bx[0]["min_payout"] == 1.0 and bx[0]["max_payout"] == 2.0

    # Also test `detect_multisport_ml_spread_polish_middles` on `-3.5`!
    pm = detect_multisport_ml_spread_polish_middles(ev_nfl, {"ml_buf": 0.60, "sp_mia35": 0.36}, sport_hint="NFL", max_box_cost_net=0.988)
    assert any(p["leg_b"]["token_id"] == "sp_mia35" for p in pm)


def test_cl1_score_confirmation_tracker_purges_var_reversions_and_vetoes_extra_time():
    tracker = ScoreConfirmationTracker()
    # Goal scored at t=1000 (score=2)
    assert tracker.observe_and_confirmed_floor("SOCCER", "g1", "REG_GOALS", 2, 1000.0, 210.0) == 0
    # At t=1150 (150s < 210s), still unconfirmed
    assert tracker.observe_and_confirmed_floor("SOCCER", "g1", "REG_GOALS", 2, 1150.0, 210.0) == 0
    # VAR disallows goal #2 at t=1180 -> reverts to 1! Goal #1 was seen at t=1000 (180s ago).
    assert tracker.observe_and_confirmed_floor("SOCCER", "g1", "REG_GOALS", 1, 1180.0, 210.0) == 0
    # At t=1220, team scores goal #2 AGAIN -> timer for `2` MUST restart at 1220, while `1` is now 220s >= 210s confirmed!
    assert tracker.observe_and_confirmed_floor("SOCCER", "g1", "REG_GOALS", 2, 1220.0, 210.0) == 1
    assert tracker.observe_and_confirmed_floor("SOCCER", "g1", "REG_GOALS", 2, 1435.0, 210.0) == 2

    # Soccer extra-time (`period == 3`) without linescores[1..2] MUST be vetoed!
    tree = SoccerRegulationTree(
        game_id="gid1", event_id_3way="ev1", slug_3way="ucl-ars-psg", title="Arsenal vs PSG",
        neg_risk_market_id="0x0", end_ts=2000.0, home_team="Arsenal", away_team="PSG",
        home_leg={}, draw_leg={}, away_leg={},
        totals=[{"market_id": "t25", "condition_id": "c25", "line": 2.5, "over_token": "ov25", "under_token": "un25", "fee_rate": 0.0, "fee_exponent": 1.0}],
    )
    g_et_no_ls = LiveMultiSportGame(
        sport="SOCCER", game_id="g_et", start_ts=2000.0 - 2.25 * 3600.0, state="in", completed=False,
        is_halftime=False, period=3, clock_sec=300.0, home_name="Arsenal", away_name="PSG", home_score=2, away_score=1,
    )
    assert evaluate_cl1_soccer_tree_clinch_locks(tree, [g_et_no_ls], tracker, 2500.0) == []


def test_ten1_bo5_veto_and_retirement_hedged_1_1_split_box():
    # BO5 match (`Set 4` present) MUST be vetoed!
    ev_bo5 = {
        "id": "gs1", "slug": "atp-sinner-alcaraz-2026", "title": "Sinner vs Alcaraz",
        "startTime": "2026-10-30T18:00:00Z",
        "markets": [
            _mk_mkt("ml", "Moneyline", "p_a", "p_b", outcomes=("Sinner", "Alcaraz"), smt="moneyline"),
            _mk_mkt("s4", "Set 4 Winner", "s4_a", "s4_b", outcomes=("Sinner", "Alcaraz"), smt="tennis_set_winner"),
            _mk_mkt("t1", "Set 1 Games O/U 8.5", "o85", "u85", outcomes=("Over", "Under"), smt="tennis_first_set_totals", line=8.5),
            _mk_mkt("t2", "Set 1 Games O/U 10.5", "o105", "u105", outcomes=("Over", "Under"), smt="tennis_first_set_totals", line=10.5),
        ],
    }
    assert parse_tennis_retirement_safe_event(ev_bo5) is None

    # Valid BO3 match after 1-1 set split:
    ev_bo3 = {
        "id": "atp1", "slug": "atp-shelton-draper-2026-10-30", "title": "Shelton vs Draper",
        "startTime": "2026-10-30T18:00:00Z",
        "markets": [
            _mk_mkt("ml", "Moneyline", "ml_a", "ml_b", outcomes=("Shelton", "Draper"), smt="moneyline", fee_enabled=True, fee_rate=0.05),
            {**_mk_mkt("s1", "Set 1 Winner", "s1_a", "s1_b", outcomes=("Shelton", "Draper"), smt="tennis_first_set_winner"), "closed": True, "outcomePrices": json.dumps(["1", "0"])},
            {**_mk_mkt("s2", "Set 2 Winner", "s2_a", "s2_b", outcomes=("Shelton", "Draper"), smt="tennis_set_winner", line=2), "closed": True, "outcomePrices": json.dumps(["0", "1"])},
            _mk_mkt("sets25", "Total Sets O/U 2.5", "so25", "su25", outcomes=("Over 2.5", "Under 2.5"), smt="tennis_set_totals", line=2.5, fee_enabled=True, fee_rate=0.05),
            _mk_mkt("comp", "Completed Match", "cy", "cn", outcomes=("Yes", "No"), smt="tennis_completed_match", fee_enabled=True, fee_rate=0.05),
            _mk_mkt("g85", "Set 1 Games O/U 8.5", "go85", "gu85", outcomes=("Over", "Under"), smt="tennis_first_set_totals", line=8.5, fee_enabled=True, fee_rate=0.05),
            _mk_mkt("g105", "Set 1 Games O/U 10.5", "go105", "gu105", outcomes=("Over", "Under"), smt="tennis_first_set_totals", line=10.5, fee_enabled=True, fee_rate=0.05),
        ],
    }
    spec = parse_tennis_retirement_safe_event(ev_bo3)
    assert spec is not None
    assert spec.set1_resolved_winner == "A" and spec.set2_resolved_winner == "B"
    opps = evaluate_ten1_tennis_opportunities(
        spec,
        {},
        {"so25": 0.94, "cn": 0.03, "go85": 0.55, "gu105": 0.39},
        max_box_cost_net=0.988,
    )
    modes = {o["mode"] for o in opps}
    assert "TEN1_1_1_RETIREMENT_HEDGED_BOX" in modes
    assert "TEN1_SET1_GAMES_CORRIDOR" in modes


def test_lp1_nfl_exact_margin_preserves_per_leg_neg_risk_flag():
    fav_bands = [("1-6", 1, 6), ("7-12", 7, 12), ("13-18", 13, 18), ("19-24", 19, 24), ("25+", 25, None)]
    dog_bands = [("1-6", 1, 6), ("7-13", 7, 13), ("14-20", 14, 20), ("21+", 21, None)]
    mkts = [
        _mk_mkt("ml", "Moneyline", "ml_buf", "ml_mia", outcomes=("Bills", "Dolphins"), smt="moneyline", fee_enabled=True, fee_rate=0.03, neg_risk=False),
        _mk_mkt("sp_65", "Spread: Bills (-6.5)", "sp_buf65", "sp_mia65", outcomes=("Bills", "Dolphins"), smt="spreads", line=-6.5, fee_enabled=True, fee_rate=0.03, question="Spread: Bills (-6.5)", neg_risk=False),
        _mk_mkt("em_tie", "Exact Margin: Tie", "emt_y", "emt_n", smt="exact_margin", fee_enabled=True, fee_rate=0.03, neg_risk=True),
    ]
    for lbl, *_ in fav_bands:
        mkts.append(_mk_mkt(f"emf_{lbl}", f"Exact Margin: Bills by {lbl}", f"emf_y_{lbl}", f"emf_n_{lbl}", smt="exact_margin", fee_enabled=True, fee_rate=0.03, neg_risk=True))
    for lbl, *_ in dog_bands:
        mkts.append(_mk_mkt(f"emd_{lbl}", f"Exact Margin: Dolphins by {lbl}", f"emd_y_{lbl}", f"emd_n_{lbl}", smt="exact_margin", fee_enabled=True, fee_rate=0.03, neg_risk=True))
    ev_nfl = {"id": "nfl_nr", "slug": "nfl-mia-buf-2026-11-01", "title": "Dolphins vs. Bills", "startTime": "2026-11-01T18:00:00Z", "markets": mkts}
    bundle = build_lp1_nfl_exact_margin_bundle(ev_nfl)
    assert bundle is not None
    by_tok = {lg["token_id"]: lg for lg in bundle["legs"]}
    assert by_tok["ml_buf"]["neg_risk"] is False
    assert by_tok["sp_mia65"]["neg_risk"] is False
    assert by_tok["emf_y_1-6"]["neg_risk"] is True
    assert by_tok["emf_n_1-6"]["neg_risk"] is True


def test_frontier_v3_strict_grad8_auto_promotion_producer_and_consumer(tmp_path, monkeypatch):
    import asyncio
    import time
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    import src.polymarket_research.polymarket_live_harvester as hv_mod
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    assert a124.FRONTIER_V3_GRAD8_SLEEVES == frozenset(V3_SLEEVES)

    st_file = tmp_path / "alpha124_shadow_state.json"
    opps_file = tmp_path / "alpha124_top_opps.json"
    mirror_dir = tmp_path / "polymarket"
    mirror_dir.mkdir(parents=True, exist_ok=True)
    mirror_file = mirror_dir / "alpha124_shadow_state.json"
    cand_file = mirror_dir / "d1_live_box_candidates.jsonl"

    monkeypatch.setattr(a124, "DATA_DIR", tmp_path)
    monkeypatch.setattr(a124, "STATE_FILE", st_file)
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "alpha124_shadow_ledger.jsonl")
    monkeypatch.setattr(a124, "OPPS_FILE", opps_file)
    monkeypatch.setattr(a124, "LIVE_POLYMARKET_DIR", mirror_dir)
    monkeypatch.setattr(a124, "LIVE_ALPHA124_STATE_MIRROR_FILE", mirror_file)
    monkeypatch.setattr(a124, "D1_LIVE_CANDIDATES_FILE", cand_file)
    monkeypatch.setattr(hv_mod, "DATA_DIR", mirror_dir)
    monkeypatch.setattr(hv_mod, "STATE_FILE", mirror_dir / "harvester_state.json")

    now_t = time.time()
    d = a124.Alpha124ShadowDaemon(single_scan=True)
    # Seed D1 as 30/30 graduated so we prove Frontier v3 STILL refuses pre-8/8 `d1_zf_bridge`!
    d.closed_positions = [
        {
            "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
            "won": True,
            "entry_eff_px_t1000": 0.96,
            "tier_pnls_usd": {"T100": 1.0, "T1000": 4.0, "T5000": 12.0},
            "legging_adjusted_tier_pnls_usd": {"T100": 1.0, "T1000": 4.0, "T5000": 12.0},
        }
        for _ in range(12)
    ]

    tok_lo_y = "1" * 26
    tok_lo_n = "2" * 26
    tok_hi_y = "3" * 26
    tok_hi_n = "4" * 26
    ev_nba = {
        "id": "nba_g8_1",
        "slug": "nba-lal-bos-2026-10-31",
        "title": "Lakers vs. Celtics",
        "startTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_t + 3600.0)),
        "markets": [
            _mk_mkt("st1", "Alex Caruso: Steals O/U 1.5", tok_lo_y, tok_lo_n, smt="steals", line=1.5),
            _mk_mkt("st2", "Alex Caruso: Steals O/U 2.5", tok_hi_y, tok_hi_n, smt="steals", line=2.5),
        ],
    }
    sl_nba = parse_nba_subperiod_and_ext_props(ev_nba, now_ts=now_t)
    assert sl_nba is not None
    d.nba_subperiod_slates = {sl_nba.event_id: sl_nba}

    mock_books = {
        tok_lo_y: {"asks": [{"price": "0.52", "size": "80"}], "bids": [{"price": "0.50", "size": "80"}]},
        tok_lo_n: {"asks": [{"price": "0.50", "size": "80"}], "bids": [{"price": "0.48", "size": "80"}]},
        tok_hi_n: {"asks": [{"price": "0.44", "size": "80"}], "bids": [{"price": "0.42", "size": "80"}]},
        tok_hi_y: {"asks": [{"price": "0.58", "size": "80"}], "bids": [{"price": "0.56", "size": "80"}]},
    }

    async def _fake_fetch_books(toks, timeout=3.5):
        return {t: mock_books[t] for t in toks if t in mock_books}

    d.fetch_books_batch = _fake_fetch_books

    def _mk_win(sl_name: str, idx: int) -> dict:
        return {
            "trade_key": f"{sl_name}_w{idx}",
            "sleeve": sl_name,
            "won": True,
            "tier_pnls_usd": {"T100": 0.8, "T1000": 4.2, "T5000": 15.0},
            "legging_adjusted_tier_pnls_usd": {"T100": 0.8, "T1000": 4.1, "T5000": 14.8},
        }

    # 1. At 7/8 wins (0 losses): Producer MUST stay silent AND Consumer MUST reject even 0%-fee boxes!
    for i in range(7):
        d.closed_positions.append(_mk_win("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", i))
    d.write_state_files([])
    assert d.is_sleeve_grad8_ready("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION") is False

    opps_7 = []
    asyncio.run(d._scan_frontier_v3_sleeves(opps_7, now_t))
    assert len(opps_7) == 1
    assert not cand_file.exists() or cand_file.read_text(encoding="utf-8").strip() == ""

    h = PolymarketLiveHarvester(
        dry_run=True, dynamic_sizing=True, hold_to_maturity=False, exit_policy="hold_98",
        ticket_notional=16.50, max_price_ceiling=0.82, max_concurrent=4, allow_cli_concurrency=True,
    )
    h._last_known_collateral = 180.0
    h.executor.get_market_book = lambda tid: mock_books.get(tid, {"asks": [], "bids": []})

    manual_cand_7 = {
        "box_id": "NBA_DOM_TEST_7",
        "dedupe_key": "SP4_SUB_st1_st2_7",
        "box_type": "NBA_DOMINANCE",
        "ts_unix": now_t,
        "asset": "NBA",
        "sleeve_source": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
        "is_quiet_book": True,
        "k_low": 1.5,
        "k_high": 2.5,
        "expiry_ts": now_t + 7200.0,
        "shares": 12,
        "box_cost_net": 0.96,
        "max_box_cost_net": 0.990,
        "leg_a_token_id": tok_lo_y,
        "leg_a_opp_token_id": tok_lo_n,
        "leg_a_market_id": "st1",
        "leg_a_condition_id": "0xcond_st1",
        "leg_a_limit_price": 0.52,
        "leg_a_avail_shares": 80.0,
        "leg_a_fee_rate": 0.0,
        "leg_a_fee_exponent": 1.0,
        "leg_a_neg_risk": False,
        "leg_b_token_id": tok_hi_n,
        "leg_b_opp_token_id": tok_hi_y,
        "leg_b_market_id": "st2",
        "leg_b_condition_id": "0xcond_st2",
        "leg_b_limit_price": 0.44,
        "leg_b_avail_shares": 80.0,
        "leg_b_fee_rate": 0.0,
        "leg_b_fee_exponent": 1.0,
        "leg_b_neg_risk": False,
    }
    rej_7 = h.maybe_execute_graduated_d1_box(manual_cand_7)
    assert rej_7["executed"] is False
    assert rej_7["reason"] == "SLEEVE_NOT_YET_8_OF_8_GRADUATED:SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"

    # 2. Add 8th win (8/8, 0 losses): Producer auto-promotes, flushes mirror immediately, emits live IPC, AND Harvester executes!
    d.open_positions.clear()
    d.entered_keys.clear()
    d._last_d1_live_emit_ts.clear()
    d.closed_positions.append(_mk_win("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION", 7))

    opps_8 = []
    asyncio.run(d._scan_frontier_v3_sleeves(opps_8, now_t))
    assert d.is_sleeve_grad8_ready("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION") is True
    mirror_json = json.loads(mirror_file.read_text(encoding="utf-8"))
    assert mirror_json["by_sleeve"]["SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"]["grad8_live_promoted"] is True
    assert cand_file.exists()
    emitted_lines = [ln for ln in cand_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(emitted_lines) == 1
    emitted_8 = json.loads(emitted_lines[0])
    assert emitted_8["sleeve_source"] == "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"
    assert emitted_8["box_type"] == "NBA_DOMINANCE"

    h._a124_grad_cache_mtime = -1.0
    ok_8 = h.maybe_execute_graduated_d1_box(emitted_8)
    assert ok_8["executed"] is True, f"Expected 8/8 auto-promoted box to execute, got: {ok_8}"

    # 3. Any single loss (8/9, 1 loss) IMMEDIATELY revokes both Producer emission and Consumer execution!
    d.closed_positions.append({
        "trade_key": "sp4_sub_loss1",
        "sleeve": "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
        "won": False,
        "tier_pnls_usd": {"T100": -0.5, "T1000": -2.0, "T5000": -8.0},
        "legging_adjusted_tier_pnls_usd": {"T100": -0.5, "T1000": -2.0, "T5000": -8.0},
    })
    d.write_state_files([])
    assert d.is_sleeve_grad8_ready("SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION") is False
    h._a124_grad_cache_mtime = -1.0
    manual_cand_9 = dict(manual_cand_7, box_id="NBA_DOM_TEST_9", dedupe_key="SP4_SUB_st1_st2_9")
    rej_9 = h.maybe_execute_graduated_d1_box(manual_cand_9)
    assert rej_9["executed"] is False
    assert rej_9["reason"] == "SLEEVE_NOT_YET_8_OF_8_GRADUATED:SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"

