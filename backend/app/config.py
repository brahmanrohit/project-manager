import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that used to ship as defaults or sit in example files.
# If any of them reach a running server we refuse to start.
PLACEHOLDER_SECRETS = {
    "change-me-in-production",
    "your-long-random-secret-key-here",
    "your-secret-key-here",
    "secret",
    "changeme",
}


class Settings(BaseSettings):
    app_name: str = "Ethara Project Management API"
    env: str = "development"
    debug: bool = True
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/ethara")
    secret_key: str | None = None
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def check_secret_key(self):
        if not self.secret_key or self.secret_key.strip().lower() in PLACEHOLDER_SECRETS:
            raise ValueError(
                "SECRET_KEY is missing or is still a placeholder. "
                "Set a real random value, for example: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        if self.is_production and len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production.")
        return self

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}


settings = Settings()
