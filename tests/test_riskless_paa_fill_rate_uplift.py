"""
Regression suite for Zero-Loss Fill-Rate Uplift under strict `RISKLESS_PAA` Governance:
  1. `RISKLESS_PAA` invariants (`PermissionGate`, `_deep_merge_validated`, `seed_zero_loss_focus_bond1_pool_pct = 0.80`,
     `strict_pure_riskless_mode = True`, `riskless_only_mode = True`, all 20 `paused_riskless_sleeves` intact).
  2. Taker headroom preservation (`$9.54` adaptive reserve at `$47.07` live NAV while keeping `$2.00` at `$26.50` and
     `$13.50` at `$75.47`), `PASSIVE_CARRY_SLEEVES` `rem_tte_sec == 600s` coverage, and selective `<70ms` single-slot
     non-`FIFO#1` cross-market Maker preemption when `_free_pre_1l < $8.50`.
  3. Dead-book (`asks=[]`, `l1_bid_usd < $75`, `volume24hr < $350`) Maker candidate rejection + seller-flow velocity ranking.
  4. Multi-map / multi-game esports parent match deduplication (`Game 2:` / `Game 3:` -> identical `EVTMATCH:` key).
  5. Active two-sided shallow L1 queue patience (`75s` hold when outbid `<= 2` ticks on a locked `<= 2`-tick spread with
     `l1_q <= $80` and active asks, vs `12s` stalk cancel on askless books).
  6. Command Center (`scripts/dominus_command_center.py`) sleeve status truthfulness under `strict_pure_riskless_mode`.
"""
from __future__ import annotations

import ast
import json
import threading
import time
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_riskless_paa_governance_and_permission_gate_invariants() -> None:
    from src.paa_os.permissions import PermissionGate
    from src.polymarket_research.holistic_strategy_governance import (
        DEFAULT_HOLISTIC_CONFIG,
        _deep_merge_validated,
    )
    from src.polymarket_research.stage_c_zero_loss_velocity import (
        PURE_RISKLESS_ALLOWED_LIVE_SLEEVES,
        PURE_RISKLESS_BLOCKED_SLEEVES,
    )

    cfg_path = REPO_ROOT / "config/polymarket_strategy_and_risk.json"
    raw_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    merged = _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, raw_cfg)

    assert merged["directional"]["riskless_only_mode"] is True
    rb = merged["riskless_boxes"]
    assert rb["strict_pure_riskless_mode"] is True
    assert rb["strict_zero_legging_pre_split_lock"] is True
    assert rb["seed_zero_loss_focus_bond1_pool_pct"] == pytest.approx(0.80)
    assert rb["paused_s2_reserve_floor_usd"] == pytest.approx(2.0)

    paused = {str(s).strip().upper() for s in rb["paused_riskless_sleeves"]}
    assert len(paused) >= 20
    assert "BOND1_UMA_RESOLUTION_CARRY" in PURE_RISKLESS_ALLOWED_LIVE_SLEEVES
    assert "S2_RTDS_EXACT_TWAP_INTEGRATOR" in PURE_RISKLESS_BLOCKED_SLEEVES

    gate = PermissionGate()
    modified_files = [
        "config/polymarket_strategy_and_risk.json",
        "src/polymarket_research/riskless_protocol_v2_expansion.py",
        "src/polymarket_research/polymarket_live_harvester.py",
        "src/polymarket_research/alpha_124_shadow_daemon.py",
        "polymarket_all_in_one.py",
        "scripts/dominus_command_center.py",
        "tests/test_riskless_paa_fill_rate_uplift.py",
    ]
    ok, violations = gate.inspect_candidate_diff(modified_files, "+ seed_zero_loss_focus_bond1_pool_pct: 0.80\n")
    assert ok is True, f"PermissionGate rejected diff: {violations}"
    assert violations == []


