import time
from typing import Dict, Any, List, Tuple
from src.execution.exchange_gateway import HyperliquidGateway
from src.execution.state_manager import StateManager

class OrderRouter:
    def __init__(self, gateway: HyperliquidGateway, state_manager: StateManager, 
                 deadband: float = 0.050, min_notional: float = 10.0, dry_run: bool = True):
        self.gw = gateway
        self.sm = state_manager
        self.deadband = deadband
        self.min_notional = min_notional
        self.dry_run = dry_run

    def compute_rebalance_orders(
        self, target_weights: Dict[str, float], total_equity: float,
        current_positions: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculates discrete delta orders respecting deadbands and precision."""
        orders_to_execute = []
        all_symbols = set(list(target_weights.keys()) + list(current_positions.keys()))

        for sym in sorted(all_symbols):
            tgt_w = target_weights.get(sym, 0.0)
            curr_pos = current_positions.get(sym, {})
            curr_sz = curr_pos.get("size", 0.0)
            
            try:
                mid_px = self.gw.get_mid_price(sym)
            except Exception as e:
                print(f" [WARN] Skipping {sym}: could not fetch mid price ({e})")
                continue

            curr_notional = curr_sz * mid_px
            curr_w = curr_notional / total_equity if total_equity > 0 else 0.0
            delta_w = tgt_w - curr_w

            # Deadband filter: skip minor fluctuations unless flipping sign or closing
            if abs(tgt_w) > 1e-4 and abs(curr_w) > 1e-4 and (tgt_w * curr_w > 0):
                if abs(delta_w) < self.deadband:
                    continue

            target_sz = self.gw.round_sz(sym, (tgt_w * total_equity) / mid_px)
            delta_sz = self.gw.round_sz(sym, target_sz - curr_sz)

            # Minimum notional check
            if abs(delta_sz * mid_px) < self.min_notional and abs(target_sz) > 1e-5:
                continue

            if abs(delta_sz) > 1e-5:
                orders_to_execute.append({
                    "symbol": sym,
                    "is_buy": delta_sz > 0,
                    "delta_sz": abs(delta_sz),
                    "target_sz": target_sz,
                    "mid_px": mid_px,
                    "target_w": tgt_w,
                    "curr_w": curr_w
                })

        return orders_to_execute

    def execute_rebalance(self, planned_orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Routes orders via ALO (post-only), logging dry-run intents when active."""
        execution_report = {"filled": [], "failed": [], "dry_run": self.dry_run}

        for ord_info in planned_orders:
            sym = ord_info["symbol"]
            is_buy = ord_info["is_buy"]
            sz = ord_info["delta_sz"]
            px = ord_info["mid_px"]

            if self.dry_run:
                print(f" [DRY-RUN] {('BUY' if is_buy else 'SELL'):<4} {sym:<6} | Size: {sz} | Limit: {px} | Tgt W: {ord_info['target_w']:+.3f}")
                execution_report["filled"].append({**ord_info, "status": "SIMULATED_FILLED"})
                continue

            try:
                res = self.gw.place_alo_order(sym, is_buy, sz, px)
                if res.get("status") == "ok":
                    execution_report["filled"].append({**ord_info, "res": res})
                    print(f" [LIVE ALO] Placed {('BUY' if is_buy else 'SELL')} {sz} {sym} @ {px}")
                else:
                    execution_report["failed"].append({**ord_info, "error": res})
                    print(f" [REJECTED] {sym}: {res}")
            except Exception as e:
                execution_report["failed"].append({**ord_info, "error": str(e)})
                print(f" [ERROR] Failed order for {sym}: {e}")

        return execution_report
