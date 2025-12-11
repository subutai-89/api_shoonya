import sys, os, time, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.engine.risk_engine import RiskEngine, RiskPolicy, RiskViolation

def run_test():
    # Initialize risk engine and set a policy
    risk = RiskEngine()
    policy = RiskPolicy(max_qty_per_order=10, max_position_qty=20, max_daily_loss=1000, allow_short=True)
    risk.set_policy("test_strat", policy)

    # Example order that exceeds max_qty_per_order
    order = {
        "meta": {"strategy_name": "test_strat"},
        "buy_or_sell": "B",
        "quantity": 15,  # This exceeds max_qty_per_order
        "price": 100,
        "product_type": "C",
        "exchange": "NSE",
        "tradingsymbol": "TEST"
    }

    try:
        # Check order using the risk engine
        risk.check_order(order)
        print("Order passed risk checks")
    except RiskViolation as e:
        print(f"Expected rejection: {e}")

    # Order within limit
    valid_order = {
        "meta": {"strategy_name": "test_strat"},
        "buy_or_sell": "B",
        "quantity": 5,
        "price": 100,
        "product_type": "C",
        "exchange": "NSE",
        "tradingsymbol": "TEST"
    }

    try:
        risk.check_order(valid_order)
        print("Valid order passed risk checks")
    except RiskViolation as e:
        print(f"Unexpected rejection: {e}")

# PyTest identifier
def test_runner():
    run_test()


if __name__ == "__main__":
    test_runner()
