# CURRENT STATE

This document captures the **current snapshot** of the project at this point in time.
It exists to provide continuity across refactors, contributors, and LLM threads.

---

## What Is Working Today

- Live Shoonya WebSocket connection
- Correct handling of `tk` (snapshot) and `tf` (delta) ticks
- Proper merge semantics with `lp` carry-forward
- Per-token `market_state` with stable snapshots
- StrategyEngine dispatching normalized ticks
- StrategyContext enforcing token purity
- Multiple instruments supported concurrently
- Clear debug visibility via verbose & print_ticks modes

---

## Recently Fixed / Locked In

- Correct interpretation of `tk` vs `tf`
- Prevention of price discontinuities due to missing `lp`
- Explicit rule: StrategyContext is bound to exactly ONE token
- Token-only routing in StrategyEngine
- Instrument names treated as display-only
- Heartbeat warnings made meaningful
- Logging adjusted to expose Shoonya mismatches safely

These are now **contractual behaviors**.

---

## Known Limitations (Accepted for Now)

- No formal test suite yet
- No backtest engine yet
- StrategyEngine currently assumes single-token strategies
- No historical data replay
- No charting / visualization
- No persistent logs or metrics store
- Order lifecycle partially implemented

These are intentional and tracked in ROADMAP.md.

---

## Immediate Next Goal

### Phase 1: Testing & Validation

- Unit tests for:
  - tk/tf merge behavior
  - lp carry-forward
  - StrategyContext token rejection
  - StrategyEngine routing correctness
- Assertion of invariants defined in ARCHITECTURE.md
- Regression safety before adding features

No new features should be added before this phase is complete.

--- 

## “Upcoming Phases (Context Only)”

### Phase 2: Backtesting Engine (planned, not started)

### Phase 3: Order Lifecycle & Risk (planned, not started)

---

## Mental Model

At this stage, the project is a **correct data pipeline** with:
- stable semantics
- explicit contracts
- controlled scope

The focus now shifts from fixing bugs to **preventing regressions**.

---

## Last Updated

This snapshot reflects the state immediately after:
- architecture finalization
- documentation consolidation
- token purity enforcement
- roadmap definition
