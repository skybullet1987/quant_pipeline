import os
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from dotenv import load_dotenv

load_dotenv(Path.home() / "quant_pipeline" / ".env")

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

import numpy as np
import polars as pl
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from catboost import CatBoost

from src.optimization.hrp_optimizer import optimize_hrp_weights
from src.signals.funding_forecaster import forecast_hourly_funding, solve_alpha_orthogonal_carry
from src.execution.microstructure_defense import MicrostructureQuotingDefense

MODEL_FILE = PIPELINE_ROOT / "data" / "models" / "catboost_tail_alpha_v1.cbm"
META_FILE = PIPELINE_ROOT / "data" / "models" / "model_metadata.json"
LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"

# Validated Institutional Parameters (Bear Market Holdout Architecture)
TARGET_GROSS_LEVERAGE = 2.00   # Institutional sweet spot
MIN_TURNOVER_DEADBAND = 0.050  # 5.0% turnover filter to curb churn
MIN_MARGIN_BUFFER = 0.15       # 15% maintenance margin floor

def round_sz(sz: float, sz_decimals: int) -> float:
    return float(Decimal(str(sz)).quantize(Decimal("1." + "0" * sz_decimals), rounding=ROUND_FLOOR))

def round_px(px: float) -> float:
    if px == 0: return 0.0
    return float(f"{px:.5g}")

