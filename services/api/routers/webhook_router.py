"""TradingView webhook receiver.

Accepts POST /api/webhook/tradingview from TradingView alert webhooks.
Auth is via a body-level `secret` field (TradingView cannot send custom headers).
"""
from __future__ import annotations

import hmac
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlmodel import Session

from python.core.database import get_session
from python.core.exchange_service import place_order as svc_place_order
from python.core.logging_config import get_logger
from python.domain.exchange import OrderRequest, OrderSide, OrderType
from services.api.config import settings
from services.api.routers.order_router import OrderResultResponse, _order_to_response

logger = get_logger(__name__)
router = APIRouter()


class TradingViewWebhookRequest(BaseModel):
    secret: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    account_id: UUID | None = None

    @field_validator("quantity", "price", "stop_loss", "take_profit", mode="before")
    @classmethod
    def _coerce_decimal(cls, v: object) -> object:
        if v is None:
            return v
        return Decimal(str(v))


@router.post("/api/webhook/tradingview", status_code=201)
async def tradingview_webhook(
    body: TradingViewWebhookRequest,
    session: Session = Depends(get_session),
) -> OrderResultResponse:
    """Receive a TradingView alert and execute the corresponding order."""
    if not hmac.compare_digest(body.secret, settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    account_id = body.account_id
    if account_id is None:
        default = settings.webhook_default_account_id
        if not default:
            raise HTTPException(
                status_code=422,
                detail="No account_id in payload and WEBHOOK_DEFAULT_ACCOUNT_ID is not set",
            )
        account_id = UUID(default)

    request = OrderRequest(
        symbol=body.symbol,
        side=body.side,
        order_type=body.order_type,
        quantity=body.quantity,
        price=body.price,
        stop_loss=body.stop_loss,
        take_profit=body.take_profit,
    )

    try:
        result = await svc_place_order(account_id, request, session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("webhook_order_failed", error=str(exc), symbol=body.symbol)
        raise HTTPException(status_code=500, detail="Internal error placing order") from exc

    return _order_to_response(result)
