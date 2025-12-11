# tests/test_pnl_fuzz.py
import sys, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core.strategy.pnl import PnLEngine


def run_test():
    print("\n=== PNL ENGINE FUZZ TEST ===")
    p = PnLEngine()

    random.seed(123)

    for i in range(5000):
        side = random.choice(["B", "S"])
        qty = random.randint(1, 5)
        price = random.uniform(90, 110)

        p.on_trade({
            "side": side,
            "qty": qty,
            "price": price
        })

        # Random MTM
        mtm = random.uniform(90, 110)
        p.update_unrealized(mtm)

        snap = p.snapshot()

        # --- Invariants ---
        # 1) If qty == 0, avg_price must be zero
        if snap.qty == 0:
            assert abs(snap.avg_price) < 1e-9, f"avg_price not zero when flat: {snap}"

        # 2) unrealized must be 0 when flat
        if snap.qty == 0:
            assert abs(snap.unrealized) < 1e-9, f"unrealized not zero when flat: {snap}"

        # 3) No NaNs
        assert snap.realized == snap.realized
        assert snap.unrealized == snap.unrealized
        assert snap.avg_price == snap.avg_price

    print("\n🎉 PNL ENGINE PASSED 5000-STEP FUZZ TEST!\n")



# PyTest identifier
def test_runner():
    run_test()


if __name__ == "__main__":
    run_test()
