# LLM GUIDE

Owner: LLM Interaction Contract
Audience: Any LLM assisting with this repository

This document defines how an LLM should reason, respond, and behave
when working with this codebase.

---

## 1. Source of Truth Hierarchy

From highest to lowest priority:

1. Latest uploaded ZIP of the repository
2. docs/START_HERE.md
3. docs/ARCHITECTURE.md
4. docs/RUNTIME_FLOW.md
5. docs/PROJECT_PREFERENCES.md
6. docs/CURRENT_STATE.md
7. docs/ROADMAP.md

If there is a conflict, higher-ranked documents win.

---

## 2. ZIP Upload Rules (CRITICAL)

- Treat each ZIP upload as a fresh snapshot
- Ignore any prior repository state
- Do NOT assume files exist unless present in the ZIP
- If something is missing, ask — do not hallucinate

The ZIP is the repo. Nothing else exists.

---

## 3. Reading Order (MANDATORY)

Before proposing changes:

1. Read START_HERE.md
2. Read ARCHITECTURE.md
3. Read RUNTIME_FLOW.md
4. Skim CURRENT_STATE.md

Only then:
- Diagnose bugs
- Suggest changes
- Propose tests

---

## 4. Response Style Expectations

- Prefer reasoning before answers
- Explain trade-offs explicitly
- Avoid large diffs unless requested
- Do not refactor for “cleanliness” alone
- Preserve existing structure unless breaking bug is proven

If uncertain, pause and ask.

---

## 5. Formatting Expectations for Docs

When generating markdown for this repo:
- Prefer plain text
- ATX headers (#, ##, ###)
- Avoid complex markdown constructs
- When requested, wrap output in a single code block for verbatim pasting

Follow the user’s formatting cue exactly.

---

## 6. What NOT to Do

- Do not silently change architectural rules
- Do not introduce new abstractions casually
- Do not bypass documented invariants
- Do not optimize prematurely

This is a correctness-first trading system.

---

## 7. Relationship to PROJECT_PREFERENCES.md

- Human collaboration preferences live in PROJECT_PREFERENCES.md
- This file governs only LLM behavior

If there is overlap:
- Defer to PROJECT_PREFERENCES.md for human intent
