"""Comprehensive tests for python/domain/position_sizer.py.

Bugs in position sizing calculations cause real financial loss.
Every branch, edge case, and validation path is covered here.
"""

from __future__ import annotations

import pytest
from decimal import Decimal, ROUND_DOWN

from python.domain.position_sizer import (
    TradeSide,
    MarketType,
    SizingInput,
    SizingResult,
    SpotSizer,
    PerpetualSizer,
    calculate_position,
    with_take_profit,
)


# ---------------------------------------------------------------------------
# Fixtures — reusable inputs
# ---------------------------------------------------------------------------


def make_spot_long(
    equity: str = "10000",
    risk_pct: str = "1",
    entry: str = "100",
    stop: str = "95",
    fee_rate: str = "0",
) -> SizingInput:
    return SizingInput(
        account_equity=Decimal(equity),
        risk_percent=Decimal(risk_pct),
        entry_price=Decimal(entry),
        stop_price=Decimal(stop),
        side=TradeSide.LONG,
        market_type=MarketType.SPOT,
        leverage=Decimal("1"),
        fee_rate=Decimal(fee_rate),
    )


def make_spot_short(
    equity: str = "10000",
    risk_pct: str = "1",
    entry: str = "100",
    stop: str = "105",
    fee_rate: str = "0",
) -> SizingInput:
    return SizingInput(
        account_equity=Decimal(equity),
        risk_percent=Decimal(risk_pct),
        entry_price=Decimal(entry),
        stop_price=Decimal(stop),
        side=TradeSide.SHORT,
        market_type=MarketType.SPOT,
        leverage=Decimal("1"),
        fee_rate=Decimal(fee_rate),
    )


def make_perp_long(
    equity: str = "10000",
    risk_pct: str = "1",
    entry: str = "100",
    stop: str = "95",
    leverage: str = "5",
    fee_rate: str = "0",
) -> SizingInput:
    return SizingInput(
        account_equity=Decimal(equity),
        risk_percent=Decimal(risk_pct),
        entry_price=Decimal(entry),
        stop_price=Decimal(stop),
        side=TradeSide.LONG,
        market_type=MarketType.PERPETUAL,
        leverage=Decimal(leverage),
        fee_rate=Decimal(fee_rate),
    )


def make_perp_short(
    equity: str = "10000",
    risk_pct: str = "1",
    entry: str = "100",
    stop: str = "105",
    leverage: str = "5",
    fee_rate: str = "0",
) -> SizingInput:
    return SizingInput(
        account_equity=Decimal(equity),
        risk_percent=Decimal(risk_pct),
        entry_price=Decimal(entry),
        stop_price=Decimal(stop),
        side=TradeSide.SHORT,
        market_type=MarketType.PERPETUAL,
        leverage=Decimal(leverage),
        fee_rate=Decimal(fee_rate),
    )


# ===========================================================================
# Section 1 — Normal Cases: SPOT
# ===========================================================================


