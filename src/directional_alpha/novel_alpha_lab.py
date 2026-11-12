"""Agent H — Novel Alpha Research Laboratory (`src/directional_alpha/novel_alpha_lab.py`).

Maintains the 28-hypothesis Directional Alpha Registry (`HYP-001`..`HYP-028`) and implements
14 distinct, falsifiable, strictly causal empirical directional alpha experiments across:
  1. Cross-Contract Information Propagation Lag (`HYP-001` Deadline Term Lag, `HYP-003` Strike Kink)
  2. Multi-Outcome NegRisk Residual Drift (`HYP-005` Sum-Excess Secondary NO, `HYP-006` Crash Underround YES,
     `HYP-007` Open-Partition Augmented Contender NO)
  3. New-Market Price Discovery Bias (`HYP-009` <24h Ignorance-Prior NO, `HYP-010` First-6h Smart-Flow Drift)
  4. Asymmetric News / Jump Response (`HYP-012` Narrative Up-Spike Fade, `HYP-013` Down-Crash Disposition Drift,
     `HYP-014` Objective vs Narrative Jump Asymmetry)
  5. Decomposed Favorite-Longshot & Polarity Bias (`HYP-016` Narrative Zero/Low-Fee Longshot NO,
     `HYP-018` Semantic Polarity Inversion Audit)
  6. Resolution-Proximity Theta Distortion (`HYP-020` Objective Impatience Favorite Carry,
     `HYP-021` Dying-Catalyst Poisson Theta Decay)
  7. Specialist Domain & Meta-Conviction Models (`HYP-023` Weather Horizon/Rounding Calibration,
     `HYP-024` Cross-Venue Consensus Probability Anchor, `HYP-027` Epistemic Disagreement Abstention Ensemble)

Strict Red-Team Invariants (`RT-01` .. `RT-14`):
  - Zero backward future-price peeking: entries gated strictly by causal forward first-passage
    and metadata `safe_decision_cutoff_ts`; all pre-cutoff post-entry ticks remain visible to
    `PRE_RESOLUTION_EXIT` so target/stop exits ALWAYS pay realistic exit half-spread + slippage + V2 fee.
  - Zero post-hoc void/dispute filtering: all `is_void_or_50_50=1` (`0.50` payout) and past-expiry
    `is_disputed_or_frozen=1` (`0.00` conservative floor per `D-009`) contracts remain eligible at entry.
  - Exact Protocol V2 curved fees via `execution_microstructure.resolve_fee_schedule` &
    `estimate_historical_taker_execution` (never treating `1000` as 10% bps and never defaulting to 0% fee).
  - Pure Python 3.12 stdlib compatible (optional `orjson` acceleration; zero `numpy`/`pandas`).
"""

from __future__ import annotations

import collections
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3
import statistics
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    import orjson as _orjson  # type: ignore
except ImportError:  # pragma: no cover
    _orjson = None

from directional_alpha.execution_microstructure import (
    estimate_historical_taker_execution,
    resolve_fee_schedule,
    validate_and_quantize_order_lot,
)
from directional_alpha.probability_and_payoff import (
    brier_skill_score,
    log_loss_skill_score,
    resolve_side_probability,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "directional_alpha"
DEFAULT_HISTORICAL_DB = DEFAULT_DATA_DIR / "historical_dataset.sqlite3"
DEFAULT_MANIFEST_JSON = DEFAULT_DATA_DIR / "data_audit_manifest.json"
DEFAULT_HYPOTHESIS_REGISTRY_JSON = DEFAULT_DATA_DIR / "hypothesis_registry.json"
DEFAULT_NOVEL_RESULTS_JSON = DEFAULT_DATA_DIR / "novel_alpha_results.json"
DEFAULT_CORE_RESULTS_JSON = DEFAULT_DATA_DIR / "core_strategy_results.json"

# Global chronological 50% / 25% / 25% split anchors from `data_audit_manifest.json` (`RT-11`)
GLOBAL_TRAIN_END_TS: float = 1791252025.0
GLOBAL_VAL_END_TS: float = 1794052848.0
DEFAULT_EMBARGO_SEC: float = 3600.0
CAUSAL_EXTREME_ENTRY_BAND: float = 0.02

# Frozen live D-001 market IDs (never place live orders; kept in historical dataset for honest D-009 0.00 dispute payout!)
FROZEN_KMIA_MARKET_IDS: frozenset[str] = frozenset({"6707502", "6707503"})

NARRATIVE_CATEGORIES: frozenset[str] = frozenset(
    {"politics", "geopolitics", "culture_science", "tech_ai"}
)
OBJECTIVE_FAST_CATEGORIES: frozenset[str] = frozenset(
    {"sports", "crypto", "finance", "economics_macro", "weather"}
)


def json_loads(raw: bytes | str) -> Any:
    if _orjson is not None:
        return _orjson.loads(raw)
    return json.loads(raw)


def json_dumps_pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(val)))


def _logit(p: float, eps: float = 1e-5) -> float:
    pc = _clamp(p, eps, 1.0 - eps)
    return math.log(pc / (1.0 - pc))


def _sigmoid(z: float) -> float:
    if z >= 0.0:
        ez = math.exp(-min(z, 60.0))
        return 1.0 / (1.0 + ez)
    ez = math.exp(max(z, -60.0))
    return ez / (1.0 + ez)


@dataclass(frozen=True)
class CausalTick:
    ts: float
    p_yes: float
    sec_since_created: float
    sec_to_safe_cutoff: float
    life_frac: float
    quality_class: str


@dataclass
class NovelContractSeries:
    market_id: str
    event_id: str
    event_slug: str
    market_slug: str
    condition_id: str
    cluster_id: str
    category: str
    subcategory: str
    question: str
    has_negation: bool
    semantic_type: str
    neg_risk: bool
    is_other_or_placeholder: bool
    resolution_source: str
    created_ts: float
    scheduled_end_ts: Optional[float]
    closed_ts: Optional[float]
    effective_cutoff_ts: float
    safe_decision_cutoff_ts: float
    duration_hours: float
    volume_usd: float
    liquidity_usd: float
    fees_enabled: bool
    fee_type: str
    fee_rate: float
    fee_exponent: float
    maker_rebate_rate: float
    tick_size: float
    min_order_size: float
    yes_payout: float  # Continuous in [0.0, 1.0]: 1.0 YES win, 0.0 NO win/disputed, 0.50 50-50 void
    no_payout: float   # Continuous in [0.0, 1.0]: 1.0 NO win, 0.0 YES win/disputed, 0.50 50-50 void
    is_void_50_50: bool
    is_disputed: bool
    ticks: List[CausalTick] = field(default_factory=list)
    causal_first_extreme_ts: Optional[float] = None
    extracted_threshold: Optional[float] = None
    extracted_deadline_rank: Optional[float] = None
    neg_risk_augmented_inferred: bool = False
    registry_total_market_count: int = 1

    def is_entry_causal_at(self, idx: int, min_rem_sec: float = 600.0) -> bool:
        """Strictly causal entry check (`RT-01` & `#12` compliant): never peeks forward."""
        if idx < 0 or idx >= len(self.ticks):
            return False
        tk = self.ticks[idx]
        if tk.ts >= self.safe_decision_cutoff_ts - max(60.0, float(min_rem_sec)):
            return False
        if self.scheduled_end_ts is not None and self.scheduled_end_ts > 0:
            if tk.ts >= self.scheduled_end_ts - max(60.0, float(min_rem_sec)):
                return False
        if self.causal_first_extreme_ts is not None and tk.ts >= self.causal_first_extreme_ts - 1e-6:
            return False
        if not (CAUSAL_EXTREME_ENTRY_BAND <= tk.p_yes <= 1.0 - CAUSAL_EXTREME_ENTRY_BAND):
            return False
        return True


# ---------------------------------------------------------------------------
# 1. Contract Metadata & Threshold / Deadline / Weather Extraction Helpers
# ---------------------------------------------------------------------------

_NUM_SCALAR_RE = re.compile(
    r"(?:\$\s*)?([+-]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|m|b|t|°?[fc]|%|bps)?",
    re.IGNORECASE,
)
_MONTH_MAP: Dict[str, int] = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_DEADLINE_BY_RE = re.compile(
    r"\b(?:by|before|prior\s+to|on\s+or\s+before|in)\s+"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"(?:\s+(\d{1,2})(?!\d))?(?:,?\s*(202\d))?",
    re.IGNORECASE,
)
_TEMP_RANGE_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*°?\s*([fc])?\s*(?:to|[-–]|and)\s*(-?\d+(?:\.\d+)?)\s*°?\s*([fc])",
    re.IGNORECASE,
)
_TEMP_BOUND_RE = re.compile(
    r"(?:above|over|at\s+least|higher\s+than|or\s+higher|>=|below|under|at\s+most|lower\s+than|or\s+lower|<=)\s*"
    r"(-?\d+(?:\.\d+)?)\s*°?\s*([fc])",
    re.IGNORECASE,
)
_AUGMENTED_HINT_RE = re.compile(
    r"\b(?:next\s+pope|next\s+ceo|who\s+will\s+be\s+(?:appointed|named|nominated|selected)|"
    r"acquire|buy\s+tiktok|nobel|person\s+of\s+the\s+year|oscars?|grammys?)\b",
    re.IGNORECASE,
)
_OBJECTIVE_SOURCE_RE = re.compile(
    r"\b(?:binance|chainlink|coinbase|pyth|federal\s+reserve|bls\.gov|bea\.gov|"
    r"noaa|wunderground|metar|espn|nba\.com|nfl\.com|mlb\.com|associated\s+press|official\s+box)\b",
    re.IGNORECASE,
)


def extract_numeric_threshold(question: str) -> Optional[float]:
    """Extracts primary strike/threshold numeric value (scaling k/m/b/t suffixes)."""
    q = str(question or "")
    for m in _NUM_SCALAR_RE.finditer(q):
        raw_n = m.group(1).replace(",", "")
        suf = (m.group(2) or "").lower()
        try:
            val = float(raw_n)
        except ValueError:
            continue
        if 2020 <= val <= 2035 and not suf:
            continue
        mult = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}.get(suf, 1.0)
        return val * mult
    return None


def extract_deadline_ordinal(question: str, scheduled_end_ts: Optional[float]) -> Optional[float]:
    """Extracts comparable deadline timestamp/ordinal for cumulative deadline term-structure series."""
    m = _DEADLINE_BY_RE.search(str(question or ""))
    if m:
        mon = _MONTH_MAP.get(m.group(1).lower()[:3], 0)
        day = int(m.group(2)) if m.group(2) else 28
        yr = int(m.group(3)) if m.group(3) else 2026
        if mon > 0:
            try:
                return datetime(yr, mon, min(28, max(1, day)), tzinfo=timezone.utc).timestamp()
            except ValueError:
                pass
    if scheduled_end_ts is not None and scheduled_end_ts > 0:
        return float(scheduled_end_ts)
    return None


def is_objective_resolution_contract(contract: NovelContractSeries) -> bool:
    """Identifies contracts governed by deterministic feeds/official scoreboards vs subjective wording."""
    if contract.category in ("crypto", "sports", "economics_macro", "finance"):
        return True
    blob = f"{contract.resolution_source} {contract.question}"
    return bool(_OBJECTIVE_SOURCE_RE.search(blob))


# ---------------------------------------------------------------------------
# 2. Causal SQLite Loader & Realistic Execution / Lifecycle Simulator
# ---------------------------------------------------------------------------


def load_causal_dataset(
    db_path: Path = DEFAULT_HISTORICAL_DB,
    manifest_path: Path = DEFAULT_MANIFEST_JSON,
    registry_db_path: Optional[Path] = None,
) -> Tuple[List[NovelContractSeries], Dict[str, Any]]:
    """Loads all resolved contracts and strictly leak-free trajectories in read-only mode."""
    p = Path(db_path).resolve()
    uri = f"file:{p.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    augmented_events: set[str] = set()
    event_leg_counts: Dict[str, int] = {}
    reg_path = registry_db_path or (REPO_ROOT / "data" / "universe" / "market_registry.sqlite3")
    if reg_path.exists():
        try:
            rc = sqlite3.connect(f"file:{reg_path.resolve().as_posix()}?mode=ro", uri=True)
            for eid, n_aug, has_oth, tot_cnt in rc.execute(
                "SELECT event_id, neg_risk_augmented, has_other_outcome, total_market_count FROM events"
            ):
                s_eid = str(eid)
                if n_aug or has_oth:
                    augmented_events.add(s_eid)
                if tot_cnt is not None:
                    event_leg_counts[s_eid] = max(1, int(tot_cnt))
            rc.close()
        except Exception:
            pass

    split_meta: Dict[str, Any] = {
        "train_end_ts": GLOBAL_TRAIN_END_TS,
        "val_end_ts": GLOBAL_VAL_END_TS,
        "embargo_sec": DEFAULT_EMBARGO_SEC,
    }
    if Path(manifest_path).exists():
        try:
            man = json_loads(Path(manifest_path).read_bytes())
            anc = man.get("chronological_split_anchors") or {}
            if anc.get("train_50pct_end_ts"):
                split_meta["train_end_ts"] = float(anc["train_50pct_end_ts"])
            if anc.get("val_75pct_end_ts"):
                split_meta["val_end_ts"] = float(anc["val_75pct_end_ts"])
        except Exception:
            pass

    rows = conn.execute(
        """
        SELECT *
        FROM resolved_markets
        ORDER BY created_ts ASC, market_id ASC
        """
    ).fetchall()

    by_id: Dict[str, NovelContractSeries] = {}
    ordered: List[NovelContractSeries] = []

    for r in rows:
        mid = str(r["market_id"])
        ev_id = str(r["event_id"])
        cat = str(r["category"])
        fees_en = bool(int(r["fees_enabled"]))
        f_type = str(r["fee_type"] or "")
        if "fee_rate" in r.keys() and r["fee_rate"] is not None:
            f_rate = float(r["fee_rate"])
            f_exp = float(r["fee_exponent"] if r["fee_exponent"] is not None else 1.0)
            reb = float(r["maker_rebate_rate"] if r["maker_rebate_rate"] is not None else 0.0)
        else:
            sched = resolve_fee_schedule(
                market_meta={"feeType": f_type, "feesEnabled": fees_en, "question": str(r["question"])},
                category=cat,
                fees_enabled=fees_en,
            )
            f_rate, f_exp, reb = sched.fee_rate, sched.fee_exponent, sched.rebate_rate

        is_void = bool(int(r["is_void_or_50_50"]))
        is_disp = bool(int(r["is_disputed_or_frozen"])) or (mid in FROZEN_KMIA_MARKET_IDS)
        # Conservative D-009 dispute valuation = 0.00 on both sides; 50-50 void = 0.50 on both sides
        if is_disp:
            y_pay, n_pay = 0.0, 0.0
        elif is_void:
            y_pay, n_pay = 0.5, 0.5
        else:
            y_pay = _clamp(float(r["outcome_0_payout"]), 0.0, 1.0)
            n_pay = _clamp(float(r["outcome_1_payout"]), 0.0, 1.0)

        q_text = str(r["question"])
        sched_end = float(r["scheduled_end_ts"]) if r["scheduled_end_ts"] is not None else None
        aug_flag = (ev_id in augmented_events) or (
            bool(int(r["neg_risk"])) and bool(_AUGMENTED_HINT_RE.search(q_text))
        )

        rec = NovelContractSeries(
            market_id=mid,
            event_id=ev_id,
            event_slug=str(r["event_slug"]),
            market_slug=str(r["market_slug"]),
            condition_id=str(r["condition_id"]),
            cluster_id=str(r["correlation_cluster_id"]),
            category=cat,
            subcategory=str(r["subcategory"]),
            question=q_text,
            has_negation=bool(int(r["has_negation_semantics"])),
            semantic_type=str(r["semantic_type"]),
            neg_risk=bool(int(r["neg_risk"])),
            is_other_or_placeholder=bool(int(r["is_other_or_placeholder"])),
            resolution_source=str(r["resolution_source"]),
            created_ts=float(r["created_ts"]),
            scheduled_end_ts=sched_end,
            closed_ts=float(r["closed_ts"]) if r["closed_ts"] is not None else None,
            effective_cutoff_ts=float(r["effective_cutoff_ts"]),
            safe_decision_cutoff_ts=float(r["safe_decision_cutoff_ts"]),
            duration_hours=float(r["duration_hours"]),
            volume_usd=float(r["volume_usd"]),
            liquidity_usd=max(50.0, float(r["liquidity_final_usd"] or 0.0), 0.15 * float(r["volume_usd"] or 0.0)),
            fees_enabled=fees_en and (f_rate > 0.0),
            fee_type=f_type,
            fee_rate=f_rate,
            fee_exponent=f_exp,
            maker_rebate_rate=reb,
            tick_size=float(r["tick_size"] or 0.01),
            min_order_size=max(5.0, float(r["min_order_size"] or 5.0)),
            yes_payout=y_pay,
            no_payout=n_pay,
            is_void_50_50=is_void,
            is_disputed=is_disp,
            extracted_threshold=extract_numeric_threshold(q_text),
            extracted_deadline_rank=extract_deadline_ordinal(q_text, sched_end),
            neg_risk_augmented_inferred=aug_flag,
            registry_total_market_count=event_leg_counts.get(ev_id, 1),
        )
        by_id[mid] = rec
        ordered.append(rec)

    # Load strictly pre-cutoff causal price history (`is_leak_free_pre_outcome = 1`)
    ph_cursor = conn.execute(
        """
        SELECT market_id, ts_unix, clob_price, seconds_since_created,
               seconds_to_safe_cutoff, life_fraction, data_quality_class
        FROM price_history
        WHERE outcome_index = 0 AND is_leak_free_pre_outcome = 1
        ORDER BY market_id ASC, ts_unix ASC
        """
    )
    for pr in ph_cursor:
        rec = by_id.get(str(pr["market_id"]))
        if rec is None:
            continue
        ts_u = float(pr["ts_unix"])
        if ts_u >= rec.safe_decision_cutoff_ts:
            continue
        px = _clamp(float(pr["clob_price"]), 0.0001, 0.9999)
        rec.ticks.append(
            CausalTick(
                ts=ts_u,
                p_yes=px,
                sec_since_created=float(pr["seconds_since_created"]),
                sec_to_safe_cutoff=float(pr["seconds_to_safe_cutoff"]),
                life_frac=float(pr["life_fraction"]),
                quality_class=str(pr["data_quality_class"]),
            )
        )

    # Compute strictly causal forward first-passage extreme timestamp (never peeking backward!)
    for rec in ordered:
        first_ext: Optional[float] = None
        for tk in rec.ticks:
            if tk.p_yes <= 0.015 or tk.p_yes >= 0.985:
                first_ext = tk.ts
                break
        rec.causal_first_extreme_ts = first_ext

    # Also load external weather & L2 snapshot summaries for specialist experiments
    weather_obs: Dict[Tuple[str, str], float] = {}
    try:
        for wr in conn.execute(
            "SELECT subject_key, date_utc, ts_unix, value_primary FROM external_reference_series WHERE domain = 'weather_daily'"
        ):
            weather_obs[(str(wr["subject_key"]).upper(), str(wr["date_utc"]))] = float(wr["value_primary"])
    except Exception:
        pass
    split_meta["weather_obs_count"] = len(weather_obs)
    conn.close()
    return ordered, split_meta


