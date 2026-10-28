#!/usr/bin/env python3
"""
bundle_polymarket_all_in_one.py
Bundles all core Polymarket production daemons, execution engines, on-chain tools,
Purged Walk-Forward Optimizer, forensic auditor, and config/systemd definitions
into a single unified Python file strictly under 1,000,000 bytes (< 1 MB) with exact TOC line numbers.
"""

import ast
import io
import re
import tokenize
from pathlib import Path
from datetime import datetime, timezone

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PIPELINE_ROOT / "polymarket_all_in_one.py"
OUTPUT_TXT_FILE = PIPELINE_ROOT / "polymarket_all_in_one.txt"

# Ordered list of all Polymarket v3.9 production modules (< 1,000,000 bytes AST-invariant)
MODULES = [
    # 1. CENTRALIZED RISK CONFIG & SYSTEMD PRODUCTION UNIT
    ("config/polymarket_risk_config.json", "Centralized Risk & Sizing Limits (Single Source of Truth)"),
    ("systemd/polymarket-live-harvester.service", "Graceful systemd Production Unit (Restart=on-failure, --max-tte 1200.0)"),

    # 2. CORE LIVE EXECUTION, HARVESTING & STREAMING ENGINE (v3.9 Purged-WFO & CPCV Production Daemons)
    ("src/polymarket_research/polymarket_live_harvester.py", "v3.9 Live Harvester Engine, Oracle-Exact Gates & 95c/98c Two-Tranche Supervisor"),
    ("src/polymarket_research/polymarket_live_executor.py", "Polymarket CLOB L2 Client, Priority EIP-712 Signing & pUSD/CTF Adapter"),
    ("src/polymarket_research/polymarket_terminal_recorder.py", "Sub-ms Binance/Coinbase/Chainlink-TWAP Shock Detection & CLOB L2 SHM Recorder"),
    ("src/polymarket_research/deribit_svi_surface.py", "Deribit SVI Options Volatility Surface & Breeden-Litzenberger Engine"),
    ("src/polymarket_research/polymarket_paper_trader.py", "Forward Paper Trader & Production-Parity Simulation Engine"),

    # 3. ON-CHAIN COLLATERAL (pUSD + USDC.e), ALLOWANCES & POSITION REDEMPTION
    ("src/polymarket_research/check_polymarket_balance.py", "Polygon pUSD + USDC.e Collateral Balance Checker"),
    ("src/polymarket_research/verify_onchain_allowances.py", "ERC-20/ERC-1155 Proxy & Exchange Allowance Verifier"),
    ("src/polymarket_research/redeem_settled_positions.py", "CTF Settled Position Redemption Engine"),
    # setup_polymarket_account.py (one-time CLOB L2 credential generator) lives only in the full-codebase bundle
    # to keep this production bundle under the 1,000,000-byte cap.

    # 4. AUTONOMOUS POST-TRADE FORENSICS & ZERO-LOOKAHEAD PURGED WALK-FORWARD OPTIMIZER
    ("audit_losing_trades.py", "Autonomous Post-Trade Forensic Auditor & Daemon Health Verifier"),
    ("scripts/honest_purged_wfo_optimizer.py", "Zero-Lookahead Purged WFO & Genuine Refit CPCV(6,2) Optimizer"),
]

_FUTURE_RE = re.compile(r"^(from\s+__future__\s+import\s+[^\n]+)$", flags=re.MULTILINE)
_KEEP_COMMENT_RE = re.compile(r"Lifted|^#!")


