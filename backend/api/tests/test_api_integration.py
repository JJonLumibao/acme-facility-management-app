"""End-to-end API tests through the Lambda handler against a real PostgreSQL database.

Skipped unless TEST_POSTGRES_NAME points at a dedicated, disposable database (its name must contain
"test"; all tables are truncated). Example:

    createdb -h localhost -U postgres incidents_test
    TEST_POSTGRES_NAME=incidents_test POSTGRES_USER=postgres POSTGRES_PASS=postgres123 \
        python -m pytest tests
"""
import json
import os

import pytest

TEST_DB = os.getenv("TEST_POSTGRES_NAME", "")
if "test" not in TEST_DB:
    pytest.skip("TEST_POSTGRES_NAME not set to a disposable *test* database", allow_module_level=True)

os.environ["POSTGRES_NAME"] = TEST_DB
os.environ.setdefault("IS_LOCAL", "true")

from db import get_connection, init_schema  # noqa: E402
from main import handler  # noqa: E402

PASSWORD = "Passw0rd!"


def call(method, path, body=None, token=None, query=None):
    """Invoke the Lambda handler like a Function URL request and return (status, parsed body)."""
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    response = handler({
        "rawPath": path,
        "requestContext": {"http": {"method": method}},
        "headers": headers,
        "queryStringParameters": query,
        "body": json.dumps(body) if body is not None else None,
    })
    return response["statusCode"], json.loads(response["body"])


@pytest.fixture(scope="module")
def world():
    """Fresh database with an admin, employee, engineer and a building/floor/seat."""
    init_schema()
    with get_connection().cursor() as cur:
        cur.execute(
            "TRUNCATE incident_events, incident_notes, incidents, seats, floors, buildings, "
            "engineer_profiles, users RESTART IDENTITY CASCADE"
        )

    def register_and_login(email, name, role=None):
        status, _ = call("POST", "/auth/register", {"email": email, "password": PASSWORD, "full_name": name, "role": role})
        assert status == 201
        return call("POST", "/auth/login", {"email": email, "password": PASSWORD})[1]["token"]

    admin = register_and_login("admin@acme.inc", "Ada Admin", role="facility_admin")
    employee = register_and_login("emp@acme.inc", "Eve Employee")

    status, engineer = call(
        "POST", "/engineers",
        {"email": "eng@acme.inc", "password": PASSWORD, "full_name": "Sam Engineer", "department": "facilities"},
        admin,
    )
    assert status == 201 and engineer["department"] == "facilities"
    engineer_token = call("POST", "/auth/login", {"email": "eng@acme.inc", "password": PASSWORD})[1]["token"]

    building = call("POST", "/buildings", {"name": "HQ"}, admin)[1]
    floor = call("POST", f"/buildings/{building['id']}/floors", {"name": "3F"}, admin)[1]
    seat = call("POST", f"/floors/{floor['id']}/seats", {"label": "3-101"}, admin)[1]
    return {
        "admin": admin, "employee": employee, "engineer": engineer_token, "engineer_id": engineer["user_id"],
        "building": building, "floor": floor, "seat": seat,
    }


def test_registration_rules(world):
    assert call("POST", "/auth/register", {"email": "x@gmail.com", "password": "p", "full_name": "X"})[0] == 400
    # The bootstrap admin already exists, so this falls back to an employee account.
    status, user = call(
        "POST", "/auth/register", {"email": "sneaky@acme.inc", "password": "p", "full_name": "S", "role": "facility_admin"}
    )
    assert status == 201 and user["role"] == "employee"
    engineer_payload = {"email": "eng@gmail.com", "password": "p", "full_name": "E"}
    assert call("POST", "/engineers", engineer_payload, world["admin"])[0] == 400


def test_catalog_exposes_categories_and_role_transitions(world):
    status, catalog = call("GET", "/catalog", token=world["employee"])
    assert status == 200
    assert "hvac" in {category["key"] for category in catalog["categories"]}
    assert catalog["transitions"]["resolved"] == ["closed", "open"]


def test_incident_validation(world):
    base = {"title": "Hot", "building_id": world["building"]["id"]}
    assert call("POST", "/incidents", {**base, "category": "weather"}, world["employee"])[0] == 400
    other = call("POST", "/buildings", {"name": "Annex"}, world["admin"])[1]
    status, body = call(
        "POST", "/incidents", {**base, "category": "hvac", "building_id": other["id"], "floor_id": world["floor"]["id"]},
        world["employee"],
    )
    assert status == 400 and body["details"]["field"] == "floor_id"


