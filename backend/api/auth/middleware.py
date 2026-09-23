"""Authentication and role-based authorization helpers for route handlers."""
from functools import wraps
from typing import Any, Callable, Dict, Optional

import jwt

from auth.security import decode_token


class AuthError(Exception):
    """Raised when a request is unauthenticated or lacks the required role."""

    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def get_current_user(headers: Dict[str, str]) -> Dict[str, Any]:
    """Extract and verify the access token from request headers, returning the user claims.

    Accepts `Authorization: Bearer <token>` or `X-Auth-Token: <token>`. The latter exists because
    CloudFront strips the Authorization header from GET requests before they reach the Lambda.
    """
    auth_header = headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
    elif headers.get("x-auth-token"):
        token = headers["x-auth-token"]
    else:
        raise AuthError("Missing or invalid Authorization header")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid token") from exc

    return {"id": int(payload["sub"]), "email": payload["email"], "role": payload["role"]}


def require_roles(*roles: str) -> Callable:
    """Decorator factory restricting a route handler to specific user roles (none = any authenticated user)."""

    def decorator(handler_func: Callable) -> Callable:
        @wraps(handler_func)
        def wrapped(request: Dict[str, Any], **kwargs: Any) -> Optional[Any]:
            user = get_current_user(request["headers"])
            if roles and user["role"] not in roles:
                raise AuthError("Insufficient permissions", status=403)
            request["user"] = user
            return handler_func(request, **kwargs)

        return wrapped

    return decorator