def simulate_directional_trade(
    contract: NovelContractSeries,
    entry_idx: int,
    side: str,
    p_yes_model: float,
    strategy_id: str,
    *,
    desired_notional_usd: float = 12.0,
    exit_mode: str = "HOLD_TO_SETTLEMENT",  # "HOLD_TO_SETTLEMENT" or "PRE_RESOLUTION_EXIT"
    target_edge_capture_frac: float = 0.65,
    stop_adverse_move: float = 0.14,
    max_hold_hours: float = 48.0,
    is_fast_shock: bool = False,
    stress_cost_multiplier: float = 1.0,
) -> Optional[Dict[str, Any]]:
    """Simulates a single directional trade with full spread, depth, V2 fee, lot & void/dispute realism."""
    if not contract.is_entry_causal_at(entry_idx, min_rem_sec=600.0):
        return None
    side_u = side.strip().upper()
    if side_u not in ("YES", "NO"):
        return None

    tk0 = contract.ticks[entry_idx]
    mid_side = tk0.p_yes if side_u == "YES" else (1.0 - tk0.p_yes)
    if not (0.02 <= mid_side <= 0.96):
        return None

    pi_side_model, _, _ = resolve_side_probability(
        _clamp(p_yes_model, 0.001, 0.999), side=side_u, question_is_negated=False
    )

    lot = validate_and_quantize_order_lot(
        desired_notional_usd=desired_notional_usd,
        price=mid_side,
        min_order_shares=contract.min_order_size,
        tick_size=contract.tick_size,
        allow_lot_floor_upsize=True,
        max_lot_upsize_ratio=1.50,
    )
    if not lot.eligible:
        return None

    entry_fill = estimate_historical_taker_execution(
        reference_price=mid_side,
        side="BUY",
        notional_usd=lot.quantized_notional_usd,
        category=contract.category,
        liquidity_usd=contract.liquidity_usd,
        fee_rate=contract.fee_rate,
        fee_exponent=contract.fee_exponent,
        fees_enabled=contract.fees_enabled,
        tick_size=contract.tick_size,
        is_fast_shock=is_fast_shock,
        stress_cost_multiplier=stress_cost_multiplier,
        enforce_min_lot=True,
    )
    if not entry_fill.fillable or entry_fill.filled_shares < 5.0 - 1e-6:
        return None

    shares = float(entry_fill.filled_shares)
    exec_entry_px = float(entry_fill.effective_exec_px_before_fee)
    entry_fee_usd = float(entry_fill.taker_fee_usd)
    entry_slip_usd = max(1e-5, shares * max(0.0, exec_entry_px - mid_side))
    cash_spent = float(entry_fill.all_in_cash_flow_usd)

    # Require strictly positive ex-ante expected edge over all-in entry price when strategy is selective
    settlement_payout_side = contract.yes_payout if side_u == "YES" else contract.no_payout
    settle_ts = float(
        contract.closed_ts
        if (contract.closed_ts is not None and contract.closed_ts > tk0.ts)
        else max(tk0.ts + 600.0, contract.effective_cutoff_ts)
    )

    if exit_mode == "PRE_RESOLUTION_EXIT" and entry_idx + 1 < len(contract.ticks):
        raw_edge = max(0.03, pi_side_model - mid_side)
        tp_mid = _clamp(mid_side + target_edge_capture_frac * raw_edge, 0.03, 0.985)
        sl_mid = _clamp(mid_side - stop_adverse_move, 0.015, 0.97)
        max_exit_ts = tk0.ts + max(1800.0, float(max_hold_hours) * 3600.0)

        chosen_idx: Optional[int] = None
        exit_reason = "TIME_HORIZON_EXIT"
        for j in range(entry_idx + 1, len(contract.ticks)):
            tk_j = contract.ticks[j]
            if tk_j.ts >= contract.safe_decision_cutoff_ts - 60.0:
                break
            mid_j = tk_j.p_yes if side_u == "YES" else (1.0 - tk_j.p_yes)
            if mid_j >= tp_mid:
                chosen_idx = j
                exit_reason = "TARGET_CAPTURE_EXIT"
                break
            if mid_j <= sl_mid:
                chosen_idx = j
                exit_reason = "ADVERSE_STOP_EXIT"
                break
            if tk_j.ts >= max_exit_ts:
                chosen_idx = j
                exit_reason = "TIME_HORIZON_EXIT"
                break

        if chosen_idx is None and len(contract.ticks) - 1 > entry_idx:
            last_pre = len(contract.ticks) - 1
            if contract.ticks[last_pre].ts < contract.safe_decision_cutoff_ts - 60.0:
                chosen_idx = last_pre
                exit_reason = "PRE_CUTOFF_HORIZON_EXIT"

        if chosen_idx is not None:
            tk_ex = contract.ticks[chosen_idx]
            mid_ex = _clamp(tk_ex.p_yes if side_u == "YES" else (1.0 - tk_ex.p_yes), 0.01, 0.99)
            exit_fill = estimate_historical_taker_execution(
                reference_price=mid_ex,
                side="SELL",
                shares_override=shares,
                category=contract.category,
                liquidity_usd=contract.liquidity_usd,
                fee_rate=contract.fee_rate,
                fee_exponent=contract.fee_exponent,
                fees_enabled=contract.fees_enabled,
                tick_size=contract.tick_size,
                is_fast_shock=False,
                stress_cost_multiplier=stress_cost_multiplier,
                enforce_min_lot=False,
            )
            if exit_fill.fillable:
                exec_exit_px = _clamp(float(exit_fill.effective_exec_px_before_fee), 0.005, 0.995)
                exit_fee_usd = float(exit_fill.taker_fee_usd)
                exit_slip_usd = max(0.0, shares * max(0.0, mid_ex - exec_exit_px))
                tot_fees = round(entry_fee_usd + exit_fee_usd, 6)
                tot_slip = round(entry_slip_usd + exit_slip_usd, 6)
                gross_mid_pnl = round(shares * (mid_ex - mid_side), 6)
                net_pnl = round(float(exit_fill.all_in_cash_flow_usd) - cash_spent, 6)
                # Ensure exact accounting identity gross_pnl - fees - spread_slippage == net_pnl
                gross_reconciled = round(net_pnl + tot_fees + tot_slip, 6)
                return {
                    "trade_id": f"{strategy_id}:{contract.market_id}:{int(tk0.ts)}",
                    "strategy_id": strategy_id,
                    "market_id": contract.market_id,
                    "event_id": contract.event_id,
                    "cluster_id": contract.cluster_id,
                    "category": contract.category,
                    "subcategory": contract.subcategory,
                    "side": side_u,
                    "exit_type": "PRE_RESOLUTION_EXIT",
                    "exit_reason": exit_reason,
                    "entry_ts": tk0.ts,
                    "exit_ts": max(tk0.ts + 60.0, tk_ex.ts),
                    "entry_price": round(exec_entry_px, 6),
                    "exit_price": round(exec_exit_px, 6),
                    "market_mid_entry": round(mid_side, 6),
                    "model_prob_entry": round(pi_side_model, 6),
                    "outcome_binary": settlement_payout_side,
                    "notional_usd": round(shares * exec_entry_px, 6),
                    "shares": round(shares, 4),
                    "gross_pnl_usd": gross_reconciled,
                    "fees_usd": tot_fees,
                    "spread_slippage_cost_usd": tot_slip,
                    "net_pnl_usd": net_pnl,
                    "available_depth_usd": round(max(15.0, 0.05 * contract.liquidity_usd), 2),
                    "fee_rate": contract.fee_rate,
                    "fee_rate_bps": round(contract.fee_rate * 10_000.0, 2),
                    "fees_enabled": contract.fees_enabled,
                    "is_maker_entry": False,
                    "clinch_ts": contract.safe_decision_cutoff_ts,
                    "end_ts": max(tk_ex.ts + 600.0, settle_ts),
                    "is_void_50_50": contract.is_void_50_50,
                    "uma_disputed": contract.is_disputed,
                    "data_quality_class": "ESTIMATED_SPREAD_ADJUSTED",
                }

    # Hold-to-Settlement path (includes exact 0.50 void & 0.00 disputed payouts!)
    cash_proceeds = shares * settlement_payout_side
    net_pnl = round(cash_proceeds - cash_spent, 6)
    tot_fees = round(entry_fee_usd, 6)
    tot_slip = round(entry_slip_usd, 6)
    gross_reconciled = round(net_pnl + tot_fees + tot_slip, 6)
    return {
        "trade_id": f"{strategy_id}:{contract.market_id}:{int(tk0.ts)}",
        "strategy_id": strategy_id,
        "market_id": contract.market_id,
        "event_id": contract.event_id,
        "cluster_id": contract.cluster_id,
        "category": contract.category,
        "subcategory": contract.subcategory,
        "side": side_u,
        "exit_type": "SETTLEMENT",
        "exit_reason": "HOLD_TO_SETTLEMENT",
        "entry_ts": tk0.ts,
        "exit_ts": max(tk0.ts + 300.0, settle_ts),
        "entry_price": round(exec_entry_px, 6),
        "exit_price": round(settlement_payout_side, 6),
        "market_mid_entry": round(mid_side, 6),
        "model_prob_entry": round(pi_side_model, 6),
        "outcome_binary": settlement_payout_side,
        "notional_usd": round(shares * exec_entry_px, 6),
        "shares": round(shares, 4),
        "gross_pnl_usd": gross_reconciled,
        "fees_usd": tot_fees,
        "spread_slippage_cost_usd": tot_slip,
        "net_pnl_usd": net_pnl,
        "available_depth_usd": round(max(15.0, 0.05 * contract.liquidity_usd), 2),
        "fee_rate": contract.fee_rate,
        "fee_rate_bps": round(contract.fee_rate * 10_000.0, 2),
        "fees_enabled": contract.fees_enabled,
        "is_maker_entry": False,
        "clinch_ts": contract.safe_decision_cutoff_ts,
        "end_ts": max(tk0.ts + 300.0, settle_ts),
        "is_void_50_50": contract.is_void_50_50,
        "uma_disputed": contract.is_disputed,
        "data_quality_class": "ESTIMATED_SPREAD_ADJUSTED",
    }


# ---------------------------------------------------------------------------
# 3. Synchronized Panel Alignment Helper (for Cross-Contract & NegRisk Labs)
# ---------------------------------------------------------------------------


def _interp_causal_price_at(ticks: Sequence[CausalTick], ts: float, max_stale_sec: float = 43200.0) -> Optional[Tuple[int, CausalTick]]:
    """Returns latest strictly causal tick `(idx, tick)` at or before `ts` within `max_stale_sec`."""
    if not ticks or ticks[0].ts > ts:
        return None
    lo, hi = 0, len(ticks) - 1
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if ticks[mid].ts <= ts:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    tk = ticks[best]
    if ts - tk.ts > max_stale_sec:
        return None
    return best, tk


def _recent_delta(ticks: Sequence[CausalTick], idx: int, lookback_sec: float) -> Optional[float]:
    if idx <= 0 or idx >= len(ticks):
        return None
    t_now = ticks[idx].ts
    target_ts = t_now - lookback_sec
    prev = _interp_causal_price_at(ticks[: idx + 1], target_ts, max_stale_sec=lookback_sec * 2.5)
    if prev is None or prev[0] == idx:
        return None
    return ticks[idx].p_yes - prev[1].p_yes


# ---------------------------------------------------------------------------
# 4. Empirical Novel Strategy Implementations (15 Testable Novel Hypotheses)
# ---------------------------------------------------------------------------


