# tests/test_pnl_portfolio.py
import sys, os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core.portfolio.manager import PortfolioManager
from src.core.strategy.base import BaseStrategy
from src.engine.strategy_engine import StrategyEngine


class FakeAPI:
    pass


class FakeOrderManager:
    pass


class MockStrat(BaseStrategy):
    def __init__(self, name, symbol):
        super().__init__(name=name, symbol=symbol, params={}, window_size=10)

    # --- required abstract methods ---
    def on_start(self, api, order_manager):
        pass

    def on_tick(self, api, order_manager, tick, ctx):
        pass

    def on_stop(self, api, order_manager):
        pass



def run_test():
    print("\n=== PORTFOLIO + PNL INTEGRATION TEST ===")

    api = FakeAPI()
    om = FakeOrderManager()
    engine = StrategyEngine(api, om)

    portfolio = PortfolioManager(starting_equity=100000.0)
    engine.portfolio = portfolio

    stratA = MockStrat("A", "AAA")
    stratB = MockStrat("B", "BBB")
    engine.register(stratA)
    engine.register(stratB)
    portfolio.add_strategy(stratA)
    portfolio.add_strategy(stratB)

    # ---------------------------------------
    print("\n--- STEP 1: BUY AAA 2 @ 100 ---")
    engine.on_order_update({
        "meta": {"strategy_name": "A"},
        "tradingsymbol": "AAA",
        "buy_or_sell": "B",
        "price": 100,
        "quantity": 2
    })

    # ---------------------------------------
    print("\n--- STEP 2: SELL AAA 1 @ 110 ---")
    engine.on_order_update({
        "meta": {"strategy_name": "A"},
        "tradingsymbol": "AAA",
        "buy_or_sell": "S",
        "price": 110,
        "quantity": 1
    })

    # ---------------------------------------
    print("\n--- STEP 3: SHORT BBB 3 @ 50 ---")
    engine.on_order_update({
        "meta": {"strategy_name": "B"},
        "tradingsymbol": "BBB",
        "buy_or_sell": "S",
        "price": 50,
        "quantity": 3
    })

    # ---------------------------------------
    print("\n--- STEP 4: COVER BBB 3 @ 40 ---")
    engine.on_order_update({
        "meta": {"strategy_name": "B"},
        "tradingsymbol": "BBB",
        "buy_or_sell": "B",
        "price": 40,
        "quantity": 3
    })

    # ---------------------------------------
    print("\n--- FINAL PORTFOLIO SNAPSHOT ---")
    snap = portfolio.snapshot()
    print(json.dumps(snap, indent=2))

    # quick checks
    assert snap["positions_by_symbol"]["AAA"]["qty"] == 1
    assert snap["positions_by_symbol"]["BBB"]["qty"] == 0
    assert snap["total_realized"] > 0

    print("\n🎉 PORTFOLIO + PNL INTEGRATION TEST PASSED!\n")


# PyTest identifier
def test_runner():
    run_test()


if __name__ == "__main__":
    test_runner()

