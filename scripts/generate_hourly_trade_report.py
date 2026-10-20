#!/usr/bin/env python3
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path('/home/skybullet1987/quant_pipeline/data/polymarket')


def top_of_book(book_resp):
    """True top-of-book over positive-size levels (CLOB level ordering is not guaranteed)."""
    def _levels(side):
        out = []
        for lvl in (book_resp or {}).get(side, []) or []:
            try:
                px, sz = float(lvl["price"]), float(lvl["size"])
            except Exception:
                continue
            if sz > 0.0 and px > 0.0:
                out.append(px)
        return out

    bids = _levels("bids")
    asks = _levels("asks")
    best_bid = max(bids) if bids else 0.0
    best_ask = min(asks) if asks else 1.0
    mid_px = round((best_bid + best_ask) / 2.0, 4) if (bids and asks) else best_bid
    return best_bid, best_ask, mid_px


def _load(name):
    path = DATA_DIR / name
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def run_report():
    now_utc = datetime.now(timezone.utc)
    now_ts = now_utc.timestamp()

    live_state = _load('live_harvester_state.json')
    paper_state = _load('paper_trader_state.json')
    sleeve_state = _load('state_sleeve_304_315.json')

    # Dynamic per-position book + resting exit order status (no hardcoded token/trade IDs)
    active_reports = {}
    for tid, pos in (live_state.get("active_positions", {}) or {}).items():
        token_id = pos.get("token_id")
        book_info = {}
        if token_id:
            try:
                book_resp = requests.get(f"https://clob.polymarket.com/book?token_id={token_id}", timeout=5).json()
                best_bid, best_ask, mid_px = top_of_book(book_resp)
                book_info = {"token_id": token_id, "best_bid": best_bid, "best_ask": best_ask, "mid_price": mid_px}
            except Exception as e:
                book_info = {"token_id": token_id, "error": str(e)}
        exit_order_data = {}
        exit_oid = pos.get("exit_order_id")
        if exit_oid:
            try:
                exit_order_data = requests.get(f"https://clob.polymarket.com/data/order/{exit_oid}", timeout=5).json()
            except Exception as e:
                exit_order_data = {"error": str(e)}
        active_reports[tid] = {
            "position": pos,
            "token_orderbook": book_info,
            "exit_order_status_clob": exit_order_data,
        }

    # Current spot for each traded asset
    spots = {}
    for sym in sorted({str(p.get("asset") or "ETH").upper() for p in (live_state.get("active_positions", {}) or {}).values()} or {"ETH", "BTC"}):
        try:
            r_spot = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}USDC", timeout=5).json()
            spots[sym] = float(r_spot.get("price", 0.0))
        except Exception:
            spots[sym] = None

    report = {
        "timestamp_utc": now_utc.isoformat(),
        "now_unix": now_ts,
        "current_hour_window": live_state.get("current_hour_window"),
        "spot_current": spots,
        "live": {
            "trades_this_hour": live_state.get("trades_this_hour"),
            "live_bankroll": live_state.get("live_bankroll"),
            "total_account_equity": live_state.get("total_account_equity"),
            "active_positions_count": live_state.get("active_positions_count"),
            "active_positions": active_reports,
        },
        "paper": {
            "active_open_positions_count": paper_state.get("active_open_positions_count"),
            "sleeve_2_capital": sleeve_state.get("current_equity"),
            "sleeve_2_realized_pnl": sleeve_state.get("realized_pnl"),
            "sleeve_2_win_rate": sleeve_state.get("win_rate_pct"),
            "sleeve_2_total_settled": sleeve_state.get("total_trades_settled"),
            "paper_validation_equity": paper_state.get("validation_oos_epoch", {}).get("paper_portfolio_equity"),
            "paper_validation_pnl": paper_state.get("validation_oos_epoch", {}).get("cumulative_realized_pnl"),
            "paper_validation_win_rate": paper_state.get("validation_oos_epoch", {}).get("win_rate_pct"),
        }
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run_report()
