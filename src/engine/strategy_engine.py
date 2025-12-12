"""
StrategyEngine (BaseStrategy-only)

- Accepts BaseStrategy instances (must implement on_tick, start, stop, on_order_update optionally).
- ThreadPoolExecutor for concurrent strategy execution.
- Queue-based tick ingestion with bounded size.
- Per-strategy min_interval throttle (seconds).
- Lifecycle: start() -> starts worker + calls strategy.start(...)
             stop()  -> stops worker + calls strategy.stop(...)
- Order update routing helper.
"""

from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import threading
import time
import traceback
import logging
from typing import Dict, Optional

from src.core.strategy.base import BaseStrategy
from src.core.portfolio.manager import PortfolioManager


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class StrategyObjectWrapper:
    """Wrapper for a BaseStrategy instance providing throttling and lifecycle helpers."""

    def __init__(self, strategy: BaseStrategy, min_interval: float = 0.0):
        self.instance = strategy
        self.name = strategy.meta.name
        self.min_interval = float(min_interval)
        self._last_run = 0.0
        self._lock = threading.Lock()
        
    def can_run(self) -> bool:
        return (time.time() - self._last_run) >= self.min_interval

    def mark_run(self):
        with self._lock:
            self._last_run = time.time()

    def on_start(self, api, order_manager):
        try:
            self.instance.start(api, order_manager)
            logger.debug("Started strategy %s", self.name)
        except Exception:
            logger.exception("Error while starting strategy %s", self.name)

    def on_stop(self, api, order_manager):
        try:
            self.instance.stop(api, order_manager)
            logger.debug("Stopped strategy %s", self.name)
        except Exception:
            logger.exception("Error while stopping strategy %s", self.name)

    def execute_tick(self, api, tick, order_manager):
        try:
            # strategy receives its own context via instance.ctx
            self.instance.on_tick(api, order_manager, tick, self.instance.ctx)
        except Exception:
            logger.exception("Error during on_tick for strategy %s", self.name)


