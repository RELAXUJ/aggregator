"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    secret_key: str = Field(default="change-me-in-production")

    # Database (port 5433 to avoid conflict with local PostgreSQL)
    database_url: PostgresDsn = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5433/rwa_aggregator"
    )

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    celery_broker_url: RedisDsn = Field(default="redis://localhost:6379/1")
    celery_result_backend: RedisDsn = Field(default="redis://localhost:6379/2")

    # Price Feed Polling
    price_poll_interval_seconds: int = Field(default=30)
    staleness_threshold_seconds: int = Field(default=300)

    # Alert System
    alert_cooldown_minutes: int = Field(default=60)
    alert_check_interval_seconds: int = Field(default=300)

    # CEX API Keys
    kraken_api_key: str = Field(default="")
    kraken_api_secret: str = Field(default="")
    coinbase_api_key: str = Field(default="")
    coinbase_api_secret: str = Field(default="")

    # DEX Configuration
    eth_rpc_url: str = Field(default="")
    thegraph_api_key: str = Field(default="")  # Get from https://thegraph.com/studio/

    # Email (SendGrid)
    sendgrid_api_key: str = Field(default="")
    alert_from_email: str = Field(default="alerts@example.com")

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


