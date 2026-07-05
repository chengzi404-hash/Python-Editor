"""MySQL backend.

Tries drivers in this order:
    1. pymysql
    2. mysql.connector
    3. MySQLdb
"""
import threading
from typing import Any, List, Optional, Tuple

from .base import Backend, Row


class MysqlBackend(Backend):
    engine_name = 'mysql'
    param_style = '%s'

    def __init__(self, alias: str, config: dict) -> None:
        super().__init__(alias, config)
        self._local = threading.local()
        self._driver: Any = None
        self._options = dict(config.get('OPTIONS') or {})
        self._autocommit = config.get('AUTOCOMMIT', True)

    def _ensure_driver(self) -> Any:
        if self._driver is None:
            self._driver = self._import_driver()
        return self._driver

    def _import_driver(self) -> Any:
        for name in ('pymysql', 'mysql.connector', 'MySQLdb'):
            try:
                return __import__(name)
            except ImportError:
                continue
        raise ImportError(
            'No MySQL driver found. Install pymysql, mysql-connector-python or MySQLdb.'
        )

    def _connect_kwargs(self) -> dict:
        cfg = {
            'host': self.config.get('HOST', 'localhost'),
            'port': int(self.config.get('PORT', 3306)),
            'user': self.config.get('USER', ''),
            'password': self.config.get('PASSWORD', ''),
            'database': self.config.get('NAME', ''),
            'charset': 'utf8mb4',
            'autocommit': self._autocommit,
        }
        cfg.update(self._options)
        return cfg

    def connection(self) -> Any:
        conn = getattr(self._local, 'conn', None)
        if conn is None:
            driver = self._ensure_driver()
            kwargs = self._connect_kwargs()
            cursor_class = getattr(driver, 'cursors', None)
            if cursor_class is not None and hasattr(cursor_class, 'DictCursor'):
                kwargs.setdefault('cursorclass', cursor_class.DictCursor)
            elif driver.__name__ == 'mysql.connector':
                kwargs.setdefault('cursorclass', driver.cursor.MySQLCursorDict)
            conn = driver.connect(**kwargs)
            self._local.conn = conn
        return conn

    def close(self) -> None:
        conn = getattr(self._local, 'conn', None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    def _cursor(self) -> Any:
        return self.connection().cursor()

    def execute(self, sql: str, params: Tuple = ()) -> Any:
        cur = self._cursor()
        try:
            cur.execute(sql, self._convert_params(params))
            return cur
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def executemany(self, sql: str, seq: List[Tuple]) -> None:
        cur = self._cursor()
        try:
            cur.executemany(sql, [self._convert_params(p) for p in seq])
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def fetchall(self, sql: str, params: Tuple = ()) -> List[Row]:
        cur = self._cursor()
        try:
            cur.execute(sql, self._convert_params(params))
            rows = cur.fetchall()
            return [Row(r) for r in rows] if rows else []
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def fetchone(self, sql: str, params: Tuple = ()) -> Optional[Row]:
        cur = self._cursor()
        try:
            cur.execute(sql, self._convert_params(params))
            row = cur.fetchone()
            return Row(row) if row else None
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def last_insert_id(self, table: str, pk: str) -> int:
        row = self.fetchone('SELECT LAST_INSERT_ID()')
        return int(row[0]) if row else 0

    def quote_name(self, name: str) -> str:
        return '`' + name.replace('`', '``') + '`'

    def auto_increment_sql(self, column_name: str, column_type: str) -> str:
        qn = self.quote_name(column_name)
        return f'{qn} {column_type} AUTO_INCREMENT PRIMARY KEY'

    def boolean_sql_type(self) -> str:
        return 'TINYINT(1)'

    def ensure_migrations_table(self) -> None:
        self.execute('''
            CREATE TABLE IF NOT EXISTS uui_migrations (
                app VARCHAR(255) NOT NULL,
                id VARCHAR(255) NOT NULL,
                applied_at VARCHAR(255),
                PRIMARY KEY (app, id)
            )
        ''')

    def convert_param(self, value: Any) -> Any:
        if isinstance(value, bool):
            return 1 if value else 0
        return super().convert_param(value)
