"""Order execution REST API router.

Delegates all exchange operations to the exchange_service orchestration layer.
Decimal fields are serialized as fixed-point strings (format(d, "f")) to avoid
scientific notation such as "0E-8" that str(Decimal) can produce.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlmodel import Session

from python.core.database import get_session
from python.core.exchange_service import (
    cancel_order as svc_cancel_order,
    get_balance as svc_get_balance,
    get_open_orders as svc_get_open_orders,
    get_order as svc_get_order,
    get_positions as svc_get_positions,
    place_order as svc_place_order,
)
from python.core.logging_config import get_logger
from python.domain.exchange import (
    AccountBalance,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderType,
    Position,
)

logger = get_logger(__name__)
router = APIRouter()

_DECIMAL_FIELDS = ("quantity", "price", "stop_loss", "take_profit")


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class PlaceOrderRequest(BaseModel):
    account_id: UUID
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    client_order_id: str | None = None

    @field_validator("quantity", "price", "stop_loss", "take_profit", mode="before")
    @classmethod
    def _coerce_decimal(cls, v: object) -> object:
        if v is None:
            return v
        return Decimal(str(v))


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class OrderResultResponse(BaseModel):
    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    status: str
    quantity: str
    filled_quantity: str
    price: str | None
    average_fill_price: str | None
    fee: str
    fee_currency: str
    created_at: str
    updated_at: str


class BalanceItemResponse(BaseModel):
    currency: str
    total: str
    free: str
    used: str


class AccountBalanceResponse(BaseModel):
    balances: list[BalanceItemResponse]
    timestamp: str


class PositionResponse(BaseModel):
    symbol: str
    side: str
    quantity: str
    entry_price: str
    mark_price: str | None
    unrealized_pnl: str | None
    leverage: str
    liquidation_price: str | None
    timestamp: str


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _fmt(d: Decimal | None) -> str | None:
    if d is None:
        return None
    return format(d, "f")


def _order_to_response(result: OrderResult) -> OrderResultResponse:
    return OrderResultResponse(
        exchange_order_id=result.exchange_order_id,
        symbol=result.symbol,
        side=result.side.value,
        order_type=result.order_type.value,
        status=result.status.value,
        quantity=format(result.quantity, "f"),
        filled_quantity=format(result.filled_quantity, "f"),
        price=_fmt(result.price),
        average_fill_price=_fmt(result.average_fill_price),
        fee=format(result.fee, "f"),
        fee_currency=result.fee_currency,
        created_at=result.created_at.isoformat(),
        updated_at=result.updated_at.isoformat(),
    )


def _balance_to_response(balance: AccountBalance) -> AccountBalanceResponse:
    items = [
        BalanceItemResponse(
            currency=b.currency,
            total=format(b.total, "f"),
            free=format(b.free, "f"),
            used=format(b.used, "f"),
        )
        for b in balance.balances
    ]
    return AccountBalanceResponse(
        balances=items,
        timestamp=balance.timestamp.isoformat(),
    )


def _position_to_response(pos: Position) -> PositionResponse:
    return PositionResponse(
        symbol=pos.symbol,
        side=pos.side.value,
        quantity=format(pos.quantity, "f"),
        entry_price=format(pos.entry_price, "f"),
        mark_price=_fmt(pos.mark_price),
        unrealized_pnl=_fmt(pos.unrealized_pnl),
        leverage=format(pos.leverage, "f"),
        liquidation_price=_fmt(pos.liquidation_price),
        timestamp=pos.timestamp.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/api/orders", status_code=201)
async def place_order(
    body: PlaceOrderRequest,
    session: Session = Depends(get_session),
) -> OrderResultResponse:
    """Place a new order on the exchange."""
    request = OrderRequest(
        symbol=body.symbol,
        side=body.side,
        order_type=body.order_type,
        quantity=body.quantity,
        price=body.price,
        stop_loss=body.stop_loss,
        take_profit=body.take_profit,
        client_order_id=body.client_order_id,
    )
    try:
        result = await svc_place_order(body.account_id, request, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _order_to_response(result)


@router.get("/api/orders/balance")
async def get_balance(
    account_id: UUID,
    session: Session = Depends(get_session),
) -> AccountBalanceResponse:
    """Get the account balance from the exchange."""
    try:
        balance = await svc_get_balance(account_id, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _balance_to_response(balance)


@router.get("/api/orders/positions")
async def get_positions(
    account_id: UUID,
    symbol: str | None = None,
    session: Session = Depends(get_session),
) -> list[PositionResponse]:
    """Get open positions, optionally filtered by symbol."""
    try:
        positions = await svc_get_positions(account_id, symbol, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_position_to_response(p) for p in positions]


@router.get("/api/orders")
async def list_open_orders(
    account_id: UUID,
    symbol: str | None = None,
    session: Session = Depends(get_session),
) -> list[OrderResultResponse]:
    """List all open orders, optionally filtered by symbol."""
    try:
        orders = await svc_get_open_orders(account_id, symbol, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_order_to_response(o) for o in orders]


@router.get("/api/orders/{exchange_order_id}")
async def get_order(
    exchange_order_id: str,
    account_id: UUID,
    symbol: str,
    session: Session = Depends(get_session),
) -> OrderResultResponse:
    """Fetch a single order by its exchange-assigned ID."""
    try:
        result = await svc_get_order(account_id, exchange_order_id, symbol, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _order_to_response(result)


@router.delete("/api/orders/{exchange_order_id}", status_code=200)
async def cancel_order(
    exchange_order_id: str,
    account_id: UUID,
    symbol: str,
    session: Session = Depends(get_session),
) -> OrderResultResponse:
    """Cancel an open order."""
    try:
        result = await svc_cancel_order(account_id, exchange_order_id, symbol, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _order_to_response(result)
