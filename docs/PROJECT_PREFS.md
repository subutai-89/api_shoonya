# Project Preferences & Working Agreement

This document captures **project-specific preferences, constraints, and working
agreements** so that future contributors (including future ChatGPT threads)
can quickly align with how this repository is intended to evolve.

This file is as important as architecture rules — it governs *how* changes are made,
not just *what* is built.

---

## Purpose of This Document

- Preserve context across time and contributors
- Avoid repeating architectural debates
- Prevent accidental large refactors
- Ensure changes remain aligned with the project’s intent
- Act as a “contract” between the maintainer and contributors

---

## Formatting Preferences (VERY IMPORTANT)

### Markdown Generation Rules

When generating `.md` files for this repository:

- Output MUST be wrapped in a **single code block**
- Use **plain text** inside the code block
- Use **ATX headers** (`#`, `##`, `###`)
- Use hyphens (`-`) for bullet points
- NO markdown code fences inside the document
- NO backticks inside content (unless explicitly requested)
- Safe to paste verbatim into `docs/*.md`

If formatting breaks, regenerate rather than partially patch.

---

## Code Change Philosophy

### Minimal Refactors Only

Strong preference for:
- Small, incremental changes
- Clearly scoped fixes
- Easy reversibility

Avoid:
- Renaming public methods unnecessarily
- Moving files without strong justification
- Large refactors that mix behavior changes with cleanup
- “While we’re here” changes

If a refactor is needed:
- Explain *why*
- Do it in isolation
- Keep behavior identical unless explicitly intended

---

## Downstream Safety Is Critical

Many modules have **significant downstream impact**, especially:
- WebSocketManager
- StrategyEngine
- StrategyContext
- Order routing and risk enforcement

Rules:
- Do not change function signatures lightly
- Do not change tick structure without updating contracts
- Assume downstream users depend on current behavior
- Prefer additive changes over breaking changes

---

## Debugging & Development Preferences

Preferred approach:
- Step-by-step debugging
- Explicit logs over implicit assumptions
- Verbose modes over silent failures
- Debug prints that can be gated by flags

Avoid:
- “Magic” behavior
- Implicit filtering
- Hidden state changes
- Silent error swallowing

---

## Identity & Data Integrity Rules (Non-Negotiable)

- Token (`tk`) is the ONLY runtime identity
- Instrument names are display-only
- All logic is token-based
- `tk` establishes truth, `tf` mutates only
- Missing `lp` must be carried forward
- StrategyContext is bound to exactly ONE token

Any change violating these must be rejected.

---

## Strategy Design Preferences

- Strategies should be simple and explicit
- Filtering should be deterministic
- Context should never mix instruments
- Indicators should operate on clean price series
- Strategy code should not need to know about WebSocket internals

---

## Testing & Validation Philosophy

Order of priority:
1. Architectural correctness
2. Deterministic behavior
3. Debuggability
4. Performance (later)

Testing approach:
- First validate with live ticks (read-only)
- Then backtest using same logic
- Then forward-test (paper trading)
- Only then enable live trading

---

## Backtesting & Live Parity Principle

- Backtest and live must share the same code paths
- No strategy code branches like `if backtest:`
- Differences should be injected at the data source layer only

---

## Documentation Expectations

- Architecture changes MUST update docs
- New invariants MUST be written down
- “It lives in code” is not acceptable
- Markdown docs are first-class artifacts

Required docs to keep updated:
- ARCHITECTURE.md
- RUNTIME_FLOW.md
- TICK_CONTRACT.md
- PROJECT_PREFS.md
- PROJECT_SCOPE.md
- ROADMAP.md

---

## Decision-Making Heuristics

When unsure, prefer:
- Correctness over speed
- Explicitness over cleverness
- Smaller scope over feature creep
- Clarity over abstraction

If a decision could introduce subtle trading bugs, it should be avoided.

---

## Intended Long-Term Direction

This project is intended to:
- Grow incrementally
- Support multiple strategies and instruments
- Enable serious experimentation
- Eventually support automated trading safely

It is NOT intended to:
- Be rushed to live trading
- Sacrifice correctness for features
- Become opaque or overly abstract

---

## Final Note

If a future change:
- Feels “clever”
- Feels “too big”
- Or feels like it might hide bugs

Pause, document, and reassess.

This document exists to protect the system from accidental complexity.

---

End of PROJECT_PREFERENCES.md
