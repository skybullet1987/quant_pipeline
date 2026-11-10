"""
Stage C Pure-Riskless Capital-Velocity & Clinched Split-to-Sell Engine
(`src/polymarket_research/stage_c_zero_loss_velocity.py`).

Implements 100% Zero-Loss (`RISKLESS_PAA`) Stage C upgrades with ZERO directional or partial-leg principal risk:
  1. `is_strict_riskless_pre_split_blocked`: Hard-locks unclinched 2-leg `PreSplitInventoryGun` OFF across all
     equity tiers (`$140`, `$250`, `$1,000+`) whenever `strict_zero_legging_pre_split_lock` is enabled.
  2. `recycle_open_zero_loss_carry_for_fast_arb` (Engine C1): Recycles slow, already-filled standalone `0%`-fee
     single-leg carries (`<= 45 bps/hr` remaining velocity) ONLY when an incoming graduated Taker arbitrage box
     has `>= 200 bps` net locked edge and `>= 4.0x` higher capital velocity, AND live CLOB bids fill the entire
     integer share lot at `ROUND_CEILING` tick-aligned `min_sell_px >= cost_per_share + min_profit_per_share`
     (`net_pnl > $0.00` mathematically guaranteed on every share).
  3. `execute_clinched_dead_leg_split_arb` (Engine C2): On-demand complete-set `splitPosition` strictly on
     `100%` mathematically clinched (`p_model >= 0.9999`) `0%`-fee binary markets where the dead (`$0.00`) leg
     has live bids `>= $0.008`: sells the worthless dead leg via limit `SELL >= min_dead_bid_px` while retaining
     the `$1.00`-guaranteed winning leg (or immediately merges `YES + NO -> $1.00` cash if the dead-leg bid was raced).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
import logging
import math
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

logger = logging.getLogger("StageCZeroLossVelocity")


def _sf(val: Any, default: float = 0.0) -> float:
    if val is None or isinstance(val, bool) or val == "":
        return default
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def is_strict_riskless_pre_split_blocked(rb_cfg: Optional[Mapping[str, Any]]) -> bool:
    """
    Returns True when `strict_zero_legging_pre_split_lock` is active and `enable_pre_split_overround_gun`
    is not explicitly enabled, preventing unclinched 2-leg `PreSplitInventoryGun` from auto-activating
    at `$140+` equity under `RISKLESS_PAA`.
    """
    if not isinstance(rb_cfg, Mapping):
        return False
    return bool(rb_cfg.get("strict_zero_legging_pre_split_lock", False)) and not bool(
        rb_cfg.get("enable_pre_split_overround_gun", False)
    )


PURE_RISKLESS_BLOCKED_SLEEVES = frozenset(
    {
        "B4_TOUCHED_BARRIER_WICK_LOCK",
        "MKR_REWARD_LOCKED_CARRY",
        "S2_EXACT_TWAP_LOCK",
        "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        "W_PRUNE1_NR0_BASKET",
        "W_SOLAR1_POST_2351_LOCK",
        "W2_FORECAST_TAIL",
        "NR0_ALL_YES_COMPLETE_SET",
        "NR0_ZERO_FEE_SLATE_ARB",
        "LP_COMP1_SPORTS_TRIANGLES",
        "DC1_DOUBLE_CHANCE_1X2_PARITY",
        "CTF_OVERROUND_MINT_SELL",
        "SP1_NBA_SPREAD_POLISH_MIDDLE",
        "SP3_SPORTS_CORRIDOR_DOMINANCE_BOX",
        "SP3_NFL_EXACT_MARGIN_AND_KEY_NUMBER_MIDDLE",
        "SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX",
        "SOC1_THREE_WAY_REGULATION_BOX",
        "SOC2_EXACT_SCORE_2D_LATTICE",
        "SOC2_SCORE_TOTAL_BTTS_LATTICE",
        "CM_B3_PYTH_BARRIER_BOX",
        "D1_MAKER_ANCHOR_BOX",
        "ZERO_FEE_MAKER_ANCHOR_BOX",
    }
)

POST_CLINCH_SINGLE_LEG_SLEEVES = frozenset(
    {
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "W_PRUNE1_DEAD_NO_BOND",
        "W1_SOLAR_PEAK_LOCK",
        "W1_LOW_TROUGH_LOCK",
        "SP2_NBA_ENDGAME_LOCK",
        "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
        "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
        "AFF1_FROZEN_SUBPERIOD_COLLAPSE",
        "GAS1_AAA_GASOLINE_LOCK",
        "XTRACK1_6HANDLE_DEAD_NO",
        "XTRACK1_HORSE_RACING_CLINCH",
    }
)

PURE_RISKLESS_DOMINANCE_AND_MERGE_SLEEVES = frozenset(
    {
        "D1_SAME_ORACLE_DOMINANCE_BOX",
        "D1_4H_DOMINANCE_BOX",
        "D1_QUIET_BOOK_BOX",
        "C1_BINARY_COMPLETE_SET",
        "NR2_CONVERT_NO_SUBSET_ARB",
        "NR_M1_DEAD_SEED_OVERROUND",
    }
)

PURE_RISKLESS_ALLOWED_LIVE_SLEEVES = (
    PURE_RISKLESS_DOMINANCE_AND_MERGE_SLEEVES
    | frozenset(
        {
            "BOND1_UMA_RESOLUTION_CARRY",
            "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
            "UMA_READY1_LIVENESS_PRIORITY",
        }
    )
    | POST_CLINCH_SINGLE_LEG_SLEEVES
)


def is_nr0_closed_partition_graduated_unlock(
    total_equity_usd: float,
    rb_cfg: Optional[Mapping[str, Any]],
    alpha124_by_sleeve: Optional[Mapping[str, Any]],
) -> bool:
    """
    Returns True ONLY when `allow_nr0_multileg_dynamic_unpause` is explicitly enabled AND
    `NR0_ZERO_FEE_SLATE_ARB` has achieved strict `8/8` (`0`-loss, `100%` WR, positive
    legging-adjusted PnL) shadow graduation AND live equity meets `nr0_dynamic_unlock_equity_usd`
    (default `$150.00`). Under `strict_pure_riskless_mode`, multi-leg sequential FAK bundles
    remain locked OFF by default to prevent partial-basket `UNWRESID` legging losses.
    """
    cfg = rb_cfg if isinstance(rb_cfg, Mapping) else {}
    if bool(cfg.get("strict_pure_riskless_mode", False)) and not bool(
        cfg.get("allow_nr0_multileg_dynamic_unpause", False)
    ):
        return False
    min_eq = max(100.0, _sf(cfg.get("nr0_dynamic_unlock_equity_usd"), 150.0))
    if _sf(total_equity_usd, 0.0) < min_eq:
        return False
    if not isinstance(alpha124_by_sleeve, Mapping):
        return False
    rec = alpha124_by_sleeve.get("NR0_ZERO_FEE_SLATE_ARB")
    if not isinstance(rec, Mapping):
        return False
    settled = int(_sf(rec.get("closed"), 0.0))
    losses = int(_sf(rec.get("losses"), 0.0))
    wr = _sf(rec.get("win_rate_pct"), 0.0)
    raw_pnl = _sf(rec.get("realized_pnl_t1000_usd"), 0.0)
    adj_pnl = _sf(rec.get("legging_adjusted_pnl_t1000_usd"), raw_pnl)
    return settled >= 8 and losses == 0 and wr >= 100.0 and raw_pnl > 0.0 and adj_pnl > 0.0


def resolve_dynamic_paused_riskless_sleeves(
    rb_cfg: Optional[Mapping[str, Any]],
    total_equity_usd: float,
    alpha124_by_sleeve: Optional[Mapping[str, Any]] = None,
) -> set[str]:
    """
    Computes the effective `paused_riskless_sleeves` set at runtime. Never unpauses multi-leg
    `NR0_ZERO_FEE_SLATE_ARB` while `strict_pure_riskless_mode` is active unless explicitly opted in.
    """
    cfg = rb_cfg if isinstance(rb_cfg, Mapping) else {}
    raw = cfg.get("paused_riskless_sleeves") or []
    paused = {str(s).strip().upper() for s in raw if str(s or "").strip()}
    if "NR0_ZERO_FEE_SLATE_ARB" in paused and is_nr0_closed_partition_graduated_unlock(
        total_equity_usd=total_equity_usd,
        rb_cfg=cfg,
        alpha124_by_sleeve=alpha124_by_sleeve,
    ):
        paused.discard("NR0_ZERO_FEE_SLATE_ARB")
    return paused

UMA_POST_EVENT_CARRY_SLEEVES = frozenset(
    {
        "BOND1_UMA_RESOLUTION_CARRY",
        "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY",
        "UMA_READY1_LIVENESS_PRIORITY",
    }
)


def is_unmocked_live_clob_harvester(harvester: Any) -> bool:
    """
    True on the real-money L2 CLOB production Harvester (`dry_run=False`, real `executor.client`,
    no monkeypatched test stubs in `executor.__dict__`) OR when `enforce_pure_riskless_mode=True`
    / `enforce_paused_riskless_sleeves=True` is explicitly set.
    """
    if getattr(harvester, "enforce_pure_riskless_mode", False) or getattr(
        harvester, "enforce_paused_riskless_sleeves", False
    ):
        return True
    if getattr(harvester, "dry_run", True):
        return False
    ex = getattr(harvester, "executor", None)
    if ex is None or getattr(ex, "dry_run", False):
        return False
    cli = getattr(ex, "client", None)
    if cli is None or getattr(cli, "_mock_children", None) is not None:
        return False
    ex_dict = getattr(ex, "__dict__", {})
    if any(
        k in ex_dict
        for k in ("get_market_book", "execute_snipe_order", "execute_snipe_order_async", "post_maker_entry_order")
    ):
        return False
    return True


def check_strict_pure_riskless_candidate_gate(
    harvester: Any,
    candidate_box: Mapping[str, Any],
    rb_cfg: Optional[Mapping[str, Any]],
    *,
    is_maker: bool = False,
) -> Optional[str]:
    """
    Zero-Trust Riskless & Post-Clinch Firewall on live production (`strict_pure_riskless_mode == True`):
      1. Blocks unclinched 2-leg Maker Anchor boxes (`DOMINANCE_MAKER_ANCHOR`, `ZERO_FEE_MAKER_ANCHOR`),
         directional/cross-question corridors (`SOC2`, `SOC1`, `SP3`, `CM_B3`, `CAL1`, `B4`), pre-expiry
         `S2` / `W_SOLAR1`, midbook `MKR_REWARD_LOCKED_CARRY`, `MULTI_LEG_BUNDLE` (`>= 3` sequential legs),
         `CTF_OVERROUND`, `NR3_SYNTHETIC_ALL_YES_OVERROUND`, and `m >= 3` `NEGRISK_CONVERT`.
      2. Permits Row-2 zero-loss post-event / post-clinch carries & METAR-contradiction-locked dead-NO bonds:
         - Objective UMA OO proposed / final-hour whitelist carries (`BOND1`, `BOND2`, `UMA_READY1`)
         - Post-clinch / monotonic already-surpassed single-leg locks (`W_PRUNE1_DEAD_NO_BOND`, `W1_*`,
           `MKR_LOCK1`, `SP2`, `SP4`, `CL1`, `AFF1`, `GAS1`, `XTRACK1`) strictly gated by `p_model >= 0.999`
         - `m == 1` `NR_M1_DEAD_SEED_OVERROUND` and `m == 2` `NR2_PURE_CASH_CONVERT`
      3. Permits 2-leg same-oracle / same-condition payoff-dominant boxes:
         - `D1_SAME_ORACLE_DOMINANCE_BOX`, `D1_4H_DOMINANCE_BOX`, `D1_QUIET_BOOK_BOX` (`K_low <= K_high`)
         - `C1_BINARY_COMPLETE_SET` (`1 YES + 1 NO == $1.00` on exact same `condition_id` / `market_id`)
    Returns `None` if allowed, or a deterministic rejection reason string if blocked.
    """
    if not isinstance(rb_cfg, Mapping) or not bool(rb_cfg.get("strict_pure_riskless_mode", False)):
        return None
    if not is_unmocked_live_clob_harvester(harvester):
        return None

    btype = str(candidate_box.get("box_type") or ("SINGLE_LEG_MAKER_LOCK" if is_maker else "")).strip().upper()
    sl_src = str(candidate_box.get("sleeve_source") or candidate_box.get("sleeve") or "").strip().upper()

    # 1. Block unclinched 2-leg resting Maker Anchor boxes
    if btype in {"DOMINANCE_MAKER_ANCHOR", "ZERO_FEE_MAKER_ANCHOR", "MAKER_ANCHOR", "SYNTHETIC_MAKER"} and not bool(
        rb_cfg.get("enable_two_leg_maker_anchor_boxes", False)
    ):
        return f"PURE_RISKLESS_TWO_LEG_MAKER_BLOCKED:{sl_src or btype}"

    # Honor explicit operator toggle on single-leg Maker resting anchors (`enable_single_leg_maker_bond1`)
    if (is_maker or btype == "SINGLE_LEG_MAKER_LOCK") and not bool(rb_cfg.get("enable_single_leg_maker_bond1", True)):
        return f"PURE_RISKLESS_SINGLE_LEG_MAKER_DISABLED:{sl_src or btype}"

    nr0_closed_ok = (
        bool(rb_cfg.get("allow_nr0_multileg_dynamic_unpause", False))
        and sl_src == "NR0_ZERO_FEE_SLATE_ARB"
        and bool(candidate_box.get("nr0_graduated_unlock_verified")) is True
        and candidate_box.get("neg_risk_augmented") is False
        and 2 <= len(candidate_box.get("legs") or candidate_box.get("no_legs") or ()) <= 6
    )
    if sl_src in PURE_RISKLESS_BLOCKED_SLEEVES and not nr0_closed_ok:
        return f"PURE_RISKLESS_SLEEVE_BLOCKED:{sl_src}"
    if btype in {"MULTI_LEG_BUNDLE", "CTF_OVERROUND"} and not (btype == "MULTI_LEG_BUNDLE" and nr0_closed_ok):
        return f"PURE_RISKLESS_SPECIAL_BOX_BLOCKED:{btype}"

    if btype == "NEGRISK_CONVERT":
        cm = str(candidate_box.get("convert_mode") or "").strip().upper()
        no_legs = candidate_box.get("no_legs") or ()
        if cm == "NR2_PURE_CASH_CONVERT" and sl_src in {"", "NR2_CONVERT_NO_SUBSET_ARB"} and len(no_legs) == 2:
            return None
        if cm == "NR_M1_DEAD_SEED_OVERROUND" and sl_src in {"", "NR_M1_DEAD_SEED_OVERROUND"} and len(no_legs) == 1:
            return None
        return f"PURE_RISKLESS_MULTI_LEG_CONVERT_BLOCKED:{cm or sl_src or len(no_legs)}"

    if nr0_closed_ok:
        return None

    # 2. Row-2 UMA Proposed Carries & Post-Clinch Single-Leg / WS-Watchlist / Atomic Dead-Leg Split Locks
    if is_maker or btype in {"", "SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK", "CLINCH_WATCHLIST_REG", "CLINCH_DEAD_SPLIT_LOCK"}:
        if btype == "CLINCH_DEAD_SPLIT_LOCK" and not bool(rb_cfg.get("enable_clinched_dead_leg_split_sell", True)):
            return "PURE_RISKLESS_DEAD_SPLIT_DISABLED"
        if sl_src in UMA_POST_EVENT_CARRY_SLEEVES:
            return None
        if sl_src in POST_CLINCH_SINGLE_LEG_SLEEVES:
            p_mod = _sf(candidate_box.get("p_model"), 0.0)
            if sl_src in {"W1_SOLAR_PEAK_LOCK", "W1_LOW_TROUGH_LOCK"}:
                rem_h_w1 = int(_sf(candidate_box.get("rem_hours_count"), 0.0))
                if (
                    p_mod < 1.0
                    or rem_h_w1 > 0
                    or bool(candidate_box.get("intraday_unclinched_forecast", False))
                ):
                    return f"PURE_RISKLESS_INTRADAY_WEATHER_FORECAST_BLOCKED:{sl_src}:p={p_mod:.4f}:rem_h={rem_h_w1}"
            if p_mod < 0.999:
                return f"PURE_RISKLESS_UNCLINCHED_P_MODEL:{sl_src}:{p_mod:.4f}"
            return None
        return f"PURE_RISKLESS_SINGLE_LEG_SLEEVE_NOT_ALLOWLISTED:{sl_src or 'UNKNOWN'}"

    # 3. Enforce strict mathematical payoff-dominance allowlist on 2-leg boxes
    if sl_src not in {"D1_SAME_ORACLE_DOMINANCE_BOX", "D1_4H_DOMINANCE_BOX", "D1_QUIET_BOOK_BOX", "C1_BINARY_COMPLETE_SET"}:
        return f"PURE_RISKLESS_SLEEVE_NOT_ALLOWLISTED:{sl_src or 'UNKNOWN'}"
    if btype not in {"DOMINANCE", "DOMINANCE_BOX", "COMPLETE_SET", "C1_BINARY_COMPLETE_SET"}:
        return f"PURE_RISKLESS_BOX_TYPE_NOT_ALLOWLISTED:{btype or 'UNKNOWN'}"

    # 3. Structural invariants per allowlisted box class
    if sl_src == "C1_BINARY_COMPLETE_SET" or btype in {"COMPLETE_SET", "C1_BINARY_COMPLETE_SET"}:
        cid_a = str(candidate_box.get("leg_a_condition_id") or "").strip().lower()
        cid_b = str(candidate_box.get("leg_b_condition_id") or "").strip().lower()
        mid_a = str(candidate_box.get("leg_a_market_id") or "").strip()
        mid_b = str(candidate_box.get("leg_b_market_id") or "").strip()
        tok_a = str(candidate_box.get("leg_a_token_id") or "").strip()
        tok_b = str(candidate_box.get("leg_b_token_id") or "").strip()
        if (cid_a and cid_b and cid_a != cid_b) or (mid_a and mid_b and mid_a != mid_b) or (tok_a and tok_b and tok_a == tok_b):
            return "PURE_RISKLESS_C1_CONDITION_MISMATCH"
    else:
        k_lo = _sf(candidate_box.get("k_low", candidate_box.get("leg_a_strike")), 0.0)
        k_hi = _sf(candidate_box.get("k_high", candidate_box.get("leg_b_strike")), 0.0)
        if k_lo > 0.0 and k_hi > 0.0 and k_lo > k_hi + 1e-9:
            return f"PURE_RISKLESS_INVERTED_DOMINANCE_STRIKES:{k_lo}>{k_hi}"
    return None


class _PureRisklessEnforcedSentinel:
    enforce_pure_riskless_mode = True


def evaluate_strict_pure_riskless_candidate(
    candidate_box: Mapping[str, Any],
    gov_snapshot: Optional[Mapping[str, Any]] = None,
) -> Tuple[bool, str]:
    rb_cfg = (
        gov_snapshot.get("riskless_boxes")
        if isinstance(gov_snapshot, Mapping) and "riskless_boxes" in gov_snapshot
        else gov_snapshot
    )
    veto = check_strict_pure_riskless_candidate_gate(_PureRisklessEnforcedSentinel, candidate_box, rb_cfg)
    return (True, "OK") if veto is None else (False, str(veto))


def ceil_to_tick_price(raw_px: float, tick_size: float = 0.001) -> float:
    """
    Quantizes `raw_px` strictly UPWARD (`ROUND_CEILING`) to an exact multiple of `tick_size` (`0.001` or `0.01`).
    Guarantees that subsequent `ROUND_FLOOR` tick quantization in `execute_unwind_order` preserves the exact
    ceiling price and NEVER rounds below break-even cost basis.
    """
    tk = 0.001 if (0.0 < float(tick_size or 0.0) <= 0.0015) else 0.01
    tk_dec = Decimal("0.001") if tk <= 0.0015 else Decimal("0.01")
    px_dec = Decimal(f"{max(0.0, float(raw_px)):.8f}") - Decimal("0.00000001")
    if px_dec <= Decimal("0"):
        return float(tk_dec)
    q = (px_dec / tk_dec).to_integral_value(rounding=ROUND_CEILING) * tk_dec
    return float(q)


def _extract_sorted_bids_asks(book: Optional[Mapping[str, Any]]) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    if not isinstance(book, Mapping):
        return [], []
    bids_out: List[Tuple[float, float]] = []
    asks_out: List[Tuple[float, float]] = []
    for b in book.get("bids") or ():
        px = _sf(b.get("price") if isinstance(b, Mapping) else (b[0] if isinstance(b, (list, tuple)) and b else 0.0))
        sz = _sf(b.get("size") if isinstance(b, Mapping) else (b[1] if isinstance(b, (list, tuple)) and len(b) > 1 else 0.0))
        if 0.0 < px < 1.0 and sz > 0.0:
            bids_out.append((px, sz))
    for a in book.get("asks") or ():
        px = _sf(a.get("price") if isinstance(a, Mapping) else (a[0] if isinstance(a, (list, tuple)) and a else 0.0))
        sz = _sf(a.get("size") if isinstance(a, Mapping) else (a[1] if isinstance(a, (list, tuple)) and len(a) > 1 else 0.0))
        if 0.0 < px <= 1.0 and sz > 0.0:
            asks_out.append((px, sz))
    bids_out.sort(key=lambda r: r[0], reverse=True)
    asks_out.sort(key=lambda r: r[0])
    return bids_out, asks_out


def _infer_tick_size(executor: Any, token_id: str, price_hint: float, bids: List[Tuple[float, float]]) -> float:
    if executor is not None and hasattr(executor, "get_token_tick_size"):
        try:
            tk = float(executor.get_token_tick_size(token_id, price_hint=price_hint) or 0.0)
            if tk in (0.001, 0.01):
                return tk
        except TypeError:
            try:
                tk = float(executor.get_token_tick_size(token_id) or 0.0)
                if tk in (0.001, 0.01):
                    return tk
            except Exception:
                pass
        except Exception:
            pass
    for px, _ in bids[:6]:
        if abs(round(px * 100.0) - (px * 100.0)) > 1e-4:
            return 0.001
    return 0.001 if price_hint >= 0.96 or price_hint <= 0.04 else 0.01


def _is_standalone_recyclable_carry(pos: Mapping[str, Any]) -> bool:
    """Strict structural filter: ONLY standalone 0%-fee single-leg carries; NEVER touches multi-leg boxes."""
    if not isinstance(pos, Mapping):
        return False
    from src.polymarket_research.riskless_machine_gun_engine import is_locked_arbitrage_box_leg

    if is_locked_arbitrage_box_leg(pos):
        return False
    if bool(pos.get("is_dominance_box")) or not bool(pos.get("is_single_leg_lock", False)):
        return False
    if str(pos.get("box_partner_trade_id") or "").strip():
        return False
    b_type = str(pos.get("box_type") or "").strip().upper()
    if b_type in {"DOMINANCE", "MULTI_LEG_BUNDLE", "COMPLETE_SET", "NEGRISK_2LEG", "SPORTS_CORRIDOR", "NBA_DOMINANCE"}:
        return False
    if bool(pos.get("is_liquidating")) or not bool(pos.get("inventory_reconciled", False)):
        return False
    st_u = str(pos.get("status") or "").strip().upper()
    if st_u in {"ENTRY_OUTCOME_UNKNOWN", "NOT_EXECUTED", "AWAITING_ONCHAIN_SETTLEMENT", "UNRESOLVED_SETTLEMENT"}:
        return False
    ex_st_u = str(pos.get("exit_order_status") or "").strip().upper()
    if "UNKNOWN" in ex_st_u:
        return False
    if _sf(pos.get("fee_rate_applied"), 0.07) > 1e-9:
        return False
    if str(pos.get("umaResolutionStatus") or pos.get("uma_resolution_status") or "").strip().lower() == "disputed":
        return False
    if "KMIA" in str(pos.get("asset") or "").upper() or "KMIA" in str(pos.get("trade_id") or "").upper():
        return False
    rem_sh = _sf(pos.get("remaining_shares", pos.get("entry_shares", 0.0)))
    if int(math.floor(rem_sh + 1e-9)) < 5:
        return False
    return True


def find_recyclable_zero_loss_open_carries(
    harvester: Any,
    *,
    challenger_net_cost: float,
    challenger_rem_tte_sec: float,
    exclude_market_ids: Optional[set[str]] = None,
    min_challenger_edge_bps: float = 200.0,
    max_victim_bps_hr: float = 45.0,
    min_velocity_mult: float = 4.0,
    min_profit_per_share: float = 0.001,
    book_lookup_fn: Optional[Callable[[str], Optional[Mapping[str, Any]]]] = None,
    now_ts: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Identifies open standalone `0%`-fee single-leg locks that can be sold IMMEDIATELY at a strictly
    positive net profit (`net_pnl >= +$0.005`, zero loss floor) to fund a `>= 200 bps` instant Taker arb.
    """
    now_u = float(now_ts if now_ts is not None else time.time())
    challenger_edge_bps = round((1.0 - float(challenger_net_cost or 1.0)) * 10000.0, 2)
    if challenger_edge_bps < float(min_challenger_edge_bps) - 1e-6:
        return []
    chal_hrs = max(0.20, float(challenger_rem_tte_sec or 900.0) / 3600.0)
    challenger_bps_hr = challenger_edge_bps / chal_hrs

    excl_mkts = {str(m) for m in (exclude_market_ids or set()) if m}
    ex = getattr(harvester, "executor", None)
    act_map = getattr(harvester, "active_positions", None) or {}
    candidates: List[Dict[str, Any]] = []

    for tid, pos in list(act_map.items()):
        if not _is_standalone_recyclable_carry(pos):
            continue
        mkt_id = str(pos.get("market_id") or "")
        tok_id = str(pos.get("token_id") or "")
        if not tok_id or (mkt_id and mkt_id in excl_mkts):
            continue
        rem_sh_full = _sf(pos.get("remaining_shares", pos.get("entry_shares", 0.0)))
        int_sh = int(math.floor(rem_sh_full + 1e-9))
        rem_cost = _sf(pos.get("remaining_cost_basis", pos.get("notional_usd", 0.0)))
        unamort_fee = max(0.0, _sf(pos.get("entry_fee_cash_usd", pos.get("fee_usd", 0.0))) - _sf(pos.get("realized_exit_fee", 0.0)))
        if rem_cost <= 0.0 or int_sh < 5 or rem_sh_full <= 0.0:
            continue

        unit_breakeven = (rem_cost + unamort_fee) / float(rem_sh_full)
        exp_ts = _sf(pos.get("candle_expiry_ts"), now_u + 7200.0)
        # Include conservative 2.0h UMA liveness floor for BOND1 carries
        sl_u = str(pos.get("sleeve") or "").upper()
        settle_floor_h = 2.0 if "BOND1" in sl_u else 0.50
        rem_hold_h = max(settle_floor_h, max(0.0, exp_ts - now_u) / 3600.0)
        rem_edge_bps = max(0.0, (1.0 - unit_breakeven) * 10000.0)
        victim_bps_hr = rem_edge_bps / rem_hold_h

        if victim_bps_hr > float(max_victim_bps_hr):
            continue
        if challenger_bps_hr < max(victim_bps_hr * float(min_velocity_mult), victim_bps_hr + 150.0):
            continue

        bk = None
        if callable(book_lookup_fn):
            bk = book_lookup_fn(tok_id)
        elif ex is not None and hasattr(ex, "get_market_book"):
            try:
                bk = ex.get_market_book(tok_id)
            except Exception:
                bk = None
        bids, asks = _extract_sorted_bids_asks(bk)
        if not bids:
            continue
        if asks and bids[0][0] >= asks[0][0]:
            continue  # Crossed book guard

        tick_sz = _infer_tick_size(ex, tok_id, unit_breakeven, bids)
        min_sell_px = ceil_to_tick_price(unit_breakeven + max(0.0005, float(min_profit_per_share)), tick_sz)
        if min_sell_px > 0.999 or min_sell_px <= 0.05:
            continue

        fillable_sh = sum(sz for px, sz in bids if px >= min_sell_px - 1e-9)
        if fillable_sh < float(int_sh) - 1e-6:
            continue

        est_proceeds = round(float(int_sh) * min_sell_px, 4)
        lot_frac = min(1.0, float(int_sh) / max(float(rem_sh_full), 1e-6))
        est_retired_cost = (rem_cost + unamort_fee) * lot_frac
        est_net_pnl = round(est_proceeds - est_retired_cost, 4)
        if est_net_pnl < 0.005:
            continue

        candidates.append({
            "trade_id": str(tid),
            "token_id": tok_id,
            "market_id": mkt_id,
            "sleeve": str(pos.get("sleeve") or ""),
            "shares": int_sh,
            "unit_breakeven": round(unit_breakeven, 5),
            "min_sell_px": min_sell_px,
            "best_bid": bids[0][0],
            "est_proceeds_usd": est_proceeds,
            "est_net_pnl_usd": est_net_pnl,
            "victim_bps_hr": round(victim_bps_hr, 2),
            "challenger_bps_hr": round(challenger_bps_hr, 2),
        })

    candidates.sort(key=lambda x: (float(x["victim_bps_hr"]), -float(x["est_proceeds_usd"])))
    return candidates


