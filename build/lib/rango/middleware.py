from aiohttp import web
from typing import Callable, Dict, Any

class Middleware:
    def __init__(self, app):
        self.app = app

    async def session(self, request, handler):
        request['session'] = {}  # Simple session implementation
        response = await handler(request)
        return response

    async def cors(self, request, handler):
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response 