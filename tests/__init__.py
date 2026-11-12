"""
Stdlib-only test runner compatibility bootstrap for Dominus `tests/`.

Ensures `python -m unittest discover -s tests -p "test_*.py"` and individual test modules
import cleanly under minimal stdlib interpreters (e.g., LibreOffice Python 3.12 on Windows)
when optional third-party libraries (`pytest`, `numpy`, `pandas`, `urllib3`, `httpx`, `requests`,
`aiohttp`, `dotenv`, `py_clob_client_v2`) are not installed. When real packages are installed,
this module is a 100% no-op for those packages.
"""

from __future__ import annotations

import contextlib
import math
from pathlib import Path
import sys
import types
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _install_optional_stdlib_test_shims() -> None:
    # 1. dotenv
    try:
        __import__("dotenv")
    except ModuleNotFoundError:
        m_dotenv = types.ModuleType("dotenv")
        m_dotenv.load_dotenv = lambda *_a, **_kw: False  # type: ignore[attr-defined]
        sys.modules["dotenv"] = m_dotenv

    # 2. urllib3 & urllib3.connection
    try:
        __import__("urllib3")
    except ModuleNotFoundError:
        m_u3 = types.ModuleType("urllib3")
        m_u3_conn = types.ModuleType("urllib3.connection")
        m_u3_conn.HTTPConnection = type("HTTPConnection", (), {"default_socket_options": []})  # type: ignore[attr-defined]
        m_u3.connection = m_u3_conn  # type: ignore[attr-defined]
        sys.modules["urllib3"] = m_u3
        sys.modules["urllib3.connection"] = m_u3_conn

    # 3. requests
    try:
        __import__("requests")
    except ModuleNotFoundError:
        m_req = types.ModuleType("requests")
        m_req.Session = object  # type: ignore[attr-defined]
        m_req.RequestException = Exception  # type: ignore[attr-defined]
        m_req.HTTPError = Exception  # type: ignore[attr-defined]
        m_req.Timeout = TimeoutError  # type: ignore[attr-defined]
        m_req.get = None  # type: ignore[attr-defined]
        m_req.post = None  # type: ignore[attr-defined]
        sys.modules["requests"] = m_req

    # 4. httpx
    try:
        __import__("httpx")
    except ModuleNotFoundError:
        m_httpx = types.ModuleType("httpx")
        m_httpx.Client = object  # type: ignore[attr-defined]
        m_httpx.AsyncClient = object  # type: ignore[attr-defined]
        m_httpx.Response = object  # type: ignore[attr-defined]
        m_httpx.Limits = lambda **kw: kw  # type: ignore[attr-defined]
        m_httpx.HTTPTransport = lambda **kw: kw  # type: ignore[attr-defined]
        m_httpx.HTTPError = Exception  # type: ignore[attr-defined]
        m_httpx.ConnectError = ConnectionError  # type: ignore[attr-defined]
        m_httpx.ConnectTimeout = TimeoutError  # type: ignore[attr-defined]
        m_httpx.PoolTimeout = TimeoutError  # type: ignore[attr-defined]
        sys.modules["httpx"] = m_httpx

    # 5. aiohttp
    try:
        m_aio = __import__("aiohttp")
        if not hasattr(m_aio, "ClientTimeout"):
            m_aio.ClientTimeout = lambda **kw: kw  # type: ignore[attr-defined]
            m_aio.ClientWSTimeout = lambda **kw: kw  # type: ignore[attr-defined]
            m_aio.TCPConnector = lambda **kw: kw  # type: ignore[attr-defined]
        if getattr(m_aio, "ClientSession", None) is object:
            m_aio.ClientSession = lambda *_a, **_kw: types.SimpleNamespace(close=lambda: None)  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        m_aio = types.ModuleType("aiohttp")
        m_aio.ClientSession = lambda *_a, **_kw: types.SimpleNamespace(close=lambda: None)  # type: ignore[attr-defined]
        m_aio.ClientTimeout = lambda **kw: kw  # type: ignore[attr-defined]
        m_aio.ClientWSTimeout = lambda **kw: kw  # type: ignore[attr-defined]
        m_aio.TCPConnector = lambda **kw: kw  # type: ignore[attr-defined]
        m_aio.WSMsgType = types.SimpleNamespace(TEXT=1, BINARY=2, CLOSED=8, CLOSING=9, ERROR=256)  # type: ignore[attr-defined]
        sys.modules["aiohttp"] = m_aio

    # 6. pytest decorator & helper shim
    try:
        __import__("pytest")
    except ModuleNotFoundError:
        m_pt = types.ModuleType("pytest")

        def _fixture(*args: Any, **_kwargs: Any) -> Any:
            if len(args) == 1 and callable(args[0]):
                return args[0]
            return lambda fn: fn

        class _MarkGen:
            def __getattr__(self, _name: str) -> Any:
                def _dec(*args: Any, **_kwargs: Any) -> Any:
                    if len(args) == 1 and callable(args[0]):
                        return args[0]
                    return lambda fn: fn

                return _dec

        @contextlib.contextmanager
        def _raises(exc_type: Any, match: Optional[str] = None) -> Any:
            info = types.SimpleNamespace(value=None)
            try:
                yield info
            except exc_type as exc:
                info.value = exc
                if match is not None:
                    import re

                    if not re.search(match, str(exc)):
                        raise AssertionError(f"Regex {match!r} did not match {str(exc)!r}") from exc
            else:
                raise AssertionError(f"DID NOT RAISE {exc_type}")

        class _Approx:
            def __init__(self, expected: float, rel: float = 1e-6, abs_tol: float = 1e-12) -> None:
                self.expected = float(expected)
                self.rel = float(rel)
                self.abs_tol = float(abs_tol)

            def __eq__(self, actual: object) -> bool:
                try:
                    return math.isclose(float(actual), self.expected, rel_tol=self.rel, abs_tol=self.abs_tol)  # type: ignore[arg-type]
                except Exception:
                    return False

        def _skip(msg: str = "", **_kwargs: Any) -> Any:
            import unittest

            raise unittest.SkipTest(msg)

        def _importorskip(modname: str, minversion: Any = None, reason: Optional[str] = None) -> Any:
            import unittest

            try:
                return __import__(modname, fromlist=["*"])
            except ImportError as exc:
                raise unittest.SkipTest(reason or f"could not import {modname!r}: {exc}") from exc

        m_pt.fixture = _fixture  # type: ignore[attr-defined]
        m_pt.mark = _MarkGen()  # type: ignore[attr-defined]
        m_pt.raises = _raises  # type: ignore[attr-defined]
        m_pt.approx = lambda val, rel=1e-6, abs=1e-12: _Approx(val, rel=rel, abs_tol=abs)  # type: ignore[attr-defined]
        m_pt.skip = _skip  # type: ignore[attr-defined]
        m_pt.importorskip = _importorskip  # type: ignore[attr-defined]
        m_pt.fail = lambda msg="": (_ for _ in ()).throw(AssertionError(msg))  # type: ignore[attr-defined]
        sys.modules["pytest"] = m_pt

    # 7. numpy / pandas lightweight import shims for stdlib discovery
    for _sci_mod in ("numpy", "pandas"):
        try:
            __import__(_sci_mod)
        except ModuleNotFoundError:
            m_sci = types.ModuleType(_sci_mod)
            if _sci_mod == "numpy":
                m_sci.ndarray = list  # type: ignore[attr-defined]
                m_sci.float64 = float  # type: ignore[attr-defined]
                m_sci.int64 = int  # type: ignore[attr-defined]
                m_sci.nan = float("nan")  # type: ignore[attr-defined]
                m_sci.inf = float("inf")  # type: ignore[attr-defined]
                m_sci.isnan = math.isnan  # type: ignore[attr-defined]
                m_sci.isfinite = math.isfinite  # type: ignore[attr-defined]
                m_sci.sqrt = math.sqrt  # type: ignore[attr-defined]
                m_sci.exp = math.exp  # type: ignore[attr-defined]
                m_sci.log = math.log  # type: ignore[attr-defined]
                m_sci.array = lambda x, **_kw: list(x) if hasattr(x, "__iter__") else [x]  # type: ignore[attr-defined]
                m_sci.zeros = lambda n, **_kw: [0.0] * (n if isinstance(n, int) else n[0])  # type: ignore[attr-defined]
                m_sci.ones = lambda n, **_kw: [1.0] * (n if isinstance(n, int) else n[0])  # type: ignore[attr-defined]
            sys.modules[_sci_mod] = m_sci

    # 8. Trigger polymarket_live_executor import so py_clob_client_v2 fallback types are registered
    try:
        import src.polymarket_research.polymarket_live_executor  # noqa: F401
    except Exception:
        pass


_install_optional_stdlib_test_shims()