class TestSpotLong:
    """SpotSizer LONG trades — verify every output field."""

    def test_basic_long_position_size(self):
        """$10,000 equity × 1% risk = $100 risk. Stop $5 away → 20 units."""
        inp = make_spot_long(equity="10000", risk_pct="1", entry="100", stop="95")
        result = SpotSizer().calculate(inp)

        # risk = 10000 * 1/100 = 100
        # price_distance = 100 - 95 = 5
        # position_size = 100 / 5 = 20
        assert result.position_size == Decimal("20")

    def test_risk_amount_equals_equity_times_risk_percent(self):
        inp = make_spot_long(equity="10000", risk_pct="2", entry="100", stop="95")
        result = SpotSizer().calculate(inp)
        assert result.risk_amount == Decimal("200")

    def test_stop_distance_percent_long(self):
        """Stop $5 below $100 entry = 5% distance."""
        inp = make_spot_long(entry="100", stop="95")
        result = SpotSizer().calculate(inp)
        expected = Decimal("5")  # abs(100-95)/100 * 100
        assert result.stop_distance_percent == expected

    def test_notional_value_long(self):
        """notional = position_size * entry_price."""
        inp = make_spot_long(equity="10000", risk_pct="1", entry="100", stop="95")
        result = SpotSizer().calculate(inp)
        # position_size = 20, entry = 100 → notional = 2000
        assert result.notional_value == Decimal("2000")

    def test_margin_required_spot_equals_notional(self):
        """Spot always has leverage=1, so margin_required == notional_value."""
        inp = make_spot_long(equity="10000", risk_pct="1", entry="100", stop="95")
        result = SpotSizer().calculate(inp)
        assert result.margin_required == result.notional_value

    def test_fee_estimate_zero_when_fee_rate_zero(self):
        inp = make_spot_long(fee_rate="0")
        result = SpotSizer().calculate(inp)
        assert result.fee_estimate == Decimal("0")

    def test_fee_estimate_with_fee_rate(self):
        """fee_estimate = notional * fee_rate * 2 (entry + exit)."""
        inp = make_spot_long(
            equity="10000", risk_pct="1", entry="100", stop="95", fee_rate="0.001"
        )
        result = SpotSizer().calculate(inp)
        # notional = 20 * 100 = 2000; fee = 2000 * 0.001 * 2 = 4
        assert result.fee_estimate == Decimal("4")

    def test_market_type_is_spot(self):
        inp = make_spot_long()
        result = SpotSizer().calculate(inp)
        assert result.market_type == MarketType.SPOT

    def test_side_is_long(self):
        inp = make_spot_long()
        result = SpotSizer().calculate(inp)
        assert result.side == TradeSide.LONG

    def test_reward_risk_ratio_none_without_take_profit(self):
        inp = make_spot_long()
        result = SpotSizer().calculate(inp)
        assert result.reward_risk_ratio is None

    def test_spot_sizer_ignores_provided_leverage(self):
        """SpotSizer must force leverage=1 regardless of SizingInput.leverage."""
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("100"),
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
            market_type=MarketType.SPOT,
            leverage=Decimal("10"),  # caller passes 10x — should be ignored
            fee_rate=Decimal("0"),
        )
        result = SpotSizer().calculate(inp)
        # margin_required == notional / 1 (not notional / 10)
        assert result.margin_required == result.notional_value


class TestSpotShort:
    """SpotSizer SHORT trades."""

    def test_basic_short_position_size(self):
        """$10,000 equity × 1% risk = $100 risk. Stop $5 above → 20 units."""
        inp = make_spot_short(equity="10000", risk_pct="1", entry="100", stop="105")
        result = SpotSizer().calculate(inp)
        # risk = 100; distance = 5 → size = 20
        assert result.position_size == Decimal("20")

    def test_short_stop_distance_percent(self):
        """Stop $5 above $100 entry = 5% distance."""
        inp = make_spot_short(entry="100", stop="105")
        result = SpotSizer().calculate(inp)
        assert result.stop_distance_percent == Decimal("5")

    def test_short_notional_value(self):
        inp = make_spot_short(equity="10000", risk_pct="1", entry="100", stop="105")
        result = SpotSizer().calculate(inp)
        assert result.notional_value == Decimal("2000")

    def test_side_is_short(self):
        inp = make_spot_short()
        result = SpotSizer().calculate(inp)
        assert result.side == TradeSide.SHORT

    def test_market_type_is_spot_for_short(self):
        inp = make_spot_short()
        result = SpotSizer().calculate(inp)
        assert result.market_type == MarketType.SPOT


# ===========================================================================
# Section 2 — Normal Cases: PERPETUAL (leveraged)
# ===========================================================================


