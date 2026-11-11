#!/usr/bin/env python3
"""
Inode-Preserving Hot/Cold JSONL Telemetry Compactor (Polymarket + Alpha-124)
===========================================================================
Compresses older slices of high-frequency `.jsonl` telemetry into `archive/<stem>__<UTC>.jsonl.gz`
while keeping a live uncompressed hot tail in place so `inotify` descriptors, open file handles
(`trigger_fp`, `_shock_file_offset`), and startup pre-warm readers (`_prewarm_hourly_opens`)
never break or miss lines.

Safety & Integrity Guarantees:
  1. Never touches trade/audit/resolution ledgers (`live_orders.jsonl`, `forensic_audit_ledger.jsonl`,
     `alpha124_shadow_ledger.jsonl`, `*resolutions*.jsonl`, `*.json`).
  2. Streams compression in bounded 4 MB chunks (constant <16 MB RAM even on multi-GB backlogs).
  3. Verifies exact decompressed byte count AND SHA-256 checksum of `.jsonl.gz` BEFORE truncating.
  4. Performs in-place `copytruncate` under `fcntl.flock(LOCK_EX)` (preserving `st_ino` for `inotify`
     and capturing any bytes appended while `gzip` was running).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHUNK_BYTES = 4 * 1024 * 1024  # 4 MB bounded streaming buffer

PROTECTED_EXACT_NAMES = frozenset(
    {
        "live_orders.jsonl",
        "forensic_audit_ledger.jsonl",
        "alpha124_shadow_ledger.jsonl",
        "finalized_market_resolutions.jsonl",
        "ground_truth_resolutions.jsonl",
        "ground_truth_resolutions_eth.jsonl",
        "ground_truth_resolutions_sol.jsonl",
        "d1_live_box_candidates.jsonl",
        "two_leg_live_box_candidates.jsonl",
        "live_shock_triggers.jsonl",  # byte-offset tailed by shadow daemon / harvester / paper trader
        "telemetry_compactor_audit.jsonl",
        "compactor.log",
    }
)
PROTECTED_SUBSTRINGS = ("resolution", "live_orders", "shadow_ledger", "audit_ledger", "live_box_candidates")


@dataclass(frozen=True)
class CompactionRule:
    rel_dir: str
    glob_pattern: str
    hot_threshold_mb: float
    keep_tail_mb: float
    min_archive_mb: float = 1.0


DEFAULT_RULES: Tuple[CompactionRule, ...] = (
    CompactionRule("data/polymarket", "polymarket_*telemetry*.jsonl", hot_threshold_mb=10.0, keep_tail_mb=3.0),
    CompactionRule("data/polymarket", "shock_responses*.jsonl", hot_threshold_mb=10.0, keep_tail_mb=3.0),
    CompactionRule("data/polymarket", "leadlag_cross_correlations*.jsonl", hot_threshold_mb=8.0, keep_tail_mb=2.0),
    CompactionRule("data/polymarket", "exp306_realtime_boundary_merge.jsonl", hot_threshold_mb=8.0, keep_tail_mb=2.0),
    CompactionRule("data/polymarket", "counterfactual_candidates.jsonl", hot_threshold_mb=8.0, keep_tail_mb=2.0),
    # NOTE: live_shock_triggers.jsonl intentionally NOT compacted — daemons tail it by byte offset
    # (`_shock_file_offset`), and an in-place truncate makes them re-read the hot tail (duplicate triggers).
    CompactionRule("data/alpha124", "alpha124_market_telemetry.jsonl", hot_threshold_mb=8.0, keep_tail_mb=2.0),
    CompactionRule("data/polymarket", "*.log", hot_threshold_mb=12.0, keep_tail_mb=2.5),
    CompactionRule("data/alpha124", "*.log", hot_threshold_mb=8.0, keep_tail_mb=2.0),
)


def is_protected_path(path: Path) -> bool:
    name_l = path.name.lower()
    if path.name in PROTECTED_EXACT_NAMES or not (name_l.endswith(".jsonl") or name_l.endswith(".log")):
        return True
    return any(tok in name_l for tok in PROTECTED_SUBSTRINGS)


def _find_newline_cut_offset(path: Path, st_size: int, keep_tail_bytes: int) -> int:
    """Finds an exact `\\n` byte boundary near `st_size - keep_tail_bytes` without loading the whole file."""
    target_pos = max(0, st_size - keep_tail_bytes)
    with open(path, "rb") as f:
        f.seek(target_pos)
        probe = f.read(min(2 * 1024 * 1024, st_size - target_pos))
    nl = probe.find(b"\n")
    if nl < 0:
        return 0
    return target_pos + nl + 1


def _next_archive_path(archive_dir: Path, stem: str, suffix: str = ".jsonl", now_dt: Optional[datetime] = None) -> Path:
    dt = now_dt or datetime.now(timezone.utc)
    stamp = dt.strftime("%Y%m%dT%H%M%SZ")
    cand = archive_dir / f"{stem}__{stamp}{suffix}.gz"
    seq = 1
    while cand.exists():
        cand = archive_dir / f"{stem}__{stamp}_{seq}{suffix}.gz"
        seq += 1
    return cand


def compact_jsonl_file(
    path: Path,
    archive_dir: Optional[Path] = None,
    *,
    hot_threshold_bytes: int = 12 * 1024 * 1024,
    keep_tail_bytes: int = 4 * 1024 * 1024,
    min_archive_bytes: int = 1 * 1024 * 1024,
    compresslevel: int = 6,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Archives `[0 .. cut_idx)` of `path` to `<archive_dir>/<stem>__<UTC>.jsonl.gz`, verifies SHA-256
    round-trip integrity, and truncates `path` in-place preserving `st_ino` and any newly appended tail.
    """
    if not path.exists():
        return {"file": str(path), "status": "MISSING"}
    if is_protected_path(path):
        return {"file": str(path), "status": "SKIPPED_PROTECTED"}

    st0 = path.stat()
    orig_size = st0.st_size
    orig_ino = st0.st_ino
    if orig_size <= hot_threshold_bytes:
        return {"file": path.name, "status": "SKIPPED_UNDER_THRESHOLD", "size_bytes": orig_size}

    cut_idx = _find_newline_cut_offset(path, orig_size, keep_tail_bytes)
    if cut_idx < min_archive_bytes or cut_idx >= orig_size:
        return {"file": path.name, "status": "SKIPPED_CUT_TOO_SMALL", "size_bytes": orig_size, "cut_idx": cut_idx}

    arch_dir = archive_dir or (path.parent / "archive")
    if dry_run:
        return {
            "file": path.name,
            "status": "DRY_RUN_WOULD_COMPACT",
            "orig_size_bytes": orig_size,
            "archive_raw_bytes": cut_idx,
            "est_tail_bytes": orig_size - cut_idx,
        }

    arch_dir.mkdir(parents=True, exist_ok=True)
    final_gz = _next_archive_path(arch_dir, path.stem, suffix=path.suffix)
    tmp_gz = final_gz.with_suffix(f".gz.tmp.{os.getpid()}")

    t0 = time.monotonic()
    raw_hasher = hashlib.sha256()
    written_raw = 0
    try:
        # Phase 1: Stream `[0 .. cut_idx)` into gzip temp file outside flock (zero writer stall!)
        with open(path, "rb") as src_f, gzip.open(tmp_gz, "wb", compresslevel=compresslevel) as gz_f:
            rem = cut_idx
            while rem > 0:
                buf = src_f.read(min(CHUNK_BYTES, rem))
                if not buf:
                    break
                raw_hasher.update(buf)
                gz_f.write(buf)
                written_raw += len(buf)
                rem -= len(buf)

        if written_raw != cut_idx:
            raise RuntimeError(f"Short read while archiving {path.name}: {written_raw} != {cut_idx}")

        # Phase 2: Cryptographic round-trip verification BEFORE truncating live file
        ver_hasher = hashlib.sha256()
        ver_bytes = 0
        with gzip.open(tmp_gz, "rb") as ver_f:
            while True:
                vbuf = ver_f.read(CHUNK_BYTES)
                if not vbuf:
                    break
                ver_hasher.update(vbuf)
                ver_bytes += len(vbuf)

        if ver_bytes != cut_idx or ver_hasher.hexdigest() != raw_hasher.hexdigest():
            raise RuntimeError(
                f"Gzip verification mismatch for {path.name}: bytes {ver_bytes}!={cut_idx} or sha256 mismatch"
            )

        gz_size = tmp_gz.stat().st_size
        os.replace(tmp_gz, final_gz)

        # Phase 3: Millisecond inode-preserving copytruncate under exclusive flock
        with open(path, "r+b") as rw_f:
            locked = False
            try:
                try:
                    import fcntl

                    fcntl.flock(rw_f.fileno(), fcntl.LOCK_EX)
                    locked = True
                except Exception:
                    pass

                rw_f.seek(cut_idx - 1)
                boundary_byte = rw_f.read(1)
                if boundary_byte != b"\n":
                    raise RuntimeError(f"Boundary byte at {cut_idx - 1} changed ({boundary_byte!r}); aborting truncate")
                new_tail = rw_f.read()
                rw_f.seek(0)
                if new_tail:
                    rw_f.write(new_tail)
                rw_f.truncate(len(new_tail))
                rw_f.flush()
            finally:
                if locked:
                    try:
                        import fcntl

                        fcntl.flock(rw_f.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
            # fsync AFTER releasing LOCK_EX: compactor runs at Nice=19 / low IO priority, so a slow
            # fsync under the lock would priority-invert and stall recorder event loops on flock.
            os.fsync(rw_f.fileno())

        new_st = path.stat()
        elapsed_s = round(time.monotonic() - t0, 3)
        ratio = round(cut_idx / max(1, gz_size), 2)
        return {
            "file": path.name,
            "status": "COMPACTED",
            "archive_file": str(final_gz.name),
            "orig_size_mb": round(orig_size / (1024 * 1024), 2),
            "archived_raw_mb": round(cut_idx / (1024 * 1024), 2),
            "archived_gz_mb": round(gz_size / (1024 * 1024), 2),
            "new_hot_tail_mb": round(new_st.st_size / (1024 * 1024), 2),
            "freed_mb": round((cut_idx - gz_size) / (1024 * 1024), 2),
            "compression_ratio_x": ratio,
            "inode_preserved": (orig_ino == new_st.st_ino) if orig_ino else True,
            "sha256": raw_hasher.hexdigest()[:16],
            "elapsed_sec": elapsed_s,
        }
    except Exception:
        if tmp_gz.exists():
            try:
                tmp_gz.unlink()
            except OSError:
                pass
        raise


def iter_archived_and_hot_lines(data_dir: Path, filename: str) -> Iterator[str]:
    """Streams chronological `<stem>__20*.jsonl.gz` cold archives followed by the hot `.jsonl` tail."""
    stem = Path(filename).stem
    arch_dir = data_dir / "archive"
    prefix = f"{stem}__20"
    if arch_dir.is_dir():
        for gz_p in sorted(arch_dir.glob(f"{stem}__*.jsonl.gz")):
            if not gz_p.name.startswith(prefix):
                continue
            with gzip.open(gz_p, "rt", encoding="utf-8", errors="replace") as gf:
                for ln in gf:
                    yield ln
    hot_p = data_dir / filename
    if hot_p.exists():
        with open(hot_p, "r", encoding="utf-8", errors="replace") as hf:
            for ln in hf:
                yield ln


def run_compaction_sweep(
    root_dir: Path = PROJECT_ROOT,
    dry_run: bool = False,
    max_archive_age_days: float = 0.0,
) -> Dict[str, Any]:
    seen: set[Path] = set()
    results: List[Dict[str, Any]] = []
    total_freed_mb = 0.0
    total_archived_raw_mb = 0.0
    total_archived_gz_mb = 0.0
    pruned_archives = 0

    for rule in DEFAULT_RULES:
        t_dir = root_dir / rule.rel_dir
        if not t_dir.is_dir():
            continue
        for fpath in sorted(t_dir.glob(rule.glob_pattern)):
            rp = fpath.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            res = compact_jsonl_file(
                fpath,
                hot_threshold_bytes=int(rule.hot_threshold_mb * 1024 * 1024),
                keep_tail_bytes=int(rule.keep_tail_mb * 1024 * 1024),
                min_archive_bytes=int(rule.min_archive_mb * 1024 * 1024),
                dry_run=dry_run,
            )
            results.append(res)
            if res.get("status") == "COMPACTED":
                total_freed_mb += float(res.get("freed_mb", 0.0))
                total_archived_raw_mb += float(res.get("archived_raw_mb", 0.0))
                total_archived_gz_mb += float(res.get("archived_gz_mb", 0.0))

    if max_archive_age_days > 0.0:
        cutoff_ts = time.time() - (max_archive_age_days * 86400.0)
        for rel_d in sorted({r.rel_dir for r in DEFAULT_RULES}):
            arch_d = root_dir / rel_d / "archive"
            if not arch_d.is_dir():
                continue
            for gz_f in sorted(arch_d.glob("*.gz")):
                if gz_f.stat().st_mtime < cutoff_ts:
                    pruned_archives += 1
                    if not dry_run:
                        gz_f.unlink(missing_ok=True)

    summary = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": dry_run,
        "compacted_files": sum(1 for r in results if r.get("status") == "COMPACTED"),
        "pruned_archives": pruned_archives,
        "total_archived_raw_mb": round(total_archived_raw_mb, 2),
        "total_archived_gz_mb": round(total_archived_gz_mb, 2),
        "total_freed_mb": round(total_freed_mb, 2),
        "overall_ratio_x": round(total_archived_raw_mb / total_archived_gz_mb, 2) if total_archived_gz_mb > 0 else 0.0,
        "files": [r for r in results if r.get("status") in ("COMPACTED", "DRY_RUN_WOULD_COMPACT")],
    }
    if not dry_run and (summary["compacted_files"] > 0 or pruned_archives > 0):
        audit_p = root_dir / "data" / "polymarket" / "telemetry_compactor_audit.jsonl"
        try:
            audit_p.parent.mkdir(parents=True, exist_ok=True)
            with open(audit_p, "a", encoding="utf-8") as af:
                af.write(json.dumps(summary, separators=(",", ":")) + "\n")
        except Exception:
            pass
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Polymarket + Alpha-124 Inode-Safe Telemetry Compactor")
    ap.add_argument("--root", type=Path, default=PROJECT_ROOT, help="Pipeline root directory")
    ap.add_argument("--dry-run", action="store_true", help="Report candidate compactions without modifying files")
    ap.add_argument("--max-archive-age-days", type=float, default=0.0, help="Optional retention window for .gz archives (0 = keep forever)")
    args = ap.parse_args()
    out = run_compaction_sweep(root_dir=args.root, dry_run=args.dry_run, max_archive_age_days=args.max_archive_age_days)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
