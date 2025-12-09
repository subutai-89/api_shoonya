from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Optional


class BaseBrokerClient(ABC):
    """
    Minimal broker interface used by the App, WebSocketManager and OrderManager.
    Broker implementations must expose a consistent interface so the rest of the
    system remains broker-agnostic.
    """

    # ----------------------------
    # Session
    # ----------------------------
    @abstractmethod
    def login(self) -> Tuple[Optional[Any], dict]:
        """Perform login and return (api_object, login_response)."""
        raise NotImplementedError

    @abstractmethod
    def logout(self) -> Any:
        """Logout / cleanup. Return whatever underlying logout returns (or a dict)."""
        raise NotImplementedError

    # ----------------------------
    # Feed Management
    # ----------------------------
    @abstractmethod
    def start_keepalive(self, api: Any, interval: int = 10) -> None:
        """Start background keepalive (non-blocking)."""
        raise NotImplementedError

    @abstractmethod
    def start_websocket(
        self,
        api: Any,
        tokens: List[str],
        **kwargs
    ) -> None:
        """
        Start websocket feed. Implementations MAY accept callback overrides via kwargs.
        Must return quickly (non-blocking).
        """
        raise NotImplementedError

    @abstractmethod
    def stop_websocket(self, api: Any = None) -> None:
        """
        Cleanly stop the websocket feed.
        'api' is optional for maximum compatibility with broker implementations.
        """
        raise NotImplementedError

    @abstractmethod
    def get_token(self, api: Any, exchange: str, tradingsymbols: List[str]) -> List[str]:
        """Resolve tradingsymbol(s) -> token(s) used for websocket subscribe."""
        raise NotImplementedError

    # ----------------------------
    # Mode
    # ----------------------------
    @property
    @abstractmethod
    def mock_mode(self) -> bool:
        """Whether this client is operating in mock/simulated mode."""
        raise NotImplementedError
