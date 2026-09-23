"""Business logic for user registration and authentication."""
from typing import Any, Dict

import jwt

from auth.security import (
    ACCESS_TOKEN_TTL_SECONDS,
    create_refresh_token,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from models import user_model
from utils.responses import error, success
from utils.validation import ValidationError, require_fields

ALLOWED_EMAIL_DOMAIN = "acme.inc"


def register(request: Dict[str, Any]) -> Dict[str, Any]:
    """Register a new employee account, or bootstrap the first facility admin if none exists yet."""
    payload = request["body"]
    require_fields(payload, ["email", "password", "full_name"])

    email = payload["email"].strip().lower()
    if not email.endswith(f"@{ALLOWED_EMAIL_DOMAIN}"):
        raise ValidationError(f"Email must be a @{ALLOWED_EMAIL_DOMAIN} address", field="email")

    if user_model.get_user_by_email(email):
        raise ValidationError("Email is already registered", field="email")

    requested_role = payload.get("role", "employee")
    if requested_role == "facility_admin" and not user_model.any_admin_exists():
        role = "facility_admin"
    else:
        role = "employee"

    password_hash = hash_password(payload["password"])
    user = user_model.create_user(email, password_hash, payload["full_name"].strip(), role)
    return success(user, status=201)


def login(request: Dict[str, Any]) -> Dict[str, Any]:
    """Authenticate a user and issue a JWT access token."""
    payload = request["body"]
    require_fields(payload, ["email", "password"])

    email = payload["email"].strip().lower()
    user = user_model.get_user_by_email(email)
    if not user or not verify_password(payload["password"], user["password_hash"]):
        return error("Invalid email or password", status=401)

    public_user = {key: value for key, value in user.items() if key != "password_hash"}
    return success({**_issue_tokens(public_user), "user": public_user})


def refresh(request: Dict[str, Any]) -> Dict[str, Any]:
    """Exchange a valid refresh token for a new access token (and a rotated refresh token).

    The user is re-read from the database, so deleted accounts are rejected and role changes apply.
    """
    payload = request["body"]
    require_fields(payload, ["refresh_token"])
    try:
        claims = decode_token(payload["refresh_token"], expected_type="refresh")
    except jwt.ExpiredSignatureError:
        return error("Session expired, please sign in again", status=401)
    except jwt.InvalidTokenError:
        return error("Invalid refresh token", status=401)

    user = user_model.get_user_by_id(int(claims["sub"]))
    if not user:
        return error("Account no longer exists", status=401)
    return success({**_issue_tokens(user), "user": user})


def _issue_tokens(user: Dict[str, Any]) -> Dict[str, Any]:
    """Access token for API calls plus a refresh token to renew it without re-entering the password."""
    return {
        "token": create_token(user["id"], user["email"], user["role"]),
        "refresh_token": create_refresh_token(user["id"]),
        "expires_in": ACCESS_TOKEN_TTL_SECONDS,
    }
