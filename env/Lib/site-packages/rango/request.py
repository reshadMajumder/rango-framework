from typing import Dict, Any, Optional
from urllib.parse import parse_qs
from aiohttp import web

class SimpleRequest:
    def __init__(self, request: web.Request):
        self._request = request  # Store the original request
        self.headers = request.headers
        self.method = request.method
        self.path = request.path
        self.query_params = self._parse_query_params(request.rel_url.query_string)
        self.body = None
        self.path_params = {}
        self._json_data = None

    async def parse_body(self, request: web.Request):
        content_type = request.headers.get('Content-Type', '')
        
        try:
            if 'application/json' in content_type:
                self.body = await request.json()
                self._json_data = self.body
            elif 'application/x-www-form-urlencoded' in content_type:
                raw_data = await request.text()
                self.body = parse_qs(raw_data)
            elif 'multipart/form-data' in content_type:
                self.body = await request.post()
            else:
                self.body = await request.text()
        except Exception as e:
            raise web.HTTPBadRequest(text=str(e))

    async def json(self) -> Optional[Dict[str, Any]]:
        """Get JSON data from the request"""
        if self._json_data is None:
            try:
                self._json_data = await self._request.json()
            except Exception:
                raise web.HTTPBadRequest(text="Invalid JSON data")
        return self._json_data

    def _parse_query_params(self, query_string: str) -> Dict[str, Any]:
        parsed = parse_qs(query_string)
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    @property
    def form(self) -> Dict[str, Any]:
        """Get form data from the request"""
        if not self.body:
            return {}
        return self.body if isinstance(self.body, dict) else {}

    @property
    def files(self) -> Dict[str, Any]:
        """Get uploaded files from the request"""
        if not hasattr(self._request, 'multipart'):
            return {}
        return self._request.multipart() 