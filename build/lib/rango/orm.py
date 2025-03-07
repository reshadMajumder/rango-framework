import sqlite3
import threading
from typing import Dict, Any, List, Optional, Union, Tuple
from aiohttp import web
import logging

logger = logging.getLogger(__name__)

class ORM:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self._local = threading.local()
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize database with optimizations"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes with reasonable safety
        conn.execute("PRAGMA cache_size=-2000")  # 2MB cache
        conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
        conn.close()

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
                logger.debug(f"Executing query: {query} with params: {params}")
                if isinstance(params, list) and len(params) > 0:
                    # Bulk operation
                    self.cursor.executemany(query, params)
                else:
                    # Single operation
                    self.cursor.execute(query, params)
                self.connection.commit()  # Commit after each successful execution
                return self.cursor
        except sqlite3.Error as e:
            self.connection.rollback()
            logger.error(f"Database error: {str(e)}")
            raise web.HTTPInternalServerError(text=str(e))
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Unexpected error: {str(e)}")
            raise

    def query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        try:
            cursor = self.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            logger.error(f"Query error: {str(e)}")
            raise

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
        try:
            if not data:
                raise ValueError("No data provided for insert")

            with self.lock:  # Ensure atomic transaction
                if isinstance(data, list):
                    # Bulk insert
                    if not data[0]:
                        raise ValueError("Empty data in bulk insert")
                    columns = list(data[0].keys())
                    placeholders = ','.join(['?' for _ in columns])
                    query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                    values = [tuple(item[col] for col in columns) for item in data]
                    self.cursor.executemany(query, values)
                else:
                    # Single insert
                    columns = list(data.keys())
                    placeholders = ','.join(['?' for _ in columns])
                    query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                    values = tuple(data.values())
                    self.cursor.execute(query, values)
                
                self.connection.commit()
                return self.cursor.lastrowid
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Insert error: {str(e)}")
            raise

    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple = ()) -> int:
        """Update records and return number of affected rows"""
        try:
            set_clause = ','.join([f"{k}=?" for k in data.keys()])
            query = f"UPDATE {table} SET {set_clause} WHERE {where}"
            values = tuple(data.values()) + params
            self.execute(query, values)
            return self.cursor.rowcount
        except Exception as e:
            logger.error(f"Update error: {str(e)}")
            raise

    def delete(self, table: str, where: str, params: tuple = ()) -> int:
        """Delete records and return number of affected rows"""
        try:
            query = f"DELETE FROM {table} WHERE {where}"
            self.execute(query, params)
            return self.cursor.rowcount
        except Exception as e:
            logger.error(f"Delete error: {str(e)}")
            raise

    def create_table(self, table_name: str, columns: Dict[str, str]):
        """Create a table if it doesn't exist"""
        try:
            columns_definition = ", ".join(f"{col} {dtype}" for col, dtype in columns.items())
            query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_definition})"
            self.execute(query)
            
            # Create indexes for better performance
            for col, dtype in columns.items():
                if 'UNIQUE' in dtype or 'PRIMARY KEY' in dtype:
                    index_name = f"idx_{table_name}_{col}"
                    self.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({col})")
        except Exception as e:
            logger.error(f"Create table error: {str(e)}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        return bool(self.get_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        ))

    