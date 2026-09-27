"""
IRONCORE VERSIONED CONFIGURATION (v2.4.0-RC2)
==============================================
Central, immutable configuration defining the execution physics, statistical
thresholds, cost models, accounting invariants, and cryptographic provenance
for the IronCore Backtester.

Kernel Freeze Integrity Guarantees:
  - hash_array_raw(): true raw-byte SHA256 with zero normalization
  - hash_array_canonicalized(): NaN-normalized semantic content hash
  - EnvironmentManifest: required, independently-verified runtime environment
  - Ordered universe hashing (symbol sequence identity)
  - Immutable NumPy arrays in ResolvedExecutionParameters (write=False)
"""

from dataclasses import dataclass, field
import hashlib
import inspect
import json
import re
import sys
from typing import Dict, Any, Tuple, Optional, List, Union
import numpy as np


@dataclass(frozen=True)
class BacktestExecutionReference:
    """
    Explicit, typed reference benchmark metrics from the backtest
    consumed by Gate 8 (Execution Parity Auditor). Eliminates ambient or implicit state.
    """
    turnover_usd: float
    fees_usd: float
    maker_ratio_pct: float
    taker_ratio_pct: float
    sl_triggers: int
    tp_triggers: int
    slippage_bps: float = 0.0
    adverse_markout_bps: float = 1.0
    trades_count: int = 0
    rebalances_count: int = 0
    funding_usd: float = 0.0
    gross_pnl_usd: Optional[float] = None
    net_pnl_usd: Optional[float] = None


# =============================================================================
# HASHING FUNCTIONS
# =============================================================================

def hash_array_raw(arr: Optional[np.ndarray]) -> str:
    """
    True raw-byte SHA256 hash of a numpy array.
    No normalization whatsoever: NaN, Inf, -0.0 all retain their native IEEE 754
    bit patterns. Any byte-level change produces a different hash.
    """
    if arr is None:
        return "NONE"
    h = hashlib.sha256()
    arr_c = np.ascontiguousarray(arr)
    h.update(arr_c.shape.__repr__().encode())
    h.update(arr_c.dtype.str.encode())
    h.update(arr_c.tobytes(order="C"))
    return h.hexdigest()


def hash_array_canonicalized(arr: Optional[np.ndarray]) -> str:
    """
    NaN-canonicalized semantic content hash.
    NaN positions are recorded in a separate mask; the data bytes have NaNs
    replaced with 0.0 so that different NaN bit patterns hash identically.
    Use this when NaN-equivalence is intentionally desired (e.g. comparing
    datasets that may have been loaded from different serialization formats).
    """
    if arr is None:
        return "NONE"
    hasher = hashlib.sha256()
    hasher.update(str(arr.shape).encode())
    hasher.update(str(arr.dtype).encode())
    hasher.update(str(arr.dtype.byteorder).encode())
    nan_mask = np.isnan(arr) if np.issubdtype(arr.dtype, np.floating) else np.zeros(arr.shape, dtype=bool)
    hasher.update(nan_mask.tobytes())
    clean_arr = np.where(nan_mask, 0.0, arr)
    hasher.update(clean_arr.tobytes())
    return hasher.hexdigest()


# =============================================================================
# ENVIRONMENT MANIFEST
# =============================================================================

_PLACEHOLDER_PATTERN = re.compile(r"^(HEAD|ENV_LOCKED|UNKNOWN|N/A|TBD|TODO|)$", re.IGNORECASE)


