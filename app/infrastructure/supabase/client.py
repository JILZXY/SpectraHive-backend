# Assisted by Antigravity (SI) — reviewed by Jeshua
"""Pool de conexiones directas a PostgreSQL/Supabase via psycopg v3."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from psycopg import Connection
from psycopg_pool import ConnectionPool

from app.config import DatabaseConfigError, get_database_url


class PostgresPoolManager:
    """Administra un pool psycopg3 compatible con Supavisor (modo transaccion)."""

    def __init__(self, database_url: str | None = None) -> None:
        if database_url is None:
            url = get_database_url()
        else:
            url = database_url.strip()
            if not url:
                raise DatabaseConfigError(
                    "Falta DATABASE_URL en las variables de entorno."
                )

        # prepare_threshold=None desactiva prepared statements en psycopg v3
        # para evitar errores con Supavisor (puerto 6543) en modo transaccion.
        self._pool = ConnectionPool(
            conninfo=url,
            min_size=1,
            max_size=5,
            open=False,
            kwargs={"prepare_threshold": None, "autocommit": False},
        )
        self._opened = False

    def ensure_open(self) -> None:
        if not self._opened:
            self._pool.open(wait=True)
            self._opened = True

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        self.ensure_open()
        with self._pool.connection() as conn:
            yield conn

    def close(self) -> None:
        if self._opened:
            self._pool.close()
            self._opened = False


def create_db_pool(database_url: str | None = None) -> PostgresPoolManager:
    """Crea el gestor de pool fallando de inmediato si falta DATABASE_URL."""
    return PostgresPoolManager(database_url=database_url)