def test_adaptive_taker_reserve_curve_and_cash_starved_sll_preemption(tmp_path: Path, monkeypatch) -> None:
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        PASSIVE_CARRY_SLEEVES,
        cap_bond1_maker_for_gatling_reserve,
        compute_sll_and_carry_gatling_budget,
    )

    assert "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER" in PASSIVE_CARRY_SLEEVES
    assert "W_PRUNE1_DEAD_NO_BOND" in PASSIVE_CARRY_SLEEVES
    assert "UMA_READY1_LIVENESS_PRIORITY" in PASSIVE_CARRY_SLEEVES

    rb_paused_s2 = {
        "gatling_enabled": True,
        "gatling_fast_gun_reserve_usd": 20.0,
        "paused_s2_reserve_floor_usd": 2.0,
        "paused_riskless_sleeves": [
            "S2_RTDS_EXACT_TWAP_INTEGRATOR",
            "S2_EXACT_TWAP_LOCK",
        ],
    }
    mock_h = types.SimpleNamespace(
        dry_run=False,
        enforce_gatling_fast_gun_reserve=True,
        _is_v5_unleashed_active=lambda: True,
        active_positions={},
        pending_entry_intents={},
    )
    # 1a. $26.50 micro-wallet keeps $2.00 floor so 3rd 8-share slot gets >=5 shares ($5.33)
    b_26 = cap_bond1_maker_for_gatling_reserve(mock_h, 20.0, 10.63, 15.87, rb_paused_s2, sleeve_src="BOND1_UMA_RESOLUTION_CARRY")
    assert b_26 >= 5.30

    # 1b. $47.07 live wallet preserves ~$9.54 unencumbered cash so Taker WS snipes never starve!
    b_47 = cap_bond1_maker_for_gatling_reserve(mock_h, 20.0, 12.07, 35.00, rb_paused_s2, sleeve_src="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER")
    assert b_47 == pytest.approx(2.53, abs=0.05)

    # Even when rem_tte_sec == 600.0 (post-clinch MKR_LOCK1 default), PASSIVE_CARRY_SLEEVES enforces the reserve!
    b_47_600s = compute_sll_and_carry_gatling_budget(
        mock_h,
        20.0,
        12.07,
        35.00,
        "SINGLE_LEG_MAKER_LOCK",
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        True,
        rb_paused_s2,
        rem_tte_sec=600.0,
        now_ts=time.time(),
    )
    assert b_47_600s == pytest.approx(2.53, abs=0.05)

    # 1c. $75.47 wallet after 6 * $7.936 ($47.616) still grants full $7.96 (8 shares) to 7th slot ($27.854 - $13.50 = $14.35)
    b_75 = cap_bond1_maker_for_gatling_reserve(mock_h, 7.96, 27.854, 47.616, rb_paused_s2, sleeve_src="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER")
    assert b_75 == pytest.approx(7.96)

    # 2. Cash-starved live `_finish_single_leg_lock` ($4.44 free cash) selectively preempts ONLY the non-FIFO#1 Maker!
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_sll_preempt.json")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._last_known_collateral = 47.07
    now_t = time.time()

    ev_fifo1 = threading.Event()
    ev_buried = threading.Event()
    h._maker_anchor_preempt_events = {"IK_FIFO1": ev_fifo1, "IK_BURIED": ev_buried}
    h._inflight_maker_anchor_keys = {"IK_FIFO1", "IK_BURIED"}
    h.pending_entry_intents = {
        "INT_FIFO1": {
            "inflight_key": "IK_FIFO1",
            "market_id": "910001",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "live_maker_anchor_inflight": True,
            "fifo_rank1_verified": True,
            "notional_usd": 21.31,
            "anchor_bid_px": 0.992,
            "expiry_ts": now_t + 1800.0,
            "ts": now_t - 60.0,
            "heartbeat_ts": now_t,
        },
        "INT_BURIED": {
            "inflight_key": "IK_BURIED",
            "market_id": "910002",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "live_maker_anchor_inflight": True,
            "fifo_rank1_verified": False,
            "notional_usd": 21.32,
            "anchor_bid_px": 0.996,
            "expiry_ts": now_t + 5400.0,
            "ts": now_t - 60.0,
            "heartbeat_ts": now_t,
        },
    }

    def _watch_buried() -> None:
        if ev_buried.wait(timeout=1.5):
            h.pending_entry_intents.pop("INT_BURIED", None)
            h._inflight_maker_anchor_keys.discard("IK_BURIED")

    t_w = threading.Thread(target=_watch_buried, daemon=True)
    t_w.start()

    h.executor.get_collateral_balance = lambda: 47.07
    h.executor.get_token_tick_size = lambda tid, price_hint=None: 0.001
    h.executor.get_market_book = lambda tid: (
        {"bids": [{"price": "0.985", "size": "80"}], "asks": [{"price": "0.988", "size": "80"}]}
        if tid == "TOK_WIN_NBA"
        else {"bids": [{"price": "0.001", "size": "80"}], "asks": [{"price": "0.999", "size": "80"}]}
    )
    h.executor.execute_snipe_order = lambda **kw: types.SimpleNamespace(
        success=True,
        size=round(kw["notional_usd"] / kw["target_price"], 4),
        price=kw["target_price"],
        notional_usd=kw["notional_usd"],
        fee_usd=0.0,
        order_id="OID_NBA_SNIPE_1",
        execution_status="MATCHED_PENDING_SETTLEMENT",
        error="",
        details={"trade_ids": ["TR_NBA_1"]},
    )

    cand_nba = {
        "box_id": "WS_SNIPE_NBA_999",
        "dedupe_key": "DK_NBA_999",
        "box_type": "SINGLE_LEG_LOCK",
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
        "asset": "NBA",
        "ts_unix": now_t,
        "expiry_ts": now_t + 600.0,
        "rem_sec": 600.0,
        "box_cost_net": 0.988,
        "max_box_cost_net": 0.995,
        "max_opp_bid": 0.020,
        "hold_to_maturity": True,
        "p_model": 1.0,
        "leg_a_token_id": "TOK_WIN_NBA",
        "leg_a_opp_token_id": "TOK_OPP_NBA",
        "leg_a_market_id": "910999",
        "leg_a_condition_id": "0x" + "ab" * 32,
        "leg_a_side": "YES",
        "leg_a_label": "NBA Clinch Lock",
        "leg_a_limit_price": 0.988,
        "leg_a_fee_rate": 0.0,
        "leg_a_fee_exponent": 1.0,
    }
    res_nba = h._finish_single_leg_lock(
        cand_nba, "BOND1_UMA_RESOLUTION_CARRY", "TOK_WIN_NBA", "910999", "DK_NBA_999", {}, now_t, {}
    )
    assert res_nba["executed"] is True, f"Expected cash-starved NBA Taker snipe to preempt 1 buried Maker & execute: {res_nba}"
    assert ev_buried.is_set() is True, "Buried non-FIFO#1 Maker MUST be preempted to fund guaranteed Taker lock"
    assert ev_fifo1.is_set() is False, "Unrelated #1 FIFO Maker MUST be preserved!"


