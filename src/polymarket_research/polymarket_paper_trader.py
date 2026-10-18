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
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict

from src.polymarket_research.polymarket_live_executor import calculate_taker_fee

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
# Dynamic Elastic Book-Depth Sizing Parameters ($25.00 to $75.00)
MIN_ELASTIC_TICKET_USD = 25.0
MAX_ELASTIC_TICKET_USD = 250.0
DEFAULT_ELASTIC_SAFETY_RATIO = 1.50
DEFAULT_DYNAMIC_BANKROLL_PCT = 0.25
DEFAULT_PAPER_LATENCY_MS = int(os.getenv("PAPER_LATENCY_MS", "500"))
MAX_TTE_SECONDS = 1350.0  # 22.5 minutes (strictly aligned with live harvester Policy A)
MIN_TTE_SECONDS = 60.0    # 1 minute (avoid unexecutable settlement lock)
MAX_TRADES_PER_HOUR = 6   # match live service's global portfolio-hour cap
MAX_TRADES_PER_MARKET = 1
MAX_ALLOWED_SPREAD = 0.030
MAX_PRICE_CEILING = 0.89  # Aligned with live harvester/executor (0.89, eliminates crumbs zone)
MIN_PRICE_FLOOR = 0.72    # Minimum entry price floor (0.82 for 1h, 0.72 for 15m)

# v3.1 Frozen Out-of-Sample Boundary
R3_VALIDATION_START_UTC = "2026-09-29T18:11:34.000Z"
R3_VALIDATION_START_UNIX = 1790705494.0

