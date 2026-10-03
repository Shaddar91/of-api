"""Environment-backed application configuration."""

import os
from dataclasses import dataclass
from urllib.parse import quote


def _database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = quote(os.getenv("DB_NAME", "of"), safe="")
    user = quote(os.getenv("DB_USER", "of"), safe="")
    password = quote(os.getenv("DB_PASSWORD", ""), safe="")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def _cors_origins() -> tuple[str, ...]:
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    return tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())


@dataclass(frozen=True, slots=True)
class Config:
    database_url: str
    token_ttl_seconds: int
    cors_allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            database_url=_database_url(),
            token_ttl_seconds=int(os.getenv("TOKEN_TTL_SECONDS", "3600")),
            cors_allowed_origins=_cors_origins(),
        )
