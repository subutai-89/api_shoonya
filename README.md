project_root/
│
├── config/
│   ├── credentials.yml          # Store API keys and credentials securely
│   └── settings.yml             # Bot-specific settings (e.g., trading pairs, parameters)
│
├── src/
│   ├── __init__.py
│   ├── api_client.py            # Handles API authentication and requests
│   ├── order_manager.py         # Functions for placing, modifying, and canceling orders
│   ├── data_handler.py          # Fetching market data and processing
│   ├── strategy.py              # Trading logic and strategy implementation
│   └── utils.py                 # Helper functions (logging, error handling, etc.)
│
├── logs/
│   └── app.log                  # Logs for debugging and monitoring
│
├── tests/
│   ├── test_api_client.py       # Unit tests for API client
│   ├── test_order_manager.py    # Unit tests for order management
│   └── test_strategy.py         # Unit tests for strategy logic
│
├── requirements.txt             # List of Python dependencies
├── main.py                      # Entry point for running the bot
└── README.md                    # Project documentation and setup instructions


GITHUB: https://github.com/Shoonya-Dev/ShoonyaApi-py