from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

import pytest

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


class TestOrderSideEnum:
    def test_values(self) -> None:
        assert OrderSide.BUY == "buy"
        assert OrderSide.SELL == "sell"

    def test_is_str(self) -> None:
        assert isinstance(OrderSide.BUY, str)


class TestOrderTypeEnum:
    def test_values(self) -> None:
        assert OrderType.MARKET == "market"
        assert OrderType.LIMIT == "limit"

    def test_is_str(self) -> None:
        assert isinstance(OrderType.MARKET, str)


class TestOrderStatusEnum:
    def test_all_values(self) -> None:
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.OPEN == "open"
        assert OrderStatus.PARTIALLY_FILLED == "partially_filled"
        assert OrderStatus.FILLED == "filled"
        assert OrderStatus.CANCELLED == "cancelled"
        assert OrderStatus.REJECTED == "rejected"
        assert OrderStatus.EXPIRED == "expired"

    def test_is_str(self) -> None:
        assert isinstance(OrderStatus.FILLED, str)


class TestExchangeModeEnum:
    def test_values(self) -> None:
        assert ExchangeMode.SANDBOX == "sandbox"
        assert ExchangeMode.LIVE == "live"

    def test_is_str(self) -> None:
        assert isinstance(ExchangeMode.SANDBOX, str)


class TestOrderRequest:
    def _make(self, **kwargs) -> OrderRequest:
        defaults = dict(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
        )
        defaults.update(kwargs)
        return OrderRequest(**defaults)

    def test_basic_fields(self) -> None:
        req = self._make()
        assert req.symbol == "BTC/USDT"
        assert req.side == OrderSide.BUY
        assert req.order_type == OrderType.MARKET
        assert req.quantity == Decimal("0.1")

    def test_defaults_are_none(self) -> None:
        req = self._make()
        assert req.price is None
        assert req.stop_loss is None
        assert req.take_profit is None
        assert req.client_order_id is None

    def test_frozen(self) -> None:
        req = self._make()
        with pytest.raises(FrozenInstanceError):
            req.symbol = "ETH/USDT"  # type: ignore[misc]

    def test_quantity_is_decimal(self) -> None:
        req = self._make(quantity=Decimal("1.5"))
        assert isinstance(req.quantity, Decimal)


class TestOrderResult:
    def _make(self, **kwargs) -> OrderResult:
        now = datetime.now(tz=timezone.utc)
        defaults = dict(
            exchange_order_id="abc123",
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            quantity=Decimal("0.1"),
            filled_quantity=Decimal("0.1"),
            price=None,
            average_fill_price=Decimal("50000"),
            fee=Decimal("0.01"),
            fee_currency="USDT",
            created_at=now,
            updated_at=now,
        )
        defaults.update(kwargs)
        return OrderResult(**defaults)

    def test_raw_defaults_to_empty_dict(self) -> None:
        result = self._make()
        assert result.raw == {}

    def test_frozen(self) -> None:
        result = self._make()
        with pytest.raises(FrozenInstanceError):
            result.symbol = "ETH/USDT"  # type: ignore[misc]

    def test_financial_fields_are_decimal(self) -> None:
        result = self._make()
        assert isinstance(result.quantity, Decimal)
        assert isinstance(result.filled_quantity, Decimal)
        assert isinstance(result.fee, Decimal)

    def test_raw_custom(self) -> None:
        result = self._make(raw={"id": "xyz"})
        assert result.raw == {"id": "xyz"}


class TestBalance:
    def test_fields(self) -> None:
        b = Balance(
            currency="USDT",
            total=Decimal("1000"),
            free=Decimal("800"),
            used=Decimal("200"),
        )
        assert b.currency == "USDT"
        assert isinstance(b.total, Decimal)

    def test_frozen(self) -> None:
        b = Balance(currency="BTC", total=Decimal("1"), free=Decimal("1"), used=Decimal("0"))
        with pytest.raises(FrozenInstanceError):
            b.currency = "ETH"  # type: ignore[misc]


class TestAccountBalance:
    def test_balances_is_tuple(self) -> None:
        b = Balance(currency="USDT", total=Decimal("1000"), free=Decimal("800"), used=Decimal("200"))
        ab = AccountBalance(balances=(b,), timestamp=datetime.now(tz=timezone.utc))
        assert isinstance(ab.balances, tuple)

    def test_frozen(self) -> None:
        ab = AccountBalance(balances=(), timestamp=datetime.now(tz=timezone.utc))
        with pytest.raises(FrozenInstanceError):
            ab.balances = ()  # type: ignore[misc]


class TestPosition:
    def test_fields(self) -> None:
        p = Position(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            entry_price=Decimal("50000"),
            mark_price=None,
            unrealized_pnl=None,
            leverage=Decimal("1"),
            liquidation_price=None,
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert p.symbol == "BTC/USDT"
        assert isinstance(p.quantity, Decimal)
        assert isinstance(p.entry_price, Decimal)

    def test_frozen(self) -> None:
        p = Position(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            entry_price=Decimal("50000"),
            mark_price=None,
            unrealized_pnl=None,
            leverage=Decimal("1"),
            liquidation_price=None,
            timestamp=datetime.now(tz=timezone.utc),
        )
        with pytest.raises(FrozenInstanceError):
            p.symbol = "ETH/USDT"  # type: ignore[misc]
