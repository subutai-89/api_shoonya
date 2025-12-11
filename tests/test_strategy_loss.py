# tests/test_strategy_engine_loss.py
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

    def simulate_fill(self, strat_name, side, price, qty):
        upd = {
            "strategy_name": strat_name,
            "transaction_type": side,
            "price": price,
            "filled_qty": qty,
        }
        self.updates.append(upd)
        return upd


class LossStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("loss_strat", "TEST", params=None, window_size=5)
        self.events = []
        self.ctx.performance = PerformanceEngine(starting_equity=100000)

    def on_start(self, api, order_manager):
        print("on_start")
        self.events.append("start")

    def on_tick(self, api, order_manager, tick, ctx):
        price = tick["lp"]
        ctx.append_tick(tick)
        ctx.update_unrealized(price)
        self.events.append(("tick", price))

        if price == 103:
            print("→ BUY @ 103")
            self.place_limit(order_manager, "B", 103, 1)

        if price == 95:
            print("→ SELL @ 95")
            self.place_limit(order_manager, "S", 95, 1)

    def on_stop(self, api, order_manager):
        print("on_stop")
        self.events.append("stop")


def run_test():
    api = MockAPI()
    om = MockOrderManager()
    eng = StrategyEngine(api, om)

    strat = LossStrategy()
    eng.register(strat)

    eng.start()

    ticks = [
        {"lp": 103},
        {"lp": 100},
        {"lp": 97},
        {"lp": 95},
    ]
    for t in ticks:
        eng.on_tick(t)
        time.sleep(0.05)

    # simulate fills
    eng.on_order_update(om.simulate_fill("loss_strat", "B", 103, 1))
    eng.on_order_update(om.simulate_fill("loss_strat", "S", 95, 1))

    time.sleep(0.2)
    eng.stop()

    print("\nPNL SNAPSHOT:", strat.ctx.pnl.snapshot())
    print("\nPERFORMANCE REPORT:\n", json.dumps(strat.ctx.performance_report(), indent=2))


# PyTest identifier
def test_runner():
    run_test()


if __name__ == "__main__":
    test_runner()
