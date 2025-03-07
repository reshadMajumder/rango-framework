from aiohttp import web
import os
import signal
import threading
import time
import traceback
import logging
from .router import SimpleRouter
from .orm import ORM
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add at the top level of the file
_global_app: Optional['App'] = None

def get_app() -> 'App':
    """Get the global app instance"""
    if _global_app is None:
        raise RuntimeError("App not initialized. Create an App instance first.")
    return _global_app

class App:
    def __init__(self, debug=True):
        global _global_app
        self.router = SimpleRouter()
        self.app = web.Application()
        self.orm = ORM()
        self.app.on_shutdown.append(self._cleanup)
        self.debug = debug
        self._setup_logging()
        _global_app = self  # Store the app instance globally

    def _setup_logging(self):
        # Configure aiohttp access logger properly
        self.app._debug = self.debug
        if self.debug:
            logging.getLogger('aiohttp.access').setLevel(logging.DEBUG)
        else:
            logging.getLogger('aiohttp.access').setLevel(logging.INFO)

    async def _cleanup(self, app):
        self.orm.close()

    def route(self, path, methods=['GET']):
        def decorator(handler):
            if isinstance(methods, str):
                self.add_route(methods, path, handler)
            else:
                for method in methods:
                    self.add_route(method, path, handler)
            return handler
        return decorator

    def add_route(self, method: str, path: str, handler):
        async def wrapped_handler(request):
            try:
                from .request import SimpleRequest
                from .response import SimpleResponse
                
                simple_request = SimpleRequest(request)
                
                # Extract path parameters
                match_info = request.match_info
                simple_request.path_params = dict(match_info)
                
                # Parse body for POST/PUT requests
                if method in ['POST', 'PUT', 'PATCH']:
                    await simple_request.parse_body(request)
                
                # Use the handler directly since we're already in the correct route
                response = await handler(simple_request, SimpleResponse)
                return response
            except web.HTTPException:
                raise
            except Exception as e:
                if self.debug:
                    error_details = {
                        'error': str(e),
                        'traceback': traceback.format_exc(),
                        'type': e.__class__.__name__
                    }
                    return web.json_response(error_details, status=500)
                else:
                    return web.json_response({
                        'error': 'Internal Server Error'
                    }, status=500)

        # Convert path parameters from {param} to {param:.*} for aiohttp
        path_pattern = path
        if '{' in path:
            import re
            path_pattern = re.sub(r'{([^:}]+)}', r'{\1:[^/]*}', path)

        # Add route to aiohttp app
        self.app.router.add_route(method, path_pattern, wrapped_handler)
        logger.debug(f"Added route: {method} {path} -> {path_pattern}")

    def run(self, host="127.0.0.1", port=8000, production=False):
        if production and not self.debug:
            if os.name == 'nt':  # Windows
                print("Warning: Production mode with Gunicorn is not supported on Windows.")
                print("Falling back to development server with debug=False")
                self._run_dev_server(host, port)
            else:
                self._run_production_server(host, port)
        else:
            self._run_dev_server(host, port)

    def _run_dev_server(self, host, port):
        if self.debug:
            print(f"======= Rango Framework =======")
            print(f"Starting development server at http://{host}:{port}")
            print("Debug mode: ON")
            self._enable_auto_reload()
        else:
            print("Running development server with debug=False")

        # Configure runner with proper logging
        runner = web.AppRunner(self.app, access_log_class=web.AccessLogger)
        return web.run_app(self.app, host=host, port=port, access_log=logger)

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