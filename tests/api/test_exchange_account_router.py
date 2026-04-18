from __future__ import annotations

from collections.abc import Generator

import pytest
from cryptography.fernet import Fernet
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

from python.core.database import get_session
from services.api.config import settings
from services.api.main import app

TEST_KEY = Fernet.generate_key().decode()
_TEST_DB_URL = "sqlite:///file:test_exchange_accounts?mode=memory&cache=shared&uri=true"


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


def _create(client: TestClient, **overrides: object) -> tuple[int, dict]:
    payload = {
        "label": "Test Binance",
        "exchange_id": "binance",
        "api_key": "myapikey1234",
        "api_secret": "mysecret5678",
        "mode": "sandbox",
        **overrides,
    }
    resp = client.post("/api/exchange-accounts", json=payload)
    return resp.status_code, resp.json()


class TestCreate:
    def test_create_returns_201_with_hint(self, client: TestClient) -> None:
        status, data = _create(client)
        assert status == 201
        assert data["api_key_hint"] == "...1234"
        assert "api_key" not in data
        assert "api_secret" not in data
        assert "api_key_encrypted" not in data

    def test_create_no_plaintext_in_response(self, client: TestClient) -> None:
        status, data = _create(client, api_key="abcdefgh", api_secret="xyz99999")
        assert status == 201
        assert "abcdefgh" not in str(data)
        assert "xyz99999" not in str(data)

    def test_create_with_passphrase(self, client: TestClient) -> None:
        status, data = _create(client, passphrase="mypass")
        assert status == 201
        assert data["has_passphrase"] is True

    def test_create_without_passphrase(self, client: TestClient) -> None:
        status, data = _create(client)
        assert status == 201
        assert data["has_passphrase"] is False

    def test_invalid_mode_returns_422(self, client: TestClient) -> None:
        status, _ = _create(client, mode="invalid")
        assert status == 422


class TestList:
    def test_list_returns_active_accounts(self, client: TestClient) -> None:
        _create(client, label="Listed Account")
        status = client.get("/api/exchange-accounts").status_code
        assert status == 200

    def test_list_items_have_required_fields(self, client: TestClient) -> None:
        data = client.get("/api/exchange-accounts").json()
        assert isinstance(data, list)
        if data:
            item = data[0]
            for field in ("id", "label", "exchange_id", "mode", "is_default", "is_active", "api_key_hint"):
                assert field in item


class TestGetById:
    def test_get_by_id_returns_account(self, client: TestClient) -> None:
        _, created = _create(client, label="GetById Test")
        account_id = created["id"]
        resp = client.get(f"/api/exchange-accounts/{account_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == account_id

    def test_get_nonexistent_returns_404(self, client: TestClient) -> None:
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/exchange-accounts/{fake_id}")
        assert resp.status_code == 404


class TestUpdate:
    def test_update_label(self, client: TestClient) -> None:
        _, created = _create(client, label="Original Label")
        account_id = created["id"]
        resp = client.put(
            f"/api/exchange-accounts/{account_id}",
            json={"label": "Updated Label"},
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "Updated Label"

    def test_update_credentials_re_encrypts(self, client: TestClient) -> None:
        _, created = _create(client, api_key="oldkey9999")
        account_id = created["id"]
        resp = client.put(
            f"/api/exchange-accounts/{account_id}",
            json={"api_key": "newkey5678"},
        )
        assert resp.status_code == 200
        assert resp.json()["api_key_hint"] == "...5678"


class TestDelete:
    def test_delete_soft_deletes(self, client: TestClient) -> None:
        _, created = _create(client, label="To Delete")
        account_id = created["id"]
        resp = client.delete(f"/api/exchange-accounts/{account_id}")
        assert resp.status_code == 204
        # Should now be gone from GET
        assert client.get(f"/api/exchange-accounts/{account_id}").status_code == 404

    def test_delete_nonexistent_returns_404(self, client: TestClient) -> None:
        fake_id = "00000000-0000-0000-0000-000000000001"
        resp = client.delete(f"/api/exchange-accounts/{fake_id}")
        assert resp.status_code == 404


class TestDefaultEnforcement:
    def test_setting_default_clears_others(self, client: TestClient) -> None:
        _, a1 = _create(client, label="Default A1", is_default=True)
        _, a2 = _create(client, label="Default A2", is_default=True)
        # a1 should no longer be default
        resp = client.get(f"/api/exchange-accounts/{a1['id']}")
        assert resp.json()["is_default"] is False
        # a2 should be default
        resp2 = client.get(f"/api/exchange-accounts/{a2['id']}")
        assert resp2.json()["is_default"] is True


class TestSupportedExchanges:
    def test_supported_exchanges_returns_list(self, client: TestClient) -> None:
        resp = client.get("/api/exchange-accounts/supported-exchanges")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert all(isinstance(x, str) for x in data)
        assert "binance" in data
