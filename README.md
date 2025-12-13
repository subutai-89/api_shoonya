```markdown
# Shoonya WebSocket API Client

This repository provides a Python-based WebSocket client for interacting with the Shoonya API, which is used to receive real-time market data, including price ticks and order book updates. It supports both **live** and **mock** WebSocket connections for testing and production environments.

## Features

- **Real-time Price and Market Data**: Subscribe to multiple instruments and receive live price updates (ticks).
- **Multiple Instrument Support**: Track and process multiple instruments (tokens) simultaneously.
- **Error Handling and Debugging**: Verbose logging and heartbeat monitoring to ensure robust and error-free connections.
- **Mock Mode**: Simulate WebSocket server for testing purposes with mock market data.
- **Strategy Engine Integration**: Forward received price ticks and order book updates to a strategy engine for further processing.

## Prerequisites

- Python 3.6 or higher
- Shoonya API account (for live mode)

## Installation

- Clone the repository:
  ```
  git clone https://github.com/your-username/shoonya-websocket-api-client.git
  ```
- Navigate to the project directory:
  ```
  cd shoonya-websocket-api-client
  ```
- Create a virtual environment:
  ```
  python3 -m venv venv
  ```
- Activate the virtual environment:
  - On macOS/Linux:
    ```
    source venv/bin/activate
    ```
  - On Windows:
    ```
    .\venv\Scripts\activate
    ```
- Install dependencies:
  ```
  pip install -r requirements.txt
  ```
```

## Architecture Overview

Market data is received via Shoonya WebSocket and processed using a
snapshot + delta merge model (`tk` / `tf`), similar to professional
exchange feeds.

### High-level flow:
```
Shoonya WebSocket → WebSocketManager → StrategyEngine → Strategies
```
For a **detailed, line-by-line runtime flow**, see:
docs/RUNTIME_FLOW.md

## Usage

### Initialize WebSocketManager

In the main script or module (e.g., `application.py`), instantiate the `WebSocketManager` class and pass necessary parameters.

```
from src.websocket_manager import WebSocketManager
from src.brokers.shoonya_client import ShoonyaClient
```

# Create a Shoonya API client instance
broker = ShoonyaClient()

# Define a callback function to handle incoming price ticks
def on_tick(tick_data):
    print(f"Received tick data: {tick_data}")

# Initialize the WebSocketManager
ws_manager = WebSocketManager(
    broker=broker,
    on_tick=on_tick,
    verbose=True,  # Set to True for detailed logs
    print_ticks=True  # Set to True to print live ticks
)

# Start the WebSocket connection
```
ws_manager.start(api=None, tokens=["MCX|467741", "MCX|472782"])
```

## Configuration Options

- `verbose`: If set to `True`, verbose logs will be printed, showing raw messages, market data updates, and other WebSocket-related events.
- `print_ticks`: If set to `True`, live ticks (price updates) will be printed to the console.
- `price_heartbeat_timeout`: The timeout (in seconds) for price tick heartbeat (default: 5 minutes).
- `order_heartbeat_timeout`: The timeout (in seconds) for order book heartbeat (default: 60 seconds).

## Mock Mode

To run the client in mock mode, which simulates a WebSocket server for testing:

```
ws_manager.start(api=None, tokens=["MCX|467741", "MCX|472782"])
```
Make sure that the mock mode is enabled in the ShoonyaClient configuration. Mock mode uses a predefined local WebSocket server that sends mock market data.

## Handling Multiple Instruments

The `WebSocketManager` supports subscribing to multiple instruments (tokens). You can pass a list of tokens when initializing the `WebSocketManager` instance:

```
tokens = ["MCX|472782", "MCX|472783", "MCX|464926"]
ws_manager.start(api=None, tokens=tokens)
```
The strategy engine will receive price ticks for each instrument separately and process them independently.

## Strategy Engine Integration

Once a tick is received (either full snapshot `tk` or incremental `tf`), the data is forwarded to the strategy engine. A simple example of the strategy callback function:

```
def on_tick(tick_data):
    instrument_name = tick_data.get("instrument_name", "Unknown Instrument")
    print(f"Processing tick for {instrument_name}: {tick_data}")
```

## Heartbeat Monitoring

The `WebSocketManager` includes a heartbeat monitor to ensure the connection is active. If no price ticks or order book updates are received within the specified timeout periods, warnings are logged.

- Price Tick Timeout: Default is 5 minutes.
- Order Book Update Timeout: Default is 60 seconds.

You can modify these values when initializing the `WebSocketManager` to suit your needs.

## Contributing

We welcome contributions! If you'd like to contribute, follow these steps:

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request with a detailed explanation of your changes

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgments

- Shoonya API for providing real-time market data feeds.
- Python WebSocket library for seamless WebSocket communication.
```