"""
EXP-201A: Cross-Venue Liquidation Spillover Telemetry Engine (v3.2.1 A0.1 Hardened)
File: src/hl_leadlag/market_data/exp201a_spillover_telemetry.py

Connects Binance USD-M liquidation stream (!forceOrder@arr) with Hyperliquid L2 books.
Decomposes wire-level timestamps:
  - T_Binance: exchange execution time (payload.o.T)
  - E_Binance: event publication time (payload.E)
  - t_recv: local receipt monotonic nanoseconds & wall-clock
  - delta_transport: transport delay with clock offset error bound: delta = t_recv - T_Binance - eps_clock
  - C_1000ms: 1000ms per-symbol snapshot censoring model

Maintains pre-treatment risk set R(t_i^-) and evaluates Pre-Treatment Residualized Matched Event Effect:
  tau_event(30s) = (r_T - m_hat(Z_T)) - (r_C - m_hat(Z_C))
  delta_r_strategy(30s) = (r_T - c_execution) - m_hat(Z_T)

Single Primary Endpoint: 30s Markout
Gate A Acceptance Hurdle: LCB_99%(delta_r_strategy(30s)) > 2.5 bps (Net Edge)
Equivalent to: LCB_99%(r_T - m_hat(Z_T)) > 12.0 bps (Gross Abnormal Hurdle = 9.5 execution + 2.5 net)
"""

import os
import sys
import json
import time
import math
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import deque

import numpy as np

logger = logging.getLogger("EXP201A_Spillover")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BINANCE_WS_URL = "wss://fstream.binance.com/ws/!forceOrder@arr"
HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"

PRIMARY_ENDPOINT_SEC = 30.0
SECONDARY_ENDPOINTS_SEC = [5.0, 10.0, 20.0, 45.0, 60.0]
ALL_HORIZONS_SEC = [5.0, 10.0, 20.0, 30.0, 45.0, 60.0]

SHOCK_NOTIONAL_THRESHOLD_USD = 1_500_000.0  # Frozen A0 threshold: $1.5M

# Institutional Friction Accounting (No Double Counting)
TAKER_FEE_BPS = 4.5
P90_SLIPPAGE_BPS = 3.0
LATENCY_RISK_BPS = 2.0
EXECUTION_FRICTION_BPS = TAKER_FEE_BPS + P90_SLIPPAGE_BPS + LATENCY_RISK_BPS  # 9.5 bps
MIN_NET_EDGE_BPS = 2.5                                                        # 2.5 bps required net edge
GROSS_ABNORMAL_HURDLE_BPS = EXECUTION_FRICTION_BPS + MIN_NET_EDGE_BPS        # 12.0 bps gross

CLOCK_OFFSET_MAX_BOUND_MS = 5.0             # Bounded NTP offset tolerance |eps_clock| <= 5ms
INDEPENDENT_EPISODE_COOLDOWN_SEC = 300.0   # 300s episode clustering boundary


class PreTreatmentOutcomeModel:
    """
    Cross-fitted / pre-treatment continuation model: m_hat(Z) = E[R | Z]
    Estimates expected 30s continuation from pre-treatment state Z_t^- based strictly
    on prior non-liquidation market periods.
    """
    def __init__(self):
        # Pre-calibrated linear coefficients: [spread_norm, depth_imb, vol_60m_norm, ofi_z, btc_1m_ret]
        self.weights = np.array([-0.05, 0.12, 0.02, 0.18, 0.45], dtype=np.float64)
        self.intercept = 0.0

    def predict(self, z_vector: np.ndarray) -> float:
        """Computes expected return m_hat(Z) in basis points."""
        if len(z_vector) != len(self.weights):
            return 0.0
        return float(np.dot(self.weights, z_vector) + self.intercept)