class TestPerpetualLong:
    """PerpetualSizer LONG — margin_required changes with leverage."""

    def test_2x_leverage_long_position_size(self):
        """Position size should be the same regardless of leverage (risk-based)."""
        inp = make_perp_long(equity="10000", risk_pct="1", entry="100", stop="95", leverage="2")
        result = PerpetualSizer().calculate(inp)
        assert result.position_size == Decimal("20")

    def test_2x_leverage_margin_required(self):
        """With 2x leverage, margin_required = notional / 2."""
        inp = make_perp_long(equity="10000", risk_pct="1", entry="100", stop="95", leverage="2")
        result = PerpetualSizer().calculate(inp)
        # position_size=20, entry=100 → notional=2000; margin=2000/2=1000
        assert result.margin_required == Decimal("1000")

    def test_5x_leverage_margin_required(self):
        """With 5x leverage, margin_required = notional / 5."""
        inp = make_perp_long(equity="10000", risk_pct="1", entry="100", stop="95", leverage="5")
        result = PerpetualSizer().calculate(inp)
        # notional=2000; margin=2000/5=400
        assert result.margin_required == Decimal("400")

    def test_10x_leverage_margin_required(self):
        """With 10x leverage, margin_required = notional / 10."""
        inp = make_perp_long(equity="10000", risk_pct="1", entry="100", stop="95", leverage="10")
        result = PerpetualSizer().calculate(inp)
        assert result.margin_required == Decimal("200")

    def test_market_type_is_perpetual(self):
        inp = make_perp_long()
        result = PerpetualSizer().calculate(inp)
        assert result.market_type == MarketType.PERPETUAL

    def test_perp_fee_estimate_with_rate(self):
        """fee = notional * fee_rate * 2; same formula as spot."""
        inp = make_perp_long(
            equity="10000", risk_pct="1", entry="100", stop="95",
            leverage="5", fee_rate="0.0005"
        )
        result = PerpetualSizer().calculate(inp)
        # notional=2000; fee=2000*0.0005*2=2
        assert result.fee_estimate == Decimal("2")


class TestPerpetualShort:
    """PerpetualSizer SHORT trades."""

    def test_5x_leverage_short_position_size(self):
        inp = make_perp_short(equity="10000", risk_pct="1", entry="100", stop="105", leverage="5")
        result = PerpetualSizer().calculate(inp)
        assert result.position_size == Decimal("20")

    def test_5x_leverage_short_margin_required(self):
        inp = make_perp_short(equity="10000", risk_pct="1", entry="100", stop="105", leverage="5")
        result = PerpetualSizer().calculate(inp)
        assert result.margin_required == Decimal("400")

    def test_side_is_short_perp(self):
        inp = make_perp_short()
        result = PerpetualSizer().calculate(inp)
        assert result.side == TradeSide.SHORT


# ===========================================================================
# Section 3 — Input Validation (errors must be raised)
# ===========================================================================


