"""Oracle backend.

Tries drivers in this order:
    1. oracledb (Oracle official, Python 3 only)
    2. cx_Oracle

Configuration uses HOST, PORT and SERVICE_NAME (falls back to NAME).
"""

import contextlib
import re
import threading
from datetime import date, datetime
from typing import Any

from .base import Backend, Row


class OracleBackend(Backend):
    engine_name = "oracle"
    param_style = ":n"

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
        for name in ("oracledb", "cx_Oracle"):
            try:
                return __import__(name)
            except ImportError:
                continue
        raise ImportError("No Oracle driver found. Install oracledb or cx_Oracle.")

    def _dsn(self) -> str:
        host = self.config.get("HOST", "localhost")
        port = int(self.config.get("PORT", 1521))
        service = self.config.get("SERVICE_NAME") or self.config.get("NAME")
        return f"{host}:{port}/{service}"

    def _connect_kwargs(self) -> dict:
        cfg = {
            "user": self.config.get("USER", ""),
            "password": self.config.get("PASSWORD", ""),
            "dsn": self._dsn(),
        }
        cfg.update(self._options)
        return cfg

    def connection(self) -> Any:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            driver = self._ensure_driver()
            kwargs = self._connect_kwargs()
            conn = driver.connect(**kwargs)
            if self._autocommit:
                conn.autocommit = True
            self._local.conn = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            with contextlib.suppress(Exception):
                conn.close()
            self._local.conn = None

    def _cursor(self) -> Any:
        return self.connection().cursor()

    @staticmethod
    def _row_factory(cursor) -> Any:
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        def factory(*args):
            return Row(zip(columns, args, strict=False))

        return factory

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
            cur.rowfactory = self._row_factory(cur)
            rows = cur.fetchall()
            return list(rows) if rows else []
        finally:
            with contextlib.suppress(Exception):
                cur.close()

    def fetchone(self, sql: str, params: tuple = ()) -> Row | None:
        cur = self._cursor()
        try:
            cur.execute(sql, self._convert_params(params))
            cur.rowfactory = self._row_factory(cur)
            row = cur.fetchone()
            return row if row else None
        finally:
            with contextlib.suppress(Exception):
                cur.close()

    def last_insert_id(self, table: str, pk: str) -> int:
        row = self.fetchone(f"SELECT MAX({self.quote_name(pk)}) FROM {self.quote_name(table)}")
        return int(row[0]) if row and row[0] is not None else 0

    def auto_increment_sql(self, column_name: str, column_type: str) -> str:
        qn = self.quote_name(column_name)
        return f"{qn} NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"

    def limit_offset_sql(self, sql: str, limit: int | None, offset: int | None) -> str:
        if offset is not None:
            sql += f" OFFSET {int(offset)} ROWS"
        if limit is not None:
            sql += f" FETCH NEXT {int(limit)} ROWS ONLY"
        elif offset is not None:
            sql += " FETCH NEXT 9223372036854775807 ROWS ONLY"
        return sql

    def boolean_sql_type(self) -> str:
        return "NUMBER(1)"

    def sql_type(self, generic_type: str) -> str:
        upper = generic_type.upper()
        if upper.startswith("VARCHAR"):
            return generic_type.upper().replace("VARCHAR", "VARCHAR2")
        if upper.startswith("TEXT"):
            return "CLOB"
        if upper == "TIMESTAMP":
            return "TIMESTAMP"
        if upper == "DATE":
            return "DATE"
        return super().sql_type(generic_type)

    def create_table_sql(self, table_name: str, columns_sql: str) -> str:
        return f"CREATE TABLE {self.quote_name(table_name)} ({columns_sql})"

    def drop_table_sql(self, table_name: str) -> str:
        try:
            self.execute(f"DROP TABLE {self.quote_name(table_name)}")
        except Exception as exc:
            err = str(exc)
            if "ORA-00942" in err or "does not exist" in err.lower():
                return ""
            raise
        return ""

    def ensure_migrations_table(self) -> None:
        try:
            self.execute("""
                CREATE TABLE uui_migrations (
                    app VARCHAR2(255) NOT NULL,
                    id VARCHAR2(255) NOT NULL,
                    applied_at VARCHAR2(255),
                    CONSTRAINT pk_uui_migrations PRIMARY KEY (app, id)
                )
            """)
        except Exception as exc:
            err = str(exc)
            if "ORA-00955" in err or "ORA-01943" in err or "already exists" in err.lower():
                return
            raise

    def convert_param(self, value: Any) -> Any:
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, str):
            try:
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?", value):
                    return datetime.fromisoformat(value)
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    return date.fromisoformat(value)
            except ValueError:
                pass
        return super().convert_param(value)
