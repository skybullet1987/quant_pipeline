import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _ensure_optional_dep_stubs() -> None:
    for mod_name in ("urllib3", "httpx", "requests", "dotenv"):
        try:
            __import__(mod_name)
        except ModuleNotFoundError:
            stub = types.ModuleType(mod_name)
            if mod_name == "urllib3":
                conn = types.ModuleType("urllib3.connection")
                conn.HTTPConnection = type("HTTPConnection", (), {"default_socket_options": []})
                stub.connection = conn
                sys.modules["urllib3.connection"] = conn
            elif mod_name == "dotenv":
                stub.load_dotenv = lambda *a, **kw: False
            elif mod_name == "requests":
                stub.Session = MagicMock
            elif mod_name == "httpx":
                stub.Client = MagicMock
                stub.Limits = MagicMock
            sys.modules[mod_name] = stub


_ensure_optional_dep_stubs()

import audit_losing_trades
from src.polymarket_research.directional_wfo_shadow_sleeves import DirectionalWfoShadowManager
from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester


class _DummyRiskController:
    def __init__(self, min_equity_floor_usd: float = 30.0):
        self.min_equity_floor_usd = min_equity_floor_usd
        self.recorded_pnls = []
        self.drawdown_checks = []

    def record_trade_pnl(self, net_pnl: float, is_non_directional: bool = False) -> None:
        self.recorded_pnls.append((net_pnl, is_non_directional))

    def check_equity_drawdown(self, equity: float, allow_auto_clear: bool = True) -> bool:
        self.drawdown_checks.append((equity, allow_auto_clear))
        return False


class _DummyExecutorForHarvester:
    is_authenticated = True

    def __init__(self, collateral: float = 47.38):
        self._collateral = collateral
        self.reserved_collateral = {}
        self.reserved_inventory = {}

    def get_collateral_balance(self) -> float:
        return self._collateral

    def set_cached_collateral(self, val: float) -> None:
        self._collateral = float(val)

    def get_open_orders(self):
        return []

    def get_all_conditional_balances(self, token_ids):
        return {}

    def release_inventory(self, token_id: str, shares: float) -> None:
        return None

    def release_collateral(self, amount: float) -> None:
        return None


