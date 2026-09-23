"""Unit tests for request parsing (CloudFront path prefix) and access/refresh token types."""
import jwt
import pytest

from auth.security import create_refresh_token, create_token, decode_token
from utils.request import parse_event, strip_service_prefix


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/api/api/incidents", "/incidents"),        # cloud: CloudFront forwards /api/<service>/...
        ("/api/api/incidents/5/notes", "/incidents/5/notes"),
        ("/api/api", "/"),
        ("/api/api/", "/"),
        ("/incidents", "/incidents"),                # local dev server / LocalStack proxy
        ("/", "/"),
    ],
)
def test_strip_service_prefix(path, expected):
    assert strip_service_prefix(path) == expected


def test_parse_event_applies_prefix_stripping():
    event = {"rawPath": "/api/api/dashboard/summary", "requestContext": {"http": {"method": "GET"}}}
    assert parse_event(event)["path"] == "/dashboard/summary"


def test_access_and_refresh_tokens_are_not_interchangeable():
    access, refresh = create_token(1, "a@acme.inc", "employee"), create_refresh_token(1)
    assert decode_token(access)["role"] == "employee"
    assert decode_token(refresh, expected_type="refresh")["sub"] == "1"
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(refresh)  # a refresh token can't be used to call the API
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(access, expected_type="refresh")
