"""Position sizing calculator — pure domain logic, no DB or exchange dependency.

Supports spot and perpetual (leveraged) markets.
All monetary values use Decimal for financial precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Protocol


class TradeSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class MarketType(str, Enum):
    SPOT = "spot"
    PERPETUAL = "perpetual"


@dataclass(frozen=True)
class SizingInput:
    account_equity: Decimal
    risk_percent: Decimal
    entry_price: Decimal
    stop_price: Decimal
    side: TradeSide
    market_type: MarketType = MarketType.SPOT
    leverage: Decimal = Decimal("1")
    fee_rate: Decimal = Decimal("0")


@dataclass(frozen=True)
class SizingResult:
    position_size: Decimal
    risk_amount: Decimal
    reward_risk_ratio: Decimal | None
    stop_distance_percent: Decimal
    stop_price: Decimal
    notional_value: Decimal
    margin_required: Decimal
    fee_estimate: Decimal
    market_type: MarketType
    side: TradeSide


class PositionSizer(Protocol):
    def calculate(self, inp: SizingInput) -> SizingResult: ...


def _validate_input(inp: SizingInput) -> None:
    if inp.account_equity <= 0:
        raise ValueError(f"account_equity must be positive, got {inp.account_equity}")
    if inp.risk_percent <= 0 or inp.risk_percent > Decimal("100"):
        raise ValueError(f"risk_percent must be in (0, 100], got {inp.risk_percent}")
    if inp.entry_price <= 0:
        raise ValueError(f"entry_price must be positive, got {inp.entry_price}")
    if inp.stop_price <= 0:
        raise ValueError(f"stop_price must be positive, got {inp.stop_price}")
    if inp.leverage < 1:
        raise ValueError(f"leverage must be >= 1, got {inp.leverage}")
    if inp.fee_rate < 0:
        raise ValueError(f"fee_rate must be non-negative, got {inp.fee_rate}")

    if inp.side == TradeSide.LONG and inp.stop_price >= inp.entry_price:
        raise ValueError(
            f"LONG stop_price ({inp.stop_price}) must be below entry_price ({inp.entry_price})"
        )
    if inp.side == TradeSide.SHORT and inp.stop_price <= inp.entry_price:
        raise ValueError(
            f"SHORT stop_price ({inp.stop_price}) must be above entry_price ({inp.entry_price})"
        )


def _stop_distance_percent(entry: Decimal, stop: Decimal) -> Decimal:
    raw = abs(entry - stop) / entry * Decimal("100")
    return raw.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)


def _compute_common(inp: SizingInput) -> SizingResult:
    """Core calculation shared by spot and perpetual sizers."""
    _validate_input(inp)

    risk_amount = inp.account_equity * inp.risk_percent / Decimal("100")
    price_distance = abs(inp.entry_price - inp.stop_price)
    stop_dist_pct = _stop_distance_percent(inp.entry_price, inp.stop_price)

    position_size = (risk_amount / price_distance).quantize(
        Decimal("0.00000001"), rounding=ROUND_DOWN
    )

    notional_value = position_size * inp.entry_price
    margin_required = notional_value / inp.leverage

    if margin_required > inp.account_equity:
        raise ValueError(
            f"Required margin {margin_required} exceeds account equity "
            f"{inp.account_equity}. Stop is too close to entry or risk% too high."
        )

    fee_estimate = notional_value * inp.fee_rate * 2

    return SizingResult(
        position_size=position_size,
        risk_amount=risk_amount,
        reward_risk_ratio=None,
        stop_distance_percent=stop_dist_pct,
        stop_price=inp.stop_price,
        notional_value=notional_value,
        margin_required=margin_required,
        fee_estimate=fee_estimate,
        market_type=inp.market_type,
        side=inp.side,
    )


class SpotSizer:
    """Position sizer for spot markets (no leverage, leverage forced to 1)."""

    def calculate(self, inp: SizingInput) -> SizingResult:
        effective_input = SizingInput(
            account_equity=inp.account_equity,
            risk_percent=inp.risk_percent,
            entry_price=inp.entry_price,
            stop_price=inp.stop_price,
            side=inp.side,
            market_type=MarketType.SPOT,
            leverage=Decimal("1"),
            fee_rate=inp.fee_rate,
        )
        return _compute_common(effective_input)


class PerpetualSizer:
    """Position sizer for perpetual/futures markets (supports leverage)."""

    def calculate(self, inp: SizingInput) -> SizingResult:
        effective_input = SizingInput(
            account_equity=inp.account_equity,
            risk_percent=inp.risk_percent,
            entry_price=inp.entry_price,
            stop_price=inp.stop_price,
            side=inp.side,
            market_type=MarketType.PERPETUAL,
            leverage=inp.leverage,
            fee_rate=inp.fee_rate,
        )
        return _compute_common(effective_input)


def calculate_position(inp: SizingInput) -> SizingResult:
    """Convenience function that dispatches to the correct sizer."""
    sizer: PositionSizer = (
        PerpetualSizer() if inp.market_type == MarketType.PERPETUAL else SpotSizer()
    )
    return sizer.calculate(inp)


def with_take_profit(
    result: SizingResult,
    take_profit_price: Decimal,
    entry_price: Decimal,
) -> SizingResult:
    """Return a new SizingResult with reward_risk_ratio filled in."""
    if take_profit_price <= 0:
        raise ValueError(f"take_profit_price must be positive, got {take_profit_price}")

    if result.side == TradeSide.LONG and take_profit_price <= entry_price:
        raise ValueError(
            f"LONG take_profit ({take_profit_price}) must be above entry ({entry_price})"
        )
    if result.side == TradeSide.SHORT and take_profit_price >= entry_price:
        raise ValueError(
            f"SHORT take_profit ({take_profit_price}) must be below entry ({entry_price})"
        )

    price_distance = abs(entry_price - result.stop_price)
    reward = abs(take_profit_price - entry_price)

    rr = (reward / price_distance).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    return SizingResult(
        position_size=result.position_size,
        risk_amount=result.risk_amount,
        reward_risk_ratio=rr,
        stop_distance_percent=result.stop_distance_percent,
        stop_price=result.stop_price,
        notional_value=result.notional_value,
        margin_required=result.margin_required,
        fee_estimate=result.fee_estimate,
        market_type=result.market_type,
        side=result.side,
    )
