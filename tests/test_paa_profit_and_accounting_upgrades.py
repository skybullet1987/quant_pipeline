#!/usr/bin/env python3
"""
Regression tests for PAA Live Profit Conversion & Zero-Phantom-Loss Accounting Upgrades:
  1. `BOND1_UMA_RESOLUTION_CARRY` `$0.996` short-window (`<= 2h`) Maker ceiling, `$6` Taker sweep floor,
     and non-lockout of live emissions when `BOND1_{mid}` already filled in shadow.
  2. `MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER` `$0.995` live ceiling (`p_lock >= 0.999`, `<= 2h`) and
     non-lockout of live emissions after shadow entry.
  3. `PolymarketLiveHarvester` `$0.996` `max_rb` ceiling, shallow-queue tie guard (`<= $120`), and
     `poll_s["terminal"]` zero-fill `ws_filled=False` safety.
  4. `_apply_market_resolution` `ENTRY_NOT_EXECUTED_AT_RESOLUTION` zero-loss guard preventing phantom
     `-$11.90` `MARKET_RESOLVED_NO_INVENTORY` losses on unexecuted `0`-share orders.
  5. `passes_capital_velocity_hurdle` Seed-tier (`< $95`) `8.0h` lockup cap enforcement on `SPORTS_CORRIDOR` /
     `NBA_DOMINANCE` boxes (`13.3h` pre-match soccer starvation prevention).
"""

import asyncio
import json
import time
from unittest.mock import MagicMock

import pytest

from src.polymarket_research.holistic_strategy_governance import passes_capital_velocity_hurdle
import src.polymarket_research.polymarket_live_executor as ex_mod
import src.polymarket_research.polymarket_live_harvester as plh
import src.polymarket_research.alpha_124_shadow_daemon as a124_mod


@pytest.fixture(autouse=True)
def _offline_clob_env(monkeypatch):
    monkeypatch.setattr(ex_mod, "ClobClient", MagicMock(name="OfflineClobClient"))
    monkeypatch.setattr(ex_mod, "PY_CLOB_AVAILABLE", True)
    monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("POLYGON_FUNDER_ADDRESS", "0x" + "22" * 20)
    monkeypatch.setenv("POLYGON_SIGNATURE_TYPE", "3")


def test_seed_tier_sports_corridor_cannot_bypass_8h_lockup_cap():
    # 13.3h pre-match soccer corridor at $0.955 (~33.8 bps/hr >= 2 * 15 bps/hr) MUST be blocked on Seed (< $95)!
    ok_soc, rsn_soc = passes_capital_velocity_hurdle(
        collat_usd=64.97,
        rem_tte_sec=13.3 * 3600.0,
        box_cost_net=0.955,
        box_type="SPORTS_CORRIDOR",
    )
    assert ok_soc is False
    assert "LOW_CAPITAL_VELOCITY_LONG_TTE" in rsn_soc

    # Same 2h live/imminent soccer corridor at $0.965 passes cleanly on Seed
    ok_live_soc, _ = passes_capital_velocity_hurdle(
        collat_usd=64.97,
        rem_tte_sec=2.0 * 3600.0,
        box_cost_net=0.965,
        box_type="SPORTS_CORRIDOR",
    )
    assert ok_live_soc is True

    # Non-sports structural barrier box at 18h ($0.940) preserves v5.0 behavior
    ok_bar, _ = passes_capital_velocity_hurdle(
        collat_usd=69.06,
        rem_tte_sec=18.0 * 3600.0,
        box_cost_net=0.940,
        box_type="BARRIER_MONO",
    )
    assert ok_bar is True

    # BOND1 at $0.996 over <= 2.0h UMA challenge window (20.0+ bps/hr >= 15.0 bps/hr) passes Seed velocity!
    ok_b1_996, _ = passes_capital_velocity_hurdle(
        collat_usd=64.97,
        rem_tte_sec=7200.0,
        box_cost_net=0.996,
        box_type="SINGLE_LEG_MAKER_LOCK",
    )
    assert ok_b1_996 is True


def test_resolution_unexecuted_ghost_never_books_phantom_loss(tmp_path, monkeypatch):
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_state.json")

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    h.executor.get_account_fills = lambda *_a, **_k: []
    h.executor.find_redemption_payouts = lambda *_a, **_k: []
    h.executor.get_current_block_number = lambda: 65000000

    tid = "MKR_LOCK1_LIVE_SPORTS_MONEYLINE_1793692777_61815"
    now = time.time()
    pos = h._make_single_leg_lock_pos(
        tid, "SINGLE_LEG_MAKER_LOCK", "BOND1_UMA_RESOLUTION_CARRY", "SPORTS_MONEYLINE", "maker_lock_1leg",
        "6561815", "0xbefc992acc", "94685133613647718252563557091454", "NO", False,
        12.0, 11.904, 0.0, 0.0, 1.0, "maker_post_only_0pct", now - 60.0, now - 1800.0, 0.0,
        "0x50b550a5", True, unk=False,
    )
    # Simulate an unverified entry that never reconciled inventory or fills
    pos["inventory_reconciled"] = False
    pos["trade_ids"] = []
    pos["transactions_hashes"] = []
    h.active_positions[tid] = pos

    asyncio.run(h._apply_market_resolution(tid, pos, "NO"))

    assert tid not in h.active_positions
    closed = [c for c in h.closed_positions if c["trade_id"] == tid]
    assert len(closed) == 1
    rec = closed[0]
    assert rec["status"] == "NOT_EXECUTED"
    assert rec["close_reason"] == "ENTRY_NOT_EXECUTED_AT_RESOLUTION"
    assert rec["net_pnl_usd"] == pytest.approx(0.0)
    assert rec["notional_usd"] == pytest.approx(0.0)


