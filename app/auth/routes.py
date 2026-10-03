"""Authentication HTTP routes."""

from datetime import UTC, datetime
from typing import Any

from flask import Blueprint, Response, jsonify, request

from app.auth import service

bp = Blueprint("auth", __name__, url_prefix="/api/v1")


def _error(message: str, status: int) -> tuple[Response, int]:
    return jsonify(error=message), status


def _expires_at(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _bearer_token() -> str | None:
    scheme, separator, token = request.headers.get("Authorization", "").partition(" ")
    if separator and scheme.lower() == "bearer" and token.strip():
        return token.strip()
    return None


@bp.post("/login")
def login() -> Response | tuple[Response, int]:
    payload: Any = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _error("username and password required", 400)

    username = payload.get("username")
    password = payload.get("password")
    credentials_present = (
        isinstance(username, str)
        and bool(username)
        and isinstance(password, str)
        and bool(password)
    )
    if not credentials_present:
        return _error("username and password required", 400)

    user = service.authenticate(username, password)
    if user is None:
        return _error("invalid credentials", 401)

    token, expires_at = service.issue_token(user["id"])
    return jsonify(
        token=token,
        expires_at=_expires_at(expires_at),
        username=user["username"],
    )


@bp.get("/me")
def me() -> Response | tuple[Response, int]:
    token = _bearer_token()
    session = service.resolve(token) if token else None
    if session is None:
        return _error("invalid token", 401)
    return jsonify(
        username=session["username"],
        expires_at=_expires_at(session["expires_at"]),
    )


@bp.post("/logout")
def logout() -> Response | tuple[Response, int]:
    token = _bearer_token()
    if token is None or service.resolve(token) is None:
        return _error("invalid token", 401)
    service.revoke(token)
    return Response(status=204)
