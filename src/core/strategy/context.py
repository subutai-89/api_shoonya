from typing import Optional, Any, Dict
from .indicators import RollingWindow
from .position import Position
from .pnl import PnLEngine
from .performance import PerformanceEngine, _safe_mean


class StrategyContext:
    def __init__(self, symbol: str, window_size=200, starting_equity: float = 0.0,
                 perf_sample_mode: str = "fills", perf_sample_interval: float = 10.0):
        self.symbol = symbol
        self.window = RollingWindow(window_size)
        self.last_tick = None
        self.position = Position()
        self.pnl = PnLEngine()
        self.state: Dict[str, Any] = {}

        # Performance engine with sampling controls
        self.performance = PerformanceEngine(
            starting_equity=starting_equity,
            sample_mode=perf_sample_mode,
            sample_interval=perf_sample_interval,
        )

        # Metadata assigned by BaseStrategy during initialization
        self.meta: Optional[Any] = None

    def append_tick(self, tick):
        self.window.append(tick)
        self.last_tick = tick

    def prices(self, n=None):
        arr = []
        data = self.window.all() if n is None else self.window.last(n)
        for t in data:
            if isinstance(t, dict):
                if "lp" in t:
                    arr.append(float(t["lp"]))
                elif "price" in t:
                    arr.append(float(t["price"]))
            else:
                arr.append(float(t))
        return arr

    def update_position_from_order(self, order):
        """
        Normalizes order fields and updates:
        - PnL engine
        - Position engine
        - Performance equity timeline
        """

        # ---- normalize side ----
        side = (
            order.get("transaction_type")
            or order.get("buy_or_sell")
            or order.get("side")
        )
        if side is None:
            return

        # normalize to "B" or "S"
        side = side.upper()
        if side.startswith("BUY") or side == "B":
            side = "B"
        elif side.startswith("SELL") or side == "S":
            side = "S"
        else:
            return  # unknown side → ignore

        # ---- normalize quantity ----
        qty = (
            order.get("filled_qty")
            or order.get("quantity")
            or order.get("qty")
            or 0
        )
        qty = int(qty)
        if qty <= 0:
            return

        # ---- normalize price ----
        price = float(order.get("price") or 0.0)

        # ---- update PnL engine ----
        # PnL engine uses a single method `update_from_fill(side, price, qty)`
        self.pnl.update_from_fill(side, price, qty)

        # ---- sync position object with PnL state ----
        self.position.qty = self.pnl.qty
        self.position.avg_price = self.pnl.avg_price
        self.position.realized_pnl = self.pnl.realized

        # ---- compute total equity and record snapshot ----
        total_equity = (
            self.performance.starting_equity
            + self.pnl.realized
            + self.pnl.unrealized
        )

        position_open = self.position.qty != 0
        self.performance.record_point(total_equity, position_open=position_open)
        

    def update_unrealized(self, mark_price: float):
        self.pnl.update_unrealized(mark_price)
        self.position.unrealized_pnl = self.pnl.unrealized

        # record equity snapshot on price updates (mark-to-market)
        # pass position_open flag — PerformanceEngine decides whether to keep it
        position_open = self.position.qty != 0
        total = (self.performance.starting_equity +
                 self.pnl.realized +
                 self.pnl.unrealized)
        self.performance.record_point(total, position_open=position_open)

    def performance_report(self, annualization: Optional[float] = None) -> Dict[str, Any]:
        """
        Return a unified performance report including PnL engine trade ledger metrics.
        """
        perf = self.performance.report(annualization=annualization)
        trades = getattr(self.pnl, "trades", []) or []

        # Only closing trades contain 'pnl'
        closing_trades = [t for t in trades if "pnl" in t]

        wins = [t for t in closing_trades if t["pnl"] > 0]
        losses = [t for t in closing_trades if t["pnl"] <= 0]

        win_count = len(wins)
        loss_count = len(losses)
        total_closed = win_count + loss_count

        avg_win = _safe_mean([t["pnl"] for t in wins]) if wins else None
        avg_loss = _safe_mean([t["pnl"] for t in losses]) if losses else None

        win_rate = (win_count / total_closed) if total_closed > 0 else None

        expectancy = None
        if avg_win is not None or avg_loss is not None:
            aw = avg_win or 0.0
            al = avg_loss or 0.0
            p = win_rate or 0.0
            expectancy = p * aw + (1 - p) * al

        perf["trade_stats"] = {
            "trade_count": len(trades),
            "closed_trades": total_closed,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "expectancy": expectancy,
        }
        return perf