def test_dead_book_rejection_and_seller_flow_velocity_ranking(tmp_path: Path) -> None:
    from src.polymarket_research.alpha_124_shadow_daemon import extract_best_bid
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        emit_single_leg_maker_lock_cand_impl,
        score_live_candidate_velocity_ev,
    )

    cand_sink = tmp_path / "cands.jsonl"
    state_sink = tmp_path / "state.json"

    class _LiveDaemonStub:
        single_scan = False

        def __init__(self) -> None:
            self._last_d1_live_emit_ts = {}
            self._token_tick_sizes = {}

        def _can_emit_zero_loss_math_live(self, *args, **kwargs) -> bool:
            return True

    daemon = _LiveDaemonStub()
    now_t = time.time()

    # 1. Dead book: zero asks, shallow $18 bid, $12 24h volume -> REJECTED!
    dead_bk_win = {
        "bids": [{"price": "0.962", "size": "18.7"}],
        "asks": [],
        "_s2_meta": {"volume24hr": 12.0, "question": "Game 2: Obscure Esports Prop"},
    }
    bk_opp = {"bids": [{"price": "0.001", "size": "100"}], "asks": [{"price": "0.999", "size": "100"}]}
    ok_dead = emit_single_leg_maker_lock_cand_impl(
        daemon,
        sleeve_source="BOND1_UMA_RESOLUTION_CARRY",
        asset="ESPORTS",
        dedupe_key="BOND1_MKR_DEAD_1",
        pair_dedupe_key="BOND1_DEAD_1",
        token_id="TOK_DEAD_W",
        opp_token_id="TOK_DEAD_L",
        market_id="800001",
        condition_id="0x" + "11" * 32,
        side_label="YES",
        display_label="Dead Esports Prop",
        bk_win=dead_bk_win,
        bk_opp=bk_opp,
        neg_risk=False,
        close_ts=now_t + 3600.0,
        now_ts=now_t,
        min_resting_bid=0.940,
        max_resting_bid=0.996,
        min_maker_edge=0.003,
        max_opp_bid=0.008,
        hold_to_maturity=True,
        p_model=1.0,
        target_bid_px=None,
        maker_rebate_ps=0.0,
        extract_best_bid_fn=extract_best_bid,
        cand_file=cand_sink,
        state_file=state_sink,
        default_cand_path=tmp_path / "prod_d1.jsonl",
        default_state_path=tmp_path / "prod_state.json",
    )
    assert ok_dead is False, "Zero-ask, low-volume dead prop must NOT emit a live Maker candidate!"

    # 2. Active two-sided liquid market: asks present + $28,500 volume24hr -> ACCEPTED with volume_24h_usd recorded!
    live_bk_win = {
        "bids": [{"price": "0.994", "size": "40.0"}],
        "asks": [{"price": "0.997", "size": "65.0"}],
        "_s2_meta": {"volume24hr": 28500.0, "question": "Will NBA Celtics defeat Knicks?"},
    }
    ok_live = emit_single_leg_maker_lock_cand_impl(
        daemon,
        sleeve_source="BOND1_UMA_RESOLUTION_CARRY",
        asset="NBA",
        dedupe_key="BOND1_MKR_LIQ_1",
        pair_dedupe_key="BOND1_LIQ_1",
        token_id="TOK_LIQ_W",
        opp_token_id="TOK_LIQ_L",
        market_id="800002",
        condition_id="0x" + "22" * 32,
        side_label="YES",
        display_label="NBA Celtics YES",
        bk_win=live_bk_win,
        bk_opp=bk_opp,
        neg_risk=False,
        close_ts=now_t + 3600.0,
        now_ts=now_t,
        min_resting_bid=0.940,
        max_resting_bid=0.996,
        min_maker_edge=0.003,
        max_opp_bid=0.008,
        hold_to_maturity=True,
        p_model=1.0,
        target_bid_px=None,
        maker_rebate_ps=0.0,
        extract_best_bid_fn=extract_best_bid,
        cand_file=cand_sink,
        state_file=state_sink,
        default_cand_path=tmp_path / "prod_d1.jsonl",
        default_state_path=tmp_path / "prod_state.json",
    )
    assert ok_live is True
    emitted = json.loads(cand_sink.read_text(encoding="utf-8").splitlines()[-1])
    assert emitted["volume_24h_usd"] == pytest.approx(28500.0)
    assert emitted["ask_depth_usd"] > 60.0

    # 3. Velocity scoring: active $0.994 market with real sellers outranks askless $0.980 low-volume prop!
    sc_active = score_live_candidate_velocity_ev(
        {
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "box_cost_net": 0.994,
            "shares": 8,
            "expiry_ts": now_t + 2400.0,
            "queue_ahead_usd": 0.0,
            "ask_depth_usd": 64.8,
            "volume_24h_usd": 28500.0,
        },
        True,
        now_ts=now_t,
    )
    sc_illiquid = score_live_candidate_velocity_ev(
        {
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "box_cost_net": 0.980,
            "shares": 8,
            "expiry_ts": now_t + 2400.0,
            "queue_ahead_usd": 0.0,
            "ask_depth_usd": 0.0,
            "volume_24h_usd": 45.0,
        },
        True,
        now_ts=now_t,
    )
    assert sc_active > sc_illiquid


