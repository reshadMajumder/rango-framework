import os
from pathlib import Path
from typing import Any, Dict

class Config:
    def __init__(self, settings_module=None):
        self.SETTINGS_MODULE = settings_module
        self._settings = {}
        self._load_settings()

    def _load_settings(self):
        # Default settings
        self._settings.update({
            'DEBUG': True,
            'SECRET_KEY': 'your-secret-key-here',
            'DATABASE': {
                'name': 'database.db',
                'type': 'sqlite'
            },
            'MIDDLEWARE': [
                'rango.middleware.session',
                'rango.middleware.cors'
            ],
            'STATIC_URL': '/static/',
            'STATIC_ROOT': 'static/',
            'TEMPLATES': 'templates/'
        })

        # Load from settings module
        if self.SETTINGS_MODULE:
            try:
                mod = __import__(self.SETTINGS_MODULE, {}, {}, [''])
                self._settings.update({
                    k: getattr(mod, k) 
                    for k in dir(mod) 
                    if k.isupper()
                })
            except ImportError:
                pass

    def __getattr__(self, name: str) -> Any:
        try:
            return self._settings[name]
        except KeyError:
            raise AttributeError(f"Setting '{name}' not found") 