"""Password authentication and opaque token storage."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app
from werkzeug.security import check_password_hash

from app.db import get_conn


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    with get_conn() as connection:
        user = connection.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s",
            (username,),
        ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return None
    return user


def issue_token(user_id: int) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    ttl = timedelta(seconds=current_app.config["TOKEN_TTL_SECONDS"])
    expires_at = datetime.now(UTC) + ttl
    with get_conn() as connection:
        row = connection.execute(
            """
            INSERT INTO tokens (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            RETURNING expires_at
            """,
            (user_id, _token_hash(token), expires_at),
        ).fetchone()
    return token, row["expires_at"]


def resolve(token: str) -> dict[str, Any] | None:
    with get_conn() as connection:
        return connection.execute(
            """
            SELECT users.username, tokens.expires_at
            FROM tokens
            JOIN users ON users.id = tokens.user_id
            WHERE tokens.token_hash = %s AND tokens.expires_at > now()
            """,
            (_token_hash(token),),
        ).fetchone()


def revoke(token: str) -> None:
    token_hash = _token_hash(token)
    with get_conn() as connection:
        connection.execute("DELETE FROM tokens WHERE token_hash = %s", (token_hash,))
