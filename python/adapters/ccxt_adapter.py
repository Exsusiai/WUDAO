from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import ccxt.async_support as ccxt_async

from python.domain.exchange import (
    AccountBalance,
    Balance,
    ExchangeMode,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


class CcxtAdapter:
    def __init__(
        self,
        exchange_id: str,
        api_key: str,
        api_secret: str,
        mode: ExchangeMode,
        password: str | None = None,
    ) -> None:
        if exchange_id not in ccxt_async.exchanges:
            raise ValueError(f"Unsupported exchange: {exchange_id}")

        exchange_class = getattr(ccxt_async, exchange_id)
        config: dict[str, Any] = {"apiKey": api_key, "secret": api_secret}
        if password is not None:
            config["password"] = password

        self._exchange = exchange_class(config)

        if mode == ExchangeMode.SANDBOX:
            self._exchange.set_sandbox_mode(True)

    async def __aenter__(self) -> CcxtAdapter:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._exchange.close()

    async def place_order(self, request: OrderRequest) -> OrderResult:
        params: dict[str, Any] = {}
        if request.stop_loss is not None:
            params["stopLoss"] = float(request.stop_loss)
        if request.take_profit is not None:
            params["takeProfit"] = float(request.take_profit)
        if request.client_order_id is not None:
            params["clientOrderId"] = request.client_order_id

        raw = await self._exchange.create_order(
            symbol=request.symbol,
            type=request.order_type.value,
            side=request.side.value,
            amount=float(request.quantity),
            price=float(request.price) if request.price is not None else None,
            params=params,
        )
        return self._parse_order(raw)

    async def cancel_order(self, exchange_order_id: str, symbol: str) -> OrderResult:
        raw = await self._exchange.cancel_order(exchange_order_id, symbol)
        return self._parse_order(raw)

    async def get_order(self, exchange_order_id: str, symbol: str) -> OrderResult:
        raw = await self._exchange.fetch_order(exchange_order_id, symbol)
        return self._parse_order(raw)

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        raw_list = await self._exchange.fetch_open_orders(symbol)
        return [self._parse_order(raw) for raw in raw_list]

    async def get_balance(self) -> AccountBalance:
        raw = await self._exchange.fetch_balance()
        return self._parse_balance(raw)

    async def get_positions(self, symbol: str | None = None) -> list[Position]:
        raw_list = await self._exchange.fetch_positions([symbol] if symbol else None)
        return [self._parse_position(raw) for raw in raw_list]

    def _parse_order(self, raw: dict) -> OrderResult:
        timestamp = raw.get("timestamp")
        if timestamp is not None:
            created_at = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        else:
            created_at = datetime.now(tz=timezone.utc)

        last_trade_timestamp = raw.get("lastTradeTimestamp") or timestamp
        if last_trade_timestamp is not None:
            updated_at = datetime.fromtimestamp(last_trade_timestamp / 1000, tz=timezone.utc)
        else:
            updated_at = created_at

        fee_info = raw.get("fee") or {}
        fee = self._to_decimal(fee_info.get("cost"))
        fee_currency = fee_info.get("currency") or ""

        side_str = raw.get("side", "buy")
        side = OrderSide(side_str) if side_str in ("buy", "sell") else OrderSide.BUY

        order_type_str = raw.get("type", "market")
        order_type = OrderType(order_type_str) if order_type_str in ("market", "limit") else OrderType.MARKET

        price_val = raw.get("price")
        avg_price_val = raw.get("average")

        return OrderResult(
            exchange_order_id=str(raw.get("id", "")),
            symbol=raw.get("symbol", ""),
            side=side,
            order_type=order_type,
            status=self._to_status(raw.get("status", "")),
            quantity=self._to_decimal(raw.get("amount")),
            filled_quantity=self._to_decimal(raw.get("filled")),
            price=Decimal(str(price_val)) if price_val is not None else None,
            average_fill_price=Decimal(str(avg_price_val)) if avg_price_val is not None else None,
            fee=fee,
            fee_currency=fee_currency,
            created_at=created_at,
            updated_at=updated_at,
            raw=raw,
        )

    def _parse_balance(self, raw: dict) -> AccountBalance:
        balances: list[Balance] = []
        total_dict = raw.get("total") or {}
        free_dict = raw.get("free") or {}
        used_dict = raw.get("used") or {}

        for currency, total_val in total_dict.items():
            total = self._to_decimal(total_val)
            if total == Decimal("0"):
                continue
            free = self._to_decimal(free_dict.get(currency, 0))
            used = self._to_decimal(used_dict.get(currency, 0))
            balances.append(Balance(currency=currency, total=total, free=free, used=used))

        timestamp_ms = raw.get("timestamp")
        if timestamp_ms is not None:
            ts = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        else:
            ts = datetime.now(tz=timezone.utc)

        return AccountBalance(balances=tuple(balances), timestamp=ts)

    def _parse_position(self, raw: dict) -> Position:
        timestamp_ms = raw.get("timestamp")
        if timestamp_ms is not None:
            ts = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        else:
            ts = datetime.now(tz=timezone.utc)

        side_str = raw.get("side", "buy")
        side = OrderSide(side_str) if side_str in ("buy", "sell") else OrderSide.BUY

        mark_price_val = raw.get("markPrice")
        unrealized_pnl_val = raw.get("unrealizedPnl")
        liquidation_price_val = raw.get("liquidationPrice")

        return Position(
            symbol=raw.get("symbol", ""),
            side=side,
            quantity=self._to_decimal(raw.get("contracts") or raw.get("size")),
            entry_price=self._to_decimal(raw.get("entryPrice")),
            mark_price=Decimal(str(mark_price_val)) if mark_price_val is not None else None,
            unrealized_pnl=Decimal(str(unrealized_pnl_val)) if unrealized_pnl_val is not None else None,
            leverage=self._to_decimal(raw.get("leverage") or 1),
            liquidation_price=Decimal(str(liquidation_price_val)) if liquidation_price_val is not None else None,
            timestamp=ts,
        )

    def _to_status(self, ccxt_status: str) -> OrderStatus:
        mapping = {
            "open": OrderStatus.OPEN,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED,
            "pending": OrderStatus.PENDING,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
        }
        return mapping.get(ccxt_status, OrderStatus.PENDING)

    def _to_decimal(self, value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        return Decimal(str(value))
