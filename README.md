# Shoonya Trading Engine

A production-oriented trading engine built around the Shoonya API.

This repository is **not just a WebSocket client** — it is a full
event-driven trading stack with strict architectural invariants designed
to prevent silent trading bugs.

---

## Core Features

- Token-first market data model (no symbol ambiguity)
- Robust `tk` / `tf` snapshot + delta merge semantics
- Strategy engine with concurrency, throttling, and isolation
- Strong invariants enforced at runtime (fail fast)
- Designed for LIVE trading and future BACKTEST parity
- Mock WebSocket support for offline testing
- Built-in PnL, position, and performance tracking

---

## Design Philosophy (IMPORTANT)

This project follows **non-negotiable rules**:

- Tokens (`tk`) are the ONLY runtime identity
- Instrument names are display-only
- Strategies are scoped to exactly ONE token
- Contexts never accept mismatched ticks
- Missing data is carried forward, never guessed
- Debug visibility is preferred over clever abstractions

If you are extending this repo, read:
- docs/ARCHITECTURE.md
- docs/RUNTIME_FLOW.md

BEFORE making changes.

---

## High-Level Architecture

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
Strategies
|
v
StrategyContext (PnL / Position / Performance)
```
For a detailed runtime walkthrough, see:
docs/RUNTIME_FLOW.md

---

## Installation

```
- Clone the repository
git clone https://github.com/your-username/api_shoonya.git

- Move into the project directory
cd api_shoonya

- Create a virtual environment
python3 -m venv venv

- Activate the virtual environment
source venv/bin/activate

- Install dependencies
pip install -r requirements.txt
```

---

## Configuration Overview

Humans configure strategies by **instrument name**.

Tokens are resolved ONCE during application startup.

After startup:
- The system is token-only
- No component re-resolves symbols
- No component trusts instrument names

---

## Example Usage (Live Mode)

In application.py (simplified):

```
broker = ShoonyaClient()
api = broker.login()

tokens = resolve_instruments([
"GOLDTEN31DEC25",
"CRUDEOIL16DEC25P5200"
])

ws = WebSocketManager(
broker=broker,
on_tick=strategy_engine.on_tick,
verbose=True,
print_ticks=True
)

ws.start(api, tokens)
strategy_engine.start()
```

---

## WebSocket Tick Model

Shoonya sends two tick types:

- tk → full snapshot
- tf → incremental update

Rules:
- tk establishes truth
- tf mutates existing state
- tf without prior tk is ignored
- lp is carried forward if missing

This logic is implemented in:
WebSocketManager._patched_on_data()

---

## Strategy Model

- Each strategy is bound to exactly ONE token
- StrategyEngine dispatches ticks blindly
- Token filtering happens at the engine boundary
- StrategyContext enforces token purity defensively

Example strategy:
- src/core/strategy/momentum_strategy.py

---

## Mock Mode

The engine supports a mock WebSocket server for offline testing.

- Mock mode uses an async websocket client
- Messages are forwarded unchanged
- Same tk/tf semantics apply
- Strategies behave identically to live mode

This guarantees:
- Deterministic testing
- Backtest parity in the future

---

## Heartbeat Monitoring

Two independent heartbeats exist:

- Price heartbeat
Warns if no price-carrying ticks received

- Message heartbeat
Warns if no messages at all received

These are warnings, not fatal errors.

---

## Documentation

- docs/ARCHITECTURE.md
Non-negotiable invariants and rules

- docs/RUNTIME_FLOW.md
Line-by-line runtime behavior

These documents define the system.
Code must follow them — not the other way around.

---

## Roadmap

- Backtest engine using the same tick contract
- Order execution simulator
- Portfolio-level risk constraints
- Multi-instrument strategies
- Persistence & replay

---

## Contributing

This repo enforces strict invariants.

If you propose a change:
- State which rule it preserves
- State which rule it strengthens
- Or explain clearly why a rule must change

---

## License

MIT License