def test_esports_multi_game_event_deduplication_and_shallow_two_sided_queue_hold() -> None:
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        eval_sll_live_book_poll,
        extract_sll_event_group_key,
    )

    exp_ts = 1794300000.0
    k_g2 = extract_sll_event_group_key({
        "asset": "SPORTS_CHILD_MONEYLINE",
        "question": "Dota 2: Game 2: Team Spirit vs Team Liquid",
        "expiry_ts": exp_ts,
        "leg_a_market_id": "700102",
    })
    k_g3 = extract_sll_event_group_key({
        "asset": "SPORTS_CHILD_MONEYLINE",
        "question": "Dota 2: Game 3: Team Spirit vs Team Liquid",
        "expiry_ts": exp_ts + 600.0,
        "leg_a_market_id": "700103",
    })
    assert k_g2.startswith("EVTMATCH:")
    assert k_g2 == k_g3, f"Multi-game props of same match must share canonical event key: {k_g2} vs {k_g3}"

    lbl_g2 = extract_sll_event_group_key({
        "asset": "ESPORTS",
        "leg_a_label": "Esports Game 2: Team Spirit vs Team Liquid YES",
        "expiry_ts": exp_ts,
        "leg_a_market_id": "700202",
    })
    lbl_g3 = extract_sll_event_group_key({
        "asset": "ESPORTS",
        "leg_a_label": "Esports Game 3: Team Spirit vs Team Liquid NO",
        "expiry_ts": exp_ts + 300.0,
        "leg_a_market_id": "700203",
    })
    assert lbl_g2 == lbl_g3

    # Positional order for `eval_sll_live_book_poll`:
    # (bk_oc, bk_wc, candidate_box, posted_px, min_rb, max_rb, max_opp, tk_wf, enforce_b1_v53, is_s2_mkr,
    #  repost_n_in, b1_q_cap, b1_buried_s, exp_ts, buried_since_mono, collat_usd=...)
    cand_two_sided = {
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
        "p_model": 1.0,
        "min_maker_edge": 0.004,
        "_max_outbid_repegs": 0,
    }
    bk_two_sided = {
        "bids": [{"price": "0.995", "size": "25.0"}, {"price": "0.994", "size": "8.0"}],
        "asks": [{"price": "0.996", "size": "60.0"}],
    }
    bk_opp_clean = {"bids": [{"price": "0.001", "size": "100.0"}], "asks": [{"price": "0.020", "size": "50.0"}]}
    live_exp = time.time() + 1800.0

    act_20s, _, _, _ = eval_sll_live_book_poll(
        bk_opp_clean,
        bk_two_sided,
        cand_two_sided,
        0.994,
        0.940,
        0.994,
        0.008,
        0.001,
        True,
        False,
        3,
        350.0,
        12.0,
        live_exp,
        time.monotonic() - 20.0,
        collat_usd=47.07,
    )
    assert act_20s == "OK", "Shallow 1-tick outbid on locked active two-sided book MUST hold FIFO queue at 20s!"

    act_76s, _, _, _ = eval_sll_live_book_poll(
        bk_opp_clean,
        bk_two_sided,
        cand_two_sided,
        0.994,
        0.940,
        0.994,
        0.008,
        0.001,
        True,
        False,
        3,
        350.0,
        12.0,
        live_exp,
        time.monotonic() - 76.0,
        collat_usd=47.07,
    )
    assert act_76s == "BURIED"

    # Askless book (`asks=[]`) STILL cancels immediately at 20s (>= 12s stalk guard):
    act_askless_20s, _, _, _ = eval_sll_live_book_poll(
        bk_opp_clean,
        {"bids": [{"price": "0.995", "size": "25.0"}], "asks": []},
        cand_two_sided,
        0.994,
        0.940,
        0.994,
        0.008,
        0.001,
        True,
        False,
        3,
        350.0,
        12.0,
        live_exp,
        time.monotonic() - 20.0,
        collat_usd=47.07,
    )
    assert act_askless_20s == "BURIED"


