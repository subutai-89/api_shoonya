from typing import Any, List, Tuple, Optional
from .base_client import BaseBrokerClient

# We continue to use the existing api_client functions for HTTP login/keepalive/get_token.
# These functions are thin wrappers around the real Shoonya HTTP endpoints in your codebase.
from src.brokers.shoonya_rest_api import (
    login_shoonya,
    logout_shoonya,
    start_keepalive,
    get_token as api_get_token,
)


class ShoonyaClient(BaseBrokerClient):
    """
    Cleaner ShoonyaClient that:
    - stores a mock flag (mock param kept for backwards compatibility)
    - returns the API object from login()
    - delegates websocket start/stop to the underlying API object (if present)
    """

    def __init__(self, mock: bool = False):
        self._mock = bool(mock)
        self._api = None
        self._login_response = {}

    @property
    def mock_mode(self) -> bool:
        return self._mock

    # ----------------------------
    def login(self) -> Tuple[Optional[Any], dict]:
        api, resp = login_shoonya(mock_mode=self._mock)
        resp = resp or {}
        self._api = api
        self._login_response = resp
        return api, resp

    def logout(self) -> Any:
        if not self._api:
            return {"stat": "Not Logged Out", "emsg": "No API session"}
        return logout_shoonya(self._api)

    # ----------------------------
    def start_keepalive(self, api: Any, interval: int = 10) -> None:
        return start_keepalive(api, interval=interval)

    # ----------------------------
    def start_websocket(
        self,
        api: Any,
        tokens: List[str],
        subscribe_callback=None,
        socket_open_callback=None,
        socket_error_callback=None,
        socket_close_callback=None,
        **kwargs
    ) -> None:
        """
        Start websocket by calling the underlying api.start_websocket if available.
        We wrap the open callback to auto-subscribe tokens where needed.
        """

        if api is None:
            api = self._api

        # Build a wrapped open callback to handle token subscription afterward
        def _wrapped_open():
            if socket_open_callback:
                try:
                    socket_open_callback()
                except Exception:
                    pass

            # subscribe if available
            if tokens and hasattr(api, "subscribe"):
                try:
                    api.subscribe(tokens)
                except Exception:
                    # some APIs expect single token or other signature; best-effort
                    try:
                        for t in tokens:
                            api.subscribe(t)
                    except Exception:
                        pass

        callback_args = {
            "subscribe_callback": subscribe_callback,
            "socket_open_callback": _wrapped_open,
            "socket_error_callback": socket_error_callback,
            "socket_close_callback": socket_close_callback,
        }
        callback_args = {k: v for k, v in callback_args.items() if v is not None}

        # Delegate to the API's start_websocket (various shoonyas use different signatures)
        if hasattr(api, "start_websocket"):
            try:
                api.start_websocket(**callback_args)
            except TypeError:
                # fallback to positional style (some old api implementations)
                try:
                    api.start_websocket(self._api, tokens, **callback_args)
                except Exception:
                    # as last resort, raise to help debugging
                    raise
        else:
            raise RuntimeError("Underlying API does not expose start_websocket()")

    # ----------------------------
    def stop_websocket(self, api=None):
        """Try to close websocket via the API object; fallback to stored self._api."""
        if api is None:
            api = getattr(self, "_api", None)

        if api is None:
            return

        try:
            if hasattr(api, "close_websocket"):
                api.close_websocket()
                return
        except Exception:
            pass

        ws_obj = getattr(api, "ws", None)
        if ws_obj and hasattr(ws_obj, "close"):
            try:
                ws_obj.close()
                return
            except Exception:
                pass

    # ----------------------------
    def get_token(self, api: Any, exchange: str, tradingsymbols: List[str]) -> List[str]:
        return api_get_token(api, exchange, tradingsymbols)
