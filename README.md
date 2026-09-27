# IronCore v2.4.0 — Canonical Backtesting & Execution Engine

## IronCore's Contract

> [!IMPORTANT]
> **IronCore is an execution/accounting engine, not an alpha validator.**
>
> It does not determine whether a strategy is profitable.  
> It determines what the specified strategy would have experienced under the frozen data, signal, risk, and execution assumptions.
>
> Any change to execution semantics, accounting, provenance, intrabar convention, queue model, or state transitions requires a new engine version and invalidates direct comparison with results produced by prior versions.

---

## Architectural Guarantees

1. **Strict Point-In-Time (PIT) Boundary**: Rebalancing costs, footprint impact, and adverse selection are evaluated strictly using completed historical bars (bar $t$ for execution at $t+1$).
2. **Causal Next-Subbar Passive Queue**: Passive limit orders placed at subbar $s$ enter the book and are strictly evaluated at $s+1$ or later.
3. **Pessimistic Intrabar Path Convention (`PESSIMISTIC_WORST_CASE:v1`)**: When stops and profit targets are simultaneous in subbar OHLC ranges, stop-loss triggers first.
4. **Gap Slippage Model (`30pct:v1`)**: Subbar gap-through-stop penetrations incur deterministic 30% gap slippage.
5. **Separated Friction Buckets**: Pure exchange fees, adverse selection markout, and market impact are segregated with exact accounting conservation ($\text{Equity}_{t+1} = \text{Equity}_t + \text{NetPnL}_t$).
6. **Bitwise Raw Provenance**: Matrix fingerprints are computed via `hash_array_raw` (preserving shape, dtype, and canonical contiguous C-order bytes with NaN sensitivity).
7. **Cross-Process Determinism**: Execution random draws derive from an immutable SHA-256 event-identity seed:
   $$\text{Seed} = \text{SHA256}(\text{master\_seed} \parallel \text{bar} \parallel \text{subbar} \parallel \text{symbol} \parallel \text{order\_gen} \parallel \text{attempt})$$
8. **Audit-Grade Complete Event Journal**: Every execution-affecting state transition (`ORDER_CREATED`, `PASSIVE_FILL`, `PARTIAL_PASSIVE_FILL`, `TAKER_TIMEOUT`, `STOP_LOSS`, `TAKE_PROFIT`, `ORDER_CANCELLED`, `COOLDOWN_CANCEL`, `POSITION_OPEN/ADD/REDUCE/FLIP/FLAT`) emits a canonical JSON-serializable record with SHA-256 fingerprinting.
9. **Fail-Closed Execution Gate 8**: Maker parity checks require empirical sample size $N \ge 50$, maker floor $\ge 20\%$, and modeled vs. empirical divergence $\le 15\text{pp}$.
