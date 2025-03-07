import re
from typing import Tuple, Dict, Any, Optional, Callable

class SimpleRouter:
    def __init__(self):
        self.routes = {}

    def add_route(self, method: str, path: str, handler: Callable):
        # Convert path parameters to regex pattern
        pattern = re.sub(r'{([^/]+)}', r'(?P<\1>[^/]+)', path)
        self.routes[(method, pattern)] = handler

    def resolve(self, method: str, path: str) -> Tuple[Optional[Callable], Dict[str, str]]:
        for (route_method, pattern), handler in self.routes.items():
            if method != route_method:
                continue
            match = re.match(f'^{pattern}$', path)
            if match:
                return handler, match.groupdict()
        return None, {} 