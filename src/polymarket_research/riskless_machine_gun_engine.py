#!/usr/bin/env python3
"""
Polymarket Riskless Machine-Gun Engine (v5.5)
=============================================
Standalone high-velocity riskless execution primitives kept outside the <1MB single-file
bundle (`polymarket_all_in_one.py`) so core production daemons stay compact while gaining:

  1. Phase 0 Plumbing & Safety:
     - `PolygonRpcFailoverPool` / `get_fast_polygon_web3`: latency-ranked multi-RPC failover.
     - `resolve_authoritative_exit_fee_rate`: live CLOB `get_token_fee_rate` cache population.
     - `is_locked_arbitrage_box_leg`: hard anti-box-breaking guard on paired 2-leg boxes.
     - `is_soc2_exhaustive_lattice_safe` & `is_sports_dead_ball_safe`: structural safety filters.
  2. Phase 1 Sub-6s Capital Recycling & Multi-Clip Unlocks:
     - `release_recycled_box_dedupe_keys`: unlocks `_seen_d1_box_keys` on merge/unwind/convert.
     - `compute_dynamic_box_unwind_hurdle`: spot-aware corridor EV replacing static `$1.060` wall.
     - `evaluate_cross_condition_complement_merge` & `execute_cross_condition_complement_merge`:
       buys `opp_a + opp_b` via atomic 2-leg FOK and merges BOTH conditions into `$2.00/pair` cash.
  3. Phase 2 Multi-Leg Batch & NegRisk `NR3` Synthetic All-YES Overround:
     - `batch_post_fok_orders`: simultaneous `PostOrdersV2` (`/orders`, up to 15 legs/batch).
     - `wait_for_erc1155_delivery`: pre-convert/pre-sell on-chain settlement barrier.
     - `attempt_onchain_split_position`: atomic `approve + splitPosition` (`pUSD` / `USDC.e`).
     - `detect_nr3_synthetic_all_yes_overround` & `execute_nr3_synthetic_all_yes_overround`:
       single atomic Relayer V2 / Safe 3-call tx (`2x splitPosition + convertPositions(0b11)`)
       minting all `N <= 15` YES tokens for `$1.00 * Q` net cost -> batch SELL into `sum_bids > $1.00`.
  4. Phase 3 `$12` Pre-Split Overround & Maker-Rebate Machine Gun:
     - `compute_crypto_maker_rebate_per_share` & `evaluate_d1_maker_rebate_anchor` (`20%` rebate + `<350ms` spot guard).
     - `PreSplitInventoryGun`: `$12` revolving `UP + DOWN` complete-set inventory on active `BTC 15m/5m`
       candles (`<40ms` overround sweep + Chainlink-anchored dual `postOnly` maker asks + `TTE <= 75s` merge).
"""

from __future__ import annotations

import asyncio
import collections
import logging
import math
import os
import threading
import time
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

try:
    import requests
except ImportError:  # pragma: no cover - stdlib fallback for minimal Python runtimes
    import json as _stdlib_json
    import urllib.parse as _urllib_parse
    import urllib.request as _urllib_request

    class _StdlibHttpResponse:
        def __init__(self, status_code: int, raw_bytes: bytes) -> None:
            self.status_code = int(status_code)
            self._raw = raw_bytes
            self.text = raw_bytes.decode("utf-8", errors="replace")

        def json(self) -> Any:
            return _stdlib_json.loads(self.text)

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}: {self.text[:200]}")

    class _StdlibRequestsShim:
        @staticmethod
        def get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: float = 5.0) -> _StdlibHttpResponse:
            full_url = f"{url}?{_urllib_parse.urlencode(params)}" if params else url
            req = _urllib_request.Request(full_url, headers=dict(headers or {}), method="GET")
            with _urllib_request.urlopen(req, timeout=timeout) as resp:
                return _StdlibHttpResponse(getattr(resp, "status", 200), resp.read())

        @staticmethod
        def post(url: str, json: Any = None, headers: Optional[Dict[str, str]] = None, timeout: float = 5.0) -> _StdlibHttpResponse:
            hdrs = {"Content-Type": "application/json", **dict(headers or {})}
            body = _stdlib_json.dumps(json).encode("utf-8") if json is not None else b""
            req = _urllib_request.Request(url, data=body, headers=hdrs, method="POST")
            with _urllib_request.urlopen(req, timeout=timeout) as resp:
                return _StdlibHttpResponse(getattr(resp, "status", 200), resp.read())

    requests = _StdlibRequestsShim()  # type: ignore[assignment]

logger = logging.getLogger("RisklessMachineGun")

PUSD_ADDRESS = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
USDC_E_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
CTF_ADAPTER_V2 = "0xAdA100Db00Ca00073811820692005400218FcE1f"
NEG_RISK_ADAPTER_V1 = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
NEG_RISK_ADAPTER_V2 = "0xadA2005600Dec949baf300f4C6120000bDB6eAab"
POLYMARKET_V2_COLLATERAL_WRAPPER = "0x93070a847eFEf7F70739046a929d47a521f5b8ee"
V2_ADAPTER_REDEMPTION_TOPIC0 = "0x1daec0b1f629de29b749a189499f43104a80df46a9f34d9ccf73aa59b85fc0c0"
MAX_UINT256_HEX = "f" * 64

DEFAULT_POLYGON_RPC_POOL: Tuple[str, ...] = (
    "https://polygon-bor-rpc.publicnode.com",
    "https://1rpc.io/matic",
    "https://polygon.drpc.org",
    "https://rpc.ankr.com/polygon",
)

CRYPTO_MAKER_REBATE_SHARE = 0.20  # Polymarket crypto maker rebate = 20% of taker fee curve


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))


# ============================================================================
# 1. MULTI-ENDPOINT POLYGON RPC LATENCY-RANKED FAILOVER POOL
# ============================================================================


class PolygonRpcFailoverPool:
    """Thread-safe latency-ranked Polygon RPC selector with automatic failure demotion."""

    def __init__(
        self,
        endpoints: Optional[Sequence[str]] = None,
        *,
        probe_ttl_sec: float = 60.0,
        demote_sec: float = 45.0,
    ) -> None:
        self._base_endpoints = [str(u).strip() for u in (endpoints or DEFAULT_POLYGON_RPC_POOL) if str(u).strip()]
        self._probe_ttl_sec = float(probe_ttl_sec)
        self._demote_sec = float(demote_sec)
        self._lock = threading.Lock()
        self._latencies_ms: Dict[str, float] = {}
        self._demoted_until: Dict[str, float] = {}
        self._last_probe_ts: float = 0.0

    def candidate_urls(self) -> List[str]:
        env_url = (os.getenv("POLYGON_RPC_URL") or "").strip()
        urls: List[str] = []
        if env_url:
            urls.append(env_url)
        for u in self._base_endpoints:
            if u not in urls:
                urls.append(u)
        return urls

    def report_failure(self, url: str) -> None:
        if not url:
            return
        with self._lock:
            self._demoted_until[str(url)] = time.monotonic() + self._demote_sec

    def _probe_once(self, urls: List[str]) -> None:
        payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
        measured: Dict[str, float] = {}
        for u in urls:
            t0 = time.perf_counter()
            try:
                resp = requests.post(u, json=payload, timeout=1.5)
                if resp.status_code == 200 and isinstance(resp.json().get("result"), str):
                    measured[u] = round((time.perf_counter() - t0) * 1000.0, 2)
                else:
                    measured[u] = 9999.0
            except Exception:
                measured[u] = 9999.0
        with self._lock:
            self._latencies_ms.update(measured)
            self._last_probe_ts = time.monotonic()

    def select_best_url(self, *, allow_probe: bool = True) -> str:
        urls = self.candidate_urls()
        if not urls:
            return DEFAULT_POLYGON_RPC_POOL[0]
        env_explicit = (os.getenv("POLYGON_RPC_URL") or "").strip()
        now_m = time.monotonic()
        with self._lock:
            demoted = dict(self._demoted_until)
            lats = dict(self._latencies_ms)
            need_probe = allow_probe and (not env_explicit) and (now_m - self._last_probe_ts) >= self._probe_ttl_sec
        if env_explicit and now_m >= float(demoted.get(env_explicit, 0.0) or 0.0):
            return env_explicit
        if need_probe and len(urls) > 1:
            try:
                self._probe_once(urls)
                with self._lock:
                    lats = dict(self._latencies_ms)
            except Exception:
                pass
        healthy = [u for u in urls if now_m >= float(demoted.get(u, 0.0) or 0.0)]
        pool = healthy if healthy else urls
        pool.sort(key=lambda u: float(lats.get(u, 500.0)))
        return pool[0]

    def ordered_failover_urls(self) -> List[str]:
        best = self.select_best_url(allow_probe=False)
        rest = [u for u in self.candidate_urls() if u != best]
        now_m = time.monotonic()
        with self._lock:
            demoted = dict(self._demoted_until)
            lats = dict(self._latencies_ms)
        rest.sort(key=lambda u: (now_m < float(demoted.get(u, 0.0) or 0.0), float(lats.get(u, 500.0))))
        return [best] + rest


GLOBAL_POLYGON_RPC_POOL = PolygonRpcFailoverPool()


def get_fast_polygon_web3(timeout: float = 5.0, *, allow_probe: bool = False) -> Any:
    from web3 import Web3

    url = GLOBAL_POLYGON_RPC_POOL.select_best_url(allow_probe=allow_probe)
    w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": float(timeout)}))
    setattr(w3, "_dominus_rpc_url", url)
    return w3


# ============================================================================
# 2. PHASE 0 SAFETY & FEE PLUMBING GUARDS
# ============================================================================


def resolve_authoritative_exit_fee_rate(executor: Any, pos: Dict[str, Any]) -> float:
    """
    Resolves exact CLOB exit taker fee rate for `pos`, querying `executor.get_token_fee_rate(tok)`
    (or `get_market_fee_rate(tok)`) live on cache miss so `CM_B3` / sports / crypto positions never under-estimate exit fees.
    """
    tok = str(pos.get("token_id") or "").strip()
    for cache_attr in ("_fee_cache", "_fee_rate_cache"):
        fc = getattr(executor, cache_attr, None)
        if isinstance(fc, dict) and tok and tok in fc:
            cached = fc[tok]
            val = cached[0] if isinstance(cached, (tuple, list)) else cached
            return max(0.0, float(val or 0.0))
    if pos.get("market_fee_rate") is not None:
        return max(0.0, float(pos["market_fee_rate"]))
    slv_chk = str(pos.get("sleeve") or "")
    if (
        pos.get("fee_rate_applied") is not None
        and float(pos.get("fee_rate_applied") or 0.0) == 0.0
        and slv_chk in {
            "LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX",
            "COND1_MACRO_PARTITION_BOX",
            "FED1_CENTRAL_BANK_LP_BOX",
            "C1_BINARY_COMPLETE_SET",
        }
    ):
        return 0.0
    fee_fn = getattr(executor, "get_token_fee_rate", None) or getattr(executor, "get_market_fee_rate", None)
    fee_params_fn = getattr(executor, "get_market_fee_params", None)
    cid = str(pos.get("condition_id") or pos.get("market_id") or "").strip()
    is_live_exec = (
        executor is not None
        and not bool(getattr(executor, "dry_run", True))
        and bool(getattr(executor, "is_authenticated", True))
        and getattr(executor, "_mock_children", None) is None
        and len(tok) >= 20
        and tok.isdigit()
        and (callable(fee_fn) or callable(fee_params_fn))
    )
    if is_live_exec:
        try:
            fetched = fee_fn(tok) if callable(fee_fn) else fee_params_fn(cid or tok, token_id=tok)
            raw_v = fetched[0] if isinstance(fetched, (tuple, list)) and fetched else fetched
            if isinstance(raw_v, (int, float)) and not isinstance(raw_v, bool) and math.isfinite(float(raw_v)):
                rate_f = max(0.0, float(raw_v))
                pos["market_fee_rate"] = rate_f
                pos["fee_rate_applied"] = rate_f
                return rate_f
        except Exception:
            pass
    fr = pos.get("fee_rate_applied")
    if fr is None or float(fr) > 0.0:
        return 0.07 if fr is None else max(0.0, float(fr))
    slv = str(pos.get("sleeve") or "")
    return 0.07 if (slv.startswith("SLEEVE_") or pos.get("box_type") == "DOMINANCE_MAKER_ANCHOR") else 0.0


def is_locked_arbitrage_box_leg(
    pos: Dict[str, Any], active_positions: Optional[Dict[str, Dict[str, Any]]] = None
) -> bool:
    """
    Returns True if `pos` is an intact leg of a paired locked arbitrage box whose partner leg
    is still active (or when `is_locked_arbitrage_box` is explicitly armed without residual demotion).
    Used to hard-block single-leg stepdowns, `< $0.99` maker exits, and box-breaking salvage stops.
    """
    if not isinstance(pos, dict) or pos.get("is_legged_out_residual"):
        return False
    if not (pos.get("is_dominance_box") or pos.get("is_locked_arbitrage_box")):
        return False
    partner_tid = str(pos.get("box_partner_trade_id") or "").strip()
    if not partner_tid:
        return bool(pos.get("is_locked_arbitrage_box"))
    if active_positions is None:
        return True
    partner = active_positions.get(partner_tid)
    return isinstance(partner, dict) and not bool(partner.get("is_legged_out_residual"))


def is_soc2_exhaustive_lattice_safe(cand: Dict[str, Any]) -> bool:
    """
    Quarantines `SOC2_EXACT_SCORE_2D_LATTICE` from live execution unless the candidate carries
    explicit mathematical proof that the 2D score partition is 100% exhaustive (`exhaustive_partition_verified=True`
    and `has_any_other_bucket_covered` not False), preventing non-exhaustive Exact Score losses.
    """
    slv = str(cand.get("sleeve_source") or cand.get("sleeve") or "").strip().upper()
    if slv != "SOC2_EXACT_SCORE_2D_LATTICE":
        return True
    return bool(cand.get("exhaustive_partition_verified") is True and cand.get("has_any_other_bucket_covered", True) is not False)


def is_sports_dead_ball_safe(cand: Dict[str, Any], now_ts: Optional[float] = None) -> bool:
    """
    Blocks live-ball sports corridor / dominance boxes during active open play unless:
      - Pre-game (`now_ts <= game_start_ts - 180s`), OR
      - Confirmed dead-ball / halftime / intermission / post-final (`is_dead_ball=True` or `game_phase in {...}`), OR
      - Deterministic irreversible clinch (`p_model >= 0.999` or `SINGLE_LEG_LOCK`).
    Candidates without live-play flags (e.g. pre-match schedules without `in_play=True`) pass cleanly.
    """
    now = float(now_ts if now_ts is not None else time.time())
    if not bool(cand.get("in_play") or cand.get("is_live_in_play") or cand.get("game_in_progress")):
        kickoff = float(cand.get("game_start_ts") or cand.get("kickoff_ts") or 0.0)
        if kickoff > 0.0 and now > kickoff - 180.0 and cand.get("is_dead_ball") is False:
            return False
        return True
    if bool(cand.get("is_dead_ball")):
        return True
    phase = str(cand.get("game_phase") or cand.get("period_status") or "").strip().upper()
    if phase in {"PREGAME", "HALFTIME", "END_OF_PERIOD", "INTERMISSION", "TIMEOUT", "FINAL", "POSTGAME", "CLINCHED"}:
        return True
    if str(cand.get("box_type") or "").upper() in {"SINGLE_LEG_LOCK", "SINGLE_LEG_MAKER_LOCK"}:
        return True
    if float(cand.get("p_model") or 0.0) >= 0.999:
        return True
    return False


# ============================================================================
# 3. PHASE 1 SUB-6S CAPITAL RECYCLING & CROSS-CONDITION COMPLEMENT MERGE
# ============================================================================


def release_recycled_box_dedupe_keys(
    harvester: Any,
    pos: Optional[Dict[str, Any]],
    partner: Optional[Dict[str, Any]] = None,
    *,
    extra_keys: Sequence[str] = (),
    cooldown_sec: float = 2.0,
) -> List[str]:
    """
    Clears `_seen_d1_box_keys` for a pair/slate immediately after pre-expiry capital recycling
    (on-chain merge, cross-condition complement merge, atomic overround unwind, or NegRisk convert)
    and arms a short `cooldown_sec` (`2.0s`) RPC settlement sync buffer so multi-clip reloading fires
    repeatedly on the same market!
    """
    seen = getattr(harvester, "_seen_d1_box_keys", None)
    seen_order = getattr(harvester, "_seen_d1_box_order", None)
    retry_cd = getattr(harvester, "_d1_retry_cooldown_until", None)
    keys: List[str] = []
    for obj in (pos, partner):
        if isinstance(obj, dict):
            for field in ("dedupe_key", "pair_dedupe_key"):
                v = str(obj.get(field) or "").strip()
                if v and v not in keys:
                    keys.append(v)
    for k_ex in extra_keys:
        v = str(k_ex or "").strip()
        if v and v not in keys:
            keys.append(v)
    now = time.time()
    released: List[str] = []
    for k in keys:
        if isinstance(seen, set) and k in seen:
            seen.discard(k)
            released.append(k)
        if isinstance(seen_order, dict):
            seen_order.pop(k, None)
        elif isinstance(seen_order, collections.deque):
            while k in seen_order:
                seen_order.remove(k)
        if isinstance(retry_cd, dict) and cooldown_sec > 0.0:
            retry_cd[k] = max(float(retry_cd.get(k, 0.0) or 0.0), now + float(cooldown_sec))
    return released


def compute_corridor_double_payout_prob(
    k_low: float,
    k_high: float,
    current_spot: Optional[float],
    tte_rem: float,
    sigma_15m: float = 0.0025,
) -> float:
    """Computes probability `P(k_low < S_T < k_high)` that a cross-strike box hits its `$2.00` middle corridor."""
    lo = min(float(k_low or 0.0), float(k_high or 0.0))
    hi = max(float(k_low or 0.0), float(k_high or 0.0))
    if lo <= 0.0 or hi <= lo * (1.0 + 1e-7):
        return 0.0
    if current_spot is None or not math.isfinite(float(current_spot)) or float(current_spot) <= 0.0:
        return -1.0
    s = float(current_spot)
    tau = max(5.0, float(tte_rem)) / 900.0
    vol_t = max(0.00035, max(0.0008, float(sigma_15m or 0.0025)) * math.sqrt(tau) * 1.20)
    z_hi = math.log(hi / s) / vol_t
    z_lo = math.log(lo / s) / vol_t
    return max(0.0, min(0.95, _norm_cdf(z_hi) - _norm_cdf(z_lo)))


def compute_dynamic_box_unwind_hurdle(
    pos: Dict[str, Any],
    partner: Dict[str, Any],
    tte_rem: float,
    current_spot: Optional[float] = None,
) -> float:
    """
    Dynamic EV-optimal bid-sum hurdle for `_try_atomic_box_overround_unwind`:
      - Zero-corridor boxes (`COMPLETE_SET`, `NEGRISK_2LEG`, `MACRO_DOMINANCE`, `k_low == k_high`, etc.):
        `max(1.002, box_cost_net + 0.008)`.
      - Corridor boxes with live spot `S`:
        `max(1.002, box_cost_net + 0.006, round(1.0 + p_corridor + 0.003, 5))` — drops from `$1.060`
        down to `$1.003-$1.005` as soon as spot moves outside `[k_low, k_high]`, while preserving full
        middle EV when spot sits inside `[k_low, k_high]`.
      - Corridor boxes without live spot: conservative fallback `max(1.060, box_cost_net + 0.060)`.
    """
    box_unit = float(pos.get("box_cost_net") or partner.get("box_cost_net") or 0.985)
    k_lo = float(pos.get("box_k_low") or pos.get("k_low") or 0.0)
    k_hi = float(pos.get("box_k_high") or pos.get("k_high") or 0.0)
    sl_u = str(pos.get("sleeve") or "").strip().upper()
    zero_corridor = (
        pos.get("has_double_payout_corridor") is False
        or str(pos.get("box_type") or "") in {"COMPLETE_SET", "NEGRISK_2LEG", "NEGRISK_CROSS", "MACRO_DOMINANCE"}
        or sl_u in {"LP1_CROSS_MARKET_PARTITION_IMPLICATION_BOX", "COND1_MACRO_PARTITION_BOX", "FED1_CENTRAL_BANK_LP_BOX"}
        or abs(k_hi - k_lo) < 1e-6
        or float(tte_rem) > 3600.0
    )
    if zero_corridor:
        return max(1.002, round(box_unit + 0.008, 5))
    sigma_15m = float(
        pos.get("candle_sigma")
        or (float(pos["sigma_1h"]) * 0.5 if pos.get("sigma_1h") else (0.0025 if str(pos.get("asset") or "").upper() == "BTC" else 0.0035))
    )
    p_corr = compute_corridor_double_payout_prob(k_lo, k_hi, current_spot, tte_rem, sigma_15m=sigma_15m)
    if p_corr < 0.0:
        return max(1.060, round(box_unit + 0.060, 5))
    return max(1.002, round(box_unit + 0.006, 5), round(1.0 + p_corr + 0.003, 5))


