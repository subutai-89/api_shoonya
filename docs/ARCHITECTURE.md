# Architecture & Invariants

This document defines non-negotiable architectural rules.
Violating these rules may introduce silent trading bugs.

---

## Market Data Model

### Token Identity Rule
- `tk` is the sole runtime identity
- All routing, filtering, and logic is token-based

### Instrument Name Rule
- Instrument names are display-only
- The ONLY valid source is:
  market_state[token]["instrument_name"]

### tk / tf Semantics
- `tk` = full snapshot, establishes truth
- `tf` = incremental diff, never establishes identity
- `tf` without a prior `tk` must be ignored

### Price Semantics
- Missing `lp` in `tf` means unchanged
- `lp` must always be carried forward

---

## Strategy Model

- Strategies are token-scoped
- StrategyEngine is symbol-agnostic
- Filtering happens inside the strategy

---

## Application Responsibilities

- Humans configure by instrument name
- Application resolves instrument → token once
- Runtime is token-only

---

## Rules

### Market Data & Identity Rules (CRITICAL)

#### Rule MD-1: Token is the ONLY identity
- `tk` is the primary key
- All routing, filtering, strategy logic uses `tk`
- Instrument names are never used for logic

Correct:
    if tick["tk"] != strategy.meta.symbol:
        return

Incorrect:
    if tick["raw"]["ts"] == "CRUDEOIL16DEC25P5200":
        ...

#### Rule MD-2: Instrument name is display-only
- Stored once from `tk`
- Used only for logs / prints / debugging
- Never trusted for correctness

IMPORTANT
The ONLY source of instrument name is:
    market_state[token]["instrument_name"]

#### Rule MD-3: tk establishes truth, tf only mutates
- `tk` → full snapshot, identity, baseline
- `tf` → partial updates only
- `tf` must never:
  - introduce new instruments
  - redefine identity
  - be processed without a prior `tk`

#### Rule MD-4: lp carry-forward is mandatory
- `tf` may omit `lp`
- Missing `lp` means unchanged
- Never treat missing `lp` as zero or invalid

---

### Strategy Rules

#### Rule ST-1: Strategies are token-scoped
- A strategy reacts to exactly one token
- Filtering happens inside the strategy

#### Rule ST-2: StrategyEngine is symbol-agnostic
- Dispatches ticks blindly
- Knows nothing about markets or instruments

#### Rule ST-3: StrategyContext must be token-pure
- ctx.append_tick() must only receive ticks for its token
- Enforced defensively in StrategyContext

---

### StrategyContext Invariants

- Bound to exactly ONE token (self.symbol)
- append_tick() rejects mismatched tokens
- Receives merged tk/tf ticks
- Instrument names are display-only

---

### Application / Configuration Rules

#### Rule APP-1: Humans configure by instrument name
- Humans never need tokens
- Tokens are resolved once

#### Rule APP-2: Instrument → token resolution happens ONCE
- In application.py
- Before websocket subscription
- Fail fast if mapping fails

#### Rule APP-3: Runtime is token-only
- No component re-resolves symbols
- No component relies on instrument names


## Design Philosophy

- Loud failures > silent corruption
- Centralize broker quirks
- Token purity everywhere
- Strategies stay simple and deterministic