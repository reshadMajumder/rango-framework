import json
import sqlite3
from http.server import HTTPServer
from urllib.parse import parse_qs, urlparse
import asyncio
from aiohttp import web
import threading
import time
import os
import signal
import sys
import re
import platform
from typing import Dict, Any, Optional
import traceback
from functools import partial

# Only import gunicorn on Unix-like systems
IS_WINDOWS = platform.system().lower() == "windows"
if not IS_WINDOWS:
    import gunicorn.app.base
    
    class ProductionServer(gunicorn.app.base.BaseApplication):
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()

        def load_config(self):
            for key, value in self.options.items():
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

class SimpleRouter:
    def __init__(self):
        self.routes = {}

    def add_route(self, method: str, path: str, handler):
        # Convert path parameters to regex pattern
        pattern = re.sub(r'{([^/]+)}', r'(?P<\1>[^/]+)', path)
        self.routes[(method, pattern)] = handler

    def resolve(self, method: str, path: str):
        for (route_method, pattern), handler in self.routes.items():
            if method != route_method:
                continue
            match = re.match(f'^{pattern}$', path)
            if match:
                return handler, match.groupdict()
        return None, None

class SimpleRequest:
    def __init__(self, request: web.Request):
        self.headers = request.headers
        self.method = request.method
        self.path = request.path
        self.query_params = self._parse_query_params(request.rel_url.query_string)
        self.body = None
        self.path_params = {}

    async def parse_body(self, request: web.Request):
        content_type = request.headers.get('Content-Type', '')
        
        try:
            if 'application/json' in content_type:
                self.body = await request.json()
            elif 'application/x-www-form-urlencoded' in content_type:
                raw_data = await request.text()
                self.body = parse_qs(raw_data)
            elif 'multipart/form-data' in content_type:
                self.body = await request.post()
            else:
                self.body = await request.text()
        except Exception as e:
            raise web.HTTPBadRequest(text=str(e))

    def _parse_query_params(self, query_string: str) -> Dict[str, Any]:
        parsed = parse_qs(query_string)
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

class SimpleResponse:
    @staticmethod
    async def json(data: Any, status: int = 200, headers: Optional[Dict] = None):
        return web.json_response(data, status=status, headers=headers)

    @staticmethod
    async def text(text: str, status: int = 200, headers: Optional[Dict] = None):
        return web.Response(text=text, status=status, headers=headers)

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

    def execute(self, query: str, params: tuple = ()):
        try:
            with self.lock:
                self.cursor.execute(query, params)
                self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            raise web.HTTPInternalServerError(text=str(e))

    def fetchall(self, query, params=()):
        with self.lock:
            self.cursor.execute(query, params)
            return [dict(row) for row in self.cursor.fetchall()]

    def fetchone(self, query, params=()):
        with self.lock:
            self.cursor.execute(query, params)
            row = self.cursor.fetchone()
            return dict(row) if row else None

    def create_table(self, table_name, columns):
        columns_definition = ", ".join(f"{col} {dtype}" for col, dtype in columns.items())
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_definition})"
        self.execute(query)

    def insert(self, table_name, data):
        if not data:
            return
            
        # Handle both single dict and list of dicts
        if not isinstance(data, list):
            data = [data]
            
        # Prepare the query for multiple inserts
        columns = list(data[0].keys())
        placeholders = ", ".join("?" * len(columns))
        columns_str = ", ".join(columns)
        
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        
        # Execute for each row
        try:
            with self.lock:
                for row in data:
                    values = tuple(row[col] for col in columns)
                    self.cursor.execute(query, values)
                self.connection.commit()
        except sqlite3.Error as e:
            self.connection.rollback()
            raise web.HTTPBadRequest(text=f"Error inserting data: {str(e)}")

    def update(self, table_name, data, where, params=()):
        if not data:
            return
            
        # Prepare SET clause
        set_clause = ", ".join(f"{key} = ?" for key in data.keys())
        values = list(data.values()) + list(params)
        
        query = f"UPDATE {table_name} SET {set_clause}"
        if where:
            query += f" WHERE {where}"
            
        try:
            with self.lock:
                self.cursor.execute(query, values)
                self.connection.commit()
                if self.cursor.rowcount == 0:
                    raise web.HTTPNotFound(text=f"No {table_name} found to update")
        except sqlite3.Error as e:
            self.connection.rollback()
            raise web.HTTPBadRequest(text=f"Error updating data: {str(e)}")

    def select(self, table_name, columns="*", where=None, params=()):
        query = f"SELECT {columns} FROM {table_name}"
        if where:
            query += f" WHERE {where}"
        return self.fetchall(query, params)

