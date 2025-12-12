import time
import threading
import inspect
import json
import asyncio
from typing import Callable, Any, List, Optional

from src.brokers.base_client import BaseBrokerClient

# Only imported/used for mock mode async client
import websockets


class WebSocketManager:
    """
    WebSocketManager (verbose debug edition)
    - Preserves exact Shoonya tick contract (forwards raw JSON unchanged)
    - Mock mode uses an async websocket client running in its own event loop/thread
    - Live mode uses the broker.start_websocket path unchanged
    - Verbose logging enabled by default to help trace flow
    """

    def __init__(
        self,
        broker: BaseBrokerClient,
        on_tick: Callable[[dict], None],
        on_open: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        heartbeat_timeout: int = 5,
        verbose: bool = False,
    ):
        # Public callbacks / broker
        self.broker = broker
        self.on_tick = on_tick
        self.on_open_user = on_open
        self.on_error_user = on_error
        self.on_close_user = on_close

        # Settings
        self.last_tick_time = 0.0
        self.heartbeat_timeout = heartbeat_timeout
        self.verbose = verbose

        # Runtime state
        self.api = None
        self.tokens: List[str] = []
        self.running = False

        self._stop_event = threading.Event()
        self._reader_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None

        # Counters for debug
        self._recv_count = 0
        self._dispatch_count = 0
        self._tick_forward_count = 0

        if self.verbose:
            print(f"[WS VERBOSE] WebSocketManager created (mock_mode={getattr(self.broker,'mock_mode',False)})")

    # -------------------------------------------------------------------
    # INTERNAL: forward raw messages unchanged
    # -------------------------------------------------------------------
    def _patched_on_data(self, raw_msg):
        if self._stop_event.is_set():
            return

        try:
            if isinstance(raw_msg, dict) and raw_msg.get("t") == "tk":
                tk = raw_msg.get("tk")
                lp_raw = raw_msg.get("lp")

                # ignore malformed ticks
                if tk is None or lp_raw is None:
                    return

                try:
                    lp = float(lp_raw)
                except Exception:
                    return

                normalized = {
                    "symbol": tk,
                    "lp": lp,
                    "raw": raw_msg
                }

                self.on_tick(normalized)
                return

            # Non-tick messages → ignore or forward?
            # Forwarding breaks strategy logic, so ignore
            return

        except Exception as e:
            print("⚠️ _patched_on_data error:", e)


    # -------------------------------------------------------------------
    # INTERNAL: open / error / close patched callbacks
    # -------------------------------------------------------------------
    def _patched_on_open(self):
        if self._stop_event.is_set():
            if self.verbose:
                print("[WS VERBOSE] _patched_on_open called AFTER stop event; returning")
            return

        self.last_tick_time = time.time()
        if self.verbose:
            print("[WS VERBOSE] _patched_on_open() called")

        if self.on_open_user:
            try:
                self.on_open_user()
            except Exception as e:
                print("⚠️ on_open handler raised:", e)

        # Best-effort subscribe for live APIs
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

    def _patched_on_error(self, error_msg: str):
        if self._stop_event.is_set():
            return
        if self.verbose:
            print("[WS VERBOSE] _patched_on_error():", error_msg)
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
        if self.verbose:
            print("[WS VERBOSE] _patched_on_close()")
        if self.on_close_user:
            try:
                self.on_close_user()
            except Exception as e:
                print("⚠️ on_close handler raised:", e)

    # -------------------------------------------------------------------
    # HEARTBEAT
    # -------------------------------------------------------------------
    def _heartbeat_monitor(self):
        if self.verbose:
            print("[WS VERBOSE] heartbeat monitor started")
        while not self._stop_event.is_set():
            if self.last_tick_time > 0:
                dt = time.time() - self.last_tick_time
                if dt > self.heartbeat_timeout:
                    print(f"⚠️ WebSocket heartbeat timeout! No ticks for {dt:.1f} seconds.")
            time.sleep(1)
        if self.verbose:
            print("[WS VERBOSE] heartbeat monitor exiting")

    # -------------------------------------------------------------------
    # MOCK MODE: async reader loop
    # -------------------------------------------------------------------
    async def _mock_ws_loop(self, uri: str = "ws://localhost:9000"):
        """Connect to mock server and forward raw Shoonya-style messages unchanged."""
        if self.verbose:
            print("[WS VERBOSE] _mock_ws_loop starting, uri=", uri)

        try:
            async with websockets.connect(uri) as ws:
                if self.verbose:
                    print("[WS VERBOSE] mock ws connected, sending subscription (if tokens present)")

                # Send subscription message as mock_server expects
                if self.tokens:
                    sub_msg = {"t": "t", "k": "#".join(self.tokens)}
                    try:
                        await ws.send(json.dumps(sub_msg))
                        if self.verbose:
                            print("[WS VERBOSE] sent subscription:", sub_msg)
                    except Exception as e:
                        print("[WS VERBOSE] failed to send subscription:", e)

                # Main receive loop
                while not self._stop_event.is_set():
                    try:
                        raw = await ws.recv()
                    except (asyncio.CancelledError, websockets.ConnectionClosed):
                        if self.verbose:
                            print("[WS VERBOSE] Mock ws recv cancelled/closed")
                        break
                    except Exception as e:
                        print("[WS VERBOSE] recv() exception:", e)
                        break

                    self._recv_count += 1
                    if self.verbose:
                        print(f"[WS VERBOSE] raw recv #{self._recv_count}: {str(raw)[:240]}")

                    # Attempt to parse JSON into a dict (mock_server sends JSON)
                    try:
                        msg = json.loads(raw)
                        if self.verbose:
                            print(f"[WS VERBOSE] parsed JSON #{self._recv_count}")
                    except Exception:
                        msg = raw
                        if self.verbose:
                            print(f"[WS VERBOSE] non-JSON message #{self._recv_count}")

                    # Dispatch to patched_on_data (which forwards unchanged)
                    if self.verbose:
                        print(f"[WS VERBOSE] dispatching recv #{self._recv_count} to _patched_on_data()")
                    try:
                        self._patched_on_data(msg)
                    except Exception as e:
                        print("[WS VERBOSE] error dispatching to _patched_on_data:", e)

                if self.verbose:
                    print("[WS VERBOSE] exiting mock recv loop")

        except Exception as e:
            print("❌ MOCK WS FATAL ERROR:", e)
        finally:
            if self.verbose:
                print("[WS VERBOSE] _mock_ws_loop cleanup complete")

    def _start_mock_async_ws(self):
        """Start the async mock websocket loop inside a dedicated thread with its own event loop."""
        if self.verbose:
            print("[WS VERBOSE] spawning mock reader thread")

        def runner():
            if self.verbose:
                print("[WS VERBOSE] runner thread starting, creating event loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                if self.verbose:
                    print("[WS VERBOSE] runner: running _mock_ws_loop() until complete")
                loop.run_until_complete(self._mock_ws_loop())
            except Exception as e:
                print("[WS VERBOSE] runner exception:", e)
            finally:
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                loop.close()
                if self.verbose:
                    print("[WS VERBOSE] runner: event loop closed")

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        self._reader_thread = t
        if self.verbose:
            print(f"[WS VERBOSE] mock reader thread started (ident={t.ident})")

    # -------------------------------------------------------------------
    # PUBLIC: start
    # -------------------------------------------------------------------
    def start(self, api: Any, tokens: List[str]):
        """
        Start the WebSocket manager.
        Mock mode uses the async client; live uses broker.start_websocket exactly as before.
        """
        self.api = api
        self.tokens = tokens or []
        self.running = True
        self._stop_event.clear()

        if self.verbose:
            print("[WS VERBOSE] start() called; mock_mode=", getattr(self.broker, "mock_mode", False))

        # Start heartbeat monitor
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
        self._heartbeat_thread.start()

        # MOCK mode path
        if getattr(self.broker, "mock_mode", False):
            if self.verbose:
                print("[WS VERBOSE] Using async mock websocket path")
            self._start_mock_async_ws()
            if self.verbose:
                print("🔌 WebSocketManager started (MOCK ASYNC).")
            return

        # LIVE mode path (unchanged)
        callback_kwargs = {
            "subscribe_callback": self._patched_on_data,
            "socket_open_callback": self._patched_on_open,
            "socket_error_callback": self._patched_on_error,
            "socket_close_callback": self._patched_on_close,
        }

        used_fallback = False
        start_ws = getattr(self.broker, "start_websocket", None)

        if self.verbose:
            print("[WS VERBOSE] LIVE mode: attempting to call broker.start_websocket() (introspection)")

        if start_ws:
            try:
                sig = inspect.signature(start_ws)
                params = sig.parameters

                accepts_callbacks = (
                    any(name in params for name in callback_kwargs)
                    or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
                )

                if accepts_callbacks:
                    try:
                        start_ws(self.api, self.tokens, **callback_kwargs)
                        if self.verbose:
                            print("[WS VERBOSE] start_websocket called with callbacks")
                    except TypeError:
                        start_ws(self.api, **callback_kwargs)
                        if self.verbose:
                            print("[WS VERBOSE] start_websocket called with alternate signature")
                else:
                    used_fallback = True
                    start_ws(self.api, self.tokens)
                    if self.verbose:
                        print("[WS VERBOSE] start_websocket called fallback style (api,tokens)")

            except Exception as e:
                print("⚠️ Broker start_websocket introspection failed:", e)
                used_fallback = True
        else:
            used_fallback = True

        if used_fallback:
            try:
                self.broker.start_websocket(self.api, self.tokens)
                if self.verbose:
                    print("[WS VERBOSE] used_fallback: broker.start_websocket(api,tokens)")
            except Exception as e:
                print("❌ Live websocket start failed:", e)

        if self.verbose:
            print(f"[WS VERBOSE] WebSocketManager started (LIVE). Heartbeat timeout: {self.heartbeat_timeout}")

    # -------------------------------------------------------------------
    # PUBLIC: stop
    # -------------------------------------------------------------------
    def stop(self):
        if self.verbose:
            print("[WS VERBOSE] stop() called: initiating graceful shutdown")

        self._stop_event.set()
        self.running = False

        # Join heartbeat thread
        if self._heartbeat_thread:
            try:
                self._heartbeat_thread.join(timeout=1.0)
            except Exception:
                pass

        # Join reader thread
        if self._reader_thread:
            try:
                if self.verbose:
                    print("[WS VERBOSE] joining reader thread (ident=%s)" % getattr(self._reader_thread, "ident", None))
                self._reader_thread.join(timeout=1.0)
            except Exception:
                pass

        # Live broker stop if available
        try:
            stop_ws = getattr(self.broker, "stop_websocket", None)
            if stop_ws:
                sig = inspect.signature(stop_ws)
                params = list(sig.parameters.values())
                if len(params) == 2:
                    stop_ws(self.api)
                else:
                    stop_ws()
        except Exception:
            pass

        if self.verbose:
            print("[WS VERBOSE] shutdown complete")
        print("🟢 WebSocketManager shutdown complete.")