class StrategyEngine:
    """A lightweight engine that dispatches ticks to BaseStrategy instances only."""

    def __init__(self, api, order_manager, max_workers: int = 8, queue_size: int = 10000):
        self.api = api
        self.order_manager = order_manager

        self._strategies: Dict[str, StrategyObjectWrapper] = {}
        self._queue: Queue = Queue(maxsize=queue_size)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        self.portfolio: Optional[PortfolioManager] = None


    # ------------------ registration ------------------
    def register(self, strategy_obj: BaseStrategy, min_interval: float = 0.0):
        name = strategy_obj.meta.name
        if name in self._strategies:
            raise ValueError(f"Strategy '{name}' already registered")

        wrapper = StrategyObjectWrapper(strategy_obj, min_interval=min_interval)
        self._strategies[name] = wrapper
        logger.info("Registered strategy %s (min_interval=%s)", name, min_interval)

        # ---------------- NEW: auto-apply risk policy ----------------
        try:
            # prefer using OrderManager helper if available so we don't rely on RiskEngine internals
            if hasattr(self, "order_manager") and hasattr(self.order_manager, "set_risk_policy"):
                if getattr(strategy_obj, "risk", None) is not None:
                    self.order_manager.set_risk_policy(strategy_obj.meta.name, strategy_obj.risk)
                    logger.info("Applied risk policy for strategy %s", strategy_obj.meta.name)
            else:
                # fallback: call risk_engine.set_policy directly if available
                if getattr(strategy_obj, "risk", None) is not None and getattr(self, "order_manager", None):
                    re = getattr(self.order_manager, "risk_engine", None)
                    if re and hasattr(re, "set_policy"):
                        re.set_policy(strategy_obj.meta.name, strategy_obj.risk)
                        logger.info("Applied risk policy for strategy %s (via risk_engine.set_policy)", strategy_obj.meta.name)
        except Exception:
            logger.exception("Failed to apply risk policy for %s", strategy_obj.meta.name)

        # -------------------------------------------------------------

        if self._running:
            wrapper.on_start(self.api, self.order_manager)


    def unregister(self, name: str):
        """
        Unregister a strategy by name. Will call stop() on the instance if engine is running.
        """
        wrapper = self._strategies.pop(name, None)
        if wrapper:
            if self._running:
                try:
                    wrapper.on_stop(self.api, self.order_manager)
                except Exception:
                    logger.exception("Error stopping strategy %s during unregister", name)
            logger.info("Unregistered strategy %s", name)

    def list_strategies(self):
        return list(self._strategies.keys())

    # ------------------ lifecycle ------------------
    def start(self):
        """
        Start the engine worker and call start() on all registered strategies.
        Safe to call multiple times.
        """
        if self._worker_thread and self._worker_thread.is_alive():
            return

        logger.info("StrategyEngine starting: starting %d strategies", len(self._strategies))
        self._stop_event.clear()

        # Mark running before starting strategy hooks so registration can check _running
        self._running = True

        # Call start on strategies
        for wrapper in list(self._strategies.values()):
            wrapper.on_start(self.api, self.order_manager)

        # Start worker loop
        self._worker_thread = threading.Thread(target=self._run_loop, daemon=True, name="StrategyEngineWorker")
        self._worker_thread.start()
        logger.info("StrategyEngine worker started")

    def stop(self, wait: bool = True):
        """
        Stop the engine: stop accepting ticks, call stop() on strategies, and shutdown executor.
        """
        logger.info("StrategyEngine stopping")
        self._stop_event.set()
        self._running = False

        # Notify strategies
        for wrapper in list(self._strategies.values()):
            try:
                wrapper.on_stop(self.api, self.order_manager)
            except Exception:
                logger.exception("Error stopping strategy %s", wrapper.name)

        # Wait for worker thread to finish
        if wait and self._worker_thread:
            self._worker_thread.join(timeout=5.0)

        # Shutdown executor (will wait for running tasks unless wait is False)
        try:
            self._executor.shutdown(wait=wait)
        except Exception:
            logger.exception("Error shutting down executor")

        logger.info("StrategyEngine stopped")

    # ------------------ input ------------------
    def on_tick(self, tick: dict):
        """
        Enqueue a tick for processing. If full, drop the tick and log once.
        """
        logger.debug(f"[ENGINE DEBUG] StrategyEngine.on_tick ENTERED: {tick}")


        
        if self._stop_event.is_set():
            return

        try:
            self._queue.put_nowait(tick)
        except Exception:
            logger.warning("StrategyEngine queue full; dropping tick")

    # ------------------ worker loop ------------------
    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                tick = self._queue.get(timeout=0.5)
            except Empty:
                continue

            logger.debug(f"[ENGINE WORKER] dequeued tick: {tick}")
            logger.debug(f"[ENGINE DEBUG] StrategyEngine.on_tick ENTERED: {tick}")



            # Dispatch to all registered strategies
            for name, wrapper in list(self._strategies.items()):
                try:
                    if not wrapper.can_run():
                        continue
                    # mark run immediately to enforce min_interval even while running
                    wrapper.mark_run()
                    # submit execution
                    self._executor.submit(wrapper.execute_tick, self.api, tick, self.order_manager)
                except Exception:
                    logger.exception("Failed to dispatch tick to strategy %s", name)

            self._queue.task_done()

    # ------------------ order update routing ------------------
    def on_order_update(self, order: dict):
        """
        Unified order update routing:
        - DO NOT call strategy.on_order_update here (prevents double callbacks)
        - Forward the update into PortfolioManager only
        - PortfolioManager will correctly route to the appropriate strategy once
        """

        # --- Route ONLY to portfolio ---
        if self.portfolio:
            try:
                self.portfolio.on_order_update(order)
            except Exception:
                logger.exception("Portfolio update failed")
        else:
            logger.warning("Received order update but no portfolio is attached")


