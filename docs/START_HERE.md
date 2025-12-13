# START HERE

If you are new to this repository — human or LLM — start here.

This file explains how to navigate the project and its documentation.

---

## 1. What This Project Is

This is a trading system designed to:

- Consume live market data (Shoonya WebSocket)
- Normalize snapshot + delta ticks (tk / tf)
- Run strategies safely on token-scoped data
- Progress toward backtesting, forward testing, and live trading

Correctness and safety are prioritized over speed of development.

---

## 2. Documentation Map (READ IN THIS ORDER)

1. START_HERE.md  
   (You are here)

2. ARCHITECTURE.md  
   Non-negotiable system rules

3. RUNTIME_FLOW.md  
   What actually happens at runtime today

4. CURRENT_STATE.md  
   What is implemented vs intentionally missing

5. PROJECT_PREFERENCES.md  
   How the project prefers to be worked on (human workflow)

6. LLM_GUIDE.md  
   How LLMs should behave when assisting

7. ROADMAP.md  
   Future phases and scope

---

## 3. Ownership & Scope Model (IMPORTANT)

Each document has a clear role:

- ARCHITECTURE.md  
  → What must never break

- RUNTIME_FLOW.md  
  → What the code actually does today

- PROJECT_PREFERENCES.md  
  → Human workflow & collaboration preferences

- LLM_GUIDE.md  
  → Rules for LLM reasoning and responses

- ROADMAP.md  
  → What will be built later (not assumed to exist)

- CURRENT_STATE.md  
  → Snapshot of today’s reality

Do not mix these concerns.

---

## 4. Key Design Principle

Token-based identity is the backbone of the system.

- Tokens drive all logic
- Instrument names are display-only
- tk establishes truth
- tf mutates state
- Missing lp is carry-forward

If you violate this, the system is wrong.

---

## 5. How to Start a New ChatGPT Thread (Recommended)

When starting a new thread:

- Upload the latest ZIP of the repo
- Explicitly say:
  - “Ignore all previous uploads and context”
  - “Use ONLY this ZIP as source of truth”
  - “Read docs/START_HERE.md first”

This keeps reasoning clean and avoids stale assumptions.

---

## 6. Current Phase

The project is currently focused on:

- Validating live tick correctness
- Locking tk/tf semantics
- Establishing safe strategy execution

Next planned phases:
- Testing & validation
- Backtest engine
- Order lifecycle & risk enforcement

Refer to ROADMAP.md for details.

---

## 7. Final Note

If something feels unclear:
- Check the docs first
- If still unclear, ask explicitly

Silence and assumptions cause trading bugs.
