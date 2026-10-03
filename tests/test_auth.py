"""Login, bearer token, logout, and CORS of the auth API against Postgres."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app import create_app

FRONTEND_ORIGIN = "http://localhost:5173"
TOKENS = """
    SELECT users.username, tokens.token_hash, tokens.expires_at
    FROM tokens JOIN users ON users.id = tokens.user_id
    ORDER BY tokens.id
"""


def sha256(value):
    return hashlib.sha256(value.encode()).hexdigest()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def login(client, user):
    response = client.post("/api/v1/login", json=user)
    assert response.status_code == 200
    return response.get_json()


def preflight(
    client, origin, path="/api/v1/login", method="POST", headers="content-type"
):
    return client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def test_login_returns_token_and_stores_only_its_sha256(app, client, user, fetch):
    ttl = timedelta(seconds=app.config["TOKEN_TTL_SECONDS"])
    before = datetime.now(UTC)
    response = client.post("/api/v1/login", json=user)
    after = datetime.now(UTC)

    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"token", "expires_at", "username"}
    assert body["username"] == user["username"]
    assert body["expires_at"].endswith("Z")
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert before + ttl <= expires_at <= after + ttl
    assert fetch(TOKENS) == [
        {
            "username": user["username"],
            "token_hash": sha256(body["token"]),
            "expires_at": expires_at,
        }
    ]


@pytest.mark.parametrize(
    ("field", "value"), [("password", "wrong-password"), ("username", "unknown-user")]
)
def test_login_rejects_bad_credentials(client, user, fetch, field, value):
    response = client.post("/api/v1/login", json={**user, field: value})

    assert response.status_code == 401
    assert response.get_json() == {"error": "invalid credentials"}
    assert fetch(TOKENS) == []


@pytest.mark.parametrize(
    "body",
    [
        '{"username": "integration-user"}',
        '{"password": "example-password"}',
        '{"username": "", "password": "example-password"}',
        '{"username": "integration-user", "password": ""}',
        '{"username": 1, "password": "example-password"}',
        "{}",
        "[]",
        "not json",
    ],
    ids=[
        "no-password",
        "no-username",
        "empty-username",
        "empty-password",
        "non-string-username",
        "empty-object",
        "array",
        "not-json",
    ],
)
def test_login_requires_username_and_password(client, user, fetch, body):
    response = client.post("/api/v1/login", data=body, content_type="application/json")

    assert response.status_code == 400
    assert response.get_json() == {"error": "username and password required"}
    assert fetch(TOKENS) == []


def test_me_returns_username_for_valid_token(client, user):
    session = login(client, user)

    response = client.get("/api/v1/me", headers=bearer(session["token"]))

    assert response.status_code == 200
    assert response.get_json() == {
        "username": user["username"],
        "expires_at": session["expires_at"],
    }


@pytest.mark.parametrize(
    "authorization",
    [None, "Bearer garbage-token", "Bearer ", "Token {token}", "{token}"],
    ids=["missing", "garbage-token", "empty-token", "wrong-scheme", "no-scheme"],
)
def test_me_rejects_invalid_bearer(client, user, authorization):
    token = login(client, user)["token"]
    headers = {}
    if authorization is not None:
        headers["Authorization"] = authorization.format(token=token)

    response = client.get("/api/v1/me", headers=headers)

    assert response.status_code == 401
    assert response.get_json() == {"error": "invalid token"}


def test_me_rejects_expired_token(client, user, fetch):
    token = login(client, user)["token"]
    expired = fetch(
        "UPDATE tokens SET expires_at = now() - interval '1 second'"
        " WHERE token_hash = %s RETURNING id",
        (sha256(token),),
    )

    response = client.get("/api/v1/me", headers=bearer(token))

    assert len(expired) == 1
    assert response.status_code == 401
    assert response.get_json() == {"error": "invalid token"}


def test_logout_revokes_token(client, user, fetch):
    token = login(client, user)["token"]

    logout = client.post("/api/v1/logout", headers=bearer(token))
    me = client.get("/api/v1/me", headers=bearer(token))

    assert logout.status_code == 204
    assert logout.data == b""
    assert me.status_code == 401
    assert me.get_json() == {"error": "invalid token"}
    assert fetch(TOKENS) == []


def test_logout_keeps_other_sessions(client, user, fetch):
    first = login(client, user)["token"]
    second = login(client, user)["token"]

    logout = client.post("/api/v1/logout", headers=bearer(first))
    me = client.get("/api/v1/me", headers=bearer(second))

    assert logout.status_code == 204
    assert me.status_code == 200
    assert [row["token_hash"] for row in fetch(TOKENS)] == [sha256(second)]


def test_logout_rejects_invalid_token(client):
    response = client.post("/api/v1/logout", headers=bearer("garbage-token"))

    assert response.status_code == 401
    assert response.get_json() == {"error": "invalid token"}


def test_healthz_still_ok(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


@pytest.mark.parametrize(
    ("path", "method", "headers"),
    [("/api/v1/login", "POST", "content-type"), ("/api/v1/me", "GET", "authorization")],
)
def test_cors_preflight_allows_default_origin(monkeypatch, path, method, headers):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    client = create_app().test_client()

    response = preflight(client, FRONTEND_ORIGIN, path, method, headers)

    assert response.headers["Access-Control-Allow-Origin"] == FRONTEND_ORIGIN
    assert headers in response.headers["Access-Control-Allow-Headers"].lower()


def test_cors_allows_only_configured_origins(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", "https://app.example.com, https://admin.example.com"
    )
    client = create_app().test_client()

    allowed = {
        origin: preflight(client, origin).headers.get("Access-Control-Allow-Origin")
        for origin in (
            "https://app.example.com",
            "https://admin.example.com",
            FRONTEND_ORIGIN,
        )
    }

    assert allowed == {
        "https://app.example.com": "https://app.example.com",
        "https://admin.example.com": "https://admin.example.com",
        FRONTEND_ORIGIN: None,
    }