class TestValidationErrors:
    """_validate_input must raise ValueError for every invalid combination."""

    # --- account_equity ---

    def test_zero_equity_raises(self):
        inp = make_spot_long(equity="0")
        with pytest.raises(ValueError, match="account_equity"):
            SpotSizer().calculate(inp)

    def test_negative_equity_raises(self):
        inp = make_spot_long(equity="-1000")
        with pytest.raises(ValueError, match="account_equity"):
            SpotSizer().calculate(inp)

    # --- risk_percent ---

    def test_zero_risk_percent_raises(self):
        inp = make_spot_long(risk_pct="0")
        with pytest.raises(ValueError, match="risk_percent"):
            SpotSizer().calculate(inp)

    def test_negative_risk_percent_raises(self):
        inp = make_spot_long(risk_pct="-1")
        with pytest.raises(ValueError, match="risk_percent"):
            SpotSizer().calculate(inp)

    def test_risk_percent_above_100_raises(self):
        """risk_percent > 100 makes no financial sense and must be rejected."""
        inp = make_spot_long(risk_pct="101")
        with pytest.raises(ValueError, match="risk_percent"):
            SpotSizer().calculate(inp)

    def test_risk_percent_exactly_100_raises_margin_guard(self):
        """100% risk with 5% stop → 20x notional → exceeds equity → margin guard fires."""
        inp = make_spot_long(equity="10000", risk_pct="100", entry="100", stop="95")
        with pytest.raises(ValueError, match="margin.*exceeds.*equity"):
            SpotSizer().calculate(inp)

    def test_risk_percent_exactly_100_with_very_wide_stop(self):
        """100% risk with stop at $1 → distance=$99, size≈101.01, notional≈$10101 > equity.
        Even 100% risk on spot almost always hits the margin guard.
        Verify it does with a moderately wide stop too."""
        inp = make_spot_long(equity="10000", risk_pct="100", entry="100", stop="50")
        with pytest.raises(ValueError, match="margin.*exceeds.*equity"):
            SpotSizer().calculate(inp)

    # --- entry_price ---

    def test_zero_entry_price_raises(self):
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("0"),
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
        )
        with pytest.raises(ValueError, match="entry_price"):
            SpotSizer().calculate(inp)

    def test_negative_entry_price_raises(self):
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("-100"),
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
        )
        with pytest.raises(ValueError, match="entry_price"):
            SpotSizer().calculate(inp)

    # --- stop_price ---

    def test_zero_stop_price_raises(self):
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("100"),
            stop_price=Decimal("0"),
            side=TradeSide.LONG,
        )
        with pytest.raises(ValueError, match="stop_price"):
            SpotSizer().calculate(inp)

    # --- LONG stop >= entry ---

    def test_long_stop_equal_to_entry_raises(self):
        inp = make_spot_long(entry="100", stop="100")
        with pytest.raises(ValueError, match="LONG"):
            SpotSizer().calculate(inp)

    def test_long_stop_above_entry_raises(self):
        """For a LONG, stop above entry is logically inverted."""
        inp = make_spot_long(entry="100", stop="105")
        with pytest.raises(ValueError, match="LONG"):
            SpotSizer().calculate(inp)

    # --- SHORT stop <= entry ---

    def test_short_stop_equal_to_entry_raises(self):
        inp = make_spot_short(entry="100", stop="100")
        with pytest.raises(ValueError, match="SHORT"):
            SpotSizer().calculate(inp)

    def test_short_stop_below_entry_raises(self):
        """For a SHORT, stop below entry is logically inverted."""
        inp = make_spot_short(entry="100", stop="90")
        with pytest.raises(ValueError, match="SHORT"):
            SpotSizer().calculate(inp)

    # --- leverage ---

    def test_leverage_below_1_raises_in_perp_sizer(self):
        inp = make_perp_long(leverage="0.5")
        with pytest.raises(ValueError, match="leverage"):
            PerpetualSizer().calculate(inp)

    def test_leverage_zero_raises(self):
        inp = make_perp_long(leverage="0")
        with pytest.raises(ValueError, match="leverage"):
            PerpetualSizer().calculate(inp)

    def test_leverage_exactly_1_is_valid(self):
        """leverage=1 is the minimum valid value."""
        inp = make_perp_long(leverage="1")
        result = PerpetualSizer().calculate(inp)
        assert result.margin_required == result.notional_value

    # --- fee_rate ---

    def test_negative_fee_rate_raises(self):
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("100"),
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
            fee_rate=Decimal("-0.001"),
        )
        with pytest.raises(ValueError, match="fee_rate"):
            SpotSizer().calculate(inp)


# ===========================================================================
# Section 4 — Financial Precision
# ===========================================================================


