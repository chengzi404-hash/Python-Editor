"""PostgreSQL backend.

Tries drivers in this order:
    1. psycopg (v3)
    2. psycopg2
"""

import contextlib
import threading
from typing import Any

from .base import Backend, Row


class PostgresqlBackend(Backend):
    engine_name = "postgresql"
    param_style = "%s"

    def __init__(self, alias: str, config: dict) -> None:
        super().__init__(alias, config)
        self._local = threading.local()
        self._driver: Any = None
        self._options = dict(config.get("OPTIONS") or {})
        self._autocommit = config.get("AUTOCOMMIT", True)

    def _ensure_driver(self) -> Any:
        if self._driver is None:
            self._driver = self._import_driver()
        return self._driver

    def _import_driver(self) -> Any:
        for name in ("psycopg", "psycopg2"):
            try:
                return __import__(name)
            except ImportError:
                continue
        raise ImportError("No PostgreSQL driver found. Install psycopg or psycopg2.")

    def _connect_kwargs(self) -> dict:
        cfg = {
            "host": self.config.get("HOST", "localhost"),
            "port": int(self.config.get("PORT", 5432)),
            "user": self.config.get("USER", ""),
            "password": self.config.get("PASSWORD", ""),
            "dbname": self.config.get("NAME", ""),
        }
        cfg.update(self._options)
        return cfg

    def connection(self) -> Any:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            driver = self._ensure_driver()
            kwargs = self._connect_kwargs()
            if driver.__name__ == "psycopg":
                conn = driver.connect(**kwargs)
                conn.autocommit = self._autocommit
            else:
                import psycopg2.extras

                kwargs.setdefault("cursor_factory", psycopg2.extras.RealDictCursor)
                conn = driver.connect(**kwargs)
                conn.autocommit = self._autocommit
            self._local.conn = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            with contextlib.suppress(Exception):
                conn.close()
            self._local.conn = None

    def _cursor(self) -> Any:
        conn = self.connection()
        driver = self._ensure_driver()
        if driver.__name__ == "psycopg":
            return conn.cursor(row_factory=driver.rows.dict_row)
        return conn.cursor()

    def execute(self, sql: str, params: tuple = ()) -> Any:
        cur = self._cursor()
        try:
            cur.execute(sql, self._convert_params(params))
            return cur
        finally:
            with contextlib.suppress(Exception):
                cur.close()

    def executemany(self, sql: str, seq: list[tuple]) -> None:
        cur = self._cursor()
        try:
            cur.executemany(sql, [self._convert_params(p) for p in seq])
        finally:
            with contextlib.suppress(Exception):
                cur.close()

    def fetchall(self, sql: str, params: tuple = ()) -> list[Row]:
        cur = self._cursor()
        try:
            cur.execute(sql, self._convert_params(params))
            rows = cur.fetchall()
            return [Row(r) for r in rows] if rows else []
        finally:
            with contextlib.suppress(Exception):
                cur.close()

    def fetchone(self, sql: str, params: tuple = ()) -> Row | None:
        cur = self._cursor()
        try:
            cur.execute(sql, self._convert_params(params))
            row = cur.fetchone()
            return Row(row) if row else None
        finally:
            with contextlib.suppress(Exception):
                cur.close()

    def last_insert_id(self, table: str, pk: str) -> int:
        sql = (
            f"SELECT currval(pg_get_identity_sequence({self.quote_name(table)}, "
            f"{self.quote_name(pk)}))"
        )
        row = self.fetchone(sql)
        return int(row[0]) if row else 0

    def auto_increment_sql(self, column_name: str, column_type: str) -> str:
        qn = self.quote_name(column_name)
        return f"{qn} {column_type} GENERATED ALWAYS AS IDENTITY PRIMARY KEY"

    def ensure_migrations_table(self) -> None:
        self.execute("""
            CREATE TABLE IF NOT EXISTS uui_migrations (
                app TEXT NOT NULL,
                id TEXT NOT NULL,
                applied_at TEXT,
                PRIMARY KEY (app, id)
            )
        """)

    def convert_param(self, value: Any) -> Any:
        return value
