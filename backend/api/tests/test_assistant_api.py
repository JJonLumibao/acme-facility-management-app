"""Integration tests for the assistant endpoints against the seeded demo data."""
import json
import os

import pytest

TEST_DB = os.getenv("TEST_POSTGRES_NAME", "")
if "test" not in TEST_DB:
    pytest.skip("TEST_POSTGRES_NAME not set to a disposable *test* database", allow_module_level=True)

os.environ["POSTGRES_NAME"] = TEST_DB
os.environ.setdefault("IS_LOCAL", "true")

from main import handler  # noqa: E402
from seed import DEMO_PASSWORD, reset_and_seed  # noqa: E402


def call(method, path, body=None, token=None):
    headers = {"content-type": "application/json", **({"authorization": f"Bearer {token}"} if token else {})}
    response = handler({
        "rawPath": path, "requestContext": {"http": {"method": method}}, "headers": headers,
        "body": json.dumps(body) if body is not None else None,
    })
    return response["statusCode"], json.loads(response["body"])


@pytest.fixture(scope="module")
def tokens():
    reset_and_seed(verbose=False)
    login = lambda email: call("POST", "/auth/login", {"email": email, "password": DEMO_PASSWORD})[1]["token"]  # noqa: E731
    return {"admin": login("admin@acme.inc"), "employee": login("jordan.lee@acme.inc")}


def test_admin_hotspot_question_uses_real_data(tokens):
    status, reply = call("POST", "/assistant", {"message": "What's the hottest spot for issues?"}, tokens["admin"])
    assert status == 200
    assert "3-A12" in reply["answer"] or "Boardroom 3A" in reply["answer"]


def test_employee_answers_are_scoped(tokens):
    status, reply = call("POST", "/assistant", {"message": "What's the status of my incidents?"}, tokens["employee"])
    assert status == 200 and reply["answer"].startswith("You have")
    status, reply = call("POST", "/assistant", {"message": "Where do issues happen most?"}, tokens["employee"])
    assert "only available to facility admins" in reply["answer"]


def test_suggestions_match_role(tokens):
    status, reply = call("GET", "/assistant", token=tokens["employee"])
    assert status == 200 and "What's the status of my incidents?" in reply["suggestions"]


def test_assistant_validation_and_auth(tokens):
    assert call("POST", "/assistant", {"message": "  "}, tokens["admin"])[0] == 400
    assert call("POST", "/assistant", {"message": "x" * 501}, tokens["admin"])[0] == 400
    assert call("POST", "/assistant", {"message": "hi"})[0] == 401
