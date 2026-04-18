"""Integration tests for the order router.

The exchange_service functions are mocked so no real exchange calls are made.
The DB session is overridden to use an in-memory SQLite database.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

from python.core.crypto import encrypt
from python.core.database import get_session
from python.core.models import ExchangeAccount
from python.domain.exchange import (
    AccountBalance,
    Balance,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)
from services.api.config import settings
from services.api.main import app

TEST_KEY = Fernet.generate_key().decode()
_TEST_DB_URL = "sqlite:///file:test_orders?mode=memory&cache=shared&uri=true"

_NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_order_result(
    exchange_order_id: str = "ord-001",
    symbol: str = "BTC/USDT",
    side: OrderSide = OrderSide.BUY,
    order_type: OrderType = OrderType.MARKET,
    status: OrderStatus = OrderStatus.FILLED,
    quantity: Decimal = Decimal("0.001"),
    filled_quantity: Decimal = Decimal("0.001"),
    price: Decimal | None = None,
    average_fill_price: Decimal | None = Decimal("50000"),
    fee: Decimal = Decimal("0.0001"),
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


def _make_balance() -> AccountBalance:
    return AccountBalance(
        balances=(
            Balance(currency="USDT", total=Decimal("10000"), free=Decimal("9000"), used=Decimal("1000")),
            Balance(currency="BTC", total=Decimal("0.1"), free=Decimal("0.1"), used=Decimal("0")),
        ),
        timestamp=_NOW,
    )


def _make_position(symbol: str = "BTC/USDT") -> Position:
    return Position(
        symbol=symbol,
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        entry_price=Decimal("50000"),
        mark_price=Decimal("51000"),
        unrealized_pnl=Decimal("1"),
        leverage=Decimal("1"),
        liquidation_price=None,
        timestamp=_NOW,
    )


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

    original_key = settings.fernet_key
    settings.fernet_key = TEST_KEY
    app.dependency_overrides[get_session] = override_session

    try:
        yield TestClient(app)
    finally:
        settings.fernet_key = original_key
        app.dependency_overrides.pop(get_session, None)
        SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def account_id(client: TestClient) -> str:
    """Create an ExchangeAccount in the test DB and return its UUID."""
    payload = {
        "label": "Test Binance",
        "exchange_id": "binance",
        "api_key": "testapikey1234",
        "api_secret": "testsecret5678",
        "mode": "sandbox",
    }
    resp = client.post("/api/exchange-accounts", json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


class TestPlaceOrder:
    def test_place_market_order_returns_201(self, client: TestClient, account_id: str) -> None:
        result = _make_order_result()
        with patch(
            "services.api.routers.order_router.svc_place_order",
            new_callable=AsyncMock,
            return_value=result,
        ):
            resp = client.post(
                "/api/orders",
                json={
                    "account_id": account_id,
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "order_type": "market",
                    "quantity": "0.001",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["exchange_order_id"] == "ord-001"
        assert data["status"] == "filled"
        assert data["side"] == "buy"

    def test_place_limit_order_includes_price(self, client: TestClient, account_id: str) -> None:
        result = _make_order_result(
            order_type=OrderType.LIMIT,
            price=Decimal("48000"),
            status=OrderStatus.OPEN,
        )
        with patch(
            "services.api.routers.order_router.svc_place_order",
            new_callable=AsyncMock,
            return_value=result,
        ):
            resp = client.post(
                "/api/orders",
                json={
                    "account_id": account_id,
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "order_type": "limit",
                    "quantity": "0.001",
                    "price": "48000",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["order_type"] == "limit"
        assert data["price"] == "48000"

    def test_decimal_no_scientific_notation(self, client: TestClient, account_id: str) -> None:
        """Ensure very small Decimal values are serialised as fixed-point."""
        result = _make_order_result(
            quantity=Decimal("0.00000001"),
            fee=Decimal("0E-8"),
        )
        with patch(
            "services.api.routers.order_router.svc_place_order",
            new_callable=AsyncMock,
            return_value=result,
        ):
            resp = client.post(
                "/api/orders",
                json={
                    "account_id": account_id,
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "order_type": "market",
                    "quantity": "0.00000001",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert "E" not in data["quantity"]
        assert "E" not in data["fee"]

    def test_invalid_account_returns_404(self, client: TestClient) -> None:
        fake_id = str(uuid4())
        with patch(
            "services.api.routers.order_router.svc_place_order",
            new_callable=AsyncMock,
            side_effect=ValueError("Exchange account not found"),
        ):
            resp = client.post(
                "/api/orders",
                json={
                    "account_id": fake_id,
                    "symbol": "BTC/USDT",
                    "side": "buy",
                    "order_type": "market",
                    "quantity": "0.001",
                },
            )
        assert resp.status_code == 404

    def test_invalid_side_returns_422(self, client: TestClient, account_id: str) -> None:
        resp = client.post(
            "/api/orders",
            json={
                "account_id": account_id,
                "symbol": "BTC/USDT",
                "side": "invalid_side",
                "order_type": "market",
                "quantity": "0.001",
            },
        )
        assert resp.status_code == 422


class TestCancelOrder:
    def test_cancel_returns_200(self, client: TestClient, account_id: str) -> None:
        result = _make_order_result(status=OrderStatus.CANCELLED)
        with patch(
            "services.api.routers.order_router.svc_cancel_order",
            new_callable=AsyncMock,
            return_value=result,
        ):
            resp = client.delete(
                "/api/orders/ord-001",
                params={"account_id": account_id, "symbol": "BTC/USDT"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancel_missing_params_returns_422(self, client: TestClient) -> None:
        resp = client.delete("/api/orders/ord-001")
        assert resp.status_code == 422

    def test_cancel_account_not_found_returns_404(self, client: TestClient) -> None:
        fake_id = str(uuid4())
        with patch(
            "services.api.routers.order_router.svc_cancel_order",
            new_callable=AsyncMock,
            side_effect=ValueError("Exchange account not found"),
        ):
            resp = client.delete(
                "/api/orders/ord-001",
                params={"account_id": fake_id, "symbol": "BTC/USDT"},
            )
        assert resp.status_code == 404


class TestGetOrder:
    def test_get_order_returns_200(self, client: TestClient, account_id: str) -> None:
        result = _make_order_result()
        with patch(
            "services.api.routers.order_router.svc_get_order",
            new_callable=AsyncMock,
            return_value=result,
        ):
            resp = client.get(
                "/api/orders/ord-001",
                params={"account_id": account_id, "symbol": "BTC/USDT"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exchange_order_id"] == "ord-001"
        assert data["symbol"] == "BTC/USDT"

    def test_get_order_missing_symbol_returns_422(self, client: TestClient, account_id: str) -> None:
        resp = client.get(
            "/api/orders/ord-001",
            params={"account_id": account_id},
        )
        assert resp.status_code == 422


class TestListOpenOrders:
    def test_list_returns_200(self, client: TestClient, account_id: str) -> None:
        orders = [_make_order_result("ord-001"), _make_order_result("ord-002")]
        with patch(
            "services.api.routers.order_router.svc_get_open_orders",
            new_callable=AsyncMock,
            return_value=orders,
        ):
            resp = client.get("/api/orders", params={"account_id": account_id})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_with_symbol_filter(self, client: TestClient, account_id: str) -> None:
        with patch(
            "services.api.routers.order_router.svc_get_open_orders",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_svc:
            resp = client.get(
                "/api/orders",
                params={"account_id": account_id, "symbol": "ETH/USDT"},
            )
        assert resp.status_code == 200
        # Verify symbol was forwarded to the service
        call_kwargs = mock_svc.call_args
        assert call_kwargs.args[1] == "ETH/USDT" or (
            call_kwargs.kwargs.get("symbol") == "ETH/USDT"
        )

    def test_list_missing_account_id_returns_422(self, client: TestClient) -> None:
        resp = client.get("/api/orders")
        assert resp.status_code == 422


class TestGetBalance:
    def test_get_balance_returns_200(self, client: TestClient, account_id: str) -> None:
        balance = _make_balance()
        with patch(
            "services.api.routers.order_router.svc_get_balance",
            new_callable=AsyncMock,
            return_value=balance,
        ):
            resp = client.get("/api/orders/balance", params={"account_id": account_id})
        assert resp.status_code == 200
        data = resp.json()
        assert "balances" in data
        assert "timestamp" in data
        currencies = {b["currency"] for b in data["balances"]}
        assert "USDT" in currencies
        assert "BTC" in currencies

    def test_balance_decimals_are_fixed_point(self, client: TestClient, account_id: str) -> None:
        balance = AccountBalance(
            balances=(Balance(currency="BTC", total=Decimal("0E-8"), free=Decimal("0"), used=Decimal("0")),),
            timestamp=_NOW,
        )
        with patch(
            "services.api.routers.order_router.svc_get_balance",
            new_callable=AsyncMock,
            return_value=balance,
        ):
            resp = client.get("/api/orders/balance", params={"account_id": account_id})
        assert resp.status_code == 200
        item = resp.json()["balances"][0]
        assert "E" not in item["total"]

    def test_balance_account_not_found_returns_404(self, client: TestClient) -> None:
        fake_id = str(uuid4())
        with patch(
            "services.api.routers.order_router.svc_get_balance",
            new_callable=AsyncMock,
            side_effect=ValueError("Exchange account not found"),
        ):
            resp = client.get("/api/orders/balance", params={"account_id": fake_id})
        assert resp.status_code == 404


class TestGetPositions:
    def test_get_positions_returns_200(self, client: TestClient, account_id: str) -> None:
        positions = [_make_position("BTC/USDT"), _make_position("ETH/USDT")]
        with patch(
            "services.api.routers.order_router.svc_get_positions",
            new_callable=AsyncMock,
            return_value=positions,
        ):
            resp = client.get("/api/orders/positions", params={"account_id": account_id})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["symbol"] == "BTC/USDT"

    def test_positions_with_symbol_filter(self, client: TestClient, account_id: str) -> None:
        with patch(
            "services.api.routers.order_router.svc_get_positions",
            new_callable=AsyncMock,
            return_value=[_make_position("BTC/USDT")],
        ):
            resp = client.get(
                "/api/orders/positions",
                params={"account_id": account_id, "symbol": "BTC/USDT"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_positions_optional_fields_null(self, client: TestClient, account_id: str) -> None:
        pos = Position(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=Decimal("0.001"),
            entry_price=Decimal("50000"),
            mark_price=None,
            unrealized_pnl=None,
            leverage=Decimal("1"),
            liquidation_price=None,
            timestamp=_NOW,
        )
        with patch(
            "services.api.routers.order_router.svc_get_positions",
            new_callable=AsyncMock,
            return_value=[pos],
        ):
            resp = client.get("/api/orders/positions", params={"account_id": account_id})
        assert resp.status_code == 200
        item = resp.json()[0]
        assert item["mark_price"] is None
        assert item["unrealized_pnl"] is None
        assert item["liquidation_price"] is None

    def test_positions_account_not_found_returns_404(self, client: TestClient) -> None:
        fake_id = str(uuid4())
        with patch(
            "services.api.routers.order_router.svc_get_positions",
            new_callable=AsyncMock,
            side_effect=ValueError("Exchange account not found"),
        ):
            resp = client.get("/api/orders/positions", params={"account_id": fake_id})
        assert resp.status_code == 404
