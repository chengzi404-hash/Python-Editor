"""Base class for database backends."""

from typing import Any


class Row(dict):
    """Dict-like row whose iterator yields values.

    This makes it compatible with ``zip(keys, row)`` in the same way
    ``sqlite3.Row`` is used by the ORM hydration logic.
    """

    def __iter__(self):
        return iter(self.values())


class Backend:
    """Abstract base for database backends."""

    engine_name: str = ""
    param_style: str = "?"  # '?', '%s' or ':n'

    def __init__(self, alias: str, config: dict) -> None:
        self.alias = alias
        self.config = config

    def connection(self) -> Any:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def execute(self, sql: str, params: tuple = ()) -> Any:
        raise NotImplementedError

    def executemany(self, sql: str, seq: list[tuple]) -> None:
        raise NotImplementedError

    def fetchall(self, sql: str, params: tuple = ()) -> list[Any]:
        raise NotImplementedError

    def fetchone(self, sql: str, params: tuple = ()) -> Any:
        raise NotImplementedError

    def placeholder(self, index: int) -> str:
        """Return the parameter placeholder for the *index* position."""
        if self.param_style == ":n":
            return f":{index}"
        return self.param_style

    def quote_name(self, name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    def last_insert_id(self, table: str, pk: str) -> int:
        raise NotImplementedError

    def auto_increment_sql(self, column_name: str, column_type: str) -> str:
        """Render an auto-incrementing primary key column definition."""
        qn = self.quote_name(column_name)
        return f"{qn} {column_type} PRIMARY KEY AUTOINCREMENT"

    def limit_offset_sql(self, sql: str, limit: int | None, offset: int | None) -> str:
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        if offset is not None:
            sql += f" OFFSET {int(offset)}"
        return sql

    def boolean_sql_type(self) -> str:
        return "BOOLEAN"

    def sql_type(self, generic_type: str) -> str:
        """Map a generic SQL type to a backend-specific type."""
        if generic_type.upper() == "BOOLEAN":
            return self.boolean_sql_type()
        return generic_type

    def create_table_sql(self, table_name: str, columns_sql: str) -> str:
        return f"CREATE TABLE IF NOT EXISTS {self.quote_name(table_name)} ({columns_sql})"

    def drop_table_sql(self, table_name: str) -> str:
        return f"DROP TABLE IF EXISTS {self.quote_name(table_name)}"

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
        """Convert a Python value before binding it to a SQL parameter."""
        return value

    def _convert_params(self, params: tuple) -> tuple:
        return tuple(self.convert_param(p) for p in params)
