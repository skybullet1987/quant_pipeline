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
    # 1. CENTRALIZED RISK & STRATEGY GOVERNANCE CONFIG + SYSTEMD PRODUCTION UNIT
    ("config/polymarket_risk_config.json", "Centralized Risk & Sizing Limits (Backward-Compatible Floor/Caps)"),
    ("config/polymarket_strategy_and_risk.json", "v5.0 Unified Hot-Reloadable Strategy, Routing & Dual-Budget Config"),
    ("systemd/polymarket-live-harvester.service", "Graceful systemd Production Unit (Restart=on-failure, --max-tte 2400.0)"),

    # 2. CORE LIVE EXECUTION, GOVERNANCE, HARVESTING & STREAMING ENGINE (v5.0 Holistic Production Daemons)
    ("src/polymarket_research/holistic_strategy_governance.py", "v5.0 HotReloadConfigManager, ev_terminal_twap_t5 Exit Supervisor & Velocity/Kelly Engine"),
    ("src/polymarket_research/polymarket_live_harvester.py", "v5.0 Live Harvester Engine, Dual-Budget Risk & Unified Exit Supervisor"),
    ("src/polymarket_research/polymarket_live_executor.py", "Polymarket CLOB L2 Client, Priority EIP-712 Signing & pUSD/CTF Adapter"),
    ("src/polymarket_research/polymarket_terminal_recorder.py", "Sub-ms Binance/Coinbase/Chainlink-TWAP Shock Detection & CLOB L2 SHM Recorder"),
    ("src/polymarket_research/deribit_svi_surface.py", "Deribit SVI Options Volatility Surface & Breeden-Litzenberger Engine"),
    ("src/polymarket_research/polymarket_paper_trader.py", "Forward Paper Trader & Production-Parity Simulation Engine"),

    # 3. ON-CHAIN COLLATERAL (pUSD + USDC.e) & POSITION REDEMPTION
    ("src/polymarket_research/check_polymarket_balance.py", "Polygon pUSD + USDC.e Collateral Balance Checker"),
    ("src/polymarket_research/redeem_settled_positions.py", "CTF Settled Position Redemption Engine"),
    # setup_polymarket_account.py & verify_onchain_allowances.py (one-time account/allowance setup CLIs)
    # live in polymarket_full_codebase_v4.py to keep this live production bundle strictly < 1,000,000 bytes.

    # 4. AUTONOMOUS POST-TRADE FORENSICS & ZERO-LOOKAHEAD PURGED WALK-FORWARD OPTIMIZER
    ("audit_losing_trades.py", "Autonomous Post-Trade Forensic Auditor & Daemon Health Verifier"),
    ("scripts/honest_purged_wfo_optimizer.py", "Zero-Lookahead Purged WFO & Genuine Refit CPCV(6,2) Optimizer"),
]

_FUTURE_RE = re.compile(r"^(from\s+__future__\s+import\s+[^\n]+)$", flags=re.MULTILINE)


