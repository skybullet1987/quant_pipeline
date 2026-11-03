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

