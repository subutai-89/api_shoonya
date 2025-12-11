# tests/test_strategy_engine_short.py
import sys, os, time, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.engine.strategy_engine import StrategyEngine
from src.core.strategy.base import BaseStrategy
from src.core.strategy.performance import PerformanceEngine


class MockAPI: pass


class MockOrderManager:
    def __init__(self):
        self.orders = []
        self.updates = []

    def place_order(self, **kwargs):
        self.orders.append(kwargs)
        print("ORDER:", kwargs)
        return {"order_id": len(self.orders)}

    def simulate_fill(self, strat, side, price, qty):
        upd = {
            "strategy_name": strat,
            "transaction_type": side,
            "price": price,
            "filled_qty": qty,
        }
        self.updates.append(upd)
        return upd


class ShortStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("short_strat", "TEST", params=None, window_size=5)
        self.ctx.performance = PerformanceEngine(starting_equity=100000)

    def on_start(self, api, order_manager):
        # optional start hook
        pass

    def on_tick(self, api, order_manager, tick, ctx):
        price = tick["lp"]
        ctx.append_tick(tick)
        ctx.update_unrealized(price)

        if price == 100:
            print("→ SHORT SELL @ 100")
            self.place_limit(order_manager, "S", 100, 1)

        if price == 90:
            print("→ COVER SHORT @ 90")
            self.place_limit(order_manager, "B", 90, 1)

    def on_stop(self, api, order_manager):
        pass


def run_test():
    api, om = MockAPI(), MockOrderManager()
    eng = StrategyEngine(api, om)

    strat = ShortStrategy()
    eng.register(strat)
    eng.start()

    ticks = [{"lp": 100}, {"lp": 95}, {"lp": 90}]
    for t in ticks:
        eng.on_tick(t)
        time.sleep(0.05)

    eng.on_order_update(om.simulate_fill("short_strat", "S", 100, 1))
    eng.on_order_update(om.simulate_fill("short_strat", "B", 90, 1))

    time.sleep(0.3)
    eng.stop()

    print("\nSHORT PNL:", strat.ctx.pnl.snapshot())
    print("\nREPORT:", json.dumps(strat.ctx.performance_report(), indent=2))


# PyTest identifier
def test_runner():
    run_test()


if __name__ == "__main__":
    test_runner()
