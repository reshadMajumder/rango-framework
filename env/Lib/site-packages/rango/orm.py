import sqlite3
import threading
from typing import Dict, Any, List, Optional, Union, Tuple
from aiohttp import web

class ORM:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self._local = threading.local()
        self.lock = threading.Lock()

    @property
    def connection(self):
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @property
    def cursor(self):
        if not hasattr(self._local, 'cursor'):
            self._local.cursor = self.connection.cursor()
        return self._local.cursor

    def close(self):
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection
        if hasattr(self._local, 'cursor'):
            del self._local.cursor

    def is_connected(self) -> bool:
        try:
            self.cursor.execute("SELECT 1")
            return True
        except (sqlite3.Error, AttributeError):
            return False

    def execute(self, query: str, params: Union[tuple, List[tuple]] = ()) -> sqlite3.Cursor:
        """Execute a query and return the cursor"""
        try:
            with self.lock:
                if isinstance(params, list) and len(params) > 0:
                    # Bulk operation
                    self.cursor.executemany(query, params)
                else:
                    # Single operation
                    self.cursor.execute(query, params)
                self.connection.commit()
                return self.cursor
        except sqlite3.Error as e:
            self.connection.rollback()
            raise web.HTTPInternalServerError(text=str(e))

    def query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        cursor = self.execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute a query and return one result as dictionary"""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))
        return None

    def insert(self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> int:
        """Insert one or multiple records and return last inserted id"""
        if not data:
            raise ValueError("No data provided for insert")

        if isinstance(data, list):
            # Bulk insert
            if not data[0]:
                raise ValueError("Empty data in bulk insert")
            columns = data[0].keys()
            placeholders = ','.join(['?' for _ in columns])
            query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
            values = [tuple(item[col] for col in columns) for item in data]
            self.execute(query, values)
        else:
            # Single insert
            columns = data.keys()
            placeholders = ','.join(['?' for _ in columns])
            query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
            self.execute(query, tuple(data.values()))

        return self.cursor.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple = ()) -> int:
        """Update records and return number of affected rows"""
        set_clause = ','.join([f"{k}=?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        values = tuple(data.values()) + params
        self.execute(query, values)
        return self.cursor.rowcount

    def delete(self, table: str, where: str, params: tuple = ()) -> int:
        """Delete records and return number of affected rows"""
        query = f"DELETE FROM {table} WHERE {where}"
        self.execute(query, params)
        return self.cursor.rowcount

    def create_table(self, table_name: str, columns: Dict[str, str]):
        """Create a table if it doesn't exist"""
        columns_definition = ", ".join(f"{col} {dtype}" for col, dtype in columns.items())
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_definition})"
        self.execute(query)

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        return bool(self.get_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ))

    