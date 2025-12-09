import asyncio
import json
import random
import time
import math
import websockets
import os
from urllib.parse import urlparse, parse_qs

"""
Available modes (choose via ws://localhost:9000?mode=X):

mode=normal      → random walk (default)
mode=momentum    → upward trend
mode=crash       → downward trend
mode=oscillate   → sine-wave price action
mode=flat        → almost no movement
"""


# ------------------------------
# GLOBAL STATE
# ------------------------------

symbol_state = {}

DEFAULT_MODE = os.getenv("MOCK_MODE", "normal")

# DEFAULT_MODE = "normal"
# DEFAULT_MODE = "momentum"
# DEFAULT_MODE = "crash"
# DEFAULT_MODE = "oscillate"
# DEFAULT_MODE = "flat"


# ------------------------------
# TICK GENERATOR
# ------------------------------

def generate_tick(symbol_full, mode):
    exchange, token = symbol_full.split("|")

    # Initialize per-symbol state
    if symbol_full not in symbol_state:
        base = random.uniform(100, 500)
        symbol_state[symbol_full] = {
            "lp": base,
            "o": base,
            "h": base,
            "l": base,
            "v": 0,
            "t0": time.time()
        }

    state = symbol_state[symbol_full]
    last_price = state["lp"]

    # --------------------------
    # PRICE ACTION MODES
    # --------------------------

    if mode == "momentum":
        new_price = last_price + random.uniform(0.4, 2.0)

    elif mode == "crash":
        new_price = last_price - random.uniform(0.4, 2.0)

    elif mode == "oscillate":
        t = time.time() - state["t0"]
        new_price = state["o"] + math.sin(t * 2) * 3

    elif mode == "flat":
        new_price = last_price + random.uniform(-0.1, 0.1)

    else:
        # normal random walk
        new_price = last_price + random.uniform(-2.0, 2.0)

    new_price = round(max(new_price, 1), 2)

    # Update OHLCV state
    state["lp"] = new_price
    state["h"] = max(state["h"], new_price)
    state["l"] = min(state["l"], new_price)
    state["v"] += random.randint(10, 300)

    # --------------------------
    # RETURN SHOONYA-STYLE TICK
    # --------------------------
    return {
        "t": "tk",
        "e": exchange,
        "tk": token,
        "ts": "MOCKSYM",
        "lp": str(new_price),
        "o": str(state["o"]),
        "h": str(state["h"]),
        "l": str(state["l"]),
        "v": str(state["v"]),
        "ft": str(int(time.time() * 1000)),
        "bp1": str(round(new_price - 0.5, 2)),
        "sp1": str(round(new_price + 0.5, 2)),
        "bq1": str(random.randint(1, 1000)),
        "sq1": str(random.randint(1, 1000)),
    }


# ------------------------------
# CLIENT HANDLING
# ------------------------------

async def handle_client(ws):
    print(f"Client connected | MODE = {DEFAULT_MODE}")

    # Shoonya handshake
    await ws.send(json.dumps({"t": "ck", "s": "OK"}))

    subscribed = []

    try:
        async for incoming in ws:
            data = json.loads(incoming)

            if data.get("t") == "t":
                subscribed = data["k"].split("#")
                print("Subscribed:", subscribed)

                print(f"Tick stream started for {subscribed} | MODE={DEFAULT_MODE}")
                asyncio.create_task(push_ticks(ws, subscribed, DEFAULT_MODE))

    except websockets.ConnectionClosed:
        print("Client disconnected")


async def push_ticks(ws, subscribed, mode):
    try:
        while True:
            for symbol in subscribed:
                tick = generate_tick(symbol, mode)
                await ws.send(json.dumps(tick))
            await asyncio.sleep(0.9)
    except websockets.ConnectionClosed:
        print("Tick push stopped: client disconnected")



# ------------------------------
# SERVER MAIN LOOP
# ------------------------------

async def main():
    print("Mock server listening at ws://localhost:9000")
    async with websockets.serve(handle_client,"localhost",9000,
                                process_request=None):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
