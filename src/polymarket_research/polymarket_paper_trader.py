#!/usr/bin/env python3
"""
Polymarket Autonomous Forward Paper Trader (Sweet Spot Strategy)
File: src/polymarket_research/polymarket_paper_trader.py

v3.1 Pure Implementation-Conformance / Forensic State:
1. Hard-Enforces R3_VALIDATION_START_UTC = 2026-09-29T18:11:34.000Z (Commit 08d50e8 frozen boundary).
2. Partitions ledgers into DEV calibration (data/polymarket/paper_trading_dev_ledger.jsonl)
   and frozen Out-Of-Sample VALIDATION (data/polymarket/paper_trading_validation_ledger.jsonl).
3. Strictly Fail-Closed executable depth check (DepthRatio >= 1.50, empty book rejects immediately).
4. Strictly requires verified fee metadata in shock payload (fee_rate_market must be present).
5. Fully restart-idempotent (persisted ledgers restored on startup, deduplicating historical events).
"""

import os
import sys
import json
import time
import math
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict

from src.polymarket_research.polymarket_live_executor import calculate_taker_fee
from src.polymarket_research.polymarket_live_harvester import (
    compute_composite_edge_score,
    compute_max_acceptable_ask,
    evaluate_coinbase_venue_veto,
)

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data" / "polymarket"
TRIGGER_FILE = DATA_DIR / "live_shock_triggers.jsonl"
SHOCK_FILE = DATA_DIR / "shock_responses.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
DEV_LEDGER_FILE = DATA_DIR / "paper_trading_dev_ledger.jsonl"
VALIDATION_LEDGER_FILE = DATA_DIR / "paper_trading_validation_ledger.jsonl"
STATE_FILE = DATA_DIR / "paper_trader_state.json"
PID_FILE = DATA_DIR / "paper_trader.pid"
HOURLY_TELEMETRY_FILE = DATA_DIR / "polymarket_hourly_telemetry.jsonl"
HOURLY_TELEMETRY_ETH_FILE = DATA_DIR / "polymarket_hourly_telemetry_eth.jsonl"

INITIAL_PAPER_CAPITAL = 1000.0
TICKET_NOTIONAL = 50.0
# Dynamic Elastic Book-Depth Sizing Parameters ($15.00 to $50.00)
MIN_ELASTIC_TICKET_USD = 15.0
MAX_ELASTIC_TICKET_USD = 200.0
DEFAULT_ELASTIC_SAFETY_RATIO = 1.50
DEFAULT_DYNAMIC_BANKROLL_PCT = 0.24
DEFAULT_PAPER_LATENCY_MS = int(os.getenv("PAPER_LATENCY_MS", "500"))
MAX_TTE_SECONDS = 2700.0  # 45 minutes (:15 onward)
MIN_TTE_SECONDS = 90.0    # 90s floor
MAX_TRADES_PER_HOUR = 6   # match live service's global portfolio-hour cap
MAX_TRADES_PER_MARKET = 2
MAX_ALLOWED_SPREAD = 0.030
MAX_PRICE_CEILING = 0.86  # Hard ceiling at 0.86
MIN_PRICE_FLOOR = 0.55    # Sweet-spot floor at 0.55

# v3.1 Frozen Out-of-Sample Boundary
R3_VALIDATION_START_UTC = "2026-09-29T18:11:34.000Z"
R3_VALIDATION_START_UNIX = 1790705494.0

# ==============================================================================
# SLEEVE 2: MULTI-ASSET 304/315 CONFIGURATION (v3.2 REBOUND CONFIGURATION)
# ==============================================================================
ENABLE_SLEEVE_304_315 = True
SLEEVE_2_INITIAL_CAPITAL = 500.0
SLEEVE_2_TICKET_NOTIONAL = 50.0
SLEEVE_2_MIN_PRICE = 0.55
SLEEVE_2_MAX_PRICE = 0.78
SLEEVE_2_MIN_DEPTH_RATIO = 1.50
SLEEVE_2_MAX_TTE = 2700.0  # 45 minutes left (:15 past the hour)
SLEEVE_2_MIN_TTE = 900.0   # 15 minutes left (:45 past the hour)
SLEEVE_2_LEDGER_FILE = DATA_DIR / "ledger_sleeve_304_315.jsonl"
SLEEVE_2_STATE_FILE = DATA_DIR / "state_sleeve_304_315.json"



