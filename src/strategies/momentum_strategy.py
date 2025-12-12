from typing import Optional, Dict, Any
import logging

# adjust import to match your aggressive refactor layout
from src.core.strategy.base import BaseStrategy


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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
        # ---------------- DEBUG STEP 2 #1 ----------------
        logger.debug("[STRATEGY DEBUG] %s on_tick ENTERED with tick: %s", self.meta.name, tick)


        # append incoming tick to strategy context
        try:
            ctx.append_tick(tick)
        except Exception as e:
            print(f"[STRATEGY ERROR] ctx.append_tick failed: {e}")
            return

        # ---------------- DEBUG STEP 2 #2 ----------------
        try:
            prices = ctx.prices(self.long + 5)
            print(f"[STRATEGY DEBUG] prices_len={len(prices)} (needed>={self.long})")
        except Exception as e:
            print(f"[STRATEGY ERROR] ctx.prices() failed: {e}")
            return

        if len(prices) < self.long:
            print(f"[STRATEGY DEBUG] insufficient prices: have {len(prices)}, need {self.long}")
            return

        # ---------------- DEBUG STEP 2 #3 ----------------
        try:
            short_sma = sum(prices[-self.short:]) / self.short
            long_sma = sum(prices[-self.long:]) / self.long
            last_price = prices[-1]
            print(f"[STRATEGY DEBUG] SMA calculated: short={short_sma}, long={long_sma}, last={last_price}")
        except Exception as e:
            print(f"[STRATEGY ERROR] SMA calculation failed: {e}")
            return

        # signal logic
        if short_sma > long_sma and self.last_signal != "LONG":
            print(f"[STRATEGY DEBUG] LONG signal triggered")
            self.last_signal = "LONG"
            self.place_limit(order_manager, "B", last_price, self.qty, self.exchange)

        elif short_sma < long_sma and self.last_signal == "LONG":
            print(f"[STRATEGY DEBUG] EXIT signal triggered")
            self.last_signal = "EXIT"
            self.place_limit(order_manager, "S", last_price, self.qty, self.exchange)
