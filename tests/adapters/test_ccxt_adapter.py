from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from python.adapters.ccxt_adapter import CcxtAdapter
from python.domain.exchange import (
    AccountBalance,
    ExchangeMode,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


def _make_raw_order(**kwargs) -> dict:
    defaults = {
        "id": "order-1",
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "market",
        "status": "closed",
        "amount": 0.1,
        "filled": 0.1,
        "price": None,
        "average": 50000.0,
        "fee": {"cost": 0.005, "currency": "USDT"},
        "timestamp": 1_700_000_000_000,
        "lastTradeTimestamp": 1_700_000_001_000,
    }
    defaults.update(kwargs)
    return defaults


def _make_adapter(exchange_id: str = "binance", mode: ExchangeMode = ExchangeMode.SANDBOX) -> CcxtAdapter:
    with patch("python.adapters.ccxt_adapter.ccxt_async") as mock_ccxt:
        mock_ccxt.exchanges = ["binance", "kraken"]
        mock_exchange = MagicMock()
        mock_exchange.set_sandbox_mode = MagicMock()
        mock_ccxt.binance = MagicMock(return_value=mock_exchange)
        mock_ccxt.kraken = MagicMock(return_value=mock_exchange)

        adapter = CcxtAdapter(
            exchange_id=exchange_id,
            api_key="key",
            api_secret="secret",
            mode=mode,
        )
        adapter._exchange = mock_exchange
        return adapter


class TestCcxtAdapterConstructor:
    def test_sandbox_mode_set(self) -> None:
        with patch("python.adapters.ccxt_adapter.ccxt_async") as mock_ccxt:
            mock_ccxt.exchanges = ["binance"]
            mock_exchange = MagicMock()
            mock_ccxt.binance = MagicMock(return_value=mock_exchange)

            CcxtAdapter(
                exchange_id="binance",
                api_key="key",
                api_secret="secret",
                mode=ExchangeMode.SANDBOX,
            )

            mock_exchange.set_sandbox_mode.assert_called_once_with(True)

    def test_live_mode_no_sandbox(self) -> None:
        with patch("python.adapters.ccxt_adapter.ccxt_async") as mock_ccxt:
            mock_ccxt.exchanges = ["binance"]
            mock_exchange = MagicMock()
            mock_ccxt.binance = MagicMock(return_value=mock_exchange)

            CcxtAdapter(
                exchange_id="binance",
                api_key="key",
                api_secret="secret",
                mode=ExchangeMode.LIVE,
            )

            mock_exchange.set_sandbox_mode.assert_not_called()

    def test_invalid_exchange_raises(self) -> None:
        with patch("python.adapters.ccxt_adapter.ccxt_async") as mock_ccxt:
            mock_ccxt.exchanges = ["binance"]

            with pytest.raises(ValueError, match="Unsupported exchange"):
                CcxtAdapter(
                    exchange_id="notaexchange",
                    api_key="key",
                    api_secret="secret",
                    mode=ExchangeMode.SANDBOX,
                )


class TestContextManager:
    async def test_context_manager_calls_close(self) -> None:
        adapter = _make_adapter()
        adapter._exchange.close = AsyncMock()

        async with adapter as ctx:
            assert ctx is adapter

        adapter._exchange.close.assert_called_once()


class TestPlaceOrder:
    async def test_place_order_delegates_to_ccxt(self) -> None:
        adapter = _make_adapter()
        raw = _make_raw_order()
        adapter._exchange.create_order = AsyncMock(return_value=raw)

        request = OrderRequest(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
        )
        result = await adapter.place_order(request)

        adapter._exchange.create_order.assert_called_once()
        call_kwargs = adapter._exchange.create_order.call_args
        assert call_kwargs.kwargs["symbol"] == "BTC/USDT"
        assert call_kwargs.kwargs["side"] == "buy"
        assert call_kwargs.kwargs["type"] == "market"
        assert call_kwargs.kwargs["amount"] == 0.1

    async def test_place_order_returns_order_result(self) -> None:
        adapter = _make_adapter()
        raw = _make_raw_order(status="closed")
        adapter._exchange.create_order = AsyncMock(return_value=raw)

        request = OrderRequest(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
        )
        result = await adapter.place_order(request)

        assert isinstance(result, OrderResult)
        assert result.status == OrderStatus.FILLED
        assert result.exchange_order_id == "order-1"

    async def test_place_order_with_limit_price(self) -> None:
        adapter = _make_adapter()
        raw = _make_raw_order(type="limit", status="open", price=49000.0)
        adapter._exchange.create_order = AsyncMock(return_value=raw)

        request = OrderRequest(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("49000"),
        )
        result = await adapter.place_order(request)

        call_kwargs = adapter._exchange.create_order.call_args
        assert call_kwargs.kwargs["price"] == 49000.0
        assert result.order_type == OrderType.LIMIT


class TestCancelOrder:
    async def test_cancel_order_delegates(self) -> None:
        adapter = _make_adapter()
        raw = _make_raw_order(status="canceled")
        adapter._exchange.cancel_order = AsyncMock(return_value=raw)

        result = await adapter.cancel_order("order-1", "BTC/USDT")

        adapter._exchange.cancel_order.assert_called_once_with("order-1", "BTC/USDT")
        assert result.status == OrderStatus.CANCELLED


class TestGetOrder:
    async def test_get_order_delegates(self) -> None:
        adapter = _make_adapter()
        raw = _make_raw_order(status="open")
        adapter._exchange.fetch_order = AsyncMock(return_value=raw)

        result = await adapter.get_order("order-1", "BTC/USDT")

        adapter._exchange.fetch_order.assert_called_once_with("order-1", "BTC/USDT")
        assert result.status == OrderStatus.OPEN


class TestGetBalance:
    async def test_get_balance_filters_zero(self) -> None:
        adapter = _make_adapter()
        raw = {
            "total": {"BTC": 1.5, "USDT": 0.0, "ETH": 2.0},
            "free": {"BTC": 1.0, "USDT": 0.0, "ETH": 1.5},
            "used": {"BTC": 0.5, "USDT": 0.0, "ETH": 0.5},
            "timestamp": 1_700_000_000_000,
        }
        adapter._exchange.fetch_balance = AsyncMock(return_value=raw)

        result = await adapter.get_balance()

        assert isinstance(result, AccountBalance)
        currencies = {b.currency for b in result.balances}
        assert "USDT" not in currencies
        assert "BTC" in currencies
        assert "ETH" in currencies

    async def test_get_balance_decimal_precision(self) -> None:
        adapter = _make_adapter()
        raw = {
            "total": {"BTC": 1.23456789},
            "free": {"BTC": 1.0},
            "used": {"BTC": 0.23456789},
            "timestamp": 1_700_000_000_000,
        }
        adapter._exchange.fetch_balance = AsyncMock(return_value=raw)

        result = await adapter.get_balance()

        btc = next(b for b in result.balances if b.currency == "BTC")
        assert isinstance(btc.total, Decimal)
        assert btc.total == Decimal("1.23456789")


class TestGetPositions:
    async def test_get_positions_parses(self) -> None:
        adapter = _make_adapter()
        raw_pos = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "contracts": 0.5,
            "entryPrice": 50000.0,
            "markPrice": 51000.0,
            "unrealizedPnl": 500.0,
            "leverage": 10.0,
            "liquidationPrice": 45000.0,
            "timestamp": 1_700_000_000_000,
        }
        adapter._exchange.fetch_positions = AsyncMock(return_value=[raw_pos])

        results = await adapter.get_positions("BTC/USDT")

        assert len(results) == 1
        pos = results[0]
        assert isinstance(pos, Position)
        assert pos.symbol == "BTC/USDT"
        assert pos.quantity == Decimal("0.5")
        assert pos.entry_price == Decimal("50000.0")
        assert pos.mark_price == Decimal("51000.0")

    async def test_get_positions_with_no_symbol(self) -> None:
        adapter = _make_adapter()
        adapter._exchange.fetch_positions = AsyncMock(return_value=[])

        results = await adapter.get_positions()

        adapter._exchange.fetch_positions.assert_called_once_with(None)
        assert results == []


class TestDecimalPrecision:
    async def test_no_float_in_returned_amounts(self) -> None:
        adapter = _make_adapter()
        raw = _make_raw_order(amount=0.123456789, filled=0.123456789)
        adapter._exchange.create_order = AsyncMock(return_value=raw)

        request = OrderRequest(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.123456789"),
        )
        result = await adapter.place_order(request)

        assert isinstance(result.quantity, Decimal)
        assert isinstance(result.filled_quantity, Decimal)
        assert result.quantity == Decimal("0.123456789")
