import os
from src.data.data_utils import to_dataframe, validate_data, clean_data, save_to_csv


class BrokerDataFetcher:
    """
    Helper class that fetches broker-specific data
    (order book, trade book, positions, holdings, limits)
    via OrderManager.

    This keeps data utilities generic and removes broker logic
    from data_utils.
    """

    def __init__(self, order_manager):
        self.order_manager = order_manager

    # ---------------------------------------------------------
    # Fetch raw data from OrderManager
    # ---------------------------------------------------------

    def get_order_book(self):
        return self.order_manager.get_order_book()

    def get_trade_book(self):
        return self.order_manager.get_trade_book()

    def get_positions(self):
        return self.order_manager.get_positions()

    def get_holdings(self):
        return self.order_manager.get_holdings()

    def get_limits(self):
        return self.order_manager.get_limits()

    # ---------------------------------------------------------
    # Convert & clean
    # ---------------------------------------------------------

    def _process(self, raw):
        df = to_dataframe(raw)
        validate_data(df)
        df = clean_data(df)
        return df

    # ---------------------------------------------------------
    # Save all data categories
    # ---------------------------------------------------------

    def save_all(self, data_dir="data/broker"):
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        datasets = [
            ("order_book.csv", self.get_order_book()),
            ("trade_book.csv", self.get_trade_book()),
            ("positions.csv", self.get_positions()),
            ("holdings.csv", self.get_holdings()),
            ("limits.csv", self.get_limits()),
        ]

        for filename, raw in datasets:
            df = self._process(raw)
            save_to_csv(df, filename, data_dir)

        print(f"Saved broker account data under {data_dir}/")

    # ---------------------------------------------------------
    # Pretty printing
    # ---------------------------------------------------------

    def print_all(self):
        print("\nORDER BOOK:")
        print(self.get_order_book())

        print("\nTRADE BOOK:")
        print(self.get_trade_book())

        print("\nPOSITIONS:")
        print(self.get_positions())

        print("\nHOLDINGS:")
        print(self.get_holdings())

        print("\nLIMITS / MARGIN:")
        print(self.get_limits())
