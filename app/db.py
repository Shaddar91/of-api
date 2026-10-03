"""Postgres connection pool and schema setup."""

import atexit
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any

from flask import current_app
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool_lock = Lock()
_pools: list[ConnectionPool] = []


def _close_pools() -> None:
    with _pool_lock:
        pools = tuple(_pools)
        _pools.clear()
    for pool in pools:
        pool.close()


atexit.register(_close_pools)


def _get_pool() -> ConnectionPool:
    pool = current_app.extensions.get("postgres_pool")
    if pool is not None:
        return pool

    with _pool_lock:
        pool = current_app.extensions.get("postgres_pool")
        if pool is None:
            pool = ConnectionPool(
                conninfo=current_app.config["DATABASE_URL"],
                min_size=1,
                max_size=5,
                kwargs={"row_factory": dict_row},
                open=False,
            )
            pool.open(wait=True)
            _pools.append(pool)
            current_app.extensions["postgres_pool"] = pool
    return pool


@contextmanager
def get_conn() -> Iterator[Connection[dict[str, Any]]]:
    with _get_pool().connection() as connection:
        yield connection


def init_schema() -> None:
    schema = Path(__file__).with_name("sql").joinpath("schema.sql").read_text()
    with get_conn() as connection:
        connection.execute(schema)
