"""Integration test for the one-time automatic demo seed (needs a disposable TEST_POSTGRES_NAME database)."""
import os

import pytest

TEST_DB = os.getenv("TEST_POSTGRES_NAME", "")
if "test" not in TEST_DB:
    pytest.skip("TEST_POSTGRES_NAME not set to a disposable *test* database", allow_module_level=True)

os.environ["POSTGRES_NAME"] = TEST_DB
os.environ.setdefault("IS_LOCAL", "true")

from db import get_connection, init_schema  # noqa: E402
from seed import INCIDENTS, USERS, seed_if_empty  # noqa: E402


def _count(table):
    with get_connection().cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")  # nosec: fixed table names from this test
        return cur.fetchone()[0]


def test_seed_if_empty_runs_once_and_never_overwrites():
    init_schema()
    with get_connection().cursor() as cur:
        cur.execute(
            "TRUNCATE incident_events, incident_notes, incidents, seats, floors, buildings, "
            "engineer_profiles, users RESTART IDENTITY CASCADE"
        )

    # A bootstrap-only database (just an admin account, no facilities/incidents) still counts as unused.
    with get_connection().cursor() as cur:
        cur.execute(
            "INSERT INTO users (email, password_hash, full_name, role) "
            "VALUES ('boot@acme.inc', 'x', 'Boot Admin', 'facility_admin')"
        )
    assert seed_if_empty() is True
    assert _count("users") == len(USERS) and _count("incidents") == len(INCIDENTS)

    # Data added after seeding survives: a non-empty database is never re-seeded.
    with get_connection().cursor() as cur:
        cur.execute("INSERT INTO buildings (name) VALUES ('Added later')")
    assert seed_if_empty() is False
    assert _count("buildings") == 4 and _count("users") == len(USERS)
