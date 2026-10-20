import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch

from src.polymarket_research.polymarket_paper_trader import (
    PolymarketForwardPaperTrader,
    SLEEVE_2_INITIAL_CAPITAL,
    SLEEVE_2_TICKET_NOTIONAL,
    SLEEVE_2_MIN_PRICE,
    SLEEVE_2_MAX_PRICE,
)

@pytest.fixture
def clean_trader(tmp_path):
    ledger2 = tmp_path / "ledger_sleeve2.jsonl"
    state2 = tmp_path / "state_sleeve2.json"
    with patch("src.polymarket_research.polymarket_paper_trader.SLEEVE_2_LEDGER_FILE", ledger2), \
         patch("src.polymarket_research.polymarket_paper_trader.SLEEVE_2_STATE_FILE", state2), \
         patch("src.polymarket_research.polymarket_paper_trader.DEV_LEDGER_FILE", tmp_path / "dev.jsonl"), \
         patch("src.polymarket_research.polymarket_paper_trader.VALIDATION_LEDGER_FILE", tmp_path / "val.jsonl"), \
         patch("src.polymarket_research.polymarket_paper_trader.STATE_FILE", tmp_path / "state.json"), \
         patch("src.polymarket_research.polymarket_paper_trader.ENABLE_SLEEVE_304_315", True), \
         patch.object(PolymarketForwardPaperTrader, "replay_existing_data", lambda self: None):
        trader = PolymarketForwardPaperTrader()
        trader.paper_latency_ms = 0
        trader.sleeve2_cash = SLEEVE_2_INITIAL_CAPITAL
        trader.sleeve2_trades = []
        trader.sleeve2_open_trades = {}
        trader.sleeve2_settled_ids = set()
        trader.sleeve2_realized_pnl = 0.0
        trader.sleeve2_total_fees = 0.0
        trader.hourly_candle_opens.clear()
        yield trader, ledger2, state2

def test_sleeve2_mutual_exclusion_sleeve1_priority(clean_trader):
    trader, ledger2, _ = clean_trader

    # A shock in Sleeve 1 domain (TTE <= 1200s, 0.52 <= p <= 0.76, dist >= 0.18)
    shock = {
        "market_id": "M_OVERLAP",
        "t0_unix": time.time(),
        "title": "Ethereum Up 1h",
        "asset": "ETH",
        "candle_interval": "1h",
        "seconds_to_expiry": 1000.0,
        "candle_distance_pct": 0.60,
        "shock_direction": "BUY",
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "best_ask": 0.65,
                "best_bid": 0.64,
                "effective_price_$50": 0.65,
                "vwap_$50": 0.65,
                "depth_ratio_ask": 2.0,
                "raw_top_asks": [[0.65, 200.0]],
            }
        }
    }

    trader.evaluate_shock_signal(shock, historical=False)

    # Core Sleeve 1 must have filled
    assert "M_OVERLAP" in trader.open_trades
    assert len(trader.open_trades["M_OVERLAP"]) == 1
    # Sleeve 2 must NOT have opened a duplicate position
    assert "M_OVERLAP" not in trader.sleeve2_open_trades

def test_sleeve2_veto_if_sleeve1_holds_position(clean_trader):
    trader, ledger2, _ = clean_trader

    # Sleeve 1 already holds a position in M_HELD
    trader.open_trades["M_HELD"] = [{"trade_id": "PAPER_M_HELD_1", "status": "OPEN"}]

    # A shock arrives in Sleeve 2 exclusive domain (TTE = 2000s, price = 0.70)
    shock = {
        "market_id": "M_HELD",
        "t0_unix": time.time(),
        "title": "Ethereum Up 1h",
        "asset": "ETH",
        "candle_interval": "1h",
        "seconds_to_expiry": 2000.0,
        "candle_distance_pct": 0.25,
        "shock_direction": "BUY",
        "pre_shock_features_t0": {
            "UP": {
                "best_ask": 0.75,
                "best_bid": 0.74,
                "raw_top_asks": [[0.75, 200.0]],
            }
        }
    }

    trader.evaluate_shock_signal(shock, historical=False)

    # Sleeve 2 must be vetoed because Sleeve 1 already holds an open position
    assert "M_HELD" not in trader.sleeve2_open_trades

