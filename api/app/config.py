"""Application settings, read from environment variables or the project's .env file.

Secrets such as passwords are typed as SecretStr so they never appear in logs or reprs.
When DATABASE_URL is not set, it is built from the POSTGRES_* values in .env, so the
same .env works for Docker Compose and for commands run from the api/ folder.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    postgres_user: str = "graphlens"
    postgres_password: SecretStr = SecretStr("")
    postgres_db: str = "graphlens"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: SecretStr | None = None

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("")
    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379/0"

    # Index version the answers are read from (stored with every answer).
    index_version: str = "idx2-full-g0"

    # Where answers come from: "replay" (saved answers, no model) or "off" (no engine).
    answer_mode: str = "replay"

    # Key for the read-only status page. Empty means the status endpoint is switched off.
    admin_api_key: SecretStr = SecretStr("")

    # Signs the anonymous visitor token. Empty means no token can be issued (deny by default).
    visitor_token_secret: SecretStr = SecretStr("")
    visitor_token_ttl_days: int = 365

    # The only browser origin allowed to call the API (CORS).
    web_origin: str = "http://localhost:3000"

    # Seconds to wait for each dependency in the health check.
    health_timeout_s: float = 3.0

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if self.database_url is None:
            password = self.postgres_password.get_secret_value()
            self.database_url = SecretStr(
                f"postgresql+psycopg://{self.postgres_user}:{password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
