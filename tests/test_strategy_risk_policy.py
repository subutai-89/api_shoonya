# tests/test_strategy_risk_policy.py
import sys, os, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core.strategy.base import BaseStrategy
from src.engine.strategy_engine import StrategyEngine
from src.engine.risk_engine import RiskPolicy
from src.engine.order_manager import OrderManager

# ---------------- Mock API ------------------------------------
class MockAPI:
    def place_order(self, **kwargs) -> dict:
        # show exactly what would be sent to the broker
        print("MOCK API CALLED with kwargs:", kwargs)
        return {"ok": True, "orderno": "MOCK123"}

    def modify_order(self, **kwargs) -> dict:
        return {"ok": True}

    def cancel_order(self, **kwargs) -> dict:
        return {"ok": True}

    def exit_order(self, **kwargs) -> dict:
        return {"ok": True}

    def get_order_book(self): return []
    def single_order_history(self, orderno): return {}
    def get_positions(self): return []
    def convert_position(self, **kwargs): return {}
    def get_trade_book(self): return []
    def get_holdings(self): return []
    def get_limits(self, **kwargs): return {}
    def get_order_status(self, orderno): return {}
    def get_market_depth(self, **kwargs): return {}
    def get_time_price_series(self, **kwargs): return []
# --------------------------------------------------------------

class RiskyStrategy(BaseStrategy):
    # class-level name for clarity (but BaseStrategy.meta.name is the source used)
    # risk policy declared at class-level (Option 1)
    risk = RiskPolicy(max_qty_per_order=1)

    def __init__(self):
        super().__init__(name="risky", symbol="TEST")

    # NOTE: parameter names MUST match BaseStrategy exactly (order_manager)
    def on_start(self, api, order_manager):
        pass

    def on_stop(self, api, order_manager):
        pass

    # parameter names must match the BaseStrategy signature
    def on_tick(self, api, order_manager, tick, ctx):
        # Try illegal order first (should be rejected by RiskEngine)
        print("Attempting illegal order (qty=5)...")
        res1 = self.place_limit(order_manager, "B", price=100, qty=5)
        print("Illegal order result:", res1)

        # Then attempt a legal order (qty=1) to show the broker gets called
        print("Attempting legal order (qty=1)...")
        res2 = self.place_limit(order_manager, "B", price=100, qty=1)
        print("Legal order result:", res2)

def run_test():
    print("=== STRATEGY RISK POLICY TEST ===")
    api = MockAPI()
    om = OrderManager(api)
    engine = StrategyEngine(api, om)

    strat = RiskyStrategy()

    # Register the strategy — this should auto-apply risk policy (StrategyEngine.register wires it)
    engine.register(strat)

    # Quick check: confirm the policy exists in OrderManager.risk_engine
    policy = om.risk_engine.get_policy("risky")
    print("Retrieved policy for 'risky':", policy)

    engine.start()
    # send a tick to trigger the strategy's on_tick (which will attempt both orders)
    engine.on_tick({"lp": 100})
    time.sleep(0.2)
    engine.stop()

if __name__ == "__main__":
    run_test()
