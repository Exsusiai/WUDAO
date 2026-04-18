from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production", "test"] = "development"
    app_mode: Literal["sandbox", "live"] = "sandbox"

    # Server
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Database
    database_url: str = "sqlite:///./wudao.db"

    # Logging
    log_level: str = "INFO"

    # Exchange
    exchange_name: str = "binance"

    # Encryption key (Fernet) — base64-encoded 32-byte key
    fernet_key: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Notion
    notion_api_token: str = ""

    # Webhook
    webhook_secret: str = ""
    webhook_default_account_id: str = ""


settings = Settings()