class TestFinancialPrecision:
    """Decimal arithmetic must not produce floating-point errors."""

    def test_position_size_is_decimal_type(self):
        inp = make_spot_long()
        result = SpotSizer().calculate(inp)
        assert isinstance(result.position_size, Decimal)

    def test_risk_amount_is_decimal_type(self):
        inp = make_spot_long()
        result = SpotSizer().calculate(inp)
        assert isinstance(result.risk_amount, Decimal)

    def test_notional_value_is_decimal_type(self):
        inp = make_spot_long()
        result = SpotSizer().calculate(inp)
        assert isinstance(result.notional_value, Decimal)

    def test_no_floating_point_drift_with_thirds(self):
        """1/3 risk is a known floating-point hazard. Decimal must handle it cleanly."""
        inp = SizingInput(
            account_equity=Decimal("9000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("300"),
            stop_price=Decimal("290"),
            side=TradeSide.LONG,
        )
        result = SpotSizer().calculate(inp)
        # risk=90, distance=10, size=9 — no rounding involved
        assert result.position_size == Decimal("9")
        assert result.risk_amount == Decimal("90")

    def test_position_size_rounds_down_not_up(self):
        """position_size must always round DOWN — never expose more than intended risk."""
        # risk=100, entry=30, stop=29.7 → distance=0.3 → size=333.33333333
        # notional = 333.33333333 * 30 = 9999.99999990 < 10000 equity ✓
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("30"),
            stop_price=Decimal("29.7"),
            side=TradeSide.LONG,
        )
        result = SpotSizer().calculate(inp)
        assert result.position_size == Decimal("333.33333333")
        # Must be strictly less than exact division
        assert result.position_size < Decimal("100") / Decimal("0.3")

    def test_position_size_8_decimal_precision(self):
        """Crypto positions are sized to 8 decimal places (satoshi precision)."""
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("65000"),
            stop_price=Decimal("63000"),
            side=TradeSide.LONG,
        )
        result = SpotSizer().calculate(inp)
        # Verify that the result has exactly 8 decimal places
        decimal_str = str(result.position_size)
        if "." in decimal_str:
            decimal_places = len(decimal_str.split(".")[1])
            assert decimal_places <= 8

    def test_stop_distance_percent_is_exact_for_round_numbers(self):
        """5% stop distance on a round number must be exactly Decimal('5')."""
        inp = make_spot_long(entry="200", stop="190")
        result = SpotSizer().calculate(inp)
        # abs(200-190)/200 * 100 = 5
        assert result.stop_distance_percent == Decimal("5")

    def test_very_small_stop_distance_raises_margin_guard(self):
        """$1 stop on $10,000 asset → 100x notional → exceeds equity → margin guard fires."""
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("10000"),
            stop_price=Decimal("9999"),
            side=TradeSide.LONG,
        )
        with pytest.raises(ValueError, match="margin.*exceeds.*equity"):
            SpotSizer().calculate(inp)

    def test_small_stop_distance_with_sufficient_equity(self):
        """Tight stop on perpetual with leverage keeps margin within equity.
        risk=100, distance=1, size=100, notional=100*10000=$1M,
        leverage=125x → margin=$8000 < $10000 ✓"""
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("10000"),
            stop_price=Decimal("9999"),
            side=TradeSide.LONG,
            market_type=MarketType.PERPETUAL,
            leverage=Decimal("125"),
        )
        result = PerpetualSizer().calculate(inp)
        assert result.position_size == Decimal("100")
        assert result.stop_distance_percent == Decimal("0.01")


# ===========================================================================
# Section 5 — Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Boundary and unusual-but-valid scenarios."""

    def test_risk_percent_exactly_100_raises_when_notional_exceeds_equity(self):
        """100% risk with 10% stop → 10x notional → exceeds equity → margin guard fires."""
        inp = make_spot_long(equity="10000", risk_pct="100", entry="100", stop="90")
        with pytest.raises(ValueError, match="margin.*exceeds.*equity"):
            SpotSizer().calculate(inp)

    def test_risk_percent_exactly_100_on_perp_with_leverage(self):
        """100% risk on perpetual with leverage → margin stays within equity.
        risk=10000, entry=100, stop=90, distance=10, size=1000, notional=100000,
        with 20x leverage: margin=5000 < 10000 ✓"""
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("100"),
            entry_price=Decimal("100"),
            stop_price=Decimal("90"),
            side=TradeSide.LONG,
            market_type=MarketType.PERPETUAL,
            leverage=Decimal("20"),
        )
        result = PerpetualSizer().calculate(inp)
        assert result.risk_amount == Decimal("10000")
        assert result.position_size == Decimal("1000")
        assert result.margin_required == Decimal("5000")

    def test_very_large_position_no_overflow(self):
        """Large equity values must not cause numeric overflow."""
        inp = SizingInput(
            account_equity=Decimal("10000000"),  # $10M
            risk_percent=Decimal("1"),
            entry_price=Decimal("50000"),
            stop_price=Decimal("49000"),
            side=TradeSide.LONG,
        )
        result = SpotSizer().calculate(inp)
        assert result.position_size > 0
        assert result.notional_value > 0

    def test_very_small_equity(self):
        """Micro-account should still produce a valid result."""
        inp = SizingInput(
            account_equity=Decimal("10"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("100"),
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
        )
        result = SpotSizer().calculate(inp)
        # risk=0.10, distance=5 → size=0.02
        assert result.position_size == Decimal("0.02")

    def test_high_leverage_with_tight_stop(self):
        """100x leverage on perpetual — margin_required should be very small."""
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("100"),
            stop_price=Decimal("99"),
            side=TradeSide.LONG,
            market_type=MarketType.PERPETUAL,
            leverage=Decimal("100"),
        )
        result = PerpetualSizer().calculate(inp)
        # notional = 100 * 100 = 10000; margin = 10000 / 100 = 100
        assert result.margin_required == Decimal("100")

    def test_result_is_frozen_dataclass(self):
        """SizingResult must be immutable — no accidental mutation."""
        inp = make_spot_long()
        result = SpotSizer().calculate(inp)
        with pytest.raises((AttributeError, TypeError)):
            result.position_size = Decimal("999")  # type: ignore[misc]

    def test_input_is_frozen_dataclass(self):
        """SizingInput must be immutable."""
        inp = make_spot_long()
        with pytest.raises((AttributeError, TypeError)):
            inp.account_equity = Decimal("999")  # type: ignore[misc]


