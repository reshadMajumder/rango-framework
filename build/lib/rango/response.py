from typing import Any, Dict, Optional
from aiohttp import web

class SimpleResponse:
    @staticmethod
    async def json(data: Any, status: int = 200, headers: Optional[Dict] = None):
        return web.json_response(data, status=status, headers=headers)

    @staticmethod
    async def text(text: str, status: int = 200, headers: Optional[Dict] = None):
        return web.Response(text=text, status=status, headers=headers)

    @staticmethod
    async def html(html: str, status: int = 200, headers: Optional[Dict] = None):
        if headers is None:
            headers = {}
        headers['Content-Type'] = 'text/html'
        return web.Response(text=html, status=status, headers=headers) 