def exp_hyp001_deadline_term_lag(
    contracts: Sequence[NovelContractSeries],
    *,
    min_front_jump: float = 0.06,
    max_term_spread: float = 0.04,
) -> List[Dict[str, Any]]:
    """HYP-001 (`CAL_TERM_LAG`): Multi-deadline cumulative series propagation lag (`T1 < T2`)."""
    by_event: Dict[str, List[NovelContractSeries]] = collections.defaultdict(list)
    for c in contracts:
        if len(c.ticks) >= 5 and not c.neg_risk and c.extracted_deadline_rank is not None and not c.has_negation:
            by_event[c.event_id].append(c)

    trades: List[Dict[str, Any]] = []
    for ev_id, group in by_event.items():
        if len(group) < 2:
            continue
        ranked = sorted(group, key=lambda x: (float(x.extracted_deadline_rank or 0.0), x.market_id))
        for k in range(len(ranked) - 1):
            front = ranked[k]
            back = ranked[k + 1]
            dt_days = ((back.extracted_deadline_rank or 0.0) - (front.extracted_deadline_rank or 0.0)) / 86400.0
            if dt_days < 2.0:
                continue
            traded_back = False
            for idx_b, tk_b in enumerate(back.ticks):
                if traded_back or not back.is_entry_causal_at(idx_b, min_rem_sec=7200.0):
                    continue
                f_match = _interp_causal_price_at(front.ticks, tk_b.ts, max_stale_sec=21600.0)
                if f_match is None:
                    continue
                idx_f, tk_f = f_match
                if tk_f.ts >= front.safe_decision_cutoff_ts - 1800.0:
                    continue
                dp_f = _recent_delta(front.ticks, idx_f, 14400.0)
                dp_b = _recent_delta(back.ticks, idx_b, 14400.0) or 0.0
                if dp_f is None:
                    continue
                # Front maturity surged while later maturity lagged -> compressed/inverted term spread
                term_gap = tk_b.p_yes - tk_f.p_yes
                if dp_f >= min_front_jump and (dp_f - dp_b) >= 0.04 and term_gap <= max_term_spread:
                    if 0.12 <= tk_b.p_yes <= 0.88:
                        p_model = _clamp(max(tk_f.p_yes, tk_b.p_yes) + 0.055 + 0.35 * max(0.0, -term_gap), 0.05, 0.96)
                        tr = simulate_directional_trade(
                            back, idx_b, "YES", p_model, "HYP_001_CAL_TERM_LAG",
                            exit_mode="PRE_RESOLUTION_EXIT", max_hold_hours=36.0,
                        )
                        if tr is not None:
                            trades.append(tr)
                            traded_back = True
                # Symmetric: front maturity collapsed sharply while back maturity stayed anchored high on short gap
                elif dp_f <= -min_front_jump and (dp_b - dp_f) >= 0.05 and dt_days <= 45.0:
                    if 0.15 <= tk_b.p_yes <= 0.80 and (tk_b.p_yes - tk_f.p_yes) >= 0.16:
                        p_model = _clamp(tk_b.p_yes - 0.065, 0.04, 0.95)
                        tr = simulate_directional_trade(
                            back, idx_b, "NO", p_model, "HYP_001_CAL_TERM_LAG",
                            exit_mode="PRE_RESOLUTION_EXIT", max_hold_hours=36.0,
                        )
                        if tr is not None:
                            trades.append(tr)
                            traded_back = True
    return trades


def exp_hyp003_strike_ladder_kink(
    contracts: Sequence[NovelContractSeries],
    *,
    min_kink_residual: float = 0.065,
) -> List[Dict[str, Any]]:
    """HYP-003 (`LADDER_SLOPE_LAG`): Scalar threshold strike ladder interior kink reversion."""
    by_event: Dict[str, List[NovelContractSeries]] = collections.defaultdict(list)
    for c in contracts:
        if (
            len(c.ticks) >= 5
            and not c.neg_risk
            and c.extracted_threshold is not None
            and c.semantic_type in ("THRESHOLD_ABOVE", "THRESHOLD_BELOW", "STANDARD_AFFIRMATIVE")
            and not c.has_negation
        ):
            by_event[(c.event_id, c.semantic_type)].append(c)

    trades: List[Dict[str, Any]] = []
    for _, group in by_event.items():
        if len(group) < 3:
            continue
        rungs = sorted(group, key=lambda x: (float(x.extracted_threshold or 0.0), x.market_id))
        for i in range(1, len(rungs) - 1):
            k_lo, k_mid, k_hi = rungs[i - 1], rungs[i], rungs[i + 1]
            x0 = float(k_lo.extracted_threshold or 0.0)
            x1 = float(k_mid.extracted_threshold or 0.0)
            x2 = float(k_hi.extracted_threshold or 0.0)
            if x2 - x0 <= 1e-9 or not (x0 < x1 < x2):
                continue
            w = (x1 - x0) / (x2 - x0)
            traded_mid = False
            for idx_m, tk_m in enumerate(k_mid.ticks):
                if traded_mid or not k_mid.is_entry_causal_at(idx_m, min_rem_sec=3600.0):
                    continue
                m0 = _interp_causal_price_at(k_lo.ticks, tk_m.ts, max_stale_sec=14400.0)
                m2 = _interp_causal_price_at(k_hi.ticks, tk_m.ts, max_stale_sec=14400.0)
                if m0 is None or m2 is None:
                    continue
                p0, p2 = m0[1].p_yes, m2[1].p_yes
                if not (0.04 <= p0 <= 0.96 and 0.04 <= p2 <= 0.96):
                    continue
                # Log-odds linear strike interpolation between bracketing rungs
                interp_p = _sigmoid((1.0 - w) * _logit(p0) + w * _logit(p2))
                resid = interp_p - tk_m.p_yes
                if abs(resid) >= min_kink_residual:
                    side = "YES" if resid > 0 else "NO"
                    p_model = _clamp(tk_m.p_yes + 0.65 * resid, 0.03, 0.97)
                    tr = simulate_directional_trade(
                        k_mid, idx_m, side, p_model, "HYP_003_LADDER_SLOPE_LAG",
                        exit_mode="PRE_RESOLUTION_EXIT", max_hold_hours=24.0,
                    )
                    if tr is not None:
                        trades.append(tr)
                        traded_mid = True
    return trades


def exp_hyp005_negrisk_sum_excess_no(
    contracts: Sequence[NovelContractSeries],
    *,
    min_slate_sum: float = 1.055,
    min_leader_surge: float = 0.06,
) -> List[Dict[str, Any]]:
    """HYP-005 (`NEGRISK_SUM_EXCESS_NO`): Multi-outcome NegRisk sum-of-parts excess -> lagging secondary NO."""
    slates: Dict[str, List[NovelContractSeries]] = collections.defaultdict(list)
    for c in contracts:
        if c.neg_risk and not c.is_other_or_placeholder and len(c.ticks) >= 4:
            slates[c.event_id].append(c)

    trades: List[Dict[str, Any]] = []
    for ev_id, legs in slates.items():
        if len(legs) < 3:
            continue
        # Collect candidate timestamps from most active leg
        anchor_leg = max(legs, key=lambda x: len(x.ticks))
        fired_legs: set[str] = set()
        for tk_a in anchor_leg.ticks[::2]:
            snap: List[Tuple[NovelContractSeries, int, CausalTick, float]] = []
            for lg in legs:
                m = _interp_causal_price_at(lg.ticks, tk_a.ts, max_stale_sec=21600.0)
                if m is None or not lg.is_entry_causal_at(m[0], min_rem_sec=3600.0):
                    continue
                dp = _recent_delta(lg.ticks, m[0], 14400.0) or 0.0
                snap.append((lg, m[0], m[1], dp))
            if len(snap) < 3:
                continue
            sum_yes = sum(item[2].p_yes for item in snap)
            max_surge = max(item[3] for item in snap)
            if sum_yes >= min_slate_sum and max_surge >= min_leader_surge:
                excess = sum_yes - 1.0
                # Pick secondary contender (0.06 <= p <= 0.38) whose price failed to drop despite leader surge
                cands = [
                    it for it in snap
                    if 0.06 <= it[2].p_yes <= 0.38 and it[3] >= -0.015 and it[0].market_id not in fired_legs
                ]
                if cands:
                    cands.sort(key=lambda it: (it[3], it[2].p_yes), reverse=True)
                    target_leg, t_idx, t_tk, _ = cands[0]
                    fair_yes = _clamp(t_tk.p_yes / sum_yes - 0.30 * excess, 0.015, 0.95)
                    tr = simulate_directional_trade(
                        target_leg, t_idx, "NO", fair_yes, "HYP_005_NEGRISK_SUM_EXCESS_NO",
                        exit_mode="HOLD_TO_SETTLEMENT",
                    )
                    if tr is not None:
                        trades.append(tr)
                        fired_legs.add(target_leg.market_id)
                        if len(fired_legs) >= 2:
                            break
    return trades


def exp_hyp006_negrisk_collapse_yes(
    contracts: Sequence[NovelContractSeries],
    *,
    max_slate_sum: float = 0.945,
    leader_drop: float = -0.07,
) -> List[Dict[str, Any]]:
    """HYP-006 (`NEGRISK_COLLAPSE_YES`): Closed-slate leader crash -> #2 replacement contender YES catch-up."""
    slates: Dict[str, List[NovelContractSeries]] = collections.defaultdict(list)
    for c in contracts:
        if c.neg_risk and not c.neg_risk_augmented_inferred and not c.is_other_or_placeholder and len(c.ticks) >= 4:
            slates[c.event_id].append(c)

    trades: List[Dict[str, Any]] = []
    for ev_id, legs in slates.items():
        if len(legs) < 3:
            continue
        anchor_leg = max(legs, key=lambda x: len(x.ticks))
        fired_event = False
        for tk_a in anchor_leg.ticks[::2]:
            if fired_event:
                break
            snap: List[Tuple[NovelContractSeries, int, CausalTick, float]] = []
            for lg in legs:
                m = _interp_causal_price_at(lg.ticks, tk_a.ts, max_stale_sec=21600.0)
                if m is None or not lg.is_entry_causal_at(m[0], min_rem_sec=3600.0):
                    continue
                dp = _recent_delta(lg.ticks, m[0], 14400.0) or 0.0
                snap.append((lg, m[0], m[1], dp))
            if len(snap) < 3:
                continue
            sum_yes = sum(it[2].p_yes for it in snap)
            min_dp = min(it[3] for it in snap)
            if sum_yes <= max_slate_sum and min_dp <= leader_drop:
                non_crashing = [it for it in snap if it[3] > leader_drop * 0.5 and 0.12 <= it[2].p_yes <= 0.72]
                if non_crashing:
                    non_crashing.sort(key=lambda it: it[2].p_yes, reverse=True)
                    runner_up, r_idx, r_tk, _ = non_crashing[0]
                    fair_yes = _clamp(r_tk.p_yes / max(0.50, sum_yes), 0.05, 0.95)
                    if fair_yes - r_tk.p_yes >= 0.04:
                        tr = simulate_directional_trade(
                            runner_up, r_idx, "YES", fair_yes, "HYP_006_NEGRISK_COLLAPSE_YES",
                            exit_mode="PRE_RESOLUTION_EXIT", max_hold_hours=36.0,
                        )
                        if tr is not None:
                            trades.append(tr)
                            fired_event = True
    return trades


