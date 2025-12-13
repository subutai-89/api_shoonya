import time
import threading
import inspect
import json
import asyncio
import websockets
from typing import Callable, Any, List, Optional
from termcolor import colored

from src.brokers.base_client import BaseBrokerClient


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
        price_heartbeat_timeout: int = 5 * 60,
        order_heartbeat_timeout: int = 60,

        verbose: bool = True,               # verbose -> print raw JSON and lifecycle messages        
        print_ticks: bool = True,           # print_ticks -> print normalized tick lines (t,e,tk,lp)
    ):
        
        self.broker = broker                # Public callbacks / broker
        self._strategy_on_tick = on_tick    # user-provided strategy callback (forward normalized ticks here)        
        self.on_open_user = on_open         # preserve original on_open/on_error/on_close user callbacks
        self.on_error_user = on_error
        self.on_close_user = on_close

        self.market_state = {}              # Hold first tick (tk) & then update subsequent deltas (tf)

        # Settings / heartbeat
        self.last_tick_time = time.time()   # Initialize last_tick_time to "now" so we don't immediately report an enormous gap
        self.price_heartbeat_timeout = price_heartbeat_timeout  # seconds

        self.last_message_time = time.time() # Track the time of the last any-message received (orders/tf etc.)
        self.order_heartbeat_timeout = order_heartbeat_timeout  # seconds

        self.verbose = verbose
        self.print_ticks = print_ticks

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

        if self.print_ticks:
            self._print_tick = self._print_tick
        else:
            self._print_tick = self._do_nothing 


    # def _print_tick(self, tick_data: dict):
    #     """Print live ticks when the print_ticks flag is set.
    #     (kept for compatibility; replaced by lambda in __init__ but retained as fallback)
    #     """
    #     print("Live Tick:", tick_data)

    def _print_tick(self, tick_data: dict):
        """Print live ticks when the print_ticks flag is set.
        Now includes instrument name dynamically for each token.
        """
        token = tick_data.get('tk')
        instrument_name = self.market_state.get(token, {}).get('instrument_name', 'Unknown')
        print(f"{instrument_name} - Live Tick:", tick_data)

    def _do_nothing(self, tick_data: dict):
        """ No-op function for tick printing when print_ticks is False. """
        pass


    # -------------------------------------------------------------------
    # INTERNAL: forward raw messages unchanged
    # -------------------------------------------------------------------
    def _patched_on_data(self, raw_msg):
        # Respect stop event quickly
        if self._stop_event.is_set():
            return

        # Update last-message heartbeat timestamp (any message)
        self.last_message_time = time.time()

        # Verbose: show the raw incoming message (useful to debug wire-level issues)
        if self.verbose:
            print(f"[WS VERBOSE] Raw message received: {raw_msg}")

        try:
            # We only handle dict-style Shoonya ticks here; non-dict pass through
            if not isinstance(raw_msg, dict):
                return

            t_type = raw_msg.get("t")

            # -------------------------------------------------------------
            # PRICE TICK ("tk") - full snapshot
            # -------------------------------------------------------------
            if t_type == "tk":
                tk = raw_msg.get("tk")
                lp_raw = raw_msg.get("lp")
                instrument_name = raw_msg.get('ts', 'Unknown Instrument')  # Instrument name (symbol)

                # --- lazy init market_state for first tick of token ---
                if tk not in self.market_state:
                    self.market_state[tk] = {
                        "instrument_name": instrument_name
                    }

                if tk is None:
                    if self.verbose:
                        print("[WS VERBOSE] tk tick missing 'tk' field, skipping")
                    return

                # lp might be string or numeric; validate and convert
                lp_val = None
                if lp_raw is not None:
                    try:
                        lp_val = float(lp_raw)
                    except Exception:
                        # if conversion fails, keep lp_val as None and we'll log and skip forwarding numeric ops
                        if self.verbose:
                            print(f"[WS VERBOSE] failed to parse lp on tk: {lp_raw}")

                # Overwrite the full market snapshot for this token
                existing_name = self.market_state.get(tk, {}).get("instrument_name")

                if existing_name and existing_name != instrument_name:
                    print(colored(
                        f"⚠️ Instrument mismatch for token {tk}: "
                        f"{existing_name} → {instrument_name}",
                        color="yellow"
                    ))

                # Ensure market_state stores lp as the canonical value (string preserved in raw)
                if lp_val is not None:
                    self.market_state[tk]['lp'] = raw_msg.get('lp')

                # Normalized payload forwarded to strategy
                normalized = {
                    "t": "tk",
                    "e": raw_msg.get("e"),
                    "tk": tk,
                    "lp": lp_val,
                    "raw": raw_msg
                }

                # Update last price tick heartbeat time (now we've received a tk)
                self.last_tick_time = time.time()

                # Print normalized line if requested (print_ticks)
                if self.print_ticks:
                    # Get instrument name from market_state (fallback to 'Unknown Instrument' if not found)
                    instrument_name = self.market_state.get(tk, {}).get('instrument_name', 'Unknown Instrument')
                    lp_print = raw_msg.get('lp')
                    print(colored(f"[LIVE TICK: {instrument_name}] t: {raw_msg.get('t')}, e: {raw_msg.get('e')}, tk: {tk}, lp: {lp_print}",color='green'))

                # Forward to strategy engine
                if self._strategy_on_tick:
                    try:
                        self._strategy_on_tick(normalized)
                        self._tick_forward_count += 1
                    except Exception as e:
                        print("⚠️ strategy callback raised on tk:", e)

                return

            # -------------------------------------------------------------
            # INCREMENTAL UPDATE TICK ("tf") - merge into existing state
            # -------------------------------------------------------------
            elif t_type == "tf":
                tk = raw_msg.get("tk")
                if tk is None:
                    if self.verbose:
                        print("[WS VERBOSE] tf tick missing 'tk' field, skipping")
                    return

                if tk not in self.market_state:
                    # no prior snapshot, warn in verbose mode
                    if self.verbose:
                        print(f"[WS VERBOSE] Warning: Token {tk} not found in market_state for 'tf' update. Ignoring tf until tk received.")
                    return

                # Carry-forward semantics: if lp is missing or None, reuse previous lp
                lp_raw = raw_msg.get("lp")
                if lp_raw is None:
                    # if previous state has an lp, attach it to this delta for downstream consumers
                    prev_lp = self.market_state[tk].get("lp")
                    if prev_lp is not None:
                        # do not mutate caller's raw_msg if it's shared; create a merged view
                        raw_msg = dict(raw_msg)
                        raw_msg['lp'] = prev_lp
                    else:
                        # No previous LP available — log and skip numeric consumers that expect a price
                        if self.verbose:
                            print(f"[WS VERBOSE] tf for {tk} has no 'lp' and no previous lp saved; forwarding tf without lp")
                        # we proceed; normalized.l p will be None

                # Merge changed fields into stored snapshot (shallow update)
                self.market_state[tk].update(raw_msg)

                # Create normalized version for strategy: convert lp to float if possible
                lp_val = None
                lp_for_norm = self.market_state[tk].get("lp")
                if lp_for_norm is not None:
                    try:
                        lp_val = float(lp_for_norm)
                    except Exception:
                        if self.verbose:
                            print(f"[WS VERBOSE] failed to parse lp for normalized tf: {lp_for_norm}")

                normalized = {
                    "t": "tf",
                    "e": raw_msg.get("e"),
                    "tk": tk,
                    "lp": lp_val,
                    "raw": raw_msg
                }

                # Verbose: show merged delta if requested
                if self.verbose:
                    print(f"[WS VERBOSE] Market Depth Update merged into state for {tk}: {raw_msg}")

                # Print normalized line if requested
                if self.print_ticks:
                    # Get instrument name from market_state (fallback to 'Unknown Instrument' if not found)
                    instrument_name = self.market_state.get(tk, {}).get('instrument_name', 'Unknown Instrument')
                    lp_print = self.market_state[tk].get('lp')
                    print(colored(
                        f"[LIVE TICK: {instrument_name}] t: {raw_msg.get('t')}, e: {raw_msg.get('e')}, tk: {tk}, lp: {lp_print}",
                        color="green"
                    ))


                # Update last_tick_time only if this delta actually carries a price update
                if lp_for_norm is not None:
                    self.last_tick_time = time.time()

                # Forward to strategy engine
                if self._strategy_on_tick:
                    try:
                        self._strategy_on_tick(normalized)
                        self._tick_forward_count += 1
                    except Exception as e:
                        print("⚠️ strategy callback raised on tf:", e)

                return

            # -------------------------------------------------------------
            # UNKNOWN / other message types
            # -------------------------------------------------------------
            else:
                if self.verbose:
                    print(f"[WS VERBOSE] Unhandled message type: {t_type} (message forwarded unchanged).")
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

        # mark last tick time to now so heartbeat doesn't immediately fire
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
    # WEBSOCKET HEARTBEAT MONITOR
    # -------------------------------------------------------------------
    def _heartbeat_monitor(self):

        if self.verbose:
            print("[WS VERBOSE] heartbeat monitor started")

        while not self._stop_event.is_set():
            try:
                # Check price tick heartbeat
                time_since_last_tick = time.time() - self.last_tick_time
                if time_since_last_tick > self.price_heartbeat_timeout:
                    print(f"⚠️ No price ticks received for {time_since_last_tick:.2f} seconds (Threshold: {self.price_heartbeat_timeout} seconds).")
                    # (Optional) you can attempt reconnect here or call an alert hook

                # Check order book update heartbeat (any message)
                time_since_last_message = time.time() - self.last_message_time
                if time_since_last_message > self.order_heartbeat_timeout:
                    print(f"⚠️ No order book updates (any messages) received for {time_since_last_message:.2f} seconds (Threshold: {self.order_heartbeat_timeout} seconds).")
                    # (Optional) you can attempt reconnect here or call an alert hook

                time.sleep(1)  # Check frequency
            except Exception as e:
                # Protect heartbeat thread from crashing
                if self.verbose:
                    print("[WS VERBOSE] heartbeat monitor exception:", e)
                time.sleep(1)

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

            # keep behavior backwards compatible: if print_ticks requested, route printed ticks to _print_tick
            if self.print_ticks:
                # preserve existing attribute usage in other parts of code (no signature changes)
                self.on_tick = self._print_tick

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
            print(f"[WS VERBOSE] WebSocketManager started (LIVE). Price heartbeat timeout: {self.price_heartbeat_timeout}s, Order heartbeat timeout: {self.order_heartbeat_timeout}s")

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
