from NorenRestApiPy import NorenApi


class OrderManager:
    def __init__(self, api):
        self.api = api

    def place_order(self, buy_or_sell, product_type, exchange, tradingsymbol, quantity, price_type, price=None, trigger_price=None, retention='DAY', remarks=None):
        """
        Place a new order.
        """
        return self.api.place_order(
            buy_or_sell=buy_or_sell,
            product_type=product_type,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            quantity=quantity,
            discloseqty=0,
            price_type=price_type,
            price=price,
            trigger_price=trigger_price,
            retention=retention,
            remarks=remarks
        )

    def modify_order(self, exchange, tradingsymbol, orderno, newquantity, newprice_type, newprice=None, newtrigger_price=None):
        """
        Modify an existing order.
        """
        return self.api.modify_order(
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            orderno=orderno,
            newquantity=newquantity,
            newprice_type=newprice_type,
            newprice=newprice,
            newtrigger_price=newtrigger_price
        )

    def cancel_order(self, orderno):
        """
        Cancel an order.
        """
        return self.api.cancel_order(orderno=orderno)

    def exit_order(self, orderno, prd):
        """
        Exit a cover or bracket order.
        """
        return self.api.exit_order(orderno=orderno, prd=prd)

    def get_order_book(self):
        """
        Get order book (all open orders).
        """
        return self.api.get_order_book()

    def single_order_history(self, orderno):
        """
        Get history of a single order.
        """
        return self.api.single_order_history(orderno=orderno)

    def get_positions(self):
        """
        Get current positions.
        """
        return self.api.get_positions()

    def convert_position(self, exchange, tradingsymbol, pos_type, new_pos_type):
        """
        Convert position type (e.g., CNC to MIS).
        """
        return self.api.convert_position(
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            pos_type=pos_type,
            new_pos_type=new_pos_type
        )

    def get_trade_book(self):
        """
        Get executed trades.
        """
        return self.api.get_trade_book()

    def get_holdings(self):
        """
        Get current holdings.
        """
        return self.api.get_holdings()

    def get_limits(self, product_type=None, segment=None, exchange=None):
        """
        Get margin and limits details.
        """
        return self.api.get_limits(product_type=product_type, segment=segment, exchange=exchange)

    def get_order_status(self, orderno):
        """
        Get status of a specific order.
        """
        return self.api.get_order_status(orderno=orderno)

    def get_market_depth(self, exchange, tradingsymbol):
        """
        Get market depth for a symbol.
        """
        return self.api.get_market_depth(exchange=exchange, tradingsymbol=tradingsymbol)

    def get_historical_data(self, exchange, tradingsymbol, interval, start_date, end_date):
        """
        Fetch historical data using get_time_price_series.
        """
        ret = self.api.get_time_price_series(
            exchange=exchange,
            token=tradingsymbol,
            starttime=start_date,
            endtime=end_date,
            interval=interval
        )
        if ret is None or not ret:
            print("No data returned from API.")
            return []
        return ret