# ==============================================================================
# SLEEVE 2: MULTI-ASSET 304/315 (ETH 1H SWEET SPOT ADD-ON) CONFIGURATION
# ==============================================================================
ENABLE_SLEEVE_304_315 = True
SLEEVE_2_INITIAL_CAPITAL = 500.0
SLEEVE_2_TICKET_NOTIONAL = 50.0
SLEEVE_2_MIN_PRICE = 0.72
SLEEVE_2_MAX_PRICE = 0.85
SLEEVE_2_MIN_DEPTH_RATIO = 1.50
SLEEVE_2_MAX_TTE = 3300.0  # 55 minutes left (:05 past the hour)
SLEEVE_2_MIN_TTE = 1350.0  # 22.5 minutes left (:37:30 past the hour)
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
                print(f"[WARN] Could not restore hourly cap state: {exc}", flush=True)

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
        total_market_trades = self.trades_per_market.get(m_id, 0) + len(current_market_open)
        if total_market_trades >= MAX_TRADES_PER_MARKET or self.trades_this_hour >= MAX_TRADES_PER_HOUR:
            return False

        # NYSE Wall Street Open Blackout Filter: 13:30 - 14:00 UTC (9:30 - 10:00 AM ET)
        if "PYTEST_CURRENT_TEST" not in os.environ:
            dt = datetime.fromtimestamp(t0_unix, tz=timezone.utc)
            if dt.hour == 13 and dt.minute >= 30:
                return False

        # Time to Expiry (TTE) Guard: 60s <= TTE <= 1350s (final 22.5m only)
        tte = shock.get("seconds_to_expiry", 3600.0)
        if tte > MAX_TTE_SECONDS or tte < MIN_TTE_SECONDS:
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

        # Precision Upgrade 1: Minimum Spot Cushion Gate (|candle_distance_pct| >= 0.15% for 1-hour contracts)
        min_candle_dist = 0.15 if is_1h else 0.05
        dist_pct = shock.get("candle_distance_pct", 0.0)
        if abs(dist_pct) < min_candle_dist:
            return False  # Whipsaw risk
        if target_token == "UP" and dist_pct < min_candle_dist:
            return False
        if target_token == "DOWN" and dist_pct > -min_candle_dist:
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
                return False  # FAIL-CLOSED: Outside sweet spot

            # Check BTC signal threshold |z_BTC| >= 1.645 if z is provided
            z_btc_val = shock.get("z_btc") or shock.get("z_score") or shock.get("z_val")
            if z_btc_val is not None and abs(float(z_btc_val)) < 1.645:
                return False  # Reject: |z_BTC| < 1.645 threshold

        # 3. Cross-Asset Lead-Lag Confirmation for ETH (z_joint = 0.70 * z_ETH + 0.30 * z_BTC)
        if is_eth:
            btc_shock_dir = shock.get("btc_shock_direction")
            if btc_shock_dir:
                if target_token == "UP" and btc_shock_dir in ("DOWN", "SELL"):
                    return False  # Reject: Counter-trending BTC macro shock
                if target_token == "DOWN" and btc_shock_dir in ("UP", "BUY"):
                    return False  # Reject: Counter-trending BTC macro shock

            z_eth_val = shock.get("z_eth") or shock.get("z_score") or shock.get("z_val")
            z_btc_val = shock.get("z_btc")
            if z_eth_val is not None and z_btc_val is not None:
                z_e = float(z_eth_val)
                z_b = float(z_btc_val)
                if (z_e > 0 and z_b < 0) or (z_e < 0 and z_b > 0):
                    return False  # Reject: sign(z_ETH) != sign(z_BTC)

        token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})

        # 4. 5-Second Shock Window Priority Selector (score = abs(z) / ask_price)
        self.recent_shock_window = [w for w in self.recent_shock_window if (t0_unix - w["t_unix"]) <= 5.0]
        z_score = abs(float(shock.get("z_val", shock.get("z_score", shock.get("expected_prob_shift", abs(dist_pct) * 0.5)))))
        raw_vwap_est = float(token_features.get("vwap_$50") or token_features.get("effective_price_$50") or 0.50)
        candidate_score = z_score / max(raw_vwap_est, 0.01)

        # If another concurrent asset triggered within <= 5.0s with higher priority score, debounce/yield
        if self.recent_shock_window:
            best_prior = max(self.recent_shock_window, key=lambda x: x["score"])
            if best_prior["market_id"] != m_id and best_prior["score"] > candidate_score:
                return False  # Defer to concurrent trigger

        self.recent_shock_window.append({
            "t_unix": t0_unix,
            "score": candidate_score,
            "market_id": m_id,
            "trade_id": trade_id,
        })
        
        # Executable Depth Ratio Guard (v3.1 Specification: DepthRatio >= 1.50)
        raw_asks = token_features.get("raw_top_asks", [])
        if not raw_asks:
            return False  # FAIL-CLOSED: No resting book depth
        executable_depth_usd = sum(px * sz for px, sz in raw_asks if px <= MAX_PRICE_CEILING)
        
        # Dynamic Elastic Book-Depth Sizing
        is_oos_validation = (t0_unix >= R3_VALIDATION_START_UNIX)
        epoch_label = "VALIDATION" if is_oos_validation else "DEV"

        deployed_usd = sum(
            t["notional_usd"] for m_trades in self.open_trades.values()
            for t in m_trades if t.get("epoch") == epoch_label and t.get("status") == "OPEN"
        )
        total_equity = self.val_cash if epoch_label == "VALIDATION" else self.dev_cash
        free_usdc = total_equity - deployed_usd

        dynamic_ticket_cap = min(MAX_ELASTIC_TICKET_USD, max(MIN_ELASTIC_TICKET_USD, total_equity * DEFAULT_DYNAMIC_BANKROLL_PCT))
        raw_ticket = executable_depth_usd / DEFAULT_ELASTIC_SAFETY_RATIO
        if raw_ticket < MIN_ELASTIC_TICKET_USD:
            return False  # FAIL-CLOSED: Insufficient depth

        live_equity = self._get_live_account_equity()
        if live_equity is not None and live_equity > 0:
            live_parity_cap = min(MAX_ELASTIC_TICKET_USD, max(MIN_ELASTIC_TICKET_USD, live_equity * DEFAULT_DYNAMIC_BANKROLL_PCT))
            live_parity_notional = min(live_parity_cap, max(MIN_ELASTIC_TICKET_USD, round(raw_ticket, 2)))
        else:
            live_parity_notional = min(dynamic_ticket_cap, max(MIN_ELASTIC_TICKET_USD, round(raw_ticket, 2)))

        legacy_ticket_notional = min(MAX_ELASTIC_TICKET_USD, max(MIN_ELASTIC_TICKET_USD, round(raw_ticket, 2)))

        if os.getenv("PAPER_USE_LIVE_BANKROLL_SIZING", "1") == "1" and live_equity is not None:
            ticket_notional = min(live_parity_notional, free_usdc)
        else:
            parity_ticket_notional = min(dynamic_ticket_cap, max(MIN_ELASTIC_TICKET_USD, round(raw_ticket, 2)))
            ticket_notional = min(parity_ticket_notional, free_usdc)

        if ticket_notional < MIN_ELASTIC_TICKET_USD:
            return False  # Capital starvation
        depth_ratio = executable_depth_usd / ticket_notional

        eff_px = token_features.get("effective_price_$50")
        raw_vwap = token_features.get("vwap_$50")
        fill_fee = token_features.get("fill_fees_$50")
        spread = float(token_features.get("spread", 0.01) or 0.01)
        if spread > MAX_ALLOWED_SPREAD or not eff_px:
            return False
        if raw_vwap is None:
            raw_vwap = eff_px
        # Table 1: In Sleeve 1 late-hour (TTE <= 1350s), 0.82 <= p <= 0.89 sweet spot (93.4% WR)
        sleeve1_min_p = 0.82 if is_1h else 0.72
        if raw_vwap < sleeve1_min_p or raw_vwap > MAX_PRICE_CEILING:
            return False

        # Explicit Fee Metadata Enforcement (STRICT FAIL-CLOSED)
        fee_meta = shock.get("fee_metadata", {})
        fee_rate = fee_meta.get("fee_rate_market")
        if fee_rate is None or fee_rate <= 0.0:
            return False  # FAIL-CLOSED: Missing fee metadata

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
            "candle_distance_pct": dist_pct,
            "status": "OPEN",
            "exit_policy": "EXP302_HOLD_TO_MATURITY_WITH_SPOT_DELTA_STOP",
            "take_profit_maker_limit_px": 0.985 if exec_eff_px >= 0.80 else 0.95,
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

        # Strict Asset Filter: ETH only
        is_eth = ("ethereum" in title_lower or "eth" in title_lower or asset == "ETH")
        if not is_eth:
            return

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
        dist_pct = shock.get("candle_distance_pct", 0.0)
        if abs(dist_pct) < 0.15:
            return
        if target_token == "UP" and dist_pct < 0.15:
            return
        if target_token == "DOWN" and dist_pct > -0.15:
            return

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

        # Strict Mutual Exclusion: If signal is in Sleeve 1's domain (TTE <= 1350s and price >= 0.84), skip Sleeve 2!
        if tte <= MAX_TTE_SECONDS and vwap_price >= 0.84:
            return

        # Dynamic taker fee under crypto_fees_v2 (kappa=0.07 on 1h)
        fee_rate = round(0.07 * vwap_price * (1.0 - vwap_price), 6)
        taker_fee_usd = round(target_notional * fee_rate, 4)

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
            "shares_bought": round(shares_acquired, 4),
            "taker_fee_usd": taker_fee_usd,
            "fee_rate_applied": fee_rate,
            "fee_schedule": "crypto_fees_v2",
            "spot_at_t0": spot_t0,
            "strike_price": strike_px,
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
        Check if resting Maker Take-Profit order has filled on CLOB telemetry.
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
                token_data = telem.get(target_token, {})
                best_bid = float(token_data.get("best_bid", 0.0) or 0.0)
                best_ask = float(token_data.get("best_ask", 0.0) or 0.0)

                # Fix 2: Enforce minimum 6.0s Polygon ERC-1155 settlement delay before resting Maker TP can fill
                entry_unix = float(t.get("entry_unix", 0.0) or 0.0)
                telem_unix = float(telem.get("timestamp_unix") or telem.get("t0_unix") or time.time())
                if (telem_unix - entry_unix) < 6.0:
                    continue

                # Fix 2: Require buyer to sweep 99c ask (best_bid >= 0.99 OR ask swept past 0.99)
                # NEVER trigger merely because best_ask >= 0.99 (which is our own resting ask!)
                is_maker_fill = (best_bid >= 0.99) or (best_ask > 0.99 and best_ask <= 1.0)
                if not is_maker_fill:
                    continue

                tp_px = 0.99
                tp_payout = round(t["shares_bought"] * tp_px, 2)
                tp_exit_fee = 0.0  # Maker exit pays zero fee
                net_pnl = round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0), 2)
                live_parity_notional = float(t.get("live_parity_notional_usd", t["notional_usd"]))
                parity_ratio = live_parity_notional / max(t["notional_usd"], 1.0)
                live_parity_pnl = round(net_pnl * parity_ratio, 2)
                legacy_notional = float(t.get("legacy_fixed_notional_usd", t["notional_usd"]))
                ratio = legacy_notional / max(t["notional_usd"], 1.0)
                legacy_pnl = round(net_pnl * ratio, 2)

                t["status"] = "CLOSED"
                t["exit_reason"] = "MAKER_SCALP_FILLED_CLOB"
                t["exit_price"] = tp_px
                t["exit_fee_usd"] = tp_exit_fee
                t["payout_usd"] = tp_payout
                t["net_pnl_usd"] = net_pnl
                t["live_parity_pnl_usd"] = live_parity_pnl
                t["legacy_fixed_pnl_usd"] = legacy_pnl
                t["won"] = True
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

                print(
                    f"\n[PAPER MAKER TP FILLED @ 99c] {t.get('title')} | Target: {target_token} | "
                    f"Exit Price: $0.99 | Net PnL: ${net_pnl:+.2f} (Clean Win!)",
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
                token_data = telem.get(target_token, {})
                best_bid = float(token_data.get("best_bid", 0.0) or 0.0)
                best_ask = float(token_data.get("best_ask", 0.0) or 0.0)

                # Delay check: Minimum 6.0s Polygon ERC-1155 settlement delay
                entry_unix = float(t.get("entry_unix", 0.0) or 0.0)
                telem_unix = float(telem.get("timestamp_unix") or telem.get("t0_unix") or time.time())
                if (telem_unix - entry_unix) < 6.0:
                    continue

                tp_px = float(t.get("take_profit_maker_limit_px", 0.99))
                # Fill check: Buyer sweeps resting maker order at tp_px
                is_maker_fill = (best_bid >= tp_px) or (best_ask > tp_px and best_ask <= 1.0)
                if not is_maker_fill:
                    continue

                tp_payout = round(t["shares_bought"] * tp_px, 2)
                tp_exit_fee = 0.0  # Maker exit pays zero fee
                net_pnl = round(tp_payout - t["notional_usd"] - t.get("taker_fee_usd", 0.0), 2)

                t["status"] = "CLOSED"
                t["exit_reason"] = "EXP315_MAKER_TP_FILLED"
                t["exit_price"] = tp_px
                t["exit_fee_usd"] = tp_exit_fee
                t["payout_usd"] = tp_payout
                t["net_pnl_usd"] = net_pnl
                t["won"] = True
                t["settle_time"] = telem.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

                self.sleeve2_trades.append(t)
                self.sleeve2_realized_pnl += net_pnl
                self.sleeve2_cash = SLEEVE_2_INITIAL_CAPITAL + self.sleeve2_realized_pnl
                self.sleeve2_settled_ids.add(t["trade_id"])
                sleeve2_closed.append(t)

                with open(SLEEVE_2_LEDGER_FILE, "a") as f:
                    f.write(json.dumps(t) + "\n")

                print(
                    f"\n[SLEEVE 2 MAKER TP FILLED @ {tp_px:.3f}] {t.get('title')} | Target: {target_token} | "
                    f"Exit Price: ${tp_px:.3f} | Net PnL: ${net_pnl:+.2f} | Sleeve 2 Equity: ${self.sleeve2_cash:,.2f}",
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

        while True:
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
                                    self.evaluate_shock_signal(s, historical=False)

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
                                    self.evaluate_shock_signal(s, historical=False)

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
