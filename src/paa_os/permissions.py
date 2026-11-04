"""
Operational Permission Model, Credential Sanitization & Compliance Gates (`src/paa_os/permissions.py`).

Implements PAA Section 4.C (Permission Design) & Acceptance Test #10 (Permission Test):
  1. `AUTOMATICALLY_PERMITTED`: Read-only inspection, permitted research, simulations, testing,
     documentation, isolated development, diagnostics, monitoring, routine safe recovery.
  2. `CONDITIONALLY_AUTOMATIC`: Versioned deployments and parameter adjustments strictly within
     existing authorizations and validated risk envelopes.
  3. `EXPLICIT_AUTHORIZATION_REQUIRED`: New live trading activation (including geographic/operator
     eligibility compliance), increased financial exposure, wallet transfers, credential/permission
     expansion, disabling risk controls.
"""

from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUTONOMY_CONFIG_PATH = PIPELINE_ROOT / "config" / "paa_autonomy_config.json"
DEFAULT_APPROVALS_DIR = PIPELINE_ROOT / "data" / "polymarket" / "paa" / "approvals"


class PermissionClass(str, Enum):
    AUTOMATICALLY_PERMITTED = "AUTOMATICALLY_PERMITTED"
    CONDITIONALLY_AUTOMATIC = "CONDITIONALLY_AUTOMATIC"
    EXPLICIT_AUTHORIZATION_REQUIRED = "EXPLICIT_AUTHORIZATION_REQUIRED"


