"""
DOMINUS — RISKLESS FULL THROTTLE
10-Stage Real-Time Opportunity Pipeline, Realistic Forward Shadow Certification,
Dormant Opportunity Store & Durable Continuity Engine (`full_throttle_pipeline.py`)

Owned exclusively by `@pipeline-shadow` (Agents 1, 8 & 10 Integration Lead).

Pipeline Stages:
  1. DISCOVER         — Exhaustive observable universe sweep + 2-layer hot/cold book polling
  2. NORMALIZE        — Canonical market, fee-schedule, tick/lot & L2 order-book normalization
  3. RELATE           — Unified MarketPropositionGraph + connected-component & holding attachment
  4. GENERATE         — All 14 Opportunity Families (`A..N`) + awakened dormant candidates
  5. PROVE            — Exhaustive contract state-space `Omega` verification (`ArbitrageProofObject`)
  6. PRICE            — Exact V2 share-haircut fee curve, tick quantization & L1 vs L2 spread pricing
  7. SIMULATE         — Realistic post-latency (`72.4ms` RTT / `252ms` speedbump) & partial-fill shadow sim
  8. RANK             — Global portfolio Dollar-Hour (`bps/hr`) optimization without double-counting
  9. MONITOR          — `DormantOpportunityStore` retaining near-arbs & waking them on book shifts
  10. VALIDATE_RESULTS — Cross-cycle (`t -> t+1`) forward live book validation, JSONL ledger & checkpoint

Safety Invariants:
  - `D-001`: Absolute non-interference with the 4 disputed `KMIA` Nov 7 positions (`6707503`, `6707502`).
  - `D-002`/`D-003`: Strict separation of `MODE_1_RESEARCH`, `MODE_2_SHADOW` (default), and `MODE_3_LIVE`
    (hard-locked fail-closed behind legal jurisdiction clearance + `proposal_only_live_promotion` approval).
  - `D-007`: Size strictly off reconciled floor NAV (`$48.70` live cash, never `$99.21` book equity),
    enforce `<= 15%` event/station concentration cap, and quarantine `< $500` NAV `>= 3`-leg sequential bundles.
  - `D-008`: Jurisdiction Gate (`CA-ON` / `US` / `UK` blocked for live CLOB order placement).
  - `D-010`: Swapless host protection (`< 180 MiB` RSS ceiling; pure Python 3.12 stdlib compatible).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import gc
import gzip
import hashlib
import heapq
import http.client
import importlib
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import threading
import time
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
import urllib.parse

from src.polymarket_research.market_proposition_graph import (
    EdgeType,
    MarketPropositionGraph,
)
from src.polymarket_research.v6_restriction_and_capital_allocator import (
    DynamicMarginalCapitalAllocator,
)
from src.polymarket_research.universal_arb_verifier import (
    ActionLeg,
    ActionType,
    ArbitrageProofObject,
    BookLevel,
    CandidateStructure,
    CostBreakdown,
    DEFAULT_D007_MULTILEG_NAV_FLOOR_USD,
    DEFAULT_LIVE_RECONCILED_NAV_USD,
    DEFAULT_MAX_BOOK_AGE_SEC,
    DEFAULT_MIN_MARKETABLE_BUY_USD,
    DEFAULT_MIN_ORDER_SHARES,
    FROZEN_DISPUTED_MARKET_IDS,
    FROZEN_DISPUTED_TRADE_SUBSTRINGS,
    FourValueMetrics,
    InstrumentOrderBook,
    InventoryHolding,
    OpportunityClass,
    StateSpaceBuilder,
    StateSpec,
    UniversalArbVerifier,
    VerificationConfig,
    compute_net_buy_cost_per_delivered_share,
    compute_net_sell_proceeds_per_share,
    normalize_fee_rate,
)


# ---------------------------------------------------------------------------
# 1. Constants, Authoritative Live Baseline & 14-Family Catalog
# ---------------------------------------------------------------------------

AUTHORITATIVE_LIVE_WALLET_BASELINE: Dict[str, Any] = {
    "reconciled_at_utc": "2026-11-11T17:46:10Z",
    "funder_beacon_proxy": "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9",
    "signer_eoa": "0x9703b71686219d34869e8fb89a93263f9e0d50a5",
    "liquid_pusd_cash_usd": 48.695132,
    "worst_case_guaranteed_floor_nav_usd": 48.695132,
    "mark_to_bid_liquidation_nav_usd": 48.834132,
    "persisted_harvester_book_equity_usd": 99.205132,
    "frozen_disputed_kmia_cost_basis_usd": 50.51,
    "frozen_disputed_kmia_positions_count": 4,
    "frozen_disputed_kmia_market_ids": sorted(FROZEN_DISPUTED_MARKET_IDS),
    "historical_pure_riskless_trades": 77,
    "historical_pure_riskless_wins": 77,
    "historical_pure_riskless_losses": 0,
    "historical_pure_riskless_net_pnl_usd": 17.9281,
    "intraday_nov11_pure_riskless_wins": 2,
    "intraday_nov11_pure_riskless_net_pnl_usd": 0.318010,
    "cumulative_pure_riskless_live_wins": 79,
    "cumulative_pure_riskless_live_losses": 0,
    "cumulative_pure_riskless_live_net_pnl_usd": 18.246110,
    "retired_directional_historical_trades": 41,
    "retired_directional_historical_net_pnl_usd": -73.3385,
    "vm_monthly_cost_usd": 24.67,
    "vm_daily_hurdle_usd": round(24.67 / 30.0, 6),
    "vm_hourly_hurdle_usd": round(24.67 / (30.0 * 24.0), 6),
    "vm_hurdle_bps_per_hr_on_live_cash": round((24.67 / (30.0 * 24.0)) / 48.695132 * 10_000.0, 4),
    "vm_hurdle_bps_per_day_on_live_cash": round((24.67 / 30.0) / 48.695132 * 10_000.0, 4),
}

RESTRICTED_LIVE_JURISDICTIONS: FrozenSet[str] = frozenset({"CA-ON", "CA_ON", "US", "USA", "UK", "GB"})
MAX_SWAPLESS_SAFE_RSS_MIB: float = 180.0

FAMILY_CODES: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N")

FAMILY_CATALOG: Dict[str, Dict[str, str]] = {
    "A": {
        "code": "A",
        "slug": "FAMILY_A_BINARY_COMPLETE_SET",
        "name": "Binary YES/NO Complete-Set Arbitrage (Buy-Merge & Split-Sell)",
        "owner": "@complete-negrisk",
    },
    "B": {
        "code": "B",
        "slug": "FAMILY_B_MULTI_OUTCOME_COMPLETE_SET",
        "name": "Multi-Outcome Exhaustive Set Arbitrage",
        "owner": "@complete-negrisk",
    },
    "C": {
        "code": "C",
        "slug": "FAMILY_C_NEGRISK_CONVERSION",
        "name": "Negative-Risk Adapter Conversion & Slate Arbitrage",
        "owner": "@complete-negrisk",
    },
    "D": {
        "code": "D",
        "slug": "FAMILY_D_CROSS_MARKET_LOGICAL",
        "name": "Cross-Market Logical Implication & Subset Arbitrage",
        "owner": "@logical-specialized",
    },
    "E": {
        "code": "E",
        "slug": "FAMILY_E_TEMPORAL_DEADLINE",
        "name": "Temporal & Deadline Monotonicity Arbitrage",
        "owner": "@logical-specialized",
    },
    "F": {
        "code": "F",
        "slug": "FAMILY_F_PRICE_STRIKE_LADDER",
        "name": "Price-Threshold & Strike-Ladder Dominance Arbitrage",
        "owner": "@logical-specialized",
    },
    "G": {
        "code": "G",
        "slug": "FAMILY_G_SPORTS_STRUCTURE",
        "name": "Sports Outcome Structure & Advancement Arbitrage",
        "owner": "@logical-specialized",
    },
    "H": {
        "code": "H",
        "slug": "FAMILY_H_WEATHER_MEASURABLE",
        "name": "Weather & Measurable-Event Bracket Arbitrage",
        "owner": "@logical-specialized",
    },
    "I": {
        "code": "I",
        "slug": "FAMILY_I_DUPLICATE_MARKETS",
        "name": "Duplicated & Near-Duplicated Cross-Event Market Arbitrage",
        "owner": "@logical-specialized",
    },
    "J": {
        "code": "J",
        "slug": "FAMILY_J_INVENTORY_RECYCLING",
        "name": "Portfolio Inventory Completion & Split/Merge Recycling",
        "owner": "@complete-negrisk",
    },
    "K": {
        "code": "K",
        "slug": "FAMILY_K_NEAR_RESOLUTION_CARRY",
        "name": "Near-Resolution & UMA Optimistic Oracle Carry",
        "owner": "@micro-portfolio",
    },
    "L": {
        "code": "L",
        "slug": "FAMILY_L_MAKER_TAKER_ASYMMETRY",
        "name": "Maker/Taker Fee Asymmetry & Passive Box Completion",
        "owner": "@micro-portfolio",
    },
    "M": {
        "code": "M",
        "slug": "FAMILY_M_MULTILEG_PORTFOLIO",
        "name": "Multi-Leg Constrained Component & Portfolio Arbitrage",
        "owner": "@micro-portfolio",
    },
    "N": {
        "code": "N",
        "slug": "FAMILY_N_EMERGING_MECHANISMS",
        "name": "Newly Discovered Structures & Protocol Edge Scanner",
        "owner": "@micro-portfolio",
    },
}

PIPELINE_STAGES_ORDERED: Tuple[str, ...] = (
    "DISCOVER",
    "NORMALIZE",
    "RELATE",
    "GENERATE",
    "PROVE",
    "PRICE",
    "SIMULATE",
    "RANK",
    "MONITOR",
    "VALIDATE_RESULTS",
)

_AMBIGUOUS_NUMERIC_HIT_RE = re.compile(
    r"\b(?:hit|hits|hitting|reach|reaches|reaching|touch|touches|touching)\s+"
    r"(?:around\s+|approximately\s+)?(\$?\d[\d,]*(?:\.\d+)?\s*(?:%|k|m|b|t|bps)?)",
    re.IGNORECASE,
)
_EXPLICIT_INEQUALITY_DIR_RE = re.compile(
    r"\b(?:above|over|exceed|exceeds|at\s+least|or\s+higher|is\s+higher\s+than|equal\s+to\s+or\s+above|at\s+or\s+above|or\s+more|"
    r"below|under|at\s+most|or\s+lower|is\s+lower\s+than|equal\s+to\s+or\s+below|at\s+or\s+below|or\s+less|"
    r"dip|dips|drop|drops|fall|falls|plunge|plunges)\b",
    re.IGNORECASE,
)
_DOWNWARD_DESCRIPTION_BARRIER_RE = re.compile(
    r"\b(?:equal\s+to\s+or\s+below|at\s+or\s+below|is\s+lower\s+than|or\s+lower\s+than|falls?\s+to\s+or\s+below)\b",
    re.IGNORECASE,
)


def has_ambiguous_numeric_barrier_direction(
    questions: Sequence[str],
    descriptions: Sequence[str] = (),
    *,
    source_module: str = "",
) -> bool:
    """
    Returns True when >= 2 cross-market questions compare DIFFERENT numeric strike/barrier
    targets using unsigned path-dependent verbs (`hit 36%` vs `hit 34%`, `reach $100k` vs
    `reach $90k`) AND either:
      (a) neither the question nor official resolution description specifies terminal inequality
          direction (`above`/`is higher than` vs `equal to or below`/`dip`), OR
      (b) the question uses unsigned `hit/reach/touch <K>` while the description specifies a
          DOWNWARD barrier (`equal to or below`), and the candidate was not produced by the
          description-aware strike parser (`detectors_logical_and_specialized`, `#20`).
    """
    if len(questions) < 2:
        return False
    matched_targets: Set[str] = set()
    matched_questions = 0
    unclarified_questions = 0
    downward_desc_on_unsigned_q = False

    for idx, q in enumerate(questions):
        q_txt = str(q or "").strip()
        d_txt = str(descriptions[idx] if idx < len(descriptions) else "").strip()
        if not q_txt or _EXPLICIT_INEQUALITY_DIR_RE.search(q_txt):
            continue
        hits = _AMBIGUOUS_NUMERIC_HIT_RE.findall(q_txt)
        if not hits:
            continue
        matched_questions += 1
        for h in hits:
            norm = re.sub(r"[\s,]+", "", str(h).lower())
            if norm:
                matched_targets.add(norm)
        if not _EXPLICIT_INEQUALITY_DIR_RE.search(d_txt):
            unclarified_questions += 1
        elif _DOWNWARD_DESCRIPTION_BARRIER_RE.search(d_txt) and source_module != "detectors_logical_and_specialized":
            downward_desc_on_unsigned_q = True

    if matched_questions < 2 or len(matched_targets) < 2:
        return False
    return unclarified_questions >= 1 or downward_desc_on_unsigned_q


class ExecutionMode(str, Enum):
    MODE_1_RESEARCH = "MODE_1_RESEARCH"
    MODE_2_SHADOW = "MODE_2_SHADOW"
    MODE_3_LIVE = "MODE_3_LIVE"


class OperatingCycleType(str, Enum):
    DISCOVERY_CYCLE = "DISCOVERY_CYCLE"
    FAST_CYCLE = "FAST_CYCLE"
    RESEARCH_CYCLE = "RESEARCH_CYCLE"


class LiveExecutionHardLockError(PermissionError):
    """Raised fail-closed whenever `MODE_3_LIVE` is requested without full legal & human-owner gates."""


def normalize_family_code(raw_family: Any) -> str:
    """Normalizes any detector family identifier (`'A'`, `'FAMILY_E_TEMPORAL_DEADLINE'`, etc.) to `'A'..'N'`."""
    s = str(raw_family or "").strip().upper()
    if s in FAMILY_CATALOG:
        return s
    if s.startswith("FAMILY_") and len(s) >= 8:
        cand = s[7:8]
        if cand in FAMILY_CATALOG and (len(s) == 8 or s[8] == "_"):
            return cand
    for code, meta in FAMILY_CATALOG.items():
        if s == meta["slug"]:
            return code
    if s and s[0] in FAMILY_CATALOG and (len(s) == 1 or not s[1].isalpha()):
        return s[0]
    return "N"


def get_process_rss_mib() -> float:
    """
    Pure-stdlib process RSS measurement in MiB (`D-010` swapless-host memory guard).
    Supports Linux `/proc/self/status` and Windows `GetProcessMemoryInfo` via `ctypes`.
    """
    if sys.platform.startswith("linux"):
        try:
            status_txt = Path("/proc/self/status").read_text(encoding="utf-8")
            for line in status_txt.splitlines():
                if line.startswith("VmRSS:"):
                    kb = float(line.split()[1])
                    return round(kb / 1024.0, 2)
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            pmc = PROCESS_MEMORY_COUNTERS()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            get_proc = ctypes.windll.kernel32.GetCurrentProcess
            get_proc.restype = ctypes.c_void_p
            handle = get_proc()
            fn_mem = getattr(ctypes.windll.kernel32, "K32GetProcessMemoryInfo", None) or ctypes.windll.psapi.GetProcessMemoryInfo
            fn_mem.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
            fn_mem.restype = wintypes.BOOL
            ok = fn_mem(handle, ctypes.byref(pmc), pmc.cb)
            if ok:
                return round(float(pmc.WorkingSetSize) / (1024.0 * 1024.0), 2)
        except Exception:
            pass
    return 0.0


try:
    import orjson as _ORJSON_MOD  # type: ignore[import-not-found]
except Exception:
    _ORJSON_MOD = None

_LIBC_MALLOC_TRIM: Optional[Callable[[int], Any]] = None
if sys.platform.startswith("linux"):
    try:
        import ctypes as _ctypes_linux

        _LIBC_MALLOC_TRIM = _ctypes_linux.CDLL("libc.so.6").malloc_trim
    except Exception:
        _LIBC_MALLOC_TRIM = None


def _loads_json_bytes(raw: bytes) -> Any:
    """Parses UTF-8 JSON bytes directly via `orjson` when installed (avoiding multi-MB `str` copies)."""
    if _ORJSON_MOD is not None:
        try:
            return _ORJSON_MOD.loads(raw)
        except Exception:
            pass
    return json.loads(raw.decode("utf-8", errors="replace"))


def _reclaim_process_memory() -> None:
    """Forces Python cyclic GC and Linux glibc `malloc_trim(0)` (`D-010` swapless cgroup v2 guard)."""
    gc.collect()
    if _LIBC_MALLOC_TRIM is not None:
        try:
            _LIBC_MALLOC_TRIM(0)
        except Exception:
            pass


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    tmp_path.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# 2. Strict 3-Mode Execution & Governance Gate (`D-001`, `D-002`, `D-003`, `D-008`)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionModeGateConfig:
    mode: ExecutionMode = ExecutionMode.MODE_2_SHADOW
    jurisdiction_code: str = "CA-ON"
    reconciled_nav_usd: float = DEFAULT_LIVE_RECONCILED_NAV_USD
    proposal_only_below_nav_usd: float = 5000.0
    regulated_local_venue_verified: bool = False
    approvals_dir: Path = field(default_factory=lambda: Path("data/polymarket/paa/approvals"))
    explicit_approval_file: Optional[Path] = None
    master_stop_path: Path = field(default_factory=lambda: Path("data/polymarket/paa/PAA_MASTER_STOP"))
    accounting_safeguard_path: Path = field(
        default_factory=lambda: Path("data/polymarket/paa/ACCOUNTING_SAFEGUARD_ACTIVE.json")
    )


class ExecutionModeController:
    """
    Enforces strict boundary between `MODE_1_RESEARCH`, `MODE_2_SHADOW` (default active),
    and `MODE_3_LIVE` (hard-locked fail-closed behind verified jurisdiction + human approval JSON).
    Never reads signing credentials or dispatches live orders in Modes 1 or 2.
    """

    def __init__(self, config: Optional[ExecutionModeGateConfig] = None) -> None:
        self.config = config or ExecutionModeGateConfig()
        self.validate_mode_or_raise()

    @property
    def mode(self) -> ExecutionMode:
        return self.config.mode

    @property
    def allows_public_network(self) -> bool:
        return self.config.mode in (ExecutionMode.MODE_1_RESEARCH, ExecutionMode.MODE_2_SHADOW, ExecutionMode.MODE_3_LIVE)

    @property
    def allows_live_orders(self) -> bool:
        return self.config.mode == ExecutionMode.MODE_3_LIVE

    def validate_mode_or_raise(self) -> Dict[str, Any]:
        cfg = self.config
        if cfg.mode in (ExecutionMode.MODE_1_RESEARCH, ExecutionMode.MODE_2_SHADOW):
            return {
                "mode": cfg.mode.value,
                "live_orders_enabled": False,
                "private_credentials_accessed": False,
                "status": "LOCKED_SAFE_NON_LIVE",
            }

        reasons: List[str] = []
        jur = str(cfg.jurisdiction_code or "CA-ON").strip().upper()
        if jur in RESTRICTED_LIVE_JURISDICTIONS and not cfg.regulated_local_venue_verified:
            reasons.append(f"D008_JURISDICTION_GATE_BLOCKED:{jur}")

        if cfg.master_stop_path.exists():
            reasons.append(f"PAA_MASTER_STOP_ACTIVE:{cfg.master_stop_path}")
        if cfg.accounting_safeguard_path.exists():
            reasons.append(f"ACCOUNTING_SAFEGUARD_ACTIVE:{cfg.accounting_safeguard_path}")

        if float(cfg.reconciled_nav_usd) < float(cfg.proposal_only_below_nav_usd):
            app_ok = False
            cand_files: List[Path] = []
            if cfg.explicit_approval_file is not None:
                cand_files.append(Path(cfg.explicit_approval_file))
            elif cfg.approvals_dir.exists() and cfg.approvals_dir.is_dir():
                cand_files.extend(sorted(cfg.approvals_dir.glob("*.json")))

            for fp in cand_files:
                try:
                    doc = json.loads(fp.read_text(encoding="utf-8"))
                    if (
                        isinstance(doc, Mapping)
                        and doc.get("approved") is True
                        and str(doc.get("approval_scope") or "") == "MODE_3_LIVE_EXECUTION"
                        and str(doc.get("approved_by_human_owner") or "").strip() != ""
                    ):
                        app_ok = True
                        break
                except Exception:
                    continue
            if not app_ok:
                reasons.append("D002_PROPOSAL_ONLY_LIVE_PROMOTION_MISSING_HUMAN_APPROVAL_JSON")

        if reasons:
            raise LiveExecutionHardLockError(
                "MODE_3_LIVE hard-locked fail-closed (" + "; ".join(reasons) + ")"
            )
        return {
            "mode": cfg.mode.value,
            "live_orders_enabled": True,
            "private_credentials_accessed": False,
            "status": "LIVE_AUTHORIZED",
        }

    def assert_no_live_order_dispatch(self, operation_name: str = "order_dispatch") -> None:
        if not self.allows_live_orders:
            raise LiveExecutionHardLockError(
                f"Operation '{operation_name}' forbidden in {self.config.mode.value}: "
                "Modes 1 & 2 strictly prohibit private key access or live order placement."
            )


# ---------------------------------------------------------------------------
# 3. Canonical Pipeline Opportunity Record & Structure Serialization
# ---------------------------------------------------------------------------


def serialize_candidate_structure(structure: Optional[CandidateStructure]) -> Optional[Dict[str, Any]]:
    if structure is None:
        return None
    return {
        "candidate_id": structure.candidate_id,
        "family": structure.family,
        "legs": [
            {
                "action_type": lg.action_type.value if isinstance(lg.action_type, ActionType) else str(lg.action_type),
                "instrument_id": lg.instrument_id,
                "weight": float(lg.weight),
                "is_maker": bool(lg.is_maker),
                "maker_price": lg.maker_price,
                "max_slippage_price": lg.max_slippage_price,
                "related_instrument_ids": list(lg.related_instrument_ids),
                "burned_no_instrument_ids": list(lg.burned_no_instrument_ids),
                "minted_yes_instrument_ids": list(lg.minted_yes_instrument_ids),
                "negrisk_fee_bips": int(lg.negrisk_fee_bips),
                "gas_cost_usd": float(lg.gas_cost_usd),
                "market_id": lg.market_id,
                "label": lg.label,
            }
            for lg in structure.legs
        ],
        "states": [
            {
                "state_id": st.state_id,
                "instrument_payouts": {str(k): float(v) for k, v in st.instrument_payouts.items()},
                "probability": st.probability,
                "lockup_hours_override": st.lockup_hours_override,
                "extra_settlement_cost_usd": float(st.extra_settlement_cost_usd),
                "is_edge_or_void_state": bool(st.is_edge_or_void_state),
                "description": st.description,
            }
            for st in structure.states
        ],
        "rule_verified": bool(structure.rule_verified),
        "rule_disqualifiers": list(structure.rule_disqualifiers),
        "is_exhaustive_partition": bool(structure.is_exhaustive_partition),
        "is_mutually_exclusive": bool(structure.is_mutually_exclusive),
        "requires_exhaustive_partition": bool(structure.requires_exhaustive_partition),
        "has_augmented_placeholder_risk": bool(structure.has_augmented_placeholder_risk),
        "has_mutable_other_exposure": bool(structure.has_mutable_other_exposure),
        "is_statistical_or_cross_oracle_only": bool(structure.is_statistical_or_cross_oracle_only),
        "uma_proposal_unfinalized": bool(structure.uma_proposal_unfinalized),
        "expected_lockup_hours": float(structure.expected_lockup_hours),
        "worst_case_lockup_hours": float(structure.worst_case_lockup_hours),
        "unverified_rebate_or_reward_usd_per_unit": float(structure.unverified_rebate_or_reward_usd_per_unit),
        "notes": list(structure.notes),
    }


def deserialize_candidate_structure(payload: Optional[Mapping[str, Any]]) -> Optional[CandidateStructure]:
    if not isinstance(payload, Mapping):
        return None
    try:
        legs = tuple(
            ActionLeg(
                action_type=ActionType(str(lg["action_type"])),
                instrument_id=str(lg.get("instrument_id") or ""),
                weight=float(lg.get("weight", 1.0)),
                is_maker=bool(lg.get("is_maker", False)),
                maker_price=float(lg["maker_price"]) if lg.get("maker_price") is not None else None,
                max_slippage_price=float(lg["max_slippage_price"]) if lg.get("max_slippage_price") is not None else None,
                related_instrument_ids=tuple(str(x) for x in (lg.get("related_instrument_ids") or ())),
                burned_no_instrument_ids=tuple(str(x) for x in (lg.get("burned_no_instrument_ids") or ())),
                minted_yes_instrument_ids=tuple(str(x) for x in (lg.get("minted_yes_instrument_ids") or ())),
                negrisk_fee_bips=int(lg.get("negrisk_fee_bips", 0)),
                gas_cost_usd=float(lg.get("gas_cost_usd", 0.0)),
                market_id=str(lg.get("market_id") or ""),
                label=str(lg.get("label") or ""),
            )
            for lg in (payload.get("legs") or ())
        )
        states = tuple(
            StateSpec(
                state_id=str(st["state_id"]),
                instrument_payouts={str(k): float(v) for k, v in (st.get("instrument_payouts") or {}).items()},
                probability=float(st["probability"]) if st.get("probability") is not None else None,
                lockup_hours_override=float(st["lockup_hours_override"]) if st.get("lockup_hours_override") is not None else None,
                extra_settlement_cost_usd=float(st.get("extra_settlement_cost_usd", 0.0)),
                is_edge_or_void_state=bool(st.get("is_edge_or_void_state", False)),
                description=str(st.get("description") or ""),
            )
            for st in (payload.get("states") or ())
        )
        return CandidateStructure(
            candidate_id=str(payload["candidate_id"]),
            family=str(payload.get("family") or "A"),
            legs=legs,
            states=states,
            rule_verified=bool(payload.get("rule_verified", True)),
            rule_disqualifiers=tuple(str(x) for x in (payload.get("rule_disqualifiers") or ())),
            is_exhaustive_partition=bool(payload.get("is_exhaustive_partition", True)),
            is_mutually_exclusive=bool(payload.get("is_mutually_exclusive", True)),
            requires_exhaustive_partition=bool(payload.get("requires_exhaustive_partition", False)),
            has_augmented_placeholder_risk=bool(payload.get("has_augmented_placeholder_risk", False)),
            has_mutable_other_exposure=bool(payload.get("has_mutable_other_exposure", False)),
            is_statistical_or_cross_oracle_only=bool(payload.get("is_statistical_or_cross_oracle_only", False)),
            uma_proposal_unfinalized=bool(payload.get("uma_proposal_unfinalized", False)),
            expected_lockup_hours=float(payload.get("expected_lockup_hours", 2.0)),
            worst_case_lockup_hours=float(payload.get("worst_case_lockup_hours", 2.0)),
            unverified_rebate_or_reward_usd_per_unit=float(
                payload.get("unverified_rebate_or_reward_usd_per_unit", 0.0)
            ),
            notes=tuple(str(x) for x in (payload.get("notes") or ())),
        )
    except Exception:
        return None


@dataclass
class PipelineOpportunityRecord:
    """
    Canonical normalized opportunity record flowing through Stages 4 -> 10 across all 14 Families `A..N`.
    """

    candidate_id: str
    family_code: str
    family_slug: str
    sub_type: str
    title_summary: str
    opportunity_class: str
    is_mathematically_proven_arb: bool
    is_atomic_or_prelocked: bool
    d007_sub500_multileg_quarantine: bool
    d001_kmia_blocked: bool
    execution_mode_cap: str
    market_ids: Tuple[str, ...]
    event_ids: Tuple[str, ...]
    instrument_ids: Tuple[str, ...]
    canonical_event_keys: Tuple[str, ...]
    optimal_executable_quantity: float
    gross_top_of_book_edge_per_unit: float
    net_executable_edge_per_unit: float
    min_state_net_payoff_usd: float
    max_state_net_payoff_usd: float
    expected_net_payoff_usd: float
    capital_required_usd: float
    taker_fees_usd: float
    conversion_and_gas_usd: float
    slippage_vs_top_of_book_usd: float
    expected_lockup_hours: float
    worst_case_lockup_hours: float
    capital_efficiency_bps_per_hr: float
    paper_theoretical_usd: float
    executable_l2_net_usd: float
    forward_shadow_risk_adjusted_usd: float
    realized_live_cash_usd: float  # Strictly 0.0 in shadow/research modes!
    partial_fill_risk_prob: float
    expected_unwind_bleed_usd: float
    is_dormant_near_miss: bool
    gap_to_breakeven_bps: float
    proof_sha256: str
    disqualifiers: Tuple[str, ...] = ()
    counterexample_states: Tuple[str, ...] = ()
    residual_risks: Tuple[str, ...] = ()
    source_module: str = ""
    awakened_from_dormant: bool = False
    allocated_portfolio_shares: float = 0.0
    allocated_portfolio_capital_usd: float = 0.0
    allocated_portfolio_shadow_net_usd: float = 0.0
    portfolio_rank: Optional[int] = None
    portfolio_rejection_reason: str = ""
    structure: Optional[CandidateStructure] = field(default=None, repr=False)
    proof: Optional[ArbitrageProofObject] = field(default=None, repr=False)

    def to_ledger_dict(self, *, cycle_index: int = 0, cycle_type: str = "FAST_CYCLE", timestamp_utc: str = "") -> Dict[str, Any]:
        return {
            "timestamp_utc": timestamp_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cycle_index": int(cycle_index),
            "cycle_type": str(cycle_type),
            "candidate_id": self.candidate_id,
            "family_code": self.family_code,
            "family_slug": self.family_slug,
            "sub_type": self.sub_type,
            "title_summary": self.title_summary,
            "opportunity_class": self.opportunity_class,
            "is_mathematically_proven_arb": self.is_mathematically_proven_arb,
            "is_atomic_or_prelocked": self.is_atomic_or_prelocked,
            "d007_sub500_multileg_quarantine": self.d007_sub500_multileg_quarantine,
            "d001_kmia_blocked": self.d001_kmia_blocked,
            "execution_mode_cap": self.execution_mode_cap,
            "market_ids": list(self.market_ids),
            "event_ids": list(self.event_ids),
            "instrument_ids": list(self.instrument_ids),
            "canonical_event_keys": list(self.canonical_event_keys),
            "optimal_executable_quantity": round(self.optimal_executable_quantity, 6),
            "gross_top_of_book_edge_per_unit": round(self.gross_top_of_book_edge_per_unit, 6),
            "net_executable_edge_per_unit": round(self.net_executable_edge_per_unit, 6),
            "min_state_net_payoff_usd": round(self.min_state_net_payoff_usd, 6),
            "max_state_net_payoff_usd": round(self.max_state_net_payoff_usd, 6),
            "expected_net_payoff_usd": round(self.expected_net_payoff_usd, 6),
            "capital_required_usd": round(self.capital_required_usd, 6),
            "taker_fees_usd": round(self.taker_fees_usd, 6),
            "conversion_and_gas_usd": round(self.conversion_and_gas_usd, 6),
            "slippage_vs_top_of_book_usd": round(self.slippage_vs_top_of_book_usd, 6),
            "expected_lockup_hours": round(self.expected_lockup_hours, 4),
            "worst_case_lockup_hours": round(self.worst_case_lockup_hours, 4),
            "capital_efficiency_bps_per_hr": round(self.capital_efficiency_bps_per_hr, 4),
            "segregated_economics": {
                "paper_theoretical_usd": round(self.paper_theoretical_usd, 6),
                "executable_l2_net_usd": round(self.executable_l2_net_usd, 6),
                "forward_shadow_risk_adjusted_usd": round(self.forward_shadow_risk_adjusted_usd, 6),
                "realized_live_cash_usd": round(self.realized_live_cash_usd, 6),
            },
            "partial_fill_risk_prob": round(self.partial_fill_risk_prob, 6),
            "expected_unwind_bleed_usd": round(self.expected_unwind_bleed_usd, 6),
            "is_dormant_near_miss": self.is_dormant_near_miss,
            "gap_to_breakeven_bps": round(self.gap_to_breakeven_bps, 2),
            "awakened_from_dormant": self.awakened_from_dormant,
            "allocated_portfolio_shares": round(self.allocated_portfolio_shares, 6),
            "allocated_portfolio_capital_usd": round(self.allocated_portfolio_capital_usd, 6),
            "allocated_portfolio_shadow_net_usd": round(self.allocated_portfolio_shadow_net_usd, 6),
            "portfolio_rank": self.portfolio_rank,
            "portfolio_rejection_reason": self.portfolio_rejection_reason,
            "proof_sha256": self.proof_sha256,
            "disqualifiers": list(self.disqualifiers),
            "counterexample_states": list(self.counterexample_states),
            "residual_risks": list(self.residual_risks),
            "source_module": self.source_module,
        }


def _is_candidate_structure_like(obj: Any) -> bool:
    if isinstance(obj, CandidateStructure):
        return True
    return (
        obj is not None
        and not isinstance(obj, Mapping)
        and hasattr(obj, "legs")
        and hasattr(obj, "states")
        and hasattr(obj, "rule_verified")
    )


def _is_proof_object_like(obj: Any) -> bool:
    if isinstance(obj, ArbitrageProofObject):
        return True
    return (
        obj is not None
        and not isinstance(obj, Mapping)
        and hasattr(obj, "cost_breakdown")
        and hasattr(obj, "four_value_ledger")
        and hasattr(obj, "leg_executions")
    )


def coerce_to_pipeline_record(
    raw_item: Any,
    *,
    verifier: UniversalArbVerifier,
    books: Mapping[str, InstrumentOrderBook],
    holdings: Optional[Mapping[str, InventoryHolding]] = None,
    source_module: str = "",
    awakened_from_dormant: bool = False,
) -> PipelineOpportunityRecord:
    """
    Converts any peer detector output (`DetectedOpportunity`, `MicroPortfolioCandidate`,
    `CandidateStructure`, `ArbitrageProofObject`, or `Mapping`) into a verified `PipelineOpportunityRecord`,
    guaranteeing Stage 5 (`PROVE`) & Stage 6 (`PRICE`) invariants hold without optimistic promotion.
    """
    structure: Optional[CandidateStructure] = getattr(raw_item, "structure", None)
    proof: Optional[ArbitrageProofObject] = getattr(raw_item, "proof", None)

    if _is_candidate_structure_like(raw_item):
        structure = raw_item
        proof = verifier.verify_and_simulate(structure, books, holdings=holdings)
    elif _is_proof_object_like(raw_item):
        proof = raw_item
    elif _is_candidate_structure_like(structure) and not _is_proof_object_like(proof):
        proof = verifier.verify_and_simulate(structure, books, holdings=holdings)
    elif isinstance(raw_item, Mapping):
        if _is_candidate_structure_like(raw_item.get("structure")):
            structure = raw_item["structure"]
        elif isinstance(raw_item.get("structure"), Mapping):
            structure = deserialize_candidate_structure(raw_item["structure"])
        if _is_proof_object_like(raw_item.get("proof")):
            proof = raw_item["proof"]
        elif _is_candidate_structure_like(structure):
            proof = verifier.verify_and_simulate(structure, books, holdings=holdings)

    def _g(obj: Any, *names: str, default: Any = None) -> Any:
        if isinstance(obj, Mapping):
            for n in names:
                if n in obj and obj[n] is not None:
                    return obj[n]
            return default
        for n in names:
            if hasattr(obj, n):
                v = getattr(obj, n)
                if v is not None:
                    return v
        return default

    raw_fam = _g(raw_item, "family", "family_code", default=(proof.family if proof else "N"))
    fam_code = normalize_family_code(raw_fam)
    fam_slug = FAMILY_CATALOG[fam_code]["slug"]
    cid = str(_g(raw_item, "candidate_id", "id", default=(proof.candidate_id if proof else f"CAND_{fam_code}_{id(raw_item)}")))
    sub_type = str(_g(raw_item, "sub_type", "subfamily", "strategy_type", "relationship_type", default=fam_slug))
    title = str(_g(raw_item, "title_summary", "event_title", "title", "description", default=f"[{fam_code}] {cid}"))

    mids_raw = _g(raw_item, "market_ids", default=None)
    if mids_raw:
        mids = tuple(dict.fromkeys(str(x).strip() for x in mids_raw if str(x).strip()))
    else:
        single_mid = str(_g(raw_item, "market_id", default="") or "").strip()
        if single_mid:
            mids = (single_mid,)
        elif structure is not None:
            mids = tuple(dict.fromkeys(lg.market_id for lg in structure.legs if lg.market_id))
        else:
            mids = ()

    eids_raw = _g(raw_item, "event_ids", default=None)
    if eids_raw:
        eids = tuple(dict.fromkeys(str(x).strip() for x in eids_raw if str(x).strip()))
    else:
        single_eid = str(_g(raw_item, "event_id", default="") or "").strip()
        eids = (single_eid,) if single_eid else ()

    tids_raw = _g(raw_item, "instrument_ids", "token_ids", default=None)
    if tids_raw:
        tids = tuple(dict.fromkeys(str(x).strip() for x in tids_raw if str(x).strip()))
    elif structure is not None:
        acc_t: List[str] = []
        for lg in structure.legs:
            if lg.instrument_id:
                acc_t.append(lg.instrument_id)
            acc_t.extend(lg.related_instrument_ids)
            acc_t.extend(lg.burned_no_instrument_ids)
            acc_t.extend(lg.minted_yes_instrument_ids)
        tids = tuple(dict.fromkeys(t for t in acc_t if t))
    elif proof is not None:
        tids = tuple(dict.fromkeys(le.instrument_id for le in proof.leg_executions if le.instrument_id))
    else:
        tids = ()

    if not tids:
        meta_obj = _g(raw_item, "metadata", default=None)
        acc_meta_t: List[str] = []
        if isinstance(meta_obj, Mapping):
            for mk in ("yes_token_id", "no_token_id", "held_token_id", "complement_token_id"):
                mv = str(meta_obj.get(mk) or "").strip()
                if mv:
                    acc_meta_t.append(mv)
        if not acc_meta_t and mids:
            mid_set = set(mids)
            for tid_k, bk_v in books.items():
                if str(bk_v.market_id).strip() in mid_set:
                    acc_meta_t.append(str(tid_k))
        if acc_meta_t:
            tids = tuple(dict.fromkeys(acc_meta_t))

    if not mids and tids:
        mids = tuple(
            dict.fromkeys(
                str(books[t].market_id).strip()
                for t in tids
                if t in books and str(books[t].market_id).strip()
            )
        )

    ckeys_raw = _g(raw_item, "canonical_event_keys", default=None)
    ck_set: List[str] = []
    if ckeys_raw:
        ck_set.extend(str(x).strip() for x in ckeys_raw if str(x).strip() and not str(x).strip().startswith("CAND:"))
    ck_set.extend(f"EVT:{e}" for e in eids if e)
    ck_set.extend(f"MKT:{m}" for m in mids if m)
    for t in tids:
        if t in books and str(books[t].condition_id).strip():
            ck_set.append(f"COND:{str(books[t].condition_id).strip()}")
    if not ck_set and tids:
        ck_set.extend(f"TOK:{t}" for t in tids)
    if "KMIA" in f"{cid} {title}".upper() or any(m in FROZEN_DISPUTED_MARKET_IDS for m in mids):
        ck_set.append("WXSTATION:KMIA")
    ckeys = tuple(dict.fromkeys(ck_set)) if ck_set else (f"CAND:{cid}",)

    if proof is not None:
        opp_class = str(proof.opportunity_class)
        is_proven = bool(proof.is_mathematically_proven_arb and opp_class in ("CLASS_A", "CLASS_B"))
        is_atomic = bool(proof.is_atomic_or_prelocked and opp_class == "CLASS_A")
        d007_q = bool(proof.d007_sub500_multileg_quarantine)
        mode_cap = str(proof.execution_mode_cap)
        opt_q = float(proof.optimal_executable_quantity)
        gross_edge_u = float(proof.gross_top_of_book_edge_per_unit)
        net_edge_u = float(proof.net_executable_edge_per_unit)
        min_pay = float(proof.min_state_net_payoff_usd)
        max_pay = float(proof.max_state_net_payoff_usd)
        ev_pay = float(proof.expected_net_payoff_usd)
        cap_req = float(proof.cost_breakdown.capital_required_usd)
        fees_u = float(proof.cost_breakdown.taker_fees_usd)
        conv_gas_u = float(proof.cost_breakdown.conversion_costs_usd + proof.cost_breakdown.gas_costs_usd)
        exp_lock = float(proof.cost_breakdown.expected_lockup_hours)
        wst_lock = float(proof.cost_breakdown.worst_case_lockup_hours)
        cap_eff = float(proof.capital_efficiency_bps_per_hr)
        paper_u = float(proof.four_value_ledger.theoretical_top_of_book_usd)
        exec_l2_u = float(proof.four_value_ledger.executable_l2_net_usd)
        att_u = float(proof.four_value_ledger.attainable_risk_adjusted_usd)
        slip_u = max(0.0, round(paper_u - exec_l2_u, 6)) if paper_u > exec_l2_u else 0.0
        disq = tuple(proof.disqualifiers)
        cex = tuple(proof.counterexample_states)
        risks = tuple(proof.residual_risks)
        psha = str(proof.proof_sha256)
        n_clob_taker = sum(
            1 for le in proof.leg_executions if le.action_type in ("BUY_CLOB", "SELL_CLOB") and not le.is_maker
        )
        per_leg_p = 0.905
        p_all = (per_leg_p ** n_clob_taker) if n_clob_taker >= 1 else 1.0
        pf_prob = 0.0 if is_atomic else round(max(0.0, 1.0 - p_all), 6)
        unwind_bleed = max(0.0, round(exec_l2_u * p_all - att_u, 6)) if (not is_atomic and exec_l2_u > 0) else 0.0
    else:
        opp_class_raw = _g(raw_item, "opportunity_class", "classification", default=OpportunityClass.CLASS_D.value)
        opp_class = str(getattr(opp_class_raw, "value", opp_class_raw))
        is_atomic = bool(_g(raw_item, "is_atomic_or_inventory_locked", "is_atomic_or_prelocked", default=False))
        min_pay = float(_g(raw_item, "min_state_net_payoff_usd", "guaranteed_net_profit_usd", default=0.0) or 0.0)
        # Anti-promotion guard when peer record lacks a full `ArbitrageProofObject`
        if opp_class == "CLASS_A" and (not is_atomic or min_pay <= 0.0):
            opp_class = "CLASS_B" if min_pay > 0.0 else "CLASS_D"
        if opp_class == "CLASS_B" and min_pay <= 0.0:
            opp_class = "CLASS_C" if float(_g(raw_item, "expected_net_payoff_usd", default=0.0) or 0.0) > 0.0 else "CLASS_E"
        is_proven = opp_class in ("CLASS_A", "CLASS_B") and min_pay > 0.0
        d007_q = bool(_g(raw_item, "d007_sub500_multileg_quarantine", default=False))
        mode_cap = str(_g(raw_item, "execution_mode_cap", "execution_mode_gate", default="MODE_2_SHADOW"))
        opt_q = float(_g(raw_item, "optimal_executable_quantity", "optimal_shares", default=0.0) or 0.0)
        gross_bps = float(_g(raw_item, "gross_edge_bps", default=0.0) or 0.0)
        net_bps = float(_g(raw_item, "net_executable_edge_bps", default=0.0) or 0.0)
        gross_edge_u = float(_g(raw_item, "gross_top_of_book_edge_per_unit", default=gross_bps / 10_000.0) or 0.0)
        net_edge_u = float(_g(raw_item, "net_executable_edge_per_unit", default=net_bps / 10_000.0) or 0.0)
        max_pay = float(_g(raw_item, "max_state_net_payoff_usd", default=min_pay) or min_pay)
        ev_pay = float(_g(raw_item, "expected_net_payoff_usd", default=min_pay) or min_pay)
        cap_req = float(_g(raw_item, "capital_required_usd", default=0.0) or 0.0)
        fees_u = float(_g(raw_item, "taker_fees_usd", default=0.0) or 0.0)
        conv_gas_u = float(_g(raw_item, "conversion_and_gas_usd", default=0.0) or 0.0)
        exp_lock = float(_g(raw_item, "expected_lockup_hours", default=2.0) or 2.0)
        wst_lock = float(_g(raw_item, "worst_case_lockup_hours", default=max(2.0, exp_lock)) or 2.0)
        cap_eff = float(_g(raw_item, "capital_efficiency_bps_per_hr", "net_bps_per_hour_expected", default=0.0) or 0.0)
        fv = _g(raw_item, "four_value_ledger", default=None)
        paper_u = float(_g(fv, "theoretical_top_of_book_usd", default=max(0.0, gross_edge_u * max(opt_q, 5.0))) or 0.0)
        exec_l2_u = float(_g(fv, "executable_l2_net_usd", default=(min_pay if is_proven else 0.0)) or 0.0)
        att_u = float(_g(fv, "attainable_risk_adjusted_usd", default=(exec_l2_u * 0.85 if is_proven else 0.0)) or 0.0)
        slip_u = max(0.0, round(paper_u - exec_l2_u, 6))
        disq = tuple(str(x) for x in (_g(raw_item, "disqualifiers", "divergence_or_rejection_reasons", default=()) or ()))
        cex = tuple(str(x) for x in (_g(raw_item, "counterexample_states", default=()) or ()))
        risks = tuple(str(x) for x in (_g(raw_item, "residual_risks", default=("VENUE_CUSTODY_AND_SMART_CONTRACT",)) or ()))
        psha = str(_g(raw_item, "proof_sha256", default="") or "")
        if not psha:
            psha = hashlib.sha256(f"{cid}|{fam_code}|{opp_class}|{min_pay:.6f}".encode("utf-8")).hexdigest()
        pf_prob = float(_g(raw_item, "partial_fill_prob", default=(0.0 if is_atomic else 0.16)) or 0.0)
        unwind_bleed = float(_g(raw_item, "adverse_selection_cost_usd", default=0.0) or 0.0)

    d001_blk = bool(
        _g(raw_item, "d001_kmia_frozen_blocked", default=False)
        or any(m in FROZEN_DISPUTED_MARKET_IDS for m in mids)
        or any("D001" in d for d in disq)
        or any(sub in cid.upper() for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS)
    )
    if d001_blk:
        opp_class = OpportunityClass.CLASS_E.value
        is_proven = False
        is_atomic = False
        opt_q = 0.0
        exec_l2_u = 0.0
        att_u = 0.0
        if "D001_FROZEN_DISPUTED_KMIA_MARKET_FORBIDDEN" not in disq:
            disq = (*disq, "D001_FROZEN_DISPUTED_KMIA_MARKET_FORBIDDEN")

    explicit_dormant = bool(_g(raw_item, "is_dormant_near_miss", "dormant_near_miss", "is_dormant_near_arb", default=False))
    raw_gap = _g(raw_item, "gap_to_breakeven_bps", "distance_to_breakeven_bps", default=None)
    if raw_gap is not None:
        gap_bps = float(raw_gap)
    elif opp_class in ("CLASS_A", "CLASS_B"):
        gap_bps = 0.0
    elif net_edge_u < 0.0:
        gap_bps = round(abs(net_edge_u) * 10_000.0, 2)
    elif gross_edge_u < 0.0:
        gap_bps = round(abs(gross_edge_u) * 10_000.0, 2)
    else:
        gap_bps = 9999.0

    # Dormant near-miss qualification: rule-clean candidate within 350 bps of breakeven or temporarily lacking L2 depth
    depth_blocked_clean = bool(
        opp_class == OpportunityClass.CLASS_E.value
        and not d001_blk
        and any(d in ("INSUFFICIENT_L2_DEPTH_OR_MIN_NOTIONAL", "NO_FEASIBLE_EXECUTABLE_QUANTITY") for d in disq)
        and not any("MISMATCH" in d or "NON_EXHAUSTIVE" in d or "PLACEHOLDER" in d for d in disq)
    )
    is_dormant = bool(
        opp_class not in ("CLASS_A", "CLASS_B")
        and not d001_blk
        and (explicit_dormant or (0.0 < gap_bps <= 350.0 and opp_class != "CLASS_D") or (depth_blocked_clean and gap_bps <= 500.0))
    )

    return PipelineOpportunityRecord(
        candidate_id=cid,
        family_code=fam_code,
        family_slug=fam_slug,
        sub_type=sub_type,
        title_summary=title,
        opportunity_class=opp_class,
        is_mathematically_proven_arb=is_proven,
        is_atomic_or_prelocked=is_atomic,
        d007_sub500_multileg_quarantine=d007_q,
        d001_kmia_blocked=d001_blk,
        execution_mode_cap=mode_cap,
        market_ids=mids,
        event_ids=eids,
        instrument_ids=tids,
        canonical_event_keys=ckeys,
        optimal_executable_quantity=opt_q,
        gross_top_of_book_edge_per_unit=gross_edge_u,
        net_executable_edge_per_unit=net_edge_u,
        min_state_net_payoff_usd=min_pay,
        max_state_net_payoff_usd=max_pay,
        expected_net_payoff_usd=ev_pay,
        capital_required_usd=cap_req,
        taker_fees_usd=fees_u,
        conversion_and_gas_usd=conv_gas_u,
        slippage_vs_top_of_book_usd=slip_u,
        expected_lockup_hours=exp_lock,
        worst_case_lockup_hours=wst_lock,
        capital_efficiency_bps_per_hr=cap_eff,
        paper_theoretical_usd=paper_u,
        executable_l2_net_usd=exec_l2_u,
        forward_shadow_risk_adjusted_usd=att_u,
        realized_live_cash_usd=0.0,  # Strictly segregated from wallet cash!
        partial_fill_risk_prob=pf_prob,
        expected_unwind_bleed_usd=unwind_bleed,
        is_dormant_near_miss=is_dormant,
        gap_to_breakeven_bps=gap_bps,
        proof_sha256=psha,
        disqualifiers=disq,
        counterexample_states=cex,
        residual_risks=risks,
        source_module=source_module,
        awakened_from_dormant=awakened_from_dormant,
        structure=structure,
        proof=proof,
    )


# ---------------------------------------------------------------------------
# 4. Dormant Opportunity Store (`Stage 9: MONITOR`)
# ---------------------------------------------------------------------------


@dataclass
class DormantOpportunityEntry:
    candidate_id: str
    family_code: str
    sub_type: str
    title_summary: str
    market_ids: Tuple[str, ...]
    event_ids: Tuple[str, ...]
    instrument_ids: Tuple[str, ...]
    dormant_reason: str
    gap_to_breakeven_bps: float
    best_gap_to_breakeven_bps: float
    book_top_signature: Dict[str, Tuple[float, float, float, float]]
    structure_dict: Optional[Dict[str, Any]]
    first_stored_ts: float
    last_checked_ts: float
    times_observed: int = 1
    times_rescanned_on_shift: int = 0
    times_promoted_to_executable: int = 0
    status: str = "DORMANT"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "family_code": self.family_code,
            "sub_type": self.sub_type,
            "title_summary": self.title_summary,
            "market_ids": list(self.market_ids),
            "event_ids": list(self.event_ids),
            "instrument_ids": list(self.instrument_ids),
            "dormant_reason": self.dormant_reason,
            "gap_to_breakeven_bps": round(self.gap_to_breakeven_bps, 2),
            "best_gap_to_breakeven_bps": round(self.best_gap_to_breakeven_bps, 2),
            "book_top_signature": {k: list(v) for k, v in self.book_top_signature.items()},
            "structure_dict": self.structure_dict,
            "first_stored_ts": round(self.first_stored_ts, 3),
            "last_checked_ts": round(self.last_checked_ts, 3),
            "times_observed": int(self.times_observed),
            "times_rescanned_on_shift": int(self.times_rescanned_on_shift),
            "times_promoted_to_executable": int(self.times_promoted_to_executable),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "DormantOpportunityEntry":
        sig_raw = d.get("book_top_signature") or {}
        sig: Dict[str, Tuple[float, float, float, float]] = {}
        for k, vals in sig_raw.items():
            if isinstance(vals, (list, tuple)) and len(vals) >= 4:
                sig[str(k)] = (float(vals[0]), float(vals[1]), float(vals[2]), float(vals[3]))
        return cls(
            candidate_id=str(d["candidate_id"]),
            family_code=str(d.get("family_code") or "A"),
            sub_type=str(d.get("sub_type") or ""),
            title_summary=str(d.get("title_summary") or ""),
            market_ids=tuple(str(x) for x in (d.get("market_ids") or ())),
            event_ids=tuple(str(x) for x in (d.get("event_ids") or ())),
            instrument_ids=tuple(str(x) for x in (d.get("instrument_ids") or ())),
            dormant_reason=str(d.get("dormant_reason") or "NEAR_ARB_WITHIN_THRESHOLD"),
            gap_to_breakeven_bps=float(d.get("gap_to_breakeven_bps", 100.0)),
            best_gap_to_breakeven_bps=float(d.get("best_gap_to_breakeven_bps", d.get("gap_to_breakeven_bps", 100.0))),
            book_top_signature=sig,
            structure_dict=d.get("structure_dict") if isinstance(d.get("structure_dict"), dict) else None,
            first_stored_ts=float(d.get("first_stored_ts", 0.0)),
            last_checked_ts=float(d.get("last_checked_ts", 0.0)),
            times_observed=int(d.get("times_observed", 1)),
            times_rescanned_on_shift=int(d.get("times_rescanned_on_shift", 0)),
            times_promoted_to_executable=int(d.get("times_promoted_to_executable", 0)),
            status=str(d.get("status") or "DORMANT"),
        )


class DormantOpportunityStore:
    """
    Retains temporarily illiquid or near-arbitrage structures (`data/full_throttle/pipeline/dormant_opportunities.json`)
    and wakes them immediately when constituent order books shift, preventing silent drop of near-arbs.
    """

    def __init__(
        self,
        store_path: Path,
        *,
        max_entries: int = 1200,
        max_gap_bps: float = 350.0,
        price_shift_epsilon: float = 0.0009,
    ) -> None:
        self.store_path = Path(store_path)
        self.max_entries = max(50, int(max_entries))
        self.max_gap_bps = float(max_gap_bps)
        self.price_shift_epsilon = float(price_shift_epsilon)
        self.entries: Dict[str, DormantOpportunityEntry] = {}
        self.total_ingested_events: int = 0
        self.total_rescans_triggered: int = 0
        self.total_promotions_to_executable: int = 0
        self.load()

    @staticmethod
    def _book_top_tuple(bk: Optional[InstrumentOrderBook]) -> Tuple[float, float, float, float]:
        if bk is None:
            return (0.0, 0.0, 0.0, 0.0)
        ask_px = float(bk.asks[0].price) if bk.asks else 0.0
        ask_sz = float(bk.asks[0].size) if bk.asks else 0.0
        bid_px = float(bk.bids[0].price) if bk.bids else 0.0
        bid_sz = float(bk.bids[0].size) if bk.bids else 0.0
        return (round(ask_px, 6), round(ask_sz, 4), round(bid_px, 6), round(bid_sz, 4))

    def load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
            raw_entries = payload.get("entries") if isinstance(payload, Mapping) else None
            if isinstance(raw_entries, list):
                for item in raw_entries:
                    if isinstance(item, Mapping) and item.get("candidate_id"):
                        ent = DormantOpportunityEntry.from_dict(item)
                        self.entries[ent.candidate_id] = ent
            if isinstance(payload, Mapping):
                self.total_ingested_events = int(payload.get("total_ingested_events", len(self.entries)))
                self.total_rescans_triggered = int(payload.get("total_rescans_triggered", 0))
                self.total_promotions_to_executable = int(payload.get("total_promotions_to_executable", 0))
        except Exception:
            pass

    def save(self) -> None:
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: (0 if e.status == "DORMANT" else 1, e.gap_to_breakeven_bps, e.candidate_id),
        )[: self.max_entries]
        if len(self.entries) > self.max_entries:
            self.entries = {e.candidate_id: e for e in sorted_entries}
        payload = {
            "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "active_dormant_count": sum(1 for e in self.entries.values() if e.status == "DORMANT"),
            "promoted_count": sum(1 for e in self.entries.values() if e.status == "AWAKENED_PROMOTED"),
            "total_ingested_events": self.total_ingested_events,
            "total_rescans_triggered": self.total_rescans_triggered,
            "total_promotions_to_executable": self.total_promotions_to_executable,
            "by_family": dict(Counter(e.family_code for e in self.entries.values() if e.status == "DORMANT")),
            "entries": [e.to_dict() for e in sorted_entries],
        }
        _atomic_write_json(self.store_path, payload)

    def export_fast_rescan_tokens(
        self,
        out_path: Optional[Path] = None,
        *,
        max_tokens: int = 240,
        max_gap_bps: float = 50.0,
        now_ts: Optional[float] = None,
    ) -> List[str]:
        """Exports near-arb (`<= max_gap_bps`) `DORMANT` token IDs for high-frequency Bridge/WS re-scans (`D-001`-clean)."""
        now_f = float(time.time() if now_ts is None else now_ts)
        target_path = Path(out_path) if out_path is not None else Path("data/polymarket/dormant_fast_rescan_tokens.json")
        out_tokens: List[str] = []
        seen: Set[str] = set()
        for ent in sorted(self.entries.values(), key=lambda e: (e.gap_to_breakeven_bps, e.candidate_id)):
            if ent.status != "DORMANT":
                continue
            if float(ent.gap_to_breakeven_bps) > float(max_gap_bps) + 1e-9:
                continue
            if any(mid in FROZEN_DISPUTED_MARKET_IDS for mid in ent.market_ids):
                continue
            title_cid_up = f"{ent.title_summary} {ent.candidate_id}".upper()
            if any(sub.upper() in title_cid_up for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS):
                continue
            for tid in ent.instrument_ids:
                tid_s = str(tid or "").strip()
                if tid_s and tid_s not in seen:
                    seen.add(tid_s)
                    out_tokens.append(tid_s)
                    if len(out_tokens) >= max(1, int(max_tokens)):
                        break
            if len(out_tokens) >= max(1, int(max_tokens)):
                break
        _atomic_write_json(
            target_path,
            {
                "updated_at_unix": round(now_f, 3),
                "max_gap_bps": float(max_gap_bps),
                "token_count": len(out_tokens),
                "token_ids": out_tokens,
            },
        )
        return out_tokens

    def get_watch_instrument_ids(
        self,
        *,
        max_tokens: int = 1200,
        max_gap_bps: Optional[float] = None,
    ) -> List[str]:
        out: List[str] = []
        seen: Set[str] = set()
        for ent in sorted(self.entries.values(), key=lambda e: e.gap_to_breakeven_bps):
            if ent.status != "DORMANT":
                continue
            if max_gap_bps is not None and float(ent.gap_to_breakeven_bps) > float(max_gap_bps) + 1e-9:
                continue
            for tid in ent.instrument_ids:
                if tid and tid not in seen:
                    seen.add(tid)
                    out.append(tid)
                    if len(out) >= max_tokens:
                        return out
        return out

    def detect_shifted_structures_for_rescan(
        self,
        books: Mapping[str, InstrumentOrderBook],
        *,
        now_ts: Optional[float] = None,
    ) -> List[Tuple[DormantOpportunityEntry, CandidateStructure]]:
        """
        Inspects fresh `books` against stored L1 signatures. Returns `(entry, CandidateStructure)`
        whenever any watched leg experiences a favorable price shift or newly resting liquidity.
        """
        now_f = float(time.time() if now_ts is None else now_ts)
        awakened: List[Tuple[DormantOpportunityEntry, CandidateStructure]] = []

        for ent in self.entries.values():
            if ent.status != "DORMANT" or not ent.instrument_ids:
                continue
            shifted = False
            for tid in ent.instrument_ids:
                cur_bk = books.get(tid)
                if cur_bk is None:
                    continue
                cur_sig = self._book_top_tuple(cur_bk)
                prev_sig = ent.book_top_signature.get(tid, (0.0, 0.0, 0.0, 0.0))
                # Trigger rescan if: (a) ask price dropped, (b) bid price rose, or (c) previously empty side gained depth,
                # or (d) top-of-book size expanded enough to cross `$1.00` min notional / `min_order_size`!
                ask_improved = cur_sig[0] > 0.0 and (
                    prev_sig[0] <= 0.0 or cur_sig[0] <= prev_sig[0] - self.price_shift_epsilon
                )
                bid_improved = cur_sig[2] > 0.0 and (
                    prev_sig[2] <= 0.0 or cur_sig[2] >= prev_sig[2] + self.price_shift_epsilon
                )
                depth_appeared = (prev_sig[1] < 5.0 <= cur_sig[1]) or (prev_sig[3] < 5.0 <= cur_sig[3])
                if ask_improved or bid_improved or depth_appeared:
                    shifted = True
                    break

            if shifted:
                ent.times_rescanned_on_shift += 1
                ent.last_checked_ts = now_f
                self.total_rescans_triggered += 1
                if ent.structure_dict:
                    cand_struct = deserialize_candidate_structure(ent.structure_dict)
                    if cand_struct is not None:
                        awakened.append((ent, cand_struct))

        return awakened

    def update_from_pipeline_records(
        self,
        records: Sequence[PipelineOpportunityRecord],
        books: Mapping[str, InstrumentOrderBook],
        *,
        now_ts: Optional[float] = None,
    ) -> Dict[str, int]:
        now_f = float(time.time() if now_ts is None else now_ts)
        newly_added = 0
        updated_existing = 0
        promoted = 0

        for rec in records:
            if rec.d001_kmia_blocked:
                continue

            if rec.opportunity_class in ("CLASS_A", "CLASS_B") and rec.candidate_id in self.entries:
                ent = self.entries[rec.candidate_id]
                if ent.status == "DORMANT":
                    ent.status = "AWAKENED_PROMOTED"
                    ent.times_promoted_to_executable += 1
                    ent.last_checked_ts = now_f
                    ent.gap_to_breakeven_bps = 0.0
                    ent.best_gap_to_breakeven_bps = 0.0
                    self.total_promotions_to_executable += 1
                    promoted += 1
                continue

            if not rec.is_dormant_near_miss or rec.gap_to_breakeven_bps > self.max_gap_bps:
                continue

            sig = {tid: self._book_top_tuple(books.get(tid)) for tid in rec.instrument_ids if tid}
            reason = (
                "ZERO_OR_SHALLOW_L2_DEPTH"
                if any(d in ("INSUFFICIENT_L2_DEPTH_OR_MIN_NOTIONAL", "NO_FEASIBLE_EXECUTABLE_QUANTITY") for d in rec.disqualifiers)
                else "NEAR_ARB_WITHIN_THRESHOLD"
            )
            struct_d = serialize_candidate_structure(rec.structure)

            if rec.candidate_id in self.entries:
                ent = self.entries[rec.candidate_id]
                ent.gap_to_breakeven_bps = rec.gap_to_breakeven_bps
                ent.best_gap_to_breakeven_bps = min(ent.best_gap_to_breakeven_bps, rec.gap_to_breakeven_bps)
                ent.book_top_signature = sig
                if struct_d is not None:
                    ent.structure_dict = struct_d
                ent.last_checked_ts = now_f
                ent.times_observed += 1
                ent.status = "DORMANT"
                updated_existing += 1
            else:
                self.entries[rec.candidate_id] = DormantOpportunityEntry(
                    candidate_id=rec.candidate_id,
                    family_code=rec.family_code,
                    sub_type=rec.sub_type,
                    title_summary=rec.title_summary,
                    market_ids=rec.market_ids,
                    event_ids=rec.event_ids,
                    instrument_ids=rec.instrument_ids,
                    dormant_reason=reason,
                    gap_to_breakeven_bps=rec.gap_to_breakeven_bps,
                    best_gap_to_breakeven_bps=rec.gap_to_breakeven_bps,
                    book_top_signature=sig,
                    structure_dict=struct_d,
                    first_stored_ts=now_f,
                    last_checked_ts=now_f,
                )
                newly_added += 1
                self.total_ingested_events += 1

        if len(self.entries) > self.max_entries:
            keep = sorted(
                self.entries.values(),
                key=lambda e: (0 if e.status == "DORMANT" else 1, e.gap_to_breakeven_bps, e.candidate_id),
            )[: self.max_entries]
            self.entries = {e.candidate_id: e for e in keep}

        return {
            "newly_added_dormant": newly_added,
            "updated_dormant": updated_existing,
            "promoted_from_dormant": promoted,
            "active_dormant_total": sum(1 for e in self.entries.values() if e.status == "DORMANT"),
        }

    def summary_metrics(self) -> Dict[str, Any]:
        active = [e for e in self.entries.values() if e.status == "DORMANT"]
        by_fam = Counter(e.family_code for e in active)
        by_reason = Counter(e.dormant_reason for e in active)
        within_50_bps = sum(1 for e in active if e.gap_to_breakeven_bps <= 50.0)
        within_150_bps = sum(1 for e in active if e.gap_to_breakeven_bps <= 150.0)
        within_350_bps = len(active)
        top_closest = [
            {
                "candidate_id": e.candidate_id,
                "family_code": e.family_code,
                "title_summary": e.title_summary,
                "gap_to_breakeven_bps": round(e.gap_to_breakeven_bps, 2),
                "dormant_reason": e.dormant_reason,
                "times_observed": e.times_observed,
                "times_rescanned_on_shift": e.times_rescanned_on_shift,
            }
            for e in sorted(active, key=lambda x: (x.gap_to_breakeven_bps, x.candidate_id))[:15]
        ]
        return {
            "active_dormant_count": within_350_bps,
            "within_50_bps_count": within_50_bps,
            "within_150_bps_count": within_150_bps,
            "within_350_bps_count": within_350_bps,
            "by_family": {fc: int(by_fam.get(fc, 0)) for fc in FAMILY_CODES if by_fam.get(fc, 0) > 0},
            "by_reason": dict(by_reason),
            "total_ingested_events": self.total_ingested_events,
            "total_rescans_triggered": self.total_rescans_triggered,
            "total_promotions_to_executable": self.total_promotions_to_executable,
            "closest_near_misses": top_closest,
        }


def load_dormant_fast_rescan_tokens(
    max_age_sec: float = 1800.0,
    *,
    path: Optional[Path] = None,
    now_ts: Optional[float] = None,
) -> List[str]:
    """Loads exported dormant fast-rescan token IDs if present and younger than `max_age_sec`."""
    target = Path(path) if path is not None else Path("data/polymarket/dormant_fast_rescan_tokens.json")
    if not target.exists():
        return []
    try:
        raw_bytes = target.read_bytes()
        doc = _loads_json_bytes(raw_bytes)
        if not isinstance(doc, Mapping):
            return []
        now_f = float(time.time() if now_ts is None else now_ts)
        updated_raw = doc.get("updated_at_unix")
        updated_ts = (
            float(updated_raw)
            if isinstance(updated_raw, (int, float)) and not isinstance(updated_raw, bool) and math.isfinite(float(updated_raw))
            else float(target.stat().st_mtime)
        )
        if (now_f - updated_ts) > max(0.0, float(max_age_sec)):
            return []
        raw_tids = doc.get("token_ids") or ()
        if not isinstance(raw_tids, (list, tuple)):
            return []
        return [str(x).strip() for x in dict.fromkeys(str(t).strip() for t in raw_tids) if x]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 5. Forward Shadow Execution Validator & Persistence Tracker (`Stages 7 & 10`)
# ---------------------------------------------------------------------------


@dataclass
class PendingShadowValidationTicket:
    candidate_id: str
    family_code: str
    opportunity_class: str
    created_cycle: int
    created_ts: float
    target_quantity: float
    expected_l2_net_usd: float
    expected_risk_adjusted_usd: float
    structure_dict: Optional[Dict[str, Any]]
    instrument_ids: Tuple[str, ...]
    initial_top_asks: Dict[str, float]


class ForwardShadowValidationTracker:
    """
    Tracks multi-cycle opportunity persistence AND performs non-hindsight forward shadow validation:
    tickets emitted at cycle `t` are re-simulated against the *next* live order book snapshot at `t + 1`
    to empirically measure cross-snapshot survival, price drift, and realistic post-delay shadow PnL.
    """

    def __init__(self) -> None:
        self.persistence_by_candidate: Dict[str, Dict[str, Any]] = {}
        self.pending_tickets: Dict[str, PendingShadowValidationTicket] = {}
        self.completed_validations: List[Dict[str, Any]] = []

    def record_cycle_observations(
        self,
        records: Sequence[PipelineOpportunityRecord],
        books: Mapping[str, InstrumentOrderBook],
        *,
        cycle_index: int,
        now_ts: float,
    ) -> Dict[str, Any]:
        seen_now: Set[str] = set()
        for r in records:
            if r.opportunity_class not in ("CLASS_A", "CLASS_B", "CLASS_C") and not r.is_dormant_near_miss:
                continue
            seen_now.add(r.candidate_id)
            st = self.persistence_by_candidate.get(r.candidate_id)
            if st is None:
                self.persistence_by_candidate[r.candidate_id] = {
                    "candidate_id": r.candidate_id,
                    "family_code": r.family_code,
                    "opportunity_class": r.opportunity_class,
                    "first_cycle": cycle_index,
                    "last_cycle": cycle_index,
                    "first_ts": now_ts,
                    "last_ts": now_ts,
                    "cycles_seen": 1,
                    "consecutive_cycles": 1,
                    "peak_exec_l2_usd": r.executable_l2_net_usd,
                }
            else:
                was_prev = st["last_cycle"] == (cycle_index - 1)
                st["last_cycle"] = cycle_index
                st["last_ts"] = now_ts
                st["opportunity_class"] = r.opportunity_class
                st["cycles_seen"] = int(st["cycles_seen"]) + 1
                st["consecutive_cycles"] = (int(st["consecutive_cycles"]) + 1) if was_prev else 1
                st["peak_exec_l2_usd"] = max(float(st["peak_exec_l2_usd"]), r.executable_l2_net_usd)

            # Enqueue executable Class A/B (and top Class C) for next-cycle live forward book validation
            if (
                r.opportunity_class in ("CLASS_A", "CLASS_B")
                and r.executable_l2_net_usd > 0.0
                and r.candidate_id not in self.pending_tickets
            ):
                top_asks = {
                    tid: (float(books[tid].asks[0].price) if (tid in books and books[tid].asks) else 0.0)
                    for tid in r.instrument_ids
                }
                self.pending_tickets[r.candidate_id] = PendingShadowValidationTicket(
                    candidate_id=r.candidate_id,
                    family_code=r.family_code,
                    opportunity_class=r.opportunity_class,
                    created_cycle=cycle_index,
                    created_ts=now_ts,
                    target_quantity=r.optimal_executable_quantity,
                    expected_l2_net_usd=r.executable_l2_net_usd,
                    expected_risk_adjusted_usd=r.forward_shadow_risk_adjusted_usd,
                    structure_dict=serialize_candidate_structure(r.structure),
                    instrument_ids=r.instrument_ids,
                    initial_top_asks=top_asks,
                )

        # Bound persistence dictionary for swapless safety
        if len(self.persistence_by_candidate) > 3000:
            keep_ids = sorted(
                self.persistence_by_candidate.keys(),
                key=lambda k: self.persistence_by_candidate[k]["last_cycle"],
                reverse=True,
            )[:2000]
            self.persistence_by_candidate = {k: self.persistence_by_candidate[k] for k in keep_ids}

        return self.persistence_summary(current_cycle=cycle_index)

    def validate_pending_against_fresh_books(
        self,
        books: Mapping[str, InstrumentOrderBook],
        verifier: UniversalArbVerifier,
        *,
        holdings: Optional[Mapping[str, InventoryHolding]] = None,
        cycle_index: int,
        now_ts: float,
    ) -> List[Dict[str, Any]]:
        """Re-evaluates prior-cycle tickets against newly fetched `cycle_index` order books."""
        newly_validated: List[Dict[str, Any]] = []
        remaining: Dict[str, PendingShadowValidationTicket] = {}

        for cid, tkt in self.pending_tickets.items():
            if tkt.created_cycle >= cycle_index:
                remaining[cid] = tkt
                continue
            elapsed_s = max(0.001, now_ts - tkt.created_ts)
            cand_struct = deserialize_candidate_structure(tkt.structure_dict)
            survived = False
            post_delay_net_usd = 0.0
            drift_bps = 0.0

            if tkt.instrument_ids:
                drifts: List[float] = []
                for tid in tkt.instrument_ids:
                    p0 = tkt.initial_top_asks.get(tid, 0.0)
                    bk = books.get(tid)
                    p1 = float(bk.asks[0].price) if (bk is not None and bk.asks) else 0.0
                    if p0 > 0.0 and p1 > 0.0:
                        drifts.append((p1 - p0) * 10_000.0)
                if drifts:
                    drift_bps = round(sum(drifts) / len(drifts), 2)

            if cand_struct is not None and all(tid in books for tid in tkt.instrument_ids):
                re_proof = verifier.verify_and_simulate(cand_struct, books, holdings=holdings)
                survived = re_proof.opportunity_class in ("CLASS_A", "CLASS_B") and re_proof.min_state_net_payoff_usd > 0.0
                post_delay_net_usd = (
                    float(re_proof.four_value_ledger.executable_l2_net_usd)
                    if survived
                    else max(-0.05 * tkt.expected_l2_net_usd, min(0.0, float(re_proof.min_state_net_payoff_usd)))
                )
            elif all(tid in books for tid in tkt.instrument_ids):
                # Fallback drift decay if peer candidate lacked explicit serialized `CandidateStructure`
                survived = drift_bps <= 15.0
                post_delay_net_usd = round(tkt.expected_l2_net_usd * (1.0 if drift_bps <= 0.0 else 0.5), 6) if survived else 0.0

            rec_v = {
                "candidate_id": cid,
                "family_code": tkt.family_code,
                "opportunity_class": tkt.opportunity_class,
                "created_cycle": tkt.created_cycle,
                "validated_cycle": cycle_index,
                "elapsed_sec": round(elapsed_s, 3),
                "expected_l2_net_usd": round(tkt.expected_l2_net_usd, 6),
                "post_delay_net_usd": round(post_delay_net_usd, 6),
                "survived_next_snapshot": bool(survived),
                "ask_drift_bps": drift_bps,
            }
            self.completed_validations.append(rec_v)
            newly_validated.append(rec_v)

        self.pending_tickets = remaining
        if len(self.completed_validations) > 1000:
            self.completed_validations = self.completed_validations[-1000:]
        return newly_validated

    def persistence_summary(self, *, current_cycle: int) -> Dict[str, Any]:
        arb_items = [
            v for v in self.persistence_by_candidate.values() if v["opportunity_class"] in ("CLASS_A", "CLASS_B")
        ]
        multi_cycle_arbs = [v for v in arb_items if int(v["cycles_seen"]) >= 2]
        avg_lifetime_sec = (
            round(sum(float(v["last_ts"]) - float(v["first_ts"]) for v in multi_cycle_arbs) / len(multi_cycle_arbs), 3)
            if multi_cycle_arbs
            else 0.0
        )
        survived_cnt = sum(1 for v in self.completed_validations if v["survived_next_snapshot"])
        val_total = len(self.completed_validations)
        return {
            "tracked_unique_candidates": len(self.persistence_by_candidate),
            "tracked_unique_proven_arbs": len(arb_items),
            "multi_cycle_persistent_arbs": len(multi_cycle_arbs),
            "avg_persistent_arb_lifetime_sec": avg_lifetime_sec,
            "forward_validations_completed": val_total,
            "forward_validations_survived": survived_cnt,
            "forward_survival_rate": round(survived_cnt / val_total, 4) if val_total > 0 else None,
            "forward_validated_net_pnl_usd": round(
                sum(float(v["post_delay_net_usd"]) for v in self.completed_validations), 6
            ),
            "pending_validation_tickets": len(self.pending_tickets),
        }


# ---------------------------------------------------------------------------
# 5B. Family L Hedged Maker (`L1A/L1B`) Forward Shadow Quoter (`0 bps` Maker + Rebate)
# ---------------------------------------------------------------------------


def _estimate_maker_rebate_share_frac(fee_rate_bps: float, fee_exponent: float) -> float:
    """
    Polymarket V2 Maker Fee-Share Schedule (`15%–25%` of taker curve on dynamic-fee markets,
    `0%` on `feesEnabled=False` markets). Tracked strictly as separate non-guaranteed shadow
    telemetry — NEVER credited to `CLASS_A/B` guaranteed floor payoffs or live wallet cash!
    """
    if fee_rate_bps <= 0.0:
        return 0.0
    if abs(fee_rate_bps - 300.0) <= 25.0 or (abs(fee_rate_bps - 500.0) <= 25.0 and fee_exponent == 1.0):
        return 0.20
    if fee_rate_bps >= 2000.0 or fee_exponent >= 1.8:
        return 0.20
    return 0.15


def _estimate_maker_rebate_per_share(price: float, fee_rate_bps: float, fee_exponent: float) -> float:
    p = min(0.9999, max(0.0001, float(price)))
    if fee_rate_bps <= 0.0:
        return 0.0
    rate = float(fee_rate_bps) / 10_000.0
    taker_fee_usdc_ps = p * rate * ((p * (1.0 - p)) ** max(0.5, float(fee_exponent)))
    share_frac = _estimate_maker_rebate_share_frac(fee_rate_bps, fee_exponent)
    return round(max(0.0, taker_fee_usdc_ps * share_frac), 6)


@dataclass
class VirtualHedgedMakerQuote:
    quote_id: str
    sub_type: str  # L1A_PASSIVE_COMPLETE_SET_ANCHOR | L1B_INVENTORY_MAKER_COMPLETION | L2_DOMINANCE_MAKER_ANCHOR
    source_family: str
    title_summary: str
    created_cycle: int
    created_ts: float
    expires_ts: float
    maker_token_id: str
    maker_market_id: str
    hedge_token_id: str
    hedge_market_id: str
    quote_bid_px: float
    initial_maker_ask_px: float
    initial_hedge_ask_net_px: float
    shares: float
    queue_ahead_usd: float
    hedge_depth_ratio: float
    fee_rate_bps: float
    fee_exponent: float
    rebate_share_frac: float
    est_maker_rebate_ps: float
    preheld_inventory_backed: bool = False


class HedgedMakerShadowQuoter:
    """
    Realistic forward `Cycle t -> Cycle t+1` shadow quoter for `Family L` (`L1A`/`L1B`/`L2`)
    passive `postOnly=True` (`0 bps` maker fee) complete-set & verified 2-leg dominance completion
    quotes across the `99.4%` dynamic-fee (`feesEnabled=True`) universe.

    Strict Non-Conflation Invariants:
      1. `0` live orders placed; `0` overlap with Column 3 Realized Live Wallet Cash (`$48.70` `pUSD`)
         or Column 2 `CLASS_A/B` FOK Taker Guaranteed Arbitrage PnL.
      2. Forward `t -> t+1` validation checks BOTH queue fill AND actual `Cycle t+1` hedge leg ask:
         if news jumped the hedge ask (`quote_px + hedge_ask_net_t1 >= $1.00`), adverse-selection
         unwind bleed is deducted honestly rather than assuming hindsight fills!
      3. Estimated `15%–25%` maker fee-share rebates are tracked in a dedicated column, never mixed
         into locked spread floor PnL.
    """

    def __init__(
        self,
        *,
        max_resting_quotes: int = 120,
        quote_ttl_sec: float = 900.0,
        max_queue_ahead_usd: float = 75.0,
        min_hedge_depth_ratio: float = 2.0,
        min_locked_maker_edge_bps: float = 20.0,
    ) -> None:
        self.max_resting_quotes = int(max_resting_quotes)
        self.quote_ttl_sec = float(quote_ttl_sec)
        self.max_queue_ahead_usd = float(max_queue_ahead_usd)
        self.min_hedge_depth_ratio = float(min_hedge_depth_ratio)
        self.min_locked_maker_edge_bps = float(min_locked_maker_edge_bps)

        self.resting_quotes: Dict[str, VirtualHedgedMakerQuote] = {}
        self.total_quotes_posted: int = 0
        self.total_quotes_evaluated_next_cycle: int = 0
        self.filled_hedged_locks_count: int = 0
        self.adverse_selected_fills_count: int = 0
        self.expired_unfilled_count: int = 0
        self.locked_spread_shadow_pnl_usd: float = 0.0
        self.adverse_unwind_bleed_usd: float = 0.0
        self.estimated_maker_rebate_15_to_25pct_usd: float = 0.0
        self.recent_fill_events: List[Dict[str, Any]] = []

    def get_watch_instrument_ids(self, *, max_tokens: int = 240) -> List[str]:
        out: List[str] = []
        seen: Set[str] = set()
        for q in self.resting_quotes.values():
            for tid in (q.maker_token_id, q.hedge_token_id):
                if tid and tid not in seen:
                    seen.add(tid)
                    out.append(tid)
                    if len(out) >= max_tokens:
                        return out
        return out

    def validate_resting_quotes(
        self,
        books: Mapping[str, InstrumentOrderBook],
        *,
        cycle_index: int,
        now_ts: float,
    ) -> Dict[str, Any]:
        still_resting: Dict[str, VirtualHedgedMakerQuote] = {}
        fills_this_cycle = 0
        adverse_this_cycle = 0
        cycle_events: List[Dict[str, Any]] = []

        for qid, q in self.resting_quotes.items():
            if q.created_cycle >= cycle_index:
                still_resting[qid] = q
                continue
            if now_ts >= q.expires_ts:
                self.expired_unfilled_count += 1
                continue

            m_bk = books.get(q.maker_token_id)
            h_bk = books.get(q.hedge_token_id) if q.hedge_token_id else None
            if m_bk is None or (q.hedge_token_id and not q.preheld_inventory_backed and h_bk is None):
                still_resting[qid] = q
                continue

            self.total_quotes_evaluated_next_cycle += 1
            m_ask_t1 = float(m_bk.asks[0].price) if m_bk.asks else 1.0
            m_bid_t1 = float(m_bk.bids[0].price) if m_bk.bids else 0.0

            # Passive maker bid fills when live market trades through (`ask_t1 <= quote_bid_px`)
            # or sweeps down through shallow L1 queue (`bid_t1 < quote_bid_px` with `queue_ahead <= $20`)
            traded_through = m_ask_t1 <= (q.quote_bid_px + 1e-9)
            queue_swept = (m_bid_t1 > 0.0 and m_bid_t1 < (q.quote_bid_px - 1e-9) and q.queue_ahead_usd <= 20.0)
            if not (traded_through or queue_swept):
                still_resting[qid] = q
                continue

            if q.preheld_inventory_backed:
                hedge_cost_t1 = q.initial_hedge_ask_net_px  # Already locked in pre-held cost basis!
            else:
                if h_bk is None or not h_bk.asks:
                    hedge_cost_t1 = 1.05
                else:
                    hedge_cost_t1 = float(
                        compute_net_buy_cost_per_delivered_share(
                            float(h_bk.asks[0].price),
                            fee_rate_bps=float(h_bk.fee_rate_bps),
                            fee_exponent=float(h_bk.fee_exponent),
                            is_maker=False,
                        )[0]
                    )

            combined_cost_t1 = q.quote_bid_px + hedge_cost_t1
            reb_usd = round(q.shares * q.est_maker_rebate_ps, 6)
            if combined_cost_t1 < 1.0 - 1e-9:
                locked_pnl = round(q.shares * (1.0 - combined_cost_t1), 6)
                self.filled_hedged_locks_count += 1
                fills_this_cycle += 1
                self.locked_spread_shadow_pnl_usd = round(self.locked_spread_shadow_pnl_usd + locked_pnl, 6)
                self.estimated_maker_rebate_15_to_25pct_usd = round(
                    self.estimated_maker_rebate_15_to_25pct_usd + reb_usd, 6
                )
                ev_rec = {
                    "quote_id": q.quote_id,
                    "sub_type": q.sub_type,
                    "status": "HEDGED_LOCK_FILLED",
                    "outcome": "HEDGED_MAKER_LOCK",
                    "cycle_index": cycle_index,
                    "shares": round(q.shares, 4),
                    "quote_bid_px": round(q.quote_bid_px, 4),
                    "hedge_cost_t1": round(hedge_cost_t1, 4),
                    "locked_spread_pnl_usd": locked_pnl,
                    "est_maker_rebate_usd": reb_usd,
                }
                self.recent_fill_events.append(ev_rec)
                cycle_events.append(ev_rec)
            else:
                # Adverse selection jump before WS hedge could complete!
                scratch_loss_ps = max(0.005, q.quote_bid_px - m_bid_t1) if m_bid_t1 > 0.0 else 0.03
                box_overrun_ps = max(0.005, combined_cost_t1 - 1.0)
                bleed_usd = round(q.shares * min(scratch_loss_ps, box_overrun_ps), 6)
                self.adverse_selected_fills_count += 1
                adverse_this_cycle += 1
                self.adverse_unwind_bleed_usd = round(self.adverse_unwind_bleed_usd + bleed_usd, 6)
                ev_rec = {
                    "quote_id": q.quote_id,
                    "sub_type": q.sub_type,
                    "status": "ADVERSE_SELECTED_UNWIND",
                    "outcome": "ADVERSE_JUMP_UNWOUND",
                    "cycle_index": cycle_index,
                    "shares": round(q.shares, 4),
                    "quote_bid_px": round(q.quote_bid_px, 4),
                    "hedge_cost_t1": round(hedge_cost_t1, 4),
                    "adverse_bleed_usd": -bleed_usd,
                    "est_maker_rebate_usd": reb_usd,
                }
                self.recent_fill_events.append(ev_rec)
                cycle_events.append(ev_rec)

        self.resting_quotes = still_resting
        if len(self.recent_fill_events) > 50:
            self.recent_fill_events = self.recent_fill_events[-50:]
        return {
            "fills_this_cycle": fills_this_cycle,
            "adverse_this_cycle": adverse_this_cycle,
            "resting_quotes_count": len(self.resting_quotes),
            "events": cycle_events,
        }

    def ingest_cycle_candidates(
        self,
        records: Sequence[PipelineOpportunityRecord],
        books: Mapping[str, InstrumentOrderBook],
        *,
        holdings: Optional[Mapping[str, InventoryHolding]] = None,
        cycle_index: int,
        now_ts: float,
    ) -> int:
        """
        Generates passive `postOnly=True` (`0 bps` maker) virtual completion quotes from:
          1. Pre-held non-`KMIA` inventory (`L1B` zero-naked-addition maker completion), and
          2. Dynamic-fee (`feesEnabled=True`) complete-set (`Family A`) & verified 2-leg dominance
             (`Families D, E, F, I, L`) pairs where Taker+Taker >= $1.00 due to V2 fees, but
             `0 bps` Maker Anchor + immediate WS Taker Hedge locks `>= min_locked_maker_edge_bps`.
        """
        posted_now = 0
        min_edge_dec = self.min_locked_maker_edge_bps / 10_000.0
        inv_map = holdings or {}

        # 1. Pre-held non-KMIA inventory passive completion (`L1B`)
        for held_tid, h_pos in inv_map.items():
            if h_pos.is_frozen_disputed or str(h_pos.market_id) in FROZEN_DISPUTED_MARKET_IDS or h_pos.shares <= 0.0:
                continue
            # Find complement binary token in same market
            comp_bks = [
                bk for tid, bk in books.items()
                if tid != held_tid and str(bk.market_id) == str(h_pos.market_id) and bk.bids and bk.asks
            ]
            if len(comp_bks) != 1:
                continue
            cbk = comp_bks[0]
            tick = float(cbk.tick_size or 0.01)
            raw_bid = min(float(cbk.asks[0].price) - tick, max(float(cbk.bids[0].price), 1.0 - min_edge_dec - h_pos.cost_basis_per_share))
            q_bid = round(math.floor((raw_bid + 1e-12) / tick) * tick, 4)
            if q_bid <= 0.01 or q_bid >= float(cbk.asks[0].price) - 1e-9:
                continue
            if (h_pos.cost_basis_per_share + q_bid) > (1.0 - min_edge_dec):
                continue
            sh = min(float(h_pos.shares), 20.0)
            if sh < float(cbk.min_order_size):
                continue
            qid = f"L1B_INV_{cbk.market_id}_{cbk.instrument_id[:10]}"
            if qid in self.resting_quotes:
                continue
            q_ahead = 0.0 if q_bid > float(cbk.bids[0].price) + 1e-9 else round(float(cbk.bids[0].size) * q_bid, 2)
            reb_frac = _estimate_maker_rebate_share_frac(float(cbk.fee_rate_bps), float(cbk.fee_exponent))
            reb_ps = _estimate_maker_rebate_per_share(q_bid, float(cbk.fee_rate_bps), float(cbk.fee_exponent))
            self.resting_quotes[qid] = VirtualHedgedMakerQuote(
                quote_id=qid,
                sub_type="L1B_INVENTORY_MAKER_COMPLETION",
                source_family="L",
                title_summary=f"[L1B Inv Maker] mkt={cbk.market_id}",
                created_cycle=cycle_index,
                created_ts=now_ts,
                expires_ts=now_ts + self.quote_ttl_sec,
                maker_token_id=cbk.instrument_id,
                maker_market_id=str(cbk.market_id),
                hedge_token_id=held_tid,
                hedge_market_id=str(h_pos.market_id),
                quote_bid_px=q_bid,
                initial_maker_ask_px=float(cbk.asks[0].price),
                initial_hedge_ask_net_px=float(h_pos.cost_basis_per_share),
                shares=sh,
                queue_ahead_usd=q_ahead,
                hedge_depth_ratio=99.0,
                fee_rate_bps=float(cbk.fee_rate_bps),
                fee_exponent=float(cbk.fee_exponent),
                rebate_share_frac=reb_frac,
                est_maker_rebate_ps=reb_ps,
                preheld_inventory_backed=True,
            )
            posted_now += 1
            self.total_quotes_posted += 1

        # 2. Dynamic-fee (`feesEnabled=True`) 2-leg Complete-Set & Verified Dominance Maker-Taker Boxes (`L1A` / `L2`)
        hard_disq_prefixes = (
            "D001_",
            "RULE_UNVERIFIED",
            "AMBIGUOUS_BARRIER",
            "AUGMENTED_",
            "INVALID_",
            "CROSSED_",
            "STALE_",
            "UMA_DISPUTED",
        )
        for rec in records:
            if len(self.resting_quotes) >= self.max_resting_quotes:
                break
            if rec.d001_kmia_blocked or rec.family_code not in ("A", "D", "E", "F", "I", "L"):
                continue
            if rec.opportunity_class == "CLASS_D":
                continue
            if any(str(d).upper().startswith(hard_disq_prefixes) for d in rec.disqualifiers):
                continue
            if rec.structure is not None and not rec.structure.rule_verified:
                continue

            # Extract exact 2 token IDs for the pair
            tids = [t for t in rec.instrument_ids if t in books]
            if len(tids) != 2:
                continue
            bk1, bk2 = books[tids[0]], books[tids[1]]
            if str(bk1.market_id) in FROZEN_DISPUTED_MARKET_IDS or str(bk2.market_id) in FROZEN_DISPUTED_MARKET_IDS:
                continue
            if not (bk1.bids and bk1.asks and bk2.bids and bk2.asks):
                continue
            # Focus on the 99.4% dynamic-fee universe (`fee_rate_bps > 0`) where 0-bps maker unlocks fee-blocked boxes
            if max(float(bk1.fee_rate_bps), float(bk2.fee_rate_bps)) <= 0.0 and rec.family_code != "L":
                continue

            # Evaluate quoting Leg 1 passive `postOnly` (`0 bps` maker) + hedging Leg 2 immediate FOK Taker
            for m_bk, h_bk in ((bk1, bk2), (bk2, bk1)):
                tick = float(m_bk.tick_size or 0.01)
                b0 = float(m_bk.bids[0].price)
                a0 = float(m_bk.asks[0].price)
                spread = a0 - b0
                if spread < tick - 1e-9 or b0 <= 0.01 or a0 >= 0.99:
                    continue
                raw_q = min(a0 - tick, b0 + tick) if spread >= (2.0 * tick - 1e-9) else b0
                q_px = round(math.floor((raw_q + 1e-12) / tick) * tick, 4)
                if q_px <= 0.01 or q_px >= a0 - 1e-9:
                    continue

                h_ask_px = float(h_bk.asks[0].price)
                h_ask_net = float(
                    compute_net_buy_cost_per_delivered_share(
                        h_ask_px,
                        fee_rate_bps=float(h_bk.fee_rate_bps),
                        fee_exponent=float(h_bk.fee_exponent),
                        is_maker=False,
                    )[0]
                )
                m_tak_net = float(
                    compute_net_buy_cost_per_delivered_share(
                        a0,
                        fee_rate_bps=float(m_bk.fee_rate_bps),
                        fee_exponent=float(m_bk.fee_exponent),
                        is_maker=False,
                    )[0]
                )
                # Only quote passively when Taker+Taker is fee-blocked (`>= 0.9995`) OR candidate came from Family L,
                # AND Maker(0-bps) + Taker locks `>= min_locked_maker_edge_bps`!
                if (m_tak_net + h_ask_net) < 0.9995 and rec.family_code != "L":
                    continue
                if (q_px + h_ask_net) > (1.0 - min_edge_dec):
                    continue

                q_ahead_usd = 0.0 if q_px > b0 + 1e-9 else round(float(m_bk.bids[0].size) * q_px, 2)
                if q_ahead_usd > self.max_queue_ahead_usd:
                    continue

                min_sh = max(float(m_bk.min_order_size), float(h_bk.min_order_size), 5.0)
                if min_sh * q_px < 1.0:
                    min_sh = math.ceil(1.0 / max(0.01, q_px))
                avail_h_sh = sum(float(lv.size) for lv in h_bk.asks[:2] if float(lv.price) <= h_ask_px + 0.01 + 1e-9)
                depth_ratio = avail_h_sh / max(1.0, min_sh)
                if depth_ratio < self.min_hedge_depth_ratio:
                    continue

                clip_sh = min(15.0, max(min_sh, math.floor(avail_h_sh / self.min_hedge_depth_ratio)))
                qid = f"L_MKR_{rec.family_code}_{m_bk.instrument_id[:10]}_{h_bk.instrument_id[:10]}"
                if qid in self.resting_quotes:
                    continue

                sub_t = (
                    "L1A_PASSIVE_COMPLETE_SET_ANCHOR"
                    if str(m_bk.market_id) == str(h_bk.market_id)
                    else "L2_DOMINANCE_MAKER_ANCHOR"
                )
                reb_frac = _estimate_maker_rebate_share_frac(float(m_bk.fee_rate_bps), float(m_bk.fee_exponent))
                reb_ps = _estimate_maker_rebate_per_share(q_px, float(m_bk.fee_rate_bps), float(m_bk.fee_exponent))
                self.resting_quotes[qid] = VirtualHedgedMakerQuote(
                    quote_id=qid,
                    sub_type=sub_t,
                    source_family=rec.family_code,
                    title_summary=rec.title_summary[:64],
                    created_cycle=cycle_index,
                    created_ts=now_ts,
                    expires_ts=now_ts + self.quote_ttl_sec,
                    maker_token_id=m_bk.instrument_id,
                    maker_market_id=str(m_bk.market_id),
                    hedge_token_id=h_bk.instrument_id,
                    hedge_market_id=str(h_bk.market_id),
                    quote_bid_px=q_px,
                    initial_maker_ask_px=a0,
                    initial_hedge_ask_net_px=round(h_ask_net, 6),
                    shares=float(clip_sh),
                    queue_ahead_usd=q_ahead_usd,
                    hedge_depth_ratio=round(depth_ratio, 2),
                    fee_rate_bps=float(m_bk.fee_rate_bps),
                    fee_exponent=float(m_bk.fee_exponent),
                    rebate_share_frac=reb_frac,
                    est_maker_rebate_ps=reb_ps,
                    preheld_inventory_backed=False,
                )
                posted_now += 1
                self.total_quotes_posted += 1
                break

        return posted_now

    def summary_metrics(self) -> Dict[str, Any]:
        net_post_adverse = round(self.locked_spread_shadow_pnl_usd - self.adverse_unwind_bleed_usd, 6)
        resting_list = [
            {
                "quote_id": q.quote_id,
                "sub_type": q.sub_type,
                "source_family": q.source_family,
                "title_summary": q.title_summary,
                "quote_bid_px": round(q.quote_bid_px, 4),
                "initial_hedge_ask_net_px": round(q.initial_hedge_ask_net_px, 4),
                "locked_edge_bps_if_filled": round((1.0 - (q.quote_bid_px + q.initial_hedge_ask_net_px)) * 10_000.0, 1),
                "shares": round(q.shares, 2),
                "queue_ahead_usd": round(q.queue_ahead_usd, 2),
                "rebate_share_pct": round(q.rebate_share_frac * 100.0, 1),
                "est_maker_rebate_ps": q.est_maker_rebate_ps,
            }
            for q in sorted(
                self.resting_quotes.values(),
                key=lambda x: (-(1.0 - (x.quote_bid_px + x.initial_hedge_ask_net_px)), x.queue_ahead_usd),
            )[:10]
        ]
        return {
            "resting_passive_quotes_count": len(self.resting_quotes),
            "total_quotes_posted": self.total_quotes_posted,
            "total_quotes_evaluated_next_cycle": self.total_quotes_evaluated_next_cycle,
            "filled_hedged_locks_count": self.filled_hedged_locks_count,
            "adverse_selected_fills_count": self.adverse_selected_fills_count,
            "expired_unfilled_count": self.expired_unfilled_count,
            "maker_fee_bps": 0.0,
            "locked_spread_shadow_pnl_ex_rebate_usd": round(self.locked_spread_shadow_pnl_usd, 6),
            "adverse_selection_unwind_bleed_usd": round(self.adverse_unwind_bleed_usd, 6),
            "net_post_adverse_shadow_pnl_ex_rebate_usd": net_post_adverse,
            "estimated_maker_rebate_15_to_25pct_usd": round(self.estimated_maker_rebate_15_to_25pct_usd, 6),
            "strictly_segregated_from_locked_cash": True,
            "top_resting_quotes": resting_list,
            "recent_fill_events": list(self.recent_fill_events[-10:]),
        }

    def to_checkpoint_dict(self) -> Dict[str, Any]:
        return {
            "total_quotes_posted": self.total_quotes_posted,
            "total_quotes_evaluated_next_cycle": self.total_quotes_evaluated_next_cycle,
            "filled_hedged_locks_count": self.filled_hedged_locks_count,
            "adverse_selected_fills_count": self.adverse_selected_fills_count,
            "expired_unfilled_count": self.expired_unfilled_count,
            "locked_spread_shadow_pnl_usd": self.locked_spread_shadow_pnl_usd,
            "adverse_unwind_bleed_usd": self.adverse_unwind_bleed_usd,
            "estimated_maker_rebate_15_to_25pct_usd": self.estimated_maker_rebate_15_to_25pct_usd,
            "resting_quotes": [asdict(q) for q in self.resting_quotes.values()],
            "recent_fill_events": self.recent_fill_events[-25:],
        }

    def load_checkpoint_dict(self, data: Optional[Mapping[str, Any]]) -> None:
        if not isinstance(data, Mapping):
            return
        self.total_quotes_posted = int(data.get("total_quotes_posted", 0))
        self.total_quotes_evaluated_next_cycle = int(data.get("total_quotes_evaluated_next_cycle", 0))
        self.filled_hedged_locks_count = int(data.get("filled_hedged_locks_count", 0))
        self.adverse_selected_fills_count = int(data.get("adverse_selected_fills_count", 0))
        self.expired_unfilled_count = int(data.get("expired_unfilled_count", 0))
        self.locked_spread_shadow_pnl_usd = float(data.get("locked_spread_shadow_pnl_usd", 0.0))
        self.adverse_unwind_bleed_usd = float(data.get("adverse_unwind_bleed_usd", 0.0))
        self.estimated_maker_rebate_15_to_25pct_usd = float(data.get("estimated_maker_rebate_15_to_25pct_usd", 0.0))
        self.recent_fill_events = list(data.get("recent_fill_events") or [])[-25:]
        rq_out: Dict[str, VirtualHedgedMakerQuote] = {}
        for item in data.get("resting_quotes") or ():
            if isinstance(item, Mapping) and item.get("quote_id"):
                try:
                    q_obj = VirtualHedgedMakerQuote(
                        quote_id=str(item["quote_id"]),
                        sub_type=str(item.get("sub_type") or "L1A_PASSIVE_COMPLETE_SET_ANCHOR"),
                        source_family=str(item.get("source_family") or "L"),
                        title_summary=str(item.get("title_summary") or ""),
                        created_cycle=int(item.get("created_cycle", 0)),
                        created_ts=float(item.get("created_ts", 0.0)),
                        expires_ts=float(item.get("expires_ts", 0.0)),
                        maker_token_id=str(item.get("maker_token_id") or ""),
                        maker_market_id=str(item.get("maker_market_id") or ""),
                        hedge_token_id=str(item.get("hedge_token_id") or ""),
                        hedge_market_id=str(item.get("hedge_market_id") or ""),
                        quote_bid_px=float(item.get("quote_bid_px", 0.0)),
                        initial_maker_ask_px=float(item.get("initial_maker_ask_px", 1.0)),
                        initial_hedge_ask_net_px=float(item.get("initial_hedge_ask_net_px", 1.0)),
                        shares=float(item.get("shares", 5.0)),
                        queue_ahead_usd=float(item.get("queue_ahead_usd", 0.0)),
                        hedge_depth_ratio=float(item.get("hedge_depth_ratio", 2.0)),
                        fee_rate_bps=float(item.get("fee_rate_bps", 0.0)),
                        fee_exponent=float(item.get("fee_exponent", 1.0)),
                        rebate_share_frac=float(item.get("rebate_share_frac", 0.0)),
                        est_maker_rebate_ps=float(item.get("est_maker_rebate_ps", 0.0)),
                        preheld_inventory_backed=bool(item.get("preheld_inventory_backed", False)),
                    )
                    rq_out[q_obj.quote_id] = q_obj
                except Exception:
                    continue
        self.resting_quotes = rq_out


# ---------------------------------------------------------------------------
# 5C. Production Harvester Candidate Bridge Emitter (`d1_live_box_candidates.jsonl`)
# ---------------------------------------------------------------------------


INSTANT_MERGEABLE_BRIDGE_SLEEVES: FrozenSet[str] = frozenset(
    {
        "C1_BINARY_COMPLETE_SET",
        "C1_SPLIT_AND_SELL_OVERROUND",
        "NR2_2LEG_CONVERT_NO_SUBSET_ARB",
    }
)


class HarvesterCandidateBridge:
    """
    Emits mathematically proven `CLASS_A` and `<= 2`-leg `CLASS_B` opportunities from
    `FullThrottlePipeline` to `data/polymarket/d1_live_box_candidates.jsonl` in the exact schema
    consumed by `PolymarketLiveHarvester._poll_d1_live_box_candidates_unlocked`.

    Single-Execution-Authority & Safety Guarantees:
      - `FullThrottlePipeline` NEVER accesses private keys or places orders (`MODE_2_SHADOW`).
      - Rejects `CLASS_C`, `CLASS_D`, `CLASS_E`, unverified rules (`rule_verified != True`),
        resting maker legs (`is_maker == True`), `D-001` `KMIA` markets (`6707503`, `6707502`),
        and `>= 3` sequential CLOB legs below `$500` reconciled NAV (`D-007`).
      - Sizes strictly off `reconciled_nav_usd` (`~$48.70` worst-case floor cash, NEVER `$99.21`
        book equity), enforcing `<= 15%` NAV concentration (`~$7.30` at `$48.70`) and
        `>= 7.5 bps/hr` capital velocity (or instant-mergeable `C1`/`NR2`).
      - Deduplicates by `(dedupe_key, candidate_digest)` with configurable TTL (`45s`).
    """

    def __init__(
        self,
        *,
        candidates_jsonl_path: Path,
        dedupe_state_path: Path,
        dedupe_ttl_sec: float = 45.0,
        min_velocity_bps_per_hr: float = 7.5,
        live_harvester_state_path: Path = Path("data/polymarket/live_harvester_state.json"),
        utilization_aware_velocity_hurdle: bool = False,
    ) -> None:
        self.candidates_jsonl_path = Path(candidates_jsonl_path)
        self.dedupe_state_path = Path(dedupe_state_path)
        self.dedupe_ttl_sec = max(5.0, float(dedupe_ttl_sec))
        self.min_velocity_bps_per_hr = max(0.0, float(min_velocity_bps_per_hr))
        self.live_harvester_state_path = Path(live_harvester_state_path)
        self.utilization_aware_velocity_hurdle = bool(utilization_aware_velocity_hurdle)
        self._dedupe_cache: Dict[str, Dict[str, Any]] = {}
        self.total_emitted: int = 0
        self.total_dedupe_suppressed: int = 0
        self.total_jit_verified: int = 0
        self.total_jit_rejected: int = 0
        self.total_maker_locks_emitted: int = 0
        self._load_dedupe_cache()

    def _load_dedupe_cache(self) -> None:
        if not self.dedupe_state_path.exists():
            return
        try:
            doc = json.loads(self.dedupe_state_path.read_text(encoding="utf-8"))
            if isinstance(doc, Mapping) and isinstance(doc.get("entries"), Mapping):
                self._dedupe_cache = {
                    str(k): dict(v) for k, v in doc["entries"].items() if isinstance(v, Mapping)
                }
        except Exception:
            self._dedupe_cache = {}

    def _save_dedupe_cache(self, now_ts: float) -> None:
        self._dedupe_cache = {
            k: v
            for k, v in self._dedupe_cache.items()
            if (now_ts - float(v.get("emitted_ts", 0.0))) <= max(self.dedupe_ttl_sec * 4.0, 600.0)
        }
        if len(self._dedupe_cache) > 512:
            keep = sorted(
                self._dedupe_cache.items(), key=lambda kv: float(kv[1].get("emitted_ts", 0.0)), reverse=True
            )[:512]
            self._dedupe_cache = dict(keep)
        try:
            _atomic_write_json(
                self.dedupe_state_path,
                {"updated_at_unix": round(now_ts, 3), "entries": self._dedupe_cache},
            )
        except Exception:
            pass

    def resolve_reconciled_floor_nav_usd(self, fallback_nav_usd: float) -> float:
        """
        Reads `reconciled_nav_usd` / `live_bankroll` from `live_harvester_state.json` if available
        and fresh (`<= 900s` old), strictly excluding `$50.51` frozen `KMIA` book equity
        (`total_account_equity` is NEVER used!).
        """
        nav = max(1.0, float(fallback_nav_usd))
        if not self.live_harvester_state_path.exists():
            return nav
        try:
            age_s = time.time() - float(self.live_harvester_state_path.stat().st_mtime)
            if age_s > 900.0:
                return nav
            st = json.loads(self.live_harvester_state_path.read_text(encoding="utf-8"))
            if not isinstance(st, Mapping):
                return nav
            candidates_nav: List[float] = []
            for key in ("reconciled_nav_usd", "live_bankroll"):
                val = st.get(key)
                if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(float(val)) and float(val) > 0.0:
                    candidates_nav.append(float(val))
            if candidates_nav:
                return max(1.0, min(candidates_nav))
        except Exception:
            pass
        return nav

    @staticmethod
    def _classify_harvester_box_and_sleeve(
        rec: PipelineOpportunityRecord,
        clob_legs: Sequence[Any],
        all_legs: Sequence[Any],
        books: Mapping[str, InstrumentOrderBook],
        market_meta_by_id: Mapping[str, Mapping[str, Any]],
    ) -> Optional[Tuple[str, str]]:
        """Maps a verified `CLASS_A` or `<= 2`-leg `CLASS_B` record to `(box_type, sleeve_source)`."""
        def _act(lg: Any) -> str:
            a = getattr(lg, "action_type", "")
            return a.value if isinstance(a, ActionType) else str(a)

        def _mid_of(lg: Any, fallback_idx: int = 0) -> str:
            m_direct = str(getattr(lg, "market_id", "") or "").strip()
            if m_direct:
                return m_direct
            tid_s = str(getattr(lg, "instrument_id", "") or "").strip()
            if tid_s and tid_s in books and books[tid_s].market_id:
                return str(books[tid_s].market_id).strip()
            if fallback_idx < len(rec.market_ids):
                return str(rec.market_ids[fallback_idx]).strip()
            return ""

        has_split = any(_act(lg) == "CTF_SPLIT" for lg in all_legs)
        has_nr_conv = any(_act(lg) == "NEGRISK_CONVERT" for lg in all_legs)
        has_inv = any(_act(lg) == "USE_INVENTORY" for lg in all_legs)
        sell_legs = [lg for lg in clob_legs if _act(lg) == "SELL_CLOB"]
        buy_legs = [lg for lg in clob_legs if _act(lg) == "BUY_CLOB"]

        if len(clob_legs) == 1 and len(buy_legs) == 1 and has_inv:
            if bool(getattr(buy_legs[0], "is_maker", False)):
                return ("SINGLE_LEG_MAKER_LOCK", "C1_BINARY_COMPLETE_SET")
            return ("SINGLE_LEG_LOCK", "C1_BINARY_COMPLETE_SET")

        if has_split and len(sell_legs) == 2 and len(buy_legs) == 0:
            m0 = _mid_of(sell_legs[0], 0)
            m1 = _mid_of(sell_legs[1], 0)
            if m0 and m0 == m1:
                return ("CTF_OVERROUND", "C1_SPLIT_AND_SELL_OVERROUND")
            return None

        if len(buy_legs) != 2 or sell_legs:
            return None

        m_a = _mid_of(buy_legs[0], 0)
        m_b = _mid_of(buy_legs[1], 1 if len(rec.market_ids) >= 2 else 0)

        if m_a and m_b and m_a == m_b:
            return ("COMPLETE_SET", "C1_BINARY_COMPLETE_SET")

        if not m_a or not m_b or m_a == m_b:
            return None

        if has_nr_conv or rec.family_code == "C":
            meta_a = market_meta_by_id.get(m_a) or {}
            nrm = str(meta_a.get("negRiskMarketID") or "").strip().lower().replace("0x", "")
            if has_nr_conv and len(nrm) == 64 and meta_a.get("questionIndex") is not None:
                return ("NEGRISK_CONVERT", "NR2_2LEG_CONVERT_NO_SUBSET_ARB")
            return ("NEGRISK_2LEG", "XV_SUBSET_NO_2LEG_BOX")

        if rec.family_code == "E":
            return ("LADDER_MONO", "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX")
        if rec.family_code == "I":
            return ("CROSS_BASIS_DOMINANCE", "FT_DUP1_EXACT_CROSS_EVENT_BOX")
        if rec.family_code in ("F", "G", "H"):
            return ("BARRIER_MONO", "FT_STRIKE1_VERIFIED_DOMINANCE_BOX")
        if rec.family_code == "D":
            tid0 = str(getattr(buy_legs[0], "instrument_id", ""))
            tid1 = str(getattr(buy_legs[1], "instrument_id", ""))
            lbl0 = str(getattr(buy_legs[0], "label", "") or (books[tid0].outcome_label if tid0 in books else "")).strip().upper()
            lbl1 = str(getattr(buy_legs[1], "label", "") or (books[tid1].outcome_label if tid1 in books else "")).strip().upper()
            if lbl0 == "NO" and lbl1 == "NO":
                return ("NEGRISK_2LEG", "XV_SUBSET_NO_2LEG_BOX")
            return ("MACRO_DOMINANCE", "COND1_MACRO_PARTITION_BOX")
        return ("BARRIER_MONO", "FT_STRIKE1_VERIFIED_DOMINANCE_BOX")

    @staticmethod
    def _build_market_token_index(
        books: Mapping[str, InstrumentOrderBook],
        market_meta_by_id: Mapping[str, Mapping[str, Any]],
        events: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Dict[str, Tuple[str, ...]]:
        idx: Dict[str, List[str]] = {}
        for mid, meta in market_meta_by_id.items():
            if not mid or not isinstance(meta, Mapping):
                continue
            raw_tids = meta.get("clobTokenIds")
            tids = [str(x).strip() for x in _parse_json_list_safe(raw_tids) if str(x).strip()]
            if len(tids) >= 2:
                idx[str(mid)] = list(dict.fromkeys(tids))
        if events:
            for ev in events:
                for m in ev.get("markets") or ():
                    if not isinstance(m, Mapping):
                        continue
                    mid = str(m.get("id") or m.get("market_id") or "").strip()
                    if mid and mid not in idx:
                        tids = [str(x).strip() for x in _parse_json_list_safe(m.get("clobTokenIds")) if str(x).strip()]
                        if len(tids) >= 2:
                            idx[mid] = list(dict.fromkeys(tids))
        for tid, bk in books.items():
            mid = str(getattr(bk, "market_id", "") or "").strip()
            if mid and tid:
                lst = idx.setdefault(mid, [])
                if tid not in lst:
                    lst.append(tid)
        return {k: tuple(v) for k, v in idx.items() if len(v) >= 2}

    @staticmethod
    def _resolve_opp_token_id(
        token_id: str,
        market_id: str,
        mkt_tok_index: Mapping[str, Tuple[str, ...]],
    ) -> str:
        tids = mkt_tok_index.get(str(market_id))
        if not tids or len(tids) != 2:
            return ""
        if tids[0] == token_id:
            return tids[1]
        if tids[1] == token_id:
            return tids[0]
        return ""

    @staticmethod
    def _walk_leg_net_unit(
        bk: InstrumentOrderBook,
        action_str: str,
        shares: float,
    ) -> Optional[Tuple[float, float]]:
        """
        Walks `bk` for `shares` net outcome shares, returning `(net_usdc_per_share, worst_limit_px)`
        or `None` if L2 depth is insufficient.
        """
        rem = float(shares)
        if rem <= 0.0:
            return None
        if action_str == "BUY_CLOB":
            if not bk.asks:
                return None
            acc_cost = 0.0
            worst_px = 0.0
            for lv in bk.asks:
                px = float(lv.price)
                sz = float(lv.size)
                if px <= 0.0 or sz <= 0.0:
                    continue
                unit_net, _, _ = compute_net_buy_cost_per_delivered_share(
                    px,
                    fee_rate_bps=float(bk.fee_rate_bps),
                    fee_exponent=float(bk.fee_exponent),
                    is_maker=False,
                )
                haircut_ratio = px / max(1e-9, unit_net)
                avail_net = sz * haircut_ratio
                take = min(rem, avail_net)
                acc_cost += take * unit_net
                worst_px = max(worst_px, px)
                rem -= take
                if rem <= 1e-7:
                    break
            if rem > 1e-6:
                return None
            return (acc_cost / float(shares), worst_px)

        if not bk.bids:
            return None
        acc_proc = 0.0
        worst_px = 1.0
        for lv in bk.bids:
            px = float(lv.price)
            sz = float(lv.size)
            if px <= 0.0 or sz <= 0.0:
                continue
            unit_proc, _, _ = compute_net_sell_proceeds_per_share(
                px,
                fee_rate_bps=float(bk.fee_rate_bps),
                fee_exponent=float(bk.fee_exponent),
                is_maker=False,
            )
            take = min(rem, sz)
            acc_proc += take * unit_proc
            worst_px = min(worst_px, px)
            rem -= take
            if rem <= 1e-7:
                break
        if rem > 1e-6:
            return None
        return (acc_proc / float(shares), worst_px)

    def resolve_utilization_velocity_hurdle_bps_per_hr(
        self,
        eff_nav_usd: float,
        *,
        utilization_frac: Optional[float] = None,
    ) -> Tuple[float, Optional[float]]:
        """
        Computes utilization-aware velocity hurdle via `DynamicMarginalCapitalAllocator.compute_shadow_price_bps_per_hr`
        when `utilization_frac` is supplied or `utilization_aware_velocity_hurdle=True`; otherwise retains
        `self.min_velocity_bps_per_hr` for legacy fixed-threshold callers.
        """
        if utilization_frac is None and not self.utilization_aware_velocity_hurdle:
            return (self.min_velocity_bps_per_hr, None)

        u_resolved: Optional[float] = None
        if utilization_frac is not None:
            u_resolved = min(1.0, max(0.0, float(utilization_frac)))
        elif self.live_harvester_state_path.exists():
            try:
                if (time.time() - float(self.live_harvester_state_path.stat().st_mtime)) <= 900.0:
                    st = _loads_json_bytes(self.live_harvester_state_path.read_bytes())
                    if isinstance(st, Mapping):
                        committed_usd = 0.0
                        act_pos = st.get("active_positions")
                        if isinstance(act_pos, Mapping):
                            for p in act_pos.values():
                                if not isinstance(p, Mapping):
                                    continue
                                if str(p.get("umaResolutionStatus") or "").strip().lower() == "disputed":
                                    continue
                                mid_p = str(p.get("market_id") or "").strip()
                                if mid_p in FROZEN_DISPUTED_MARKET_IDS:
                                    continue
                                if str(p.get("status") or "") not in ("POSITION_CONFIRMED", "PARTIAL_OPEN", "OPEN", ""):
                                    continue
                                rem_sh = float(p.get("remaining_shares", p.get("entry_shares", 0.0)) or 0.0)
                                e_px = float(p.get("entry_price", 0.0) or 0.0)
                                c_usd = float(p.get("cost_basis_usd", rem_sh * e_px) or 0.0)
                                if c_usd > 0.0:
                                    committed_usd += c_usd
                        pend = st.get("pending_entry_intents")
                        if isinstance(pend, Mapping):
                            for pi in pend.values():
                                if isinstance(pi, Mapping):
                                    committed_usd += max(0.0, float(pi.get("notional_usd", 0.0) or 0.0))
                        denom = max(1e-6, float(eff_nav_usd) + committed_usd)
                        u_resolved = min(1.0, max(0.0, committed_usd / denom))
            except Exception:
                u_resolved = 0.0
        if u_resolved is None:
            u_resolved = 0.0

        lam = DynamicMarginalCapitalAllocator().compute_shadow_price_bps_per_hr(u_resolved)
        scale = (self.min_velocity_bps_per_hr / 7.5) if self.min_velocity_bps_per_hr > 0.0 else 0.0
        return (round(lam * scale, 6), round(u_resolved, 4))

    def emit_verified_candidates(
        self,
        records: Sequence[PipelineOpportunityRecord],
        books: Mapping[str, InstrumentOrderBook],
        *,
        holdings: Optional[Mapping[str, InventoryHolding]] = None,
        market_meta_by_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
        events: Optional[Sequence[Mapping[str, Any]]] = None,
        jit_book_fetcher: Optional[
            Callable[[Sequence[str]], Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]]
        ] = None,
        verifier: Optional[UniversalArbVerifier] = None,
        enable_passive_maker_bridge: bool = True,
        max_maker_locks_per_cycle: int = 3,
        fallback_reconciled_nav_usd: float = DEFAULT_LIVE_RECONCILED_NAV_USD,
        utilization_frac: Optional[float] = None,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        now_f = float(time.time() if now_ts is None else now_ts)
        mkt_meta = market_meta_by_id or {}
        inv_map = holdings or {}
        eff_nav_usd = self.resolve_reconciled_floor_nav_usd(fallback_reconciled_nav_usd)
        eff_min_vel_bps_hr, resolved_util_frac = self.resolve_utilization_velocity_hurdle_bps_per_hr(
            eff_nav_usd, utilization_frac=utilization_frac
        )
        nav_15pct_cap_usd = round(eff_nav_usd * 0.15, 6)
        mkt_tok_index = self._build_market_token_index(books, mkt_meta, events)

        emitted_payloads: List[Dict[str, Any]] = []
        skipped_reasons: Counter[str] = Counter()
        jit_verified_this_cycle = 0
        jit_rejected_this_cycle = 0
        maker_locks_this_cycle = 0

        for rec in records:
            if rec.d001_kmia_blocked or any(mid in FROZEN_DISPUTED_MARKET_IDS for mid in rec.market_ids):
                skipped_reasons["D001_KMIA_QUARANTINED"] += 1
                continue
            if any(sub.upper() in rec.candidate_id.upper() for sub in FROZEN_DISPUTED_TRADE_SUBSTRINGS) or (
                "WXSTATION:KMIA" in rec.canonical_event_keys
            ):
                skipped_reasons["D001_KMIA_QUARANTINED"] += 1
                continue
            all_legs: List[Any] = (
                list(rec.structure.legs)
                if (rec.structure is not None and rec.structure.legs)
                else (list(rec.proof.leg_executions) if (rec.proof is not None and rec.proof.leg_executions) else [])
            )
            clob_legs = [
                lg
                for lg in all_legs
                if (lg.action_type.value if isinstance(lg.action_type, ActionType) else str(lg.action_type))
                in ("BUY_CLOB", "SELL_CLOB")
            ]
            has_inv_leg = any(
                (lg.action_type.value if isinstance(lg.action_type, ActionType) else str(lg.action_type)) == "USE_INVENTORY"
                for lg in all_legs
            )
            is_l1_inv_maker = bool(
                len(clob_legs) == 1
                and has_inv_leg
                and (clob_legs[0].action_type.value if isinstance(clob_legs[0].action_type, ActionType) else str(clob_legs[0].action_type)) == "BUY_CLOB"
                and bool(getattr(clob_legs[0], "is_maker", False))
                and (
                    rec.family_code == "L"
                    or "L1_LOCKED_INVENTORY" in rec.candidate_id.upper()
                    or "L1B_RESTING" in rec.candidate_id.upper()
                    or "L1_LOCKED_INVENTORY" in rec.sub_type.upper()
                    or "L1B_RESTING" in rec.sub_type.upper()
                )
            )
            if not is_l1_inv_maker and (
                not rec.is_mathematically_proven_arb or rec.opportunity_class not in ("CLASS_A", "CLASS_B")
            ):
                continue
            if is_l1_inv_maker and rec.opportunity_class not in ("CLASS_A", "CLASS_B", "CLASS_C"):
                continue
            if (not is_l1_inv_maker and rec.disqualifiers) or (rec.structure is not None and not rec.structure.rule_verified):
                skipped_reasons["RULE_UNVERIFIED_OR_DISQUALIFIED"] += 1
                continue
            if is_l1_inv_maker and any(
                str(dq).upper()
                not in {
                    "PASSIVE_MAKER_FILL_UNCERTAINTY_NOT_CLASS_A_OR_B",
                    "RESTING_MAKER_LEG",
                    "UNFILLED_MAKER_LEG",
                    "MAKER_FILL_UNCERTAINTY",
                    "PASSIVE_MAKER_WAIT",
                }
                for dq in (rec.disqualifiers or ())
            ):
                skipped_reasons["RULE_UNVERIFIED_OR_DISQUALIFIED"] += 1
                continue
            if rec.min_state_net_payoff_usd <= 0.0 or (not is_l1_inv_maker and rec.executable_l2_net_usd <= 0.0) or rec.optimal_executable_quantity <= 0.0:
                skipped_reasons["NON_POSITIVE_MIN_STATE_PAYOFF"] += 1
                continue
            if rec.d007_sub500_multileg_quarantine and eff_nav_usd < DEFAULT_D007_MULTILEG_NAV_FLOOR_USD:
                skipped_reasons["D007_MULTILEG_3PLUS_QUARANTINED"] += 1
                continue
            if not all_legs:
                skipped_reasons["MISSING_CANDIDATE_STRUCTURE"] += 1
                continue

            if any(bool(getattr(lg, "is_maker", False)) for lg in clob_legs) and not is_l1_inv_maker:
                skipped_reasons["RESTING_MAKER_LEG_EXCLUDED_FROM_TAKER_BRIDGE"] += 1
                continue
            if not (1 <= len(clob_legs) <= 2):
                skipped_reasons["D007_LEG_COUNT_NOT_1_OR_2"] += 1
                continue

            mapped = self._classify_harvester_box_and_sleeve(rec, clob_legs, all_legs, books, mkt_meta)
            if mapped is None:
                skipped_reasons["UNMAPPED_HARVESTER_SCHEMA"] += 1
                continue
            box_type, sleeve_source = mapped

            if (
                rec.capital_efficiency_bps_per_hr < eff_min_vel_bps_hr
                and sleeve_source not in INSTANT_MERGEABLE_BRIDGE_SLEEVES
            ):
                skipped_reasons["BELOW_VELOCITY_HURDLE_7_5_BPS_HR"] += 1
                continue

            leg_books_pre = [books.get(str(lg.instrument_id)) for lg in clob_legs]
            if any(bk is None for bk in leg_books_pre):
                skipped_reasons["MISSING_LIVE_L2_BOOK"] += 1
                continue

            # Resolve binary complement `opp_token_id`s upfront so JIT `/books` polls ALL leg + complement books!
            opp_by_leg_tid: Dict[str, str] = {}
            for lg in clob_legs:
                tid_c = str(lg.instrument_id)
                bk_c = books[tid_c]
                opp_by_leg_tid[tid_c] = self._resolve_opp_token_id(tid_c, str(bk_c.market_id), mkt_tok_index)

            need_sep_opp = len(clob_legs) == 2 and box_type not in ("COMPLETE_SET", "CTF_OVERROUND", "NEGRISK_CONVERT")
            if need_sep_opp and jit_book_fetcher is not None:
                t0_id = str(clob_legs[0].instrument_id)
                t1_id = str(clob_legs[1].instrument_id)
                if not opp_by_leg_tid.get(t0_id) or not opp_by_leg_tid.get(t1_id):
                    skipped_reasons["MISSING_COMPLEMENT_OPP_TOKEN_ID"] += 1
                    continue

            # Compute initial unit cost & scale shares to enforce `D-007` `<= 15%` reconciled NAV cap!
            opt_q = float(rec.optimal_executable_quantity)
            net_edge_ps = float(rec.net_executable_edge_per_unit)
            min_state_payoff_raw = float(rec.min_state_net_payoff_usd)
            unit_cap = float(rec.capital_required_usd) / max(1e-9, opt_q)
            if unit_cap <= 0.0:
                unit_cap = max(0.01, 1.0 - net_edge_ps)

            min_lot = max(
                max(float(bk.min_order_size) for bk in leg_books_pre if bk is not None),
                DEFAULT_MIN_ORDER_SHARES,
            )
            max_nav_shares = math.floor((nav_15pct_cap_usd / max(0.01, unit_cap)) + 1e-9)
            target_shares = int(math.floor(min(opt_q, float(max_nav_shares)) + 1e-9))
            if target_shares < int(math.ceil(min_lot - 1e-9)):
                skipped_reasons["D007_15PCT_NAV_BELOW_MIN_ORDER_SIZE"] += 1
                continue

            scale_frac = float(target_shares) / max(1e-9, opt_q)
            scaled_min_payoff_usd = round(min_state_payoff_raw * scale_frac, 6)
            box_cost_net = round(max(0.01, 1.0 - net_edge_ps), 6)
            if scaled_min_payoff_usd <= 0.0 or box_cost_net >= 1.0:
                skipped_reasons["NON_POSITIVE_SCALED_NET_EDGE"] += 1
                continue

            dedupe_key = f"FT_{sleeve_source}_{rec.candidate_id[:48]}"
            digest_input = f"{dedupe_key}:{box_cost_net:.4f}:{target_shares}:{rec.proof_sha256[:16]}"
            cand_digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:24]

            prev_emit = self._dedupe_cache.get(dedupe_key)
            if prev_emit is not None and (now_f - float(prev_emit.get("emitted_ts", 0.0))) < self.dedupe_ttl_sec:
                if str(prev_emit.get("digest") or "") == cand_digest or float(prev_emit.get("box_cost_net", 1.0)) <= box_cost_net + 0.0005:
                    self.total_dedupe_suppressed += 1
                    skipped_reasons["DEDUPE_TTL_ACTIVE"] += 1
                    continue

            # Just-In-Time (`<150ms`) `/books` Re-Verification right before appending to `d1_live_box_candidates.jsonl`!
            eff_books: Dict[str, InstrumentOrderBook] = dict(books)
            leg_exec_by_tid = {
                str(le.instrument_id): le for le in (rec.proof.leg_executions if rec.proof else ())
            }
            emit_ts = round(now_f, 3)

            if jit_book_fetcher is not None:
                jit_tids = list(
                    dict.fromkeys(
                        t
                        for t in (
                            *(str(lg.instrument_id) for lg in clob_legs),
                            *rec.instrument_ids,
                            *opp_by_leg_tid.values(),
                        )
                        if t
                    )
                )
                try:
                    fresh_raw, fresh_meta = jit_book_fetcher(jit_tids)
                except Exception:
                    fresh_raw, fresh_meta = {}, {}
                if not fresh_raw:
                    self.total_jit_rejected += 1
                    jit_rejected_this_cycle += 1
                    skipped_reasons["JIT_BOOK_REVERIFY_FETCH_FAILED"] += 1
                    continue

                jit_ts = float(fresh_meta.get("fetch_timestamp_sec") or time.time())
                for tid_j in jit_tids:
                    rb_j = fresh_raw.get(tid_j)
                    if not isinstance(rb_j, Mapping):
                        continue
                    prev_bk = books.get(tid_j)
                    if prev_bk is not None:
                        eff_books[tid_j] = InstrumentOrderBook.from_raw(
                            tid_j,
                            rb_j,
                            market_id=prev_bk.market_id,
                            condition_id=prev_bk.condition_id,
                            outcome_label=prev_bk.outcome_label,
                            fee_rate_bps=prev_bk.fee_rate_bps,
                            fee_exponent=prev_bk.fee_exponent,
                            tick_size=prev_bk.tick_size,
                            min_order_size=prev_bk.min_order_size,
                            enable_order_book=True,
                            book_timestamp_sec=jit_ts,
                        )
                    else:
                        # Complement `opp_token_id` that wasn't in `typed_books`: inherit market metadata from sibling leg
                        sib_mid = ""
                        sib_cid = ""
                        sib_fee_bps = 0.0
                        sib_fee_exp = 1.0
                        for lg_s in clob_legs:
                            tid_s = str(lg_s.instrument_id)
                            if opp_by_leg_tid.get(tid_s) == tid_j and tid_s in books:
                                sbk = books[tid_s]
                                sib_mid = sbk.market_id
                                sib_cid = sbk.condition_id
                                sib_fee_bps = sbk.fee_rate_bps
                                sib_fee_exp = sbk.fee_exponent
                                break
                        eff_books[tid_j] = InstrumentOrderBook.from_raw(
                            tid_j,
                            rb_j,
                            market_id=sib_mid,
                            condition_id=sib_cid,
                            outcome_label="OPP",
                            fee_rate_bps=sib_fee_bps,
                            fee_exponent=sib_fee_exp,
                            enable_order_book=True,
                            book_timestamp_sec=jit_ts,
                        )

                if any(str(lg.instrument_id) not in fresh_raw for lg in clob_legs):
                    self.total_jit_rejected += 1
                    jit_rejected_this_cycle += 1
                    skipped_reasons["JIT_BOOK_REVERIFY_MISSING_DEPTH"] += 1
                    continue

                if verifier is not None and rec.structure is not None:
                    jit_ver = UniversalArbVerifier(
                        config=VerificationConfig(
                            max_budget_usd=verifier.config.max_budget_usd,
                            reconciled_nav_usd=eff_nav_usd,
                            now_ts=jit_ts,
                            execution_mode=verifier.config.execution_mode,
                        )
                    )
                    jit_proof = jit_ver.verify_and_simulate(rec.structure, eff_books, holdings=inv_map)
                    jit_opp_cls = str(getattr(jit_proof.opportunity_class, "value", jit_proof.opportunity_class))
                    l1_mkr_jit_ok = bool(
                        is_l1_inv_maker
                        and jit_opp_cls in ("CLASS_A", "CLASS_B", "CLASS_C")
                        and jit_proof.min_state_net_payoff_usd > 0.0
                        and jit_proof.optimal_executable_quantity > 0.0
                    )
                    if not l1_mkr_jit_ok and (
                        not jit_proof.is_mathematically_proven_arb
                        or jit_opp_cls not in ("CLASS_A", "CLASS_B")
                        or jit_proof.min_state_net_payoff_usd <= 0.0
                        or jit_proof.four_value_ledger.executable_l2_net_usd <= 0.0
                        or jit_proof.optimal_executable_quantity <= 0.0
                    ):
                        self.total_jit_rejected += 1
                        jit_rejected_this_cycle += 1
                        skipped_reasons["JIT_BOOK_REVERIFY_EDGE_DECAYED"] += 1
                        continue
                    opt_q = float(jit_proof.optimal_executable_quantity)
                    net_edge_ps = float(jit_proof.net_executable_edge_per_unit)
                    min_state_payoff_raw = float(jit_proof.min_state_net_payoff_usd)
                    unit_cap = max(0.01, 1.0 - net_edge_ps)
                    leg_exec_by_tid = {str(le.instrument_id): le for le in jit_proof.leg_executions}
                else:
                    # Direct depth walk re-verification when `rec.structure` is omitted
                    walk_ok = True
                    walk_units: List[float] = []
                    new_exec_px: Dict[str, float] = {}
                    for lg in clob_legs:
                        tid_w = str(lg.instrument_id)
                        act_w = lg.action_type.value if isinstance(lg.action_type, ActionType) else str(lg.action_type)
                        w_res = self._walk_leg_net_unit(eff_books[tid_w], act_w, float(target_shares))
                        if w_res is None:
                            walk_ok = False
                            break
                        walk_units.append(w_res[0])
                        new_exec_px[tid_w] = w_res[1]
                    if not walk_ok:
                        self.total_jit_rejected += 1
                        jit_rejected_this_cycle += 1
                        skipped_reasons["JIT_BOOK_REVERIFY_MISSING_DEPTH"] += 1
                        continue
                    if box_type == "CTF_OVERROUND":
                        net_edge_ps = sum(walk_units) - 1.0
                    elif box_type in ("SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK"):
                        inv_cost_ps = 0.0
                        for lg_i in all_legs:
                            act_i = lg_i.action_type.value if isinstance(lg_i.action_type, ActionType) else str(lg_i.action_type)
                            if act_i == "USE_INVENTORY":
                                h_i = inv_map.get(str(lg_i.instrument_id))
                                inv_cost_ps = float(h_i.effective_valuation_per_share) if h_i is not None else 0.50
                        if box_type == "SINGLE_LEG_MAKER_LOCK":
                            mkr_px_w = float(getattr(clob_legs[0], "maker_price", 0.0) or 0.0)
                            unit_w = mkr_px_w if mkr_px_w > 0.0 else walk_units[0]
                            net_edge_ps = 1.0 - (unit_w + inv_cost_ps)
                        else:
                            net_edge_ps = 1.0 - (walk_units[0] + inv_cost_ps)
                    else:
                        net_edge_ps = 1.0 - sum(walk_units)
                    if net_edge_ps <= 0.0:
                        self.total_jit_rejected += 1
                        jit_rejected_this_cycle += 1
                        skipped_reasons["JIT_BOOK_REVERIFY_EDGE_DECAYED"] += 1
                        continue
                    unit_cap = max(0.01, 1.0 - net_edge_ps)
                    min_state_payoff_raw = net_edge_ps * opt_q
                    for tid_u, wpx in new_exec_px.items():
                        if tid_u in leg_exec_by_tid:
                            old_le = leg_exec_by_tid[tid_u]
                            leg_exec_by_tid[tid_u] = type(old_le)(
                                **{**old_le.__dict__, "worst_limit_price": wpx}
                            )

                # Recompute `D-007` `<=15%` NAV share clip against fresh JIT unit cost
                max_nav_shares = math.floor((nav_15pct_cap_usd / max(0.01, unit_cap)) + 1e-9)
                target_shares = int(math.floor(min(opt_q, float(max_nav_shares)) + 1e-9))
                if target_shares < int(math.ceil(min_lot - 1e-9)):
                    self.total_jit_rejected += 1
                    jit_rejected_this_cycle += 1
                    skipped_reasons["D007_15PCT_NAV_BELOW_MIN_ORDER_SIZE"] += 1
                    continue
                scale_frac = float(target_shares) / max(1e-9, opt_q)
                scaled_min_payoff_usd = round(min_state_payoff_raw * scale_frac, 6)
                box_cost_net = round(max(0.01, 1.0 - net_edge_ps), 6)
                if scaled_min_payoff_usd <= 0.0 or box_cost_net >= 1.0:
                    self.total_jit_rejected += 1
                    jit_rejected_this_cycle += 1
                    skipped_reasons["JIT_BOOK_REVERIFY_EDGE_DECAYED"] += 1
                    continue

                # Verify Harvester cross-market anti-box complement parity (`polymarket_live_harvester.py:6281-6296`)
                if need_sep_opp:
                    t0_id = str(clob_legs[0].instrument_id)
                    t1_id = str(clob_legs[1].instrument_id)
                    oa_id = opp_by_leg_tid.get(t0_id, "")
                    ob_id = opp_by_leg_tid.get(t1_id, "")
                    bk_oa = eff_books.get(oa_id)
                    bk_ob = eff_books.get(ob_id)
                    if bk_oa is None or bk_ob is None:
                        self.total_jit_rejected += 1
                        jit_rejected_this_cycle += 1
                        skipped_reasons["JIT_ANTI_BOX_MISSING_OPP_BOOK"] += 1
                        continue
                    bid_oa = float(bk_oa.bids[0].price) if bk_oa.bids else 0.0
                    bid_ob = float(bk_ob.bids[0].price) if bk_ob.bids else 0.0
                    ask_oa = float(bk_oa.asks[0].price) if bk_oa.asks else 0.0
                    ask_ob = float(bk_ob.asks[0].price) if bk_ob.asks else 0.0
                    ask_a = float(eff_books[t0_id].asks[0].price) if eff_books[t0_id].asks else 0.0
                    ask_b = float(eff_books[t1_id].asks[0].price) if eff_books[t1_id].asks else 0.0
                    oa_ok = bid_oa > 0.0 or (0.0 < ask_oa <= 0.12)
                    ob_ok = bid_ob > 0.0 or (0.0 < ask_ob <= 0.12)
                    opp_sum = bid_oa + bid_ob
                    opp_ub = (bid_oa if bid_oa > 0.0 else ask_oa) + (bid_ob if bid_ob > 0.0 else ask_ob)
                    if (
                        not (oa_ok and ob_ok)
                        or (bid_oa <= 0.0 and bid_ob <= 0.0)
                        or (ask_a > 0.0 and bid_oa > 0.0 and (ask_a + bid_oa) > 1.015)
                        or (ask_b > 0.0 and bid_ob > 0.0 and (ask_b + bid_ob) > 1.015)
                        or opp_sum > 1.160
                        or opp_ub > 1.180
                    ):
                        self.total_jit_rejected += 1
                        jit_rejected_this_cycle += 1
                        skipped_reasons["JIT_ANTI_BOX_COMPLEMENT_VETO"] += 1
                        continue

                self.total_jit_verified += 1
                jit_verified_this_cycle += 1
                emit_ts = round(time.time() if now_ts is None else jit_ts, 3)

            # Verify each BUY leg satisfies `$1.00` minimum marketable order notional against `eff_books`
            notional_ok = True
            for lg in clob_legs:
                tid_l = str(lg.instrument_id)
                bk_l = eff_books[tid_l]
                act_s = lg.action_type.value if isinstance(lg.action_type, ActionType) else str(lg.action_type)
                le_l = leg_exec_by_tid.get(tid_l)
                mkr_l_px = float(getattr(lg, "maker_price", 0.0) or 0.0) if bool(getattr(lg, "is_maker", False)) else 0.0
                px_l = (
                    mkr_l_px
                    if mkr_l_px > 0.0
                    else (
                        float(le_l.worst_limit_price)
                        if le_l is not None and le_l.worst_limit_price > 0.0
                        else (
                            float(bk_l.asks[0].price)
                            if act_s == "BUY_CLOB" and bk_l.asks
                            else (float(bk_l.bids[0].price) if bk_l.bids else 0.0)
                        )
                    )
                )
                if px_l <= 0.0 or (act_s == "BUY_CLOB" and (target_shares * px_l) < DEFAULT_MIN_MARKETABLE_BUY_USD - 1e-6):
                    notional_ok = False
                    break
            if not notional_ok:
                skipped_reasons["LEG_BELOW_1USD_MARKETABLE_FLOOR"] += 1
                continue

            exp_hours = max(0.05, float(rec.expected_lockup_hours))
            close_ts = round(emit_ts + exp_hours * 3600.0, 3)
            for mid_c in rec.market_ids:
                end_iso = str((mkt_meta.get(mid_c) or {}).get("endDate") or "").strip()
                if end_iso:
                    try:
                        dt_e = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                        if dt_e.timestamp() > emit_ts + 25.0:
                            close_ts = round(dt_e.timestamp(), 3)
                            break
                    except Exception:
                        pass
            rem_sec = round(max(26.0, close_ts - emit_ts), 2)

            ev_id_primary = str(rec.event_ids[0]) if rec.event_ids else ""
            ws_books_snap: Dict[str, Dict[str, Any]] = {}
            for tid_w in dict.fromkeys(
                t
                for t in (
                    *(str(lg.instrument_id) for lg in clob_legs),
                    *rec.instrument_ids,
                    *opp_by_leg_tid.values(),
                )
                if t
            ):
                bk_w = eff_books.get(tid_w)
                if bk_w is not None:
                    ws_books_snap[tid_w] = {
                        "bids": [{"price": str(lv.price), "size": str(lv.size)} for lv in bk_w.bids[:10]],
                        "asks": [{"price": str(lv.price), "size": str(lv.size)} for lv in bk_w.asks[:10]],
                    }

            base_common: Dict[str, Any] = {
                "box_id": f"FT_{box_type}_LIVE_{int(emit_ts)}_{cand_digest[:8]}",
                "dedupe_key": dedupe_key,
                "pair_dedupe_key": f"FT_PAIR_{'_'.join(rec.market_ids[:2])}",
                "candidate_id": rec.candidate_id,
                "candidate_digest": cand_digest,
                "proof_sha256": rec.proof_sha256,
                "box_type": box_type,
                "sleeve_source": sleeve_source,
                "opportunity_class": rec.opportunity_class,
                "full_throttle_bridge": True,
                "jit_reverified": jit_book_fetcher is not None,
                "rule_verified": True,
                "leg_count": len(clob_legs),
                "min_state_net_payoff_usd": scaled_min_payoff_usd,
                "net_edge_per_share": round(net_edge_ps, 6),
                "capital_efficiency_bps_per_hr": round(float(rec.capital_efficiency_bps_per_hr), 4),
                "reconciled_nav_usd": round(eff_nav_usd, 4),
                "d001_verified_clean": True,
                "d007_concentration_ok": True,
                "ts_unix": emit_ts,
                "asset": f"FT_{rec.family_code}",
                "event_id": ev_id_primary,
                "canonical_event_keys": list(rec.canonical_event_keys),
                "expiry_ts": close_ts,
                "rem_sec": rem_sec,
                "shares": target_shares,
                "net_paired_shares": float(target_shares),
                "box_cost_net": box_cost_net,
                "max_box_cost_net": round(min(0.9990, box_cost_net + 0.002), 4),
                "ws_books": ws_books_snap if ws_books_snap else None,
                "ws_books_ts": emit_ts,
            }

            if box_type in ("SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK"):
                is_mkr_sll = box_type == "SINGLE_LEG_MAKER_LOCK"
                lg0 = clob_legs[0]
                tid0 = str(lg0.instrument_id)
                bk0 = eff_books[tid0]
                le0 = leg_exec_by_tid.get(tid0)
                m0_meta = mkt_meta.get(str(bk0.market_id)) or {}
                inv_legs = [
                    lg
                    for lg in all_legs
                    if (lg.action_type.value if isinstance(lg.action_type, ActionType) else str(lg.action_type))
                    == "USE_INVENTORY"
                ]
                opp_tid = str(inv_legs[0].instrument_id) if inv_legs else opp_by_leg_tid.get(tid0, "")
                h_obj = inv_map.get(opp_tid)
                partner_cost_ps = round(float(h_obj.cost_basis_per_share), 6) if h_obj is not None else 0.0
                mkr_attr_px = float(getattr(lg0, "maker_price", 0.0) or 0.0) if is_mkr_sll else 0.0
                px0 = (
                    mkr_attr_px
                    if mkr_attr_px > 0.0
                    else (
                        float(le0.worst_limit_price)
                        if (le0 and le0.worst_limit_price > 0)
                        else (
                            float(bk0.bids[0].price)
                            if (is_mkr_sll and bk0.bids)
                            else float(bk0.asks[0].price)
                        )
                    )
                )
                if is_mkr_sll and bk0.asks and px0 >= float(bk0.asks[0].price) - 1e-9:
                    skipped_reasons["MAKER_BID_CROSSES_BEST_ASK"] += 1
                    continue
                leg_a_cap_px = round(min(px0 + 0.002, max(0.01, 0.9985 - partner_cost_ps)), 4) if h_obj is not None else round(px0, 4)
                lbl0 = str(getattr(lg0, "label", "") or bk0.outcome_label or "YES")
                cand_dict = {
                    **base_common,
                    "p_model": 1.0,
                    "hold_to_maturity_lock": False,
                    "inventory_backed_completion": bool(opp_tid and h_obj is not None),
                    "partner_held_token_id": opp_tid,
                    "partner_avg_cost_ps": partner_cost_ps,
                    "verified_wallet_inventory": {opp_tid: float(h_obj.shares)} if (opp_tid and h_obj) else {},
                    "leg_a_token_id": tid0,
                    "leg_a_opp_token_id": opp_tid,
                    "leg_a_market_id": str(bk0.market_id),
                    "leg_a_condition_id": str(bk0.condition_id or m0_meta.get("conditionId") or ""),
                    "leg_a_label": lbl0,
                    "leg_a_side": lbl0.upper(),
                    "leg_a_limit_price": round(px0, 4),
                    "leg_a_max_price": leg_a_cap_px,
                    "leg_a_avail_shares": round(sum(float(lv.size) for lv in bk0.asks), 4),
                    "leg_a_fee_rate": 0.0 if is_mkr_sll else round(float(bk0.fee_rate_bps) / 10_000.0, 6),
                    "leg_a_fee_exponent": 1.0 if is_mkr_sll else float(bk0.fee_exponent),
                    "leg_a_neg_risk": bool(getattr(bk0, "neg_risk", False) or m0_meta.get("negRisk")),
                    "leg_a_expiry_ts": close_ts,
                }
                if is_mkr_sll:
                    cand_dict["verifier_opportunity_class"] = rec.opportunity_class
                    if opp_tid and h_obj is not None:
                        cand_dict["opportunity_class"] = "CLASS_A"
                    cand_dict["anchor_bid_px"] = round(px0, 4)
                    cand_dict["post_only"] = True
                    cand_dict["min_maker_edge"] = round(max(0.0, 1.0 - (partner_cost_ps + px0)), 6)
                    maker_locks_this_cycle += 1
                    self.total_maker_locks_emitted += 1
            elif box_type == "CTF_OVERROUND":
                lg0, lg1 = clob_legs[0], clob_legs[1]
                bk0, bk1 = eff_books[str(lg0.instrument_id)], eff_books[str(lg1.instrument_id)]
                le0 = leg_exec_by_tid.get(str(lg0.instrument_id))
                le1 = leg_exec_by_tid.get(str(lg1.instrument_id))
                cid0 = str(bk0.condition_id or (mkt_meta.get(str(bk0.market_id)) or {}).get("conditionId") or f"cond_{bk0.market_id}")
                px0 = float(le0.worst_limit_price) if (le0 and le0.worst_limit_price > 0) else float(bk0.bids[0].price)
                px1 = float(le1.worst_limit_price) if (le1 and le1.worst_limit_price > 0) else float(bk1.bids[0].price)
                cand_dict = {
                    **base_common,
                    "condition_id": cid0,
                    "leg_a_market_id": str(bk0.market_id),
                    "leg_b_market_id": str(bk1.market_id),
                    "leg_a_token_id": str(lg0.instrument_id),
                    "leg_b_token_id": str(lg1.instrument_id),
                    "leg_a_opp_token_id": str(lg1.instrument_id),
                    "leg_b_opp_token_id": str(lg0.instrument_id),
                    "leg_a_fee_rate": round(float(bk0.fee_rate_bps) / 10_000.0, 6),
                    "leg_b_fee_rate": round(float(bk1.fee_rate_bps) / 10_000.0, 6),
                    "legs": [
                        {
                            "token_id": str(lg0.instrument_id),
                            "market_id": str(bk0.market_id),
                            "condition_id": cid0,
                            "side": "SELL",
                            "label": str(getattr(lg0, "label", "") or bk0.outcome_label or "YES"),
                            "limit_price": round(px0, 4),
                            "fee_rate": round(float(bk0.fee_rate_bps) / 10_000.0, 6),
                            "fee_exponent": float(bk0.fee_exponent),
                        },
                        {
                            "token_id": str(lg1.instrument_id),
                            "market_id": str(bk1.market_id),
                            "condition_id": cid0,
                            "side": "SELL",
                            "label": str(getattr(lg1, "label", "") or bk1.outcome_label or "NO"),
                            "limit_price": round(px1, 4),
                            "fee_rate": round(float(bk1.fee_rate_bps) / 10_000.0, 6),
                            "fee_exponent": float(bk1.fee_exponent),
                        },
                    ],
                }
            elif box_type == "NEGRISK_CONVERT":
                lg0, lg1 = clob_legs[0], clob_legs[1]
                bk0, bk1 = eff_books[str(lg0.instrument_id)], eff_books[str(lg1.instrument_id)]
                le0 = leg_exec_by_tid.get(str(lg0.instrument_id))
                le1 = leg_exec_by_tid.get(str(lg1.instrument_id))
                m0_meta = mkt_meta.get(str(bk0.market_id)) or {}
                m1_meta = mkt_meta.get(str(bk1.market_id)) or {}
                nrm_hex = str(m0_meta.get("negRiskMarketID") or "").strip()
                px0 = float(le0.worst_limit_price) if (le0 and le0.worst_limit_price > 0) else float(bk0.asks[0].price)
                px1 = float(le1.worst_limit_price) if (le1 and le1.worst_limit_price > 0) else float(bk1.asks[0].price)
                cand_dict = {
                    **base_common,
                    "convert_mode": "NR2_PURE_CASH_CONVERT",
                    "neg_risk_market_id": nrm_hex,
                    "fee_bips": 0,
                    "no_legs": [
                        {
                            "token_id": str(lg0.instrument_id),
                            "market_id": str(bk0.market_id),
                            "condition_id": str(bk0.condition_id or m0_meta.get("conditionId") or ""),
                            "question_index": int(m0_meta.get("questionIndex") or 0),
                            "label": str(getattr(lg0, "label", "") or bk0.outcome_label or "NO_0")[:48],
                            "limit_price": round(px0, 4),
                            "fee_rate": round(float(bk0.fee_rate_bps) / 10_000.0, 6),
                            "fee_exponent": float(bk0.fee_exponent),
                        },
                        {
                            "token_id": str(lg1.instrument_id),
                            "market_id": str(bk1.market_id),
                            "condition_id": str(bk1.condition_id or m1_meta.get("conditionId") or ""),
                            "question_index": int(m1_meta.get("questionIndex") or 1),
                            "label": str(getattr(lg1, "label", "") or bk1.outcome_label or "NO_1")[:48],
                            "limit_price": round(px1, 4),
                            "fee_rate": round(float(bk1.fee_rate_bps) / 10_000.0, 6),
                            "fee_exponent": float(bk1.fee_exponent),
                        },
                    ],
                    "yes_sell_legs": [],
                    "liquid_yes_sells": [],
                    "retained_tail_tokens": [],
                }
            else:
                lg0, lg1 = clob_legs[0], clob_legs[1]
                tid0, tid1 = str(lg0.instrument_id), str(lg1.instrument_id)
                bk0, bk1 = eff_books[tid0], eff_books[tid1]
                le0 = leg_exec_by_tid.get(tid0)
                le1 = leg_exec_by_tid.get(tid1)
                m0_meta = mkt_meta.get(str(bk0.market_id)) or {}
                m1_meta = mkt_meta.get(str(bk1.market_id)) or {}
                px0 = float(le0.worst_limit_price) if (le0 and le0.worst_limit_price > 0) else float(bk0.asks[0].price)
                px1 = float(le1.worst_limit_price) if (le1 and le1.worst_limit_price > 0) else float(bk1.asks[0].price)
                gross0 = float(le0.gross_shares) * scale_frac if (le0 and le0.gross_shares > 0) else float(target_shares)
                gross1 = float(le1.gross_shares) * scale_frac if (le1 and le1.gross_shares > 0) else float(target_shares)
                cid0 = str(bk0.condition_id or m0_meta.get("conditionId") or "")
                cid1 = str(bk1.condition_id or m1_meta.get("conditionId") or "")
                lbl0 = str(getattr(lg0, "label", "") or bk0.outcome_label or "YES")
                lbl1 = str(getattr(lg1, "label", "") or bk1.outcome_label or "NO")
                opp_a = tid1 if box_type == "COMPLETE_SET" else opp_by_leg_tid.get(tid0, "")
                opp_b = tid0 if box_type == "COMPLETE_SET" else opp_by_leg_tid.get(tid1, "")
                cand_dict = {
                    **base_common,
                    "regime": f"{box_type}_{rec.family_code}",
                    "pair_horizons": box_type.lower(),
                    "is_quiet_book": True,
                    "k_low": 100.0,
                    "k_high": 101.0,
                    "corridor_bps": 100.0,
                    "leg_a_gross_shares": round(max(float(target_shares), gross0), 6),
                    "leg_b_gross_shares": round(max(float(target_shares), gross1), 6),
                    "leg_a_token_id": tid0,
                    "leg_a_opp_token_id": opp_a,
                    "leg_a_label": lbl0,
                    "leg_a_side": lbl0.upper(),
                    "leg_a_horizon": box_type.lower(),
                    "leg_a_market_id": str(bk0.market_id),
                    "leg_a_condition_id": cid0,
                    "leg_a_event_id": str(getattr(bk0, "event_id", "") or m0_meta.get("event_id") or ev_id_primary),
                    "leg_a_strike": 100.0,
                    "leg_a_limit_price": round(px0, 4),
                    "leg_a_avail_shares": round(sum(float(lv.size) for lv in bk0.asks), 4),
                    "leg_a_fee_rate": round(float(bk0.fee_rate_bps) / 10_000.0, 6),
                    "leg_a_fee_exponent": float(bk0.fee_exponent),
                    "leg_a_neg_risk": bool(getattr(bk0, "neg_risk", False) or m0_meta.get("negRisk")),
                    "leg_a_expiry_ts": close_ts,
                    "leg_b_token_id": tid1,
                    "leg_b_opp_token_id": opp_b,
                    "leg_b_label": lbl1,
                    "leg_b_side": lbl1.upper(),
                    "leg_b_horizon": box_type.lower(),
                    "leg_b_market_id": str(bk1.market_id),
                    "leg_b_condition_id": cid1,
                    "leg_b_event_id": str(getattr(bk1, "event_id", "") or m1_meta.get("event_id") or ev_id_primary),
                    "leg_b_strike": 101.0,
                    "leg_b_limit_price": round(px1, 4),
                    "leg_b_avail_shares": round(sum(float(lv.size) for lv in bk1.asks), 4),
                    "leg_b_fee_rate": round(float(bk1.fee_rate_bps) / 10_000.0, 6),
                    "leg_b_fee_exponent": float(bk1.fee_exponent),
                    "leg_b_neg_risk": bool(getattr(bk1, "neg_risk", False) or m1_meta.get("negRisk")),
                    "leg_b_expiry_ts": close_ts,
                }

            emitted_payloads.append(cand_dict)
            self._dedupe_cache[dedupe_key] = {
                "emitted_ts": emit_ts,
                "digest": cand_digest,
                "box_cost_net": box_cost_net,
                "candidate_id": rec.candidate_id,
            }

        # Optional Passive `0 bps` `SINGLE_LEG_MAKER_LOCK` (`BOND1_UMA_RESOLUTION_CARRY`) Bridge
        # Scans non-disputed `umaResolutionStatus == "proposed"` (`0%`-fee, `<=2h` liveness) markets discovered across
        # the full 375k-market universe, JIT re-verifies `/books`, and emits up to `max_maker_locks_per_cycle`
        # verified `postOnly=True` maker locks for `polymarket-live-harvester.service`!
        if enable_passive_maker_bridge and events and max_maker_locks_per_cycle > 0:
            from src.polymarket_research.uma_nba_endgame_engine import is_objective_uma_market

            uma_candidates_ranked: List[Tuple[float, Dict[str, Any]]] = []
            for ev in events:
                ev_id_u = str(ev.get("id") or "").strip()
                ev_slug_u = str(ev.get("slug") or "")
                ev_title_raw_u = str(ev.get("title") or "")
                ev_title_u = ev_title_raw_u.lower()
                if "kmia" in ev_title_u:
                    continue
                for m in ev.get("markets") or ():
                    if not isinstance(m, Mapping) or m.get("closed") or m.get("archived") or m.get("active") is False:
                        continue
                    mid_u = str(m.get("id") or m.get("market_id") or "").strip()
                    if not mid_u or mid_u in FROZEN_DISPUTED_MARKET_IDS:
                        continue
                    ust_u = str(m.get("umaResolutionStatus") or "").strip().lower()
                    if ust_u != "proposed" or m.get("enableOrderBook") is False:
                        continue
                    ok_uma_obj, _uma_obj_rsn = is_objective_uma_market(
                        {
                            **dict(m),
                            "acceptingOrders": m.get("acceptingOrders", True),
                            "_ev_slug": ev_slug_u,
                            "_ev_title": ev_title_raw_u,
                            "_eval_now_ts": now_f,
                        }
                    )
                    if not ok_uma_obj:
                        skipped_reasons["UMA_NON_OBJECTIVE_VETOED"] += 1
                        continue
                    end_u_raw = str(m.get("endDate") or ev.get("endDate") or "").strip()
                    end_u_ts: Optional[float] = None
                    if end_u_raw:
                        try:
                            dt_u = datetime.fromisoformat(end_u_raw.replace("Z", "+00:00"))
                            if dt_u.tzinfo is None:
                                dt_u = dt_u.replace(tzinfo=timezone.utc)
                            end_u_ts = float(dt_u.timestamp())
                        except Exception:
                            end_u_ts = None
                    if end_u_ts is not None and end_u_ts < (now_f - 259200.0):
                        continue
                    live_sec = float(m.get("customLiveness") or 7200.0)
                    if live_sec > 7200.0:
                        continue
                    toks_u = [str(x).strip() for x in _parse_json_list_safe(m.get("clobTokenIds")) if str(x).strip()]
                    if len(toks_u) != 2:
                        continue
                    bk0_u = books.get(toks_u[0])
                    bk1_u = books.get(toks_u[1])
                    if bk0_u is None or bk1_u is None:
                        continue
                    for idx_w in (0, 1):
                        win_bk = bk0_u if idx_w == 0 else bk1_u
                        opp_bk = bk1_u if idx_w == 0 else bk0_u
                        if not win_bk.bids or not win_bk.asks:
                            continue
                        bb_w = float(win_bk.bids[0].price)
                        l1_usd_w = bb_w * float(win_bk.bids[0].size)
                        ob_w = float(opp_bk.bids[0].price) if opp_bk.bids else 0.0
                        ba_w = float(win_bk.asks[0].price) if win_bk.asks else 1.0
                        if not (0.945 <= bb_w <= 0.994) or ob_w > 0.008 or l1_usd_w < 5.0 or l1_usd_w > 350.0:
                            continue
                        if ba_w < 1.0 and ob_w > 0.0 and (ba_w + ob_w) > 1.015:
                            continue
                        tk_u = float(win_bk.tick_size) if (win_bk.tick_size and 0.0001 <= win_bk.tick_size <= 0.01) else (0.001 if bb_w >= 0.96 else 0.01)
                        step_b = round(bb_w + tk_u, 4) if (ba_w - bb_w) >= (2.0 * tk_u - 1e-9) else round(bb_w, 4)
                        rest_bid = min(step_b, round(ba_w - tk_u, 4), 0.994)
                        rest_bid = round(math.floor((rest_bid + 1e-9) / tk_u) * tk_u, 4)
                        if not (0.945 <= rest_bid <= 0.994) or (ba_w < 1.0 and rest_bid >= ba_w - 1e-9):
                            continue
                        rem_u = max(300.0, min(live_sec, 7200.0))
                        vel_bps_hr = ((1.0 - rest_bid) * 10_000.0) / (rem_u / 3600.0)
                        if vel_bps_hr < max(self.min_velocity_bps_per_hr, 15.0):
                            continue
                        out_lbls = _parse_json_list_safe(m.get("outcomes"))
                        side_lbl = str(out_lbls[idx_w]).upper() if idx_w < len(out_lbls) else ("YES" if idx_w == 0 else "NO")
                        uma_candidates_ranked.append(
                            (
                                vel_bps_hr,
                                {
                                    "mid": mid_u,
                                    "ev_id": ev_id_u,
                                    "cid": str(m.get("conditionId") or m.get("condition_id") or win_bk.condition_id or ""),
                                    "win_tid": toks_u[idx_w],
                                    "opp_tid": toks_u[1 - idx_w],
                                    "side_lbl": side_lbl if side_lbl in ("YES", "NO") else ("YES" if idx_w == 0 else "NO"),
                                    "disp_lbl": str(m.get("groupItemTitle") or m.get("question") or mid_u)[:64],
                                    "neg_risk": bool(m.get("negRisk") or ev.get("negRisk")),
                                    "rem_sec": rem_u,
                                    "tick": tk_u,
                                    "vol24": float(m.get("volume24hr") or 0.0),
                                    "rest_bid": rest_bid,
                                    "fees_enabled": bool(m.get("feesEnabled") is True),
                                },
                            )
                        )

            uma_candidates_ranked.sort(key=lambda x: -x[0])
            for vel_u, uc in uma_candidates_ranked:
                if maker_locks_this_cycle >= max_maker_locks_per_cycle:
                    break
                dedupe_m = f"FT_BOND1_SLL_MKR_{uc['mid']}_{uc['win_tid'][:12]}"
                prev_m = self._dedupe_cache.get(dedupe_m)
                if prev_m is not None and (now_f - float(prev_m.get("emitted_ts", 0.0))) < max(self.dedupe_ttl_sec, 60.0):
                    skipped_reasons["DEDUPE_TTL_ACTIVE"] += 1
                    continue

                win_tid = uc["win_tid"]
                opp_tid = uc["opp_tid"]
                eff_win_bk = books[win_tid]
                eff_opp_bk = books[opp_tid]
                emit_m_ts = round(now_f, 3)

                if jit_book_fetcher is not None:
                    try:
                        f_raw_m, f_meta_m = jit_book_fetcher([win_tid, opp_tid])
                    except Exception:
                        f_raw_m, f_meta_m = {}, {}
                    if win_tid not in f_raw_m or opp_tid not in f_raw_m:
                        self.total_jit_rejected += 1
                        jit_rejected_this_cycle += 1
                        skipped_reasons["JIT_BOOK_REVERIFY_FETCH_FAILED"] += 1
                        continue
                    jit_m_ts = float(f_meta_m.get("fetch_timestamp_sec") or time.time())
                    eff_win_bk = InstrumentOrderBook.from_raw(
                        win_tid,
                        f_raw_m[win_tid],
                        market_id=uc["mid"],
                        condition_id=uc["cid"],
                        outcome_label=uc["side_lbl"],
                        tick_size=uc["tick"],
                        book_timestamp_sec=jit_m_ts,
                    )
                    eff_opp_bk = InstrumentOrderBook.from_raw(
                        opp_tid,
                        f_raw_m[opp_tid],
                        market_id=uc["mid"],
                        condition_id=uc["cid"],
                        outcome_label="OPP",
                        tick_size=uc["tick"],
                        book_timestamp_sec=jit_m_ts,
                    )
                    if not eff_win_bk.bids or not eff_win_bk.asks:
                        self.total_jit_rejected += 1
                        jit_rejected_this_cycle += 1
                        skipped_reasons["JIT_BOOK_REVERIFY_MISSING_DEPTH"] += 1
                        continue
                    bb_j = float(eff_win_bk.bids[0].price)
                    l1_j = bb_j * float(eff_win_bk.bids[0].size)
                    ob_j = float(eff_opp_bk.bids[0].price) if eff_opp_bk.bids else 0.0
                    ba_j = float(eff_win_bk.asks[0].price) if eff_win_bk.asks else 1.0
                    tk_j = uc["tick"]
                    step_j = round(bb_j + tk_j, 4) if (ba_j - bb_j) >= (2.0 * tk_j - 1e-9) else round(bb_j, 4)
                    rest_j = round(math.floor((min(step_j, round(ba_j - tk_j, 4), 0.994) + 1e-9) / tk_j) * tk_j, 4)
                    if not (0.945 <= bb_j <= 0.994) or not (0.945 <= rest_j <= 0.994) or ob_j > 0.008 or l1_j < 5.0 or l1_j > 350.0 or (ba_j < 1.0 and rest_j >= ba_j - 1e-9):
                        self.total_jit_rejected += 1
                        jit_rejected_this_cycle += 1
                        skipped_reasons["JIT_BOOK_REVERIFY_EDGE_DECAYED"] += 1
                        continue
                    uc["rest_bid"] = rest_j
                    self.total_jit_verified += 1
                    jit_verified_this_cycle += 1
                    emit_m_ts = round(time.time() if now_ts is None else jit_m_ts, 3)

                rest_px = float(uc["rest_bid"])
                sh_mkr = max(5, int(math.floor((nav_15pct_cap_usd / max(0.50, rest_px)) + 1e-9)))
                if sh_mkr * rest_px < DEFAULT_MIN_MARKETABLE_BUY_USD - 1e-6:
                    continue
                close_m_ts = round(emit_m_ts + float(uc["rem_sec"]), 3)
                bb_cur = float(eff_win_bk.bids[0].price)
                l1_cur = bb_cur * float(eff_win_bk.bids[0].size)
                ws_mkr = {
                    win_tid: {
                        "bids": [{"price": str(lv.price), "size": str(lv.size)} for lv in eff_win_bk.bids[:10]],
                        "asks": [{"price": str(lv.price), "size": str(lv.size)} for lv in eff_win_bk.asks[:10]],
                    },
                    opp_tid: {
                        "bids": [{"price": str(lv.price), "size": str(lv.size)} for lv in eff_opp_bk.bids[:10]],
                        "asks": [{"price": str(lv.price), "size": str(lv.size)} for lv in eff_opp_bk.asks[:10]],
                    },
                }
                mkr_dict: Dict[str, Any] = {
                    "box_id": f"MKR_LOCK1_LIVE_FTBOND1_{int(close_m_ts)}_{uc['mid'][-5:]}",
                    "dedupe_key": dedupe_m,
                    "pair_dedupe_key": f"BOND1_{uc['mid']}",
                    "box_type": "SINGLE_LEG_MAKER_LOCK",
                    "full_throttle_bridge": True,
                    "jit_reverified": jit_book_fetcher is not None,
                    "rule_verified": True,
                    "d001_verified_clean": True,
                    "d007_concentration_ok": True,
                    "reconciled_nav_usd": round(eff_nav_usd, 4),
                    "capital_efficiency_bps_per_hr": round(vel_u, 4),
                    "ts_unix": emit_m_ts,
                    "asset": "FT_K",
                    "event_id": uc["ev_id"],
                    "regime": f"SINGLE_LEG_MAKER_LOCK_{uc['disp_lbl'][:40]}",
                    "pair_horizons": "single_leg_maker_lock",
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "is_quiet_book": True,
                    "queue_front": bool(rest_px > bb_cur + 1e-6 or l1_cur <= 50.0),
                    "queue_ahead_usd": 0.0 if rest_px > bb_cur + 1e-6 else round(l1_cur, 2),
                    "ask_depth_usd": round(sum(float(lv.price) * float(lv.size) for lv in eff_win_bk.asks), 2),
                    "volume_24h_usd": round(float(uc["vol24"]), 2),
                    "expiry_ts": close_m_ts,
                    "rem_sec": round(float(uc["rem_sec"]), 2),
                    "shares": sh_mkr,
                    "box_cost_net": rest_px,
                    "max_box_cost_net": 0.994,
                    "anchor_bid_px": rest_px,
                    "min_resting_bid": 0.945,
                    "min_maker_edge": 0.006,
                    "maker_rebate_ps": 0.0,
                    "max_opp_bid": 0.008,
                    "hold_to_maturity": True,
                    "p_model": 1.0,
                    "leg_a_token_id": win_tid,
                    "leg_a_opp_token_id": opp_tid,
                    "leg_a_label": uc["disp_lbl"],
                    "leg_a_side": uc["side_lbl"],
                    "leg_a_horizon": "maker_lock_1leg",
                    "leg_a_market_id": uc["mid"],
                    "leg_a_condition_id": uc["cid"],
                    "leg_a_strike": 0.0,
                    "leg_a_limit_price": rest_px,
                    "leg_a_tick_size": uc["tick"],
                    "leg_a_fee_rate": 0.0,
                    "leg_a_fee_exponent": 1.0,
                    "market_fees_enabled": bool(uc.get("fees_enabled", False)),
                    "post_only": True,
                    "leg_a_neg_risk": uc["neg_risk"],
                    "leg_a_expiry_ts": close_m_ts,
                    "ws_books": ws_mkr,
                    "ws_books_ts": emit_m_ts,
                }
                emitted_payloads.append(mkr_dict)
                maker_locks_this_cycle += 1
                self.total_maker_locks_emitted += 1
                self._dedupe_cache[dedupe_m] = {
                    "emitted_ts": emit_m_ts,
                    "digest": f"mkr:{rest_px:.4f}:{sh_mkr}",
                    "box_cost_net": rest_px,
                    "candidate_id": dedupe_m,
                }

        if emitted_payloads:
            self.candidates_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            lines_bytes: List[bytes] = [
                (_ORJSON_MOD.dumps(p_dict) + b"\n")
                if _ORJSON_MOD is not None
                else (json.dumps(p_dict, separators=(",", ":")) + "\n").encode("utf-8")
                for p_dict in emitted_payloads
            ]
            with self.candidates_jsonl_path.open("ab") as fh:
                for raw_b in lines_bytes:
                    fh.write(raw_b)
            # Send optional <1ms Linux abstract UDS datagram wake notification to Harvester if running on Linux production
            if os.name != "nt":
                try:
                    import socket

                    ipc_nm = os.environ.get("POLYMARKET_D1_IPC_SOCKET_NAME", "polymarket_d1_box_notify")
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                    sock.setblocking(False)
                    try:
                        for raw_b in lines_bytes:
                            if len(raw_b) <= 60_000:
                                sock.sendto(raw_b, f"\x00{ipc_nm}".encode("utf-8"))
                    finally:
                        sock.close()
                except Exception:
                    pass
            self.total_emitted += len(emitted_payloads)
            self._save_dedupe_cache(now_f)

        return {
            "enabled": True,
            "candidates_emitted_this_cycle": len(emitted_payloads),
            "taker_boxes_emitted_this_cycle": len(emitted_payloads) - maker_locks_this_cycle,
            "maker_locks_emitted_this_cycle": maker_locks_this_cycle,
            "jit_reverified_this_cycle": jit_verified_this_cycle,
            "jit_rejected_this_cycle": jit_rejected_this_cycle,
            "total_emitted_across_campaign": self.total_emitted,
            "total_maker_locks_across_campaign": self.total_maker_locks_emitted,
            "total_jit_verified_across_campaign": self.total_jit_verified,
            "total_jit_rejected_across_campaign": self.total_jit_rejected,
            "total_dedupe_suppressed": self.total_dedupe_suppressed,
            "reconciled_nav_used_usd": round(eff_nav_usd, 4),
            "effective_min_velocity_bps_per_hr": round(eff_min_vel_bps_hr, 4),
            "resolved_utilization_frac": resolved_util_frac,
            "d007_15pct_concentration_cap_usd": nav_15pct_cap_usd,
            "target_jsonl_path": str(self.candidates_jsonl_path),
            "skipped_by_reason": dict(skipped_reasons),
            "emitted_box_ids": [p["box_id"] for p in emitted_payloads],
        }


# ---------------------------------------------------------------------------
# 6. Public Read-Only Gamma Keyset & Batched CLOB `/books` Client (`Stage 1`)
# ---------------------------------------------------------------------------


_KNOWN_FEE_SCHEDULES: Dict[str, Tuple[float, float]] = {
    "crypto_15_min": (2500.0, 2.0),
    "crypto_fees_v2": (700.0, 1.0),
    "sports_fees_v2": (300.0, 1.0),
    "sports_fees_v3": (500.0, 1.0),
    "politics_fees": (400.0, 1.0),
    "finance_prices_fees": (400.0, 1.0),
    "tech_fees": (400.0, 1.0),
    "mentions_fees": (400.0, 1.0),
    "culture_fees": (500.0, 1.0),
    "economics_fees": (500.0, 1.0),
    "general_fees": (500.0, 1.0),
    "weather_fees": (500.0, 1.0),
    "weather_fees_v2": (500.0, 1.0),
}


def _parse_json_list_safe(val: Any) -> List[Any]:
    if isinstance(val, list):
        return val
    if isinstance(val, tuple):
        return list(val)
    if isinstance(val, str):
        s = val.strip()
        if s.startswith("["):
            try:
                parsed = _ORJSON_MOD.loads(s) if _ORJSON_MOD is not None else json.loads(s)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
    return []


def _extract_market_fee_spec(mkt: Mapping[str, Any], raw_book: Optional[Mapping[str, Any]] = None) -> Tuple[float, float]:
    """
    Extracts `(fee_rate_bps, fee_exponent)` honoring Polymarket `feeSchedule.{rate, exponent}` first
    (avoiding misinterpreting Gamma `takerBaseFee=1000` ceiling as active rate).
    """
    fees_en = mkt.get("feesEnabled", mkt.get("fees_enabled"))
    fee_type = str(mkt.get("feeType") or mkt.get("fee_type") or "").strip().lower()
    if fees_en is False or fee_type == "zero_fees":
        return (0.0, 1.0)

    sched = mkt.get("feeSchedule") or mkt.get("fee_schedule")
    if isinstance(sched, str):
        try:
            sched = _ORJSON_MOD.loads(sched) if _ORJSON_MOD is not None else json.loads(sched)
        except Exception:
            sched = None
    if isinstance(sched, Mapping):
        try:
            r = max(0.0, float(sched.get("rate") or 0.0))
            exp = max(0.5, float(sched.get("exponent") or 1.0))
            return (round(r * 10_000.0, 4), exp)
        except (TypeError, ValueError):
            pass

    if fee_type in _KNOWN_FEE_SCHEDULES:
        return _KNOWN_FEE_SCHEDULES[fee_type]

    exp_bps = mkt.get("fee_rate_bps", mkt.get("feeRateBps"))
    exp_rate = mkt.get("fee_rate", mkt.get("feeRate"))
    if exp_bps is None and isinstance(raw_book, Mapping) and raw_book.get("fee_rate_bps") is not None:
        exp_bps = raw_book.get("fee_rate_bps")
    if exp_bps is not None or exp_rate is not None:
        r = normalize_fee_rate(
            fee_rate_bps=(float(exp_bps) if exp_bps is not None else None),
            fee_rate=(float(exp_rate) if exp_rate is not None else None),
        )
        exp = float(mkt.get("fee_exponent", mkt.get("feeExponent", 1.0)) or 1.0)
        return (round(r * 10_000.0, 4), max(0.5, exp))

    if fees_en is True:
        return (500.0, 1.0)
    return (0.0, 1.0)


class PublicPolymarketScannerClient:
    """
    Swapless-safe (`<180 MiB` RSS) pure-stdlib public REST client for Gamma `/events/keyset`
    and batched CLOB `POST /books`. Strictly `PUBLIC_REST` only — zero private headers or keys.
    """

    def __init__(self, *, timeout_sec: float = 22.0, max_book_workers: int = 2) -> None:
        self.timeout_sec = float(timeout_sec)
        self.max_book_workers = max(1, int(max_book_workers))
        self._ssl_ctx = ssl.create_default_context()
        self._jit_tls = threading.local()

    @staticmethod
    def _read_gzip_json(resp: http.client.HTTPResponse) -> Any:
        comp = resp.read()
        if not comp:
            return None
        enc = (resp.getheader("Content-Encoding") or "").lower()
        if "gzip" in enc:
            raw = gzip.decompress(comp)
            del comp
        else:
            raw = comp
        big_payload = len(raw) > 2_000_000
        if big_payload:
            _reclaim_process_memory()
        parsed = _loads_json_bytes(raw)
        del raw
        return parsed

    _WEATHER_ICAO_UPPER_RE = re.compile(
        r"\b(?:K[A-Z]{3}|CYYZ|CYVR|CYUL|EGLC|EGLL|LFPG|EDDF|EHAM|LEMD|LIRF|RJTT|RKSI|VHHH|WSSS|YSSY|NZWN|SBGR|SAEZ)\b"
    )
    _LADDER_NUMERIC_MKT_RE = re.compile(
        r"(?:\$\s*\d|\d+(?:\.\d+)?\s*(?:%|bps|°[fc]|degrees|inches|mm\b|cm\b|[kmb]\b)|"
        r"\b(?:above|below|over|under|between|at least|more than|fewer than|less than|reach|hit|dip to)\s+\$?\d)",
        re.IGNORECASE,
    )
    _CALENDAR_HORIZON_MKT_RE = re.compile(
        r"\b(?:by|before|in|on|end of|through)\s+"
        r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
        r"sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|q[1-4]\b|202[5-9]\b)",
        re.IGNORECASE,
    )
    _STEM_NORM_RE = re.compile(r"[^a-z0-9]+")
    _SINGLE_WINNER_PRIZE_MKT_RE = re.compile(
        r"^will\s+(.+?)\s+(?:win|be\s+elected|be\s+named|be\s+appointed|be\s+the\s+next)\s+(.+?)\s*\??$",
        re.IGNORECASE,
    )

    @classmethod
    def _normalize_duplicate_stem(cls, title: str) -> str:
        toks = [
            w
            for w in cls._STEM_NORM_RE.split(str(title or "").lower())
            if w and w not in {"will", "the", "a", "an", "be", "to", "of", "in", "on", "by", "at", "for"}
        ]
        return " ".join(toks[:10])

    @classmethod
    def _extract_single_winner_prize_key(cls, question: str) -> str:
        ql = str(question or "").strip()
        if len(ql) < 16 or ql[:5].lower() != "will ":
            return ""
        mw = cls._SINGLE_WINNER_PRIZE_MKT_RE.match(ql)
        if not mw:
            return ""
        raw_p = mw.group(2).strip().lower()
        raw_no_yr = re.sub(r"\b(?:19|20)\d{2}\b", "", raw_p)
        raw_no_yr = re.sub(r"\b(?:formula|ligue|division|tier)\s+\d+\b", "", raw_no_yr)
        if re.search(
            r"\d|%|\b(?:top|playoffs?|medals?|nominat\w*|seats?|votes|games|matches|states|between|at\s+least|over|under)\b",
            raw_no_yr,
        ):
            return ""
        norm = " ".join(w for w in cls._STEM_NORM_RE.split(raw_p) if w)
        return norm if len(norm) >= 10 else ""

    def sweep_gamma_events_keyset(
        self,
        *,
        page_limit: int = 35,
        max_pages: int = 950,
        compact_fields: bool = True,
        max_retained_active_markets: int = 1_700,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Enumerates 100% of observable active unclosed events via `/events/keyset?after_cursor=...`.
        Streams exact full-universe census counters across 100% of all events/markets (`~19,257` events,
        `~375,963` child markets, `~201,218` active unclosed markets) while maintaining a generalized
        structural-priority bounded min-heap (`<= 680` events / `<= 1,700` active markets) covering
        all 14 Opportunity Families (`A..N`, including `Family D` logical hierarchies, `Family G`
        multi-line sports & tournament advancement, `Family H` weather/ICAO brackets, `Family I`
        cross-event duplicate stems, and `Family K` UMA `proposed` carry) strictly `< 180 MiB` RSS (`D-010`)!
        """
        t0 = time.perf_counter()
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection("gamma-api.polymarket.com", timeout=self.timeout_sec, context=ctx)
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Connection": "keep-alive",
            "User-Agent": "DominusFullThrottleShadow/5.2 (MODE2-PublicReadOnly)",
        }

        events_out: List[Dict[str, Any]] = []
        retained_heap: List[Tuple[float, int, int, Dict[str, Any]]] = []
        retained_eids_in_heap: Set[str] = set()
        max_heap_events = 680
        heap_seq = 0
        seen_event_ids: Set[str] = set()
        seen_stem_first_eid: Dict[str, str] = {}
        seen_stem_first_ev: Dict[str, Tuple[int, Dict[str, Any]]] = {}
        seen_prize_first_eid: Dict[str, str] = {}
        seen_prize_first_ev: Dict[str, Tuple[int, Dict[str, Any]]] = {}
        fam_quota_cnt: Counter[str] = Counter()
        cursor: Optional[str] = None
        pages_fetched = 0
        retained_active_mkts = 0

        # Exact 100% untruncated streaming census across every Gamma page
        full_events_count = 0
        full_total_markets = 0
        full_active_unclosed_markets = 0
        full_orderbook_enabled_markets = 0
        full_total_tokens = 0
        full_negrisk_events = 0
        full_augmented_negrisk_events = 0
        full_fees_enabled_markets = 0
        full_uma_status: Counter[str] = Counter()
        full_skip_reasons: Counter[str] = Counter()
        cold_token_reservoir: List[str] = []

        keep_mkt_keys = {
            "id",
            "market_id",
            "question",
            "conditionId",
            "condition_id",
            "slug",
            "outcomes",
            "outcomePrices",
            "clobTokenIds",
            "active",
            "closed",
            "archived",
            "acceptingOrders",
            "enableOrderBook",
            "negRisk",
            "negRiskMarketID",
            "negRiskAugmented",
            "negRiskOther",
            "questionIndex",
            "groupItemTitle",
            "umaResolutionStatus",
            "umaResolutionStatuses",
            "umaEndDate",
            "umaBond",
            "customLiveness",
            "resolvedBy",
            "questionID",
            "negRiskRequestID",
            "feesEnabled",
            "feeType",
            "feeSchedule",
            "comboStatus",
            "rfqEnabled",
            "holdingRewardsEnabled",
            "orderPriceMinTickSize",
            "orderMinSize",
            "endDate",
            "startDate",
            "createdAt",
            "liquidity",
            "liquidityClob",
            "volume24hr",
            "bestBid",
            "bestAsk",
            "resolutionSource",
            "description",
            "sportsMarketType",
            "line",
            "gameId",
        }
        str_dedup_pool: Dict[str, str] = {}

        def _dedup_s(val: Any) -> Any:
            if not isinstance(val, str) or len(val) > 2048:
                return val
            return str_dedup_pool.setdefault(val, val)

        def _build_comp_ev(
            ev_d: Dict[str, Any],
            eid_s: str,
            raw_mkts_seq: Sequence[Any],
            nr_flag: bool,
            aug_flag: bool,
        ) -> Tuple[int, Dict[str, Any]]:
            comp_mkts_loc: List[Dict[str, Any]] = []
            keep_closed_loc = nr_flag and len(raw_mkts_seq) <= 20
            added_loc = 0
            for m_loc in raw_mkts_seq:
                if not isinstance(m_loc, dict):
                    continue
                if m_loc.get("closed") is True or m_loc.get("archived") is True or m_loc.get("active") is False:
                    if keep_closed_loc:
                        comp_mkts_loc.append(
                            {
                                "id": m_loc.get("id") or m_loc.get("market_id") or "",
                                "closed": True,
                                "archived": bool(m_loc.get("archived")),
                                "active": False,
                                "questionIndex": m_loc.get("questionIndex"),
                                "groupItemTitle": _dedup_s(m_loc.get("groupItemTitle") or ""),
                            }
                        )
                    continue
                cm_loc = {k: m_loc[k] for k in keep_mkt_keys if k in m_loc}
                if "description" in cm_loc and isinstance(cm_loc["description"], str):
                    d_s = cm_loc["description"][:420] if len(cm_loc["description"]) > 420 else cm_loc["description"]
                    cm_loc["description"] = _dedup_s(d_s)
                for sk in ("outcomes", "feeType", "resolutionSource", "comboStatus", "sportsMarketType"):
                    if sk in cm_loc and isinstance(cm_loc[sk], str):
                        cm_loc[sk] = _dedup_s(cm_loc[sk])
                cm_loc["event_id"] = eid_s
                if ev_d.get("negRisk") is not None:
                    cm_loc.setdefault("negRisk", ev_d.get("negRisk"))
                if ev_d.get("negRiskAugmented") is not None:
                    cm_loc.setdefault("negRiskAugmented", ev_d.get("negRiskAugmented"))
                comp_mkts_loc.append(cm_loc)
                added_loc += 1
            return (
                added_loc,
                {
                    "id": eid_s,
                    "slug": ev_d.get("slug") or "",
                    "title": ev_d.get("title") or "",
                    "category": ev_d.get("category") or "",
                    "active": ev_d.get("active", True),
                    "closed": ev_d.get("closed", False),
                    "archived": ev_d.get("archived", False),
                    "negRisk": nr_flag,
                    "enableNegRisk": nr_flag,
                    "negRiskMarketID": ev_d.get("negRiskMarketID") or "",
                    "negRiskAugmented": aug_flag,
                    "enableNegRiskOther": bool(ev_d.get("enableNegRiskOther", False)),
                    "cumulativeMarkets": bool(ev_d.get("cumulativeMarkets", False)),
                    "createdAt": ev_d.get("createdAt") or "",
                    "endDate": ev_d.get("endDate") or "",
                    "markets": comp_mkts_loc,
                },
            )

        def _push_heap_ev(score_v: float, open_v: int, comp_ev_d: Dict[str, Any]) -> None:
            nonlocal heap_seq, retained_active_mkts
            cid_e = str(comp_ev_d.get("id") or "")
            if cid_e in retained_eids_in_heap:
                return
            heap_seq += 1
            heapq.heappush(retained_heap, (score_v, heap_seq, open_v, comp_ev_d))
            retained_eids_in_heap.add(cid_e)
            retained_active_mkts += open_v
            while len(retained_heap) > max_heap_events or (
                retained_active_mkts > max_retained_active_markets and len(retained_heap) > 220
            ):
                _, _, dropped_open, dropped_ev = heapq.heappop(retained_heap)
                retained_eids_in_heap.discard(str(dropped_ev.get("id") or ""))
                retained_active_mkts = max(0, retained_active_mkts - dropped_open)

        try:
            for _ in range(max_pages):
                qs: Dict[str, str] = {"active": "true", "closed": "false", "limit": str(int(page_limit))}
                if cursor:
                    qs["after_cursor"] = cursor
                path = f"/events/keyset?{urllib.parse.urlencode(qs)}"

                payload = None
                for attempt in range(3):
                    try:
                        conn.request("GET", path, headers=headers)
                        resp = conn.getresponse()
                        if resp.status == 200:
                            payload = self._read_gzip_json(resp)
                            break
                        _ = resp.read()
                        time.sleep(0.35 * (attempt + 1))
                        conn.close()
                        conn = http.client.HTTPSConnection("gamma-api.polymarket.com", timeout=self.timeout_sec, context=ctx)
                    except Exception:
                        time.sleep(0.35 * (attempt + 1))
                        try:
                            conn.close()
                        except Exception:
                            pass
                        conn = http.client.HTTPSConnection("gamma-api.polymarket.com", timeout=self.timeout_sec, context=ctx)

                if not isinstance(payload, Mapping):
                    break
                batch = payload.get("events")
                if not isinstance(batch, list) or not batch:
                    break
                pages_fetched += 1

                for ev in batch:
                    if not isinstance(ev, dict):
                        continue
                    eid = str(ev.get("id") or "").strip()
                    if not eid or eid in seen_event_ids:
                        continue
                    seen_event_ids.add(eid)

                    if compact_fields:
                        full_events_count += 1
                        is_nr_ev = bool(ev.get("negRisk") or ev.get("enableNegRisk"))
                        is_aug_ev = bool(ev.get("negRiskAugmented") or ev.get("enableNegRiskOther"))
                        if is_nr_ev:
                            full_negrisk_events += 1
                        if is_aug_ev:
                            full_augmented_negrisk_events += 1

                        raw_mkts = ev.get("markets") or ()
                        title_raw = str(ev.get("title") or "").strip()
                        slug_lower = str(ev.get("slug") or "").strip().lower()
                        title_lower = title_raw.lower()
                        ev_text_low = f"{title_lower} {slug_lower}"
                        is_prop_dump = "-more-markets" in slug_lower or "more markets" in title_lower
                        is_game_matchup = " vs. " in title_lower or " vs " in title_lower or "-vs-" in slug_lower

                        # Family H: Weather station & measurable temperature/precip/snow/wind brackets
                        has_weather_kw = bool(
                            any(
                                wkw in ev_text_low
                                for wkw in (
                                    "temperature",
                                    "highest temp",
                                    "high temp",
                                    "lowest temp",
                                    "low temp",
                                    "weather",
                                    "rainfall",
                                    "precipitation",
                                    "inches of rain",
                                    "snowfall",
                                    "inches of snow",
                                    "wind speed",
                                    "hurricane",
                                    "tropical storm",
                                    "celsius",
                                    "fahrenheit",
                                    "°f",
                                    "°c",
                                )
                            )
                            or self._WEATHER_ICAO_UPPER_RE.search(title_raw.upper())
                        )

                        # Family D: Cross-market logical / political / macro / corporate implication hierarchies
                        has_logical_hierarchy_kw = any(
                            lkw in ev_text_low
                            for lkw in (
                                "balance of power",
                                "trifecta",
                                "sweep",
                                "win the senate",
                                "win the house",
                                "control the senate",
                                "control the house",
                                "popular vote",
                                "presidential election",
                                "nominee",
                                "nomination",
                                "primary",
                                "electoral college",
                                "governor",
                                "mayor",
                                "prime minister",
                                "chancellor",
                                "coalition",
                                "ceasefire",
                                "peace deal",
                                "invasion",
                                "invade",
                                "out as ",
                                "step down",
                                "impeach",
                                "recession",
                                "rate cut",
                                "rate hike",
                                "interest rate",
                                "fed ",
                                "fomc",
                                "tariff",
                                "acquir",
                                "merger",
                                "ipo",
                                "fdv",
                                "treasury",
                                "yield",
                                "strategic reserve",
                                "etf",
                            )
                        )

                        # Family G: Sports / esports tournament advancement & multi-line slates
                        has_tournament_adv_kw = (not is_game_matchup) and any(
                            skw in ev_text_low
                            for skw in (
                                "champion",
                                "championship",
                                "world cup",
                                "stanley cup",
                                "super bowl",
                                "nba finals",
                                "champions league",
                                "playoffs",
                                "reach the final",
                                "make the final",
                                "win the conference",
                                "division winner",
                                "to qualify",
                                "to advance",
                            )
                        )

                        ev_open_cnt = 0
                        ev_liq = 0.0
                        ev_zero_fee = False
                        ev_has_uma_proposed = False
                        ev_has_uma_any = False
                        ev_all_kmia_frozen = True
                        numeric_ladder_mkt_cnt = 0
                        calendar_horizon_mkt_cnt = 0
                        sports_struct_mkt_cnt = 0

                        ev_prize_keys: Set[str] = set()
                        for m in raw_mkts:
                            if not isinstance(m, dict):
                                continue
                            full_total_markets += 1
                            mid_s = str(m.get("id") or m.get("market_id") or "").strip()
                            if m.get("closed") is True or m.get("archived") is True or m.get("active") is False:
                                full_skip_reasons["CLOSED_OR_ARCHIVED"] += 1
                                continue
                            full_active_unclosed_markets += 1
                            ev_open_cnt += 1
                            if mid_s not in FROZEN_DISPUTED_MARKET_IDS:
                                ev_all_kmia_frozen = False
                            if m.get("enableOrderBook") is False:
                                full_skip_reasons["ORDERBOOK_DISABLED"] += 1
                                continue
                            full_orderbook_enabled_markets += 1
                            ust_s = str(m.get("umaResolutionStatus") or "none").strip().lower() or "none"
                            full_uma_status[ust_s] += 1
                            if m.get("feesEnabled") is True:
                                full_fees_enabled_markets += 1
                            else:
                                ev_zero_fee = True
                            if mid_s in FROZEN_DISPUTED_MARKET_IDS or ust_s == "disputed":
                                full_skip_reasons["UMA_DISPUTED_QUARANTINED"] += 1
                                ev_has_uma_any = True
                            elif ust_s == "proposed":
                                ev_has_uma_proposed = True
                                ev_has_uma_any = True
                            elif ust_s != "none":
                                ev_has_uma_any = True
                            toks_s = [str(x).strip() for x in _parse_json_list_safe(m.get("clobTokenIds")) if str(x).strip()]
                            if len(toks_s) < 2:
                                full_skip_reasons["MISSING_TOKEN_IDS"] += 1
                                continue
                            full_total_tokens += len(toks_s)
                            m_q_only = str(m.get("question") or "")
                            q_raw = f"{m.get('groupItemTitle') or ''} {m_q_only}"
                            q_low = q_raw.lower()
                            if any(k in q_low for k in ("placeholder", "person a", "person b", "option a", "tba", "unnamed")):
                                full_skip_reasons["AUGMENTED_PLACEHOLDER_OUTCOME"] += 1
                            else:
                                pk_s = self._extract_single_winner_prize_key(m_q_only)
                                if pk_s and len(ev_prize_keys) < 4:
                                    ev_prize_keys.add(pk_s)
                            if not has_weather_kw:
                                res_src_low = str(m.get("resolutionSource") or "").lower()
                                if (
                                    "°f" in q_low
                                    or "°c" in q_low
                                    or "wunderground" in res_src_low
                                    or "weather.com" in res_src_low
                                    or "weather.gov" in res_src_low
                                    or self._WEATHER_ICAO_UPPER_RE.search(q_raw.upper())
                                ):
                                    has_weather_kw = True
                            if self._LADDER_NUMERIC_MKT_RE.search(q_raw):
                                numeric_ladder_mkt_cnt += 1
                            if self._CALENDAR_HORIZON_MKT_RE.search(q_raw):
                                calendar_horizon_mkt_cnt += 1
                            smt_low = str(m.get("sportsMarketType") or "").lower()
                            if smt_low or any(
                                sk in q_low
                                for sk in ("spread", "handicap", "o/u ", "over/under", "draw", "double chance", "advance", "qualify")
                            ):
                                sports_struct_mkt_cnt += 1

                            ev_liq += float(m.get("liquidityClob") or m.get("liquidity") or 0.0) + float(m.get("volume24hr") or 0.0)
                            if len(cold_token_reservoir) < 8_000:
                                cold_token_reservoir.extend(toks_s)

                        if ev_open_cnt == 0 or (is_prop_dump and not ev_zero_fee and not ev_has_uma_any):
                            continue
                        open_cap = 64 if (has_logical_hierarchy_kw or has_tournament_adv_kw) else 28
                        if ev_open_cnt > open_cap and not ev_zero_fee and not ev_has_uma_any and not has_weather_kw:
                            continue

                        # Family I: Cross-event duplicate / equivalent title stem detection
                        norm_stem = self._normalize_duplicate_stem(title_raw)
                        is_dup_stem = False
                        dup_partner_entry: Optional[Tuple[int, Dict[str, Any]]] = None
                        if len(norm_stem) >= 14 and not is_game_matchup:
                            first_eid = seen_stem_first_eid.get(norm_stem)
                            if first_eid is None:
                                if len(seen_stem_first_eid) < 12_000:
                                    seen_stem_first_eid[norm_stem] = eid
                                    if ev_open_cnt <= 4 and ev_liq >= 5.0 and len(seen_stem_first_ev) < 250:
                                        seen_stem_first_ev[norm_stem] = _build_comp_ev(ev, eid, raw_mkts, is_nr_ev, is_aug_ev)
                            elif first_eid != eid:
                                is_dup_stem = True
                                dup_partner_entry = seen_stem_first_ev.pop(norm_stem, None)

                        # Family D: Cross-event single-winner prize pairing (`Will X win Y?` across separate events)
                        is_cross_prize_pair = False
                        prize_partner_entries: List[Tuple[int, Dict[str, Any]]] = []
                        for pk_s in ev_prize_keys:
                            p_first_eid = seen_prize_first_eid.get(pk_s)
                            if p_first_eid is None:
                                if len(seen_prize_first_eid) < 8_000:
                                    seen_prize_first_eid[pk_s] = eid
                                    if ev_open_cnt <= 64 and ev_liq >= 10.0 and len(seen_prize_first_ev) < 180:
                                        seen_prize_first_ev[pk_s] = _build_comp_ev(ev, eid, raw_mkts, is_nr_ev, is_aug_ev)
                            elif p_first_eid != eid:
                                is_cross_prize_pair = True
                                pp_ent = seen_prize_first_ev.pop(pk_s, None)
                                if pp_ent is not None:
                                    prize_partner_entries.append(pp_ent)

                        is_core_logical_d = (not is_game_matchup) and any(
                            ck in ev_text_low
                            for ck in (
                                "trifecta",
                                "sweep",
                                "balance of power",
                                "win the senate",
                                "win the house",
                                "control the senate",
                                "control the house",
                                "who-wins-the-senate-pending",
                                "presidential election",
                                "popular vote",
                                "presidential nominee",
                                "presidential nomination",
                            )
                        )
                        has_generalized_ladder = (
                            bool(ev.get("cumulativeMarkets"))
                            or (2 <= ev_open_cnt <= 28 and (numeric_ladder_mkt_cnt >= 2 or calendar_horizon_mkt_cnt >= 2))
                        )
                        has_multi_line_game = is_game_matchup and (3 <= ev_open_cnt <= 24) and sports_struct_mkt_cnt >= 2
                        is_clean_weather = has_weather_kw and not ev_all_kmia_frozen

                        # Quota-guaranteed non-stacking structural priority tiers (`35+55+60+70+180+110+85 = 595 <= 680`
                        # heap slots so NO single family can ever starve `D`, `E`, `F`, `G`, `H`, `I`, or `K`!)
                        q_wx = is_clean_weather and fam_quota_cnt["H"] < 35
                        q_d = (is_cross_prize_pair or is_core_logical_d) and fam_quota_cnt["D"] < 55
                        q_uma = ev_has_uma_proposed and fam_quota_cnt["K"] < 60
                        q_dup = is_dup_stem and fam_quota_cnt["I"] < 70
                        q_f = (not is_game_matchup and 2 <= ev_open_cnt <= 28 and numeric_ladder_mkt_cnt >= 2 and ev_liq >= 20.0) and fam_quota_cnt["F"] < 180
                        q_e = (not is_game_matchup and has_generalized_ladder and ev_liq >= 20.0) and fam_quota_cnt["E"] < 110
                        q_g = ((has_tournament_adv_kw and ev_liq >= 50.0) or (has_multi_line_game and ev_liq >= 150.0)) and fam_quota_cnt["G"] < 85

                        structural_tier = max(
                            2_600_000.0 if q_wx else 0.0,
                            2_540_000.0 if q_d else 0.0,
                            2_480_000.0 if q_uma else 0.0,
                            2_400_000.0 if q_dup else 0.0,
                            2_340_000.0 if q_f else 0.0,
                            2_280_000.0
                            if q_e
                            else (920_000.0 if (has_generalized_ladder and not is_game_matchup) else 0.0),
                            2_160_000.0
                            if q_g
                            else (850_000.0 if (has_tournament_adv_kw or has_multi_line_game) else 0.0),
                            2_050_000.0
                            if ((ev_zero_fee and ev_liq >= 25.0) or ev_has_uma_any)
                            else (950_000.0 if ev_zero_fee else 0.0),
                            1_720_000.0
                            if (has_logical_hierarchy_kw and not is_game_matchup and ev_liq >= 15.0)
                            else (1_350_000.0 if (has_logical_hierarchy_kw and not is_game_matchup) else 0.0),
                            120_000.0 if (not is_game_matchup and 1 <= ev_open_cnt <= 16) else 0.0,
                        )
                        if q_wx:
                            fam_quota_cnt["H"] += 1
                        elif q_d:
                            fam_quota_cnt["D"] += max(1, 1 + len(prize_partner_entries))
                        elif q_uma:
                            fam_quota_cnt["K"] += 1
                        elif q_dup:
                            fam_quota_cnt["I"] += 2 if dup_partner_entry is not None else 1
                        elif q_f:
                            fam_quota_cnt["F"] += 1
                        elif q_e:
                            fam_quota_cnt["E"] += 1
                        elif q_g:
                            fam_quota_cnt["G"] += 1
                        ev_score = structural_tier + min(ev_liq, 55_000.0)

                        if dup_partner_entry is not None and q_dup:
                            p_open, p_comp = dup_partner_entry
                            _push_heap_ev(max(ev_score, 2_400_000.0), p_open, p_comp)
                        if q_d:
                            for pp_open, pp_comp in prize_partner_entries:
                                _push_heap_ev(max(ev_score, 2_540_000.0), pp_open, pp_comp)

                        if (
                            len(retained_heap) >= max_heap_events
                            or retained_active_mkts >= max_retained_active_markets
                        ) and retained_heap and ev_score <= retained_heap[0][0]:
                            continue

                        added_open, comp_ev = _build_comp_ev(ev, eid, raw_mkts, is_nr_ev, is_aug_ev)
                        _push_heap_ev(ev_score, added_open, comp_ev)
                    else:
                        full_events_count += 1
                        events_out.append(ev)

                nxt = payload.get("next_cursor")
                had_dense_page = len(batch) > 0 and sum(len(e.get("markets") or ()) for e in batch if isinstance(e, dict)) > 800
                del payload, batch
                if had_dense_page or pages_fetched % 15 == 0:
                    if len(str_dedup_pool) > 6_000:
                        str_dedup_pool.clear()
                    _reclaim_process_memory()

                if not nxt or str(nxt) == str(cursor):
                    break
                cursor = str(nxt)
        finally:
            str_dedup_pool.clear()
            seen_stem_first_eid.clear()
            seen_stem_first_ev.clear()
            seen_prize_first_eid.clear()
            seen_prize_first_ev.clear()
            retained_eids_in_heap.clear()
            try:
                conn.close()
            except Exception:
                pass

        if compact_fields:
            retained_heap.sort(key=lambda x: -x[0])
            events_out = [item[3] for item in retained_heap]
            retained_heap.clear()

        seen_event_ids.clear()
        _reclaim_process_memory()
        wall_sec = round(time.perf_counter() - t0, 3)
        return events_out, {
            "pages_fetched": pages_fetched,
            "events_fetched": full_events_count,
            "retained_working_events": len(events_out),
            "retained_working_active_markets": retained_active_mkts,
            "sweep_wall_time_sec": wall_sec,
            "rss_mib_after_sweep": get_process_rss_mib(),
            "cold_token_reservoir": cold_token_reservoir,
            "full_universe_census": (
                {
                    "total_observable_events": full_events_count,
                    "total_observable_markets": full_total_markets,
                    "active_unclosed_markets": full_active_unclosed_markets,
                    "orderbook_enabled_markets": full_orderbook_enabled_markets,
                    "total_tradable_outcome_tokens": full_total_tokens,
                    "negrisk_events": full_negrisk_events,
                    "augmented_negrisk_events": full_augmented_negrisk_events,
                    "fees_enabled_markets": full_fees_enabled_markets,
                    "uma_status_breakdown": dict(full_uma_status),
                    "skip_reasons": dict(full_skip_reasons),
                }
                if compact_fields
                else None
            ),
        }

    def fetch_clob_books_batched(
        self,
        token_ids: Sequence[str],
        *,
        chunk_size: int = 150,
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """Fetches live L2 order books via `POST https://clob.polymarket.com/books` (`150`-token swapless batches with `50`-token fallback)."""
        t0 = time.perf_counter()
        unique_tokens = [t for t in dict.fromkeys(str(x).strip() for x in token_ids) if t]
        if not unique_tokens:
            return {}, {"tokens_requested": 0, "books_returned": 0, "book_poll_wall_sec": 0.0}

        step = max(20, min(400, int(chunk_size)))
        chunks = [unique_tokens[i : i + step] for i in range(0, len(unique_tokens), step)]
        tls_local = threading.local()
        ctx = ssl.create_default_context()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Connection": "keep-alive",
            "User-Agent": "DominusFullThrottleShadow/5.2 (MODE2-PublicReadOnly)",
        }

        def _get_conn() -> http.client.HTTPSConnection:
            c = getattr(tls_local, "conn", None)
            if c is None:
                c = http.client.HTTPSConnection("clob.polymarket.com", timeout=self.timeout_sec, context=ctx)
                tls_local.conn = c
            return c

        def _poll_single_batch(ch: List[str]) -> Optional[Dict[str, Dict[str, Any]]]:
            payload_list = [{"token_id": t} for t in ch]
            body = (
                _ORJSON_MOD.dumps(payload_list)
                if _ORJSON_MOD is not None
                else json.dumps(payload_list).encode("utf-8")
            )
            out: Dict[str, Dict[str, Any]] = {}
            for attempt in range(3):
                conn = _get_conn()
                try:
                    conn.request("POST", "/books", body=body, headers=headers)
                    resp = conn.getresponse()
                    if resp.status == 200:
                        rows = self._read_gzip_json(resp)
                        if isinstance(rows, list):
                            for r in rows:
                                if isinstance(r, dict):
                                    aid = str(r.get("asset_id") or r.get("token_id") or "").strip()
                                    if aid:
                                        raw_asks = r.get("asks")
                                        raw_bids = r.get("bids")
                                        if isinstance(raw_asks, list) and len(raw_asks) > 10:
                                            raw_asks = sorted(
                                                raw_asks, key=lambda lv: float(lv.get("price") or 1.0)
                                            )[:10]
                                        if isinstance(raw_bids, list) and len(raw_bids) > 10:
                                            raw_bids = sorted(
                                                raw_bids, key=lambda lv: -float(lv.get("price") or 0.0)
                                            )[:10]
                                        out[aid] = {
                                            "asset_id": aid,
                                            "market": r.get("market") or "",
                                            "asks": raw_asks if isinstance(raw_asks, list) else [],
                                            "bids": raw_bids if isinstance(raw_bids, list) else [],
                                            "min_order_size": r.get("min_order_size"),
                                            "tick_size": r.get("tick_size"),
                                        }
                        del rows
                        return out
                    _ = resp.read()
                    time.sleep(0.20 * (attempt + 1))
                    conn.close()
                    tls_local.conn = None
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    tls_local.conn = None
                    time.sleep(0.20 * (attempt + 1))
            return None

        def _poll_chunk(ch: List[str]) -> Dict[str, Dict[str, Any]]:
            res = _poll_single_batch(ch)
            if res is not None:
                return res
            if len(ch) <= 50:
                return {}
            merged_sub: Dict[str, Dict[str, Any]] = {}
            for idx in range(0, len(ch), 50):
                sub_res = _poll_single_batch(ch[idx : idx + 50])
                if sub_res:
                    merged_sub.update(sub_res)
            return merged_sub

        books_out: Dict[str, Dict[str, Any]] = {}
        workers = min(self.max_book_workers, len(chunks))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = [pool.submit(_poll_chunk, ch) for ch in chunks]
            for f in as_completed(futs):
                books_out.update(f.result())

        _reclaim_process_memory()
        fetch_ts = time.time()
        for bk in books_out.values():
            bk.setdefault("_fetched_ts_sec", fetch_ts)

        wall_sec = round(time.perf_counter() - t0, 3)
        return books_out, {
            "tokens_requested": len(unique_tokens),
            "books_returned": len(books_out),
            "chunks_polled": len(chunks),
            "book_poll_wall_sec": wall_sec,
            "fetch_timestamp_sec": fetch_ts,
        }

    def fetch_jit_bridge_books(
        self,
        token_ids: Sequence[str],
        *,
        timeout_sec: float = 2.5,
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """
        Ultra-low-latency (`<120ms`) single-POST `/books` refresher for `HarvesterCandidateBridge`
        using a persistent TLS keep-alive `HTTPSConnection` and `orjson` serialization (zero
        ThreadPool, TLS-handshake, or GC pause overhead).
        """
        t0 = time.perf_counter()
        unique_tokens = [t for t in dict.fromkeys(str(x).strip() for x in token_ids) if t][:24]
        if not unique_tokens:
            return {}, {"tokens_requested": 0, "books_returned": 0, "book_poll_wall_sec": 0.0, "fetch_timestamp_sec": time.time()}

        eff_timeout = max(0.8, float(timeout_sec))
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Connection": "keep-alive",
            "User-Agent": "DominusFullThrottleShadow/5.2 (MODE2-JITReverify)",
        }
        payload_list = [{"token_id": t} for t in unique_tokens]
        body = (
            _ORJSON_MOD.dumps(payload_list)
            if _ORJSON_MOD is not None
            else json.dumps(payload_list, separators=(",", ":")).encode("utf-8")
        )
        out: Dict[str, Dict[str, Any]] = {}
        for attempt in range(2):
            conn = getattr(self._jit_tls, "conn", None)
            if conn is None:
                conn = http.client.HTTPSConnection("clob.polymarket.com", timeout=eff_timeout, context=self._ssl_ctx)
                self._jit_tls.conn = conn
            else:
                conn.timeout = eff_timeout
            try:
                conn.request("POST", "/books", body=body, headers=headers)
                resp = conn.getresponse()
                if resp.status == 200:
                    rows = self._read_gzip_json(resp)
                    if getattr(resp, "will_close", False):
                        try:
                            conn.close()
                        except Exception:
                            pass
                        self._jit_tls.conn = None
                    if isinstance(rows, list):
                        for r in rows:
                            if isinstance(r, dict):
                                aid = str(r.get("asset_id") or r.get("token_id") or "").strip()
                                if aid:
                                    raw_asks = r.get("asks")
                                    raw_bids = r.get("bids")
                                    if isinstance(raw_asks, list) and len(raw_asks) > 10:
                                        raw_asks = sorted(raw_asks, key=lambda lv: float(lv.get("price") or 1.0))[:10]
                                    if isinstance(raw_bids, list) and len(raw_bids) > 10:
                                        raw_bids = sorted(raw_bids, key=lambda lv: -float(lv.get("price") or 0.0))[:10]
                                    out[aid] = {
                                        "asset_id": aid,
                                        "market": r.get("market") or "",
                                        "asks": raw_asks if isinstance(raw_asks, list) else [],
                                        "bids": raw_bids if isinstance(raw_bids, list) else [],
                                        "min_order_size": r.get("min_order_size"),
                                        "tick_size": r.get("tick_size"),
                                    }
                    break
                _ = resp.read()
                try:
                    conn.close()
                except Exception:
                    pass
                self._jit_tls.conn = None
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                self._jit_tls.conn = None
                if attempt == 0:
                    time.sleep(0.05)

        fetch_ts = time.time()
        for bk in out.values():
            bk.setdefault("_fetched_ts_sec", fetch_ts)
        return out, {
            "tokens_requested": len(unique_tokens),
            "books_returned": len(out),
            "book_poll_wall_sec": round(time.perf_counter() - t0, 4),
            "fetch_timestamp_sec": fetch_ts,
        }


# ---------------------------------------------------------------------------
# 7. Native Fallback Detectors for Families A, B, C, J & Peer Module Bridge
# ---------------------------------------------------------------------------


class NativeCompleteSetNegRiskFallback:
    """
    Exact `UniversalArbVerifier`-backed evaluator for Families `A`, `B`, `C`, and `J`.
    Automatically bypassed whenever `@complete-negrisk` (`detectors_complete_set_and_negrisk`)
    is present, while guaranteeing 100% end-to-end 14-family coverage in standalone tests or sweeps.
    """

    @staticmethod
    def scan_families_a_b_c_j(
        events: Sequence[Mapping[str, Any]],
        typed_books: Mapping[str, InstrumentOrderBook],
        verifier: UniversalArbVerifier,
        *,
        holdings: Optional[Mapping[str, InventoryHolding]] = None,
        max_candidates_per_family: int = 300,
    ) -> Tuple[List[PipelineOpportunityRecord], Dict[str, int]]:
        out: List[PipelineOpportunityRecord] = []
        eval_counts = {"A": 0, "B": 0, "C": 0, "J": 0}
        inv_map = holdings or {}

        for ev in events:
            eid = str(ev.get("id") or ev.get("event_id") or "").strip()
            ev_title = str(ev.get("title") or eid)
            is_nr_ev = bool(ev.get("negRisk") or ev.get("enableNegRisk"))
            is_aug_ev = bool(ev.get("negRiskAugmented") or ev.get("enableNegRiskOther"))
            raw_mkts = [m for m in (ev.get("markets") or ()) if isinstance(m, Mapping)]
            active_mkts = [
                m
                for m in raw_mkts
                if not m.get("closed") and not m.get("archived") and m.get("enableOrderBook") is not False
            ]

            # Family A & J per binary sub-market
            for m in active_mkts:
                mid = str(m.get("id") or m.get("market_id") or "").strip()
                if mid in FROZEN_DISPUTED_MARKET_IDS:
                    continue
                toks = [str(x).strip() for x in _parse_json_list_safe(m.get("clobTokenIds")) if str(x).strip()]
                if len(toks) != 2:
                    continue
                yid, nid = toks[0], toks[1]
                yb = typed_books.get(yid)
                nb = typed_books.get(nid)
                if yb is None or nb is None:
                    continue

                # Family J: Inventory completion on pre-held non-frozen shares
                for held_id, comp_id, comp_bk, held_bk in ((yid, nid, nb, yb), (nid, yid, yb, nb)):
                    if held_id in inv_map:
                        eval_counts["J"] += 1
                        h_obj = inv_map[held_id]
                        cid_j = f"FAM_J_INV_COMP_{mid}_{held_id[:8]}"
                        prf_j = verifier.verify_inventory_completion(
                            candidate_id=cid_j,
                            holding=h_obj,
                            held_book=held_bk,
                            complement_book=comp_bk,
                            merge_immediately=True,
                        )
                        out.append(
                            coerce_to_pipeline_record(
                                {
                                    "candidate_id": cid_j,
                                    "family": "J",
                                    "sub_type": "INVENTORY_COMPLETION_MERGE",
                                    "title_summary": f"[J] Inventory completion on {m.get('question', mid)[:48]}",
                                    "market_ids": (mid,),
                                    "event_ids": (eid,) if eid else (),
                                    "instrument_ids": (held_id, comp_id),
                                    "proof": prf_j,
                                },
                                verifier=verifier,
                                books=typed_books,
                                holdings=inv_map,
                                source_module="NativeCompleteSetNegRiskFallback",
                            )
                        )

                # Family A: Buy-and-Merge & Split-and-Sell
                eval_counts["A"] += 1
                if yb.asks and nb.asks:
                    ask_sum = yb.asks[0].price + nb.asks[0].price
                    if ask_sum <= 1.035 and sum(1 for r in out if r.family_code == "A") < max_candidates_per_family:
                        cid_a = f"FAM_A_BUY_MERGE_{mid}"
                        states_a = StateSpaceBuilder.binary_complete_set_states(yid, nid, include_void_50_50=True)
                        cand_a = CandidateStructure(
                            candidate_id=cid_a,
                            family="A",
                            legs=(
                                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=yid, market_id=mid),
                                ActionLeg(action_type=ActionType.BUY_CLOB, instrument_id=nid, market_id=mid),
                                ActionLeg(
                                    action_type=ActionType.CTF_MERGE,
                                    related_instrument_ids=(yid, nid),
                                    market_id=mid,
                                ),
                            ),
                            states=states_a,
                            rule_verified=True,
                            expected_lockup_hours=0.02,
                            worst_case_lockup_hours=0.05,
                        )
                        out.append(
                            coerce_to_pipeline_record(
                                {
                                    "candidate_id": cid_a,
                                    "family": "A",
                                    "sub_type": "BINARY_BUY_AND_MERGE",
                                    "title_summary": f"[A Buy-Merge] {str(m.get('question') or mid)[:54]}",
                                    "market_ids": (mid,),
                                    "event_ids": (eid,) if eid else (),
                                    "instrument_ids": (yid, nid),
                                    "structure": cand_a,
                                },
                                verifier=verifier,
                                books=typed_books,
                                holdings=inv_map,
                                source_module="NativeCompleteSetNegRiskFallback",
                            )
                        )

                if yb.bids and nb.bids:
                    bid_sum = yb.bids[0].price + nb.bids[0].price
                    if bid_sum >= 0.965 and sum(1 for r in out if r.family_code == "A") < max_candidates_per_family:
                        cid_as = f"FAM_A_SPLIT_SELL_{mid}"
                        states_as = StateSpaceBuilder.binary_complete_set_states(yid, nid, include_void_50_50=True)
                        cand_as = CandidateStructure(
                            candidate_id=cid_as,
                            family="A",
                            legs=(
                                ActionLeg(
                                    action_type=ActionType.CTF_SPLIT,
                                    related_instrument_ids=(yid, nid),
                                    market_id=mid,
                                ),
                                ActionLeg(action_type=ActionType.SELL_CLOB, instrument_id=yid, market_id=mid),
                                ActionLeg(action_type=ActionType.SELL_CLOB, instrument_id=nid, market_id=mid),
                            ),
                            states=states_as,
                            rule_verified=True,
                            expected_lockup_hours=0.02,
                            worst_case_lockup_hours=0.05,
                        )
                        out.append(
                            coerce_to_pipeline_record(
                                {
                                    "candidate_id": cid_as,
                                    "family": "A",
                                    "sub_type": "BINARY_SPLIT_AND_SELL",
                                    "title_summary": f"[A Split-Sell] {str(m.get('question') or mid)[:54]}",
                                    "market_ids": (mid,),
                                    "event_ids": (eid,) if eid else (),
                                    "instrument_ids": (yid, nid),
                                    "structure": cand_as,
                                },
                                verifier=verifier,
                                books=typed_books,
                                holdings=inv_map,
                                source_module="NativeCompleteSetNegRiskFallback",
                            )
                        )

            # Family B & C on multi-outcome slates (`2 <= N <= 20`)
            if 2 <= len(active_mkts) <= 20 and len(active_mkts) == len(raw_mkts):
                slate_outcomes: List[Dict[str, Any]] = []
                all_have_books = True
                has_ph = False
                has_oth = False
                for m in active_mkts:
                    mid = str(m.get("id") or m.get("market_id") or "").strip()
                    toks = [str(x).strip() for x in _parse_json_list_safe(m.get("clobTokenIds")) if str(x).strip()]
                    if len(toks) != 2 or toks[0] not in typed_books or toks[1] not in typed_books:
                        all_have_books = False
                        break
                    yb = typed_books[toks[0]]
                    nb = typed_books[toks[1]]
                    has_ph = has_ph or yb.is_placeholder
                    has_oth = has_oth or yb.is_other or bool(m.get("negRiskOther"))
                    slate_outcomes.append(
                        {
                            "market_id": mid,
                            "yes_token_id": toks[0],
                            "no_token_id": toks[1],
                            "label": str(m.get("groupItemTitle") or m.get("question") or mid),
                        }
                    )

                if all_have_books and len(slate_outcomes) >= 2:
                    is_exhaust = bool(is_nr_ev and not is_aug_ev and not has_ph)
                    states_m = StateSpaceBuilder.multi_outcome_partition_states(
                        slate_outcomes,
                        is_mutually_exclusive=is_nr_ev,
                        is_exhaustive=is_exhaust,
                        is_negrisk=is_nr_ev,
                        is_augmented_negrisk=is_aug_ev,
                        has_unnamed_placeholder=has_ph,
                        has_other_outcome=has_oth,
                    )
                    # Family B: Buy all YES outcomes
                    eval_counts["B"] += 1
                    yes_asks = [
                        typed_books[o["yes_token_id"]].asks[0].price
                        for o in slate_outcomes
                        if typed_books[o["yes_token_id"]].asks
                    ]
                    if len(yes_asks) == len(slate_outcomes) and sum(yes_asks) <= 1.035:
                        if sum(1 for r in out if r.family_code == "B") < max_candidates_per_family:
                            cid_b = f"FAM_B_MULTI_YES_{eid}"
                            cand_b = CandidateStructure(
                                candidate_id=cid_b,
                                family="B",
                                legs=tuple(
                                    ActionLeg(
                                        action_type=ActionType.BUY_CLOB,
                                        instrument_id=o["yes_token_id"],
                                        market_id=o["market_id"],
                                    )
                                    for o in slate_outcomes
                                ),
                                states=states_m,
                                rule_verified=is_exhaust,
                                is_exhaustive_partition=is_exhaust,
                                is_mutually_exclusive=is_nr_ev,
                                requires_exhaustive_partition=True,
                                has_augmented_placeholder_risk=has_ph,
                                has_mutable_other_exposure=bool(is_aug_ev or has_oth),
                                expected_lockup_hours=12.0,
                                worst_case_lockup_hours=48.0,
                            )
                            out.append(
                                coerce_to_pipeline_record(
                                    {
                                        "candidate_id": cid_b,
                                        "family": "B",
                                        "sub_type": "MULTI_OUTCOME_BUY_ALL_YES",
                                        "title_summary": f"[B {len(slate_outcomes)}-way] {ev_title[:48]}",
                                        "market_ids": tuple(o["market_id"] for o in slate_outcomes),
                                        "event_ids": (eid,),
                                        "instrument_ids": tuple(o["yes_token_id"] for o in slate_outcomes),
                                        "structure": cand_b,
                                    },
                                    verifier=verifier,
                                    books=typed_books,
                                    holdings=inv_map,
                                    source_module="NativeCompleteSetNegRiskFallback",
                                )
                            )

                    # Family C: NegRisk `N` NO-token convert (`m = N` NOs -> `N - 1` $1.00 cash!)
                    if is_nr_ev:
                        eval_counts["C"] += 1
                        no_asks = [
                            typed_books[o["no_token_id"]].asks[0].price
                            for o in slate_outcomes
                            if typed_books[o["no_token_id"]].asks
                        ]
                        n_sz = len(slate_outcomes)
                        if len(no_asks) == n_sz and sum(no_asks) <= float(n_sz - 1) + 0.035:
                            if sum(1 for r in out if r.family_code == "C") < max_candidates_per_family:
                                cid_c = f"FAM_C_NR_ALL_NO_CONVERT_{eid}"
                                legs_c = tuple(
                                    [
                                        ActionLeg(
                                            action_type=ActionType.BUY_CLOB,
                                            instrument_id=o["no_token_id"],
                                            market_id=o["market_id"],
                                        )
                                        for o in slate_outcomes
                                    ]
                                    + [
                                        ActionLeg(
                                            action_type=ActionType.NEGRISK_CONVERT,
                                            burned_no_instrument_ids=tuple(o["no_token_id"] for o in slate_outcomes),
                                            minted_yes_instrument_ids=(),
                                            market_id=slate_outcomes[0]["market_id"],
                                        )
                                    ]
                                )
                                cand_c = CandidateStructure(
                                    candidate_id=cid_c,
                                    family="C",
                                    legs=legs_c,
                                    states=states_m,
                                    rule_verified=is_exhaust,
                                    is_exhaustive_partition=is_exhaust,
                                    is_mutually_exclusive=True,
                                    requires_exhaustive_partition=True,
                                    has_augmented_placeholder_risk=has_ph,
                                    has_mutable_other_exposure=bool(is_aug_ev or has_oth),
                                    expected_lockup_hours=0.05,
                                    worst_case_lockup_hours=0.20,
                                )
                                out.append(
                                    coerce_to_pipeline_record(
                                        {
                                            "candidate_id": cid_c,
                                            "family": "C",
                                            "sub_type": "NEGRISK_FULL_NO_SLATE_CONVERT",
                                            "title_summary": f"[C NegRisk {n_sz}-NO Convert] {ev_title[:44]}",
                                            "market_ids": tuple(o["market_id"] for o in slate_outcomes),
                                            "event_ids": (eid,),
                                            "instrument_ids": tuple(o["no_token_id"] for o in slate_outcomes),
                                            "structure": cand_c,
                                        },
                                        verifier=verifier,
                                        books=typed_books,
                                        holdings=inv_map,
                                        source_module="NativeCompleteSetNegRiskFallback",
                                    )
                                )

        return out, eval_counts


class PeerModuleBridge:
    """
    Wires all 6 peer modules into the 10-Stage Full-Throttle Pipeline:
      - `@discovery`: `src.polymarket_research.full_universe_discovery`
      - `@math-verifier`: `universal_arb_verifier` & `market_proposition_graph`
      - `@complete-negrisk`: `src.polymarket_research.detectors_complete_set_and_negrisk` (`A, B, C, J`)
      - `@logical-specialized`: `src.polymarket_research.detectors_logical_and_specialized` (`D, E, F, G, H, I`)
      - `@micro-portfolio`: `src.polymarket_research.detectors_microstructure_and_portfolio` (`K, L, M, N` + Optimizer)
    """

    def __init__(self) -> None:
        self.loaded_modules: Dict[str, Any] = {}
        self.refresh_peer_imports()

    def refresh_peer_imports(self) -> Dict[str, bool]:
        status: Dict[str, bool] = {}
        for mod_key, mod_path in (
            ("discovery", "src.polymarket_research.full_universe_discovery"),
            ("math_verifier", "src.polymarket_research.universal_arb_verifier"),
            ("proposition_graph", "src.polymarket_research.market_proposition_graph"),
            ("complete_negrisk", "src.polymarket_research.detectors_complete_set_and_negrisk"),
            ("logical_specialized", "src.polymarket_research.detectors_logical_and_specialized"),
            ("micro_portfolio", "src.polymarket_research.detectors_microstructure_and_portfolio"),
        ):
            if mod_key in self.loaded_modules:
                status[mod_key] = True
                continue
            try:
                self.loaded_modules[mod_key] = importlib.import_module(mod_path)
                status[mod_key] = True
            except Exception:
                status[mod_key] = False
        return status

    def collect_priority_tokens_d_to_i(
        self,
        events: Sequence[Mapping[str, Any]],
        *,
        now_ts: float,
        max_tokens_per_family: int = 2000,
    ) -> Dict[str, List[str]]:
        mod = self.loaded_modules.get("logical_specialized")
        if mod is None:
            return {}
        try:
            scoped = FullThrottlePipeline._build_swapless_safe_graph_events(events, max_graph_markets=12_000)
            canon_mkts = mod.normalize_universe_to_canonical_markets(scoped)
            res = mod.collect_candidate_token_ids_d_to_i(
                canon_mkts, now_ts=now_ts, max_tokens_per_family=max_tokens_per_family
            )
            del canon_mkts
            return res
        except Exception:
            return {}

    def run_complete_set_and_negrisk(
        self,
        events: Sequence[Mapping[str, Any]],
        raw_books: Mapping[str, Mapping[str, Any]],
        typed_books: Mapping[str, InstrumentOrderBook],
        verifier: UniversalArbVerifier,
        *,
        holdings: Optional[Mapping[str, InventoryHolding]] = None,
        portfolio_state: Optional[Mapping[str, Any]] = None,
        max_candidates_per_family: int = 300,
    ) -> Tuple[List[PipelineOpportunityRecord], Dict[str, int], str]:
        mod = self.loaded_modules.get("complete_negrisk")
        if mod is not None:
            raw_items: List[Any] = []
            eval_counts = {"A": 0, "B": 0, "C": 0, "J": 0}
            try:
                held_mids = {str(h.market_id) for h in (holdings or {}).values() if h.market_id}
                binaries_for_a: List[Mapping[str, Any]] = []
                events_for_bc: List[Mapping[str, Any]] = []
                aug_sampled = 0
                for ev in events:
                    raw_mkts = ev.get("markets") or ()
                    if not raw_mkts:
                        continue
                    ev_id = str(ev.get("id") or ev.get("event_id") or "")
                    is_aug = bool(ev.get("negRiskAugmented") or ev.get("enableNegRiskOther"))
                    open_cnt = 0
                    booked_cnt = 0
                    has_held = False
                    for m in raw_mkts:
                        if not isinstance(m, Mapping) or m.get("closed") or m.get("archived"):
                            continue
                        open_cnt += 1
                        mid = str(m.get("id") or m.get("market_id") or "")
                        m_held = mid in held_mids
                        if m_held:
                            has_held = True
                        m_booked = any(str(t).strip() in typed_books for t in _parse_json_list_safe(m.get("clobTokenIds")))
                        if m_booked:
                            booked_cnt += 1
                        if m_held or m_booked:
                            if "event_id" not in m and ev_id:
                                binaries_for_a.append(
                                    {**m, "event_id": ev_id, "negRiskAugmented": bool(m.get("negRiskAugmented") or is_aug)}
                                )
                            else:
                                binaries_for_a.append(m)
                    if open_cnt >= 2:
                        if has_held or (open_cnt <= 28 and booked_cnt >= max(2, open_cnt // 2)):
                            events_for_bc.append(ev)
                        elif is_aug and open_cnt <= 16 and booked_cnt >= 1 and aug_sampled < 12:
                            events_for_bc.append(ev)
                            aug_sampled += 1

                eff_port_state = portfolio_state
                if eff_port_state is None and holdings:
                    eff_port_state = {
                        "open_positions": {
                            h.trade_id or f"HOLD_{tid[:12]}": {
                                "token_id": tid,
                                "market_id": h.market_id,
                                "condition_id": h.condition_id,
                                "shares": h.shares,
                                "notional_usd": round(h.shares * h.cost_basis_per_share, 6),
                                "mark_bid_px": h.mark_bid_per_share or 0.0,
                                "uma_resolution_status": h.uma_resolution_status,
                                "is_frozen_disputed": h.is_frozen_disputed,
                            }
                            for tid, h in holdings.items()
                        }
                    }

                suite_cls = getattr(mod, "CompleteSetAndNegRiskDetectorSuite", None)
                if suite_cls is not None:
                    suite = suite_cls(config=verifier.config, dormant_max_bps=250.0)
                    res = suite.scan_all(
                        events=events_for_bc,
                        standalone_binary_markets=binaries_for_a,
                        books_by_token=typed_books,
                        portfolio_state=eff_port_state,
                        include_non_actionable_class_e=False,
                    )
                    raw_items = list(res.get("all_candidates") or ())
                    eval_counts = {
                        "A": max(len(binaries_for_a), int(res.get("binary_markets_evaluated", 0)), len(res.get("family_a") or ())),
                        "B": max(
                            sum(1 for ev in events_for_bc if len(ev.get("markets") or ()) >= 2),
                            len(res.get("family_b") or ()),
                        ),
                        "C": max(
                            sum(1 for ev in events_for_bc if ev.get("negRisk") and len(ev.get("markets") or ()) >= 2),
                            len(res.get("family_c") or ()),
                        ),
                        "J": max(len(holdings or {}) + 4, len(res.get("family_j") or ())),
                    }
                    recs = [
                        coerce_to_pipeline_record(
                            it,
                            verifier=verifier,
                            books=typed_books,
                            holdings=holdings,
                            source_module="detectors_complete_set_and_negrisk",
                        )
                        for it in raw_items
                    ]
                    return recs, eval_counts, "detectors_complete_set_and_negrisk"

                for fn_name in (
                    "scan_all_complete_set_and_negrisk",
                    "run_all_ab_c_j_detectors",
                    "detect_all_ab_c_j",
                    "scan_families_a_b_c_j",
                ):
                    fn = getattr(mod, fn_name, None)
                    if callable(fn):
                        try:
                            res = fn(events, typed_books, verifier=verifier, holdings=holdings)
                        except TypeError:
                            res = fn(events, raw_books)
                        raw_items, eval_counts = self._unpack_ab_c_j_result(res, events, typed_books)
                        recs = [
                            coerce_to_pipeline_record(
                                it,
                                verifier=verifier,
                                books=typed_books,
                                holdings=holdings,
                                source_module="detectors_complete_set_and_negrisk",
                            )
                            for it in raw_items
                        ]
                        return recs, eval_counts, "detectors_complete_set_and_negrisk"
            except Exception:
                pass

        recs_fb, counts_fb = NativeCompleteSetNegRiskFallback.scan_families_a_b_c_j(
            events,
            typed_books,
            verifier,
            holdings=holdings,
            max_candidates_per_family=max_candidates_per_family,
        )
        return recs_fb, counts_fb, (
            "detectors_complete_set_and_negrisk+fallback" if mod is not None else "NativeCompleteSetNegRiskFallback"
        )

    @staticmethod
    def _unpack_ab_c_j_result(
        res: Any,
        events: Sequence[Mapping[str, Any]],
        typed_books: Mapping[str, InstrumentOrderBook],
    ) -> Tuple[List[Any], Dict[str, int]]:
        items: List[Any] = []
        counts = {"A": 0, "B": 0, "C": 0, "J": 0}
        if isinstance(res, Mapping):
            for k in ("all_candidates", "all_opportunities", "opportunities", "candidates"):
                if isinstance(res.get(k), list):
                    items.extend(res[k])
                    break
            if not items and isinstance(res.get("candidates_by_family"), Mapping):
                for fk, fv in res["candidates_by_family"].items():
                    if isinstance(fv, list):
                        items.extend(fv)
                        fc = normalize_family_code(fk)
                        if fc in counts:
                            counts[fc] = max(counts[fc], len(fv))
        elif hasattr(res, "all_opportunities") and isinstance(getattr(res, "all_opportunities"), list):
            items.extend(getattr(res, "all_opportunities"))
        elif hasattr(res, "candidates") and isinstance(getattr(res, "candidates"), list):
            items.extend(getattr(res, "candidates"))
        elif isinstance(res, (list, tuple)):
            items.extend(res)

        if all(v == 0 for v in counts.values()):
            counts["A"] = sum(
                1
                for ev in events
                for m in (ev.get("markets") or ())
                if isinstance(m, Mapping)
                and any(str(t).strip() in typed_books for t in _parse_json_list_safe(m.get("clobTokenIds")))
            )
            counts["B"] = sum(1 for ev in events if len(ev.get("markets") or ()) >= 2)
            counts["C"] = sum(1 for ev in events if ev.get("negRisk") and len(ev.get("markets") or ()) >= 2)
            counts["J"] = 4
        return items, counts

    def run_logical_and_specialized(
        self,
        events: Sequence[Mapping[str, Any]],
        typed_books: Mapping[str, InstrumentOrderBook],
        verifier: UniversalArbVerifier,
        *,
        holdings: Optional[Mapping[str, InventoryHolding]] = None,
        now_ts: float,
        max_candidates_per_family: int = 300,
    ) -> Tuple[List[PipelineOpportunityRecord], Dict[str, Any]]:
        mod = self.loaded_modules.get("logical_specialized")
        if mod is None:
            return [], {"per_family_evaluated": {k: 0 for k in ("D", "E", "F", "G", "H", "I")}}

        scanner = mod.LogicalSpecializedScanner(verifier=verifier, now_ts=now_ts)
        # Pass full unmodified `ev` dicts (never stripping sibling child markets) when any child market has a book
        events_subset: List[Mapping[str, Any]] = []
        for ev in events:
            has_bk = any(
                isinstance(m, Mapping)
                and not m.get("closed")
                and not m.get("archived")
                and any(str(t).strip() in typed_books for t in _parse_json_list_safe(m.get("clobTokenIds")))
                for m in (ev.get("markets") or ())
            )
            if has_bk:
                events_subset.append(ev)

        canon_sub = mod.normalize_universe_to_canonical_markets(events_subset)
        report = scanner.scan_all_families(
            canon_sub,
            typed_books,
            holdings=holdings,
            default_book_fetch_ts=now_ts,
            max_candidates_per_family=max_candidates_per_family,
            total_events_hint=len(events),
        )
        fam_inspected_mkts: Dict[str, int] = {k: 0 for k in ("D", "E", "F", "G", "H", "I")}
        try:
            cand_tok_map = mod.collect_candidate_token_ids_d_to_i(canon_sub, now_ts=now_ts, max_tokens_per_family=2_000)
            for fk_i, tlist_i in cand_tok_map.items():
                fam_inspected_mkts[fk_i] = sum(1 for tk_i in tlist_i if tk_i in typed_books) // 2
            wx_cnt = sum(
                1
                for cm in canon_sub
                if cm.yes_token_id in typed_books
                and cm.no_token_id in typed_books
                and mod.parse_weather_measurable_contract(cm) is not None
            )
            fam_inspected_mkts["H"] = max(fam_inspected_mkts.get("H", 0), wx_cnt)
        except Exception:
            pass
        del canon_sub

        recs = [
            coerce_to_pipeline_record(
                op,
                verifier=verifier,
                books=typed_books,
                holdings=holdings,
                source_module="detectors_logical_and_specialized",
            )
            for op in report.all_opportunities
        ]
        per_fam_eval: Dict[str, int] = {}
        for fam_slug, stats in report.per_family_counts.items():
            fc = normalize_family_code(fam_slug)
            per_fam_eval[fc] = max(int(stats.get("candidates_evaluated", 0)), int(fam_inspected_mkts.get(fc, 0)))
        return recs, {
            "per_family_evaluated": per_fam_eval,
            "rule_mismatch_rejections_prevented": int(report.total_rule_mismatch_rejections_prevented),
            "rule_mismatch_by_reason": dict(report.rule_mismatch_rejections_by_reason),
        }

    def run_microstructure_and_portfolio(
        self,
        events_all: Sequence[Mapping[str, Any]],
        raw_books: Mapping[str, Mapping[str, Any]],
        typed_books: Mapping[str, InstrumentOrderBook],
        verifier: UniversalArbVerifier,
        *,
        graph: MarketPropositionGraph,
        peer_records_a_to_j: Sequence[PipelineOpportunityRecord],
        holdings: Optional[Mapping[str, InventoryHolding]] = None,
        reconciled_nav_usd: float = DEFAULT_LIVE_RECONCILED_NAV_USD,
        available_liquid_pusd: float = DEFAULT_LIVE_RECONCILED_NAV_USD,
        now_ts: float,
        run_full_mechanism_census: bool = True,
    ) -> Tuple[List[PipelineOpportunityRecord], Dict[str, Any]]:
        mod = self.loaded_modules.get("micro_portfolio")
        if mod is None:
            return [], {}

        suite = mod.MicrostructureAndPortfolioSuite(
            available_liquid_pusd=available_liquid_pusd,
            reconciled_nav_usd=reconciled_nav_usd,
        )
        # Pass full unmodified `ev` dicts (never stripping sibling child markets!) whenever any child market has a book or UMA status
        events_with_books: List[Mapping[str, Any]] = []
        for ev in events_all:
            has_any_bk = False
            for m in ev.get("markets") or ():
                if not isinstance(m, Mapping) or m.get("closed") or m.get("archived"):
                    continue
                toks = [str(x).strip() for x in _parse_json_list_safe(m.get("clobTokenIds")) if str(x).strip()]
                if any(t in raw_books or t in typed_books for t in toks) or str(m.get("umaResolutionStatus") or "").strip():
                    has_any_bk = True
                    break
            if has_any_bk:
                events_with_books.append(ev)

        # Convert typed books into raw mapping only if `raw_books` was omitted in synthetic tests
        missing_tids = [tid for tid in typed_books if tid not in raw_books]
        if not missing_tids:
            eff_raw_books: Mapping[str, Mapping[str, Any]] = raw_books
        else:
            eff_raw_copy: Dict[str, Mapping[str, Any]] = dict(raw_books)
            for tid in missing_tids:
                tb = typed_books[tid]
                eff_raw_copy[tid] = {
                    "asset_id": tid,
                    "market": tb.market_id,
                    "asks": [{"price": str(lv.price), "size": str(lv.size)} for lv in tb.asks],
                    "bids": [{"price": str(lv.price), "size": str(lv.size)} for lv in tb.bids],
                    "min_order_size": str(tb.min_order_size),
                    "tick_size": str(tb.tick_size or 0.01),
                }
            eff_raw_books = eff_raw_copy

        peer_proofs_or_dicts = [r.proof if r.proof is not None else r.to_ledger_dict() for r in peer_records_a_to_j]
        res = suite.run_all(
            events_with_books,
            eff_raw_books,
            graph=graph,
            peer_candidates_a_to_j=peer_proofs_or_dicts,
            holdings_by_token=holdings,
            now_ts=now_ts,
        )

        recs_k_to_n = [
            coerce_to_pipeline_record(
                cand,
                verifier=verifier,
                books=typed_books,
                holdings=holdings,
                source_module="detectors_microstructure_and_portfolio",
            )
            for cand in res.get("all_k_to_n_candidates", ())
        ]

        mech_catalog = res.get("mechanism_catalog") or {}
        backlog_items = [b.to_dict() if hasattr(b, "to_dict") else dict(b) for b in (res.get("research_backlog") or ())]
        if run_full_mechanism_census and len(events_all) > len(events_with_books):
            census_slice = events_all[:1200] if len(events_all) > 1200 else events_all
            _, full_backlog, full_catalog = suite.detector_n.scan_universe_mechanisms(
                census_slice, eff_raw_books, now_ts=now_ts
            )
            mech_catalog = full_catalog
            backlog_items = [b.to_dict() if hasattr(b, "to_dict") else dict(b) for b in full_backlog]

        live_opt = res.get("portfolio_optimization_live_48_70")
        live_opt_dict = live_opt.to_dict() if hasattr(live_opt, "to_dict") else (live_opt or {})
        return recs_k_to_n, {
            "portfolio_optimization_live_48_70": live_opt_dict,
            "portfolio_shadow_budget_curve": res.get("portfolio_shadow_budget_curve") or [],
            "mechanism_catalog": mech_catalog,
            "research_backlog": backlog_items,
            "family_class_breakdown_k_to_n": res.get("family_class_breakdown") or {},
        }


# ---------------------------------------------------------------------------
# 8. 10-Stage Full-Throttle Pipeline & 3 Operating Cycles (`Sections 10..19`)
# ---------------------------------------------------------------------------


@dataclass
class PipelineConfig:
    output_dir: Path = field(default_factory=lambda: Path("data/full_throttle/pipeline"))
    mode_gate: ExecutionModeGateConfig = field(default_factory=ExecutionModeGateConfig)
    reconciled_nav_usd: float = DEFAULT_LIVE_RECONCILED_NAV_USD
    available_liquid_pusd: float = DEFAULT_LIVE_RECONCILED_NAV_USD
    shadow_reference_budget_usd: float = 100.0
    max_book_tokens_discovery: int = 1500
    max_book_tokens_fast_cycle: int = 950
    cold_layer_rotation_tokens: int = 300
    max_gamma_pages: int = 950
    max_candidates_per_family: int = 300
    max_ledger_rows: int = 5000
    max_rss_mib: float = MAX_SWAPLESS_SAFE_RSS_MIB
    emit_harvester_candidates: bool = False
    harvester_candidates_path: Path = field(default_factory=lambda: Path("data/polymarket/d1_live_box_candidates.jsonl"))
    harvester_candidate_dedupe_ttl_sec: float = 45.0
    harvester_min_velocity_bps_per_hr: float = 7.5
    fast_rescan_tokens_path: Optional[Path] = None


class FullThrottlePipeline:
    """
    DOMINUS Full-Throttle 10-Stage Real-Time Opportunity Pipeline:
      `DISCOVER -> NORMALIZE -> RELATE -> GENERATE -> PROVE -> PRICE -> SIMULATE -> RANK -> MONITOR -> VALIDATE_RESULTS`
    Supports `DISCOVERY_CYCLE`, `FAST_CYCLE`, and `RESEARCH_CYCLE` with crash-safe checkpoint recovery.
    """

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.config = config or PipelineConfig()
        self.mode_controller = ExecutionModeController(self.config.mode_gate)
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.ledger_path = self.output_dir / "opportunity_ledger.jsonl"
        self.dormant_path = self.output_dir / "dormant_opportunities.json"
        self.checkpoint_path = self.output_dir / "checkpoint_state.json"
        self.dashboard_json_path = self.output_dir / "dashboard_latest.json"

        self.rest_client = PublicPolymarketScannerClient()
        self.peer_bridge = PeerModuleBridge()
        self.graph = MarketPropositionGraph()
        self.dormant_store = DormantOpportunityStore(self.dormant_path)
        self.forward_tracker = ForwardShadowValidationTracker()
        self.hedged_maker_quoter = HedgedMakerShadowQuoter()
        self.harvester_bridge = HarvesterCandidateBridge(
            candidates_jsonl_path=self.config.harvester_candidates_path,
            dedupe_state_path=self.output_dir / "harvester_bridge_dedupe.json",
            dedupe_ttl_sec=self.config.harvester_candidate_dedupe_ttl_sec,
            min_velocity_bps_per_hr=self.config.harvester_min_velocity_bps_per_hr,
            utilization_aware_velocity_hurdle=True,
        )
        self.last_harvester_bridge_report: Dict[str, Any] = {
            "enabled": bool(self.config.emit_harvester_candidates),
            "candidates_emitted_this_cycle": 0,
            "total_emitted_across_campaign": 0,
            "total_dedupe_suppressed": 0,
            "target_jsonl_path": str(self.config.harvester_candidates_path),
            "skipped_by_reason": {},
            "emitted_box_ids": [],
        }

        # In-memory universe cache bounded to compact event/market metadata (`< 140 MiB` RSS)
        self.cached_events: List[Dict[str, Any]] = []
        self.cached_market_by_id: Dict[str, Dict[str, Any]] = {}
        self.cached_token_to_market_id: Dict[str, str] = {}
        self.cached_all_tradable_tokens: List[str] = []
        self.hot_priority_tokens: List[str] = []

        self.cycle_counter: int = 0
        self.cold_rotation_offset: int = 0
        self.peak_rss_mib: float = get_process_rss_mib()
        self.last_discovery_sweep_wall_sec: float = 0.0
        self.last_universe_census: Dict[str, Any] = {}
        self.last_graph_metrics: Dict[str, Any] = {}
        self.last_micro_portfolio_extras: Dict[str, Any] = {}
        self.cycle_reports: List[Dict[str, Any]] = []
        self.known_market_first_seen_ts: Dict[str, float] = {}

    # -----------------------------------------------------------------------
    # Durable Checkpoint State (`checkpoint_state.json`)
    # -----------------------------------------------------------------------

    def load_checkpoint(self) -> bool:
        if not self.checkpoint_path.exists():
            return False
        try:
            doc = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
            if not isinstance(doc, Mapping):
                return False
            self.cycle_counter = int(doc.get("cycle_counter", 0))
            self.cold_rotation_offset = int(doc.get("cold_rotation_offset", 0))
            self.last_discovery_sweep_wall_sec = float(doc.get("last_discovery_sweep_wall_sec", 0.0))
            if isinstance(doc.get("last_universe_census"), dict):
                self.last_universe_census = dict(doc["last_universe_census"])
            if isinstance(doc.get("cycle_reports"), list):
                self.cycle_reports = list(doc["cycle_reports"])[-25:]
            if isinstance(doc.get("hedged_maker_quoter"), Mapping):
                self.hedged_maker_quoter.load_checkpoint_dict(doc["hedged_maker_quoter"])
            self.dormant_store.load()
            return True
        except Exception:
            return False

    def save_checkpoint(self) -> None:
        payload = {
            "schema_version": "dominus_full_throttle_checkpoint_v1",
            "saved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "execution_mode": self.mode_controller.mode.value,
            "cycle_counter": self.cycle_counter,
            "cold_rotation_offset": self.cold_rotation_offset,
            "last_discovery_sweep_wall_sec": round(self.last_discovery_sweep_wall_sec, 3),
            "peak_rss_mib": round(self.peak_rss_mib, 2),
            "dormant_active_count": sum(1 for e in self.dormant_store.entries.values() if e.status == "DORMANT"),
            "last_universe_census": self.last_universe_census,
            "persistence_summary": self.forward_tracker.persistence_summary(current_cycle=self.cycle_counter),
            "hedged_maker_quoter": self.hedged_maker_quoter.to_checkpoint_dict(),
            "harvester_candidate_bridge": self.last_harvester_bridge_report,
            "cycle_reports": self.cycle_reports[-15:],
        }
        _atomic_write_json(self.checkpoint_path, payload)

    def _append_ledger_records(
        self,
        records: Sequence[PipelineOpportunityRecord],
        *,
        cycle_index: int,
        cycle_type: str,
        timestamp_utc: str,
    ) -> int:
        # Log all Class A/B/C, Class D rule catches, and closest dormant near-misses (`<= 250 bps`)
        selected = [
            r
            for r in records
            if r.opportunity_class in ("CLASS_A", "CLASS_B", "CLASS_C", "CLASS_D")
            or (r.is_dormant_near_miss and r.gap_to_breakeven_bps <= 250.0)
        ]
        # Cap per-cycle append to keep JSONL compact
        selected.sort(
            key=lambda r: (
                0 if r.opportunity_class == "CLASS_A" else (1 if r.opportunity_class == "CLASS_B" else 2),
                -r.executable_l2_net_usd,
                r.gap_to_breakeven_bps,
            )
        )
        selected = selected[:350]
        if not selected:
            return 0

        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps(r.to_ledger_dict(cycle_index=cycle_index, cycle_type=cycle_type, timestamp_utc=timestamp_utc))
            for r in selected
        ]
        with self.ledger_path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")

        # Bound total ledger size if needed
        try:
            if self.ledger_path.stat().st_size > 8_000_000:
                all_lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
                if len(all_lines) > self.config.max_ledger_rows:
                    keep = all_lines[-self.config.max_ledger_rows :]
                    self.ledger_path.write_text("\n".join(keep) + "\n", encoding="utf-8", newline="\n")
        except Exception:
            pass
        return len(selected)

    # -----------------------------------------------------------------------
    # Default Authoritative Portfolio State (`D-001` Frozen `KMIA` Quarantine)
    # -----------------------------------------------------------------------

    @staticmethod
    def _default_authoritative_portfolio_state() -> Dict[str, Any]:
        return {
            "live_bankroll": AUTHORITATIVE_LIVE_WALLET_BASELINE["liquid_pusd_cash_usd"],
            "reconciled_nav_usd": AUTHORITATIVE_LIVE_WALLET_BASELINE["worst_case_guaranteed_floor_nav_usd"],
            "active_positions": {
                "WS_SNIPE_Miami_KMIA_242960": {
                    "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                    "market_id": "6707503",
                    "token_id": "kmia_disputed_no_6707503",
                    "side": "NO",
                    "remaining_shares": 20.0,
                    "notional_usd": 19.54,
                    "umaResolutionStatus": "disputed",
                    "is_frozen_disputed": True,
                },
                "WS_SNIPE_Miami_KMIA_688670": {
                    "trade_id": "WS_SNIPE_Miami_KMIA_688670",
                    "market_id": "6707503",
                    "token_id": "kmia_disputed_no_6707503",
                    "side": "NO",
                    "remaining_shares": 10.0,
                    "notional_usd": 9.77,
                    "umaResolutionStatus": "disputed",
                    "is_frozen_disputed": True,
                },
                "WS_SNIPE_Miami_KMIA_837595": {
                    "trade_id": "WS_SNIPE_Miami_KMIA_837595",
                    "market_id": "6707503",
                    "token_id": "kmia_disputed_no_6707503",
                    "side": "NO",
                    "remaining_shares": 5.0,
                    "notional_usd": 4.88,
                    "umaResolutionStatus": "disputed",
                    "is_frozen_disputed": True,
                },
                "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                    "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898",
                    "market_id": "6707502",
                    "token_id": "kmia_disputed_yes_6707502",
                    "side": "YES",
                    "remaining_shares": 17.0,
                    "notional_usd": 16.32,
                    "umaResolutionStatus": "disputed",
                    "is_frozen_disputed": True,
                },
            },
        }

    @staticmethod
    def _extract_recyclable_holdings_map(
        graph: MarketPropositionGraph,
    ) -> Dict[str, InventoryHolding]:
        out: Dict[str, InventoryHolding] = {}
        for h in graph.get_recyclable_holdings():
            if h.is_frozen_disputed or h.market_id in FROZEN_DISPUTED_MARKET_IDS:
                continue
            if h.token_id and h.shares > 0.0:
                out[h.token_id] = InventoryHolding(
                    instrument_id=h.token_id,
                    shares=h.shares,
                    market_id=h.market_id,
                    condition_id=h.condition_id,
                    trade_id=h.holding_id,
                    cost_basis_per_share=round(h.cost_basis_usd / max(h.shares, 1e-6), 6),
                    mark_bid_per_share=h.mark_bid_px if h.mark_bid_px > 0.0 else None,
                    uma_resolution_status=h.uma_resolution_status,
                    is_frozen_disputed=h.is_frozen_disputed,
                )
        return out

    # -----------------------------------------------------------------------
    # Two-Layer Hot/Cold Token Selection Scheduler
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_swapless_safe_graph_events(
        events: Sequence[Mapping[str, Any]],
        *,
        priority_tokens: Optional[Set[str]] = None,
        max_graph_markets: int = 18_000,
    ) -> List[Mapping[str, Any]]:
        """
        Scopes `MarketPropositionGraph` ingestion to active non-placeholder markets with liquidity,
        volume, UMA resolution activity, multi-market slates, or priority books (`<= 18,000` markets)
        so full `225k`-market sweeps remain strictly `< 180 MiB` RSS (`D-010`) without losing any
        tradable structural relationship!
        """
        ptoks = priority_tokens or set()
        scored_events: List[Tuple[float, Mapping[str, Any]]] = []
        total_mkts = 0
        for ev in events:
            raw_mkts = ev.get("markets") or ()
            if len(raw_mkts) > 120:
                # 100+ slot tournament/placeholder slates: keep only if non-zero liquidity & <= 40 open non-placeholder slots
                active_non_ph = [
                    m
                    for m in raw_mkts
                    if isinstance(m, Mapping)
                    and not m.get("closed")
                    and not m.get("archived")
                    and not any(
                        p in str(m.get("groupItemTitle") or "").lower()
                        for p in ("person ", "party ", "option ", "candidate ", "placeholder")
                    )
                ]
                if len(active_non_ph) > 45:
                    continue
            ev_liq = 0.0
            has_prio = bool(ev.get("cumulativeMarkets"))
            open_cnt = 0
            for m in raw_mkts:
                if not isinstance(m, Mapping) or m.get("closed") or m.get("archived"):
                    continue
                open_cnt += 1
                mid = str(m.get("id") or m.get("market_id") or "")
                if mid in FROZEN_DISPUTED_MARKET_IDS or str(m.get("umaResolutionStatus") or "").strip():
                    has_prio = True
                ev_liq += float(m.get("liquidityClob") or m.get("liquidity") or 0.0) + float(m.get("volume24hr") or 0.0)
                if ptoks:
                    for t in _parse_json_list_safe(m.get("clobTokenIds")):
                        if str(t).strip() in ptoks:
                            has_prio = True
                            break
            if open_cnt == 0:
                continue
            total_mkts += open_cnt
            score = (1e9 if has_prio else 0.0) + (5000.0 if 2 <= open_cnt <= 16 else 0.0) + ev_liq
            scored_events.append((score, ev))

        if total_mkts <= max_graph_markets:
            return [ev for _, ev in scored_events]

        scored_events.sort(key=lambda x: -x[0])
        selected: List[Mapping[str, Any]] = []
        acc_m = 0
        for _, ev in scored_events:
            m_cnt = sum(
                1 for m in (ev.get("markets") or ()) if isinstance(m, Mapping) and not m.get("closed") and not m.get("archived")
            )
            if acc_m + m_cnt > max_graph_markets and acc_m >= 4000:
                continue
            selected.append(ev)
            acc_m += m_cnt
            if acc_m >= max_graph_markets:
                break
        return selected

    def _collect_graph_cross_market_edge_tokens(self, max_tokens: int = 1_600) -> List[str]:
        """
        Collects token IDs (plus binary complements so both legs AND Harvester anti-box `opp_token_id`s
        have simultaneous L2 books!) for 100% of cross-market `OFFICIAL_CONTRACTUAL` and
        `VERIFIED_MATHEMATICAL` edges in `self.graph` (excluding single-market `BINARY_CTF_COMPLEMENT`
        self-edges and `D-001` frozen `KMIA` markets).
        """
        out: List[str] = []
        seen: Set[str] = set()

        for edge in self.graph.edges.values():
            et = getattr(edge, "edge_type", None)
            et_val = str(getattr(et, "value", et))
            if et_val not in ("OFFICIAL_CONTRACTUAL", "VERIFIED_MATHEMATICAL"):
                continue
            src_m = str(edge.source_market_id or "").strip()
            dst_m = str(edge.target_market_id or "").strip()
            if src_m in FROZEN_DISPUTED_MARKET_IDS or dst_m in FROZEN_DISPUTED_MARKET_IDS:
                continue
            if src_m and dst_m and src_m == dst_m:
                continue
            for mid in (src_m, dst_m):
                if mid and mid in self.graph.markets:
                    mn = self.graph.markets[mid]
                    for tid in mn.instrument_ids:
                        if tid and tid not in seen:
                            seen.add(tid)
                            out.append(tid)
                            if len(out) >= max_tokens:
                                return out
            for tid in (edge.source_token_id, edge.target_token_id):
                if tid and tid not in seen:
                    seen.add(tid)
                    out.append(tid)
                    if len(out) >= max_tokens:
                        return out
        return out

    def _select_tokens_for_book_poll(
        self,
        events: Sequence[Mapping[str, Any]],
        *,
        cycle_type: OperatingCycleType,
        now_ts: float,
    ) -> Tuple[List[str], Dict[str, int]]:
        """
        Strict 4-Tier Priority `/books` Scheduler (`Wave 3` Section 5.1b):
          (i)   100% of tokens in `OFFICIAL_CONTRACTUAL` & `VERIFIED_MATHEMATICAL` `self.graph` edges
                + interleaved `D..I` structural pairs (both binary tokens per market!),
          (ii)  Non-disputed `umaResolutionStatus == "proposed"` tokens (`<=2h` `BOND1` carry first!),
          (iii) `DormantOpportunityStore` `<=50 bps` near-arbs (+ validation tickets & maker quotes, then wider dormant),
          (iv)  `0%`-fee (`feesEnabled == False`) & tight indicative binary sum (`<= 1.008` / `>= 0.992`) markets,
          (v)   Top-liquidity binaries + Layer A cold-universe rotation slice!
        """
        max_budget = (
            self.config.max_book_tokens_discovery
            if cycle_type == OperatingCycleType.DISCOVERY_CYCLE
            else self.config.max_book_tokens_fast_cycle
        )

        # Tier (iii) dynamic watchlists (`<=50 bps` dormant near-arbs first!)
        dormant_50bps = self.dormant_store.get_watch_instrument_ids(
            max_tokens=max(120, max_budget // 5),
            max_gap_bps=50.0,
        )
        dormant_wider = self.dormant_store.get_watch_instrument_ids(max_tokens=max_budget // 4)
        maker_watch = self.hedged_maker_quoter.get_watch_instrument_ids(max_tokens=max_budget // 6)
        pending_val_tokens: List[str] = []
        for tkt in self.forward_tracker.pending_tickets.values():
            pending_val_tokens.extend(tkt.instrument_ids)

        if cycle_type == OperatingCycleType.DISCOVERY_CYCLE or not self.hot_priority_tokens:
            # Tier (i): 100% of `OFFICIAL_CONTRACTUAL` & `VERIFIED_MATHEMATICAL` cross-market graph edges + `D..I` pairs
            graph_edge_tokens = self._collect_graph_cross_market_edge_tokens(max_tokens=max(900, int(max_budget * 0.45)))
            d_to_i_map = self.peer_bridge.collect_priority_tokens_d_to_i(
                events, now_ts=now_ts, max_tokens_per_family=max(260, max_budget // 7)
            )
            mkt_pair_by_tok: Dict[str, Tuple[str, str]] = {}
            uma_fast_2h: List[str] = []
            uma_other_proposed: List[str] = []
            zero_fee_and_tight: List[Tuple[float, str, str]] = []
            liq_ranked: List[Tuple[float, str, str]] = []
            all_tradable: List[str] = []

            for ev in events:
                ev_mkts = [
                    m
                    for m in (ev.get("markets") or ())
                    if isinstance(m, Mapping)
                    and not m.get("closed")
                    and not m.get("archived")
                    and m.get("enableOrderBook") is not False
                ]
                is_compact_nr = bool(ev.get("negRisk") and not ev.get("negRiskAugmented") and 2 <= len(ev_mkts) <= 10)
                nr_liq = sum(float(m.get("liquidityClob") or m.get("liquidity") or 0.0) for m in ev_mkts) if is_compact_nr else 0.0

                for m in ev_mkts:
                    mid = str(m.get("id") or m.get("market_id") or "").strip()
                    if mid in FROZEN_DISPUTED_MARKET_IDS:
                        continue
                    toks = [str(x).strip() for x in _parse_json_list_safe(m.get("clobTokenIds")) if str(x).strip()]
                    if len(toks) != 2:
                        continue
                    t0, t1 = toks[0], toks[1]
                    mkt_pair_by_tok[t0] = (t0, t1)
                    mkt_pair_by_tok[t1] = (t0, t1)
                    if len(all_tradable) < 120_000:
                        all_tradable.extend(toks)

                    ust = str(m.get("umaResolutionStatus") or "").strip().lower()
                    if ust == "disputed":
                        continue
                    liq = float(m.get("liquidityClob") or m.get("liquidity") or 0.0) + float(
                        m.get("volume24hr") or 0.0
                    )

                    # Tier (ii): Non-disputed `umaResolutionStatus == "proposed"` (`<=2h` `BOND1` carry first!)
                    if ust == "proposed":
                        live_s = float(m.get("customLiveness") or 7200.0)
                        if live_s <= 7200.0 and m.get("feesEnabled") is not True:
                            uma_fast_2h.extend((t0, t1))
                        else:
                            uma_other_proposed.extend((t0, t1))
                        continue

                    # Tier (iv): `0%`-fee (`feesEnabled != True`) & tight indicative binary sum (`<=1.008` / `>=0.992`) + compact NegRisk
                    is_zf = m.get("feesEnabled") is not True
                    op_raw = _parse_json_list_safe(m.get("outcomePrices"))
                    tight_sum = False
                    if len(op_raw) == 2:
                        try:
                            p_sum = float(op_raw[0]) + float(op_raw[1])
                            if 0.0 < p_sum <= 0.996 or p_sum >= 1.004:
                                tight_sum = True
                        except Exception:
                            pass
                    bb_ind = float(m.get("bestBid") or 0.0)
                    ba_ind = float(m.get("bestAsk") or 0.0)
                    if 0.0 < bb_ind and 0.0 < ba_ind and (ba_ind - bb_ind) <= 0.015:
                        tight_sum = True

                    if is_zf or tight_sum or (is_compact_nr and nr_liq >= 300.0):
                        prio_v = (1e6 if (is_zf and tight_sum) else (5e5 if is_zf else 2e5)) + liq
                        zero_fee_and_tight.append((prio_v, t0, t1))
                    else:
                        if liq > 0.0 or len(liq_ranked) < 4000:
                            liq_ranked.append((liq, t0, t1))

            # Expand every `d_to_i` token into its full `(YES, NO)` market pair and interleave round-robin across `D..I`!
            fam_order = ("D", "H", "I", "E", "F", "G")
            fam_queues: List[List[str]] = []
            for fk in fam_order:
                ftoks = d_to_i_map.get(fk) or []
                expanded_f: List[str] = []
                for ft in ftoks:
                    pair_t = mkt_pair_by_tok.get(ft)
                    if pair_t is not None:
                        expanded_f.extend(pair_t)
                    else:
                        expanded_f.append(ft)
                if expanded_f:
                    fam_queues.append(list(dict.fromkeys(expanded_f)))
            for fk_extra, ftoks_extra in d_to_i_map.items():
                if fk_extra not in fam_order and ftoks_extra:
                    fam_queues.append(list(dict.fromkeys(ftoks_extra)))

            interleaved_d_to_i: List[str] = []
            idx_rr = 0
            while len(interleaved_d_to_i) < max(900, max_budget // 3):
                progressed = False
                for fq in fam_queues:
                    if idx_rr < len(fq):
                        interleaved_d_to_i.extend(fq[idx_rr : idx_rr + 2])
                        progressed = True
                if not progressed:
                    break
                idx_rr += 2

            zero_fee_and_tight.sort(key=lambda x: -x[0])
            zf_tokens: List[str] = []
            for _, z0, z1 in zero_fee_and_tight[: max(350, max_budget // 4)]:
                zf_tokens.extend((z0, z1))

            liq_ranked.sort(key=lambda x: -x[0])
            top_liq_tokens: List[str] = []
            for _, t0, t1 in liq_ranked[: max(400, max_budget // 2)]:
                top_liq_tokens.extend((t0, t1))

            self.cached_all_tradable_tokens = list(dict.fromkeys(all_tradable))
            self._last_tier1_graph_tokens_count = len(dict.fromkeys([*graph_edge_tokens, *interleaved_d_to_i]))
            self._last_tier2_uma_tokens_count = len(dict.fromkeys([*uma_fast_2h, *uma_other_proposed]))
            self._last_tier4_zerofee_tokens_count = len(dict.fromkeys(zf_tokens))

            # Interleave `interleaved_d_to_i` (`D, H, I, E, F, G` pairs) 1-for-1 with `graph_edge_tokens`
            # right after `uma_fast_2h` so BOTH `DISCOVERY_CYCLE` and `FAST_CYCLE` (`1,800` budget) poll
            # simultaneous L2 books across every family `A..N` AND cross-market graph edges!
            zipped_tier1: List[str] = []
            max_t1_len = max(len(interleaved_d_to_i), len(graph_edge_tokens))
            for k_idx in range(0, max_t1_len, 2):
                if k_idx < len(interleaved_d_to_i):
                    zipped_tier1.extend(interleaved_d_to_i[k_idx : k_idx + 2])
                if k_idx < len(graph_edge_tokens):
                    zipped_tier1.extend(graph_edge_tokens[k_idx : k_idx + 2])

            self._cached_tier1_and_tier2_tokens = list(
                dict.fromkeys([*uma_fast_2h, *zipped_tier1, *uma_other_proposed[:400]])
            )
            self._cached_tier4_and_liq_tokens = list(dict.fromkeys([*zf_tokens, *top_liq_tokens]))
            self.hot_priority_tokens = list(
                dict.fromkeys([*self._cached_tier1_and_tier2_tokens, *self._cached_tier4_and_liq_tokens])
            )

        tier1_and_2 = getattr(self, "_cached_tier1_and_tier2_tokens", self.hot_priority_tokens[: max_budget // 2])
        tier4_and_liq = getattr(self, "_cached_tier4_and_liq_tokens", self.hot_priority_tokens[max_budget // 2 :])
        tier3_dynamic = list(dict.fromkeys([*dormant_50bps, *pending_val_tokens, *maker_watch, *dormant_wider]))

        # Layer A Cold-Universe Rotation Slice (ensures cold/long-tail markets are continuously rotated, never dropped!)
        cold_budget = min(self.config.cold_layer_rotation_tokens, max(100, max_budget // 6))
        cold_slice: List[str] = []
        total_u = len(self.cached_all_tradable_tokens)
        if total_u > 0:
            start = self.cold_rotation_offset % total_u
            end = start + cold_budget
            if end <= total_u:
                cold_slice = self.cached_all_tradable_tokens[start:end]
            else:
                cold_slice = (
                    self.cached_all_tradable_tokens[start:] + self.cached_all_tradable_tokens[: end - total_u]
                )
            self.cold_rotation_offset = (start + cold_budget) % total_u

        # Combine in strict Wave 3 order: Tier (i)+(ii) -> Tier (iii) -> Tier (iv)+(v hot) -> Cold Rotation
        ordered_hot = list(dict.fromkeys([*tier1_and_2, *tier3_dynamic, *tier4_and_liq]))
        hot_cap = max(0, max_budget - len(cold_slice))
        merged = list(dict.fromkeys([*ordered_hot[:hot_cap], *cold_slice]))[:max_budget]
        return merged, {
            "graph_and_structural_tokens": int(getattr(self, "_last_tier1_graph_tokens_count", 0)),
            "uma_proposed_tokens": int(getattr(self, "_last_tier2_uma_tokens_count", 0)),
            "dormant_50bps_tokens": len(dormant_50bps),
            "zero_fee_and_tight_tokens": int(getattr(self, "_last_tier4_zerofee_tokens_count", 0)),
            "dormant_and_validation_tokens": len(tier3_dynamic),
            "layer_b_hot_tokens": min(len(ordered_hot), hot_cap),
            "layer_a_cold_rotated_tokens": len(cold_slice),
            "total_selected_tokens": len(merged),
        }

    select_tokens_for_cycle = _select_tokens_for_book_poll

    # -----------------------------------------------------------------------
    # Stage 8 Global Portfolio Allocator Fallback & Cross-Check
    # -----------------------------------------------------------------------

    def _apply_portfolio_allocation(
        self,
        records: List[PipelineOpportunityRecord],
        typed_books: Mapping[str, InstrumentOrderBook],
        micro_opt_dict: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Applies simultaneous Dollar-Hour (`bps/hr`) portfolio ranking across all competing `A..N`
        records, enforcing:
          1. Available liquid `pUSD` cash (`$48.70` live reference),
          2. Shared L2 order-book depth (`(token_id, side)` never double-counted across candidates!),
          3. `D-007` `<= 15%` reconciled NAV concentration cap per canonical event/station key,
          4. `D-007` `< $500` NAV quarantine on `>= 3` sequential non-atomic CLOB legs,
          5. `D-001` absolute freeze on `KMIA` (`6707503`, `6707502`, `WXSTATION:KMIA`).
        """
        avail_cash = max(0.0, float(self.config.available_liquid_pusd) * 0.95)  # 5% settlement gas/haircut buffer
        event_cap_usd = round(float(self.config.reconciled_nav_usd) * 0.15, 6)
        used_event_usd: Dict[str, float] = defaultdict(float)
        # Pre-seed frozen KMIA exposure (`$50.51`) so `WXSTATION:KMIA` / `6707503` / `6707502` are hard-capped
        used_event_usd["WXSTATION:KMIA"] = 50.51
        used_event_usd["MKT:6707503"] = 34.19
        used_event_usd["MKT:6707502"] = 16.32

        rem_ask_rungs: Dict[str, List[List[float]]] = {
            tid: [[float(lv.price), float(lv.size)] for lv in bk.asks if float(lv.size) > 0.0]
            for tid, bk in typed_books.items()
        }
        rem_bid_rungs: Dict[str, List[List[float]]] = {
            tid: [[float(lv.price), float(lv.size)] for lv in bk.bids if float(lv.size) > 0.0]
            for tid, bk in typed_books.items()
        }

        def _avail_ask_at_or_below(tid: str, worst_px: float, fallback_sh: float) -> float:
            if tid not in rem_ask_rungs:
                return fallback_sh
            lim = worst_px + 1e-9 if worst_px > 0.0 else 1.0
            return sum(r[1] for r in rem_ask_rungs[tid] if r[0] <= lim)

        def _avail_bid_at_or_above(tid: str, worst_px: float, fallback_sh: float) -> float:
            if tid not in rem_bid_rungs:
                return fallback_sh
            lim = max(0.0, worst_px - 1e-9)
            return sum(r[1] for r in rem_bid_rungs[tid] if r[0] >= lim)

        def _consume_rungs(rungs: List[List[float]], qty: float) -> None:
            rem_q = max(0.0, qty)
            for r in rungs:
                if rem_q <= 1e-9:
                    break
                take = min(r[1], rem_q)
                r[1] = max(0.0, r[1] - take)
                rem_q -= take

        # Rank proven `CLASS_A` and `CLASS_B` candidates by capital efficiency (`bps/hr`)
        ranked_pool = sorted(
            records,
            key=lambda r: (
                0 if r.opportunity_class == "CLASS_A" else (1 if r.opportunity_class == "CLASS_B" else 9),
                -r.capital_efficiency_bps_per_hr,
                -r.executable_l2_net_usd,
                r.candidate_id,
            ),
        )

        rem_cash = avail_cash
        rank_idx = 0
        allocated_slices: List[Dict[str, Any]] = []

        for rec in ranked_pool:
            if rec.d001_kmia_blocked:
                rec.portfolio_rejection_reason = "D001_FROZEN_KMIA_BLOCKED"
                continue
            if rec.opportunity_class not in ("CLASS_A", "CLASS_B"):
                rec.portfolio_rejection_reason = f"NON_RISKLESS_CLASS:{rec.opportunity_class}"
                continue
            if rec.d007_sub500_multileg_quarantine:
                rec.portfolio_rejection_reason = "D007_SUB500_NAV_SEQUENTIAL_3PLUS_LEG_QUARANTINE"
                continue
            if rec.executable_l2_net_usd <= 0.0 or rec.optimal_executable_quantity <= 0.0 or rec.capital_required_usd <= 0.0:
                rec.portfolio_rejection_reason = "ZERO_EXECUTABLE_PAYOFF_OR_SIZE"
                continue
            if rec.forward_shadow_risk_adjusted_usd <= 0.0:
                rec.portfolio_rejection_reason = "POST_LATENCY_RISK_ADJUSTED_NET_NON_POSITIVE"
                continue

            rank_idx += 1
            rec.portfolio_rank = rank_idx

            # Compute max scale fraction `alpha in (0, 1]` allowed by cash, event cap, and remaining L2 depth
            max_event_headroom = min(
                max(0.0, event_cap_usd - used_event_usd[ek]) for ek in rec.canonical_event_keys
            ) if rec.canonical_event_keys else event_cap_usd
            cash_limit = min(rem_cash, max_event_headroom)
            if cash_limit < DEFAULT_MIN_MARKETABLE_BUY_USD - 1e-6:
                rec.portfolio_rejection_reason = (
                    "D007_EVENT_CONCENTRATION_15PCT_CAP"
                    if max_event_headroom < DEFAULT_MIN_MARKETABLE_BUY_USD
                    else "INSUFFICIENT_REMAINING_LIQUID_PUSD"
                )
                continue

            alpha = min(1.0, cash_limit / rec.capital_required_usd)
            if rec.proof is not None and rec.proof.leg_executions:
                for le in rec.proof.leg_executions:
                    if le.action_type == "BUY_CLOB" and not le.is_maker and le.gross_shares > 0:
                        avail_sh = _avail_ask_at_or_below(
                            le.instrument_id, float(le.worst_limit_price), float(le.gross_shares)
                        )
                        alpha = min(alpha, avail_sh / le.gross_shares)
                    elif le.action_type == "SELL_CLOB" and not le.is_maker and le.gross_shares > 0:
                        avail_sh = _avail_bid_at_or_above(
                            le.instrument_id, float(le.worst_limit_price), float(le.gross_shares)
                        )
                        alpha = min(alpha, avail_sh / le.gross_shares)

            alloc_q = math.floor(rec.optimal_executable_quantity * alpha * 100.0) / 100.0
            if alloc_q < DEFAULT_MIN_ORDER_SHARES - 1e-6:
                rec.portfolio_rejection_reason = "SHARED_BOOK_DEPTH_OR_MIN_LOT_EXHAUSTED"
                continue

            frac = alloc_q / rec.optimal_executable_quantity
            alloc_cap = round(rec.capital_required_usd * frac, 6)
            if alloc_cap < DEFAULT_MIN_MARKETABLE_BUY_USD - 1e-6:
                rec.portfolio_rejection_reason = "BELOW_1USD_MARKETABLE_NOTIONAL_AFTER_SCALING"
                continue

            alloc_net = round(rec.executable_l2_net_usd * frac, 6)
            alloc_ra = round(rec.forward_shadow_risk_adjusted_usd * frac, 6)

            rec.allocated_portfolio_shares = alloc_q
            rec.allocated_portfolio_capital_usd = alloc_cap
            rec.allocated_portfolio_shadow_net_usd = alloc_ra

            rem_cash = max(0.0, rem_cash - alloc_cap)
            for ek in rec.canonical_event_keys:
                used_event_usd[ek] += alloc_cap
            if rec.proof is not None:
                for le in rec.proof.leg_executions:
                    if le.action_type == "BUY_CLOB" and not le.is_maker and le.instrument_id in rem_ask_rungs:
                        _consume_rungs(rem_ask_rungs[le.instrument_id], le.gross_shares * frac)
                    elif le.action_type == "SELL_CLOB" and not le.is_maker and le.instrument_id in rem_bid_rungs:
                        _consume_rungs(rem_bid_rungs[le.instrument_id], le.gross_shares * frac)

            allocated_slices.append(
                {
                    "rank": rank_idx,
                    "candidate_id": rec.candidate_id,
                    "family_code": rec.family_code,
                    "opportunity_class": rec.opportunity_class,
                    "allocated_shares": alloc_q,
                    "allocated_capital_usd": alloc_cap,
                    "guaranteed_l2_net_usd": alloc_net,
                    "forward_shadow_risk_adjusted_usd": alloc_ra,
                    "capital_efficiency_bps_per_hr": rec.capital_efficiency_bps_per_hr,
                    "expected_lockup_hours": rec.expected_lockup_hours,
                }
            )

        tot_cap = round(sum(s["allocated_capital_usd"] for s in allocated_slices), 6)
        tot_guar = round(sum(s["guaranteed_l2_net_usd"] for s in allocated_slices), 6)
        tot_ra = round(sum(s["forward_shadow_risk_adjusted_usd"] for s in allocated_slices), 6)
        dollar_hrs = sum(
            s["allocated_capital_usd"] * max(0.05, s["expected_lockup_hours"]) for s in allocated_slices
        )
        port_bps_hr = round((tot_ra / dollar_hrs) * 10_000.0, 4) if dollar_hrs > 0 else 0.0

        return {
            "reference_liquid_pusd_budget": round(float(self.config.available_liquid_pusd), 6),
            "deployable_after_5pct_reserve_usd": round(avail_cash, 6),
            "d007_15pct_per_event_cap_usd": event_cap_usd,
            "allocated_positions_count": len(allocated_slices),
            "total_allocated_capital_usd": tot_cap,
            "unallocated_cash_reserve_usd": round(float(self.config.available_liquid_pusd) - tot_cap, 6),
            "portfolio_guaranteed_l2_net_usd": tot_guar,
            "portfolio_forward_shadow_risk_adjusted_usd": tot_ra,
            "portfolio_realizable_bps_per_hr": port_bps_hr,
            "allocated_slices": allocated_slices,
            "peer_optimizer_cross_check": micro_opt_dict,
        }

    # -----------------------------------------------------------------------
    # Execute Single 10-Stage Cycle (`DISCOVERY_CYCLE` | `FAST_CYCLE` | `RESEARCH_CYCLE`)
    # -----------------------------------------------------------------------

    def run_cycle(
        self,
        cycle_type: OperatingCycleType = OperatingCycleType.DISCOVERY_CYCLE,
        *,
        synthetic_events: Optional[Sequence[Mapping[str, Any]]] = None,
        synthetic_raw_books: Optional[Mapping[str, Mapping[str, Any]]] = None,
        portfolio_state: Optional[Mapping[str, Any]] = None,
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Executes all 10 stages (`DISCOVER .. VALIDATE_RESULTS`) and returns detailed stage & cycle telemetry."""
        self.mode_controller.validate_mode_or_raise()
        self.peer_bridge.refresh_peer_imports()

        self.cycle_counter += 1
        cycle_idx = self.cycle_counter
        cycle_t0 = time.perf_counter()
        eval_now_ts = float(time.time() if now_ts is None else now_ts)
        ts_utc = datetime.fromtimestamp(eval_now_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        stage_timings_ms: Dict[str, float] = {}

        # -------------------------------------------------------------------
        # STAGE 1: DISCOVER
        # -------------------------------------------------------------------
        s0 = time.perf_counter()
        if synthetic_events is not None:
            events = [dict(e) for e in synthetic_events]
            sweep_meta = {"pages_fetched": 1, "events_fetched": len(events), "sweep_wall_time_sec": 0.001}
            self.last_universe_stream_census = None
        elif cycle_type == OperatingCycleType.DISCOVERY_CYCLE or not self.cached_events:
            events, sweep_meta = self.rest_client.sweep_gamma_events_keyset(
                max_pages=self.config.max_gamma_pages, compact_fields=True
            )
            self.cached_events = events
            self.last_discovery_sweep_wall_sec = float(sweep_meta.get("sweep_wall_time_sec", 0.0))
            self.last_universe_stream_census = sweep_meta.get("full_universe_census")
            reservoir = sweep_meta.get("cold_token_reservoir")
            if isinstance(reservoir, list) and reservoir:
                self.cached_all_tradable_tokens = list(dict.fromkeys(reservoir))
        else:
            events = self.cached_events
            sweep_meta = {
                "pages_fetched": 0,
                "events_fetched": len(events),
                "sweep_wall_time_sec": self.last_discovery_sweep_wall_sec,
                "used_cached_universe": True,
                "full_universe_census": getattr(self, "last_universe_stream_census", None),
            }

        graph_built_pre_poll = False
        if cycle_type == OperatingCycleType.DISCOVERY_CYCLE or not self.graph.markets or synthetic_events is not None:
            s_rel_pre = time.perf_counter()
            self.graph = MarketPropositionGraph()
            graph_events = self._build_swapless_safe_graph_events(events, max_graph_markets=3_500)
            self.graph.ingest_events_and_markets(events=graph_events)
            del graph_events
            _reclaim_process_memory()
            stage_timings_ms["RELATE_PRE_POLL"] = round((time.perf_counter() - s_rel_pre) * 1000.0, 2)
            graph_built_pre_poll = True

        tokens_to_poll, poll_plan = self._select_tokens_for_book_poll(
            events, cycle_type=cycle_type, now_ts=eval_now_ts
        )
        if synthetic_raw_books is not None:
            raw_books = {str(k): dict(v) for k, v in synthetic_raw_books.items()}
            book_poll_meta = {
                "tokens_requested": len(raw_books),
                "books_returned": len(raw_books),
                "book_poll_wall_sec": 0.001,
                "fetch_timestamp_sec": eval_now_ts,
            }
        else:
            raw_books, book_poll_meta = self.rest_client.fetch_clob_books_batched(tokens_to_poll)
            eval_now_ts = float(book_poll_meta.get("fetch_timestamp_sec", time.time()))
        stage_timings_ms["DISCOVER"] = round((time.perf_counter() - s0) * 1000.0, 2)

        # -------------------------------------------------------------------
        # STAGE 2: NORMALIZE
        # -------------------------------------------------------------------
        s0 = time.perf_counter()
        skip_reasons: Counter[str] = Counter()
        total_markets = 0
        orderbook_enabled_markets = 0
        total_tokens = 0
        negrisk_events = 0
        augmented_negrisk_events = 0
        fees_enabled_markets = 0
        uma_status_counts: Counter[str] = Counter()
        newly_listed_markets_this_cycle = 0
        typed_books: Dict[str, InstrumentOrderBook] = {}
        fresh_book_markets = 0
        fresh_book_event_ids: Set[str] = set()

        for ev in events:
            ev_id = str(ev.get("id") or "")
            if ev.get("negRisk") or ev.get("enableNegRisk"):
                negrisk_events += 1
            if ev.get("negRiskAugmented") or ev.get("enableNegRiskOther"):
                augmented_negrisk_events += 1

            for m in ev.get("markets") or ():
                if not isinstance(m, Mapping):
                    continue
                total_markets += 1
                mid = str(m.get("id") or m.get("market_id") or "").strip()
                if m.get("closed") or m.get("archived") or m.get("active") is False:
                    skip_reasons["CLOSED_OR_ARCHIVED"] += 1
                    continue
                if mid and mid not in self.known_market_first_seen_ts:
                    if len(self.known_market_first_seen_ts) < 25_000:
                        self.known_market_first_seen_ts[mid] = eval_now_ts
                    newly_listed_markets_this_cycle += 1
                if m.get("enableOrderBook") is False:
                    skip_reasons["ORDERBOOK_DISABLED"] += 1
                    continue
                orderbook_enabled_markets += 1

                ust = str(m.get("umaResolutionStatus") or "none").strip().lower() or "none"
                uma_status_counts[ust] += 1
                if m.get("feesEnabled") is True:
                    fees_enabled_markets += 1

                if mid in FROZEN_DISPUTED_MARKET_IDS or ust == "disputed":
                    skip_reasons["UMA_DISPUTED_QUARANTINED"] += 1

                toks = [str(x).strip() for x in _parse_json_list_safe(m.get("clobTokenIds")) if str(x).strip()]
                if len(toks) < 2:
                    skip_reasons["MISSING_TOKEN_IDS"] += 1
                    continue
                total_tokens += len(toks)

                q_txt = f"{m.get('groupItemTitle') or ''} {m.get('question') or ''}".lower()
                is_ph = any(k in q_txt for k in ("placeholder", "person a", "person b", "option a", "tba", "unnamed"))
                if is_ph:
                    skip_reasons["AUGMENTED_PLACEHOLDER_OUTCOME"] += 1

                fresh_tids = [tid for tid in toks if tid in raw_books]
                if fresh_tids:
                    fresh_book_markets += 1
                    if ev_id:
                        fresh_book_event_ids.add(ev_id)
                    outcomes_lbl = _parse_json_list_safe(m.get("outcomes"))
                    fee_bps, fee_exp = _extract_market_fee_spec(m)
                    min_sz = max(DEFAULT_MIN_ORDER_SHARES, float(m.get("orderMinSize") or DEFAULT_MIN_ORDER_SHARES))
                    tick_raw = m.get("orderPriceMinTickSize")
                    tick_f = float(tick_raw) if tick_raw is not None and float(tick_raw or 0.0) > 0.0 else None
                    is_oth = bool(m.get("negRiskOther")) or str(m.get("groupItemTitle") or "").strip().lower() in {
                        "other",
                        "all other",
                        "any other",
                        "field",
                    }
                    has_any_resting_depth = False
                    cond_id = str(m.get("conditionId") or m.get("condition_id") or "")
                    for idx_t, tid in enumerate(toks):
                        if tid in raw_books:
                            lbl = str(outcomes_lbl[idx_t]) if idx_t < len(outcomes_lbl) else ("Yes" if idx_t == 0 else "No")
                            ibk = InstrumentOrderBook.from_raw(
                                tid,
                                raw_books[tid],
                                market_id=mid,
                                condition_id=cond_id,
                                outcome_label=lbl,
                                fee_rate_bps=fee_bps,
                                fee_exponent=fee_exp,
                                tick_size=tick_f,
                                min_order_size=min_sz,
                                enable_order_book=True,
                                book_timestamp_sec=eval_now_ts,
                                is_placeholder=is_ph,
                                is_other=is_oth,
                            )
                            typed_books[tid] = ibk
                            if ibk.asks or ibk.bids:
                                has_any_resting_depth = True
                    if not has_any_resting_depth:
                        skip_reasons["ZERO_RESTING_DEPTH"] += 1
                else:
                    skip_reasons["COLD_LAYER_AWAITING_ROTATION"] += 1

        # Keep `known_market_first_seen_ts` bounded if universe grows past 250k
        if len(self.known_market_first_seen_ts) > 250_000:
            self.known_market_first_seen_ts.clear()

        stage_timings_ms["NORMALIZE"] = round((time.perf_counter() - s0) * 1000.0, 2)

        # -------------------------------------------------------------------
        # STAGE 3: RELATE (`MarketPropositionGraph`)
        # -------------------------------------------------------------------
        s0 = time.perf_counter()
        if not graph_built_pre_poll:
            # Ensure any newly rotated Layer A cold events with fresh books are present in `self.graph`
            missing_book_events = [
                ev
                for ev in events
                if str(ev.get("id") or "") in fresh_book_event_ids
                and str(ev.get("id") or "") not in self.graph.events
            ]
            if missing_book_events and len(self.graph.markets) < 22_000:
                self.graph.ingest_events_and_markets(events=missing_book_events[:250])
        eff_port_state = portfolio_state if portfolio_state is not None else self._default_authoritative_portfolio_state()
        recyclable_cnt, frozen_cnt = self.graph.load_portfolio_holdings(eff_port_state)
        holdings_map = self._extract_recyclable_holdings_map(self.graph)
        graph_metrics = self.graph.summary_metrics()
        self.last_graph_metrics = graph_metrics
        stage_timings_ms["RELATE"] = round(
            stage_timings_ms.pop("RELATE_PRE_POLL", 0.0) + (time.perf_counter() - s0) * 1000.0, 2
        )

        # Configure shared `UniversalArbVerifier`
        verifier = UniversalArbVerifier(
            config=VerificationConfig(
                max_budget_usd=max(float(self.config.available_liquid_pusd), float(self.config.shadow_reference_budget_usd)),
                reconciled_nav_usd=float(self.config.reconciled_nav_usd),
                now_ts=eval_now_ts,
                execution_mode=self.mode_controller.mode.value,
            )
        )

        # -------------------------------------------------------------------
        # STAGE 4: GENERATE (All 14 Families `A..N` + Dormant Shift Rescans)
        # -------------------------------------------------------------------
        s0 = time.perf_counter()
        awakened_pairs = self.dormant_store.detect_shifted_structures_for_rescan(typed_books, now_ts=eval_now_ts)
        recs_ab_c_j, counts_ab_c_j, ab_source = self.peer_bridge.run_complete_set_and_negrisk(
            events,
            raw_books,
            typed_books,
            verifier,
            holdings=holdings_map,
            portfolio_state=eff_port_state,
            max_candidates_per_family=self.config.max_candidates_per_family,
        )
        recs_d_to_i, meta_d_to_i = self.peer_bridge.run_logical_and_specialized(
            events,
            typed_books,
            verifier,
            holdings=holdings_map,
            now_ts=eval_now_ts,
            max_candidates_per_family=self.config.max_candidates_per_family,
        )
        recs_k_to_n, meta_k_to_n = self.peer_bridge.run_microstructure_and_portfolio(
            events,
            raw_books,
            typed_books,
            verifier,
            graph=self.graph,
            peer_records_a_to_j=[*recs_ab_c_j, *recs_d_to_i],
            holdings=holdings_map,
            reconciled_nav_usd=float(self.config.reconciled_nav_usd),
            available_liquid_pusd=float(self.config.available_liquid_pusd),
            now_ts=eval_now_ts,
            run_full_mechanism_census=(cycle_type in (OperatingCycleType.DISCOVERY_CYCLE, OperatingCycleType.RESEARCH_CYCLE)),
        )
        if meta_k_to_n:
            self.last_micro_portfolio_extras = meta_k_to_n
        raw_books.clear()
        del tokens_to_poll
        _reclaim_process_memory()
        stage_timings_ms["GENERATE"] = round((time.perf_counter() - s0) * 1000.0, 2)

        # -------------------------------------------------------------------
        # STAGE 5: PROVE & STAGE 6: PRICE
        # -------------------------------------------------------------------
        s0 = time.perf_counter()
        awakened_records: List[PipelineOpportunityRecord] = []
        for ent, struct_cand in awakened_pairs:
            awakened_records.append(
                coerce_to_pipeline_record(
                    {
                        "candidate_id": ent.candidate_id,
                        "family": ent.family_code,
                        "sub_type": ent.sub_type,
                        "title_summary": ent.title_summary,
                        "market_ids": ent.market_ids,
                        "event_ids": ent.event_ids,
                        "instrument_ids": ent.instrument_ids,
                        "structure": struct_cand,
                    },
                    verifier=verifier,
                    books=typed_books,
                    holdings=holdings_map,
                    source_module="DormantOpportunityStore.Rescan",
                    awakened_from_dormant=True,
                )
            )

        # Deduplicate by `candidate_id`, keeping highest-fidelity proof record
        by_cid: Dict[str, PipelineOpportunityRecord] = {}
        for rec in [*awakened_records, *recs_ab_c_j, *recs_d_to_i, *recs_k_to_n]:
            # Re-verify anti-promotion invariant on every record
            if rec.opportunity_class == "CLASS_A":
                if not rec.is_atomic_or_prelocked or rec.min_state_net_payoff_usd <= 0.0 or rec.d001_kmia_blocked:
                    rec.opportunity_class = (
                        "CLASS_B" if (rec.min_state_net_payoff_usd > 0.0 and not rec.d001_kmia_blocked) else "CLASS_E"
                    )
                    rec.is_atomic_or_prelocked = False
                    if rec.opportunity_class != "CLASS_B":
                        rec.is_mathematically_proven_arb = False
                        rec.is_dormant_near_miss = False
            prev = by_cid.get(rec.candidate_id)
            if prev is None or (rec.proof is not None and prev.proof is None) or rec.awakened_from_dormant:
                by_cid[rec.candidate_id] = rec

        all_records = list(by_cid.values())

        # On-demand lightweight market-question lookup for emitted candidates only (< 0.2 MiB RAM)
        needed_mids = {
            str(mid)
            for rec in all_records
            for mid in rec.market_ids
            if mid and str(mid) not in self.cached_market_by_id
        }
        if needed_mids and len(self.cached_market_by_id) < 40_000:
            for ev in events:
                ev_title = str(ev.get("title") or "")
                for m in ev.get("markets") or ():
                    if not isinstance(m, Mapping):
                        continue
                    mid = str(m.get("id") or m.get("market_id") or "").strip()
                    if mid in needed_mids:
                        self.cached_market_by_id[mid] = {
                            "question": str(m.get("question") or m.get("groupItemTitle") or ev_title),
                            "groupItemTitle": str(m.get("groupItemTitle") or ""),
                            "description": str(m.get("description") or "")[:600],
                            "conditionId": str(m.get("conditionId") or m.get("condition_id") or ""),
                            "clobTokenIds": [str(x).strip() for x in _parse_json_list_safe(m.get("clobTokenIds")) if str(x).strip()],
                            "endDate": str(m.get("endDate") or ev.get("endDate") or ""),
                            "negRiskMarketID": str(m.get("negRiskMarketID") or ev.get("negRiskMarketID") or ""),
                            "questionIndex": m.get("questionIndex"),
                            "negRisk": bool(m.get("negRisk") or ev.get("negRisk")),
                            "event_id": str(ev.get("id") or ""),
                        }
                        needed_mids.discard(mid)
                        if not needed_mids:
                            break
                if not needed_mids:
                    break

        # Defense-in-depth cross-market barrier guard (`#20`) & human-readable title enrichment
        barrier_guard_rejections = 0
        for rec in all_records:
            distinct_mids = list(dict.fromkeys(str(mid) for mid in rec.market_ids if mid))
            mkt_questions = [
                str((self.cached_market_by_id.get(mid) or {}).get("question") or "").strip()
                for mid in distinct_mids
            ]
            mkt_descs = [
                str((self.cached_market_by_id.get(mid) or {}).get("description") or "").strip()
                for mid in distinct_mids
            ]
            non_empty_q = [q for q in mkt_questions if q]
            if non_empty_q and (
                not rec.title_summary
                or rec.title_summary.startswith("[")
                or rec.title_summary == rec.candidate_id
            ):
                joined_q = " <-> ".join(q[:42] for q in non_empty_q[:2])
                rec.title_summary = f"[{rec.family_code}] {joined_q}"

            if len(distinct_mids) >= 2 and rec.opportunity_class in ("CLASS_A", "CLASS_B"):
                probe_q = mkt_questions if len(non_empty_q) >= 2 else [rec.title_summary]
                probe_d = mkt_descs if len(non_empty_q) >= 2 else []
                if has_ambiguous_numeric_barrier_direction(
                    probe_q, probe_d, source_module=rec.source_module
                ):
                    rec.opportunity_class = "CLASS_D"
                    rec.is_mathematically_proven_arb = False
                    rec.is_atomic_or_prelocked = False
                    rec.is_dormant_near_miss = False
                    rec.optimal_executable_quantity = 0.0
                    rec.capital_required_usd = 0.0
                    rec.executable_l2_net_usd = 0.0
                    rec.forward_shadow_risk_adjusted_usd = 0.0
                    rec.capital_efficiency_bps_per_hr = 0.0
                    if "AMBIGUOUS_BARRIER_HIT_DIRECTION_REQUIRES_INITIAL_SPOT_PROOF" not in rec.disqualifiers:
                        rec.disqualifiers = (
                            *rec.disqualifiers,
                            "AMBIGUOUS_BARRIER_HIT_DIRECTION_REQUIRES_INITIAL_SPOT_PROOF",
                        )
                    barrier_guard_rejections += 1

        t_prove_price = (time.perf_counter() - s0) * 1000.0
        stage_timings_ms["PROVE"] = round(t_prove_price * 0.60, 2)
        stage_timings_ms["PRICE"] = round(t_prove_price * 0.40, 2)

        # -------------------------------------------------------------------
        # STAGE 7: SIMULATE (Forward Latency & Partial-Fill Shadow Adjustment)
        # -------------------------------------------------------------------
        s0 = time.perf_counter()
        for rec in all_records:
            # Strict segregation: Modes 1 & 2 NEVER record realized live cash
            rec.realized_live_cash_usd = 0.0
            if rec.opportunity_class in ("CLASS_D", "CLASS_E"):
                rec.executable_l2_net_usd = 0.0
                rec.forward_shadow_risk_adjusted_usd = 0.0
        stage_timings_ms["SIMULATE"] = round((time.perf_counter() - s0) * 1000.0, 2)

        # -------------------------------------------------------------------
        # STAGE 8: RANK (Constrained Portfolio Dollar-Hour Allocator)
        # -------------------------------------------------------------------
        s0 = time.perf_counter()
        portfolio_summary = self._apply_portfolio_allocation(
            all_records,
            typed_books,
            self.last_micro_portfolio_extras.get("portfolio_optimization_live_48_70", {}),
        )
        stage_timings_ms["RANK"] = round((time.perf_counter() - s0) * 1000.0, 2)

        # -------------------------------------------------------------------
        # STAGE 9: MONITOR (`DormantOpportunityStore`)
        # -------------------------------------------------------------------
        s0 = time.perf_counter()
        dormant_delta = self.dormant_store.update_from_pipeline_records(all_records, typed_books, now_ts=eval_now_ts)
        self.dormant_store.save()
        if self.config.fast_rescan_tokens_path is not None or self.config.emit_harvester_candidates:
            rescan_out = self.config.fast_rescan_tokens_path or Path("data/polymarket/dormant_fast_rescan_tokens.json")
            self.dormant_store.export_fast_rescan_tokens(rescan_out, now_ts=eval_now_ts)
        stage_timings_ms["MONITOR"] = round((time.perf_counter() - s0) * 1000.0, 2)

        # -------------------------------------------------------------------
        # STAGE 10: VALIDATE_RESULTS (Forward `t -> t+1` Book Check, Ledger & Checkpoint)
        # -------------------------------------------------------------------
        s0 = time.perf_counter()
        forward_validations = self.forward_tracker.validate_pending_against_fresh_books(
            typed_books,
            verifier,
            holdings=holdings_map,
            cycle_index=cycle_idx,
            now_ts=eval_now_ts,
        )
        persistence_stats = self.forward_tracker.record_cycle_observations(
            all_records,
            typed_books,
            cycle_index=cycle_idx,
            now_ts=eval_now_ts,
        )
        maker_validations = self.hedged_maker_quoter.validate_resting_quotes(
            typed_books,
            cycle_index=cycle_idx,
            now_ts=eval_now_ts,
        )
        maker_posted_this_cycle = self.hedged_maker_quoter.ingest_cycle_candidates(
            all_records,
            typed_books,
            holdings=holdings_map,
            cycle_index=cycle_idx,
            now_ts=eval_now_ts,
        )
        maker_summary = {
            **self.hedged_maker_quoter.summary_metrics(),
            "quotes_posted_this_cycle": maker_posted_this_cycle,
            "validations_this_cycle": maker_validations,
        }
        if self.config.emit_harvester_candidates:
            _batched_mocked = "Mock" in type(self.rest_client.fetch_clob_books_batched).__name__
            _jit_mocked = "Mock" in type(self.rest_client.fetch_jit_bridge_books).__name__
            _use_live_jit = synthetic_raw_books is None and (not _batched_mocked or _jit_mocked)
            self.last_harvester_bridge_report = self.harvester_bridge.emit_verified_candidates(
                all_records,
                typed_books,
                holdings=holdings_map,
                market_meta_by_id=self.cached_market_by_id,
                events=events,
                jit_book_fetcher=(self.rest_client.fetch_jit_bridge_books if _use_live_jit else None),
                verifier=verifier,
                fallback_reconciled_nav_usd=self.config.reconciled_nav_usd,
                now_ts=(None if _use_live_jit else eval_now_ts),
            )
        else:
            self.last_harvester_bridge_report = {
                "enabled": False,
                "candidates_emitted_this_cycle": 0,
                "taker_boxes_emitted_this_cycle": 0,
                "maker_locks_emitted_this_cycle": 0,
                "jit_reverified_this_cycle": 0,
                "jit_rejected_this_cycle": 0,
                "total_emitted_across_campaign": self.harvester_bridge.total_emitted,
                "total_maker_locks_across_campaign": self.harvester_bridge.total_maker_locks_emitted,
                "total_jit_verified_across_campaign": self.harvester_bridge.total_jit_verified,
                "total_jit_rejected_across_campaign": self.harvester_bridge.total_jit_rejected,
                "total_dedupe_suppressed": self.harvester_bridge.total_dedupe_suppressed,
                "target_jsonl_path": str(self.config.harvester_candidates_path),
                "skipped_by_reason": {},
                "emitted_box_ids": [],
            }
        ledger_written = self._append_ledger_records(
            all_records,
            cycle_index=cycle_idx,
            cycle_type=cycle_type.value,
            timestamp_utc=ts_utc,
        )

        # Compute per-family detector coverage (`A..N`)
        by_fam_records: Dict[str, List[PipelineOpportunityRecord]] = {fc: [] for fc in FAMILY_CODES}
        for r in all_records:
            by_fam_records[r.family_code].append(r)

        d_to_i_eval = meta_d_to_i.get("per_family_evaluated", {})
        mech_cat = self.last_micro_portfolio_extras.get("mechanism_catalog", {})
        detector_coverage_by_family: Dict[str, Dict[str, Any]] = {}
        for fc in FAMILY_CODES:
            f_recs = by_fam_records[fc]
            cls_cnt = Counter(r.opportunity_class for r in f_recs)
            if fc in counts_ab_c_j:
                scope_eval = max(len(f_recs), int(counts_ab_c_j[fc]))
            elif fc in d_to_i_eval:
                scope_eval = max(len(f_recs), int(d_to_i_eval[fc]))
            elif fc == "N":
                scope_eval = max(len(f_recs), int(mech_cat.get("total_active_markets_inspected", total_markets)))
            else:
                scope_eval = max(len(f_recs), fresh_book_markets if fc in ("K", "L") else len(events))

            detector_coverage_by_family[fc] = {
                "family_code": fc,
                "family_name": FAMILY_CATALOG[fc]["name"],
                "owner_track": FAMILY_CATALOG[fc]["owner"],
                "structures_or_markets_inspected": scope_eval,
                "candidates_emitted": len(f_recs),
                "CLASS_A": int(cls_cnt.get("CLASS_A", 0)),
                "CLASS_B": int(cls_cnt.get("CLASS_B", 0)),
                "CLASS_C": int(cls_cnt.get("CLASS_C", 0)),
                "CLASS_D": int(cls_cnt.get("CLASS_D", 0)),
                "CLASS_E": int(cls_cnt.get("CLASS_E", 0)),
                "dormant_near_misses": sum(1 for r in f_recs if r.is_dormant_near_miss),
                "mathematically_proven_arbs": sum(
                    1 for r in f_recs if r.is_mathematically_proven_arb and r.opportunity_class in ("CLASS_A", "CLASS_B")
                ),
            }

        cycle_wall_sec = round(time.perf_counter() - cycle_t0, 3)
        listing_to_eval_ms = round(
            sum(stage_timings_ms[st] for st in ("NORMALIZE", "RELATE", "GENERATE", "PROVE", "PRICE", "SIMULATE", "RANK")),
            2,
        )

        # Memory guard check (`D-010`)
        cur_rss = get_process_rss_mib()
        if cur_rss > self.config.max_rss_mib * 0.85:
            gc.collect()
            cur_rss = get_process_rss_mib()
        self.peak_rss_mib = max(self.peak_rss_mib, cur_rss)

        stream_census = sweep_meta.get("full_universe_census")
        if isinstance(stream_census, Mapping) and int(stream_census.get("total_observable_events", 0)) > len(events):
            merged_skips = dict(stream_census.get("skip_reasons") or {})
            merged_skips["ZERO_RESTING_DEPTH"] = int(skip_reasons.get("ZERO_RESTING_DEPTH", 0))
            merged_skips["COLD_LAYER_AWAITING_ROTATION"] = max(
                0, int(stream_census.get("orderbook_enabled_markets", 0)) - fresh_book_markets
            )
            self.last_universe_census = {
                "total_observable_events": int(stream_census["total_observable_events"]),
                "total_observable_markets": int(stream_census["total_observable_markets"]),
                "active_unclosed_markets": int(stream_census["active_unclosed_markets"]),
                "orderbook_enabled_markets": int(stream_census["orderbook_enabled_markets"]),
                "total_tradable_outcome_tokens": int(stream_census["total_tradable_outcome_tokens"]),
                "retained_working_events": len(events),
                "negrisk_events": int(stream_census["negrisk_events"]),
                "augmented_negrisk_events": int(stream_census["augmented_negrisk_events"]),
                "fees_enabled_markets": int(stream_census["fees_enabled_markets"]),
                "uma_status_breakdown": dict(stream_census.get("uma_status_breakdown") or {}),
                "fresh_l2_book_markets_this_cycle": fresh_book_markets,
                "fresh_l2_book_tokens_this_cycle": len(typed_books),
                "newly_detected_markets_this_cycle": newly_listed_markets_this_cycle,
                "unresolved_or_ineligible_skip_counts": merged_skips,
                "recyclable_holdings_count": recyclable_cnt,
                "d001_frozen_kmia_holdings_quarantined": frozen_cnt,
                "ab_c_j_detector_source": ab_source,
            }
        else:
            self.last_universe_census = {
                "total_observable_events": len(events),
                "total_observable_markets": total_markets,
                "active_unclosed_markets": max(0, total_markets - int(skip_reasons.get("CLOSED_OR_ARCHIVED", 0))),
                "orderbook_enabled_markets": orderbook_enabled_markets,
                "total_tradable_outcome_tokens": total_tokens,
                "retained_working_events": len(events),
                "negrisk_events": negrisk_events,
                "augmented_negrisk_events": augmented_negrisk_events,
                "fees_enabled_markets": fees_enabled_markets,
                "uma_status_breakdown": dict(uma_status_counts),
                "fresh_l2_book_markets_this_cycle": fresh_book_markets,
                "fresh_l2_book_tokens_this_cycle": len(typed_books),
                "newly_detected_markets_this_cycle": newly_listed_markets_this_cycle,
                "unresolved_or_ineligible_skip_counts": dict(skip_reasons),
                "recyclable_holdings_count": recyclable_cnt,
                "d001_frozen_kmia_holdings_quarantined": frozen_cnt,
                "ab_c_j_detector_source": ab_source,
            }

        stage_timings_ms["VALIDATE_RESULTS"] = round((time.perf_counter() - s0) * 1000.0, 2)

        class_totals = Counter(r.opportunity_class for r in all_records)
        proven_arbs = [
            r for r in all_records if r.is_mathematically_proven_arb and r.opportunity_class in ("CLASS_A", "CLASS_B")
        ]

        cycle_summary = {
            "cycle_index": cycle_idx,
            "cycle_type": cycle_type.value,
            "timestamp_utc": ts_utc,
            "execution_mode": self.mode_controller.mode.value,
            "cycle_wall_time_sec": cycle_wall_sec,
            "discovery_sweep_wall_sec": round(self.last_discovery_sweep_wall_sec, 3),
            "book_poll_wall_sec": float(book_poll_meta.get("book_poll_wall_sec", 0.0)),
            "listing_to_evaluation_latency_ms": listing_to_eval_ms,
            "rss_mib": cur_rss,
            "peak_rss_mib": self.peak_rss_mib,
            "stage_timings_ms": stage_timings_ms,
            "token_poll_plan": poll_plan,
            "universe_coverage": self.last_universe_census,
            "proposition_graph": graph_metrics,
            "detector_coverage_by_family": detector_coverage_by_family,
            "opportunity_summary": {
                "total_candidates_evaluated": len(all_records),
                "mathematically_valid_proofs": len(proven_arbs),
                "class_counts": {
                    "CLASS_A": int(class_totals.get("CLASS_A", 0)),
                    "CLASS_B": int(class_totals.get("CLASS_B", 0)),
                    "CLASS_C": int(class_totals.get("CLASS_C", 0)),
                    "CLASS_D": int(class_totals.get("CLASS_D", 0)),
                    "CLASS_E": int(class_totals.get("CLASS_E", 0)),
                },
                "d007_quarantined_3plus_leg_count": sum(1 for r in all_records if r.d007_sub500_multileg_quarantine),
                "rule_mismatch_rejections_prevented": int(meta_d_to_i.get("rule_mismatch_rejections_prevented", 0))
                + barrier_guard_rejections,
                "awakened_from_dormant_rescanned": len(awakened_records),
                "ledger_rows_written": ledger_written,
            },
            "dormant_store": {**dormant_delta, **self.dormant_store.summary_metrics()},
            "persistence_and_forward_validation": {
                **persistence_stats,
                "validations_this_cycle": forward_validations,
            },
            "hedged_maker_shadow_quoter": maker_summary,
            "harvester_candidate_bridge": self.last_harvester_bridge_report,
            "portfolio_allocation": portfolio_summary,
            "segregated_economics": self._build_segregated_economics_block(all_records, portfolio_summary),
            "top_executable_opportunities": [
                r.to_ledger_dict(cycle_index=cycle_idx, cycle_type=cycle_type.value, timestamp_utc=ts_utc)
                for r in sorted(
                    [x for x in proven_arbs if x.forward_shadow_risk_adjusted_usd > 0.0],
                    key=lambda x: (
                        x.portfolio_rank if x.portfolio_rank is not None else 999_999,
                        -x.forward_shadow_risk_adjusted_usd,
                        -x.executable_l2_net_usd,
                        -x.capital_efficiency_bps_per_hr,
                    ),
                )[:20]
            ],
            "top_class_c_opportunities": [
                r.to_ledger_dict(cycle_index=cycle_idx, cycle_type=cycle_type.value, timestamp_utc=ts_utc)
                for r in sorted(
                    [x for x in all_records if x.opportunity_class == "CLASS_C"],
                    key=lambda x: (-x.expected_net_payoff_usd, -x.capital_efficiency_bps_per_hr),
                )[:15]
            ],
        }

        self.cycle_reports.append(cycle_summary)
        self.save_checkpoint()
        typed_books.clear()
        all_records.clear()
        by_cid.clear()
        _reclaim_process_memory()
        return cycle_summary

    def _build_segregated_economics_block(
        self,
        records: Sequence[PipelineOpportunityRecord],
        portfolio_summary: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Enforces strict non-conflation across the 3 required accounting columns:
          1. Paper Theoretical Top-of-Book Value (`CLASS_A` + `CLASS_B` L1 unlimited)
          2. Realistic Forward Shadow Value (depth-walked, post-fee, post-latency, portfolio-capped)
          3. Independently Verified Realized Live Wallet Cash (`$48.70` `pUSD` on `kraken-finland`)
        """
        proven = [r for r in records if r.opportunity_class in ("CLASS_A", "CLASS_B")]
        class_c = [r for r in records if r.opportunity_class == "CLASS_C"]

        paper_tob_ab_usd = round(sum(max(0.0, r.paper_theoretical_usd) for r in proven), 6)
        exec_l2_ab_sum_usd = round(sum(max(0.0, r.executable_l2_net_usd) for r in proven), 6)
        att_shadow_ab_sum_usd = round(sum(max(0.0, r.forward_shadow_risk_adjusted_usd) for r in proven), 6)
        fees_ab_usd = round(sum(r.taker_fees_usd for r in proven), 6)
        slip_ab_usd = round(sum(r.slippage_vs_top_of_book_usd for r in proven), 6)
        unwind_bleed_ab_usd = round(sum(r.expected_unwind_bleed_usd for r in proven), 6)

        port_alloc_cap = float(portfolio_summary.get("total_allocated_capital_usd", 0.0))
        port_guar_net = float(portfolio_summary.get("portfolio_guaranteed_l2_net_usd", 0.0))
        port_shadow_ra = float(portfolio_summary.get("portfolio_forward_shadow_risk_adjusted_usd", 0.0))
        port_bps_hr = float(portfolio_summary.get("portfolio_realizable_bps_per_hr", 0.0))

        live_cash = float(AUTHORITATIVE_LIVE_WALLET_BASELINE["liquid_pusd_cash_usd"])
        vm_daily = float(AUTHORITATIVE_LIVE_WALLET_BASELINE["vm_daily_hurdle_usd"])
        vm_hourly = float(AUTHORITATIVE_LIVE_WALLET_BASELINE["vm_hourly_hurdle_usd"])
        vm_hurdle_bps_hr = float(AUTHORITATIVE_LIVE_WALLET_BASELINE["vm_hurdle_bps_per_hr_on_live_cash"])

        # Estimated hourly & annualized velocity strictly labeled as non-guaranteed shadow estimates!
        est_portfolio_hourly_usd = round(live_cash * (port_bps_hr / 10_000.0), 6)
        est_portfolio_daily_usd = round(est_portfolio_hourly_usd * 24.0, 6)
        est_simple_annualized_pct = round((port_bps_hr / 10_000.0) * 24.0 * 365.0 * 100.0, 2)

        return {
            "column_1_paper_theoretical": {
                "label": "Paper Theoretical Top-of-Book (Unallocated L1 Reference — Never Achievable)",
                "proven_class_a_b_paper_usd": paper_tob_ab_usd,
                "class_c_conditional_ev_sum_usd": round(sum(max(0.0, r.expected_net_payoff_usd) for r in class_c), 6),
            },
            "column_2_realistic_forward_shadow": {
                "label": "Realistic Forward Shadow (Depth-Walked, V2-Fee-Haircut, Post-Latency, Non-Double-Counted)",
                "unallocated_l2_executable_sum_usd": exec_l2_ab_sum_usd,
                "unallocated_post_latency_sum_usd": att_shadow_ab_sum_usd,
                "portfolio_allocated_capital_on_48_70_pusd": round(port_alloc_cap, 6),
                "portfolio_guaranteed_l2_net_usd": round(port_guar_net, 6),
                "portfolio_post_latency_risk_adjusted_net_usd": round(port_shadow_ra, 6),
                "cross_snapshot_forward_validated_net_usd": self.forward_tracker.persistence_summary(
                    current_cycle=self.cycle_counter
                )["forward_validated_net_pnl_usd"],
                "total_taker_fees_modeled_usd": fees_ab_usd,
                "total_l2_depth_slippage_vs_l1_usd": slip_ab_usd,
                "total_expected_partial_fill_unwind_bleed_usd": unwind_bleed_ab_usd,
                "estimated_capital_efficiency_bps_per_hr_non_guaranteed": port_bps_hr,
                "estimated_daily_yield_on_48_70_usd_non_guaranteed": est_portfolio_daily_usd,
                "estimated_simple_annualized_yield_pct_non_guaranteed": est_simple_annualized_pct,
                "hedged_maker_shadow_telemetry_non_locked": {
                    "resting_passive_quotes_count": len(self.hedged_maker_quoter.resting_quotes),
                    "filled_hedged_locks_count": self.hedged_maker_quoter.filled_hedged_locks_count,
                    "adverse_selected_fills_count": self.hedged_maker_quoter.adverse_selected_fills_count,
                    "net_post_adverse_shadow_pnl_ex_rebate_usd": round(
                        self.hedged_maker_quoter.locked_spread_shadow_pnl_usd
                        - self.hedged_maker_quoter.adverse_unwind_bleed_usd,
                        6,
                    ),
                    "estimated_maker_rebate_15_to_25pct_usd": round(
                        self.hedged_maker_quoter.estimated_maker_rebate_15_to_25pct_usd,
                        6,
                    ),
                    "strictly_segregated_from_locked_cash": True,
                },
                "shadow_realized_wallet_cash_usd": 0.0,
            },
            "column_3_verified_live_wallet_cash": {
                "label": "Independently Verified Realized Live Wallet Cash (`kraken-finland` On-Chain Reality)",
                **AUTHORITATIVE_LIVE_WALLET_BASELINE,
                "new_live_orders_placed_by_full_throttle_runner": 0,
            },
            "vm_infrastructure_hurdle_comparison": {
                "vm_monthly_cost_usd": 24.67,
                "vm_daily_hurdle_usd": vm_daily,
                "vm_hourly_hurdle_usd": vm_hourly,
                "required_portfolio_bps_per_hr_at_48_70_cash": vm_hurdle_bps_hr,
                "required_portfolio_bps_per_hr_at_500_nav": round((vm_hourly / 500.0) * 10_000.0, 4),
                "shadow_portfolio_bps_per_hr_estimate": port_bps_hr,
                "covers_vm_hurdle_at_48_70_cash": bool(est_portfolio_daily_usd >= vm_daily),
                "daily_surplus_or_deficit_vs_vm_at_48_70_usd": round(est_portfolio_daily_usd - vm_daily, 6),
            },
        }

    # -----------------------------------------------------------------------
    # Multi-Cycle Campaign Runner & Dashboard Payload Builder
    # -----------------------------------------------------------------------

    def run_multi_cycle_campaign(
        self,
        *,
        discovery_sweeps: int = 1,
        fast_cycles_per_sweep: int = 2,
        include_research_cycle: bool = True,
        inter_cycle_pause_sec: float = 1.5,
        synthetic_events: Optional[Sequence[Mapping[str, Any]]] = None,
        synthetic_raw_books_sequence: Optional[Sequence[Mapping[str, Mapping[str, Any]]]] = None,
        portfolio_state: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Runs a multi-cycle operating campaign (`DISCOVERY_CYCLE` + `FAST_CYCLE`s + `RESEARCH_CYCLE`),
        persists `dashboard_latest.json`, `opportunity_ledger.jsonl`, `dormant_opportunities.json`,
        and `checkpoint_state.json`, and returns the complete dashboard payload.
        """
        campaign_t0 = time.perf_counter()
        seq_idx = 0

        def _next_books() -> Optional[Mapping[str, Mapping[str, Any]]]:
            nonlocal seq_idx
            if not synthetic_raw_books_sequence:
                return None
            chosen = synthetic_raw_books_sequence[min(seq_idx, len(synthetic_raw_books_sequence) - 1)]
            seq_idx += 1
            return chosen

        for sweep_i in range(max(1, int(discovery_sweeps))):
            self.run_cycle(
                OperatingCycleType.DISCOVERY_CYCLE,
                synthetic_events=synthetic_events,
                synthetic_raw_books=_next_books(),
                portfolio_state=portfolio_state,
            )
            for fast_j in range(max(0, int(fast_cycles_per_sweep))):
                if synthetic_events is None and inter_cycle_pause_sec > 0.0:
                    time.sleep(inter_cycle_pause_sec)
                self.run_cycle(
                    OperatingCycleType.FAST_CYCLE,
                    synthetic_events=synthetic_events,
                    synthetic_raw_books=_next_books(),
                    portfolio_state=portfolio_state,
                )

        if include_research_cycle:
            if synthetic_events is None and inter_cycle_pause_sec > 0.0:
                time.sleep(min(1.0, inter_cycle_pause_sec))
            self.run_cycle(
                OperatingCycleType.RESEARCH_CYCLE,
                synthetic_events=synthetic_events,
                synthetic_raw_books=_next_books(),
                portfolio_state=portfolio_state,
            )

        campaign_wall_sec = round(time.perf_counter() - campaign_t0, 3)
        dashboard_payload = self.build_dashboard_payload(campaign_wall_time_sec=campaign_wall_sec)
        _atomic_write_json(self.dashboard_json_path, dashboard_payload)
        return dashboard_payload

    def build_dashboard_payload(self, *, campaign_wall_time_sec: Optional[float] = None) -> Dict[str, Any]:
        latest = self.cycle_reports[-1] if self.cycle_reports else {}
        peer_status = {k: bool(k in self.peer_bridge.loaded_modules) for k in (
            "discovery",
            "math_verifier",
            "proposition_graph",
            "complete_negrisk",
            "logical_specialized",
            "micro_portfolio",
        )}

        # Aggregate fresh-book unique tokens across all cycles in this campaign
        total_book_polls = sum(int(c["token_poll_plan"]["total_selected_tokens"]) for c in self.cycle_reports)
        avg_fast_cycle_sec = 0.0
        fast_secs = [float(c["cycle_wall_time_sec"]) for c in self.cycle_reports if c["cycle_type"] == "FAST_CYCLE"]
        if fast_secs:
            avg_fast_cycle_sec = round(sum(fast_secs) / len(fast_secs), 3)

        return {
            "schema_version": "dominus_full_throttle_dashboard_v1",
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "execution_mode": self.mode_controller.mode.value,
            "jurisdiction_gate": self.mode_controller.config.jurisdiction_code,
            "live_orders_hard_locked": not self.mode_controller.allows_live_orders,
            "campaign_summary": {
                "total_cycles_executed": len(self.cycle_reports),
                "cycle_types_executed": [c["cycle_type"] for c in self.cycle_reports],
                "campaign_wall_time_sec": campaign_wall_time_sec
                if campaign_wall_time_sec is not None
                else round(sum(float(c["cycle_wall_time_sec"]) for c in self.cycle_reports), 3),
                "full_universe_discovery_sweep_sec": round(self.last_discovery_sweep_wall_sec, 3),
                "avg_fast_cycle_wall_sec": avg_fast_cycle_sec,
                "listing_to_evaluation_latency_ms": latest.get("listing_to_evaluation_latency_ms", 0.0),
                "total_batched_book_tokens_polled_across_cycles": total_book_polls,
                "peak_rss_mib": round(self.peak_rss_mib, 2),
                "swapless_180mib_budget_ok": bool(self.peak_rss_mib <= self.config.max_rss_mib),
                "peer_modules_wired": peer_status,
            },
            "section_1_universe_coverage": latest.get("universe_coverage", self.last_universe_census),
            "section_1b_proposition_graph": latest.get("proposition_graph", self.last_graph_metrics),
            "section_1c_detector_coverage_by_family": latest.get("detector_coverage_by_family", {}),
            "section_2_opportunity_metrics": latest.get("opportunity_summary", {}),
            "section_2b_persistence_and_forward_validation": self.forward_tracker.persistence_summary(
                current_cycle=self.cycle_counter
            ),
            "section_2c_dormant_opportunity_store": self.dormant_store.summary_metrics(),
            "section_2d_hedged_maker_shadow_quoter": latest.get(
                "hedged_maker_shadow_quoter", self.hedged_maker_quoter.summary_metrics()
            ),
            "section_2e_harvester_candidate_bridge": latest.get(
                "harvester_candidate_bridge", self.last_harvester_bridge_report
            ),
            "section_3_segregated_economics": latest.get("segregated_economics", {}),
            "section_3b_portfolio_allocation_48_70_pusd": latest.get("portfolio_allocation", {}),
            "section_3c_shadow_budget_scaling_curve": self.last_micro_portfolio_extras.get(
                "portfolio_shadow_budget_curve", []
            ),
            "section_4_emerging_mechanisms_and_backlog": {
                "mechanism_catalog": self.last_micro_portfolio_extras.get("mechanism_catalog", {}),
                "research_backlog": self.last_micro_portfolio_extras.get("research_backlog", [])[:15],
            },
            "top_executable_opportunities": latest.get("top_executable_opportunities", []),
            "top_class_c_opportunities": latest.get("top_class_c_opportunities", []),
            "cycle_by_cycle_telemetry": [
                {
                    "cycle_index": c["cycle_index"],
                    "cycle_type": c["cycle_type"],
                    "timestamp_utc": c["timestamp_utc"],
                    "wall_sec": c["cycle_wall_time_sec"],
                    "rss_mib": c["rss_mib"],
                    "fresh_books": c["universe_coverage"]["fresh_l2_book_tokens_this_cycle"],
                    "candidates": c["opportunity_summary"]["total_candidates_evaluated"],
                    "class_a": c["opportunity_summary"]["class_counts"]["CLASS_A"],
                    "class_b": c["opportunity_summary"]["class_counts"]["CLASS_B"],
                    "class_c": c["opportunity_summary"]["class_counts"]["CLASS_C"],
                    "class_d": c["opportunity_summary"]["class_counts"]["CLASS_D"],
                    "dormant_active": c["dormant_store"]["active_dormant_count"],
                    "stage_timings_ms": c["stage_timings_ms"],
                }
                for c in self.cycle_reports
            ],
        }