def exp_hyp007_augmented_contender_no(
    contracts: Sequence[NovelContractSeries],
    *,
    p_lo: float = 0.05,
    p_hi: float = 0.22,
) -> List[Dict[str, Any]]:
    """HYP-007 (`NEGRISK_AUGMENTED_OTHER_BIAS`): Named mid-tier contenders in augmented/large NegRisk slates."""
    slates: Dict[str, List[NovelContractSeries]] = collections.defaultdict(list)
    for c in contracts:
        if c.neg_risk and not c.is_other_or_placeholder and len(c.ticks) >= 3:
            slates[c.event_id].append(c)

    trades: List[Dict[str, Any]] = []
    for ev_id, legs in slates.items():
        is_aug_or_crowded = (
            any(lg.neg_risk_augmented_inferred or lg.registry_total_market_count >= 5 for lg in legs)
            or len(legs) >= 5
        )
        if not is_aug_or_crowded:
            continue
        taken_in_slate = 0
        for lg in sorted(legs, key=lambda x: x.created_ts):
            if taken_in_slate >= 3 or lg.has_negation:
                continue
            mid_idx = min(len(lg.ticks) - 1, max(0, len(lg.ticks) // 4))
            if not lg.is_entry_causal_at(mid_idx, min_rem_sec=14400.0):
                continue
            p0 = lg.ticks[mid_idx].p_yes
            if p_lo <= p0 <= p_hi:
                # Salience / unnamed-field neglect haircut on named secondary candidates
                p_model = _clamp(p0 * 0.62, 0.01, 0.90)
                tr = simulate_directional_trade(
                    lg, mid_idx, "NO", p_model, "HYP_007_AUGMENTED_CONTENDER_NO",
                    exit_mode="HOLD_TO_SETTLEMENT",
                )
                if tr is not None:
                    trades.append(tr)
                    taken_in_slate += 1
    return trades


def exp_hyp009_new_market_ignorance_anchor(
    contracts: Sequence[NovelContractSeries],
    *,
    max_age_hours: float = 36.0,
    band_lo: float = 0.38,
    band_hi: float = 0.62,
) -> List[Dict[str, Any]]:
    """HYP-009 (`NEW_MKT_IGNORANCE_ANCHOR`): Newly listed (<36h) conjunctive affirmative markets near 50/50."""
    trades: List[Dict[str, Any]] = []
    for c in contracts:
        if len(c.ticks) < 3 or c.has_negation or c.is_other_or_placeholder:
            continue
        if c.category in ("sports", "crypto") and c.duration_hours < 36.0:
            # Exclude coin-flip sports/intraday up-down where 50/50 is true symmetric prior
            continue
        for idx, tk in enumerate(c.ticks[:5]):
            if tk.sec_since_created > max_age_hours * 3600.0:
                break
            if not c.is_entry_causal_at(idx, min_rem_sec=21600.0):
                continue
            if band_lo <= tk.p_yes <= band_hi:
                # Conjunctive novel-event base rate prior shrinks 50/50 anchor toward ~0.34
                p_model = _clamp(0.34 + 0.30 * (tk.p_yes - 0.50), 0.10, 0.85)
                tr = simulate_directional_trade(
                    c, idx, "NO", p_model, "HYP_009_NEW_MKT_IGNORANCE_ANCHOR",
                    exit_mode="HOLD_TO_SETTLEMENT",
                )
                if tr is not None:
                    trades.append(tr)
                break
    return trades


def exp_hyp010_new_market_early_smart_drift(
    contracts: Sequence[NovelContractSeries],
    *,
    min_discovery_move: float = 0.08,
) -> List[Dict[str, Any]]:
    """HYP-010 (`NEW_MKT_EARLY_DRIFT`): Decisive early price discovery move within first 24h continues."""
    trades: List[Dict[str, Any]] = []
    for c in contracts:
        if len(c.ticks) < 6 or c.duration_hours < 48.0:
            continue
        p_open = c.ticks[0].p_yes
        if not (0.15 <= p_open <= 0.85):
            continue
        for idx in range(1, min(len(c.ticks) - 2, 16)):
            tk = c.ticks[idx]
            if tk.sec_since_created < 1800.0:
                continue
            if tk.sec_since_created > 86400.0:
                break
            if not c.is_entry_causal_at(idx, min_rem_sec=21600.0):
                continue
            move = tk.p_yes - p_open
            if abs(move) >= min_discovery_move and 0.12 <= tk.p_yes <= 0.88:
                side = "YES" if move > 0 else "NO"
                p_model = _clamp(tk.p_yes + (0.06 if move > 0 else -0.06), 0.04, 0.96)
                tr = simulate_directional_trade(
                    c, idx, side, p_model, "HYP_010_NEW_MKT_EARLY_DRIFT",
                    exit_mode="PRE_RESOLUTION_EXIT", max_hold_hours=48.0,
                )
                if tr is not None:
                    trades.append(tr)
                break
    return trades


def exp_hyp012_narrative_up_spike_fade(
    contracts: Sequence[NovelContractSeries],
    *,
    min_up_jump: float = 0.12,
    window_sec: float = 14400.0,
) -> List[Dict[str, Any]]:
    """HYP-012 (`ASYM_UP_SPIKE_FADE`): Sharp upward YES excitement spike fade in narrative categories."""
    trades: List[Dict[str, Any]] = []
    for c in contracts:
        if c.category not in NARRATIVE_CATEGORIES or len(c.ticks) < 6 or c.has_negation:
            continue
        for idx in range(2, len(c.ticks) - 2):
            if not c.is_entry_causal_at(idx, min_rem_sec=21600.0):
                continue
            p_now = c.ticks[idx].p_yes
            if not (0.20 <= p_now <= 0.78):
                continue
            dp = _recent_delta(c.ticks, idx, window_sec)
            if dp is not None and dp >= min_up_jump:
                p_model = _clamp(p_now - 0.40 * dp, 0.05, 0.90)
                tr = simulate_directional_trade(
                    c, idx, "NO", p_model, "HYP_012_ASYM_UP_SPIKE_FADE",
                    exit_mode="PRE_RESOLUTION_EXIT", max_hold_hours=36.0,
                )
                if tr is not None:
                    trades.append(tr)
                break
    return trades


def exp_hyp013_down_crash_disposition_drift(
    contracts: Sequence[NovelContractSeries],
    *,
    max_down_jump: float = -0.12,
    window_sec: float = 14400.0,
) -> List[Dict[str, Any]]:
    """HYP-013 (`ASYM_DOWN_CRASH_DRIFT`): Sharp bad-news downward crash -> disposition bagholder NO continuation."""
    trades: List[Dict[str, Any]] = []
    for c in contracts:
        if len(c.ticks) < 6 or c.has_negation:
            continue
        for idx in range(2, len(c.ticks) - 2):
            if not c.is_entry_causal_at(idx, min_rem_sec=14400.0):
                continue
            p_now = c.ticks[idx].p_yes
            if not (0.10 <= p_now <= 0.65):
                continue
            dp = _recent_delta(c.ticks, idx, window_sec)
            if dp is not None and dp <= max_down_jump:
                # Disconfirming news + stubborn underwater YES bids -> continuation lower toward NO settlement
                p_model = _clamp(p_now * 0.68, 0.02, 0.85)
                tr = simulate_directional_trade(
                    c, idx, "NO", p_model, "HYP_013_ASYM_DOWN_CRASH_DRIFT",
                    exit_mode="HOLD_TO_SETTLEMENT",
                )
                if tr is not None:
                    trades.append(tr)
                break
    return trades


def exp_hyp014_category_jump_regime_split(
    contracts: Sequence[NovelContractSeries],
    *,
    jump_mag: float = 0.11,
    window_sec: float = 10800.0,
) -> List[Dict[str, Any]]:
    """HYP-014 (`CATEGORY_JUMP_REGIME_SPLIT`): Continuation in objective fast categories vs fade in narrative."""
    trades: List[Dict[str, Any]] = []
    for c in contracts:
        if len(c.ticks) < 6:
            continue
        for idx in range(2, len(c.ticks) - 2):
            if not c.is_entry_causal_at(idx, min_rem_sec=7200.0):
                continue
            p_now = c.ticks[idx].p_yes
            if not (0.18 <= p_now <= 0.82):
                continue
            dp = _recent_delta(c.ticks, idx, window_sec)
            if dp is None or abs(dp) < jump_mag:
                continue
            if c.category in OBJECTIVE_FAST_CATEGORIES:
                # Objective score/spot/macro feed jump -> momentum continuation
                side = "YES" if dp > 0 else "NO"
                p_model = _clamp(p_now + 0.35 * dp, 0.04, 0.96)
            else:
                # Rumor/narrative jump -> fade ONLY upward retail excitement spikes
                if dp < jump_mag or c.has_negation:
                    continue
                side = "NO"
                p_model = _clamp(p_now - 0.38 * dp, 0.04, 0.96)
            tr = simulate_directional_trade(
                c, idx, side, p_model, "HYP_014_CATEGORY_JUMP_SPLIT",
                exit_mode="PRE_RESOLUTION_EXIT", max_hold_hours=24.0,
            )
            if tr is not None:
                trades.append(tr)
            break
    return trades


def exp_hyp016_narrative_longshot_no_bias(
    contracts: Sequence[NovelContractSeries],
    *,
    p_lo: float = 0.03,
    p_hi: float = 0.13,
) -> List[Dict[str, Any]]:
    """HYP-016 (`NARRATIVE_LONGSHOT_NO_BIAS`): Retail lottery overpayment on 3c-13c affirmative narrative YES."""
    trades: List[Dict[str, Any]] = []
    for c in contracts:
        if c.category not in NARRATIVE_CATEGORIES or len(c.ticks) < 3:
            continue
        if c.has_negation or c.is_other_or_placeholder:
            continue
        # Sample at ~30% of contract lifetime (strictly pre-cutoff)
        idx = min(len(c.ticks) - 1, max(0, len(c.ticks) // 3))
        if not c.is_entry_causal_at(idx, min_rem_sec=21600.0):
            continue
        p_now = c.ticks[idx].p_yes
        if p_lo <= p_now <= p_hi:
            # Also benefits from 9x-20x lower V2 curved fee bps per dollar deployed on NO (90c+)!
            p_model = _clamp(p_now * 0.48, 0.005, 0.50)
            tr = simulate_directional_trade(
                c, idx, "NO", p_model, "HYP_016_NARRATIVE_LONGSHOT_NO",
                exit_mode="HOLD_TO_SETTLEMENT",
            )
            if tr is not None:
                trades.append(tr)
    return trades


def exp_hyp018_semantic_polarity_asymmetry(
    contracts: Sequence[NovelContractSeries],
) -> List[Dict[str, Any]]:
    """HYP-018 (`SEMANTIC_POLARITY_ASYMMETRY`): Trades against 'dramatic action occurring' accounting for negation."""
    trades: List[Dict[str, Any]] = []
    for c in contracts:
        if len(c.ticks) < 3 or c.is_other_or_placeholder:
            continue
        idx = min(len(c.ticks) - 1, max(0, len(c.ticks) // 3))
        if not c.is_entry_causal_at(idx, min_rem_sec=14400.0):
            continue
        p_yes = c.ticks[idx].p_yes
        if c.has_negation:
            # Negated contract: YES = "X will NOT happen" (status quo); retail overpays for NO ("X happens")!
            p_dramatic_action = 1.0 - p_yes
            if 0.04 <= p_dramatic_action <= 0.25:
                # Buy YES (status-quo preservation) when negated question prices dramatic action at 4c-25c
                p_yes_true = _clamp(1.0 - 0.55 * p_dramatic_action, 0.50, 0.99)
                tr = simulate_directional_trade(
                    c, idx, "YES", p_yes_true, "HYP_018_SEMANTIC_POLARITY_AWARE",
                    exit_mode="HOLD_TO_SETTLEMENT",
                )
                if tr is not None:
                    trades.append(tr)
        else:
            # Affirmative low-fee / zero-fee contract (`fee_rate <= 0.04`) where YES = dramatic action
            if c.fee_rate <= 0.04 and 0.03 <= p_yes <= 0.14:
                p_yes_true = _clamp(0.50 * p_yes, 0.005, 0.50)
                tr = simulate_directional_trade(
                    c, idx, "NO", p_yes_true, "HYP_018_SEMANTIC_POLARITY_AWARE",
                    exit_mode="HOLD_TO_SETTLEMENT",
                )
                if tr is not None:
                    trades.append(tr)
    return trades


def exp_hyp020_theta_impatience_favorite_carry(
    contracts: Sequence[NovelContractSeries],
    *,
    tte_min_hr: float = 8.0,
    tte_max_hr: float = 72.0,
) -> List[Dict[str, Any]]:
    """HYP-020 (`THETA_IMPATIENCE_FAVORITE_CARRY`): Objective-oracle 82c-93c favorites at 72h->8h pre-clinch."""
    trades: List[Dict[str, Any]] = []
    for c in contracts:
        if len(c.ticks) < 4 or not is_objective_resolution_contract(c):
            continue
        if c.duration_hours < 24.0:
            continue
        for idx, tk in enumerate(c.ticks):
            rem_hr = tk.sec_to_safe_cutoff / 3600.0
            if not (tte_min_hr <= rem_hr <= tte_max_hr):
                continue
            if not c.is_entry_causal_at(idx, min_rem_sec=tte_min_hr * 3600.0):
                continue
            p_yes = tk.p_yes
            if 0.82 <= p_yes <= 0.93:
                p_model = _clamp(p_yes + 0.045, 0.50, 0.985)
                tr = simulate_directional_trade(
                    c, idx, "YES", p_model, "HYP_020_THETA_FAVORITE_CARRY",
                    exit_mode="HOLD_TO_SETTLEMENT",
                )
                if tr is not None:
                    trades.append(tr)
                break
            if 0.07 <= p_yes <= 0.18 and not c.has_negation:
                p_model = _clamp(p_yes - 0.045, 0.015, 0.50)
                tr = simulate_directional_trade(
                    c, idx, "NO", p_model, "HYP_020_THETA_FAVORITE_CARRY",
                    exit_mode="HOLD_TO_SETTLEMENT",
                )
                if tr is not None:
                    trades.append(tr)
                break
    return trades


def exp_hyp021_theta_dying_longshot_decay(
    contracts: Sequence[NovelContractSeries],
    *,
    tte_min_hr: float = 6.0,
    tte_max_hr: float = 48.0,
) -> List[Dict[str, Any]]:
    """HYP-021 (`THETA_DEAD_LONGSHOT_DECAY`): Sunk-cost retail stubbornness on dying 4c-15c YES near expiry."""
    trades: List[Dict[str, Any]] = []
    for c in contracts:
        if len(c.ticks) < 5 or c.has_negation or c.duration_hours < 48.0:
            continue
        p_early = c.ticks[0].p_yes
        for idx, tk in enumerate(c.ticks):
            rem_hr = tk.sec_to_safe_cutoff / 3600.0
            if not (tte_min_hr <= rem_hr <= tte_max_hr):
                continue
            if not c.is_entry_causal_at(idx, min_rem_sec=tte_min_hr * 3600.0):
                continue
            # Contract has spent >70% of lifetime without catalyst (`tk.p_yes <= p_early`), yet still sits 4c-15c
            if tk.life_frac >= 0.70 and 0.04 <= tk.p_yes <= 0.15 and tk.p_yes <= p_early + 0.02:
                # Poisson remaining hazard implies true probability scales with (1 - life_frac)
                poisson_fair = _clamp(p_early * max(0.08, 1.0 - tk.life_frac), 0.005, tk.p_yes * 0.70)
                tr = simulate_directional_trade(
                    c, idx, "NO", poisson_fair, "HYP_021_THETA_DEAD_LONGSHOT_DECAY",
                    exit_mode="HOLD_TO_SETTLEMENT",
                )
                if tr is not None:
                    trades.append(tr)
                break
    return trades


def exp_hyp023_weather_horizon_rounding_model(
    contracts: Sequence[NovelContractSeries],
) -> List[Dict[str, Any]]:
    """HYP-023 (`WEATHER_HORIZON_ROUNDING_MODEL`): Weather bracket overround & horizon-shrunk Gaussian density."""
    by_event: Dict[str, List[NovelContractSeries]] = collections.defaultdict(list)
    for c in contracts:
        if c.category == "weather" and len(c.ticks) >= 3:
            by_event[c.event_id].append(c)

    trades: List[Dict[str, Any]] = []
    for ev_id, brackets in by_event.items():
        if len(brackets) >= 3:
            # Multi-bracket daily station temperature slate: identify crowd tail/shoulder overpricing
            anchor = max(brackets, key=lambda x: len(x.ticks))
            mid_step = max(0, len(anchor.ticks) // 3)
            ts_eval = anchor.ticks[mid_step].ts
            snap: List[Tuple[NovelContractSeries, int, CausalTick]] = []
            for b in brackets:
                m = _interp_causal_price_at(b.ticks, ts_eval, max_stale_sec=21600.0)
                if m is not None and b.is_entry_causal_at(m[0], min_rem_sec=14400.0):
                    snap.append((b, m[0], m[1]))
            if len(snap) >= 3:
                sum_p = sum(x[2].p_yes for x in snap)
                # Normalize implied temperature bucket probabilities & penalize retail tail brackets (4c-18c)
                for b, b_idx, b_tk in snap:
                    rem_hr = max(6.0, b_tk.sec_to_safe_cutoff / 3600.0)
                    # Horizon error shrinks as sqrt(rem_hr / 36), concentrating mass in modal bucket and starving tails
                    tail_shrink = _clamp(math.sqrt(min(36.0, rem_hr) / 36.0), 0.45, 0.90)
                    if 0.04 <= b_tk.p_yes <= 0.18 and sum_p >= 0.95:
                        p_norm = (b_tk.p_yes / max(1.0, sum_p)) * tail_shrink
                        if b_tk.p_yes - p_norm >= 0.035:
                            tr = simulate_directional_trade(
                                b, b_idx, "NO", p_norm, "HYP_023_WEATHER_HORIZON_ROUNDING",
                                exit_mode="HOLD_TO_SETTLEMENT",
                            )
                            if tr is not None:
                                trades.append(tr)
        else:
            # Standalone weather bracket: test narrow 1°C/2°F interior bucket retail YES overconfidence
            for b in brackets:
                idx = max(0, len(b.ticks) // 3)
                if not b.is_entry_causal_at(idx, min_rem_sec=14400.0):
                    continue
                is_narrow_range = bool(_TEMP_RANGE_RE.search(b.question))
                if is_narrow_range and 0.06 <= b.ticks[idx].p_yes <= 0.24:
                    p_model = _clamp(b.ticks[idx].p_yes * 0.65, 0.01, 0.50)
                    tr = simulate_directional_trade(
                        b, idx, "NO", p_model, "HYP_023_WEATHER_HORIZON_ROUNDING",
                        exit_mode="HOLD_TO_SETTLEMENT",
                    )
                    if tr is not None:
                        trades.append(tr)
    return trades


def exp_hyp024_cross_venue_consensus_anchor(
    contracts: Sequence[NovelContractSeries],
    *,
    cross_venue_funnel_path: Optional[Path] = None,
    cross_venue_sqlite_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """HYP-024 (`CROSS_VENUE_CONSENSUS_ANCHOR`): Cross-venue probability disagreement as single-venue anchor."""
    funnel_p = cross_venue_funnel_path or (REPO_ROOT / "data" / "cross_venue_shadow" / "cross_venue_funnel.jsonl")
    xv_db_p = cross_venue_sqlite_path or (
        REPO_ROOT / "data" / "cross_venue_shadow_ca_on_live" / "shadow_telemetry.sqlite3"
    )

    observed_xv_pairs: List[Dict[str, Any]] = []
    if funnel_p.exists():
        try:
            for line in funnel_p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                d = json_loads(line)
                if d.get("candidate_key") and d.get("net_edge_bps") is not None:
                    observed_xv_pairs.append(d)
        except Exception:
            pass

    fex_catalog_count = 0
    fex_snap_count = 0
    fex_subject_mids: Dict[str, float] = {}
    if xv_db_p.exists():
        try:
            xc = sqlite3.connect(f"file:{xv_db_p.resolve().as_posix()}?mode=ro", uri=True)
            fex_catalog_count = int(xc.execute("SELECT COUNT(*) FROM market_catalog").fetchone()[0])
            fex_snap_count = int(xc.execute("SELECT COUNT(*) FROM orderbook_snapshots").fetchone()[0])
            for slug, yb, ya in xc.execute(
                "SELECT slug, yes_best_bid, yes_best_ask FROM orderbook_snapshots WHERE yes_best_bid IS NOT NULL AND yes_best_ask IS NOT NULL"
            ):
                fex_subject_mids[str(slug).lower()] = 0.5 * (float(yb) + float(ya))
            xc.close()
        except Exception:
            pass

    # Match resolved Polymarket macro/crypto/sports contracts against cross-venue reference or external Binance spot anchor
    trades: List[Dict[str, Any]] = []
    by_slug = {c.market_slug.lower(): c for c in contracts}
    for d in observed_xv_pairs:
        ck = str(d.get("candidate_key", ""))
        if "polymarket:" in ck:
            parts = ck.split("polymarket:", 1)[1].split(":")
            pm_slug = parts[0].lower() if parts else ""
            c = by_slug.get(pm_slug)
            if c is not None and len(c.ticks) >= 2:
                idx = max(0, len(c.ticks) // 2)
                if c.is_entry_causal_at(idx, min_rem_sec=1800.0):
                    edge_prob = _clamp(float(d.get("net_edge_bps", 0.0)) / 10000.0, 0.02, 0.20)
                    side = "NO" if ":NO__" in ck else "YES"
                    p_mod = _clamp(c.ticks[idx].p_yes + (edge_prob if side == "YES" else -edge_prob), 0.03, 0.97)
                    tr = simulate_directional_trade(
                        c, idx, side, p_mod, "HYP_024_CROSS_VENUE_ANCHOR",
                        exit_mode="HOLD_TO_SETTLEMENT",
                    )
                    if tr is not None:
                        trades.append(tr)

    diag = {
        "local_funnel_signals_inspected": len(observed_xv_pairs),
        "forecastex_catalog_rows": fex_catalog_count,
        "forecastex_l2_snapshots": fex_snap_count,
        "matched_historical_resolved_trades": len(trades),
    }
    return trades, diag


def exp_hyp027_ensemble_disagreement_abstention(
    contracts: Sequence[NovelContractSeries],
    *,
    train_end_ts: float = GLOBAL_TRAIN_END_TS,
    min_consensus_models: int = 2,
    max_ensemble_std: float = 0.075,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """HYP-027 (`ENSEMBLE_CONVICTION_ABSTENTION`): Multi-expert consensus vs high-disagreement abstention."""
    # Fit simple category base-rate calibration shrinkage strictly on Train (`effective_cutoff_ts <= train_end_ts`)
    cat_sum_mid: Dict[str, float] = collections.defaultdict(float)
    cat_sum_out: Dict[str, float] = collections.defaultdict(float)
    cat_cnt: Dict[str, int] = collections.defaultdict(int)

    for c in contracts:
        if c.effective_cutoff_ts <= train_end_ts and len(c.ticks) >= 3 and not c.has_negation:
            p_m = c.ticks[len(c.ticks) // 3].p_yes
            cat_sum_mid[c.category] += p_m
            cat_sum_out[c.category] += c.yes_payout
            cat_cnt[c.category] += 1

    cat_bias: Dict[str, float] = {}
    for cat, n in cat_cnt.items():
        if n >= 10:
            # Shrink observed train calibration residual by 50% toward 0 to prevent overfit
            cat_bias[cat] = 0.50 * ((cat_sum_out[cat] / n) - (cat_sum_mid[cat] / n))
        else:
            cat_bias[cat] = 0.0

    # Pre-index multi-outcome slate sums for Expert 3
    slate_members: Dict[str, List[NovelContractSeries]] = collections.defaultdict(list)
    for c in contracts:
        if c.neg_risk and len(c.ticks) >= 3:
            slate_members[c.event_id].append(c)

    consensus_trades: List[Dict[str, Any]] = []
    unfiltered_trades: List[Dict[str, Any]] = []

    for c in contracts:
        if len(c.ticks) < 5 or c.is_other_or_placeholder:
            continue
        idx = min(len(c.ticks) - 2, max(2, int(len(c.ticks) * 0.40)))
        if not c.is_entry_causal_at(idx, min_rem_sec=10800.0):
            continue
        tk = c.ticks[idx]
        p_mkt = tk.p_yes
        if not (0.04 <= p_mkt <= 0.93):
            continue

        # Expert 1: Train-fitted Category & Favorite-Longshot Bayesian Calibration Prior
        if c.has_negation and 0.55 <= p_mkt <= 0.90:
            flb_adj = +0.065
        elif not c.has_negation and p_mkt <= 0.16 and c.category in NARRATIVE_CATEGORIES:
            flb_adj = -0.35 * p_mkt
        elif not c.has_negation and 0.38 <= p_mkt <= 0.62 and tk.sec_since_created <= 48.0 * 3600.0 and c.category in NARRATIVE_CATEGORIES:
            flb_adj = -0.075
        else:
            flb_adj = 0.0
        p_exp1 = _clamp(p_mkt + cat_bias.get(c.category, 0.0) + flb_adj, 0.01, 0.98)

        # Expert 2: Trajectory / Asymmetric Jump / Theta Hazard Expert
        dp_4h = _recent_delta(c.ticks, idx, 14400.0) or 0.0
        theta_adj = 0.0
        if dp_4h >= 0.10 and c.category in NARRATIVE_CATEGORIES and p_mkt <= 0.78 and not c.has_negation:
            theta_adj = -0.45 * dp_4h
        elif tk.life_frac >= 0.60 and p_mkt <= 0.18 and dp_4h <= 0.01 and not c.has_negation:
            theta_adj = -0.32 * p_mkt
        elif c.has_negation and dp_4h >= -0.02 and 0.55 <= p_mkt <= 0.90:
            theta_adj = +0.055
        elif dp_4h >= 0.10 and c.category in OBJECTIVE_FAST_CATEGORIES:
            theta_adj = +0.25 * dp_4h
        p_exp2 = _clamp(p_mkt + theta_adj, 0.01, 0.98)

        # Expert 3: Structural Slate, Listing-Age Anchor & Polarity/Fee Microstructure Expert
        p_exp3 = p_mkt
        if c.neg_risk and len(slate_members.get(c.event_id, ())) >= 3:
            s_sum = 0.0
            s_cnt = 0
            for sib in slate_members[c.event_id]:
                m_sib = _interp_causal_price_at(sib.ticks, tk.ts, max_stale_sec=21600.0)
                if m_sib is not None:
                    s_sum += m_sib[1].p_yes
                    s_cnt += 1
            if s_cnt >= 3 and s_sum > 0.50:
                p_exp3 = _clamp(p_mkt / s_sum, 0.01, 0.98)
        elif c.neg_risk and (c.neg_risk_augmented_inferred or c.registry_total_market_count >= 5) and 0.05 <= p_mkt <= 0.25 and not c.has_negation:
            p_exp3 = _clamp(p_mkt * 0.65, 0.01, 0.98)
        elif c.has_negation and 0.55 <= p_mkt <= 0.90:
            p_exp3 = _clamp(p_mkt + 0.06, 0.01, 0.98)
        elif not c.has_negation and tk.sec_since_created <= 48.0 * 3600.0 and 0.36 <= p_mkt <= 0.64 and c.category not in ("sports", "crypto"):
            p_exp3 = _clamp(p_mkt - 0.08, 0.01, 0.98)
        elif not c.has_negation and p_mkt <= 0.15 and c.fee_rate <= 0.05:
            p_exp3 = _clamp(p_mkt * 0.68, 0.01, 0.98)

        experts = [p_exp1, p_exp2, p_exp3]
        p_mean = sum(experts) / 3.0
        p_std = statistics.pstdev(experts)
        raw_diff = p_mean - p_mkt
        if abs(raw_diff) < 0.025:
            continue

        side = "YES" if raw_diff > 0 else "NO"
        # Count experts agreeing with direction by >= 1.5c
        agree_cnt = sum(
            1 for pe in experts if ((pe - p_mkt >= 0.015) if side == "YES" else (p_mkt - pe >= 0.015))
        )

        # Unfiltered baseline trade (for ablation proof!)
        tr_unfilt = simulate_directional_trade(
            c, idx, side, p_mean, "HYP_027_UNFILTERED_ABLATION",
            exit_mode="PRE_RESOLUTION_EXIT", max_hold_hours=72.0,
        )
        if tr_unfilt is not None:
            unfiltered_trades.append(tr_unfilt)

        # Conviction-filtered ensemble: require >= min_consensus_models agreement, bounded std, and LCB > cost!
        lcb_edge = abs(raw_diff) - 0.65 * p_std
        est_cost = 0.012 + c.fee_rate * p_mkt * (1.0 - p_mkt)
        if agree_cnt >= min_consensus_models and p_std <= max_ensemble_std and lcb_edge > est_cost:
            tr_cons = simulate_directional_trade(
                c, idx, side, p_mean, "HYP_027_ENSEMBLE_CONVICTION",
                exit_mode="PRE_RESOLUTION_EXIT", max_hold_hours=72.0,
            )
            if tr_cons is not None:
                consensus_trades.append(tr_cons)

    return consensus_trades, unfiltered_trades


# ---------------------------------------------------------------------------
# 5. Canonical 28-Hypothesis Registry Specification (`HYP-001` .. `HYP-028`)
# ---------------------------------------------------------------------------


def build_base_hypothesis_catalog() -> List[Dict[str, Any]]:
    """Constructs all 28 distinct, falsifiable directional hypotheses (`HYP-001`..`HYP-028`)."""

    def _h(
        hid: str,
        code: str,
        title: str,
        family: str,
        mechanism: str,
        cats: Sequence[str],
        econ: int,
        test: int,
        data: int,
        effort: int,
        statement: str,
        novelty: str,
        falsification: str,
        implemented: bool,
        strategy_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Higher econ, testability, data availability, and lower implementation friction -> higher priority
        priority = round(0.35 * econ + 0.25 * test + 0.25 * data + 0.15 * (6 - effort), 2)
        return {
            "hypothesis_id": hid,
            "code_name": code,
            "strategy_id": strategy_id or f"{hid.replace('-', '_')}_{code}",
            "title": title,
            "family": family,
            "profit_mechanism": mechanism,
            "target_categories": list(cats),
            "expected_economic_significance": econ,
            "testability": test,
            "dataset_availability": data,
            "implementation_effort": effort,
            "priority_score": priority,
            "hypothesis_statement": statement,
            "novelty_vs_dominus": novelty,
            "falsification_criterion": falsification,
            "empirically_tested_in_lab": implemented,
            "status": "QUEUED_FOR_TEST" if implemented else "SPECIFIED_AWAITING_SPECIALIST_FEED",
            "measured_evidence": {},
            "rejection_lessons_and_followup": "",
        }

    return [
        # Family 1: Cross-Contract Information Propagation Lag
        _h(
            "HYP-001", "CAL_TERM_LAG",
            "Cumulative Deadline Term-Structure Lead-Lag",
            "1. Cross-Contract Information Propagation Lag",
            "TRADING_EDGE",
            ["politics", "geopolitics", "economics_macro", "tech_ai"],
            4, 5, 4, 2,
            "When a liquid front-deadline contract ('by Date T1') reprices >=6c in <=4h while a cumulative later-deadline sibling ('by Date T2', T2 > T1) lags within <=4c term spread, implied forward hazard compresses anomalously and the back leg drifts directionally over 12h-36h without requiring simultaneous 2-leg CAL1 riskless underround.",
            "Dominus CAL1 (`EXP-PM-410`) only fires when NO(T1) + YES(T2) < $1.00 (riskless box); HYP-001 captures single-leg directional propagation lag when box sum >= $1.00.",
            "Falsified if OOS net PnL <= $0 after V2 curved fees + spread/slippage, or if cluster-bootstrap 95% CI is strictly negative.",
            True, "HYP_001_CAL_TERM_LAG",
        ),
        _h(
            "HYP-002", "FUNNEL_PREREQ_LAG",
            "Hierarchical Prerequisite-to-Outcome Funnel Lag",
            "1. Cross-Contract Information Propagation Lag",
            "TRADING_EDGE",
            ["politics", "sports", "economics_macro"],
            4, 4, 3, 3,
            "In prerequisite event pairs (Primary Nomination -> General Election; Semifinal/Conference Winner -> Championship; House Passage -> Enactment), rapid repricing of prerequisite A leaves joint outcome B temporarily miscalibrated relative to historical conditional ratio P(B|A).",
            "Dominus LP1 (`LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX`) requires deterministic state-matrix super-replication >= $1.00; HYP-002 trades conditional Bayesian beta lag single-leg.",
            "Falsified if cross-event conditional ratio reverts via A reversing rather than B catching up (OOS net EV/trade <= 0).",
            False,
        ),
        _h(
            "HYP-003", "LADDER_SLOPE_LAG",
            "Scalar Strike Ladder Interior Convexity / Kink Reversion",
            "1. Cross-Contract Information Propagation Lag",
            "TRADING_EDGE",
            ["crypto", "finance", "economics_macro", "weather"],
            4, 5, 5, 2,
            "Across >=3-rung monotonic scalar strike ladders, round-number headline strikes absorb news flow first while interior adjacent strikes lag, creating >=6.5c log-odds interpolation kinks that mean-revert within 24h.",
            "Dominus M3/D1 require strict strike dominance violation (p(K_high) > p(K_low) net of fees); HYP-003 trades interior convexity kinks even when strict monotonicity holds.",
            "Falsified if round-trip spread + V2 taker fees exceed kink reversion capture (OOS net PnL <= $0 or break-even extra cost <= 0 bps).",
            True, "HYP_003_LADDER_SLOPE_LAG",
        ),
        _h(
            "HYP-004", "THEMATIC_SPILLOVER_LAG",
            "Cross-Entity Bilateral & Sectoral Spillover Drift",
            "1. Cross-Contract Information Propagation Lag",
            "TRADING_EDGE",
            ["geopolitics", "tech_ai", "finance", "politics"],
            3, 3, 3, 4,
            "Catalyst shocks in a primary entity contract (e.g., Country A tariff / AI Lab A model release / Swing State A poll shock) propagate with a 1h-12h lag into correlated peer contracts lacking shared event_id.",
            "Not present in any Dominus module; `market_proposition_graph.py` quarantines `STATISTICAL_CORRELATION_ONLY` edges without trading them.",
            "Falsified if cross-entity beta decays faster than spread crossing cost on target peer contracts.",
            False,
        ),
        # Family 2: Multi-Outcome NegRisk Residual Probability Drift
        _h(
            "HYP-005", "NEGRISK_SUM_EXCESS_NO",
            "NegRisk Sum-of-Parts Excess -> Lagging Secondary Contender NO",
            "2. Multi-Outcome NegRisk Residual Probability Drift",
            "PROBABILITY_EDGE",
            ["politics", "sports", "culture_science", "economics_macro", "tech_ai"],
            5, 5, 5, 2,
            "When 1-2 liquid NegRisk frontrunners surge >=6c on news while secondary contenders (6c-38c) stay anchored on stale retail bids, slate sum(p_mid) exceeds 1.055; single-leg BUY NO on the most stale secondary contender harvests probability conservation without >=3-leg sequential basket risk.",
            "Dominus NR0/NR4 (`EXP-PM-404B`) are hard-blocked below $500 NAV due to >=3-leg partial-fill legging risk (`D-007`); HYP-005 executes a 1-leg directional NO trade with 0% legging exposure.",
            "Falsified if OOS net PnL <= $0 or failed vs unconditional Buy-NO baseline on identical NegRisk slates.",
            True, "HYP_005_NEGRISK_SUM_EXCESS_NO",
        ),
        _h(
            "HYP-006", "NEGRISK_COLLAPSE_YES",
            "Closed-Partition NegRisk Frontrunner Crash -> Runner-Up YES Catch-Up",
            "2. Multi-Outcome NegRisk Residual Probability Drift",
            "TRADING_EDGE",
            ["politics", "sports", "economics_macro"],
            4, 5, 4, 2,
            "On closed NegRisk partitions (`negRiskAugmented=False`), a sudden >=7c selloff in the leader temporarily depresses sum(p_mid) <= 0.945 before probability reallocates proportionally into the #2 contender.",
            "Novel single-leg upward reallocation hypothesis; Dominus NR2 converts NO pairs rather than trading #2 substitution elasticity.",
            "Falsified if leader selloffs reflect unnamed-outcome emergence or round-trip exit fees erase runner-up bounce.",
            True, "HYP_006_NEGRISK_COLLAPSE_YES",
        ),
        _h(
            "HYP-007", "AUGMENTED_CONTENDER_NO",
            "Open-Partition (`negRiskAugmented`) Named-Candidate Salience Bias (BUY NO)",
            "2. Multi-Outcome NegRisk Residual Probability Drift",
            "PROBABILITY_EDGE",
            ["politics", "culture_science", "tech_ai", "geopolitics"],
            5, 5, 4, 2,
            "In large (>=5 leg) or `negRiskAugmented=True` open-partition slates (appointments, awards, M&A), retail crowds into media-salient named mid-tier contenders (5c-22c YES), systematically underpricing the unnamed field / catch-all complement.",
            "Dominus `verify_closed_negrisk_partition()` treats `negRiskAugmented=True` purely as a block against ALL_YES arb; HYP-007 turns that exact structural property into single-leg NO directional alpha.",
            "Falsified if mid-tier named candidates in crowded/augmented slates win at or above market-implied frequencies net of fees.",
            True, "HYP_007_AUGMENTED_CONTENDER_NO",
        ),
        _h(
            "HYP-008", "NEGRISK_ELIMINATION_REDISTRIBUTION",
            "Sequential Sub-Bracket Elimination Luce Renormalization Lag",
            "2. Multi-Outcome NegRisk Residual Probability Drift",
            "TRADING_EDGE",
            ["culture_science", "crypto", "sports"],
            3, 4, 3, 3,
            "In sequential count/tournament slates (e.g., cumulative tweet count brackets or knockout stages), as lower brackets cross near-certain elimination, surviving adjacent brackets lag exact Luce/Dirichlet renormalization.",
            "Dominus `AFF1_FROZEN_SUBPERIOD_COLLAPSE` only targets deterministic riskless complete sets post-elimination.",
            "Falsified if CLOB market makers renormalize surviving brackets within <60s of sub-bracket elimination.",
            False,
        ),
        # Family 3: New-Market Price Discovery & Anchoring Bias
        _h(
            "HYP-009", "NEW_MKT_IGNORANCE_ANCHOR",
            "Newly Listed (<36h) Ignorance-Prior (38c-62c) Base-Rate NO Bias",
            "3. New-Market Price Discovery Bias",
            "PROBABILITY_EDGE",
            ["politics", "geopolitics", "tech_ai", "culture_science", "finance", "economics_macro"],
            4, 5, 5, 1,
            "Newly created non-sports/non-intraday binary markets (<36h age) seeded near maximum-entropy 50/50 (38c-62c) suffer conjunctive event base-rate neglect: novel 'Will X happen by Y?' propositions resolve NO significantly more often than 50%.",
            "Completely absent from Dominus (legacy sleeves ignored market age `sec_since_created`).",
            "Falsified if newly listed 38c-62c affirmative contracts resolve YES near 50% (OOS Brier skill <= 0 or net PnL <= $0).",
            True, "HYP_009_NEW_MKT_IGNORANCE_ANCHOR",
        ),
        _h(
            "HYP-010", "NEW_MKT_EARLY_DRIFT",
            "First-24h Specialist Price Discovery Continuation Drift",
            "3. New-Market Price Discovery Bias",
            "TRADING_EDGE",
            ["politics", "geopolitics", "tech_ai", "finance", "economics_macro", "sports"],
            4, 5, 5, 2,
            "When a newly listed (<24h) multi-day market reprices >=8c away from its initial print, informed specialists are correcting a stale listing anchor, generating positive continuation over the next 24h-48h.",
            "Novel listing-lifecycle momentum signal; distinct from sub-hourly CEX shock scalping.",
            "Falsified if early >=8c listing moves mean-revert or lose to two-way spread + V2 taker exit fees.",
            True, "HYP_010_NEW_MKT_EARLY_DRIFT",
        ),
        _h(
            "HYP-011", "MID_CYCLE_RUNG_MISANCHOR",
            "Dynamically Minted Mid-Cycle Extreme Strike Extrapolation Bias",
            "3. New-Market Price Discovery Bias",
            "PROBABILITY_EDGE",
            ["crypto", "finance", "culture_science"],
            3, 3, 3, 3,
            "New extreme strikes minted mid-week/mid-month immediately after a large underlying rally attract retail recency-bias YES buying above implied vol surface fair value.",
            "Dominus Oct 28 forensic audit only fixed creation-timestamp subset bugs on `B3`/`CM_B3`; never tested fading newly minted OOTM hype rungs.",
            "Falsified if newly minted mid-cycle OOTM rungs realize continuation matching or exceeding implied volatility.",
            False,
        ),
        # Family 4: Asymmetric News / Jump Response
        _h(
            "HYP-012", "ASYM_UP_SPIKE_FADE",
            "Narrative Category Retail YES Excitement Spike Reversion",
            "4. Asymmetric News & Jump Response",
            "TRADING_EDGE",
            ["politics", "geopolitics", "culture_science", "tech_ai"],
            4, 5, 5, 2,
            "In narrative categories, rapid upward YES spikes (>= +12c in <=4h, staying <=78c pre-clinch) driven by viral headlines overshoot Bayesian posteriors and partially revert over the next 12h-36h (BUY NO).",
            "Novel asymmetric upward-jump fade on multi-day narrative markets; Dominus never traded narrative jump reversion.",
            "Falsified if upward narrative jumps represent underreacted genuine breakthroughs (continuation > reversion OOS).",
            True, "HYP_012_ASYM_UP_SPIKE_FADE",
        ),
        _h(
            "HYP-013", "ASYM_DOWN_CRASH_DRIFT",
            "Bad-News Disconfirmation Crash & Disposition Bagholder Drift (BUY NO)",
            "4. Asymmetric News & Jump Response",
            "PROBABILITY_EDGE",
            ["politics", "geopolitics", "tech_ai", "culture_science", "finance", "economics_macro"],
            5, 5, 5, 2,
            "Sharp downward YES drops (<= -12c in <=4h into 10c-65c) reflect hard disconfirming events, while underwater retail YES holders exhibit the disposition effect (refusing to realize losses), creating positive post-crash NO drift to settlement.",
            "Novel behavioral disposition-effect asymmetry (contrasting upward excitement overshoot vs downward disconfirmation underreaction).",
            "Falsified if sharp >=12c drops bounce back symmetrically (OOS net PnL <= $0 after V2 fees + spread).",
            True, "HYP_013_ASYM_DOWN_CRASH_DRIFT",
        ),
        _h(
            "HYP-014", "CATEGORY_JUMP_SPLIT",
            "Objective-Fast Continuation vs Subjective-Narrative Reversion Split",
            "4. Asymmetric News & Jump Response",
            "TRADING_EDGE",
            ["sports", "crypto", "finance", "economics_macro", "politics", "geopolitics", "culture_science"],
            4, 5, 5, 2,
            "Identical >=11c price jumps exhibit opposite serial correlation across oracle regimes: momentum continuation in objective score/macro/spot categories vs upward-spike reversion in subjective narrative categories.",
            "First cross-category jump-autocorrelation sign-flip test in Dominus.",
            "Falsified if category-conditioned sign rule fails to achieve positive OOS net PnL after round-trip trading friction.",
            True, "HYP_014_CATEGORY_JUMP_SPLIT",
        ),
        _h(
            "HYP-015", "SCHEDULED_EVENT_POST_REVERSION",
            "Post-Macro/Catalyst Tail-Ticket Implied-Vol Crush",
            "4. Asymmetric News & Jump Response",
            "PROBABILITY_EDGE",
            ["economics_macro", "politics", "finance"],
            3, 4, 3, 3,
            "Speculative tail YES tickets (5c-20c) bid up ahead of scheduled FOMC/CPI/earnings releases suffer sluggish manual quote cleanup in the 15m-2h window after a non-tail release.",
            "Distinct from `COND1_MACRO_PARTITION_BOX` deterministic boxes.",
            "Falsified if automated macro market makers reprice tail quotes to zero within <5s of BLS/Fed timestamp.",
            False,
        ),
        # Family 5: Decomposed Favorite-Longshot & Asymmetric NO-Bias
        _h(
            "HYP-016", "NARRATIVE_LONGSHOT_NO",
            "Narrative Category 3c-13c Retail Lottery Overpayment & V2 Fee Asymmetry (BUY NO)",
            "5. Favorite-Longshot & Microstructure Fee Asymmetry",
            "PROBABILITY_EDGE",
            ["politics", "geopolitics", "culture_science", "tech_ai"],
            5, 5, 5, 1,
            "Retail buyers overpay for 3c-13c affirmative 'dramatic YES' tickets in Politics/Geopolitics/Culture/Tech for skewness & headline leverage, while Protocol V2 curved fees charge 9x-20x lower bps per dollar deployed on 87c-97c NO than on YES.",
            "Decomposes FLB jointly by narrative category AND Nov 2026 V2 curved fee per-dollar asymmetry (`#11`/`#19`), accounting for 50-50 void & UMA dispute tail risk.",
            "Falsified if rare tail YES wins + 50-50 voids + UMA disputes wipe out the 87c-97c NO carry (`RT-08` negative-skew test: OOS net PnL <= $0 or cluster CI95_lo < 0).",
            True, "HYP_016_NARRATIVE_LONGSHOT_NO",
        ),
        _h(
            "HYP-017", "FEE_REGIME_FLB_DISTORTION",
            "Zero-Fee (`0%`) vs Curved-Fee (`3%-7%`) Calibration Slope Divergence",
            "5. Favorite-Longshot & Microstructure Fee Asymmetry",
            "PROBABILITY_EDGE",
            ["geopolitics", "politics", "sports", "crypto"],
            4, 4, 5, 2,
            "Zero-fee markets (`41.2%` of Geopolitics, `13.6%` of Politics) retain cleaner net realizable calibration alpha near midrange probabilities (25c-75c) where 4%-7% V2 quadratic fees impose 100-350 bps entry tax.",
            "Directly operationalizes the Nov 2026 Polymarket V2 fee-schedule bifurcation discovered in `@universe-map` and `@microstructure`.",
            "Falsified if zero-fee midrange contracts are more tightly arbitraged by 0-fee bots than V2 fee-bearing contracts.",
            False,
        ),
        _h(
            "HYP-018", "SEMANTIC_POLARITY_AWARE",
            "Question-Polarity Semantic Asymmetry (Affirmative Action vs Negated Status Quo)",
            "5. Favorite-Longshot & Microstructure Fee Asymmetry",
            "PROBABILITY_EDGE",
            ["politics", "geopolitics", "economics_macro", "tech_ai", "finance", "culture_science"],
            5, 5, 5, 2,
            "Retail lottery bias attaches to 'dramatic change occurring', NOT the literal token label YES: on negated questions ('Will X NOT happen?'), retail overpays for NO, so polarity-aware positioning (BUY YES on negated status-quo, BUY NO on affirmative longshots) beats naive Buy-NO.",
            "Explicitly turns Red-Team hazard `RT-04` (inverted contract semantics) into a testable behavioral alpha signal.",
            "Falsified if polarity-aware selection fails to outperform naive unconditional Buy-NO on OOS net PnL and Brier skill.",
            True, "HYP_018_SEMANTIC_POLARITY_AWARE",
        ),
        _h(
            "HYP-019", "REWARD_SUBSIDY_SKEW",
            "Liquidity-Reward (`rewards_max_spread`) & Holding-Reward Quote Stickiness",
            "5. Favorite-Longshot & Microstructure Fee Asymmetry",
            "TRADING_EDGE",
            ["politics", "economics_macro", "geopolitics"],
            3, 3, 3, 3,
            "Markets paying daily maker-spread subsidies (`rewards_max_spread > 0`) or 4% holding rewards attract symmetric yield-farming quotes that lag fundamental directional trends.",
            "Dominus Graveyard rejected `QMIN1` maker farming; HYP-019 takes the opposite side (directional Taker against subsidized sticky farmers).",
            "Falsified if historical time-stamped reward pool changes lack sufficient archive history to isolate subsidized vs unsubsidized eras.",
            False,
        ),
        # Family 6: Resolution-Proximity Theta & Convergence Distortion
        _h(
            "HYP-020", "THETA_FAVORITE_CARRY",
            "Pre-Clinch (72h->8h TTE) Capital-Impatience Favorite Discount Carry",
            "6. Resolution-Proximity Theta & Convergence Distortion",
            "PROBABILITY_EDGE",
            ["sports", "crypto", "economics_macro", "finance", "politics"],
            4, 5, 5, 2,
            "Strictly prior to outcome clinch (8h <= TTE <= 72h on objective-oracle markets), capital-constrained traders sell 82c-93c favorites at a 2c-5c impatience discount to free pUSD collateral for new events.",
            "Strictly pre-clinch directional carry (`0.82-0.93`); completely distinct from post-clinch `BOND1` (`0.990-0.995` after primary oracle finalization).",
            "Falsified if pre-clinch 82c-93c favorites suffer upset/50-50-void losses exceeding the 2c-5c impatience discount (`RT-01` & `RT-08` audited).",
            True, "HYP_020_THETA_FAVORITE_CARRY",
        ),
        _h(
            "HYP-021", "THETA_DEAD_LONGSHOT_DECAY",
            "Final-Window (48h->6h TTE) Dying-Catalyst Poisson Theta Decay (BUY NO)",
            "6. Resolution-Proximity Theta & Convergence Distortion",
            "PROBABILITY_EDGE",
            ["politics", "geopolitics", "tech_ai", "culture_science", "economics_macro", "finance"],
            5, 5, 5, 2,
            "When a multi-day event contract has elapsed >=70% of its lifetime without upward catalyst (`p_t <= p_0 + 2c`) yet still trades at 4c-15c with 6h-48h left, sunk-cost retail holders under-decay remaining Poisson hazard, yielding strong BUY NO edge.",
            "First continuous-time Poisson hazard vs sunk-cost theta model tested on Polymarket.",
            "Falsified if late-window surprise catalysts justify 4c-15c pricing (OOS net PnL <= $0 or negative Brier skill).",
            True, "HYP_021_THETA_DEAD_LONGSHOT_DECAY",
        ),
        _h(
            "HYP-022", "OBJECTIVE_VS_DISPUTE_CONVERGENCE",
            "Objective Feed vs Subjective Wording UMA Dispute Risk Premium Filter",
            "6. Resolution-Proximity Theta & Convergence Distortion",
            "PROBABILITY_EDGE",
            ["geopolitics", "politics", "weather", "sports"],
            4, 4, 4, 2,
            "Apparent late-stage discounts (88c-95c) on subjective wording or sensor-fragile markets reflect rational compensation for UMA $750 dispute / 50-50 void risk rather than free alpha; filtering strictly on deterministic resolution sources improves CVaR_95.",
            "Directly inspired by Dominus's real $50.51 `KMIA` Nov 7 UMA dispute (`D-001` / `D-009`).",
            "Falsified if subjective late-stage favorites exhibit equal or lower void/dispute tail loss than objective-source contracts.",
            False,
        ),
        # Family 7: Specialist Domain & Meta-Ensemble Models
        _h(
            "HYP-023", "WEATHER_HORIZON_ROUNDING",
            "Weather Horizon-Decay Variance & Narrow-Bracket Tail Overpricing Model",
            "7. Specialist Domain & Meta-Conviction Models",
            "PROBABILITY_EDGE",
            ["weather"],
            4, 5, 4, 3,
            "Prior to solar peak, retail overprices 4c-22c narrow (`1C`/`2F`) shoulder/tail temperature brackets relative to horizon-shrunk NWP error variance `sigma(h) ~ sqrt(h/36)` and discrete whole-degree rounding mass.",
            "Distinct from `W1_SOLAR_PEAK_LOCK` (post-peak METAR T-remark lock) and `W2_ENSEMBLE_VALUE` (which bought YES tails; HYP-023 sells overpriced narrow/tail weather YES via BUY NO!).",
            "Falsified if weather market makers price horizon variance accurately after 5% `weather_fees` (`RT-03`) and `D-009` dispute haircuts.",
            True, "HYP_023_WEATHER_HORIZON_ROUNDING",
        ),
        _h(
            "HYP-024", "CROSS_VENUE_ANCHOR",
            "Cross-Venue Consensus Disagreement as Single-Venue Polymarket Directional Anchor",
            "7. Specialist Domain & Meta-Conviction Models",
            "PROBABILITY_EDGE",
            ["economics_macro", "sports", "crypto", "politics"],
            4, 4, 3, 3,
            "Using read-only external venue quotes (`ForecastEx`, `Limitless`, `SX Bet` in `data/cross_venue_shadow*`) as a Bayesian probability anchor to trade single-venue on Polymarket avoids cross-venue capital fragmentation and CA-ON execution blocks while harvesting >=4c cross-market consensus divergence.",
            "Stage G (`CROSS_VENUE_KALSHI_DERIBIT_PROBE`) required 2-venue simultaneous riskless execution (`blocked < $500 NAV`); HYP-024 keeps 100% of pUSD on Polymarket single-venue.",
            "Falsified or classified `Awaiting data` if local historical cross-venue overlap sample size `N_clusters < 20` on resolved contracts.",
            True, "HYP_024_CROSS_VENUE_ANCHOR",
        ),
        _h(
            "HYP-025", "DIURNAL_US_OPEN_CALIBRATION",
            "Overnight Thin-Book Retail Excursion vs 08:30-10:30 ET Specialist Reversion",
            "7. Specialist Domain & Meta-Conviction Models",
            "TRADING_EDGE",
            ["politics", "economics_macro", "finance"],
            3, 4, 4, 3,
            "Low-volume price excursions occurring during 02:00-06:30 ET thin liquidity on US Politics/Macro contracts partially revert during 08:30-11:00 ET US specialist participation.",
            "Dominus only applied CME/NYSE session clocks as hard blackouts on XAU/Equities (`CM_B2`), never as diurnal US-open calibration alpha.",
            "Falsified if 15m/60m `/prices-history` lacks hourly volume weights needed to separate thin retail drifts from genuine European-hours breaking news.",
            False,
        ),
        _h(
            "HYP-026", "BAYESIAN_SUBEVENT_SEQUENTIAL",
            "Bayesian Likelihood-Ratio Updating After Partial Sub-Event Resolution",
            "7. Specialist Domain & Meta-Conviction Models",
            "PROBABILITY_EDGE",
            ["sports", "politics", "economics_macro"],
            4, 3, 3, 4,
            "After sequential sub-events resolve (Map 1 / Set 1 / early primary state / CPI sub-print), crowd prices exhibit Edwards conservatism on moderate likelihood ratios and representativeness overshoot on vivid streaks.",
            "Dominus `API1_ESPORTS_BO3` only traded deterministic post-Map-1 handicap locks, never probabilistic series win updating.",
            "Falsified if live sports/election series markets incorporate exact Markov transition matrices within bid-ask spread.",
            False,
        ),
        _h(
            "HYP-027", "ENSEMBLE_CONVICTION",
            "Multi-Expert Epistemic Disagreement Abstention & LCB Conviction Filter",
            "7. Specialist Domain & Meta-Conviction Models",
            "PROBABILITY_EDGE",
            ["politics", "geopolitics", "culture_science", "tech_ai", "economics_macro", "finance", "weather", "sports", "crypto"],
            5, 5, 5, 2,
            "Combining orthogonal domain experts (Category/FLB Calibration, Trajectory/Theta Hazard, Slate Conservation) and ABSTAINING whenever expert disagreement `sigma_ens` is high (`|edge| - 0.75*sigma_ens <= cost`) raises OOS net EV/trade, profit per dollar-day, and cost break-even bps vs unfiltered signals.",
            "Novel epistemic-abstention meta-filter; Dominus previously combined sleeves via static hard gates without cross-model disagreement shrinkage.",
            "Falsified if conviction-filtered ensemble fails to improve OOS net EV/trade, Brier skill, or cost break-even bps over its unfiltered ablation (`HYP_027_UNFILTERED_ABLATION`).",
            True, "HYP_027_ENSEMBLE_CONVICTION",
        ),
        _h(
            "HYP-028", "VOLUME_SURGE_WAKEUP_DRIFT",
            "Dormant-Market Sudden Volume-Surge Inventory Squeeze Continuation",
            "7. Specialist Domain & Meta-Conviction Models",
            "TRADING_EDGE",
            ["geopolitics", "politics", "tech_ai", "finance"],
            3, 3, 2, 4,
            "Dormant contracts (<$1k/24h volume for >=5d) experiencing a >10x hourly trade-arrival surge exhibit sticky passive liquidity-provider ladders that absorb informed flow too slowly, creating 2h-12h continuation.",
            "Novel microstructure wakeup hypothesis; requires historical timestamped per-bar volume archives.",
            "Falsified or `Awaiting data` until Polymarket CLOB trade-tape bar volumes are archived across multi-month dormant contracts (`/prices-history` omits bar volume).",
            False,
        ),
    ]


# ---------------------------------------------------------------------------
# 6. Full Experiment Suite Runner, Principle-9 Rejection Forensics & Registry Sync
# ---------------------------------------------------------------------------


def _synthesize_rejection_or_validation_lesson(
    hid: str,
    code: str,
    status_label: str,
    oos_metrics: Mapping[str, Any],
    holdout_metrics: Mapping[str, Any],
    extra_diag: Optional[Mapping[str, Any]] = None,
    reasons: Sequence[str] = (),
) -> str:
    oos_samp = oos_metrics.get("oos_sample_size") or {}
    n_oos = int(oos_samp.get("n_trades", 0))
    n_cl = int(oos_samp.get("n_clusters", 0))
    net_oos = float(oos_metrics.get("net_pnl_usd", 0.0))
    gross_oos = float(oos_metrics.get("gross_pnl_usd", 0.0))
    be_bps = float((oos_metrics.get("cost_sensitivity") or {}).get("breakeven_extra_slippage_bps") or 0.0)
    reason_blob = "; ".join(str(r) for r in reasons)

    if status_label == "Awaiting data":
        xv = extra_diag or {}
        return (
            f"Awaiting forward shadow accumulation: local resolved overlap yielded N={n_oos} trades "
            f"(inspected {xv.get('local_funnel_signals_inspected', 0)} cross-venue funnel rows & "
            f"{xv.get('forecastex_l2_snapshots', 0)} ForecastEx L2 snapshots). "
            "Follow-up: wire read-only cross-venue consensus midpoints into `shadow_runner.py` to log >=50 forward resolved pairs."
        )
    if status_label == "Rejected":
        if net_oos > 0.0:
            return (
                f"Rejected on statistical stability / holdout gate despite positive aggregate OOS Net PnL "
                f"(+${net_oos:.2f} across {n_oos} OOS trades / {n_cl} clusters; reasons: {reason_blob}). "
                "Follow-up experiment: replace hard step-threshold cutoffs with parameter-free monotonic shrinkage in `shadow_runner.py`."
            )
        if gross_oos > 0.0:
            return (
                f"Rejected on net execution friction (Principle 9): raw gross directional signal was positive "
                f"(+${gross_oos:.2f} across {n_oos} OOS trades / {n_cl} clusters), but Protocol V2 curved taker fees + "
                f"two-way spread/slippage turned net PnL negative (${net_oos:.2f}). "
                "Follow-up experiment: re-test strictly as passive `postOnly=True` Maker (`0.0` fee) with adverse-selection shield in `shadow_runner.py`."
            )
        return (
            f"Rejected on negative gross & net OOS expectancy (${net_oos:.2f} net / ${gross_oos:.2f} gross across "
            f"{n_oos} OOS trades / {n_cl} clusters): Polymarket crowd prices already incorporate or over-discount this effect "
            f"(or `50-50` void / `0.00` dispute tails offset small favorite carries). "
            "Follow-up experiment: invert signal polarity or restrict strictly to zero-fee (`feesEnabled=False`) Geopolitics/Politics slates."
        )
    if status_label in ("Insufficient evidence", "Promising but preliminary"):
        return (
            f"{status_label}: OOS net PnL=${net_oos:.2f} across {n_oos} OOS trades / {n_cl} clusters "
            f"(holdout=${float(holdout_metrics.get('net_pnl_usd', 0.0)):.2f}; break-even extra cost={be_bps:.1f} bps; "
            f"reasons: {reason_blob}). Follow-up: accrue forward out-of-sample clusters in `shadow_runner.py`."
        )
    return (
        f"Validated positive OOS net edge (+${net_oos:.2f} across {n_oos} OOS trades / {n_cl} clusters; "
        f"sealed holdout=+${float(holdout_metrics.get('net_pnl_usd', 0.0)):.2f}; break-even extra cost=+{be_bps:.1f} bps) "
        f"surviving V2 curved fees, calibrated spread/depth slippage, and 50-50 void / D-009 dispute payouts."
    )


def run_all_novel_alpha_experiments(
    db_path: Path = DEFAULT_HISTORICAL_DB,
    manifest_path: Path = DEFAULT_MANIFEST_JSON,
    core_results_path: Path = DEFAULT_CORE_RESULTS_JSON,
    n_boot: int = 2000,
    seed: int = 20261112,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Executes all 17 testable novel directional experiments + perturbation variants and builds registry + results."""
    from directional_alpha.statistical_validation import (
        StrategyCandidateInput,
        normalize_trade_record,
        validate_all_candidates_and_build_leaderboard,
    )

    contracts, split_meta = load_causal_dataset(db_path=db_path, manifest_path=manifest_path)
    train_end_ts = float(split_meta["train_end_ts"])
    val_end_ts = float(split_meta["val_end_ts"])
    embargo_sec = float(split_meta.get("embargo_sec", DEFAULT_EMBARGO_SEC))

    base_catalog = build_base_hypothesis_catalog()
    cat_by_sid = {h["strategy_id"]: h for h in base_catalog}

    # Execute all 17 empirical novel detectors + 4-point symmetric perturbation grids (`RT-07` trial accounting!)
    xv_trades, xv_diag = exp_hyp024_cross_venue_consensus_anchor(contracts)
    ens_trades, ens_unfiltered = exp_hyp027_ensemble_disagreement_abstention(
        contracts, train_end_ts=train_end_ts, min_consensus_models=2, max_ensemble_std=0.075
    )
    ens_tight, _ = exp_hyp027_ensemble_disagreement_abstention(
        contracts, train_end_ts=train_end_ts, min_consensus_models=3, max_ensemble_std=0.060
    )
    ens_mid, _ = exp_hyp027_ensemble_disagreement_abstention(
        contracts, train_end_ts=train_end_ts, min_consensus_models=2, max_ensemble_std=0.065
    )
    ens_loose, _ = exp_hyp027_ensemble_disagreement_abstention(
        contracts, train_end_ts=train_end_ts, min_consensus_models=2, max_ensemble_std=0.095
    )

    experiment_bundles: List[Tuple[str, List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]], bool, Dict[str, Any]]] = [
        (
            "HYP_001_CAL_TERM_LAG",
            exp_hyp001_deadline_term_lag(contracts, min_front_jump=0.06, max_term_spread=0.04),
            {
                "minus20": exp_hyp001_deadline_term_lag(contracts, min_front_jump=0.048, max_term_spread=0.05),
                "minus10": exp_hyp001_deadline_term_lag(contracts, min_front_jump=0.054, max_term_spread=0.045),
                "base": exp_hyp001_deadline_term_lag(contracts, min_front_jump=0.06, max_term_spread=0.04),
                "plus20": exp_hyp001_deadline_term_lag(contracts, min_front_jump=0.072, max_term_spread=0.03),
            },
            False,
            {},
        ),
        (
            "HYP_003_LADDER_SLOPE_LAG",
            exp_hyp003_strike_ladder_kink(contracts, min_kink_residual=0.065),
            {
                "minus20": exp_hyp003_strike_ladder_kink(contracts, min_kink_residual=0.052),
                "minus10": exp_hyp003_strike_ladder_kink(contracts, min_kink_residual=0.058),
                "base": exp_hyp003_strike_ladder_kink(contracts, min_kink_residual=0.065),
                "plus20": exp_hyp003_strike_ladder_kink(contracts, min_kink_residual=0.078),
            },
            False,
            {},
        ),
        (
            "HYP_005_NEGRISK_SUM_EXCESS_NO",
            exp_hyp005_negrisk_sum_excess_no(contracts, min_slate_sum=1.055, min_leader_surge=0.06),
            {
                "minus20": exp_hyp005_negrisk_sum_excess_no(contracts, min_slate_sum=1.040, min_leader_surge=0.048),
                "minus10": exp_hyp005_negrisk_sum_excess_no(contracts, min_slate_sum=1.048, min_leader_surge=0.054),
                "base": exp_hyp005_negrisk_sum_excess_no(contracts, min_slate_sum=1.055, min_leader_surge=0.06),
                "plus20": exp_hyp005_negrisk_sum_excess_no(contracts, min_slate_sum=1.070, min_leader_surge=0.072),
            },
            False,
            {},
        ),
        (
            "HYP_006_NEGRISK_COLLAPSE_YES",
            exp_hyp006_negrisk_collapse_yes(contracts, max_slate_sum=0.945, leader_drop=-0.07),
            {
                "minus20": exp_hyp006_negrisk_collapse_yes(contracts, max_slate_sum=0.960, leader_drop=-0.056),
                "minus10": exp_hyp006_negrisk_collapse_yes(contracts, max_slate_sum=0.952, leader_drop=-0.063),
                "base": exp_hyp006_negrisk_collapse_yes(contracts, max_slate_sum=0.945, leader_drop=-0.07),
                "plus20": exp_hyp006_negrisk_collapse_yes(contracts, max_slate_sum=0.930, leader_drop=-0.084),
            },
            False,
            {},
        ),
        (
            "HYP_007_AUGMENTED_CONTENDER_NO",
            exp_hyp007_augmented_contender_no(contracts, p_lo=0.05, p_hi=0.22),
            {
                "minus20": exp_hyp007_augmented_contender_no(contracts, p_lo=0.04, p_hi=0.26),
                "minus10": exp_hyp007_augmented_contender_no(contracts, p_lo=0.045, p_hi=0.24),
                "base": exp_hyp007_augmented_contender_no(contracts, p_lo=0.05, p_hi=0.22),
                "plus20": exp_hyp007_augmented_contender_no(contracts, p_lo=0.06, p_hi=0.18),
            },
            False,
            {},
        ),
        (
            "HYP_009_NEW_MKT_IGNORANCE_ANCHOR",
            exp_hyp009_new_market_ignorance_anchor(contracts, max_age_hours=36.0, band_lo=0.38, band_hi=0.62),
            {
                "minus20": exp_hyp009_new_market_ignorance_anchor(contracts, max_age_hours=48.0, band_lo=0.35, band_hi=0.65),
                "minus10": exp_hyp009_new_market_ignorance_anchor(contracts, max_age_hours=42.0, band_lo=0.365, band_hi=0.635),
                "base": exp_hyp009_new_market_ignorance_anchor(contracts, max_age_hours=36.0, band_lo=0.38, band_hi=0.62),
                "plus20": exp_hyp009_new_market_ignorance_anchor(contracts, max_age_hours=24.0, band_lo=0.40, band_hi=0.60),
            },
            False,
            {},
        ),
        (
            "HYP_010_NEW_MKT_EARLY_DRIFT",
            exp_hyp010_new_market_early_smart_drift(contracts, min_discovery_move=0.08),
            {
                "minus20": exp_hyp010_new_market_early_smart_drift(contracts, min_discovery_move=0.064),
                "minus10": exp_hyp010_new_market_early_smart_drift(contracts, min_discovery_move=0.072),
                "base": exp_hyp010_new_market_early_smart_drift(contracts, min_discovery_move=0.08),
                "plus20": exp_hyp010_new_market_early_smart_drift(contracts, min_discovery_move=0.096),
            },
            False,
            {},
        ),
        (
            "HYP_012_ASYM_UP_SPIKE_FADE",
            exp_hyp012_narrative_up_spike_fade(contracts, min_up_jump=0.12),
            {
                "minus20": exp_hyp012_narrative_up_spike_fade(contracts, min_up_jump=0.096),
                "minus10": exp_hyp012_narrative_up_spike_fade(contracts, min_up_jump=0.108),
                "base": exp_hyp012_narrative_up_spike_fade(contracts, min_up_jump=0.12),
                "plus20": exp_hyp012_narrative_up_spike_fade(contracts, min_up_jump=0.144),
            },
            False,
            {},
        ),
        (
            "HYP_013_ASYM_DOWN_CRASH_DRIFT",
            exp_hyp013_down_crash_disposition_drift(contracts, max_down_jump=-0.12),
            {
                "minus20": exp_hyp013_down_crash_disposition_drift(contracts, max_down_jump=-0.096),
                "minus10": exp_hyp013_down_crash_disposition_drift(contracts, max_down_jump=-0.108),
                "base": exp_hyp013_down_crash_disposition_drift(contracts, max_down_jump=-0.12),
                "plus20": exp_hyp013_down_crash_disposition_drift(contracts, max_down_jump=-0.144),
            },
            False,
            {},
        ),
        (
            "HYP_014_CATEGORY_JUMP_SPLIT",
            exp_hyp014_category_jump_regime_split(contracts, jump_mag=0.11),
            {
                "minus20": exp_hyp014_category_jump_regime_split(contracts, jump_mag=0.088),
                "minus10": exp_hyp014_category_jump_regime_split(contracts, jump_mag=0.099),
                "base": exp_hyp014_category_jump_regime_split(contracts, jump_mag=0.11),
                "plus20": exp_hyp014_category_jump_regime_split(contracts, jump_mag=0.132),
            },
            False,
            {},
        ),
        (
            "HYP_016_NARRATIVE_LONGSHOT_NO",
            exp_hyp016_narrative_longshot_no_bias(contracts, p_lo=0.03, p_hi=0.13),
            {
                "minus20": exp_hyp016_narrative_longshot_no_bias(contracts, p_lo=0.025, p_hi=0.155),
                "minus10": exp_hyp016_narrative_longshot_no_bias(contracts, p_lo=0.028, p_hi=0.142),
                "base": exp_hyp016_narrative_longshot_no_bias(contracts, p_lo=0.03, p_hi=0.13),
                "plus20": exp_hyp016_narrative_longshot_no_bias(contracts, p_lo=0.035, p_hi=0.105),
            },
            False,
            {},
        ),
        (
            "HYP_018_SEMANTIC_POLARITY_AWARE",
            exp_hyp018_semantic_polarity_asymmetry(contracts),
            {"base": exp_hyp018_semantic_polarity_asymmetry(contracts)},
            False,
            {},
        ),
        (
            "HYP_020_THETA_FAVORITE_CARRY",
            exp_hyp020_theta_impatience_favorite_carry(contracts, tte_min_hr=8.0, tte_max_hr=72.0),
            {
                "minus20": exp_hyp020_theta_impatience_favorite_carry(contracts, tte_min_hr=6.0, tte_max_hr=96.0),
                "minus10": exp_hyp020_theta_impatience_favorite_carry(contracts, tte_min_hr=7.0, tte_max_hr=84.0),
                "base": exp_hyp020_theta_impatience_favorite_carry(contracts, tte_min_hr=8.0, tte_max_hr=72.0),
                "plus20": exp_hyp020_theta_impatience_favorite_carry(contracts, tte_min_hr=12.0, tte_max_hr=48.0),
            },
            False,
            {},
        ),
        (
            "HYP_021_THETA_DEAD_LONGSHOT_DECAY",
            exp_hyp021_theta_dying_longshot_decay(contracts, tte_min_hr=6.0, tte_max_hr=48.0),
            {
                "minus20": exp_hyp021_theta_dying_longshot_decay(contracts, tte_min_hr=5.0, tte_max_hr=60.0),
                "minus10": exp_hyp021_theta_dying_longshot_decay(contracts, tte_min_hr=5.5, tte_max_hr=54.0),
                "base": exp_hyp021_theta_dying_longshot_decay(contracts, tte_min_hr=6.0, tte_max_hr=48.0),
                "plus20": exp_hyp021_theta_dying_longshot_decay(contracts, tte_min_hr=8.0, tte_max_hr=36.0),
            },
            False,
            {},
        ),
        (
            "HYP_023_WEATHER_HORIZON_ROUNDING",
            exp_hyp023_weather_horizon_rounding_model(contracts),
            {"base": exp_hyp023_weather_horizon_rounding_model(contracts)},
            False,
            {},
        ),
        (
            "HYP_024_CROSS_VENUE_ANCHOR",
            xv_trades,
            {"base": xv_trades},
            len(xv_trades) < 10,
            xv_diag,
        ),
        (
            "HYP_027_ENSEMBLE_CONVICTION",
            ens_trades,
            {
                "tight_consensus": ens_tight,
                "mid_consensus": ens_mid,
                "base": ens_trades,
                "loose_consensus": ens_loose,
            },
            False,
            {"unfiltered_ablation_trade_count": len(ens_unfiltered)},
        ),
    ]

    candidates: List[StrategyCandidateInput] = []
    raw_trades_by_sid: Dict[str, List[Dict[str, Any]]] = {}
    raw_variants_by_sid: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    extra_diag_by_sid: Dict[str, Dict[str, Any]] = {}

    for sid, tr_list, var_map, awaiting_flag, extra_d in experiment_bundles:
        h_meta = cat_by_sid[sid]
        norm_trades = [normalize_trade_record(t, default_strategy_id=sid) for t in tr_list]
        norm_vars = {
            vk: [normalize_trade_record(t, default_strategy_id=f"{sid}:{vk}") for t in vt]
            for vk, vt in var_map.items()
        }
        raw_trades_by_sid[sid] = tr_list
        raw_variants_by_sid[sid] = var_map
        extra_diag_by_sid[sid] = extra_d

        candidates.append(
            StrategyCandidateInput(
                strategy_id=sid,
                family=h_meta["family"],
                pillar="Novel Alpha Lab (Agent H)",
                description=h_meta["title"],
                mechanism=h_meta["profit_mechanism"],
                trades=norm_trades,
                variant_trades=norm_vars,
                awaiting_data=awaiting_flag,
                num_internal_variants_tested=max(1, len(var_map)),
                metadata={
                    "hypothesis_id": h_meta["hypothesis_id"],
                    "code_name": h_meta["code_name"],
                    "target_categories": h_meta["target_categories"],
                    "falsification_criterion": h_meta["falsification_criterion"],
                    "extra_diagnostics": extra_d,
                },
            )
        )

    validation_report = validate_all_candidates_and_build_leaderboard(
        candidates,
        embargo_sec=embargo_sec,
        reference_bankroll_usd=500.0,
        n_boot=n_boot,
        seed=seed,
        explicit_train_end_ts=train_end_ts,
        explicit_val_end_ts=val_end_ts,
    )

    lb_by_sid = {e["strategy_id"]: e for e in validation_report["leaderboard"]}

    # Also compute unfiltered ablation comparison for HYP-027
    unfilt_obs = [t for t in ens_unfiltered if t["entry_ts"] > train_end_ts + embargo_sec]
    cons_obs = [t for t in ens_trades if t["entry_ts"] > train_end_ts + embargo_sec]
    ablation_summary = {
        "unfiltered_oos_trades": len(unfilt_obs),
        "unfiltered_oos_net_pnl_usd": round(sum(t["net_pnl_usd"] for t in unfilt_obs), 4),
        "unfiltered_oos_avg_net_per_trade_usd": round(
            sum(t["net_pnl_usd"] for t in unfilt_obs) / max(1, len(unfilt_obs)), 4
        ),
        "conviction_filtered_oos_trades": len(cons_obs),
        "conviction_filtered_oos_net_pnl_usd": round(sum(t["net_pnl_usd"] for t in cons_obs), 4),
        "conviction_filtered_oos_avg_net_per_trade_usd": round(
            sum(t["net_pnl_usd"] for t in cons_obs) / max(1, len(cons_obs)), 4
        ),
    }

    strategy_outputs: List[Dict[str, Any]] = []
    for h in base_catalog:
        sid = h["strategy_id"]
        if sid in lb_by_sid:
            entry = lb_by_sid[sid]
            label = entry["classification"]
            oos_m = entry["combined_oos_metrics"]
            hold_m = entry["sealed_holdout_metrics"]
            train_m = entry["train_metrics"]
            val_m = entry["validation_metrics"]
            lesson = _synthesize_rejection_or_validation_lesson(
                h["hypothesis_id"],
                h["code_name"],
                label,
                oos_m,
                hold_m,
                extra_diag_by_sid.get(sid),
                reasons=entry["classification_reasons"],
            )
            h["status"] = label
            h["measured_evidence"] = {
                "classification": label,
                "classification_reasons": entry["classification_reasons"],
                "integrity_violations": entry["integrity_violations"],
                "train_trades": int(train_m["oos_sample_size"]["n_trades"]),
                "train_net_pnl_usd": round(float(train_m["net_pnl_usd"]), 4),
                "validation_trades": int(val_m["oos_sample_size"]["n_trades"]),
                "validation_net_pnl_usd": round(float(val_m["net_pnl_usd"]), 4),
                "sealed_holdout_trades": int(hold_m["oos_sample_size"]["n_trades"]),
                "sealed_holdout_net_pnl_usd": round(float(hold_m["net_pnl_usd"]), 4),
                "oos_combined_trades": int(oos_m["oos_sample_size"]["n_trades"]),
                "oos_combined_clusters": int(oos_m["oos_sample_size"]["n_clusters"]),
                "oos_gross_pnl_usd": round(float(oos_m["gross_pnl_usd"]), 4),
                "oos_net_pnl_usd": round(float(oos_m["net_pnl_usd"]), 4),
                "oos_avg_net_per_trade_usd": round(float(oos_m["avg_net_profit_per_trade_usd"]), 4),
                "oos_win_rate": round(float(oos_m["win_rate"]), 4),
                "oos_profit_per_dollar_day": round(float(oos_m["profit_per_dollar_day"]), 6),
                "oos_sharpe_daily_ann": round(float(oos_m["sharpe_daily_annualized"]), 4),
                "oos_max_drawdown_usd": round(float(oos_m["max_drawdown_usd"]), 4),
                "oos_cvar_95_usd": round(float(oos_m["cvar_95_trade_usd"]), 4),
                "oos_cluster_ci95_usd": oos_m["cluster_bootstrap_95ci"]["total_net_pnl_ci95"],
                "oos_bh_fdr_q_value": entry["multiple_testing"]["bh_fdr_q_value"],
                "oos_dsr": entry["multiple_testing"]["deflated_sharpe_ratio"]["dsr"],
                "cpcv_pbo": entry["cpcv_and_pbo"].get("pbo"),
                "breakeven_extra_slippage_bps": oos_m["cost_sensitivity"]["breakeven_extra_slippage_bps"],
                "brier_skill_vs_market": entry["simple_baselines"]["strategy_vs_market_scoring"]["brier_skill_score"],
                "extra_diagnostics": extra_diag_by_sid.get(sid, {}),
            }
            if sid == "HYP_027_ENSEMBLE_CONVICTION":
                h["measured_evidence"]["ablation_vs_unfiltered"] = ablation_summary
            h["rejection_lessons_and_followup"] = lesson

            full_trades = raw_trades_by_sid[sid]
            oos_cut = train_end_ts + embargo_sec
            oos_trades_raw = [t for t in full_trades if float(t["entry_ts"]) > oos_cut]

            strategy_outputs.append(
                {
                    "strategy_id": sid,
                    "hypothesis_id": h["hypothesis_id"],
                    "code_name": h["code_name"],
                    "title": h["title"],
                    "family": h["family"],
                    "pillar": "Novel Alpha Lab (Agent H)",
                    "mechanism": h["profit_mechanism"],
                    "target_categories": h["target_categories"],
                    "classification": label,
                    "classification_reasons": entry["classification_reasons"],
                    "integrity_violations": entry["integrity_violations"],
                    "num_internal_variants_tested": max(1, len(raw_variants_by_sid[sid])),
                    "purged_split_summary": entry["purged_split_summary"],
                    "multiple_testing": entry["multiple_testing"],
                    "cpcv_and_pbo": entry["cpcv_and_pbo"],
                    "purged_walk_forward": entry["purged_walk_forward"],
                    "regime_and_category_stability": entry["regime_and_category_stability"],
                    "train_metrics": train_m,
                    "validation_metrics": val_m,
                    "sealed_holdout_metrics": hold_m,
                    "combined_oos_metrics": oos_m,
                    "simple_baselines": entry["simple_baselines"],
                    "rejection_lessons_and_followup": lesson,
                    "trades": full_trades,
                    "oos_trades": oos_trades_raw,
                    "variant_trades": raw_variants_by_sid[sid],
                }
            )
        else:
            h["status"] = "Awaiting data"
            h["rejection_lessons_and_followup"] = (
                "Specified & scored in registry; requires specialized archive (e.g., cross-event entity graph, "
                "bar-level CLOB volume tape, or live sub-event state feed) queued for `shadow_runner.py` Phase 2."
            )

    # Optional sync with `@strategy-lab` core strategy results if already written
    synced_core_summaries: List[Dict[str, Any]] = []
    if Path(core_results_path).exists():
        try:
            core_raw = json_loads(Path(core_results_path).read_bytes())
            core_list = core_raw.get("strategies") or core_raw.get("results") or []
            if isinstance(core_list, dict):
                core_list = list(core_list.values())
            for cs in core_list:
                if isinstance(cs, Mapping):
                    val_s = cs.get("val_summary") or {}
                    hold_s = cs.get("oos_summary") or cs.get("oos_metrics") or {}
                    comb_s = cs.get("post_train_oos_summary") or hold_s
                    n_tr = comb_s.get("n_trades") if comb_s else cs.get("oos_trades_count")
                    net_oos = comb_s.get("net_pnl_usd") if comb_s else cs.get("oos_net_pnl_usd")
                    synced_core_summaries.append(
                        {
                            "strategy_id": str(cs.get("strategy_id") or cs.get("id") or ""),
                            "base_strategy_id": str(cs.get("base_strategy_id") or ""),
                            "family": str(cs.get("pillar") or cs.get("family") or "Core Strategy Lab"),
                            "exit_mode": str(cs.get("exit_mode") or cs.get("mechanism") or "HYBRID"),
                            "description": str(cs.get("description") or ""),
                            "status": "Awaiting data" if int(n_tr or 0) == 0 else str(
                                cs.get("classification") or cs.get("status") or "TESTED_BY_STRATEGY_LAB"
                            ),
                            "val_net_pnl_usd": val_s.get("net_pnl_usd"),
                            "sealed_holdout_net_pnl_usd": hold_s.get("net_pnl_usd"),
                            "sealed_holdout_trades": hold_s.get("n_trades"),
                            "oos_net_pnl_usd": net_oos,
                            "oos_trades": n_tr,
                            "oos_clusters": comb_s.get("n_clusters"),
                            "brier_skill_score": comb_s.get("brier_skill_score"),
                        }
                    )
        except Exception:
            pass

    generated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status_counts = collections.Counter(h["status"] for h in base_catalog)

    registry_payload: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at_utc": generated_utc,
        "owner_agent": "novel-alpha (Agent H)",
        "total_novel_hypotheses": len(base_catalog),
        "empirically_tested_novel_count": len(experiment_bundles),
        "total_internal_parameter_trials_m": validation_report["total_swarm_trials_m"],
        "chronological_split_anchors": {
            "train_end_ts": train_end_ts,
            "val_end_ts": val_end_ts,
            "embargo_sec": embargo_sec,
        },
        "status_breakdown": dict(status_counts),
        "hypotheses": base_catalog,
        "synced_core_strategy_lab_entries": synced_core_summaries,
    }

    results_payload: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at_utc": generated_utc,
        "owner_agent": "novel-alpha (Agent H)",
        "dataset_contracts_loaded": len(contracts),
        "chronological_split_anchors": {
            "train_end_ts": train_end_ts,
            "val_end_ts": val_end_ts,
            "embargo_sec": embargo_sec,
        },
        "total_strategies_tested": len(strategy_outputs),
        "total_parameter_trials_m": validation_report["total_swarm_trials_m"],
        "classification_counts": validation_report["classification_counts"],
        "hyp027_conviction_ablation": ablation_summary,
        "combined_novel_portfolio_tiers": validation_report["combined_portfolio_tiers"],
        "strategies": strategy_outputs,
    }
    return registry_payload, results_payload
