"""Helpers for building consistent Lambda-compatible JSON responses."""
import json
from typing import Any, Dict, Optional


def json_response(status: int, payload: Any) -> dict:
    """Build a Lambda Function URL response dict with a JSON-encoded body."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=str),
    }


def success(data: Any, status: int = 200) -> dict:
    """Build a successful JSON response."""
    return json_response(status, data)


def no_content() -> dict:
    """Build an empty 204 response (used for successful deletes)."""
    return {"statusCode": 204, "headers": {}, "body": ""}


def error(message: str, status: int = 400, details: Optional[Any] = None) -> dict:
    """Build an error JSON response with an optional details payload."""
    payload: Dict[str, Any] = {"error": message}
    if details is not None:
        payload["details"] = details
    return json_response(status, payload)


__all__ = ["json_response", "success", "no_content", "error"]
