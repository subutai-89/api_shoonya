# Tick Contract

This document defines the **non-negotiable tick contract** used across the entire
system: live trading, backtesting, mocks, and replays.

Any component that produces, transforms, or consumes ticks MUST obey this contract.
Violating it will introduce subtle and dangerous trading bugs.

---

## 1. Definitions

### 1.1 Token (tk)

- `tk` is the unique, immutable identifier for an instrument at runtime
- All logic is token-based
- Tokens are treated as opaque strings
- Tokens must never be inferred or guessed

### 1.2 Instrument Name (ts)

- `ts` is a human-readable instrument name
- Examples:
  - CRUDEOIL16DEC25P5200
  - GOLDTEN31DEC25
- Instrument names are display-only
- Instrument names are NEVER used for logic

---

## 2. Tick Types

Shoonya emits two relevant tick types.

### 2.1 tk — Full Snapshot Tick

Characteristics:
- First tick for a token
- Establishes identity and baseline state
- Contains a full market snapshot

Required fields:
- t = "tk"
- tk = token
- ts = instrument name
- lp = last traded price (string or numeric)

Behavior:
- tk establishes truth
- tk overwrites any previous snapshot for the token
- tk MUST be received before any tf is processed

### 2.2 tf — Incremental / Delta Tick

Characteristics:
- Subsequent updates after tk
- Partial updates only
- May omit fields

Required fields:
- t = "tf"
- tk = token

Behavior:
- tf NEVER establishes identity
- tf ONLY mutates existing state
- tf without a prior tk MUST be ignored

---

## 3. Price Semantics (CRITICAL)

### 3.1 lp Field Rules

- lp represents the last traded price
- lp may be missing in tf
- Missing lp means “unchanged price”

Rules:
- Missing lp MUST be carried forward
- Missing lp MUST NOT be treated as zero
- Missing lp MUST NOT invalidate the tick

This rule applies equally to:
- Live trading
- Backtests
- Mocks
- Replays

---

## 4. market_state Contract

market_state is the single source of truth for market data.

Structure:
- Keyed by token
- One snapshot per token

Responsibilities:
- Store latest known state per token
- Preserve raw Shoonya values
- Track last known lp for carry-forward

Rules:
- tk replaces the entire snapshot
- tf merges into the existing snapshot
- market_state must never contain partial identity

Instrument name rule:
- Stored once from tk
- Source: market_state[token]['instrument_name']
- Never trusted for correctness

---

## 5. Normalized Tick Format

Downstream consumers (StrategyEngine, strategies, backtests) receive
normalized ticks with the following shape:

- t  : "tk" or "tf"
- e  : exchange
- tk : token
- lp : float or None
- raw: original Shoonya message (unchanged)

Guarantees:
- lp is numeric if available
- raw is never mutated
- raw may contain extra fields safely

---

## 6. Strategy Routing Rules

### 6.1 Token Purity

- Each strategy is bound to exactly ONE token
- StrategyContext.symbol == token
- StrategyContext must never accept other tokens

Enforcement:
- StrategyEngine routes only matching tokens
- StrategyContext.append_tick rejects mismatches loudly

### 6.2 No Instrument Logic

Strategies MUST NOT:
- Filter by instrument name
- Depend on ts for correctness
- Assume ts is reliable

Instrument names may be used ONLY for:
- Logging
- Debug prints
- Visual inspection

---

## 7. Error Handling Rules

- tf before tk → ignore
- Missing lp → carry forward
- Token mismatch → hard error in context
- Unknown message types → log and ignore

Silent failures are forbidden.

---

## 8. Cross-Environment Consistency

This tick contract MUST behave identically across:

- Live trading
- Backtesting
- Simulation
- Mock WebSocket feeds
- Historical replay

Any divergence is a bug.

---

## 9. Design Philosophy

- Tokens are truth
- Deltas are incomplete
- Missing data means unchanged
- Debug visibility beats cleverness
- Correctness beats elegance

This contract is intentionally strict.
Relaxing it will break trading correctness.
