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
    if not values:
        return ""
    mn, mx = min(values), max(values)
    span = max(mx - mn, 1e-9)
    blocks = "▁▂▃▄▅▆▇█"
    return "".join(
        blocks[int((v - mn) / span * (len(blocks) - 1))] for v in values[-width:]
    )


# ===========================================
# START MOCK SERVER
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
    start_ts = time.time()
    while time.time() - start_ts < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                print("[MAIN] Mock server is LIVE.")
                return True
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("Mock server did not start in time.")


# ===========================================
# AUTO-FILL ORDER MANAGER
# ===========================================
class MockAPI:
    pass


class AutoFillOrderManager:
    """
    Any placed order is immediately filled at the same price.
    Also respects per-strategy cooldown and max-position guard
    (enforced by the strategy itself).
    """
    def __init__(self, engine):
        self.engine = engine
        self.orders = []
        self.fills = []

    def place_order(self, **kwargs):
        print(f"[AutoFillOrderManager] ORDER: {kwargs}")
        self.orders.append(kwargs)

        # Construct fill
        fill = {
            "strategy_name": kwargs["meta"]["strategy_name"],
            "transaction_type": kwargs["buy_or_sell"],
            "price": kwargs["price"],
            "filled_qty": kwargs["quantity"],
        }
        print(f"[AutoFillOrderManager] FILL: {fill}")
        self.fills.append(fill)

        # feed back into the strategy engine
        self.engine.on_order_update(fill)
        return {"order_id": len(self.orders)}


# ===========================================
# PER-STRATEGY POSITION GUARD (cooldown + max_pos)
# ===========================================
class PositionGuardMixin:
    def __init__(self):
        self._last_order_ts = 0.0
        self._cooldown_s = 0.5     # half-second cooldown
        self._max_pos = 1          # do not exceed 1 long or 1 short

    def can_place(self, ctx, side):
        # cooldown check
        now = time.time()
        if now - self._last_order_ts < self._cooldown_s:
            return False

        # position check
        qty = 0
        try:
            qty = ctx.position.qty
        except Exception:
            qty = 0

        if side == "B" and qty >= self._max_pos:
            return False
        if side == "S" and qty <= -self._max_pos:
            return False

        return True

    def record_order(self):
        self._last_order_ts = time.time()


# ======================================================
# STRATEGY AAA (Momentum) — With Correct Init Order
# ======================================================
class StratAAA(BaseStrategy, PositionGuardMixin):
    def __init__(self):
        BaseStrategy.__init__(self, "AAA_strat", "AAA_EQ", {}, 5)
        PositionGuardMixin.__init__(self)

        self.ctx.performance = PerformanceEngine(100000)
        self.history = []

    def on_start(self, api, order_manager):
        print("[AAA] started")

    def on_tick(self, api, order_manager, tick, ctx: StrategyContext):
        try:
            price = float(tick["lp"])
        except Exception:
            return

        # previous price
        prev_price = None
        lt = getattr(ctx, "last_tick", None)
        if isinstance(lt, dict):
            val = lt.get("lp")
            if isinstance(val, (float, int, str)):
                try:
                    prev_price = float(val)
                except:
                    prev_price = None

        ctx.append_tick(tick)
        ctx.update_unrealized(price)

        self.history.append(price)
        if len(self.history) > 20:
            self.history.pop(0)

        if prev_price is None:
            return

        delta = price - prev_price

        if delta > 1.0 and self.can_place(ctx, "B"):
            print("[AAA] BUY (momentum)")
            self.place_limit(order_manager, "B", price, 1)
            self.record_order()

        elif delta < -1.0 and self.can_place(ctx, "S"):
            print("[AAA] SELL (reversal)")
            self.place_limit(order_manager, "S", price, 1)
            self.record_order()

    def on_stop(self, api, order_manager):
        print("[AAA] stopped")



# ======================================================
# STRATEGY BBB (Oscillation) — With Correct Init Order
# ======================================================
class StratBBB(BaseStrategy, PositionGuardMixin):
    def __init__(self):
        BaseStrategy.__init__(self, "BBB_strat", "BBB_EQ", {}, 10)
        PositionGuardMixin.__init__(self)

        self.ctx.performance = PerformanceEngine(100000)
        self.history = []

    def on_start(self, api, order_manager):
        print("[BBB] started")

    def on_tick(self, api, order_manager, tick, ctx: StrategyContext):
        try:
            price = float(tick["lp"])
        except Exception:
            return

        ctx.append_tick(tick)
        ctx.update_unrealized(price)

        self.history.append(price)
        if len(self.history) > 60:
            self.history.pop(0)

        if len(self.history) < 5:
            return

        lo = min(self.history)
        hi = max(self.history)

        if price <= lo and self.can_place(ctx, "B"):
            print("[BBB] BUY (local low)")
            self.place_limit(order_manager, "B", price, 1)
            self.record_order()

        elif price >= hi and self.can_place(ctx, "S"):
            print("[BBB] SELL (local high)")
            self.place_limit(order_manager, "S", price, 1)
            self.record_order()

    def on_stop(self, api, order_manager):
        print("[BBB] stopped")


# ===========================================
# WEBSOCKET CLIENT → ENGINE TICK FEED
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

            engine.on_tick({
                "symbol": msg["tk"],
                "lp": float(msg["lp"]),
                "raw": msg,
            })


def start_ws_client_thread(engine):
    asyncio.run(websocket_client(engine))


# ===========================================
# LIVE PNL PRINTER (ASCII SPARKLINES)
# ===========================================
def pnl_printer(portfolio, stop_flag):
    curves = {}

    while not stop_flag["stop"]:
        snap = portfolio.snapshot()
        eq = snap["last_equity"]

        for strat in snap["strategies"]:
            curves.setdefault(strat, []).append(eq)

        os.system("clear")
        print("📈 LIVE PNL UPDATE")
        print("====================")
        print(f"Total Equity     : {eq:.2f}")
        print(f"Realized PnL     : {snap['total_realized']:.2f}")
        print(f"Unrealized PnL   : {snap['total_unrealized']:.2f}\n")

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
    print("MULTI-STRATEGY SMOKE TEST (AUTO-FILL + GUARDS)")
    print("===============================\n")

    # start mock server
    proc = start_mock_server(mode)
    wait_for_port("127.0.0.1", 9000)

    api = MockAPI()
    engine = StrategyEngine(api, None, max_workers=4, queue_size=200)

    # auto-fill manager
    om = AutoFillOrderManager(engine)
    engine.order_manager = om

    # portfolio setup
    portfolio = PortfolioManager(100000)
    engine.portfolio = portfolio

    # strategies
    stratA = StratAAA()
    stratB = StratBBB()
    engine.register(stratA)
    engine.register(stratB)

    portfolio.add_strategy(stratA)
    portfolio.add_strategy(stratB)

    # start engine
    engine.start()

    # websocket feed
    threading.Thread(target=start_ws_client_thread, args=(engine,), daemon=True).start()

    # pnl printer
    stop_flag = {"stop": False}
    threading.Thread(target=pnl_printer, args=(portfolio, stop_flag), daemon=True).start()

    # allow run
    time.sleep(12)

    stop_flag["stop"] = True
    time.sleep(1)

    engine.stop()

    print("\n--- FINAL PORTFOLIO SNAPSHOT ---")
    print(json.dumps(portfolio.snapshot(), indent=2))

    proc.terminate()
    print("\n🎉 SMOKE TEST COMPLETED SUCCESSFULLY!\n")


if __name__ == "__main__":
    # Try: momentum, oscillate, crash, normal, flat
    run_smoke_test("oscillate")
