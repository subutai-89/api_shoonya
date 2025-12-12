from typing import Optional, Dict, Any
import logging

# Adjust import to match the structure in your repo
from src.core.strategy.base import BaseStrategy

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class BasicStrategy(BaseStrategy):
    DEFAULT_NAME = "basic_strategy"
    DEFAULT_SYMBOL = "NSE|1594"

    def __init__(
        self,
        name: str = DEFAULT_NAME,
        symbol: str = DEFAULT_SYMBOL,
        params: Optional[Dict[str, Any]] = None,
    ):
        """
        Basic strategy to print ticks. No trading logic.
        """
        # Ensure params is a valid dictionary before passing to BaseStrategy
        safe_params: Dict[str, Any] = params or {}
        
        super().__init__(name=name, symbol=symbol, params=safe_params)

    def on_start(self, api, order_manager):
        # Optional startup logic
        pass

    def on_stop(self, api, order_manager):
        # Optional stop logic
        pass

    def on_tick(self, api, order_manager, tick, ctx):
        """
        Print the tick received and log the processing.
        """
        logger.debug("[STRATEGY DEBUG] BasicStrategy on_tick ENTERED with tick: %s", tick)

        # Log tick reception and processing
        print(f"[STRATEGY DEBUG] BasicStrategy received tick: {tick}")

        # Additional log to confirm processing
        logger.debug("[STRATEGY DEBUG] Tick processed by BasicStrategy.")

