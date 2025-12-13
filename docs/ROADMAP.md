# Project Roadmap

This document defines the scope, priorities, and phased roadmap for the project.
It is intended to align development decisions and avoid scope creep while ensuring
the system remains production-grade and extensible.

---

## Vision

Build a robust, token-correct, strategy-driven trading framework that supports:
- Live market data ingestion
- Deterministic strategy execution
- Reliable backtesting and forward testing
- Gradual transition to automated live trading
- Strong observability and debuggability

The project should evolve incrementally from a minimal, correct core into a
full-featured trading system.

---

## Guiding Principles

- Correctness over features
- Token-first, symbol-agnostic runtime
- Minimal refactors, minimal breakage
- Strong invariants documented in markdown
- Same code paths for live, backtest, and forward-test wherever possible
- Humans configure by instrument name; runtime is token-only

---

## Phase 0 — Foundation (COMPLETED / IN PROGRESS)

Goal: Ensure the system is architecturally correct and safe.

Completed / Mostly Completed:
- WebSocketManager with correct tk / tf merge semantics
- Token-based identity enforcement
- Instrument name treated as display-only
- StrategyEngine with queue + worker model
- StrategyContext bound to exactly one token
- Context-level rejection of wrong-token ticks
- Architecture, runtime flow, tick contract documentation
- Verbose logging and heartbeat monitoring

Exit Criteria:
- No ambiguity around tk vs tf
- No strategy can accidentally consume wrong-token data
- All routing rules documented and enforced in code

---

## Phase 1 — Minimal Viable Trading Engine (MVP)

Goal: A usable system for running and validating single-instrument strategies.

Must-Haves:
- Stable live tick ingestion
- Deterministic strategy execution
- Correct price history in StrategyContext
- Order placement plumbing (even if mocked)
- Risk policy hooks enforced at order time
- Clean startup and shutdown lifecycle

Deliverables:
- One or two reference strategies (e.g. momentum)
- Clear strategy configuration pattern
- Ability to run multiple strategies simultaneously (token-scoped)
- Logs sufficient to debug strategy decisions

Not Included Yet:
- Backtesting
- UI
- Multi-instrument strategies

---

## Phase 2 — Backtesting Engine

Goal: Validate strategies offline using the same logic as live trading.

Must-Haves:
- Backtest data loader (CSV / Parquet)
- Replay engine that emits tk/tf-equivalent ticks
- Same StrategyEngine + StrategyContext code paths
- Deterministic, repeatable results
- Performance metrics (PnL, drawdown, win rate)

Important Constraints:
- No strategy code changes between live and backtest
- Same tick contract as live
- Time control must be explicit (no wall-clock leaks)

Deliverables:
- Backtest runner CLI
- Backtest reports (JSON + optional plots)
- Comparison between strategies

---

## Phase 3 — Strategy Development & Analytics

Goal: Make it easier to build, analyze, and improve strategies.

Features:
- Extended indicators (volume, OI, VWAP, etc.)
- Better performance reporting
- Trade logs and decision logs
- Exportable data for notebooks
- Debug modes for step-by-step replay

Optional:
- Lightweight charting (price + signals)
- Strategy parameter sweeps

---

## Phase 4 — Options & Derivatives Support

Goal: Expand beyond simple price-based strategies.

Features:
- Option chain ingestion
- ATM / OTM / ITM classification
- Greeks (delta, gamma, vega, theta)
- Multi-leg strategies
- StrategyContext extensions for derivatives

Constraints:
- Token identity rules must still hold
- No symbol-based shortcuts

---

## Phase 5 — Forward Testing & Paper Trading

Goal: Run strategies live without real capital.

Features:
- Paper trading mode
- Simulated fills with realistic slippage
- Margin and risk simulation
- Long-running deployments

Deliverables:
- Forward-test reports
- Stability metrics
- Failure and recovery testing

---

## Phase 6 — Live Trading Automation

Goal: Controlled transition to real money.

Features:
- Strict risk enforcement
- Capital allocation per strategy
- Kill switches
- Audit logs
- Broker failure handling

Non-Negotiable:
- One-click disable for any strategy
- Full traceability of every order

---

## Phase 7 — UI & Observability

Goal: Visibility into what the system is doing.

Features:
- Live dashboards
- Strategy state visualization
- PnL tracking
- Order status monitoring
- Alerts and notifications

UI is explicitly low priority until the core is stable.

---

## Out of Scope (For Now)

- High-frequency trading
- Microsecond latency optimization
- Arbitrage across venues
- Complex portfolio optimization
- Fully automated strategy generation

---

## Progress Tracking

This roadmap should be updated when:
- A phase is completed
- Scope changes materially
- New invariants are introduced

Documentation updates are considered part of “done”.

---

End of ROADMAP.md