def _walk_ask_vwap_and_limit(
    asks: Sequence[Any], req_net_shares: float, fee_rate: float = 0.0, fee_exponent: float = 1.0
) -> Optional[Dict[str, float]]:
    norm: List[Tuple[float, float]] = []
    for lv in asks or ():
        px = float(lv["price"] if isinstance(lv, dict) else lv[0])
        sz = float(lv["size"] if isinstance(lv, dict) else lv[1])
        if 0.001 <= px <= 0.999 and sz > 0.0:
            norm.append((px, sz))
    norm.sort(key=lambda r: r[0])
    if not norm:
        return None
    top_px = norm[0][0]
    fee_ps_est = fee_rate * ((top_px * (1.0 - top_px)) ** fee_exponent) if fee_rate > 0.0 else 0.0
    h_est = min(0.25, max(0.0, fee_ps_est / max(top_px, 1e-6))) if fee_rate > 0.0 else 0.0
    req_gross = req_net_shares / max(1.0 - h_est, 1e-6)
    cum = 0.0
    cost = 0.0
    lim_px = top_px
    for px, sz in norm:
        take = min(sz, req_gross - cum)
        cost += take * px
        lim_px = px
        cum += take
        if cum >= req_gross - 1e-6:
            break
    if cum < req_gross * 1.10 - 1e-6 and sum(s for _, s in norm) < req_gross * 1.10:
        if cum < req_gross - 1e-6:
            return None
    fee_lim = fee_rate * ((lim_px * (1.0 - lim_px)) ** fee_exponent) if fee_rate > 0.0 else 0.0
    h_lim = min(0.25, max(0.0, fee_lim / max(lim_px, 1e-6))) if fee_rate > 0.0 else 0.0
    gross_sh = math.ceil((req_net_shares / max(1.0 - h_lim, 1e-6)) * 100.0 - 1e-9) / 100.0 if h_lim > 0.0 else req_net_shares
    return {
        "limit_price": round(lim_px, 4),
        "vwap_gross": round(cost / max(req_gross, 1e-6), 5),
        "worst_net_cost_per_share": round((gross_sh * lim_px) / max(req_net_shares, 1e-6), 5),
        "gross_shares": float(gross_sh),
    }


def evaluate_cross_condition_complement_merge(
    pos: Dict[str, Any],
    partner: Dict[str, Any],
    bk_opp_a: Optional[Dict[str, Any]],
    bk_opp_b: Optional[Dict[str, Any]],
    pairs: float,
    *,
    tte_rem: float,
    current_spot: Optional[float] = None,
    min_cycle_profit_per_share: float = 0.005,
) -> Optional[Dict[str, Any]]:
    """
    Checks whether buying complement tokens `opp_a` (on `cid_a`) + `opp_b` (on `cid_b`) allows
    merging BOTH conditions immediately into `$2.00/pair` cash at locked profit:
        `box_cost_net + comp_cost_net <= $2.00 - max(min_cycle_profit, p_corridor + 0.003)`
    """
    cid_a = str(pos.get("condition_id") or "").strip()
    cid_b = str(partner.get("condition_id") or "").strip()
    opp_a = str(pos.get("opp_token_id") or "").strip()
    opp_b = str(partner.get("opp_token_id") or "").strip()
    if not (cid_a and cid_b and cid_a.lower() != cid_b.lower() and opp_a and opp_b and opp_a != opp_b):
        return None
    if not isinstance(bk_opp_a, dict) or not isinstance(bk_opp_b, dict) or pairs < 5.0:
        return None
    fr_a = float(pos.get("market_fee_rate") if pos.get("market_fee_rate") is not None else (pos.get("fee_rate_applied") or 0.0))
    fr_b = float(partner.get("market_fee_rate") if partner.get("market_fee_rate") is not None else (partner.get("fee_rate_applied") or 0.0))
    fe_a = float(pos.get("fee_exponent_applied") or 1.0)
    fe_b = float(partner.get("fee_exponent_applied") or 1.0)
    wa = _walk_ask_vwap_and_limit(bk_opp_a.get("asks") or [], pairs, fr_a, fe_a)
    wb = _walk_ask_vwap_and_limit(bk_opp_b.get("asks") or [], pairs, fr_b, fe_b)
    if wa is None or wb is None:
        return None
    box_unit = float(pos.get("box_cost_net") or partner.get("box_cost_net") or 0.985)
    comp_worst = round(wa["worst_net_cost_per_share"] + wb["worst_net_cost_per_share"], 5)
    k_lo = float(pos.get("box_k_low") or pos.get("k_low") or 0.0)
    k_hi = float(pos.get("box_k_high") or pos.get("k_high") or 0.0)
    p_corr = 0.0
    if abs(k_hi - k_lo) > 1e-6 and pos.get("has_double_payout_corridor") is not False:
        p_c = compute_corridor_double_payout_prob(k_lo, k_hi, current_spot, tte_rem)
        p_corr = 0.060 if p_c < 0.0 else p_c
    req_margin = max(float(min_cycle_profit_per_share), p_corr + 0.003)
    max_comp_cap = round(2.0 - box_unit - req_margin, 5)
    if comp_worst > max_comp_cap + 1e-6:
        return None
    return {
        "eligible": True,
        "cid_a": cid_a,
        "cid_b": cid_b,
        "opp_a": opp_a,
        "opp_b": opp_b,
        "pairs": float(pairs),
        "limit_a": wa["limit_price"],
        "limit_b": wb["limit_price"],
        "gross_a": wa["gross_shares"],
        "gross_b": wb["gross_shares"],
        "fee_rate_a": fr_a,
        "fee_rate_b": fr_b,
        "fee_exponent_a": fe_a,
        "fee_exponent_b": fe_b,
        "comp_worst_cost_net": comp_worst,
        "comp_cost_ps": comp_worst,
        "max_comp_cost_net": max_comp_cap,
        "recycle_edge_ps": round(2.0 - box_unit - comp_worst, 5),
        "expected_cycle_profit_usd": round(pairs * (2.0 - box_unit - comp_worst), 4),
    }


