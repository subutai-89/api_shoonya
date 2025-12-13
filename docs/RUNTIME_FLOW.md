# Detailed Runtime Flow

This section documents the **current, real behavior** of the system at runtime.  
It is intentionally explicit to help with debugging, onboarding, and future refactors.

---

### High-Level Architecture

```
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
Strategies (e.g. momentum_strategy)
```

---

### 1. WebSocket Startup Flow

- `application.py` initializes the broker and logs in.
- Instruments are resolved into Shoonya tokens (e.g. `MCX|472782`).
- `WebSocketManager.start(api, tokens)` is called.
- Heartbeat monitor thread starts immediately.
- Broker WebSocket is started using introspection-safe callbacks:
  - `subscribe_callback` → `_patched_on_data`
  - `socket_open_callback` → `_patched_on_open`
  - `socket_error_callback` → `_patched_on_error`
  - `socket_close_callback` → `_patched_on_close`

---

### 2. Message Types from Shoonya

Shoonya sends two relevant tick types:

#### `tk` — Full Snapshot Tick
- First message per instrument.
- Contains full market snapshot.
- Includes:
  - `tk` → token
  - `ts` → instrument name
  - `lp` → last price
  - OHLC, volume, OI, depth, etc.

#### `tf` — Incremental / Delta Tick
- Subsequent updates.
- May omit fields (especially `lp`).
- Represents partial updates to order book or price.

---

### 3. market_state (Core Design)

`market_state` is a dictionary keyed by token:

```
market_state = {
"472782": {
"instrument_name": "GOLDTEN31DEC25",
"lp": "131848.00",
...
}
}
```

#### Rules
- `tk` overwrites the entire snapshot.
- `tf` merges into existing snapshot.
- `lp` is carried forward if missing in `tf`.
- Raw values are preserved as strings (Shoonya-native).
- Parsed floats are only used in normalized output.

This guarantees:
- Stable price continuity.
- Correct behavior during partial updates.
- Easy debugging across instruments.


---

### 4. _patched_on_data() Flow

#### Step-by-step
- Stop event checked first (fast exit).
- `last_message_time` updated for heartbeat.
- Raw message printed if `verbose=True`.
- For `tk` ticks:
  - Extract:
    - `token` (`tk`)
    - `instrument name` (`ts`)
    - `last price` (`lp`)
  - Store full snapshot in `market_state`.
  - Update `last_tick_time`.
  - Print tick if `print_ticks=True`.
  - Forward normalized tick to strategy engine.
    - Normalized payload:
      ```
      {
          "t": "tk",
          "e": "MCX",
          "tk": "472782",
          "lp": 131848.0,
          "raw": raw_msg
      }
      ```
- For `tf` ticks:
  - Verify token exists in `market_state`.
  - If `lp` missing:
    - Carry forward previous `lp`.
  - Merge delta into stored snapshot.
  - Update `last_tick_time` only if `lp` present.
  - Print tick with resolved instrument name.
  - Forward normalized tick to strategy engine.

---

### 5. Tick Printing Logic

When `print_ticks=True`, output format is:
[LIVE TICK: GOLDTEN31DEC25] t: tf, e: MCX, tk: 472782, lp: 131848.00


#### Why this matters:
- Works with multiple instruments.
- Detects Shoonya mismatches.
- Allows visual correlation between token ↔ instrument.
- Safe even if Shoonya sends wrong token data.

---

### 6. Multiple Instrument Handling

#### Important behavior:
- All instruments share the same WebSocket.
- Each instrument has its own:
  - Market snapshot.
  - Last price.
- StrategyEngine currently receives interleaved ticks.
  - Example: `GOLD` → `CRUDE` → `GAS` → `GOLD` → `CRUDE` ...

#### Current Strategy Implication
- StrategyEngine treats ticks as a single stream.
- `prices_len` currently grows across instruments.
- For multi-instrument strategies, future work should:
  - Maintain per-instrument buffers.
  - Key indicators by `tk` or `instrument_name`.
  - (Current behavior is correct for single-instrument strategies.)

---

### 7. Heartbeat Monitoring

Runs in a dedicated thread.

#### Price Tick Heartbeat
- Uses `last_tick_time`.
- Warns if no price-carrying tick received.
- Default threshold: 300 seconds.

#### Order Book Heartbeat
- Uses `last_message_time`.
- Warns if no messages at all received.
- Default threshold: 60 seconds.

#### Example warning:
⚠️ No price ticks received for 312.45 seconds (Threshold: 300 seconds)


#### Note:
- This can appear during startup before first `tk`.
- Safe but noisy (can be gated further if needed).

---

### 8. Strategy Dispatch Guarantees

- Every valid `tk` and `tf` produces exactly one strategy callback.
- Callback receives:
  - Parsed numeric `lp`.
  - Full raw message.
  - No mutation of raw messages sent by Shoonya.
- Failures in strategy code are isolated and logged.

---

### 9. Shutdown Flow

- `stop()` sets stop event.
- Heartbeat thread stops.
- Reader thread stops.
- Broker WebSocket is closed if supported.
- Clean logout is performed.

---

### Design Philosophy

- Minimal mutation.
- Carry forward missing data.
- Never assume completeness of `tf`.
- Debug visibility over cleverness.
- Backward compatibility over refactors.

This flow documentation reflects the system exactly as it runs today.