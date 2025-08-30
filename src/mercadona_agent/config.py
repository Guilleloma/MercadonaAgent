from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    app_env: str = os.getenv("APP_ENV", "dev")
    language: str = os.getenv("APP_LANGUAGE", "es")

    mercadona_api_base: str = os.getenv("MERCADONA_API_BASE", "https://api.mercadona.com")
    mercadona_username: str | None = os.getenv("MERCADONA_USERNAME")
    mercadona_password: str | None = os.getenv("MERCADONA_PASSWORD")

    http_timeout_ms: int = int(os.getenv("HTTP_TIMEOUT_MS", "10000"))
    retry_max: int = int(os.getenv("RETRY_MAX", "3"))

    # AI providers
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")


settings = Settings()
