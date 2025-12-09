# src/engine/risk_engine.py
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional
import time
import logging

logger = logging.getLogger(__name__)


class RiskViolation(Exception):
    """Raised when a proposed order violates risk policy."""
    pass


@dataclass
class RiskPolicy:
    """
    Per-strategy risk limits. Tune these when enabling a strategy live.
    - max_qty_per_order: maximum absolute quantity in a single order
    - max_notional_per_order: maximum notional for a single order (price * qty)
    - max_position_qty: maximum absolute position allowed for the strategy (exposure)
    - max_daily_loss: maximum realized loss per day (positive number, e.g. 1000 means stop after -1000)
    - allow_short: whether shorting is allowed
    """
    max_qty_per_order: int = 1000
    max_notional_per_order: float = 1e9
    max_position_qty: int = 10000
    max_daily_loss: float = 1e9
    allow_short: bool = True


@dataclass
class _StrategyState:
    realized_today: float = 0.0
    last_reset_ts: float = field(default_factory=lambda: time.time())
    locked: Lock = field(default_factory=Lock)


class RiskEngine:
    """
    Lightweight risk engine with per-strategy policies and runtime state.
    Usage:
        risk = RiskEngine()
        risk.set_policy('my_strat', RiskPolicy(max_qty_per_order=10, ...))
        risk.check_order(order_dict)  # raises RiskViolation if not allowed
        risk.on_fill(order_dict, pnl_delta)  # update realized PnL for strategy
    """

    def __init__(self, timezone_reset_hour: int = 0):
        # strategy_name -> RiskPolicy
        self._policies: Dict[str, RiskPolicy] = {}
        # strategy_name -> _StrategyState
        self._state: Dict[str, _StrategyState] = {}
        # lock for policy/state maps
        self._map_lock = Lock()
        self.timezone_reset_hour = timezone_reset_hour
        self.global_kill = False

    def set_policy(self, strategy_name: str, policy: RiskPolicy):
        with self._map_lock:
            self._policies[strategy_name] = policy
            if strategy_name not in self._state:
                self._state[strategy_name] = _StrategyState()

    def get_policy(self, strategy_name: str) -> Optional[RiskPolicy]:
        return self._policies.get(strategy_name)

    def _get_state(self, strategy_name: str) -> _StrategyState:
        with self._map_lock:
            if strategy_name not in self._state:
                self._state[strategy_name] = _StrategyState()
            return self._state[strategy_name]

    def enable_global_kill(self):
        self.global_kill = True
        logger.warning("RiskEngine: GLOBAL KILL SWITCH ENABLED")

    def disable_global_kill(self):
        self.global_kill = False
        logger.info("RiskEngine: GLOBAL KILL SWITCH DISABLED")

    # ---------------- checks ----------------
    def check_order(self, order: dict):
        """
        Validate an order dict before sending.
        Expects order to include either:
          - 'meta': {'strategy_name': '...'} OR
          - 'strategy_name' top-level key
        Order keys: buy_or_sell, quantity, price (optional), tradingsymbol
        Raises RiskViolation on failure.
        """
        if self.global_kill:
            raise RiskViolation("Global kill switch is ON")

        meta = order.get("meta") or {}
        strategy_name = meta.get("strategy_name") or order.get("strategy_name")
        if not strategy_name:
            # If unknown, allow by default but log a warning
            logger.debug("RiskEngine: no strategy_name in order; skipping checks")
            return

        policy = self.get_policy(strategy_name) or RiskPolicy()
        qty = int(order.get("quantity") or 0)
        if qty == 0:
            raise RiskViolation("Order quantity is zero")

        # check no-shorting policy
        side = order.get("buy_or_sell")  # expected 'B' or 'S' or 'BUY'/'SELL'
        normalized_side = str(side).upper()[0] if side is not None else None
        if normalized_side == "S" and not policy.allow_short:
            raise RiskViolation("Shorting is not allowed for this strategy")

        # absolute qty checks
        if abs(qty) > policy.max_qty_per_order:
            raise RiskViolation(f"Order qty {qty} exceeds max per-order {policy.max_qty_per_order}")

        # notional check if price provided
        price = float(order.get("price") or 0.0)
        notional = abs(price * qty) if price else 0.0
        if policy.max_notional_per_order and notional > float(policy.max_notional_per_order):
            raise RiskViolation(f"Order notional {notional} exceeds max {policy.max_notional_per_order}")

        # check position limit (we can't see current position here reliably; best-effort: order may include current_position)
        current_pos = int(order.get("current_position") or 0)
        prospective_pos = current_pos + (qty if normalized_side == "B" else -qty)
        if abs(prospective_pos) > policy.max_position_qty:
            raise RiskViolation(f"Prospective position {prospective_pos} exceeds max position {policy.max_position_qty}")

        # check daily loss
        state = self._get_state(strategy_name)
        # reset daily if required (simple day rollover based on local time)
        # For simplicity we reset if 24h passed since last reset
        if time.time() - state.last_reset_ts > 24 * 3600:
            state.realized_today = 0.0
            state.last_reset_ts = time.time()

        if state.realized_today <= -abs(policy.max_daily_loss):
            raise RiskViolation(f"Strategy {strategy_name} has already hit max daily loss {policy.max_daily_loss}")

        # passed all checks
        logger.debug("RiskEngine: order passed checks for %s", strategy_name)
        return

    # ---------------- updates ----------------
    def on_fill(self, order: dict, pnl_delta: float):
        """Called after a fill / realized pnl change to update daily totals."""
        meta = order.get("meta") or {}
        strategy_name = meta.get("strategy_name") or order.get("strategy_name")
        if not strategy_name:
            logger.debug("RiskEngine.on_fill: no strategy_name; skipping state update")
            return

        state = self._get_state(strategy_name)
        with state.locked:
            state.realized_today += float(pnl_delta)
            logger.debug("RiskEngine: updated realized_today for %s: %s", strategy_name, state.realized_today)

            # enforce max_daily_loss: we can optionally flip global_kill or set a flag
            policy = self.get_policy(strategy_name) or RiskPolicy()
            if state.realized_today <= -abs(policy.max_daily_loss):
                logger.warning("RiskEngine: strategy %s exceeded max_daily_loss (%.2f); enabling global kill",
                               strategy_name, policy.max_daily_loss)
                # choose to enable global kill to stop everything, or we could set per-strategy kill
                self.enable_global_kill()
