"""Lightweight path router for dispatching Lambda events to handler functions."""
import re
from typing import Callable, Dict, Optional, Tuple


class Router:
    """Registers (method, path pattern) -> handler mappings and matches incoming requests."""

    def __init__(self) -> None:
        self._routes = []

    def add(self, method: str, pattern: str, handler: Callable) -> None:
        """Register a handler for the given HTTP method and path pattern (supports {param} segments)."""
        regex_pattern = re.sub(r"{(\w+)}", r"(?P<\1>[^/]+)", pattern)
        compiled = re.compile(f"^{regex_pattern}$")
        self._routes.append((method.upper(), pattern, compiled, handler))

    def get(self, pattern: str, handler: Callable) -> None:
        """Register a GET route."""
        self.add("GET", pattern, handler)

    def post(self, pattern: str, handler: Callable) -> None:
        """Register a POST route."""
        self.add("POST", pattern, handler)

    def put(self, pattern: str, handler: Callable) -> None:
        """Register a PUT route."""
        self.add("PUT", pattern, handler)

    def delete(self, pattern: str, handler: Callable) -> None:
        """Register a DELETE route."""
        self.add("DELETE", pattern, handler)

    def match(self, method: str, path: str) -> Tuple[Optional[Callable], Dict[str, str]]:
        """Find the handler and extracted path parameters for a method/path pair."""
        for route_method, _pattern, regex, handler in self._routes:
            if route_method != method.upper():
                continue
            match = regex.match(path)
            if match:
                return handler, match.groupdict()
        return None, {}

    def routes(self) -> list:
        """Return all registered (method, pattern) pairs, e.g. for generating external API docs."""
        return [(method, pattern) for method, pattern, _regex, _handler in self._routes]
