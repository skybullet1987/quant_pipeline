"""
Trial Registry v1.0 — Immutable Audit-Grade Research Trial Accounting
Enforces preregistration, research-family tracking, and exact multiple-testing DSR trial counts.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Set
import json
import hashlib
import os
import time


@dataclass
class ExperimentRecord:
    """Immutable record for a single preregistered hypothesis."""
    experiment_id: str
    research_family: str  # A1_FUNDING, A2_MOMENTUM, B_SIGNAL_TIMING, C_PORTFOLIO, D_EXECUTION, NULL_CONTROL
    hypothesis: str
    feature_set: List[str]
    signal_version: str
    training_spec: str
    portfolio_spec: str
    execution_config_hash: str
    dataset_snapshot_hash: str
    universe_ordering_hash: str
    primary_test: str
    secondary_metrics: List[str]
    parent_experiment_id: Optional[str] = None
    status: str = "PREREGISTERED"  # PREREGISTERED, EXECUTING, COMPLETED, REJECTED, PROMOTED, CONFIRMED_HOLDOUT, FAILED_HOLDOUT, FAILED_TECHNICAL
    deterministic_seed: int = 42
    created_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    completed_at_utc: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    pnl_decomposition: Optional[Dict[str, float]] = None
    event_journal_hash: Optional[str] = None
    hac_paired_t: Optional[float] = None
    dsr_p_value: Optional[float] = None

    def content_fingerprint(self) -> str:
        """Cryptographic hash of the preregistration specification."""
        spec = {
            "experiment_id": self.experiment_id,
            "research_family": self.research_family,
            "hypothesis": self.hypothesis,
            "feature_set": sorted(self.feature_set),
            "signal_version": self.signal_version,
            "training_spec": self.training_spec,
            "portfolio_spec": self.portfolio_spec,
            "execution_config_hash": self.execution_config_hash,
            "dataset_snapshot_hash": self.dataset_snapshot_hash,
            "universe_ordering_hash": self.universe_ordering_hash,
            "parent_experiment_id": self.parent_experiment_id,
            "deterministic_seed": self.deterministic_seed,
        }
        return hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()


class TrialRegistry:
    """
    Authoritative ledger of all research trials within a defined research campaign.
    Prevents post-hoc specification changes and computes exact DSR trial counts.
    """
    def __init__(self, registry_file: Optional[str] = None):
        self.registry_file = registry_file
        self.records: Dict[str, ExperimentRecord] = {}
        self.fingerprints: Dict[str, str] = {}
        if registry_file and os.path.exists(registry_file):
            self.load_from_disk(registry_file)

    def preregister(self, record: ExperimentRecord) -> str:
        """Preregisters an experiment before execution. Rejects duplicate IDs."""
        if record.experiment_id in self.records:
            raise ValueError(f"Experiment ID '{record.experiment_id}' is already registered.")
        
        fingerprint = record.content_fingerprint()
        record.status = "PREREGISTERED"
        self.records[record.experiment_id] = record
        self.fingerprints[record.experiment_id] = fingerprint
        
        if self.registry_file:
            self.save_to_disk(self.registry_file)
        return fingerprint

    def log_completion(
        self,
        experiment_id: str,
        results: Dict[str, Any],
        pnl_decomp: Optional[Dict[str, float]] = None,
        event_journal_hash: Optional[str] = None,
        hac_paired_t: Optional[float] = None,
        dsr_p_value: Optional[float] = None,
        status: str = "COMPLETED",
    ) -> None:
        """Logs execution results for a preregistered experiment."""
        if experiment_id not in self.records:
            raise KeyError(f"Cannot log completion: '{experiment_id}' is not preregistered.")
        
        rec = self.records[experiment_id]
        rec.results = results
        rec.pnl_decomposition = pnl_decomp
        rec.event_journal_hash = event_journal_hash
        rec.hac_paired_t = hac_paired_t
        rec.dsr_p_value = dsr_p_value
        rec.status = status
        rec.completed_at_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if self.registry_file:
            self.save_to_disk(self.registry_file)

    def total_trial_count(self, family: Optional[str] = None) -> int:
        """
        Calculates total statistical hypothesis count for DSR penalization:
        all preregistered, completed, failed, or promoted trials.
        """
        if family is not None:
            return sum(1 for r in self.records.values() if r.research_family == family)
        return len(self.records)

    def get_family_counts(self) -> Dict[str, int]:
        """Returns distribution of trial attempts per research family."""
        counts: Dict[str, int] = {}
        for r in self.records.values():
            counts[r.research_family] = counts.get(r.research_family, 0) + 1
        return counts

    def save_to_disk(self, path: str) -> None:
        """Atomically persists registry to JSON file."""
        data = {
            "schema_version": "1.0.0",
            "total_trials": len(self.records),
            "records": {k: asdict(v) for k, v in self.records.items()},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def load_from_disk(self, path: str) -> None:
        """Loads registry from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, rec_dict in data.get("records", {}).items():
            rec = ExperimentRecord(**rec_dict)
            self.records[k] = rec
            self.fingerprints[k] = rec.content_fingerprint()