def test_command_center_sleeve_status_truthfulness_under_pure_riskless(tmp_path: Path) -> None:
    import scripts.dominus_command_center as dcc

    ast.parse(dcc.REMOTE_PROBE_PY)
    (tmp_path / "config").mkdir()
    (tmp_path / "data/polymarket").mkdir(parents=True)
    (tmp_path / "config/polymarket_strategy_and_risk.json").write_text(
        (REPO_ROOT / "config/polymarket_strategy_and_risk.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "data/polymarket/live_harvester_state.json").write_text(
        json.dumps({"live_bankroll": 47.07, "total_account_equity": 97.58, "active_positions": {}, "closed_positions": []}),
        encoding="utf-8",
    )

    probe_src = dcc.REMOTE_PROBE_PY.replace(
        'root = pathlib.Path("/home/skybullet1987/quant_pipeline")',
        f"root = pathlib.Path(r'''{str(tmp_path)}''')",
    )
    ns: dict = {"__builtins__": __builtins__}
    captured: list[str] = []
    ns["print"] = lambda s, *a, **k: captured.append(str(s))
    exec(compile(probe_src, "<remote_probe_test>", "exec"), ns)
    assert captured, "Expected JSON output from REMOTE_PROBE_PY"
    payload = json.loads(captured[-1])
    by_sleeve = {row["sleeve"]: row for row in payload["polymarket_live"]["live_strategies"]}

    assert "80% Pool Cap" in by_sleeve["BOND1_UMA_RESOLUTION_CARRY"]["desc"]
    assert by_sleeve["BOND1_UMA_RESOLUTION_CARRY"]["is_active_riskless"] is True

    for blocked_sl in (
        "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        "CM_B3_PYTH_BARRIER_BOX",
        "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
    ):
        assert by_sleeve[blocked_sl]["desc"].startswith("PAUSED —"), f"{blocked_sl} should show PAUSED: {by_sleeve[blocked_sl]}"
        assert by_sleeve[blocked_sl]["is_active_riskless"] is False

    assert by_sleeve["MKR_REWARD_LOCKED_CARRY"]["desc"].startswith(("PAUSED —", "GATED ("))
    assert by_sleeve["MKR_REWARD_LOCKED_CARRY"]["is_active_riskless"] is False