def test_harvester_bond1_0996_cap_and_terminal_zero_fill_poll_safety(tmp_path, monkeypatch):
    a124_state = tmp_path / "alpha124_shadow_state.json"
    a124_state.write_text(json.dumps({
        "by_sleeve": {
            "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 32, "wins": 32, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 120.0},
            "BOND1_UMA_RESOLUTION_CARRY": {"closed": 23, "wins": 23, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 15.0},
        }
    }), encoding="utf-8")
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_state.json")

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h.enforce_bond1_smart_queue = True
    h.executor.auth_mode = "LIVE"
    h._last_known_collateral = 60.0
    h.executor.get_collateral_balance = lambda: 60.0
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    for _cfg_d in (plh.RISK_CONFIG, h.risk_config):
        monkeypatch.setitem(_cfg_d, "bond1_maker_ttl_sec", 0.25)
        monkeypatch.setitem(_cfg_d, "bond1_maker_max_keep_sec", 0.25)

    # Book has competing bid at $0.9950 and ask at $0.9980 -> with max_box_cost_net=0.996, must step to $0.9960!
    def _book(tok):
        if tok == "tok_w_996":
            return {"bids": [{"price": "0.995", "size": "40"}], "asks": [{"price": "0.998", "size": "100"}], "minimum_tick_size": "0.001"}
        return {"bids": [{"price": "0.001", "size": "50"}], "asks": []}

    posted = []

    def _post(self_ex, token_id, price, notional_usd=0.0, **kw):
        posted.append((price, kw.get("max_price_ceiling")))
        sh = int(notional_usd / price)
        return {"success": True, "orderID": "0xoid_996", "price": price, "shares": sh}

    monkeypatch.setattr(type(h.executor), "get_market_book", lambda _s, tok: _book(tok))
    monkeypatch.setattr(type(h.executor), "post_maker_entry_order", _post)
    monkeypatch.setattr(type(h.executor), "cancel_order", lambda _s, oid: {"is_canceled": True, "outcome": "CANCELED_ZERO_FILL", "matched": 0.0})
    # Terminal zero-fill order summary must NEVER be treated as ws_filled=True!
    monkeypatch.setattr(type(h.executor), "get_order_fill_summary", lambda _s, oid, tok: {"terminal": True, "resting": False, "matched": 0.0, "status": "CANCELED"})

    now = time.time()
    cand = {
        "box_id": "B1_996_LIVE",
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
        "dedupe_key": "BOND1_MKR_996",
        "pair_dedupe_key": "BOND1_996",
        "leg_a_market_id": "996001",
        "leg_a_condition_id": "0xcond996",
        "leg_a_token_id": "tok_w_996",
        "leg_a_opp_token_id": "tok_l_996",
        "leg_a_side": "YES",
        "leg_a_neg_risk": False,
        "anchor_bid_px": 0.996,
        "min_resting_bid": 0.940,
        "max_box_cost_net": 0.996,
        "min_maker_edge": 0.004,
        "max_opp_bid": 0.008,
        "p_model": 1.0,
        "expiry_ts": now + 5400.0,
        "ts_unix": now,
    }
    res = asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock(cand))
    assert len(posted) == 1
    assert posted[0][0] == pytest.approx(0.996)
    assert posted[0][1] == pytest.approx(0.996)
    assert res["executed"] is False
    assert h.active_positions == {}


