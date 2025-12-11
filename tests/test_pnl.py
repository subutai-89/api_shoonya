# tests/test_pnl.py
import sys, os, json

# ensure project root on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core.strategy.pnl import PnLEngine


def almost(a, b, eps=1e-6):
    return abs(a - b) < eps


def run_test():
    print("\n=== PNL ENGINE FULL TEST ===")

    results = {}

    # ---------------------------------------------------------
    # 1) BASIC POSITIONING
    # ---------------------------------------------------------
    print("\n--- TEST 1: OPEN LONG POSITION ---")
    p = PnLEngine()
    p.on_trade({"side": "BUY", "qty": 100, "price": 10.0})
    snap = p.snapshot()

    assert snap.qty == 100
    assert almost(snap.avg_price, 10.0)
    assert snap.realized == 0
    assert snap.unrealized == 0

    print("PASS: opened long 100 @ 10")


    print("\n--- TEST 2: OPEN SHORT POSITION ---")
    p = PnLEngine()
    p.on_trade({"side": "SELL", "qty": 50, "price": 20.0})
    snap = p.snapshot()

    assert snap.qty == -50
    assert almost(snap.avg_price, 20.0)
    print("PASS: opened short 50 @ 20")


    # ---------------------------------------------------------
    # 2) PARTIAL EXIT LOGIC
    # ---------------------------------------------------------
    print("\n--- TEST 3: PARTIAL EXIT REALIZED PNL ---")
    p = PnLEngine()
    p.on_trade({"side": "BUY", "qty": 100, "price": 10.0})

    res = p.on_trade({"side": "SELL", "qty": 40, "price": 12.0})
    snap = res["snapshot"]

    assert almost(res["realized_pnl_change"], 80.0)
    assert almost(snap.realized, 80.0)
    assert snap.qty == 60
    assert almost(snap.avg_price, 10.0)

    print("PASS: partial close +80 realized")


    # ---------------------------------------------------------
    # 3) FULL EXIT LOGIC
    # ---------------------------------------------------------
    print("\n--- TEST 4: FULL EXIT REALIZED PNL + UNREALIZED ---")
    p = PnLEngine()

    p.on_trade({"side": "BUY", "qty": 50, "price": 20.0})
    p.update_unrealized(25.0)

    assert almost(p.snapshot().unrealized, 250)

    res = p.on_trade({"side": "SELL", "qty": 50, "price": 22.0})
    snap = res["snapshot"]

    assert almost(res["realized_pnl_change"], 100.0)
    assert snap.qty == 0
    assert snap.avg_price == 0.0
    assert snap.unrealized == 0.0

    print("PASS: full close +100 realized")


    # ---------------------------------------------------------
    # 4) FLIP LONG → SHORT
    # ---------------------------------------------------------
    print("\n--- TEST 5: FLIP LONG TO SHORT ---")
    p = PnLEngine()
    p.on_trade({"side": "BUY", "qty": 100, "price": 5.0})

    res = p.on_trade({"side": "SELL", "qty": 150, "price": 6.0})
    snap = res["snapshot"]

    assert almost(res["realized_pnl_change"], 100.0)
    assert snap.qty == -50
    assert almost(snap.avg_price, 6.0)

    print("PASS: flipped to short -50 @ 6 with +100 realized")


    # ---------------------------------------------------------
    # 5) FLIP SHORT → LONG
    # ---------------------------------------------------------
    print("\n--- TEST 6: FLIP SHORT TO LONG ---")
    p = PnLEngine()
    p.on_trade({"side": "SELL", "qty": 80, "price": 50.0})

    res = p.on_trade({"side": "BUY", "qty": 100, "price": 40.0})
    snap = res["snapshot"]

    assert almost(res["realized_pnl_change"], 800.0)
    assert snap.qty == 20
    assert almost(snap.avg_price, 40.0)

    print("PASS: flipped to long 20 @ 40 with +800 realized")


    # ---------------------------------------------------------
    # 6) UNREALIZED UPDATES
    # ---------------------------------------------------------
    print("\n--- TEST 7: UNREALIZED PNL ---")
    p = PnLEngine()
    p.on_trade({"side": "BUY", "qty": 10, "price": 100.0})

    p.update_unrealized(110.0)
    assert almost(p.snapshot().unrealized, 100)

    p.update_unrealized(90.0)
    assert almost(p.snapshot().unrealized, -100)

    print("PASS: unrealized updates correctly")


    # ---------------------------------------------------------
    # 7) SIDE STRING VARIANTS
    # ---------------------------------------------------------
    print("\n--- TEST 8: SIDE VARIANTS ---")
    p = PnLEngine()

    p.on_trade({"side": "buy", "qty": 10, "price": 10})
    p.on_trade({"side": "SELL", "qty": 5, "price": 12})

    snap = p.snapshot()

    assert snap.qty == 5
    assert almost(snap.realized, (12 - 10) * 5)

    print("PASS: side variants BUY/buy/SELL supported")


    # ---------------------------------------------------------
    # 8) INVALID INPUT SAFETY
    # ---------------------------------------------------------
    print("\n--- TEST 9: INVALID / ZERO SAFETY ---")
    p = PnLEngine()

    p.on_trade({"side": "BUY", "qty": 0, "price": 100})
    assert p.snapshot().qty == 0

    p.on_trade({"side": None, "qty": 10, "price": 10})
    assert p.snapshot().qty == 0

    p.on_trade({"side": "??", "qty": 10, "price": 10})
    assert p.snapshot().qty == 0

    print("PASS: invalid sides and zero qty safely ignored")


    print("\n🎉 ALL PNL TESTS PASSED SUCCESSFULLY!\n")


# PyTest identifier
def test_runner():
    run_test()


if __name__ == "__main__":
    test_runner()
