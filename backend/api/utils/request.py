"""Helpers for normalizing Lambda Function URL events into a simple request dict."""
import base64
import json
from typing import Any, Dict


def strip_service_prefix(path: str) -> str:
    """Remove the `/api/<service-name>` prefix CloudFront uses to route requests to this Lambda.

    In the cloud the browser calls e.g. `/api/api/incidents` and CloudFront forwards the full path, while
    locally the dev server and the LocalStack proxy already send `/incidents`. No route starts with `/api`.
    """
    if path == "/api" or not path.startswith("/api/"):
        return path
    remainder = path.split("/", 3)[3:]  # ['', 'api', '<service>', 'rest/of/path']
    return "/" + (remainder[0] if remainder else "")


def parse_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a raw Lambda event into a normalized request dict (method/path/query/headers/body)."""
    request_context = event.get("requestContext", {}) or {}
    http_ctx = request_context.get("http", {}) or {}
    method = http_ctx.get("method") or event.get("httpMethod") or "GET"
    path = event.get("rawPath") or event.get("path") or "/"
    query = event.get("queryStringParameters") or {}
    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}

    raw_body = event.get("body")
    body: Dict[str, Any] = {}
    if raw_body:
        if event.get("isBase64Encoded"):
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        try:
            body = json.loads(raw_body)
        except (json.JSONDecodeError, TypeError):
            body = {}

    return {"method": method, "path": strip_service_prefix(path or "/"), "query": query, "headers": headers, "body": body}
