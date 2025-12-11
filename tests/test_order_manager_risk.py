import sys, os, time, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


from typing import Dict, Any

from src.engine.order_manager import OrderManager
from src.engine.risk_engine import RiskPolicy


class MockAPI:
    def place_order(self, **kwargs) -> Dict[str, Any]:
        return {"mock": True}

    def modify_order(self, **kwargs) -> Dict[str, Any]:
        return {"mock_modify": True}

    def cancel_order(self, **kwargs) -> Dict[str, Any]:
        return {"cancelled": True}

    def exit_order(self, **kwargs) -> Dict[str, Any]:
        return {"exited": True}

    def get_order_book(self):
        return []

    def single_order_history(self, orderno: str):
        return {}

    def get_positions(self):
        return []

    def convert_position(self, **kwargs):
        return {"converted": True}

    def get_trade_book(self):
        return []

    def get_holdings(self):
        return []

    def get_limits(self, **kwargs):
        return {}

    def get_order_status(self, orderno: str):
        return {}

    def get_market_depth(self, **kwargs):
        return {}

    def get_time_price_series(self, **kwargs):
        return []


def run():
    api = MockAPI()
    om = OrderManager(api)

    om.set_risk_policy("test", RiskPolicy(max_qty_per_order=1))

    # Should be rejected
    print("Reject:", om.place_order(
        "B", "C", "NSE", "TEST", quantity=5, price_type="LMT", price=100, strategy_name="test"
    ))

    # Should pass
    print("Accept:", om.place_order(
        "B", "C", "NSE", "TEST", quantity=1, price_type="LMT", price=100, strategy_name="test"
    ))


# PyTest identifier
def test_runner():
    run()



if __name__ == "__main__":
    test_runner()
