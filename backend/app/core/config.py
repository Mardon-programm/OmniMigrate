from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Core ---
    app_name: str = "OmniMigrate"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    environment: Literal["development", "staging", "production"] = "development"

    # --- Security ---
    secret_key: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    refresh_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    bcrypt_rounds: int = 12
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    # --- Rate limiting ---
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # --- Database ---
    database_url: str = "postgresql+asyncpg://omnimigrate:omnimigrate@postgres:5432/omnimigrate"

    # --- Redis ---
    redis_url: str = "redis://redis:6379/0"

    # --- OpenAI / LLM ---
    openai_api_key: str = Field(default="")
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None
    llm_temperature: float = 0.1
    llm_max_tokens: int = 8192
    llm_fallback_to_rules: bool = True

    # --- Sandbox ---
    sandbox_enabled: bool = True
    sandbox_timeout_seconds: int = 30
    max_self_heal_attempts: int = 3

    # --- Git / GitHub ---
    github_api_url: str = "https://api.github.com"
    github_default_base_branch: str = "main"
    git_author_name: str = "OmniMigrate Bot"
    git_author_email: str = "bot@omnimigrate.app"
    git_branch_prefix: str = "omnimigrate"
    git_clone_timeout_seconds: int = 120
    git_test_timeout_seconds: int = 600
    git_max_repo_bytes: int = 200 * 1024 * 1024

    # --- Storage ---
    workspace_root: str = "/data/workspaces"

    # --- Stripe / Billing ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # --- Observability ---
    otel_enabled: bool = False
    otel_service_name: str = "omnimigrate-backend"
    otel_exporter_otlp_endpoint: str = ""
    prometheus_enabled: bool = True

    @property
    def postgres_url_for_alembic(self) -> str:
        return self.database_url.replace("+asyncpg", "")

    @property
    def cors_origins(self) -> list[str]:
        return list(self.allowed_origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