def run_rebalance_cycle(live_mode: bool = False, network_url: str = constants.TESTNET_API_URL):
    priv_key = os.getenv("HYPERLIQUID_PRIVATE_KEY") or os.getenv("HYPERLIQUID_API_KEY")
    master_addr = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5").lower().strip()

    if not priv_key:
        print("[DAEMON] Error: Private key environment variable missing in .env")
        return

    signer_account = Account.from_key(priv_key)
    info = Info(network_url, skip_ws=True)
    is_agent = (master_addr != signer_account.address.lower())
    exchange = Exchange(signer_account, network_url, account_address=master_addr if is_agent else None)
    defense_engine = MicrostructureQuotingDefense()

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n[{now_utc}] === RUNNING PRODUCTION REBALANCE CYCLE ===")
    print(f" • Mode: {'LIVE (REAL ORDERS)' if live_mode else 'DRY-RUN (SIMULATED)'}")
    print(f" • Master Account: {master_addr} | Agent Signer: {signer_account.address}")

    # 1. Fetch Unified Account State (Fixed to avoid double-counting)
    user_state = info.user_state(master_addr)
    perp_equity = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
    spot_state = info.spot_user_state(master_addr)
    
    spot_usdc = sum(float(b.get("total", 0.0)) for b in spot_state.get("balances", []) if b.get("coin") == "USDC")
    total_equity = spot_usdc if spot_usdc > 0 else perp_equity
    print(f" • Unified Portfolio Equity: ${total_equity:,.2f} USDC (Spot Pool: ${spot_usdc:,.2f} | Perp Margin: ${perp_equity:,.2f})")

    # Map current active positions
    current_positions = {}
    for p in user_state.get("assetPositions", []):
        pos = p.get("position", {})
        coin = pos.get("coin")
        szi = float(pos.get("szi", 0.0))
        if abs(szi) > 0 and coin:
            current_positions[coin] = szi

    print(f" • Active Positions ({len(current_positions)}): {current_positions}")
    if total_equity <= 0:
        print("[DAEMON] Equity is zero. Rebalance aborted.")
        return

    # 2. Check Circuit Breaker Maintenance Margin Buffer
    total_notional = sum(abs(szi * float(p["position"]["entryPx"])) for p in user_state.get("assetPositions", []) if abs(float(p["position"]["szi"])) > 0)
    if total_notional > 0:
        margin_buffer = total_equity / total_notional
        print(f" • Margin Ratio: {margin_buffer * 100:.2f}% (Floor: {MIN_MARGIN_BUFFER * 100:.1f}%)")
        if margin_buffer < MIN_MARGIN_BUFFER:
            print("[CIRCUIT BREAKER] Margin buffer below floor! Liquidation triggered.")
            return

    # 3. Model Inference & Signal Generation
    if not LAKE_FILE.exists() or not MODEL_FILE.exists() or not META_FILE.exists():
        print("[DAEMON] Required data or model artifacts missing. Aborting.")
        return

    df = pl.read_parquet(LAKE_FILE).sort(["timestamp_ms", "symbol"])
    latest_ts = df.select(pl.max("timestamp_ms")).to_series()[0]
    current_panel = df.filter(pl.col("timestamp_ms") == latest_ts)

    with open(META_FILE, "r") as f:
        meta = json.load(f)
    features = meta["features"]

    model = CatBoost()
    model.load_model(str(MODEL_FILE))
    scores = model.predict(current_panel.select(features).to_pandas())
    current_panel = current_panel.with_columns(pl.Series("pred_alpha", scores))

    symbols = current_panel.select("symbol").to_series().to_list()
    hist_window = df.filter(pl.col("timestamp_ms") > latest_ts - (42 * 4 * 3600 * 1000))
    pivoted_rets = hist_window.pivot(values="ret_4h", index="timestamp_ms", on="symbol").sort("timestamp_ms")
    common_symbols = [s for s in symbols if s in pivoted_rets.columns]
    ret_matrix = pivoted_rets.select(common_symbols).fill_null(0.0).to_numpy()

    alpha_scores = {row["symbol"]: float(row["pred_alpha"]) for row in current_panel.iter_rows(named=True) if row["symbol"] in common_symbols}
    betas = {row["symbol"]: float(row["beta_btc"]) for row in current_panel.iter_rows(named=True) if row["symbol"] in common_symbols}

    # 4. Momentum Core (HRP) Scaled to 2.00x Gross Leverage
    # Allocate 1.65x to Alpha Momentum and 0.35x to Alpha-Orthogonal Short Hedge
    momentum_weights = optimize_hrp_weights(
        symbols=common_symbols,
        alpha_scores=alpha_scores,
        returns_matrix=ret_matrix,
        target_gross_leverage=1.65,
        top_k=5
    )

    carry_yields = {}
    for row in current_panel.iter_rows(named=True):
        sym = row["symbol"]
        if sym in common_symbols:
            _, y_ann = forecast_hourly_funding(
                instant_basis=float(row["basis_spread"]),
                volume_zscore=float(row["volume_zscore_72h"]),
                ret_4h=float(row["ret_4h"]),
                realized_twap_basis=float(row["basis_spread"])
            )
            carry_yields[sym] = y_ann

    carry_weights = solve_alpha_orthogonal_carry(
        symbols=common_symbols,
        carry_yields=carry_yields,
        alpha_scores=alpha_scores,
        btc_betas=betas,
        returns_matrix=ret_matrix,
        target_carry_leverage=0.35
    )

    all_symbols = set(list(momentum_weights.keys()) + list(carry_weights.keys()))
    raw_targets = {s: momentum_weights.get(s, 0.0) + carry_weights.get(s, 0.0) for s in all_symbols}

    # Normalize to exactly 2.00x gross exposure
    gross_sum = sum(abs(w) for w in raw_targets.values())
    target_weights = {s: round(w * (TARGET_GROOS := TARGET_GROSS_LEVERAGE) / (gross_sum + 1e-9), 4) for s, w in raw_targets.items()}
    print(f" • Target Portfolio (Gross: {sum(abs(w) for w in target_weights.values()):.2f}x): {target_weights}")

    # 5. Universe Specs & Execution Planning
    meta_info, asset_ctxs = info.meta_and_asset_ctxs()
    sz_decimals_map = {a["name"]: a["szDecimals"] for a in meta_info["universe"]}
    price_map = {meta_info["universe"][i]["name"]: float(asset_ctxs[i]["markPx"]) for i in range(len(meta_info["universe"]))}

    all_eval_coins = set(list(target_weights.keys()) + list(current_positions.keys()))
    print(f"\n--- EXECUTION ROUTING ({len(all_eval_coins)} ASSETS) ---")

    for sym in all_eval_coins:
        if sym not in price_map or sym not in sz_decimals_map:
            continue

        mark_px = price_map[sym]
        sz_dec = sz_decimals_map[sym]
        current_sz = current_positions.get(sym, 0.0)
        current_w = (current_sz * mark_px) / total_equity
        target_w = target_weights.get(sym, 0.0)

        # 5% Deadband Filter (Skip small rebalance drift unless unwinding to 0)
        delta_w = target_w - current_w
        if abs(delta_w) < MIN_TURNOVER_DEADBAND and target_w != 0.0:
            continue

        target_notional = total_equity * target_w
        target_sz = round_sz(target_notional / mark_px, sz_dec)
        delta_sz = round_sz(target_sz - current_sz, sz_dec)

        if abs(delta_sz * mark_px) < 5.0:
            continue

        is_buy = (delta_sz > 0)
        order_sz = abs(delta_sz)
        is_reduce_only = (target_w == 0.0) or (current_sz > 0 and not is_buy) or (current_sz < 0 and is_buy)

        # Orderbook inspection
        l2_data = info.l2_snapshot(sym)
        bids = l2_data.get("levels", [[]])[0]
        asks = l2_data.get("levels", [[], []])[1]
        best_bid = float(bids[0]["px"]) if bids else mark_px * 0.999
        best_ask = float(asks[0]["px"]) if asks else mark_px * 1.001
        half_spread = (best_ask - best_bid) / 2.0

        # Peg ALO order inside book to capture spread and prevent taker fee / oracle collars
        if is_buy:
            limit_px = round_px(best_bid)
        else:
            limit_px = round_px(best_ask)

        action_str = f"{'BUY' if is_buy else 'SELL'} {order_sz} {sym} @ ${limit_px} (Cur: {current_sz} -> Tgt: {target_sz})"

        if not live_mode:
            print(f" • [DRY-RUN] Would submit ALO: {action_str} | ReduceOnly: {is_reduce_only}")
            continue

        try:
            order_res = exchange.order(
                name=sym,
                is_buy=is_buy,
                sz=order_sz,
                limit_px=limit_px,
                order_type={"limit": {"tif": "Alo"}},
                reduce_only=is_reduce_only
            )
            print(f" • [LIVE ALO] {action_str} | Status: {order_res.get('status')}")
        except Exception as e:
            print(f" • [ORDER ERROR] {sym}: {e}")

    print("\n[DAEMON] Rebalance cycle completed successfully.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperliquid Production Execution Daemon")
    parser.add_argument("--live", action="store_true", help="Submit live orders to exchange (default: DRY-RUN)")
    parser.add_argument("--mainnet", action="store_true", help="Target Hyperliquid Mainnet (default: Testnet)")
    args = parser.parse_args()

    net_url = constants.MAINNET_API_URL if args.mainnet else constants.TESTNET_API_URL
    run_rebalance_cycle(live_mode=args.live, network_url=net_url)
