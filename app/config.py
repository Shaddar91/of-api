"""Settings from the environment, or from one file per setting under SECRETS_DIR."""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


def _setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None and (secrets_dir := os.getenv("SECRETS_DIR")):
        try:
            value = Path(secrets_dir, name).read_text(encoding="utf-8").strip()
        except OSError:
            value = None
    return default if value is None else value


def _database_url() -> str:
    explicit_url = _setting("DATABASE_URL")
    if explicit_url:
        return explicit_url

    host = _setting("DB_HOST", "localhost")
    port = _setting("DB_PORT", "5432")
    name = quote(_setting("DB_NAME", "of"), safe="")
    user = quote(_setting("DB_USER", "of"), safe="")
    password = quote(_setting("DB_PASSWORD", ""), safe="")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def _cors_origins() -> tuple[str, ...]:
    raw_origins = _setting("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
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
            token_ttl_seconds=int(_setting("TOKEN_TTL_SECONDS", "3600")),
            cors_allowed_origins=_cors_origins(),
        )
