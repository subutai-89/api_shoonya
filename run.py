# run.py
import signal
import sys
import os

from src.brokers.shoonya_client import ShoonyaClient
from src.brokers.mock_client import MockClient
from src.app.application import App


# --------------------------------------------
# CONFIGURATION
# --------------------------------------------

# RUN_MODE = "live"; MOCK_PRICE_MODE = None
RUN_MODE = "mock"; MOCK_PRICE_MODE = "normal"
# RUN_MODE = "mock"; MOCK_PRICE_MODE = "momentum"
# RUN_MODE = "mock"; MOCK_PRICE_MODE = "crash"
# RUN_MODE = "mock"; MOCK_PRICE_MODE = "oscillate"
# RUN_MODE = "mock"; MOCK_PRICE_MODE = "flat"


# --------------------------------------------
# MAIN APP LAUNCHER
# --------------------------------------------

def main():

    # ------------------ SELECT BROKER ------------------
    if RUN_MODE == "live":
        broker = ShoonyaClient(mock=False)
        print("🚀 Running LIVE mode. No mock server will be started.")
    else:
        broker = MockClient()
        print("🧪 Running MOCK mode.")

        # Set the mock environment variable for mock_server.py
        if MOCK_PRICE_MODE:
            os.environ["MOCK_MODE"] = MOCK_PRICE_MODE
            print(f"🧪 Mock price mode set to: {MOCK_PRICE_MODE}")
        else:
            print("🧪 Mock price mode: normal (default)")

    # ------------------ START APP ------------------
    app = App(broker)
    app.start()

    # ------------------ GRACEFUL SHUTDOWN ------------------
    def handle_interrupt(sig, frame):
        print("\n🔻 KeyboardInterrupt received — shutting down...")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    print("🟢 App is running. Press Ctrl+C to exit.")
    signal.pause()


if __name__ == "__main__":
    main()