def test_full_lifecycle_timeline_and_dashboard(world):
    admin, employee, engineer = world["admin"], world["employee"], world["engineer"]
    status, incident = call(
        "POST", "/incidents",
        {
            "title": "AC not working", "category": "hvac", "priority": "high",
            "building_id": world["building"]["id"], "floor_id": world["floor"]["id"], "seat_id": world["seat"]["id"],
        },
        employee,
    )
    assert status == 201
    assert incident["status"] == "open" and incident["building_name"] == "HQ" and incident["seat_label"] == "3-101"
    path = f"/incidents/{incident['id']}"

    # Engineers only see tickets assigned to them.
    assert call("GET", "/incidents", token=engineer)[1] == []
    assert call("GET", path, token=engineer)[0] == 403

    # Workload ranking recommends the facilities engineer for an HVAC ticket.
    workload = call("GET", "/engineers/workload", token=admin, query={"category": "hvac"})[1]
    assert workload["department"] == "facilities"
    assert workload["engineers"][0]["recommended"] and workload["engineers"][0]["department_match"]

    status, updated = call("PUT", path, {"assigned_to": world["engineer_id"]}, admin)
    assert status == 200
    assert updated["assignee_name"] == "Sam Engineer" and updated["assigned_at"] and updated["acknowledged_at"]
    assert call("PUT", path, {"assigned_to": 1}, admin)[0] == 400  # admin is not an engineer

    status, updated = call("PUT", path, {"status": "in_progress"}, engineer)
    assert status == 200 and updated["started_at"]
    assert call("PUT", path, {"status": "blocked"}, engineer)[0] == 400  # reason required
    status, updated = call("PUT", path, {"status": "blocked", "status_reason": "Waiting on compressor"}, engineer)
    assert updated["blocked_reason"] == "Waiting on compressor"
    status, updated = call("PUT", path, {"status": "resolved", "status_reason": "Replaced compressor"}, engineer)
    assert updated["resolved_at"] and updated["blocked_reason"] is None
    assert call("PUT", path, {"status": "closed"}, engineer)[0] == 400  # engineers cannot close

    status, updated = call("PUT", path, {"status": "closed"}, employee)
    assert status == 200 and updated["closed_at"]
    assert call("POST", f"{path}/notes", {"message": "thanks"}, employee)[0] == 409  # closed is read-only

    notes = call("GET", f"{path}/notes", token=employee)[1]
    assert [note["message"] for note in notes] == ["Blocked: Waiting on compressor", "Resolution: Replaced compressor"]
    assert notes[0]["author_name"] == "Sam Engineer"

    timeline = call("GET", f"{path}/timeline", token=employee)[1]
    assert [(e["event_type"], e["to_value"]) for e in timeline] == [
        ("created", "open"),
        ("assigned", "Sam Engineer"),
        ("status_changed", "in_progress"),
        ("status_changed", "blocked"),
        ("status_changed", "resolved"),
        ("status_changed", "closed"),
    ]

    summary = call("GET", "/dashboard/summary", token=admin)[1]
    assert summary["response_times"]["resolve"]["count"] == 1
    assert summary["hotspots"]["seats"][0]["label"] == "3-101"
    assert summary["communication"]["staff_update_rate"] == 100
    assert summary["by_category"][0]["category"] == "hvac"
    employee_summary = call("GET", "/dashboard/summary", token=employee)[1]
    assert employee_summary["hotspots"] is None and employee_summary["kpis"]["total"] == 1


def test_escalation_filters_and_referential_delete(world):
    admin, employee = world["admin"], world["employee"]
    status, incident = call(
        "POST", "/incidents",
        {"title": "Wi-Fi down", "category": "network", "building_id": world["building"]["id"]},
        employee,
    )
    path = f"/incidents/{incident['id']}"
    assert call("PUT", path, {"is_escalated": True}, employee)[0] == 400  # reason required
    status, updated = call("PUT", path, {"is_escalated": True, "escalation_reason": "Whole floor offline"}, employee)
    assert status == 200 and updated["is_escalated"]

    attention = call("GET", "/dashboard/summary", token=admin)[1]["needs_attention"]
    assert [item["id"] for item in attention] == [incident["id"]]

    escalated = call("GET", "/incidents", token=admin, query={"escalated": "true", "status": "open,in_progress"})[1]
    assert [item["id"] for item in escalated] == [incident["id"]]
    by_id = call("GET", "/incidents", token=admin, query={"search": f"#{incident['id']}"})[1]
    assert [item["id"] for item in by_id] == [incident["id"]]
    assert call("GET", "/incidents", token=admin, query={"status": "bogus"})[0] == 400

    # Buildings with incidents can't be deleted - clean 409 instead of a 500.
    assert call("DELETE", f"/buildings/{world['building']['id']}", token=admin)[0] == 409


