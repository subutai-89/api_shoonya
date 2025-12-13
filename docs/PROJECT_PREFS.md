# PROJECT PREFERENCES

Owner: Human (Project Maintainer)
Audience: Human collaborators (including future-you)

This document defines how this project prefers to be worked on.
These are collaboration and workflow preferences, not architecture rules.

---

## 1. Core Philosophy

- Correctness > cleverness
- Explicitness > abstraction
- Observability > premature optimization
- Stability > refactors

This is a trading system. Subtle bugs are worse than missing features.

---

## 2. Change & Refactor Preferences

- Prefer minimal, localized changes
- Avoid renaming functions, classes, or files unless strictly necessary
- Avoid architectural rewrites unless explicitly requested
- When fixing bugs:
  - Patch first
  - Validate
  - Refactor later (if at all)

If a change can be reverted easily, it is preferred.

---

## 3. Debugging & Development Style

- Step-by-step debugging is strongly preferred
- Explain *why* a bug happens before proposing a fix
- Prefer printing / logging over silent logic changes
- Never “assume” upstream correctness (especially market data)

---

## 4. Strategy & Trading Safety Bias

- Market data must be treated as unreliable
- Token-based identity is sacred
- Instrument names are display-only
- Missing data should be handled defensively

If something looks odd, surface it loudly rather than hiding it.

---

## 5. Documentation Expectations

- Architecture rules must be documented
- Runtime behavior must match documentation
- If behavior changes, docs must be updated in the same commit

Docs are not optional — they are part of the system.

---

## 6. Preferred New-Thread Prompt Format (IMPORTANT)

When starting a **new ChatGPT thread**, use a prompt similar to:

- “This is a continuation of an existing repo.”
- “Ignore all previous uploads and context.”
- “Use ONLY the contents of this ZIP as source of truth.”
- “Read docs/START_HERE.md first.”
- “Follow docs/PROJECT_PREFERENCES.md and docs/LLM_GUIDE.md.”

This avoids context bleed and hallucinated assumptions.

---

## 7. What This File Is NOT

This file does NOT define:
- Architecture invariants
- Runtime flow
- LLM behavior rules
- Roadmap or scope

Those live in other documents.

If unsure where something belongs:
- Human workflow → here
- LLM behavior → LLM_GUIDE.md
- System rules → ARCHITECTURE.md