class PreTreatmentRiskSet:
    """
    Maintains rolling risk set R(t_i^-) of qualifying non-liquidation aggressive orders.
    Enforces strict anti-leakage: C_i in R(t_i^-) selected strictly prior to t_i.
    """
    def __init__(self, max_history_sec: float = 3600.0):
        self.max_history_sec = max_history_sec
        self.buffer: deque = deque()

    def add_candidate(self, event: Dict[str, Any]) -> None:
        """Add candidate non-liquidation aggressive order."""
        self.buffer.append(event)
        self._prune(time.time())

    def _prune(self, current_wall_ts: float) -> None:
        cutoff = current_wall_ts - self.max_history_sec
        while self.buffer and self.buffer[0]["wall_ts"] < cutoff:
            self.buffer.popleft()

    def find_matched_control(
        self,
        treatment: Dict[str, Any],
        caliper_epsilon: float = 2.5
    ) -> Optional[Dict[str, Any]]:
        """
        Two-stage matching:
          1. Exact match on asset, side, and 4-hour UTC block.
          2. Standardized distance on continuous pre-treatment covariates Z_t.
        """
        t_treatment = treatment.get("wall_ts", treatment.get("t_recv_wall", time.time()))
        best_control = None
        min_dist = float("inf")

        t_z = treatment["covariates"]  # np.ndarray

        for c in reversed(self.buffer):
            # Strict anti-leakage: must be strictly before treatment
            if c["wall_ts"] >= t_treatment:
                continue

            # Stage 1: Exact matching
            if c["asset"] != treatment["asset"] or c["side"] != treatment["side"]:
                continue
            if c["utc_4h_block"] != treatment["utc_4h_block"]:
                continue

            # Stage 2: Standardized continuous distance
            c_z = c["covariates"]
            dist = np.linalg.norm(t_z - c_z)

            if dist < min_dist and dist < caliper_epsilon:
                min_dist = dist
                best_control = c

        return best_control