# ===========================================================================
# Section 6 — with_take_profit
# ===========================================================================


class TestWithTakeProfit:
    """with_take_profit must compute R:R correctly for LONG and SHORT."""

    def _base_long_result(self) -> tuple[SizingResult, Decimal]:
        entry = Decimal("100")
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=entry,
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
        )
        result = SpotSizer().calculate(inp)
        return result, entry

    def _base_short_result(self) -> tuple[SizingResult, Decimal]:
        entry = Decimal("100")
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=entry,
            stop_price=Decimal("105"),
            side=TradeSide.SHORT,
        )
        result = SpotSizer().calculate(inp)
        return result, entry

    def test_long_1_to_1_rr(self):
        """Entry 100, stop 95 (5pt risk). TP=105 (5pt reward) → R:R = 1.00."""
        result, entry = self._base_long_result()
        enriched = with_take_profit(result, Decimal("105"), entry)
        assert enriched.reward_risk_ratio == Decimal("1.00")

    def test_long_2_to_1_rr(self):
        """Entry 100, stop 95 (5pt risk). TP=110 (10pt reward) → R:R = 2.00."""
        result, entry = self._base_long_result()
        enriched = with_take_profit(result, Decimal("110"), entry)
        assert enriched.reward_risk_ratio == Decimal("2.00")

    def test_long_3_to_1_rr(self):
        result, entry = self._base_long_result()
        enriched = with_take_profit(result, Decimal("115"), entry)
        assert enriched.reward_risk_ratio == Decimal("3.00")

    def test_short_1_to_1_rr(self):
        """Entry 100, stop 105 (5pt risk). TP=95 (5pt reward) → R:R = 1.00."""
        result, entry = self._base_short_result()
        enriched = with_take_profit(result, Decimal("95"), entry)
        assert enriched.reward_risk_ratio == Decimal("1.00")

    def test_short_2_to_1_rr(self):
        """Entry 100, stop 105 (5pt risk). TP=90 (10pt reward) → R:R = 2.00."""
        result, entry = self._base_short_result()
        enriched = with_take_profit(result, Decimal("90"), entry)
        assert enriched.reward_risk_ratio == Decimal("2.00")

    def test_rr_rounds_down(self):
        """R:R must round DOWN to 2 decimal places (conservative)."""
        result, entry = self._base_long_result()
        # reward=7, risk=5 → 1.4 exactly → should be 1.40
        enriched = with_take_profit(result, Decimal("107"), entry)
        assert enriched.reward_risk_ratio == Decimal("1.40")

    def test_with_take_profit_preserves_other_fields(self):
        """with_take_profit must not mutate other fields in SizingResult."""
        result, entry = self._base_long_result()
        enriched = with_take_profit(result, Decimal("110"), entry)
        assert enriched.position_size == result.position_size
        assert enriched.risk_amount == result.risk_amount
        assert enriched.stop_distance_percent == result.stop_distance_percent
        assert enriched.notional_value == result.notional_value
        assert enriched.margin_required == result.margin_required
        assert enriched.fee_estimate == result.fee_estimate
        assert enriched.market_type == result.market_type
        assert enriched.side == result.side

    def test_with_take_profit_returns_new_object(self):
        """with_take_profit must return a new SizingResult, not mutate the original."""
        result, entry = self._base_long_result()
        enriched = with_take_profit(result, Decimal("110"), entry)
        assert enriched is not result
        assert result.reward_risk_ratio is None  # original unchanged

    def test_zero_take_profit_raises(self):
        result, entry = self._base_long_result()
        with pytest.raises(ValueError, match="take_profit_price"):
            with_take_profit(result, Decimal("0"), entry)

    def test_negative_take_profit_raises(self):
        result, entry = self._base_long_result()
        with pytest.raises(ValueError, match="take_profit_price"):
            with_take_profit(result, Decimal("-10"), entry)

    def test_rr_is_decimal_type(self):
        result, entry = self._base_long_result()
        enriched = with_take_profit(result, Decimal("110"), entry)
        assert isinstance(enriched.reward_risk_ratio, Decimal)


