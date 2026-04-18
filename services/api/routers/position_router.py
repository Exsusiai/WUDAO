from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from python.core.logging_config import get_logger
from python.domain.position_sizer import (
    MarketType,
    SizingInput,
    SizingResult,
    TradeSide,
    calculate_position,
    with_take_profit,
)

logger = get_logger(__name__)
router = APIRouter()

_DECIMAL_FIELDS = (
    "account_equity",
    "risk_percent",
    "entry_price",
    "stop_price",
    "leverage",
    "fee_rate",
    "take_profit_price",
)


class PositionCalculateRequest(BaseModel):
    account_equity: Decimal
    risk_percent: Decimal
    entry_price: Decimal
    stop_price: Decimal
    side: TradeSide
    market_type: MarketType = MarketType.SPOT
    leverage: Decimal = Decimal("1")
    fee_rate: Decimal = Decimal("0")
    take_profit_price: Decimal | None = None

    @field_validator(*_DECIMAL_FIELDS, mode="before")
    @classmethod
    def _coerce_via_string(cls, v: object) -> Decimal | None:
        if v is None:
            return None
        return Decimal(str(v))


class PositionCalculateResponse(BaseModel):
    position_size: str
    risk_amount: str
    reward_risk_ratio: str | None
    stop_distance_percent: str
    stop_price: str
    notional_value: str
    margin_required: str
    fee_estimate: str
    market_type: MarketType
    side: TradeSide

    @classmethod
    def from_result(cls, result: SizingResult) -> PositionCalculateResponse:
        def _fmt(d: Decimal) -> str:
            return format(d, "f")

        return cls(
            position_size=_fmt(result.position_size),
            risk_amount=_fmt(result.risk_amount),
            reward_risk_ratio=(
                _fmt(result.reward_risk_ratio)
                if result.reward_risk_ratio is not None
                else None
            ),
            stop_distance_percent=_fmt(result.stop_distance_percent),
            stop_price=_fmt(result.stop_price),
            notional_value=_fmt(result.notional_value),
            margin_required=_fmt(result.margin_required),
            fee_estimate=_fmt(result.fee_estimate),
            market_type=result.market_type,
            side=result.side,
        )


@router.post(
    "/api/position/calculate",
    response_model=PositionCalculateResponse,
)
def calculate_position_size(
    body: PositionCalculateRequest,
) -> PositionCalculateResponse:
    logger.info(
        "position_calculate",
        side=body.side.value,
        market_type=body.market_type.value,
    )
    try:
        inp = SizingInput(
            account_equity=body.account_equity,
            risk_percent=body.risk_percent,
            entry_price=body.entry_price,
            stop_price=body.stop_price,
            side=body.side,
            market_type=body.market_type,
            leverage=body.leverage,
            fee_rate=body.fee_rate,
        )
        result = calculate_position(inp)

        if body.take_profit_price is not None:
            result = with_take_profit(
                result, body.take_profit_price, body.entry_price
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PositionCalculateResponse.from_result(result)
