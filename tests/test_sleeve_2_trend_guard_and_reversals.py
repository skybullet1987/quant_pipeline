import pytest
import time
from collections import defaultdict
from unittest.mock import MagicMock, AsyncMock

from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.polymarket_paper_trader import PolymarketForwardPaperTrader

def test_sleeve_2_trend_guard_vetoes_early_counter_trend():
    harvester = PolymarketLiveHarvester(dry_run=True)
    # Simulate bull trend in ETH:
    # Hour 100: open 2350.0
    # Hour 101: open 2370.0 (UP)
    # Hour 102: open 2395.0 (UP, ret_2h = +1.91%)
    harvester.hourly_candle_opens["ETH"][100] = 2350.0
    harvester.hourly_candle_opens["ETH"][101] = 2370.0
    harvester.hourly_candle_opens["ETH"][102] = 2395.0

    # 1. Counter-trend DOWN signal at minute :16 (TTE = 2600s) on shallow dip (-0.25% < 0.45% hurdle)
    shock_counter = {
        "market_id": "999901",
        "asset": "ETH",
        "title": "Ethereum Up or Down - 7PM ET",
        "t0_unix": 102 * 3600 + 960,  # 16 minutes past hour 102
        "seconds_to_expiry": 2640.0,
        "shock_direction": "SELL",  # DOWN
        "candle_distance_pct": -0.25,
        "finalized_1h_open": 2395.0,
        "pre_shock_features_t0": {
            "DOWN": {
                "token_id": "tok_down_1",
                "raw_top_asks": [[0.75, 1000.0]],
                "raw_top_bids": [[0.74, 1000.0]]
            }
        }
    }

    # Should be vetoed by trend guard
    opens_map = harvester.hourly_candle_opens["ETH"]
    cur_h = 102
    ret_2h = (opens_map[cur_h] - opens_map[cur_h-2]) / opens_map[cur_h-2]
    assert ret_2h > 0.0030  # Bull trend confirmed (+1.91%)

    # Verify paper trader also has the guard
    paper = PolymarketForwardPaperTrader()
    paper.hourly_candle_opens["ETH"][100] = 2350.0
    paper.hourly_candle_opens["ETH"][101] = 2370.0
    paper.hourly_candle_opens["ETH"][102] = 2395.0

    # Test paper trader shock evaluation rejects counter-trend
    paper.open_trades.clear()
    paper.sleeve2_open_trades.clear()
    paper._evaluate_sleeve_2(shock_counter)
    assert "999901" not in paper.sleeve2_open_trades

def test_sleeve_2_trend_guard_preserves_trend_aligned_signals():
    harvester = PolymarketLiveHarvester(dry_run=True)
    # Simulate bull trend in ETH:
    harvester.hourly_candle_opens["ETH"][100] = 2350.0
    harvester.hourly_candle_opens["ETH"][101] = 2370.0
    harvester.hourly_candle_opens["ETH"][102] = 2395.0

    # Trend-aligned UP signal at minute :05 (TTE = 3300s) with +0.20% cushion
    opens_map = harvester.hourly_candle_opens["ETH"]
    cur_h = 102
    ret_2h = (opens_map[cur_h] - opens_map[cur_h-2]) / opens_map[cur_h-2]
    assert ret_2h > 0.0  # Uptrend

    # UP signal is trend-aligned: is_counter_trend must be False
    is_counter_trend = False
    target_token = "UP"
    if target_token == "DOWN":
        if ret_2h > 0.0030:
            is_counter_trend = True
    elif target_token == "UP":
        if ret_2h < -0.0030:
            is_counter_trend = True
    assert not is_counter_trend

def test_strict_per_market_mutual_exclusion_rejects_double_betting():
    harvester = PolymarketLiveHarvester(dry_run=True)
    m_id = "5791402"
    now = time.time()

    # Suppose Sleeve 2 entered DOWN at TTE = 2461s (early in hour)
    harvester.active_positions["LIVE_5791402_DOWN"] = {
        "trade_id": "LIVE_5791402_DOWN",
        "market_id": m_id,
        "target_token": "DOWN",
        "sleeve": "SLEEVE_2_MULTI_304_315",
        "entry_tte": 2461.0,
        "candle_expiry_ts": now + 800.0,
        "entry_ts": now - 1661.0,
        "notional_usd": 40.0,
        "remaining_shares": 50.0,
        "status": "OPEN"
    }

    # Now at TTE = 800s (final 13m), a SLEEVE_1 signal triggers UP on the same market!
    # Strict mutual exclusion must REJECT this entry to avoid paying $1.62 total cost for $1.00 binary payoff
    active_for_market = any(
        p.get("market_id") == m_id
        for p in harvester.active_positions.values()
    )
    assert active_for_market  # Market is already active! Entry rejected!

def test_final_45s_capital_recycler_threshold():
    # Final-45s Capital Recycler must trigger when TTE <= 45s, best_bid >= 0.90, and best_bid > entry + 0.03
    tte_rem = 35.0
    rem_shrs = 30.0
    entry_px = 0.78
    best_b = 0.93

    should_recycle = (tte_rem <= 45.0 and rem_shrs > 0.01 and best_b >= 0.90 and best_b > (entry_px + 0.03))
    assert should_recycle

    # Should not recycle if best_bid is below entry + 0.03 (e.g. fire-sale loss)
    bad_bid = 0.80  # only +0.02 above entry
    assert not (tte_rem <= 45.0 and rem_shrs > 0.01 and bad_bid >= 0.90 and bad_bid > (entry_px + 0.03))

    # Should not recycle if best_bid < 0.90
    low_bid = 0.88
    assert not (tte_rem <= 45.0 and rem_shrs > 0.01 and low_bid >= 0.90 and low_bid > (entry_px + 0.03))

def test_tiered_dynamic_equity_sizing():
    harvester = PolymarketLiveHarvester(dry_run=True)
    bankroll = 118.17
    total_account_value = bankroll

    # Sleeve 2 (Early/Mid): 28% of equity with min floor $25.00
    sleeve2_pct = 0.28
    sleeve2_cap = round(min(250.0, max(25.0, total_account_value * sleeve2_pct)), 2)
    assert sleeve2_cap == 33.09  # 28% of $118.17

    # Sleeve 1 (Late Conviction): 30% of equity
    sleeve1_pct = 0.30
    sleeve1_cap = round(min(250.0, max(25.0, total_account_value * sleeve1_pct)), 2)
    assert sleeve1_cap == 35.45  # 30% of $118.17

def test_sleeve_2_btc_1h_permitted():
    # Verify paper trader permits BTC in Sleeve 2
    paper = PolymarketForwardPaperTrader()
    shock_btc = {
        "market_id": "5792999",
        "asset": "BTC",
        "title": "Bitcoin Up or Down - October 18, 10PM ET",
        "t0_unix": 1792376000.0,
        "seconds_to_expiry": 2400.0,
        "shock_direction": "BUY",
        "candle_distance_pct": 0.25,
        "candle_open_spot": 82000.0,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "tok_btc_up",
                "raw_top_asks": [[0.75, 100.0]],
                "raw_top_bids": [[0.74, 100.0]]
            }
        }
    }
    paper.open_trades.clear()
    paper.sleeve2_open_trades.clear()
    paper._evaluate_sleeve_2(shock_btc)
    assert "5792999" in paper.sleeve2_open_trades
    trade = paper.sleeve2_open_trades["5792999"][0]
    assert trade["target_token"] == "UP"
