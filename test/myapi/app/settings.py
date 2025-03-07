# Application settings
import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Database settings
DATABASE = {
    'name': str(BASE_DIR / 'database.db'),
    'type': 'sqlite'
}

# Server settings
HOST = '127.0.0.1'
PORT = 8000

# Middleware
MIDDLEWARE = [
    'rango.middleware.session',
    'rango.middleware.cors'
]

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = str(BASE_DIR / 'static')

# Templates
TEMPLATES_DIR = str(BASE_DIR / 'templates') 