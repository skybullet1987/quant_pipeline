#!/usr/bin/env python3
"""
Regression & adversarial unit tests for Maker Queue Retention, UMA P0 Fault Isolation,
S2 Fast-Gun Confinement, User-WS Post-Auth Keepalive, and PAA Ghost-Order Hygiene:
  (a) `_scan_phase2_macro_counting_gas` `AAA_GAS` (`is_reward_locked_carry_live_ready`) +
      fault-isolated `scan_uma_resolution_bonds` + post-liveness `close_est` + `BOND2` dedupe.
  (b) `S2` Maker preemption ban + 1-slot concurrent cap + `BTC/ETH/SOL` asset priority +
      `min_lot_shares=5` & `$22.50` cap + `cap_bond1_maker_for_gatling_reserve` `inflight_s2_usd`.
  (c) `compute_sll_maker_keep_and_renew` `#1` top-of-book renewal vs buried non-renewal +
      UMA `BOND1`/`BOND2` `60s` expiry exemption + partial-fill `notional_usd` sync.
  (d) `PolymarketUserWsCache` post-auth `"PING"` loop ordering, `"PONG"` health refresh, and cleanup.
  (e) `PAAAccountant` & `PAAMonitor` `heartbeat_ts` freshness + `>3600s` untracked CLOB ghost
      filtering + fail-closed `"already canceled or matched"` zero-fill cancel resolution.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
import src.polymarket_research.polymarket_live_executor as ex_mod
import src.polymarket_research.polymarket_live_harvester as plh
import src.polymarket_research.polymarket_ws_streams as ws_mod
from src.paa_os.accountant import PAAAccountant
from src.paa_os.budget import BudgetManager
from src.paa_os.monitor import PAAMonitor
from src.paa_os.task_db import PAATaskDB
from src.polymarket_research.riskless_protocol_v2_expansion import (
    cap_bond1_maker_for_gatling_reserve,
    compute_sll_and_carry_gatling_budget,
    compute_sll_maker_keep_and_renew,
    select_sll_velocity_preempt_target,
)
from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec


@pytest.fixture(autouse=True)
def _offline_clob_env(tmp_path, monkeypatch):
    monkeypatch.setattr(ex_mod, "ClobClient", MagicMock(name="OfflineClobClient"))
    monkeypatch.setattr(ex_mod, "PY_CLOB_AVAILABLE", True)
    monkeypatch.setattr(a124_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(a124_mod, "STATE_FILE", tmp_path / "alpha124_shadow_state.json")
    monkeypatch.setattr(a124_mod, "LEDGER_FILE", tmp_path / "alpha124_shadow_ledger.jsonl")
    monkeypatch.setattr(a124_mod, "OPPS_FILE", tmp_path / "alpha124_live_opportunities.json")
    monkeypatch.setattr(a124_mod, "MARKET_TELEMETRY_FILE", tmp_path / "alpha124_market_telemetry.jsonl")
    monkeypatch.setattr(a124_mod, "LIVE_ALPHA124_STATE_MIRROR_FILE", tmp_path / "_isolated_a124_mirror.json")
    monkeypatch.setattr(a124_mod, "D1_LIVE_CANDIDATES_FILE", tmp_path / "d1_live_box_candidates.jsonl")
    monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("POLYGON_FUNDER_ADDRESS", "0x" + "22" * 20)
    monkeypatch.setenv("POLYGON_SIGNATURE_TYPE", "3")


# ---------------------------------------------------------------------------
# (a) AAA_GAS AttributeError fix + UMA fault isolation + post-liveness + BOND2
# ---------------------------------------------------------------------------


def test_aaa_gas_reward_carry_no_attribute_error_and_uma_bonds_execute(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone

    now = time.time()
    now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
    today_str = now_dt.strftime("%Y-%m-%d")
    end_iso = (now_dt + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")

    cand_file = tmp_path / "d1_live_box_candidates.jsonl"
    monkeypatch.setattr(a124_mod, "D1_LIVE_CANDIDATES_FILE", cand_file)
    monkeypatch.setattr(
        a124_mod,
        "fetch_aaa_national_gas_sync",
        lambda: {"current_regular": 3.150, "as_of_date": today_str},
    )

    d = a124_mod.Alpha124ShadowDaemon(single_scan=False)

    # Seed an AAA_GAS market whose bracket ($3.10 - $3.20) is clinched by current_regular=3.150
    # and whose book has bid=0.990, ask=0.996 (triggers MKR_REWARD_LOCKED_CARRY live-ready check!)
    d.gas_events_raw = {
        "us-gas-price-daily": [
            {
                "slug": f"us-gas-price-on-{today_str}",
                "title": f"US National Regular Gas on {today_str}",
                "endDate": end_iso,
                "negRisk": False,
                "closed": False,
                "markets": [
                    {
                        "id": "gas_mkt_1",
                        "conditionId": "0xcond_gas_1",
                        "groupItemTitle": "$3.10 - $3.20",
                        "question": f"US regular gas $3.10 - $3.20 on {today_str}?",
                        "clobTokenIds": json.dumps(["tok_gas_yes", "tok_gas_no"]),
                        "rewardsMinSize": 20,
                        "rewardsMaxSpread": 2.0,
                        "negRisk": False,
                        "closed": False,
                    }
                ],
            }
        ]
    }

    uma_called = {"count": 0}

    async def _fake_uma(opps_out, now_ts=None):
        uma_called["count"] += 1
        opps_out.append({"sleeve": "BOND1_UMA_RESOLUTION_CARRY", "market": "UMA_OK"})

    async def _fake_books(toks, timeout=3.0):
        return {
            "tok_gas_yes": {"bids": [{"price": "0.990", "size": "80"}], "asks": [{"price": "0.996", "size": "80"}]},
            "tok_gas_no": {"bids": [{"price": "0.002", "size": "80"}], "asks": [{"price": "0.010", "size": "80"}]},
        }

    monkeypatch.setattr(d, "fetch_books_batch", _fake_books)
    monkeypatch.setattr(d, "scan_uma_resolution_bonds", _fake_uma)

    opps = []
    asyncio.run(d._scan_phase2_macro_counting_gas(opps, now))

    assert uma_called["count"] == 1
    sleeves = [o["sleeve"] for o in opps]
    assert "MKR_REWARD_LOCKED_CARRY" in sleeves
    assert "BOND1_UMA_RESOLUTION_CARRY" in sleeves


def test_uma_bonds_isolated_when_upstream_macro_scanner_raises(tmp_path, monkeypatch):
    d = a124_mod.Alpha124ShadowDaemon(single_scan=False)
    now = time.time()

    async def _boom(_opps, _now):
        raise RuntimeError("simulated upstream macro counting crash")

    uma_called = {"ok": False}

    async def _fake_uma(opps_out, now_ts=None):
        uma_called["ok"] = True
        opps_out.append({"sleeve": "BOND1_UMA_RESOLUTION_CARRY", "market": "ISOLATED_OK"})

    monkeypatch.setattr(d, "_scan_phase2_macro_counting_gas_core", _boom)
    monkeypatch.setattr(d, "scan_uma_resolution_bonds", _fake_uma)

    opps = []
    asyncio.run(d._scan_phase2_macro_counting_gas(opps, now))
    assert uma_called["ok"] is True
    assert [o["sleeve"] for o in opps] == ["BOND1_UMA_RESOLUTION_CARRY"]


def test_uma_post_liveness_horizon_and_bond2_dedupe_plus_shadow_non_starvation(tmp_path, monkeypatch):
    cand_file = tmp_path / "d1_live_box_candidates.jsonl"
    monkeypatch.setattr(a124_mod, "D1_LIVE_CANDIDATES_FILE", cand_file)

    d = a124_mod.Alpha124ShadowDaemon(single_scan=False)
    now = time.time()
    d.last_uma_discovery_ts = now

    # Case 1: Post-liveness undisputed market (expiration_ts = now - 45s, rem_challenge_sec = 0.0)
    # Previously close_est = max(now+120, exp+60) = now+120 failed `_b1_rem_s > 120.0`!
    d.uma_proposed_markets = {
        "m_post": {
            "id": "m_post",
            "conditionId": "0xcond_post",
            "question": "Lakers vs Heat final winner?",
            "negRisk": False,
        }
    }
    d.uma_onchain_cache["m_post"] = (
        now,
        {
            "verified": True,
            "win_index": 0,
            "win_token": "tok_post_w",
            "lose_token": "tok_post_l",
            "win_label": "YES",
            "win_outcome_name": "Heat",
            "domain": "SPORTS_MONEYLINE",
            "oo_state": 2,
            "proposer": "0xprop",
            "expiration_ts": now - 45.0,
            "rem_challenge_sec": 0.0,
            "proposal_age_sec": 7245.0,
            "eff_liveness_sec": 7200.0,
            "fee_rate": 0.0,
            "fee_exponent": 1.0,
        },
    )
    monkeypatch.setattr(a124_mod, "passes_uma_bond_dispute_guard", lambda m, v: True)
    monkeypatch.setattr(a124_mod, "verify_uma_against_nba_live", lambda m, idx, board: (True, "OK"))

    async def _books_post(_toks, timeout=3.5):
        return {
            "tok_post_w": {"bids": [{"price": "0.994", "size": "50"}], "asks": [{"price": "0.999", "size": "50"}]},
            "tok_post_l": {"bids": [{"price": "0.001", "size": "50"}], "asks": [{"price": "0.004", "size": "50"}]},
        }

    monkeypatch.setattr(d, "fetch_books_batch", _books_post)
    d.entered_keys.add("BOND1_m_post")

    opps = []
    asyncio.run(d.scan_uma_resolution_bonds(opps, now_ts=now))
    emitted_1 = [json.loads(ln) for ln in cand_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(emitted_1) == 1
    assert emitted_1[0]["dedupe_key"] == "BOND1_MKR_m_post"
    assert emitted_1[0]["expiry_ts"] == pytest.approx(now + 900.0)

    # Case 2: Final-hour MOOv2 market where BOTH BOND1 Maker and BOND2 Maker qualify:
    # `_b1_mkr_emitted == True` MUST suppress duplicate `BOND2_m_wl_MKR`!
    cand_file.unlink()
    d.uma_proposed_markets = {
        "m_wl": {
            "id": "m_wl",
            "conditionId": "0xcond_wl",
            "question": "BTC above $90k at close?",
            "negRisk": False,
        }
    }
    d.uma_onchain_cache["m_wl"] = (
        now,
        {
            "verified": True,
            "win_index": 0,
            "win_token": "tok_wl_w",
            "lose_token": "tok_wl_l",
            "win_label": "YES",
            "win_outcome_name": "Yes",
            "domain": "CRYPTO",
            "oo_state": 1,
            "proposer": "0xwl",
            "expiration_ts": now + 900.0,
            "rem_challenge_sec": 900.0,
            "proposal_age_sec": 6300.0,
            "eff_liveness_sec": 7200.0,
            "fee_rate": 0.0,
            "fee_exponent": 1.0,
        },
    )
    monkeypatch.setattr(
        a124_mod,
        "verify_bond2_moov2_final_hour_sync",
        lambda m, rpc, t: {
            "verified": True,
            "domain": "CRYPTO",
            "win_label": "YES",
            "win_outcome_name": "Yes",
            "rem_challenge_sec": 900.0,
            "fee_rate": 0.0,
            "fee_exponent": 1.0,
            "oo_address": "0xoo2",
        },
    )

    async def _books_wl(_toks, timeout=3.5):
        return {
            "tok_wl_w": {"bids": [{"price": "0.995", "size": "40"}], "asks": [{"price": "0.999", "size": "40"}]},
            "tok_wl_l": {"bids": [{"price": "0.001", "size": "40"}], "asks": [{"price": "0.004", "size": "40"}]},
        }

    monkeypatch.setattr(d, "fetch_books_batch", _books_wl)
    d.entered_keys.add("BOND1_m_wl")
    d.entered_keys.add("BOND2_m_wl")  # Shadow already entered BOND2 earlier!

    asyncio.run(d.scan_uma_resolution_bonds([], now_ts=now))
    emitted_2 = [json.loads(ln) for ln in cand_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert [c["dedupe_key"] for c in emitted_2] == ["BOND1_MKR_m_wl"]

    # Case 3: If BOND1 Maker does NOT emit (e.g. BOND1 taker filled @ 0.9975, while BOND2 taker asks empty/unfilled),
    # shadow `BOND2_m_wl in entered_keys` must NOT starve live `BOND2_m_wl` emission!
    cand_file.unlink()
    orig_emit_mkr = d.emit_live_single_leg_maker_lock_candidate
    monkeypatch.setattr(
        d,
        "emit_live_single_leg_maker_lock_candidate",
        lambda **kw: False if kw.get("sleeve_source") == "BOND1_UMA_RESOLUTION_CARRY" else orig_emit_mkr(**kw),
    )
    opps_b2 = []
    asyncio.run(d.scan_uma_resolution_bonds(opps_b2, now_ts=now))
    emitted_3 = [json.loads(ln) for ln in cand_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert [c["dedupe_key"] for c in emitted_3] == ["BOND2_m_wl_MKR"]
    assert opps_b2 == []  # Shadow did NOT double-enter because `_shadow_b2_free` is False!


# ---------------------------------------------------------------------------
# (b) S2 Maker preemption ban, 1-slot cap, BTC/ETH/SOL priority, min_lot_shares=5
# ---------------------------------------------------------------------------


def test_s2_maker_preemption_banned_and_passive_cannibalism_guarded():
    now = 1_793_875_200.0
    h = SimpleNamespace(
        _maker_anchor_preempt_events={"BOND1_HEAT": asyncio.Event(), "MLK_NBA": asyncio.Event()},
        _claimed_velocity_preempts=set(),
        pending_entry_intents={
            "i_b1": {
                "live_maker_anchor_inflight": True,
                "inflight_key": "BOND1_HEAT",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "anchor_bid_px": 0.995,  # 50 bps; 120s left -> 0.25h floor => 200 bps/h
                "expiry_ts": now + 120.0,
                "ts": now - 400.0,
            },
            "i_mlk": {
                "live_maker_anchor_inflight": True,
                "inflight_key": "MLK_NBA",
                "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                "anchor_bid_px": 0.985,  # 150 bps; 300s left -> 1.50h floor => 100 bps/h
                "expiry_ts": now + 300.0,
                "ts": now - 120.0,  # < 180s age -> protected from passive cannibalism!
            },
        },
    )

    # 1. S2 Maker candidates NEVER preempt resting orders regardless of apparent bps/hr
    for s2_sl in ("S2_RTDS_EXACT_TWAP_INTEGRATOR", "S2_EXACT_TWAP_LOCK"):
        vel, key = select_sll_velocity_preempt_target(
            h, cand_edge_hr=50_000.0, is_s2_mkr=True, vel_mult=1.80, now_pe=now, cand_sleeve=s2_sl
        )
        assert (vel, key) == (0.0, "")

    # 2. Passive candidate @ 350 bps/h CANNOT preempt `BOND1_HEAT` (200 bps/h needs >= max(600, 250) = 600)
    #    and CANNOT preempt `MLK_NBA` because `MLK_NBA` age is 120s (< 180s)!
    assert select_sll_velocity_preempt_target(
        h, cand_edge_hr=350.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now, cand_sleeve="BOND1_UMA_RESOLUTION_CARRY"
    ) == (0.0, "")

    # 3. Once `MLK_NBA` has rested >= 180s (100 bps/h at 1.5h floor), a genuine >= 300 bps/h (>= 3x & >= +50)
    #    BOND1 upgrade CAN preempt it, while 280 bps/h (< 3x) still cannot!
    h.pending_entry_intents["i_mlk"]["ts"] = now - 240.0
    assert select_sll_velocity_preempt_target(
        h, cand_edge_hr=280.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now, cand_sleeve="BOND1_UMA_RESOLUTION_CARRY"
    ) == (0.0, "")
    assert select_sll_velocity_preempt_target(
        h, cand_edge_hr=310.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now, cand_sleeve="BOND1_UMA_RESOLUTION_CARRY"
    ) == (100.0, "MLK_NBA")


def test_s2_asset_priority_ranks_btc_eth_sol_ahead_of_altcoins(tmp_path, monkeypatch):
    d = a124_mod.Alpha124ShadowDaemon(single_scan=False)
    now = time.time()
    d.last_twap_discovery_ts = now

    def _mk_spec(asset: str, idx: int) -> TwapCandleMarketSpec:
        return TwapCandleMarketSpec(
            asset=asset,
            horizon="5m",
            market_id=f"m_{asset}",
            condition_id=f"0xc_{asset}",
            title=f"{asset} Up or Down 5m",
            start_iso="2026-11-05T10:35:00Z",
            end_iso="2026-11-05T10:40:00Z",
            start_ts=now - 280.0,
            end_ts=now + 20.0,
            up_token=f"up_{asset}",
            down_token=f"dn_{asset}",
            fee_rate=0.07,
            fee_exponent=1.0,
            neg_risk=False,
            twap_lookback_sec=60,
            resolution_source="https://data.chain.link/streams/btc-usd",
        )

    # Deliberately insert illiquid altcoins FIRST in dict insertion order
    for i, sym in enumerate(["HYPE", "XRP", "DOGE", "SOL", "ETH", "BTC"]):
        sp = _mk_spec(sym, i)
        d.twap_candles[sp.market_id] = sp
        d.spots[sym] = 100.5
        d.usd_direct_flags[sym] = True

    seen_assets = []

    async def _strike(_sp):
        return 100.0

    async def _books(toks, timeout=1.5):
        return {t: {"bids": [{"price": "0.985", "size": "50"}], "asks": [{"price": "0.995", "size": "50"}]} for t in toks}

    monkeypatch.setattr(d, "get_authoritative_open_strike", _strike)
    monkeypatch.setattr(d, "fetch_books_batch", _books)
    monkeypatch.setattr(d, "_strike_is_rest_verified", lambda _sp: True)
    monkeypatch.setattr(a124_mod, "read_shm_usd_anchor", lambda *a, **kw: {})
    monkeypatch.setattr(a124_mod, "get_wing_implied_vol", lambda *a, **kw: (0.45, "mock"))
    d._chainlink_ws = SimpleNamespace(
        get_latest_spot=lambda _a, now_ts=None, max_age_sec=2.5: 100.5,
        get_recent_samples=lambda _a, _since: [(now - 50.0 + k * 5.0, 100.5) for k in range(10)],
    )
    import src.polymarket_research.riskless_protocol_v2_expansion as rpv2

    monkeypatch.setattr(rpv2, "hydrate_fast_s2_from_shm", lambda _d, _n: {})
    monkeypatch.setattr(
        rpv2,
        "maybe_emit_s2_live_locks",
        lambda _d, **kw: seen_assets.append(kw["spec"].asset),
    )

    asyncio.run(d.scan_exact_twap_locks([], now_ts=now))
    assert seen_assets[:3] == ["BTC", "ETH", "SOL"]
    assert set(seen_assets[3:]) == {"HYPE", "XRP", "DOGE"}


def test_s2_maker_concurrent_1slot_cap_and_sizing_discipline_plus_gatling_no_double_sub(tmp_path, monkeypatch):
    # 1. Verify cap_bond1_maker_for_gatling_reserve does NOT double-subtract inflight_s2_usd
    fake_harv_g = SimpleNamespace(enforce_gatling_fast_gun_reserve=True)
    rb_cfg_g = {"gatling_enabled": True, "gatling_fast_gun_reserve_usd": 22.50}
    capped_with_inflight = cap_bond1_maker_for_gatling_reserve(
        fake_harv_g,
        budget=30.00,
        collat_f=42.50,
        sll_used_u=0.0,
        rb_cfg=rb_cfg_g,
        inflight_s2_usd=22.50,
    )
    capped_double_sub = cap_bond1_maker_for_gatling_reserve(
        fake_harv_g,
        budget=30.00,
        collat_f=42.50,
        sll_used_u=22.50,
        rb_cfg=rb_cfg_g,
        inflight_s2_usd=0.0,
    )
    assert capped_with_inflight == pytest.approx(23.38)
    assert capped_double_sub == pytest.approx(20.00)
    assert capped_with_inflight > capped_double_sub

    # 2. Verify Harvester caps S2 Maker at <= $22.50 (<= 22 sh @ $0.990, NEVER 25 sh = $24.75),
    #    allows 6 sh ($5.94 >= min_lot_shares=5), AND enforces <= 1 concurrent S2 Maker slot!
    a124_state = tmp_path / "alpha124_shadow_state.json"
    a124_state.write_text(
        json.dumps(
            {
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {
                        "closed": 32,
                        "wins": 32,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 140.0,
                    },
                    "S2_RTDS_EXACT_TWAP_INTEGRATOR": {
                        "closed": 2,
                        "wins": 2,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 1.2,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_state.json")

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h.holistic_v5_live_mode = True
    h.enforce_bond1_smart_queue = True
    h.enforce_gatling_fast_gun_reserve = True
    h.executor.auth_mode = "LIVE"
    h._last_known_collateral = 75.01
    h.executor.get_collateral_balance = lambda: h._last_known_collateral
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)

    gov_rb = plh.GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
    s2_b = compute_sll_and_carry_gatling_budget(
        h, 34.50, 75.01, 0.0, "SINGLE_LEG_MAKER_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR", False, gov_rb, rem_tte_sec=15.0
    )
    assert s2_b <= 22.50
    assert int(s2_b // 0.990) <= 22  # Strictly <= 22 shares ($21.78), NEVER 25 shares ($24.75)!

    posted_orders = []

    def _book(_s, tok):
        if tok.startswith("tok_w"):
            return {"bids": [{"price": "0.989", "size": "30"}], "asks": [{"price": "0.995", "size": "60"}], "minimum_tick_size": "0.001"}
        return {"bids": [{"price": "0.001", "size": "40"}], "asks": []}

    def _post(_s, token_id, price, notional_usd=0.0, **kw):
        sh = int(notional_usd / price)
        posted_orders.append((token_id, price, sh, notional_usd))
        return {"success": True, "orderID": f"0xoid_{token_id}", "price": price, "shares": sh}

    monkeypatch.setattr(type(h.executor), "get_market_book", _book)
    monkeypatch.setattr(type(h.executor), "post_maker_entry_order", _post)
    monkeypatch.setattr(type(h.executor), "cancel_order", lambda _s, oid, **kw: {"is_canceled": True, "outcome": "CANCELED", "matched": 0.0})
    monkeypatch.setattr(type(h.executor), "get_order_fill_summary", lambda _s, oid, tok: {"terminal": True, "resting": False, "matched": 0.0})

    def _s2_cand(sym: str, mid: str, now_u: float):
        return {
            "box_id": f"S2_{sym}",
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
            "asset": sym,
            "dedupe_key": f"S2_MKR_{sym}_{mid}",
            "pair_dedupe_key": f"S2_{sym}_{mid}",
            "leg_a_market_id": mid,
            "leg_a_condition_id": f"0xcond_{mid}",
            "leg_a_token_id": f"tok_w_{mid}",
            "leg_a_opp_token_id": f"tok_l_{mid}",
            "leg_a_side": "UP",
            "leg_a_neg_risk": False,
            "anchor_bid_px": 0.990,
            "min_resting_bid": 0.940,
            "max_box_cost_net": 0.994,
            "min_maker_edge": 0.006,
            "max_opp_bid": 0.008,
            "p_model": 0.9992,
            "expiry_ts": now_u + 14.0,
            "ts_unix": now_u,
        }

    async def _run_burst():
        now_u = time.time()
        # Fire BTC_5m, SOL_5m, and SOL_15m simultaneously
        t1 = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(_s2_cand("BTC", "m_btc5", now_u)))
        await asyncio.sleep(0.02)
        t2 = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(_s2_cand("SOL", "m_sol5", now_u)))
        t3 = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(_s2_cand("SOL", "m_sol15", now_u)))
        r2, r3 = await asyncio.gather(t2, t3)
        assert r2["reason"] == "S2_MAKER_CONCURRENT_CAP_1"
        assert r3["reason"] == "S2_MAKER_CONCURRENT_CAP_1"
        h._shutdown_requested = True
        await t1

        # After first S2 exits cleanly (`inflight_s2_mkr.discard`), test small $8.00 free cash + $65.00 carry ($73.00 NAV >= $42 ruin floor) -> 7 shares >= min_lot_shares=5!
        h._shutdown_requested = False
        h.active_positions["pos_carry_1"] = {
            "market_id": "m_carry_other",
            "token_id": "tok_carry_other",
            "box_id": "BOX_CARRY_1",
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
            "status": "OPEN",
            "notional_usd": 65.00,
            "shares": 65.0,
        }
        h._last_known_collateral = 8.00
        now_u2 = time.time()
        t4 = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(_s2_cand("ETH", "m_eth5", now_u2)))
        await asyncio.sleep(0.05)
        h._shutdown_requested = True
        await t4

    asyncio.run(_run_burst())
    assert len(posted_orders) == 2
    assert posted_orders[0][0] == "tok_w_m_btc5"
    assert posted_orders[0][2] <= 22
    assert posted_orders[1][0] == "tok_w_m_eth5"
    assert 5 <= posted_orders[1][2] <= 8


# ---------------------------------------------------------------------------
# (c) compute_sll_maker_keep_and_renew + partial-fill notional_usd sync
# ---------------------------------------------------------------------------


def test_compute_sll_maker_keep_and_renew_top_of_book_vs_buried_and_uma_exemption():
    t0 = 1000.0
    now_ts = 1_793_875_200.0

    # 1. Healthy uws_ok=True -> 1800s initial max_keep_s; degraded uws_ok=False -> 300s fallback
    mk_ok, dl_ok, exp_c_ok = compute_sll_maker_keep_and_renew(
        "BOND1_UMA_RESOLUTION_CARRY",
        uws_ok=True,
        exp_ts=now_ts + 3600.0,
        now_ts=now_ts,
        created_mono=t0,
        now_mono=t0,
        deadline_mono=0.0,
        posted_px=0.995,
        cur_best_bid=0.995,
    )
    assert mk_ok == pytest.approx(1800.0)
    assert dl_ok == pytest.approx(t0 + 1800.0)
    assert exp_c_ok is False

    mk_deg, dl_deg, _ = compute_sll_maker_keep_and_renew(
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        uws_ok=False,
        exp_ts=now_ts + 3600.0,
        now_ts=now_ts,
        created_mono=t0,
        now_mono=t0,
        deadline_mono=0.0,
        posted_px=0.961,
        cur_best_bid=0.961,
    )
    assert mk_deg == pytest.approx(300.0)
    assert dl_deg == pytest.approx(t0 + 300.0)

    # 2. #1 at top-of-book (`cur_best_bid <= posted_px`) auto-renews by +900s up to created_mono + 7200s
    _, dl_renewed, _ = compute_sll_maker_keep_and_renew(
        "BOND1_UMA_RESOLUTION_CARRY",
        uws_ok=True,
        exp_ts=now_ts + 3600.0,
        now_ts=now_ts + 1500.0,
        created_mono=t0,
        now_mono=t0 + 1500.0,
        deadline_mono=t0 + 1800.0,
        posted_px=0.995,
        cur_best_bid=0.995,
        buried_since_mono=None,
    )
    assert dl_renewed == pytest.approx(t0 + 2400.0)

    # Cap at created_mono + 7200.0
    _, dl_capped, _ = compute_sll_maker_keep_and_renew(
        "BOND1_UMA_RESOLUTION_CARRY",
        uws_ok=True,
        exp_ts=now_ts + 9000.0,
        now_ts=now_ts + 6800.0,
        created_mono=t0,
        now_mono=t0 + 6800.0,
        deadline_mono=t0 + 7000.0,
        posted_px=0.995,
        cur_best_bid=0.995,
    )
    assert dl_capped == pytest.approx(t0 + 7200.0)

    # 3. Buried behind a higher bid (`cur_best_bid = 0.998 > posted_px = 0.995`) MUST NOT renew!
    _, dl_buried, _ = compute_sll_maker_keep_and_renew(
        "BOND1_UMA_RESOLUTION_CARRY",
        uws_ok=True,
        exp_ts=now_ts + 3600.0,
        now_ts=now_ts + 1500.0,
        created_mono=t0,
        now_mono=t0 + 1500.0,
        deadline_mono=t0 + 1800.0,
        posted_px=0.995,
        cur_best_bid=0.998,
    )
    assert dl_buried == pytest.approx(t0 + 1800.0)

    # 4. UMA `BOND1` & `BOND2` are EXEMPT from `(exp_ts - now) <= 60.0` self-cancel (even post-liveness!),
    #    whereas `MKR_LOCK1` cancels at `<= 60.0s` and `S2` cancels at `<= 1.5s`.
    for uma_sl in ("BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"):
        _, _, should_c = compute_sll_maker_keep_and_renew(
            uma_sl,
            uws_ok=True,
            exp_ts=now_ts - 15.0,
            now_ts=now_ts,
            created_mono=t0,
            now_mono=t0 + 60.0,
            deadline_mono=t0 + 1800.0,
            posted_px=0.996,
            cur_best_bid=0.996,
        )
        assert should_c is False

    _, _, mlk_c = compute_sll_maker_keep_and_renew(
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        uws_ok=True,
        exp_ts=now_ts + 45.0,
        now_ts=now_ts,
        created_mono=t0,
        now_mono=t0 + 30.0,
        deadline_mono=t0 + 1800.0,
        posted_px=0.961,
        cur_best_bid=0.961,
    )
    assert mlk_c is True

    mk_s2, _, s2_c_5s = compute_sll_maker_keep_and_renew(
        "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        uws_ok=True,
        exp_ts=now_ts + 15.0,
        now_ts=now_ts + 10.0,
        created_mono=t0,
        now_mono=t0 + 2.0,
        deadline_mono=0.0,
        posted_px=0.990,
        cur_best_bid=0.990,
    )
    assert mk_s2 == pytest.approx(6.0)
    assert s2_c_5s is False
    _, _, s2_c_1s = compute_sll_maker_keep_and_renew(
        "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        uws_ok=True,
        exp_ts=now_ts + 11.2,
        now_ts=now_ts + 10.0,
        created_mono=t0,
        now_mono=t0 + 2.0,
        deadline_mono=t0 + 10.0,
        posted_px=0.990,
        cur_best_bid=0.990,
    )
    assert s2_c_1s is True


# ---------------------------------------------------------------------------
# (d) ws/user post-auth "PING" loop
# ---------------------------------------------------------------------------


def test_user_ws_sends_auth_strictly_before_ping_and_refreshes_health(monkeypatch):
    sent_frames = []
    pong_received = asyncio.Event()

    class _FakeWs:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def send(self, payload):
            sent_frames.append(payload)

        async def recv(self):
            # Wait until at least one post-auth PING has been sent, then reply PONG!
            while "PING" not in sent_frames:
                await asyncio.sleep(0.01)
            if not pong_received.is_set():
                pong_received.set()
                return "PONG"
            await asyncio.sleep(0.05)
            return "PONG"

    fake_websockets = SimpleNamespace(connect=lambda *_a, **_k: _FakeWs())
    monkeypatch.setitem(sys.modules, "websockets", fake_websockets)

    cache = ws_mod.PolymarketUserWsCache(
        api_key="k_test", api_secret="s_test", api_passphrase="p_test", ws_url="wss://fake.example/ws/user"
    )
    monkeypatch.setattr(
        cache,
        "_user_ping_loop",
        lambda ws, interval_sec=12.0: ws_mod.PolymarketUserWsCache._user_ping_loop(cache, ws, interval_sec=0.03),
    )

    async def _exercise():
        t = asyncio.create_task(cache._ws_forever())
        await asyncio.wait_for(pong_received.wait(), timeout=2.0)
        await asyncio.sleep(0.02)
        assert cache.is_healthy(max_silence_sec=5.0) is True
        cache._stop_event.set()
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass

    asyncio.run(_exercise())
    assert len(sent_frames) >= 2
    first_json = json.loads(sent_frames[0])
    assert first_json["type"] == "user"
    assert sent_frames[1] == "PING"


# ---------------------------------------------------------------------------
# (e) PAA heartbeat_ts + ghost-order filtering + zero-fill cancel resolution
# ---------------------------------------------------------------------------


def test_paa_accountant_and_monitor_heartbeat_ts_and_ghost_order_hygiene(tmp_path, monkeypatch):
    now = time.time()
    data_dir = tmp_path / "data" / "polymarket"
    data_dir.mkdir(parents=True)
    db = PAATaskDB(tmp_path / "paa_test.db")

    # Resting BOND1 order created 1200s ago with fresh heartbeat_ts (now - 8s) and partial-fill synced notional
    harv_state = {
        "status": "RUNNING",
        "risk_halt": False,
        "active_positions": {},
        "closed_positions": [],
        "pending_entry_intents": {
            "BOND1_LIVE_INTENT": {
                "live_maker_anchor_inflight": True,
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "order_id": "0xtracked_bond1_live",
                "notional_usd": 19.90,
                "ts": now - 1200.0,
                "heartbeat_ts": now - 8.0,
            }
        },
    }
    (data_dir / "live_harvester_state.json").write_text(json.dumps(harv_state), encoding="utf-8")

    # Simulate `/tmp/dominus_clob_open_orders_cache.json` with BOTH:
    #   1) Untracked 12-hour-old ghost order `0x991211b7...` ($22.82) -> MUST BE IGNORED
    #   2) Tracked 4000s-old auto-renewed `0xtracked_bond1_live` ($19.90) -> MUST BE KEPT
    fake_ord_cache = tmp_path / "dominus_clob_open_orders_cache.json"
    fake_ord_cache.write_text(
        json.dumps(
            [
                {
                    "id": "0x991211b7ghost",
                    "status": "LIVE",
                    "side": "BUY",
                    "price": "0.992",
                    "original_size": "23",
                    "size_matched": "0",
                    "created_at": int(now - 43200),
                },
                {
                    "id": "0xtracked_bond1_live",
                    "status": "LIVE",
                    "side": "BUY",
                    "price": "0.995",
                    "original_size": "20",
                    "size_matched": "0",
                    "created_at": int(now - 4000),
                },
            ]
        ),
        encoding="utf-8",
    )

    cfg = {
        "riskless_mandate": {
            "enforce_riskless_only_live": True,
            "riskless_epoch_start_utc": "2026-11-04T02:05:00Z",
            "live_loss_alert_threshold_usd": -0.05,
        }
    }
    budget = BudgetManager(db, autonomy_cfg=cfg)
    acc = PAAAccountant(db=db, budget=budget, data_dir=data_dir, autonomy_cfg=cfg)

    # First verify fallback (`pending_entry_intents` with `heartbeat_ts`) when cache file is absent
    monkeypatch.setattr(
        "src.paa_os.accountant.Path",
        lambda p: (tmp_path / "missing.json") if "dominus_clob_open_orders_cache" in str(p) else Path(p),
    )
    tel_fb = acc._compute_riskless_live_and_quoting_metrics(
        {"portfolio_nav_book_usd": 75.01, "free_cash_pusd": 55.11, "open_cost_basis_usd": 0.0}
    )
    assert tel_fb["working_maker_buy_orders_count"] == 1
    assert tel_fb["working_maker_quoting_usd"] == pytest.approx(19.90)

    # Next verify live CLOB cache filtering drops `0x991211b7ghost` ($22.82) while keeping `0xtracked_bond1_live` ($19.90)
    monkeypatch.setattr(
        "src.paa_os.accountant.Path",
        lambda p: fake_ord_cache if "dominus_clob_open_orders_cache" in str(p) else Path(p),
    )
    tel_cache = acc._compute_riskless_live_and_quoting_metrics(
        {"portfolio_nav_book_usd": 75.01, "free_cash_pusd": 55.11, "open_cost_basis_usd": 0.0}
    )
    assert tel_cache["working_maker_buy_orders_count"] == 1
    assert tel_cache["working_maker_quoting_usd"] == pytest.approx(19.90)

    # Verify PAAMonitor does NOT emit UNRESOLVED_ENTRY_INTENTS when heartbeat_ts is fresh (8s ago)
    mon = PAAMonitor(db=db, accountant=acc, budget=budget, data_dir=data_dir, autonomy_cfg=cfg)
    monkeypatch.setattr("src.paa_os.monitor.check_operational_status", lambda auto_recover_safe=False: ({"all_core_units_active": True, "systemd_units": {}}, []))
    monkeypatch.setattr(acc, "measure_and_record", lambda live_rpc_check=False: {"accounting_ok": True, "free_cash_pusd": 55.11, "nav_mark_to_bid_usd": 75.01, "details": {"anomalies": []}})
    monkeypatch.setattr(mon, "_check_failed_systemd_jobs", lambda: [])
    monkeypatch.setattr(mon, "_check_vm_resources", lambda: [])
    db.record_heartbeat("paa_director", status="OK", details={"status": "IDLE"})

    chk_ok = mon.run_monitor_cycle(live_rpc_check=False, auto_recover_safe=False, check_network=False)
    assert not any("UNRESOLVED_ENTRY_INTENTS" in a for a in chk_ok.get("anomalies", []))

    # Adversarial check: if heartbeat_ts goes stale (> 90s), PAAMonitor MUST still flag UNRESOLVED_ENTRY_INTENTS!
    harv_state["pending_entry_intents"]["BOND1_LIVE_INTENT"]["heartbeat_ts"] = now - 130.0
    (data_dir / "live_harvester_state.json").write_text(json.dumps(harv_state), encoding="utf-8")
    chk_stale = mon.run_monitor_cycle(live_rpc_check=False, auto_recover_safe=False, check_network=False)
    assert any("UNRESOLVED_ENTRY_INTENTS" in a for a in chk_stale.get("anomalies", []))


def test_cancel_order_already_canceled_or_matched_resolves_zero_fill_but_stays_fail_closed_on_silent_fill(monkeypatch):
    ex = ex_mod.PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    ex.client = MagicMock()

    ex.client.cancel_orders.return_value = {
        "canceled": [],
        "not_canceled": {"0xghost_oid": "order already canceled or matched, can't be canceled"},
    }
    monkeypatch.setattr(
        ex,
        "get_order_status",
        lambda _oid: {"id": "0xghost_oid", "status": "LIVE", "size_matched": "0", "original_size": "20", "asset_id": "tok_z"},
    )
    monkeypatch.setattr(ex, "get_account_fills", lambda *_a, **_k: [])

    # 1. Verified zero-fill (ERC-1155 balance delta == 0.0 and 0 fills) -> CANCELED (`is_canceled=True`)
    monkeypatch.setattr(ex, "get_conditional_balance", lambda _tok: 5.0)
    res_clean = ex.cancel_order("0xghost_oid", token_id="tok_z", pre_token_balance=5.0)
    assert res_clean.is_canceled is True
    assert res_clean["outcome"] == "CANCELED"
    assert res_clean["matched"] == pytest.approx(0.0)

    # 2. Market closed zero-fill -> CANCELED (`is_canceled=True`) even without token_id
    res_closed = ex.cancel_order("0xghost_oid", market_closed=True)
    assert res_closed.is_canceled is True
    assert res_closed["outcome"] == "CANCELED"

    # 3. Adversarial silent fill (stale CLOB says size_matched=0, BUT on-chain ERC-1155 balance jumped +20 shares!)
    #    MUST remain fail-closed (`is_canceled=False`, `outcome="UNKNOWN"`)!
    monkeypatch.setattr(ex, "get_conditional_balance", lambda _tok: 25.0)
    res_filled = ex.cancel_order("0xghost_oid", token_id="tok_z", pre_token_balance=5.0)
    assert res_filled.is_canceled is False
    assert res_filled["outcome"] == "UNKNOWN"


def test_harvester_partial_fill_syncs_pending_intent_notional_usd(tmp_path, monkeypatch):
    a124_state = tmp_path / "alpha124_shadow_state.json"
    a124_state.write_text(
        json.dumps(
            {
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {
                        "closed": 32,
                        "wins": 32,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 140.0,
                    },
                    "BOND1_UMA_RESOLUTION_CARRY": {
                        "closed": 20,
                        "wins": 20,
                        "losses": 0,
                        "win_rate_pct": 100.0,
                        "realized_pnl_t1000_usd": 15.0,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
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

    class _FakeUws:
        fill_sequence = 1

        def is_healthy(self):
            return True

        async def wait_for_fill_or_timeout(self, timeout_s, prev_seq=0):
            await asyncio.sleep(0.02)

        def get_order_snapshot(self, oid, max_age_sec=5.0):
            return {"id": oid, "status": "LIVE", "size_matched": "8.0", "original_size": "20.0"}

    h.executor._user_ws_cache = _FakeUws()
    monkeypatch.setattr(
        type(h.executor),
        "get_market_book",
        lambda _s, tok: {"bids": [{"price": "0.994", "size": "40"}], "asks": [{"price": "0.999", "size": "60"}], "minimum_tick_size": "0.001"}
        if tok == "tok_pf_w"
        else {"bids": [{"price": "0.001", "size": "40"}], "asks": []},
    )
    monkeypatch.setattr(
        type(h.executor),
        "post_maker_entry_order",
        lambda _s, token_id, price, notional_usd=0.0, **kw: {"success": True, "orderID": "0xoid_pf", "price": 0.995, "shares": 20},
    )
    monkeypatch.setattr(
        type(h.executor),
        "cancel_order",
        lambda _s, oid, **kw: {"is_canceled": True, "outcome": "PARTIALLY_FILLED_CANCELED", "matched": 8.0},
    )
    monkeypatch.setattr(
        type(h.executor),
        "get_order_fill_summary",
        lambda _s, oid, tok: {"terminal": True, "resting": False, "matched": 8.0, "avg_price": 0.995},
    )

    observed_notional = []

    async def _drive_pf():
        now_u = time.time()
        t = asyncio.create_task(
            h.maybe_execute_graduated_single_leg_maker_lock(
                {
                    "box_id": "B1_PF_TEST",
                    "box_type": "SINGLE_LEG_MAKER_LOCK",
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "dedupe_key": "BOND1_MKR_PF",
                    "pair_dedupe_key": "BOND1_PF",
                    "leg_a_market_id": "m_pf_1",
                    "leg_a_condition_id": "0xcond_pf",
                    "leg_a_token_id": "tok_pf_w",
                    "leg_a_opp_token_id": "tok_pf_l",
                    "leg_a_side": "YES",
                    "leg_a_neg_risk": False,
                    "anchor_bid_px": 0.995,
                    "min_resting_bid": 0.940,
                    "max_box_cost_net": 0.996,
                    "min_maker_edge": 0.004,
                    "max_opp_bid": 0.008,
                    "p_model": 1.0,
                    "expiry_ts": now_u + 1800.0,
                    "ts_unix": now_u,
                }
            )
        )
        await asyncio.sleep(0.08)
        it = h.pending_entry_intents.get("B1_PF_TEST_SLL_INTENT")
        if it is not None:
            observed_notional.append(it["notional_usd"])
            observed_notional.append(it.get("heartbeat_ts", 0.0))
        h._shutdown_requested = True
        return await t

    res_pf = asyncio.run(_drive_pf())
    assert observed_notional[0] == pytest.approx(round(12.0 * 0.995, 4))
    assert observed_notional[1] > 0.0
    assert res_pf["executed"] is True


def test_live_gatling_mkr_lock1_coexists_with_bond1_without_preempt_churn(tmp_path, monkeypatch):
    """
    Regression test for live `Heat @ $0.961` (`MKR_LOCK1`) queue destruction:
    On a `$75.01` Gatling wallet (`enforce_bond1_smart_queue=True`), resting `MKR_LOCK1` (`$21.14`)
    leaves `$53.87` free cash — enough for BOTH a full `$20.50` `BOND1` clip AND the `$21.00` Gatling reserve!
    Neither a duplicate/cooldown `BOND1` nor a fresh valid `BOND1` may cancel `MKR_LOCK1`.
    """
    a124_state = tmp_path / "alpha124_shadow_state.json"
    a124_state.write_text(
        json.dumps(
            {
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 32, "wins": 32, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 140.0},
                    "BOND1_UMA_RESOLUTION_CARRY": {"closed": 20, "wins": 20, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 15.0},
                    "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER": {"closed": 5, "wins": 5, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 6.0},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "harv_coexist.json")

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h.holistic_v5_live_mode = True
    h.enforce_bond1_smart_queue = True
    h.enforce_gatling_fast_gun_reserve = True
    h.executor.auth_mode = "LIVE"
    h._last_known_collateral = 75.01
    h.executor.get_collateral_balance = lambda: 75.01
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)

    posted = []
    canceled = []

    def _bk(_s, tok):
        if tok == "tok_heat_w":
            return {"bids": [{"price": "0.960", "size": "50"}], "asks": [{"price": "0.990", "size": "50"}], "minimum_tick_size": "0.001"}
        if tok == "tok_kings_w":
            return {"bids": [{"price": "0.994", "size": "50"}], "asks": [{"price": "0.999", "size": "50"}], "minimum_tick_size": "0.001"}
        return {"bids": [{"price": "0.001", "size": "50"}], "asks": []}

    monkeypatch.setattr(type(h.executor), "get_market_book", _bk)
    monkeypatch.setattr(
        type(h.executor),
        "post_maker_entry_order",
        lambda _s, token_id, price, notional_usd=0.0, **kw: posted.append((token_id, price, notional_usd))
        or {"success": True, "orderID": f"0x_{token_id}", "price": price, "shares": int(notional_usd / price)},
    )
    monkeypatch.setattr(
        type(h.executor),
        "cancel_order",
        lambda _s, oid, **kw: canceled.append(oid) or {"is_canceled": True, "outcome": "CANCELED", "matched": 0.0},
    )
    monkeypatch.setattr(
        type(h.executor),
        "get_order_fill_summary",
        lambda _s, oid, tok: {"terminal": True, "resting": False, "matched": 0.0},
    )

    async def _run_coexist():
        now_u = time.time()
        t_heat = asyncio.create_task(
            h.maybe_execute_graduated_single_leg_maker_lock(
                {
                    "box_id": "MLK_HEAT",
                    "box_type": "SINGLE_LEG_MAKER_LOCK",
                    "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                    "dedupe_key": "MLK_HEAT_KEY",
                    "pair_dedupe_key": "MLK_HEAT_PAIR",
                    "asset": "NBA",
                    "leg_a_market_id": "m_heat",
                    "leg_a_condition_id": "0xheat",
                    "leg_a_token_id": "tok_heat_w",
                    "leg_a_opp_token_id": "tok_heat_l",
                    "leg_a_side": "YES",
                    "anchor_bid_px": 0.961,
                    "min_resting_bid": 0.940,
                    "max_box_cost_net": 0.991,
                    "max_opp_bid": 0.008,
                    "p_model": 0.999,
                    "expiry_ts": now_u + 1800.0,
                    "ts_unix": now_u,
                }
            )
        )
        await asyncio.sleep(0.05)
        assert len(posted) == 1 and posted[0][0] == "tok_heat_w"

        # 1. Duplicate/cooldown BOND1 arrives -> rejected, Heat MKR_LOCK1 untouched!
        h._seen_d1_box_keys = {"BOND1_DUP"}
        res_dup = await h.maybe_execute_graduated_single_leg_maker_lock(
            {
                "box_id": "B1_DUP",
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "dedupe_key": "BOND1_DUP",
                "pair_dedupe_key": "BOND1_DUP_PAIR",
                "asset": "NBA",
                "leg_a_market_id": "m_dup",
                "leg_a_condition_id": "0xdup",
                "leg_a_token_id": "tok_kings_w",
                "leg_a_opp_token_id": "tok_kings_l",
                "leg_a_side": "YES",
                "anchor_bid_px": 0.995,
                "min_resting_bid": 0.940,
                "max_box_cost_net": 0.996,
                "max_opp_bid": 0.008,
                "expiry_ts": now_u + 1200.0,
                "ts_unix": now_u,
            }
        )
        assert res_dup["reason"] == "ALREADY_SEEN_OR_COOLDOWN"
        assert canceled == []

        # 2. Fresh valid BOND1 (`Kings @ $0.995`) arrives -> BOTH rest simultaneously with zero Heat cancel!
        t_kings = asyncio.create_task(
            h.maybe_execute_graduated_single_leg_maker_lock(
                {
                    "box_id": "B1_KINGS",
                    "box_type": "SINGLE_LEG_MAKER_LOCK",
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "dedupe_key": "BOND1_KINGS_MKR",
                    "pair_dedupe_key": "BOND1_KINGS",
                    "asset": "NBA",
                    "leg_a_market_id": "m_kings",
                    "leg_a_condition_id": "0xkings",
                    "leg_a_token_id": "tok_kings_w",
                    "leg_a_opp_token_id": "tok_kings_l",
                    "leg_a_side": "YES",
                    "anchor_bid_px": 0.995,
                    "min_resting_bid": 0.940,
                    "max_box_cost_net": 0.996,
                    "max_opp_bid": 0.008,
                    "expiry_ts": now_u + 1200.0,
                    "ts_unix": now_u,
                }
            )
        )
        await asyncio.sleep(0.06)
        assert len(posted) == 2
        assert canceled == []  # Heat @ $0.961 was NEVER canceled!
        assert len(h.pending_entry_intents) == 2

        h._shutdown_requested = True
        await asyncio.gather(t_heat, t_kings)

    asyncio.run(_run_coexist())


