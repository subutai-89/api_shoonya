# Project Scope & Boundaries

This document defines the **explicit scope, boundaries, and priorities** of the project.
It exists to prevent scope creep, clarify intent, and align all future work with a
shared understanding of what this system is (and is not).

This file should be read alongside:
- ROADMAP.md
- ARCHITECTURE.md
- PROJECT_PREFERENCES.md

---

## Core Intent

The project is a **modular trading research and execution platform** designed to:

- Ingest real-time market data reliably
- Process data deterministically using strategies
- Validate strategies via backtesting and forward testing
- Progress cautiously toward automated trading
- Provide transparency and debuggability at every stage

The system prioritizes **correctness, traceability, and safety** over speed or feature count.

---

## In-Scope (Current & Planned)

### 1. Market Data Ingestion

- Live tick ingestion via Shoonya WebSocket
- Snapshot + delta (`tk` / `tf`) model
- Token-based identity
- Instrument name resolution for display only
- Heartbeat and liveness monitoring
- Mock WebSocket for deterministic testing

This is **foundational and non-negotiable**.

---

### 2. Strategy Execution Engine

- StrategyEngine dispatching normalized ticks
- Token-scoped strategies
- Per-strategy execution throttling
- Isolated strategy failures
- Clean lifecycle (start / stop)

Strategies:
- React only to their bound token
- Operate on clean price series
- Produce signals deterministically

---

### 3. Strategy Context & State

- One StrategyContext per strategy
- Exactly one token per context
- Rolling price windows
- Position, PnL, and performance tracking
- No cross-instrument contamination

This layer ensures **logical purity**.

---

### 4. Backtesting Engine (Planned)

- Reuse live strategy code
- Inject historical data instead of live ticks
- Support CSV / structured historical feeds
- Maintain live/backtest parity
- Deterministic replay

Backtesting is a **first-class requirement**, not an afterthought.

---

### 5. Forward Testing / Paper Trading (Planned)

- Live data + simulated execution
- No real orders placed
- Realistic latency and fills (eventually)
- Risk policies enforced identically to live trading

This is the bridge between backtest and live.

---

### 6. Order Management & Risk Enforcement

- Centralized OrderManager
- Strategy-tagged orders
- RiskPolicy enforcement
- Portfolio-aware routing
- One source of truth for order state

Live order placement will only be enabled **after sufficient validation**.

---

### 7. Multi-Strategy & Multi-Instrument Support

- Multiple strategies running simultaneously
- Multiple instruments subscribed in parallel
- Clean routing by token
- No shared mutable state between strategies

Concurrency correctness is required.

---

### 8. Observability & Diagnostics

- Verbose logging modes
- Tick printing with resolved instrument names
- Performance reports
- Trade statistics
- Debug-first design

Future extensions:
- Charts
- Dashboards
- UI overlays

---

## Explicitly Out of Scope (For Now)

These items are **intentionally deferred**:

### 1. Complex UI / Frontend

- No web UI initially
- No heavy visualization frameworks
- No real-time dashboards yet

CLI + logs + reports are sufficient for MVP.

---

### 2. High-Frequency / Ultra-Low Latency Trading

- No microsecond optimizations
- No co-location assumptions
- No tick-to-trade latency guarantees

Correctness > speed.

---

### 3. Broker Abstraction Explosion

- Focused primarily on Shoonya initially
- Avoid premature multi-broker abstractions
- Additional brokers only after core stabilizes

---

### 4. Advanced Options Greeks (Deferred)

- Options strategies are planned
- Greeks, ATM/OTM classification deferred
- Underlying infra must stabilize first

---

### 5. ML / AI-Based Strategies

- No machine learning pipelines
- No feature engineering frameworks
- No model training infra

May be revisited after deterministic foundation is solid.

---

## Non-Goals

This project is NOT:

- A plug-and-play retail trading bot
- A signal-selling platform
- A black-box execution engine
- A fully managed trading product

It is a **research-grade system** evolving carefully toward production readiness.

---

## MVP Definition

The MVP is considered complete when:

- Live ticks are ingested correctly
- Strategies process only their bound tokens
- Backtests can replay historical data
- Forward tests simulate execution
- Logs and reports clearly explain behavior
- No silent data corruption exists

Live trading is **not part of MVP**.

---

## Success Criteria

The project is succeeding if:

- Bugs are easy to trace
- Behavior is explainable post-fact
- Strategy results are reproducible
- Adding strategies does not destabilize the system
- Contributors understand the rules quickly

---

## Scope Discipline Rule

If a proposed change:
- Expands scope significantly
- Blurs system boundaries
- Introduces implicit behavior
- Breaks live/backtest parity

It must be deferred, documented, or rejected.

---

End of PROJECT_SCOPE.md
