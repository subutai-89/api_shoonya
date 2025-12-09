# src/core/portfolio/manager.py
from typing import Dict, Any, Optional, List
import logging
import time

from src.core.strategy.base import BaseStrategy

logger = logging.getLogger(__name__)


class PortfolioManager:
    """
    Simple PortfolioManager (push model).

    Responsibilities:
      - maintain registry of strategies (by name)
      - aggregate positions per-symbol across strategies
      - aggregate realized/unrealized PnL and simple equity curve
      - accept order updates (push) and route them into strategies so their context/pnl updates
    """

    def __init__(self, starting_equity: float = 100000.0):
        self.starting_equity = float(starting_equity)
        # strategy_name -> BaseStrategy instance
        self._strategies: Dict[str, BaseStrategy] = {}
        # equity curve points: list of {'ts': ts, 'equity': value}
        self.equity_curve: List[Dict[str, Any]] = []
        # initialize first equity point
        self._record_equity_point(self.starting_equity)

    # ---------------- strategy registry ----------------
    def add_strategy(self, strategy: BaseStrategy):
        name = strategy.meta.name
        if name in self._strategies:
            raise ValueError(f"Strategy '{name}' already registered in portfolio")
        self._strategies[name] = strategy
        logger.info("PortfolioManager: added strategy %s", name)

    def remove_strategy(self, name: str):
        self._strategies.pop(name, None)
        logger.info("PortfolioManager: removed strategy %s", name)

    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        return self._strategies.get(name)

    def list_strategies(self) -> List[str]:
        return list(self._strategies.keys())

    # ---------------- order / fill routing ----------------
    def on_order_update(self, order: Dict[str, Any]):
        """
        Push model entry-point: accept an order update dict (e.g. from OrderManager/webhook).
        We attempt to route to the strategy identified in order['meta']['strategy_name']
        or try to heuristically parse remarks. If routed, we call the strategy's on_order_update
        which is expected to update the strategy.ctx and pnl accordingly.
        """
        if not isinstance(order, dict):
            logger.warning("PortfolioManager.on_order_update received non-dict order: %r", order)
            return

        strategy_name = None
        meta = order.get("meta") or {}
        if isinstance(meta, dict):
            strategy_name = meta.get("strategy_name") or meta.get("strategy")

        if not strategy_name:
            # fallback to naive parse of remarks
            remarks = order.get("remarks") or order.get("note") or ""
            if isinstance(remarks, str) and "strategy=" in remarks:
                try:
                    strategy_name = remarks.split("strategy=")[1].split()[0].strip()
                except Exception:
                    strategy_name = None

        if strategy_name and strategy_name in self._strategies:
            strat = self._strategies[strategy_name]
            try:
                # call strategy hook to let it process the order/fill
                # note: BaseStrategy.on_order_update expects (api, order_manager, order),
                # here we don't have api/order_manager in portfolio — that's okay,
                # BaseStrategy.on_order_update only uses order to update ctx.
                strat.on_order_update(None, None, order)
            except Exception:
                logger.exception("Error routing order update to strategy %s", strategy_name)
                return
        else:
            # broadcast: if no strategy matched, broadcast to all strategies
            for sname, strat in self._strategies.items():
                try:
                    strat.on_order_update(None, None, order)
                except Exception:
                    logger.exception("Error broadcasting order update to strategy %s", sname)

        # After routing, update aggregated equity point
        self._record_equity_point(self._compute_total_equity())

    # ---------------- aggregation helpers ----------------
    def _aggregate_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns mapping: symbol -> {qty, avg_price, notional, strategies: {name: {qty, avg_price}}}
        """
        agg: Dict[str, Dict[str, Any]] = {}
        for sname, strat in self._strategies.items():
            try:
                ctx = getattr(strat, "ctx", None)
                if not ctx:
                    continue
                # assume ctx has pnl with qty/avg_price/unrealized/realized
                pnl = getattr(ctx, "pnl", None)
                if not pnl:
                    continue
                sym = getattr(ctx, "symbol", None) or strat.meta.symbol
                if sym is None:
                    continue
                s_qty = int(pnl.qty)
                s_avg = float(pnl.avg_price or 0.0)
                if sym not in agg:
                    agg[sym] = {"qty": 0, "notional": 0.0, "avg_price": 0.0, "strategies": {}}
                # store per-strategy snapshot
                agg[sym]["strategies"][sname] = {"qty": s_qty, "avg_price": s_avg}
                # accumulate qty and notional for the symbol
                agg[sym]["qty"] += s_qty
                agg[sym]["notional"] += s_qty * s_avg
            except Exception:
                logger.exception("Error aggregating for strategy %s", sname)
        # finalize avg_price per symbol (weighted by notional if qty != 0)
        for sym, info in agg.items():
            total_qty = info["qty"]
            if total_qty != 0:
                # avoid divide by zero — compute naive avg
                info["avg_price"] = (info["notional"] / total_qty) if total_qty != 0 else 0.0
            else:
                info["avg_price"] = 0.0
        return agg

    def _compute_total_realized(self) -> float:
        total = 0.0
        for strat in self._strategies.values():
            try:
                pnl = getattr(getattr(strat, "ctx", None), "pnl", None)
                if pnl:
                    total += float(getattr(pnl, "realized", 0.0))
            except Exception:
                logger.exception("Error summing realized for %s", getattr(strat, "meta", {}).get("name"))
        return total

    def _compute_total_unrealized(self) -> float:
        total = 0.0
        for strat in self._strategies.values():
            try:
                pnl = getattr(getattr(strat, "ctx", None), "pnl", None)
                if pnl:
                    total += float(getattr(pnl, "unrealized", 0.0))
            except Exception:
                logger.exception("Error summing unrealized for %s", getattr(strat, "meta", {}).get("name"))
        return total

    def _compute_total_equity(self) -> float:
        return self.starting_equity + self._compute_total_realized() + self._compute_total_unrealized()

    def _record_equity_point(self, equity: float):
        self.equity_curve.append({"ts": time.time(), "equity": float(equity)})

    # ---------------- public snapshots / reports ----------------
    def snapshot(self) -> Dict[str, Any]:
        return {
            "strategies": list(self._strategies.keys()),
            "positions_by_symbol": self._aggregate_positions(),
            "total_realized": self._compute_total_realized(),
            "total_unrealized": self._compute_total_unrealized(),
            "last_equity": self.equity_curve[-1]["equity"] if self.equity_curve else self.starting_equity,
            "equity_curve_len": len(self.equity_curve),
        }

    def performance_report(self) -> Dict[str, Any]:
        """
        Lightweight summary combining key portfolio stats.
        """
        pos = self._aggregate_positions()
        return {
            "last_equity": self.equity_curve[-1]["equity"] if self.equity_curve else self.starting_equity,
            "positions": pos,
            "realized": self._compute_total_realized(),
            "unrealized": self._compute_total_unrealized(),
            "equity_curve": list(self.equity_curve),
        }
