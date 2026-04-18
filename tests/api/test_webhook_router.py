"""Tests for TradingView webhook endpoint.

Exchange service is mocked — no real exchange calls. DB session uses in-memory SQLite.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

from python.core.database import get_session
from python.domain.exchange import OrderResult, OrderSide, OrderStatus, OrderType
from services.api.config import settings
from services.api.main import app

_TEST_DB_URL = "sqlite:///file:test_webhook?mode=memory&cache=shared&uri=true"
_NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
_WEBHOOK_SECRET = "test-secret-abc"
_DEFAULT_ACCOUNT_ID = str(uuid4())


def _make_order_result(
    exchange_order_id: str = "wh-ord-001",
    symbol: str = "BTC/USDT",
    side: OrderSide = OrderSide.BUY,
    order_type: OrderType = OrderType.MARKET,
    status: OrderStatus = OrderStatus.FILLED,
    quantity: Decimal = Decimal("0.05"),
    filled_quantity: Decimal = Decimal("0.05"),
    price: Decimal | None = None,
    average_fill_price: Decimal | None = Decimal("65000"),
    fee: Decimal = Decimal("0.001"),
    fee_currency: str = "USDT",
) -> OrderResult:
    return OrderResult(
        exchange_order_id=exchange_order_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        status=status,
        quantity=quantity,
        filled_quantity=filled_quantity,
        price=price,
        average_fill_price=average_fill_price,
        fee=fee,
        fee_currency=fee_currency,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _webhook_payload(**overrides: object) -> dict:
    base: dict = {
        "secret": _WEBHOOK_SECRET,
        "symbol": "BTC/USDT",
        "side": "buy",
        "order_type": "market",
        "quantity": "0.05",
        "price": None,
        "stop_loss": "63000",
        "take_profit": "72000",
        "account_id": None,
    }
    base.update(overrides)
    return base


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    import python.core.models  # noqa: F401 — registers SQLModel metadata

    engine = create_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False, "uri": True},
    )
    SQLModel.metadata.create_all(engine)

    def override_session() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    original_secret = settings.webhook_secret
    original_default = settings.webhook_default_account_id
    settings.webhook_secret = _WEBHOOK_SECRET
    settings.webhook_default_account_id = _DEFAULT_ACCOUNT_ID
    app.dependency_overrides[get_session] = override_session

    try:
        yield TestClient(app)
    finally:
        settings.webhook_secret = original_secret
        settings.webhook_default_account_id = original_default
        app.dependency_overrides.pop(get_session, None)
        SQLModel.metadata.drop_all(engine)


class TestWebhookAuth:
    def test_wrong_secret_returns_401(self, client: TestClient) -> None:
        result = _make_order_result()
        with patch(
            "services.api.routers.webhook_router.svc_place_order",
            new_callable=AsyncMock,
            return_value=result,
        ):
            resp = client.post("/api/webhook/tradingview", json=_webhook_payload(secret="wrong-secret"))
        assert resp.status_code == 401

    def test_missing_secret_field_returns_422(self, client: TestClient) -> None:
        payload = _webhook_payload()
        del payload["secret"]
        resp = client.post("/api/webhook/tradingview", json=payload)
        assert resp.status_code == 422


class TestWebhookAccountResolution:
    def test_no_account_id_and_no_default_returns_422(self, client: TestClient) -> None:
        original = settings.webhook_default_account_id
        settings.webhook_default_account_id = ""
        try:
            result = _make_order_result()
            with patch(
                "services.api.routers.webhook_router.svc_place_order",
                new_callable=AsyncMock,
                return_value=result,
            ):
                resp = client.post("/api/webhook/tradingview", json=_webhook_payload(account_id=None))
        finally:
            settings.webhook_default_account_id = original
        assert resp.status_code == 422

    def test_payload_account_id_overrides_default(self, client: TestClient) -> None:
        explicit_id = str(uuid4())
        captured: list[UUID] = []

        async def mock_place(account_id: UUID, request: object, session: object) -> OrderResult:
            captured.append(account_id)
            return _make_order_result()

        with patch("services.api.routers.webhook_router.svc_place_order", side_effect=mock_place):
            resp = client.post(
                "/api/webhook/tradingview",
                json=_webhook_payload(account_id=explicit_id),
            )
        assert resp.status_code == 201
        assert str(captured[0]) == explicit_id

    def test_default_account_id_used_when_payload_null(self, client: TestClient) -> None:
        captured: list[UUID] = []

        async def mock_place(account_id: UUID, request: object, session: object) -> OrderResult:
            captured.append(account_id)
            return _make_order_result()

        with patch("services.api.routers.webhook_router.svc_place_order", side_effect=mock_place):
            resp = client.post(
                "/api/webhook/tradingview",
                json=_webhook_payload(account_id=None),
            )
        assert resp.status_code == 201
        assert str(captured[0]) == _DEFAULT_ACCOUNT_ID


class TestWebhookSuccess:
    def test_valid_webhook_returns_201_and_order_result(self, client: TestClient) -> None:
        result = _make_order_result()
        with patch(
            "services.api.routers.webhook_router.svc_place_order",
            new_callable=AsyncMock,
            return_value=result,
        ):
            resp = client.post("/api/webhook/tradingview", json=_webhook_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert data["exchange_order_id"] == "wh-ord-001"
        assert data["symbol"] == "BTC/USDT"
        assert data["side"] == "buy"
        assert data["order_type"] == "market"
        assert data["status"] == "filled"
        assert data["quantity"] == "0.05"

    def test_decimal_fields_coerced_from_strings(self, client: TestClient) -> None:
        result = _make_order_result()
        with patch(
            "services.api.routers.webhook_router.svc_place_order",
            new_callable=AsyncMock,
            return_value=result,
        ) as mock_svc:
            resp = client.post(
                "/api/webhook/tradingview",
                json=_webhook_payload(quantity="0.123", stop_loss="60000.50", take_profit="75000.00"),
            )
        assert resp.status_code == 201
        called_request = mock_svc.call_args[0][1]
        assert called_request.quantity == Decimal("0.123")
        assert called_request.stop_loss == Decimal("60000.50")
        assert called_request.take_profit == Decimal("75000.00")


class TestWebhookErrors:
    def test_exchange_service_value_error_returns_404(self, client: TestClient) -> None:
        with patch(
            "services.api.routers.webhook_router.svc_place_order",
            new_callable=AsyncMock,
            side_effect=ValueError("Exchange account not found"),
        ):
            resp = client.post("/api/webhook/tradingview", json=_webhook_payload())
        assert resp.status_code == 404
        assert "Exchange account not found" in resp.json()["detail"]

    def test_unexpected_exception_returns_500(self, client: TestClient) -> None:
        with patch(
            "services.api.routers.webhook_router.svc_place_order",
            new_callable=AsyncMock,
            side_effect=RuntimeError("unexpected boom"),
        ):
            resp = client.post("/api/webhook/tradingview", json=_webhook_payload())
        assert resp.status_code == 500