def recycle_open_zero_loss_carry_for_fast_arb(
    harvester: Any,
    *,
    needed_cash_gap_usd: float,
    challenger_net_cost: float,
    challenger_rem_tte_sec: float,
    challenger_sleeve: str = "",
    exclude_market_ids: Optional[set[str]] = None,
    book_lookup_fn: Optional[Callable[[str], Optional[Mapping[str, Any]]]] = None,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Executes 100% zero-loss open-carry recycling up to `needed_cash_gap_usd`:
      1. Cancels any resting passive exit ask (`exit_order_id`) first and verifies `matched == 0`.
      2. Submits `SELL` via `execute_unwind_order` at exact `ROUND_CEILING` `min_sell_px` (`> cost_per_share`).
      3. Closes/updates `active_positions` with exact realized exchange proceeds (`exit_cash_estimated = False`).
    """
    gap = float(needed_cash_gap_usd or 0.0)
    if gap <= 0.25 or getattr(harvester, "dry_run", True):
        return {"recycled_count": 0, "freed_cash_usd": 0.0, "realized_pnl_usd": 0.0, "trades": []}
    ex = getattr(harvester, "executor", None)
    if ex is None or not hasattr(ex, "execute_unwind_order"):
        return {"recycled_count": 0, "freed_cash_usd": 0.0, "realized_pnl_usd": 0.0, "trades": []}

    cands = find_recyclable_zero_loss_open_carries(
        harvester,
        challenger_net_cost=challenger_net_cost,
        challenger_rem_tte_sec=challenger_rem_tte_sec,
        exclude_market_ids=exclude_market_ids,
        book_lookup_fn=book_lookup_fn,
        now_ts=now_ts,
    )
    if not cands:
        return {"recycled_count": 0, "freed_cash_usd": 0.0, "realized_pnl_usd": 0.0, "trades": []}

    freed_cash = 0.0
    tot_pnl = 0.0
    recycled_ids: List[str] = []

    for c in cands:
        if freed_cash >= gap:
            break
        tid = c["trade_id"]
        pos = (getattr(harvester, "active_positions", None) or {}).get(tid)
        if not isinstance(pos, dict) or not _is_standalone_recyclable_carry(pos):
            continue
        tok_id = c["token_id"]
        int_sh = int(c["shares"])
        min_px = float(c["min_sell_px"])

        # Step 1: Cancel any resting passive Maker exit order FIRST so shares are unreserved on CLOB
        resting_oid = str(pos.get("exit_order_id") or "").strip()
        if resting_oid:
            if not hasattr(ex, "cancel_order"):
                continue
            try:
                c_res = ex.cancel_order(resting_oid, token_id=tok_id)
            except TypeError:
                c_res = ex.cancel_order(resting_oid)
            except Exception:
                continue
            c_matched = _sf(c_res.get("matched") if isinstance(c_res, Mapping) else getattr(c_res, "matched", 0.0))
            c_ok = bool(
                (c_res.get("is_canceled") if isinstance(c_res, Mapping) else getattr(c_res, "is_canceled", False))
                or str((c_res.get("outcome") if isinstance(c_res, Mapping) else getattr(c_res, "outcome", "")) or "").upper() == "CANCELED"
            )
            if not c_ok or c_matched > 0.001:
                # Resting exit order may have filled on CLOB; leave to normal exit reconciler!
                continue
            pos["exit_order_id"] = None
            pos["exit_order_status"] = "NONE"

        # Step 2: Execute limit SELL strictly >= min_px (mathematically >= cost_basis + min_profit)
        uw = ex.execute_unwind_order(
            tok_id,
            size=float(int_sh),
            side="SELL",
            min_price=min_px,
            neg_risk=bool(pos.get("neg_risk", False)),
        )
        if not isinstance(uw, Mapping):
            continue
        if uw.get("outcome_unknown"):
            pos["unwind_order_id"] = uw.get("orderID")
            pos["exit_order_status"] = "UNWIND_OUTCOME_UNKNOWN"
            if hasattr(harvester, "save_state"):
                harvester.save_state()
            break
        m_sz = _sf(uw.get("matched_size"), 0.0)
        if not uw.get("success") or m_sz <= 0.01:
            if hasattr(harvester, "save_state"):
                harvester.save_state()
            continue

        tak_u = _sf(uw.get("taking_amount"), m_sz * min_px)
        fee_u = _sf(uw.get("fee_usd"), 0.0)
        rem_cost_before = _sf(pos.get("remaining_cost_basis", pos.get("notional_usd", 0.0)))
        rem_sh_before = max(float(int_sh), _sf(pos.get("remaining_shares", pos.get("entry_shares", float(int_sh)))))
        oid_u = uw.get("orderID")

        st_lock = getattr(harvester, "_state_save_lock", None) or getattr(harvester, "_GLOBAL_STATE_SAVE_LOCK", None)
        if m_sz >= rem_sh_before - 0.01:
            pos["filled_exit_shares"] = round(_sf(pos.get("filled_exit_shares")) + m_sz, 4)
            pos["remaining_shares"] = 0.0
            pos["remaining_exit_shares"] = 0.0
            pos["remaining_cost_basis"] = 0.0
            pos["realized_exit_cash"] = round(_sf(pos.get("realized_exit_cash")) + tak_u, 4)
            pos["confirmed_realized_cash"] = pos["realized_exit_cash"]
            pos["realized_exit_fee"] = round(_sf(pos.get("realized_exit_fee")) + fee_u, 4)
            pos["exit_cash_estimated"] = False
            pos["estimated_exit_cash"] = 0.0
            pos["average_exit_price"] = round(tak_u / max(m_sz, 0.01), 5)
            pos["exit_price"] = pos["average_exit_price"]
            pos["unwind_order_id"] = oid_u
            pnl_closed = None
            if hasattr(harvester, "_close_position"):
                if st_lock is not None:
                    with st_lock:
                        pnl_closed = harvester._close_position(
                            tid, pos, "SETTLED", "ZERO_LOSS_VELOCITY_PREEMPT_RECYCLED", won=True
                        )
                else:
                    pnl_closed = harvester._close_position(
                        tid, pos, "SETTLED", "ZERO_LOSS_VELOCITY_PREEMPT_RECYCLED", won=True
                    )
            else:
                pnl_closed = round(tak_u - fee_u - rem_cost_before, 4)
                harvester.active_positions.pop(tid, None)
            realized_gain = _sf(pnl_closed, round(tak_u - fee_u - rem_cost_before, 4))
        else:
            frac = min(1.0, m_sz / max(rem_sh_before, 0.01))
            cost_retired = round(rem_cost_before * frac, 4)
            pos["filled_exit_shares"] = round(_sf(pos.get("filled_exit_shares")) + m_sz, 4)
            pos["remaining_shares"] = round(max(0.0, rem_sh_before - m_sz), 4)
            pos["remaining_exit_shares"] = pos["remaining_shares"]
            if pos["remaining_shares"] < 5.0:
                pos["hold_to_maturity_lock"] = True
            pos["remaining_cost_basis"] = round(max(0.0, rem_cost_before - cost_retired), 4)
            pos["realized_exit_cash"] = round(_sf(pos.get("realized_exit_cash")) + tak_u, 4)
            pos["confirmed_realized_cash"] = pos["realized_exit_cash"]
            pos["realized_exit_fee"] = round(_sf(pos.get("realized_exit_fee")) + fee_u, 4)
            pos["exit_cash_estimated"] = False
            pos["estimated_exit_cash"] = 0.0
            pos["unwind_order_id"] = oid_u
            if hasattr(harvester, "save_state"):
                if st_lock is not None:
                    with st_lock:
                        harvester.save_state()
                else:
                    harvester.save_state()
            realized_gain = round(tak_u - fee_u - cost_retired, 4)

        freed_cash = round(freed_cash + max(0.0, tak_u - fee_u), 4)
        tot_pnl = round(tot_pnl + realized_gain, 4)
        recycled_ids.append(tid)
        logger.info(
            f"[STAGE-C ZERO-LOSS RECYCLE] Freed ${tak_u - fee_u:.2f} (PnL +${realized_gain:.3f}) from {tid} "
            f"({c['victim_bps_hr']:.1f} bps/h -> {challenger_sleeve} {c['challenger_bps_hr']:.1f} bps/h)"
        )
        try:
            from src.polymarket_research.economic_attribution_ledger import emit_funnel_event

            emit_funnel_event(
                "COMPLETE_BASKET_LOCKED",
                sleeve=c["sleeve"] or "BOND1_UMA_RESOLUTION_CARRY",
                candidate_key=tid,
                box_type="ZERO_LOSS_VELOCITY_RECYCLE",
                est_profit_usd=realized_gain,
                notional_usd=tak_u,
                reason=f"recycled_for_{challenger_sleeve[:24]}",
            )
        except Exception:
            pass

    if recycled_ids and hasattr(ex, "get_collateral_balance"):
        try:
            new_c = ex.get_collateral_balance()
            if isinstance(new_c, (int, float)) and not isinstance(new_c, bool) and math.isfinite(float(new_c)) and float(new_c) >= 0.0:
                harvester._last_known_collateral = float(new_c)
        except Exception:
            pass

    return {
        "recycled_count": len(recycled_ids),
        "freed_cash_usd": freed_cash,
        "realized_pnl_usd": tot_pnl,
        "trades": recycled_ids,
    }


def evaluate_clinched_dead_leg_split_arb(
    candidate: Mapping[str, Any],
    bk_dead: Optional[Mapping[str, Any]],
    *,
    budget_usd: float,
    now_ts: Optional[float] = None,
    min_dead_bid_px: float = 0.008,
    min_total_dead_proceeds_usd: float = 0.08,
    max_clip_usd: float = 20.0,
    max_hold_sec: float = 21600.0,
    executor: Any = None,
) -> Optional[Dict[str, Any]]:
    """
    Evaluates whether a `100%` mathematically clinched (`p_model >= 0.9999`) `0%`-fee binary market
    can be monetized risklessly by splitting `$1.00 * Q` -> `Q WINNER + Q DEAD` and selling `Q DEAD`
    into live bids `>= min_dead_bid_px`.
    """
    if not isinstance(candidate, Mapping):
        return None
    now_u = float(now_ts if now_ts is not None else time.time())
    p_mod = _sf(candidate.get("p_model"), 0.0)
    if p_mod < 0.9999:
        return None
    fee_r = _sf(candidate.get("leg_a_fee_rate", candidate.get("fee_rate", 0.0)), 0.0)
    if fee_r > 1e-9:
        return None
    cid = str(candidate.get("condition_id") or candidate.get("leg_a_condition_id") or "").strip()
    if not (cid.startswith("0x") and len(cid) == 66):
        return None
    win_tok = str(candidate.get("leg_a_token_id") or candidate.get("token_id") or "").strip()
    dead_tok = str(candidate.get("opp_token_id") or candidate.get("leg_b_token_id") or "").strip()
    if not win_tok or not dead_tok or win_tok == dead_tok:
        return None

    exp_ts = _sf(candidate.get("expiry_ts") or candidate.get("leg_a_expiry_ts"), 0.0)
    rem_s = exp_ts - now_u if exp_ts > 0.0 else 0.0
    if rem_s <= 0.0 or rem_s > float(max_hold_sec):
        return None

    bids_d, asks_d = _extract_sorted_bids_asks(bk_dead)
    if not bids_d:
        return None
    if asks_d and bids_d[0][0] >= asks_d[0][0]:
        return None  # Crossed book guard

    tick_d = _infer_tick_size(executor, dead_tok, min_dead_bid_px, bids_d)
    min_sell_px = ceil_to_tick_price(max(0.004, float(min_dead_bid_px)), tick_d)
    if min_sell_px <= 0.0 or min_sell_px >= 0.50:
        return None

    avail_dead_sh = sum(sz for px, sz in bids_d if px >= min_sell_px - 1e-9)
    max_q = int(math.floor(min(float(max_clip_usd), max(0.0, float(budget_usd)), avail_dead_sh)))
    if max_q < 5:
        return None

    est_dead_cash = round(float(max_q) * min_sell_px, 4)
    if est_dead_cash < float(min_total_dead_proceeds_usd) - 1e-6:
        return None

    eff_win_cost_px = round(1.0 - min_sell_px, 5)
    edge_bps = round(min_sell_px * 10000.0, 2)
    bps_hr = round(edge_bps / max(0.25, rem_s / 3600.0), 2)
    return {
        "condition_id": cid,
        "winner_token_id": win_tok,
        "dead_token_id": dead_tok,
        "neg_risk": bool(candidate.get("leg_a_neg_risk", candidate.get("neg_risk", False))),
        "shares": max_q,
        "split_cost_usd": float(max_q),
        "min_dead_sell_px": min_sell_px,
        "best_dead_bid_px": bids_d[0][0],
        "est_dead_cash_usd": est_dead_cash,
        "effective_winner_cost_px": eff_win_cost_px,
        "net_edge_bps": edge_bps,
        "bps_per_hour": bps_hr,
        "expiry_ts": exp_ts,
    }


def execute_clinched_dead_leg_split_arb(
    harvester: Any,
    candidate: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Executes a 100% zero-loss Clinched Dead-Leg Split-to-Sell:
      1. Splits `$1.00 * Q` via `attempt_onchain_split_position`.
      2. Waits for `dead_token_id` ERC-1155 delivery.
      3. Sells `Q` shares of `dead_token_id` at `min_price = min_dead_sell_px` (`0%` fee).
      4. If `SELL` misses (`matched == 0`), merges all `Q` pairs right back into `$1.00 * Q` cash (`$0.00` loss).
         If `SELL` fills `m` shares, merges any `>= 5` unmatched pairs back into cash and records the
         clinched `$1.00`-guaranteed winning shares in `harvester.active_positions` at reduced net cost basis!
    """
    from src.polymarket_research.riskless_machine_gun_engine import (
        attempt_onchain_split_position,
        wait_for_erc1155_delivery,
    )

    now_u = float(now_ts if now_ts is not None else time.time())
    ex = getattr(harvester, "executor", None)
    if ex is None or getattr(harvester, "dry_run", True):
        return {"executed": False, "reason": "DRY_RUN_OR_NO_EXECUTOR"}

    cid = str(plan["condition_id"])
    win_tok = str(plan["winner_token_id"])
    dead_tok = str(plan["dead_token_id"])
    nr = bool(plan.get("neg_risk", False))
    q_sh = int(plan["shares"])
    min_px = float(plan["min_dead_sell_px"])

    pre_dead_bal = 0.0
    pre_win_bal = 0.0
    if hasattr(ex, "get_conditional_balance"):
        try:
            b0 = ex.get_conditional_balance(dead_tok)
            if isinstance(b0, (int, float)) and b0 >= 0.0:
                pre_dead_bal = float(b0)
        except Exception:
            pre_dead_bal = 0.0
        try:
            bw0 = ex.get_conditional_balance(win_tok)
            if isinstance(bw0, (int, float)) and bw0 >= 0.0:
                pre_win_bal = float(bw0)
        except Exception:
            pre_win_bal = 0.0

    prev_lk = getattr(harvester, "_last_known_collateral", None)
    sp_res = attempt_onchain_split_position(
        ex,
        cid,
        float(q_sh),
        neg_risk=nr,
        up_token_id=win_tok,
        down_token_id=dead_tok,
    )
    if not isinstance(sp_res, Mapping) or not sp_res.get("success"):
        return {
            "executed": False,
            "reason": f"SPLIT_FAILED:{(sp_res or {}).get('reason') or (sp_res or {}).get('error') or 'UNKNOWN'}",
        }

    sleeve_src = str(candidate.get("sleeve_source") or candidate.get("sleeve") or "W_PRUNE1_DEAD_NO_BOND")
    asset_s = str(candidate.get("asset") or "CLINCH")
    mid_a = str(candidate.get("leg_a_market_id") or candidate.get("market_id") or cid[:16])
    side_s = str(candidate.get("leg_a_side_label") or candidate.get("side_label") or "NO")
    exp_ts = float(plan.get("expiry_ts") or candidate.get("expiry_ts") or (now_u + 3600.0))
    lid = f"CLINCH_SPLIT_{asset_s}_{int(now_u * 1000) % 1000000}"
    st_lock = getattr(harvester, "_state_save_lock", None) or getattr(harvester, "_GLOBAL_STATE_SAVE_LOCK", None)
    try:
        from src.polymarket_research.riskless_protocol_v2_expansion import extract_sll_event_group_key

        evt_gk_sp = extract_sll_event_group_key(candidate)
    except Exception:
        evt_gk_sp = ""

    def _build_split_pos(win_sh: float, cost_u: float) -> Dict[str, Any]:
        if hasattr(harvester, "_make_single_leg_lock_pos"):
            p_out = harvester._make_single_leg_lock_pos(
                lid,
                "CLINCH_DEAD_SPLIT_LOCK",
                sleeve_src,
                asset_s,
                "clinch_split",
                mid_a,
                cid,
                win_tok,
                side_s,
                nr,
                win_sh,
                cost_u,
                0.0,
                0.0,
                1.0,
                "zero_fee_clinch_split",
                exp_ts,
                now_u,
                pre_win_bal,
                sp_res.get("tx_hash"),
                True,
                unk=False,
            )
        else:
            p_out = {
                "trade_id": lid,
                "box_type": "CLINCH_DEAD_SPLIT_LOCK",
                "sleeve": sleeve_src,
                "asset": asset_s,
                "market_id": mid_a,
                "condition_id": cid,
                "token_id": win_tok,
                "target_token": side_s,
                "neg_risk": nr,
                "entry_shares": win_sh,
                "remaining_shares": win_sh,
                "notional_usd": cost_u,
                "entry_price": round(cost_u / max(win_sh, 0.01), 5),
                "fee_usd": 0.0,
                "fee_rate_applied": 0.0,
                "candle_expiry_ts": exp_ts,
                "entry_ts": now_u,
                "hold_to_maturity_lock": True,
                "is_single_leg_lock": True,
            }
        p_out["opp_token_id"] = dead_tok
        if evt_gk_sp:
            p_out["event_group_key"] = evt_gk_sp
        p_out["inventory_reconciled"] = True
        p_out["status"] = "POSITION_CONFIRMED"
        return p_out

    # Persist provisional par-value split position immediately so SIGTERM/SIGKILL or HTTP errors mid-flight can NEVER orphan tokens!
    if isinstance(getattr(harvester, "active_positions", None), dict):
        prov_pos = _build_split_pos(float(q_sh), round(float(q_sh), 4))
        prov_pos["unmerged_dead_opp_shares"] = float(q_sh)
        if st_lock is not None:
            with st_lock:
                harvester.active_positions[lid] = prov_pos
                if hasattr(harvester, "save_state"):
                    harvester.save_state()
        else:
            harvester.active_positions[lid] = prov_pos
            if hasattr(harvester, "save_state"):
                harvester.save_state()

    delivered = False
    try:
        delivered = bool(
            wait_for_erc1155_delivery(
                ex,
                [dead_tok],
                pre_dead_bal + float(q_sh),
                timeout_sec=8.0,
                poll_sec=0.35,
            )
        )
    except Exception:
        delivered = False

    uw: Optional[Mapping[str, Any]] = None
    if delivered:
        try:
            uw_raw = ex.execute_unwind_order(
                dead_tok,
                size=float(q_sh),
                side="SELL",
                min_price=min_px,
                neg_risk=nr,
            )
            uw = uw_raw if isinstance(uw_raw, Mapping) else None
        except Exception as uw_exc:
            uw = {"success": False, "outcome_unknown": True, "error": str(uw_exc)}

    uw_unknown = bool(isinstance(uw, Mapping) and uw.get("outcome_unknown"))
    m_dead = _sf((uw or {}).get("matched_size"), 0.0) if (isinstance(uw, Mapping) and not uw_unknown) else 0.0
    dead_cash = (
        max(0.0, _sf(uw.get("taking_amount"), m_dead * min_px) - _sf(uw.get("fee_usd"), 0.0))
        if isinstance(uw, Mapping) and uw.get("success") and not uw_unknown
        else 0.0
    )

    if uw_unknown:
        # Never call on-chain complete-set merge while the dead-leg CLOB SELL order outcome is ambiguous!
        merged_pairs = 0.0
        rem_win_q = float(q_sh)
        net_cost_u = round(float(q_sh), 4)
    elif m_dead <= 0.01:
        merged_pairs = 0.0
        if hasattr(ex, "attempt_onchain_complete_set_merge"):
            try:
                m_res = ex.attempt_onchain_complete_set_merge(cid, min_pairs=float(q_sh), max_pairs=float(q_sh), neg_risk=nr)
                if isinstance(m_res, tuple) and m_res[0]:
                    merged_pairs = float(m_res[1])
            except Exception:
                merged_pairs = 0.0
        if merged_pairs >= float(q_sh) - 0.05:
            if isinstance(getattr(harvester, "active_positions", None), dict):
                if st_lock is not None:
                    with st_lock:
                        harvester.active_positions.pop(lid, None)
                        if hasattr(harvester, "save_state"):
                            harvester.save_state()
                else:
                    harvester.active_positions.pop(lid, None)
                    if hasattr(harvester, "save_state"):
                        harvester.save_state()
            return {
                "executed": False,
                "reason": "DEAD_BID_RACED_MERGED_FLAT_ZERO_LOSS" if delivered else "SPLIT_DELIVERY_TIMEOUT_MERGED_BACK",
                "merged_pairs": merged_pairs,
                "split_tx_hash": sp_res.get("tx_hash"),
            }
        # Fallback: register remaining clinched winner shares at $1.00 par if merge deferred so zero tokens are orphaned!
        rem_win_q = max(0.0, float(q_sh) - merged_pairs)
        net_cost_u = round(rem_win_q, 4)
    else:
        unmatched_pairs = int(math.floor(max(0.0, float(q_sh) - m_dead)))
        merged_pairs = 0.0
        if unmatched_pairs >= 5 and hasattr(ex, "attempt_onchain_complete_set_merge"):
            try:
                m_res = ex.attempt_onchain_complete_set_merge(
                    cid, min_pairs=float(unmatched_pairs), max_pairs=float(unmatched_pairs), neg_risk=nr
                )
                if isinstance(m_res, tuple) and m_res[0]:
                    merged_pairs = float(m_res[1])
            except Exception:
                merged_pairs = 0.0
        rem_win_q = round(max(0.0, float(q_sh) - merged_pairs), 4)
        net_cost_u = round(max(0.01, float(q_sh) - merged_pairs - dead_cash), 4)

    unmerged_dead_q = 0.0 if uw_unknown else round(max(0.0, float(q_sh) - m_dead - merged_pairs), 4)
    if rem_win_q > 0.01 and isinstance(getattr(harvester, "active_positions", None), dict):
        pos_w = _build_split_pos(rem_win_q, net_cost_u)
        pos_w["dead_leg_sold_shares"] = round(m_dead, 4)
        pos_w["dead_leg_cash_usd"] = round(dead_cash, 4)
        if uw_unknown:
            pos_w["dead_leg_unwind_outcome_unknown"] = True
            if isinstance(uw, Mapping) and uw.get("orderID"):
                pos_w["dead_leg_unwind_order_id"] = uw.get("orderID")
        elif unmerged_dead_q > 0.01:
            pos_w["unmerged_dead_opp_shares"] = unmerged_dead_q
        if st_lock is not None:
            with st_lock:
                harvester.active_positions[lid] = pos_w
                if hasattr(ex, "invalidate_collateral_cache"):
                    ex.invalidate_collateral_cache()
                harvester._pending_collateral_refresh = True
                if hasattr(harvester, "save_state"):
                    harvester.save_state()
        else:
            harvester.active_positions[lid] = pos_w
            if hasattr(ex, "invalidate_collateral_cache"):
                ex.invalidate_collateral_cache()
            harvester._pending_collateral_refresh = True
            if hasattr(harvester, "save_state"):
                harvester.save_state()
    elif isinstance(getattr(harvester, "active_positions", None), dict):
        harvester.active_positions.pop(lid, None)

    expected_post_collat = (
        max(0.0, round(float(prev_lk) - net_cost_u, 4))
        if (rem_win_q > 0.01 and isinstance(prev_lk, (int, float)) and not isinstance(prev_lk, bool))
        else None
    )
    collat_synced = False
    if hasattr(ex, "get_collateral_balance"):
        try:
            nc = ex.get_collateral_balance()
            if isinstance(nc, (int, float)) and not isinstance(nc, bool) and math.isfinite(float(nc)) and float(nc) >= 0.0:
                harvester._last_known_collateral = (
                    min(float(nc), expected_post_collat)
                    if (expected_post_collat is not None and float(nc) > expected_post_collat + 0.25)
                    else float(nc)
                )
                collat_synced = True
        except Exception:
            pass
    if not collat_synced and expected_post_collat is not None:
        harvester._last_known_collateral = expected_post_collat

    locked_profit_u = round(rem_win_q - net_cost_u, 4)
    try:
        from src.polymarket_research.economic_attribution_ledger import emit_funnel_event

        emit_funnel_event(
            "COMPLETE_BASKET_LOCKED",
            sleeve=sleeve_src,
            candidate_key=lid,
            box_type="CLINCH_DEAD_SPLIT_LOCK",
            asset=asset_s,
            net_edge_bps=round((locked_profit_u / max(1.0, float(q_sh))) * 10000.0, 2),
            est_profit_usd=locked_profit_u,
            notional_usd=net_cost_u,
            reason=f"dead_leg_sold={m_dead:.1f}sh_cash=${dead_cash:.3f}",
        )
    except Exception:
        pass

    return {
        "executed": bool(m_dead > 0.01 or rem_win_q > 0.01),
        "trade_id": lid,
        "shares": rem_win_q,
        "dead_sold_shares": round(m_dead, 4),
        "dead_cash_usd": round(dead_cash, 4),
        "net_cost_usd": net_cost_u,
        "locked_profit_usd": locked_profit_u,
        "split_tx_hash": sp_res.get("tx_hash"),
    }
