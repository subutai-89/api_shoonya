from src.api_client import login_shoonya, logout_shoonya
from src.order_manager import OrderManager
from src.data_handler import to_dataframe, process_and_save_data, print_pretty


# Login
api, login_response = login_shoonya()
print_pretty(login_response)

# Perform Trading Here
order_manager = OrderManager(api)

# Place buy Order
order_response = order_manager.place_order(
    buy_or_sell='B',  # 'B' for Buy, 'S' for Sell
    product_type='C',  # 'C' for Cash, 'M' for Margin, etc.
    exchange='NSE',  # Exchange (e.g., NSE, BSE)
    tradingsymbol='INFY-EQ',  # Trading symbol (e.g., INFY-EQ)
    quantity=1,  # Quantity to buy/sell
    price_type='LMT',  # 'LMT' for Limit, 'MKT' for Market
    price=1500  # Price (for Limit orders)
)
print_pretty(order_response)        

# Query data
order_book = order_manager.get_order_book()
trade_book = order_manager.get_trade_book()
positions = order_manager.get_positions()
holdings = order_manager.get_holdings()
limits = order_manager.get_limits()

# Convert to DataFrames
df_order_book = to_dataframe(order_book)
df_trade_book = to_dataframe(trade_book)
df_positions = to_dataframe(positions)
df_holdings = to_dataframe(holdings)
df_limits = to_dataframe(limits)

# Process and save all DataFrames
data_list = [
    (df_order_book, 'order_book.csv'),
    (df_trade_book, 'trade_book.csv'),
    (df_positions, 'positions.csv'),
    (df_holdings, 'holdings.csv'),
    (df_limits, 'limits.csv')
]
process_and_save_data(data_list)

# Print pretty
print("Order Book:")
print_pretty(order_book)

print("Trade Book:")
print_pretty(trade_book)

print("Positions:")
print_pretty(positions)

print("Holdings:")
print_pretty(holdings)

print("Limits:")
print_pretty(limits)

# Logout
logout_response = logout_shoonya(api)
print_pretty(logout_response)
