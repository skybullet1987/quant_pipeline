#!/usr/bin/env python3
"""
Summarise data/polymarket/latency_trace.jsonl (written by src/polymarket_research/latency_trace.py).

Usage:
    python scripts/latency_trace_report.py [path] [--group sleeve|asset|book_source|outcome] [--since-hours N]

Prints p50/p95/p99/p99.9 (+ n, max) for every stage duration, grouped as requested, and flags:
  * records missing key timestamps (Phase-0 exit gate: >= 99% valid)
  * REST-book fallbacks and on-chain inventory RPC usage on the entry path
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_PATH = Path("data") / "polymarket" / "latency_trace.jsonl"

# (name, start stamp, end stamp) derived from stamps_rel_ms; scalar metrics are read directly.
DERIVED = [
    ("consume->dispatch_call (qualify+risk+book+inventory)", "trigger_consumed", "dispatch_call"),
    ("dispatch_call->exec_enter", "dispatch_call", "exec_enter"),
    ("exec_enter->qualify_end (depth/fee/sizing)", "exec_enter", "qualify_end"),
    ("qualify_end->dispatch_enqueue", "qualify_end", "dispatch_enqueue"),
    ("dispatch_enqueue->post_return (hop+sign+POST)", "dispatch_enqueue", "post_return"),
    ("trigger_consumed->post_return (TOTAL)", "trigger_consumed", "post_return"),
]
SCALARS = [
    "trigger_to_consume_wall_ms",
    "ws_book_age_ms",
    "rest_book_fetch_ms",
    "inventory_rpc_ms",
    "qualify_ms",
    "thread_hop_ms",
    "sign_ms",
    "clob_http_post_ms",
    "total_trigger_to_ack_ms",
]


def pct(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return sorted_vals[int(k)]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def load(path: Path, since_hours: Optional[float]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    cutoff_ns = None if since_hours is None else time.time_ns() - int(since_hours * 3600 * 1e9)
    bad = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if cutoff_ns is not None and int(rec.get("created_wall_ns", 0)) < cutoff_ns:
                continue
            out.append(rec)
    if bad:
        print(f"[warn] {bad} unparsable lines skipped", file=sys.stderr)
    return out


def stage_ms(rec: Dict[str, Any], a: str, b: str) -> Optional[float]:
    st = rec.get("stamps_rel_ms") or {}
    if a in st and b in st:
        return st[b] - st[a]
    return None


def fmt(vals: List[float]) -> str:
    s = sorted(vals)
    return (
        f"n={len(s):<5} p50={pct(s,.5):8.2f} p95={pct(s,.95):8.2f} "
        f"p99={pct(s,.99):8.2f} p99.9={pct(s,.999):8.2f} max={s[-1]:8.2f}"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=os.environ.get("PM_LATENCY_TRACE_FILE", str(DEFAULT_PATH)))
    ap.add_argument("--group", default="sleeve", help="field to group by (sleeve, asset, book_source, outcome)")
    ap.add_argument("--since-hours", type=float, default=None)
    args = ap.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"No trace file at {path}. Run the harvester with PM_LATENCY_TRACE=1 (default).")
        return 1
    recs = load(path, args.since_hours)
    if not recs:
        print("Trace file is empty for the selected window.")
        return 1

    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in recs:
        groups[str(r.get(args.group) or "(none)")].append(r)

    # Phase-0 exit gate: timestamp validity
    needed = ("trigger_consumed", "dispatch_call", "exec_enter", "dispatch_enqueue", "post_return")
    valid = sum(1 for r in recs if all(k in (r.get("stamps_rel_ms") or {}) for k in needed) or r.get("outcome") == "dispatch_exception")
    print(f"records={len(recs)}  timestamp-complete={valid} ({100.0*valid/len(recs):.1f}%)  [gate >= 99%]")
    rest = sum(1 for r in recs if r.get("book_source") == "rest")
    rpc = sum(1 for r in recs if r.get("inventory_rpc_used"))
    unk = sum(1 for r in recs if r.get("outcome") == "dispatch_exception")
    print(f"rest-book fallbacks={rest}  inventory-RPC-on-entry={rpc}  dispatch exceptions={unk}\n")

    for gname, grecs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"=== {args.group} = {gname}  ({len(grecs)} dispatches) ===")
        for label, a, b in DERIVED:
            vals = [v for v in (stage_ms(r, a, b) for r in grecs) if v is not None]
            if vals:
                print(f"  {label:<52} {fmt(vals)}")
        for key in SCALARS:
            vals = [float(r[key]) for r in grecs if isinstance(r.get(key), (int, float))]
            if vals:
                print(f"  {key:<52} {fmt(vals)}")
        by_out: Dict[str, int] = defaultdict(int)
        for r in grecs:
            by_out[f"{r.get('outcome')}/{r.get('resp_status')}"] += 1
        print("  outcomes: " + ", ".join(f"{k}={v}" for k, v in sorted(by_out.items(), key=lambda kv: -kv[1])))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
