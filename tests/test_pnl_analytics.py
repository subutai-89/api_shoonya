# tests/test_pnl_analytics.py
import sys, os, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core.strategy.pnl import PnLEngine

def run():
    p = PnLEngine()
    print("Initial snapshot:", p.snapshot())

    # open long: buy 1 @100
    p.update_from_fill("B", 100.0, 1)
    print("After buy:", p.snapshot())

    # price moves to 98 (adverse)
    p.update_unrealized(98.0)
    print("MTM 98:", p.snapshot(), "open_trade:", p.open_trade)

    # price moves to 95 (max adverse)
    p.update_unrealized(95.0)
    print("MTM 95:", p.snapshot(), "open_trade:", p.open_trade)

    # price moves favorable to 110
    p.update_unrealized(110.0)
    print("MTM 110:", p.snapshot(), "open_trade:", p.open_trade)

    # close sell at 110 -> should finalize trade
    p.update_from_fill("S", 110.0, 1)
    print("After close:", p.snapshot())
    print("Trades ledger:", p.trades)

if __name__ == "__main__":
    run()
