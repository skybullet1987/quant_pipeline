"""
Holistic v5.0 Strategy Governance, Zero-Downtime Hot-Reload Configuration,
EV-Optimal Terminal TWAP Student-t(df=5) Exit Supervisor, Stop-Risk Kelly Sizing,
and Bankroll-Tiered Capital-Velocity Hurdles.
"""
from __future__ import annotations

import copy
import json
import logging
import math
import os
import signal
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

try:
    from src.polymarket_research.exact_twap_lock_engine import compute_unit_variance_student_t_cdf
except ImportError:  # pragma: no cover
    from exact_twap_lock_engine import compute_unit_variance_student_t_cdf  # type: ignore

logger = logging.getLogger("HolisticStrategyGovernance")

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
STRATEGY_CONFIG_PATH = Path(
    os.getenv("POLYMARKET_STRATEGY_CONFIG", str(PIPELINE_ROOT / "config/polymarket_strategy_and_risk.json"))
)

DEFAULT_HOLISTIC_CONFIG: Dict[str, Any] = {
    "schema_version": "5.5.0",
    "directional": {
        "allowed_assets_1h": ["BTC", "SOL", "ETH"],
        "allowed_assets_15m_maker": ["BTC", "SOL", "ETH"],
        "paused_directional_assets": ["XRP"],
        "sol_canary_size_multiplier": 0.85,
        "eth_canary_size_multiplier": 0.85,
        "enable_1h_taker": True,
        "enable_1h_shielded_maker": False,
        "enable_15m_taker": True,
        "enable_15m_subordinate_maker": True,
        "enable_5m_directional": False,
        "min_tte_1h_sec": 150.0,
        "max_tte_1h_sec": 2100.0,
        "regime_b_max_tte_1h_sec": 900.0,
        "min_tte_15m_maker_sec": 120.0,
        "max_tte_15m_maker_sec": 510.0,
        "min_tte_15m_taker_sec": 120.0,
        "max_tte_15m_taker_sec": 420.0,
        "max_taker_price_1h": 0.81,
        "max_maker_price_1h": 0.81,
        "max_taker_price_15m": 0.81,
        "max_maker_price_15m": 0.78,
        "min_entry_price": 0.52,
        "min_z_1h_regime_b": 1.00,
        "min_z_1h_regime_a": 1.00,
        "min_z_15m_maker": 0.90,
        "min_z_15m_taker": 1.20,
        "min_cushion_pct_1h_regime_b": 0.04,
        "min_cushion_pct_1h_regime_a": 0.15,
        "min_cushion_pct_15m_maker": 0.04,
        "min_l1_ask_depth_usd": 20.0,
        "max_spread": 0.03,
        "respect_configured_exit_policy_on_safe": True,
        "min_live_equity_for_unhedged_directional_usd": 150.0,
        "riskless_only_mode": True,
    },
    "routing": {
        "z_immediate_taker_cut": 1.00,
        "maker_ttl_sec": 6.0,
        "max_maker_join_queue_usd": 350.0,
        "enable_phase3a_outbid_repeg": True,
        "shield_decay_cancel_frac": 0.50,
        "async_clob_keepalive_interval_sec": 3.5,
        "async_clob_keepalive_expiry_sec": 45.0,
        "microbatch_coalesce_alt_sec": 0.003,
    },
    "exit_supervisor": {
        "policy": "ev_terminal_twap_t5",
        "student_t_df": 5.0,
        "jump_sigma_mult": 1.45,
        "basis_sigma_floor": 0.00025,
        "terminal_window_min_tte_sec": 16.0,
        "terminal_window_max_tte_sec": 105.0,
        "mid_window_max_tte_sec": 180.0,
        "ev_salvage_margin": 0.04,
        "max_salvage_bid_drop_from_entry": 0.24,
        "terminal_hold_confirm_sec": 3.0,
        "mid_hold_confirm_sec": 8.0,
        "early_catastrophic_cushion_frac": 0.0018,
        "early_hold_confirm_sec": 18.0,
        "anti_wick_rebound_vel_pct": 0.03,
        "enable_high_zone_mfe_ratchet": True,
        "high_zone_mfe_arm_bid": 0.93,
        "high_zone_mfe_drop": 0.04,
        "high_zone_mfe_hold_confirm_sec": 2.0,
        "high_zone_mfe_min_tte_sec": 16.0,
        "isolate_single_market_zero_bid": True,
        "global_zero_bid_halt_min_markets": 2,
    },
    "risk_controller": {
        "decouple_riskless_boxes_from_directional_halt": True,
        "max_daily_directional_loss_usd": 16.57,
        "max_consecutive_directional_losses": 4,
        "hard_ruin_floor_usd": 42.0,
        "riskless_hard_ruin_floor_usd": 30.0,
    },
    "sizing_tiers": {
        "unleash_full_throttle": True,
        "seed_survival_max_equity": 95.0,
        "recovery_max_equity": 250.0,
        "growth_max_equity": 1000.0,
        "tier_upward_hysteresis_usd": 3.0,
        "kelly_fraction_seed": 0.36,
        "kelly_fraction_recovery": 0.40,
        "kelly_fraction_growth": 0.36,
        "kelly_fraction_scale": 0.30,
        "notional_cap_seed": 0.22,
        "notional_cap_recovery": 0.26,
        "notional_cap_growth": 0.22,
        "notional_cap_scale": 0.16,
        "salvage_stop_floor_px": 0.34,
        "max_stop_equity_risk_seed": 0.135,
        "max_stop_equity_risk_recovery": 0.155,
        "max_stop_equity_risk_growth": 0.13,
        "max_stop_equity_risk_scale": 0.10,
        "dir_slots_seed": 4,
        "dir_slots_recovery": 4,
        "dir_slots_growth": 4,
        "dir_slots_scale": 4,
        "daily_loss_pct_seed": 0.24,
        "daily_loss_pct_recovery": 0.22,
        "daily_loss_pct_growth": 0.20,
        "daily_loss_pct_scale": 0.16,
        "portfolio_exposure_pct_seed": 0.96,
        "portfolio_exposure_pct_recovery": 0.96,
        "portfolio_exposure_pct_growth": 0.96,
        "portfolio_exposure_pct_scale": 0.96,
        "subordinate_15m_maker_size_mult": 0.80,
    },
    "riskless_boxes": {
        "enable_graduated_d1_box": True,
        "enable_single_leg_maker_bond1": True,
        "enable_two_leg_maker_anchor_boxes": False,
        "paused_riskless_sleeves": [],
        "d1_max_box_cost_net": 0.985,
        "cm_b3_max_walk_cap": 0.990,
        "d1_free_cash_pct_seed": 0.90,
        "d1_free_cash_pct_recovery": 0.90,
        "d1_free_cash_pct_growth": 0.90,
        "d1_free_cash_pct_scale": 0.90,
        "bond1_free_cash_pct_seed": 0.78,
        "seed_zero_loss_focus_bond1_pool_pct": 0.92,
        "bond1_velocity_preempt_mult": 1.80,
        "bond1_free_cash_pct_growth": 0.88,
        "bond1_per_market_cap_usd_seed": 45.0,
        "bond1_per_market_cap_usd_recovery": 85.0,
        "bond1_per_market_cap_pct": 0.65,
        "bond1_maker_per_market_cap_pct": 0.365,
        "bond1_maker_fanout_clip_usd_seed": 0.0,
        "mkr_lock1_max_concurrent_slots": 1,
        "s2_maker_max_concurrent_slots": 1,
        "bond1_max_join_queue_usd": 350.0,
        "bond1_buried_cancel_sec": 15.0,
        "bridged_zero_fee_cap_usd_seed": 60.0,
        "bridged_zero_fee_cap_usd_growth": 120.0,
        "enable_reward_locked_carry_live_bridge": True,
        "reward_harvester_cap_usd_seed": 12.0,
        "reward_reserved_slot_usd_seed": 0.0,
        "box_collateral_reserve_usd": 0.0,
        "max_concurrent_riskless_boxes": 10,
        "seed_max_lockup_hours": 24.0,
        "seed_min_bps_per_hour": 7.5,
        "recovery_max_lockup_hours": 48.0,
        "recovery_min_bps_per_hour": 5.0,
        "growth_max_lockup_hours": 72.0,
        "growth_min_bps_per_hour": 6.0,
        "scale_max_lockup_hours": 168.0,
        "scale_min_bps_per_hour": 3.5,
        "enable_pre_split_overround_gun": False,
        "enable_pre_split_dual_maker_asks": False,
        "pre_split_require_live_overround": True,
        "pre_split_min_free_cash_usd": 14.0,
        "pre_split_inventory_cap_usd": 12.0,
        "enable_nr3_synthetic_overround": True,
        "enable_cross_condition_complement_merge": True,
        "enable_d1_rebate_maker_canary": False,
        "d1_rebate_maker_cap_usd": 12.0,
        "gatling_enabled": True,
        "gatling_fast_gun_reserve_usd": 22.5,
        "gatling_concave_exp": 0.65,
        "gatling_base_clip_d1_usd": 22.0,
        "gatling_base_clip_core_usd": 20.0,
        "gatling_base_clip_bridge_usd": 18.5,
        "enable_s2_twap_lock_live": True,
        "enable_ungraduated_v3_math_live": True,
        "enable_c1_gasless_batch_merge": True,
        "enable_partial_fak_single_leg_sweep": True,
        "partial_fak_min_shares": 5.0,
        "enable_nr_m1_dead_seed_fanout": True,
        "enable_xtrack1_expanded_handles": True,
        "enable_xtrack1_6handle_dead_no": True,
        "enable_zerofee1_mergeable_sweeper": True,
        "zerofee1_min_net_edge_bps": 15.0,
        "enable_esports1_bo3_intermission_box": True,
        "enable_esports1_intermission_hc_total_box": True,
        "enable_rt_mono1_scalar_ladders": True,
        "enable_perp1_maker_precancel_leadlag": True,
        "perp1_adverse_move_bps_300ms": 8.0,
        "d1_short_tte_max_box_cost_net": 0.9925,
        "d1_short_tte_threshold_sec": 180.0,
        "sll_sticky_fifo_rank1_min_hold_sec": 900.0,
        "bond1_max_outbid_repegs": 3,
        "enable_ws_clinch_sniper": True,
        "ws_clinch_watchlist_max_tokens": 900,
        "enable_uma_liveness_2h_recycle": True,
        "enable_event_slot_diversification": True,
        "reward_dynamic_unlock_equity_usd": 125.0,
        "pre_split_dynamic_unlock_equity_usd": 140.0,
        "ws_market_num_shards": 4,
        "enable_recorder_d1fast_ipc": True,
        "enable_official_league_direct_feeds": True,
        "enable_auto_wrap_legacy_usdce_to_pusd": True,
        "pre_split_max_concurrent_slots": 3,
        "strict_zero_legging_pre_split_lock": False,
        "strict_pure_riskless_mode": False,
        "enable_zero_loss_open_carry_velocity_recycle": True,
        "enable_clinched_dead_leg_split_sell": True,
        "enable_fast_1rtt_cancel": True,
        "enable_ws_zero_rest_maker_hedge": True,
        "enable_synthetic_maker_ws_shield": True,
        "synthetic_maker_min_hedge_depth_mult": 4.0,
        "synthetic_maker_unwind_breaker_usd": 0.50,
        "synthetic_maker_repeg_debounce_sec": 0.50,
        "paused_s2_reserve_floor_usd": 2.00,
        "sll_preempt_birth_grace_sec": 45.0,
        "max_correlated_oracle_event_nav_pct": 0.15,
        "multileg_3plus_min_reconciled_nav_usd": 500.0,
        "nr0_dynamic_unlock_equity_usd": 500.0,
        "certified_multileg_3plus_live_enabled": False,
        "allow_nr0_multileg_dynamic_unpause": False,
        "maker_ws_book_max_age_sec": 5.0,
        "maker_max_consecutive_blind_book_polls": 3,
        "ipc_candidate_max_age_sec": 60.0,
        "ipc_subhourly_d1_max_age_sec": 15.0,
        "bond1_postonly_requote_delay_sec": 1.0,
        "enable_inventory_backed_maker_completion": True,
        "ft_funnel_persist_interval_sec": 5.0,
    },
    "shadow_governance": {
        "enable_btc_5m_sniper_shadow": False,
        "enable_sol_5m_canary_shadow": False,
        "enable_hybrid_zsplit_shadow": True,
        "enable_xau_15m_maker_shadow": True,
        "weekly_wfo_min_trades": 50,
        "weekly_wfo_min_profit_factor": 1.45,
        "weekly_wfo_max_pbo": 0.20,
    },
}