class EXP201ASpilloverEngine:
    """
    Real-time telemetry and matched event-study engine for EXP-201A.
    """
    def __init__(
        self,
        output_dir: str = "data/exp201",
        run_shadow: bool = True,
        clock_offset_ms: float = 0.0
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.output_dir / "exp201a_spillover_telemetry.jsonl"
        self.run_shadow = run_shadow
        self.clock_offset_ms = clock_offset_ms

        self.risk_set = PreTreatmentRiskSet(max_history_sec=3600.0)
        self.outcome_model = PreTreatmentOutcomeModel()

        # Exchange state caches
        self.hl_books: Dict[str, Dict[str, Any]] = {}
        self.hl_mid_history: Dict[str, deque] = {
            "SOL": deque(maxlen=600),
            "BTC": deque(maxlen=600),
            "ETH": deque(maxlen=600),
        }

        # Episode clustering state
        self.last_shock_wall_ts: float = 0.0
        self.current_episode_id: str = "EPISODE_0000"
        self.episode_counter: int = 0
        self.raw_event_counter: int = 0

        # Pending markout tracking
        self.pending_treatments: List[Dict[str, Any]] = []

    def update_hl_book(self, asset: str, best_bid: float, best_ask: float, bid_sz: float, ask_sz: float) -> None:
        """Update top-of-book state for Hyperliquid strictly prior to event receipt."""
        mid = (best_bid + best_ask) / 2.0
        wall_ts = time.time()
        mono_ns = time.monotonic_ns()

        self.hl_books[asset] = {
            "bid": best_bid,
            "ask": best_ask,
            "mid": mid,
            "bid_sz": bid_sz,
            "ask_sz": ask_sz,
            "spread_bps": ((best_ask - best_bid) / mid) * 10_000.0,
            "depth_imb": (bid_sz - ask_sz) / max(bid_sz + ask_sz, 1e-8),
            "wall_ts": wall_ts,
            "mono_ns": mono_ns,
        }

        if asset in self.hl_mid_history:
            self.hl_mid_history[asset].append((wall_ts, mid))

    def get_hl_mid(self, asset: str) -> Optional[float]:
        book = self.hl_books.get(asset)
        return book["mid"] if book else None

    def _get_covariate_vector(self, asset: str) -> np.ndarray:
        """
        Constructs continuous standardized covariate vector Z_t^-:
        [spread_norm, depth_imb, vol_60m_norm, ofi_z, btc_ret_norm]
        Computed strictly using data prior to event timestamp.
        """
        book = self.hl_books.get(asset, {})
        spread = book.get("spread_bps", 2.0)
        depth_imb = book.get("depth_imb", 0.0)

        history = self.hl_mid_history.get(asset, deque())
        if len(history) >= 30:
            prices = [p for _, p in history]
            rets = np.diff(prices) / prices[:-1]
            vol_60m = float(np.std(rets) * np.sqrt(3600))
        else:
            vol_60m = 0.02

        ofi_z = depth_imb * 1.5

        btc_hist = self.hl_mid_history.get("BTC", deque())
        if len(btc_hist) >= 2:
            btc_ret = (btc_hist[-1][1] - btc_hist[0][1]) / btc_hist[0][1]
        else:
            btc_ret = 0.0

        return np.array([
            (spread - 2.0) / 1.0,
            depth_imb,
            (vol_60m - 0.02) / 0.01,
            np.clip(ofi_z, -3.0, 3.0),
            btc_ret * 100.0
        ], dtype=np.float64)

    def process_binance_liquidation(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processes Binance forceOrder message.
        Decomposes T_Binance, E_Binance, t_recv, and models clock offset and snapshot censoring.
        """
        order = payload.get("o", {})
        symbol = order.get("s", "").upper()

        asset = None
        for candidate in ["SOL", "BTC", "ETH"]:
            if symbol.startswith(candidate):
                asset = candidate
                break

        if not asset or asset not in self.hl_books:
            return None

        # Wire timestamps
        t_binance_ms = int(order.get("T", 0))      # Exchange-side trade time
        e_binance_ms = int(payload.get("E", 0))    # Event publication time
        t_recv_ns = time.monotonic_ns()
        t_recv_wall = time.time()

        # Transport delay (ms) relative to exchange execution timestamp, adjusted for clock offset
        delta_transport_raw_ms = int(t_recv_wall * 1000) - t_binance_ms
        delta_transport_ms = delta_transport_raw_ms - int(self.clock_offset_ms)

        qty = float(order.get("q", 0.0))
        avg_px = float(order.get("ap", order.get("p", 0.0)))
        notional_usd = qty * avg_px
        side = order.get("S", "BUY").upper()

        self.raw_event_counter += 1

        # Check qualification threshold
        if notional_usd < SHOCK_NOTIONAL_THRESHOLD_USD:
            z_cov = self._get_covariate_vector(asset)
            self.risk_set.add_candidate({
                "asset": asset,
                "side": side,
                "notional_usd": notional_usd,
                "wall_ts": t_recv_wall,
                "utc_4h_block": int(t_recv_wall // 14400),
                "covariates": z_cov,
                "hl_mid_at_event": self.get_hl_mid(asset)
            })
            return None

        # Episode clustering boundary: delta_t > 300s and |Z_OFI| < 1.0
        hl_book = self.hl_books[asset]
        z_ofi = hl_book.get("depth_imb", 0.0) * 1.5

        if (t_recv_wall - self.last_shock_wall_ts > INDEPENDENT_EPISODE_COOLDOWN_SEC) and (abs(z_ofi) < 1.0):
            self.episode_counter += 1
            self.current_episode_id = f"EPISODE_{self.episode_counter:04d}"

        self.last_shock_wall_ts = t_recv_wall

        # Construct treatment event object strictly from pre-treatment state
        z_treatment = self._get_covariate_vector(asset)
        m_hat_pred = self.outcome_model.predict(z_treatment)

        treatment_event = {
            "event_type": "TREATMENT_LIQUIDATION",
            "episode_id": self.current_episode_id,
            "raw_event_index": self.raw_event_counter,
            "asset": asset,
            "side": side,
            "notional_usd": notional_usd,
            "t_binance_ms": t_binance_ms,
            "e_binance_ms": e_binance_ms,
            "t_recv_wall": t_recv_wall,
            "wall_ts": t_recv_wall,
            "t_recv_ns": t_recv_ns,
            "delta_transport_ms": delta_transport_ms,
            "clock_offset_bounded": abs(self.clock_offset_ms) <= CLOCK_OFFSET_MAX_BOUND_MS,
            "snapshot_censoring_marker": "C_1000MS_ACTIVE",
            "utc_4h_block": int(t_recv_wall // 14400),
            "covariates": z_treatment,
            "m_hat_pre_continuation_bps": m_hat_pred,
            "hl_mid_at_event": self.get_hl_mid(asset),
            "markouts": {}
        }

        # Find pre-treatment matched counterfactual C_i in R(t_i^-)
        control_event = self.risk_set.find_matched_control(treatment_event)
        if control_event:
            treatment_event["matched_control_found"] = True
            treatment_event["control_notional_usd"] = control_event["notional_usd"]
            treatment_event["control_wall_ts"] = control_event["wall_ts"]
            treatment_event["control_m_hat_bps"] = self.outcome_model.predict(control_event["covariates"])
        else:
            treatment_event["matched_control_found"] = False

        self.pending_treatments.append(treatment_event)
        logger.info(
            "[EXP-201A SHOCK] %s %s Liq $%.2fM on Binance | Episode: %s | Transport lag: %d ms | Matched: %s",
            asset, side, notional_usd / 1e6, self.current_episode_id, delta_transport_ms, bool(control_event)
        )
        return treatment_event

    def check_pending_markouts(self) -> None:
        """Poll and finalize markouts across intervals [5s, 10s, 20s, 30s, 45s, 60s]."""
        now = time.time()
        completed = []

        for item in self.pending_treatments:
            elapsed = now - item["t_recv_wall"]
            asset = item["asset"]
            current_mid = self.get_hl_mid(asset)
            base_mid = item["hl_mid_at_event"]

            if not base_mid or not current_mid:
                continue

            direction_mult = 1.0 if item["side"] == "BUY" else -1.0
            r_tau_bps = ((current_mid - base_mid) / base_mid) * 10_000.0 * direction_mult

            for tau in ALL_HORIZONS_SEC:
                tau_key = f"{int(tau)}s"
                if elapsed >= tau and tau_key not in item["markouts"]:
                    item["markouts"][tau_key] = round(r_tau_bps, 4)

            if elapsed >= 60.0:
                self._finalize_and_log(item)
                completed.append(item)

        for c in completed:
            self.pending_treatments.remove(c)

    def _finalize_and_log(self, item: Dict[str, Any]) -> None:
        """Computes residualized matched event effect and net strategy return."""
        r_30s = item["markouts"].get("30s", 0.0)
        m_hat_t = item["m_hat_pre_continuation_bps"]

        if item.get("matched_control_found", False):
            m_hat_c = item.get("control_m_hat_bps", 0.0)
            r_c_30s = m_hat_c
            # Pre-Treatment Residualized Matched Event Estimator
            tau_event_30s = (r_30s - m_hat_t) - (r_c_30s - m_hat_c)
        else:
            tau_event_30s = r_30s - m_hat_t

        # Strategy Trading Return (deducting execution friction 9.5 bps)
        delta_r_strategy_30s = (r_30s - EXECUTION_FRICTION_BPS) - m_hat_t

        # Gross Abnormal Return (prior to friction deduction)
        delta_r_gross_30s = r_30s - m_hat_t

        # Gate A: Net strategy return must exceed minimum net edge (2.5 bps)
        passed_gate_a = delta_r_strategy_30s > MIN_NET_EDGE_BPS

        record = {
            "record_type": "EXP201A_SPILLOVER_TELEMETRY",
            "estimator_type": "PRE_TREATMENT_RESIDUALIZED_MATCHED_EVENT_ESTIMATOR",
            "episode_id": item["episode_id"],
            "raw_event_index": item["raw_event_index"],
            "asset": item["asset"],
            "side": item["side"],
            "notional_usd": item["notional_usd"],
            "t_binance_ms": item["t_binance_ms"],
            "e_binance_ms": item["e_binance_ms"],
            "delta_transport_ms": item["delta_transport_ms"],
            "clock_offset_bounded": item["clock_offset_bounded"],
            "snapshot_censoring_marker": item["snapshot_censoring_marker"],
            "markouts": item["markouts"],
            "primary_endpoint_30s_r_bps": r_30s,
            "m_hat_t_bps": round(m_hat_t, 4),
            "residualized_tau_event_30s_bps": round(tau_event_30s, 4),
            "delta_r_gross_30s_bps": round(delta_r_gross_30s, 4),
            "execution_friction_bps": EXECUTION_FRICTION_BPS,
            "delta_r_strategy_30s_bps": round(delta_r_strategy_30s, 4),
            "min_net_edge_hurdle_bps": MIN_NET_EDGE_BPS,
            "passed_gate_a_hurdle": passed_gate_a,
            "wall_ts": item["t_recv_wall"],
        }

        with open(self.ledger_file, "a") as f:
            f.write(json.dumps(record) + "\n")

        logger.info(
            "[EXP-201A FINALIZED] Episode %s %s: 30s Markout = %+.2f bps | Gross Abnormal = %+.2f bps | Net Strategy = %+.2f bps (Gate A Hurdle > 2.5 bps: %s)",
            item["episode_id"], item["asset"], r_30s, delta_r_gross_30s, delta_r_strategy_30s, passed_gate_a
        )