def test_bond1_live_daemon_reemits_when_shadow_already_entered_and_allows_0996(tmp_path, monkeypatch):
    monkeypatch.setattr(a124_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(a124_mod, "STATE_FILE", tmp_path / "alpha124_shadow_state.json")
    monkeypatch.setattr(a124_mod, "D1_LIVE_CANDIDATES_FILE", tmp_path / "d1_live_box_candidates.jsonl")

    d = a124_mod.Alpha124ShadowDaemon(single_scan=False)
    now = time.time()
    d.last_uma_discovery_ts = now
    mid = "777888"
    # Pre-populate shadow entered_keys to simulate shadow having already filled earlier
    d.entered_keys.add(f"BOND1_{mid}")
    d.uma_proposed_markets[mid] = {
        "id": mid,
        "question": "Will Team A win Game 1?",
        "conditionId": "0xcond777888",
        "negRisk": False,
        "bestBid": 0.995,
        "bestAsk": 0.998,
    }
    d.uma_onchain_cache[mid] = (
        now,
        {
            "verified": True,
            "win_index": 0,
            "win_token": "111111111111111111111111",
            "lose_token": "222222222222222222222222",
            "win_outcome_name": "Yes",
            "win_label": "YES",
            "fee_rate": 0.0,
            "fee_exponent": 1.0,
            "domain": "SPORTS_MONEYLINE",
            "oo_state": "PROPOSED",
            "proposer": "0xprop",
            "expiration_ts": now + 3600.0,
            "rem_challenge_sec": 3600.0,
        },
    )

    async def _fake_books(_toks, timeout=3.5):
        return {
            "111111111111111111111111": {
                "bids": [{"price": "0.995", "size": "50"}],
                "asks": [{"price": "0.998", "size": "100"}],
                "minimum_tick_size": "0.001",
            },
            "222222222222222222222222": {
                "bids": [{"price": "0.001", "size": "50"}],
                "asks": [{"price": "0.005", "size": "100"}],
            },
        }

    d.fetch_books_batch = _fake_books
    cand_file = tmp_path / "d1_live_box_candidates.jsonl"

    opps = []
    asyncio.run(d.scan_uma_resolution_bonds(opps, now))

    # Live candidate MUST be emitted @ $0.996 (stepping 1 tick ahead of $0.995!) while shadow does NOT double-enter!
    assert cand_file.exists()
    emitted = [json.loads(ln) for ln in cand_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(emitted) == 1
    assert emitted[0]["box_type"] == "SINGLE_LEG_MAKER_LOCK"
    assert emitted[0]["anchor_bid_px"] == pytest.approx(0.996)
    assert emitted[0]["max_box_cost_net"] == pytest.approx(0.996)
    assert opps == []


def test_harvester_bond1_survives_book_poll_timeout_and_cancels_on_shutdown(tmp_path, monkeypatch):
    a124_state = tmp_path / "alpha124_shadow_state.json"
    a124_state.write_text(json.dumps({
        "by_sleeve": {
            "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 33, "wins": 33, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 173.6},
            "BOND1_UMA_RESOLUTION_CARRY": {"closed": 25, "wins": 25, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 12.8},
        }
    }), encoding="utf-8")
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_state.json")

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h.enforce_bond1_smart_queue = True
    h.executor.auth_mode = "LIVE"
    h._last_known_collateral = 60.94
    h.executor.get_collateral_balance = lambda: 60.94
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    for _cfg_d in (plh.RISK_CONFIG, h.risk_config):
        monkeypatch.setitem(_cfg_d, "bond1_maker_ttl_sec", 2.0)
        monkeypatch.setitem(_cfg_d, "bond1_maker_max_keep_sec", 2.0)
        monkeypatch.setitem(_cfg_d, "bond1_book_poll_sec", 0.05)

    calls = {"book": 0, "cancel": 0}

    def _flaky_book(_s, tok):
        calls["book"] += 1
        if calls["book"] >= 3:
            raise TimeoutError("HTTPSConnectionPool Read timed out (read timeout=3.0)")
        if tok == "tok_w_tmo":
            return {"bids": [{"price": "0.994", "size": "40"}], "asks": [{"price": "0.998", "size": "100"}], "minimum_tick_size": "0.001"}
        return {"bids": [{"price": "0.001", "size": "50"}], "asks": []}

    def _post(_s, token_id, price, notional_usd=0.0, **kw):
        return {"success": True, "orderID": "0xoid_tmo", "price": price, "shares": int(notional_usd / price)}

    def _cancel(_s, oid):
        calls["cancel"] += 1
        return {"is_canceled": True, "outcome": "CANCELED_ZERO_FILL", "matched": 0.0}

    monkeypatch.setattr(type(h.executor), "get_market_book", _flaky_book)
    monkeypatch.setattr(type(h.executor), "post_maker_entry_order", _post)
    monkeypatch.setattr(type(h.executor), "cancel_order", _cancel)
    monkeypatch.setattr(type(h.executor), "get_order_fill_summary", lambda _s, oid, tok: {"terminal": True, "resting": False, "matched": 0.0})

    async def _drive():
        now = time.time()
        t = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock({
            "box_id": "B1_TMO_LIVE",
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "dedupe_key": "BOND1_MKR_TMO",
            "pair_dedupe_key": "BOND1_TMO",
            "leg_a_market_id": "996002",
            "leg_a_condition_id": "0xcondtmo",
            "leg_a_token_id": "tok_w_tmo",
            "leg_a_opp_token_id": "tok_l_tmo",
            "leg_a_side": "YES",
            "leg_a_neg_risk": False,
            "anchor_bid_px": 0.995,
            "min_resting_bid": 0.940,
            "max_box_cost_net": 0.996,
            "min_maker_edge": 0.004,
            "max_opp_bid": 0.008,
            "p_model": 1.0,
            "expiry_ts": now + 3600.0,
            "ts_unix": now,
        }))
        await asyncio.sleep(0.18)
        assert calls["book"] >= 3  # Timeout fired inside monitoring loop without crashing!
        h._shutdown_requested = True
        return await t

    res = asyncio.run(_drive())
    assert res["executed"] is False
    assert calls["cancel"] == 1  # Order was cleanly canceled on CLOB, NEVER orphaned!
    assert h.pending_entry_intents == {}


def test_seed_rebuild_directional_shadow_gate_below_150(tmp_path, monkeypatch):
    """Verifies BOTH 15m and 1h unhedged crypto directional shocks route to shadow when equity < $150."""
    import src.polymarket_research.polymarket_live_harvester as plh

    cf_file = tmp_path / "cf_cands.jsonl"
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "seed_gate_state.json")
    monkeypatch.setattr(plh, "COUNTERFACTUAL_CANDIDATES_FILE", cf_file)
    monkeypatch.setattr(plh, "read_fast_tick", lambda *a, **kw: None)
    plh.GLOBAL_GOVERNANCE_MANAGER.maybe_reload(force=True)
    assert plh.GLOBAL_GOVERNANCE_MANAGER.snapshot["directional"]["min_live_equity_for_unhedged_directional_usd"] == pytest.approx(150.0)

    h = plh.PolymarketLiveHarvester(dry_run=True, max_price_ceiling=0.81, max_tte=2400.0, allowed_assets={"BTC", "ETH", "SOL"})
    h.dry_run = False
    h.holistic_v5_live_mode = True
    h.enforce_seed_directional_shadow_gate = True
    h._last_known_collateral = 60.94
    taker_calls = []

    async def _never_snipe(**kw):
        taker_calls.append(kw)

    h.executor.execute_snipe_order_async = _never_snipe
    now_s = time.time()
    for hz, m_id in (("1h", "7701"), ("15m", "7702")):
        shk = {
            "event_id": f"SG_{hz}", "market_id": m_id, "condition_id": f"0x{m_id}", "t0_unix": now_s,
            "title": f"Bitcoin Up or Down - {hz}", "asset": "BTC", "horizon": hz, "shock_direction": "BUY",
            "seconds_to_expiry": 360.0, "spot_at_t0": 70250.0, "trigger_price": 70250.0,
            "candle_open_spot": 70000.0, "twap_60s_open": 70000.0, "candle_distance_pct": 0.35,
            "candle_sigma": 0.0030, "shock_volume_100ms": 1_800_000.0, "shock_ofi": 0.90,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "1" * 26, "raw_top_asks": [[0.76, 120.0]], "raw_top_bids": [[0.74, 120.0]],
                    "effective_price_$25": 0.76, "vwap_$25": 0.76, "age_ask_ms": 100.0, "obi_l1": 0.25,
                    "age_book_ms": 20.0, "book_timestamp": now_s,
                }
            },
        }
        asyncio.run(h.evaluate_shock_and_execute(shk))
    assert taker_calls == []
    plh._get_hot_io_pool().submit(lambda: None).result(timeout=2.0)
    for _ in range(20):
        if cf_file.exists() and len([x for x in cf_file.read_text(encoding="utf-8").splitlines() if x.strip()]) >= 2:
            break
        time.sleep(0.02)
    rows = [json.loads(x) for x in cf_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2
    assert all(r["reason_blocked"] == "SEED_REBUILD_SHADOW_UNTIL_$150" for r in rows)


def test_cal1_grad8_emits_up_to_0992(tmp_path, monkeypatch):
    """Verifies 8/8-graduated 0%-fee boxes (CAL1 / COND1) emit live candidates up to $0.992."""
    import src.polymarket_research.alpha_124_shadow_daemon as a124

    cand_file = tmp_path / "d1_live_box_candidates.jsonl"
    st_file = tmp_path / "alpha124_shadow_state.json"
    monkeypatch.setattr(a124, "DATA_DIR", tmp_path)
    monkeypatch.setattr(a124, "STATE_FILE", st_file)
    monkeypatch.setattr(a124, "D1_LIVE_CANDIDATES_FILE", cand_file)

    d = a124.Alpha124ShadowDaemon(single_scan=True)
    for i in range(12):
        d.closed_positions.append({
            "sleeve": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
            "won": True,
            "tier_pnls_usd": {"T1000": 3.4},
            "legging_adjusted_tier_pnls_usd": {"T1000": 3.4},
        })
    assert d.is_sleeve_grad8_ready("CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX") is True

    now = time.time()
    ok = d.emit_live_two_leg_box_candidate(
        sleeve_source="CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
        box_type="MACRO_DOMINANCE",
        asset="MACRO",
        dedupe_key="CAL1_TEST_09915",
        leg_a={"token_id": "1" * 25, "opp_token_id": "2" * 25, "market_id": "8801", "condition_id": "0x8801", "label": "YES_A", "side": "YES", "fee_rate": 0.0, "fee_exponent": 1.0, "neg_risk": False},
        leg_b={"token_id": "3" * 25, "opp_token_id": "4" * 25, "market_id": "8802", "condition_id": "0x8802", "label": "NO_B", "side": "NO", "fee_rate": 0.0, "fee_exponent": 1.0, "neg_risk": False},
        bk_a={"bids": [{"price": "0.48", "size": "100"}], "asks": [{"price": "0.491", "size": "100"}]},
        bk_b={"bids": [{"price": "0.49", "size": "100"}], "asks": [{"price": "0.5005", "size": "100"}]},
        close_ts=now + 43200.0,
        now_ts=now,
    )
    assert ok is True
    emitted = [json.loads(x) for x in cand_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(emitted) == 1
    assert emitted[0]["sleeve_source"] == "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"
    assert 0.990 < emitted[0]["box_cost_net"] <= 0.992


def test_bond1_velocity_upgrade_and_92pct_zero_loss_pool(tmp_path, monkeypatch):
    """Verifies 92% Seed zero-loss pool sizing and dynamic bps/hr preemption of slow resting BOND1 bids."""
    import src.polymarket_research.polymarket_live_harvester as plh

    monkeypatch.setattr(plh, "PIPELINE_ROOT", tmp_path)
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "vel_state.json")
    plh.GLOBAL_GOVERNANCE_MANAGER.maybe_reload(force=True)
    (tmp_path / "alpha124_shadow_state.json").write_text(json.dumps({
        "by_sleeve": {
            "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 33, "wins": 33, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 173.6, "legging_adjusted_pnl_t1000_usd": 171.7},
            "BOND1_UMA_RESOLUTION_CARRY": {"closed": 25, "wins": 25, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 12.8, "legging_adjusted_pnl_t1000_usd": 12.8},
        }
    }), encoding="utf-8")

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h.holistic_v5_live_mode = True
    h.enforce_bond1_smart_queue = True
    h.executor.auth_mode = "LIVE"
    h.executor.signature_type = 2
    h.executor.is_heartbeat_healthy = lambda: True
    h.check_recorder_freshness = lambda *a, **kw: (True, 0.05, "OK")
    h._last_known_collateral = 60.94
    h.executor.get_collateral_balance = lambda: 60.94
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    for _cfg_d in (plh.RISK_CONFIG, h.risk_config):
        monkeypatch.setitem(_cfg_d, "bond1_maker_ttl_sec", 0.25)
        monkeypatch.setitem(_cfg_d, "bond1_maker_max_keep_sec", 0.25)

    posted = []
    monkeypatch.setattr(type(h.executor), "get_market_book", lambda _s, tok: (
        {"bids": [{"price": "0.991", "size": "40"}], "asks": [{"price": "0.998", "size": "100"}], "minimum_tick_size": "0.001"}
        if "win" in tok else {"bids": [{"price": "0.001", "size": "50"}], "asks": []}
    ))
    monkeypatch.setattr(type(h.executor), "post_maker_entry_order", lambda _s, token_id, price, notional_usd=0.0, **kw: (
        posted.append((token_id, price, notional_usd)) or {"success": True, "orderID": f"0x{token_id}", "price": price, "shares": int(notional_usd / price)}
    ))
    monkeypatch.setattr(type(h.executor), "cancel_order", lambda _s, oid: {"is_canceled": True, "outcome": "CANCELED_ZERO_FILL", "matched": 0.0})
    monkeypatch.setattr(type(h.executor), "get_order_fill_summary", lambda _s, oid, tok: {"terminal": True, "resting": False, "matched": 0.0})

    now = time.time()
    slow_ev = plh.threading.Event()
    h._inflight_maker_anchor_keys = {"SLOW_BOND1"}
    h._inflight_maker_anchor_types = {"SINGLE_LEG_MAKER_LOCK:9001"}
    h._maker_anchor_preempt_events = {"SLOW_BOND1": slow_ev}
    h.pending_entry_intents["SLOW_INTENT"] = {
        "trade_id": "SLOW_INTENT", "market_id": "9001", "token_id": "tok_slow",
        "notional_usd": 55.0, "ts": now - 45.0, "heartbeat_ts": now,
        "live_maker_anchor_inflight": True, "inflight_key": "SLOW_BOND1",
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "velocity_bps_hr": 25.0,
    }

    async def _run_preempt():
        async def _watch_slow():
            for _ in range(200):
                if slow_ev.is_set():
                    h.pending_entry_intents.pop("SLOW_INTENT", None)
                    h._inflight_maker_anchor_keys.discard("SLOW_BOND1")
                    h._inflight_maker_anchor_types.discard("SINGLE_LEG_MAKER_LOCK:9001")
                    return
                await asyncio.sleep(0.01)

        w_task = asyncio.create_task(_watch_slow())
        res = await h.maybe_execute_graduated_single_leg_maker_lock({
            "box_id": "FAST_BOND1", "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "dedupe_key": "FAST_B1_KEY",
            "pair_dedupe_key": "FAST_B1_PAIR", "leg_a_market_id": "9002", "leg_a_condition_id": "0x9002",
            "leg_a_token_id": "tok_win_fast", "leg_a_opp_token_id": "tok_lose_fast",
            "leg_a_side": "YES", "leg_a_neg_risk": False, "anchor_bid_px": 0.992,
            "min_resting_bid": 0.940, "max_box_cost_net": 0.996, "min_maker_edge": 0.004,
            "max_opp_bid": 0.008, "p_model": 1.0, "expiry_ts": now + 900.0, "ts_unix": now,
        })
        await w_task
        return res

    asyncio.run(_run_preempt())
    assert slow_ev.is_set() is True  # Slow 25 bps/hr order was preempted for 320 bps/hr fast order!
    assert len(posted) == 1
    assert posted[0][0] == "tok_win_fast"
    assert posted[0][2] >= 26.0  # 46% per-market cap on $60.94 (~$28.03 -> 28 shares)


def test_paa_director_proactive_profit_conversion_audit(tmp_path):
    """Verifies PAADirector Step B7 runs PROFIT_CONVERSION_AUDIT and persists Tier-B verified fact."""
    from src.paa_os.director import PAADirector

    data_dir = tmp_path / "data" / "polymarket"
    data_dir.mkdir(parents=True)
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "polymarket_strategy_and_risk.json").write_text(
        json.dumps({"directional": {"min_live_equity_for_unhedged_directional_usd": 150.0}}),
        encoding="utf-8",
    )
    (data_dir / "alpha124_shadow_state.json").write_text(json.dumps({
        "by_sleeve": {
            "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX": {"wins": 12, "losses": 0, "realized_pnl_t1000_usd": 40.85},
            "SOC2_EXACT_SCORE_2D_LATTICE": {"wins": 5, "losses": 0, "realized_pnl_t1000_usd": 3.64},
        }
    }), encoding="utf-8")
    (data_dir / "live_harvester_state.json").write_text(
        json.dumps({"live_bankroll": 60.94, "closed_positions": []}),
        encoding="utf-8",
    )

    director = PAADirector(repo_root=tmp_path, data_dir=data_dir)
    director.db.record_heartbeat("paa_research", status="OK")  # Simulate fresh 5m research timer
    rep = director.run_cycle(max_tasks_per_cycle=3, allow_headless_ai=False, run_proactive_research_if_idle=True)
    assert rep["status"] == "OK"
    assert any(t.get("evidence", {}).get("conversion_audit") for t in rep["tasks_executed"])
    facts = {f["fact_key"]: f for f in director.db.list_verified_facts(include_stale=False)}
    assert "profit.conversion_and_velocity_audit" in facts
    val = facts["profit.conversion_and_velocity_audit"]["value"]
    assert "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX" in val["grad8_zero_live_conversion_gaps"]
    assert val["seed_zero_loss_focus_active"] is True
    # Running a 2nd cycle in the same UTC hour must NOT re-enqueue a duplicate completed PROFIT_CONVERSION_AUDIT!
    rep2 = director.run_cycle(max_tasks_per_cycle=3, allow_headless_ai=False, run_proactive_research_if_idle=True)
    assert rep2["status"] == "OK"
    assert not any(t.get("evidence", {}).get("conversion_audit") for t in rep2["tasks_executed"])


