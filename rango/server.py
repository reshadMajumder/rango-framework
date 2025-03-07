import os
import importlib.util
from pathlib import Path

def run_server(host='127.0.0.1', port=8000, reload=True):
    """Run the development server"""
    # Find and load settings
    settings_path = Path('app/settings.py')
    if not settings_path.exists():
        raise ImportError("Cannot find settings.py")

    # Load settings module
    spec = importlib.util.spec_from_file_location("settings", settings_path)
    settings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings)

    # Load routes
    routes_path = Path('app/routes.py')
    if not routes_path.exists():
        raise ImportError("Cannot find routes.py")

    spec = importlib.util.spec_from_file_location("routes", routes_path)
    routes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(routes)

    # Get the app instance
    app = getattr(routes, 'app', None)
    if not app:
        raise ImportError("No app instance found in routes.py")

    # Override settings with command line arguments
    app.debug = getattr(settings, 'DEBUG', True)
    app.run(host=host, port=port, production=not reload) 