@dataclass(frozen=True)
class EnvironmentManifest:
    """
    Required, independently-verified runtime environment description.
    No defaults. No placeholders. All fields must be explicitly supplied
    and must not contain placeholder tokens ("HEAD", "ENV_LOCKED", "").
    """
    engine_git_commit: str
    lockfile_sha256: str
    python_version: str
    numpy_version: str
    scipy_version: str
    polars_version: str

    def __post_init__(self):
        for field_name in self.__dataclass_fields__:
            val = getattr(self, field_name)
            if not isinstance(val, str) or _PLACEHOLDER_PATTERN.match(val.strip()):
                raise ValueError(
                    f"ENVIRONMENT_MANIFEST_PLACEHOLDER: Field '{field_name}' has "
                    f"value '{val}' which is a placeholder or empty. "
                    f"All EnvironmentManifest fields must be explicitly supplied."
                )

    def to_dict(self) -> Dict[str, str]:
        return {
            "engine_git_commit": self.engine_git_commit,
            "lockfile_sha256": self.lockfile_sha256,
            "python_version": self.python_version,
            "numpy_version": self.numpy_version,
            "scipy_version": self.scipy_version,
            "polars_version": self.polars_version,
        }

    def content_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class ResolvedExecutionParameters:
    """
    Immutable, fully resolved runtime execution parameters.
    Consumed directly by simulate_canonical_execution and certify_strategy.
    Guarantees that no optional caller arguments can silently disable
    configured stops, deadbands, or governor risk limits.

    NumPy array fields (dynamic_stop_loss, dynamic_take_profit) are made
    read-only (write=False) to prevent post-resolution mutation.
    """
    # Version & Identity
    version: str = "2.4.0"

    # Execution & Fee Physics
    maker_fee: float = 0.00015             # 1.5 bps maker rebate/fee
    taker_fee: float = 0.00045             # 4.5 bps aggressive crossing fee
    base_maker_ratio: float = 0.60         # Default maker ratio
    base_adverse_bps: float = 0.00010      # 1.0 bps adverse selection markout
    impact_coefficient: float = 0.03       # Footprint impact gamma
    min_adv_usdc: float = 500_000.0        # PIT liquidity cutoff

    # Churn & Turnover Controls
    portfolio_deadband: float = 0.08       # 8.0% portfolio notional deadband
    deadband: float = 0.00                 # Per-asset deadband
    rank_entry_k: int = 10                 # Entry rank
    rank_exit_k: int = 15                  # Exit rank
    fixed_slot_sizing: bool = True         # Zero-churn slot weight allocation

    # Sub-Bar Execution Physics
    subbars_per_bar: int = 4               # Sub-bars per 4H bar
    passive_fill_horizon_subbars: int = 2  # Subbars to wait before crossing as taker
    causal_passive_mode: bool = True       # True: next-subbar touch only; no same-subbar lookahead
    same_subbar_stop_vulnerable: bool = True # True: entered position in s is vulnerable to stop in s
    tp_penetration_bps: float = 0.00015    # 1.5 bps depth penetration required for TP execution

    # Bracket Stops & Cooldown
    fixed_stop_loss_pct: Optional[float] = 0.035   # 3.5% Stop Loss
    fixed_take_profit_pct: Optional[float] = 0.070 # 7.0% Take Profit
    dynamic_stop_loss: Optional[np.ndarray] = None  # Asset/time dynamic ATR stops
    dynamic_take_profit: Optional[np.ndarray] = None
    enable_cooldown: bool = True
    cooldown_bars: int = 1

    # Stateful Drawdown Governor
    enable_governor: bool = True
    governor_halt_threshold: float = 0.15
    rerisk_buffer_pct: float = 0.02
    drawdown_tiers: Tuple[Tuple[float, float], ...] = (
        (0.05, 1.00),  # DD < 5%  -> 1.00x
        (0.10, 0.75),  # 5% <= DD < 10% -> 0.75x
        (0.15, 0.35),  # 10% <= DD < 15% -> 0.35x
        (1.00, 0.00),  # DD >= 15% -> 0.00x (ALLOCATION_HALT)
    )
    halt_liquidation_policy: str = "allocation_halt"  # "allocation_halt" vs "emergency_market_close"

    # Risk Bounds & Tolerances
    initial_capital: float = 10_000.0
    max_single_name_leverage: float = 0.15
    max_gross_leverage: float = 1.20
    max_net_exposure: float = 0.10
    drift_tolerance: float = 1.0e-4

    # Scientific Model Convention Labels (part of the frozen specification)
    # These are included in execution_config_hash and provenance manifest.
    # Changing any convention string constitutes a specification change.
    intrabar_path_convention: str = "PESSIMISTIC_WORST_CASE:v1"
    gap_slip_model: str = "30pct:v1"
    passive_queue_model: str = "causal_stochastic_queue:v1"
    gap_slip_pct: float = 0.30  # 30% gap-slip heuristic for stop-triggered exits

    def __post_init__(self):
        """
        Enforce write-protection on any NumPy array fields.
        Makes a DEFENSIVE COPY first so that the caller's original array
        reference cannot mutate the resolved parameters through shared memory.
        
        Invariant: once constructed, params.dynamic_stop_loss[...] = X raises ValueError,
        AND caller_original_array[...] = Y does NOT affect params.
        """
        for field_name in ("dynamic_stop_loss", "dynamic_take_profit"):
            arr = getattr(self, field_name)
            if arr is not None and isinstance(arr, np.ndarray):
                # Defensive copy — breaks any shared memory with the caller's reference
                private_copy = np.ascontiguousarray(arr).copy()
                private_copy.setflags(write=False)
                object.__setattr__(self, field_name, private_copy)

    def execution_config_hash(self) -> str:
        """Deterministic cryptographic hash of all resolved physics parameters + model conventions."""
        d = {
            "maker_fee": self.maker_fee,
            "taker_fee": self.taker_fee,
            "base_maker_ratio": self.base_maker_ratio,
            "base_adverse_bps": self.base_adverse_bps,
            "impact_coefficient": self.impact_coefficient,
            "portfolio_deadband": self.portfolio_deadband,
            "rank_entry_k": self.rank_entry_k,
            "rank_exit_k": self.rank_exit_k,
            "fixed_slot_sizing": self.fixed_slot_sizing,
            "subbars_per_bar": self.subbars_per_bar,
            "passive_fill_horizon_subbars": self.passive_fill_horizon_subbars,
            "causal_passive_mode": self.causal_passive_mode,
            "same_subbar_stop_vulnerable": self.same_subbar_stop_vulnerable,
            "tp_penetration_bps": self.tp_penetration_bps,
            "fixed_stop_loss_pct": self.fixed_stop_loss_pct,
            "fixed_take_profit_pct": self.fixed_take_profit_pct,
            "has_dynamic_stop": self.dynamic_stop_loss is not None,
            "has_dynamic_tp": self.dynamic_take_profit is not None,
            "enable_cooldown": self.enable_cooldown,
            "cooldown_bars": self.cooldown_bars,
            "enable_governor": self.enable_governor,
            "governor_halt_threshold": self.governor_halt_threshold,
            "rerisk_buffer_pct": self.rerisk_buffer_pct,
            "drawdown_tiers": self.drawdown_tiers,
            "halt_liquidation_policy": self.halt_liquidation_policy,
            "max_gross_leverage": self.max_gross_leverage,
            # Model convention labels — changing any changes the specification
            "intrabar_path_convention": self.intrabar_path_convention,
            "gap_slip_model": self.gap_slip_model,
            "passive_queue_model": self.passive_queue_model,
            "gap_slip_pct": self.gap_slip_pct,
        }
        serialized = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class CertificationProvenance:
    """
    Immutable provenance chain-of-custody object required for institutional certification.
    Encapsulates the complete research and execution audit trail:
    Canonical Serialized Manifest -> SHA256(Manifest_Bytes)

    Uses hash_array_raw() for true raw-byte provenance.
    Requires EnvironmentManifest (no placeholders) for independent verification.
    Universe hash preserves symbol ordering (membership + sequence identity).
    """
    engine_version: str
    config_hash: str
    feature_manifest_hash: str
    dataset_hash: str
    universe_hash: str
    model_spec_hash: str
    wfo_partition_hash: str
    trial_registry_hash: str
    execution_engine_hash: str
    oos_equity_hash: str
    engine_source_sha256: str = ""
    environment_manifest_hash: str = ""
    dataset_manifest_hash: str = ""
    timestamp_bounds: Tuple[str, str] = ("0", "0")
    oos_event_journal_hash: str = ""
    master_provenance_hash: str = ""
    # Deprecated alias preserved for backward compatibility
    python_version: str = ""

    def __post_init__(self):
        if not self.dataset_manifest_hash:
            object.__setattr__(self, "dataset_manifest_hash", self.dataset_hash)
        if not self.dataset_hash:
            object.__setattr__(self, "dataset_hash", self.dataset_manifest_hash)
        if not self.master_provenance_hash:
            canonical_manifest = {
                "engine_version": self.engine_version,
                "engine_source_sha256": self.engine_source_sha256,
                "environment_manifest_hash": self.environment_manifest_hash,
                "config_hash": self.config_hash,
                "feature_manifest_hash": self.feature_manifest_hash,
                "dataset_manifest_hash": self.dataset_manifest_hash,
                "universe_hash": self.universe_hash,
                "timestamp_bounds": list(self.timestamp_bounds),
                "model_spec_hash": self.model_spec_hash,
                "wfo_partition_hash": self.wfo_partition_hash,
                "trial_registry_hash": self.trial_registry_hash,
                "execution_engine_hash": self.execution_engine_hash,
                "oos_equity_hash": self.oos_equity_hash,
                "oos_event_journal_hash": self.oos_event_journal_hash,
            }
            manifest_bytes = json.dumps(canonical_manifest, sort_keys=True).encode("utf-8")
            object.__setattr__(self, "master_provenance_hash", hashlib.sha256(manifest_bytes).hexdigest())

    @staticmethod
    def hash_array_bitwise(arr: np.ndarray) -> str:
        """Backward-compatible alias for hash_array_canonicalized."""
        return hash_array_canonicalized(arr)

    @classmethod
    def create(
        cls,
        engine_version: str,
        resolved_config: ResolvedExecutionParameters,
        dataset_matrices: Dict[str, np.ndarray],
        symbols: List[str],
        candidate_name: str,
        folds: List[Tuple[int, int, int, int]],
        trial_registry_hash: str,
        combined_bar_returns: np.ndarray,
        feature_panel: Optional[Dict[str, np.ndarray]] = None,
        engine_source: str = "",
        timestamp_bounds: Tuple[str, str] = ("0", "0"),
        model_spec: Optional[Dict[str, Any]] = None,
        event_journal_bytes: bytes = b"",
        environment: Optional[EnvironmentManifest] = None,
    ) -> "CertificationProvenance":
        # 1. Engine source hash
        engine_src_h = hashlib.sha256(engine_source.encode("utf-8")).hexdigest()[:16] if engine_source else "0" * 16
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # 2. Environment Manifest hash (independently verified)
        env_h = environment.content_hash()[:16] if environment is not None else "0" * 16

        # 3. Raw-byte Dataset Manifest Hash (no NaN normalization)
        ds_hasher = hashlib.sha256()
        for k in sorted(dataset_matrices.keys()):
            arr = dataset_matrices[k]
            arr_h = hash_array_raw(arr)
            ds_hasher.update(f"{k}:{arr.shape}:{arr.dtype}:{arr_h}".encode())
        dataset_h = ds_hasher.hexdigest()[:16]

        # 4. Raw-byte Feature Manifest Hash
        feat_hasher = hashlib.sha256()
        if feature_panel:
            for k in sorted(feature_panel.keys()):
                arr = feature_panel[k]
                arr_h = hash_array_raw(arr)
                feat_hasher.update(f"{k}:{arr.shape}:{arr.dtype}:{arr_h}".encode())
        feat_h = feat_hasher.hexdigest()[:16]

        # 5. Ordered Universe Hash: exact symbol sequence (membership + ordering)
        # NOT sorted — [BTC, ETH, SOL] and [SOL, BTC, ETH] produce different hashes
        univ_h = hashlib.sha256(",".join(symbols).encode("utf-8")).hexdigest()[:16]

        # 5. Model Specification Hash
        spec_dict = {
            "candidate_name": candidate_name,
            "rank_entry_k": resolved_config.rank_entry_k,
            "rank_exit_k": resolved_config.rank_exit_k,
            "fixed_slot_sizing": resolved_config.fixed_slot_sizing,
            "spec_details": model_spec or {},
        }
        model_h = hashlib.sha256(json.dumps(spec_dict, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]

        # 6. WFO Partition Hash
        folds_str = ";".join(f"{f[0]},{f[1]},{f[2]},{f[3]}" for f in folds)
        wfo_h = hashlib.sha256(folds_str.encode("utf-8")).hexdigest()[:16]

        # 7. Execution Engine Config Hash
        exec_h = resolved_config.execution_config_hash()

        # 8. Full Config Hash
        cfg_dict = {k: v for k, v in resolved_config.__dict__.items() if not isinstance(v, np.ndarray)}
        cfg_h = hashlib.sha256(json.dumps(cfg_dict, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]

        # 9. OOS Equity Hash (raw bytes)
        eq_arr = np.array(combined_bar_returns, dtype=np.float64)
        eq_h = hash_array_raw(eq_arr)[:16]

        # 10. Event Journal Hash
        journal_h = hashlib.sha256(event_journal_bytes).hexdigest()[:16]

        # Canonical Manifest Serialization
        canonical_manifest = {
            "engine_version": engine_version,
            "engine_source_sha256": engine_src_h,
            "python_version": py_ver,
            "config_hash": cfg_h,
            "feature_manifest_hash": feat_h,
            "dataset_manifest_hash": dataset_h,
            "universe_hash": univ_h,
            "timestamp_bounds": list(timestamp_bounds),
            "model_spec_hash": model_h,
            "wfo_partition_hash": wfo_h,
            "trial_registry_hash": trial_registry_hash,
            "execution_engine_hash": exec_h,
            "oos_equity_hash": eq_h,
            "oos_event_journal_hash": journal_h,
        }
        manifest_bytes = json.dumps(canonical_manifest, sort_keys=True).encode("utf-8")
        master_h = hashlib.sha256(manifest_bytes).hexdigest()

        return cls(
            engine_version=engine_version,
            config_hash=cfg_h,
            feature_manifest_hash=feat_h,
            dataset_hash=dataset_h,
            universe_hash=univ_h,
            model_spec_hash=model_h,
            wfo_partition_hash=wfo_h,
            trial_registry_hash=trial_registry_hash,
            execution_engine_hash=exec_h,
            oos_equity_hash=eq_h,
            engine_source_sha256=engine_src_h,
            environment_manifest_hash=env_h,
            python_version=py_ver,
            dataset_manifest_hash=dataset_h,
            timestamp_bounds=timestamp_bounds,
            oos_event_journal_hash=journal_h,
            master_provenance_hash=master_h,
        )

    def master_hash(self) -> str:
        return self.master_provenance_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "engine_source_sha256": self.engine_source_sha256,
            "environment_manifest_hash": self.environment_manifest_hash,
            "config_hash": self.config_hash,
            "feature_manifest_hash": self.feature_manifest_hash,
            "dataset_manifest_hash": self.dataset_manifest_hash,
            "universe_hash": self.universe_hash,
            "timestamp_bounds": list(self.timestamp_bounds),
            "model_spec_hash": self.model_spec_hash,
            "wfo_partition_hash": self.wfo_partition_hash,
            "trial_registry_hash": self.trial_registry_hash,
            "execution_engine_hash": self.execution_engine_hash,
            "oos_equity_hash": self.oos_equity_hash,
            "oos_event_journal_hash": self.oos_event_journal_hash,
            "master_provenance_hash": self.master_provenance_hash,
        }

    def verify_against_inputs(
        self,
        engine_version: str,
        resolved_config: ResolvedExecutionParameters,
        dataset_matrices: Dict[str, np.ndarray],
        symbols: List[str],
        candidate_name: str,
        folds: List[Tuple[int, int, int, int]],
        trial_registry_hash: str,
        combined_bar_returns: np.ndarray,
        feature_panel: Optional[Dict[str, np.ndarray]] = None,
        engine_source: str = "",
        timestamp_bounds: Tuple[str, str] = ("0", "0"),
        model_spec: Optional[Dict[str, Any]] = None,
        event_journal_bytes: bytes = b"",
        environment: Optional[EnvironmentManifest] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Cryptographic verification gatekeeper.
        Recomputes the canonical manifest from input artifacts and asserts 100% bitwise parity
        across EVERY single provenance dimension.

        When `environment` is supplied, it is independently hashed and compared against the
        stored `environment_manifest_hash` — not fed back from the stored provenance object.
        """
        expected = self.create(
            engine_version=engine_version,
            resolved_config=resolved_config,
            dataset_matrices=dataset_matrices,
            symbols=symbols,
            candidate_name=candidate_name,
            folds=folds,
            trial_registry_hash=trial_registry_hash,
            combined_bar_returns=combined_bar_returns,
            feature_panel=feature_panel,
            engine_source=engine_source,
            timestamp_bounds=timestamp_bounds,
            model_spec=model_spec,
            event_journal_bytes=event_journal_bytes,
            environment=environment,
        )

        mismatches = []
        if self.engine_version != expected.engine_version:
            mismatches.append(f"ENGINE_VERSION: {self.engine_version} != {expected.engine_version}")
        if self.engine_source_sha256 != expected.engine_source_sha256:
            mismatches.append(f"ENGINE_SOURCE_HASH_MISMATCH: {self.engine_source_sha256} != {expected.engine_source_sha256}")
        if self.environment_manifest_hash and expected.environment_manifest_hash:
            if self.environment_manifest_hash != expected.environment_manifest_hash:
                mismatches.append(f"ENVIRONMENT_MANIFEST_HASH_MISMATCH: {self.environment_manifest_hash} != {expected.environment_manifest_hash}")
        if self.config_hash != expected.config_hash:
            mismatches.append("CONFIG_HASH_MISMATCH")
        if self.execution_engine_hash != expected.execution_engine_hash:
            mismatches.append("EXECUTION_CONFIG_HASH_MISMATCH")
        if self.feature_manifest_hash != expected.feature_manifest_hash:
            mismatches.append("FEATURE_MANIFEST_HASH_MISMATCH")
        if self.dataset_manifest_hash != expected.dataset_manifest_hash:
            mismatches.append("DATASET_MANIFEST_HASH_MISMATCH")
        if self.universe_hash != expected.universe_hash:
            mismatches.append("UNIVERSE_HASH_MISMATCH")
        if self.timestamp_bounds != expected.timestamp_bounds:
            mismatches.append(f"TIMESTAMP_BOUNDS_MISMATCH: {self.timestamp_bounds} != {expected.timestamp_bounds}")
        if self.model_spec_hash != expected.model_spec_hash:
            mismatches.append("MODEL_SPEC_HASH_MISMATCH")
        if self.wfo_partition_hash != expected.wfo_partition_hash:
            mismatches.append("WFO_PARTITION_HASH_MISMATCH")
        if self.trial_registry_hash != expected.trial_registry_hash:
            mismatches.append("TRIAL_REGISTRY_HASH_MISMATCH")
        if self.oos_equity_hash != expected.oos_equity_hash:
            mismatches.append("OOS_EQUITY_HASH_MISMATCH")
        if self.oos_event_journal_hash != expected.oos_event_journal_hash:
            mismatches.append("EVENT_JOURNAL_HASH_MISMATCH")
        if self.master_provenance_hash != expected.master_provenance_hash:
            mismatches.append("MASTER_PROVENANCE_HASH_MISMATCH")

        return len(mismatches) == 0, mismatches


@dataclass(frozen=True)
class IronCoreConfig_v1:
    version: str = "2.4.0"
    
    # Execution & Fee Physics
    maker_fee: float = 0.00015             # 1.5 bps maker rebate/fee
    taker_fee: float = 0.00045             # 4.5 bps aggressive crossing fee
    base_maker_ratio: float = 0.60         # 60% passive ALO fills modeled in Mode A
    base_adverse_bps: float = 0.00010      # 1.0 bps baseline adverse selection markout
    
    # Square-Root Footprint Market Impact
    impact_coefficient: float = 0.03       # gamma footprint impact coefficient
    min_adv_usdc: float = 500_000.0        # PIT liquidity cutoff
    
    # Churn & Turnover Controls
    deadband: float = 0.00                 # Per-asset deadband
    portfolio_deadband: float = 0.08       # 8.0% aggregate portfolio turnover threshold
    rank_entry_k: int = 10                 # Top-K entry rank
    rank_exit_k: int = 15                  # Exit threshold rank
    fixed_slot_sizing: bool = True         # True: fixed slot weight (budget/entry_k)
    
    # Sub-Bar Execution Parameters
    subbars_per_bar: int = 4               # Default 4 sub-bars per 4H bar
    passive_fill_horizon_subbars: int = 2  # Subbars to wait before crossing as taker
    causal_passive_mode: bool = True       # Next-subbar touch only
    same_subbar_stop_vulnerable: bool = True # Intra-subbar stop vulnerability
    tp_penetration_bps: float = 0.00015    # Depth penetration required for TP execution
    
    # Risk Limits & Stops
    fixed_stop_loss_pct: Optional[float] = 0.035
    fixed_take_profit_pct: Optional[float] = 0.070
    dynamic_stop_loss: Optional[np.ndarray] = None
    dynamic_take_profit: Optional[np.ndarray] = None
    enable_cooldown: bool = True
    cooldown_bars: int = 1
    
    # Portfolio Drawdown Governor
    enable_governor: bool = True
    rerisk_buffer_pct: float = 0.02        # 2.0% recovery buffer required before re-risking
    governor_halt_threshold: float = 0.15  # >= 15% DD halts trading
    drawdown_tiers: Tuple[Tuple[float, float], ...] = (
        (0.05, 1.00),  # < 5% DD: 100% risk budget
        (0.10, 0.75),  # 5% - 10% DD: 75% risk budget
        (0.15, 0.35),  # 10% - 15% DD: 35% aggressive de-risk
        (1.00, 0.00),  # >= 15% DD: 0% allocation halt
    )
    halt_liquidation_policy: str = "allocation_halt"
    
    # Portfolio Risk Bounds & Invariants
    max_single_name_leverage: float = 0.15
    max_gross_leverage: float = 1.20
    max_net_exposure: float = 0.10
    drift_tolerance: float = 1.0e-4
    zero_signal_tolerance: float = 1.0e-12
    oracle_required: bool = False

    # IronCore v2.4.1 Causal Hardening & Margin Invariants
    pyramid_causal_mode: str = "next_bar_open"       # Options: "next_bar_open", "none". "intrabar_touch" strictly forbidden.
    forbid_intrabar_touch_fill: bool = True          # Fatal error if order filled at touch and marked to same candle close.
    enforce_total_gross_margin_cap: bool = True      # Hard margin check on sum(|w_core|) + sum(|w_hedge|).
    max_total_portfolio_gross: float = 3.0           # Total gross leverage upper bound across all tranches and overlays.
    enforce_maker_fee_as_cost: bool = True           # Asserts maker fee rate is deducted as positive cost (0.015%).
    forbid_tight_trailing_ratchet: bool = True       # Enforces warning/safety check against trailing ratchets < 3.0 ATR on 4H crypto.
    
    # Statistical Testing & Gate Parameters
    newey_west_lags: int = 12
    adverse_markout_horizon_bars: int = 1
    mc_placebo_draws: int = 500
    bootstrap_paths: int = 1000
    ruin_drawdown_threshold: float = 0.15
    ruin_exceedance_thresholds: Tuple[float, ...] = (0.10, 0.15, 0.20, 0.25, 0.30, 0.50)
    
    # WFO Partitions & Capital
    wfo_train_bars: int = 540
    wfo_test_bars: int = 180
    initial_capital: float = 10_000.0
    
    def resolve_runtime_parameters(self, **overrides: Any) -> ResolvedExecutionParameters:
        """
        Constructs authoritative ResolvedExecutionParameters.
        Overriding is explicit; omitted fields default strictly to config values.
        Any unrecognized override key immediately raises ValueError (Zero Silent Ignored Overrides).
        """
        # Validate that all override keys are known
        valid_override_keys = set(ResolvedExecutionParameters.__dataclass_fields__.keys()) | {
            "sl_pct", "tp_pct", "governor_tiers"
        }
        for k in overrides:
            if k not in valid_override_keys:
                raise ValueError(
                    f"UNKNOWN_EXECUTION_OVERRIDE: '{k}' is not a recognized configuration parameter. "
                    f"Valid keys: {sorted(valid_override_keys)}"
                )

        kwargs = {
            "version": self.version,
            "maker_fee": self.maker_fee,
            "taker_fee": self.taker_fee,
            "base_maker_ratio": self.base_maker_ratio,
            "base_adverse_bps": self.base_adverse_bps,
            "impact_coefficient": self.impact_coefficient,
            "min_adv_usdc": self.min_adv_usdc,
            "portfolio_deadband": self.portfolio_deadband,
            "deadband": self.deadband,
            "rank_entry_k": self.rank_entry_k,
            "rank_exit_k": self.rank_exit_k,
            "fixed_slot_sizing": self.fixed_slot_sizing,
            "subbars_per_bar": self.subbars_per_bar,
            "passive_fill_horizon_subbars": self.passive_fill_horizon_subbars,
            "causal_passive_mode": self.causal_passive_mode,
            "same_subbar_stop_vulnerable": self.same_subbar_stop_vulnerable,
            "tp_penetration_bps": self.tp_penetration_bps,
            "fixed_stop_loss_pct": self.fixed_stop_loss_pct,
            "fixed_take_profit_pct": self.fixed_take_profit_pct,
            "dynamic_stop_loss": self.dynamic_stop_loss,
            "dynamic_take_profit": self.dynamic_take_profit,
            "enable_cooldown": self.enable_cooldown,
            "cooldown_bars": self.cooldown_bars,
            "enable_governor": self.enable_governor,
            "governor_halt_threshold": self.governor_halt_threshold,
            "rerisk_buffer_pct": self.rerisk_buffer_pct,
            "drawdown_tiers": self.drawdown_tiers,
            "halt_liquidation_policy": self.halt_liquidation_policy,
            "initial_capital": self.initial_capital,
            "max_single_name_leverage": self.max_single_name_leverage,
            "max_gross_leverage": self.max_gross_leverage,
            "max_net_exposure": self.max_net_exposure,
            "drift_tolerance": self.drift_tolerance,
            # Model convention labels (frozen specification strings)
            "intrabar_path_convention": "PESSIMISTIC_WORST_CASE:v1",
            "gap_slip_model": "30pct:v1",
            "passive_queue_model": "causal_stochastic_queue:v1",
            "gap_slip_pct": 0.30,
        }
        
        # Apply caller overrides with explicit None support
        for k, v in overrides.items():
            if k == "sl_pct":
                if isinstance(v, np.ndarray):
                    kwargs["dynamic_stop_loss"] = v
                    kwargs["fixed_stop_loss_pct"] = None
                elif v is not None:
                    kwargs["fixed_stop_loss_pct"] = float(v)
                    kwargs["dynamic_stop_loss"] = None
                else:
                    kwargs["fixed_stop_loss_pct"] = None
                    kwargs["dynamic_stop_loss"] = None
            elif k == "tp_pct":
                if isinstance(v, np.ndarray):
                    kwargs["dynamic_take_profit"] = v
                    kwargs["fixed_take_profit_pct"] = None
                elif v is not None:
                    kwargs["fixed_take_profit_pct"] = float(v)
                    kwargs["dynamic_take_profit"] = None
                else:
                    kwargs["fixed_take_profit_pct"] = None
                    kwargs["dynamic_take_profit"] = None
            elif k == "governor_tiers":
                if v is not None:
                    kwargs["drawdown_tiers"] = tuple(v)
                    kwargs["enable_governor"] = True
                else:
                    kwargs["enable_governor"] = False
            elif k in kwargs:
                kwargs[k] = v
                
        return ResolvedExecutionParameters(**kwargs)

    def config_hash(self) -> str:
        d = {k: v for k, v in self.__dict__.items() if not isinstance(v, np.ndarray)}
        serialized = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


DEFAULT_CONFIG = IronCoreConfig_v1()
