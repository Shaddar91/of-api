"""Fixtures for tests against the Postgres named by DATABASE_URL."""

import os

import pytest

from app import create_app
from app.db import get_conn, init_schema


@pytest.fixture(scope="session")
def app():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.fail(
            "DATABASE_URL must name a disposable Postgres: tests truncate its tables"
        )
    app = create_app()
    app.config.update(DATABASE_URL=database_url, TESTING=True)
    with app.app_context():
        init_schema()
    return app


@pytest.fixture
def clean_database(app):
    with app.app_context(), get_conn() as connection:
        connection.execute("TRUNCATE TABLE tokens, users RESTART IDENTITY CASCADE")


@pytest.fixture
def client(app, clean_database):
    return app.test_client()


@pytest.fixture
def fetch(app):
    def run(statement, params=None):
        with app.app_context(), get_conn() as connection:
            return connection.execute(statement, params).fetchall()

    return run


@pytest.fixture
def user(app, clean_database, monkeypatch):
    credentials = {"username": "integration-user", "password": "example-password"}
    monkeypatch.setenv("OF_API_USER_PASSWORD", credentials["password"])
    with app.app_context():
        result = app.test_cli_runner().invoke(
            args=["create-user", credentials["username"]]
        )
    assert result.exit_code == 0, result.output
    return credentials
