import logging
from typing import Protocol, runtime_checkable, Optional, Dict, Any

from NorenRestApiPy.NorenApi import NorenApi
from src.engine.risk_engine import RiskEngine, RiskPolicy, RiskViolation

logger = logging.getLogger(__name__)


@runtime_checkable
class BrokerAPI(Protocol):
    def place_order(self, **kwargs) -> Dict[str, Any]: ...
    def modify_order(self, **kwargs) -> Dict[str, Any]: ...
    def cancel_order(self, **kwargs) -> Dict[str, Any]: ...
    def exit_order(self, **kwargs) -> Dict[str, Any]: ...
    def get_order_book(self) -> Any: ...
    def single_order_history(self, orderno: str) -> Any: ...
    def get_positions(self) -> Any: ...
    def convert_position(self, **kwargs) -> Any: ...
    def get_trade_book(self) -> Any: ...
    def get_holdings(self) -> Any: ...
    def get_limits(self, **kwargs) -> Any: ...
    def get_order_status(self, orderno: str) -> Any: ...
    def get_market_depth(self, **kwargs) -> Any: ...
    def get_time_price_series(self, **kwargs) -> Any: ...


class OrderManager:
    def __init__(self, api: BrokerAPI):
        self.api = api
        self.risk_engine = RiskEngine()
        # optional mapping or config can be added here

    # ----------------- risk helpers -----------------
    def set_risk_policy(self, strategy_name: str, policy: RiskPolicy):
        """
        Register a RiskPolicy for a particular strategy.
        """
        self.risk_engine.set_policy(strategy_name, policy)

    # ----------------- order helpers -----------------
    def _normalize_order_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure the order dict uses a predictable shape for the risk checks.
        Accepts the same kwargs you pass to place_order.
        """
        order = {
            "buy_or_sell": kwargs.get("buy_or_sell"),
            "product_type": kwargs.get("product_type"),
            "exchange": kwargs.get("exchange"),
            "tradingsymbol": kwargs.get("tradingsymbol"),
            "quantity": int(kwargs.get("quantity") or 0),
            "price_type": kwargs.get("price_type"),
            "price": kwargs.get("price"),
            "trigger_price": kwargs.get("trigger_price"),
            "retention": kwargs.get("retention"),
            "remarks": kwargs.get("remarks"),
        }

        # If caller provided meta or strategy_name, keep it
        meta = kwargs.get("meta")
        if meta:
            order["meta"] = meta
        else:
            # allow a top-level strategy_name key (convenience)
            strat = kwargs.get("strategy_name")
            if strat:
                order["meta"] = {"strategy_name": strat}

        # optional current position hint (used to check prospective pos limits)
        if "current_position" in kwargs:
            order["current_position"] = kwargs.get("current_position")

        return order

    def place_order(self,
                    buy_or_sell: str,
                    product_type: str,
                    exchange: str,
                    tradingsymbol: str,
                    quantity: int,
                    price_type: str,
                    price: Optional[float] = None,
                    trigger_price: Optional[float] = None,
                    retention: str = 'DAY',
                    remarks: Optional[str] = None,
                    meta: Optional[Dict[str, Any]] = None,
                    strategy_name: Optional[str] = None,
                    current_position: Optional[int] = None
                    ) -> Dict[str, Any]:
        """
        Place a new order with pre-order risk checks.

        Returns broker response on success, or {"rejected": True, "reason": "..."} on rejection.
        """
        # build kwargs dict for both risk check and broker call
        kwargs = dict(
            buy_or_sell=buy_or_sell,
            product_type=product_type,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            quantity=quantity,
            price_type=price_type,
            price=price,
            trigger_price=trigger_price,
            retention=retention,
            remarks=remarks,
            meta=meta,
            strategy_name=strategy_name,
            current_position=current_position,
        )

        order_for_check = self._normalize_order_kwargs(kwargs)

        # If meta not provided, attach strategy_name hint if available
        if "meta" not in order_for_check or not order_for_check.get("meta"):
            if strategy_name:
                order_for_check["meta"] = {"strategy_name": strategy_name}

        # run risk checks
        try:
            self.risk_engine.check_order(order_for_check)
        except RiskViolation as rv:
            logger.warning("Order rejected by RiskEngine: %s", rv)
            return {"rejected": True, "reason": str(rv)}

        # If checks passed, call the underlying broker API
        try:
            result = self.api.place_order(
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

            logger.debug("Order placed: %s -> %s", order_for_check, result)

            # Guarantee return type is Dict[str, Any]
            if result is None:
                return {"error": "broker returned None", "success": False}

            return result
        
        except Exception:
            logger.exception("Error sending order to broker")
            raise

    def modify_order(self,
                     exchange: str,
                     tradingsymbol: str,
                     orderno: str,
                     newquantity: int,
                     newprice_type: str,
                     newprice: Optional[float] = None,
                     newtrigger_price: Optional[float] = None,
                     meta: Optional[Dict[str, Any]] = None,
                     strategy_name: Optional[str] = None,
                     current_position: Optional[int] = None
                     ):
        """
        Modify an existing order. Best-effort risk checks are applied when newquantity is present.
        If you want strict modify-time checks, include 'current_position' hint.
        """
        kwargs = dict(
            buy_or_sell=None,
            product_type=None,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            quantity=newquantity,
            price_type=newprice_type,
            price=newprice,
            trigger_price=newtrigger_price,
            meta=meta,
            strategy_name=strategy_name,
            current_position=current_position
        )

        order_for_check = self._normalize_order_kwargs(kwargs)
        if strategy_name and ("meta" not in order_for_check or not order_for_check.get("meta")):
            order_for_check["meta"] = {"strategy_name": strategy_name}

        # Only run check if quantity provided (we want to avoid false positives otherwise)
        try:
            if newquantity:
                self.risk_engine.check_order(order_for_check)
        except RiskViolation as rv:
            logger.warning("Modify rejected by RiskEngine: %s", rv)
            return {"rejected": True, "reason": str(rv)}

        # Proceed with modify call
        return self.api.modify_order(
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            orderno=orderno,
            newquantity=newquantity,
            newprice_type=newprice_type,
            newprice=newprice,
            newtrigger_price=newtrigger_price
        )

    def cancel_order(self, orderno: str):
        """
        Cancel an order. No risk check required for cancel.
        """
        return self.api.cancel_order(orderno=orderno)

    def exit_order(self, orderno: str, prd: str):
        """
        Exit a cover or bracket order.
        """
        return self.api.exit_order(orderno=orderno, prd=prd)

    def get_order_book(self):
        return self.api.get_order_book()

    def single_order_history(self, orderno: str):
        return self.api.single_order_history(orderno=orderno)

    def get_positions(self):
        return self.api.get_positions()

    def convert_position(self, exchange: str, tradingsymbol: str, pos_type: str, new_pos_type: str):
        return self.api.convert_position(
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            pos_type=pos_type,
            new_pos_type=new_pos_type
        )

    def get_trade_book(self):
        return self.api.get_trade_book()

    def get_holdings(self):
        return self.api.get_holdings()

    def get_limits(self, product_type: Optional[str] = None, segment: Optional[str] = None, exchange: Optional[str] = None):
        return self.api.get_limits(product_type=product_type, segment=segment, exchange=exchange)

    def get_order_status(self, orderno: str):
        return self.api.get_order_status(orderno=orderno)

    def get_market_depth(self, exchange: str, tradingsymbol: str):
        return self.api.get_market_depth(exchange=exchange, tradingsymbol=tradingsymbol)

    def get_historical_data(self, exchange: str, tradingsymbol: str, interval: str, start_date: str, end_date: str):
        ret = self.api.get_time_price_series(
            exchange=exchange,
            token=tradingsymbol,
            starttime=start_date,
            endtime=end_date,
            interval=interval
        )
        if ret is None or not ret:
            logger.debug("No data returned from API for %s", tradingsymbol)
            return []
        return ret

    # ----------------- fill handling -----------------
    def notify_fill(self, order: Dict[str, Any], pnl_delta: float):
        """
        Call this after a fill is processed and PnL updated.
        - order: the order dict (should include meta.strategy_name if available)
        - pnl_delta: realized PnL delta (positive for profit, negative for loss)
        This method updates risk engine state.
        """
        try:
            self.risk_engine.on_fill(order, pnl_delta)
        except Exception:
            logger.exception("Error in notify_fill")

