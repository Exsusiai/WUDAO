from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExchangeMode(str, Enum):
    SANDBOX = "sandbox"
    LIVE = "live"


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    client_order_id: str | None = None


@dataclass(frozen=True)
class OrderResult:
    exchange_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    quantity: Decimal
    filled_quantity: Decimal
    price: Decimal | None
    average_fill_price: Decimal | None
    fee: Decimal
    fee_currency: str
    created_at: datetime
    updated_at: datetime
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Balance:
    currency: str
    total: Decimal
    free: Decimal
    used: Decimal


@dataclass(frozen=True)
class AccountBalance:
    balances: tuple[Balance, ...]
    timestamp: datetime


@dataclass(frozen=True)
class Position:
    symbol: str
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    mark_price: Decimal | None
    unrealized_pnl: Decimal | None
    leverage: Decimal
    liquidation_price: Decimal | None
    timestamp: datetime


class ExchangeAdapter(Protocol):
    async def place_order(self, request: OrderRequest) -> OrderResult: ...
    async def cancel_order(self, exchange_order_id: str, symbol: str) -> OrderResult: ...
    async def get_order(self, exchange_order_id: str, symbol: str) -> OrderResult: ...
    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]: ...
    async def get_balance(self) -> AccountBalance: ...
    async def get_positions(self, symbol: str | None = None) -> list[Position]: ...
