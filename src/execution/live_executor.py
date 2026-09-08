import os
import sys
import time
import json
import math
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from dotenv import load_dotenv

import numpy as np
import polars as pl
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

load_dotenv(PIPELINE_ROOT / ".env")

from src.execution.microstructure_defense import MicrostructureQuotingDefense
from src.config import STRATEGY_CONFIG

LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
STATE_FILE = PIPELINE_ROOT / "data" / "execution" / "reconciliation_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

DRY_RUN = STRATEGY_CONFIG.execution.dry_run


class DynamicHyperliquidExecutor:
    def __init__(self, network_url: str = constants.TESTNET_API_URL):
        self.network_url = network_url
        priv_key = os.getenv("HYPERLIQUID_PRIVATE_KEY") or os.getenv("HYPERLIQUID_API_KEY")
        if not priv_key:
            raise ValueError("HYPERLIQUID_PRIVATE_KEY not configured in environment.")

        self.account = Account.from_key(priv_key)
        self.wallet = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", self.account.address).lower().strip()
        self.info = Info(self.network_url, skip_ws=True)
        is_agent = (self.wallet != self.account.address.lower())
        self.exchange = Exchange(self.account, self.network_url, account_address=self.wallet if is_agent else None)
        self.defense_engine = MicrostructureQuotingDefense()

    @staticmethod
    def round_sz(sz: float, sz_decimals: int) -> float:
        return float(Decimal(str(sz)).quantize(Decimal("1." + "0" * sz_decimals), rounding=ROUND_FLOOR))

    @staticmethod
    def round_px(px: float, sig_figs: int = 5) -> float:
        if px == 0:
            return 0.0
        return round(px, sig_figs - int(math.floor(math.log10(abs(px)))) - 1)

    def cancel_all_open_orders(self):
        """Cancels all active resting orders and trigger brackets before rebalancing."""
        if DRY_RUN:
            print("[DRY-RUN] Bypassing exchange order cancellation.")
            return

        try:
            for o in self.info.frontend_open_orders(self.wallet):
                try:
                    self.exchange.cancel(o["coin"], o["oid"])
                except Exception:
                    pass
        except Exception as e:
            print(f"[EXECUTOR] Error cancelling resting orders: {e}")


    def get_live_account_state(self):
        """Calculates Unified Portfolio Value (Perps Margin + Spot USDC)."""
        ch = self.info.user_state(self.wallet)
        perp_equity = float(ch.get("marginSummary", {}).get("accountValue", 0.0))

        spot = self.info.spot_user_state(self.wallet)
        spot_usdc = sum(
            float(b.get("total", 0.0))
            for b in spot.get("balances", [])
            if b.get("coin") == "USDC" or b.get("token") == 0
        )

        total_equity = spot_usdc if spot_usdc > 0 else perp_equity

        current_positions = {}
        for p in ch.get("assetPositions", []):
            pos = p.get("position", {})
            coin = pos.get("coin")
            szi = float(pos.get("szi", 0.0))
            if abs(szi) > 0 and coin:
                current_positions[coin] = szi

        return round(total_equity, 2), current_positions

    def arm_position_brackets(self):
        """Arms native Stop-Loss and Take-Profit triggers for all active exchange positions."""
        user_state = self.info.user_state(self.wallet)
        all_orders = self.info.frontend_open_orders(self.wallet)
        positions = [p["position"] for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]

        if not positions:
            return

        # Cancel stale triggers for active positions to avoid stacking
        for o in all_orders:
            if o.get("isTrigger") or "trigger" in str(o.get("orderType", "")).lower():
                coin = o.get("coin")
                oid = o.get("oid")
                if coin and oid:
                    try:
                        self.exchange.cancel(coin, oid)
                    except Exception:
                        pass
        existing_triggers = set()

        df = pl.read_parquet(LAKE_FILE) if LAKE_FILE.exists() else None

        print("\n[BRACKETS] Synchronizing Native Stop & Profit Triggers...")
        for p in positions:
            coin = p["coin"]
            szi = float(p["szi"])
            entry_px = float(p["entryPx"])
            sz = abs(szi)
            is_long = szi > 0

            if coin in existing_triggers:
                continue

            atr_pct = 0.035
            if df is not None:
                sub = df.filter(pl.col("symbol") == coin)
                if sub.height > 0:
                    if "atr_14" in sub.columns and "close" in sub.columns:
                        atr_pct = float(sub.select((pl.col("atr_14") / (pl.col("close") + 1e-8)).last()).to_series()[0])
                    elif "vol_yang_zhang" in sub.columns:
                        atr_pct = float(sub.select(pl.col("vol_yang_zhang").last()).to_series()[0])

            cfg_risk = STRATEGY_CONFIG.risk_brackets
            stop_dist = entry_px * max(atr_pct * cfg_risk.stop_loss_atr_mult, cfg_risk.stop_loss_min_pct)
            tp_dist = entry_px * max(atr_pct * cfg_risk.take_profit_atr_mult, cfg_risk.take_profit_min_pct)

            sl_px = self.round_px(entry_px - stop_dist if is_long else entry_px + stop_dist)
            tp_px = self.round_px(entry_px + tp_dist if is_long else entry_px - tp_dist)

            if DRY_RUN:
                print(f"   • [DRY-RUN BRACKET] {coin}: SL @ ${sl_px} | TP @ ${tp_px} (Simulated)")
                continue

            try:
                self.exchange.order(
                    name=coin,
                    is_buy=not is_long,
                    sz=sz,
                    limit_px=sl_px,
                    order_type={"trigger": {"isMarket": True, "triggerPx": sl_px, "tpsl": "sl"}},
                    reduce_only=True
                )
            except Exception as e:
                print(f"   [BRACKET ERROR] {coin} SL: {e}")

            try:
                self.exchange.order(
                    name=coin,
                    is_buy=not is_long,
                    sz=sz,
                    limit_px=tp_px,
                    order_type={"trigger": {"isMarket": True, "triggerPx": tp_px, "tpsl": "tp"}},
                    reduce_only=True
                )
            except Exception as e:
                print(f"   [BRACKET ERROR] {coin} TP: {e}")

    def reconcile_and_execute(self, target_weights: dict) -> dict:
        self.cancel_all_open_orders()
        equity, current_positions = self.get_live_account_state()

        meta = self.info.meta()
        sz_decimals_map = {u["name"]: int(u.get("szDecimals", 4)) for u in meta.get("universe", [])}
        all_mids = self.info.all_mids()

        target_positions = {}
        for coin, weight in target_weights.items():
            px = float(all_mids.get(coin, 0.0))
            if px > 0:
                ntl = equity * weight
                decimals = sz_decimals_map.get(coin, 4)
                target_positions[coin] = self.round_sz(ntl / px, decimals)

        all_coins = sorted(list(set(current_positions.keys()).union(set(target_positions.keys()))))
        actions = []

        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        mode_str = "DRY-RUN (SIMULATED)" if DRY_RUN else "LIVE TRADING"
        print(f"[{now_utc}] Executing Micro-Defended ALO Rebalance [{mode_str}]...")
        print(f"[EXECUTOR] Live Unified Equity: ${equity:,.2f} | Open Positions: {len(current_positions)}")
        print("=" * 95)
        print(f"{'SYMBOL':<10} {'CURRENT':<10} {'TARGET':<10} {'DELTA':<10} {'ACTION':<18} {'DEFENSE':<18} {'STATUS'}")
        print("=" * 95)

        for coin in all_coins:
            curr_sz = current_positions.get(coin, 0.0)
            tgt_sz = target_positions.get(coin, 0.0)
            delta = tgt_sz - curr_sz
            px = float(all_mids.get(coin, 1.0))
            delta_usd = abs(delta * px)
            decimals = sz_decimals_map.get(coin, 4)
            delta = self.round_sz(delta, decimals)

            # 1. Close unallocated positions via ALO Maker Orders
            if coin not in target_positions and abs(curr_sz) > 0:
                is_buy = curr_sz < 0
                sz = abs(curr_sz)
                try:
                    l2 = self.info.l2_snapshot(coin)
                    bids = l2.get("levels", [[]])[0]
                    asks = l2.get("levels", [[], []])[1]
                    best_bid = float(bids[0]["px"]) if bids else px * 0.999
                    best_ask = float(asks[0]["px"]) if asks else px * 1.001
                    close_px = self.round_px(best_bid if is_buy else best_ask)
                except Exception:
                    close_px = self.round_px(px * (0.999 if is_buy else 1.001))

                action_str = f"CLOSE_ALO ({curr_sz:+g})"
                if DRY_RUN:
                    res = {"status": "dry_run_simulated", "simulated": True}
                else:
                    try:
                        res = self.exchange.order(
                            name=coin,
                            is_buy=is_buy,
                            sz=sz,
                            limit_px=close_px,
                            order_type={"limit": {"tif": "Alo"}},
                            reduce_only=True
                        )
                    except Exception as e:
                        res = {"status": "error", "error": str(e)}

                status = "simulated" if DRY_RUN else ("submitted" if res.get("status") == "ok" else "failed")
                print(f"{coin:<10} {curr_sz:<10.4f} {tgt_sz:<10.4f} {delta:<10.4f} {action_str:<18} {'UNALLOC_CLOSE':<18} {status}")
                actions.append({"coin": coin, "action": "CLOSE", "result": res})

            # 2. Defended ALO Maker Entry with 5% Turnover Deadband
            elif abs(delta_usd) >= STRATEGY_CONFIG.execution.min_delta_usd:
                curr_w = (curr_sz * px) / equity if equity > 0 else 0.0
                tgt_w = target_weights.get(coin, 0.0)
                if abs(tgt_w - curr_w) < STRATEGY_CONFIG.execution.min_turnover_deadband and tgt_w != 0.0:
                    continue

                is_buy = delta > 0
                sz = abs(delta)

                try:
                    l2 = self.info.l2_snapshot(coin)
                    bids = l2.get("levels", [[]])[0]
                    asks = l2.get("levels", [[], []])[1]
                    best_bid = float(bids[0]["px"]) if bids else px * 0.999
                    best_ask = float(asks[0]["px"]) if asks else px * 1.001
                    half_spread = max((best_ask - best_bid) / 2.0, 0.0001)

                    l2_snap = {f"bid_p{m}": float(bids[m-1]["px"]) if len(bids) >= m else best_bid * (1 - 0.001 * m) for m in range(1, 6)}
                    l2_snap.update({f"bid_q{m}": float(bids[m-1]["sz"]) if len(bids) >= m else 1.0 for m in range(1, 6)})
                    l2_snap.update({f"ask_p{m}": float(asks[m-1]["px"]) if len(asks) >= m else best_ask * (1 + 0.001 * m) for m in range(1, 6)})
                    l2_snap.update({f"ask_q{m}": float(asks[m-1]["sz"]) if len(asks) >= m else 1.0 for m in range(1, 6)})

                    mlofi_pca = self.defense_engine.compute_mlofi_pca([l2_snap, l2_snap])
                    eval_res = self.defense_engine.evaluate_quoting_parameters(
                        mlofi_pca=mlofi_pca,
                        vpin=0.22,
                        base_half_spread=half_spread,
                        vol_yz=0.03
                    )

                    if is_buy:
                        if eval_res["action"] == "WITHDRAW_BIDS":
                            print(f"{coin:<10} {curr_sz:<10.4f} {tgt_sz:<10.4f} {delta:<10.4f} {'BUY':<18} {'WITHDRAW_BID':<18} skipped")
                            continue
                        offset = eval_res["delta_bid"] or half_spread
                        limit_px = self.round_px(min(best_bid, px - offset))
                    else:
                        if eval_res["action"] == "WITHDRAW_ASKS":
                            print(f"{coin:<10} {curr_sz:<10.4f} {tgt_sz:<10.4f} {delta:<10.4f} {'SELL':<18} {'WITHDRAW_ASK':<18} skipped")
                            continue
                        offset = eval_res["delta_ask"] or half_spread
                        limit_px = self.round_px(max(best_ask, px + offset))

                except Exception:
                    limit_px = self.round_px(px * (0.9995 if is_buy else 1.0005))
                    eval_res = {"action": "BASELINE_ALO"}

                action_str = f"{'BUY' if is_buy else 'SELL'} (~${delta_usd:.2f})"

                if DRY_RUN:
                    res = {"status": "dry_run_simulated", "simulated": True}
                else:
                    try:
                        res = self.exchange.order(
                            name=coin,
                            is_buy=is_buy,
                            sz=sz,
                            limit_px=limit_px,
                            order_type={"limit": {"tif": "Alo"}},
                            reduce_only=((curr_sz > 0 and not is_buy) or (curr_sz < 0 and is_buy))
                        )
                    except Exception as e:
                        res = {"status": "error", "error": str(e)}

                status = "simulated" if DRY_RUN else ("submitted" if res.get("status") == "ok" else "failed")
                defense_label = eval_res.get("action", "POST_ALO")
                print(f"{coin:<10} {curr_sz:<10.4f} {tgt_sz:<10.4f} {delta:<10.4f} {action_str:<18} {defense_label:<18} {status}")
                actions.append({"coin": coin, "action": "REBALANCE", "result": res})

        print("=" * 95)

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_equity": equity,
            "current_positions": current_positions,
            "target_positions": target_positions,
            "actions_dispatched": len(actions),
            "results": actions
        }
        with open(STATE_FILE, "w") as f:
            json.dump(report, f, indent=2)

        return report