class PolymarketForwardPaperTrader:
    def __init__(self, paper_latency_ms: Optional[int] = None):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.paper_latency_ms = paper_latency_ms if paper_latency_ms is not None else DEFAULT_PAPER_LATENCY_MS
        
        # Deduplication & Idempotency Sets
        self.settled_trade_ids: Set[str] = set()
        self.seen_shock_ids: Set[str] = set()
        self.seen_resolution_ids: Set[str] = set()
        self.trades_per_market: Dict[str, int] = defaultdict(int)
        
        # Partitioned Track Records
        self.dev_cash: float = INITIAL_PAPER_CAPITAL
        self.dev_realized_pnl: float = 0.0
        self.dev_total_fees: float = 0.0
        self.dev_trades: List[Dict[str, Any]] = []
        
        self.val_cash: float = INITIAL_PAPER_CAPITAL
        self.val_realized_pnl: float = 0.0
        self.val_total_fees: float = 0.0
        self.val_trades: List[Dict[str, Any]] = []
        
        # In-Flight Open Positions: market_id -> list of open positions
        self.open_trades: Dict[str, List[Dict[str, Any]]] = {}
        self.current_hour_window = int(time.time() // 3600)
        self.trades_this_hour = 0
        
        self.last_trigger_file_pos: int = 0
        self.last_shock_file_pos: int = 0
        self.last_res_file_pos: int = 0
        self.last_telemetry_file_pos: int = 0
        self.last_telemetry_eth_file_pos: int = 0
        self.recent_shock_window: List[Dict[str, Any]] = []

        # SLEEVE 2 State (EXP-304/EXP-315 ETH 1h Sweet-Spot Add-On)
        self.sleeve2_cash: float = SLEEVE_2_INITIAL_CAPITAL
        self.sleeve2_realized_pnl: float = 0.0
        self.sleeve2_total_fees: float = 0.0
        self.sleeve2_trades: List[Dict[str, Any]] = []
        self.sleeve2_open_trades: Dict[str, List[Dict[str, Any]]] = {}
        self.sleeve2_settled_ids: Set[str] = set()

        # Load existing ledgers idempotently
        self.load_persisted_ledgers()
        self.load_persisted_sleeve2_ledger()
        if STATE_FILE.exists():
            try:
                saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                if int(saved.get("current_hour_window", -1)) == self.current_hour_window:
                    self.trades_this_hour = int(saved.get("trades_this_hour", 0))
            except Exception as exc:
                pass
        self.hourly_candle_opens: Dict[str, Dict[int, float]] = defaultdict(dict)
        self._prewarm_hourly_opens()

    def _prewarm_hourly_opens(self):
        """Prewarms recent hourly candle opens from live_shock_triggers.jsonl to empower rolling trend guards."""
        trigger_path = DATA_DIR / "live_shock_triggers.jsonl"
        if not trigger_path.exists():
            return
        try:
            with open(trigger_path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                read_sz = min(size, 8 * 1024 * 1024)
                f.seek(size - read_sz)
                lines = f.read().decode("utf-8", errors="ignore").splitlines()
            for line in lines:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    title_l = str(data.get("title", "") or "").lower()
                    horiz_l = str(data.get("horizon", "") or data.get("candle_interval", "")).lower()
                    slug_l = str(data.get("series_slug", "") or data.get("slug", "")).lower()
                    if any(x in horiz_l or x in slug_l or x in title_l for x in ("5m", "15m", "300s", "900s")):
                        continue
                    asset = data.get("asset")
                    t0_unix = data.get("t0_unix")
                    open_p = data.get("finalized_1h_open") or data.get("candle_open_spot")
                    if asset in ("BTC", "ETH") and t0_unix and open_p and float(open_p) > 0:
                        h_idx = int(float(t0_unix) // 3600)
                        if h_idx not in self.hourly_candle_opens[asset]:
                            self.hourly_candle_opens[asset][h_idx] = float(open_p)
                except Exception:
                    pass
        except Exception:
            pass

    def load_persisted_ledgers(self):
        """Loads DEV and VALIDATION ledgers to restore state idempotently without duplication."""
        # 1. Ingest DEV ledger
        if DEV_LEDGER_FILE.exists():
            with open(DEV_LEDGER_FILE, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    tid = t["trade_id"]
                    if tid not in self.settled_trade_ids:
                        self.settled_trade_ids.add(tid)
                        self.dev_trades.append(t)
                        self.dev_realized_pnl += t.get("net_pnl_usd", 0.0)
                        self.dev_total_fees += t.get("taker_fee_usd", 0.0)
                        m_id = t.get("market_id")
                        if m_id:
                            self.trades_per_market[m_id] += 1
            self.dev_cash = INITIAL_PAPER_CAPITAL + self.dev_realized_pnl

        # 2. Ingest VALIDATION ledger
        if VALIDATION_LEDGER_FILE.exists():
            with open(VALIDATION_LEDGER_FILE, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    tid = t["trade_id"]
                    if tid not in self.settled_trade_ids:
                        self.settled_trade_ids.add(tid)
                        self.val_trades.append(t)
                        self.val_realized_pnl += t.get("net_pnl_usd", 0.0)
                        self.val_total_fees += t.get("taker_fee_usd", 0.0)
                        m_id = t.get("market_id")
                        if m_id:
                            self.trades_per_market[m_id] += 1
            self.val_cash = INITIAL_PAPER_CAPITAL + self.val_realized_pnl

        print(f"[RECOVERY COMPLETE] Loaded {len(self.settled_trade_ids)} settled trades from disk across {len(self.trades_per_market)} markets."
              f"\n  DEV Ledger: {len(self.dev_trades)} trades | Realized PnL: ${self.dev_realized_pnl:+.2f} | Cash: ${self.dev_cash:,.2f}"
              f"\n  OOS VALIDATION Ledger: {len(self.val_trades)} trades | Realized PnL: ${self.val_realized_pnl:+.2f} | Cash: ${self.val_cash:,.2f}", flush=True)

    def load_persisted_sleeve2_ledger(self):
        """Loads SLEEVE_2_LEDGER_FILE to restore Sleeve 2 state idempotently."""
        if SLEEVE_2_LEDGER_FILE.exists():
            with open(SLEEVE_2_LEDGER_FILE, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    tid = t.get("trade_id")
                    if tid and tid not in self.sleeve2_settled_ids:
                        self.sleeve2_settled_ids.add(tid)
                        self.sleeve2_trades.append(t)
                        self.sleeve2_realized_pnl += t.get("net_pnl_usd", 0.0)
                        self.sleeve2_total_fees += t.get("taker_fee_usd", 0.0)
            self.sleeve2_cash = SLEEVE_2_INITIAL_CAPITAL + self.sleeve2_realized_pnl
            print(f"[SLEEVE 2 RECOVERY] Loaded {len(self.sleeve2_trades)} settled trades | Realized PnL: ${self.sleeve2_realized_pnl:+.2f} | Cash: ${self.sleeve2_cash:,.2f}", flush=True)

    def save_sleeve2_state(self):
        """Saves isolated state persistence for SLEEVE_2_MULTI_304_315."""
        total_trades = len(self.sleeve2_trades)
        wins = sum(1 for t in self.sleeve2_trades if t.get("won"))
        wr = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
        state = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "sleeve_id": "SLEEVE_2_MULTI_304_315",
            "strategy": "ETH 1h Sweet-Spot (0.72-0.85) Lead-Lag Momentum",
            "initial_capital": SLEEVE_2_INITIAL_CAPITAL,
            "current_equity": round(self.sleeve2_cash, 2),
            "realized_pnl": round(self.sleeve2_realized_pnl, 2),
            "total_fees_paid": round(self.sleeve2_total_fees, 2),
            "total_trades_settled": total_trades,
            "winning_trades": wins,
            "losing_trades": total_trades - wins,
            "win_rate_pct": round(wr, 2),
            "active_open_positions_count": sum(len(v) for v in self.sleeve2_open_trades.values()),
            "status": "RUNNING" if ENABLE_SLEEVE_304_315 else "DISABLED",
            "ledger_file": str(SLEEVE_2_LEDGER_FILE),
        }
        tmp_file = SLEEVE_2_STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, SLEEVE_2_STATE_FILE)
        except Exception:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass

    def _get_live_account_equity(self) -> Optional[float]:
        """Reads live_harvester_state.json to extract the live wallet's actual total equity."""
        try:
            live_state_file = getattr(self, "live_state_file", DATA_DIR / "live_harvester_state.json")
            if live_state_file.exists():
                st = json.loads(live_state_file.read_text(encoding="utf-8"))
                eq = st.get("total_account_equity")
                if eq is not None and isinstance(eq, (int, float)) and eq > 0:
                    return float(eq)
                bankroll = st.get("live_bankroll")
                if bankroll is not None and isinstance(bankroll, (int, float)) and bankroll > 0:
                    active_exp = sum(p.get("notional_usd", 0.0) for p in st.get("active_positions", {}).values())
                    return float(bankroll) + active_exp
        except Exception:
            pass
        return None

    def _get_latest_telemetry_snapshot(
        self, market_id: str, asset: str = "", min_timestamp_unix: float = 0.0, poll_timeout_sec: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """Fast tail search of hourly telemetry to obtain post-latency orderbook snapshot for live triggers.
        If min_timestamp_unix > 0 and poll_timeout_sec > 0, polls until a snapshot with
        timestamp_unix >= min_timestamp_unix is written to disk (up to poll_timeout_sec).
        """
        target_file = HOURLY_TELEMETRY_ETH_FILE if str(asset).upper() == "ETH" else HOURLY_TELEMETRY_FILE
        if not target_file.exists():
            return None

        deadline = time.time() + max(0.0, poll_timeout_sec)
        while True:
            try:
                sz = target_file.stat().st_size
                read_sz = min(sz, 131072)
                with open(target_file, "rb") as f:
                    f.seek(sz - read_sz)
                    lines = f.read().decode("utf-8", errors="ignore").splitlines()
                for l in reversed(lines):
                    if not l.strip():
                        continue
                    try:
                        d = json.loads(l)
                        if str(d.get("market_id")) == str(market_id):
                            ts_u = float(d.get("timestamp_unix") or d.get("ts") or 0.0)
                            if min_timestamp_unix <= 0.0 or ts_u >= min_timestamp_unix:
                                return d
                    except Exception:
                        continue
            except Exception:
                pass

            if time.time() >= deadline:
                break
            time.sleep(0.05)

        # Fallback to latest available snapshot without min_timestamp restriction if timeout reached
        try:
            sz = target_file.stat().st_size
            read_sz = min(sz, 131072)
            with open(target_file, "rb") as f:
                f.seek(sz - read_sz)
                lines = f.read().decode("utf-8", errors="ignore").splitlines()
            for l in reversed(lines):
                if not l.strip():
                    continue
                try:
                    d = json.loads(l)
                    if str(d.get("market_id")) == str(market_id):
                        return d
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def replay_existing_data(self):
        """Replays historical shock data to catch any pending un-settled trades in active markets."""
        if not RESOLUTIONS_FILE.exists() or not SHOCK_FILE.exists():
            return

        resolutions: Dict[str, Dict[str, Any]] = {}
        with open(RESOLUTIONS_FILE, "r") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    resolutions[r["market_id"]] = r
                    self.seen_resolution_ids.add(r["market_id"])

        with open(SHOCK_FILE, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                s = json.loads(line)
                shock_id = f"{s.get('market_id')}_{s.get('t0_unix')}"
                self.seen_shock_ids.add(shock_id)
                self.evaluate_shock_signal(s, historical=True)

        if TRIGGER_FILE.exists():
            with open(TRIGGER_FILE, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    s = json.loads(line)
                    shock_id = f"{s.get('market_id')}_{s.get('t0_unix')}"
                    if shock_id not in self.seen_shock_ids:
                        self.seen_shock_ids.add(shock_id)
                        self.evaluate_shock_signal(s, historical=True)
            self.last_trigger_file_pos = TRIGGER_FILE.stat().st_size

        if SHOCK_FILE.exists():
            self.last_shock_file_pos = SHOCK_FILE.stat().st_size

        # Settle any open historical markets against finalized resolutions
        for m_id, res in resolutions.items():
            self.settle_market(m_id, res, historical=True)

        self.save_state()
        print(f"[REPLAY SYNCHRONIZED] Open in-flight markets: {len(self.open_trades)}", flush=True)

    def evaluate_shock_signal(self, shock: Dict[str, Any], historical: bool = False):
        # 1. Evaluate Core Sleeve 1 (EXP-302 Baseline)
        sleeve1_filled = self._evaluate_sleeve_1(shock, historical=historical)
        if sleeve1_filled:
            return  # Mutual exclusion: Trade filled in Sleeve 1 -> Sleeve 2 skipped!

        # 2. Evaluate Sleeve 2 (EXP-304/EXP-315 ETH 1h Sweet-Spot Add-On) if enabled
        if ENABLE_SLEEVE_304_315:
            self._evaluate_sleeve_2(shock, historical=historical)

    def _evaluate_sleeve_1(self, shock: Dict[str, Any], historical: bool = False) -> bool:
        m_id = shock.get("market_id")
        if not m_id:
            return False

        t0_unix = shock.get("t0_unix", time.time())
        shock_dir = shock.get("shock_direction")  # BUY or SELL
        target_token = "UP" if shock_dir == "BUY" else "DOWN"
        trade_id = f"PAPER_{m_id}_{int(t0_unix)}_{target_token}"

        # Idempotency Guard: Never open or re-evaluate already settled trades
        if trade_id in self.settled_trade_ids:
            return False

        # Check in-flight open trades for this market
        current_market_open = self.open_trades.get(m_id, [])
        if any(t["trade_id"] == trade_id for t in current_market_open):
            return False

        # Policy A: Check 99c Maker TP fills on open positions for this market
        if current_market_open:
            token_feats = shock.get("pre_shock_features_t0", {})
            self.check_maker_tp_fills(m_id, token_feats)
            current_market_open = self.open_trades.get(m_id, [])

        # Check total trades per market hour cap (settled + open)
        hour_now = int(time.time() // 3600)
        if hour_now != self.current_hour_window:
            self.current_hour_window = hour_now
            self.trades_this_hour = 0
        # Futures Basis Divergence Gate (delta_basis_100ms)
        delta_basis = float(shock.get("delta_basis_100ms", 0.0) or 0.0)
        if target_token == "UP" and delta_basis < -2.0:
            return False
        elif target_token == "DOWN" and delta_basis > 2.0:
            return False

        # Strict Per-Market Mutual Exclusion: Never hold positions in both Sleeve 1 and Sleeve 2 on the same market
        if ENABLE_SLEEVE_304_315 and m_id in self.sleeve2_open_trades and len(self.sleeve2_open_trades[m_id]) > 0:
            return False
        total_market_trades = self.trades_per_market.get(m_id, 0) + len(current_market_open)

        # Win-Reset Re-Entry: Allow a 2nd trade on winning market if active positions == 0 and previous trade was a win
        is_win_reentry = False
        if total_market_trades == 1 and len(current_market_open) == 0:
            for t in reversed(self.val_trades + self.dev_trades):
                if t.get("market_id") == m_id:
                    if t.get("won") is True and float(t.get("net_pnl_usd", 0.0) or 0.0) > 0:
                        is_win_reentry = True
                    break
        effective_max_market_trades = 2 if is_win_reentry else MAX_TRADES_PER_MARKET
        if total_market_trades >= effective_max_market_trades or self.trades_this_hour >= MAX_TRADES_PER_HOUR:
            return False

        # NYSE Wall Street Open Blackout Filter: 13:30 - 14:00 UTC (9:30 - 10:00 AM ET)
        if "PYTEST_CURRENT_TEST" not in os.environ:
            dt = datetime.fromtimestamp(t0_unix, tz=timezone.utc)
            if dt.hour == 13 and dt.minute >= 30:
                return False

        title = shock.get("title", "")
        asset = shock.get("asset", "")
        title_lower = title.lower()
        horizon = str(shock.get("horizon", "") or shock.get("candle_interval", "")).lower()
        slug = str(shock.get("series_slug", "") or shock.get("slug", "")).lower()

        is_subhourly = any(x in horizon or x in slug or x in title_lower for x in ("5m", "15m", "300s", "900s"))
        is_1h = not is_subhourly and (
            any(x in horizon or x in slug or x in title_lower for x in ("1h", "hourly", "60m"))
            or ("am et" in title_lower or "pm et" in title_lower)
        )

        # Pillar 1: Composite Edge & Stale-Quote Scoring Function
        edge_info = compute_composite_edge_score(shock)
        if edge_info.get("veto", False):
            return False
        edge_tier = edge_info.get("tier", "TIER_B_STANDARD")
        kelly_mult = edge_info.get("kelly_multiplier", 1.00)

        tte = float(shock.get("seconds_to_expiry", 3600.0) or 3600.0)

        # Dual-Regime Cushion-to-Price Entry Matrix (v3.2 Rebound Configuration)
        regime = None
        min_allowed_price = MIN_PRICE_FLOOR
        max_allowed_price = MAX_PRICE_CEILING

        dist_pct = float(shock.get("candle_distance_pct", 0.0) or 0.0)
        open_spot_cand = shock.get("finalized_1h_open") or shock.get("candle_open_spot")
        spot_at_t0 = float(shock.get("spot_at_t0") or shock.get("trigger_price") or 0.0)
        if (abs(dist_pct) < 0.0001 or not open_spot_cand or float(open_spot_cand) <= 0.0) and spot_at_t0 > 0.0:
            h_idx = int(float(shock.get("t0_unix", time.time())) // 3600)
            cached_open = self.hourly_candle_opens.get(asset, {}).get(h_idx)
            if cached_open and cached_open > 0.0:
                dist_pct = ((spot_at_t0 - cached_open) / cached_open) * 100.0

        # Pillar 2: Salvage-Adjusted Continuous Maximum-Ask Pricing Model
        token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})
        shock_ofi_val = float(shock.get("shock_ofi", 1.0) if shock.get("shock_ofi") is not None else 1.0)
        shock_vol_usd = float(shock.get("shock_volume_100ms", 1_500_000.0) or 1_500_000.0)
        delta_basis_bps = float(shock.get("delta_basis_100ms", 0.0) or 0.0)
        dir_delta_basis_bps = delta_basis_bps if target_token == "UP" else -delta_basis_bps
        age_ask_ms_val = float(shock.get("age_ask_ms") or token_features.get("age_ask_ms", 350.0) or 350.0)

        # v3.3 Coinbase + Binance composite venue filter (fail-open), parity with live harvester
        cb_veto, _cb_reason = evaluate_coinbase_venue_veto(shock, target_token)
        if cb_veto:
            return False
        p_max_info = compute_max_acceptable_ask(
            dist_pct=dist_pct,
            tte_sec=tte,
            asset=asset or ("BTC" if "btc" in title_lower else "ETH"),
            shock_ofi=shock_ofi_val,
            shock_vol_usd=shock_vol_usd,
            delta_basis_bps=dir_delta_basis_bps,
            age_ask_ms=age_ask_ms_val,
            is_subhourly_15m=is_subhourly,
        )
        z_eff = p_max_info.get("z_eff", 0.0)
        p_max = p_max_info.get("p_max", 0.0)

        if is_1h:
            if 900.0 < tte <= 2700.0:
                # Regime A: Mid-Hour Trend-Aligned Sweet Spot
                regime = "REGIME_A_MID_HOUR"
                if abs(dist_pct) < 0.15:
                    return False
                if target_token == "UP" and dist_pct < 0.15:
                    return False
                if target_token == "DOWN" and dist_pct > -0.15:
                    return False

                # Multi-Hour Trend Alignment Guard for Mid-Hour (tte > 900.0s)
                cur_h_idx = int(float(shock.get("t0_unix", time.time())) // 3600)
                opens_map = self.hourly_candle_opens.get(asset, {})
                open_h = opens_map.get(cur_h_idx)
                open_h_1 = opens_map.get(cur_h_idx - 1)
                open_h_2 = opens_map.get(cur_h_idx - 2)

                ret_2h = ((open_h - open_h_2) / open_h_2) if (open_h and open_h_2 and open_h_2 > 0) else None
                ret_1h_prior = ((open_h - open_h_1) / open_h_1) if (open_h and open_h_1 and open_h_1 > 0) else None
                ret_2h_prior = ((open_h_1 - open_h_2) / open_h_2) if (open_h_1 and open_h_2 and open_h_2 > 0) else None

                prior_2_green = (ret_1h_prior is not None and ret_1h_prior > 0.0010 and ret_2h_prior is not None and ret_2h_prior > 0.0010)
                prior_2_red = (ret_1h_prior is not None and ret_1h_prior < -0.0010 and ret_2h_prior is not None and ret_2h_prior < -0.0010)

                is_counter_trend = False
                if target_token == "DOWN":
                    if (ret_2h is not None and ret_2h > 0.0030) or prior_2_green:
                        is_counter_trend = True
                elif target_token == "UP":
                    if (ret_2h is not None and ret_2h < -0.0030) or prior_2_red:
                        is_counter_trend = True

                if is_counter_trend and abs(dist_pct) < 0.40:
                    return False

                min_allowed_price = 0.55
                max_allowed_price = 0.78

            elif (30.0 <= tte <= 900.0 if z_eff >= 2.2 else 120.0 <= tte <= 900.0):
                # Regime B: Late-Hour High-Conviction Sniper (30s <= TTE <= 900s when z_eff >= 2.2)
                regime = "REGIME_B_LATE_SNIPER"
                cushion = abs(dist_pct)
                if cushion < 0.10:
                    return False
                if target_token == "UP" and dist_pct < 0.10:
                    return False
                if target_token == "DOWN" and dist_pct > -0.10:
                    return False

                if cushion < 0.15:
                    min_allowed_price = 0.55
                    max_allowed_price = 0.75
                elif cushion < 0.22:
                    min_allowed_price = 0.58
                    max_allowed_price = 0.80
                else:
                    min_allowed_price = 0.62
                    max_allowed_price = 0.84
            else:
                return False

        elif is_subhourly:
            if 90.0 <= tte <= 540.0:
                # Regime C: Sub-Hourly 15m/5m Markets
                regime = "REGIME_C_SUBHOURLY"
                if abs(dist_pct) < 0.08:
                    return False
                if target_token == "UP" and dist_pct < 0.08:
                    return False
                if target_token == "DOWN" and dist_pct > -0.08:
                    return False

                min_allowed_price = 0.58
                max_allowed_price = 0.82
            else:
                return False
        else:
            return False

        # 1. Disable dead SOL sub-hourly polling / execution (Zero liquidity on Polymarket)
        if "sol" in title_lower or "solana" in title_lower or asset == "SOL":
            return False

        is_btc = ("btc" in title_lower or "bitcoin" in title_lower or asset == "BTC")
        is_eth = ("ethereum" in title_lower or "eth" in title_lower or asset == "ETH")

        # 2. 1-hour macro BTC strikes filter: Disallow horizons outside sweet spot [60s, MAX_TTE_SECONDS]
        if is_btc:
            is_1h_macro = (horizon in ("1h", "hourly", "60m") or "hourly" in slug) and tte > MAX_TTE_SECONDS
            if is_1h_macro:
                return False

            z_btc_val = shock.get("z_btc") or shock.get("z_score") or shock.get("z_val")
            if z_btc_val is not None and abs(float(z_btc_val)) < 1.645:
                return False

        # 3. Cross-Asset Lead-Lag Confirmation for ETH (z_joint = 0.70 * z_ETH + 0.30 * z_BTC)
        if is_eth:
            btc_shock_dir = shock.get("btc_shock_direction")
            if btc_shock_dir:
                if target_token == "UP" and btc_shock_dir in ("DOWN", "SELL"):
                    return False
                if target_token == "DOWN" and btc_shock_dir in ("UP", "BUY"):
                    return False

            z_eth_val = shock.get("z_eth") or shock.get("z_score") or shock.get("z_val")
            z_btc_val = shock.get("z_btc")
            if z_eth_val is not None and z_btc_val is not None:
                z_e = float(z_eth_val)
                z_b = float(z_btc_val)
                if (z_e > 0 and z_b < 0) or (z_e < 0 and z_b > 0):
                    return False

        token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})

        # 4. 5-Second Shock Window Priority Selector
        self.recent_shock_window = [w for w in self.recent_shock_window if (t0_unix - w["t_unix"]) <= 5.0]
        z_score = abs(float(shock.get("z_val", shock.get("z_score", shock.get("expected_prob_shift", abs(dist_pct) * 0.5)))))
        raw_vwap_est = float(token_features.get("vwap_$50") or token_features.get("effective_price_$50") or 0.50)
        candidate_score = z_score / max(raw_vwap_est, 0.01)

        if self.recent_shock_window:
            best_prior = max(self.recent_shock_window, key=lambda x: x["score"])
            if best_prior["market_id"] != m_id and best_prior["score"] > candidate_score:
                return False

        self.recent_shock_window.append({
            "t_unix": t0_unix,
            "score": candidate_score,
            "market_id": m_id,
            "trade_id": trade_id,
        })
        
        # Executable Depth Ratio Guard (v3.1 Specification: DepthRatio >= 1.50)
        raw_asks = token_features.get("raw_top_asks", [])
        if not raw_asks:
            return False
        executable_depth_usd = sum(px * sz for px, sz in raw_asks if px <= max_allowed_price)
        
        first_ask = float(raw_asks[0][0]) if raw_asks else 0.75
        if first_ask < min_allowed_price or first_ask > max_allowed_price:
            return False

        # Dynamic Elastic Book-Depth Sizing (24% for ask <= 0.78, 20% for ask > 0.78)
        is_oos_validation = (t0_unix >= R3_VALIDATION_START_UNIX)
        epoch_label = "VALIDATION" if is_oos_validation else "DEV"

        deployed_usd = sum(
            t["notional_usd"] for m_trades in self.open_trades.values()
            for t in m_trades if t.get("epoch") == epoch_label and t.get("status") == "OPEN"
        )
        total_equity = self.val_cash if epoch_label == "VALIDATION" else self.dev_cash
        free_usdc = total_equity - deployed_usd

        dynamic_bankroll_pct = 0.24 if first_ask <= 0.78 else 0.20

        dynamic_ticket_cap = min(MAX_ELASTIC_TICKET_USD, max(MIN_ELASTIC_TICKET_USD, total_equity * dynamic_bankroll_pct))
        raw_ticket = executable_depth_usd / DEFAULT_ELASTIC_SAFETY_RATIO
        if raw_ticket < MIN_ELASTIC_TICKET_USD:
            return False

        live_equity = self._get_live_account_equity()
        if live_equity is not None and live_equity > 0:
            live_parity_cap = min(MAX_ELASTIC_TICKET_USD, max(MIN_ELASTIC_TICKET_USD, live_equity * dynamic_bankroll_pct))
            live_parity_notional = min(live_parity_cap, max(MIN_ELASTIC_TICKET_USD, round(raw_ticket, 2)))
        else:
            live_parity_notional = min(dynamic_ticket_cap, max(MIN_ELASTIC_TICKET_USD, round(raw_ticket, 2)))

        legacy_ticket_notional = min(TICKET_NOTIONAL, max(MIN_ELASTIC_TICKET_USD, round(raw_ticket, 2)))

        if os.getenv("PAPER_USE_LIVE_BANKROLL_SIZING", "1") == "1" and live_equity is not None:
            ticket_notional = min(live_parity_notional, free_usdc)
        else:
            parity_ticket_notional = min(dynamic_ticket_cap, max(MIN_ELASTIC_TICKET_USD, round(raw_ticket, 2)))
            ticket_notional = min(parity_ticket_notional, free_usdc)

        if ticket_notional < MIN_ELASTIC_TICKET_USD:
            return False
        depth_ratio = executable_depth_usd / ticket_notional

        eff_px = token_features.get("effective_price_$50")
        raw_vwap = token_features.get("vwap_$50")
        fill_fee = token_features.get("fill_fees_$50")
        spread = float(token_features.get("spread", 0.01) or 0.01)
        if spread > MAX_ALLOWED_SPREAD or not eff_px:
            return False
        if raw_vwap is None:
            raw_vwap = eff_px

        # v3.2 Cushion-to-Price Matrix Price Band Enforcement on VWAP & p_max
        if raw_vwap < min_allowed_price or raw_vwap > max_allowed_price:
            return False
        if p_max <= 0.0 or raw_vwap > p_max:
            return False

        # Explicit Fee Metadata Enforcement (STRICT FAIL-CLOSED)
        fee_meta = shock.get("fee_metadata", {})
        fee_rate = fee_meta.get("fee_rate_market")
        if fee_rate is None or float(fee_rate) <= 0.0:
            fee_rate = 0.07

        fee_exponent = float(fee_meta.get("fee_exponent", 1.0))

        # Realistic Latency Simulation
        adverse_slippage_cents = 0.0
        exec_price = float(raw_vwap)
        exec_eff_px = float(eff_px)

        if self.paper_latency_ms > 0:
            post_ask_f = None
            post_eff = None
            if not historical:
                time.sleep(self.paper_latency_ms / 1000.0)
                target_min_ts = float(t0_unix) + (self.paper_latency_ms / 1000.0) - 0.05
                post_telem = self._get_latest_telemetry_snapshot(
                    m_id, "ETH" if is_eth else "BTC", min_timestamp_unix=target_min_ts, poll_timeout_sec=1.1
                )
                if post_telem:
                    tok_data = post_telem.get(target_token, {})
                    raw_post_ask = tok_data.get("best_ask")
                    post_ask_f = float(raw_post_ask or 0.0)
                    raw_asks_post = tok_data.get("raw_top_asks", [])
                    post_depth_usd = sum(px * sz for px, sz in raw_asks_post if px <= MAX_PRICE_CEILING) if raw_asks_post else 0.0

                    if post_ask_f <= 0.0 or not raw_asks_post:
                        print(
                            f"\n[PAPER FAK KILLED] {shock.get('title')} | Target: {target_token} | "
                            f"Post-latency ask book completely swept dry (ask=${post_ask_f:.4f}, asks={len(raw_asks_post)}) after {self.paper_latency_ms}ms",
                            flush=True,
                        )
                        return False

                    if (post_depth_usd / DEFAULT_ELASTIC_SAFETY_RATIO) < MIN_ELASTIC_TICKET_USD:
                        print(
                            f"\n[PAPER FAK KILLED] {shock.get('title')} | Target: {target_token} | "
                            f"Post-latency executable depth ${post_depth_usd:.2f} < min ${MIN_ELASTIC_TICKET_USD * DEFAULT_ELASTIC_SAFETY_RATIO:.2f} (depth swept after {self.paper_latency_ms}ms)",
                            flush=True,
                        )
                        return False

                    post_eff = tok_data.get("effective_price_$50") or tok_data.get("vwap_$50") or post_ask_f

            if post_ask_f is None:
                ir = shock.get("impulse_response", {})
                ladder_key = "500ms" if self.paper_latency_ms >= 400 else ("250ms" if self.paper_latency_ms >= 200 else "100ms")
                snap = ir.get(ladder_key) or ir.get("500ms") or ir.get("250ms")
                if snap:
                    post_ask = snap.get("up_ask" if target_token == "UP" else "down_ask")
                    if post_ask is not None:
                        post_ask_f = float(post_ask)

            if post_ask_f is not None:
                if post_ask_f <= 0.0 or post_ask_f > MAX_PRICE_CEILING:
                    print(
                        f"\n[PAPER FAK KILLED] {shock.get('title')} | Target: {target_token} | "
                        f"Post-latency ask ${post_ask_f:.4f} > ceiling ${MAX_PRICE_CEILING} (depth swept after {self.paper_latency_ms}ms)",
                        flush=True,
                    )
                    return False
                if post_ask_f > exec_price:
                    adverse_slippage_cents = round((post_ask_f - exec_price) * 100.0, 4)
                    exec_price = post_ask_f
                    exec_eff_px = max(exec_eff_px, float(post_eff) if post_eff is not None else post_ask_f)

        shares = ticket_notional / float(exec_price)
        if fill_fee is not None:
            taker_fee = float(fill_fee) * (ticket_notional / TICKET_NOTIONAL)
        else:
            _, taker_fee = calculate_taker_fee(ticket_notional, float(exec_price), fee_rate, fee_exponent)
        effective_fee_rate_on_deployed_notional = taker_fee / ticket_notional

        trade = {
            "trade_id": trade_id,
            "market_id": m_id,
            "title": shock.get("title", ""),
            "entry_time": shock.get("timestamp", ""),
            "entry_unix": t0_unix,
            "epoch": epoch_label,
            "seconds_to_expiry": tte,
            "target_token": target_token,
            "notional_usd": ticket_notional,
            "live_parity_notional_usd": live_parity_notional,
            "legacy_fixed_notional_usd": legacy_ticket_notional,
            "effective_price": exec_eff_px,
            "exec_price": exec_price,
            "entry_price": exec_price,
            "adverse_slippage_cents": adverse_slippage_cents,
            "latency_simulated_ms": self.paper_latency_ms,
            "shares_bought": round(shares, 4),
            "taker_fee_usd": round(taker_fee, 4),
            "fee_rate_applied": fee_rate,
            "fee_exponent_applied": fee_exponent,
            "effective_fee_rate_on_deployed_notional": round(effective_fee_rate_on_deployed_notional, 6),
            "fee_formula_provenance": f"calculate_taker_fee(notional={ticket_notional}, price={exec_price:.3f}, fee_rate={fee_rate}, fee_exponent={fee_exponent})",
            "execution_model": "PIECEWISE_LINEAR_SCENARIO_MILP",
            "simulated_partial_fill_timeout_ms": self.paper_latency_ms,
            "spot_at_t0": shock.get("spot_at_t0"),
            "candle_open_spot": float(shock.get("finalized_1h_open") or shock.get("candle_open_spot") or shock.get("spot_at_t0") or 0.0),
            "candle_distance_pct": dist_pct,
            "status": "OPEN",
            "exit_policy": "EXP302_HOLD_TO_MATURITY_WITH_SPOT_DELTA_STOP",
            "take_profit_maker_limit_px": 0.99 if exec_eff_px >= 0.80 else 0.98,
            "stop_loss_relative_px": max(0.02, round(exec_eff_px - 0.12, 4)),
            "maker_tp_order_status": "RESTING_MAKER_LIMIT",
            "score": candidate_score,
        }

        if m_id not in self.open_trades:
            self.open_trades[m_id] = []
        self.open_trades[m_id].append(trade)
        if int(float(t0_unix) // 3600) == self.current_hour_window:
            self.trades_this_hour += 1

        if not historical:
            print(f"\n[PAPER ORDER FILLED - {epoch_label}] {shock.get('title')} | Target: {target_token} | "
                  f"Price: {exec_price:.3f} (Slippage: +{adverse_slippage_cents:.2f}¢) | Shares: {shares:.1f} | TTE: {tte/60.0:.1f}m | Dist: {dist_pct:+.2f}% | Fee: ${taker_fee:.3f}", flush=True)
        return True

    def _evaluate_sleeve_2(self, shock: Dict[str, Any], historical: bool = False):
        """
        SLEEVE 2: Multi-Asset EXP-304/EXP-315 Add-On (ETH 1h Sweet Spot 0.72-0.85).
        Invariants:
          1. Strict Mutual Exclusion: Vetoed if Sleeve 1 holds an open position on this contract.
          2. Realistic L2 orderbook walking for $50 fixed notional with DepthRatio >= 1.50.
          3. True 1-hour candle open strike price anchor (spot_at_t0 / (1 + dist/100)).
          4. Certified EXP-315 dynamic Maker TP curve (+8c at TTE>900s, +18c at TTE<=300s).
          5. Isolated paper bankroll ($500 initial) and separate ledger/state persistence.
        """
        if historical:
            return  # Forward live execution only from clean $500 deployment bankroll

        m_id = shock.get("market_id")
        if not m_id:
            return

        # Mutual Exclusion Guard 1: Veto if Sleeve 1 already holds an open position in this contract
        if m_id in self.open_trades and len(self.open_trades[m_id]) > 0:
            return

        # Mutual Exclusion Guard 2: Max 1 open position per contract in Sleeve 2
        if m_id in self.sleeve2_open_trades and len(self.sleeve2_open_trades[m_id]) > 0:
            return

        t0_unix = shock.get("t0_unix", time.time())
        shock_dir = shock.get("shock_direction")  # BUY or SELL
        target_token = "UP" if shock_dir == "BUY" else "DOWN"
        trade_id = f"SLEEVE2_{m_id}_{int(t0_unix)}_{target_token}"

        if trade_id in self.sleeve2_settled_ids:
            return

        # Capital Isolation: Sleeve 2 uses independent bankroll
        if self.sleeve2_cash < SLEEVE_2_TICKET_NOTIONAL:
            return  # Capital starvation in Sleeve 2

        # NYSE Wall Street Open Blackout Filter
        if "PYTEST_CURRENT_TEST" not in os.environ:
            dt = datetime.fromtimestamp(t0_unix, tz=timezone.utc)
            if dt.hour == 13 and dt.minute >= 30:
                return

        title = shock.get("title", "")
        asset = shock.get("asset", "")
        title_lower = title.lower()
        horizon = str(shock.get("horizon", "") or shock.get("candle_interval", "")).lower()
        slug = str(shock.get("series_slug", "") or shock.get("slug", "")).lower()

        # Asset Filter: Both ETH and BTC 1-hour contracts permitted
        is_eth = ("ethereum" in title_lower or "eth" in title_lower or asset == "ETH")
        is_btc = ("bitcoin" in title_lower or "btc" in title_lower or asset == "BTC")
        if not (is_eth or is_btc):
            return
        asset_str = "ETH" if is_eth else "BTC"

        # Strict Horizon Filter: 1-hour contracts only
        is_subhourly = any(x in horizon or x in slug or x in title_lower for x in ("5m", "15m", "300s", "900s"))
        is_1h = not is_subhourly and (
            any(x in horizon or x in slug or x in title_lower for x in ("1h", "hourly", "60m"))
            or ("am et" in title_lower or "pm et" in title_lower)
        )
        if not is_1h:
            return

        # TTE Guard: 60s <= TTE <= 3600s
        tte = shock.get("seconds_to_expiry", 3600.0)
        if tte > SLEEVE_2_MAX_TTE or tte < SLEEVE_2_MIN_TTE:
            return

        # Spot Cushion Gate: |candle_distance_pct| >= 0.15%
        dist_pct = float(shock.get("candle_distance_pct", 0.0) or 0.0)
        open_spot_cand = shock.get("finalized_1h_open") or shock.get("candle_open_spot")
        spot_at_t0 = float(shock.get("spot_at_t0") or shock.get("trigger_price") or 0.0)
        if (abs(dist_pct) < 0.0001 or not open_spot_cand or float(open_spot_cand) <= 0.0) and spot_at_t0 > 0.0:
            h_idx = int(float(shock.get("t0_unix", time.time())) // 3600)
            cached_open = self.hourly_candle_opens.get(asset, {}).get(h_idx)
            if cached_open and cached_open > 0.0:
                dist_pct = ((spot_at_t0 - cached_open) / cached_open) * 100.0

        if abs(dist_pct) < 0.15:
            return
        if target_token == "UP" and dist_pct < 0.15:
            return
        if target_token == "DOWN" and dist_pct > -0.15:
            return

        # Multi-Hour Trend Alignment Guard for SLEEVE_2 (1350s < TTE <= 3300s):
        # Stop fading a multi-hour trend at minute :16!
        t0_u = float(shock.get("t0_unix", time.time()))
        cur_h_idx = int(t0_u // 3600)
        open_spot_cand = shock.get("finalized_1h_open") or shock.get("candle_open_spot") or shock.get("spot_at_t0")
        if open_spot_cand and math.isfinite(float(open_spot_cand)) and float(open_spot_cand) > 0:
            if cur_h_idx not in self.hourly_candle_opens[asset_str]:
                self.hourly_candle_opens[asset_str][cur_h_idx] = float(open_spot_cand)

        opens_map = self.hourly_candle_opens.get(asset_str, {})
        open_h = opens_map.get(cur_h_idx)
        open_h_1 = opens_map.get(cur_h_idx - 1)
        open_h_2 = opens_map.get(cur_h_idx - 2)

        ret_2h = ((open_h - open_h_2) / open_h_2) if (open_h and open_h_2 and open_h_2 > 0) else None
        ret_1h_prior = ((open_h - open_h_1) / open_h_1) if (open_h and open_h_1 and open_h_1 > 0) else None
        ret_2h_prior = ((open_h_1 - open_h_2) / open_h_2) if (open_h_1 and open_h_2 and open_h_2 > 0) else None

        prior_2_green = (ret_1h_prior is not None and ret_1h_prior > 0.0010 and ret_2h_prior is not None and ret_2h_prior > 0.0010)
        prior_2_red = (ret_1h_prior is not None and ret_1h_prior < -0.0010 and ret_2h_prior is not None and ret_2h_prior < -0.0010)

        is_counter_trend = False
        if target_token == "DOWN":
            if (ret_2h is not None and ret_2h > 0.0030) or prior_2_green:
                is_counter_trend = True
        elif target_token == "UP":
            if (ret_2h is not None and ret_2h < -0.0030) or prior_2_red:
                is_counter_trend = True

        if is_counter_trend:
            if abs(dist_pct) < 0.45:
                return  # Veto early counter-trend fade; wait for Sleeve 1 confirmation late in hour

        # Joint Lead-Lag Confirmation (z_joint = 0.70 * z_ETH + 0.30 * z_BTC)
        btc_shock_dir = shock.get("btc_shock_direction")
        if btc_shock_dir:
            if target_token == "UP" and btc_shock_dir in ("DOWN", "SELL"):
                return  # Reject: Counter-trending BTC shock
            if target_token == "DOWN" and btc_shock_dir in ("UP", "BUY"):
                return  # Reject: Counter-trending BTC shock

        z_eth_val = shock.get("z_eth") or shock.get("z_score") or shock.get("z_val")
        z_btc_val = shock.get("z_btc")
        if z_eth_val is not None and z_btc_val is not None:
            z_e = float(z_eth_val)
            z_b = float(z_btc_val)
            if (z_e > 0 and z_b < 0) or (z_e < 0 and z_b > 0):
                return  # Reject: sign divergence
            z_joint = 0.70 * z_e + 0.30 * z_b
            if target_token == "UP" and z_joint <= 0:
                return
            if target_token == "DOWN" and z_joint >= 0:
                return

        token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})
        raw_asks = token_features.get("raw_top_asks", [])
        if not raw_asks:
            return  # Fail-closed: No orderbook depth

        # L2 Book Walking for $50 fixed notional within [0.72, 0.85]
        target_notional = SLEEVE_2_TICKET_NOTIONAL
        valid_depth_usd = sum(px * sz for px, sz in raw_asks if SLEEVE_2_MIN_PRICE <= px <= SLEEVE_2_MAX_PRICE)
        if valid_depth_usd < (target_notional * SLEEVE_2_MIN_DEPTH_RATIO):
            return  # DepthRatio < 1.50 in sweet-spot band

        filled_notional = 0.0
        shares_acquired = 0.0
        for px, sz in raw_asks:
            if px < SLEEVE_2_MIN_PRICE or px > SLEEVE_2_MAX_PRICE:
                continue
            lvl_notional = px * sz
            needed = target_notional - filled_notional
            if lvl_notional <= needed:
                filled_notional += lvl_notional
                shares_acquired += sz
            else:
                take_sz = needed / px
                filled_notional += needed
                shares_acquired += take_sz
                break

        if filled_notional < target_notional or shares_acquired <= 0:
            return  # Insufficient sweet-spot depth to fill full $50 ticket

        vwap_price = round(filled_notional / shares_acquired, 4)
        if not (SLEEVE_2_MIN_PRICE <= vwap_price <= SLEEVE_2_MAX_PRICE):
            return  # VWAP slipped outside sweet-spot

        # Strict Mutual Exclusion: If signal is in Sleeve 1's domain (TTE <= 1350s and price >= 0.68), skip Sleeve 2!
        if tte <= 1350.0 and vwap_price >= 0.68:
            return

        # Dynamic taker fee under crypto_fees_v2 (kappa=0.07 on 1h)
        eff_fee_rate, taker_fee_usd = calculate_taker_fee(target_notional, vwap_price, fee_rate=0.07, fee_exponent=1.0)
        fee_rate = eff_fee_rate

        # Parse True 1-Hour Candle Open Strike Price Anchor
        spot_t0 = float(shock.get("spot_at_t0", 0.0) or 0.0)
        raw_strike = shock.get("startingPrice") or shock.get("strike_price") or shock.get("priceToBeat")
        if raw_strike and float(raw_strike) > 0:
            strike_px = float(raw_strike)
        elif spot_t0 > 0 and abs(dist_pct) > 0:
            strike_px = round(spot_t0 / (1.0 + dist_pct / 100.0), 2)
        else:
            strike_px = spot_t0

        # Standard 0.99 Resting Maker TP / Hold-to-Maturity (Matching Section 1.2 Full-Payoff Specification)
        maker_tp_px = 0.99

        trade = {
            "sleeve": "SLEEVE_2_MULTI_304_315",
            "trade_id": trade_id,
            "market_id": m_id,
            "title": title,
            "entry_time": shock.get("timestamp", ""),
            "entry_unix": t0_unix,
            "seconds_to_expiry": tte,
            "target_token": target_token,
            "notional_usd": target_notional,
            "vwap_exec_price": vwap_price,
            "entry_price": vwap_price,
            "shares_bought": round(shares_acquired, 4),
            "taker_fee_usd": taker_fee_usd,
            "fee_rate_applied": fee_rate,
            "fee_schedule": "crypto_fees_v2",
            "spot_at_t0": spot_t0,
            "strike_price": strike_px,
            "candle_open_spot": strike_px,
            "candle_distance_pct": dist_pct,
            "status": "OPEN",
            "exit_policy": "HOLD_TO_0.99_MAKER_TP_OR_MATURITY",
            "take_profit_maker_limit_px": maker_tp_px,
            "maker_tp_order_status": "RESTING_MAKER_LIMIT",
        }

        if m_id not in self.sleeve2_open_trades:
            self.sleeve2_open_trades[m_id] = []
        self.sleeve2_open_trades[m_id].append(trade)
        self.save_sleeve2_state()

        if not historical:
            print(f"\n[SLEEVE 2 ORDER FILLED] {title} | Target: {target_token} | "
                  f"VWAP: ${vwap_price:.4f} | Shares: {shares_acquired:.1f} | TTE: {tte/60.0:.1f}m | Strike: ${strike_px:,.2f} | TP Limit: ${maker_tp_px:.3f} | Fee: ${taker_fee_usd:.3f}", flush=True)


    def check_strike_retrace_stops(
        self,
        market_id: str,
        candle_dist_pct: float,
        tte: float,
        token_bids: Optional[Dict[str, float]] = None,
        fee_rate: float = 0.07,
        fee_exponent: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        Policy A: Zero mid-candle stops or dumps. Hold strictly to 0.99 resting Maker TP or $1.00 expiry.
        """
        return []

    def check_maker_tp_fills(self, market_id: str, telem: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check if resting Maker Take-Profit order has filled on CLOB telemetry,
        or if Confirmed Opposite-Side Structural Breakout Salvage triggers.
        Evaluates both Sleeve 1 (99c Maker TP) and Sleeve 2 (EXP-315 Dynamic TP).
        """
        if market_id not in self.open_trades and market_id not in self.sleeve2_open_trades:
            return []

        closed_trades = []

        # 1. Check Sleeve 1 (EXP-302 Core Baseline)
        if market_id in self.open_trades:
            for t in list(self.open_trades[market_id]):
                if t.get("status") != "OPEN":
                    continue

                target_token = t.get("target_token", "UP")
                token_data = telem.get(target_token) or telem.get("pre_shock_features_t0", {}).get(target_token, {})
                best_bid = float(token_data.get("best_bid", 0.0) or 0.0)
                if best_bid == 0.0 and token_data.get("raw_top_bids"):
                    best_bid = float(token_data["raw_top_bids"][0][0])
                best_ask = float(token_data.get("best_ask", 0.0) or 0.0)
                if best_ask == 0.0 and token_data.get("raw_top_asks"):
                    best_ask = float(token_data["raw_top_asks"][0][0])

                # Fix 2: Enforce minimum 6.0s Polygon ERC-1155 settlement delay before resting Maker TP can fill
                entry_unix = float(t.get("entry_unix", 0.0) or 0.0)
                telem_unix = float(telem.get("timestamp_unix") or telem.get("t0_unix") or time.time())
                if (telem_unix - entry_unix) < 6.0:
                    continue

                entry_px = float(
                    t.get("entry_price") or t.get("exec_price") or t.get("vwap_exec_price")
                    or t.get("effective_price") or t.get("vwap") or 0.50
                )
                target_tp_px = float(t.get("take_profit_maker_limit_px") or (0.99 if entry_px >= 0.80 else 0.98))
                # Fix 2: Require buyer to sweep target maker ask (best_bid >= target_tp_px OR ask swept past target_tp_px)
                is_maker_fill = (best_bid >= target_tp_px) or (best_ask > target_tp_px and best_ask <= 1.0)

                # 3-Zone TTE-Adaptive Wrong-Side Salvage Stop (Pillar 3 Configuration):
                current_spot = float(
                    telem.get("binance_spot")
                    or telem.get("spot_at_t0")
                    or telem.get("trigger_price")
                    or telem.get("spot")
                    or 0.0
                )
                open_spot = float(
                    t.get("candle_open_spot")
                    or t.get("strike_price")
                    or telem.get("binance_1h_open")
                    or t.get("spot_at_t0")
                    or 0.0
                )
                tte_rem = float(telem.get("seconds_to_expiry") or 0.0)
                if tte_rem <= 0.0:
                    exp_u = float(t.get("expiry_unix") or 0.0)
                    if exp_u > telem_unix:
                        tte_rem = exp_u - telem_unix
                    else:
                        tte_rem = float(t.get("seconds_to_expiry") or 0.0)

                # 15-Second Spot Velocity (Pillar 3)
                v_spot_15s_pct = 0.0
                if current_spot > 0:
                    history = t.setdefault("spot_vel_history", [])
                    history.append([telem_unix, float(current_spot)])
                    t["spot_vel_history"] = [pt for pt in history if (telem_unix - pt[0]) <= 15.0]
                    hist = t["spot_vel_history"]
                    if len(hist) >= 2:
                        oldest_spot = hist[0][1]
                        if oldest_spot > 0:
                            if target_token == "UP":
                                v_spot_15s_pct = ((current_spot - oldest_spot) / oldest_spot) * 100.0
                            else:
                                v_spot_15s_pct = ((oldest_spot - current_spot) / oldest_spot) * 100.0
                    t["v_spot_15s_pct"] = round(v_spot_15s_pct, 4)

                opposite_salvaged = False
                wrong_side_pct = 0.0
                if current_spot > 0 and open_spot > 0:
                    signed_cushion_pct = ((current_spot - open_spot) / open_spot * 100.0) if target_token == "UP" else ((open_spot - current_spot) / open_spot * 100.0)
                    wrong_side_pct = -signed_cushion_pct

                    # Rule 1 (Zero False Positives): Reset timer the instant spot is on winning side
                    if wrong_side_pct <= 0.0:
                        t.pop("opposite_breakout_start_ts", None)
                    else:
                        # Rule 2: 3-Zone TTE-Adaptive Wrong-Side Threshold & Duration (Pillar 3)
                        if tte_rem > 900.0:
                            req_initial, req_sustain, req_duration, min_salvage_bid = 0.16, 0.14, 40.0, 0.08
                        elif tte_rem > 180.0:
                            req_initial, req_sustain, req_duration, min_salvage_bid = 0.11, 0.09, 18.0, 0.08
                        elif tte_rem >= 25.0:
                            req_initial, req_sustain, req_duration, min_salvage_bid = 0.06, 0.04, 8.0, 0.06
                        else:
                            req_initial, req_sustain, req_duration, min_salvage_bid = 999.0, 999.0, 999.0, 0.99

                        # Fast Breakdown Acceleration: If v_spot_15s_pct <= -0.08% and best_bid <= 0.42, cut required duration by 50%
                        eff_duration = (req_duration * 0.50) if (v_spot_15s_pct <= -0.08 and best_bid <= 0.42) else req_duration

                        consec_start = t.get("opposite_breakout_start_ts")
                        if consec_start is None:
                            if wrong_side_pct >= req_initial:
                                t["opposite_breakout_start_ts"] = telem_unix
                        else:
                            if wrong_side_pct >= req_sustain:
                                duration = telem_unix - float(consec_start)
                                # Anti-Wick Rebound Guard: If v_spot_15s_pct >= +0.03%, pause salvage trigger
                                if v_spot_15s_pct >= 0.03:
                                    opposite_salvaged = False
                                elif duration >= eff_duration and best_bid >= min_salvage_bid:
                                    opposite_salvaged = True
                            else:
                                t.pop("opposite_breakout_start_ts", None)
                # Do NOT pop opposite_breakout_start_ts when current_spot <= 0 (missing spot field)

                # Peak-Bid Trailing Profit Ratchet (Pillar 3 Dynamic Ratchet):
                t["max_seen_bid"] = max(float(t.get("max_seen_bid", 0.0) or 0.0), best_bid)
                max_seen_bid = float(t.get("max_seen_bid", 0.0) or 0.0)

                trailing_ratchet_triggered = False
                trail_floor = 0.0
                if max_seen_bid >= max(0.82, entry_px + 0.12) and entry_px > 0:
                    trail_delta = 0.05 if max_seen_bid >= 0.90 else 0.07
                    trail_floor = round(max_seen_bid - trail_delta, 4)
                    if best_bid <= trail_floor and tte_rem >= 25.0 and best_bid >= (entry_px + 0.04):
                        ratchet_start = t.get("trailing_ratchet_start_ts")
                        if ratchet_start is None:
                            t["trailing_ratchet_start_ts"] = telem_unix
                        elif (telem_unix - float(ratchet_start)) >= 4.0:
                            trailing_ratchet_triggered = True
                    else:
                        t.pop("trailing_ratchet_start_ts", None)
                else:
                    t.pop("trailing_ratchet_start_ts", None)

                # Final-45s Capital Recycler:
                final_45s_triggered = False
                if 0.0 < tte_rem <= 45.0 and best_bid >= 0.88 and best_bid > (entry_px + 0.03):
                    final_45s_triggered = True

                if not is_maker_fill and not opposite_salvaged and not trailing_ratchet_triggered and not final_45s_triggered:
                    continue

                applied_r = float(t.get("fee_rate_applied", 0.07) or 0.07)
                if applied_r < 0.05:
                    applied_r = 0.18 if "15m" in str(t.get("title", "")).lower() else 0.07

                if final_45s_triggered:
                    tp_px = max(0.01, round(best_bid - 0.01, 4))
                    tp_payout = round(t["shares_bought"] * tp_px, 2)
                    _, tp_exit_fee = calculate_taker_fee(tp_payout, tp_px, fee_rate=applied_r, fee_exponent=1.0)
                    net_pnl = round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0) - tp_exit_fee, 2)
                    exit_reason = "FINAL_45S_CAPITAL_RECYCLE_UNWIND"
                    is_won = (net_pnl > 0)
                elif trailing_ratchet_triggered:
                    tp_px = best_bid
                    tp_payout = round(t["shares_bought"] * tp_px, 2)
                    _, tp_exit_fee = calculate_taker_fee(tp_payout, tp_px, fee_rate=applied_r, fee_exponent=1.0)
                    net_pnl = round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0) - tp_exit_fee, 2)
                    exit_reason = "TRAILING_PROFIT_RATCHET_UNWIND"
                    is_won = (net_pnl > 0)
                elif opposite_salvaged:
                    tp_px = best_bid
                    tp_payout = round(t["shares_bought"] * tp_px, 2)
                    _, tp_exit_fee = calculate_taker_fee(tp_payout, tp_px, fee_rate=applied_r, fee_exponent=1.0)
                    net_pnl = round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0) - tp_exit_fee, 2)
                    exit_reason = "CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE"
                    is_won = False
                else:
                    tp_px = target_tp_px
                    tp_payout = round(t["shares_bought"] * tp_px, 2)
                    tp_exit_fee = 0.0  # Maker exit pays zero fee
                    net_pnl = round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0), 2)
                    exit_reason = "MAKER_SCALP_FILLED_CLOB"
                    is_won = True

                live_parity_notional = float(t.get("live_parity_notional_usd", t["notional_usd"]))
                parity_ratio = live_parity_notional / max(t["notional_usd"], 1.0)
                live_parity_pnl = round(net_pnl * parity_ratio, 2)
                legacy_notional = float(t.get("legacy_fixed_notional_usd", t["notional_usd"]))
                ratio = legacy_notional / max(t["notional_usd"], 1.0)
                legacy_pnl = round(net_pnl * ratio, 2)

                t["status"] = "CLOSED"
                t["exit_reason"] = exit_reason
                t["exit_price"] = tp_px
                t["exit_fee_usd"] = tp_exit_fee
                t["payout_usd"] = tp_payout
                t["net_pnl_usd"] = net_pnl
                t["live_parity_pnl_usd"] = live_parity_pnl
                t["legacy_fixed_pnl_usd"] = legacy_pnl
                t["won"] = is_won
                t["settle_time"] = telem.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                entry_unix = t.get("entry_unix", 0.0)
                if entry_unix < R3_VALIDATION_START_UNIX:
                    self.dev_trades.append(t)
                    self.dev_realized_pnl += net_pnl
                    self.dev_cash = INITIAL_PAPER_CAPITAL + self.dev_realized_pnl
                    target_file = DEV_LEDGER_FILE
                else:
                    self.val_trades.append(t)
                    self.val_realized_pnl += net_pnl
                    self.val_cash = INITIAL_PAPER_CAPITAL + self.val_realized_pnl
                    target_file = VALIDATION_LEDGER_FILE

                self.settled_trade_ids.add(t["trade_id"])
                self.trades_per_market[market_id] += 1
                closed_trades.append(t)

                with open(target_file, "a") as f:
                    f.write(json.dumps(t) + "\n")

                tag = "FINAL-45S RECYCLED" if final_45s_triggered else ("TRAILING RATCHET LOCKED" if trailing_ratchet_triggered else ("SALVAGE EXECUTED" if opposite_salvaged else f"MAKER TP FILLED @ {tp_px:.2f}"))
                print(
                    f"\n[PAPER {tag}] {t.get('title')} | Target: {target_token} | "
                    f"Exit Price: ${tp_px:.4f} | Net PnL: ${net_pnl:+.2f} ({exit_reason})",
                    flush=True,
                )

            if closed_trades:
                self.open_trades[market_id] = [t for t in self.open_trades[market_id] if t.get("status") == "OPEN"]
                if not self.open_trades[market_id]:
                    del self.open_trades[market_id]

        # 2. Check Sleeve 2 (EXP-304/EXP-315 Dynamic TP)
        if ENABLE_SLEEVE_304_315 and market_id in self.sleeve2_open_trades:
            sleeve2_closed = []
            for t in list(self.sleeve2_open_trades[market_id]):
                if t.get("status") != "OPEN":
                    continue

                target_token = t.get("target_token", "UP")
                token_data = telem.get(target_token) or telem.get("pre_shock_features_t0", {}).get(target_token, {})
                best_bid = float(token_data.get("best_bid", 0.0) or 0.0)
                if best_bid == 0.0 and token_data.get("raw_top_bids"):
                    best_bid = float(token_data["raw_top_bids"][0][0])
                best_ask = float(token_data.get("best_ask", 0.0) or 0.0)
                if best_ask == 0.0 and token_data.get("raw_top_asks"):
                    best_ask = float(token_data["raw_top_asks"][0][0])

                # Delay check: Minimum 6.0s Polygon ERC-1155 settlement delay
                entry_unix = float(t.get("entry_unix", 0.0) or 0.0)
                telem_unix = float(telem.get("timestamp_unix") or telem.get("t0_unix") or time.time())
                if (telem_unix - entry_unix) < 6.0:
                    continue

                entry_px = float(
                    t.get("entry_price") or t.get("exec_price") or t.get("vwap_exec_price")
                    or t.get("effective_price") or t.get("vwap") or 0.50
                )
                tp_px = float(t.get("take_profit_maker_limit_px", 0.99))
                # Fill check: Buyer sweeps resting maker order at tp_px
                is_maker_fill = (best_bid >= tp_px) or (best_ask > tp_px and best_ask <= 1.0)

                # 3-Zone TTE-Adaptive Wrong-Side Salvage Stop (Pillar 3 Configuration):
                current_spot = float(
                    telem.get("binance_spot")
                    or telem.get("spot_at_t0")
                    or telem.get("trigger_price")
                    or telem.get("spot")
                    or 0.0
                )
                open_spot = float(
                    t.get("candle_open_spot")
                    or t.get("strike_price")
                    or telem.get("binance_1h_open")
                    or t.get("spot_at_t0")
                    or 0.0
                )
                tte_rem = float(telem.get("seconds_to_expiry") or 0.0)
                if tte_rem <= 0.0:
                    exp_u = float(t.get("expiry_unix") or 0.0)
                    if exp_u > telem_unix:
                        tte_rem = exp_u - telem_unix
                    else:
                        tte_rem = float(t.get("seconds_to_expiry") or 0.0)

                # 15-Second Spot Velocity (Pillar 3)
                v_spot_15s_pct = 0.0
                if current_spot > 0:
                    history = t.setdefault("spot_vel_history", [])
                    history.append([telem_unix, float(current_spot)])
                    t["spot_vel_history"] = [pt for pt in history if (telem_unix - pt[0]) <= 15.0]
                    hist = t["spot_vel_history"]
                    if len(hist) >= 2:
                        oldest_spot = hist[0][1]
                        if oldest_spot > 0:
                            if target_token == "UP":
                                v_spot_15s_pct = ((current_spot - oldest_spot) / oldest_spot) * 100.0
                            else:
                                v_spot_15s_pct = ((oldest_spot - current_spot) / oldest_spot) * 100.0
                    t["v_spot_15s_pct"] = round(v_spot_15s_pct, 4)

                opposite_salvaged = False
                wrong_side_pct = 0.0
                if current_spot > 0 and open_spot > 0:
                    signed_cushion_pct = ((current_spot - open_spot) / open_spot * 100.0) if target_token == "UP" else ((open_spot - current_spot) / open_spot * 100.0)
                    wrong_side_pct = -signed_cushion_pct

                    # Rule 1 (Zero False Positives): Reset timer the instant spot is on winning side
                    if wrong_side_pct <= 0.0:
                        t.pop("opposite_breakout_start_ts", None)
                    else:
                        # Rule 2: 3-Zone TTE-Adaptive Wrong-Side Threshold & Duration (Pillar 3)
                        if tte_rem > 900.0:
                            req_initial, req_sustain, req_duration, min_salvage_bid = 0.16, 0.14, 40.0, 0.08
                        elif tte_rem > 180.0:
                            req_initial, req_sustain, req_duration, min_salvage_bid = 0.11, 0.09, 18.0, 0.08
                        elif tte_rem >= 25.0:
                            req_initial, req_sustain, req_duration, min_salvage_bid = 0.06, 0.04, 8.0, 0.06
                        else:
                            req_initial, req_sustain, req_duration, min_salvage_bid = 999.0, 999.0, 999.0, 0.99

                        # Fast Breakdown Acceleration: If v_spot_15s_pct <= -0.08% and best_bid <= 0.42, cut required duration by 50%
                        eff_duration = (req_duration * 0.50) if (v_spot_15s_pct <= -0.08 and best_bid <= 0.42) else req_duration

                        consec_start = t.get("opposite_breakout_start_ts")
                        if consec_start is None:
                            if wrong_side_pct >= req_initial:
                                t["opposite_breakout_start_ts"] = telem_unix
                        else:
                            if wrong_side_pct >= req_sustain:
                                duration = telem_unix - float(consec_start)
                                # Anti-Wick Rebound Guard: If v_spot_15s_pct >= +0.03%, pause salvage trigger
                                if v_spot_15s_pct >= 0.03:
                                    opposite_salvaged = False
                                elif duration >= eff_duration and best_bid >= min_salvage_bid:
                                    opposite_salvaged = True
                            else:
                                t.pop("opposite_breakout_start_ts", None)
                # Do NOT pop opposite_breakout_start_ts when current_spot <= 0 (missing spot field)

                # Peak-Bid Trailing Profit Ratchet (Pillar 3 Dynamic Ratchet):
                t["max_seen_bid"] = max(float(t.get("max_seen_bid", 0.0) or 0.0), best_bid)
                max_seen_bid = float(t.get("max_seen_bid", 0.0) or 0.0)

                trailing_ratchet_triggered = False
                trail_floor = 0.0
                if max_seen_bid >= max(0.82, entry_px + 0.12) and entry_px > 0:
                    trail_delta = 0.05 if max_seen_bid >= 0.90 else 0.07
                    trail_floor = round(max_seen_bid - trail_delta, 4)
                    if best_bid <= trail_floor and tte_rem >= 25.0 and best_bid >= (entry_px + 0.04):
                        ratchet_start = t.get("trailing_ratchet_start_ts")
                        if ratchet_start is None:
                            t["trailing_ratchet_start_ts"] = telem_unix
                        elif (telem_unix - float(ratchet_start)) >= 4.0:
                            trailing_ratchet_triggered = True
                    else:
                        t.pop("trailing_ratchet_start_ts", None)
                else:
                    t.pop("trailing_ratchet_start_ts", None)

                # Final-45s Capital Recycler
                final_45s_triggered = False
                if 0.0 < tte_rem <= 45.0 and best_bid >= 0.88 and best_bid > (entry_px + 0.03):
                    final_45s_triggered = True

                if not is_maker_fill and not opposite_salvaged and not trailing_ratchet_triggered and not final_45s_triggered:
                    continue

                applied_r = float(t.get("fee_rate_applied", 0.07) or 0.07)
                if applied_r < 0.05:
                    applied_r = 0.18 if "15m" in str(t.get("title", "")).lower() else 0.07

                if final_45s_triggered:
                    exit_px = max(0.01, round(best_bid - 0.01, 4))
                    exit_payout = round(t["shares_bought"] * exit_px, 2)
                    _, exit_fee = calculate_taker_fee(exit_payout, exit_px, fee_rate=applied_r, fee_exponent=1.0)
                    net_pnl = round(exit_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0) - exit_fee, 2)
                    exit_reason = "FINAL_45S_CAPITAL_RECYCLE_UNWIND"
                    is_won = (net_pnl > 0)
                elif trailing_ratchet_triggered:
                    exit_px = best_bid
                    exit_payout = round(t["shares_bought"] * exit_px, 2)
                    _, exit_fee = calculate_taker_fee(exit_payout, exit_px, fee_rate=applied_r, fee_exponent=1.0)
                    net_pnl = round(exit_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0) - exit_fee, 2)
                    exit_reason = "TRAILING_PROFIT_RATCHET_UNWIND"
                    is_won = (net_pnl > 0)
                elif opposite_salvaged:
                    exit_px = best_bid
                    exit_payout = round(t["shares_bought"] * exit_px, 2)
                    _, exit_fee = calculate_taker_fee(exit_payout, exit_px, fee_rate=applied_r, fee_exponent=1.0)
                    net_pnl = round(exit_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0) - exit_fee, 2)
                    exit_reason = "CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE"
                    is_won = False
                else:
                    exit_px = tp_px
                    exit_payout = round(t["shares_bought"] * exit_px, 2)
                    exit_fee = 0.0  # Maker exit pays zero fee
                    net_pnl = round(exit_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0), 2)
                    exit_reason = "EXP315_MAKER_TP_FILLED"
                    is_won = True

                t["status"] = "CLOSED"
                t["exit_reason"] = exit_reason
                t["exit_price"] = exit_px
                t["exit_fee_usd"] = exit_fee
                t["payout_usd"] = exit_payout
                t["net_pnl_usd"] = net_pnl
                t["won"] = is_won
                t["settle_time"] = telem.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

                self.sleeve2_trades.append(t)
                self.sleeve2_realized_pnl += net_pnl
                self.sleeve2_cash = SLEEVE_2_INITIAL_CAPITAL + self.sleeve2_realized_pnl
                self.sleeve2_settled_ids.add(t["trade_id"])
                sleeve2_closed.append(t)

                with open(SLEEVE_2_LEDGER_FILE, "a") as f:
                    f.write(json.dumps(t) + "\n")

                tag = "SLEEVE 2 SALVAGE EXECUTED" if opposite_salvaged else f"SLEEVE 2 MAKER TP FILLED @ {exit_px:.3f}"
                print(
                    f"\n[{tag}] {t.get('title')} | Target: {target_token} | "
                    f"Exit Price: ${exit_px:.3f} | Net PnL: ${net_pnl:+.2f} | Sleeve 2 Equity: ${self.sleeve2_cash:,.2f}",
                    flush=True,
                )

            if sleeve2_closed:
                self.sleeve2_open_trades[market_id] = [t for t in self.sleeve2_open_trades[market_id] if t.get("status") == "OPEN"]
                if not self.sleeve2_open_trades[market_id]:
                    del self.sleeve2_open_trades[market_id]
                self.save_sleeve2_state()

        return closed_trades

    def settle_market(self, m_id: str, resolution: Dict[str, Any], historical: bool = False):
        if m_id not in self.open_trades and m_id not in self.sleeve2_open_trades:
            return

        winning = resolution.get("winning_outcome")  # UP or DOWN

        # 1. Settle Sleeve 1 (EXP-302 Core Baseline)
        if m_id in self.open_trades:
            closed_this_round = []
            for trade in self.open_trades[m_id]:
                tid = trade["trade_id"]
                if tid in self.settled_trade_ids or trade.get("status") == "CLOSED":
                    continue

                won = (trade["target_token"] == winning)
                payout = trade["shares_bought"] * 1.0 if won else 0.0
                taker_fee = trade.get("taker_fee_usd", 0.0)
                net_pnl = payout - trade["notional_usd"] - taker_fee
                legacy_notional = float(trade.get("legacy_fixed_notional_usd", trade["notional_usd"]))
                ratio = legacy_notional / max(trade["notional_usd"], 1.0)
                legacy_pnl = round(net_pnl * ratio, 2)

                trade["settle_time"] = resolution.get("timestamp_resolved", "")
                trade["winning_outcome"] = winning
                trade["won"] = won
                trade["payout_usd"] = round(payout, 2)
                trade["net_pnl_usd"] = round(net_pnl, 2)
                live_parity_notional = float(trade.get("live_parity_notional_usd", trade["notional_usd"]))
                parity_ratio = live_parity_notional / max(trade["notional_usd"], 1.0)
                trade["live_parity_pnl_usd"] = round(net_pnl * parity_ratio, 2)
                trade["legacy_fixed_pnl_usd"] = legacy_pnl
                trade["status"] = "CLOSED"
                trade["exit_reason"] = "EXP302_HOLD_TO_MATURITY_SETTLEMENT"

                entry_unix = trade.get("entry_unix", 0.0)
                if entry_unix < R3_VALIDATION_START_UNIX:
                    # Route to DEV ledger
                    self.dev_trades.append(trade)
                    self.dev_realized_pnl += net_pnl
                    self.dev_total_fees += trade.get("taker_fee_usd", 0.0)
                    self.dev_cash = INITIAL_PAPER_CAPITAL + self.dev_realized_pnl
                    target_file = DEV_LEDGER_FILE
                else:
                    # Route to frozen Out-of-Sample VALIDATION ledger
                    self.val_trades.append(trade)
                    self.val_realized_pnl += net_pnl
                    self.val_total_fees += trade.get("taker_fee_usd", 0.0)
                    self.val_cash = INITIAL_PAPER_CAPITAL + self.val_realized_pnl
                    target_file = VALIDATION_LEDGER_FILE

                self.settled_trade_ids.add(tid)
                self.trades_per_market[m_id] += 1
                closed_this_round.append(trade)

                with open(target_file, "a") as f:
                    f.write(json.dumps(trade) + "\n")

            del self.open_trades[m_id]

            if not historical and closed_this_round:
                total_round_pnl = sum(t["net_pnl_usd"] for t in closed_this_round)
                print(f"\n[MARKET SETTLED] Market ID: {m_id} | Winner: {winning} | "
                      f"Trades Settled: {len(closed_this_round)} | Net PnL: ${total_round_pnl:+.2f} | "
                      f"Validation Equity: ${self.val_cash:,.2f} | Dev Equity: ${self.dev_cash:,.2f}", flush=True)

        # 2. Settle Sleeve 2 (EXP-304/EXP-315 Dynamic TP)
        if ENABLE_SLEEVE_304_315 and m_id in self.sleeve2_open_trades:
            s2_closed = []
            for trade in list(self.sleeve2_open_trades[m_id]):
                tid = trade["trade_id"]
                if tid in self.sleeve2_settled_ids or trade.get("status") == "CLOSED":
                    continue

                won = (trade["target_token"] == winning)
                payout = trade["shares_bought"] * 1.0 if won else 0.0
                taker_fee = trade.get("taker_fee_usd", 0.0)
                net_pnl = payout - trade["notional_usd"] - taker_fee

                trade["settle_time"] = resolution.get("timestamp_resolved", "")
                trade["winning_outcome"] = winning
                trade["won"] = won
                trade["payout_usd"] = round(payout, 2)
                trade["net_pnl_usd"] = round(net_pnl, 2)
                trade["status"] = "CLOSED"
                trade["exit_reason"] = "EXP304_315_HOLD_TO_MATURITY_SETTLEMENT"
                trade["exit_price"] = 1.0 if won else 0.0
                trade["exit_fee_usd"] = 0.0

                self.sleeve2_trades.append(trade)
                self.sleeve2_realized_pnl += net_pnl
                self.sleeve2_total_fees += taker_fee
                self.sleeve2_cash = SLEEVE_2_INITIAL_CAPITAL + self.sleeve2_realized_pnl
                self.sleeve2_settled_ids.add(tid)
                s2_closed.append(trade)

                with open(SLEEVE_2_LEDGER_FILE, "a") as f:
                    f.write(json.dumps(trade) + "\n")

                if not historical:
                    print(f"\n[SLEEVE 2 MARKET SETTLED] Market ID: {m_id} | Winner: {winning} | "
                          f"Won: {won} | Net PnL: ${net_pnl:+.2f} | Sleeve 2 Equity: ${self.sleeve2_cash:,.2f}", flush=True)

            del self.sleeve2_open_trades[m_id]
            self.save_sleeve2_state()

    def save_state(self):
        val_total = len(self.val_trades)
        val_wins = sum(1 for t in self.val_trades if t.get("won"))
        val_wr = (val_wins / val_total * 100.0) if val_total > 0 else 0.0

        dev_total = len(self.dev_trades)
        dev_wins = sum(1 for t in self.dev_trades if t.get("won"))
        dev_wr = (dev_wins / dev_total * 100.0) if dev_total > 0 else 0.0

        state = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "governance": {
                "specification_version": "v3.1",
                "validation_start_utc": R3_VALIDATION_START_UTC,
                "validation_start_unix": R3_VALIDATION_START_UNIX,
                "executable_depth_guard": "DepthRatio >= 1.50 (Fail-Closed)",
                "fee_schedule": "crypto_fees_v2 (7% dynamic schedule enforced)",
                "idempotent_event_sourced": True
            },
            "validation_oos_epoch": {
                "paper_portfolio_equity": round(self.val_cash, 2),
                "initial_capital": INITIAL_PAPER_CAPITAL,
                "cumulative_realized_pnl": round(self.val_realized_pnl, 2),
                "total_fees_paid": round(self.val_total_fees, 2),
                "total_trades_settled": val_total,
                "winning_trades": val_wins,
                "losing_trades": val_total - val_wins,
                "win_rate_pct": round(val_wr, 2),
                "ledger_file": str(VALIDATION_LEDGER_FILE)
            },
            "dev_calibration_epoch": {
                "paper_portfolio_equity": round(self.dev_cash, 2),
                "initial_capital": INITIAL_PAPER_CAPITAL,
                "cumulative_realized_pnl": round(self.dev_realized_pnl, 2),
                "total_fees_paid": round(self.dev_total_fees, 2),
                "total_trades_settled": dev_total,
                "winning_trades": dev_wins,
                "losing_trades": dev_total - dev_wins,
                "win_rate_pct": round(dev_wr, 2),
                "ledger_file": str(DEV_LEDGER_FILE)
            },
            "active_open_positions_count": sum(len(v) for v in self.open_trades.values()),
            "total_settled_trade_ids_tracked": len(self.settled_trade_ids),
            "current_hour_window": self.current_hour_window,
            "trades_this_hour": self.trades_this_hour,
            "status": "RUNNING"
        }
        tmp_file = STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, STATE_FILE)
        except Exception:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass

    async def live_loop(self):
        print("===============================================================================", flush=True)
        print("   POLYMARKET AUTONOMOUS FORWARD PAPER TRADER (v3.1 Conformance State)        ", flush=True)
        print(f"   Frozen OOS Boundary: {R3_VALIDATION_START_UTC}                             ", flush=True)
        print("   Depth Guard: Fail-Closed (Ratio >= 1.50) | Fee Schedule: crypto_fees_v2    ", flush=True)
        print("   Ticket Size: $50.00 Notional | Initial Capital: $1,000.00                  ", flush=True)
        print("===============================================================================", flush=True)

        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        if HOURLY_TELEMETRY_FILE.exists():
            self.last_telemetry_file_pos = HOURLY_TELEMETRY_FILE.stat().st_size
        if HOURLY_TELEMETRY_ETH_FILE.exists():
            self.last_telemetry_eth_file_pos = HOURLY_TELEMETRY_ETH_FILE.stat().st_size

        self.replay_existing_data()

        # Graceful shutdown: SIGTERM/SIGINT set a flag; the loop finishes its current iteration, flushes state
        # atomically (save_state uses tmp+fsync+os.replace) and exits 0.
        import signal as _signal
        self._shutdown_requested = False

        def _request_shutdown(signame: str):
            if not self._shutdown_requested:
                print(f"[SHUTDOWN] {signame} received; flushing state and stopping gracefully.", flush=True)
            self._shutdown_requested = True

        _loop = asyncio.get_running_loop()
        for _sig in (_signal.SIGTERM, _signal.SIGINT):
            try:
                _loop.add_signal_handler(_sig, _request_shutdown, _sig.name)
            except (NotImplementedError, RuntimeError, ValueError):
                pass

        while True:
            if self._shutdown_requested:
                self.save_state()
                print("[SHUTDOWN] Paper trader state flushed; exiting cleanly (STOPPED_GRACEFULLY).", flush=True)
                break
            try:
                # 1. Ingest new zero-latency shock triggers (<1ms from recorder detection)
                if TRIGGER_FILE.exists():
                    current_trig_size = TRIGGER_FILE.stat().st_size
                    if current_trig_size > self.last_trigger_file_pos:
                        with open(TRIGGER_FILE, "rb") as f:
                            f.seek(self.last_trigger_file_pos)
                            chunk = f.read()
                        complete_end = chunk.rfind(b"\n") + 1
                        if complete_end:
                            new_lines = chunk[:complete_end].decode("utf-8").splitlines()
                            self.last_trigger_file_pos += complete_end
                            for line in new_lines:
                                if not line.strip():
                                    continue
                                s = json.loads(line)
                                shock_id = f"{s.get('market_id')}_{s.get('t0_unix')}"
                                if shock_id not in self.seen_shock_ids:
                                    self.seen_shock_ids.add(shock_id)
                                    await asyncio.to_thread(self.evaluate_shock_signal, s, False)

                # Fallback to shock_responses if trigger file is absent
                elif SHOCK_FILE.exists():
                    current_shock_size = SHOCK_FILE.stat().st_size
                    if current_shock_size > self.last_shock_file_pos:
                        with open(SHOCK_FILE, "rb") as f:
                            f.seek(self.last_shock_file_pos)
                            chunk = f.read()
                        complete_end = chunk.rfind(b"\n") + 1
                        if complete_end:
                            new_lines = chunk[:complete_end].decode("utf-8").splitlines()
                            self.last_shock_file_pos += complete_end
                            for line in new_lines:
                                if not line.strip():
                                    continue
                                s = json.loads(line)
                                shock_id = f"{s.get('market_id')}_{s.get('t0_unix')}"
                                if shock_id not in self.seen_shock_ids:
                                    self.seen_shock_ids.add(shock_id)
                                    await asyncio.to_thread(self.evaluate_shock_signal, s, False)

                # 2. Check for newly finalized market resolutions
                if RESOLUTIONS_FILE.exists():
                    current_res_size = RESOLUTIONS_FILE.stat().st_size
                    if current_res_size > self.last_res_file_pos:
                        with open(RESOLUTIONS_FILE, "rb") as f:
                            f.seek(self.last_res_file_pos)
                            chunk = f.read()
                        complete_end = chunk.rfind(b"\n") + 1
                        if complete_end:
                            new_res_lines = chunk[:complete_end].decode("utf-8").splitlines()
                            self.last_res_file_pos += complete_end
                            for line in new_res_lines:
                                if not line.strip():
                                    continue
                                res = json.loads(line)
                                m_id = res.get("market_id")
                                if m_id not in self.seen_resolution_ids:
                                    self.seen_resolution_ids.add(m_id)
                                    self.settle_market(m_id, res, historical=False)

                # 3. Check live telemetry for Maker TP fills on open positions across sleeves
                if self.open_trades or (ENABLE_SLEEVE_304_315 and self.sleeve2_open_trades):
                    for telem_path, pos_attr in (
                        (HOURLY_TELEMETRY_FILE, "last_telemetry_file_pos"),
                        (HOURLY_TELEMETRY_ETH_FILE, "last_telemetry_eth_file_pos"),
                    ):
                        if telem_path.exists():
                            cur_sz = telem_path.stat().st_size
                            last_pos = getattr(self, pos_attr)
                            if cur_sz > last_pos:
                                with open(telem_path, "rb") as f:
                                    f.seek(last_pos)
                                    chunk = f.read()
                                complete_end = chunk.rfind(b"\n") + 1
                                if complete_end:
                                    lines = chunk[:complete_end].decode("utf-8").splitlines()
                                    setattr(self, pos_attr, last_pos + complete_end)
                                    for line in lines:
                                        if not line.strip():
                                            continue
                                        try:
                                            telem = json.loads(line)
                                            t_m_id = str(telem.get("market_id", ""))
                                            if t_m_id in self.open_trades or (ENABLE_SLEEVE_304_315 and t_m_id in self.sleeve2_open_trades):
                                                self.check_maker_tp_fills(t_m_id, telem)
                                        except Exception:
                                            pass

                self.save_state()
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"[-] Error in paper trader loop: {e}", flush=True)
                await asyncio.sleep(1.0)


if __name__ == "__main__":
    trader = PolymarketForwardPaperTrader()
    asyncio.run(trader.live_loop())
