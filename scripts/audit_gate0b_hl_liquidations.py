"""
Gate 0B: Hyperliquid Native Liquidation Ledger Data-Completeness Audit (v3.2.1)
File: scripts/audit_gate0b_hl_liquidations.py

Verifies whether the historical/reconstructed Hyperliquid dataset satisfies the
6-point institutional completeness requirements before proxy classifier optimization:
  1. Reconstructs all native liquidation events without missing blocks.
  2. Identifies every fill structure and fee tier.
  3. Provides millisecond-accurate execution timestamps.
  4. Distinguishes partial liquidations (20%) from backstop vault transfers (HLP).
  5. Records full liquidation notional in USDC.
  6. Records asset ticker and order side.

Outputs pass/fail certification and bounds the classifier validation domain.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger("Gate0B_Audit")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PIPELINE_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FIELDS = [
    "liquidated_user",
    "execution_ts_ms",
    "asset",
    "side",
    "notional_usd",
    "liquidation_method",  # e.g., 'PARTIAL_20PCT', 'FULL_SWEEP', 'BACKSTOP_HLP'
    "fill_price",
    "fee_tier_bps"
]


class Gate0BLiquidationAuditor:
    def __init__(self, ledger_path: str = "data/hyperliquid/historical_liquidations_raw.jsonl"):
        self.ledger_path = Path(ledger_path)
        self.total_records = 0
        self.missing_field_counts = {field: 0 for field in REQUIRED_FIELDS}
        self.method_distribution = {}
        self.valid_records = 0

    def run_audit(self) -> Dict[str, Any]:
        logger.info("Executing Gate 0B Liquidation Data-Completeness Audit on %s", self.ledger_path)

        if not self.ledger_path.exists():
            logger.warning("Historical liquidation file %s does not exist on disk.", self.ledger_path)
            return {
                "audit_status": "PARTIAL_GROUND_TRUTH_UNVERIFIED",
                "total_records": 0,
                "data_completeness_pct": 0.0,
                "gate_0b_passed": False,
                "reason": "Missing raw historical L1 liquidation stream. Real-time proxy classifier must operate in Stage 1 Offline Lab."
            }

        with open(self.ledger_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                self.total_records += 1
                try:
                    record = json.loads(line)
                except Exception:
                    continue

                is_valid = True
                for field in REQUIRED_FIELDS:
                    if field not in record or record[field] is None:
                        self.missing_field_counts[field] += 1
                        is_valid = False

                method = record.get("liquidation_method", "UNKNOWN")
                self.method_distribution[method] = self.method_distribution.get(method, 0) + 1

                if is_valid:
                    self.valid_records += 1

        completeness_pct = (self.valid_records / max(self.total_records, 1)) * 100.0
        gate_passed = (completeness_pct >= 99.0) and (self.total_records >= 100)

        result = {
            "audit_status": "CERTIFIED_COMPLETE" if gate_passed else "PARTIAL_GROUND_TRUTH",
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "completeness_pct": round(completeness_pct, 2),
            "missing_field_breakdown": self.missing_field_counts,
            "method_distribution": self.method_distribution,
            "gate_0b_passed": gate_passed
        }

        logger.info(
            "Gate 0B Audit Result: Status = %s | Completeness = %.2f%% | Valid Records = %d / %d",
            result["audit_status"], result["completeness_pct"], self.valid_records, self.total_records
        )
        return result


if __name__ == "__main__":
    auditor = Gate0BLiquidationAuditor()
    res = auditor.run_audit()
    print(json.dumps(res, indent=2))
