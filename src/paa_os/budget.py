"""
Budget, Resource Allocation & Economic Justification Controller (`src/paa_os/budget.py`).

Implements PAA Section 4.A.9 (Budget and Resource Management):
  - Tracks exact AI CLI invocations, input/output tokens, duration, and USD cost in `budget_ledger`.
  - Tracks prorated VM compute & infrastructure costs so PAA measures true net operational profit.
  - Enforces hard hourly and daily AI call & spend limits.
  - Enforces per-endpoint polling rate limits, bounded retries, exponential backoff,
    maximum simultaneous engineering jobs, and financial-value-based task gating.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.paa_os.permissions import load_autonomy_config
from src.paa_os.task_db import PAATaskDB, utc_now


class BudgetManager:
    def __init__(self, db: PAATaskDB, autonomy_cfg: Optional[Dict[str, Any]] = None) -> None:
        self.db = db
        self.cfg = autonomy_cfg or load_autonomy_config()
        self.b_cfg = self.cfg.get("budget") or {}
        self._last_poll_ts: Dict[str, float] = {}

    def estimate_ai_call_cost_usd(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        m = (model_name or "").lower()
        if "argon" in m or "opus" in m or "pro" in m:
            in_rate = float(self.b_cfg.get("est_cost_per_1k_input_tokens_argon_usd", 0.00125))
            out_rate = float(self.b_cfg.get("est_cost_per_1k_output_tokens_argon_usd", 0.00500))
        else:
            in_rate = float(self.b_cfg.get("est_cost_per_1k_input_tokens_flash_usd", 0.00015))
            out_rate = float(self.b_cfg.get("est_cost_per_1k_output_tokens_flash_usd", 0.00060))
        return round((max(0, int(input_tokens)) / 1000.0) * in_rate + (max(0, int(output_tokens)) / 1000.0) * out_rate, 6)

    def record_ai_usage(
        self,
        *,
        model_name: str,
        task_id: str,
        input_tokens: int,
        output_tokens: int,
        duration_sec: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> float:
        now = utc_now()
        cost = self.estimate_ai_call_cost_usd(model_name, input_tokens, output_tokens)
        with self.db._connect(immediate=True) as conn:
            conn.execute(
                """
                INSERT INTO budget_ledger(
                    recorded_at_utc, date_utc, hour_utc, cost_type, model_name, task_id,
                    input_tokens, output_tokens, duration_sec, estimated_cost_usd, details_json
                ) VALUES (?, ?, ?, 'AI_AGENT_CALL', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now.isoformat(),
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%Y-%m-%dT%H"),
                    model_name,
                    task_id,
                    int(input_tokens),
                    int(output_tokens),
                    round(float(duration_sec), 3),
                    cost,
                    json.dumps(details or {}, default=str),
                ),
            )
        return cost

    def get_usage_summary(self) -> Dict[str, Any]:
        now = utc_now()
        today_s = now.strftime("%Y-%m-%d")
        hour_s = now.strftime("%Y-%m-%dT%H")
        with self.db._connect() as conn:
            day_row = conn.execute(
                """
                SELECT COUNT(*) AS calls,
                       COALESCE(SUM(input_tokens), 0) AS in_tok,
                       COALESCE(SUM(output_tokens), 0) AS out_tok,
                       COALESCE(SUM(duration_sec), 0.0) AS dur_s,
                       COALESCE(SUM(estimated_cost_usd), 0.0) AS cost_usd
                FROM budget_ledger
                WHERE date_utc = ? AND cost_type = 'AI_AGENT_CALL'
                """,
                (today_s,),
            ).fetchone()
            hr_row = conn.execute(
                """
                SELECT COUNT(*) AS calls, COALESCE(SUM(estimated_cost_usd), 0.0) AS cost_usd
                FROM budget_ledger
                WHERE hour_utc = ? AND cost_type = 'AI_AGENT_CALL'
                """,
                (hour_s,),
            ).fetchone()
            all_row = conn.execute(
                """
                SELECT COUNT(*) AS calls, COALESCE(SUM(estimated_cost_usd), 0.0) AS cost_usd
                FROM budget_ledger
                WHERE cost_type = 'AI_AGENT_CALL'
                """
            ).fetchone()

        # Prorated infrastructure cost for today (UTC hours elapsed * hourly VM rate)
        hours_elapsed_today = now.hour + (now.minute / 60.0) + (now.second / 3600.0)
        vm_hr_rate = float(self.b_cfg.get("prorated_vm_hourly_cost_usd", 0.0730))
        infra_today_usd = round(hours_elapsed_today * vm_hr_rate, 4)

        max_daily_calls = int(self.b_cfg.get("max_daily_ai_invocations", 96))
        max_hourly_calls = int(self.b_cfg.get("max_hourly_ai_invocations", 8))
        max_daily_usd = float(self.b_cfg.get("max_daily_ai_cost_usd", 2.50))

        daily_calls = int(day_row["calls"]) if day_row else 0
        hourly_calls = int(hr_row["calls"]) if hr_row else 0
        daily_ai_usd = round(float(day_row["cost_usd"] or 0.0), 6) if day_row else 0.0
        all_ai_usd = round(float(all_row["cost_usd"] or 0.0), 6) if all_row else 0.0

        return {
            "date_utc": today_s,
            "daily_ai_calls": daily_calls,
            "max_daily_ai_calls": max_daily_calls,
            "hourly_ai_calls": hourly_calls,
            "max_hourly_ai_calls": max_hourly_calls,
            "daily_ai_cost_usd": daily_ai_usd,
            "max_daily_ai_cost_usd": max_daily_usd,
            "all_time_ai_calls": int(all_row["calls"]) if all_row else 0,
            "all_time_ai_cost_usd": all_ai_usd,
            "daily_input_tokens": int(day_row["in_tok"]) if day_row else 0,
            "daily_output_tokens": int(day_row["out_tok"]) if day_row else 0,
            "daily_infra_vm_cost_usd": infra_today_usd,
            "daily_total_ops_cost_usd": round(daily_ai_usd + infra_today_usd, 4),
            "budget_healthy": (
                daily_calls < max_daily_calls
                and hourly_calls < max_hourly_calls
                and daily_ai_usd < max_daily_usd
            ),
        }

    def can_invoke_ai_agent(self, task: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Checks hard AI invocation & spend caps plus economic value justification (reserving 1.5x emergency headroom for P0)."""
        usage = self.get_usage_summary()
        is_p0 = bool(task and str(task.get("priority_label") or "").upper() == "P0")
        cap_mult = 1.5 if is_p0 else 1.0
        if usage["daily_ai_cost_usd"] >= usage["max_daily_ai_cost_usd"] * cap_mult:
            return False, f"DAILY_AI_BUDGET_EXHAUSTED:${usage['daily_ai_cost_usd']:.4f}>=${usage['max_daily_ai_cost_usd'] * cap_mult:.2f}"
        if usage["daily_ai_calls"] >= int(usage["max_daily_ai_calls"] * cap_mult):
            return False, f"DAILY_AI_CALL_LIMIT_REACHED:{usage['daily_ai_calls']}>={int(usage['max_daily_ai_calls'] * cap_mult)}"
        if usage["hourly_ai_calls"] >= int(usage["max_hourly_ai_calls"] * cap_mult):
            return False, f"HOURLY_AI_CALL_LIMIT_REACHED:{usage['hourly_ai_calls']}>={int(usage['max_hourly_ai_calls'] * cap_mult)}"

        if task is not None:
            cat = str(task.get("category") or "")
            prio = str(task.get("priority_label") or "P2")
            ev = float(task.get("expected_net_ev_usd_per_day") or 0.0)
            min_ev = float(self.b_cfg.get("min_expected_daily_ev_for_ai_build_usd", 0.25))
            # P0/P1 safety, service recovery, and forensics are always economically justified to protect principal
            if prio not in ("P0", "P1") and cat in ("ENGINEERING_OPTIMIZATION", "RESEARCH_DISCOVERY") and ev < min_ev:
                return False, f"ECONOMIC_GATE_LOW_EV:expected_daily_ev=${ev:.3f}<min_required=${min_ev:.3f}"
        return True, "OK"

    def check_engineering_concurrency(self) -> Tuple[bool, int, int]:
        max_sim = int(self.b_cfg.get("max_simultaneous_engineering_jobs", 1))
        running = self.db.list_tasks(states=("RUNNING",))
        eng_cnt = sum(
            1 for t in running if str(t.get("category") or "") in ("ENGINEERING_REPAIR", "ENGINEERING_OPTIMIZATION", "QA_VALIDATION")
        )
        return (eng_cnt < max_sim), eng_cnt, max_sim

    def check_api_rate_limit(self, endpoint_key: str, min_interval_sec: Optional[float] = None) -> bool:
        interval = float(
            min_interval_sec
            if min_interval_sec is not None
            else self.b_cfg.get("min_gamma_poll_interval_sec", 60.0)
        )
        now_m = time.monotonic()
        prev = self._last_poll_ts.get(endpoint_key)
        if prev is not None and (now_m - prev) < interval:
            return False
        self._last_poll_ts[endpoint_key] = now_m
        return True

    @staticmethod
    def compute_backoff_seconds(attempt: int, base_sec: float = 30.0, cap_sec: float = 1800.0) -> float:
        return min(float(cap_sec), float(base_sec) * (2 ** max(0, int(attempt) - 1)))
