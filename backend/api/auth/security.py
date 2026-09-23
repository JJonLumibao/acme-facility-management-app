"""Password hashing and JWT helpers (short-lived access tokens + longer-lived refresh tokens)."""
import os
import time

import bcrypt
import jwt

# Injected by Terraform in the cloud (infra/locals.tf); the fallback is for local development only.
JWT_SECRET = os.getenv("JWT_SECRET", "local-dev-only-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL_SECONDS = 30 * 60          # sent with every API request
REFRESH_TOKEN_TTL_SECONDS = 7 * 24 * 3600   # only used to obtain new access tokens


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(claims: dict, token_type: str, ttl_seconds: int) -> str:
    now = int(time.time())
    payload = {**claims, "type": token_type, "iat": now, "exp": now + ttl_seconds}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_token(user_id: int, email: str, role: str) -> str:
    """Create a signed access token carrying the user's id, email, and role."""
    return _create_token({"sub": str(user_id), "email": email, "role": role}, "access", ACCESS_TOKEN_TTL_SECONDS)


def create_refresh_token(user_id: int) -> str:
    """Create a signed refresh token. It only identifies the user; role is re-read from the database on refresh."""
    return _create_token({"sub": str(user_id)}, "refresh", REFRESH_TOKEN_TTL_SECONDS)


def decode_token(token: str, expected_type: str = "access") -> dict:
    """Decode and verify a JWT, raising jwt exceptions if invalid/expired or of the wrong type."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    # Tokens issued before refresh support had no "type" claim; they are access tokens.
    if payload.get("type", "access") != expected_type:
        raise jwt.InvalidTokenError(f"Expected a {expected_type} token")
    return payload
