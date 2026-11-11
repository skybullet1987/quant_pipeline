"""
Honest Event-Driven Pure-Riskless Backtester & Candidate-Triggered L2 Recorder
(`src/polymarket_research/honest_riskless_backtester.py`).

Implements Phase 1 of the Dominus Riskless Architecture Blueprint:
  1. `CompactCandidateL2Recorder`: Candidate-triggered (`gross_box <= 1.035` or `overround >= 0.975`)
     Top-5 L2 delta + WS trade-print ring-buffer recorder with `zstandard` / `gzip` compression and
     strict `< 12 MB/day` disk budget enforcement.
  2. `MakerQueueTradeThroughTracker`: FIFO queue-ahead & trade-through fill tracker for passive
     `postOnly` maker orders (`traded_through_shares >= queue_ahead_shares + order_shares`).
  3. `HonestClobExecutionKernel`: Exact Polymarket Protocol V2 share-haircut (`p / (1 - h(p))`),
     `0.001` boundary tick & 2-decimal `makerAmount` FOK quantization, `$1.00` / `5`-share minimums,
     asynchronous per-leg wire-RTT + `takerDelayMs` book lookup, and `3,500ms` `deferExec` ERC-1155
     settlement hold on raced single-leg unwinds.
  4. `ZeroLookaheadBacktestHarness`: Strict `visible_ts_ms`-ordered event-driven replay engine with
     hard anti-lookahead, anti-survivorship, and confirmed-scoreboard halftime assertions.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import gzip
import json
import math
from pathlib import Path
import time
from typing import Any, Callable, Deque, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

try:
    import zstandard as _zstd  # type: ignore
except ImportError:  # pragma: no cover
    _zstd = None

from src.polymarket_research.cross_venue_riskless_shadow import (
    DEFAULT_EXTERNAL_GAS_USD,
    DEFAULT_RELAY_BRIDGE_DRAG_BPS,
    DEFAULT_WIRE_LATENCY_MS,
    NormalizedBinaryMarket,
    OrderLevel,
    collateral_fx_ask_to_usd,
    collateral_fx_settle_floor_to_usd,
    compute_venue_taker_fee_usd,
    polymarket_v2_share_haircut_frac,
    relay_bridge_drag_usd,
    walk_asks_for_shares,
    walk_bids_for_unwind,
)


class LookaheadViolationError(RuntimeError):
    """Raised whenever an event or strategy attempts to access information not yet visible at `decision_ts_ms`."""


class SurvivorshipBiasError(RuntimeError):
    """Raised when a backtest dataset strips unresolved/disputed markets or leaks resolution status before expiry."""


# ---------------------------------------------------------------------------
# 1. Candidate-Triggered Top-5 L2 & Trade-Print Recorder (< 12 MB/day)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactL2Frame:
    ts_ms: int
    venue: str
    market_slug: str
    yes_asks: Tuple[Tuple[float, float], ...]
    yes_bids: Tuple[Tuple[float, float], ...]
    no_asks: Tuple[Tuple[float, float], ...]
    no_bids: Tuple[Tuple[float, float], ...]
    fee_rate_bps: float = 0.0
    taker_delay_ms: float = 0.0
    collateral_asset: str = "USDC"
    trigger_reason: str = ""
    recent_trades: Tuple[Tuple[int, str, float, float], ...] = ()  # (ts_ms, side, price, shares)


class CompactCandidateL2Recorder:
    """
    Bounded-RAM, candidate-triggered Top-5 L2 + WS trade-print recorder:
      - Maintains a rolling pre-trigger ring buffer (`pre_trigger_ring_max_frames`) per `(venue, slug)`.
      - Activates capture for `post_trigger_capture_ms` whenever an intra-market or cross-market pair
        reaches `gross_box <= trigger_gross_box_max` (`1.035`) or `overround >= trigger_overround_min` (`0.975`).
      - Compresses batches with `zstandard` when installed (else stdlib `gzip`) and enforces a hard
        `max_daily_bytes` (`12 MB/day` default) disk ceiling.
    """

    def __init__(
        self,
        output_dir: Path,
        *,
        top_k_levels: int = 5,
        trigger_gross_box_max: float = 1.035,
        trigger_overround_min: float = 0.975,
        pre_trigger_ring_max_frames: int = 32,
        post_trigger_capture_ms: int = 30_000,
        flush_batch_frames: int = 128,
        max_daily_bytes: int = 12 * 1024 * 1024,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.top_k_levels = max(1, min(10, int(top_k_levels)))
        self.trigger_gross_box_max = float(trigger_gross_box_max)
        self.trigger_overround_min = float(trigger_overround_min)
        self.pre_trigger_ring_max_frames = max(4, int(pre_trigger_ring_max_frames))
        self.post_trigger_capture_ms = max(1_000, int(post_trigger_capture_ms))
        self.flush_batch_frames = max(8, int(flush_batch_frames))
        self.max_daily_bytes = max(64 * 1024, int(max_daily_bytes))

        self._ring_by_key: Dict[Tuple[str, str], Deque[CompactL2Frame]] = {}
        self._recent_trades_by_key: Dict[Tuple[str, str], Deque[Tuple[int, str, float, float]]] = {}
        self._active_capture_until_ms: Dict[Tuple[str, str], int] = {}
        self._last_sig_by_key: Dict[Tuple[str, str], Tuple[Any, ...]] = {}
        self._pending_flush: List[CompactL2Frame] = []
        self._bytes_written_by_day: Dict[str, int] = {}
        self.frames_recorded: int = 0
        self.budget_drops: int = 0

    @staticmethod
    def _day_key(ts_ms: int) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(max(0.0, ts_ms / 1000.0)))

    def record_trade_print(
        self,
        *,
        venue: str,
        market_slug: str,
        side: str,
        price: float,
        shares: float,
        ts_ms: Optional[int] = None,
    ) -> None:
        if shares <= 0.0 or not (0.0 < price < 1.0):
            return
        cur_ms = int(time.time() * 1000) if ts_ms is None else int(ts_ms)
        k = (venue.strip().lower(), market_slug.strip())
        dq = self._recent_trades_by_key.setdefault(k, deque(maxlen=32))
        dq.append((cur_ms, side.strip().upper(), round(float(price), 6), round(float(shares), 4)))

    def _to_compact_frame(
        self,
        mkt: NormalizedBinaryMarket,
        ts_ms: int,
        trigger_reason: str = "",
    ) -> CompactL2Frame:
        k = (mkt.venue.lower(), mkt.slug)
        trades_dq = self._recent_trades_by_key.get(k)
        trades_tuple = tuple(trades_dq) if trades_dq else ()
        if trades_dq:
            trades_dq.clear()
        tk = self.top_k_levels
        return CompactL2Frame(
            ts_ms=ts_ms,
            venue=mkt.venue.lower(),
            market_slug=mkt.slug,
            yes_asks=tuple((round(x.price, 6), round(x.size, 4)) for x in mkt.yes_asks[:tk]),
            yes_bids=tuple((round(x.price, 6), round(x.size, 4)) for x in mkt.yes_bids[:tk]),
            no_asks=tuple((round(x.price, 6), round(x.size, 4)) for x in mkt.no_asks[:tk]),
            no_bids=tuple((round(x.price, 6), round(x.size, 4)) for x in mkt.no_bids[:tk]),
            fee_rate_bps=float(mkt.fee_rate_bps or 0.0),
            taker_delay_ms=float(mkt.taker_delay_ms or 0.0),
            collateral_asset=str(mkt.collateral_asset or "USDC"),
            trigger_reason=trigger_reason,
            recent_trades=trades_tuple,
        )

    def observe_markets(
        self,
        markets: Sequence[NormalizedBinaryMarket],
        *,
        candidate_keys: Sequence[Tuple[str, str]] = (),
        now_ms: Optional[int] = None,
    ) -> int:
        """
        Ingests a batch of normalized markets, deduplicates unchanged books, activates candidate windows
        whenever `gross_box <= 1.035` or `overround >= 0.975` (or explicit `candidate_keys`), and buffers
        delta frames for compressed disk flush.
        """
        cur_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        explicit_set = {(v.lower(), s) for v, s in candidate_keys}

        # Also check cross-market gross box across markets sharing `(category, asset, horizon)`
        by_group: Dict[Tuple[str, str, str], List[NormalizedBinaryMarket]] = {}
        for m in markets:
            if m.asset:
                by_group.setdefault((m.category, m.asset, m.horizon), []).append(m)

        group_triggered: Set[Tuple[str, str]] = set()
        for grp in by_group.values():
            if len(grp) < 2:
                continue
            min_ya = min((m.yes_asks[0].price for m in grp if m.yes_asks), default=1.0)
            min_na = min((m.no_asks[0].price for m in grp if m.no_asks), default=1.0)
            max_yb = max((m.yes_bids[0].price for m in grp if m.yes_bids), default=0.0)
            max_nb = max((m.no_bids[0].price for m in grp if m.no_bids), default=0.0)
            if (min_ya + min_na) <= self.trigger_gross_box_max or (max_yb + max_nb) >= self.trigger_overround_min:
                for m in grp:
                    group_triggered.add((m.venue.lower(), m.slug))

        emitted = 0
        for m in markets:
            key = (m.venue.lower(), m.slug)
            eff_ms = int(m.quote_ts_ms) if m.quote_ts_ms > 0 else cur_ms
            intra_box = (
                (m.yes_asks[0].price + m.no_asks[0].price)
                if (m.yes_asks and m.no_asks)
                else 9.99
            )
            intra_over = (
                (m.yes_bids[0].price + m.no_bids[0].price)
                if (m.yes_bids and m.no_bids)
                else 0.0
            )
            trig_reason = ""
            if key in explicit_set:
                trig_reason = "EXPLICIT_CANDIDATE"
            elif intra_box <= self.trigger_gross_box_max:
                trig_reason = f"INTRA_BOX_{intra_box:.4f}"
            elif intra_over >= self.trigger_overround_min:
                trig_reason = f"INTRA_OVERROUND_{intra_over:.4f}"
            elif key in group_triggered:
                trig_reason = "CROSS_VENUE_NEAR_ARB"

            frame = self._to_compact_frame(m, eff_ms, trigger_reason=trig_reason)
            sig = (frame.yes_asks, frame.yes_bids, frame.no_asks, frame.no_bids, frame.recent_trades)
            if self._last_sig_by_key.get(key) == sig and not trig_reason:
                continue
            self._last_sig_by_key[key] = sig

            if trig_reason:
                was_active = self._active_capture_until_ms.get(key, 0) >= eff_ms
                self._active_capture_until_ms[key] = max(
                    self._active_capture_until_ms.get(key, 0),
                    eff_ms + self.post_trigger_capture_ms,
                )
                if not was_active and key in self._ring_by_key:
                    while self._ring_by_key[key]:
                        self._pending_flush.append(self._ring_by_key[key].popleft())
                        emitted += 1
                self._pending_flush.append(frame)
                emitted += 1
            elif self._active_capture_until_ms.get(key, 0) >= eff_ms:
                self._pending_flush.append(frame)
                emitted += 1
            else:
                ring = self._ring_by_key.setdefault(key, deque(maxlen=self.pre_trigger_ring_max_frames))
                ring.append(frame)

        if len(self._pending_flush) >= self.flush_batch_frames:
            self.flush()
        return emitted

    def flush(self) -> Optional[Path]:
        if not self._pending_flush:
            return None
        batch = list(self._pending_flush)
        self._pending_flush.clear()
        day = self._day_key(batch[-1].ts_ms)
        used = self._bytes_written_by_day.get(day, 0)
        if used >= self.max_daily_bytes:
            self.budget_drops += len(batch)
            return None

        raw_jsonl = "\n".join(
            json.dumps(asdict(f), separators=(",", ":")) for f in batch
        ).encode("utf-8") + b"\n"

        if _zstd is not None:
            cctx = _zstd.ZstdCompressor(level=3)
            comp = cctx.compress(raw_jsonl)
            ext = "jsonl.zst"
        else:
            comp = gzip.compress(raw_jsonl, compresslevel=6)
            ext = "jsonl.gz"

        if used + len(comp) > self.max_daily_bytes:
            self.budget_drops += len(batch)
            return None

        out_path = self.output_dir / f"candidate_l2_{day}.{ext}"
        with open(out_path, "ab") as fh:
            fh.write(comp)

        self._bytes_written_by_day[day] = used + len(comp)
        self.frames_recorded += len(batch)
        return out_path

    @staticmethod
    def load_frames(path: Path) -> List[CompactL2Frame]:
        p = Path(path)
        raw_bytes = p.read_bytes()
        if p.name.endswith(".zst"):
            if _zstd is None:
                raise RuntimeError("zstandard is required to read .zst archives")
            dctx = _zstd.ZstdDecompressor()
            text = dctx.decompress(raw_bytes).decode("utf-8")
        elif p.name.endswith(".gz"):
            text = gzip.decompress(raw_bytes).decode("utf-8")
        else:
            text = raw_bytes.decode("utf-8")

        frames: List[CompactL2Frame] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            frames.append(
                CompactL2Frame(
                    ts_ms=int(d["ts_ms"]),
                    venue=str(d["venue"]),
                    market_slug=str(d["market_slug"]),
                    yes_asks=tuple((float(x[0]), float(x[1])) for x in d.get("yes_asks", ())),
                    yes_bids=tuple((float(x[0]), float(x[1])) for x in d.get("yes_bids", ())),
                    no_asks=tuple((float(x[0]), float(x[1])) for x in d.get("no_asks", ())),
                    no_bids=tuple((float(x[0]), float(x[1])) for x in d.get("no_bids", ())),
                    fee_rate_bps=float(d.get("fee_rate_bps", 0.0)),
                    taker_delay_ms=float(d.get("taker_delay_ms", 0.0)),
                    collateral_asset=str(d.get("collateral_asset", "USDC")),
                    trigger_reason=str(d.get("trigger_reason", "")),
                    recent_trades=tuple(
                        (int(t[0]), str(t[1]), float(t[2]), float(t[3]))
                        for t in d.get("recent_trades", ())
                    ),
                )
            )
        return frames


# ---------------------------------------------------------------------------
# 2. Passive Maker Queue-Ahead & Trade-Through Fill Tracker
# ---------------------------------------------------------------------------


@dataclass
class TrackedMakerOrder:
    order_id: str
    venue: str
    market_slug: str
    side: str  # "YES" or "NO" (buying outcome share passively at `bid_price`)
    bid_price: float
    order_shares: float
    placed_ts_ms: int
    initial_queue_ahead_shares: float
    remaining_queue_ahead_shares: float
    cumulative_traded_through_shares: float = 0.0
    filled_shares: float = 0.0
    last_observed_level_shares: float = 0.0
    canceled: bool = False

    @property
    def is_fully_filled(self) -> bool:
        return self.filled_shares >= self.order_shares - 1e-7


class MakerQueueTradeThroughTracker:
    """
    Conservative FIFO queue-position & trade-through tracker for passive `postOnly` maker bids:
      - On placement at `bid_price`: if `bid_price` improves current `best_bid`, `queue_ahead = 0`;
        otherwise `queue_ahead` equals total visible bid depth at `>= bid_price`.
      - `observe_trade_print`: trades at `price < bid_price` (or `price == bid_price` hitting bids)
        deplete `remaining_queue_ahead_shares` FIFO before crediting `filled_shares`.
      - `observe_book_snapshot`: ask prices crossing `<= bid_price` execute directly; pure L2 bid-size
        reductions without trade prints apply conservative `cancel_vs_fill_attribution_frac` (`0.25` default)
        so front-of-queue cancellations are NEVER over-credited as phantom fills.
    """

    def __init__(self, *, cancel_vs_fill_attribution_frac: float = 0.25) -> None:
        self.cancel_vs_fill_attribution_frac = min(1.0, max(0.0, float(cancel_vs_fill_attribution_frac)))
        self._orders: Dict[str, TrackedMakerOrder] = {}

    def place_maker_bid(
        self,
        *,
        order_id: str,
        market: NormalizedBinaryMarket,
        side: str,
        bid_price: float,
        order_shares: float,
        placed_ts_ms: int,
    ) -> Optional[TrackedMakerOrder]:
        side_u = side.strip().upper()
        asks = market.yes_asks if side_u == "YES" else market.no_asks
        bids = market.yes_bids if side_u == "YES" else market.no_bids
        # postOnly rejection check: cannot cross or touch resting ask!
        if asks and float(bid_price) >= asks[0].price - 1e-9:
            return None
        queue_ahead = sum(lvl.size for lvl in bids if lvl.price >= float(bid_price) - 1e-9)
        same_lvl_sh = sum(lvl.size for lvl in bids if abs(lvl.price - float(bid_price)) <= 1e-9)
        tracked = TrackedMakerOrder(
            order_id=order_id,
            venue=market.venue.lower(),
            market_slug=market.slug,
            side=side_u,
            bid_price=round(float(bid_price), 6),
            order_shares=float(order_shares),
            placed_ts_ms=int(placed_ts_ms),
            initial_queue_ahead_shares=queue_ahead,
            remaining_queue_ahead_shares=queue_ahead,
            last_observed_level_shares=same_lvl_sh,
        )
        self._orders[order_id] = tracked
        return tracked

    def cancel_order(self, order_id: str) -> Optional[TrackedMakerOrder]:
        od = self._orders.get(order_id)
        if od is not None:
            od.canceled = True
        return od

    def get_order(self, order_id: str) -> Optional[TrackedMakerOrder]:
        return self._orders.get(order_id)

    def _apply_flow(self, od: TrackedMakerOrder, flow_shares: float) -> float:
        if od.canceled or od.is_fully_filled or flow_shares <= 0.0:
            return 0.0
        od.cumulative_traded_through_shares += flow_shares
        consume_q = min(od.remaining_queue_ahead_shares, flow_shares)
        od.remaining_queue_ahead_shares -= consume_q
        rem_flow = flow_shares - consume_q
        if rem_flow <= 1e-9:
            return 0.0
        need = max(0.0, od.order_shares - od.filled_shares)
        newly_filled = min(need, rem_flow)
        od.filled_shares += newly_filled
        return newly_filled

    def observe_trade_print(
        self,
        *,
        venue: str,
        market_slug: str,
        outcome_side: str,
        trade_price: float,
        trade_shares: float,
        ts_ms: int,
        aggressor_side: str = "SELL",
    ) -> Dict[str, float]:
        """Updates matching resting maker bids from a real trade print at `ts_ms >= placed_ts_ms`."""
        v_low = venue.strip().lower()
        s_up = outcome_side.strip().upper()
        agg = aggressor_side.strip().upper()
        fills: Dict[str, float] = {}
        for oid, od in self._orders.items():
            if od.canceled or od.is_fully_filled or ts_ms < od.placed_ts_ms:
                continue
            if od.venue != v_low or od.market_slug != market_slug or od.side != s_up:
                continue
            if trade_price < od.bid_price - 1e-9 or (
                abs(trade_price - od.bid_price) <= 1e-9 and agg in ("SELL", "HIT_BID", "UNKNOWN")
            ):
                df = self._apply_flow(od, float(trade_shares))
                if df > 0.0:
                    fills[oid] = df
        return fills

    def observe_book_snapshot(self, market: NormalizedBinaryMarket, ts_ms: int) -> Dict[str, float]:
        v_low = market.venue.lower()
        fills: Dict[str, float] = {}
        for oid, od in self._orders.items():
            if od.canceled or od.is_fully_filled or ts_ms < od.placed_ts_ms:
                continue
            if od.venue != v_low or od.market_slug != market.slug:
                continue
            asks = market.yes_asks if od.side == "YES" else market.no_asks
            bids = market.yes_bids if od.side == "YES" else market.no_bids
            crossed_ask_sh = sum(lvl.size for lvl in asks if lvl.price <= od.bid_price + 1e-9)
            df = 0.0
            if crossed_ask_sh > 0.0:
                df += self._apply_flow(od, crossed_ask_sh)
            lvl_sh = sum(lvl.size for lvl in bids if abs(lvl.price - od.bid_price) <= 1e-9)
            higher_sh = sum(lvl.size for lvl in bids if lvl.price > od.bid_price + 1e-9)
            if higher_sh == 0.0 and lvl_sh < od.last_observed_level_shares and crossed_ask_sh == 0.0:
                drop = od.last_observed_level_shares - lvl_sh
                conservative_flow = drop * self.cancel_vs_fill_attribution_frac
                df += self._apply_flow(od, conservative_flow)
            od.last_observed_level_shares = lvl_sh
            if df > 0.0:
                fills[oid] = df
        return fills


# ---------------------------------------------------------------------------
# 3. Honest CLOB & Cross-Venue Sequential Execution Kernel
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SimulatedBoxExecution:
    locked: bool
    status: str
    decision_ts_ms: int
    net_paired_shares: float
    all_in_cost_usd: float
    guaranteed_min_payout_usd: float
    worst_state_net_pnl_usd: float
    unwind_bleed_usd: float
    leg_arrival_ts_ms: Tuple[int, ...]


class HonestClobExecutionKernel:
    """
    Simulates realistic sequential leg execution with:
      - Polymarket dynamic tick grid (`0.001` at `p <= 0.04` or `p >= 0.96`, else `0.01`)
      - Polymarket `min_shares >= 5.0` & `$1.00` marketable BUY notional floor + 2-decimal `makerAmount`
      - Exact Protocol V2 BUY share haircut (`delivered = gross * (1 - h(p))`)
      - Sequential fragile-leg-first or parallel leg arrival `decision_ts_ms + rtt_ms + taker_delay_ms`
      - `3,500ms` (`defer_exec_settlement_ms`) hold before newly bought Polymarket ERC-1155 shares
        can be sold into resting bids during an emergency leg-out unwind.
    """

    def __init__(
        self,
        *,
        wire_latency_ms: Optional[Mapping[str, float]] = None,
        defer_exec_settlement_ms: int = 3_500,
        bridge_drag_bps: float = DEFAULT_RELAY_BRIDGE_DRAG_BPS,
    ) -> None:
        self.wire_latency_ms: Dict[str, float] = dict(DEFAULT_WIRE_LATENCY_MS)
        self.wire_latency_ms.setdefault("forecastex", 65.0)
        self.wire_latency_ms.setdefault("stx_ontario", 35.0)
        if wire_latency_ms:
            for k, v in wire_latency_ms.items():
                self.wire_latency_ms[k.lower()] = float(v)
        self.defer_exec_settlement_ms = max(0, int(defer_exec_settlement_ms))
        self.bridge_drag_bps = float(bridge_drag_bps)

    @staticmethod
    def quantize_polymarket_fok_buy(net_shares: float, limit_price: float, fee_rate_bps: float = 0.0) -> Tuple[float, float, float, bool]:
        """
        Returns `(quantized_price, gross_shares, maker_amount_usd_2dec, valid_fok)` enforcing Polymarket's
        `0.001`/`0.01` tick grid, `5`-share minimum, `$1.00` marketable notional minimum, and 2-decimal USDC `makerAmount`.
        """
        p_clamped = min(0.999, max(0.001, float(limit_price)))
        tick = Decimal("0.001") if (p_clamped >= 0.96 or p_clamped <= 0.04) else Decimal("0.01")
        q_px = float((Decimal(str(round(p_clamped, 6))) / tick).to_integral_value(rounding=ROUND_CEILING) * tick)
        q_px = min(0.999, max(float(tick), round(q_px, 4)))

        h = polymarket_v2_share_haircut_frac(q_px, fee_rate_bps)
        req_gross = float(net_shares) / max(0.50, 1.0 - h)
        # Quantize gross shares on 0.01 step (or integer step on cent tick so gross*price has <= 2 decimals!)
        lot_step = Decimal("1") if tick == Decimal("0.01") else Decimal("10")
        # Try exact 0.01 lot first if `maker_amount` has <= 2 decimals, else step up to clean 2-decimal USDC lot
        cand_gross = float((Decimal(str(round(req_gross, 6))) / Decimal("0.01")).to_integral_value(rounding=ROUND_CEILING) * Decimal("0.01"))
        maker_amt = Decimal(str(round(cand_gross * q_px, 6)))
        if maker_amt != maker_amt.quantize(Decimal("0.01")):
            cand_gross = float((Decimal(str(round(req_gross, 6))) / lot_step).to_integral_value(rounding=ROUND_CEILING) * lot_step)
            maker_amt = (Decimal(str(cand_gross)) * Decimal(str(q_px))).quantize(Decimal("0.01"), rounding=ROUND_CEILING)

        maker_usd = float(maker_amt)
        delivered_net = cand_gross * max(0.50, 1.0 - h)
        valid = cand_gross >= 5.0 - 1e-9 and delivered_net >= 5.0 - 1e-9 and maker_usd >= 1.0 - 1e-9
        return (q_px, round(cand_gross, 4), round(maker_usd, 2), valid)

    def execute_two_leg_taker_box(
        self,
        *,
        decision_ts_ms: int,
        leg_a_venue: str,
        leg_a_slug: str,
        leg_a_side: str,
        leg_a_limit_px: float,
        leg_b_venue: str,
        leg_b_slug: str,
        leg_b_side: str,
        leg_b_limit_px: float,
        target_net_shares: float,
        unit_guaranteed_payout_usd: float,
        book_lookup_fn: Callable[[str, str, int], Optional[NormalizedBinaryMarket]],
        dispatch_mode: str = "FRAGILE_FIRST",
    ) -> SimulatedBoxExecution:
        """
        Executes a 2-leg box against the causal book timeline `book_lookup_fn(venue, slug, ts_ms)`:
          - `FRAGILE_FIRST`: sends slower / speed-bump leg first; if its FOK rejects cleanly, Leg 2 is
            never sent (`unwind_bleed = $0.00`). If Leg 1 fills, Leg 2 is dispatched upon fill confirmation!
          - `PARALLEL`: dispatches both legs at `decision_ts_ms`; if Leg 1 fills and Leg 2 rejects,
            unwinds Leg 1 after `defer_exec_settlement_ms` (on Polymarket) + wire RTT.
        """
        mkt_a_0 = book_lookup_fn(leg_a_venue, leg_a_slug, decision_ts_ms)
        mkt_b_0 = book_lookup_fn(leg_b_venue, leg_b_slug, decision_ts_ms)
        if mkt_a_0 is None or mkt_b_0 is None:
            return SimulatedBoxExecution(False, "MISSING_DECISION_BOOK", decision_ts_ms, 0.0, 0.0, 0.0, 0.0, 0.0, ())

        delay_a = int(round(self.wire_latency_ms.get(leg_a_venue.lower(), 80.0) + mkt_a_0.taker_delay_ms))
        delay_b = int(round(self.wire_latency_ms.get(leg_b_venue.lower(), 110.0) + mkt_b_0.taker_delay_ms))

        # Order legs so leg_1 is dispatched first when FRAGILE_FIRST (slower/delayed leg first)
        legs_cfg = [
            (leg_a_venue.lower(), leg_a_slug, leg_a_side.upper(), float(leg_a_limit_px), delay_a, mkt_a_0),
            (leg_b_venue.lower(), leg_b_slug, leg_b_side.upper(), float(leg_b_limit_px), delay_b, mkt_b_0),
        ]
        if dispatch_mode.upper() == "FRAGILE_FIRST" and delay_b > delay_a:
            legs_cfg.reverse()

        v1, s1, sd1, lim1, d1, m1_init = legs_cfg[0]
        v2, s2, sd2, lim2, d2, m2_init = legs_cfg[1]

        t_arr_1 = decision_ts_ms + d1
        t_arr_2 = (t_arr_1 + d2) if dispatch_mode.upper() == "FRAGILE_FIRST" else (decision_ts_ms + d2)

        fx_ask_1 = collateral_fx_ask_to_usd(m1_init.collateral_asset)
        fx_fl_1 = collateral_fx_settle_floor_to_usd(m1_init.collateral_asset)
        fx_ask_2 = collateral_fx_ask_to_usd(m2_init.collateral_asset)
        fx_fl_2 = collateral_fx_settle_floor_to_usd(m2_init.collateral_asset)

        req_sh_1 = math.ceil(target_net_shares / max(fx_fl_1, 1e-6)) if abs(fx_fl_1 - 1.0) > 1e-6 else target_net_shares
        req_sh_2 = math.ceil(target_net_shares / max(fx_fl_2, 1e-6)) if abs(fx_fl_2 - 1.0) > 1e-6 else target_net_shares

        if v1 == "polymarket":
            lim1, _, _, ok_q1 = self.quantize_polymarket_fok_buy(req_sh_1, lim1, m1_init.fee_rate_bps)
            if not ok_q1:
                return SimulatedBoxExecution(False, "LEG1_FOK_QUANTIZATION_REJECTED", decision_ts_ms, 0.0, 0.0, 0.0, 0.0, 0.0, (t_arr_1,))
        if v2 == "polymarket":
            lim2, _, _, ok_q2 = self.quantize_polymarket_fok_buy(req_sh_2, lim2, m2_init.fee_rate_bps)
            if not ok_q2:
                return SimulatedBoxExecution(False, "LEG2_FOK_QUANTIZATION_REJECTED", decision_ts_ms, 0.0, 0.0, 0.0, 0.0, 0.0, (t_arr_1, t_arr_2))

        m1_arr = book_lookup_fn(v1, s1, t_arr_1)
        if m1_arr is None:
            return SimulatedBoxExecution(False, "LEG1_BOOK_UNAVAILABLE", decision_ts_ms, 0.0, 0.0, 0.0, 0.0, 0.0, (t_arr_1,))
        asks_1 = m1_arr.yes_asks if sd1 == "YES" else m1_arr.no_asks
        w1 = walk_asks_for_shares(asks_1, req_sh_1, m1_arr, max_price=lim1)
        if not w1.filled:
            return SimulatedBoxExecution(False, "LEG1_FOK_KILLED_CLEANLY", decision_ts_ms, 0.0, 0.0, 0.0, 0.0, 0.0, (t_arr_1,))

        m2_arr = book_lookup_fn(v2, s2, t_arr_2)
        asks_2 = (m2_arr.yes_asks if sd2 == "YES" else m2_arr.no_asks) if m2_arr is not None else []
        w2 = walk_asks_for_shares(asks_2, req_sh_2, m2_arr, max_price=lim2) if m2_arr is not None else None

        if w2 is not None and w2.filled:
            cost_usd = (w1.gross_cost_usd + w1.taker_fee_usd) * fx_ask_1 + (w2.gross_cost_usd + w2.taker_fee_usd) * fx_ask_2
            gas_usd = DEFAULT_EXTERNAL_GAS_USD.get(v1, 0.002) + (0.0 if v1 == v2 else DEFAULT_EXTERNAL_GAS_USD.get(v2, 0.005))
            bridge_usd = 0.0 if v1 == v2 else relay_bridge_drag_usd(cost_usd, self.bridge_drag_bps)
            all_in = cost_usd + gas_usd + bridge_usd
            net_pairs = min(w1.filled_shares * fx_fl_1, w2.filled_shares * fx_fl_2)
            min_payout = net_pairs * float(unit_guaranteed_payout_usd)
            net_pnl = min_payout - all_in
            return SimulatedBoxExecution(
                locked=net_pnl > 0.0,
                status="LOCKED_RISKLESS_BOX" if net_pnl > 0.0 else "NEGATIVE_POST_FILL_NET_EDGE",
                decision_ts_ms=decision_ts_ms,
                net_paired_shares=round(net_pairs, 4),
                all_in_cost_usd=round(all_in, 6),
                guaranteed_min_payout_usd=round(min_payout, 6),
                worst_state_net_pnl_usd=round(net_pnl, 6),
                unwind_bleed_usd=0.0,
                leg_arrival_ts_ms=(t_arr_1, t_arr_2),
            )

        # Leg 1 filled, Leg 2 failed -> simulate honest emergency unwind of Leg 1 AFTER settlement hold (`deferExec` on Polymarket)!
        hold_ms = self.defer_exec_settlement_ms if v1 == "polymarket" else 0
        rtt_unwind = int(round(self.wire_latency_ms.get(v1, 80.0)))
        t_unwind = max(t_arr_2, t_arr_1 + hold_ms) + rtt_unwind
        m1_unwind = book_lookup_fn(v1, s1, t_unwind) or m1_arr
        bids_1 = m1_unwind.yes_bids if sd1 == "YES" else m1_unwind.no_bids
        proceeds_1_local, _ = walk_bids_for_unwind(bids_1, w1.filled_shares, m1_unwind)
        paid_1_usd = (w1.gross_cost_usd + w1.taker_fee_usd) * fx_ask_1 + DEFAULT_EXTERNAL_GAS_USD.get(v1, 0.002)
        proceeds_1_usd = proceeds_1_local * fx_fl_1
        bleed = max(0.0, paid_1_usd - proceeds_1_usd)
        return SimulatedBoxExecution(
            locked=False,
            status="LEG2_MISSED_DEFER_EXEC_UNWOUND",
            decision_ts_ms=decision_ts_ms,
            net_paired_shares=0.0,
            all_in_cost_usd=round(paid_1_usd, 6),
            guaranteed_min_payout_usd=0.0,
            worst_state_net_pnl_usd=round(-bleed, 6),
            unwind_bleed_usd=round(bleed, 6),
            leg_arrival_ts_ms=(t_arr_1, t_arr_2, t_unwind),
        )


# ---------------------------------------------------------------------------
# 4. Zero-Lookahead Event-Driven Backtest Harness
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BacktestEvent:
    visible_ts_ms: int          # Timestamp when Dominus actually receives/observes the event
    source_event_ts_ms: int     # Exchange/oracle generation timestamp (`visible_ts_ms >= source_event_ts_ms` REQUIRED!)
    event_type: str             # "BOOK_SNAPSHOT" | "TRADE_PRINT" | "SCOREBOARD_UPDATE" | "ORACLE_OBSERVATION" | "RESOLUTION_FINALIZED"
    payload: Any
    seq_no: int = 0


@dataclass(frozen=True)
class HonestBacktestReport:
    events_processed: int
    signals_generated: int
    boxes_locked: int
    leg_out_unwinds: int
    total_guaranteed_min_pnl_usd: float
    total_unwind_bleed_usd: float
    net_worst_case_pnl_usd: float
    min_single_trade_worst_state_pnl_usd: float
    zero_lookahead_verified: bool
    no_survivorship_verified: bool


class ZeroLookaheadBacktestHarness:
    """
    Event-driven pure-riskless replay engine enforcing strict temporal causality:
      1. Every `BacktestEvent` must satisfy `visible_ts_ms >= source_event_ts_ms` (raises `LookaheadViolationError` otherwise).
      2. Strategy callbacks only ever see causal book/oracle/scoreboard state with `visible_ts_ms <= decision_ts_ms`,
         while `HonestClobExecutionKernel` evaluates post-submission fills at `t_arrival > decision_ts_ms`.
      3. Rejects survivorship-biased market metadata (`umaResolutionStatus == "resolved"` or winner leaked prior to `end_ts`).
      4. Requires explicit `SCOREBOARD_UPDATE` confirmation (`is_halftime=True, clock_sec=0.0`) before halftime strategies fire.
    """

    def __init__(self, kernel: Optional[HonestClobExecutionKernel] = None) -> None:
        self.kernel = kernel or HonestClobExecutionKernel()
        self.maker_tracker = MakerQueueTradeThroughTracker()
        self._timeline_books: Dict[Tuple[str, str], List[Tuple[int, NormalizedBinaryMarket]]] = {}
        self._visible_books: Dict[Tuple[str, str], NormalizedBinaryMarket] = {}
        self._visible_scoreboards: Dict[str, Dict[str, Any]] = {}
        self._visible_oracles: Dict[str, Dict[str, Any]] = {}
        self._current_decision_ts_ms: int = 0

    @staticmethod
    def validate_dataset_no_survivorship_bias(markets_meta: Sequence[Mapping[str, Any]]) -> bool:
        """
        Ensures historical market metadata was NOT pre-filtered to `umaResolutionStatus == 'resolved'` winners
        or stripped of disputed/voided contracts prior to market expiration.
        """
        if not markets_meta:
            return True
        statuses = set()
        for m in markets_meta:
            snap_ts = float(m.get("snapshot_ts") or 0.0)
            end_ts = float(m.get("end_ts") or 0.0)
            uma_st = str(m.get("umaResolutionStatus") or "").strip().lower()
            statuses.add(uma_st or "unresolved")
            if snap_ts > 0.0 and end_ts > 0.0 and snap_ts < end_ts and uma_st == "resolved":
                raise SurvivorshipBiasError(
                    f"Market {m.get('slug') or m.get('market_id')} leaked umaResolutionStatus='resolved' at {snap_ts} < end_ts {end_ts}"
                )
            if snap_ts > 0.0 and end_ts > 0.0 and snap_ts < end_ts and m.get("resolved_winner") is not None:
                raise SurvivorshipBiasError(
                    f"Market {m.get('slug') or m.get('market_id')} leaked resolved_winner before end_ts"
                )
        if len(markets_meta) >= 5 and statuses == {"resolved"}:
            raise SurvivorshipBiasError(
                "Dataset contains >=5 markets with 100% pre-filtered umaResolutionStatus='resolved' (survivorship bias)"
            )
        return True

    def get_visible_book(self, venue: str, slug: str, query_ts_ms: int) -> Optional[NormalizedBinaryMarket]:
        if query_ts_ms > self._current_decision_ts_ms:
            raise LookaheadViolationError(
                f"Strategy queried book at {query_ts_ms}ms > current_decision_ts_ms {self._current_decision_ts_ms}ms"
            )
        return self._lookup_book_at(venue, slug, query_ts_ms)

    def verify_halftime_state_confirmed(self, matchup_key: str, *, min_remaining_intermission_sec: float = 480.0) -> bool:
        """True ONLY if a causal `SCOREBOARD_UPDATE` confirmed `is_halftime=True` & `clock_sec == 0` with `>= 480s` left."""
        sb = self._visible_scoreboards.get(matchup_key)
        if not isinstance(sb, Mapping):
            return False
        if not bool(sb.get("is_halftime", False)):
            return False
        if abs(float(sb.get("clock_sec", -1.0))) > 1e-6:
            return False
        elapsed_since_ht = max(0.0, (self._current_decision_ts_ms - int(sb.get("halftime_started_ts_ms", self._current_decision_ts_ms))) / 1000.0)
        rem_intermission = float(sb.get("scheduled_intermission_sec", 900.0)) - elapsed_since_ht
        return rem_intermission >= float(min_remaining_intermission_sec)

    def _lookup_book_at(self, venue: str, slug: str, ts_ms: int) -> Optional[NormalizedBinaryMarket]:
        hist = self._timeline_books.get((venue.lower(), slug))
        if not hist:
            return None
        lo, hi = 0, len(hist) - 1
        ans: Optional[NormalizedBinaryMarket] = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if hist[mid][0] <= ts_ms:
                ans = hist[mid][1]
                lo = mid + 1
            else:
                hi = mid - 1
        return ans

    def run(
        self,
        events: Sequence[BacktestEvent],
        strategy_fn: Callable[["ZeroLookaheadBacktestHarness", int, Mapping[Tuple[str, str], NormalizedBinaryMarket]], Sequence[Mapping[str, Any]]],
        *,
        markets_meta: Sequence[Mapping[str, Any]] = (),
    ) -> HonestBacktestReport:
        """
        Replays `events` in strict `(visible_ts_ms, seq_no)` order, invokes `strategy_fn(harness, decision_ts_ms, visible_books)`
        on each visible update, and executes emitted 2-leg box intents through `HonestClobExecutionKernel` against the true
        post-latency timeline.
        """
        no_surv = self.validate_dataset_no_survivorship_bias(markets_meta)

        ordered = sorted(events, key=lambda e: (int(e.visible_ts_ms), int(e.seq_no)))
        self._timeline_books.clear()
        self._visible_books.clear()
        self._visible_scoreboards.clear()
        self._visible_oracles.clear()

        for ev in ordered:
            if int(ev.visible_ts_ms) < int(ev.source_event_ts_ms):
                raise LookaheadViolationError(
                    f"Event {ev.event_type} has visible_ts_ms={ev.visible_ts_ms} < source_event_ts_ms={ev.source_event_ts_ms}"
                )
            if ev.event_type == "BOOK_SNAPSHOT" and isinstance(ev.payload, NormalizedBinaryMarket):
                mkt = ev.payload
                self._timeline_books.setdefault((mkt.venue.lower(), mkt.slug), []).append((int(ev.visible_ts_ms), mkt))

        signals_count = 0
        locked_count = 0
        unwind_count = 0
        guaranteed_pnl_sum = 0.0
        unwind_bleed_sum = 0.0
        min_locked_trade_pnl: Optional[float] = None
        executed_keys: set[str] = set()

        for ev in ordered:
            ts_ms = int(ev.visible_ts_ms)
            self._current_decision_ts_ms = ts_ms

            if ev.event_type == "BOOK_SNAPSHOT" and isinstance(ev.payload, NormalizedBinaryMarket):
                mkt = ev.payload
                self._visible_books[(mkt.venue.lower(), mkt.slug)] = mkt
                self.maker_tracker.observe_book_snapshot(mkt, ts_ms)
            elif ev.event_type == "TRADE_PRINT" and isinstance(ev.payload, Mapping):
                tp = ev.payload
                self.maker_tracker.observe_trade_print(
                    venue=str(tp.get("venue") or ""),
                    market_slug=str(tp.get("market_slug") or ""),
                    outcome_side=str(tp.get("side") or "YES"),
                    trade_price=float(tp.get("price") or 0.0),
                    trade_shares=float(tp.get("shares") or 0.0),
                    ts_ms=ts_ms,
                    aggressor_side=str(tp.get("aggressor_side") or "SELL"),
                )
            elif ev.event_type == "SCOREBOARD_UPDATE" and isinstance(ev.payload, Mapping):
                mk = str(ev.payload.get("matchup_key") or "")
                if mk:
                    self._visible_scoreboards[mk] = dict(ev.payload)
            elif ev.event_type == "ORACLE_OBSERVATION" and isinstance(ev.payload, Mapping):
                ok = str(ev.payload.get("oracle_key") or "")
                if ok:
                    self._visible_oracles[ok] = dict(ev.payload)

            intents = strategy_fn(self, ts_ms, dict(self._visible_books))
            for intent in intents or ():
                dedupe_k = str(intent.get("dedupe_key") or "")
                if dedupe_k and dedupe_k in executed_keys:
                    continue
                if dedupe_k:
                    executed_keys.add(dedupe_k)
                signals_count += 1
                res = self.kernel.execute_two_leg_taker_box(
                    decision_ts_ms=ts_ms,
                    leg_a_venue=str(intent["leg_a_venue"]),
                    leg_a_slug=str(intent["leg_a_slug"]),
                    leg_a_side=str(intent["leg_a_side"]),
                    leg_a_limit_px=float(intent["leg_a_limit_px"]),
                    leg_b_venue=str(intent["leg_b_venue"]),
                    leg_b_slug=str(intent["leg_b_slug"]),
                    leg_b_side=str(intent["leg_b_side"]),
                    leg_b_limit_px=float(intent["leg_b_limit_px"]),
                    target_net_shares=float(intent.get("shares", 10.0)),
                    unit_guaranteed_payout_usd=float(intent.get("unit_guaranteed_payout_usd", 1.0)),
                    book_lookup_fn=self._lookup_book_at,
                    dispatch_mode=str(intent.get("dispatch_mode", "FRAGILE_FIRST")),
                )
                if res.locked:
                    locked_count += 1
                    guaranteed_pnl_sum += res.worst_state_net_pnl_usd
                    if min_locked_trade_pnl is None or res.worst_state_net_pnl_usd < min_locked_trade_pnl:
                        min_locked_trade_pnl = res.worst_state_net_pnl_usd
                elif res.unwind_bleed_usd > 0.0:
                    unwind_count += 1
                    unwind_bleed_sum += res.unwind_bleed_usd

        net_total = guaranteed_pnl_sum - unwind_bleed_sum
        return HonestBacktestReport(
            events_processed=len(ordered),
            signals_generated=signals_count,
            boxes_locked=locked_count,
            leg_out_unwinds=unwind_count,
            total_guaranteed_min_pnl_usd=round(guaranteed_pnl_sum, 6),
            total_unwind_bleed_usd=round(unwind_bleed_sum, 6),
            net_worst_case_pnl_usd=round(net_total, 6),
            min_single_trade_worst_state_pnl_usd=round(min_locked_trade_pnl if min_locked_trade_pnl is not None else 0.0, 6),
            zero_lookahead_verified=True,
            no_survivorship_verified=no_surv,
        )
