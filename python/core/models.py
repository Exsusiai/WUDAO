"""Wudao SQLModel domain models.

Scope is intentionally minimal: start with only AppSettings, which is the
single piece of state the app needs to boot (current mode, feature flags).
Additional tables will be introduced as concrete milestones land.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel



def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AppSettings(SQLModel, table=True):
    __tablename__ = "app_settings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # "sandbox" or "live"
    current_mode: str = Field(default="sandbox")
    default_account_id: Optional[UUID] = Field(default=None)
    telegram_notifications_enabled: bool = Field(default=False)
    notion_sync_enabled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ExchangeAccount(SQLModel, table=True):
    __tablename__ = "exchange_accounts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    label: str = Field(index=True)
    exchange_id: str = Field()
    api_key_encrypted: str = Field()
    api_secret_encrypted: str = Field()
    passphrase_encrypted: Optional[str] = Field(default=None)
    mode: str = Field(default="sandbox")
    is_default: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
