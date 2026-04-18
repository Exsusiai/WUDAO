"""Exchange service orchestration layer.

Single entry point for all exchange operations. Looks up an ExchangeAccount
from the database, decrypts credentials, creates an adapter, executes the
operation, and returns domain types.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlmodel import Session

from python.adapters.factory import create_exchange_adapter
from python.core.crypto import decrypt
from python.core.logging_config import get_logger
from python.core.models import ExchangeAccount
from python.domain.exchange import (
    AccountBalance,
    ExchangeMode,
    OrderRequest,
    OrderResult,
    Position,
)

logger = get_logger(__name__)


def _get_account(account_id: UUID, session: Session) -> ExchangeAccount:
    """Fetch an active ExchangeAccount or raise ValueError."""
    account = session.get(ExchangeAccount, account_id)
    if not account or not account.is_active:
        raise ValueError("Exchange account not found")
    return account


async def place_order(
    account_id: UUID,
    request: OrderRequest,
    session: Session,
) -> OrderResult:
    """Place an order on the exchange."""
    account = _get_account(account_id, session)
    api_key = decrypt(account.api_key_encrypted)
    api_secret = decrypt(account.api_secret_encrypted)
    passphrase = decrypt(account.passphrase_encrypted) if account.passphrase_encrypted else None
    mode = ExchangeMode(account.mode)

    adapter = create_exchange_adapter(
        exchange_id=account.exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        mode=mode,
        password=passphrase,
    )
    async with adapter:
        result = await adapter.place_order(request)

    logger.info(
        "order_placed",
        account_id=str(account_id),
        exchange_order_id=result.exchange_order_id,
        symbol=result.symbol,
        side=result.side.value,
        order_type=result.order_type.value,
        status=result.status.value,
    )
    return result


async def cancel_order(
    account_id: UUID,
    exchange_order_id: str,
    symbol: str,
    session: Session,
) -> OrderResult:
    """Cancel an open order on the exchange."""
    account = _get_account(account_id, session)
    api_key = decrypt(account.api_key_encrypted)
    api_secret = decrypt(account.api_secret_encrypted)
    passphrase = decrypt(account.passphrase_encrypted) if account.passphrase_encrypted else None
    mode = ExchangeMode(account.mode)

    adapter = create_exchange_adapter(
        exchange_id=account.exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        mode=mode,
        password=passphrase,
    )
    async with adapter:
        result = await adapter.cancel_order(exchange_order_id, symbol)

    logger.info(
        "order_cancelled",
        account_id=str(account_id),
        exchange_order_id=exchange_order_id,
        symbol=symbol,
    )
    return result


async def get_order(
    account_id: UUID,
    exchange_order_id: str,
    symbol: str,
    session: Session,
) -> OrderResult:
    """Fetch a single order from the exchange."""
    account = _get_account(account_id, session)
    api_key = decrypt(account.api_key_encrypted)
    api_secret = decrypt(account.api_secret_encrypted)
    passphrase = decrypt(account.passphrase_encrypted) if account.passphrase_encrypted else None
    mode = ExchangeMode(account.mode)

    adapter = create_exchange_adapter(
        exchange_id=account.exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        mode=mode,
        password=passphrase,
    )
    async with adapter:
        result = await adapter.get_order(exchange_order_id, symbol)

    return result


async def get_open_orders(
    account_id: UUID,
    symbol: str | None,
    session: Session,
) -> list[OrderResult]:
    """Fetch all open orders, optionally filtered by symbol."""
    account = _get_account(account_id, session)
    api_key = decrypt(account.api_key_encrypted)
    api_secret = decrypt(account.api_secret_encrypted)
    passphrase = decrypt(account.passphrase_encrypted) if account.passphrase_encrypted else None
    mode = ExchangeMode(account.mode)

    adapter = create_exchange_adapter(
        exchange_id=account.exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        mode=mode,
        password=passphrase,
    )
    async with adapter:
        results = await adapter.get_open_orders(symbol)

    return results


async def get_balance(
    account_id: UUID,
    session: Session,
) -> AccountBalance:
    """Fetch account balance from the exchange."""
    account = _get_account(account_id, session)
    api_key = decrypt(account.api_key_encrypted)
    api_secret = decrypt(account.api_secret_encrypted)
    passphrase = decrypt(account.passphrase_encrypted) if account.passphrase_encrypted else None
    mode = ExchangeMode(account.mode)

    adapter = create_exchange_adapter(
        exchange_id=account.exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        mode=mode,
        password=passphrase,
    )
    async with adapter:
        balance = await adapter.get_balance()

    return balance


async def get_positions(
    account_id: UUID,
    symbol: str | None,
    session: Session,
) -> list[Position]:
    """Fetch open positions, optionally filtered by symbol."""
    account = _get_account(account_id, session)
    api_key = decrypt(account.api_key_encrypted)
    api_secret = decrypt(account.api_secret_encrypted)
    passphrase = decrypt(account.passphrase_encrypted) if account.passphrase_encrypted else None
    mode = ExchangeMode(account.mode)

    adapter = create_exchange_adapter(
        exchange_id=account.exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        mode=mode,
        password=passphrase,
    )
    async with adapter:
        positions = await adapter.get_positions(symbol)

    return positions