async def execute_cross_condition_complement_merge(
    harvester: Any,
    tid_a: str,
    pos: Dict[str, Any],
    tid_b: str,
    partner: Dict[str, Any],
    plan: Dict[str, Any],
    open_oids: Set[str],
    now_ts: float,
) -> bool:
    """
    Executes Cross-Condition Complement-Pair Merge end-to-end:
      1. Cancels any resting exit orders on `pos` & `partner`.
      2. Buys `opp_a + opp_b` via atomic 2-leg FOK (`execute_atomic_dominance_box`, `parallel_dispatch=True`).
      3. Calls `attempt_onchain_complete_set_merge` on BOTH `cid_a` and `cid_b` -> `$2.00/pair` cash.
      4. Closes both legs as `CROSS_CONDITION_COMPLEMENT_MERGED` and unlocks `_seen_d1_box_keys`!
    """
    ex = harvester.executor
    if getattr(harvester, "dry_run", False) or not hasattr(ex, "execute_atomic_dominance_box") or not hasattr(ex, "attempt_onchain_complete_set_merge"):
        return False
    collat = getattr(harvester, "_last_known_collateral", None)
    pairs = float(plan["pairs"])
    est_need = pairs * float(plan["comp_worst_cost_net"])
    if isinstance(collat, (int, float)) and float(collat) < est_need + 0.25:
        return False

    e_oids = [str(lg.get("exit_order_id")) for lg in (pos, partner) if lg.get("exit_order_id")]
    batch_c = await asyncio.to_thread(ex.cancel_orders_batch, e_oids) if len(e_oids) == 2 and hasattr(ex, "cancel_orders_batch") else None
    for lg_tid, lg_p in ((tid_a, pos), (tid_b, partner)):
        e_oid = lg_p.get("exit_order_id")
        if not e_oid:
            continue
        if isinstance(batch_c, dict) and str(e_oid) in batch_c:
            c_r = batch_c[str(e_oid)]
            is_c = bool(getattr(c_r, "is_canceled", False) if not isinstance(c_r, dict) else (c_r.get("is_canceled") or str(e_oid) in (c_r.get("canceled") or [])))
        elif isinstance(batch_c, dict) and ("is_canceled" in batch_c or "canceled" in batch_c):
            is_c = bool(batch_c.get("is_canceled") or str(e_oid) in (batch_c.get("canceled") or []))
        else:
            c_one = await asyncio.to_thread(ex.cancel_order, str(e_oid))
            is_c = bool((c_one or {}).get("is_canceled"))
        s_r = await asyncio.to_thread(ex.get_order_fill_summary, str(e_oid), lg_p.get("token_id"))
        if s_r is not None:
            harvester._record_order_summary(lg_p, s_r, float(lg_p.get("target_exit_price", 0.99) or 0.99), taker=False)
        if not is_c or float(lg_p.get("filled_exit_shares", 0.0) or 0.0) > 0.01:
            return False
        open_oids.discard(str(e_oid))
        ex.release_inventory(reservation_id=str(e_oid))
        lg_p["exit_order_id"] = None
        lg_p["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"

    b_id = str(pos.get("box_id") or f"CC_{int(now_ts)}")
    buy_res = await asyncio.to_thread(
        ex.execute_atomic_dominance_box,
        box_id=f"CCMERGE_{b_id}",
        leg_a_token_id=str(plan["opp_a"]),
        leg_a_label="COMP_A",
        leg_a_limit_price=float(plan["limit_a"]),
        leg_b_token_id=str(plan["opp_b"]),
        leg_b_label="COMP_B",
        leg_b_limit_price=float(plan["limit_b"]),
        shares=pairs,
        leg_a_gross_shares=float(plan["gross_a"]),
        leg_b_gross_shares=float(plan["gross_b"]),
        max_box_cost_net=min(1.15, float(plan["max_comp_cost_net"]) + 0.002),
        leg_a_fee_rate=float(plan["fee_rate_a"]),
        leg_b_fee_rate=float(plan["fee_rate_b"]),
        leg_a_fee_exponent=float(plan["fee_exponent_a"]),
        leg_b_fee_exponent=float(plan["fee_exponent_b"]),
        leg_a_neg_risk=bool(pos.get("neg_risk", False)),
        leg_b_neg_risk=bool(partner.get("neg_risk", False)),
        parallel_dispatch=True,
    )
    if not (buy_res or {}).get("success"):
        await asyncio.to_thread(harvester.save_state)
        return False

    m_sh = float(buy_res.get("net_paired_shares") or buy_res.get("shares") or pairs)
    merge_p = round(min(pairs, m_sh), 2)
    m_a = await asyncio.to_thread(
        ex.attempt_onchain_complete_set_merge, str(plan["cid_a"]), min_pairs=merge_p, max_pairs=merge_p, neg_risk=pos.get("neg_risk")
    )
    m_b = await asyncio.to_thread(
        ex.attempt_onchain_complete_set_merge, str(plan["cid_b"]), min_pairs=merge_p, max_pairs=merge_p, neg_risk=partner.get("neg_risk")
    )
    if not (isinstance(m_a, tuple) and m_a[0] and isinstance(m_b, tuple) and m_b[0]):
        logger.warning(f"[CC-MERGE] Complement legs bought for {b_id}; merge pending next cycle (m_a={m_a}, m_b={m_b}).")
        await asyncio.to_thread(harvester.save_state)
        return False

    leg1_r = buy_res.get("leg_1") or {}
    leg2_r = buy_res.get("leg_2") or {}
    cost_1 = float(leg1_r.get("gross_shares") or m_sh) * float(leg1_r.get("price") or plan["limit_a"])
    cost_2 = float(leg2_r.get("gross_shares") or m_sh) * float(leg2_r.get("price") or plan["limit_b"])
    net_cash_a = round(max(0.01, float(m_a[1]) - cost_1), 4)
    net_cash_b = round(max(0.01, float(m_b[1]) - cost_2), 4)
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus

    for lg_tid, lg_p, tx_m, pairs_m, net_c in (
        (tid_a, pos, str(m_a[0]), float(m_a[1]), net_cash_a),
        (tid_b, partner, str(m_b[0]), float(m_b[1]), net_cash_b),
    ):
        lg_p["merge_tx_hash"] = tx_m
        harvester.record_fill_and_update_position(
            lg_p, f"CCMERGE_{tx_m}_{lg_tid}", pairs_m, net_c, 0.0, cash_is_estimated=False
        )
        if float(lg_p.get("remaining_shares", 0.0) or 0.0) <= 0.05:
            harvester._close_position(lg_tid, lg_p, ExecutionStatus.SETTLED, "CROSS_CONDITION_COMPLEMENT_MERGED", won=True)

    release_recycled_box_dedupe_keys(harvester, pos, partner, cooldown_sec=2.0)
    ex.invalidate_collateral_cache()
    harvester._pending_collateral_refresh = True
    await asyncio.to_thread(harvester.save_state)
    logger.info(f"✓ [CROSS-CONDITION COMPLEMENT MERGED] {b_id}: {merge_p:.2f} pairs -> $2.00/pair cash freed immediately!")
    return True


# ============================================================================
# 4. PHASE 2 MULTI-LEG BATCH CLOB DISPATCH & ATOMIC NR3 SYNTHETIC ALL-YES MINT
# ============================================================================


def batch_post_fok_orders(
    executor: Any,
    signed_orders: Sequence[Any],
    order_type: Any,
    *,
    post_one_fallback: Callable[[Any], Tuple[Any, Optional[Exception]]],
    max_batch_size: int = 15,
) -> List[Tuple[Any, Optional[Exception]]]:
    """
    Dispatches up to `15` signed orders per HTTP request via Polymarket `PostOrdersV2` (`client.post_orders`),
    falling back seamlessly to parallel `post_order` when `client.post_order` is explicitly mocked or `PostOrdersV2Args` is absent.
    """
    orders = list(signed_orders or [])
    if not orders:
        return []
    client = getattr(executor, "client", None)
    custom_single_post = client is not None and "post_order" in getattr(client, "__dict__", {}) and "post_orders" not in getattr(client, "__dict__", {})
    post_orders_args_cls = None
    try:
        from src.polymarket_research.polymarket_live_executor import PostOrdersV2Args as _POA

        post_orders_args_cls = _POA
    except Exception:
        post_orders_args_cls = None

    if (
        client is not None
        and not custom_single_post
        and post_orders_args_cls is not None
        and callable(getattr(client, "post_orders", None))
    ):
        results: List[Tuple[Any, Optional[Exception]]] = []
        for idx in range(0, len(orders), max_batch_size):
            chunk = orders[idx : idx + max_batch_size]
            try:
                batch_args = [post_orders_args_cls(order=sg, orderType=order_type, deferExec=True) for sg in chunk]
                resp = client.post_orders(batch_args, post_only=False, defer_exec=True)
                if isinstance(resp, list) and len(resp) == len(chunk):
                    results.extend((r, None) for r in resp)
                else:
                    err = RuntimeError(f"UNEXPECTED_BATCH_POST_ORDERS_LEN:{type(resp).__name__}")
                    results.extend((None, err) for _ in chunk)
            except Exception as exc_b:
                results.extend((None, exc_b) for _ in chunk)
        return results

    return [post_one_fallback(sg) for sg in orders]


def wait_for_erc1155_delivery(
    executor: Any,
    token_ids: Sequence[str],
    min_shares: float,
    *,
    timeout_sec: float = 3.5,
    poll_sec: float = 0.20,
) -> bool:
    """
    Confirms on-chain ERC-1155 balances >= `min_shares - 0.05` before calling `convertPositions`
    or selling minted shares, preventing Polygon revert when `deferExec=True` settles 0.5-2.0s later.
    """
    if getattr(executor, "dry_run", True) or getattr(executor, "auth_mode", "") not in ("LIVE", "AUTHENTICATED_L2"):
        return True
    toks = [str(t) for t in token_ids if str(t).isdigit() and len(str(t)) >= 20]
    if not toks or not callable(getattr(executor, "get_onchain_erc1155_balance", None)):
        return True
    deadline = time.monotonic() + float(timeout_sec)
    while time.monotonic() < deadline:
        all_ready = True
        for t in toks:
            try:
                b = executor.get_onchain_erc1155_balance(t)
            except Exception:
                b = None
            if b is None:
                return True
            if float(b) < float(min_shares) - 0.05:
                all_ready = False
                break
        if all_ready:
            return True
        time.sleep(float(poll_sec))
    return False


def execute_negrisk_subset_convert_arb_impl(
    executor: Any,
    *,
    convert_id: str,
    neg_risk_market_id: str,
    no_legs: List[Dict[str, Any]],
    shares: float,
    max_no_cost_per_share: float,
    liquid_yes_sells: Optional[List[Dict[str, Any]]] = None,
    fee_bips: int = 0,
    nr_m1_zero_loss_verified: bool = False,
    nr_m1_mode: str = "",
    surviving_yes_legs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Batch `PostOrdersV2` + ERC-1155 delivery barrier implementation for `execute_negrisk_subset_convert_arb`."""
    from src.polymarket_research.polymarket_live_executor import (
        OrderArgsV2,
        OrderType,
        PartialCreateOrderOptions,
        ROUND_CEILING,
        ROUND_FLOOR,
        _HOT_DISPATCH_ACTIVE,
        _UrgentSignPriority,
        _safe_create_order,
        is_clob_400_rejection,
    )

    m_legs = list(no_legs or [])
    yes_sells = list(liquid_yes_sells or [])
    sh_int = float(math.floor(max(0.0, float(shares or 0.0)) + 1e-9))
    is_verified_m1 = (
        len(m_legs) == 1
        and bool(nr_m1_zero_loss_verified) is True
        and str(nr_m1_mode) == "NR_M1_DEAD_SEED_OVERROUND"
        and len(yes_sells) == 1
    )
    if (len(m_legs) < 2 and not is_verified_m1) or sh_int < 5.0:
        return {"success": False, "error": "INVALID_NR_CONVERT_LEGS_OR_SHARES", "legged_out": False, "outcome_unknown": False}
    try:
        q_indices = [int(lg["question_index"]) for lg in m_legs]
        toks = [str(lg["token_id"]) for lg in m_legs]
    except Exception:
        return {"success": False, "error": "INVALID_NR_CONVERT_METADATA", "legged_out": False, "outcome_unknown": False}
    if len(set(q_indices)) != len(m_legs) or len(set(toks)) != len(m_legs) or any(not t for t in toks):
        return {"success": False, "error": "DUPLICATE_OR_EMPTY_NR_CONVERT_LEGS", "legged_out": False, "outcome_unknown": False}

    prep_legs: List[Dict[str, Any]] = []
    worst_cost_ps = 0.0
    for lg in m_legs:
        tok_i = str(lg["token_id"])
        px_i = executor.quantize_order_price(float(lg["limit_price"]), tok_i, rounding=ROUND_CEILING)
        fr_i = float(lg.get("fee_rate", 0.0) or 0.0)
        fe_i = float(lg.get("fee_exponent", 1.0) or 1.0)
        fee_ps = fr_i * ((px_i * (1.0 - px_i)) ** fe_i) if fr_i > 0.0 else 0.0
        h_i = min(0.25, max(0.0, fee_ps / max(px_i, 1e-6))) if fr_i > 0.0 else 0.0
        gross_sh_i = float(math.ceil((sh_int / max(1.0 - h_i, 1e-6)) * 100.0 - 1e-9) / 100.0) if h_i > 0.0 else float(sh_int)
        worst_cost_ps += (gross_sh_i * px_i) / max(sh_int, 1e-6)
        prep_legs.append({
            "token_id": tok_i,
            "market_id": str(lg.get("market_id") or ""),
            "condition_id": str(lg.get("condition_id") or ""),
            "question_index": int(lg["question_index"]),
            "label": str(lg.get("label") or f"NO_{lg['question_index']}"),
            "px": px_i,
            "fee_rate": fr_i,
            "fee_exponent": fe_i,
            "fee_ps": fee_ps,
            "share_haircut": h_i,
            "gross_shares_req": gross_sh_i,
        })
    if worst_cost_ps > float(max_no_cost_per_share) + 1e-6:
        return {
            "success": False,
            "error": f"NR_CONVERT_WORST_COST_EXCEEDS_CAP ({worst_cost_ps:.4f} > {float(max_no_cost_per_share):.4f})",
            "legged_out": False,
            "outcome_unknown": False,
        }

    eff_mult = 1.0 - max(0, int(fee_bips)) / 10000.0
    if is_verified_m1 and worst_cost_ps >= (eff_mult - 0.001):
        return {
            "success": False,
            "error": f"NR_M1_COST_NOT_STRICTLY_BELOW_PAR ({worst_cost_ps:.4f} >= {eff_mult - 0.001:.4f})",
            "legged_out": False,
            "outcome_unknown": False,
        }
    cash_from_convert_ps = float(len(prep_legs) - 1) * eff_mult
    if executor.dry_run:
        conv_r = executor.attempt_negrisk_convert_positions(neg_risk_market_id, q_indices, sh_int)
        conv_ok_dry = bool(conv_r.get("success", True))
        yes_net_usd = 0.0
        for yl in yes_sells:
            y_px = float(yl.get("min_bid_price") or yl.get("bid_vwap") or 0.0)
            y_fr = float(yl.get("fee_rate", 0.0) or 0.0)
            y_fe = float(yl.get("fee_exponent", 1.0) or 1.0)
            y_fee = y_fr * ((y_px * (1.0 - y_px)) ** y_fe) if y_fr > 0.0 else 0.0
            yes_net_usd += sh_int * max(0.0, (y_px - y_fee) * eff_mult)
        spent_u = round(sum(float(x["gross_shares_req"]) * float(x["px"]) for x in prep_legs), 4)
        conv_u = round(sh_int * cash_from_convert_ps, 4) if conv_ok_dry else 0.0
        net_pnl_u = round(conv_u + (yes_net_usd if conv_ok_dry else 0.0) - spent_u, 4) if conv_ok_dry else 0.0
        return {
            "success": conv_ok_dry,
            "mode": "DRY_RUN",
            "convert_id": convert_id,
            "shares": sh_int,
            "m_no_legs": len(prep_legs),
            "spent_usd": spent_u,
            "converted_cash_usd": conv_u,
            "yes_sell_net_usd": round(yes_net_usd, 4) if conv_ok_dry else 0.0,
            "net_profit_usd": net_pnl_u,
            "convert_tx_hash": conv_r.get("tx_hash"),
            "convert_executed": conv_ok_dry,
            "convert_error": conv_r.get("error"),
            "legged_out": False,
            "outcome_unknown": False,
            "leg_fills": [
                {
                    "token_id": x["token_id"],
                    "market_id": x["market_id"],
                    "condition_id": x["condition_id"],
                    "question_index": x["question_index"],
                    "label": x["label"],
                    "price": x["px"],
                    "gross_shares": x["gross_shares_req"],
                    "matched_shares": sh_int,
                    "orderID": f"MOCK_NRC_{i}",
                }
                for i, x in enumerate(prep_legs)
            ],
        }

    if not executor.is_authenticated or executor.client is None or OrderArgsV2 is None:
        return {"success": False, "error": f"UNAUTHENTICATED_NR_CONVERT ({executor.auth_mode})", "legged_out": False, "outcome_unknown": False}
    if int(getattr(executor, "signature_type", 1) or 1) == 3:
        _rl_pre = getattr(executor, "_relayer_rate_limiter", None)
        if _rl_pre is not None and _rl_pre.recent_count() >= int(_rl_pre.max_per_min):
            return {
                "success": False,
                "stage": "RELAYER_RATE_LIMIT_PRECHECK",
                "error": "RELAYER_RATE_LIMIT_AT_CAP",
                "legged_out": False,
                "outcome_unknown": False,
            }

    _hot_held = True
    _HOT_DISPATCH_ACTIVE.enter()

    def _release_hot_nr() -> None:
        nonlocal _hot_held
        if _hot_held:
            _hot_held = False
            _HOT_DISPATCH_ACTIVE.leave()

    try:
        signed_orders: List[Any] = []
        with _UrgentSignPriority():
            for lg_p in prep_legs:
                tok_i = lg_p["token_id"]
                try:
                    tk_i = executor.get_token_tick_size(tok_i, price_hint=lg_p["px"])
                except TypeError:
                    tk_i = executor.get_token_tick_size(tok_i)
                executor.get_token_neg_risk(tok_i, True)
                op_i = PartialCreateOrderOptions(tick_size=str(tk_i), neg_risk=True, version=2) if PartialCreateOrderOptions else None
                sg_i = _safe_create_order(
                    executor.client.create_order,
                    OrderArgsV2(price=lg_p["px"], size=float(lg_p["gross_shares_req"]), side="BUY", token_id=tok_i),
                    op_i,
                )
                signed_orders.append(sg_i)

        def _post_fok_one(sg_x: Any) -> Tuple[Any, Optional[Exception]]:
            try:
                try:
                    return executor.client.post_order(sg_x, OrderType.FOK, False, True), None
                except TypeError:
                    return executor.client.post_order(sg_x, OrderType.FOK), None
            except Exception as ex_o:
                return None, ex_o

        raw_results = batch_post_fok_orders(executor, signed_orders, OrderType.FOK, post_one_fallback=_post_fok_one)
        _release_hot_nr()

        leg_evals: List[Dict[str, Any]] = []
        any_unknown = False
        filled_count = 0
        for lg_p, (rx, ex_o) in zip(prep_legs, raw_results):
            if ex_o is not None:
                em = str(getattr(ex_o, "error_message", "") or str(ex_o))
                clean = is_clob_400_rejection(ex_o) or any(
                    k in em.lower() for k in ("fok", "couldn't be fully filled", "fully filled", "not enough balance")
                )
                if not clean:
                    any_unknown = True
                leg_evals.append({**lg_p, "filled": False, "outcome_unknown": not clean, "matched_shares": 0.0, "gross_matched_shares": 0.0, "orderID": None, "error": em})
                continue
            if not isinstance(rx, dict):
                any_unknown = True
                leg_evals.append({**lg_p, "filled": False, "outcome_unknown": True, "matched_shares": 0.0, "gross_matched_shares": 0.0, "orderID": None, "error": "MISSING_RESP"})
                continue
            err_s = rx.get("errorMsg") or rx.get("error")
            oid_s = rx.get("orderID") or rx.get("id")
            if err_s and not oid_s:
                leg_evals.append({**lg_p, "filled": False, "outcome_unknown": False, "matched_shares": 0.0, "gross_matched_shares": 0.0, "orderID": None, "error": str(err_s)})
                continue
            gross_req_i = float(lg_p["gross_shares_req"])
            m_sh_gross = executor._extract_fok_matched_shares(rx, gross_req_i) if (oid_s and not err_s) else None
            if m_sh_gross is None:
                any_unknown = True
                leg_evals.append({**lg_p, "filled": False, "outcome_unknown": True, "matched_shares": 0.0, "gross_matched_shares": 0.0, "orderID": oid_s, "error": str(err_s or rx.get("status"))})
                continue
            if m_sh_gross <= 0.0:
                leg_evals.append({**lg_p, "filled": False, "outcome_unknown": False, "matched_shares": 0.0, "gross_matched_shares": 0.0, "orderID": oid_s, "error": "ZERO_MATCH"})
                continue
            h_leg = float(lg_p.get("share_haircut", 0.0) or 0.0)
            net_sh_i = float(math.floor(float(m_sh_gross) * (1.0 - h_leg) * 100.0 + 1e-9) / 100.0) if h_leg > 0.0 else float(m_sh_gross)
            filled_count += 1
            leg_evals.append({**lg_p, "filled": True, "outcome_unknown": False, "gross_matched_shares": float(m_sh_gross), "matched_shares": net_sh_i, "orderID": str(oid_s), "raw": rx})

        if filled_count == 0 and not any_unknown:
            return {
                "success": False,
                "stage": "ALL_LEGS_REJECTED_CLEAN",
                "legged_out": False,
                "outcome_unknown": False,
                "error": "; ".join(str(x.get("error") or "") for x in leg_evals[:2]),
            }

        if filled_count < len(prep_legs) or any_unknown:
            _filled_toks_u = [str(ev["token_id"]) for ev in leg_evals if ev.get("filled") and float(ev.get("matched_shares") or 0.0) > 0.01]
            if _filled_toks_u:
                _min_u_sh = min(float(ev["matched_shares"]) for ev in leg_evals if ev.get("filled") and float(ev.get("matched_shares") or 0.0) > 0.01)
                wait_for_erc1155_delivery(executor, _filled_toks_u, _min_u_sh, timeout_sec=3.5)
            residuals: List[Dict[str, Any]] = []
            for ev in leg_evals:
                if ev.get("filled") and float(ev["matched_shares"] or 0.0) > 0.01:
                    uw = executor.execute_unwind_order(
                        ev["token_id"],
                        size=float(ev["matched_shares"]),
                        side="SELL",
                        min_price=max(0.01, round(float(ev["px"]) - 0.03, 2)),
                        neg_risk=True,
                    )
                    uw_ok = bool(isinstance(uw, dict) and (uw.get("success") or uw.get("partial")) and not uw.get("outcome_unknown"))
                    unw_sh = float(uw.get("matched_size") or 0.0) if uw_ok else 0.0
                    rem_sh = round(max(0.0, float(ev["matched_shares"]) - unw_sh), 4)
                    residuals.append({
                        "token_id": ev["token_id"],
                        "market_id": ev["market_id"],
                        "condition_id": ev["condition_id"],
                        "label": ev["label"],
                        "price": ev["px"],
                        "matched_shares": ev["matched_shares"],
                        "unwound_shares": unw_sh,
                        "residual_shares": rem_sh,
                        "orderID": ev["orderID"],
                        "unwind_outcome_unknown": bool(isinstance(uw, dict) and uw.get("outcome_unknown")),
                        "unwind_result": uw,
                    })
            return {
                "success": False,
                "stage": "PARTIAL_NR_CONVERT_UNWOUND",
                "legged_out": bool(residuals),
                "outcome_unknown": any_unknown,
                "residuals": residuals,
                "leg_evals": leg_evals,
                "error": f"PARTIAL_NR_FILL ({filled_count}/{len(prep_legs)})",
            }

        paired_sh = float(math.floor(min(float(ev["matched_shares"]) for ev in leg_evals) * 100.0 + 1e-9) / 100.0)
        spent_usd = round(sum(float(ev.get("gross_matched_shares") or ev["matched_shares"]) * float(ev["px"]) for ev in leg_evals), 4)
        wait_for_erc1155_delivery(executor, [str(ev["token_id"]) for ev in leg_evals], paired_sh, timeout_sec=3.5)
        conv_res = executor.attempt_negrisk_convert_positions(
            neg_risk_market_id, q_indices, paired_sh, prefer_v2_pusd_adapter=True
        )
        conv_ok = bool(conv_res.get("success"))
        if not conv_ok and not getattr(executor, "dry_run", False):
            wait_for_erc1155_delivery(executor, [str(ev["token_id"]) for ev in leg_evals], paired_sh, timeout_sec=2.5)
            conv_res = executor.attempt_negrisk_convert_positions(
                neg_risk_market_id, q_indices, paired_sh, prefer_v2_pusd_adapter=True
            )
            conv_ok = bool(conv_res.get("success"))
        yes_net_usd = 0.0
        yes_sell_results: List[Dict[str, Any]] = []
        held_guaranteed_complete_set = False
        held_surviving_yes_legs: List[Dict[str, Any]] = []
        if conv_ok and is_verified_m1:
            # Ironclad Post-Convert Zero-Loss Guard for m=1 Dead-Seed Fanout:
            # 1) Re-walk live YES bid book after Polygon block confirmation;
            # 2) Execute a SINGLE all-or-nothing FOK SELL strictly at a limit price that guarantees net proceeds > spent_usd;
            # 3) If bid slipped or FOK rejects, ZERO YES shares leave the wallet, preserving the 100% intact surviving YES
            #    complete set ($1.00 * eff_mult > spent_usd/sh guaranteed at resolution -> 0.000% loss in every branch).
            yl = yes_sells[0]
            y_tok = str(yl.get("yes_token") or yl.get("token_id") or "")
            minted_sh = float(math.floor(paired_sh * eff_mult * 100.0 + 1e-9) / 100.0)
            y_fr = float(yl.get("fee_rate", 0.0) or 0.0)
            y_fe = float(yl.get("fee_exponent", 1.0) or 1.0)
            live_bk = (executor.get_market_book(y_tok) or {}) if (y_tok and hasattr(executor, "get_market_book")) else {}
            raw_bids = live_bk.get("bids", []) if isinstance(live_bk, dict) else getattr(live_bk, "bids", [])
            norm_bids: List[Tuple[float, float]] = []
            for b_lv in (raw_bids or []):
                try:
                    bp = float(b_lv.get("price") if isinstance(b_lv, dict) else getattr(b_lv, "price", b_lv[0]))
                    bs = float(b_lv.get("size") if isinstance(b_lv, dict) else getattr(b_lv, "size", b_lv[1]))
                    if bp > 0 and bs > 0:
                        norm_bids.append((bp, bs))
                except Exception:
                    continue
            norm_bids.sort(key=lambda t: t[0], reverse=True)
            cum_b, gross_b, walk_floor_px = 0.0, 0.0, 0.0
            for bp, bs in norm_bids:
                take_b = min(bs, max(0.0, minted_sh - cum_b))
                if take_b <= 0:
                    break
                gross_b += take_b * bp
                walk_floor_px = bp
                cum_b += take_b
                if cum_b >= minted_sh - 1e-6:
                    break
            live_net_b = 0.0
            if cum_b >= minted_sh - 1e-6 and minted_sh >= 5.0:
                vwap_b = gross_b / minted_sh
                fee_b = minted_sh * y_fr * ((vwap_b * (1.0 - vwap_b)) ** y_fe) if y_fr > 0.0 else 0.0
                live_net_b = max(0.0, gross_b - fee_b)
            fok_swept = False
            if live_net_b >= spent_usd + 0.01 and walk_floor_px > 0.0:
                # Floor limit ensures even worst-case FOK fill recovers > spent_usd after taker fee
                req_gross_ps = (spent_usd + 0.01) / max(minted_sh, 1e-6)
                safe_lim = max(walk_floor_px, round(req_gross_ps + (y_fr * 0.25 if y_fr > 0 else 0.0), 4))
                q_lim = executor.quantize_order_price(min(0.999, safe_lim), y_tok, rounding=ROUND_CEILING)
                if walk_floor_px + 1e-9 >= q_lim:
                    try:
                        try:
                            tk_y = executor.get_token_tick_size(y_tok, price_hint=q_lim)
                        except TypeError:
                            tk_y = executor.get_token_tick_size(y_tok)
                        executor.get_token_neg_risk(y_tok, True)
                        op_y = PartialCreateOrderOptions(tick_size=str(tk_y), neg_risk=True, version=2) if PartialCreateOrderOptions else None
                        sg_y = _safe_create_order(
                            executor.client.create_order,
                            OrderArgsV2(price=q_lim, size=minted_sh, side="SELL", token_id=y_tok),
                            op_y,
                        )
                        try:
                            rx_y = executor.client.post_order(sg_y, OrderType.FOK, False, True)
                        except TypeError:
                            rx_y = executor.client.post_order(sg_y, OrderType.FOK)
                        m_y = executor._extract_fok_matched_shares(rx_y, minted_sh) if isinstance(rx_y, dict) else 0.0
                        if m_y and float(m_y) >= minted_sh - 0.05:
                            tk_u = float((rx_y or {}).get("takingAmount") or 0.0)
                            if tk_u >= 1e4:
                                tk_u /= 1e6
                            gross_fill = tk_u if tk_u > 0.0 else (float(m_y) * vwap_b)
                            px_fill = gross_fill / max(float(m_y), 1e-6)
                            fee_fill = float(m_y) * y_fr * ((px_fill * (1.0 - px_fill)) ** y_fe) if y_fr > 0.0 else 0.0
                            yes_net_usd = max(0.0, gross_fill - fee_fill)
                            fok_swept = True
                            yes_sell_results.append({"token_id": y_tok, "result": rx_y, "swept_fok": True})
                        else:
                            if hasattr(executor, "get_onchain_erc1155_balance") and not getattr(executor, "dry_run", False):
                                try:
                                    rem_y_bal = executor.get_onchain_erc1155_balance(y_tok)
                                    if isinstance(rem_y_bal, (int, float)) and float(rem_y_bal) <= max(0.05, minted_sh * 0.10):
                                        fee_est_y = minted_sh * y_fr * ((q_lim * (1.0 - q_lim)) ** y_fe) if y_fr > 0.0 else 0.0
                                        yes_net_usd = max(0.0, minted_sh * q_lim - fee_est_y)
                                        fok_swept = True
                                except Exception:
                                    pass
                            yes_sell_results.append({"token_id": y_tok, "result": rx_y, "swept_fok": fok_swept})
                    except Exception as ex_y:
                        if hasattr(executor, "get_onchain_erc1155_balance") and not getattr(executor, "dry_run", False):
                            try:
                                rem_y_bal = executor.get_onchain_erc1155_balance(y_tok)
                                if isinstance(rem_y_bal, (int, float)) and float(rem_y_bal) <= max(0.05, minted_sh * 0.10):
                                    fee_est_y = minted_sh * y_fr * ((q_lim * (1.0 - q_lim)) ** y_fe) if y_fr > 0.0 else 0.0
                                    yes_net_usd = max(0.0, minted_sh * q_lim - fee_est_y)
                                    fok_swept = True
                            except Exception:
                                pass
                        yes_sell_results.append({"token_id": y_tok, "error": str(ex_y), "swept_fok": fok_swept})
            if not fok_swept:
                held_guaranteed_complete_set = True
                held_surviving_yes_legs = [
                    {**dict(sv), "shares": minted_sh}
                    for sv in (surviving_yes_legs or [])
                    if isinstance(sv, dict) and sv.get("yes_token")
                ]
        elif conv_ok and yes_sells:
            for yl in yes_sells:
                y_tok = str(yl.get("yes_token") or yl.get("token_id") or "")
                if not y_tok:
                    continue
                min_b = max(0.01, round(float(yl.get("min_bid_price") or yl.get("bid_vwap") or 0.02) - 0.01, 2))
                ys_r = executor.execute_unwind_order(y_tok, size=paired_sh, side="SELL", min_price=min_b, neg_risk=True)
                if isinstance(ys_r, dict) and (ys_r.get("success") or ys_r.get("partial")) and not ys_r.get("outcome_unknown"):
                    m_y = float(ys_r.get("matched_size") or 0.0)
                    p_y = float(ys_r.get("price") or min_b)
                    f_y = float(ys_r.get("fee_usd") or 0.0)
                    yes_net_usd += max(0.0, m_y * p_y - f_y)
                yes_sell_results.append({"token_id": y_tok, "result": ys_r})

        conv_cash = round(paired_sh * cash_from_convert_ps, 4) if conv_ok else 0.0
        guar_carry_pnl = round(paired_sh * eff_mult - spent_usd, 4) if held_guaranteed_complete_set else 0.0
        return {
            "success": True,
            "convert_id": convert_id,
            "shares": paired_sh,
            "m_no_legs": len(prep_legs),
            "spent_usd": spent_usd,
            "converted_cash_usd": conv_cash,
            "yes_sell_net_usd": round(yes_net_usd, 4),
            "guaranteed_hold_profit_usd": guar_carry_pnl,
            "net_profit_usd": guar_carry_pnl if held_guaranteed_complete_set else (round(conv_cash + yes_net_usd - spent_usd, 4) if conv_ok else 0.0),
            "held_guaranteed_complete_set": held_guaranteed_complete_set,
            "held_surviving_yes_legs": held_surviving_yes_legs,
            "convert_executed": conv_ok,
            "convert_tx_hash": conv_res.get("tx_hash"),
            "convert_error": conv_res.get("error"),
            "adapter_used": conv_res.get("adapter_used"),
            "legged_out": False,
            "outcome_unknown": False,
            "leg_fills": leg_evals,
            "yes_sell_results": yes_sell_results,
        }
    finally:
        _release_hot_nr()


def _encode_erc20_approve(spender: str, amount_hex: str = MAX_UINT256_HEX) -> str:
    sp_hex = spender.lower().replace("0x", "").rjust(64, "0")
    return f"0x095ea7b3{sp_hex}{amount_hex}"


def _encode_erc1155_set_approval_for_all(operator: str, approved: bool = True) -> str:
    op_hex = operator.lower().replace("0x", "").rjust(64, "0")
    flag_hex = ("1" if approved else "0").rjust(64, "0")
    return f"0xa22cb465{op_hex}{flag_hex}"


def attempt_onchain_split_position(
    executor: Any,
    condition_id: str,
    shares: float,
    *,
    neg_risk: bool = False,
    up_token_id: str = "",
    down_token_id: str = "",
) -> Dict[str, Any]:
    """
    Mints `shares` complete sets (`1 YES + 1 NO` per `$1.00` `pUSD` / `USDC.e`) via Polygon
    `CTF.splitPosition` (`neg_risk=False`) or `NegRiskAdapterV2.splitPosition` (`neg_risk=True`).
    Automatically prepends `ERC20.approve` inside the same Relayer V2 / Safe batch if needed.
    """
    from src.polymarket_research.redeem_settled_positions import encode_ctf_merge_or_split_calldata

    sh = round(max(0.0, float(shares or 0.0)), 6)
    if not condition_id or sh <= 0.0:
        return {"success": False, "error": "INVALID_SPLIT_ARGS", "reason": "INVALID_SPLIT_ARGS", "tx_hash": None}
    if getattr(executor, "dry_run", True):
        tgt, cd = encode_ctf_merge_or_split_calldata(condition_id, sh, collateral=PUSD_ADDRESS, is_split=True, neg_risk=neg_risk)
        if not neg_risk:
            tgt = CTF_ADAPTER_V2
        return {"success": True, "dry_run": True, "shares": sh, "target": tgt, "calldata": cd, "tx_hash": f"0xdry_split_{int(time.time())}"}

    sig_type = 1 if getattr(executor, "signature_type", None) is None else int(executor.signature_type)
    pk = (os.getenv("POLYGON_PRIVATE_KEY") or getattr(executor, "private_key", "") or "").strip()
    if sig_type not in (0, 1, 2, 3) or not pk or not getattr(executor, "funder_address", None):
        return {"success": False, "error": "MISSING_CREDENTIALS_FOR_SPLIT", "reason": "MISSING_CREDENTIALS_FOR_SPLIT", "tx_hash": None}
    try:
        from web3 import Web3

        w3 = get_fast_polygon_web3(timeout=5.0)
        funder_cs = Web3.to_checksum_address(executor.funder_address)
        signer_cs = Web3.to_checksum_address(w3.eth.account.from_key(pk).address)
        raw_amt = int(math.floor(sh * 1_000_000 + 1e-6))
        erc20_abi = [
            {"constant": True, "inputs": [{"name": "a", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
            {"constant": True, "inputs": [{"name": "o", "type": "address"}, {"name": "s", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        ]
        chosen_col = None
        chosen_target = None
        for col_addr, nr_adapter_addr, bin_target_addr in (
            (PUSD_ADDRESS, NEG_RISK_ADAPTER_V2, CTF_ADAPTER_V2),
            (USDC_E_ADDRESS, NEG_RISK_ADAPTER_V1, CTF_ADDRESS),
        ):
            c_tok = w3.eth.contract(address=Web3.to_checksum_address(col_addr), abi=erc20_abi)
            bal = int(c_tok.functions.balanceOf(funder_cs).call())
            if bal >= raw_amt:
                chosen_col = Web3.to_checksum_address(col_addr)
                chosen_target = Web3.to_checksum_address(nr_adapter_addr if neg_risk else bin_target_addr)
                allow = int(c_tok.functions.allowance(funder_cs, chosen_target).call())
                calls: List[Tuple[str, str]] = []
                if allow < raw_amt:
                    calls.append((chosen_col, _encode_erc20_approve(chosen_target)))
                _, split_cd = encode_ctf_merge_or_split_calldata(
                    condition_id, sh, collateral=chosen_col, is_split=True, neg_risk=neg_risk
                )
                calls.append((chosen_target, split_cd))
                tx_h = executor._dispatch_funder_calls(w3, Web3, pk, sig_type, funder_cs, signer_cs, calls, f"split:{condition_id.lower()}")
                if tx_h:
                    rc = w3.eth.wait_for_transaction_receipt(tx_h, timeout=60, poll_latency=1.5)
                    if int(rc.get("status", 0)) == 1:
                        executor.invalidate_collateral_cache()
                        clob_cli = getattr(executor, "client", None)
                        if clob_cli is not None and hasattr(clob_cli, "update_balance_allowance"):
                            try:
                                try:
                                    from py_clob_client_v2.clob_types import AssetType, BalanceAllowanceParams
                                except ImportError:
                                    from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
                                clob_cli.update_balance_allowance(
                                    BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=sig_type)
                                )
                                for tid_s in (up_token_id, down_token_id):
                                    if tid_s:
                                        clob_cli.update_balance_allowance(
                                            BalanceAllowanceParams(
                                                asset_type=AssetType.CONDITIONAL,
                                                token_id=str(tid_s),
                                                signature_type=sig_type,
                                            )
                                        )
                            except Exception:
                                pass
                        return {"success": True, "shares": sh, "collateral": chosen_col, "target": chosen_target, "tx_hash": tx_h}
                return {"success": False, "error": "SPLIT_TX_FAILED_OR_REVERTED", "reason": "SPLIT_TX_FAILED_OR_REVERTED", "tx_hash": tx_h}
        return {"success": False, "error": "INSUFFICIENT_PUSD_OR_USDC_FOR_SPLIT", "reason": "INSUFFICIENT_PUSD_OR_USDC_FOR_SPLIT", "tx_hash": None}
    except Exception as exc:
        GLOBAL_POLYGON_RPC_POOL.report_failure(getattr(locals().get("w3"), "_dominus_rpc_url", ""))
        return {"success": False, "error": str(exc), "reason": str(exc), "tx_hash": None}


def encode_v2_collateral_wrap_call(
    token_addr: str = USDC_E_ADDRESS,
    recipient_addr: str = "",
    raw_amount: int = 0,
) -> Tuple[str, str]:
    """
    Encodes Polymarket V2 Collateral Wrapper `wrap(address token, address to, uint256 amount)`
    (`0x93070a847eFEf7F70739046a929d47a521f5b8ee`, selector `0x62355638`) for 1:1 `$0.00`-fee
    `USDC.e -> pUSD` conversion.
    """
    if int(raw_amount) <= 0 or not recipient_addr:
        raise ValueError("raw_amount > 0 and recipient_addr required")
    tok_hex = str(token_addr).lower().replace("0x", "").rjust(64, "0")
    to_hex = str(recipient_addr).lower().replace("0x", "").rjust(64, "0")
    amt_hex = f"{int(raw_amount):064x}"
    return POLYMARKET_V2_COLLATERAL_WRAPPER, f"0x62355638{tok_hex}{to_hex}{amt_hex}"


def attempt_wrap_legacy_usdce_to_pusd(
    executor: Any,
    *,
    min_usd: float = 1.0,
) -> Dict[str, Any]:
    """
    Automatically wraps any legacy bridged `USDC.e` (`0x2791...`) sitting on `funder_address`
    1:1 into spendable Polymarket V2 `pUSD` (`0xC011...`) via Relayer V2 (`$0.00` gas on `sig_type=3`),
    then syncs the CLOB L2 collateral allowance cache.
    """
    min_raw = max(1, int(math.floor(max(0.01, float(min_usd)) * 1_000_000)))
    if getattr(executor, "dry_run", False):
        return {"success": False, "wrapped_usd": 0.0, "reason": "DRY_RUN", "tx_hash": None}
    sig_type = 1 if getattr(executor, "signature_type", None) is None else int(executor.signature_type)
    pk = (os.getenv("POLYGON_PRIVATE_KEY") or getattr(executor, "private_key", "") or "").strip()
    b_key = (os.getenv("POLY_BUILDER_API_KEY") or os.getenv("BUILDER_API_KEY") or "").strip()
    if sig_type not in (0, 1, 2, 3) or not pk or not getattr(executor, "funder_address", None):
        return {"success": False, "wrapped_usd": 0.0, "reason": "MISSING_CREDENTIALS", "tx_hash": None}
    if sig_type == 3 and not b_key:
        return {"success": False, "wrapped_usd": 0.0, "reason": "MISSING_BUILDER_KEY", "tx_hash": None}
    try:
        from web3 import Web3

        w3 = get_fast_polygon_web3(timeout=5.0)
        funder_cs = Web3.to_checksum_address(executor.funder_address)
        signer_cs = Web3.to_checksum_address(w3.eth.account.from_key(pk).address)
        if sig_type in (0, 1, 2):
            gas_payer_cs = funder_cs if sig_type == 0 else signer_cs
            if w3.eth.get_balance(gas_payer_cs) < int(0.05 * 1e18):
                return {"success": False, "wrapped_usd": 0.0, "reason": "INSUFFICIENT_POL_GAS", "tx_hash": None}
        usdce_cs = Web3.to_checksum_address(USDC_E_ADDRESS)
        wrapper_cs = Web3.to_checksum_address(POLYMARKET_V2_COLLATERAL_WRAPPER)
        erc20_abi = [
            {"constant": True, "inputs": [{"name": "a", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
            {"constant": True, "inputs": [{"name": "o", "type": "address"}, {"name": "s", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        ]
        usdce = w3.eth.contract(address=usdce_cs, abi=erc20_abi)
        raw_bal = int(usdce.functions.balanceOf(funder_cs).call())
        if raw_bal < min_raw:
            return {"success": False, "wrapped_usd": 0.0, "reason": "NO_LEGACY_USDCE", "tx_hash": None}
        allow = int(usdce.functions.allowance(funder_cs, wrapper_cs).call())
        calls: List[Tuple[str, str]] = []
        if allow < raw_bal:
            calls.append((usdce_cs, "0x" + _encode_erc20_approve(wrapper_cs).replace("0x", "")))
        _, wrap_cd = encode_v2_collateral_wrap_call(usdce_cs, funder_cs, raw_bal)
        if allow >= raw_bal and hasattr(w3.eth, "call"):
            w3.eth.call({"from": funder_cs, "to": wrapper_cs, "data": wrap_cd})
        calls.append((wrapper_cs, wrap_cd))
        tx_h = executor._dispatch_funder_calls(
            w3, Web3, pk, sig_type, funder_cs, signer_cs, calls, f"wrap:usdce_to_pusd:{raw_bal}"
        )
        if not tx_h:
            return {"success": False, "wrapped_usd": 0.0, "reason": "RELAYER_SUBMIT_FAILED", "tx_hash": None}
        rc = w3.eth.wait_for_transaction_receipt(tx_h, timeout=60, poll_latency=1.5)
        if int(rc.get("status", 0)) != 1:
            return {"success": False, "wrapped_usd": 0.0, "reason": "WRAP_TX_REVERTED", "tx_hash": tx_h}
        executor.invalidate_collateral_cache()
        clob_cli = getattr(executor, "client", None)
        if clob_cli is not None and hasattr(clob_cli, "update_balance_allowance"):
            try:
                try:
                    from py_clob_client_v2.clob_types import AssetType, BalanceAllowanceParams
                except ImportError:
                    from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
                clob_cli.update_balance_allowance(
                    BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=sig_type)
                )
            except Exception:
                pass
        wrapped_usd = round(raw_bal / 1_000_000.0, 6)
        logger.info(f"✓ [V2 COLLATERAL WRAP] Wrapped ${wrapped_usd:.2f} legacy USDC.e -> pUSD 1:1 (tx={tx_h}).")
        return {"success": True, "wrapped_usd": wrapped_usd, "reason": "WRAPPED_TO_PUSD", "tx_hash": tx_h}
    except Exception as exc:
        GLOBAL_POLYGON_RPC_POOL.report_failure(getattr(locals().get("w3"), "_dominus_rpc_url", ""))
        return {"success": False, "wrapped_usd": 0.0, "reason": str(exc), "tx_hash": None}


def build_nr3_atomic_mint_all_yes_calls(
    neg_risk_market_id: str,
    cond_0: str,
    cond_1: str,
    q_idx_0: int,
    q_idx_1: int,
    shares: float,
    *,
    adapter_address: str = NEG_RISK_ADAPTER_V2,
) -> List[Tuple[str, str]]:
    """
    Constructs the exact 3-call atomic NegRisk `NR3` synthetic all-YES mint batch:
      1. `splitPosition(cond_0, Q)` -> `Q YES_0 + Q NO_0` (`-$Q`)
      2. `splitPosition(cond_1, Q)` -> `Q YES_1 + Q NO_1` (`-$Q`)
      3. `convertPositions(marketId, (1<<q_idx_0)|(1<<q_idx_1), Q)` -> burns `Q NO_0 + Q NO_1`,
         returns `+$Q * (1 - fee_bips/10000)` collateral + `Q` of ALL remaining `YES_2 .. YES_{N-1}`!
    Net collateral cost = `$1.00 * Q` (plus adapter `fee_bips`), yielding `Q` of all `N` YES outcomes!
    """
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    from src.polymarket_research.redeem_settled_positions import encode_ctf_merge_or_split_calldata

    if int(q_idx_0) == int(q_idx_1) or min(int(q_idx_0), int(q_idx_1)) < 0:
        raise ValueError("NR3 requires two distinct non-negative question indices")
    _, cd_split_0 = encode_ctf_merge_or_split_calldata(cond_0, shares, is_split=True, neg_risk=True)
    _, cd_split_1 = encode_ctf_merge_or_split_calldata(cond_1, shares, is_split=True, neg_risk=True)
    conv_call = PolymarketLiveExecutor.encode_negrisk_convert_positions_call(
        neg_risk_market_id, [int(q_idx_0), int(q_idx_1)], shares, adapter_address=adapter_address
    )
    return [
        (adapter_address, cd_split_0),
        (adapter_address, cd_split_1),
        (adapter_address, conv_call["data"]),
    ]


def detect_nr3_synthetic_all_yes_overround(
    spec: Any,
    books_by_token: Dict[str, Dict[str, Any]],
    *,
    target_budget_usd: float = 25.0,
    min_net_edge_per_set: float = 0.008,
    min_shares: int = 5,
    fee_bips: int = 0,
) -> Optional[Dict[str, Any]]:
    """
    Detects closed-partition `NR3_SYNTHETIC_ALL_YES_OVERROUND` opportunities where:
      - `spec.is_closed_convert_safe` is True (`negRiskAugmented == False`, zero unnamed/Other slots)
      - `2 <= len(spec.brackets) <= 15`
      - Net bid proceeds across ALL `N` YES books exceed `$1.00 + fee_bips/10000 + min_net_edge_per_set`!
    """
    if not getattr(spec, "is_closed_convert_safe", False):
        return None
    if getattr(spec, "neg_risk_augmented", False) or getattr(spec, "enable_neg_risk_other", False):
        return None
    brackets = list(getattr(spec, "brackets", None) or [])
    n_br = len(brackets)
    if n_br < 2 or n_br > 15 or int(getattr(spec, "total_market_count", n_br)) != n_br:
        return None
    conds_ok = [b for b in brackets if str(b.get("condition_id") or "").strip() and b.get("question_index") is not None]
    if len(conds_ok) < 2:
        return None

    parsed_bids: List[Tuple[Dict[str, Any], List[Tuple[float, float]]]] = []
    avail_depths: List[float] = []
    for b in brackets:
        y_tok = str(b.get("yes_token") or "")
        bk = books_by_token.get(y_tok)
        if not isinstance(bk, dict):
            return None
        lvls: List[Tuple[float, float]] = []
        for x in bk.get("bids") or ():
            px = float(x["price"] if isinstance(x, dict) else x[0])
            sz = float(x["size"] if isinstance(x, dict) else x[1])
            if 0.001 <= px <= 0.999 and sz > 0.0:
                lvls.append((px, sz))
        lvls.sort(key=lambda r: r[0], reverse=True)
        if not lvls:
            return None
        avail_depths.append(sum(s for _, s in lvls[:3]))
        parsed_bids.append((b, lvls))

    mint_cost_ps = 1.0 + max(0, int(fee_bips)) / 10000.0
    # Note: 2x splitPosition + convertPositions(0b11) requires 2*Q peak collateral intra-tx ($1*Q refunded inside same tx)
    max_sh_budget = int(math.floor(max(0.0, float(target_budget_usd)) / max(mint_cost_ps, 1.0)))
    max_sh_depth = int(math.floor(min(avail_depths) / 1.15))
    sh_int = min(max_sh_budget, max_sh_depth)
    if sh_int < int(min_shares):
        return None

    yes_sell_legs: List[Dict[str, Any]] = []
    net_proceeds_ps = 0.0
    total_fee_usd = 0.0
    min_l1_usd = float("inf")
    for b, lvls in parsed_bids:
        min_l1_usd = min(min_l1_usd, lvls[0][0] * lvls[0][1])
        cum = 0.0
        gross = 0.0
        min_px = lvls[0][0]
        for px, sz in lvls:
            take = min(sz, sh_int - cum)
            gross += take * px
            min_px = px
            cum += take
            if cum >= sh_int - 1e-6:
                break
        if cum < sh_int - 1e-6:
            return None
        vwap = gross / sh_int
        fr = float(b.get("fee_rate", 0.0) or 0.0)
        fe = float(b.get("fee_exponent", 1.0) or 1.0)
        fee_ps = fr * ((vwap * (1.0 - vwap)) ** fe) if fr > 0.0 else 0.0
        total_fee_usd += sh_int * fee_ps
        net_proceeds_ps += max(0.0, vwap - fee_ps)
        yes_sell_legs.append({
            "yes_token": str(b["yes_token"]),
            "market_id": str(b.get("market_id") or ""),
            "condition_id": str(b.get("condition_id") or ""),
            "question_index": int(b["question_index"]),
            "label": str(b.get("label") or f"YES_{b['question_index']}"),
            "min_bid_price": round(min_px, 4),
            "bid_vwap": round(vwap, 5),
            "fee_rate": fr,
            "fee_exponent": fe,
        })

    net_edge_ps = round(net_proceeds_ps - mint_cost_ps, 5)
    if net_edge_ps < float(min_net_edge_per_set):
        return None
    b0, b1 = conds_ok[0], conds_ok[1]
    return {
        "mode": "NR3_SYNTHETIC_ALL_YES_OVERROUND",
        "neg_risk_market_id": str(spec.neg_risk_market_id),
        "event_id": str(spec.event_id),
        "title": str(spec.title),
        "shares": int(sh_int),
        "n_yes_legs": n_br,
        "split_cond_0": str(b0["condition_id"]),
        "split_cond_1": str(b1["condition_id"]),
        "split_q_idx_0": int(b0["question_index"]),
        "split_q_idx_1": int(b1["question_index"]),
        "mint_cost_per_share": round(mint_cost_ps, 5),
        "net_proceeds_per_share": round(net_proceeds_ps, 5),
        "net_edge_per_share": net_edge_ps,
        "total_net_profit_usd": round(sh_int * net_edge_ps, 4),
        "total_fee_usd": round(total_fee_usd, 4),
        "l1_usd": round(min_l1_usd, 2),
        "fee_bips": int(fee_bips),
        "yes_sell_legs": yes_sell_legs,
    }


def execute_nr3_synthetic_all_yes_overround(
    executor: Any,
    *,
    convert_id: str,
    neg_risk_market_id: str,
    split_cond_0: str,
    split_cond_1: str,
    split_q_idx_0: int,
    split_q_idx_1: int,
    yes_sell_legs: Sequence[Dict[str, Any]],
    shares: float,
    fee_bips: int = 0,
) -> Dict[str, Any]:
    """
    Executes `NR3_SYNTHETIC_ALL_YES_OVERROUND`:
      1. Dispatches 1 atomic Relayer V2 / Safe tx (`2x splitPosition + convertPositions(0b11)`),
         spending `$1.00 * Q` net (`$2.00 * Q` intra-tx peak) to mint `Q` of all `N` YES outcomes.
      2. Verifies on-chain ERC-1155 delivery across all `N` YES tokens.
      3. Pre-signs and dispatches all `N` SELL orders simultaneously via `batch_post_fok_orders` (`FAK`).
    """
    y_legs = list(yes_sell_legs or [])
    sh_int = float(math.floor(max(0.0, float(shares or 0.0)) + 1e-9))
    if len(y_legs) < 2 or len(y_legs) > 15 or sh_int < 5.0:
        return {"success": False, "error": "INVALID_NR3_LEGS_OR_SHARES", "legged_out": False, "outcome_unknown": False}

    mint_cost_ps = 1.0 + max(0, int(fee_bips)) / 10000.0
    spent_usd = round(sh_int * mint_cost_ps, 4)
    if getattr(executor, "dry_run", True):
        calls = build_nr3_atomic_mint_all_yes_calls(
            neg_risk_market_id, split_cond_0, split_cond_1, split_q_idx_0, split_q_idx_1, sh_int
        )
        proceeds = 0.0
        for yl in y_legs:
            px = float(yl.get("bid_vwap") or yl.get("min_bid_price") or 0.0)
            fr = float(yl.get("fee_rate", 0.0) or 0.0)
            fe = float(yl.get("fee_exponent", 1.0) or 1.0)
            fee = fr * ((px * (1.0 - px)) ** fe) if fr > 0.0 else 0.0
            proceeds += sh_int * max(0.0, px - fee)
        return {
            "success": True,
            "mode": "DRY_RUN",
            "convert_id": convert_id,
            "shares": sh_int,
            "m_no_legs": 2,
            "n_yes_legs": len(y_legs),
            "spent_usd": spent_usd,
            "converted_cash_usd": 0.0,
            "yes_sell_net_usd": round(proceeds, 4),
            "net_profit_usd": round(proceeds - spent_usd, 4),
            "convert_executed": True,
            "convert_tx_hash": f"0xdry_nr3_{int(time.time())}",
            "atomic_calls_count": len(calls),
            "legged_out": False,
            "outcome_unknown": False,
        }

    sig_type = 1 if getattr(executor, "signature_type", None) is None else int(executor.signature_type)
    pk = (os.getenv("POLYGON_PRIVATE_KEY") or getattr(executor, "private_key", "") or "").strip()
    if sig_type not in (0, 1, 2, 3) or not pk or not getattr(executor, "funder_address", None):
        return {"success": False, "error": "MISSING_NR3_CREDENTIALS", "legged_out": False, "outcome_unknown": False}

    try:
        from web3 import Web3

        w3 = get_fast_polygon_web3(timeout=5.0)
        funder_cs = Web3.to_checksum_address(executor.funder_address)
        signer_cs = Web3.to_checksum_address(w3.eth.account.from_key(pk).address)
        raw_peak_need = int(math.ceil(2.0 * sh_int * 1_000_000))
        erc20_abi = [
            {"constant": True, "inputs": [{"name": "a", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
            {"constant": True, "inputs": [{"name": "o", "type": "address"}, {"name": "s", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        ]
        ctf_op_abi = [
            {"constant": True, "inputs": [{"name": "account", "type": "address"}, {"name": "operator", "type": "address"}], "name": "isApprovedForAll", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
        ]
        chosen_col = None
        chosen_adapter = None
        for col_addr, ad_addr in ((PUSD_ADDRESS, NEG_RISK_ADAPTER_V2), (USDC_E_ADDRESS, NEG_RISK_ADAPTER_V1)):
            c_tok = w3.eth.contract(address=Web3.to_checksum_address(col_addr), abi=erc20_abi)
            if int(c_tok.functions.balanceOf(funder_cs).call()) >= raw_peak_need:
                chosen_col = Web3.to_checksum_address(col_addr)
                chosen_adapter = Web3.to_checksum_address(ad_addr)
                allow = int(c_tok.functions.allowance(funder_cs, chosen_adapter).call())
                ctf_op = w3.eth.contract(address=Web3.to_checksum_address(CTF_ADDRESS), abi=ctf_op_abi)
                op_ok = bool(ctf_op.functions.isApprovedForAll(funder_cs, chosen_adapter).call())
                prefix_calls: List[Tuple[str, str]] = []
                if allow < raw_peak_need:
                    prefix_calls.append((chosen_col, _encode_erc20_approve(chosen_adapter)))
                if not op_ok:
                    prefix_calls.append((Web3.to_checksum_address(CTF_ADDRESS), _encode_erc1155_set_approval_for_all(chosen_adapter, True)))
                core_calls = build_nr3_atomic_mint_all_yes_calls(
                    neg_risk_market_id, split_cond_0, split_cond_1, split_q_idx_0, split_q_idx_1, sh_int, adapter_address=chosen_adapter
                )
                tx_h = executor._dispatch_funder_calls(
                    w3, Web3, pk, sig_type, funder_cs, signer_cs, prefix_calls + core_calls, f"nr3:{neg_risk_market_id.lower()}"
                )
                if not tx_h:
                    return {"success": False, "error": "NR3_MINT_DISPATCH_FAILED", "legged_out": False, "outcome_unknown": False}
                rc = w3.eth.wait_for_transaction_receipt(tx_h, timeout=60, poll_latency=1.5)
                if int(rc.get("status", 0)) != 1:
                    return {"success": False, "error": f"NR3_MINT_REVERTED:{tx_h}", "legged_out": False, "outcome_unknown": False}
                executor.invalidate_collateral_cache()
                wait_for_erc1155_delivery(executor, [str(x["yes_token"]) for x in y_legs], sh_int, timeout_sec=3.5)

                from src.polymarket_research.polymarket_live_executor import (
                    OrderArgsV2,
                    OrderType,
                    PartialCreateOrderOptions,
                    _safe_create_order,
                    _UrgentSignPriority,
                )

                signed_sells: List[Any] = []
                sell_mins: List[float] = []
                with _UrgentSignPriority():
                    for yl in y_legs:
                        yt = str(yl["yes_token"])
                        min_b = max(0.01, round(float(yl.get("min_bid_price") or yl.get("bid_vwap") or 0.02) - 0.01, 2))
                        min_q = executor.quantize_order_price(min_b, yt, rounding=ROUND_FLOOR)
                        tk = executor.get_token_tick_size(yt, price_hint=min_q)
                        opts = PartialCreateOrderOptions(tick_size=str(tk), neg_risk=True, version=2) if PartialCreateOrderOptions else None
                        sg = _safe_create_order(
                            executor.client.create_order,
                            OrderArgsV2(price=min_q, size=sh_int, side="SELL", token_id=yt),
                            opts,
                        )
                        signed_sells.append(sg)
                        sell_mins.append(min_q)

                fak_type = getattr(OrderType, "FAK", OrderType.FOK)

                def _post_sell_one(sg_x: Any) -> Tuple[Any, Optional[Exception]]:
                    try:
                        return executor.client.post_order(sg_x, fak_type, False, True), None
                    except TypeError:
                        return executor.client.post_order(sg_x, fak_type), None
                    except Exception as ex_s:
                        return None, ex_s

                sell_resps = batch_post_fok_orders(executor, signed_sells, fak_type, post_one_fallback=_post_sell_one)
                yes_net_usd = 0.0
                unfilled_holds: List[Dict[str, Any]] = []
                for yl, min_q, (rx, ex_s) in zip(y_legs, sell_mins, sell_resps):
                    m_sz = executor._extract_fok_matched_shares(rx, sh_int) if isinstance(rx, dict) and ex_s is None else 0.0
                    m_f = float(m_sz or 0.0)
                    rem_y = round(max(0.0, sh_int - m_f), 4)
                    if m_f > 0.0:
                        tk_amt = float((rx or {}).get("takingAmount") or 0.0)
                        if tk_amt >= 1e4:
                            tk_amt /= 1e6
                        gross_y = tk_amt if tk_amt > 0.0 else (m_f * float(yl.get("bid_vwap") or min_q))
                        fr_y = float(yl.get("fee_rate", 0.0) or 0.0)
                        fe_y = float(yl.get("fee_exponent", 1.0) or 1.0)
                        px_eff = gross_y / max(m_f, 1e-6)
                        fee_y = m_f * fr_y * ((px_eff * (1.0 - px_eff)) ** fe_y) if fr_y > 0.0 else 0.0
                        yes_net_usd += max(0.0, gross_y - fee_y)
                    if rem_y > 0.05:
                        unfilled_holds.append({
                            "token_id": str(yl["yes_token"]),
                            "market_id": str(yl.get("market_id") or ""),
                            "condition_id": str(yl.get("condition_id") or ""),
                            "label": str(yl.get("label") or "YES"),
                            "matched_shares": rem_y,
                            "price": round(1.0 / len(y_legs), 4),
                            "orderID": (rx or {}).get("orderID") if isinstance(rx, dict) else None,
                        })
                return {
                    "success": True,
                    "convert_id": convert_id,
                    "shares": sh_int,
                    "m_no_legs": 2,
                    "n_yes_legs": len(y_legs),
                    "spent_usd": spent_usd,
                    "converted_cash_usd": 0.0,
                    "yes_sell_net_usd": round(yes_net_usd, 4),
                    "net_profit_usd": round(yes_net_usd - spent_usd, 4) if not unfilled_holds else 0.0,
                    "convert_executed": len(unfilled_holds) == 0,
                    "convert_tx_hash": tx_h,
                    "adapter_used": chosen_adapter,
                    "leg_fills": unfilled_holds,
                    "legged_out": False,
                    "outcome_unknown": False,
                }
        return {"success": False, "error": "INSUFFICIENT_2X_INTRA_TX_COLLATERAL_FOR_NR3", "legged_out": False, "outcome_unknown": False}
    except Exception as exc:
        return {"success": False, "error": str(exc), "legged_out": False, "outcome_unknown": False}


def finish_nr3_convert_arb(
    harvester: Any,
    cand: Dict[str, Any],
    *,
    sleeve_src: str,
    nrm_id: str,
    dedupe_k: str,
    budget: float,
    collat_f: float,
    fee_bips: int,
    now_ts: float,
) -> Dict[str, Any]:
    """Harvester execution + accounting wrapper for `NR3_SYNTHETIC_ALL_YES_OVERROUND`."""
    raw_y_nr3 = list(cand.get("yes_sell_legs") or [])
    sh_nr3 = int(
        math.floor(
            min(
                float(cand.get("shares") or 12),
                budget / 1.02,
                (collat_f / 2.02) if not getattr(harvester, "dry_run", True) else 999.0,
            )
        )
    )
    if sh_nr3 < 5:
        return {"executed": False, "reason": "INSUFFICIENT_NR3_2X_PEAK_COLLATERAL"}
    cid_nr3 = str(cand.get("box_id") or f"NR3_{int(now_ts)}")
    c_res = harvester.executor.execute_nr3_synthetic_all_yes_overround(
        convert_id=cid_nr3,
        neg_risk_market_id=nrm_id,
        split_cond_0=str(cand.get("split_cond_0") or ""),
        split_cond_1=str(cand.get("split_cond_1") or ""),
        split_q_idx_0=int(cand.get("split_q_idx_0") or 0),
        split_q_idx_1=int(cand.get("split_q_idx_1") or 1),
        yes_sell_legs=raw_y_nr3,
        shares=float(sh_nr3),
        fee_bips=fee_bips,
    )
    if c_res.get("success") and c_res.get("convert_executed"):
        from datetime import datetime, timezone
        net_pnl = round(float(c_res.get("net_profit_usd") or 0.0), 4)
        spent_u = float(c_res["spent_usd"])
        exit_f = time.time()
        harvester.closed_positions.append({
            "trade_id": cid_nr3,
            "box_id": cid_nr3,
            "sleeve": sleeve_src,
            "asset": "NEGRISK_NR3",
            "market_id": str((raw_y_nr3[0] if raw_y_nr3 else {}).get("market_id") or nrm_id[:16]),
            "token_id": "|".join(str(x.get("yes_token") or "") for x in raw_y_nr3),
            "entry_shares": float(c_res["shares"]),
            "notional_usd": spent_u,
            "fee_usd": 0.0,
            "payout_usd": round(spent_u + net_pnl, 4),
            "net_pnl_usd": net_pnl,
            "won": bool(net_pnl >= 0.0),
            "status": "CLOSED",
            "close_reason": "NR3_SYNTHETIC_OVERROUND_COMPLETED",
            "convert_tx_hash": c_res.get("convert_tx_hash"),
            "entry_ts": now_ts,
            "exit_ts": exit_f,
            "entry_time_utc": datetime.fromtimestamp(float(now_ts), tz=timezone.utc).isoformat(),
            "settled_at_utc": datetime.fromtimestamp(float(exit_f), tz=timezone.utc).isoformat(),
        })
        harvester.closed_positions = harvester.closed_positions[-600:]
        release_recycled_box_dedupe_keys(harvester, None, extra_keys=[dedupe_k], cooldown_sec=2.5)
        harvester.executor.invalidate_collateral_cache()
        harvester._pending_collateral_refresh = True
        harvester.save_state()
        return {"executed": True, "result": c_res, "leg_trade_ids": []}
    return {"executed": False, "reason": f"NR3_ABORT:{c_res.get('error')}", "result": c_res}


# ============================================================================
# 5. PHASE 3: 20% CRYPTO MAKER REBATE ANCHOR & $12 PRE-SPLIT OVERROUND GUN
# ============================================================================


def compute_crypto_maker_rebate_per_share(
    price: float, fee_rate: float = 0.07, fee_exponent: float = 1.0, rebate_share: float = CRYPTO_MAKER_REBATE_SHARE
) -> float:
    """Computes Polymarket's 20% Crypto Maker Rebate (`0.20 * fee_rate * (p * (1 - p))^exponent`) in USDC/share."""
    p = min(0.999, max(0.001, float(price)))
    fr = max(0.0, float(fee_rate))
    if fr <= 0.0:
        return 0.0
    return round(float(rebate_share) * fr * ((p * (1.0 - p)) ** max(1.0, float(fee_exponent))), 6)


def evaluate_d1_maker_rebate_anchor(
    *,
    anchor_bid_px: float,
    hedge_ask_px: float,
    anchor_ask_px: Optional[float] = None,
    hedge_avail_shares: Optional[float] = None,
    req_shares: float = 0.0,
    fee_rate: Optional[float] = None,
    anchor_fee_rate: float = 0.07,
    hedge_fee_rate: float = 0.07,
    fee_exponent: float = 1.0,
    shm_spot_age_ms: float = 0.0,
    spot_age_ms: Optional[float] = None,
    adverse_spot_velocity_pct: float = 0.0,
    max_effective_box_cost: float = 0.990,
    max_shm_age_ms: float = 350.0,
) -> Dict[str, Any]:
    """
    Evaluates a Chainlink-guarded `D1_REBATE_MACHINE_GUN` entry where Leg 1 posts `postOnly` at `anchor_bid_px`
    (0% maker fee + 20% USDC maker rebate!) and Leg 2 sweeps Taker FOK at `hedge_ask_px`.
    """
    eff_age_ms = float(spot_age_ms if spot_age_ms is not None else shm_spot_age_ms)
    if eff_age_ms > float(max_shm_age_ms) or eff_age_ms < 0.0:
        return {"eligible": False, "reason": "STALE_SPOT_FEED"}
    if float(adverse_spot_velocity_pct) > 0.00025:
        return {"eligible": False, "reason": "ADVERSE_SPOT_VELOCITY"}
    b1 = round(float(anchor_bid_px), 4)
    a2 = round(float(hedge_ask_px), 4)
    if anchor_ask_px is not None and b1 >= float(anchor_ask_px) - 1e-9:
        return {"eligible": False, "reason": "ANCHOR_CROSSES_ASK"}
    if hedge_avail_shares is not None and float(req_shares) > 0.0 and float(hedge_avail_shares) < max(15.0, 2.0 * float(req_shares)):
        return {"eligible": False, "reason": "INSUFFICIENT_HEDGE_DEPTH"}
    if not (0.15 <= b1 <= 0.85 and 0.15 <= a2 <= 0.85):
        return {"eligible": False, "reason": "PRICE_OUT_OF_REBATE_ZONE"}
    anc_fr = float(fee_rate) if fee_rate is not None else float(anchor_fee_rate)
    hdg_fr = float(fee_rate) if fee_rate is not None else float(hedge_fee_rate)
    rebate_1 = compute_crypto_maker_rebate_per_share(b1, anc_fr, fee_exponent)
    fee_2 = hdg_fr * ((a2 * (1.0 - a2)) ** fee_exponent) if hdg_fr > 0.0 else 0.0
    h_2 = min(0.25, max(0.0, fee_2 / max(a2, 1e-6))) if hdg_fr > 0.0 else 0.0
    leg2_net_cost = a2 / max(1.0 - h_2, 1e-6)
    gross_box_cost = round(b1 + leg2_net_cost, 6)
    eff_box_cost = round((b1 - rebate_1) + leg2_net_cost, 6)
    if eff_box_cost > float(max_effective_box_cost) + 1e-9:
        return {
            "eligible": False,
            "reason": "REBATE_BOX_COST_ABOVE_CAP",
            "effective_box_cost": eff_box_cost,
            "net_rebated_box_cost": eff_box_cost,
        }
    return {
        "eligible": True,
        "anchor_bid_px": b1,
        "hedge_ask_px": a2,
        "maker_rebate_per_share": rebate_1,
        "gross_box_cost": gross_box_cost,
        "effective_box_cost": eff_box_cost,
        "net_rebated_box_cost": eff_box_cost,
        "locked_edge_with_rebate": round(1.0 - eff_box_cost, 6),
    }


def _walk_dual_leg_overround_bids(
    bids_a: Sequence[Any],
    bids_b: Sequence[Any],
    req_shares: float,
    fr_a: float = 0.07,
    fe_a: float = 1.0,
    fr_b: float = 0.07,
    fe_b: float = 1.0,
    depth_mult: float = 1.15,
) -> Dict[str, Any]:
    def _walk_side(bids: Sequence[Any], fr: float, fe: float) -> Optional[Tuple[float, float]]:
        lvls: List[Tuple[float, float]] = []
        for x in bids or ():
            px = float(x["price"] if isinstance(x, dict) else x[0])
            sz = float(x["size"] if isinstance(x, dict) else x[1])
            if 0.001 <= px <= 0.999 and sz > 0.0:
                lvls.append((px, sz))
        lvls.sort(key=lambda r: r[0], reverse=True)
        if sum(s for _, s in lvls) < float(req_shares) * float(depth_mult) - 1e-6:
            return None
        cum = 0.0
        gross = 0.0
        min_px = lvls[0][0]
        for px, sz in lvls:
            take = min(sz, float(req_shares) - cum)
            gross += take * px
            min_px = px
            cum += take
            if cum >= float(req_shares) - 1e-6:
                break
        if cum < float(req_shares) - 1e-6:
            return None
        vwap = gross / max(float(req_shares), 1e-6)
        fee_ps = float(fr) * ((vwap * (1.0 - vwap)) ** float(fe)) if float(fr) > 0.0 else 0.0
        return (round(vwap - fee_ps, 6), round(min_px, 4))

    wa = _walk_side(bids_a, fr_a, fe_a)
    wb = _walk_side(bids_b, fr_b, fe_b)
    if wa is None or wb is None:
        return {"fillable": False}
    return {
        "fillable": True,
        "net_sum_per_share": round(wa[0] + wb[0], 6),
        "min_px_a": wa[1],
        "min_px_b": wb[1],
    }


def is_reward_locked_carry_live_ready(
    daemon: Any,
    p_model: float = 1.0,
    *,
    min_reward_shares: float = 0.0,
    resting_bid_px: float = 0.99,
) -> bool:
    """
    Allows 100%-mathematically-locked (`p_model >= 0.999`, e.g. physical METAR passed high/low by >=2 deg
    or monotonic counter passed bracket) `MKR_REWARD_LOCKED_CARRY` quotes with 0 shadow losses to bridge
    into live `SINGLE_LEG_MAKER_LOCK` once `D1` is `8/8` graduated AND live seed clip size actually
    qualifies for Polymarket's `rewards_min_size` share floor (preventing unrewarded zero-seller slot squatting).
    """
    if float(p_model or 0.0) < 0.999 and not (
        hasattr(daemon, "is_sleeve_grad8_ready") and daemon.is_sleeve_grad8_ready("MKR_REWARD_LOCKED_CARRY")
    ):
        return False
    if not (
        hasattr(daemon, "is_sleeve_grad8_ready")
        and (
            daemon.is_sleeve_grad8_ready("MKR_REWARD_LOCKED_CARRY")
            or daemon.is_sleeve_grad8_ready("D1_SAME_ORACLE_DOMINANCE_BOX")
        )
    ):
        return False
    if any(
        isinstance(p, dict) and p.get("sleeve") == "MKR_REWARD_LOCKED_CARRY" and not bool(p.get("won", True))
        for p in (getattr(daemon, "closed_positions", None) or ())
    ):
        return False
    try:
        from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

        rb = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {})
        if not bool(rb.get("enable_reward_locked_carry_live_bridge", True)):
            return False
        if float(min_reward_shares or 0.0) > 0.0:
            from src.polymarket_research.riskless_protocol_v2_expansion import compute_dynamic_riskless_tier_caps

            eq_u = float(getattr(daemon, "live_account_equity_usd", 0.0) or 0.0)
            rw_cap_u = float(compute_dynamic_riskless_tier_caps(eq_u, rb)["reward_harvester_cap_usd"])
            est_sh = math.floor(rw_cap_u / max(0.50, float(resting_bid_px or 0.99)))
            if est_sh < float(min_reward_shares) - 1e-6:
                return False
        return True
    except Exception:
        return True


def read_shm_spot_age_ms(asset: str, now_ts: float, fallback_age_ms: float = 999.0) -> float:
    """Reads `/dev/shm/pm_fast_tick_{ASSET}.json` timestamp so Alpha-124 sees true sub-10ms SHM spot age."""
    shm_p = f"/dev/shm/pm_fast_tick_{str(asset or '').strip().upper()}.json"
    try:
        if os.path.exists(shm_p):
            import json as _json

            with open(shm_p, "r", encoding="utf-8") as fh:
                d = _json.load(fh)
            ts = float(d.get("timestamp_unix") or d.get("ts") or 0.0)
            if ts > 0.0:
                return min(float(fallback_age_ms), max(0.0, (float(now_ts) - ts) * 1000.0))
    except Exception:
        pass
    return float(fallback_age_ms)


def _is_clob_book_crossed(bk: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(bk, dict):
        return False
    bs = [
        float(lv["price"] if isinstance(lv, dict) else lv[0])
        for lv in (bk.get("bids") or ())
        if (isinstance(lv, dict) and float(lv.get("size", 0) or 0) > 0 and float(lv.get("price", 0) or 0) > 0)
        or (isinstance(lv, (list, tuple)) and len(lv) >= 2 and float(lv[1]) > 0 and float(lv[0]) > 0)
    ]
    aks = [
        float(lv["price"] if isinstance(lv, dict) else lv[0])
        for lv in (bk.get("asks") or ())
        if (isinstance(lv, dict) and float(lv.get("size", 0) or 0) > 0 and float(lv.get("price", 0) or 0) > 0)
        or (isinstance(lv, (list, tuple)) and len(lv) >= 2 and float(lv[1]) > 0 and float(lv[0]) > 0)
    ]
    return bool(bs and aks and max(bs) >= min(aks))


def _shm_side_to_clob_book(side_obj: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(side_obj, dict) or bool(side_obj.get("is_crossed")):
        return None
    bids = [
        {"price": float(lv[0]), "size": float(lv[1])}
        for lv in (side_obj.get("raw_top_bids") or ())
        if isinstance(lv, (list, tuple)) and len(lv) >= 2 and 0.0 < float(lv[0]) < 1.0 and float(lv[1]) > 0
    ]
    asks = [
        {"price": float(lv[0]), "size": float(lv[1])}
        for lv in (side_obj.get("raw_top_asks") or ())
        if isinstance(lv, (list, tuple)) and len(lv) >= 2 and 0.0 < float(lv[0]) < 1.0 and float(lv[1]) > 0
    ]
    bsz1 = side_obj.get("bid_size_l1") or side_obj.get("bid_depth_1c_shares")
    if not bids and side_obj.get("best_bid") and bsz1 and 0.0 < float(side_obj["best_bid"]) < 1.0 and float(bsz1) > 0:
        bids = [{"price": float(side_obj["best_bid"]), "size": float(bsz1)}]
    asz1 = side_obj.get("ask_size_l1") or side_obj.get("ask_depth_1c_shares")
    if not asks and side_obj.get("best_ask") and asz1 and 0.0 < float(side_obj["best_ask"]) < 1.0 and float(asz1) > 0:
        asks = [{"price": float(side_obj["best_ask"]), "size": float(asz1)}]
    raw_bb = float(side_obj.get("best_bid") or 0.0)
    raw_ba_val = side_obj.get("best_ask")
    raw_ba = float(raw_ba_val) if raw_ba_val is not None else 0.0
    has_real_ba = (0.0 < raw_ba < 1.0) or (raw_ba >= 1.0 and bool(asks or (asz1 and float(asz1) > 0)))
    if raw_bb > 0.0 and has_real_ba and raw_bb >= raw_ba:
        return None
    top_b = max((b["price"] for b in bids), default=(raw_bb if 0.0 < raw_bb < 1.0 else 0.0))
    top_a = min((a["price"] for a in asks), default=(raw_ba if 0.0 < raw_ba < 1.0 else 0.0))
    if top_b > 0.0 and top_a > 0.0 and top_b >= top_a:
        return None
    return {"bids": bids, "asks": asks}


class PreSplitInventoryGun:
    """
    Revolving `$12` Pre-Split Complete-Set Overround Machine Gun for active `BTC 15m/5m` candles:
      - Watches `/dev/shm/pm_fast_tick_BTC.json` (`m15` / `m5` L2 `raw_top_bids` or synthetic top-level books).
      - Under `riskless_only_mode: true` (`enable_pre_split_dual_maker_asks: false`), NEVER posts naked 1-leg
        maker asks that can be adversely sniped; strictly executes atomic dual-leg L2 bid overround sweeps
        (`net_sum >= $1.004`) and merges `UP + DOWN -> $1.00/pair` `pUSD` at `TTE <= 75s` (`$0` loss).
    """

    def __init__(self, cap_usd: Optional[float] = None, min_free_cash_usd: Optional[float] = None) -> None:
        self._explicit_cap_usd = float(cap_usd) if cap_usd is not None else None
        self.cap_usd = float(cap_usd) if cap_usd is not None else 12.0
        self._explicit_min_free_cash = float(min_free_cash_usd) if min_free_cash_usd is not None else None
        self.min_free_cash_usd = float(min_free_cash_usd) if min_free_cash_usd is not None else 14.0
        self.last_tick_ts = 0.0
        self._cid_cache: Dict[str, str] = {}

    @staticmethod
    def _state(harvester: Any) -> Dict[str, Any]:
        st = getattr(harvester, "pre_split_inventory_state", None)
        if not isinstance(st, dict):
            st = {}
            setattr(harvester, "pre_split_inventory_state", st)
        return st

    def _resolve_cid_for_market(self, market_id: str) -> str:
        mid = str(market_id or "").strip()
        if not mid:
            return ""
        if mid in self._cid_cache:
            return self._cid_cache[mid]
        try:
            resp = requests.get(
                f"https://gamma-api.polymarket.com/markets/{mid}",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=2.5,
            )
            if resp.status_code == 200:
                cid = str((resp.json() or {}).get("conditionId") or "").strip()
                if cid.startswith("0x") and len(cid) >= 42:
                    self._cid_cache[mid] = cid
                    return cid
        except Exception:
            pass
        return ""

    def _extract_shm_books_for_tokens(self, ft: Optional[Dict[str, Any]], up_tok: str, dn_tok: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        if not isinstance(ft, dict):
            return None, None
        bks = ft.get("books")
        if isinstance(bks, dict) and (up_tok in bks or dn_tok in bks):
            bu, bd = bks.get(up_tok), bks.get(dn_tok)
            return (None if _is_clob_book_crossed(bu) else bu), (None if _is_clob_book_crossed(bd) else bd)
        for hk in ("m15", "m5", "h1", "h4"):
            sub = ft.get(hk)
            if isinstance(sub, dict):
                u_o, d_o = sub.get("UP"), sub.get("DOWN")
                if isinstance(u_o, dict) and isinstance(d_o, dict):
                    if str(u_o.get("token_id") or "") == up_tok and str(d_o.get("token_id") or "") == dn_tok:
                        return _shm_side_to_clob_book(u_o), _shm_side_to_clob_book(d_o)
        return None, None

    async def tick(self, harvester: Any, now_ts: float, *, fast_tick_reader: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None) -> Optional[str]:
        if (now_ts - self.last_tick_ts) < 0.35:
            return None
        self.last_tick_ts = now_ts
        snap: Dict[str, Any] = {}
        dir_snap: Dict[str, Any] = {}
        gov_override = getattr(harvester, "governance_snapshot", None)
        if isinstance(gov_override, dict):
            snap = gov_override.get("riskless_boxes", {}) or {}
            dir_snap = gov_override.get("directional", {}) or {}
        else:
            try:
                from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

                snap = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("riskless_boxes", {}) or {}
                dir_snap = GLOBAL_GOVERNANCE_MANAGER.snapshot.get("directional", {}) or {}
            except Exception:
                pass
        ex = harvester.executor
        st = self._state(harvester)

        # Always supervise & merge ALL active pre-split slots BEFORE checking enable_pre_split_overround_gun
        # so hot-reload disabling mid-cycle never strands minted shares across BTC/ETH/SOL.
        extra_slots: Dict[str, Dict[str, Any]] = st.get("extra_slots") if isinstance(st.get("extra_slots"), dict) else {}
        last_sup_res: Optional[str] = None
        if st.get("active"):
            saved_extras = dict(extra_slots)
            last_sup_res = await self._supervise_active_inventory(
                harvester, ex, st, now_ts, fast_tick_reader, snap=snap, dir_snap=dir_snap
            )
            if saved_extras and not isinstance(st.get("extra_slots"), dict):
                st["extra_slots"] = saved_extras
                extra_slots = saved_extras
        for k_sl in list(extra_slots.keys()):
            sl_d = extra_slots.get(k_sl)
            if not isinstance(sl_d, dict) or not sl_d.get("active"):
                extra_slots.pop(k_sl, None)
                continue
            r_sl = await self._supervise_active_inventory(
                harvester, ex, sl_d, now_ts, fast_tick_reader, snap=snap, dir_snap=dir_snap
            )
            if r_sl is not None:
                last_sup_res = r_sl
            if not sl_d.get("active"):
                extra_slots.pop(k_sl, None)
        if not st.get("active") and extra_slots:
            prom_k = next(iter(extra_slots.keys()))
            prom_d = extra_slots.pop(prom_k)
            st.update(prom_d)
            if extra_slots:
                st["extra_slots"] = extra_slots
            else:
                st.pop("extra_slots", None)
            await asyncio.to_thread(harvester.save_state)
        elif not extra_slots and "extra_slots" in st:
            st.pop("extra_slots", None)

        is_test_override = (
            self._explicit_cap_usd is not None
            and not isinstance(gov_override, dict)
            and not getattr(harvester, "holistic_v5_live_mode", False)
            and (getattr(ex, "dry_run", True) or getattr(ex, "client", None) is None)
        )
        collat_pre = getattr(harvester, "_last_known_collateral", None)
        _ps_open_eq = (min(float(st.get("up_rem", 0.0) or 0.0), float(st.get("dn_rem", 0.0) or 0.0)) if st.get("active") else 0.0) + sum(
            min(float(s.get("up_rem", 0.0) or 0.0), float(s.get("dn_rem", 0.0) or 0.0))
            for s in extra_slots.values()
            if isinstance(s, dict) and s.get("active")
        )
        tot_eq_ps = (
            (float(collat_pre) if isinstance(collat_pre, (int, float)) else 0.0)
            + _ps_open_eq
            + sum(
                float(p.get("notional_usd", 0.0) or 0.0)
                for p in (getattr(harvester, "active_positions", None) or {}).values()
                if isinstance(p, dict)
            )
        )
        from src.polymarket_research.riskless_protocol_v2_expansion import compute_dynamic_riskless_tier_caps

        dyn_ps = compute_dynamic_riskless_tier_caps(tot_eq_ps, snap)
        cfg_max_slots = max(1, min(3, int(snap.get("pre_split_max_concurrent_slots", 3) or 3)))
        max_conc_slots = 1
        if dyn_ps["pre_split_enabled"] or bool(snap.get("enable_pre_split_overround_gun", False)):
            max_conc_slots = min(cfg_max_slots, 1 if tot_eq_ps < 220.0 else (2 if tot_eq_ps < 360.0 else 3))
        active_slot_count = (1 if st.get("active") else 0) + sum(
            1 for s in extra_slots.values() if isinstance(s, dict) and s.get("active")
        )
        if active_slot_count >= max_conc_slots:
            return last_sup_res

        from src.polymarket_research.stage_c_zero_loss_velocity import is_strict_riskless_pre_split_blocked

        _live_prod_strict = bool(
            (hasattr(harvester, "_is_v5_live_strict") and harvester._is_v5_live_strict())
            or getattr(harvester, "holistic_v5_live_mode", False) is True
            or (isinstance(gov_override, dict) and "strict_zero_legging_pre_split_lock" in (gov_override.get("riskless_boxes") or {}))
        )
        if not is_test_override and _live_prod_strict and is_strict_riskless_pre_split_blocked(snap):
            return last_sup_res
        explicit_gov_disabled = (
            isinstance(gov_override, dict)
            and (gov_override.get("riskless_boxes") or {}).get("enable_pre_split_overround_gun") is False
            and "pre_split_dynamic_unlock_equity_usd" not in (gov_override.get("riskless_boxes") or {})
        )
        if not is_test_override and not (bool(snap.get("enable_pre_split_overround_gun", False)) or (bool(dyn_ps["pre_split_enabled"]) and not explicit_gov_disabled)):
            return last_sup_res
        eff_ps_cap = (
            float(self.cap_usd)
            if (is_test_override and self._explicit_min_free_cash is not None)
            else float(dyn_ps["pre_split_cap_usd"] if dyn_ps["pre_split_enabled"] else snap.get("pre_split_inventory_cap_usd", self.cap_usd))
        )
        cap_shares = float(math.floor(min(60.0 if dyn_ps["pre_split_enabled"] else 20.0, max(5.0, eff_ps_cap))))
        min_free_req = (
            self._explicit_min_free_cash
            if self._explicit_min_free_cash is not None
            else float(snap.get("pre_split_min_free_cash_usd", self.min_free_cash_usd))
        )

        if harvester.dry_run or not getattr(harvester, "_startup_reconciled", False) or getattr(harvester, "global_halt_active", False):
            return last_sup_res
        if float(st.get("cooldown_until", 0.0) or 0.0) > now_ts:
            return last_sup_res
        collat = getattr(harvester, "_last_known_collateral", None)
        if not isinstance(collat, (int, float)):
            return last_sup_res
        collat_free = float(collat)
        if not getattr(harvester, "_collateral_excludes_resting_maker", False):
            from src.polymarket_research.riskless_protocol_v2_expansion import pending_intents_cash_reserved_usd

            _pre_res_ps = sum(float(v or 0.0) for v in (getattr(harvester, "_prepost_sll_reserved_usd", None) or {}).values())
            collat_free = max(
                0.0,
                collat_free
                - pending_intents_cash_reserved_usd(getattr(harvester, "pending_entry_intents", None))
                - _pre_res_ps,
            )
        if self._explicit_min_free_cash is not None:
            need_cash = max(min_free_req, cap_shares * 2.5)
        else:
            if collat_free < min_free_req:
                return last_sup_res
            cap_shares = min(cap_shares, float(math.floor(collat_free - 2.0)))
            if cap_shares < 5.0:
                return last_sup_res
            need_cash = max(min_free_req, cap_shares + 1.5)
        if collat_free < need_cash:
            return last_sup_res
        if fast_tick_reader is None:
            return last_sup_res
        open_ps_assets: Set[str] = set()
        open_ps_cids: Set[str] = set()
        if st.get("active"):
            open_ps_assets.add(str(st.get("asset") or "").upper())
            open_ps_cids.add(str(st.get("condition_id") or ""))
        for _es in extra_slots.values():
            if isinstance(_es, dict) and _es.get("active"):
                open_ps_assets.add(str(_es.get("asset") or "").upper())
                open_ps_cids.add(str(_es.get("condition_id") or ""))
        req_ovr = bool(snap.get("pre_split_require_live_overround", True))
        asset_sel = "BTC"
        fr_sel = 0.072
        fe_sel = 1.0
        cid = ""
        up_tok = ""
        dn_tok = ""
        exp_ts = 0.0
        open_spot = 0.0
        best_cand = None
        for asset_sym in ("BTC", "ETH", "SOL", "XRP", "XAU", "XAG"):
            if asset_sym in open_ps_assets:
                continue
            ft = fast_tick_reader(asset_sym)
            if not isinstance(ft, dict):
                continue
            ts_ft = float(ft.get("timestamp_unix") or ft.get("ts") or 0.0)
            if (now_ts - ts_ft) > 1.5:
                continue
            cid_t = str(ft.get("condition_id") or "").strip()
            ut_t = str(ft.get("up_token_id") or (ft.get("tokens") or {}).get("UP") or "").strip()
            dt_t = str(ft.get("down_token_id") or (ft.get("tokens") or {}).get("DOWN") or "").strip()
            exp_t = float(ft.get("candle_expiry_ts") or ft.get("expiry_ts") or 0.0)
            op_t = float(ft.get("candle_open_spot") or ft.get("open_spot") or 0.0)
            tte_t = exp_t - now_ts
            if cid_t and len(ut_t) >= 20 and len(dt_t) >= 20 and 150.0 <= tte_t <= 840.0 and op_t > 0.0:
                def_fr_t = 0.07
                fr_t = float(ft.get("fee_rate") if ft.get("fee_rate") is not None else def_fr_t)
                fe_t = float(ft.get("fee_exponent") or 1.0)
                eff_req_ovr_t = req_ovr and (self._explicit_min_free_cash is None)
                if eff_req_ovr_t and isinstance(ft.get("books"), dict):
                    bk_ut, bk_dt = ft["books"].get(ut_t), ft["books"].get(dt_t)
                    if _is_clob_book_crossed(bk_ut) or _is_clob_book_crossed(bk_dt):
                        continue
                    w_t = _walk_dual_leg_overround_bids(
                        (bk_ut or {}).get("bids") or [], (bk_dt or {}).get("bids") or [], cap_shares, fr_t, fe_t, fr_t, fe_t, 1.05
                    )
                    net_t = float(w_t.get("net_sum_per_share") or 0.0) if w_t.get("fillable") else 0.0
                    min_ovr_t = 1.003 if fr_t == 0.0 else 1.004
                    if net_t >= min_ovr_t and (best_cand is None or net_t > best_cand[0]):
                        best_cand = (net_t, "", ut_t, dt_t, exp_t, op_t, asset_sym, cid_t, fr_t, fe_t)
                elif not eff_req_ovr_t:
                    if isinstance(ft.get("books"), dict) and (
                        _is_clob_book_crossed(ft["books"].get(ut_t)) or _is_clob_book_crossed(ft["books"].get(dt_t))
                    ):
                        continue
                    best_cand = (1.01, "", ut_t, dt_t, exp_t, op_t, asset_sym, cid_t, fr_t, fe_t)
                    break
                continue
            for hk, min_t, max_t in (("m15", 150.0, 840.0), ("m5", 85.0, 285.0), ("h1", 180.0, 3300.0)):
                sub = ft.get(hk)
                if not isinstance(sub, dict):
                    continue
                mid_s = str(sub.get("market_id") or "").strip()
                cid_s = str(sub.get("condition_id") or sub.get("conditionId") or "").strip()
                exp_s = float(sub.get("expiry_ts") or 0.0)
                tte_s = exp_s - now_ts
                op_s = float(sub.get("authoritative_chainlink_open") or sub.get("finalized_open") or ft.get("spot_price") or 0.0)
                u_o, d_o = sub.get("UP"), sub.get("DOWN")
                if not ((mid_s or cid_s) and min_t <= tte_s <= max_t and op_s > 0.0 and isinstance(u_o, dict) and isinstance(d_o, dict)):
                    continue
                ut_s = str(u_o.get("token_id") or "").strip()
                dt_s = str(d_o.get("token_id") or "").strip()
                if len(ut_s) < 20 or len(dt_s) < 20:
                    continue
                fm_s = sub.get("fee_metadata") if isinstance(sub.get("fee_metadata"), dict) else {}
                def_fr = 0.07
                fees_en = fm_s.get("fees_enabled", True)
                fr_s = float(sub.get("fee_rate") if sub.get("fee_rate") is not None else (fm_s.get("rate", def_fr) if fees_en else 0.0))
                fe_s = float(sub.get("fee_exponent") if sub.get("fee_exponent") is not None else fm_s.get("exponent", 1.0))
                bk_u_s = _shm_side_to_clob_book(u_o)
                bk_d_s = _shm_side_to_clob_book(d_o)
                if bk_u_s is None or bk_d_s is None:
                    continue
                w_s = _walk_dual_leg_overround_bids(
                    (bk_u_s or {}).get("bids") or [], (bk_d_s or {}).get("bids") or [], cap_shares, fr_s, fe_s, fr_s, fe_s, 1.05
                )
                net_s = float(w_s.get("net_sum_per_share") or 0.0) if w_s.get("fillable") else 0.0
                min_ovr_s = 1.003 if fr_s == 0.0 else 1.004
                if req_ovr and net_s < min_ovr_s:
                    continue
                if best_cand is None or net_s > best_cand[0]:
                    best_cand = (net_s, mid_s, ut_s, dt_s, exp_s, op_s, asset_sym, cid_s, fr_s, fe_s)
        if best_cand is None:
            return last_sup_res
        _, mid_sel, up_tok, dn_tok, exp_ts, open_spot, asset_sel, cid_sub, fr_sel, fe_sel = best_cand
        cid = cid_sub if (cid_sub.startswith("0x") and len(cid_sub) >= 42) else await asyncio.to_thread(self._resolve_cid_for_market, mid_sel)
        if not cid or cid in open_ps_cids:
            return last_sup_res

        inflight_u = sum(
            float(i.get("notional_usd", 0.0) or 0.0)
            for i in (getattr(harvester, "pending_entry_intents", None) or {}).values()
            if isinstance(i, dict)
        )
        if (float(collat) - inflight_u) < need_cash:
            return last_sup_res

        busy_cids = {str(p.get("condition_id") or "") for p in harvester.active_positions.values()} | open_ps_cids
        if cid in busy_cids:
            return last_sup_res

        sp_res = await asyncio.to_thread(
            attempt_onchain_split_position, ex, cid, cap_shares, neg_risk=False, up_token_id=up_tok, down_token_id=dn_tok
        )
        if not sp_res.get("success"):
            st["cooldown_until"] = now_ts + 30.0
            return last_sup_res
        new_slot = {
            "active": True,
            "asset": asset_sel,
            "fee_rate": fr_sel,
            "fee_exponent": fe_sel,
            "condition_id": cid,
            "up_token_id": up_tok,
            "down_token_id": dn_tok,
            "expiry_ts": exp_ts,
            "open_spot": open_spot,
            "initial_shares": cap_shares,
            "up_rem": cap_shares,
            "dn_rem": cap_shares,
            "cost_usd": cap_shares,
            "realized_cash_usd": 0.0,
            "rebate_est_usd": 0.0,
            "up_ask_oid": None,
            "dn_ask_oid": None,
            "up_ask_px": 0.0,
            "dn_ask_px": 0.0,
            "split_tx_hash": sp_res.get("tx_hash"),
            "opened_ts": now_ts,
        }
        if st.get("active"):
            st.setdefault("extra_slots", {})[asset_sel] = new_slot
        else:
            saved_ex_d = st.get("extra_slots") if isinstance(st.get("extra_slots"), dict) else None
            st.clear()
            st.update(new_slot)
            if saved_ex_d:
                st["extra_slots"] = saved_ex_d
        if getattr(harvester, "_last_known_collateral", None) is not None:
            harvester._last_known_collateral = max(0.0, float(harvester._last_known_collateral) - cap_shares)
        await asyncio.to_thread(harvester.save_state)
        logger.info(f"✓ [PRE-SPLIT GUN ARMED] {asset_sel} cid={cid[:12]} | {cap_shares:.0f} UP + {cap_shares:.0f} DOWN minted (tx={sp_res.get('tx_hash')}).")
        return "ARMED"

    async def _cancel_resting_asks(self, ex: Any, st: Dict[str, Any]) -> None:
        oids = [str(st[k]) for k in ("up_ask_oid", "dn_ask_oid") if st.get(k)]
        if oids and hasattr(ex, "cancel_orders_batch"):
            await asyncio.to_thread(ex.cancel_orders_batch, oids)
        else:
            for oid in oids:
                await asyncio.to_thread(ex.cancel_order, oid)
        for side_k, oid_k, px_k, tok_k in (
            ("up_rem", "up_ask_oid", "up_ask_px", "up_token_id"),
            ("dn_rem", "dn_ask_oid", "dn_ask_px", "down_token_id"),
        ):
            oid = st.get(oid_k)
            if oid:
                s_r = await asyncio.to_thread(ex.get_order_fill_summary, str(oid), st.get(tok_k))
                if isinstance(s_r, dict) and float(s_r.get("matched") or 0.0) > 0.0:
                    m_sh = float(s_r["matched"])
                    px_f = float(st.get(px_k) or 0.51)
                    cash_f = float(s_r.get("cash") or (m_sh * px_f))
                    st[side_k] = round(max(0.0, float(st[side_k]) - m_sh), 4)
                    st["realized_cash_usd"] = round(float(st.get("realized_cash_usd") or 0.0) + cash_f, 4)
                    st["rebate_est_usd"] = round(
                        float(st.get("rebate_est_usd") or 0.0) + m_sh * compute_crypto_maker_rebate_per_share(px_f, 0.07, 1.0), 4
                    )
                ex.release_inventory(reservation_id=str(oid))
                st[oid_k] = None

    async def _supervise_active_inventory(
        self,
        harvester: Any,
        ex: Any,
        st: Dict[str, Any],
        now_ts: float,
        fast_tick_reader: Optional[Callable[[str], Optional[Dict[str, Any]]]],
        *,
        snap: Optional[Dict[str, Any]] = None,
        dir_snap: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        tte = float(st.get("expiry_ts") or 0.0) - now_ts
        asset_st = str(st.get("asset") or "BTC").upper()
        fr_st = float(st.get("fee_rate") if st.get("fee_rate") is not None else 0.07)
        fe_st = float(st.get("fee_exponent") or 1.0)
        ft = fast_tick_reader(asset_st) if callable(fast_tick_reader) else None
        spot_fresh = isinstance(ft, dict) and (now_ts - float(ft.get("timestamp_unix") or ft.get("ts") or 0.0)) <= 1.5

        # Reconcile any fills on resting maker asks first
        for side_k, oid_k, px_k, tok_k in (
            ("up_rem", "up_ask_oid", "up_ask_px", "up_token_id"),
            ("dn_rem", "dn_ask_oid", "dn_ask_px", "down_token_id"),
        ):
            oid = st.get(oid_k)
            if oid:
                s_r = await asyncio.to_thread(ex.get_order_fill_summary, str(oid), st.get(tok_k))
                if isinstance(s_r, dict) and s_r.get("terminal") and float(s_r.get("matched") or 0.0) > 0.0:
                    m_sh = float(s_r["matched"])
                    px_f = float(st.get(px_k) or 0.51)
                    cash_f = float(s_r.get("cash") or (m_sh * px_f))
                    st[side_k] = round(max(0.0, float(st[side_k]) - m_sh), 4)
                    st["realized_cash_usd"] = round(float(st.get("realized_cash_usd") or 0.0) + cash_f, 4)
                    st["rebate_est_usd"] = round(
                        float(st.get("rebate_est_usd") or 0.0) + m_sh * compute_crypto_maker_rebate_per_share(px_f, 0.07, 1.0), 4
                    )
                    ex.release_inventory(reservation_id=str(oid))
                    st[oid_k] = None

        up_rem = float(st.get("up_rem") or 0.0)
        dn_rem = float(st.get("dn_rem") or 0.0)

        # Both legs sold -> book profit and re-arm!
        if up_rem <= 0.05 and dn_rem <= 0.05:
            return await self._finalize_cycle(harvester, st, "PRE_SPLIT_DUAL_MAKER_OVERROUND_FILLED", now_ts)

        bk_up, bk_dn = self._extract_shm_books_for_tokens(ft, str(st["up_token_id"]), str(st["down_token_id"]))
        if bk_up is None:
            bk_up = await ex.get_market_book_async(st["up_token_id"])
            if _is_clob_book_crossed(bk_up):
                bk_up = None
        if bk_dn is None:
            bk_dn = await ex.get_market_book_async(st["down_token_id"])
            if _is_clob_book_crossed(bk_dn):
                bk_dn = None

        # Asymmetric 1-leg fill: ONLY sweep remaining leg when strictly profitable (`net >= cost + $0.002`) — NEVER dump at a loss!
        if abs(up_rem - dn_rem) >= 4.95 and isinstance(bk_up, dict) and isinstance(bk_dn, dict):
            rem_tok = st["up_token_id"] if up_rem > dn_rem else st["down_token_id"]
            rem_sh = abs(up_rem - dn_rem)
            rem_bk = bk_up if up_rem > dn_rem else bk_dn
            bids_r = sorted(
                [(float(b["price"]), float(b["size"])) for b in (rem_bk.get("bids") or []) if float(b.get("size", 0)) > 0],
                key=lambda r: r[0],
                reverse=True,
            )
            if bids_r:
                b_top = bids_r[0][0]
                fee_r = (fr_st * ((b_top * (1.0 - b_top)) ** fe_st)) if fr_st > 0.0 else 0.0
                need_net = max(0.02, (float(st["cost_usd"]) - float(st["realized_cash_usd"])) / max(rem_sh, 1.0) + 0.002)
                if (b_top - fee_r) >= need_net:
                    await self._cancel_resting_asks(ex, st)
                    uw = await asyncio.to_thread(ex.execute_unwind_order, rem_tok, size=rem_sh, side="SELL", min_price=max(0.01, round(need_net, 2)), neg_risk=False)
                    if isinstance(uw, dict) and (uw.get("success") or uw.get("partial")):
                        m_u = float(uw.get("matched_size") or rem_sh)
                        c_u = float(uw.get("taking_amount") or (m_u * b_top)) - float(uw.get("fee_usd") or 0.0)
                        st["realized_cash_usd"] = round(float(st["realized_cash_usd"]) + max(0.0, c_u), 4)
                        if up_rem > dn_rem:
                            st["up_rem"] = round(max(0.0, up_rem - m_u), 4)
                        else:
                            st["dn_rem"] = round(max(0.0, dn_rem - m_u), 4)
                        if float(st["up_rem"]) <= 0.05 and float(st["dn_rem"]) <= 0.05:
                            return await self._finalize_cycle(harvester, st, "PRE_SPLIT_MAKER_TAKER_OVERROUND_COMPLETED", now_ts)

        paired = round(min(float(st.get("up_rem") or 0.0), float(st.get("dn_rem") or 0.0)), 2)
        if paired >= 5.0 and isinstance(bk_up, dict) and isinstance(bk_dn, dict):
            walk = _walk_dual_leg_overround_bids(bk_up.get("bids") or [], bk_dn.get("bids") or [], paired, fr_st, fe_st, fr_st, fe_st, 1.05)
            min_ovr_sw = 1.003 if fr_st == 0.0 else 1.004
            if walk.get("fillable") and float(walk.get("net_sum_per_share") or 0.0) >= min_ovr_sw:
                await self._cancel_resting_asks(ex, st)
                paired = round(min(float(st.get("up_rem") or 0.0), float(st.get("dn_rem") or 0.0)), 2)
                if paired >= 5.0:
                    u_res = await asyncio.to_thread(
                        ex.execute_atomic_box_overround_unwind,
                        f"PRESPLIT_{st['condition_id'][:10]}",
                        st["up_token_id"],
                        max(0.01, round(float(walk["min_px_a"]), 4)),
                        st["down_token_id"],
                        max(0.01, round(float(walk["min_px_b"]), 4)),
                        paired,
                        False,
                        False,
                        fr_st,
                        fe_st,
                        fr_st,
                        fe_st,
                    )
                    if (u_res or {}).get("success"):
                        la, lb = u_res["leg_a"], u_res["leg_b"]
                        net_a = float(la.get("taking_amount") or 0.0) - float(la.get("fee_usd") or 0.0)
                        net_b = float(lb.get("taking_amount") or 0.0) - float(lb.get("fee_usd") or 0.0)
                        st["realized_cash_usd"] = round(float(st["realized_cash_usd"]) + net_a + net_b, 4)
                        st["up_rem"] = round(max(0.0, float(st["up_rem"]) - paired), 4)
                        st["dn_rem"] = round(max(0.0, float(st["dn_rem"]) - paired), 4)
                        return await self._finalize_cycle(harvester, st, "PRE_SPLIT_OVERROUND_SWEEP", now_ts)
                    elif (u_res or {}).get("partial_leg_unwind"):
                        la, lb = (u_res or {}).get("leg_a") or {}, (u_res or {}).get("leg_b") or {}
                        if la.get("filled"):
                            m_a = float(la.get("matched_size") or paired)
                            st["realized_cash_usd"] = round(float(st["realized_cash_usd"]) + max(0.0, float(la.get("taking_amount") or 0.0) - float(la.get("fee_usd") or 0.0)), 4)
                            st["up_rem"] = round(max(0.0, float(st["up_rem"]) - m_a), 4)
                        if lb.get("filled"):
                            m_b = float(lb.get("matched_size") or paired)
                            st["realized_cash_usd"] = round(float(st["realized_cash_usd"]) + max(0.0, float(lb.get("taking_amount") or 0.0) - float(lb.get("fee_usd") or 0.0)), 4)
                            st["dn_rem"] = round(max(0.0, float(st["dn_rem"]) - m_b), 4)
                        await asyncio.to_thread(harvester.save_state)

        # Strictly gate naked dual Maker Asks off when `riskless_only_mode` is True (prevents 1-leg adverse sniping!)
        allow_dual_mkr = bool((snap or {}).get("enable_pre_split_dual_maker_asks", False)) and not bool((dir_snap or {}).get("riskless_only_mode", False))

        # Pre-expiry (`TTE <= 75s`) or dual-maker stale-spot safety merge -> $1.00/pair cash!
        if tte <= 75.0 or (allow_dual_mkr and not spot_fresh):
            await self._cancel_resting_asks(ex, st)
            paired = round(min(float(st.get("up_rem") or 0.0), float(st.get("dn_rem") or 0.0)), 2)
            if paired >= 4.99:
                m_res = await asyncio.to_thread(ex.attempt_onchain_complete_set_merge, st["condition_id"], min_pairs=paired, max_pairs=paired, neg_risk=False)
                if isinstance(m_res, tuple) and m_res[0]:
                    st["realized_cash_usd"] = round(float(st["realized_cash_usd"]) + float(m_res[1]), 4)
                    st["up_rem"] = round(max(0.0, float(st["up_rem"]) - float(m_res[1])), 4)
                    st["dn_rem"] = round(max(0.0, float(st["dn_rem"]) - float(m_res[1])), 4)
                    if float(st["up_rem"]) <= 0.05 and float(st["dn_rem"]) <= 0.05:
                        return await self._finalize_cycle(harvester, st, "PRE_SPLIT_PRE_EXPIRY_MERGED", now_ts)
            elif float(st.get("up_rem") or 0.0) <= 0.05 and float(st.get("dn_rem") or 0.0) <= 0.05:
                return await self._finalize_cycle(harvester, st, "PRE_SPLIT_PRE_EXPIRY_MERGED", now_ts)
            if tte <= -30.0:
                cid_h = str(st.get("condition_id") or "")
                exp_h = float(st.get("expiry_ts") or now_ts)
                rem_cost = max(0.0, float(st.get("cost_usd") or 0.0) - float(st.get("realized_cash_usd") or 0.0))
                legs_h = [("UP", str(st.get("up_token_id") or ""), float(st.get("up_rem") or 0.0)), ("DOWN", str(st.get("down_token_id") or ""), float(st.get("dn_rem") or 0.0))]
                tot_rem_sh = sum(s for _, _, s in legs_h if s > 0.05)
                for side_h, tok_h, sh_h in legs_h:
                    if sh_h > 0.05 and tok_h and hasattr(harvester, "active_positions"):
                        hid = f"PRESPLIT_SETTLE_{side_h}_{cid_h[:8]}_{int(now_ts)}"
                        alloc_cost = round(rem_cost * (sh_h / max(tot_rem_sh, 0.01)), 4)
                        if hasattr(harvester, "_make_single_leg_lock_pos"):
                            p_h = harvester._make_single_leg_lock_pos(
                                hid, "COMPLETE_SET", "PRE_SPLIT_OVERROUND_MACHINE_GUN", str(st.get("asset") or "BTC"),
                                "15m", cid_h, cid_h, tok_h, side_h, False, sh_h, alloc_cost, 0.0, 0.07, 1.0,
                                "crypto_fees_v2", exp_h, float(st.get("opened_ts") or now_ts), 0.0, None, True, unk=False,
                            )
                            p_h["box_id"] = f"PRESPLIT_SETTLE_{cid_h[:8]}_{int(now_ts)}"
                            p_h["is_dominance_box"] = tot_rem_sh > sh_h + 0.05
                            harvester.active_positions[hid] = p_h
                st.clear()
                st["cooldown_until"] = now_ts + 5.0
                await asyncio.to_thread(harvester.save_state)
            return None

        if not allow_dual_mkr:
            return "SUPERVISED"

        # Chainlink-anchored dual postOnly Maker Asks (`ask_up + ask_dn >= $1.012`)
        spot_now = float((ft or {}).get("spot_price") or (ft or {}).get("chainlink_spot") or st.get("open_spot") or 0.0)
        open_s = float(st.get("open_spot") or spot_now)
        if paired >= 5.0 and spot_now > 0.0 and open_s > 0.0:
            vol_t = max(0.0004, 0.0025 * math.sqrt(max(15.0, tte) / 900.0))
            p_up = min(0.88, max(0.12, _norm_cdf(math.log(spot_now / open_s) / vol_t)))
            tgt_up = min(0.95, max(0.06, round(math.ceil((p_up + 0.007) * 100.0) / 100.0, 2)))
            tgt_dn = min(0.95, max(0.06, round(math.ceil(((1.0 - p_up) + 0.007) * 100.0) / 100.0, 2)))
            if tgt_up + tgt_dn < 1.012:
                tgt_dn = min(0.96, round(1.012 - tgt_up, 2))
            need_repeg = (
                not st.get("up_ask_oid")
                or not st.get("dn_ask_oid")
                or abs(float(st.get("up_ask_px") or 0.0) - tgt_up) >= 0.02
                or abs(float(st.get("dn_ask_px") or 0.0) - tgt_dn) >= 0.02
            )
            if need_repeg and hasattr(ex, "post_maker_exit_order"):
                await self._cancel_resting_asks(ex, st)
                paired = round(min(float(st.get("up_rem") or 0.0), float(st.get("dn_rem") or 0.0)), 2)
                if paired >= 5.0:
                    r_u = await asyncio.to_thread(ex.post_maker_exit_order, token_id=st["up_token_id"], price=tgt_up, size=paired, side="SELL")
                    r_d = await asyncio.to_thread(ex.post_maker_exit_order, token_id=st["down_token_id"], price=tgt_dn, size=paired, side="SELL")
                    if (r_u or {}).get("success"):
                        st["up_ask_oid"] = r_u.get("orderID")
                        st["up_ask_px"] = float(r_u.get("price") or tgt_up)
                    if (r_d or {}).get("success"):
                        st["dn_ask_oid"] = r_d.get("orderID")
                        st["dn_ask_px"] = float(r_d.get("price") or tgt_dn)
                    await asyncio.to_thread(harvester.save_state)
        return "SUPERVISED"

    async def _finalize_cycle(self, harvester: Any, st: Dict[str, Any], reason: str, now_ts: float) -> str:
        from datetime import datetime, timezone

        realized = round(float(st.get("realized_cash_usd") or 0.0), 4)
        cost = round(float(st.get("cost_usd") or 0.0), 4)
        net_pnl = round(realized - cost, 4)
        opened_f = float(st.get("opened_ts") or now_ts)
        uniq_tid = f"PRESPLIT_{st.get('condition_id', 'BTC')[:10]}_{int(now_ts)}"
        is_noop_flat_merge = reason == "PRE_SPLIT_PRE_EXPIRY_MERGED" and abs(net_pnl) < 0.005
        rec = {
            "trade_id": uniq_tid,
            "box_id": uniq_tid,
            "is_dominance_box": False,
            "sleeve": "PRE_SPLIT_OVERROUND_MACHINE_GUN",
            "asset": str(st.get("asset") or "BTC"),
            "condition_id": str(st.get("condition_id") or ""),
            "token_id": f"{st.get('up_token_id')}|{st.get('down_token_id')}",
            "entry_shares": float(st.get("initial_shares") or 12.0),
            "notional_usd": cost,
            "fee_usd": 0.0,
            "payout_usd": realized,
            "net_pnl_usd": net_pnl,
            "estimated_maker_rebate_usd": float(st.get("rebate_est_usd") or 0.0),
            "won": bool(net_pnl > 0.005),
            "status": "CLOSED",
            "close_reason": reason,
            "entry_ts": opened_f,
            "exit_ts": now_ts,
            "entry_time_utc": datetime.fromtimestamp(opened_f, tz=timezone.utc).isoformat(),
            "settled_at_utc": datetime.fromtimestamp(float(now_ts), tz=timezone.utc).isoformat(),
        }
        if not is_noop_flat_merge:
            harvester.closed_positions.append(rec)
            harvester.closed_positions = harvester.closed_positions[-600:]
            if getattr(harvester, "risk_controller", None) is not None and hasattr(harvester.risk_controller, "record_trade_pnl"):
                try:
                    harvester.risk_controller.record_trade_pnl(net_pnl, is_non_directional=True)
                except Exception:
                    pass
        if getattr(harvester, "_last_known_collateral", None) is not None:
            harvester._last_known_collateral = float(harvester._last_known_collateral) + realized
        harvester.executor.invalidate_collateral_cache()
        harvester._pending_collateral_refresh = True
        st.clear()
        st["cooldown_until"] = now_ts + 2.0
        await asyncio.to_thread(harvester.save_state)
        logger.info(f"✓ [PRE-SPLIT CYCLE CLOSED] {reason} | Cost=${cost:.2f} -> Cash=${realized:.2f} | Net PnL=${net_pnl:+.2f}")
        return reason


def finish_nr2_subset_convert_arb(
    harvester: Any,
    cand: Dict[str, Any],
    *,
    sleeve_src: str,
    nrm_id: str,
    dedupe_k: str,
    retry_cd: Dict[str, float],
    budget: float,
    fee_bips: int,
    exp_ts: float,
    now_ts: float,
) -> Dict[str, Any]:
    """Fresh L2 book walk + `NegRiskAdapterV2.convertPositions` execution + `NR5` freeroll tail registration."""
    from datetime import datetime, timezone

    raw_no_legs = list(cand.get("no_legs") or [])
    raw_yes_sells = list(cand.get("liquid_yes_sells") or [])
    all_toks = [str(lg["token_id"]) for lg in raw_no_legs] + [str(yl["yes_token"]) for yl in raw_yes_sells if yl.get("yes_token")]
    custom_bk = "get_market_book" in getattr(harvester.executor, "__dict__", {})
    ws_bks = cand.get("ws_books") if not custom_bk else None
    if isinstance(ws_bks, dict) and (time.time() - float(cand.get("ws_books_ts") or 0.0)) <= 1.5 and all(isinstance(ws_bks.get(t), dict) for t in all_toks):
        bk_map = {t: ws_bks[t] for t in all_toks}
    elif not custom_bk and hasattr(harvester.executor, "get_market_books_batch"):
        bk_map = harvester.executor.get_market_books_batch(all_toks) or {}
    else:
        bk_map = {t: (harvester.executor.get_market_book(t) or {}) for t in all_toks}

    def _norm(ls: Any) -> List[Dict[str, float]]:
        return [
            {"price": float(x["price"] if isinstance(x, dict) else x[0]), "size": float(x["size"] if isinstance(x, dict) else x[1])}
            for x in (ls or [])
            if float(x.get("size", 0) if isinstance(x, dict) else x[1]) > 0
        ]

    avail_per_leg: List[float] = []
    best_asks: List[Tuple[Dict[str, Any], List[Dict[str, float]]]] = []
    for lg in raw_no_legs:
        asks_i = sorted(_norm((bk_map.get(str(lg["token_id"])) or {}).get("asks")), key=lambda r: r["price"])
        if not asks_i:
            return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:EMPTY_NO_ASK_BOOK"}
        avail_per_leg.append(sum(x["size"] for x in asks_i[:3]))
        best_asks.append((lg, asks_i))

    est_sum_px = max(0.50, sum(asks_i[0]["price"] for _, asks_i in best_asks))
    sh_int = int(math.floor(min(min(avail_per_leg) / 1.15, budget / est_sum_px)))
    if sh_int < 5:
        return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:MIN_SHARES"}

    from decimal import ROUND_CEILING

    _tick_cache = getattr(harvester.executor, "_tick_size_cache", None)
    if isinstance(_tick_cache, dict):
        for _t_bk, _bk_d in bk_map.items():
            _raw_mt = (_bk_d or {}).get("minimum_tick_size") if isinstance(_bk_d, dict) else None
            if _raw_mt is not None:
                try:
                    _tv = float(_raw_mt)
                    if any(abs(_tv - _vt) < 1e-9 for _vt in (0.1, 0.01, 0.005, 0.0025, 0.001, 0.0001)):
                        _tick_cache[str(_t_bk)] = _tv
                except Exception:
                    pass

    verified_no_legs: List[Dict[str, Any]] = []
    worst_no_cost_ps = 0.0
    for lg, asks_i in best_asks:
        cum_s, w_px = 0.0, asks_i[0]["price"]
        for lv in asks_i:
            w_px = lv["price"]
            cum_s += lv["size"]
            if cum_s >= sh_int:
                break
        if cum_s < sh_int:
            return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:INSUFFICIENT_NO_DEPTH"}
        tok_no_s = str(lg["token_id"])
        if hasattr(harvester.executor, "quantize_order_price"):
            w_px = float(harvester.executor.quantize_order_price(float(w_px), tok_no_s, rounding=ROUND_CEILING))
        fr_i = float(lg.get("fee_rate", 0.0) or 0.0)
        fe_i = float(lg.get("fee_exponent", 1.0) or 1.0)
        fee_i = fr_i * ((w_px * (1.0 - w_px)) ** fe_i) if fr_i > 0.0 else 0.0
        h_i = min(0.25, max(0.0, fee_i / max(w_px, 1e-6))) if fr_i > 0.0 else 0.0
        worst_no_cost_ps += w_px / max(1.0 - h_i, 1e-6)
        verified_no_legs.append({
            "token_id": tok_no_s,
            "market_id": str(lg.get("market_id") or ""),
            "condition_id": str(lg.get("condition_id") or ""),
            "question_index": int(lg["question_index"]),
            "label": str(lg.get("label") or f"NO_{lg['question_index']}"),
            "limit_price": w_px,
            "fee_rate": fr_i,
            "fee_exponent": fe_i,
        })

    eff_mult = 1.0 - max(0, fee_bips) / 10000.0
    verified_yes_sells: List[Dict[str, Any]] = []
    yes_net_ps = 0.0
    for yl in raw_yes_sells:
        y_tok = str(yl.get("yes_token") or "")
        bids_y = sorted(_norm((bk_map.get(y_tok) or {}).get("bids")), key=lambda r: r["price"], reverse=True)
        if not bids_y:
            return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:EMPTY_YES_BID_BOOK"}
        cum_y, min_b, gross_y = 0.0, bids_y[0]["price"], 0.0
        for lv in bids_y:
            take_y = min(lv["size"], sh_int - cum_y)
            gross_y += take_y * lv["price"]
            min_b = lv["price"]
            cum_y += take_y
            if cum_y >= sh_int - 1e-6:
                break
        if cum_y < sh_int - 1e-6:
            return {"executed": False, "reason": "FRESH_BOOK_WALK_REJECT:INSUFFICIENT_YES_BID_DEPTH"}
        vwap_y = gross_y / sh_int
        fr_y = float(yl.get("fee_rate", 0.0) or 0.0)
        fe_y = float(yl.get("fee_exponent", 1.0) or 1.0)
        fee_y = fr_y * ((vwap_y * (1.0 - vwap_y)) ** fe_y) if fr_y > 0.0 else 0.0
        yes_net_ps += max(0.0, (vwap_y - fee_y) * eff_mult)
        verified_yes_sells.append({
            "yes_token": y_tok,
            "min_bid_price": min_b,
            "bid_vwap": vwap_y,
            "fee_rate": fr_y,
            "fee_exponent": fe_y,
        })

    proceeds_ps = float(len(verified_no_legs) - 1) * eff_mult + yes_net_ps
    _cm_nr = str(cand.get("convert_mode") or "")
    _m1_verified = (
        _cm_nr == "NR_M1_DEAD_SEED_OVERROUND"
        and bool(cand.get("nr_m1_zero_loss_verified")) is True
        and len(verified_no_legs) == 1
        and len(verified_yes_sells) == 1
    )
    if _m1_verified:
        if worst_no_cost_ps >= (eff_mult - 0.001):
            return {"executed": False, "reason": f"FRESH_BOOK_WALK_REJECT:M1_COST_ABOVE_PAR:{worst_no_cost_ps:.4f}"}
        from src.polymarket_research.holistic_strategy_governance import get_unleashed_v5_tier_profile
        _eq_nr_m1 = float(getattr(harvester, "_last_known_collateral", None) or (200.0 if getattr(harvester, "dry_run", False) else max(25.0, budget))) + sum(
            float(p.get("notional_usd", 0.0) or 0.0) for p in getattr(harvester, "active_positions", {}).values()
        )
        _max_m1_h = float(get_unleashed_v5_tier_profile(_eq_nr_m1)["max_lockup_hours"])
        if exp_ts > now_ts and (exp_ts - now_ts) > (_max_m1_h * 3600.0 + 1e-6):
            return {"executed": False, "reason": f"LOW_CAPITAL_VELOCITY_LONG_TTE:{(exp_ts - now_ts) / 3600.0:.2f}h>{_max_m1_h:.1f}h"}
    if _cm_nr == "NR5_NEGATIVE_COST_FREEROLL":
        min_edge_req = 0.0020
    elif _cm_nr in {"NR4_FULL_SWEEP", "NR_M1_DEAD_SEED_OVERROUND"}:
        min_edge_req = 0.0035
    else:
        min_edge_req = 0.0045 if not verified_yes_sells else 0.0065
    if (proceeds_ps - worst_no_cost_ps) < min_edge_req:
        return {"executed": False, "reason": f"FRESH_BOOK_WALK_REJECT:EDGE_BELOW_MIN:{proceeds_ps - worst_no_cost_ps:.4f}"}

    cid_conv = str(cand.get("box_id") or f"NRCONV_{int(now_ts)}")
    _nr_exec_kwargs: Dict[str, Any] = dict(
        convert_id=cid_conv,
        neg_risk_market_id=nrm_id,
        no_legs=verified_no_legs,
        shares=float(sh_int),
        max_no_cost_per_share=worst_no_cost_ps + 0.002,
        liquid_yes_sells=verified_yes_sells,
        fee_bips=fee_bips,
    )
    if _m1_verified:
        _nr_exec_kwargs["nr_m1_zero_loss_verified"] = True
        _nr_exec_kwargs["nr_m1_mode"] = _cm_nr
        _nr_exec_kwargs["surviving_yes_legs"] = list(cand.get("surviving_yes_legs") or [])
    c_res = harvester.executor.execute_negrisk_subset_convert_arb(**_nr_exec_kwargs)
    with getattr(harvester, "_state_save_lock", None) or harvester._GLOBAL_STATE_SAVE_LOCK:
        if not c_res.get("success"):
            if dedupe_k and not c_res.get("legged_out") and not c_res.get("outcome_unknown"):
                retry_cd[dedupe_k] = now_ts + 9.5
            elif dedupe_k:
                harvester._record_seen_d1_box_key(dedupe_k)
            for r_idx, resid in enumerate(c_res.get("residuals") or []):
                if float(resid.get("residual_shares") or 0.0) > 0.01 or resid.get("unwind_outcome_unknown"):
                    r_tid = f"{cid_conv}_LEG_RESID_{r_idx}"
                    harvester.active_positions[r_tid] = harvester._make_single_leg_lock_pos(
                        r_tid, "NEGRISK_CONVERT_RESIDUAL", sleeve_src, "NEGRISK", "nr_conv",
                        str(resid.get("market_id") or ""), str(resid.get("condition_id") or ""), str(resid["token_id"]),
                        "NO", True, float(resid["residual_shares"]),
                        round(float(resid["residual_shares"]) * float(resid["price"]), 4),
                        0.0, 0.0, 1.0, "zero_fees", exp_ts, now_ts, 0.0, resid.get("orderID"), False,
                        unk=bool(resid.get("unwind_outcome_unknown")),
                    )
            if c_res.get("outcome_unknown"):
                harvester._refresh_global_halt()
            harvester.save_state()
            return {"executed": False, "reason": f"NR_CONVERT_ABORT:{c_res.get('error')}", "result": c_res}

        if dedupe_k:
            retry_cd.pop(dedupe_k, None)
            harvester._record_seen_d1_box_key(dedupe_k)
        harvester.executor.invalidate_collateral_cache()
        harvester._pending_collateral_refresh = True
        if c_res.get("convert_executed") and c_res.get("held_guaranteed_complete_set"):
            # Fallback zero-loss complete-set hold when YES bid slipped during Polygon block confirmation:
            # Consolidate surviving YES legs as a MULTI_LEG_BUNDLE under shared box_id=cid_conv so OTM legs never record standalone losses.
            sv_legs = [
                sv for sv in (c_res.get("held_surviving_yes_legs") or cand.get("surviving_yes_legs") or [])
                if isinstance(sv, dict) and sv.get("yes_token")
            ]
            spent_c = float(c_res.get("spent_usd") or 0.0)
            n_sv = max(1, len(sv_legs))
            is_multi_sv = len(sv_legs) >= 2
            for s_idx, sv in enumerate(sv_legs):
                s_tid = f"{cid_conv}_M1_GUAR_YES_{s_idx}"
                s_sh = float(sv.get("shares") or round(float(c_res["shares"]) * eff_mult, 4))
                leg_not = round(spent_c - round(spent_c / n_sv, 2) * (n_sv - 1), 2) if s_idx == (n_sv - 1) else round(spent_c / n_sv, 2)
                pos_sv = harvester._make_single_leg_lock_pos(
                    s_tid, "MULTI_LEG_BUNDLE" if is_multi_sv else "SINGLE_LEG_LOCK", sleeve_src, "NEGRISK", "nr_m1_guar_hold",
                    str(sv.get("market_id") or ""), str(sv.get("condition_id") or ""), str(sv["yes_token"]),
                    "YES", True, s_sh, leg_not, 0.0, 0.0, 1.0, "zero_fees", exp_ts, now_ts, 0.0, None, True, unk=False,
                )
                if is_multi_sv:
                    pos_sv["box_id"] = cid_conv
                    pos_sv["box_expected_legs"] = n_sv
                    pos_sv["is_dominance_box"] = True
                    pos_sv["is_single_leg_lock"] = False
                    pos_sv["box_cost_net"] = round(spent_c / max(0.01, s_sh), 5)
                    pos_sv["box_total_cost_usd"] = round(spent_c, 4)
                    pos_sv["shares"] = s_sh
                harvester.active_positions[s_tid] = pos_sv
            logger.info(
                f"✓ [NR_M1 COMPLETE-SET FALLBACK LOCKED] {cid_conv} ({sleeve_src}) | {c_res['shares']:.0f} sh | "
                f"YES bid slipped mid-block -> holding {len(sv_legs)} surviving YES legs for guaranteed +${c_res.get('net_profit_usd', 0.0):.2f} at resolution."
            )
        elif c_res.get("convert_executed"):
            net_pnl = round(float(c_res.get("net_profit_usd") or 0.0), 4)
            exit_c = time.time()
            spent_c = float(c_res["spent_usd"])
            tail_toks = cand.get("retained_tail_tokens") or []
            closed_rec = {
                "trade_id": cid_conv,
                "box_id": cid_conv,
                "sleeve": sleeve_src,
                "asset": "NEGRISK",
                "market_id": str(verified_no_legs[0].get("market_id") or nrm_id[:16]),
                "token_id": "|".join(x["token_id"] for x in verified_no_legs),
                "entry_shares": float(c_res["shares"]),
                "notional_usd": spent_c,
                "fee_usd": 0.0,
                "payout_usd": round(spent_c + net_pnl, 4),
                "net_pnl_usd": net_pnl,
                "won": net_pnl >= 0.0,
                "status": "CLOSED",
                "close_reason": "ONCHAIN_NEGRISK_CONVERT_COMPLETED",
                "convert_tx_hash": c_res.get("convert_tx_hash"),
                "adapter_used": c_res.get("adapter_used"),
                "retained_tail_tokens": tail_toks,
                "entry_ts": now_ts,
                "exit_ts": exit_c,
                "entry_time_utc": datetime.fromtimestamp(float(now_ts), tz=timezone.utc).isoformat(),
                "settled_at_utc": datetime.fromtimestamp(float(exit_c), tz=timezone.utc).isoformat(),
            }
            harvester.closed_positions.append(closed_rec)
            harvester.closed_positions = harvester.closed_positions[-600:]
            if hasattr(harvester, "risk_controller"):
                try:
                    harvester.risk_controller.record_trade_pnl(net_pnl, is_non_directional=True)
                except Exception:
                    pass
            for t_idx, rt in enumerate(tail_toks):
                if isinstance(rt, dict) and rt.get("yes_token"):
                    t_id_f = f"{cid_conv}_FREEROLL_{t_idx}"
                    f_sh = round(float(c_res["shares"]) * max(0.0, 1.0 - float(cand.get("fee_bips", 0) or 0) / 10000.0), 4)
                    harvester.active_positions[t_id_f] = harvester._make_single_leg_lock_pos(
                        t_id_f, "SINGLE_LEG_LOCK", sleeve_src, "NEGRISK", "freeroll",
                        str(rt.get("market_id") or ""), str(rt.get("condition_id") or ""), str(rt["yes_token"]),
                        "YES", True, f_sh, 0.0, 0.0, 0.0, 1.0, "zero_fees", exp_ts, now_ts, 0.0, None, True, unk=False,
                    )
            release_recycled_box_dedupe_keys(harvester, None, extra_keys=[dedupe_k], cooldown_sec=2.5)
            logger.info(
                f"✓ [NEGRISK CONVERT COMPLETED] {cid_conv} ({sleeve_src}) | {c_res['shares']:.0f} sh | "
                f"m={c_res['m_no_legs']} | net_pnl=${net_pnl:+.2f} | tx={c_res.get('convert_tx_hash')}"
            )
        else:
            l_fills = list(c_res.get("leg_fills") or [])
            is_multi_no = len(l_fills) >= 2
            tot_no_cost = round(sum(float(x["matched_shares"]) * float(x["price"]) for x in l_fills), 4)
            min_no_sh = min((float(x["matched_shares"]) for x in l_fills), default=0.0)
            for l_idx, lf in enumerate(l_fills):
                l_tid = f"{cid_conv}_HOLD_NO_{l_idx}"
                sh_l = float(lf["matched_shares"])
                px_l = float(lf["price"])
                q_idx = lf.get("question_index")
                if q_idx is None and l_idx < len(verified_no_legs):
                    q_idx = verified_no_legs[l_idx].get("question_index")
                pos_no = harvester._make_single_leg_lock_pos(
                    l_tid, "MULTI_LEG_BUNDLE" if is_multi_no else "SINGLE_LEG_LOCK", sleeve_src, "NEGRISK", "nr_conv_hold",
                    str(lf.get("market_id") or ""), str(lf.get("condition_id") or ""), str(lf["token_id"]),
                    "NO", True, sh_l, round(sh_l * px_l, 4), 0.0, 0.0, 1.0, "zero_fees",
                    exp_ts, now_ts, 0.0, lf.get("orderID"), True, unk=False,
                )
                pos_no["box_id"] = cid_conv
                pos_no["box_expected_legs"] = len(l_fills)
                pos_no["pending_negrisk_convert"] = True
                pos_no["neg_risk_market_id"] = nrm_id
                if q_idx is not None:
                    pos_no["question_index"] = int(q_idx)
                pos_no["convert_fee_bips"] = int(fee_bips)
                if l_idx == 0 and verified_yes_sells:
                    pos_no["pending_liquid_yes_sells"] = [dict(y) for y in verified_yes_sells]
                if is_multi_no:
                    pos_no["is_dominance_box"] = True
                    pos_no["is_single_leg_lock"] = False
                    pos_no["box_cost_net"] = round(tot_no_cost / max(0.01, min_no_sh), 5)
                    pos_no["box_total_cost_usd"] = tot_no_cost
                    pos_no["shares"] = sh_l
                harvester.active_positions[l_tid] = pos_no
        harvester.save_state()
    return {"executed": True, "result": c_res, "leg_trade_ids": []}
