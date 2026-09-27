from pathlib import Path

daemon_path = Path.home() / "quant_pipeline" / "src" / "execution" / "hyperliquid_tail_daemon.py"
code = daemon_path.read_text()

# 1. Swap import to HRP optimizer
code = code.replace(
    "from src.optimization.portfolio_optimizer import optimize_portfolio_weights",
    "from src.optimization.hrp_optimizer import optimize_hrp_weights"
)

# 2. Update optimizer call signature
old_opt = """weights = optimize_portfolio_weights(
            symbols=common_symbols,
            alpha_scores=alpha_scores,
            returns_matrix=ret_matrix,
            betas_btc=betas,
            target_gross_leverage=1.5
        )"""

new_opt = """# Dynamic gross leverage scaled by Yang-Zhang volatility
        market_yz = float(latest_df.select(pl.mean('vol_yang_zhang')).to_series()[0])
        dyn_leverage = float(np.clip(1.5 * (0.035 / (market_yz + 1e-8)), 0.6, 2.2))
        
        weights = optimize_hrp_weights(
            symbols=common_symbols,
            alpha_scores=alpha_scores,
            returns_matrix=ret_matrix,
            target_gross_leverage=dyn_leverage
        )"""

if old_opt in code:
    code = code.replace(old_opt, new_opt)

# 3. Add Parabolic Take-Profit Trimming (+3.5 ATR)
tp_logic = """
    def check_parabolic_take_profits(self):
        \"\"\"Harvests 33% of position notional on explosive +3.5 ATR runners.\"\"\"
        user_state = self.info.user_state(self.address)
        for p in user_state.get("assetPositions", []):
            pos = p["position"]
            sym = pos["coin"]
            sz = float(pos["szi"])
            if abs(sz) == 0:
                continue
                
            entry_px = float(pos["entryPx"]) if pos.get("entryPx") else 0.0
            unrealized_pnl = float(pos["unrealizedPnl"])
            pos_val = float(pos["positionValue"])
            
            if entry_px <= 0 or pos_val <= 0:
                continue
                
            pnl_pct = unrealized_pnl / (pos_val / float(pos["leverage"]["value"]))
            atr = self.metadata.get("latest_atr", {}).get(sym, entry_px * 0.04)
            atr_multiple = (abs(unrealized_pnl) / pos_val) / (atr / entry_px + 1e-8)
            
            if pnl_pct > 0 and atr_multiple >= 3.5:
                trim_sz = round(abs(sz) * 0.33, self.meta_universe.get(sym, {}).get("szDecimals", 2))
                if trim_sz > 0:
                    logger.info(f"PARABOLIC GAIN on {sym} (+{atr_multiple:.1f}x ATR). Trimming 33% ({trim_sz} units) via ALO.")
                    self.execute_maker_order(sym, trim_sz, is_buy=(sz < 0), sz_decimals=self.meta_universe[sym]["szDecimals"], reduce_only=True)
"""

if "def check_parabolic_take_profits" not in code:
    code = code.replace("def rebalance(self):", tp_logic + "\n    def rebalance(self):")
    
# Add periodic 15-minute parabolic check to daemon loop
old_run = """        while True:
            try:
                self.rebalance()
            except Exception as e:
                logger.error(f"Rebalance error: {e}", exc_info=True)
            time.sleep(72 * 3600)"""

new_run = """        last_rebalance = 0
        while True:
            try:
                now = time.time()
                if now - last_rebalance >= 72 * 3600:
                    self.rebalance()
                    last_rebalance = now
                else:
                    self.check_parabolic_take_profits()
            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
            time.sleep(900)  # Check intraday runners every 15 mins"""

if old_run in code:
    code = code.replace(old_run, new_run)

daemon_path.write_text(code)
print("Successfully patched daemon with HRP optimization and Parabolic Take-Profit Trimming.")
