"""SQLite backend."""

import contextlib
import sqlite3
import threading
from typing import Any

from .base import Backend


class SqliteBackend(Backend):
    engine_name = "sqlite"

    def __init__(self, alias: str, config: dict) -> None:
        super().__init__(alias, config)
        self._local = threading.local()
        self._name = config.get("NAME", ":memory:")
        if self._name != ":memory:":
            import os

            parent = os.path.dirname(self._name)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
        self._pragmas = config.get("OPTIONS", {}) or {}
        self._auto_commit = self._pragmas.pop("autocommit", True)

    def connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            isolation = None if self._auto_commit else "DEFERRED"
            conn = sqlite3.connect(self._name, isolation_level=isolation, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            for pragma, value in self._pragmas.items():
                with contextlib.suppress(Exception):
                    conn.execute(f"PRAGMA {pragma} = {value!r}")
            self._local.conn = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            with contextlib.suppress(Exception):
                conn.close()
            self._local.conn = None

    def execute(self, sql: str, params: tuple = ()) -> Any:
        cur = self.connection().execute(sql, params)
        try:
            return cur.fetchall()
        except Exception:
            return cur

    def executemany(self, sql: str, seq: list[tuple]) -> None:
        cur = self.connection().executemany(sql, seq)
        with contextlib.suppress(Exception):
            cur.close()

    def fetchall(self, sql: str, params: tuple = ()) -> list[tuple]:
        cur = self.connection().execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows

    def fetchone(self, sql: str, params: tuple = ()) -> tuple:
        cur = self.connection().execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return row

    def last_insert_id(self, table: str, pk: str) -> int:
        cur = self.connection().execute("SELECT last_insert_rowid()")
        row = cur.fetchone()
        cur.close()
        return int(row[0]) if row else 0
