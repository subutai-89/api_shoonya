import time
import datetime
import pandas as pd

from src.engine.order_manager import OrderManager
from src.data.data_utils import to_dataframe, save_to_csv


def fetch_historical_ohlcv(
    api,
    exchange: str,
    tradingsymbol: str,
    interval: int,
    days: int = 30,
    data_dir: str = 'data/historical/ohlcv'
):
    """Fetch historical intraday OHLCV from Shoonya."""
    order_manager = OrderManager(api)

    token_list = api.searchscrip(exchange, tradingsymbol)
    if not token_list or "values" not in token_list:
        print(f"Token not found for {tradingsymbol}")
        return None

    token = token_list["values"][0]["token"]

    end_date = int(time.time())
    start_date = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())

    ohlcv_data = order_manager.get_historical_data(
        exchange=exchange,
        tradingsymbol=f"{exchange}|{token}",
        interval=interval,
        start_date=start_date,
        end_date=end_date
    )

    if not ohlcv_data:
        print("No OHLCV data returned from API.")
        return None

    df = to_dataframe(ohlcv_data)
    df['time'] = pd.to_datetime(df['time'], format='%d-%m-%Y %H:%M:%S')
    df = df.sort_values(by='time').reset_index(drop=True)

    filename = f"{tradingsymbol}_OHLCV_last_{days}_days.csv"
    save_to_csv(df, filename, data_dir)

    print(f"Saved OHLCV data to {data_dir}/{filename}")
    return df
