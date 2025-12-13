from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from src.core.strategy.meta import StrategyMeta
from src.core.strategy.context import StrategyContext
from src.engine.risk_engine import RiskPolicy

from .indicators import sma, ema, rsi, vwap


class BaseStrategy(ABC):
    """
    BaseStrategy now accepts optional args to configure StrategyContext / PerformanceEngine:
      - starting_equity: float (default 0.0)
      - perf_sample_mode: str (default 'fills')
      - perf_sample_interval: float (default 10.0 seconds)

    This lets you configure sampling per-strategy when constructing a strategy.
    """
    
    # Each strategy may define: risk = RiskPolicy(...)
    risk: Optional[RiskPolicy] = None
    
    def __init__(self,
                 name: str,
                 symbol: str,
                 params: Optional[Dict[str, Any]] = None,
                 window_size: int = 200,
                 starting_equity: float = 0.0,
                 perf_sample_mode: str = "fills",
                 perf_sample_interval: float = 10.0):

        # Strategy metadata
        # meta.symbol MUST be the token (string), not instrument name
        self.meta = StrategyMeta(name=name, symbol=symbol, params=params or {})

        # Strategy runtime context
        # forward sampling / starting equity to context so each strategy can use custom sampling
        self.ctx = StrategyContext(symbol, window_size,
                                   starting_equity=starting_equity,
                                   perf_sample_mode=perf_sample_mode,
                                   perf_sample_interval=perf_sample_interval)
        self.ctx.meta = self.meta

        self._running = False

    # Lifecycle
    def start(self, api, order_manager):
        self._running = True
        return self.on_start(api, order_manager)

    def stop(self, api, order_manager):
        self._running = False
        return self.on_stop(api, order_manager)

    def on_start(self, api, order_manager):
        pass

    def on_stop(self, api, order_manager):
        pass

    def on_order_update(self, api, order_manager, order):
        try:
            self.ctx.update_position_from_order(order)
        except Exception as e:
            print(f"Error updating position for {self.meta.name}: {e}")

    # Abstract tick handler
    @abstractmethod
    def on_tick(self, api, order_manager, tick, ctx):
        pass

    # Indicator helpers
    def sma(self, n): return sma(self.ctx.prices(n))
    def ema(self, n): return ema(self.ctx.prices(n), n)
    def rsi(self, n=14): return rsi(self.ctx.prices(n+1), n)
    def vwap(self): return vwap(self.ctx.window.all())

    # Order helper
    def place_limit(self, order_manager, side, price, qty, exchange="NSE", product_type="C"):
        # attach strategy identification so OrderManager & RiskEngine can route/check
        order = {
            "buy_or_sell": side,
            "product_type": product_type,
            "exchange": exchange,
            "tradingsymbol": self.ctx.symbol,
            "quantity": qty,
            "price_type": "LMT",
            "price": price,
            "meta": {"strategy_name": self.meta.name},
        }
        return order_manager.place_order(**order)