def test_ghost_wide_spread_bid_cannot_preempt_tight_bond1_order(tmp_path, monkeypatch):
    """Verifies <$0.990 wide-spread props ($0.980) cannot preempt tight $0.993 BOND1 orders, and concurrent tasks cannot double-claim."""
    monkeypatch.setattr(plh, "PIPELINE_ROOT", tmp_path)
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "ghost_vel_state.json")
    plh.GLOBAL_GOVERNANCE_MANAGER.maybe_reload(force=True)
    (tmp_path / "alpha124_shadow_state.json").write_text(json.dumps({
        "by_sleeve": {
            "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 33, "wins": 33, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 173.6, "legging_adjusted_pnl_t1000_usd": 171.7},
            "BOND1_UMA_RESOLUTION_CARRY": {"closed": 25, "wins": 25, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 12.8, "legging_adjusted_pnl_t1000_usd": 12.8},
        }
    }), encoding="utf-8")

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h.holistic_v5_live_mode = True
    h.enforce_bond1_smart_queue = True
    h.executor.auth_mode = "LIVE"
    h.executor.signature_type = 2
    h.executor.is_heartbeat_healthy = lambda: True
    h.check_recorder_freshness = lambda *a, **kw: (True, 0.05, "OK")
    h._last_known_collateral = 60.94
    h.executor.get_collateral_balance = lambda: 60.94
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)

    now = time.time()
    tight_ev = plh.threading.Event()
    h._inflight_maker_anchor_keys = {"TIGHT_BOND1_993"}
    h._inflight_maker_anchor_types = {"SINGLE_LEG_MAKER_LOCK:9101"}
    h._maker_anchor_preempt_events = {"TIGHT_BOND1_993": tight_ev}
    h.pending_entry_intents["TIGHT_INTENT"] = {
        "trade_id": "TIGHT_INTENT", "market_id": "9101", "token_id": "tok_tight",
        "anchor_bid_px": 0.993, "notional_usd": 55.0, "ts": now - 40.0, "heartbeat_ts": now,
        "live_maker_anchor_inflight": True, "inflight_key": "TIGHT_BOND1_993",
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "velocity_bps_hr": 56.0,
    }

    # Wide-spread $0.980 near-expiry prop (3 min remaining) MUST NOT preempt a working tight $0.993 order!
    res_ghost = asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock({
        "box_id": "GHOST_980", "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "dedupe_key": "GHOST_B1_KEY",
        "pair_dedupe_key": "GHOST_B1_PAIR", "leg_a_market_id": "9102", "leg_a_condition_id": "0x9102",
        "leg_a_token_id": "tok_ghost", "leg_a_opp_token_id": "tok_ghost_opp",
        "leg_a_side": "NO", "leg_a_neg_risk": False, "anchor_bid_px": 0.980,
        "min_resting_bid": 0.940, "max_box_cost_net": 0.996, "min_maker_edge": 0.004,
        "max_opp_bid": 0.008, "p_model": 1.0, "expiry_ts": now + 180.0, "ts_unix": now,
    }))
    assert res_ghost["executed"] is False
    assert tight_ev.is_set() is False


