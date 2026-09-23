"""Integration tests for the admin "Reset demo data" action (needs a disposable TEST_POSTGRES_NAME database)."""
import json
import os

import pytest

TEST_DB = os.getenv("TEST_POSTGRES_NAME", "")
if "test" not in TEST_DB:
    pytest.skip("TEST_POSTGRES_NAME not set to a disposable *test* database", allow_module_level=True)

os.environ["POSTGRES_NAME"] = TEST_DB
os.environ.setdefault("IS_LOCAL", "true")

from db import get_connection  # noqa: E402
from main import handler  # noqa: E402
from seed import DEMO_PASSWORD, INCIDENTS, USERS, reset_and_seed  # noqa: E402

PATH = "/admin/reset-demo-data"


def call(method, path, body=None, token=None):
    headers = {"content-type": "application/json", **({"authorization": f"Bearer {token}"} if token else {})}
    response = handler({
        "rawPath": path, "requestContext": {"http": {"method": method}}, "headers": headers,
        "body": json.dumps(body) if body is not None else None,
    })
    return response["statusCode"], json.loads(response["body"])


def login(email):
    return call("POST", "/auth/login", {"email": email, "password": DEMO_PASSWORD})[1]["token"]


def count(table):
    with get_connection().cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")  # nosec: fixed table names from this test
        return cur.fetchone()[0]


@pytest.fixture()
def demo():
    reset_and_seed(verbose=False)
    return {"admin": login("admin@acme.inc"), "employee": login("jordan.lee@acme.inc")}


def test_admin_reset_restores_demo_data(demo):
    call("POST", "/buildings", {"name": "Test-only building"}, demo["admin"])
    buildings_before = count("buildings")

    status, body = call("POST", PATH, {"confirm": "RESET"}, demo["admin"])

    assert status == 200 and body == {"reset": True, "users": len(USERS), "incidents": len(INCIDENTS)}
    assert count("buildings") == buildings_before - 1
    assert count("incidents") == len(INCIDENTS)


def test_reset_is_guarded(demo, monkeypatch):
    assert call("POST", PATH, {"confirm": "RESET"}, demo["employee"])[0] == 403
    assert call("POST", PATH, {}, demo["admin"])[0] == 400
    assert call("POST", PATH, {"confirm": "RESET"})[0] == 401

    # Outside local dev and the cloud demo, the action doesn't exist.
    monkeypatch.setenv("IS_LOCAL", "false")
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)
    assert call("POST", PATH, {"confirm": "RESET"}, demo["admin"])[0] == 404


def test_catalog_flag_only_for_admins(demo):
    assert call("GET", "/catalog", token=demo["admin"])[1]["demo_reset_enabled"] is True
    assert call("GET", "/catalog", token=demo["employee"])[1]["demo_reset_enabled"] is False