def test_archiving_cascades_to_floors_seats_and_incidents(world):
    admin, employee = world["admin"], world["employee"]
    building = call("POST", "/buildings", {"name": "Old Warehouse"}, admin)[1]
    floor = call("POST", f"/buildings/{building['id']}/floors", {"name": "G"}, admin)[1]
    seat = call("POST", f"/floors/{floor['id']}/seats", {"label": "G-1"}, admin)[1]
    report = {
        "title": "Leak", "category": "plumbing",
        "building_id": building["id"], "floor_id": floor["id"], "seat_id": seat["id"],
    }
    incident = call("POST", "/incidents", report, employee)[1]
    ids = lambda response: [row["id"] for row in response[1]]  # noqa: E731
    active_before = call("GET", "/dashboard/summary", token=admin)[1]["kpis"]["active"]

    # Can't delete (incident history), but can archive - which cascades.
    assert call("DELETE", f"/buildings/{building['id']}", token=admin)[0] == 409
    assert call("PUT", f"/buildings/{building['id']}", {"is_archived": "yes"}, admin)[0] == 400
    status, archived = call("PUT", f"/buildings/{building['id']}", {"is_archived": True}, admin)
    assert status == 200 and archived["is_archived"]
    assert call("GET", f"/floors/{floor['id']}", token=admin)[1]["is_archived"]
    assert call("GET", f"/seats/{seat['id']}", token=admin)[1]["is_archived"]

    # Location hidden from new reports; incident hidden from lists and dashboards, read-only, still viewable.
    assert building["id"] not in ids(call("GET", "/buildings", token=employee))
    assert building["id"] in ids(call("GET", "/buildings", token=admin, query={"include_archived": "true"}))
    assert call("POST", "/incidents", report, employee)[0] == 400
    assert incident["id"] not in ids(call("GET", "/incidents", token=employee))
    assert incident["id"] in ids(call("GET", "/incidents", token=admin, query={"archived": "true"}))
    assert call("GET", "/dashboard/summary", token=admin)[1]["kpis"]["active"] == active_before - 1
    status, archived_incident = call("GET", f"/incidents/{incident['id']}", token=employee)
    assert status == 200 and archived_incident["is_archived"] and archived_incident["allowed_transitions"] == []
    assert call("PUT", f"/incidents/{incident['id']}", {"priority": "high"}, employee)[0] == 409
    assert call("POST", f"/incidents/{incident['id']}/notes", {"message": "hi"}, employee)[0] == 409

    # A floor can't be restored while its building is archived; restoring the building restores everything.
    assert call("PUT", f"/floors/{floor['id']}", {"is_archived": False}, admin)[0] == 400
    assert not call("PUT", f"/buildings/{building['id']}", {"is_archived": False}, admin)[1]["is_archived"]
    assert not call("GET", f"/seats/{seat['id']}", token=admin)[1]["is_archived"]
    assert incident["id"] in ids(call("GET", "/incidents", token=employee))
    assert call("GET", "/dashboard/summary", token=admin)[1]["kpis"]["active"] == active_before

    # Archiving just a seat archives only the incidents reported at that seat.
    call("PUT", f"/seats/{seat['id']}", {"is_archived": True}, admin)
    assert not call("GET", f"/floors/{floor['id']}", token=admin)[1]["is_archived"]
    assert incident["id"] not in ids(call("GET", "/incidents", token=employee))


def test_refresh_tokens_cloud_paths_and_204_deletes(world):
    admin = world["admin"]
    status, session = call("POST", "/auth/login", {"email": "emp@acme.inc", "password": PASSWORD})
    assert status == 200 and session["refresh_token"] and session["expires_in"] > 0

    # Refresh issues a working access token; refresh tokens can't call the API; garbage is rejected.
    status, renewed = call("POST", "/auth/refresh", {"refresh_token": session["refresh_token"]})
    assert status == 200 and renewed["user"]["email"] == "emp@acme.inc"
    assert call("GET", "/users/me", token=renewed["token"])[0] == 200
    assert call("GET", "/users/me", token=session["refresh_token"])[0] == 401
    assert call("POST", "/auth/refresh", {"refresh_token": "nope"})[0] == 401

    # CloudFront-style path prefix and the X-Auth-Token header (Authorization is stripped on GETs).
    response = handler({
        "rawPath": "/api/api/users/me",
        "requestContext": {"http": {"method": "GET"}},
        "headers": {"x-auth-token": renewed["token"]},
    })
    assert response["statusCode"] == 200 and json.loads(response["body"])["email"] == "emp@acme.inc"

    # Successful deletes return 204 No Content with an empty body.
    building = call("POST", "/buildings", {"name": "Temp"}, admin)[1]
    response = handler({
        "rawPath": f"/buildings/{building['id']}",
        "requestContext": {"http": {"method": "DELETE"}},
        "headers": {"authorization": f"Bearer {admin}"},
    })
    assert response["statusCode"] == 204 and response["body"] == ""
    assert call("GET", f"/buildings/{building['id']}", token=admin)[0] == 404