def test_sleeve2_fills_in_sweet_spot_with_l2_walking_and_dynamic_tp(clean_trader):
    trader, ledger2, state2 = clean_trader

    shock = {
        "market_id": "M_S2_VALID",
        "t0_unix": time.time(),
        "title": "Ethereum Up 1h",
        "asset": "ETH",
        "candle_interval": "1h",
        "seconds_to_expiry": 2400.0,  # TTE > 900s -> TP should be VWAP + 0.08
        "spot_at_t0": 3000.0,
        "candle_distance_pct": 0.50,
        "shock_direction": "BUY",
        "pre_shock_features_t0": {
            "UP": {
                "best_ask": 0.75,
                "best_bid": 0.74,
                # Sufficient depth: 0.75 * 150 = $112.50 >= $75 ($50 * 1.5)
                "raw_top_asks": [[0.75, 150.0]],
            }
        }
    }

    trader.evaluate_shock_signal(shock, historical=False)

    # Sleeve 1 should not touch this (TTE = 2400s > 1350s)
    assert "M_S2_VALID" not in trader.open_trades
    # Sleeve 2 should have filled
    assert "M_S2_VALID" in trader.sleeve2_open_trades
    s2_pos = trader.sleeve2_open_trades["M_S2_VALID"][0]
    assert s2_pos["sleeve"] == "SLEEVE_2_MULTI_304_315"
    assert s2_pos["notional_usd"] == SLEEVE_2_TICKET_NOTIONAL
    assert s2_pos["vwap_exec_price"] == 0.75
    # Expected strike anchor: 3000 / (1 + 0.5/100) = 2985.07
    assert s2_pos["strike_price"] == pytest.approx(3000.0 / 1.005, 0.01)
    # Expected maker TP: Standard 0.99 resting Maker TP
    assert s2_pos["take_profit_maker_limit_px"] == 0.99

    # Now test 0.99 Maker TP fill on telemetry
    telem = {
        "timestamp_unix": shock["t0_unix"] + 10.0,  # > 6s delay
        "UP": {
            "best_bid": 0.99,
            "best_ask": 1.00,
        }
    }
    closed = trader.check_maker_tp_fills("M_S2_VALID", telem)
    assert len(closed) == 0  # check_maker_tp_fills returns Sleeve 1 closed trades
    assert "M_S2_VALID" not in trader.sleeve2_open_trades
    assert len(trader.sleeve2_trades) == 1
    assert trader.sleeve2_trades[0]["won"] is True
    assert trader.sleeve2_trades[0]["exit_reason"] in ("EXP315_MAKER_TP_FILLED", "MAKER_SCALP_FILLED_CLOB")
    assert trader.sleeve2_realized_pnl > 0
    assert trader.sleeve2_cash > SLEEVE_2_INITIAL_CAPITAL

def test_sleeve2_settle_market(clean_trader):
    trader, ledger2, _ = clean_trader

    shock = {
        "market_id": "M_S2_SETTLE",
        "t0_unix": time.time(),
        "title": "Ethereum Up 1h",
        "asset": "ETH",
        "candle_interval": "1h",
        "seconds_to_expiry": 2000.0,  # 1350s < TTE <= 3300s (Sleeve 2 sweet spot)
        "spot_at_t0": 3000.0,
        "candle_distance_pct": 0.30,
        "shock_direction": "BUY",
        "pre_shock_features_t0": {
            "UP": {
                "best_ask": 0.72,
                "raw_top_asks": [[0.72, 200.0]],
            }
        }
    }

    trader.evaluate_shock_signal(shock, historical=False)
    assert "M_S2_SETTLE" in trader.sleeve2_open_trades

    # Settle market as UP winning
    resolution = {
        "winning_outcome": "UP",
        "timestamp_resolved": "2026-10-18 05:00:00 UTC"
    }
    trader.settle_market("M_S2_SETTLE", resolution, historical=False)

    assert "M_S2_SETTLE" not in trader.sleeve2_open_trades
    assert len(trader.sleeve2_trades) == 1
    trade = trader.sleeve2_trades[0]
    assert trade["won"] is True
    assert trade["exit_reason"] == "EXP304_315_HOLD_TO_MATURITY_SETTLEMENT"
    assert trade["net_pnl_usd"] > 0
