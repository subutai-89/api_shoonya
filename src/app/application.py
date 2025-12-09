import time
import subprocess
import sys
from typing import Optional
import os

from src.brokers.base_client import BaseBrokerClient
from src.engine.websocket_manager import WebSocketManager

from src.engine.order_manager import OrderManager
from src.engine.strategy_engine import StrategyEngine
from src.strategies.momentum_strategy import MomentumStrategy

from src.core.portfolio.manager import PortfolioManager


class App:

    def __init__(self, broker: BaseBrokerClient):
        self.broker = broker
        self.api = None
        self.tokens = []
        self.mock_process: Optional[subprocess.Popen] = None
        self.ws: Optional[WebSocketManager] = None
        self.strategy_engine: Optional[StrategyEngine] = None


    # -----------------------------------------------------------
    # MOCK SERVER START
    # -----------------------------------------------------------
    def _start_mock_server(self):
        if not self.broker.mock_mode:
            return

        print("🟡 Starting Mock Server subprocess...")

        env = os.environ.copy()
        env["MOCK_MODE"] = os.getenv("MOCK_MODE", "normal")

        self.mock_process = subprocess.Popen(
            [sys.executable, "src/mock/mock_server.py"],
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            # text=True,
            start_new_session=True,
            env=env
        )

        print("🟡 Mock Server PID:", self.mock_process.pid)
        time.sleep(1)


    # -----------------------------------------------------------
    # APPLICATION START
    # -----------------------------------------------------------
    def start(self):
        print("\n🚀 Starting Application...")


        # ---- MOCK SERVER ----
        self._start_mock_server()
        print(f"📡 Broker Mode: {'MOCK' if self.broker.mock_mode else 'LIVE'}")


        # ---- LOGIN ----
        api, login_resp = self.broker.login()
        self.api = api

        if not api:
            print("❌ Login failed — cannot continue.")
            return

        # Print a filtered login summary
        keys_of_interest = ["stat", "request_time", "uname", "actid"]
        login_summary = {k: login_resp.get(k) for k in keys_of_interest if k in login_resp}
        print(f"🔑 Login Summary: {login_summary}")


        # ---- KEEPALIVE ----
        self.broker.start_keepalive(api, interval=30)

        # ---- TOKENS ----
        exchange = "NSE"
        instruments = ["INFY-EQ"]
        self.tokens = self.broker.get_token(api, exchange, instruments)
        print("🎯 Subscribe Tokens:", self.tokens)

        # ---- ORDER MANAGER ----
        order_manager = OrderManager(api)


        # ---- STRATEGY ENGINE ----
        self.strategy_engine = StrategyEngine(
            api=api,
            order_manager=order_manager,
            max_workers=6
        )

        # register your strategy
        strategy_obj = MomentumStrategy()
        self.strategy_engine.register(strategy_obj, min_interval=0.2)
        

        # ---- PORTFOLIO MANAGER ----
        self.portfolio = PortfolioManager(starting_equity=100000.0)

        # register strategy with portfolio
        self.portfolio.add_strategy(strategy_obj)

        # Bind engine → portfolio (this is correct)
        self.strategy_engine.portfolio = self.portfolio

        # Start engine
        self.strategy_engine.start()
        print("🧠 StrategyEngine started.")


        # ---- WEBSOCKET ----
        self.ws = WebSocketManager(
            broker=self.broker,
            on_tick=self.strategy_engine.on_tick,   # <== STRATEGIES GET TICKS
            on_open=self._on_ws_open,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close
        )

        self.ws.start(api, self.tokens)
        print("🔌 WebSocket started.")


    # -----------------------------------------------------------
    # CALLBACKS
    # -----------------------------------------------------------
    def _on_ws_open(self):
        print("🔓 WebSocket OPEN")

    def _on_ws_error(self, err: str):
        print("⚠️ WebSocket ERROR:", err)

    def _on_ws_close(self):
        print("🔒 WebSocket CLOSED")


    # -----------------------------------------------------------
    # GRACEFUL SHUTDOWN
    # -----------------------------------------------------------
    def stop(self):

        print("\n🛑 Stopping App...")

        # 1) Stop StrategyEngine
        if self.strategy_engine:
            self.strategy_engine.stop()

        # 2) Stop WebSocket
        if self.ws:
            self.ws.stop()

        # 3) Logout
        if self.api:
            resp = self.broker.logout()
            print(f"👋 Logout Summary: {resp}")

        # 4) Stop mock server
        if self.mock_process:
            print("🟡 Terminating Mock Server...")
            try:
                self.mock_process.terminate()
                self.mock_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                print("⚠️ Mock server did not exit, killing...")
                self.mock_process.kill()