# ===========================================================================
# Section 7 — calculate_position dispatch
# ===========================================================================


class TestCalculatePositionDispatch:
    """calculate_position must dispatch to the correct sizer by market_type."""

    def test_dispatches_to_spot_sizer_for_spot(self):
        inp = make_spot_long()
        result = calculate_position(inp)
        assert result.market_type == MarketType.SPOT

    def test_dispatches_to_perpetual_sizer_for_perpetual(self):
        inp = make_perp_long()
        result = calculate_position(inp)
        assert result.market_type == MarketType.PERPETUAL

    def test_spot_dispatch_margin_equals_notional(self):
        """Via dispatch, SPOT market → leverage forced to 1 → margin == notional."""
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("100"),
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
            market_type=MarketType.SPOT,
            leverage=Decimal("5"),  # will be overridden by SpotSizer
        )
        result = calculate_position(inp)
        assert result.margin_required == result.notional_value

    def test_perp_dispatch_uses_leverage(self):
        """Via dispatch, PERPETUAL market → leverage is applied."""
        inp = make_perp_long(leverage="5")
        result = calculate_position(inp)
        expected_margin = result.notional_value / Decimal("5")
        assert result.margin_required == expected_margin

    def test_dispatch_raises_validation_error(self):
        """calculate_position must propagate validation errors."""
        inp = make_spot_long(equity="-1")
        with pytest.raises(ValueError):
            calculate_position(inp)


# ===========================================================================
# Section 8 — Real-World Scenarios
# ===========================================================================