class PermissionDeniedError(RuntimeError):
    """Raised when an autonomous worker attempts an action outside its operational authorization."""

    def __init__(self, reason: str, violations: Optional[List[str]] = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.violations = list(violations or [reason])


# Secrets that MUST NEVER be inherited by research, development, or QA sub-workers
SENSITIVE_SIGNING_ENV_KEYS = (
    "POLYGON_PRIVATE_KEY",
    "HYPERLIQUID_PRIVATE_KEY",
    "POLY_BUILDER_SECRET",
    "POLY_BUILDER_PASSPHRASE",
    "POLY_BUILDER_API_KEY",
    "EXECUTION_LIVE_CONFIRMED",
    "PRIVATE_KEY",
    "MNEMONIC",
)


def load_autonomy_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(config_path) if config_path is not None else DEFAULT_AUTONOMY_CONFIG_PATH
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def build_isolated_worker_env(
    role: str = "ENGINEERING_ISOLATED",
    base_env: Optional[Dict[str, str]] = None,
    autonomy_cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Constructs a sanitized subprocess environment for Research, Builder, and QA workers.
    Guarantees zero access to production wallet signing keys (`POLYGON_PRIVATE_KEY`, etc.).
    """
    cfg = autonomy_cfg or load_autonomy_config()
    rt = cfg.get("runtime") or {}
    raw = dict(base_env if base_env is not None else os.environ)
    clean: Dict[str, str] = {}
    for k, v in raw.items():
        ku = k.upper()
        if ku in SENSITIVE_SIGNING_ENV_KEYS or "PRIVATE_KEY" in ku or "SECRET" in ku or "PASSPHRASE" in ku:
            continue
        clean[k] = v

    clean["PAA_WORKER_ROLE"] = role
    clean["PAA_SIGNING_DISABLED"] = "1"
    clean["PYTHONUNBUFFERED"] = "1"
    clean["AGY_ADC_AUTH"] = "true"
    if os.name != "nt":
        adc_path = str(rt.get("adc_credentials_linux") or "/home/skybullet1987/.config/gcloud/application_default_credentials.json")
        if Path(adc_path).exists():
            clean["GOOGLE_APPLICATION_CREDENTIALS"] = adc_path
        clean["GOOGLE_CLOUD_PROJECT"] = str(rt.get("gcp_project") or "parnasa-498503")
        local_bin = str(Path.home() / ".local" / "bin")
        cur_path = clean.get("PATH", "/usr/bin:/bin")
        if local_bin not in cur_path.split(":"):
            clean["PATH"] = f"{local_bin}:{cur_path}"
    return clean


def has_explicit_operator_approval(
    approval_scope: str,
    task_or_release_id: Optional[str] = None,
    approvals_dir: Optional[Path] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Checks for an explicit operator-created JSON approval record in `data/polymarket/paa/approvals/`.
    Autonomous agents are strictly forbidden from writing to `approvals/`.
    """
    adir = Path(approvals_dir) if approvals_dir is not None else DEFAULT_APPROVALS_DIR
    if not adir.exists():
        return False, None
    for f in sorted(adir.glob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(rec, dict) or rec.get("approved") is not True:
                continue
            if str(rec.get("approved_by") or "").strip().lower() in ("", "paa", "agent", "director", "auto"):
                continue
            scopes = rec.get("scopes") or []
            target = rec.get("target_id")
            if approval_scope in scopes or "*" in scopes:
                if task_or_release_id is None or target in (None, "*", task_or_release_id):
                    return True, rec
        except Exception:
            continue
    return False, None


class PermissionGate:
    """Enforces PAA 3-class permission boundaries across tasks, config changes, and Git release diffs."""

    def __init__(
        self,
        autonomy_cfg: Optional[Dict[str, Any]] = None,
        approvals_dir: Optional[Path] = None,
    ) -> None:
        self.cfg = autonomy_cfg or load_autonomy_config()
        self.approvals_dir = Path(approvals_dir) if approvals_dir is not None else DEFAULT_APPROVALS_DIR
        perm = self.cfg.get("permissions") or {}
        self.protected_files = {
            str(x).replace("\\", "/").removeprefix("./").lstrip("/")
            for x in (
                perm.get("protected_files")
                or [
                    ".env",
                    "src/paa_os/permissions.py",
                    "src/paa_os/zero_trust.py",
                    "src/polymarket_research/execute_approvals.py",
                    "src/polymarket_research/setup_polymarket_account.py",
                    "config/paa_master_mandate.md",
                    "config/paa_autonomy_config.json",
                    "config/policies/PAA_MISSION.md",
                    "config/policies/PAA_AUTONOMY_POLICY.md",
                    "config/policies/PAA_RISK_POLICY.md",
                    "config/policies/PAA_DEPLOYMENT_POLICY.md",
                    "config/policies/PAA_VERIFICATION_POLICY.md",
                ]
            )
        }
        self.forbidden_patterns = list(
            perm.get("forbidden_diff_patterns")
            or [
                "POLYGON_PRIVATE_KEY",
                "HYPERLIQUID_PRIVATE_KEY",
                "POLY_BUILDER_SECRET",
                "safeTransferFrom(",
                "eth_sendRawTransaction",
            ]
        )
        self.risk_floors = dict(perm.get("immutable_risk_floors") or {})

    def check_task_authorization(self, task: Dict[str, Any]) -> Tuple[bool, str]:
        """Verifies whether a task is authorized to execute unattended."""
        p_cls = str(task.get("required_permission_class") or PermissionClass.AUTOMATICALLY_PERMITTED.value)
        scopes = list(task.get("required_scopes") or [])
        tid = str(task.get("task_id") or "")

        # Hard-check action scopes even if caller mislabeled permission_class
        explicit_scopes = {
            "NEW_LIVE_TRADING_ACTIVATION",
            "INCREASE_CAPITAL_EXPOSURE",
            "WALLET_TRANSFER_OR_WITHDRAWAL",
            "CREDENTIAL_OR_PERMISSION_EXPANSION",
            "DISABLE_RISK_CONTROLS",
            "OVERRIDE_GEOGRAPHIC_COMPLIANCE",
        }
        needed_explicit = [s for s in scopes if s in explicit_scopes]
        if p_cls == PermissionClass.EXPLICIT_AUTHORIZATION_REQUIRED.value or needed_explicit:
            scope_key = needed_explicit[0] if needed_explicit else "EXPLICIT_AUTHORIZATION"
            ok, _ = has_explicit_operator_approval(scope_key, tid, self.approvals_dir)
            if not ok:
                return (
                    False,
                    f"EXPLICIT_AUTHORIZATION_REQUIRED: scope={scope_key} lacks verified human approval in {self.approvals_dir}",
                )
        return True, "AUTHORIZED"

    def inspect_config_envelope(
        self,
        baseline_cfg: Dict[str, Any],
        candidate_cfg: Dict[str, Any],
        release_id: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Ensures autonomous config changes NEVER increase financial exposure, weaken risk safeguards,
        or activate unapproved live trading strategies without explicit operator approval.
        """
        violations: List[str] = []

        b_rc = baseline_cfg.get("risk_controller") or {}
        c_rc = candidate_cfg.get("risk_controller") or {}
        min_ruin = float(self.risk_floors.get("min_hard_ruin_floor_usd", b_rc.get("hard_ruin_floor_usd", 42.0)))
        if float(c_rc.get("hard_ruin_floor_usd", 0.0)) < max(min_ruin, float(b_rc.get("hard_ruin_floor_usd", 42.0))) - 1e-6:
            violations.append(
                f"RISK_FLOOR_WEAKENED: hard_ruin_floor_usd {c_rc.get('hard_ruin_floor_usd')} < baseline {b_rc.get('hard_ruin_floor_usd')}"
            )
        max_loss = float(self.risk_floors.get("max_daily_directional_loss_usd", b_rc.get("max_daily_directional_loss_usd", 16.57)))
        if float(c_rc.get("max_daily_directional_loss_usd", 999.0)) > min(max_loss, float(b_rc.get("max_daily_directional_loss_usd", 16.57))) + 1e-6:
            violations.append(
                f"EXPOSURE_INCREASED: max_daily_directional_loss_usd {c_rc.get('max_daily_directional_loss_usd')} > {b_rc.get('max_daily_directional_loss_usd')}"
            )
        if int(c_rc.get("max_consecutive_directional_losses", 99)) > int(b_rc.get("max_consecutive_directional_losses", 4)):
            violations.append("RISK_CONTROL_WEAKENED: max_consecutive_directional_losses increased")

        b_sz = baseline_cfg.get("sizing_tiers") or {}
        c_sz = candidate_cfg.get("sizing_tiers") or {}
        for cap_key in (
            "notional_cap_seed",
            "notional_cap_recovery",
            "notional_cap_growth",
            "notional_cap_scale",
            "max_stop_equity_risk_seed",
            "max_stop_equity_risk_recovery",
            "portfolio_exposure_pct_seed",
            "daily_loss_pct_seed",
            "kelly_fraction_seed",
        ):
            if cap_key in b_sz and cap_key in c_sz:
                if float(c_sz[cap_key]) > float(b_sz[cap_key]) + 1e-6:
                    violations.append(f"EXPOSURE_INCREASED: sizing_tiers.{cap_key} ({c_sz[cap_key]} > {b_sz[cap_key]})")
        for slot_key in ("dir_slots_seed", "dir_slots_recovery", "dir_slots_growth", "dir_slots_scale"):
            if slot_key in b_sz and slot_key in c_sz and int(c_sz[slot_key]) > int(b_sz[slot_key]):
                violations.append(f"EXPOSURE_INCREASED: sizing_tiers.{slot_key} ({c_sz[slot_key]} > {b_sz[slot_key]})")

        b_dir = baseline_cfg.get("directional") or {}
        c_dir = candidate_cfg.get("directional") or {}
        if bool(b_dir.get("riskless_only_mode")) and not bool(c_dir.get("riskless_only_mode")):
            violations.append("NEW_LIVE_TRADING_ACTIVATION: riskless_only_mode cannot be disabled without explicit approval")
        if bool(c_dir.get("enable_5m_directional")) and not bool(b_dir.get("enable_5m_directional")):
            violations.append("NEW_LIVE_TRADING_ACTIVATION: enable_5m_directional cannot be enabled without explicit approval")
        if bool(c_dir.get("enable_1h_shielded_maker")) and not bool(b_dir.get("enable_1h_shielded_maker")):
            violations.append("NEW_LIVE_TRADING_ACTIVATION: enable_1h_shielded_maker cannot be enabled without explicit approval")
        b_assets = set(b_dir.get("allowed_assets_1h") or []) | set(b_dir.get("allowed_assets_15m_maker") or [])
        c_assets = set(c_dir.get("allowed_assets_1h") or []) | set(c_dir.get("allowed_assets_15m_maker") or [])
        new_assets = sorted(c_assets - b_assets)
        if new_assets:
            violations.append(f"NEW_LIVE_ASSET_ACTIVATION: {new_assets} requires explicit operator approval")
        for px_key in ("max_taker_price_1h", "max_maker_price_1h", "max_taker_price_15m", "max_maker_price_15m"):
            if px_key in b_dir and px_key in c_dir and float(c_dir[px_key]) > float(b_dir[px_key]) + 1e-6:
                violations.append(f"PRICE_CEILING_RAISED: directional.{px_key} ({c_dir[px_key]} > {b_dir[px_key]})")

        b_bx = baseline_cfg.get("riskless_boxes") or {}
        c_bx = candidate_cfg.get("riskless_boxes") or {}
        if bool(c_bx.get("enable_two_leg_maker_anchor_boxes")) and not bool(b_bx.get("enable_two_leg_maker_anchor_boxes")):
            violations.append("UNGRADUATED_LIVE_ACTIVATION: enable_two_leg_maker_anchor_boxes is forbidden unattended")
        b_paused_rb = {str(s).strip().upper() for s in (b_bx.get("paused_riskless_sleeves") or []) if str(s).strip()}
        c_paused_rb = {str(s).strip().upper() for s in (c_bx.get("paused_riskless_sleeves") or []) if str(s).strip()}
        unpaused_rb = sorted(b_paused_rb - c_paused_rb)
        if unpaused_rb:
            violations.append(f"NEW_LIVE_TRADING_ACTIVATION: unpausing {unpaused_rb} requires explicit operator approval")

        if violations:
            ok_exp, _ = has_explicit_operator_approval("INCREASE_CAPITAL_EXPOSURE", release_id, self.approvals_dir)
            ok_live, _ = has_explicit_operator_approval("NEW_LIVE_TRADING_ACTIVATION", release_id, self.approvals_dir)
            if ok_exp and ok_live:
                return True, []
            return False, violations
        return True, []

    def inspect_candidate_diff(
        self,
        changed_files: Iterable[str],
        diff_text: str,
        baseline_cfg: Optional[Dict[str, Any]] = None,
        candidate_cfg: Optional[Dict[str, Any]] = None,
        release_id: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Audits a Git candidate release diff before QA/Deployment.
        Blocks protected files, secret access, approval-directory tampering, wallet transfer injection,
        and unauthorized risk/exposure/live-trading expansion.
        """
        violations: List[str] = []
        norm_files = [str(f).replace("\\", "/").removeprefix("./").lstrip("/") for f in changed_files]

        for nf in norm_files:
            if nf in self.protected_files or nf.startswith("config/policies/") or nf.endswith((".env", ".key", ".pem")):
                violations.append(f"PROTECTED_FILE_MODIFIED:{nf}")
            if "data/polymarket/paa/approvals" in nf:
                violations.append(f"SELF_APPROVAL_TAMPERING_FORBIDDEN:{nf}")

        added_lines = [
            ln[1:]
            for ln in (diff_text or "").splitlines()
            if ln.startswith("+") and not ln.startswith("+++")
        ]
        added_blob = "\n".join(added_lines)
        for pat in self.forbidden_patterns:
            if pat in added_blob:
                violations.append(f"FORBIDDEN_CREDENTIAL_OR_TRANSFER_PATTERN:{pat}")

        if baseline_cfg is not None and candidate_cfg is not None:
            ok_cfg, cfg_v = self.inspect_config_envelope(baseline_cfg, candidate_cfg, release_id=release_id)
            if not ok_cfg:
                violations.extend(cfg_v)

        if violations:
            ok_override, _ = has_explicit_operator_approval("CREDENTIAL_OR_PERMISSION_EXPANSION", release_id, self.approvals_dir)
            if not ok_override:
                return False, violations
        return True, []
