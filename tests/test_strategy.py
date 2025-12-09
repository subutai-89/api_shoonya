# tests/test_strategy_engine.py
import sys, os, time, json

# ensure project root on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.engine.strategy_engine import StrategyEngine
from src.core.strategy.base import BaseStrategy
from src.core.strategy.performance import PerformanceEngine
from src.core.strategy.context import StrategyContext


# ------------------------------
# Mock API & OrderManager
# ------------------------------
class MockAPI:
    pass


class MockOrderManager:
    def __init__(self):
        self.orders = []
        self.updates = []

    def place_order(self, **kwargs):
        self.orders.append(kwargs)
        print(f"[MockOrderManager] order placed: {kwargs}")
        return {"order_id": len(self.orders)}

    def simulate_fill(self, strategy_name, side, price, qty):
        update = {
            "strategy_name": strategy_name,
            "transaction_type": side,  # 'B' or 'S'
            "price": price,
            "filled_qty": qty,
        }
        self.updates.append(update)
        return update


# ------------------------------
# Test strategy
# ------------------------------
class TestStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(
            name="test_strat",
            symbol="TEST",
            params={"short": 2},
            window_size=5
        )
        self.events = []
        # set starting capital for meaningful returns
        self.ctx.performance = PerformanceEngine(starting_equity=100000.0)

    def on_start(self, api, order_manager):
        print("[TestStrategy] on_start()")
        self.events.append("start")

    def on_tick(self, api, order_manager, tick, ctx: StrategyContext):
        print(f"[TestStrategy] on_tick: {tick}")
        ctx.append_tick(tick)
        price = tick["lp"]

        # update unrealized PnL
        ctx.update_unrealized(price)

        # Example signal: buy at lp=103, sell at lp=108
        if price == 103:
            print("→ placing BUY")
            self.place_limit(order_manager, "B", price=103, qty=1)

        if price == 108:
            print("→ placing SELL")
            self.place_limit(order_manager, "S", price=108, qty=1)

        self.events.append(("tick", price))

    def on_stop(self, api, order_manager):
        print("[TestStrategy] on_stop()")
        self.events.append("stop")


# ------------------------------
# TEST RUNNER
# ------------------------------
def run_test():
    print("\n=== FULL STRATEGY ENGINE TEST ===")

    api = MockAPI()
    om = MockOrderManager()
    engine = StrategyEngine(api, om, max_workers=2, queue_size=100)

    strat = TestStrategy()
    
    # record only while position open
    strat.ctx.performance = PerformanceEngine(starting_equity=100000.0, sample_mode="on_position")
    
    engine.register(strat)

    # ---- START ENGINE ----
    engine.start()

    # ---- SEND TICKS ----
    ticks = [
        {"lp": 101},
        {"lp": 102},
        {"lp": 103},   # triggers BUY
        {"lp": 105},
        {"lp": 108},   # triggers SELL
        {"lp": 110},
    ]

    for t in ticks:
        engine.on_tick(t)
        time.sleep(0.05)

    # ---- SIMULATE ORDER FILLS ----
    # BUY fill
    buy_fill = om.simulate_fill("test_strat", "B", price=103, qty=1)
    engine.on_order_update(buy_fill)

    # SELL fill
    sell_fill = om.simulate_fill("test_strat", "S", price=108, qty=1)
    engine.on_order_update(sell_fill)

    # Allow engine to process remaining work
    time.sleep(0.3)

    # ---- STOP ENGINE ----
    engine.stop()

    print("\n--- STRATEGY EVENTS ---")
    print(strat.events)

    print("\n--- FINAL POSITION ---")
    print("Qty:", strat.ctx.position.qty)
    print("AvgPrice:", strat.ctx.position.avg_price)

    print("\n--- PnL SNAPSHOT ---")
    print(strat.ctx.pnl.snapshot())

    print("\n--- TRADE LEDGER ---")
    print("--- TRADE LEDGER REMOVED UNDER B3 ACCOUNTING ---")

    print("\n--- PERFORMANCE REPORT ---")
    print(json.dumps(strat.ctx.performance_report(annualization=None), indent=2, default=str))


if __name__ == "__main__":
    run_test()