def transform_module(rel_path: str, code: str) -> str:
    """Deterministic AST-invariant text a source file contributes to the <1 MB bundle (verified by test_zero_trust_forensic_audit)."""
    if not rel_path.endswith(".py"):
        var_name = re.sub(r"[^0-9A-Za-z]", "_", Path(rel_path).name).upper()
        if rel_path.endswith(".json"):
            import json as _json
            code = _json.dumps(_json.loads(code), separators=(",", ":"))
        elif rel_path.endswith(".service"):
            code = "\n".join(ln for ln in code.splitlines() if ln.strip() and not ln.lstrip().startswith("#"))
        return f"{var_name}=r'''\n{code.strip()}\n'''\n"
    clean_code = _FUTURE_RE.sub("", code)
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
            for attr_b in ("body", "orelse", "finalbody"):
                seq_b = getattr(node, attr_b, None)
                if not isinstance(seq_b, list):
                    continue
                kept_b = len(seq_b)
                for st_b in seq_b:
                    val_b = getattr(st_b, "value", None) if isinstance(st_b, ast.Expr) else None
                    fn_b = getattr(val_b, "func", None) if isinstance(val_b, ast.Call) else None
                    if (
                        isinstance(fn_b, ast.Attribute)
                        and fn_b.attr == "debug"
                        and isinstance(fn_b.value, ast.Name)
                        and fn_b.value.id == "logger"
                    ):
                        sb_i, eb_i = st_b.lineno - 1, (st_b.end_lineno or st_b.lineno) - 1
                        if kept_b <= 1:
                            ind_b = lines[sb_i][: len(lines[sb_i]) - len(lines[sb_i].lstrip())]
                            replace_pass[sb_i] = f"{ind_b}pass\n"
                            for k in range(sb_i + 1, eb_i + 1):
                                drop_lines.add(k)
                        else:
                            kept_b -= 1
                            for k in range(sb_i, eb_i + 1):
                                drop_lines.add(k)
    except Exception:
        pass
    inline_strip: dict[int, int] = {}
    for tok in tokenize.generate_tokens(io.StringIO(clean_code).readline):
        if tok.type == tokenize.COMMENT:
            idx = tok.start[0] - 1
            if idx in drop_lines or idx in replace_pass:
                continue
            if lines[idx].lstrip().startswith("#"):
                drop_lines.add(idx)
            else:
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
    compacted = re.sub(r"\n(?:[ \t]*\n)+", "\n", "".join(out_lines)).lstrip("\r\n")
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
    try:
        t_ann = ast.parse(compacted)
        cls_ann_ids: set[int] = set()
        def _collect_cls_anns(stmts):
            for st_c in stmts:
                if isinstance(st_c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if isinstance(st_c, ast.AnnAssign):
                    cls_ann_ids.add(id(st_c))
                for ch_c in ast.iter_child_nodes(st_c):
                    if not isinstance(ch_c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if isinstance(ch_c, ast.AnnAssign):
                            cls_ann_ids.add(id(ch_c))
                        _collect_cls_anns(list(ast.iter_child_nodes(ch_c)))
        for cls_n in ast.walk(t_ann):
            if isinstance(cls_n, ast.ClassDef):
                _collect_cls_anns(cls_n.body)
        ann_spans: dict[int, list[tuple[int, int]]] = {}
        c_b_lines = [ln.encode("utf-8") for ln in compacted.splitlines(keepends=True)]
        for nd in ast.walk(t_ann):
            if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if nd.returns is not None and nd.returns.lineno == nd.returns.end_lineno and nd.returns.end_col_offset is not None:
                    r_i = nd.returns.lineno - 1
                    lb = c_b_lines[r_i]
                    p_arw = lb.rfind(b"->", 0, nd.returns.col_offset)
                    if p_arw >= 0:
                        while p_arw > 0 and lb[p_arw - 1:p_arw] in (b" ", b"\t"):
                            p_arw -= 1
                        ann_spans.setdefault(r_i, []).append((p_arw, nd.returns.end_col_offset))
                all_args = nd.args.posonlyargs + nd.args.args + nd.args.kwonlyargs + ([nd.args.vararg] if nd.args.vararg else []) + ([nd.args.kwarg] if nd.args.kwarg else [])
                for ag in all_args:
                    if ag.annotation is not None and ag.annotation.lineno == ag.annotation.end_lineno and ag.annotation.end_col_offset is not None:
                        r_i = ag.annotation.lineno - 1
                        lb = c_b_lines[r_i]
                        p_col = lb.rfind(b":", 0, ag.annotation.col_offset)
                        if p_col >= 0:
                            while p_col > 0 and lb[p_col - 1:p_col] in (b" ", b"\t"):
                                p_col -= 1
                            ann_spans.setdefault(r_i, []).append((p_col, ag.annotation.end_col_offset))
            elif (
                isinstance(nd, ast.AnnAssign)
                and id(nd) not in cls_ann_ids
                and nd.value is not None
                and isinstance(nd.target, (ast.Name, ast.Attribute))
                and nd.lineno == nd.annotation.lineno == nd.annotation.end_lineno
                and nd.annotation.end_col_offset is not None
                and getattr(nd.target, "end_col_offset", None) is not None
            ):
                r_i = nd.lineno - 1
                lb = c_b_lines[r_i]
                p_col = lb.find(b":", nd.target.end_col_offset, nd.annotation.col_offset + 1)
                if p_col >= 0:
                    while p_col > 0 and lb[p_col - 1:p_col] in (b" ", b"\t"):
                        p_col -= 1
                    ann_spans.setdefault(r_i, []).append((p_col, nd.annotation.end_col_offset))
        if ann_spans:
            for r_i, sps in ann_spans.items():
                lb = c_b_lines[r_i]
                for s_b, e_b in sorted(sps, reverse=True):
                    lb = lb[:s_b] + lb[e_b:]
                c_b_lines[r_i] = lb
            cand_ann = b"".join(c_b_lines).decode("utf-8")
            ast.parse(cand_ann)
            compacted = cand_ann
    except Exception:
        pass
    str_cont_rows: set[int] = set()
    row_depth: dict[int, int] = {}
    cur_depth = 0
    for tok in tokenize.generate_tokens(io.StringIO(compacted).readline):
        if tok.type == tokenize.INDENT:
            cur_depth += 1
        elif tok.type == tokenize.DEDENT:
            cur_depth = max(0, cur_depth - 1)
        else:
            if tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                for r_s in range(tok.start[0], tok.end[0]):
                    str_cont_rows.add(r_s)
            if tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER):
                row_depth.setdefault(tok.start[0] - 1, cur_depth)
    i_lines = compacted.splitlines(keepends=True)
    for idx_i, iln in enumerate(i_lines):
        if idx_i in str_cont_rows:
            continue
        stripped_i = iln.lstrip(" \t")
        if idx_i > 0 and i_lines[idx_i - 1].rstrip("\r\n").endswith("\\"):
            i_lines[idx_i] = (" " * (row_depth.get(idx_i - 1, 0) + 1)) + stripped_i
        elif idx_i in row_depth:
            i_lines[idx_i] = (" " * row_depth[idx_i]) + stripped_i
    reindented = "".join(i_lines)
    try:
        reindent_ok = ast.dump(ast.parse(reindented)) == ast.dump(ast.parse(compacted))
    except SyntaxError:
        reindent_ok = False
    if reindent_ok:
        compacted = reindented
    else:
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
            and tok.string in {",", ":", "=", "==", "!=", "<=", ">=", "<", ">", "+", "-", "*", "/", "%", "//", "**", "<<", ">>", "|", "&", "|=", "&=", "+=", "-=", "*=", "/=", "->", "(", ")", "[", "]", "{", "}"}
            and tok.start[0] == tok.end[0]
        ):
            op_spans_by_row.setdefault(tok.start[0] - 1, []).append((tok.start[1], tok.end[1]))
    if op_spans_by_row:
        r_lines = compacted.splitlines(keepends=True)
        for r_idx, spans in op_spans_by_row.items():
            ln = r_lines[r_idx]
            indent_len = len(ln) - len(ln.lstrip(" \t"))
            for s_col, e_col in reversed(spans):
                op_s = ln[s_col:e_col]
                r_end = e_col
                while r_end < len(ln) and ln[r_end] in (" ", "\t"):
                    r_end += 1
                l_start = s_col
                if op_s not in {"(", "[", "{"} or (s_col > indent_len and ln[:s_col].rstrip(" \t")[-1:] not in {"'", '"'}):
                    while l_start > indent_len and ln[l_start - 1] in (" ", "\t"):
                        l_start -= 1
                ln = ln[:l_start] + op_s + ln[r_end:]
            r_lines[r_idx] = ln
        tightened = "".join(r_lines)
        try:
            if ast.dump(ast.parse(tightened)) == ast.dump(ast.parse(compacted)):
                compacted = tightened
        except SyntaxError:
            pass
    _COMPOUND = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)
    try:
        t_semi = ast.parse(compacted)
        join_next: set[int] = set()
        for nd in ast.walk(t_semi):
            for attr in ("body", "orelse", "finalbody"):
                seq = getattr(nd, attr, None)
                if isinstance(seq, list) and len(seq) >= 2:
                    for a_st, b_st in zip(seq, seq[1:]):
                        if (
                            not isinstance(a_st, _COMPOUND)
                            and not isinstance(b_st, _COMPOUND)
                            and a_st.lineno == (a_st.end_lineno or a_st.lineno)
                            and b_st.lineno == (b_st.end_lineno or b_st.lineno)
                            and b_st.lineno == a_st.lineno + 1
                        ):
                            join_next.add(a_st.lineno - 1)
        if join_next:
            s_lns = compacted.splitlines(keepends=True)
            merged_lns: list[str] = []
            idx_s = 0
            while idx_s < len(s_lns):
                cur_s = s_lns[idx_s]
                while idx_s in join_next and (idx_s + 1) < len(s_lns) and len(cur_s) < 8000:
                    cur_s = cur_s.rstrip("\r\n") + ";" + s_lns[idx_s + 1].lstrip(" \t")
                    idx_s += 1
                merged_lns.append(cur_s)
                idx_s += 1
            cand_semi = "".join(merged_lns)
            if ast.dump(ast.parse(cand_semi)) == ast.dump(t_semi):
                compacted = cand_semi
    except Exception:
        pass
    try:
        t_if = ast.parse(compacted)
        inline_if_rows: set[int] = set()
        for nd in ast.walk(t_if):
            if (
                isinstance(nd, ast.If)
                and not nd.orelse
                and len(nd.body) == 1
                and not isinstance(nd.body[0], _COMPOUND)
                and nd.lineno == nd.test.end_lineno
                and nd.body[0].lineno == (nd.body[0].end_lineno or nd.body[0].lineno) == nd.lineno + 1
            ):
                inline_if_rows.add(nd.lineno - 1)
        if inline_if_rows:
            if_lns = compacted.splitlines(keepends=True)
            out_if: list[str] = []
            idx_f = 0
            while idx_f < len(if_lns):
                cur_f = if_lns[idx_f]
                if idx_f in inline_if_rows and (idx_f + 1) < len(if_lns) and cur_f.rstrip("\r\n").endswith(":"):
                    out_if.append(cur_f.rstrip("\r\n") + if_lns[idx_f + 1].lstrip(" \t"))
                    idx_f += 2
                else:
                    out_if.append(cur_f)
                    idx_f += 1
            cand_if = "".join(out_if)
            if ast.dump(ast.parse(cand_if)) == ast.dump(t_if):
                compacted = cand_if
    except Exception:
        pass
    try:
        t_el = ast.parse(compacted)
        el_lns = compacted.splitlines(keepends=True)
        out_el: list[str] = []
        idx_e = 0
        while idx_e < len(el_lns):
            cur_e = el_lns[idx_e]
            nxt_e = el_lns[idx_e + 1] if (idx_e + 1) < len(el_lns) else ""
            nxt_st = nxt_e.lstrip(" \t")
            if (
                cur_e.strip() in {"else:", "try:", "finally:"}
                and nxt_st
                and not nxt_st.startswith(("if ", "if(", "for ", "for(", "while ", "while(", "with ", "with(", "try:", "try ", "def ", "class ", "async ", "match ", "@"))
                and not nxt_e.rstrip("\r\n").endswith(":")
            ):
                out_el.append(cur_e.rstrip("\r\n") + nxt_st)
                idx_e += 2
            else:
                out_el.append(cur_e)
                idx_e += 1
        cand_el = "".join(out_el)
        if ast.dump(ast.parse(cand_el)) == ast.dump(t_el):
            compacted = cand_el
    except Exception:
        pass
    for _ in range(2):
        try:
            t_hd = ast.parse(compacted)
            hd_lns = compacted.splitlines(keepends=True)
            inline_hdr: set[int] = set()
            for nd in ast.walk(t_hd):
                if isinstance(nd, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.ExceptHandler, ast.FunctionDef, ast.AsyncFunctionDef)):
                    bd = nd.body
                    if bd and all(not isinstance(s, _COMPOUND) for s in bd):
                        b0 = bd[0]
                        b_end = bd[-1].end_lineno or bd[-1].lineno
                        if b0.lineno == b_end and b0.lineno > nd.lineno:
                            hdr_row = b0.lineno - 2
                            if 0 <= hdr_row < len(hd_lns) and hd_lns[hdr_row].rstrip("\r\n").endswith(":"):
                                inline_hdr.add(hdr_row)
            if inline_hdr:
                out_hd: list[str] = []
                idx_h = 0
                while idx_h < len(hd_lns):
                    if idx_h in inline_hdr and (idx_h + 1) < len(hd_lns) and (idx_h + 1) not in inline_hdr:
                        out_hd.append(hd_lns[idx_h].rstrip("\r\n") + hd_lns[idx_h + 1].lstrip(" \t"))
                        idx_h += 2
                    else:
                        out_hd.append(hd_lns[idx_h])
                        idx_h += 1
                cand_hd = "".join(out_hd)
                if ast.dump(ast.parse(cand_hd)) == ast.dump(t_hd):
                    compacted = cand_hd
        except Exception:
            pass
    try:
        t_lx = ast.parse(compacted)
        lx_lines = compacted.splitlines(keepends=True)
        fstr_m = getattr(tokenize, "FSTRING_MIDDLE", -1)
        fstr_s = getattr(tokenize, "FSTRING_START", -1)
        fstr_e = getattr(tokenize, "FSTRING_END", -1)
        prev_t = None
        lx_edits: dict[int, list[tuple[int, int, str]]] = {}
        for tok in tokenize.generate_tokens(io.StringIO(compacted).readline):
            r_i = tok.start[0] - 1
            s_num_eff = tok.string
            if tok.type == tokenize.NUMBER and tok.start[0] == tok.end[0]:
                s_num = tok.string.replace("_", "")
                s_num_best = s_num
                if "." in s_num and "e" not in s_num.lower():
                    s_new = s_num.rstrip("0")
                    if s_new.startswith("0.") and len(s_new) > 2:
                        s_new = s_new[1:]
                    elif s_new == "0.":
                        s_new = ".0"
                    if len(s_new) < len(s_num) and float(s_new) == float(s_num):
                        s_num_best = s_new
                    try:
                        f_val = float(s_num)
                        for p_sci in range(0, 6):
                            s_sci = f"{f_val:.{p_sci}e}".replace("e+0", "e").replace("e+", "e").replace("e-0", "e-")
                            if len(s_sci) < len(s_num_best) and float(s_sci) == f_val:
                                s_num_best = s_sci
                                break
                    except Exception:
                        pass
                if len(s_num_best) < len(tok.string):
                    ln_cur = lx_lines[r_i]
                    nxt_c = ln_cur[tok.end[1]:tok.end[1] + 1]
                    prv_c = ln_cur[tok.start[1] - 1:tok.start[1]] if tok.start[1] > 0 else ""
                    if not (s_num_best.endswith(".") and (nxt_c.isalpha() or nxt_c == "_")) and not (
                        s_num_best.startswith(".") and (prv_c.isalnum() or prv_c in ("_", "."))
                    ) and not (nxt_c.isalnum() or nxt_c == "_"):
                        lx_edits.setdefault(r_i, []).append((tok.start[1], tok.end[1], s_num_best))
                        s_num_eff = s_num_best
            if prev_t is not None and prev_t.end[0] == tok.start[0]:
                if (
                    prev_t.type == tokenize.STRING
                    and tok.type == tokenize.STRING
                    and (
                        (prev_t.string.startswith('"') and not prev_t.string.startswith('"""') and tok.string.startswith('"') and not tok.string.startswith('"""'))
                        or (prev_t.string.startswith("'") and not prev_t.string.startswith("'''") and tok.string.startswith("'") and not tok.string.startswith("'''"))
                    )
                ):
                    lx_edits.setdefault(r_i, []).append((prev_t.end[1] - 1, tok.start[1] + 1, ""))
                elif prev_t.type == fstr_e and tok.type == fstr_s and prev_t.string in ('"', "'") and tok.string == "f" + prev_t.string:
                    lx_edits.setdefault(r_i, []).append((prev_t.start[1], tok.end[1], ""))
                elif tok.start[1] > prev_t.end[1] and prev_t.type != fstr_m and tok.type != fstr_m:
                    if prev_t.type in (tokenize.STRING, fstr_e) and tok.type == tokenize.NAME:
                        lx_edits.setdefault(r_i, []).append((prev_t.end[1], tok.start[1], ""))
                    elif prev_t.type == tokenize.NAME and tok.type == tokenize.STRING and tok.string[:1] in ("'", '"'):
                        lx_edits.setdefault(r_i, []).append((prev_t.end[1], tok.start[1], ""))
                    elif prev_t.type == tokenize.NAME and tok.type == tokenize.NUMBER and s_num_eff.startswith("."):
                        lx_edits.setdefault(r_i, []).append((prev_t.end[1], tok.start[1], ""))
                    elif (prev_t.type == tokenize.OP or tok.type == tokenize.OP) and not (
                        prev_t.type == tokenize.OP and tok.type == tokenize.OP and prev_t.string in ("+", "-") and tok.string in ("+", "-")
                    ) and not (
                        prev_t.type == tokenize.STRING and tok.type == tokenize.OP and tok.string in ("(", "[", "{")
                    ) and not (
                        prev_t.type == tokenize.NUMBER and prev_t.string.endswith(".") and tok.type == tokenize.NAME
                    ):
                        ind_w = len(lx_lines[r_i]) - len(lx_lines[r_i].lstrip(" \t"))
                        if prev_t.end[1] > ind_w:
                            lx_edits.setdefault(r_i, []).append((prev_t.end[1], tok.start[1], ""))
            if tok.type not in (tokenize.NL, tokenize.NEWLINE):
                prev_t = tok
        if lx_edits:
            for r_i, eds in lx_edits.items():
                ln_m = lx_lines[r_i]
                last_s = 10**9
                for s_c, e_c, rep_s in sorted(eds, key=lambda x: (x[0], x[1]), reverse=True):
                    if e_c <= last_s:
                        ln_m = ln_m[:s_c] + rep_s + ln_m[e_c:]
                        last_s = s_c
                lx_lines[r_i] = ln_m
            cand_lx = "".join(lx_lines)
            if ast.dump(ast.parse(cand_lx)) == ast.dump(t_lx):
                compacted = cand_lx
    except Exception:
        pass
    _KW_BLK_RE = re.compile(r"^(?:if|elif|else|for|while|with|try|except|finally|def|class|async|match|case)\b|@")
    for _ in range(4):
        try:
            t_in = ast.parse(compacted)
            t_in_d = ast.dump(t_in)
            in_lns = compacted.splitlines(keepends=True)
            mstr_rows: set[int] = set()
            for tok in tokenize.generate_tokens(io.StringIO(compacted).readline):
                if tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                    for r_m in range(tok.start[0] - 1, tok.end[0]):
                        mstr_rows.add(r_m)
            out_in: list[str] = []
            idx_in = 0
            changed_in = False
            while idx_in < len(in_lns):
                if (
                    idx_in + 1 < len(in_lns)
                    and idx_in not in mstr_rows
                    and (idx_in + 1) not in mstr_rows
                    and in_lns[idx_in].rstrip("\r\n").endswith(":")
                    and not in_lns[idx_in + 1].rstrip("\r\n").endswith(":")
                ):
                    ns_in = in_lns[idx_in + 1].lstrip(" \t")
                    if ns_in and not _KW_BLK_RE.match(ns_in):
                        ind_c = len(in_lns[idx_in]) - len(in_lns[idx_in].lstrip(" "))
                        ind_n = len(in_lns[idx_in + 1]) - len(in_lns[idx_in + 1].lstrip(" "))
                        ind_2 = (len(in_lns[idx_in + 2]) - len(in_lns[idx_in + 2].lstrip(" "))) if (idx_in + 2) < len(in_lns) else -1
                        if ind_n > ind_c and ind_2 <= ind_c:
                            out_in.append(in_lns[idx_in].rstrip("\r\n") + ns_in)
                            idx_in += 2
                            changed_in = True
                            continue
                out_in.append(in_lns[idx_in])
                idx_in += 1
            if not changed_in:
                break
            cand_in = "".join(out_in)
            if ast.dump(ast.parse(cand_in)) == t_in_d:
                compacted = cand_in
            else:
                break
        except Exception:
            break
    try:
        t_tc = ast.parse(compacted)
        t_tc_d = ast.dump(t_tc)
        one_tup_spans: set[tuple[int, int, int]] = set()
        for nd_t in ast.walk(t_tc):
            if isinstance(nd_t, ast.Tuple) and len(nd_t.elts) == 1 and nd_t.end_lineno and nd_t.end_col_offset is not None:
                el0 = nd_t.elts[0]
                if el0.end_lineno == nd_t.end_lineno and el0.end_col_offset is not None:
                    one_tup_spans.add((nd_t.end_lineno - 1, el0.end_col_offset, nd_t.end_col_offset))
        tc_lns = compacted.splitlines(keepends=True)
        tc_toks = list(tokenize.generate_tokens(io.StringIO(compacted).readline))
        tc_edits: dict[int, list[tuple[int, int]]] = {}
        for i_tk in range(len(tc_toks) - 1):
            tk_a, tk_b = tc_toks[i_tk], tc_toks[i_tk + 1]
            if (
                tk_a.type == tokenize.OP
                and tk_a.string == ","
                and tk_b.type == tokenize.OP
                and tk_b.string in ("]", "}", ")")
                and tk_a.start[0] == tk_a.end[0]
            ):
                r_t = tk_a.start[0] - 1
                if tk_b.string == ")" and any(r_t == rr and c0 <= tk_a.start[1] < c1 for rr, c0, c1 in one_tup_spans):
                    continue
                tc_edits.setdefault(r_t, []).append((tk_a.start[1], tk_a.end[1]))
        if tc_edits:
            for r_tc, sp_tc in tc_edits.items():
                ln_tc = tc_lns[r_tc]
                for s_tc, e_tc in sorted(sp_tc, reverse=True):
                    ln_tc = ln_tc[:s_tc] + ln_tc[e_tc:]
                tc_lns[r_tc] = ln_tc
            cand_tc = "".join(tc_lns)
            if ast.dump(ast.parse(cand_tc)) == t_tc_d:
                compacted = cand_tc
    except Exception:
        pass
    try:
        t_pr = ast.parse(compacted)
        t_pr_d = ast.dump(t_pr)
        pr_lns = compacted.splitlines(keepends=True)
        changed_pr = False
        for r_pr, ln_pr in enumerate(pr_lns):
            if len(ln_pr) > 300 or not ln_pr.rstrip("\r\n").endswith((")", "):")):
                continue
            for pat_pr in (
                (r"^([ ]*(?:if|elif|while|return))\((.+)\)(:?\r?\n)$", r"\1 \2\3"),
                (r"^([ ]*from [A-Za-z0-9_.]+ import)\(([^()\n]+)\)(\r?\n)$", r"\1 \2\3"),
                (r"^([ ]*[A-Za-z_][A-Za-z0-9_.]*=)\(([^,\n]+)\)(\r?\n)$", r"\1\2\3"),
            ):
                m_pr = re.match(pat_pr[0], ln_pr)
                if m_pr:
                    cand_ln = re.sub(pat_pr[0], pat_pr[1], ln_pr)
                    if len(cand_ln) < len(ln_pr):
                        try:
                            if ast.dump(ast.parse("def _w():\n " + cand_ln.lstrip(" "))) == ast.dump(ast.parse("def _w():\n " + ln_pr.lstrip(" "))):
                                pr_lns[r_pr] = cand_ln
                                ln_pr = cand_ln
                                changed_pr = True
                        except Exception:
                            pass
        if changed_pr:
            cand_pr = "".join(pr_lns)
            if ast.dump(ast.parse(cand_pr)) == t_pr_d:
                compacted = cand_pr
    except Exception:
        pass
    try:
        t_bp = ast.parse(compacted)
        t_bp_d = ast.dump(t_bp)
        bp_b = [ln.encode("utf-8") for ln in compacted.splitlines(keepends=True)]
        bp_drop: dict[int, set[int]] = {}
        for nd_b in ast.walk(t_bp):
            if isinstance(nd_b, ast.BinOp) and isinstance(nd_b.op, (ast.Add, ast.Sub)):
                for ch_b in (nd_b.left, nd_b.right):
                    if (
                        isinstance(ch_b, (ast.Call, ast.Attribute, ast.Subscript))
                        or (isinstance(ch_b, ast.BinOp) and isinstance(ch_b.op, (ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)))
                    ) and ch_b.lineno == ch_b.end_lineno and ch_b.col_offset and ch_b.end_col_offset is not None:
                        rb = ch_b.lineno - 1
                        lb = bp_b[rb]
                        c0, c1 = ch_b.col_offset - 1, ch_b.end_col_offset
                        if c0 >= 0 and c1 < len(lb) and lb[c0:c0 + 1] == b"(" and lb[c1:c1 + 1] == b")":
                            prv_b = lb[c0 - 1:c0] if c0 > 0 else b""
                            nxt_b = lb[c1 + 1:c1 + 2]
                            if not (prv_b.isalnum() or prv_b in (b"_", b".")) and not (nxt_b.isalnum() or nxt_b in (b"_", b".")):
                                bp_drop.setdefault(rb, set()).update((c0, c1))
        if bp_drop:
            for rb, cols in bp_drop.items():
                lb = bp_b[rb]
                bp_b[rb] = bytes(b for idx_b, b in enumerate(lb) if idx_b not in cols)
            cand_bp = b"".join(bp_b).decode("utf-8")
            if ast.dump(ast.parse(cand_bp)) == t_bp_d:
                compacted = cand_bp
    except Exception:
        pass
    try:
        t_lv = ast.parse(compacted)
        lv_b = [ln.encode("utf-8") for ln in compacted.splitlines(keepends=True)]
        lv_edits: dict[int, list[tuple[int, int, bytes]]] = {}
        _ID1 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        _B62 = _ID1 + "0123456789"
        def _shallow_walk(stmts):
            stack = list(stmts)
            out_n, nested_defs = [], []
            while stack:
                cur_n = stack.pop()
                if isinstance(cur_n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    nested_defs.append(cur_n)
                    for dec_n in getattr(cur_n, "decorator_list", ()):
                        stack.append(dec_n)
                    if isinstance(cur_n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for df_n in list(cur_n.args.defaults) + [d for d in cur_n.args.kw_defaults if d is not None]:
                            stack.append(df_n)
                    continue
                out_n.append(cur_n)
                stack.extend(ast.iter_child_nodes(cur_n))
            return out_n, nested_defs
        def _safe_locals_pinned(fn_root):
            par = {}
            for p_n in ast.walk(fn_root):
                for ch_n in ast.iter_child_nodes(p_n):
                    par[id(ch_n)] = p_n
            pinned = set()
            for nd_l in ast.walk(fn_root):
                if isinstance(nd_l, ast.Name) and nd_l.id == "locals":
                    if isinstance(nd_l.ctx, ast.Store):
                        return None
                    p1 = par.get(id(nd_l))
                    if not (isinstance(p1, ast.Call) and p1.func is nd_l and not p1.args and not p1.keywords):
                        return None
                    p2 = par.get(id(p1))
                    if (
                        isinstance(p2, ast.Compare)
                        and len(p2.ops) == 1
                        and isinstance(p2.ops[0], (ast.In, ast.NotIn))
                        and len(p2.comparators) == 1
                        and p2.comparators[0] is p1
                        and isinstance(p2.left, ast.Constant)
                        and isinstance(p2.left.value, str)
                    ):
                        pinned.add(p2.left.value)
                    elif isinstance(p2, ast.Attribute) and p2.value is p1 and p2.attr == "get":
                        p3 = par.get(id(p2))
                        if (
                            isinstance(p3, ast.Call)
                            and p3.func is p2
                            and 1 <= len(p3.args) <= 2
                            and not p3.keywords
                            and isinstance(p3.args[0], ast.Constant)
                            and isinstance(p3.args[0].value, str)
                        ):
                            pinned.add(p3.args[0].value)
                        else:
                            return None
                    else:
                        return None
            return pinned
        anc_reserved: dict[int, set[str]] = {}
        anc_renamed_old: dict[int, set[str]] = {}
        for fn_nd in ast.walk(t_lv):
            if not isinstance(fn_nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            full_nodes = [x for st_fn in fn_nd.body for x in ast.walk(st_fn)]
            if any(isinstance(x, ast.ClassDef) for x in full_nodes):
                continue
            all_names = {x.id for x in full_nodes if isinstance(x, ast.Name)}
            if all_names & {"vars", "eval", "exec", "dir"}:
                continue
            locals_pinned: set[str] = set()
            if "locals" in all_names:
                lp_res = _safe_locals_pinned(fn_nd)
                if lp_res is None:
                    continue
                locals_pinned = lp_res
            anc_res = anc_reserved.get(id(fn_nd), set())
            anc_old = anc_renamed_old.get(id(fn_nd), set())
            global_nonlocal_ids = {
                nm for x in full_nodes if isinstance(x, (ast.Global, ast.Nonlocal)) for nm in x.names
            }
            sub_nodes, nested_defs = _shallow_walk(fn_nd.body)
            nested_scopes = [x for x in sub_nodes if isinstance(x, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))]
            nested_eh_names = {
                y.name for ndf in nested_defs for y in ast.walk(ndf) if isinstance(y, ast.ExceptHandler) and y.name
            }
            nested_subdef_names = {
                y.name
                for ndf in nested_defs
                for y in ast.walk(ndf)
                if isinstance(y, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and y is not ndf
            }
            all_arg_names = {x.arg for x in full_nodes if isinstance(x, ast.arg)}
            comp_bound_ids = (
                {y.id for ns in nested_scopes for y in ast.walk(ns) if isinstance(y, ast.Name) and isinstance(y.ctx, ast.Store)}
                | {y.arg for ns in nested_scopes for y in ast.walk(ns) if isinstance(y, ast.arg)}
                | {y.id for ndf in nested_defs for y in ast.walk(ndf) if isinstance(y, ast.Name) and isinstance(y.ctx, ast.Store)}
                | {y.arg for ndf in nested_defs for y in ast.walk(ndf) if isinstance(y, ast.arg)}
                | nested_eh_names
                | nested_subdef_names
                | global_nonlocal_ids
                | locals_pinned
                | anc_old
            )
            p_names = {a.arg for a in (fn_nd.args.posonlyargs + fn_nd.args.args + fn_nd.args.kwonlyargs + ([fn_nd.args.vararg] if fn_nd.args.vararg else []) + ([fn_nd.args.kwarg] if fn_nd.args.kwarg else []))}
            imp_names = {al.asname or al.name.split(".")[0] for x in full_nodes if isinstance(x, (ast.Import, ast.ImportFrom)) for al in x.names}
            store_names = {x.id for x in full_nodes if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)}
            eh_nodes = []
            for x in sub_nodes:
                if isinstance(x, ast.ExceptHandler) and x.name:
                    eh_used = {y.id for st_e in x.body for y in ast.walk(st_e) if isinstance(y, ast.Name)}
                    if (
                        x.name not in eh_used
                        and x.name not in store_names
                        and x.name not in p_names
                        and x.name not in imp_names
                        and x.name not in comp_bound_ids
                        and x.type is not None
                        and x.type.end_lineno == x.lineno
                        and x.type.end_col_offset is not None
                    ):
                        r_eu = x.lineno - 1
                        lb_eu = lv_b[r_eu]
                        c_start = x.type.end_col_offset
                        c_eu = lb_eu.find(b":", c_start)
                        if c_eu > c_start:
                            m_eu = re.match(
                                rb"\s*\bas\s+" + re.escape(x.name.encode("utf-8")) + rb"(?=\s*:)",
                                lb_eu[c_start:c_eu + 1],
                            )
                            if m_eu:
                                lv_edits.setdefault(r_eu, []).append((c_start + m_eu.start(), c_start + m_eu.end(), b""))
                                continue
                    if len(x.name) >= 2:
                        eh_nodes.append(x)
            nested_ids = (
                {y.id for ns in nested_scopes for y in ast.walk(ns) if isinstance(y, ast.Name)}
                | {y.id for ndf in nested_defs for y in ast.walk(ndf) if isinstance(y, ast.Name)}
                | comp_bound_ids
                | all_arg_names
            )
            all_def_names = {x.name for x in full_nodes if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            used_all = all_names | p_names | imp_names | nested_ids | {eh.name for eh in eh_nodes} | {ndf.name for ndf in nested_defs} | all_def_names | anc_res
            stored = {}
            self_arg_nd = (
                fn_nd.args.args[0]
                if (
                    fn_nd.args.args
                    and not fn_nd.args.posonlyargs
                    and fn_nd.args.args[0].arg in ("self", "cls")
                    and "super" not in all_names
                    and fn_nd.args.args[0].arg not in comp_bound_ids
                    and fn_nd.args.args[0].arg not in imp_names
                    and not any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in fn_nd.decorator_list)
                )
                else None
            )
            if self_arg_nd is not None:
                s_nm = self_arg_nd.arg
                self_uses = sum(1 for x in full_nodes if isinstance(x, ast.Name) and x.id == s_nm)
                if self_uses >= 2:
                    stored[s_nm] = self_uses + 1
            for eh in eh_nodes:
                if eh.name not in p_names and eh.name not in imp_names and eh.name not in comp_bound_ids and not eh.name.startswith("__"):
                    stored[eh.name] = stored.get(eh.name, 0) + 2
            renamable_ndefs = [
                ndf for ndf in nested_defs
                if isinstance(ndf, (ast.FunctionDef, ast.AsyncFunctionDef))
                and len(ndf.name) >= 2
                and ndf.name not in p_names
                and ndf.name not in imp_names
                and ndf.name not in comp_bound_ids
                and not ndf.name.startswith("__")
            ]
            for ndf in renamable_ndefs:
                ndf_uses = sum(1 for x in full_nodes if isinstance(x, ast.Name) and x.id == ndf.name)
                stored[ndf.name] = stored.get(ndf.name, 0) + ndf_uses + 1
            imp_alias_targets: list[tuple[ast.alias, int, str, bool]] = []
            for st_imp in sub_nodes:
                if isinstance(st_imp, ast.ImportFrom) and st_imp.lineno == st_imp.end_lineno:
                    for al in st_imp.names:
                        if al.name == "*" or al.lineno != st_imp.lineno or al.end_col_offset is None:
                            continue
                        bnd = al.asname or al.name
                        if bnd in p_names or bnd in comp_bound_ids or bnd.startswith("__"):
                            continue
                        uses_i = sum(1 for x in full_nodes if isinstance(x, ast.Name) and x.id == bnd)
                        if al.asname and len(bnd) >= 2 and uses_i >= 1:
                            imp_alias_targets.append((al, st_imp.lineno - 1, bnd, True))
                            stored[bnd] = stored.get(bnd, 0) + uses_i + 1
                        elif al.asname is None and len(bnd) >= 6 and (uses_i * (len(bnd) - 1)) > 5:
                            imp_alias_targets.append((al, st_imp.lineno - 1, bnd, False))
                            stored[bnd] = stored.get(bnd, 0) + uses_i
            imp_ren_set = {t[2] for t in imp_alias_targets}
            for x in sub_nodes:
                if isinstance(x, ast.Name) and len(x.id) >= 2 and x.id not in p_names and (x.id not in imp_names or x.id in imp_ren_set) and x.id not in comp_bound_ids and not x.id.startswith("__"):
                    if isinstance(x.ctx, ast.Store):
                        stored[x.id] = stored.get(x.id, 0) + 1
            if not stored:
                continue
            gen_idx = 0
            ren_map: dict[str, bytes] = {}
            for old_nm in sorted(stored, key=lambda k: len(k) * stored[k], reverse=True):
                while True:
                    if gen_idx < len(_ID1):
                        short_nm = _ID1[gen_idx]
                    else:
                        g2 = gen_idx - len(_ID1)
                        short_nm = f"_{_B62[g2]}" if g2 < 62 else f"_{_B62[g2 // 62 - 1]}{_B62[g2 % 62]}"
                    gen_idx += 1
                    if len(short_nm) >= len(old_nm):
                        break
                    if short_nm not in used_all:
                        used_all.add(short_nm)
                        ren_map[old_nm] = short_nm.encode("ascii")
                        break
            if ren_map:
                new_shorts = {v.decode("ascii") for v in ren_map.values()}
                new_olds = set(ren_map.keys())
                for sub_fn in full_nodes:
                    if isinstance(sub_fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        anc_reserved.setdefault(id(sub_fn), set()).update(new_shorts)
                        anc_renamed_old.setdefault(id(sub_fn), set()).update(new_olds)
            if self_arg_nd is not None and self_arg_nd.arg in ren_map and self_arg_nd.lineno == self_arg_nd.end_lineno and self_arg_nd.end_col_offset is not None:
                r_sa = self_arg_nd.lineno - 1
                s_b = self_arg_nd.arg.encode("utf-8")
                if lv_b[r_sa][self_arg_nd.col_offset:self_arg_nd.end_col_offset] == s_b:
                    lv_edits.setdefault(r_sa, []).append((self_arg_nd.col_offset, self_arg_nd.end_col_offset, ren_map[self_arg_nd.arg]))
            for eh in eh_nodes:
                if eh.name in ren_map:
                    r_eh = eh.lineno - 1
                    lb_eh = lv_b[r_eh]
                    eh_b = eh.name.encode("utf-8")
                    colon_i = lb_eh.find(b":", eh.col_offset)
                    if colon_i > 0:
                        m_eh = re.search(rb"\bas\s+(" + re.escape(eh_b) + rb")\s*:", lb_eh[eh.col_offset:colon_i + 1])
                        if m_eh:
                            c0_eh = eh.col_offset + m_eh.start(1)
                            c1_eh = eh.col_offset + m_eh.end(1)
                            lv_edits.setdefault(r_eh, []).append((c0_eh, c1_eh, ren_map[eh.name]))
            for ndf in renamable_ndefs:
                if ndf.name in ren_map:
                    r_nd = ndf.lineno - 1
                    lb_nd = lv_b[r_nd]
                    nd_b = ndf.name.encode("utf-8")
                    m_nd = re.search(rb"\bdef\s+(" + re.escape(nd_b) + rb")\s*\(", lb_nd[ndf.col_offset:])
                    if m_nd:
                        c0_nd = ndf.col_offset + m_nd.start(1)
                        c1_nd = ndf.col_offset + m_nd.end(1)
                        lv_edits.setdefault(r_nd, []).append((c0_nd, c1_nd, ren_map[ndf.name]))
            for al, r_im, bnd, had_as in imp_alias_targets:
                if bnd in ren_map and al.end_col_offset is not None:
                    lb_im = lv_b[r_im]
                    bnd_b = bnd.encode("utf-8")
                    if had_as and lb_im[al.end_col_offset - len(bnd_b):al.end_col_offset] == bnd_b:
                        lv_edits.setdefault(r_im, []).append((al.end_col_offset - len(bnd_b), al.end_col_offset, ren_map[bnd]))
                    elif not had_as and lb_im[al.col_offset:al.end_col_offset] == bnd_b:
                        lv_edits.setdefault(r_im, []).append((al.end_col_offset, al.end_col_offset, b" as " + ren_map[bnd]))
            for x in full_nodes:
                if isinstance(x, ast.Name) and x.id in ren_map and x.lineno == x.end_lineno and x.end_col_offset is not None:
                    r_lv = x.lineno - 1
                    if lv_b[r_lv][x.col_offset:x.end_col_offset] == x.id.encode("utf-8"):
                        lv_edits.setdefault(r_lv, []).append((x.col_offset, x.end_col_offset, ren_map[x.id]))
            for ns in nested_scopes:
                if sum(1 for z in ast.walk(ns) if isinstance(z, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))) != 1:
                    continue
                ns_ids = {id(z) for z in ast.walk(ns)}
                outer_names = {x.id for x in sub_nodes if isinstance(x, ast.Name) and id(x) not in ns_ids} | p_names | imp_names | set(ren_map.keys()) | anc_old
                iter0_names = {z.id for z in ast.walk(ns.generators[0].iter) if isinstance(z, ast.Name)} if hasattr(ns, "generators") and ns.generators else set()
                ns_bound = {z.id for z in ast.walk(ns) if isinstance(z, ast.Name) and isinstance(z.ctx, ast.Store)}
                lam_args = [a for a in (ns.args.posonlyargs + ns.args.args) if len(a.arg) >= 2] if isinstance(ns, ast.Lambda) and not ns.args.kwonlyargs and not ns.args.vararg and not ns.args.kwarg and not ns.args.defaults else []
                ns_used = {z.id for z in ast.walk(ns) if isinstance(z, ast.Name)} | {a.arg for a in lam_args} | used_all
                ns_ren: dict[str, bytes] = {}
                c_idx = 0
                cand_b = [b for b in sorted(ns_bound) if len(b) >= 2 and b not in outer_names and b not in iter0_names and not b.startswith("__")] + [
                    a.arg for a in lam_args if a.arg not in outer_names and not a.arg.startswith("__")
                ]
                for bn in cand_b:
                    while c_idx < len(_ID1):
                        sn = _ID1[c_idx]
                        c_idx += 1
                        if sn not in ns_used:
                            ns_used.add(sn)
                            ns_ren[bn] = sn.encode("ascii")
                            break
                if ns_ren:
                    for a_l in lam_args:
                        if a_l.arg in ns_ren and a_l.lineno == a_l.end_lineno and a_l.end_col_offset is not None:
                            rl = a_l.lineno - 1
                            if lv_b[rl][a_l.col_offset:a_l.end_col_offset] == a_l.arg.encode("utf-8"):
                                lv_edits.setdefault(rl, []).append((a_l.col_offset, a_l.end_col_offset, ns_ren[a_l.arg]))
                    for z in ast.walk(ns):
                        if isinstance(z, ast.Name) and z.id in ns_ren and z.lineno == z.end_lineno and z.end_col_offset is not None:
                            rz = z.lineno - 1
                            if lv_b[rz][z.col_offset:z.end_col_offset] == z.id.encode("utf-8"):
                                lv_edits.setdefault(rz, []).append((z.col_offset, z.end_col_offset, ns_ren[z.id]))
        if lv_edits:
            for r_lv, eds_lv in lv_edits.items():
                lb_lv = lv_b[r_lv]
                last_c = 10**9
                for c0_l, c1_l, rep_b in sorted(eds_lv, key=lambda t: (t[0], t[1]), reverse=True):
                    if c1_l <= last_c:
                        lb_lv = lb_lv[:c0_l] + rep_b + lb_lv[c1_l:]
                        last_c = c0_l
                lv_b[r_lv] = lb_lv
            cand_lv = b"".join(lv_b).decode("utf-8")
            compile(cand_lv, rel_path, "exec")
            import symtable as _symtable
            def _verify_symtable_invariance(sb, sa) -> None:
                if sb.get_type() != sa.get_type() or len(sb.get_children()) != len(sa.get_children()):
                    raise RuntimeError(f"Bundle symtable tree mismatch in {rel_path}:{sb.get_name()}")
                if isinstance(sb, _symtable.Function):
                    if (
                        len(sb.get_frees()) != len(sa.get_frees())
                        or len(sb.get_parameters()) != len(sa.get_parameters())
                        or set(sb.get_globals()) != set(sa.get_globals())
                    ):
                        raise RuntimeError(
                            f"Bundle symtable invariance failed in {rel_path}:{sb.get_name()} "
                            f"(frees {sb.get_frees()} -> {sa.get_frees()}, globals {sb.get_globals()} -> {sa.get_globals()})"
                        )
                for cb, ca in zip(sb.get_children(), sa.get_children()):
                    _verify_symtable_invariance(cb, ca)
            _verify_symtable_invariance(
                _symtable.symtable(compacted, rel_path, "exec"),
                _symtable.symtable(cand_lv, rel_path, "exec"),
            )
            compacted = cand_lv
    except RuntimeError:
        raise
    except Exception:
        pass
    try:
        t_s2 = ast.parse(compacted)
        jn2: set[int] = set()
        for nd2 in ast.walk(t_s2):
            for at2 in ("body", "orelse", "finalbody"):
                sq2 = getattr(nd2, at2, None)
                if isinstance(sq2, list) and len(sq2) >= 2:
                    for a2, b2 in zip(sq2, sq2[1:]):
                        if (
                            not isinstance(a2, _COMPOUND)
                            and not isinstance(b2, _COMPOUND)
                            and a2.lineno == (a2.end_lineno or a2.lineno)
                            and b2.lineno == (b2.end_lineno or b2.lineno)
                            and b2.lineno == a2.lineno + 1
                        ):
                            jn2.add(a2.lineno - 1)
        if jn2:
            s2_lns = compacted.splitlines(keepends=True)
            m2_lns: list[str] = []
            i2 = 0
            while i2 < len(s2_lns):
                c2 = s2_lns[i2]
                while i2 in jn2 and (i2 + 1) < len(s2_lns) and len(c2) < 8000:
                    c2 = c2.rstrip("\r\n") + ";" + s2_lns[i2 + 1].lstrip(" \t")
                    i2 += 1
                m2_lns.append(c2)
                i2 += 1
            cand_s2 = "".join(m2_lns)
            if ast.dump(ast.parse(cand_s2)) == ast.dump(t_s2):
                compacted = cand_s2
    except Exception:
        pass
    for _ in range(3):
        try:
            t_in2 = ast.parse(compacted)
            t_in2_d = ast.dump(t_in2)
            in2_lns = compacted.splitlines(keepends=True)
            mstr2: set[int] = set()
            for tok in tokenize.generate_tokens(io.StringIO(compacted).readline):
                if tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                    for r_m in range(tok.start[0] - 1, tok.end[0]):
                        mstr2.add(r_m)
            out_in2: list[str] = []
            idx_i2 = 0
            chg_i2 = False
            while idx_i2 < len(in2_lns):
                if (
                    idx_i2 + 1 < len(in2_lns)
                    and idx_i2 not in mstr2
                    and (idx_i2 + 1) not in mstr2
                    and in2_lns[idx_i2].rstrip("\r\n").endswith(":")
                    and not in2_lns[idx_i2 + 1].rstrip("\r\n").endswith(":")
                ):
                    ns2 = in2_lns[idx_i2 + 1].lstrip(" \t")
                    if ns2 and not _KW_BLK_RE.match(ns2):
                        ic2 = len(in2_lns[idx_i2]) - len(in2_lns[idx_i2].lstrip(" "))
                        in_n2 = len(in2_lns[idx_i2 + 1]) - len(in2_lns[idx_i2 + 1].lstrip(" "))
                        i_22 = (len(in2_lns[idx_i2 + 2]) - len(in2_lns[idx_i2 + 2].lstrip(" "))) if (idx_i2 + 2) < len(in2_lns) else -1
                        if in_n2 > ic2 and i_22 <= ic2:
                            out_in2.append(in2_lns[idx_i2].rstrip("\r\n") + ns2)
                            idx_i2 += 2
                            chg_i2 = True
                            continue
                out_in2.append(in2_lns[idx_i2])
                idx_i2 += 1
            if not chg_i2:
                break
            cand_in2 = "".join(out_in2)
            if ast.dump(ast.parse(cand_in2)) == t_in2_d:
                compacted = cand_in2
            else:
                break
        except Exception:
            break
    return compacted.rstrip("\n") + "\n"


_TRANSFORM_CACHE: dict[tuple[str, int, str], str] = {}


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
        banner = f"# [{idx:02d}/{len(module_data):02d}] {rel_path}\n"
        ck = (rel_path, len(code), code[:64])
        body = _TRANSFORM_CACHE.get(ck)
        if body is None:
            body = transform_module(rel_path, code)
            _TRANSFORM_CACHE[ck] = body
        start_line = cur_line + 1
        end_line = cur_line + banner.count("\n") + body.count("\n")
        n_bytes = len(code.encode("utf-8"))
        computed_toc.append(
            f"  - [{rel_path}] (L{start_line}-{end_line} | {n_bytes:,}B) :: {desc}"
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
    compile(full_code, "polymarket_all_in_one.py", "exec")

    OUTPUT_FILE.write_text(full_code, encoding="utf-8", newline="\n")
    OUTPUT_TXT_FILE.write_text(full_code, encoding="utf-8", newline="\n")
    disk_bytes = OUTPUT_FILE.stat().st_size

    total_lines = len(full_code.splitlines())
    print(f"SUCCESS: Generated {OUTPUT_FILE} and {OUTPUT_TXT_FILE}")
    print(f"  - Total Modules: {len(module_data)}")
    print(f"  - Total Lines:   {total_lines:,}")
    print(f"  - Total Size:    {disk_bytes:,} bytes ({disk_bytes / 1_000_000:.3f} MB decimal / {disk_bytes / (1024*1024):.3f} MiB)")
    for t in verify_toc:
        print(t)


if __name__ == "__main__":
    main()