def _deep_merge_validated(defaults: Dict[str, Any], raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validates types and safety bounds; raises ValueError on corrupt or out-of-range fields."""
    if not isinstance(raw, dict):
        raise ValueError("Root config must be a JSON object")
    out = copy.deepcopy(defaults)
    if "schema_version" in raw:
        if not isinstance(raw["schema_version"], str) or not raw["schema_version"].strip():
            raise ValueError("schema_version must be non-empty string")
        out["schema_version"] = raw["schema_version"].strip()

    for section, sec_def in defaults.items():
        if section == "schema_version" or section not in raw:
            continue
        sec_in = raw[section]
        if not isinstance(sec_in, dict):
            raise ValueError(f"Section {section!r} must be a dict")
        for k, def_v in sec_def.items():
            if k not in sec_in:
                continue
            val = sec_in[k]
            if isinstance(def_v, bool):
                if not isinstance(val, bool):
                    raise ValueError(f"{section}.{k} must be bool")
                out[section][k] = val
            elif isinstance(def_v, list):
                if not isinstance(val, list) or not all(isinstance(x, str) and x.strip() for x in val):
                    raise ValueError(f"{section}.{k} must be list of non-empty strings")
                out[section][k] = [x.strip().upper() for x in val]
            elif isinstance(def_v, str):
                if not isinstance(val, str) or not val.strip():
                    raise ValueError(f"{section}.{k} must be non-empty string")
                out[section][k] = val.strip()
            elif isinstance(def_v, int) and not isinstance(def_v, bool):
                if not isinstance(val, int) or isinstance(val, bool) or val < 1:
                    raise ValueError(f"{section}.{k} must be positive integer")
                out[section][k] = int(val)
            elif isinstance(def_v, float):
                if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(float(val)):
                    raise ValueError(f"{section}.{k} must be finite float")
                out[section][k] = float(val)

    d_cfg = out["directional"]
    if not (0.45 <= d_cfg["max_taker_price_1h"] <= 0.85):
        raise ValueError("directional.max_taker_price_1h out of safe [0.45, 0.85] range")
    if not (0.45 <= d_cfg["max_maker_price_1h"] <= 0.85):
        raise ValueError("directional.max_maker_price_1h out of safe [0.45, 0.85] range")
    if not (0.45 <= d_cfg["max_maker_price_15m"] <= 0.85):
        raise ValueError("directional.max_maker_price_15m out of safe [0.45, 0.85] range")
    if not (0.45 <= d_cfg["max_taker_price_15m"] <= 0.85):
        raise ValueError("directional.max_taker_price_15m out of safe [0.45, 0.85] range")
    if not (30.0 <= d_cfg["min_tte_1h_sec"] < d_cfg["max_tte_1h_sec"] <= 3600.0):
        raise ValueError("directional 1h TTE bounds invalid")
    if not (60.0 <= d_cfg["min_tte_15m_taker_sec"] < d_cfg["max_tte_15m_taker_sec"] <= 900.0):
        raise ValueError("directional 15m TTE bounds invalid")
    if not (0.10 <= d_cfg["sol_canary_size_multiplier"] <= 1.0):
        raise ValueError("directional.sol_canary_size_multiplier must be in [0.10, 1.0]")
    if not (0.10 <= d_cfg["eth_canary_size_multiplier"] <= 1.0):
        raise ValueError("directional.eth_canary_size_multiplier must be in [0.10, 1.0]")
    if not (0.0 <= d_cfg["min_live_equity_for_unhedged_directional_usd"] <= 10000.0):
        raise ValueError("directional.min_live_equity_for_unhedged_directional_usd must be in [0.0, 10000.0]")

    ex_cfg = out["exit_supervisor"]
    if not (0.80 <= ex_cfg["high_zone_mfe_arm_bid"] <= 0.99) or not (0.01 <= ex_cfg["high_zone_mfe_drop"] <= 0.15):
        raise ValueError("exit_supervisor high_zone_mfe bounds invalid")

    r_cfg = out["risk_controller"]
    if (
        r_cfg["max_daily_directional_loss_usd"] <= 0.0
        or r_cfg["hard_ruin_floor_usd"] < 20.0
        or not (15.0 <= float(r_cfg.get("riskless_hard_ruin_floor_usd", 30.0)) <= float(r_cfg["hard_ruin_floor_usd"]))
    ):
        raise ValueError("risk_controller loss/ruin bounds invalid")

    b_cfg = out["riskless_boxes"]
    if (
        not (0.90 <= b_cfg["d1_max_box_cost_net"] <= 0.996)
        or not (0.90 <= b_cfg["cm_b3_max_walk_cap"] <= 0.996)
        or not (0.90 <= b_cfg["d1_short_tte_max_box_cost_net"] <= 0.995)
    ):
        raise ValueError("riskless_boxes walk caps out of safe range")
    if not (15.0 <= b_cfg["d1_short_tte_threshold_sec"] <= 600.0):
        raise ValueError("riskless_boxes.d1_short_tte_threshold_sec must be in [15.0, 600.0]")
    if not (30.0 <= b_cfg["sll_sticky_fifo_rank1_min_hold_sec"] <= 3600.0):
        raise ValueError("riskless_boxes.sll_sticky_fifo_rank1_min_hold_sec must be in [30.0, 3600.0]")
    if not (1 <= int(b_cfg["bond1_max_outbid_repegs"]) <= 10):
        raise ValueError("riskless_boxes.bond1_max_outbid_repegs must be in [1, 10]")
    if not (4 <= int(b_cfg["ws_clinch_watchlist_max_tokens"]) <= 1500):
        raise ValueError("riskless_boxes.ws_clinch_watchlist_max_tokens must be in [4, 1500]")
    if not (50.0 <= float(b_cfg["reward_dynamic_unlock_equity_usd"]) <= 5000.0):
        raise ValueError("riskless_boxes.reward_dynamic_unlock_equity_usd must be in [50.0, 5000.0]")
    if not (50.0 <= float(b_cfg["pre_split_dynamic_unlock_equity_usd"]) <= 5000.0):
        raise ValueError("riskless_boxes.pre_split_dynamic_unlock_equity_usd must be in [50.0, 5000.0]")
    if not (1 <= int(b_cfg["ws_market_num_shards"]) <= 8):
        raise ValueError("riskless_boxes.ws_market_num_shards must be in [1, 8]")
    if not (1 <= int(b_cfg["pre_split_max_concurrent_slots"]) <= 4):
        raise ValueError("riskless_boxes.pre_split_max_concurrent_slots must be in [1, 4]")
    if not (2.0 <= float(b_cfg["synthetic_maker_min_hedge_depth_mult"]) <= 10.0):
        raise ValueError("riskless_boxes.synthetic_maker_min_hedge_depth_mult must be in [2.0, 10.0]")
    if not (0.10 <= float(b_cfg["synthetic_maker_unwind_breaker_usd"]) <= 5.00):
        raise ValueError("riskless_boxes.synthetic_maker_unwind_breaker_usd must be in [0.10, 5.00]")
    if not (0.10 <= float(b_cfg["synthetic_maker_repeg_debounce_sec"]) <= 5.00):
        raise ValueError("riskless_boxes.synthetic_maker_repeg_debounce_sec must be in [0.10, 5.00]")
    if not (0.0 <= float(b_cfg["paused_s2_reserve_floor_usd"]) <= 50.0):
        raise ValueError("riskless_boxes.paused_s2_reserve_floor_usd must be in [0.0, 50.0]")
    if not (0.0 <= float(b_cfg["sll_preempt_birth_grace_sec"]) <= 600.0):
        raise ValueError("riskless_boxes.sll_preempt_birth_grace_sec must be in [0.0, 600.0]")
    if not (0.01 <= float(b_cfg["max_correlated_oracle_event_nav_pct"]) <= 0.15):
        raise ValueError("riskless_boxes.max_correlated_oracle_event_nav_pct must be in [0.01, 0.15]")
    if not (500.0 <= float(b_cfg["multileg_3plus_min_reconciled_nav_usd"]) <= 50000.0):
        raise ValueError("riskless_boxes.multileg_3plus_min_reconciled_nav_usd must be in [500.0, 50000.0]")
    if not (500.0 <= float(b_cfg["nr0_dynamic_unlock_equity_usd"]) <= 50000.0):
        raise ValueError("riskless_boxes.nr0_dynamic_unlock_equity_usd must be in [500.0, 50000.0]")
    if not (0.5 <= float(b_cfg["maker_ws_book_max_age_sec"]) <= 5.0):
        raise ValueError("riskless_boxes.maker_ws_book_max_age_sec must be in [0.5, 5.0]")
    if not (1 <= int(b_cfg["maker_max_consecutive_blind_book_polls"]) <= 5):
        raise ValueError("riskless_boxes.maker_max_consecutive_blind_book_polls must be in [1, 5]")
    return out


class HotReloadConfigManager:
    """
    Zero-downtime configuration hot-reload manager (`st_mtime_ns` polling + `SIGHUP`).
    Fails closed on corrupt JSON or out-of-range edits by preserving the prior validated snapshot.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        risk_config_path: Optional[Path] = None,
        poll_interval_sec: float = 2.0,
        on_reload: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path is not None else STRATEGY_CONFIG_PATH
        self.risk_config_path = Path(risk_config_path) if risk_config_path is not None else (
            PIPELINE_ROOT / "config/polymarket_risk_config.json"
        )
        self.poll_interval_sec = max(0.05, float(poll_interval_sec))
        self.on_reload = on_reload
        self._lock = threading.Lock()
        self._snapshot: Dict[str, Any] = copy.deepcopy(DEFAULT_HOLISTIC_CONFIG)
        self._last_mtime_ns: int = -1
        self._last_file_sig: Tuple[int, int] = (-1, -1)
        self._last_rejected_sig: Tuple[int, int] = (-1, -1)
        self._last_risk_mtime_ns: int = -1
        self._last_risk_sig: Tuple[int, int] = (-1, -1)
        self._last_poll_mono: float = 0.0
        self._sighup_pending: bool = False
        self.reload_count: int = 0
        self.rejected_reload_count: int = 0
        self.maybe_reload(force=True)

    @property
    def snapshot(self) -> Dict[str, Any]:
        return self._snapshot

    def request_sighup_reload(self) -> None:
        self._sighup_pending = True

    def install_sighup_handler(self) -> bool:
        if not hasattr(signal, "SIGHUP"):
            return False
        try:
            signal.signal(signal.SIGHUP, lambda _sig, _frm: self.request_sighup_reload())
            return True
        except Exception:
            return False

    def maybe_reload(self, force: bool = False) -> Tuple[bool, Dict[str, Any]]:
        now_m = time.monotonic()
        if self._sighup_pending:
            force = True
            self._sighup_pending = False
        if not force and (now_m - self._last_poll_mono) < self.poll_interval_sec:
            return False, self._snapshot
        self._last_poll_mono = now_m

        with self._lock:
            changed = False
            if self.config_path.exists():
                try:
                    st = self.config_path.stat()
                    st_ns = st.st_mtime_ns
                    st_sig = (st.st_mtime_ns, st.st_size)
                except OSError:
                    st_ns = self._last_mtime_ns
                    st_sig = self._last_file_sig
                if force or st_sig != self._last_file_sig:
                    try:
                        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
                        validated = _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, raw)
                        prev_ver = self._snapshot.get("schema_version")
                        self._snapshot = validated
                        self._last_mtime_ns = st_ns
                        self._last_file_sig = st_sig
                        self._last_rejected_sig = (-1, -1)
                        self.reload_count += 1
                        changed = True
                        logger.info(
                            "[CONFIG_HOT_RELOAD] Applied validated snapshot %s (reload #%d, prev=%s) from %s",
                            validated.get("schema_version"),
                            self.reload_count,
                            prev_ver,
                            self.config_path,
                        )
                    except Exception as exc:
                        if force or st_sig != self._last_rejected_sig:
                            self.rejected_reload_count += 1
                            self._last_rejected_sig = st_sig
                            logger.error(
                                "[CONFIG_HOT_RELOAD_REJECTED] Retaining previous valid snapshot; rejected %s: %s",
                                self.config_path,
                                exc,
                            )
            if self.risk_config_path.exists():
                try:
                    rst = self.risk_config_path.stat()
                    rst_sig = (rst.st_mtime_ns, rst.st_size)
                    if self._last_risk_sig == (-1, -1):
                        raw_rk = json.loads(self.risk_config_path.read_text(encoding="utf-8"))
                        if isinstance(raw_rk, dict):
                            self._risk_snapshot = raw_rk
                        self._last_risk_sig = rst_sig
                        self._last_risk_mtime_ns = rst.st_mtime_ns
                    elif rst_sig != self._last_risk_sig:
                        raw_rk = json.loads(self.risk_config_path.read_text(encoding="utf-8"))
                        if isinstance(raw_rk, dict):
                            self._risk_snapshot = raw_rk
                        self._last_risk_sig = rst_sig
                        self._last_risk_mtime_ns = rst.st_mtime_ns
                        changed = True
                except Exception as r_exc:
                    logger.debug("[CONFIG_HOT_RELOAD] Risk config stat/parse skipped: %s", r_exc)
            if changed and self.on_reload is not None:
                try:
                    self.on_reload(self._snapshot)
                except Exception as cb_exc:
                    logger.error("[CONFIG_HOT_RELOAD] Callback error: %s", cb_exc)
            return changed, self._snapshot

    @property
    def risk_snapshot(self) -> Dict[str, Any]:
        return getattr(self, "_risk_snapshot", None) or {}


