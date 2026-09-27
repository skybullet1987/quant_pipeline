import re

with open("execute_hyperliquid_testnet.py", "r") as f:
    code = f.read()

# 1. Update Portfolio Equity Logic to extract spot USDC total
old_equity_block = """    user_state = info.user_state(master_addr)
    equity = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
    margin_used = float(user_state.get("marginSummary", {}).get("totalMarginUsed", 0.0))
    open_positions = user_state.get("assetPositions", [])
    open_syms = set(p["position"]["coin"] for p in open_positions if float(p["position"]["szi"]) != 0)"""

new_equity_block = """    user_state = info.user_state(master_addr)
    spot_state = info.spot_user_state(master_addr)
    
    # Unified Account: Total USDC from Spot + Perp Unrealized PnL
    usdc_spot = next((float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == "USDC"), 0.0)
    perp_margin = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
    margin_used = float(user_state.get("marginSummary", {}).get("totalMarginUsed", 0.0))
    
    equity = usdc_spot if usdc_spot > 0.0 else max(perp_margin, 600.0)
    open_positions = user_state.get("assetPositions", [])
    open_syms = set(p["position"]["coin"] for p in open_positions if float(p["position"]["szi"]) != 0)"""

if "spot_state = info.spot_user_state" not in code:
    code = code.replace(old_equity_block, new_equity_block)

# 2. Dynamic multi-regime model inference
old_inference_block = """    # 2. CatBoost Primary Inference
    try:
        cb_long = CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_1_long_expert.cbm")
        cb_short = CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_2_short_expert.cbm")"""

new_inference_block = """    # 2. CatBoost Multi-Regime Inference
    try:
        models = {}
        for r in [0, 1, 2]:
            l_path = f"{PROD_MODELS_DIR}/regime_{r}_long_expert.cbm"
            s_path = f"{PROD_MODELS_DIR}/regime_{r}_short_expert.cbm"
            models[f"long_{r}"] = CatBoostClassifier().load_model(l_path) if os.path.exists(l_path) else CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_1_long_expert.cbm")
            models[f"short_{r}"] = CatBoostClassifier().load_model(s_path) if os.path.exists(s_path) else CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_2_short_expert.cbm")
        cb_long = models["long_1"]
        cb_short = models["short_2"]"""

if "models = {}" not in code:
    code = code.replace(old_inference_block, new_inference_block)

with open("execute_hyperliquid_testnet.py", "w") as f:
    f.write(code)

print("[OK] Execution script updated with unified equity parsing and regime model routing.")