class TestV6FullSystemQA(unittest.TestCase):
    def test_qa01_close_position_and_reconcile_haircut_frozen_equity_for_tier(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "live_harvester_state.json"
            harv = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
            harv.dry_run = False
            harv.state_file = state_path
            harv.executor = _DummyExecutorForHarvester(collateral=47.38)
            harv.risk_controller = _DummyRiskController()
            harv._last_known_collateral = 47.38
            harv.current_equity_tier = "RECOVERY"
            harv.equity_tier_hwm = 47.38
            harv.realized_pnl_total = 0.0
            harv.closed_positions = []
            harv.active_positions = {
                "frozen_kmia": {
                    "market_id": "6707503",
                    "token_id": "tok_kmia",
                    "notional_usd": 50.51,
                    "shares": 35.0,
                    "entry_price": 0.99,
                    "uma_disputed": True,
                    "resolution_status": "disputed",
                    "status": "OPEN",
                },
                "closing_pos": {
                    "market_id": "m_close",
                    "token_id": "tok_close",
                    "notional_usd": 5.0,
                    "shares": 5.0,
                    "entry_price": 1.0,
                    "cum_exit_cash": 5.10,
                    "cum_exit_fees": 0.0,
                    "status": "OPEN",
                },
            }
            harv._pending_collateral_refresh = False
            harv._strict_open_orders = lambda: []
            harv.save_state = lambda: None
            harv.get_position_market_value = lambda pos, now_ts=None: float(pos.get("notional_usd") or 0.0)
            harv._update_live_capital_telemetry = lambda *a, **kw: None
            harv._recompute_global_halt = lambda: None
            harv._attempt_maker_exit_post = lambda *a, **kw: None
            harv._refresh_global_halt = lambda **kw: None
            harv.risk_halt = False
            harv.global_halt = False
            harv.global_halt_reasons = []
            harv.tte_cancel_window = 30.0

            # Before fix, raw tot_equity ($47.38 + $50.51 = $97.89) promoted tier to HYPER_GROWTH
            harv._close_position("closing_pos", harv.active_positions["closing_pos"], "CLOSED", "TAKE_PROFIT", won=True)
            self.assertEqual(harv.current_equity_tier, "RECOVERY")
            self.assertNotEqual(harv.current_equity_tier, "HYPER_GROWTH")
            self.assertLessEqual(harv.equity_tier_hwm, 47.39)

            # Reconcile must also use sizing equity (excluding frozen KMIA) and suppress HWM ratchet
            harv.reconcile_with_exchange()
            self.assertEqual(harv.current_equity_tier, "RECOVERY")
            self.assertNotEqual(harv.current_equity_tier, "HYPER_GROWTH")
            self.assertLessEqual(harv.equity_tier_hwm, 47.39)

    def test_qa03_calculate_realized_cash_pnl_handles_none_fields(self):
        self.assertEqual(
            PolymarketLiveHarvester.calculate_realized_cash_pnl(
                {
                    "entry_fee_asset": None,
                    "entry_fee_cash_usd": None,
                    "fee_usd": None,
                    "notional_usd": None,
                },
                gross_exit_cash=None,
                exit_fee=None,
            ),
            0.0,
        )
        self.assertEqual(
            PolymarketLiveHarvester.calculate_realized_cash_pnl(
                {
                    "entry_fee_asset": "SHARES",
                    "entry_fee_cash_usd": None,
                    "fee_usd": 0.25,
                    "notional_usd": 10.0,
                },
                gross_exit_cash=11.0,
                exit_fee=None,
            ),
            1.0,
        )

    def test_qa02a_post_maker_entry_reprice_exception_marks_outcome_unknown(self):
        ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
        ex.dry_run = False
        ex.is_authenticated = True
        ex.auth_mode = "PROXY"
        ex.client = MagicMock()
        ex._neg_risk_cache = {"tok_1": False}
        ex.get_collateral_balance = lambda force_refresh=False: 100.0
        ex.get_unreserved_collateral = lambda: 100.0
        ex.invalidate_collateral_cache = lambda: None
        ex.quantize_order_price = lambda px, tid, rounding=None: round(float(px), 2)
        ex.get_token_tick_size = lambda tid, price_hint=None: 0.01
        ex.get_token_fee_params = lambda tid: (0.0, 1.0)
        ex.get_market_book = lambda tid: {"asks": [{"price": "0.52", "size": "20"}]}
        ex._post_order_compat = MagicMock(
            side_effect=[
                {"errorMsg": "order crosses book"},
                RuntimeError("socket reset after submit"),
            ]
        )
        ex.client.create_order = MagicMock(return_value={"signed": True})

        with patch("src.polymarket_research.polymarket_live_executor.OrderArgsV2", side_effect=lambda **kw: kw, create=True):
            res = ex.post_maker_entry_order("tok_1", price=0.53, notional_usd=10.0, side="BUY", neg_risk=False)

        self.assertFalse(res.get("success"))
        self.assertTrue(res.get("outcome_unknown"), f"Expected outcome_unknown=True, got {res}")

    def test_qa02b_post_maker_exit_tick_size_failure_does_not_raise_unbound_local(self):
        ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
        ex.dry_run = False
        ex.is_authenticated = True
        ex.auth_mode = "PROXY"
        ex.client = MagicMock()
        ex.reserved_inventory = {}
        ex.get_unreserved_conditional_balance = lambda tid: 20.0
        ex.quantize_order_price = lambda px, tid, rounding=None: round(float(px), 2)
        ex.get_token_tick_size = MagicMock(side_effect=RuntimeError("tick lookup failed"))

        res = ex.post_maker_exit_order("tok_exit", price=0.55, size=10.0, side="SELL", neg_risk=False)
        self.assertFalse(res.get("success"))
        self.assertIn("tick lookup failed", str(res.get("error") or ""))

    def test_qa04_shadow_ledger_survives_corrupt_line_and_ewma_normalizes_dt(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            ledger = data_dir / "ledger_shadow_btc_5m.jsonl"
            ledger.write_text(
                json.dumps({"trade_id": "t1", "market_id": "m1"}) + "\n"
                + "{corrupt json line\n"
                + json.dumps({"trade_id": "t2", "market_id": "m2"}) + "\n",
                encoding="utf-8",
            )
            mgr = DirectionalWfoShadowManager(data_dir=data_dir)
            self.assertEqual([t["trade_id"] for t in mgr.b5_trades], ["t1", "t2"])

            # Compare 1-minute gap vs 10-minute gap for identical log return
            mgr_1m = DirectionalWfoShadowManager(data_dir=data_dir)
            mgr_1m._btc_last_1m_bkt = 1000
            mgr_1m._btc_last_1m_spot = 100.0
            mgr_1m._btc_sigma_1h = 0.0040
            mgr_1m._ingest_btc_5m_telemetry_tick({
                "asset": "BTC",
                "horizon": "5m",
                "timestamp_unix": 1001 * 60 + 5,
                "binance_spot": 100.5,
            })

            mgr_10m = DirectionalWfoShadowManager(data_dir=data_dir)
            mgr_10m._btc_last_1m_bkt = 1000
            mgr_10m._btc_last_1m_spot = 100.0
            mgr_10m._btc_sigma_1h = 0.0040
            mgr_10m._ingest_btc_5m_telemetry_tick({
                "asset": "BTC",
                "horizon": "5m",
                "timestamp_unix": 1010 * 60 + 5,
                "binance_spot": 100.5,
            })

            self.assertLess(mgr_10m._btc_sigma_1h, mgr_1m._btc_sigma_1h)

    def test_qa05_load_audit_state_backs_up_corrupt_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            corrupt_file = Path(tmp) / "audit_state.json"
            corrupt_file.write_text("{not valid json", encoding="utf-8")
            with patch.object(audit_losing_trades, "AUDIT_STATE_FILE", corrupt_file):
                st = audit_losing_trades.load_audit_state()
            self.assertIn("audited_trades", st)
            self.assertFalse(corrupt_file.exists())
            backups = list(Path(tmp).glob("audit_state.json.corrupt.*"))
            self.assertEqual(len(backups), 1)


if __name__ == "__main__":
    unittest.main()
