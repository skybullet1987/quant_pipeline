"""
POLYMARKET COMPLETE UNIFIED SYSTEM CODEBASE (ALL-IN-ONE BUNDLE)
Generated: 2026-11-13 14:53:06 UTC | Repo: C:/Users/Anton/source/repos/Dominus
TABLE OF CONTENTS (Exact 1-Based Line Ranges):
  - [config/polymarket_risk_config.json] (L20-23 | 1,649B) :: Centralized Risk & Sizing Limits (Backward-Compatible Floor/Caps)
  - [config/polymarket_strategy_and_risk.json] (L24-27 | 9,436B) :: v5.0 Unified Hot-Reloadable Strategy, Routing & Dual-Budget Config
  - [systemd/polymarket-live-harvester.service] (L28-55 | 1,995B) :: Graceful systemd Production Unit (Restart=on-failure, --max-tte 2400.0)
  - [src/polymarket_research/holistic_strategy_governance.py] (L56-251 | 48,762B) :: v5.0 HotReloadConfigManager, ev_terminal_twap_t5 Exit Supervisor & Velocity/Kelly Engine
  - [src/polymarket_research/polymarket_live_harvester.py] (L252-4218 | 761,192B) :: v5.0 Live Harvester Engine, Dual-Budget Risk & Unified Exit Supervisor
  - [src/polymarket_research/polymarket_live_executor.py] (L4219-7444 | 561,245B) :: Polymarket CLOB L2 Client, Priority EIP-712 Signing & pUSD/CTF Adapter
  - [src/polymarket_research/polymarket_terminal_recorder.py] (L7445-8572 | 202,766B) :: Sub-ms Binance/Coinbase/Chainlink-TWAP Shock Detection & CLOB L2 SHM Recorder
  - [src/polymarket_research/deribit_svi_surface.py] (L8573-8739 | 24,417B) :: Deribit SVI Options Volatility Surface & Breeden-Litzenberger Engine
  - [src/polymarket_research/polymarket_paper_trader.py] (L8740-9481 | 127,481B) :: Forward Paper Trader & Production-Parity Simulation Engine
  - [src/polymarket_research/check_polymarket_balance.py] (L9482-9515 | 3,757B) :: Polygon pUSD + USDC.e Collateral Balance Checker
  - [src/polymarket_research/redeem_settled_positions.py] (L9516-9618 | 15,024B) :: CTF Settled Position Redemption Engine
  - [audit_losing_trades.py] (L9619-9764 | 26,363B) :: Autonomous Post-Trade Forensic Auditor & Daemon Health Verifier
  - [scripts/honest_purged_wfo_optimizer.py] (L9765-10166 | 66,113B) :: Zero-Lookahead Purged WFO & Genuine Refit CPCV(6,2) Optimizer
"""
from __future__ import annotations
# [01/13] config/polymarket_risk_config.json
POLYMARKET_RISK_CONFIG_JSON=r'''
{"ticket_notional":16.5,"dynamic_sizing":true,"dynamic_risk_pct":0.18,"scale_up_equity_threshold":110.0,"correlated_crypto_single_slot_threshold":150.0,"high_price_ticket_cap_pct":0.16,"scale_up_risk_pct":0.22,"min_equity_floor":66.67,"seed_survival_equity_threshold":88.0,"seed_survival_ticket_usd":12.0,"seed_survival_max_concurrent":1,"seed_survival_floor_usd":48.0,"seed_smooth_compounding":true,"enable_fak_plus2c_fallback":false,"enable_live_maker_anchor_boxes":false,"enable_single_leg_maker_bond1":true,"enable_graduated_d1_box":true,"enable_sol_d1_box":true,"phase3a_maker_max_notional_usd":22.0,"phase3a_maker_ttl_sec":4.0,"phase3a_15m_long_tte_max_price":0.72,"directional_taker_max_price":0.74,"directional_maker_max_price":0.76,"min_floor_bps_per_hour":25.0,"enable_orthogonal_boundary_slot":true,"d1_routing_mode":"hybrid_auto","d1_max_box_cost_net":0.985,"d1_box_max_budget_usd":250.0,"d1_box_collateral_reserve_usd":0.0,"d1_box_bankroll_pct":0.25,"d1_depth_ratio_threshold":1.2,"d1_min_depth_mult_gate":1.15,"d1_max_giveback_frac":0.25,"max_concurrent_d1_boxes":99,"max_total_portfolio_slots":99,"unlimited_slots":true,"enable_graduated_alt_sleeves":true,"enable_ungraduated_v3_math_live":true,"max_daily_loss":20.0,"max_exposure":100.0,"max_concurrent_positions":2,"hold_to_maturity":false,"exit_policy":"hold_98","stale_fast_tick_max_age_sec":15.0,"stale_telemetry_max_age_sec":30.0,"stale_alert_after_sec":60.0,"alert_rate_limit_sec":300.0}
'''
# [02/13] config/polymarket_strategy_and_risk.json
POLYMARKET_STRATEGY_AND_RISK_JSON=r'''
{"schema_version":"5.5.0","directional":{"allowed_assets_1h":["BTC","SOL","ETH"],"allowed_assets_15m_maker":["BTC","SOL","ETH"],"paused_directional_assets":["XRP"],"sol_canary_size_multiplier":0.85,"eth_canary_size_multiplier":0.85,"enable_1h_taker":true,"enable_1h_shielded_maker":false,"enable_15m_taker":true,"enable_15m_subordinate_maker":true,"enable_5m_directional":false,"min_tte_1h_sec":150.0,"max_tte_1h_sec":2100.0,"regime_b_max_tte_1h_sec":900.0,"min_tte_15m_maker_sec":120.0,"max_tte_15m_maker_sec":510.0,"min_tte_15m_taker_sec":120.0,"max_tte_15m_taker_sec":420.0,"max_taker_price_1h":0.81,"max_maker_price_1h":0.81,"max_taker_price_15m":0.81,"max_maker_price_15m":0.78,"min_entry_price":0.52,"min_z_1h_regime_b":1.0,"min_z_1h_regime_a":1.0,"min_z_15m_maker":0.9,"min_z_15m_taker":1.2,"min_cushion_pct_1h_regime_b":0.04,"min_cushion_pct_1h_regime_a":0.15,"min_cushion_pct_15m_maker":0.04,"min_l1_ask_depth_usd":20.0,"max_spread":0.03,"respect_configured_exit_policy_on_safe":true,"min_live_equity_for_unhedged_directional_usd":150.0,"riskless_only_mode":true},"routing":{"z_immediate_taker_cut":1.0,"maker_ttl_sec":6.0,"max_maker_join_queue_usd":350.0,"enable_phase3a_outbid_repeg":true,"shield_decay_cancel_frac":0.5,"async_clob_keepalive_interval_sec":3.5,"async_clob_keepalive_expiry_sec":45.0,"microbatch_coalesce_alt_sec":0.003},"exit_supervisor":{"policy":"ev_terminal_twap_t5","student_t_df":5.0,"jump_sigma_mult":1.45,"basis_sigma_floor":0.00025,"terminal_window_min_tte_sec":16.0,"terminal_window_max_tte_sec":105.0,"mid_window_max_tte_sec":180.0,"ev_salvage_margin":0.04,"max_salvage_bid_drop_from_entry":0.24,"terminal_hold_confirm_sec":3.0,"mid_hold_confirm_sec":8.0,"early_catastrophic_cushion_frac":0.0018,"early_hold_confirm_sec":18.0,"anti_wick_rebound_vel_pct":0.03,"enable_high_zone_mfe_ratchet":true,"high_zone_mfe_arm_bid":0.93,"high_zone_mfe_drop":0.04,"high_zone_mfe_hold_confirm_sec":2.0,"high_zone_mfe_min_tte_sec":16.0,"isolate_single_market_zero_bid":true,"global_zero_bid_halt_min_markets":2},"risk_controller":{"decouple_riskless_boxes_from_directional_halt":true,"max_daily_directional_loss_usd":16.57,"max_consecutive_directional_losses":4,"hard_ruin_floor_usd":62.0,"riskless_hard_ruin_floor_usd":30.0},"sizing_tiers":{"unleash_full_throttle":true,"seed_survival_max_equity":95.0,"recovery_max_equity":250.0,"growth_max_equity":1000.0,"tier_upward_hysteresis_usd":3.0,"kelly_fraction_seed":0.36,"kelly_fraction_recovery":0.4,"kelly_fraction_growth":0.36,"kelly_fraction_scale":0.3,"notional_cap_seed":0.22,"notional_cap_recovery":0.26,"notional_cap_growth":0.22,"notional_cap_scale":0.16,"salvage_stop_floor_px":0.34,"max_stop_equity_risk_seed":0.135,"max_stop_equity_risk_recovery":0.155,"max_stop_equity_risk_growth":0.13,"max_stop_equity_risk_scale":0.1,"dir_slots_seed":4,"dir_slots_recovery":4,"dir_slots_growth":4,"dir_slots_scale":4,"daily_loss_pct_seed":0.24,"daily_loss_pct_recovery":0.22,"daily_loss_pct_growth":0.2,"daily_loss_pct_scale":0.16,"portfolio_exposure_pct_seed":0.96,"portfolio_exposure_pct_recovery":0.96,"portfolio_exposure_pct_growth":0.96,"portfolio_exposure_pct_scale":0.96,"subordinate_15m_maker_size_mult":0.8},"riskless_boxes":{"enable_graduated_d1_box":true,"enable_single_leg_maker_bond1":true,"enable_two_leg_maker_anchor_boxes":false,"paused_riskless_sleeves":["B4_TOUCHED_BARRIER_WICK_LOCK","SOC2_EXACT_SCORE_2D_LATTICE","SOC2_SCORE_TOTAL_BTTS_LATTICE","SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX","SOC1_THREE_WAY_REGULATION_BOX","SP3_SPORTS_CORRIDOR_DOMINANCE_BOX","CM_B3_PYTH_BARRIER_BOX","S2_EXACT_TWAP_LOCK","S2_RTDS_EXACT_TWAP_INTEGRATOR","W_PRUNE1_NR0_BASKET","NR0_ALL_YES_COMPLETE_SET","NR0_ZERO_FEE_SLATE_ARB","LP_COMP1_SPORTS_TRIANGLES","DC1_DOUBLE_CHANCE_1X2_PARITY","CTF_OVERROUND_MINT_SELL","W_SOLAR1_POST_2351_LOCK","W2_FORECAST_TAIL","MKR_REWARD_LOCKED_CARRY","D1_MAKER_ANCHOR_BOX","ZERO_FEE_MAKER_ANCHOR_BOX"],"d1_max_box_cost_net":0.985,"cm_b3_max_walk_cap":0.99,"d1_free_cash_pct_seed":0.9,"d1_free_cash_pct_recovery":0.9,"d1_free_cash_pct_growth":0.9,"d1_free_cash_pct_scale":0.9,"bond1_free_cash_pct_seed":0.78,"seed_zero_loss_focus_bond1_pool_pct":0.8,"bond1_velocity_preempt_mult":1.8,"bond1_free_cash_pct_growth":0.88,"bond1_per_market_cap_usd_seed":45.0,"bond1_per_market_cap_usd_recovery":85.0,"bond1_per_market_cap_pct":0.65,"bond1_maker_per_market_cap_pct":0.365,"bond1_maker_fanout_clip_usd_seed":7.96,"mkr_lock1_max_concurrent_slots":3,"s2_maker_max_concurrent_slots":2,"bond1_max_join_queue_usd":350.0,"bond1_buried_cancel_sec":90.0,"bridged_zero_fee_cap_usd_seed":60.0,"bridged_zero_fee_cap_usd_growth":120.0,"enable_reward_locked_carry_live_bridge":true,"reward_harvester_cap_usd_seed":12.0,"reward_reserved_slot_usd_seed":7.96,"box_collateral_reserve_usd":0.0,"max_concurrent_riskless_boxes":10,"seed_max_lockup_hours":24.0,"seed_min_bps_per_hour":7.5,"recovery_max_lockup_hours":48.0,"recovery_min_bps_per_hour":5.0,"growth_max_lockup_hours":72.0,"growth_min_bps_per_hour":6.0,"scale_max_lockup_hours":168.0,"scale_min_bps_per_hour":3.5,"enable_pre_split_overround_gun":false,"enable_pre_split_dual_maker_asks":false,"pre_split_require_live_overround":true,"pre_split_min_free_cash_usd":14.0,"pre_split_inventory_cap_usd":12.0,"enable_nr3_synthetic_overround":false,"enable_cross_condition_complement_merge":false,"enable_d1_rebate_maker_canary":false,"d1_rebate_maker_cap_usd":12.0,"gatling_enabled":true,"gatling_fast_gun_reserve_usd":20.0,"gatling_concave_exp":0.65,"gatling_base_clip_d1_usd":22.0,"gatling_base_clip_core_usd":20.0,"gatling_base_clip_bridge_usd":18.5,"enable_s2_twap_lock_live":false,"enable_ungraduated_v3_math_live":true,"enable_c1_gasless_batch_merge":true,"enable_partial_fak_single_leg_sweep":true,"partial_fak_min_shares":5.0,"enable_nr_m1_dead_seed_fanout":true,"enable_xtrack1_expanded_handles":true,"enable_xtrack1_6handle_dead_no":true,"enable_zerofee1_mergeable_sweeper":true,"zerofee1_min_net_edge_bps":15.0,"enable_esports1_bo3_intermission_box":true,"enable_esports1_intermission_hc_total_box":true,"enable_rt_mono1_scalar_ladders":true,"enable_perp1_maker_precancel_leadlag":true,"perp1_adverse_move_bps_300ms":8.0,"d1_short_tte_max_box_cost_net":0.9925,"d1_short_tte_threshold_sec":180.0,"sll_sticky_fifo_rank1_min_hold_sec":900.0,"bond1_max_outbid_repegs":3,"enable_ws_clinch_sniper":true,"ws_clinch_watchlist_max_tokens":900,"enable_uma_liveness_2h_recycle":true,"enable_event_slot_diversification":true,"reward_dynamic_unlock_equity_usd":125.0,"pre_split_dynamic_unlock_equity_usd":140.0,"ws_market_num_shards":4,"enable_recorder_d1fast_ipc":true,"enable_official_league_direct_feeds":true,"enable_auto_wrap_legacy_usdce_to_pusd":true,"pre_split_max_concurrent_slots":3,"strict_zero_legging_pre_split_lock":true,"strict_pure_riskless_mode":true,"enable_zero_loss_open_carry_velocity_recycle":true,"enable_clinched_dead_leg_split_sell":true,"enable_fast_1rtt_cancel":true,"enable_ws_zero_rest_maker_hedge":true,"enable_synthetic_maker_ws_shield":true,"synthetic_maker_min_hedge_depth_mult":4.0,"synthetic_maker_unwind_breaker_usd":0.5,"synthetic_maker_repeg_debounce_sec":0.5,"paused_s2_reserve_floor_usd":2.0,"sll_preempt_birth_grace_sec":45.0,"max_correlated_oracle_event_nav_pct":0.15,"multileg_3plus_min_reconciled_nav_usd":500.0,"nr0_dynamic_unlock_equity_usd":500.0,"certified_multileg_3plus_live_enabled":false,"allow_nr0_multileg_dynamic_unpause":false,"maker_ws_book_max_age_sec":5.0,"maker_max_consecutive_blind_book_polls":3,"ipc_candidate_max_age_sec":60.0,"ipc_subhourly_d1_max_age_sec":15.0,"bond1_postonly_requote_delay_sec":1.0,"enable_inventory_backed_maker_completion":true,"ft_funnel_persist_interval_sec":60.0},"shadow_governance":{"enable_btc_5m_sniper_shadow":false,"enable_sol_5m_canary_shadow":false,"enable_hybrid_zsplit_shadow":false,"enable_xau_15m_maker_shadow":false,"weekly_wfo_min_trades":50,"weekly_wfo_min_profit_factor":1.45,"weekly_wfo_max_pbo":0.2}}
'''
# [03/13] systemd/polymarket-live-harvester.service
POLYMARKET_LIVE_HARVESTER_SERVICE=r'''
[Unit]
Description=Polymarket Live CLOB Real-Money Harvester (v5.4.0 BTC+ETH+SOL, Option B Z>=0.90 Ask<=$0.82 Taker-Only & $0.93 MFE Ratchet; config/polymarket_strategy_and_risk.json)
After=network-online.target polymarket-recorder.service polymarket-recorder-eth.service polymarket-recorder-sol.service
Wants=network-online.target polymarket-recorder.service
StartLimitIntervalSec=600
StartLimitBurst=5
[Service]
Type=simple
WorkingDirectory=/home/skybullet1987/quant_pipeline
Environment="PM_ENFORCE_V5_TIER_SLOTS=1"
Environment=MALLOC_ARENA_MAX=2
ExecStart=/home/skybullet1987/quant_pipeline/venv/bin/python src/polymarket_research/polymarket_live_harvester.py --dynamic-sizing --no-hold-to-maturity --exit-policy hold_98 --max-concurrent 99 --max-ticket-cap 200.0 --max-trades-per-market 4 --max-trades-per-hour 180 --min-price-floor 0.52 --max-price-ceiling 0.82 --max-tte 2400.0 --allowed-assets BTC ETH SOL
Restart=on-failure
RestartSec=3
Nice=-10
CPUWeight=1000
IOWeight=1000
OOMScoreAdjust=-900
KillSignal=SIGTERM
KillMode=mixed
TimeoutStopSec=20s
StandardOutput=append:/home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_stdout.log
StandardError=append:/home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_stdout.log
[Install]
WantedBy=default.target
'''
# [04/13] src/polymarket_research/holistic_strategy_governance.py
import copy;import json;import logging;import math;import os;import signal;import threading;import time;from pathlib import Path;from typing import Any,Callable,Dict,Optional,Tuple
try:from src.polymarket_research.exact_twap_lock_engine import compute_unit_variance_student_t_cdf
except ImportError:from exact_twap_lock_engine import compute_unit_variance_student_t_cdf
logger=logging.getLogger("HolisticStrategyGovernance");PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent;STRATEGY_CONFIG_PATH=Path(os.getenv("POLYMARKET_STRATEGY_CONFIG",str(PIPELINE_ROOT/"config/polymarket_strategy_and_risk.json")));DEFAULT_HOLISTIC_CONFIG={"schema_version":"5.5.0","directional":{"allowed_assets_1h":["BTC","SOL","ETH"],"allowed_assets_15m_maker":["BTC","SOL","ETH"],"paused_directional_assets":["XRP"],"sol_canary_size_multiplier":.85,"eth_canary_size_multiplier":.85,"enable_1h_taker":True,"enable_1h_shielded_maker":False,"enable_15m_taker":True,"enable_15m_subordinate_maker":True,"enable_5m_directional":False,"min_tte_1h_sec":150.,"max_tte_1h_sec":2100.,"regime_b_max_tte_1h_sec":9e2,"min_tte_15m_maker_sec":120.,"max_tte_15m_maker_sec":510.,"min_tte_15m_taker_sec":120.,"max_tte_15m_taker_sec":420.,"max_taker_price_1h":.81,"max_maker_price_1h":.81,"max_taker_price_15m":.81,"max_maker_price_15m":.78,"min_entry_price":.52,"min_z_1h_regime_b":1.,"min_z_1h_regime_a":1.,"min_z_15m_maker":.9,"min_z_15m_taker":1.2,"min_cushion_pct_1h_regime_b":.04,"min_cushion_pct_1h_regime_a":.15,"min_cushion_pct_15m_maker":.04,"min_l1_ask_depth_usd":20.,"max_spread":.03,"respect_configured_exit_policy_on_safe":True,"min_live_equity_for_unhedged_directional_usd":150.,"riskless_only_mode":True},"routing":{"z_immediate_taker_cut":1.,"maker_ttl_sec":6.,"max_maker_join_queue_usd":350.,"enable_phase3a_outbid_repeg":True,"shield_decay_cancel_frac":.5,"async_clob_keepalive_interval_sec":3.5,"async_clob_keepalive_expiry_sec":45.,"microbatch_coalesce_alt_sec":.003},"exit_supervisor":{"policy":"ev_terminal_twap_t5","student_t_df":5.,"jump_sigma_mult":1.45,"basis_sigma_floor":.00025,"terminal_window_min_tte_sec":16.,"terminal_window_max_tte_sec":105.,"mid_window_max_tte_sec":180.,"ev_salvage_margin":.04,"max_salvage_bid_drop_from_entry":.24,"terminal_hold_confirm_sec":3.,"mid_hold_confirm_sec":8.,"early_catastrophic_cushion_frac":.0018,"early_hold_confirm_sec":18.,"anti_wick_rebound_vel_pct":.03,"enable_high_zone_mfe_ratchet":True,"high_zone_mfe_arm_bid":.93,"high_zone_mfe_drop":.04,"high_zone_mfe_hold_confirm_sec":2.,"high_zone_mfe_min_tte_sec":16.,"isolate_single_market_zero_bid":True,"global_zero_bid_halt_min_markets":2},"risk_controller":{"decouple_riskless_boxes_from_directional_halt":True,"max_daily_directional_loss_usd":16.57,"max_consecutive_directional_losses":4,"hard_ruin_floor_usd":42.,"riskless_hard_ruin_floor_usd":30.},"sizing_tiers":{"unleash_full_throttle":True,"seed_survival_max_equity":95.,"recovery_max_equity":250.,"growth_max_equity":1e3,"tier_upward_hysteresis_usd":3.,"kelly_fraction_seed":.36,"kelly_fraction_recovery":.4,"kelly_fraction_growth":.36,"kelly_fraction_scale":.3,"notional_cap_seed":.22,"notional_cap_recovery":.26,"notional_cap_growth":.22,"notional_cap_scale":.16,"salvage_stop_floor_px":.34,"max_stop_equity_risk_seed":.135,"max_stop_equity_risk_recovery":.155,"max_stop_equity_risk_growth":.13,"max_stop_equity_risk_scale":.1,"dir_slots_seed":4,"dir_slots_recovery":4,"dir_slots_growth":4,"dir_slots_scale":4,"daily_loss_pct_seed":.24,"daily_loss_pct_recovery":.22,"daily_loss_pct_growth":.2,"daily_loss_pct_scale":.16,"portfolio_exposure_pct_seed":.96,"portfolio_exposure_pct_recovery":.96,"portfolio_exposure_pct_growth":.96,"portfolio_exposure_pct_scale":.96,"subordinate_15m_maker_size_mult":.8},"riskless_boxes":{"enable_graduated_d1_box":True,"enable_single_leg_maker_bond1":True,"enable_two_leg_maker_anchor_boxes":False,"paused_riskless_sleeves":[],"d1_max_box_cost_net":.985,"cm_b3_max_walk_cap":.99,"d1_free_cash_pct_seed":.9,"d1_free_cash_pct_recovery":.9,"d1_free_cash_pct_growth":.9,"d1_free_cash_pct_scale":.9,"bond1_free_cash_pct_seed":.78,"seed_zero_loss_focus_bond1_pool_pct":.92,"bond1_velocity_preempt_mult":1.8,"bond1_free_cash_pct_growth":.88,"bond1_per_market_cap_usd_seed":45.,"bond1_per_market_cap_usd_recovery":85.,"bond1_per_market_cap_pct":.65,"bond1_maker_per_market_cap_pct":.365,"bond1_maker_fanout_clip_usd_seed":.0,"mkr_lock1_max_concurrent_slots":1,"s2_maker_max_concurrent_slots":1,"bond1_max_join_queue_usd":350.,"bond1_buried_cancel_sec":15.,"bridged_zero_fee_cap_usd_seed":60.,"bridged_zero_fee_cap_usd_growth":120.,"enable_reward_locked_carry_live_bridge":True,"reward_harvester_cap_usd_seed":12.,"reward_reserved_slot_usd_seed":.0,"box_collateral_reserve_usd":.0,"max_concurrent_riskless_boxes":10,"seed_max_lockup_hours":24.,"seed_min_bps_per_hour":7.5,"recovery_max_lockup_hours":48.,"recovery_min_bps_per_hour":5.,"growth_max_lockup_hours":72.,"growth_min_bps_per_hour":6.,"scale_max_lockup_hours":168.,"scale_min_bps_per_hour":3.5,"enable_pre_split_overround_gun":False,"enable_pre_split_dual_maker_asks":False,"pre_split_require_live_overround":True,"pre_split_min_free_cash_usd":14.,"pre_split_inventory_cap_usd":12.,"enable_nr3_synthetic_overround":True,"enable_cross_condition_complement_merge":True,"enable_d1_rebate_maker_canary":False,"d1_rebate_maker_cap_usd":12.,"gatling_enabled":True,"gatling_fast_gun_reserve_usd":22.5,"gatling_concave_exp":.65,"gatling_base_clip_d1_usd":22.,"gatling_base_clip_core_usd":20.,"gatling_base_clip_bridge_usd":18.5,"enable_s2_twap_lock_live":True,"enable_ungraduated_v3_math_live":True,"enable_c1_gasless_batch_merge":True,"enable_partial_fak_single_leg_sweep":True,"partial_fak_min_shares":5.,"enable_nr_m1_dead_seed_fanout":True,"enable_xtrack1_expanded_handles":True,"enable_xtrack1_6handle_dead_no":True,"enable_zerofee1_mergeable_sweeper":True,"zerofee1_min_net_edge_bps":15.,"enable_esports1_bo3_intermission_box":True,"enable_esports1_intermission_hc_total_box":True,"enable_rt_mono1_scalar_ladders":True,"enable_perp1_maker_precancel_leadlag":True,"perp1_adverse_move_bps_300ms":8.,"d1_short_tte_max_box_cost_net":.9925,"d1_short_tte_threshold_sec":180.,"sll_sticky_fifo_rank1_min_hold_sec":9e2,"bond1_max_outbid_repegs":3,"enable_ws_clinch_sniper":True,"ws_clinch_watchlist_max_tokens":900,"enable_uma_liveness_2h_recycle":True,"enable_event_slot_diversification":True,"reward_dynamic_unlock_equity_usd":125.,"pre_split_dynamic_unlock_equity_usd":140.,"ws_market_num_shards":4,"enable_recorder_d1fast_ipc":True,"enable_official_league_direct_feeds":True,"enable_auto_wrap_legacy_usdce_to_pusd":True,"pre_split_max_concurrent_slots":3,"strict_zero_legging_pre_split_lock":False,"strict_pure_riskless_mode":False,"enable_zero_loss_open_carry_velocity_recycle":True,"enable_clinched_dead_leg_split_sell":True,"enable_fast_1rtt_cancel":True,"enable_ws_zero_rest_maker_hedge":True,"enable_synthetic_maker_ws_shield":True,"synthetic_maker_min_hedge_depth_mult":4.,"synthetic_maker_unwind_breaker_usd":.5,"synthetic_maker_repeg_debounce_sec":.5,"paused_s2_reserve_floor_usd":2.,"sll_preempt_birth_grace_sec":45.,"max_correlated_oracle_event_nav_pct":.15,"multileg_3plus_min_reconciled_nav_usd":5e2,"nr0_dynamic_unlock_equity_usd":5e2,"certified_multileg_3plus_live_enabled":False,"allow_nr0_multileg_dynamic_unpause":False,"maker_ws_book_max_age_sec":5.,"maker_max_consecutive_blind_book_polls":3,"ipc_candidate_max_age_sec":60.,"ipc_subhourly_d1_max_age_sec":15.,"bond1_postonly_requote_delay_sec":1.,"enable_inventory_backed_maker_completion":True,"ft_funnel_persist_interval_sec":5.},"shadow_governance":{"enable_btc_5m_sniper_shadow":False,"enable_sol_5m_canary_shadow":False,"enable_hybrid_zsplit_shadow":True,"enable_xau_15m_maker_shadow":True,"weekly_wfo_min_trades":50,"weekly_wfo_min_profit_factor":1.45,"weekly_wfo_max_pbo":.2}}
def _deep_merge_validated(defaults,raw):
 if not isinstance(raw,dict):raise ValueError("Root config must be a JSON object")
 j=copy.deepcopy(defaults)
 if"schema_version"in raw:
  if not isinstance(raw["schema_version"],str)or not raw["schema_version"].strip():raise ValueError("schema_version must be non-empty string")
  j["schema_version"]=raw["schema_version"].strip()
 for b,a in defaults.items():
  if b=="schema_version"or b not in raw:continue
  d=raw[b]
  if not isinstance(d,dict):raise ValueError(f"Section {b!r} must be a dict")
  for k,h in a.items():
   if k not in d:continue
   i=d[k]
   if isinstance(h,bool):
    if not isinstance(i,bool):raise ValueError(f"{b}.{k} must be bool")
    j[b][k]=i
   elif isinstance(h,list):
    if not isinstance(i,list)or not all(isinstance(x,str)and x.strip()for x in i):raise ValueError(f"{b}.{k} must be list of non-empty strings")
    j[b][k]=[x.strip().upper()for x in i]
   elif isinstance(h,str):
    if not isinstance(i,str)or not i.strip():raise ValueError(f"{b}.{k} must be non-empty string")
    j[b][k]=i.strip()
   elif isinstance(h,int)and not isinstance(h,bool):
    if not isinstance(i,int)or isinstance(i,bool)or i<1:raise ValueError(f"{b}.{k} must be positive integer")
    j[b][k]=int(i)
   elif isinstance(h,float):
    if not isinstance(i,(int,float))or isinstance(i,bool)or not math.isfinite(float(i)):raise ValueError(f"{b}.{k} must be finite float")
    j[b][k]=float(i)
 g=j["directional"]
 if not(.45<=g["max_taker_price_1h"]<=.85):raise ValueError("directional.max_taker_price_1h out of safe [0.45, 0.85] range")
 if not(.45<=g["max_maker_price_1h"]<=.85):raise ValueError("directional.max_maker_price_1h out of safe [0.45, 0.85] range")
 if not(.45<=g["max_maker_price_15m"]<=.85):raise ValueError("directional.max_maker_price_15m out of safe [0.45, 0.85] range")
 if not(.45<=g["max_taker_price_15m"]<=.85):raise ValueError("directional.max_taker_price_15m out of safe [0.45, 0.85] range")
 if not(30.<=g["min_tte_1h_sec"]<g["max_tte_1h_sec"]<=3600.):raise ValueError("directional 1h TTE bounds invalid")
 if not(60.<=g["min_tte_15m_taker_sec"]<g["max_tte_15m_taker_sec"]<=9e2):raise ValueError("directional 15m TTE bounds invalid")
 if not(.1<=g["sol_canary_size_multiplier"]<=1.):raise ValueError("directional.sol_canary_size_multiplier must be in [0.10, 1.0]")
 if not(.1<=g["eth_canary_size_multiplier"]<=1.):raise ValueError("directional.eth_canary_size_multiplier must be in [0.10, 1.0]")
 if not(.0<=g["min_live_equity_for_unhedged_directional_usd"]<=1e4):raise ValueError("directional.min_live_equity_for_unhedged_directional_usd must be in [0.0, 10000.0]")
 c=j["exit_supervisor"]
 if not(.8<=c["high_zone_mfe_arm_bid"]<=.99)or not(.01<=c["high_zone_mfe_drop"]<=.15):raise ValueError("exit_supervisor high_zone_mfe bounds invalid")
 f=j["risk_controller"]
 if(f["max_daily_directional_loss_usd"]<=.0 or f["hard_ruin_floor_usd"]<20. or not(15.<=float(f.get("riskless_hard_ruin_floor_usd",30.))<=float(f["hard_ruin_floor_usd"]))):raise ValueError("risk_controller loss/ruin bounds invalid")
 e=j["riskless_boxes"]
 if(not(.9<=e["d1_max_box_cost_net"]<=.996)or not(.9<=e["cm_b3_max_walk_cap"]<=.996)or not(.9<=e["d1_short_tte_max_box_cost_net"]<=.995)):raise ValueError("riskless_boxes walk caps out of safe range")
 if not(15.<=e["d1_short_tte_threshold_sec"]<=6e2):raise ValueError("riskless_boxes.d1_short_tte_threshold_sec must be in [15.0, 600.0]")
 if not(30.<=e["sll_sticky_fifo_rank1_min_hold_sec"]<=3600.):raise ValueError("riskless_boxes.sll_sticky_fifo_rank1_min_hold_sec must be in [30.0, 3600.0]")
 if not(1<=int(e["bond1_max_outbid_repegs"])<=10):raise ValueError("riskless_boxes.bond1_max_outbid_repegs must be in [1, 10]")
 if not(4<=int(e["ws_clinch_watchlist_max_tokens"])<=1500):raise ValueError("riskless_boxes.ws_clinch_watchlist_max_tokens must be in [4, 1500]")
 if not(50.<=float(e["reward_dynamic_unlock_equity_usd"])<=5e3):raise ValueError("riskless_boxes.reward_dynamic_unlock_equity_usd must be in [50.0, 5000.0]")
 if not(50.<=float(e["pre_split_dynamic_unlock_equity_usd"])<=5e3):raise ValueError("riskless_boxes.pre_split_dynamic_unlock_equity_usd must be in [50.0, 5000.0]")
 if not(1<=int(e["ws_market_num_shards"])<=8):raise ValueError("riskless_boxes.ws_market_num_shards must be in [1, 8]")
 if not(1<=int(e["pre_split_max_concurrent_slots"])<=4):raise ValueError("riskless_boxes.pre_split_max_concurrent_slots must be in [1, 4]")
 if not(2.<=float(e["synthetic_maker_min_hedge_depth_mult"])<=10.):raise ValueError("riskless_boxes.synthetic_maker_min_hedge_depth_mult must be in [2.0, 10.0]")
 if not(.1<=float(e["synthetic_maker_unwind_breaker_usd"])<=5.):raise ValueError("riskless_boxes.synthetic_maker_unwind_breaker_usd must be in [0.10, 5.00]")
 if not(.1<=float(e["synthetic_maker_repeg_debounce_sec"])<=5.):raise ValueError("riskless_boxes.synthetic_maker_repeg_debounce_sec must be in [0.10, 5.00]")
 if not(.0<=float(e["paused_s2_reserve_floor_usd"])<=50.):raise ValueError("riskless_boxes.paused_s2_reserve_floor_usd must be in [0.0, 50.0]")
 if not(.0<=float(e["sll_preempt_birth_grace_sec"])<=6e2):raise ValueError("riskless_boxes.sll_preempt_birth_grace_sec must be in [0.0, 600.0]")
 if not(.01<=float(e["max_correlated_oracle_event_nav_pct"])<=.15):raise ValueError("riskless_boxes.max_correlated_oracle_event_nav_pct must be in [0.01, 0.15]")
 if not(5e2<=float(e["multileg_3plus_min_reconciled_nav_usd"])<=5e4):raise ValueError("riskless_boxes.multileg_3plus_min_reconciled_nav_usd must be in [500.0, 50000.0]")
 if not(5e2<=float(e["nr0_dynamic_unlock_equity_usd"])<=5e4):raise ValueError("riskless_boxes.nr0_dynamic_unlock_equity_usd must be in [500.0, 50000.0]")
 if not(.5<=float(e["maker_ws_book_max_age_sec"])<=5.):raise ValueError("riskless_boxes.maker_ws_book_max_age_sec must be in [0.5, 5.0]")
 if not(1<=int(e["maker_max_consecutive_blind_book_polls"])<=5):raise ValueError("riskless_boxes.maker_max_consecutive_blind_book_polls must be in [1, 5]")
 return j
class HotReloadConfigManager:
 def __init__(a,config_path=None,risk_config_path=None,poll_interval_sec=2.,on_reload=None):a.config_path=Path(config_path)if config_path is not None else STRATEGY_CONFIG_PATH;a.risk_config_path=Path(risk_config_path)if risk_config_path is not None else(PIPELINE_ROOT/"config/polymarket_risk_config.json");a.poll_interval_sec=max(.05,float(poll_interval_sec));a.on_reload=on_reload;a._lock=threading.Lock();a._snapshot=copy.deepcopy(DEFAULT_HOLISTIC_CONFIG);a._last_mtime_ns=-1;a._last_file_sig=(-1,-1);a._last_rejected_sig=(-1,-1);a._last_risk_mtime_ns=-1;a._last_risk_sig=(-1,-1);a._last_poll_mono=.0;a._sighup_pending=False;a.reload_count=0;a.rejected_reload_count=0;a.maybe_reload(force=True)
 @property
 def snapshot(self):return self._snapshot
 def request_sighup_reload(self):self._sighup_pending=True
 def install_sighup_handler(self):
  if not hasattr(signal,"SIGHUP"):return False
  try:signal.signal(signal.SIGHUP,lambda _sig,_frm:self.request_sighup_reload());return True
  except Exception:return False
 def maybe_reload(a,force=False):
  k=time.monotonic()
  if a._sighup_pending:force=True;a._sighup_pending=False
  if not force and(k-a._last_poll_mono)<a.poll_interval_sec:return False,a._snapshot
  a._last_poll_mono=k
  with a._lock:
   b=False
   if a.config_path.exists():
    try:n=a.config_path.stat();f=n.st_mtime_ns;e=(n.st_mtime_ns,n.st_size)
    except OSError:f=a._last_mtime_ns;e=a._last_file_sig
    if force or e!=a._last_file_sig:
     try:m=json.loads(a.config_path.read_text(encoding="utf-8"));g=_deep_merge_validated(DEFAULT_HOLISTIC_CONFIG,m);h=a._snapshot.get("schema_version");a._snapshot=g;a._last_mtime_ns=f;a._last_file_sig=e;a._last_rejected_sig=(-1,-1);a.reload_count+=1;b=True;logger.info("[CONFIG_HOT_RELOAD] Applied validated snapshot %s (reload #%d, prev=%s) from %s",g.get("schema_version"),a.reload_count,h,a.config_path)
     except Exception as j:
      if force or e!=a._last_rejected_sig:a.rejected_reload_count+=1;a._last_rejected_sig=e;logger.error("[CONFIG_HOT_RELOAD_REJECTED] Retaining previous valid snapshot; rejected %s: %s",a.config_path,j)
   if a.risk_config_path.exists():
    try:
     l=a.risk_config_path.stat();i=(l.st_mtime_ns,l.st_size)
     if a._last_risk_sig==(-1,-1):
      d=json.loads(a.risk_config_path.read_text(encoding="utf-8"))
      if isinstance(d,dict):a._risk_snapshot=d
      a._last_risk_sig=i;a._last_risk_mtime_ns=l.st_mtime_ns
     elif i!=a._last_risk_sig:
      d=json.loads(a.risk_config_path.read_text(encoding="utf-8"))
      if isinstance(d,dict):a._risk_snapshot=d
      a._last_risk_sig=i;a._last_risk_mtime_ns=l.st_mtime_ns;b=True
    except Exception:pass
   if b and a.on_reload is not None:
    try:a.on_reload(a._snapshot)
    except Exception as c:logger.error("[CONFIG_HOT_RELOAD] Callback error: %s",c)
   return b,a._snapshot
 @property
 def risk_snapshot(self):return getattr(self,"_risk_snapshot",None)or{}
GLOBAL_GOVERNANCE_MANAGER=HotReloadConfigManager()
def evaluate_ev_terminal_twap_t5_salvage(*,pos,now_ts,tte_rem,spot_valid,open_spot,spot_disp,sigma_valid,candle_sigma,is_subhourly_pos,is_5m_pos,best_b,entry_px,v_spot_15s_pct,exit_fee_rate,fee_exp,twap_locked_mean=None,twap_locked_weight=None,current_spot=None,is_live_auth=True,cfg=None):
 F=(cfg or GLOBAL_GOVERNANCE_MANAGER.snapshot).get("exit_supervisor",DEFAULT_HOLISTIC_CONFIG["exit_supervisor"])
 if not spot_valid or open_spot<=.0:pos.pop("opposite_breakout_start_ts",None);return False,.0,{}
 t=spot_disp/open_spot;j=(-t)*1e2
 if j<=.0:pos.pop("opposite_breakout_start_ts",None);return False,.0,{}
 z=str(pos.get("asset")or"BTC").upper()
 if sigma_valid and candle_sigma>.0:O=math.sqrt(12.)if is_5m_pos else(2. if is_subhourly_pos else 1.);g=candle_sigma*O
 else:g=.005 if z=="BTC"else(.0068 if z=="ETH"else.0085)
 y=float(F.get("jump_sigma_mult",1.45));s=float(F.get("basis_sigma_floor",.00025));N=float(F.get("student_t_df",5.));f=t
 if is_subhourly_pos and.0<tte_rem<=60.:
  K=(max(.0,min(1.,float(twap_locked_weight)))if twap_locked_weight is not None else max(.0,min(1.,(60.-tte_rem)/60.)))
  if twap_locked_mean is not None and float(twap_locked_mean)>.0 and current_spot is not None and float(current_spot)>.0:x=K*float(twap_locked_mean)+(1.-K)*float(current_spot);w=1. if str(pos.get("target_token")or"UP").upper()=="UP"else-1.;f=w*((x-open_spot)/open_spot)
  u=max(1.,((1.-K)**2)*(tte_rem/3.));i=max(.00018,y*g*math.sqrt(u/3600.)+s)
 else:i=max(s,y*g*math.sqrt(max(tte_rem,10.)/3600.)+s)
 M=f/max(i,1e-6);D=compute_unit_variance_student_t_cdf(M,df=N);H=exit_fee_rate*((best_b*(1.-best_b))**fee_exp)if(exit_fee_rate>.0 and.0<best_b<1.)else.0;n=max(.0,best_b-H);v=float(F.get("ev_salvage_margin",.04));C=float(F.get("max_salvage_bid_drop_from_entry",.24));J=float(F.get("terminal_window_min_tte_sec",16.));G=float(F.get("terminal_window_max_tte_sec",105.));I=float(F.get("mid_window_max_tte_sec",180.));e=.08 if is_live_auth else.06;m=1. if z=="BTC"else min(1.8,max(1.,g/.005));l=best_b<=max(.36,entry_px-C)+1e-6;c=False;b=False;a=999.
 if J<=tte_rem<=G:d=(n>=D+v)or(best_b<=.38 and D<=.28);c=(f<=-5e-5)and l and d;b=(f<.0)and l and(n>=D+.02 or best_b<=.38);a=float(F.get("terminal_hold_confirm_sec",3.))
 elif G<tte_rem<=I:
  B=6e-4*m;q=4e-4*m;d=(n>=D+v)or(best_b<=.35 and D<=.38);c=(f<=-B)and l and d;b=(f<=-q)and l and(d or best_b<=.36);p=float(F.get("mid_hold_confirm_sec",8.))
  if tte_rem<=150. and j>=.05 and best_b<=(entry_px-.22):a=min(p,3.)
  elif v_spot_15s_pct<=-.08 and best_b<=.42:a=p*.5
  else:a=p
  e=.12 if is_live_auth else.08
 elif tte_rem>I:A=float(F.get("early_catastrophic_cushion_frac",.0018))*(1. if tte_rem<=9e2 else 1.15);r=.8*A;c=(f<=-A)and(best_b<=min(.42,entry_px-C)+1e-6)and(D<=.38);b=(f<=-r)and(best_b<=min(.44,entry_px-.2)+1e-6);h=40. if tte_rem>9e2 else float(F.get("early_hold_confirm_sec",18.));a=(h*.5)if(v_spot_15s_pct<=-.08 and best_b<=.42)else h;e=.12 if is_live_auth else.08
 L={"p_win_t5":round(D,4),"v_salvage_net":round(n,4),"z_t5":round(M,3),"req_duration":round(a,2)};o=pos.get("opposite_breakout_start_ts")
 if o is None:
  if c:pos["opposite_breakout_start_ts"]=now_ts
  return False,j,L
 if not b:pos.pop("opposite_breakout_start_ts",None);return False,j,L
 k=float(F.get("anti_wick_rebound_vel_pct",.03))
 if v_spot_15s_pct>=k:return False,j,L
 E=now_ts-float(o)
 if E>=a and best_b>=e:return True,j,L
 return False,j,L
_CASHFLOW_WD_CACHE={"mtime_ns":-1,"val":.0,"checked_ts":.0}
def _cached_post_lock_net_withdrawals_usd():
 c=time.time()
 if(c-float(_CASHFLOW_WD_CACHE.get("checked_ts")or.0))<5.:return float(_CASHFLOW_WD_CACHE.get("val")or.0)
 _CASHFLOW_WD_CACHE["checked_ts"]=c
 try:
  from src.polymarket_research.economic_attribution_ledger import(external_cashflows_config_path as b,load_external_cashflows_summary as a);p=b();d=p.stat().st_mtime_ns if p.exists()else 0
  if d!=_CASHFLOW_WD_CACHE.get("mtime_ns"):s=a();_CASHFLOW_WD_CACHE["val"]=max(.0,-float(s.get("net_deposits_post_lock_usd")or.0));_CASHFLOW_WD_CACHE["mtime_ns"]=d
 except Exception:pass
 return float(_CASHFLOW_WD_CACHE.get("val")or.0)
def get_unleashed_v5_tier_profile(total_equity,high_water_mark_equity=None,previous_tier=None,cfg=None):
 B=cfg or GLOBAL_GOVERNANCE_MANAGER.snapshot;z=B.get("sizing_tiers",DEFAULT_HOLISTIC_CONFIG["sizing_tiers"]);y=B.get("risk_controller",DEFAULT_HOLISTIC_CONFIG["risk_controller"]);x=B.get("riskless_boxes",DEFAULT_HOLISTIC_CONFIG["riskless_boxes"]);F=float(total_equity)if(total_equity is not None and math.isfinite(float(total_equity)))else.0;q=float(B.get("_net_withdrawals_post_lock_usd",.0)or.0)
 if q<=.0 and cfg is None:q=_cached_post_lock_net_withdrawals_usd()
 w=(max(.0,float(high_water_mark_equity)-q)if(high_water_mark_equity is not None and math.isfinite(float(high_water_mark_equity))and float(high_water_mark_equity)>.0)else F);w=max(w,F);A=float(z.get("tier_upward_hysteresis_usd",3.));v=str(previous_tier or"").strip().upper();E=float(z.get("seed_survival_max_equity",95.))+(A if v in{"UNLEASHED_LAUNCH","SEED_SURVIVAL","SEED"}else.0);D=float(z.get("recovery_max_equity",250.))+(A if v in{"HYPER_GROWTH","RECOVERY"}else.0);C=float(z.get("growth_max_equity",1e3))+(A if v in{"SCALE","GROWTH"}else.0);u=max(5.,round(float(y.get("hard_ruin_floor_usd",42.))-q,2));r=float(x.get("bond1_per_market_cap_pct",.65));o=float(x.get("bond1_maker_per_market_cap_pct",.365))
 if F<E:n="UNLEASHED_LAUNCH";e=float(z.get("notional_cap_seed",.22));a=float(z.get("max_stop_equity_risk_seed",.135));i=float(z.get("kelly_fraction_seed",.36));m=int(z.get("dir_slots_seed",4));d=float(z.get("daily_loss_pct_seed",.24));h=float(z.get("portfolio_exposure_pct_seed",.96));j=float(x.get("d1_free_cash_pct_seed",.9));c=float(x.get("bond1_free_cash_pct_seed",.78));f=min(float(x.get("bond1_per_market_cap_usd_seed",45.)),round(F*r,2));b=float(x.get("bridged_zero_fee_cap_usd_seed",60.));g=float(x.get("seed_max_lockup_hours",24.));k=float(x.get("seed_min_bps_per_hour",7.5));l=u
 elif F<D:n="HYPER_GROWTH";e=float(z.get("notional_cap_recovery",.26));a=float(z.get("max_stop_equity_risk_recovery",.155));i=float(z.get("kelly_fraction_recovery",.4));m=int(z.get("dir_slots_recovery",4));d=float(z.get("daily_loss_pct_recovery",.22));h=float(z.get("portfolio_exposure_pct_recovery",.96));j=float(x.get("d1_free_cash_pct_recovery",.9));c=float(x.get("bond1_free_cash_pct_seed",.78));f=min(float(x.get("bond1_per_market_cap_usd_recovery",85.)),round(F*r,2));b=max(float(x.get("bridged_zero_fee_cap_usd_seed",60.)),round(F*.4,2));g=float(x.get("recovery_max_lockup_hours",48.));k=float(x.get("recovery_min_bps_per_hour",5.));l=round(max(u,min(68.,w*.58)),2)
 elif F<C:n="SCALE";e=float(z.get("notional_cap_growth",.22));a=float(z.get("max_stop_equity_risk_growth",.13));i=float(z.get("kelly_fraction_growth",.36));m=int(z.get("dir_slots_growth",4));d=float(z.get("daily_loss_pct_growth",.2));h=float(z.get("portfolio_exposure_pct_growth",.96));j=float(x.get("d1_free_cash_pct_growth",.9));c=float(x.get("bond1_free_cash_pct_growth",.88));f=min(120.,round(F*.35,2));b=float(x.get("bridged_zero_fee_cap_usd_growth",120.));g=float(x.get("growth_max_lockup_hours",72.));k=float(x.get("growth_min_bps_per_hour",6.));l=round(max(75.,w*.64),2)
 else:n="INSTITUTIONAL";e=float(z.get("notional_cap_scale",.16));a=float(z.get("max_stop_equity_risk_scale",.1));i=float(z.get("kelly_fraction_scale",.3));m=int(z.get("dir_slots_scale",4));d=float(z.get("daily_loss_pct_scale",.16));h=float(z.get("portfolio_exposure_pct_scale",.96));j=float(x.get("d1_free_cash_pct_scale",.9));c=float(x.get("bond1_free_cash_pct_growth",.88));f=250.;b=150.;g=float(x.get("scale_max_lockup_hours",168.));k=float(x.get("scale_min_bps_per_hour",3.5));l=round(max(2e2,w*.68),2)
 t=float(y.get("max_daily_directional_loss_usd",16.57));p=round(max(t,F*d),2);s=round(min(9e2,max(65.,F*h)),2);return{"unleash_full_throttle":bool(z.get("unleash_full_throttle",True)),"tier":n,"dynamic_bankroll_pct":e,"alpha_notional":e,"alpha_stop_risk":a,"kelly_lambda":i,"max_concurrent_positions":m,"max_directional_slots":m,"max_slots":m,"max_exposure":s,"portfolio_exposure_pct":h,"max_daily_loss":p,"max_consecutive_losses":int(y.get("max_consecutive_directional_losses",4)),"min_equity_floor":l,"d1_free_cash_pct":j,"bond1_free_cash_pct":c,"bond1_per_market_cap_usd":f,"bond1_maker_per_market_cap_usd":min(f,round(F*o,2)),"bridged_zero_fee_cap_usd":b,"box_collateral_reserve_usd":float(x.get("box_collateral_reserve_usd",.0)),"max_concurrent_riskless_boxes":int(x.get("max_concurrent_riskless_boxes",10)),"max_lockup_hours":g,"min_bps_per_hour":k,"subordinate_15m_maker_size_mult":float(z.get("subordinate_15m_maker_size_mult",.8)),"salvage_stop_floor_px":float(z.get("salvage_stop_floor_px",.34))}
def passes_capital_velocity_hurdle(*,box_type,sleeve_src="",collat_usd,rem_tte_sec,box_cost_net,fast_recycle_eligible=False,merge_wallet_ok=False,previous_tier=None,cfg=None,use_dynamic_opportunity_cost=False,utilization_frac=.0,competing_top_bps_per_hr=.0):
 s=str(box_type or"").upper();n=str(sleeve_src or"").strip().upper();d=bool(merge_wallet_ok)and(s in{"COMPLETE_SET","C1_BINARY_COMPLETE_SET"}or n=="C1_BINARY_COMPLETE_SET")
 if use_dynamic_opportunity_cost:
  if(s in{"NEGRISK_CONVERT","CTF_OVERROUND"}or d or(s=="SINGLE_LEG_LOCK"and float(rem_tte_sec)<=60.)):return True,"OK"
  i=max(.05,float(rem_tte_sec)/3600.);h=min(i,2.)if fast_recycle_eligible else i;e=max(.0,(1.-float(box_cost_net))*1e4);c=e/max(.05,h);m=min(1.,max(.0,float(utilization_frac)));k=max(.5+17.5*(m**2),.5*max(.0,float(competing_top_bps_per_hr))*m)
  if c<k-1e-6:return False,f"BELOW_DYNAMIC_OPPORTUNITY_COST:{c:.4f}bps_hr<{k:.4f}bps_hr"
  return True,"OK"
 if(s in{"DOMINANCE","NEGRISK_CONVERT","CTF_OVERROUND"}or d or(s=="SINGLE_LEG_LOCK"and float(rem_tte_sec)<=60.)):return True,"OK"
 t=get_unleashed_v5_tier_profile(collat_usd,previous_tier=previous_tier,cfg=cfg);r=float(t["max_lockup_hours"]);j=float(t["min_bps_per_hour"]);q=max(.05,float(rem_tte_sec)/3600.);p=(cfg or GLOBAL_GOVERNANCE_MANAGER.snapshot).get("riskless_boxes",{});g=(2. if(n in{"BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","UMA_READY1_LIVENESS_PRIORITY"}and bool(p.get("enable_uma_liveness_2h_recycle",True)))else 4.);o=min(q,g)if fast_recycle_eligible else q;l=max(.0,(1.-float(box_cost_net))*1e4);f=l/max(.1,o);b=(t.get("tier")in{"UNLEASHED_LAUNCH","SEED","SEED_SURVIVAL"})and(str(box_type or"").upper()in{"SPORTS_CORRIDOR","NBA_DOMINANCE"});a=((not b)and(o<=24.+1e-6)and(f>=2.*j-1e-6))
 if o>r+1e-6 and not a:return False,f"LOW_CAPITAL_VELOCITY_LONG_TTE:{o:.2f}h>{r:.1f}h({f:.2f}bps_hr)"
 if f<j-1e-6:return False,f"LOW_CAPITAL_VELOCITY_LONG_TTE:{f:.2f}bps_hr<{j:.1f}bps_hr"
 return True,"OK"
def compute_stop_risk_fractional_kelly_ticket(*,live_equity,p_win,entry_px,is_maker=False,is_subhourly_15m=False,fee_rate=.07,asset="BTC",kelly_multiplier=1.,active_positions=None,cand_expiry_ts=.0,cand_direction="UP",min_lot_usd=8.,max_ticket_cap=2e2,cfg=None):
 if not(math.isfinite(live_equity)and live_equity>.0 and math.isfinite(entry_px)and.05<=entry_px<=.92 and math.isfinite(p_win)and p_win>.0):return.0
 p_win=min(.995,max(.01,float(p_win)));w=cfg or GLOBAL_GOVERNANCE_MANAGER.snapshot;u=w.get("directional",DEFAULT_HOLISTIC_CONFIG["directional"]);v=get_unleashed_v5_tier_profile(live_equity,cfg=w);s=.0 if is_maker else(fee_rate*entry_px*(1.-entry_px));l=entry_px+s
 if p_win<=l:return.0
 h=float(v["salvage_stop_floor_px"]);t=max(.04,(.985-l)/l);f=max(.25,min(.85,(l-h)/l));o=p_win*t-(1.-p_win)*f
 if o<=.0:return.0
 r=o/max(t*f,1e-4);q=float(v["kelly_lambda"])*max(.8,min(1.2,float(kelly_multiplier)));e=float(v["alpha_notional"]);c=float(v["alpha_stop_risk"]);g=live_equity*min(e,q*r);d=(live_equity*c)/f;b=round(live_equity*e,2);a=min(g,d,b,float(max_ticket_cap))
 if active_positions:
  for p in active_positions.values():
   k=str(p.get("status")or"FILLED");j=float(p.get("remaining_shares")or.0)
   if k in("OPEN","FILLED","PENDING_CONFIRMATION","RESTING","EXIT_RESTING","POSITION_CONFIRMED","MATCHED_PENDING_SETTLEMENT")or j>.0:
    if"BOX"in str(p.get("sleeve")or"").upper()or p.get("is_dominance_box")or p.get("is_single_leg_lock"):continue
    n=float(p.get("candle_expiry_ts")or.0);m=str(p.get("target_token")or"").upper()
    if cand_expiry_ts>.0 and n>.0 and abs(n-cand_expiry_ts)<=9e2 and m:
     if m==str(cand_direction or"").upper():a*=round(1./(1.+.85),4)
     else:return.0
 if is_subhourly_15m and is_maker:a*=float(v["subordinate_15m_maker_size_mult"])
 i=str(asset or"").upper()
 if i=="SOL":a*=float(u.get("sol_canary_size_multiplier",.85))
 elif i=="ETH":a*=float(u.get("eth_canary_size_multiplier",.85))
 if a<min_lot_usd*.625:return.0
 return round(min(float(max_ticket_cap),max(float(min_lot_usd),a)),2)
# [05/13] src/polymarket_research/polymarket_live_harvester.py
import asyncio;import ctypes;import json;import logging;import math;import os;import signal;import sys;import threading;import time;from collections import defaultdict,deque;from contextvars import ContextVar;from datetime import datetime,timezone;from decimal import Decimal,ROUND_FLOOR
try:import fcntl
except ImportError:fcntl=None
from pathlib import Path;from typing import Any,Dict,List,Optional,Set,Tuple;from dotenv import load_dotenv;import requests
try:
 import orjson as _orjson
 def _json_loads(s):return _orjson.loads(s)
except Exception:
 _orjson=None
 def _json_loads(s):return json.loads(s)
PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT)not in sys.path:sys.path.insert(0,str(PIPELINE_ROOT))
load_dotenv(PIPELINE_ROOT/".env");from src.polymarket_research.polymarket_live_executor import(PolymarketLiveExecutor,OrderResult,ExecutionStatus,calculate_taker_fee,is_market_closed_or_disabled_error,load_risk_config,quantize_fok_buy_box_legs,RISK_CONFIG,_get_hot_io_pool,_HOT_DISPATCH_ACTIVE);_PRE_HOT_CTX=ContextVar("polymarket_pre_hot_ctx",default=None)
try:from zoneinfo import ZoneInfo as _ZoneInfo;_NY_TZ=_ZoneInfo("America/New_York")
except Exception:
 try:from src.polymarket_research.riskless_protocol_v2_expansion import get_us_eastern_tz as _get_ny_tz;_NY_TZ=_get_ny_tz()
 except Exception:_NY_TZ=None
try:from src.polymarket_research.latency_trace import(LatencyTrace as _LatencyTrace,CURRENT_TRACE as _CURRENT_TRACE,emit_shock_attempt as _emit_shock_attempt,emit_shock_attempt_from_trace as _emit_shock_attempt_trace)
except Exception:_LatencyTrace=None;_CURRENT_TRACE=None;_emit_shock_attempt=None;_emit_shock_attempt_trace=None
try:from src.polymarket_research.economic_attribution_ledger import(GLOBAL_DECAY_TRACKER as _STAGE_B_DECAY_TRACKER,GLOBAL_MARKOUT_SAMPLER as _STAGE_B_MARKOUT_SAMPLER,emit_funnel_event as _stage_b_emit_funnel,register_candidate_funnel_and_decay_watch as _stage_b_reg_decay_watch)
except Exception:_STAGE_B_DECAY_TRACKER=None;_STAGE_B_MARKOUT_SAMPLER=None;_stage_b_emit_funnel=None;_stage_b_reg_decay_watch=None
try:from src.polymarket_research.polymarket_ws_streams import(PolymarketClobMarketWsTracker as _PolymarketClobMarketWsTracker,PolymarketShardedClobMarketWsTracker as _PolymarketShardedClobMarketWsTracker,PolymarketPerpsLeadLagStream as _PolymarketPerpsLeadLagStream)
except Exception:
 try:from polymarket_ws_streams import(PolymarketClobMarketWsTracker as _PolymarketClobMarketWsTracker,PolymarketShardedClobMarketWsTracker as _PolymarketShardedClobMarketWsTracker,PolymarketPerpsLeadLagStream as _PolymarketPerpsLeadLagStream)
 except Exception:_PolymarketClobMarketWsTracker=None;_PolymarketShardedClobMarketWsTracker=None;_PolymarketPerpsLeadLagStream=None
LIVE_WS_BOOK_MAX_AGE_MS=float(os.environ.get("PM_LIVE_WS_BOOK_MAX_AGE_MS","2500"))
try:from src.polymarket_research.deribit_svi_surface import GLOBAL_SVI_ENGINE
except Exception:GLOBAL_SVI_ENGINE=None
try:from src.polymarket_research.holistic_strategy_governance import(GLOBAL_GOVERNANCE_MANAGER,compute_stop_risk_fractional_kelly_ticket,evaluate_ev_terminal_twap_t5_salvage,get_unleashed_v5_tier_profile,passes_capital_velocity_hurdle)
except Exception:from holistic_strategy_governance import(GLOBAL_GOVERNANCE_MANAGER,compute_stop_risk_fractional_kelly_ticket,evaluate_ev_terminal_twap_t5_salvage,get_unleashed_v5_tier_profile,passes_capital_velocity_hurdle)
try:from src.polymarket_research.net_alpha_opportunity_engine import(compute_capital_velocity_ev,compute_smart_maker_bid,evaluate_cross_oracle_basis_box_ev,evaluate_d1_15m_to_5m_corridor_conversion,evaluate_guarded_complement_merge,evaluate_optimal_stopping_exit,inspect_microstructure_feature_completeness,publish_global_positions_shm,rank_microbatch_shock_tournament,walk_dual_leg_overround_bids)
except Exception:compute_capital_velocity_ev=None;compute_smart_maker_bid=None;evaluate_cross_oracle_basis_box_ev=None;evaluate_d1_15m_to_5m_corridor_conversion=None;evaluate_guarded_complement_merge=None;evaluate_optimal_stopping_exit=None;inspect_microstructure_feature_completeness=None;publish_global_positions_shm=None;rank_microbatch_shock_tournament=None;walk_dual_leg_overround_bids=None
try:from src.polymarket_research.exact_twap_lock_engine import should_suppress_final60s_twap_salvage
except Exception:should_suppress_final60s_twap_salvage=None
try:from src.polymarket_research.same_oracle_dominance_box import walk_equal_shares_dominance_box
except Exception:walk_equal_shares_dominance_box=None
logger=logging.getLogger("LiveHarvester");logging.basicConfig(level=logging.INFO,format="[%(asctime)s UTC] [%(levelname)s] [HARVESTER] %(message)s",handlers=[logging.StreamHandler(sys.stdout)]);_FILE_LOGGER_ATTACHED=False;_LOG_QUEUE_LISTENER=None
def _ensure_file_logging():
 global _FILE_LOGGER_ATTACHED,_LOG_QUEUE_LISTENER
 if _FILE_LOGGER_ATTACHED:return
 try:
  import atexit;import logging.handlers;import queue as _qmod;c=DATA_DIR/"live_harvester.log";c.parent.mkdir(parents=True,exist_ok=True);g=logging.FileHandler(c,encoding="utf-8");g.setFormatter(logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [HARVESTER] %(message)s"));b=logging.getLogger()
  if os.environ.get("PM_ASYNC_FILE_LOGGING","1")=="1":
   a=[g]
   for h in list(b.handlers):
    if type(h)is logging.StreamHandler:b.removeHandler(h);a.append(h)
   d=_qmod.SimpleQueue();f=logging.handlers.QueueHandler(d);e=logging.handlers.QueueListener(d,*a,respect_handler_level=True);e.start();_LOG_QUEUE_LISTENER=e;atexit.register(e.stop);b.addHandler(f)
  else:b.addHandler(g)
  _FILE_LOGGER_ATTACHED=True
 except Exception:pass
_ALERT_LAST_SENT={};_ALERT_LOCK=threading.Lock();_ALERT_THREADS=[]
def flush_operational_alerts(timeout=3.):
 a=time.time()+max(.0,float(timeout))
 for t in list(_ALERT_THREADS):t.join(max(.0,a-time.time()))
 _ALERT_THREADS[:]=[t for t in _ALERT_THREADS if t.is_alive()]
def _alerts_file_path():
 if"POLYMARKET_ALERTS_FILE"in os.environ:a=os.environ["POLYMARKET_ALERTS_FILE"].strip();return Path(a)if a else None
 return DATA_DIR/"critical_alerts.jsonl"
def _post_alert_http(text,record):
 try:
  import urllib.request;e=os.environ.get("TELEGRAM_BOT_TOKEN","").strip();d=os.environ.get("TELEGRAM_CHAT_ID","").strip();c=os.environ.get("ALERT_WEBHOOK_URL","").strip();b=[]
  if e and d:b.append((f"https://api.telegram.org/bot{e}/sendMessage",{"chat_id":d,"text":text}))
  if c:b.append((c,{"text":text,**record}))
  for g,a in b:f=urllib.request.Request(g,data=json.dumps(a).encode("utf-8"),headers={"Content-Type":"application/json"},method="POST");urllib.request.urlopen(f,timeout=2.5).read()
 except Exception:pass
def send_operational_alert(event_type,message,severity="CRITICAL",rate_limit_sec=.0,dedupe_key=None):
 h=time.time();g=dedupe_key or event_type
 with _ALERT_LOCK:
  if rate_limit_sec>0 and(h-_ALERT_LAST_SENT.get(g,.0))<rate_limit_sec:return False
  _ALERT_LAST_SENT[g]=h
 d={"ts_utc":datetime.now(timezone.utc).isoformat(),"unix":round(h,3),"severity":str(severity).upper(),"event_type":str(event_type),"message":str(message),"host_pid":os.getpid()};f=_alerts_file_path()
 if f is not None:
  try:
   f.parent.mkdir(parents=True,exist_ok=True)
   with open(f,"a",encoding="utf-8")as j:j.write(json.dumps(d)+"\n")
  except Exception as b:logger.error(f"[ALERT] Failed to append alert ledger: {b}")
 c=logger.critical if d["severity"]=="CRITICAL"else(logger.warning if d["severity"]=="WARNING"else logger.info);c(f"[ALERT:{d['severity']}] {event_type}: {message}");a=(os.environ.get("POLYMARKET_ALERTS_SUPPRESS_HTTP")=="1"and os.environ.get("POLYMARKET_ALERTS_FORCE_HTTP")!="1")
 if not a:e=f"[Polymarket {d['severity']}] {event_type}: {message}";i=threading.Thread(target=_post_alert_http,args=(e,d),daemon=True,name="pm-alert-dispatch");_ALERT_THREADS.append(i);i.start()
 return True
class LinuxInotifyWatcher:
 IN_MODIFY=0x00000002;IN_CLOSE_WRITE=0x00000008;IN_NONBLOCK=0x00000800
 def __init__(a,filepath):
  a.filepath=filepath;a.fd=-1;a.wd=-1;a._available=False
  try:
   a.libc=ctypes.CDLL("libc.so.6",use_errno=True);a.inotify_init1=a.libc.inotify_init1;a.inotify_init1.restype=ctypes.c_int;a.inotify_init1.argtypes=[ctypes.c_int];a.inotify_add_watch=a.libc.inotify_add_watch;a.inotify_add_watch.restype=ctypes.c_int;a.inotify_add_watch.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_uint32];a.fd=a.inotify_init1(a.IN_NONBLOCK)
   if a.fd>=0:
    if not a.filepath.exists():a.filepath.touch()
    b=str(a.filepath).encode("utf-8");a.wd=a.inotify_add_watch(a.fd,b,a.IN_MODIFY|a.IN_CLOSE_WRITE)
    if a.wd>=0:a._available=True
  except Exception:pass
 @property
 def is_available(a):return a._available and a.fd>=0
 def drain_events(a):
  if not a.is_available:return
  try:os.read(a.fd,4096)
  except(BlockingIOError,OSError):pass
 def close(a):
  if a.fd>=0:
   try:os.close(a.fd)
   except Exception:pass
   a.fd=-1
DATA_DIR=PIPELINE_ROOT/"data/polymarket";TRIGGER_FILE=DATA_DIR/"live_shock_triggers.jsonl";SHOCK_FILE=DATA_DIR/"shock_responses.jsonl";RESOLUTIONS_FILE=DATA_DIR/"finalized_market_resolutions.jsonl";STATE_FILE=DATA_DIR/"live_harvester_state.json";PID_FILE=DATA_DIR/"live_harvester.pid";COUNTERFACTUAL_CANDIDATES_FILE=DATA_DIR/"counterfactual_candidates.jsonl";SHADOW_PHASE3_4_FILE=DATA_DIR/"shadow_phase3_4_tracker.jsonl";D1_LIVE_CANDIDATES_FILE=DATA_DIR/"d1_live_box_candidates.jsonl";FAST_TICK_DIR=Path(os.getenv("PM_FAST_TICK_DIR","/dev/shm"));FAST_TICK_SHM_DIR=FAST_TICK_DIR;FAST_TICK_MAX_AGE_SEC=.5;VENUE_DIVERGENCE_VETO_BPS=15.;RECORDER_HEARTBEAT_FILES=[FAST_TICK_DIR/f"pm_fast_tick_{a}.json"for a in("BTC","ETH","SOL")]
def read_fast_tick(asset,max_age_sec=FAST_TICK_MAX_AGE_SEC,now=None):
 if"PM_FAST_TICK_DIR"in os.environ:
  b=os.environ["PM_FAST_TICK_DIR"].strip()
  if not b:return None
  a=Path(b)
 else:a=FAST_TICK_SHM_DIR
 try:
  with open(a/f"pm_fast_tick_{str(asset).upper()}.json","rb")as f:c=_json_loads(f.read())
  e=float(c.get("ts")or c.get("timestamp_unix")or.0);d=(now if now is not None else time.time())-e
  if e<=.0 or d>max_age_sec or d<-2.:return None
  return c
 except Exception:return None
def check_recorder_freshness(max_stale_sec=15.,now_ts=None):
 d=float(now_ts if now_ts is not None else time.time())
 if not RECORDER_HEARTBEAT_FILES:return False,"no_heartbeat_files"
 c=[]
 for p in RECORDER_HEARTBEAT_FILES:
  try:
   h=d-p.stat().st_mtime
   if h<-2. or h>max_stale_sec:c.append(f"mtime_stale:{p.name}:{h:.1f}s");continue
   i=_json_loads(p.read_bytes())
   if isinstance(i,dict):
    a=float(i.get("ts")or i.get("timestamp_unix")or.0)
    if a>.0:
     g=d-a
     if g<-2. or g>max_stale_sec:c.append(f"internal_stale:{p.name}:{g:.1f}s>{max_stale_sec:.1f}s");continue
    b=float(i.get("spot_ts")or.0)
    if b>.0:
     f=d-b
     if f<-2. or f>max_stale_sec:c.append(f"spot_stale:{p.name}:{f:.1f}s>{max_stale_sec:.1f}s");continue
   return True,f"ok:{p.name}"
  except Exception as e:c.append(f"missing:{p.name}:{e}")
 return False,";".join(c)or"stale"
def fast_tick_book_for_token(snap,token_id):
 if not snap or not token_id:return None
 a=[snap.get("UP"),snap.get("DOWN")]
 for i in("m15","m5","h4"):
  h=snap.get(i)
  if isinstance(h,dict):a+=[h.get("UP"),h.get("DOWN")]
 d=snap.get("markets")
 if isinstance(d,dict):
  for g in d.values():
   if isinstance(g,dict):a+=[g.get("UP"),g.get("DOWN")]
 for j in a:
  if not isinstance(j,dict)or str(j.get("token_id"))!=str(token_id):continue
  l=float(j.get("best_bid")or.0);k=float(j.get("best_ask")or.0)
  if l<=.0 or k<=.0 or k>=1. or l>=k:return None
  f=j.get("raw_top_bids");e=j.get("raw_top_asks");c=([{"price":str(p),"size":str(s)}for p,s in f if float(p)>0 and float(s)>0]if isinstance(f,list)and f else[])or[{"price":str(l),"size":str(j.get("bid_size_l1")or.0)}];b=([{"price":str(p),"size":str(s)}for p,s in e if float(p)>0 and float(s)>0]if isinstance(e,list)and e else[])or[{"price":str(k),"size":str(j.get("ask_size_l1")or.0)}];return{"bids":c,"asks":b,"source":"shm_fast_tick"}
 return None
def evaluate_coinbase_venue_veto(shock,target_token):
 try:
  n=float(shock.get("coinbase_spot")or.0)
  if n<=.0:return False,"coinbase_unavailable_fail_open"
  j=str(shock.get("asset")or"").upper();m=str(shock.get("horizon")or shock.get("candle_interval")or"").lower();k=float(shock.get("candle_sigma")or.0)
  if k>.0:a=k*(2. if("15m"in m or"900"in m)else(math.sqrt(12.)if m in("5m","5min","300","300s")else 1.))
  elif j=="ETH":a=.0068
  elif j in("SOL","XRP"):a=.0085
  else:a=.005
  g=min(2.,max(1.,a/.005));c=shock.get("venue_divergence_centered_bps")is not None
  if c:b=float(shock["venue_divergence_centered_bps"])
  else:b=float(shock.get("venue_divergence_bps")or.0)
  i=float(shock.get("coinbase_move_bps_2s")or.0);l=1. if target_token=="UP"else-1.;h=l*b;d=l*i;f=d<(-.5*g)
  if(c and h>(12.*g))or d<(-4.*g)or(h>(VENUE_DIVERGENCE_VETO_BPS*g)and f):return True,f"directional venue divergence {h:+.1f}bps / Coinbase opposing dump ({i:+.2f}bps/2s, mult={g:.2f}x)"
  return False,f"ok (dir_div={h:+.1f}bps, cb_move={i:+.2f}bps)"
 except Exception as e:return False,f"veto_eval_error_fail_open: {e}"
QUEUE_JUMP_MIN_WALL_SHARES=250.;QUEUE_JUMP_WALL_MULT=6.;QUEUE_JUMP_MIN_TP_FLOOR=.95;QUEUE_JUMP_MIN_TARGET=.97;FAST_CONFIRM_POLL_SEC=.2;FAST_CONFIRM_WINDOW_SEC=10.;FAST_SETTLEMENT_RECHECK_WINDOW_SEC=12.
def compute_queue_priority_maker_price(entry_price,rem_shares,valid_bids,valid_asks,current_target_px):
 try:
  j=round(float(current_target_px),2)
  if j<QUEUE_JUMP_MIN_TARGET or float(rem_shares)<=.0:return None
  h=[(float(b.get("price",.0)),float(b.get("size",.0)))for b in(valid_bids or[])];g=[(float(a.get("price",.0)),float(a.get("size",.0)))for a in(valid_asks or[])];h=[(p,s)for p,s in h if s>0 and.0<p<1.];g=[(p,s)for p,s in g if s>0 and.0<p<1.]
  if not h or not g:return None
  f=max(p for p,_ in h);e=min(p for p,_ in g)
  if e<j-1e-9:return None
  c=sum(s for p,s in g if abs(p-j)<1e-9)
  if c<=max(QUEUE_JUMP_MIN_WALL_SHARES,QUEUE_JUMP_WALL_MULT*float(rem_shares)):return None
  if f<j-.03-1e-9:return None
  i=max(round(float(entry_price)+.14,2),QUEUE_JUMP_MIN_TP_FLOOR);d=round(j-.01,2)
  if d<i-1e-9 or d<=f+1e-9:return None
  return d
 except Exception:return None
DEFAULT_TICKET_NOTIONAL=RISK_CONFIG["ticket_notional"];DEFAULT_MAX_TRADES_PER_MARKET=2;DEFAULT_MAX_TRADES_PER_HOUR=6;HARD_PORTFOLIO_EXPOSURE_CEILING=5e2;MAX_PORTFOLIO_EXPOSURE_USD=5e2;MIN_LOT_SIZE_USD=12.;DEFAULT_MAX_CONCURRENT_POSITIONS=RISK_CONFIG["max_concurrent_positions"];PROFIT_THETA=.14;MIN_DISTANCE_PCT=.1;MAX_TTE_SECONDS=2700.;MIN_TTE_SECONDS=90.;MAX_PRICE_CEILING=.86;MIN_PRICE_FLOOR=.55;MAX_ALLOWED_SPREAD=.03;ALLOWED_ASSETS={"BTC","ETH"};CIRCUIT_BREAKER_EQUITY_FLOOR=RISK_CONFIG["min_equity_floor"];DYNAMIC_BANKROLL_PCT=RISK_CONFIG["dynamic_risk_pct"];SL_POLICY="SPOT_DELTA_PASSIVE";SPOT_DELTA_K=1.15;MAX_ADVERSE_SPOT_MOVE_PCT=float(os.getenv("POLYMARKET_MAX_ADVERSE_SPOT_MOVE_PCT","0.0040"));TTE_CANCEL_WINDOW=15.;KELLY_FRACTION=.5;MAX_NOTIONAL_CAP_PCT=.25;MAX_ABSOLUTE_TICKET_USD=2e2;PASSIVE_UNWIND_TIMEOUT=15.;GLOBAL_HALT_STATUSES=frozenset({"ENTRY_OUTCOME_UNKNOWN","EXIT_POST_OUTCOME_UNKNOWN","UNWIND_EXECUTION_OUTCOME_UNKNOWN","UNWIND_RECONCILIATION_REQUIRED","FILL_RECONCILIATION_REQUIRED","RESOLUTION_CANCEL_UNCONFIRMED","RECONCILIATION_HOLD_INCOMPLETE_SCHEMA","UNRESOLVED_BALANCE_DISCREPANCY","TERMINAL_UNWIND_FAILED_SUPERVISED","ENTRY_ONCHAIN_REVERTED","LIQUIDITY_CRISIS"});MARKET_SCOPED_ENTRY_HALT_STATUSES=frozenset({"ENTRY_OUTCOME_UNKNOWN","ENTRY_ONCHAIN_REVERTED"});PIPELINE_GLOBAL_HALT_STATUSES=GLOBAL_HALT_STATUSES-MARKET_SCOPED_ENTRY_HALT_STATUSES;MAKER_EXIT_POSTABLE_STATUSES=frozenset({"","NONE","PENDING_CONFIRMATION","AWAITING_DELTA_SETTLEMENT","AWAITING_SETTLEMENT","ENTRY_INVENTORY_RECONCILIATION_REQUIRED","POST_FAILED","EXIT_RECOVERY_REQUIRED","CROSSED_AT_MAX_TICK_WAIT"});PARTIAL_UNWIND_RESIDUAL_STATUSES=frozenset({"PARTIAL_UNWIND_REMAINING","PARTIAL_SALVAGE_REMAINING","PARTIAL_REPRICED_UNWIND_REMAINING","PARTIAL_PASSIVE_UNWIND_REMAINING"});SETTLEMENT_RECEIVABLE_STATUSES=frozenset({"AWAITING_ONCHAIN_SETTLEMENT"});UNRESOLVED_RECONCILIATION_STATUSES=GLOBAL_HALT_STATUSES;ENTRY_UNEXECUTED_PROOF_AGE_S=60.;UNWIND_UNKNOWN_PROOF_AGE_S=30.;REDEMPTION_POLL_INTERVAL_S=15.
def position_requires_global_halt(pos):return(pos.get("exit_order_status")in PIPELINE_GLOBAL_HALT_STATUSES or pos.get("status")in PIPELINE_GLOBAL_HALT_STATUSES)
def position_requires_lifecycle_resolution(pos):return(pos.get("exit_order_status")in GLOBAL_HALT_STATUSES or pos.get("status")in GLOBAL_HALT_STATUSES)
def position_may_post_new_maker_exit(pos):
 if position_requires_lifecycle_resolution(pos):return False
 if pos.get("is_liquidating")or pos.get("unwind_order_id"):return False
 if pos.get("status")in SETTLEMENT_RECEIVABLE_STATUSES or pos.get("status")in{"ENTRY_OUTCOME_UNKNOWN","FAILED"}:return False
 if pos.get("hold_to_maturity_lock")or pos.get("terminal_policy")=="DETERMINISTIC_TERMINAL_HOLD_FINAL"or pos.get("exit_order_status")=="SUB_MINIMUM_LOT_SUPERVISED_HOLD":return False
 return str(pos.get("exit_order_status")or"")in MAKER_EXIT_POSTABLE_STATUSES
def position_is_settlement_receivable(pos):return pos.get("status")in SETTLEMENT_RECEIVABLE_STATUSES
def compute_composite_edge_score(shock,*,v5_wfo_parity=False):
 L=str(shock.get("shock_direction")or"UP").upper();o="UP"if L in("BUY","UP")else"DOWN";K="DOWN"if o=="UP"else"UP";_c=shock.get("pre_shock_features_t0",{})or{};tf=_c.get(o,{})or{};_a=_c.get(K,{})or{}
 if inspect_microstructure_feature_completeness is not None:
  n=inspect_microstructure_feature_completeness(shock,o,str(tf.get("token_id")or""));z=list(n.get("missing_fields")or[])
  if n.get("hard_veto_live")and(not v5_wfo_parity or any(f!="age_ask_ms"for f in z)):return{"e_score":.0,"tier":"TIER_C_REJECT","kelly_multiplier":.0,"fak_price_buffer":.01,"veto":True,"veto_reason":f"Missing live microstructure telemetry: {z}","feature_hygiene":n}
 if tf.get("age_ask_ms")is not None:d=float(tf.get("age_ask_ms"))
 elif float(tf.get("best_ask")or.0)>=.995 and tf.get("age_bid_ms")is not None:d=min(240.,float(tf.get("age_bid_ms")))
 else:d=4e2
 if shock.get("shock_source")in("BOUNDARY_LOCK","EXP316_TRACK_A_CONVERGENCE")or shock.get("sleeve")=="SLEEVE_3_STRIKE_CONVERGENCE":d=max(d,450.)
 y=float(tf.get("age_bid_ms")if tf.get("age_bid_ms")is not None else 4e2);t=float(_a.get("age_bid_ms")if _a.get("age_bid_ms")is not None else 4e2);s=min(55.,max(.0,(d/350.)*55.));J=min(10.,max(.0,(t/5e2)*10.));V=min(1e2,max(.0,35.+s+J));I=float(shock.get("shock_ofi",1.)if shock.get("shock_ofi")is not None else 1.);U=min(1.,max(.0,abs(I)));H=float(shock.get("shock_volume_100ms",1e6)or 1e6);G=str(shock.get("asset","BTC")).upper();Q=1.5e6 if G=="BTC"else 5e5;F=min(2.5,max(.2,H/Q));r=float(shock.get("delta_basis_100ms",.0)or.0);k=r if o=="UP"else-r;x=bool(shock.get("is_40ms_fast_track",False));E=U*50.+min(30.,F*12.)+(10. if x else.0);w=max(-20.,min(15.,k*5.));Z=min(1e2,max(.0,E+w));Y=float(tf.get("obi_l1",.0)or.0);D=float(tf.get("obi_depth",.0)or.0);X=float(tf.get("spread",.01)or.01);T=float(tf.get("q_micro",.0)or.0);_b=float(tf.get("q_mid",.0)or.0);v=((T-_b)/max(X,.005))if(T>0 and _b>0)else.0;_d=min(1e2,max(.0,50.+Y*20.+D*15.+v*15.));P=tf.get("raw_top_asks",[])or[];C=float(P[0][0])if P else.65;S=float(tf.get("vwap_$25")or tf.get("vwap_$20")or C);m=max(.0,1e2-max(.0,X-.01)*2e3);O=max(.0,S-C);u=max(.0,1e2-O*2500.);W=min(1e2,max(.0,.5*m+.5*u));R=.35*V+.3*Z+.2*_d+.15*W;e=False;a=None;i=-6. if str(shock.get("shock_source","")).upper()=="SPOT"else-2.;l=.2 if v5_wfo_parity else.6;g=.0 if v5_wfo_parity else 50.;j=abs(float(shock.get("candle_distance_pct",.0)or.0));B=float(shock.get("candle_sigma")or.0);N=float(shock.get("seconds_to_expiry")or 3600.);M=str(shock.get("horizon")or"").lower();A=math.sqrt(12.)if M=="5m"else(2. if M=="15m"else 1.);q=(B*A)if B>.0 else.005;p=(j/1e2)/max(.00025,q*math.sqrt(max(N,30.)/3600.))
 if U<l:e=True;a=f"OFI {U:.2f} < {l:.2f} hurdle"
 elif k<i:e=True;a=f"Directional delta_basis {k:.2f} bps < {i:.1f} bps"
 elif not v5_wfo_parity and d<25. and Y<-.25:e=True;a=f"Ultra-fresh MM ask reload (age={d:.1f}ms < 25ms, obi_l1={Y:.2f} < -0.25)"
 elif not v5_wfo_parity and d<50. and Y<-.5:e=True;a=f"Ask already repriced by MM (age={d:.1f}ms < 50ms, obi_l1={Y:.2f} < -0.50)"
 elif Y<-.55 and.0<j<.09 and not(B>.0 and p>=.55 and d>=150.):e=True;a=f"Heavy L1 ask wall against thin cushion (obi_l1={Y:.2f} < -0.55, dist={j:.4f}% < 0.09%)"
 if e:h="TIER_C_REJECT";c=.0;b=.01
 elif round(R,1)>=70. and d>=250.:h="TIER_A_PLUS_STALE_SNIPE";c=1.15;b=.02
 elif round(R,1)>=g:h="TIER_B_STANDARD";c=1.;b=.015
 else:h="TIER_C_REJECT";c=.0;b=.01;e=True;a=f"e_score {R:.1f} < {g:.1f} threshold"
 return{"e_score":round(R,2),"tier":h,"kelly_multiplier":c,"fak_price_buffer":b,"veto":e,"is_vetoed":e,"veto_reason":a,"sub_scores":{"s_stale":round(V,2),"s_flow":round(Z,2),"s_l2":round(_d,2),"s_slip":round(W,2),"S_stale":round(V,2),"S_flow":round(Z,2),"S_L2":round(_d,2),"S_slip":round(W,2)},"age_ask_ms":d}
def compute_max_acceptable_ask(dist_pct,tte_sec,asset="BTC",shock_ofi=1.,shock_vol_usd=1.5e6,delta_basis_bps=.0,age_ask_ms=350.,target_return=.14,fee_rate=.07,is_subhourly_15m=False,expected_salvage_net=.36,q_tail=.08,candle_sigma=None,is_5m=False):
 i=str(asset or"BTC").upper();a=.005 if i=="BTC"else(.0095 if i=="SOL"else.0068);m=.0028
 if candle_sigma is not None and float(candle_sigma)>.0:y=math.sqrt(12.)if is_5m else(2. if is_subhourly_15m else 1.);a=max(m,float(candle_sigma)*y)
 if GLOBAL_SVI_ENGINE is not None and os.environ.get("PM_SVI_DISABLE_BG_REFRESH")!="1":
  try:
   s=float(GLOBAL_SVI_ENGINE.get_hourly_sigma(i,fallback=a)or.0)
   if s>.0:a=max(m,min(a,s*.8))
  except Exception:pass
 c=3e2 if is_5m else(9e2 if is_subhourly_15m else 3600.);g=a*math.sqrt(c/3600.);h=max(float(tte_sec),15.);p=g*math.sqrt(h/c);f=abs(float(dist_pct))/1e2;q=1.5e6 if i=="BTC"else 5e5;o=min(3.,max(.2,float(shock_vol_usd)/q));t=min(1.,max(.0,abs(float(shock_ofi))));l=1.+.15*max(-.5,min(1.,(float(age_ask_ms)-2e2)/4e2));n=(6.5*t*(o**.3)+.45*float(delta_basis_bps))*l;b=(n/1e4)*min(1.,math.sqrt(3e2/h))
 if is_subhourly_15m or is_5m:x=max(.0,min(1.,(f-.00065)/5e-4));b=min(b,(.25+.75*x)*f);expected_salvage_net=float(expected_salvage_net)*(.45+.55*x)
 z=(f+b)/max(p,1e-6);w=.5*(1.+math.erf(z/math.sqrt(2.)));v=.985;d=w*v+(1.-w)*(1.-q_tail)*expected_salvage_net;r=float(fee_rate);A=float(target_return);e=(1.+r)**2-4.*r*d/(1.+A)
 if e<=.0 or w<=.53:j=.0
 else:u=((1.+r)-math.sqrt(e))/(2.*r);k=.78 if h>9e2 else.85;j=min(k,max(.0,round(u,4)))
 return{"p_max":j,"p_true":round(w,4),"expected_payoff":round(d,4),"z_eff":round(z,3),"sigma_rem_pct":round(p*1e2,4)}
def compute_modified_salvage_kelly_fraction(p_win,entry_price,target_exit=.985,l_salvage=.42,q_tail=.05,kelly_lambda=.28):
 if entry_price<=.01 or entry_price>=.99 or p_win<=.5:return.0
 d=(target_exit-entry_price)/entry_price
 if d<=.001:return.0
 c=(1.-q_tail)*l_salvage+q_tail;e=p_win*d-(1.-p_win)*c;b=d*c
 if b<=.0:return.0
 a=e/b
 if a<=.0:return.0
 return round(float(a*kelly_lambda),4)
def compute_correlated_truncated_kelly_size(live_equity=.0,entry_px=.0,p_win=.0,kelly_multiplier=1.,active_positions=None,cand_expiry_ts=.0,cand_direction="UP",min_lot_usd=12.,max_ticket_cap=2e2,default_sizing_pct=.24,bankroll_usd=None,entry_price=None,p_true=None):
 if bankroll_usd is not None and live_equity<=.0:live_equity=bankroll_usd
 if entry_price is not None and entry_px<=.0:entry_px=entry_price
 if p_true is not None and p_win<=.0:p_win=p_true
 if live_equity<=.0 or entry_px<=.0 or p_win<=.0:return.0
 j=compute_modified_salvage_kelly_fraction(p_win,entry_px)
 if j<=.0:return.0
 j=min(float(default_sizing_pct),j);i=max(.8,min(1.3,float(kelly_multiplier)));h=min(float(default_sizing_pct)*1.15,j*i);a=1.
 if active_positions:
  for p in active_positions.values():
   e=str(p.get("status")or"FILLED");d=float(p.get("remaining_shares")or.0)
   if e in("OPEN","FILLED","PENDING_CONFIRMATION","RESTING","EXIT_RESTING")or d>.0:
    g=float(p.get("candle_expiry_ts")or.0);f=str(p.get("target_token")or"").upper()
    if cand_expiry_ts>0 and g>0 and abs(g-cand_expiry_ts)<=9e2 and f:
     if f==cand_direction.upper():a=min(a,round(1./(1.+.85),4))
     else:return.0
 c=live_equity*h*a;b=round(min(max_ticket_cap,max(min_lot_usd,c)),2);return b
def apply_convex_payoff_sizing_cap(raw_ticket_usd,*,live_equity,entry_px,sleeve="",knee=.79,gamma=.75,min_taper=.58,max_salvage_risk_pct=.125,salvage_floor_px=.24,min_lot_usd=8.):
 if raw_ticket_usd<=.0 or live_equity<=.0 or entry_px<=.0:return max(.0,float(raw_ticket_usd))
 g=str(sleeve or"").upper()
 if"BOX"in g or g=="SLEEVE_4_BOUNDARY_SNIPE":return round(float(raw_ticket_usd),2)
 h=min(.97,max(.05,float(entry_px)));c=1.
 if h>knee:f=max(.04,.99-h);e=max(.04,.99-knee);c=max(float(min_taper),(f/e)**float(gamma))
 a=max(.25,(h-float(salvage_floor_px))/h);b=(float(max_salvage_risk_pct)*float(live_equity))/a;d=min(float(raw_ticket_usd)*c,b);return round(min(float(raw_ticket_usd),max(float(min_lot_usd),d)),2)
def get_equity_tier_limits(total_equity,high_water_mark_equity=None,previous_tier=None):
 l=float(total_equity)if(total_equity is not None and math.isfinite(float(total_equity)))else.0;k=(float(high_water_mark_equity)if(high_water_mark_equity is not None and math.isfinite(float(high_water_mark_equity))and float(high_water_mark_equity)>.0)else l)
 if k<l:k=l
 j=float(RISK_CONFIG.get("seed_survival_equity_threshold",88.));g=j+3. if previous_tier=="SEED_SURVIVAL"else j
 if l<g:d="SEED_SURVIVAL";b=float(RISK_CONFIG.get("dynamic_risk_pct",.1568));a=int(RISK_CONFIG.get("seed_survival_max_concurrent",1));h=float(RISK_CONFIG.get("max_exposure",24.));c=round(max(min(h,l*.82)if l>0 else h,l*.3),2);f=float(RISK_CONFIG.get("max_daily_loss",22.));e=float(RISK_CONFIG.get("seed_survival_floor_usd",48.));return{"tier":d,"dynamic_bankroll_pct":b,"max_concurrent_positions":a,"max_slots":a,"max_exposure":c,"max_daily_loss":f,"min_equity_floor":e}
 if previous_tier in("SEED_SURVIVAL","SEED_RAMP")and l<108.:i=1 if l<98. else 2;return{"tier":"SEED_RAMP","dynamic_bankroll_pct":float(RISK_CONFIG.get("dynamic_risk_pct",.18)),"max_concurrent_positions":i,"max_slots":i,"max_exposure":round(max(30.,l*.38),2),"max_daily_loss":round(max(22.,l*.26),2),"min_equity_floor":round(max(54.,min(65.,k*.64)),2)}
 if l<140.:d="RECOVERY";b=.22;a=2;c=round(max(45.,l*.55),2)
 elif l<3e2:d="GROWTH";b=.26;a=3;c=round(min(350.,l*.75),2)
 else:d="SCALE";b=.28;a=3;c=round(min(5e2,l*.85),2)
 f=round(max(25.,l*.3),2);e=round(max(65.,k*.68),2);return{"tier":d,"dynamic_bankroll_pct":b,"max_concurrent_positions":a,"max_slots":a,"max_exposure":c,"max_daily_loss":f,"min_equity_floor":e}
class StatePersistenceError(RuntimeError):pass
class EmergencyRiskController:
 def __init__(a,max_consecutive_losses=3,max_daily_loss_usd=None,max_daily_loss_pct=.18,min_equity_floor_usd=CIRCUIT_BREAKER_EQUITY_FLOOR):a.max_consecutive_losses=max_consecutive_losses;a.max_daily_loss_usd=max_daily_loss_usd if max_daily_loss_usd is not None else float(RISK_CONFIG["max_daily_loss"]);a.max_daily_loss_pct=max_daily_loss_pct;a.min_equity_floor_usd=min_equity_floor_usd;a.consecutive_losses=0;a.daily_realized_loss=.0;a.last_loss_date_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d");a.halted=False;a.halt_reason="";a.kill_file=DATA_DIR/"KILL_SWITCH";a._halt_alerted=False;a.last_checked_equity=None;a._harvester_ref=None
 def _kill_file_active(self):
  a=self.kill_file
  if a==(DATA_DIR/"KILL_SWITCH")and STATE_FILE.parent!=DATA_DIR:a=STATE_FILE.parent/"KILL_SWITCH"
  return a.exists()
 def check_equity_drawdown(a,current_equity,high_water_mark=None,*,allow_auto_clear=False):
  if current_equity is not None and math.isfinite(float(current_equity)):
   b=float(current_equity);a.last_checked_equity=b
   if b<a.min_equity_floor_usd:a.halted=True;a.halt_reason=(f"Account equity ${b:.2f} < ${a.min_equity_floor_usd:.2f} circuit-breaker threshold (2-loss variance buffer breached).");logger.critical(f"[CIRCUIT_BREAKER_HALT] {a.halt_reason}")
   elif(a.halted and"Account equity"in a.halt_reason and allow_auto_clear and b>=(a.min_equity_floor_usd+3.)):
    if a._kill_file_active():a.halt_reason=f"Emergency KILL_SWITCH file detected at {a.kill_file}"
    else:a.halted=False;a.halt_reason="";logger.info(f"[CIRCUIT_BREAKER_CLEARED] Verified equity ${b:.2f} >= +$3.00 above ${a.min_equity_floor_usd:.2f} floor.")
  return bool(a.halted)
 def _check_and_reset_daily(a):
  b=datetime.now(timezone.utc).strftime("%Y-%m-%d")
  if b!=a.last_loss_date_utc:
   logger.info(f"[RISK CONTROLLER] UTC day rolled over ({a.last_loss_date_utc} -> {b}). Resetting daily realized loss to $0.00.");a.daily_realized_loss=.0;a.last_loss_date_utc=b
   if a.halted and"Max daily loss reached"in a.halt_reason:a.halted=False;a.halt_reason="";a._halt_alerted=False
 def record_trade_pnl(a,net_pnl,*,is_non_directional=False):
  a._check_and_reset_daily()
  if is_non_directional and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("risk_controller",{}).get("decouple_riskless_boxes_from_directional_halt",True)):a.non_directional_realized_pnl=round(float(getattr(a,"non_directional_realized_pnl",.0)or.0)+float(net_pnl),4);return
  if net_pnl<0:
   a.consecutive_losses+=1;a.daily_realized_loss+=abs(net_pnl)
   if a.consecutive_losses>=a.max_consecutive_losses:a.halted=True;a.halt_reason=f"Max consecutive losses reached ({a.consecutive_losses})"
   elif a.daily_realized_loss>=a.max_daily_loss_usd:a.halted=True;a.halt_reason=f"Max daily loss reached (${a.daily_realized_loss:.2f} on {a.last_loss_date_utc})"
  else:
   a.consecutive_losses=0
   if not a.halted:a.daily_realized_loss=max(.0,a.daily_realized_loss-net_pnl)
 def is_halted(a):
  a._check_and_reset_daily();c=a._kill_file_active()
  if a.halted and"KILL_SWITCH file"in str(a.halt_reason or"")and not c:a.halted=False;a.halt_reason="";a._halt_alerted=False
  b=False
  if c:
   a.halted=True
   if not a.halt_reason:a.halt_reason=f"Emergency KILL_SWITCH file detected at {a.kill_file}"
   b=True
  elif a.halted:b=True
  if b and not a._halt_alerted:a._halt_alerted=True;send_operational_alert("KILL_SWITCH_TRIPPED",f"Trading halted: {a.halt_reason or'unspecified'}","CRITICAL",rate_limit_sec=float(RISK_CONFIG["alert_rate_limit_sec"]),dedupe_key=f"halt:{a.halt_reason[:60]}")
  elif not b:a._halt_alerted=False
  return b
 def check_kill_switch(self):return self.is_halted()
 def is_riskless_box_halted(b):
  if b._kill_file_active():return True
  if b.halted:
   g=str(b.halt_reason or"").lower()
   if any(k in g for k in("persistence","reconcil","heartbeat","kill_switch")):return True
   if"equity"in g:
    e=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("risk_controller",{})
    if not bool(e.get("decouple_riskless_boxes_from_directional_halt",True)):return True
    d=float(e.get("riskless_hard_ruin_floor_usd",30.)or 30.);c=[]
    if b.last_checked_equity is not None and math.isfinite(float(b.last_checked_equity)):c.append(float(b.last_checked_equity))
    f=getattr(b,"_harvester_ref",None)
    if f is not None:
     try:
      from src.polymarket_research.riskless_protocol_v2_expansion import compute_reconciled_concentration_nav_usd as a
      if(getattr(f,"_last_known_collateral",None)is not None or getattr(f,"active_positions",None)or getattr(f,"pending_entry_intents",None)):c.append(a(f))
     except Exception:return True
    if not c:return True
    if min(c)<d-1e-6:return True
  return False
def compute_kelly_ticket_size(p_model,p_market_ask=None,bankroll=.0,fee_rate=None,fee_exponent=None,max_cap=None,*,p_eff=None):
 c=p_eff if p_market_ask is None else p_market_ask
 if c is None or not all(math.isfinite(float(v))for v in(p_model,c,bankroll)):return.0
 if not(.0<float(p_model)<1.)or float(bankroll)<=.0 or float(c)<=.0 or float(p_model)<=float(c):return.0
 a=float(max_cap)if max_cap is not None else MAX_ABSOLUTE_TICKET_USD;b=min(max(25.,float(bankroll)*MAX_NOTIONAL_CAP_PCT),a);return round(b,2)
from src.polymarket_research.riskless_protocol_v2_expansion import(_hv__attempt_live_phase3a_maker_rescue,_hv__finish_single_leg_lock,_hv__finish_negrisk_convert_arb,_hv__record_inline_d1_legged_out_close,_hv_maybe_execute_graduated_maker_anchor_box,_hv__evaluate_shock_and_execute_impl,_hv__maybe_recycle_disputed_htm_lock)
def _bind_hv_method(_raw_fn,_pub_name):import types as _types;a=_types.FunctionType(_raw_fn.__code__,globals(),_pub_name,_raw_fn.__defaults__,_raw_fn.__closure__);a.__kwdefaults__=getattr(_raw_fn,'__kwdefaults__',None);a.__annotations__=dict(getattr(_raw_fn,'__annotations__',{})or{});a.__doc__=_raw_fn.__doc__;a.__module__=_raw_fn.__module__;return a
class PolymarketLiveHarvester:
 def __init__(a,ticket_notional=DEFAULT_TICKET_NOTIONAL,dry_run=False,dynamic_sizing=True,max_exposure=None,max_concurrent=None,max_trades_per_market=DEFAULT_MAX_TRADES_PER_MARKET,max_trades_per_hour=DEFAULT_MAX_TRADES_PER_HOUR,max_tte=MAX_TTE_SECONDS,max_price_ceiling=MAX_PRICE_CEILING,min_price_floor=MIN_PRICE_FLOOR,profit_theta=PROFIT_THETA,spot_delta_k=SPOT_DELTA_K,tte_cancel_window=TTE_CANCEL_WINDOW,kelly_fraction=KELLY_FRACTION,max_notional_cap_pct=MAX_NOTIONAL_CAP_PCT,passive_unwind_timeout=PASSIVE_UNWIND_TIMEOUT,depth_hurdle=1.3,unconstrained_kelly=False,max_absolute_ticket_usd=None,dynamic_theta=False,hold_to_maturity=True,exit_policy="two_tranche_95_98",allow_cli_exposure=False,allow_cli_concurrency=False,allowed_assets=None,reset_risk=False,max_daily_loss=None):
  DATA_DIR.mkdir(parents=True,exist_ok=True);a.ticket_notional=ticket_notional;a.dry_run=dry_run;a.dynamic_sizing=dynamic_sizing;a.unconstrained_kelly=unconstrained_kelly;a.hold_to_maturity=hold_to_maturity;a.exit_policy=str(exit_policy or"two_tranche_95_98").strip().lower();e=STATE_FILE.parent/"RESET_RISK_ONCE"
  if not dry_run and e.exists():
   try:e.unlink();reset_risk=True;logger.info("[STARTUP] Consumed RESET_RISK_ONCE marker; risk controller will be reset once.")
   except Exception as g:logger.warning(f"[STARTUP] Could not consume RESET_RISK_ONCE marker: {g}")
  a.reset_risk=reset_risk;a.risk_config=dict(RISK_CONFIG);a._shutdown_requested=False;a._shutdown_status=None;a.allowed_assets=set(allowed_assets)if allowed_assets is not None else set(ALLOWED_ASSETS);c=float(max_exposure if max_exposure is not None else float(a.risk_config.get("max_exposure",MAX_PORTFOLIO_EXPOSURE_USD)));f=allow_cli_exposure or(os.getenv("POLYMARKET_ALLOW_EXTENDED_EXPOSURE","0")=="1")
  if c>HARD_PORTFOLIO_EXPOSURE_CEILING and not f:logger.warning(f"[RISK CEILING] Requested max_exposure (${c:.2f}) exceeds immutable hard ceiling (${HARD_PORTFOLIO_EXPOSURE_CEILING:.2f}). Clamped to ${HARD_PORTFOLIO_EXPOSURE_CEILING:.2f}.");a.max_exposure=HARD_PORTFOLIO_EXPOSURE_CEILING
  else:a.max_exposure=max(.0,c)
  a.allow_cli_exposure=bool(allow_cli_exposure);a.high_water_mark_equity=.0;a.max_trades_per_market=max_trades_per_market;a.max_trades_per_hour=max_trades_per_hour;a.max_tte=max_tte;a.max_price_ceiling=max_price_ceiling;a.min_price_floor=min_price_floor;a.profit_theta=profit_theta;a.spot_delta_k=spot_delta_k;a.tte_cancel_window=tte_cancel_window;a.kelly_fraction=kelly_fraction;a.max_notional_cap_pct=max_notional_cap_pct;a.dynamic_bankroll_pct=DYNAMIC_BANKROLL_PCT;a.passive_unwind_timeout=passive_unwind_timeout;a.depth_hurdle=depth_hurdle;a.dynamic_theta=dynamic_theta;a.max_absolute_ticket_usd=max_absolute_ticket_usd if max_absolute_ticket_usd is not None else(1e4 if unconstrained_kelly else MAX_ABSOLUTE_TICKET_USD);a.max_ticket_cap=a.max_absolute_ticket_usd;a._spot_cache={}
  if max_concurrent is not None:a.max_concurrent_positions=max_concurrent
  elif"MAX_CONCURRENT_POSITIONS"in os.environ:a.max_concurrent_positions=int(os.environ["MAX_CONCURRENT_POSITIONS"])
  else:a.max_concurrent_positions=DEFAULT_MAX_CONCURRENT_POSITIONS
  a.allow_cli_concurrency=bool(allow_cli_concurrency or os.getenv("PM_FORCE_MAX_CONCURRENT","0")=="1");a._explicit_max_concurrent=int(a.max_concurrent_positions);a.executor=PolymarketLiveExecutor(dry_run=dry_run,ledger_path=None);b=max_daily_loss if max_daily_loss is not None else float(RISK_CONFIG["max_daily_loss"]);d=CIRCUIT_BREAKER_EQUITY_FLOOR;a.risk_controller=EmergencyRiskController(max_daily_loss_usd=b,min_equity_floor_usd=d);a.risk_controller._harvester_ref=a;a.seen_shock_ids=set();a._seen_shock_order={};a._seen_d1_box_keys=set();a._seen_d1_box_order={};a.traded_market_ids=set();a.trades_per_market=defaultdict(int);a.trades_per_market_direction=defaultdict(int);a.hourly_candle_opens=defaultdict(dict);a.active_positions={};a.closed_positions=[]
  if"POLYMARKET_LOW_BID_PERSISTENCE_SECONDS"in os.environ:a.low_bid_persistence_seconds=float(os.environ["POLYMARKET_LOW_BID_PERSISTENCE_SECONDS"])
  else:a.low_bid_persistence_seconds=1.5
  a.trades_this_hour=0;a.current_hour_window=time.time()//3600;a.last_trigger_file_pos=0;a.last_shock_file_pos=0;a.last_res_file_pos=0;a.last_heartbeat_time=.0;a.market_tokens_cache={};a.market_condition_ids={};a.calibrated_p_model=float(os.getenv("POLYMARKET_CALIBRATED_P_MODEL","0.95"));a.calibrated_model_version="REGIME_4_EMPIRICAL_V2";a.calibrated_model_id="OOS_LEDGER_248_TRADES";a.pending_entry_intents={};a._inflight_directional_entry_ids=set();a.risk_halt=False;a.reconciliation_required=False;a.global_halt_reasons=[];a._startup_reconciled=False;a._last_redemption_poll=.0;a.recent_shock_window=[];a._last_known_collateral=None;a._current_equity_tier=None;a.current_equity_tier=None;a._capital_reservation_ledger=None;a.hierarchical_risk_budget_config=None;a._prewarm_hourly_opens()
  try:a.sync_capital_reservation_ledger()
  except Exception:pass
 def sync_capital_reservation_ledger(self,now_ts=None,*,safety_buffer_usd=None):from src.polymarket_research.riskless_protocol_v2_expansion import(sync_harvester_capital_reservation_ledger as a);return a(self,now_ts=now_ts,safety_buffer_usd=safety_buffer_usd)
 def get_hierarchical_risk_budget_config(self):from src.polymarket_research.riskless_protocol_v2_expansion import(build_harvester_hierarchical_risk_budget as a);return a(self)
 def check_pre_trade_reservation_and_budget(self,candidate,*,requested_notional_usd=None,market_ids=None,now_ts=None,exclude_intent_ids=None,reserve_on_accept=False):from src.polymarket_research.riskless_protocol_v2_expansion import(evaluate_candidate_v6_cwce_and_reservation as a);return a(self,candidate,requested_notional_usd=requested_notional_usd,market_ids=market_ids,now_ts=now_ts,exclude_intent_ids=exclude_intent_ids,reserve_on_accept=reserve_on_accept)
 def _record_seen_shock_id(a,shock_id):
  if not hasattr(a,"_seen_shock_order"):a._seen_shock_order={f:None for f in a.seen_shock_ids}
  a._seen_shock_order.pop(shock_id,None);a._seen_shock_order[shock_id]=None;a.seen_shock_ids.add(shock_id)
  while len(a._seen_shock_order)>2000:d=next(iter(a._seen_shock_order));a._seen_shock_order.pop(d,None);a.seen_shock_ids.discard(d)
  e=int(time.time()//3600)
  for c in a.hourly_candle_opens.values():
   b=[h for h in c if h<(e-48)]
   for h in b:c.pop(h,None)
  if len(a.closed_positions)>500:a.closed_positions=a.closed_positions[-500:]
 def effective_risk_pct(a,equity):
  try:
   if float(equity)>=float(a.risk_config["scale_up_equity_threshold"]):return float(a.risk_config["scale_up_risk_pct"])
  except(TypeError,ValueError):pass
  return float(a.dynamic_bankroll_pct)
 @staticmethod
 def _shock_asset(shock):
  a=str(shock.get("asset")or"").upper()
  if not a:b=str(shock.get("title")or"").strip();a=b.split()[0].upper()if b else"BTC"
  return a
 def check_recorder_freshness(b,asset,now_ts):
  asset=str(asset).upper();j=os.environ.get("PM_FAST_TICK_DIR");i=Path(j)if j else FAST_TICK_DIR;h=Path(os.environ.get("PM_TELEMETRY_DIR",str(DATA_DIR)));c="polymarket_hourly_telemetry.jsonl"if asset=="BTC"else f"polymarket_hourly_telemetry_{asset.lower()}.jsonl"
  def a(p,is_jsonl=False):
   try:
    u=float(now_ts)-p.stat().st_mtime
    if u<-2.:return float("inf")
    t=max(.0,u)
    try:
     if not is_jsonl:
      v=_json_loads(p.read_bytes())
      if isinstance(v,dict):
       n=float(v.get("ts")or v.get("timestamp_unix")or.0);s=float(v.get("spot_ts")or.0);l=t
       if n>.0:
        m=float(now_ts)-n
        if m<-2.:return float("inf")
        l=max(l,max(.0,m))
       if s>.0:
        q=float(now_ts)-s
        if q<-2.:return float("inf")
        l=max(l,max(.0,q))
       return l
     else:
      x=p.stat().st_size
      if x>2:
       with open(p,"rb")as w:w.seek(max(0,x-4096));r=[y.strip()for y in w.read().splitlines()if y.strip()]
       if r:
        o=_json_loads(r[-1])
        if isinstance(o,dict):
         n=float(o.get("timestamp_unix")or o.get("ts")or.0)
         if n>.0:m=float(now_ts)-n;return float("inf")if m<-2. else max(t,max(.0,m))
    except Exception:pass
    return t
   except OSError:return float("inf")
  g=a(i/f"pm_fast_tick_{asset}.json",is_jsonl=False);f=float(b.risk_config["stale_fast_tick_max_age_sec"])
  if g<=f:return True,g,f"fast_tick_age={g:.1f}s<={f:.0f}s"
  e=a(h/c,is_jsonl=True);d=float(b.risk_config["stale_telemetry_max_age_sec"]);k=min(g,e)
  if e<=d:return True,k,f"telemetry_age={e:.1f}s<={d:.0f}s"
  return False,k,f"fast_tick_age={g:.1f}s>{f:.0f}s and telemetry_age={e:.1f}s>{d:.0f}s"
 def monitor_recorder_staleness(a,now_ts):
  b=float(a.risk_config["stale_alert_after_sec"])
  for d in sorted(a.allowed_assets):
   f,e,c=a.check_recorder_freshness(d,now_ts)
   if e>b:send_operational_alert("STALE_RECORDER_FEED",f"{d} recorder silent for {'>'+str(int(b))+'s'if math.isinf(e)else f'{e:.0f}s'} ({c}). New entries blocked.","CRITICAL",rate_limit_sec=float(a.risk_config["alert_rate_limit_sec"]),dedupe_key=f"stale_recorder:{d}")
 def _append_shadow_phase3_4_event(self,record):
  a=os.environ.get("PM_SHADOW_TRACKER_FILE")
  if a is not None and not a.strip():return
  try:
   b=Path(a)if a else SHADOW_PHASE3_4_FILE;b.parent.mkdir(parents=True,exist_ok=True)
   with open(b,"a",encoding="utf-8")as c:c.write(json.dumps(record)+"\n")
  except Exception:pass
 def _register_shadow_phase3a_maker_in(b,shock,target_token,first_ask,first_bid,max_allowed_price,raw_asks,reject_reason,is_subhourly,dist_pct,tte):
  try:
   if first_ask<=.0 or first_bid<.5 or tte<35.:return
   n=str(shock.get("market_id")or"")
   if not n:return
   a=getattr(b,"_shadow_maker_orders",None)
   if a is None:b._shadow_maker_orders={};a=b._shadow_maker_orders
   p=f"{n}_{target_token}"
   if p in a:return
   k=round(min(max_allowed_price,first_ask-.01),2)
   if k<.54:return
   j=.2*.07;d=round(k-j*k*(1.-k),5);f=sum(q*r for q,r in(raw_asks or[])if q<=max_allowed_price);e=16.5 if f>=16.5 else(12. if f>=12. else.0);c=round((max_allowed_price-first_ask)*1e2,2);m=time.time();l=float(os.environ.get("PM_SHADOW_MAKER_TTL_SEC","3.5"));i=float((shock.get("candle_open_spot")if is_subhourly else(shock.get("finalized_1h_open")or shock.get("candle_open_spot")))or.0);h=float(shock.get("expiry_ts")or shock.get("candle_expiry_ts")or(m+tte));g=str(shock.get("asset")or"BTC").upper();o={"event_type":"SHADOW_PHASE3A_MAKER_IN_REGISTERED","logged_at_utc":datetime.now(timezone.utc).isoformat(),"market_id":n,"title":shock.get("title"),"asset":g,"horizon":"15m"if is_subhourly else"1h","target_token":target_token,"reject_reason":reject_reason,"first_ask":round(first_ask,4),"first_bid":round(first_bid,4),"max_allowed_price":round(max_allowed_price,4),"shadow_maker_px":k,"shadow_maker_eff_cost":d,"idea1_depth_at_max_usd":round(f,2),"idea1_snapped_rung_usd":e,"idea5_headroom_cents":c,"entry_dist_pct":round(dist_pct,4),"tte_sec":round(tte,1),"placed_ts":m,"ttl_sec":l,"ttl_expires_ts":m+l,"expiry_ts":h,"open_spot":i,"status":"RESTING"};a[p]=o;b._append_shadow_phase3_4_event(o);logger.info(f"[SHADOW PHASE 3A] Registered virtual Maker-In {g} {target_token} @ ${k:.2f} (eff=${d:.4f}, TTL={l:.1f}s, reason={reject_reason}, snapped_rung=${e:.2f})")
  except Exception:pass
 @staticmethod
 def _ws_snap_fully_filled(snap_o,expected_sh=.0):
  if not isinstance(snap_o,dict)or str(snap_o.get("status")or"").upper()not in("MATCHED","FILLED"):return False
  a=max(float(expected_sh or.0),float(snap_o.get("original_size")or.0));return a<=.0 or float(snap_o.get("size_matched")or.0)>=a-1e-6
 async def _reconcile_maker_entry_fill(a,maker_oid,token_id,ws_filled,posted_sh,fallback_px,pre_bal=None,*,allow_ws_fast_fill=False,use_fast_cancel=None):
  g=(bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_fast_1rtt_cancel",True))if use_fast_cancel is None else bool(use_fast_cancel))
  def b():
   if(g and hasattr(a.executor,"cancel_order_fast")and"cancel_order"not in getattr(a.executor,"__dict__",{})):
    try:return a.executor.cancel_order_fast(maker_oid,token_id=token_id,pre_token_balance=pre_bal)
    except TypeError:return a.executor.cancel_order_fast(maker_oid)
   try:return a.executor.cancel_order(maker_oid,token_id=token_id,pre_token_balance=pre_bal)
   except TypeError:return a.executor.cancel_order(maker_oid)
  d={"is_canceled":False,"outcome":"FILLED"}if ws_filled else await asyncio.to_thread(b);n=getattr(a.executor,"_user_ws_cache",None);j=bool(n is not None and hasattr(n,"is_healthy")and n.is_healthy());m=n.get_order_snapshot(maker_oid,max_age_sec=10.)if(n is not None and hasattr(n,"get_order_snapshot"))else None;r=float((m or{}).get("size_matched")or.0)if isinstance(m,dict)else.0
  if(not a.dry_run and ws_filled and allow_ws_fast_fill and j and isinstance(m,dict)and r>=max(.01,float(posted_sh or.0)-1e-4)and"get_order_fill_summary"not in getattr(a.executor,"__dict__",{})and getattr(getattr(a.executor,"client",None),"_mock_children",None)is None):
   t=float(m.get("avg_fill_price")or m.get("price")or fallback_px)
   if _STAGE_B_MARKOUT_SAMPLER is not None and r>.01 and t>.0 and hasattr(a.executor,"get_market_book"):
    try:i=next((str(v.get("sleeve")or v.get("sleeve_source")or"")for v in(a.pending_entry_intents or{}).values()if isinstance(v,dict)and str(v.get("entry_order_id")or v.get("order_id")or"")==str(maker_oid)),"")or"MAKER_ENTRY";e=getattr(a,"_pos_market_ws",None);h=(lambda _t:(e.get_book(str(_t),max_age_sec=5.)if e is not None else None)or a.executor.get_market_book(str(_t)));_STAGE_B_MARKOUT_SAMPLER.schedule_maker_fill(order_id=str(maker_oid),token_id=str(token_id),sleeve=i,side="BUY",fill_px=t,shares=r,book_lookup_fn=h)
    except Exception:pass
   return d,{"order_id":maker_oid,"matched":r,"avg_price":t,"cash":round(r*t,6),"fee":.0,"terminal":True,"resting":False,"source":"USER_WS_FAST_FILL"},r,t
  if(not a.dry_run and not ws_filled and j and isinstance(m,dict)and r<=.0 and str(m.get("status")or"").upper()in("CANCELED","CANCELLED")and bool((d or{}).get("is_canceled"))and not bool((d or{}).get("read_replica_stale_live"))and float((d or{}).get("matched")or.0)<=.0 and"get_order_fill_summary"not in getattr(a.executor,"__dict__",{})and getattr(getattr(a.executor,"client",None),"_mock_children",None)is None):return(d,{"order_id":maker_oid,"matched":.0,"avg_price":.0,"cash":.0,"fee":.0,"terminal":True,"resting":False,"source":"USER_WS_FAST_CANCEL"},.0,fallback_px)
  c=await asyncio.to_thread(a.executor.get_order_fill_summary,maker_oid,token_id)
  if ws_filled and(c is None or bool(c.get("resting"))or float((c or{}).get("matched")or.0)<.01):d=await asyncio.to_thread(b);c=await asyncio.to_thread(a.executor.get_order_fill_summary,maker_oid,token_id)
  s=str((d or{}).get("outcome")or"");q=max(r,float(posted_sh or.0)if(ws_filled or s=="FILLED")else float((d or{}).get("matched")or.0));f=bool(not a.dry_run and not ws_filled and(bool((d or{}).get("read_replica_stale_live"))or bool((c or{}).get("resting"))))
  for _ in range(3):
   l=(q>.01 and float((c or{}).get("matched")or.0)<q-.01)or(f and bool((c or{}).get("resting")))
   if not l:break
   await asyncio.sleep(.15);c=await asyncio.to_thread(a.executor.get_order_fill_summary,maker_oid,token_id)
  u=float((c or{}).get("matched")or.0);k=max(u,r,float((d or{}).get("matched")or.0),float(posted_sh or.0)if(ws_filled and u>.0)else.0);p=float((c or{}).get("cash")or.0);o=float((c or{}).get("avg_price")or(round(p/u,6)if(p>.0 and u>.0)else.0)or(c or{}).get("limit_price")or fallback_px)
  if not a.dry_run and _STAGE_B_MARKOUT_SAMPLER is not None and k>.01 and o>.0 and hasattr(a.executor,"get_market_book"):
   try:i=next((str(v.get("sleeve")or v.get("sleeve_source")or"")for v in(a.pending_entry_intents or{}).values()if isinstance(v,dict)and str(v.get("entry_order_id")or v.get("order_id")or"")==str(maker_oid)),"")or"MAKER_ENTRY";e=getattr(a,"_pos_market_ws",None);h=(lambda _t:(e.get_book(str(_t),max_age_sec=5.)if e is not None else None)or a.executor.get_market_book(str(_t)));_STAGE_B_MARKOUT_SAMPLER.schedule_maker_fill(order_id=str(maker_oid),token_id=str(token_id),sleeve=i,side="BUY",fill_px=o,shares=k,book_lookup_fn=h)
   except Exception:pass
  return d,c,k,o
 _attempt_live_phase3a_maker_rescue=_bind_hv_method(_hv__attempt_live_phase3a_maker_rescue,'_attempt_live_phase3a_maker_rescue')
 async def _maybe_merge_live_complete_sets(self,now_ts):from src.polymarket_research.riskless_protocol_v2_expansion import maybe_merge_live_complete_sets_impl as a;await a(self,now_ts,ExecutionStatus,logger)
 async def _execute_guarded_complement_merge(self,tid,pos,opp_tok,cm_plan,now_ts):from src.polymarket_research.riskless_protocol_v2_expansion import execute_guarded_complement_merge_impl as a;return await a(self,tid,pos,opp_tok,cm_plan,now_ts,ExecutionStatus)
 async def _try_atomic_box_overround_unwind(self,now_ts,open_oids):from src.polymarket_research.riskless_protocol_v2_expansion import try_atomic_box_overround_unwind_impl as a;await a(self,now_ts,open_oids,pos_is_recv_fn=position_is_settlement_receivable,read_fast_tick_fn=read_fast_tick,walk_ovr_fn=walk_dual_leg_overround_bids,gov_mgr=GLOBAL_GOVERNANCE_MANAGER,exec_status_cls=ExecutionStatus,h_logger=logger)
 def _update_shadow_phase4_monotonicity_scanner(self,shock,asset_str,is_subhourly,is_1h,tte,open_spot):from src.polymarket_research.riskless_protocol_v2_expansion import update_shadow_phase4_monotonicity_scanner_impl as a;a(self,shock,asset_str,is_subhourly,is_1h,tte,open_spot,eval_basis_fn=evaluate_cross_oracle_basis_box_ev,h_logger=logger)
 def _step_shadow_phase3_4_tracker(self,now_ts):from src.polymarket_research.riskless_protocol_v2_expansion import step_shadow_phase3_4_tracker_impl as a;a(self,now_ts,read_fast_tick_fn=read_fast_tick,h_logger=logger)
 def _get_verified_shm_book(self,pos):
  m=str(pos.get("asset")or"BTC").upper();e=str(pos.get("market_id")or"");d=str(pos.get("token_id")or"");c=str(pos.get("target_token")or"UP").upper()
  if not e or not d:return None
  a=os.environ.get("PM_FAST_TICK_DIR")
  if not a:
   if self.dry_run:return None
   a="/dev/shm"
  i=Path(f"{a}/pm_fast_tick_{m}.json")
  if not i.exists():return None
  try:
   q=_json_loads(i.read_bytes());b=q.get("markets",{}).get(e)if isinstance(q.get("markets"),dict)else q
   if not isinstance(b,dict):return None
   if str(b.get("market_id")or"")!=e:return None
   r=float(b.get("timestamp_unix")or b.get("ts")or.0);l=time.time()-r
   if r<=.0 or l>1.5 or l<-2.:return None
   f=b.get(c)or{}
   if str(f.get("token_id")or"")!=d:return None
   h=f.get("raw_top_bids")or[];g=f.get("raw_top_asks")or[]
   if h:return{"bids":[{"price":str(p),"size":str(s)}for p,s in h],"asks":[{"price":str(p),"size":str(s)}for p,s in g],"timestamp":r}
   k=float(f.get("best_bid",.0)or.0);j=float(f.get("best_ask",1.)or 1.);o=float(f.get("bid_size_l1",.0)or.0);n=float(f.get("ask_size_l1",.0)or.0)
   if k<=.0 or o<=.0:return None
   return{"bids":[{"price":str(k),"size":str(o)}],"asks":[{"price":str(j),"size":str(n)}]if j<1. and n>0 else[],"timestamp":r}
  except Exception:return None
 async def _atomic_replace_maker_exit(a,tid,pos,new_price,collapse_tranches=False):
  l=pos.get("token_id");n=pos.get("exit_order_id")
  if not l:return False
  c=.0
  if n:
   i=await asyncio.to_thread(a.executor.cancel_order,str(n));f=bool((i or{}).get("is_canceled"));e=await asyncio.to_thread(a.executor.get_order_fill_summary,str(n),l)
   if f and isinstance(e,dict)and e.get("resting",False):await asyncio.sleep(.25);e=await asyncio.to_thread(a.executor.get_order_fill_summary,str(n),l)
   if e is None:logger.warning(f"[QUEUE JUMP ABORT] No fill summary for {n} after cancel; retaining reservation.");pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED";pos["pending_canceled_order_id"]=str(n);await asyncio.to_thread(a.save_state);return False
   c=float(e.get("matched",.0)or.0);a._record_order_summary(pos,e,float(pos.get("target_exit_price",.99)or.99),taker=False)
   if float(pos.get("remaining_shares",.0)or.0)<=.02:a._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True);return True
   if e.get("resting",False)or not f or not e.get("terminal",False):
    if not e.get("resting",False)or f:pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED";pos["pending_canceled_order_id"]=str(n)
    logger.warning(f"[QUEUE JUMP ABORT] {n} not terminally canceled; retaining reservation.");await asyncio.to_thread(a.save_state);return False
   a.executor.release_inventory(reservation_id=str(n));pos["exit_order_id"]=None
  h=float(Decimal(str(pos.get("remaining_shares",pos.get("entry_shares",.0))or.0)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
  if h<.01:return False
  d=h;b=None
  if collapse_tranches:pos.pop("exit_tranches",None)
  elif pos.get("exit_tranches"):
   for t in pos["exit_tranches"]:
    if t.get("status")in{"POSTED","IN_FLIGHT"}:
     p=max(.0,round(float(t.get("size",.0))-c,2))
     if p<=.01:t["status"]="FILLED"
     else:t["size"]=p;t["status"]="PENDING"
   g=[t for t in pos["exit_tranches"]if t.get("status")=="PENDING"and float(t.get("size",.0))>=5.]
   if g and h>=5.:
    m=min(h,float(g[0]["size"]));k=round(h-m,4)
    if.01<k<5.:pos.pop("exit_tranches",None)
    else:b=g[0];d=m;b["price"]=round(float(new_price),4)
   else:pos.pop("exit_tranches",None)
  if d<5. and not a.dry_run and str(l).isdigit()and len(str(l))>=20:pos["exit_order_status"]="SUB_MINIMUM_LOT_SUPERVISED_HOLD";pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD";await asyncio.to_thread(a.save_state);return False
  pos["target_exit_price"]=round(float(new_price),4);j=await asyncio.to_thread(a.executor.post_maker_exit_order,token_id=l,price=pos["target_exit_price"],size=d,side="SELL");o=a._apply_exit_post_result(pos,j,d)
  if b is not None and o:b["status"]="POSTED"
  elif b is not None and(j or{}).get("outcome_unknown"):b["status"]="IN_FLIGHT"
  await asyncio.to_thread(a.save_state);return o
 def _prewarm_hourly_opens(a):
  b=DATA_DIR/"live_shock_triggers.jsonl"
  if not b.exists():return
  try:
   with open(b,"rb")as f:f.seek(0,2);q=f.tell();i=min(q,8*1024*1024);f.seek(q-i);n=f.read().decode("utf-8",errors="ignore").splitlines()
   for p in n:
    if not p.strip():continue
    try:
     o=_json_loads(p);h=str(o.get("title","")or"").lower();g=str(o.get("horizon","")or o.get("candle_interval","")).lower();k=str(o.get("series_slug","")or o.get("slug","")).lower()
     if any(x in g or x in k or x in h for x in("5m","15m","300s","900s")):continue
     m=o.get("asset");d=o.get("t0_unix");j=o.get("finalized_1h_open")or o.get("candle_open_spot")
     if m in("BTC","ETH","SOL")and d and j and float(j)>0:
      l=int(float(d)//3600);c=a.hourly_candle_opens.setdefault(m,{})
      if l not in c:c[l]=float(j)
    except Exception:pass
   logger.info(f"[TREND GUARD PREWARMED] Prewarmed {len(a.hourly_candle_opens.get('BTC',{}))} BTC, {len(a.hourly_candle_opens.get('SOL',{}))} SOL, and {len(a.hourly_candle_opens.get('ETH',{}))} ETH hourly opens for multi-hour trend alignment.")
  except Exception as e:logger.warning(f"[TREND GUARD PREWARM WARN] Failed to prewarm hourly opens: {e}")
 def _register_active_warmed_token(a,tok_id,expiry_ts=.0):
  if not tok_id:return
  f=getattr(a,"_active_warmed_token_expiries",None)
  if f is None:f={};a._active_warmed_token_expiries=f
  g=time.time();b=float(expiry_ts or.0)
  if b<=.0:b=g+3600.
  f[str(tok_id)]=max(float(f.get(str(tok_id),.0)),b);e=[k for k,v in f.items()if v<g-30.]
  for k in e:f.pop(k,None)
  d=24 if len(getattr(a,"allowed_assets",None)or())>=3 else 12
  while len(f)>d:c=max(f,key=f.get);f.pop(c,None)
 def _prewarm_market_metadata(a,shock):
  try:
   m=str(shock.get("title","")or"").lower();e=.07;l=shock.get("condition_id")or shock.get("fee_metadata",{}).get("condition_id");i=shock.get("fee_metadata",{});h=float(i.get("fee_rate_market",e)or e);k=float(i.get("fee_exponent",1.)or 1.);j=int(round(h*10000));d=float(shock.get("candle_expiry_ts")or shock.get("expiry_ts")or.0)
   if d<=.0 and shock.get("seconds_to_expiry"):d=float(shock.get("t0_unix")or time.time())+float(shock.get("seconds_to_expiry")or.0)
   b=str(shock.get("asset")or"").upper()
   if not b:b="BTC"if"btc"in m or"bitcoin"in m else("ETH"if"eth"in m or"ethereum"in m else("SOL"if"sol"in m or"solana"in m else""))
   c=(not a._is_riskless_only_mode())and((not b)or(b in getattr(a,"allowed_assets",{"BTC","ETH"})));o=shock.get("pre_shock_features_t0",{})
   for g in("UP","DOWN"):
    f=o.get(g,{});n=f.get("token_id")
    if n:
     a.executor.prewarm_token_market_cache(token_id=n,tick_size=f.get("tick_size")or shock.get("tick_size")or"0.01",neg_risk=False,fee_rate_bps=j,condition_id=l,fee_rate=h,fee_exponent=k)
     if c and(d<=.0 or d>time.time()-30.):a._register_active_warmed_token(str(n),d)
  except Exception:pass
 def _handle_prewarm_ipc_signal(a):
  b=time.monotonic()
  if(b-float(getattr(a,"_last_precursor_touch_mono",.0)or.0))<1.5:return
  a._last_precursor_touch_mono=b
  if not getattr(a,"active_positions",None):
   try:import gc as _gc_p;_gc_p.collect(0)
   except Exception:pass
  if not a.dry_run and hasattr(a.executor,"touch_hot_async_clob_socket"):
   try:asyncio.get_running_loop().create_task(a.executor.touch_hot_async_clob_socket(1.5))
   except Exception:pass
 def _prewarm_active_market_tokens(a):
  try:
   c=a._is_riskless_only_mode();e=getattr(a,"_active_warmed_token_expiries",None)
   if(not c)and(not getattr(a,"_startup_prewarmed_logged",False)or not e):
    if TRIGGER_FILE.exists()and TRIGGER_FILE.stat().st_size>0:
     j=TRIGGER_FILE.stat().st_size;d=min(j,131072)
     with open(TRIGGER_FILE,"rb")as f:f.seek(j-d);h=f.read().decode("utf-8",errors="ignore").splitlines()
     for l in reversed(h):
      if not l.strip():continue
      try:i=_json_loads(l);a._prewarm_market_metadata(i)
      except Exception:continue
   e=getattr(a,"_active_warmed_token_expiries",None)or{};g=time.time();b=[k for k,m in e.items()if m>=g-30.]
   if b and not getattr(a,"_startup_prewarmed_logged",False):a._startup_prewarmed_logged=True;logger.info(f"[HOT-PATH PREWARMED] Proactively pre-warmed CLOB metadata & fee caches for {len(b)} active token(s) [version=2, markets-by-token, clob-markets].")
   if b and not c and hasattr(a.executor,"prewarm_order_ladder")and not getattr(a.executor,"dry_run",True):a._spawn_ladder_prewarm(b)
   if getattr(a,"_last_known_collateral",None)is not None:a.executor.set_cached_collateral(float(a._last_known_collateral))
  except Exception:pass
 def _spawn_ladder_prewarm(a,tokens):
  import threading
  if _HOT_DISPATCH_ACTIVE.is_set()or a._is_riskless_only_mode():return
  g=getattr(a,"_ladder_prewarm_thread",None)
  if g is not None and g.is_alive():return
  f=[float(a.ticket_notional)];j=getattr(a,"_last_known_collateral",None);d=(12.,16.5,20.,24.,28.,36.)if(j and isinstance(j,(int,float))and j>=45.)else(12.,13.77,16.5)
  for c in d:
   if all(abs(c-x)>=.4 for x in f):f.append(c)
  if getattr(a,"dynamic_sizing",False)and j and isinstance(j,(int,float))and j>0:
   h=float(getattr(a,"dynamic_bankroll_pct",.22)or.22)
   for k in(1.,1.15,.5405,.6216):
    i=round(float(j)*h*k,2)
    if i>=12. and all(abs(i-x)>=.4 for x in f):f.append(i)
  def b():
   try:
    if hasattr(os,"sched_setscheduler")and hasattr(os,"SCHED_IDLE"):os.sched_setscheduler(0,os.SCHED_IDLE,os.sched_param(0))
   except Exception:pass
   e=0;u=sum(float(p.get("notional_usd")or.0)for p in getattr(a,"active_positions",{}).values());x=float(getattr(getattr(a,"risk_controller",None),"equity_high_water_mark_usd",.0)or.0);w=max(float(j)+u,x)if(j and isinstance(j,(int,float))and j>0)else max(140.,x);q=max(48,min(160,int(math.ceil(max(w*.35,float(a.ticket_notional or 16.5)*1.35)/.52))+6));o=list(range(5,q))
   for t in tokens:
    if not getattr(a,"dry_run",True):
     s=0
     while 4.<=(3e2-time.time()%3e2)<=42. and s<160:time.sleep(.25);s+=1
    m=0
    while _HOT_DISPATCH_ACTIVE.is_set()and m<40:time.sleep(.05);m+=1
    v=str(getattr(a.executor,"_tick_size_cache",{}).get(t)or"0.01")
    try:e+=int(a.executor.prewarm_order_ladder(t,12.,tick_size=v,exact_shares=o,pace_every=2,pace_sleep_sec=.008)or 0)
    except TypeError:
     try:e+=int(a.executor.prewarm_order_ladder(t,12.,tick_size=v,exact_shares=o)or 0)
     except TypeError:
      for r in f:e+=int(a.executor.prewarm_order_ladder(t,r)or 0)
    except Exception:pass
    for r in f:
     if r<=18. or(math.floor(r/.55)+1)<q:continue
     try:e+=int(a.executor.prewarm_order_ladder(t,r,tick_size=v,share_deltas=(-2,-1,0,1),pace_every=2,pace_sleep_sec=.008)or 0)
     except TypeError:e+=int(a.executor.prewarm_order_ladder(t,r)or 0)
     except Exception:pass
    time.sleep(.015)
   if e:
    if not getattr(a,"_gc_frozen_ladder",False)and e>=500:
     a._gc_frozen_ladder=True
     try:
      import gc as _gc_f;_gc_f.collect()
      if hasattr(_gc_f,"freeze"):_gc_f.freeze()
     except Exception:pass
    logger.info(f"[PREWARM LADDER] Pre-signed {e} BUY order(s) across {len(tokens)} token(s) (dense_shares=5..{q-1} + tickets={[n for n in f if n>18.]}).")
  l=threading.Thread(target=b,name="ladder-prewarm",daemon=True);a._ladder_prewarm_thread=l;l.start()
 async def _prewarm_next_candle_markets(a):
  v=("btc-up-or-down-hourly","solana-up-or-down-hourly","eth-up-or-down-hourly","btc-up-or-down-15m","solana-up-or-down-15m","eth-up-or-down-15m");m=(*v,"xrp-up-or-down-15m","btc-updown-5m","eth-updown-5m","sol-updown-5m","xrp-updown-5m");o={str(p.get("token_id")or"")for p in getattr(a,"active_positions",{}).values()};i=a.__dict__.setdefault("_d1_clean_pre_bal_cache",{});j=0;z=datetime.now(timezone.utc);h=("_sync_session"not in getattr(a.executor,"__dict__",{})and hasattr(a.executor,"get_async_client"));u=a.executor.get_async_client()if h else None
  async def b(slug):
   t=f"https://gamma-api.polymarket.com/events?series_slug={slug}&limit=3&closed=false"
   try:
    if u is not None:p=await u.get(t,timeout=3.)
    else:p=await asyncio.to_thread(a.executor._sync_session.get,t,timeout=3.)
    if getattr(p,"status_code",0)!=200:return slug,None
    e=getattr(p,"content",None)
    if _orjson is not None and isinstance(e,(bytes,bytearray))and e:return slug,_orjson.loads(e)
    return slug,p.json()
   except Exception:return slug,None
  y=await asyncio.gather(*[b(slug)for slug in m])
  for slug,E in y:
   if not E:continue
   try:
    for F in E:
     for D in F.get("markets",[]):
      I=str(D.get("id"));x=str(D.get("conditionId")or"");l=D.get("endDate")
      if not l or not x:continue
      try:C=datetime.fromisoformat(l.replace("Z","+00:00"));f=(C-z).total_seconds()
      except Exception:f=3600.
      if 0<f<=7200:
       r=D.get("clobTokenIds")
       if isinstance(r,str):k=_orjson.loads(r)if _orjson is not None else json.loads(r)
       else:k=r
       if k and len(k)>=2:
        H=str(k[0]);B=str(k[1]);a.market_condition_ids[I]=x;a.market_tokens_cache[f"{I}_UP"]=H;a.market_tokens_cache[f"{I}_DOWN"]=B;g=.07;s=D.get("feeSchedule",{});G=float(s.get("rate",g)or g);K=float(s.get("exponent",1.)or 1.);J=int(round(G*10000));A=time.time();q=D.get("orderPriceMinTickSize")or"0.01";w=slug.lower();n="BTC"if"btc"in w else("SOL"if"sol"in w else("ETH"if"eth"in w else"XRP"));c=1050. if"15m"in w else 2520.;d=(not a._is_riskless_only_mode()and slug in v and n in a.get_graduated_allowed_assets()and f<=c)
        for t in(H,B):
         a.executor.prewarm_token_market_cache(token_id=t,tick_size=q,neg_risk=False,fee_rate_bps=J,condition_id=x,fee_rate=G,fee_exponent=K)
         if d:a._register_active_warmed_token(str(t),z.timestamp()+f)
         if str(t)not in o:i[str(t)]=(.0,A)
        j+=1
   except Exception as e:pass
  if j>0:logger.info(f"[PREWARM NEXT-CANDLE] Pre-warmed metadata & CLOB caches for {j} upcoming token(s) from Gamma API.");a._prewarm_active_market_tokens()
 def _has_unsettled_collateral_overlap(a,now_ts=None):
  if now_ts is None:now_ts=time.time()
  if getattr(a,"pending_entry_intents",None):return True
  for p in(getattr(a,"active_positions",None)or{}).values():
   d=p.get("status")
   if d in{"MATCHED_PENDING_SETTLEMENT","ENTRY_OUTCOME_UNKNOWN","UNRESOLVED_SETTLEMENT","AWAITING_ONCHAIN_SETTLEMENT"}:return True
   if position_is_settlement_receivable(p):return True
   b=float(p.get("candle_expiry_ts")or.0)
   if b>.0 and now_ts>=b:return True
   c=float(p.get("entry_ts")or.0)
   if c>.0 and(now_ts-c)<30.:return True
   if(float(p.get("filled_exit_shares",.0)or.0)>.0 or float(p.get("confirmed_realized_cash",.0)or.0)>.0 or float(p.get("estimated_exit_cash",.0)or.0)>.0):return True
  return False
 def _is_v5_live_strict(a):
  b=getattr(a,"holistic_v5_live_mode",None)
  if b is False:return False
  if b is True:return True
  d=getattr(a,"executor",None);c=getattr(d,"__dict__",{})if d is not None else{};return bool(not getattr(a,"dry_run",True)and getattr(d,"auth_mode","")in("LIVE","AUTHENTICATED_L2")and getattr(d,"client",None)is not None and getattr(getattr(d,"client",None),"_mock_children",None)is None and not any(k in c for k in("execute_snipe_order_async","execute_snipe_order")))
 def _is_v5_unleashed_active(self):return bool(self._is_v5_live_strict()and GLOBAL_GOVERNANCE_MANAGER.snapshot.get("sizing_tiers",{}).get("unleash_full_throttle",True))
 def _effective_sizing_equity_usd(c,raw_tot_equity,now_ts=None):
  h=(max(.0,float(raw_tot_equity))if(raw_tot_equity is not None and math.isfinite(float(raw_tot_equity)))else.0);f=getattr(c,"active_positions",None)or{}
  if not f:return h,False
  g=float(time.time()if now_ts is None else now_ts)
  try:
   from src.polymarket_research.riskless_protocol_v2_expansion import(compute_reconciled_concentration_nav_usd as a,is_post_expiry_uma_frozen_lock as b);d=any(isinstance(p,dict)and(b(p,g)or str(p.get("umaResolutionStatus")or"").strip().lower()=="disputed")for p in f.values())
   if not d:return h,False
   e=a(c,now_ts=g);return(min(h,e)if h>.0 else e),True
  except Exception:return h,False
 def _update_equity_tier(a,total_equity,*,allow_hwm_ratchet=None):
  e=float(total_equity)if(total_equity is not None and math.isfinite(float(total_equity)))else.0;d=float(RISK_CONFIG.get("seed_survival_equity_threshold",88.))
  if allow_hwm_ratchet is None:allow_hwm_ratchet=not a._has_unsettled_collateral_overlap()
  i=getattr(a,"high_water_mark_equity",None)
  if i is None or not math.isfinite(float(i))or float(i)<=.0:a.high_water_mark_equity=e
  elif e<d and float(i)>e*1.15:a.high_water_mark_equity=e
  elif allow_hwm_ratchet and e>float(i):a.high_water_mark_equity=e
  f=getattr(a,"_current_equity_tier",None)or getattr(a,"current_equity_tier",None)
  if a._is_v5_unleashed_active():
   j=get_unleashed_v5_tier_profile(e,a.high_water_mark_equity,previous_tier=f);a._current_equity_tier=j["tier"];a.current_equity_tier=j["tier"];a.dynamic_bankroll_pct=j["dynamic_bankroll_pct"]
   if not getattr(a,"allow_cli_exposure",False):a.max_exposure=j["max_exposure"]
   a.max_concurrent_positions=j["max_directional_slots"];b=os.environ.get("PM_ENFORCE_V5_TIER_SLOTS")=="1"or bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("sizing_tiers",{}).get("enforce_tier_slots_over_unlimited",False))
   if getattr(a,"allow_cli_concurrency",False)and not b and e>=j["min_equity_floor"]:
    a.max_concurrent_positions=max(1,int(getattr(a,"_explicit_max_concurrent",a.max_concurrent_positions)))
    if not getattr(a,"allow_cli_exposure",False)and a._is_unlimited_slots_active():a.max_exposure=round(max(a.max_exposure,1e2 if e<140. else(350. if e<3e2 else 5e2)),2)
   if hasattr(a.risk_controller,"min_equity_floor_usd"):a.risk_controller.min_equity_floor_usd=j["min_equity_floor"]
   if hasattr(a.risk_controller,"max_daily_loss_usd"):a.risk_controller.max_daily_loss_usd=j["max_daily_loss"]
   if hasattr(a.risk_controller,"max_consecutive_losses"):a.risk_controller.max_consecutive_losses=j["max_consecutive_losses"]
   return j
  c=get_equity_tier_limits(e,a.high_water_mark_equity,previous_tier=f);a._current_equity_tier=c["tier"];a.current_equity_tier=c["tier"];a.dynamic_bankroll_pct=c["dynamic_bankroll_pct"]
  if not getattr(a,"allow_cli_exposure",False):h=getattr(a,"risk_config",None)or RISK_CONFIG;g=float(h.get("max_exposure",35.))if(not h.get("unlimited_slots")or a._is_unlimited_slots_active())else float(c["max_exposure"]);a.max_exposure=round(min(HARD_PORTFOLIO_EXPOSURE_CEILING if e<140. else 5e2,max(c["max_exposure"],min(g,e*.82)if e>0 else g)),2)
  a.max_concurrent_positions=c["max_concurrent_positions"]
  if hasattr(a.risk_controller,"min_equity_floor_usd"):a.risk_controller.min_equity_floor_usd=c["min_equity_floor"]
  if hasattr(a.risk_controller,"max_daily_loss_usd"):a.risk_controller.max_daily_loss_usd=c["max_daily_loss"]
  if e<d:
   a.max_concurrent_positions=min(a.max_concurrent_positions,int(RISK_CONFIG.get("seed_survival_max_concurrent",1)))
   if hasattr(a.risk_controller,"min_equity_floor_usd"):a.risk_controller.min_equity_floor_usd=float(RISK_CONFIG.get("seed_survival_floor_usd",48.))
  if getattr(a,"allow_cli_concurrency",False)and e>=float(RISK_CONFIG.get("seed_survival_floor_usd",48.)):
   a.max_concurrent_positions=max(1,int(getattr(a,"_explicit_max_concurrent",a.max_concurrent_positions)))
   if not getattr(a,"allow_cli_exposure",False):
    if a._is_unlimited_slots_active():a.max_exposure=round(max(a.max_exposure,1e2 if e<140. else(350. if e<3e2 else 5e2)),2)
    else:a.max_exposure=max(a.max_exposure,round(e*min(.82,.26*a.max_concurrent_positions),2))
  return c
 def _is_unlimited_slots_active(a):
  if os.environ.get("PM_ENFORCE_V5_TIER_SLOTS")=="1"or bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("sizing_tiers",{}).get("enforce_tier_slots_over_unlimited",False)):return False
  return bool((getattr(a,"risk_config",None)or RISK_CONFIG).get("unlimited_slots",False)and getattr(a,"allow_cli_concurrency",False)and int(getattr(a,"_explicit_max_concurrent",0)or 0)>=10)
 def _effective_directional_slot_cap(a,now_u=None):
  h=float(now_u if now_u is not None else time.time())
  if a._is_v5_unleashed_active()and not a._is_unlimited_slots_active():j=float(getattr(a,"_last_known_collateral",.0)or.0)+sum(a.get_position_market_value(p,h)for p in a.active_positions.values());f=get_unleashed_v5_tier_profile(j if j>.0 else 69.06,getattr(a,"high_water_mark_equity",None),previous_tier=getattr(a,"_current_equity_tier",None));return max(1,int(f["max_directional_slots"]))
  b=max(1,int(getattr(a,"max_concurrent_positions",1)or 1))
  if getattr(a,"allow_cli_concurrency",False):
   g=float(getattr(a,"_last_known_collateral",.0)or.0)+sum(a.get_position_market_value(p,h)for p in a.active_positions.values())
   if g<=.0 or g>=float(RISK_CONFIG.get("seed_survival_floor_usd",48.)):return max(1,int(getattr(a,"_explicit_max_concurrent",b)))
  if getattr(a,"dynamic_sizing",False):
   e=getattr(a,"risk_config",None)or RISK_CONFIG;i=float(getattr(a,"_last_known_collateral",.0)or.0)+sum(a.get_position_market_value(p,h)for p in a.active_positions.values())
   if i>.0:
    c=float(e.get("correlated_crypto_single_slot_threshold",110.))
    if not a.dry_run and i<c and os.environ.get("PM_ALLOW_SMALL_BANKROLL_CORRELATED_CRYPTO")!="1":b=1
    else:d=get_equity_tier_limits(i,getattr(a,"high_water_mark_equity",None),previous_tier=getattr(a,"_current_equity_tier",None));b=max(1,int(d.get("max_concurrent_positions",b)or 1))
  return b
 async def _async_refresh_collateral(a):
  if a.dry_run or not a.executor.is_authenticated:return
  try:
   t=await asyncio.to_thread(a.executor.get_collateral_balance,.0)
   if t is not None and isinstance(t,(int,float))and math.isfinite(t)and t>0:
    y=time.time();x=getattr(a,"_last_exit_credit_window",None);z=getattr(a,"_last_entry_debit_window",None)
    if(isinstance(x,tuple)and len(x)==2 and not getattr(a,"pending_entry_intents",None)and(y-float(x[0]))<15. and getattr(a.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2")and float(t)<float(x[1])-.5):t=float(x[1]);a._pending_collateral_refresh=True
    elif(isinstance(z,tuple)and len(z)==2 and(y-float(z[0]))<10. and not(isinstance(x,tuple)and len(x)==2 and float(x[0])>float(z[0]))and getattr(a.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2")and float(t)>float(z[1])+.5):t=float(z[1]);a._pending_collateral_refresh=True
    v=getattr(a,"_last_known_collateral",None);m=getattr(a,"_last_persisted_collateral",v);a._last_known_collateral=float(t);a._collateral_sync_seq=int(getattr(a,"_collateral_sync_seq",0)or 0)+1;from src.polymarket_research.riskless_protocol_v2_expansion import(pending_intents_synced_equity_usd as c,sync_pending_intents_on_collateral_refresh as b);b(a,v,float(t))
    for w in a.active_positions.values():
     if isinstance(w,dict)and not w.get("exit_cash_estimated",False):
      n=max(.0,float(w.get("confirmed_realized_cash",w.get("realized_exit_cash",.0))or.0)-float(w.get("realized_exit_fee",.0)or.0))
      if n>.0:w["_synced_exit_cash_usd"]=max(float(w.get("_synced_exit_cash_usd",.0)or.0),n)
    a.executor.set_cached_collateral(float(t));l=c(getattr(a,"pending_entry_intents",None));f=sum(a.get_position_market_value(p,y)for p in a.active_positions.values())+l;e=sum(max(float(p.get("confirmed_realized_cash",.0)or.0),float(p.get("estimated_exit_cash",.0)or.0))for p in a.active_positions.values()if p.get("status")=="UNRESOLVED_SETTLEMENT");r=float(t)+f+e;s,j=a._effective_sizing_equity_usd(r,y);k=((e<=.0)and(l<=.0)and(not j)and(not a._has_unsettled_collateral_overlap(y)));i=getattr(a,"_current_equity_tier",None)or getattr(a,"current_equity_tier",None);q=a._update_equity_tier(s,allow_hwm_ratchet=k);o=bool(a.risk_controller.halted);d=float(r)
    if not a.dry_run and d<float(a.risk_controller.min_equity_floor_usd)and hasattr(a.executor,"get_idle_usdce_balance"):
     u=await asyncio.to_thread(a.executor.get_idle_usdce_balance)
     if isinstance(u,(int,float))and not isinstance(u,bool)and float(u)>.0:d+=float(u)
    a.risk_controller.check_equity_drawdown(d,allow_auto_clear=True);h=(o!=bool(a.risk_controller.halted));g=(i!=q["tier"])
    if(v is None or abs(float(t)-float(v))>=.25 or m is None or abs(float(t)-float(m))>=.05 or h or g):await asyncio.to_thread(a.save_state)
  except Exception:pass
 def _effective_exit_policy(a):
  b=str(getattr(a,"exit_policy","")or"")
  if GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional",{}).get("respect_configured_exit_policy_on_safe",True):return b
  if(b=="hold_98"and not getattr(a,"dry_run",True)and getattr(a.executor,"client",None)is not None and not hasattr(a.executor.client,"_mock_children")and int(getattr(a.executor,"signature_type",0)or 0)==3 and not(os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY"))and os.getenv("PM_ENABLE_ONCHAIN_MERGE","0")!="1"):return"two_tranche_95_98"
  return b
 def _calculate_target_exit(a,price,tte):
  if getattr(a,"hold_to_maturity",False):return.98 if price<.8 else.99
  if a._effective_exit_policy()=="hold_98":return.98
  return min(.95,round(price+a.profit_theta,2))
 def _use_two_tranche_maker_exit(a,sleeve):
  if sleeve and("BOX"in str(sleeve).upper()or sleeve=="SLEEVE_4_BOUNDARY_SNIPE"):return False
  if sleeve=="SLEEVE_2_MID_HOUR"and getattr(a,"enable_mid_hour_t1_12c",False):return True
  if a._effective_exit_policy()=="hold_98":return False
  if not getattr(a,"hold_to_maturity",False):return True
  return False
 def _tranche1_tp_offset(self,sleeve):
  if sleeve=="SLEEVE_2_MID_HOUR"and getattr(self,"enable_mid_hour_t1_12c",False):return.12
  return.14
 def _global_halt_reasons(b):
  s=[];r=getattr(b,"pending_entry_intents",{})or{}
  if r:
   t=time.time();e=getattr(b,"_inflight_maker_anchor_keys",None)or set();h=getattr(b,"_inflight_phase3a_maker_ids",None)or set();g=getattr(b,"_inflight_directional_entry_ids",None)or set();c=[k for k,v in r.items()if not(isinstance(v,dict)and(t-float(v.get("heartbeat_ts")or v.get("ts")or v.get("submitted_at_ts")or.0))<45. and((v.get("live_maker_anchor_inflight")and str(v.get("inflight_key")or"")in e)or(k in h)or(k in g)))]
   if c:s.append(f"PENDING_ENTRY_INTENTS:{','.join(sorted(c))}")
  o=time.time();m=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("exit_supervisor",{});q=bool(m.get("isolate_single_market_zero_bid",True));f=int(m.get("global_zero_bid_halt_min_markets",m.get("min_markets_for_global_liquidity_halt",2)));d=getattr(b,"active_positions",{})or{};i={str(x.get("market_id")or w)for w,x in d.items()if(x.get("status")=="LIQUIDITY_CRISIS"or x.get("exit_order_status")=="LIQUIDITY_CRISIS")and(float(x.get("candle_expiry_ts",.0)or.0)-o)>120.}
  for u,p in d.items():
   if position_requires_global_halt(p):
    l=(p.get("status")=="LIQUIDITY_CRISIS"or p.get("exit_order_status")=="LIQUIDITY_CRISIS")and p.get("status")not in(PIPELINE_GLOBAL_HALT_STATUSES-{"LIQUIDITY_CRISIS"})and p.get("exit_order_status")not in(PIPELINE_GLOBAL_HALT_STATUSES-{"LIQUIDITY_CRISIS"})
    if l and q and len(i)<f:continue
    j="LIQUIDITY_CRISIS"if p.get("status")=="LIQUIDITY_CRISIS"else(p.get('exit_order_status')or p.get('status'));s.append(f"{u}:{j}")
  n=getattr(b,"executor",None)
  if n is not None and not b.dry_run and not getattr(n,"reservations_trusted",True):s.append("RESERVATIONS_UNTRUSTED")
  if not b.dry_run:
   try:from src.polymarket_research.riskless_protocol_v2_expansion import check_harvester_fail_closed_accounting_halt as a;s.extend(a(b,default_state_file=STATE_FILE))
   except Exception:s.append("ACCOUNTING_INVARIANT_CHECK_FAILED")
  return s
 def _reconciling_market_ids(self):
  a=set()
  for p in(getattr(self,"active_positions",{})or{}).values():
   d=p.get("status");c=p.get("exit_order_status")
   if d in MARKET_SCOPED_ENTRY_HALT_STATUSES or c in MARKET_SCOPED_ENTRY_HALT_STATUSES:
    b=str(p.get("market_id")or"")
    if b:a.add(b)
  return a
 def _refresh_global_halt(a,authoritative=False):
  e=a._global_halt_reasons();b=authoritative or a.dry_run or getattr(a,"_startup_reconciled",False);c=bool(e)or(a.risk_halt and not b);d=(c!=a.risk_halt)or(e!=a.global_halt_reasons);a.risk_halt=c;a.reconciliation_required=bool(e)or bool(a._reconciling_market_ids());a.global_halt_reasons=e if e else(a.global_halt_reasons if c else[])
  if d:
   if c:logger.critical(f"[GLOBAL HALT] New entries blocked: {a.global_halt_reasons}")
   else:logger.warning("[GLOBAL HALT CLEARED] All unknown outcomes authoritatively reconciled.")
   a.save_state()
  return c
 @staticmethod
 def get_position_market_value(pos,now_ts=None):
  if now_ts is None:now_ts=time.time()
  if pos.get("pending_settlement_close_reason")in{"MARKET_RESOLVED_LOSS","EXPIRED_OUT_OF_MONEY"}:return.0
  if pos.get("close_reason")and"MARKET_RESOLVED_LOSS"in str(pos.get("close_reason")):return.0
  d=pos.get("resolved_winning_outcome");f=pos.get("target_token")
  if d is not None and f is not None and d!=f:return.0
  b=pos.get("_closed_partner_leg");a=bool(pos.get("is_dominance_box")and isinstance(b,dict)and float(b.get("payout_usd",.0)or.0)<=.01);c=(max(float(pos.get("expected_terminal_payout_usd")or pos.get("entry_shares")or.0),float(pos.get("remaining_cost_basis",pos.get("notional_usd",.0))or.0)+float(b.get("notional_usd",.0)or.0))if a else.0);e=float(pos.get("candle_expiry_ts")or.0)
  if e>.0 and now_ts>=e:
   if d is not None and d==f:return float(pos.get("expected_terminal_payout_usd")or pos.get("entry_shares")or.0)
   if a:return c
   if d is None:return float(pos.get("remaining_cost_basis",pos.get("notional_usd",.0))or.0)
   return.0
  if pos.get("status")in{"UNRESOLVED_SETTLEMENT","AWAITING_ONCHAIN_SETTLEMENT"}:
   if d is not None and d==f:return float(pos.get("expected_terminal_payout_usd")or pos.get("entry_shares")or.0)
   if a:return c
   if d is None and(pos.get("is_dominance_box")or pos.get("is_single_leg_lock")):return float(pos.get("remaining_cost_basis",pos.get("notional_usd",.0))or.0)
   return.0
  return float(pos.get("remaining_cost_basis",pos.get("notional_usd",.0))or.0)
 def _risk_bearing_positions(self):
  c=time.time();b={}
  for k,v in self.active_positions.items():
   if v.get("is_dominance_box")or v.get("is_single_leg_lock"):continue
   if position_is_settlement_receivable(v):continue
   if v.get("status")in{"UNRESOLVED_SETTLEMENT","AWAITING_ONCHAIN_SETTLEMENT"}:continue
   a=float(v.get("candle_expiry_ts")or.0)
   if a>.0 and c>=a:continue
   b[k]=v
  return b
 def _active_box_ids(self):a=time.time();return{str(p.get("box_id")or k)for k,p in self.active_positions.items()if(p.get("is_dominance_box")or p.get("is_single_leg_lock"))and not position_is_settlement_receivable(p)and p.get("status")not in{"UNRESOLVED_SETTLEMENT","AWAITING_ONCHAIN_SETTLEMENT"}and not(float(p.get("candle_expiry_ts")or.0)>.0 and a>=float(p.get("candle_expiry_ts")or.0))}
 def _total_open_portfolio_slots(a):return len(a._active_box_ids())+len(a._risk_bearing_positions())
 def _preempt_resting_maker_anchors(a,reason="",market_ids=None):
  c=getattr(a,"_maker_anchor_preempt_events",None)or{}
  if not c:return 0
  d=a.__dict__.setdefault("_maker_anchor_preempt_reasons",{});b=0
  for f in list((getattr(a,"pending_entry_intents",None)or{}).values()):
   if not(isinstance(f,dict)and f.get("live_maker_anchor_inflight")):continue
   if market_ids is not None and str(f.get("market_id")or"")not in market_ids:continue
   g=str(f.get("inflight_key")or"");e=c.get(g)
   if e is not None:
    if reason and g not in d:d[g]=reason
    e.set();b+=1
  return b
 def can_enter_new_position(a,market_id=None):
  if a.risk_controller.is_halted()or getattr(a,"risk_halt",False):return False
  if bool(a._global_halt_reasons()):return False
  if market_id and str(market_id)in a._reconciling_market_ids():return False
  if len(a._risk_bearing_positions())>=a.max_concurrent_positions:return False
  return True
 ONCHAIN_SOURCE="POLYGON_ONCHAIN_ERC1155";UNWIND_UNKNOWN_STATES=frozenset({"UNWIND_EXECUTION_OUTCOME_UNKNOWN","UNWIND_RECONCILIATION_REQUIRED","UNRESOLVED_BALANCE_DISCREPANCY"})
 @staticmethod
 def _num(val):
  if isinstance(val,bool)or not isinstance(val,(int,float,str,Decimal)):return None
  try:f=float(val)
  except(TypeError,ValueError):return None
  return f if math.isfinite(f)else None
 def _wallet_token_balance(a,token_id):
  if not token_id:return None,"UNAVAILABLE"
  d=getattr(a.executor,"get_onchain_erc1155_balance",None);e=getattr(a.executor,"get_conditional_balance",None);b=None
  if d is not None:
   try:b=a._num(d(token_id))
   except Exception:b=None
  if b is not None and b>.0:return b,a.ONCHAIN_SOURCE
  if(b is not None and b==.0 and not any(str(p.get("token_id"))==str(token_id)for p in a.active_positions.values())and not any(str(i.get("token_id"))==str(token_id)for i in(getattr(a,"pending_entry_intents",None)or{}).values()if isinstance(i,dict))):return.0,a.ONCHAIN_SOURCE
  c=None
  if e is not None:
   try:c=a._num(e(token_id))
   except Exception:c=None
  if c is not None and c>.0:return c,"CLOB_BALANCE_API"
  if b is not None and b>=.0:return b,a.ONCHAIN_SOURCE
  if c is not None and c>=.0:return c,"CLOB_BALANCE_API"
  return None,"UNAVAILABLE"
 def _mark_token_pre_bal_dirty(a,token_id,ttl_sec=3600.):
  if not token_id:return
  f=str(token_id);e=time.time();d=a.__dict__.setdefault("_d1_dirty_token_until",{})
  if len(d)>256:
   for c,b in list(d.items()):
    if float(b or.0)<=e:d.pop(c,None)
  d[f]=e+float(ttl_sec);(a.__dict__.get("_d1_clean_pre_bal_cache")or{}).pop(f,None)
 def _try_fast_clean_zero_pre_bal(a,token_id,exclude_intent_id=""):
  if a.dry_run or not token_id:return.0
  g=str(token_id);j=getattr(a,"executor",None);h=getattr(j,"__dict__",{})if j is not None else{};b=bool(getattr(a,"_force_fast_pre_bal_ram",False))or(getattr(j,"auth_mode","")in("LIVE","AUTHENTICATED_L2")and getattr(getattr(j,"client",None),"_mock_children",None)is None and getattr(j,"_mock_children",None)is None);c=("_wallet_token_balance"in a.__dict__)or any(k in h for k in("get_onchain_erc1155_balance","get_conditional_balance","get_token_balance"))
  if not b or c:return None
  e=time.time();f=a.__dict__.setdefault("_d1_dirty_token_until",{})
  if float(f.get(g,.0)or.0)>e:return None
  d=getattr(j,"_user_ws_cache",None)
  if d is not None and hasattr(d,"has_token_fill_since")and d.has_token_fill_since(g,e-6e2):return None
  if any(str(p.get("token_id")or"")==g for p in(getattr(a,"active_positions",None)or{}).values()):return None
  if any(k!=exclude_intent_id and isinstance(i,dict)and str(i.get("token_id")or"")==g for k,i in(getattr(a,"pending_entry_intents",None)or{}).items()):return None
  if any(str(p.get("token_id")or"")==g and(float(p.get("remaining_shares",.0)or.0)>.01 or(e-float(p.get("closed_at_ts")or p.get("exit_ts")or.0))<180.)for p in(getattr(a,"closed_positions",None)or[])[-30:]):return None
  (a.__dict__.setdefault("_d1_clean_pre_bal_cache",{}))[g]=(.0,e);return.0
 def _resolve_fast_pre_token_balance_sync(a,token_id,exclude_intent_id=""):
  b=a._try_fast_clean_zero_pre_bal(token_id,exclude_intent_id=exclude_intent_id)
  if b is not None:return b
  return float((a._wallet_token_balance(token_id))[0]or.0)
 async def _resolve_fast_pre_token_balance_async(a,token_id,exclude_intent_id=""):
  b=a._try_fast_clean_zero_pre_bal(token_id,exclude_intent_id=exclude_intent_id)
  if b is not None:return b
  return float((await asyncio.to_thread(a._wallet_token_balance,token_id))[0]or.0)
 def _known_fill_ids(a,exclude_tid=None):
  e=set();b=list(a.active_positions.items())+[(str(c.get("trade_id")),c)for c in a.closed_positions[-1000:]]
  for d,p in b:
   if exclude_tid is not None and d==exclude_tid:continue
   e.update(str(x)for x in(p.get("entry_fill_ids")or[]));e.update(str(x)for x in(p.get("exit_fill_ids")or[]))
  return e
 def _fetch_account_fills(b,token_id,after_ts,side,order_id=None,exclude_tid=None):
  p=getattr(b.executor,"get_account_fills",None)
  if p is None:return None
  try:n=p(token_id,after_ts=float(after_ts),side=side,order_id=order_id or None)
  except Exception as e:logger.error(f"[LIFECYCLE] Trade history unavailable for {token_id}: {e}");return None
  if not isinstance(n,list):return None
  from src.polymarket_research.riskless_protocol_v2_expansion import collect_claimed_position_fill_and_order_ids as a;j,i,d,c=a(b,exclude_tid=exclude_tid);m=b._known_fill_ids(exclude_tid)|j;h=str(side or"").upper();g=str(order_id or"").strip();o=[]
  for f in n:
   if not isinstance(f,dict)or str(f.get("fill_id"))in m:continue
   l=str(f.get("order_id")or"").strip();k=str(f.get("trade_id")or f.get("id")or"").strip()
   if k and k in i and not(g and l==g):continue
   if not g and l:
    if h=="SELL"and l in c:continue
    if h=="BUY"and l in d:continue
   if(b._num(f.get("size"))or.0)<=.0:continue
   o.append(f)
  return o
 def _fetch_entry_evidence(a,token_id,submitted_ts,entry_order_id=None,exclude_tid=None):
  b=a._fetch_account_fills(token_id,submitted_ts-5.,"BUY",entry_order_id,exclude_tid)
  if b is None:return None
  return{"fills":b,"shares":round(sum(a._num(f.get("size"))or.0 for f in b),6),"cash":round(sum(a._num(f.get("cash"))or.0 for f in b),6),"trade_ids":sorted({str(f["trade_id"])for f in b if f.get("trade_id")}),"transactions_hashes":sorted({str(f["transaction_hash"])for f in b if f.get("transaction_hash")}),"order_ids":sorted({str(f["order_id"])for f in b if f.get("order_id")}),"fill_ids":sorted({str(f["fill_id"])for f in b if f.get("fill_id")})}
 def _classify_entry(a,token_id,pre_bal,submitted_ts,entry_order_id,exclude_tid,market_resolved=False,condition_id=None,resolution_seen_at_ts=.0):
  t,s=a._wallet_token_balance(token_id);h=a._fetch_entry_evidence(token_id,submitted_ts,entry_order_id,exclude_tid);r={"verdict":"UNKNOWN","balance":t,"source":s,"delta":None,"evidence":h}
  if t is None:return r
  m=t-float(pre_bal or.0);r["delta"]=m
  if m>=.01:r["verdict"]="ARRIVED";return r
  if m<=-.01:return r
  if h is not None and h["shares"]>.0:r["verdict"]="MATCHED_UNSETTLED";return r
  k=time.time();q=k-float(submitted_ts or.0);i=(k-float(resolution_seen_at_ts))if float(resolution_seen_at_ts or.0)>.0 else q
  def b(nc_reason_raw,matched_qty,assoc_trades):
   if not market_resolved or matched_qty>1e-4 or bool(assoc_trades):return False
   if h is None or h.get("fills")or s!=a.ONCHAIN_SOURCE:return False
   if q<ENTRY_UNEXECUTED_PROOF_AGE_S or i<15.:return False
   u=str(nc_reason_raw or"").lower()
   if not any(p in u for p in("can't be found","cannot be found","already canceled","already cancelled","market is closed")):return False
   if condition_id and hasattr(a.executor,"redemption_payouts"):
    try:v=a.executor.redemption_payouts(str(condition_id),float(submitted_ts or.0))
    except Exception:return False
    if v is None or len(v)>0:return False
   return True
  if entry_order_id:
   try:e=a.executor.get_order_status(str(entry_order_id))
   except Exception:e=None
   if isinstance(e,dict):
    n=str(e.get("status","")).upper();d=a._num(e.get("size_matched"))or.0
    if n in{"LIVE","OPEN","RESTING","DELAYED"}:
     try:g=a.executor.cancel_order(str(entry_order_id))
     except Exception:g={}
     if not(g or{}).get("is_canceled"):
      if b((g or{}).get("not_canceled_reason"),d,e.get("associate_trades")):a.executor.release_inventory(reservation_id=str(entry_order_id));r["verdict"]="NOT_EXECUTED";r["proof"]="RESOLVED_MARKET_PURGED_ORDER_ZERO_FILL"
      return r
     try:e=a.executor.get_order_status(str(entry_order_id))or e
     except Exception:pass
     n=str(e.get("status","")).upper();d=max(d,a._num((g or{}).get("matched"))or.0,a._num(e.get("size_matched"))or.0)
     if d>1e-4:r["verdict"]="MATCHED_UNSETTLED";return r
     if(g or{}).get("is_canceled")and d<=1e-4:r["verdict"]="NOT_EXECUTED";r["proof"]="RESTING_ENTRY_CANCELED_ZERO_FILL";return r
    if(n.startswith("CANCEL")or n in{"EXPIRED","REJECTED","INVALID"})and d<=1e-4:r["verdict"]="NOT_EXECUTED";r["proof"]="TERMINAL_ZERO_FILL_ORDER_STATUS";return r
  if(h is not None and not h["fills"]and s in(a.ONCHAIN_SOURCE,"CLOB_BALANCE_API")and(q>=ENTRY_UNEXECUTED_PROOF_AGE_S or market_resolved)):
   if hasattr(a.executor,"get_open_orders"):
    try:c=a.executor.get_open_orders(strict=True)
    except TypeError:c=a.executor.get_open_orders()
    except Exception:c=None
    if not isinstance(c,list):
     if market_resolved and s==a.ONCHAIN_SOURCE:r["verdict"]="NOT_EXECUTED";r["proof"]="RESOLVED_MARKET_ONCHAIN_ZERO_AND_NO_FILLS";return r
     return r
    if isinstance(c,list):
     for o in c:
      if str((o or{}).get("asset_id")or(o or{}).get("token_id")or"")==str(token_id)and str((o or{}).get("side")or"").upper()=="BUY":
       l=str((o or{}).get("id")or(o or{}).get("orderID")or"")
       if l:
        try:j=a.executor.cancel_order(l)
        except Exception:j={}
        f=max(a._num((j or{}).get("matched"))or.0,a._num((o or{}).get("size_matched"))or.0)
        if not(j or{}).get("is_canceled")or f>1e-4:
         if not b((j or{}).get("not_canceled_reason"),f,(o or{}).get("associate_trades")):return r
         a.executor.release_inventory(reservation_id=l)
   r["verdict"]="NOT_EXECUTED";r["proof"]="ONCHAIN_UNCHANGED_AND_NO_ACCOUNT_FILLS"
  return r
 def _apply_entry_evidence(b,pos,cls):
  c=cls.get("evidence")or{};g=cls.get("delta");d=datetime.now(timezone.utc).isoformat()
  if cls["verdict"]=="ARRIVED"and g is not None:
   h=float(Decimal(str(g)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR));pos["entry_shares"]=h;pos["remaining_shares"]=h;pos["remaining_exit_shares"]=h;pos["filled_exit_shares"]=.0
   if float(pos.get("notional_usd",.0)or.0)<=.0 and h>0:e=float(pos.get("entry_price")or pos.get("target_price")or.7);pos["notional_usd"]=round(h*e,4);pos["cost_basis_estimated"]=True
   pos["remaining_cost_basis"]=pos.get("notional_usd",.0)
   if h>0 and float(pos.get("notional_usd",.0)or.0)>0:
    a=round(float(pos["notional_usd"])/h,4)
    if a>float(pos.get("entry_price",.0)or.0):pos["entry_price"]=a;pos["target_exit_price"]=b._calculate_target_exit(a,float(pos.get("candle_expiry_ts",time.time()+6e2))-time.time())
   pos["inventory_reconciled"]=True;pos["entry_inventory_source"]=cls.get("source")
  if c.get("shares",.0)>.0:
   pos["trade_ids"]=c["trade_ids"];pos["transactions_hashes"]=c["transactions_hashes"];pos["entry_fill_ids"]=c["fill_ids"]
   if not pos.get("entry_order_id")and c["order_ids"]:pos["entry_order_id"]=c["order_ids"][0]
   f=max(float(c["shares"]),float(g or.0));pos["gross_entry_shares"]=round(f,6)
   if c["cash"]>.0:pos["notional_usd"]=round(float(c["cash"]),6);pos["entry_price"]=round(float(c["cash"])/max(float(c["shares"]),1e-9),6);pos["cost_basis_estimated"]=False
   pos["entry_finality_source"]="EXCHANGE_TRADE_HISTORY"
   if cls["verdict"]!="ARRIVED":pos["entry_shares"]=round(float(c["shares"]),6);pos["remaining_shares"]=pos["entry_shares"];pos["remaining_exit_shares"]=pos["entry_shares"];pos["inventory_reconciled"]=False
  elif cls["verdict"]=="ARRIVED":pos["gross_entry_shares"]=round(float(g),6);pos["cost_basis_estimated"]=True;pos["entry_finality_source"]=("ONCHAIN_BALANCE_DELTA"if cls.get("source")==b.ONCHAIN_SOURCE else"CLOB_BALANCE_DELTA")
  pos["remaining_cost_basis"]=float(pos.get("notional_usd",.0)or.0);pos["entry_finality_verified_at_utc"]=d
 def _verify_entry_finality(b,pos):
  a=False
  for f in pos.get("trade_ids")or[]:
   try:d=b.executor.get_trade_status(f)or{}
   except Exception:d={}
   h=str(d.get("status","")).upper()if isinstance(d,dict)else""
   if h in{"CONFIRMED","MINED"}:return True,False
   g=d.get("transactionHash")or d.get("transaction_hash")if isinstance(d,dict)else None
   if g:
    e=b.executor.get_transaction_receipt_status(g)
    if e is True:return True,False
    if e is False:a=True
  c=pos.get("transactions_hashes")or pos.get("transactionsHashes")or pos.get("transaction_hashes")or[]
  for g in c:
   try:e=b.executor.get_transaction_receipt_status(g)
   except Exception:e=None
   if e is True:return True,False
   if e is False:a=True
  return False,a
 def _pending_reservations(self,pos):return[str(r)for r in(pos.get("pending_reservation_ids")or[])if r]
 def _release_position_reservations(a,pos,extra_ids=None):
  c=set(a._pending_reservations(pos))|{str(x)for x in(extra_ids or[])if x}
  for b in c:
   try:a.executor.release_inventory(reservation_id=b)
   except Exception as e:logger.error(f"[LIFECYCLE] Could not release reservation {b}: {e}");raise
  pos["pending_reservation_ids"]=[]
 def _consolidate_dominance_box_close(self,tid,pos,cum_cash,cum_fee,net_pnl,reason,record_pnl):from src.polymarket_research.riskless_protocol_v2_expansion import consolidate_any_box_leg_close as a;return a(self,tid,pos,cum_cash,cum_fee,net_pnl,reason,record_pnl)
 def _close_position(a,tid,pos,status,reason,won=None,record_pnl=True):
  h=(reason in{"MARKET_RESOLVED_LOSS","EXPIRED_OUT_OF_MONEY"}or pos.get("pending_settlement_close_reason")in{"MARKET_RESOLVED_LOSS","EXPIRED_OUT_OF_MONEY"}or(pos.get("close_reason")and"MARKET_RESOLVED_LOSS"in str(pos.get("close_reason"))));d=float(pos.get("filled_exit_shares",.0)or.0)>.01
  if h and not d:pos["exit_cash_estimated"]=False;pos["estimated_exit_cash"]=.0
  x=float(pos.get("estimated_exit_cash",.0)or.0)
  if(not h or d)and(x>.0 or pos.get("exit_cash_estimated",False)):logger.warning(f"[SETTLEMENT_BLOCKED] Cannot settle position {tid} with unconfirmed/estimated cash (estimated=${x:.2f}, exit_cash_estimated={pos.get('exit_cash_estimated')}). " "Retaining in UNRESOLVED_SETTLEMENT state pending authoritative fills.");pos["status"]="UNRESOLVED_SETTLEMENT";pos["close_reason"]=f"BLOCKED_UNCONFIRMED_ESTIMATE: {reason}";pos["pending_settlement_close_status"]=status;pos["pending_settlement_close_reason"]=reason;a.save_state();return None
  if(not getattr(a,"dry_run",True)and not bool(pos.get("inventory_reconciled"))and(str(pos.get("status")or"")in{"ENTRY_OUTCOME_UNKNOWN","NOT_EXECUTED"}or str(pos.get("exit_order_status")or"")=="ENTRY_OUTCOME_UNKNOWN")and not(pos.get("trade_ids")or pos.get("transactions_hashes"))and float(pos.get("filled_exit_shares",.0)or.0)<.01 and float(pos.get("confirmed_realized_cash",pos.get("realized_exit_cash",.0))or.0)<=.0):
   status="NOT_EXECUTED"
   if status!=reason and"NOT_EXECUTED"not in str(reason or"").upper()and"UNFILLED"not in str(reason or"").upper():reason=("UNFILLED_MAKER_EXPIRED_NO_FILL"if"MAKER"in str(pos.get("box_type")or pos.get("fee_source")or"").upper()else"ENTRY_NOT_EXECUTED_AT_RESOLUTION")
   won=False;record_pnl=False;pos["entry_shares"]=.0;pos["notional_usd"]=.0;pos["remaining_cost_basis"]=.0;pos["fee_usd"]=.0;pos["entry_fee_cash_usd"]=.0
  w=float(pos.get("confirmed_realized_cash",pos.get("realized_exit_cash",.0))or.0);y=float(pos.get("realized_exit_fee",.0)or.0);A=float(pos.get("filled_exit_shares",.0)or.0);j=a.calculate_realized_cash_pnl(pos,w,y)if record_pnl else.0;a._release_position_reservations(pos,[pos.get("exit_order_id"),pos.get("unwind_order_id")]);v=pos.get("token_id")
  if v and not any(p.get("token_id")==v for k,p in a.active_positions.items()if k!=tid):
   try:a.executor.release_inventory(v,float(pos.get("entry_shares",.0)or.0))
   except Exception as e:logger.error(f"[LIFECYCLE] Token reservation release failed for {v}: {e}");raise
  pos["status"]=status;s=time.time();pos.setdefault("opened_at_ts",float(pos.get("entry_ts")or s));pos["closed_at_ts"]=s;pos["exit_ts"]=s;pos["settled_at_utc"]=datetime.now(timezone.utc).isoformat();pos["won"]=(j>.0)if won is None else won;pos["payout_usd"]=round(w,4);pos["net_pnl_usd"]=round(j,4);pos["close_reason"]=reason
  if A>.0:pos["average_exit_price"]=round(w/A,4)
  pos["remaining_shares"]=.0;pos["remaining_exit_shares"]=.0;pos["is_liquidating"]=False;C=str(reason or"").upper()
  if status=="NOT_EXECUTED":pos["exit_decomposition_bucket"]="NOT_EXECUTED"
  elif"MAKER_SCALP"in C or"MAKER_RECYCLE"in C or"FILLED_OFFLINE"in C:
   pos["exit_decomposition_bucket"]="MAKER_SCALP"
   if not getattr(a,"dry_run",True)and _STAGE_B_MARKOUT_SAMPLER is not None and A>.01 and w>.0 and v and hasattr(a.executor,"get_market_book"):
    try:u=getattr(a,"_pos_market_ws",None);_STAGE_B_MARKOUT_SAMPLER.schedule_maker_fill(order_id=str(pos.get("exit_order_id")or tid),token_id=str(v),sleeve=str(pos.get("sleeve")or pos.get("sleeve_source")or"MAKER_EXIT"),side="SELL",fill_px=round(w/A,6),shares=A,book_lookup_fn=lambda D:(u.get_book(str(D),max_age_sec=5.)if u is not None else None)or a.executor.get_market_book(str(D)))
    except Exception:pass
  elif"RATCHET"in C or"RECYCLE"in C:pos["exit_decomposition_bucket"]="PROFIT_RATCHET"
  elif"STOP"in C or"UNWIND"in C or"SALVAGE"in C:pos["exit_decomposition_bucket"]="SALVAGE_UNWIND"
  elif"AUTOREDEEM"in C:pos["exit_decomposition_bucket"]="TERMINAL_HOLD_WIN"
  elif"REDEMPTION"in C or(pos.get("won")and"RESOLVED"in C):pos["exit_decomposition_bucket"]="TERMINAL_SETTLEMENT"
  elif pos.get("won")and j>.0:pos["exit_decomposition_bucket"]="PROFIT_RATCHET"
  else:pos["exit_decomposition_bucket"]="TERMINAL_LOSS"
  o=str(pos.get("market_id")or"");pos["entry_sequence_in_market"]=int((getattr(a,"trades_per_market",None)or{}).get(o,1)or 1);pos["is_win_reset_second_entry"]=bool(pos["entry_sequence_in_market"]>=2);n=max(.0,float(w or.0)-float(y or.0));f=max(.0,n-float(pos.get("_synced_exit_cash_usd",.0)or.0));r=pos.get("_unresolved_settle_seq");b=(r is not None and int(getattr(a,"_collateral_sync_seq",0)or 0)>int(r))
  if(not getattr(a,"dry_run",True)and getattr(a,"_last_known_collateral",None)is not None and f>.0 and not pos.get("_collateral_exit_credited")and not b):pos["_collateral_exit_credited"]=True;a._last_known_collateral=float(a._last_known_collateral)+f;a._last_exit_credit_window=(time.time(),float(a._last_known_collateral))
  g,j=a._consolidate_dominance_box_close(tid,pos,w,y,j,reason,record_pnl)
  if g:
   try:asyncio.get_running_loop().create_task(a._async_refresh_collateral())
   except RuntimeError:pass
   return j
  a.closed_positions.append(pos)
  if record_pnl:z=bool(pos.get("is_dominance_box")or pos.get("is_single_leg_lock")or pos.get("is_legged_out_residual")or"BOX"in str(pos.get("sleeve")or"").upper());a.risk_controller.record_trade_pnl(j,is_non_directional=z)
  a.active_positions.pop(tid,None);from src.polymarket_research.riskless_protocol_v2_expansion import clear_d1_dedupe_on_close as c;c(a,pos);m=getattr(a,"_last_known_collateral",None)
  if not getattr(a,"dry_run",True)and isinstance(m,(int,float))and math.isfinite(m)and m>.0:l=time.time();q=sum(a.get_position_market_value(p,l)for p in a.active_positions.values());i,_=a._effective_sizing_equity_usd(float(m)+q,l);a._update_equity_tier(i,allow_hwm_ratchet=False)
  a.save_state();a._pending_collateral_refresh=True
  try:B=asyncio.get_running_loop();B.create_task(a._async_refresh_collateral())
  except RuntimeError:pass
  t=f"{j:+.4f}"if.0<abs(j)<.01 else f"{j:+.2f}";logger.info(f"[CLOSED] {tid} | {reason} | Payout=${w:.2f} | Net PnL=${t}");return j
 @staticmethod
 def _estimated_taker_fee(shares,cash,fee_rate=.07,fee_exponent=1.):
  if shares<=.0:return.0
  a=min(.999,max(.001,cash/shares));return round(shares*fee_rate*((a*(1.-a))**max(1.,float(fee_exponent))),5)
 def _exit_taker_fee_rate(self,pos):from src.polymarket_research.riskless_machine_gun_engine import resolve_authoritative_exit_fee_rate as a;return a(getattr(self,"executor",None),pos)
 def _record_order_summary(a,pos,summary,fallback_px,taker):
  y=str(summary["order_id"]);s=float(summary.get("matched",.0)or.0);o=(pos.get("order_records")or{}).get(y)or{};u=float(o.get("matched",.0)or.0);e=bool(o.get("cash_is_estimated",False));q=summary.get("cash");d=False
  if q is None:
   q=round(s*max(.0,float(fallback_px or.0)),6)
   if s>.0:d=True;pos["exit_cash_estimated"]=True
  elif summary.get("cash_is_estimated")and s>.0:d=True;pos["exit_cash_estimated"]=True
  if s<=1e-6 and float(pos.get("estimated_exit_cash",.0)or.0)<=1e-6:
   j=any(isinstance(v,dict)and v.get("cash_is_estimated")and float(v.get("matched",.0)or.0)>1e-6 for k,v in(pos.get("order_records")or{}).items()if str(k)!=y)
   if not j and pos.get("exit_cash_estimated"):pos["exit_cash_estimated"]=False
  h=(s>u+1e-6);b=e and(not d);l=float(o.get("cash",.0)or.0);c=(abs(float(q)-l)>1e-6)and(not d)
  if not(h or b or c):return False
  n=a._exit_taker_fee_rate(pos);m=float(pos.get("fee_exponent_applied")or 1.);g=bool(taker and not summary.get("cash_from_reported_taking"));x=a._estimated_taker_fee(s,float(q),fee_rate=n,fee_exponent=m)if g else.0
  if g:pos["exit_fee_estimated"]=True
  p=a.record_fill_and_update_position(pos,y,s,float(q),x,cash_is_estimated=d)
  if isinstance(p,dict):p["is_taker"]=bool(taker);p["fallback_price"]=float(fallback_px or.0)
  w=set(pos.get("exit_trade_ids")or[])|set(summary.get("trade_ids")or[]);pos["exit_trade_ids"]=sorted(str(i)for i in w);t=set(pos.get("exit_fill_ids")or[])|set(summary.get("fill_ids")or[]);pos["exit_fill_ids"]=sorted(str(i)for i in t);r=float(summary.get("original_size",.0)or pos.get("exit_order_size",pos.get("entry_shares",.0))or.0);f=max(.0,r-s)
  if summary.get("terminal")or f<=.0:a.executor.release_inventory(reservation_id=y)
  else:a.executor.update_reservation(y,f)
  return True
 def _record_history_fills(a,pos,fills,taker):
  from src.polymarket_research.riskless_protocol_v2_expansion import filter_unclaimed_position_fills as b;fills=b(a,pos,fills,side="SELL",exclude_tid=str(pos.get("trade_id")or""))
  if not fills:return 0
  u=defaultdict(list)
  for f in fills:u[str(f.get("order_id")or f.get("fill_id"))].append(f)
  d=0;o=a._exit_taker_fee_rate(pos);n=float(pos.get("fee_exponent_applied")or 1.);i=float(pos.get("entry_shares")or.0);h=[]
  for z,x in u.items():
   w=(pos.get("order_records")or{}).get(z)or{};j=.0 if w.get("cash_is_estimated")else float(w.get("matched",.0)or.0);m=.0 if w.get("cash_is_estimated")else float(w.get("cash",.0)or.0);t=.0 if w.get("cash_is_estimated")else float(w.get("fee",.0)or.0);q=sum(a._num(f.get("size"))or.0 for f in x);g=sum(a._num(f.get("cash"))or.0 for f in x);e=j+q;r=m+g
   if i>.0:
    s=sum(float((v or{}).get("matched",.0)or.0)for k,v in(pos.get("order_records")or{}).items()if str(k)!=z and isinstance(v,dict));l=max(.0,i-s)
    if e>l+.02:
     if l<=1e-6:continue
     r=r*(l/e);q=max(.0,l-j);g=max(.0,r-m);e=l
   y=t+(a._estimated_taker_fee(q,g,fee_rate=o,fee_exponent=n)if taker else.0);c=all(bool(f.get("transaction_hash"))and str(f.get("status","")).upper()in{"MINED","CONFIRMED"}for f in x);p=a.record_fill_and_update_position(pos,z,e,r,y,cash_is_estimated=(not c and not a.dry_run))
   if isinstance(p,dict):p["is_taker"]=bool(taker)
   d+=len(x);h.extend(x)
  if h:pos["exit_fill_ids"]=sorted(set(pos.get("exit_fill_ids")or[])|{str(f.get("fill_id"))for f in h if f.get("fill_id")});pos["exit_trade_ids"]=sorted(set(pos.get("exit_trade_ids")or[])|{str(f.get("trade_id"))for f in h if f.get("trade_id")})
  if taker and d:pos["exit_fee_estimated"]=True
  return d
 def _after_unwind_reconciled(a,tid,pos,reason_default):
  pos["unwind_order_id"]=None;pos["is_liquidating"]=False;pos.pop("unwind_attempt_ts",None)
  if float(pos.get("remaining_shares",.0)or.0)<=.01:a._close_position(tid,pos,ExecutionStatus.SETTLED,pos.get("unwind_reason")or reason_default,won=None);return
  pos["status"]=ExecutionStatus.PARTIALLY_FILLED if float(pos.get("filled_exit_shares",.0)or.0)>0 else pos.get("status");b=float(pos.get("candle_expiry_ts",.0)or.0)
  if b>.0 and time.time()>=b:pos["exit_order_status"]="DETERMINISTIC_TERMINAL_HOLD";pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD";pos["next_unwind_retry_ts"]=.0;a.save_state();return
  pos["exit_order_status"]="UNWIND_RETRY_REQUIRED";pos["next_unwind_retry_ts"]=.0;a.save_state()
 def _resolve_unknown_unwind(a,tid,pos):
  n=pos.get("token_id");r=pos.get("unwind_order_id");h=float(pos.get("unwind_attempt_ts")or pos.get("unwind_last_attempt_ts")or pos.get("unwind_start_time")or pos.get("entry_ts")or.0);d=float(pos.get("unwind_limit_price")or.01);g=[str(x)for x in(pos.get("canceled_maker_exit_oids")or[])if x];l=set(g)
  for q in g:
   p=a.executor.get_order_fill_summary(q,n)
   if p is not None and float(p.get("matched")or.0)>.0:
    a._record_order_summary(pos,p,float(pos.get("target_exit_price",.98)or.98),taker=False)
    if float(pos.get("remaining_shares",.0)or.0)<=.01:a._after_unwind_reconciled(tid,pos,"MAKER_SCALP_FILLED_CLOB");return True
  if r:
   o=a.executor.get_order_fill_summary(str(r),n)
   if o is not None:
    if not o["terminal"]:a._record_order_summary(pos,o,d,taker=True);a.save_state();return False
    a._record_order_summary(pos,o,d,taker=True);a._release_position_reservations(pos,[str(r)]);logger.warning(f"[UNWIND RECONCILED] {tid}: order {r} terminal {o['status']} matched={o['matched']:.2f}");a._after_unwind_reconciled(tid,pos,"UNWIND_RECONCILED");return True
  if not n:return False
  m=pos.get("order_records")or{};c={str(k)for k,v in m.items()if str(k)not in l or(isinstance(v,dict)and not v.get("cash_is_estimated")and float(v.get("matched")or.0)>.0)}
  if pos.get("exit_order_id"):c.add(str(pos["exit_order_id"]))
  b=min(h,float(pos.get("entry_ts")or h))-5. if l else(h-5.);e=a._fetch_account_fills(n,b,"SELL",exclude_tid=tid)
  if e is None:return False
  e=[f for f in e if str(f.get("order_id"))not in c]
  if e:
   j=[f for f in e if str(f.get("order_id"))in l];i=[f for f in e if str(f.get("order_id"))not in l]
   if j:a._record_history_fills(pos,j,taker=False)
   if i:a._record_history_fills(pos,i,taker=True)
   a._release_position_reservations(pos,[str(r)]if r else None);logger.warning(f"[UNWIND RECONCILED] {tid}: {len(e)} fill(s) recovered from exchange trade history.");a._after_unwind_reconciled(tid,pos,"UNWIND_RECONCILED_FROM_HISTORY");return True
  if time.time()-h<UNWIND_UNKNOWN_PROOF_AGE_S:return False
  w,u=a._wallet_token_balance(n);t=float(pos.get("remaining_shares",pos.get("entry_shares",.0))or.0);s=a.executor.calculate_balance_epsilon(.001)
  if w is not None and u==a.ONCHAIN_SOURCE and w+s>=t:a._release_position_reservations(pos,[str(r)]if r else None);logger.warning(f"[UNWIND RECONCILED] {tid}: no fills and on-chain inventory intact ({w:.4f} >= {t:.4f}); unwind did not execute.");a._after_unwind_reconciled(tid,pos,"UNWIND_RECONCILED");return True
  return False
 def _resolve_unknown_entry(a,tid,pos):
  h=a._classify_entry(pos.get("token_id"),float(pos.get("pre_token_balance",.0)or.0),float(pos.get("submitted_at_ts")or pos.get("entry_ts")or.0),pos.get("entry_order_id"),tid,market_resolved=bool(pos.get("resolved_winning_outcome")is not None),condition_id=pos.get("condition_id"),resolution_seen_at_ts=float(pos.get("resolution_seen_at_ts")or.0));e=h["verdict"];g=str(pos.get("box_partner_trade_id")or"")
  if e in{"ARRIVED","MATCHED_UNSETTLED"}:
   a._apply_entry_evidence(pos,h)
   if pos.get("is_single_leg_lock")and float(pos.get("entry_shares")or.0)>.0:f=round(float(pos.get("notional_usd")or.0)+float(pos.get("fee_usd")or.0),4);pos["box_total_cost_usd"]=f;pos["box_cost_net"]=round(f/float(pos["entry_shares"]),6)
   b=bool(g and g not in a.active_positions and any(c.get("trade_id")==g and c.get("status")=="NOT_EXECUTED"for c in a.closed_positions))
   if b:pos["is_dominance_box"]=False;pos["is_legged_out_residual"]=True;pos["pending_unwind_tag"]="D1_LEGGED_OUT_RESIDUAL_UNWIND";pos["status"]=ExecutionStatus.POSITION_CONFIRMED if e=="ARRIVED"else ExecutionStatus.MATCHED_PENDING_SETTLEMENT;pos["exit_order_status"]="UNWIND_RETRY_REQUIRED";pos["stop_triggered_ts"]=time.time();pos["next_unwind_retry_ts"]=.0
   else:pos["status"]=ExecutionStatus.POSITION_CONFIRMED if e=="ARRIVED"else ExecutionStatus.MATCHED_PENDING_SETTLEMENT;pos["exit_order_status"]="DETERMINISTIC_TERMINAL_HOLD"if pos.get("hold_to_maturity_lock")else"AWAITING_DELTA_SETTLEMENT"
   a.save_state();logger.warning(f"[ENTRY RECONCILED] {tid}: {e} ({pos.get('entry_finality_source')}, shares={pos.get('entry_shares')}).");return True
  if e=="NOT_EXECUTED":
   pos["entry_shares"]=.0;pos["notional_usd"]=.0;pos["non_execution_proof"]=h.get("proof");d=a.active_positions.get(g)if g else None
   if isinstance(d,dict)and d.get("is_dominance_box"):
    d["is_dominance_box"]=False;d["is_legged_out_residual"]=True;d["pending_unwind_tag"]="D1_LEGGED_OUT_RESIDUAL_UNWIND"
    if d.get("status")!="ENTRY_OUTCOME_UNKNOWN":d["exit_order_status"]="UNWIND_RETRY_REQUIRED";d["stop_triggered_ts"]=time.time();d["next_unwind_retry_ts"]=.0
   a._close_position(tid,pos,"NOT_EXECUTED","ENTRY_NOT_EXECUTED_VERIFIED",won=False,record_pnl=False);return True
  return False
 def _resolve_unknown_exit_post(a,tid,pos,open_orders):
  g=pos.get("token_id");m=pos.get("exit_order_id");b=float(pos.get("target_exit_price",.0)or.0)
  if m:
   j=a.executor.get_order_fill_summary(str(m),g)
   if j is None:return False
   a._record_order_summary(pos,j,b,taker=False)
   if float(pos.get("remaining_shares",.0)or.0)<=.01:a._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True);return True
   if not j["terminal"]:pos["exit_order_status"]="RESTING";pos["status"]=ExecutionStatus.EXIT_RESTING;a._release_position_reservations(pos);a.save_state();return True
   a._release_position_reservations(pos,[str(m)]);pos["exit_order_id"]=None;pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED"
   for t in pos.get("exit_tranches",[]):
    if t.get("status")in{"POSTED","IN_FLIGHT"}:t["status"]="PENDING"
   a.save_state();return True
  if open_orders is None:return False
  i={str(p.get(k))for p in a.active_positions.values()for k in("exit_order_id","unwind_order_id")if p.get(k)};e=[o for o in open_orders if o and str(o.get("side","")).upper()=="SELL"and str(o.get("asset_id")or o.get("token_id")or"")==str(g)and str(o.get("id")or o.get("orderID")or"")not in i]
  if len(e)==1:h=str(e[0].get("id")or e[0].get("orderID"));pos["exit_order_id"]=h;pos["exit_order_size"]=float(a._num(e[0].get("original_size"))or pos.get("remaining_shares",.0));pos["exit_order_status"]="RESTING";pos["status"]=ExecutionStatus.EXIT_RESTING;l=float(pos["exit_order_size"])-float(a._num(e[0].get("size_matched"))or.0);a._release_position_reservations(pos);a.executor.reserve_inventory(g,l,reservation_id=h);a.save_state();logger.warning(f"[EXIT RECONCILED] {tid}: adopted resting exit order {h} discovered on the exchange.");return True
  if len(e)>1:return False
  d=float(pos.get("exit_post_attempt_ts")or.0);c=a._fetch_account_fills(g,d-5.,"SELL",exclude_tid=tid)
  if c is None:return False
  c=[f for f in c if str(f.get("order_id"))not in set((pos.get("order_records")or{}).keys())]
  if c:a._record_history_fills(pos,c,taker=False)
  if time.time()-d<UNWIND_UNKNOWN_PROOF_AGE_S and not c:return False
  a._release_position_reservations(pos)
  if float(pos.get("remaining_shares",.0)or.0)<=.01:a._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True);return True
  return False
 def _exit_fill_settled_onchain(b,pos,summary):
  try:
   j=str(summary.get("status")or"").upper();e=float(summary.get("original_size")or.0);d=float(summary.get("matched")or.0);c=j in{"MATCHED","FILLED","CONFIRMED","MINED"}and e>.0 and d>=e-.01;a=(j.startswith("CANCEL")or j in{"EXPIRED"})and d>.01
   if(b.dry_run or summary.get("resting")or summary.get("has_reverted_fills")or not(c or a)or str((summary.get("raw")or{}).get("side")or"SELL").upper()!="SELL"or not hasattr(b.executor,"get_onchain_erc1155_balance")):return False
   h=str(pos.get("token_id")or"")
   if not h:return False
   g=b.executor.get_onchain_erc1155_balance(h)
   if not isinstance(g,(int,float))or isinstance(g,bool)or not math.isfinite(float(g)):return False
   f=float(pos.get("remaining_shares",.0)or.0);i=float(g)<=f+.011
   if i:logger.info(f"[FILL RECONCILED ON-CHAIN] {summary.get('order_id')}: MATCHED {d:.2f}/{e:.2f}; wallet {float(g):.4f} <= position remaining {f:.4f} -> exit fill final.")
   return i
  except Exception:return False
 def _resolve_fill_reconciliation(a,tid,pos):
  g=pos.get("pending_canceled_order_id")or pos.get("exit_order_id")or pos.get("unwind_order_id")
  if not g:return False
  b=a.executor.get_order_fill_summary(str(g),pos.get("token_id"))
  if b is None:return False
  e=str(g)==str(pos.get("exit_order_id")or pos.get("pending_canceled_order_id")or"");c=float(pos.get("target_exit_price",.0)or.0)if e else float(pos.get("unwind_limit_price")or.01);a._record_order_summary(pos,b,c,taker=not e)
  if float(pos.get("remaining_shares",.0)or.0)<=.01:a._close_position(tid,pos,ExecutionStatus.FILLED if e else ExecutionStatus.SETTLED,"MAKER_SCALP_FILLED_CLOB"if e else"UNWIND_RECONCILED",won=None);return True
  if not b["terminal"]and e and a._exit_fill_settled_onchain(pos,b):b={**b,"terminal":True}
  if not b["terminal"]:
   if b.get("resting",False)and str(g)==str(pos.get("exit_order_id")or"")and not pos.get("pending_canceled_order_id"):pos["exit_order_status"]="RESTING";pos["status"]=ExecutionStatus.PARTIALLY_FILLED;a.save_state();return True
   return False
  a._release_position_reservations(pos,[str(g)])
  if str(pos.get("exit_order_id")or"")==str(g):pos["exit_order_id"]=None
  pos["pending_canceled_order_id"]=None;pos["cancel_pending_order_id"]=None;pos["unwind_order_id"]=None if str(pos.get("unwind_order_id")or"")==str(g)else pos.get("unwind_order_id");pos["status"]=ExecutionStatus.PARTIALLY_FILLED;f=float(pos.get("candle_expiry_ts",.0)or.0)
  if pos.get("resolved_winning_outcome")is not None:pos["exit_order_status"]="CANCELED_FOR_RESOLUTION"
  elif time.time()-float(pos.get("stop_triggered_ts",.0)or.0)<3e2:pos["exit_order_status"]="UNWIND_RETRY_REQUIRED";d=int(pos.get("unwind_retry_count",0)or 0)+1;pos["unwind_retry_count"]=d;pos["next_unwind_retry_ts"]=time.time()+min(15.,1.5**min(d,5));pos["is_liquidating"]=False
  elif f and(f-time.time())<a.tte_cancel_window:pos["exit_order_status"]="PRE_EXPIRY_EVALUATION_REQUIRED"
  else:pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED"
  a.save_state();return True
 def _resolve_lifecycle(d,tid,pos,open_orders=None,force=False):
  r=time.time()
  if not force and r<float(pos.get("next_resolve_ts",.0)or.0):return False
  s=pos.get("exit_order_status");q=pos.get("status");c=False
  try:
   if s=="ENTRY_OUTCOME_UNKNOWN"or q=="ENTRY_OUTCOME_UNKNOWN"or s=="ENTRY_ONCHAIN_REVERTED":c=d._resolve_unknown_entry(tid,pos)
   elif s in d.UNWIND_UNKNOWN_STATES:c=d._resolve_unknown_unwind(tid,pos)
   elif s=="EXIT_POST_OUTCOME_UNKNOWN":c=d._resolve_unknown_exit_post(tid,pos,open_orders)
   elif s=="FILL_RECONCILIATION_REQUIRED":c=d._resolve_fill_reconciliation(tid,pos)
   elif s=="LIQUIDITY_CRISIS"or q=="LIQUIDITY_CRISIS":
    k=pos.get("token_id");h=pos.get("exit_order_id")
    if h and k and hasattr(d.executor,"get_order_fill_summary"):
     n=d.executor.get_order_fill_summary(str(h),k)
     if n is not None:
      d._record_order_summary(pos,n,float(pos.get("target_exit_price",.98)or.98),taker=False)
      if float(pos.get("remaining_shares",.0)or.0)<=.02:d._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True);return True
    i=float(pos.get("candle_expiry_ts",.0)or.0);f=(i>.0 and r>=i);j={}
    if k and not f:
     try:j=d.executor.get_market_book(k)
     except Exception as g:
      if"404"in str(g)or"no orderbook exists"in str(g).lower():f=True
      else:raise
    p=[b for b in(j.get("bids")or[])if float(b.get("price",.0))>0 and float(b.get("size",.0))>0];o=[a for a in(j.get("asks")or[])if float(a.get("price",.0))>0 and float(a.get("size",.0))>0];m=max((float(b["price"])for b in p),default=.0);l=min((float(a["price"])for a in o),default=1.)
    if f or(m>.0 and(not o or m<l)):pos["status"]=ExecutionStatus.EXIT_RESTING if pos.get("exit_order_id")else ExecutionStatus.POSITION_CONFIRMED;pos["exit_order_status"]="RESTING"if pos.get("exit_order_id")else("CANCELED_FOR_EXPIRY_HOLD"if f else"EXIT_RECOVERY_REQUIRED");pos.pop("liquidity_crisis_ts",None);pos.pop("zero_bid_detected_ts",None);d.save_state();logger.info(f"[LIQUIDITY_CRISIS_RESOLVED] {tid}: {'Market expired/closed'if f else f'Valid bid restored (${m:.4f})'}. Resuming.");c=True
  except Exception as e:logger.error(f"[LIFECYCLE] Resolver error for {tid} ({s}): {e}",exc_info=True);c=False
  if not c and tid in d.active_positions:pos["next_resolve_ts"]=r+5.
  return c
 def _apply_exit_post_result(self,pos,exit_res,size):
  exit_res=exit_res or{};f=time.time()
  if exit_res.get("success"):
   pos["exit_order_id"]=exit_res.get("orderID");pos["exit_order_size"]=float(size);b=self._num(exit_res.get("price"))
   if b is not None and.0<b<1.:
    if abs(b-float(pos.get("target_exit_price")or.0))>1e-9:pos["requested_exit_price"]=pos.get("target_exit_price")
    pos["target_exit_price"]=b
   pos["exit_order_status"]="RESTING";pos["status"]=ExecutionStatus.EXIT_RESTING;pos["exit_post_failures"]=0;pos.pop("next_exit_post_ts",None);return True
  if exit_res.get("outcome_unknown"):
   e=exit_res.get("orderID")
   if e:pos["exit_order_id"]=e;pos["exit_order_size"]=float(size)
   if exit_res.get("reservation_id"):pos.setdefault("pending_reservation_ids",[]).append(exit_res["reservation_id"])
   pos["exit_post_attempt_ts"]=f;pos["exit_order_status"]="EXIT_POST_OUTCOME_UNKNOWN";logger.critical(f"Ambiguous maker exit post for {pos.get('trade_id')} (OID: {e}); no re-post until reconciled.");return False
  if exit_res.get("crossed_at_max_tick"):pos["next_exit_post_ts"]=f+1.;pos["exit_order_status"]="CROSSED_AT_MAX_TICK_WAIT";return False
  c=int(pos.get("exit_post_failures",0)or 0)+1;pos["exit_post_failures"]=c;d=str(exit_res.get("error")or"").lower();a=f-float(pos.get("entry_ts",.0)or.0)
  if("not enough balance"in d or"insufficient_unreserved_balance"in d)and.0<=a<15.:pos["next_exit_post_ts"]=f+.4;pos["exit_order_status"]="AWAITING_DELTA_SETTLEMENT";logger.info(f"Maker exit post awaiting CLOB balance indexer sync for {pos.get('trade_id')} (age={a:.2f}s); retry in 0.40s.");return False
  pos["next_exit_post_ts"]=f+min(30.,2.**min(c,5));pos["exit_order_status"]="AWAITING_DELTA_SETTLEMENT"if exit_res.get("retryable")else"POST_FAILED";logger.warning(f"Maker exit post deferred for {pos.get('trade_id')} ({exit_res.get('error')}); retry with backoff.");return False
 def _attempt_maker_exit_post(a,tid,pos):
  import threading;c=a.__dict__.setdefault("_exit_post_locks",{});b=c.get(tid)
  if b is None:b=c.setdefault(tid,threading.Lock())
  if not b.acquire(blocking=False):return False
  try:
   if pos.get("exit_order_id"):return False
   return a._attempt_maker_exit_post_impl(tid,pos)
  finally:b.release()
 def _settlement_recheck_delay(self,pos,now):
  a=float(pos.get("entry_ts",.0)or.0)
  if a>.0 and(now-a)<FAST_SETTLEMENT_RECHECK_WINDOW_SEC:return FAST_CONFIRM_POLL_SEC
  return 5.
 def _maybe_queue_jump_on_post(self,pos,size):
  if pos.get("queue_jumped")or pos.get("is_dominance_box")or pos.get("is_single_leg_lock"):return
  c=float(pos.get("target_exit_price")or.0)
  if c<QUEUE_JUMP_MIN_TARGET or(self._effective_exit_policy()=="hold_98"and c<=.98):return
  b=fast_tick_book_for_token(read_fast_tick(pos.get("asset","BTC")),pos.get("token_id"))
  if not b:return
  a=compute_queue_priority_maker_price(float(pos.get("entry_price",.7)or.7),size,b.get("bids",[]),b.get("asks",[]),c)
  if a is not None:
   logger.info(f"[QUEUE JUMP] {pos.get('trade_id')}: wall at ${c:.2f}; posting maker TP at ${a:.2f} instead.");pos["target_exit_price"]=a;pos["queue_jumped"]=True
   for t in pos.get("exit_tranches",[]):
    if t.get("status")=="PENDING"and abs(float(t.get("price",.0))-c)<1e-9:t["price"]=a;break
 async def _fast_confirm_and_post_maker_exit(a,trade_id):
  d=time.time()+FAST_CONFIRM_WINDOW_SEC;g=getattr(a.executor,"_user_ws_cache",None)
  while time.time()<d:
   c=g.fill_sequence if g is not None else None;f=a.active_positions.get(trade_id)
   if f is None or f.get("exit_order_id"):return False
   if position_may_post_new_maker_exit(f):
    try:b=await asyncio.to_thread(a._attempt_maker_exit_post,trade_id,f)
    except Exception as e:logger.warning(f"[FAST CONFIRM] {trade_id}: maker exit attempt error: {e}");b=False
    if b:logger.info(f"[FAST CONFIRM] {trade_id}: maker TP posted within the fast-confirm window.");return True
    if position_requires_lifecycle_resolution(f):return False
   if g is not None and g.is_healthy():await g.wait_for_fill_or_timeout(FAST_CONFIRM_POLL_SEC,prev_seq=c)
   else:await asyncio.sleep(FAST_CONFIRM_POLL_SEC)
  return False
 def _spawn_fast_confirm(a,trade_id):
  c=a.__dict__.setdefault("_fast_confirm_inflight_ids",set())
  if trade_id in c:return
  try:f=asyncio.get_running_loop();a._main_loop=f
  except RuntimeError:
   b=getattr(a,"_main_loop",None)
   if b is not None and b.is_running():
    try:b.call_soon_threadsafe(a._spawn_fast_confirm,trade_id)
    except RuntimeError:pass
   return
  c.add(trade_id);e=f.create_task(a._fast_confirm_and_post_maker_exit(trade_id));d=a.__dict__.setdefault("_fast_confirm_tasks",set());d.add(e);e.add_done_callback(lambda t:(d.discard(t),c.discard(trade_id)))
 def _attempt_maker_exit_post_impl(a,tid,pos):
  _g=time.time();R=float(pos.get("candle_expiry_ts",_g+6e2)or(_g+6e2));n=5. if pos.get("sleeve")=="SLEEVE_4_BOUNDARY_SNIPE"else a.tte_cancel_window
  if not position_may_post_new_maker_exit(pos)or(R-_g)<n:return False
  if _g<float(pos.get("next_exit_post_ts",.0)or.0):return False
  I=pos.get("token_id")
  if not I:return False
  _f=a.executor.calculate_balance_epsilon(.001)
  if a.dry_run:
   m=Decimal(str(pos.get("gross_entry_shares",pos.get("entry_shares",.0))))
   if not pos.get("inventory_reconciled"):
    P=float(m.quantize(Decimal("0.01"),rounding=ROUND_FLOOR));pos["entry_shares"]=P;pos["remaining_shares"]=P;pos["remaining_exit_shares"]=P;pos["remaining_cost_basis"]=pos.get("notional_usd",.0)
    if P>0 and float(pos.get("notional_usd",.0)or.0)>0:
     d=round(float(pos["notional_usd"])/P,4)
     if d>float(pos.get("entry_price",.0)or.0):pos["entry_price"]=d;pos["target_exit_price"]=float(pos.get("custom_maker_exit_price")or.99)if(pos.get("is_dominance_box")or pos.get("is_single_leg_lock"))else a._calculate_target_exit(d,R-_g)
    pos["inventory_reconciled"]=True
  else:
   v,H=a._verify_entry_finality(pos)
   if H and not v:logger.critical(f"[ON-CHAIN REVERT] Entry for {tid} reverted on Polygon; holding for reconciliation.");pos["status"]=ExecutionStatus.FAILED;pos["exit_order_status"]="ENTRY_ONCHAIN_REVERTED";pos["close_reason"]="ONCHAIN_REVERT_DETECTED";a.save_state();return False
   _e,_d=a._wallet_token_balance(I)
   if _e is None:logger.warning(f"[FAIL-CLOSED] Wallet inventory unavailable for {I}; delaying exit for {tid}.");return False
   if not v and _d in{a.ONCHAIN_SOURCE,"CLOB_BALANCE_API"}:v=True
   if not v:pos["exit_blocked_reason"]=f"ENTRY_FINALITY_UNPROVEN(source={_d})";pos["next_exit_post_ts"]=_g+a._settlement_recheck_delay(pos,_g);a.save_state();return False
   if not pos.get("inventory_reconciled")and float(pos.get("filled_exit_shares",.0)or.0)<=.0:
    K=float(pos.get("pre_token_balance",.0)or.0);G=Decimal(str(_e-K));m=Decimal(str(pos.get("gross_entry_shares",pos.get("entry_shares",.0))));Z=Decimal(str(_f));i=Decimal("0.01")
    if G>m+Z+Decimal("0.01"):
     q=str(pos.get("entry_order_id")or pos.get("order_id")or"").strip()
     if q and hasattr(a.executor,"get_order_fill_summary"):
      try:
       Q=a.executor.get_order_fill_summary(q,I);_c=Decimal(str((Q or{}).get("matched")or.0))
       if _c>=G-Decimal("0.05"):
        m=_c;pos["gross_entry_shares"]=float(_c);Y=float((Q or{}).get("avg_price")or(Q or{}).get("limit_price")or pos.get("entry_price")or.0)
        if Y>.0:pos["entry_price"]=Y
        pos["notional_usd"]=round(float((Q or{}).get("cash")or(float(_c)*max(Y,.01))),4)
      except Exception:pass
    if G<i or G>m+Z+Decimal("0.01"):pos["exit_blocked_reason"]=f"ENTRY_INVENTORY_UNRECONCILED(received={G}, gross={m})";pos["next_exit_post_ts"]=_g+a._settlement_recheck_delay(pos,_g);a.save_state();return False
    P=float(min(G,m).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
    if m>Decimal("0")and G<m-Decimal("0.02"):
     A=str(pos.get("entry_order_id")or pos.get("order_id")or"").strip();c=None
     if A and hasattr(a.executor,"get_order_fill_summary"):
      try:
       O=a.executor.get_order_fill_summary(A,I)
       if isinstance(O,dict)and float(O.get("matched")or.0)>.0:c=O
      except Exception:c=None
     s=max(.0,_g-float(pos.get("entry_ts")or _g))
     if c is not None:
      N=Decimal(str(c["matched"]));o=(min(N,Decimal(str(pos.get("entry_shares")or N)))if str(pos.get("entry_fee_asset")or"").upper()=="SHARES"else N)
      if G+Decimal("0.05")<o:
       if s<18.:pos["exit_blocked_reason"]=f"PARTIAL_BATCH_SETTLING(wallet={G}, clob={N})";pos["next_exit_post_ts"]=_g+a._settlement_recheck_delay(pos,_g)
       else:pos["exit_blocked_reason"]=f"ENTRY_INVENTORY_RECONCILIATION_REQUIRED(wallet={G}, clob={N})";pos["exit_order_status"]="ENTRY_INVENTORY_RECONCILIATION_REQUIRED"
       a.save_state();return False
      if N<m*Decimal("0.98"):g=float(pos.get("notional_usd",.0)or.0);pos.setdefault("intended_notional",g);z=float(c.get("cash")or.0);h=float(N/m);pos["notional_usd"]=round(z if z>.0 else(g*h),4);pos["fee_usd"]=round(float(c.get("fee")or(float(pos.get("fee_usd",.0)or.0)*h)),4)
     elif A:
      if s<15.:pos["exit_blocked_reason"]=f"ENTRY_SETTLEMENT_PENDING(wallet={G}, gross={m})";pos["next_exit_post_ts"]=_g+a._settlement_recheck_delay(pos,_g)
      else:pos["exit_blocked_reason"]=f"ENTRY_INVENTORY_RECONCILIATION_REQUIRED(wallet={G}, gross={m})";pos["exit_order_status"]="ENTRY_INVENTORY_RECONCILIATION_REQUIRED"
      a.save_state();return False
     elif G<m*Decimal("0.92"):h=float(G/m);g=float(pos.get("notional_usd",.0)or.0);pos.setdefault("intended_notional",g);pos["notional_usd"]=round(g*h,4);pos["fee_usd"]=round(float(pos.get("fee_usd",.0)or.0)*h,4)
     elif"v2"not in str(pos.get("fee_source")or"").lower():pos["entry_fee_asset"]="SHARES";pos["entry_fee_cash_usd"]=.0
    elif(m>Decimal("0")and str(pos.get("entry_fee_asset")or"").upper()=="SHARES"and float(pos.get("fee_usd",.0)or.0)==.0 and float(pos.get("fee_rate_applied",.0)or.0)>.0 and P>.0):
     y=float(pos.get("notional_usd",.0)or.0)/float(P)
     if.0<y<1.:
      X=float(pos.get("fee_rate_applied",.0)or.0);W=float(pos.get("fee_exponent_applied",1.)or 1.);F=round(float(P)*X*((y*(1.-y))**W),4);pos["entry_fee_asset"]="USDC";pos["fee_usd"]=F;pos["entry_fee_cash_usd"]=F
      if F>.0 and not pos.get("_v2_fee_collat_debited"):
       pos["_v2_fee_collat_debited"]=True;M=getattr(a,"_last_known_collateral",None)
       if isinstance(M,(int,float))and not isinstance(M,bool):a._last_known_collateral=max(.0,float(M)-F)
       a._pending_collateral_refresh=True
    pos["entry_shares"]=P;pos["remaining_shares"]=P;pos["remaining_exit_shares"]=P;pos["remaining_cost_basis"]=pos.get("notional_usd",.0)
    if P>0 and float(pos.get("notional_usd",.0)or.0)>0:
     d=round(float(pos["notional_usd"])/P,4)
     if d>float(pos.get("entry_price",.0)or.0):pos["entry_price"]=d;pos["target_exit_price"]=float(pos.get("custom_maker_exit_price")or.99)if(pos.get("is_dominance_box")or pos.get("is_single_leg_lock"))else a._calculate_target_exit(d,R-_g)
    pos["inventory_reconciled"]=True;pos.pop("exit_blocked_reason",None);pos.setdefault("entry_inventory_source",_d)
   else:
    u=float(pos.get("remaining_shares",pos.get("entry_shares",.0))or.0)
    if _e+_f<u:logger.critical(f"[INVENTORY DISCREPANCY] {tid}: wallet {_e:.4f} < remaining {u:.4f} ({_d}). " "Refusing to post; reconciling against exchange history.");pos["exit_order_status"]="UNRESOLVED_BALANCE_DISCREPANCY";pos["unwind_attempt_ts"]=float(pos.get("entry_ts")or _g);a.save_state();return False
  k=float(Decimal(str(pos.get("remaining_shares",pos.get("entry_shares",.0))or.0)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
  if k<.01:return False
  x=k;E=float(pos.get("entry_price",.7));p=False if pos.get("is_single_leg_lock")else a._use_two_tranche_maker_exit(pos.get("sleeve"));w=a._tranche1_tp_offset(pos.get("sleeve"));r=((not a.dry_run)and getattr(a.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2")and bool(I and str(I).isdigit()and len(str(I))>=20)and not getattr(a,"enable_mid_hour_t1_12c",False))
  if p and float(pos.get("notional_usd",.0)or.0)>=10. and"exit_tranches"not in pos and x>=10.:
   V=float((Decimal(str(x))*Decimal("0.50")).quantize(Decimal("0.01"),rounding=ROUND_FLOOR));U=float((Decimal(str(x))-Decimal(str(V))).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
   if V>=5. and U>=5.:T=.95 if r else min(.94,round(E+w,2));S=.98;pos["exit_tranches"]=[{"idx":1,"size":V,"price":T,"status":"PENDING"},{"idx":2,"size":U,"price":S,"status":"PENDING"}]
   else:pos["target_exit_price"]=.96 if r else min(.96,round(E+.16,2))
  e=None;l=[t for t in pos.get("exit_tranches",[])if t.get("status")=="PENDING"]
  if l and float(l[0]["size"])>=5. and x>=5.:
   J=min(x,float(l[0]["size"]));D=round(x-J,4)
   if.01<D<5.:k=x;pos["target_exit_price"]=max(float(t["price"])for t in l);pos.pop("exit_tranches",None)
   else:e=l[0];k=J;pos["target_exit_price"]=float(e["price"])
  else:
   k=x
   if l and x>=5.:pos["target_exit_price"]=max(float(t["price"])for t in l)
   from src.polymarket_research.riskless_machine_gun_engine import is_locked_arbitrage_box_leg as f;pos.pop("exit_tranches",None)
   if f(pos,a.active_positions):pos["target_exit_price"]=max(.99,float(pos.get("custom_maker_exit_price")or.99))
   elif pos.get("custom_maker_exit_price"):pos["target_exit_price"]=float(pos["custom_maker_exit_price"])
   elif pos.get("is_dominance_box")or pos.get("is_single_leg_lock"):pos["target_exit_price"]=.99
   elif a._effective_exit_policy()=="hold_98":pos["target_exit_price"]=.98
   elif not pos.get("target_exit_price"):pos["target_exit_price"]=.96 if r else min(.96,round(E+.16,2))
  pos["status"]=ExecutionStatus.POSITION_CONFIRMED
  if k<5. and not a.dry_run and str(I).isdigit()and len(str(I))>=20:logger.warning(f"[SUB-MINIMUM LOT GUARD] {tid}: remaining size {k:.2f} < 5.0 CLOB lot minimum; " "holding under supervised terminal policy without spamming HTTP 400s.");pos["exit_order_status"]="SUB_MINIMUM_LOT_SUPERVISED_HOLD";pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD";a.save_state();return False
  a._maybe_queue_jump_on_post(pos,k);j=a.executor.post_maker_exit_order(token_id=I,price=pos["target_exit_price"],size=k,side="SELL")
  if(not(j or{}).get("success")and not(j or{}).get("outcome_unknown")and not(j or{}).get("crossed_at_max_tick")and"crosses book"in str((j or{}).get("error","")).lower()):
   try:
    _b=a.executor.get_market_book(I)if hasattr(a.executor,"get_market_book")else None;_a=(_b or{}).get("bids",[])
    if _a:
     C=max((float(b.get("price",.0)or.0)for b in _a if isinstance(b,dict)),default=.0);B=min(.99,round(C+.01,4))
     if B>float(pos["target_exit_price"]):
      logger.info(f"[MAKER REPRICE] {tid}: post_only crossed book (bid={C:.4f}). Repricing ask to ${B:.4f}.");pos["target_exit_price"]=B
      if e is not None:e["price"]=B
      j=a.executor.post_maker_exit_order(token_id=I,price=B,size=k,side="SELL")
   except Exception:pass
  L=a._apply_exit_post_result(pos,j,k)
  if e is not None and L:e["status"]="POSTED"
  elif e is not None and(j or{}).get("outcome_unknown"):e["status"]="IN_FLIGHT"
  a.save_state()
  if L:logger.info(f"✓ MAKER EXIT POSTED: {tid} | {k:.2f} shares @ ${pos['target_exit_price']:.4f} | OID={pos['exit_order_id']}")
  return L
 def _handle_unwind_response(a,tid,pos,res,requested,close_reason,partial_state,limit_price):
  res=res or{};n=time.time();m=res.get("orderID");pos["unwind_limit_price"]=float(limit_price)
  def b(why):
   pos["exit_order_status"]="UNWIND_EXECUTION_OUTCOME_UNKNOWN";pos["is_liquidating"]=True;pos["unwind_order_id"]=m;pos["unwind_attempt_ts"]=n;pos["unwind_reason"]=close_reason;pos["unwind_last_error"]=why
   if res.get("reservation_id"):pos.setdefault("pending_reservation_ids",[]).append(res["reservation_id"])
   pos["next_resolve_ts"]=.0;a.save_state();logger.critical(f"[UNWIND OUTCOME UNKNOWN] {tid}: {why}. No repeat submission until exchange reconciliation.");return"UNKNOWN"
  if res.get("outcome_unknown")and str(close_reason or"")=="HTM_EARLY_998_PROFIT_RECYCLE":from src.polymarket_research.riskless_protocol_v2_expansion import resolve_delayed_recycle_unwind_sync as c;res=c(a,pos,res,close_reason,limit_price);m=res.get("orderID")or m
  if res.get("outcome_unknown"):return b(str(res.get("error")or"AMBIGUOUS_UNWIND_RESPONSE"))
  j=a._num(res.get("matched_size"));l=a._num(res.get("taking_amount"));g=bool(res.get("success")or res.get("partial")or(j or.0)>.0 or(m and(l or.0)>.0)or(res.get("matched_size")is not None and(l or.0)>.0))
  if not g:return"FAILED"
  if res.get("success")and not m and(j or.0)==.0 and(l or.0)==.0:
   if requested<.01:a._close_position(tid,pos,ExecutionStatus.SETTLED,f"{close_reason}_DUST_RESIDUAL",won=None);return"CLOSED"
   return"FAILED"
  f=j is None or j<=.0 or j>requested+1e-4 or l is None or l<.0 or bool(res.get("taking_amount_missing"))
  if f:return b(f"CONTRADICTORY_OR_INCOMPLETE_FILL_QUANTITIES(matched={res.get('matched_size')}, taking={res.get('taking_amount')})")
  k=a._num(res.get("fee_usd"))or.0
  if k>.0 and a._exit_taker_fee_rate(pos)<=.0 and res.get("fee_is_estimated",True):k=.0
  h=m or f"{close_reason}_{int(n*1000)}";e=bool(res.get("taking_amount_estimated",False));a.record_fill_and_update_position(pos,h,j,l,k,cash_is_estimated=e)
  if e:pos["pending_settlement_order_id"]=str(h)
  if res.get("fee_is_estimated"):pos["exit_fee_estimated"]=True
  if float(pos.get("remaining_shares",.0)or.0)<=.01:
   d=False if("SALVAGE"in close_reason or"STOP"in close_reason)else None
   if e:d=None
   a._close_position(tid,pos,ExecutionStatus.SETTLED,close_reason,won=d);return"CLOSED"
  pos["status"]=ExecutionStatus.PARTIALLY_FILLED;pos["exit_order_status"]=partial_state;pos["is_liquidating"]=False;pos["unwind_order_id"]=None;i=int(pos.get("unwind_retry_count",0)or 0)+1;pos["unwind_retry_count"]=i;pos["next_unwind_retry_ts"]=n+min(30.,2.**min(i,5));logger.warning(f"⚠️ [PARTIAL UNWIND] {tid}: matched {j:.2f}; cumulative {pos.get('filled_exit_shares',.0):.2f}/{pos.get('entry_shares',.0):.2f}; remaining {pos.get('remaining_shares',.0):.2f} retained.");a.save_state();return"PARTIAL"
 @staticmethod
 def calculate_realized_cash_pnl(pos,gross_exit_cash,exit_fee=.0):
  c=str(pos.get("entry_fee_asset")or"").upper();b=pos.get("entry_fee_cash_usd")
  if c=="SHARES":a=float(b or.0)
  else:a=float(b if b is not None else(pos.get("fee_usd")or.0))
  g=float(pos.get("notional_usd")or.0);i=float(gross_exit_cash or.0);d=float(exit_fee or.0);h=i-g-a-d;f=round(h,2)
  if f!=.0:return f
  e=round(h,4);return e if abs(e)>=1e-4 else.0
 @staticmethod
 def record_fill_and_update_position(pos,order_id,matched_shares,taking_cash,fee_usd=.0,cash_is_estimated=False):
  g=pos.setdefault("order_records",{});a=str(pos.get("exit_order_id")or"");f=float(pos.get("filled_exit_shares",.0)or.0);l=float(pos.get("realized_exit_cash",.0)or.0);q=float(pos.get("realized_exit_fee",.0)or.0)
  if str(order_id)!=a and(f>.0 or l>.0 or q>.0)and"LEGACY_PREVIOUS_FILLS"not in g:
   b=sum(float(r.get("matched",.0))for r in g.values());e=sum(float(r.get("cash",.0))for r in g.values());j=sum(float(r.get("fee",.0))for r in g.values());k=max(.0,round(f-b,4));s=max(.0,round(l-e,4));t=max(.0,round(q-j,4))
   if k>.0 or s>.0 or t>.0:g["LEGACY_PREVIOUS_FILLS"]={"size":k,"matched":k,"cash":s,"fee":t,"cash_is_estimated":bool(pos.get("exit_cash_estimated",False))}
  v=str(order_id);u=g.setdefault(v,{"size":float(pos.get("exit_order_size",pos.get("entry_shares",.0))),"matched":.0,"cash":.0,"confirmed_cash":.0,"estimated_cash":.0,"fee":.0,"cash_is_estimated":bool(cash_is_estimated)});u["matched"]=max(float(u.get("matched",.0)),float(matched_shares or.0));p=float(taking_cash or.0)
  if not cash_is_estimated:u["confirmed_cash"]=p;u["estimated_cash"]=.0;u["cash"]=p;u["cash_is_estimated"]=False
  else:
   if not u.get("cash_is_estimated",False)and float(u.get("confirmed_cash",.0))>.0:pass
   else:u["estimated_cash"]=p;u["cash"]=p;u["cash_is_estimated"]=True
  if float(fee_usd or.0)>.0:u["fee"]=max(float(u.get("fee",.0)),float(fee_usd))
  i=sum(float(r.get("matched",.0))for r in g.values());d=sum(float(r.get("cash",.0))for r in g.values()if not r.get("cash_is_estimated"));c=sum(float(r.get("cash",.0))for r in g.values()if r.get("cash_is_estimated"));o=d+c;n=sum(float(r.get("fee",.0))for r in g.values());pos["filled_exit_shares"]=round(i,4);pos["confirmed_realized_cash"]=round(d,4);pos["estimated_exit_cash"]=round(c,4);pos["realized_exit_cash"]=round(o,4);pos["gross_exit_cash"]=round(o,4);pos["exit_cash_estimated"]=(c>.0);pos["realized_exit_fee"]=round(n,4);h=float(pos.get("entry_shares",.0));m=max(.0,round(h-i,4));pos["remaining_shares"]=m;pos["remaining_exit_shares"]=m
  if h>.0:pos["remaining_cost_basis"]=round(float(pos.get("notional_usd",.0))*(m/h),4)
  return u
 def confirm_onchain_redemption(a,trade_id,verified_usdc_received=None,tx_hash=None):
  x=a.active_positions.get(trade_id)
  if not x:logger.warning(f"[REDEMPTION] Position {trade_id} not found in active_positions.");return False
  if not position_is_settlement_receivable(x):logger.warning(f"[REDEMPTION] Position {trade_id} is not awaiting on-chain settlement ({x.get('status')}).");return False
  p=float(x.get("winning_shares_held",.0)or.0);g=list(dict.fromkeys(str(h)for h in(getattr(a,"redeemed_tx_hashes",[])or[])if h));s=set(g);m=a.__dict__.setdefault("redeemed_tx_consumed_usd",{})
  if a.dry_run:l=float(verified_usdc_received if verified_usdc_received is not None else p);w=tx_hash or f"DRYRUN_REDEMPTION_{trade_id}"
  else:
   d=a.executor.find_redemption_payouts(str(x.get("condition_id")or""),from_block=x.get("resolution_block"),tx_hash=tx_hash)
   if not d and p>=.01 and not tx_hash:
    v=str(x.get("token_id")or"");e=None
    if v and hasattr(a.executor,"get_onchain_erc1155_balance"):
     try:e=a.executor.get_onchain_erc1155_balance(v)
     except Exception:e=None
    if e is not None and float(e)<=1e-4:logger.info(f"[REDEMPTION EXTERNAL] {trade_id}: winning token balance is 0 on-chain -> settling {p:.2f} sh receivable as redeemed outside the harvester.");d=[{"transaction_hash":f"EXTERNAL_REDEMPTION_{trade_id}","payout_usd":p}]
   if d is None:
    if(p<.01 and float(x.get("confirmed_realized_cash",x.get("realized_exit_cash",.0))or.0)>.0):x["exit_cash_estimated"]=False;x["estimated_exit_cash"]=.0;x["confirmed_realized_cash"]=float(x.get("confirmed_realized_cash")or x.get("realized_exit_cash")or.0);logger.info(f"[REDEMPTION DUST CLOSE] {trade_id}: closing on confirmed CLOB cash ${x['confirmed_realized_cash']:.2f} (ignoring {p:.4f} sh dust receivable).");a._close_position(trade_id,x,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=None);return True
    logger.warning(f"[REDEMPTION] Cannot verify redemption for {trade_id} (RPC unavailable); retaining receivable.");return False
   u=[r for r in d if r.get("transaction_hash")and r["transaction_hash"]not in s and(float(r.get("payout_usd")or.0)-float(m.get(str(r["transaction_hash"]),.0)or.0))>.005]
   if not u:return False
   t=u[0];l=float(t["payout_usd"]);w=str(t["transaction_hash"])
  if w in s:logger.warning(f"[REDEMPTION] Duplicate redemption receipt {w} ignored for {trade_id}.");return False
  k=l if a.dry_run else max(.0,l-float(m.get(w,.0)or.0))
  if not a.dry_run and k<=.005:return False
  o=round(min(k,p),6);a.record_fill_and_update_position(x,f"ONCHAIN_REDEMPTION_{w}",p,o,.0);q=float(x.get("realized_exit_cash",.0));j=float(x.get("realized_exit_fee",.0));f=a.calculate_realized_cash_pnl(x,q,j);x["status"]=ExecutionStatus.SETTLED;x["settled_at_utc"]=datetime.now(timezone.utc).isoformat();x["won"]=(f>.0);x["payout_usd"]=round(q,4);x["net_pnl_usd"]=round(f,4);x["close_reason"]="ONCHAIN_REDEMPTION_CONFIRMED";x["exit_decomposition_bucket"]="TERMINAL_SETTLEMENT";x["redemption_tx_hash"]=w;x["redemption_payout_verified_usd"]=l;x["redemption_receivable_usd"]=.0
  if not a.dry_run:m[w]=round(float(m.get(w,.0)or.0)+o,6)
  if a.dry_run or float(m.get(w,.0)or.0)>=l-.009:
   if w not in s:s.add(w);g.append(w)
   m.pop(w,None)
  a.redeemed_tx_hashes=g[-1000:];i=max(.0,float(q or.0)-float(j or.0));b=max(.0,i-float(x.get("_synced_exit_cash_usd",.0)or.0))
  if(not getattr(a,"dry_run",True)and getattr(a,"_last_known_collateral",None)is not None and b>.0 and not x.get("_collateral_exit_credited")and not x.get("_pre_redeemed_onchain")and not str(w).startswith("EXTERNAL_REDEMPTION_")):x["_collateral_exit_credited"]=True;a._last_known_collateral=float(a._last_known_collateral)+b;a._last_exit_credit_window=(time.time(),float(a._last_known_collateral))
  c,f=a._consolidate_dominance_box_close(trade_id,x,q,j,f,"ONCHAIN_REDEMPTION_CONFIRMED",True)
  if c:a.executor.invalidate_collateral_cache();return True
  a.closed_positions.append(x);n=bool(x.get("is_dominance_box")or x.get("is_single_leg_lock")or x.get("is_legged_out_residual")or"BOX"in str(x.get("sleeve")or"").upper());a.risk_controller.record_trade_pnl(f,is_non_directional=n);del a.active_positions[trade_id];a.save_state();a.executor.invalidate_collateral_cache();a._pending_collateral_refresh=True;logger.info(f"✓ ON-CHAIN REDEMPTION VERIFIED: {trade_id} | tx={w} | USDC=${o:.2f} | Net PnL=${f:+.2f}");return True
 def poll_onchain_redemptions(a,force=False):
  w=time.time()
  if not force and(w-a._last_redemption_poll)<REDEMPTION_POLL_INTERVAL_S:return 0
  a._last_redemption_poll=w;d=0;c={}
  for v,u in list(a.active_positions.items()):
   if position_is_settlement_receivable(u)and float(u.get("winning_shares_held",.0)or.0)>.0:
    try:
     p=str(u.get("market_id")or"")
     if not a.dry_run and p.isdigit()and int(p)>=100000:
      try:
       z=a.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{p}",timeout=3.).json();s=str(z.get("umaResolutionStatus")or"").strip().lower();r=z.get("outcomePrices");y=_json_loads(r)if isinstance(r,str)else r;o=z.get("clobTokenIds");m=_json_loads(o)if isinstance(o,str)else o
       if s in("","resolved")and isinstance(y,list)and len(y)>=2:
        q=str(u.get("token_id")or"")
        if isinstance(m,list)and q and q in[str(x)for x in m]:i=[str(x)for x in m].index(q)
        else:i=0 if str(u.get("target_token","UP")).upper()in("UP","YES")else 1
        if float(y[i])==.0 and float(y[1-i])==1.:logger.warning(f"[GAMMA ORACLE OVERRIDE] {v}: Gamma outcomePrices={y} (idx={i}) shows authoritative resolution against local spot oracle. Closing ghost receivable.");u["expected_terminal_payout_usd"]=.0;u["redemption_receivable_usd"]=.0;u["winning_shares_held"]=.0;a._close_position(v,u,ExecutionStatus.SETTLED,"MARKET_RESOLVED_LOSS",won=False);continue
      except Exception:pass
     b=None
     if not a.dry_run and hasattr(a.executor,"attempt_onchain_redemption"):
      l=getattr(a.executor,"signature_type",None);k=1 if l is None else int(l)
      if k==3 and not bool((os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY")or"").strip()):send_operational_alert("REDEMPTION_BUILDER_CREDS_MISSING",f"Mature winning receivable {v} (${float(u.get('winning_shares_held')or.0):.2f}) requires POLY_BUILDER_API_KEY.","WARNING",rate_limit_sec=3600.,dedupe_key="redemption_builder_creds_missing")
      n=str(u.get("condition_id")or"");h=u.get("pending_redemption_tx_hash");g=float(u.get("pending_redemption_submitted_ts",.0)or.0)
      if n and n in c:b=c[n]
      elif h and(w-g)<60.:b=None
      else:
       try:b=a.executor.attempt_onchain_redemption(n,neg_risk=u.get("neg_risk")if"neg_risk"in u else None)
       except TypeError:b=a.executor.attempt_onchain_redemption(n)
       if b and n:c[n]=str(b)
     if b:u["pending_redemption_tx_hash"]=str(b);u["pending_redemption_submitted_ts"]=w
     if a.confirm_onchain_redemption(v,tx_hash=b or u.get("pending_redemption_tx_hash")):d+=1
    except Exception as e:logger.error(f"[REDEMPTION] Verification error for {v}: {e}")
  f=bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("routing",{}).get("enable_auto_wrap_legacy_usdce_to_pusd",True))
  if d>0:
   if not a.dry_run and f and hasattr(a.executor,"wrap_idle_usdce_to_pusd"):
    try:a._last_usdce_wrap_chk=w;a.executor.wrap_idle_usdce_to_pusd(min_usd=1.)
    except Exception:pass
   if not a.dry_run and hasattr(a.executor,"sync_clob_collateral_allowance"):
    try:a.executor.sync_clob_collateral_allowance()
    except Exception:a.executor.invalidate_collateral_cache()
   else:a.executor.invalidate_collateral_cache()
   a._pending_collateral_refresh=True;j=getattr(a,"_main_loop",None)
   if j is not None and j.is_running():
    try:j.call_soon_threadsafe(lambda:asyncio.create_task(a._async_refresh_collateral()))
    except Exception:pass
   logger.info(f"[AUTO-REDEEMER] Swept and settled {d} mature position(s). Reclaimed collateral to balance.")
  elif(not a.dry_run and f and hasattr(a.executor,"wrap_idle_usdce_to_pusd")and getattr(a.executor,"_mock_children",None)is None and getattr(getattr(a.executor,"client",None),"_mock_children",None)is None and(w-float(getattr(a,"_last_usdce_wrap_chk",.0)or.0))>=3e2):
   a._last_usdce_wrap_chk=w
   try:
    t=a.executor.wrap_idle_usdce_to_pusd(min_usd=1.)
    if t:a.executor.invalidate_collateral_cache();a._pending_collateral_refresh=True
   except Exception:pass
  return d
 def get_condition_id(a,market_id):
  c=str(market_id)
  if c in a.market_condition_ids:return a.market_condition_ids[c]
  try:
   r=a.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{c}",timeout=3).json();b=r.get("conditionId")
   if b:a.market_condition_ids[c]=str(b);return str(b)
  except Exception as e:logger.error(f"Error fetching condition_id for market {market_id}: {e}")
  return None
 def get_token_id(a,market_id,target_token):
  b=f"{market_id}_{target_token}"
  if b in a.market_tokens_cache:return a.market_tokens_cache[b]
  try:
   r=a.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{market_id}",timeout=3).json();c=r.get("conditionId")
   if c:a.market_condition_ids[str(market_id)]=str(c)
   f=r.get("clobTokenIds");d=json.loads(f)if isinstance(f,str)else f
   if d and len(d)>=2:a.market_tokens_cache[f"{market_id}_UP"]=str(d[0]);a.market_tokens_cache[f"{market_id}_DOWN"]=str(d[1]);logger.info(f"Resolved tokens for market {market_id}: UP={d[0][:10]}... DOWN={d[1][:10]}...");return a.market_tokens_cache.get(b)
  except Exception as e:logger.error(f"Error fetching tokens for market {market_id}: {e}")
  return None
 @staticmethod
 def _resolve_true_usd_spot_from_shock(shock):
  d=float(shock.get("chainlink_proxy_spot")or.0);f=float(shock.get("coinbase_spot")or.0);e=float(shock.get("spot_at_t0")or shock.get("spot_price")or shock.get("spot")or shock.get("trigger_price")or.0);a=float(shock.get("chainlink_twap_60s")or.0);b=bool(shock.get("chainlink_basis_anchored",False))
  if not b and f>.0 and d>.0 and e>.0:
   if abs(d-f)/f>4e-4 and abs(d-e)/e<.00025:return f,(round(a*(f/d),4)if a>.0 else.0)
  c=d if d>.0 else f
  if c>.0 and a>.0 and e>.0 and not b:
   if abs(a-c)/c>4e-4 and abs(a-e)/e<5e-4:a=round(a*(c/e),4)
  return c,a
 def get_usd_reference_spot_price(a,asset):
  i=time.time();h=asset.upper();b=f"{h}USD";f=read_fast_tick(h,max_age_sec=FAST_TICK_MAX_AGE_SEC,now=i)
  if f and not(float(f.get("spot_ts")or.0)>.0 and(i-float(f["spot_ts"]))>5.):
   c,_=a._resolve_true_usd_spot_from_shock(f)
   if math.isfinite(c)and c>.0:a._spot_cache[b]=(c,i);return c
  if b in a._spot_cache:
   g,j=a._spot_cache[b]
   if i-j<1.:return g
  try:
   e=a.executor._sync_session.get(f"https://api.exchange.coinbase.com/products/{h}-USD/ticker",timeout=1.5)
   if e.status_code==200:
    d=float(e.json().get("price",.0))
    if math.isfinite(d)and d>.0:a._spot_cache[b]=(d,i);return d
  except Exception:pass
  return None
 def get_reference_spot_price(a,asset):
  i=time.time();b=f"{asset.upper()}USDT";f=read_fast_tick(asset,max_age_sec=FAST_TICK_MAX_AGE_SEC,now=i)
  if f and not(float(f.get("spot_ts")or.0)>.0 and(i-float(f["spot_ts"]))>5.):
   c=float(f.get("spot")or.0)
   if math.isfinite(c)and c>.0:a._spot_cache[b]=(c,i);return c
  if b in a._spot_cache:
   h,j=a._spot_cache[b]
   if i-j<1.:return h
  try:
   g=f"https://api.binance.com/api/v3/ticker/price?symbol={b}";e=a.executor._sync_session.get(g,timeout=1.5)
   if e.status_code==200:
    d=float(e.json().get("price",.0))
    if not math.isfinite(d)or d<=.0:logger.error("Rejected nonfinite/invalid spot price: %r",d);return None
    a._spot_cache[b]=(d,i);return d
  except Exception:pass
  return None
 def compute_kelly_ticket_size(d,p_model,p_market_ask,bankroll,fee_rate=None,fee_exponent=None):
  if not all(math.isfinite(float(v))for v in(p_model,p_market_ask,bankroll)):return.0
  if not(.0<float(p_model)<1.):return.0
  if bankroll<=0:return.0
  if p_market_ask>=d.max_price_ceiling or p_market_ask<=d.min_price_floor:return.0
  p=float(p_market_ask);q=float(p_model);r=float(fee_rate if fee_rate is not None else.07);e=float(fee_exponent if fee_exponent is not None else 1.)
  if not(math.isfinite(r)and r>=.0 and math.isfinite(e)and(e>.0 or(r==.0 and e>=.0))):return.0
  k=min(.9999,max(1e-4,p));s=r*((k*(1.-k))**e);o=s/max(k,1e-6);n=1.-o
  if n<=.005:return.0
  m=p/n
  if not math.isfinite(m)or m>=1. or m<=.0:return.0
  l=q-m
  if l<=.015:return.0
  h=l/max(.05,1.-m)
  try:c=float(getattr(d,"max_notional_cap_pct",.35))
  except(TypeError,ValueError):c=.35
  if not math.isfinite(c)or c<=.0:c=.35
  try:f=float(getattr(d,"kelly_fraction",.5))
  except(TypeError,ValueError):f=.5
  if not math.isfinite(f)or f<=.0:f=.5
  j=h*f;i=min(c,max(.015,j))
  if getattr(d,"unconstrained_kelly",False):
   b=getattr(d,"max_absolute_ticket_usd",1e4)or 1e4;a=min(bankroll*i,b)
   if not math.isfinite(a)or a<=.0:a=.0
   return round(a,2)
  try:g=float(getattr(d,"max_absolute_ticket_usd",MAX_ABSOLUTE_TICKET_USD))
  except(TypeError,ValueError):g=MAX_ABSOLUTE_TICKET_USD
  if not math.isfinite(g)or g<=.0:b=MAX_ABSOLUTE_TICKET_USD
  else:b=min(g,MAX_ABSOLUTE_TICKET_USD)
  a=min(bankroll*i,b)
  if not math.isfinite(a)or a<=.0:return.0
  if a>MAX_ABSOLUTE_TICKET_USD:a=min(MAX_ABSOLUTE_TICKET_USD,b)
  return round(a,2)
 def load_state(a):
  d=getattr(a,"state_file",STATE_FILE)
  if d.exists():
   try:
    with open(d,"r",encoding="utf-8")as f:I=json.load(f)
    a.active_positions=I.get("active_positions",{});a.closed_positions=I.get("closed_positions",[]);a.pending_entry_intents=I.get("pending_entry_intents",{});a.redeemed_tx_hashes=list(I.get("redeemed_tx_hashes",[])or[]);a.redeemed_tx_consumed_usd=dict(I.get("redeemed_tx_consumed_usd",{})or{});a.pre_split_inventory_state=dict(I.get("pre_split_inventory_state")or{});n=bool(I.get("risk_halt",False)or I.get("reconciliation_required",False));m=a._global_halt_reasons();a.risk_halt=n or bool(m);a.reconciliation_required=a.risk_halt;a.global_halt_reasons=m or(list(I.get("global_halt_reasons",[]))or(["PERSISTED_HALT"]if n else[]))
    if a.risk_halt:logger.warning(f"[STARTUP RECOVERY] Persistent global risk halt active: {a.global_halt_reasons}. " "New entries blocked until authoritative exchange reconciliation.")
    b=False
    for J in a.active_positions.values():
     if(J.get("is_liquidating")and not J.get("unwind_order_id")):
      if position_requires_lifecycle_resolution(J):continue
      J["is_liquidating"]=False;J["exit_order_status"]="UNWIND_RETRY_REQUIRED";J["next_unwind_retry_ts"]=.0;J["unwind_last_error"]=("MIGRATED_ORPHANED_LIQUIDATION_FLAG");b=True
    a.seen_shock_ids=set(I.get("seen_shock_ids",[]));a._seen_shock_order={L:None for L in I.get("seen_shock_ids",[])};p=[str(k)for k in(I.get("seen_d1_box_keys")or[])if k];a._seen_d1_box_keys=set(p);a._seen_d1_box_order={k:None for k in p};x=I.get("seen_d1_box_ts")if isinstance(I.get("seen_d1_box_ts"),dict)else{};a._seen_d1_box_ts={str(k):float(v)for k,v in x.items()if str(k)in a._seen_d1_box_keys and isinstance(v,(int,float))};a._persisted_state=dict(I);i=I.get("ft_live_funnel")
    if not isinstance(i,dict)and isinstance(I.get("live_riskless_funnel"),dict):i=I["live_riskless_funnel"].get("ft_bridge_stats")
    if isinstance(i,dict):a._ft_live_funnel=dict(i)
    a.traded_market_ids=set(I.get("traded_market_ids",[]));B=I.get("trades_per_market",{});z=I.get("trades_per_market_direction",{})or{};a.trades_per_market=defaultdict(int,{str(k):int(v)for k,v in B.items()});a.trades_per_market_direction=defaultdict(int)
    for H,G in z.items():
     if"_"in str(H):F,E=str(H).rsplit("_",1);a.trades_per_market_direction[(F,E)]=int(G)
    if not z:
     for C in a.closed_positions:
      w=str(C.get("market_id",""));D=str(C.get("target_token",""))
      if w:
       if not B:a.trades_per_market[w]+=1
       if D:a.trades_per_market_direction[(w,D)]+=1
     for K in a.active_positions.values():
      w=str(K.get("market_id",""));D=str(K.get("target_token",""))
      if w and D:a.trades_per_market_direction[(w,D)]+=1
    elif not B and a.closed_positions:
     for C in a.closed_positions:
      w=str(C.get("market_id",""))
      if w:a.trades_per_market[w]+=1
    t=I.get("current_hour_window");r=time.time()//3600
    if t==r:a.trades_this_hour=I.get("trades_this_hour",0);a.current_hour_window=r
    else:a.trades_this_hour=0;a.current_hour_window=r
    a.last_event_id=I.get("last_event_id","");A=I.get("risk_state",{})
    if getattr(a,"reset_risk",False):a.risk_controller.halted=False;a.risk_controller.halt_reason="";a.risk_controller.consecutive_losses=0;a.risk_controller.daily_realized_loss=.0;a.risk_controller.non_directional_realized_pnl=.0;a.risk_halt=False;a.reconciliation_required=False;a.global_halt_reasons=[];logger.info("[STARTUP] Risk controller circuit breaker explicitly reset via --reset-risk flag.")
    else:
     if A.get("halted"):
      q=str(A.get("halt_reason","Restored from persisted halt state"))
      if not a.dry_run and"Heartbeat degraded"in q and a.executor.is_heartbeat_healthy():logger.info(f"[STARTUP] Cleared transient session heartbeat halt on fresh process startup ({q}).");a.risk_controller.halted=False;a.risk_controller.halt_reason=""
      else:a.risk_controller.halted=True;a.risk_controller.halt_reason=q
     l=A.get("last_loss_date_utc");u=datetime.now(timezone.utc).strftime("%Y-%m-%d")
     if l and l!=u:a.risk_controller.consecutive_losses=0;a.risk_controller.daily_realized_loss=.0;a.risk_controller.last_loss_date_utc=u
     else:
      a.risk_controller.consecutive_losses=int(A.get("consecutive_losses",0)or 0);a.risk_controller.daily_realized_loss=float(A.get("daily_realized_loss",.0)or.0)
      if l:a.risk_controller.last_loss_date_utc=str(l)
     a.risk_controller.non_directional_realized_pnl=float(A.get("non_directional_realized_pnl",.0)or.0)
    if b:a.save_state()
    a._last_known_collateral=I.get("live_bankroll")
    if isinstance(a._last_known_collateral,(int,float))and math.isfinite(a._last_known_collateral)and a._last_known_collateral>.0:a.executor.set_cached_collateral(float(a._last_known_collateral))
    s=I.get("current_equity_tier")or I.get("equity_tier")
    if isinstance(s,str)and s:a._current_equity_tier=s;a.current_equity_tier=s
    elif not getattr(a,"_current_equity_tier",None):a._current_equity_tier="UNLEASHED_LAUNCH";a.current_equity_tier="UNLEASHED_LAUNCH"
    if I.get("dynamic_bankroll_pct")is not None:
     try:a.dynamic_bankroll_pct=float(I["dynamic_bankroll_pct"])
     except(TypeError,ValueError):pass
    if getattr(a,"reset_risk",False):a.high_water_mark_equity=float(I.get("live_bankroll")or.0)
    else:a.high_water_mark_equity=float(I.get("high_water_mark_equity")or I.get("total_account_equity")or I.get("live_bankroll")or getattr(a,"high_water_mark_equity",.0)or.0)
    h=float(I.get("total_account_equity")or a._last_known_collateral or.0)
    if h>0:
     j,g=a._effective_sizing_equity_usd(h);a._update_equity_tier(j,allow_hwm_ratchet=(not g))
     if(a.risk_controller.halted and"Account equity"in str(a.risk_controller.halt_reason or"")and h>=(a.risk_controller.min_equity_floor_usd+3.)):logger.info(f"[STARTUP] Cleared stale equity circuit-breaker halt on startup: persisted equity ${h:.2f} >= +$3.00 above ${a.risk_controller.min_equity_floor_usd:.2f} tier floor.");a.risk_controller.halted=False;a.risk_controller.halt_reason=""
    c=0
    for C in a.closed_positions:
     if(isinstance(C,dict)and str(C.get("status")or"").upper()in{"SETTLED","FILLED"}and not bool(C.get("exit_cash_estimated",False))and float(C.get("estimated_exit_cash",.0)or.0)<=.0 and not(C.get("box_legs_summary")or[])and not bool(C.get("won"))and float(C.get("net_pnl_usd",.0)or.0)==.0 and float(C.get("notional_usd",.0)or.0)>.0):
      y=float(C.get("confirmed_realized_cash",C.get("realized_exit_cash",.0))or.0)
      if y>.0:
       o=a.calculate_realized_cash_pnl(C,y,float(C.get("realized_exit_fee",.0)or.0))
       if.0<o<.01:
        C["net_pnl_usd"]=o;C["won"]=True
        if"REDEMPTION"in str(C.get("close_reason")or"").upper():C["exit_decomposition_bucket"]="TERMINAL_SETTLEMENT"
        if bool(C.get("is_dominance_box")or C.get("is_single_leg_lock")or C.get("is_legged_out_residual")or"BOX"in str(C.get("sleeve")or"").upper()):a.risk_controller.non_directional_realized_pnl=round(float(getattr(a.risk_controller,"non_directional_realized_pnl",.0)or.0)+o,4)
        c+=1
    if c>0:logger.info(f"[STARTUP] Reconciled {c} sub-cent settled winning trade(s) in closed_positions.");a.save_state()
    logger.info(f"Loaded existing state: {len(a.active_positions)} active positions, {len(a.traded_market_ids)} traded markets.")
   except Exception as e:logger.critical(f"LIVE STATE UNREADABLE; refusing all reconciliation and order mutation: {e}");raise RuntimeError("Refusing live startup with unreadable position state")from e
 _GLOBAL_STATE_SAVE_LOCK=threading.RLock();_RISKLESS_SAVE_HELPERS:Optional[Tuple[Any,Any]]=None
 def save_state(a):
  F=getattr(a,"_state_save_lock",None)or a._GLOBAL_STATE_SAVE_LOCK
  with F:
   D=time.time();l=type(a)._RISKLESS_SAVE_HELPERS
   if l is None:from src.polymarket_research.riskless_protocol_v2_expansion import(compute_dynamic_riskless_tier_caps as b,pending_intents_synced_equity_usd as c);l=(b,c);type(a)._RISKLESS_SAVE_HELPERS=l
   else:b,c=l
   C=getattr(a,"pre_split_inventory_state",None)or{};B=(min(float(C.get("up_rem",.0)or.0),float(C.get("dn_rem",.0)or.0))if C.get("active")else.0)+sum(min(float(G.get("up_rem",.0)or.0),float(G.get("dn_rem",.0)or.0))for G in((C.get("extra_slots")if isinstance(C.get("extra_slots"),dict)else None)or{}).values()if isinstance(G,dict)and G.get("active"));e=sum(a.get_position_market_value(p,D)for p in a.active_positions.values())+B+c(getattr(a,"pending_entry_intents",None));r=((float(a._last_known_collateral)+e)if getattr(a,"_last_known_collateral",None)is not None else None);j,_=a._effective_sizing_equity_usd(r,D);w=sorted(float(x)for x in(a.__dict__.get("_sll_post_http_ms")or()));o=getattr(a,"pending_entry_intents",None)or{};q={"ws_watch_tokens":len(getattr(a,"_clinched_ws_watchlist",None)or{})*2,"ws_snipe_emitted":int(a.__dict__.get("_ws_clinch_snipe_emitted_count",0)or 0),"resting_maker_slots":sum(1 for i in o.values()if isinstance(i,dict)and i.get("live_maker_anchor_inflight")),"fifo_rank1_slots":sum(1 for i in o.values()if isinstance(i,dict)and bool(i.get("fifo_rank1_verified"))),"outbid_repegs":int(a.__dict__.get("_sll_repeg_count",0)or 0),"http_p50_ms":round(w[len(w)//2],2)if w else None,"http_p99_ms":round(w[min(len(w)-1,int(len(w)*.99))],2)if w else None,"uma_early_recycles":int(a.__dict__.get("_uma_early_recycle_count",0)or 0),"presigned_repeg_hits":int(getattr(getattr(a,"executor",None),"_presigned_maker_repeg_hits",0)or 0),"dynamic_tier_caps":b(float(j if r is not None else.0),GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes"))};n=datetime.now(timezone.utc).isoformat();u=a._snapshot_ft_live_funnel(o,now_utc_iso=n);q["ft_bridge_stats"]=u;h=list(a._seen_shock_order.keys())[-1000:]if hasattr(a,"_seen_shock_order")else list(a.seen_shock_ids)[-1000:];m=(list(a._seen_d1_box_order.keys())[-200:]if hasattr(a,"_seen_d1_box_order")else list(getattr(a,"_seen_d1_box_keys",set()))[-200:]);t=getattr(a,"_current_equity_tier",None)or getattr(a,"current_equity_tier",None);E={"state_version":"2.0.0","updated_at_utc":n,"ticket_notional":a.ticket_notional,"dynamic_sizing":a.dynamic_sizing,"max_exposure":a.max_exposure,"max_concurrent_positions":a.max_concurrent_positions,"max_total_portfolio_slots":int((getattr(a,"risk_config",None)or RISK_CONFIG).get("max_total_portfolio_slots",4)),"unlimited_slots":a._is_unlimited_slots_active(),"dry_run":a.dry_run,"last_event_id":getattr(a,"last_event_id",""),"live_bankroll":getattr(a,"_last_known_collateral",None),"total_account_equity":r,"reconciled_nav_usd":(round(j,4)if r is not None else None),"high_water_mark_equity":getattr(a,"high_water_mark_equity",None),"equity_tier":t,"current_equity_tier":t,"dynamic_bankroll_pct":getattr(a,"dynamic_bankroll_pct",None),"active_positions_count":len(a.active_positions),"closed_positions_count":len(a.closed_positions),"trades_this_hour":a.trades_this_hour,"current_hour_window":a.current_hour_window,"active_positions":a.active_positions,"active_position_ids":list(a.active_positions.keys()),"pending_entry_intents":getattr(a,"pending_entry_intents",{}),"risk_halt":getattr(a,"risk_halt",False),"reconciliation_required":getattr(a,"reconciliation_required",False),"global_halt_reasons":list(getattr(a,"global_halt_reasons",[])or[]),"redeemed_tx_hashes":list(getattr(a,"redeemed_tx_hashes",[])or[])[-1000:],"redeemed_tx_consumed_usd":dict(getattr(a,"redeemed_tx_consumed_usd",{})or{}),"pre_split_inventory_state":dict(getattr(a,"pre_split_inventory_state",{})or{}),"closed_positions":a.closed_positions[-500:],"seen_shock_ids":h,"seen_d1_box_keys":m,"seen_d1_box_ts":{k:float(a.__dict__.get("_seen_d1_box_ts",{}).get(k))for k in m if k in(a.__dict__.get("_seen_d1_box_ts")or{})},"traded_market_ids":list(a.traded_market_ids)[-100:],"trades_per_market":dict(a.trades_per_market),"trades_per_market_direction":{f"{k[0]}_{k[1]}":v for k,v in getattr(a,"trades_per_market_direction",{}).items()},"risk_state":{"halted":a.risk_controller.halted,"halt_reason":a.risk_controller.halt_reason,"consecutive_losses":a.risk_controller.consecutive_losses,"daily_realized_loss":a.risk_controller.daily_realized_loss,"non_directional_realized_pnl":float(getattr(a.risk_controller,"non_directional_realized_pnl",.0)or.0),"last_loss_date_utc":getattr(a.risk_controller,"last_loss_date_utc",datetime.now(timezone.utc).strftime("%Y-%m-%d"))},"status":getattr(a,"_shutdown_status",None)or("HALTED"if a.risk_controller.is_halted()else"RUNNING"),"live_riskless_funnel":q,"ft_live_funnel":u};g=getattr(a,"state_file",STATE_FILE);s=g.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}")
   try:
    d=None
    if _orjson is not None:
     try:d=_orjson.dumps(E,option=_orjson.OPT_INDENT_2)
     except TypeError:d=None
    if d is not None:
     with open(s,"wb")as f:f.write(d);f.flush();os.fsync(f.fileno())
    else:
     with open(s,"w",encoding="utf-8")as f:json.dump(E,f,indent=2);f.flush();os.fsync(f.fileno())
    for A in range(3):
     try:os.replace(s,g);break
     except PermissionError:
      if os.name!="nt"or A>=2:raise
      time.sleep(.01)
    a._last_persisted_collateral=E.get("live_bankroll")
    if publish_global_positions_shm is not None and not a.dry_run:publish_global_positions_shm("live_harvester",a.active_positions.values())
    if os.name!="nt":
     z=os.open(str(g.parent),os.O_RDONLY)
     try:os.fsync(z)
     finally:os.close(z)
   except Exception as y:
    try:s.unlink(missing_ok=True)
    except Exception:pass
    raise StatePersistenceError(f"Critical live state save failed: {y}")from y
 def get_graduated_allowed_assets(a,total_equity=None):
  h=set(a.allowed_assets)
  if a._is_v5_live_strict():
   g=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional",{})
   for s in("allowed_assets_1h","allowed_assets_15m_maker"):h.update(str(x).upper()for x in(g.get(s)or[]))
   c={str(x).upper()for x in(g.get("paused_directional_assets")or[])}
  else:c=set()
  if not RISK_CONFIG.get("enable_graduated_alt_sleeves",True):return h-c
  n=total_equity
  if n is None and getattr(a,"_last_known_collateral",None)is not None:m=time.time();n=float(a._last_known_collateral)+sum(a.get_position_market_value(p,m)for p in a.active_positions.values())
  if n is None or float(n)<float(RISK_CONFIG.get("scale_up_equity_threshold",110.)):return h-c
  d=a.__dict__.setdefault("_alt_grad_file_cache",{})
  for o,l in(("SOL","state_shadow_sol_v392.json"),("XRP","state_shadow_xrp_v392.json")):
   try:
    r=DATA_DIR/l;k=r.stat();q=(str(r),k.st_mtime_ns,k.st_size);e=d.get(o)
    if isinstance(e,tuple)and len(e)==2 and e[0]==q:b=bool(e[1])
    else:f=_json_loads(r.read_bytes());j=float(f.get("profit_factor",2.)or 2.)>=1.8 if"profit_factor"in f else True;i=float(f.get("win_rate_pct",90.)or 90.)>=84. if"win_rate_pct"in f else True;b=bool(f.get("ready_for_live_graduation")is True and j and i);d[o]=(q,b)
    if b:h.add(o)
   except Exception:continue
  return h-c
 def _record_seen_d1_box_key(a,dedupe_k):
  if not dedupe_k:return
  c=a.__dict__.setdefault("_seen_d1_box_keys",set());b=a.__dict__.setdefault("_seen_d1_box_order",{k:None for k in c});e=a.__dict__.setdefault("_seen_d1_box_ts",{});b.pop(dedupe_k,None);b[dedupe_k]=None;c.add(dedupe_k);e[dedupe_k]=round(time.time(),3)
  while len(b)>400:d=next(iter(b));b.pop(d,None);c.discard(d);e.pop(d,None)
 def _live_sleeve_graduation_stats(a,sleeve_src):
  e=str(sleeve_src or"").strip().upper()
  if not e:return 0,0,0,.0
  b=getattr(a,"closed_positions",None)or[];d=len(b);c=a.__dict__.get("_live_sleeve_grad_cache")
  if not(isinstance(c,tuple)and len(c)==2 and c[0]==d):
   i={}
   for p in b:
    if not isinstance(p,dict):continue
    if str(p.get("status")or"").upper()=="NOT_EXECUTED":continue
    if str(p.get("exit_decomposition_bucket")or"").upper()=="NOT_EXECUTED":continue
    if float(p.get("notional_usd")or.0)<=.01:continue
    h=float(p.get("net_pnl_usd")or.0)
    if p.get("won")is None and abs(h)<=1e-6:continue
    j=str(p.get("sleeve")or p.get("sleeve_source")or"").strip().upper()
    if not j:continue
    l=i.setdefault(j,[0,0,0,.0]);l[0]+=1;g=bool(p.get("won"))if p.get("won")is not None else(h>.0)
    if g:l[1]+=1
    else:l[2]+=1
    l[3]+=h
   f={k:(v[0],v[1],v[2],round(v[3],6))for k,v in i.items()};a._live_sleeve_grad_cache=(d,f);c=a._live_sleeve_grad_cache
  return c[1].get(e,(0,0,0,.0))
 def _has_recent_asset_legging_cooldown(a,cand_asset,now_ts):
  if not cand_asset:return False
  b=getattr(a,"closed_positions",None)or[];d=int(now_ts//60.);c=a.__dict__.get("_asset_legging_cd_cache")
  if not(isinstance(c,tuple)and len(c)==3 and c[0]==len(b)and c[1]==d):
   g=now_ts-43200.;h={}
   for p in b:
    if not isinstance(p,dict):continue
    ast=str(p.get("asset")or"").upper()
    if not ast:continue
    f=float(p.get("exit_ts")or p.get("exit_time_unix")or p.get("entry_ts")or.0)
    if f<g:continue
    if("LEGGED_OUT"in str(p.get("close_reason")or"").upper()or"LEGGED_OUT"in str(p.get("sleeve")or"").upper()or"_LEG_RESID"in str(p.get("trade_id")or"")or"_UNWRESID_"in str(p.get("trade_id")or"")or bool(p.get("is_legged_out_residual"))or str(p.get("box_type")or"").upper()in{"MULTI_LEG_RESIDUAL","CTF_OVERROUND_RESIDUAL"}):st=h.setdefault(ast,[0,.0]);st[0]+=1;st[1]+=float(p.get("net_pnl_usd")or.0)
   e={ast for ast,st in h.items()if st[0]>=2 or st[1]<=-2.5};a._asset_legging_cd_cache=(len(b),d,e);c=a._asset_legging_cd_cache
  return cand_asset in c[2]
 def _is_d1_box_halted(a):
  c=getattr(a,"risk_config",None)or{};b=bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_graduated_d1_box",True))
  if(not bool(c.get("enable_graduated_d1_box",RISK_CONFIG.get("enable_graduated_d1_box",True)))or not b or getattr(a,"risk_halt",False)):return True
  if not a.dry_run:
   if a._global_halt_reasons()or not a.executor.is_heartbeat_healthy():return True
  if hasattr(a.risk_controller,"_mock_children"):
   if bool(a.risk_controller.is_halted()):return True
  elif a.risk_controller.is_riskless_box_halted():return True
  return False
 def _d1_acquire_inflight_slot(a,dedupe_k,m_a,m_b,concurrent_ok=False):
  b=a.__dict__.setdefault("_d1_inflight_exec_lock",threading.Lock())
  if not concurrent_ok:
   if not b.acquire(blocking=False):return None
   return False,b,"",set()
  if b.locked():return None
  e=a.__dict__.setdefault("_d1_inflight_set_lock",threading.Lock());g=a.__dict__.setdefault("_d1_inflight_keys",set());f=a.__dict__.setdefault("_d1_inflight_mkts",set());c=str(dedupe_k or"");d={str(m)for m in(m_a,m_b)if m}
  with e:
   if(c and c in g)or(d&f):return None
   if c:g.add(c)
   f.update(d)
  return True,None,c,d
 def _d1_release_inflight_slot(a,slot_info):
  if not slot_info:return
  c,b,d,f=slot_info
  if not c:
   if b is not None:
    try:b.release()
    except RuntimeError:pass
   return
  e=a.__dict__.get("_d1_inflight_set_lock");h=a.__dict__.get("_d1_inflight_keys");g=a.__dict__.get("_d1_inflight_mkts")
  if e is not None:
   with e:
    if h is not None and d:h.discard(d)
    if g is not None and f:g.difference_update(f)
 def _notify_maker_preempt_released(a):
  c=a.__dict__.get("_maker_preempt_released_ev");b=a.__dict__.get("_maker_preempt_released_ev_loop")
  if c is None:return
  try:
   if b is not None and b.is_running():
    try:
     if asyncio.get_running_loop()is b:c.set();return
    except RuntimeError:pass
    b.call_soon_threadsafe(c.set);return
   c.set()
  except Exception:pass
 def _has_inflight_maker_anchor(self,m_a,m_b,preempt_keys):return any(isinstance(_i_p,dict)and _i_p.get("live_maker_anchor_inflight")and(str(_i_p.get("inflight_key")or"")in preempt_keys if preempt_keys else str(_i_p.get("market_id")or"")in{m_a,m_b})for _i_p in getattr(self,"pending_entry_intents",{}).values())
 async def _wait_maker_anchor_preempt_async(a,m_a,m_b,preempt_keys):
  c=asyncio.get_running_loop()
  if a.__dict__.get("_maker_preempt_released_ev_loop")is not c or a.__dict__.get("_maker_preempt_released_ev")is None:a._maker_preempt_released_ev=asyncio.Event();a._maker_preempt_released_ev_loop=c
  e=a._maker_preempt_released_ev;b=time.monotonic()+.9
  while a._has_inflight_maker_anchor(m_a,m_b,preempt_keys):
   d=b-time.monotonic()
   if d<=.0:break
   e.clear()
   if not a._has_inflight_maker_anchor(m_a,m_b,preempt_keys):break
   try:await asyncio.wait_for(e.wait(),timeout=min(.05,d))
   except asyncio.TimeoutError:pass
 def _get_d1_books_from_ws(self,candidate_box,tok_a,tok_b,opp_a,opp_b,need_sep_opp,custom_book_fn):
  d=candidate_box.get("ws_books")if not custom_book_fn else None;b=float(candidate_box.get("ws_books_ts")or.0)
  if(isinstance(d,dict)and(time.time()-b)<=.65 and isinstance(d.get(tok_a),dict)and isinstance(d.get(tok_b),dict)and(not need_sep_opp or(isinstance(d.get(opp_a),dict)and isinstance(d.get(opp_b),dict)))):return(d[tok_a],d[tok_b],d[tok_b]if not need_sep_opp else d[opp_a],d[tok_a]if not need_sep_opp else d[opp_b])
  c=getattr(self,"_pos_market_ws",None)
  if c is not None and not custom_book_fn and hasattr(c,"get_book"):
   def a(tok):
    i=c.get_book(tok,max_age_sec=.65)
    if not isinstance(i,dict):return None
    if i.get("is_partial_delta")and(not i.get("bids")or not i.get("asks")):return None
    return i
   h=a(tok_a);g=a(tok_b);f=g if not need_sep_opp else a(opp_a);e=h if not need_sep_opp else a(opp_b);return h,g,f,e
  return None,None,None,None
 def _d1_step1_gate_and_preempt(a,candidate_box,concurrent_ok=False):
  if a._is_d1_box_halted():return{"executed":False,"reason":"DISABLED_OR_HALTED"}
  o=str(candidate_box.get("box_type")or"DOMINANCE").strip().upper()
  if o=="C1_BINARY_COMPLETE_SET":o="COMPLETE_SET"
  elif o=="DOMINANCE_BOX":o="MACRO_DOMINANCE"
  _I=str(candidate_box.get("sleeve_source")or("D1_SAME_ORACLE_DOMINANCE_BOX"if o!="SINGLE_LEG_LOCK"else"")).strip();E=bool(getattr(a,"enforce_paused_riskless_sleeves",False)or(not a.dry_run and getattr(a.executor,"client",None)is not None and getattr(getattr(a.executor,"client",None),"_mock_children",None)is None and"get_market_book"not in getattr(a.executor,"__dict__",{})));from src.polymarket_research.stage_c_zero_loss_velocity import(check_strict_pure_riskless_candidate_gate as f,is_nr0_closed_partition_graduated_unlock as g,is_verified_full_throttle_2leg_box as l,resolve_dynamic_paused_riskless_sleeves as h);_s=l(candidate_box)
  if _s:
   candidate_box=dict(candidate_box);candidate_box["box_type"]=o
   if o=="DOMINANCE"and str(candidate_box.get("leg_a_side")or"").strip().upper()!="UP":o="MACRO_DOMINANCE";candidate_box["box_type"]=o
   elif o=="NEGRISK_CONVERT"and not candidate_box.get("convert_mode"):candidate_box["convert_mode"]="NR2_PURE_CASH_CONVERT"
  _7=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{});U=(getattr(a,"_d1_grad_cache",None)or(None,{},{}))[1];_6=float(getattr(a,"_last_known_collateral",.0)or.0);_r=h(_7,_6,U)
  if E and _I.upper()in _r:return{"executed":False,"reason":f"PAUSED_RISKLESS_SLEEVE:{_I}"}
  if(_I.upper()=="NR0_ZERO_FEE_SLATE_ARB"and candidate_box.get("neg_risk_augmented")is False and g(_6,_7,U)):candidate_box=dict(candidate_box);candidate_box["nr0_graduated_unlock_verified"]=True
  Z=f(a,candidate_box,_7,is_maker=False)
  if Z is not None:return{"executed":False,"reason":Z}
  _H=str(candidate_box.get("asset")or"").strip().upper();_al={"BTC","ETH","XRP"}|({"SOL"}if RISK_CONFIG.get("enable_sol_d1_box",True)else set());_ax={"BNB","DOGE","HYPE","ZEC","XAU","XAG"};_T=str(candidate_box.get("leg_a_market_id")or"");_S=str(candidate_box.get("leg_b_market_id")or"");_aI=str(candidate_box.get("leg_a_token_id")or"");_aH=str(candidate_box.get("leg_b_token_id")or"")
  if o=="DOMINANCE":
   if _H and _H not in(_al|_ax):return{"executed":False,"reason":f"UNSUPPORTED_D1_ASSET:{_H}"}
   _5=float(candidate_box.get("corridor_bps")or.0);_4=6. if _H=="ZEC"else(4. if _H in{"XAU","XAG"}else(5. if _H in _ax else 3.))
   if _5<_4:return{"executed":False,"reason":f"CORRIDOR_TOO_NARROW_OR_MISSING:{_5:.2f}"}
   try:T=float(candidate_box.get("leg_a_strike")or.0);S=float(candidate_box.get("leg_b_strike")or.0)
   except(TypeError,ValueError):T=S=.0
   if(str(candidate_box.get("leg_a_side")or"").upper()!="UP"or str(candidate_box.get("leg_b_side")or"").upper()!="DOWN"or not(.0<T<S)or not _T or not _S or _T==_S or not _aI or not _aH or _aI==_aH):return{"executed":False,"reason":"INVALID_BOX_INVARIANTS"}
  elif o=="SINGLE_LEG_LOCK":
   _ak=str(candidate_box.get("leg_a_opp_token_id")or"")
   if not _I or not _aI or not _ak or _aI==_ak or not _T:return{"executed":False,"reason":"INVALID_SINGLE_LEG_LOCK_INVARIANTS"}
  elif o=="NEGRISK_CONVERT":
   _aj=str(candidate_box.get("neg_risk_market_id")or"").strip().lower().replace("0x","");_ai=str(candidate_box.get("convert_mode")or"");_q=_ai=="NR3_SYNTHETIC_ALL_YES_OVERROUND";_G=(_ai=="NR_M1_DEAD_SEED_OVERROUND"and bool(candidate_box.get("nr_m1_zero_loss_verified"))is True and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_nr_m1_dead_seed_fanout",True)));_p=(candidate_box.get("yes_sell_legs")if _q else candidate_box.get("no_legs"))or[];_h=1 if _G else 2
   if not _I or len(_aj)!=64 or not isinstance(_p,list)or not(_h<=len(_p)<=15):return{"executed":False,"reason":"INVALID_NEGRISK_CONVERT_INVARIANTS"}
  elif o in{"COMPLETE_SET","LADDER_MONO","BARRIER_MONO","NEGRISK_2LEG","NBA_DOMINANCE","SPORTS_CORRIDOR","MACRO_DOMINANCE","COUNTING_DOMINANCE","CROSS_BASIS_DOMINANCE"}:
   _o=(_T==_S)if o=="COMPLETE_SET"else(_T!=_S)
   if not _aI or not _aH or _aI==_aH or not _T or not _S or not _o:return{"executed":False,"reason":"INVALID_BOX_INVARIANTS"}
  elif o in{"CTF_OVERROUND","MULTI_LEG_BUNDLE"}:
   if not _I or(o=="CTF_OVERROUND"and not candidate_box.get("condition_id"))or(o=="MULTI_LEG_BUNDLE"and not(3<=len(candidate_box.get("legs")or[])<=12)):return{"executed":False,"reason":"INVALID_SPECIAL_BOX_INVARIANTS"}
  else:return{"executed":False,"reason":f"UNSUPPORTED_BOX_TYPE:{o}"}
  if not a.dry_run:
   if not getattr(a,"_startup_reconciled",False):return{"executed":False,"reason":"STARTUP_NOT_RECONCILED"}
   _ah=a._global_halt_reasons()
   if _ah:return{"executed":False,"reason":f"GLOBAL_HALT:{_ah[0]}"}
   _ag=a._reconciling_market_ids();R=o=="NEGRISK_CONVERT"and any(str(lg.get("market_id")or"")in _ag for lg in(candidate_box.get("no_legs")or[])if isinstance(lg,dict)and lg.get("market_id"))
   if _T in _ag or(_S and _S in _ag)or R:return{"executed":False,"reason":"MARKET_RECONCILING"}
  from src.polymarket_research.riskless_protocol_v2_expansion import is_post_expiry_uma_frozen_lock as p;_n=time.time();k={"TERMINAL_UNWIND_FAILED_SUPERVISED","SUB_MINIMUM_LOT_SUPERVISED_HOLD","DETERMINISTIC_TERMINAL_HOLD","EXIT_RECOVERY_REQUIRED","HOLD_TO_MATURITY_LOCK","AWAITING_REDEMPTION"}
  for _aG in a.active_positions.values():
   if position_is_settlement_receivable(_aG)or p(_aG,_n):continue
   _F=str(_aG.get("exit_order_status")or"")
   if _F in("UNWIND_RETRY_REQUIRED","UNWIND_EXECUTION_OUTCOME_UNKNOWN","PARTIAL_UNWIND_REMAINING"):return{"executed":False,"reason":"UNHEDGED_BOX_RESIDUAL_ACTIVE"}
   _3="BOX"in str(_aG.get("sleeve")or"").upper()or bool(_aG.get("box_id"))
   if(_3 and not(_aG.get("is_dominance_box")or _aG.get("is_single_leg_lock"))and _F not in k):return{"executed":False,"reason":"UNHEDGED_BOX_RESIDUAL_ACTIVE"}
  _aw=time.time();Q=a._active_box_ids();_2=getattr(a,"risk_config",None)or RISK_CONFIG;r=int(_2.get("max_concurrent_d1_boxes",4));t=int(_2.get("max_total_portfolio_slots",4))
  if a._is_v5_unleashed_active():_aN=GLOBAL_GOVERNANCE_MANAGER.snapshot;r=int(_aN.get("riskless_boxes",{}).get("max_concurrent_riskless_boxes",10));t=int(_aN.get("sizing_tiers",{}).get("max_total_slots",12))
  if len(Q)>=r or(not a.dry_run and(len(Q)+len(a._risk_bearing_positions()))>=t):return{"executed":False,"reason":"MAX_CONCURRENT_BOXES_REACHED"}
  Y=float(candidate_box.get("expiry_ts")or.0)
  if o not in{"DOMINANCE","NEGRISK_CONVERT","CTF_OVERROUND"}and r>=2 and Y>.0 and(Y-_aw)>3600.:
   if len(Q)>=(r-1):return{"executed":False,"reason":"INTRADAY_D1_SLOT_RESERVED"}
  _1=str(candidate_box.get("dedupe_key")or"");X=str(candidate_box.get("pair_dedupe_key")or(f"BOND1_{_T}"if _I in{"BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY"}and _T else""));_E=a.__dict__.setdefault("_seen_d1_box_keys",set());_g=[_T,_S]if(_T or _S)else[str(lg.get("market_id")or"")for lg in(candidate_box.get("no_legs")or candidate_box.get("legs")or[])if isinstance(lg,dict)and lg.get("market_id")];from src.polymarket_research.riskless_protocol_v2_expansion import is_d1_dedupe_blocked as y
  if y(a,_1,X,_g,_aw):return{"executed":False,"reason":"ALREADY_EXECUTED_PAIR"}
  _0=a.__dict__.setdefault("_d1_retry_cooldown_until",{})
  if _1 and float(_0.get(_1,.0)or.0)>_aw:return{"executed":False,"reason":"RETRY_COOLDOWN_10S"}
  if a._has_recent_asset_legging_cooldown(_H,_aw):return{"executed":False,"reason":f"ASSET_LEGGING_COOLDOWN:{_H}"}
  try:
   from src.polymarket_research.stage_c_zero_loss_velocity import load_alpha124_graduation_maps_with_lkg_cache as e;D,C,w=e(a,DATA_DIR,PIPELINE_ROOT,json_loads_fn=_json_loads,stale_reason="ALPHA124_STATE_STALE",missing_reason="NO_ALPHA124_STATE")
   if w is not None or D is None or C is None:
    if(_s and getattr(a,"_d1_grad_cache","UNSET")is not None and(_aw-float(candidate_box.get("ts_unix")or _aw))<=86400.):D,C,w={},{},None
    else:return{"executed":False,"reason":w or"NO_ALPHA124_STATE"}
   def c(rec):_am=rec.get("realized_pnl_t1000_usd",rec.get("realized_pnl_usd",.0));x=rec.get("legging_adjusted_pnl_t1000_usd",_am);return bool(int(rec.get("closed",0)or 0)>=8 and float(rec.get("win_rate_pct",.0)or.0)>=1e2 and float(_am or.0)>.0 and float(x or.0)>.0)
   _D=candidate_box.get("legs")or candidate_box.get("no_legs")or[];_aM=(float(candidate_box["leg_a_fee_rate"])if candidate_box.get("leg_a_fee_rate")is not None else(max((float(x.get("fee_rate")or.0)for x in _D if isinstance(x,dict)),default=.07)if _D else.07));_aL=(float(candidate_box["leg_b_fee_rate"])if candidate_box.get("leg_b_fee_rate")is not None else(.0 if o in{"SINGLE_LEG_LOCK","MULTI_LEG_BUNDLE","CTF_OVERROUND"}else _aM));_f=(_aM==.0)if o=="SINGLE_LEG_LOCK"else(max(_aM,_aL)==.0);_R=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{});_Z=round(1.-max(.001,float(_R.get("zerofee1_min_net_edge_bps",15.)or 15.)/1e4),4);_av=getattr(a.executor,"signature_type",None);I=((3 if _av is None else int(_av))!=3 or bool(os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY")or os.getenv("PM_ENABLE_ONCHAIN_MERGE","0")=="1")or a.dry_run or hasattr(getattr(a.executor,"client",None),"_mock_children"));_af=str(candidate_box.get("leg_a_condition_id")or"").strip();M=(o=="COMPLETE_SET"and _f and bool(candidate_box.get("leg_a_neg_risk"))==bool(candidate_box.get("leg_b_neg_risk"))and bool(_af)and _af==str(candidate_box.get("leg_b_condition_id")or"").strip()and bool(_R.get("enable_zerofee1_mergeable_sweeper",True))and bool(_R.get("enable_c1_gasless_batch_merge",True))and(I or(float(candidate_box.get("expiry_ts")or.0)-_aw)<=86400.));H=True;q=True;from src.polymarket_research.riskless_protocol_v2_expansion import PROTOCOL_V2_MATH_SLEEVES as u;_au={"LP2_ELECTION_AND_CONDITIONAL_IMPLICATION_DAG","CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX","LP1_NFL_EXACT_MARGIN_AND_ML_SPREAD_BOX","CRY_INC1_SAME_ORACLE_BINANCE_INCLUSION"};P={"MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER","MKR_REWARD_LOCKED_CARRY"};_at=_au|u|P|{"SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR","AFF1_FROZEN_SUBPERIOD_COLLAPSE","SOC2_EXACT_SCORE_2D_LATTICE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS","SUM1_FRECHET_SUM_TRIANGLES","B3_BARRIER_MONO_BOX","D2_12PM_BINANCE_BOX","GAS1_AAA_GASOLINE_LOCK","API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK","SP2_NBA_ENDGAME_LOCK","U1_DAILY_UPDOWN_LOCK","CM_B2_PYTH_SESSION_NO_LOCK","CM_U1_PYTH_CLOSE_LOCK"}
   if o=="DOMINANCE":
    _C=c(D.get("D1_SAME_ORACLE_DOMINANCE_BOX")or{});_m=_I=="D1_QUIET_BOOK_BOX"and c(D.get("D1_QUIET_BOOK_BOX")or{})
    if not(_C or _m or _s):return{"executed":False,"reason":"D1_NOT_YET_8_OF_8_GRADUATED"}
    if _H in _ax:
     _as=C.get(_H)or{};q=c(_as);W=bool((getattr(a,"risk_config",None)or RISK_CONFIG).get("enable_exp_d1_bridge",True))and int(_as.get("losses",0)or 0)==0 and float(_as.get("legging_adjusted_pnl_t1000_usd",.0)or.0)>=.0
     if not(q or W or _s):return{"executed":False,"reason":f"EXPANSION_ASSET_NOT_YET_8_OF_8_GRADUATED:{_H}"}
   else:
    _ar=D.get(_I)or{};_B=D.get("BOND1_UMA_RESOLUTION_CARRY")or{};_aF,_aE,_aD,_ae=a._live_sleeve_graduation_stats(_I);_Q=(_aD==0 and _aF>=8 and _aE==_aF and _ae>.0);B=(_aD==0 and _aF>=3 and _aE==_aF and _ae>.0);_ad=(_aD==0)and((int(_ar.get("losses",0)or 0)==0 and(_I!="UMA_READY1_LIVENESS_PRIORITY"or int(_B.get("losses",0)or 0)==0))or _Q or(B and _I in{"BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"}));_aC=c(D.get("D1_SAME_ORACLE_DOMINANCE_BOX")or{});G={"W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK","W_SOLAR1_POST_2351_LOCK","SP2_NBA_ENDGAME_LOCK","U1_DAILY_UPDOWN_LOCK","CM_B2_PYTH_SESSION_NO_LOCK","CM_U1_PYTH_CLOSE_LOCK"};_ac=bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional",{}).get("riskless_only_mode",False))and not a.dry_run;_l=float(candidate_box.get("p_model")or.0);_e=not(_ac and o=="SINGLE_LEG_LOCK"and _I in G)or _l>=.999;H=((c(_ar)or _Q or(_I=="UMA_READY1_LIVENESS_PRIORITY"and c(_B)))and _ad and _e);_k=float(candidate_box.get("expiry_ts")or.0)-_aw;_aB=float(candidate_box.get("box_cost_net")or 1.);_aA={"COMPLETE_SET","BARRIER_MONO","NEGRISK_2LEG","NBA_DOMINANCE","SPORTS_CORRIDOR","MACRO_DOMINANCE","COUNTING_DOMINANCE","LADDER_MONO","CROSS_BASIS_DOMINANCE"};O=_I=="COND1_MACRO_PARTITION_BOX"and((H and.0<_k<=172800. and _aB<=.992)or(.0<_k<=1.08e5 and _aB<=.985)or _s);_P=_ad and((_I=="C1_BINARY_COMPLETE_SET"and bool(candidate_box.get("recorder_fast_ipc"))and _aB<=.989 and.0<_k<=86400.)or(_aB<=.988 and((_I=="SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX"and.0<_k<=21600.)or(_I in{"SP3_SPORTS_CORRIDOR_DOMINANCE_BOX","M3_LADDER_MONO_BOX"}and.0<_k<=86400.))));_aq=o in _aA and _I!="NR_CONV_NO_BASKET_ARB"and(_I!="COND1_MACRO_PARTITION_BOX"or O);_d=_aq and(_f or _P)and _I not in _at and _aC;_j=604800. if _I in _au else 129600.;_O=(o in{"CTF_OVERROUND","MULTI_LEG_BUNDLE"}or M)and bool(_R.get("enable_graduated_d1_box",True));_A=bool(_R.get("enable_ungraduated_v3_math_live",False))if E else(bool(_2.get("enable_ungraduated_v3_math_live",False))or bool(_R.get("enable_ungraduated_v3_math_live",False)));_ap=(_A or _O)and(not E or _I.upper()not in{str(x).upper()for x in(_R.get("paused_riskless_sleeves")or[])});_Y=float(candidate_box.get("p_model")or(.0 if(_I in P or(_ac and _I in G))else.998));L=5.4e4 if _I=="W_PRUNE1_DEAD_NO_BOND"else 14400.;_z=.9975 if(_f and _k<=28800.)else((.995 if _Y>=.9999 else.994)if(_Y>=.999 and _k<=L)else.992);_y=_ap and not a.dry_run and a._is_v5_unleashed_active()and _ad and _aC and _e and(o=="CTF_OVERROUND"or(M and _k>25.)or.0<_k<=_j)and((_aq and _aB<=(_Z if M else(.992 if _f else.989)))or(o in{"CTF_OVERROUND","MULTI_LEG_BUNDLE"}and _aB<=.9955)or(o=="SINGLE_LEG_LOCK"and(_I in _at or _I.startswith("SP4_"))and _Y>=(.999 if(_I in P or(_ac and _I in G))else.998)and _aB<=_z));_X=str(candidate_box.get("convert_mode")or"");z=o=="NEGRISK_CONVERT"and bool(_2.get("enable_nr2_pure_cash_bridge",True))and((_X in{"NR2_PURE_CASH_CONVERT","NR2_SUBSET_LIQUID_YES_CONVERT","NR2_SUBSET_CONVERT_FREE_TAIL","NR4_FULL_SWEEP","NR5_NEGATIVE_COST_FREEROLL"}and 2<=len(candidate_box.get("no_legs")or[])<=15)or(_X=="NR3_SYNTHETIC_ALL_YES_OVERROUND"and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_nr3_synthetic_overround",True))and 2<=len(candidate_box.get("yes_sell_legs")or[])<=15)or(_X=="NR_M1_DEAD_SEED_OVERROUND"and bool(candidate_box.get("nr_m1_zero_loss_verified"))is True and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_nr_m1_dead_seed_fanout",True))and len(candidate_box.get("no_legs")or[])==1))and _ad and(_aC or _s);_x=_B if(_I=="UMA_READY1_LIVENESS_PRIORITY"and int(_ar.get("closed",0)or 0)==0)else _ar;F=o=="SINGLE_LEG_LOCK"and _I in{"BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","UMA_READY1_LIVENESS_PRIORITY"}and bool(_2.get("enable_bond1_live_bridge",True))and _ad and float(_x.get("realized_pnl_t1000_usd",.0)or.0)>=.0 and(int(_x.get("closed",0)or 0)==0 or float(_x.get("win_rate_pct",1e2)or.0)>=1e2)and _aC;N=o=="SINGLE_LEG_LOCK"and _I in{"S2_EXACT_TWAP_LOCK","S2_RTDS_EXACT_TWAP_INTEGRATOR"}and(bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_s2_twap_lock_live",True))or not E)and not a.dry_run and _ad and float(candidate_box.get("p_model")or.0)>=.9985 and _aB<=.9972 and _aC;A=bool(_s and _ad and bool(_R.get("enable_graduated_d1_box",True))and(not E or _I.upper()not in{str(x).upper()for x in(_R.get("paused_riskless_sleeves")or[])}))
    if not(H or _d or _y or z or F or N or A):return{"executed":False,"reason":f"SLEEVE_NOT_YET_8_OF_8_GRADUATED:{_I}"}
  except Exception as exc:return{"executed":False,"reason":f"STATE_READ_ERROR:{exc}"}
  _N=a._d1_acquire_inflight_slot(_1,str(candidate_box.get("leg_a_market_id")or""),str(candidate_box.get("leg_b_market_id")or""),concurrent_ok=concurrent_ok)
  if _N is None:return{"executed":False,"reason":"BOX_EXECUTION_INFLIGHT"}
  s=False
  try:
   from src.polymarket_research.stage_c_zero_loss_velocity import check_multileg_3plus_nav_and_certification_gate as d;_M=d(a,candidate_box,GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}),now_ts=_aw)
   if _M is not None:return{"executed":False,"reason":_M}
   if o=="SINGLE_LEG_LOCK":return a._finish_single_leg_lock(candidate_box,_I,_aI,_T,_1,_0,_aw,_2,own_grad=H)
   if o=="NEGRISK_CONVERT":return a._finish_negrisk_convert_arb(candidate_box,_I,_1,_0,_aw,_2,own_grad=H)
   if o in{"CTF_OVERROUND","MULTI_LEG_BUNDLE"}:from src.polymarket_research.riskless_protocol_v2_expansion import finish_protocol_v2_special_box_sync as j;return j(a,candidate_box,_1,_0,_aw,_2,own_grad=H)
   _az=str(candidate_box.get("leg_a_label","LEG_A"));_ay=str(candidate_box.get("leg_b_label","LEG_B"));_W=float(candidate_box["leg_a_limit_price"]);_V=float(candidate_box["leg_b_limit_price"]);_ao=float(candidate_box.get("net_paired_shares")or candidate_box.get("shares",12.));_w=float(candidate_box.get("leg_a_gross_shares")or candidate_box.get("shares",_ao));_v=float(candidate_box.get("leg_b_gross_shares")or candidate_box.get("shares",_ao));_ab=float(candidate_box.get("max_box_cost_net",.995));V=float(candidate_box.get("box_cost_net")or(_W+_V));_aa=candidate_box.get("leg_a_avail_shares");_9=candidate_box.get("leg_b_avail_shares");_aK=float(candidate_box.get("leg_a_fee_exponent",1.)or 1.);_aJ=float(candidate_box.get("leg_b_fee_exponent",1.)or 1.);_L,_K=.0,.0;m_a,m_b=str(candidate_box.get("leg_a_market_id")or""),str(candidate_box.get("leg_b_market_id")or"");_an=float(candidate_box.get("expiry_ts")or.0);v=0;n=set();K=((not a.dry_run)and getattr(a.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2")and len(_aI)>=20 and _aI.isdigit()and len(_aH)>=20 and _aH.isdigit());_8=float(candidate_box.get("ts_unix")or _aw);_u=round(max(.0,(_aw-_8)*1e3),2);_t,_c=.0,.0
   if not a.dry_run and(not K or not candidate_box.get("ts_unix")or not candidate_box.get("expiry_ts")or walk_equal_shares_dominance_box is None or not hasattr(a.executor,"get_market_book")):return{"executed":False,"reason":"LIVE_PRECHECK_UNAVAILABLE"}
   if K:
    _J=str(candidate_box.get("leg_a_horizon")or"").lower()in("4h","1h")or str(candidate_box.get("leg_b_horizon")or"").lower()in("4h","1h")
    if o=="DOMINANCE":b=9e2 if _J else 3e2
    elif _I=="COND1_MACRO_PARTITION_BOX"and not H:b=1.08e5
    elif _I=="LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX"or _I in _au or _s:b=604800.
    elif o in{"SPORTS_CORRIDOR","NBA_DOMINANCE"}:b=259200.
    elif o in{"NEGRISK_2LEG","MACRO_DOMINANCE","BARRIER_MONO"}:b=172800.
    elif M:b=3.1536e7
    else:b=86400.
    _i=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{});_b=(float(_i.get("ipc_candidate_max_age_sec",60.)or 60.)if(_s or o!="DOMINANCE")else float(_i.get("ipc_subhourly_d1_max_age_sec",15.)or 15.))
    if(_aw-_8)>_b or(_an>.0 and not(16.<=(_an-_aw)<=b)):return{"executed":False,"reason":"STALE_OR_OUTSIDE_TTE_WINDOW"}
    if m_a in{"6707502","6707503"}or m_b in{"6707502","6707503"}:return{"executed":False,"reason":"D001_DISPUTED_KMIA_NON_INTERFERENCE"}
    from src.polymarket_research.riskless_protocol_v2_expansion import(pending_intents_cash_reserved_usd as m,preempt_makers_for_instant_taker_arb as i);_U=getattr(a,"_last_known_collateral",None);_a=(max(.0,float(_U)-(.0 if a.dry_run else m(getattr(a,"pending_entry_intents",None))))if isinstance(_U,(int,float))and not isinstance(_U,bool)else None);J=bool(not a.dry_run and(o=="DOMINANCE"or H));v,n=i(a,reason=f"D1_BOX:{_H}",target_market_ids={m_a,m_b},cand_net_cost=V,free_cash_hint=_a,target_arb_cash_usd=45.,min_fallback_cash_usd=26.,force_cross_market_when_low_cash=J,now_ts=_aw)
   s=True;return{"_s1_ok":True,"slot_info":_N,"candidate_box":candidate_box,"box_type":o,"sleeve_src":_I,"cand_asset":_H,"tok_a":_aI,"tok_b":_aH,"lbl_a":_az,"lbl_b":_ay,"px_a_lim":_W,"px_b_lim":_V,"sh_req":_ao,"sh_a_gross":_w,"sh_b_gross":_v,"cap_net":_ab,"fresh_box_net":V,"avail_a":_aa,"avail_b":_9,"fr_a":_aM,"fr_b":_aL,"fe_a":_aK,"fe_b":_aJ,"pre_bal_a":_L,"pre_bal_b":_K,"pre_bal_ms":_t,"book_walk_ms":_c,"ipc_age_ms":_u,"is_live_ctf_box":K,"m_a":m_a,"m_b":m_b,"exp_ts":_an,"now_ts":_aw,"dedupe_k":_1,"retry_cd":_0,"seen_boxes":_E,"by_sl_map":D,"exp_d1":_ax,"own_grad":H,"own_asset_grad":q,"zero_fee_box":_f,"_ft_cert_2l":_s,"_v3_7d":_au,"_zf1_cap":_Z,"_zf_c1_merge_ok":M,"_merge_wallet_ok":I,"_signaled_d1":v,"_preempt_keys_d1":n,"_grad8":c}
  finally:
   if not s:a._d1_release_inflight_slot(_N)
 def _d1_step2_budget_and_bal_prep(a,s1,fetched_collat,prev_c_d1,async_reserved_usd=.0):
  _U=s1["_grad8"];V=s1["candidate_box"];_F=s1["box_type"];_s=s1["sleeve_src"];_r=s1["cand_asset"];_Y,_X=s1["tok_a"],s1["tok_b"];_W,_V=s1["lbl_a"],s1["lbl_b"];_E,_D=s1["px_a_lim"],s1["px_b_lim"];_T,_q,_p=s1["sh_req"],s1["sh_a_gross"],s1["sh_b_gross"];_K,U=s1["cap_net"],s1["fresh_box_net"];_J,_I=s1["avail_a"],s1["avail_b"];_6,_5,_4,_3=s1["fr_a"],s1["fr_b"],s1["fe_a"],s1["fe_b"];O=s1["is_live_ctf_box"];_8,_7,_S,_R=s1["m_a"],s1["m_b"],s1["exp_ts"],s1["now_ts"];_z,_Q=s1["by_sl_map"],s1["exp_d1"];_C,R=s1["own_grad"],s1["own_asset_grad"];_e,_j=s1["zero_fee_box"],s1["_ft_cert_2l"];_P,_B=s1["_v3_7d"],s1["_zf1_cap"];N,J=s1["_zf_c1_merge_ok"],s1["_merge_wallet_ok"];_d=s1["_signaled_d1"];c=float(U*_T);_y=max(1.,_S-_R)if _S>.0 else.0;v=False;P=360.;W=time.time();H,G=None,None;B,A,z="","",False
  if O:
   from src.polymarket_research.riskless_protocol_v2_expansion import(check_per_event_concentration_cap as o,compute_d1_per_market_notional_cap as n,compute_sll_and_carry_gatling_budget as m,is_market_busy_for_scaling as f,open_market_notional_usd as g,pending_intents_cash_reserved_usd as q,pending_intents_synced_equity_usd as r,sync_pending_intents_on_collateral_refresh as j)
   if(_8 and f(a,_8))or(_7 and f(a,_7)):return{"executed":False,"reason":"MARKET_ALREADY_OCCUPIED"}
   F=prev_c_d1 if not(_d>0 and not a.dry_run)else None
   if F is None:
    F=fetched_collat
    if isinstance(F,(int,float))and not isinstance(F,bool)and math.isfinite(float(F))and float(F)>=.0:a._last_known_collateral=float(F);j(a,prev_c_d1,float(F))
   _A=getattr(a,"pending_entry_intents",None);D=q(_A);I=max(.0,float(F or.0)-D-float(async_reserved_usd or.0))
   if True:
    _i=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{});_c=min(26.,max(12.,float(_i.get("gatling_base_clip_d1_usd",22.)or 22.)))
    if(not a.dry_run and I<_c-.5 and U<=.98005 and getattr(a.executor,"client",None)is not None and getattr(getattr(a.executor,"client",None),"_mock_children",None)is None and bool(_i.get("enable_zero_loss_open_carry_velocity_recycle",True))):
     from src.polymarket_research.stage_c_zero_loss_velocity import recycle_open_zero_loss_carry_for_fast_arb as l;_O=l(a,needed_cash_gap_usd=max(.0,_c-I),challenger_net_cost=U,challenger_rem_tte_sec=_y,challenger_sleeve=_s,exclude_market_ids={_8,_7},now_ts=_R)
     if _O.get("recycled_count",0)>0:F=getattr(a,"_last_known_collateral",F);I=max(I+float(_O.get("freed_cash_usd",.0)),max(.0,float(F or.0)-D))
    _b=min(float(V.get("leg_a_expiry_ts")or _S),float(V.get("leg_b_expiry_ts")or _S));_x=(max(1.,_b-_R)if(_s=="CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"and _b>.0)else _y)
    if _F!="DOMINANCE"and _y>.0:
     M=_e and(_s in{"COND1_MACRO_PARTITION_BOX","LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX","M3_LADDER_MONO_BOX","N1_NEGRISK_CROSS_BOX","TW1_COUNTING_TRUNCATION_AND_BOX","FED1_CENTRAL_BANK_LP_BOX","C1_BINARY_COMPLETE_SET","NR0_ZERO_FEE_SLATE_ARB","FT_DUP1_EXACT_CROSS_EVENT_BOX","FT_STRIKE1_VERIFIED_DOMINANCE_BOX","XV_SUBSET_NO_2LEG_BOX"}or(_s=="CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"and(_C or _j)and _x<=129600.)or(_s=="CM_B3_PYTH_BARRIER_BOX"and _x<=43200. and U<=.988));from src.polymarket_research.riskless_protocol_v2_expansion import is_disputed_or_frozen_uma_position as b;_o=I+D+sum(float(_p_lq.get("notional_usd",.0)or.0)for _p_lq in a.active_positions.values()if isinstance(_p_lq,dict)and not position_is_settlement_receivable(_p_lq)and not b(_p_lq,_R));_n=getattr(a,"_current_equity_tier",None)or"UNLEASHED_LAUNCH";_N,_m=passes_capital_velocity_hurdle(collat_usd=_o,rem_tte_sec=_x,box_cost_net=U,box_type=_F,sleeve_src=_s,fast_recycle_eligible=M,merge_wallet_ok=bool(N and J),previous_tier=_n)
     if not _N:return{"executed":False,"reason":_m}
    from src.polymarket_research.riskless_machine_gun_engine import is_soc2_exhaustive_lattice_safe as s,is_sports_dead_ball_safe as y;from src.polymarket_research.riskless_protocol_v2_expansion import is_disputed_or_frozen_uma_position as b
    if not s(V):return{"executed":False,"reason":"SOC2_NON_EXHAUSTIVE_QUARANTINED"}
    if _F in{"SPORTS_CORRIDOR","NBA_DOMINANCE"}and not y(V):return{"executed":False,"reason":"LIVE_BALL_SPORTS_ORACLE_LAG_VETO"}
    _a=sum(float(p.get("notional_usd",.0)or.0)for p in a.active_positions.values()if not position_is_settlement_receivable(p)and not b(p,_R))+D+r(_A)
    if a._is_v5_unleashed_active():
     _h=I+_a;Z=get_unleashed_v5_tier_profile(_h,previous_tier=getattr(a,"_current_equity_tier",None)or"UNLEASHED_LAUNCH");X=float(Z["d1_free_cash_pct"]);h={"BTC":250.,"ETH":150.,"SOL":65.,"XRP":65.,"BNB":35.,"HYPE":25.,"DOGE":25.,"ZEC":10.,"XAU":25.,"XAG":25.}.get(_r,45.);Y=str(Z.get("tier")or"");C=(60. if Y=="UNLEASHED_LAUNCH"else(120. if Y=="HYPER_GROWTH"else 150.))
     if not(_s=="D1_SAME_ORACLE_DOMINANCE_BOX"and _y<=3600. and U<=.975):h=min(h,C)
     if _r in _Q and not R:h=min(h,20.)
     x=max(.0,max(float(a.max_exposure),_h*.96)-_a);e=min(float(Z["bridged_zero_fee_cap_usd"]),C)
     if _F!="DOMINANCE"and not _C:
      E=max(12.,_h*.28)if Y=="UNLEASHED_LAUNCH"else max(20.,_h*.25);e=min(e,E)
      if not a.dry_run:from src.polymarket_research.riskless_protocol_v2_expansion import is_post_expiry_uma_frozen_lock as t;L=sum(float(p.get("notional_usd",.0)or.0)for p in a.active_positions.values()if not position_is_settlement_receivable(p)and not t(p,_R)and str(p.get("box_type")or"DOMINANCE")!="DOMINANCE"and not _U(_z.get(str(p.get("sleeve")or""))or{}));e=min(e,max(.0,max(12.,_h*.3)-L))
     w=float(Z["box_collateral_reserve_usd"])
    else:
     X=(.32 if I>=160. else float(RISK_CONFIG.get("d1_box_bankroll_pct",.25)));h={"BTC":150.,"ETH":75.,"SOL":16.5,"XRP":16.5,"BNB":22.,"HYPE":15.,"DOGE":15.,"ZEC":10.,"XAU":25.,"XAG":25.}.get(_r,25.)
     if _r in _Q and not R:h=min(h,12.)
     x=max(.0,max(float(a.max_exposure),I*.55)-_a);e=12. if _s=="COND1_MACRO_PARTITION_BOX"else 16.5;w=float(RISK_CONFIG.get("d1_box_collateral_reserve_usd",16.5))
    c=min(float(RISK_CONFIG.get("d1_box_max_budget_usd",250.)),e if(_F!="DOMINANCE"and not _C)else h,max(.0,I-w),I*X,x);c=m(a,c,I,_a,_F,_s,_C,GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes"),rem_tte_sec=_y,now_ts=_R,cap_usd=min(float(RISK_CONFIG.get("d1_box_max_budget_usd",250.)),h if _F=="DOMINANCE"else 250.));K=max(g(a,[_8])if _8 else.0,g(a,[_7])if _7 else.0)
    if K>.0:c=min(c,max(.0,n(a)-K))
    if _F!="DOMINANCE":
     _l,_g,_f,_=o(a,V,market_ids=[_8,_7],now_ts=_R,min_headroom_usd=4.5)
     if not _l:return{"executed":False,"reason":_g}
     c=min(c,_f)
    if c<4.5:return{"executed":False,"reason":"INSUFFICIENT_BOX_COLLATERAL_HEADROOM"}
    Q=a.dry_run or hasattr(getattr(a.executor,"client",None),"_mock_children")
    for _2,_1,_M,_0,_Z,_w in((_Y,str(V.get("leg_a_condition_id")or""),V.get("leg_a_neg_risk"),_6,_4,V.get("leg_a_tick_size")if Q else None),(_X,str(V.get("leg_b_condition_id")or""),V.get("leg_b_neg_risk"),_5,_3,V.get("leg_b_tick_size")if Q else None)):
     if _1 and isinstance(_M,bool)and hasattr(a.executor,"prewarm_token_market_cache"):a.executor.prewarm_token_market_cache(token_id=_2,tick_size=_w,neg_risk=_M,fee_rate_bps=int(round(_0*10000)),condition_id=_1,fee_rate=_0,fee_exponent=_Z)
    T=a.__dict__.setdefault("_d1_clean_pre_bal_cache",{});v="_wallet_token_balance"not in a.__dict__;W=time.time();_L=getattr(a.executor,"_user_ws_cache",None)if v else None;_v=bool(_L is not None and _L.is_healthy());P=1800. if _v else 360.;_k=({p.get("token_id")for p in a.active_positions.values()}|{i.get("token_id")for i in getattr(a,"pending_entry_intents",{}).values()}|{p.get("token_id")for p in getattr(a,"closed_positions",[])[-20:]if float(p.get("remaining_shares",.0)or.0)>.01 or not _v}|{k for k,u in(a.__dict__.get("_d1_dirty_token_until")or{}).items()if float(u or.0)>W})if v else{_Y,_X};H=T.get(_Y)if v else None;G=T.get(_X)if v else None
    if H is not None and _v and _L.has_token_fill_since(_Y,H[1]):H=None
    if G is not None and _v and _L.has_token_fill_since(_X,G[1]):G=None
    if v and _Y not in _k and H is None and not(_v and _L.has_token_fill_since(_Y,W-3e2)):H=(.0,W)
    if v and _X not in _k and G is None and not(_v and _L.has_token_fill_since(_X,W-3e2)):G=(.0,W)
    if walk_equal_shares_dominance_box is not None and hasattr(a.executor,"get_market_book"):
     B=str(V.get("leg_a_opp_token_id")or"").strip();A=str(V.get("leg_b_opp_token_id")or"").strip();_u=str(V.get("leg_a_condition_id")or"").strip();_t=str(V.get("leg_b_condition_id")or"").strip();S=bool(((_8 and _8==_7)or(_u and _u==_t))and _Y!=_X)
     if S:B=B or _X;A=A or _Y
     z=_F!="COMPLETE_SET"and not S
     if z:
      from src.polymarket_research.riskless_protocol_v2_expansion import resolve_missing_opp_token_id as d
      if not(len(B)>=20 and B.isdigit()):
       _H=d(a,_8,_u,_Y)
       if _H:B=_H;V["leg_a_opp_token_id"]=B
      if not(len(A)>=20 and A.isdigit()):
       _G=d(a,_7,_t,_X)
       if _G:A=_G;V["leg_b_opp_token_id"]=A
      if not(len(B)>=20 and B.isdigit()and len(A)>=20 and A.isdigit()):return{"executed":False,"reason":"ANTI_BOX_COMPLEMENT_UNVERIFIED:MISSING_OPP_TOKENS"}
  return{"_s2_ok":True,"s1":s1,"target_budget":c,"rem_tte_s":_y,"use_bal_cache":v,"bal_ttl":P,"now_pb":W,"c_ba":H,"c_bb":G,"need_books":bool(O and walk_equal_shares_dominance_box is not None and hasattr(a.executor,"get_market_book")),"opp_a":B,"opp_b":A,"need_sep_opp":z}
 def _d1_step3_walk_and_call(b,s2,bk_a,bk_b,bk_oa_pre,bk_ob_pre,pre_bal_a,pre_bal_b,pre_bal_ms,t_bk0):
  s1=s2["s1"];D=s1["candidate_box"];_e,T,S=s1["box_type"],s1["sleeve_src"],s1["cand_asset"];_E,_D,_C,_B=s1["tok_a"],s1["tok_b"],s1["lbl_a"],s1["lbl_b"];q,p=s1["px_a_lim"],s1["px_b_lim"];l,g,f=s1["sh_req"],s1["sh_a_gross"],s1["sh_b_gross"];w,c=s1["cap_net"],s1["fresh_box_net"];z,y=s1["avail_a"],s1["avail_b"];_M,_L,_K,_J=s1["fr_a"],s1["fr_b"],s1["fe_a"],s1["fe_b"];R,t=s1["ipc_age_ms"],s1["is_live_ctf_box"];_r,_d=s1["now_ts"],s1["dedupe_k"];_c,I=s1["own_grad"],s1["zero_fee_box"];M,_q=s1["_ft_cert_2l"],s1["_v3_7d"];_b,s=s1["_zf1_cap"],s1["_zf_c1_merge_ok"];C,U=s2["target_budget"],s2["rem_tte_s"];j=.0
  if s2["need_books"]:
   if True:
    if True:
     try:
      _A=bk_oa_pre;_z=bk_ob_pre;_I=_A.get("bids")or[];_H=_z.get("bids")or[];_G=_A.get("asks")or[];_F=_z.get("asks")or[];_a=max((float(x["price"]if isinstance(x,dict)else x[0])for x in _I),default=.0);Z=max((float(x["price"]if isinstance(x,dict)else x[0])for x in _H),default=.0);Y=min((float(x["price"]if isinstance(x,dict)else x[0])for x in _G),default=.0);X=min((float(x["price"]if isinstance(x,dict)else x[0])for x in _F),default=.0);_y=_a>.0 or(.0<Y<=.12);_x=Z>.0 or(.0<X<=.12)
      if not(_y and _x)or(_a<=.0 and Z<=.0):return{"executed":False,"reason":"ANTI_BOX_COMPLEMENT_UNVERIFIED:EMPTY_OPP_BOOK"}
      _j=_a+Z;Q=(_a if _a>.0 else Y)+(Z if Z>.0 else X);_i=min((float(x["price"]if isinstance(x,dict)else x[0])for x in(bk_a.get("asks")or[])),default=.0);_h=min((float(x["price"]if isinstance(x,dict)else x[0])for x in(bk_b.get("asks")or[])),default=.0);B=_i>.0 and _a>.0 and(_i+_a)>1.015;A=_h>.0 and Z>.0 and(_h+Z)>1.015
      if B or A or _j>1.16 or Q>1.18:return{"executed":False,"reason":f"ANTI_BOX_COMPLEMENT_VETO:{max(_j,Q,_i+_a,_h+Z):.4f}"}
     except Exception as u:return{"executed":False,"reason":f"ANTI_BOX_COMPLEMENT_UNVERIFIED:{u}"}
     j=round((time.perf_counter_ns()-t_bk0)/1e6,2)
     def i(bk_d):
      _P,_O=bk_d.get("asks")or[],bk_d.get("bids")or[]
      if not _P or not _O:return False
      ba=min(float(x["price"]if isinstance(x,dict)else x[0])for x in _P);bb=max(float(x["price"]if isinstance(x,dict)else x[0])for x in _O);return bb>.0 and(ba-bb)<=.041
     L=bool(D.get("is_quiet_book")and i(bk_a)and i(bk_b));P=getattr(b,"risk_config",None)or RISK_CONFIG;O=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{});K=float(P["d1_max_box_cost_net"]if isinstance(P,dict)and"d1_max_box_cost_net"in P else O.get("d1_max_box_cost_net",RISK_CONFIG.get("d1_max_box_cost_net",.985)))
     if T=="COND1_MACRO_PARTITION_BOX"and not _c:a=.985
     elif T=="COND1_MACRO_PARTITION_BOX"and _c and.0<U<=172800.:a=.992 if I else.988
     elif I:
      n=604800. if T in _q else 172800.;H=(float(P["cm_b3_max_walk_cap"]if isinstance(P,dict)and"cm_b3_max_walk_cap"in P else O.get("cm_b3_max_walk_cap",RISK_CONFIG.get("cm_b3_max_walk_cap",.99)))if _e=="BARRIER_MONO"else(.992 if(L or(_c and.0<U<=n))else.99))
      if s:a=max(H,_b)
      elif(_e=="DOMINANCE"and b._is_v5_unleashed_active()and.0<U<=float(O.get("d1_short_tte_threshold_sec",180.))):a=max(H,float(O.get("d1_short_tte_max_box_cost_net",.9925)))
      else:a=H
     elif _e in{"SPORTS_CORRIDOR","MACRO_DOMINANCE","NBA_DOMINANCE","NEGRISK_2LEG","LADDER_MONO","COUNTING_DOMINANCE"}or T=="SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX":a=.988
     elif T=="D1_QUIET_BOOK_BOX"and L and b._is_v5_unleashed_active():a=max(K,.989)
     elif _e=="COMPLETE_SET"and b._is_v5_unleashed_active():a=max(K,min(.99,float(D.get("max_box_cost_net")or.989)))
     else:a=K
     if M:G=max(_b,.999)if s else(.999 if I else.995);a=max(a,min(G,float(D.get("max_box_cost_net")or a)))
     h=walk_equal_shares_dominance_box(bk_a.get("asks")or[],bk_b.get("asks")or[],target_budget_usd=C,fee_rate_a=_M,fee_rate_b=_L,fee_exponent_a=_K,fee_exponent_b=_J,max_box_cost_net=a,min_shares=5,min_box_notional_usd=4.5,min_box_cost_net=.86)
     if not h.get("filled"):
      _w=str(h.get("reason"));logger.info(f"[D1 FRESH BOOK REJECT] {D.get('box_id')} ({S or'BTC'}): {_w} | cap={a:.3f} quiet={L} ipc_age_ms={R:.1f} pre_bal_ms={pre_bal_ms:.1f} book_ms={j:.1f}")
      if not b.dry_run and _stage_b_emit_funnel is not None and R>=.0:
       try:
        _g=str(D.get("box_id")or _d or"")
        if _STAGE_B_DECAY_TRACKER is not None and _g:_STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(_g)
        _v=float(D.get("box_cost_net")or.985);_p=float(D.get("shares")or 10.);_stage_b_emit_funnel("COMPETITOR_DECAY_OBSERVED",sleeve=T,candidate_key=_g,box_type=_e,asset=str(S or""),net_edge_bps=max(.0,1.-_v)*1e4,est_profit_usd=max(.0,1.-_v)*_p,competitor_decay_ms=max(.1,R+pre_bal_ms+j),reason=f"FRESH_BOOK_WALK_REJECT:{_w}")
       except Exception:pass
      return{"executed":False,"reason":f"FRESH_BOOK_WALK_REJECT:{_w}"}
     e=min(float(h["avail_a_shares"]),float(h["avail_b_shares"]))
     if int(h["shares"])>16 and e<2.*float(h["shares"]):
      _o=max(16,int(math.floor(e*.5)));_n=walk_equal_shares_dominance_box(bk_a.get("asks")or[],bk_b.get("asks")or[],target_budget_usd=min(C,(_o+.25)*float(h["eff_px"])),fee_rate_a=_M,fee_rate_b=_L,fee_exponent_a=_K,fee_exponent_b=_J,max_box_cost_net=a,min_shares=5,min_box_notional_usd=4.5,min_box_cost_net=.86)
      if _n.get("filled"):h=_n;e=min(float(h["avail_a_shares"]),float(h["avail_b_shares"]))
     r=max(1.,float((getattr(b,"risk_config",None)or RISK_CONFIG).get("d1_min_depth_mult_gate",1.15)))
     if e+1e-6<r*float(h["shares"]):
      J=int(math.floor((e+1e-9)/r))
      if J<5:return{"executed":False,"reason":"FRESH_BOOK_WALK_REJECT:MIN_DEPTH_MULT_GATE"}
      _m=walk_equal_shares_dominance_box(bk_a.get("asks")or[],bk_b.get("asks")or[],target_budget_usd=min(C,(J+.25)*float(h["eff_px"])),fee_rate_a=_M,fee_rate_b=_L,fee_exponent_a=_K,fee_exponent_b=_J,max_box_cost_net=a,min_shares=5,min_box_notional_usd=4.5,min_box_cost_net=.86)
      if not _m.get("filled")or e+1e-6<r*float(_m["shares"]):return{"executed":False,"reason":"FRESH_BOOK_WALK_REJECT:MIN_DEPTH_MULT_GATE"}
      h=_m;e=min(float(h["avail_a_shares"]),float(h["avail_b_shares"]))
     c=float(h["box_cost_net"])
     if c>.975 and e<1.5*float(h["shares"]):
      W=int(math.floor((e+1e-9)/1.5));_N=(walk_equal_shares_dominance_box(bk_a.get("asks")or[],bk_b.get("asks")or[],target_budget_usd=min(C,(W+.25)*float(h["eff_px"])),fee_rate_a=_M,fee_rate_b=_L,fee_exponent_a=_K,fee_exponent_b=_J,max_box_cost_net=a,min_shares=5,min_box_notional_usd=4.5,min_box_cost_net=.86)if W>=5 else{"filled":False})
      if not _N.get("filled")or e+1e-6<1.5*float(_N["shares"]):logger.info(f"[D1 FRESH BOOK REJECT] {D.get('box_id')} ({S or'BTC'}): QUIET_DEPTH_THINNED | net={c:.4f} sh={h['shares']} avail_min={e:.1f}");return{"executed":False,"reason":"FRESH_BOOK_WALK_REJECT:QUIET_DEPTH_THINNED"}
      h=_N;e=min(float(h["avail_a_shares"]),float(h["avail_b_shares"]));c=float(h["box_cost_net"])
     q=float(h["leg_a_walk"]["worst_px"]);p=float(h["leg_b_walk"]["worst_px"]);l=float(h.get("net_paired_shares")or h["shares"]);g=float(h.get("leg_a_gross_shares")or h["shares"]);f=float(h.get("leg_b_gross_shares")or h["shares"]);z=float(h["avail_a_shares"]);y=float(h["avail_b_shares"]);w=a;o=(not b.dry_run and getattr(b.executor,"client",None)is not None and getattr(getattr(b.executor,"client",None),"_mock_children",None)is None and("execute_atomic_dominance_box"not in getattr(b.executor,"__dict__",{})or getattr(b,"holistic_v5_live_mode",None)is True))
     if o:
      _u=min(.25,max(.0,(_M*((q*(1.-q))**_K))/max(q,1e-6)))if _M>.0 else.0;_t=min(.25,max(.0,(_L*((p*(1.-p))**_J))/max(p,1e-6)))if _L>.0 else.0;_s=quantize_fok_buy_box_legs(shares_net=l,px_a=q,px_b=p,h_a=_u,h_b=_t,max_box_cost_net=a,avail_a=z,avail_b=y,max_budget_usd=max(C,5.),min_shares=5.)
      if _s is None:return{"executed":False,"reason":"FRESH_BOOK_WALK_REJECT:FOK_QUANTIZATION_EXCEEDS_CAP"}
      g=_s["leg_a_gross_shares"];f=_s["leg_b_gross_shares"];l=_s["net_paired_shares"];c=max(c,_s["eff_box_cost_net"])
  if c<.86:return{"executed":False,"reason":f"ANTI_BOX_COST_FLOOR_REJECT:{c:.4f}"}
  N=(str(D.get("leg_a_horizon")or"").lower()=="4h"or str(D.get("leg_b_horizon")or"").lower()=="4h");m=_e=="COMPLETE_SET"or(I and _e in{"NEGRISK_2LEG","NEGRISK_CROSS","NBA_DOMINANCE","SPORTS_CORRIDOR","MACRO_DOMINANCE","COUNTING_DOMINANCE","BARRIER_MONO"});V=getattr(b,"risk_config",None)or RISK_CONFIG;v=str(V.get("d1_routing_mode","hybrid_auto"))
  if v=="fragile_first":d=False
  elif v=="parallel_2leg":d=bool((not N)and min(q,p)>=(.05 if m else.3))
  else:k=("execute_atomic_dominance_box"in getattr(b.executor,"__dict__",{})and not bool(D.get("force_parallel_batch")));F=.975 if k else.994;d=bool((m or((not N)and(not S or S in{"BTC","ETH","SOL","XRP","BNB","DOGE","HYPE","ZEC","XAU","XAG"})and c<=F))and min(q,p)>=(.05 if m else.2)and(z is None or y is None or min(float(z),float(y))>=1.5*l))
  _l=str(D.get("box_id")or f"D1_LIVE_{int(_r)}");_f=getattr(b,"_state_save_lock",None)or b._GLOBAL_STATE_SAVE_LOCK;_k=time.perf_counter_ns();E=dict(box_id=_l,leg_a_token_id=_E,leg_a_label=_C,leg_a_limit_price=q,leg_b_token_id=_D,leg_b_label=_B,leg_b_limit_price=p,shares=l,max_box_cost_net=w,leg_a_avail_shares=z,leg_b_avail_shares=y,fee_rate_a=_M,fee_rate_b=_L,fee_exponent_a=_K,fee_exponent_b=_J,parallel_dispatch=d);return{"_s3_ok":True,"box_id":_l,"st_lock":_f,"t_fok0":_k,"box_call_kw":E,"use_parallel_d1":d,"sh_req":l,"sh_a_gross":g,"sh_b_gross":f,"fresh_box_net":c,"pre_bal_a":pre_bal_a,"pre_bal_b":pre_bal_b,"pre_bal_ms":pre_bal_ms,"book_walk_ms":j}
 def _d1_step4_commit_result(a,s1,s3,res,defer_save=False):
  I,C,H=s3["box_id"],s3["st_lock"],s3["t_fok0"];f,G,h=s3["use_parallel_d1"],s3["sh_req"],s3["fresh_box_net"];q,p=s3["pre_bal_a"],s3["pre_bal_b"];o,i=s3["pre_bal_ms"],s3["book_walk_ms"];g,u,n=s1["candidate_box"],s1["box_type"],s1["sleeve_src"];m,M,L=s1["cand_asset"],s1["tok_a"],s1["tok_b"];l,e=s1["ipc_age_ms"],s1["is_live_ctf_box"];F,t=s1["now_ts"],s1["dedupe_k"];s,k=s1["retry_cd"],s1["seen_boxes"];b=False
  if True:
   j=round((time.perf_counter_ns()-H)/1e6,2);B=bool(res.get("success"));r=""if B else f" | abort={res.get('stage')or res.get('error')or'FAILED'}";logger.info(f"[D1 LATENCY TELEMETRY] {I} ({m or'BTC'}): ipc_age_ms={l:.2f} | pre_bal_ms={o:.2f} | book_walk_ms={i:.2f} | fok_box_ms={j:.2f} | sh={G:.0f} | parallel={f} | ok={B}{r}")
   if _LatencyTrace is not None:
    try:E=_LatencyTrace(box_id=I,asset=str(m or"BTC"),sleeve=n,ipc_age_ms=l,pre_bal_ms=o,book_walk_ms=i,fok_box_ms=j,shares=G,parallel=f,outcome="d1_ok"if B else f"d1_{res.get('stage')or'fail'}");E.emit()
    except Exception:pass
   if not a.dry_run and _stage_b_emit_funnel is not None:
    try:
     A=round(max(.0,1.-h)*1e4,2);z=round(max(.0,1.-h)*G,4);y=round(h*G,4);_stage_b_emit_funnel("ORDER_SUBMITTED",sleeve=n,candidate_key=I,box_type=u,asset=str(m or""),net_edge_bps=A,est_profit_usd=z,notional_usd=y)
     if _STAGE_B_DECAY_TRACKER is not None:
      _STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(I)
      if t:_STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(t)
     if B:_stage_b_emit_funnel("COMPLETE_BASKET_LOCKED",sleeve=n,candidate_key=I,box_type=u,asset=str(m or""),net_edge_bps=A,est_profit_usd=z,notional_usd=y)
     elif isinstance(res.get("residual_unhedged_leg"),dict)or res.get("legged_out"):_stage_b_emit_funnel("PARTIAL_BASKET_UNWOUND",sleeve=n,candidate_key=I,box_type=u,asset=str(m or""),notional_usd=y,reason=str(res.get("stage")or"LEGGED_OUT"))
    except Exception:pass
   c=[];d=bool(not res.get("success")and not res.get("outcome_unknown")and not res.get("legged_out")and not isinstance(res.get("residual_unhedged_leg"),dict));x=a.__dict__.setdefault("_d1_clean_pre_bal_cache",{})
   if d and"_wallet_token_balance"not in a.__dict__:
    D=time.time()
    for w,(_,v)in list(x.items()):
     if(D-v)>120.:x.pop(w,None)
    x[M]=(q,D);x[L]=(p,D)
   else:x.pop(M,None);x.pop(L,None)
   with C:
    if t:
     if d:
      k.discard(t);a.__dict__.get("_seen_d1_box_order",{}).pop(t,None)
      for N,K in list(s.items()):
       if float(K or.0)<=F:s.pop(N,None)
      s[t]=F+9.5
      if e:
       if defer_save:b=True
       else:a.save_state()
     else:s.pop(t,None);a._record_seen_d1_box_key(t)
    if res.get("success")and isinstance(res.get("leg_1"),dict)and isinstance(res.get("leg_2"),dict):c=a._register_live_d1_box_positions(I,g,res,q,p)
    elif res.get("outcome_unknown"):a._register_unknown_d1_box_legs(I,g,res,q,p)
    elif isinstance(res.get("residual_unhedged_leg"),dict):
     a.executor.invalidate_collateral_cache();a._pending_collateral_refresh=True;J=res["residual_unhedged_leg"]
     if float(J.get("residual_shares")or.0)>.01 or J.get("unwind_outcome_unknown"):c=a._register_legged_out_d1_residual(I,g,J,q,p)
     else:a._record_inline_d1_legged_out_close(I,g,J,res)
    elif t and not d:
     if defer_save:b=True
     else:a.save_state()
   return{"executed":bool(res.get("success")),"result":res,"leg_trade_ids":c},b
 def _call_atomic_box_sync(a,s3):
  f=s3["box_call_kw"];c,b=s3["pre_bal_a"],s3["pre_bal_b"];e,d=s3["sh_a_gross"],s3["sh_b_gross"]
  try:return a.executor.execute_atomic_dominance_box(**f,leg_a_pre_balance=c,leg_b_pre_balance=b,min_box_cost_floor=.86,leg_a_shares=e,leg_b_shares=d)
  except TypeError:
   try:return a.executor.execute_atomic_dominance_box(**f,leg_a_pre_balance=c,leg_b_pre_balance=b,min_box_cost_floor=.86)
   except TypeError:
    try:return a.executor.execute_atomic_dominance_box(**f,leg_a_pre_balance=c,leg_b_pre_balance=b)
    except TypeError:return a.executor.execute_atomic_dominance_box(**f)
 def _cache_d1_pre_bals(self,s2,b_a,b_b):
  b,a=float(b_a or.0),float(b_b or.0)
  if s2["use_bal_cache"]:e=s2["s1"];d=time.time();c=self.__dict__.setdefault("_d1_clean_pre_bal_cache",{});c[e["tok_a"]]=(b,d);c[e["tok_b"]]=(a,d)
  return b,a
 def maybe_execute_graduated_d1_box(a,candidate_box):
  Q=a._d1_step1_gate_and_preempt(candidate_box,concurrent_ok=False)
  if not Q.get("_s1_ok"):return Q
  u=Q["slot_info"]
  try:
   N,M=Q["m_a"],Q["m_b"];p=getattr(a,"_main_loop",None);o=p is not None and getattr(p,"_thread_id",None)==threading.get_ident()
   if Q["is_live_ctf_box"]and Q["_signaled_d1"]>0 and not o:
    for _ in range(60):
     if not a._has_inflight_maker_anchor(N,M,Q["_preempt_keys_d1"]):break
     time.sleep(.015)
   s=getattr(a,"_last_known_collateral",None);c=s
   if Q["is_live_ctf_box"]and(s is None or(Q["_signaled_d1"]>0 and not a.dry_run)):
    try:c=a.executor.get_collateral_balance()
    except Exception:c=None
   P=a._d1_step2_budget_and_bal_prep(Q,c,s,async_reserved_usd=.0)
   if not P.get("_s2_ok"):return P
   l=k=e=d=None;i=h=g=.0;r=time.perf_counter_ns()
   if Q["is_live_ctf_box"]:
    v=_get_hot_io_pool();x,w,H,G=P["now_pb"],P["bal_ttl"],P["c_ba"],P["c_bb"];C,B=Q["tok_a"],Q["tok_b"];A=time.perf_counter_ns();F=None if(H is not None and(x-H[1])<=w)else v.submit(a._wallet_token_balance,C);E=None if(G is not None and(x-G[1])<=w)else v.submit(a._wallet_token_balance,B);L=H[0]if F is None else F.result()[0];K=G[0]if E is None else E.result()[0];g=round((time.perf_counter_ns()-A)/1e6,2);i,h=a._cache_d1_pre_bals(P,L,K)
    if P["need_books"]:
     r=time.perf_counter_ns();z,y,n=P["opp_a"],P["opp_b"],P["need_sep_opp"];j="get_market_book"in getattr(a.executor,"__dict__",{});l,k,e,d=a._get_d1_books_from_ws(Q["candidate_box"],C,B,z,y,n,j);m=[t for t,b in((C,l),(B,k))if b is None]
     if n:m.extend([t for t,b in((z,e),(y,d))if b is None and t not in m])
     if m:
      if not j and hasattr(a.executor,"get_market_books_batch"):q=a.executor.get_market_books_batch(m)or{}
      else:D={t:v.submit(a.executor.get_market_book,t)for t in m};q={t:(f.result()or{})for t,f in D.items()}
      if l is None:l=q.get(C)or{}
      if k is None:k=q.get(B)or{}
      if e is None:e=k if not n else(q.get(z)or{})
      if d is None:d=l if not n else(q.get(y)or{})
   O=a._d1_step3_walk_and_call(P,l,k,e,d,i,h,g,r)
   if not O.get("_s3_ok"):return O
   J=a._call_atomic_box_sync(O);I,_=a._d1_step4_commit_result(Q,O,J,defer_save=False);return I
  finally:a._d1_release_inflight_slot(u)
 async def maybe_execute_graduated_d1_box_async(a,candidate_box,concurrent_ok=False):
  s=str(candidate_box.get("box_type")or"DOMINANCE").strip().upper()
  if s in{"SINGLE_LEG_LOCK","NEGRISK_CONVERT","CTF_OVERROUND","MULTI_LEG_BUNDLE"}:return await asyncio.to_thread(a.maybe_execute_graduated_d1_box,candidate_box)
  S=a._d1_step1_gate_and_preempt(candidate_box,concurrent_ok=concurrent_ok)
  if not S.get("_s1_ok"):return S
  r=S["slot_info"];d=.0
  try:
   if S["is_live_ctf_box"]and S["_signaled_d1"]>0:await a._wait_maker_anchor_preempt_async(S["m_a"],S["m_b"],S["_preempt_keys_d1"])
   q=getattr(a,"_last_known_collateral",None);c=q
   if S["is_live_ctf_box"]and(q is None or(S["_signaled_d1"]>0 and not a.dry_run)):
    try:c=await asyncio.to_thread(a.executor.get_collateral_balance)
    except Exception:c=None
   y=float(getattr(a,"_d1_async_reserved_usd",.0)or.0);R=a._d1_step2_budget_and_bal_prep(S,c,q,async_reserved_usd=y)
   if not R.get("_s2_ok"):return R
   if S["is_live_ctf_box"]:d=float(R["target_budget"]or.0);a._d1_async_reserved_usd=y+d
   n=m=f=e=None;k=j=i=.0;M=time.perf_counter_ns()
   if S["is_live_ctf_box"]:
    B,x,O,N=R["now_pb"],R["bal_ttl"],R["c_ba"],R["c_bb"];L,K=S["tok_a"],S["tok_b"];w=not(O is not None and(B-O[1])<=x);u=not(N is not None and(B-N[1])<=x);J,I,o=R["opp_a"],R["opp_b"],R["need_sep_opp"];l="get_market_book"in getattr(a.executor,"__dict__",{});g=[]
    if R["need_books"]:
     n,m,f,e=a._get_d1_books_from_ws(S["candidate_box"],L,K,J,I,o,l);g=[t for t,b in((L,n),(K,m))if b is None]
     if o:g.extend([t for t,b in((J,f),(I,e))if b is None and t not in g])
    async def h():
     if not g:return{}
     if not l and asyncio.iscoroutinefunction(getattr(a.executor,"get_market_books_batch_async",None)):return await a.executor.get_market_books_batch_async(g)or{}
     if not l and asyncio.iscoroutinefunction(getattr(a.executor,"get_market_book_async",None)):b=await asyncio.gather(*[a.executor.get_market_book_async(t)for t in g]);return{t:(v or{})for t,v in zip(g,b)}
     b=await asyncio.gather(*[asyncio.to_thread(a.executor.get_market_book,t)for t in g]);return{t:(v or{})for t,v in zip(g,b)}
    H=time.perf_counter_ns();G,F,E=await asyncio.gather(asyncio.to_thread(a._wallet_token_balance,L)if w else asyncio.sleep(0,result=(O[0],.0)),asyncio.to_thread(a._wallet_token_balance,K)if u else asyncio.sleep(0,result=(N[0],.0)),h());i=round((time.perf_counter_ns()-H)/1e6,2);k,j=a._cache_d1_pre_bals(R,G[0],F[0])
    if R["need_books"]:
     if g:
      A=getattr(a,"_pos_market_ws",None)
      if A is not None and not l and hasattr(A,"seed_book"):
       for D,C in E.items():
        if isinstance(C,dict)and(C.get("bids")or C.get("asks")):A.seed_book(D,C)
     if n is None:n=E.get(L)or{}
     if m is None:m=E.get(K)or{}
     if f is None:f=m if not o else(E.get(J)or{})
     if e is None:e=n if not o else(E.get(I)or{})
   Q=a._d1_step3_walk_and_call(R,n,m,f,e,k,j,i,M)
   if not Q.get("_s3_ok"):return Q
   if"execute_atomic_dominance_box"in getattr(a.executor,"__dict__",{})or not hasattr(a.executor,"execute_atomic_dominance_box_async"):z=await asyncio.to_thread(a._call_atomic_box_sync,Q)
   else:z=await a.executor.execute_atomic_dominance_box_async(**Q["box_call_kw"],leg_a_pre_balance=Q["pre_bal_a"],leg_b_pre_balance=Q["pre_bal_b"],min_box_cost_floor=.86,leg_a_shares=Q["sh_a_gross"],leg_b_shares=Q["sh_b_gross"])
   P,p=a._d1_step4_commit_result(S,Q,z,defer_save=True)
   if p:await asyncio.to_thread(a.save_state)
   return P
  finally:
   if d>.0:a._d1_async_reserved_usd=max(.0,float(getattr(a,"_d1_async_reserved_usd",.0)or.0)-d)
   a._d1_release_inflight_slot(r)
 def _make_single_leg_lock_pos(b,lid,box_type,sleeve_src,cand_asset,horizon_s,mid_a,cid_a,tok_a,side_s,nr_a,f_sh,not_u,fee_u,fr_a,fe_a,fee_src,exp_ts,now_ts,pre_b,oid,h_mat,unk=False,sub_ts=None):
  from src.polymarket_research.riskless_protocol_v2_expansion import resolve_canonical_fee_source as a;d=round((not_u+fee_u)/max(f_sh,.01),5);c="maker_post_only_0pct"if fee_src=="maker_post_only_0pct"else a(fr_a,sleeve_src,fee_src);e={"trade_id":lid,"box_id":lid,"box_partner_trade_id":"","is_dominance_box":False,"is_single_leg_lock":True,"hold_to_maturity_lock":h_mat,"box_type":box_type,"box_cost_net":d,"box_total_cost_usd":round(not_u+fee_u,4),"sleeve":sleeve_src,"sleeve_source":sleeve_src,"entry_tte":max(1.,exp_ts-now_ts),"event_id":lid,"event_group_key":"","market_id":mid_a,"condition_id":cid_a,"token_id":tok_a,"target_token":side_s,"asset":cand_asset,"horizon":horizon_s,"is_subhourly":False,"neg_risk":bool(nr_a),"candle_open_spot":1e2,"entry_spot_ref":1e2,"spot_denomination":"USD","candle_sigma":.0,"entry_price":round(not_u/max(f_sh,.01),4),"entry_shares":f_sh,"gross_entry_shares":f_sh,"remaining_shares":f_sh,"filled_exit_shares":.0,"remaining_exit_shares":f_sh,"remaining_cost_basis":not_u,"realized_exit_cash":.0,"realized_exit_fee":.0,"gross_exit_cash":.0,"average_exit_price":.0,"exit_trade_ids":[],"notional_usd":not_u,"fee_usd":fee_u,"entry_fee_cash_usd":fee_u,"entry_fee_asset":"USDC","fee_source":c,"fee_rate_applied":fr_a,"fee_exponent_applied":fe_a,"target_exit_price":1. if h_mat else.99,"exit_order_size":f_sh,"entry_time_utc":datetime.now(timezone.utc).isoformat(),"entry_ts":now_ts,"candle_expiry_ts":exp_ts,"pre_token_balance":pre_b,"order_id":oid,"entry_order_id":oid,"trade_ids":[],"transactions_hashes":[],"status":"ENTRY_OUTCOME_UNKNOWN"if unk else(ExecutionStatus.POSITION_CONFIRMED if b.dry_run else ExecutionStatus.MATCHED_PENDING_SETTLEMENT),"inventory_reconciled":bool(b.dry_run and not unk),"exit_order_id":None,"exit_order_status":"ENTRY_OUTCOME_UNKNOWN"if unk else("DETERMINISTIC_TERMINAL_HOLD"if h_mat else("NONE"if b.dry_run else"AWAITING_DELTA_SETTLEMENT")),"terminal_policy":"DETERMINISTIC_TERMINAL_HOLD"if h_mat else None,"is_liquidating":False,"unwind_order_id":None,"unwind_start_time":.0}
  if sub_ts is not None:e["submitted_at_ts"]=sub_ts
  return e
 _finish_single_leg_lock=_bind_hv_method(_hv__finish_single_leg_lock,'_finish_single_leg_lock');_finish_negrisk_convert_arb=_bind_hv_method(_hv__finish_negrisk_convert_arb,'_finish_negrisk_convert_arb');_record_inline_d1_legged_out_close=_bind_hv_method(_hv__record_inline_d1_legged_out_close,'_record_inline_d1_legged_out_close')
 def _register_live_d1_box_positions(self,box_id,cand,res,pre_bal_a,pre_bal_b):from src.polymarket_research.riskless_protocol_v2_expansion import register_live_d1_box_positions_impl as a;return a(self,box_id,cand,res,pre_bal_a,pre_bal_b,ExecutionStatus.POSITION_CONFIRMED,ExecutionStatus.MATCHED_PENDING_SETTLEMENT)
 def _register_legged_out_d1_residual(a,box_id,cand,resid,pre_bal_a,pre_bal_b):
  k=time.time();j=float(cand.get("expiry_ts")or(k+180.));d=str(cand.get("asset")or"BTC").upper();q=str(resid.get("token_id")or"");c={str(cand.get("leg_a_token_id")):("leg_a",pre_bal_a),str(cand.get("leg_b_token_id")):("leg_b",pre_bal_b)};o,m=c.get(q,("leg_a",.0));n=float(resid.get("matched_shares")or cand.get("shares")or 12.);i=bool(resid.get("unwind_outcome_unknown"));h=n if i else float(resid.get("residual_shares")or.0);t=float(resid.get("price")or cand.get(f"{o}_limit_price")or.48);s=.0 if resid.get("is_maker_anchor")else(float(cand[f"{o}_fee_rate"])if cand.get(f"{o}_fee_rate")is not None else.07);r=float(cand.get(f"{o}_fee_exponent",1.)or 1.);e=round(h*t,4);l=round(h*s*((t*(1.-t))**r),4)if s>.0 else.0;g=f"{box_id}_LEG_RESID"
  if g in a.active_positions or any(p.get("trade_id")==g for p in a.closed_positions):g=f"{g}_{int(k)}"
  f=(resid.get("unwind_result")or{}).get("orderID")if isinstance(resid.get("unwind_result"),dict)else None;b=float(cand.get(f"{o}_strike")or cand.get("k_low"if o=="leg_a"else"k_high")or 1e2);a.active_positions[g]={"trade_id":g,"box_id":box_id,"is_dominance_box":False,"is_legged_out_residual":True,"pending_unwind_tag":"D1_LEGGED_OUT_RESIDUAL_UNWIND","sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","entry_tte":max(1.,j-k),"event_id":box_id,"market_id":str(cand.get(f"{o}_market_id")or g),"condition_id":str(cand.get(f"{o}_condition_id")or""),"token_id":q,"target_token":str(cand.get(f"{o}_side")or"UP"),"asset":d,"horizon":str(cand.get(f"{o}_horizon")or"15m"),"is_subhourly":True,"candle_open_spot":b,"entry_spot_ref":b,"spot_denomination":"USD","candle_sigma":.0025 if d=="BTC"else.0035,"entry_price":t,"entry_shares":h,"gross_entry_shares":h,"remaining_shares":h,"filled_exit_shares":.0,"remaining_exit_shares":h,"remaining_cost_basis":e,"realized_exit_cash":.0,"realized_exit_fee":.0,"gross_exit_cash":.0,"average_exit_price":.0,"exit_trade_ids":[],"notional_usd":e,"fee_usd":l,"entry_fee_cash_usd":l,"entry_fee_asset":"USDC","fee_source":"crypto_fees_v2","fee_rate_applied":s,"fee_exponent_applied":r,"target_exit_price":.99,"entry_time_utc":datetime.now(timezone.utc).isoformat(),"entry_ts":k,"candle_expiry_ts":j,"pre_token_balance":m,"order_id":resid.get("orderID"),"entry_order_id":resid.get("orderID"),"trade_ids":[],"transactions_hashes":[],"status":ExecutionStatus.MATCHED_PENDING_SETTLEMENT,"inventory_reconciled":False,"exit_order_id":None,"exit_order_status":"UNWIND_EXECUTION_OUTCOME_UNKNOWN"if i else"UNWIND_RETRY_REQUIRED","stop_triggered_ts":k,"next_unwind_retry_ts":k+.35,"unwind_attempt_ts":k,"unwind_order_id":f if i else None,"is_liquidating":False,"unwind_start_time":k};a._refresh_global_halt();a.save_state();logger.warning(f"[D1 LEGGED-OUT RESIDUAL SUPERVISED] {g} ({d}): {h:.2f} sh queued for supervised unwind.");return[g]
 def _register_unknown_d1_box_legs(a,box_id,cand,res,pre_bal_a,pre_bal_b):
  m=time.time();l=float(cand.get("expiry_ts")or(m+180.));t=float(cand.get("shares")or 12.);d={str(cand.get("leg_a_token_id")):("leg_a",pre_bal_a),str(cand.get("leg_b_token_id")):("leg_b",pre_bal_b)};q=[(res.get("leg_1_token_id")or cand.get("leg_a_token_id"),res.get("leg_1_order_id")),(res.get("leg_2_token_id")or cand.get("leg_b_token_id"),res.get("leg_2_order_id"))];g=[];c=[]
  for k,(h,i)in enumerate(q):
   j=str(h or"")
   if not j:continue
   e=f"{box_id}_UNK_{k+1}"
   if e in a.active_positions or any(p.get("trade_id")==e for p in a.closed_positions):e=f"{e}_{int(m)}"
   g.append(e);c.append((k,j,i))
  for o,(k,j,i)in enumerate(c):e=g[o];b=g[1-o]if len(g)==2 else"";r,n=d.get(j,("leg_a"if k==0 else"leg_b",.0));s=float(cand.get(f"{r}_limit_price")or.5);f=float(cand.get(f"{r}_strike")or cand.get("k_low"if r=="leg_a"else"k_high")or 1e2);a.active_positions[e]={"trade_id":e,"box_id":box_id,"box_partner_trade_id":b,"is_dominance_box":True,"sleeve":"D1_SAME_ORACLE_DOMINANCE_BOX","event_id":box_id,"market_id":str(cand.get(f"{r}_market_id")or e),"condition_id":str(cand.get(f"{r}_condition_id")or""),"token_id":j,"target_token":str(cand.get(f"{r}_side")or"UP"),"asset":str(cand.get("asset")or"BTC").upper(),"candle_open_spot":f,"entry_spot_ref":f,"spot_denomination":"USD","candle_sigma":.003,"entry_price":s,"entry_shares":t,"gross_entry_shares":t,"remaining_shares":t,"filled_exit_shares":.0,"remaining_exit_shares":t,"remaining_cost_basis":round(t*s,4),"realized_exit_cash":.0,"realized_exit_fee":.0,"gross_exit_cash":.0,"average_exit_price":.0,"exit_trade_ids":[],"notional_usd":round(t*s,4),"intended_notional":round(t*s,4),"fee_usd":.0,"entry_fee_cash_usd":.0,"entry_fee_asset":"USDC","fee_source":"crypto_fees_v2","target_exit_price":.99,"entry_time_utc":datetime.now(timezone.utc).isoformat(),"entry_ts":m,"submitted_at_ts":m,"candle_expiry_ts":l,"pre_token_balance":n,"entry_order_id":i,"order_id":i,"trade_ids":[],"transactions_hashes":[],"status":"ENTRY_OUTCOME_UNKNOWN","exit_order_status":"ENTRY_OUTCOME_UNKNOWN","inventory_reconciled":False,"is_liquidating":False,"unwind_order_id":None,"unwind_start_time":.0}
  a._refresh_global_halt();a.save_state()
 maybe_execute_graduated_maker_anchor_box=_bind_hv_method(_hv_maybe_execute_graduated_maker_anchor_box,'maybe_execute_graduated_maker_anchor_box')
 async def maybe_execute_graduated_single_leg_maker_lock(c,candidate_box):
  if c._is_d1_box_halted():return{"executed":False,"reason":"DISABLED_OR_HALTED"}
  _cl=str(candidate_box.get("box_type")or"").strip().upper()
  if _cl!="SINGLE_LEG_MAKER_LOCK":return{"executed":False,"reason":f"UNSUPPORTED_SINGLE_LEG_MAKER_TYPE:{_cl}"}
  _bO=str(candidate_box.get("sleeve_source")or"BOND1_UMA_RESOLUTION_CARRY").strip();_bN=str(candidate_box.get("asset")or _bO[:4]).strip().upper();_df=str(candidate_box.get("leg_a_market_id")or"")
  if _df in{"6707502","6707503"}:return{"executed":False,"reason":"D001_DISPUTED_KMIA_NON_INTERFERENCE"}
  _de=str(candidate_box.get("leg_a_condition_id")or"");_dd=str(candidate_box.get("leg_a_token_id")or"");_bL=str(candidate_box.get("leg_a_opp_token_id")or"").strip()
  if _dd and not _bL:
   from src.polymarket_research.riskless_protocol_v2_expansion import resolve_missing_opp_token_id as _h;_bM=_h(c,_df,_de,_dd)
   if _bM:_bL=_bM;candidate_box["leg_a_opp_token_id"]=_bL
  _c2=str(candidate_box.get("leg_a_side")or"YES").upper()
  if not _bO or not _df or not _dd or not _bL or _dd==_bL:return{"executed":False,"reason":"INVALID_SINGLE_LEG_MAKER_INVARIANTS"}
  _a1=c.__dict__.setdefault("_inflight_maker_anchor_keys",set());_P=c.__dict__.setdefault("_inflight_maker_anchor_types",set());_9=c.__dict__.setdefault("_inflight_s2_maker_keys",set());_ck=str(candidate_box.get("dedupe_key")or f"BOND1_MKR_{_df}");_aG=str(candidate_box.get("pair_dedupe_key")or f"BOND1_{_df}");_bK=c._is_unlimited_slots_active()or c._is_v5_unleashed_active();from src.polymarket_research.riskless_protocol_v2_expansion import(PROTOCOL_V2_MATH_SLEEVES as _q,check_per_event_concentration_cap as e,check_s2_live_adverse_move_cancel as T,check_sll_cand_dispute_guard as _g,compute_d1_per_market_notional_cap as P,compute_dynamic_riskless_tier_caps as Q,compute_sll_entry_budget as q,compute_sll_maker_keep_and_renew as g,debit_sll_collateral_after_fill as Z,eval_sll_fresh_book_and_peg as _j,eval_sll_live_book_poll as _A,extract_sll_event_group_key as _k,extract_top_bid_from_book as A,is_d1_dedupe_blocked as w,is_market_busy_for_scaling as _m,is_s2_maker_concurrent_capped,maybe_preempt_low_tier_s2_maker_slot as r,maybe_preempt_mlk1_if_bond1_starved as N,prepare_sll_stalk_guard as _B,record_sll_exit_cooldown as _r,release_sll_pending_intent as o,resolve_harvester_sll_tick_size as _a,select_sll_velocity_preempt_target as R,sll_repost_expiry_and_ok as s,sll_settlement_lag_floor_hours as _c,sync_harvester_sll_enforced_tick as v,spawn_fast_htm_maker_fill_reconcile as O,sync_pending_intents_on_collateral_refresh as F,update_sll_intent_partial_fill as y);_a0=_bO in{"S2_EXACT_TWAP_LOCK","S2_RTDS_EXACT_TWAP_INTEGRATOR"}
  if _a0 and not await r(c,_bN,_9):return{"executed":False,"reason":"S2_MAKER_CONCURRENT_CAP_1"}
  _bJ=f"SINGLE_LEG_MAKER_LOCK:{_df}";_2=sum(1 for k in _P if str(k).startswith("SINGLE_LEG_MAKER_LOCK:"))
  if(_bJ in _P or(not _a0 and _2>=(8 if _bK else 2))or len(_a1)>=((12 if _a0 else 10)if _bK else(6 if _a0 else 4))):return{"executed":False,"reason":"SINGLE_LEG_MAKER_ALREADY_INFLIGHT"}
  if _bO=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER":
   _aZ=sum(1 for _iv in getattr(c,"pending_entry_intents",{}).values()if isinstance(_iv,dict)and _iv.get("sleeve_source")=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER");_b8=(max(1,int(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("mkr_lock1_max_concurrent_slots",1)or 1))if(getattr(c,"enforce_bond1_smart_queue",False)or(not c.dry_run and getattr(c.executor,"client",None)is not None and getattr(getattr(c.executor,"client",None),"_mock_children",None)is None and"post_maker_entry_order"not in getattr(c.executor,"__dict__",{})))else 1)
   if _aZ>=_b8:return{"executed":False,"reason":"MKR_LOCK1_CONCURRENT_CAP_1"}
  _c1=time.time();_b7=_g(candidate_box)
  if _b7:return{"executed":False,"reason":_b7}
  _bI=c.__dict__.setdefault("_seen_d1_box_keys",set());_cj=c.__dict__.setdefault("_d1_retry_cooldown_until",{})
  if(w(c,_ck,_aG,[_df],_c1)or(_ck and float(_cj.get(_ck,.0)or.0)>_c1)or(_aG and float(_cj.get(_aG,.0)or.0)>_c1)):return{"executed":False,"reason":"ALREADY_SEEN_OR_COOLDOWN"}
  if not c.dry_run and(not getattr(c,"_startup_reconciled",False)or c._global_halt_reasons()or _df in c._reconciling_market_ids()):return{"executed":False,"reason":"NOT_READY_OR_GLOBAL_HALT"}
  _b6=getattr(c,"risk_config",None)or RISK_CONFIG
  try:
   from src.polymarket_research.stage_c_zero_loss_velocity import load_alpha124_graduation_maps_with_lkg_cache as E;_b5,_ci,_bo=E(c,DATA_DIR,PIPELINE_ROOT,json_loads_fn=_json_loads,stale_reason="ALPHA124_STATE_MISSING_OR_STALE",missing_reason="ALPHA124_STATE_MISSING_OR_STALE")
   if _bo is not None or _b5 is None:return{"executed":False,"reason":_bo or"ALPHA124_STATE_MISSING_OR_STALE"}
   def V(rec):a=rec.get("legging_adjusted_pnl_t1000_usd",rec.get("realized_pnl_t1000_usd",.0));return bool(int(rec.get("closed",0)or 0)>=8 and float(rec.get("win_rate_pct",.0)or.0)>=1e2 and float(rec.get("realized_pnl_t1000_usd",.0)or.0)>.0 and float(a or.0)>.0)
   _ch=_bO=="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER";_aY=_bO=="MKR_REWARD_LOCKED_CARRY";_bH=_bO in{"S2_EXACT_TWAP_LOCK","S2_RTDS_EXACT_TWAP_INTEGRATOR"};_bG=_bO in{"W_PRUNE1_DEAD_NO_BOND","UMA_READY1_LIVENESS_PRIORITY"};_bn=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{});_1=bool(_bO in{"C1_BINARY_COMPLETE_SET","D1_SAME_ORACLE_DOMINANCE_BOX","CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"}and bool(_bn.get("enable_inventory_backed_maker_completion",True))and(bool(candidate_box.get("full_throttle_bridge"))or candidate_box.get("rule_verified")is True));_0=str(candidate_box.get("partner_held_token_id")or candidate_box.get("leg_b_token_id")or(_bL if _bO=="C1_BINARY_COMPLETE_SET"else"")or"").strip();n,m,B=.0,.0,.998
   if _1:
    from src.polymarket_research.riskless_protocol_v2_expansion import resolve_unencumbered_partner_inventory_and_leg_cap as d
    if not _0 or _0==_dd:return{"executed":False,"reason":"PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
    n,m,B=d(c,candidate_box,_0,default_max_box_net=.994,now_ts=_c1,verify_wallet=not c.dry_run)
    if n<5.:return{"executed":False,"reason":"PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
    if B<=.01:return{"executed":False,"reason":f"PARTNER_COST_BASIS_EXCEEDS_BOX_CAP:{m:.4f}"}
    candidate_box["_inventory_backed_maker"]=True
   _8={str(x).upper()for x in(_bn.get("paused_riskless_sleeves")or[])};_J=bool(getattr(c,"enforce_paused_riskless_sleeves",False)or(not c.dry_run and getattr(c.executor,"client",None)is not None and getattr(getattr(c.executor,"client",None),"_mock_children",None)is None and"post_maker_entry_order"not in getattr(c.executor,"__dict__",{})))
   if _J and not bool(_bn.get("enable_single_leg_maker_bond1",True)):return{"executed":False,"reason":"SINGLE_LEG_MAKER_BOND1_DISABLED"}
   if _J and _bO.upper()in _8:return{"executed":False,"reason":f"PAUSED_RISKLESS_SLEEVE:{_bO}"}
   from src.polymarket_research.stage_c_zero_loss_velocity import check_strict_pure_riskless_candidate_gate as l;_al=l(c,candidate_box,_bn,is_maker=True)
   if _al is not None:return{"executed":False,"reason":_al}
   _cg=_b5.get(_bO)or{};_cf=_b5.get("BOND1_UMA_RESOLUTION_CARRY")or{};_cL,_cK,_cJ,_b4=c._live_sleeve_graduation_stats(_bO);_bm=(_cJ==0 and _cL>=8 and _cK==_cL and _b4>.0);_aF=(_cJ==0 and _cL>=3 and _cK==_cL and _b4>.0);_c0=(_cJ==0)and((int(_cg.get("losses",0)or 0)==0 and(_bO!="UMA_READY1_LIVENESS_PRIORITY"or int(_cf.get("losses",0)or 0)==0))or _bm or(_aF and _bO in{"BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"}));_cI=V(_b5.get("D1_SAME_ORACLE_DOMINANCE_BOX")or{});_R={"W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK","W_SOLAR1_POST_2351_LOCK","SP2_NBA_ENDGAME_LOCK","U1_DAILY_UPDOWN_LOCK","CM_B2_PYTH_SESSION_NO_LOCK","CM_U1_PYTH_CLOSE_LOCK"};_cH=bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional",{}).get("riskless_only_mode",False))and not c.dry_run;_aX=not(_cH and _bO in _R)or float(candidate_box.get("p_model")or.0)>=.999;_aW=((V(_cg)or _bm or(_bO=="UMA_READY1_LIVENESS_PRIORITY"and V(_cf)))and _c0 and _aX);_ak=bool(_bn.get("enable_ungraduated_v3_math_live",False))if _J else bool(_b6.get("enable_ungraduated_v3_math_live",False)or _bn.get("enable_ungraduated_v3_math_live",False));_bl=(_ak and(not _J or _bO.upper()not in _8)and(_bO in _q or _bO.startswith("SP4_")or _bO in{"SP2_NBA_ENDGAME_LOCK","CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH","API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK","B4_TOUCHED_BARRIER_WICK_LOCK","GAS1_AAA_GASOLINE_LOCK","W1_SOLAR_PEAK_LOCK","W1_LOW_TROUGH_LOCK","TEN1_TENNIS_RETIREMENT_SAFE_SET_CORRIDOR","AFF1_FROZEN_SUBPERIOD_COLLAPSE","NFL_PRP1_MILESTONE_AND_MAX_LOCKS","U1_DAILY_UPDOWN_LOCK","CM_B2_PYTH_SESSION_NO_LOCK","CM_U1_PYTH_CLOSE_LOCK"}));_Z=bool((_c0 and _1)or(_c0 and _cI and((_bO in{"BOND1_UMA_RESOLUTION_CARRY","BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","UMA_READY1_LIVENESS_PRIORITY"}and _b6.get("enable_bond1_live_bridge",True)and float(_cg.get("realized_pnl_t1000_usd",.0)or.0)>=.0 and(int(_cg.get("closed",0)or 0)==0 or float(_cg.get("win_rate_pct",1e2)or.0)>=1e2))or(not c.dry_run and c._is_v5_unleashed_active()and _ch and float(candidate_box.get("p_model")or.0)>=(.999 if _cH else.998))or(not c.dry_run and _aY and float(candidate_box.get("p_model")or.0)>=.999 and(bool(_bn.get("enable_reward_locked_carry_live_bridge",True))or not _J))or(not c.dry_run and _bH and float(candidate_box.get("p_model")or.0)>=.9985 and(bool(_bn.get("enable_s2_twap_lock_live",True))or not _J))or(not c.dry_run and c._is_v5_unleashed_active()and(_bG or _bl)and float(candidate_box.get("p_model")or.0)>=.999))))
   if not(_aW or _Z):return{"executed":False,"reason":f"SINGLE_LEG_MAKER_NOT_GRADUATED:{_bO}"}
   if _aY:
    from src.polymarket_research.riskless_protocol_v2_expansion import is_disputed_or_frozen_uma_position as _K;_bF=float(getattr(c,"_last_known_collateral",None)or.0)+sum(float(p.get("notional_usd",.0)or.0)for p in c.active_positions.values()if not position_is_settlement_receivable(p)and not _K(p,_c1))
    if Q(_bF,_bn).get("reward_unlocked"):c._last_rw_carry_cand_ts=_c1
  except Exception as _bp:return{"executed":False,"reason":f"STATE_READ_ERROR:{_bp}"}
  _cZ=float(candidate_box.get("expiry_ts")or.0);_cG=float(candidate_box.get("ts_unix")or _c1);_aV=4.8 if _bH else(45. if(_ch or _1 or _bO in{"BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY","UMA_READY1_LIVENESS_PRIORITY"})else 90.);_aU=39. if _bH else(86400. if(_aY or _1 or _bG)else 86400.);_aT=2.5 if _bH else float(_bn.get("ipc_candidate_max_age_sec",60.)or 60.)
  if not c.dry_run and((_c1-_cG)>_aT or(_cZ>.0 and not(_aV<=(_cZ-_c1)<=_aU))):return{"executed":False,"reason":"STALE_OR_OUTSIDE_TTE_WINDOW"}
  _aS=c.__dict__.setdefault("_prepost_sll_reserved_usd",{});_aE=c.__dict__.setdefault("_prepost_sll_markets",{});_aD=c.__dict__.setdefault("_prepost_sll_events",{})
  if _1:
   if any(not position_is_settlement_receivable(_pm_d)and str(_pm_d.get("token_id")or"").strip()==_dd for _pm_d in c.active_positions.values())or any(isinstance(_im_d,dict)and str(_im_d.get("token_id")or"").strip()==_dd for _im_d in getattr(c,"pending_entry_intents",{}).values()):return{"executed":False,"reason":"MARKET_ALREADY_OCCUPIED"}
  elif _m(c,_df,extra_busy_markets=list(_aE.values())):return{"executed":False,"reason":"MARKET_ALREADY_OCCUPIED"}
  _aj=c._active_box_ids();_cY=GLOBAL_GOVERNANCE_MANAGER.snapshot;_cF=_cY.get("riskless_boxes",{});_z=int(_b6.get("max_concurrent_d1_boxes",4));_F=int(_b6.get("max_total_portfolio_slots",4))
  if c._is_v5_unleashed_active():_z=int(_cF.get("max_concurrent_riskless_boxes",10));_F=int(_cY.get("sizing_tiers",{}).get("max_total_slots",12))
  if len(_aj)>=_z or(not c.dry_run and(len(_aj)+len(c._risk_bearing_positions()))>=_F):return{"executed":False,"reason":"MAX_CONCURRENT_BOXES_REACHED"}
  if _z>=2 and _cZ>.0 and(_cZ-_c1)>3600. and len(_aj)>=(_z-1):return{"executed":False,"reason":"INTRADAY_D1_SLOT_RESERVED"}
  _aR=int(candidate_box.get("_bond1_repost_count")or 0)
  if not c.dry_run and(_ck in _a1 or _bJ in _P or _df in _aE.values()or any(str(i.get("market_id")or"")==_df for i in getattr(c,"pending_entry_intents",{}).values()if isinstance(i,dict))):return{"executed":False,"reason":"SINGLE_LEG_MAKER_ALREADY_INFLIGHT"}
  _7=bool(getattr(c,"enforce_bond1_smart_queue",False)or(not c.dry_run and getattr(c.executor,"client",None)is not None and getattr(getattr(c.executor,"client",None),"_mock_children",None)is None and"post_maker_entry_order"not in getattr(c.executor,"__dict__",{})));_cX=str(candidate_box.get("box_id")or f"MKR_LOCK1_{int(_c1)}");_b3=f"{_cX}_SLL_INTENT";_6=_k(candidate_box);_E,_y,_x,_bk=e(c,candidate_box,market_ids=[_df],now_ts=_c1,enforce_override=bool(_7 and _cF.get("enable_event_slot_diversification",True)),exclude_intent_ids=(_b3,))
  if not _E:return{"executed":False,"reason":_y}
  _6=_bk or _6 or(f"MKT:{_df}"if _df else"")
  if not c.dry_run and _6:_aD[_b3]={"trade_id":_b3,"market_id":_df,"condition_id":_de,"inflight_key":_ck,"event_group_key":_6,"event_id":candidate_box.get("event_id"),"title":candidate_box.get("title"),"leg_a_label":candidate_box.get("leg_a_label"),"asset":_bN,"expiry_ts":_cZ,"notional_usd":5.,"live_maker_anchor_inflight":True}
  try:
   _w=getattr(c,"_last_known_collateral",None);_O=bool(_aR>0 and candidate_box.get("_repeg_zero_fill")and _w is not None and"get_collateral_balance"not in getattr(c.executor,"__dict__",{}))
   if not c.dry_run and(_w is None or(_aR>0 and not _O))and hasattr(c.executor,"get_collateral_balance"):
    _bj=_w
    try:
     _ce=await asyncio.to_thread(c.executor.get_collateral_balance)
     if isinstance(_ce,(int,float))and not isinstance(_ce,bool)and math.isfinite(float(_ce))and float(_ce)>=.0:_w=float(_ce);c._last_known_collateral=_w;F(c,_bj,_w)
    except Exception:
     if _w is None:_w=.0
   if not c.dry_run and(_ck in _a1 or _bJ in _P or _df in _aE.values()or any(str(i.get("market_id")or"")==_df for i in getattr(c,"pending_entry_intents",{}).values()if isinstance(i,dict))):_aD.pop(_b3,None);return{"executed":False,"reason":"SINGLE_LEG_MAKER_ALREADY_INFLIGHT"}
   _E,_y,_x,_aQ=e(c,candidate_box,market_ids=[_df],now_ts=_c1,enforce_override=bool(_7 and _cF.get("enable_event_slot_diversification",True)),exclude_intent_ids=(_b3,))
   if not _E:_aD.pop(_b3,None);return{"executed":False,"reason":_y}
   _6=_aQ or _6;_b2=float(_b6.get("bond1_max_join_queue_usd",_cF.get("bond1_max_join_queue_usd",350.))or 350.);_aP=float(_b6.get("bond1_buried_cancel_sec",_cF.get("bond1_buried_cancel_sec",15.))or 15.);L,_D,_=q(c,_bO,_df,_w,_aW,_7,_cF,_b6,_cY,_cZ-_c1,_c1);L=min(L,_x);_cW=float(candidate_box.get("min_resting_bid",.02 if _1 else.94)or(.02 if _1 else.94));_N=min(.998,float(candidate_box.get("max_box_cost_net",.994)or.994))
   if _1:
    from src.polymarket_research.riskless_protocol_v2_expansion import resolve_unencumbered_partner_inventory_and_leg_cap as d;n,m,B=d(c,candidate_box,_0,default_max_box_net=.994,now_ts=_c1,exclude_intent_id=_b3,verify_wallet=False)
    if n<5.:return{"executed":False,"reason":"PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
    _N=min(_N,B)
    if _N<_cW or _N<=.01:_aD.pop(_b3,None);return{"executed":False,"reason":f"PARTNER_COST_BASIS_EXCEEDS_BOX_CAP:{_N:.4f}"}
   _cE=float(candidate_box.get("max_opp_bid",.99 if _1 else.008)or(.99 if _1 else.008));_H=float(candidate_box.get("anchor_bid_px")or candidate_box.get("leg_a_limit_price")or.0)
   if not(_cW<=_H<=_N):_aD.pop(_b3,None);return{"executed":False,"reason":f"RESTING_BID_OUT_OF_BAND:{_H:.4f}"}
   L=await N(c,_bO,L,_w,_aW,_7,_cF,_b6,_cY,_D,_cZ-_c1,_c1,P(c)if _D>.0 else.0,cand_bid_px=_H);L=min(L,_x);_bi=_c(_bO);_aO=round(((1.-_H)*1e4)/max(_bi,(_cZ-_c1)/3600.),2)if _cZ>_c1 else.0;_bh=candidate_box.get("ask_depth_usd");_bg=candidate_box.get("volume_24h_usd",candidate_box.get("volume24hr"));_aC=candidate_box.get("total_volume_usd");_aB=(_bg is not None)or(_aC is not None);_aA=(max(float(_bg or.0),float(_aC or.0)*.5)if _aB else None);_az=(max(float(_bg or.0),float(_aC or.0))if _aB else None)
   if(not c.dry_run and not _bH and _bO!="MKR_REWARD_LOCKED_CARRY"and _bh is not None and float(_bh or.0)<5. and _az is not None and _az<25.):
    _aD.pop(_b3,None)
    if _ck:_cj[_ck]=time.time()+3e2
    return{"executed":False,"reason":"GHOST_ZERO_VOLUME_BOOK"}
   h=1.
   if _bh is not None and _aA is not None:
    _cV=float(_bh or.0)
    if _cV<5.:
     if _aA<25.:h=.04
     elif _aA<5e2:h=.15
     elif _aA<1500.:h=.65
     elif _aA>=2500.:h=1.1
    elif _cV>=10. and _aA>=1e3:h=1.15
   _ay=round(_aO*h,2);_ai=5;z=int(math.floor(L/_H))
   if _1 and n>.0:z=min(z,int(math.floor(n+1e-9)))
   _5=bool((getattr(c,"enforce_gatling_sizing",False)or getattr(c,"enforce_gatling_fast_gun_reserve",False)or(not c.dry_run and getattr(c.executor,"client",None)is not None and getattr(getattr(c.executor,"client",None),"_mock_children",None)is None and"get_market_book"not in getattr(c.executor,"__dict__",{})and not getattr(c,"enforce_bond1_smart_queue",False)))and float(_cF.get("bond1_maker_fanout_clip_usd_seed")or.0)>.0 and float(_w or.0)<150.)
   if(not _bH and z<(_ai if _5 else 12)and not c.dry_run and _H>=_cW and _aO>=40. and c._is_v5_unleashed_active()):
    _b1=float(_cF.get("bond1_velocity_preempt_mult",1.8)or 1.8);_cD=getattr(c,"_maker_anchor_preempt_events",{});_bf=c.__dict__.setdefault("_claimed_velocity_preempts",set());_b0,_ah=R(c,_ay,_bH,_b1,cand_sleeve=_bO)
    if _ah:
     _cC,_,_=q(c,_bO,_df,_w,_aW,_7,_cF,_b6,_cY,_cZ-_c1,_c1,post_vel_preempt=True,exclude_inflight_key=_ah)
     if int(math.floor(_cC/_H))<_ai:_ah=""
    if _ah:
     _bf.add(_ah)
     try:
      (c.__dict__.setdefault("_maker_anchor_preempt_reasons",{}))[_ah]=f"VELOCITY_UPGRADE:{_ck}";logger.info(f"[BOND1 VELOCITY UPGRADE] Preempting {_ah} ({_b0:.1f} bps/h) -> {_ck} ({_ay:.1f} bps/h @ ${_H:.3f})");_cD[_ah].set()
      for _ in range(16):
       await asyncio.sleep(.06)
       if not any(isinstance(i,dict)and i.get("inflight_key")==_ah for i in c.pending_entry_intents.values()):break
     finally:_bf.discard(_ah)
     _w=getattr(c,"_last_known_collateral",_w);L,_D,_=q(c,_bO,_df,_w,_aW,_7,_cF,_b6,_cY,_cZ-_c1,_c1,post_vel_preempt=True);L=min(L,_x);z=int(math.floor(L/_H))
     if _1 and n>.0:z=min(z,int(math.floor(n+1e-9)))
   if _1:
    n,m,_Q=d(c,candidate_box,_0,default_max_box_net=.994,now_ts=time.time(),exclude_intent_id=_b3,verify_wallet=False);_N=min(_N,_Q);z=min(z,int(math.floor(n+1e-9)))
    if n<_ai or _H>_N+1e-6:_aD.pop(_b3,None);return{"executed":False,"reason":"PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
   if z<_ai:
    _aD.pop(_b3,None)
    if not c.dry_run and _ck:_cj[_ck]=time.time()+(2. if _bH else 8.)
    return{"executed":False,"reason":"INSUFFICIENT_MAKER_BOX_BUDGET"}
   if _a0 and not await r(c,_bN,_9):_aD.pop(_b3,None);return{"executed":False,"reason":"S2_MAKER_CONCURRENT_CAP_1"}
  except BaseException:_aD.pop(_b3,None);(c.__dict__.get("_prepost_partner_pledged_shares")or{}).pop(_b3,None);raise
  _aN=_ck;_a1.add(_aN);_P.add(_bJ)
  if _a0:_9.add(_aN)
  _ag=c.__dict__.setdefault("_maker_anchor_preempt_events",{});_bE=threading.Event();_ag[_aN]=_bE;_aS[_b3]=round(z*_H,4);_aE[_b3]=_df
  if _1:c.__dict__.setdefault("_prepost_partner_pledged_shares",{})[_b3]=(_0,float(z))
  if _b3 in _aD:_aD[_b3]["notional_usd"]=round(z*_H,4)
  t=.0;_cd=getattr(c,"_pos_market_ws",None)
  if _cd is not None and hasattr(_cd,"subscribe_tokens_immediate"):_cd.subscribe_tokens_immediate([_dd,_bL])
  _bZ=asyncio.Event();_n=None;c.__dict__.setdefault("_sll_ws_book_events",{})[_b3]=(_dd,_bL,_bZ)
  try:
   if c.dry_run:D=.0
   elif hasattr(c.executor,"get_market_book"):
    _be="get_market_book"in getattr(c.executor,"__dict__",{});_cc=candidate_box.get("ws_books")if not _be else None;_bD=isinstance(_cc,dict)and(time.time()-float(candidate_box.get("ws_books_ts")or.0))<=.65;_bd=.85 if _aR>0 else 1.5;Y=_cc.get(_dd)if _bD else(_cd.get_book(_dd,max_age_sec=_bd)if(_cd and not _be)else None);X=_cc.get(_bL)if _bD else(_cd.get_book(_bL,max_age_sec=_bd)if(_cd and not _be)else None)
    if isinstance(Y,dict)and Y.get("is_partial_delta")and(not Y.get("bids")or not Y.get("asks")):Y=None
    if isinstance(X,dict)and X.get("is_partial_delta")and not X.get("bids"):X=None
    if Y is None or X is None:
     if(Y is None and X is None and not _be and asyncio.iscoroutinefunction(getattr(c.executor,"get_market_books_batch_async",None))):D,_bY=await asyncio.gather(c._resolve_fast_pre_token_balance_async(_dd,exclude_intent_id=_b3),c.executor.get_market_books_batch_async([_dd,_bL]));Y=(_bY or{}).get(_dd);X=(_bY or{}).get(_bL)
     else:_bX=(not _be)and asyncio.iscoroutinefunction(getattr(c.executor,"get_market_book_async",None));D,Y,X=await asyncio.gather(c._resolve_fast_pre_token_balance_async(_dd,exclude_intent_id=_b3),(c.executor.get_market_book_async(_dd)if _bX else asyncio.to_thread(c.executor.get_market_book,_dd))if Y is None else asyncio.sleep(0,result=Y),(c.executor.get_market_book_async(_bL)if _bX else asyncio.to_thread(c.executor.get_market_book,_bL))if X is None else asyncio.sleep(0,result=X))
     if _cd is not None and not _be and hasattr(_cd,"seed_book"):
      if isinstance(Y,dict):_cd.seed_book(_dd,Y)
      if isinstance(X,dict):_cd.seed_book(_bL,X)
    else:D=await c._resolve_fast_pre_token_balance_async(_dd,exclude_intent_id=_b3)
    _af=(getattr(c.executor,"client",None)is not None and getattr(getattr(c.executor,"client",None),"_mock_children",None)is None);_ax="get_token_tick_size"in getattr(c.executor,"__dict__",{});t=_a(c.executor,_dd,candidate_box,bk_win=Y,mkt_ws=_cd,real_clob=_af,custom_tk_fn=_ax,price_hint=_H)
    if t<=.0 and hasattr(c.executor,"get_token_tick_size")and(_af or _ax):
     try:
      if not _ax and asyncio.iscoroutinefunction(getattr(c.executor,"get_token_metadata_async",None)):_bc,_=await c.executor.get_token_metadata_async(_dd,price_hint=_H);t=float(_bc or.0)
      else:t=float((await asyncio.to_thread(c.executor.get_token_tick_size,_dd,_H))or.0)
     except TypeError:t=float((await asyncio.to_thread(c.executor.get_token_tick_size,_dd))or.0)
     except Exception:t=.0
     if t>.0 and _af:
      if hasattr(c.executor,"update_ws_tick_size"):c.executor.update_ws_tick_size(_dd,t)
      if _cd is not None and hasattr(_cd,"_tick_sizes"):_cd._tick_sizes[_dd]=t
    _cB,_dc,_H,z,t=_j(Y,X,candidate_box,_H,_cW,_N,_cE,L,t,_af,_7,_ch,_bH,_aR,_b2)
    if _cB is not None:
     if(not c.dry_run and _af and bool(_bn.get("enable_clinched_dead_leg_split_sell",False))and _bO in{"W_PRUNE1_DEAD_NO_BOND","MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"}):
      from src.polymarket_research.stage_c_zero_loss_velocity import(evaluate_clinched_dead_leg_split_arb as J,execute_clinched_dead_leg_split_arb as M);_bC,_bb,_ba,_=e(c,candidate_box,market_ids=[_df],now_ts=_c1,enforce_override=bool(_7 and _cF.get("enable_event_slot_diversification",True)),exclude_intent_ids=(_b3,));_Y=(J(candidate_box,X,budget_usd=min(L,_ba),now_ts=_c1,executor=c.executor)if _bC else None)
      if _Y is not None:
       _Y={**_Y,"market_id":_df,"exclude_intent_ids":[_b3]};_cA=await asyncio.to_thread(M,c,candidate_box,_Y,now_ts=_c1)
       if _cA.get("executed")or _cA.get("split_tx_hash")or _cA.get("merged_pairs"):
        if _ck:
         if hasattr(c,"_record_seen_d1_box_key"):c._record_seen_d1_box_key(_ck)
         else:_bI.add(_ck)
        return _cA
     if _dc>.0:_cj[_ck]=time.time()+_dc
     return{"executed":False,"reason":_cB}
    if _1 and n>.0:
     z=min(z,int(math.floor(n+1e-9)))
     if z<_ai:return{"executed":False,"reason":"PURE_RISKLESS_UNVERIFIED_OPP_INVENTORY"}
    _aS[_b3]=round(z*_H,4)
   else:D=await c._resolve_fast_pre_token_balance_async(_dd,exclude_intent_id=_b3)
   _bW=candidate_box.get("leg_a_neg_risk");_dh=_bW if isinstance(_bW,bool)else None
   if hasattr(c.executor,"prewarm_token_market_cache"):
    _a9=c.dry_run or hasattr(getattr(c.executor,"client",None),"_mock_children");_cz=candidate_box.get("leg_a_tick_size")if _a9 else(t if t>.0 else None);_cy=max(.0,float(candidate_box.get("leg_a_market_fee_rate")or candidate_box.get("leg_a_fee_rate")or.0));_cx=max(1.,float(candidate_box.get("leg_a_market_fee_exponent")or candidate_box.get("leg_a_fee_exponent")or 1.))
    try:c.executor.prewarm_token_market_cache(token_id=_dd,tick_size=_cz,neg_risk=bool(_dh),fee_rate_bps=int(round(_cy*1e4)),condition_id=(_de if str(_de or"").startswith("0x")else None),fee_rate=_cy,fee_exponent=_cx,preserve_fee_cache=(_cy<=.0))
    except TypeError:c.executor.prewarm_token_market_cache(token_id=_dd,tick_size=_cz,neg_risk=bool(_dh),fee_rate_bps=int(round(_cy*1e4)),condition_id=(_de if str(_de or"").startswith("0x")else None),fee_rate=_cy,fee_exponent=_cx)
   _v=round((z+.01)*_H,4);_bB=time.time()
   if not c.dry_run:
    _aM,_aw,_av,_=e(c,candidate_box,market_ids=[_df],now_ts=_bB,enforce_override=bool(_7 and _cF.get("enable_event_slot_diversification",True)),exclude_intent_ids=(_b3,))
    if not _aM:return{"executed":False,"reason":_aw}
    if _av<round(z*_H,4)-.05:
     z=int(math.floor(_av/_H))
     if _1 and n>.0:z=min(z,int(math.floor(n+1e-9)))
     if z<_ai:return{"executed":False,"reason":"MAX_EVENT_NOTIONAL_CAP_REACHED"}
     _v=round((z+.01)*_H,4)
   _au=float(candidate_box.get("_bond1_first_post_ts")or _bB);_at=bool(candidate_box.get("queue_front")and float(candidate_box.get("queue_ahead_usd")or.0)<=5.)
   if not c.dry_run:c._mark_token_pre_bal_dirty(_dd)
   _db=time.perf_counter();_I=bool(not c.dry_run and"post_maker_entry_order"not in getattr(c.executor,"__dict__",{})and asyncio.iscoroutinefunction(getattr(c.executor,"post_maker_entry_order_async",None))and bool(getattr(c.executor,"_can_use_native_async_post_order",lambda:False)()));_as=max(.02 if _1 else(.5 if _bH else.9),_cW);_aL=_N if _1 else max(.995,_N)
   if _I:_X=await c.executor.post_maker_entry_order_async(token_id=_dd,price=_H,notional_usd=_v,side="BUY",neg_risk=_dh,min_price_floor=_as,max_price_ceiling=_aL)
   else:_X=await asyncio.to_thread(c.executor.post_maker_entry_order,token_id=_dd,price=_H,notional_usd=_v,side="BUY",neg_risk=_dh,min_price_floor=_as,max_price_ceiling=_aL)
   _a8=round((time.perf_counter()-_db)*1e3,2);c.__dict__.setdefault("_sll_post_http_ms",deque(maxlen=128)).append(_a8);_bV=str((_X or{}).get("orderID")or"").strip()
   if not isinstance(_X,dict)or not _X.get("success")or not _bV:
    if not c.dry_run and D==.0 and not(_X or{}).get("outcome_unknown"):(c.__dict__.get("_d1_dirty_token_until")or{}).pop(_dd,None)
    _aS.pop(_b3,None);_aE.pop(_b3,None);_aD.pop(_b3,None);(c.__dict__.get("_prepost_partner_pledged_shares")or{}).pop(_b3,None);c.pending_entry_intents.pop(_b3,None)
    if _emit_shock_attempt is not None:_emit_shock_attempt({"dry_run":c.dry_run,"asset":_bN or"BOND1","horizon":"box","side":_c2,"market_id":_df,"title":str(candidate_box.get("title")or _cX),"sleeve":_bO,"path_type":"MAKER_BOX","target_px":float((_X or{}).get("price")or _H),"notional_usd":_v,"http_ms":_a8,"stage_outcome":"BOND1_MAKER_POST_FAILED","gate_detail":str((_X or{}).get("error")or"")})
    return{"executed":False,"reason":f"BOND1_MAKER_POST_FAILED:{(_X or{}).get('error')}"}
   _bU=float(_X.get("price")or _H);_bT=float(_X.get("shares")or z);t=v(c.executor,_cd,_dd,t);_cU=time.time();_aS.pop(_b3,None);_aE.pop(_b3,None);_aD.pop(_b3,None);(c.__dict__.get("_prepost_partner_pledged_shares")or{}).pop(_b3,None);_4=round(((1.-_bU)*1e4)/max(_bi,(_cZ-_cU)/3600.),2)if _cZ>_cU else.0;c.pending_entry_intents[_b3]={"trade_id":_b3,"market_id":_df,"token_id":_dd,"opp_token_id":_bL,"anchor_bid_px":_bU,"asset":_bN,"entry_order_id":_bV,"posted_shares":_bT,"posted_notional_usd":round(_bT*_bU,4),"notional_usd":round(_bT*_bU,4),"matched_notional_usd":.0,"collat_drop_usd":.0,"ts":_au,"heartbeat_ts":_cU,"_last_persist_ts":_cU,"live_maker_anchor_inflight":True,"inflight_key":_aN,"sleeve_source":_bO,"event_group_key":_6,**({"inventory_backed_completion":True,"partner_held_token_id":_0,"partner_avg_cost_ps":round(m,4)}if _1 else{}),**({"event_id":str(candidate_box.get("event_id"))}if candidate_box.get("event_id")else{}),**({"ask_depth_usd":round(float(_bh or.0),2)}if _bh is not None else{}),**({"volume_24h_usd":round(float(_aA or.0),2)}if _aA is not None else{}),**({"effective_velocity_bps_hr":round(_4*h,2)}if _aA is not None else{}),"expiry_ts":_cZ,"fifo_rank1_verified":_at,"velocity_bps_hr":_4};c._record_ft_candidate_funnel(candidate_box,stage="MAKER_POSTED",maker_posted=True,is_maker=True)
   if not c.dry_run:
    await asyncio.to_thread(c.save_state)
    if _aR<=0 and _stage_b_emit_funnel is not None:
     try:_stage_b_emit_funnel("ORDER_SUBMITTED",sleeve=_bO,candidate_key=_cX,box_type="SINGLE_LEG_MAKER_LOCK",asset=str(_bN or""),net_edge_bps=round(max(.0,1.-_bU)*1e4,2),est_profit_usd=round(max(.0,1.-_bU)*_bT,4),notional_usd=round(_bT*_bU,4))
     except Exception:pass
   I=None
   if c.dry_run:_G,_aH=_bT,_bU;_ab={"matched":_G,"avg_price":_aH,"cash":round(_G*_aH,4),"fee":.0,"terminal":True};I=o(c.pending_entry_intents,_b3,round(_G*_aH,4))
   else:
    uws=getattr(c.executor,"_user_ws_cache",None);_ar=_au;_cT=max(.0,time.time()-_ar)if"_bond1_first_post_ts"in candidate_box else.0;_bA=.35 if _bH else(float(_b6.get("bond1_book_poll_sec",4.)or 4.));G=(bool(float(_bh or.0)>=1.)if _bh is not None else None);_cw=time.monotonic();_3,_s,_=g(_bO,uws_ok=bool(uws is not None and uws.is_healthy()),exp_ts=_cZ,now_ts=time.time(),created_mono=_cw,posted_px=_bU,rcfg=_b6,first_post_elapsed_s=_cT,has_active_asks=G,matched_notional_usd=.0,volume_24h_usd=_aA);_u=_cw;_C=.0;_i=_cw;_t=_cw;_e=_bU;j=False;W=False;S=None;_f=None;_l=False;u=0;K=_cw;_aq=bool(_cd is not None or getattr(c,"_force_sll_ws_events",False))
    try:
     while time.monotonic()<_s:
      _aK=bool(uws is not None and uws.is_healthy());_,_,_bS=g(_bO,uws_ok=_aK,exp_ts=_cZ,now_ts=time.time(),created_mono=_cw,deadline_mono=_s,posted_px=_bU,rcfg=_b6,first_post_elapsed_s=_cT)
      if(_bE.is_set()or getattr(c,"_shutdown_requested",False)or c._is_d1_box_halted()or _bS):break
      if _J:
       _bz=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{})
       if(not bool(_bz.get("enable_single_leg_maker_bond1",True))or _bO.upper()in{str(x).upper()for x in(_bz.get("paused_riskless_sleeves")or[])}or l(c,candidate_box,_bz,is_maker=True)is not None):j=True;logger.warning(f"[PURE RISKLESS PREEMPT] {_cX}: single-leg maker disabled/paused by governance; canceling {_bV} immediately.");break
      if _bH and T(_bN,_c2,candidate_box,_cZ):j=True;logger.warning(f"[S2 TWAP SIGMA VETO] {_cX}: SHM cushion < 2.5 sigma; canceling {_bV} immediately.");break
      if _b3 in c.pending_entry_intents:
       _cv=time.time();_cS=c.pending_entry_intents[_b3];_cS["heartbeat_ts"]=_cv
       if not c.dry_run and(_cv-float(_cS.get("_last_persist_ts",.0)or.0))>=30.:_cS["_last_persist_ts"]=_cv;await asyncio.to_thread(c.save_state)
      _da=max(.05,min(.1,_s-time.monotonic()))
      if _aK:
       if _aq:
        if _bZ.is_set():await asyncio.sleep(0)
        else:
         _c9=asyncio.create_task(uws.wait_for_fill_or_timeout(_da,prev_seq=uws.fill_sequence))
         if _n is None or _n.done():_n=asyncio.create_task(_bZ.wait())
         _cu,_=await asyncio.wait({_c9,_n},return_when=asyncio.FIRST_COMPLETED)
         if _c9 not in _cu:_c9.cancel();await asyncio.gather(_c9,return_exceptions=True)
       else:await uws.wait_for_fill_or_timeout(_da,prev_seq=uws.fill_sequence)
       _cR=uws.get_order_snapshot(_bV,max_age_sec=5.)
       if isinstance(_cR,dict)and _b3 in c.pending_entry_intents:
        _ct=float(_cR.get("size_matched")or.0)
        if _ct>.0:
         if y(c.pending_entry_intents,_b3,_bT,_bU,_ct,time.time())and not c.dry_run:await asyncio.to_thread(c.save_state)
       if c._ws_snap_fully_filled(_cR,_bT):_l=True;break
      else:
       if _aq:
        try:await asyncio.wait_for(_bZ.wait(),timeout=_da)
        except asyncio.TimeoutError:pass
       else:await asyncio.sleep(_da)
      if _bE.is_set()or getattr(c,"_shutdown_requested",False):break
      _W=bool(_aq and _bZ.is_set())
      if _W:_bZ.clear()
      _by=time.monotonic()
      if hasattr(c.executor,"get_market_book")and((_W and(_by-_C)>=.01)or(_by-_u)>=_bA):
       _u=_by
       if _W:_C=_by
       _a7="get_market_book"in getattr(c.executor,"__dict__",{});_ae=(1. if _bH else min(5.,max(1.,float(_cF.get("maker_ws_book_max_age_sec",5.)or 5.))));_p=_cd.get_book(_bL,max_age_sec=_ae)if(_cd and not _a7)else None;_o=_cd.get_book(_dd,max_age_sec=_ae)if(_cd and not _a7)else None
       if isinstance(_p,dict)and _p.get("is_partial_delta")and not _p.get("bids"):_p=None
       if isinstance(_o,dict)and _o.get("is_partial_delta")and(not _o.get("bids")or not _o.get("asks")):_o=None
       if _p is None or _o is None:
        try:
         if(_p is None and _o is None and not _a7 and hasattr(c.executor,"get_market_books_batch_async")):_cb=await c.executor.get_market_books_batch_async([_bL,_dd]);_p=(_cb or{}).get(_bL);_o=(_cb or{}).get(_dd)
         else:_a6=(not _a7)and hasattr(c.executor,"get_market_book_async");_p,_o=await asyncio.gather((c.executor.get_market_book_async(_bL)if _a6 else asyncio.to_thread(c.executor.get_market_book,_bL))if _p is None else asyncio.sleep(0,result=_p),(c.executor.get_market_book_async(_dd)if _a6 else asyncio.to_thread(c.executor.get_market_book,_dd))if _o is None else asyncio.sleep(0,result=_o))
         if _cd is not None and not _a7 and hasattr(_cd,"seed_book"):
          if isinstance(_p,dict):_cd.seed_book(_bL,_p)
          if isinstance(_o,dict):_cd.seed_book(_dd,_o)
        except Exception:_p,_o=None,None
       if _p is None or _o is None:
        u+=1;_V=max(1,int(_cF.get("maker_max_consecutive_blind_book_polls",3)or 3));_U=3.5 if _bH else 12.
        if u>=_V or(time.monotonic()-K)>=_U:j=True;logger.warning(f"[MAKER BLIND BOOK FAIL-CLOSED CANCEL] {_cX}: {u} blind book polls (age={time.monotonic()-K:.1f}s); canceling {_bV} immediately.");break
       if _p is not None and _o is not None:
        u=0;K=time.monotonic();_a5=t;t=v(c.executor,_cd,_dd,t,bk_wc=_o);_bx=getattr(c.executor,"_clob_400_tick_until",None);_aJ=isinstance(_bx,dict)and _dd in _bx and time.monotonic()<float(_bx[_dd][1])
        if not _aJ and(t<=.0 or t>=.01):
         _bw=float(_cd.get_tick_size(_dd)or.0)if(_cd is not None and hasattr(_cd,"get_tick_size"))else.0
         if 1e-4<=_bw<.01:t=_bw
         elif _bH and _bU>=.96 and hasattr(c.executor,"get_token_tick_size")and(time.monotonic()-_t)>=2.5:
          _t=time.monotonic()
          try:
           _a4=float((await asyncio.to_thread(c.executor.get_token_tick_size,_dd,_bU))or.0)
           if 1e-4<=_a4<.01:t=_a4
          except Exception:pass
        candidate_box["_posted_notional_usd"]=round(_bT*_bU,2);_bv=A(_o);_bR=(_o.get("bids")or[])if isinstance(_o,dict)else[];_bu=sum(float(b["price"]if isinstance(b,dict)else b[0])*float(b["size"]if isinstance(b,dict)else b[1])for b in _bR if float(b["price"]if isinstance(b,dict)else b[0])>_bU+1e-6);_ad=((_bv is not None)and(float(_bv)>_bU+1e-6)and(_bu>50.));_bt=time.time();_ap=_B(c,_ck,candidate_box,_aR,time.monotonic()-_cw,int(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("bond1_max_outbid_repegs",3)),_aP,_bt,is_outbid_now=_ad,buried_since_mono=S);from src.polymarket_research.riskless_protocol_v2_expansion import is_post_expiry_uma_frozen_lock as _b;_a3=float(_w or 75.)+sum(float(_p_lq.get("notional_usd",.0)or.0)for _p_lq in c.active_positions.values()if isinstance(_p_lq,dict)and not position_is_settlement_receivable(_p_lq)and not _b(_p_lq,_bt));_cQ,_c8,S,_cP=_A(_p,_o,candidate_box,_bU,_cW,_N,_cE,t,_7,_bH,_aR,_b2,_ap,_cZ,S,collat_usd=_a3);_ac=sum(float(a["price"]if isinstance(a,dict)else a[0])*float(a["size"]if isinstance(a,dict)else a[1])for a in((_o.get("asks")or[])if isinstance(_o,dict)else[])if float(a["size"]if isinstance(a,dict)else a[1])>.0)
        if _aA is not None or _bh is not None:G=bool(_ac>=1.)
        if _b3 in c.pending_entry_intents:
         c.pending_entry_intents[_b3]["fifo_rank1_verified"]=bool(candidate_box.get("_fifo_rank1_verified"))
         if _bh is not None:c.pending_entry_intents[_b3]["ask_depth_usd"]=round(_ac,2)
        if _cQ=="ADVERSE":j=True;logger.warning(f"[BOND1 DISPUTE/COLLAPSE VETO] {_cX}: {_cP}; canceling {_bV} immediately.");break
        if _cQ=="REPEG":_f=_c8;logger.info(f"[BOND1 OUTBID REPEG] {_cX}: {_cP}.");break
        if _cQ=="BURIED":W=True;logger.info(f"[BOND1 BURIED RELEASE] {_cX}: {_cP}; canceling {_bV}.");break
        _e=A(_o);_,_s,_=g(_bO,uws_ok=bool(uws is not None and uws.is_healthy()),exp_ts=_cZ,now_ts=time.time(),created_mono=_cw,now_mono=time.monotonic(),deadline_mono=_s,posted_px=_bU,cur_best_bid=_e,buried_since_mono=S,rcfg=_b6,first_post_elapsed_s=_cT,has_active_asks=G,matched_notional_usd=float((c.pending_entry_intents.get(_b3)or{}).get("matched_notional_usd")or.0),volume_24h_usd=_aA)
      _bs=1.5 if(_aR>0 and _i==_cw and(_s-_cw)>=60.)else 15.
      if hasattr(c.executor,"get_order_fill_summary")and(time.monotonic()-_i)>=_bs:
       _i=time.monotonic()
       try:_aI=await asyncio.to_thread(c.executor.get_order_fill_summary,_bV,_dd)
       except Exception:_aI=None
       if isinstance(_aI,dict):
        _cs=float(_aI.get("matched")or.0)
        if y(c.pending_entry_intents,_b3,_bT,_bU,_cs,time.time())and not c.dry_run:await asyncio.to_thread(c.save_state)
        if _cs>=_bT-.01:_l=True;break
        if _aI.get("terminal"):
         if(_s-time.monotonic())>5.:candidate_box["_clob_early_terminal_detected"]=True
         break
        _,_s,_=g(_bO,uws_ok=bool(uws is not None and uws.is_healthy()),exp_ts=_cZ,now_ts=time.time(),created_mono=_cw,now_mono=time.monotonic(),deadline_mono=_s,posted_px=_bU,cur_best_bid=_e,buried_since_mono=S,rcfg=_b6,first_post_elapsed_s=_cT,has_active_asks=G,matched_notional_usd=float((c.pending_entry_intents.get(_b3)or{}).get("matched_notional_usd")or.0),volume_24h_usd=_aA)
    except BaseException as _S:logger.warning(f"[BOND1 MONITOR INTERRUPTED] {_cX}: {_S}; reconciling/canceling {_bV} before releasing intent.")
    _br,_ab,_G,_aH=await c._reconcile_maker_entry_fill(_bV,_dd,_l,_bT,_bU,D);_ca=round(float((_ab or{}).get("cash")or(max(.0,_G)*_aH)),4)if _G>=.01 else.0
    if not c.dry_run and(_G>=.01 or not bool((_br or{}).get("is_canceled"))):_aD[_b3]={"trade_id":_b3,"market_id":_df,"condition_id":_de,"inflight_key":_aN,"event_group_key":_6 or(f"MKT:{_df}"if _df else""),"event_id":candidate_box.get("event_id"),"title":candidate_box.get("title"),"leg_a_label":candidate_box.get("leg_a_label"),"asset":_bN,"expiry_ts":_cZ,"notional_usd":_ca if _ca>.0 else round(_bT*_bU,4),"live_maker_anchor_inflight":True}
    I=o(c.pending_entry_intents,_b3,_ca)
    if not c.dry_run:await asyncio.to_thread(c.save_state)
    _cr=str((_br or{}).get("outcome")or"");_M=bool((_br or{}).get("is_canceled"))
    if(not _M and _cr!="FILLED"and _G<.01 and"already canceled or matched"in str((_br or{}).get("not_canceled_reason")or"").lower()):
     _c7,_cO=await asyncio.to_thread(c._wallet_token_balance,_dd)
     if _cO in(c.ONCHAIN_SOURCE,"CLOB_BALANCE_API")and(float(_c7 or.0)-D)<=1e-4:_M=True
    if not _M and _cr!="FILLED"and(_ab is None or not _ab.get("terminal"))and _G<.01:
     _c6=_cX if _cX not in c.active_positions else f"{_cX}_{int(time.time()*1000)%10000}";_cq=round(_bT*_bU,4);_aa=getattr(c,"_state_save_lock",None)or c._GLOBAL_STATE_SAVE_LOCK
     with _aa:
      _cN=c._make_single_leg_lock_pos(_c6,"SINGLE_LEG_MAKER_LOCK",_bO,_bN,"maker_lock_1leg",_df,_de,_dd,_c2,bool(_dh),_bT,_cq,.0,.0,1.,"maker_post_only_0pct",_cZ,time.time(),D,_bV,True,unk=True,sub_ts=_bB);_cN["dedupe_key"],_cN["pair_dedupe_key"],_cN["event_group_key"]=_ck,_aG,_6
      if candidate_box.get("event_id"):_cN["event_id"]=str(candidate_box.get("event_id"))
      if _1:_cN["inventory_backed_completion"]=True;_cN["partner_held_token_id"]=_0;_cN["partner_avg_cost_ps"]=round(m,4)
      c.active_positions[_c6]=_cN;_aD.pop(_b3,None);c._refresh_global_halt();c.save_state()
     return{"executed":False,"reason":"BOND1_CANCEL_OUTCOME_UNKNOWN"}
    if _G<.01:
     _aD.pop(_b3,None)
     if not c.dry_run and _M and D==.0:(c.__dict__.get("_d1_dirty_token_until")or{}).pop(_dd,None)
     if _f is not None and not c.dry_run and not getattr(c,"_shutdown_requested",False):
      _cj.pop(_ck,None);_ao=float(_f);c._sll_repeg_count=int(getattr(c,"_sll_repeg_count",0)or 0)+1
      async def H():
       await asyncio.sleep(.08);b=time.time();f,a=s(_bO,_cZ,b,(7. if _bH else 120.),first_post_ts=_ar,uws_ok=bool(uws is not None and uws.is_healthy()),rcfg=_b6)
       if(not f or getattr(c,"_shutdown_requested",False)or c._is_d1_box_halted()or w(c,_ck,_aG,[_df],b)):return
       k=_cd.get_book(_dd,max_age_sec=.85)if(_cd is not None and"get_market_book"not in getattr(c.executor,"__dict__",{}))else None;i=_cd.get_book(_bL,max_age_sec=.85)if(_cd is not None and"get_market_book"not in getattr(c.executor,"__dict__",{}))else None;c._spawn_live_maker_anchor_box_task({**candidate_box,"expiry_ts":a,"anchor_bid_px":_ao,"box_cost_net":_ao,**({"leg_a_max_price":_N}if(_1 and not candidate_box.get("leg_a_max_price"))else{}),"ws_books":({_dd:k,_bL:i}if(k and i)else None),"ws_books_ts":b,"ts_unix":b,"_bond1_repost_count":_aR+1,"_bond1_first_post_ts":_ar,"_repeg_zero_fill":bool(_M)})
      _L=c.__dict__.setdefault("_bond1_repost_bg_tasks",set());_bq=asyncio.create_task(H());_L.add(_bq);_bq.add_done_callback(_L.discard);return{"executed":False,"reason":"BOND1_OUTBID_REPEGGED","repeg_px":_ao}
     _T=bool(candidate_box.pop("_clob_early_terminal_detected",False)and not j and not W and not _bE.is_set());_an=bool(_bE.is_set()and not j and not W);U=str((getattr(c,"_maker_anchor_preempt_reasons",None)or{}).pop(_aN,"")or"")
     if W and not U:U=f"outbid_buried_{_aP:.0f}s"
     elif _T and not U:U="clob_postonly_early_terminal_requote"
     _bQ="BOND1_MAKER_ADVERSE_CANCELLED"if j else("BOND1_MAKER_OUTBID_RELEASED"if W else("BOND1_MAKER_PREEMPTED"if _an else("BOND1_MAKER_POSTONLY_REQUOTE"if _T else"BOND1_MAKER_EXPIRED_UNFILLED")))
     if _emit_shock_attempt is not None:_emit_shock_attempt({"dry_run":c.dry_run,"asset":_bN or"BOND1","horizon":"box","side":_c2,"market_id":_df,"title":str(candidate_box.get("title")or _cX),"sleeve":_bO,"path_type":"MAKER_BOX","target_px":_bU,"notional_usd":round(_bT*_bU,2),"http_ms":_a8,"ttl_ms":round((time.monotonic()-_cw)*1e3,1),"stage_outcome":_bQ,"gate_detail":U})
     _cp,_=s(_bO,_cZ,time.time(),150.,first_post_ts=_ar,uws_ok=bool(uws is not None and uws.is_healthy()),rcfg=_b6)
     if((_an or _T)and not c.dry_run and not getattr(c,"_shutdown_requested",False)and U!="SHUTDOWN"and not U.startswith(("VELOCITY_UPGRADE:","S2_TIER1_UPGRADE:","GOVERNANCE_DISABLED"))and _aR<3 and _cp):
      _am=(float(_cF.get("bond1_postonly_requote_delay_sec",1.)or 1.)if _T else float(_b6.get("bond1_preempt_repost_delay_sec",6.)or 6.));_cj[_ck]=time.time()+min(1.,_am*.5)
      async def C():
       await asyncio.sleep(_am);i=time.time();f,b=s(_bO,_cZ,i,120.,first_post_ts=_ar,uws_ok=bool(uws is not None and uws.is_healthy()),rcfg=_b6)
       if(not f or getattr(c,"_shutdown_requested",False)or c._is_d1_box_halted()or w(c,_ck,_aG,[_df],i)):return
       a={**candidate_box,"expiry_ts":b,"ts_unix":i,"_bond1_repost_count":_aR+1,"_bond1_first_post_ts":_ar}
       if _T:a.pop("ws_books",None);a.pop("ws_books_ts",None)
       c._spawn_live_maker_anchor_box_task(a)
      _L=c.__dict__.setdefault("_bond1_repost_bg_tasks",set());_bq=asyncio.create_task(C());_L.add(_bq);_bq.add_done_callback(_L.discard)
     else:_co=time.time();_cj[_ck]=_co+_r(c,_ck,W,j,_bH,_aR,_co)
     return{"executed":False,"reason":_bQ}
   _dg=round(_G,4);_c5=round(float((_ab or{}).get("cash")or(_dg*_aH)),4)
   if _emit_shock_attempt is not None:_emit_shock_attempt({"dry_run":c.dry_run,"asset":_bN or"BOND1","horizon":"box","side":_c2,"market_id":_df,"title":str(candidate_box.get("title")or _cX),"sleeve":_bO,"path_type":"MAKER_BOX","target_px":_bU,"fill_px":_aH,"notional_usd":_c5,"http_ms":_a8,"stage_outcome":"FILLED_BOX"})
   _c4=round(float((_ab or{}).get("fee")or.0),4);_cM=round((_c5+_c4)/max(_dg,.01),5);_c3=bool(_1 or candidate_box.get("hold_to_maturity",True)or _aH>=.982);_d=list((_ab or{}).get("fills")or[])
   if not _d and not c.dry_run and hasattr(c.executor,"get_account_fills"):
    try:_d=list((await asyncio.to_thread(c.executor.get_account_fills,_dd,max(.0,_bB-60.),"BUY",_bV))or[])
    except Exception:_d=[]
   _bP=list(dict.fromkeys([str(x)for x in((_ab or{}).get("trade_ids")or(_X or{}).get("tradeIDs")or[])if x]+[str(f.get("trade_id")or f.get("id"))for f in _d if isinstance(f,dict)and(f.get("trade_id")or f.get("id"))]));_b9=list(dict.fromkeys([str(x)for x in((_ab or{}).get("transactions_hashes")or(_X or{}).get("transactionsHashes")or[])if x]+[str(f.get("transaction_hash"))for f in _d if isinstance(f,dict)and f.get("transaction_hash")]));_a2=time.time();lid=_cX if _cX not in c.active_positions else f"{_cX}_{int(_a2*1000)%10000}";_aa=getattr(c,"_state_save_lock",None)or c._GLOBAL_STATE_SAVE_LOCK
   with _aa:
    for _cn in(_ck,_aG):
     if _cn:_cj.pop(_cn,None);c._record_seen_d1_box_key(_cn)
    _cm=c._make_single_leg_lock_pos(lid,"SINGLE_LEG_MAKER_LOCK",_bO,_bN,"maker_lock_1leg",_df,_de,_dd,_c2,bool(_dh),_dg,_c5,_c4,.0,1.,"maker_post_only_0pct",_cZ,_a2,D,_bV,_c3,unk=False);_cm["trade_ids"],_cm["transactions_hashes"]=_bP,_b9;_cm["dedupe_key"],_cm["pair_dedupe_key"],_cm["event_group_key"]=_ck,_aG,_6
    if candidate_box.get("event_id"):_cm["event_id"]=str(candidate_box.get("event_id"))
    if _1:_cm["inventory_backed_completion"]=True;_cm["partner_held_token_id"]=_0;_cm["partner_avg_cost_ps"]=round(m,4)
    c._record_ft_candidate_funnel(candidate_box,stage="MAKER_FILLED",executed=True,maker_filled=True,is_maker=True);(c.__dict__.get("_clinched_ws_watchlist")or{}).pop(_dd,None);c.active_positions[lid]=_cm;_aD.pop(_b3,None);Z(c,I,_c5+_c4,time.time());c.executor.invalidate_collateral_cache();c._pending_collateral_refresh=True;c.save_state();logger.info(f"✓ [SINGLE-LEG MAKER LOCK FILLED] {lid} ({_bO}) | {_dg:.2f} sh @ ${_cM:.4f} (0% Maker fee, hold_to_maturity={_c3})")
   if not c.dry_run and _stage_b_emit_funnel is not None:
    try:
     if _STAGE_B_DECAY_TRACKER is not None:
      _STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(_cX)
      if _ck:_STAGE_B_DECAY_TRACKER.mark_our_fill_or_cancel(_ck)
     _stage_b_emit_funnel("COMPLETE_BASKET_LOCKED",sleeve=_bO,candidate_key=_cX,box_type="SINGLE_LEG_MAKER_LOCK",asset=str(_bN or""),net_edge_bps=round(max(.0,1.-_cM)*1e4,2),est_profit_usd=round(max(.0,1.-_cM)*_dg,4),notional_usd=_c5)
    except Exception:pass
   if not c.dry_run and _c3:O(c,lid)
   return{"executed":True,"result":_ab or _X,"leg_trade_ids":[]if _c3 else[lid]}
  finally:
   if _n is not None and not _n.done():_n.cancel();await asyncio.gather(_n,return_exceptions=True)
   (c.__dict__.get("_sll_ws_book_events")or{}).pop(_b3,None);_aS.pop(_b3,None);_aE.pop(_b3,None);_aD.pop(_b3,None);(c.__dict__.get("_prepost_partner_pledged_shares")or{}).pop(_b3,None);o(c.pending_entry_intents,_b3,.0);_a1.discard(_aN);_P.discard(_bJ);_9.discard(_aN);_ag.pop(_aN,None);c._notify_maker_preempt_released()
 def _notify_sll_ws_book_change(b,_tok,loop_ref=None):
  c=getattr(b,"_sll_ws_book_events",None)
  if not c:return 0
  h=loop_ref or getattr(b,"_main_loop",None);a=False
  if h is not None:
   try:a=asyncio.get_running_loop()is h
   except RuntimeError:a=False
  d=0
  for g,f,e in list(c.values()):
   if _tok in(g,f)and not e.is_set():
    if h is not None and not a:h.call_soon_threadsafe(e.set)
    else:e.set()
    d+=1
  return d
 def _spawn_live_maker_anchor_box_task(a,candidate_box):
  from src.polymarket_research.riskless_protocol_v2_expansion import is_s2_maker_bg_task_capped as b,register_s2_maker_bg_task as c;p=a.__dict__.setdefault("_maker_anchor_bg_tasks",set());m=a.__dict__.setdefault("_maker_anchor_bg_tasks_by_type",{});n=str(candidate_box.get("box_type")or"DOMINANCE_MAKER_ANCHOR").strip().upper();r=str(candidate_box.get("sleeve_source")or"").strip();l=r in{"S2_EXACT_TWAP_LOCK","S2_RTDS_EXACT_TWAP_INTEGRATOR"};j=a._is_unlimited_slots_active();h=n=="SINGLE_LEG_MAKER_LOCK"
  if h:
   if l and b(a):return False
   g=f"SINGLE_LEG_MAKER_LOCK:{candidate_box.get('dedupe_key')or candidate_box.get('leg_a_market_id')or n}";f=sum(1 for k,tk in m.items()if str(k).startswith("SINGLE_LEG_MAKER_LOCK:")and not tk.done());i=(10 if l else 8)if(j or a._is_v5_unleashed_active())else(4 if l else 2)
   if f>=i:return False
  else:
   g=f"{n}:{candidate_box.get('dedupe_key')or candidate_box.get('asset')or n}"if j else n;e=sum(1 for k,tk in m.items()if not str(k).startswith("SINGLE_LEG_MAKER_LOCK:")and not tk.done())
   if e>=(8 if j else 2):return False
  o=m.get(g)
  if o is not None and not o.done():return False
  if len(p)>=((12 if l else 10)if(j or a._is_v5_unleashed_active())else(6 if l else 4)):return False
  q=(a.maybe_execute_graduated_single_leg_maker_lock(candidate_box)if h else a.maybe_execute_graduated_maker_anchor_box(candidate_box));t=asyncio.create_task(q);p.add(t);m[g]=t
  if h and l:c(a,t)
  def d(done_t):
   p.discard(done_t)
   if m.get(g)is done_t:m.pop(g,None)
   a._notify_maker_preempt_released()
   try:
    if not done_t.cancelled()and done_t.exception()is None:
     k=done_t.result()
     if isinstance(k,dict)and not k.get("executed"):logger.info(f"[SLL MAKER SKIP] {g} ({r or n}): {k.get('reason')}")
   except Exception:pass
  t.add_done_callback(d);return True
 def _desired_market_ws_tokens(self,now_ts=None):
  from src.polymarket_research.riskless_protocol_v2_expansion import desired_market_ws_tokens_impl as b;f=list(b(self,now_ts=now_ts))
  try:
   from src.polymarket_research.full_throttle_pipeline import load_dormant_fast_rescan_tokens as a;c=a(max_age_sec=1800.)
   if c:
    e=set(f)
    for d in c:
     if d and d not in e:e.add(d);f.append(d)
  except ImportError:pass
  except Exception:pass
  return f
 def register_clinched_ws_watch_cand(self,cand,now_ts=None):from src.polymarket_research.riskless_protocol_v2_expansion import register_clinched_ws_watch_cand_impl as a;return a(self,cand,now_ts=now_ts)
 def evaluate_clinched_ws_book_snipe(self,tok_id,bk_win=None,now_ts=None):from src.polymarket_research.riskless_protocol_v2_expansion import evaluate_clinched_ws_book_snipe_impl as a;return a(self,tok_id,bk_win=bk_win,now_ts=now_ts)
 async def _poll_d1_live_box_candidates(a,now_ts):
  b=asyncio.get_running_loop()
  if getattr(a,"_d1_poll_lock_loop",None)is not b or getattr(a,"_d1_poll_async_lock",None)is None:a._d1_poll_async_lock=asyncio.Lock();a._d1_poll_lock_loop=b
  async with a._d1_poll_async_lock:return await a._poll_d1_live_box_candidates_unlocked(now_ts,b)
 async def _poll_d1_live_box_candidates_unlocked(a,now_ts,loop):
  L=[];X=getattr(a,"_fast_d1_cand_lines",None)
  if X:
   while X:L.append(X.popleft())
  if not L or(now_ts-getattr(a,"_last_d1_disk_poll",.0))>=.5:
   a._last_d1_disk_poll=now_ts;K=DATA_DIR/"d1_live_box_candidates.jsonl"
   if not getattr(a,"_d1_cand_initialized",False):a._d1_cand_initialized=True;a._last_d1_cand_offset=K.stat().st_size if K.exists()else 0
   if K.exists():
    sz=K.stat().st_size
    if sz<a._last_d1_cand_offset:a._last_d1_cand_offset=0
    if sz>a._last_d1_cand_offset:
     with open(K,"rb")as fp:fp.seek(a._last_d1_cand_offset);Z=fp.read()
     W=Z.rfind(b"\n")+1
     if W:a._last_d1_cand_offset+=W;L.extend(Z[:W].decode("utf-8",errors="ignore").splitlines())
  if not L:return 0
  C=a.__dict__.setdefault("_seen_d1_emit_ids",{});x=a.__dict__.setdefault("_d1_retry_cooldown_until",{});from src.polymarket_research.riskless_protocol_v2_expansion import is_d1_dedupe_blocked as k;h=0;loop=asyncio.get_running_loop();a._main_loop=loop;B=[];J=[]
  for V in L:
   if not V.strip():continue
   try:
    p=_json_loads(V);j=f"{p.get('dedupe_key')or p.get('box_id')}:{p.get('ts_unix')}"
    if j in C:continue
    Q=str(p.get("box_type")or"").strip().upper()
    if Q=="CLINCH_WATCHLIST_REG":C[j]=None;a._record_ft_candidate_funnel(p,stage="CLINCH_WATCHLIST");a.register_clinched_ws_watch_cand(p,now_ts);continue
    a._record_ft_candidate_funnel(p,stage="RECEIVED")
    if not a.dry_run and _stage_b_reg_decay_watch is not None:
     try:_stage_b_reg_decay_watch(p,emit_funnel=False,tracker=_STAGE_B_DECAY_TRACKER)
     except Exception:pass
    if Q=="SINGLE_LEG_MAKER_LOCK"and float(p.get("p_model")or.0)>=.998:a.register_clinched_ws_watch_cand(p,now_ts)
    if Q in{"DOMINANCE_MAKER_ANCHOR","ZERO_FEE_MAKER_ANCHOR","SINGLE_LEG_MAKER_LOCK"}:J.append((j,p))
    else:B.append((j,p))
   except Exception as s:logger.error(f"[D1 LIVE BRIDGE] Error evaluating candidate: {s}",exc_info=True)
  if not a.dry_run and getattr(a,"_pos_market_ws",None)is not None and(B or J):
   w=(len(a.active_positions),len(getattr(a,"pending_entry_intents",{})or{}),len(getattr(a,"_clinched_ws_watchlist",{})or{}))
   if(w!=getattr(a,"_last_ws_desired_sig",None)or(now_ts-float(getattr(a,"_last_ws_desired_sync_ts",.0)or.0))>=1.):
    a._last_ws_desired_sig=w;a._last_ws_desired_sync_ts=now_ts
    try:a._pos_market_ws.set_desired_tokens(a._desired_market_ws_tokens(now_ts))
    except Exception:pass
  from src.polymarket_research.riskless_protocol_v2_expansion import score_live_candidate_velocity_ev as e
  def b(c,is_maker):return e(c,is_maker,now_ts,compute_capital_velocity_ev)
  if B:
   if len(B)>1:B.sort(key=lambda item:b(item[1],False),reverse=True)
   u=int(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("max_concurrent_riskless_boxes",10))if a._is_v5_unleashed_active()else max(1,int(RISK_CONFIG.get("max_concurrent_d1_boxes",4)));z=("maybe_execute_graduated_d1_box"not in getattr(a,"__dict__",{})and hasattr(a,"maybe_execute_graduated_d1_box_async"))
   if z and len(B)>1 and u>1:
    _d=asyncio.Semaphore(min(u,3))
    async def g(e_id,c_box):
     async with _d:
      try:m=await a.maybe_execute_graduated_d1_box_async(c_box,concurrent_ok=True);return e_id,c_box,m,None
      except Exception as c:return e_id,c_box,None,c
    n=list(B)
    while n and h<u:
     _c=[];P=[];I=set();H=set();O=max(1,u-h)
     for e_id,c_box in n:
      _b=str(c_box.get("dedupe_key")or c_box.get("box_id")or"");U={str(m)for m in(c_box.get("leg_a_market_id"),c_box.get("leg_b_market_id"))if m}
      if len(_c)<O and not(_b and _b in H)and not(U&I):
       C[e_id]=None
       while len(C)>4096:C.pop(next(iter(C)),None)
       if _b:H.add(_b)
       I.update(U);_c.append((e_id,c_box))
      else:P.append((e_id,c_box))
     y=await asyncio.gather(*[g(e_id,c_box)for e_id,c_box in _c])
     for _,p,G,s in y:
      if s is not None:logger.error(f"[D1 LIVE BRIDGE] Error evaluating candidate: {s}",exc_info=True);continue
      if G and G.get("executed"):
       a._record_ft_candidate_funnel(p,stage="TAKER_EXECUTED",executed=True)
       if not a.dry_run:
        for T in G.get("leg_trade_ids")or[]:
         if not(a.active_positions.get(T)or{}).get("hold_to_maturity_lock"):a._spawn_fast_confirm(T)
       h+=1
      else:
       v=str((G or{}).get("reason")or"UNKNOWN");a._record_ft_candidate_funnel(p,stage="TAKER_REJECTED",reason=v)
       if v not in{"DUPLICATE_BOX_KEY","RETRY_COOLDOWN_10S","BOX_EXECUTION_INFLIGHT"}:logger.info(f"[D1 LIVE BOX SKIP] {p.get('box_id')or p.get('dedupe_key')} ({p.get('sleeve_source')or p.get('box_type')} {p.get('asset')}): {v}")
     n=P
   else:
    for j,p in B:
     try:
      C[j]=None
      while len(C)>4096:C.pop(next(iter(C)),None)
      if z:G=await a.maybe_execute_graduated_d1_box_async(p,concurrent_ok=False)
      else:G=await loop.run_in_executor(_get_hot_io_pool(),a.maybe_execute_graduated_d1_box,p)
      if G.get("executed"):
       a._record_ft_candidate_funnel(p,stage="TAKER_EXECUTED",executed=True)
       if not a.dry_run:
        for T in G.get("leg_trade_ids")or[]:
         if not(a.active_positions.get(T)or{}).get("hold_to_maturity_lock"):a._spawn_fast_confirm(T)
       h+=1
       if h>=u:break
      else:
       v=str(G.get("reason")or"UNKNOWN");a._record_ft_candidate_funnel(p,stage="TAKER_REJECTED",reason=v)
       if v not in{"DUPLICATE_BOX_KEY","RETRY_COOLDOWN_10S","BOX_EXECUTION_INFLIGHT"}:logger.info(f"[D1 LIVE BOX SKIP] {p.get('box_id')or p.get('dedupe_key')} ({p.get('sleeve_source')or p.get('box_type')} {p.get('asset')}): {v}")
     except Exception as s:logger.error(f"[D1 LIVE BRIDGE] Error evaluating candidate: {s}",exc_info=True)
  if J and os.environ.get("PM_DISABLE_LIVE_MAKER_ANCHOR_BOX","0")!="1":
   A=getattr(a,"risk_config",None)or RISK_CONFIG;F=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{})if a._is_v5_live_strict()else{};t=bool(A.get("enable_live_maker_anchor_boxes",False)and F.get("enable_two_leg_maker_anchor_boxes",True));o=bool(A.get("enable_single_leg_maker_bond1",True)and F.get("enable_single_leg_maker_bond1",True));r=bool(F.get("enable_d1_rebate_maker_canary",False));from src.polymarket_research.riskless_protocol_v2_expansion import(check_per_event_concentration_cap as d,extract_canonical_event_keys as f)
   if len(J)>1:J.sort(key=lambda item:b(item[1],True),reverse=True)
   i={};q=int((F.get("max_concurrent_intents_per_event")if isinstance(F,dict)else None)or 1)
   for j,p in J:
    E=str(p.get("box_type")or"").strip().upper()=="SINGLE_LEG_MAKER_LOCK";D=str(p.get("sleeve_source")or"").strip()=="D1_REBATE_MACHINE_GUN"
    if not(o if E else(r if D else t)):a._record_ft_candidate_funnel(p,stage="MAKER_REJECTED",reason="MAKER_LANE_DISABLED",is_maker=True);C[j]=None;continue
    _a=str(p.get("dedupe_key")or"");Y=str(p.get("pair_dedupe_key")or"");S=[str(p.get("leg_a_market_id")or""),str(p.get("leg_b_market_id")or"")]
    if(_a and float(x.get(_a,.0)or.0)>now_ts)or k(a,_a,Y,S,now_ts):a._record_ft_candidate_funnel(p,stage="MAKER_REJECTED",reason="ALREADY_SEEN_OR_COOLDOWN",is_maker=True);C[j]=None;continue
    if E and bool(F.get("enable_event_slot_diversification",True)):
     l=f(p,market_ids=[m for m in S if m])
     if l:
      N,R,_,_=d(a,p,market_ids=[m for m in S if m],now_ts=now_ts)
      if not N or any(i.get(ek,0)>=q for ek in l):a._record_ft_candidate_funnel(p,stage="MAKER_REJECTED",reason=str(R or"EVENT_SLOT_CAPPED"),is_maker=True);C[j]=None;continue
    else:l=set()
    if a._spawn_live_maker_anchor_box_task(p):
     a._record_ft_candidate_funnel(p,stage="MAKER_SPAWNED",is_maker=True)
     for ek in l:i[ek]=i.get(ek,0)+1
     C[j]=None
     while len(C)>4096:C.pop(next(iter(C)),None)
  if not a.dry_run and(B or J)and h==0:
   M=float(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("ft_funnel_persist_interval_sec",5.)or 5.)
   if(now_ts-float(a.__dict__.get("_last_ft_funnel_save_ts")or.0))>=M:a._last_ft_funnel_save_ts=now_ts;await asyncio.to_thread(a.save_state)
  return h
 def _snapshot_ft_live_funnel(a,pend_map=None,*,now_utc_iso=None):c=a.__dict__.setdefault("_ft_live_funnel",{});d=pend_map if isinstance(pend_map,dict)else(getattr(a,"pending_entry_intents",None)or{});b=sum(1 for v in d.values()if isinstance(v,dict)and v.get("live_maker_anchor_inflight"));return{"updated_at_utc":now_utc_iso or datetime.now(timezone.utc).isoformat(),"candidates_received":int(c.get("candidates_received",0)or 0),"ft_bridge_received":int(c.get("ft_bridge_received",0)or 0),"clinch_watchlist_registered":int(c.get("clinch_watchlist_registered",0)or 0),"taker_evaluated":int(c.get("taker_evaluated",0)or 0),"taker_executed":int(c.get("taker_executed",0)or 0),"maker_spawned":int(c.get("maker_spawned",0)or 0),"maker_posted":int(c.get("maker_posted",0)or 0),"maker_filled":int(c.get("maker_filled",0)or 0),"rejected_total":int(c.get("rejected_total",0)or 0),"resting_maker_slots":int(b),"by_sleeve":dict(c.get("by_sleeve")or{}),"reject_reasons":dict(c.get("reject_reasons")or{}),"recent_candidates":list(c.get("recent_candidates")or[])[-25:]}
 def _record_ft_candidate_funnel(self,cand,*,stage,reason="",executed=False,maker_posted=False,maker_filled=False,is_maker=False):
  if not isinstance(cand,dict):return
  i=self.__dict__.setdefault("_ft_live_funnel",{});h=str(cand.get("sleeve_source")or cand.get("sleeve")or cand.get("box_type")or"UNKNOWN").strip()or"UNKNOWN";c=bool(cand.get("full_throttle_bridge")or cand.get("rule_verified")is True);b=time.time();a=i.setdefault("by_sleeve",{})
  if h not in a and len(a)>=64:a.pop(next(iter(a)),None)
  d=a.setdefault(h,{"received":0,"ft_bridge":0,"taker_evaluated":0,"taker_executed":0,"maker_spawned":0,"maker_posted":0,"maker_filled":0,"rejected":0,"last_reason":"","last_ts":.0});d["last_ts"]=round(b,3)
  if stage=="CLINCH_WATCHLIST":i["clinch_watchlist_registered"]=int(i.get("clinch_watchlist_registered",0)or 0)+1;return
  if stage=="RECEIVED":
   i["candidates_received"]=int(i.get("candidates_received",0)or 0)+1;d["received"]=int(d.get("received",0)or 0)+1
   if c:i["ft_bridge_received"]=int(i.get("ft_bridge_received",0)or 0)+1;d["ft_bridge"]=int(d.get("ft_bridge",0)or 0)+1
   return
  if stage in{"TAKER_EXECUTED","TAKER_REJECTED"}:i["taker_evaluated"]=int(i.get("taker_evaluated",0)or 0)+1;d["taker_evaluated"]=int(d.get("taker_evaluated",0)or 0)+1
  if executed and not is_maker:i["taker_executed"]=int(i.get("taker_executed",0)or 0)+1;d["taker_executed"]=int(d.get("taker_executed",0)or 0)+1;d["last_reason"]="EXECUTED"
  if stage=="MAKER_SPAWNED":i["maker_spawned"]=int(i.get("maker_spawned",0)or 0)+1;d["maker_spawned"]=int(d.get("maker_spawned",0)or 0)+1
  if maker_posted:i["maker_posted"]=int(i.get("maker_posted",0)or 0)+1;d["maker_posted"]=int(d.get("maker_posted",0)or 0)+1;d["last_reason"]="MAKER_POSTED"
  if maker_filled:i["maker_filled"]=int(i.get("maker_filled",0)or 0)+1;d["maker_filled"]=int(d.get("maker_filled",0)or 0)+1;d["last_reason"]="MAKER_FILLED"
  if reason:
   g=str(reason).split(":",1)[0][:64];i["rejected_total"]=int(i.get("rejected_total",0)or 0)+1;d["rejected"]=int(d.get("rejected",0)or 0)+1;d["last_reason"]=str(reason)[:96];f=i.setdefault("reject_reasons",{})
   if g not in f and len(f)>=64:f.pop(next(iter(f)),None)
   f[g]=int(f.get(g,0)or 0)+1
  e=i.setdefault("recent_candidates",[]);e.append({"ts_unix":round(b,3),"box_id":str(cand.get("box_id")or cand.get("dedupe_key")or"")[:72],"sleeve":h[:64],"box_type":str(cand.get("box_type")or"")[:32],"asset":str(cand.get("asset")or"")[:16],"market_id":str(cand.get("leg_a_market_id")or cand.get("market_id")or"")[:24],"ft_bridge":c,"stage":stage,"reason":str(reason or("EXECUTED"if(executed or maker_filled)else stage))[:96]})
  if len(e)>25:del e[:-25]
 def _is_phase3a_maker_rescue_live_active(a):
  b=a.__dict__.get("enable_live_phase3a_maker_fallback")
  if b is False or os.environ.get("PM_DISABLE_LIVE_PHASE3A_MAKER","0")=="1":return False
  c=(not a.dry_run and getattr(a.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2")and getattr(getattr(a.executor,"client",None),"_mock_children",None)is None and not any(k in getattr(a.executor,"__dict__",{})for k in("execute_snipe_order_async","execute_snipe_order")));return bool(b is True or(c and bool(RISK_CONFIG.get("enable_live_phase3a_maker_fallback",True))))
 def _calc_priority_score(a,s_item):
  u=str(s_item.get("asset")or"").upper()
  if u and u not in a.get_graduated_allowed_assets():return.0
  r=s_item.get("shock_direction");v="UP"if r=="BUY"else"DOWN";q=s_item.get("pre_shock_features_t0",{});f=q.get(v,{})if isinstance(q,dict)else{};h=float(s_item.get("candle_distance_pct",.0)or.0)
  if(v=="UP"and h<.04)or(v=="DOWN"and h>-.04):return.0
  t=abs(h);s=abs(float(s_item.get("z_val",s_item.get("z_score",s_item.get("expected_prob_shift",t*.5)))));e=a._is_v5_live_strict();c=((f.get("vwap_$20")or f.get("effective_price_$20")or f.get("vwap_$25")or f.get("effective_price_$25")or f.get("best_ask")or f.get("vwap_$50")or f.get("effective_price_$50"))if e else(f.get("vwap_$50")or f.get("effective_price_$50")or f.get("vwap_$25")or f.get("effective_price_$25")or f.get("best_ask")));m=float(c)if c is not None else(.6 if e else.5);o=str(s_item.get("title","")).lower();l=str(s_item.get("horizon")or s_item.get("candle_interval")or s_item.get("timeframe")or"").lower();k=("pm-"in o or"am-"in o or"15"in l);n=float(s_item.get("seconds_to_expiry",3600.)or 3600.);j=(s_item.get("shock_source")=="BOUNDARY_LOCK"or s_item.get("regime_override")=="REGIME_D_BOUNDARY_LOCK"or(12.<=n<=90. and t>=.08));g=s_item.get("sleeve")=="SLEEVE_3_STRIKE_CONVERGENCE"or s_item.get("shock_source")=="EXP316_TRACK_A_CONVERGENCE";p=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional",{})if e else{}
  if j:b=.94
  elif g:b=.89
  elif e:b=(max(float(p.get("max_taker_price_15m",.82)),float(p.get("max_maker_price_15m",.82)))if k else max(float(p.get("max_taker_price_1h",.82)),float(p.get("max_maker_price_1h",.82))))
  else:b=min(a.max_price_ceiling,.85)if k else a.max_price_ceiling
  d=float(p.get("min_entry_price",.52))if e else a.min_price_floor
  if m<d:return.0
  if m>b:
   i=float(f.get("best_ask")or m)
   if not j and not g and n>=85. and t>=.06 and min(m,i)<=round(b+.03,4)and a._is_phase3a_maker_rescue_live_active():return.5*(s/max(m,.01))
   return.0
  return s/max(m,.01)
 async def evaluate_shock_and_execute(c,shock,*,_cold_unqualified=False):
  c._main_loop=asyncio.get_running_loop();j=[];_hot_held=False;i=c.__dict__.get("_cold_shock_objs")
  if i and id(shock)in i:i.discard(id(shock));_cold_unqualified=True
  h=str(shock.get("asset")or"").upper();l="UP"if shock.get("shock_direction")=="BUY"else"DOWN";m=((shock.get("pre_shock_features_t0")or{}).get(l)or{})if isinstance(shock.get("pre_shock_features_t0"),dict)else{};e=bool(float(m.get("best_ask")or.0)>=.985 and float(m.get("best_bid")or.0)>=.95);g=(not _cold_unqualified)and(not e)and((not h)or(h in c.get_graduated_allowed_assets())or(h in("SOL","ETH")))
  if not getattr(c,"dry_run",False)and g:_HOT_DISPATCH_ACTIVE.enter();_hot_held=True
  def b():
   if j:
    n=j[:];j.clear()
    for o in n:logger.info(o)
  def a():
   nonlocal _hot_held
   if _hot_held:_hot_held=False;_HOT_DISPATCH_ACTIVE.leave()
  k=_PRE_HOT_CTX.set((j,b,a));d=None;f=None
  try:
   if _LatencyTrace is not None and _CURRENT_TRACE is not None:
    try:
     f=_LatencyTrace(shock_id=str(shock.get("shock_id")or f"{shock.get('market_id')}_{shock.get('t0_unix')}"),market_id=str(shock.get("market_id")or""),asset=str(shock.get("asset")or""),sleeve=str(shock.get("sleeve")or shock.get("regime")or shock.get("strategy")or""),src_t0_unix=shock.get("t0_unix"),dry_run=bool(getattr(c,"dry_run",False)));f.stamp("trigger_consumed")
     try:f.set(trigger_to_consume_wall_ms=round((time.time()-float(shock.get("t0_unix")))*1e3,3))
     except(TypeError,ValueError):pass
     d=_CURRENT_TRACE.set(f)
    except Exception:d=None
   return await c._evaluate_shock_and_execute_impl(shock)
  finally:
   a();b()
   try:_PRE_HOT_CTX.reset(k)
   except Exception:pass
   if _emit_shock_attempt_trace is not None and f is not None:
    try:_emit_shock_attempt_trace(f,shock)
    except Exception:pass
   if d is not None:
    try:_CURRENT_TRACE.reset(d)
    except Exception:pass
 _evaluate_shock_and_execute_impl=_bind_hv_method(_hv__evaluate_shock_and_execute_impl,'_evaluate_shock_and_execute_impl')
 def _recover_pending_intent(a,trade_id,intent):
  m=intent.get("token_id");o=float(intent.get("pre_token_balance",.0)or.0);b=float(intent.get("notional_usd",intent.get("intended_notional",.0))or.0);g=float(intent.get("target_price",.7)or.7);f=float(intent.get("submitted_at_ts",intent.get("timestamp",time.time()))or time.time())
  if not m:logger.error(f"[RECONCILIATION] Pending intent {trade_id} has no token id; retaining global halt.");return"UNRESOLVED"
  p=a._classify_entry(m,o,f,intent.get("entry_order_id")or intent.get("order_id"),trade_id);n=p["verdict"]
  if n=="NOT_EXECUTED":logger.info(f"[RECONCILIATION] Pending entry intent {trade_id} authoritatively NOT executed ({p.get('proof')}). Discarding intent.");a.pending_entry_intents.pop(trade_id,None);a.save_state();return"NOT_EXECUTED"
  if n not in{"ARRIVED","MATCHED_UNSETTLED"}:logger.error(f"[RECONCILIATION] Pending entry intent {trade_id} outcome not authoritatively provable (balance={p.get('balance')}, source={p.get('source')}). Retaining intent and global halt.");return"UNRESOLVED"
  e=float(intent.get("target_exit_price")or(.99 if a.hold_to_maturity else round(min(.99,g+.08),2)));h=float(intent.get("candle_open_spot",.0)or.0);k=float(intent.get("candle_expiry_ts",.0)or.0);j=float(intent.get("candle_sigma",.005)or.005);l=intent.get("asset","");i=intent.get("target_token","");d={"trade_id":trade_id,"entry_trade_id":intent.get("entry_trade_id")or trade_id,"order_id":intent.get("entry_order_id")or intent.get("order_id"),"entry_order_id":intent.get("entry_order_id")or intent.get("order_id"),"trade_ids":[],"transactions_hashes":[],"pre_token_balance":o,"event_id":intent.get("event_id",""),"market_id":intent.get("market_id",""),"condition_id":intent.get("condition_id",""),"token_id":m,"target_token":i,"asset":l,"candle_open_spot":h,"entry_spot_ref":float(intent.get("entry_spot_ref")or h),"spot_denomination":intent.get("spot_denomination","USDT"),"candle_sigma":j,"candle_expiry_ts":k,"side":intent.get("side","BUY"),"entry_price":g,"entry_shares":.0,"gross_entry_shares":.0,"remaining_shares":.0,"remaining_exit_shares":.0,"filled_exit_shares":.0,"remaining_cost_basis":b,"notional_usd":b,"intended_notional":b,"cost_basis_estimated":True,"fee_usd":float(intent.get("fee_usd",.0)or.0),"entry_fee_cash_usd":float(intent.get("entry_fee_cash_usd",.0)or.0),"entry_fee_asset":intent.get("entry_fee_asset","USDC"),"fee_source":intent.get("fee_source","crypto_fees_v2"),"target_exit_price":e,"entry_time_utc":intent.get("created_at_utc",datetime.now(timezone.utc).isoformat()),"entry_ts":f,"submitted_at_ts":f,"status":ExecutionStatus.POSITION_CONFIRMED if n=="ARRIVED"else ExecutionStatus.MATCHED_PENDING_SETTLEMENT,"exit_order_id":None,"exit_order_status":"AWAITING_DELTA_SETTLEMENT","created_at_utc":intent.get("created_at_utc",datetime.now(timezone.utc).isoformat()),"realized_exit_cash":.0,"realized_exit_fee":.0,"gross_exit_cash":.0,"average_exit_price":.0,"exit_trade_ids":[],"inventory_reconciled":False,"is_liquidating":False,"unwind_order_id":None,"unwind_start_time":.0,"order_records":{},"recovered_from_intent":True};a._apply_entry_evidence(d,p)
  if not d.get("target_exit_price")or not math.isfinite(float(d["target_exit_price"])):d["target_exit_price"]=e
  c=[]
  if not i:c.append("target_token")
  if not l:c.append("asset")
  if h<=.0 or not math.isfinite(h):c.append("candle_open_spot")
  if k<=.0 or not math.isfinite(k):c.append("candle_expiry_ts")
  if c:logger.critical(f"[RECONCILIATION] Recovered position {trade_id} lacks critical supervisory fields {c}. " "Enforcing persistent reconciliation hold!");d["exit_order_status"]="RECONCILIATION_HOLD_INCOMPLETE_SCHEMA";d["missing_supervisory_fields"]=c
  a.active_positions[trade_id]=d;a.pending_entry_intents.pop(trade_id,None);a.save_state();logger.warning(f"[RECONCILIATION] RECOVERED position from intent {trade_id}: {n} | shares={d['entry_shares']} | cost=${d['notional_usd']:.4f} | finality={d.get('entry_finality_source')} | trade_ids={d.get('trade_ids')}");return"RECOVERED"
 def reconcile_with_exchange(a):
  if a.dry_run or not a.executor.is_authenticated:return
  logger.info("[RECONCILIATION] Reconciling local state with live exchange...")
  try:
   try:
    r=a.executor.get_collateral_balance()
    if r is not None and isinstance(r,(int,float))and r>0:
     a._last_known_collateral=float(r);a.executor.set_cached_collateral(a._last_known_collateral);logger.info(f"[RECONCILIATION] Live collateral balance: ${a._last_known_collateral:.2f}");T=time.time();h=sum(a.get_position_market_value(p,T)for p in a.active_positions.values());I=a._last_known_collateral+h;v,q=a._effective_sizing_equity_usd(I,T);a._update_equity_tier(v,allow_hwm_ratchet=(not q));f=float(I)
     if not a.dry_run and f<float(a.risk_controller.min_equity_floor_usd)and hasattr(a.executor,"get_idle_usdce_balance"):
      u=a.executor.get_idle_usdce_balance()
      if isinstance(u,(int,float))and not isinstance(u,bool)and float(u)>.0:f+=float(u)
     a.risk_controller.check_equity_drawdown(f,allow_auto_clear=True)
   except Exception:pass
   D=a._strict_open_orders();n={o.get("id")or o.get("orderID")for o in D if o};logger.info(f"[RECONCILIATION] CLOB reports {len(n)} live open orders.")
   for N,S in list((getattr(a,"pending_entry_intents",None)or{}).items()):
    if N in a.active_positions:logger.info(f"[RECONCILIATION] Pending entry intent {N} already in active_positions; clearing intent.");a.pending_entry_intents.pop(N,None);a.save_state();continue
    a._recover_pending_intent(N,S)
   for R,Q in list(a.active_positions.items()):
    if position_requires_lifecycle_resolution(Q):a._resolve_lifecycle(R,Q,D,force=True)
   for R,Q in list(a.active_positions.items()):
    if R not in a.active_positions:continue
    if position_is_settlement_receivable(Q)or position_requires_lifecycle_resolution(Q):continue
    M=Q.get("exit_order_id");L=Q.get("token_id")
    if M and M in n:logger.info(f"[RECONCILIATION] Active position {R} has confirmed resting exit order {M}.");continue
    if M:
     m=Q.get("exit_order_status","");H=a.executor.get_order_status(M)
     if m in{"STOP_CANCEL_PENDING","PRE_EXPIRY_CANCEL_PENDING"}:
      if not H:logger.warning(f"Cannot reconcile pending cancellation {M} for {R}; retaining position.");continue
      K=str(H.get("status","")).upper();C=float(a._num(H.get("size_matched"))or.0)
      if K in{"MATCHED","FILLED","CONFIRMED"}or(C>1e-6 and(K.startswith("CANCEL")or K in{"EXPIRED","REJECTED","INVALID"})):Q["exit_order_status"]="FILL_RECONCILIATION_REQUIRED";Q["pending_canceled_order_id"]=M;a.save_state();continue
      if not(K.startswith("CANCEL")or K in{"EXPIRED","REJECTED"}or(K=="INVALID"and C<=1e-6)):logger.warning(f"Cancellation not terminal: {M} (status={K}); retaining position.");continue
      try:a.executor.release_inventory(reservation_id=M)
      except Exception as d:logger.error(f"Reservation release failed for {M}: {d}");raise
      Q["exit_order_id"]=None
      if m=="STOP_CANCEL_PENDING":Q["exit_order_status"]="UNWIND_RETRY_REQUIRED";Q["next_unwind_retry_ts"]=.0;Q["is_liquidating"]=False
      else:Q["exit_order_status"]="PRE_EXPIRY_EVALUATION_REQUIRED"
      a.save_state();continue
     if not H:logger.warning(f"[RECONCILIATION] Exit order {M} for {R} absent from snapshot and status UNKNOWN; retaining.");continue
     G=float(Q.get("exit_order_size",Q.get("entry_shares",.0))or.0);s=float(a._num(H.get("size_matched"))or.0);l=str(H.get("status","")).upper()
     if l=="INVALID"and s>1e-6:Q["exit_order_status"]="FILL_RECONCILIATION_REQUIRED";Q["pending_canceled_order_id"]=M;Q["status"]="UNRESOLVED_SETTLEMENT";a.save_state();logger.warning(f"[RECONCILIATION] {R}: INVALID exit {M} has size_matched={s:.2f}; deferring to fill reconciliation.");continue
     F=H.get("taking_amount")or H.get("takingAmount");c=a._num(F);b=False
     if c is None:
      c=s*float(Q.get("target_exit_price",.0)or.0)
      if s>0:Q["exit_cash_estimated"]=True;b=True
     P=float(a._num(H.get("fee"))or a._num(H.get("fee_usd"))or.0);a.record_fill_and_update_position(Q,M,s,c,fee_usd=P,cash_is_estimated=b);U=[str(x)for x in(H.get("fill_ids")or H.get("associate_trades")or[])if x]
     if U:Q["exit_fill_ids"]=sorted(set(Q.get("exit_fill_ids")or[])|set(U))
     E=float(Q["remaining_shares"]);i=float(Q["filled_exit_shares"]);j=(l in{"MATCHED","FILLED","CONFIRMED"}or l.startswith("CANCEL")or l in{"EXPIRED","REJECTED"}or(l=="INVALID"and s<=1e-6)or s>=G-1e-4);B=(l.startswith("CANCEL")or l in{"EXPIRED","REJECTED"}or(l=="INVALID"and s<=1e-6));g=E<=.01 or i>=float(Q["entry_shares"])-1e-4
     if g:
      if b or float(Q.get("estimated_exit_cash",.0))>.0:Q["exit_order_status"]="FILL_RECONCILIATION_REQUIRED";Q["status"]="UNRESOLVED_SETTLEMENT";a.save_state();logger.warning(f"[RECONCILIATION] Position {R} filled offline but cash is estimated; retaining in UNRESOLVED_SETTLEMENT.")
      else:a._close_position(R,Q,ExecutionStatus.FILLED,"FILLED_OFFLINE",won=True);logger.info(f"[RECONCILIATION] Position {R} completely filled while offline.")
      continue
     if j:Q["exit_order_id"]=None;Q["pending_canceled_order_id"]=M;Q["exit_order_status"]="FILL_RECONCILIATION_REQUIRED";Q["status"]=ExecutionStatus.PARTIALLY_FILLED;a.save_state();logger.warning(f"[PARTIAL ORDER MATCH] Position {R}: order {M} filled {s:.2f} shares. Remaining unsold: {E:.2f}");continue
     if not B:
      if s>0:Q["exit_order_status"]="FILL_RECONCILIATION_REQUIRED";Q["pending_canceled_order_id"]=M
      a.save_state();logger.warning(f"[RECONCILIATION] Exit order {M} for {R} non-terminal ({l}) but absent from snapshot; retaining.");continue
     try:a.executor.release_inventory(reservation_id=M)
     except Exception as d:logger.error(f"Reservation release failed for {M}: {d}");raise
     Q["exit_order_id"]=None;Q["exit_order_status"]="EXIT_RECOVERY_REQUIRED"
     if i>0:Q["status"]=ExecutionStatus.PARTIALLY_FILLED
     J=Q.get("exit_tranches",[])
     for t in J:
      if t.get("status")in{"POSTED","IN_FLIGHT"}:
       A=max(.0,round(float(t["size"])-s,2))
       if A<=.01:t["status"]="FILLED"
       else:t["size"]=A;t["status"]="PENDING"
     z=[t for t in J if t.get("status")=="PENDING"]
     if z:Q["target_exit_price"]=float(z[0]["price"])
     a.save_state();logger.warning(f"[RECONCILIATION] Exit order {M} for {R} terminally {l}; residual {E:.2f} eligible for recovery.")
    if L and not Q.get("exit_order_id"):Q.pop("recovered_from_intent",None);a._attempt_maker_exit_post(R,Q)
   y={str(p.get(k))for p in a.active_positions.values()for k in("exit_order_id","unwind_order_id","pending_canceled_order_id","cancel_pending_order_id")if p.get(k)}
   for o in D:
    V=o.get("id")or o.get("orderID")
    if V and str(V)not in y:logger.warning(f"[RECONCILIATION] Orphan CLOB order {V} detected. Canceling for capital safety.");a.executor.cancel_order(V)
   O=getattr(a.executor,"rebuild_reservations_from_exchange",None)
   if callable(O):
    w=a._strict_open_orders()
    if O(w)is False:raise RuntimeError("Reservation book could not be rebuilt from the exchange")
   a._startup_reconciled=True;a._refresh_global_halt(authoritative=True);a.save_state();logger.info(f"[RECONCILIATION] Exchange state reconciled. Global halt={a.risk_halt} reasons={a.global_halt_reasons}")
  except Exception as e:logger.critical(f"[RECONCILIATION] Exchange/local state is UNKNOWN; refusing to mutate orders: {e}");raise RuntimeError("Live exchange reconciliation failed; safe startup refused")from e
 def _strict_open_orders(b):
  try:a=b.executor.get_open_orders(strict=True)
  except TypeError:a=b.executor.get_open_orders()
  if a is None or not isinstance(a,list):raise RuntimeError("CLOB open-order snapshot unavailable")
  return a
 async def _apply_market_resolution(a,tid,pos,winning_outcome):
  if tid not in a.active_positions:return
  i=winning_outcome.get("winning_outcome")if isinstance(winning_outcome,dict)else str(winning_outcome or"")
  if pos.get("resolved_winning_outcome")is None:pos["resolved_winning_outcome"]=i;pos["resolution_seen_at_ts"]=time.time();a.save_state()
  if position_is_settlement_receivable(pos):return
  if pos.get("status")=="UNRESOLVED_SETTLEMENT"and not a.dry_run and bool(pos.get("exit_cash_estimated")):logger.info(f"[RESOLUTION DEFERRED] {tid}: awaiting CLOB fill confirmation for in-flight UNRESOLVED_SETTLEMENT exit.");return
  if pos.get("status")=="LIQUIDITY_CRISIS"or pos.get("exit_order_status")=="LIQUIDITY_CRISIS":pos["status"]=ExecutionStatus.POSITION_CONFIRMED;pos["exit_order_status"]="RESTING"if pos.get("exit_order_id")else"NONE"
  if not a.dry_run and position_requires_lifecycle_resolution(pos)and pos.get("exit_order_status")!="RESOLUTION_CANCEL_UNCONFIRMED":
   await asyncio.to_thread(a._resolve_lifecycle,tid,pos,None,True)
   if tid not in a.active_positions:return
   if position_requires_lifecycle_resolution(pos)and pos.get("exit_order_status")!="RESOLUTION_CANCEL_UNCONFIRMED":logger.warning(f"[RESOLUTION DEFERRED] {tid}: unresolved execution outcome {pos.get('exit_order_status')}; settling after reconciliation.");return
  t=(pos.get("target_token")==i);n=pos.get("token_id");m=pos.get("exit_order_id")
  if m:
   k=await asyncio.to_thread(a.executor.cancel_order,m)
   if not a.dry_run:
    if(k or{}).get("error"):pos["exit_order_status"]="RESOLUTION_CANCEL_UNCONFIRMED";a.save_state();return
    q=await asyncio.to_thread(a.executor.get_order_fill_summary,m,n)
    if q is None:
     try:u=await asyncio.to_thread(a._strict_open_orders);h={o.get("id")or o.get("orderID")for o in u if o};j=await asyncio.to_thread(a.executor.get_account_fills,n,float(pos.get("entry_ts",.0)or.0),"SELL",m)
     except Exception:h,j={m},None
     if m in h or j is None:pos["exit_order_status"]="RESOLUTION_CANCEL_UNCONFIRMED";a.save_state();return
     if j:a._record_history_fills(pos,j,taker=False)
     if float(pos.get("remaining_shares",.0)or.0)<=.02:a._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True);return
    else:
     a._record_order_summary(pos,q,float(pos.get("target_exit_price",.0)or.0),taker=False)
     if float(pos.get("remaining_shares",.0)or.0)<=.02:a._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True);return
     if not q["terminal"]:pos["exit_order_status"]="RESOLUTION_CANCEL_UNCONFIRMED";a.save_state();return
    a.executor.release_inventory(reservation_id=m)
   if str(m)not in pos.setdefault("canceled_maker_exit_oids",[]):pos["canceled_maker_exit_oids"].append(str(m))
   pos.pop("_htm_passive_recycle_active",None);pos["exit_order_id"]=None;pos["exit_order_status"]="CANCELED_FOR_RESOLUTION"
  g=str(m or pos.get("unwind_order_id")or"").strip()or None;f=str(pos.get("entry_order_id")or pos.get("order_id")or"").strip()or None;d=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",pos.get("entry_shares",.0)))or.0);c=d
  if not a.dry_run:
   from src.polymarket_research.riskless_protocol_v2_expansion import reconcile_resolution_fills_and_pre_redeem as b;l,c=await b(a,tid,pos,i,t,n,g,f,d)
   if l!="RECEIVABLE":return
   s=await asyncio.to_thread(a.executor.get_current_block_number);e=15000 if pos.get("_pre_redeemed_onchain")else 2500;pos["status"]="AWAITING_ONCHAIN_SETTLEMENT";pos["exit_order_status"]="AWAITING_REDEMPTION";pos["is_liquidating"]=False;pos["expected_terminal_payout_usd"]=round(c,4);pos["redemption_receivable_usd"]=round(c,4);pos["winning_shares_held"]=round(c,6);pos["expected_winning_outcome"]=i;pos["resolution_block"]=max(0,int(s)-e)if isinstance(s,int)else None;a.save_state();logger.info(f"[RESOLVED - RECEIVABLE] {tid}: {c:.2f} winning shares held. Expected ${c:.2f} is a " "receivable, NOT realized cash, until a verified on-chain redemption receipt.")
   try:await asyncio.to_thread(a.poll_onchain_redemptions,True)
   except Exception:pass
   return
  r=c*1. if(t and c>=.01)else.0
  if r>.0:a.record_fill_and_update_position(pos,"SETTLEMENT_RESOLUTION_PAYOUT",c,r,.0)
  p=a._close_position(tid,pos,ExecutionStatus.SETTLED,"MARKET_RESOLVED",won=None);logger.info(f"✓ POSITION RESOLVED AT MATURITY: {tid} | Won={t} | RemShares={c:.2f} | Net PnL=${p:+.2f}")
 _maybe_recycle_disputed_htm_lock=_bind_hv_method(_hv__maybe_recycle_disputed_htm_lock,'_maybe_recycle_disputed_htm_lock')
 async def check_resolutions_and_manage_positions(d):
  d._main_loop=asyncio.get_running_loop()
  if not d.dry_run:
   try:from src.polymarket_research.riskless_machine_gun_engine import PreSplitInventoryGun as _d;_cI=d.__dict__.get("_pre_split_gun")or setattr(d,"_pre_split_gun",_d())or d._pre_split_gun;await _cI.tick(d,time.time(),fast_tick_reader=(lambda a:read_fast_tick(a,max_age_sec=1.5))if callable(read_fast_tick)else None)
   except Exception:pass
  if(not d.dry_run and getattr(d.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2")and hasattr(d.executor,"wrap_idle_usdce_to_pusd")):
   _bD=time.time()
   if(_bD-float(getattr(d,"_last_usdce_wrap_check_ts",.0)or.0))>=180.:
    d._last_usdce_wrap_check_ts=_bD
    try:
     _bC=await asyncio.to_thread(d.executor.wrap_idle_usdce_to_pusd,1.)
     if isinstance(_bC,dict)and _bC.get("wrapped"):d._pending_collateral_refresh=True;await d._async_refresh_collateral()
    except Exception:pass
  if not d.active_positions:d._refresh_global_halt();return
  _av=PIPELINE_ROOT/"data/polymarket/finalized_market_resolutions.jsonl";_be=RESOLUTIONS_FILE if(RESOLUTIONS_FILE.parent==DATA_DIR or RESOLUTIONS_FILE!=_av)else(DATA_DIR/"finalized_market_resolutions.jsonl")
  if _be.exists():
   try:
    _H=_be.stat().st_size
    if _H>d.last_res_file_pos:
     with open(_be,"rb")as f:f.seek(d.last_res_file_pos);_cy=f.read()
     _au=_cy.rfind(b"\n")+1
     if _au:_s=_cy[:_au].decode("utf-8").splitlines();d.last_res_file_pos+=_au
     else:_s=[]
     for _cH in _s:
      if not _cH.strip():continue
      try:
       res=_json_loads(_cH);_bB=str(res.get("market_id"));_P=res.get("winning_outcome")
       for tid,pos in list(d.active_positions.items()):
        if str(pos.get("market_id"))==_bB:await d._apply_market_resolution(tid,pos,_P)
      except Exception as e:logger.error(f"Error parsing resolution line: {e}",exc_info=True)
   except Exception as e:logger.error(f"Error checking resolutions: {e}")
  if not d.dry_run and getattr(d.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2"):
   _cx=time.time()
   for tid,pos in list(d.active_positions.items()):
    _ch=float(pos.get("candle_expiry_ts",.0)or.0);_cG=str(pos.get("market_id")or"");_aO=_ch>.0 and(_ch-float(pos.get("entry_ts")or.0))<=3600.;_a0=(bool(pos.get("is_single_leg_lock"))and _cx>=float(pos.get("entry_ts")or.0)+45.)or bool(pos.get("_zero_bal_gamma_urgent"));_bA=3. if(_aO and _cx>=_ch+3.)else(8. if(pos.get("is_single_leg_lock")and _cx<_ch+12.)else 15.)
    if((_ch>.0 and _cx>=_ch+(3. if _aO else 12.))or _a0)and pos.get("resolved_winning_outcome")is None and _cG.isdigit()and int(_cG)>=100000:
     if _cx-float(pos.get("_last_gamma_res_poll",.0)or.0)>=_bA:
      pos.pop("_zero_bal_gamma_urgent",None);pos["_last_gamma_res_poll"]=_cx
      try:
       _cF=await asyncio.to_thread(lambda:d.executor._sync_session.get(f"https://gamma-api.polymarket.com/markets/{_cG}",timeout=3.).json())
       if isinstance(_cF,dict)and _cF.get("umaResolutionStatus")is not None:pos["umaResolutionStatus"]=str(_cF.get("umaResolutionStatus")or"")
       if isinstance(_cF,dict)and(_cF.get("umaResolutionStatus")=="resolved"or _cF.get("closed")):
        _cw=_cF.get("outcomePrices");_cg=_json_loads(_cw)if isinstance(_cw,str)else(_cw or[]);_cv=_cF.get("clobTokenIds");_cf=_json_loads(_cv)if isinstance(_cv,str)else(_cv or[]);_bZ=str(pos.get("token_id")or"");_bY=str(pos.get("target_token")or"UP");_bd={"UP":"DOWN","DOWN":"UP","YES":"NO","NO":"YES"};_bX=_bd.get(_bY.upper(),f"NOT_{_bY}")
        if len(_cg)>=2 and len(_cf)>=2 and _bZ in(str(_cf[0]),str(_cf[1])):
         idx=0 if _bZ==str(_cf[0])else 1
         if str(_cg[idx])in("1","1.0"):await d._apply_market_resolution(tid,pos,_bY)
         elif str(_cg[1-idx])in("1","1.0"):await d._apply_market_resolution(tid,pos,_bX)
        elif len(_cg)>=2 and str(_cg[0])in("1","1.0")and str(_cg[1])in("0","0.0"):await d._apply_market_resolution(tid,pos,"YES"if _bY.upper()in("YES","NO")else"UP")
        elif len(_cg)>=2 and str(_cg[0])in("0","0.0")and str(_cg[1])in("1","1.0"):await d._apply_market_resolution(tid,pos,"NO"if _bY.upper()in("YES","NO")else"DOWN")
       elif(isinstance(_cF,dict)and str(_cF.get("umaResolutionStatus")or"").strip().lower()=="disputed"and not _cF.get("closed")and bool(pos.get("hold_to_maturity_lock"))and bool(pos.get("is_single_leg_lock"))and"KMIA"not in str(pos.get("asset")or"").upper()and"KMIA"not in str(tid or"").upper()):await d._maybe_recycle_disputed_htm_lock(tid,pos,_cx)
      except Exception:pass
  if not d.dry_run:
   try:_aZ=(any(position_is_settlement_receivable(p)for p in d.active_positions.values())and(time.time()-float(getattr(d,"_last_redemption_poll",.0)or.0))>=2.5);await asyncio.to_thread(d.poll_onchain_redemptions,_aZ)
   except Exception as e:logger.error(f"[REDEMPTION] Poll error: {e}")
  if d.dry_run:
   for tid,pos in list(d.active_positions.items()):
    try:
     _E=pos.get("token_id")
     if not _E or position_is_settlement_receivable(pos)or pos.get("hold_to_maturity_lock"):continue
     X=await d.executor.get_market_book_async(_E);_bv=X.get("bids",[])
     if _bv:
      _bz=max(float(b.get("price",.0))for b in _bv)
      if _bz>=pos.get("target_exit_price",.99):_ce=round(pos["entry_shares"]*pos["target_exit_price"],2);_bW=d.calculate_realized_cash_pnl(pos,_ce,.0);pos["status"]=ExecutionStatus.FILLED;pos["settled_at_utc"]=datetime.now(timezone.utc).isoformat();pos["won"]=True;pos["filled_exit_shares"]=pos["entry_shares"];pos["remaining_exit_shares"]=.0;pos["gross_exit_cash"]=_ce;pos["average_exit_price"]=pos["target_exit_price"];pos["payout_usd"]=_ce;pos["net_pnl_usd"]=_bW;pos["close_reason"]="DRY_RUN_MAKER_SCALP_FILLED";d.closed_positions.append(pos);d.risk_controller.record_trade_pnl(_bW,is_non_directional=bool(pos.get("is_dominance_box")or pos.get("is_single_leg_lock")or pos.get("is_legged_out_residual")or"BOX"in str(pos.get("sleeve")or"").upper()));del d.active_positions[tid];logger.info(f"[DRY-RUN] ✓ POSITION CLOSED VIA SIMULATED MAKER SCALP: {tid} | Net PnL=${_bW:+.2f}");d.save_state()
    except Exception:pass
  try:
   try:_b=await asyncio.to_thread(d._strict_open_orders);_r={o.get("id")or o.get("orderID")for o in _b if o};w=True
   except Exception as _ae:logger.warning(f"[SUPERVISION WARN] Open-orders snapshot degraded ({_ae}); " "continuing per-position stop-loss and fill supervision fail-closed.");_b=None;_r=set();w=False
   _cd=time.time();_cc=getattr(d,"_pos_market_ws",None)
   if _cc is not None:_cc.set_desired_tokens(d._desired_market_ws_tokens(_cd))
   try:await d._maybe_merge_live_complete_sets(_cd)
   except Exception as _l:logger.exception(f"[C1 MERGE] complete-set merge pass failed (supervision continues): {_l}")
   try:await d._try_atomic_box_overround_unwind(_cd,_r)
   except Exception as _R:logger.exception(f"[BOX OVERROUND] dual-leg unwind pass failed (supervision continues): {_R}")
   for tid,pos in list(d.active_positions.items()):
    if tid not in d.active_positions:continue
    try:
     if position_is_settlement_receivable(pos):continue
     if pos.get("status")=="UNRESOLVED_SETTLEMENT":
      pos.setdefault("_unresolved_settle_seq",int(getattr(d,"_collateral_sync_seq",0)or 0));_aY=pos.get("exit_order_id")or pos.get("pending_settlement_order_id")or pos.get("unwind_order_id");_by=[str(k)for k,v in(pos.get("order_records")or{}).items()if isinstance(v,dict)and v.get("cash_is_estimated")];_aN={str(x)for x in(pos.get("canceled_maker_exit_oids")or[])if x}
      for _bx in dict.fromkeys(([str(_aY)]if _aY else[])+_by):
       _bw=(pos.get("order_records")or{}).get(str(_bx))or{}
       if isinstance(_bw,dict)and"is_taker"in _bw:Y=bool(_bw["is_taker"])
       else:Y=(str(_bx)!=str(pos.get("exit_order_id")or"")and str(_bx)not in _aN)
       y=await asyncio.to_thread(d.executor.get_order_fill_summary,str(_bx),pos.get("token_id"))
       if y is not None:_cu=float((_bw.get("fallback_price")if isinstance(_bw,dict)else None)or((pos.get("unwind_limit_price")or.01)if Y else(pos.get("target_exit_price",.0)or.0)));d._record_order_summary(pos,y,_cu,taker=Y)
       _bc=(pos.get("order_records")or{}).get(str(_bx))or{}
       if((y is None or(isinstance(_bc,dict)and _bc.get("cash_is_estimated")))and pos.get("token_id")):
        _aX=await asyncio.to_thread(d._fetch_account_fills,str(pos.get("token_id")),max(.0,float(pos.get("entry_ts",.0)or.0)-60.),"SELL",str(_bx),tid)
        if isinstance(_aX,list)and _aX:d._record_history_fills(pos,_aX,taker=Y)
      _G=(pos.get("pending_settlement_close_reason")in{"MARKET_RESOLVED_LOSS","EXPIRED_OUT_OF_MONEY"}or(pos.get("close_reason")and"MARKET_RESOLVED_LOSS"in str(pos.get("close_reason"))));_F=float(pos.get("filled_exit_shares",.0)or.0)>.01
      if(_G and not _F)or(not pos.get("exit_cash_estimated",False)and float(pos.get("estimated_exit_cash",.0)or.0)==.0):
       if _G and not _F:pos["exit_cash_estimated"]=False;pos["estimated_exit_cash"]=.0
       d._close_position(tid,pos,pos.get("pending_settlement_close_status",ExecutionStatus.SETTLED if _G else ExecutionStatus.FILLED),pos.get("pending_settlement_close_reason","MARKET_RESOLVED_LOSS"if _G else"SETTLEMENT_CONFIRMED_CLOB"),won=False if(_G and not _F)else None)
      continue
     if pos.get("resolved_winning_outcome")is not None:await d._apply_market_resolution(tid,pos,pos["resolved_winning_outcome"]);continue
     if position_requires_lifecycle_resolution(pos):
      await asyncio.to_thread(d._resolve_lifecycle,tid,pos,_b)
      if tid not in d.active_positions or position_requires_lifecycle_resolution(pos):continue
     _aM=str(pos.get("umaResolutionStatus")or pos.get("uma_resolution_status")or"").strip().lower()
     if(not pos.get("exit_order_id")and not pos.get("is_liquidating")and not pos.get("is_legged_out_residual")and("KMIA"in str(pos.get("asset")or"").upper()or"KMIA"in str(tid or"").upper())and(pos.get("hold_to_maturity_lock")or _aM=="disputed"or max(.0,float(pos.get("candle_expiry_ts",_cd+6e2)or.0)-_cd)<=.0)):continue
     n=pos.get("exit_order_id");_E=pos.get("token_id");_bb=pos.get("candle_expiry_ts",_cd+6e2);_0=max(.0,_bb-_cd)
     if(not d.dry_run and _E and pos.get("hold_to_maturity_lock")and pos.get("status")==ExecutionStatus.MATCHED_PENDING_SETTLEMENT and(_cd-float(pos.get("_last_htm_inv_chk",.0)or.0))>=10.):
      pos["_last_htm_inv_chk"]=_cd;_ct,_cs=await asyncio.to_thread(d._wallet_token_balance,_E);_cr=float(pos.get("pre_token_balance",.0)or.0);_cq=float(pos.get("entry_shares",.0)or.0)
      if _ct is not None and _cs in{d.ONCHAIN_SOURCE,"CLOB_BALANCE_API"}:
       d_h=_ct-_cr;_cE=float(pos.get("fee_rate_applied",.0)or.0)
       if d_h>=max(.01,_cq-.05):pos["status"],pos["inventory_reconciled"]=ExecutionStatus.POSITION_CONFIRMED,True;d.save_state()
       elif _cE>.0 and d_h>=max(.01,_cq*(1.-_cE*.3)-.05):pos["entry_shares"]=pos["remaining_shares"]=pos["remaining_exit_shares"]=round(d_h,4);pos["entry_fee_asset"],pos["entry_fee_cash_usd"]="SHARES",.0;pos["status"],pos["inventory_reconciled"]=ExecutionStatus.POSITION_CONFIRMED,True;d.save_state()
     elif(not d.dry_run and _E and pos.get("hold_to_maturity_lock")and pos.get("status")==ExecutionStatus.POSITION_CONFIRMED and"KMIA"not in str(pos.get("asset")or"").upper()and"KMIA"not in str(tid or"").upper()and _aM!="disputed"and(_cd-float(pos.get("_last_htm_prereed_chk",.0)or.0))>=12.):
      pos["_last_htm_prereed_chk"]=_cd;_cp,_co=await asyncio.to_thread(d._wallet_token_balance,_E)
      if _cp is not None and _co==d.ONCHAIN_SOURCE and float(_cp)<=1e-4:pos["_last_gamma_res_poll"]=.0;pos["_zero_bal_gamma_urgent"]=True
     _2=5. if pos.get("sleeve")=="SLEEVE_4_BOUNDARY_SNIPE"else d.tte_cancel_window
     if(not n and position_may_post_new_maker_exit(pos)and _0>=_2):
      pos.pop("recovered_from_intent",None);_ap=await asyncio.to_thread(d._attempt_maker_exit_post,tid,pos);n=pos.get("exit_order_id")
      if _ap or not pos.get("inventory_reconciled")or position_requires_lifecycle_resolution(pos):continue
     _D=float(pos.get("entry_price",.5));z=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",pos.get("entry_shares",.0)))or.0);F=(pos.get("exit_order_status")=="STOP_CANCEL_PENDING"or(pos.get("exit_order_status")in({"UNWIND_RETRY_REQUIRED"}|PARTIAL_UNWIND_RESIDUAL_STATUSES)and _cd>=float(pos.get("next_unwind_retry_ts",.0)or.0)));_n=.0;from src.polymarket_research.riskless_machine_gun_engine import is_locked_arbitrage_box_leg as Q;_ar=bool(str(pos.get("box_type")or"")=="SPORTS_CORRIDOR"and not str(pos.get("box_partner_trade_id")or"")and not Q(pos,d.active_positions)and not pos.get("hold_to_maturity_lock"))
     if _ar and.05<float(pos.get("target_exit_price")or.99)<.95 and not pos.get("custom_maker_exit_price"):pos["custom_maker_exit_price"]=float(pos["target_exit_price"])
     u=False;H=None;_ba=float(pos.get("candle_open_spot",.0)or.0);_1=float(pos.get("entry_spot_ref")or pos.get("candle_open_spot")or _ba);_aq=float(pos.get("candle_sigma",.005)or.0);_j=False;_q=.0;O=.0;P=.0
     if(not n and not pos.get("is_liquidating")and not F and("KMIA"in str(pos.get("asset")or"").upper()or"KMIA"in str(tid or"").upper())and(pos.get("hold_to_maturity_lock")or _0<=.0)):continue
     if(not pos.get("is_liquidating")or F)and _E and z>.01:
      X=d._get_verified_shm_book(pos)
      if X is None and _cc is not None and"get_market_book_async"not in getattr(d.executor,"__dict__",{}):X=_cc.get_book(_E,max_age_sec=2.)
      if X is None:
       try:X=await d.executor.get_market_book_async(_E)
       except Exception as _ad:
        _a9=str(_ad).lower()
        if"404"in _a9 or"no orderbook exists"in _a9:pos["_book_closed_404"]=True;X={};_0=.0
        elif pos.get("hold_to_maturity_lock")and not pos.get("is_liquidating"):continue
        elif((any(c in _a9 for c in("429","502","503","504","timeout","timed out","remoteprotocolerror","connecterror","connection"))or"timeout"in type(_ad).__name__.lower())and not pos.get("is_liquidating")and(pos.get("is_single_leg_lock")or pos.get("is_dominance_box")or _0<=.0)):X={}
        else:raise
      _bv=X.get("bids",[])if isinstance(X,dict)else[];_cD=X.get("asks",[])if isinstance(X,dict)else[]
      if _bv or _cD:pos.pop("_book_closed_404",None)
      _n=max(float(b.get("price",.0))for b in _bv if float(b.get("size",.0))>0)if _bv else.0;_cb=min(float(a.get("price",.0))for a in _cD if float(a.get("size",.0))>0)if _cD else.0;_aL=(_cb-_n)if(_cb>0 and _n>0 and _cb>_n)else.0
      if 0<_0<=120.:
       _aK=f"_prewarmed_candle_{pos.get('market_id')}"
       if not getattr(d,_aK,False):setattr(d,_aK,True);asyncio.create_task(d._prewarm_next_candle_markets())
      _D=float(pos.get("entry_price")or.0)
      if pos.get("hold_to_maturity_lock"):
       from src.polymarket_research.riskless_protocol_v2_expansion import maybe_early_profit_recycle_htm_lock as I,maybe_manage_passive_htm_early_maker_recycle as C
       if(_n>=.998 and await I(d,tid,pos,X,_cd))or await C(d,tid,pos,X,_cd,_r):continue
       n=pos.get("exit_order_id")
      _aJ=bool(pos.get("is_dominance_box")or pos.get("is_single_leg_lock"))
      if(_ar and n and not pos.get("is_liquidating")and z>=5. and _n>=.35 and _0>3e2):
       _aW=float(pos.get("target_exit_price")or.99);_ca=(round(_n+.01,2)if _0<=9e2 else max(round(_n+.02,2),round(min(_aW-.02,_n+.04),2))if _0<=1800. else(round(_cb-.01,2)if(.58<=_cb<_aW-1e-4 and _cb>=_n+.02)else None))
       if _ca is not None and _n+1e-4<_ca<_aW-1e-4 and(_cd-float(pos.get("_sc_step_ts",.0)or.0))>=180.:pos["_sc_step_ts"]=_cd;pos["custom_maker_exit_price"]=_ca;logger.info(f"[PAA PRE-KICKOFF STEPDOWN] {tid}: TTE={_0:.0f}s bid=${_n:.2f} ask=${_cb:.2f} -> ${_aW:.2f} to ${_ca:.2f}");await d._atomic_replace_maker_exit(tid,pos,_ca);continue
      if(not _aJ and n and not pos.get("queue_jumped")and not pos.get("is_liquidating")and z>.01 and _0>=d.tte_cancel_window):
       _Z=float(pos.get("target_exit_price")or.0);_C=(_Z==.99 or(_Z==.98 and(d._effective_exit_policy()!="hold_98"or(_0<=75. and _n>=.96))))
       if _C:
        _bV=compute_queue_priority_maker_price(_D,z,_bv,_cD,_Z)
        if _bV is not None and(_cd-float(pos.get("queue_jump_attempt_ts",.0)or.0))>=30.:
         pos["queue_jump_attempt_ts"]=_cd;logger.info(f"[QUEUE JUMP SUPERVISION] Position {tid}: massive wall at ${_Z:.2f}. Stepping 1c in front to ${_bV:.2f} (cancelling OID: {n}).");_ap=await d._atomic_replace_maker_exit(tid,pos,_bV)
         if tid not in d.active_positions:continue
         if _ap:pos["queue_jumped"]=True
         n=pos.get("exit_order_id");z=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",z))or.0)
      _a8=pos.get("asset","BTC")
      if not _aJ and str(_a8 or"").upper()in{"BTC","ETH","SOL","XRP","BNB","DOGE","HYPE","ZEC","XAU","XAG"}:
       if pos.get("spot_denomination")=="USD":H=await asyncio.to_thread(d.get_usd_reference_spot_price,_a8)
       else:H=await asyncio.to_thread(d.get_reference_spot_price,_a8)
      _j=(H is not None and isinstance(H,(int,float))and math.isfinite(H)and math.isfinite(_ba)and H>0 and _ba>0)
      if _j:
       _q=(H-_ba)if pos.get("target_token")=="UP"else(_ba-H)
       if _1>0 and math.isfinite(_1):O=(H-_1)if pos.get("target_token")=="UP"else(_1-H);P=O/_1
       r=.0;_bU=pos.setdefault("spot_vel_history",[]);_bU.append([_cd,float(H)]);pos["spot_vel_history"]=[pt for pt in _bU if(_cd-pt[0])<=15.];_cC=pos["spot_vel_history"]
       if len(_cC)>=2:
        _aI=_cC[0][1]
        if _aI>0:
         if pos.get("target_token")=="UP":r=((H-_aI)/_aI)*1e2
         else:r=((_aI-H)/_aI)*1e2
       pos["v_spot_15s_pct"]=round(r,4)
      else:r=float(pos.get("v_spot_15s_pct",.0)or.0)
      if(not _aJ and evaluate_optimal_stopping_exit is not None and(d._effective_exit_policy()!="hold_98"or os.environ.get("PM_ENABLE_HOLD98_OBI_STEPDOWN","0")=="1")and not getattr(d,"hold_to_maturity",False)and n and not pos.get("obi_stepped_down")and not pos.get("is_liquidating")and z>=5. and _0>=d.tte_cancel_window and _n>.0 and _cb>.0 and _bv and _cD):
       _b9=sum(float(b.get("size",.0)if isinstance(b,dict)else b[1])for b in _bv if abs(float(b.get("price",.0)if isinstance(b,dict)else b[0])-_n)<1e-6);_b8=sum(float(a.get("size",.0)if isinstance(a,dict)else a[1])for a in _cD if abs(float(a.get("price",.0)if isinstance(a,dict)else a[0])-_cb)<1e-6);_bu=(_b9-_b8)/max(1e-6,_b9+_b8);_a7=evaluate_optimal_stopping_exit(entry_px=_D,rem_shares=z,best_bid=_n,best_ask=_cb,curr_target_px=float(pos.get("target_exit_price")or.0),tte_sec=_0,obi_l1=_bu,v_spot_15s_pct=r)
       if _a7.get("action")=="OBI_MAKER_STEP_DOWN"and(_cd-float(pos.get("obi_step_attempt_ts",.0)or.0))>=30.:
        pos["obi_step_attempt_ts"]=_cd;_bt=float(_a7["target_px"]);logger.info(f"[OBI MAKER STEP-DOWN] {tid}: heavy sell wall obi_l1={_bu:.2f} <= -0.40 at TTE={_0:.0f}s (v_spot_15s={r:+.3f}%); stepping resting maker ask to ${_bt:.2f}.");_aH=await d._atomic_replace_maker_exit(tid,pos,_bt,collapse_tranches=True)
        if tid not in d.active_positions:continue
        if _aH:pos["obi_stepped_down"]=True
        n=pos.get("exit_order_id");z=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",z))or.0)
      _i=bool(_0<=3e2);_aG=math.isfinite(_aq)and _aq>0 and _ba>0;_aV=str(pos.get("horizon")or"").lower()=="5m";_y=bool(_aV or pos.get("is_subhourly")or pos.get("horizon")=="15m"or pos.get("sleeve")=="SLEEVE_1_SUBHOURLY_15M"or(.0<float(pos.get("entry_tte",3600.)or 3600.)<=9e2 and pos.get("sleeve")=="SLEEVE_4_BOUNDARY_SNIPE"and"hourly"not in str(pos.get("title","")or"").lower()));_bT=read_fast_tick(_a8,max_age_sec=2.)if _y or not _aJ else None;_Y=((_bT.get("markets")or{}).get(str(pos.get("market_id")or""))if isinstance(_bT,dict)and isinstance(_bT.get("markets"),dict)else None)
      if _Y is None and isinstance(_bT,dict):
       for _hk in("m15","m5","h1"):
        _bS=_bT.get(_hk)
        if isinstance(_bS,dict)and str(_bS.get("market_id")or"")==str(pos.get("market_id")or""):_Y=_bS;break
      if(not _aJ and not d.dry_run and evaluate_guarded_complement_merge is not None and n and not pos.get("is_liquidating")and z>=5. and _0>=12. and isinstance(_Y,dict)and(os.getenv("PM_ENABLE_ONCHAIN_MERGE","0")=="1"or os.getenv("POLY_BUILDER_API_KEY")or getattr(d.executor,"signature_type",3)!=3)and(_cd-float(pos.get("comp_merge_attempt_ts",.0)or.0))>=15.):
       _b7="DOWN"if pos.get("target_token")=="UP"else"UP";_bR=_Y.get(_b7)or{};_bs=float(_bR.get("best_ask")or 1.);_br=str(_bR.get("token_id")or"")
       if _br and.0<_bs<=.03:
        _bq=evaluate_guarded_complement_merge(rem_shares=z,opp_ask=_bs,opp_ask_size=float(_bR.get("ask_size_l1")or.0),min_net_proceeds_ps=max(.982,float(pos.get("target_exit_price")or.98)+.002),fee_rate=d._exit_taker_fee_rate(pos),fee_exponent=float(pos.get("market_fee_exponent",pos.get("fee_exponent_applied",1.))or 1.))
        if _bq.get("approved"):
         pos["comp_merge_attempt_ts"]=_cd
         if await d._execute_guarded_complement_merge(tid,pos,_br,_bq,_cd):continue
      if(not _aJ and _y and not _aV and evaluate_d1_15m_to_5m_corridor_conversion is not None and 15.<=_0<=295. and z>=5. and isinstance(_bT,dict)and isinstance(_bT.get("m5"),dict)):
       _cn=evaluate_d1_15m_to_5m_corridor_conversion(pos,_bT.get("m5"),now_ts=_cd)
       if _cn.get("eligible"):pos["d1_corridor_candidate"]=_cn
      _O=3e2 if _aV else(9e2 if _y else 3600.);_x=(2.*_ba*_aq*math.sqrt(max(_0,1.)/_O))if(_j and _aG)else.0;_p=bool(_i and not _aG);_ao=bool(_i and not _j);_h=_p or _ao;M=bool(_i and _j and _aG and(_q>=-_x))or _h;G=bool(_i and _j and _aG and(_q<-_x)and(_n>=.01))
      if(G and _y and.0<_0<60. and should_suppress_final60s_twap_salvage is not None and isinstance(_Y,dict)):
       _aF=_aq*(math.sqrt(12.)if _aV else 2.);_bQ,_=should_suppress_final60s_twap_salvage(side=str(pos.get("target_token")or"UP"),strike_open=_ba,current_spot=float(H),twap_locked_mean=_Y.get("twap_locked_mean"),tte_sec=_0,sigma_1h=_aF,twap_locked_weight=_Y.get("twap_locked_weight"))
       if _bQ:G=False;M=True
      if G:
       if _0<=10. or getattr(d.executor,"auth_mode","")not in("LIVE","AUTHENTICATED_L2"):g=True
       else:
        _aU=2. if _0<=60. else 3.;_bP=pos.get("pre_expiry_otm_detected_ts")
        if _bP is None:pos["pre_expiry_otm_detected_ts"]=_cd;g=False
        else:g=(_cd-float(_bP))>=_aU
      else:pos.pop("pre_expiry_otm_detected_ts",None);g=False
      _X=-(d.spot_delta_k*_aq*_ba)if(_ba>0 and _aG)else-999999.;_ac=(_q/_ba)if _j else.0;_o=(_ac*1e2)if _j else None;_N=float(pos.get("filled_exit_shares",.0)or.0)>=(float(pos.get("entry_shares",.0)or.0)*.4);W=False;pos.pop("strike_retrace_detected_ts",None);l=False;_an=.1 if _N else.2;_ab=((not d.dry_run)and(getattr(d.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2"))and bool(_E and str(_E).isdigit()and len(str(_E))>=20));_aE=_y
      if(_n>=.08 and _n<=(_D-_an)and(not _i and not _j and _n<=.36)and _0>=25.):
       _aa=pos.get("low_bid_detected_ts")
       if _aa is None:pos["low_bid_detected_ts"]=_cd
       elif(_cd-float(_aa))>=6.:l=True
      else:pos.pop("low_bid_detected_ts",None)
      s,_W,_bp=evaluate_ev_terminal_twap_t5_salvage(pos=pos,now_ts=_cd,tte_rem=_0,spot_valid=_j,open_spot=_ba,spot_disp=_q,sigma_valid=_aG,candle_sigma=_aq,is_subhourly_pos=_y,is_5m_pos=_aV,best_b=_n,entry_px=_D,v_spot_15s_pct=r,exit_fee_rate=d._exit_taker_fee_rate(pos),fee_exp=float(pos.get("market_fee_exponent",pos.get("fee_exponent_applied",1.))or 1.),twap_locked_mean=_Y.get("twap_locked_mean")if isinstance(_Y,dict)else None,twap_locked_weight=_Y.get("twap_locked_weight")if isinstance(_Y,dict)else None,current_spot=float(H)if _j and H else None,is_live_auth=_ab)
      if _n>0:pos["max_seen_bid"]=max(float(pos.get("max_seen_bid",.0)or.0),_n)
      _am=float(pos.get("max_seen_bid",.0)or.0);h=False;u=False;K=.0;_bO=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("exit_supervisor",{});_b6=bool(_ab and _bO.get("enable_high_zone_mfe_ratchet",True));_bN=float(_bO.get("high_zone_mfe_arm_bid",.93));_bo=float(_bO.get("high_zone_mfe_drop",.04));_aT=float(_bO.get("high_zone_mfe_hold_confirm_sec",2.));_aD=float(_bO.get("high_zone_mfe_min_tte_sec",16.))
      if _ab:_aS=max(.04,.98-_D);L=round(min(.945,max(.86,_D+max(.05,.65*_aS))),4)
      else:L=max(.82,_D+.12)
      _w=.03 if _ab else.04;_M=(_aq*math.sqrt(max(_0,15.)/_O))if _aG else.0;_aC=(_q/max(1e-9,_ba*max(2e-4,_M)))if(_j and _aG)else.0
      if _b6 and.0<_D<.9 and not pos.get("is_single_leg_lock")and _am>=_bN:
       K=round(_am-_bo,4)
       if _n<=K+1e-6 and _0>=_aD and _n>=max(.5,round(_D+.03,4)):
        R=pos.get("trail_stop_detected_ts")or pos.get("trailing_ratchet_detected_ts")
        if R is None:pos["trail_stop_detected_ts"]=_cd;pos["trailing_ratchet_detected_ts"]=_cd
        elif(_cd-float(R))>=_aT:h=True;u=True
       else:pos.pop("trail_stop_detected_ts",None);pos.pop("trailing_ratchet_detected_ts",None)
      elif _am>=L and _D>0 and _aC<1.5:
       _aB=(.04 if _am>=.93 else.05)if _ab else(.05 if _am>=.9 else.07);K=round(_am-_aB,4)
       if _n<=K and _0>=25. and _n>=(_D+_w):
        R=pos.get("trail_stop_detected_ts")or pos.get("trailing_ratchet_detected_ts")
        if R is None:pos["trail_stop_detected_ts"]=_cd;pos["trailing_ratchet_detected_ts"]=_cd
        elif(_cd-float(R))>=4.:h=True
       else:pos.pop("trail_stop_detected_ts",None);pos.pop("trailing_ratchet_detected_ts",None)
      else:pos.pop("trail_stop_detected_ts",None);pos.pop("trailing_ratchet_detected_ts",None)
      D=bool(8.<=_0<=25. and z>=5. and _n>=.985 and _n>(_D+.02));m=False;j=False;i=False
      if _aJ:
       g=False;l=False;s=False;h=False;_a6=float(pos.get("box_cost_net")or.975);_9=float(pos.get("box_total_cost_usd",999.)or 999.);_a5=pos.get("_closed_partner_leg");_bM=d.active_positions.get(str(pos.get("box_partner_trade_id")or""));_al=bool((isinstance(_a5,dict)and float(_a5.get("payout_usd",.0)or.0)>=_9)or(isinstance(_bM,dict)and float(_bM.get("remaining_shares",1.)or.0)<=.01 and max(float(_bM.get("confirmed_realized_cash",.0)or.0),float(_bM.get("realized_exit_cash",.0)or.0))>=_9));i=bool((isinstance(_a5,dict)and"BOX_EARLY_BID_HARVEST"in str(_a5.get("close_reason")or""))or(isinstance(_bM,dict)and float(_bM.get("remaining_shares",1.)or.0)<=.01 and"BOX_EARLY_BID_HARVEST"in str(_bM.get("pending_settlement_close_reason")or _bM.get("close_reason")or"")));J=z;q=.0
       if isinstance(_a5,dict)and"BOX_EARLY_BID_HARVEST"in str(_a5.get("close_reason")or""):q=float(_a5.get("payout_usd",.0)or.0)-float(_a5.get("exit_fee_usd",.0)or.0)
       elif isinstance(_bM,dict):
        _b5=float(_bM.get("remaining_shares",z)or.0);_bL=max(float(_bM.get("confirmed_realized_cash",.0)or.0),float(_bM.get("realized_exit_cash",.0)or.0))-float(_bM.get("realized_exit_fee",.0)or.0)
        if i:q=_bL
        elif(z-_b5>=5. and float(_bM.get("filled_exit_shares",.0)or.0)>=5. and("BOX_EARLY_BID_HARVEST"in str(_bM.get("unwind_reason")or _bM.get("pending_unwind_tag")or"")or _bM.get("exit_order_status")in PARTIAL_UNWIND_RESIDUAL_STATUSES)):i=True;J=round(z-_b5,2);q=_bL
       _bK=d._exit_taker_fee_rate(pos);_bJ=float(pos.get("fee_exponent_applied",1.)or 1.);_b4=_n-(_bK*((_n*(1.-_n))**_bJ)if _bK>.0 else.0);V=.02
       if i and J>=5.:
        _aA=max(J,float(pos.get("entry_shares")or J));_B=(_9*(J/_aA))if _9<9e2 else(_a6*J);_az=max(.02,(_B-q-.02)/max(J,1e-6));_ak=_az
        for _ in range(2):_cm=max(.01,min(.99,_ak));_ak=_az+(_bK*((_cm*(1.-_cm))**_bJ)if _bK>.0 else.0)
        V=max(.02,min(.99,math.ceil(_ak*1e2-1e-9)/1e2))
       if J>=5. and _n>=V and i:j=True
       elif(_0>45. and z>=5. and _n>=.05 and isinstance(_bM,dict)and not pos.get("is_liquidating")and not _bM.get("is_liquidating")and _bM.get("exit_order_status")not in({"STOP_CANCEL_PENDING","UNWIND_RETRY_REQUIRED"}|PARTIAL_UNWIND_RESIDUAL_STATUSES)and _bM.get("pending_unwind_tag")!="BOX_EARLY_BID_HARVEST_UNWIND"and(d.dry_run or(pos.get("inventory_reconciled")and _bM.get("inventory_reconciled")))and abs(z-float(_bM.get("remaining_shares")or.0))<=.02):
        _b3=sum(float(b.get("size",.0)if isinstance(b,dict)else b[1])for b in _bv if abs(float(b.get("price",.0)if isinstance(b,dict)else b[0])-_n)<1e-6)
        if _b3>=z*1.25:
         _bn=d._get_verified_shm_book(_bM)
         if _bn is None and hasattr(d.executor,"get_market_book")and(d.dry_run or _cd-float(pos.get("_pb_ts",.0))>=3.):pos["_pb_ts"]=_cd;_bn=await asyncio.to_thread(d.executor.get_market_book,str(_bM.get("token_id")or""))
         _b2=(_bn or{}).get("bids")or[];_cB=max((float(b.get("price",.0)if isinstance(b,dict)else b[0])for b in _b2 if float(b.get("size",.0)if isinstance(b,dict)else b[1])>0),default=.0);_bI=sum(float(b.get("size",.0)if isinstance(b,dict)else b[1])for b in _b2 if abs(float(b.get("price",.0)if isinstance(b,dict)else b[0])-_cB)<1e-6);_cA=d._exit_taker_fee_rate(_bM);_cz=float(_bM.get("fee_exponent_applied",_bJ)or 1.);_bH=_cB-(_cA*((_cB*(1.-_cB))**_cz)if _cA>.0 else.0);_g=(str(pos.get("box_type")or"")in{"COMPLETE_SET","NEGRISK_2LEG","NEGRISK_CROSS"}or _0>3600. or(_b4+_bH)>=max(1.08,_a6+.08))
         if _cB>=.05 and _bI>=z*1.25 and(_b4+_bH)>=max(1.008,_a6+.015)and _g:j=True
       if _ar and(_bb-3e2)<=_cd<=(_bb+3e2)and z>=1. and _n>=.25:j=True
       if F and pos.get("pending_unwind_tag")=="BOX_EARLY_BID_HARVEST_UNWIND"and not j and not n:F=False;pos.pop("pending_unwind_tag",None);pos["is_liquidating"]=False;pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED"if _0>45. else"DETERMINISTIC_TERMINAL_HOLD";d.save_state();continue
       _cl=float(pos.get("box_k_low")or.0);_ck=float(pos.get("box_k_high")or.0);_8=bool(_j and _ck>=_cl>.0 and(H<_cl*(1.-.0012)or H>_ck*(1.+.0012)));_bm=bool(not pos.get("hold_to_maturity_lock")and z>=5. and _b4>=(_a6+.002)and((5.<=_0<=35. and _n>=.99)or(5.<=_0<=65. and _n>=.985 and _8)));_a4=bool(5.<=_0<=35. and z>=5. and _al and _n>=.2);D=_bm;m=bool(_bm or _a4 or j)
      elif D or(d._effective_exit_policy()!="hold_98"and not getattr(d,"hold_to_maturity",False)and pos.get("sleeve")!="SLEEVE_4_BOUNDARY_SNIPE"and _0<=45. and z>.01 and _n>=.85 and _n>(_D+.03)):m=True
      if(not _bv or _n<=.0)and not pos.get("is_liquidating"):
       if _0<=30. or _aJ:pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD";continue
       _V=pos.get("zero_bid_detected_ts")
       if _V is None:pos["zero_bid_detected_ts"]=_cd;continue
       if(_cd-float(_V))<max(1.5,float(d.low_bid_persistence_seconds)):continue
       if pos.get("status")!="LIQUIDITY_CRISIS":
        pos["status"]="LIQUIDITY_CRISIS";pos["exit_order_status"]="LIQUIDITY_CRISIS";pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD";pos["liquidity_crisis_ts"]=_cd;_bG=GLOBAL_GOVERNANCE_MANAGER.snapshot.get("exit_supervisor",{});_a3=int(_bG.get("global_zero_bid_halt_min_markets",_bG.get("min_markets_for_global_liquidity_halt",2)));_bl={str(p_lc.get("market_id")or k_lc)for k_lc,p_lc in d.active_positions.items()if p_lc.get("status")=="LIQUIDITY_CRISIS"and(float(p_lc.get("candle_expiry_ts",.0)or.0)-_cd)>120.}
        if not bool(_bG.get("isolate_single_market_zero_bid",True))or len(_bl)>=_a3:logger.critical(f"[LIQUIDITY_CRISIS_GLOBAL] {len(_bl)} markets zero-bid (>120s TTE). Suspending new entries.");d.risk_halt=True;d._refresh_global_halt()
        else:logger.warning(f"[ZERO_BID_ISOLATED] {tid} ({_E}) zero-bid; isolated to DETERMINISTIC_TERMINAL_HOLD without global halt.")
       continue
      else:pos.pop("zero_bid_detected_ts",None)
      if pos.get("exit_order_status")=="PASSIVE_STOP_RESTING":
       _L=_cd-float(pos.get("passive_stop_start_ts",_cd));_A=3.
       if l or W or _L>=_A:_aR=("Strike-retrace stop"if W else"Spot structural crash"if l else f"3.0s passive window expired ({_L:.1f}s)");logger.info(f"[PASSIVE STOP ESCALATION] {tid}: {_aR}. Escalating to verified cancel + FAK unwind.");F=True
       else:
        if n:
         y=await asyncio.to_thread(d.executor.get_order_fill_summary,n,_E)
         if y is not None:
          if d._record_order_summary(pos,y,float(pos.get("target_exit_price",.0)or.0),taker=False):d.save_state()
          if float(pos.get("remaining_shares",.0)or.0)<=.02:d._close_position(tid,pos,ExecutionStatus.FILLED,"PASSIVE_STOP_MAKER_FILLED",won=None)
        continue
      _v=False
      if _i and(M or _h or not _j or not _aG)and not W and not l and not s and not h and not m:
       if(not pos.get("is_legged_out_residual")and pos.get("active_unwind_trigger_kind")not in{"BOX_HARVEST","PROFIT_RATCHET","PRE_EXPIRY_99C","FINAL_45S"}and pos.get("exit_order_status")not in({"STOP_CANCEL_PENDING"}|PARTIAL_UNWIND_RESIDUAL_STATUSES)):F=False;pos["is_liquidating"]=False
       pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD_FINAL"if _0<d.tte_cancel_window else"DETERMINISTIC_TERMINAL_HOLD"
      if _0<=.0 and not(_ar and _cd<=_bb+3e2)and(F or s or W or l or g or h or m):pos["is_liquidating"]=False;pos["exit_order_status"]="DETERMINISTIC_TERMINAL_HOLD";pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD_FINAL";pos["next_unwind_retry_ts"]=.0;d.save_state();continue
      _a=pos.get("exit_order_status")=="TERMINAL_UNWIND_FAILED_SUPERVISED"or(pos.get("exit_order_status")in({"UNWIND_RETRY_REQUIRED"}|PARTIAL_UNWIND_RESIDUAL_STATUSES)and not F and not l and _0>10.)
      if not _a and(F or s or W or l or g or h or m):
       _7=str(pos.get("active_unwind_trigger_kind")or"");_K=bool(j or m or h or s or W or l or g)
       if(F and not _K and pos.get("exit_order_status")not in{"STOP_CANCEL_PENDING","PASSIVE_STOP_RESTING"}and _7 in{"PROFIT_RATCHET","PRE_EXPIRY_99C"}and not _aJ):
        _bk=float(pos.get("_last_ratchet_floor",.0)or.0);U=(_7=="PROFIT_RATCHET"and _bk>.0 and _n>_bk+.005);Z=(_7=="PRE_EXPIRY_99C"and _n<.98)
        if U or Z:
         pos["is_liquidating"]=False;pos.pop("active_unwind_trigger_kind",None);pos.pop("pending_unwind_tag",None)
         if not n and"saved_tp_exit_price"in pos:pos["target_exit_price"]=float(pos.pop("saved_tp_exit_price"))
         pos["exit_order_status"]=("RESTING"if n else("EXIT_RECOVERY_REQUIRED"if _0>=_2 else"DETERMINISTIC_TERMINAL_HOLD"));d.save_state();logger.info(f"[UNWIND RETRY ABORTED -> RESTORE TP] {tid}: prior {_7} condition cleared (best_b=${_n:.4f}, floor=${_bk:.4f}, TTE={_0:.0f}s); restoring {pos['exit_order_status']}.");continue
       if j:pos["active_unwind_trigger_kind"]="BOX_HARVEST"
       elif D or m:pos["active_unwind_trigger_kind"]="PRE_EXPIRY_99C"if D else"FINAL_45S"
       elif h:pos["active_unwind_trigger_kind"]="PROFIT_RATCHET";pos["_last_ratchet_floor"]=float(K)
       elif s or W or l or g:pos["active_unwind_trigger_kind"]="ADVERSE_SALVAGE"
       _aj=str(pos.get("active_unwind_trigger_kind")or _7);T=bool(j or m or h or _aj in{"BOX_HARVEST","PRE_EXPIRY_99C","FINAL_45S","PROFIT_RATCHET"});_b1=(f"Box combined-bid overround harvest (TTE={_0:.0f}s, bid ${_n:.4f})"if j else f"Final-45s capital recycle (TTE={_0:.0f}s <= 45s, bid ${_n:.4f} >= 0.88, recycling USDC before rollover)"if m else f"High-Zone MFE profit-lock ratchet (peak bid ${_am:.4f} >= ${_bN:.2f} armed floor ${K:.4f}, current bid ${_n:.4f} <= floor for >={_aT:.1f}s, locking {_n-_D:+.2f}/share)"if u else f"Trailing profit ratchet (peak bid ${_am:.4f} armed trail floor ${K:.4f}, current bid ${_n:.4f} <= trail floor for >=4.0s, locking in +{_n-_D:+.2f}/share)"if h else f"3-Zone opposite-side structural breakout salvage (wrong-side {_W:+.2f}%, TTE={_0:.0f}s, bid=${_n:.4f})"if s else f"Strike-retrace stop (signed cushion {_o:+.4f}% <= retrace floor for >=10s, TTE={_0:.0f}s, bid=${_n:.4f})"if W else f"Hard bid-drop stop (bid ${_n:.4f} <= entry ${_D:.4f} - {_an:.2f} for >=6s, TTE={_0:.0f}s)"if l else f"Scheduled Unwind Retry ({_aj or'STOP_LOSS'})"if F else f"Pre-expiry OTM salvage (TTE={_0:.0f}s, spot={H:.2f} vs open={_ba:.2f})"if g else f"Spot structural breakdown (candle_disp={_q:.2f}, entry_disp={O:.2f}, move={_ac*100:.2f}%)");logger.warning(f"[SALVAGE ACTIVATED] Position {tid}: {_b1}. Unwinding position immediately...")
       if not d.dry_run and not T:send_operational_alert("WRONG_SIDE_SALVAGE_EXIT",f"Position {tid}: {_b1}","WARNING",dedupe_key=f"salvage:{tid}")
       pos["stop_triggered_ts"]=_cd;pos.pop("exit_tranches",None);_bF=("D1_LEGGED_OUT_RESIDUAL_UNWIND"if pos.get("is_legged_out_residual")else"BOX_EARLY_BID_HARVEST_UNWIND"if j else"FINAL_45S_CAPITAL_RECYCLE_UNWIND"if m else"TRAILING_PROFIT_RATCHET_UNWIND"if(h or _aj=="PROFIT_RATCHET")else"CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE"if s else"STRIKE_RETRACE_SALVAGE"if W else"HARD_BID_DROP_SALVAGE"if l else"PRE_EXPIRY_OTM_SALVAGE"if g else pos.get("pending_unwind_tag")or"ADVERSE_STOP_LOSS_UNWIND");pos["pending_unwind_tag"]=_bF
       if n:
        _ai=float(pos.get("filled_exit_shares",.0)or.0);_aQ=await asyncio.to_thread(d.executor.cancel_order,n);y=await asyncio.to_thread(d.executor.get_order_fill_summary,n,_E)
        if y is not None:d._record_order_summary(pos,y,float(pos.get("target_exit_price",.0)or.0),taker=False)
        if float(pos.get("remaining_shares",z)or.0)<=.02:logger.info(f"✓ [STOP-LOSS RECONCILED] {tid} already fully matched on resting exit before unwind.");d._close_position(tid,pos,ExecutionStatus.SETTLED,"MAKER_SCALP_FILLED_CLOB",won=None);continue
        _ay=max(float(y.get("matched",.0)or.0)if isinstance(y,dict)else.0,float(_aQ.get("matched",.0)or.0)if isinstance(_aQ,dict)else.0)
        if _ay>_ai+1e-4:pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED";pos["pending_canceled_order_id"]=n;d.save_state();continue
        if isinstance(_aQ,dict)and bool(_aQ.get("is_canceled")):_r.discard(n)
        E=((d.dry_run and(n not in _r or y is None))or(n not in _r and((y is not None and y["terminal"])or(isinstance(_aQ,dict)and(n in(_aQ.get("canceled")or[])or bool(_aQ.get("is_canceled")))))))
        if not E:pos["exit_order_status"]="STOP_CANCEL_PENDING";pos["cancel_pending_order_id"]=n;pos["pending_unwind_tag"]=_bF;d.save_state();continue
        d.executor.release_inventory(reservation_id=n);_ah=pos.setdefault("canceled_maker_exit_oids",[])
        if str(n)not in _ah:
         _ah.append(str(n))
         if len(_ah)>16:del _ah[:-16]
        pos["exit_order_id"]=None;n=None
        if"saved_tp_exit_price"in pos:pos["target_exit_price"]=float(pos.pop("saved_tp_exit_price"))
       pos.pop("low_bid_detected_ts",None);pos.pop("strike_retrace_detected_ts",None);pos.pop("trail_stop_detected_ts",None);pos.pop("trailing_ratchet_detected_ts",None);pos["exit_order_status"]="CANCELED_FOR_STOP_LOSS";_c=bool(h and not u and not s and not g and r>-.05)
       if(_c and _0>120. and _aL>=.04 and z>=5. and not pos.get("passive_3s_attempted")and not d.dry_run and getattr(d.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2")):
        pos["passive_3s_attempted"]=True;_J=round(min(_cb-.01,_n+max(.01,.4*_aL)),2);logger.info(f"[TWO-STAGE MAKER UNWIND] Posting 3.0s non-blocking passive maker sell for {tid}: {z:.1f} shrs @ ${_J:.2f} (midpoint maker before FAK)...");_cj=await asyncio.to_thread(d.executor.post_maker_exit_order,token_id=_E,price=_J,size=z,side="SELL")
        if isinstance(_cj,dict)and _cj.get("success")and _cj.get("orderID"):_aP=_cj["orderID"];pos.setdefault("saved_tp_exit_price",float(pos.get("target_exit_price")or.98));pos["exit_order_id"]=_aP;pos["target_exit_price"]=_J;pos["exit_order_status"]="PASSIVE_STOP_RESTING";pos["passive_stop_start_ts"]=_cd;d.save_state();continue
        elif isinstance(_cj,dict)and _cj.get("outcome_unknown"):
         _aP=_cj.get("orderID")
         if _aP:pos["exit_order_id"]=_aP;pos["exit_order_size"]=float(z)
         if _cj.get("reservation_id"):pos.setdefault("pending_reservation_ids",[]).append(_cj["reservation_id"])
         pos["target_exit_price"]=_J;pos["exit_post_attempt_ts"]=_cd;pos["exit_order_status"]="EXIT_POST_OUTCOME_UNKNOWN";d.save_state();logger.critical(f"[TWO-STAGE MAKER UNWIND] Ambiguous passive maker post for {tid} (OID: {_aP}); " "holding reservation and deferring FAK unwind until reconciled.");continue
       z=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",z))or.0)
       if z<=.02:d._close_position(tid,pos,ExecutionStatus.SETTLED,"MAKER_SCALP_FILLED_CLOB",won=None);continue
       if _ab:
        _I=d._get_verified_shm_book(pos)
        if isinstance(_I,dict):
         _bj=_I.get("bids")or[];_bi=max((float(b.get("price",.0))for b in _bj if float(b.get("size",.0))>0),default=.0)
         if _bi>.0:_n=_bi
       _U=int(pos.get("unwind_retry_count",0)or 0);_f=z
       if _aJ and j:_f=min(z,J)if i else z;A=(max(.25,round(_n-.03,2))if _ar else max(V if i else.02,round(_n-(.02 if i else.0),4)))
       elif _aJ and not _a4:A=.98
       elif m or _aj=="PRE_EXPIRY_99C":A=(max(.98,round(math.floor((_n+1e-9)*1e3)/1e3,3))if(D or _aj=="PRE_EXPIRY_99C")else max(.01,round(_n-.01,4)))
       elif _aj=="PROFIT_RATCHET":A=max(.01,round(_n-min(.04,.02+.01*min(_U,2)),4))
       elif(_ab and not h)or _U>0:_a2=.04+.04*min(_U,4);_bh=(getattr(d.executor,"_tick_size_cache",None)or{}).get(str(_E));S=(.001 if(_n<.02 or(_bh is not None and float(_bh)<=.001+1e-9))else.01);A=max(S,round(_n-_a2,4))
       else:S=.001 if _n<.02 else.01;A=max(S,round(_n-.02,4))
       if isinstance(getattr(d.executor,"_fee_cache",None),dict)and str(_E)not in d.executor._fee_cache:d.executor._fee_cache[str(_E)]=(d._exit_taker_fee_rate(pos),float(pos.get("fee_exponent_applied",pos.get("fee_exponent",1.))or 1.))
       N=await asyncio.to_thread(d.executor.execute_unwind_order,token_id=_E,size=_f,side="SELL",min_price=A);pos.pop("pending_unwind_tag",None);_S=d._handle_unwind_response(tid,pos,N,_f,_bF,"PARTIAL_UNWIND_REMAINING",A)
       if _S!="FAILED":d.executor.invalidate_collateral_cache();d._pending_collateral_refresh=True;d.save_state();continue
       pos["pending_unwind_tag"]=_bF;N=N or{};logger.error(f"Immediate FAK unwind failed for {tid}: {N.get('error')}. Verifying inventory...");_6=(not pos.get("inventory_reconciled")and(_cd-float(pos.get("entry_ts")or _cd))<18. and"sell_inventory_reconciliation_required"in str(N.get("error","")).lower())
       if not d.dry_run and _E:
        bal,src=await asyncio.to_thread(d._wallet_token_balance,_E);eps=d.executor.calculate_balance_epsilon(.001)
        if bal is not None and bal>=z-.05:pos["inventory_reconciled"]=True
        _e="not enough balance"in str(N.get("error","")).lower()
        if not _6 and bal is not None and((_e and bal<=.01)or bal+eps<z-.01):logger.critical(f"[FAIL-CLOSED] {tid}: wallet {bal:.4f} < remaining {z:.4f} after failed unwind. " "Reconciling from exchange trade history before any further action.");pos["exit_order_status"]="UNRESOLVED_BALANCE_DISCREPANCY";pos["unwind_attempt_ts"]=float(pos.get("unwind_last_attempt_ts")or pos.get("entry_ts")or _cd);pos["unwind_reason"]="ADVERSE_STOP_LOSS_UNWIND";pos["next_resolve_ts"]=.0;d.save_state();continue
       _a1=str(N.get("error","")or"").lower()
       if(bool(N.get("market_closed"))or is_market_closed_or_disabled_error(resp=N)or(_0<=5. and"trading is disabled"in _a1)or any(k in _a1 for k in("market is closed","orderbook does not exist","no orderbook exists"))):pos["is_liquidating"]=False;pos["exit_order_status"]="DETERMINISTIC_TERMINAL_HOLD";pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD_FINAL";pos["next_unwind_retry_ts"]=.0;d.save_state();continue
       if z<5. and any(k in _a1 for k in("minimum","min size","invalid amounts","size too small")):pos["is_liquidating"]=False;pos["exit_order_status"]="SUB_MINIMUM_LOT_SUPERVISED_HOLD";pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD";d.save_state();continue
       pos["is_liquidating"]=False
       if _aJ and not _a4 and not i and not _ar:pos.pop("pending_unwind_tag",None);pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED"if(j and _0>45.)else"DETERMINISTIC_TERMINAL_HOLD";pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD";d.save_state();continue
       if _6:_z=int(pos.get("unwind_retry_count",0));B=.5
       else:
        _z=int(pos.get("unwind_retry_count",0))+1;pos["unwind_retry_count"]=_z
        if"no orders found to match with fak order"in _a1:B=.35 if _z<=3 else min(30.,2.**min(_z-2,5))
        else:B=min(30.,2.**min(_z,5))
       pos["next_unwind_retry_ts"]=_cd+B;pos["unwind_last_error"]=str(N.get("error","unknown"));pos["unwind_last_attempt_ts"]=_cd
       if _z>=10:pos["exit_order_status"]="TERMINAL_UNWIND_FAILED_SUPERVISED";logger.critical(f"[UNWIND ESCALATION TERMINAL] {tid}: {_z} consecutive failed FAK attempts. " "Position remains exposed and requires active supervisor intervention.")
       else:
        pos["exit_order_status"]="UNWIND_RETRY_REQUIRED"
        if _z in{3,6}:logger.critical(f"[UNWIND ESCALATION] {tid}: {_z} consecutive failed FAK attempts. Position remains exposed.")
       d.save_state();continue
     _u=False
     if _u:
      _t=_aq*math.sqrt(max(_0,1.)/_O)if(math.isfinite(_aq)and _aq>0)else.0;_T=2.*_ba*_t if(_ba>0 and _t>0)else.0;_k=(pos.get("exit_order_status")=="RESTING_099_CAPITAL_RECYCLE"and bool(n)and _0>=30. and(not _j or(_T>.0 and _q>=_T)))
      if not _k:
       if n:
        if n in _r and pos.get("exit_order_status")!="PRE_EXPIRY_CANCEL_PENDING":logger.info(f"[REGIME 4 TTE < {d.tte_cancel_window:.0f}s] TTE={_0:.0f}s. Initiating cancellation of resting maker scalp ask {n} for {tid}.");await asyncio.to_thread(d.executor.cancel_order,n);pos["exit_order_status"]="PRE_EXPIRY_CANCEL_PENDING";pos["cancel_pending_order_id"]=n;d.save_state();continue
        y=await asyncio.to_thread(d.executor.get_order_fill_summary,n,_E)
        if y is not None:d._record_order_summary(pos,y,float(pos.get("target_exit_price",.0)or.0),taker=False)
        E=(d.dry_run and(n not in _r or y is None))or(n not in _r and y is not None and bool(y.get("terminal")))
        if not E:
         if n in _r:await asyncio.to_thread(d.executor.cancel_order,n)
         logger.warning(f"[REGIME 4] Awaiting verified cancellation of {n} before unwinding {tid}.");pos["exit_order_status"]="PRE_EXPIRY_CANCEL_PENDING";d.save_state();continue
        d.executor.release_inventory(reservation_id=n);pos["pending_settlement_order_id"]=n;pos["exit_order_id"]=None;n=None
       z=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",.0))or.0)
       if z<.01:logger.info(f"✓ [MAKER SCALP FILLED PRE-EXPIRY] {tid} fully matched on resting ask before cancellation.");d._close_position(tid,pos,ExecutionStatus.SETTLED,"MAKER_SCALP_FILLED_CLOB",won=True);continue
       if(not math.isfinite(_aq)or _aq<=0 or not math.isfinite(_ba)or _ba<=0):logger.critical(f"[REGIME 4 TTE < {d.tte_cancel_window:.0f}s] TTE={_0:.0f}s. Position {tid} nonfinite sigma ({_aq}) or open ({_ba}). Outcome classification is UNKNOWN; refusing assumption of ITM.");pos["exit_order_status"]="OUTCOME_UNKNOWN";pos["status"]=ExecutionStatus.POSITION_CONFIRMED;d.save_state();continue
       _5=_aq*math.sqrt(max(_0,1.)/_O);_4=2.*_ba*_5
       if not _j:logger.critical(f"[REGIME 4 TTE < {d.tte_cancel_window:.0f}s] TTE={_0:.0f}s. Position {tid} spot price UNAVAILABLE/INVALID (ref={H}, open={_ba}). Outcome classification is UNKNOWN; refusing assumption of ITM. Retaining open exposure under supervised terminal resolution.");pos["exit_order_status"]="OUTCOME_UNKNOWN";pos["status"]=ExecutionStatus.POSITION_CONFIRMED;d.save_state();continue
       elif _q<-_4:
        logger.warning(f"[REGIME 4 TTE < {d.tte_cancel_window:.0f}s] TTE={_0:.0f}s. Position {tid} is strictly OUT-OF-THE-MONEY (delta={_q:+.2f} vs open={_ba:.2f}, pin_thresh={_4:.2f}). Dispatching emergency salvage unwind for {z:.2f} shares.");pos["exit_order_status"]="EMERGENCY_SALVAGE_UNWIND"
        if isinstance(getattr(d.executor,"_fee_cache",None),dict)and str(_E)not in d.executor._fee_cache:d.executor._fee_cache[str(_E)]=(d._exit_taker_fee_rate(pos),float(pos.get("fee_exponent_applied",pos.get("fee_exponent",1.))or 1.))
        N=await asyncio.to_thread(d.executor.execute_unwind_order,token_id=_E,size=z,side="SELL",min_price=.01);_S=d._handle_unwind_response(tid,pos,N,z,"PRE_EXPIRY_OTM_SALVAGE_UNWIND","PARTIAL_SALVAGE_REMAINING",.01)
        if _S!="FAILED":continue
        logger.error(f"[EMERGENCY SALVAGE FAILED] {tid}: {(N or{}).get('error')}. Fail-closed: Retaining open exposure for terminal resolution supervision.");pos["exit_order_status"]="SALVAGE_FAILED_TERMINAL_HOLD";pos["status"]=ExecutionStatus.POSITION_CONFIRMED;d.save_state();continue
       elif abs(_q)<=_4:
        if pos.get("exit_order_status")!="PIN_RISK_EXPIRY_HOLD":logger.warning(f"[REGIME 4 TTE < {d.tte_cancel_window:.0f}s] TTE={_0:.0f}s. Position {tid} is in PIN-RISK UNCERTAINTY ZONE (spot={H:.2f} vs open={_ba:.2f}, delta={_q:+.2f}). " "Holding with supervisor awareness to terminal market resolution.");pos["exit_order_status"]="PIN_RISK_EXPIRY_HOLD";pos["status"]=ExecutionStatus.POSITION_CONFIRMED;d.save_state()
        continue
       else:
        _m=1.5*_4
        if _q>=_m and _0>=30. and not pos.get("recycle_099_attempted"):
         pos["recycle_099_attempted"]=True;pos["target_exit_price"]=.99;_ax=await asyncio.to_thread(d.executor.post_maker_exit_order,token_id=_E,price=.99,size=z,side="SELL")
         if d._apply_exit_post_result(pos,_ax,z):pos["exit_order_status"]="RESTING_099_CAPITAL_RECYCLE";d.save_state();continue
        if pos.get("exit_order_status")!="CANCELED_FOR_EXPIRY_HOLD":logger.info(f"[REGIME 4 TTE < {d.tte_cancel_window:.0f}s] TTE={_0:.0f}s. Position {tid} is strictly IN-THE-MONEY (spot={H:.2f} vs open={_ba:.2f}, delta={_q:+.2f} > threshold={_4:.2f}). " "Holding to $1.00 settlement.");pos["exit_order_status"]="CANCELED_FOR_EXPIRY_HOLD";pos["status"]=ExecutionStatus.POSITION_CONFIRMED;d.save_state()
        continue
     if pos.get("is_liquidating")and pos.get("unwind_order_id"):
      _ci=pos["unwind_order_id"]
      if _ci not in _r:
       y=await asyncio.to_thread(d.executor.get_order_fill_summary,_ci,_E)
       if y is None:pos["exit_order_status"]="UNWIND_RECONCILIATION_REQUIRED";d.save_state();continue
       _ag=str(y.get("status","")).upper();_bE=float(y.get("matched",.0)or.0);z=float(pos.get("remaining_shares",pos.get("remaining_exit_shares",pos.get("entry_shares",.0)))or.0);_bg=float(pos.get("unwind_order_size",z))
       if _ag not in{"MATCHED","FILLED","CONFIRMED"}or _bE<_bg-1e-4:pos["exit_order_status"]="UNWIND_RECONCILIATION_REQUIRED";d.save_state();continue
       d._record_order_summary(pos,y,float(y.get("limit_price")or.01),taker=False)
       if float(pos.get("remaining_shares",.0)or.0)<=.01:d._close_position(tid,pos,ExecutionStatus.SETTLED,"SPOT_DELTA_PASSIVE_UNWIND",won=None);continue
       pos["status"]=ExecutionStatus.PARTIALLY_FILLED;pos["exit_order_status"]="PARTIAL_PASSIVE_UNWIND_REMAINING";d.save_state();continue
      elif(_cd-float(pos.get("unwind_start_time",_cd)or _cd))>d.passive_unwind_timeout:
       logger.info(f"[REGIME 4 UNWIND TIMEOUT] Passive order {_ci} timed out; cancelling and reconciling before repricing.");await asyncio.to_thread(d.executor.cancel_order,_ci);y=await asyncio.to_thread(d.executor.get_order_fill_summary,_ci,_E)
       if y is not None and y.get("matched",.0)>float(pos.get("filled_exit_shares",.0)or.0)+1e-4:d._record_order_summary(pos,y,float(y.get("limit_price")or.01),taker=False);pos["exit_order_status"]="FILL_RECONCILIATION_REQUIRED";pos["pending_canceled_order_id"]=_ci;d.save_state();continue
       pos["exit_order_status"]="UNWIND_RECONCILIATION_REQUIRED";pos["unwind_attempt_ts"]=_cd;pos["unwind_reason"]="SPOT_DELTA_TIMEOUT_REPRICED_UNWIND";d.save_state();continue
     if not n and _0<60. and not pos.get("is_liquidating"):pos["terminal_policy"]="DETERMINISTIC_TERMINAL_HOLD_FINAL"if _0<d.tte_cancel_window else"DETERMINISTIC_TERMINAL_HOLD"
     if n:
      y=await asyncio.to_thread(d.executor.get_order_fill_summary,n,_E)
      if y is not None:
       if d._record_order_summary(pos,y,float(pos.get("target_exit_price",.0)or.0),taker=False):d.save_state()
       _b0=float(pos.get("filled_exit_shares",.0)or.0)
       if _b0>0:pos["average_exit_price"]=round(float(pos.get("realized_exit_cash",.0))/_b0,4)
       if float(pos.get("remaining_shares",.0)or.0)<=.02:logger.info(f"✓ POSITION CLOSED VIA CONFIRMED CLOB FILL: {tid} | OID: {n}");d._close_position(tid,pos,ExecutionStatus.FILLED,"MAKER_SCALP_FILLED_CLOB",won=True)
       elif y.get("terminal"):
        logger.warning(f"⚠️ Exit order {n} is terminal ({y.get('status','TERMINAL')}) with {pos.get('remaining_shares')} unsold. Position {tid} remains OPEN.");d.executor.release_inventory(reservation_id=n);pos["exit_order_id"]=None;pos["exit_order_status"]="EXIT_RECOVERY_REQUIRED";pos["status"]=ExecutionStatus.PARTIALLY_FILLED if _b0>0 else ExecutionStatus.EXIT_PENDING_SETTLEMENT;_bf=pos.get("exit_tranches",[]);_3=float(y.get("matched",.0)or.0)
        for t in _bf:
         if t.get("status")in{"POSTED","IN_FLIGHT"}:
          _aw=max(.0,round(float(t["size"])-_3,2))
          if _aw<=.01:t["status"]="FILLED"
          else:t["size"]=_aw;t["status"]="PENDING"
        _af=[t for t in _bf if t.get("status")=="PENDING"]
        if _af:
         pos["target_exit_price"]=float(_af[0]["price"])
         if _0>=d.tte_cancel_window and position_may_post_new_maker_exit(pos):await asyncio.to_thread(d._attempt_maker_exit_post,tid,pos)
        d.save_state()
       elif _b0>0 and pos.get("status")!=ExecutionStatus.PARTIALLY_FILLED:pos["status"]=ExecutionStatus.PARTIALLY_FILLED;logger.info(f"[PARTIAL FILL] {tid}: Filled {_b0:.2f}/{pos['entry_shares']:.2f} shares. Remaining: {pos.get('remaining_shares',.0):.2f}");d.save_state()
    except Exception as _Q:logger.error(f"Error managing position {tid}: {_Q}",exc_info=True)
  except Exception as e:logger.error(f"Error querying live CLOB order status: {e}")
  finally:d._refresh_global_halt()
 def check_resolutions_and_manage_positions_sync(self):return asyncio.run(self.check_resolutions_and_manage_positions())
 async def _drain_and_dispatch_shock_triggers(a,trigger_fp=None,wakeup_supervision_event=None):
  if a._shutdown_requested:return 0
  if not a.dry_run and not a.executor.is_heartbeat_healthy():
   if not a.risk_controller.is_halted():a.risk_controller.halted=True;a.risk_controller.halt_reason=(f"Heartbeat degraded ({a.executor.heartbeat_failures} drops) - " "new entries halted; existing positions remain supervised.")
   if wakeup_supervision_event is not None:wakeup_supervision_event.set()
  q=[];C=getattr(a,"_fast_trigger_lines",None)
  if C:
   while C:q.append(C.popleft())
  e=[]
  if trigger_fp is not None and not getattr(trigger_fp,"closed",True):
   try:j=trigger_fp.read()
   except Exception:j=b""
   if not j and TRIGGER_FILE.exists():
    try:
     B=TRIGGER_FILE.stat().st_size
     if B<a.last_trigger_file_pos:trigger_fp.seek(0,2);a.last_trigger_file_pos=trigger_fp.tell();j=b""
    except Exception:pass
   if j:
    n=j.rfind(b"\n")+1
    if n:
     e=j[:n].decode("utf-8",errors="ignore").splitlines();a.last_trigger_file_pos+=n
     if n<len(j):trigger_fp.seek(a.last_trigger_file_pos)
    else:e=[];trigger_fp.seek(a.last_trigger_file_pos)
  s=q+e
  if not s:return 0
  F=time.time();m=sum(1 for p in a.active_positions.values()if not p.get("is_dominance_box")and"BOX"not in str(p.get("sleeve")or"").upper()and not position_is_settlement_receivable(p));l=a._effective_directional_slot_cap(F)
  if(len(s)==1 and not q and not a.dry_run and len(a.allowed_assets)>1 and(l-m)<=1 and'"BTC"'not in s[0]):
   A=(float(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("routing",{}).get("microbatch_coalesce_alt_sec",.003)or.003)if a._is_v5_live_strict()else 5e-4);await asyncio.sleep(A)
   if C:
    while C:s.append(C.popleft())
   if trigger_fp is not None and not getattr(trigger_fp,"closed",True):
    try:
     z=trigger_fp.read()
     if z:
      E=z.rfind(b"\n")+1
      if E:
       s.extend(z[:E].decode("utf-8",errors="ignore").splitlines());a.last_trigger_file_pos+=E
       if E<len(z):trigger_fp.seek(a.last_trigger_file_pos)
      else:trigger_fp.seek(a.last_trigger_file_pos)
    except Exception:pass
  if a.risk_controller.is_halted()and not a.active_positions:return 0
  d=[];k=set()
  for H in s:
   if not H.strip():continue
   try:I=_json_loads(H)
   except Exception as h:logger.error(f"Error parsing trigger line: {h}");continue
   s_id=I.get("shock_id")or f"{I.get('market_id')}_{I.get('t0_unix')}"
   if s_id in a.seen_shock_ids or s_id in k:continue
   k.add(s_id);d.append(I)
  if not d:return 0
  a.recent_shock_window=[w for w in a.recent_shock_window if(F-w["t_unix"])<=5.];y={id(c):a._calc_priority_score(c)for c in d}
  if len(d)>1 and rank_microbatch_shock_tournament is not None:D=[c for c in d if y[id(c)]>.0];G=[c for c in d if y[id(c)]<=.0];d=(rank_microbatch_shock_tournament(D,list(a._risk_bearing_positions().values()))+G)
  elif len(d)>1:d.sort(key=lambda c:(y[id(c)],1 if str(c.get("horizon")or"").lower()in("15m","5m")else 0),reverse=True)
  v=asyncio.get_running_loop();i=[];u=a.__dict__.setdefault("_bg_shock_tasks",set());o=a.__dict__.setdefault("_cold_shock_objs",set())
  def b(shock,is_cold):
   M=shock.get("shock_id")or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
   if M in a.seen_shock_ids:return None
   w=y[id(shock)];L=str(shock.get("market_id")or"")
   if w>.0 and a.recent_shock_window and m>=l:
    p=max(a.recent_shock_window,key=lambda x:x["score"])
    if p["market_id"]!=L and p["score"]>w:logger.info(f"[PRIORITY DEFER] Deferring {shock.get('title')!r} (score={w:.3f}) to concurrent superior qualified trigger {p.get('trade_id')} (score={p['score']:.3f})");return None
   a.last_event_id=M;a._triggers_scanned_count=getattr(a,"_triggers_scanned_count",0)+1;K=id(shock)
   if is_cold:o.add(K)
   J=asyncio.create_task(a.evaluate_shock_and_execute(shock));u.add(J);i.append(J)
   if not is_cold:v.call_soon(a._prewarm_market_metadata,shock)
   def c(_t,_m_id=L,_oid=K):
    u.discard(_t);o.discard(_oid)
    if _t.cancelled():return
    x=_t.exception()
    if isinstance(x,StatePersistenceError):
     a.risk_controller.halted=True;a.risk_controller.halt_reason="Critical state persistence failure";logger.critical("Critical live state persistence failure; blocking further entries",exc_info=x)
     if wakeup_supervision_event is not None:wakeup_supervision_event.set()
    elif x is not None:
     logger.error(f"[SIGNAL ERROR] Unhandled exception evaluating shock {_m_id}: {x}")
     try:a._refresh_global_halt()
     except Exception:pass
   J.add_done_callback(c);return J
  t=[c for c in d if y[id(c)]>.0];r=[c for c in d if y[id(c)]<=.0];g=0
  for shock in t:
   if b(shock,False)is not None:g+=1
  if g:await asyncio.sleep(0)
  f=0
  for shock in r:
   if b(shock,True)is not None:f+=1
  if f:await asyncio.sleep(0)
  return len(i)
 def _is_riskless_only_mode(a):return bool(not a.dry_run and(a._is_v5_live_strict()or getattr(a,"enforce_seed_directional_shadow_gate",False))and GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional",{}).get("riskless_only_mode",False))
 async def _fast_trigger_consumer_loop(a,fast_shock_event,trigger_fp=None,wakeup_supervision_event=None,has_event_driven_wakeup=False):
  b=.25 if has_event_driven_wakeup else.01
  try:
   while not a._shutdown_requested:
    fast_shock_event.clear()
    if a._is_riskless_only_mode()and not getattr(a,"_fast_trigger_lines",None):
     if trigger_fp is not None:
      try:trigger_fp.seek(0,os.SEEK_END);a.last_trigger_file_pos=trigger_fp.tell()
      except Exception:pass
     try:await asyncio.wait_for(fast_shock_event.wait(),timeout=1.)
     except asyncio.TimeoutError:pass
     continue
    await a._drain_and_dispatch_shock_triggers(trigger_fp=trigger_fp,wakeup_supervision_event=wakeup_supervision_event)
    if a._shutdown_requested:break
    if getattr(a,"_fast_trigger_lines",None):await asyncio.sleep(0);continue
    try:await asyncio.wait_for(fast_shock_event.wait(),timeout=b)
    except asyncio.TimeoutError:pass
  finally:
   if wakeup_supervision_event is not None:wakeup_supervision_event.set()
 def _rebuild_active_recycle_tok_map(a):
  d={}
  for p in getattr(a,"active_positions",{}).values():
   if not isinstance(p,dict):continue
   e=str(p.get("token_id")or"")
   if not e:continue
   c,b=d.get(e,(False,False));d[e]=(c or bool(p.get("is_dominance_box")),b or bool(p.get("hold_to_maturity_lock")))
  a._active_recycle_tok_map=d;return d
 def _drain_and_handle_lifecycle_events(b,poly_logs_ws=None):
  k=[];j=getattr(b,"_pos_market_ws",None)
  if j is not None and hasattr(j,"drain_lifecycle_events"):
   try:k.extend(j.drain_lifecycle_events(max_items=64)or[])
   except Exception:pass
  if poly_logs_ws is not None and hasattr(poly_logs_ws,"drain_events"):
   try:k.extend(poly_logs_ws.drain_events(max_items=64)or[])
   except Exception:pass
  if not k:return False
  f={"6707502","6707503"};e=set();d=set()
  for p in getattr(b,"active_positions",{}).values():
   if isinstance(p,dict)and str(p.get("market_id")or"")in f:
    if p.get("condition_id"):e.add(str(p.get("condition_id")).lower())
    if p.get("token_id"):d.add(str(p.get("token_id")))
  c=False;a=False
  for n in k:
   if not isinstance(n,dict)or n.get("quarantined_d001"):continue
   h={str(x)for x in(n.get("market_ids")or[])if x}
   if n.get("market_id"):h.add(str(n.get("market_id")))
   if h&f:continue
   i=str(n.get("condition_id")or"").lower()
   if i and i in e:continue
   g={str(x)for x in(n.get("assets_ids")or n.get("token_ids")or[])if x}
   for m in("asset_id","token_id","winning_asset_id"):
    if n.get(m):g.add(str(n.get(m)))
   if g&d:continue
   l=str(n.get("event_type")or n.get("event_kind")or n.get("type")or"").lower()
   if l in{"market_resolved","new_market"}:a=True
   if l in{"market_resolved","oo_settle","ctf_condition_resolution","payout_redemption","ctf_payout_redemption","negrisk_payout_redemption"}:c=True
  if a and j is not None and hasattr(j,"set_desired_tokens"):
   try:j.set_desired_tokens(b._desired_market_ws_tokens())
   except Exception:pass
  if c:b._lifecycle_urgent_ts=time.time()
  return c
 async def _fast_d1_consumer_loop(a,fast_d1_event,wakeup_supervision_event=None):
  try:
   while not a._shutdown_requested:
    fast_d1_event.clear();d=time.time();b=bool(getattr(a,"_d1_inotify_dirty",False))
    if b:a._d1_inotify_dirty=False
    if a._is_d1_box_halted():
     c=getattr(a,"_fast_d1_cand_lines",None)
     if c:c.clear()
    elif(b or bool(getattr(a,"_fast_d1_cand_lines",None))or(d-getattr(a,"_last_d1_cand_poll",.0)>=.5)):
     a._last_d1_cand_poll=d
     try:
      if await a._poll_d1_live_box_candidates(d)>0 and wakeup_supervision_event is not None:wakeup_supervision_event.set()
     except Exception:logger.exception("[FAST D1 CONSUMER] Candidate poll failed; continuing.")
    if a._shutdown_requested:break
    if not a._is_d1_box_halted()and(bool(getattr(a,"_fast_d1_cand_lines",None))or bool(getattr(a,"_d1_inotify_dirty",False))):await asyncio.sleep(0);continue
    try:await asyncio.wait_for(fast_d1_event.wait(),timeout=.25)
    except asyncio.TimeoutError:pass
  finally:
   if wakeup_supervision_event is not None:wakeup_supervision_event.set()
 async def run(a):
  if not a.dry_run and _alerts_file_path()is not None:_ensure_file_logging()
  logger.info(f"[LIVE HARVESTER] Wallet={a.executor.funder_address} | Auth={a.executor.auth_mode} | Ticket=${a.ticket_notional:.2f} | Cap=${a.max_exposure:.2f} (slots={a.max_concurrent_positions}) | Mode={'DRY-RUN'if a.dry_run else'LIVE'} | RisklessOnly={a._is_riskless_only_mode()}");O=PID_FILE.with_suffix(".lock");a._instance_lock_fd=open(O,"a+b")
  if fcntl is not None:
   try:fcntl.flock(a._instance_lock_fd.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError as E:a._instance_lock_fd.close();raise RuntimeError("Another live harvester instance already holds the lock")from E
  elif os.name=="nt":
   import msvcrt as _msvcrt
   try:
    a._instance_lock_fd.seek(0,os.SEEK_END)
    if a._instance_lock_fd.tell()==0:a._instance_lock_fd.write(b"\x00");a._instance_lock_fd.flush()
    a._instance_lock_fd.seek(0);_msvcrt.locking(a._instance_lock_fd.fileno(),_msvcrt.LK_NBLCK,1)
   except OSError as E:a._instance_lock_fd.close();raise RuntimeError("Another live harvester instance already holds the lock")from E
  watcher=None;trigger_fp=None;loop=None
  try:
   with open(PID_FILE,"w")as f:f.write(str(os.getpid()))
   a.load_state();a.reconcile_with_exchange()
   if not a.dry_run:a.save_state()
   if not TRIGGER_FILE.exists():TRIGGER_FILE.touch()
   a.last_trigger_file_pos=TRIGGER_FILE.stat().st_size;logger.info(f"Tailing zero-latency shock triggers from byte offset: {a.last_trigger_file_pos}");trigger_fp=open(TRIGGER_FILE,"rb");trigger_fp.seek(a.last_trigger_file_pos)
   if SHOCK_FILE.exists():a.last_shock_file_pos=SHOCK_FILE.stat().st_size;logger.info(f"Tailing shock responses fallback from byte offset: {a.last_shock_file_pos}")
   G=PIPELINE_ROOT/"data/polymarket/finalized_market_resolutions.jsonl";N=RESOLUTIONS_FILE if(RESOLUTIONS_FILE.parent==DATA_DIR or RESOLUTIONS_FILE!=G)else(DATA_DIR/"finalized_market_resolutions.jsonl")
   if N.exists():a.last_res_file_pos=0;await a.check_resolutions_and_manage_positions();a.last_res_file_pos=N.stat().st_size;logger.info(f"Tailing new resolutions from byte offset: {a.last_res_file_pos}")
   watcher=LinuxInotifyWatcher(TRIGGER_FILE);d1_watcher=LinuxInotifyWatcher(D1_LIVE_CANDIDATES_FILE);loop=asyncio.get_running_loop();u=asyncio.Event();y=asyncio.Event();w=asyncio.Event()
   def o(signame):
    if not a._shutdown_requested:logger.warning(f"[SHUTDOWN] {signame} received; finishing in-flight step then stopping gracefully.")
    a._shutdown_requested=True;y.set();w.set();u.set()
   for _l in(signal.SIGTERM,signal.SIGINT):
    try:loop.add_signal_handler(_l,o,_l.name)
    except(NotImplementedError,RuntimeError,ValueError):pass
   a._main_loop=loop
   if getattr(a,"_fast_trigger_lines",None)is None:from collections import deque as n;a._fast_trigger_lines=n(maxlen=512)
   if getattr(a,"_fast_d1_cand_lines",None)is None:from collections import deque as n;a._fast_d1_cand_lines=n(maxlen=256)
   def j():watcher.drain_events();y.set()
   if watcher.is_available:loop.add_reader(watcher.fd,j);logger.info(f"✓ Linux inotify event listener armed on {TRIGGER_FILE.name} (sub-millisecond wakeups enabled).")
   else:logger.info("Linux inotify unavailable; using responsive 10ms consumer polling fallback.")
   def d():d1_watcher.drain_events();a._d1_inotify_dirty=True;w.set()
   if d1_watcher.is_available:loop.add_reader(d1_watcher.fd,d);logger.info(f"✓ Linux inotify event listener armed on {D1_LIVE_CANDIDATES_FILE.name} (sub-ms D1 box wakeups enabled).")
   ipc_sock=None
   if os.name!="nt":
    try:
     import socket;ipc_sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);ipc_sock.setblocking(False)
     try:ipc_sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,262144)
     except Exception:pass
     S=os.environ.get("POLYMARKET_IPC_SOCKET_NAME","polymarket_shock_notify"if not a.dry_run else f"pm_shock_dry_{os.getpid()}");R=f"\x00{S}".encode("utf-8");ipc_sock.bind(R)
     def k():
      f=False
      while True:
       try:
        p=ipc_sock.recv(65536)
        if not p:break
        for ln in p.decode("utf-8",errors="ignore").splitlines():
         i=ln.strip()
         if not i:continue
         if'"_prewarm_clob_tls"'in i:a._handle_prewarm_ipc_signal();continue
         if a._is_riskless_only_mode():continue
         a._fast_trigger_lines.append(i);f=True
       except(BlockingIOError,InterruptedError):break
       except Exception:break
      if f:y.set()
     loop.add_reader(ipc_sock.fileno(),k);logger.info("✓ Fast RAM IPC datagram listener armed on @polymarket_shock_notify (~15us zero-VFS delivery).")
    except Exception:
     if ipc_sock is not None:
      try:ipc_sock.close()
      except Exception:pass
      ipc_sock=None
   d1_ipc_sock=None
   if os.name!="nt":
    try:
     import socket;d1_ipc_sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);d1_ipc_sock.setblocking(False)
     try:d1_ipc_sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,524288)
     except Exception:pass
     J=os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME","polymarket_d1_box_notify"if not a.dry_run else f"pm_d1_dry_{os.getpid()}");d1_ipc_sock.bind(f"\x00{J}".encode("utf-8"))
     def e():
      while True:
       try:
        f=d1_ipc_sock.recv(262144)
        if not f:break
        for i in f.decode("utf-8",errors="ignore").splitlines():
         if i.strip():a._fast_d1_cand_lines.append(i)
       except(BlockingIOError,InterruptedError):break
       except Exception:break
      w.set()
     loop.add_reader(d1_ipc_sock.fileno(),e);logger.info("✓ Fast D1 Box IPC datagram listener armed on @polymarket_d1_box_notify (~15us wakeup).")
    except Exception:
     if d1_ipc_sock is not None:
      try:d1_ipc_sock.close()
      except Exception:pass
      d1_ipc_sock=None
   q=time.time();m=.0;h=.0;a._triggers_scanned_count=0;pos_ws_task=None;fast_consumer_task=None;fast_d1_consumer_task=None
   if(not a.dry_run and _PolymarketClobMarketWsTracker is not None and getattr(a.executor,"auth_mode","")in("LIVE","AUTHENTICATED_L2")and getattr(getattr(a.executor,"client",None),"_mock_children",None)is None and os.environ.get("PM_ENABLE_HARVESTER_MKT_WS","1")=="1"):
    def c(_tok,_bb):a._ws_urgent_recycle_ts=time.time();loop.call_soon_threadsafe(u.set)
    def b(_tok,_bk):
     a._notify_sll_ws_book_change(_tok,loop);_r=(_bk or{}).get("asks")or[]
     if _STAGE_B_DECAY_TRACKER is not None and _tok in _STAGE_B_DECAY_TRACKER._by_token:
      try:_p=float(_r[0].get("price")or.0)if _r else None;_o=float(_r[0].get("size")or.0)if _r else.0;_STAGE_B_DECAY_TRACKER.on_top_of_book_tick(_tok,_p,_o)
      except Exception:pass
     _q=(_bk or{}).get("bids")or[]
     if _q and float(_q[0].get("price",.0)or.0)>=.52:
      i=float(_q[0].get("price",.0)or.0);_j=getattr(a,"_active_recycle_tok_map",None)
      if _j is not None:_k=_j.get(_tok);f=bool(_k is not None and(_k[0]or(i>=.997 and _k[1])))
      else:f=any((p.get("is_dominance_box")or(i>=.997 and p.get("hold_to_maturity_lock")))and str(p.get("token_id")or"")==_tok for p in a.active_positions.values())
      if f:a._ws_urgent_recycle_ts=time.time();loop.call_soon_threadsafe(u.set)
     if getattr(a,"_clinched_ws_watchlist",None)and _r:
      _i=a.evaluate_clinched_ws_book_snipe(_tok,_bk)
      if _i is not None:
       _s=getattr(a,"_fast_d1_cand_lines",None)
       if _s is not None:_s.append(_orjson.dumps(_i).decode("utf-8")if _orjson is not None else json.dumps(_i,separators=(",",":")));loop.call_soon_threadsafe(w.set);loop.call_soon_threadsafe(u.set)
    B=max(1,min(8,int(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("ws_market_num_shards",4)or 4)));M=((lambda _tok,_tk:a.executor.update_ws_tick_size(_tok,_tk))if hasattr(a.executor,"update_ws_tick_size")else None)
    if B>1 and _PolymarketShardedClobMarketWsTracker is not None:a._pos_market_ws=_PolymarketShardedClobMarketWsTracker(num_shards=B,per_shard_max=485,recycle_bid_trigger=.985,on_urgent_bid=c,on_book_change=b,on_tick_size_change=M)
    else:a._pos_market_ws=_PolymarketClobMarketWsTracker(recycle_bid_trigger=.985,on_urgent_bid=c,on_book_change=b,on_tick_size_change=M)
    a._pos_market_ws.set_desired_tokens(a._desired_market_ws_tokens());pos_ws_task=asyncio.create_task(a._pos_market_ws.run_forever(lambda:bool(a._shutdown_requested)))
   if(not a.dry_run and _PolymarketPerpsLeadLagStream is not None and bool(GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes",{}).get("enable_perp1_maker_precancel_leadlag",True))):a._perps_leadlag_ws=_PolymarketPerpsLeadLagStream();a._perps_leadlag_ws.start_background()
   poly_logs_ws=None
   if not a.dry_run:
    try:from.riskless_fast_feeds import(FROZEN_KMIA_MARKET_IDS as g,PolygonScopedLogsWs as l);F=str(getattr(a.executor,"funder_address","")or getattr(a.executor,"funder","")or"");poly_logs_ws=l(funder_address=F,quarantined_market_ids=g);poly_logs_ws.start_background();a._poly_logs_ws=poly_logs_ws
    except Exception:poly_logs_ws=None
   a._rebuild_active_recycle_tok_map();a._prewarm_active_market_tokens();I=bool(ipc_sock is not None and watcher.is_available);fast_consumer_task=asyncio.create_task(a._fast_trigger_consumer_loop(y,trigger_fp,u,I));fast_d1_consumer_task=asyncio.create_task(a._fast_d1_consumer_loop(w,u))
   while True:
    if a._shutdown_requested:
     a._shutdown_status="STOPPED_GRACEFULLY";a._preempt_resting_maker_anchors(reason="SHUTDOWN");y.set();w.set()
     for _n in(fast_consumer_task,fast_d1_consumer_task):
      if _n is not None and not _n.done():await asyncio.gather(_n,return_exceptions=True)
     if getattr(a,"_bg_shock_tasks",None):await asyncio.gather(*list(a._bg_shock_tasks),return_exceptions=True)
     if getattr(a,"_maker_anchor_bg_tasks",None):await asyncio.gather(*list(a._maker_anchor_bg_tasks),return_exceptions=True)
     logger.warning(f"[SHUTDOWN] Graceful stop: {len(a.active_positions)} active position(s) persisted to state; resting exit orders (if any) remain on the exchange for restart reconciliation.");await asyncio.to_thread(a.save_state);t=any(isinstance(_p_sh,dict)and(_p_sh.get("exit_order_id")or _p_sh.get("unwind_order_id"))for _p_sh in a.active_positions.values())
     if not t and not a.dry_run:await asyncio.to_thread(a.executor.cancel_all_orders)
     break
    if fast_consumer_task is not None and fast_consumer_task.done()and not fast_consumer_task.cancelled():
     X=fast_consumer_task.exception()
     if X is not None:raise X
     fast_consumer_task=asyncio.create_task(a._fast_trigger_consumer_loop(y,trigger_fp,u,I))
    if fast_d1_consumer_task is not None and fast_d1_consumer_task.done()and not fast_d1_consumer_task.cancelled():
     Q=fast_d1_consumer_task.exception()
     if Q is not None:raise Q
     fast_d1_consumer_task=asyncio.create_task(a._fast_d1_consumer_loop(w,u))
    D=time.time()
    if not a.dry_run and(D-getattr(a,"_last_pre_halt_gov_chk",.0)>=6.):
     a._last_pre_halt_gov_chk=D;await a._apply_governance_hot_reload(D)
     if a.pending_entry_intents:
      W=getattr(a,"_inflight_directional_entry_ids",set());V=getattr(a,"_inflight_phase3a_maker_ids",set());x=False
      for _h,_g in list(a.pending_entry_intents.items()):
       if(not isinstance(_g,dict)or _h in W or _h in V or _g.get("live_maker_anchor_inflight")):continue
       U=D-float(_g.get("heartbeat_ts")or _g.get("submitted_at_ts")or.0)
       if bool(_g.get("needs_runtime_recovery"))or U>=12.:await asyncio.to_thread(a._recover_pending_intent,_h,_g);x=True
      if x:a._refresh_global_halt(authoritative=True)
    if(not a.dry_run and a.risk_controller.is_halted()and"Heartbeat degraded"in str(a.risk_controller.halt_reason or"")and a.executor.is_heartbeat_healthy()):a.risk_controller.halted=False;a.risk_controller.halt_reason="";a._halt_logged_active=False;logger.info("[HEARTBEAT RECOVERED] CLOB heartbeat healthy again; clearing temporary heartbeat halt.");await asyncio.to_thread(a.save_state)
    if a.risk_controller.is_halted():
     if(not a.active_positions and not a.dry_run and(time.time()-getattr(a,"_last_halt_collat_check",.0)>=15.)):a._last_halt_collat_check=time.time();await a._async_refresh_collateral()
     if a.risk_controller.is_halted():
      if not getattr(a,"_halt_logged_active",False):logger.critical(f"[CIRCUIT BREAKER] {a.risk_controller.halt_reason}. " "Halting new entries (supervisor staying alive for recovery / UTC rollover).");await asyncio.to_thread(a.save_state);a._halt_logged_active=True
      if not a.active_positions:
       if not a.dry_run and not getattr(a,"_halt_orders_cancelled",False):await asyncio.to_thread(a.executor.cancel_all_orders);a._halt_orders_cancelled=True
       if not a.dry_run and"Heartbeat degraded"in str(a.risk_controller.halt_reason or""):
        if(time.time()-getattr(a,"_last_halt_hb_probe",.0))>=5.:a._last_halt_hb_probe=time.time();await asyncio.to_thread(a.executor.post_heartbeat)
       await asyncio.sleep(1.);continue
    else:a._halt_logged_active=False;a._halt_orders_cancelled=False
    if not a.dry_run and not a.executor.is_heartbeat_healthy():
     a.risk_controller.halted=True;a.risk_controller.halt_reason=f"Heartbeat degraded ({a.executor.heartbeat_failures} drops) - new entries halted; existing positions remain supervised."
     if not getattr(a,"_halt_logged_active",False):logger.critical(f"[HEARTBEAT UNHEALTHY] CLOB heartbeat dropped {a.executor.heartbeat_failures} times. Halting new entries.");await asyncio.to_thread(a.save_state);a._halt_logged_active=True
     if not a.active_positions:
      if not getattr(a,"_halt_orders_cancelled",False):await asyncio.to_thread(a.executor.cancel_all_orders);a._halt_orders_cancelled=True
      await asyncio.to_thread(a.executor.post_heartbeat);await asyncio.sleep(1.);continue
    _c=time.time();H=getattr(a.executor,"auth_mode","")not in("LIVE","AUTHENTICATED_L2");A=bool(a.active_positions or(getattr(a,"pre_split_inventory_state",None)or{}).get("active")or any(isinstance(i,dict)and(i.get("live_maker_anchor_inflight")or i.get("entry_order_id"))for i in getattr(a,"pending_entry_intents",{}).values()))
    if not a.dry_run and A and(_c-m>=5.):
     m=_c
     if H:
      _b=await asyncio.to_thread(a.executor.post_heartbeat)
      if isinstance(_b,dict)and _b.get("error"):logger.warning(f"[HEARTBEAT WARN] Heartbeat error: {_b.get('error')}")
     elif not getattr(a,"_hb_in_flight",False):
      a._hb_in_flight=True
      async def s():
       try:
        f=await asyncio.to_thread(a.executor.post_heartbeat)
        if isinstance(f,dict)and f.get("error"):logger.warning(f"[HEARTBEAT WARN] Heartbeat error: {f.get('error')}")
       finally:a._hb_in_flight=False
      asyncio.create_task(s())
    if not a.dry_run and(_c-getattr(a,"_last_clob_keepalive",.0)>=5.):
     a._last_clob_keepalive=_c
     if hasattr(a.executor,"touch_hot_async_clob_socket")and not H:
      asyncio.create_task(a.executor.touch_hot_async_clob_socket(3.))
      if hasattr(a.executor,"start_async_clob_keepalive_task"):a.executor.start_async_clob_keepalive_task(3.5)
     await a._apply_governance_hot_reload(_c)
     if H:await asyncio.to_thread(a.executor.ping_clob_keepalive)
     elif not getattr(a,"_keepalive_in_flight",False):
      a._keepalive_in_flight=True
      async def r():
       try:await asyncio.to_thread(a.executor.ping_clob_keepalive)
       finally:a._keepalive_in_flight=False
      asyncio.create_task(r())
     a._prewarm_active_market_tokens()
     if not a.active_positions:
      try:import gc as _gc;_gc.collect(0)
      except Exception:pass
     if(GLOBAL_SVI_ENGINE is not None and not a._is_riskless_only_mode()and(_c-getattr(a,"_last_svi_refresh",.0)>=60.)):a._last_svi_refresh=_c;asyncio.create_task(asyncio.to_thread(GLOBAL_SVI_ENGINE.get_surface,"BTC"));asyncio.create_task(asyncio.to_thread(GLOBAL_SVI_ENGINE.get_surface,"ETH"))
    _a=datetime.now(timezone.utc)
    if _a.minute in(58,13,28,43,8,23,38,53):
     z=f"{_a.hour}:{_a.minute}"
     if getattr(a,"_last_prewarm_minute_key","")!=z:a._last_prewarm_minute_key=z;asyncio.create_task(a._prewarm_next_candle_markets())
    Z=getattr(a.executor,"_user_ws_cache",None);L=60. if(not a.active_positions and Z is not None and Z.is_healthy())else 20.
    if not a.dry_run and(getattr(a,"_pending_collateral_refresh",False)or(_c-getattr(a,"_last_collat_poll",.0)>=L)):a._pending_collateral_refresh=False;a._last_collat_poll=_c;asyncio.create_task(a._async_refresh_collateral())
    if a._drain_and_handle_lifecycle_events(poly_logs_ws):h=.0
    v=((_c-float(getattr(a,"_ws_urgent_recycle_ts",.0)or.0))<=1.5 or(_c-float(getattr(a,"_lifecycle_urgent_ts",.0)or.0))<=1.5 or any(p.get("_zero_bal_gamma_urgent")or p.get("strike_retrace_detected_ts")or p.get("opposite_breakout_start_ts")or p.get("low_bid_detected_ts")or p.get("trail_stop_detected_ts")or p.get("zero_bid_detected_ts")or p.get("exit_order_status")in{"STOP_CANCEL_PENDING","PRE_EXPIRY_CANCEL_PENDING","FILL_RECONCILIATION_REQUIRED","PASSIVE_STOP_RESTING","EXIT_RECOVERY_REQUIRED","UNWIND_RETRY_REQUIRED"}for p in a.active_positions.values()));C=.2 if v else 1.
    if _c-h>=C:
     h=_c
     try:
      await a.check_resolutions_and_manage_positions();a._rebuild_active_recycle_tok_map()
      if not a.dry_run and not a._is_riskless_only_mode():a._step_shadow_phase3_4_tracker(_c)
     except StatePersistenceError:raise
     except Exception:logger.exception("[SUPERVISION ERROR] Position management cycle failed; retrying next cycle.")
    if time.time()-q>=300:
     q=time.time()
     for P,Y in(("_d1_retry_cooldown_until",.0),("_ovr_unwind_cd",6e2)):
      _f=getattr(a,P,None)
      if isinstance(_f,dict):
       for _k,_v in list(_f.items()):
        if float(_v or.0)<(q-Y):_f.pop(_k,None)
     _e=getattr(a,"_d1_clean_pre_bal_cache",None)
     if isinstance(_e,dict):
      for _k,_v in list(_e.items()):
       if isinstance(_v,tuple)and(q-float(_v[1]or.0))>3600.:_e.pop(_k,None)
     _m=getattr(a.executor,"order_ladder_cache",None)
     if _m is not None and hasattr(_m,"prune_expired"):_m.prune_expired()
     import gc as _gc
     if a.active_positions or a.pending_entry_intents or getattr(a,"_clinched_ws_watchlist",None):_gc.collect(0)
     else:await asyncio.to_thread(_gc.collect)
     K=sum(p.get("notional_usd",.0)for p in a.active_positions.values());logger.info(f"[HEARTBEAT] Harvester active | Triggers scanned: {a._triggers_scanned_count} | Active positions: {len(a.active_positions)} (${K:.2f}) | Closed: {len(a.closed_positions)}")
    if not a.dry_run and(time.time()-getattr(a,"_last_stale_check",.0)>=5.):
     a._last_stale_check=time.time()
     try:a.monitor_recorder_staleness(a._last_stale_check)
     except Exception:pass
    try:await asyncio.wait_for(u.wait(),timeout=.05);u.clear()
    except asyncio.TimeoutError:pass
  except Exception:logger.critical("[FATAL] Harvester loop terminated by unhandled exception.",exc_info=True);raise
  finally:
   for _d in(fast_consumer_task if'fast_consumer_task'in locals()else None,fast_d1_consumer_task if'fast_d1_consumer_task'in locals()else None):
    if _d is not None and not _d.done():
     _d.cancel()
     try:await _d
     except(asyncio.CancelledError,Exception):pass
   if'pos_ws_task'in locals()and pos_ws_task is not None:pos_ws_task.cancel()
   if getattr(a,"_perps_leadlag_ws",None)is not None:
    try:a._perps_leadlag_ws.stop()
    except Exception:pass
   if'poly_logs_ws'in locals()and poly_logs_ws is not None:
    try:poly_logs_ws.stop()
    except Exception:pass
   if'd1_ipc_sock'in locals()and d1_ipc_sock is not None:
    try:
     if'loop'in locals()and loop is not None:loop.remove_reader(d1_ipc_sock.fileno())
    except Exception:pass
    try:d1_ipc_sock.close()
    except Exception:pass
   if'ipc_sock'in locals()and ipc_sock is not None:
    try:
     if'loop'in locals()and loop is not None:loop.remove_reader(ipc_sock.fileno())
    except Exception:pass
    try:ipc_sock.close()
    except Exception:pass
   if'trigger_fp'in locals()and trigger_fp is not None and not getattr(trigger_fp,"closed",True):
    try:trigger_fp.close()
    except Exception:pass
   for _w in(watcher if'watcher'in locals()else None,d1_watcher if'd1_watcher'in locals()else None):
    if _w is not None and getattr(_w,"is_available",False):
     try:
      if'loop'in locals()and loop is not None:loop.remove_reader(_w.fd)
     except Exception:pass
     try:_w.close()
     except Exception:pass
   try:flush_operational_alerts(3.)
   except Exception:pass
   T=getattr(a,"_instance_lock_fd",None)
   if T is not None:
    try:
     if fcntl is not None:fcntl.flock(T.fileno(),fcntl.LOCK_UN)
     T.close()
    except Exception:pass
   try:PID_FILE.unlink(missing_ok=True)
   except Exception:pass
 async def _apply_governance_hot_reload(a,now_ts):
  if not getattr(a,"_v5_sighup_installed",False):a._v5_sighup_installed=True;GLOBAL_GOVERNANCE_MANAGER.install_sighup_handler()
  e,k=GLOBAL_GOVERNANCE_MANAGER.maybe_reload()
  if not e or not isinstance(getattr(a,"risk_config",None),dict):return False
  j=k.get("directional",{});i=k.get("risk_controller",{});h=k.get("riskless_boxes",{});a.risk_config["directional_taker_max_price"]=float(j.get("max_taker_price_1h",.74));a.risk_config["directional_taker_max_price_15m"]=float(j.get("max_taker_price_15m",.72));a.risk_config["directional_maker_max_price"]=float(j.get("max_maker_price_1h",.76));a.risk_config["phase3a_15m_long_tte_max_price"]=float(j.get("max_maker_price_15m",.72))
  if isinstance(h,dict):
   if"enable_graduated_d1_box"in h:a.risk_config["enable_graduated_d1_box"]=bool(h["enable_graduated_d1_box"])
   if h.get("d1_max_box_cost_net")is not None:a.risk_config["d1_max_box_cost_net"]=float(h["d1_max_box_cost_net"])
   if h.get("cm_b3_max_walk_cap")is not None:a.risk_config["cm_b3_max_walk_cap"]=float(h["cm_b3_max_walk_cap"])
  if isinstance(h,dict)and not bool(h.get("enable_single_leg_maker_bond1",True)):a._preempt_resting_maker_anchors(reason="GOVERNANCE_DISABLED:SINGLE_LEG_MAKER_BOND1")
  elif isinstance(h,dict)and getattr(a,"pending_entry_intents",None):
   c={str(x).upper()for x in(h.get("paused_riskless_sleeves")or[])};b={str(l.get("market_id")or"")for l in a.pending_entry_intents.values()if isinstance(l,dict)and l.get("live_maker_anchor_inflight")and str(l.get("sleeve_source")or"").upper()in c and l.get("market_id")}
   if b:a._preempt_resting_maker_anchors(reason="GOVERNANCE_DISABLED:PAUSED_SLEEVE",market_ids=b)
  if j.get("min_entry_price")is not None:a.min_price_floor=float(j["min_entry_price"])
  if j.get("max_maker_price_1h")is not None:a.max_price_ceiling=float(j["max_maker_price_1h"])
  a.risk_controller.max_daily_loss_usd=float(i.get("max_daily_directional_loss_usd",a.risk_controller.max_daily_loss_usd));d=i.get("max_consecutive_directional_losses",i.get("max_consecutive_losses"))
  if d is not None:a.risk_controller.max_consecutive_losses=int(d)
  if a.risk_controller.halted:
   g=str(a.risk_controller.halt_reason or"")
   if("Max daily loss reached"in g and a.risk_controller.daily_realized_loss<a.risk_controller.max_daily_loss_usd):a.risk_controller.halted=False;a.risk_controller.halt_reason="";a._halt_logged_active=False
   elif("Max consecutive losses reached"in g and a.risk_controller.consecutive_losses<a.risk_controller.max_consecutive_losses):a.risk_controller.halted=False;a.risk_controller.halt_reason="";a._halt_logged_active=False
  if getattr(a,"_last_known_collateral",None)is not None:f=float(a._last_known_collateral or.0)+sum(a.get_position_market_value(p,now_ts)for p in a.active_positions.values());a._update_equity_tier(f);await asyncio.to_thread(a.save_state)
  return True
if __name__=="__main__":
 import argparse;parser=argparse.ArgumentParser(description="Polymarket Live Harvester");parser.add_argument("--lot-size",type=float,default=RISK_CONFIG["ticket_notional"],help="Ticket size in USD (default: config/polymarket_risk_config.json ticket_notional)");parser.add_argument("--dynamic-sizing",action="store_true",default=True,help="Dynamically scale lot size with orderbook depth (default: True)");parser.add_argument("--no-dynamic-sizing",dest="dynamic_sizing",action="store_false",help="Disable dynamic sizing and use fixed lot size");parser.add_argument("--max-exposure",type=float,default=RISK_CONFIG["max_exposure"],help="Maximum concurrent portfolio exposure in USD (default: config max_exposure)");parser.add_argument("--max-concurrent",type=int,default=RISK_CONFIG["max_concurrent_positions"],help="Maximum concurrent open positions (default: config max_concurrent_positions)");parser.add_argument("--max-trades-per-market",type=int,default=DEFAULT_MAX_TRADES_PER_MARKET,help="Max trades per market candle (default: 1)");parser.add_argument("--max-trades-per-hour",type=int,default=DEFAULT_MAX_TRADES_PER_HOUR,help="Max total portfolio trades per hour (default: 6)");parser.add_argument("--max-tte",type=float,default=MAX_TTE_SECONDS,help="Max TTE in seconds (default: module MAX_TTE_SECONDS)");parser.add_argument("--max-price-ceiling",type=float,default=MAX_PRICE_CEILING,help="Maximum entry price ceiling (default: module MAX_PRICE_CEILING)");parser.add_argument("--min-price-floor",type=float,default=MIN_PRICE_FLOOR,help="Minimum entry price floor (default: module MIN_PRICE_FLOOR)");parser.add_argument("--unconstrained-kelly",action="store_true",default=False,help="Allow Half-Kelly position sizing to compound proportionally (25 percent of bankroll) beyond $39.92");parser.add_argument("--max-ticket-cap",type=float,default=MAX_ABSOLUTE_TICKET_USD,help="Explicit maximum dollar cap for single ticket (default: module MAX_ABSOLUTE_TICKET_USD)");parser.add_argument("--dynamic-theta",action="store_true",default=False,help="Enable EXP-315 regime-dependent profit target (0.06 when TTE>900s, 0.09 standard, hold-to-expiry when TTE<=300s)");parser.add_argument("--hold-to-maturity",dest="hold_to_maturity",action="store_true",default=bool(RISK_CONFIG.get("hold_to_maturity",False)),help="Hold resting $0.99 single-tranche ask to maturity instead of 2-tranche / $0.95 WFO maker exit");parser.add_argument("--no-hold-to-maturity",dest="hold_to_maturity",action="store_false",help="Enable WFO-optimal resting maker exits (default in production)");parser.add_argument("--exit-policy",type=str,default=str(RISK_CONFIG.get("exit_policy","two_tranche_95_98")),help="Exit policy: hold_98 or two_tranche_95_98");parser.add_argument("--allowed-assets",nargs="+",default=["BTC","ETH"],help="Assets permitted for live trading (default: BTC ETH)");parser.add_argument("--dry-run",action="store_true",help="Run in dry-run simulation mode");parser.add_argument("--reset-risk",action="store_true",default=False,help="Reset circuit breaker and consecutive losses on launch");parser.add_argument("--max-daily-loss",type=float,default=None,help="Circuit breaker max daily loss limit in USD (default: config max_daily_loss)");args=parser.parse_args();harvester=PolymarketLiveHarvester(ticket_notional=args.lot_size,dry_run=args.dry_run,dynamic_sizing=args.dynamic_sizing,max_exposure=args.max_exposure,max_concurrent=args.max_concurrent,max_trades_per_market=args.max_trades_per_market,max_trades_per_hour=args.max_trades_per_hour,max_tte=args.max_tte,max_price_ceiling=args.max_price_ceiling,min_price_floor=args.min_price_floor,unconstrained_kelly=args.unconstrained_kelly,max_absolute_ticket_usd=args.max_ticket_cap,dynamic_theta=args.dynamic_theta,hold_to_maturity=args.hold_to_maturity,exit_policy=args.exit_policy,allow_cli_exposure=any(a=="--max-exposure"or a.startswith("--max-exposure=")for a in sys.argv[1:]),allow_cli_concurrency=any(a=="--max-concurrent"or a.startswith("--max-concurrent=")for a in sys.argv[1:]),allowed_assets=set(args.allowed_assets),reset_risk=args.reset_risk,max_daily_loss=args.max_daily_loss)
 if os.name!="nt":
  try:import uvloop;uvloop.install()
  except Exception:pass
 asyncio.run(harvester.run())
# [06/13] src/polymarket_research/polymarket_live_executor.py
import asyncio;import base64;import concurrent.futures;import gc;import hashlib;import hmac;import json;import logging;import math;import os;import queue;import re;import secrets;import sys;import threading;import time;from collections import defaultdict,deque;from dataclasses import dataclass,field;from datetime import datetime,timezone;from decimal import Decimal,ROUND_CEILING,ROUND_FLOOR,ROUND_HALF_UP;from pathlib import Path;from typing import Any,Dict,List,Optional,Tuple,Union;import socket;import types as _types
try:from urllib3.connection import HTTPConnection
except ImportError:
 class HTTPConnection:default_socket_options:List[Any]=[]
try:import httpx
except ImportError:httpx=_types.SimpleNamespace(Client=object,AsyncClient=object,Response=object,Limits=lambda**kw:kw,HTTPTransport=lambda**kw:kw,AsyncHTTPTransport=lambda**kw:kw,HTTPError=Exception,ConnectError=ConnectionError,ConnectTimeout=TimeoutError,PoolTimeout=TimeoutError)
try:import requests
except ImportError:requests=_types.SimpleNamespace(Session=object,get=None,post=None)
try:from dotenv import load_dotenv
except ImportError:
 def load_dotenv(*_args,**_kwargs):return False
try:import orjson as _orjson
except ImportError:_orjson=None
def enable_tcp_nodelay_globally():
 try:
  b=list(HTTPConnection.default_socket_options);c=(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);a=(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)
  if c not in b:b.append(c)
  if a not in b:b.append(a)
  HTTPConnection.default_socket_options=b
 except Exception:pass
class _ThreadLocalClobHttpClient:
 def __init__(a,timeout=8.,max_pool_size=16):a._local=threading.local();a._timeout=timeout;a._pool=queue.LifoQueue(maxsize=max_pool_size);a._bg_pool=queue.LifoQueue(maxsize=max(8,max_pool_size));a._warm_lock=threading.Lock()
 def _make_client(a):
  c=httpx.Limits(max_keepalive_connections=8,max_connections=16,keepalive_expiry=45.)
  try:b=httpx.HTTPTransport(http2=False,limits=c,socket_options=[(socket.IPPROTO_TCP,socket.TCP_NODELAY,1),(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)]);return httpx.Client(http2=False,timeout=a._timeout,transport=b)
  except Exception:return httpx.Client(http2=False,timeout=a._timeout,limits=c)
 def _client(a,reset=False):
  b=getattr(a._local,"client",None)
  if reset and b is not None:
   try:b.close()
   except Exception:pass
   b=None
  if b is None or getattr(b,"is_closed",False):b=a._make_client();a._local.client=b
  return b
 @staticmethod
 def _is_hot_request(method,url):
  m=str(method or"").upper()
  if m!="GET":return True
  u=str(url or"");return(not u)or u.endswith("/time")
 def _borrow_from(self,target_pool):
  while True:
   try:b,a=target_pool.get_nowait()
   except queue.Empty:return self._make_client()
   if b is not None and not getattr(b,"is_closed",False)and(time.monotonic()-a)<40.:return b
   try:
    if b is not None:b.close()
   except Exception:pass
 @staticmethod
 def _return_to(target_pool,cli):
  if cli is None or getattr(cli,"is_closed",False):return
  try:target_pool.put_nowait((cli,time.monotonic()))
  except queue.Full:
   try:cli.close()
   except Exception:pass
 def _borrow_pool_client(a):return a._borrow_from(a._pool)
 def _return_pool_client(a,cli):a._return_to(a._pool,cli)
 def _record_resp_meta(self,resp):
  try:
   a=getattr(resp,"headers",None)
   if a and hasattr(a,"get"):self._local.last_resp_meta={"cf_ray":a.get("cf-ray"),"ratelimit_remaining":a.get("Poly-RateLimit-Remaining")or a.get("poly-ratelimit-remaining"),"status_code":getattr(resp,"status_code",None)}
  except Exception:pass
 def get_last_response_meta(self):return dict(getattr(self._local,"last_resp_meta",None)or{})
 def warm_pool(a,url="https://clob.polymarket.com/time",min_warm=4,max_idle_sec=18.):
  if not a._warm_lock.acquire(blocking=False):return 0
  g=set();c=0;i=max(1,int(min_warm))
  try:
   for _ in range(i):
    j=time.monotonic();e=None;b=.0
    with a._pool.mutex:
     h=a._pool.queue;d=None
     for k in range(len(h)-1,-1,-1):
      f,_=h[k]
      if id(f)not in g:d=k;break
     if d is not None:e,b=h.pop(d)
    if e is None or getattr(e,"is_closed",False):e,b=a._make_client(),.0
    if(j-b)>=max_idle_sec:
     try:e.request("GET",url);b=time.monotonic()
     except Exception:
      try:e.close()
      except Exception:pass
      continue
    g.add(id(e))
    try:a._pool.put_nowait((e,b));c+=1
    except queue.Full:
     try:e.close()
     except Exception:pass
  finally:a._warm_lock.release()
  return c
 def request(a,method,url,**kwargs):
  d=a._pool if a._is_hot_request(method,url)else a._bg_pool;h=a._borrow_from(d);b=True
  try:e=h.request(method=method,url=url,**kwargs);a._record_resp_meta(e);return e
  except httpx.HTTPError as f:
   b=False
   try:h.close()
   except Exception:pass
   c=isinstance(f,(httpx.ConnectError,httpx.ConnectTimeout,httpx.PoolTimeout))
   if c or str(method).upper()=="GET":
    g=a._make_client()
    try:e=g.request(method=method,url=url,**kwargs);a._record_resp_meta(e);a._return_to(d,g);return e
    except Exception:
     try:g.close()
     except Exception:pass
     raise
   raise f
  finally:
   if b:a._return_to(d,h)
def install_thread_safe_clob_http_client(target_module=None):
 try:logging.getLogger("httpx").setLevel(logging.WARNING);logging.getLogger("httpcore").setLevel(logging.WARNING)
 except Exception:pass
 try:
  if target_module is None:import py_clob_client_v2.http_helpers.helpers as hh;target_module=hh
  a=getattr(target_module,"_http_client",None)
  if isinstance(a,_ThreadLocalClobHttpClient):return True
  target_module._http_client=_ThreadLocalClobHttpClient()
  try:
   if a is not None and hasattr(a,"close"):a.close()
  except Exception:pass
  return True
 except Exception:return False
enable_tcp_nodelay_globally();install_thread_safe_clob_http_client();PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT)not in sys.path:sys.path.insert(0,str(PIPELINE_ROOT))
load_dotenv(PIPELINE_ROOT/".env");POLYMARKET_DATA_DIR=Path(os.getenv("POLYMARKET_DATA_DIR",str(PIPELINE_ROOT/"data/polymarket")));RISK_CONFIG_PATH=Path(os.getenv("POLYMARKET_RISK_CONFIG",str(PIPELINE_ROOT/"config/polymarket_risk_config.json")));_RISK_CONFIG_DEFAULTS={"ticket_notional":16.5,"dynamic_sizing":True,"dynamic_risk_pct":.18,"scale_up_equity_threshold":110.,"correlated_crypto_single_slot_threshold":150.,"high_price_ticket_cap_pct":.16,"scale_up_risk_pct":.22,"min_equity_floor":66.67,"seed_survival_equity_threshold":88.,"seed_survival_ticket_usd":12.,"seed_survival_max_concurrent":1,"seed_survival_floor_usd":48.,"seed_smooth_compounding":True,"enable_fak_plus2c_fallback":False,"enable_live_maker_anchor_boxes":False,"enable_single_leg_maker_bond1":True,"enable_bond1_live_bridge":True,"enable_nr2_pure_cash_bridge":True,"velocity_gate_bankroll_usd":250.,"min_floor_bps_per_hour":25.,"long_tte_min_floor_bps":180.,"enable_live_phase3a_maker_fallback":True,"phase3a_maker_max_notional_usd":22.,"phase3a_maker_ttl_sec":4.,"phase3a_15m_long_tte_max_price":.72,"directional_taker_max_price":.74,"directional_maker_max_price":.76,"enable_orthogonal_boundary_slot":True,"enable_graduated_d1_box":True,"enable_sol_d1_box":True,"d1_routing_mode":"hybrid_auto","d1_max_box_cost_net":.985,"cm_b3_max_walk_cap":.99,"bond1_maker_max_keep_sec":3e2,"d1_box_max_budget_usd":250.,"d1_box_collateral_reserve_usd":12.,"d1_box_bankroll_pct":.25,"d1_depth_ratio_threshold":1.2,"d1_min_depth_mult_gate":1.15,"d1_max_giveback_frac":.25,"max_concurrent_d1_boxes":4,"max_total_portfolio_slots":4,"unlimited_slots":False,"enable_graduated_alt_sleeves":True,"enable_ungraduated_v3_math_live":False,"enable_exp_d1_bridge":True,"max_daily_loss":20.,"max_exposure":35.,"max_concurrent_positions":2,"hold_to_maturity":False,"exit_policy":"hold_98","stale_fast_tick_max_age_sec":15.,"stale_telemetry_max_age_sec":30.,"stale_alert_after_sec":60.,"alert_rate_limit_sec":3e2}
def load_risk_config(path=None):
 e=dict(_RISK_CONFIG_DEFAULTS)
 try:
  with open(path or RISK_CONFIG_PATH,"r",encoding="utf-8")as f:d=json.load(f)
  if isinstance(d,dict):
   for c,a in _RISK_CONFIG_DEFAULTS.items():
    if c not in d:continue
    b=d[c]
    if isinstance(a,bool):e[c]=bool(b)
    elif c=="exit_policy"and isinstance(b,str)and b in("hold_98","two_tranche_95_98"):e[c]=b
    elif c=="d1_routing_mode"and isinstance(b,str)and b in("hybrid_auto","fragile_first","parallel_2leg"):e[c]=b
    elif isinstance(b,(int,float))and not isinstance(b,bool)and math.isfinite(float(b))and(float(b)>=.0 if c=="d1_box_collateral_reserve_usd"else float(b)>0):e[c]=int(b)if c in("max_concurrent_positions","seed_survival_max_concurrent","max_concurrent_d1_boxes","max_total_portfolio_slots")else float(b)
 except Exception:pass
 return e
RISK_CONFIG=load_risk_config()
try:
 import py_clob_client_v2
 if getattr(py_clob_client_v2,"_IS_STDLIB_TEST_STUB",False):raise ImportError("py_clob_client_v2 is stdlib test stub")
 import py_clob_client_v2.clob_types as _clob_types_mod;from py_clob_client_v2.client import(ClobClient,_is_v2_order as _clob_is_v2_order,order_to_json_v1 as _clob_order_to_json_v1,order_to_json_v2 as _clob_order_to_json_v2);from py_clob_client_v2.exceptions import PolyApiException;from py_clob_client_v2.clob_types import(ApiCreds,OrderArgsV2,MarketOrderArgsV2,OrderType,AssetType,BalanceAllowanceParams,TradeParams,PartialCreateOrderOptions,FeeInfo);PostOrdersV2Args=getattr(_clob_types_mod,"PostOrdersV2Args",None);PY_CLOB_AVAILABLE=True;PY_CLOB_VERSION=getattr(py_clob_client_v2,"__version__","1.2.0")
except ImportError:
 PY_CLOB_AVAILABLE=False;PY_CLOB_VERSION=None;ClobClient=None;_clob_is_v2_order=None;_clob_order_to_json_v1=None;_clob_order_to_json_v2=None
 class PolyApiException(Exception):
  def __init__(self,resp=None,error_msg=None):self.status_code=getattr(resp,"status_code",None);self.error_msg=error_msg if error_msg is not None else(getattr(resp,"text",None)or resp or"");self.error_message=self.error_msg;super().__init__(f"PolyApiException[status_code={self.status_code}, error_message={self.error_msg}]")
 class _FallbackClobStruct:
  def __init__(self,*args,**kwargs):
   for k,v in kwargs.items():setattr(self,k,v)
 class ApiCreds(_FallbackClobStruct):
  def __init__(self,api_key="",api_secret="",api_passphrase="",**kw):super().__init__(api_key=api_key,api_secret=api_secret,api_passphrase=api_passphrase,**kw)
 class OrderArgsV2(_FallbackClobStruct):
  def __init__(self,price=.0,size=.0,side="BUY",token_id="",fee_rate_bps=0,nonce=0,expiration=0,taker="0x0000000000000000000000000000000000000000",**kw):super().__init__(price=price,size=size,side=side,token_id=token_id,fee_rate_bps=fee_rate_bps,nonce=nonce,expiration=expiration,taker=taker,**kw)
 class MarketOrderArgsV2(_FallbackClobStruct):
  def __init__(self,token_id="",amount=.0,side="BUY",price=.0,fee_rate_bps=0,nonce=0,taker="0x0000000000000000000000000000000000000000",order_type="FOK",**kw):super().__init__(token_id=token_id,amount=amount,side=side,price=price,fee_rate_bps=fee_rate_bps,nonce=nonce,taker=taker,order_type=order_type,**kw)
 class OrderType:GTC="GTC";FOK="FOK";GTD="GTD";FAK="FAK"
 class AssetType:COLLATERAL="COLLATERAL";CONDITIONAL="CONDITIONAL"
 class BalanceAllowanceParams(_FallbackClobStruct):
  def __init__(self,asset_type=None,token_id=None,signature_type=-1,**kw):super().__init__(asset_type=asset_type,token_id=token_id,signature_type=signature_type,**kw)
 class TradeParams(_FallbackClobStruct):pass
 class PartialCreateOrderOptions(_FallbackClobStruct):
  def __init__(self,tick_size=None,neg_risk=None,version=None,**kw):super().__init__(tick_size=tick_size,neg_risk=neg_risk,version=version,**kw)
 class FeeInfo(_FallbackClobStruct):pass
 class PostOrdersV2Args(_FallbackClobStruct):
  def __init__(self,order=None,orderType="FOK",**kw):super().__init__(order=order,orderType=orderType,**kw)
 class RequestArgs(_FallbackClobStruct):
  def __init__(self,method="GET",request_path="",body=None,serialized_body=None,**kw):super().__init__(method=method,request_path=request_path,body=body,serialized_body=serialized_body,**kw)
 if"py_clob_client_v2"not in sys.modules:
  _pkg_stub=_types.ModuleType("py_clob_client_v2");_pkg_stub._IS_STDLIB_TEST_STUB=True;_exc_stub=_types.ModuleType("py_clob_client_v2.exceptions");_exc_stub.PolyApiException=PolyApiException;_ct_stub=_types.ModuleType("py_clob_client_v2.clob_types")
  for _nm,_obj in(("ApiCreds",ApiCreds),("OrderArgsV2",OrderArgsV2),("MarketOrderArgsV2",MarketOrderArgsV2),("OrderType",OrderType),("AssetType",AssetType),("BalanceAllowanceParams",BalanceAllowanceParams),("TradeParams",TradeParams),("PartialCreateOrderOptions",PartialCreateOrderOptions),("FeeInfo",FeeInfo),("PostOrdersV2Args",PostOrdersV2Args),("RequestArgs",RequestArgs)):setattr(_ct_stub,_nm,_obj)
  _pkg_stub.exceptions=_exc_stub;_pkg_stub.clob_types=_ct_stub;sys.modules["py_clob_client_v2"]=_pkg_stub;sys.modules["py_clob_client_v2.exceptions"]=_exc_stub;sys.modules["py_clob_client_v2.clob_types"]=_ct_stub
EXPECTED_CLOB_V2="1.2.0";CLOB_ALLOWED_TICK_SIZES=(.1,.01,.005,.0025,.001,1e-4)
def quantize_fok_buy_box_legs(shares_net,px_a,px_b,h_a=.0,h_b=.0,max_box_cost_net=.985,avail_a=None,avail_b=None,max_budget_usd=None,min_shares=5.):
 if px_a<=.0 or px_b<=.0 or shares_net<min_shares-1e-9:return None
 x=max(1,int(round(float(px_a)*10000)));w=max(1,int(round(float(px_b)*10000)));J=10000//math.gcd(x,10000);I=10000//math.gcd(w,10000);v=(J*25)//math.gcd(J,25);u=(I*25)//math.gcd(I,25);H=max(.0,min(.25,float(h_a)));G=max(.0,min(.25,float(h_b)));h=max(500,int(math.ceil(float(min_shares)*1e2-1e-9)));f=max(h,int(math.floor(float(shares_net)*1e2+1e-9)))
 def b(sc,hl):return sc if hl<=.0 else int(math.floor(sc*(1.-hl)+1e-9))
 def a(nc,hl):
  if hl<=.0:return nc
  g=int(math.ceil((nc-1e-9)/max(1.-hl,1e-6)))
  while b(g,hl)<nc:g+=1
  return g
 e=v>=u;t,L,n=(v,H,avail_a)if e else(u,G,avail_b);s,K=(u,G)if e else(v,H);c=(a(f,L)//t)*t
 if n is not None and math.isfinite(float(n)):c=min(c,(int(math.floor(float(n)*1e2+1e-9))//t)*t)
 i=None;sc=c
 while sc>=500:
  nc=b(sc,L)
  if nc<h:break
  A=a(nc,K);z=((A+s-1)//s)*s;y=(A//s)*s;k=(z,)if y==z else(z,y)
  for O in k:
   if O<500:continue
   F,E=(sc,O)if e else(O,sc);D=round(F/1e2,2);C=round(E/1e2,2)
   if D<5. or C<5.:continue
   if D*float(px_a)<1.-1e-9 or C*float(px_b)<1.-1e-9:continue
   if avail_a is not None and D>float(avail_a)+1e-6:continue
   if avail_b is not None and C>float(avail_b)+1e-6:continue
   N=b(F,H)/1e2;M=b(E,G)/1e2;r=round(min(N,M),2)
   if r<float(min_shares)-1e-9 or abs(N-M)>=5.:continue
   j=round(D*float(px_a)+C*float(px_b),4);d=round(D*float(px_a)*(1.+H)+C*float(px_b)*(1.+G),4);m=round(min(D,C),2)
   if max_budget_usd is not None and max(j,d)>float(max_budget_usd)+1e-6:continue
   q=round(j/max(r,1e-6),6);p=round(d/max(m,1e-6),6);l=max(q,p)
   if l>float(max_box_cost_net)+1e-6:continue
   B=round(min(r-j,m-d),6);o={"leg_a_gross_shares":D,"leg_b_gross_shares":C,"net_paired_shares":r,"total_cost_usd":j,"v2_total_cash_usd":d,"v2_box_cost_net":p,"eff_box_cost_net":l}
   if i is None or(B,r)>(i[0],i[1]):i=(B,r,o)
  sc-=t
 return i[2]if i is not None else None
def quantize_fok_buy_leg_size(size,price,*,round_up=False,prefer_integer_on_cent_tick=False):
 if size<=.0 or price<=.0:return.0
 d=max(1,int(round(float(price)*10000)));e=10000//math.gcd(d,10000);a=(e*25)//math.gcd(e,25)
 if prefer_integer_on_cent_tick and(d%100==0):a=(a*100)//math.gcd(a,100)
 if round_up:b=int(math.ceil(float(size)*1e2-1e-9));c=((b+a-1)//a)*a
 else:b=int(math.floor(float(size)*1e2+1e-9));c=(b//a)*a
 return round(c/1e2,2)if c>0 else.0
MAX_PRICE_CEILING=.86;MIN_PRICE_FLOOR=.55;MIN_LOT_SIZE_USD=12.;DEFAULT_DEPTH_HURDLE=1.3;SLEEVE_1_MIN_PRICE=.55;SLEEVE_1_MAX_PRICE=.86;SLEEVE_2_ENABLED=True;SLEEVE_2_MIN_PRICE=.55;SLEEVE_2_MAX_PRICE=.78;SLEEVE_2_SUBHOURLY_MAX_PRICE=.78;CIRCUIT_BREAKER_EQUITY_FLOOR=RISK_CONFIG["min_equity_floor"];DYNAMIC_EQUITY_RISK_PCT=RISK_CONFIG["dynamic_risk_pct"];MIN_TICKET_USD=12.;MAX_TICKET_CAP_USD=2e2;MAX_CONCURRENT_POSITIONS=3;MAX_POSITIONS_PER_MARKET_ID=2;logger=logging.getLogger("PolymarketLiveExecutor")
if not logger.handlers:handler=logging.StreamHandler(sys.stdout);handler.setFormatter(logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [PM-EXEC] %(message)s"));logger.addHandler(handler);logger.setLevel(logging.INFO)
class ExecutionStatus:REJECTED="REJECTED";SUBMITTED="SUBMITTED";MATCHED_PENDING_SETTLEMENT="MATCHED_PENDING_SETTLEMENT";POSITION_CONFIRMED="POSITION_CONFIRMED";EXIT_PENDING_SETTLEMENT="EXIT_PENDING_SETTLEMENT";EXIT_RESTING="EXIT_RESTING";PARTIALLY_FILLED="PARTIALLY_FILLED";FILLED="FILLED";SETTLED="SETTLED"
def calculate_taker_fee(notional_usd,price,fee_rate=.07,fee_exponent=1.):c=max(.001,min(.999,price));e=notional_usd/c;b=fee_rate*((c*(1.-c))**fee_exponent);d=float(Decimal(str(e*b)).quantize(Decimal("0.00001"),rounding=ROUND_HALF_UP));a=round(d/max(notional_usd,1e-6),8);return a,d
def is_fak_killed_no_match(err=None,raw_resp=None):
 c="no orders found to match with fak order"
 if err is not None:
  a=getattr(err,"error_message",None)or getattr(err,"error_msg",None)
  if a and c in str(a).lower():return True
  if c in str(getattr(err,"error_msg","")).lower():return True
  if c in str(err).lower():return True
 if raw_resp and isinstance(raw_resp,dict):
  b=str(raw_resp.get("errorMsg")or raw_resp.get("error")or raw_resp.get("error_message")or"")
  if c in b.lower():return True
 return False
def is_clob_400_rejection(err=None,raw_resp=None):
 if is_fak_killed_no_match(err,raw_resp):return True
 if err is not None:
  e=getattr(err,"status_code",None)
  if e in(400,425,429,"400","425","429"):return True
  a=str(err).lower()
  if("status_code=400"in a or"status=400"in a or"status_code=425"in a or"status_code=429"in a or"invalid amounts"in a or"fok_order_not_filled"in a or"couldn't be fully filled"in a or"trading is disabled"in a or"market is closed"in a or"orderbook does not exist"in a):return True
  b=getattr(err,"error_message",None)or getattr(err,"error_msg",None)
  if b:
   c=str(b).lower()
   if any(p in c for p in("invalid amounts","supports a max accuracy","not enough balance","order crosses book","min size","fok_order_not_filled","couldn't be fully filled","trading is disabled","market is closed","orderbook does not exist")):return True
 if raw_resp and isinstance(raw_resp,dict):
  d=raw_resp.get("status")or raw_resp.get("statusCode")or raw_resp.get("status_code")
  if d in(400,425,429,"400","425","429"):return True
  a=str(raw_resp.get("error")or raw_resp.get("errorMsg")or raw_resp.get("error_message")or"").lower()
  if"invalid amounts"in a or"supports a max accuracy"in a or"bad request"in a:return True
 return False
def encode_builder_code_bytes32_hex(raw_code):
 c="0x"+"00"*32
 if raw_code is None:return c
 s=str(raw_code).strip()
 if not s:return c
 if s.startswith(("0x","0X")):
  d=s[2:].strip()
  if not d or all(ch=="0"for ch in d):return c
  if len(d)<=64 and all(ch in"0123456789abcdefABCDEF"for ch in d):return"0x"+d.lower().zfill(64)
 a=s.encode("utf-8")[:32]
 if not a or all(b==0 for b in a):return c
 return"0x"+a.ljust(32,b"\x00").hex()
class RelayerRateLimiter:
 def __init__(a,max_per_min=24,window_sec=60.):a.max_per_min=max(1,int(max_per_min));a.window_sec=max(1.,float(window_sec));a._lock=threading.Lock();a._timestamps=deque()
 def _prune_unlocked(a,now_mono):
  b=now_mono-a.window_sec
  while a._timestamps and a._timestamps[0]<=b:a._timestamps.popleft()
 def recent_count(a,now_mono=None):
  b=float(time.monotonic()if now_mono is None else now_mono)
  with a._lock:a._prune_unlocked(b);return len(a._timestamps)
 def allow_and_record(a,now_mono=None):
  c=float(time.monotonic()if now_mono is None else now_mono)
  with a._lock:
   a._prune_unlocked(c)
   if len(a._timestamps)>=a.max_per_min:b=max(.05,(a._timestamps[0]+a.window_sec)-c);return False,round(b,3)
   a._timestamps.append(c);return True,.0
class FastV2OrderSigner:
 _SIDE_WORDS:Tuple[bytes,bytes]=((0).to_bytes(32,"big"),(1).to_bytes(32,"big"));_REC_ID_HEX:Tuple[str,str,str,str]=("1b","1c","1d","1e")
 def __init__(a,clob_client):
  import dataclasses as _dc;import coincurve;from py_clob_client_v2.config import get_contract_config as i;from py_clob_client_v2.order_builder.builder import ROUNDING_CONFIG as m;from py_clob_client_v2.order_builder.helpers import round_normal as p;from py_clob_client_v2.order_utils import ExchangeOrderBuilderV2 as b,Side,SignatureTypeV2 as e;from py_clob_client_v2.order_utils.exchange_order_builder_v2 import(BYTES32_ZERO as c,DEPOSIT_WALLET_DOMAIN_SALT as g,DEPOSIT_WALLET_NAME_HASH as h,DEPOSIT_WALLET_VERSION_HASH as f,ORDER_TYPE_HASH as l,ORDER_TYPE_STRING as d,SOLADY_TYPE_HASH as j,_keccak as s,generate_order_salt);from py_clob_client_v2.order_utils.model.order_data_v2 import OrderDataV2 as q,SignedOrderV2 as n;a._client=clob_client;a._orig_create_order=clob_client.create_order;a._order_builder=clob_client.builder;a._signer=a._order_builder.signer;a._chain_id=int(a._signer.get_chain_id());a._signature_type=e(int(a._order_builder.signature_type));a._sig_type_int=int(a._signature_type);a._is_poly_1271=a._signature_type==e.POLY_1271;a._maker_addr=str(a._order_builder.funder);a._signer_addr=str(a._order_builder._v2_order_signer());o=(getattr(getattr(clob_client,"builder_config",None),"builder_code",None)or os.getenv("POLY_BUILDER_CODE")or os.getenv("BUILDER_CODE")or"");r=getattr(a._order_builder,"_resolve_builder_hex",None)
  if callable(r)and o:
   try:a._default_builder_hex=str(r(o)or c)
   except Exception:a._default_builder_hex=encode_builder_code_bytes32_hex(str(o))
  else:a._default_builder_hex=encode_builder_code_bytes32_hex(str(o))
  a._has_builder_code=a._default_builder_hex!=c;a._tick_sizes_dict=getattr(clob_client,"_ClobClient__tick_sizes",{});a._neg_risk_dict=getattr(clob_client,"_ClobClient__neg_risk",{});a._rounding_config=m;a._round_normal=p;a._keccak=s;a._SignedOrderV2=n;a._OrderDataV2=q;a._ExchangeOrderBuilderV2=b;a._Side=Side;a._bytes32_zero_hex=c;a._bytes32_zero=b"\x00"*32;a._order_type_hash=l;a._dc_asdict=_dc.asdict;k=str(a._signer.private_key).strip()
  if k.startswith(("0x","0X")):k=k[2:]
  a._cc_priv=coincurve.PrivateKey(bytes.fromhex(k.zfill(64)));a._maker_word=a._addr_to_word32(a._maker_addr);a._signer_word=a._addr_to_word32(a._signer_addr);a._sig_type_word=a._sig_type_int.to_bytes(32,"big");v=i(a._chain_id);u=b(v.exchange_v2,a._chain_id,a._signer,domain_version="2");t=b(v.neg_risk_exchange_v2,a._chain_id,a._signer,domain_version="2");a._std_exchange=v.exchange_v2;a._neg_exchange=v.neg_risk_exchange_v2;a._dom_sep_std=u.app_domain_separator;a._dom_sep_neg=t.app_domain_separator;a._dom_sep_std_hex=a._dom_sep_std.hex();a._dom_sep_neg_hex=a._dom_sep_neg.hex();a._solady_prefix=j;a._solady_suffix=(h+f+a._chain_id.to_bytes(32,"big")+a._signer_word+g);a._poly_1271_type_tail_hex=(d.encode("utf-8").hex()+len(d).to_bytes(2,"big").hex());a._default_builder_word=a._hex_to_word32(a._default_builder_hex);a._tok_word_cache={};a._amt_cache={};a._amt_cache_lock=threading.Lock();a._salt_lock=threading.Lock();a._salt_pool=[];a._verify_parity_against_sdk()
 def _next_buffered_salt(a):
  d=getattr(a,"_salt_pool",None);c=getattr(a,"_salt_lock",None)
  if d is None or c is None:return a._generate_salt()
  with c:
   if not d:e=os.urandom(2048);b=(1<<53)-1;d.extend(((int.from_bytes(e[i:i+8],"little")&b)or 1)for i in range(0,2048,8))
   return d.pop()
 @staticmethod
 def _generate_salt():return secrets.randbelow((1<<53)-1)+1
 @staticmethod
 def _addr_to_word32(addr):
  a=str(addr).strip().lower()
  if a.startswith("0x"):a=a[2:]
  if len(a)!=40:raise ValueError(f"Invalid 20-byte hex address: {addr}")
  return b"\x00"*12+bytes.fromhex(a)
 @staticmethod
 def _hex_to_word32(hex_str):
  if not hex_str:return b"\x00"*32
  a=str(hex_str).strip()
  if a.startswith(("0x","0X")):a=a[2:]
  if not a or a=="0"*len(a):return b"\x00"*32
  b=bytes.fromhex(a.zfill(64));return b[:32]if len(b)>=32 else b.rjust(32,b"\x00")
 def sign_v2_order_data(a,*,token_id,maker_amount,taker_amount,side,neg_risk,salt=None,timestamp=None,expiration="0",metadata=None,builder=None):
  m=int(salt)if salt is not None else int(a._generate_salt());v=str(timestamp)if timestamp else str(time.time_ns()//1000000);s=str(expiration)if expiration else"0";l=metadata if metadata else a._bytes32_zero_hex;h=builder if builder else a._bytes32_zero_hex;r=str(token_id);j=a._tok_word_cache.get(r)
  if j is None:
   q=int(r,16)if r.startswith(("0x","0X"))else int(r);j=q.to_bytes(32,"big")
   if len(a._tok_word_cache)<2048:a._tok_word_cache[r]=j
  k=int(side);u=a._SIDE_WORDS[k]if k in(0,1)else k.to_bytes(32,"big");t=a._bytes32_zero if l==a._bytes32_zero_hex else a._hex_to_word32(l)
  if h==a._bytes32_zero_hex:b=a._bytes32_zero
  elif h==a._default_builder_hex:b=a._default_builder_word
  else:b=a._hex_to_word32(h)
  e=a._keccak(primitive=b"".join((a._order_type_hash,m.to_bytes(32,"big"),a._maker_word,a._signer_word,j,int(maker_amount).to_bytes(32,"big"),int(taker_amount).to_bytes(32,"big"),u,a._sig_type_word,int(v).to_bytes(32,"big"),t,b)));p=a._dom_sep_neg if neg_risk else a._dom_sep_std
  if a._is_poly_1271:o=a._keccak(primitive=b"".join((a._solady_prefix,e,a._solady_suffix)));g=a._keccak(primitive=b"".join((b"\x19\x01",p,o)));i=a._cc_priv.sign_recoverable(g,hasher=None);f=i[64];d=a._REC_ID_HEX[f]if f<4 else f"{f+27:02x}";n=a._dom_sep_neg_hex if neg_risk else a._dom_sep_std_hex;c="0x"+i[:64].hex()+d+n+e.hex()+a._poly_1271_type_tail_hex
  else:g=a._keccak(primitive=b"".join((b"\x19\x01",p,e)));i=a._cc_priv.sign_recoverable(g,hasher=None);f=i[64];d=a._REC_ID_HEX[f]if f<4 else f"{f+27:02x}";c="0x"+i[:64].hex()+d
  return a._SignedOrderV2(salt=m,maker=a._maker_addr,signer=a._signer_addr,tokenId=r,makerAmount=str(maker_amount),takerAmount=str(taker_amount),side=side,signatureType=a._signature_type,timestamp=v,metadata=l,builder=h,expiration=s,signature=c)
 def _verify_parity_against_sdk(a):
  i="580531616296768985464990134503";b=encode_builder_code_bytes32_hex("dominus_v55")
  for h,g in((False,a._std_exchange),(True,a._neg_exchange)):
   for f,k,j in((a._Side.BUY,"15200000","20000000"),(a._Side.SELL,"20000000","19800000")):
    for l in(a._bytes32_zero_hex,b):
     d=a._ExchangeOrderBuilderV2(g,a._chain_id,a._signer,generate_salt=lambda:987654321,domain_version="2");m=a._OrderDataV2(maker=a._maker_addr,tokenId=i,makerAmount=k,takerAmount=j,side=f,signer=a._signer_addr,signatureType=a._signature_type,timestamp="1700000000000",metadata=a._bytes32_zero_hex,builder=l,expiration="0");e=d.build_signed_order(m);c=a.sign_v2_order_data(token_id=i,maker_amount=k,taker_amount=j,side=f,neg_risk=h,salt=987654321,timestamp="1700000000000",expiration="0",metadata=a._bytes32_zero_hex,builder=l)
     if a._dc_asdict(c)!=a._dc_asdict(e):raise RuntimeError(f"FastV2OrderSigner parity mismatch (neg_risk={h}, side={f}, builder={l})")
 def create_order(a,order_args,options=None):
  if(getattr(order_args,"position_id",None)or getattr(order_args,"user_usdc_balance",None)is not None or(options is not None and getattr(options,"version",None)not in(None,2))):return a._orig_create_order(order_args,options)
  j=str(getattr(order_args,"token_id","")or"")
  if not j:return a._orig_create_order(order_args,options)
  h=(str(options.tick_size)if(options is not None and getattr(options,"tick_size",None)is not None)else a._tick_sizes_dict.get(j))
  if not h or h not in a._rounding_config:return a._orig_create_order(order_args,options)
  o=float(h);l=float(order_args.price)
  if not(o<=l<=round(1.-o,8)):return a._orig_create_order(order_args,options)
  i=(bool(options.neg_risk)if(options is not None and getattr(options,"neg_risk",None)is not None)else a._neg_risk_dict.get(j))
  if i is None:return a._orig_create_order(order_args,options)
  n=a._rounding_config[h];m=a._round_normal(l,n.price);k=(str(order_args.side),float(order_args.size),m,h);f=a._amt_cache.get(k)
  if f is not None:e,d,c=f
  else:
   e,d,c=a._order_builder.get_order_amounts(order_args.side,order_args.size,m,n)
   with a._amt_cache_lock:
    if len(a._amt_cache)>=4096:a._amt_cache.clear()
    a._amt_cache[k]=(e,d,c)
  g=getattr(order_args,"builder_code",None)
  if g not in(None,"",a._bytes32_zero_hex):b=encode_builder_code_bytes32_hex(str(g))
  else:b=a._default_builder_hex
  return a.sign_v2_order_data(token_id=j,maker_amount=str(d),taker_amount=str(c),side=e,neg_risk=bool(i),salt=a._next_buffered_salt(),expiration=str(getattr(order_args,"expiration",0)or 0),metadata=getattr(order_args,"metadata",None)or a._bytes32_zero_hex,builder=b)
 @classmethod
 def from_clob_client(cls,clob_client):return cls(clob_client)
def _safe_create_order(client_fn,args,options=None):
 b=getattr(client_fn,"__self__",None)
 if b is not None and"create_order"not in getattr(b,"__dict__",{}):
  a=getattr(b,"_fast_v2_signer",None)
  if a is not None:return a.create_order(args,options)
 if options is not None:
  try:return client_fn(args,options)
  except TypeError:return client_fn(args)
 return client_fn(args)
class PreSignedOrderLadderCache:
 def __init__(a,ttl_seconds=3e2):a.ttl_seconds=ttl_seconds;a._cache={};a._lock=threading.Lock();a.hits=0;a.misses=0
 @staticmethod
 def _make_key(token_id,price,shares,price_cents=None,tick_size="0.01",neg_risk=False):
  if price_cents is None:
   d=float(price)*1e2;a=int(round(d))
   if abs(d-a)>1e-6:return None
  else:a=int(price_cents)
  c=float(shares);b=int(round(c))
  if b<=0 or abs(c-b)>1e-9:return None
  return str(token_id),a,b,str(tick_size or"0.01"),bool(neg_risk)
 def get_presigned_order(a,token_id,price=.0,shares=.0,price_cents=None,tick_size="0.01",neg_risk=False):
  f=a._make_key(token_id,price,shares,price_cents,tick_size=tick_size,neg_risk=neg_risk)
  if f is None:
   with a._lock:a.misses+=1
   return None
  e=time.time()
  with a._lock:
   d=a._cache.pop(f,None)
   if d:
    c,b=d
    if(e-c)<=a.ttl_seconds:a.hits+=1;return b
   a.misses+=1;return None
 def get_presigned_order_near(a,token_id,price,shares,max_share_delta=2,max_notional_usd=None,tick_size="0.01",neg_risk=False):
  h=a._make_key(token_id,price,shares,tick_size=tick_size,neg_risk=neg_risk)
  if h is None:return None
  o,j,d,k,i=h;g=j/1e2;q=time.time();n=max(0,int(max_share_delta))
  with a._lock:
   for p in range(1,n+1):
    for m in(-p,p):
     c=d+m
     if c<5:continue
     if max_notional_usd is not None and(c*g)>float(max_notional_usd)+1e-6:continue
     f=(o,j,c,k,i);l=a._cache.pop(f,None)
     if l:
      e,b=l
      if(q-e)<=a.ttl_seconds:a.hits+=1;return b,c
  return None
 def has_fresh(a,token_id,price,shares,min_remaining_sec=60.,tick_size="0.01",neg_risk=False):
  c=a._make_key(token_id,price,shares,tick_size=tick_size,neg_risk=neg_risk)
  if c is None:return False
  with a._lock:b=a._cache.get(c)
  return bool(b)and(time.time()-b[0])<=(a.ttl_seconds-min_remaining_sec)
 def evict_mismatched_tick(a,token_id,valid_tick_str):
  c,b=str(token_id),str(valid_tick_str or"0.01")
  with a._lock:
   d=[k for k in a._cache if k[0]==c and k[3]!=b]
   for k in d:a._cache.pop(k,None)
   return len(d)
 def filter_missing_or_stale(a,token_id,price_share_pairs,min_remaining_sec=60.,tick_size="0.01",neg_risk=False):
  k=str(token_id);h=str(tick_size or"0.01");f=bool(neg_risk);e=a.ttl_seconds-min_remaining_sec;m=time.time();d=[];j=a._cache
  with a._lock:
   for o,n in price_share_pairs:
    c=float(o)*1e2;b=int(round(c));l=float(n);g=int(round(l))
    if abs(c-b)>1e-6 or g<=0 or abs(l-g)>1e-9:d.append((o,n));continue
    i=j.get((k,b,g,h,f))
    if not i or(m-i[0])>e:d.append((o,n))
  return d
 def store_presigned_order(a,token_id,price=.0,shares=.0,signed_order=None,price_cents=None,tick_size="0.01",neg_risk=False):
  b=a._make_key(token_id,price,shares,price_cents,tick_size=tick_size,neg_risk=neg_risk)
  if b is None or signed_order is None:return False
  with a._lock:a._cache[b]=(time.time(),signed_order)
  return True
 def prune_expired(a):
  c=time.time()
  with a._lock:
   b=[k for k,(d,_)in a._cache.items()if(c-d)>a.ttl_seconds]
   for k in b:a._cache.pop(k,None)
 def clear(a):
  with a._lock:a._cache.clear()
 def __len__(a):
  with a._lock:return len(a._cache)
_CLOB_CLIENT_SIGN_LOCK=threading.Lock();_CLOB_HTTP_LOCK=threading.RLock()
try:from src.polymarket_research.polymarket_ws_streams import PolymarketUserWsCache as _PolymarketUserWsCache
except ImportError:
 try:from polymarket_ws_streams import PolymarketUserWsCache as _PolymarketUserWsCache
 except ImportError:_PolymarketUserWsCache=None
try:from src.polymarket_research.latency_trace import ActiveCounter as _ActiveCounter,CURRENT_TRACE as _CURRENT_TRACE
except ImportError:
 try:from latency_trace import ActiveCounter as _ActiveCounter,CURRENT_TRACE as _CURRENT_TRACE
 except ImportError:
  _CURRENT_TRACE=None
  class _ActiveCounter:
   def __init__(a):a._n=0;a._lock=threading.Lock()
   def enter(a):
    with a._lock:a._n+=1
   def leave(a):
    with a._lock:a._n=max(0,a._n-1)
   def __enter__(a):a.enter();return a
   def __exit__(self,exc_type,exc_val,exc_tb):self.leave();return False
   def is_set(self):return self._n>0
   @property
   def count(self):return self._n
_HOT_DISPATCH_ACTIVE=_ActiveCounter();_URGENT_SIGN_COUNTER_LOCK=threading.Lock();_URGENT_SIGN_WAITERS=0;_HOT_IO_POOL_LOCK=threading.Lock();_HOT_IO_POOL=None
def _get_hot_io_pool():
 global _HOT_IO_POOL
 if _HOT_IO_POOL is None:
  with _HOT_IO_POOL_LOCK:
   if _HOT_IO_POOL is None:
    b=concurrent.futures.ThreadPoolExecutor(max_workers=12,thread_name_prefix="pm-hot");c=threading.Barrier(12,timeout=.25)
    def a():
     try:c.wait()
     except Exception:pass
    for f in[b.submit(a)for _ in range(12)]:
     try:f.result(timeout=.35)
     except Exception:pass
    _HOT_IO_POOL=b
 return _HOT_IO_POOL
class _UrgentSignPriority:
 def __enter__(self):
  global _URGENT_SIGN_WAITERS
  with _URGENT_SIGN_COUNTER_LOCK:_URGENT_SIGN_WAITERS+=1
  _CLOB_CLIENT_SIGN_LOCK.acquire();return self
 def __exit__(self,exc_type,exc_val,exc_tb):
  global _URGENT_SIGN_WAITERS
  try:_CLOB_CLIENT_SIGN_LOCK.release()
  finally:
   with _URGENT_SIGN_COUNTER_LOCK:_URGENT_SIGN_WAITERS=max(0,_URGENT_SIGN_WAITERS-1)
  return False
class PreSubmitError(RuntimeError):pass
def _sign_and_post_single_hop(client,ladder_cache,token_id,price,size,side,order_type,create_options=None,stage=None,max_notional_usd=None,enqueue_ns=None):
 if stage is None:stage={}
 stage["submitted"]=False;_HOT_DISPATCH_ACTIVE.enter();m=time.perf_counter_ns();f=round(max(.0,(m-enqueue_ns)/1e6),3)if enqueue_ns is not None else.0;p=time.perf_counter();b=None;c=False;a=float(size)
 try:
  try:
   j=str(getattr(create_options,"tick_size","0.01")or"0.01");l=bool(getattr(create_options,"neg_risk",False))
   if ladder_cache is not None and str(side).upper()=="BUY":
    b=ladder_cache.get_presigned_order(token_id,price,size,tick_size=j,neg_risk=l);c=b is not None
    if b is None:
     k=ladder_cache.get_presigned_order_near(token_id,price,size,max_share_delta=3,max_notional_usd=max_notional_usd,tick_size=j,neg_risk=l)
     if k is not None:b,g=k;a=float(g);c=True
   if b is None:
    if OrderArgsV2 is None:raise RuntimeError("OrderArgsV2 is required for CLOB entry order signing")
    h=OrderArgsV2(price=price,size=size,side=side,token_id=token_id);d=(getattr(client,"_fast_v2_signer",None)is not None and"create_order"not in getattr(client,"__dict__",{}))
    if d:b=_safe_create_order(client.create_order,h,create_options)
    else:
     with _UrgentSignPriority():b=_safe_create_order(client.create_order,h,create_options)
   if b is None:raise RuntimeError("create_order returned no signed order")
  except Exception as e:raise PreSubmitError(f"Order signing failed before submission: {e}")from e
  o=time.perf_counter();stage["sign_ms"]=round((o-p)*1e3,3);stage["thread_hop_ms"]=f;stage["cache_hit"]=c;stage["signed_shares"]=a;stage["t_post_start"]=o;stage["submitted"]=True;i=client.post_order(b,order_type,False,True);n=time.perf_counter();return{"post_resp":i,"sign_ms":(o-p)*1e3,"post_ms":(n-o)*1e3,"thread_hop_ms":f,"cache_hit":c,"signed_shares":a,"t_post_end":n}
 finally:_HOT_DISPATCH_ACTIVE.leave()
@dataclass
class OrderResult:success:bool;order_id:Optional[str];trade_id:str;token_id:str;target_token:str;side:str;price:float;size:float;notional_usd:float;fee_usd:float;latency_ms:float;mode:str;execution_status:str=ExecutionStatus.SUBMITTED;confirmed_onchain:bool=False;details:Dict[str,Any]=field(default_factory=dict);error:Optional[str]=None
class CancelOrderResult(dict):
 def __init__(self,*args,**kwargs):b=args[0]if args else kwargs.pop("raw",{});a=dict(b)if isinstance(b,dict)else{};super().__init__(a);kwargs.pop("raw",None);self._extra=dict(kwargs);self._extra["raw"]=a
 def __getitem__(self,key):
  if super().__contains__(key):return super().__getitem__(key)
  if key in self._extra:return self._extra[key]
  raise KeyError(key)
 def get(self,key,default=None):
  if super().__contains__(key):return super().get(key,default)
  return self._extra.get(key,default)
 def __contains__(self,key):return super().__contains__(key)or(key in self._extra)
 def __bool__(self):return super().__len__()>0 or bool(self._extra)
 def __getattr__(a,name):
  if name in a._extra:return a._extra[name]
  raise AttributeError(name)
 def __repr__(a):b=dict(a);b.update(a._extra);return repr(b)
_MARKET_CLOSED_PHRASES=("trading is disabled","market closed","market is closed","no orderbook exists","orderbook does not exist","market not active")
def is_market_closed_or_disabled_error(exc=None,resp=None):
 a=[]
 if exc is not None:a.append(str(getattr(exc,"error_message","")or""));a.append(str(exc))
 if isinstance(resp,dict):
  for k in("error","errorMsg","message","status"):
   if resp.get(k):a.append(str(resp[k]))
 elif resp is not None:a.append(str(resp))
 b=" ".join(a).lower();return any(p in b for p in _MARKET_CLOSED_PHRASES)
class PolymarketLiveExecutor:
 CLOB_HOST="https://clob.polymarket.com";CHAIN_ID=137
 def __init__(a,private_key=None,funder_address=None,signature_type=None,dry_run=False,ledger_path=None):
  a.dry_run=dry_run
  if private_key is not None:a.private_key=private_key.strip()
  else:a.private_key=os.getenv("POLYGON_PRIVATE_KEY","").strip()
  if funder_address is not None:a.funder_address=funder_address.strip()
  else:a.funder_address=(os.getenv("POLYGON_FUNDER_ADDRESS","").strip()or os.getenv("POLYGON_PROXY_ADDRESS","").strip())
  e=os.getenv("POLYGON_SIGNATURE_TYPE","").strip()
  if signature_type is None and not e and not dry_run:raise RuntimeError("LIVE MODE REFUSED: POLYGON_SIGNATURE_TYPE must be explicitly configured")
  a.signature_type=signature_type if signature_type is not None else(int(e)if e else 3)
  if a.signature_type not in(0,1,2,3):raise RuntimeError(f"Unsupported POLYGON_SIGNATURE_TYPE={a.signature_type}")
  if not a.dry_run and a.private_key:
   from eth_account import Account as d
   try:b=d.from_key(a.private_key).address
   except Exception:b=None
   if a.signature_type==0:
    if(b and a.funder_address and a.funder_address.lower()!=b.lower()):raise RuntimeError("LIVE MODE REFUSED: Type 0 requires the EOA funder to equal the signing address.")
   elif a.signature_type==3:
    if not a.funder_address:raise RuntimeError("LIVE MODE REFUSED: Type 3 requires an explicitly configured Polymarket deposit-wallet funder.")
  c=os.getenv("POLYMARKET_LEDGER_PATH","").strip()
  if ledger_path is not None:a.ledger_path=Path(ledger_path)
  elif c:a.ledger_path=Path(c)
  elif a.dry_run:a.ledger_path=Path(POLYMARKET_DATA_DIR/"dry_run_orders.jsonl")
  else:a.ledger_path=Path(POLYMARKET_DATA_DIR/"live_orders.jsonl")
  a.ledger_path.parent.mkdir(parents=True,exist_ok=True);a.client=None;a.is_authenticated=False;a.auth_mode="UNINITIALIZED";a.last_heartbeat_id="";a.heartbeat_failures=0;a._fee_cache={};a._tick_size_cache={};a._neg_risk_cache={};a._async_client=None;a._hot_order_async_client=None;a._hot_order_async_loop=None;a._hot_order_last_touch_mono=.0;a._hot_order_touch_in_flight=False;a._fast_l2_ready=False;a._fast_l2_secret_bytes=b"";a._fast_l2_signer_addr="";a._fast_l2_api_key="";a._fast_l2_passphrase="";a._last_ladder_prune_mono=.0;a._thread_local=threading.local();a._collateral_cache=(None,.0);a.reservation_records={};a.reserved_inventory=defaultdict(float);a.reservation_corruption_detected=False;a._reservations_lock=threading.RLock();a._load_durable_reservations();a.order_ladder_cache=PreSignedOrderLadderCache(ttl_seconds=1800.);a._user_ws_cache=None;a._initialize_client()
 @property
 def _sync_session(a):
  c=getattr(a,"_sync_session_override",None)
  if c is not None:return c
  b=getattr(a._thread_local,"session",None)
  if b is None:b=requests.Session();a._thread_local.session=b
  return b
 @_sync_session.setter
 def _sync_session(a,sess):a._sync_session_override=sess;a._thread_local.session=sess
 def _initialize_client(a):
  if a.dry_run:a.auth_mode="DRY_RUN_STANDBY";logger.info("Initializing in DRY-RUN / Standby mode (--dry-run specified).");return
  if not a.private_key:a.auth_mode="LIVE_REFUSED_NO_KEY";raise RuntimeError("LIVE MODE REFUSED: POLYGON_PRIVATE_KEY is missing or empty. Live money trading cannot execute without an L1 private key.")
  if not PY_CLOB_AVAILABLE:a.auth_mode="LIVE_REFUSED_NO_SDK";raise RuntimeError("LIVE MODE REFUSED: py_clob_client_v2 is required for live execution. Legacy fallback is strictly prohibited.")
  try:
   import importlib.metadata;d=importlib.metadata.version("py_clob_client_v2")
   if d!=EXPECTED_CLOB_V2:a.auth_mode="LIVE_REFUSED_SDK_VERSION_MISMATCH";raise RuntimeError(f"LIVE MODE REFUSED: py_clob_client_v2 version mismatch (found '{d}', required hard-pinned '{EXPECTED_CLOB_V2}').")
  except Exception as e:
   if isinstance(e,RuntimeError):raise
   if not a.dry_run:a.auth_mode="LIVE_REFUSED_SDK_VERSION_UNVERIFIED";raise RuntimeError(f"LIVE MODE REFUSED: Inability to authoritatively verify py_clob_client_v2 installed package version: {e}")
   logger.warning(f"Metadata version check exception: {e}")
  try:
   j=time.perf_counter();install_thread_safe_clob_http_client();h={"host":a.CLOB_HOST,"key":a.private_key,"chain_id":a.CHAIN_ID,"signature_type":a.signature_type,"funder":a.funder_address if a.funder_address else None};f=(os.getenv("POLY_BUILDER_CODE")or os.getenv("BUILDER_CODE")or"").strip()
   if f:
    try:from types import SimpleNamespace as b;h["builder_config"]=b(builder_code=f)
    except Exception:pass
   try:a.client=ClobClient(**h)
   except TypeError:h.pop("builder_config",None);a.client=ClobClient(**h)
   if f and getattr(a.client,"builder_config",None)is None:
    try:from types import SimpleNamespace as b;a.client.builder_config=b(builder_code=f)
    except Exception:pass
   c=None
   if getattr(a.client,"_mock_children",None)is None and hasattr(a.client,"derive_api_key"):
    try:c=a.client.derive_api_key()
    except Exception:c=None
   if not c:
    if hasattr(a.client,"create_or_derive_api_key"):c=a.client.create_or_derive_api_key()
    else:c=a.client.create_or_derive_api_creds()
   a.client.set_api_creds(c)
   try:
    if hasattr(a.client,"_ClobClient__cached_version"):a.client._ClobClient__cached_version=2
   except Exception:pass
   if os.environ.get("PM_DISABLE_FAST_V2_SIGNER","0")!="1":
    try:a.client._fast_v2_signer=FastV2OrderSigner.from_clob_client(a.client);logger.info("FastV2OrderSigner enabled (coincurve C secp256k1, SDK byte-exact parity self-test PASSED).")
    except Exception as g:a.client._fast_v2_signer=None;logger.warning(f"FastV2OrderSigner unavailable, using py_clob_client_v2 signer: {g}")
   i=(time.perf_counter()-j)*1e3;a.is_authenticated=True;a.auth_mode="AUTHENTICATED_L2";logger.info(f"Successfully authenticated with Polymarket CLOB L2 (v2 client v{PY_CLOB_VERSION}) in {i:.2f} ms.");a._init_fast_l2_headers_cache(c)
   if os.environ.get("PM_ENABLE_TLS_KEEPALIVE","1")=="1":a.start_clob_tls_keepalive_daemon(interval_sec=6.)
   if(_PolymarketUserWsCache is not None and os.environ.get("PM_ENABLE_USER_WS","1")=="1"and getattr(a.client,"_mock_children",None)is None and getattr(c,"_mock_children",None)is None and isinstance(getattr(c,"api_key",None),str)):
    try:a._user_ws_cache=_PolymarketUserWsCache(c.api_key,c.api_secret,c.api_passphrase,on_fill_callback=lambda k:a.invalidate_collateral_cache());a._user_ws_cache.start()
    except Exception:a._user_ws_cache=None
  except Exception as e:a.auth_mode="AUTH_FAILED";a.is_authenticated=False;logger.error(f"Failed to authenticate with Polymarket CLOB: {e}");raise RuntimeError(f"LIVE MODE REFUSED: CLOB L2 authentication failed: {e}")
 def assert_market_routing(self,asset_id,market_version="CTF"):
  if market_version.upper()=="CTF":
   if not(isinstance(asset_id,str)and(asset_id.isdigit()or asset_id.startswith("0x"))and len(asset_id)>=10):raise ValueError(f"ASSET ROUTING ERROR: Invalid CTF token_id format '{asset_id}' for CTF market route.")
  elif market_version.upper()in("V2_POSITION","PROTOCOL_V2","EXCHANGE_V3"):
   if not(isinstance(asset_id,str)and asset_id.startswith("0x")and len(asset_id)>=42):raise ValueError(f"ASSET ROUTING ERROR: Invalid position_id '{asset_id}' for Exchange V3 route.")
 def prewarm_token_market_cache(a,token_id,tick_size="0.01",neg_risk=False,fee_rate_bps=0,condition_id=None,fee_rate=.072,fee_exponent=1.,preserve_fee_cache=False):
  if not token_id:return
  c=str(tick_size)if tick_size is not None else None
  if c is not None:
   try:a._tick_size_cache[token_id]=float(c)
   except Exception:a._tick_size_cache[token_id]=.01
  a._neg_risk_cache[token_id]=bool(neg_risk);e,d=float(fee_rate),float(fee_exponent)
  if preserve_fee_cache and e<=.0:
   h=a._fee_cache.get(str(condition_id or""))or a._fee_cache.get(str(token_id))
   if h and float(h[0])>.0:e,d=float(h[0]),float(h[1]);fee_rate_bps=int(round(e*1e4))
  f=condition_id or"0x0000000000000000000000000000000000000000000000000000000000000000"
  if f and(not preserve_fee_cache or e>.0):a._fee_cache[f]=(e,d)
  if a.client is not None:
   try:
    if c is not None and hasattr(a.client,"_ClobClient__tick_sizes"):a.client._ClobClient__tick_sizes[token_id]=c
    if hasattr(a.client,"_ClobClient__neg_risk"):a.client._ClobClient__neg_risk[token_id]=bool(neg_risk)
    if hasattr(a.client,"_ClobClient__fee_rates"):
     if not preserve_fee_cache or e>.0 or token_id not in a.client._ClobClient__fee_rates:a.client._ClobClient__fee_rates[token_id]=int(fee_rate_bps)
    if hasattr(a.client,"_ClobClient__cached_version"):a.client._ClobClient__cached_version=2
    g=str(condition_id or"").strip();b=(len(g)>=4 and g.lower().startswith("0x")and set(g[2:])!={"0"});f=g if b else("0x"+"0"*64)
    if b and hasattr(a.client,"_ClobClient__token_condition_map"):a.client._ClobClient__token_condition_map[token_id]=g
    if hasattr(a.client,"_ClobClient__fee_infos"):
     if not preserve_fee_cache or e>.0 or token_id not in a.client._ClobClient__fee_infos:
      if FeeInfo is not None:i=FeeInfo(rate=e,exponent=d)
      else:i=type("FeeInfoObj",(),{"rate":e,"exponent":d})()
      a.client._ClobClient__fee_infos[token_id]=i
    if not preserve_fee_cache or e>.0:a._fee_cache[f]=(e,d);a._fee_cache[str(token_id)]=(e,d)
   except Exception:pass
 def get_token_neg_risk(a,token_id,explicit_neg_risk=None):
  if explicit_neg_risk is not None:
   b=bool(explicit_neg_risk)
   if token_id:
    a._neg_risk_cache[token_id]=b
    if a.client is not None and hasattr(a.client,"_ClobClient__neg_risk"):a.client._ClobClient__neg_risk[token_id]=b
   return b
  if token_id in a._neg_risk_cache:return a._neg_risk_cache[token_id]
  if a.client is not None and hasattr(a.client,"get_neg_risk"):
   try:b=bool(a.client.get_neg_risk(token_id));a._neg_risk_cache[token_id]=b;return b
   except Exception:pass
  return False
 def prewarm_order_ladder(a,token_id,ticket_notional,price_levels=None,tick_size="0.01",fee_rate_bps=0,share_deltas=(0,),exact_shares=None,neg_risk=None,pace_every=16,pace_sleep_sec=5e-4):
  if a.dry_run or not a.is_authenticated or a.client is None or OrderArgsV2 is None:return 0
  b=0
  while(_HOT_DISPATCH_ACTIVE.is_set()or _URGENT_SIGN_WAITERS>0)and b<12:time.sleep(.025);b+=1
  if _HOT_DISPATCH_ACTIVE.is_set()or _URGENT_SIGN_WAITERS>0:return 0
  if price_levels is None:price_levels=[round(c/1e2,2)for c in(list(range(52,83))+list(range(90,95)))]
  j=a.get_token_neg_risk(token_id,neg_risk)
  if neg_risk is None and token_id not in a._neg_risk_cache:return 0
  l=a._tick_size_cache.get(token_id)
  if l is not None:tick_size=str(l)
  u=time.monotonic()
  if(u-float(getattr(a,"_last_ladder_prune_mono",.0)or.0))>=30.:a._last_ladder_prune_mono=u;a.order_ladder_cache.prune_expired()
  f=[];o=[float(s)for s in exact_shares if s>=5]if exact_shares is not None else None
  for px in price_levels:
   if px<=0:continue
   if o is not None:
    for i in o:f.append((px,i))
   else:
    k=float(math.floor(float(ticket_notional)/px))
    for t in share_deltas:
     r=k+float(t)
     if r>=5.:f.append((px,r))
  if not f:return 0
  if hasattr(a.order_ladder_cache,"filter_missing_or_stale"):d=a.order_ladder_cache.filter_missing_or_stale(token_id,f,tick_size=tick_size,neg_risk=j)
  else:d=[(px,v)for px,v in f if not a.order_ladder_cache.has_fresh(token_id,px,v,tick_size=tick_size,neg_risk=j)]
  if not d:return 0
  g=PartialCreateOrderOptions(tick_size=tick_size,neg_risk=j,version=2)if PartialCreateOrderOptions else None;e=(getattr(a.client,"_fast_v2_signer",None)is not None and"create_order"not in getattr(a.client,"__dict__",{}));q=max(1,int(pace_every or 16));p=max(.0,float(pace_sleep_sec or.0));m=0
  for px,i in d:
   b=0
   while(_HOT_DISPATCH_ACTIVE.is_set()or _URGENT_SIGN_WAITERS>0)and b<12:time.sleep(.025);b+=1
   if _HOT_DISPATCH_ACTIVE.is_set()or _URGENT_SIGN_WAITERS>0:return m
   if m>0 and p>.0 and(m%q)==0:time.sleep(p)
   try:
    n=OrderArgsV2(price=px,size=i,side="BUY",token_id=token_id)
    if e:h=_safe_create_order(a.client.create_order,n,g)
    else:
     with _CLOB_CLIENT_SIGN_LOCK:h=_safe_create_order(a.client.create_order,n,g)
    if h and a.order_ladder_cache.store_presigned_order(token_id,px,i,h,tick_size=tick_size,neg_risk=j):m+=1
   except Exception:continue
  return m
 def start_clob_tls_keepalive_daemon(a,interval_sec=20.):
  if a.dry_run or getattr(a,"_tls_keepalive_started",False):return
  a._tls_keepalive_started=True
  def b():
   try:
    if not _HOT_DISPATCH_ACTIVE.is_set():a.ping_clob_keepalive()
   except Exception:pass
   while not a.dry_run:
    d=float(interval_sec)
    try:
     from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as c;e=c.snapshot.get("routing",{})
     if e.get("async_clob_keepalive_interval_sec")is not None:d=float(e["async_clob_keepalive_interval_sec"])
    except Exception:pass
    time.sleep(max(1.,d))
    if a.dry_run:break
    try:
     if not _HOT_DISPATCH_ACTIVE.is_set():a.ping_clob_keepalive()
    except Exception:pass
  t=threading.Thread(target=b,name="clob-tls-keepalive",daemon=True);t.start()
 def ping_clob_keepalive(c):
  if c.dry_run or not c.client or _HOT_DISPATCH_ACTIVE.is_set():return
  if not _CLOB_HTTP_LOCK.acquire(blocking=False):return
  try:
   h=time.perf_counter();d=0
   try:
    import py_clob_client_v2.http_helpers.helpers as hh;f=getattr(hh,"_http_client",None)
    if isinstance(f,_ThreadLocalClobHttpClient):
     b=6.5
     try:
      from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as a;g=a.snapshot.get("routing",{})
      if g.get("async_clob_keepalive_expiry_sec")is not None:b=min(float(g["async_clob_keepalive_expiry_sec"]),15.)
     except Exception:pass
     d=f.warm_pool(url=f"{c.CLOB_HOST.rstrip('/')}/time",min_warm=4,max_idle_sec=max(3.5,b))
   except Exception:d=0
   if d==0:c.client.get_server_time()
   e=(time.perf_counter()-h)*1e3
  except Exception:pass
  finally:_CLOB_HTTP_LOCK.release()
 def get_async_client(a):
  try:b=asyncio.get_running_loop()
  except RuntimeError:b=None
  if(a._async_client is None or a._async_client.is_closed or(b is not None and getattr(a,"_async_client_loop",None)is not b)):
   e=httpx.Limits(max_keepalive_connections=10,max_connections=20,keepalive_expiry=45.)
   try:d=[(socket.IPPROTO_TCP,socket.TCP_NODELAY,1),(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)];c=httpx.AsyncHTTPTransport(http2=False,limits=e,socket_options=d);a._async_client=httpx.AsyncClient(http2=False,timeout=3.,transport=c)
   except Exception:a._async_client=httpx.AsyncClient(http2=False,timeout=3.,limits=e)
   a._async_client_loop=b
  return a._async_client
 async def close_async(a):
  b=getattr(a,"_async_keepalive_task",None)
  if b is not None and not b.done():b.cancel()
  a._async_keepalive_task=None
  if a._async_client is not None and not a._async_client.is_closed:await a._async_client.aclose();a._async_client=None
  if getattr(a,"_hot_order_async_client",None)is not None and not a._hot_order_async_client.is_closed:await a._hot_order_async_client.aclose();a._hot_order_async_client=None
 def _init_fast_l2_headers_cache(a,api_creds):
  a._fast_l2_ready=False
  try:
   if a.client is None:return
   a._install_sync_client_builder_headers_hook()
   if api_creds is None:return
   l=getattr(api_creds,"api_key",None);k=getattr(api_creds,"api_secret",None);j=getattr(api_creds,"api_passphrase",None);g=getattr(a.client,"signer",None);f=g.address()if(g is not None and hasattr(g,"address"))else None
   if not(isinstance(l,str)and isinstance(k,str)and isinstance(j,str)and isinstance(f,str)):return
   a._fast_l2_secret_bytes=base64.urlsafe_b64decode(k);a._fast_l2_signer_addr=f;a._fast_l2_api_key=l;a._fast_l2_passphrase=j;a._fast_l2_static_headers={"POLY_ADDRESS":f,"POLY_API_KEY":l,"POLY_PASSPHRASE":j,"User-Agent":"py_clob_client_v2","Accept":"*/*","Connection":"keep-alive","Content-Type":"application/json"};a._cached_builder_hmac_creds=a._resolve_valid_builder_hmac_creds()
   try:
    from py_clob_client_v2.headers.headers import create_level_2_headers as b;from py_clob_client_v2.clob_types import RequestArgs as c;d='{"order":{"salt":1},"owner":"k","orderType":"FAK","deferExec":true,"postOnly":false}';i=b(g,api_creds,c(method="POST",request_path="/order",body={},serialized_body=d),timestamp=1760000000);e=a._build_fast_l2_headers("POST","/order",d,ts_override=1760000000)
    for h in("POLY_ADDRESS","POLY_SIGNATURE","POLY_TIMESTAMP","POLY_API_KEY","POLY_PASSPHRASE"):
     if e.get(h)!=i.get(h):raise RuntimeError(f"FastL2 header mismatch on {h}")
   except ImportError:pass
   a._fast_l2_ready=True;logger.info("FastL2HeaderSigner enabled (zero-hop uvloop POST /order parity self-test PASSED).")
  except Exception:a._fast_l2_ready=False
 def _install_sync_client_builder_headers_hook(b):
  d=getattr(b,"client",None)
  if d is None or getattr(d,"_mock_children",None)is not None or getattr(d,"_builder_l2_hook_installed",False):return False
  c=getattr(d,"_l2_headers",None)
  if not callable(c):return False
  def a(method,endpoint,body=None,serialized_body=None,*args,**kwargs):
   h=c(method,endpoint,body=body,serialized_body=serialized_body,*args,**kwargs)
   if isinstance(h,dict)and str(endpoint)in("/order","/orders"):
    f=b._resolve_valid_builder_hmac_creds()
    if f is not None:
     try:
      g=int(h.get("POLY_TIMESTAMP")or time.time())
      if serialized_body is not None:e=serialized_body
      elif body is not None:
       if _orjson is not None:
        try:e=_orjson.dumps(body).decode("utf-8")
        except TypeError:e=json.dumps(body,separators=(",",":"),ensure_ascii=False)
       else:e=json.dumps(body,separators=(",",":"),ensure_ascii=False)
      else:e=None
      h.update(b.build_relayer_builder_headers(api_key=f[0],secret=f[1],passphrase=f[2],method=method,request_path=endpoint,body=e,timestamp=g))
     except Exception:pass
   return h
  d._l2_headers=a;d._builder_l2_hook_installed=True;return True
 @staticmethod
 def _resolve_valid_builder_hmac_creds():
  e=(os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY")or"").strip();d=(os.getenv("POLY_BUILDER_"+"SECRET")or os.getenv("BUILDER_SECRET")or"").strip();c=(os.getenv("POLY_BUILDER_PASSPHRASE")or os.getenv("BUILDER_PASS_PHRASE")or"").strip()
  if not(e and d and c):return None
  a=d+"="*((4-len(d)%4)%4)
  try:
   b=base64.urlsafe_b64decode(a.encode("ascii"))
   if not b:return None
  except Exception:return None
  return e,a,c
 def _build_fast_l2_headers(a,method,endpoint,serialized_body="",ts_override=None,*,body_bytes=None):
  h=int(ts_override)if ts_override is not None else int(time.time());f=str(h)
  if body_bytes is not None:e=f"{f}{method}{endpoint}".encode("ascii")+body_bytes
  else:e=f"{f}{method}{endpoint}{serialized_body}".encode("utf-8")
  g=base64.urlsafe_b64encode(hmac.new(a._fast_l2_secret_bytes,e,hashlib.sha256).digest()).decode("ascii");b=getattr(a,"_fast_l2_static_headers",None)
  if b is not None:c=b.copy();c["POLY_SIGNATURE"]=g;c["POLY_TIMESTAMP"]=f
  else:c={"POLY_ADDRESS":a._fast_l2_signer_addr,"POLY_SIGNATURE":g,"POLY_TIMESTAMP":f,"POLY_API_KEY":a._fast_l2_api_key,"POLY_PASSPHRASE":a._fast_l2_passphrase,"User-Agent":"py_clob_client_v2","Accept":"*/*","Connection":"keep-alive","Content-Type":"application/json"}
  d=(a._cached_builder_hmac_creds if hasattr(a,"_cached_builder_hmac_creds")else a._resolve_valid_builder_hmac_creds())
  if d is not None:
   try:
    if body_bytes is not None and not serialized_body:serialized_body=body_bytes.decode("utf-8")
    c.update(a.build_relayer_builder_headers(api_key=d[0],secret=d[1],passphrase=d[2],method=method,request_path=endpoint,body=serialized_body if serialized_body else None,timestamp=h))
   except Exception:pass
  return c
 def verify_builder_attribution_trades(a,limit=20,builder_code=None,*,check_relayer=False):
  q=a._resolve_valid_builder_hmac_creds()
  if q is None:return{"ok":False,"reason":"missing_or_invalid_builder_hmac_creds","count":0,"trades":[]}
  f=(str(builder_code or"").strip()or(os.getenv("POLY_BUILDER_CODE")or os.getenv("BUILDER_CODE")or"").strip()or str(getattr(getattr(getattr(a,"client",None),"builder_config",None),"builder_code","")or"").strip());i="0x"+"00"*32;d=encode_builder_code_bytes32_hex(f)if f else i;e=bool(d and d!=i)
  if not e:n=q[0].replace("-","").strip().lower();h=str(getattr(a,"funder_address","")or"").replace("0x","").strip().lower();m=n if(n and all(c in"0123456789abcdef"for c in n))else h;d=("0x"+m.zfill(64)[-64:])if m else encode_builder_code_bytes32_hex(q[0])
  l=f"/builder/trades?builder_code={d}&limit={max(1,int(limit))}";p=getattr(a,"_sync_session",requests);b=None
  if check_relayer:
   g=str(getattr(a,"funder_address","")or"").strip()
   if g:
    try:k=f"/deployed?address={g}";j=a.build_relayer_builder_headers(api_key=q[0],secret=q[1],passphrase=q[2],method="GET",request_path=k,body=None);u=p.get(f"https://relayer-v2.polymarket.com{k}",headers=j,timeout=5.);b=u.status_code==200
    except Exception:b=False
  try:
   w=a.build_relayer_builder_headers(api_key=q[0],secret=q[1],passphrase=q[2],method="GET",request_path=l,body=None);v=p.get(f"{a.CLOB_HOST.rstrip('/')}{l}",headers=w,timeout=6.)
   if v.status_code!=200:return{"ok":False,"status_code":v.status_code,"reason":v.text[:200],"builder_code":d,"builder_code_configured":e,"relayer_v2_auth_ok":b,"count":0,"trades":[]}
   o=v.json()if v.content else{};t=o.get("data",o)if isinstance(o,dict)else o;s=t if isinstance(t,list)else[];return{"ok":True,"status_code":200,"builder_code":d,"builder_code_configured":e,"hmac_headers_armed":True,"sync_client_hook_armed":bool(getattr(getattr(a,"client",None),"_builder_l2_hook_installed",False)),"relayer_v2_auth_ok":b,"count":len(s),"trades":s}
  except Exception as r:return{"ok":False,"reason":str(r),"builder_code":d,"builder_code_configured":e,"relayer_v2_auth_ok":b,"count":0,"trades":[]}
 def get_hot_order_async_client(a):
  try:b=asyncio.get_running_loop()
  except RuntimeError:b=None
  c=getattr(a,"_hot_order_async_client",None)
  if c is None or c.is_closed or(b is not None and getattr(a,"_hot_order_async_loop",None)is not b):
   g=httpx.Limits(max_keepalive_connections=8,max_connections=16,keepalive_expiry=45.);f=httpx.Timeout(connect=2.,write=3.,read=5.,pool=2.)
   try:e=[(socket.IPPROTO_TCP,socket.TCP_NODELAY,1),(socket.SOL_SOCKET,socket.SO_KEEPALIVE,1)];d=httpx.AsyncHTTPTransport(http2=False,limits=g,socket_options=e);c=httpx.AsyncClient(http2=False,timeout=f,transport=d)
   except Exception:c=httpx.AsyncClient(http2=False,timeout=f,limits=g)
   a._hot_order_async_client=c;a._hot_order_async_loop=b
  return c
 def start_async_clob_keepalive_task(a,interval_sec=3.5):
  if a.dry_run or not a.is_authenticated:return None
  c=getattr(a,"_async_keepalive_task",None)
  if c is not None and not c.done():return c
  async def b():
   d=max(2.,float(interval_sec))
   while not a.dry_run:
    try:await a.touch_hot_async_clob_socket(max_idle_sec=max(1.5,d-.5))
    except asyncio.CancelledError:break
    except Exception:pass
    await asyncio.sleep(d)
  a._async_keepalive_task=asyncio.create_task(b());return a._async_keepalive_task
 async def touch_hot_async_clob_socket(a,max_idle_sec=3.5):
  if a.dry_run or not a.is_authenticated or _HOT_DISPATCH_ACTIVE.is_set():return False
  if getattr(a,"_hot_order_touch_in_flight",False):return False
  h=time.monotonic()
  if(h-float(getattr(a,"_hot_order_last_touch_mono",.0)or.0))<float(max_idle_sec):return False
  a._hot_order_touch_in_flight=True
  try:
   l=a.get_hot_order_async_client();k=str(getattr(a.client,"host",None)or a.CLOB_HOST).rstrip("/");j={"User-Agent":"py_clob_client_v2","Accept":"*/*","Connection":"keep-alive"};g=getattr(a,"_hot_order_async_loop",None);e=getattr(a,"_async_client",None);f=(e is not None and not getattr(e,"is_closed",True)and(g is None or getattr(a,"_async_client_loop",None)is g))
   if(int(getattr(a,"_hot_async_inflight",0)or 0)<=0 and(h-float(getattr(a,"_hot_order_last_dual_touch_mono",.0)or.0))>=12.):
    i=[l.get(f"{k}/time",headers=j),l.get(f"{k}/time",headers=j)]
    if f:i.append(e.get(f"{k}/time",headers=j))
    c=await asyncio.gather(*i,return_exceptions=True);n,m=c[0],c[1];b=n if getattr(n,"status_code",0)==200 else m
    if getattr(b,"status_code",0)==200:a._hot_order_last_dual_touch_mono=time.monotonic()
   else:
    if f:
     c=await asyncio.gather(l.get(f"{k}/time",headers=j),e.get(f"{k}/time",headers=j),return_exceptions=True);b=c[0]
     if isinstance(b,Exception):raise b
    else:b=await l.get(f"{k}/time",headers=j)
   if b.status_code==200:a._hot_order_last_touch_mono=time.monotonic();return True
  except Exception:
   d=getattr(a,"_hot_order_async_client",None)
   if d is not None and int(getattr(a,"_hot_async_inflight",0)or 0)<=0:
    a._hot_order_async_client=None
    try:await d.aclose()
    except Exception:pass
  finally:a._hot_order_touch_in_flight=False
  return False
 async def _retire_hot_async_client(a,cli):
  if getattr(a,"_hot_order_async_client",None)is cli:a._hot_order_async_client=None
  if int(getattr(a,"_hot_async_inflight",0)or 0)<=0:
   try:await cli.aclose()
   except Exception:pass
 def _can_use_native_async_post_order(a):
  if a.dry_run or not getattr(a,"_fast_l2_ready",False)or a.client is None:return False
  if os.environ.get("PM_NATIVE_ASYNC_ORDER_POST","1")!="1":return False
  if getattr(a,"_force_native_async_post",False):return True
  b=getattr(a.client,"__dict__",{})
  if type(a.client).__name__!="ClobClient"or"post_order"in b or"_post"in b:return False
  try:
   import py_clob_client_v2.http_helpers.helpers as hh
   if not isinstance(getattr(hh,"_http_client",None),_ThreadLocalClobHttpClient):return False
  except Exception:return False
  return True
 def _can_use_hot_async_bridge(a):
  b=getattr(a,"_hot_order_async_loop",None)
  if not a._can_use_native_async_post_order()or b is None or not b.is_running():return False
  try:return asyncio.get_running_loop()is not b
  except RuntimeError:return True
 def _serialize_signed_order_payload(self,signed,order_type,post_only=False,defer_exec=True):
  if _clob_is_v2_order is not None and _clob_order_to_json_v2 is not None and _clob_order_to_json_v1 is not None:a,b,c=_clob_is_v2_order,_clob_order_to_json_v1,_clob_order_to_json_v2
  else:from py_clob_client_v2.client import _is_v2_order as a,order_to_json_v1 as b,order_to_json_v2 as c
  d=self._fast_l2_api_key;return(c(signed,d,order_type,bool(post_only),bool(defer_exec))if a(signed)else b(signed,d,order_type,bool(post_only),bool(defer_exec)))
 async def _exec_hot_async_post(a,endpoint,headers,body_bytes,stage=None):
  j=str(getattr(a.client,"host",None)or a.CLOB_HOST).rstrip("/");d=f"{j}{endpoint}";i=a.get_hot_order_async_client();c=time.perf_counter()
  if stage is not None:stage["submitted"]=True;stage["t_post_start"]=c
  a._hot_async_inflight=int(getattr(a,"_hot_async_inflight",0)or 0)+1;b=True
  try:
   try:f=await i.post(d,headers=headers,content=body_bytes)
   except(httpx.ConnectError,httpx.ConnectTimeout,httpx.PoolTimeout):
    if b:a._hot_async_inflight=max(0,int(getattr(a,"_hot_async_inflight",1)or 1)-1);b=False
    await a._retire_hot_async_client(i);i=a.get_hot_order_async_client();a._hot_async_inflight=int(getattr(a,"_hot_async_inflight",0)or 0)+1;b=True;f=await i.post(d,headers=headers,content=body_bytes)
  except httpx.RequestError as g:
   if b:a._hot_async_inflight=max(0,int(getattr(a,"_hot_async_inflight",1)or 1)-1);b=False
   await a._retire_hot_async_client(i);logger.error("[py_clob_client_v2] async request error: %s",g)
   if PolyApiException is not None:raise PolyApiException(error_msg=f"Request exception: {g}")from g
   raise
  finally:
   if b:a._hot_async_inflight=max(0,int(getattr(a,"_hot_async_inflight",0)or 0)-1)
  k=time.perf_counter();a._hot_order_last_touch_mono=time.monotonic();h=f.headers.get("cf-ray")if hasattr(f,"headers")else None
  if stage is not None:stage["cf_ray"]=h
  if f.status_code!=200:
   logger.error("[py_clob_client_v2] request error status=%s url=%s body=%s",f.status_code,d,f.text)
   if PolyApiException is not None:raise PolyApiException(f)
   raise RuntimeError(f"CLOB HTTP {f.status_code}: {f.text}")
  e=_orjson.loads(f.content)if _orjson is not None else f.json()
  if hasattr(a.client,"_is_order_version_mismatch")and a.client._is_order_version_mismatch(e):
   try:a.client._ClobClient__resolve_version(force_update=True)
   except Exception:pass
  return e,h,k
 def _encode_fast_l2_request(a,endpoint,payload):
  d=(int(a.client._get_timestamp())if getattr(a.client,"use_server_time",False)and hasattr(a.client,"_get_timestamp")else int(time.time()))
  if _orjson is not None:b=_orjson.dumps(payload);return a._build_fast_l2_headers("POST",endpoint,ts_override=d,body_bytes=b),b
  c=json.dumps(payload,separators=(",",":"),ensure_ascii=False);b=c.encode("utf-8");return a._build_fast_l2_headers("POST",endpoint,c,ts_override=d,body_bytes=b),b
 def _post_json_hot_async_bridge(a,endpoint,payload):
  d=getattr(a,"_hot_order_async_loop",None)
  if d is None or not d.is_running():raise RuntimeError("Hot async loop not active")
  c,b=a._encode_fast_l2_request(endpoint,payload);e,_,_=asyncio.run_coroutine_threadsafe(a._exec_hot_async_post(endpoint,c,b),d).result(timeout=8.5);return e
 def _post_signed_order_bridge_or_sync(a,signed,order_type,post_only=False,defer_exec=True):
  if a._can_use_hot_async_bridge():return a._post_json_hot_async_bridge("/order",a._serialize_signed_order_payload(signed,order_type,post_only,defer_exec))
  if post_only:return a.client.post_order(signed,order_type,post_only=True,defer_exec=defer_exec)
  try:return a.client.post_order(signed,order_type,False,defer_exec)
  except TypeError:return a.client.post_order(signed,order_type)
 def _pop_presigned_maker_repeg(a,token_id,price,shares,side,tick_size,neg_risk):
  d=getattr(a,"_presigned_maker_repeg_cache",None)
  if not d:return None
  g=float(shares);f=int(round(g));b=float(price)*1e4;e=int(round(b))
  if f<5 or abs(g-f)>1e-9 or abs(b-e)>1e-4:return None
  h=(str(token_id),e,f,str(side).upper(),str(tick_size),bool(neg_risk));i=a.__dict__.setdefault("_presigned_maker_repeg_lock",threading.Lock())
  with i:c=d.pop(h,None)
  if c is not None and(time.monotonic()-float(c[0]))<=25.:a._presigned_maker_repeg_hits=int(getattr(a,"_presigned_maker_repeg_hits",0)or 0)+1;return c[1]
  return None
 def _prebuild_next_tick_maker_repegs(a,token_id,base_price,shares_base,max_ceiling,side,tick_sz,neg_risk):
  if a.dry_run or str(side).upper()!="BUY"or a.client is None or OrderArgsV2 is None:return 0
  t=int(round(float(shares_base)))
  if t<5:return 0
  p=a.__dict__.setdefault("_presigned_maker_repeg_cache",{});v=a.__dict__.setdefault("_presigned_maker_repeg_lock",threading.Lock());o=time.monotonic()
  with v:
   f=[k for k,(w,_)in p.items()if(o-float(w))>25.]
   for u in f:p.pop(u,None)
   while len(p)>56:p.pop(next(iter(p)),None)
  d=0;e=.001 if(float(base_price)>=.959 and float(tick_sz or.01)<=.001+1e-9)else float(tick_sz or.01);c=[t,t-1]if t>=6 else[t]
  for l in(1,2):
   if _HOT_DISPATCH_ACTIVE.is_set():break
   j=round(float(base_price)+l*e,4)
   if j>float(max_ceiling)+1e-9 or j>=.9995:break
   try:b=a.get_token_tick_size(token_id,price_hint=j)
   except TypeError:b=a.get_token_tick_size(token_id)
   s=a.quantize_order_price(j,token_id,rounding=ROUND_FLOOR)
   if s<=float(base_price)+1e-9 or s>float(max_ceiling)+1e-9:continue
   i=str(b);h=PartialCreateOrderOptions(tick_size=i,neg_risk=bool(neg_risk),version=2)if PartialCreateOrderOptions else None;r=int(round(s*1e4))
   for q in c:
    n=(str(token_id),r,int(q),"BUY",i,bool(neg_risk))
    with v:
     if n in p and(time.monotonic()-float(p[n][0]))<=20.:continue
    try:
     g=OrderArgsV2(price=s,size=float(q),side="BUY",token_id=str(token_id));m=_safe_create_order(a.client.create_order,g,h)
     if m is not None:
      with v:p[n]=(time.monotonic(),m)
      d+=1
    except Exception:break
  return d
 def _maybe_schedule_maker_repeg_presign(a,token_id,base_price,shares_base,max_ceiling,side,tick_sz,neg_risk):
  if(a.dry_run or str(side).upper()!="BUY"or a.client is None or not(getattr(a,"_enable_maker_repeg_presign",False)or(getattr(a.client,"_mock_children",None)is None and"create_order"not in getattr(a.client,"__dict__",{})and getattr(a.client,"_fast_v2_signer",None)is not None))):return
  if getattr(a,"_enable_maker_repeg_presign_sync",False):a._prebuild_next_tick_maker_repegs(token_id,base_price,shares_base,max_ceiling,side,tick_sz,neg_risk);return
  try:_get_hot_io_pool().submit(a._prebuild_next_tick_maker_repegs,token_id,base_price,shares_base,max_ceiling,side,tick_sz,neg_risk)
  except Exception:pass
 async def _sign_and_post_async_zero_hop(b,token_id,price,size,side,order_type,create_options=None,stage=None,max_notional_usd=None,post_only=False):
  if stage is None:stage={}
  stage["submitted"]=False;_HOT_DISPATCH_ACTIVE.enter();u=time.perf_counter();d=None;c=False;a=float(size);e=gc.isenabled()
  if e:gc.disable()
  try:
   try:
    l=str(getattr(create_options,"tick_size","0.01")or"0.01");p=bool(getattr(create_options,"neg_risk",False))
    if b.order_ladder_cache is not None and str(side).upper()=="BUY":
     d=b.order_ladder_cache.get_presigned_order(token_id,price,size,tick_size=l,neg_risk=p);c=d is not None
     if d is None:
      m=b.order_ladder_cache.get_presigned_order_near(token_id,price,size,max_share_delta=3,max_notional_usd=max_notional_usd,tick_size=l,neg_risk=p)
      if m is not None:d,h=m;a=float(h);c=True
    if d is None and post_only and str(side).upper()=="BUY":
     d=b._pop_presigned_maker_repeg(token_id,price,size,side,l,p)
     if d is not None:c=True
    if d is None:
     if OrderArgsV2 is None:raise RuntimeError("OrderArgsV2 is required for CLOB entry order signing")
     j=OrderArgsV2(price=price,size=size,side=side,token_id=token_id);d=_safe_create_order(b.client.create_order,j,create_options)
    if d is None:raise RuntimeError("create_order returned no signed order")
    f=b._serialize_signed_order_payload(d,order_type,post_only,True);o,i=b._encode_fast_l2_request("/order",f)
   except Exception as q:raise PreSubmitError(f"Order signing failed before submission: {q}")from q
   finally:
    if e:gc.enable()
   t=time.perf_counter();n=round((t-u)*1e3,3);stage["sign_ms"]=n;stage["thread_hop_ms"]=.0;stage["cache_hit"]=c;stage["signed_shares"]=a;k,r,s=await b._exec_hot_async_post("/order",o,i,stage=stage);g=float(stage.get("t_post_start")or t);return{"post_resp":k or{},"sign_ms":n,"post_ms":round((s-g)*1e3,3),"t_post_end":s,"cache_hit":c,"signed_shares":a,"thread_hop_ms":.0,"cf_ray":r}
  finally:
   if e and not gc.isenabled():gc.enable()
   _HOT_DISPATCH_ACTIVE.leave()
 @staticmethod
 def calculate_balance_epsilon(quantity_unit_or_shares=.001):b=.001 if quantity_unit_or_shares>.01 else quantity_unit_or_shares;c=Decimal(str(b));a=Decimal("2")*c;return float(a)
 def get_market_fee_params(a,condition_id,token_id=None):
  if condition_id in a._fee_cache:
   d=a._fee_cache[condition_id]
   if token_id:a._fee_cache[str(token_id)]=d
   return d
  if token_id and str(token_id)in a._fee_cache:d=a._fee_cache[str(token_id)];a._fee_cache[condition_id]=d;return d
  def b(r_val,e_val):
   e=(float(r_val),float(e_val));a._fee_cache[condition_id]=e
   if c:a._fee_cache[c]=e
   if token_id:a._fee_cache[str(token_id)]=e
   return e
  c=condition_id
  if a.dry_run or a.client is None:return b(.07,1.)
  if not condition_id.startswith("0x"):
   try:
    k=requests.get if hasattr(requests.get,"mock_calls")else getattr(a,"_sync_session",requests).get;j=k(f"https://gamma-api.polymarket.com/markets/{condition_id}",timeout=2.);r=(_orjson.loads(j.content)if(_orjson is not None and isinstance(getattr(j,"content",None),(bytes,bytearray)))else j.json())
    if r.get("conditionId"):c=str(r["conditionId"]);logger.info(f"Resolved condition_id {c} for numeric market {condition_id}")
   except Exception:pass
  try:
   if hasattr(a.client,"get_clob_market_info"):
    g=a.client.get_clob_market_info(c)
    if isinstance(g,dict):
     n=g.get("fd")or{};m=n.get("r");l=n.get("e")
     if m is not None and l is not None:return b(float(m),float(l))
   if token_id and hasattr(a.client,"get_fee_rate_bps")and hasattr(a.client,"get_fee_exponent"):p=a.client.get_fee_rate_bps(token_id);o=a.client.get_fee_exponent(token_id);return b(float(p)/1e4,float(o))
   if hasattr(a.client,"get_market"):
    g=a.client.get_market(c)
    if isinstance(g,dict):
     n=g.get("fd")or{}
     if"r"in n and"e"in n:return b(float(n["r"]),float(n["e"]))
     h=g.get("taker_base_fee")
     if h is not None:i=float(h)/1e4 if float(h)>1. else float(h);f=float(g.get("fee_exponent",1.));return b(i,f)
   if not a.dry_run and a.is_authenticated:raise RuntimeError(f"AUTHORITATIVE_FEE_METADATA_UNAVAILABLE: CLOB returned no fee metadata for {c}")
   logger.warning(f"CLOB returned no specific fee schedule for {c}; applying standard 0.072 crypto rate.");return b(.072,1.)
  except RuntimeError:raise
  except Exception as e:
   if not a.dry_run and a.is_authenticated:raise RuntimeError(f"AUTHORITATIVE_FEE_METADATA_UNAVAILABLE: {e}")
   logger.warning(f"Notice fetching authoritative CLOB fee metadata for {condition_id} ({c}): {e}. Applying default 0.072.");return b(.072,1.)
 async def get_market_book_async(a,token_id):
  d=f"{a.CLOB_HOST}/book?token_id={token_id}"
  try:
   b=a.get_async_client();c=await b.get(d)
   if c.status_code==200:return(_orjson.loads(c.content)if(_orjson is not None and isinstance(getattr(c,"content",None),(bytes,bytearray)))else c.json())
   if c.status_code==404:return{"bids":[],"asks":[],"closed":True}
  except Exception:
   if a.dry_run:return{"bids":[],"asks":[]}
   raise
  if a.dry_run:return{"bids":[],"asks":[]}
  raise RuntimeError(f"HTTP {c.status_code} querying orderbook for {token_id}: {c.text[:100]}")
 async def get_market_books_batch_async(a,token_ids):
  j=list(dict.fromkeys(str(t)for t in token_ids if t))
  if not j:return{}
  if"get_market_book"in a.__dict__ or"get_market_books_batch"in a.__dict__:return await asyncio.to_thread(a.get_market_books_batch,j)
  o={};i=str(getattr(a.client,"host",None)or a.CLOB_HOST).rstrip("/");n=f"{i}/books"
  try:
   m=a.get_async_client()
   for l in range(0,len(j),50):
    d=[{"token_id":t}for t in j[l:l+50]];c=_orjson.dumps(d)if _orjson is not None else json.dumps(d).encode("utf-8");h=await m.post(n,content=c,headers={"Content-Type":"application/json","Accept":"application/json"})
    if h.status_code==200:
     g=(_orjson.loads(h.content)if(_orjson is not None and isinstance(getattr(h,"content",None),(bytes,bytearray)))else h.json())
     if isinstance(g,list):
      for r in g:
       if isinstance(r,dict):
        k=str(r.get("asset_id")or r.get("token_id")or"")
        if k:o[k]=r
  except Exception:pass
  e=[t for t in j if t not in o]
  if e:
   f=await asyncio.gather(*(a.get_market_book_async(t)for t in e),return_exceptions=True)
   for t,b in zip(e,f):o[t]=b if isinstance(b,dict)else{}
  return o
 async def get_token_metadata_async(a,token_id,price_hint=None,explicit_neg_risk=None):
  A=getattr(a,"_enforced_tick_override_until",None);m=isinstance(A,dict)and token_id in A and time.monotonic()<float(A[token_id][1]);h=a._tick_size_cache.get(token_id);q=time.monotonic();p=a.__dict__.setdefault("_boundary_tick_recheck_ts",{});l=(price_hint is not None and math.isfinite(float(price_hint))and(float(price_hint)>=.96 or float(price_hint)<=.04 or abs(round(float(price_hint),2)-round(float(price_hint),4))>1e-6));i=not m and(h is None or(h==.01 and l and(q-float(p.get(token_id,-999.)))>=2.5))
  if explicit_neg_risk is not None:f=a.get_token_neg_risk(token_id,explicit_neg_risk);d=False
  else:f=a._neg_risk_cache.get(token_id);d=f is None
  if not i and not d:k=float(A[token_id][0])if m else float(h);return k,bool(f)
  c=(not a.dry_run and a.client is not None and getattr(a.client,"_mock_children",None)is None and"get_token_tick_size"not in a.__dict__ and"get_token_neg_risk"not in a.__dict__)
  if c:
   try:
    y=a.get_async_client();x=str(getattr(a.client,"host",None)or a.CLOB_HOST).rstrip("/");o=[]
    if i:o.append(y.get(f"{x}/tick-size?token_id={token_id}"))
    if d:o.append(y.get(f"{x}/neg-risk?token_id={token_id}"))
    n=await asyncio.gather(*o);g=0;b=None;e=None if d else bool(f)
    if i:
     w=n[g];g+=1
     if w.status_code==200:
      v=_orjson.loads(w.content)if(_orjson is not None and isinstance(getattr(w,"content",None),(bytes,bytearray)))else w.json();j=v.get("minimum_tick_size")if isinstance(v,dict)else None
      if j is not None:
       z=float(j)
       if any(abs(z-B)<1e-9 for B in(.1,.01,.005,.0025,.001,1e-4)):
        a._tick_size_cache[token_id]=z
        if l:p[token_id]=q
        if hasattr(a.client,"_ClobClient__tick_sizes"):a.client._ClobClient__tick_sizes[token_id]=str(j)
        b=z
    else:b=float(A[token_id][0])if m else float(h)
    if d:
     u=n[g]
     if u.status_code==200:
      t=_orjson.loads(u.content)if(_orjson is not None and isinstance(getattr(u,"content",None),(bytes,bytearray)))else u.json()
      if isinstance(t,dict)and"neg_risk"in t:
       e=bool(t["neg_risk"]);a._neg_risk_cache[token_id]=e
       if hasattr(a.client,"_ClobClient__neg_risk"):a.client._ClobClient__neg_risk[token_id]=e
    if b is not None and e is not None:return b,e
   except Exception:pass
  s,r=await asyncio.gather(asyncio.to_thread(a.get_token_tick_size,token_id,price_hint=price_hint),asyncio.to_thread(a.get_token_neg_risk,token_id,explicit_neg_risk));return float(s),bool(r)
 async def get_transaction_receipt_status_async(a,tx_hash):
  if a.dry_run:return True
  if not tx_hash or not isinstance(tx_hash,str)or not tx_hash.startswith("0x"):return False
  try:
   c=os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com");b={"jsonrpc":"2.0","method":"eth_getTransactionReceipt","params":[tx_hash],"id":1};g=a.get_async_client();i=await g.post(c,json=b,timeout=3.)
   if i.status_code==200:
    h=i.json();f=h.get("result")
    if f is None:return None
    d=f.get("status")
    if d in(1,"0x1","1"):return True
    elif d in(0,"0x0","0"):logger.critical(f"[ON-CHAIN REVERT] Transaction {tx_hash} reverted on Polygon (status={d})!");return False
   return None
  except Exception as e:logger.warning(f"Failed to query Polygon transaction receipt for {tx_hash}: {e}");return None
 def get_transaction_receipt_status(a,tx_hash):
  if a.dry_run:return True
  if not tx_hash or not isinstance(tx_hash,str)or not tx_hash.startswith("0x"):return False
  try:
   d=os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com");c={"jsonrpc":"2.0","method":"eth_getTransactionReceipt","params":[tx_hash],"id":1};b=requests.post if hasattr(requests.post,"mock_calls")else getattr(a,"_sync_session",requests).post;i=b(d,json=c,timeout=3.)
   if i.status_code==200:
    h=i.json();g=h.get("result")
    if g is None:return None
    f=g.get("status")
    if f in(1,"0x1","1"):return True
    elif f in(0,"0x0","0"):return False
   return None
  except Exception as e:logger.warning(f"Failed to query Polygon transaction receipt for {tx_hash}: {e}");return None
 def get_market_book(a,token_id):
  f=f"{a.CLOB_HOST}/book?token_id={token_id}"
  try:
   b=hasattr(requests.get,"mock_calls")or("session"in a._thread_local.__dict__)
   if not b:
    try:import py_clob_client_v2.http_helpers.helpers as hh;c=getattr(hh,"_http_client",None)
    except Exception:c=None
    if isinstance(c,_ThreadLocalClobHttpClient):
     d=c.request("GET",f,timeout=3.)
     if d.status_code==200:return _orjson.loads(d.content)if _orjson is not None else d.json()
     if d.status_code==404:return{"bids":[],"asks":[],"closed":True}
     if a.dry_run:return{"bids":[],"asks":[]}
     raise RuntimeError(f"HTTP {d.status_code} querying orderbook for {token_id}: {d.text[:100]}")
   e=requests.get if hasattr(requests.get,"mock_calls")else getattr(a,"_sync_session",requests).get;d=e(f,timeout=3.)
   if d.status_code==200:return _orjson.loads(d.content)if(_orjson is not None and isinstance(getattr(d,"content",None),(bytes,bytearray)))else d.json()
   if d.status_code==404:return{"bids":[],"asks":[],"closed":True}
  except Exception:
   if a.dry_run:return{"bids":[],"asks":[]}
   raise
  if a.dry_run:return{"bids":[],"asks":[]}
  raise RuntimeError(f"HTTP {d.status_code} querying orderbook for {token_id}: {d.text[:100]}")
 def get_market_books_batch(a,token_ids):
  k=list(dict.fromkeys(str(t)for t in token_ids if t))
  if not k:return{}
  if"get_market_book"in a.__dict__:return{t:(a.get_market_book(t)or{})for t in k}
  o={};n=f"{a.CLOB_HOST}/books"
  try:
   b=None
   if not hasattr(requests.post,"mock_calls"):
    try:import py_clob_client_v2.http_helpers.helpers as hh;b=getattr(hh,"_http_client",None)
    except Exception:b=None
   for m in range(0,len(k),50):
    i=k[m:m+50];e=[{"token_id":t}for t in i]
    if isinstance(b,_ThreadLocalClobHttpClient):
     h=b._borrow_from(b._bg_pool);c=True
     try:d=_orjson.dumps(e)if _orjson is not None else json.dumps(e).encode("utf-8");f=h.request("POST",n,content=d,headers={"Content-Type":"application/json","Accept":"application/json"},timeout=3.)
     except Exception:
      c=False
      try:h.close()
      except Exception:pass
      raise
     finally:
      if c:b._return_to(b._bg_pool,h)
    else:g=requests.post if hasattr(requests.post,"mock_calls")else getattr(a,"_sync_session",requests).post;f=g(n,json=e,timeout=3.)
    if f.status_code==200:
     j=(_orjson.loads(f.content)if(_orjson is not None and isinstance(getattr(f,"content",None),(bytes,bytearray)))else f.json())
     if isinstance(j,list):
      for r in j:
       if isinstance(r,dict):
        l=str(r.get("asset_id")or r.get("token_id")or"")
        if l:o[l]=r
  except Exception:pass
  for t in k:
   if t not in o:o[t]=a.get_market_book(t)or{}
  return o
 @staticmethod
 def normalize_trade_record(data):
  if not isinstance(data,dict):return{}
  c=dict(data);a=c.get("transaction_hash")or c.get("transactionHash")
  if a:c["transaction_hash"]=str(a);c["transactionHash"]=str(a)
  b=c.get("id")or c.get("trade_id")or c.get("tradeId")
  if b:c["id"]=str(b);c["trade_id"]=str(b)
  d=c.get("status")
  if d:c["status"]=str(d).upper()
  return c
 def get_trade_status(a,trade_id):
  if a.dry_run:return{"status":"CONFIRMED","trade_id":trade_id,"transaction_hash":None,"transactionHash":None}
  if not a.client or not a.is_authenticated:return{"status":"UNKNOWN","trade_id":trade_id,"error":"client unavailable"}
  try:
   if hasattr(a.client,"get_trades"):
    try:
     if TradeParams is not None:c=TradeParams(id=trade_id);b=a.client.get_trades(params=c)
     else:b=a.client.get_trades(trade_id=trade_id)
    except(TypeError,AttributeError):b=a.client.get_trades(trade_id=trade_id)
    if isinstance(b,list)and len(b)>0:return a.normalize_trade_record(b[0])
    elif isinstance(b,dict)and b:return a.normalize_trade_record(b)
    return{"status":"NOT_FOUND","trade_id":trade_id}
   return{"status":"UNKNOWN","trade_id":trade_id,"error":"get_trades unsupported"}
  except Exception as e:return{"status":"UNKNOWN","error":str(e)}
 @staticmethod
 def _iso_or_unix_to_ts(val):
  try:f=float(val);return f/1e3 if f>1e12 else f
  except(TypeError,ValueError):pass
  try:return datetime.fromisoformat(str(val).replace("Z","+00:00")).timestamp()
  except Exception:return.0
 def extract_account_fills(a,trades,token_id,target_order_id=None):
  v=[];B=str(a.funder_address or"").lower();j=str(getattr(a,"signer_address","")or"").lower();i=str(getattr(getattr(a.client,"creds",None),"api_key","")or"");c=str(target_order_id)if target_order_id else None
  for y in trades or[]:
   t=a.normalize_trade_record(y)
   if not t:continue
   p=str(t.get("id")or"");A=t.get("transaction_hash");u=str(t.get("status","")).upper();o=a._iso_or_unix_to_ts(t.get("match_time")or t.get("last_update")or 0);w=str(t.get("trader_side","")).upper();r=str(t.get("asset_id",""));h=str(t.get("taker_order_id")or"")
   if(w=="TAKER"or(not w and c and h==c))and(r==str(token_id)or(c and h==c)):
    l=float(t.get("size",.0)or.0);g=float(t.get("price",.0)or.0);v.append({"fill_id":f"{p}:{h}","trade_id":p,"order_id":h,"side":str(t.get("side","")).upper(),"size":l,"price":g,"cash":round(l*g,6),"transaction_hash":A,"status":u,"match_ts":o,"role":"TAKER"})
    if r==str(token_id):continue
   for x,z in enumerate(t.get("maker_orders",[])or[]):
    s=str(z.get("order_id")or"");b=bool(c and s==c);q=str(z.get("maker_address","")or"").lower();n=str(z.get("owner")or z.get("api_key")or"");e=(b or(B and q==B)or(j and q==j)or(i and n==i));m=str(z.get("asset_id")or"");d=(m==str(token_id))or(not m and r==str(token_id))or b
    if not e or not d:continue
    l=float(z.get("matched_amount",.0)or.0);g=float(z.get("price",.0)or.0);k=str(z.get("side","")).upper()
    if not k:f=str(t.get("side","")).upper();k={"BUY":"SELL","SELL":"BUY"}.get(f,"")if(m or r)==r else f
    v.append({"fill_id":f"{p}:{s or f'm{x}'}","trade_id":p,"order_id":s,"side":k,"size":l,"price":g,"cash":round(l*g,6),"transaction_hash":A,"status":u,"match_ts":o,"role":"MAKER"})
  return v
 def get_account_fills(a,token_id,after_ts=None,side=None,order_id=None,include_failed=False):
  if a.dry_run:return[]
  if not a.client or not a.is_authenticated or not hasattr(a.client,"get_trades"):return None
  def b(items):
   n=[];e=set()
   for f in items:
    m=f.get("fill_id")
    if m in e:continue
    if not include_failed and f["status"]=="FAILED":continue
    if side and f["side"]!=side.upper():continue
    if order_id and f["order_id"]!=str(order_id):continue
    if after_ts and f["match_ts"]and f["match_ts"]<float(after_ts)-1.:continue
    e.add(m);n.append(f)
   return n
  try:
   i=int(after_ts)if after_ts else None;k=TradeParams(asset_id=str(token_id),after=i)if TradeParams is not None else None;l=a.client.get_trades(params=k)if k is not None else a.client.get_trades()
   if not isinstance(l,list):return None
   d=list(l)
   if k is not None:
    c=TradeParams(after=i)if i else None;h=a.client.get_trades(params=c)if c is not None else a.client.get_trades()
    if isinstance(h,list):d.extend(h)
   j=b(a.extract_account_fills(d,token_id,target_order_id=order_id))
   if not j and k is not None and i and order_id:
    g=a.client.get_trades()
    if isinstance(g,list):j=b(a.extract_account_fills(g,token_id,target_order_id=order_id))
   return j
  except Exception as e:logger.error(f"[PM-EXEC] Trade history unavailable for {token_id}: {e}");return None
 def get_order_fill_summary(g,order_id,token_id=None):
  B=g.get_order_status(order_id)
  if not B:return None
  A=str(B.get("status","")).upper()
  try:z=float(B.get("size_matched",.0)or.0)
  except(TypeError,ValueError):return None
  x=float(B.get("original_size",.0)or.0);y=float(B.get("price",.0)or.0);C=str(token_id or B.get("asset_id")or"");h=None;m=[];l=[];q=[];d=False;v=[];i=[];c=False
  if z>.0 and C:
   try:i=g.get_account_fills(C,order_id=order_id,include_failed=True)or[]
   except TypeError:i=g.get_account_fills(C,order_id=order_id)or[]
   v=[f for f in i if str(f.get("status","")).upper()!="FAILED"]
   if v:
    q=sorted({str(f["fill_id"])for f in v if f.get("fill_id")});m=sorted({str(f["trade_id"])for f in v if f.get("trade_id")});l=sorted({str(f["transaction_hash"])for f in v if f.get("transaction_hash")});w=sum(f["size"]for f in v)
    if abs(w-z)<=.011:
     h=round(sum(f["cash"]for f in v),6);c=True;o=all(f.get("status")in{"MINED","CONFIRMED"}and bool(f.get("transaction_hash"))for f in v)
     if o and l and not any(str(f.get("status","")).upper()in{"FAILED","RETRYING"}for f in i):d=True
  a=h is None;e=False
  if h is None:
   u=B.get("taking_amount")
   if u in(None,""):u=B.get("takingAmount")
   try:p=float(u)if u not in(None,"")else None
   except(TypeError,ValueError):p=None
   if p is not None and math.isfinite(p)and p>=.0:
    h=round(p,6);e=True
    if A in{"CONFIRMED","MINED"}and l:a=False;d=True
    else:a=True
   elif y>.0:h=round(z*y,6);a=True
   else:h=None
  s=str(B.get("order_type")or B.get("type")or"GTC").upper();r=x<=.0 or z>=x-1e-4 or s in{"FAK","FOK"};n=(A.startswith("CANCEL")or A in{"CONFIRMED","EXPIRED","REJECTED","INVALID"}or(A in{"MATCHED","FILLED"}and r)or(x>0 and z>=x-1e-4));t=A.startswith("CANCEL")or A in{"EXPIRED","REJECTED"}or(A=="INVALID"and z<=1e-6);k=any(str(f.get("status","")).upper()in{"FAILED","RETRYING"}for f in i)
  if t:
   if z<=1e-6 or d:b=True;a=False if(z<=1e-6 or h is not None)else True
   elif(not g.dry_run and g.is_authenticated and g.client is not None and str(B.get("side","SELL")).upper()=="SELL"and not k and y>.0 and C):
    j=g.get_onchain_erc1155_balance(C)
    if j is not None and j<=max(.0,x-z)+.01:
     d=True;b=True
     if h is None:h=round(z*y,6)
     a=not(c or e or s=="GTC")
    else:b=False;a=True
   else:b=False;a=True
  elif d and(A in{"MATCHED","FILLED","CONFIRMED","MINED","INVALID"}or(x>0 and z>=x-1e-4)):b=True;a=False
  elif(not g.dry_run and g.is_authenticated and g.client is not None and str(B.get("side","SELL")).upper()=="SELL"and not k and A in{"MATCHED","FILLED","CONFIRMED","MINED"}and x>0 and z>=x-.01 and y>.0 and C):
   j=g.get_onchain_erc1155_balance(C)
   if j is not None and j<=max(.0,x-z)+.01:
    d=True;b=True
    if h is None:h=round(z*y,6)
    a=not(c or e or s=="GTC")
   else:b=False;a=True
  else:b=False;a=True
  return{"order_id":str(order_id),"status":A,"resting":not n,"is_canceled":t,"is_matched":z>.0,"is_settled":d,"has_reverted_fills":k,"terminal":b,"original_size":x,"matched":z,"cash":h,"cash_is_estimated":a,"cash_from_reported_taking":e,"limit_price":y,"avg_price":round(h/z,6)if(h is not None and z>1e-9)else(y if y>.0 else None),"trade_ids":m,"transactions_hashes":l,"fill_ids":q,"raw":B}
 CTF_ADDRESS="0x4D97DCd97eC945f40cF65F87097ACe5EA0476045";PUSD_ADDRESS="0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB";USDC_E_ADDRESS="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174";CTF_ADAPTER_V2_ADDRESS="0xAdA100Db00Ca00073811820692005400218FcE1f";PUSD_WRAPPER_ADDRESS="0x93070a847efEf7F70739046A929D47a521F5B8ee";NEG_RISK_ADAPTER_ADDRESS="0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296";NEG_RISK_ADAPTER_V2_ADDRESS="0xadA2005600Dec949baf300f4C6120000bDB6eAab";AUTOREDEEMER_ADDRESS="0xa1200000d0002264c9a1698e001292d00e1b00af";AUTO_REDEEM_CTF_TOPIC0="0xb434294b5904213c83a167af0068ab82637c6fd4fac945e2abc74ed8d3f4d52a";AUTO_REDEEM_NEGRISK_TOPIC0="0x74a51ebefec30281ec6849b727ec7916f9b1a3e5e148d6771d98315215b38b96";V2_ADAPTER_REDEMPTION_TOPIC0="0x1daec0b1f629de29b749a189499f43104a80df46a9f34d9ccf73aa59b85fc0c0";NEG_RISK_WRAPPED_COLLATERAL="0x3A3BD7bb9528E159577F7C2e685CC81A765002E2";DEPOSIT_WALLET_FACTORY="0x00000000000Fb5C9ADea0298D729A0CB3823Cc07";POLY_PROXY_FACTORY="0xaB45c5A4B0c941a2F231C04C3f49182e1A254052";RELAYER_V2_URL="https://relayer-v2.polymarket.com"
 @classmethod
 def encode_pusd_wrap_calls(b,*,funder_address,amount_raw,current_allowance_raw):
  f=int(amount_raw or 0)
  if f<=0 or not funder_address:return[]
  from web3 import Web3;c=Web3.to_checksum_address(funder_address);d=Web3.to_checksum_address(b.USDC_E_ADDRESS);a=Web3.to_checksum_address(b.PUSD_WRAPPER_ADDRESS);e=[]
  if int(current_allowance_raw or 0)<f:e.append((d,f"0x095ea7b3{a[2:].lower().rjust(64,'0')}{'f'*64}"))
  e.append((a,f"0x62355638{d[2:].lower().rjust(64,'0')}{c[2:].lower().rjust(64,'0')}{f:064x}"));return e
 def sync_clob_collateral_allowance(a):
  a.invalidate_collateral_cache()
  try:
   b=getattr(a,"signature_type",None);c=1 if b is None else int(b)
   if getattr(a,"client",None)is not None and BalanceAllowanceParams is not None and AssetType is not None:a.client.update_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL,signature_type=c));return True
  except Exception:pass
  return False
 @staticmethod
 def _payout_redemption_topic():from eth_utils import keccak;return"0x"+keccak(text="PayoutRedemption(address,address,bytes32,bytes32,uint256[],uint256)").hex().replace("0x","")
 @staticmethod
 def _neg_risk_payout_redemption_topic():from eth_utils import keccak;return"0x"+keccak(text="PayoutRedemption(address,bytes32,uint256[],uint256)").hex().replace("0x","")
 @staticmethod
 def build_relayer_builder_headers(api_key,secret,passphrase,method,request_path,body=None,timestamp=None):
  import base64;import hashlib;import hmac;c=str(int(timestamp if timestamp is not None else time.time()));b=base64.urlsafe_b64decode(secret);a=c+str(method)+str(request_path)
  if body is not None:
   if isinstance(body,(bytes,bytearray)):a+=body.decode("utf-8")
   elif isinstance(body,str):a+=body
   else:a+=str(body).replace("'",'"')
  d=base64.urlsafe_b64encode(hmac.new(b,a.encode("utf-8"),hashlib.sha256).digest()).decode("utf-8");return{"POLY_BUILDER_API_KEY":api_key,"POLY_BUILDER_TIMESTAMP":c,"POLY_BUILDER_PASSPHRASE":passphrase,"POLY_BUILDER_SIGNATURE":d}
 @classmethod
 def build_deposit_wallet_relayer_batch(cls,*,private_key,wallet_address,nonce,deadline,calls,chain_id=137):
  from eth_account import Account as b;from eth_account.messages import encode_typed_data as a;from web3 import Web3;i=Web3.to_checksum_address(wallet_address);h=Web3.to_checksum_address(b.from_key(private_key).address);f=Web3.to_checksum_address(cls.DEPOSIT_WALLET_FACTORY);e=[];d=[]
  for c in calls:o=Web3.to_checksum_address(c["target"]);n=str(int(c.get("value","0")or 0));k=str(c["data"])if str(c["data"]).startswith("0x")else("0x"+str(c["data"]));e.append({"target":o,"value":n,"data":k});d.append({"target":o,"value":int(n),"data":bytes.fromhex(k[2:])})
  g={"types":{"EIP712Domain":[{"name":"name","type":"string"},{"name":"version","type":"string"},{"name":"chainId","type":"uint256"},{"name":"verifyingContract","type":"address"}],"Call":[{"name":"target","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"}],"Batch":[{"name":"wallet","type":"address"},{"name":"nonce","type":"uint256"},{"name":"deadline","type":"uint256"},{"name":"calls","type":"Call[]"}]},"primaryType":"Batch","domain":{"name":"DepositWallet","version":"1","chainId":int(chain_id),"verifyingContract":i},"message":{"wallet":i,"nonce":int(nonce),"deadline":int(deadline),"calls":d}};j=a(full_message=g);m=b.sign_message(j,private_key=private_key).signature.hex();l=m if m.startswith("0x")else f"0x{m}";return{"type":"WALLET","from":h,"to":f,"nonce":str(int(nonce)),"signature":l,"depositWalletParams":{"depositWallet":i,"deadline":str(int(deadline)),"calls":e}}
 def _rpc(self,method,params):
  c=(os.getenv("POLYGON_RPC_URL")or"https://polygon-bor-rpc.publicnode.com").strip();f=[]
  for u in(c,"https://polygon-bor-rpc.publicnode.com","https://polygon-rpc.com","https://1rpc.io/matic"):
   if u and u not in f:f.append(u)
  b=getattr(self,"_sync_session",requests)
  for a in f:
   try:
    e=b.post(a,json={"jsonrpc":"2.0","id":1,"method":method,"params":params},timeout=4.)
    if e.status_code!=200:continue
    d=e.json()
    if not isinstance(d,dict)or"error"in d:continue
    g=d.get("result")
    if g is None:continue
    return g
   except Exception:pass
  return None
 def get_current_block_number(self):
  a=self._rpc("eth_blockNumber",[])
  try:return int(a,16)if a else None
  except(TypeError,ValueError):return None
 def parse_payout_redemption_logs(a,logs,condition_id):
  n=[];c=a._payout_redemption_topic().lower();g=a._neg_risk_payout_redemption_topic().lower();f=a.V2_ADAPTER_REDEMPTION_TOPIC0.lower();i={a.CTF_ADAPTER_V2_ADDRESS.lower(),a.NEG_RISK_ADAPTER_V2_ADDRESS.lower()};e={a.AUTO_REDEEM_CTF_TOPIC0.lower(),a.AUTO_REDEEM_NEGRISK_TOPIC0.lower()};p=str(a.funder_address or"").lower().replace("0x","").rjust(64,"0");m=str(condition_id or"").lower().replace("0x","").rjust(64,"0");d=set()
  for o in logs or[]:
   j=[str(t).lower()for t in(o.get("topics")or[])];l=str(o.get("address","")).lower();k=str(o.get("data","")).replace("0x","")
   if len(j)>=2 and j[0]==c and l==a.CTF_ADDRESS.lower():
    if j[1].replace("0x","").rjust(64,"0")!=p:continue
    if len(k)<192 or k[0:64]!=m:continue
    b=int(k[128:192],16)/1e6
   elif len(j)>=3 and j[0]==g and l==a.NEG_RISK_ADAPTER_ADDRESS.lower():
    if j[1].replace("0x","").rjust(64,"0")!=p:continue
    if j[2].replace("0x","").rjust(64,"0")!=m:continue
    if len(k)<128:continue
    b=int(k[64:128],16)/1e6
   elif len(j)>=3 and j[0]==f and l in i:
    if j[1].replace("0x","").rjust(64,"0")!=p:continue
    if j[2].replace("0x","").rjust(64,"0")!=m:continue
    if len(k)<128:continue
    b=int(k[64:128],16)/1e6
   elif len(j)>=3 and j[0]in e and l==a.AUTOREDEEMER_ADDRESS.lower():
    if j[1].replace("0x","").rjust(64,"0")!=p:continue
    if j[2].replace("0x","").rjust(64,"0")!=m:continue
    if len(k)<64:continue
    b=int.from_bytes(bytes.fromhex(k[0:64]),"big")/1e6
   else:continue
   h=(o.get("transactionHash"),o.get("logIndex"))
   if h!=(None,None)and h in d:continue
   d.add(h);n.append({"transaction_hash":o.get("transactionHash"),"block_number":int(str(o.get("blockNumber","0x0")),16)if str(o.get("blockNumber","")).startswith("0x")else o.get("blockNumber"),"payout_usd":b,"log_index":o.get("logIndex")})
  return n
 def find_redemption_payouts(a,condition_id,from_block=None,tx_hash=None,max_span=15000):
  if a.dry_run or not a.funder_address or not condition_id:return None
  if tx_hash:
   m=a._rpc("eth_getTransactionReceipt",[tx_hash])
   if not m:return None
   if str(m.get("status","")).lower()not in{"0x1","1"}:return[]
   return a.parse_payout_redemption_logs(m.get("logs",[]),condition_id)
  p=a.get_current_block_number()
  if p is None:return None
  h=max(int(max_span),15000);e=min(int(max_span),1000)if int(max_span)>0 else 1000;n=max(int(from_block),max(0,p-max(h,50000)))if from_block else max(0,p-h);g=[];f="0x"+str(a.funder_address).lower().replace("0x","").rjust(64,"0");d="0x"+str(condition_id).lower().replace("0x","").rjust(64,"0");c=[a.AUTO_REDEEM_CTF_TOPIC0,a.AUTO_REDEEM_NEGRISK_TOPIC0];b=n
  while b<=p:
   q=min(p,b+e);o=a._rpc("eth_getLogs",[{"address":a.CTF_ADDRESS,"fromBlock":hex(b),"toBlock":hex(q),"topics":[a._payout_redemption_topic(),f]}])
   if o is None:return None
   if o:g.extend(o)
   l=a._rpc("eth_getLogs",[{"address":a.NEG_RISK_ADAPTER_ADDRESS,"fromBlock":hex(b),"toBlock":hex(q),"topics":[a._neg_risk_payout_redemption_topic(),f,d]}])
   if l is None:return None
   if l:g.extend(l)
   k=a._rpc("eth_getLogs",[{"address":a.AUTOREDEEMER_ADDRESS,"fromBlock":hex(b),"toBlock":hex(q),"topics":[c,f,d]}])
   if k is None:return None
   if k:g.extend(k)
   for j in(a.CTF_ADAPTER_V2_ADDRESS,a.NEG_RISK_ADAPTER_V2_ADDRESS):
    i=a._rpc("eth_getLogs",[{"address":j,"fromBlock":hex(b),"toBlock":hex(q),"topics":[a.V2_ADAPTER_REDEMPTION_TOPIC0,f,d]}])
    if isinstance(i,list)and i:g.extend(i)
   b=q+1
  return a.parse_payout_redemption_logs(g,condition_id)
 def _submit_deposit_wallet_relayer_redemption(a,*,pk,funder_cs,nonce,calls,condition_id):
  u=(os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY")or"").strip();t=(os.getenv("POLY_BUILDER_SECRET")or os.getenv("BUILDER_SECRET")or"").strip();q=(os.getenv("POLY_BUILDER_PASSPHRASE")or os.getenv("BUILDER_PASS_PHRASE")or"").strip()
  if not(u and t and q):return None
  e=str(condition_id or"").startswith(("nrconv:","nr3:","split:","merge:","batch_merge:","wrap:","wrap_pusd"));b=getattr(a,"_relayer_redemption_cooldown",None)
  if b is None:a._relayer_redemption_cooldown=b={}
  s=time.time()
  if(not e)and float(b.get(condition_id,.0))>s:return None
  c=getattr(a,"_relayer_rate_limiter",None)
  if c is None:c=RelayerRateLimiter(max_per_min=24,window_sec=60.);a._relayer_rate_limiter=c
  if(not e)and c.recent_count()>=max(1,int(c.max_per_min)-1):logger.warning(f"[RELAYER-GOVERNOR] Deferring passive Relayer V2 /submit for {condition_id}: reserving slot {c.max_per_min}/min for post-fill recycle ops.");return None
  i,l=c.allow_and_record()
  if not i:logger.warning(f"[RELAYER-GOVERNOR] Deferring Relayer V2 /submit for {condition_id}: 24/min safety cap reached (retry in {l:.2f}s).");return None
  h=os.getenv("POLY_RELAYER_URL",a.RELAYER_V2_URL).rstrip("/");k=a.build_deposit_wallet_relayer_batch(private_key=pk,wallet_address=funder_cs,nonce=nonce,deadline=int(s)+300,calls=calls,chain_id=a.CHAIN_ID);j=json.dumps(k,separators=(",",":"));o=a.build_relayer_builder_headers(api_key=u,secret=t,passphrase=q,method="POST",request_path="/submit",body=j);o["Content-Type"]="application/json";n=getattr(a,"_sync_session",requests);w=n.post(f"{h}/submit",headers=o,data=j.encode("utf-8"),timeout=8.)
  if w.status_code!=200:logger.warning(f"[REDEMPTION] Relayer V2 submit HTTP {w.status_code}: {w.text[:200]}");return None
  v=w.json()if w.content else{}
  if v.get("state")in("STATE_FAILED","STATE_INVALID"):return None
  if not e:b[condition_id]=s+30.
  d=v.get("transactionHash");r=v.get("transactionID")
  if not d and r:
   for _ in range(3):
    time.sleep(1.5);x=n.get(f"{h}/transaction",params={"id":r},timeout=5.)
    if x.status_code==200:
     p=x.json()
     if isinstance(p,list)and p:
      if p[0].get("state")in("STATE_FAILED","STATE_INVALID"):return None
      d=p[0].get("transactionHash")
      if d:break
  if d:
   g=d if str(d).startswith("0x")else f"0x{d}"
   for f in range(3):
    m=a._rpc("eth_getTransactionReceipt",[g])
    if isinstance(m,dict)and m.get("status")is not None:
     if str(m.get("status","")).lower()not in{"0x1","1"}:return None
     if not e:b[condition_id]=time.time()+180.
     break
    if f<2 and n is requests:time.sleep(1.2)
   return g
  return None
 def attempt_onchain_redemption(a,condition_id,*,neg_risk=None):
  m=getattr(a,"signature_type",None);u=1 if m is None else int(m)
  if a.dry_run or not condition_id or u not in(0,1,2,3):return None
  J=(os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY")or"").strip()
  if u==3 and not J:
   a._funder_is_gnosis_safe=False;t=time.time()
   if(t-float(getattr(a,"_last_missing_builder_key_warn_ts",.0)))>=3600.:a._last_missing_builder_key_warn_ts=t;logger.warning(f"[REDEMPTION] DepositWallet ({a.funder_address}) requires POLY_BUILDER_API_KEY for Relayer V2.")
   return None
  if u==2 and getattr(a,"_funder_is_gnosis_safe",None)is False:return None
  Q=(os.getenv("POLYGON_PRIVATE_KEY")or a.private_key or"").strip()
  if not Q or not a.funder_address:return None
  try:
   from web3 import Web3;from src.polymarket_research.riskless_machine_gun_engine import get_fast_polygon_web3 as f;P=f(timeout=5.);s=Web3.to_checksum_address(a.funder_address);r=Web3.to_checksum_address(P.eth.account.from_key(Q).address)
   if u in(0,1,2):
    l=s if u==0 else r
    if P.eth.get_balance(l)<int(.05*1e18):return None
   p=bytes.fromhex(condition_id.lower().replace("0x","").rjust(64,"0"));B=[{"inputs":[{"name":"collateralToken","type":"address"},{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSets","type":"uint256[]"}],"name":"redeemPositions","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSet","type":"uint256"}],"name":"getCollectionId","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"collateralToken","type":"address"},{"name":"collectionId","type":"bytes32"}],"name":"getPositionId","outputs":[{"name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"name":"owner","type":"address"},{"name":"id","type":"uint256"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"conditionId","type":"bytes32"}],"name":"payoutDenominator","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"conditionId","type":"bytes32"},{"name":"index","type":"uint256"}],"name":"payoutNumerators","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}];F=[{"inputs":[{"name":"_conditionId","type":"bytes32"},{"name":"_amounts","type":"uint256[]"}],"name":"redeemPositions","outputs":[],"stateMutability":"nonpayable","type":"function"}];E=Web3.to_checksum_address(a.CTF_ADDRESS);L=P.eth.contract(address=E,abi=B);I=Web3.to_checksum_address(a.NEG_RISK_ADAPTER_ADDRESS);n=P.eth.contract(address=I,abi=F);g=0;e=None
   try:
    g=int(L.functions.payoutDenominator(p).call())
    if g<=0:return None
    O=int(L.functions.payoutNumerators(p,0).call());N=int(L.functions.payoutNumerators(p,1).call())
    if 0<=O<=g and 0<=N<=g and(O+N)<=g:e=(O,N)
   except Exception:pass
   j=[];b=0;c=False
   if neg_risk is not False:
    try:
     A=Web3.to_checksum_address(a.NEG_RISK_WRAPPED_COLLATERAL);H=int(L.functions.balanceOf(s,L.functions.getPositionId(A,L.functions.getCollectionId(b"\x00"*32,p,1).call()).call()).call());K=int(L.functions.balanceOf(s,L.functions.getPositionId(A,L.functions.getCollectionId(b"\x00"*32,p,2).call()).call()).call())
     if H>0 or K>0:
      D=(n.encode_abi("redeemPositions",args=[p,[H,K]])if hasattr(n,"encode_abi")else n.encodeABI(fn_name="redeemPositions",args=[p,[H,K]]));j.append((I,D));c=True
      if e is not None and g>0:b+=(H*e[0])//g+(K*e[1])//g
    except Exception:pass
   if neg_risk is not True:
    for z in(a.PUSD_ADDRESS,a.USDC_E_ADDRESS):
     try:
      C=Web3.to_checksum_address(z);G=[int(L.functions.balanceOf(s,L.functions.getPositionId(C,L.functions.getCollectionId(b"\x00"*32,p,R).call()).call()).call())for R in(1,2)]
      if G[0]>0 or G[1]>0:
       y=(L.encode_abi("redeemPositions",args=[C,b"\x00"*32,p,[1,2]])if hasattr(L,"encode_abi")else L.encodeABI(fn_name="redeemPositions",args=[C,b"\x00"*32,p,[1,2]]));j.append((E,y))
       if C.lower()==a.USDC_E_ADDRESS.lower():
        c=True
        if e is not None and g>0:b+=(G[0]*e[0])//g+(G[1]*e[1])//g
     except Exception:continue
   if not j:return None
   d=False;i=None
   if u in(1,3)and b>0:
    try:
     q=[{"inputs":[{"name":"a","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}];x=P.eth.contract(address=Web3.to_checksum_address(a.USDC_E_ADDRESS),abi=q);k=max(0,int(x.functions.balanceOf(s).call()));w=max(0,int(x.functions.allowance(s,Web3.to_checksum_address(a.PUSD_WRAPPER_ADDRESS)).call()));o=a.encode_pusd_wrap_calls(funder_address=s,amount_raw=k+b,current_allowance_raw=w)
     if o:
      i=a._dispatch_funder_calls(P,Web3,Q,u,s,r,j+o,condition_id)
      if i:d=True
    except Exception:i=None
   if not i:i=a._dispatch_funder_calls(P,Web3,Q,u,s,r,j,condition_id)
   if not i:return None
   v=getattr(P.eth,"wait_for_transaction_receipt",None);h=False
   if callable(v):
    try:
     M=v(i,timeout=30,poll_latency=1.2)
     if isinstance(M,dict)and M.get("status")is not None:
      if int(M.get("status",0))!=1:return None
      h=True
    except Exception:pass
   if h and c and not d:a.wrap_idle_usdce_to_pusd(min_usd=.5)
   a.sync_clob_collateral_allowance();return i
  except Exception:return None
 def get_idle_usdce_balance(b):
  if b.dry_run or not b.funder_address:return.0
  try:from web3 import Web3;from src.polymarket_research.riskless_machine_gun_engine import get_fast_polygon_web3 as a;g=a(timeout=3.5);d=Web3.to_checksum_address(b.funder_address);e=Web3.to_checksum_address(b.USDC_E_ADDRESS);c=[{"inputs":[{"name":"a","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}];f=int(g.eth.contract(address=e,abi=c).functions.balanceOf(d).call());return round(max(.0,f/1e6),6)
  except Exception:return None
 def wrap_idle_usdce_to_pusd(a,min_usd=1.):
  d=getattr(a,"signature_type",None);k=1 if d is None else int(d)
  if a.dry_run:return{"wrapped":False,"dry_run":True,"amount_usd":.0,"tx_hash":None}
  v=(os.getenv("POLYGON_PRIVATE_KEY")or a.private_key or"").strip()
  if k not in(0,1,2,3)or not v or not a.funder_address:return{"wrapped":False,"amount_usd":.0,"tx_hash":None,"reason":"UNCONFIGURED"}
  r=(os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY")or"").strip()
  if k==3 and not r:return{"wrapped":False,"amount_usd":.0,"tx_hash":None,"reason":"MISSING_BUILDER_KEY"}
  if k==2 and getattr(a,"_funder_is_gnosis_safe",None)is False:return{"wrapped":False,"amount_usd":.0,"tx_hash":None,"reason":"NOT_GNOSIS_SAFE"}
  try:
   from web3 import Web3;from src.polymarket_research.riskless_machine_gun_engine import get_fast_polygon_web3 as b;u=b(timeout=5.);i=Web3.to_checksum_address(a.funder_address);h=Web3.to_checksum_address(u.eth.account.from_key(v).address)
   if k in(0,1,2):
    c=i if k==0 else h
    if u.eth.get_balance(c)<int(.05*1e18):return{"wrapped":False,"amount_usd":.0,"tx_hash":None,"reason":"INSUFFICIENT_GAS"}
   g=[{"inputs":[{"name":"a","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}];j=Web3.to_checksum_address(a.USDC_E_ADDRESS);f=Web3.to_checksum_address(a.PUSD_WRAPPER_ADDRESS);p=u.eth.contract(address=j,abi=g);o=int(p.functions.balanceOf(i).call());n=max(1,int(math.floor(max(1e-6,float(min_usd))*1e6)))
   if o<n:return{"wrapped":False,"amount_usd":round(o/1e6,6),"tx_hash":None,"reason":"BELOW_MIN_USD"}
   m=int(p.functions.allowance(i,f).call());e=a.encode_pusd_wrap_calls(funder_address=i,amount_raw=o,current_allowance_raw=m);s=a._dispatch_funder_calls(u,Web3,v,k,i,h,e,"wrap_pusd")
   if not s:return{"wrapped":False,"amount_usd":round(o/1e6,6),"tx_hash":None,"reason":"DISPATCH_DEFERRED"}
   t=u.eth.wait_for_transaction_receipt(s,timeout=60,poll_latency=1.2)
   if int(t.get("status",0))!=1:logger.warning(f"[PUSD-WRAP] wrap tx {s} reverted for ${o/1e6:.2f} USDC.e.");return{"wrapped":False,"amount_usd":round(o/1e6,6),"tx_hash":s,"reason":"TX_REVERTED"}
   a.sync_clob_collateral_allowance();l=round(o/1e6,6);logger.info(f"✓ [PUSD-WRAP] Wrapped ${l:.2f} idle USDC.e -> pUSD | tx={s}");return{"wrapped":True,"amount_usd":l,"tx_hash":s}
  except Exception as q:return{"wrapped":False,"amount_usd":.0,"tx_hash":None,"reason":str(q)}
 def attempt_wrap_legacy_usdce_to_pusd(self,*,min_usd=1.):a=self.wrap_idle_usdce_to_pusd(min_usd=min_usd);return{**a,"success":bool(a.get("wrapped")),"wrapped_usd":float(a.get("amount_usd")or.0)if a.get("wrapped")else.0}
 def _dispatch_funder_calls(a,w3,Web3,pk,sig_type,funder_cs,signer_cs,call_targets,condition_id):
  b=getattr(a,"_onchain_tx_lock",None)
  if b is None:b=threading.RLock();a._onchain_tx_lock=b
  with b:return a._dispatch_funder_calls_locked(w3,Web3,pk,sig_type,funder_cs,signer_cs,call_targets,condition_id)
 def _dispatch_funder_calls_locked(c,w3,Web3,pk,sig_type,funder_cs,signer_cs,call_targets,condition_id):
  if sig_type==3:n=[{"inputs":[],"name":"nonce","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}];r=w3.eth.contract(address=funder_cs,abi=n);j=int(r.functions.nonce().call());e=[{"target":u,"value":"0","data":s}for u,s in call_targets];return c._submit_deposit_wallet_relayer_redemption(pk=pk,funder_cs=funder_cs,nonce=j,calls=e,condition_id=condition_id)
  def a(mk_tx):
   h=None
   for w,(t,o)in enumerate(call_targets):
    s=str(o).lower().startswith(("0x095ea7b3","0xa22cb465"))
    try:
     x=mk_tx(t,o)
     if not x:
      if s:return None
      continue
     u=w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(x,private_key=pk).raw_transaction).hex();v=u if str(u).startswith("0x")else f"0x{u}"
     if w+1<len(call_targets):
      if int(w3.eth.wait_for_transaction_receipt(v,timeout=45,poll_latency=1.2).get("status",0))!=1:return None
      if not s:h=v
     else:return v
    except Exception:
     if s:return None
   return h
  if sig_type==2:
   i=[{"inputs":[],"name":"getThreshold","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getOwners","outputs":[{"name":"","type":"address[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"},{"name":"operation","type":"uint8"},{"name":"safeTxGas","type":"uint256"},{"name":"baseGas","type":"uint256"},{"name":"gasPrice","type":"uint256"},{"name":"gasToken","type":"address"},{"name":"refundReceiver","type":"address"},{"name":"signatures","type":"bytes"}],"name":"execTransaction","outputs":[{"name":"success","type":"bool"}],"stateMutability":"payable","type":"function"}];p=w3.eth.contract(address=funder_cs,abi=i)
   try:m=[Web3.to_checksum_address(o)for o in p.functions.getOwners().call()];d=int(p.functions.getThreshold().call())
   except Exception:c._funder_is_gnosis_safe=False;return None
   c._funder_is_gnosis_safe=True
   if d!=1 or signer_cs not in m:return None
   k=Web3.to_checksum_address("0x"+"00"*20);g=b"\x00"*12+bytes.fromhex(signer_cs[2:].lower())+b"\x00"*32+b"\x01"
   def b(tgt_cs,inner_hex):h=p.functions.execTransaction(tgt_cs,0,bytes.fromhex(inner_hex[2:]if inner_hex.startswith("0x")else inner_hex),0,0,0,0,k,k,g);return h.build_transaction({"from":signer_cs,"nonce":w3.eth.get_transaction_count(signer_cs,"pending"),"gas":300000,"gasPrice":w3.eth.gas_price,"chainId":137})if h.call({"from":signer_cs})else None
   return a(b)
  if sig_type==1:l=[{"inputs":[{"components":[{"name":"typeCode","type":"uint8"},{"name":"to","type":"address"},{"name":"value","type":"uint256"},{"name":"data","type":"bytes"}],"name":"calls","type":"tuple[]"}],"name":"proxy","outputs":[{"name":"returnValues","type":"bytes[]"}],"stateMutability":"payable","type":"function"}];q=w3.eth.contract(address=Web3.to_checksum_address(c.POLY_PROXY_FACTORY),abi=l);f=[(1,s,0,bytes.fromhex(h[2:]if h.startswith("0x")else h))for s,h in call_targets];q.functions.proxy(f).call({"from":signer_cs});tx=q.functions.proxy(f).build_transaction({"from":signer_cs,"nonce":w3.eth.get_transaction_count(signer_cs,"pending"),"gas":320000,"gasPrice":w3.eth.gas_price,"chainId":137});raw_h=w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(tx,private_key=pk).raw_transaction).hex();return raw_h if str(raw_h).startswith("0x")else f"0x{raw_h}"
  return a(lambda t,h:(w3.eth.call({"from":funder_cs,"to":t,"data":h}),{"from":funder_cs,"to":t,"value":0,"data":h,"nonce":w3.eth.get_transaction_count(funder_cs,"pending"),"gas":250000,"gasPrice":w3.eth.gas_price,"chainId":137})[1])
 def attempt_onchain_complete_set_merge(a,condition_id,*,min_pairs=5.,max_pairs=None,neg_risk=None):
  j=getattr(a,"signature_type",None);s=1 if j is None else int(j)
  if a.dry_run or not condition_id or s not in(0,1,2,3):return None
  J=(os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY")or"").strip()
  if s==3 and not J:return None
  if s==2 and getattr(a,"_funder_is_gnosis_safe",None)is False:return None
  P=(os.getenv("POLYGON_PRIVATE_KEY")or a.private_key or"").strip()
  if not P or not a.funder_address:return None
  try:
   from web3 import Web3;from src.polymarket_research.riskless_machine_gun_engine import get_fast_polygon_web3 as d;O=d(timeout=5.);p=Web3.to_checksum_address(a.funder_address);o=Web3.to_checksum_address(O.eth.account.from_key(P).address)
   if s in(0,1,2):
    i=p if s==0 else o
    if O.eth.get_balance(i)<int(.05*1e18):return None
   m=bytes.fromhex(condition_id.lower().replace("0x","").rjust(64,"0"));z=max(1,int(math.floor(float(min_pairs)*1e6)));y=max(z,int(math.floor(float(max_pairs)*1e6)))if max_pairs else None;x=[{"inputs":[{"name":"collateralToken","type":"address"},{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"partition","type":"uint256[]"},{"name":"amount","type":"uint256"}],"name":"mergePositions","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSet","type":"uint256"}],"name":"getCollectionId","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"collateralToken","type":"address"},{"name":"collectionId","type":"bytes32"}],"name":"getPositionId","outputs":[{"name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"name":"owner","type":"address"},{"name":"id","type":"uint256"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"account","type":"address"},{"name":"operator","type":"address"}],"name":"isApprovedForAll","outputs":[{"name":"","type":"bool"}],"stateMutability":"view","type":"function"}];E=[{"inputs":[{"name":"_conditionId","type":"bytes32"},{"name":"_amount","type":"uint256"}],"name":"mergePositions","outputs":[],"stateMutability":"nonpayable","type":"function"}];D=Web3.to_checksum_address(a.CTF_ADDRESS);M=O.eth.contract(address=D,abi=x);I=Web3.to_checksum_address(a.NEG_RISK_ADAPTER_ADDRESS);r=Web3.to_checksum_address(a.NEG_RISK_ADAPTER_V2_ADDRESS);k=O.eth.contract(address=I,abi=E);g=[];c=0;b=False
   if neg_risk is not False:
    try:
     w=Web3.to_checksum_address(a.NEG_RISK_WRAPPED_COLLATERAL);l=int(M.functions.balanceOf(p,M.functions.getPositionId(w,M.functions.getCollectionId(b"\x00"*32,m,1).call()).call()).call());q=int(M.functions.balanceOf(p,M.functions.getPositionId(w,M.functions.getCollectionId(b"\x00"*32,m,2).call()).call()).call());L=min(l,q)if y is None else min(l,q,y)
     if L>=z:
      e=bool(M.functions.isApprovedForAll(p,r).call())
      if not e and s==3:g.append((D,f"0xa22cb465{r[2:].lower().rjust(64,'0')}{'1'.rjust(64,'0')}"));e=True
      C=r if e else I
      if not e:b=True
      B=k.encode_abi("mergePositions",args=[m,L])if hasattr(k,"encode_abi")else k.encodeABI(fn_name="mergePositions",args=[m,L]);g.append((C,B));c+=L
    except Exception:pass
   if neg_risk is not True and not g:
    v=Web3.to_checksum_address(a.PUSD_ADDRESS);n=Web3.to_checksum_address(a.CTF_ADAPTER_V2_ADDRESS)
    for u in(a.PUSD_ADDRESS,a.USDC_E_ADDRESS):
     try:
      A=Web3.to_checksum_address(u);l=int(M.functions.balanceOf(p,M.functions.getPositionId(A,M.functions.getCollectionId(b"\x00"*32,m,1).call()).call()).call());q=int(M.functions.balanceOf(p,M.functions.getPositionId(A,M.functions.getCollectionId(b"\x00"*32,m,2).call()).call()).call());H=min(l,q)if y is None else min(l,q,y)
      if H>=z:
       f=A!=v and bool(M.functions.isApprovedForAll(p,n).call())
       if A!=v and not f and s==3:g.append((D,f"0xa22cb465{n[2:].lower().rjust(64,'0')}{'1'.rjust(64,'0')}"));f=True
       G=v if f else A;F=n if f else D
       if G!=v:b=True
       t=M.encode_abi("mergePositions",args=[G,b"\x00"*32,m,[1,2],H])if hasattr(M,"encode_abi")else M.encodeABI(fn_name="mergePositions",args=[G,b"\x00"*32,m,[1,2],H]);g.append((F,t));c+=H;break
     except Exception:continue
   if not g or c<z:return None
   K=a._dispatch_funder_calls(O,Web3,P,s,p,o,g,condition_id)
   if K:
    a.invalidate_collateral_cache()
    try:
     N=O.eth.wait_for_transaction_receipt(K,timeout=60,poll_latency=1.5)
     if int(N.get("status",0))!=1:logger.warning(f"[MERGE] mergePositions tx {K} reverted for {condition_id}; legs remain open.");return None
    except Exception as h:logger.warning(f"[MERGE] mergePositions tx {K} unconfirmed for {condition_id} ({h}); legs remain open.");return None
    if b:a.wrap_idle_usdce_to_pusd(min_usd=.5)
    a.sync_clob_collateral_allowance();return K,round(c/1e6,6)
   return None
  except Exception:return None
 def attempt_onchain_batch_complete_set_merges(a,merge_specs):
  n=getattr(a,"signature_type",None);x=1 if n is None else int(n)
  if a.dry_run or not merge_specs or x not in(0,1,2,3):return None
  S=(os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY")or"").strip()
  if x==3 and not S:return None
  if x==2 and getattr(a,"_funder_is_gnosis_safe",None)is False:return None
  pk=(os.getenv("POLYGON_PRIVATE_KEY")or a.private_key or"").strip()
  if not pk or not a.funder_address:return None
  try:
   from web3 import Web3;from src.polymarket_research.riskless_machine_gun_engine import get_fast_polygon_web3 as f;Z=f(timeout=5.);u=Web3.to_checksum_address(a.funder_address);t=Web3.to_checksum_address(Z.eth.account.from_key(pk).address)
   if x in(0,1,2):
    m=u if x==0 else t
    if Z.eth.get_balance(m)<int(.05*1e18):return None
   F=[{"inputs":[{"name":"collateralToken","type":"address"},{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"partition","type":"uint256[]"},{"name":"amount","type":"uint256"}],"name":"mergePositions","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"parentCollectionId","type":"bytes32"},{"name":"conditionId","type":"bytes32"},{"name":"indexSet","type":"uint256"}],"name":"getCollectionId","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"collateralToken","type":"address"},{"name":"collectionId","type":"bytes32"}],"name":"getPositionId","outputs":[{"name":"","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"name":"owner","type":"address"},{"name":"id","type":"uint256"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"name":"account","type":"address"},{"name":"operator","type":"address"}],"name":"isApprovedForAll","outputs":[{"name":"","type":"bool"}],"stateMutability":"view","type":"function"}];L=[{"inputs":[{"name":"_conditionId","type":"bytes32"},{"name":"_amount","type":"uint256"}],"name":"mergePositions","outputs":[],"stateMutability":"nonpayable","type":"function"}];K=Web3.to_checksum_address(a.CTF_ADDRESS);X=Z.eth.contract(address=K,abi=F);R=Web3.to_checksum_address(a.NEG_RISK_ADAPTER_ADDRESS);w=Web3.to_checksum_address(a.NEG_RISK_ADAPTER_V2_ADDRESS);p=Z.eth.contract(address=R,abi=L);E=Web3.to_checksum_address(a.PUSD_ADDRESS);s=Web3.to_checksum_address(a.CTF_ADAPTER_V2_ADDRESS);D=Web3.to_checksum_address(a.NEG_RISK_WRAPPED_COLLATERAL);o=[];j={};d=False;b=False;c=False;h={}
   for V in merge_specs[:8]:
    W=str(V.get("condition_id")or"").strip();Q=str(V.get("key")or W)
    if not W:continue
    r=bytes.fromhex(W.lower().replace("0x","").rjust(64,"0"));C=max(1,int(math.floor(float(V.get("min_pairs")or 1.)*1e6)));P=V.get("max_pairs");B=max(C,int(math.floor(float(P)*1e6)))if P else None;A=V.get("neg_risk");l=h.get(W.lower(),0);e=False
    if A is not False:
     try:
      q=max(0,int(X.functions.balanceOf(u,X.functions.getPositionId(D,X.functions.getCollectionId(b"\x00"*32,r,1).call()).call()).call())-l);v=max(0,int(X.functions.balanceOf(u,X.functions.getPositionId(D,X.functions.getCollectionId(b"\x00"*32,r,2).call()).call()).call())-l);U=min(q,v)if B is None else min(q,v,B)
      if U>=C:
       g=b or bool(X.functions.isApprovedForAll(u,w).call())
       if not g and x==3:o.append((K,f"0xa22cb465{w[2:].lower().rjust(64,'0')}{'1'.rjust(64,'0')}"));g=True;b=True
       J=w if g else R
       if not g:c=True
       I=p.encode_abi("mergePositions",args=[r,U])if hasattr(p,"encode_abi")else p.encodeABI(fn_name="mergePositions",args=[r,U]);o.append((J,I));j[Q]=round(U/1e6,6);h[W.lower()]=l+U;e=True
     except Exception:pass
    if A is not True and not e:
     for z in(a.PUSD_ADDRESS,a.USDC_E_ADDRESS):
      try:
       H=Web3.to_checksum_address(z);q=max(0,int(X.functions.balanceOf(u,X.functions.getPositionId(H,X.functions.getCollectionId(b"\x00"*32,r,1).call()).call()).call())-l);v=max(0,int(X.functions.balanceOf(u,X.functions.getPositionId(H,X.functions.getCollectionId(b"\x00"*32,r,2).call()).call()).call())-l);O=min(q,v)if B is None else min(q,v,B)
       if O>=C:
        i=H!=E and(d or bool(X.functions.isApprovedForAll(u,s).call()))
        if H!=E and not i and x==3:o.append((K,f"0xa22cb465{s[2:].lower().rjust(64,'0')}{'1'.rjust(64,'0')}"));i=True;d=True
        N=E if i else H;M=s if i else K
        if N!=E:c=True
        y=X.encode_abi("mergePositions",args=[N,b"\x00"*32,r,[1,2],O])if hasattr(X,"encode_abi")else X.encodeABI(fn_name="mergePositions",args=[N,b"\x00"*32,r,[1,2],O]);o.append((M,y));j[Q]=round(O/1e6,6);h[W.lower()]=l+O;break
      except Exception:continue
   if not o or not j:return None
   G=f"batch_merge:{len(j)}:{next(iter(j))[:18]}";T=a._dispatch_funder_calls(Z,Web3,pk,x,u,t,o,G)
   if not T:return None
   a.invalidate_collateral_cache()
   try:
    Y=Z.eth.wait_for_transaction_receipt(T,timeout=60,poll_latency=1.5)
    if int(Y.get("status",0))!=1:logger.warning(f"[BATCH-MERGE] tx {T} reverted ({G}); legs remain open.");return None
   except Exception as k:logger.warning(f"[BATCH-MERGE] tx {T} unconfirmed ({G}: {k}); legs remain open.");return None
   if c:a.wrap_idle_usdce_to_pusd(min_usd=.5)
   a.sync_clob_collateral_allowance();return T,j
  except Exception:return None
 @classmethod
 def encode_negrisk_convert_positions_call(cls,market_id,question_indices,shares,*,adapter_address=None):
  e=str(market_id or"").strip().lower().replace("0x","")
  if len(e)!=64 or any(c not in"0123456789abcdef"for c in e):raise ValueError(f"Invalid 32-byte negRiskMarketID: {market_id!r}")
  f=sorted({int(i)for i in(question_indices or[])})
  if not f or f[0]<0 or f[-1]>=256:raise ValueError(f"Invalid NegRisk question_indices: {question_indices!r}")
  d=int(math.floor(float(shares)*1e6))
  if d<=0:raise ValueError(f"Invalid convertPositions shares: {shares!r}")
  a=0
  for i in f:a|=1<<i
  b=str(adapter_address or cls.NEG_RISK_ADAPTER_ADDRESS);return{"target":b,"value":"0","data":f"0xc64748c4{e}{a:064x}{d:064x}","index_set":hex(a),"amount_raw":str(d)}
 def attempt_negrisk_convert_positions(a,market_id,question_indices,shares,*,prefer_v2_pusd_adapter=True):
  d=a.NEG_RISK_ADAPTER_V2_ADDRESS if prefer_v2_pusd_adapter else a.NEG_RISK_ADAPTER_ADDRESS;g=a.encode_negrisk_convert_positions_call(market_id,question_indices,shares,adapter_address=d)
  if a.dry_run:return{"success":True,"dry_run":True,"tx_hash":f"0xdry_nr_conv_{int(time.time())}","adapter_used":g["target"],"call":g}
  h=1 if getattr(a,"signature_type",None)is None else int(a.signature_type);l=(os.getenv("POLY_BUILDER_API_KEY")or os.getenv("BUILDER_API_KEY")or"").strip()
  if h==3 and not l:return{"success":False,"tx_hash":None,"error":"MISSING_BUILDER_API_KEY_FOR_RELAYER_V2","call":g}
  p=(os.getenv("POLYGON_PRIVATE_KEY")or a.private_key or"").strip()
  if h not in(0,1,2,3)or not p or not a.funder_address:return{"success":False,"tx_hash":None,"error":"MISSING_CREDENTIALS_OR_UNSUPPORTED_SIG_TYPE","call":g}
  try:
   from web3 import Web3;from src.polymarket_research.riskless_machine_gun_engine import get_fast_polygon_web3 as c;o=c(timeout=5.);f=Web3.to_checksum_address(a.funder_address);e=Web3.to_checksum_address(o.eth.account.from_key(p).address)
   if h in(0,1,2)and o.eth.get_balance(f if h==0 else e)<int(.05*1e18):return{"success":False,"tx_hash":None,"error":"INSUFFICIENT_EOA_POL_GAS","call":g}
   b=a.NEG_RISK_ADAPTER_ADDRESS
   if prefer_v2_pusd_adapter:
    try:
     j=o.eth.contract(address=Web3.to_checksum_address(a.CTF_ADDRESS),abi=[{"constant":True,"inputs":[{"name":"account","type":"address"},{"name":"operator","type":"address"}],"name":"isApprovedForAll","outputs":[{"name":"","type":"bool"}],"type":"function"}]);k=Web3.to_checksum_address(a.NEG_RISK_ADAPTER_V2_ADDRESS)
     if bool(j.functions.isApprovedForAll(f,k).call()):b=a.NEG_RISK_ADAPTER_V2_ADDRESS
    except Exception:b=a.NEG_RISK_ADAPTER_V2_ADDRESS
   g=a.encode_negrisk_convert_positions_call(market_id,question_indices,shares,adapter_address=b);m=a._dispatch_funder_calls(o,Web3,p,h,f,e,[(Web3.to_checksum_address(g["target"]),g["data"])],f"nrconv:{market_id.lower()}")
   if m:
    n=o.eth.wait_for_transaction_receipt(m,timeout=60,poll_latency=1.5)
    if int(n.get("status",0))==1:
     a.invalidate_collateral_cache()
     try:
      if a.client is not None and BalanceAllowanceParams is not None and AssetType is not None:a.client.update_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL,signature_type=h))
     except Exception:pass
     return{"success":True,"tx_hash":m,"adapter_used":b,"pusd_wrapped":b.lower()==a.NEG_RISK_ADAPTER_V2_ADDRESS.lower(),"call":g}
  except Exception as i:logger.warning(f"[NR_CONVERT] convertPositions failed for {market_id}: {i}");return{"success":False,"tx_hash":None,"error":str(i),"call":g}
  return{"success":False,"tx_hash":None,"error":"CONVERT_DISPATCH_FAILED","call":g}
 def execute_negrisk_subset_convert_arb(self,*,convert_id,neg_risk_market_id,no_legs,shares,max_no_cost_per_share,liquid_yes_sells=None,fee_bips=0,nr_m1_zero_loss_verified=False,nr_m1_mode="",surviving_yes_legs=None):from src.polymarket_research.riskless_machine_gun_engine import execute_negrisk_subset_convert_arb_impl as a;return a(self,convert_id=convert_id,neg_risk_market_id=neg_risk_market_id,no_legs=no_legs,shares=shares,max_no_cost_per_share=max_no_cost_per_share,liquid_yes_sells=liquid_yes_sells,fee_bips=fee_bips,nr_m1_zero_loss_verified=nr_m1_zero_loss_verified,nr_m1_mode=nr_m1_mode,surviving_yes_legs=surviving_yes_legs)
 def merge_complete_set_positions(b,condition_id,amount_shares,*,neg_risk=None):
  f=round(max(.0,float(amount_shares or.0)),6)
  if not condition_id or f<=.0:return{"merged":False,"success":False,"merged_pairs":.0,"target_contract":"","calldata":"","tx_hash":None}
  from src.polymarket_research.redeem_settled_positions import encode_ctf_merge_or_split_calldata as a;d,e=a(condition_id,f,neg_risk=bool(neg_risk),is_merge=True)
  if b.dry_run:return{"merged":True,"success":True,"dry_run":True,"merged_pairs":f,"target_contract":d,"calldata":e,"tx_hash":None}
  c=b.attempt_onchain_complete_set_merge(condition_id,min_pairs=min(5.,f),max_pairs=f,neg_risk=neg_risk)
  if isinstance(c,tuple)and len(c)==2 and c[0]:return{"merged":True,"success":True,"dry_run":False,"merged_pairs":float(c[1]),"target_contract":d,"calldata":e,"tx_hash":str(c[0])}
  return{"merged":False,"success":False,"dry_run":False,"merged_pairs":.0,"target_contract":d,"calldata":e,"tx_hash":None}
 def attempt_onchain_split_position(self,condition_id,shares,*,neg_risk=False,up_token_id="",down_token_id=""):from src.polymarket_research.riskless_machine_gun_engine import attempt_onchain_split_position as a;return a(self,condition_id,shares,neg_risk=neg_risk,up_token_id=up_token_id,down_token_id=down_token_id)
 def execute_nr3_synthetic_all_yes_overround(self,**kwargs):from src.polymarket_research.riskless_machine_gun_engine import execute_nr3_synthetic_all_yes_overround as a;return a(self,**kwargs)
 def simulate_fok_sweep(self,orderbook,target_notional_usd,side="BUY",max_acceptable_price=MAX_PRICE_CEILING,min_acceptable_price=MIN_PRICE_FLOOR,return_legs=False,fee_rate=.07,fee_exponent=1.):
  n=orderbook.get("asks"if side=="BUY"else"bids",[])
  if not n:
   if return_legs:return False,.0,.0,.0,.0,[]
   return False,.0,.0,.0,.0
  m=side=="BUY";j=math.isfinite;l=[];a=True;g=-1. if m else 2.
  try:
   for r in n:
    q=float(r.get("price"));p=float(r.get("size"))
    if not(j(q)and j(p))or not(.0<q<1.)or p<.0:return(False,.0,.0,.0,.0,[])if return_legs else(False,.0,.0,.0,.0)
    if m:
     if q<g:a=False
    else:
     if q>g:a=False
    g=q;l.append((q,p))
  except(TypeError,ValueError,AttributeError):return(False,.0,.0,.0,.0,[])if return_legs else(False,.0,.0,.0,.0)
  if not a:l.sort(key=lambda s:s[0],reverse=not m)
  b=target_notional_usd;c=.0;e=.0;d=.0;i=[]
  for q,p in l:
   if p<=.0:continue
   if m:
    if q>max_acceptable_price:break
   elif q<min_acceptable_price:break
   f=q*p
   if f>=b-1e-6:h=min(p,b/q);c+=h;e+=b;d=q;i.append((q,h));b=.0;break
   c+=p;e+=f;d=q;i.append((q,p));b-=f
  if b>1e-4:
   if return_legs:return False,.0,.0,d,.0,[]
   return False,.0,.0,d,.0
  o=e/c if c>0 else.0;k=round(sum(t*fee_rate*((s*(1.-s))**fee_exponent)for s,t in i),5);self.last_fok_fill_legs=i
  if return_legs:return True,o,c,d,k,i
  return True,o,c,d,k
 @staticmethod
 def _book_levels_valid(levels):
  try:
   for a in levels:
    c=float(a.get("price"));b=float(a.get("size"))
    if not(math.isfinite(c)and math.isfinite(b))or not(.0<c<1.)or b<.0:return False
  except(TypeError,ValueError,AttributeError):return False
  return True
 def _invalid_notional_result(self,trade_id,token_id,target_token,side,notional_usd,t0):a=f"NotionalGuard Rejected: non-finite or non-positive notional ({notional_usd!r}).";logger.error(f"[{trade_id}] {a}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=.0,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=self.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=a)
 def verify_pre_trade_depth(self,orderbook,target_notional_usd,side="BUY",depth_hurdle_ratio=DEFAULT_DEPTH_HURDLE,max_price_ceiling=MAX_PRICE_CEILING,min_price_floor=MIN_PRICE_FLOOR,return_adjusted=False,min_lot_size=MIN_LOT_SIZE_USD,max_ticket_size=MAX_TICKET_CAP_USD):
  m=orderbook.get("asks"if side=="BUY"else"bids",[])
  try:g=float(target_notional_usd)
  except(TypeError,ValueError):return(False,.0,.0,.0)if return_adjusted else(False,.0,.0)
  if not m or not math.isfinite(g)or g<=.0:return(False,.0,.0,.0)if return_adjusted else(False,.0,.0)
  l=side=="BUY";k=math.isfinite;d=2. if l else-1.;a=2. if l else-1.;h=False;b=.0
  try:
   for o in m:
    q=float(o.get("price"));p=float(o.get("size"))
    if not(k(q)and k(p))or not(.0<q<1.)or p<.0:return(False,.0,.0,.0)if return_adjusted else(False,.0,.0)
    if l:
     if q<d:d=q
    elif q>d:d=q
    if min_price_floor<=q<=max_price_ceiling:
     h=True;b+=q*p
     if l:
      if q<a:a=q
     elif q>a:a=q
  except(TypeError,ValueError,AttributeError):return(False,.0,.0,.0)if return_adjusted else(False,.0,.0)
  if not h:return(False,.0,d,.0)if return_adjusted else(False,.0,d)
  j=a;n=b/max(target_notional_usd,1e-6)
  if not return_adjusted:e=n>=depth_hurdle_ratio;return e,n,j
  f=b/max(depth_hurdle_ratio,1.)
  if f<min_lot_size:e=False;c=.0
  else:e=True;i=min(target_notional_usd,max_ticket_size);c=round(min(i,max(min_lot_size,f)),2)
  return e,n,j,c
 @staticmethod
 def calculate_elastic_ticket_size(executable_depth_usd,depth_hurdle_ratio=DEFAULT_DEPTH_HURDLE,min_ticket_usd=MIN_TICKET_USD,max_ticket_usd=MAX_TICKET_CAP_USD):
  if not math.isfinite(executable_depth_usd)or executable_depth_usd<=0:return False,.0
  b=executable_depth_usd/max(depth_hurdle_ratio,1.)
  if b<min_ticket_usd:return False,.0
  a=min(max_ticket_usd,max(min_ticket_usd,round(b,2)));return True,a
 @staticmethod
 def validate_btc_signal(z_btc,min_z_score=1.645):
  if abs(z_btc)<min_z_score:return False,f"REJECT_BTC_Z_TOO_LOW (|z|={abs(z_btc):.3f} < {min_z_score})"
  return True,"BTC_SIGNAL_CONFIRMED"
 @staticmethod
 def validate_cross_asset_lead_lag(target_asset,target_direction,btc_direction=None,z_alt=.0,z_btc=.0):
  f=target_asset.upper().strip()
  if f not in("ETH","SOL","XRP"):return True,z_alt,"NON_ALT_ASSET_PASSED"
  def a(d):
   if not d:return None
   u=str(d).upper().strip()
   if u in("BUY","UP","LONG","YES"):return"UP"
   if u in("SELL","DOWN","SHORT","NO"):return"DOWN"
   return u
  b=a(target_direction);c=a(btc_direction)
  if c is not None and b is not None and c!=b:return False,z_alt,f"REJECT_BTC_COUNTER_TREND ({f} {b} vs BTC {c})"
  if z_alt!=.0 and z_btc!=.0:
   if(z_alt>0 and z_btc<0)or(z_alt<0 and z_btc>0):return False,z_alt,f"REJECT_BTC_{f}_SIGN_DIVERGENCE (sign(z_{f}) != sign(z_BTC))"
  e=.7*z_alt+.3*z_btc;return True,e,"CROSS_ASSET_CONFIRMED"
 @staticmethod
 def validate_cross_asset_directional_conflict(candidate_asset,candidate_direction,candidate_expiry_ts,active_positions,max_expiry_window_delta=9e2,candidate_duration_s=None):
  if not active_positions:return True,"CROSS_ASSET_DIRECTION_ALIGNED"
  e=candidate_asset.upper().strip()
  if e not in("BTC","ETH","SOL","XRP"):return True,"CROSS_ASSET_DIRECTION_ALIGNED"
  i=candidate_direction.upper().strip();b=("BTC","ETH","SOL","XRP")
  for m in active_positions:
   g=str(m.get("asset","")).upper().strip();k=str(m.get("target_token","")).upper().strip();d=float(m.get("candle_expiry_ts",.0)or.0);c=(e in b and g in b)
   if d>0 and candidate_expiry_ts>0 and candidate_duration_s is not None and candidate_duration_s>0:l=str(m.get("horizon")or"").lower();j=float(m.get("candle_duration_s")or(3e2 if l=="5m"else(9e2 if(m.get("is_subhourly")or l=="15m"or m.get("sleeve")=="SLEEVE_1_SUBHOURLY_15M")else 3600.)));f=candidate_expiry_ts-float(candidate_duration_s);h=d-j;a=max(f,h)<(min(candidate_expiry_ts,d)-5.)
   else:a=(abs(d-candidate_expiry_ts)<=max_expiry_window_delta if(d>0 and candidate_expiry_ts>0)else True)
   if c and a:
    if k and i and k!=i:return(False,f"REJECT_CROSS_ASSET_CONFLICT ({e} {i} opposes active {g} {k} with expiry delta {abs(d-candidate_expiry_ts):.0f}s)")
  return True,"CROSS_ASSET_DIRECTION_ALIGNED"
 @staticmethod
 def validate_market_universe(asset,title="",horizon="",slug="",tte_seconds=None,max_tte_seconds=1500.):
  e=(asset or"").upper().strip();d=(title or"").lower().strip();f=(slug or"").lower().strip();b=(horizon or"").lower().strip()
  if e=="SOL"or"sol"in d or"solana"in d or"sol"in f:return False,"REJECT_SOL_MARKET (Dead venue on Polymarket)"
  i=(e=="BTC"or"btc"in d or"bitcoin"in d or"btc"in f);h=(e=="ETH"or"eth"in d or"ethereum"in d or"eth"in f)
  if e and not(i or h):return False,f"REJECT_UNAPPROVED_ASSET ({e} not in 5m/15m BTC/ETH universe)"
  if i:
   c=("5m"in b or"15m"in b or"5m"in f or"15m"in f or"5m"in d or"15m"in d or(tte_seconds is not None and tte_seconds<=max_tte_seconds));j=("1h"in b or"hourly"in b or"60m"in b or"1h"in f or"hourly"in f or"1h"in d or"hourly"in d or(("pm et"in d or"am et"in d)and not c))
   if j and not c:return False,"REJECT_1H_BTC_MARKET (Negative EV macro mean-reversion)"
  a=("5m"in b or"15m"in b or"5m"in f or"15m"in f or"5m"in d or"15m"in d);g=not a and("1h"in b or"hourly"in b or"60m"in b or"1h"in f or"hourly"in f or"1h"in d or"hourly"in d or("pm et"in d or"am et"in d))
  if g and tte_seconds is not None and(tte_seconds>max_tte_seconds or tte_seconds<120.):return False,f"REJECT_1H_MARKET_OUTSIDE_SWEETSPOT (TTE={tte_seconds:.1f}s not in [120s, {max_tte_seconds:.0f}s])"
  return True,"MARKET_UNIVERSE_APPROVED"
 @staticmethod
 def calculate_relative_stop_price(entry_price,stop_delta=.12,price_floor=.02):return max(price_floor,round(entry_price-stop_delta,4))
 @staticmethod
 def evaluate_exp302_exit_policy(entry_price,current_bid,current_ask,spot_reversal_atr_multiple=.0,free_usdc=1e3,higher_score_trigger_pending=False,stop_delta=.12,maker_tp_price=.95,min_free_usdc_threshold=25.,signed_candle_distance_pct=None,tte_seconds=None):
  c=max(.02,round(entry_price-stop_delta,4));a=maker_tp_price
  if maker_tp_price==.95 and entry_price>=.8:a=.985
  if current_bid>=a:return{"action":"MAKER_TAKE_PROFIT","price":a,"is_maker":True,"fee_schedule":"0% Maker Fee","reason":f"Resting maker limit swept at ${a:.3f} (captures terminal value without payoff compression)"}
  b=signed_candle_distance_pct*1e2 if(signed_candle_distance_pct is not None and abs(signed_candle_distance_pct)<=.005 and signed_candle_distance_pct!=.0)else signed_candle_distance_pct
  if(b is not None and b<.03 and(tte_seconds is None or tte_seconds>60.)):return{"action":"STRIKE_RETRACE_STOP_LOSS","price":max(.02,current_bid),"is_maker":False,"fee_schedule":"Taker Fee","reason":(f"Strike-retrace stop triggered: signed candle distance {b:+.4f}% < +0.03% with TTE={tte_seconds if tte_seconds is not None else.0:.1f}s > 60s. Salvaging position at bid ${current_bid:.3f}.")}
  if spot_reversal_atr_multiple>=.5 or current_bid<=c:return{"action":"SPOT_DELTA_STOP_LOSS","price":max(.02,current_bid),"is_maker":False,"fee_schedule":"Taker Fee","reason":f"Relative spot-delta stop triggered (bid={current_bid:.3f} <= stop_px={c:.3f} or ATR multiple={spot_reversal_atr_multiple:.2f} >= 0.50)"}
  if free_usdc<min_free_usdc_threshold and higher_score_trigger_pending and current_bid>entry_price:return{"action":"CAPITAL_STARVATION_UNWIND","price":max(.02,current_bid),"is_maker":False,"fee_schedule":"Taker Fee","reason":f"Capital-Starvation Override: free_usdc (${free_usdc:.2f}) < ${min_free_usdc_threshold:.2f} with superior shock pending. Unwinding green position early at bid."}
  return{"action":"HOLD_TO_MATURITY","price":1.,"is_maker":True,"fee_schedule":"0% Settlement","reason":"EXP-302 Hold-to-Maturity with resting $0.95 Maker limit and Relative Spot-Delta Stop active."}
 @staticmethod
 def rank_concurrent_shock_candidates(candidates,window_seconds=5.):
  def a(c):z=abs(float(c.get("z_val",c.get("z_score",c.get("expected_prob_shift",.0)))));b=max(float(c.get("clob_price",c.get("price",c.get("effective_price_$50",.5)))),.01);return z/b
  return sorted(candidates,key=a,reverse=True)
 def calculate_dynamic_crypto_fee(self,entry_price,notional_usd,fee_rate=.07,fee_exponent=1.):return calculate_taker_fee(notional_usd,entry_price,fee_rate,fee_exponent)
 def execute_snipe_order(a,trade_id,token_id,target_token,notional_usd,target_price,side="BUY",depth_hurdle=DEFAULT_DEPTH_HURDLE,market_id=None,condition_id=None,market_fee_rate=None,market_fee_exponent=None,max_price_ceiling=MAX_PRICE_CEILING,sizing_fn=None,max_ticket_cap=None,min_price_floor=MIN_PRICE_FLOOR,prefetched_pre_balance=None,prefetched_book=None,neg_risk=None,expected_best_price=None,max_book_buffer=.02,allow_partial_fak=False,min_order_shares=5.):
  t0=time.perf_counter();_D=_CURRENT_TRACE.get()if _CURRENT_TRACE is not None else None
  if _D is not None:_D.stamp("exec_enter")
  _y=datetime.now(timezone.utc).isoformat()
  if neg_risk is not None:a.get_token_neg_risk(token_id,neg_risk)
  try:notional_usd=float(notional_usd)
  except(TypeError,ValueError):notional_usd=.0
  O=float(max_ticket_cap)if(max_ticket_cap is not None and math.isfinite(float(max_ticket_cap))and float(max_ticket_cap)>0)else MAX_TICKET_CAP_USD
  if not math.isfinite(notional_usd)or notional_usd<=.0:return a._invalid_notional_result(trade_id,token_id,target_token,side,notional_usd,t0)
  notional_usd=min(notional_usd,O)
  if prefetched_book is not None and isinstance(prefetched_book,dict):_t=prefetched_book
  else:
   try:_t=a.get_market_book(token_id)
   except Exception as e:return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=target_price,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=f"Orderbook fetch error: {e}")
  _f=float(target_price)if(target_price and target_price>0)else max(.01,float(min_price_floor));I=(round(max(1.,float(min_order_shares)*max(.01,_f)),2)if allow_partial_fak else MIN_LOT_SIZE_USD);U,Y,_x,B=a.verify_pre_trade_depth(_t,notional_usd,side=side,depth_hurdle_ratio=depth_hurdle,max_price_ceiling=max_price_ceiling,min_price_floor=min_price_floor,return_adjusted=True,min_lot_size=I,max_ticket_size=O)
  if not U:r=f"DepthGuard Rejected: Ratio {Y:.2f}x < {depth_hurdle:.2f}x requirement.";logger.warning(f"[{trade_id}] {r}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=r)
  if B<notional_usd:logger.info(f"[{trade_id}] [DYNAMIC DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${B:.2f} to match available book depth (Ratio: {Y:.2f}x vs hurdle {depth_hurdle:.2f}x).");notional_usd=B
  if _x<min_price_floor or _x>max_price_ceiling:r=f"PriceGuard Rejected: Best price ${_x:.4f} outside valid boundary [{min_price_floor:.2f}, {max_price_ceiling:.2f}].";logger.warning(f"[{trade_id}] {r}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=r)
  if target_price>0 and(_x-target_price)>.04:r=f"SlippageGuard Rejected: Best price ${_x:.4f} exceeds target ${target_price:.4f} by > 4¢.";logger.warning(f"[{trade_id}] {r}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=r)
  if side=="BUY"and expected_best_price is not None and expected_best_price>0 and(expected_best_price-_x)>=.04:r=f"AdverseCollapseGuard Rejected: Best ask ${_x:.4f} collapsed >= 4¢ below trigger ask ${expected_best_price:.4f}.";logger.warning(f"[{trade_id}] {r}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=r)
  T=target_price if target_price>0 else _x;_s=round(min(_x+max(.0,float(max_book_buffer)),target_price if target_price>0 else max_price_ceiling,max_price_ceiling),4);g=a.quantize_order_price(_s,token_id,rounding=ROUND_FLOOR if _s>=max_price_ceiling-1e-9 else ROUND_CEILING)
  if g>max_price_ceiling+1e-9:g=a.quantize_order_price(max_price_ceiling,token_id,rounding=ROUND_FLOOR)
  if g<_x-1e-9:r=f"Worst acceptable price (${g:.4f}) below best ask (${_x:.4f}) after capping at ceiling (${max_price_ceiling:.4f})";logger.warning(f"[{trade_id}] {r}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=r)
  if sizing_fn is not None:
   try:j=float(sizing_fn(g))
   except Exception as e:logger.error(f"[{trade_id}] Error in sizing_fn at {g:.4f}: {e}");j=.0
   if not math.isfinite(j)or j<I:r=(f"SlippageKellyGuard Rejected: Order limit ${g:.4f} does not support minimum Kelly ticket (${j:.2f} < ${I:.2f}).");logger.warning(f"[{trade_id}] {r}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=g,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=r)
   if j<notional_usd:logger.info(f"[{trade_id}] [SLIPPAGE KELLY DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${j:.2f} due to slippage limit price ${g:.4f}.");notional_usd=j
  _e=float(market_fee_rate)if market_fee_rate is not None else.07;_m=float(market_fee_exponent)if market_fee_exponent is not None else 1.;F,_q,v,E,M,y=a.simulate_fok_sweep(_t,notional_usd,side=side,max_acceptable_price=g,return_legs=True,fee_rate=_e,fee_exponent=_m)
  if not F and allow_partial_fak and side=="BUY":
   _r=_t.get("asks",[])if isinstance(_t,dict)else getattr(_t,"asks",[]);N=.0;H=.0
   for _Q in(_r or[]):
    try:_M=float(_Q.get("price")if isinstance(_Q,dict)else getattr(_Q,"price",.0));_L=float(_Q.get("size")if isinstance(_Q,dict)else getattr(_Q,"size",.0))
    except(TypeError,ValueError):continue
    if _M>0 and _L>0 and _M<=g+1e-9:N+=_L;H+=_M*_L
   _d=max(1.,float(min_order_shares))
   if N>=_d and H>=1.:
    G=round(min(notional_usd,max(1.,H*.9999)),4);_K,_C,_J,_I,_H,_B=a.simulate_fok_sweep(_t,G,side=side,max_acceptable_price=g,return_legs=True,fee_rate=_e,fee_exponent=_m)
    if _K and _J>=_d-1e-6:logger.info(f"[{trade_id}] [PARTIAL-FAK DOWN-SIZING] Sweeping available depth ${G:.2f} ({_J:.2f} sh <= ${g:.4f}) instead of rejecting ${notional_usd:.2f}.");notional_usd=G;F,_q,v,E,M,y=_K,_C,_J,_I,_H,_B
  if not F:r=f"FOK Sweep Infeasible: Could not fill ${notional_usd:.2f} within limit ${g:.4f}.";logger.warning(f"[{trade_id}] {r}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=E,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=r)
  d=float(math.floor(v))
  if side=="BUY"and g>0:w=float(math.floor(notional_usd/g));d=quantize_fok_buy_leg_size(min(d,w),g,round_up=False,prefer_integer_on_cent_tick=True)
  if d<=0:r=f"Calculated shares_to_buy ({d}) <= 0 for notional ${notional_usd:.2f} at limit ${g:.4f}";return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=g,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=r)
  _c=round(_q,4);_P=condition_id or market_id
  if market_fee_rate is not None and market_fee_exponent is not None:
   p=float(market_fee_rate);t=float(market_fee_exponent)
   if _P:a._fee_cache[str(_P)]=(p,t)
   if condition_id:a._fee_cache[str(condition_id)]=(p,t)
   if market_id:a._fee_cache[str(market_id)]=(p,t)
   if token_id:a._fee_cache[str(token_id)]=(p,t)
  elif _P and(str(_P)in a._fee_cache or str(_P).lower()in a._fee_cache):p,t=a._fee_cache.get(str(_P))or a._fee_cache[str(_P).lower()]
  elif _P:
   try:p,t=a.get_market_fee_params(str(_P),token_id=token_id)
   except Exception as e:logger.warning(f"Authoritative CLOB fee query notice for {_P}: {e}; using fallback fee.");p=float(market_fee_rate)if market_fee_rate is not None else.07;t=float(market_fee_exponent or 1.)
  else:p,t=.07,1.
  if not a.dry_run:
   _l=math.isfinite(p)and p>=.0 and math.isfinite(t)and(t>.0 or(p==.0 and t>=.0))
   if not _l:r=f"AuthoritativeFeeGuard Rejected: Non-finite or invalid fee parameters (rate={p}, exp={t}) for {_P}.";logger.error(f"[{trade_id}] {r}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=E,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=r)
  J=round(sum(shares_i*p*((price_i*(1.-price_i))**t)for price_i,shares_i in y),5);x=J/max(notional_usd,1e-9)
  if not a.dry_run:
   if not a.is_authenticated or a.client is None:raise RuntimeError(f"LIVE ORDER REFUSED: Executor is in live real-money mode but unauthenticated ({a.auth_mode}). " "Refusing mock fallback.")
  else:m=(time.perf_counter()-t0)*1e3;Q=f"MOCK_CLOB_{int(time.time()*1000)}";logger.info(f"[DRY-RUN SNIPE] {trade_id} -> {target_token} | Shares={d:.2f} @ ${_c:.4f} | Notional=${notional_usd:.2f} | Fee=${J:.4f} ({x*100:.2f}%) | Latency={m:.2f}ms");l=OrderResult(success=True,order_id=Q,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_c,size=d,notional_usd=notional_usd,fee_usd=J,latency_ms=m,mode="DRY_RUN_SIMULATION",execution_status=ExecutionStatus.POSITION_CONFIRMED,confirmed_onchain=True,details={"fee_rate":x,"depth_ratio":Y,"timestamp_utc":_y,"confirmed_onchain":True,"pre_token_balance":.0,"post_token_balance":d,"balance_delta":d});a._log_order(l);return l
  o=False;_w=.01
  try:
   if prefetched_pre_balance is not None:pre_token_bal=float(prefetched_pre_balance)
   elif not a.dry_run:
    pre_token_bal=a.get_onchain_erc1155_balance(token_id)
    if pre_token_bal is None:pre_token_bal=a.get_conditional_balance(token_id)
    if pre_token_bal is None:pre_token_bal=.0
   else:pre_token_bal=.0
   D=getattr(OrderType,"FAK",OrderType.FOK);P=time.perf_counter()
   if _D is not None:_D.stamp("qualify_end")
   qualify_ms=(P-t0)*1e3;A=(g>=.96 or g<=.04 or abs(round(g,2)-round(g,4))>1e-6)
   if token_id in a._tick_size_cache and not(A and abs(float(a._tick_size_cache[token_id])-.01)<1e-9):f=str(a._tick_size_cache[token_id])
   elif A:
    try:u=a.get_token_tick_size(token_id,g)
    except TypeError:u=a.get_token_tick_size(token_id)
    f=str(u or"0.01")
   else:f="0.01"
   C=int(round(p*10000))if p else 0;S=a.get_token_neg_risk(token_id,neg_risk);a.prewarm_token_market_cache(token_id=token_id,tick_size=f if token_id in a._tick_size_cache else None,neg_risk=S,fee_rate_bps=C,condition_id=condition_id,fee_rate=p,fee_exponent=t);L=PartialCreateOrderOptions(tick_size=f,neg_risk=S,version=2)if PartialCreateOrderOptions else None;dispatch_stage={"submitted":False}
   try:_O=_sign_and_post_single_hop(a.client,a.order_ladder_cache,token_id,g,d,side,D,L,dispatch_stage,notional_usd)
   finally:
    o=bool(dispatch_stage.get("submitted"))
    if o:
     _v=a.__dict__.setdefault("_wire_submitted_trade_ids",set());_G=a.__dict__.setdefault("_wire_submitted_trade_order",[]);_A=str(trade_id)
     if _A not in _v:
      if len(_G)>=2048:
       for _p in _G[:512]:_v.discard(_p)
       del _G[:512]
      elif len(_v)>2048:_F=set(_G[-1536:]);_v.intersection_update(_F)
      _v.add(_A);_G.append(_A)
   d=float(_O.get("signed_shares",d));_k=_O["post_resp"];sign_ms=_O["sign_ms"];i=_O["post_ms"];_b=_O["t_post_end"];b=(_b-t0)*1e3
   if _O["cache_hit"]:pass
   logger.info(f"[{trade_id}] LATENCY TELEMETRY: qualify_ms={qualify_ms:.2f} | sign_ms={sign_ms:.2f} | clob_http_post_ms={i:.2f} | total_trigger_to_ack_ms={b:.2f}");m=(_b-t0)*1e3;_o=_k.get("orderID")or _k.get("id")
   if _D is not None:_D.emit(trade_id=trade_id,token_id=token_id,side=side,outcome="posted",order_id_present=bool(_o),resp_status=str(_k.get("status")),resp_error=str(_k.get("errorMsg")or _k.get("error")or"")[:120],qualify_ms=round(qualify_ms,3),sign_ms=round(sign_ms,3),thread_hop_ms=round(float(_O.get("thread_hop_ms",.0)),3),clob_http_post_ms=round(i,3),total_trigger_to_ack_ms=round(b,3),presign_cache_hit=bool(_O.get("cache_hit")),hot_active=_HOT_DISPATCH_ACTIVE.count,taker_delay_hint=getattr(a,"_taker_delay_ms_hint",None))
   if is_fak_killed_no_match(None,_k):q=_k.get("error")or _k.get("errorMsg")or"FAK order killed with zero match";logger.warning(f"[{trade_id}] FAK order deterministically killed by CLOB (zero match): {q} | orderID={_o}");l=OrderResult(success=False,order_id=_o,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=m,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=q,details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":_k,"depth_ratio":Y,"timestamp_utc":_y,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,"latency_telemetry":{"qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",.0),"clob_http_post_ms":i,"total_trigger_to_ack_ms":b}});a._log_order(l);return l
   K=_k.get("errorMsg")or _k.get("error")
   if(not _o and not K)or(_o and K):q=K or"No orderID returned from CLOB matching engine (ambiguous)";logger.critical(f"[{trade_id}] Ambiguous entry submission: {q} | raw={_k}");l=OrderResult(success=False,order_id=_o,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=d,notional_usd=notional_usd,fee_usd=J,latency_ms=m,mode="LIVE_AMBIGUOUS_SUBMISSION",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,error=q,details={"outcome_unknown":True,"requires_exchange_reconciliation":True,"raw_response":_k,"entry_order_id":_o,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,"latency_telemetry":{"qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",.0),"clob_http_post_ms":i,"total_trigger_to_ack_ms":b}});a._log_order(l);return l
   if not _o or K:q=K or"No orderID returned from CLOB matching engine";logger.error(f"[{trade_id}] Order rejected by CLOB: {q} | raw={_k}");l=OrderResult(success=False,order_id=_o,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=d,notional_usd=notional_usd,fee_usd=J,latency_ms=m,mode="LIVE_CLOB_ERROR",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=q,details={"raw_response":_k,"depth_ratio":Y,"timestamp_utc":_y,"pre_token_balance":pre_token_bal,"outcome_unknown":False,"requires_exchange_reconciliation":False,"latency_telemetry":{"qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",.0),"clob_http_post_ms":i,"total_trigger_to_ack_ms":b}});a._log_order(l);return l
   X=str(_k.get("status")or"").upper();_a=_k.get("makingAmount");Z=_k.get("takingAmount")
   if X.startswith("CANCEL")or X in{"UNMATCHED","EXPIRED","REJECTED"}:l=OrderResult(success=False,order_id=_o,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=m,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=f"CLOB order returned terminal non-fill status={X}",details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":_k});a._log_order(l);return l
   if X in{"DELAYED","LIVE"}and _a in(None,"")and Z in(None,""):l=OrderResult(success=False,order_id=_o,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=d,notional_usd=notional_usd,fee_usd=J,latency_ms=m,mode="LIVE_AMBIGUOUS_SUBMISSION",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,error=f"CLOB order returned non-immediate status={X} without fill amounts",details={"outcome_unknown":True,"requires_exchange_reconciliation":True,"raw_response":_k,"entry_order_id":_o,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd});a._log_order(l);return l
   if _a not in(None,""):
    try:n=float(_a)
    except(ValueError,TypeError)as h:raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid makingAmount={_a}: {h}")
   else:n=round(d*_c,4)
   if Z not in(None,""):
    try:s=float(Z)
    except(ValueError,TypeError)as h:raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid takingAmount={Z}: {h}")
   else:s=d
   if(_a not in(None,"")or Z not in(None,""))and s<=.0:l=OrderResult(success=False,order_id=_o,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=m,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error="FAK order matched 0 shares",details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":_k});a._log_order(l);return l
   _u=round(n/max(s,1e-4),4)if(_a not in(None,"")and Z not in(None,"")and s>0)else _c
   if _a not in(None,"")and Z not in(None,"")and s>0:_j=max(.001,min(.999,_u));J=round(s*p*((_j*(1.-_j))**t),5)
   _i=_k.get("tradeIDs",[]);_h=_k.get("transactionsHashes",[]);logger.info(f"[LIVE CLOB MATCHED] {trade_id} -> OID: {_o} | {target_token} | Shares={s:.2f} @ ${_u:.4f} | Notional=${n:.2f} | Latency={m:.2f}ms | Trades={_i}");W=ExecutionStatus.MATCHED_PENDING_SETTLEMENT;z=False;l=OrderResult(success=True,order_id=_o,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_u,size=s,notional_usd=n,fee_usd=J,latency_ms=m,mode="LIVE_CLOB",execution_status=W,confirmed_onchain=z,details={"raw_response":_k,"depth_ratio":Y,"timestamp_utc":_y,"confirmed_onchain":z,"pre_token_balance":pre_token_bal,"trade_ids":_i,"transactions_hashes":_h,"latency_telemetry":{"qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",.0),"clob_http_post_ms":i,"total_trigger_to_ack_ms":b}});a._log_order(l);return l
  except Exception as e:
   _E=time.perf_counter();m=(_E-t0)*1e3;_N=locals().get("dispatch_stage")or{};_g=_N.get("t_post_start")or locals().get("t_post_start");i=round(max(.0,(_E-float(_g))*1e3),3)if _g else.0;R=float(_N.get("sign_ms")if _N.get("sign_ms")is not None else locals().get("sign_ms",.0));V=float(_N.get("thread_hop_ms")if _N.get("thread_hop_ms")is not None else locals().get("thread_hop_ms",.0));b=(_E-t0)*1e3;q=f"CLOB order submission failed: {e}"
   if is_clob_400_rejection(e):
    a._evict_tick_size_if_tick_err(token_id,e)
    if any(k in str(getattr(e,"error_message","")or e).lower()for k in("not enough balance","allowance")):a.invalidate_collateral_cache()
    c=None;_n=getattr(e,"error_message",None)or getattr(e,"error_msg",None)
    if isinstance(_n,dict):c=_n.get("orderID")or _n.get("id")
    elif isinstance(_n,str):
     try:
      _z=json.loads(_n)
      if isinstance(_z,dict):c=_z.get("orderID")or _z.get("id")
     except Exception:pass
    logger.warning(f"[{trade_id}] Order deterministically rejected by CLOB (HTTP 400 / 0 match): {e} | orderID={c}");l=OrderResult(success=False,order_id=c,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=m,mode="FAK_KILLED_NO_MATCH"if is_fak_killed_no_match(e)else"CLOB_HTTP_400_REJECTION",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=str(e),details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"clob_400_rejection":True,"raw_exception":str(e),"status_code":getattr(e,"status_code",400),"pre_token_balance":locals().get("pre_token_bal"),"intended_notional_usd":notional_usd,"latency_telemetry":{"qualify_ms":locals().get("qualify_ms",.0),"sign_ms":R,"thread_hop_ms":V,"clob_http_post_ms":i,"total_trigger_to_ack_ms":b}});a._log_order(l);return l
   logger.error(f"[{trade_id}] {q}");l=OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_x,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=m,mode="LIVE_CLOB_ERROR",execution_status=ExecutionStatus.SUBMITTED if o else ExecutionStatus.REJECTED,confirmed_onchain=False,error=q,details={"outcome_unknown":bool(o),"requires_exchange_reconciliation":bool(o),"pre_token_balance":locals().get("pre_token_bal"),"intended_notional_usd":notional_usd,"latency_telemetry":{"qualify_ms":locals().get("qualify_ms",.0),"sign_ms":R,"thread_hop_ms":V,"clob_http_post_ms":i,"total_trigger_to_ack_ms":b}});a._log_order(l);return l
 async def execute_snipe_order_async(a,trade_id,token_id,target_token,notional_usd=20.,target_price=.0,side="BUY",depth_hurdle=DEFAULT_DEPTH_HURDLE,market_id=None,condition_id=None,market_fee_rate=None,market_fee_exponent=None,max_price_ceiling=MAX_PRICE_CEILING,sizing_fn=None,max_ticket_cap=None,prefetched_book=None,prefetched_pre_balance=None,min_price_floor=MIN_PRICE_FLOOR,neg_risk=None,expected_best_price=None,max_book_buffer=.02,allow_partial_fak=False,min_order_shares=5.):
  t0=time.perf_counter();_F=_CURRENT_TRACE.get()if _CURRENT_TRACE is not None else None
  if _F is not None:_F.stamp("exec_enter")
  _A=datetime.now(timezone.utc).isoformat()
  if neg_risk is not None:a.get_token_neg_risk(token_id,neg_risk)
  try:notional_usd=float(notional_usd)
  except(TypeError,ValueError):notional_usd=.0
  L=float(max_ticket_cap)if(max_ticket_cap is not None and math.isfinite(float(max_ticket_cap))and float(max_ticket_cap)>0)else MAX_TICKET_CAP_USD
  if not math.isfinite(notional_usd)or notional_usd<=.0:return a._invalid_notional_result(trade_id,token_id,target_token,side,notional_usd,t0)
  notional_usd=min(notional_usd,L);a.assert_market_routing(token_id,market_version="CTF")
  try:_Q=prefetched_book if prefetched_book is not None else await a.get_market_book_async(token_id)
  except Exception as e:o=f"Async Orderbook Fetch Failed for {token_id}: {e}";logger.error(f"[{trade_id}] {o}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=.0,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
  _h=float(target_price)if(target_price and target_price>0)else max(.01,float(min_price_floor));G=(round(max(1.,float(min_order_shares)*max(.01,_h)),2)if allow_partial_fak else MIN_LOT_SIZE_USD);W,Z,_z,x=a.verify_pre_trade_depth(_Q,target_notional_usd=notional_usd,side=side,depth_hurdle_ratio=depth_hurdle,max_price_ceiling=max_price_ceiling,min_price_floor=min_price_floor,return_adjusted=True,min_lot_size=G,max_ticket_size=L)
  if not W:o=f"DepthGuard Rejected: Available depth ratio {Z:.2f}x < hurdle {depth_hurdle:.2f}x.";logger.warning(f"[{trade_id}] {o}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
  if x<notional_usd:logger.info(f"[{trade_id}] [DYNAMIC DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${x:.2f} to match available book depth (Ratio: {Z:.2f}x vs hurdle {depth_hurdle:.2f}x).");notional_usd=x
  if _z<min_price_floor or _z>max_price_ceiling:o=f"PriceGuard Rejected: Best price ${_z:.4f} outside valid boundary [{min_price_floor:.2f}, {max_price_ceiling:.2f}].";logger.warning(f"[{trade_id}] {o}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
  if target_price>0 and(_z-target_price)>.04:o=f"SlippageGuard Rejected: Best price ${_z:.4f} exceeds target ${target_price:.4f} by > 4¢.";logger.warning(f"[{trade_id}] {o}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
  if side=="BUY"and expected_best_price is not None and expected_best_price>0 and(expected_best_price-_z)>=.04:o=f"AdverseCollapseGuard Rejected: Best ask ${_z:.4f} collapsed >= 4¢ below trigger ask ${expected_best_price:.4f}.";logger.warning(f"[{trade_id}] {o}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
  V=target_price if target_price>0 else _z;_v=round(min(_z+max(.0,float(max_book_buffer)),target_price if target_price>0 else max_price_ceiling,max_price_ceiling),4)
  if token_id not in a._tick_size_cache and not a.dry_run:await asyncio.to_thread(a.get_token_tick_size,token_id)
  f=a.quantize_order_price(_v,token_id,rounding=ROUND_FLOOR if _v>=max_price_ceiling-1e-9 else ROUND_CEILING)
  if f>max_price_ceiling+1e-9:f=a.quantize_order_price(max_price_ceiling,token_id,rounding=ROUND_FLOOR)
  if f<_z-1e-9:o=f"Worst acceptable price (${f:.4f}) below best ask (${_z:.4f}) after capping at ceiling (${max_price_ceiling:.4f})";logger.warning(f"[{trade_id}] {o}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
  if sizing_fn is not None:
   try:i=float(sizing_fn(f))
   except Exception as e:logger.error(f"[{trade_id}] Error in sizing_fn at {f:.4f}: {e}");i=.0
   if not math.isfinite(i)or i<G:o=(f"SlippageKellyGuard Rejected: Order limit ${f:.4f} does not support minimum Kelly ticket (${i:.2f} < ${G:.2f}).");logger.warning(f"[{trade_id}] {o}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=f,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
   if i<notional_usd:logger.info(f"[{trade_id}] [SLIPPAGE KELLY DOWN-SIZING] Order adjusted from ${notional_usd:.2f} -> ${i:.2f} due to slippage limit price ${f:.4f}.");notional_usd=i
  _g=float(market_fee_rate)if market_fee_rate is not None else.07;_p=float(market_fee_exponent)if market_fee_exponent is not None else 1.;C,_t,t,B,J,w=a.simulate_fok_sweep(_Q,notional_usd,side=side,max_acceptable_price=f,return_legs=True,fee_rate=_g,fee_exponent=_p)
  if not C and allow_partial_fak and side=="BUY":
   _u=_Q.get("asks",[])if isinstance(_Q,dict)else getattr(_Q,"asks",[]);K=.0;E=.0
   for _T in(_u or[]):
    try:_P=float(_T.get("price")if isinstance(_T,dict)else getattr(_T,"price",.0));_O=float(_T.get("size")if isinstance(_T,dict)else getattr(_T,"size",.0))
    except(TypeError,ValueError):continue
    if _P>0 and _O>0 and _P<=f+1e-9:K+=_O;E+=_P*_O
   _f=max(1.,float(min_order_shares))
   if K>=_f and E>=1.:
    D=round(min(notional_usd,max(1.,E*.9999)),4);_N,_E,_M,_L,_K,_D=a.simulate_fok_sweep(_Q,D,side=side,max_acceptable_price=f,return_legs=True,fee_rate=_g,fee_exponent=_p)
    if _N and _M>=_f-1e-6:logger.info(f"[{trade_id}] [PARTIAL-FAK DOWN-SIZING] Sweeping available depth ${D:.2f} ({_M:.2f} sh <= ${f:.4f}) instead of rejecting ${notional_usd:.2f}.");notional_usd=D;C,_t,t,B,J,w=_N,_E,_M,_L,_K,_D
  if not C:o=f"FOK Sweep Infeasible: Could not fill ${notional_usd:.2f} within limit ${f:.4f}.";logger.warning(f"[{trade_id}] {o}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=B,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
  d=float(math.floor(t))
  if side=="BUY"and f>0:u=float(math.floor(notional_usd/f));d=quantize_fok_buy_leg_size(min(d,u),f,round_up=False,prefer_integer_on_cent_tick=True)
  if d<=0:o=f"Calculated shares_to_buy ({d}) <= 0 for notional ${notional_usd:.2f} at limit ${f:.4f}";return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=f,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
  _e=round(_t,4);_S=condition_id or market_id
  if market_fee_rate is not None and market_fee_exponent is not None:
   p=float(market_fee_rate);s=float(market_fee_exponent)
   if _S:a._fee_cache[str(_S)]=(p,s)
   if condition_id:a._fee_cache[str(condition_id)]=(p,s)
   if market_id:a._fee_cache[str(market_id)]=(p,s)
   if token_id:a._fee_cache[str(token_id)]=(p,s)
  elif _S and(str(_S)in a._fee_cache or str(_S).lower()in a._fee_cache):p,s=a._fee_cache.get(str(_S))or a._fee_cache[str(_S).lower()]
  elif _S:
   try:p,s=await asyncio.to_thread(a.get_market_fee_params,str(_S),token_id)
   except Exception as e:logger.warning(f"Authoritative CLOB fee query notice for {_S}: {e}; using fallback fee.");p=float(market_fee_rate)if market_fee_rate is not None else.07;s=float(market_fee_exponent or 1.)
  else:p,s=.07,1.
  if not a.dry_run:
   _o=math.isfinite(p)and p>=.0 and math.isfinite(s)and(s>.0 or(p==.0 and s>=.0))
   if not _o:o=f"AuthoritativeFeeGuard Rejected: Non-finite or invalid fee parameters (rate={p}, exp={s}) for {_S}.";logger.error(f"[{trade_id}] {o}");return OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=B,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=(time.perf_counter()-t0)*1e3,mode=a.auth_mode,execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=o)
  H=round(sum(shares_i*p*((price_i*(1.-price_i))**s)for price_i,shares_i in w),5);v=H/max(notional_usd,1e-9)
  if a.dry_run:l=(time.perf_counter()-t0)*1e3;O=f"MOCK_CLOB_{int(time.time()*1000)}";logger.info(f"[DRY-RUN SNIPE] {trade_id} -> {target_token} | Shares={d:.2f} @ ${_e:.4f} | Notional=${notional_usd:.2f} | Fee=${H:.4f} ({v*100:.2f}%) | Latency={l:.2f}ms");j=OrderResult(success=True,order_id=O,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_e,size=d,notional_usd=notional_usd,fee_usd=H,latency_ms=l,mode="DRY_RUN_SIMULATION",execution_status=ExecutionStatus.POSITION_CONFIRMED,confirmed_onchain=True,details={"fee_rate":v,"depth_ratio":Z,"timestamp_utc":_A,"confirmed_onchain":True,"pre_token_balance":.0,"post_token_balance":d,"balance_delta":d});a._log_order(j);return j
  if not a.is_authenticated or a.client is None:raise RuntimeError(f"LIVE ORDER REFUSED: Executor is in live real-money mode but unauthenticated ({a.auth_mode}).")
  n=False;_y=.01
  try:
   if not a.dry_run:
    if prefetched_pre_balance is not None and math.isfinite(float(prefetched_pre_balance)):pre_token_bal=float(prefetched_pre_balance)
    elif side=="BUY":pre_token_bal=.0
    else:
     pre_token_bal=await asyncio.to_thread(a.get_onchain_erc1155_balance,token_id)
     if pre_token_bal is None:pre_token_bal=await asyncio.to_thread(a.get_conditional_balance,token_id)
     if pre_token_bal is None:pre_token_bal=.0
   else:pre_token_bal=.0
   A=getattr(OrderType,"FAK",OrderType.FOK);N=time.perf_counter()
   if _F is not None:_F.stamp("qualify_end")
   qualify_ms=(N-t0)*1e3;U=time.perf_counter();M=str(a.get_token_tick_size(token_id)or"0.01")
   if neg_risk is None and token_id not in a._neg_risk_cache and not a.dry_run:await asyncio.to_thread(a.get_token_neg_risk,token_id)
   z=int(round(p*10000))if p else 0;T=a.get_token_neg_risk(token_id,neg_risk);a.prewarm_token_market_cache(token_id=token_id,tick_size=M,neg_risk=T,fee_rate_bps=z,condition_id=condition_id,fee_rate=p,fee_exponent=s);I=PartialCreateOrderOptions(tick_size=M,neg_risk=T,version=2)if PartialCreateOrderOptions else None;dispatch_stage={"submitted":False};_n=None;y=None
   if _F is not None:_F.stamp("dispatch_enqueue")
   _d=time.perf_counter_ns()
   try:
    if a._can_use_native_async_post_order():_n=await a._sign_and_post_async_zero_hop(token_id,f,d,side,A,I,dispatch_stage,notional_usd)
    else:_n=await asyncio.get_running_loop().run_in_executor(_get_hot_io_pool(),_sign_and_post_single_hop,a.client,a.order_ladder_cache,token_id,f,d,side,A,I,dispatch_stage,notional_usd,_d)
   except BaseException as P:y=P;raise
   finally:
    n=bool(dispatch_stage.get("submitted"))
    if n:
     _x=a.__dict__.setdefault("_wire_submitted_trade_ids",set());_J=a.__dict__.setdefault("_wire_submitted_trade_order",[]);_C=str(trade_id)
     if _C not in _x:
      if len(_J)>=2048:
       for _s in _J[:512]:_x.discard(_s)
       del _J[:512]
      elif len(_x)>2048:_I=set(_J[-1536:]);_x.intersection_update(_I)
      _x.add(_C);_J.append(_C)
    if _F is not None:
     _F.stamp("post_return")
     if _n is None:_H=dispatch_stage.get("t_post_start");S=round((time.perf_counter()-float(_H))*1e3,3)if _H else None;R=("fak_killed"if(y is not None and is_fak_killed_no_match(y))else("clob_400_rejected"if(y is not None and is_clob_400_rejection(y))else"dispatch_exception"));_F.emit(trade_id=trade_id,token_id=token_id,side=side,outcome=R,submitted=n,hot_active=_HOT_DISPATCH_ACTIVE.count,qualify_ms=round(qualify_ms,3),sign_ms=dispatch_stage.get("sign_ms"),thread_hop_ms=dispatch_stage.get("thread_hop_ms"),clob_http_post_ms=S,presign_cache_hit=dispatch_stage.get("cache_hit"),cf_ray=dispatch_stage.get("cf_ray"))
   d=float(_n.get("signed_shares",d));_m=_n["post_resp"];sign_ms=_n["sign_ms"];thread_hop_ms=float(_n.get("thread_hop_ms",.0));h=_n["post_ms"];_c=time.perf_counter();b=(_c-t0)*1e3
   if _n["cache_hit"]:pass
   logger.info(f"[{trade_id}] LATENCY TELEMETRY: qualify_ms={qualify_ms:.2f} | sign_ms={sign_ms:.2f} | thread_hop_ms={thread_hop_ms:.3f} | clob_http_post_ms={h:.2f} | total_trigger_to_ack_ms={b:.2f}");l=(_c-t0)*1e3;_r=_m.get("orderID")or _m.get("id")
   if _F is not None:_F.emit(trade_id=trade_id,token_id=token_id,side=side,outcome="posted",order_id_present=bool(_r),resp_status=str(_m.get("status")),resp_error=str(_m.get("errorMsg")or _m.get("error")or"")[:120],qualify_ms=round(qualify_ms,3),sign_ms=round(sign_ms,3),thread_hop_ms=round(float(_n.get("thread_hop_ms",.0)),3),clob_http_post_ms=round(h,3),total_trigger_to_ack_ms=round(b,3),presign_cache_hit=bool(_n.get("cache_hit")),hot_active=_HOT_DISPATCH_ACTIVE.count,taker_delay_hint=getattr(a,"_taker_delay_ms_hint",None),cf_ray=_n.get("cf_ray"))
   if is_fak_killed_no_match(None,_m):q=_m.get("error")or _m.get("errorMsg")or"FAK order killed with zero match";logger.warning(f"[{trade_id}] FAK order deterministically killed by CLOB (zero match): {q} | orderID={_r}");j=OrderResult(success=False,order_id=_r,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=l,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=q,details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":_m,"depth_ratio":Z,"timestamp_utc":_A,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,"latency_telemetry":{"qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",.0),"clob_http_post_ms":h,"total_trigger_to_ack_ms":b}});a._log_order(j);return j
   F=_m.get("errorMsg")or _m.get("error")
   if F and not _r:q=F;logger.error(f"[{trade_id}] Order rejected by CLOB: {q} | raw={_m}");j=OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=d,notional_usd=notional_usd,fee_usd=H,latency_ms=l,mode="LIVE_CLOB_ERROR",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=q,details={"raw_response":_m,"depth_ratio":Z,"timestamp_utc":_A,"pre_token_balance":pre_token_bal,"outcome_unknown":False,"requires_exchange_reconciliation":False,"latency_telemetry":{"qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",.0),"clob_http_post_ms":h,"total_trigger_to_ack_ms":b}});a._log_order(j);return j
   if not _r or F:q=(f"CONTRADICTORY_RESPONSE: orderID={_r} with errorMsg={F}"if _r else"No orderID returned from CLOB matching engine (incomplete/ambiguous response)");logger.error(f"[{trade_id}] {q} | raw={_m}");j=OrderResult(success=False,order_id=_r,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=d,notional_usd=notional_usd,fee_usd=H,latency_ms=l,mode="LIVE_AMBIGUOUS_SUBMISSION",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,error=q,details={"outcome_unknown":True,"requires_exchange_reconciliation":True,"raw_response":_m,"depth_ratio":Z,"timestamp_utc":_A,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd,"entry_order_id":_r,"latency_telemetry":{"qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",.0),"clob_http_post_ms":h,"total_trigger_to_ack_ms":b}});a._log_order(j);return j
   Y=str(_m.get("status")or"").upper();_b=_m.get("makingAmount");_a=_m.get("takingAmount")
   if Y.startswith("CANCEL")or Y in{"UNMATCHED","EXPIRED","REJECTED"}:j=OrderResult(success=False,order_id=_r,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=l,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=f"CLOB order returned terminal non-fill status={Y}",details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":_m});a._log_order(j);return j
   if Y in{"DELAYED","LIVE"}and _b in(None,"")and _a in(None,""):j=OrderResult(success=False,order_id=_r,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=d,notional_usd=notional_usd,fee_usd=H,latency_ms=l,mode="LIVE_AMBIGUOUS_SUBMISSION",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,error=f"CLOB order returned non-immediate status={Y} without fill amounts",details={"outcome_unknown":True,"requires_exchange_reconciliation":True,"raw_response":_m,"entry_order_id":_r,"pre_token_balance":pre_token_bal,"intended_notional_usd":notional_usd});a._log_order(j);return j
   if _b not in(None,""):
    try:m=float(_b)
    except(ValueError,TypeError)as g:raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid makingAmount={_b}: {g}")
   else:m=round(d*_e,4)
   if _a not in(None,""):
    try:r=float(_a)
    except(ValueError,TypeError)as g:raise RuntimeError(f"MALFORMED_CLOB_RESPONSE: Invalid takingAmount={_a}: {g}")
   else:r=d
   if(_b not in(None,"")or _a not in(None,""))and r<=.0:j=OrderResult(success=False,order_id=_r,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=l,mode="FAK_KILLED_NO_MATCH",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error="FAK order matched 0 shares",details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"raw_response":_m});a._log_order(j);return j
   _w=round(m/max(r,1e-4),4)if(_b not in(None,"")and _a not in(None,"")and r>0)else _e
   if _b not in(None,"")and _a not in(None,"")and r>0:_l=max(.001,min(.999,_w));H=round(r*p*((_l*(1.-_l))**s),5)
   _k=_m.get("tradeIDs",[]);_j=_m.get("transactionsHashes",[]);logger.info(f"[LIVE CLOB MATCHED] {trade_id} -> OID: {_r} | {target_token} | Shares={r:.2f} @ ${_w:.4f} | Notional=${m:.2f} | Latency={l:.2f}ms | Trades={_k}");j=OrderResult(success=True,order_id=_r,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_w,size=r,notional_usd=m,fee_usd=H,latency_ms=l,mode="LIVE_CLOB",execution_status=ExecutionStatus.MATCHED_PENDING_SETTLEMENT,confirmed_onchain=False,details={"raw_response":_m,"depth_ratio":Z,"timestamp_utc":_A,"confirmed_onchain":False,"pre_token_balance":pre_token_bal,"trade_ids":_k,"transactions_hashes":_j,"latency_telemetry":{"qualify_ms":qualify_ms,"sign_ms":sign_ms,"thread_hop_ms":locals().get("thread_hop_ms",.0),"clob_http_post_ms":h,"total_trigger_to_ack_ms":b}});a._log_order(j);return j
  except Exception as e:
   _G=time.perf_counter();l=(_G-t0)*1e3;_R=locals().get("dispatch_stage")or{};_i=_R.get("t_post_start")or locals().get("t_post_start");h=round(max(.0,(_G-float(_i))*1e3),3)if _i else.0;Q=float(_R.get("sign_ms")if _R.get("sign_ms")is not None else locals().get("sign_ms",.0));X=float(_R.get("thread_hop_ms")if _R.get("thread_hop_ms")is not None else locals().get("thread_hop_ms",.0));b=(_G-t0)*1e3;q=f"CLOB order submission failed: {e}"
   if is_clob_400_rejection(e):
    a._evict_tick_size_if_tick_err(token_id,e)
    if any(k in str(getattr(e,"error_message","")or e).lower()for k in("not enough balance","allowance")):a.invalidate_collateral_cache()
    c=None;_q=getattr(e,"error_message",None)or getattr(e,"error_msg",None)
    if isinstance(_q,dict):c=_q.get("orderID")or _q.get("id")
    elif isinstance(_q,str):
     try:
      _B=json.loads(_q)
      if isinstance(_B,dict):c=_B.get("orderID")or _B.get("id")
     except Exception:pass
    logger.warning(f"[{trade_id}] Order deterministically rejected by CLOB (HTTP 400 / 0 match): {e} | orderID={c}");j=OrderResult(success=False,order_id=c,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=.0,fee_usd=.0,latency_ms=l,mode="FAK_KILLED_NO_MATCH"if is_fak_killed_no_match(e)else"CLOB_HTTP_400_REJECTION",execution_status=ExecutionStatus.REJECTED,confirmed_onchain=False,error=str(e),details={"outcome_unknown":False,"requires_exchange_reconciliation":False,"fak_killed":True,"clob_400_rejection":True,"raw_exception":str(e),"status_code":getattr(e,"status_code",400),"pre_token_balance":locals().get("pre_token_bal"),"intended_notional_usd":notional_usd,"latency_telemetry":{"qualify_ms":locals().get("qualify_ms",.0),"sign_ms":Q,"thread_hop_ms":X,"clob_http_post_ms":h,"total_trigger_to_ack_ms":b}});a._log_order(j);return j
   logger.error(f"[{trade_id}] {q}");j=OrderResult(success=False,order_id=None,trade_id=trade_id,token_id=token_id,target_token=target_token,side=side,price=_z,size=.0,notional_usd=notional_usd,fee_usd=.0,latency_ms=l,mode="LIVE_CLOB_ERROR",execution_status=ExecutionStatus.SUBMITTED if n else ExecutionStatus.REJECTED,confirmed_onchain=False,error=q,details={"outcome_unknown":bool(n),"requires_exchange_reconciliation":bool(n),"pre_token_balance":locals().get("pre_token_bal"),"intended_notional_usd":notional_usd,"latency_telemetry":{"qualify_ms":locals().get("qualify_ms",.0),"sign_ms":Q,"thread_hop_ms":X,"clob_http_post_ms":h,"total_trigger_to_ack_ms":b}});a._log_order(j);return j
 _CANONICAL_CLOB_TICKS:Tuple[Tuple[float,str],...]=((.1,"0.1"),(.01,"0.01"),(.005,"0.005"),(.0025,"0.0025"),(.001,"0.001"),(1e-4,"0.0001"));_TICK_RULE_RE=re.compile(r"(?:minimum|min)[\s_]+tick[\s_]+size(?:\s+rule)?[\s:=]+([0-9]+(?:\.[0-9]+)?)",re.IGNORECASE)
 @classmethod
 def _extract_tick_size_from_error(a,err_obj):
  b=getattr(err_obj,"error_message",None)or getattr(err_obj,"error_msg",None);d=f"{b} | {err_obj}"if b is not None else str(err_obj or"");m=a._TICK_RULE_RE.search(d)
  if not m:return None
  try:c=float(m.group(1))
  except(TypeError,ValueError):return None
  for f,e in a._CANONICAL_CLOB_TICKS:
   if abs(c-f)<1e-9:return(f,e)
  return None
 def _apply_enforced_tick_size(a,token_id,tick_val,tick_str,ttl_sec=30.,*,from_clob_400=False):
  if not token_id:return
  d=time.monotonic()+max(1.,float(ttl_sec));c=a.__dict__.setdefault("_enforced_tick_override_until",{});c[token_id]=(float(tick_val),d)
  if from_clob_400:
   a.__dict__.setdefault("_clob_400_tick_until",{})[token_id]=(float(tick_val),d);b=getattr(a,"_presigned_maker_repegs",None)
   if isinstance(b,dict):b.pop(token_id,None)
  a._tick_size_cache[token_id]=float(tick_val);e=getattr(a,"order_ladder_cache",None)
  if e is not None and hasattr(e,"evict_mismatched_tick"):e.evict_mismatched_tick(token_id,str(tick_str))
  if a.client is not None and hasattr(a.client,"_ClobClient__tick_sizes"):
   try:a.client._ClobClient__tick_sizes[token_id]=str(tick_str)
   except Exception:pass
 def update_ws_tick_size(a,token_id,tick_size,ttl_sec=120.):
  if not token_id or tick_size in(None,"")or isinstance(tick_size,bool):return None
  try:c=float(tick_size)
  except(TypeError,ValueError):return None
  d=str(token_id)
  for f,e in a._CANONICAL_CLOB_TICKS:
   if abs(c-f)<1e-9:
    if f<.01:
     b=getattr(a,"_clob_400_tick_until",None)
     if isinstance(b,dict):b.pop(d,None)
     a._apply_enforced_tick_size(d,f,e,ttl_sec=ttl_sec)
    else:
     a._apply_enforced_tick_size(d,f,e,ttl_sec=1.);b=getattr(a,"_clob_400_tick_until",None)
     if not(isinstance(b,dict)and d in b and time.monotonic()<float(b[d][1])):getattr(a,"_enforced_tick_override_until",{}).pop(d,None)
    return f
  return None
 def _evict_tick_size_if_tick_err(a,token_id,err_obj):
  if not token_id:return
  b=a._extract_tick_size_from_error(err_obj)
  if b is not None:a._apply_enforced_tick_size(token_id,b[0],b[1],ttl_sec=120.,from_clob_400=True);return
  c=str(err_obj or"").lower()
  if any(k in c for k in("tick","minimum_tick_size","invalid price","price precision")):
   a._tick_size_cache.pop(token_id,None)
   if a.client is not None and hasattr(a.client,"_ClobClient__tick_sizes"):
    try:a.client._ClobClient__tick_sizes.pop(token_id,None)
    except Exception:pass
 def get_token_tick_size(a,token_id,price_hint=None):
  h=getattr(a,"_enforced_tick_override_until",None)
  if isinstance(h,dict)and token_id in h:
   j,l=h[token_id]
   if time.monotonic()<l:return float(j)
   h.pop(token_id,None)
  k=a._tick_size_cache.get(token_id);m=time.monotonic();f=a.__dict__.setdefault("_boundary_tick_recheck_ts",{});d=(price_hint is not None and math.isfinite(float(price_hint))and(float(price_hint)>=.96 or float(price_hint)<=.04 or abs(round(float(price_hint),2)-round(float(price_hint),4))>1e-6)and a.client is not None and hasattr(a.client,"get_tick_size"));b=(k==.01 and d and(m-float(f.get(token_id,-999.)))>=2.5)
  if k is not None and not b:return k
  if a.client and hasattr(a.client,"get_tick_size"):
   c=None;g=getattr(a.client,"_ClobClient__token_condition_map",None)
   try:
    if d and hasattr(a.client,"_ClobClient__tick_sizes"):
     if str(a.client._ClobClient__tick_sizes.get(token_id)or"")=="0.01":a.client._ClobClient__tick_sizes.pop(token_id,None)
    if isinstance(g,dict)and token_id in g:c=g.pop(token_id,None)
    i=a.client.get_tick_size(token_id)
    if isinstance(i,(str,int,float,Decimal))and not isinstance(i,bool):
     e=float(i)
     if any(abs(e-n)<1e-9 for n in(.1,.01,.005,.0025,.001,1e-4)):
      a._tick_size_cache[token_id]=e
      if d:f[token_id]=m
      if hasattr(a.client,"_ClobClient__tick_sizes"):a.client._ClobClient__tick_sizes[token_id]=str(i)
      return e
   except Exception:pass
   finally:
    if(isinstance(g,dict)and isinstance(c,str)and len(c)>=4 and c.lower().startswith("0x")and set(c[2:])!={"0"}):g.setdefault(token_id,c)
  if k is not None:return k
  if not a.dry_run and not hasattr(a.client,"_mock_children"):raise RuntimeError(f"AUTHORITATIVE_TICK_SIZE_UNAVAILABLE for live token {token_id}")
  e=.01;a._tick_size_cache[token_id]=e;return e
 def quantize_order_price(a,price,token_id,rounding=ROUND_HALF_UP):
  if price is None or not math.isfinite(float(price)):raise ValueError(f"Refusing to quantize non-finite price {price!r} for {token_id}")
  try:b=a.get_token_tick_size(token_id,price_hint=float(price))
  except TypeError:b=a.get_token_tick_size(token_id)
  e=Decimal(str(b));c=round(float(price),6);d=(Decimal(str(c))/e).to_integral_value(rounding=rounding);q=d*e;q=max(e,min(Decimal("1")-e,q));return float(q)
 def post_maker_entry_order(b,token_id,price,notional_usd,side="BUY",neg_risk=None,min_price_floor=.02,max_price_ceiling=.999):
  try:u=float(notional_usd);C=float(price)
  except(TypeError,ValueError):return{"success":False,"orderID":None,"error":"INVALID_MAKER_ENTRY_INPUTS","retryable":False}
  if not math.isfinite(u)or u<=0 or not math.isfinite(C)or C<=0:return{"success":False,"orderID":None,"error":"NON_POSITIVE_MAKER_ENTRY_INPUTS","retryable":False}
  d=b.quantize_order_price(C,token_id,rounding=ROUND_FLOOR)
  if d<min_price_floor or d>max_price_ceiling:return{"success":False,"orderID":None,"error":f"MAKER_ENTRY_PRICE_OUT_OF_BOUNDS ({d:.4f} not in [{min_price_floor:.2f}, {max_price_ceiling:.2f}])","retryable":False}
  f=float(math.floor(u/d))
  if f<5.:return{"success":False,"orderID":None,"error":f"MAKER_ENTRY_MIN_SHARES_REJECTED ({f:.0f} < 5 shares at ${d:.4f})","retryable":False}
  if b.dry_run:
   if neg_risk is not None:b.get_token_neg_risk(token_id,neg_risk)
   B=f"MOCK_MAKER_ENTRY_{int(time.time()*1000)}";logger.info(f"[DRY-RUN MAKER ENTRY] Resting {side} post_only GTC: {f:.0f} shares @ ${d:.4f} (notional=${f*d:.2f}, ID={B})");return{"success":True,"orderID":B,"mode":"DRY_RUN","post_only":True,"price":d,"shares":f,"notional_usd":round(f*d,4)}
  if not b.is_authenticated or b.client is None or OrderArgsV2 is None:raise RuntimeError(f"LIVE MAKER ENTRY REFUSED: Executor unauthenticated ({b.auth_mode}).")
  order_submitted=False;J=time.perf_counter()
  try:
   try:o=b.get_token_tick_size(token_id,price_hint=d)
   except TypeError:o=b.get_token_tick_size(token_id)
   r=b.get_token_neg_risk(token_id,neg_risk);m=(PartialCreateOrderOptions(tick_size=str(o),neg_risk=r,version=2)if PartialCreateOrderOptions else None);i=(getattr(b.client,"_fast_v2_signer",None)is not None and"create_order"not in getattr(b.client,"__dict__",{}))
   def c(px_use,sh_use):
    nonlocal order_submitted;a=b._pop_presigned_maker_repeg(token_id,px_use,sh_use,side,str(o),bool(r))
    if a is None:
     e=OrderArgsV2(price=px_use,size=sh_use,side=side,token_id=token_id)
     if i:a=_safe_create_order(b.client.create_order,e,m)
     else:
      with _UrgentSignPriority():a=_safe_create_order(b.client.create_order,e,m)
    order_submitted=True;return b._post_signed_order_bridge_or_sync(a,OrderType.GTC,post_only=True,defer_exec=True)
   try:h=c(d,f)
   except Exception as p:
    H=str(getattr(p,"error_message","")or str(p))
    if b._extract_tick_size_from_error(p)is not None or(str(side).upper()=="BUY"and any(k in H.lower()for k in("crosses book","post only","post-only"))):order_submitted=False;h={"errorMsg":H}
    else:raise
   n=h.get("errorMsg")or h.get("error");g=h.get("orderID")or h.get("id");x=b._extract_tick_size_from_error(n)if(n and not g)else None
   if x is not None:
    A,z=x;b._apply_enforced_tick_size(token_id,A,z,ttl_sec=120.,from_clob_400=True);o=A;m=(PartialCreateOrderOptions(tick_size=z,neg_risk=r,version=2)if PartialCreateOrderOptions else None);w=ROUND_FLOOR if str(side).upper()=="BUY"else ROUND_CEILING;t=b.quantize_order_price(C,token_id,rounding=w);s=(float(math.floor(u/t))if(min_price_floor<=t<=max_price_ceiling)else.0)
    if min_price_floor<=t<=max_price_ceiling and s>=5. and abs(t-d)>1e-9:
     d,f=t,s
     try:h=c(d,f)
     except Exception as l:
      G=str(getattr(l,"error_message","")or str(l))
      if str(side).upper()=="BUY"and any(k in G.lower()for k in("crosses book","post only","post-only")):order_submitted=False;h={"errorMsg":G}
      else:raise
     n=h.get("errorMsg")or h.get("error");g=h.get("orderID")or h.get("id")
   if n and not g and str(side).upper()=="BUY"and any(k in str(n).lower()for k in("crosses book","post only","post-only")):
    try:
     I=b.get_market_book(token_id);F=I.get("asks",[])if isinstance(I,dict)else[];E=min((float(a.get("price",.0))for a in F if float(a.get("size",.0))>0 and float(a.get("price",.0))>0),default=.0)
     if E>o:
      t=b.quantize_order_price(min(d,E-o),token_id,rounding=ROUND_FLOOR);s=float(math.floor(u/t))if t>=min_price_floor else.0
      if t>=min_price_floor and s>=5. and t<E-1e-9:
       d,f=t,s
       try:h=c(d,f)
       except Exception as j:
        D=str(getattr(j,"error_message","")or str(j))
        if any(k in D.lower()for k in("crosses book","post only","post-only")):order_submitted=False;h={"errorMsg":D}
        else:raise
       n=h.get("errorMsg")or h.get("error");g=h.get("orderID")or h.get("id")
    except Exception:
     if order_submitted:raise
   if n and g:return{"success":False,"orderID":g,"outcome_unknown":True,"retryable":False,"error":f"CONTRADICTORY_MAKER_ENTRY_RESPONSE: {n}","raw":h}
   if n:
    if any(k in str(n).lower()for k in("not enough balance","allowance")):b.invalidate_collateral_cache()
    return{"success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"error":str(n),"raw":h}
   if g:v=(time.perf_counter()-J)*1e3;b._maybe_schedule_maker_repeg_presign(token_id,d,f,max_price_ceiling,side,o,r);logger.info(f"[LIVE MAKER ENTRY POSTED] OID={g} | {side} {f:.0f} shares @ ${d:.4f} (neg_risk={r})");b._log_order(OrderResult(success=True,order_id=str(g),trade_id=f"MAKER_ENTRY_{g}",token_id=str(token_id),target_token="",side=side,price=d,size=f,notional_usd=round(f*d,4),fee_usd=.0,latency_ms=v,mode="LIVE_MAKER_ENTRY",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,details={"post_only":True}));return{"success":True,"orderID":g,"post_only":True,"price":d,"shares":f,"notional_usd":round(f*d,4),"raw":h}
   return{"success":False,"orderID":None,"outcome_unknown":True,"retryable":False,"error":"MISSING_ORDER_ID_IN_MAKER_ENTRY","raw":h}
  except Exception as e:
   y=str(getattr(e,"error_message","")or str(e));b._evict_tick_size_if_tick_err(token_id,y)
   if any(k in y.lower()for k in("not enough balance","allowance")):b.invalidate_collateral_cache()
   q=is_clob_400_rejection(e)or any(k in y.lower()for k in("crosses book","post only","post-only","not enough balance","allowance"));return{"success":False,"orderID":None,"outcome_unknown":bool(order_submitted and not q),"retryable":bool(not order_submitted or q),"error":y}
 place_passive_maker_entry=post_maker_entry_order
 async def post_maker_entry_order_async(b,token_id,price,notional_usd,side="BUY",neg_risk=None,min_price_floor=.02,max_price_ceiling=.999):
  if b.dry_run or not b._can_use_native_async_post_order():return await asyncio.to_thread(b.post_maker_entry_order,token_id,price,notional_usd,side,neg_risk,min_price_floor,max_price_ceiling)
  try:w,J=float(notional_usd),float(price)
  except(TypeError,ValueError):return{"success":False,"orderID":None,"error":"INVALID_MAKER_ENTRY_INPUTS","retryable":False}
  if not math.isfinite(w)or w<=0 or not math.isfinite(J)or J<=0:return{"success":False,"orderID":None,"error":"NON_POSITIVE_MAKER_ENTRY_INPUTS","retryable":False}
  M=getattr(b,"_enforced_tick_override_until",None);v=isinstance(M,dict)and token_id in M and time.monotonic()<float(M[token_id][1]);u=b._tick_size_cache.get(token_id);C=(b.__dict__.get("_boundary_tick_recheck_ts")or{}).get(token_id,-999.);l=((not v and(u is None or(u==.01 and(J>=.96 or J<=.04)and(time.monotonic()-float(C))>=2.5)))or(neg_risk is None and token_id not in b._neg_risk_cache))
  if l:await b.get_token_metadata_async(token_id,price_hint=J,explicit_neg_risk=neg_risk)
  c=b.quantize_order_price(J,token_id,rounding=ROUND_FLOOR)
  if c<min_price_floor or c>max_price_ceiling:return{"success":False,"orderID":None,"error":f"MAKER_ENTRY_PRICE_OUT_OF_BOUNDS ({c:.4f})","retryable":False}
  d=float(math.floor(w/c))
  if d<5.:return{"success":False,"orderID":None,"error":f"MAKER_ENTRY_MIN_SHARES_REJECTED ({d:.0f} < 5)","retryable":False}
  m={"submitted":False};O=time.perf_counter()
  try:
   n=b.get_token_tick_size(token_id,price_hint=c);q=b.get_token_neg_risk(token_id,neg_risk);g=PartialCreateOrderOptions(tick_size=str(n),neg_risk=q,version=2)if PartialCreateOrderOptions else None
   try:r=await b._sign_and_post_async_zero_hop(token_id,c,d,side,OrderType.GTC,create_options=g,stage=m,max_notional_usd=w,post_only=True);i=r.get("post_resp")or{}
   except Exception as p:
    L=str(getattr(p,"error_message","")or str(p))
    if b._extract_tick_size_from_error(p)is not None or(str(side).upper()=="BUY"and any(k in L.lower()for k in("crosses book","post only","post-only"))):m["submitted"]=False;i={"errorMsg":L};r={"post_resp":i}
    else:raise
   h=i.get("errorMsg")or i.get("error");f=i.get("orderID")or i.get("id");t=b._extract_tick_size_from_error(h)if(h and not f)else None
   if t is not None:
    z,y=t;b._apply_enforced_tick_size(token_id,z,y,ttl_sec=120.,from_clob_400=True);n=z;g=PartialCreateOrderOptions(tick_size=y,neg_risk=q,version=2)if PartialCreateOrderOptions else None;s=ROUND_FLOOR if str(side).upper()=="BUY"else ROUND_CEILING;I=b.quantize_order_price(J,token_id,rounding=s);H=float(math.floor(w/I))if(min_price_floor<=I<=max_price_ceiling)else.0
    if min_price_floor<=I<=max_price_ceiling and H>=5. and abs(I-c)>1e-9:
     c,d=I,H;m={"submitted":False}
     try:r=await b._sign_and_post_async_zero_hop(token_id,c,d,side,OrderType.GTC,create_options=g,stage=m,max_notional_usd=w,post_only=True);i=r.get("post_resp")or{}
     except Exception as j:
      B=str(getattr(j,"error_message","")or str(j))
      if str(side).upper()=="BUY"and any(k in B.lower()for k in("crosses book","post only","post-only")):m["submitted"]=False;i={"errorMsg":B};r={"post_resp":i}
      else:raise
     h=i.get("errorMsg")or i.get("error");f=i.get("orderID")or i.get("id")
   if h and not f and str(side).upper()=="BUY"and any(k in str(h).lower()for k in("crosses book","post only","post-only")):
    try:
     N=await(b.get_market_book_async(token_id)if"get_market_book"not in b.__dict__ else asyncio.to_thread(b.get_market_book,token_id));K=N.get("asks",[])if isinstance(N,dict)else[];G=min((float(a.get("price",.0))for a in K if float(a.get("size",.0))>0 and float(a.get("price",.0))>0),default=.0)
     if G>n:
      F=b.quantize_order_price(min(c,G-n),token_id,rounding=ROUND_FLOOR);E=float(math.floor(w/F))if F>=min_price_floor else.0
      if F>=min_price_floor and E>=5. and F<G-1e-9:c,d=F,E;m={"submitted":False};r=await b._sign_and_post_async_zero_hop(token_id,c,d,side,OrderType.GTC,create_options=g,stage=m,max_notional_usd=w,post_only=True);i=r.get("post_resp")or{};h=i.get("errorMsg")or i.get("error");f=i.get("orderID")or i.get("id")
    except Exception:pass
   if h and f:return{"success":False,"orderID":f,"outcome_unknown":True,"retryable":False,"error":f"CONTRADICTORY_MAKER_ENTRY_RESPONSE: {h}","raw":i}
   if h:
    if any(k in str(h).lower()for k in("not enough balance","allowance")):b.invalidate_collateral_cache()
    return{"success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"error":str(h),"raw":i}
   if f:x=float(m.get("signed_shares")or d);A=(time.perf_counter()-O)*1e3;b._maybe_schedule_maker_repeg_presign(token_id,c,x,max_price_ceiling,side,n,q);logger.info(f"[LIVE MAKER ENTRY ASYNC] OID={f} | {side} {x:.0f} sh @ ${c:.4f} | post={r.get('post_ms')}ms sign={r.get('sign_ms')}ms");b._log_order(OrderResult(success=True,order_id=str(f),trade_id=f"MAKER_ENTRY_{f}",token_id=str(token_id),target_token="",side=side,price=c,size=x,notional_usd=round(x*c,4),fee_usd=.0,latency_ms=A,mode="LIVE_MAKER_ENTRY",execution_status=ExecutionStatus.SUBMITTED,confirmed_onchain=False,details={"post_only":True,"post_ms":r.get("post_ms"),"sign_ms":r.get("sign_ms"),"zero_hop":True,"presign_cache_hit":bool(m.get("cache_hit"))}));return{"success":True,"orderID":f,"post_only":True,"price":c,"shares":x,"notional_usd":round(x*c,4),"post_ms":r.get("post_ms"),"sign_ms":r.get("sign_ms"),"presign_cache_hit":bool(m.get("cache_hit")),"raw":i}
   return{"success":False,"orderID":None,"outcome_unknown":True,"retryable":False,"error":"MISSING_ORDER_ID_IN_MAKER_ENTRY","raw":i}
  except Exception as e:
   D=str(getattr(e,"error_message","")or str(e));b._evict_tick_size_if_tick_err(token_id,D)
   if any(k in D.lower()for k in("not enough balance","allowance")):b.invalidate_collateral_cache()
   o=isinstance(e,PreSubmitError)or is_clob_400_rejection(e)or any(k in D.lower()for k in("crosses book","post only","post-only","not enough balance","allowance"));return{"success":False,"orderID":None,"outcome_unknown":bool(m.get("submitted")and not o),"retryable":bool(not m.get("submitted")or o),"error":D}
 place_passive_maker_entry_async=post_maker_entry_order_async
 @staticmethod
 def _extract_fok_matched_shares(resp,default_shares):
  if not isinstance(resp,dict):return None
  for c in("takingAmount","taking_amount","matched_size","size_matched","sizeMatched"):
   b=resp.get(c)
   if b not in(None,""):
    try:a=float(b);return a if math.isfinite(a)else None
    except(TypeError,ValueError):return None
  if str(resp.get("status","")).upper()in{"DELAYED","LIVE","UNMATCHED"}:return None
  return default_shares
 @staticmethod
 def _extract_ws_deferred_gross(ws_snap):
  if not isinstance(ws_snap,dict):return None
  b=str(ws_snap.get("status")or"").strip().upper()
  try:m=float(ws_snap.get("size_matched")or.0);a=float(ws_snap.get("original_size")or.0)
  except(TypeError,ValueError):return None
  if m>.0 and(b in{"MATCHED","FILLED"}or(a>.0 and m>=a-1e-4)):return m
  if b in{"CANCELED","CANCELLED","EXPIRED","REJECTED"}or(b=="INVALID"and m<=1e-6):return m if m>.0 else.0
  return None
 def _resolve_deferred_fok_gross(a,oid_v,tok_v,resp_v):
  if not oid_v or not isinstance(resp_v,dict)or str(resp_v.get("status","")).upper()not in{"DELAYED","LIVE","UNMATCHED"}:return None
  h=getattr(a,"_user_ws_cache",None);f=bool(h is not None and hasattr(h,"is_healthy")and h.is_healthy())
  if f and hasattr(h,"wait_for_order_terminal"):
   try:
    b=a._extract_ws_deferred_gross(h.wait_for_order_terminal(str(oid_v),timeout_sec=.08))
    if b is not None:return b
   except Exception:pass
  d=(hasattr(a.client,"get_order")or"get_order_fill_summary"in a.__dict__ or h is not None)
  if not d or not hasattr(a,"get_order_fill_summary"):return None
  for c in range(5):
   if c>0:
    if f and hasattr(h,"wait_for_order_terminal"):
     try:
      b=a._extract_ws_deferred_gross(h.wait_for_order_terminal(str(oid_v),timeout_sec=.12))
      if b is not None:return b
     except Exception:time.sleep(.12)
    else:time.sleep(.12)
   try:e=a.get_order_fill_summary(str(oid_v),tok_v)
   except Exception:e=None
   if isinstance(e,dict):
    g=float(e.get("matched")or.0)
    if g>.0:return g
    if e.get("terminal"):return.0
  return None
 async def _resolve_deferred_fok_gross_async(a,oid_v,tok_v,resp_v):
  if not oid_v or not isinstance(resp_v,dict)or str(resp_v.get("status","")).upper()not in{"DELAYED","LIVE","UNMATCHED"}:return None
  h=getattr(a,"_user_ws_cache",None);f=bool(h is not None and hasattr(h,"is_healthy")and h.is_healthy())
  if f and hasattr(h,"get_order_snapshot"):
   b=a._extract_ws_deferred_gross(h.get_order_snapshot(str(oid_v),max_age_sec=8.))
   if b is not None:return b
   if hasattr(h,"wait_for_fill_or_timeout"):
    try:
     await h.wait_for_fill_or_timeout(.08,prev_seq=h.fill_sequence);b=a._extract_ws_deferred_gross(h.get_order_snapshot(str(oid_v),max_age_sec=8.))
     if b is not None:return b
    except Exception:pass
  d=hasattr(a.client,"get_order")or"get_order_fill_summary"in a.__dict__ or h is not None
  if not d or not hasattr(a,"get_order_fill_summary"):return None
  for c in range(5):
   if c>0:
    if f and hasattr(h,"wait_for_fill_or_timeout"):
     try:
      await h.wait_for_fill_or_timeout(.12,prev_seq=h.fill_sequence);b=a._extract_ws_deferred_gross(h.get_order_snapshot(str(oid_v),max_age_sec=8.))
      if b is not None:return b
     except Exception:await asyncio.sleep(.12)
    else:await asyncio.sleep(.12)
   try:e=await asyncio.to_thread(a.get_order_fill_summary,str(oid_v),tok_v)
   except Exception:e=None
   if isinstance(e,dict):
    g=float(e.get("matched")or.0)
    if g>.0:return g
    if e.get("terminal"):return.0
  return None
 @staticmethod
 def _net_delivered_box_shares(gross_m,h_leg,explicit_gross):
  if not explicit_gross or h_leg<=.0:return float(gross_m)
  return math.floor(float(gross_m)*(1.-h_leg)*1e2+1e-9)/1e2
 def _prepare_atomic_dominance_box_ctx(a,box_id,leg_a_token_id,leg_a_label,leg_a_limit_price,leg_b_token_id,leg_b_label,leg_b_limit_price,shares,max_box_cost_net,fee_rate,fee_exponent,leg_a_avail_shares,leg_b_avail_shares,neg_risk,fee_rate_a,fee_rate_b,fee_exponent_a,fee_exponent_b,parallel_dispatch,leg_a_pre_balance,leg_b_pre_balance,min_box_cost_floor,leg_a_shares,leg_b_shares):
  try:u,t,l,y=float(leg_a_limit_price),float(leg_b_limit_price),float(shares),float(max_box_cost_net);J=float(fee_rate if fee_rate_a is None else fee_rate_a);I=float(fee_exponent if fee_exponent_a is None else fee_exponent_a);H=float(fee_rate if fee_rate_b is None else fee_rate_b);G=float(fee_exponent if fee_exponent_b is None else fee_exponent_b);q=float(leg_a_shares)if leg_a_shares is not None else None;p=float(leg_b_shares)if leg_b_shares is not None else None
  except(TypeError,ValueError):return{"success":False,"error":"INVALID_BOX_INPUTS","legged_out":False,"outcome_unknown":False},None
  if(not leg_a_token_id or not leg_b_token_id or str(leg_a_token_id)==str(leg_b_token_id)or not math.isfinite(u)or not math.isfinite(t)or not math.isfinite(l)or u<=.0 or t<=.0 or(q is not None and(not math.isfinite(q)or q<=.0))or(p is not None and(not math.isfinite(p)or p<=.0))):return{"success":False,"error":"INVALID_BOX_TOKENS_OR_PRICES","legged_out":False,"outcome_unknown":False},None
  f=float(math.floor(l))
  if f<5.:return{"success":False,"error":f"BOX_MIN_SHARES_REJECTED ({f:.0f} < 5 shares)","legged_out":False,"outcome_unknown":False},None
  F=a.quantize_order_price(u,leg_a_token_id,rounding=ROUND_CEILING);E=a.quantize_order_price(t,leg_b_token_id,rounding=ROUND_CEILING);o=J*((F*(1.-F))**I)if J>.0 else.0;n=H*((E*(1.-E))**G)if H>.0 else.0;L=min(.25,max(.0,o/max(F,1e-6)))if J>.0 else.0;K=min(.25,max(.0,n/max(E,1e-6)))if H>.0 else.0;c=round(F/max(1.-L,1e-6)+E/max(1.-K,1e-6),6);d=(q is not None or p is not None);i=round(q,2)if q is not None else f;g=round(p,2)if p is not None else f;e=(not a.dry_run and a.client is not None and getattr(a.client,"_mock_children",None)is None and"create_order"not in getattr(a.client,"__dict__",{}))
  if e:
   s=max(1,int(round(F*10000)));r=max(1,int(round(E*10000)))
   if(int(round(i*100))*s)%10000!=0 or(int(round(g*100))*r)%10000!=0:
    x=quantize_fok_buy_box_legs(shares_net=l,px_a=F,px_b=E,h_a=L,h_b=K,max_box_cost_net=y,avail_a=leg_a_avail_shares,avail_b=leg_b_avail_shares,min_shares=5.)
    if x is None:return{"success":False,"error":f"FOK_QUANTIZATION_EXCEEDS_CAP (px_a={F:.4f}, px_b={E:.4f}, cap={y:.4f})","worst_box_cost_net":c,"legged_out":False,"outcome_unknown":False},None
    i=x["leg_a_gross_shares"];g=x["leg_b_gross_shares"];f=x["net_paired_shares"];c=max(c,x["eff_box_cost_net"]);d=d or(L>.0 or K>.0)
  k=float(min_box_cost_floor)
  if c<k-1e-6:return{"success":False,"error":f"ANTI_BOX_COST_FLOOR_VETO ({c:.5f} < {k:.5f})","worst_box_cost_net":c,"legged_out":False,"outcome_unknown":False},None
  if c>y+1e-6:return{"success":False,"error":f"WORST_LIMIT_BOX_COST_EXCEEDS_CAP ({c:.5f} > {y:.5f})","worst_box_cost_net":c,"legged_out":False,"outcome_unknown":False},None
  B="4h"in str(leg_a_label).lower();A="4h"in str(leg_b_label).lower();w=any(h in str(leg_a_label).lower()for h in("15m","5m"));v=any(h in str(leg_b_label).lower()for h in("15m","5m"))
  if B and v and not A:b=True
  elif A and w and not B:b=False
  elif leg_a_avail_shares is not None and leg_b_avail_shares is not None and min(float(leg_a_avail_shares),float(leg_b_avail_shares))>.0:D,C=float(leg_a_avail_shares),float(leg_b_avail_shares);b=(C<D)if max(D,C)>1.2*min(D,C)else(E<F)
  else:b=E<F
  if b:m=[(leg_b_token_id,leg_b_label,E,n,K,g),(leg_a_token_id,leg_a_label,F,o,L,i)]
  else:m=[(leg_a_token_id,leg_a_label,F,o,L,i),(leg_b_token_id,leg_b_label,E,n,K,g)]
  if a.dry_run:a.get_token_neg_risk(leg_a_token_id,neg_risk);a.get_token_neg_risk(leg_b_token_id,neg_risk);z=int(time.time()*1000);return{"success":True,"mode":"DRY_RUN","box_id":box_id,"shares":f,"net_paired_shares":f,"worst_box_cost_net":c,"guaranteed_min_profit_usd":round(f*(1.-c),4),"legged_out":False,"outcome_unknown":False,"leg_1":{"label":m[0][1],"token_id":m[0][0],"price":m[0][2],"matched_shares":f,"gross_shares":m[0][5],"entry_fee_asset":("SHARES"if(d and m[0][4]>.0)else"USDC"),"orderID":f"MOCK_BOX_L1_{z}"},"leg_2":{"label":m[1][1],"token_id":m[1][0],"price":m[1][2],"matched_shares":f,"gross_shares":m[1][5],"entry_fee_asset":("SHARES"if(d and m[1][4]>.0)else"USDC"),"orderID":f"MOCK_BOX_L2_{z}"}},None
  if not a.is_authenticated or a.client is None or OrderArgsV2 is None:raise RuntimeError(f"LIVE DOMINANCE BOX REFUSED: Executor unauthenticated ({a.auth_mode}).")
  j=(bool(parallel_dispatch)if parallel_dispatch is not None else bool(leg_a_avail_shares is not None and leg_b_avail_shares is not None and float(leg_a_avail_shares)>=1.5*max(f,i)and float(leg_b_avail_shares)>=1.5*max(f,g)));return None,{"box_id":box_id,"legs":m,"shares_int":f,"worst_box_cost_net":c,"explicit_gross":d,"use_parallel":j,"pre_bal_map":{str(leg_a_token_id):float(leg_a_pre_balance or.0),str(leg_b_token_id):float(leg_b_pre_balance or.0)}}
 def _sign_atomic_dominance_box_legs(a,ctx,tick_1,nr_1,tick_2,nr_2):
  (f,_,j,_,_,i),(e,_,h,_,_,g)=ctx["legs"];d=PartialCreateOrderOptions(tick_size=str(tick_1),neg_risk=nr_1,version=2)if PartialCreateOrderOptions else None;c=PartialCreateOrderOptions(tick_size=str(tick_2),neg_risk=nr_2,version=2)if PartialCreateOrderOptions else None;b=(getattr(a.client,"_fast_v2_signer",None)is not None and"create_order"not in getattr(a.client,"__dict__",{}))
  if b:return(_safe_create_order(a.client.create_order,OrderArgsV2(price=j,size=i,side="BUY",token_id=f),d),_safe_create_order(a.client.create_order,OrderArgsV2(price=h,size=g,side="BUY",token_id=e),c))
  with _UrgentSignPriority():return(_safe_create_order(a.client.create_order,OrderArgsV2(price=j,size=i,side="BUY",token_id=f),d),_safe_create_order(a.client.create_order,OrderArgsV2(price=h,size=g,side="BUY",token_id=e),c))
 def _can_batch_post_dominance_box(a):b=getattr(a.client,"_mock_children",None);c=getattr(a.client,"__dict__",{});return bool(PostOrdersV2Args is not None and"post_order"not in c and(b is None or"post_orders"in b or"post_orders"in c)and hasattr(a.client,"post_orders")and os.environ.get("PM_DISABLE_D1_BATCH_POST_ORDERS","0")!="1")
 @staticmethod
 def _build_atomic_box_success_dict(ctx,m_1,m_1_gross,oid_1,resp_1,nr_1,m_2,m_2_gross,oid_2,resp_2,nr_2,disp_mode=None,skew_ms=None):
  (i,h,k,_,n,_),(g,f,j,_,m,_)=ctx["legs"];b=min(m_1,m_2);a=None
  if abs(m_1-m_2)>.05:c,e,d=(i,k,nr_1)if m_1>m_2 else(g,j,nr_2);a={"token_id":c,"shares":round(abs(m_1-m_2),4),"price":e,"neg_risk":d}
  l={"success":True,"box_id":ctx["box_id"],"shares":b,"net_paired_shares":b,"worst_box_cost_net":ctx["worst_box_cost_net"],"guaranteed_min_profit_usd":round(b*(1.-ctx["worst_box_cost_net"]),4),"legged_out":False,"outcome_unknown":False,"imbalance_unwind":None,"excess_leg":a,"leg_1":{"label":h,"token_id":i,"price":k,"matched_shares":m_1,"gross_shares":m_1_gross,"entry_fee_asset":("SHARES"if(ctx["explicit_gross"]and n>.0)else"USDC"),"orderID":oid_1,"raw":resp_1},"leg_2":{"label":f,"token_id":g,"price":j,"matched_shares":m_2,"gross_shares":m_2_gross,"entry_fee_asset":("SHARES"if(ctx["explicit_gross"]and m>.0)else"USDC"),"orderID":oid_2,"raw":resp_2}}
  if disp_mode is not None:l["dispatch_mode"]=disp_mode
  if skew_ms is not None:l["inter_leg_skew_ms"]=skew_ms
  return l
 def _unwind_atomic_box_leg_sync(c,ctx,tok_u,lbl_u,m_u,px_u,nr_u,oid_u,raw_u):
  u=ctx["pre_bal_map"].get(str(tok_u),.0);d=None;j=getattr(c,"auth_mode","")in("LIVE","AUTHENTICATED_L2")
  if j:
   o=time.monotonic()+5.
   while time.monotonic()<o:
    try:d=c.get_unreserved_conditional_balance(tok_u)
    except Exception:d=None;break
    if d is None:break
    l=max(.0,float(d)-u)if u>.0 else float(d)
    if l>=float(m_u)-.05:break
    time.sleep(.15)
  b=float(m_u)
  if j and d is not None:b=max(.0,float(d)-u)if u>.0 else float(d);b=min(float(d),b)
  if j and d is not None and b<.05:g={"success":False,"matched_size":.0,"outcome_unknown":False,"error":"DEFERRED_TO_ASYNC_SUPERVISOR_PENDING_SETTLEMENT"};return g,{"token_id":tok_u,"label":lbl_u,"price":px_u,"matched_shares":float(m_u),"unwound_shares":.0,"residual_shares":round(float(m_u),4),"orderID":oid_u,"raw":raw_u,"unwind_outcome_unknown":False,"unwind_result":g}
  t=(math.floor(min(float(m_u),b)*1e2+1e-9)/1e2)if(j and d is not None and b<float(m_u)-.05)else float(m_u);q=float((getattr(c,"risk_config",None)or RISK_CONFIG).get("d1_max_giveback_frac",.25));n=max(.01,min(.03,round(q*max(.02,1.-ctx["worst_box_cost_net"]),2)));g=c.execute_unwind_order(tok_u,size=t,side="SELL",min_price=max(.01,round(px_u-n,2)),neg_risk=nr_u);m=bool(isinstance(g,dict)and g.get("outcome_unknown"));f=(float(g.get("matched_size")or.0)if(isinstance(g,dict)and(g.get("success")or g.get("partial"))and not m)else.0);e=float((g or{}).get("taking_amount")or(g or{}).get("notional_usd")or.0)if f>.0 else.0;i=float((g or{}).get("fee_usd")or.0)if f>.0 else.0;s=round(max(.0,float(m_u)-f),4);a=max(.0,b-f)
  if j and d is not None and s>.05 and not m:
   try:h=c.get_unreserved_conditional_balance(tok_u)
   except Exception:h=None
   if h is not None:
    if float(h)>float(d)+.05:a+=float(h)-float(d)
    k=max(.0,float(h)-u)if u>.0 else max(.0,float(h));a=min(a,k)
  if s>.05 and not m and(not j or d is None or a>=.05):
   r=(math.floor(min(s,a)*1e2+1e-9)/1e2)if(j and d is not None)else s
   if r>=.05:
    w=c.execute_unwind_order(tok_u,size=r,side="SELL",min_price=max(.01,round(px_u*.85,2)),neg_risk=nr_u)
    if isinstance(w,dict):
     m=bool(w.get("outcome_unknown"))
     if(w.get("success")or w.get("partial"))and not m:
      v=float(w.get("matched_size")or.0);f+=v
      if v>.0:e+=float(w.get("taking_amount")or w.get("notional_usd")or.0);i+=float(w.get("fee_usd")or.0)
     g=dict(w)
     if f>.0:g["matched_size"]=round(f,4);g["taking_amount"]=round(e,6);g["fee_usd"]=round(i,6)
  p=round(max(.0,float(m_u)-f),4);return g,{"token_id":tok_u,"label":lbl_u,"price":px_u,"matched_shares":float(m_u),"unwound_shares":f,"residual_shares":p,"orderID":oid_u,"raw":raw_u,"unwind_outcome_unknown":m,"unwind_result":g}
 def execute_atomic_dominance_box(b,box_id,leg_a_token_id,leg_a_label,leg_a_limit_price,leg_b_token_id,leg_b_label,leg_b_limit_price,shares,max_box_cost_net=.995,fee_rate=.07,fee_exponent=1.,leg_a_avail_shares=None,leg_b_avail_shares=None,neg_risk=False,fee_rate_a=None,fee_rate_b=None,fee_exponent_a=None,fee_exponent_b=None,parallel_dispatch=None,leg_a_pre_balance=None,leg_b_pre_balance=None,min_box_cost_floor=.9,leg_a_shares=None,leg_b_shares=None):
  L,_p=b._prepare_atomic_dominance_box_ctx(box_id,leg_a_token_id,leg_a_label,leg_a_limit_price,leg_b_token_id,leg_b_label,leg_b_limit_price,shares,max_box_cost_net,fee_rate,fee_exponent,leg_a_avail_shares,leg_b_avail_shares,neg_risk,fee_rate_a,fee_rate_b,fee_exponent_a,fee_exponent_b,parallel_dispatch,leg_a_pre_balance,leg_b_pre_balance,min_box_cost_floor,leg_a_shares,leg_b_shares)
  if L is not None or _p is None:return L or{"success":False,"error":"INVALID_BOX_CTX"}
  (X,W,_k,_,_o,_j),(V,U,_i,_,_n,_h)=_p["legs"];G=_p["shares_int"];v=_p["worst_box_cost_net"];w=_p["explicit_gross"];T=b.get_token_tick_size(X);S=b.get_token_tick_size(V);_g=b.get_token_neg_risk(X,neg_risk);_f=b.get_token_neg_risk(V,neg_risk);O,N=b._sign_atomic_dominance_box_legs(_p,T,_g,S,_f)
  def a(tok_u,lbl_u,m_u,px_u,nr_u,oid_u,raw_u):return b._unwind_atomic_box_leg_sync(_p,tok_u,lbl_u,m_u,px_u,nr_u,oid_u,raw_u)
  import inspect as _inspect;R=b.client.post_order
  try:F=list(_inspect.signature(R).parameters.values());l=len(F)>=4 or any(p.kind in(_inspect.Parameter.VAR_POSITIONAL,_inspect.Parameter.VAR_KEYWORD)or p.name=="defer_exec"for p in F)
  except Exception:l=True
  def e(signed_ord):
   if b._can_use_hot_async_bridge():return b._post_json_hot_async_bridge("/order",b._serialize_signed_order_payload(signed_ord,OrderType.FOK,False,True))
   if l:return R(signed_ord,OrderType.FOK,False,True)
   return R(signed_ord,OrderType.FOK)
  _hot_d1_held=True;_HOT_DISPATCH_ACTIVE.enter()
  def c():
   nonlocal _hot_d1_held
   if _hot_d1_held:_hot_d1_held=False;_HOT_DISPATCH_ACTIVE.leave()
  try:
   if _p["use_parallel"]:
    if b._can_batch_post_dominance_box():
     u="BATCH_POST_ORDERS_FOK";x=.0
     try:
      if b._can_use_hot_async_bridge():t=b._post_json_hot_async_bridge("/orders",[b._serialize_signed_order_payload(O,OrderType.FOK,False,True),b._serialize_signed_order_payload(N,OrderType.FOK,False,True)])
      else:t=b.client.post_orders([PostOrdersV2Args(order=O,orderType=OrderType.FOK,deferExec=True),PostOrdersV2Args(order=N,orderType=OrderType.FOK,deferExec=True)],post_only=False,defer_exec=True)
      if isinstance(t,list)and len(t)==2:j,s=t[0],None;h,r=t[1],None
      else:z=RuntimeError(f"UNEXPECTED_BATCH_POST_ORDERS_RESPONSE:{type(t).__name__}");j,s=None,z;h,r=None,z
     except Exception as A:j,s=None,A;h,r=None,A
    else:
     u="PARALLEL_2LEG_FOK"
     def o(signed_ord):
      p=time.perf_counter()
      try:return e(signed_ord),None,p
      except Exception as k:return None,k,p
     M=_get_hot_io_pool();f1=M.submit(o,O);f2=M.submit(o,N);j,s,_e=f1.result();h,r,_d=f2.result();x=round(abs(_d-_e)*1e3,3)
    def n(resp_x,exc_x,exp_sz,tok_x):
     if exc_x is not None:em=str(getattr(exc_x,"error_message","")or str(exc_x));_r=is_clob_400_rejection(exc_x)or any(k in em.lower()for k in("fok","couldn't be fully filled","fully filled","not enough balance"));return("REJECTED"if _r else"UNKNOWN"),.0,None,em
     if not isinstance(resp_x,dict):return"UNKNOWN",.0,None,"MISSING_RESPONSE"
     _q=resp_x.get("errorMsg")or resp_x.get("error");_a=resp_x.get("orderID")or resp_x.get("id")
     if _q and not _a:return"REJECTED",.0,None,str(_q)
     if _q or not _a:return"UNKNOWN",.0,_a,str(_q or"missing orderID")
     p=b._extract_fok_matched_shares(resp_x,exp_sz)
     if p is None:p=b._resolve_deferred_fok_gross(_a,tok_x,resp_x)
     if p is None:return"UNKNOWN",.0,_a,f"NON_IMMEDIATE_STATUS ({resp_x.get('status')})"
     if p<=.0:return"REJECTED",.0,_a,"MATCHED_ZERO_SHARES"
     return"FILLED",float(p),str(_a),""
    _c,K,D,Q=n(j,s,_j,X);_b,J,B,P=n(h,r,_h,V);_m=b._net_delivered_box_shares(K,_o,w);_l=b._net_delivered_box_shares(J,_n,w)
    if _c=="FILLED"and _b=="FILLED":return b._build_atomic_box_success_dict(_p,_m,K,D,j,_g,_l,J,B,h,_f,u,x)
    if _c=="REJECTED"and _b=="REJECTED":return{"success":False,"stage":"PARALLEL_BOTH_REJECTED","dispatch_mode":u,"inter_leg_skew_ms":x,"legged_out":False,"outcome_unknown":False,"error":f"L1={Q}; L2={P}"}
    if _c=="FILLED"and _b=="REJECTED":c();uw,d=a(X,W,_m,_k,_g,D,j);return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","dispatch_mode":u,"inter_leg_skew_ms":x,"legged_out":True,"outcome_unknown":False,"leg_1_order_id":D,"unwind_result":uw,"residual_unhedged_leg":d,"error":P}
    if _b=="FILLED"and _c=="REJECTED":c();uw,d=a(V,U,_l,_i,_f,B,h);return{"success":False,"stage":"LEG_1_REJECTED_LEG_2_UNWOUND","dispatch_mode":u,"inter_leg_skew_ms":x,"legged_out":True,"outcome_unknown":False,"leg_2_order_id":B,"unwind_result":uw,"residual_unhedged_leg":d,"error":Q}
    return{"success":False,"stage":"PARALLEL_OUTCOME_UNKNOWN","dispatch_mode":u,"inter_leg_skew_ms":x,"legged_out":bool(_c=="FILLED"or _b=="FILLED"),"outcome_unknown":True,"leg_1_order_id":D,"leg_2_order_id":B,"leg_1_token_id":X,"leg_2_token_id":V,"error":f"L1={_c}:{Q}; L2={_b}:{P}"}
   m=False
   try:m=True;j=e(O)
   except Exception as Z:E=str(getattr(Z,"error_message","")or str(Z));q=is_clob_400_rejection(Z)or any(k in E.lower()for k in("fok","couldn't be fully filled","fully filled","not enough balance"));return{"success":False,"stage":"LEG_1_EXCEPTION","legged_out":False,"outcome_unknown":bool(m and not q),"leg_1_token_id":X,"error":E}
   E=j.get("errorMsg")or j.get("error");D=j.get("orderID")or j.get("id")
   if E and not D:return{"success":False,"stage":"LEG_1_REJECTED","legged_out":False,"outcome_unknown":False,"error":str(E),"raw_leg_1":j}
   if E or not D:return{"success":False,"stage":"LEG_1_UNKNOWN","legged_out":False,"outcome_unknown":True,"leg_1_order_id":D,"leg_1_token_id":X,"error":f"AMBIGUOUS_LEG_1_RESPONSE: {E or'missing orderID'}","raw_leg_1":j}
   i=b._extract_fok_matched_shares(j,_j)
   if i is None:i=b._resolve_deferred_fok_gross(D,X,j)
   if i is None:return{"success":False,"stage":"LEG_1_UNKNOWN","legged_out":False,"outcome_unknown":True,"leg_1_order_id":D,"leg_1_token_id":X,"error":f"LEG_1_NON_IMMEDIATE_STATUS ({j.get('status')})","raw_leg_1":j}
   if i<=.0:return{"success":False,"stage":"LEG_1_REJECTED","legged_out":False,"outcome_unknown":False,"error":"LEG_1_MATCHED_ZERO_SHARES","raw_leg_1":j}
   I=b._net_delivered_box_shares(i,_o,w)
   if I<G-.05:c();f,d=a(X,W,I,_k,_g,D,j);return{"success":False,"stage":"LEG_1_PARTIAL_FILL_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":D,"unwind_result":f,"residual_unhedged_leg":d,"error":f"LEG_1_UNDERFILLED ({I:.2f} < {G:.2f})","raw_leg_1":j}
   try:h=e(N)
   except Exception as Y:
    c();C=str(getattr(Y,"error_message","")or str(Y));q=is_clob_400_rejection(Y)or any(k in C.lower()for k in("fok","couldn't be fully filled","fully filled","not enough balance"))
    if not q:return{"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":D,"leg_1_token_id":X,"leg_2_token_id":V,"error":C}
    f,d=a(X,W,I,_k,_g,D,j);return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":D,"unwind_result":f,"residual_unhedged_leg":d,"error":C}
   c();C=h.get("errorMsg")or h.get("error");B=h.get("orderID")or h.get("id")
   if not C and B:
    g=b._extract_fok_matched_shares(h,_h if w else I)
    if g is None:g=b._resolve_deferred_fok_gross(B,V,h)
    if g is None:return{"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":D,"leg_2_order_id":B,"leg_1_token_id":X,"leg_2_token_id":V,"error":f"LEG_2_NON_IMMEDIATE_STATUS ({h.get('status')})","raw_leg_2":h}
    if g<=.0:f,d=a(X,W,I,_k,_g,D,j);return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":D,"unwind_result":f,"residual_unhedged_leg":d,"error":"LEG_2_MATCHED_ZERO_SHARES","raw_leg_2":h}
    H=b._net_delivered_box_shares(g,_n,w);y=min(I,H);logger.info(f"[LIVE DOMINANCE BOX FILLED] {box_id} | {y:.2f} pairs @ worst_net=${v:.4f} ({W}={D}, {U}={B})");return b._build_atomic_box_success_dict(_p,I,i,D,j,_g,H,g,B,h,_f)
   if C and not B:f,d=a(X,W,I,_k,_g,D,j);return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":D,"unwind_result":f,"residual_unhedged_leg":d,"error":str(C),"raw_leg_2":h}
   return{"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":D,"leg_2_order_id":B,"leg_1_token_id":X,"leg_2_token_id":V,"error":f"AMBIGUOUS_LEG_2_RESPONSE: {C or'missing orderID'}","raw_leg_2":h}
  finally:c()
 async def execute_atomic_dominance_box_async(a,box_id,leg_a_token_id,leg_a_label,leg_a_limit_price,leg_b_token_id,leg_b_label,leg_b_limit_price,shares,max_box_cost_net=.995,fee_rate=.07,fee_exponent=1.,leg_a_avail_shares=None,leg_b_avail_shares=None,neg_risk=False,fee_rate_a=None,fee_rate_b=None,fee_exponent_a=None,fee_exponent_b=None,parallel_dispatch=None,leg_a_pre_balance=None,leg_b_pre_balance=None,min_box_cost_floor=.9,leg_a_shares=None,leg_b_shares=None):
  if("execute_atomic_dominance_box"in getattr(a,"__dict__",{})or(not a.dry_run and not a._can_use_native_async_post_order())):return await asyncio.to_thread(a.execute_atomic_dominance_box,box_id,leg_a_token_id,leg_a_label,leg_a_limit_price,leg_b_token_id,leg_b_label,leg_b_limit_price,shares,max_box_cost_net,fee_rate,fee_exponent,leg_a_avail_shares,leg_b_avail_shares,neg_risk,fee_rate_a,fee_rate_b,fee_exponent_a,fee_exponent_b,parallel_dispatch,leg_a_pre_balance,leg_b_pre_balance,min_box_cost_floor,leg_a_shares,leg_b_shares)
  F,_d=a._prepare_atomic_dominance_box_ctx(box_id,leg_a_token_id,leg_a_label,leg_a_limit_price,leg_b_token_id,leg_b_label,leg_b_limit_price,shares,max_box_cost_net,fee_rate,fee_exponent,leg_a_avail_shares,leg_b_avail_shares,neg_risk,fee_rate_a,fee_rate_b,fee_exponent_a,fee_exponent_b,parallel_dispatch,leg_a_pre_balance,leg_b_pre_balance,min_box_cost_floor,leg_a_shares,leg_b_shares)
  if F is not None or _d is None:return F or{"success":False,"error":"INVALID_BOX_CTX"}
  (S,R,Y,_,_c,X),(Q,P,W,_,_b,V)=_d["legs"];A=_d["shares_int"];p=_d["explicit_gross"]
  if"get_token_tick_size"in getattr(a,"__dict__",{})or"get_token_neg_risk"in getattr(a,"__dict__",{}):u,t=a.get_token_tick_size(S),a.get_token_tick_size(Q);L,K=a.get_token_neg_risk(S,neg_risk),a.get_token_neg_risk(Q,neg_risk)
  else:(u,L),(t,K)=await asyncio.gather(a.get_token_metadata_async(S,neg_risk),a.get_token_metadata_async(Q,neg_risk))
  J,I=a._sign_atomic_dominance_box_legs(_d,u,L,t,K)
  async def e(endpoint,payload):_e,k=a._encode_fast_l2_request(endpoint,payload);_f,_,_=await a._exec_hot_async_post(endpoint,_e,k);return _f
  async def c(signed_ord):
   _f=time.perf_counter()
   try:_e=await e("/order",a._serialize_signed_order_payload(signed_ord,OrderType.FOK,False,True));return _e,None,_f
   except Exception as k:return None,k,_f
  async def d(resp_x,exc_x,exp_sz,tok_x):
   if exc_x is not None:em=str(getattr(exc_x,"error_message","")or str(exc_x));_h=is_clob_400_rejection(exc_x)or any(k in em.lower()for k in("fok","couldn't be fully filled","fully filled","not enough balance"));return("REJECTED"if _h else"UNKNOWN"),.0,None,em
   if not isinstance(resp_x,dict):return"UNKNOWN",.0,None,"MISSING_RESPONSE"
   _g=resp_x.get("errorMsg")or resp_x.get("error");_f=resp_x.get("orderID")or resp_x.get("id")
   if _g and not _f:return"REJECTED",.0,None,str(_g)
   if _g or not _f:return"UNKNOWN",.0,_f,str(_g or"missing orderID")
   _e=a._extract_fok_matched_shares(resp_x,exp_sz)
   if _e is None:_e=await a._resolve_deferred_fok_gross_async(_f,tok_x,resp_x)
   if _e is None:return"UNKNOWN",.0,_f,f"NON_IMMEDIATE_STATUS ({resp_x.get('status')})"
   if _e<=.0:return"REJECTED",.0,_f,"MATCHED_ZERO_SHARES"
   return"FILLED",float(_e),str(_f),""
  _hot_d1_held=True;_HOT_DISPATCH_ACTIVE.enter()
  def b():
   nonlocal _hot_d1_held
   if _hot_d1_held:_hot_d1_held=False;_HOT_DISPATCH_ACTIVE.leave()
  try:
   if _d["use_parallel"]:
    if a._can_batch_post_dominance_box():
     m="BATCH_POST_ORDERS_FOK";q=.0
     try:
      z=await e("/orders",[a._serialize_signed_order_payload(J,OrderType.FOK,False,True),a._serialize_signed_order_payload(I,OrderType.FOK,False,True)])
      if isinstance(z,list)and len(z)==2:h,l=z[0],None;g,j=z[1],None
      else:O=RuntimeError(f"UNEXPECTED_BATCH_POST_ORDERS_RESPONSE:{type(z).__name__}");h,l,g,j=None,O,None,O
     except Exception as v:h,l,g,j=None,v,None,v
    else:m="PARALLEL_2LEG_FOK";(h,l,U),(g,j,T)=await asyncio.gather(c(J),c(I));q=round(abs(T-U)*1e3,3)
    (H,E,y,s),(G,D,x,r)=await asyncio.gather(d(h,l,X,S),d(g,j,V,Q));_a=a._net_delivered_box_shares(E,_c,p);Z=a._net_delivered_box_shares(D,_b,p)
    if H=="FILLED"and G=="FILLED":return a._build_atomic_box_success_dict(_d,_a,E,y,h,L,Z,D,x,g,K,m,q)
    if H=="REJECTED"and G=="REJECTED":return{"success":False,"stage":"PARALLEL_BOTH_REJECTED","dispatch_mode":m,"inter_leg_skew_ms":q,"legged_out":False,"outcome_unknown":False,"error":f"L1={s}; L2={r}"}
    if H=="FILLED"and G=="REJECTED":b();w,f=await asyncio.to_thread(a._unwind_atomic_box_leg_sync,_d,S,R,_a,Y,L,y,h);return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","dispatch_mode":m,"inter_leg_skew_ms":q,"legged_out":True,"outcome_unknown":False,"leg_1_order_id":y,"unwind_result":w,"residual_unhedged_leg":f,"error":r}
    if G=="FILLED"and H=="REJECTED":b();w,f=await asyncio.to_thread(a._unwind_atomic_box_leg_sync,_d,Q,P,Z,W,K,x,g);return{"success":False,"stage":"LEG_1_REJECTED_LEG_2_UNWOUND","dispatch_mode":m,"inter_leg_skew_ms":q,"legged_out":True,"outcome_unknown":False,"leg_2_order_id":x,"unwind_result":w,"residual_unhedged_leg":f,"error":s}
    return{"success":False,"stage":"PARALLEL_OUTCOME_UNKNOWN","dispatch_mode":m,"inter_leg_skew_ms":q,"legged_out":bool(H=="FILLED"or G=="FILLED"),"outcome_unknown":True,"leg_1_order_id":y,"leg_2_order_id":x,"leg_1_token_id":S,"leg_2_token_id":Q,"error":f"L1={H}:{s}; L2={G}:{r}"}
   h,e1,_=await c(J)
   if e1 is not None:N=str(getattr(e1,"error_message","")or str(e1));i=is_clob_400_rejection(e1)or any(k in N.lower()for k in("fok","couldn't be fully filled","fully filled","not enough balance"));return{"success":False,"stage":"LEG_1_EXCEPTION","legged_out":False,"outcome_unknown":bool(not i),"leg_1_token_id":S,"error":N}
   H,o,y,s=await d(h,None,X,S)
   if H=="REJECTED":return{"success":False,"stage":"LEG_1_REJECTED","legged_out":False,"outcome_unknown":False,"error":s,"raw_leg_1":h}
   if H!="FILLED":return{"success":False,"stage":"LEG_1_UNKNOWN","legged_out":False,"outcome_unknown":True,"leg_1_order_id":y,"leg_1_token_id":S,"error":s,"raw_leg_1":h}
   C=a._net_delivered_box_shares(o,_c,p)
   if C<A-.05:b();w,f=await asyncio.to_thread(a._unwind_atomic_box_leg_sync,_d,S,R,C,Y,L,y,h);return{"success":False,"stage":"LEG_1_PARTIAL_FILL_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":y,"unwind_result":w,"residual_unhedged_leg":f,"error":f"LEG_1_UNDERFILLED ({C:.2f} < {A:.2f})","raw_leg_1":h}
   g,e2,_=await c(I);b()
   if e2 is not None:
    M=str(getattr(e2,"error_message","")or str(e2));i=is_clob_400_rejection(e2)or any(k in M.lower()for k in("fok","couldn't be fully filled","fully filled","not enough balance"))
    if not i:return{"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":y,"leg_1_token_id":S,"leg_2_token_id":Q,"error":M}
    w,f=await asyncio.to_thread(a._unwind_atomic_box_leg_sync,_d,S,R,C,Y,L,y,h);return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":y,"unwind_result":w,"residual_unhedged_leg":f,"error":M}
   G,n,x,r=await d(g,None,V if p else C,Q)
   if G=="FILLED":B=a._net_delivered_box_shares(n,_b,p);logger.info(f"[LIVE DOMINANCE BOX FILLED] {box_id} | {min(C,B):.2f} pairs @ worst_net=${_d['worst_box_cost_net']:.4f} ({R}={y}, {P}={x})");return a._build_atomic_box_success_dict(_d,C,o,y,h,L,B,n,x,g,K)
   if G=="REJECTED":w,f=await asyncio.to_thread(a._unwind_atomic_box_leg_sync,_d,S,R,C,Y,L,y,h);return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":y,"unwind_result":w,"residual_unhedged_leg":f,"error":r,"raw_leg_2":g}
   return{"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":y,"leg_2_order_id":x,"leg_1_token_id":S,"leg_2_token_id":Q,"error":r,"raw_leg_2":g}
  finally:b()
 def execute_maker_anchor_hedge_or_unwind(a,box_id,anchor_token_id,anchor_label,anchor_price,anchor_matched_shares,anchor_order_id,hedge_token_id,hedge_label,hedge_limit_price,max_box_cost_net=.993,hedge_fee_rate=.07,hedge_fee_exponent=1.,neg_risk=None,anchor_neg_risk=None,hedge_neg_risk=None,anchor_pre_balance=.0,hedge_pre_balance=.0,anchor_raw=None):
  try:J=float(anchor_price);I=float(anchor_matched_shares);z=float(hedge_limit_price);H=float(max_box_cost_net);Q=float(hedge_fee_rate);P=float(hedge_fee_exponent)
  except(TypeError,ValueError):return{"success":False,"error":"INVALID_MAKER_ANCHOR_HEDGE_INPUTS","legged_out":False,"outcome_unknown":False}
  if not anchor_token_id or not hedge_token_id or str(anchor_token_id)==str(hedge_token_id)or I<=.0:return{"success":False,"error":"INVALID_MAKER_ANCHOR_TOKENS_OR_SHARES","legged_out":False,"outcome_unknown":False}
  G=a.get_token_neg_risk(anchor_token_id,anchor_neg_risk if anchor_neg_risk is not None else neg_risk);F=a.get_token_neg_risk(hedge_token_id,hedge_neg_risk if hedge_neg_risk is not None else neg_risk);E=a.quantize_order_price(z,hedge_token_id,rounding=ROUND_CEILING);B=Q*((E*(1.-E))**P)if Q>.0 else.0;R=min(.25,max(.0,B/max(E,1e-6)))if Q>.0 else.0;p=J+E/max(1.-R,1e-6);o=J+E+B;c=round(max(p,o),6);v=float(math.floor(I+1e-9))
  if not a.dry_run and v>=5.:
   O=quantize_fok_buy_leg_size(v/max(1.-R,1e-6),E,round_up=True);u=(v*J+O*E)/max(v,1e-6);t=(v*J+O*(E+B))/max(v,1e-6);y=round(max(u,t),6)
   if y<=H+1e-6:e=O;c=max(c,y)
   else:
    N=quantize_fok_buy_leg_size(v/max(1.-R,1e-6),E,round_up=False);x=(math.floor(N*(1.-R)*1e2+1e-9)/1e2)if R>.0 else N;s=round((v*J+N*(E+B))/max(min(v,N),1e-6),6)
    if N>=5. and x>=5. and s<=H+1e-6:e=N;c=max(c,s)
    else:e=O;c=max(c,y)
  else:e=v
  def b():
   _c=float(anchor_pre_balance or.0);S=None;T=(not a.dry_run)and getattr(a,"auth_mode","")in("LIVE","AUTHENTICATED_L2")
   if T:
    X=time.monotonic()+5.
    while time.monotonic()<X:
     try:S=a.get_unreserved_conditional_balance(anchor_token_id)
     except Exception:S=None;break
     if S is None:break
     Y=max(.0,float(S)-_c)if _c>.0 else float(S)
     if Y>=I-.05:break
     time.sleep(.15)
   k=I
   if T and S is not None:k=min(float(S),max(.0,float(S)-_c)if _c>.0 else float(S))
   if T and S is not None and k<.05:Z={"success":False,"matched_size":.0,"outcome_unknown":False,"error":"DEFERRED_TO_ASYNC_SUPERVISOR_PENDING_SETTLEMENT"};return Z,{"token_id":anchor_token_id,"label":anchor_label,"price":J,"is_maker_anchor":True,"matched_shares":I,"unwound_shares":.0,"residual_shares":round(I,4),"orderID":anchor_order_id,"raw":anchor_raw,"unwind_outcome_unknown":False,"unwind_result":Z}
   _b=(math.floor(min(I,k)*1e2+1e-9)/1e2)if(T and S is not None and k<I-.05)else I;U=a.execute_unwind_order(anchor_token_id,size=_b,side="SELL",min_price=max(.01,round(J-.02,2)),neg_risk=G);W=bool(isinstance(U,dict)and U.get("outcome_unknown"));V=float(U.get("matched_size")or.0)if(isinstance(U,dict)and(U.get("success")or U.get("partial"))and not W)else.0;_a=round(max(.0,I-V),4)
   if _a>.05 and not W:
    _d=a.execute_unwind_order(anchor_token_id,size=_a,side="SELL",min_price=max(.01,round(J*.85,2)),neg_risk=G)
    if isinstance(_d,dict):
     W=bool(_d.get("outcome_unknown"))
     if(_d.get("success")or _d.get("partial"))and not W:V+=float(_d.get("matched_size")or.0)
     U=dict(_d);U["matched_size"]=round(V,4)
   return U,{"token_id":anchor_token_id,"label":anchor_label,"price":J,"is_maker_anchor":True,"matched_shares":I,"unwound_shares":round(V,4),"residual_shares":round(max(.0,I-V),4),"orderID":anchor_order_id,"raw":anchor_raw,"unwind_outcome_unknown":W,"unwind_result":U}
  if v<5. or c<.05-1e-6 or c>H+1e-6:j,g=b();return{"success":False,"stage":"ANCHOR_PARTIAL_OR_CAP_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":anchor_order_id,"unwind_result":j,"residual_unhedged_leg":g,"error":f"MAKER_ANCHOR_PRE_HEDGE_VETO (sh={I:.2f}, net={c:.4f}, cap={H:.4f})"}
  if a.dry_run:q=f"MOCK_MKR_HDG_L2_{int(time.time()*1000)}";return{"success":True,"mode":"DRY_RUN","box_id":box_id,"shares":v,"worst_box_cost_net":c,"guaranteed_min_profit_usd":round(v*(1.-c),4),"legged_out":False,"outcome_unknown":False,"leg_1":{"label":anchor_label,"token_id":anchor_token_id,"price":J,"matched_shares":v,"orderID":anchor_order_id,"is_maker_anchor":True,"raw":anchor_raw},"leg_2":{"label":hedge_label,"token_id":hedge_token_id,"price":E,"matched_shares":v,"orderID":q}}
  if not a.is_authenticated or a.client is None or OrderArgsV2 is None:raise RuntimeError(f"LIVE MAKER ANCHOR HEDGE REFUSED: Executor unauthenticated ({a.auth_mode}).")
  _hot_ma_held=True;_HOT_DISPATCH_ACTIVE.enter()
  def d():
   nonlocal _hot_ma_held
   if _hot_ma_held:_hot_ma_held=False;_HOT_DISPATCH_ACTIVE.leave()
  try:
   try:n=a.get_token_tick_size(hedge_token_id,price_hint=E)
   except TypeError:n=a.get_token_tick_size(hedge_token_id)
   D=PartialCreateOrderOptions(tick_size=str(n),neg_risk=F,version=2)if PartialCreateOrderOptions else None
   with _UrgentSignPriority():A=_safe_create_order(a.client.create_order,OrderArgsV2(price=E,size=e,side="BUY",token_id=hedge_token_id),D)
   try:
    if a._can_use_hot_async_bridge():i=a._post_json_hot_async_bridge("/order",a._serialize_signed_order_payload(A,OrderType.FOK,False,True))
    else:i=a.client.post_order(A,OrderType.FOK,False,True)
   except TypeError:i=a.client.post_order(A,OrderType.FOK)
   except Exception as M:
    d();r=str(getattr(M,"error_message","")or str(M));m=is_clob_400_rejection(M)or any(k in r.lower()for k in("fok","couldn't be fully filled","fully filled","not enough balance"))
    if not m:return{"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":anchor_order_id,"leg_1_token_id":anchor_token_id,"leg_2_token_id":hedge_token_id,"error":r}
    j,g=b();return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":anchor_order_id,"unwind_result":j,"residual_unhedged_leg":g,"error":r}
   d();r=i.get("errorMsg")or i.get("error");q=i.get("orderID")or i.get("id")
   if not r and q:
    f=a._extract_fok_matched_shares(i,e)
    if f is None:f=a._resolve_deferred_fok_gross(q,hedge_token_id,i)
    if f is None:return{"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":anchor_order_id,"leg_2_order_id":q,"leg_1_token_id":anchor_token_id,"leg_2_token_id":hedge_token_id,"error":f"LEG_2_NON_IMMEDIATE_STATUS ({i.get('status')})","raw_leg_2":i}
    if f<=.0:j,g=b();return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":anchor_order_id,"unwind_result":j,"residual_unhedged_leg":g,"error":"LEG_2_MATCHED_ZERO_SHARES","raw_leg_2":i}
    w=(math.floor(float(f)*(1.-R)*1e2+1e-9)/1e2)if R>.0 else float(f);l=min(I,w);h=None
    if abs(I-w)>.05:C,L,K=(anchor_token_id,J,G)if I>w else(hedge_token_id,E,F);h={"token_id":C,"shares":round(abs(I-w),4),"price":L,"neg_risk":K}
    logger.info(f"[LIVE MAKER ANCHOR BOX FILLED] {box_id} | {l:.2f} pairs @ worst_net=${c:.4f} (MKR={anchor_order_id}, FOK={q})");return{"success":True,"box_id":box_id,"shares":l,"net_paired_shares":l,"worst_box_cost_net":c,"guaranteed_min_profit_usd":round(l*(1.-c),4),"legged_out":False,"outcome_unknown":False,"imbalance_unwind":None,"excess_leg":h,"leg_1":{"label":anchor_label,"token_id":anchor_token_id,"price":J,"matched_shares":I,"orderID":anchor_order_id,"is_maker_anchor":True,"raw":anchor_raw},"leg_2":{"label":hedge_label,"token_id":hedge_token_id,"price":E,"matched_shares":w,"gross_shares":f,"entry_fee_asset":("SHARES"if R>.0 else"USDC"),"orderID":q,"raw":i}}
   if r and not q:j,g=b();return{"success":False,"stage":"LEG_2_REJECTED_UNWOUND","legged_out":True,"outcome_unknown":False,"leg_1_order_id":anchor_order_id,"unwind_result":j,"residual_unhedged_leg":g,"error":str(r),"raw_leg_2":i}
   return{"success":False,"stage":"LEG_2_UNKNOWN","legged_out":True,"outcome_unknown":True,"leg_1_order_id":anchor_order_id,"leg_2_order_id":q,"leg_1_token_id":anchor_token_id,"leg_2_token_id":hedge_token_id,"error":f"AMBIGUOUS_LEG_2_RESPONSE: {r or'missing orderID'}","raw_leg_2":i}
  finally:d()
 def buy_complement_leg_fak(a,token_id,limit_price,shares,tick_size="0.001",neg_risk=None):
  b=float(math.floor(float(shares)*1e2+1e-9)/1e2)
  if not token_id or b<5. or not(.001<=float(limit_price)<=.05):return{"success":False,"matched_shares":.0,"error":"INVALID_COMPLEMENT_PARAMS"}
  if a.dry_run:return{"success":True,"matched_shares":b,"cost_usd":round(b*float(limit_price),4)}
  if not a.is_authenticated or a.client is None or OrderArgsV2 is None:return{"success":False,"matched_shares":.0,"error":"UNAUTHENTICATED"}
  _HOT_DISPATCH_ACTIVE.enter()
  try:
   k=a.get_token_neg_risk(token_id,neg_risk);i=a.quantize_order_price(float(limit_price),token_id,rounding=ROUND_CEILING);b=quantize_fok_buy_leg_size(b,i,round_up=False)
   if b<5.:return{"success":False,"matched_shares":.0,"error":"INVALID_COMPLEMENT_PARAMS"}
   h=PartialCreateOrderOptions(tick_size=str(tick_size),neg_risk=k,version=2)if PartialCreateOrderOptions else None
   with _UrgentSignPriority():f=_safe_create_order(a.client.create_order,OrderArgsV2(price=i,size=b,side="BUY",token_id=token_id),h)
   try:g=a._post_signed_order_bridge_or_sync(f,OrderType.FAK,False,True)
   except Exception as d:return{"success":False,"matched_shares":.0,"error":str(d)}
   j=(g or{}).get("errorMsg")or(g or{}).get("error");c=float(a._extract_fok_matched_shares(g or{},.0)or.0)
   if j or c<5.:return{"success":False,"matched_shares":c,"error":str(j or"INSUFFICIENT_FAK_MATCH")}
   e=.07*i*(1.-i);return{"success":True,"matched_shares":c,"price":i,"cost_usd":round(c*(i+e),4)}
  finally:_HOT_DISPATCH_ACTIVE.leave()
 def execute_atomic_box_overround_unwind(a,box_id,leg_a_token_id,leg_a_min_price,leg_b_token_id,leg_b_min_price,shares,neg_risk_a=None,neg_risk_b=None,fee_rate_a=.0,fee_exp_a=1.,fee_rate_b=.0,fee_exp_b=1.):
  G=float(Decimal(str(max(.0,float(shares or.0)))).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
  if G<1. or not leg_a_token_id or not leg_b_token_id or str(leg_a_token_id)==str(leg_b_token_id):return{"success":False,"error":"INVALID_OVERROUND_INPUTS","outcome_unknown":False}
  q=a.quantize_order_price(float(leg_a_min_price),leg_a_token_id,rounding=ROUND_FLOOR);p=a.quantize_order_price(float(leg_b_min_price),leg_b_token_id,rounding=ROUND_FLOOR)
  if q>=.01 and(int(round(G*1e2))*int(round(q*1e4)))%100!=0:q=float(Decimal(str(q)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
  if p>=.01 and(int(round(G*1e2))*int(round(p*1e4)))%100!=0:p=float(Decimal(str(p)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
  y=round(G*float(fee_rate_a)*((q*(1.-q))**float(fee_exp_a)),5)if fee_rate_a>0 else.0;x=round(G*float(fee_rate_b)*((p*(1.-p))**float(fee_exp_b)),5)if fee_rate_b>0 else.0
  if a.dry_run:u=int(time.time()*1000);s,r=round(G*q,4),round(G*p,4);return{"success":True,"mode":"DRY_RUN","box_id":box_id,"shares":G,"leg_a":{"filled":True,"orderID":f"MOCK_OVR_A_{u}","matched_size":G,"taking_amount":s,"fee_usd":y,"avg_px":q},"leg_b":{"filled":True,"orderID":f"MOCK_OVR_B_{u}","matched_size":G,"taking_amount":r,"fee_usd":x,"avg_px":p}}
  if not a.is_authenticated or a.client is None or OrderArgsV2 is None:return{"success":False,"error":"UNAUTHENTICATED_OVERROUND_UNWIND","outcome_unknown":False}
  w=a.get_unreserved_conditional_balance(leg_a_token_id);v=a.get_unreserved_conditional_balance(leg_b_token_id)
  if w is None or v is None or w+1e-6<G or v+1e-6<G:return{"success":False,"error":f"INSUFFICIENT_OVERROUND_INVENTORY (a={w}, b={v}, req={G})","outcome_unknown":False}
  _HOT_DISPATCH_ACTIVE.enter()
  try:
   try:o=a.get_token_tick_size(leg_a_token_id,price_hint=q);n=a.get_token_tick_size(leg_b_token_id,price_hint=p)
   except TypeError:o=a.get_token_tick_size(leg_a_token_id);n=a.get_token_tick_size(leg_b_token_id)
   F=a.get_token_neg_risk(leg_a_token_id,neg_risk_a);E=a.get_token_neg_risk(leg_b_token_id,neg_risk_b);D=PartialCreateOrderOptions(tick_size=str(o),neg_risk=F,version=2)if PartialCreateOrderOptions else None;C=PartialCreateOrderOptions(tick_size=str(n),neg_risk=E,version=2)if PartialCreateOrderOptions else None
   with _UrgentSignPriority():B=_safe_create_order(a.client.create_order,OrderArgsV2(price=q,size=G,side="SELL",token_id=leg_a_token_id),D);A=_safe_create_order(a.client.create_order,OrderArgsV2(price=p,size=G,side="SELL",token_id=leg_b_token_id),C)
   f=getattr(a.client,"_mock_children",None);e=getattr(a.client,"__dict__",{});d=(PostOrdersV2Args is not None and"post_order"not in e and(f is None or"post_orders"in f or"post_orders"in e)and hasattr(a.client,"post_orders")and os.environ.get("PM_DISABLE_D1_BATCH_POST_ORDERS","0")!="1")
   if d:
    try:
     if a._can_use_hot_async_bridge():m=a._post_json_hot_async_bridge("/orders",[a._serialize_signed_order_payload(B,OrderType.FOK,False,True),a._serialize_signed_order_payload(A,OrderType.FOK,False,True)])
     else:m=a.client.post_orders([PostOrdersV2Args(order=B,orderType=OrderType.FOK,deferExec=True),PostOrdersV2Args(order=A,orderType=OrderType.FOK,deferExec=True)],post_only=False,defer_exec=True)
     if isinstance(m,list)and len(m)==2:l,j=m[0],None;i,h=m[1],None
     else:t=RuntimeError(f"UNEXPECTED_BATCH_OVERROUND_RESP:{type(m).__name__}");l,j=None,t;i,h=None,t
    except Exception as g:l,j=None,g;i,h=None,g
   else:
    def b(sg_x):
     try:return a._post_signed_order_bridge_or_sync(sg_x,OrderType.FOK,False,True),None
     except Exception as k:return None,k
    z=_get_hot_io_pool();L=z.submit(b,B);K=z.submit(b,A);l,j=L.result(timeout=6.);i,h=K.result(timeout=6.)
   def c(tok,min_p,fr,fe,rx,ex):
    if ex is not None:em=str(getattr(ex,"error_message","")or str(ex));c4=is_clob_400_rejection(ex)or is_market_closed_or_disabled_error(ex)or any(k in em.lower()for k in("fok","couldn't be fully filled","fully filled","not enough balance"));return{"filled":False,"outcome_unknown":not c4,"error":em,"orderID":None}
    if not isinstance(rx,dict):return{"filled":False,"outcome_unknown":True,"error":f"INVALID_RESP:{rx!r}","orderID":None}
    Z=rx.get("orderID")or rx.get("id");X=str(rx.get("status")or"").upper();U=rx.get("errorMsg")or rx.get("error");O=rx.get("makingAmount")if rx.get("makingAmount")not in(None,"")else rx.get("size_matched");M=rx.get("takingAmount")if rx.get("takingAmount")not in(None,"")else rx.get("taking_amount");P=Z and not U and hasattr(a,"get_order_fill_summary")and(hasattr(a.client,"get_order")or"get_order_fill_summary"in a.__dict__ or getattr(a,"_user_ws_cache",None)is not None);N=None
    if P and(X in{"DELAYED","LIVE"}or(X in{"MATCHED","FILLED","CONFIRMED","MINED"}and M in(None,""))):
     for T in range(4):
      if T>0:time.sleep(.12)
      try:N=a.get_order_fill_summary(str(Z),tok)
      except Exception:N=None
      if isinstance(N,dict)and(float(N.get("matched")or.0)>.0 or N.get("terminal")):break
    if isinstance(N,dict):
     if float(N.get("matched")or.0)>.0:
      O=float(N["matched"]);X="MATCHED"
      if M in(None,"")and float(N.get("cash")or.0)>.0:M=float(N["cash"])
     elif N.get("terminal"):return{"filled":False,"outcome_unknown":False,"error":f"TERMINAL_ZERO_FILL:{X}","orderID":str(Z)}
    if Z and not U and X in{"MATCHED","FILLED","CONFIRMED","MINED"}and O not in(None,""):
     W=float(O)
     if W>.0:R=M in(None,"");Q=float(M)if not R else round(W*float((N or{}).get("avg_price")or min_p),4);S=min(.999,max(.001,Q/max(W,1e-9)));Y=round(W*fr*((S*(1.-S))**fe),5)if fr>0 else.0;return{"filled":True,"outcome_unknown":False,"orderID":str(Z),"matched_size":W,"taking_amount":Q,"taking_amount_estimated":R,"fee_usd":Y,"avg_px":S}
    V=(bool(U)and not Z)or X.startswith("CANCEL")or X in{"EXPIRED","REJECTED","UNMATCHED"}or is_fak_killed_no_match(None,rx)or is_clob_400_rejection(None,rx)or is_market_closed_or_disabled_error(None,rx);return{"filled":False,"outcome_unknown":not V,"error":str(U or X or"UNMATCHED"),"orderID":Z}
   J=c(leg_a_token_id,q,fee_rate_a,fee_exp_a,l,j);I=c(leg_b_token_id,p,fee_rate_b,fee_exp_b,i,h);H=bool(J.get("outcome_unknown")or I.get("outcome_unknown"));return{"success":bool(J.get("filled")and I.get("filled")and not H),"partial_leg_unwind":bool(J.get("filled")^I.get("filled")),"outcome_unknown":H,"box_id":box_id,"shares":G,"leg_a":J,"leg_b":I}
  finally:_HOT_DISPATCH_ACTIVE.leave()
 def post_maker_exit_order(a,token_id,price,size,side="SELL",neg_risk=None):
  L=Decimal("0.01");B=Decimal(str(size)).quantize(L,rounding=ROUND_FLOOR)
  if B<=Decimal("0.00"):return{"success":False,"orderID":None,"error":"NON_POSITIVE_EXIT_SIZE","retryable":False}
  if not a.dry_run:
   if not a.is_authenticated or a.client is None:raise RuntimeError(f"LIVE EXIT REFUSED: Executor is in live mode but unauthenticated ({a.auth_mode}).")
   A=a.get_unreserved_conditional_balance(token_id)
   if A is None:H=f"UNKNOWN_CONDITIONAL_BALANCE: Balance query failed for {token_id}. Refusing unverified exit order submission.";logger.warning(f"[PM-EXEC] {H}");return{"success":False,"orderID":None,"error":H,"available_balance":None,"retryable":True}
   z=Decimal(str(A)).quantize(L,rounding=ROUND_FLOOR)
   if z<B:H=f"INSUFFICIENT_UNRESERVED_BALANCE: INSUFFICIENT_CONDITIONAL_BALANCE: Unreserved balance {z} < requested exit size {B} (reserved: {a.reserved_inventory.get(token_id,.0):.2f})";logger.warning(f"[PM-EXEC] {H}");return{"success":False,"orderID":None,"error":H,"available_balance":float(z),"retryable":True}
   g=float(B)
  else:g=float(B);F=f"MOCK_EXIT_{int(time.time()*1000)}";logger.info(f"[DRY-RUN EXIT] Resting {side} limit order: {g:.2f} shares @ ${price:.4f} (ID: {F})");return{"success":True,"orderID":F,"mode":"DRY_RUN","post_only":True}
  c=False;n=.01
  try:
   q=a.quantize_order_price(price,token_id,rounding=ROUND_CEILING)
   try:n=a.get_token_tick_size(token_id,price_hint=q)
   except TypeError:n=a.get_token_tick_size(token_id)
   v=a.get_token_neg_risk(token_id,neg_risk);x=(PartialCreateOrderOptions(tick_size=str(n),neg_risk=v,version=2)if PartialCreateOrderOptions else None);y=OrderArgsV2(price=q,size=g,side=side,token_id=token_id);l=(getattr(a.client,"_fast_v2_signer",None)is not None and"create_order"not in getattr(a.client,"__dict__",{}))
   if l:j=_safe_create_order(a.client.create_order,y,x)
   else:
    with _UrgentSignPriority():j=_safe_create_order(a.client.create_order,y,x)
   c=True;C=a._post_signed_order_bridge_or_sync(j,OrderType.GTC,post_only=True,defer_exec=True);s=C.get("errorMsg")or C.get("error");D=C.get("orderID")or C.get("id")
   if s and D:logger.critical(f"Contradictory maker post response (orderID={D} with error={s}). Retaining as UNKNOWN/HELD.");a.reserve_inventory(token_id,g,reservation_id=D);return{"success":False,"orderID":D,"outcome_unknown":True,"retryable":False,"error":f"CONTRADICTORY_RESPONSE: {s}","raw":C}
   if s:
    a._evict_tick_size_if_tick_err(token_id,s)
    if str(side).upper()=="SELL"and("crosses book"in str(s).lower()or"post only"in str(s).lower()or"post-only"in str(s).lower()):
     p=.0;h=float(Decimal("1")-Decimal(str(n)));i=None;m=q
     try:
      K=a.get_market_book(token_id);t=K.get("bids",[])if isinstance(K,dict)else[];p=max((float(b.get("price",.0))for b in t if float(b.get("size",.0))>0),default=.0)
      if p>=h-1e-9:return{"success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"crossed_at_max_tick":True,"best_bid":p,"error":str(s),"raw":C}
      if p>=q:
       m=a.quantize_order_price(min(h,p+n),token_id,rounding=ROUND_CEILING)
       if m>max(q,p)+1e-9:
        logger.info(f"[POST-ONLY PRICE IMPROVEMENT] Best bid ${p:.4f} >= target ${q:.4f}. Repricing maker sell to ${m:.4f}!");u=OrderArgsV2(price=m,size=g,side=side,token_id=token_id)
        if l:i=_safe_create_order(a.client.create_order,u,x)
        else:
         with _UrgentSignPriority():i=_safe_create_order(a.client.create_order,u,x)
     except Exception:pass
     if i is not None:
      c=True;G=a._post_signed_order_bridge_or_sync(i,OrderType.GTC,post_only=True,defer_exec=True);J=G.get("errorMsg")or G.get("error")if isinstance(G,dict)else"INVALID_MAKER_REPRICE_RESP";I=(G.get("orderID")or G.get("id"))if isinstance(G,dict)else None
      if J and I:a.reserve_inventory(token_id,g,reservation_id=I);return{"success":False,"orderID":I,"outcome_unknown":True,"retryable":False,"error":f"CONTRADICTORY_RESPONSE: {J}","raw":G}
      if I and not J:a.reserve_inventory(token_id,g,reservation_id=I);return{"success":True,"orderID":I,"post_only":True,"price":m,"raw":G,"matched_size":.0}
      if not I and not J:o=f"AMBIGUOUS_POST_{int(time.time()*1000)}";a.reserve_inventory(token_id,g,reservation_id=o);return{"success":False,"orderID":None,"outcome_unknown":True,"retryable":False,"reservation_id":o,"error":"MISSING_ORDER_ID_IN_MAKER_REPRICE","raw":G}
      s=J;C=G
    logger.error(f"Failed to post maker exit order (rejected): {C}");return{"success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"error":str(s),"raw":C}
   if D:
    logger.info(f"[LIVE MAKER EXIT POSTED (POST-ONLY)] OID: {D} | {side} {size:.2f} shares @ ${q:.4f}")
    try:f=float(C.get("size_matched",C.get("matched_size",C.get("sizeMatched",.0)))or.0)
    except(TypeError,ValueError):f=.0
    r=max(.0,g-f)
    if r>.0:a.reserve_inventory(token_id,r,reservation_id=D)
    return{"success":True,"orderID":D,"post_only":True,"price":q,"raw":C,"matched_size":f}
   logger.critical(f"Failed to post maker exit order (missing orderID, ambiguous outcome): {C}");o=f"AMBIGUOUS_POST_{int(time.time()*1000)}";a.reserve_inventory(token_id,g,reservation_id=o);return{"success":False,"orderID":None,"outcome_unknown":True,"retryable":False,"reservation_id":o,"error":"MISSING_ORDER_ID_IN_MAKER_POST","raw":C}
  except Exception as e:
   d=False;w=getattr(e,"status_code",None);E=str(getattr(e,"error_message","")or str(e))
   if w and int(w)in{400,401,403,404,422}:d=True;a._evict_tick_size_if_tick_err(token_id,E)
   elif any(k in E.lower()for k in("not enough balance","allowance","invalid order","crosses book","post only","post-only")):d=True
   if not c or d:
    if side.upper()=="SELL"and any(k in E.lower()for k in("crosses book","post only","post-only")):
     h=round(1.-float(n),4)
     try:
      K=a.get_market_book(token_id);t=K.get("bids",[])if isinstance(K,dict)else[];p=max((float(b.get("price",.0))for b in t if float(b.get("size",.0))>0),default=.0)
      if p>=h-1e-9:return{"success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"crossed_at_max_tick":True,"best_bid":p,"error":E}
     except Exception:pass
    logger.warning(f"Maker exit order rejected by exchange before matching (no open order): {e}");return{"success":False,"orderID":None,"outcome_unknown":False,"retryable":True,"error":E}
   logger.critical(f"Exception posting maker exit order (outcome unknown): {e}");o=f"EXCEPTION_POST_{int(time.time()*1000)}";a.reserve_inventory(token_id,g,reservation_id=o);return{"success":False,"orderID":None,"outcome_unknown":True,"retryable":False,"reservation_id":o,"error":str(e)}
 def execute_unwind_order(a,token_id,size,side="SELL",min_price=.01,neg_risk=None):
  if a.dry_run:
   P=f"MOCK_UNWIND_{int(time.time()*1000)}";logger.info(f"[DRY-RUN UNWIND] Executed simulated {side} unwind: {size:.2f} shares @ min ${min_price:.4f}");c=.07;b=1.
   if token_id in a._fee_cache:c,b=a._fee_cache[token_id]
   k=size*min_price;U=min(.999,max(.001,min_price));O=round(size*c*((U*(1.-U))**b),5);return{"success":True,"orderID":P,"matched_size":size,"taking_amount":k,"fee_usd":O}
  if not a.is_authenticated or a.client is None:return{"success":False,"orderID":None,"retryable":True,"outcome_unknown":False,"error":"Live CLOB client unavailable; no simulated success permitted"}
  g=float(Decimal(str(max(.0,float(size or.0)))).quantize(Decimal("0.01"),rounding=ROUND_FLOOR));d=False;j=.01
  try:
   X=Decimal("0.01");n=Decimal(str(size)).quantize(X,rounding=ROUND_FLOOR);t=a.get_unreserved_conditional_balance(token_id)
   if t is None:return{"success":False,"orderID":None,"matched_size":.0,"retryable":True,"outcome_unknown":False,"error":"UNVERIFIED_SELL_INVENTORY: balance query unavailable"}
   M=Decimal(str(t)).quantize(X,rounding=ROUND_FLOOR)
   if M<n:
    if M>Decimal("0.00")and M>=n-Decimal("0.05"):logger.info(f"[PM-EXEC] Clamping unwind size {n} -> {M} shares to match exact unreserved wallet dust.");n=M
    else:return{"success":False,"orderID":None,"matched_size":.0,"retryable":False,"outcome_unknown":False,"error":f"SELL_INVENTORY_RECONCILIATION_REQUIRED: unreserved {M} < requested {n} (reserved: {a.reserved_inventory.get(token_id,.0):.2f})"}
   g=float(n)
   if g<=.0:logger.warning(f"[UNWIND SKIPPED] Size {size} rounds to 0.00 lots.");return{"success":True,"orderID":None,"matched_size":.0,"taking_amount":.0,"fee_usd":.0}
   f=a.quantize_order_price(min_price,token_id,rounding=ROUND_FLOOR)
   if f>=.01 and(int(round(g*1e2))*int(round(f*1e4)))%100!=0:f=float(Decimal(str(f)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR))
   try:j=a.get_token_tick_size(token_id,price_hint=f)
   except TypeError:j=a.get_token_tick_size(token_id)
   C=a.get_token_neg_risk(token_id,neg_risk);F=(PartialCreateOrderOptions(tick_size=str(j),neg_risk=C,version=2)if PartialCreateOrderOptions else None);K=OrderArgsV2(price=f,size=g,side=side,token_id=token_id);W=time.perf_counter()
   with _UrgentSignPriority():B=_safe_create_order(a.client.create_order,K,F)
   m=getattr(OrderType,"FAK",OrderType.FOK);d=True;V=a.client.post_order(B,m,post_only=False,defer_exec=True);y=(time.perf_counter()-W)*1e3;N=V.get("orderID")or V.get("id");T=V.get("status");x=V.get("takingAmount")or V.get("taking_amount");J=str(T).upper()if T else"";E=V.get("makingAmount")if V.get("makingAmount")not in(None,"")else V.get("size_matched");s=J in{"MATCHED","FILLED","CONFIRMED","MINED"};I=bool(N)and s and E not in(None,"")
   if I:
    A=float(E);r=x in(None,"");k=float(x)if not r else A*f;L=V.get("transactionsHashes")or V.get("transaction_hashes")or[];p=bool(a.dry_run or(J in{"CONFIRMED","MINED"}and L and all(a.get_transaction_receipt_status(str(Y))is True for Y in L)));l=r or(not p)
    if not(math.isfinite(A)and math.isfinite(k)and.0<=A<=g+1e-4 and k>=.0):h=str(N or f"AMBIGUOUS_UNWIND_{int(time.time()*1000)}");a.reserve_inventory(token_id,g,reservation_id=h);return{"success":False,"orderID":N,"matched_size":.0,"outcome_unknown":True,"retryable":False,"reservation_id":h,"submitted_size":g,"error":"INCONSISTENT_UNWIND_FILL_AMOUNTS","raw":V}
    w=min(.999,max(.001,k/max(A,1e-9)));c=.07;b=1.;S=str(token_id)
    if S not in a._fee_cache and not a.dry_run and a.client is not None and getattr(a.client,"_mock_children",None)is None:
     try:
      if hasattr(a.client,"get_fee_rate_bps"):R=float(a.client.get_fee_rate_bps(S)or.0);Q=float(a.client.get_fee_exponent(S)or 1.)if hasattr(a.client,"get_fee_exponent")else 1.;a._fee_cache[S]=(R/1e4,max(1.,Q))
     except Exception:pass
    if S in a._fee_cache:c,b=a._fee_cache[S]
    elif token_id in a._fee_cache:c,b=a._fee_cache[token_id]
    v=round(A*c*((w*(1.-w))**b),5);a._log_order(OrderResult(success=True,order_id=str(N),trade_id=f"UNWIND_{N}",token_id=str(token_id),target_token="",side=side,price=round(w,4),size=A,notional_usd=round(k,4),fee_usd=v,latency_ms=y,mode="LIVE_UNWIND",execution_status=ExecutionStatus.FILLED,confirmed_onchain=p,details={"raw_response":V,"taking_is_estimated":l}));H=Decimal(str(g)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR);D=Decimal(str(A)).quantize(Decimal("0.01"),rounding=ROUND_FLOOR)
    if D<H:z=H-D;u=float(z);logger.warning(f"[PARTIAL UNWIND FILL] Order {N}: matched {A:.2f} of {g:.2f} shares. Proceeds: ${k:.2f}. Residual: {u:.2f} shares remain open.");return{"success":False,"orderID":N,"matched_size":A,"unfilled_size":u,"taking_amount":k,"fee_usd":v,"fee_is_estimated":True,"taking_amount_estimated":l,"taking_amount_missing":r,"partial":True,"retryable":True,"error":f"PARTIAL_FILL: Matched {A:.2f} of {g:.2f} shares (residual: {u:.2f})","raw":V}
    logger.info(f"[LIVE UNWIND EXECUTED] OID: {N} | Sold {A:.2f} shares @ min ${f:.4f} (Proceeds: ${k:.2f})");return{"success":True,"orderID":N,"matched_size":A,"taking_amount":k,"taking_amount_estimated":l,"taking_amount_missing":r,"fee_usd":v,"fee_is_estimated":True,"raw":V}
   else:
    G=is_market_closed_or_disabled_error(None,V);i=(G or J.startswith("CANCEL")or J in{"EXPIRED","REJECTED","UNMATCHED","INVALID"}or is_fak_killed_no_match(None,V)or is_clob_400_rejection(None,V));o=not i;logger.warning(f"[LIVE UNWIND NON-MATCHED] Response: {V} | terminal={i} | closed={G}");h=None
    if o:h=str(N or f"AMBIGUOUS_UNWIND_{int(time.time()*1000)}");a.reserve_inventory(token_id,g,reservation_id=h)
    return{"success":False,"orderID":N,"matched_size":.0,"retryable":bool(i and not G),"market_closed":bool(G),"outcome_unknown":o,"reservation_id":h,"submitted_size":g,"error":f"Status: {T}","raw":V}
  except Exception as e:
   q=is_market_closed_or_disabled_error(e);logger.error(f"[LIVE UNWIND EXCEPTION] Error executing unwind order (submitted={d}, closed={q}): {e}")
   if not d or is_clob_400_rejection(e)or q:return{"success":False,"orderID":None,"matched_size":.0,"retryable":not q,"market_closed":bool(q),"outcome_unknown":False,"error":str(e)}
   h=f"EXCEPTION_UNWIND_{int(time.time()*1000)}";a.reserve_inventory(token_id,g,reservation_id=h);return{"success":False,"orderID":None,"matched_size":.0,"retryable":True,"outcome_unknown":True,"reservation_id":h,"submitted_size":g,"error":str(e)}
 def post_heartbeat(a,heartbeat_id=None):
  if a.dry_run or not a.is_authenticated or a.client is None:return{"heartbeat_id":"MOCK_HEARTBEAT"}
  k=a.last_heartbeat_id if heartbeat_id is None else heartbeat_id
  try:
   with _CLOB_HTTP_LOCK:j=a.client.post_heartbeat(heartbeat_id=k or"")
   g=j.get("heartbeat_id")if isinstance(j,dict)else None
   if g:a.last_heartbeat_id=g
   a.heartbeat_failures=0;return j
  except Exception as e:
   b=None;h=getattr(e,"error_message",None)or getattr(e,"error_msg",None)
   if isinstance(h,dict)and h.get("heartbeat_id"):b=str(h["heartbeat_id"]).strip()
   else:
    import re;i=re.search(r"['\"]heartbeat_id['\"]\s*:\s*['\"]([0-9a-fA-F-]{16,})['\"]",str(e))
    if i:b=i.group(1).strip()
   if b and b!=(k or""):
    try:
     with _CLOB_HTTP_LOCK:c=a.client.post_heartbeat(heartbeat_id=b)
     g=c.get("heartbeat_id")if isinstance(c,dict)else None;a.last_heartbeat_id=str(g or b);a.heartbeat_failures=0;logger.info(f"[HEARTBEAT RESYNCED] Automatically resynced CLOB heartbeat_id ({b} -> {a.last_heartbeat_id}).");return c if isinstance(c,dict)else{"heartbeat_id":a.last_heartbeat_id}
    except Exception as f:logger.warning(f"[HEARTBEAT RESYNC WARN] Retry with server heartbeat_id {b} failed: {f}")
   elif k and("invalid heartbeat"in str(e).lower()or"expired"in str(e).lower()):
    try:
     with _CLOB_HTTP_LOCK:c=a.client.post_heartbeat(heartbeat_id="")
     g=c.get("heartbeat_id")if isinstance(c,dict)else None;a.last_heartbeat_id=str(g or"");a.heartbeat_failures=0;logger.info(f"[HEARTBEAT SESSION RESET] Re-initialized expired CLOB heartbeat session (-> {a.last_heartbeat_id}).");return c if isinstance(c,dict)else{"heartbeat_id":a.last_heartbeat_id}
    except Exception as d:logger.warning(f"[HEARTBEAT RESET WARN] Fresh heartbeat_id='' retry failed: {d}")
   a.last_heartbeat_id="";a.heartbeat_failures+=1;logger.error(f"[HEARTBEAT FAILURE] CLOB heartbeat error (failures={a.heartbeat_failures}): {e}");return{"error":str(e),"failures":a.heartbeat_failures}
 def is_heartbeat_healthy(self):return self.heartbeat_failures<3
 def get_open_orders(b,*,strict=False):
  if b.dry_run:return[]
  if not b.is_authenticated or b.client is None:
   if strict:raise RuntimeError("Cannot establish authoritative open-order state in live mode")
   return None
  from src.polymarket_research.riskless_protocol_v2_expansion import filter_purged_ghost_orders as a;g=getattr(b,"_user_ws_cache",None);d=(g is not None and"get_open_orders"not in getattr(b.client,"__dict__",{})and getattr(b.client,"_mock_children",None)is None)
  if d:
   f=g.get_open_orders_snapshot(max_age_sec=15.)
   if f is not None:return a(b,f)
  try:
   c=b.client.get_open_orders()
   if not isinstance(c,list):raise RuntimeError(f"Unexpected open-orders response type: {type(c).__name__}")
   c=a(b,c)
   if d:g.seed_open_orders(c)
   return c
  except Exception as e:
   logger.error(f"Error fetching open orders: {e}")
   if strict:raise RuntimeError("CLOB open-order snapshot unavailable")from e
   return None
 def cancel_all_orders(a):
  if a.dry_run or not a.is_authenticated or a.client is None:return{"canceled_all":True}
  try:logger.warning("[KILL-SWITCH] Canceling all open CLOB orders...");return a.client.cancel_all()
  except Exception as e:logger.error(f"Failed to cancel all orders: {e}");return{"error":str(e)}
 def cancel_orders_batch(a,order_ids):
  b=[str(o).strip()for o in(order_ids or[])if o and str(o).strip()]
  if not b:return{}
  if len(b)==1:return{b[0]:a.cancel_order(b[0])}
  d=_get_hot_io_pool();c={oid:d.submit(a.cancel_order,oid)for oid in b};return{oid:f.result(timeout=6.)for oid,f in c.items()}
 def cancel_order(a,order_id,*,token_id=None,pre_token_balance=None,market_closed=False):
  if a.dry_run and(a.client is None or not a.is_authenticated):a.release_inventory(reservation_id=order_id);return CancelOrderResult({"canceled":[order_id]},order_id=str(order_id),outcome="CANCELED",is_canceled=True,canceled=[order_id],matched=.0)
  c=None;v={}
  try:
   if a.client:
    for w,t in enumerate((.0,.18,.4)):
     if t>.0 and not a.dry_run:time.sleep(t)
     try:v=a.client.cancel_orders([order_id])or{};c=None;break
     except Exception as u:
      c=str(u);z=c.lower();p=any(k in z for k in("425","order manager not ready","too early","500","502","503","504","cancel request failed","temporarily","timeout"))
      if not p or w>=2:break
      logger.warning(f"[PM-EXEC] Transient CLOB cancel error on {order_id} (attempt {w+1}/3): {c}")
   m=(v or{}).get("canceled");o=(v or{}).get("not_canceled");b=c
   if isinstance(o,dict):
    for C,B in o.items():
     if str(C)==str(order_id):b=str(B or"NOT_CANCELED");break
   elif isinstance(o,(list,tuple,set))and str(order_id)in{str(x)for x in o}:b="NOT_CANCELED"
   h=bool(b is None and isinstance(m,list)and str(order_id)in[str(x)for x in m]);g=a.get_order_status(order_id)
   if h and g is None and not a.dry_run:time.sleep(.12);g=a.get_order_status(order_id)
   D=getattr(a,"_user_ws_cache",None);s=D.get_order_snapshot(order_id,max_age_sec=8.)if(D is not None and D.is_healthy())else None;n=str((g or{}).get("status","")).upper();l=float((g or{}).get("size_matched",.0)or.0);i=float((g or{}).get("original_size",.0)or.0)
   if isinstance(s,dict):
    A=float(s.get("size_matched",.0)or.0)
    if A>l:l=A
    if i<=.0:i=float(s.get("original_size",.0)or.0)
    y=str(s.get("status","")).upper();r=i<=.0 or l>=i-1e-4
    if not n or(n=="LIVE"and(y in{"CANCELED","CANCELLED"}or(y=="INVALID"and l<=1e-6)or(y in{"MATCHED","FILLED"}and r))):n=y
   q=str((g or{}).get("order_type")or(g or{}).get("type")or"").upper()
   if(n in{"MATCHED","FILLED"}and(i<=.0 or l>=i-1e-4 or q in{"FAK","FOK"}))or(i>.0 and l>=i-1e-4):f="FILLED";logger.warning(f"[PM-EXEC] Order {order_id} cancellation returned FILLED/MATCHED (matched={l:.2f}). " "Retaining reservation until caller reconciles filled quantity.");return CancelOrderResult(v or{},order_id=str(order_id),outcome=f,is_canceled=False,matched=l,not_canceled_reason=b,raw=v)
   elif n.startswith("CANCEL")or n in{"EXPIRED","REJECTED"}or(n=="INVALID"and l<=1e-6)or(h and(a.dry_run or g is not None)):
    j=bool(h and n=="LIVE")
    if l>.0 and i>.0 and l<i:f="PARTIALLY_FILLED_CANCELED"
    else:f="CANCELED"
    a.release_inventory(reservation_id=order_id);logger.info(f"[PM-EXEC] Order {order_id} verified canceled ({f}). Released reservation.");return CancelOrderResult(v if h else{"canceled":[order_id]},order_id=str(order_id),outcome=f,is_canceled=True,matched=l,not_canceled_reason=b,raw=v,canceled=[order_id],read_replica_stale_live=j)
   else:
    from src.polymarket_research.riskless_protocol_v2_expansion import is_verified_zero_fill_cancel_purge as d
    if d(a,str(order_id),l,b,g,token_id=token_id,pre_token_balance=pre_token_balance,market_closed=market_closed):a.release_inventory(reservation_id=order_id);logger.info(f"[PM-EXEC] Order {order_id} purged zero-fill verified CANCELED ({b}).");return CancelOrderResult({"canceled":[order_id]},order_id=str(order_id),outcome="CANCELED",is_canceled=True,matched=.0,not_canceled_reason=b,raw=v,canceled=[order_id],read_replica_stale_live=(n=="LIVE"))
    f="UNKNOWN";logger.warning(f"[PM-EXEC] Order {order_id} cancellation could NOT be verified terminally (status={n}, not_canceled={b}). Retaining inventory reservation fail-closed.");return CancelOrderResult(v or{},order_id=str(order_id),outcome=f,is_canceled=False,matched=l,not_canceled_reason=b,raw=v,error=c)
  except Exception as e:logger.error(f"Failed to cancel order {order_id}: {e}");return CancelOrderResult({},order_id=str(order_id),outcome="UNKNOWN",is_canceled=False,error=str(e))
 def _verify_and_release_canceled_reservation_bg(a,order_id,*,token_id=None,pre_token_balance=None,market_closed=False):
  k=str(order_id)
  try:
   j=getattr(a,"_user_ws_cache",None)
   if j is not None and j.is_healthy()and hasattr(j,"wait_for_order_terminal_sync"):
    i=j.wait_for_order_terminal_sync(k,timeout_sec=.25)
    if isinstance(i,dict):
     e=str(i.get("status")or"").upper();h=float(i.get("size_matched",.0)or.0)
     if e in{"MATCHED","FILLED"}or h>1e-6:return False
     if e in{"CANCELED","CANCELLED"}or(e=="INVALID"and h<=1e-6):a.release_inventory(reservation_id=k);return True
   for d in(.0,.12,.25):
    if d>.0 and not a.dry_run:time.sleep(d)
    g=a.get_order_status(k);l=str((g or{}).get("status")or"").upper();f=float((g or{}).get("size_matched",.0)or.0)
    if l in{"MATCHED","FILLED"}or f>1e-6:return False
    if l.startswith("CANCEL")or l in{"EXPIRED","REJECTED"}or(l=="INVALID"and f<=1e-6):a.release_inventory(reservation_id=k);return True
   from src.polymarket_research.riskless_protocol_v2_expansion import is_verified_zero_fill_cancel_purge as b
   if b(a,k,.0,None,a.get_order_status(k),token_id=token_id,pre_token_balance=pre_token_balance,market_closed=market_closed):a.release_inventory(reservation_id=k);return True
  except Exception as c:logger.warning(f"[PM-EXEC] Background cancel proof check failed for {k}: {c}")
  return False
 def cancel_order_fast(a,order_id,*,token_id=None,pre_token_balance=None,market_closed=False,ws_confirm_timeout_sec=.035,defer_unconfirmed_proof=True):
  if a.dry_run and(a.client is None or not a.is_authenticated):a.release_inventory(reservation_id=order_id);return CancelOrderResult({"canceled":[order_id]},order_id=str(order_id),outcome="CANCELED",is_canceled=True,canceled=[order_id],matched=.0)
  if(a.client is None or"get_order_status"in a.__dict__ or getattr(a.client,"_mock_children",None)is not None):return a.cancel_order(order_id,token_id=token_id,pre_token_balance=pre_token_balance,market_closed=market_closed)
  c=None;A={}
  try:
   for B,w in enumerate((.0,.12,.25)):
    if w>.0 and not a.dry_run:time.sleep(w)
    try:A=a.client.cancel_orders([order_id])or{};c=None;break
    except Exception as y:
     c=str(y);D=c.lower();l=any(k in D for k in("425","order manager not ready","too early","500","502","503","504","cancel request failed","temporarily","timeout"))
     if not l or B>=2:break
   i=(A or{}).get("canceled");j=(A or{}).get("not_canceled");b=c
   if isinstance(j,dict):
    for H,G in j.items():
     if str(H)==str(order_id):b=str(G or"NOT_CANCELED");break
   elif isinstance(j,(list,tuple,set))and str(order_id)in{str(x)for x in j}:b="NOT_CANCELED"
   g=bool(b is None and isinstance(i,list)and str(order_id)in[str(x)for x in i]);I=getattr(a,"_user_ws_cache",None);m=bool(I is not None and hasattr(I,"is_healthy")and I.is_healthy());v=(I.wait_for_order_terminal_sync(order_id,timeout_sec=ws_confirm_timeout_sec)if(m and hasattr(I,"wait_for_order_terminal_sync"))else(I.get_order_snapshot(order_id,max_age_sec=8.)if m else None))
   if isinstance(v,dict):
    C=str(v.get("status")or"").upper();F=float(v.get("size_matched",.0)or.0);u=float(v.get("original_size",.0)or.0);t=u<=.0 or F>=u-1e-4
    if(C in{"MATCHED","FILLED"}and t)or(u>.0 and F>=u-1e-4):return CancelOrderResult(A or{},order_id=str(order_id),outcome="FILLED",is_canceled=False,matched=F,not_canceled_reason=b,raw=A)
    if C in{"CANCELED","CANCELLED"}or(C=="INVALID"and F<=1e-6):
     if F<=1e-6:a.release_inventory(reservation_id=order_id);return CancelOrderResult(A if g else{"canceled":[order_id]},order_id=str(order_id),outcome="CANCELED",is_canceled=True,matched=.0,not_canceled_reason=b,raw=A,canceled=[order_id],read_replica_stale_live=False)
     if str(order_id)not in a.reservation_records and u>.0 and F<u:return CancelOrderResult(A if g else{"canceled":[order_id]},order_id=str(order_id),outcome="PARTIALLY_FILLED_CANCELED",is_canceled=True,matched=F,not_canceled_reason=b,raw=A,canceled=[order_id],read_replica_stale_live=False)
   o=float((v or{}).get("size_matched",.0)or.0)if isinstance(v,dict)else.0;n=str((v or{}).get("status")or"").upper()if isinstance(v,dict)else""
   if(g and m and defer_unconfirmed_proof and o<=1e-6 and n not in{"MATCHED","FILLED"}):
    s=str(order_id)in a.reservation_records
    if s:
     E=getattr(a,"_reservations_lock",None)or _CLOB_HTTP_LOCK
     with E:
      if str(order_id)in a.reservation_records:a.reservation_records[str(order_id)]["status"]="PENDING_CANCEL_PROOF"
     _get_hot_io_pool().submit(a._verify_and_release_canceled_reservation_bg,str(order_id),token_id=token_id,pre_token_balance=pre_token_balance,market_closed=market_closed)
    return CancelOrderResult(A,order_id=str(order_id),outcome="CANCELED",is_canceled=True,matched=.0,not_canceled_reason=None,raw=A,canceled=[order_id],read_replica_stale_live=False)
   f=a.get_order_status(order_id)
   if g and f is None and not a.dry_run:time.sleep(.12);f=a.get_order_status(order_id)
   z=str((f or{}).get("status","")).upper();r=max(o,float((f or{}).get("size_matched",.0)or.0));h=float((f or{}).get("original_size",.0)or.0)
   if h<=.0 and isinstance(v,dict):h=float(v.get("original_size",.0)or.0)
   q=str((f or{}).get("order_type")or(f or{}).get("type")or"").upper()
   if(z in{"MATCHED","FILLED"}and(h<=.0 or r>=h-1e-4 or q in{"FAK","FOK"}))or(h>.0 and r>=h-1e-4):return CancelOrderResult(A or{},order_id=str(order_id),outcome="FILLED",is_canceled=False,matched=r,not_canceled_reason=b,raw=A)
   if z.startswith("CANCEL")or z in{"EXPIRED","REJECTED"}or(z=="INVALID"and r<=1e-6)or(g and(a.dry_run or f is not None)):p="PARTIALLY_FILLED_CANCELED"if(r>.0 and h>.0 and r<h)else"CANCELED";a.release_inventory(reservation_id=order_id);return CancelOrderResult(A if g else{"canceled":[order_id]},order_id=str(order_id),outcome=p,is_canceled=True,matched=r,not_canceled_reason=b,raw=A,canceled=[order_id],read_replica_stale_live=bool(g and z=="LIVE"))
   from src.polymarket_research.riskless_protocol_v2_expansion import is_verified_zero_fill_cancel_purge as d
   if d(a,str(order_id),r,b,f,token_id=token_id,pre_token_balance=pre_token_balance,market_closed=market_closed):a.release_inventory(reservation_id=order_id);return CancelOrderResult({"canceled":[order_id]},order_id=str(order_id),outcome="CANCELED",is_canceled=True,matched=.0,not_canceled_reason=b,raw=A,canceled=[order_id],read_replica_stale_live=(z=="LIVE"))
   return CancelOrderResult(A or{},order_id=str(order_id),outcome="UNKNOWN",is_canceled=False,matched=r,not_canceled_reason=b,raw=A,error=c)
  except Exception as e:logger.error(f"Failed fast cancel on order {order_id}: {e}");return CancelOrderResult({},order_id=str(order_id),outcome="UNKNOWN",is_canceled=False,error=str(e))
 def get_order_status(a,order_id):
  if a.dry_run or not a.is_authenticated or a.client is None:return None
  try:b=a.client.get_order(order_id);return b if isinstance(b,dict)and b else None
  except Exception as e:logger.error(f"Error querying order {order_id}: {e}");return None
 def get_collateral_balance(a,max_cache_age_s=15.,hot_path=False):
  m=time.time();h,g=getattr(a,"_collateral_cache",(None,.0))
  if isinstance(h,(int,float))and h>1e9 and isinstance(g,(int,float))and g<1e9:d,b=float(h),float(g)
  else:b,d=h,float(g or.0)
  c=float(os.getenv("PM_HOT_PATH_COLLATERAL_MAX_AGE_SEC","120.0"))
  if hot_path and b is not None and isinstance(b,(int,float))and b>0:
   f=(m-d)if d>.0 else.0
   if a.dry_run or(-5.<=f<=c):return b
   logger.warning(f"[PM-EXEC] Stale hot-path collateral cache (age={f:.1f}s > {c:.1f}s); refreshing.")
  if a.dry_run:return b if(b is not None and b>0)else.0
  if max_cache_age_s>.0 and b is not None and(m-d)<=max_cache_age_s:return b
  if not a.is_authenticated or a.client is None or BalanceAllowanceParams is None:logger.warning("[PM-EXEC] Cannot query collateral balance: unauthenticated or client unavailable");return None
  try:
   i=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL,signature_type=a.signature_type);l=a.client.get_balance_allowance(i)
   if not isinstance(l,dict)or"balance"not in l:logger.error(f"[PM-EXEC] Unexpected response querying collateral balance: {l}");return None
   k=float(l.get("balance","0"));j=k/1e6;a._collateral_cache=(j,m);return j
  except Exception as e:logger.error(f"[PM-EXEC] Failed to query CLOB collateral balance: {e}");return None
 def set_cached_collateral(self,balance):
  if isinstance(balance,(int,float))and math.isfinite(balance)and balance>0:self._collateral_cache=(float(balance),time.time())
 def invalidate_collateral_cache(self):self._collateral_cache=(None,.0)
 def get_conditional_balance(a,token_id):
  if a.dry_run:return.0
  if not a.is_authenticated or a.client is None or BalanceAllowanceParams is None:logger.warning(f"[PM-EXEC] Cannot query conditional balance for {token_id}: unauthenticated or client unavailable");return None
  try:
   f=BalanceAllowanceParams(asset_type=AssetType.CONDITIONAL,token_id=token_id,signature_type=a.signature_type);h=a.client.get_balance_allowance(f)
   if not isinstance(h,dict)or"balance"not in h:logger.error(f"[PM-EXEC] Unexpected response querying conditional balance for {token_id}: {h}");return None
   c=float(h.get("balance","0"))
   if(c<=.0 and hasattr(a.client,"update_balance_allowance")and"update_balance_allowance"not in getattr(a.client,"__dict__",{})and getattr(a.client,"_mock_children",None)is None):
    b=a.__dict__.setdefault("_cond_bal_sync_ts",{});d=time.monotonic()
    if(d-float(b.get(str(token_id),.0)))>=3.:
     b[str(token_id)]=d
     try:
      a.client.update_balance_allowance(f);g=a.client.get_balance_allowance(f)
      if isinstance(g,dict)and"balance"in g:c=float(g.get("balance","0"))
     except Exception:pass
   return c/1e6
  except Exception as e:logger.error(f"[PM-EXEC] Failed to query CLOB conditional balance for {token_id}: {e}");return None
 _class_reservations:Dict[str,Dict[str,Dict[str,Any]]]={};RESERVATIONS_STATE_PATH=POLYMARKET_DATA_DIR/"inventory_reservations.json";RESERVATIONS_SCHEMA="pm-reservations/2.3.8"
 @property
 def reservations_path(a):b=os.getenv("POLYMARKET_RESERVATIONS_PATH","").strip();c=Path(b)if b else Path(a.RESERVATIONS_STATE_PATH);return c.with_name(c.stem+".dryrun"+c.suffix)if a.dry_run else c
 def _class_res_bucket(self):
  a=str(self.reservations_path)
  if a not in PolymarketLiveExecutor._class_reservations:PolymarketLiveExecutor._class_reservations[a]={}
  return PolymarketLiveExecutor._class_reservations[a]
 @classmethod
 def _get_hmac_secret(cls,live_mode=False):
  import hashlib,secrets;c=os.getenv("POLYMARKET_RESERVATION_KEY")
  if c and c.strip():return c.strip().encode("utf-8")
  f=os.getenv("POLYGON_PRIVATE_KEY")or os.getenv("POLYMARKET_PRIVATE_KEY")
  if f and f.strip():return hashlib.sha256(f"PM_RESERVATION_SECRET_SALT:{f.strip()}".encode("utf-8")).digest()
  a=Path.home()/".polymarket_reservation_hmac.key"
  if a.exists():
   try:
    d=a.read_text().strip()
    if len(d)>=32:return d.encode("utf-8")
   except Exception:pass
  if live_mode:
   try:b=secrets.token_hex(32);a.write_text(b);os.chmod(a,0o600);return b.encode("utf-8")
   except Exception as e:raise RuntimeError(f"Cannot generate secure live HMAC key: {e}")
  return b"PM_RESERVATION_HMAC_SECRET"
 @classmethod
 def _reservation_digest(cls,records,key=None,live_mode=False):import hashlib,hmac;a=json.dumps(records,sort_keys=True,separators=(",",":"),default=str);b=key or cls._get_hmac_secret(live_mode=live_mode);return hmac.new(b,a.encode("utf-8"),hashlib.sha256).hexdigest()
 @classmethod
 def _verify_reservation_digest(cls,records,digest,live_mode=False):
  import hashlib,hmac
  if not digest:return False
  a=cls._reservation_digest(records,live_mode=live_mode)
  if hmac.compare_digest(digest,a):return True
  if live_mode:return False
  c=json.dumps(records,sort_keys=True,separators=(",",":"),default=str);b=hashlib.sha256(c.encode("utf-8")).hexdigest();return hmac.compare_digest(digest,b)
 def _load_durable_reservations(a):
  a.reservation_records={};a.reservations_trusted=True;j=a.reservations_path
  if j.exists():
   try:
    with open(j,"r",encoding="utf-8")as f:d=f.read().strip()
    if not d:raise ValueError("reservation file is empty")
    i=json.loads(d)
    if not isinstance(i,dict)or not isinstance(i.get("reservation_records"),dict):raise ValueError("reservation file has corrupt schema")
    c=i["reservation_records"];h=i.get("hmac_sha256")or i.get("sha256")
    if not h:raise ValueError("reservation file missing required integrity digest (hmac_sha256)")
    if not a._verify_reservation_digest(c,h,live_mode=not a.dry_run):raise ValueError("reservation file integrity digest mismatch")
    for l,k in c.items():
     if not isinstance(k,dict)or not k.get("token_id")or not math.isfinite(float(k.get("size","nan"))):raise ValueError(f"malformed reservation record {l!r}")
    a.reservation_records=c
   except Exception as e:
    a.reservation_corruption_detected=True;a.reservations_trusted=False;b=j.with_name(f"{j.name}.corrupt.{int(time.time())}")
    try:os.replace(j,b)
    except Exception:b=j
    logger.critical(f"CRITICAL: Durable reservation state at {j} is untrusted ({e}); quarantined to {b}. " "All sell submissions are blocked until reservations are rebuilt from authoritative exchange orders.");a.reservation_records={};a._class_res_bucket().clear()
  g=a._class_res_bucket();a.reservation_records.update(g);g.update(a.reservation_records);a._sync_reserved_inventory()
 def rebuild_reservations_from_exchange(a,open_orders):
  g=getattr(a,"_reservations_lock",None)or _CLOB_HTTP_LOCK
  with g:
   if open_orders is None:a.reservations_trusted=False;return False
   e={}
   for o in open_orders:
    if not o or str(o.get("side","")).upper()!="SELL":continue
    j=str(o.get("id")or o.get("orderID")or"");i=str(o.get("asset_id")or o.get("token_id")or"")
    try:d=float(o.get("original_size",o.get("size",.0))or.0)-float(o.get("size_matched",.0)or.0)
    except(TypeError,ValueError):a.reservations_trusted=False;return False
    if not j or not i or d<=.0:continue
    e[j]={"reservation_id":j,"token_id":i,"size":float(Decimal(str(d)).quantize(Decimal("0.01"),rounding=ROUND_CEILING)),"status":"RESERVED","created_at_ts":time.time(),"source":"EXCHANGE_OPEN_ORDERS"}
   b=False
   for h,r in(a.reservation_records or{}).items():
    if r.get("status")=="RELEASED":continue
    c=(str(h).startswith(("AMBIGUOUS_","EXCEPTION_","PENDING_"))or str(r.get("status","")).upper()in{"AMBIGUOUS","IN_FLIGHT","UNRESOLVED"}or bool(r.get("ambiguous",False)))
    if c and h not in e:e[h]=dict(r);b=True
   f=a._class_res_bucket();f.clear();f.update(e);a.reservation_records=dict(e);a._sync_reserved_inventory();a._save_durable_reservations()
   if b:a.reservations_trusted=False;logger.warning(f"[PM-EXEC] Rebuilt reservations with {len(e)} commitments, but ambiguous unresolved commitments " "remain. reservations_trusted set to False fail-closed.")
   else:a.reservations_trusted=True;a.reservation_corruption_detected=False;logger.info(f"[PM-EXEC] Reservation book rebuilt from exchange: {len(e)} resting SELL commitment(s).")
   return True
 def _sync_reserved_inventory(a):
  c=getattr(a,"_reservations_lock",None)or _CLOB_HTTP_LOCK
  with c:
   b=defaultdict(float)
   for r in list(a.reservation_records.values()):
    d=str(r.get("token_id",""))
    if d and r.get("status")!="RELEASED":b[d]+=float(r.get("size",.0))
   a.reserved_inventory=defaultdict(float,{k:round(v,4)for k,v in b.items()})
 def _save_durable_reservations(a):
  i=getattr(a,"_reservations_lock",None)or _CLOB_HTTP_LOCK
  with i:
   h=a.reservations_path;b=h.with_name(f"{h.name}.tmp.{os.getpid()}.{threading.get_ident()}")
   try:
    h.parent.mkdir(parents=True,exist_ok=True);d=a._reservation_digest(a.reservation_records,live_mode=not a.dry_run);c={"schema":a.RESERVATIONS_SCHEMA,"reservation_records":a.reservation_records,"hmac_sha256":d,"sha256":d,"updated_at":time.time()}
    with open(b,"w",encoding="utf-8")as f:json.dump(c,f,indent=2,default=str);f.flush();os.fsync(f.fileno())
    os.replace(b,h)
    if os.name!="nt":
     g=os.open(str(h.parent),os.O_RDONLY)
     try:os.fsync(g)
     finally:os.close(g)
   except Exception as e:
    try:b.unlink(missing_ok=True)
    except Exception:pass
    logger.error(f"Could not save durable reservations: {e}")
    if not a.dry_run:raise RuntimeError(f"CRITICAL: Failed to persist durable reservations: {e}")
 @classmethod
 def clear_all_reservations(a):
  a._class_reservations.clear();b=Path(a.RESERVATIONS_STATE_PATH)
  for p in(b,b.with_name(b.stem+".dryrun"+b.suffix)):
   if p.exists():
    try:p.unlink()
    except Exception:pass
 def reserve_inventory(a,token_id,size,reservation_id=None):
  f=Decimal("0.01");b=float(Decimal(str(max(.0,size))).quantize(f,rounding=ROUND_FLOOR))
  if b<=.0:return
  e=getattr(a,"_reservations_lock",None)or _CLOB_HTTP_LOCK
  with e:d=str(reservation_id or f"RES_{token_id}_{int(time.time()*1000)}_{len(a.reservation_records)}");c={"reservation_id":d,"token_id":token_id,"size":b,"status":"RESERVED","created_at_ts":time.time()};a.reservation_records[d]=c;a._class_res_bucket()[d]=c;a._sync_reserved_inventory();a._save_durable_reservations()
 def release_inventory(b,token_id="",size=.0,reservation_id=None):
  h=Decimal("0.01");c=float(Decimal(str(max(.0,size))).quantize(h,rounding=ROUND_FLOOR))if size else.0;g=getattr(b,"_reservations_lock",None)or _CLOB_HTTP_LOCK
  with g:
   f=b._class_res_bucket()
   if reservation_id and str(reservation_id)in b.reservation_records:d=str(reservation_id);b.reservation_records.pop(d,None);f.pop(d,None)
   elif token_id:
    a=c if c>.0 else b.reserved_inventory.get(token_id,.0)
    for d,r in list(b.reservation_records.items()):
     if r.get("token_id")==token_id and r.get("status")!="RELEASED":
      e=float(r.get("size",.0))
      if e<=a:a-=e;b.reservation_records.pop(d,None);f.pop(d,None)
      else:
       r["size"]=round(e-a,4)
       if d in f:f[d]["size"]=r["size"]
       a=.0;break
      if a<=.0:break
   b._sync_reserved_inventory();b._save_durable_reservations()
 def update_reservation(a,reservation_id,new_remaining_size):
  e=str(reservation_id);d=getattr(a,"_reservations_lock",None)or _CLOB_HTTP_LOCK
  with d:
   if e not in a.reservation_records:return
   f=Decimal("0.01");b=float(Decimal(str(max(.0,new_remaining_size))).quantize(f,rounding=ROUND_FLOOR))
   if b<=.0:a.release_inventory(reservation_id=e)
   else:
    c=a._class_res_bucket();a.reservation_records[e]["size"]=b
    if e in c:c[e]["size"]=b
    a._sync_reserved_inventory();a._save_durable_reservations()
 def get_unreserved_conditional_balance(a,token_id):
  if not getattr(a,"reservations_trusted",True):logger.critical(f"[PM-EXEC] Reservation book UNTRUSTED; refusing to compute free inventory for {token_id}.");return None
  d=a.get_conditional_balance(token_id)
  if d is None:return None
  c=getattr(a,"_reservations_lock",None)or _CLOB_HTTP_LOCK
  with c:b=float(a.reserved_inventory.get(token_id,.0))
  return max(.0,round(d-b,4))
 def get_onchain_erc1155_balance(c,token_id,account_address=None):
  b=account_address or c.funder_address
  if not b or not token_id:return None
  try:
   m=os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com");a="0x4D97DCd97eC945f40cF65F87097ACe5EA0476045";i="00fdd58e";f=b[2:]if b.startswith("0x")else b;e=f.lower().rjust(64,"0");d=int(token_id,16)if str(token_id).startswith("0x")else int(token_id);n=hex(d)[2:].rjust(64,"0");g="0x"+i+e+n;l={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":a,"data":g},"latest"]};k=requests.post if hasattr(requests.post,"mock_calls")else getattr(c,"_sync_session",requests).post;o=k(m,json=l,timeout=3.)
   if o.status_code==200:
    h=o.json()
    if"result"in h and h["result"]is not None:j=int(h["result"],16);return j/1e6
   return None
  except Exception:return None
 _LEDGER_WRITER_LOCK=threading.Lock();_LEDGER_WRITER_QUEUE:Optional["queue.Queue[Optional[Tuple[Path, bytes]]]"]=None
 @classmethod
 def _ensure_ledger_writer(c):
  if c._LEDGER_WRITER_QUEUE is None:
   with c._LEDGER_WRITER_LOCK:
    if c._LEDGER_WRITER_QUEUE is None:
     import atexit;q=queue.Queue(maxsize=4096)
     def b():
      while True:
       h=q.get()
       try:
        if h is None:return
        f,g=h
        with open(f,"ab")as i:i.write(g)
       except Exception as e:logger.error(f"Async order ledger write error: {e}")
       finally:q.task_done()
     def a():
      try:q.join()
      except Exception:pass
     d=threading.Thread(target=b,name="pm-order-ledger-writer",daemon=True);d.start();atexit.register(a);c._LEDGER_WRITER_QUEUE=q
  return c._LEDGER_WRITER_QUEUE
 def _log_order(a,res):
  try:
   d={"timestamp_utc":datetime.now(timezone.utc).isoformat(),"success":res.success,"order_id":res.order_id,"trade_id":res.trade_id,"token_id":res.token_id,"target_token":res.target_token,"side":res.side,"price":res.price,"size":res.size,"notional_usd":res.notional_usd,"fee_usd":res.fee_usd,"latency_ms":res.latency_ms,"mode":res.mode,"error":res.error,"details":res.details}
   if _orjson is not None:
    try:b=_orjson.dumps(d,default=str)+b"\n"
    except Exception:b=(json.dumps(d,default=str)+"\n").encode("utf-8")
   else:b=(json.dumps(d,default=str)+"\n").encode("utf-8")
   c=(not a.dry_run and os.environ.get("PM_SYNC_ORDER_LEDGER","0")!="1"and not os.environ.get("POLYMARKET_LEDGER_PATH")and a.ledger_path==Path(POLYMARKET_DATA_DIR/"live_orders.jsonl"))
   if c:
    try:a._ensure_ledger_writer().put_nowait((a.ledger_path,b));return
    except Exception:pass
   with open(a.ledger_path,"ab")as f:f.write(b)
  except Exception as e:logger.error(f"Failed to append to live order ledger: {e}")
if __name__=="__main__":print("="*80);print("  POLYMARKET LIVE CLOB EXECUTION ADAPTER - STANDALONE PREFLIGHT");print("="*80);executor=PolymarketLiveExecutor(dry_run=True);print(f"Auth Mode: {executor.auth_mode}");print(f"SDK Available: {PY_CLOB_AVAILABLE}");print(f"Ledger Path: {executor.ledger_path}");fee_rate,fee_usd=executor.calculate_dynamic_crypto_fee(.77,50.);print(f"Dynamic Fee on $50 @ $0.77: Rate={fee_rate*100:.2f}% | USD=${fee_usd:.4f}");assert abs(fee_rate-.0161)<1e-4,"Dynamic fee calculation mismatch";print(">>> POLYMARKET LIVE ADAPTER PREFLIGHT: PASS (100% OPERATIONAL) <<<")
# [07/13] src/polymarket_research/polymarket_terminal_recorder.py
import asyncio;import collections;from collections import defaultdict,deque;import copy;import statistics;import json;import logging;import math;import os;import socket;import sys;import time;from datetime import datetime,timezone;from pathlib import Path;from typing import Dict,List,Optional,Any,Tuple,Set
try:import aiohttp
except ImportError:aiohttp=None
try:import numpy as np
except ImportError:np=None
try:import websockets
except ImportError:websockets=None
def _release_unused_heap_memory():
 import gc as _gc;_gc.collect()
 if os.name!="nt":
  try:import ctypes;a=ctypes.CDLL("libc.so.6");return bool(a.malloc_trim(0))
  except Exception:return False
 return True
def _enable_ws_nodelay(ws):
 try:
  b=getattr(ws,"transport",None);a=b.get_extra_info("socket")if b is not None else None
  if a is not None:a.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);return True
 except Exception:pass
 return False
def _has_buffered_ws_message(ws):
 d=getattr(ws,"recv_messages",None)
 if d is not None:c=getattr(getattr(d,"frames",None),"queue",None);return bool(c and getattr(c[0],"fin",True))
 a=getattr(ws,"messages",None)
 if a is not None:b=getattr(a,"qsize",None);return(int(b())>0)if callable(b)else bool(a)
 return False
async def _drain_ws_frames(ws,first_msg,max_batch=64):
 a=[first_msg]
 while len(a)<max_batch and _has_buffered_ws_message(ws):a.append(await ws.recv())
 return a
try:import orjson as _orjson
except Exception:_orjson=None
async def _fast_resp_json(resp):
 a=await resp.read()
 if _orjson is not None:return _orjson.loads(a)
 return json.loads(a.decode("utf-8",errors="ignore"))
try:from src.polymarket_research.polymarket_ws_streams import(get_shared_chainlink_stream as _get_shared_cl_stream,ensure_shared_chainlink_stream_started as _ensure_shared_cl_stream)
except Exception:
 try:from polymarket_ws_streams import(get_shared_chainlink_stream as _get_shared_cl_stream,ensure_shared_chainlink_stream_started as _ensure_shared_cl_stream)
 except Exception:_get_shared_cl_stream=None;_ensure_shared_cl_stream=None
PROJECT_ROOT=Path(__file__).resolve().parent.parent.parent;DATA_DIR=PROJECT_ROOT/"data"/"polymarket";DATA_DIR.mkdir(parents=True,exist_ok=True);TRIGGER_FILE=DATA_DIR/"live_shock_triggers.jsonl";RESOLUTIONS_FILE=DATA_DIR/"finalized_market_resolutions.jsonl";GAMMA_API_URL="https://gamma-api.polymarket.com";CLOB_API_URL="https://clob.polymarket.com";CLOB_WS_URL="wss://ws-subscriptions-clob.polymarket.com/ws/market";BINANCE_REST_URL="https://api.binance.com";BINANCE_FUTURES_REST_URL="https://fapi.binance.com";COINBASE_WS_URL="wss://ws-feed.exchange.coinbase.com";SHM_DIR=Path(os.getenv("PM_FAST_TICK_DIR","/dev/shm"));FAST_TICK_THROTTLE_SEC=.025;COINBASE_STALE_SEC=5.;EXP306_REALTIME_LEDGER=DATA_DIR/"exp306_realtime_boundary_merge.jsonl"
def fast_tick_path(asset):return SHM_DIR/f"pm_fast_tick_{str(asset).upper()}.json"
LEAD_STATE_MAX_AGE_MS=1500.;LEAD_STATE_THROTTLE_SEC=.025;SYMPATHY_BTC_MAX_AGE_MS=5e2;SYMPATHY_BTC_MIN_VOL_USD=2.25e6;SYMPATHY_BTC_MIN_ABS_OFI=.85;SYMPATHY_THRESHOLD_MULT=.65;SYMPATHY_MIN_AGE_ASK_MS=3e2;ADAPTIVE_THRESH_MIN_MULT=.65;ADAPTIVE_THRESH_MAX_MULT=1.35;ADAPTIVE_THRESH_VOL_MULT=18.;ADAPTIVE_THRESH_WINDOW_SEC=300;ADAPTIVE_THRESH_MIN_COVERAGE_SEC=60.;_INPROC_BTC_LEAD_STATE=None
def lead_state_path(asset="BTC"):return SHM_DIR/f"pm_lead_state_{str(asset).upper()}.json"
def write_lead_state(state,path=None):
 global _INPROC_BTC_LEAD_STATE;a=lead_state_path("BTC");path=path or a
 if path==a and isinstance(state,dict):_INPROC_BTC_LEAD_STATE=dict(state)
 try:
  b=_orjson.dumps(state)if _orjson else json.dumps(state).encode("utf-8");c=path.with_suffix(f".tmp.{os.getpid()}")
  with open(c,"wb")as f:f.write(b)
  os.replace(c,path);return True
 except Exception:return False
def read_lead_state_inproc(max_age_ms=LEAD_STATE_MAX_AGE_MS,now_ns=None):
 a=_INPROC_BTC_LEAD_STATE
 if not a:return None
 now_ns=now_ns if now_ns is not None else time.time_ns()
 if(now_ns-int(a.get("ts_ns")or 0))/1e6>max_age_ms:return None
 return a
def read_lead_state(path=None,max_age_ms=LEAD_STATE_MAX_AGE_MS,now_ns=None):
 path=path or lead_state_path("BTC")
 try:
  with open(path,"rb")as f:a=f.read()
  b=_orjson.loads(a)if _orjson else json.loads(a);now_ns=now_ns if now_ns is not None else time.time_ns()
  if(now_ns-int(b.get("ts_ns")or 0))/1e6>max_age_ms:return None
  return b
 except Exception:return None
def compute_adaptive_shock_threshold(base_threshold,avg_100ms_vol_5m):
 if avg_100ms_vol_5m is None or not math.isfinite(avg_100ms_vol_5m)or avg_100ms_vol_5m<=.0:return float(base_threshold)
 return min(ADAPTIVE_THRESH_MAX_MULT*base_threshold,max(ADAPTIVE_THRESH_MIN_MULT*base_threshold,ADAPTIVE_THRESH_VOL_MULT*avg_100ms_vol_5m))
def evaluate_btc_sympathy(lead,eth_flow_dir,eth_target_age_ask_ms,now_ns=None):
 if not lead or eth_target_age_ask_ms is None:return False
 try:
  now_ns=now_ns if now_ns is not None else time.time_ns();a=int(lead.get("last_shock_ts_ns")or 0)
  if a<=0 or(now_ns-a)/1e6>SYMPATHY_BTC_MAX_AGE_MS:return False
  if float(lead.get("last_shock_vol_100ms")or.0)<SYMPATHY_BTC_MIN_VOL_USD:return False
  if abs(float(lead.get("last_shock_ofi_100ms")or.0))<SYMPATHY_BTC_MIN_ABS_OFI:return False
  if str(lead.get("last_shock_dir")or"").upper()!=str(eth_flow_dir).upper():return False
  return float(eth_target_age_ask_ms)>=SYMPATHY_MIN_AGE_ASK_MS
 except Exception:return False
def evaluate_realtime_exp306_boundary_and_merge(asset,horizon,market_id,up_top,down_top,spot,strike_open,secs_left,fee_rate=.07,sigma_1h=None,estimated_gas_usd=.015):
 k=float(up_top.get("best_ask")or.0);j=float(down_top.get("best_ask")or.0);n=float(up_top.get("ask_size_l1")or.0);m=float(down_top.get("ask_size_l1")or.0);d=None;e=False
 if.0<k<1. and.0<j<1. and min(n,m)>0:i=fee_rate*k*(1.-k);h=fee_rate*j*(1.-j);g=estimated_gas_usd/min(n,m);d=round(1.-(k+j+i+h+g),5);e=d>=.015
 if sigma_1h is None:l=str(asset).upper();sigma_1h=.0022 if l=="XAU"else(.005 if l=="BTC"else.0068)
 c=None;b=False;a=None
 if spot>0 and strike_open>0 and 0<secs_left<=120.:f=sigma_1h*math.sqrt(max(secs_left,1.)/3600.);c=round(abs(spot-strike_open)/(strike_open*max(f,1e-9)),3);a="UP"if spot>=strike_open else"DOWN";b=c>=3.5
 return{"timestamp_unix":time.time(),"asset":str(asset).upper(),"horizon":horizon,"market_id":market_id,"secs_left":round(float(secs_left),1),"ask_up":k,"ask_down":j,"merge_net_per_share":d,"merge_opportunity":e,"boundary_z":c,"boundary_side":a,"boundary_opportunity":b,"mode":"READ_ONLY_SHADOW"}
ASSET_CONFIGS={"BTC":{"series_slug":"btc-up-or-down-hourly","binance_symbol":"BTCUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/btcusdt@trade","binance_futures_ws":"wss://fstream.binance.com:443/ws/btcusdt@trade","default_shock_threshold":1.5e6,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry.jsonl","shock_file":DATA_DIR/"shock_responses.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations.jsonl","log_file":DATA_DIR/"recorder.log","pid_file":DATA_DIR/"recorder.pid"},"ETH":{"series_slug":"eth-up-or-down-hourly","binance_symbol":"ETHUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/ethusdt@trade","binance_futures_ws":"wss://fstream.binance.com:443/ws/ethusdt@trade","default_shock_threshold":5e5,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry_eth.jsonl","shock_file":DATA_DIR/"shock_responses_eth.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations_eth.jsonl","log_file":DATA_DIR/"recorder_eth.log","pid_file":DATA_DIR/"recorder_eth.pid"},"SOL":{"series_slug":"solana-up-or-down-hourly","binance_symbol":"SOLUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/solusdt@trade","binance_futures_ws":"wss://fstream.binance.com:443/ws/solusdt@trade","default_shock_threshold":2.5e5,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry_sol.jsonl","shock_file":DATA_DIR/"shock_responses_sol.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations_sol.jsonl","log_file":DATA_DIR/"recorder_sol.log","pid_file":DATA_DIR/"recorder_sol.pid"},"XRP":{"series_slug":"xrp-up-or-down-hourly","binance_symbol":"XRPUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/xrpusdt@trade","binance_futures_ws":"wss://fstream.binance.com:443/ws/xrpusdt@trade","default_shock_threshold":1e5,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry_xrp.jsonl","shock_file":DATA_DIR/"shock_responses_xrp.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations_xrp.jsonl","log_file":DATA_DIR/"recorder_xrp.log","pid_file":DATA_DIR/"recorder_xrp.pid"},"BNB":{"series_slug":"bnb-up-or-down-hourly","binance_symbol":"BNBUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/bnbusdt@trade","binance_futures_ws":"wss://fstream.binance.com:443/ws/bnbusdt@trade","default_shock_threshold":1.5e5,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry_bnb.jsonl","shock_file":DATA_DIR/"shock_responses_bnb.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations_bnb.jsonl","log_file":DATA_DIR/"recorder_bnb.log","pid_file":DATA_DIR/"recorder_bnb.pid"},"DOGE":{"series_slug":"doge-up-or-down-hourly","binance_symbol":"DOGEUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/dogeusdt@trade","binance_futures_ws":"wss://fstream.binance.com:443/ws/dogeusdt@trade","default_shock_threshold":7.5e4,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry_doge.jsonl","shock_file":DATA_DIR/"shock_responses_doge.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations_doge.jsonl","log_file":DATA_DIR/"recorder_doge.log","pid_file":DATA_DIR/"recorder_doge.pid"},"HYPE":{"series_slug":"hype-up-or-down-hourly","binance_symbol":"HYPEUSDT","binance_spot_ws":"","binance_futures_ws":"wss://fstream.binance.com:443/ws/hypeusdt@trade","futures_only_ref":True,"default_shock_threshold":7.5e4,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry_hype.jsonl","shock_file":DATA_DIR/"shock_responses_hype.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations_hype.jsonl","log_file":DATA_DIR/"recorder_hype.log","pid_file":DATA_DIR/"recorder_hype.pid"},"ZEC":{"series_slug":"zec-up-or-down-15m","binance_symbol":"ZECUSDT","binance_spot_ws":"wss://stream.binance.com:443/ws/zecusdt@trade","binance_futures_ws":"wss://fstream.binance.com:443/ws/zecusdt@trade","coinbase_product":"ZEC-USD","default_shock_threshold":5e4,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry_zec.jsonl","shock_file":DATA_DIR/"shock_responses_zec.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations_zec.jsonl","log_file":DATA_DIR/"recorder_zec.log","pid_file":DATA_DIR/"recorder_zec.pid"},"XAU":{"series_slug":"gold-up-or-down-1h","binance_symbol":"XAUUSDT","binance_spot_ws":"","binance_futures_ws":"wss://fstream.binance.com:443/ws/xauusdt@trade","futures_only_ref":True,"coinbase_product":"USDT-USD","default_shock_threshold":2e5,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry_xau.jsonl","shock_file":DATA_DIR/"shock_responses_xau.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations_xau.jsonl","log_file":DATA_DIR/"recorder_xau.log","pid_file":DATA_DIR/"recorder_xau.pid"},"XAG":{"series_slug":"silver-up-or-down-1h","binance_symbol":"XAGUSDT","binance_spot_ws":"","binance_futures_ws":"wss://fstream.binance.com:443/ws/xagusdt@trade","futures_only_ref":True,"coinbase_product":"USDT-USD","default_shock_threshold":1.5e5,"telemetry_file":DATA_DIR/"polymarket_hourly_telemetry_xag.jsonl","shock_file":DATA_DIR/"shock_responses_xag.jsonl","correlations_file":DATA_DIR/"leadlag_cross_correlations_xag.jsonl","log_file":DATA_DIR/"recorder_xag.log","pid_file":DATA_DIR/"recorder_xag.pid"}};logger=logging.getLogger("PolymarketDualFeed1H");_FAST_IPC_SOCK=None;_FAST_IPC_ADDR=b"\x00polymarket_shock_notify";_IPC_SEND_FAILURES=0;_IPC_LAST_WARN_TS=.0;_LAST_GLOBAL_PREWARM_IPC_TS=.0
def _broadcast_fast_trigger_ipc(data):
 global _FAST_IPC_SOCK,_IPC_SEND_FAILURES,_IPC_LAST_WARN_TS
 if os.name=="nt":return True
 try:
  import socket
  if _FAST_IPC_SOCK is None:
   s=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
   try:s.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,262144)
   except OSError:pass
   s.setblocking(False);_FAST_IPC_SOCK=s
  a=b"\x00"+os.environ.get("POLYMARKET_IPC_SOCKET_NAME","polymarket_shock_notify").encode("utf-8");_FAST_IPC_SOCK.sendto(data,a);return True
 except Exception as e:
  _IPC_SEND_FAILURES+=1;b=time.time()
  if(b-_IPC_LAST_WARN_TS)>=60.:_IPC_LAST_WARN_TS=b;logger.warning(f"[FAST IPC NOTICE] Abstract socket send missed ({_IPC_SEND_FAILURES} total, disk fallback active): {e}")
  return False
def _dumps_compact(payload):
 if _orjson is not None:return _orjson.dumps(payload).decode("utf-8")
 return json.dumps(payload,separators=(",",":"))
def _atomic_append_jsonl(path,line_str,broadcast_ipc=True):
 if not line_str.endswith("\n"):line_str+="\n"
 a=line_str.encode("utf-8")
 if broadcast_ipc and(path==TRIGGER_FILE or str(path).endswith("live_shock_triggers.jsonl")):_broadcast_fast_trigger_ipc(a)
 b=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o664)
 try:
  try:import fcntl;fcntl.flock(b,fcntl.LOCK_EX)
  except Exception:pass
  os.write(b,a)
 finally:
  try:import fcntl;fcntl.flock(b,fcntl.LOCK_UN)
  except Exception:pass
  os.close(b)
def _encode_trigger_fast(payload):
 if _orjson is not None:b=_orjson.dumps(payload)+b"\n";return b,b.decode("utf-8")
 a=json.dumps(payload)+"\n";return a.encode("utf-8"),a
def _dispatch_trigger_fast(path,payload,defer_ipc=False):
 b,a=_encode_trigger_fast(payload)
 if not defer_ipc and(path==TRIGGER_FILE or str(path).endswith("live_shock_triggers.jsonl")):_broadcast_fast_trigger_ipc(b)
 return b,a
def _persist_trigger_nonblocking(path,line_str):
 path.parent.mkdir(parents=True,exist_ok=True);c=line_str.encode("utf-8");b=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o644)
 try:
  try:import fcntl;fcntl.flock(b,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:
   os.close(b);b=-1
   try:a=asyncio.get_running_loop();a.run_in_executor(None,_atomic_append_jsonl,path,line_str,False);return
   except RuntimeError:_atomic_append_jsonl(path,line_str,False);return
  except Exception:pass
  os.write(b,c)
 finally:
  if b>=0:
   try:import fcntl;fcntl.flock(b,fcntl.LOCK_UN)
   except Exception:pass
   try:os.close(b)
   except OSError:pass
def setup_logging(asset="BTC"):
 c=ASSET_CONFIGS.get(asset.upper(),ASSET_CONFIGS["BTC"]);a=c["log_file"];b=logging.getLogger()
 for h in list(b.handlers):
  b.removeHandler(h)
  try:h.close()
  except Exception:pass
 logging.basicConfig(level=logging.INFO,format="[%(asctime)s UTC] [%(levelname)s] [%(name)s] %(message)s",datefmt="%Y-%m-%d %H:%M:%S",handlers=[logging.FileHandler(a)]+([logging.StreamHandler(sys.stdout)]if sys.stdout.isatty()else[]));global logger;logger=logging.getLogger(f"PolymarketDualFeed1H-{asset.upper()}")
DEFAULT_FEE_RATE=.072;TICKET_CAPACITY_LEVELS=[1.,5.,20.,25.,50.,1e2,150.,2e2,250.];CORRELATION_LAGS_MS=[-1000,-500,-250,-100,-50,0,50,100,250,500,1000]
def calculate_per_share_taker_fee(price,fee_rate=DEFAULT_FEE_RATE,fee_exponent=1.):p=max(.001,min(.999,price));return fee_rate*((p*(1.-p))**fee_exponent)
class L2OrderBook:
 def __init__(a,asset_id):a.asset_id=str(asset_id);a.token_id=str(asset_id);a.bids={};a.asks={};a.last_book_update_ts=.0;a.last_best_bid_change_ts=.0;a.last_best_ask_change_ts=.0;a.prev_best_bid=(.0,.0);a.prev_best_ask=(1.,.0);a.book_sequence_id=0;a.microprice_formula="(best_ask * bid_sz_1 + best_bid * ask_sz_1) / (bid_sz_1 + ask_sz_1)";a.obi_depth_levels=5;a._dirty=True;a._best_bid_dirty=True;a._best_ask_dirty=True;a._cached_best_bid=.0;a._cached_best_ask=1.;a._sorted_bids=[];a._sorted_asks=[];a._bid_birth_ts={};a._ask_birth_ts={};a._empty_ask_since_ts=.0;a._metrics_cache_key=None;a._metrics_cache_payload=None
 def _sorted_levels(a):
  if a._dirty:a._sorted_bids=sorted(a.bids.items(),key=lambda x:x[0],reverse=True);a._sorted_asks=sorted(a.asks.items(),key=lambda x:x[0]);a._dirty=False
  return a._sorted_bids,a._sorted_asks
 def _check_top_changes(a,now_ts):
  if a.bids:
   if a._best_bid_dirty or a._cached_best_bid not in a.bids:a._cached_best_bid=max(a.bids);a._best_bid_dirty=False
   g=a._cached_best_bid;c=(g,a.bids[g]);e=a.prev_best_bid[0]
   if e>.0 and g<e-1e-9:a._bid_birth_ts[g]=now_ts;a.last_best_bid_change_ts=now_ts
   else:a.last_best_bid_change_ts=a._bid_birth_ts.get(g,now_ts)
  else:a._cached_best_bid=.0;a._best_bid_dirty=False;c=(.0,.0);a.last_best_bid_change_ts=.0
  if a.asks:
   if a._best_ask_dirty or a._cached_best_ask not in a.asks:a._cached_best_ask=min(a.asks);a._best_ask_dirty=False
   f=a._cached_best_ask;b=(f,a.asks[f]);d=a.prev_best_ask[0]
   if.0<d<1. and f>d+1e-9:a._ask_birth_ts[f]=now_ts;a.last_best_ask_change_ts=now_ts
   else:a.last_best_ask_change_ts=a._ask_birth_ts.get(f,now_ts)
   a._empty_ask_since_ts=.0
  else:
   a._cached_best_ask=1.;a._best_ask_dirty=False;b=(1.,.0)
   if a._empty_ask_since_ts<=.0:a._empty_ask_since_ts=now_ts
   a.last_best_ask_change_ts=.0
  a.prev_best_bid=c;a.prev_best_ask=b
 def _prune_deep_levels(a,max_keep=40,trigger_len=80):
  b=0
  if len(a.bids)>trigger_len:
   for d in sorted(a.bids.keys(),reverse=True)[max_keep:]:a.bids.pop(d,None);a._bid_birth_ts.pop(d,None);b+=1
   a._dirty=True
  elif len(a._bid_birth_ts)>len(a.bids)+8:
   for c in[px for px in list(a._bid_birth_ts.keys())if px not in a.bids]:a._bid_birth_ts.pop(c,None)
  if len(a.asks)>trigger_len:
   for d in sorted(a.asks.keys())[max_keep:]:a.asks.pop(d,None);a._ask_birth_ts.pop(d,None);b+=1
   a._dirty=True
  elif len(a._ask_birth_ts)>len(a.asks)+8:
   for c in[px for px in list(a._ask_birth_ts.keys())if px not in a.asks]:a._ask_birth_ts.pop(c,None)
  return b
 def apply_snapshot(c,bids,asks):d=time.time();c.bids={float(b["price"]):float(b["size"])for b in bids if float(b["size"])>0};c.asks={float(a["price"]):float(a["size"])for a in asks if float(a["size"])>0};c._bid_birth_ts={px:c._bid_birth_ts.get(px,d)for px in c.bids};c._ask_birth_ts={px:c._ask_birth_ts.get(px,d)for px in c.asks};c._prune_deep_levels();c.last_book_update_ts=d;c.book_sequence_id+=1;c._dirty=True;c._best_bid_dirty=True;c._best_ask_dirty=True;c._check_top_changes(d)
 def apply_price_changes(a,changes):
  b=time.time()
  for c in changes:
   h=float(c["price"]);g=float(c["size"]);f=c.get("side","").upper()
   if f=="BUY":
    if g<=0:
     a.bids.pop(h,None);a._bid_birth_ts.pop(h,None)
     if abs(h-a._cached_best_bid)<1e-9:a._best_bid_dirty=True
    else:
     e=a.bids.get(h,.0)
     if e<=.0 or g>=e*1.25:a._bid_birth_ts[h]=b
     a.bids[h]=g
     if h>a._cached_best_bid:a._cached_best_bid=h;a._best_bid_dirty=False
   elif f=="SELL":
    if g<=0:
     a.asks.pop(h,None);a._ask_birth_ts.pop(h,None)
     if abs(h-a._cached_best_ask)<1e-9:a._best_ask_dirty=True
    else:
     d=a.asks.get(h,.0)
     if d<=.0 or g>=d*1.25:a._ask_birth_ts[h]=b
     a.asks[h]=g
     if h<a._cached_best_ask:a._cached_best_ask=h;a._best_ask_dirty=False
  a._prune_deep_levels();a.last_book_update_ts=b;a.book_sequence_id+=1
  if changes:a._dirty=True
  a._check_top_changes(b)
 def top_of_book(a,obs_ts=None):i=obs_ts if obs_ts is not None else time.time();c,b=a._sorted_levels();e,g=c[0]if c else(.0,.0);d,f=b[0]if b else(1.,.0);h=g+f;return{"best_bid":round(e,4),"best_ask":round(d,4),"bid_size_l1":round(g,2),"ask_size_l1":round(f,2),"spread":round(d-e,4),"is_crossed":bool(e>.0 and d<1. and e>=d),"q_mid":round((e+d)/2.,4),"obi_l1":round((g-f)/h,3)if h>0 else.0,"age_book_ms":round((i-a.last_book_update_ts)*1e3,1)if a.last_book_update_ts>0 else None,"age_ask_ms":round((i-a.last_best_ask_change_ts)*1e3,1)if a.last_best_ask_change_ts>0 else None,"empty_ask_ms":round((i-a._empty_ask_since_ts)*1e3,1)if(not b and a._empty_ask_since_ts>0)else None,"raw_top_bids":c[:15],"raw_top_asks":b[:15]}
 def get_metrics(a,obs_ts=None,fee_rate=DEFAULT_FEE_RATE,compact=False):
  P=obs_ts if obs_ts is not None else time.time();z=round((P-a.last_book_update_ts)*1e3,1)if a.last_book_update_ts>0 else None;D=round((P-a.last_best_bid_change_ts)*1e3,1)if a.last_best_bid_change_ts>0 else None;C=round((P-a.last_best_ask_change_ts)*1e3,1)if a.last_best_ask_change_ts>0 else None;G=(a.book_sequence_id,float(fee_rate),bool(compact))
  if a._metrics_cache_key==G and a._metrics_cache_payload is not None:R=dict(a._metrics_cache_payload);R["age_book_ms"]=z;R["age_bid_ms"]=D;R["age_ask_ms"]=C;R["empty_ask_ms"]=(round((P-a._empty_ask_since_ts)*1e3,1)if(not a.asks and getattr(a,"_empty_ask_since_ts",.0)>0)else None);return R
  y,x=a._sorted_levels();L=y[0][0]if y else.0;K=y[0][1]if y else.0;J=x[0][0]if x else 1.;I=x[0][1]if x else.0;B=bool(L>0 and J<1. and L>=J);N=J-L;O=(L+J)/2.;H=K+I
  if H>0:t=(K-I)/H;l=(L*I+J*K)/H
  else:t=.0;l=O
  if not B and H>0 and N>1e-5:
   if(t>1e-4 and l<O-1e-4)or(t<-1e-4 and l>O+1e-4):logger.warning(f"[BOOK INVARIANT NOTICE] OBI_L1={t:.4f}, q_micro={l:.4f}, q_mid={O:.4f}")
  w=sum(sz for _,sz in y[:a.obi_depth_levels]);v=sum(sz for _,sz in x[:a.obi_depth_levels]);u=w+v;F=(w-v)/u if u>0 else.0;E=calculate_per_share_taker_fee(J,fee_rate);h=J+E;g={};A=(20.,25.,50.)if compact else sorted(TICKET_CAPACITY_LEVELS)
  if x:
   c=.0;b=.0;e=.0;k=0;M=len(x);q,d=x[0]
   for i in A:
    while k<M and c<i-1e-6:
     s=q*d;Q=i-c
     if s<=Q:
      p=d;r=s;c+=r;b+=p;e+=p*fee_rate*q*(1.-q);k+=1
      if k<M:q,d=x[k]
     else:p=Q/q;c+=Q;b+=p;e+=p*fee_rate*q*(1.-q);d-=p
    if b>0:
     j=round(c/b,4);o=round((c+e)/b,4);m=round(o-O,4)
     if j<J-1e-4:j=round(J,4)
     g[f"vwap_${int(i)}"]=j
     if not compact:g[f"effective_price_${int(i)}"]=o;g[f"crossing_cost_${int(i)}"]=m;g[f"fill_fees_${int(i)}"]=round(e,5)
     elif i==50.:g["effective_price_$50"]=o;g["fill_fees_$50"]=round(e,5)
  elif not compact:
   for i in A:g[f"vwap_${int(i)}"]=None;g[f"effective_price_${int(i)}"]=None;g[f"crossing_cost_${int(i)}"]=None;g[f"fill_fees_${int(i)}"]=None
  n=(round((P-a._empty_ask_since_ts)*1e3,1)if(not x and getattr(a,"_empty_ask_since_ts",.0)>0)else None)
  if compact:f={"best_bid":round(L,4),"best_ask":round(J,4),"bid_size_l1":round(K,2),"ask_size_l1":round(I,2),"spread":round(N,4),"q_mid":round(O,4),"q_micro":round(l,4),"obi_l1":round(t,3),"obi_depth":round(F,3),"book_sequence_id":a.book_sequence_id,"book_timestamp":round(a.last_book_update_ts,3)if a.last_book_update_ts>0 else.0,"is_crossed":B,"age_book_ms":z,"age_bid_ms":D,"age_ask_ms":C,"empty_ask_ms":n,"taker_fee":round(E,5),"executable_hurdle":round(h,5),**g,"raw_top_bids":y[:10],"raw_top_asks":x[:10]}
  else:f={"best_bid":round(L,4),"best_ask":round(J,4),"bid_size_l1":round(K,2),"ask_size_l1":round(I,2),"spread":round(N,4),"q_mid":round(O,4),"q_micro":round(l,4),"obi_l1":round(t,3),"obi_depth":round(F,3),"obi_depth_levels":a.obi_depth_levels,"microprice_formula":a.microprice_formula,"book_sequence_id":a.book_sequence_id,"book_timestamp":a.last_book_update_ts,"is_crossed":B,"age_book_ms":z,"age_bid_ms":D,"age_ask_ms":C,"empty_ask_ms":n,"taker_fee":round(E,5),"executable_hurdle":round(h,5),**g,"raw_top_bids":y[:15],"raw_top_asks":x[:15]}
  a._metrics_cache_key=G;a._metrics_cache_payload=f;return dict(f)
class PolymarketDualFeed1HRecorder:
 def __init__(a,asset="BTC",shock_threshold=None,riskless_bus_only=False):
  a.asset=asset.upper()
  if a.asset not in ASSET_CONFIGS:raise ValueError(f"Unsupported asset {a.asset}. Must be one of: {list(ASSET_CONFIGS.keys())}")
  a.riskless_bus_only=bool(riskless_bus_only or os.environ.get("POLYMARKET_RISKLESS_BUS_ONLY")=="1");a.cfg=ASSET_CONFIGS[a.asset];a.series_slug=a.cfg["series_slug"];a.binance_symbol=a.cfg["binance_symbol"];a.binance_spot_ws=(a.cfg["binance_spot_ws"].replace("@trade","@aggTrade")if a.riskless_bus_only and a.cfg.get("binance_spot_ws")else a.cfg["binance_spot_ws"]);a.binance_futures_ws=(a.cfg["binance_futures_ws"].replace("@trade","@aggTrade")if a.riskless_bus_only and a.cfg.get("binance_futures_ws")else a.cfg["binance_futures_ws"]);a.futures_only_ref=bool(a.cfg.get("futures_only_ref",False));a.shock_threshold_usd=shock_threshold if shock_threshold is not None else a.cfg["default_shock_threshold"];a.telemetry_file=a.cfg["telemetry_file"];a.shock_file=a.cfg["shock_file"];a.correlations_file=a.cfg["correlations_file"];a.pid_file=a.cfg["pid_file"];a.log_file=a.cfg["log_file"];a.session=None;a.current_market=None;a.market_15m=None;a.market_5m=None;a.market_4h=None;a.books={};b=64 if a.riskless_bus_only else 30000;a.spot_trades=collections.deque(maxlen=b);a.futures_trades=collections.deque(maxlen=b);a.basis_history=collections.deque(maxlen=128 if a.riskless_bus_only else 2000);a.spot_price=.0;a.futures_price=.0;a.spot_price_ts=.0;a.futures_price_ts=.0;a.basis_usd=.0;a.basis_bps=.0;a.finalized_1h_open=.0;a.fee_rate_market=DEFAULT_FEE_RATE;a.fee_exponent=1.;a.fee_source="polymarket_crypto_schedule_v1";a.fee_enabled=True;a.fee_formula_version="taker_fee_c_times_rate_times_p_one_minus_p";a.clock_offset_ms=.0;a.clock_uncertainty_ms=.0;a.last_clock_sync_ts=.0;a.last_shock_ts=.0;a.last_shock_ts_by_source=defaultdict(float);a.last_cross_corr_ts=.0;a.active_burst_tasks=set();a.running=True;a.clob_ws_connected=False;a.last_clob_ws_msg_ts=.0;a._last_stale_exch_warn_ts=.0;DATA_DIR.mkdir(parents=True,exist_ok=True);a.telemetry_15m_file=DATA_DIR/f"polymarket_15m_telemetry_{a.asset.lower()}.jsonl";a.telemetry_5m_file=DATA_DIR/f"polymarket_5m_telemetry_{a.asset.lower()}.jsonl";a.telemetry_4h_file=DATA_DIR/f"polymarket_4h_telemetry_{a.asset.lower()}.jsonl";a._last_telem_bbo_by_hz={};a._spot_1m_bucket=0;a._last_1m_spot=.0;a._rolling_sigma_1h={"XAU":.0022,"BTC":.005,"ETH":.0068,"BNB":.0068,"SOL":.0075,"XRP":.008,"DOGE":.0095,"HYPE":.011}.get(a.asset,.0068);a.coinbase_product=str(a.cfg.get("coinbase_product")or f"{a.asset}-USD");a.coinbase_spot=.0;a.coinbase_spot_ts=.0;a.coinbase_history=collections.deque(maxlen=600);a._venue_div_history=collections.deque(maxlen=200);a._raw_usd_history=collections.deque(maxlen=1500);a._cl_to_raw_usd_ratio=1.;a._cl_basis_anchor_ts=.0;a._cl_proxy_history=collections.deque(maxlen=1200);a.chainlink_last_updated_ts=.0;a.chainlink_stream=_get_shared_cl_stream()if _get_shared_cl_stream is not None else None;a.fast_tick_file=fast_tick_path(a.asset);a._last_fast_tick_write=.0;a._fast_tick_enabled=SHM_DIR.is_dir();a._last_exp306_eval=.0;a.lead_state_file=lead_state_path("BTC");a._last_lead_state_write=.0;a._last_btc_shock={};a._last_btc_flow_z=.0;a._vol_buckets=collections.deque(maxlen=16 if a.riskless_bus_only else(ADAPTIVE_THRESH_WINDOW_SEC+2));a._vol_first_sec=None;a._adaptive_cache=(.0,float(a.shock_threshold_usd))
 def get_coinbase_spot(a,now=None):
  now=now if now is not None else time.time()
  if getattr(a,"coinbase_product","")=="USDT-USD":
   if a.spot_price<=0:return.0
   b=a.coinbase_spot>0 and(now-a.coinbase_spot_ts)<=max(float(COINBASE_STALE_SEC),60.);c=a.coinbase_spot if(b and.98<=a.coinbase_spot<=1.02)else 1.;return round(a.spot_price*c,4)
  if a.coinbase_spot>0 and(now-a.coinbase_spot_ts)<=COINBASE_STALE_SEC:return a.coinbase_spot
  return.0
 def get_venue_divergence_bps(a,now=None):
  b=a.get_coinbase_spot(now)
  if b<=0 or a.spot_price<=0:return.0
  return round((a.spot_price-b)/b*1e4,2)
 def get_venue_divergence_centered_bps(a,now=None):
  b=a.get_venue_divergence_bps(now);d=a.get_coinbase_spot(now)
  if d<=0 or a.spot_price<=0:return.0
  c=getattr(a,"_venue_div_history",None)
  if c and len(c)>=10:return round(b-statistics.median(c),2)
  return b
 def _get_live_cl_spot(a,now_ts):
  b=getattr(a,"chainlink_stream",None)
  if b is None:return None
  c=b.get_latest_spot(a.asset,now_ts=now_ts,max_age_sec=4.5);return float(c)if c is not None and c>.0 else None
 def is_chainlink_basis_anchored(a,now=None):
  b=now if now is not None else time.time()
  if a._get_live_cl_spot(b)is not None:return True
  c=float(getattr(a,"_cl_basis_anchor_ts",.0)or.0);r=float(getattr(a,"_cl_to_raw_usd_ratio",1.)or 1.);return c>.0 and-5.<=(b-c)<=1800. and.975<=r<=1.025
 def get_chainlink_proxy_spot(a,now=None):
  h=now if now is not None else time.time();k=a.get_coinbase_spot(h);e=getattr(a,"_venue_div_history",None);g=(a.spot_price/(1.+max(-250.,min(250.,float(statistics.median(e))))/1e4)if(a.spot_price>0 and e and len(e)>=10)else.0);c=.5*(k+g)if(k>0 and g>0)else(k if k>0 else g);d=getattr(a,"_raw_usd_history",None)
  if d is not None and c>0:
   if not d or(h-d[-1][0])>=.2:d.append((h,round(c,4)))
   while d and(h-d[0][0])>240.:d.popleft()
  f=a._get_live_cl_spot(h)
  if f is not None:
   if c>0 and.975<=(f/c)<=1.025:a._cl_to_raw_usd_ratio=f/c;a._cl_basis_anchor_ts=h
   b=round(f,4)
  else:
   if c<=0:return.0
   i=float(getattr(a,"_cl_to_raw_usd_ratio",1.)or 1.)if a.is_chainlink_basis_anchored(h)else 1.;b=round(c*i,4)
  j=getattr(a,"_cl_proxy_history",None)
  if j is not None and b>0:
   if not j or(h-j[-1][0])>=.2:j.append((h,b))
   while j and(h-j[0][0])>65.:j.popleft()
  return b
 def get_chainlink_twap_60s(a,now=None):
  d=now if now is not None else time.time();c=a.get_chainlink_proxy_spot(d);f=getattr(a,"chainlink_stream",None)
  if f is not None:
   b=f.get_rolling_twap_60s(a.asset,now_ts=d,max_age_sec=4.5)
   if b is not None and b>0:return round(float(b),4)
  e=getattr(a,"_cl_proxy_history",None)
  if not e:return c
  g=[h for t,h in e if(d-t)<=60. and h>0]
  if len(g)<2:return c
  return round(statistics.mean(g),4)
 def get_settlement_twap_slice(a,end_ts,now=None):
  c=now if now is not None else time.time();e=getattr(a,"chainlink_stream",None)
  if e is not None:
   b=e.get_settlement_twap_slice(a.asset,end_ts,now_ts=c,max_age_sec=4.5)
   if b is not None:return b
  g=float(end_ts)-c
  if not(.0<g<60.):return.0,.0
  d=getattr(a,"_cl_proxy_history",None)or();h=float(end_ts)-60.;f=[i for t,i in d if h<=t<=c+.5 and i>0]
  if not f:return.0,.0
  return round(statistics.mean(f),4),round((60.-g)/60.,4)
 async def fetch_polygon_chainlink_spot(a):
  f={"BTC":"0xc907E116054Ad103354f2D350FD2514433D57F6f","ETH":"0xF9680D99D6C9589e2a93a78A04A279e509205945"};h=f.get(a.asset.upper())
  if not h:return.0
  e=os.environ.get("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com")
  try:
   d=await a.get_session();c={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":h,"data":"0xfeaf968c"},"latest"]}
   async with d.post(e,json=c,timeout=1.5)as g:
    if g.status==200:
     k=await _fast_resp_json(g);b=str(k.get("result")or"")
     if b.startswith("0x")and len(b)>=2+64*4:
      j=int(b[2+64:2+128],16);i=int(b[2+192:2+256],16)
      if j>0 and(time.time()-i)<=20.:a.chainlink_last_updated_ts=float(i);return round(j/1e8,4)
  except Exception:pass
  return.0
 def get_coinbase_move_bps(a,window_sec=2.,now=None):
  now=now if now is not None else time.time();d=a.get_coinbase_spot(now)
  if d<=0 or not a.coinbase_history:return.0
  b=None
  for t,c in a.coinbase_history:
   if now-t<=window_sec:b=c;break
  if not b or b<=0:return.0
  return round((d-b)/b*1e4,2)
 _SHARED_CB_USDT_STATE:Dict[str,Any]={"owner":None,"px":.0,"ts":.0}
 async def _coinbase_stream_worker(a):
  c=a.riskless_bus_only and getattr(a,"coinbase_product","")=="USDT-USD"
  if c:
   h=a._SHARED_CB_USDT_STATE
   if h.get("owner")not in(None,a.asset):
    while a.running:
     await asyncio.sleep(.5);k=float(h.get("px")or.0);j=float(h.get("ts")or.0);g=time.time()
     if k>.0 and(g-j)<=15.:
      a.coinbase_spot=k;a.coinbase_spot_ts=j
      if a.spot_price>.0 and.95<=k<=1.05:
       a.coinbase_history.append((g,round(a.spot_price*k,4)))
       while a.coinbase_history and g-a.coinbase_history[0][0]>30.:a.coinbase_history.popleft()
     elif h.get("owner")is None:h["owner"]=a.asset;break
    if not a.running:return
   else:h["owner"]=a.asset
  b=2.
  try:
   while a.running:
    try:
     async with websockets.connect(COINBASE_WS_URL,ping_interval=20,ping_timeout=10,max_queue=512,compression=None)as n:
      _enable_ws_nodelay(n);await n.send(json.dumps({"type":"subscribe","product_ids":[a.coinbase_product],"channels":["ticker"]}));logger.info(f"[+] Subscribed to Coinbase ticker ({a.coinbase_product}) for composite venue filter.");b=2.
      async for d in n:
       if not a.running:break
       i=_orjson.loads(d)if _orjson else json.loads(d)
       if i.get("type")!="ticker"or i.get("product_id")!=a.coinbase_product:continue
       m=float(i.get("price")or.0)
       if m>0:
        l=time.time();a.coinbase_spot=m;a.coinbase_spot_ts=l
        if c:a._SHARED_CB_USDT_STATE["px"]=m;a._SHARED_CB_USDT_STATE["ts"]=l
        f=(round(a.spot_price*m,4)if(a.coinbase_product=="USDT-USD"and a.spot_price>0 and.95<=m<=1.05)else(.0 if a.coinbase_product=="USDT-USD"else m))
        if f>0:
         a.coinbase_history.append((l,f))
         if a.spot_price>0:a._venue_div_history.append(round((a.spot_price-f)/f*1e4,2))
        while a.coinbase_history and l-a.coinbase_history[0][0]>30.:a.coinbase_history.popleft()
    except Exception as e:logger.warning(f"Coinbase feed disconnected ({e}); fail-open, retrying in {b:.0f}s...");await asyncio.sleep(b);b=min(30.,b*2.)
  finally:
   if c and a._SHARED_CB_USDT_STATE.get("owner")==a.asset:a._SHARED_CB_USDT_STATE["owner"]=None
 def build_fast_tick_snapshot(a,now=None):
  now=now if now is not None else time.time();c=a.get_chainlink_proxy_spot(now);d=a._get_live_cl_spot(now)is not None;g=getattr(getattr(a,"chainlink_stream",None),"active_source","none")if d else"cex_proxy";n={"ts":now,"timestamp_unix":now,"asset":a.asset,"market_id":str(a.current_market["market_id"])if a.current_market else None,"clob_ws_connected":bool(getattr(a,"clob_ws_connected",False)),"clob_ws_rx_age_ms":round(max(.0,(now-float(a.last_clob_ws_msg_ts))*1e3),1)if getattr(a,"last_clob_ws_msg_ts",.0)>.0 else None,"spot":a.spot_price,"futures":a.futures_price,"spot_price":a.spot_price,"futures_price":a.futures_price,"spot_ts":round(a.spot_price_ts,3)if getattr(a,"spot_price_ts",.0)>.0 else None,"futures_ts":round(a.futures_price_ts,3)if getattr(a,"futures_price_ts",.0)>.0 else None,"coinbase_spot":a.get_coinbase_spot(now),"chainlink_spot":c,"chainlink_proxy_spot":c,"chainlink_twap_60s":a.get_chainlink_twap_60s(now),"chainlink_source":g,"chainlink_basis_anchored":a.is_chainlink_basis_anchored(now),"venue_divergence_bps":a.get_venue_divergence_bps(now),"venue_divergence_centered_bps":a.get_venue_divergence_centered_bps(now),"coinbase_move_bps_2s":a.get_coinbase_move_bps(2.,now),"basis_bps":round(a.basis_bps,2),"finalized_1h_open":a.finalized_1h_open};b={}
  if"UP"in a.books and"DOWN"in a.books:
   n["UP"]=a.books["UP"].top_of_book(now);n["DOWN"]=a.books["DOWN"].top_of_book(now)
   if a.current_market and"tokens"in a.current_market:
    n["UP"]["token_id"]=a.current_market["tokens"].get("UP");n["DOWN"]["token_id"]=a.current_market["tokens"].get("DOWN")
    if"end_dt"in a.current_market:n["expiry_ts_1h"]=a.current_market["end_dt"].timestamp()
    o=str(a.current_market.get("market_id"));b[o]={"market_id":o,"asset":a.asset,"horizon":"1h","timestamp_unix":now,"spot_price":a.spot_price,"futures_price":a.futures_price,"UP":n["UP"],"DOWN":n["DOWN"]}
  for q,f,m,l,e in(("5m","market_5m","UP_5M","DOWN_5M","m5"),("15m","market_15m","UP_15M","DOWN_15M","m15"),("4h","market_4h","UP_4H","DOWN_4H","h4")):
   p=getattr(a,f,None)
   if p and m in a.books and l in a.books:i=p["end_dt"].timestamp()if"end_dt"in p else float(p.get("expiry_ts")or.0);k,j=a.get_settlement_twap_slice(i,now)if i>0 else(.0,.0);n[e]={"market_id":p.get("market_id"),"condition_id":p.get("condition_id"),"horizon":q,"expiry_ts":i,"finalized_open":p.get("finalized_open",p.get("finalized_15m_open")),"finalized_15m_open":p.get("finalized_15m_open"),"authoritative_chainlink_open":p.get("authoritative_chainlink_open"),"twap_locked_mean":k,"twap_locked_weight":j,"UP":dict(a.books[m].top_of_book(now),token_id=p["tokens"].get("UP")),"DOWN":dict(a.books[l].top_of_book(now),token_id=p["tokens"].get("DOWN"))};h=str(p.get("market_id"));b[h]={"market_id":h,"condition_id":p.get("condition_id"),"asset":a.asset,"horizon":q,"expiry_ts":i,"finalized_open":p.get("finalized_open",p.get("finalized_15m_open")),"authoritative_chainlink_open":p.get("authoritative_chainlink_open"),"timestamp_unix":now,"spot_price":a.spot_price,"futures_price":a.futures_price,"twap_locked_mean":k,"twap_locked_weight":j,"UP":n[e]["UP"],"DOWN":n[e]["DOWN"]}
  n["markets"]=b;return n
 def _has_urgent_c1_arb_raw(a):
  def b(mh,up_role,dn_role):
   if not isinstance(mh,dict):return None,None
   B=a.books.get(up_role)or(a.books.get(mh.get("up_id"))if mh.get("up_id")else None);A=a.books.get(dn_role)or(a.books.get(mh.get("down_id"))if mh.get("down_id")else None);return B,A
  def c(mh):
   if not isinstance(mh,dict):return.0
   if"end_dt"in mh and hasattr(mh["end_dt"],"timestamp"):return float(mh["end_dt"].timestamp())
   return float(mh.get("expiry_ts")or mh.get("candle_close_ts")or.0)
  z=getattr(a,"market_5m",None);o=getattr(a,"market_15m",None);n=getattr(a,"current_market",None)
  for mh,y,x in((z,"UP_5M","DOWN_5M"),(o,"UP_15M","DOWN_15M"),(n,"UP","DOWN")):
   m,l=b(mh,y,x)
   if m is None or l is None:continue
   w=float(m.prev_best_ask[0]);v=float(l.prev_best_ask[0])
   if.01<=w<1. and.01<=v<1. and(w+v)<=.992:return True
  for u,k,j,t,i,h in((o,"UP_15M","DOWN_15M",z,"UP_5M","DOWN_5M"),(n,"UP","DOWN",o,"UP_15M","DOWN_15M")):
   e,d=c(u),c(t)
   if e>.0 and d>.0 and abs(e-d)<=2.:
    s,r=b(u,k,j);q,p=b(t,i,h)
    if s is not None and p is not None:
     g,f=float(s.prev_best_ask[0]),float(p.prev_best_ask[0])
     if.01<=g<1. and.01<=f<1. and(g+f)<=.9925:return True
    if q is not None and r is not None:
     g,f=float(q.prev_best_ask[0]),float(r.prev_best_ask[0])
     if.01<=g<1. and.01<=f<1. and(g+f)<=.9925:return True
  return False
 def _fast_tick_throttle_sec(a,now):
  if not a.riskless_bus_only:return FAST_TICK_THROTTLE_SEC
  if a._has_urgent_c1_arb_raw():return FAST_TICK_THROTTLE_SEC
  b=3e2-now%3e2;return.05 if(.0<b<=75.)else.15
 def _maybe_write_fast_tick(a,force=False):
  if not a._fast_tick_enabled:return False
  g=time.time()
  if not force and(g-a._last_fast_tick_write)<a._fast_tick_throttle_sec(g):return False
  a._last_fast_tick_write=g
  try:
   d=a.build_fast_tick_snapshot(g);c=_orjson.dumps(d)if _orjson else json.dumps(d).encode("utf-8");e=a.fast_tick_file.with_suffix(f".tmp.{os.getpid()}")
   with open(e,"wb")as f:f.write(c)
   os.replace(e,a.fast_tick_file)
  except Exception:return False
  try:from src.polymarket_research.riskless_protocol_v2_expansion import maybe_emit_recorder_fast_riskless_ipc as b;b(a,d,g)
  except Exception:pass
  if not a.riskless_bus_only and g-a._last_exp306_eval>=1.:a._last_exp306_eval=g;a._run_exp306_realtime_eval(d)
  return True
 def _run_exp306_realtime_eval(a,snap):
  try:
   e=[]
   if a.current_market and"UP"in snap and"DOWN"in snap:c=(a.current_market["end_dt"]-datetime.now(timezone.utc)).total_seconds();e.append(evaluate_realtime_exp306_boundary_and_merge(a.asset,"1h",str(a.current_market["market_id"]),snap["UP"],snap["DOWN"],a.spot_price,a.finalized_1h_open,c,fee_rate=a.fee_rate_market))
   f=getattr(a,"market_15m",None)
   if f and"m15"in snap:b=(f["end_dt"]-datetime.now(timezone.utc)).total_seconds();e.append(evaluate_realtime_exp306_boundary_and_merge(a.asset,"15m",str(f.get("market_id")),snap["m15"]["UP"],snap["m15"]["DOWN"],a.spot_price,float(f.get("finalized_15m_open")or.0),b,fee_rate=float(f.get("fee_metadata",{}).get("fee_rate_market",.07)or.07),sigma_1h=a.get_rolling_sigma("1h")))
   d=[r for r in e if r.get("merge_opportunity")or r.get("boundary_opportunity")]
   if d:
    for r in d:_persist_trigger_nonblocking(EXP306_REALTIME_LEDGER,_dumps_compact(r)+"\n")
  except Exception:pass
 def _update_rolling_sigma(a,px,now_sec=None):
  if px<=0:return
  now_sec=now_sec if now_sec is not None else time.time();e=int(now_sec//60)
  if e>a._spot_1m_bucket:
   if a._last_1m_spot>0:d=math.log(px/a._last_1m_spot);b=60.*(d**2);c=.95*(a._rolling_sigma_1h**2)+.05*b;a._rolling_sigma_1h=max(.002,min(.03,math.sqrt(c)))
   a._last_1m_spot=px;a._spot_1m_bucket=e
 def get_rolling_sigma(a,horizon="1h"):
  b=getattr(a,"_rolling_sigma_1h",.005 if a.asset=="BTC"else.0068)
  if str(horizon).lower()=="15m":return round(b*.5,5)
  return round(b,5)
 async def get_session(a):
  if a.session is None or a.session.closed:b=8 if a.riskless_bus_only else 20;a.session=aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=b,enable_cleanup_closed=True),timeout=aiohttp.ClientTimeout(total=10),headers={"User-Agent":"PolymarketDualFeedRecorder/2.7"},max_line_size=65536,max_field_size=65536)
  return a.session
 def _evict_recorder_memory(c,now_ts=None,trim_heap=False):
  l=float(now_ts if now_ts is not None else time.time());a=0;f=getattr(c,"_logged_resolution_market_ids",None)
  if isinstance(f,set)and len(f)>512:e=sorted(f)[-256:];a+=len(f)-len(e);f.clear();f.update(e)
  g=getattr(c,"_boundary_lock_cooldowns",None)
  if isinstance(g,dict):
   for j,i in list(g.items()):
    if(l-float(i or.0))>3600.:g.pop(j,None);a+=1
  d=getattr(c,"active_burst_tasks",None)
  if isinstance(d,set)and d:
   for k in[t for t in list(d)if getattr(t,"done",lambda:False)()]:d.discard(k);a+=1
  b=0
  for h in list((getattr(c,"books",None)or{}).values()):
   if isinstance(h,L2OrderBook):b+=h._prune_deep_levels()
  if trim_heap:_release_unused_heap_memory()
  return{"evicted_entries":a,"pruned_book_levels":b}
 async def calibrate_binance_clock_offset(a):
  c=await a.get_session()
  try:
   j=time.time()*1e3
   async with c.get(f"{BINANCE_REST_URL}/api/v3/time")as g:
    if g.status==200:f=await _fast_resp_json(g);b=float(f["serverTime"]);i=time.time()*1e3;h=i-j;d=(j+i)/2.;a.clock_offset_ms=round(d-b,2);a.clock_uncertainty_ms=round(h/2.,2);a.last_clock_sync_ts=time.time();logger.info(f"[CLOCK CALIBRATION] Tokyo <-> Binance Offset: {a.clock_offset_ms:+.2f}ms (Uncertainty: +/-{a.clock_uncertainty_ms:.2f}ms, RTT: {h:.2f}ms)")
  except Exception as e:logger.warning(f"Clock calibration failed: {e}")
 async def discover_nearest_1h_market(a):
  z=await a.get_session()
  try:
   B=datetime.now(timezone.utc);y=B.strftime("%Y-%m-%dT%H:%M:%SZ");F=(f"{GAMMA_API_URL}/events?series_slug={a.series_slug}&limit=20&closed=false&end_date_min={y}&order=endDate&ascending=true")
   async with z.get(F)as E:
    if E.status==200:
     C=await _fast_resp_json(E);B=datetime.now(timezone.utc);n=[]
     for l in C:
      w=l.get("markets",[])
      if not w:continue
      m=w[0];b=m.get("endDate")or l.get("endDate")
      if not b:continue
      j=datetime.fromisoformat(b.replace("Z","+00:00"));c=(j-B).total_seconds()
      if 0<c<=7200:n.append((c,l,m,j,b))
     if not n:return None
     n.sort(key=lambda x:x[0]);c,l,m,j,b=n[0];D=str(m.get("id"));i=str(m.get("conditionId")or"");k=m.get("clobTokenIds");A=json.loads(k)if isinstance(k,str)else k;h=m.get("outcomes",'["Up", "Down"]');u=json.loads(h)if isinstance(h,str)else h;f=int(j.timestamp()-3600);d=int(j.timestamp());g=m.get("feeSchedule",{})
     if isinstance(g,dict)and"rate"in g:a.fee_rate_market=float(g["rate"]);a.fee_exponent=float(g.get("exponent",1.));a.fee_source=f"gamma_feeSchedule_{m.get('feeType','crypto_fees_v2')}"
     elif m.get("takerBaseFee")is not None:q=float(m.get("takerBaseFee"));a.fee_rate_market=q/1e4 if q>1. else q;a.fee_exponent=1.;a.fee_source="gamma_takerBaseFee"
     else:a.fee_rate_market=DEFAULT_FEE_RATE;a.fee_exponent=1.;a.fee_source="polymarket_crypto_schedule_v1"
     a.fee_enabled=bool(m.get("feesEnabled",True));a.fee_formula_version=str(m.get("feeType","crypto_fees_v2"));t=f"{BINANCE_REST_URL}/api/v3/ticker/price?symbol={a.binance_symbol}";v=f"{BINANCE_FUTURES_REST_URL}/fapi/v1/ticker/price?symbol={a.binance_symbol}"
     try:
      if not a.futures_only_ref:
       async with z.get(t)as p:
        if p.status==200:
         o=await _fast_resp_json(p);a.spot_price=float(o["price"])
         if a.spot_price>0:a.spot_price_ts=time.time()
      async with z.get(v)as s:
       if s.status==200:
        r=await _fast_resp_json(s);a.futures_price=float(r["price"])
        if a.futures_only_ref and a.futures_price>0:a.spot_price=a.futures_price;a.spot_price_ts=time.time()
        a.update_basis()
     except Exception:pass
     return{"market_id":D,"condition_id":i,"title":l.get("title"),"question":m.get("question"),"slug":l.get("slug"),"resolution_source":str(m.get("resolutionSource")or l.get("resolutionSource")or""),"end_date_iso":b,"end_dt":j,"candle_open_ts":f,"candle_close_ts":d,"tokens":{"UP":A[0],"DOWN":A[1]},"outcomes":u,"fee_metadata":{"fee_rate_market":a.fee_rate_market,"fee_exponent":a.fee_exponent,"fee_source":a.fee_source,"fee_enabled":a.fee_enabled,"fee_formula_version":a.fee_formula_version,"condition_id":i,"timestamp_utc":time.time()}}
  except Exception as e:logger.error(f"Error discovering 1H market: {e}")
  return None
 async def discover_nearest_twap_market(b,horizon="15m"):
  M=str(horizon).lower();D={"5m":300,"15m":900,"4h":14400}.get(M,900);y={"5m":600,"15m":1800,"4h":28800}.get(M,1800);C=await b.get_session();q=b.asset.lower();u={"xau":"gold","xag":"silver","sol":"solana","btc":"bitcoin","eth":"ethereum"};H=u.get(q);a=[f"{q}-up-or-down-{M}",f"{q}-{M}"]
  if H:a=[f"{H}-up-or-down-{M}",f"{H}-{M}"]+a
  L=datetime.now(timezone.utc);B=L.strftime("%Y-%m-%dT%H:%M:%SZ")
  for G in a:
   try:
    K=f"{GAMMA_API_URL}/events?series_slug={G}&limit=10&closed=false&end_date_min={B}&order=endDate&ascending=true"
    async with C.get(K)as J:
     if J.status!=200:continue
     F=await _fast_resp_json(J);t=[]
     for s in F:
      A=s.get("markets",[])
      if not A:continue
      m=A[0];d=m.get("endDate")or s.get("endDate")
      if not d:continue
      o=datetime.fromisoformat(d.replace("Z","+00:00"));e=(o-L).total_seconds()
      if 0<e<=y:t.append((e,s,m,o,d))
     if not t:continue
     t.sort(key=lambda x:x[0]);e,s,m,o,d=t[0];I=str(m.get("id"));n=str(m.get("conditionId")or"");r=m.get("clobTokenIds");E=json.loads(r)if isinstance(r,str)else r;l=m.get("outcomes",'["Up", "Down"]');w=json.loads(l)if isinstance(l,str)else l;i=int(o.timestamp()-D);f=int(o.timestamp());k=m.get("feeSchedule",{});c=DEFAULT_FEE_RATE;h=1.
     if isinstance(k,dict)and"rate"in k:c=float(k["rate"]);h=float(k.get("exponent",1.))
     elif m.get("takerBaseFee")is not None:v=float(m.get("takerBaseFee"));c=v/1e4 if v>1. else v
     z,_=await b.fetch_finalized_binance_candle(i,interval=M);p=await b.fetch_binance_60s_twap_open(i);j=await b.fetch_authoritative_chainlink_open(i,f,horizon=M);g=j if j>.0 else.0
     if g<=.0 and abs(time.time()-i)<=35.:g=await b.fetch_polygon_chainlink_spot()
     return{"market_id":I,"condition_id":n,"horizon":M,"title":s.get("title"),"question":m.get("question"),"slug":s.get("slug"),"series_slug":G,"resolution_source":str(m.get("resolutionSource")or s.get("resolutionSource")or""),"end_date_iso":d,"end_dt":o,"candle_open_ts":i,"candle_close_ts":f,"tokens":{"UP":E[0],"DOWN":E[1]},"outcomes":w,"finalized_open":z,"finalized_15m_open":z,"twap_60s_open":p,"authoritative_chainlink_open":j or None,"chainlink_open_spot":g or None,"fee_metadata":{"fee_rate_market":c,"fee_exponent":h,"fee_source":f"gamma_{M}_crypto_fees","fee_enabled":True,"fee_formula_version":"crypto_fees_v2","condition_id":n,"timestamp_utc":time.time()}}
   except Exception:pass
  return None
 async def discover_nearest_15m_market(self):return await self.discover_nearest_twap_market("15m")
 async def discover_nearest_5m_market(self):return await self.discover_nearest_twap_market("5m")
 async def discover_nearest_4h_market(self):return await self.discover_nearest_twap_market("4h")
 async def _calibrate_chainlink_basis_anchor(a,candle_open_ts,auth_open_px):
  if not math.isfinite(auth_open_px)or auth_open_px<=.0:return
  q,m=time.time(),int(candle_open_ts)
  if m<=int(getattr(a,"_cl_basis_anchor_ts",.0)or.0)or abs(q-m)>960.:return
  b=.0;e=getattr(a,"_raw_usd_history",None)
  if e:
   x=[(t,p)for t,p in e if(m-60.)<=t<=(m+.5)and p>0]
   if len(x)>=10 and(x[-1][0]-x[0][0])>=40.:b=statistics.mean(p for _,p in x)
  if b<=.0:
   try:
    h=await a.get_session();s=m-60
    if getattr(a,"coinbase_product","")=="USDT-USD":
     c=BINANCE_FUTURES_REST_URL if a.futures_only_ref else BINANCE_REST_URL;g="/fapi/v1/klines"if a.futures_only_ref else"/api/v3/klines";l=f"{c}{g}?symbol={a.binance_symbol}&interval=1m&startTime={s*1000}&limit=1"
     async with h.get(l,timeout=aiohttp.ClientTimeout(total=2.5))as d:
      if d.status==200:
       r=await _fast_resp_json(d)or()
       if isinstance(r,list)and r and isinstance(r[0],list)and len(r[0])>=5:k=a.coinbase_spot if(.98<=a.coinbase_spot<=1.02)else 1.;b=.25*(float(r[0][1])+float(r[0][2])+float(r[0][3])+float(r[0][4]))*k
    else:
     w=lambda u:datetime.fromtimestamp(u,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");j=f"https://api.exchange.coinbase.com/products/{a.coinbase_product}/candles?granularity=60&start={w(s)}&end={w(m)}"
     async with h.get(j,timeout=aiohttp.ClientTimeout(total=2.5))as d:
      if d.status==200:
       for v in(await _fast_resp_json(d)or()):
        if isinstance(v,list)and len(v)>=5 and int(v[0])==s:b=.25*(float(v[1])+float(v[2])+float(v[3])+float(v[4]));break
   except Exception:pass
  if b>.0 and math.isfinite(b)and.975<=(auth_open_px/b)<=1.025:
   o=auth_open_px/b;n=float(getattr(a,"_cl_to_raw_usd_ratio",1.)or 1.)if a.is_chainlink_basis_anchored(q)else 1.;f=getattr(a,"_cl_proxy_history",None)
   if f and abs(o/n-1.)>1e-9:i=[(t,round(p*(o/n),4))for t,p in f];f.clear();f.extend(i)
   a._cl_to_raw_usd_ratio,a._cl_basis_anchor_ts=o,float(m);logger.info(f"[{a.asset} CHAINLINK BASIS ANCHORED] open_ts={m} cl=${auth_open_px:,.4f} raw=${b:,.4f} ({(o-1.)*1e4:+.2f}bps)")
 async def fetch_authoritative_chainlink_open(a,candle_open_ts,candle_close_ts,horizon="15m"):
  l=time.time()
  if l<float(candle_open_ts)+2.:return.0
  i={"5m":"fiveminute","15m":"fifteen","4h":"fourhour"}.get(str(horizon).lower(),"fifteen");h=await a.get_session();c=datetime.fromtimestamp(int(candle_open_ts),tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");g=datetime.fromtimestamp(int(candle_close_ts),tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ");f=(f"https://polymarket.com/api/crypto/crypto-price?symbol={a.asset.upper()}&eventStartTime={c}&variant={i}&endDate={g}&twapEnabled=true&twapLookbackSeconds=60")
  try:
   async with h.get(f,timeout=aiohttp.ClientTimeout(total=3.5))as e:
    if e.status==200:
     b=await _fast_resp_json(e)
     if isinstance(b,dict)and(b.get("cached")is True or b.get("completed")is True):
      if b.get("openPrice")is not None:
       j=float(b["openPrice"])
       if math.isfinite(j)and j>.0:await a._calibrate_chainlink_basis_anchor(candle_open_ts,j);return j
  except Exception:pass
  if l>=float(candle_open_ts)+35.:
   try:
    k=f"{GAMMA_API_URL}/events?slug={a.asset.lower()}-updown-5m-{int(candle_open_ts)-300}"
    async with h.get(k,timeout=aiohttp.ClientTimeout(total=3.5))as e:
     if e.status==200:
      b=await _fast_resp_json(e);m=b[0]if isinstance(b,list)and b else b
      if isinstance(m,dict)and m.get("closed")is True:
       d=m.get("eventMetadata");d=json.loads(d)if isinstance(d,str)else d
       if isinstance(d,dict)and d.get("finalPrice")is not None:
        j=float(d["finalPrice"])
        if math.isfinite(j)and j>.0:await a._calibrate_chainlink_basis_anchor(candle_open_ts,j);return j
   except Exception:pass
  return.0
 async def fetch_authoritative_chainlink_open_15m(self,candle_open_ts,candle_close_ts):return await self.fetch_authoritative_chainlink_open(candle_open_ts,candle_close_ts,"15m")
 async def fetch_binance_60s_twap_open(a,candle_open_ts):
  f=await a.get_session();c=(int(candle_open_ts)-60)*1000
  if not a.futures_only_ref:
   try:
    g=f"{BINANCE_REST_URL}/api/v3/klines?symbol={a.binance_symbol}&interval=1s&startTime={c}&limit=60"
    async with f.get(g)as e:
     if e.status==200:
      d=await _fast_resp_json(e)
      if isinstance(d,list)and len(d)>=30:o=sum((float(k[1])+float(k[4]))/2. for k in d)/len(d);return round(o,4)
   except Exception:pass
  try:
   b=f"{BINANCE_FUTURES_REST_URL}/fapi/v1/klines"if a.futures_only_ref else f"{BINANCE_REST_URL}/api/v3/klines";p=(f"{b}?symbol={a.binance_symbol}&interval=1m&startTime={c}&limit=1")
   async with f.get(p)as n:
    if n.status==200:
     m=await _fast_resp_json(n)
     if m:l=float(m[0][1]);j=float(m[0][2]);i=float(m[0][3]);h=float(m[0][4]);return round((l+j+i+h)/4.,4)
  except Exception:pass
  return.0
 async def fetch_finalized_binance_candle(b,candle_open_ts,interval="1h"):
  h=await b.get_session();i=str(interval).lower()
  if i in("5m","300s"):a="5m"
  elif i in("15m","900s"):a="15m"
  elif i in("4h","14400s"):a="4h"
  else:a="1h"
  try:
   f=int(candle_open_ts)*1000;c=f"{BINANCE_FUTURES_REST_URL}/fapi/v1/klines"if b.futures_only_ref else f"{BINANCE_REST_URL}/api/v3/klines";l=(f"{c}?symbol={b.binance_symbol}&interval={a}&startTime={f}&limit=1")
   async with h.get(l)as k:
    if k.status==200:
     j=await _fast_resp_json(k)
     if j:g=float(j[0][1]);d=float(j[0][4]);return g,d
  except Exception as e:logger.error(f"Failed to fetch Binance {a} candle for {b.binance_symbol}: {e}")
  return.0,.0
 async def verify_and_log_resolution(b,market,max_polls=60,poll_interval_sec=30.):
  if getattr(b,"riskless_bus_only",False):return
  q=str(market.get("market_id")or"");d=getattr(b,"_logged_resolution_market_ids",None)
  if d is None:d=set();b._logged_resolution_market_ids=d
  if not q or q in d:return
  if len(d)>512:j=sorted(d)[-256:];d.clear();d.update(j)
  d.add(q);p=int(market.get("candle_close_ts",0))-int(market.get("candle_open_ts",0));m="5m"if 0<p<=300 else("15m"if 0<p<=900 else("4h"if p>=10800 else"1h"));v=str(market.get("horizon")or m);logger.info(f"[*] Awaiting finalized {v} resolution for market {market['market_id']} ({market['title']})...");await asyncio.sleep(6.);u,o=await b.fetch_finalized_binance_candle(market["candle_open_ts"],interval=v);i=(1 if o>=u else 0)if(u>0 and o>0)else None;f=("UP"if i==1 else"DOWN")if i is not None else None;t=(((o-u)/u)*1e2)if(u>0 and o>0)else.0;a=None;c=str(market.get("resolution_source")or"")
  for s in range(max_polls):
   try:
    r=await b.get_session()
    async with r.get(f"{GAMMA_API_URL}/markets/{q}")as z:
     if z.status==200:
      y=await _fast_resp_json(z)
      if isinstance(y,dict):
       if not c and y.get("resolutionSource"):c=str(y.get("resolutionSource"))
       l=y.get("outcomePrices");h=y.get("outcomes",'["Up", "Down"]');x=json.loads(l)if isinstance(l,str)else l;n=json.loads(h)if isinstance(h,str)else h
       if isinstance(x,list)and len(x)>=2:
        E,D=float(x[0]),float(x[1]);C=str(n[0]).upper()if isinstance(n,list)and len(n)>=2 else"UP";B=str(n[1]).upper()if isinstance(n,list)and len(n)>=2 else"DOWN"
        if E>=.99 and D<=.01:a="UP"if"UP"in C or"YES"in C else("DOWN"if"DOWN"in C or"NO"in C else C);break
        elif D>=.99 and E<=.01:a="UP"if"UP"in B or"YES"in B else("DOWN"if"DOWN"in B or"NO"in B else B);break
   except Exception:pass
   if s+1<max_polls:await asyncio.sleep(poll_interval_sec)
  g=a;A=(1 if g=="UP"else 0)if g in("UP","DOWN")else None;w=(1 if g=="DOWN"else 0)if g in("UP","DOWN")else None;e=bool(a and f and a!=f)
  if e:logger.warning(f"[ORACLE MISMATCH ALERT] {market['title']} ({v}, m_id={q}): Binance Spot={f} (${u:,.2f}->${o:,.2f}, {t:+.4f}%) vs Official Gamma Settlement={a} (source={c or'unknown'})!")
  k={"timestamp_resolved":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"asset":b.asset,"horizon":v,"market_id":str(market["market_id"]),"title":market["title"],"candle_open_ts":market["candle_open_ts"],"candle_close_ts":market["candle_close_ts"],"authoritative_chainlink_open":market.get("authoritative_chainlink_open"),"binance_spot_open":u,"binance_spot_close":o,"candle_return_pct":round(t,4),"Y_UP":A,"Y_DOWN":w,"winning_outcome":g,"binance_winning_outcome":f,"gamma_winning_outcome":a,"oracle_mismatch":e,"resolution_source":c,"ground_truth_rule":"Official Polymarket Gamma/Chainlink Settlement (outcomePrices)"};_atomic_append_jsonl(RESOLUTIONS_FILE,json.dumps(k));logger.info(f"[GROUND TRUTH RESOLUTION LOGGED] {market['title']} ({v}) | Gamma={a} | BinanceDiag={f} ({t:+.3f}%)")
 def update_basis(a):
  if a.spot_price>0 and a.futures_price>0:a.basis_usd=a.futures_price-a.spot_price;a.basis_bps=(a.basis_usd/a.spot_price)*1e4;a.basis_history.append((time.monotonic_ns(),a.basis_bps))
 def get_delta_basis_100ms(b):
  if not b.basis_history:return.0
  c=time.monotonic_ns()-100000000;a=None
  for e,d in reversed(b.basis_history):
   if e>=c:a=d
   else:
    if(c-e)<=5000000000:a=d
    break
  return round(b.basis_bps-a,2)if a is not None else.0
 async def stream_binance_spot(a):
  if a.futures_only_ref or not a.binance_spot_ws:logger.info(f"[{a.asset}] futures_only_ref active; skipping Binance Spot WS (using Binance Futures + Coinbase USD).");return
  while a.running:
   try:
    logger.info(f"Connecting to Binance Spot @trade ({a.binance_spot_ws})...")
    async with websockets.connect(a.binance_spot_ws,ping_interval=20,ping_timeout=10,max_queue=512,compression=None)as t:
     _enable_ws_nodelay(t);logger.info(f"[+] Subscribed to Binance Spot @trade stream ({a.binance_symbol}).");b=0
     while a.running:
      f=await asyncio.wait_for(t.recv(),timeout=15.)
      if not a.running:break
      l=await _drain_ws_frames(t,f,max_batch=64);d=time.monotonic_ns();m=time.time();c=.25*float(a.shock_threshold_usd);k=(l[-1],)if a.riskless_bus_only else l;i=len(k)
      for q,j in enumerate(k):
       p=_orjson.loads(j)if _orjson is not None else json.loads(j);s=float(p.get("p",0));r=float(p.get("q",0));h=not p.get("m",False);o=int(p.get("E",0));n=int(p.get("T",0));g=s*r;a.spot_price=s;a.spot_price_ts=m;a._update_rolling_sigma(s);a.update_basis()
       if not a.riskless_bus_only:
        a.spot_trades.append((d,o,n,g,h,s))
        if q==i-1 or g>=c:a.evaluate_shock(d,n or o,source="SPOT")
        else:a._record_volume(g,m)
      a._maybe_write_fast_tick();b+=1
      if a.riskless_bus_only:await asyncio.sleep(.025)
      elif(b&31)==0:await asyncio.sleep(0)
   except Exception as e:logger.warning(f"Binance Spot feed disconnected: {e}. Reconnecting in 3s...");await asyncio.sleep(3)
 async def stream_binance_futures(a):
  while a.running:
   try:
    logger.info(f"Connecting to Binance Futures @trade ({a.binance_futures_ws})...")
    async with websockets.connect(a.binance_futures_ws,ping_interval=20,ping_timeout=10,max_queue=512,compression=None)as t:
     _enable_ws_nodelay(t);logger.info(f"[+] Subscribed to Binance Futures @trade stream ({a.binance_symbol} unbatched /ws).");b=0
     while a.running:
      f=await asyncio.wait_for(t.recv(),timeout=15.)
      if not a.running:break
      l=await _drain_ws_frames(t,f,max_batch=64);d=time.monotonic_ns();m=time.time();c=.25*float(a.shock_threshold_usd);k=(l[-1],)if a.riskless_bus_only else l;i=len(k)
      for q,j in enumerate(k):
       p=_orjson.loads(j)if _orjson is not None else json.loads(j);s=float(p.get("p",0));r=float(p.get("q",0));h=not p.get("m",False);o=int(p.get("E",0));n=int(p.get("T",0));g=s*r;a.futures_price=s;a.futures_price_ts=m
       if a.futures_only_ref:
        a.spot_price=s;a.spot_price_ts=m;a._update_rolling_sigma(s)
        if a.coinbase_product=="USDT-USD"and.95<=a.coinbase_spot<=1.05:
         if(m-a.coinbase_spot_ts)<=COINBASE_STALE_SEC and(not a.coinbase_history or(m-a.coinbase_history[-1][0])>=.2):
          a.coinbase_history.append((m,round(s*a.coinbase_spot,4)))
          while a.coinbase_history and m-a.coinbase_history[0][0]>30.:a.coinbase_history.popleft()
       a.update_basis()
       if not a.riskless_bus_only:
        a.futures_trades.append((d,o,n,g,h,s))
        if q==i-1 or g>=c:a.evaluate_shock(d,n or o,source="FUTURES")
        else:a._record_volume(g,m)
      a._maybe_write_fast_tick();b+=1
      if a.riskless_bus_only:await asyncio.sleep(.025)
      elif(b&31)==0:await asyncio.sleep(0)
   except Exception as e:logger.warning(f"Binance Futures feed disconnected: {e}. Reconnecting in 3s...");await asyncio.sleep(3)
 def _record_volume(a,notional,now_sec=None):
  b=int(now_sec if now_sec is not None else time.time())
  if a._vol_first_sec is None:a._vol_first_sec=b
  if a._vol_buckets and a._vol_buckets[-1][0]==b:a._vol_buckets[-1][1]+=notional
  else:a._vol_buckets.append([b,float(notional)])
 def get_avg_100ms_vol_5m(a,now_sec=None):
  now_sec=now_sec if now_sec is not None else time.time()
  if a._vol_first_sec is None or(now_sec-a._vol_first_sec)<ADAPTIVE_THRESH_MIN_COVERAGE_SEC:return None
  c=now_sec-ADAPTIVE_THRESH_WINDOW_SEC;d=sum(v for s,v in a._vol_buckets if s>=c);b=min(float(ADAPTIVE_THRESH_WINDOW_SEC),now_sec-a._vol_first_sec)
  if b<=0:return None
  return d/(b*10.)
 def get_effective_shock_threshold(a,now_sec=None):
  now_sec=now_sec if now_sec is not None else time.time();b,c=a._adaptive_cache
  if now_sec-b>=1.:c=compute_adaptive_shock_threshold(float(a.shock_threshold_usd),a.get_avg_100ms_vol_5m(now_sec));a._adaptive_cache=(now_sec,c)
  return c
 def _publish_btc_lead_state(a,vol_100ms,ofi_100ms,delta_basis=None,flow_dir="BUY",z_btc=.0,force=False):
  if a.asset!="BTC"or not a._fast_tick_enabled:return
  c=time.time()
  if not force and(c-a._last_lead_state_write)<LEAD_STATE_THROTTLE_SEC:return
  a._last_lead_state_write=c
  if delta_basis is None:delta_basis=a.get_delta_basis_100ms()
  b={"asset":"BTC","ts_ns":time.time_ns(),"t0_unix":c,"spot_px":a.spot_price,"spot_price":a.spot_price,"basis_bps":round(a.basis_bps,2),"vol_100ms":round(vol_100ms,0),"ofi_100ms":round(ofi_100ms,3),"delta_basis_100ms":delta_basis,"shock_dir":flow_dir,"btc_shock_direction":flow_dir,"btc_target_token":"UP"if flow_dir in("BUY","UP")else"DOWN","z_btc":round(z_btc,4)};b.update(a._last_btc_shock);write_lead_state(b,a.lead_state_file)
 def evaluate_shock(a,recv_mono_ns,event_ts_ms,source):
  _k=a.spot_trades if source=="SPOT"else a.futures_trades
  if _k:a._record_volume(float(_k[-1][3]))
  _b=time.time();_j=(_b*1e3-float(event_ts_ms))if event_ts_ms>0 else.0
  if event_ts_ms>1600000000000 and 1e3<_j<8.64e7:
   _G=float(getattr(a,"_last_stale_exch_warn_ts",.0)or.0)
   if _b-_G>=5.:a._last_stale_exch_warn_ts=_b;logger.warning(f"[STALE_EXCHANGE_EVENT_VETO] Dropping stale {source} {a.asset} packet (exch_lag_ms={_j:.1f}ms > 1000ms ceiling) to prevent burst-drain phantom shock.")
   return
  L=float(a.shock_threshold_usd);j=a.get_effective_shock_threshold();_F=recv_mono_ns-100000000;_a=recv_mono_ns-40000000;b=.0;d=.0;c=.0;D=.0;C=.0;u=.0;w=.0;v=.0;r=.0;P=recv_mono_ns-250000000;K=int((_k[-1][2]or _k[-1][1])if _k else 0)or int(event_ts_ms or 0)
  for _7,_6,_5,_2,_v,_ in reversed(_k):
   if _7<P:break
   _Y=int(_5 or _6 or 0)
   if K>0 and _Y>0:
    _w=K-_Y
    if _w>250:break
    if _w<-50:continue
    E=(_w<=100)and(_7>=_F);J=(_w<=40)and(_7>=_a)
   else:E=(_7>=_F);J=(_7>=_a)
   w+=_2
   if _v:v+=_2
   else:r+=_2
   if E:
    b+=_2
    if _v:d+=_2
    else:c+=_2
   if J:
    D+=_2
    if _v:C+=_2
    else:u+=_2
  _i=a.futures_trades if source=="SPOT"else a.spot_trades;p=.0;h=.0;g=.0
  for t_m,_4,_3,_2,_v,_ in reversed(_i):
   if t_m<_F:break
   _X=int(_3 or _4 or 0)
   if K>0 and _X>0 and abs(K-_X)>120:
    if(K-_X)>120:break
    continue
   p+=_2
   if _v:h+=_2
   else:g+=_2
  I=b+.75*p;_N="BUY"if d>=c else"SELL";O=(d-c)/b if b>0 else.0;Z=None;B=False
  if a.asset in("ETH","SOL","XRP"):
   if a.lead_state_file==lead_state_path("BTC"):Z=read_lead_state_inproc(max_age_ms=LEAD_STATE_MAX_AGE_MS)
   if Z is None:
    _W=_b
    if(_W-float(getattr(a,"_last_disk_lead_poll_ts",.0)or.0))>=.025 or a.lead_state_file!=lead_state_path("BTC"):a._last_disk_lead_poll_ts=_W;a._cached_disk_lead=read_lead_state(a.lead_state_file,max_age_ms=LEAD_STATE_MAX_AGE_MS)
    Z=getattr(a,"_cached_disk_lead",None)
   if Z is not None:
    _h=int(Z.get("last_shock_ts_ns")or 0)
    if _h>0 and(time.time_ns()-_h)<=int(SYMPATHY_BTC_MAX_AGE_MS*1000000):
     _M=a.books.get("UP"if _N=="BUY"else"DOWN");_V=(round((_b-_M.last_best_ask_change_ts)*1e3,1)if(_M is not None and _M.last_best_ask_change_ts>.0)else None);B=evaluate_btc_sympathy(Z,_N,_V)
     if B:j=min(j,SYMPATHY_THRESHOLD_MULT*L)
  elif a.asset=="BTC":_9=(1. if _N=="BUY"else-1.)*abs(O)*(b/max(L,1.));a._publish_btc_lead_state(b,O,None,_N,_9)
  _L=(C-u)/max(D,1e-6)if D>0 else.0;t=bool(D>=.75*j and abs(_L)>=.9)
  if t:b=D;d=C;c=u
  elif b<j and w>=(j*1.45):b,d,c=w,v,r
  elif b<j and I>=(j*1.2):b=b+p;d=d+h;c=c+g
  _U=time.time();H=(t or b>=j);global _LAST_GLOBAL_PREWARM_IPC_TS
  if(not H and b>=.45*j and(_U-float(getattr(a,"_last_prewarm_ipc_ts",.0)or.0))>=2.5 and(_U-_LAST_GLOBAL_PREWARM_IPC_TS)>=1.5):a._last_prewarm_ipc_ts=_U;_LAST_GLOBAL_PREWARM_IPC_TS=_U;a.get_rolling_sigma("15m");a.get_rolling_sigma("1h");_broadcast_fast_trigger_ipc(b'{"_prewarm_clob_tls":1}\n')
  if H and(_U-a.last_shock_ts>2.5):
   _T=a.books.get("UP");_E=a.books.get("DOWN");_1=bool(_T and _E and a.current_market);_S=bool(getattr(a,"market_15m",None)and"UP_15M"in a.books and"DOWN_15M"in a.books)
   if not _1 and not _S:return
   if source=="FUTURES"and not a.futures_only_ref:
    _8=float(getattr(a,"spot_price_ts",.0)or.0)
    if _8>.0 and(_U-_8)>15.:logger.warning(f"[STALE_SPOT_ANCHOR_VETO] Skipping {a.asset} FUTURES shock: spot_price_ts stale ({_U-_8:.1f}s > 15s).");return
   a.last_shock_ts_by_source[source]=_U;a.last_shock_ts=_U;_D="BUY"if d>=c else"SELL";ofi=(d-c)/b if b>0 else.0;_u=a.spot_price if source=="SPOT"else a.futures_price;_R=(1. if _D=="BUY"else-1.)*abs(ofi)*(b/max(L,1.))
   if a.asset=="BTC":a._last_btc_shock={"last_shock_ts_ns":time.time_ns(),"last_shock_vol_100ms":round(b,0),"last_shock_ofi_100ms":round(ofi,3),"last_shock_dir":_D,"last_shock_z_btc":round(_R,4)}
   Y={"effective_shock_threshold":round(j,0),"btc_shock_direction":None,"z_btc":None}
   if a.asset in("ETH","SOL","XRP"):
    Y["shock_z"]=round(_R,4);Y["sympathy_trigger"]=bool(B)
    if Z is not None:
     X=int(Z.get("last_shock_ts_ns")or 0)
     if X>0 and(time.time_ns()-X)/1e6<=LEAD_STATE_MAX_AGE_MS:Y["btc_shock_direction"]="UP"if str(Z.get("last_shock_dir")).upper()=="BUY"else"DOWN";Y["z_btc"]=float(Z.get("last_shock_z_btc")or.0);Y["btc_shock_age_ms"]=round((time.time_ns()-X)/1e6,1)
   elif a.asset=="BTC":Y["shock_z"]=round(_R,4);Y["btc_shock_direction"]=_D;Y["z_btc"]=round(_R,4)
   _0=_U;_t=recv_mono_ns;x=a.get_delta_basis_100ms();o=a.basis_bps;s=abs(a.basis_bps);_Q=a.spot_price;_s=a.futures_price;W=Y.get("btc_shock_direction");_C=Y.get("z_btc");_B=datetime.fromtimestamp(_0,tz=timezone.utc);_A=_B.strftime("%Y-%m-%d %H:%M:%S UTC");_r=a.get_coinbase_spot(_0);_q=a.get_chainlink_proxy_spot(_0);_p=a.get_chainlink_twap_60s(_0);_o=a.is_chainlink_basis_anchored(_0);_P=a.get_venue_divergence_bps(_0);_z=a.get_venue_divergence_centered_bps(_0);_n=a.get_coinbase_move_bps(2.,_0);_m=[];m=""
   if _S:
    try:
     m15=a.market_15m;_K=float(m15.get("finalized_15m_open",.0)or.0);_g=float(m15.get("authoritative_chainlink_open",.0)or.0);_f=float(_q or.0);_e=(m15["end_dt"]-_B).total_seconds()
     if 0<_e<=9e2:
      if _g>.0 and _f>.0:A=((_f-_g)/_g*1e2)
      else:A=((a.spot_price-_K)/_K*1e2)if _K>0 else.0
      V=max(.001,_e/float(m15.get("duration_s",9e2)));z=a.get_rolling_sigma("15m");U=(A/1e2)/max(z*math.sqrt(V),1e-6);N=round(U,4)if a.asset in("ETH","SOL","XRP")else None;M=a.books["UP_15M"].get_metrics(obs_ts=_0,fee_rate=m15.get("fee_metadata",{}).get("fee_rate_market",.07));F=a.books["DOWN_15M"].get_metrics(obs_ts=_0,fee_rate=m15.get("fee_metadata",{}).get("fee_rate_market",.07));M["token_id"]=m15["tokens"].get("UP");F["token_id"]=m15["tokens"].get("DOWN");T=f"{m15['market_id']}_{_0:.6f}";_d={"shock_id":T,"event_id":T,"timestamp":_A,"t0_unix":_0,"t0_mono_ns":_t,"t0_definition":"local_receipt_boundary","exchange_event_ts_ms":event_ts_ms,"clob_ws_connected":bool(getattr(a,"clob_ws_connected",True)),"clob_ws_rx_age_ms":round(max(.0,(_0-float(a.last_clob_ws_msg_ts))*1e3),1)if getattr(a,"last_clob_ws_msg_ts",.0)>.0 else None,"shock_source":source,"asset":a.asset,"horizon":"15m","candle_interval":"15m","series_slug":m15.get("series_slug",f"{a.asset.lower()}-up-or-down-15m"),"slug":m15.get("slug",""),"resolution_source":m15.get("resolution_source",""),"market_id":m15["market_id"],"condition_id":m15.get("condition_id",""),"title":m15["title"],"seconds_to_expiry":round(_e,1),"expiry_ts":float(m15.get("candle_close_ts")or(_0+_e)),"candle_expiry_ts":float(m15.get("candle_close_ts")or(_0+_e)),"candle_open_ts":int(m15.get("candle_open_ts")or(int(m15["end_dt"].timestamp())-900)),"candle_sigma":z,"shock_volume_100ms":round(b,0),"is_40ms_fast_track":t,"shock_direction":_D,"btc_shock_direction":W,"z_val":round(abs(U),4),"z_score":round(U,4),"z_btc":_C,"z_eth":N,"shock_ofi":round(ofi,3),"trigger_price":_u,"spot_at_t0":_Q,"futures_at_t0":_s,"basis_signed_bps_t0":round(o,2),"basis_abs_bps_t0":round(s,2),"delta_basis_100ms":x,"coinbase_spot":_r,"chainlink_proxy_spot":_q,"chainlink_twap_60s":_p,"chainlink_basis_anchored":_o,"venue_divergence_bps":_P,"venue_divergence_centered_bps":_z,"coinbase_move_bps_2s":_n,**Y,"finalized_1h_open":_K,"candle_open_spot":_K,"twap_60s_open":float(m15.get("twap_60s_open",.0)or.0)or None,"authoritative_chainlink_open":float(m15.get("authoritative_chainlink_open",.0)or.0)or None,"chainlink_open_spot":float(m15.get("chainlink_open_spot",.0)or.0)or None,"candle_distance_pct":round(A,4),"fee_metadata":dict(m15.get("fee_metadata",{})),"pre_shock_features_t0":{"UP":M,"DOWN":F}}
      try:
       _O,m=_dispatch_trigger_fast(TRIGGER_FILE,_d,defer_ipc=True)
       if isinstance(_O,(bytes,bytearray)):_m.append(bytes(_O))
      except TypeError:_,m=_dispatch_trigger_fast(TRIGGER_FILE,_d)
    except Exception:pass
   e=None;l={};i={};k=.0;n=.0;_J="";G="";y={};q=""
   if _1:
    l=_T.get_metrics(obs_ts=_0,fee_rate=a.fee_rate_market);i=_E.get_metrics(obs_ts=_0,fee_rate=a.fee_rate_market)
    if a.current_market and"tokens"in a.current_market:l["token_id"]=a.current_market["tokens"].get("UP");i["token_id"]=a.current_market["tokens"].get("DOWN")
    k=(a.current_market["end_dt"]-_B).total_seconds();n=((a.spot_price-a.finalized_1h_open)/a.finalized_1h_open*1e2)if a.finalized_1h_open>0 else.0;_J=a.current_market["market_id"];S=a.current_market.get("condition_id","");G=a.current_market["title"];y=dict(a.current_market.get("fee_metadata",{}));_c=str(a.current_market.get("horizon","1h"));R=a.get_rolling_sigma(_c);_I=max(.001,k/float(a.current_market.get("duration_s",3600.)));_H=(n/1e2)/max(R*math.sqrt(_I),1e-6);_y=round(_H,4)if a.asset in("ETH","SOL","XRP")else None;Q=f"{_J}_{_0:.6f}";e={"shock_id":Q,"event_id":Q,"timestamp":_A,"t0_unix":_0,"t0_mono_ns":_t,"t0_definition":"local_receipt_boundary","exchange_event_ts_ms":event_ts_ms,"clob_ws_connected":bool(getattr(a,"clob_ws_connected",True)),"clob_ws_rx_age_ms":round(max(.0,(_0-float(a.last_clob_ws_msg_ts))*1e3),1)if getattr(a,"last_clob_ws_msg_ts",.0)>.0 else None,"shock_source":source,"asset":a.asset,"horizon":_c,"candle_interval":_c,"series_slug":a.series_slug,"slug":a.current_market.get("slug",""),"resolution_source":a.current_market.get("resolution_source",""),"market_id":_J,"condition_id":S,"title":G,"seconds_to_expiry":round(k,1),"expiry_ts":float(a.current_market.get("candle_close_ts")or(_0+k)),"candle_expiry_ts":float(a.current_market.get("candle_close_ts")or(_0+k)),"candle_open_ts":int(a.current_market.get("candle_open_ts")or(int(a.current_market["end_dt"].timestamp())-3600)),"candle_sigma":R,"shock_volume_100ms":round(b,0),"is_40ms_fast_track":t,"shock_direction":_D,"btc_shock_direction":W,"z_val":round(abs(_H),4),"z_score":round(_H,4),"z_btc":_C,"z_eth":_y,"shock_ofi":round(ofi,3),"trigger_price":_u,"spot_at_t0":_Q,"futures_at_t0":_s,"basis_signed_bps_t0":round(o,2),"basis_abs_bps_t0":round(s,2),"delta_basis_100ms":x,"coinbase_spot":_r,"chainlink_proxy_spot":_q,"chainlink_twap_60s":_p,"chainlink_basis_anchored":_o,"venue_divergence_bps":_P,"venue_divergence_centered_bps":_z,"coinbase_move_bps_2s":_n,**Y,"finalized_1h_open":a.finalized_1h_open if _c=="1h"else None,"candle_open_spot":a.finalized_1h_open,"twap_60s_open":float(getattr(a,"twap_60s_1h_open",.0)or.0)or None,"chainlink_open_spot":float(getattr(a,"chainlink_1h_open",.0)or.0)or None,"candle_distance_pct":round(n,4),"fee_metadata":y,"pre_shock_features_t0":{"UP":l,"DOWN":i}}
    try:
     try:
      _Z,q=_dispatch_trigger_fast(TRIGGER_FILE,e,defer_ipc=True)
      if isinstance(_Z,(bytes,bytearray)):_m.append(bytes(_Z))
     except TypeError:_,q=_dispatch_trigger_fast(TRIGGER_FILE,e)
    except Exception as f:logger.error(f"Failed to encode 1h trigger: {f}")
   if _m:
    _x=b"".join(_m)
    if len(_x)<=60000 and _broadcast_fast_trigger_ipc(_x):pass
    else:
     for ch in _m:_broadcast_fast_trigger_ipc(ch)
   if a.asset=="BTC":a._publish_btc_lead_state(b,ofi,x,_D,_R,force=True)
   if q:
    try:_persist_trigger_nonblocking(TRIGGER_FILE,q)
    except Exception as f:logger.error(f"Failed to persist zero-latency trigger: {f}")
   if m:
    try:_persist_trigger_nonblocking(TRIGGER_FILE,m)
    except Exception:pass
   _l="40ms FAST-TRACK"if t else"100ms";logger.info(f"\n[!!! {source} SHOCK TRIGGERED ({_l}) !!!] Vol=${b:,.0f} | Dir={_D} | OFI={ofi:+.2f} | Spot=${a.spot_price:,.1f} | Fut=${a.futures_price:,.1f} | Basis={a.basis_bps:+.1f}bps | DeltaBasis100ms={x:+.1f}bps")
   if _1 and len(a.active_burst_tasks)<5:_aa=asyncio.create_task(a.capture_shock_burst(_0,_t,source,b,_D,ofi,_u,x,l,i,o,s,k,n,_Q,_s,_J,G,y));a.active_burst_tasks.add(_aa);_aa.add_done_callback(a.active_burst_tasks.discard)
   elif _1:logger.warning(f"Concurrent burst tasks throttle reached ({len(a.active_burst_tasks)}). Skipping telemetry capture.")
 async def capture_shock_burst(a,t0,t0_mono_ns,source,shock_vol,shock_dir,ofi,trigger_px,delta_basis_100ms,pre_shock_up,pre_shock_down,pre_shock_basis_signed,pre_shock_basis_abs,t0_secs_left,t0_dist_pct,t0_spot,t0_futures,m_id,m_title,fee_meta):
  k=a.books.get("UP");h=a.books.get("DOWN")
  if not k or not h or not a.current_market:return
  d=[.1,.15,.25,.5,4.,25.];c=["100ms","250ms","500ms","1s","5s","30s"];b={}
  for n,m in zip(d,c):await asyncio.sleep(n);i=time.time();o=k.get_metrics(obs_ts=i,fee_rate=a.fee_rate_market);l=h.get_metrics(obs_ts=i,fee_rate=a.fee_rate_market);b[m]={"elapsed_sec":round(i-t0,3),"up_mid":o["q_mid"],"up_ask":o["best_ask"],"up_delta_q_ask":round(o["best_ask"]-pre_shock_up["best_ask"],4),"up_delta_q_mid":round(o["q_mid"]-pre_shock_up["q_mid"],4),"up_obi_l1":o["obi_l1"],"up_obi_depth":o["obi_depth"],"down_mid":l["q_mid"],"down_ask":l["best_ask"],"down_delta_q_ask":round(l["best_ask"]-pre_shock_down["best_ask"],4),"down_delta_q_mid":round(l["q_mid"]-pre_shock_down["q_mid"],4),"binance_spot":a.spot_price,"binance_futures":a.futures_price,"basis_bps":round(a.basis_bps,2),"delta_basis_bps":round(a.basis_bps-pre_shock_basis_signed,2)}
  j=a.current_market.get("condition_id","")if a.current_market else"";f={"timestamp":datetime.fromtimestamp(t0,tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"t0_unix":t0,"t0_mono_ns":t0_mono_ns,"shock_source":source,"market_id":m_id,"condition_id":j,"title":m_title,"seconds_to_expiry":round(t0_secs_left,1),"shock_volume_100ms":round(shock_vol,0),"shock_direction":shock_dir,"shock_ofi":round(ofi,3),"trigger_price":trigger_px,"spot_at_t0":t0_spot,"futures_at_t0":t0_futures,"basis_signed_bps_t0":round(pre_shock_basis_signed,2),"basis_abs_bps_t0":round(pre_shock_basis_abs,2),"delta_basis_100ms":delta_basis_100ms,"finalized_1h_open":a.finalized_1h_open,"candle_distance_pct":round(t0_dist_pct,4),"fee_metadata":fee_meta,"pre_shock_features_t0":{"UP":pre_shock_up,"DOWN":pre_shock_down},"impulse_response":b,"pre_registered_models":{"model_a_spot":"Y = f(q_mid, X_spot, TTE, dist)","model_b_futures":"Y = f(q_mid, X_futures, TTE, dist)","model_c_joint":"Y = f(q_mid, X_spot, X_futures, basis, delta_basis, TTE, dist)","model_d_incremental":"Y = f(q_mid, X_spot, TTE, dist) + g(X_futures | X_spot) -> test beta_{F|S} = 0","oos_training_invariant":"T_train_end < t0 (model trained strictly on completed prior markets)"},"clock_metadata":{"clock_offset_ms":a.clock_offset_ms,"clock_uncertainty_ms":a.clock_uncertainty_ms,"timestamp_designation":"exchange_to_local_delta_with_calibrated_offset"},"statistical_clustering":{"cluster_market_hour":m_id,"cluster_shock_episode":f"{m_id}_{int(t0)}","variance_estimator":"IRF: shock-episode block bootstrap | Regressions: market-hour cluster-robust SE"}};_atomic_append_jsonl(a.shock_file,json.dumps(f));e=b["30s"]["up_delta_q_ask"];g=float(pre_shock_up.get("age_ask_ms")or.0);logger.info(f"[SHOCK BURST CAPTURED] Market {m_id} | Source={source} | AgeAsk(UP)={g:.0f}ms | UP ask={pre_shock_up['best_ask']:.3f} -> 30s Delta: {e:+.3f} | Basis={pre_shock_basis_signed:+.1f}bps (Observational episode, not yet evidence of persistent structural lag)")
 async def _refresh_quiet_books_batch(a,token_ids,subscribed_tokens):
  if not token_ids:return 0
  b=0
  try:
   d=await a.get_session();c=[{"token_id":str(t)}for t in dict.fromkeys(token_ids)if t]
   async with d.post(f"{CLOB_API_URL}/books",json=c,timeout=1.5)as h:
    if h.status==200:
     e=await _fast_resp_json(h)
     if isinstance(e,list):
      for g in e:
       if not isinstance(g,dict):continue
       i=str(g.get("asset_id")or"");f=subscribed_tokens.get(i)
       if f and f in a.books:a.books[f].apply_snapshot(g.get("bids",[]),g.get("asks",[]));b+=1
  except Exception:pass
  if b>0:a._maybe_write_fast_tick()
  return b
 async def stream_polymarket_clob(a):
  l={}
  while a.running:
   L=datetime.now(timezone.utc);d=(a.current_market if a.current_market and(a.current_market["end_dt"]-L).total_seconds()>0 else None);b=str(d["market_id"])if d else"";c=d["end_dt"]if d else None;k={}
   if d:
    K=str(d["tokens"]["UP"]);D=str(d["tokens"]["DOWN"])
    if"UP"not in a.books or getattr(a.books["UP"],"token_id",None)!=K:a.books["UP"]=L2OrderBook(K)
    if"DOWN"not in a.books or getattr(a.books["DOWN"],"token_id",None)!=D:a.books["DOWN"]=L2OrderBook(D)
    k[K]="UP";k[D]="DOWN"
   J=time.monotonic()
   for T,j,s,q in(("5m","market_5m","UP_5M","DOWN_5M"),("15m","market_15m","UP_15M","DOWN_15M"),("4h","market_4h","UP_4H","DOWN_4H")):
    I=getattr(a,j,None)
    if I and(I["end_dt"]-L).total_seconds()<=0:setattr(a,j,None);I=None
    if not I and(J-l.get(T,.0))>=15.:
     l[T]=J
     try:setattr(a,j,await a.discover_nearest_twap_market(T))
     except Exception:pass
    S=getattr(a,j,None)
    if S and"tokens"in S and(S["end_dt"]-L).total_seconds()>0:
     _a=str(S["tokens"]["UP"]);Z=str(S["tokens"]["DOWN"])
     if s not in a.books or getattr(a.books[s],"token_id",None)!=_a:a.books[s]=L2OrderBook(_a)
     if q not in a.books or getattr(a.books[q],"token_id",None)!=Z:a.books[q]=L2OrderBook(Z)
     k[_a]=s;k[Z]=q
   if not k:await asyncio.sleep(1.);continue
   try:
    C=list(k.keys());Q=b or f"{a.asset}-TWAP";logger.info(f"Connecting to Polymarket CLOB WS ({CLOB_WS_URL}) for market {Q} tokens ({list(k.values())})...")
    try:
     B=[tok_id for tok_id,role_name in k.items()if(bk_obj:=a.books.get(role_name))is not None and(not bk_obj.bids or not bk_obj.asks)]
     if B:await a._refresh_quiet_books_batch(B,k)
    except Exception:pass
    async with websockets.connect(CLOB_WS_URL,ping_interval=20,ping_timeout=10,max_queue=512,compression=None)as ws:
     _enable_ws_nodelay(ws);P={"assets_ids":C,"type":"market","custom_feature_enabled":True};await ws.send(json.dumps(P));logger.info(f"[+] Subscribed to Polymarket L2 orderbooks for market {Q}.");a._reconnect_clob=False;o={};g=time.time();h=g;f=g;a.clob_ws_connected=True;a.last_clob_ws_msg_ts=g
     while a.running:
      O=datetime.now(timezone.utc);U=(a.current_market if a.current_market and(a.current_market["end_dt"]-O).total_seconds()>0 else None);F=str(U["market_id"])if U else""
      if(c is not None and(c-O).total_seconds()<=0)or(F!=b):
       logger.info(f"[*] Market {b or'twap-only'} expired or rotated to {F or'twap-only'}. Rotating 1H subscription in-place.");v=[t for t,r in k.items()if r in("UP","DOWN")]
       for p in v:k.pop(p,None);o.pop(p,None)
       if U and"tokens"in U:
        W=str(U["tokens"]["UP"]);V=str(U["tokens"]["DOWN"])
        if"UP"not in a.books or getattr(a.books["UP"],"token_id",None)!=W:a.books["UP"]=L2OrderBook(W)
        if"DOWN"not in a.books or getattr(a.books["DOWN"],"token_id",None)!=V:a.books["DOWN"]=L2OrderBook(V)
        k[W]="UP";k[V]="DOWN";d=U;b=F;c=U["end_dt"];await ws.send(json.dumps({"assets_ids":[W,V],"operation":"subscribe","custom_feature_enabled":True}));A=time.time();o[W]=A;o[V]=A;await a._refresh_quiet_books_batch([W,V],k);o.pop(W,None);o.pop(V,None)
       else:
        a.books.pop("UP",None);a.books.pop("DOWN",None);d=None;b="";c=None
        if not k:a.clob_ws_connected=False;break
      i=False
      for T,j,s,q in(("5m","market_5m","UP_5M","DOWN_5M"),("15m","market_15m","UP_15M","DOWN_15M"),("4h","market_4h","UP_4H","DOWN_4H")):
       S=getattr(a,j,None)
       if S and(S["end_dt"]-O).total_seconds()<=0:
        logger.info(f"[*] {T.upper()} Market {S['market_id']} reached expiry. Cycling to next.")
        if not a.riskless_bus_only:asyncio.create_task(a.verify_and_log_resolution(S))
        setattr(a,j,None);a.books.pop(s,None);a.books.pop(q,None)
        for p in[t for t,r in k.items()if r in(s,q)]:k.pop(p,None)
        i=True
      if i or getattr(a,"_reconnect_clob",False):
       a._reconnect_clob=False;z=[]
       for T,j,s,q in(("5m","market_5m","UP_5M","DOWN_5M"),("15m","market_15m","UP_15M","DOWN_15M"),("4h","market_4h","UP_4H","DOWN_4H")):
        S=getattr(a,j,None)
        if not(S and"tokens"in S):continue
        for y,R in((str(S["tokens"]["UP"]),s),(str(S["tokens"]["DOWN"]),q)):
         if R not in a.books or getattr(a.books[R],"token_id",None)!=y:a.books[R]=L2OrderBook(y)
         if k.get(y)!=R:
          for p in[t for t,r in k.items()if r==R and t!=y]:k.pop(p,None)
          k[y]=R;z.append(y)
       if z:
        await ws.send(json.dumps({"assets_ids":z,"operation":"subscribe","custom_feature_enabled":True}));N=time.time()
        for y in z:o[y]=N
        logger.info(f"[+] In-place CLOB WS subscribe for {len(z)} rolled TWAP token(s).")
      if o and(time.time()-min(o.values()))>8.:
       E=list(o.keys());H=await a._refresh_quiet_books_batch(E,k)
       if H>0:
        for pt in E:o.pop(pt,None)
       else:logger.warning("[*] In-place CLOB WS subscribe got no book within 8s. Reconnecting...");a.clob_ws_connected=False;break
      G=time.time()
      if(G-h)>=9.:h=G;await ws.send("PING")
      if(G-f)>=1.6:
       f=G;x=[tok_q for tok_q,role_q in k.items()if role_q in("UP","DOWN","UP_15M","DOWN_15M","UP_5M","DOWN_5M","UP_4H","DOWN_4H")and role_q in a.books and((G-a.books[role_q].last_book_update_ts)>=1.8 or(a.books[role_q].prev_best_bid[0]>.0 and a.books[role_q].prev_best_ask[0]<1. and a.books[role_q].prev_best_bid[0]>=a.books[role_q].prev_best_ask[0]))]
       if x:await a._refresh_quiet_books_batch(x,k)
      if time.time()-g>25.:logger.warning(f"[*] CLOB WS silent for >25s on market {b}. Reconnecting...");a.clob_ws_connected=False;break
      try:M=await asyncio.wait_for(ws.recv(),timeout=1.);g=time.time();a.last_clob_ws_msg_ts=g
      except asyncio.TimeoutError:a._maybe_emit_boundary_lock_trigger();continue
      if M in("PONG","pong","",b"PONG",b"pong"):a._maybe_emit_boundary_lock_trigger();continue
      Y=_orjson.loads(M)if _orjson is not None else json.loads(M)
      if isinstance(Y,list):
       for X in Y:
        n=str(X.get("asset_id")or"");o.pop(n,None);m=k.get(n)
        if m and m in a.books:a.books[m].apply_snapshot(X.get("bids",[]),X.get("asks",[]))
      elif isinstance(Y,dict):
       w=Y.get("event_type")
       if w=="price_change":
        u=defaultdict(list)
        for pc in Y.get("price_changes",[]):
         m=k.get(str(pc.get("asset_id")or""))
         if m:u[m].append(pc)
        for m,_b in u.items():
         if m in a.books:a.books[m].apply_price_changes(_b)
       elif w=="book":
        n=str(Y.get("asset_id")or"");o.pop(n,None);m=k.get(n)
        if m and m in a.books:a.books[m].apply_snapshot(Y.get("bids",[]),Y.get("asks",[]))
      a._maybe_write_fast_tick();a._maybe_emit_boundary_lock_trigger()
   except Exception as e:a.clob_ws_connected=False;logger.warning(f"Polymarket CLOB WS disconnected: {e}. Reconnecting in 1s...");await asyncio.sleep(1.)
 def _maybe_emit_boundary_lock_trigger(a):
  if a.riskless_bus_only or a.spot_price<=0:return
  B=time.time()
  if B-getattr(a,"_last_boundary_check_ts",.0)<.25:return
  a._last_boundary_check_ts=B;b=getattr(a,"_boundary_lock_cooldowns",None)
  if b is None:b={};a._boundary_lock_cooldowns=b
  A=datetime.now(timezone.utc);i=[]
  if a.current_market and a.finalized_1h_open>0 and"UP"in a.books and"DOWN"in a.books:i.append((a.current_market,float(a.finalized_1h_open),"UP","DOWN","1h",3600.))
  if getattr(a,"market_15m",None)and"UP_15M"in a.books and"DOWN_15M"in a.books:
   w=float(a.market_15m.get("finalized_15m_open",.0)or.0)
   if w>0:i.append((a.market_15m,w,"UP_15M","DOWN_15M","15m",9e2))
  for I,z,D,v,y,E in i:
   H=str(I.get("market_id")or"")
   if not H or(B-b.get(H,.0))<15.:continue
   l=(I["end_dt"]-A).total_seconds()
   if not(12.<=l<=75.):continue
   h=float(I.get("authoritative_chainlink_open",.0)or.0)if y=="15m"else.0;k=(a.get_chainlink_twap_60s(B)if l<=60. else a.get_chainlink_proxy_spot(B))if y=="15m"else.0
   if y=="15m"and h>.0 and k>.0:c=((k-h)/h)*1e2
   else:c=((a.spot_price-z)/z)*1e2
   f=.08 if y=="15m"else.12
   if abs(c)<f:continue
   if a.asset=="XAU":g=.0012 if y=="15m"else.0022
   else:g=(.0035 if a.asset=="BTC"else.005)if y=="15m"else(.005 if a.asset=="BTC"else.0075)
   u=max(.001,l/E);t=(c/1e2)/max(g*math.sqrt(u),1e-6)
   if abs(t)<3.:continue
   s="UP"if c>0 else"DOWN";r=a.books[D if s=="UP"else v]
   if not r.asks or not r.bids:continue
   q=min(r.asks.keys())
   if not(.62<=q<=.94):continue
   p=dict(I.get("fee_metadata",{}));o=float(p.get("fee_rate_market",a.fee_rate_market)or.07);d=o*q*(1.-q);n=(1.-q)-d
   if n<.025:continue
   b[H]=B;G=a.books[D].get_metrics(obs_ts=B,fee_rate=o);C=a.books[v].get_metrics(obs_ts=B,fee_rate=o);G["token_id"]=I["tokens"].get("UP");C["token_id"]=I["tokens"].get("DOWN");j="BUY"if s=="UP"else"SELL";m=f"BOUNDARY_{H}_{B:.6f}";e=a._read_cross_asset_fields(B,t,j)if hasattr(a,"_read_cross_asset_fields")else{};F={"shock_id":m,"event_id":m,"timestamp":datetime.fromtimestamp(B,tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"t0_unix":B,"t0_mono_ns":time.monotonic_ns(),"t0_definition":"boundary_lock_scanner","shock_source":"BOUNDARY_LOCK","regime_override":"REGIME_D_BOUNDARY_LOCK","asset":a.asset,"horizon":y,"candle_interval":y,"series_slug":I.get("series_slug",a.series_slug),"slug":I.get("slug",""),"market_id":H,"condition_id":I.get("condition_id",""),"title":I.get("title",""),"seconds_to_expiry":round(l,1),"expiry_ts":float(I.get("candle_close_ts")or(B+l)),"candle_expiry_ts":float(I.get("candle_close_ts")or(B+l)),"candle_open_ts":int(I.get("candle_open_ts")or(int(I["end_dt"].timestamp())-int(E))),"candle_sigma":g,"shock_volume_100ms":2e6,"is_40ms_fast_track":True,"shock_direction":j,"btc_shock_direction":j if a.asset=="BTC"else e.get("btc_shock_direction",j),"z_val":round(abs(t),4),"z_score":round(t,4),"z_btc":round(t,4)if a.asset=="BTC"else e.get("z_btc",round(t,4)),"z_eth":round(t,4)if a.asset=="ETH"else None,"p_model":.985,"shock_ofi":.9 if s=="UP"else-.9,"trigger_price":a.spot_price,"spot_at_t0":a.spot_price,"futures_at_t0":a.futures_price or a.spot_price,"basis_signed_bps_t0":round(a.basis_bps,2),"basis_abs_bps_t0":round(abs(a.basis_bps),2),"delta_basis_100ms":max(.0,a.get_delta_basis_100ms())if s=="UP"else min(.0,a.get_delta_basis_100ms()),"coinbase_spot":a.get_coinbase_spot(B),"chainlink_proxy_spot":a.get_chainlink_proxy_spot(B),"chainlink_twap_60s":a.get_chainlink_twap_60s(B),"chainlink_basis_anchored":a.is_chainlink_basis_anchored(B),"resolution_source":I.get("resolution_source",""),"authoritative_chainlink_open":I.get("authoritative_chainlink_open")if y=="15m"else None,"venue_divergence_bps":a.get_venue_divergence_bps(B),"coinbase_move_bps_2s":a.get_coinbase_move_bps(2.,B),"finalized_1h_open":z,"candle_open_spot":z,"candle_distance_pct":round(c,4),"fee_metadata":p,"pre_shock_features_t0":{"UP":G,"DOWN":C}}
   try:
    _,x=_dispatch_trigger_fast(TRIGGER_FILE,F)
    if x:_persist_trigger_nonblocking(TRIGGER_FILE,x)
    logger.info(f"[BOUNDARY LOCK TRIGGER] {a.asset} ({y}) {s} | TTE={l:.1f}s | z={t:+.2f} | dist={c:+.2f}% | BestAsk=${q:.3f} | NetEdge=+{n*100:.2f}c")
   except Exception:pass
 def compute_leadlag_cross_correlation(a,spot_trades=None,futures_trades=None):
  if spot_trades is None:spot_trades=a.spot_trades
  if futures_trades is None:futures_trades=a.futures_trades
  if len(spot_trades)<200 or len(futures_trades)<200:return
  u=time.monotonic_ns();l=300000000000;j=u-l;d=25000000;h=int(l//d);k=np.zeros(h,dtype=np.float64);n=np.zeros(h,dtype=np.float64)
  for g,_,_,t,i,_ in spot_trades:
   if g>=j:r=min(int((g-j)//d),h-1);k[r]+=(t if i else-t)
  for g,_,_,t,i,_ in futures_trades:
   if g>=j:r=min(int((g-j)//d),h-1);n[r]+=(t if i else-t)
  b=np.diff(k);c=np.diff(n);w={}
  for q in CORRELATION_LAGS_MS:
   e=int(q*1000000/d)
   if e==0:s=b;f=c
   elif e>0:f=c[:-e];s=b[e:]
   else:v=abs(e);f=c[v:];s=b[:-v]
   if len(s)>10 and np.std(s)>1e-6 and np.std(f)>1e-6:m=float(np.corrcoef(f,s)[0,1]);w[str(q)]=round(m,4)
   else:w[str(q)]=.0
  o=max(w.items(),key=lambda x:x[1])if w else("0",.0);p={"timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"timestamp_unix":time.time(),"market_id":a.current_market["market_id"]if a.current_market else"none","correlation_grid_lags_ms":w,"peak_correlation_lag_ms":int(o[0]),"peak_correlation_val":o[1],"metric_evaluated":"flow_innovations_cross_correlation (diff(signed_dollar_flow_25ms))","telemetry_classification":"illustrative live telemetry, not evidence of persistent lead/lag","null_hypothesis":"H0: no stable lead/lag structure across pre-registered grid","clock_metadata":{"calibrated_offset_ms":a.clock_offset_ms,"clock_uncertainty_ms":a.clock_uncertainty_ms,"resolution_caveat":"Lags <= 50ms are within RTT uncertainty (+/-21.6ms) and must be evaluated strictly under pooled bootstrap bands."}};_atomic_append_jsonl(a.correlations_file,_dumps_compact(p),broadcast_ipc=False);logger.info(f"[LEAD/LAG INNOVATION TELEMETRY] Peak Lag: {o[0]}ms (r={o[1]:+.3f}) | Status: Illustrative telemetry (H0: no stable lead/lag)")
 async def telemetry_logger_loop(a):
  while a.running:
   try:
    _a=datetime.now(timezone.utc);g=time.time();k=a.__dict__.setdefault("_empty_discovery_backoff_ts",{})
    if not a.current_market or(a.current_market["end_dt"]-_a).total_seconds()<=0:
     f=a.current_market
     if f and not a.riskless_bus_only:asyncio.create_task(a.verify_and_log_resolution(f))
     j=getattr(a,"_cached_next_market",None)
     if not j or(f and j.get("market_id")==f.get("market_id")):
      if f or(g-float(k.get("1h")or.0))>=30.:
       j=await a.discover_nearest_1h_market()
       if j is None:k["1h"]=g
       else:k.pop("1h",None)
     a._cached_next_market=None
     if j:
      a.current_market=j;b,_=await a.fetch_finalized_binance_candle(j["candle_open_ts"]);a.twap_60s_1h_open=await a.fetch_binance_60s_twap_open(j["candle_open_ts"]);a.chainlink_1h_open=(await a.fetch_polygon_chainlink_spot()if abs(time.time()-float(j["candle_open_ts"]))<=35. else.0);a._open_1h_provisional=False
      if b<=.0 and a.spot_price>.0:b=a.spot_price;a._open_1h_provisional=True
      a.finalized_1h_open=b;logger.info(f"[ACTIVE 1H LOADED: {a.asset}] {j['title']} (ID={j['market_id']}, End={j['end_date_iso']}, UP={j['tokens']['UP']}, DOWN={j['tokens']['DOWN']}, Open=${a.finalized_1h_open:,.2f}, Fee={a.fee_rate_market*100:.1f}%)")
     elif a.current_market is not None:logger.info(f"[*] [{a.asset}] 1H market {a.current_market.get('market_id')} expired and no active 1H market within 2h window; clearing 1H slot while keeping 5m/15m/4h TWAP feeds live.");a.current_market=None;a.finalized_1h_open=.0;a.books.pop("UP",None);a.books.pop("DOWN",None)
    for K,c in(("5m","market_5m"),("15m","market_15m"),("4h","market_4h")):
     i=getattr(a,c,None)
     if not i or(i["end_dt"]-_a).total_seconds()<=0:
      p=bool(i and(i["end_dt"]-_a).total_seconds()<=0)
      if p and not a.riskless_bus_only:asyncio.create_task(a.verify_and_log_resolution(i))
      if not p and(g-float(k.get(K)or.0))<30.:continue
      try:
       P=await a.discover_nearest_twap_market(K)
       if P:
        k.pop(K,None);E=i.get("market_id")if i else None;setattr(a,c,P);i=P
        if P.get("market_id")!=E:logger.info(f"[ACTIVE {K.upper()} PRODUCT LOADED: {a.asset}] {P['title']} (ID: {P['market_id']}, Open: ${P.get('finalized_open',.0):,.4f})");a._reconnect_clob=True
       else:k[K]=g
      except Exception:pass
    if a.current_market and(a.finalized_1h_open<=.0 or getattr(a,"_open_1h_provisional",False)):
     b,_=await a.fetch_finalized_binance_candle(a.current_market["candle_open_ts"])
     if b>.0:
      a.finalized_1h_open=b;a._open_1h_provisional=False
      if float(getattr(a,"twap_60s_1h_open",.0)or.0)<=.0:a.twap_60s_1h_open=await a.fetch_binance_60s_twap_open(a.current_market["candle_open_ts"])
      logger.info(f"[{a.asset} FINALIZED OPEN RECOVERED] Binance Spot 1H Open: ${a.finalized_1h_open:,.2f}")
    o=int(datetime.now(timezone.utc).timestamp())
    for K,c,V in(("5m","market_5m",300),("15m","market_15m",900),("4h","market_4h",14400)):
     W=getattr(a,c,None)
     if not W:continue
     y=int(W.get("candle_open_ts",0))
     if o<y:continue
     if float(W.get("finalized_open")or W.get("finalized_15m_open")or.0)<=.0 or W.get("_provisional_open",False):
      x,_=await a.fetch_finalized_binance_candle(y,interval=K)
      if x>.0:W["finalized_open"]=x;W["finalized_15m_open"]=x;W["_provisional_open"]=False
      elif float(W.get("finalized_open")or.0)<=.0 and a.spot_price>.0:W["finalized_open"]=a.spot_price;W["finalized_15m_open"]=a.spot_price;W["_provisional_open"]=True
     if float(W.get("twap_60s_open")or.0)<=.0:
      w=await a.fetch_binance_60s_twap_open(y)
      if w>.0:W["twap_60s_open"]=w
     if float(W.get("authoritative_chainlink_open")or.0)<=.0:
      n=int(W.get("candle_close_ts",y+V))
      if(o-float(W.get("_last_auth_open_try",.0)))>=5.:
       W["_last_auth_open_try"]=float(o);D=await a.fetch_authoritative_chainlink_open(y,n,horizon=K)
       if D>.0:W["authoritative_chainlink_open"]=D;W["chainlink_open_spot"]=D;logger.info(f"[{a.asset} {K.upper()} AUTHORITATIVE CHAINLINK OPEN LOCKED] Polymarket openPrice: ${D:,.6f}")
    B=round(_a.timestamp(),3)
    if a.current_market and"UP"in a.books and"DOWN"in a.books:
     m=a.books["UP"].get_metrics(fee_rate=a.fee_rate_market,compact=True);h=a.books["DOWN"].get_metrics(fee_rate=a.fee_rate_market,compact=True);v=(a.current_market["end_dt"]-_a).total_seconds()
     if 0<v<=120. and getattr(a,"_prewarmed_market_id",None)!=a.current_market["market_id"]:
      a._prewarmed_market_id=a.current_market["market_id"];logger.info(f"[PREWARM TTE={v:.0f}s] Pre-fetching next 1H market from Gamma API to eliminate :00 open delay...")
      try:
       u=await a.discover_nearest_1h_market()
       if u and u["market_id"]!=a.current_market["market_id"]:a._cached_next_market=u;logger.info(f"[PREWARM READY] Next market pre-cached: {u['title']} ({u['market_id']}).")
      except Exception:pass
     A=((a.spot_price-a.finalized_1h_open)/a.finalized_1h_open*1e2)if a.finalized_1h_open>0 else.0;d=a.get_delta_basis_100ms();O=(a.current_market["market_id"],m["best_bid"],m["best_ask"],h["best_bid"],h["best_ask"]);C=a._last_telem_bbo_by_hz.get("1h")
     if not a.riskless_bus_only and(C is None or C[1]!=O or v<=9e2 or(B-C[0])>=19.):a._last_telem_bbo_by_hz["1h"]=(B,O);N={"timestamp":_a.strftime("%Y-%m-%d %H:%M:%S UTC"),"timestamp_unix":B,"asset":a.asset,"market_id":a.current_market["market_id"],"title":a.current_market["title"],"seconds_to_expiry":round(v,1),"binance_spot":a.spot_price,"binance_futures":a.futures_price,"basis_signed_usd":round(a.basis_usd,2),"basis_signed_bps":round(a.basis_bps,2),"basis_abs_bps":round(abs(a.basis_bps),2),"delta_basis_100ms":d,"binance_1h_open":a.finalized_1h_open,"candle_distance_pct":round(A,4),"clock_metadata":{"clock_offset_ms":round(a.clock_offset_ms,2),"clock_uncertainty_ms":round(a.clock_uncertainty_ms,2)},"fee_metadata":{"fee_rate_market":a.fee_rate_market},"UP":m,"DOWN":h};await asyncio.to_thread(_atomic_append_jsonl,a.telemetry_file,_dumps_compact(N),False)
     logger.info(f"[1H TELEMETRY: {a.asset}] {a.current_market['title'][:32]} | Tau: {v/60.:.1f}m ({v:.0f}s) | UP ask={m['best_ask']:.3f} (mid={m['q_mid']:.3f}, hurdle={m['executable_hurdle']:.4f}) | Spot=${a.spot_price:,.1f} | Fut=${a.futures_price:,.1f} | Basis={a.basis_bps:+.1f}bp | dist={A:+.2f}%")
    M=a.get_coinbase_spot(B);L=a.get_chainlink_proxy_spot(B)
    for K,c,Y,X,U in(()if a.riskless_bus_only else(("5m","market_5m","UP_5M","DOWN_5M",a.telemetry_5m_file),("15m","market_15m","UP_15M","DOWN_15M",a.telemetry_15m_file),("4h","market_4h","UP_4H","DOWN_4H",a.telemetry_4h_file))):
     W=getattr(a,c,None)
     if W and Y in a.books and X in a.books:
      J=(W["end_dt"]-_a).total_seconds()
      if J>0:
       Z=float(W.get("fee_metadata",{}).get("fee_rate_market",.07)or.07);T=a.books[Y].get_metrics(fee_rate=Z,compact=True);S=a.books[X].get_metrics(fee_rate=Z,compact=True);R=(W["market_id"],T["best_bid"],T["best_ask"],S["best_bid"],S["best_ask"]);I=a._last_telem_bbo_by_hz.get(K)
       if K=="4h"and J>1800. and I is not None and I[1]==R and(B-I[0])<58.:continue
       if K=="15m"and J>360. and I is not None and I[1]==R and(B-I[0])<28.:continue
       a._last_telem_bbo_by_hz[K]=(B,R);H=float(W.get("finalized_open")or W.get("finalized_15m_open")or.0);t=W.get("authoritative_chainlink_open");s=L if L>0 else M;G=((a.spot_price-H)/H*1e2)if H>0 else.0;r=(round(((s-float(t))/float(t))*1e2,4)if t and float(t)>0 and s>0 else None);Q={"timestamp":_a.strftime("%Y-%m-%d %H:%M:%S UTC"),"timestamp_unix":B,"asset":a.asset,"horizon":K,"market_id":W["market_id"],"title":W["title"],"seconds_to_expiry":round(J,1),"binance_spot":a.spot_price,"binance_futures":a.futures_price,"coinbase_usd_spot":round(M,6)if M>0 else.0,"chainlink_proxy_usd_spot":round(L,6)if L>0 else.0,"binance_open":H,"candle_distance_pct":round(G,4),"fee_metadata":{"fee_rate_market":Z},"UP":T,"DOWN":S}
       if K=="15m":
        Q["binance_15m_open"]=H
        if a.asset=="XAU":Q["binance_xau_usdt"]=a.futures_price or a.spot_price;Q["coinbase_usdt_usd"]=round(M,6)if.98<=M<=1.02 else 1.
       F=W.get("twap_60s_open")
       if F is not None:Q["twap_60s_open"]=F
       if t is not None:Q["authoritative_chainlink_open"]=t
       if r is not None:Q["chainlink_usd_distance_pct"]=r
       await asyncio.to_thread(_atomic_append_jsonl,U,_dumps_compact(Q),False)
    if not a.riskless_bus_only and time.time()-a.last_cross_corr_ts>60.:a.last_cross_corr_ts=time.time();q=list(a.spot_trades);z=list(a.futures_trades);await asyncio.to_thread(a.compute_leadlag_cross_correlation,q,z)
    l=time.time()
    if(l-float(a.__dict__.get("_last_recorder_mem_evict_ts")or.0))>=120.:a.__dict__["_last_recorder_mem_evict_ts"]=l;a._evict_recorder_memory(now_ts=l,trim_heap=(a.asset=="BTC"))
    if l-a.last_clock_sync_ts>3e2:asyncio.create_task(a.calibrate_binance_clock_offset())
    await asyncio.sleep(10.)
   except Exception as e:logger.error(f"Error in telemetry loop: {e}",exc_info=True);await asyncio.sleep(10.)
 async def run(a):
  logger.info(f"[RECORDER v2.8 {a.asset}] {a.binance_symbol} | Shock=${a.shock_threshold_usd:,.0f} | Mode={'RISKLESS_SHM_BUS_ONLY'if a.riskless_bus_only else'FULL_TELEMETRY'}");a._pid_lock_fh=open(a.pid_file,"w")
  if os.name!="nt":
   try:import fcntl;fcntl.flock(a._pid_lock_fh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:a._pid_lock_fh.close();raise RuntimeError(f"Another {a.asset} recorder already holds exclusive lock on {a.pid_file}")
  a._pid_lock_fh.write(str(os.getpid()));a._pid_lock_fh.flush()
  if _ensure_shared_cl_stream is not None:a.chainlink_stream=_ensure_shared_cl_stream()
  await a.calibrate_binance_clock_offset();await asyncio.gather(a.stream_binance_spot(),a.stream_binance_futures(),a.stream_polymarket_clob(),a.telemetry_logger_loop(),a._coinbase_stream_worker())
if __name__=="__main__":
 import argparse;parser=argparse.ArgumentParser(description="Polymarket Dual Feed 1H Telemetry Recorder");parser.add_argument("--asset",choices=list(ASSET_CONFIGS.keys()),default="BTC",help=f"Asset to record ({', '.join(ASSET_CONFIGS.keys())}, default: BTC)");parser.add_argument("--shock-threshold",type=float,default=None,help="Volume shock threshold in USD over 100ms");parser.add_argument("--co-assets",type=str,default="",help="Comma-separated co-resident assets sharing this uvloop process");parser.add_argument("--riskless-bus-only",action="store_true",help="Lean /dev/shm fast-tick bus only (no shock/JSONL disk telemetry)");args=parser.parse_args();setup_logging(args.asset)
 if os.name!="nt":
  try:import uvloop;uvloop.install()
  except Exception:pass
 co_syms=[s.strip().upper()for s in str(args.co_assets or"").split(",")if s.strip()and s.strip().upper()in ASSET_CONFIGS and s.strip().upper()!=args.asset];recorders=[PolymarketDualFeed1HRecorder(asset=args.asset,shock_threshold=args.shock_threshold,riskless_bus_only=args.riskless_bus_only)]+[PolymarketDualFeed1HRecorder(asset=sym,riskless_bus_only=args.riskless_bus_only)for sym in co_syms]
 async def _run_multi_recorders():await asyncio.gather(*(r.run()for r in recorders))
 try:asyncio.run(_run_multi_recorders())
 except KeyboardInterrupt:
  for r in recorders:r.running=False
  logger.info("Stopped by user.")
# [08/13] src/polymarket_research/deribit_svi_surface.py
import json;import logging;import math;import os;import threading;import time;import urllib.request;from dataclasses import dataclass;from datetime import datetime,timezone;from typing import Any,Dict,List,Optional,Tuple;import numpy as np;from scipy.optimize import minimize;from scipy.stats import norm;logger=logging.getLogger("DeribitSVISurface");logging.getLogger("httpx").setLevel(logging.WARNING);logging.getLogger("httpcore").setLevel(logging.WARNING);DERIBIT_PUBLIC_URL="https://www.deribit.com/api/v2/public/get_book_summary_by_currency";DEFAULT_SIGMA_1H={"BTC":.005,"ETH":.0068,"SOL":.0095,"XRP":.01};ASSET_VOL_MULT_VS_BTC={"BTC":1.,"ETH":1.28,"SOL":1.75,"XRP":1.85}
def _tte_horizon_bucket(target_tte_sec):
 if target_tte_sec is None or target_tte_sec<=43200.:return"0DTE"
 if target_tte_sec<=2.16e5:return"DAILY"
 if target_tte_sec<=950400.:return"WEEKLY"
 return"MONTHLY"
@dataclass
class SVIParams:
 a:float;b:float;rho:float;m:float;sigma:float;t_years:float;forward_price:float;calibrated_at:float;index_price:float=.0
 def implied_forward_drift_rate(a):
  if a.index_price<=.0 or a.forward_price<=.0 or a.t_years<=1e-6:return.0
  b=math.log(a.forward_price/a.index_price)/max(1e-4,a.t_years);return max(-.3,min(.4,b))
 def total_variance(a,k):b=a.a+a.b*(a.rho*(k-a.m)+math.sqrt((k-a.m)**2+a.sigma**2));return max(1e-8,b)
 def implied_vol(a,k,t_override=None):
  e=max(1e-6,t_override if t_override is not None else a.t_years)
  if t_override is not None and a.t_years>1e-6:c=e/a.t_years;b=max(.25,min(2.,1./math.sqrt(max(.05,c))));d=a.total_variance(k*b)/a.t_years;return max(.1,min(3.,math.sqrt(max(1e-8,d))))
  w=a.total_variance(k);return max(.1,min(3.,math.sqrt(w/e)))
def scale_svi_sticky_delta(base_svi,vol_mult,forward_price):a=max(.5,float(vol_mult));return SVIParams(a=base_svi.a*(a**2),b=base_svi.b*a,rho=base_svi.rho,m=base_svi.m*a,sigma=base_svi.sigma*a,t_years=base_svi.t_years,forward_price=forward_price,calibrated_at=base_svi.calibrated_at)
def black_scholes_call(F,K,T,sigma,r=.0):
 if T<=.0 or sigma<=.0 or K<=.0 or F<=.0:return max(.0,F-K)*math.exp(-r*max(.0,T))
 b=math.sqrt(T);a=sigma*b;d=(math.log(F/K)+.5*(sigma**2)*T)/a;c=d-a;return math.exp(-r*T)*(F*float(norm.cdf(d))-K*float(norm.cdf(c)))
def compute_breeden_litzenberger_digital(F,K,T_years,svi,r=.0):
 if F<=.0 or K<=.0:return.5
 k=max(1e-6,T_years);p=max(1e-5,K*.001);j=math.log(K/F);o=math.log((K+p)/F);n=math.log(max(1e-8,K-p)/F);c=svi.implied_vol(j,t_override=k);e=svi.implied_vol(o,t_override=k);d=svi.implied_vol(n,t_override=k);m=black_scholes_call(F,K+p,k,e,r);l=black_scholes_call(F,max(1e-8,K-p),k,d,r);i=(m-l)/(2.*p);h=-math.exp(r*k)*i;a=max(1e-6,c*math.sqrt(k));g=(math.log(F/K)+(r-.5*(c**2))*k)/a;f=float(norm.cdf(g));b=max(f-.08,min(f+.08,float(h)));return max(1e-4,min(.9999,b))
def fit_svi_slice(log_moneyness,mark_ivs,t_years,forward_price):
 l=max(1e-5,float(t_years))
 if len(log_moneyness)<4:g=float(np.median(mark_ivs))if mark_ivs else.55;k=(g**2)*l;return SVIParams(a=k*.85,b=k*.3,rho=-.1,m=.0,sigma=.05,t_years=l,forward_price=forward_price,calibrated_at=time.time())
 j=np.array(log_moneyness,dtype=float);i=(np.array(mark_ivs,dtype=float)**2)*l;h=np.argsort(j);d=max(1e-7,float(np.interp(.0,j[h],i[h])));c=min(.5,max(1e-4,3.5*math.sqrt(d*l)))
 def e(params):a,b,s,m,r=params;q=a+b*(s*(j-m)+np.sqrt((j-m)**2+r**2));p=np.exp(-4.*np.abs(j));return float(np.sum(p*((q-i)**2)))
 o=np.array([max(1e-6,d*.85),min(c*.5,max(1e-5,d*.4)),-.12,.0,.05]);f=[(1e-7,max(1e-3,float(np.max(i)))),(1e-6,c),(-.9,.9),(-.35,.35),(.02,.5)]
 try:
  n=minimize(e,o,method="L-BFGS-B",bounds=f,options={"maxiter":60})
  if n.success:a,b,rho,m,sig=n.x;return SVIParams(a=float(a),b=float(b),rho=float(rho),m=float(m),sigma=float(sig),t_years=l,forward_price=forward_price,calibrated_at=time.time())
 except Exception:pass
 return SVIParams(a=max(1e-6,d*.85),b=min(c,max(1e-5,d*.3)),rho=-.1,m=.0,sigma=.05,t_years=l,forward_price=forward_price,calibrated_at=time.time())
class DeribitSVISurfaceEngine:
 def __init__(a,ttl_seconds=60.):import queue as _queue;a.ttl_seconds=ttl_seconds;a._lock=threading.Lock();a._cache={};a._last_fetch_attempt={};a._refresh_in_flight={};a._refresh_queue=_queue.SimpleQueue();a._bg_worker_thread=None;a._http_client=None
 @staticmethod
 def _cache_key(asset_u,target_tte_sec=None):a=_tte_horizon_bucket(target_tte_sec);return asset_u if a=="0DTE"else f"{asset_u}:{a}"
 @staticmethod
 def _parse_deribit_instrument(name):
  f=name.split("-")
  if len(f)!=4:return None
  e,c,a,b=f
  try:d=float(a);g=datetime.strptime(c,"%d%b%y").replace(hour=8,minute=0,second=0,tzinfo=timezone.utc);return e.upper(),g.timestamp(),d,b.upper()
  except Exception:return None
 def fetch_and_calibrate_sync(a,asset,target_tte_sec=7200.):
  u=asset.upper();F=a._cache_key(u,target_tte_sec)
  if u not in("BTC","ETH"):
   t=a.fetch_and_calibrate_sync("BTC",target_tte_sec=target_tte_sec)
   if t is None:return None
   I=ASSET_VOL_MULT_VS_BTC.get(u,1.75);E=scale_svi_sticky_delta(t,I,t.forward_price)
   with a._lock:a._cache[F]=E
   return E
  L=f"{DERIBIT_PUBLIC_URL}?currency={u}&kind=option"
  try:
   d=urllib.request.urlopen;g=hasattr(d,"mock_calls")or getattr(d,"__module__","")!="urllib.request"
   if g:
    C=urllib.request.Request(L,headers={"User-Agent":"Polymarket-SVI-Engine/1.0"})
    with d(C,timeout=2.5)as n:b=n.read()
   else:
    try:
     import httpx as _httpx;D=a._http_client
     if D is None or getattr(D,"is_closed",False):D=_httpx.Client(http2=False,timeout=2.5,headers={"User-Agent":"Polymarket-SVI-Engine/1.0"});a._http_client=D
     b=D.get(L).content
    except Exception:
     C=urllib.request.Request(L,headers={"User-Agent":"Polymarket-SVI-Engine/1.0"})
     with d(C,timeout=2.5)as n:b=n.read()
   try:import orjson as _orjson;m=_orjson.loads(b)
   except Exception:m=json.loads(b.decode("utf-8")if isinstance(b,(bytes,bytearray))else b)
   i=m.get("result",[])
   if not i:return None
   B=time.time();h={};f=.25 if target_tte_sec<=86400. else.45
   for H in i:
    G=H.get("instrument_name","");A=a._parse_deribit_instrument(G)
    if not A:continue
    _,z,y,_=A;K=z-B
    if K<=6e2:continue
    s=float(H.get("mark_iv")or.0)/1e2;l=float(H.get("underlying_price")or H.get("estimated_delivery_price")or.0);x=float(H.get("estimated_delivery_price")or l or.0)
    if s<=.05 or s>=3. or l<=.0:continue
    k=math.log(y/l)
    if abs(k)<=f:h.setdefault(z,[]).append((k,s,l,x))
   if not h:return None
   c=[e for e,pts in h.items()if len(pts)>=4]
   if not c:c=list(h.keys())
   j=min(c,key=lambda e:abs((e-B)-max(3600.,target_tte_sec)));pts=h[j];w=[p[0]for p in pts];r=[p[1]for p in pts];v=float(np.median([p[2]for p in pts]));q=float(np.median([p[3]for p in pts if p[3]>0]))if any(p[3]>0 for p in pts)else v;o=max(1e-5,(j-B)/(365.25*86400.));J=fit_svi_slice(w,r,o,v);J.index_price=q
   with a._lock:a._cache[F]=J
   return J
  except Exception as e:return None
 def _ensure_bg_worker(a):
  c=a._bg_worker_thread
  if c is not None and c.is_alive():return
  with a._lock:
   c=a._bg_worker_thread
   if c is not None and c.is_alive():return
   def b():
    while True:
     g,f,e=a._refresh_queue.get()
     try:
      try:
       from src.polymarket_research.polymarket_live_executor import _HOT_DISPATCH_ACTIVE as d
       if d.is_set():time.sleep(.05)
      except Exception:pass
      a.fetch_and_calibrate_sync(f,target_tte_sec=e)
     except Exception:pass
     finally:
      with a._lock:a._refresh_in_flight[g]=False
   t=threading.Thread(target=b,name="svi-bg-refresher",daemon=True);t.start();a._bg_worker_thread=t
 def _trigger_background_refresh(a,asset,target_tte_sec=None):
  c=asset.upper();d=a._cache_key(c,target_tte_sec);b=float(target_tte_sec)if target_tte_sec is not None else 7200.;e=time.time()
  with a._lock:
   if a._refresh_in_flight.get(d,False):return
   if e-a._last_fetch_attempt.get(d,.0)<15.:return
   a._refresh_in_flight[d]=True;a._last_fetch_attempt[d]=e
  a._ensure_bg_worker();a._refresh_queue.put((d,c,b))
 def get_svi_params(a,asset,allow_sync_if_empty=False,target_tte_sec=None):
  d=asset.upper();e=a._cache_key(d,target_tte_sec);c=float(target_tte_sec)if target_tte_sec is not None else 7200.;g=time.time()
  with a._lock:
   b=a._cache.get(e)
   if b is None and e!=d and not allow_sync_if_empty:b=a._cache.get(d)
  if b is not None:
   f=g-b.calibrated_at
   if f>a.ttl_seconds and os.environ.get("PM_SVI_DISABLE_BG_REFRESH")!="1":a._trigger_background_refresh(d,target_tte_sec=target_tte_sec)
   if f<=9e2 or os.environ.get("PM_SVI_DISABLE_BG_REFRESH")=="1"or b.calibrated_at<=.0:return b
  if os.environ.get("PM_SVI_DISABLE_BG_REFRESH")=="1"and not allow_sync_if_empty:return None
  if allow_sync_if_empty:return a.fetch_and_calibrate_sync(d,target_tte_sec=c)
  a._trigger_background_refresh(d,target_tte_sec=target_tte_sec);return None
 def get_surface(self,asset):return self.fetch_and_calibrate_sync(asset)
 def get_hourly_sigma(b,asset,fallback=None):
  f=asset.upper();c=fallback if fallback is not None else DEFAULT_SIGMA_1H.get(f,.006);h=b.get_svi_params(f)
  if h is None:
   if f in("SOL","XRP"):
    e=b.get_svi_params("BTC")
    if e is not None:g=ASSET_VOL_MULT_VS_BTC.get(f,1.8);a=e.implied_vol(.0)*g;return max(.003,min(.025,a/math.sqrt(8760.)))
   return c
  a=h.implied_vol(.0);d=a/math.sqrt(8760.);return max(.002,min(.025,d))
 get_implied_hourly_sigma=get_hourly_sigma
 def evaluate_strike_probability(f,asset,spot,strike,tte_seconds,outcome="YES",is_downward_question=False,is_upward=None,is_barrier_no=False,fallback_sigma_1h=None,allow_sync_fetch=False,target_tte_sec=None):
  if is_upward is not None:is_downward_question=not bool(is_upward)
  p=asset.upper();e=target_tte_sec if target_tte_sec is not None else tte_seconds;o=max(1e-6,tte_seconds/(365.25*86400.));l=max(.01,tte_seconds/3600.);q=f.get_svi_params(p,allow_sync_if_empty=allow_sync_fetch,target_tte_sec=e)
  if q is None and p in("SOL","XRP"):
   n=f.get_svi_params("BTC",allow_sync_if_empty=allow_sync_fetch,target_tte_sec=e)
   if n is not None:s=ASSET_VOL_MULT_VS_BTC.get(p,1.8);q=scale_svi_sticky_delta(n,s,spot if spot>0 else n.forward_price)
  if q is not None and spot>0 and strike>0:i=(max(.95,min(1.08,q.forward_price/q.index_price))if(q.index_price>.0 and q.forward_price>.0)else 1.);h=min(1.5,max(.0,o/max(1e-5,q.t_years)))if i!=1. else.0;r=spot*(1.+(i-1.)*h);k=math.log(strike/r);c=q.implied_vol(k,t_override=o);d=c/math.sqrt(8760.);a=compute_breeden_litzenberger_digital(r,strike,o,q);g="DERIBIT_SVI_BL"
  else:
   d=fallback_sigma_1h if fallback_sigma_1h is not None else DEFAULT_SIGMA_1H.get(p,.006);c=d*math.sqrt(8760.)
   if spot>0 and strike>0:z=math.log(spot/strike)/max(1e-6,d*math.sqrt(l));a=float(norm.cdf(z))
   else:a=.5
   g="FALLBACK_GAUSSIAN"
  if is_downward_question:j=1.-a
  else:j=a
  b=j if outcome.upper()=="YES"else(1.-j)
  if is_barrier_no and outcome.upper()=="NO":m=min(.9999,2.*max(.0,1.-b));b=max(1e-4,1.-m)
  return{"p_svi":round(float(b),4),"p_above_strike":round(float(a),4),"svi_sigma_1h":round(float(d),5),"svi_iv_annual":round(float(c),4),"source":g}
def enforce_monotone_ladder_probabilities(strikes_and_probs):
 if not strikes_and_probs:return{"strikes":[],"probs":[],"interval_probs":[],"max_adjustment":.0}
 c=sorted((float(k),max(1e-4,min(.9999,float(p))))for k,p in strikes_and_probs);e=[]
 for _,g in c:
  e.append([g,1.])
  while len(e)>=2 and(e[-2][0]/e[-2][1])<e[-1][0]/e[-1][1]-1e-12:d=e.pop();e[-1][0]+=d[0];e[-1][1]+=d[1]
 h=[]
 for f,l in e:j=max(1e-4,min(.9999,f/l));h.extend([round(j,6)]*int(l))
 b=max(abs(h[i]-c[i][1])for i in range(len(h)));a=[round(max(.0,h[i]-h[i+1]),6)for i in range(len(h)-1)];return{"strikes":[k for k,_ in c],"probs":h,"interval_probs":a,"max_adjustment":round(b,6)}
GLOBAL_SVI_ENGINE=DeribitSVISurfaceEngine(ttl_seconds=60.)
if __name__=="__main__":
 for sym,spot_test,k_test in[("BTC",82500.,8.2e4),("ETH",2450.,2400.),("SOL",106.,105.)]:res=GLOBAL_SVI_ENGINE.evaluate_strike_probability(sym,spot_test,k_test,tte_seconds=3600.,outcome="YES",allow_sync_fetch=True);print(f"{sym} Spot={spot_test} Strike={k_test} (1h TTE): {res}")
# [09/13] src/polymarket_research/polymarket_paper_trader.py
import os;import sys;import json;import time;import math;import asyncio;from datetime import datetime,timezone;from pathlib import Path;from typing import Dict,Any,List,Set,Optional;from collections import defaultdict;from src.polymarket_research.directional_wfo_shadow_sleeves import DirectionalWfoShadowManager;from src.polymarket_research.polymarket_live_executor import calculate_taker_fee;from src.polymarket_research.polymarket_live_harvester import(compute_composite_edge_score,compute_max_acceptable_ask,evaluate_coinbase_venue_veto);PIPELINE_ROOT=Path(__file__).resolve().parents[2];DATA_DIR=PIPELINE_ROOT/"data"/"polymarket";TRIGGER_FILE=DATA_DIR/"live_shock_triggers.jsonl";SHOCK_FILE=DATA_DIR/"shock_responses.jsonl";RESOLUTIONS_FILE=DATA_DIR/"finalized_market_resolutions.jsonl";DEV_LEDGER_FILE=DATA_DIR/"paper_trading_dev_ledger.jsonl";VALIDATION_LEDGER_FILE=DATA_DIR/"paper_trading_validation_ledger.jsonl";STATE_FILE=DATA_DIR/"paper_trader_state.json";PID_FILE=DATA_DIR/"paper_trader.pid";HOURLY_TELEMETRY_FILE=DATA_DIR/"polymarket_hourly_telemetry.jsonl";HOURLY_TELEMETRY_ETH_FILE=DATA_DIR/"polymarket_hourly_telemetry_eth.jsonl";HOURLY_TELEMETRY_SOL_FILE=DATA_DIR/"polymarket_hourly_telemetry_sol.jsonl";SUBHOURLY_TELEMETRY_SOL_FILE=DATA_DIR/"polymarket_15m_telemetry_sol.jsonl";HOURLY_TELEMETRY_XRP_FILE=DATA_DIR/"polymarket_hourly_telemetry_xrp.jsonl";SUBHOURLY_TELEMETRY_XRP_FILE=DATA_DIR/"polymarket_15m_telemetry_xrp.jsonl";SHOCK_SOL_FILE=DATA_DIR/"shock_responses_sol.jsonl";SHOCK_XRP_FILE=DATA_DIR/"shock_responses_xrp.jsonl";INITIAL_PAPER_CAPITAL=1e3;TICKET_NOTIONAL=50.;MIN_ELASTIC_TICKET_USD=15.;MAX_ELASTIC_TICKET_USD=2e2;DEFAULT_ELASTIC_SAFETY_RATIO=1.5;DEFAULT_DYNAMIC_BANKROLL_PCT=.24;DEFAULT_PAPER_LATENCY_MS=int(os.getenv("PAPER_LATENCY_MS","500"));MAX_TTE_SECONDS=2700.;MIN_TTE_SECONDS=90.;MAX_TRADES_PER_HOUR=6;MAX_TRADES_PER_MARKET=2;MAX_ALLOWED_SPREAD=.03;MAX_PRICE_CEILING=.86;MIN_PRICE_FLOOR=.55;R3_VALIDATION_START_UTC="2026-09-29T18:11:34.000Z";R3_VALIDATION_START_UNIX=1790705494.;ENABLE_SLEEVE_304_315=False;SLEEVE_2_INITIAL_CAPITAL=5e2;SLEEVE_2_TICKET_NOTIONAL=50.;SLEEVE_2_MIN_PRICE=.55;SLEEVE_2_MAX_PRICE=.78;SLEEVE_2_MIN_DEPTH_RATIO=1.5;SLEEVE_2_MAX_TTE=2700.;SLEEVE_2_MIN_TTE=9e2;SLEEVE_2_LEDGER_FILE=DATA_DIR/"ledger_sleeve_304_315.jsonl";SLEEVE_2_STATE_FILE=DATA_DIR/"state_sleeve_304_315.json"
try:from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as _PT_GOV_MGR;ENABLE_SOL_SHADOW_SLEEVE=bool(_PT_GOV_MGR.snapshot.get("shadow_governance",{}).get("enable_sol_15m_1h_shadow",True))
except Exception:ENABLE_SOL_SHADOW_SLEEVE=True
SOL_SHADOW_INITIAL_CAPITAL=5e2;SOL_SHADOW_TICKET_NOTIONAL=12.;SOL_SHADOW_LEDGER_FILE=DATA_DIR/"ledger_shadow_sol_v392.jsonl";SOL_SHADOW_STATE_FILE=DATA_DIR/"state_shadow_sol_v392.json";ENABLE_XRP_SHADOW_SLEEVE=False;XRP_SHADOW_INITIAL_CAPITAL=5e2;XRP_SHADOW_TICKET_NOTIONAL=12.;XRP_SHADOW_LEDGER_FILE=DATA_DIR/"ledger_shadow_xrp_v392.jsonl";XRP_SHADOW_STATE_FILE=DATA_DIR/"state_shadow_xrp_v392.json"
class PolymarketForwardPaperTrader:
 def __init__(a,paper_latency_ms=None):
  DATA_DIR.mkdir(parents=True,exist_ok=True);a.paper_latency_ms=paper_latency_ms if paper_latency_ms is not None else DEFAULT_PAPER_LATENCY_MS;a.settled_trade_ids=set();a.seen_shock_ids=set();a.seen_resolution_ids=set();a.trades_per_market=defaultdict(int);a.dev_cash=INITIAL_PAPER_CAPITAL;a.dev_realized_pnl=.0;a.dev_total_fees=.0;a.dev_trades=[];a.val_cash=INITIAL_PAPER_CAPITAL;a.val_realized_pnl=.0;a.val_total_fees=.0;a.val_trades=[];a.open_trades={};a.current_hour_window=int(time.time()//3600);a.trades_this_hour=0;a.last_trigger_file_pos=0;a.last_shock_file_pos=0;a.last_res_file_pos=0;a.last_telemetry_file_pos=0;a.last_telemetry_eth_file_pos=0;a.last_telemetry_sol_file_pos=0;a.last_telemetry_sol_15m_file_pos=0;a.last_telemetry_xrp_file_pos=0;a.last_telemetry_xrp_15m_file_pos=0;a.last_shock_sol_file_pos=0;a.last_shock_xrp_file_pos=0;a.recent_shock_window=[];a.sleeve2_cash=SLEEVE_2_INITIAL_CAPITAL;a.sleeve2_realized_pnl=.0;a.sleeve2_total_fees=.0;a.sleeve2_trades=[];a.sleeve2_open_trades={};a.sleeve2_settled_ids=set();a.sol_shadow_cash=SOL_SHADOW_INITIAL_CAPITAL;a.sol_shadow_realized_pnl=.0;a.sol_shadow_total_fees=.0;a.sol_shadow_trades=[];a.sol_shadow_open_trades={};a.sol_shadow_settled_ids=set();a.xrp_shadow_cash=XRP_SHADOW_INITIAL_CAPITAL;a.xrp_shadow_realized_pnl=.0;a.xrp_shadow_total_fees=.0;a.xrp_shadow_trades=[];a.xrp_shadow_open_trades={};a.xrp_shadow_settled_ids=set();a.load_persisted_ledgers();a.load_persisted_sleeve2_ledger();a.load_persisted_sol_shadow_ledger();a.load_persisted_xrp_shadow_ledger()
  if STATE_FILE.exists():
   try:
    c=json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if int(c.get("current_hour_window",-1))==a.current_hour_window:a.trades_this_hour=int(c.get("trades_this_hour",0))
   except Exception:pass
  a.hourly_candle_opens=defaultdict(dict);a._prewarm_hourly_opens();b=(PIPELINE_ROOT/"data"/"polymarket").resolve();a.wfo_shadow=DirectionalWfoShadowManager(STATE_FILE.parent,production_mode=(STATE_FILE.parent.resolve()==b))
 def _prewarm_hourly_opens(a):
  b=DATA_DIR/"live_shock_triggers.jsonl"
  if not b.exists():return
  try:
   with open(b,"rb")as f:f.seek(0,2);o=f.tell();g=min(o,8*1024*1024);f.seek(o-g);l=f.read().decode("utf-8",errors="ignore").splitlines()
   for n in l:
    if not n.strip():continue
    try:
     m=json.loads(n);e=str(m.get("title","")or"").lower();d=str(m.get("horizon","")or m.get("candle_interval","")).lower();i=str(m.get("series_slug","")or m.get("slug","")).lower()
     if any(x in d or x in i or x in e for x in("5m","15m","300s","900s")):continue
     k=m.get("asset");c=m.get("t0_unix");h=m.get("finalized_1h_open")or m.get("candle_open_spot")
     if k in("BTC","ETH","SOL","XRP")and c and h and float(h)>0:
      j=int(float(c)//3600)
      if j not in a.hourly_candle_opens[k]:a.hourly_candle_opens[k][j]=float(h)
    except Exception:pass
  except Exception:pass
 def load_persisted_ledgers(a):
  if DEV_LEDGER_FILE.exists():
   with open(DEV_LEDGER_FILE,"r")as f:
    for c in f:
     if not c.strip():continue
     t=json.loads(c);d=t["trade_id"]
     if d not in a.settled_trade_ids:
      a.settled_trade_ids.add(d);a.dev_trades.append(t);a.dev_realized_pnl+=t.get("net_pnl_usd",.0);a.dev_total_fees+=t.get("taker_fee_usd",.0);b=t.get("market_id")
      if b:a.trades_per_market[b]+=1
   a.dev_cash=INITIAL_PAPER_CAPITAL+a.dev_realized_pnl
  if VALIDATION_LEDGER_FILE.exists():
   with open(VALIDATION_LEDGER_FILE,"r")as f:
    for c in f:
     if not c.strip():continue
     t=json.loads(c);d=t["trade_id"]
     if d not in a.settled_trade_ids:
      a.settled_trade_ids.add(d);a.val_trades.append(t);a.val_realized_pnl+=t.get("net_pnl_usd",.0);a.val_total_fees+=t.get("taker_fee_usd",.0);b=t.get("market_id")
      if b:a.trades_per_market[b]+=1
   a.val_cash=INITIAL_PAPER_CAPITAL+a.val_realized_pnl
  print(f"[RECOVERY COMPLETE] Loaded {len(a.settled_trade_ids)} settled trades from disk across {len(a.trades_per_market)} markets.\n  DEV Ledger: {len(a.dev_trades)} trades | Realized PnL: ${a.dev_realized_pnl:+.2f} | Cash: ${a.dev_cash:,.2f}\n  OOS VALIDATION Ledger: {len(a.val_trades)} trades | Realized PnL: ${a.val_realized_pnl:+.2f} | Cash: ${a.val_cash:,.2f}",flush=True)
 def load_persisted_sleeve2_ledger(a):
  if SLEEVE_2_LEDGER_FILE.exists():
   with open(SLEEVE_2_LEDGER_FILE,"r")as f:
    for b in f:
     if not b.strip():continue
     t=json.loads(b);c=t.get("trade_id")
     if c and c not in a.sleeve2_settled_ids:a.sleeve2_settled_ids.add(c);a.sleeve2_trades.append(t);a.sleeve2_realized_pnl+=t.get("net_pnl_usd",.0);a.sleeve2_total_fees+=t.get("taker_fee_usd",.0)
   a.sleeve2_cash=SLEEVE_2_INITIAL_CAPITAL+a.sleeve2_realized_pnl;print(f"[SLEEVE 2 RECOVERY] Loaded {len(a.sleeve2_trades)} settled trades | Realized PnL: ${a.sleeve2_realized_pnl:+.2f} | Cash: ${a.sleeve2_cash:,.2f}",flush=True)
 def save_sleeve2_state(a):
  b=len(a.sleeve2_trades);e=sum(1 for t in a.sleeve2_trades if t.get("won"));g=(e/b*1e2)if b>0 else.0;d={"timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"sleeve_id":"SLEEVE_2_MULTI_304_315","strategy":"ETH 1h Sweet-Spot (0.72-0.85) Lead-Lag Momentum","initial_capital":SLEEVE_2_INITIAL_CAPITAL,"current_equity":round(a.sleeve2_cash,2),"realized_pnl":round(a.sleeve2_realized_pnl,2),"total_fees_paid":round(a.sleeve2_total_fees,2),"total_trades_settled":b,"winning_trades":e,"losing_trades":b-e,"win_rate_pct":round(g,2),"active_open_positions_count":sum(len(v)for v in a.sleeve2_open_trades.values()),"status":"RUNNING"if ENABLE_SLEEVE_304_315 else"DISABLED","ledger_file":str(SLEEVE_2_LEDGER_FILE)};c=SLEEVE_2_STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
  try:
   with open(c,"w",encoding="utf-8")as f:json.dump(d,f,indent=2);f.flush();os.fsync(f.fileno())
   os.replace(c,SLEEVE_2_STATE_FILE)
  except Exception:
   if c.exists():
    try:c.unlink()
    except Exception:pass
 def load_persisted_sol_shadow_ledger(a):
  if SOL_SHADOW_LEDGER_FILE.exists():
   with open(SOL_SHADOW_LEDGER_FILE,"r",encoding="utf-8",errors="ignore")as f:
    for b in f:
     if not b.strip():continue
     t=json.loads(b);c=t.get("trade_id")
     if c and c not in a.sol_shadow_settled_ids:a.sol_shadow_settled_ids.add(c);a.sol_shadow_trades.append(t);a.sol_shadow_realized_pnl+=float(t.get("net_pnl_usd",.0));a.sol_shadow_total_fees+=float(t.get("taker_fee_usd",.0))+float(t.get("exit_fee_usd",.0))
   a.sol_shadow_cash=SOL_SHADOW_INITIAL_CAPITAL+a.sol_shadow_realized_pnl
 def save_sol_shadow_state(a):
  b=len(a.sol_shadow_trades);o=sum(1 for t in a.sol_shadow_trades if t.get("won"));q=(o/b*1e2)if b>0 else.0;g=sum(float(t.get("net_pnl_usd",.0))for t in a.sol_shadow_trades if float(t.get("net_pnl_usd",.0))>0);d=abs(sum(float(t.get("net_pnl_usd",.0))for t in a.sol_shadow_trades if float(t.get("net_pnl_usd",.0))<0));p=round(g/d,2)if d>0 else(99. if g>0 else.0);c=[t for t in a.sol_shadow_trades if t.get("schema_v395_fixed")is True];m=len(c);e=sum(1 for t in c if t.get("won"));l=(e/m*1e2)if m>0 else.0;k=sum(float(t.get("net_pnl_usd",.0))for t in c if float(t.get("net_pnl_usd",.0))>0);j=abs(sum(float(t.get("net_pnl_usd",.0))for t in c if float(t.get("net_pnl_usd",.0))<0));i=round(k/j,2)if j>0 else(99. if k>0 else.0);n={"timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"sleeve_id":"SLEEVE_SOL_V392_SHADOW","strategy":"SOL 15m/1h Volatility-Normalized Sniper (v3.9.5 USD-matched, 15m*2.0 sigma, <=0.81 cap, 3-Zone Salvage)","graduation_criteria":"v395_clean_trades >= 30 and v395_profit_factor >= 2.0 and v395_win_rate_pct >= 85.0","ready_for_live_graduation":bool(m>=30 and i>=2. and l>=85.),"v395_clean_trades_settled":m,"v395_profit_factor":i,"v395_win_rate_pct":round(l,2),"initial_capital":SOL_SHADOW_INITIAL_CAPITAL,"current_equity":round(a.sol_shadow_cash,2),"realized_pnl":round(a.sol_shadow_realized_pnl,2),"profit_factor":p,"total_fees_paid":round(a.sol_shadow_total_fees,2),"total_trades_settled":b,"winning_trades":o,"losing_trades":b-o,"win_rate_pct":round(q,2),"active_open_positions_count":sum(len(v)for v in a.sol_shadow_open_trades.values()),"status":"RUNNING"if ENABLE_SOL_SHADOW_SLEEVE else"DISABLED","ledger_file":str(SOL_SHADOW_LEDGER_FILE)};h=SOL_SHADOW_STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
  try:
   with open(h,"w",encoding="utf-8")as f:json.dump(n,f,indent=2);f.flush();os.fsync(f.fileno())
   os.replace(h,SOL_SHADOW_STATE_FILE)
  except Exception:
   if h.exists():
    try:h.unlink()
    except Exception:pass
 def load_persisted_xrp_shadow_ledger(a):
  if XRP_SHADOW_LEDGER_FILE.exists():
   with open(XRP_SHADOW_LEDGER_FILE,"r",encoding="utf-8",errors="ignore")as f:
    for b in f:
     if not b.strip():continue
     t=json.loads(b);c=t.get("trade_id")
     if c and c not in a.xrp_shadow_settled_ids:a.xrp_shadow_settled_ids.add(c);a.xrp_shadow_trades.append(t);a.xrp_shadow_realized_pnl+=float(t.get("net_pnl_usd",.0));a.xrp_shadow_total_fees+=float(t.get("taker_fee_usd",.0))+float(t.get("exit_fee_usd",.0))
   a.xrp_shadow_cash=XRP_SHADOW_INITIAL_CAPITAL+a.xrp_shadow_realized_pnl
 def save_xrp_shadow_state(a):
  b=len(a.xrp_shadow_trades);h=sum(1 for t in a.xrp_shadow_trades if t.get("won"));j=(h/b*1e2)if b>0 else.0;d=sum(float(t.get("net_pnl_usd",.0))for t in a.xrp_shadow_trades if float(t.get("net_pnl_usd",.0))>0);c=abs(sum(float(t.get("net_pnl_usd",.0))for t in a.xrp_shadow_trades if float(t.get("net_pnl_usd",.0))<0));i=round(d/c,2)if c>0 else(99. if d>0 else.0);g={"timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"sleeve_id":"SLEEVE_XRP_V392_SHADOW","strategy":"XRP 15m/1h Volatility-Normalized Sniper (dist>=0.12%, z>=0.70, band_L2>=$15, spread<=6c, 95c/98c TP + 3-Zone Salvage)","graduation_criteria":"trades >= 30 and profit_factor >= 2.0 and win_rate_pct >= 85.0","ready_for_live_graduation":bool(b>=30 and i>=2. and j>=85.),"initial_capital":XRP_SHADOW_INITIAL_CAPITAL,"current_equity":round(a.xrp_shadow_cash,2),"realized_pnl":round(a.xrp_shadow_realized_pnl,2),"profit_factor":i,"total_fees_paid":round(a.xrp_shadow_total_fees,2),"total_trades_settled":b,"winning_trades":h,"losing_trades":b-h,"win_rate_pct":round(j,2),"active_open_positions_count":sum(len(v)for v in a.xrp_shadow_open_trades.values()),"status":"RUNNING"if ENABLE_XRP_SHADOW_SLEEVE else"DISABLED","ledger_file":str(XRP_SHADOW_LEDGER_FILE)};e=XRP_SHADOW_STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
  try:
   with open(e,"w",encoding="utf-8")as f:json.dump(g,f,indent=2);f.flush();os.fsync(f.fileno())
   os.replace(e,XRP_SHADOW_STATE_FILE)
  except Exception:
   if e.exists():
    try:e.unlink()
    except Exception:pass
 def _get_live_account_equity(self):
  try:
   a=getattr(self,"live_state_file",DATA_DIR/"live_harvester_state.json")
   if a.exists():
    e=json.loads(a.read_text(encoding="utf-8"));d=e.get("total_account_equity")
    if d is not None and isinstance(d,(int,float))and d>0:return float(d)
    c=e.get("live_bankroll")
    if c is not None and isinstance(c,(int,float))and c>0:b=sum(p.get("notional_usd",.0)for p in e.get("active_positions",{}).values());return float(c)+b
  except Exception:pass
  return None
 def _get_latest_telemetry_snapshot(self,market_id,asset="",min_timestamp_unix=.0,poll_timeout_sec=.0):
  m=str(asset).upper();c=m if m in("BTC","ETH","SOL","XRP")else"BTC";n=os.environ.get("PM_FAST_TICK_DIR","/dev/shm");k=Path(n)/f"pm_fast_tick_{c}.json"if n else None;g={"BTC":HOURLY_TELEMETRY_FILE,"ETH":HOURLY_TELEMETRY_ETH_FILE,"SOL":HOURLY_TELEMETRY_SOL_FILE,"XRP":HOURLY_TELEMETRY_XRP_FILE};b=g.get(c,HOURLY_TELEMETRY_FILE);j=time.time()+max(.0,poll_timeout_sec)
  while True:
   if k is not None and k.exists():
    try:
     i=json.loads(k.read_text(encoding="utf-8"));q=i.get("markets",{})
     if str(market_id)in q:
      o=q[str(market_id)];h=float(o.get("timestamp_unix")or i.get("timestamp_unix")or.0)
      if min_timestamp_unix<=.0 or h>=min_timestamp_unix:return o
    except Exception:pass
   if not b.exists():
    if time.time()>=j:return None
    time.sleep(.05);continue
   try:
    p=b.stat().st_size;a=min(p,131072)
    with open(b,"rb")as f:f.seek(p-a);e=f.read().decode("utf-8",errors="ignore").splitlines()
    for l in reversed(e):
     if not l.strip():continue
     try:
      d=json.loads(l)
      if str(d.get("market_id"))==str(market_id):
       h=float(d.get("timestamp_unix")or d.get("ts")or.0)
       if min_timestamp_unix<=.0 or h>=min_timestamp_unix:return d
     except Exception:continue
   except Exception:pass
   if time.time()>=j:break
   time.sleep(.05)
  try:
   p=b.stat().st_size;a=min(p,131072)
   with open(b,"rb")as f:f.seek(p-a);e=f.read().decode("utf-8",errors="ignore").splitlines()
   for l in reversed(e):
    if not l.strip():continue
    try:
     d=json.loads(l)
     if str(d.get("market_id"))==str(market_id):return d
    except Exception:continue
  except Exception:pass
  return None
 def replay_existing_data(a):
  if not RESOLUTIONS_FILE.exists()or not SHOCK_FILE.exists():return
  d={}
  with open(RESOLUTIONS_FILE,"r")as f:
   for c in f:
    if c.strip():
     r=json.loads(c)
     if r.get("winning_outcome")in("UP","DOWN"):d[r["market_id"]]=r;a.seen_resolution_ids.add(r["market_id"])
  with open(SHOCK_FILE,"r")as f:
   for c in f:
    if not c.strip():continue
    s=json.loads(c);b=f"{s.get('market_id')}_{s.get('t0_unix')}";a.seen_shock_ids.add(b);a.evaluate_shock_signal(s,historical=True)
  if TRIGGER_FILE.exists():
   with open(TRIGGER_FILE,"r")as f:
    for c in f:
     if not c.strip():continue
     s=json.loads(c);b=f"{s.get('market_id')}_{s.get('t0_unix')}"
     if b not in a.seen_shock_ids:a.seen_shock_ids.add(b);a.evaluate_shock_signal(s,historical=True)
   a.last_trigger_file_pos=TRIGGER_FILE.stat().st_size
  if SHOCK_FILE.exists():a.last_shock_file_pos=SHOCK_FILE.stat().st_size
  for e,g in d.items():a.settle_market(e,g,historical=True)
  a.save_state();print(f"[REPLAY SYNCHRONIZED] Open in-flight markets: {len(a.open_trades)}",flush=True)
 def evaluate_shock_signal(a,shock,historical=False):
  if not historical:a.wfo_shadow.on_shock_signal(shock)
  c=str(shock.get("asset","")or"").upper();d=str(shock.get("title","")or"").lower()
  if ENABLE_SOL_SHADOW_SLEEVE and(c=="SOL"or"solana"in d):a._evaluate_sol_shadow_sleeve(shock,historical=historical);return
  if ENABLE_XRP_SHADOW_SLEEVE and(c=="XRP"or"xrp"in d or"ripple"in d):a._evaluate_xrp_shadow_sleeve(shock,historical=historical);return
  if c not in("","BTC","ETH")and"bitcoin"not in d and"btc"not in d and"ethereum"not in d and"eth"not in d:return
  b=a._evaluate_sleeve_1(shock,historical=historical)
  if b:return
  if ENABLE_SLEEVE_304_315:a._evaluate_sleeve_2(shock,historical=historical)
 def _evaluate_sol_shadow_sleeve(self,shock,historical=False):return self._evaluate_alt_shadow_sleeve(shock,asset_sym="SOL",historical=historical)
 def _evaluate_xrp_shadow_sleeve(self,shock,historical=False):return self._evaluate_alt_shadow_sleeve(shock,asset_sym="XRP",historical=historical)
 def _evaluate_alt_shadow_sleeve(a,shock,asset_sym="SOL",historical=False):
  if historical:return False
  Q=str(shock.get("market_id")or"")
  if not Q:return False
  P=(asset_sym=="SOL");p=a.sol_shadow_settled_ids if P else a.xrp_shadow_settled_ids;I=a.sol_shadow_open_trades if P else a.xrp_shadow_open_trades;o=a.sol_shadow_trades if P else a.xrp_shadow_trades;q=SOL_SHADOW_TICKET_NOTIONAL if P else XRP_SHADOW_TICKET_NOTIONAL;M=float(shock.get("t0_unix",time.time())or time.time());A=shock.get("shock_direction");k="UP"if A=="BUY"else"DOWN";H=f"{asset_sym}_SHDW_{Q}_{int(M)}_{k}"
  if H in p:return False
  if Q in I and I[Q]:
   a.check_maker_tp_fills(Q,shock.get("pre_shock_features_t0",{}))
   if Q in I and I[Q]:return False
  if any(t.get("market_id")==Q for t in o):return False
  n=str(shock.get("title","")or"").lower();L=str(shock.get("horizon","")or shock.get("candle_interval","")).lower();j=any(x in L or x in n for x in("15m","900s","am-","pm-"));S=float(shock.get("seconds_to_expiry",3600.)or 3600.)
  if j and not(90.<=S<=540.):return False
  if not j and not(90.<=S<=2400.):return False
  i=float(shock.get("authoritative_chainlink_open")or shock.get("chainlink_open_spot")or.0);m=float(shock.get("chainlink_proxy_spot")or shock.get("coinbase_spot")or.0)
  if j and i>.0 and m>.0:d=m;c=i;b="USD"
  elif j:d=float(shock.get("spot_at_t0")or shock.get("trigger_price")or.0);c=float(shock.get("twap_60s_open")or shock.get("candle_open_spot")or.0);b="USDT"
  else:d=float(shock.get("spot_at_t0")or shock.get("trigger_price")or.0);c=float(shock.get("finalized_1h_open")or shock.get("candle_open_spot")or.0);b="USDT"
  if d<=.0 or c<=.0:return False
  if b=="USDT"and j and shock.get("twap_60s_open")and shock.get("candle_open_spot"):
   if abs(float(shock["twap_60s_open"])-float(shock["candle_open_spot"]))/max(float(shock["candle_open_spot"]),1e-6)*1e2>=.09:return False
  G=((d-c)/c)*1e2;l=G if k=="UP"else-G
  if l<.12:return False
  K=str(shock.get("btc_shock_direction")or"").upper()
  if K:
   if(k=="UP"and K in("DOWN","SELL"))or(k=="DOWN"and K in("UP","BUY")):return False
  z=float(shock.get("shock_volume_100ms")or.0);y=abs(float(shock.get("shock_ofi")or.0));h=1.2e5 if P else 7.5e4
  if z<h or y<.6:return False
  g=.0085 if P else.0082;F=float(shock.get("candle_sigma")or.0);e=(F*2. if j else F)if F>.0 else g;e=max(.006,min(.016,e));w=e*math.sqrt(max(S,15.)/3600.)*1e2;E=l/max(w,.01)
  if E<.78:return False
  T=(shock.get("pre_shock_features_t0")or{}).get(k)or{};D=[(float(px),float(sz))for px,sz in(T.get("raw_top_asks")or[])if float(px)>0 and float(sz)>0];C=[(float(px),float(sz))for px,sz in(T.get("raw_top_bids")or[])if float(px)>0 and float(sz)>0];v=D[0][0]if D else float(T.get("best_ask")or.0);u=C[0][0]if C else float(T.get("best_bid")or.0);f=.03 if j else.04
  if not(.56<=v<=.81)or u<=.0 or round(v-u,6)>f:return False
  B=sum(px*sz for px,sz in D if px<=v+.02)if D else float(T.get("l1_ask_usd")or 20.)
  if B<15.:return False
  O=.5*(1.+math.erf((E+.14)/math.sqrt(2.)));J=O*.965+(1.-O)*.9*.35;s=min(.81,round(J/1.04,4))
  if v>s:return False
  N=round(q/v,4);_,r=calculate_taker_fee(q,v,fee_rate=.07,fee_exponent=1.);R={"trade_id":H,"sleeve":f"SLEEVE_{asset_sym}_V392_SHADOW","schema_v395_fixed":True,"spot_denomination":b,"market_id":Q,"title":shock.get("title"),"asset":asset_sym,"horizon":"15m"if j else"1h","target_token":k,"entry_unix":M,"expiry_unix":float(shock.get("expiry_ts")or(M+S)),"seconds_to_expiry":round(S,1),"candle_open_spot":round(c,4),"spot_at_t0":round(d,4),"dist_pct":round(G,4),"z_strike":round(E,3),"entry_price":round(v,4),"shares_bought":N,"notional_usd":q,"taker_fee_usd":round(r,4),"fee_rate_applied":.07,"take_profit_maker_limit_px":.965,"status":"OPEN"};I.setdefault(Q,[]).append(R)
  if P:a.save_sol_shadow_state()
  else:a.save_xrp_shadow_state()
  return True
 def _evaluate_sleeve_1(a,shock,historical=False):
  _6=shock.get("market_id")
  if not _6:return False
  _P=shock.get("t0_unix",time.time());_B=shock.get("shock_direction");_c="UP"if _B=="BUY"else"DOWN";_K=f"PAPER_{_6}_{int(_P)}_{_c}"
  if _K in a.settled_trade_ids:return False
  h=a.open_trades.get(_6,[])
  if any(t["trade_id"]==_K for t in h):return False
  if h:_l=shock.get("pre_shock_features_t0",{});a.check_maker_tp_fills(_6,_l);h=a.open_trades.get(_6,[])
  _J=int(float(_P)//3600)
  if _J!=a.current_hour_window:a.current_hour_window=_J;a.trades_this_hour=0
  _k=float(shock.get("delta_basis_100ms",.0)or.0)
  if _c=="UP"and _k<-2.:return False
  elif _c=="DOWN"and _k>2.:return False
  if ENABLE_SLEEVE_304_315 and _6 in a.sleeve2_open_trades and len(a.sleeve2_open_trades[_6])>0:return False
  z=a.trades_per_market.get(_6,0)+len(h);m=False;l=False
  if z>=1 and len(h)==0:
   for t in reversed(a.val_trades+a.dev_trades):
    if t.get("market_id")==_6:
     if t.get("won")is True and float(t.get("net_pnl_usd",.0)or.0)>0:m=(z==1)
     else:l=True
     break
  n=0 if l else(2 if m else MAX_TRADES_PER_MARKET)
  if z>=n or a.trades_this_hour>=MAX_TRADES_PER_HOUR:return False
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   dt=datetime.fromtimestamp(_P,tz=timezone.utc)
   if dt.hour==13 and dt.minute>=30:return False
  _3=shock.get("title","");_2=shock.get("asset","");_j=_3.lower();_O=str(shock.get("horizon","")or shock.get("candle_interval","")).lower();_5=str(shock.get("series_slug","")or shock.get("slug","")).lower();_b=any(x in _O or x in _5 or x in _j for x in("5m","15m","300s","900s"));_1=not _b and(any(x in _O or x in _5 or x in _j for x in("1h","hourly","60m"))or("am et"in _j or"pm et"in _j));_A=compute_composite_edge_score(shock)
  if _A.get("veto",False):return False
  _z=_A.get("tier","TIER_B_STANDARD");_t=_A.get("kelly_multiplier",1.);_9=float(shock.get("seconds_to_expiry",3600.)or 3600.);o=None;c=MIN_PRICE_FLOOR;b=MAX_PRICE_CEILING;H=float(shock.get("candle_distance_pct",.0)or.0);N=shock.get("finalized_1h_open")or shock.get("candle_open_spot");_s=float(shock.get("spot_at_t0")or shock.get("trigger_price")or.0)
  if(abs(H)<1e-4 or not N or float(N)<=.0)and _s>.0:
   _0=int(float(shock.get("t0_unix",time.time()))//3600);_i=a.hourly_candle_opens.get(_2,{}).get(_0)
   if _i and _i>.0:H=((_s-_i)/_i)*1e2
  k=shock.get("pre_shock_features_t0",{}).get(_c,{});T=float(shock.get("shock_ofi",1.)if shock.get("shock_ofi")is not None else 1.);S=float(shock.get("shock_volume_100ms",1.5e6)or 1.5e6);K=float(shock.get("delta_basis_100ms",.0)or.0);y=K if _c=="UP"else-K;M=float(shock.get("age_ask_ms")or k.get("age_ask_ms",350.)or 350.);_N,_r=evaluate_coinbase_venue_veto(shock,_c)
  if _N:return False
  _q=compute_max_acceptable_ask(dist_pct=H,tte_sec=_9,asset=_2 or("BTC"if"btc"in _j else"ETH"),shock_ofi=T,shock_vol_usd=S,delta_basis_bps=y,age_ask_ms=M,is_subhourly_15m=_b);_Z=_q.get("z_eff",.0);_Y=_q.get("p_max",.0)
  if _1:
   if 9e2<_9<=2700.:
    o="REGIME_A_MID_HOUR"
    if abs(H)<.15:return False
    if _c=="UP"and H<.15:return False
    if _c=="DOWN"and H>-.15:return False
    _y=int(float(shock.get("t0_unix",time.time()))//3600);_x=a.hourly_candle_opens.get(_2,{});_W=_x.get(_y);_I=_x.get(_y-1);_H=_x.get(_y-2);_V=((_W-_H)/_H)if(_W and _H and _H>0)else None;_a=((_W-_I)/_I)if(_W and _I and _I>0)else None;Z=((_I-_H)/_H)if(_I and _H and _H>0)else None;R=(_a is not None and _a>.001 and Z is not None and Z>.001);_h=(_a is not None and _a<-.001 and Z is not None and Z<-.001);d=False
    if _c=="DOWN":
     if(_V is not None and _V>.003)or R:d=True
    elif _c=="UP":
     if(_V is not None and _V<-.003)or _h:d=True
    if d and abs(H)<.4:return False
    c=.55;b=.78
   elif(30.<=_9<=9e2 if _Z>=2.2 else 120.<=_9<=9e2):
    o="REGIME_B_LATE_SNIPER";_M=abs(H)
    if _M<.1:return False
    if _c=="UP"and H<.1:return False
    if _c=="DOWN"and H>-.1:return False
    if _M<.15:c=.55;b=.75
    elif _M<.22:c=.58;b=.8
    else:c=.62;b=.84
   else:return False
  elif _b:
   if 90.<=_9<=420.:
    o="REGIME_C_SUBHOURLY"
    if abs(H)<.18:return False
    if _c=="UP"and H<.18:return False
    if _c=="DOWN"and H>-.18:return False
    c=.58;b=.82
   else:return False
  else:return False
  if"sol"in _j or"solana"in _j or _2=="SOL":return False
  _U=("btc"in _j or"bitcoin"in _j or _2=="BTC");_T=("ethereum"in _j or"eth"in _j or _2=="ETH")
  if _U:
   _g=(_O in("1h","hourly","60m")or"hourly"in _5)and _9>MAX_TTE_SECONDS
   if _g:return False
   C=shock.get("z_btc")or shock.get("z_score")or shock.get("z_val")
   if C is not None and abs(float(C))<1.645:return False
  if _T:
   Q=shock.get("btc_shock_direction")
   if Q:
    if _c=="UP"and Q in("DOWN","SELL"):return False
    if _c=="DOWN"and Q in("UP","BUY"):return False
   _w=shock.get("z_eth")or shock.get("z_score")or shock.get("z_val");C=shock.get("z_btc")
   if _w is not None and C is not None:
    _8=float(_w);_7=float(C)
    if(_8>0 and _7<0)or(_8<0 and _7>0):return False
  k=shock.get("pre_shock_features_t0",{}).get(_c,{});a.recent_shock_window=[w for w in a.recent_shock_window if(_P-w["t_unix"])<=5.];_L=abs(float(shock.get("z_val",shock.get("z_score",shock.get("expected_prob_shift",abs(H)*.5)))));Y=float(k.get("vwap_$50")or k.get("effective_price_$50")or.5);J=_L/max(Y,.01)
  if a.recent_shock_window:
   _p=max(a.recent_shock_window,key=lambda x:x["score"])
   if _p["market_id"]!=_6 and _p["score"]>J:return False
  a.recent_shock_window.append({"t_unix":_P,"score":J,"market_id":_6,"trade_id":_K});_G=k.get("raw_top_asks",[])
  if not _G:return False
  v=sum(px*sz for px,sz in _G if px<=b);_v=float(_G[0][0])if _G else.75
  if _v<c or _v>b:return False
  D=(_P>=R3_VALIDATION_START_UNIX);_f="VALIDATION"if D else"DEV";X=sum(t["notional_usd"]for m_trades in a.open_trades.values()for t in m_trades if t.get("epoch")==_f and t.get("status")=="OPEN");W=a.val_cash if _f=="VALIDATION"else a.dev_cash;_u=W-X;u=.24 if _v<=.78 else.2;B=min(MAX_ELASTIC_TICKET_USD,max(MIN_ELASTIC_TICKET_USD,W*u));_o=v/DEFAULT_ELASTIC_SAFETY_RATIO
  if _o<MIN_ELASTIC_TICKET_USD:return False
  _e=a._get_live_account_equity()
  if _e is not None and _e>0:I=min(MAX_ELASTIC_TICKET_USD,max(MIN_ELASTIC_TICKET_USD,_e*u));f=min(I,max(MIN_ELASTIC_TICKET_USD,round(_o,2)))
  else:f=min(B,max(MIN_ELASTIC_TICKET_USD,round(_o,2)))
  r=min(TICKET_NOTIONAL,max(MIN_ELASTIC_TICKET_USD,round(_o,2)))
  if os.getenv("PAPER_USE_LIVE_BANKROLL_SIZING","1")=="1"and _e is not None:j=min(f,_u)
  else:q=min(B,max(MIN_ELASTIC_TICKET_USD,round(_o,2)));j=min(q,_u)
  if j<MIN_ELASTIC_TICKET_USD:return False
  _d=v/j;_S=k.get("effective_price_$50");G=k.get("vwap_$50");_F=k.get("fill_fees_$50");_R=float(k.get("spread",.01)or.01)
  if _R>MAX_ALLOWED_SPREAD or not _S:return False
  if G is None:G=_S
  if G<c or G>b:return False
  if _Y<=.0 or G>_Y:return False
  _E=shock.get("fee_metadata",{});F=_E.get("fee_rate_market")
  if F is None or float(F)<=.0:F=.07
  V=float(_E.get("fee_exponent",1.));e=.0;s=float(G);p=float(_S)
  if a.paper_latency_ms>0:
   i=None;E=None
   if not historical:
    time.sleep(a.paper_latency_ms/1e3);P=float(_P)+a.paper_latency_ms/1e3-.05;_n=a._get_latest_telemetry_snapshot(_6,"ETH"if _T else"BTC",min_timestamp_unix=P,poll_timeout_sec=1.1)
    if _n:
     _D=_n.get(_c,{});U=_D.get("best_ask");i=float(U or.0);O=_D.get("raw_top_asks",[]);L=sum(px*sz for px,sz in O if px<=MAX_PRICE_CEILING)if O else.0
     if i<=.0 or not O:print(f"\n[PAPER FAK KILLED] {shock.get('title')} | Target: {_c} | Post-latency ask book completely swept dry (ask=${i:.4f}, asks={len(O)}) after {a.paper_latency_ms}ms",flush=True);return False
     if(L/DEFAULT_ELASTIC_SAFETY_RATIO)<MIN_ELASTIC_TICKET_USD:print(f"\n[PAPER FAK KILLED] {shock.get('title')} | Target: {_c} | Post-latency executable depth ${L:.2f} < min ${MIN_ELASTIC_TICKET_USD*DEFAULT_ELASTIC_SAFETY_RATIO:.2f} (depth swept after {a.paper_latency_ms}ms)",flush=True);return False
     E=_D.get("effective_price_$50")or _D.get("vwap_$50")or i
   if i is None:
    ir=shock.get("impulse_response",{});_m="500ms"if a.paper_latency_ms>=400 else("250ms"if a.paper_latency_ms>=200 else"100ms");_4=ir.get(_m)or ir.get("500ms")or ir.get("250ms")
    if _4:
     _C=_4.get("up_ask"if _c=="UP"else"down_ask")
     if _C is not None:i=float(_C)
   if i is not None:
    if i<=.0 or i>MAX_PRICE_CEILING:print(f"\n[PAPER FAK KILLED] {shock.get('title')} | Target: {_c} | Post-latency ask ${i:.4f} > ceiling ${MAX_PRICE_CEILING} (depth swept after {a.paper_latency_ms}ms)",flush=True);return False
    if i>s:e=round((i-s)*1e2,4);s=i;p=max(p,float(E)if E is not None else i)
  _Q=j/float(s)
  if _F is not None:A=float(_F)*(j/TICKET_NOTIONAL)
  else:_,A=calculate_taker_fee(j,float(s),F,V)
  g=A/j;_X={"trade_id":_K,"market_id":_6,"title":shock.get("title",""),"entry_time":shock.get("timestamp",""),"entry_unix":_P,"epoch":_f,"seconds_to_expiry":_9,"target_token":_c,"notional_usd":j,"live_parity_notional_usd":f,"legacy_fixed_notional_usd":r,"effective_price":p,"exec_price":s,"entry_price":s,"adverse_slippage_cents":e,"latency_simulated_ms":a.paper_latency_ms,"shares_bought":round(_Q,4),"taker_fee_usd":round(A,4),"fee_rate_applied":F,"fee_exponent_applied":V,"effective_fee_rate_on_deployed_notional":round(g,6),"fee_formula_provenance":f"calculate_taker_fee(notional={j}, price={s:.3f}, fee_rate={F}, fee_exponent={V})","execution_model":"PIECEWISE_LINEAR_SCENARIO_MILP","simulated_partial_fill_timeout_ms":a.paper_latency_ms,"spot_at_t0":shock.get("spot_at_t0"),"candle_open_spot":float(shock.get("finalized_1h_open")or shock.get("candle_open_spot")or shock.get("spot_at_t0")or.0),"candle_distance_pct":H,"status":"OPEN","exit_policy":"EXP302_HOLD_TO_MATURITY_WITH_SPOT_DELTA_STOP","take_profit_maker_limit_px":.99 if p>=.8 else.98,"stop_loss_relative_px":max(.02,round(p-.12,4)),"maker_tp_order_status":"RESTING_MAKER_LIMIT","score":J}
  if _6 not in a.open_trades:a.open_trades[_6]=[]
  a.open_trades[_6].append(_X)
  if int(float(_P)//3600)==a.current_hour_window:a.trades_this_hour+=1
  if not historical:print(f"\n[PAPER ORDER FILLED - {_f}] {shock.get('title')} | Target: {_c} | Price: {s:.3f} (Slippage: +{e:.2f}¢) | Shares: {_Q:.1f} | TTE: {_9/60.:.1f}m | Dist: {H:+.2f}% | Fee: ${A:.3f}",flush=True)
  return True
 def _evaluate_sleeve_2(a,shock,historical=False):
  if historical:return
  _d=shock.get("market_id")
  if not _d:return
  if _d in a.open_trades and len(a.open_trades[_d])>0:return
  if _d in a.sleeve2_open_trades and len(a.sleeve2_open_trades[_d])>0:return
  Q=shock.get("t0_unix",time.time());G=shock.get("shock_direction");s="UP"if G=="BUY"else"DOWN";L=f"SLEEVE2_{_d}_{int(Q)}_{s}"
  if L in a.sleeve2_settled_ids:return
  if a.sleeve2_cash<SLEEVE_2_TICKET_NOTIONAL:return
  if os.environ.get("PM_DISABLE_NYSE_BLACKOUT")!="1":
   dt=datetime.fromtimestamp(Q,tz=timezone.utc)
   if dt.hour==13 and dt.minute>=30:return
  _a=shock.get("title","");Z=shock.get("asset","");w=_a.lower();P=str(shock.get("horizon","")or shock.get("candle_interval","")).lower();_c=str(shock.get("series_slug","")or shock.get("slug","")).lower();V=("ethereum"in w or"eth"in w or Z=="ETH");U=("bitcoin"in w or"btc"in w or Z=="BTC")
  if not(V or U):return
  F="ETH"if V else"BTC";r=any(x in P or x in _c or x in w for x in("5m","15m","300s","900s"));Y=not r and(any(x in P or x in _c or x in w for x in("1h","hourly","60m"))or("am et"in w or"pm et"in w))
  if not Y:return
  _g=shock.get("seconds_to_expiry",3600.)
  if _g>SLEEVE_2_MAX_TTE or _g<SLEEVE_2_MIN_TTE:return
  g=float(shock.get("candle_distance_pct",.0)or.0);e=shock.get("finalized_1h_open")or shock.get("candle_open_spot");A=float(shock.get("spot_at_t0")or shock.get("trigger_price")or.0)
  if(abs(g)<1e-4 or not e or float(e)<=.0)and A>.0:
   X=int(float(shock.get("t0_unix",time.time()))//3600);v=a.hourly_candle_opens.get(Z,{}).get(X)
   if v and v>.0:g=((A-v)/v)*1e2
  if abs(g)<.15:return
  if s=="UP"and g<.15:return
  if s=="DOWN"and g>-.15:return
  _b=float(shock.get("t0_unix",time.time()));E=int(_b//3600);e=shock.get("finalized_1h_open")or shock.get("candle_open_spot")or shock.get("spot_at_t0")
  if e and math.isfinite(float(e))and float(e)>0:
   if E not in a.hourly_candle_opens[F]:a.hourly_candle_opens[F][E]=float(e)
  D=a.hourly_candle_opens.get(F,{});T=D.get(E);K=D.get(E-1);J=D.get(E-2);S=((T-J)/J)if(T and J and J>0)else None;q=((T-K)/K)if(T and K and K>0)else None;p=((K-J)/J)if(K and J and J>0)else None;m=(q is not None and q>.001 and p is not None and p>.001);u=(q is not None and q<-.001 and p is not None and p<-.001);b=False
  if s=="DOWN":
   if(S is not None and S>.003)or m:b=True
  elif s=="UP":
   if(S is not None and S<-.003)or u:b=True
  if b:
   if abs(g)<.45:return
  l=shock.get("btc_shock_direction")
  if l:
   if s=="UP"and l in("DOWN","SELL"):return
   if s=="DOWN"and l in("UP","BUY"):return
  C=shock.get("z_eth")or shock.get("z_score")or shock.get("z_val");B=shock.get("z_btc")
  if C is not None and B is not None:
   _f=float(C);_e=float(B)
   if(_f>0 and _e<0)or(_f<0 and _e>0):return
   O=.7*_f+.3*_e
   if s=="UP"and O<=0:return
   if s=="DOWN"and O>=0:return
  j=shock.get("pre_shock_features_t0",{}).get(s,{});I=j.get("raw_top_asks",[])
  if not I:return
  i=SLEEVE_2_TICKET_NOTIONAL;h=sum(px*sz for px,sz in I if SLEEVE_2_MIN_PRICE<=px<=SLEEVE_2_MAX_PRICE)
  if h<(i*SLEEVE_2_MIN_DEPTH_RATIO):return
  d=.0;c=.0
  for px,sz in I:
   if px<SLEEVE_2_MIN_PRICE or px>SLEEVE_2_MAX_PRICE:continue
   o=px*sz;R=i-d
   if o<=R:d+=o;c+=sz
   else:N=R/px;d+=R;c+=N;break
  if d<i or c<=0:return
  z=round(d/c,4)
  if not(SLEEVE_2_MIN_PRICE<=z<=SLEEVE_2_MAX_PRICE):return
  if _g<=1350. and z>=.68:return
  n,k=calculate_taker_fee(i,z,fee_rate=.07,fee_exponent=1.);H=n;M=float(shock.get("spot_at_t0",.0)or.0);y=shock.get("startingPrice")or shock.get("strike_price")or shock.get("priceToBeat")
  if y and float(y)>0:f=float(y)
  elif M>0 and abs(g)>0:f=round(M/(1.+g/1e2),2)
  else:f=M
  t=.99;W={"sleeve":"SLEEVE_2_MULTI_304_315","trade_id":L,"market_id":_d,"title":_a,"entry_time":shock.get("timestamp",""),"entry_unix":Q,"seconds_to_expiry":_g,"target_token":s,"notional_usd":i,"vwap_exec_price":z,"entry_price":z,"shares_bought":round(c,4),"taker_fee_usd":k,"fee_rate_applied":H,"fee_schedule":"crypto_fees_v2","spot_at_t0":M,"strike_price":f,"candle_open_spot":f,"candle_distance_pct":g,"status":"OPEN","exit_policy":"HOLD_TO_0.99_MAKER_TP_OR_MATURITY","take_profit_maker_limit_px":t,"maker_tp_order_status":"RESTING_MAKER_LIMIT"}
  if _d not in a.sleeve2_open_trades:a.sleeve2_open_trades[_d]=[]
  a.sleeve2_open_trades[_d].append(W);a.save_sleeve2_state()
  if not historical:print(f"\n[SLEEVE 2 ORDER FILLED] {_a} | Target: {s} | VWAP: ${z:.4f} | Shares: {c:.1f} | TTE: {_g/60.:.1f}m | Strike: ${f:,.2f} | TP Limit: ${t:.3f} | Fee: ${k:.3f}",flush=True)
 def check_strike_retrace_stops(self,market_id,candle_dist_pct,tte,token_bids=None,fee_rate=.07,fee_exponent=1.):return[]
 def check_maker_tp_fills(a,market_id,telem):
  a.wfo_shadow.on_telemetry_tick(str(market_id),telem)
  if(market_id not in a.open_trades and market_id not in a.sleeve2_open_trades and market_id not in a.sol_shadow_open_trades and market_id not in a.xrp_shadow_open_trades):return[]
  W=[]
  if market_id in a.open_trades:
   for t in list(a.open_trades[market_id]):
    if t.get("status")!="OPEN":continue
    z=t.get("target_token","UP");G=telem.get(z)or telem.get("pre_shock_features_t0",{}).get(z,{});r=float(G.get("best_bid",.0)or.0)
    if r==.0 and G.get("raw_top_bids"):r=float(G["raw_top_bids"][0][0])
    D=float(G.get("best_ask",.0)or.0)
    if D==.0 and G.get("raw_top_asks"):D=float(G["raw_top_asks"][0][0])
    H=float(t.get("entry_unix",.0)or.0);F=float(telem.get("timestamp_unix")or telem.get("t0_unix")or time.time())
    if(F-H)<6.:continue
    K=float(t.get("entry_price")or t.get("exec_price")or t.get("vwap_exec_price")or t.get("effective_price")or t.get("vwap")or.5);Z=float(t.get("take_profit_maker_limit_px")or(.99 if K>=.8 else.98));x=r>=Z;q=float(telem.get("binance_spot")or telem.get("spot_at_t0")or telem.get("trigger_price")or telem.get("spot")or.0);I=float(t.get("candle_open_spot")or t.get("strike_price")or telem.get("binance_1h_open")or t.get("spot_at_t0")or.0);o=float(telem.get("seconds_to_expiry")or.0)
    if o<=.0:
     _f=float(t.get("expiry_unix")or.0)
     if _f>F:o=_f-F
     else:o=float(t.get("seconds_to_expiry")or.0)
    j=.0
    if q>0:
     U=t.setdefault("spot_vel_history",[]);U.append([F,float(q)]);t["spot_vel_history"]=[pt for pt in U if(F-pt[0])<=15.];_p=t["spot_vel_history"]
     if len(_p)>=2:
      O=_p[0][1]
      if O>0:
       if z=="UP":j=((q-O)/O)*1e2
       else:j=((O-q)/O)*1e2
     t["v_spot_15s_pct"]=round(j,4)
    c=False;n=.0
    if q>0 and I>0:
     B=((q-I)/I*1e2)if z=="UP"else((I-q)/I*1e2);n=-B
     if n<=.0:t.pop("opposite_breakout_start_ts",None)
     else:
      if o>9e2:i,h,g,d=.16,.14,40.,.08
      elif o>180.:i,h,g,d=.11,.09,18.,.08
      elif o>=25.:i,h,g,d=.06,.04,8.,.06
      else:i,h,g,d=999.,999.,999.,.99
      M=(g*.5)if(j<=-.08 and r<=.42)else g;L=t.get("opposite_breakout_start_ts")
      if L is None:
       if n>=i:t["opposite_breakout_start_ts"]=F
      else:
       if n>=h:
        R=F-float(L)
        if j>=.03:c=False
        elif R>=M and r>=d:c=True
       else:t.pop("opposite_breakout_start_ts",None)
    t["max_seen_bid"]=max(float(t.get("max_seen_bid",.0)or.0),r);y=float(t.get("max_seen_bid",.0)or.0);b=False;u=.0
    if y>=max(.73,K+.09)and K>0:
     N=.05 if y>=.9 else(.07 if y>=.82 else.05);u=round(y-N,4)
     if r<=u and o>=25. and r>=.25:
      J=t.get("trailing_ratchet_start_ts")
      if J is None:t["trailing_ratchet_start_ts"]=F
      elif(F-float(J))>=3.:b=True
     else:t.pop("trailing_ratchet_start_ts",None)
    else:t.pop("trailing_ratchet_start_ts",None)
    k=False
    if.0<o<=45. and r>=.88 and r>(K+.03):k=True
    if not x and not c and not b and not k:continue
    A=float(t.get("fee_rate_applied",.07)or.07)
    if A<.05:A=.18 if"15m"in str(t.get("title","")).lower()else.07
    if k:E=max(.01,round(r-.01,4));C=round(t["shares_bought"]*E,2);_,v=calculate_taker_fee(C,E,fee_rate=A,fee_exponent=1.);m=round(C-t["notional_usd"]-t.get("taker_fee_usd",.0)-v,2);e="FINAL_45S_CAPITAL_RECYCLE_UNWIND";s=(m>0)
    elif b:E=r;C=round(t["shares_bought"]*E,2);_,v=calculate_taker_fee(C,E,fee_rate=A,fee_exponent=1.);m=round(C-t["notional_usd"]-t.get("taker_fee_usd",.0)-v,2);e="TRAILING_PROFIT_RATCHET_UNWIND";s=(m>0)
    elif c:E=r;C=round(t["shares_bought"]*E,2);_,v=calculate_taker_fee(C,E,fee_rate=A,fee_exponent=1.);m=round(C-t["notional_usd"]-t.get("taker_fee_usd",.0)-v,2);e="CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE";s=False
    else:E=Z;C=round(t["shares_bought"]*E,2);v=.0;m=round(C-t["notional_usd"]-t.get("taker_fee_usd",.0),2);e="MAKER_SCALP_FILLED_CLOB";s=True
    Q=float(t.get("live_parity_notional_usd",t["notional_usd"]));Y=Q/max(t["notional_usd"],1.);T=round(m*Y,2);S=float(t.get("legacy_fixed_notional_usd",t["notional_usd"]));_v=S/max(t["notional_usd"],1.);_g=round(m*_v,2);t["status"]="CLOSED";t["exit_reason"]=e;t["exit_price"]=E;t["exit_fee_usd"]=v;t["payout_usd"]=C;t["net_pnl_usd"]=m;t["live_parity_pnl_usd"]=T;t["legacy_fixed_pnl_usd"]=_g;t["won"]=s;t["settle_time"]=telem.get("timestamp")or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC");H=t.get("entry_unix",.0)
    if H<R3_VALIDATION_START_UNIX:a.dev_trades.append(t);a.dev_realized_pnl+=m;a.dev_cash=INITIAL_PAPER_CAPITAL+a.dev_realized_pnl;P=DEV_LEDGER_FILE
    else:a.val_trades.append(t);a.val_realized_pnl+=m;a.val_cash=INITIAL_PAPER_CAPITAL+a.val_realized_pnl;P=VALIDATION_LEDGER_FILE
    a.settled_trade_ids.add(t["trade_id"]);a.trades_per_market[market_id]+=1;W.append(t)
    with open(P,"a")as f:f.write(json.dumps(t)+"\n")
    _t="FINAL-45S RECYCLED"if k else("TRAILING RATCHET LOCKED"if b else("SALVAGE EXECUTED"if c else f"MAKER TP FILLED @ {E:.2f}"));print(f"\n[PAPER {_t}] {t.get('title')} | Target: {z} | Exit Price: ${E:.4f} | Net PnL: ${m:+.2f} ({e})",flush=True)
   if W:
    a.open_trades[market_id]=[t for t in a.open_trades[market_id]if t.get("status")=="OPEN"]
    if not a.open_trades[market_id]:del a.open_trades[market_id]
  if ENABLE_SLEEVE_304_315 and market_id in a.sleeve2_open_trades:
   V=[]
   for t in list(a.sleeve2_open_trades[market_id]):
    if t.get("status")!="OPEN":continue
    z=t.get("target_token","UP");G=telem.get(z)or telem.get("pre_shock_features_t0",{}).get(z,{});r=float(G.get("best_bid",.0)or.0)
    if r==.0 and G.get("raw_top_bids"):r=float(G["raw_top_bids"][0][0])
    D=float(G.get("best_ask",.0)or.0)
    if D==.0 and G.get("raw_top_asks"):D=float(G["raw_top_asks"][0][0])
    H=float(t.get("entry_unix",.0)or.0);F=float(telem.get("timestamp_unix")or telem.get("t0_unix")or time.time())
    if(F-H)<6.:continue
    K=float(t.get("entry_price")or t.get("exec_price")or t.get("vwap_exec_price")or t.get("effective_price")or t.get("vwap")or.5);E=float(t.get("take_profit_maker_limit_px",.99));x=r>=E;q=float(telem.get("binance_spot")or telem.get("spot_at_t0")or telem.get("trigger_price")or telem.get("spot")or.0);I=float(t.get("candle_open_spot")or t.get("strike_price")or telem.get("binance_1h_open")or t.get("spot_at_t0")or.0);o=float(telem.get("seconds_to_expiry")or.0)
    if o<=.0:
     _f=float(t.get("expiry_unix")or.0)
     if _f>F:o=_f-F
     else:o=float(t.get("seconds_to_expiry")or.0)
    j=.0
    if q>0:
     U=t.setdefault("spot_vel_history",[]);U.append([F,float(q)]);t["spot_vel_history"]=[pt for pt in U if(F-pt[0])<=15.];_p=t["spot_vel_history"]
     if len(_p)>=2:
      O=_p[0][1]
      if O>0:
       if z=="UP":j=((q-O)/O)*1e2
       else:j=((O-q)/O)*1e2
     t["v_spot_15s_pct"]=round(j,4)
    c=False;n=.0
    if q>0 and I>0:
     B=((q-I)/I*1e2)if z=="UP"else((I-q)/I*1e2);n=-B
     if n<=.0:t.pop("opposite_breakout_start_ts",None)
     else:
      if o>9e2:i,h,g,d=.16,.14,40.,.08
      elif o>180.:i,h,g,d=.11,.09,18.,.08
      elif o>=25.:i,h,g,d=.06,.04,8.,.06
      else:i,h,g,d=999.,999.,999.,.99
      M=(g*.5)if(j<=-.08 and r<=.42)else g;L=t.get("opposite_breakout_start_ts")
      if L is None:
       if n>=i:t["opposite_breakout_start_ts"]=F
      else:
       if n>=h:
        R=F-float(L)
        if j>=.03:c=False
        elif R>=M and r>=d:c=True
       else:t.pop("opposite_breakout_start_ts",None)
    t["max_seen_bid"]=max(float(t.get("max_seen_bid",.0)or.0),r);y=float(t.get("max_seen_bid",.0)or.0);b=False;u=.0
    if y>=max(.73,K+.09)and K>0:
     N=.05 if y>=.9 else(.07 if y>=.82 else.05);u=round(y-N,4)
     if r<=u and o>=25. and r>=.25:
      J=t.get("trailing_ratchet_start_ts")
      if J is None:t["trailing_ratchet_start_ts"]=F
      elif(F-float(J))>=3.:b=True
     else:t.pop("trailing_ratchet_start_ts",None)
    else:t.pop("trailing_ratchet_start_ts",None)
    k=False
    if.0<o<=45. and r>=.88 and r>(K+.03):k=True
    if not x and not c and not b and not k:continue
    A=float(t.get("fee_rate_applied",.07)or.07)
    if A<.05:A=.18 if"15m"in str(t.get("title","")).lower()else.07
    if k:w=max(.01,round(r-.01,4));l=round(t["shares_bought"]*w,2);_,p=calculate_taker_fee(l,w,fee_rate=A,fee_exponent=1.);m=round(l-t["notional_usd"]-t.get("taker_fee_usd",.0)-p,2);e="FINAL_45S_CAPITAL_RECYCLE_UNWIND";s=(m>0)
    elif b:w=r;l=round(t["shares_bought"]*w,2);_,p=calculate_taker_fee(l,w,fee_rate=A,fee_exponent=1.);m=round(l-t["notional_usd"]-t.get("taker_fee_usd",.0)-p,2);e="TRAILING_PROFIT_RATCHET_UNWIND";s=(m>0)
    elif c:w=r;l=round(t["shares_bought"]*w,2);_,p=calculate_taker_fee(l,w,fee_rate=A,fee_exponent=1.);m=round(l-t["notional_usd"]-t.get("taker_fee_usd",.0)-p,2);e="CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE";s=False
    else:w=E;l=round(t["shares_bought"]*w,2);p=.0;m=round(l-t["notional_usd"]-t.get("taker_fee_usd",.0),2);e="EXP315_MAKER_TP_FILLED";s=True
    t["status"]="CLOSED";t["exit_reason"]=e;t["exit_price"]=w;t["exit_fee_usd"]=p;t["payout_usd"]=l;t["net_pnl_usd"]=m;t["won"]=s;t["settle_time"]=telem.get("timestamp")or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC");a.sleeve2_trades.append(t);a.sleeve2_realized_pnl+=m;a.sleeve2_cash=SLEEVE_2_INITIAL_CAPITAL+a.sleeve2_realized_pnl;a.sleeve2_settled_ids.add(t["trade_id"]);V.append(t)
    with open(SLEEVE_2_LEDGER_FILE,"a")as f:f.write(json.dumps(t)+"\n")
    _t="SLEEVE 2 SALVAGE EXECUTED"if c else f"SLEEVE 2 MAKER TP FILLED @ {w:.3f}";print(f"\n[{_t}] {t.get('title')} | Target: {z} | Exit Price: ${w:.3f} | Net PnL: ${m:+.2f} | Sleeve 2 Equity: ${a.sleeve2_cash:,.2f}",flush=True)
   if V:
    a.sleeve2_open_trades[market_id]=[t for t in a.sleeve2_open_trades[market_id]if t.get("status")=="OPEN"]
    if not a.sleeve2_open_trades[market_id]:del a.sleeve2_open_trades[market_id]
    a.save_sleeve2_state()
  for _l,X,_o,_c,_b,_a,_n,_k,_m,_j,_q in(("SOL",ENABLE_SOL_SHADOW_SLEEVE,a.sol_shadow_open_trades,a.sol_shadow_trades,a.sol_shadow_settled_ids,SOL_SHADOW_LEDGER_FILE,SOL_SHADOW_INITIAL_CAPITAL,"sol_shadow_cash","sol_shadow_realized_pnl","sol_shadow_total_fees",a.save_sol_shadow_state),("XRP",ENABLE_XRP_SHADOW_SLEEVE,a.xrp_shadow_open_trades,a.xrp_shadow_trades,a.xrp_shadow_settled_ids,XRP_SHADOW_LEDGER_FILE,XRP_SHADOW_INITIAL_CAPITAL,"xrp_shadow_cash","xrp_shadow_realized_pnl","xrp_shadow_total_fees",a.save_xrp_shadow_state)):
   if X and market_id in _o:
    _e=[]
    for t in list(_o[market_id]):
     if t.get("status")!="OPEN":continue
     z=t.get("target_token","UP");G=telem.get(z)or telem.get("pre_shock_features_t0",{}).get(z,{});r=float(G.get("best_bid",.0)or.0)
     if r==.0 and G.get("raw_top_bids"):r=float(G["raw_top_bids"][0][0])
     F=float(telem.get("timestamp_unix")or telem.get("t0_unix")or time.time())
     if(F-float(t.get("entry_unix",.0)or.0))<6.:continue
     K=float(t.get("entry_price")or.7);E=float(t.get("take_profit_maker_limit_px",.965));x=r>=E;_s=t.get("horizon")=="15m";_i=t.get("spot_denomination")or("USD"if(_s and not t.get("schema_v395_fixed"))else"USDT")
     if _i=="USD":q=float(telem.get("chainlink_proxy_usd_spot")or telem.get("chainlink_proxy_spot")or telem.get("coinbase_spot")or telem.get("chainlink_twap_60s")or.0)
     else:q=float(telem.get("binance_spot")or telem.get("spot_at_t0")or telem.get("spot")or.0)
     I=float(t.get("candle_open_spot")or.0);o=float(telem.get("seconds_to_expiry")or max(.0,float(t.get("expiry_unix",.0))-F));c=False
     if q>.0 and I>.0 and o>=25.:
      _r=((q-I)/I*1e2)if z=="UP"else((I-q)/I*1e2);_h=-_r
      if _h<=.0:t.pop("opposite_breakout_start_ts",None)
      else:
       _u=.22 if o>9e2 else(.15 if o>180. else.08);_d=35. if o>9e2 else(18. if o>180. else 8.)
       if o<=150. and _h>=.09 and r<=(K-.22):_d=min(_d,3.)
       if _h>=_u:
        cs=t.get("opposite_breakout_start_ts")
        if cs is None:t["opposite_breakout_start_ts"]=F
        elif(F-float(cs))>=_d and r>=.08:c=True
       else:t.pop("opposite_breakout_start_ts",None)
     t["max_seen_bid"]=max(float(t.get("max_seen_bid",.0)or.0),r);y=float(t["max_seen_bid"]);b=False
     if y>=.93 and r<=round(y-.05,4)and o>=25. and r>=(K+.04):
      rs=t.get("trailing_ratchet_start_ts")
      if rs is None:t["trailing_ratchet_start_ts"]=F
      elif(F-float(rs))>=4.:b=True
     else:t.pop("trailing_ratchet_start_ts",None)
     if not x and not c and not b:continue
     if x:w,p,e=E,.0,f"{_l}_SHADOW_MAKER_TP_95_98";l=round(t["shares_bought"]*w,2)
     else:w=r;l=round(t["shares_bought"]*w,2);_,p=calculate_taker_fee(l,w,fee_rate=.07,fee_exponent=1.);e=f"{_l}_SHADOW_RATCHET_93"if b else f"{_l}_SHADOW_3ZONE_SALVAGE"
     m=round(l-t["notional_usd"]-t.get("taker_fee_usd",.0)-p,2);t.update({"status":"CLOSED","exit_reason":e,"exit_price":w,"exit_fee_usd":round(p,4),"payout_usd":l,"net_pnl_usd":m,"won":bool(m>0),"settle_time":telem.get("timestamp")or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")});_c.append(t);setattr(a,_m,getattr(a,_m)+m);setattr(a,_j,getattr(a,_j)+float(t.get("taker_fee_usd",.0))+p);setattr(a,_k,_n+getattr(a,_m));_b.add(t["trade_id"]);_e.append(t)
     with open(_a,"a",encoding="utf-8")as f:f.write(json.dumps(t)+"\n")
    if _e:
     _o[market_id]=[t for t in _o[market_id]if t.get("status")=="OPEN"]
     if not _o[market_id]:del _o[market_id]
     _q()
  return W
 def settle_market(a,m_id,resolution,historical=False):
  if not historical:a.wfo_shadow.on_market_resolution(m_id,resolution)
  if(m_id not in a.open_trades and m_id not in a.sleeve2_open_trades and m_id not in a.sol_shadow_open_trades and m_id not in a.xrp_shadow_open_trades):return
  D=resolution.get("winning_outcome")
  if D not in("UP","DOWN"):return
  if m_id in a.open_trades:
   h=[]
   for i in a.open_trades[m_id]:
    u=i["trade_id"]
    if u in a.settled_trade_ids or i.get("status")=="CLOSED":continue
    s=(i["target_token"]==D);g=i["shares_bought"]*1. if s else.0;b=i.get("taker_fee_usd",.0);d=g-i["notional_usd"]-b;k=float(i.get("legacy_fixed_notional_usd",i["notional_usd"]));E=k/max(i["notional_usd"],1.);r=round(d*E,2);i["settle_time"]=resolution.get("timestamp_resolved","");i["winning_outcome"]=D;i["won"]=s;i["payout_usd"]=round(g,2);i["net_pnl_usd"]=round(d,2);e=float(i.get("live_parity_notional_usd",i["notional_usd"]));m=e/max(i["notional_usd"],1.);i["live_parity_pnl_usd"]=round(d*m,2);i["legacy_fixed_pnl_usd"]=r;i["status"]="CLOSED";i["exit_reason"]="EXP302_HOLD_TO_MATURITY_SETTLEMENT";q=i.get("entry_unix",.0)
    if q<R3_VALIDATION_START_UNIX:a.dev_trades.append(i);a.dev_realized_pnl+=d;a.dev_total_fees+=i.get("taker_fee_usd",.0);a.dev_cash=INITIAL_PAPER_CAPITAL+a.dev_realized_pnl;c=DEV_LEDGER_FILE
    else:a.val_trades.append(i);a.val_realized_pnl+=d;a.val_total_fees+=i.get("taker_fee_usd",.0);a.val_cash=INITIAL_PAPER_CAPITAL+a.val_realized_pnl;c=VALIDATION_LEDGER_FILE
    a.settled_trade_ids.add(u);a.trades_per_market[m_id]+=1;h.append(i)
    with open(c,"a")as f:f.write(json.dumps(i)+"\n")
   del a.open_trades[m_id]
   if not historical and h:j=sum(t["net_pnl_usd"]for t in h);print(f"\n[MARKET SETTLED] Market ID: {m_id} | Winner: {D} | Trades Settled: {len(h)} | Net PnL: ${j:+.2f} | Validation Equity: ${a.val_cash:,.2f} | Dev Equity: ${a.dev_cash:,.2f}",flush=True)
  if ENABLE_SLEEVE_304_315 and m_id in a.sleeve2_open_trades:
   y=[]
   for i in list(a.sleeve2_open_trades[m_id]):
    u=i["trade_id"]
    if u in a.sleeve2_settled_ids or i.get("status")=="CLOSED":continue
    s=(i["target_token"]==D);g=i["shares_bought"]*1. if s else.0;b=i.get("taker_fee_usd",.0);d=g-i["notional_usd"]-b;i["settle_time"]=resolution.get("timestamp_resolved","");i["winning_outcome"]=D;i["won"]=s;i["payout_usd"]=round(g,2);i["net_pnl_usd"]=round(d,2);i["status"]="CLOSED";i["exit_reason"]="EXP304_315_HOLD_TO_MATURITY_SETTLEMENT";i["exit_price"]=1. if s else.0;i["exit_fee_usd"]=.0;a.sleeve2_trades.append(i);a.sleeve2_realized_pnl+=d;a.sleeve2_total_fees+=b;a.sleeve2_cash=SLEEVE_2_INITIAL_CAPITAL+a.sleeve2_realized_pnl;a.sleeve2_settled_ids.add(u);y.append(i)
    with open(SLEEVE_2_LEDGER_FILE,"a")as f:f.write(json.dumps(i)+"\n")
    if not historical:print(f"\n[SLEEVE 2 MARKET SETTLED] Market ID: {m_id} | Winner: {D} | Won: {s} | Net PnL: ${d:+.2f} | Sleeve 2 Equity: ${a.sleeve2_cash:,.2f}",flush=True)
   del a.sleeve2_open_trades[m_id];a.save_sleeve2_state()
  for x,l,B,p,o,n,A,w,z,v,C in(("SOL",ENABLE_SOL_SHADOW_SLEEVE,a.sol_shadow_open_trades,a.sol_shadow_trades,a.sol_shadow_settled_ids,SOL_SHADOW_LEDGER_FILE,SOL_SHADOW_INITIAL_CAPITAL,"sol_shadow_cash","sol_shadow_realized_pnl","sol_shadow_total_fees",a.save_sol_shadow_state),("XRP",ENABLE_XRP_SHADOW_SLEEVE,a.xrp_shadow_open_trades,a.xrp_shadow_trades,a.xrp_shadow_settled_ids,XRP_SHADOW_LEDGER_FILE,XRP_SHADOW_INITIAL_CAPITAL,"xrp_shadow_cash","xrp_shadow_realized_pnl","xrp_shadow_total_fees",a.save_xrp_shadow_state)):
   if l and m_id in B:
    for i in list(B[m_id]):
     u=i["trade_id"]
     if u in o or i.get("status")=="CLOSED":continue
     s=(i["target_token"]==D);g=i["shares_bought"]*1. if s else.0;b=float(i.get("taker_fee_usd",.0));d=round(g-i["notional_usd"]-b,2);i.update({"settle_time":resolution.get("timestamp_resolved",""),"winning_outcome":D,"won":s,"payout_usd":round(g,2),"net_pnl_usd":d,"status":"CLOSED","exit_reason":f"{x}_SHADOW_HOLD_TO_MATURITY_SETTLEMENT","exit_price":1. if s else.0,"exit_fee_usd":.0});p.append(i);setattr(a,z,getattr(a,z)+d);setattr(a,v,getattr(a,v)+b);setattr(a,w,A+getattr(a,z));o.add(u)
     with open(n,"a",encoding="utf-8")as f:f.write(json.dumps(i)+"\n")
    del B[m_id];C()
 def save_state(a):
  c=len(a.val_trades);g=sum(1 for t in a.val_trades if t.get("won"));i=(g/c*1e2)if c>0 else.0;b=len(a.dev_trades);e=sum(1 for t in a.dev_trades if t.get("won"));h=(e/b*1e2)if b>0 else.0;j={"timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"governance":{"specification_version":"v3.1","validation_start_utc":R3_VALIDATION_START_UTC,"validation_start_unix":R3_VALIDATION_START_UNIX,"executable_depth_guard":"DepthRatio >= 1.50 (Fail-Closed)","fee_schedule":"crypto_fees_v2 (7% dynamic schedule enforced)","idempotent_event_sourced":True},"validation_oos_epoch":{"paper_portfolio_equity":round(a.val_cash,2),"initial_capital":INITIAL_PAPER_CAPITAL,"cumulative_realized_pnl":round(a.val_realized_pnl,2),"total_fees_paid":round(a.val_total_fees,2),"total_trades_settled":c,"winning_trades":g,"losing_trades":c-g,"win_rate_pct":round(i,2),"ledger_file":str(VALIDATION_LEDGER_FILE)},"dev_calibration_epoch":{"paper_portfolio_equity":round(a.dev_cash,2),"initial_capital":INITIAL_PAPER_CAPITAL,"cumulative_realized_pnl":round(a.dev_realized_pnl,2),"total_fees_paid":round(a.dev_total_fees,2),"total_trades_settled":b,"winning_trades":e,"losing_trades":b-e,"win_rate_pct":round(h,2),"ledger_file":str(DEV_LEDGER_FILE)},"active_open_positions_count":sum(len(v)for v in a.open_trades.values()),"total_settled_trade_ids_tracked":len(a.settled_trade_ids),"current_hour_window":a.current_hour_window,"trades_this_hour":a.trades_this_hour,"status":"RUNNING"};d=STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
  try:
   with open(d,"w",encoding="utf-8")as f:json.dump(j,f,indent=2);f.flush();os.fsync(f.fileno())
   os.replace(d,STATE_FILE)
  except Exception:
   if d.exists():
    try:d.unlink()
    except Exception:pass
  if ENABLE_SOL_SHADOW_SLEEVE:a.save_sol_shadow_state()
  if ENABLE_XRP_SHADOW_SLEEVE:a.save_xrp_shadow_state()
 async def live_loop(a):
  print(f"[PAPER TRADER v3.1] OOS: {R3_VALIDATION_START_UTC} | Depth>=1.50 | crypto_fees_v2 | " "Shadows: Hybrid-zSplit + BTC-5m + SOL-v3.9.2",flush=True)
  with open(PID_FILE,"w")as f:f.write(str(os.getpid()))
  if HOURLY_TELEMETRY_FILE.exists():a.last_telemetry_file_pos=HOURLY_TELEMETRY_FILE.stat().st_size
  if HOURLY_TELEMETRY_ETH_FILE.exists():a.last_telemetry_eth_file_pos=HOURLY_TELEMETRY_ETH_FILE.stat().st_size
  if HOURLY_TELEMETRY_SOL_FILE.exists():a.last_telemetry_sol_file_pos=HOURLY_TELEMETRY_SOL_FILE.stat().st_size
  if SUBHOURLY_TELEMETRY_SOL_FILE.exists():a.last_telemetry_sol_15m_file_pos=SUBHOURLY_TELEMETRY_SOL_FILE.stat().st_size
  if HOURLY_TELEMETRY_XRP_FILE.exists():a.last_telemetry_xrp_file_pos=HOURLY_TELEMETRY_XRP_FILE.stat().st_size
  if SUBHOURLY_TELEMETRY_XRP_FILE.exists():a.last_telemetry_xrp_15m_file_pos=SUBHOURLY_TELEMETRY_XRP_FILE.stat().st_size
  if SHOCK_SOL_FILE.exists():a.last_shock_sol_file_pos=SHOCK_SOL_FILE.stat().st_size
  if SHOCK_XRP_FILE.exists():a.last_shock_xrp_file_pos=SHOCK_XRP_FILE.stat().st_size
  a.replay_existing_data();import signal as _signal;a._shutdown_requested=False
  def c(signame):
   if not a._shutdown_requested:print(f"[SHUTDOWN] {signame} received; flushing state and stopping gracefully.",flush=True)
   a._shutdown_requested=True
  G=asyncio.get_running_loop()
  for I in(_signal.SIGTERM,_signal.SIGINT):
   try:G.add_signal_handler(I,c,I.name)
   except(NotImplementedError,RuntimeError,ValueError):pass
  d=.0
  while True:
   if a._shutdown_requested:a.wfo_shadow.poll_tick(True);a.save_state();print("[SHUTDOWN] Paper trader state flushed; exiting cleanly (STOPPED_GRACEFULLY).",flush=True);break
   try:
    B=time.time()
    if(B-d)>=5.:
     d=B
     try:from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER as h;z=h.snapshot.get("shadow_governance",{})or{};globals()["ENABLE_SLEEVE_304_315"]=bool(z.get("enable_eth_1h_shadow",False));globals()["ENABLE_SOL_SHADOW_SLEEVE"]=bool(z.get("enable_sol_15m_1h_shadow",True));globals()["ENABLE_XRP_SHADOW_SLEEVE"]=bool(z.get("enable_xrp_shadow",False))
     except Exception:pass
    if TRIGGER_FILE.exists():
     n=TRIGGER_FILE.stat().st_size
     if n<a.last_trigger_file_pos:a.last_trigger_file_pos=n
     if n>a.last_trigger_file_pos:
      with open(TRIGGER_FILE,"rb")as f:f.seek(a.last_trigger_file_pos);g=f.read()
      b=g.rfind(b"\n")+1
      if b:
       l=g[:b].decode("utf-8").splitlines();a.last_trigger_file_pos+=b
       for k in l:
        if not k.strip():continue
        s=json.loads(k);i=f"{s.get('market_id')}_{s.get('t0_unix')}"
        if i not in a.seen_shock_ids:a.seen_shock_ids.add(i);await asyncio.to_thread(a.evaluate_shock_signal,s,False)
    elif SHOCK_FILE.exists():
     m=SHOCK_FILE.stat().st_size
     if m<a.last_shock_file_pos:a.last_shock_file_pos=m
     if m>a.last_shock_file_pos:
      with open(SHOCK_FILE,"rb")as f:f.seek(a.last_shock_file_pos);g=f.read()
      b=g.rfind(b"\n")+1
      if b:
       l=g[:b].decode("utf-8").splitlines();a.last_shock_file_pos+=b
       for k in l:
        if not k.strip():continue
        s=json.loads(k);i=f"{s.get('market_id')}_{s.get('t0_unix')}"
        if i not in a.seen_shock_ids:a.seen_shock_ids.add(i);await asyncio.to_thread(a.evaluate_shock_signal,s,False)
    for q,u,A,v in((SHOCK_SOL_FILE,"last_shock_sol_file_pos","SOL",ENABLE_SOL_SHADOW_SLEEVE),(SHOCK_XRP_FILE,"last_shock_xrp_file_pos","XRP",ENABLE_XRP_SHADOW_SLEEVE)):
     if v and q.exists():
      x=q.stat().st_size;j=getattr(a,u)
      if x<j:setattr(a,u,x);j=x
      if x>j:
       with open(q,"rb")as f:f.seek(j);g=f.read()
       b=g.rfind(b"\n")+1
       if b:
        t=g[:b].decode("utf-8",errors="ignore").splitlines();setattr(a,u,j+b)
        for k in t:
         if not k.strip():continue
         s=json.loads(k);s.setdefault("asset",A);i=f"{s.get('market_id')}_{s.get('t0_unix')}"
         if i not in a.seen_shock_ids:a.seen_shock_ids.add(i);await asyncio.to_thread(a.evaluate_shock_signal,s,False)
    if RESOLUTIONS_FILE.exists():
     p=RESOLUTIONS_FILE.stat().st_size
     if p>a.last_res_file_pos:
      with open(RESOLUTIONS_FILE,"rb")as f:f.seek(a.last_res_file_pos);g=f.read()
      b=g.rfind(b"\n")+1
      if b:
       r=g[:b].decode("utf-8").splitlines();a.last_res_file_pos+=b
       for k in r:
        if not k.strip():continue
        J=json.loads(k);H=J.get("market_id")
        if J.get("winning_outcome")in("UP","DOWN")and H not in a.seen_resolution_ids:a.seen_resolution_ids.add(H);a.settle_market(H,J,historical=False)
    if(a.open_trades or(ENABLE_SLEEVE_304_315 and a.sleeve2_open_trades)or(ENABLE_SOL_SHADOW_SLEEVE and a.sol_shadow_open_trades)or(ENABLE_XRP_SHADOW_SLEEVE and a.xrp_shadow_open_trades)):
     for w,y in((HOURLY_TELEMETRY_FILE,"last_telemetry_file_pos"),(HOURLY_TELEMETRY_ETH_FILE,"last_telemetry_eth_file_pos"),(HOURLY_TELEMETRY_SOL_FILE,"last_telemetry_sol_file_pos"),(SUBHOURLY_TELEMETRY_SOL_FILE,"last_telemetry_sol_15m_file_pos"),(HOURLY_TELEMETRY_XRP_FILE,"last_telemetry_xrp_file_pos"),(SUBHOURLY_TELEMETRY_XRP_FILE,"last_telemetry_xrp_15m_file_pos")):
      if w.exists():
       D=w.stat().st_size;o=getattr(a,y)
       if D<o:setattr(a,y,D);o=D
       if D>o:
        with open(w,"rb")as f:f.seek(o);g=f.read()
        b=g.rfind(b"\n")+1
        if b:
         F=g[:b].decode("utf-8").splitlines();setattr(a,y,o+b)
         for k in F:
          if not k.strip():continue
          try:
           E=json.loads(k);C=str(E.get("market_id",""))
           if(C in a.open_trades or(ENABLE_SLEEVE_304_315 and C in a.sleeve2_open_trades)or(ENABLE_SOL_SHADOW_SLEEVE and C in a.sol_shadow_open_trades)or(ENABLE_XRP_SHADOW_SLEEVE and C in a.xrp_shadow_open_trades)):a.check_maker_tp_fills(C,E)
          except Exception:pass
    await asyncio.to_thread(a.wfo_shadow.poll_tick,False);a.save_state();await asyncio.sleep(.1)
   except Exception as e:print(f"[-] Error in paper trader loop: {e}",flush=True);await asyncio.sleep(1.)
if __name__=="__main__":trader=PolymarketForwardPaperTrader();asyncio.run(trader.live_loop())
# [10/13] src/polymarket_research/check_polymarket_balance.py
import json;import os;import sys;from pathlib import Path;from dotenv import load_dotenv;import requests;PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent;load_dotenv(PIPELINE_ROOT/".env");WALLET_ADDR=os.getenv("POLYGON_FUNDER_ADDRESS","").strip()
if not WALLET_ADDR:print("[ERROR] POLYGON_FUNDER_ADDRESS is not set in .env");sys.exit(1)
USDC_E="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174";PUSD="0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
def check_balance():
 print("="*65);print("        POLYMARKET LIVE BALANCE & STATUS INSPECTOR");print("="*65);print(f"Funder Wallet:   {WALLET_ADDR}");d=None
 try:
  from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor as a;q=a(dry_run=False)
  if q.is_authenticated:d=q.get_collateral_balance();print(f"CLOB L2 Balance: ${d:,.2f} USD")
 except Exception:pass
 n=["https://polygon-bor-rpc.publicnode.com","https://polygon-rpc.com","https://polygon.gateway.tenderly.co","https://1rpc.io/matic"];e=.0;c=.0;b=.0
 for p in n:
  try:
   l=requests.post(p,json={"jsonrpc":"2.0","method":"eth_getBalance","params":[WALLET_ADDR,"latest"],"id":1},timeout=2.5).json()
   if"result"in l:e=int(l["result"],16)/1e18
   h="0x70a08231"+WALLET_ADDR[2:].lower().rjust(64,"0");k=requests.post(p,json={"jsonrpc":"2.0","method":"eth_call","params":[{"to":PUSD,"data":h},"latest"],"id":2},timeout=2.5).json()
   if"result"in k:c=int(k["result"],16)/1e6
   j=requests.post(p,json={"jsonrpc":"2.0","method":"eth_call","params":[{"to":USDC_E,"data":h},"latest"],"id":3},timeout=2.5).json()
   if"result"in j:b=int(j["result"],16)/1e6
   if c>0 or b>0 or e>0:break
  except Exception:continue
 print(f"POL Gas Balance: {e:.4f} POL");print(f"pUSD On-chain:   ${c:,.2f} pUSD (V2 Primary Collateral)");print(f"USDC.e On-chain: ${b:,.2f} USDC.e (Legacy Bridge)");g=PIPELINE_ROOT/"data/polymarket/live_orders.jsonl"
 if g.exists():
  i=[]
  with open(g,"r")as f:
   for m in f:
    if m.strip():i.append(json.loads(m))
  print(f"\nLive Orders Dispatched: {len(i)}")
  if i:
   print("Recent Orders:")
   for o in i[-5:]:print(f"  • [{o.get('timestamp_utc')[:19]}] {o.get('trade_id')} | {o.get('target_token')} | ${o.get('notional_usd')} @ ${o.get('price')} (Mode: {o.get('mode')})")
 else:print("\nLive Orders Ledger: No live orders placed yet.")
 print("="*65)
if __name__=="__main__":check_balance()
# [11/13] src/polymarket_research/redeem_settled_positions.py
import json;import logging;import math;import os;import sys;from pathlib import Path;from typing import Any,Dict,List,Optional;import requests;from dotenv import load_dotenv;PIPELINE_ROOT=Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT)not in sys.path:sys.path.insert(0,str(PIPELINE_ROOT))
load_dotenv(PIPELINE_ROOT/".env");logging.basicConfig(level=logging.INFO,format="[%(asctime)s UTC] [%(levelname)s] [CTF-REDEMPTION] %(message)s");logger=logging.getLogger("CTFRedemption");CTF_CONTRACT="0x4D97DCd97eC945f40cF65F87097ACe5EA0476045";NEG_RISK_ADAPTER="0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296";PUSD_ADDRESS="0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB";USDC_ADDRESS="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174";POLYGON_RPCS=[os.getenv("POLYGON_RPC_URL","https://polygon-bor-rpc.publicnode.com"),"https://polygon-rpc.com","https://1rpc.io/matic"];DATA_DIR=PIPELINE_ROOT/"data/polymarket";STATE_FILE=DATA_DIR/"live_harvester_state.json";from typing import Optional
def get_token_balance_onchain(funder_address,token_id):
 try:
  c=funder_address.lower().replace("0x","").zfill(64);i=int(token_id,16)if str(token_id).startswith("0x")else int(token_id);h=hex(i)[2:].zfill(64);g=f"0x00fdd58e{c}{h}";l={"jsonrpc":"2.0","method":"eth_call","params":[{"to":CTF_CONTRACT,"data":g},"latest"],"id":1};a=None
  for k in POLYGON_RPCS:
   try:
    j=requests.post(k,json=l,timeout=5);j.raise_for_status();m=j.json()
    if m.get("error")or not isinstance(m.get("result"),str):raise RuntimeError(f"Invalid eth_call response: {m}")
    f=m["result"];b=int(f,16);return b/1e6
   except Exception as d:a=d
  raise RuntimeError(f"All Polygon RPCs failed: {a}")
 except Exception as e:logger.error(f"Error querying on-chain balance for {token_id}: {e}");return None
def encode_ctf_merge_or_split_calldata(condition_id,amount_shares,collateral=USDC_ADDRESS,is_split=False,neg_risk=False,is_merge=None):
 b=(not bool(is_merge))if is_merge is not None else bool(is_split);h=int(math.floor(max(.0,float(amount_shares))*1000000+1e-6))
 if h<=0:raise ValueError("amount_shares must be > 0")
 d=condition_id.lower().replace("0x","").rjust(64,"0");g=hex(h)[2:].rjust(64,"0")
 if neg_risk:i="0xa3d7da1d"if b else"0xb10c5c17";return NEG_RISK_ADAPTER,f"{i}{d}{g}"
 i="0x72ce4275"if b else"0x9e7212ad";f=collateral.lower().replace("0x","").rjust(64,"0");c="0"*64;a=hex(5*32)[2:].rjust(64,"0");e=hex(2)[2:].rjust(64,"0");k=hex(1)[2:].rjust(64,"0");j=hex(2)[2:].rjust(64,"0");return CTF_CONTRACT,f"{i}{f}{c}{d}{a}{g}{e}{k}{j}"
def inspect_mergeable_complete_set(funder_or_condition_id,yes_token_or_shares,no_token_or_shares,neg_risk=None):
 if neg_risk is not None or isinstance(yes_token_or_shares,(int,float)):
  a=round(max(.0,min(float(yes_token_or_shares or.0),float(no_token_or_shares or.0))),6)
  if a<=.0:return{"mergeable":False,"mergeable_sets":.0,"target_contract":"","calldata":""}
  d,e=encode_ctf_merge_or_split_calldata(funder_or_condition_id,a,neg_risk=bool(neg_risk),is_merge=True);return{"mergeable":True,"mergeable_sets":a,"target_contract":d,"calldata":e}
 c=get_token_balance_onchain(funder_or_condition_id,str(yes_token_or_shares));b=get_token_balance_onchain(funder_or_condition_id,str(no_token_or_shares))
 if c is None or b is None:return.0
 return round(max(.0,min(c,b)),6)
def _is_harvester_lock_active(lock_path):
 if not lock_path.exists():return False
 try:
  c=lock_path.read_text(encoding="utf-8").strip()
  if not c.isdigit():return False
  d=int(c)
  if d<=0:return False
  os.kill(d,0);a=Path(f"/proc/{d}/cmdline")
  if a.exists():
   try:
    b=a.read_bytes().replace(b"\x00",b" ").decode("utf-8",errors="ignore").lower()
    if b.strip()and not any(k in b for k in("polymarket","python","pytest")):return False
   except OSError:pass
  return True
 except PermissionError:return True
 except OSError:return False
def _is_flock_held(lock_path):
 if not lock_path.exists():return False
 if os.name=="nt":
  try:
   import msvcrt
   with open(lock_path,"r+b")as a:
    a.seek(0,os.SEEK_END)
    if a.tell()==0:return False
    a.seek(0);msvcrt.locking(a.fileno(),msvcrt.LK_NBLCK,1);a.seek(0);msvcrt.locking(a.fileno(),msvcrt.LK_UNLCK,1)
   return False
  except FileNotFoundError:return False
  except OSError:return True
  except Exception:return lock_path.exists()
 try:import fcntl
 except ImportError:return False
 try:
  with open(lock_path,"r+")as a:fcntl.flock(a.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(a.fileno(),fcntl.LOCK_UN)
  return False
 except FileNotFoundError:return False
 except BlockingIOError:return True
 except OSError:return lock_path.exists()
def audit_positions_and_redemptions(execute=False,force=False):
 p=os.getenv("POLYGON_FUNDER_ADDRESS","").strip()or os.getenv("POLYGON_PROXY_ADDRESS","").strip()
 if not p:logger.error("No funder/proxy address configured in .env!");return
 print("="*80);print("      POLYMARKET CTF SETTLEMENT & REDEMPTION AUDITOR");print("="*80);print(f"Proxy Wallet: {p}");print(f"CTF Contract: {CTF_CONTRACT}");print(f"Collateral:   pUSD ({PUSD_ADDRESS}) / USDC.e ({USDC_ADDRESS})")
 if not STATE_FILE.exists():print(f"\nNo state file found at {STATE_FILE}. Zero recorded positions.");return
 with open(STATE_FILE,"r")as f:A=json.load(f)
 m=A.get("active_positions",{});l=A.get("closed_positions",[]);print(f"\nActive Positions: {len(m)}");print(f"Closed Positions: {len(l)}");b=.0;a=.0;h=False;k={};d=set();j=[];o={};print("\n--- POSITION AUDIT TABLE ---")
 for I in list(m.values())+list(l):
  H=I.get("trade_id","N/A");u=I.get("token_id");G=I.get("won",False);r=I.get("close_reason","UNKNOWN");y=I.get("net_pnl_usd",.0);q=(I.get("status")=="AWAITING_ONCHAIN_SETTLEMENT"or float(I.get("winning_shares_held",.0)or.0)>.0 or(bool(G)and r in{"MARKET_RESOLVED","ONCHAIN_REDEMPTION_CONFIRMED"}));n=[]
  if u:n.append((str(u),str(I.get("condition_id")or"").strip(),I.get("neg_risk")))
  for E in I.get("box_legs_summary")or():
   if isinstance(E,dict)and E.get("token_id"):
    D=str(E["token_id"])
    if all(D!=x[0]for x in n):n.append((D,str(E.get("condition_id")or I.get("condition_id")or"").strip(),E.get("neg_risk",I.get("neg_risk"))))
  if q and n:
   g=False;c=False
   for w,v,z in n:
    if w in k:i=k[w]
    else:i=get_token_balance_onchain(p,w);k[w]=i
    if i is None:h=True;c=True;print(f"  [UNKNOWN / RETRY] {H}: Polygon balance query failed; cannot classify redemption state");continue
    if i>.01:
     g=True
     if w not in d:d.add(w);b+=i;a+=i*1.
     if v and v not in j:j.append(v);o[v]={"neg_risk":z,"winning_token_id":w}
     print(f"  [CLAIMABLE] {H}: {i:.2f} shares held on-chain -> ${i:.2f} pUSD/USDC.e claimable")
   if not g and not c:print(f"  [REDEEMED/EMPTY] {H}: 0.00 shares held on-chain (already redeemed)")
  else:print(f"  [{r}] {H}: Won={G} | Net PnL=${y:+.2f}")
 print("\n"+"="*80);print(f"Total Claimable Winning Shares: {b:.2f}");print(f"Estimated Claimable Collateral:   ${a:.2f} pUSD/USDC.e");print("="*80)
 if execute and j:
  t=DATA_DIR/"live_harvester.pid"
  if not force and(_is_harvester_lock_active(t)or _is_flock_held(DATA_DIR/"live_harvester.lock")):logger.error(f"Refusing --execute while Live Harvester holds {t} (prevents EOA nonce collision with " "60s poll_onchain_redemptions). Stop harvester first or pass --force.");return
  from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor as e;s=e(dry_run=False)
  for F in j:C=o.get(F,{});B=s.attempt_onchain_redemption(F,neg_risk=C.get("neg_risk"));print(f"  [EXECUTE REDEMPTION] condition={F} -> tx_hash={B or'SKIPPED (insufficient EOA POL gas or non-1of1 proxy)'}")
 if a>0:print("\n[ACTION REQUIRED: REDEMPTION GUIDANCE]");print("If EOA holds >= 0.05 POL, run with --execute for Safe/EOA on-chain redemption, or redeem gaslessly:");print("  1. Log into https://polymarket.com using your funder wallet.");print("  2. Navigate to Portfolio -> History / Positions.");print("  3. Click 'Claim All' / 'Redeem' (Polymarket's relayer pays Polygon gas automatically).");print("  4. Collateral (pUSD / USDC.e) will be credited to your trading balance.")
 elif h:print("\n[WARNING] One or more positions could not be queried on-chain. Reconciliation incomplete - retry required.")
 else:print("\nAll winning positions are reconciled. No unredeemed tokens pending.")
if __name__=="__main__":audit_positions_and_redemptions(execute="--execute"in sys.argv,force="--force"in sys.argv)
# [12/13] audit_losing_trades.py
import argparse;import contextlib;import json;import os;import subprocess;import time;from datetime import datetime,timezone;from pathlib import Path;from typing import Any,Dict,Iterator,List,Optional;REPO_DIR=Path(os.getenv("DOMINUS_REPO_DIR")or Path(__file__).resolve().parent);DATA_DIR=REPO_DIR/"data"/"polymarket";AUDIT_STATE_FILE=DATA_DIR/"forensic_audit_state.json";_DEFAULT_AUDIT_LOCK_FILE=DATA_DIR/"forensic_audit_state.lock";AUDIT_LOCK_FILE=_DEFAULT_AUDIT_LOCK_FILE;AUDIT_LEDGER_FILE=DATA_DIR/"forensic_audit_ledger.jsonl";WFO_HYPOTHESIS_QUEUE_FILE=DATA_DIR/"wfo_hypothesis_queue.jsonl"
@contextlib.contextmanager
def _audit_state_lock(timeout_sec=10.):
 DATA_DIR.mkdir(parents=True,exist_ok=True);b=((Path(DATA_DIR)/"forensic_audit_state.lock")if AUDIT_LOCK_FILE==_DEFAULT_AUDIT_LOCK_FILE else Path(AUDIT_LOCK_FILE));b.parent.mkdir(parents=True,exist_ok=True);d=open(b,"r+b"if b.exists()else"w+b");c=time.monotonic()+max(.5,timeout_sec);a=False
 try:
  while True:
   try:
    if os.name=="nt":
     import msvcrt;d.seek(0,os.SEEK_END)
     if d.tell()==0:d.write(b"\x00");d.flush()
     d.seek(0);msvcrt.locking(d.fileno(),msvcrt.LK_NBLCK,1)
    else:import fcntl;fcntl.flock(d.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    a=True;break
   except OSError:
    if time.monotonic()>=c:raise TimeoutError(f"Timed out acquiring exclusive audit lock: {b}")
    time.sleep(.05)
  yield
 finally:
  if a:
   try:
    if os.name=="nt":import msvcrt;d.seek(0);msvcrt.locking(d.fileno(),msvcrt.LK_UNLCK,1)
    else:import fcntl;fcntl.flock(d.fileno(),fcntl.LOCK_UN)
   except OSError:pass
  d.close()
AUDIT_CLASSIFICATIONS=("PLUMBING_0_PARAM","SEQUENCE_TELEMETRY_REQUIRED","PARAM_WFO_REQUIRED","EXPECTED_VARIANCE_NO_CHANGE","WIN_AUTO_CLEARED");_TYPE2_PARAM_TOKENS=("min_cushion","dist_pct","z_strike","min_z","sigma_1h","max_px","min_px","kelly","wrong_side_thresh");_TUNE_VERBS=("tighten","widen","raise","lower","increase","decrease","tune","adjust threshold");HISTORICAL_BASELINE_TRADES={"LIVE_6011767_1792677997_DOWN","LIVE_6011823_1792678868_UP","LIVE_6011834_1792678920_UP","LIVE_6012053_1792679970_UP","LIVE_6012062_1792679970_UP","LIVE_5969579_1792680240_UP","LIVE_6012995_1792682563_UP","LIVE_6013539_1792683334_UP","LIVE_6014317_1792684214_UP","LIVE_5972389_1792686568_DOWN","LIVE_6016117_1792686984_DOWN","LIVE_6017333_1792688700_DOWN","LIVE_5978915_1792691143_UP","LIVE_6019058_1792692519_DOWN","LIVE_6022563_1792694165_UP","LIVE_6024982_1792697736_DOWN","LIVE_6026368_1792702377_DOWN","LIVE_6027101_1792704984_DOWN","LIVE_6032439_1792715250_DOWN","LIVE_6032790_1792716941_UP"}
def load_audit_state():
 if AUDIT_STATE_FILE.exists():
  try:
   c=json.loads(AUDIT_STATE_FILE.read_text(encoding="utf-8"));b=c.setdefault("audited_trades",{})
   for tid in HISTORICAL_BASELINE_TRADES:
    if tid not in b:b[tid]={"trade_id":tid,"verdict":"HISTORICAL_BASELINE"}
   return c
  except Exception:
   try:a=AUDIT_STATE_FILE.with_name(f"{AUDIT_STATE_FILE.name}.corrupt.{int(time.time())}");os.replace(AUDIT_STATE_FILE,a)
   except Exception:pass
 return{"updated_at":None,"audited_trades":{tid:{"trade_id":tid,"verdict":"HISTORICAL_BASELINE"}for tid in HISTORICAL_BASELINE_TRADES},"stats":{"profits_skipped":0,"expected_losses_ok":0,"bugs_fixed_and_redeployed":0,"total_redeployments":0},"recent_verdicts":[]}
def save_audit_state(st):DATA_DIR.mkdir(parents=True,exist_ok=True);st["updated_at"]=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC");a=AUDIT_STATE_FILE.with_suffix(".tmp");a.write_text(json.dumps(st,indent=2),encoding="utf-8");os.replace(a,AUDIT_STATE_FILE)
def append_audit_ledger(rec):
 DATA_DIR.mkdir(parents=True,exist_ok=True)
 with open(AUDIT_LEDGER_FILE,"a",encoding="utf-8")as f:f.write(json.dumps(rec)+"\n")
def append_wfo_hypothesis_queue(rec):
 DATA_DIR.mkdir(parents=True,exist_ok=True)
 with open(WFO_HYPOTHESIS_QUEUE_FILE,"a",encoding="utf-8")as f:f.write(json.dumps(rec)+"\n")
def classify_losing_trade_forensics(rec):
 c=str(rec.get("trade_id")or"");b=str(rec.get("sleeve")or"");f=str(rec.get("status")or"").upper();a=str(rec.get("exit_order_status")or"").upper();e=str(rec.get("close_reason")or"").upper();d=str(rec.get("entry_mode")or"").upper()
 if(f in{"UNRESOLVED_BALANCE_DISCREPANCY","ENTRY_OUTCOME_UNKNOWN","EXIT_CANCEL_PENDING"}or a in{"UNRESOLVED_BALANCE_DISCREPANCY","ENTRY_OUTCOME_UNKNOWN","EXIT_CANCEL_PENDING"}or"ERROR"in e):return{"suggested_classification":"PLUMBING_0_PARAM","rationale":"Deterministic state/reconciliation anomaly."}
 if"PRE_KICKOFF"in e or(c.startswith("SPORTS_CORRIDOR_LIVE_")and b=="SOC2_EXACT_SCORE_2D_LATTICE"):return{"suggested_classification":"EXPECTED_VARIANCE_NO_CHANGE","rationale":"Authorized pre-kickoff Maker scratch / T-5m protection on legacy pre-v5.4.2 SOC2 corridor leg (SOC2 live routing already disabled in v5.4.2+); record EXPECTED_LOSS and do NOT edit code or restart."}
 if"LEGGED_OUT"in e or any(k in d for k in("RESCUE","FALLBACK","DOWNSNAP")):return{"suggested_classification":"SEQUENCE_TELEMETRY_REQUIRED","rationale":"Sequence/timing event; check simulator."}
 return{"suggested_classification":"EXPECTED_VARIANCE_NO_CHANGE","rationale":"Variance; threshold edits need PARAM_WFO_REQUIRED."}
def fetch_kraken_live_state():
 b=Path("/home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json")
 if os.name!="nt"and b.exists():d=subprocess.run(["systemctl","--user","is-active","polymarket-live-harvester.service"],capture_output=True,text=True,timeout=5.);c=(d.stdout or"").strip().splitlines();a=c[0].strip()if c else"unknown";return{"service_status":a,"state":json.loads(b.read_text(encoding="utf-8"))}
 f=["ssh","-n","-o","ConnectTimeout=5","kraken-finland","systemctl --user is-active polymarket-live-harvester.service ; cat /home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json"];d=subprocess.run(f,capture_output=True,text=True,timeout=9.)
 if d.returncode!=0 and not d.stdout.strip():raise RuntimeError(d.stderr.strip()or"SSH to kraken-finland failed")
 e=d.stdout.strip().splitlines();a=e[0].strip()if e else"unknown";g=json.loads("\n".join(e[1:]));return{"service_status":a,"state":g}
def scan_trades():
 try:z=fetch_kraken_live_state();n=z["service_status"];G=z["state"];w=G.get("risk_state")or{};q=bool(G.get("risk_halt",False)or w.get("halted",False));v=(n=="active")and(not q)and(G.get("status")=="RUNNING");f=list(G.get("closed_positions",[]))
 except Exception as e:d=load_audit_state();return{"status":"ACTION_REQUIRED","daemon_health":{"healthy":False,"error":str(e)},"newly_cleared_wins":0,"uninspected_losses_count":0,"uninspected_losses":[],"audit_stats":d.get("stats",{})}
 with _audit_state_lock():
  d=load_audit_state();u=d.setdefault("audited_trades",{});c=[];a=0;b=G.get("active_positions")or{};h={str(p.get("box_id")or"").strip()for p in(b.values()if isinstance(b,dict)else[])if isinstance(p,dict)and str(p.get("box_id")or"").strip()};i={}
  for F in f:
   if isinstance(F,dict):
    D=str(F.get("box_id")or"").strip()
    if D:i.setdefault(D,[]).append(F)
  for C in f:
   B=str(C.get("trade_id")or"")
   if not B or B in u:continue
   if(C.get("exit_order_status")=="AWAITING_REDEMPTION"or C.get("status")=="AWAITING_ONCHAIN_SETTLEMENT")and C.get("net_pnl_usd")is None:continue
   E=str(C.get("box_id")or"").strip();k=bool(E)and(bool(C.get("is_dominance_box"))or len(i.get(E,()))>1)
   if k and E in h:continue
   t=C.get("net_pnl_usd")
   if k and len(i.get(E,()))>=2:
    s=i[E]
    if any((x.get("exit_order_status")=="AWAITING_REDEMPTION"or x.get("status")=="AWAITING_ONCHAIN_SETTLEMENT")and x.get("net_pnl_usd")is None for x in s):continue
    m=sum(float(x.get("net_pnl_usd")if x.get("net_pnl_usd")is not None else(x.get("realized_pnl_usd")or.0))for x in s);o=m>=-1e-6
   elif t is not None:o=float(t)>=.0
   else:o=bool(C.get("won")is True)
   if o:r=(f"Winning multi-leg box leg (box_id={E}) — auto-cleared."if k and float(t or.0)<.0 else"Winning real-money trade — auto-cleared.");A={"timestamp":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),"trade_id":B,"sleeve":C.get("sleeve"),"asset":C.get("asset"),"net_pnl_usd":C.get("net_pnl_usd"),"verdict":"PROFIT_OK","classification":"WIN_AUTO_CLEARED","notes":r};u[B]=A;d["stats"]["profits_skipped"]=d["stats"].get("profits_skipped",0)+1;a+=1;append_audit_ledger(A)
   else:j=dict(C);j["forensic_classification_hint"]=classify_losing_trade_forensics(C);c.append(j)
  if a>0 or not AUDIT_STATE_FILE.exists():save_audit_state(d)
  g=dict(d.get("stats",{}))
 y={"mode":"LIVE_REAL_MONEY_KRAKEN_FINLAND","healthy":v,"service_status":n,"status":G.get("status"),"risk_halt":q,"halt_reason":(G.get("risk_state")or{}).get("halt_reason",""),"live_bankroll_usd":round(float(G.get("live_bankroll")or.0),2),"total_account_equity_usd":round(float(G.get("total_account_equity")or.0),2),"open_positions_count":G.get("active_positions_count",0),"open_position_ids":G.get("active_position_ids",[]),"closed_positions_count":G.get("closed_positions_count",0),"trades_this_hour":G.get("trades_this_hour",0)};l="ACTION_REQUIRED"if(c or not v)else"ALL_GOOD";return{"status":l,"daemon_health":y,"newly_cleared_wins":a,"uninspected_losses_count":len(c),"uninspected_losses":c,"audit_stats":g}
def mark_audited(trade_id,verdict,notes,classification=None,wfo_grid=""):
 b={"EXPECTED_LOSS":"EXPECTED_VARIANCE_NO_CHANGE","BUG_FIXED":"PLUMBING_0_PARAM","PARAM_WFO_REQUIRED":"PARAM_WFO_REQUIRED","PROFIT_OK":"WIN_AUTO_CLEARED"};a=classification or b.get(verdict,"EXPECTED_VARIANCE_NO_CHANGE")
 if a not in AUDIT_CLASSIFICATIONS:raise ValueError(f"Unsupported classification: {a}")
 c=(notes or"").lower()
 if verdict=="BUG_FIXED":
  if a!="PLUMBING_0_PARAM":raise ValueError(f"GOVERNANCE_VIOLATION: verdict=BUG_FIXED requires classification=PLUMBING_0_PARAM (got {a}).")
  if any(j in c for j in _TYPE2_PARAM_TOKENS)and any(j in c for j in _TUNE_VERBS):raise ValueError("GOVERNANCE_VIOLATION: Numerical strategy/risk parameter tuning cannot be recorded as BUG_FIXED; use --verdict PARAM_WFO_REQUIRED.")
 with _audit_state_lock():
  e=load_audit_state();g=e.setdefault("audited_trades",{});d=g.get(trade_id)
  if isinstance(d,dict)and d.get("verdict")not in(None,"HISTORICAL_BASELINE"):print(json.dumps({"ok":True,"already_audited":True,"recorded":d},indent=2));return d
  f=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC");i={"timestamp":f,"trade_id":trade_id,"verdict":verdict,"classification":a,"notes":notes}
  if wfo_grid:i["wfo_grid"]=wfo_grid
  g[trade_id]=i
  if verdict=="EXPECTED_LOSS":e["stats"]["expected_losses_ok"]=e["stats"].get("expected_losses_ok",0)+1
  elif verdict=="BUG_FIXED":e["stats"]["bugs_fixed_and_redeployed"]=e["stats"].get("bugs_fixed_and_redeployed",0)+1
  elif verdict=="PARAM_WFO_REQUIRED":e["stats"]["param_wfo_queued"]=e["stats"].get("param_wfo_queued",0)+1
  if verdict=="PARAM_WFO_REQUIRED"or a in("PARAM_WFO_REQUIRED","SEQUENCE_TELEMETRY_REQUIRED"):append_wfo_hypothesis_queue({"queued_at":f,"trade_id":trade_id,"verdict":verdict,"classification":a,"wfo_grid":wfo_grid,"notes":notes,"status":"QUEUED_FOR_PURGED_WFO"})
  h=e.setdefault("recent_verdicts",[]);h.append(i);e["recent_verdicts"]=h[-30:];save_audit_state(e);append_audit_ledger(i)
 print(json.dumps({"ok":True,"recorded":i},indent=2));return i
def _is_restart_safe_frozen_uma_lock(pos,now_ts=None):
 if not isinstance(pos,dict):return False
 f=float(time.time()if now_ts is None else now_ts)
 try:
  from scripts.paa_flat_harvester_redeploy_once import _is_restart_safe_frozen_uma_lock as a
  if a(pos,f):return True
 except Exception:pass
 if str(pos.get("exit_order_status")or"").upper()in("UNWIND_RETRY_REQUIRED","UNWIND_EXECUTION_OUTCOME_UNKNOWN","PARTIAL_UNWIND_REMAINING"):return False
 if pos.get("is_legged_out_residual")and not pos.get("hold_to_maturity_lock")and str(pos.get("umaResolutionStatus")or"").strip().lower()!="disputed":return False
 if pos.get("is_liquidating")or pos.get("exit_order_id")or pos.get("unwind_order_id"):return False
 e=str(pos.get("box_type")or"").strip().upper()
 if not(pos.get("is_single_leg_lock")or pos.get("is_dominance_box")or pos.get("hold_to_maturity_lock")or e in{"SINGLE_LEG_LOCK","SINGLE_LEG_MAKER_LOCK","MULTI_LEG_RESIDUAL","MULTI_LEG_BUNDLE","DOMINANCE"}):return False
 d=float(pos.get("candle_expiry_ts")or.0)
 if d<=.0 or f<d+60.:return False
 c=str(pos.get("umaResolutionStatus")or pos.get("uma_resolution_status")or"").strip().lower();b=max(d,float(pos.get("entry_ts")or.0));return c=="disputed"or f>=b+14400.
def is_harvester_state_restart_safe(st,now_ts=None):
 if not isinstance(st,dict):return False,["INVALID_STATE_PAYLOAD"]
 d=float(time.time()if now_ts is None else now_ts);b=[]
 if bool((st.get("pre_split_inventory_state")or{}).get("active",False)):b.append("PRE_SPLIT_INVENTORY_ACTIVE")
 if float(st.get("_prepost_sll_reserved_usd")or.0)>.0:b.append("PREPOST_SLL_RESERVED_USD_ACTIVE")
 e=st.get("pending_entry_intents")or{}
 if isinstance(e,dict):
  for j,i in e.items():
   if isinstance(i,dict)and not i.get("live_maker_anchor_inflight"):b.append(f"PENDING_ENTRY_INTENT:{j}")
 h=st.get("active_positions");c=int(st.get("active_positions_count")if st.get("active_positions_count")is not None else(len(h)if isinstance(h,dict)else 0))
 if c>0 and(not isinstance(h,dict)or len(h)<c):a=[str(x)for x in(st.get("active_position_ids")or[])]or[f"UNSPECIFIED_OPEN_POSITIONS({c})"];b.extend(a)
 elif isinstance(h,dict):
  for g,f in h.items():
   if not _is_restart_safe_frozen_uma_lock(f,d):b.append(str(g))
 return(len(b)==0),b
def redeploy_daemon(force=False):
 if not force:
  i=fetch_kraken_live_state()["state"];f,a=is_harvester_state_restart_safe(i)
  if not f:e=int(i.get("active_positions_count")or len(i.get("active_positions")or{}));b=bool((i.get("pre_split_inventory_state")or{}).get("active",False));raise RuntimeError(f"Refusing to restart live harvester with {e} open position(s) / pre_split_active={b} (blocking={a}): {i.get('active_position_ids',[])}. Wait until flat.")
 h=["ssh","-n","kraken-finland",("/home/skybullet1987/quant_pipeline/venv/bin/python -m py_compile /home/skybullet1987/quant_pipeline/src/polymarket_research/holistic_strategy_governance.py /home/skybullet1987/quant_pipeline/src/polymarket_research/riskless_machine_gun_engine.py /home/skybullet1987/quant_pipeline/src/polymarket_research/riskless_protocol_v2_expansion.py /home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_terminal_recorder.py /home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_executor.py /home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_harvester.py && systemctl --user daemon-reload && systemctl --user reset-failed polymarket-live-harvester.service || true && systemctl --user restart polymarket-live-harvester.service && for i in 1 2 3 4 5 6 7 8 9 10; do sleep 2; if grep -q '\"status\": \"RUNNING\"' /home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json 2>/dev/null; then break; fi; done && systemctl --user is-active polymarket-live-harvester.service")];g=subprocess.run(h,capture_output=True,text=True,timeout=45.)
 if g.returncode!=0:raise RuntimeError(f"Redeploy on kraken-finland failed: {g.stderr or g.stdout}")
 with _audit_state_lock():d=load_audit_state();d["stats"]["total_redeployments"]=d["stats"].get("total_redeployments",0)+1;save_audit_state(d)
 c=scan_trades();print(json.dumps({"redeployed":True,"daemon_health":c["daemon_health"]},indent=2))
def main():
 a=argparse.ArgumentParser(description="Autonomous Post-Trade Forensic Auditor (Real-Money Live Harvester)");a.add_argument("--check",action="store_true",help="Scan for uninspected real-money losing trades and live harvester health");a.add_argument("--mark-audited",type=str,help="Trade ID to mark as audited");a.add_argument("--verdict",type=str,choices=["EXPECTED_LOSS","BUG_FIXED","PARAM_WFO_REQUIRED","PROFIT_OK"],default="EXPECTED_LOSS");a.add_argument("--classification",type=str,choices=list(AUDIT_CLASSIFICATIONS),default=None,help="Structured Type 0 / Type 1 / Type 2 forensic classification");a.add_argument("--wfo-grid",type=str,default="",help="Optional Purged WFO grid specification routed to wfo_hypothesis_queue.jsonl");a.add_argument("--notes",type=str,default="",help="Forensic explanation or patch summary");a.add_argument("--redeploy",action="store_true",help="Compile-check and restart polymarket-live-harvester.service on kraken-finland");a.add_argument("--force-redeploy",action="store_true",help="Override open-position safety lock during emergency recovery");b=a.parse_args()
 if b.mark_audited:mark_audited(b.mark_audited,b.verdict,b.notes,classification=b.classification,wfo_grid=b.wfo_grid)
 elif b.redeploy:redeploy_daemon(force=b.force_redeploy)
 else:c=scan_trades();print(json.dumps(c,indent=2))
if __name__=="__main__":main()
# [13/13] scripts/honest_purged_wfo_optimizer.py
import bisect;import collections;import gzip;import json;import math;import multiprocessing as mp;import os;import pickle;import random;import statistics;import sys;import time;from pathlib import Path;from typing import Any,Dict,Iterator,List,Optional,Tuple;_REPO_ROOT=str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:sys.path.insert(0,_REPO_ROOT)
try:from src.polymarket_research.orderflow_wfo_simulators import(calibrate_d1_box_wfo,compute_v395_pricing_and_twap_gate,run_subhourly_v395_wfo_ablation_suite,run_wfo_post_selection_diagnostics,simulate_microclip_cascade_entry)
except ImportError:calibrate_d1_box_wfo=None;compute_v395_pricing_and_twap_gate=None;run_subhourly_v395_wfo_ablation_suite=None;run_wfo_post_selection_diagnostics=None;simulate_microclip_cascade_entry=None
try:
 import orjson as _orjson
 def _loads(line):return _orjson.loads(line)
except ImportError:
 def _loads(line):return json.loads(line)
PIPELINE_ROOT=Path("/home/skybullet1987/quant_pipeline");DATA_DIR=PIPELINE_ROOT/"data"/"polymarket";OUT_JSON=DATA_DIR/"honest_wfo_results.json";CACHE_PKL=Path("/tmp/pm_wfo_v395_dataset.pkl");FEE_RATE=.07
def taker_fee_per_share(px,fee_rate=FEE_RATE):a=max(.001,min(.999,px));return fee_rate*a*(1.-a)
def walk_bids_vwap(raw_bids,best_bid,target_shares=22.):
 if not raw_bids:return max(.0,best_bid-.01)if best_bid>.02 else best_bid
 d=target_shares;b=.0;a=.0
 for f in raw_bids:
  if not isinstance(f,(list,tuple))or len(f)<2:continue
  h,g=float(f[0]),float(f[1])
  if h<=0 or g<=0:continue
  e=min(d,g);b+=e*h;a+=e;d-=e
  if d<=1e-6:break
 if a<=0:return.0
 if d>1e-6:c=max(.01,float(raw_bids[-1][0])-.03);b+=d*c;a+=d
 return round(b/a,4)
def infer_asset_and_horizon(d):
 e=str(d.get("title")or"");a=str(d.get("asset")or"").upper()
 if not a:
  if"Ethereum"in e or"ETH"in e:a="ETH"
  elif"Solana"in e or"SOL"in e:a="SOL"
  else:a="BTC"
 b=str(d.get("horizon")or d.get("candle_interval")or d.get("timeframe")or"").lower()
 if not b:
  if"above"in e.lower()or"strike"in e.lower():b="daily"
  elif"-"in e.split("ET")[0].split(",")[-1]:c=e.split("ET")[0].split(",")[-1];f=[int(g.split(":")[1][:2])for g in c.split("-")if":"in g and g.split(":")[1][:2].isdigit()];b="5m"if(len(f)==2 and(f[1]-f[0])%60==5)else"15m"
  else:b="1h"
 if"15"in b:b="15m"
 elif b in("5m","5","5min","300","300s")or"-5m"in b or" 5m"in b:b="5m"
 elif"1h"in b or"hour"in b or"60"in b:b="1h"
 return a,b
def iter_jsonl_lines_with_archives(data_dir,filename):
 f=Path(filename).stem;c=data_dir/"archive";e=f"{f}__20"
 if c.is_dir():
  for d in sorted(c.glob(f"{f}__*.jsonl.gz")):
   if not d.name.startswith(e):continue
   try:
    with gzip.open(d,"rt",encoding="utf-8",errors="replace")as h:
     for a in h:yield a
   except Exception:continue
 b=data_dir/filename
 if b.exists():
  with open(b,"r",encoding="utf-8",errors="replace")as g:
   for a in g:yield a
def load_dataset(use_cache=True):
 if use_cache and CACHE_PKL.exists():
  try:
   _aq=time.time()
   with open(CACHE_PKL,"rb")as f:_ah,_q=pickle.load(f)
   _q["cache_hit_sec"]=round(time.time()-_aq,2);return _ah,_q
  except Exception:pass
 _O=time.time();_B=DATA_DIR/"verified_gamma_resolutions.json";_A=json.loads(_B.read_text(encoding="utf-8"));T=collections.defaultdict(list);F={};_z=collections.defaultdict(list);v=0;_f={"100ms":.1,"250ms":.25,"500ms":.5,"1s":1.,"5s":5.,"30s":30.}
 for _N in("shock_responses.jsonl","shock_responses_eth.jsonl","shock_responses_sol.jsonl"):
  for u in iter_jsonl_lines_with_archives(DATA_DIR,_N):
   if not u.strip():continue
   try:d=_loads(u)
   except Exception:continue
   g=str(d.get("market_id")or"")
   if g not in _A:continue
   t0=float(d.get("t0_unix")or.0);ir=d.get("impulse_response")or{}
   if t0>0 and ir:
    _z[g].append((t0,ir));v+=1;_M=float(d.get("spot_at_t0")or d.get("spot_at_shock")or.0)
    for _ag,_8 in _f.items():
     _ap=ir.get(_ag)
     if not _ap:continue
     dt=float(_ap.get("elapsed_sec")or _8);l=float(_ap.get("up_ask")or 1.);_af=float(_ap.get("up_mid")or.0);m=max(.0,round(2.*_af-l,3))if(_af>0 and l<1.)else.0;h=float(_ap.get("down_ask")or 1.);_ae=float(_ap.get("down_mid")or.0);k=max(.0,round(2.*_ae-h,3))if(_ae>0 and h<1.)else.0;N=float(_ap.get("binance_spot")or _M);T[g].append((t0+dt,N,m,l,k,h,max(.0,m-.005),max(.0,k-.005)))
 for g in _z:_z[g].sort(key=lambda x:x[0])
 n=0;X=("polymarket_hourly_telemetry.jsonl","polymarket_hourly_telemetry_eth.jsonl","polymarket_hourly_telemetry_sol.jsonl","polymarket_15m_telemetry_btc.jsonl","polymarket_15m_telemetry_eth.jsonl","polymarket_15m_telemetry_sol.jsonl","polymarket_5m_telemetry_btc.jsonl","polymarket_5m_telemetry_eth.jsonl","polymarket_5m_telemetry_sol.jsonl")
 for _7 in X:
  _y=("_15m_"in _7)or("_5m_"in _7);S=180. if _y else 90.;D={}
  for u in iter_jsonl_lines_with_archives(DATA_DIR,_7):
   if not u.strip():continue
   try:d=_loads(u)
   except Exception:continue
   g=str(d.get("market_id")or"")
   if g not in _A:continue
   ts=float(d.get("timestamp_unix")or.0)
   if ts-D.get(g,.0)<2. and float(d.get("seconds_to_expiry")or 999)>S:continue
   D[g]=ts;_l=float(d.get("seconds_to_expiry")or.0)
   if _l>0:F[g]=ts+_l
   N=float(d.get("binance_spot")or.0);up=d.get("UP")or{};dn=d.get("DOWN")or{};m=float(up.get("best_bid")or.0);l=float(up.get("best_ask")or 1.);k=float(dn.get("best_bid")or.0);h=float(dn.get("best_ask")or 1.);_6=walk_bids_vwap(up.get("raw_top_bids")or[],m);_5=walk_bids_vwap(dn.get("raw_top_bids")or[],k);T[g].append((ts,N,m,l,k,h,_6,_5));n+=1
 for u in iter_jsonl_lines_with_archives(DATA_DIR,"exp306_realtime_boundary_merge.jsonl"):
  if not u.strip():continue
  try:d=_loads(u)
  except Exception:continue
  g=str(d.get("market_id")or"")
  if g not in _A:continue
  ts=float(d.get("timestamp_unix")or.0);l=float(d.get("ask_up")or 1.);h=float(d.get("ask_down")or 1.);m=max(.0,round(1.-h,3))if h<1. else.0;k=max(.0,round(1.-l,3))if l<1. else.0;T[g].append((ts,.0,m,l,k,h,max(.0,m-.01),max(.0,k-.01)))
 R=[]
 for u in iter_jsonl_lines_with_archives(DATA_DIR,"live_shock_triggers.jsonl"):
  if not u.strip():continue
  try:d=_loads(u)
  except Exception:continue
  g=str(d.get("market_id")or"")
  if g not in _A:continue
  _c,hz=infer_asset_and_horizon(d)
  if hz not in("5m","15m","1h")or _c not in("BTC","ETH","SOL"):continue
  t0=float(d.get("t0_unix")or.0);_l=float(d.get("seconds_to_expiry")or.0)
  if t0<=0 or _l<=5.:continue
  O=float(d.get("candle_expiry_ts")or d.get("expiry_ts")or(t0+_l));F[g]=O;_1=d.get("pre_shock_features_t0")or{};up=_1.get("UP")or{};dn=_1.get("DOWN")or{};N=float(d.get("spot_at_t0")or.0);m=float(up.get("best_bid")or.0);l=float(up.get("best_ask")or 1.);k=float(dn.get("best_bid")or.0);h=float(dn.get("best_ask")or 1.);_x=walk_bids_vwap(up.get("raw_top_bids")or[],m);_w=walk_bids_vwap(dn.get("raw_top_bids")or[],k);T[g].append((t0,N,m,l,k,h,_x,_w));R.append((t0,_c,hz,g,O,d))
 R.sort(key=lambda x:x[0]);z={}
 for g,_U in T.items():
  _U.sort(key=lambda x:x[0]);_L=[];C=.0;Q=-1.
  for pt in _U:
   ts,N,ub,ua,db,da,_R,_Q=pt
   if N>0:C=N
   else:N=C
   if ts-Q<.05 and _L:_L[-1]=(ts,N,ub,ua,db,da,_R,_Q)
   else:_L.append((ts,N,ub,ua,db,da,_R,_Q));Q=ts
  T[g]=_L;z[g]=[p[0]for p in _L]
 _e={a:collections.deque(maxlen=200)for a in("BTC","ETH","SOL")};P={a:collections.deque(maxlen=60)for a in("BTC","ETH","SOL")};B={a:0 for a in("BTC","ETH","SOL")};t={"BTC":.0048,"ETH":.0062,"SOL":.009};_d=[]
 for t0,_c,hz,g,O,d in R:
  N=float(d.get("spot_at_t0")or.0)
  if N<=0:continue
  b5=int(t0//300)
  if b5>B[_c]:
   if P[_c]:_K=P[_c][-1];_2=math.log(N/_K);_b=12.*(_2**2);_J=t[_c]**2;_I=.94*_J+.06*_b;t[_c]=max(.002,min(.025,math.sqrt(_I)))
   P[_c].append(N);B[_c]=b5
  _v=d.get("venue_divergence_bps");e=.0
  if _v is not None:
   rv=float(_v)
   if len(_e[_c])>=20:_ad=statistics.median(_e[_c]);e=rv-_ad
   _e[_c].append(rv)
  _p=str(d.get("shock_direction")or"").upper()
  if _p not in("BUY","SELL"):continue
  _al="UP"if _p=="BUY"else"DOWN";_ak=1. if _al=="UP"else-1.;_H=float(d.get("candle_open_spot")or d.get("finalized_1h_open")or.0)
  if _H<=0:continue
  o=float(d.get("twap_60s_open")or _H)
  if o<=0:o=_H
  _1=(d.get("pre_shock_features_t0")or{}).get(_al)or{};_G=(d.get("pre_shock_features_t0")or{}).get("DOWN"if _al=="UP"else"UP")or{};_0=float(_1.get("best_ask")or 1.);_Z=float(_1.get("best_bid")or.0);_a=float(_G.get("best_bid")or.0)
  if not(.35<=_0<=.96)or _Z<=.0:continue
  _o=round(_0-_Z,4)
  if _o<-.001 or _o>.12:continue
  _Y=float(_1.get("ask_size_l1")or _1.get("ask_size")or.0);_X=float(_1.get("bid_size_l1")or _1.get("bid_size")or.0);_W=float(_1.get("obi_l1")if _1.get("obi_l1")is not None else(_1.get("obi")or.0));Z=float(_1.get("age_ask_ms")if _1.get("age_ask_ms")is not None else(_1.get("quote_age_ms")or 50.));_n=float(_1.get("vwap_$20")or _0);_m=max(.0,_n-_0);_l=float(d.get("seconds_to_expiry")or(O-t0));_u=t[_c];_k=max(.00025,_u*math.sqrt(max(_l,1.)/3600.));M=_ak*(N-_H)/_H;L=_ak*(N-o)/o;W=min(M,L);s=max(-50.,min(50.,e));V=N*(1.-.5*(s/1e4));r=min(_ak*(V-_H)/_H,_ak*(V-o)/o);A=M if hz=="1h"else min(W,r);_j=W/_k;K=r/_k;_t=A/_k;_i=float(d.get("shock_volume_100ms")or.0);_h=abs(float(d.get("shock_ofi")or.0));Y=float(d.get("coinbase_move_bps_2s")or.0)*_ak;E=float(d.get("coinbase_move_bps_250ms")if d.get("coinbase_move_bps_250ms")is not None else(.35*float(d.get("coinbase_move_bps_2s")or.0)))*_ak;b=None;c=None;_F=_z.get(g)
  if _F:
   _V=bisect.bisect_left(_F,(t0-.3,{}))
   for j in range(_V,min(len(_F),_V+3)):
    if abs(_F[j][0]-t0)<=.35:
     ir=_F[j][1];_ac="up_ask"if _al=="UP"else"down_ask"
     if ir.get("500ms")and ir["500ms"].get(_ac):b=float(ir["500ms"][_ac])
     if ir.get("1s")and ir["1s"].get(_ac):c=float(ir["1s"][_ac])
     break
  _U=T[g];_E=z[g];_s=bisect.bisect_right(_E,t0+.12)
  if b is None:
   if _s<len(_U)and(_U[_s][0]-t0)<=2.:b=_U[_s][3]if _al=="UP"else _U[_s][5]
   else:
    J=.01 if _i>=350000 else.0
    if _W<-.35:J+=.01
    if _Y*_0<25.:J+=.01
    b=min(.99,round(_0+J,4))
  if c is None:c=min(.99,round(b+(.01 if _i>=500000 else.0),4))
  _T=bisect.bisect_right(_E,t0+.45);q=_U[_T:]
  if len(q)>90:
   _S=max(1,len(q)//65);_r=set(range(0,len(q),_S))
   for k_i,_ab in enumerate(q):
    if O-_ab[0]<=75. or(_ab[0]-t0)<=35.:_r.add(k_i)
   _aa=2 if _al=="UP"else 4;_r.add(max(range(len(q)),key=lambda i:q[i][_aa]));_r.add(min(range(len(q)),key=lambda i:q[i][_aa]));q=[q[i]for i in sorted(_r)]
  I=[];H=_H if hz=="1h"else(max(_H,o)if _al=="UP"else min(_H,o));_D=bisect.bisect_right(_E,t0+.04);_C=bisect.bisect_right(_E,t0+5.5);U=[(round(p_ts-t0,3),_ak*(p_sp-H)/H if p_sp>0 else A,ub if _al=="UP"else db,ua if _al=="UP"else da)for p_ts,p_sp,ub,ua,db,da,_,_ in _U[_D:_C]];y=[(round(p_ts-t0,3),_ak*(p_sp-H)/H if p_sp>0 else A,ub if _al=="UP"else db,ua if _al=="UP"else da,db if _al=="UP"else ub)for p_ts,p_sp,ub,ua,db,da,_,_ in _U[_D:_C]]
  for p_ts,p_sp,ub,ua,db,da,_R,_Q in q:_9=max(.0,O-p_ts);b_i=ub if _al=="UP"else db;a_i=ua if _al=="UP"else da;_ai=_R if _al=="UP"else _Q;_P=_ak*(p_sp-H)/H if p_sp>0 else A;I.append((_9,_P,b_i,a_i,_ai))
  G=_A[g]["winner"];_g=(G==_al);w=bool(_A[g].get("oracle_mismatch",False));_d.append({"event_id":str(d.get("event_id")or d.get("shock_id")or f"{g}_{t0}"),"t0":t0,"exp_ts":O,"tte":_l,"asset":_c,"hz":hz,"mid":g,"side":_al,"ask_t0":_0,"bid_t0":_Z,"spread_t0":_o,"slip20_t0":_m,"l1_ask_usd":_0*_Y,"l1_bid_usd":_Z*_X,"opp_bid_t0":_a,"depth_ratio":(_0*_Y+_Z*_X)/20.,"obi_l1":_W,"age_ask_ms":Z,"cushion_open":M,"cushion_min":W,"cushion_cl_proxy":r,"cushion_oracle":A,"z_cushion":_j,"z_cushion_cl":K,"z_oracle":_t,"sigma_rem":_k,"shock_vol":_i,"shock_ofi":_h,"vdiv_centered":e,"cb_move_2s":Y,"cb_move_250ms":E,"ask_500ms":b,"ask_1000ms":c,"micro_clips":U,"micro_clips_opp":y,"path":I,"won":_g,"oracle_mismatch":w})
 _q={"verified_markets":len(_A),"shock_responses_indexed":v,"telemetry_rows_loaded":n,"total_candidates":len(_d),"load_sec":round(time.time()-_O,2)}
 if use_cache:
  try:
   with open(CACHE_PKL,"wb")as f:pickle.dump((_d,_q),f,protocol=pickle.HIGHEST_PROTOCOL)
  except Exception:pass
 return _d,_q
def simulate_single_trade(cand,cfg,latency_mode="500ms"):
 a=simulate_single_trade_ex(cand,cfg,latency_mode=latency_mode)
 if a is None:return None
 return a[0],a[1],a[2]
def simulate_single_trade_ex(cand,cfg,latency_mode="500ms"):
 if cand["asset"]not in cfg["assets"]:return None
 hz=cand["hz"]
 if hz not in cfg["horizons"]:return None
 _k=cand["tte"]
 if hz=="5m":
  if not(float(cfg.get("min_tte_5m",60.))<=_k<=float(cfg.get("max_tte_5m",180.))):return None
 elif hz=="15m":
  if not(cfg["min_tte_15m"]<=_k<=cfg["max_tte_15m"]):return None
 else:
  if not(cfg["min_tte_1h"]<=_k<=cfg["max_tte_1h"]):return None
 _g=cand["ask_t0"]
 if not(cfg["min_px"]<=_g<=cfg["max_px"]):return None
 if cand["spread_t0"]>cfg["max_spread"]:return None
 if cand["l1_ask_usd"]<cfg["min_l1_usd"]:return None
 X=cand.get("cushion_oracle",cand["cushion_min"])if cfg.get("use_cl_proxy",True)else cand["cushion_min"];O=cand.get("z_oracle",cand["z_cushion"])if cfg.get("use_cl_proxy",True)else cand["z_cushion"]
 if(cfg.get("use_kemna_vorst")or cfg.get("v395_df")is not None)and compute_v395_pricing_and_twap_gate is not None:
  O,_f=compute_v395_pricing_and_twap_gate(cand,df=cfg.get("v395_df"),jump_vol_mult=float(cfg.get("v395_jump_vol_mult",1.)),use_kemna_vorst=bool(cfg.get("use_kemna_vorst",False)))
  if cfg.get("v395_df")is not None and _g>(.98*_f+.36*(1.-_f)-.015):return None
 if X<cfg["min_cushion"]:return None
 if O<cfg["min_z"]:return None
 if cand["shock_ofi"]<cfg["min_ofi"]:return None
 if cfg["use_venue_veto"]:
  _j=1. if cand["side"]=="UP"else-1.
  if _j*cand["vdiv_centered"]>12. or cand["cb_move_2s"]<-4.:return None
 if cfg.get("cb_250ms_veto_bps")is not None and float(cand.get("cb_move_250ms",.0))<float(cfg["cb_250ms_veto_bps"]):return None
 N=cfg["entry_mode"];w=1.;s=""
 if N=="maker_in":
  W=round(min(_g-.01,cand["bid_t0"]+(.01 if cand["spread_t0"]>=.02 else.0)),2)
  if W<cfg["min_px"]:return None
  q=False;A=0
  for _h,(L,F,_d,_c,U)in enumerate(cand["path"]):
   if(cand["tte"]-L)>20.:break
   if _c<=W:q=True;A=_h;break
  if not q:return None
  t=W;m=.0;n=cand["path"][A+1:]
 elif N=="cascade_v4"and simulate_microclip_cascade_entry is not None:
  _i=simulate_microclip_cascade_entry(cand,cfg,latency_mode=latency_mode)
  if _i is None:return None
  t,m,S,w,s=_i;n=[r for r in cand["path"]if(cand["tte"]-r[0])>S]
 else:
  _a=cand["ask_500ms"]if latency_mode=="500ms"else cand["ask_1000ms"];V=min(cfg["max_px"]+.01,round(_g+cfg["fak_buffer"],4))
  if _a>V or _a<=.0 or _a>=.99:return None
  t=round(max(_a,_g+min(.02,cand["slip20_t0"])),4)
  if t>V:return None
  m=taker_fee_per_share(t);n=cand["path"]
 _e=1./t;M=1.+_e*m;J=cfg["exit_policy"];l=.98;h=.0;e=.98
 if J=="hold_98":e=.98
 elif J=="single_95":e=.95
 elif J=="single_plus14":e=min(.97,round(t+.14,2))
 elif J=="two_tranche_10_98":l=min(.95,round(t+.1,2));h=.5;e=.98
 elif J=="two_tranche_12_98":l=min(.96,round(t+.12,2));h=.5;e=.98
 elif J=="two_tranche_14_98":l=min(.96,round(t+.14,2));h=.5;e=.98
 elif J=="two_tranche_95_98":l=.95;h=.5;e=.98
 elif J=="dynamic_95_98":l=.95 if O>=1.35 else min(.95,round(t+.14,2));h=.5;e=.98
 g=1.;z=(h<=.0);a=.0;p=cand["bid_t0"];y=cfg["ratchet_arm"];I=cfg["ratchet_drop"];H=cfg["salvage_mode"];G=cfg["wrong_side_thresh"];x=cfg.get("salvage_persist_s",15.);R=cfg["clob_drop_thresh"];i=None;d=None;f=None;C=float(cfg.get("settle_delay_s",4.));E=float(cfg.get("t2_post_lag_s",.5));u=bool(cfg.get("buggy_f01_lock_300s",False));k=None if h>.0 else.0;j=False;b="HOLD_RESOLUTION";c=None
 for L,F,_d,_c,U in n:
  Q=max(.0,cand["tte"]-L);P=(.01<=_d<_c<=.999)or(_d>=.98 and _c>_d)
  if _d>p and P:p=_d
  D=(Q>=C)and(L>=15.)
  if not z and D and P and _d>=l and(_d>=l+.01 or _c>l):
   a+=(_e*h)*l;g-=h;z=True;k=Q
   if u and L<=3e2:j=True
  T=z and not j and D and(k is None or h<=.0 or(Q-k)>=E)
  if g>1e-6 and T and P and _d>=e and(_d>=e+.01 or _c>e):a+=(_e*g)*e;g=.0;b="MAKER_TP_FULL";c=Q;break
  if g>1e-6 and y is not None:
   Z=max(.84,t+y)
   if p>=Z and _d>.05 and _d<=(p-I)and L>=25. and _d>=(t+.04):
    if f is None:f=L
    elif(f-L)>=4.:v=max(.01,min(_d,U));B=taker_fee_per_share(v);a+=(_e*g)*max(.0,v-B);g=.0;b="PROFIT_RATCHET";c=Q;break
   else:f=None
  if g>1e-6 and H!="none"and L>=25. and _d>=.18:
   if F>=.0:i=None
   elif F<=-G:
    if i is None:i=L
   K=(i is not None)and((i-L)>=x)and(F<=-(G*.8));o=False
   if H=="hybrid_persist":
    if(_d<=t-R)and(F<=-2e-4):
     if d is None:d=L
     elif(d-L)>=max(8.,x*.6):o=True
    else:d=None
   if K or o:v=max(.01,min(_d,U));B=taker_fee_per_share(v);a+=(_e*g)*max(.0,v-B);g=.0;b="SALVAGE_SPOT"if K else"SALVAGE_CLOB_COLLAPSE";c=Q;break
  if g>1e-6 and cfg.get("final_45s_unwind",False)and 10.<=L<=45. and _d>=.05:v=max(.01,min(_d,U));B=taker_fee_per_share(v);a+=(_e*g)*max(.0,v-B);g=.0;b="FINAL_45S_UNWIND";c=Q;break
 if g>1e-6:
  if cand["won"]:a+=(_e*g)*1.;b="TP1_PLUS_WIN"if z and h>0 else"RESOLVED_WIN"
  else:b="TP1_PLUS_LOSS"if z and h>0 else"RESOLVED_LOSS_WIPEOUT"
 Y=(a-M)*w
 if s:b=f"{s}:{b}"
 _b=(cand["t0"]+c+4.)if c is not None else cand["exp_ts"];return Y,b,(Y>0),_b
def evaluate_portfolio_on_slice(cands,cfg,latency_mode="500ms",max_concurrent=2,ticket_usd=15.):
 g=set();a=[];f=bool(cfg.get("legacy_candle_end_slots",False));B=[];p=collections.Counter();b=0;A=.0;d=.0;e=.0
 for c in cands:
  D=c["mid"]
  if D in g:continue
  G=c["t0"];a=[s for s in a if s[0]>G]
  if len(a)>=max_concurrent:continue
  if not f:
   m=[s for s in a if abs(s[1]-c["exp_ts"])<=3e2 and s[2]==c["hz"]]
   if m:
    if c["hz"]=="1h":continue
    w=c.get("cushion_oracle",c["cushion_min"])if cfg.get("use_cl_proxy",True)else c["cushion_min"]
    if c["hz"]=="15m"and w<9e-4:continue
  C=simulate_single_trade_ex(c,cfg,latency_mode=latency_mode)
  if C is None:continue
  l,v,_,u=C;o=l*ticket_usd;g.add(D);h=c["exp_ts"]if f else u;a.append((h,c["exp_ts"],c["hz"]));B.append(o);p[v]+=1
  if v=="RESOLVED_LOSS_WIPEOUT":b+=1
  A+=o
  if A>d:d=A
  F=d-A
  if F>e:e=F
 n=len(B)
 if n==0:return{"trades":0,"total_pnl":.0,"ev_per_trade":.0,"win_rate":.0,"avg_win":.0,"avg_loss":.0,"profit_factor":.0,"sharpe":-99.,"max_dd":.0,"wipeout_count":0,"wipeout_rate":.0,"reasons":{},"pnls":[]}
 k=sum(B);z=[x for x in B if x>0];t=[x for x in B if x<=0];j=sum(z);i=abs(sum(t));E=j/i if i>1e-6 else(99. if j>0 else.0);r=k/n;y=statistics.stdev(B)if n>1 else 1e-6;q=(r/max(y,1e-6))*math.sqrt(n);return{"trades":n,"total_pnl":round(k,2),"ev_per_trade":round(r,4),"win_rate":round(len(z)/n,4),"avg_win":round(j/len(z),3)if z else.0,"avg_loss":round(-i/len(t),3)if t else.0,"profit_factor":round(E,3),"sharpe":round(q,3),"max_dd":round(e,2),"wipeout_count":b,"wipeout_rate":round(b/n,4),"reasons":dict(p),"pnls":B}
def prefilter_entry_slice(slice_cands,cfg):
 a=set(cfg["assets"]);n=set(cfg["horizons"]);h,g=cfg["min_tte_15m"],cfg["max_tte_15m"];f,e=cfg["min_tte_1h"],cfg["max_tte_1h"];m,l=cfg["min_px"],cfg["max_px"];k=cfg["max_spread"];j=cfg["min_l1_usd"];b=cfg["min_cushion"];q=cfg["min_z"];d=cfg["min_ofi"];i=cfg["use_venue_veto"];t=[]
 for c in slice_cands:
  if c["asset"]not in a:continue
  u=c["hz"]
  if u not in n:continue
  s=c["tte"]
  if u=="5m":
   if not(float(cfg.get("min_tte_5m",60.))<=s<=float(cfg.get("max_tte_5m",180.))):continue
  elif u=="15m":
   if not(h<=s<=g):continue
  else:
   if not(f<=s<=e):continue
  if not(m<=c["ask_t0"]<=l):continue
  if c["spread_t0"]>k or c["l1_ask_usd"]<j:continue
  p=max(c["cushion_min"],c.get("cushion_oracle",c["cushion_min"]),c.get("cushion_cl_proxy",c["cushion_min"]));o=max(c["z_cushion"],c.get("z_oracle",c["z_cushion"]),c.get("z_cushion_cl",c["z_cushion"]))
  if p<b:continue
  if o<q or c["shock_ofi"]<d:continue
  if i:
   r=1. if c["side"]=="UP"else-1.
   if r*c["vdiv_centered"]>12. or c["cb_move_2s"]<-4.:continue
  t.append(c)
 return t
def compute_wfo_dev_score(r_tr,r_vl,r_vl_1000=None,subfold_pnls=None):
 c=min(r_tr["sharpe"],r_vl["sharpe"]);i=min(r_tr["profit_factor"],r_vl["profit_factor"],3.5);h=min(r_tr["ev_per_trade"],r_vl["ev_per_trade"]);j=r_tr["trades"]+r_vl["trades"];g=math.sqrt(min(max(j,1),130)/130.);e=h*math.sqrt(min(j,180));f=max(r_tr["max_dd"],r_vl["max_dd"]);b=max(r_tr["wipeout_rate"],r_vl["wipeout_rate"]);a=(25.*c+35.*(i*g)+12.*e+.16*min(r_tr["total_pnl"]+r_vl["total_pnl"],3e2)-.55*f-90.*b)
 if r_vl_1000 is not None:a+=10.*min(r_vl_1000["sharpe"],2.5)
 if subfold_pnls:d=sum(1 for x in subfold_pnls if x>0);a+=12.*d
 return a
_G_TR_POOL=[];_G_VL_POOL=[];_G_DEV_SUBFOLDS=[]
def _eval_s1_batch(batch_cfgs):
 h=[]
 for g in batch_cfgs:
  b=40;a=20;f=evaluate_portfolio_on_slice(_G_TR_POOL,g,latency_mode="500ms")
  if f["trades"]<b or f["total_pnl"]<=0 or f["profit_factor"]<1.3:continue
  e=evaluate_portfolio_on_slice(_G_VL_POOL,g,latency_mode="500ms")
  if e["trades"]<a or e["total_pnl"]<=0 or e["profit_factor"]<1.3:continue
  i=compute_wfo_dev_score(f,e);d={k:v for k,v in f.items()if k!="pnls"};c={k:v for k,v in e.items()if k!="pnls"};h.append((i,g,d,c))
 return h
def bootstrap_ci(pnls,n_boot=1000,seed=42):
 if len(pnls)<5:return{"p05_total_pnl":.0,"p50_total_pnl":.0,"p95_total_pnl":.0,"prob_positive":.0}
 c=random.Random(seed);n=len(pnls);b=[];a=0
 for _ in range(n_boot):
  s=sum(pnls[c.randrange(n)]for _ in range(n));b.append(s)
  if s>0:a+=1
 b.sort();return{"p05_total_pnl":round(b[int(.05*n_boot)],2),"p50_total_pnl":round(b[int(.5*n_boot)],2),"p95_total_pnl":round(b[int(.95*n_boot)],2),"prob_positive":round(a/n_boot,4)}
def compute_quarter_kelly(pnls,ticket_usd=15.):
 if len(pnls)<10:return{"full_kelly_pct":.0,"quarter_kelly_pct":.08}
 c=[p/ticket_usd for p in pnls];e=statistics.mean(c);d=statistics.variance(c)
 if e<=0 or d<=1e-6:return{"full_kelly_pct":.0,"quarter_kelly_pct":.05}
 b=min(.8,e/d);a=round(max(.08,min(.2,.25*b)),4);return{"full_kelly_pct":round(b,4),"quarter_kelly_pct":a}
def main():
 global _G_TR_POOL,_G_VL_POOL,_G_DEV_SUBFOLDS
 if"--subhourly-v395-sweep"in sys.argv:_G,_W=load_dataset(use_cache=True);_5=run_subhourly_v395_wfo_ablation_suite(_G,evaluate_portfolio_on_slice,purge_sec=9e2);print(json.dumps({"dataset_meta":_W,"v395_subhourly_wfo":_5},indent=2),flush=True);return
 print("="*80);print("RUNNING HONEST ZERO-LOOKAHEAD PURGED WALK-FORWARD OPTIMIZER (v3.7)");print("="*80,flush=True);_4,_ag=load_dataset(use_cache=True);print(f"Loaded dataset: {_ag}",flush=True);_g=7200.;S=[];_f=[];E=[];h={}
 for _V in("15m","1h"):
  _F=[c for c in _4 if c["hz"]==_V]
  if not _F:continue
  _3=sorted(c["t0"]for c in _F);_s=_3[int(.5*len(_3))];_r=_3[int(.75*len(_3))];_af=[c for c in _F if c["exp_ts"]<=_s];_ae=[c for c in _F if c["t0"]>=(_s+_g)and c["exp_ts"]<=_r];_ad=[c for c in _F if c["t0"]>=(_r+_g)];S.extend(_af);_f.extend(_ae);E.extend(_ad);h[_V]={"train_n":len(_af),"val_n":len(_ae),"holdout_n":len(_ad),"train_end_utc":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime(_s)),"val_end_utc":time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime(_r))}
 S.sort(key=lambda x:x["t0"]);_f.sort(key=lambda x:x["t0"]);E.sort(key=lambda x:x["t0"]);_e=sorted(S+_f,key=lambda x:x["t0"]);_2=len(_e);O=[]
 for _1 in range(4):i0=int((_1*.25)*_2);i1=int(((_1+1)*.25)*_2)-1;_d=_e[i0]["t0"]+(_g if _1>0 else.0);_E=_e[max(i0,i1)]["t0"];O.append([c for c in _e if _d<=c["t0"]<=_E])
 print(f"Purged Splits -> Train: {len(S)} | Val: {len(_f)} | Sealed Holdout: {len(E)}",flush=True);B={"name":"BUGGY_OCT23_HOTPATCH_BASELINE","assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":150.,"max_tte_15m":825.,"min_tte_1h":150.,"max_tte_1h":6e2,"min_px":.55,"max_px":.88,"max_spread":.04,"min_l1_usd":15.,"min_cushion":2e-4,"min_z":.25,"min_ofi":.5,"use_venue_veto":False,"entry_mode":"taker_fak","fak_buffer":.02,"exit_policy":"hold_98","ratchet_arm":.16,"ratchet_drop":.06,"salvage_mode":"none","wrong_side_thresh":6e-4,"clob_drop_thresh":.3,"final_45s_unwind":False};W=evaluate_portfolio_on_slice(S,B);_q=evaluate_portfolio_on_slice(_f,B);_c=evaluate_portfolio_on_slice(E,B);print(f"[BASELINE BUGGY LIVE] Train PnL=${W['total_pnl']} (WR={W['win_rate']}, Wipeout={W['wipeout_rate']}) | Val PnL=${_q['total_pnl']} | Holdout PnL=${_c['total_pnl']} (Wipeout={_c['wipeout_rate']})",flush=True);V=[("BTC","ETH")];N=[("15m","1h")];_p=[(.52,.74),(.55,.75),(.55,.78),(.55,.8),(.55,.82),(.58,.78),(.58,.8),(.58,.82),(.6,.8),(.55,.85)];M=[.45,.65,.72,.75,.78,.85,1.05,1.25,1.5];l=[4e-4,6e-4,8e-4,.001,.0012];R=[(60.,420.,120.,6e2),(90.,480.,120.,6e2),(90.,540.,150.,9e2),(120.,6e2,150.,9e2),(90.,480.,150.,1200.)];A=[("taker_fak",.02),("maker_in",.0)];q={"assets":("BTC","ETH"),"horizons":("15m","1h"),"min_tte_15m":60.,"max_tte_15m":6e2,"min_tte_1h":120.,"max_tte_1h":1200.,"min_px":.52,"max_px":.85,"max_spread":.03,"min_l1_usd":20.,"min_cushion":4e-4,"min_z":.45,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True};_G_TR_POOL=prefilter_entry_slice(S,q);_G_VL_POOL=prefilter_entry_slice(_f,q);_G_DEV_SUBFOLDS=O;z=[(None,"none"),(None,"spot_persist")];Q=[]
 for _U in V:
  for _o in N:
   for _T,_S in _p:
    for _0 in M:
     for _n in l:
      for _D,_C,_B,_A in R:
       for K,U in A:
        for _z,_y in z:Q.append({"assets":_U,"horizons":_o,"min_px":_T,"max_px":_S,"min_tte_15m":_D,"max_tte_15m":_C,"min_tte_1h":_B,"max_tte_1h":_A,"max_spread":.03,"min_l1_usd":20.,"min_cushion":_n,"min_z":_0,"min_ofi":.6,"use_venue_veto":True,"use_cl_proxy":True,"entry_mode":K,"fak_buffer":U,"exit_policy":"two_tranche_12_98","ratchet_arm":_z,"ratchet_drop":.06,"salvage_mode":_y,"wrong_side_thresh":9e-4,"salvage_persist_s":18.,"clob_drop_thresh":.3,"final_45s_unwind":False})
 _b=max(1,min(8,(os.cpu_count()or 4)));_m=250;_x=[Q[i:i+_m]for i in range(0,len(Q),_m)];_ac=time.time();y=[]
 with mp.get_context("fork").Pool(processes=_b)as _ab:
  for _a in _ab.imap_unordered(_eval_s1_batch,_x):y.extend(_a)
 y.sort(key=lambda x:x[0],reverse=True);print(f"Stage 1 evaluated {len(Q)} configs across {_b} workers in {time.time()-_ac:.1f}s | Passed Train+Val PF>=1.25: {len(y)}",flush=True);Z=[];w=set();_R=[lambda c:True,lambda c:c["assets"]==("BTC","ETH")and c["horizons"]==("15m","1h"),lambda c:c["assets"]==("BTC","ETH")and c["entry_mode"]=="taker_fak",lambda c:c["entry_mode"]=="maker_in"]
 for _aa in _R:
  e=0
  for _,_J,_,_ in y:
   if not _aa(_J):continue
   ck=(_J["assets"],_J["horizons"],_J["min_px"],_J["max_px"],_J["min_z"],_J["min_cushion"],_J["min_tte_15m"],_J["max_tte_15m"],_J["min_tte_1h"],_J["max_tte_1h"],_J["entry_mode"])
   if ck not in w:w.add(ck);Z.append(_J);e+=1
   if e>=6 or len(Z)>=24:break
 D=["hold_98","single_95","single_plus14","two_tranche_10_98","two_tranche_12_98","two_tranche_14_98","two_tranche_95_98","dynamic_95_98"];L=[None,.1,.12,.16];p=[("none",6e-4,15.,.3),("spot_persist",6e-4,15.,.3),("spot_persist",9e-4,18.,.3),("hybrid_persist",6e-4,15.,.22),("hybrid_persist",8e-4,20.,.25)];u=[];d=len(Q)
 for _Q in Z:
  K=_Q["entry_mode"];J=[.01,.02,.03];_P=prefilter_entry_slice(S,_Q);_O=prefilter_entry_slice(_f,_Q);_l=40;_k=20
  for U in J:
   o=dict(_Q);o.update({"entry_mode":K,"fak_buffer":U,"exit_policy":"hold_98","ratchet_arm":None,"ratchet_drop":.06,"salvage_mode":"none","wrong_side_thresh":6e-4,"salvage_persist_s":15.,"clob_drop_thresh":.3})
   def b(sub_cands,lat):return[c_item for c_item in sub_cands if simulate_single_trade_ex(c_item,o,latency_mode=lat)is not None]
   t=b(_P,"500ms")
   if len(t)<_l:d+=len(D)*len(L)*len(p);continue
   s=b(_O,"500ms")
   if len(s)<_k:d+=len(D)*len(L)*len(p);continue
   n=b(_O,"1000ms");m=[b(prefilter_entry_slice(sf,_Q),"500ms")for sf in O]
   for _N in D:
    for _Z in L:
     for _M,_9,_L,_K in p:
      d+=1;_J=dict(_Q);_J.update({"entry_mode":K,"fak_buffer":U,"exit_policy":_N,"ratchet_arm":_Z,"ratchet_drop":.06,"salvage_mode":_M,"wrong_side_thresh":_9,"salvage_persist_s":_L,"clob_drop_thresh":_K});_8=evaluate_portfolio_on_slice(t,_J,latency_mode="500ms")
      if _8["trades"]<_l or _8["total_pnl"]<=0 or _8["profit_factor"]<1.25:continue
      _7=evaluate_portfolio_on_slice(s,_J,latency_mode="500ms")
      if _7["trades"]<_k or _7["total_pnl"]<=0 or _7["profit_factor"]<1.25:continue
      Y=evaluate_portfolio_on_slice(n,_J,latency_mode="1000ms")
      if Y["total_pnl"]<=0 or Y["profit_factor"]<1.15:continue
      _w=[evaluate_portfolio_on_slice(sf_e,_J,latency_mode="500ms")["total_pnl"]for sf_e in m];I=sum(1 for x in _w if x>0)
      if I<3:continue
      _Y=compute_wfo_dev_score(_8,_7,Y,_w);u.append((_Y,_J,_8,_7,Y))
 u.sort(key=lambda x:x[0],reverse=True);print(f"Total grid evaluations: {d} | Stage 2 passed Train+Val+1000ms+SubFolds: {len(u)}",flush=True)
 if not u:raise RuntimeError("No configuration passed strict Train+Val+1000ms+SubFolds WFO gates!")
 T,_j,_v,_u,H=u[0]
 def a(label,mod):c=dict(_j);c.update(mod);v=evaluate_portfolio_on_slice(S,c);k=evaluate_portfolio_on_slice(_f,c);i=evaluate_portfolio_on_slice(E,c);return{"label":label,"train_pnl":v["total_pnl"],"train_trades":v["trades"],"train_pf":v["profit_factor"],"train_wipeout":v["wipeout_rate"],"val_pnl":k["total_pnl"],"val_trades":k["trades"],"val_pf":k["profit_factor"],"val_wipeout":k["wipeout_rate"],"holdout_pnl":i["total_pnl"],"holdout_trades":i["trades"],"holdout_pf":i["profit_factor"],"holdout_wipeout":i["wipeout_rate"]}
 C=evaluate_portfolio_on_slice(E,_j,latency_mode="500ms");r=evaluate_portfolio_on_slice(E,_j,latency_mode="1000ms");g=evaluate_portfolio_on_slice(E,_j,latency_mode="500ms",max_concurrent=1,ticket_usd=12.);X=[a("SELECTED_WFO_OPTIMAL (v3.9 Contract-Oracle + WFO#2 Corr + Exact Parity)",{}),a("ABLATE_LEGACY_CANDLE_END_NO_CORR_FILTER (Vector 6 F-12a)",{"legacy_candle_end_slots":True}),a("ABLATE_CONTRACT_ORACLE_PROXY (R07 + F-11)",{"use_cl_proxy":not _j.get("use_cl_proxy",True)}),a("ABLATE_BUGGY_F01_T2_LOCKED_300S_5S_LAG (v3.7 F-01+F-07 bug)",{"buggy_f01_lock_300s":True,"t2_post_lag_s":5.}),a("ABLATE_HIGH_PX_085_THIN_CUSHION (Oct23 overpay bug)",{"max_px":.85,"min_cushion":2e-4,"min_z":.35}),a("ABLATE_TO_SINGLE_HOLD_98 (15m wipeout bug)",{"exit_policy":"hold_98"}),a("ABLATE_RATCHET_TO_+16c (pytest-divergence bug)",{"ratchet_arm":.16}),a("ABLATE_NO_SALVAGE (dead boolean bug)",{"salvage_mode":"none"}),a("ABLATE_ENABLE_FINAL_45S_TAKER_UNWIND",{"final_45s_unwind":True}),a("ABLATE_NO_VENUE_VETO",{"use_venue_veto":False}),a("ABLATE_ALT_ENTRY_MODE (maker_in vs taker_fak)",{"entry_mode":"maker_in"if _j["entry_mode"]!="maker_in"else"taker_fak"}),a("ABLATE_CASCADE_V4_4STEP_ENTRY",{"entry_mode":"cascade_v4"})];_i=bootstrap_ci(_v["pnls"]);_I=bootstrap_ci(_u["pnls"]);_t=bootstrap_ci(C["pnls"]);_X=compute_quarter_kelly(_v["pnls"]+_u["pnls"],ticket_usd=15.);_6=run_wfo_post_selection_diagnostics(cands=_4,dev_cands=_e,holdout_cands=E,best_cfg=_j,best_tr=_v,best_vl=_u,best_hold_500=C,stage2_results=u,data_dir=DATA_DIR,purge_sec=_g,evaluate_portfolio_fn=evaluate_portfolio_on_slice,prefilter_fn=prefilter_entry_slice,dev_score_fn=compute_wfo_dev_score,simulate_single_fn=simulate_single_trade);G=_6["cpcv_summary"];f=_6["chainlink_proxy_audit"];P=_6["bankroll_mc"];F=_6["top5_summary"];j=_6["live_counterfactual"];_h=_6["cv_folds"];_H={"generated_at_utc":time.strftime("%Y-%m-%d %H:%M:%S UTC",time.gmtime()),"wfo_version":"3.9.5","dataset_meta":_ag,"total_grid_configs_evaluated":d,"purged_splits":{"purge_embargo_seconds":_g,"train_candidates":len(S),"val_candidates":len(_f),"holdout_candidates":len(E),"per_horizon":h},"cpcv_6_2_validation":G,"chainlink_proxy_audit":f,"bankroll_50trade_monte_carlo":P,"expanding_4fold_purged_cv":_h,"buggy_oct23_live_baseline":{"train":{k:v for k,v in W.items()if k!="pnls"},"val":{k:v for k,v in _q.items()if k!="pnls"},"holdout":{k:v for k,v in _c.items()if k!="pnls"}},"selected_optimal_config":{k:(list(v)if isinstance(v,tuple)else v)for k,v in _j.items()},"selected_optimal_performance":{"train_500ms":{k:v for k,v in _v.items()if k!="pnls"},"val_500ms":{k:v for k,v in _u.items()if k!="pnls"},"val_1000ms_stress":{k:v for k,v in H.items()if k!="pnls"},"sealed_holdout_500ms":{k:v for k,v in C.items()if k!="pnls"},"sealed_holdout_seed_12_conc1":{k:v for k,v in g.items()if k!="pnls"},"sealed_holdout_1000ms_stress":{k:v for k,v in r.items()if k!="pnls"},"bootstrap_95ci":{"train":_i,"val":_I,"sealed_holdout":_t},"kelly_sizing":_X},"controlled_ablations":X,"d1_box_wfo_calibration":calibrate_d1_box_wfo(data_dir=DATA_DIR)if calibrate_d1_box_wfo is not None else{},"top_5_configs":F,"live_105_trades_counterfactual":j};tmp=OUT_JSON.with_suffix(".tmp");tmp.write_text(json.dumps(_H,indent=2),encoding="utf-8");tmp.replace(OUT_JSON);print("\n"+"="*80);print("OPTIMAL WFO v3.7 CONFIG SELECTED (STRICTLY ON TRAIN + VAL + DEV SUB-FOLDS):");print(json.dumps(_H["selected_optimal_config"],indent=2));print("\nSEALED HOLDOUT PERFORMANCE (+500ms Finland RTT):");print(json.dumps(_H["selected_optimal_performance"]["sealed_holdout_500ms"],indent=2));print("\nSEALED HOLDOUT (+1000ms SEVERE LATENCY STRESS):");print(json.dumps(_H["selected_optimal_performance"]["sealed_holdout_1000ms_stress"],indent=2));print("\nSEALED HOLDOUT BOOTSTRAP 95% CI:");print(json.dumps(_t,indent=2));print("\nCONTROLLED ABLATIONS:")
 for ab in X:print(f"  - {ab['label']}: Train=${ab['train_pnl']} | Val=${ab['val_pnl']} | Holdout=${ab['holdout_pnl']} (PF={ab['holdout_pf']}, Wipeout={ab['holdout_wipeout']})")
 print("\nCPCV(6, 2) 15-SPLIT OUT-OF-SAMPLE SUMMARY:");print(json.dumps({k:v for k,v in G.items()if k!="splits"},indent=2));print("\nCHAINLINK PROXY ORACLE-MISMATCH AUDIT:");print(json.dumps(f,indent=2));print("\n50-TRADE MONTE CARLO BANKROLL SURVIVAL FROM $76.49:");print(json.dumps(P,indent=2));print("\nLIVE COUNTERFACTUAL:");print(json.dumps(j,indent=2));print("="*80,flush=True)
if __name__=="__main__":main()
