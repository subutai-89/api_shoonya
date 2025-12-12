from typing import Any, List, Tuple, Optional
from .base_client import BaseBrokerClient
import websocket
import threading
import json
import time


class MockAPI:
    """
    Minimal API-like object used by MockClient.
    Holds websocket instance and exposes place_order for testing.
    """
    def __init__(self):
        self.ws = None

    def place_order(self, **order):
        """
        Simulate a broker order placement.
        """
        return {
            "stat": "Ok",
            "order_id": f"MOCK-{int(time.time() * 1000)}",
            "details": order,
        }


class MockClient(BaseBrokerClient):
    """
    Broker implementation for local development & testing.
    - Connects to mock_server.py for websocket ticks
    - Simulates login, logout, keepalive, token lookup, and order placement
    """

    def __init__(self, mock: bool = True):
        self._mock = True
        self._api = None
        self._keepalive_thread = None
        self._stop_keepalive = False

    @property
    def mock_mode(self) -> bool:
        return True

    # -------------------------------------------------------
    # LOGIN / LOGOUT
    # -------------------------------------------------------
    def login(self) -> Tuple[Optional[Any], dict]:
        """
        Creates a MockAPI instance and returns a mock login response.
        """
        self._api = MockAPI()
        return self._api, {"stat": "Ok", "mock": True}

    def logout(self) -> dict:
        """
        Mock logout always succeeds.
        """
        return {"stat": "Ok"}

    # -------------------------------------------------------
    # KEEPALIVE
    # -------------------------------------------------------
    def start_keepalive(self, api: Any, interval: int = 10) -> None:
        """
        Mock keepalive does nothing except sleep in a background thread.
        """

        def run():
            while not self._stop_keepalive:
                time.sleep(interval)

        self._stop_keepalive = False
        self._keepalive_thread = threading.Thread(target=run, daemon=True)
        self._keepalive_thread.start()

    # -------------------------------------------------------
    # TOKEN RESOLUTION
    # -------------------------------------------------------
    def get_token(self, api: Any, exchange: str, tradingsymbols: List[str]) -> List[str]:
        """
        Mock: produce deterministic numeric tokens, same structure as real Shoonya.
        """
        tokens = []
        api._mock_token_map = {}  # symbol → token
        api._mock_symbol_map = {} # token  → symbol

        for s in tradingsymbols:
            token = abs(hash(s)) % 100000  # stable 5-digit token
            token_str = f"{token}"
            tokens.append(f"{exchange}|{token_str}")

            api._mock_token_map[s] = token_str
            api._mock_symbol_map[token_str] = s

        return tokens



    # -------------------------------------------------------
    # WEBSOCKET HANDLING
    # -------------------------------------------------------
    def start_websocket(
        self,
        api: Any,
        tokens: List[str],
        subscribe_callback=None,
        socket_open_callback=None,
        socket_error_callback=None,
        socket_close_callback=None,
        **_,
    ):
        """
        Connect to ws://localhost:9000 and forward messages to provided callbacks.
        Mimics the WebSocket behavior of a real broker.
        """

        url = "ws://localhost:9000"

        def on_message(ws, message):
            try:
                msg = json.loads(message)
            except Exception:
                msg = message

            if subscribe_callback:
                try:
                    subscribe_callback(msg)
                except Exception:
                    pass

        def on_open(ws):
            if socket_open_callback:
                try:
                    socket_open_callback()
                except Exception:
                    pass

            # Send subscription request expected by mock_server.py
            k = "#".join(tokens)
            ws.send(json.dumps({"t": "t", "k": k}))

        def on_error(ws, error):
            if socket_error_callback:
                try:
                    socket_error_callback(str(error))
                except Exception:
                    pass

        def on_close(ws, *args):
            if socket_close_callback:
                try:
                    socket_close_callback()
                except Exception:
                    pass

        # Create WebSocketApp
        ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        api.ws = ws  # store in API obj

        # Run WebSocket in background thread
        t = threading.Thread(target=ws.run_forever, daemon=True)
        t.start()

    # -------------------------------------------------------
    # STOP WEBSOCKET
    # -------------------------------------------------------
    def stop_websocket(self, api=None):
        if api is None:
            api = self._api

        if api and api.ws:
            try:
                api.ws.close()
            except Exception:
                pass
