"""Database administration commands."""

import os

import click
from flask import Flask
from werkzeug.security import generate_password_hash

from app.db import get_conn, init_schema


@click.command("init-db")
def init_db_command() -> None:
    init_schema()
    click.echo("Database schema initialized.")


@click.command("create-user")
@click.argument("name")
def create_user_command(name: str) -> None:
    password = os.getenv("OF_API_USER_PASSWORD")
    if not password:
        raise click.ClickException("OF_API_USER_PASSWORD is required")

    password_hash = generate_password_hash(password)
    with get_conn() as connection:
        connection.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (%s, %s)
            ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
            """,
            (name, password_hash),
        )
    click.echo(f"User {name} created.")


def register_commands(app: Flask) -> None:
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_user_command)