class App:
    def __init__(self, debug=True):
        self.router = SimpleRouter()
        self.app = web.Application()
        self.orm = ORM()
        self.app.on_shutdown.append(self._cleanup)
        self.debug = debug

    async def _cleanup(self, app):
        self.orm.close()

    def add_route(self, method: str, path: str, handler):
        async def wrapped_handler(request):
            try:
                simple_request = SimpleRequest(request)
                handler_func, path_params = self.router.resolve(request.method, request.path)
                
                if not handler_func:
                    raise web.HTTPNotFound()

                simple_request.path_params = path_params
                await simple_request.parse_body(request)
                
                response = await handler_func(simple_request, SimpleResponse, self.orm)
                return response
            except web.HTTPException as http_ex:
                # Always show HTTP exceptions (404, 400, etc)
                raise
            except Exception as e:
                if self.debug:
                    # In debug mode, show detailed error information
                    error_details = {
                        'error': str(e),
                        'traceback': traceback.format_exc(),
                        'type': e.__class__.__name__
                    }
                    return web.json_response(error_details, status=500)
                else:
                    # In production, show generic error message
                    return web.json_response({
                        'error': 'Internal Server Error'
                    }, status=500)

        self.app.router.add_route(method, path, wrapped_handler)
        self.router.add_route(method, path, handler)

    def run(self, host="127.0.0.1", port=8000, production=False):
        if production and not self.debug:
            if IS_WINDOWS:
                print("Warning: Production mode with Gunicorn is not supported on Windows.")
                print("Falling back to development server with debug=False")
                self._run_dev_server(host, port)
            else:
                # Production server configuration
                options = {
                    'bind': f'{host}:{port}',
                    'workers': (os.cpu_count() or 1) * 2 + 1,
                    'worker_class': 'aiohttp.worker.GunicornWebWorker',
                    'accesslog': 'access.log',
                    'errorlog': 'error.log',
                    'capture_output': True,
                    'loglevel': 'info'
                }
                ProductionServer(self.app, options).run()
        else:
            self._run_dev_server(host, port)

    def _run_dev_server(self, host, port):
        if self.debug:
            print(f"======= This rango framework is created by Reshad =======")
            print(f"Starting development server at http://{host}:{port}")
            print("Debug mode: ON")
            self._enable_auto_reload()
        else:
            print("Warning: Running development server with debug=False")
        web.run_app(self.app, host=host, port=port, access_log=self.debug)

    def _enable_auto_reload(self):
        def restart_on_file_change():
            watched_files = {}
            for root, _, files in os.walk("."):
                for file in files:
                    if file.endswith(".py"):
                        filepath = os.path.join(root, file)
                        watched_files[filepath] = os.path.getmtime(filepath)

            while True:
                time.sleep(1)
                for filepath, last_modified in watched_files.items():
                    if not os.path.exists(filepath):
                        continue
                    current_modified = os.path.getmtime(filepath)
                    if current_modified != last_modified:
                        print(f"File changed: {filepath}. Restarting server...")
                        os.kill(os.getpid(), signal.SIGINT)

        threading.Thread(target=restart_on_file_change, daemon=True).start()

# Example Usage
if __name__ == "__main__":
    # Create app with debug mode
    app = App(debug=False)  # Set to False for production-like behavior

    # Initialize database table
    app.orm.create_table("users", {
        "id": "INTEGER PRIMARY KEY", 
        "name": "TEXT NOT NULL", 
        "age": "INTEGER NOT NULL"
    })
    app.orm.create_table("products", {"id": "INTEGER PRIMARY KEY", "name": "TEXT", "price": "INTEGER"})

    async def create_user(req, res, orm):
        data = req.body
        orm.insert("users", {"name": data["name"], "age": data["age"]})
        return await res.json({"message": "User created successfully!"})
    
    async def create_products(req, res, orm):
        data = req.body
        try:
            # Handle both single product and list of products
            if isinstance(data, dict):
                data = [data]
            
            # Validate data
            for product in data:
                if not all(key in product for key in ['name', 'price']):
                    raise web.HTTPBadRequest(text="Each product must have 'name' and 'price'")
            
                # Convert price to integer if it's a string
                if isinstance(product['price'], str):
                    product['price'] = int(product['price'])
            
            orm.insert("products", data)
            return await res.json({
                "message": f"Successfully added {len(data)} product(s)",
                "products": data
            })
        except ValueError as e:
            raise web.HTTPBadRequest(text="Invalid price value. Price must be a number")
        except Exception as e:
            if isinstance(e, web.HTTPException):
                raise
            raise web.HTTPBadRequest(text=str(e))

    async def get_users(req, res, orm):
        users = orm.select("users")
        return await res.json({"users": users})
    
    async def get_products(req, res, orm):
        products = orm.select("products")
        return await res.json({"products": products})

    async def get_user(req, res, orm):
        user_id = req.path_params.get('id')
        user = orm.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            raise web.HTTPNotFound(text="User not found")
        return await res.json({"user": user})

    async def update_product(req, res, orm):
        product_id = req.path_params.get('id')
        data = req.body
        
        # Validate data
        valid_fields = {'name', 'price'}
        update_data = {k: v for k, v in data.items() if k in valid_fields}
        
        if not update_data:
            raise web.HTTPBadRequest(text="No valid fields to update")
        
        # Convert price to integer if it's present and a string
        if 'price' in update_data and isinstance(update_data['price'], str):
            try:
                update_data['price'] = int(update_data['price'])
            except ValueError:
                raise web.HTTPBadRequest(text="Invalid price value. Price must be a number")
        
        orm.update("products", update_data, "id = ?", (product_id,))
        
        # Get updated product
        updated_product = orm.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))
        return await res.json({
            "message": "Product updated successfully",
            "product": updated_product
        })

    app.add_route("POST", "/users", create_user)
    app.add_route("GET", "/users", get_users)
    app.add_route("POST", "/products", create_products)
    app.add_route("GET", "/products", get_products)
    app.add_route("GET", "/users/{id}", get_user)
    app.add_route("PUT", "/products/{id}", update_product)

    # Run the server
    if IS_WINDOWS:
        # On Windows, always use development server
        app.run(port=8001, production=False)
    else:
        # On Unix-like systems, can use production mode
        app.run(port=8001, production=True)
