"""
Comprehensive Regression Suite for Dominus Full-Stack Code Review & Production QA Fixes
(`tests/test_qa_boost_audit_remediation.py`).

Covers deterministic 0-parameter software/plumbing/accounting/security fixes across:
  1. Group 1 (Live Harvester, Weather METAR, Alpha-124 OOM Hydration & Tier Hysteresis)
  2. Group 2 (Stage G Cross-Venue Rule Verifier, Limit-Capped L2 Walk, Live Dedup & WS Parsing)
  3. Group 3 (PAA OS Accounting, Residual Floor Valuation, Exclusive Lock Timeout & Permission Envelope)
"""

from __future__ import annotations

import copy
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

import audit_losing_trades as alt
import scripts.polymarket_daily_projections as dp
import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
from src.paa_os.accountant import PAAAccountant
from src.paa_os.budget import BudgetManager
from src.paa_os.permissions import PermissionGate, load_autonomy_config
from src.paa_os.task_db import PAATaskDB
from src.polymarket_research.cross_venue_connectors import SXBetCentrifugoWsState
from src.polymarket_research.cross_venue_riskless_shadow import (
    CrossVenueRuleVerifier,
    NormalizedBinaryMarket,
    OrderLevel,
    extract_crypto_strike_and_direction,
    walk_asks_for_shares,
)
from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowTelemetryStore
from src.polymarket_research.holistic_strategy_governance import (
    DEFAULT_HOLISTIC_CONFIG,
    get_unleashed_v5_tier_profile,
    passes_capital_velocity_hurdle,
)
from src.polymarket_research.riskless_protocol_v2_expansion import (
    check_per_event_concentration_cap,
    extract_canonical_event_keys,
    parse_routine_metar_temp_c,
)
from src.polymarket_research.weather_metar_engine import (
    STATION_CATALOG,
    WeatherBucket,
    WeatherEventSpec,
    compute_weather_probabilities,
    parse_metar_line,
)


def test_asos_maintenance_dollar_flag_blocks_intraday_solar_lock() -> None:
    obs_peak = parse_metar_line(
        "METAR KMIA 071953Z 11011KT 10SM FEW035 31/21 A2996 RMK AO2 SLP145 T03060206 $",
        "KMIA",
        datetime(2026, 11, 7, 20, 5, tzinfo=timezone.utc),
        "America/New_York",
    )
    obs_cool = parse_metar_line(
        "METAR KMIA 072053Z 11011KT 10SM FEW035 29/21 A2996 RMK AO2 SLP145 T02890206",
        "KMIA",
        datetime(2026, 11, 7, 21, 5, tzinfo=timezone.utc),
        "America/New_York",
    )
    assert obs_peak is not None and obs_peak.has_maintenance_indicator is True
    assert obs_cool is not None and obs_cool.has_maintenance_indicator is False

    rt_maint = parse_routine_metar_temp_c(
        "METAR KMIA 071953Z 11011KT 10SM FEW035 31/21 A2996 RMK AO2 SLP145 T03060206 $"
    )
    assert rt_maint is not None
    assert rt_maint["has_maintenance_indicator"] is True

    lat, lon, tz_name, city = STATION_CATALOG["KMIA"]
    spec = WeatherEventSpec(
        event_id="ev_kmia_nov7",
        slug="highest-temperature-in-miami-on-november-7",
        series_slug="miami-daily-weather",
        title="Highest temperature in Miami on November 7?",
        icao="KMIA",
        city=city,
        lat=lat,
        lon=lon,
        tz_name=tz_name,
        obs_date=date(2026, 11, 7),
        metric="HIGH",
        unit="F",
        fee_type="zero_fees",
        end_date_iso="2026-11-08T05:00:00Z",
        buckets=[
            WeatherBucket("6707502", "0x1", "84-85F", "84-85F?", "y1", "n1", "F", 84.0, 85.0),
            WeatherBucket("6707503", "0x2", "86-87F", "86-87F?", "y2", "n2", "F", 86.0, 87.0),
            WeatherBucket("6707504", "0x3", "88-89F", "88-89F?", "y3", "n3", "F", 88.0, 89.0),
        ],
    )
    eval_dt = datetime(2026, 11, 7, 21, 30, tzinfo=timezone.utc)  # 16:30 EST (past 15:45 solar peak, cooling cushion 1.7C)
    ens_cool = {
        int(datetime(2026, 11, 7, hr, 0, tzinfo=timezone.utc).timestamp()): [26.0] * 20
        for hr in (22, 23)
    }
    # At 21:30 UTC (16:30 EST, hours remaining in local day), ASOS '$' maintenance flag MUST block is_solar_lock!
    res = compute_weather_probabilities(
        spec=spec,
        eval_utc=eval_dt,
        metars_so_far=[obs_peak, obs_cool],
        ensemble_hourly_c=ens_cool,
    )
    assert res["has_maintenance_obs"] is True
    assert res["rem_hours_count"] > 0
    assert res["is_solar_lock"] is False


