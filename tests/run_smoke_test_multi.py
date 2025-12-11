#!/usr/bin/env python3
import sys, os, time, json
import asyncio
import threading
import socket
from multiprocessing import Process
from websockets import connect

# ===========================================
# Ensure project root is importable
# ===========================================
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Project imports
from src.engine.strategy_engine import StrategyEngine
from src.core.portfolio.manager import PortfolioManager
from src.core.strategy.base import BaseStrategy
from src.core.strategy.performance import PerformanceEngine
from src.core.strategy.context import StrategyContext


# ===========================================
# ASCII Sparkline Helper
# ===========================================
def sparkline(values, width=40):
    """Simple ASCII sparkline."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    span = mx - mn or 1
    blocks = "▁▂▃▄▅▆▇█"
    out = []
    for v in values[-width:]:
        idx = int((v - mn) / span * (len(blocks) - 1))
        out.append(blocks[idx])
    return "".join(out)


# ===========================================
# Mock Server Launcher
# ===========================================
def start_mock_server(mode="oscillate"):
    server_path = os.path.join(ROOT, "src", "mock", "mock_server.py")
    env = os.environ.copy()
    env["MOCK_MODE"] = mode

    def run():
        os.execv(sys.executable, [sys.executable, server_path])

    proc = Process(target=run, daemon=True)
    proc.start()
    print(f"[MAIN] Mock server launched with MODE={mode} (PID={proc.pid})")
    return proc


def wait_for_port(host, port, timeout=10):
    print(f"[MAIN] Waiting for mock server on {host}:{port}…")
    start = time.time()

    while time.time() - start < timeout:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            sock.close()
            print("[MAIN] Mock server is LIVE.")
            return True
        except Exception:
            time.sleep(0.2)

    raise RuntimeError("Mock server did not start in time.")


# ===========================================
# Auto-Fill OrderManager
# ===========================================
class MockAPI:
    pass


class AutoFillOrderManager:
    """
    Any placed order is instantly filled at the same price.
    This is ideal for smoke-testing the full trading pipeline.
    """
    def __init__(self, engine):
        self.engine = engine
        self.orders = []
        self.fills = []

    def place_order(self, **kwargs):
        print(f"[AutoFillOrderManager] ORDER: {kwargs}")
        self.orders.append(kwargs)
        order_id = len(self.orders)

        # --- AUTO FILL LOGIC ---
        fill = {
            "strategy_name": kwargs["meta"]["strategy_name"],
            "transaction_type": kwargs["buy_or_sell"],
            "price": kwargs["price"],
            "filled_qty": kwargs["quantity"],
        }
        print(f"[AutoFillOrderManager] FILL: {fill}")
        self.fills.append(fill)

        # Feed fill back into the engine
        self.engine.on_order_update(fill)

        return {"order_id": order_id}


# ===========================================
# Strategy AAA — Momentum
# ===========================================
class StratAAA(BaseStrategy):
    """
    Momentum strategy:
      BUY if price rises > 1.0 since previous tick
      SELL if price falls > 1.0 since previous tick
    """
    def __init__(self):
        super().__init__("AAA_strat", "AAA_EQ", {}, 5)
        self.ctx.performance = PerformanceEngine(100000)
        self.history = []

    def on_start(self, api, order_manager):
        print("[AAA] started")

    def on_tick(self, api, order_manager, tick, ctx: StrategyContext):
        try:
            price = float(tick["lp"])
        except Exception:
            return

        # Extract previous price safely
        prev_price = None
        lt = getattr(ctx, "last_tick", None)
        if isinstance(lt, dict):
            raw_lp = lt.get("lp")
            if isinstance(raw_lp, (float, int, str)):
                try:
                    prev_price = float(raw_lp)
                except Exception:
                    prev_price = None

        # Update local history
        self.history.append(price)
        if len(self.history) > 20:
            self.history.pop(0)

        # Update context
        ctx.append_tick(tick)
        ctx.update_unrealized(price)

        if prev_price is None:
            return

        delta = price - prev_price

        if delta > 1.0:
            print("[AAA] BUY (momentum)")
            self.place_limit(order_manager, "B", price, 1)

        elif delta < -1.0:
            print("[AAA] SELL (reversal)")
            self.place_limit(order_manager, "S", price, 1)

    def on_stop(self, api, order_manager):
        print("[AAA] stopped")


# ===========================================
# Strategy BBB — Oscillation
# ===========================================
class StratBBB(BaseStrategy):
    """
    Oscillation strategy:
      BUY when price hits local lows
      SELL when price hits local highs
    """
    def __init__(self):
        super().__init__("BBB_strat", "BBB_EQ", {}, 10)
        self.ctx.performance = PerformanceEngine(100000)
        self.history = []

    def on_start(self, api, order_manager):
        print("[BBB] started")

    def on_tick(self, api, order_manager, tick, ctx: StrategyContext):
        try:
            price = float(tick["lp"])
        except Exception:
            return

        # Local history, not ctx.window
        self.history.append(price)
        if len(self.history) > 60:
            self.history.pop(0)

        ctx.append_tick(tick)
        ctx.update_unrealized(price)

        if len(self.history) < 5:
            return

        lo = min(self.history)
        hi = max(self.history)

        if price <= lo:
            print("[BBB] BUY (local low)")
            self.place_limit(order_manager, "B", price, 1)

        elif price >= hi:
            print("[BBB] SELL (local high)")
            self.place_limit(order_manager, "S", price, 1)

    def on_stop(self, api, order_manager):
        print("[BBB] stopped")


# ===========================================
# WebSocket → Engine tick forwarding
# ===========================================
async def websocket_client(engine):
    uri = "ws://localhost:9000"
    await asyncio.sleep(0.3)

    print("[WS CLIENT] Connecting…")
    async with connect(uri) as ws:
        print("[WS CLIENT] Connected!")

        await ws.send(json.dumps({"t": "t", "k": "NSE|AAA_EQ#NSE|BBB_EQ"}))

        while True:
            raw = await ws.recv()
            msg = json.loads(raw)

            if msg.get("t") == "ck":
                continue
            if msg.get("t") != "tk":
                continue

            engine_tick = {
                "symbol": msg["tk"],
                "lp": float(msg["lp"]),
                "raw": msg
            }
            engine.on_tick(engine_tick)


def start_ws_client_thread(engine):
    asyncio.run(websocket_client(engine))


# ===========================================
# LIVE PNL PRINTER WITH ASCII SPARKLINES
# ===========================================
def pnl_printer(portfolio, stop_flag):
    curves = {}

    while not stop_flag["stop"]:
        snap = portfolio.snapshot()
        equity = snap["last_equity"]
        syms = snap["strategies"]

        for strat in syms:
            curves.setdefault(strat, []).append(equity)

        os.system("clear")
        print("📈 LIVE PNL UPDATE")
        print("====================")
        print(f"Total Equity     : {equity:.2f}")
        print(f"Realized PnL     : {snap['total_realized']:.2f}")
        print(f"Unrealized PnL   : {snap['total_unrealized']:.2f}")
        print()

        for strat, curve in curves.items():
            print(f"Strategy {strat}:")
            print(" ", sparkline(curve, width=50))
            print()

        time.sleep(1)


# ===========================================
# MAIN SMOKE TEST
# ===========================================
def run_smoke_test(mode="oscillate"):
    print("\n===============================")
    print("MULTI-STRATEGY SMOKE TEST (AUTO-FILL)")
    print("===============================\n")

    server_proc = start_mock_server(mode)
    wait_for_port("127.0.0.1", 9000)

    api = MockAPI()
    engine = StrategyEngine(api, None, max_workers=4, queue_size=200)
    om = AutoFillOrderManager(engine)
    engine.order_manager = om

    portfolio = PortfolioManager(100000)
    engine.portfolio = portfolio

    # Register strategies
    stratA = StratAAA()
    stratB = StratBBB()
    engine.register(stratA)
    engine.register(stratB)

    portfolio.add_strategy(stratA)
    portfolio.add_strategy(stratB)

    # Start engine
    engine.start()

    # WS client
    threading.Thread(target=start_ws_client_thread, args=(engine,), daemon=True).start()

    # Live PnL printer
    stop_flag = {"stop": False}
    threading.Thread(target=pnl_printer, args=(portfolio, stop_flag), daemon=True).start()

    # Let everything run
    time.sleep(10)

    # Stop PnL printer
    stop_flag["stop"] = True
    time.sleep(1)

    # Stop engine
    engine.stop()

    print("\n--- FINAL PORTFOLIO SNAPSHOT ---")
    print(json.dumps(portfolio.snapshot(), indent=2))

    server_proc.terminate()
    print("\n🎉 SMOKE TEST COMPLETED SUCCESSFULLY!\n")


if __name__ == "__main__":
    # Try modes: momentum, oscillate, crash, normal, flat
    run_smoke_test("oscillate")
