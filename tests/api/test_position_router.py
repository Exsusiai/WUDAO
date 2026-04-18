"""Integration tests for POST /api/position/calculate.

Every assertion uses exact string comparison — this is a financial calculation
endpoint where rounding errors cause real monetary loss.

Exact expected values were captured from a live TestClient run so they reflect
the full serialization path: domain Decimal → str() → Pydantic response model
→ JSON response body.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from services.api.main import app


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> TestClient:
    """A single TestClient instance reused across the module.

    scope="module" is safe here because the endpoint is stateless — it has
    no side-effects and does not touch the database.
    """
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _post(client: TestClient, payload: dict) -> tuple[int, dict]:
    """POST to the calculate endpoint and return (status_code, body)."""
    resp = client.post("/api/position/calculate", json=payload)
    return resp.status_code, resp.json()


# ===========================================================================
# Happy-path tests
# ===========================================================================


class TestHappyPaths:
    """Successful 200 responses with exact field assertions."""

    def test_spot_long_calculate(self, client: TestClient) -> None:
        """Basic LONG spot trade.

        equity=10000, risk=1%, entry=100, stop=95 (distance=5)
        risk_amount = 100
        position_size = 100 / 5 = 20 units, quantized to 8 dp
        notional = 20 * 100 = 2000
        margin_required = 2000 / 1 (spot) = 2000
        """
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "95",
                "side": "long",
                "market_type": "spot",
            },
        )

        assert status == 200
        assert data["position_size"] == "20.00000000"
        assert data["risk_amount"] == "100"
        assert data["side"] == "long"
        assert data["market_type"] == "spot"
        assert data["stop_price"] == "95"

    def test_spot_short_calculate(self, client: TestClient) -> None:
        """Basic SHORT spot trade.

        equity=10000, risk=1%, entry=100, stop=105 (distance=5)
        position_size = 100 / 5 = 20 units
        """
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "105",
                "side": "short",
            },
        )

        assert status == 200
        assert data["position_size"] == "20.00000000"
        assert data["side"] == "short"

    def test_perpetual_with_leverage(self, client: TestClient) -> None:
        """Perpetual (leveraged) trade: leverage reduces margin_required.

        equity=10000, risk=1%, entry=100, stop=95, leverage=5
        position_size = 100 / 5 = 20 units
        notional = 20 * 100 = 2000
        margin_required = 2000 / 5 = 400
        """
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "95",
                "side": "long",
                "market_type": "perpetual",
                "leverage": "5",
            },
        )

        assert status == 200
        assert data["margin_required"] == "400.00000000"
        assert data["market_type"] == "perpetual"

    def test_with_take_profit(self, client: TestClient) -> None:
        """Take-profit enriches the response with reward_risk_ratio.

        entry=100, stop=95 (risk=5pt), TP=110 (reward=10pt) → R:R = 2.00
        """
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "95",
                "side": "long",
                "market_type": "spot",
                "take_profit_price": "110",
            },
        )

        assert status == 200
        assert data["reward_risk_ratio"] == "2.00"

    def test_without_take_profit_rr_is_null(self, client: TestClient) -> None:
        """No take_profit_price → reward_risk_ratio must be null in JSON."""
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "95",
                "side": "long",
                "market_type": "spot",
            },
        )

        assert status == 200
        assert data["reward_risk_ratio"] is None

    def test_default_market_type_is_spot(self, client: TestClient) -> None:
        """Omitting market_type must default to 'spot' in the response."""
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "95",
                "side": "long",
            },
        )

        assert status == 200
        assert data["market_type"] == "spot"

    def test_fee_estimate_with_rate(self, client: TestClient) -> None:
        """fee_estimate = notional * fee_rate * 2 (entry and exit legs).

        position_size=20, entry=100 → notional=2000
        fee = 2000 * 0.001 * 2 = 4.00000000000
        """
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "95",
                "side": "long",
                "market_type": "spot",
                "fee_rate": "0.001",
            },
        )

        assert status == 200
        assert data["fee_estimate"] == "4.00000000000"


# ===========================================================================
# Field-type tests
# ===========================================================================


class TestFieldTypes:
    """Verify the contract that all numeric fields are serialized as strings."""

    def test_decimal_fields_are_strings(self, client: TestClient) -> None:
        """Every numeric output field must be a JSON string, never a float/int.

        Returning floats risks silent precision loss in downstream consumers.
        """
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "95",
                "side": "long",
                "market_type": "spot",
            },
        )

        assert status == 200

        decimal_fields = [
            "position_size",
            "risk_amount",
            "stop_distance_percent",
            "stop_price",
            "notional_value",
            "margin_required",
            "fee_estimate",
        ]
        for field in decimal_fields:
            assert isinstance(data[field], str), (
                f"Field '{field}' must be a string, got {type(data[field]).__name__} "
                f"(value={data[field]!r})"
            )


# ===========================================================================
# Error / 422 tests
# ===========================================================================


class TestValidationErrors:
    """Invalid inputs must produce 422 responses with informative detail text."""

    def test_wrong_stop_direction_returns_422(self, client: TestClient) -> None:
        """LONG trade with stop above entry is logically invalid.

        The domain error message must reference 'LONG' so the client can
        display a meaningful error to the trader.
        """
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "105",
                "side": "long",
            },
        )

        assert status == 422
        assert "LONG" in data["detail"]

    def test_margin_exceeds_equity_returns_422(self, client: TestClient) -> None:
        """Very tight stop on spot causes position size to exceed equity.

        equity=10000, risk=1%, entry=65000, stop=64900 (distance=100)
        position_size = 100 / 100 = 1 BTC
        notional = 1 * 65000 = 65000 >> 10000 equity → domain raises
        """
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "65000",
                "stop_price": "64900",
                "side": "long",
                "market_type": "spot",
            },
        )

        assert status == 422
        # The detail must mention 'margin' so the trader understands the cause
        assert "margin" in data["detail"].lower()

    def test_wrong_tp_direction_returns_422(self, client: TestClient) -> None:
        """LONG trade with TP below entry price is logically invalid."""
        status, data = _post(
            client,
            {
                "account_equity": "10000",
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "95",
                "side": "long",
                "take_profit_price": "90",
            },
        )

        assert status == 422
        assert "LONG" in data["detail"]

    def test_missing_required_field(self, client: TestClient) -> None:
        """Omitting account_equity must trigger Pydantic's required-field check.

        FastAPI returns 422 with a list of validation errors from Pydantic.
        """
        status, data = _post(
            client,
            {
                "risk_percent": "1",
                "entry_price": "100",
                "stop_price": "95",
                "side": "long",
            },
        )

        assert status == 422
        # Pydantic validation errors are returned as a list under "detail"
        assert isinstance(data["detail"], list)
        error_locs = [err["loc"] for err in data["detail"]]
        assert any("account_equity" in loc for loc in error_locs)
