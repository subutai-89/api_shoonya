# src/core/strategy/pnl.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import threading


@dataclass
class PnLSnapshot:
    qty: int
    avg_price: float
    realized: float
    unrealized: float


class PnLEngine:
    """
    Strict trade PnL with averaged-price accounting (B3).

    Behavior guarantees:
      - avg_price represents the weighted-average entry price for the current net position.
      - realized increases ONLY when part/all of an existing position is closed.
      - update_unrealized(market_price) computes unrealized separately (no effect on realized).
      - Partial closes and flips are handled deterministically:
          * Close existing side first (realize pnl using prev avg_price)
          * Any remainder becomes a new position at the fill price (avg_price set accordingly)
      - Minimal by default: no trade ledger. Set record_trades=True to keep a simple ledger for debugging.

    Notes:
      - This engine is intentionally small and in-memory. Let PortfolioManager persist or aggregate snapshots.
      - The engine is now thread-safe for common concurrent access patterns.
    """

    def __init__(self, record_trades: bool = False):
        # Net signed quantity: positive = long, negative = short
        self.qty: int = 0
        # Weighted average entry price for the current net position (0.0 when flat)
        self.avg_price: float = 0.0
        # Cumulative realized pnl (float)
        self.realized: float = 0.0
        # Last computed unrealized pnl (updated via update_unrealized)
        self.unrealized: float = 0.0

        # Optional simple trade ledger for debugging (list of dicts). Disabled by default.
        self.record_trades = bool(record_trades)
        if self.record_trades:
            self.trades: List[Dict[str, Any]] = []

        # Lock to guard concurrent updates if called from multiple threads.
        self._lock = threading.RLock()

    # -------------------------
    # Public helpers
    # -------------------------
    def update_from_fill(self, side: Optional[str], price: float, qty: int) -> None:
        """
        Apply a fill to the PnL engine.

        Args:
            side: 'B' or 'S' (also accepts 'BUY'/'SELL'); may be None.
            price: fill price (float)
            qty: filled quantity (positive int)
        """
        if qty <= 0:
            return

        # Normalize side: accept None safely
        s = (side or "").strip().upper()

        # accept 'B'/'BUY' and 'S'/'SELL'
        if s in ("BUY", "B"):
            s = "B"
        elif s in ("SELL", "S"):
            s = "S"
        else:
            # Unknown or missing side — do nothing
            return

        with self._lock:
            # Dispatch to handlers
            if s == "B":
                self._apply_buy(price=float(price), qty=int(qty))
            else:
                self._apply_sell(price=float(price), qty=int(qty))

            # After a fill we clear unrealized until caller recomputes with update_unrealized()
            self.unrealized = 0.0

    def on_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience wrapper that accepts a trade dictionary and applies it to the engine.

        Expected keys in trade dict:
            - 'side' : 'B'/'S' or 'BUY'/'SELL'
            - 'qty' : positive int
            - 'price' : fill price

        Returns:
            dict containing:
                {
                    "realized_pnl_change": float,   # change in realized due to this fill (may be 0)
                    "snapshot": PnLSnapshot        # current position snapshot after the fill
                }
        """
        side = trade.get("side")
        qty = int(trade.get("qty", 0))
        price = float(trade.get("price", 0.0))

        if qty <= 0:
            return {"realized_pnl_change": 0.0, "snapshot": self.snapshot()}

        # record realized before and after to compute delta returned to caller
        with self._lock:
            prev_realized = self.realized
            self.update_from_fill(side=side, price=price, qty=qty)
            realized_change = self.realized - prev_realized
            return {"realized_pnl_change": realized_change, "snapshot": self.snapshot()}

    def update_unrealized(self, market_price: float) -> None:
        """
        Compute unrealized PnL given current market price.
        Does NOT change realized or avg_price.
        """
        with self._lock:
            if self.qty == 0:
                self.unrealized = 0.0
            elif self.qty > 0:
                self.unrealized = (float(market_price) - self.avg_price) * self.qty
            else:
                self.unrealized = (self.avg_price - float(market_price)) * abs(self.qty)

    # -------------------------
    # Internal helpers
    # -------------------------
    def _apply_buy(self, price: float, qty: int) -> None:
        """
        Handle a buy fill.
        - If currently short: buy first closes short (realize using short avg_price).
        - Remaining qty (if any) becomes/increases a long position using weighted average.
        """
        # If currently short, close that first
        if self.qty < 0:
            closing = min(qty, abs(self.qty))
            # For shorts: realized = (short_entry - cover_price) * closing_qty
            self.realized += (self.avg_price - price) * closing

            # Optional trade record (single close event)
            if self.record_trades:
                self.trades.append({
                    "side": "COVER", "qty": closing, "entry_price": self.avg_price,
                    "exit_price": price, "pnl": (self.avg_price - price) * closing
                })

            # reduce short
            self.qty += closing
            qty -= closing

            # if fully closed, reset avg_price
            if self.qty == 0:
                self.avg_price = 0.0

        # Any remaining qty creates / increases long
        if qty > 0:
            if self.qty == 0:
                # new long position
                self.qty = qty
                self.avg_price = float(price)
                if self.record_trades:
                    self.trades.append({"side": "LONG_OPEN", "qty": qty, "price": price})
            elif self.qty > 0:
                # increase existing long -> weighted average
                prev_notional = self.avg_price * self.qty
                new_notional = float(price) * qty
                self.qty += qty
                self.avg_price = (prev_notional + new_notional) / self.qty
                if self.record_trades:
                    self.trades.append({"side": "LONG_ADD", "qty": qty, "price": price})
            else:
                # shouldn't happen: qty < 0 handled above
                pass

    def _apply_sell(self, price: float, qty: int) -> None:
        """
        Handle a sell fill.
        - If currently long: sell first closes long (realize using long avg_price).
        - Remaining qty (if any) becomes/increases a short position using weighted average.
        """
        # If currently long, close that first
        if self.qty > 0:
            closing = min(qty, self.qty)
            # Realized for long = (sell_price - entry_price) * closed_qty
            self.realized += (price - self.avg_price) * closing

            if self.record_trades:
                self.trades.append({
                    "side": "LONG_CLOSE", "qty": closing, "entry_price": self.avg_price,
                    "exit_price": price, "pnl": (price - self.avg_price) * closing
                })

            self.qty -= closing
            qty -= closing

            if self.qty == 0:
                self.avg_price = 0.0

        # Any remaining qty becomes/increases short
        if qty > 0:
            if self.qty == 0:
                # new short
                self.qty = -qty
                self.avg_price = float(price)
                if self.record_trades:
                    self.trades.append({"side": "SHORT_OPEN", "qty": qty, "price": price})
            elif self.qty < 0:
                # increase existing short -> weighted average on absolute notional
                prev_notional = self.avg_price * abs(self.qty)
                new_notional = float(price) * qty
                self.qty -= qty  # more negative
                self.avg_price = (prev_notional + new_notional) / abs(self.qty)
                if self.record_trades:
                    self.trades.append({"side": "SHORT_ADD", "qty": qty, "price": price})
            else:
                # shouldn't happen: qty > 0 handled above
                pass

    # -------------------------
    # Utilities
    # -------------------------
    def snapshot(self) -> PnLSnapshot:
        with self._lock:
            return PnLSnapshot(qty=self.qty, avg_price=self.avg_price,
                               realized=self.realized, unrealized=self.unrealized)

    def __repr__(self) -> str:
        with self._lock:
            return (f"<PnLEngine qty={self.qty} avg={self.avg_price:.4f} "
                    f"realized={self.realized:.4f} unrealized={self.unrealized:.4f}>")
