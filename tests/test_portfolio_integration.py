import sys, os, json, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.engine.strategy_engine import StrategyEngine
from src.core.portfolio.manager import PortfolioManager
from src.core.strategy.base import BaseStrategy


# ---------------------------------------------------------------------------
# Minimal mock strategy that uses PnL engine for testing
# ---------------------------------------------------------------------------
class MockStrategy(BaseStrategy):
    def __init__(self, name="mock_strat", symbol="TEST"):
        super().__init__(name=name, symbol=symbol, params={}, window_size=20)

    def on_start(self, api, order_manager):
        pass

    def on_stop(self, api, order_manager):
        pass

    def on_tick(self, api, order_manager, tick, ctx):
        pass  # Not needed for this test


# ---------------------------------------------------------------------------
# Fake API + Fake OrderManager (we only need minimal stubs)
# ---------------------------------------------------------------------------
class FakeAPI:
    pass


class FakeOrderManager:
    # Not used in this test directly
    pass


# ---------------------------------------------------------------------------
# TEST BEGINS
# ---------------------------------------------------------------------------
def run_test():
    print("\n=== PORTFOLIO INTEGRATION TEST ===")

    api = FakeAPI()
    om = FakeOrderManager()
    engine = StrategyEngine(api=api, order_manager=om, max_workers=1)

    portfolio = PortfolioManager(starting_equity=100000.0)
    engine.portfolio = portfolio   # <-- Step 2 integration

    # ---- register one strategy ----
    strat = MockStrategy(name="mockA", symbol="ABC-EQ")
    engine.register(strat)
    portfolio.add_strategy(strat)

    # ---- simulate fills routed via StrategyEngine.on_order_update ----
    # BUY 1 @ 100
    order1 = {
        "buy_or_sell": "B",
        "exchange": "NSE",
        "tradingsymbol": "ABC-EQ",
        "quantity": 1,
        "price": 100.0,
        "meta": {"strategy_name": "mockA"},
    }
    engine.on_order_update(order1)

    # Unrealized check should reflect MTM updates if market price changes
    # MTM @ 90
    strat.ctx.pnl.update_unrealized(90.0)

    # SELL 1 @ 105 (close position)
    order2 = {
        "buy_or_sell": "S",
        "exchange": "NSE",
        "tradingsymbol": "ABC-EQ",
        "quantity": 1,
        "price": 105.0,
        "meta": {"strategy_name": "mockA"},
    }
    engine.on_order_update(order2)

    # ---- portfolio snapshot ----
    snap = portfolio.snapshot()
    report = portfolio.performance_report()

    print("\n--- SNAPSHOT ---")
    print(json.dumps(snap, indent=2))

    print("\n--- PERFORMANCE REPORT ---")
    print(json.dumps(report, indent=2))

    # ---- Assertions ----
    assert snap["total_realized"] == 5.0, "Realized PnL should be +5"
    assert snap["total_unrealized"] == 0.0, "Unrealized PnL must return to zero"
    assert snap["positions_by_symbol"]["ABC-EQ"]["qty"] == 0, "Position must be flat"
    assert report["last_equity"] == 100005.0, "Equity should increase by +5"

    print("\n🎉 TEST PASSED: Portfolio integration is working correctly!")


# PyTest identifier
def test_runner():
    run_test()


if __name__ == "__main__":
    test_runner()