from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import ccxt
from fastapi import APIRouter, Depends, HTTPException
from typing import Self

from pydantic import BaseModel, field_validator, model_validator
from sqlmodel import Session, select

from python.core.crypto import decrypt, encrypt
from python.core.database import get_session
from python.core.logging_config import get_logger
from python.core.models import ExchangeAccount

logger = get_logger(__name__)
router = APIRouter()


class CreateExchangeAccountRequest(BaseModel):
    label: str
    exchange_id: str
    api_key: str
    api_secret: str
    passphrase: str | None = None
    mode: str = "sandbox"
    is_default: bool = False

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, v: str) -> str:
        if v not in ("sandbox", "live"):
            raise ValueError("mode must be 'sandbox' or 'live'")
        return v

    @field_validator("exchange_id")
    @classmethod
    def _normalize_exchange_id(cls, v: str) -> str:
        return v.strip().lower()

    @model_validator(mode="after")
    def _validate_hyperliquid(self) -> Self:
        if self.exchange_id == "hyperliquid" and self.passphrase:
            raise ValueError("Hyperliquid uses wallet-based auth and does not accept a passphrase")
        return self


class UpdateExchangeAccountRequest(BaseModel):
    label: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    passphrase: str | None = None
    mode: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, v: str | None) -> str | None:
        if v is not None and v not in ("sandbox", "live"):
            raise ValueError("mode must be 'sandbox' or 'live'")
        return v


class ExchangeAccountResponse(BaseModel):
    id: str
    label: str
    exchange_id: str
    mode: str
    is_default: bool
    is_active: bool
    has_passphrase: bool
    api_key_hint: str
    created_at: str
    updated_at: str


def _to_response(account: ExchangeAccount) -> ExchangeAccountResponse:
    try:
        decrypted_key = decrypt(account.api_key_encrypted)
        hint = f"...{decrypted_key[-4:]}" if len(decrypted_key) >= 4 else "..."
    except Exception:
        hint = "...****"
    return ExchangeAccountResponse(
        id=str(account.id),
        label=account.label,
        exchange_id=account.exchange_id,
        mode=account.mode,
        is_default=account.is_default,
        is_active=account.is_active,
        has_passphrase=account.passphrase_encrypted is not None,
        api_key_hint=hint,
        created_at=account.created_at.isoformat(),
        updated_at=account.updated_at.isoformat(),
    )


def _clear_default(session: Session, exclude_id: UUID | None = None) -> None:
    stmt = select(ExchangeAccount).where(ExchangeAccount.is_default == True)  # noqa: E712
    if exclude_id:
        stmt = stmt.where(ExchangeAccount.id != exclude_id)
    for account in session.exec(stmt).all():
        account.is_default = False
        account.updated_at = datetime.now(timezone.utc)
        session.add(account)


@router.get("/api/exchange-accounts/supported-exchanges")
def get_supported_exchanges() -> list[str]:
    return sorted(ccxt.exchanges)


@router.get("/api/exchange-accounts")
def list_exchange_accounts(
    session: Session = Depends(get_session),
) -> list[ExchangeAccountResponse]:
    stmt = select(ExchangeAccount).where(ExchangeAccount.is_active == True)  # noqa: E712
    accounts = session.exec(stmt).all()
    return [_to_response(a) for a in accounts]


@router.get("/api/exchange-accounts/{account_id}")
def get_exchange_account(
    account_id: UUID,
    session: Session = Depends(get_session),
) -> ExchangeAccountResponse:
    account = session.get(ExchangeAccount, account_id)
    if not account or not account.is_active:
        raise HTTPException(status_code=404, detail="Exchange account not found")
    return _to_response(account)


@router.post("/api/exchange-accounts", status_code=201)
def create_exchange_account(
    body: CreateExchangeAccountRequest,
    session: Session = Depends(get_session),
) -> ExchangeAccountResponse:
    if body.is_default:
        _clear_default(session)

    account = ExchangeAccount(
        label=body.label,
        exchange_id=body.exchange_id,
        api_key_encrypted=encrypt(body.api_key),
        api_secret_encrypted=encrypt(body.api_secret),
        passphrase_encrypted=encrypt(body.passphrase) if body.passphrase else None,
        mode=body.mode,
        is_default=body.is_default,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    logger.info("exchange_account_created", id=str(account.id), label=account.label)
    return _to_response(account)


@router.put("/api/exchange-accounts/{account_id}")
def update_exchange_account(
    account_id: UUID,
    body: UpdateExchangeAccountRequest,
    session: Session = Depends(get_session),
) -> ExchangeAccountResponse:
    account = session.get(ExchangeAccount, account_id)
    if not account or not account.is_active:
        raise HTTPException(status_code=404, detail="Exchange account not found")

    if body.label is not None:
        account.label = body.label
    if body.api_key is not None:
        account.api_key_encrypted = encrypt(body.api_key)
    if body.api_secret is not None:
        account.api_secret_encrypted = encrypt(body.api_secret)
    if body.passphrase is not None:
        account.passphrase_encrypted = encrypt(body.passphrase)
    if body.mode is not None:
        account.mode = body.mode
    if body.is_active is not None:
        account.is_active = body.is_active
    if body.is_default is not None:
        if body.is_default:
            _clear_default(session, exclude_id=account_id)
        account.is_default = body.is_default

    account.updated_at = datetime.now(timezone.utc)
    session.add(account)
    session.commit()
    session.refresh(account)
    return _to_response(account)


@router.delete("/api/exchange-accounts/{account_id}", status_code=204)
def delete_exchange_account(
    account_id: UUID,
    session: Session = Depends(get_session),
) -> None:
    account = session.get(ExchangeAccount, account_id)
    if not account or not account.is_active:
        raise HTTPException(status_code=404, detail="Exchange account not found")

    account.is_active = False
    account.is_default = False
    account.updated_at = datetime.now(timezone.utc)
    session.add(account)
    session.commit()
