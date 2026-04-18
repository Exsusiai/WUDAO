from __future__ import annotations

from python.adapters.ccxt_adapter import CcxtAdapter
from python.domain.exchange import ExchangeMode


def create_exchange_adapter(
    exchange_id: str,
    api_key: str,
    api_secret: str,
    mode: ExchangeMode,
    password: str | None = None,
) -> CcxtAdapter:
    return CcxtAdapter(
        exchange_id=exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        mode=mode,
        password=password,
    )
