import time
import threading
import inspect
from typing import Callable, Any, List, Optional
from src.brokers.base_client import BaseBrokerClient


class WebSocketManager:
    """
    Broker-agnostic WebSocket manager.
    - Accepts a broker (implements BaseClient)
    - Provides unified callbacks (on_tick/on_open/on_error/on_close)
    - Heartbeat monitoring
    - Robust start/stop that works with older Shoonya wrappers
      (which may or may not accept callback args)
    """

    def __init__(
        self,
        broker: BaseBrokerClient,
        on_tick: Callable[[dict], None],
        on_open: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        heartbeat_timeout: int = 5,
    ):
        self.broker = broker
        self.on_tick = on_tick
        self.on_open_user = on_open
        self.on_error_user = on_error
        self.on_close_user = on_close

        self.last_tick_time = 0
        self.heartbeat_timeout = heartbeat_timeout

        self.api = None
        self.tokens: List[str] = []
        self.running = False

        self.heartbeat_thread: Optional[threading.Thread] = None

        # NEW graceful-shutdown controls
        self._stop_event = threading.Event()
        self._reader_thread = None   # Some brokers expose reader threads; safe placeholder
        self._heartbeat_thread = None

    # -------------------------------------------------------
    # internal patched callbacks
    # -------------------------------------------------------
    def _patched_on_data(self, raw_msg):
        """Normalize/route incoming raw messages to the user on_tick handler."""
        if self._stop_event.is_set():
            return  # Prevent callbacks after shutdown

        self.last_tick_time = time.time()
        try:
            self.on_tick(raw_msg)
        except Exception as e:
            print("⚠️ on_tick handler raised:", e)

    def _patched_on_open(self):
        if self._stop_event.is_set():
            return

        self.last_tick_time = time.time()

        if self.on_open_user:
            try:
                self.on_open_user()
            except Exception as e:
                print("⚠️ on_open handler raised:", e)

        # Attempt subscription if underlying API supports it
        try:
            if self.api and hasattr(self.api, "subscribe") and self.tokens:
                try:
                    self.api.subscribe(self.tokens)
                except TypeError:
                    for t in self.tokens:
                        try:
                            self.api.subscribe(t)
                        except Exception:
                            pass
        except Exception:
            pass

    def _patched_on_error(self, error_msg):
        if self._stop_event.is_set():
            return

        if self.on_error_user:
            try:
                self.on_error_user(error_msg)
            except Exception as e:
                print("⚠️ on_error handler raised:", e)
        else:
            print("⚠️ WebSocket error:", error_msg)

    def _patched_on_close(self):
        if self._stop_event.is_set():
            return

        if self.on_close_user:
            try:
                self.on_close_user()
            except Exception as e:
                print("⚠️ on_close handler raised:", e)

    # -------------------------------------------------------
    # HEARTBEAT MONITORING
    # -------------------------------------------------------
    def _heartbeat_monitor(self):
        while not self._stop_event.is_set():
            if self.last_tick_time != 0:
                if time.time() - self.last_tick_time > self.heartbeat_timeout:
                    print(
                        "⚠️ WebSocket heartbeat timeout! No ticks for",
                        time.time() - self.last_tick_time,
                        "seconds.",
                    )
            time.sleep(1)

    # -------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------
    def start(self, api: Any, tokens: List[str]):
        """
        Start the websocket using the broker.
        Handles both modern callback-based APIs and legacy Shoonya start_websocket().
        """
        self.api = api
        self.tokens = tokens or []
        self.running = True
        self._stop_event.clear()

        callback_kwargs = {
            "subscribe_callback": self._patched_on_data,
            "socket_open_callback": self._patched_on_open,
            "socket_error_callback": self._patched_on_error,
            "socket_close_callback": self._patched_on_close,
        }

        start_ws = getattr(self.broker, "start_websocket", None)
        used_fallback = False

        if start_ws:
            try:
                sig = inspect.signature(start_ws)
                params = sig.parameters

                accepts_callbacks = any(
                    name in params for name in callback_kwargs.keys()
                ) or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in params.values()
                )

                if accepts_callbacks:
                    try:
                        start_ws(self.api, self.tokens, **callback_kwargs)
                    except TypeError:
                        start_ws(self.api, **callback_kwargs)
                else:
                    used_fallback = True
                    start_ws(self.api, self.tokens)
            except Exception as e:
                print("⚠️ Broker start_websocket introspection failed:", e)
                used_fallback = True
        else:
            used_fallback = True

        if used_fallback:
            try:
                self.broker.start_websocket(self.api, self.tokens)
            except Exception as e:
                print("❌ Failed to start websocket via broker:", e)
                try:
                    if hasattr(self.api, "start_websocket"):
                        try:
                            self.api.start_websocket(**callback_kwargs)
                        except TypeError:
                            self.api.start_websocket(
                                self._patched_on_data,
                                self._patched_on_open,
                                self._patched_on_error,
                                self._patched_on_close,
                            )
                    else:
                        raise RuntimeError(
                            "No start_websocket method found on API or broker."
                        )
                except Exception as e2:
                    print("❌ Last-resort api.start_websocket failed:", e2)
                    self.running = False
                    return

        # Start heartbeat monitor
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_monitor, daemon=True
        )
        self._heartbeat_thread.start()

        print("🔌 WebSocketManager started. Heartbeat timeout:", self.heartbeat_timeout)

    # -------------------------------------------------------
    def stop(self):
        print("🛑 WebSocketManager: Graceful shutdown…")

        # 1. Stop callbacks & loops
        self._stop_event.set()
        self.running = False

        # 2. Stop heartbeat thread FIRST
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=1.0)

        # 3. Stop reader thread BEFORE closing websocket
        if self._reader_thread:
            try:
                self._reader_thread.join(timeout=1.0)
            except RuntimeError:
                pass  # thread was never started

        # 4. Now safely close the websocket connection
        try:
            # Determine whether stop_websocket requires API arg
            sig = inspect.signature(self.broker.stop_websocket)
            params = list(sig.parameters.values())

            if len(params) == 2:  # (self, api)
                self.broker.stop_websocket(self.api)
            else:
                self.broker.stop_websocket()
        except Exception:
            pass

        print("🟢 WebSocketManager shutdown complete.")