class TestRealWorldScenarios:
    """Production-like scenarios using realistic trading parameters."""

    def test_btc_usdt_long_spot_10k_equity_1pct_risk(self):
        """
        Scenario: BTC/USDT spot
        Equity: $10,000 | Risk: 1% | Entry: $65,000 | Stop: $63,000

        Expected:
          risk_amount = $100
          price_distance = $2,000
          position_size = 100 / 2000 = 0.05 BTC
          notional = 0.05 * 65,000 = $3,250
          margin_required = $3,250 (spot, leverage=1)
          stop_distance = 2000/65000 * 100 ≈ 3.07692307...%
        """
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("65000"),
            stop_price=Decimal("63000"),
            side=TradeSide.LONG,
            market_type=MarketType.SPOT,
        )
        result = calculate_position(inp)

        assert result.risk_amount == Decimal("100")
        assert result.position_size == Decimal("0.05")
        assert result.notional_value == Decimal("3250")
        assert result.margin_required == Decimal("3250")
        assert result.market_type == MarketType.SPOT
        assert result.side == TradeSide.LONG

        # stop_distance_percent = 2000/65000 * 100 ≈ 3.076923..., quantized to 4 decimals
        assert result.stop_distance_percent == Decimal("3.0769")

    def test_eth_usdt_short_perpetual_5x(self):
        """
        Scenario: ETH/USDT perpetual short
        Equity: $5,000 | Risk: 2% | Entry: $3,500 | Stop: $3,600 | Leverage: 5x

        Expected:
          risk_amount = $100
          price_distance = $100
          position_size = 100 / 100 = 1 ETH
          notional = 1 * 3500 = $3,500
          margin_required = 3500 / 5 = $700
          side = SHORT
        """
        inp = SizingInput(
            account_equity=Decimal("5000"),
            risk_percent=Decimal("2"),
            entry_price=Decimal("3500"),
            stop_price=Decimal("3600"),
            side=TradeSide.SHORT,
            market_type=MarketType.PERPETUAL,
            leverage=Decimal("5"),
        )
        result = calculate_position(inp)

        assert result.risk_amount == Decimal("100")
        assert result.position_size == Decimal("1")
        assert result.notional_value == Decimal("3500")
        assert result.margin_required == Decimal("700")
        assert result.side == TradeSide.SHORT
        assert result.market_type == MarketType.PERPETUAL

    def test_btc_long_with_take_profit_2_to_1(self):
        """
        BTC long: entry $65,000, stop $63,000 (risk=$2,000/BTC), TP $69,000 (reward=$4,000/BTC).
        R:R should be 2.00.
        """
        entry = Decimal("65000")
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=entry,
            stop_price=Decimal("63000"),
            side=TradeSide.LONG,
            market_type=MarketType.SPOT,
        )
        result = calculate_position(inp)
        enriched = with_take_profit(result, Decimal("69000"), entry)
        assert enriched.reward_risk_ratio == Decimal("2.00")

    def test_btc_long_with_fees_reduces_net_pnl(self):
        """
        Entry $65,000, position 0.05 BTC, fee_rate 0.1% (taker).
        fee_estimate = 0.05 * 65,000 * 0.001 * 2 = $6.50
        """
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("65000"),
            stop_price=Decimal("63000"),
            side=TradeSide.LONG,
            market_type=MarketType.SPOT,
            fee_rate=Decimal("0.001"),
        )
        result = calculate_position(inp)
        assert result.fee_estimate == Decimal("6.5")

    def test_tight_stop_large_position_crypto_raises_margin_guard(self):
        """
        $10,000 equity, 1% risk, BTC at $65,000 with only $100 stop.
        position = 1 BTC → notional = $65,000 >> equity → margin guard fires.
        """
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("65000"),
            stop_price=Decimal("64900"),
            side=TradeSide.LONG,
            market_type=MarketType.SPOT,
        )
        with pytest.raises(ValueError, match="margin.*exceeds.*equity"):
            calculate_position(inp)

    def test_tight_stop_crypto_ok_with_leverage(self):
        """Same scenario but on perpetual with leverage — margin fits within equity."""
        inp = SizingInput(
            account_equity=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("65000"),
            stop_price=Decimal("64900"),
            side=TradeSide.LONG,
            market_type=MarketType.PERPETUAL,
            leverage=Decimal("10"),
        )
        result = calculate_position(inp)
        assert result.position_size == Decimal("1")
        assert result.notional_value == Decimal("65000")
        assert result.margin_required == Decimal("6500")


# ===========================================================================
# Section 9 — Enum and SizingInput Defaults
# ===========================================================================


class TestSizingInputDefaults:
    """SizingInput default values must match documented contract."""

    def test_default_market_type_is_spot(self):
        inp = SizingInput(
            account_equity=Decimal("1000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("100"),
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
        )
        assert inp.market_type == MarketType.SPOT

    def test_default_leverage_is_one(self):
        inp = SizingInput(
            account_equity=Decimal("1000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("100"),
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
        )
        assert inp.leverage == Decimal("1")

    def test_default_fee_rate_is_zero(self):
        inp = SizingInput(
            account_equity=Decimal("1000"),
            risk_percent=Decimal("1"),
            entry_price=Decimal("100"),
            stop_price=Decimal("95"),
            side=TradeSide.LONG,
        )
        assert inp.fee_rate == Decimal("0")

    def test_trade_side_values(self):
        assert TradeSide.LONG == "long"
        assert TradeSide.SHORT == "short"

    def test_market_type_values(self):
        assert MarketType.SPOT == "spot"
        assert MarketType.PERPETUAL == "perpetual"
