# Detailed Runtime Flow

This document describes the actual runtime behavior of the system.
It is intentionally explicit and conservative.

If code behavior diverges from this document, the code is wrong.

---

## High-Level Architecture

    Shoonya WebSocket
            |
            v
    WebSocketManager
            |
            |-- market_state (per-token snapshot)
            |
            v
    StrategyEngine
            |
            v
    Strategies
            |
            v
    StrategyContext (PnL / Position / Performance)

---

## Mental Model: Live vs Backtest

The system is designed so that LIVE and BACKTEST converge on the same
normalized tick stream.

    LIVE WebSocket          BACKTEST CSV
          |                     |
          v                     v
    Normalized Tick Stream (tk / tf merged)
                  |
                  v
            StrategyEngine
                  |
                  v
                Strategy
                  |
                  v
            StrategyContext
                  |
                  v
            Signals / Orders

---

## 1. WebSocket Startup Flow

- application.py initializes the broker and logs in
- Humans configure instruments using instrument names
- Application resolves instrument → token exactly once
- WebSocketManager.start(api, tokens) is called
- Heartbeat monitor thread starts immediately
- Broker WebSocket is started with patched callbacks:
  - subscribe_callback → _patched_on_data
  - socket_open_callback → _patched_on_open
  - socket_error_callback → _patched_on_error
  - socket_close_callback → _patched_on_close

After startup, the runtime is token-only.

---

## 2. Message Types from Shoonya

Shoonya sends two relevant market data messages.

### tk — Full Snapshot Tick

- First message per instrument
- Establishes identity and truth
- Contains:
  - tk → token
  - ts → instrument name
  - lp → last traded price
  - OHLC, volume, depth, OI, etc.

### tf — Incremental / Delta Tick

- Sent after tk
- Contains only changed fields
- May omit lp
- Never establishes identity
- Must be ignored if tk was not seen first

---

## 3. market_state (Core Design)

market_state is a dictionary keyed by token.

Example:

    market_state = {
        "472782": {
            "instrument_name": "GOLDTEN31DEC25",
            "lp": "131848.00",
            ...
        }
    }

Rules:

- tk overwrites the entire snapshot
- tf merges into existing snapshot
- Missing lp in tf means unchanged
- lp is always carried forward
- Raw values remain Shoonya-native strings
- Parsed floats are only used in normalized output

This guarantees:
- Price continuity
- Correct partial-update handling
- Easy multi-instrument debugging

---

## 4. WebSocketManager _patched_on_data Flow

For every incoming message:

- Stop event is checked first
- last_message_time is updated
- Raw message is printed if verbose is enabled

### tk Handling

- Extract token (tk), instrument name (ts), and lp
- Store full snapshot in market_state[token]
- Update last_tick_time
- Print tick if print_ticks is enabled
- Forward normalized tick to StrategyEngine

Normalized tick structure:

    {
        "t": "tk",
        "e": "MCX",
        "tk": "472782",
        "lp": 131848.0,
        "raw": raw_msg
    }

### tf Handling

- Verify token exists in market_state
- If lp is missing, reuse last known lp
- Merge delta into market_state[token]
- Update last_tick_time only if lp present
- Print tick with resolved instrument name
- Forward normalized tick to StrategyEngine

---

## 5. Tick Printing Semantics

When print_ticks is enabled, output looks like:

    [LIVE TICK: GOLDTEN31DEC25] t: tf, e: MCX, tk: 472782, lp: 131848.00

Why this matters:

- Works with multiple instruments
- Exposes Shoonya data mismatches
- Allows visual token ↔ instrument verification
- Safe even if Shoonya sends incorrect ts values

---

## 6. StrategyEngine Dispatch Rules

- StrategyEngine receives a single interleaved tick stream
- Engine does NOT understand instruments or symbols
- Engine routes ticks strictly by token
- Each strategy receives ticks only for its configured token

Dispatch rule:

    if tick["tk"] != strategy.meta.symbol:
        skip

---

## 7. StrategyContext Invariants

A StrategyContext is bound to exactly one token.

Guarantees:

- ctx.symbol == token
- append_tick rejects ticks for other tokens
- ctx.prices operates on merged tk/tf data
- Instrument names are never used for logic

Violations raise immediately.

---

## 8. Heartbeat Monitoring

Runs in a dedicated thread.

Price heartbeat:
- Based on last_tick_time
- Warns if no price-carrying tick received
- Default threshold: 300 seconds

Message heartbeat:
- Based on last_message_time
- Warns if no messages at all received
- Default threshold: 60 seconds

Example warning:

    No price ticks received for 312.45 seconds (threshold: 300)

Startup note:
- Warning may appear before first tk
- Safe but noisy

---

## 9. Shutdown Flow

- stop() sets stop event
- Heartbeat thread exits
- Reader thread exits
- Broker WebSocket closed if supported
- Clean logout performed

---

## Design Philosophy

- Token-first identity
- Snapshot + delta correctness
- Carry-forward semantics
- Debug visibility over cleverness
- Backward compatibility over refactors

This document reflects the system exactly as it runs today.