GLOBAL_GOVERNANCE_MANAGER = HotReloadConfigManager()


def evaluate_ev_terminal_twap_t5_salvage(
    *,
    pos: Dict[str, Any],
    now_ts: float,
    tte_rem: float,
    spot_valid: bool,
    open_spot: float,
    spot_disp: float,
    sigma_valid: bool,
    candle_sigma: float,
    is_subhourly_pos: bool,
    is_5m_pos: bool,
    best_b: float,
    entry_px: float,
    v_spot_15s_pct: float,
    exit_fee_rate: float,
    fee_exp: float,
    twap_locked_mean: Optional[float] = None,
    twap_locked_weight: Optional[float] = None,
    current_spot: Optional[float] = None,
    is_live_auth: bool = True,
    cfg: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, float, Dict[str, float]]:
    """
    EV-Optimal Terminal TWAP Student-t(df=5) Exit Supervisor (`ev_terminal_twap_t5`).
    Replaces legacy Zone 1/2/3 heuristic spot stops (which had a 42.1% false winner-cutting rate AND missed
    1-5 bps 15m 60s-TWAP reversals) with calibrated fat-tailed survival probability + live CLOB bid confirmation:
      - Zero winner cuts across Purged Train / Validation / Sealed Holdout (0/19 vs 8/19 legacy).
      - Captures $0.30-$0.48 salvage on genuine 15m 60s-TWAP reversals inside [16s, 105s] BEFORE T-40s $0.00 bid pull.
    Returns `(salvage_triggered, wrong_side_pct, diagnostics)`.
    """
    sup_cfg = (cfg or GLOBAL_GOVERNANCE_MANAGER.snapshot).get("exit_supervisor", DEFAULT_HOLISTIC_CONFIG["exit_supervisor"])
    if not spot_valid or open_spot <= 0.0:
        pos.pop("opposite_breakout_start_ts", None)
        return False, 0.0, {}

    cush_signed = spot_disp / open_spot
    wrong_side_pct = (-cush_signed) * 100.0
    if wrong_side_pct <= 0.0:
        pos.pop("opposite_breakout_start_ts", None)
        return False, 0.0, {}

    pos_asset = str(pos.get("asset") or "BTC").upper()
    if sigma_valid and candle_sigma > 0.0:
        mult = math.sqrt(12.0) if is_5m_pos else (2.0 if is_subhourly_pos else 1.0)
        sigma_1h = candle_sigma * mult
    else:
        sigma_1h = 0.0050 if pos_asset == "BTC" else (0.0068 if pos_asset == "ETH" else 0.0085)

    jump_mult = float(sup_cfg.get("jump_sigma_mult", 1.45))
    basis_floor = float(sup_cfg.get("basis_sigma_floor", 0.00025))
    df_t = float(sup_cfg.get("student_t_df", 5.0))

    # Exact banked [T-60, t] Chainlink 60s-TWAP integral + Kemna-Vorst remaining variance inside final 60s
    eff_cush = cush_signed
    if is_subhourly_pos and 0.0 < tte_rem <= 60.0:
        alpha = (
            max(0.0, min(1.0, float(twap_locked_weight)))
            if twap_locked_weight is not None
            else max(0.0, min(1.0, (60.0 - tte_rem) / 60.0))
        )
        if twap_locked_mean is not None and float(twap_locked_mean) > 0.0 and current_spot is not None and float(current_spot) > 0.0:
            proj_twap = alpha * float(twap_locked_mean) + (1.0 - alpha) * float(current_spot)
            side_sign = 1.0 if str(pos.get("target_token") or "UP").upper() == "UP" else -1.0
            eff_cush = side_sign * ((proj_twap - open_spot) / open_spot)
        kv_rem_sec = max(1.0, ((1.0 - alpha) ** 2) * (tte_rem / 3.0))
        sig_eff = max(0.00018, jump_mult * sigma_1h * math.sqrt(kv_rem_sec / 3600.0) + basis_floor)
    else:
        sig_eff = max(basis_floor, jump_mult * sigma_1h * math.sqrt(max(tte_rem, 10.0) / 3600.0) + basis_floor)

    z_t5 = eff_cush / max(sig_eff, 1e-6)
    p_win_t5 = compute_unit_variance_student_t_cdf(z_t5, df=df_t)
    fee_ps = exit_fee_rate * ((best_b * (1.0 - best_b)) ** fee_exp) if (exit_fee_rate > 0.0 and 0.0 < best_b < 1.0) else 0.0
    v_salvage_net = max(0.0, best_b - fee_ps)

    ev_margin = float(sup_cfg.get("ev_salvage_margin", 0.04))
    max_drop = float(sup_cfg.get("max_salvage_bid_drop_from_entry", 0.24))
    t_min = float(sup_cfg.get("terminal_window_min_tte_sec", 16.0))
    t_term = float(sup_cfg.get("terminal_window_max_tte_sec", 105.0))
    t_mid = float(sup_cfg.get("mid_window_max_tte_sec", 180.0))
    min_bid = 0.08 if is_live_auth else 0.06

    salv_vol_mult = 1.0 if pos_asset == "BTC" else min(1.8, max(1.0, sigma_1h / 0.0050))
    bid_collapsed = best_b <= max(0.36, entry_px - max_drop) + 1e-6

    qualifies_arm = False
    qualifies_sustain = False
    req_duration = 999.0

    if t_min <= tte_rem <= t_term:
        # Terminal window (includes 15m 60s-TWAP lock): catches -0.5 to -5.0 bps reversals BEFORE T-40s $0.00 liquidity crisis!
        ev_positive = (v_salvage_net >= p_win_t5 + ev_margin) or (best_b <= 0.38 and p_win_t5 <= 0.28)
        qualifies_arm = (eff_cush <= -0.00005) and bid_collapsed and ev_positive
        qualifies_sustain = (eff_cush < 0.0) and bid_collapsed and (v_salvage_net >= p_win_t5 + 0.02 or best_b <= 0.38)
        req_duration = float(sup_cfg.get("terminal_hold_confirm_sec", 3.0))
    elif t_term < tte_rem <= t_mid:
        req_cush = 0.0006 * salv_vol_mult
        sustain_cush = 0.0004 * salv_vol_mult
        ev_positive = (v_salvage_net >= p_win_t5 + ev_margin) or (best_b <= 0.35 and p_win_t5 <= 0.38)
        qualifies_arm = (eff_cush <= -req_cush) and bid_collapsed and ev_positive
        qualifies_sustain = (eff_cush <= -sustain_cush) and bid_collapsed and (ev_positive or best_b <= 0.36)
        base_mid_dur = float(sup_cfg.get("mid_hold_confirm_sec", 8.0))
        if tte_rem <= 150.0 and wrong_side_pct >= 0.05 and best_b <= (entry_px - 0.22):
            req_duration = min(base_mid_dur, 3.0)
        elif v_spot_15s_pct <= -0.08 and best_b <= 0.42:
            req_duration = base_mid_dur * 0.50
        else:
            req_duration = base_mid_dur
        min_bid = 0.12 if is_live_auth else 0.08
    elif tte_rem > t_mid:
        # Early/mid candle: strictly protect rebounding mid-candle dips; only salvage confirmed structural crashes
        cat_cush = float(sup_cfg.get("early_catastrophic_cushion_frac", 0.0018)) * (1.0 if tte_rem <= 900.0 else 1.15)
        sustain_cat = 0.80 * cat_cush
        qualifies_arm = (eff_cush <= -cat_cush) and (best_b <= min(0.42, entry_px - max_drop) + 1e-6) and (p_win_t5 <= 0.38)
        qualifies_sustain = (eff_cush <= -sustain_cat) and (best_b <= min(0.44, entry_px - 0.20) + 1e-6)
        base_early_dur = 40.0 if tte_rem > 900.0 else float(sup_cfg.get("early_hold_confirm_sec", 18.0))
        req_duration = (base_early_dur * 0.50) if (v_spot_15s_pct <= -0.08 and best_b <= 0.42) else base_early_dur
        min_bid = 0.12 if is_live_auth else 0.08

    diag = {
        "p_win_t5": round(p_win_t5, 4),
        "v_salvage_net": round(v_salvage_net, 4),
        "z_t5": round(z_t5, 3),
        "req_duration": round(req_duration, 2),
    }

    consec_start = pos.get("opposite_breakout_start_ts")
    if consec_start is None:
        if qualifies_arm:
            pos["opposite_breakout_start_ts"] = now_ts
        return False, wrong_side_pct, diag

    if not qualifies_sustain:
        pos.pop("opposite_breakout_start_ts", None)
        return False, wrong_side_pct, diag

    rebound_guard = float(sup_cfg.get("anti_wick_rebound_vel_pct", 0.03))
    if v_spot_15s_pct >= rebound_guard:
        return False, wrong_side_pct, diag

    elapsed = now_ts - float(consec_start)
    if elapsed >= req_duration and best_b >= min_bid:
        return True, wrong_side_pct, diag
    return False, wrong_side_pct, diag


