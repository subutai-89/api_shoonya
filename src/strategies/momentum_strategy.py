# src/strategies/momentum_strategy.py

from typing import Optional, Dict, Any

# adjust import to match your aggressive refactor layout
from src.core.strategy.base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    DEFAULT_NAME = "momentum_strategy"
    DEFAULT_SYMBOL = "TEST"

    def __init__(
        self,
        name: str = DEFAULT_NAME,
        symbol: str = DEFAULT_SYMBOL,
        params: Optional[Dict[str, Any]] = None,
        window_size: int = 200,
    ):
        """
        Momentum strategy with safe defaults.
        Always pass a dict to BaseStrategy.__init__ to satisfy static type checkers.
        """
        # ensure params is a real dict before passing to BaseStrategy
        safe_params: Dict[str, Any] = params or {}

        super().__init__(name=name, symbol=symbol, params=safe_params, window_size=window_size)

        # safe_params is a dict; use .get with defaults
        self.short = safe_params.get("short", 5)
        self.long = safe_params.get("long", 20)
        self.qty = safe_params.get("qty", 1)
        self.exchange = safe_params.get("exchange", "NSE")

        self.last_signal = None

    def on_start(self, api, order_manager):
        # optional startup logic
        pass

    def on_stop(self, api, order_manager):
        # optional stop logic
        pass

    def on_tick(self, api, order_manager, tick, ctx):
        # append incoming tick to strategy context
        ctx.append_tick(tick)
        prices = ctx.prices(self.long + 5)

        if len(prices) < self.long:
            return

        short_sma = sum(prices[-self.short:]) / self.short
        long_sma = sum(prices[-self.long:]) / self.long
        last_price = prices[-1]

        if short_sma > long_sma and self.last_signal != "LONG":
            self.last_signal = "LONG"
            self.place_limit(order_manager, "B", last_price, self.qty, self.exchange)

        elif short_sma < long_sma and self.last_signal == "LONG":
            self.last_signal = "EXIT"
            self.place_limit(order_manager, "S", last_price, self.qty, self.exchange)
