"""
Layer 4: Authoritative Exchange Position Reconciliation & 4-Clock Latency Supervisor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class LatencyProfile:
    t_signal_ns: int
    t_submit_ns: int = 0
    t_ack_ns: int = 0
    t_fill_ns: int = 0

    @property
    def internal_latency_ms(self) -> float:
        return (self.t_submit_ns - self.t_signal_ns) / 1_000_000.0 if self.t_submit_ns > 0 else 0.0

    @property
    def rtt_exchange_ms(self) -> float:
        return (self.t_ack_ns - self.t_submit_ns) / 1_000_000.0 if self.t_ack_ns > 0 else 0.0

    @property
    def fill_latency_ms(self) -> float:
        return (self.t_fill_ns - self.t_ack_ns) / 1_000_000.0 if self.t_fill_ns > 0 else 0.0

    @property
    def total_latency_ms(self) -> float:
        return (self.t_fill_ns - self.t_signal_ns) / 1_000_000.0 if self.t_fill_ns > 0 else 0.0


@dataclass(frozen=True)
class PositionState:
    symbol: str
    net_size: float
    entry_px: float
    unrealized_pnl: float
    liquidation_px: float | None = None


class PositionReconciler:
    """
    Authoritative state reconciler:
    Validates internal target positions against authoritative exchange state feeds.
    Halts execution if position divergence exceeds max_position_divergence_pct.
    """
    def __init__(
        self,
        max_position_divergence_pct: float = 0.05,
        max_rtt_latency_ms: float = 250.0,
        max_unacked_orders: int = 5,
    ):
        self.max_position_divergence_pct = max_position_divergence_pct
        self.max_rtt_latency_ms = max_rtt_latency_ms
        self.max_unacked_orders = max_unacked_orders
        
        self.internal_positions: dict[str, float] = {}
        self.exchange_positions: dict[str, PositionState] = {}
        self.latency_records: dict[str, LatencyProfile] = {}
        self.unacked_order_count = 0
        self.is_circuit_broken = False
        self.circuit_break_reason: str | None = None

    def record_signal(self, cl_ord_id: str, t_signal_ns: int) -> None:
        self.latency_records[cl_ord_id] = LatencyProfile(t_signal_ns=t_signal_ns)

    def record_submit(self, cl_ord_id: str, t_submit_ns: int | None = None) -> None:
        now_ns = t_submit_ns or time.time_ns()
        if cl_ord_id in self.latency_records:
            self.latency_records[cl_ord_id].t_submit_ns = now_ns
        self.unacked_order_count += 1
        if self.unacked_order_count > self.max_unacked_orders:
            self.trigger_circuit_breaker(f"Unacknowledged order threshold ({self.max_unacked_orders}) breached.")

    def record_ack(self, cl_ord_id: str, t_ack_ns: int | None = None) -> None:
        now_ns = t_ack_ns or time.time_ns()
        self.unacked_order_count = max(0, self.unacked_order_count - 1)
        if cl_ord_id in self.latency_records:
            profile = self.latency_records[cl_ord_id]
            profile.t_ack_ns = now_ns
            if profile.rtt_exchange_ms > self.max_rtt_latency_ms:
                self.trigger_circuit_breaker(
                    f"Exchange RTT latency ({profile.rtt_exchange_ms:.1f}ms) exceeded {self.max_rtt_latency_ms}ms limit."
                )

    def record_fill(self, cl_ord_id: str, symbol: str, fill_size: float, is_buy: bool, t_fill_ns: int | None = None) -> None:
        now_ns = t_fill_ns or time.time_ns()
        if cl_ord_id in self.latency_records:
            self.latency_records[cl_ord_id].t_fill_ns = now_ns
        
        delta = fill_size if is_buy else -fill_size
        self.internal_positions[symbol] = self.internal_positions.get(symbol, 0.0) + delta

    def reconcile_exchange_state(self, exchange_feed: dict[str, PositionState]) -> bool:
        self.exchange_positions = exchange_feed
        
        for symbol, internal_qty in self.internal_positions.items():
            ex_pos = exchange_feed.get(symbol)
            ex_qty = ex_pos.net_size if ex_pos else 0.0
            
            diff = abs(internal_qty - ex_qty)
            denom = max(abs(internal_qty), abs(ex_qty), 1e-4)
            pct_diff = diff / denom

            if pct_diff > self.max_position_divergence_pct and diff > 1e-4:
                self.trigger_circuit_breaker(
                    f"Position divergence on {symbol}: internal={internal_qty:.4f}, exchange={ex_qty:.4f} (diff={pct_diff:.2%})"
                )
                return False

        return True

    def trigger_circuit_breaker(self, reason: str) -> None:
        self.is_circuit_broken = True
        self.circuit_break_reason = reason

    def reset_circuit_breaker(self) -> None:
        self.is_circuit_broken = False
        self.circuit_break_reason = None
        self.unacked_order_count = 0