_CASHFLOW_WD_CACHE: Dict[str, Any] = {"mtime_ns": -1, "val": 0.0, "checked_ts": 0.0}


def _cached_post_lock_net_withdrawals_usd() -> float:
    now_t = time.time()
    if (now_t - float(_CASHFLOW_WD_CACHE.get("checked_ts") or 0.0)) < 5.0:
        return float(_CASHFLOW_WD_CACHE.get("val") or 0.0)
    _CASHFLOW_WD_CACHE["checked_ts"] = now_t
    try:
        from src.polymarket_research.economic_attribution_ledger import (
            external_cashflows_config_path,
            load_external_cashflows_summary,
        )
        p = external_cashflows_config_path()
        mt = p.stat().st_mtime_ns if p.exists() else 0
        if mt != _CASHFLOW_WD_CACHE.get("mtime_ns"):
            s = load_external_cashflows_summary()
            _CASHFLOW_WD_CACHE["val"] = max(0.0, -float(s.get("net_deposits_post_lock_usd") or 0.0))
            _CASHFLOW_WD_CACHE["mtime_ns"] = mt
    except Exception:
        pass
    return float(_CASHFLOW_WD_CACHE.get("val") or 0.0)


def get_unleashed_v5_tier_profile(
    total_equity: float,
    high_water_mark_equity: Optional[float] = None,
    previous_tier: Optional[str] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    v5.1 Unleashed Full-Throttle Bankroll & Capital-Velocity Schedule (`E[Delta log W / day]` Half-Kelly optimal):
      - `UNLEASHED_LAUNCH` (`$45 <= W < $100`, `+$3` hysteresis): `20.0%` stop-risk / `35.0%` notional (`$24.17` BTC 1h,
        `$20.54` SOL 1h @ `0.85x` on `$69.06`), `2` directional slots (`15m<=0.72` Maker open at `0` pos so Slot #2 stays
        reserved for `1h`), `30%` daily directional loss (`~$20.72`), `85%` D1 / `75%` BOND1 free-cash velocity (`<=12h & >=15 bps/hr`).
      - `HYPER_GROWTH` (`$100 <= W < $250`): `18.5%` stop-risk / `32.0%` notional, `3` directional slots, `26%` daily loss,
        `85%` free-cash arb (`<=24h & >=10 bps/hr`).
      - `SCALE` (`$250 <= W < $1,000`): `15.0%` stop-risk / `26.0%` notional, `4` directional slots, `22%` daily loss,
        `88%` free-cash arb (`<=72h & >=6 bps/hr`).
      - `INSTITUTIONAL` (`W >= $1,000`): `12.0%` stop-risk / `20.0%` notional (`$250` L2 cap), `4` directional slots,
        `18%` daily loss, `90%` free-cash arb (`<=168h & >=3.5 bps/hr`).
    """
    snap = cfg or GLOBAL_GOVERNANCE_MANAGER.snapshot
    s_cfg = snap.get("sizing_tiers", DEFAULT_HOLISTIC_CONFIG["sizing_tiers"])
    r_cfg = snap.get("risk_controller", DEFAULT_HOLISTIC_CONFIG["risk_controller"])
    b_cfg = snap.get("riskless_boxes", DEFAULT_HOLISTIC_CONFIG["riskless_boxes"])

    eq = float(total_equity) if (total_equity is not None and math.isfinite(float(total_equity))) else 0.0
    _net_wd = float(snap.get("_net_withdrawals_post_lock_usd", 0.0) or 0.0)
    if _net_wd <= 0.0 and cfg is None:
        _net_wd = _cached_post_lock_net_withdrawals_usd()
    hwm = (
        max(0.0, float(high_water_mark_equity) - _net_wd)
        if (high_water_mark_equity is not None and math.isfinite(float(high_water_mark_equity)) and float(high_water_mark_equity) > 0.0)
        else eq
    )
    hwm = max(hwm, eq)
    hyst = float(s_cfg.get("tier_upward_hysteresis_usd", 3.0))

    prev_norm = str(previous_tier or "").strip().upper()
    b1 = float(s_cfg.get("seed_survival_max_equity", 95.0)) + (
        hyst if prev_norm in {"UNLEASHED_LAUNCH", "SEED_SURVIVAL", "SEED"} else 0.0
    )
    b2 = float(s_cfg.get("recovery_max_equity", 250.0)) + (
        hyst if prev_norm in {"HYPER_GROWTH", "RECOVERY"} else 0.0
    )
    b3 = float(s_cfg.get("growth_max_equity", 1000.0)) + (
        hyst if prev_norm in {"SCALE", "GROWTH"} else 0.0
    )
    hard_floor = max(5.0, round(float(r_cfg.get("hard_ruin_floor_usd", 42.0)) - _net_wd, 2))

    bond1_mkt_pct = float(b_cfg.get("bond1_per_market_cap_pct", 0.65))
    bond1_mkr_mkt_pct = float(b_cfg.get("bond1_maker_per_market_cap_pct", 0.365))
    if eq < b1:
        tier_name = "UNLEASHED_LAUNCH"
        alpha_notional = float(s_cfg.get("notional_cap_seed", 0.22))
        alpha_stop_risk = float(s_cfg.get("max_stop_equity_risk_seed", 0.135))
        kelly_lambda = float(s_cfg.get("kelly_fraction_seed", 0.36))
        dir_slots = int(s_cfg.get("dir_slots_seed", 4))
        daily_loss_pct = float(s_cfg.get("daily_loss_pct_seed", 0.24))
        port_exp_pct = float(s_cfg.get("portfolio_exposure_pct_seed", 0.96))
        d1_cash_pct = float(b_cfg.get("d1_free_cash_pct_seed", 0.90))
        bond1_cash_pct = float(b_cfg.get("bond1_free_cash_pct_seed", 0.78))
        bond1_mkt_cap = min(float(b_cfg.get("bond1_per_market_cap_usd_seed", 45.0)), round(eq * bond1_mkt_pct, 2))
        bridged_zf_cap = float(b_cfg.get("bridged_zero_fee_cap_usd_seed", 60.0))
        max_lockup_h = float(b_cfg.get("seed_max_lockup_hours", 24.0))
        min_bps_hr = float(b_cfg.get("seed_min_bps_per_hour", 7.5))
        min_floor = hard_floor
    elif eq < b2:
        tier_name = "HYPER_GROWTH"
        alpha_notional = float(s_cfg.get("notional_cap_recovery", 0.26))
        alpha_stop_risk = float(s_cfg.get("max_stop_equity_risk_recovery", 0.155))
        kelly_lambda = float(s_cfg.get("kelly_fraction_recovery", 0.40))
        dir_slots = int(s_cfg.get("dir_slots_recovery", 4))
        daily_loss_pct = float(s_cfg.get("daily_loss_pct_recovery", 0.22))
        port_exp_pct = float(s_cfg.get("portfolio_exposure_pct_recovery", 0.96))
        d1_cash_pct = float(b_cfg.get("d1_free_cash_pct_recovery", 0.90))
        bond1_cash_pct = float(b_cfg.get("bond1_free_cash_pct_seed", 0.78))
        bond1_mkt_cap = min(float(b_cfg.get("bond1_per_market_cap_usd_recovery", 85.0)), round(eq * bond1_mkt_pct, 2))
        bridged_zf_cap = max(float(b_cfg.get("bridged_zero_fee_cap_usd_seed", 60.0)), round(eq * 0.40, 2))
        max_lockup_h = float(b_cfg.get("recovery_max_lockup_hours", 48.0))
        min_bps_hr = float(b_cfg.get("recovery_min_bps_per_hour", 5.0))
        min_floor = round(max(hard_floor, min(68.0, hwm * 0.58)), 2)
    elif eq < b3:
        tier_name = "SCALE"
        alpha_notional = float(s_cfg.get("notional_cap_growth", 0.22))
        alpha_stop_risk = float(s_cfg.get("max_stop_equity_risk_growth", 0.13))
        kelly_lambda = float(s_cfg.get("kelly_fraction_growth", 0.36))
        dir_slots = int(s_cfg.get("dir_slots_growth", 4))
        daily_loss_pct = float(s_cfg.get("daily_loss_pct_growth", 0.20))
        port_exp_pct = float(s_cfg.get("portfolio_exposure_pct_growth", 0.96))
        d1_cash_pct = float(b_cfg.get("d1_free_cash_pct_growth", 0.90))
        bond1_cash_pct = float(b_cfg.get("bond1_free_cash_pct_growth", 0.88))
        bond1_mkt_cap = min(120.0, round(eq * 0.35, 2))
        bridged_zf_cap = float(b_cfg.get("bridged_zero_fee_cap_usd_growth", 120.0))
        max_lockup_h = float(b_cfg.get("growth_max_lockup_hours", 72.0))
        min_bps_hr = float(b_cfg.get("growth_min_bps_per_hour", 6.0))
        min_floor = round(max(75.0, hwm * 0.64), 2)
    else:
        tier_name = "INSTITUTIONAL"
        alpha_notional = float(s_cfg.get("notional_cap_scale", 0.16))
        alpha_stop_risk = float(s_cfg.get("max_stop_equity_risk_scale", 0.10))
        kelly_lambda = float(s_cfg.get("kelly_fraction_scale", 0.30))
        dir_slots = int(s_cfg.get("dir_slots_scale", 4))
        daily_loss_pct = float(s_cfg.get("daily_loss_pct_scale", 0.16))
        port_exp_pct = float(s_cfg.get("portfolio_exposure_pct_scale", 0.96))
        d1_cash_pct = float(b_cfg.get("d1_free_cash_pct_scale", 0.90))
        bond1_cash_pct = float(b_cfg.get("bond1_free_cash_pct_growth", 0.88))
        bond1_mkt_cap = 250.0
        bridged_zf_cap = 150.0
        max_lockup_h = float(b_cfg.get("scale_max_lockup_hours", 168.0))
        min_bps_hr = float(b_cfg.get("scale_min_bps_per_hour", 3.5))
        min_floor = round(max(200.0, hwm * 0.68), 2)

    base_daily = float(r_cfg.get("max_daily_directional_loss_usd", 16.57))
    max_daily_loss = round(max(base_daily, eq * daily_loss_pct), 2)
    max_exposure = round(min(900.0, max(65.0, eq * port_exp_pct)), 2)

    return {
        "unleash_full_throttle": bool(s_cfg.get("unleash_full_throttle", True)),
        "tier": tier_name,
        "dynamic_bankroll_pct": alpha_notional,
        "alpha_notional": alpha_notional,
        "alpha_stop_risk": alpha_stop_risk,
        "kelly_lambda": kelly_lambda,
        "max_concurrent_positions": dir_slots,
        "max_directional_slots": dir_slots,
        "max_slots": dir_slots,
        "max_exposure": max_exposure,
        "portfolio_exposure_pct": port_exp_pct,
        "max_daily_loss": max_daily_loss,
        "max_consecutive_losses": int(r_cfg.get("max_consecutive_directional_losses", 4)),
        "min_equity_floor": min_floor,
        "d1_free_cash_pct": d1_cash_pct,
        "bond1_free_cash_pct": bond1_cash_pct,
        "bond1_per_market_cap_usd": bond1_mkt_cap,
        "bond1_maker_per_market_cap_usd": min(bond1_mkt_cap, round(eq * bond1_mkr_mkt_pct, 2)),
        "bridged_zero_fee_cap_usd": bridged_zf_cap,
        "box_collateral_reserve_usd": float(b_cfg.get("box_collateral_reserve_usd", 0.0)),
        "max_concurrent_riskless_boxes": int(b_cfg.get("max_concurrent_riskless_boxes", 10)),
        "max_lockup_hours": max_lockup_h,
        "min_bps_per_hour": min_bps_hr,
        "subordinate_15m_maker_size_mult": float(s_cfg.get("subordinate_15m_maker_size_mult", 0.80)),
        "salvage_stop_floor_px": float(s_cfg.get("salvage_stop_floor_px", 0.34)),
    }


def passes_capital_velocity_hurdle(
    *,
    box_type: str,
    sleeve_src: str = "",
    collat_usd: float,
    rem_tte_sec: float,
    box_cost_net: float,
    fast_recycle_eligible: bool = False,
    merge_wallet_ok: bool = False,
    previous_tier: Optional[str] = None,
    cfg: Optional[Dict[str, Any]] = None,
    use_dynamic_opportunity_cost: bool = False,
    utilization_frac: float = 0.0,
    competing_top_bps_per_hr: float = 0.0,
) -> Tuple[bool, str]:
    """
    Bankroll-tiered Capital-Velocity Hurdle for riskless structural sleeves.
    Fixes the legacy `and` bug (where 185 bps over 72h bypassed `min_floor_bps_per_hour`) by enforcing
    BOTH maximum lockup hours AND minimum annualized/hourly net edge (`OR` rejection).
    Exempts `COMPLETE_SET` / `C1_BINARY_COMPLETE_SET` ONLY when `merge_wallet_ok=True` is verified so
    unmergeable long-dated complete sets never lock seed cash past `max_lockup_hours`.
    When `use_dynamic_opportunity_cost=True` (v6.0 `R-09`/`R-43`), replaces both the unconditional
    `DOMINANCE` infinite-maturity exemption AND rigid `24h` maturity cliffs with smooth endogenous
    capital opportunity-cost pricing `lambda_cap(utilization, competing_top_bps_per_hr)`.
    """
    btype_u = str(box_type or "").upper()
    _sl_vel_u = str(sleeve_src or "").strip().upper()
    _c1_merge_ready = bool(merge_wallet_ok) and (
        btype_u in {"COMPLETE_SET", "C1_BINARY_COMPLETE_SET"} or _sl_vel_u == "C1_BINARY_COMPLETE_SET"
    )
    if use_dynamic_opportunity_cost:
        if (
            btype_u in {"NEGRISK_CONVERT", "CTF_OVERROUND"}
            or _c1_merge_ready
            or (btype_u == "SINGLE_LEG_LOCK" and float(rem_tte_sec) <= 60.0)
        ):
            return True, "OK"
        raw_hrs_dyn = max(0.05, float(rem_tte_sec) / 3600.0)
        eff_hrs_dyn = min(raw_hrs_dyn, 2.0) if fast_recycle_eligible else raw_hrs_dyn
        floor_bps_dyn = max(0.0, (1.0 - float(box_cost_net)) * 10000.0)
        floor_bps_hr_dyn = floor_bps_dyn / max(0.05, eff_hrs_dyn)
        u_clamped = min(1.0, max(0.0, float(utilization_frac)))
        lam_bps_hr = max(0.50 + 17.50 * (u_clamped ** 2), 0.50 * max(0.0, float(competing_top_bps_per_hr)) * u_clamped)
        if floor_bps_hr_dyn < lam_bps_hr - 1e-6:
            return False, f"BELOW_DYNAMIC_OPPORTUNITY_COST:{floor_bps_hr_dyn:.4f}bps_hr<{lam_bps_hr:.4f}bps_hr"
        return True, "OK"

    if (
        btype_u in {"DOMINANCE", "NEGRISK_CONVERT", "CTF_OVERROUND"}
        or _c1_merge_ready
        or (btype_u == "SINGLE_LEG_LOCK" and float(rem_tte_sec) <= 60.0)
    ):
        return True, "OK"

    prof = get_unleashed_v5_tier_profile(collat_usd, previous_tier=previous_tier, cfg=cfg)
    max_hrs = float(prof["max_lockup_hours"])
    min_bps_hr = float(prof["min_bps_per_hour"])

    raw_hrs = max(0.05, float(rem_tte_sec) / 3600.0)
    _rb_vel = (cfg or GLOBAL_GOVERNANCE_MANAGER.snapshot).get("riskless_boxes", {})
    _uma_2h_cap = (
        2.0
        if (
            _sl_vel_u in {"BOND1_UMA_RESOLUTION_CARRY", "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY", "UMA_READY1_LIVENESS_PRIORITY"}
            and bool(_rb_vel.get("enable_uma_liveness_2h_recycle", True))
        )
        else 4.0
    )
    eff_hrs = min(raw_hrs, _uma_2h_cap) if fast_recycle_eligible else raw_hrs
    floor_bps = max(0.0, (1.0 - float(box_cost_net)) * 10000.0)
    floor_bps_hr = floor_bps / max(0.10, eff_hrs)
    _seed_sports_box = (prof.get("tier") in {"UNLEASHED_LAUNCH", "SEED", "SEED_SURVIVAL"}) and (
        str(box_type or "").upper() in {"SPORTS_CORRIDOR", "NBA_DOMINANCE"}
    )
    ultra_high_yield_intraday = (
        (not _seed_sports_box)
        and (eff_hrs <= 24.0 + 1e-6)
        and (floor_bps_hr >= (2.0 * min_bps_hr) - 1e-6)
    )
    if eff_hrs > max_hrs + 1e-6 and not ultra_high_yield_intraday:
        return False, f"LOW_CAPITAL_VELOCITY_LONG_TTE:{eff_hrs:.2f}h>{max_hrs:.1f}h({floor_bps_hr:.2f}bps_hr)"
    if floor_bps_hr < min_bps_hr - 1e-6:
        return False, f"LOW_CAPITAL_VELOCITY_LONG_TTE:{floor_bps_hr:.2f}bps_hr<{min_bps_hr:.1f}bps_hr"
    return True, "OK"


def compute_stop_risk_fractional_kelly_ticket(
    *,
    live_equity: float,
    p_win: float,
    entry_px: float,
    is_maker: bool = False,
    is_subhourly_15m: bool = False,
    fee_rate: float = 0.07,
    asset: str = "BTC",
    kelly_multiplier: float = 1.0,
    active_positions: Optional[Dict[str, Any]] = None,
    cand_expiry_ts: float = 0.0,
    cand_direction: str = "UP",
    min_lot_usd: float = 8.0,
    max_ticket_cap: float = 200.0,
    cfg: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Computes stop-loss-normalized Fractional Kelly ticket size (`E[Delta log(Wealth)]` Half-Kelly optimal):
      - Accounts for asymmetric binary net win `g_win` vs expected salvage loss `L_stop` (`$0.34` floor).
      - Applies `0.85x` canary size multiplier on `SOL` (`103W/19L = 84.4%` WR in shadow) and `0.80x` on subordinate `15m` Maker.
      - Enforces `0.5405x` (`1 / (1 + 0.85)`) correlation haircut for a 2nd concurrent same-direction position in the same `<= 900s`
        expiry window, and `$0.00` veto on opposite-direction exposure in the same window.
    """
    if not (
        math.isfinite(live_equity)
        and live_equity > 0.0
        and math.isfinite(entry_px)
        and 0.05 <= entry_px <= 0.92
        and math.isfinite(p_win)
        and p_win > 0.0
    ):
        return 0.0
    p_win = min(0.995, max(0.01, float(p_win)))
    snap = cfg or GLOBAL_GOVERNANCE_MANAGER.snapshot
    d_cfg = snap.get("directional", DEFAULT_HOLISTIC_CONFIG["directional"])
    prof = get_unleashed_v5_tier_profile(live_equity, cfg=snap)

    fee_in = 0.0 if is_maker else (fee_rate * entry_px * (1.0 - entry_px))
    eff_cost = entry_px + fee_in
    if p_win <= eff_cost:
        return 0.0

    salv_floor = float(prof["salvage_stop_floor_px"])
    g_win = max(0.04, (0.985 - eff_cost) / eff_cost)
    loss_frac_stop = max(0.25, min(0.85, (eff_cost - salv_floor) / eff_cost))

    edge_ev = p_win * g_win - (1.0 - p_win) * loss_frac_stop
    if edge_ev <= 0.0:
        return 0.0
    f_full = edge_ev / max(g_win * loss_frac_stop, 1e-4)

    k_mult = float(prof["kelly_lambda"]) * max(0.80, min(1.20, float(kelly_multiplier)))
    alpha_notional = float(prof["alpha_notional"])
    max_stop_eq_risk = float(prof["alpha_stop_risk"])

    raw_kelly_usd = live_equity * min(alpha_notional, k_mult * f_full)
    stop_capped_usd = (live_equity * max_stop_eq_risk) / loss_frac_stop
    notional_capped_usd = round(live_equity * alpha_notional, 2)
    sized = min(raw_kelly_usd, stop_capped_usd, notional_capped_usd, float(max_ticket_cap))

    if active_positions:
        for p in active_positions.values():
            p_status = str(p.get("status") or "FILLED")
            rem_shrs = float(p.get("remaining_shares") or 0.0)
            if p_status in ("OPEN", "FILLED", "PENDING_CONFIRMATION", "RESTING", "EXIT_RESTING", "POSITION_CONFIRMED", "MATCHED_PENDING_SETTLEMENT") or rem_shrs > 0.0:
                if "BOX" in str(p.get("sleeve") or "").upper() or p.get("is_dominance_box") or p.get("is_single_leg_lock"):
                    continue
                pos_exp = float(p.get("candle_expiry_ts") or 0.0)
                pos_dir = str(p.get("target_token") or "").upper()
                if cand_expiry_ts > 0.0 and pos_exp > 0.0 and abs(pos_exp - cand_expiry_ts) <= 900.0 and pos_dir:
                    if pos_dir == str(cand_direction or "").upper():
                        sized *= round(1.0 / (1.0 + 0.85), 4)
                    else:
                        return 0.0

    if is_subhourly_15m and is_maker:
        sized *= float(prof["subordinate_15m_maker_size_mult"])

    asset_up = str(asset or "").upper()
    if asset_up == "SOL":
        sized *= float(d_cfg.get("sol_canary_size_multiplier", 0.85))
    elif asset_up == "ETH":
        sized *= float(d_cfg.get("eth_canary_size_multiplier", 0.85))

    if sized < min_lot_usd * 0.625:
        return 0.0
    return round(min(float(max_ticket_cap), max(float(min_lot_usd), sized)), 2)
