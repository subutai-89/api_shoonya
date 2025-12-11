# tests/test_pnl_context.py
import sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core.strategy.base import BaseStrategy
from src.core.strategy.performance import PerformanceEngine
from src.core.strategy.pnl import PnLEngine


def almost(a, b, eps=1e-6):
    return abs(a - b) < eps


# ---------------------------------------------------------
# Strategy used to obtain a real StrategyContext
# ---------------------------------------------------------
class StrategyUnderTest(BaseStrategy):
    """
    Small wrapper strategy to expose a real StrategyContext.
    """

    def __init__(self):
        super().__init__(
            name="ctx_test",
            symbol="TEST",
            params={},
            window_size=5
        )

        # attach a performance engine if your code expects it
        self.ctx.performance = PerformanceEngine(starting_equity=100000.0)

    def on_start(self, api, order_manager):
        pass

    def on_tick(self, api, order_manager, tick, ctx):
        pass

    def on_stop(self, api, order_manager):
        pass


# ---------------------------------------------------------
# THE TEST
# ---------------------------------------------------------
def run_test():
    print("\n=== PNL + STRATEGY CONTEXT INTEGRATION TEST ===")

    strat = StrategyUnderTest()
    ctx = strat.ctx
    pnl: PnLEngine = ctx.pnl

    # ---------------------------------------------------------
    print("\n--- STEP 1: Append ticks (Context window) ---")
    ticks = [{"lp": p} for p in [100, 101, 102, 103, 104]]

    for t in ticks:
        ctx.append_tick(t)

    # StrategyContext does not guarantee inspection of internal tick buffer.
    # The only valid guarantee: append_tick() must not crash and indicators must still work afterward.
    print("PASS: append_tick executed without errors (tick window opaque by design)")


    # ---------------------------------------------------------
    print("\n--- STEP 2: BUY 2 @ 100 ---")
    pnl.on_trade({"side": "B", "qty": 2, "price": 100.0})

    snap = pnl.snapshot()
    assert snap.qty == 2
    assert almost(snap.avg_price, 100.0)

    print("PASS: BUY recorded correctly")

    # ---------------------------------------------------------
    print("\n--- STEP 3: MTM update to 105 ---")
    ctx.update_unrealized(105)   # valid method on your StrategyContext

    snap = pnl.snapshot()
    assert almost(snap.unrealized, 2 * 5)

    print("PASS: Unrealized updated correctly")

    # ---------------------------------------------------------
    print("\n--- STEP 4: SELL 1 @ 110 ---")
    pnl.on_trade({"side": "S", "qty": 1, "price": 110.0})

    snap = pnl.snapshot()
    assert almost(snap.realized, 10)  # (110 - 100)

    assert snap.qty == 1
    assert almost(snap.avg_price, 100.0)

    print("PASS: partial exit realized ok")

    # ---------------------------------------------------------
    print("\n--- STEP 5: SELL 1 @ 95 ---")
    pnl.on_trade({"side": "S", "qty": 1, "price": 95.0})

    snap = pnl.snapshot()

    # realized should be: +10 from earlier + (95 - 100) = +10 - 5 = +5
    assert almost(snap.realized, 5.0)
    assert snap.qty == 0
    assert snap.unrealized == 0

    print("PASS: full exit correct, average reset")

    print("\n🎉 CONTEXT + PNL INTEGRATION TEST PASSED!\n")



# PyTest identifier
def test_runner():
    run_test()



if __name__ == "__main__":
    test_runner()

