import json
import threading
import time

from src.polymarket_research import latency_trace as lt
from src.polymarket_research.polymarket_live_executor import _HOT_DISPATCH_ACTIVE


def test_active_counter_overlapping_dispatches():
    c = lt.ActiveCounter()
    c.enter()
    c.enter()
    assert c.is_set()
    c.leave()  # first finisher must NOT mark the hot path idle
    assert c.is_set() and c.count == 1
    c.leave()
    assert not c.is_set()
    c.leave()  # never goes negative
    assert c.count == 0


def test_active_counter_threadsafe():
    c = lt.ActiveCounter()

    def work():
        for _ in range(1000):
            c.enter()
            c.leave()

    ts = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert c.count == 0


def test_executor_uses_refcounted_flag():
    assert hasattr(_HOT_DISPATCH_ACTIVE, "enter") and hasattr(_HOT_DISPATCH_ACTIVE, "leave")


def test_trace_emit_writes_jsonl(tmp_path, monkeypatch):
    out = tmp_path / "trace.jsonl"
    monkeypatch.setenv("PM_LATENCY_TRACE_FILE", str(out))
    monkeypatch.setenv("PM_LATENCY_TRACE", "1")
    t = lt.LatencyTrace(sleeve="TEST", asset="BTC")
    t.stamp("trigger_consumed")
    time.sleep(0.002)
    t.stamp("dispatch_call")
    t.emit(outcome="posted", sign_ms=1.5)
    lt.flush(5.0)
    deadline = time.time() + 5
    while not out.exists() and time.time() < deadline:
        time.sleep(0.05)
    rec = json.loads(out.read_text().strip().splitlines()[0])
    assert rec["sleeve"] == "TEST" and rec["outcome"] == "posted"
    assert rec["stamps_rel_ms"]["dispatch_call"] > rec["stamps_rel_ms"]["trigger_consumed"]
    assert rec["attempt"] == 0


def test_trace_disabled_is_noop(tmp_path, monkeypatch):
    out = tmp_path / "off.jsonl"
    monkeypatch.setenv("PM_LATENCY_TRACE_FILE", str(out))
    monkeypatch.setenv("PM_LATENCY_TRACE", "0")
    lt.LatencyTrace(a=1).emit()
    time.sleep(0.4)
    assert not out.exists()


def test_emit_never_raises_on_unserialisable():
    class Weird:
        def __str__(self):
            raise RuntimeError("boom")

    lt.LatencyTrace(x=Weird()).emit()  # must not propagate