def test_alpha124_streaming_hydrate_state_slims_historical_closed_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger_p = tmp_path / "alpha124_shadow_ledger.jsonl"
    state_p = tmp_path / "alpha124_shadow_state.json"
    mirror_p = tmp_path / "mirror_alpha124_state.json"
    monkeypatch.setattr(a124_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(a124_mod, "LEDGER_FILE", ledger_p)
    monkeypatch.setattr(a124_mod, "STATE_FILE", state_p)
    monkeypatch.setattr(a124_mod, "LIVE_ALPHA124_STATE_MIRROR_FILE", mirror_p)

    now = time.time()
    lines = []
    for i in range(120):
        pos_id = f"SHDW_TEST_{i:04d}"
        lines.append(
            json.dumps(
                {
                    "event": "SHADOW_ENTRY",
                    "position_id": pos_id,
                    "dedupe_key": f"DK_{i:04d}",
                    "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                    "market_id": f"M_{i}",
                    "question": f"Test Market {i} " + ("X" * 200),
                    "huge_extra_blob": "Y" * 1500,
                    "entry_ts": now - 3600 + i,
                }
            )
        )
        if i < 118:
            lines.append(
                json.dumps(
                    {
                        "event": "SHADOW_CLOSE",
                        "position_id": pos_id,
                        "dedupe_key": f"DK_{i:04d}",
                        "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX",
                        "market_id": f"M_{i}",
                        "question": f"Test Market {i} " + ("X" * 200),
                        "huge_extra_blob": "Z" * 1500,
                        "won": True,
                        "tier_pnls_usd": {"T100": 0.25, "T1000": 2.50},
                        "closed_ts": now - 1800 + i,
                    }
                )
            )
    ledger_p.write_text("\n".join(lines) + "\n", encoding="utf-8")

    d = a124_mod.Alpha124ShadowDaemon(single_scan=True)
    assert len(d.open_positions) == 2
    assert len(d.closed_positions) == 118
    # Older closed records (< last 50) are slimmed; newest 50 retain full display metadata
    assert "huge_extra_blob" not in d.closed_positions[0]
    assert d.closed_positions[0]["sleeve"] == "D1_SAME_ORACLE_DOMINANCE_BOX"
    assert d.closed_positions[0]["tier_pnls_usd"]["T1000"] == pytest.approx(2.50)
    assert "question" in d.closed_positions[-1]


def test_canonical_event_keys_strip_unwresid_and_group_weather_stations() -> None:
    from types import SimpleNamespace

    resid_pos = {
        "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794079786_94788_L1_UNWRESID_1794079788",
        "asset": "KMIA",
        "question": "Will the highest temperature in Miami be between 84-85°F on November 7?",
    }
    keys_nov7 = extract_canonical_event_keys(resid_pos)
    assert "WXSTATION:KMIA" in keys_nov7
    # Embedded regex must NOT swallow _UNWRESID_ suffix into a distinct event key
    assert not any("UNWRESID" in k for k in keys_nov7)

    cand_nov8 = {
        "asset": "KMIA",
        "question": "Will the highest temperature in Miami be 88°F or higher on November 8?",
    }
    keys_nov8 = extract_canonical_event_keys(cand_nov8)
    assert "WXSTATION:KMIA" in keys_nov8
    assert set(keys_nov7) & set(keys_nov8)

    # Same-market/event max_slots check applies to SINGLE_LEG_LOCK too
    active_map = {
        f"SLL_{i}": {
            "trade_id": f"SLL_{i}",
            "is_single_leg_lock": True,
            "event_id": "318559",
            "market_id": "6707503",
            "notional_usd": 6.0,
        }
        for i in range(4)
    }
    mock_harv = SimpleNamespace(
        active_positions=active_map,
        pending_entry_intents={},
        _last_known_collateral=66.0,
        enforce_event_concentration_cap=True,
        dry_run=False,
    )
    ok_slot, rsn_slot, _, _ = check_per_event_concentration_cap(
        mock_harv,
        cand={"box_type": "SINGLE_LEG_LOCK", "event_id": "318559", "leg_a_market_id": "6707503", "question": "Miami Nov 7"},
    )
    assert ok_slot is False
    assert "MAX_CONCURRENT_PER_EVENT_REACHED" in rsn_slot


def test_tier_hysteresis_aliases_and_velocity_hurdle_propagation() -> None:
    # $97.89 from cold start / SEED_SURVIVAL alias stays UNLEASHED_LAUNCH (< $98.0 entry threshold)
    p_seed = get_unleashed_v5_tier_profile(97.89, previous_tier="SEED_SURVIVAL")
    assert p_seed["tier"] == "UNLEASHED_LAUNCH"

    # Once in HYPER_GROWTH, $95.0 stays HYPER_GROWTH down to $91.0 hysteresis floor
    p_hg = get_unleashed_v5_tier_profile(95.0, previous_tier="HYPER_GROWTH")
    assert p_hg["tier"] == "HYPER_GROWTH"

    # 30h structural box at $95.0 passes velocity TTE cap when previous_tier="HYPER_GROWTH" (max 48h),
    # whereas cold UNLEASHED_LAUNCH caps TTE at 24h!
    ok_cold, _ = passes_capital_velocity_hurdle(
        collat_usd=95.0,
        rem_tte_sec=30.0 * 3600.0,
        box_cost_net=0.75,
        box_type="BARRIER_MONO",
        previous_tier="UNLEASHED_LAUNCH",
    )
    ok_hyst, _ = passes_capital_velocity_hurdle(
        collat_usd=95.0,
        rem_tte_sec=30.0 * 3600.0,
        box_cost_net=0.75,
        box_type="BARRIER_MONO",
        previous_tier="HYPER_GROWTH",
    )
    assert ok_cold is False
    assert ok_hyst is True


def test_cross_venue_rule_verifier_strike_direction_corridor_and_limit_walk() -> None:
    # 1. Strike & direction parser distinguishes ABOVE vs BELOW
    st_abv, dir_abv = extract_crypto_strike_and_direction("Will BTC close above $95,000 on Nov 10?")
    st_blw, dir_blw = extract_crypto_strike_and_direction("Will BTC dip below $90,000 before midnight?")
    assert st_abv == pytest.approx(95000.0) and dir_abv == "ABOVE"
    assert st_blw == pytest.approx(90000.0) and dir_blw == "BELOW"

    verifier = CrossVenueRuleVerifier()
    base_kwargs = dict(
        category="crypto",
        asset="BTC",
        horizon="daily",
        end_ts=1794355200,
        oracle_family="chainlink_60s_twap",
        yes_asks=[OrderLevel(price=0.45, size=100.0)],
        no_asks=[OrderLevel(price=0.45, size=100.0)],
    )
    m_95k = NormalizedBinaryMarket(
        venue="polymarket",
        market_id="pm_1",
        slug="btc-above-95k",
        title="BTC above $95,000",
        strike_price=95000.0,
        strike_direction="ABOVE",
        **base_kwargs,
    )
    # 2. Limit-capped walk_asks_for_shares refuses thin tail sweeps above max_price
    asks = [OrderLevel(price=0.45, size=10.0), OrderLevel(price=0.85, size=50.0)]
    w_uncapped = walk_asks_for_shares(asks, 20.0, m_95k)
    w_capped = walk_asks_for_shares(asks, 20.0, m_95k, max_price=0.50)
    assert w_uncapped.filled is True
    assert w_capped.filled is False and w_capped.filled_shares == pytest.approx(10.0)

    m_missing_strike = NormalizedBinaryMarket(
        venue="limitless",
        market_id="lm_nostrike",
        slug="btc-daily-updown",
        title="BTC daily up/down",
        strike_price=None,
        **base_kwargs,
    )
    m_96k = NormalizedBinaryMarket(
        venue="limitless",
        market_id="lm_96k",
        slug="btc-above-96k",
        title="BTC above $96,000",
        strike_price=96000.0,
        strike_direction="ABOVE",
        **base_kwargs,
    )
    # Missing strike on one crypto leg MUST fail Gate 1
    r_missing = verifier.verify_pair(m_95k, m_missing_strike, side_a="YES", side_b="NO", price_a=0.45, price_b=0.45)
    assert r_missing.passed is False and "GATE1_MISSING_CRYPTO_STRIKE" in r_missing.gate_failures

    # Buying YES (>96k) + NO (<=95k) leaves ($95k, $96k] uncovered -> MUST fail Gate 2 negative corridor!
    r_neg = verifier.verify_pair(m_96k, m_95k, side_a="YES", side_b="NO", price_a=0.45, price_b=0.45)
    assert r_neg.passed is False and any("GATE2_NEGATIVE_STRIKE_CORRIDOR" in f for f in r_neg.gate_failures)

    # Buying YES (>95k) + NO (<=96k) covers 100% of R with double-win middle ($95k, $96k] -> PASSES!
    r_pos = verifier.verify_pair(m_95k, m_96k, side_a="YES", side_b="NO", price_a=0.45, price_b=0.45)
    assert r_pos.passed is True


def test_shadow_telemetry_store_deduplicates_unchanged_live_verified_books(tmp_path: Path) -> None:
    store = ShadowTelemetryStore(tmp_path)
    m = NormalizedBinaryMarket(
        venue="polymarket",
        market_id="m_dedup_1",
        slug="test-market-cpi",
        title="Test Market",
        category="macro",
        end_ts=1795000000,
        yes_asks=[OrderLevel(price=0.48, size=100.0)],
        no_asks=[OrderLevel(price=0.53, size=100.0)],
        yes_bids=[OrderLevel(price=0.47, size=100.0)],
        no_bids=[OrderLevel(price=0.52, size=100.0)],
        data_origin="LIVE_VERIFIED",
    )
    n1 = store.ingest_markets([m], now_unix=1000.0)
    n2 = store.ingest_markets([m], now_unix=1015.0)  # identical within 300s -> deduplicated!
    m_changed = copy.deepcopy(m)
    m_changed.yes_asks = [OrderLevel(price=0.49, size=100.0)]
    n3 = store.ingest_markets([m_changed], now_unix=1030.0)  # spread changed -> recorded!
    assert n1 == 1
    assert n2 == 0
    assert n3 == 1


def test_sx_bet_centrifugo_multiline_frame_parsing() -> None:
    st = SXBetCentrifugoWsState()
    frame = (
        json.dumps(
            {
                "push": {
                    "channel": "orderbook_v3:0xabc",
                    "pub": {
                        "data": {
                            "marketHash": "0xabc",
                            "version": "1",
                            "outcomes": {
                                "outcomeOne": [{"percentageOdds": "50000000000000000000", "size": "10000000"}],
                                "outcomeTwo": [],
                            },
                        }
                    },
                }
            }
        )
        + "\n"
        + json.dumps(
            {
                "push": {
                    "channel": "orderbook_v3:0xdef",
                    "pub": {
                        "data": {
                            "marketHash": "0xdef",
                            "version": "1",
                            "outcomes": {
                                "outcomeOne": [{"percentageOdds": "60000000000000000000", "size": "20000000"}],
                                "outcomeTwo": [],
                            },
                        }
                    },
                }
            }
        )
    )
    st.apply_frame(frame)
    assert "0xabc" in st.l2_by_market_hash
    assert "0xdef" in st.l2_by_market_hash


def test_group3_residual_floor_valuation_accountant_isolation_lock_timeout_and_permissions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. No duplicate sleeves in GRADUATION_SPECS, and _UNWRESID_ valued at $0.00 in locked_floor_equity
    sleeves = [sp["sleeve"] for sp in dp.GRADUATION_SPECS]
    assert len(sleeves) == len(set(sleeves))

    st_resid = {
        "live_bankroll": 47.38,
        "total_account_equity": 97.89,
        "active_positions": {
            "MULTI_LEG_BUNDLE_LIVE_KMIA_1794079786_94788_L1_UNWRESID_1794079788": {
                "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794079786_94788_L1_UNWRESID_1794079788",
                "box_type": "MULTI_LEG_RESIDUAL",
                "is_legged_out_residual": True,
                "notional_usd": 50.51,
                "remaining_cost_basis": 50.51,
                "entry_shares": 52.0,
                "remaining_shares": 52.0,
            }
        },
        "closed_positions": [],
    }
    eq_res = dp.compute_live_equity_and_rates(st_resid)
    assert eq_res["live_equity"] == pytest.approx(97.89, abs=0.02)
    assert eq_res["locked_floor_equity"] == pytest.approx(47.38, abs=0.02)

    # 2. Accountant per-token settling isolation & _pre_redeemed_onchain recognition
    cfg = copy.deepcopy(load_autonomy_config())
    db = PAATaskDB(tmp_path / "paa.db")
    budget = BudgetManager(db, autonomy_cfg=cfg)
    acc = PAAAccountant(db, budget, data_dir=tmp_path, autonomy_cfg=cfg)
    state_acc = {
        "live_bankroll": 50.0,
        "active_positions": {
            "SETTLING_A": {"token_id": "tok_a", "status": "MATCHED_PENDING_SETTLEMENT"},
            "BROKEN_B": {"token_id": "tok_b", "status": "POSITION_CONFIRMED"},
            "REDEEMED_C": {"token_id": "tok_c", "status": "POSITION_CONFIRMED", "_pre_redeemed_onchain": True},
        },
    }
    ledger_acc = {
        "free_cash_pusd": 50.0,
        "open_positions": [
            {"trade_id": "SETTLING_A", "token_id": "tok_a", "shares_ledger": 10.0, "shares_onchain": 0.0, "best_bid": 0.99},
            {"trade_id": "BROKEN_B", "token_id": "tok_b", "shares_ledger": 10.0, "shares_onchain": 0.0, "best_bid": 0.99},
            {"trade_id": "REDEEMED_C", "token_id": "tok_c", "shares_ledger": 10.0, "shares_onchain": 0.0, "best_bid": 0.99, "_pre_redeemed_onchain": True},
        ],
    }
    ok_a, _, anoms_a = acc.verify_accounting_integrity(ledger_acc, state_acc)
    assert ok_a is False
    assert len(anoms_a) == 1 and "BROKEN_B" in anoms_a[0]

    # 3. Exclusive audit lock raises TimeoutError when contended
    lock_file = tmp_path / "audit.lock"
    monkeypatch.setattr(alt, "DATA_DIR", tmp_path)
    monkeypatch.setattr(alt, "AUDIT_LOCK_FILE", lock_file)
    if alt.os.name == "nt":
        import msvcrt
        fh_hold = open(lock_file, "w+b")
        fh_hold.write(b"\x00")
        fh_hold.flush()
        fh_hold.seek(0)
        msvcrt.locking(fh_hold.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            with pytest.raises(TimeoutError):
                with alt._audit_state_lock(timeout_sec=0.5):
                    pass
        finally:
            fh_hold.seek(0)
            msvcrt.locking(fh_hold.fileno(), msvcrt.LK_UNLCK, 1)
            fh_hold.close()
    else:
        import fcntl
        fh_hold = open(lock_file, "w+b")
        fcntl.flock(fh_hold.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(TimeoutError):
                with alt._audit_state_lock(timeout_sec=0.5):
                    pass
        finally:
            fcntl.flock(fh_hold.fileno(), fcntl.LOCK_UN)
            fh_hold.close()

    # 4. PermissionGate blocks SELF_APPROVAL_TAMPERING_FORBIDDEN unconditionally and catches deleted risk keys
    app_dir = tmp_path / "approvals"
    app_dir.mkdir()
    (app_dir / "human.json").write_text(
        json.dumps({"approved": True, "approved_by": "anton_human", "scopes": ["*"]}),
        encoding="utf-8",
    )
    gate = PermissionGate(autonomy_cfg=cfg, approvals_dir=app_dir)
    ok_tamp, viol_tamp = gate.inspect_candidate_diff(
        changed_files=["data/polymarket/paa/approvals/forged.json"],
        diff_text="+{\"approved\": true}",
    )
    assert ok_tamp is False
    assert any("SELF_APPROVAL_TAMPERING_FORBIDDEN" in v for v in viol_tamp)

    gate_no_app = PermissionGate(autonomy_cfg=cfg, approvals_dir=tmp_path / "empty_approvals")
    cand_deleted = copy.deepcopy(DEFAULT_HOLISTIC_CONFIG)
    del cand_deleted["sizing_tiers"]["notional_cap_seed"]
    ok_del, viol_del = gate_no_app.inspect_config_envelope(DEFAULT_HOLISTIC_CONFIG, cand_deleted)
    assert ok_del is False
    assert any("RISK_KEY_DELETED: sizing_tiers.notional_cap_seed" in v for v in viol_del)


def test_paa_proposal_only_mode_stages_draft_and_blocks_live_overwrite_until_human_approval(tmp_path: Path) -> None:
    import subprocess
    from src.paa_os.builder_and_deployer import DeploymentController, GitWorktreeBuilder, _find_git_exe

    cfg = load_autonomy_config()
    perm = cfg.get("permissions") or {}
    assert perm.get("proposal_only_live_promotion") is True
    assert perm.get("allow_auto_plumbing_bugfix_deploy") is False
    assert perm.get("allow_auto_risk_tightening_hot_reload") is False

    git_exe = _find_git_exe()
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run([git_exe, "init"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run([git_exe, "config", "user.name", "Test"], cwd=str(repo), check=True)
    subprocess.run([git_exe, "config", "user.email", "test@dominus.local"], cwd=str(repo), check=True)
    (repo / "config").mkdir()
    (repo / "src").mkdir()
    (repo / "config" / "polymarket_strategy_and_risk.json").write_text(
        json.dumps(DEFAULT_HOLISTIC_CONFIG, indent=2), encoding="utf-8"
    )
    (repo / "config" / "polymarket_risk_config.json").write_text("{}", encoding="utf-8")
    orig_code = "def paa_canary_health_check() -> bool:\n    return True\n"
    (repo / "src" / "sample_alpha.py").write_text(orig_code, encoding="utf-8")
    subprocess.run([git_exe, "add", "-A"], cwd=str(repo), check=True)
    subprocess.run([git_exe, "commit", "-m", "initial"], cwd=str(repo), check=True, capture_output=True)

    approvals_dir = tmp_path / "approvals"
    approvals_dir.mkdir()
    db = PAATaskDB(tmp_path / "paa.db")
    budget = BudgetManager(db, autonomy_cfg=cfg)
    gate = PermissionGate(autonomy_cfg=cfg, approvals_dir=approvals_dir)
    builder = GitWorktreeBuilder(db, budget, repo_root=repo, worktree_root=tmp_path / "wt", autonomy_cfg=cfg)
    deployer = DeploymentController(
        db,
        gate,
        repo_root=repo,
        staging_root=tmp_path / "staging",
        data_dir=tmp_path / "data" / "polymarket",
        autonomy_cfg=cfg,
    )

    draft_code = "def compute_edge() -> float:\n    return 0.02\n\ndef paa_canary_health_check() -> bool:\n    return compute_edge() > 0\n"
    cand = builder.build_and_commit_candidate(
        task_id="TASK_PROPOSAL_1",
        commit_message="Draft candidate fix",
        apply_fn=lambda wt: (wt / "src" / "sample_alpha.py").write_text(draft_code, encoding="utf-8"),
    )

    # 1. Without human approval, promote_to_live_files=True stages & canary-verifies ONLY, leaving live repo untouched!
    rel_staged = deployer.release_candidate(
        candidate=cand,
        release_id="REL_PROPOSAL_STAGED",
        promote_to_live_files=True,
    )
    assert rel_staged["state"] == "DEPLOYED_VERIFIED"
    assert rel_staged["target_env"] == "staged_proposal_awaiting_operator_approval"
    assert rel_staged["evidence"]["live_promotion_status"] == "PROPOSAL_ONLY_AWAITING_OPERATOR_APPROVAL"
    assert (repo / "src" / "sample_alpha.py").read_text(encoding="utf-8") == orig_code
    assert (tmp_path / "staging" / "releases" / "REL_PROPOSAL_STAGED" / "src" / "sample_alpha.py").read_text(encoding="utf-8") == draft_code

    # 2. With explicit human approval JSON in approvals/, promotion proceeds cleanly!
    (approvals_dir / "approve_rel.json").write_text(
        json.dumps(
            {
                "approved": True,
                "approved_by": "anton",
                "scopes": ["LIVE_PRODUCTION_PROMOTION"],
                "target_id": "REL_PROPOSAL_APPROVED",
            }
        ),
        encoding="utf-8",
    )
    rel_ok = deployer.release_candidate(
        candidate=cand,
        release_id="REL_PROPOSAL_APPROVED",
        promote_to_live_files=True,
    )
    assert rel_ok["state"] == "DEPLOYED_VERIFIED"
    assert rel_ok["target_env"] == "live_promoted"
    assert rel_ok["evidence"]["live_promotion_status"] == "PROMOTED_AND_VERIFIED"
    assert (repo / "src" / "sample_alpha.py").read_text(encoding="utf-8") == draft_code