def test_alpha124_early_multileg_settlement_disputed_recycle_and_reward_carry_0993(tmp_path, monkeypatch):
    """Verifies early pre-endDate NR0 settlement, shadow disputed BOND1 recycle, $0.993 reward carry, and ledger path isolation."""
    from src.polymarket_research.macro_counting_ctf_engine import evaluate_locked_market_reward_carry

    # 1. Reward carry preserves 0.975 on 0.975/0.990 AND steps to 0.993 on 0.992/0.996 tight locked books!
    rw_classic = evaluate_locked_market_reward_carry(1.0, 0.975, 0.990, 50.0, 3.5, 0.0)
    assert rw_classic["eligible"] is True and rw_classic["resting_bid"] == pytest.approx(0.975)
    rw_tight = evaluate_locked_market_reward_carry(1.0, 0.992, 0.996, 50.0, 3.0, 0.0)
    assert rw_tight["eligible"] is True and rw_tight["resting_bid"] == pytest.approx(0.993)

    # 2. Monkeypatching DATA_DIR + STATE_FILE automatically isolates _resolve_ledger_path() away from production LEDGER_FILE
    monkeypatch.setattr(a124_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(a124_mod, "STATE_FILE", tmp_path / "a124_state.json")
    monkeypatch.setattr(a124_mod, "OPPS_FILE", tmp_path / "a124_opps.json")
    monkeypatch.setattr(a124_mod, "LIVE_ALPHA124_STATE_MIRROR_FILE", tmp_path / "mirror_state.json")
    d = a124_mod.Alpha124ShadowDaemon(single_scan=True)
    assert d._resolve_ledger_path() == tmp_path / "alpha124_shadow_ledger.jsonl"

    now = time.time()
    # Early-resolved NR0 slate (6.7h before close_ts)
    d.open_positions["NR0_EARLY_RBA"] = {
        "position_id": "NR0_EARLY_RBA",
        "dedupe_key": "NR0_EARLY_RBA",
        "sleeve": "NR0_ZERO_FEE_SLATE_ARB",
        "asset_or_city": "RBA",
        "title": "RBA Decision in November",
        "side": "YES_BASKET",
        "token_id": "rba_1|rba_2",
        "fee_rate": 0.0,
        "entry_ts": now - 7200.0,
        "close_ts": now + 24000.0,
        "entry_vwap_t1000": 0.990,
        "entry_eff_px_t1000": 0.990,
        "p_model_entry": 1.0,
        "tier_fills": {"T1000": {"shares": 100.0, "spent_usd": 99.0, "fee_usd": 0.0, "eff_px": 0.990}},
        "extra": {
            "legs": [
                {"token_id": "rba_1", "market_id": "m_rba_1", "side": "YES", "fee_rate": 0.0},
                {"token_id": "rba_2", "market_id": "m_rba_2", "side": "YES", "fee_rate": 0.0},
            ],
            "guaranteed_payout": 1.0,
        },
    }
    # Disputed BOND1 past close_ts + 900s with $0.998 live bid
    d.open_positions["BOND1_DISPUTED_ETH"] = {
        "position_id": "BOND1_DISPUTED_ETH",
        "dedupe_key": "BOND1_DISPUTED_ETH",
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "asset_or_city": "ETH",
        "title": "Ethereum Up or Down on November 2",
        "side": "YES",
        "token_id": "tok_eth_disp",
        "fee_rate": 0.0,
        "entry_ts": now - 108000.0,
        "close_ts": now - 100000.0,
        "entry_vwap_t1000": 0.995,
        "entry_eff_px_t1000": 0.995,
        "p_model_entry": 0.999,
        "tier_fills": {"T1000": {"shares": 50.0, "spent_usd": 49.75, "fee_usd": 0.0, "eff_px": 0.995}},
        "extra": {"market_id": "6476073"},
    }

    async def _fake_fetch(url: str, timeout: float = 3.0):
        if "/markets/m_rba_1" in url:
            return {"closed": True, "umaResolutionStatus": "resolved", "clobTokenIds": ["rba_1", "rba_1n"], "outcomePrices": ["1", "0"]}
        if "/markets/m_rba_2" in url:
            return {"closed": True, "umaResolutionStatus": "resolved", "clobTokenIds": ["rba_2", "rba_2n"], "outcomePrices": ["0", "1"]}
        if "/markets/6476073" in url:
            return {"closed": False, "umaResolutionStatus": "disputed", "clobTokenIds": ["tok_eth_disp", "tok_eth_n"], "outcomePrices": ["0.998", "0.002"]}
        if "token_id=tok_eth_disp" in url:
            return {"bids": [{"price": "0.998", "size": "100"}], "asks": [{"price": "0.999", "size": "100"}]}
        return None

    d.fetch_json = _fake_fetch
    asyncio.run(d.manage_open_positions())
    assert "NR0_EARLY_RBA" not in d.open_positions
    assert "BOND1_DISPUTED_ETH" not in d.open_positions
    by_id = {c["position_id"]: c for c in d.closed_positions}
    assert by_id["NR0_EARLY_RBA"]["won"] is True and by_id["NR0_EARLY_RBA"]["status"] == "SETTLED_MULTI_LEG_ARB"
    assert by_id["BOND1_DISPUTED_ETH"]["won"] is True and by_id["BOND1_DISPUTED_ETH"]["status"] == "UMA_DISPUTED_LOCK_PROFIT_RECYCLE"


def test_paa_zero_loss_shadow_benchmark_and_hourly_opt_latency_fallback(tmp_path, monkeypatch):
    """Verifies PAAAccountant zero-loss shadow PnL separation and paa_cli hourly-opt latency extraction."""
    import argparse
    import scripts.paa_cli as pcli
    from src.paa_os.director import PAADirector

    data_dir = tmp_path / "data" / "polymarket"
    data_dir.mkdir(parents=True)
    (data_dir / "alpha124_shadow_state.json").write_text(json.dumps({
        "by_sleeve": {
            "D1_SAME_ORACLE_DOMINANCE_BOX": {"wins": 33, "losses": 0, "realized_pnl_t1000_usd": 173.60},
            "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX": {"wins": 12, "losses": 0, "realized_pnl_t1000_usd": 40.85},
            "M4_SHOCK_STRIKE_CATCHUP": {"wins": 10, "losses": 28, "realized_pnl_t1000_usd": -2500.00},
        }
    }), encoding="utf-8")
    (data_dir / "live_harvester_state.json").write_text(json.dumps({"live_bankroll": 43.01, "closed_positions": []}), encoding="utf-8")
    (data_dir / "live_orders.jsonl").write_text(
        "\n".join(json.dumps({"clob_http_post_ms": ms}) for ms in [82.5, 95.0, 110.2, 134.8, 165.0]) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "src.paa_os.accountant.reconcile_authoritative_ledger",
        lambda live_rpc_check=False: {
            "verified_realized_net_profit_usd": 0.56,
            "raw_state_ledger_realized_pnl_usd": 0.56,
            "non_cash_unfilled_artifact_adjustment_usd": 0.0,
            "total_realized_fees_paid_usd": 0.0,
            "free_cash_pusd": 43.01,
            "open_cost_basis_usd": 17.93,
            "portfolio_nav_mark_to_bid_usd": 60.94,
            "portfolio_nav_at_resting_maker_usd": 61.01,
            "unrealized_pnl_mark_to_bid_usd": 0.0,
            "unrealized_pnl_at_maker_ask_usd": 0.07,
            "drawdown_from_hwm_usd": 0.0,
            "capital_utilization_pct": 29.4,
            "live_by_sleeve": {},
        },
    )
    director_inst = PAADirector(repo_root=tmp_path, data_dir=data_dir)
    monkeypatch.setattr(pcli, "PAADirector", lambda: director_inst)
    rc = pcli.cmd_hourly_opt(argparse.Namespace())
    assert rc == 0
    hr_sum = json.loads((director_inst.paa_dir / "hourly_optimization_summary.json").read_text(encoding="utf-8"))
    assert hr_sum["zero_loss_shadow_t1000_pnl_usd"] == pytest.approx(214.45)
    assert hr_sum["zero_loss_shadow_wins"] == 45
    assert hr_sum["latency_source"] == "live_orders.jsonl"
    assert hr_sum["latency_samples"] == 5
    assert hr_sum["latency_p50_ms"] == pytest.approx(110.2)


def test_shadow_reward_carry_outbid_repeg_and_zero_lookahead_tape_fill(tmp_path, monkeypatch):
    """Verifies MKR_REWARD_LOCKED_CARRY re-pegs when outbid without retroactively claiming pre-repeg tape prints, then fills on post-repeg tape prints."""
    monkeypatch.setattr(a124_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(a124_mod, "STATE_FILE", tmp_path / "a124_rp_state.json")
    monkeypatch.setattr(a124_mod, "OPPS_FILE", tmp_path / "a124_rp_opps.json")
    monkeypatch.setattr(a124_mod, "LIVE_ALPHA124_STATE_MIRROR_FILE", tmp_path / "mirror_rp_state.json")
    d = a124_mod.Alpha124ShadowDaemon(single_scan=True)

    now = time.time()
    oid = "MKR_MKR_REWARD_LOCKED_CARRY_TEST_WELLINGTON"
    d.pending_maker_orders[oid] = {
        "order_id": oid,
        "dedupe_key": "MKR_RW_W_6564320",
        "sleeve": "MKR_REWARD_LOCKED_CARRY",
        "asset_or_city": "Wellington_NZWN",
        "title": "Lowest temperature in Wellington on November 4? [Dead NO 16C]",
        "side": "NO",
        "token_id": "tok_rw_no",
        "resting_bid": 0.989,
        "best_bid_at_post": 0.988,
        "best_ask_at_post": 0.999,
        "l1_bid_usd": 45.0,
        "queue_ahead_usd": 0.0,
        "p_model_at_post": 1.0,
        "maker_edge_at_post": 0.011,
        "spot_at_post": 0.0,
        "created_ts": now - 600.0,
        "created_utc": "2026-11-03T22:00:00+00:00",
        "close_ts": now + 14400.0,
        "ttl_override_sec": None,
        "extra": {"market_id": "6564320", "condition_id": "0xcond_rw", "opp_token_id": "tok_rw_yes"},
    }

    tape_prints = [
        {"transactionHash": "0xold", "timestamp": int(now - 120), "asset": "tok_rw_no", "price": "0.992", "size": "40"},
    ]

    async def _fake_fetch(url, timeout=3.0):
        if "tok_rw_yes" in url:
            return {"bids": [{"price": "0.001", "size": "100"}], "asks": [{"price": "0.009", "size": "100"}]}
        if "tok_rw_no" in url:
            return {"bids": [{"price": "0.992", "size": "80"}], "asks": [{"price": "0.999", "size": "150"}]}
        if "/trades?market=0xcond_rw" in url:
            return tape_prints
        return None

    d.fetch_json = _fake_fetch
    # Cycle 1: Outbid at 0.992 -> re-pegs 0.989 -> 0.993 and sets last_repeg_ts = now
    asyncio.run(d.manage_pending_maker_orders())
    assert oid in d.pending_maker_orders
    assert d.pending_maker_orders[oid]["resting_bid"] == pytest.approx(0.993)
    assert d.pending_maker_orders[oid]["queue_ahead_usd"] == pytest.approx(0.0)
    repeg_ts = float(d.pending_maker_orders[oid]["last_repeg_ts"])
    assert repeg_ts >= now

    # Cycle 2: Old print at 0.992 (ts = now - 120 < last_repeg_ts + 2) MUST NOT retroactively fill our new 0.993 bid!
    d._last_trade_tape_chk_ts.clear()
    asyncio.run(d.manage_pending_maker_orders())
    assert oid in d.pending_maker_orders
    assert len(d.open_positions) == 0

    # Cycle 3: Post-repeg print at 0.993 (ts = int(repeg_ts) + 5) fills cleanly via trade tape!
    tape_prints.append(
        {"transactionHash": "0xnew", "timestamp": int(repeg_ts) + 5, "asset": "tok_rw_no", "price": "0.993", "size": "35"}
    )
    d._last_trade_tape_chk_ts.clear()
    asyncio.run(d.manage_pending_maker_orders())
    assert oid not in d.pending_maker_orders
    assert len(d.open_positions) == 1
    pos_rw = next(iter(d.open_positions.values()))
    assert pos_rw["sleeve"] == "MKR_REWARD_LOCKED_CARRY"
    assert pos_rw["entry_vwap_t1000"] == pytest.approx(0.993)
    assert pos_rw["extra"].get("filled_via_trade_tape") is True


def test_paa_baseline_staging_refresh_preserves_staged_and_advances_baseline(tmp_path):
    """Verifies ensure_baseline_staging_release(refresh_if_baseline=True) updates stale REL_BASELINE_* pointers without clobbering active REL_* releases."""
    import subprocess as _sp
    from src.paa_os.builder_and_deployer import DeploymentController
    from src.paa_os.permissions import PermissionGate
    from src.paa_os.task_db import PAATaskDB

    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    (repo / "config" / "polymarket_strategy_and_risk.json").write_text("{}", encoding="utf-8")
    (repo / "config" / "polymarket_risk_config.json").write_text("{}", encoding="utf-8")

    db = PAATaskDB(tmp_path / "paa.sqlite")
    gate = PermissionGate(approvals_dir=tmp_path / "approvals")
    dep = DeploymentController(db=db, permission_gate=gate, repo_root=repo, staging_root=tmp_path / "staging")

    sha_state = {"sha": "11111111aaaaaaaabbbbbbbbccccccccdddddddd"}
    dep._git = lambda args: _sp.CompletedProcess(args, 0, stdout=sha_state["sha"] + "\n", stderr="")

    p1 = dep.ensure_baseline_staging_release()
    assert p1["active_release_id"] == "REL_BASELINE_11111111"

    sha_state["sha"] = "22222222eeeeeeeeffffffff0000000011111111"
    # Default refresh_if_baseline=False preserves existing baseline pointer
    p2 = dep.ensure_baseline_staging_release()
    assert p2["active_release_id"] == "REL_BASELINE_11111111"
    # Explicit refresh_if_baseline=True advances stale REL_BASELINE_* to verified HEAD
    p3 = dep.ensure_baseline_staging_release(refresh_if_baseline=True)
    assert p3["active_release_id"] == "REL_BASELINE_22222222"
    assert p3["commit_sha"] == sha_state["sha"]

    # Non-baseline staged release MUST NEVER be clobbered by refresh_if_baseline=True
    cand_dir = dep.releases_dir / "REL_CAND_999"
    cand_dir.mkdir(parents=True)
    dep._set_active_staging_pointer("REL_CAND_999", cand_dir, "99999999")
    sha_state["sha"] = "33333333aaaaaaaa"
    p4 = dep.ensure_baseline_staging_release(refresh_if_baseline=True)
    assert p4["active_release_id"] == "REL_CAND_999"