def transform_module(rel_path: str, code: str) -> str:
    """Deterministic AST-invariant text a source file contributes to the <1 MB bundle (verified by test_zero_trust_forensic_audit)."""
    if not rel_path.endswith(".py"):
        var_name = re.sub(r"[^0-9A-Za-z]", "_", Path(rel_path).name).upper()
        return f"# Non-Python asset embedded as string constant:\n{var_name} = r'''\n{code}\n'''\n\n"
    clean_code = _FUTURE_RE.sub(r"# \1  # (Lifted to top of consolidated bundle)", code)
    lines = clean_code.splitlines(keepends=True)
    drop_lines = set()
    replace_pass: dict[int, str] = {}
    try:
        tree = ast.parse(clean_code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
                first = node.body[0]
                if (
                    isinstance(first, ast.Expr)
                    and isinstance(getattr(first, "value", None), ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    s_idx = first.lineno - 1
                    e_idx = (first.end_lineno or first.lineno) - 1
                    if len(node.body) == 1 and not isinstance(node, ast.Module):
                        indent = lines[s_idx][: len(lines[s_idx]) - len(lines[s_idx].lstrip())]
                        replace_pass[s_idx] = f"{indent}pass\n"
                        for k in range(s_idx + 1, e_idx + 1):
                            drop_lines.add(k)
                    else:
                        for k in range(s_idx, e_idx + 1):
                            drop_lines.add(k)
    except Exception:
        pass
    inline_strip: dict[int, int] = {}
    for tok in tokenize.generate_tokens(io.StringIO(clean_code).readline):
        if tok.type == tokenize.COMMENT:
            idx = tok.start[0] - 1
            if idx in drop_lines or idx in replace_pass:
                continue
            ln = lines[idx]
            if ln.lstrip().startswith("#"):
                if not _KEEP_COMMENT_RE.search(ln):
                    drop_lines.add(idx)
            elif not _KEEP_COMMENT_RE.search(tok.string):
                inline_strip[idx] = tok.start[1]
    out_lines = []
    for i, ln in enumerate(lines):
        if i in drop_lines:
            continue
        if i in replace_pass:
            out_lines.append(replace_pass[i])
            continue
        if i in inline_strip:
            ln = ln[: inline_strip[i]].rstrip() + "\n"
        out_lines.append(ln)
    compacted = re.sub(r"\n(?:[ \t]*\n)+", "\n", "".join(out_lines))
    nl_rows = {
        tok.start[0] - 1
        for tok in tokenize.generate_tokens(io.StringIO(compacted).readline)
        if tok.type == tokenize.NL
    }
    if nl_rows:
        c_lines = compacted.splitlines(keepends=True)
        joined = []
        for idx, cln in enumerate(c_lines):
            if idx > 0 and (idx - 1) in nl_rows:
                cln = " " + cln.lstrip(" \t")
            if idx in nl_rows:
                cln = cln.rstrip("\r\n")
            joined.append(cln)
        compacted = "".join(joined)
    compacted = re.sub(r"\n([ \t]{4,})", lambda m: "\n" + " " * (len(m.group(1)) // 2), compacted)
    op_spans_by_row: dict[int, list[tuple[int, int]]] = {}
    fstr_start = getattr(tokenize, "FSTRING_START", -1)
    fstr_end = getattr(tokenize, "FSTRING_END", -1)
    fstr_depth = 0
    for tok in tokenize.generate_tokens(io.StringIO(compacted).readline):
        if tok.type == fstr_start:
            fstr_depth += 1
        elif tok.type == fstr_end:
            fstr_depth = max(0, fstr_depth - 1)
        elif (
            fstr_depth == 0
            and tok.type == tokenize.OP
            and tok.string in {",", ":", "=", "==", "!=", "<=", ">=", "->"}
            and tok.start[0] == tok.end[0]
        ):
            op_spans_by_row.setdefault(tok.start[0] - 1, []).append((tok.start[1], tok.end[1]))
    if op_spans_by_row:
        r_lines = compacted.splitlines(keepends=True)
        for r_idx, spans in op_spans_by_row.items():
            ln = r_lines[r_idx]
            indent_len = len(ln) - len(ln.lstrip(" \t"))
            for s_col, e_col in reversed(spans):
                r_end = e_col
                while r_end < len(ln) and ln[r_end] in (" ", "\t"):
                    r_end += 1
                l_start = s_col
                while l_start > indent_len and ln[l_start - 1] in (" ", "\t"):
                    l_start -= 1
                ln = ln[:l_start] + ln[s_col:e_col] + ln[r_end:]
            r_lines[r_idx] = ln
        tightened = "".join(r_lines)
        if ast.dump(ast.parse(tightened)) == ast.dump(ast.parse(compacted)):
            compacted = tightened
    return compacted.rstrip("\n") + "\n\n"


def _assemble(module_data, toc_lines):
    header_text = f'''"""
POLYMARKET COMPLETE UNIFIED SYSTEM CODEBASE (ALL-IN-ONE BUNDLE)
Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")} | Repo: {PIPELINE_ROOT.as_posix()}
TABLE OF CONTENTS (Exact 1-Based Line Ranges):
'''
    chunks = [header_text]
    for ln in toc_lines:
        chunks.append(ln + "\n")
    chunks.append('"""\nfrom __future__ import annotations\n')

    cur_line = sum(c.count("\n") for c in chunks)
    computed_toc = []
    for idx, (rel_path, desc, code) in enumerate(module_data, 1):
        banner = f"# === [{idx:02d}/{len(module_data):02d}] {rel_path} :: {desc} ===\n"
        body = transform_module(rel_path, code)
        start_line = cur_line + 1
        end_line = cur_line + banner.count("\n") + body.count("\n")
        n_bytes = len(code.encode("utf-8"))
        computed_toc.append(
            f"  - [{rel_path}] (Lines {start_line:,} - {end_line:,} | {n_bytes:,} B) :: {desc}"
        )
        chunks.append(banner)
        chunks.append(body)
        cur_line = end_line
    return "".join(chunks), computed_toc


def main():
    print(f"Bundling {len(MODULES)} Polymarket modules into {OUTPUT_FILE}...")
    module_data = []
    for rel_path, desc in MODULES:
        full_path = PIPELINE_ROOT / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Required bundle module missing: {full_path}")
        code = full_path.read_text(encoding="utf-8", errors="replace")
        module_data.append((rel_path, desc, code))

    placeholder = [f"  - [{r}] :: {d}" for r, d, _ in module_data]
    _, exact_toc = _assemble(module_data, placeholder)
    full_code, verify_toc = _assemble(module_data, exact_toc)
    assert exact_toc == verify_toc, "TOC line counts shifted!"

    total_bytes = len(full_code.encode("utf-8"))
    assert total_bytes < 1_000_000, f"File size {total_bytes:,} bytes exceeds 1,000,000-byte limit!"
    compile(full_code, "polymarket_all_in_one.py", "exec")

    OUTPUT_FILE.write_text(full_code, encoding="utf-8", newline="\n")
    OUTPUT_TXT_FILE.write_text(full_code, encoding="utf-8", newline="\n")
    disk_bytes = OUTPUT_FILE.stat().st_size
    assert disk_bytes < 1_000_000, f"Disk file size {disk_bytes:,} bytes exceeds 1,000,000-byte limit!"

    total_lines = len(full_code.splitlines())
    print(f"SUCCESS: Generated {OUTPUT_FILE} and {OUTPUT_TXT_FILE}")
    print(f"  - Total Modules: {len(module_data)}")
    print(f"  - Total Lines:   {total_lines:,}")
    print(f"  - Total Size:    {disk_bytes:,} bytes ({disk_bytes / 1_000_000:.3f} MB decimal / {disk_bytes / (1024*1024):.3f} MiB)")
    for t in verify_toc:
        print(t)


if __name__ == "__main__":
    main()
